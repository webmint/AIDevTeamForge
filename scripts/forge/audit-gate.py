#!/usr/bin/env python3
"""Audit gate: blocks new development while an audit is due or its blocking findings are unfixed.

The state is derived, never stored, so every developer and CI see the same thing and it cannot drift:
- an audit is a commit on the integration ref that adds a file matching `auditGate.auditReports` (`/audit` writes
  `audits/YYYY-MM-DD-audit.md`);
- a merged spec is a file matching `auditGate.mergedSpecMarker` added on the ref after the last audit (`/summarize`
  writes `specs/NNN-feature-name/summary.md`); a remediation spec (its spec file carries
  `Audit gate: remediation of <report> ...`) is not counted;
- a blocking finding is an open issue returned by `auditGate.blockingIssues.command` that has every label in
  `auditGate.blockingIssues.labels` (one issue per triaged theme, closed by the pull request that fixes it).
The gate is blocked when any of these holds:
  1. `auditGate.every` specs merged since the last audit (an audit is due);
  2. the last audit report has no `auditGate.triageHeading` line, or a theme row in that section still carries the
     placeholder `(to file)` instead of its issue (the audit is not triaged: `/audit` drafts the table, the
     orchestrator files one issue per blocking theme and replaces the placeholder);
  3. a blocking issue is open (the audit is not fixed).
All values come from the project binding `.claude/quality-profile.json` (`auditGate`, `integrationRef`), loaded
through scripts/forge/quality_profile.py.

Blocking issues source: `auditGate.blockingIssues.command` is any command that prints a JSON array of issues, each
an object with an integer `number`, a `title` and, optionally, `labels` (names, or objects with a `name`). A row that
carries `labels` blocks when it has every required label; a row without `labels` is taken as already filtered by the
command and blocks. The default command is `gh issue list`; a project on another tracker replaces only the command.
When the command cannot answer (it is not installed, there is no network, the repository is not on that tracker, it
exits non-zero, times out or prints no such array), the blocking issues are `unknown`: the state says so with the
reason on one line, reason 3 does not count, and the other reasons and exit codes are unchanged. A remediation start
line then names its issues unverified, and the triage check only requires a blocking row to name an issue.

Usage:
  python3 scripts/forge/audit-gate.py status [--ref <ref>] [--json]
      print the state; exit 0 whatever it is.
  python3 scripts/forge/audit-gate.py start-line [--ref <ref>] [--remediation "#n,#m"]
      before a new spec starts (`/specify`): print the line the spec records in its header and exit 0, or exit 1 with
      the reasons. A feature spec gets `Audit gate: started at <n>/<every> after <report>` and needs an open gate. A
      remediation spec (--remediation, naming the blocking issues it fixes) gets
      `Audit gate: remediation of <report> (#n, #m)` and is allowed while blocked by 1 or 3, never while the last
      audit is untriaged.
  python3 scripts/forge/audit-gate.py check-pr --base <ref> [--head <rev>]
      on a change: a change that adds a spec file (`auditGate.specFile`) fails while the gate is blocked, unless the
      spec carries a remediation line, or a start line with a count below the threshold (it started legally and is
      in flight). Changes that add no spec pass, except that a change adding an audit report must pass `triage-check`
      on it.
  python3 scripts/forge/audit-gate.py triage-check [--report <path>] [--ref <ref>]
      the triage table of an audit report (default: the last report on the ref; --report reads a working-tree file)
      after the orchestrator filed its issues: the table has `Theme`, `Blocks`, `Machine check` and `Issue` columns;
      every row names its machine check (a lint rule, ratchet or catalog test that fails on a new copy; a
      non-blocking row may say `none: <reason>`); every blocking row names at least one open issue that carries every
      blocking label, so a theme that only continues a warning-level issue cannot fail to block. Exit 1 with one line
      per problem.

When `auditGate` is unset (`{}`, as the binding skeleton writes it without an integration ref), every command prints
one line saying so and exits 0: no gate runs, and whether an audit is due is decided by hand. A binding without the
`auditGate` key at all is an error (exit 2).

Exit codes: 0 open / passed / gate unset; 1 blocked / failed; 2 usage, profile or git error.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; the path is set above)

START_LINE = re.compile(r"Audit gate: started at (\d+)/(\d+) after (\S+)")
REMEDIATION_LINE = re.compile(r"Audit gate: remediation of (\S+)")
# The Issue cell of a triage row that `/audit` drafted and the orchestrator has not filed yet.
PENDING_ISSUE = "(to file)"
ISSUES_TIMEOUT_SECONDS = 120


class GateError(Exception):
    """A git call failed or the profile is unusable."""


def git(repo: str, *args: str) -> str:
    """Run git in the repository and return stdout; raise GateError on failure."""
    result = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise GateError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def matches(path: str, pattern: str) -> bool:
    """Match a repo path against a glob segment by segment, so `*` never crosses a `/`."""
    parts, globs = path.split("/"), pattern.split("/")
    return len(parts) == len(globs) and all(fnmatch.fnmatchcase(p, g) for p, g in zip(parts, globs))


def static_prefix(pattern: str) -> str:
    """The leading directories of a glob that hold no wildcard, used to narrow git listings."""
    prefix = []
    for segment in pattern.split("/")[:-1]:
        if any(ch in segment for ch in "*?["):
            break
        prefix.append(segment)
    return "/".join(prefix)


def added_files(repo: str, rev_range: str, pattern: str) -> list[tuple[str, str, str]]:
    """(commit, date, path) for every file matching `pattern` added in `rev_range`, newest first."""
    out = git(repo, "log", "--diff-filter=A", "--format=@%H %cs", "--name-only", rev_range, "--", f":(glob){pattern}")
    rows, commit, date = [], "", ""
    for line in out.splitlines():
        if line.startswith("@"):
            commit, date = line[1:].split(" ", 1)
        elif line.strip() and matches(line.strip(), pattern):
            rows.append((commit, date, line.strip()))
    return rows


def _one_line(text: str) -> str:
    """The first non-empty line of a message, so an unknown reason fits on one line."""
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def blocking_issues(repo: str, gate: dict) -> tuple[list[dict], str | None]:
    """The open blocking issues and None, or no issues and the reason the command could not answer (`unknown`)."""
    spec = gate["blockingIssues"]
    try:
        command = shlex.split(spec["command"])
    except ValueError as exc:
        raise GateError(f"auditGate.blockingIssues.command: {exc}") from exc
    if not command:
        raise GateError("auditGate.blockingIssues.command: empty")
    try:
        result = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=ISSUES_TIMEOUT_SECONDS)
    except FileNotFoundError:
        return [], f"{command[0]}: command not found"
    except subprocess.TimeoutExpired:
        return [], f"{command[0]}: no answer in {ISSUES_TIMEOUT_SECONDS}s"
    except OSError as exc:
        return [], f"{command[0]}: {exc}"
    if result.returncode != 0:
        return [], f"{command[0]} exited {result.returncode}" + (
            f": {_one_line(result.stderr)}" if _one_line(result.stderr) else "")
    try:
        rows = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        return [], f"{command[0]} printed no JSON: {exc}"
    if not isinstance(rows, list):
        return [], f"{command[0]} printed no JSON array"
    required = set(spec["labels"])
    found = []
    for index, row in enumerate(rows):
        number = row.get("number") if isinstance(row, dict) else None
        if not isinstance(number, int) or isinstance(number, bool):
            return [], f"{command[0]}: issue {index} has no integer number"
        if "labels" in row:
            labels = row.get("labels") or []
            names = {label.get("name") if isinstance(label, dict) else label for label in labels}
            if not required <= names:
                continue
        found.append({"number": number, "title": str(row.get("title", ""))})
    return sorted(found, key=lambda issue: issue["number"]), None


def is_remediation(repo: str, ref: str, spec_dir: str, spec_file: str) -> bool:
    """Whether the merged spec in `spec_dir` recorded a remediation line in its spec file."""
    name = spec_file.rsplit("/", 1)[-1]
    try:
        text = git(repo, "show", f"{ref}:{spec_dir}/{name}")
    except GateError:
        return False
    return bool(REMEDIATION_LINE.search(text))


def compute(repo: str, gate: dict, ref: str, issues: list[dict] | None = None, unknown: str | None = None) -> dict:
    """The gate state on `ref`; `issues` are the open blocking issues (fetched when None), `unknown` the reason they
    could not be fetched."""
    git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    prefix = static_prefix(gate["auditReports"])
    listing = git(repo, "ls-tree", "-r", "--name-only", ref, *([prefix] if prefix else []))
    reports = sorted(p for p in listing.splitlines() if matches(p, gate["auditReports"]))

    audits = added_files(repo, ref, gate["auditReports"])
    last = None
    if audits:
        # The newest commit that added a report; when one commit adds several, the last path by name is the newest.
        commit, date = audits[0][0], audits[0][1]
        path = max(p for c, _, p in audits if c == commit)
        last = {"report": path, "commit": commit[:10], "date": date}

    since = f"{audits[0][0]}..{ref}" if audits else ref
    dirs = sorted({p.rsplit("/", 1)[0] for _, _, p in added_files(repo, since, gate["mergedSpecMarker"])})
    remediation = [d for d in dirs if is_remediation(repo, ref, d, gate["specFile"])]
    merged = [d for d in dirs if d not in remediation]
    if issues is None:
        issues, unknown = blocking_issues(repo, gate)

    triage, pending = None, 0
    if last:
        text = git(repo, "show", f"{ref}:{last['report']}")
        present, pending = triage_section(text, gate["triageHeading"])
        triage = present and not pending

    every = gate["every"]
    reasons = []
    if len(merged) >= every:
        reasons.append(f"{len(merged)} specs merged since the last audit (threshold {every})")
    if last and not triage:
        if pending:
            reasons.append(f"the last audit report's '{gate['triageHeading']}' has {pending} theme(s) {PENDING_ISSUE}")
        else:
            reasons.append(f"the last audit report has no '{gate['triageHeading']}' section")
    if issues:
        numbers = ", ".join(f"#{issue['number']}" for issue in issues)
        reasons.append(f"{len(issues)} blocking audit issue(s) open: {numbers}")
    return {
        "ref": ref,
        "every": every,
        "specsSinceAudit": len(merged),
        "specs": merged,
        "remediationSpecs": remediation,
        "blockingIssues": issues,
        "blockingIssuesUnknown": unknown,
        "auditsOnRef": len(reports),
        "lastAudit": last,
        "triage": triage,
        "triagePending": pending,
        "blocked": bool(reasons),
        "reasons": reasons,
    }


def triage_section(text: str, heading: str) -> tuple[bool, int]:
    """Whether the report has the triage heading, and how many lines of that section still carry `PENDING_ISSUE`."""
    present, inside, pending = False, False, 0
    level = len(heading) - len(heading.lstrip("#"))
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == heading:
            present = inside = True
            continue
        if inside and stripped.startswith("#") and len(stripped) - len(stripped.lstrip("#")) <= level:
            inside = False
        if inside and PENDING_ISSUE in stripped:
            pending += 1
    return present, pending


# Cells that name no machine check.
NO_CHECK = {"", "-", "—", "?", "n/a", "none", "(none)", "tbd"}
TRIAGE_COLUMNS = ("theme", "blocks", "machine check", "issue")


def triage_table(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    """The header cells (lower case) and the body rows of the first table in the triage section."""
    header: list[str] = []
    rows: list[list[str]] = []
    inside = False
    level = len(heading) - len(heading.lstrip("#"))
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == heading:
            inside = True
            continue
        if not inside:
            continue
        if stripped.startswith("#") and len(stripped) - len(stripped.lstrip("#")) <= level:
            break
        if not stripped.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not header:
            header = [cell.lower() for cell in cells]
        elif not all(re.fullmatch(r":?-+:?", cell) for cell in cells if cell):
            rows.append(cells)
    return header, rows


def triage_problems(text: str, heading: str, open_numbers: set[int] | None) -> list[str]:
    """One message per triage row that names no machine check, or blocks without an open blocking issue.
    `open_numbers` None means the blocking issues are unknown: a blocking row must then name some issue."""
    header, rows = triage_table(text, heading)
    if not header:
        return [f"no table under '{heading}'"]
    missing = [name for name in TRIAGE_COLUMNS if name not in header]
    if missing:
        return [f"the triage table has no column: {', '.join(missing)}"]
    col = {name: header.index(name) for name in TRIAGE_COLUMNS}
    problems = []
    for cells in rows:
        cell = lambda name: cells[col[name]] if col[name] < len(cells) else ""  # noqa: E731
        theme = cell("theme") or "?"
        blocks = cell("blocks").lower().startswith("yes")
        check = cell("machine check")
        if check.lower() in NO_CHECK or (check.lower().startswith("none") and (blocks or ":" not in check)):
            problems.append(f"{theme}: no machine check (name the lint rule, ratchet or catalog test that fails on "
                            "a new copy; only a non-blocking row may say `none: <reason>`)")
        if blocks:
            issue = cell("issue")
            numbers = {int(n) for n in re.findall(r"#(\d+)", issue)}
            named = numbers if open_numbers is None else numbers & open_numbers
            if PENDING_ISSUE in issue or not named:
                which = "no issue" if open_numbers is None else "no open blocking issue"
                problems.append(f"{theme}: blocks but names {which} ({issue or 'empty'}); file one "
                                "with the blocking labels or relabel the single issue it continues")
    return problems


def issues_text(state: dict) -> str:
    """The blocking-issues part of the status line: the open count, or `unknown` with its reason."""
    if state.get("blockingIssuesUnknown"):
        return f"unknown ({state['blockingIssuesUnknown']})"
    return str(len(state["blockingIssues"]))


def status_line(state: dict) -> str:
    last = state["lastAudit"]
    where = f"{last['report']}, {last['date']}, {last['commit']}" if last else "no audit yet"
    triage = {None: "n/a", True: "present", False: "missing"}[state["triage"]]
    if state.get("triagePending"):
        triage = f"pending ({state['triagePending']} {PENDING_ISSUE})"
    verdict = "BLOCKED" if state["blocked"] else "open"
    return (
        f"audit-gate: {verdict} — specs since last audit {state['specsSinceAudit']}/{state['every']} ({where}); "
        f"audits on {state['ref']}: {state['auditsOnRef']}; triage: {triage}; "
        f"blocking issues open: {issues_text(state)}"
    )


def unknown_note(state: dict) -> list[str]:
    """The one-line note that the blocking issues are unknown and do not count; empty when they are known."""
    reason = state.get("blockingIssuesUnknown")
    return [f"blocking issues unknown ({reason}); not counted"] if reason else []


def check_pr(repo: str, gate: dict, base: str, head: str) -> tuple[bool, dict, list[str]]:
    """Whether the change base...head may pass, the base state and the notes explaining the verdict."""
    diff = git(repo, "diff", "--name-only", "--diff-filter=A", "--no-renames", f"{base}...{head}")
    specs = [p for p in diff.splitlines() if matches(p, gate["specFile"])]
    reports = [p for p in diff.splitlines() if matches(p, gate["auditReports"])]
    state = compute(repo, gate, base)
    if not specs:
        # The way out (fixes, chores, the audit itself) never depends on the tracker: when it is unknown the counter
        # is still shown, and an added audit report's triage check only asks blocking rows to name an issue.
        notes, passed = ["no new spec in this change"] + unknown_note(state), True
        known = state["blockingIssuesUnknown"] is None
        open_numbers = {issue["number"] for issue in state["blockingIssues"]} if known else None
        for report in reports:
            problems = triage_problems(git(repo, "show", f"{head}:{report}"), gate["triageHeading"], open_numbers)
            passed = passed and not problems
            notes += [f"{report}: triage: {problem}" for problem in problems] or [f"{report}: triage check passed"]
        return passed, state, notes
    if not state["blocked"]:
        return True, state, unknown_note(state) + [f"new spec allowed: {', '.join(specs)}"]

    notes, passed = unknown_note(state), True
    for spec in specs:
        text = git(repo, "show", f"{head}:{spec}")
        start, fix = START_LINE.search(text), REMEDIATION_LINE.search(text)
        if fix and state["triage"] is not False:
            notes.append(f"{spec}: remediation of {fix.group(1)} — allowed")
        elif start and int(start.group(1)) < int(start.group(2)):
            notes.append(f"{spec}: started at {start.group(1)}/{start.group(2)} after {start.group(3)}, in flight — allowed")
        else:
            passed = False
            notes.append(f"{spec}: new development is blocked; only remediation specs may start (see the reasons)")
    return passed, state, notes


def start_line(state: dict, remediation: str | None) -> int:
    """Print the start line of a new spec and return 0, or print the reasons it may not start and return 1."""
    report = state["lastAudit"]["report"] if state["lastAudit"] else "none"
    for note in unknown_note(state):
        print(f"audit-gate: {note}", file=sys.stderr)
    if remediation is not None:
        wanted = sorted({int(n) for n in re.findall(r"\d+", remediation)})
        problems = []
        if state["triage"] is False:
            problems.append("the last audit is not triaged yet")
        if not wanted:
            problems.append("--remediation names no issue")
        if state["blockingIssuesUnknown"] is None:
            open_numbers = {issue["number"] for issue in state["blockingIssues"]}
            problems += [f"#{n} is not an open blocking issue" for n in wanted if n not in open_numbers]
        elif wanted:
            print(f"audit-gate: {', '.join(f'#{n}' for n in wanted)} not verified as open blocking issues",
                  file=sys.stderr)
        if problems:
            print(status_line(state))
            for problem in problems:
                print(f"refused: {problem}")
            return 1
        print(f"Audit gate: remediation of {report} ({', '.join(f'#{n}' for n in wanted)})")
        return 0
    if state["blocked"]:
        print(status_line(state))
        for reason in state["reasons"]:
            print(f"blocked: {reason}")
        return 1
    print(f"Audit gate: started at {state['specsSinceAudit']}/{state['every']} after {report}")
    return 0


def triage_check(repo: str, gate: dict, ref: str, report: str | None) -> int:
    """Print the triage problems of an audit report and return 1 when there are any."""
    if report:
        with open(os.path.join(repo, report), encoding="utf-8") as handle:
            text, name = handle.read(), report
    else:
        state = compute(repo, gate, ref, issues=[])
        if not state["lastAudit"]:
            raise GateError(f"no audit report on {ref}")
        name = state["lastAudit"]["report"]
        text = git(repo, "show", f"{ref}:{name}")
    issues, unknown = blocking_issues(repo, gate)
    open_numbers = None if unknown else {issue["number"] for issue in issues}
    if unknown:
        print(f"triage-check: {name}: blocking issues unknown ({unknown}); a blocking row only has to name an issue")
    problems = triage_problems(text, gate["triageHeading"], open_numbers)
    for problem in problems:
        print(f"triage-check: {name}: {problem}")
    print(f"triage-check: {name}: {'FAILED' if problems else 'passed'} ({len(problems)} problem(s))")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", default=quality_profile.DEFAULT_PROFILE)
    sub = parser.add_subparsers(dest="command", required=True)
    p_status = sub.add_parser("status")
    p_status.add_argument("--ref")
    p_status.add_argument("--json", action="store_true")
    p_start = sub.add_parser("start-line")
    p_start.add_argument("--ref")
    p_start.add_argument("--remediation", help='blocking issues this remediation spec fixes, e.g. "#3,#4"')
    p_triage = sub.add_parser("triage-check")
    p_triage.add_argument("--report", help="a working-tree audit report (default: the last report on the ref)")
    p_triage.add_argument("--ref")
    p_pr = sub.add_parser("check-pr")
    p_pr.add_argument("--base", required=True)
    p_pr.add_argument("--head", default="HEAD")
    args = parser.parse_args(argv)

    repo = os.path.dirname(os.path.dirname(os.path.abspath(args.profile)))
    try:
        profile = quality_profile.load(args.profile)
        problems = quality_profile.validate(profile, repo=repo)
        if problems or "auditGate" not in profile:
            raise GateError("quality profile: " + ("; ".join(problems) or "no auditGate section"))
        if quality_profile.is_unset("auditGate", profile["auditGate"]):
            print("audit-gate: auditGate is unset in the quality profile; no audit gate runs "
                  "(decide by hand whether an audit is due)")
            return 0
        gate = profile["auditGate"]
        ref = getattr(args, "ref", None) or profile.get("integrationRef")

        if args.command == "status":
            state = compute(repo, gate, ref)
            print(json.dumps(state, indent=2) if args.json else status_line(state))
            return 0
        if args.command == "triage-check":
            return triage_check(repo, gate, ref, args.report)
        if args.command == "start-line":
            return start_line(compute(repo, gate, ref), args.remediation)

        passed, state, notes = check_pr(repo, gate, args.base, args.head)
        print(status_line(state))
        for note in notes:
            print(f"audit-gate: {note}")
        return 0 if passed else 1
    except (GateError, quality_profile.ProfileError, OSError) as exc:
        print(f"audit-gate: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
