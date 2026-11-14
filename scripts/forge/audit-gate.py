#!/usr/bin/env python3
"""Audit gate: blocks new development while an audit is due or its blocking findings are unfixed.

The state is derived, never stored, so every developer and CI see the same thing and it cannot drift:
- an audit is a commit on the integration ref that adds a file matching `auditGate.auditReports` (`/audit` writes
  `audits/YYYY-MM-DD-audit.md`);
- a merged spec is a file matching `auditGate.mergedSpecMarker` added on the ref after the last audit (`/finalize`
  writes `specs/<KEY|NNN>-feature-name/summary.md`); a remediation spec (its spec file carries
  `Audit gate: remediation of <report> ...`) is not counted;
- a blocking finding is an open issue returned by `auditGate.blockingIssues.command` that has every label in
  `auditGate.blockingIssues.labels` (one issue per triaged theme, closed by the pull request that fixes it); without
  an issue tracker there are none (see below).
The gate is blocked when any of these holds:
  1. `auditGate.every` specs merged since the last audit (an audit is due);
  2. the last audit report has no `auditGate.triageHeading` line, or a blocking theme row in that section (its Blocks
     cell starts with `yes`) still carries the placeholder `(to file)` instead of its issue (the audit is not
     triaged: `/audit` drafts the table, and the user, in the `/audit` triage, files one issue per blocking theme
     and replaces the placeholder);
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

No issue tracker: `auditGate.blockingIssues` absent, or its `command` empty (`""`), means the project has none. The
blocking issues are then known to be none (reason 3 never blocks and there is no `unknown` note; the status says
`0 (no issue tracker)`), `labels` is not required, the cadence (reason 1) and the triage (reason 2) still run, and the
triage table is the record: the triage check accepts a blocking row whose Issue cell is `-`.

Usage:
  python3 scripts/forge/audit-gate.py status [--ref <ref>] [--json]
      print the state; exit 0 whatever it is.
  python3 scripts/forge/audit-gate.py start-line [--ref <ref>] [--remediation "#n,#m" | --remediation "T1,T3"]
      before a new spec starts (`/specify`): print the line the spec records in its header and exit 0, or exit 1 with
      the reasons. A feature spec gets `Audit gate: started at <n>/<every> after <report>` and needs an open gate. A
      remediation spec (--remediation, naming the blocking issues it fixes) gets
      `Audit gate: remediation of <report> (#n, #m)` and is allowed while blocked by 1 or 3, never while the last
      audit is untriaged. Without an issue tracker it names the blocking themes instead (`--remediation T1,T3`:
      each a theme of the last report's triage table whose Blocks cell is `yes`, matched by the leading id of the
      Theme cell) and gets `Audit gate: remediation of <report> (T1, T3)`.
  python3 scripts/forge/audit-gate.py check-pr --base <ref> [--head <rev>]
      on a change: a change that adds a spec file (`auditGate.specFile`) fails while the gate is blocked, unless the
      spec carries a remediation line, or a start line with a count below the threshold (it started legally and is
      in flight). Changes that add no spec pass, except that a change adding an audit report must pass `triage-check`
      on it.
  python3 scripts/forge/audit-gate.py triage-check [--report <path>] [--ref <ref>]
      the triage table of an audit report (default: the last report on the ref; --report reads a working-tree file)
      after the user filed its issues in the `/audit` triage: the table has `Theme`, `Blocks`, `Machine check` and `Issue` columns;
      every row names its machine check (a lint rule, ratchet or catalog test that fails on a new copy; a
      non-blocking row may say `none: <reason>`); every blocking row names at least one open issue that carries every
      blocking label, so a theme that only continues a warning-level issue cannot fail to block (without an issue
      tracker, its Issue cell is `-`). Exit 1 with one line per problem.

When `auditGate` is unset (`{}`, as the binding skeleton writes it without an integration ref), every command prints
one line saying so and exits 0: no gate runs, and whether an audit is due is decided by hand. A binding without the
`auditGate` key at all is an error (exit 2).

An integration ref that does not resolve is an error (exit 2, "integrationRef <ref> does not resolve ..."), except
in a fresh project: no remote, and the working branch holds no audit report and no merged spec. There is then
nothing to count, so the gate is open (`specs since last audit 0/<every>`, "no history yet") and `/specify` can start
the first spec; once a merged spec or an audit lands without the ref, the error returns.

The history is read from the integration ref, so a shallow clone (CI checkouts default to depth 1) is an error:
fetch the full history (e.g. `fetch-depth: 0`).

Exit codes: 0 open / passed / gate unset; 1 blocked / failed; 2 usage, profile or git error, or a shallow clone.
A missing binding file counts as every key unset: one line (`no .claude/quality-profile.json; run python3
scripts/forge/quality_profile.py init`) and exit 0.
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
# The Issue cell of a triage row that `/audit` drafted and the user has not filed yet (the `/audit` triage).
PENDING_ISSUE = "(to file)"
ISSUES_TIMEOUT_SECONDS = 120


class GateError(Exception):
    """A git call failed or the profile is unusable."""


def git(repo: str, *args: str) -> str:
    """Run git in the repository and return stdout; raise GateError on failure. Paths are printed unquoted
    (`core.quotepath=off`), so a spec directory with a non-ASCII name reads as itself."""
    result = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=off", *args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
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
    # `%cd` with `--date=short`: the short-date placeholder (`%c` + `s`) needs git 2.25 or later.
    out = git(repo, "log", "--diff-filter=A", "--date=short", "--format=@%H %cd", "--name-only", rev_range, "--",
              f":(glob){pattern}")
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


def has_tracker(gate: dict) -> bool:
    """Whether the project has an issue tracker: `auditGate.blockingIssues` is present and its `command` is not empty."""
    spec = gate.get("blockingIssues")
    return isinstance(spec, dict) and bool(str(spec.get("command") or "").strip())


def blocking_issues(repo: str, gate: dict) -> tuple[list[dict], str | None]:
    """The open blocking issues and None, or no issues and the reason the command could not answer (`unknown`).
    Without an issue tracker (see `has_tracker`) there are none, and they are known."""
    if not has_tracker(gate):
        return [], None
    spec = gate["blockingIssues"]
    try:
        command = shlex.split(spec["command"])
    except ValueError as exc:
        raise GateError(f"auditGate.blockingIssues.command: {exc}") from exc
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


def unresolved_ref(ref: str) -> str:
    """The error for an integration ref that names no commit."""
    return f"integrationRef {ref} does not resolve (no remote or no commits yet); fetch it or set integrationRef"


def resolves(repo: str, ref: str) -> bool:
    """Whether `ref` names a commit."""
    try:
        git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    except GateError:
        return False
    return True


def no_history_yet(repo: str, gate: dict) -> bool:
    """A fresh project: no remote, and the working branch (when it has a commit) holds no audit report and no merged
    spec. The gate then has nothing to count, so a missing integration ref cannot hide a due audit."""
    if git(repo, "remote").strip():
        return False
    if not resolves(repo, "HEAD"):
        return True
    listing = git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    return not any(matches(p, gate["auditReports"]) or matches(p, gate["mergedSpecMarker"]) for p in listing)


def compute(repo: str, gate: dict, ref: str, issues: list[dict] | None = None, unknown: str | None = None) -> dict:
    """The gate state on `ref`; `issues` are the open blocking issues (fetched when None), `unknown` the reason they
    could not be fetched. A ref that does not resolve is an error, except in a fresh project (`no_history_yet`),
    whose gate is open with nothing counted."""
    if not resolves(repo, ref):
        if not no_history_yet(repo, gate):
            raise GateError(unresolved_ref(ref))
        if issues is None:
            issues, unknown = blocking_issues(repo, gate)
        return {
            "ref": ref, "every": gate["every"], "specsSinceAudit": 0, "specs": [], "remediationSpecs": [],
            "blockingIssues": issues, "blockingIssuesUnknown": unknown, "issueTracker": has_tracker(gate),
            "auditsOnRef": 0, "lastAudit": None, "triage": None, "triagePending": 0,
            "blocked": bool(issues), "reasons": [f"{len(issues)} blocking audit issue(s) open"] if issues else [],
            "noHistory": f"{ref} does not resolve and the repository has no remote, audits or merged specs",
        }
    # A shallow clone's grafted root commit "adds" every file it holds, so audits and specs would be miscounted.
    if git(repo, "rev-parse", "--is-shallow-repository").strip() == "true":
        raise GateError("shallow clone: fetch full history (e.g. fetch-depth: 0)")
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
        "issueTracker": has_tracker(gate),
        "auditsOnRef": len(reports),
        "lastAudit": last,
        "triage": triage,
        "triagePending": pending,
        "blocked": bool(reasons),
        "reasons": reasons,
        "noHistory": None,
    }


def triage_section(text: str, heading: str) -> tuple[bool, int]:
    """Whether the report has the triage heading, and how many blocking themes of that section still carry
    `PENDING_ISSUE`. When the triage table has a `Blocks` column, only the rows whose Blocks cell starts with `yes`
    count (a non-blocking row needs no issue, as `triage_problems` says); without one, every line that carries the
    placeholder counts."""
    header, rows = triage_table(text, heading)
    if "blocks" in header:
        col = header.index("blocks")
        pending = sum(1 for cells in rows if col < len(cells) and cells[col].lower().startswith("yes")
                      and any(PENDING_ISSUE in cell for cell in cells))
        return any(line.strip() == heading for line in text.splitlines()), pending
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


def triage_problems(text: str, heading: str, open_numbers: set[int] | None, tracker: bool = True) -> list[str]:
    """One message per triage row that names no machine check, or blocks without an open blocking issue.
    `open_numbers` None means the blocking issues are unknown: a blocking row must then name some issue. Without an
    issue tracker (`tracker` False) the table is the record: a blocking row writes `-` in its Issue cell."""
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
        if blocks and not tracker:
            if cell("issue") != "-":
                problems.append(f"{theme}: blocks but its Issue cell is {cell('issue') or 'empty'}; without an issue "
                                "tracker write `-` (the triage table is the record)")
        elif blocks:
            issue = cell("issue")
            numbers = {int(n) for n in re.findall(r"#(\d+)", issue)}
            named = numbers if open_numbers is None else numbers & open_numbers
            if PENDING_ISSUE in issue or not named:
                which = "no issue" if open_numbers is None else "no open blocking issue"
                problems.append(f"{theme}: blocks but names {which} ({issue or 'empty'}); file one "
                                "with the blocking labels or relabel the single issue it continues")
    return problems


def issues_text(state: dict) -> str:
    """The blocking-issues part of the status line: the open count, `unknown` with its reason, or no tracker."""
    if state.get("blockingIssuesUnknown"):
        return f"unknown ({state['blockingIssuesUnknown']})"
    if state.get("issueTracker") is False:
        return "0 (no issue tracker)"
    return str(len(state["blockingIssues"]))


def status_line(state: dict) -> str:
    last = state["lastAudit"]
    where = f"{last['report']}, {last['date']}, {last['commit']}" if last else "no audit yet"
    if state.get("noHistory"):
        where = f"no history yet: {state['noHistory']}"
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
            problems = triage_problems(git(repo, "show", f"{head}:{report}"), gate["triageHeading"], open_numbers,
                                       state["issueTracker"])
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


def blocking_themes(repo: str, gate: dict, state: dict) -> list[str]:
    """The Theme cells of the blocking rows (Blocks starts with `yes`) of the last audit report's triage table."""
    last = state["lastAudit"]
    if not last:
        return []
    header, rows = triage_table(git(repo, "show", f"{state['ref']}:{last['report']}"), gate["triageHeading"])
    if "theme" not in header or "blocks" not in header:
        return []
    theme, blocks = header.index("theme"), header.index("blocks")
    return [cells[theme] for cells in rows
            if max(theme, blocks) < len(cells) and cells[blocks].lower().startswith("yes") and cells[theme]]


def theme_named(theme: str, wanted: str) -> bool:
    """Whether a Theme cell (`T1 copies`, `T1: copies`) is the theme id `wanted` (`T1`), ignoring case."""
    return re.match(re.escape(wanted) + r"(?![\w-])", theme, re.IGNORECASE) is not None


def theme_remediation(state: dict, remediation: str, themes: list[str]) -> tuple[list[str], list[str]]:
    """Without an issue tracker: the theme ids `--remediation` names, and the problems (an id that is no blocking
    theme of the last audit's triage table, or `#n` issue numbers)."""
    wanted = [part for part in re.split(r"[,\s]+", remediation.strip()) if part]
    problems = []
    if not wanted:
        problems.append("--remediation names no theme")
    if any(part.startswith("#") for part in wanted):
        problems.append("there is no issue tracker: name the blocking themes of the last audit's triage table "
                        "(e.g. --remediation T1,T3)")
    elif state["lastAudit"] is None:
        problems.append("there is no audit report, so no blocking theme to remediate")
    else:
        problems += [f"{part} is not a blocking theme (Blocks = yes) of {state['lastAudit']['report']}"
                     for part in wanted if not any(theme_named(theme, part) for theme in themes)]
    return wanted, problems


def start_line(state: dict, remediation: str | None, themes: list[str] | None = None) -> int:
    """Print the start line of a new spec and return 0, or print the reasons it may not start and return 1.
    `themes` are the blocking themes of the last audit (`blocking_themes`), read without an issue tracker."""
    report = state["lastAudit"]["report"] if state["lastAudit"] else "none"
    for note in unknown_note(state):
        print(f"audit-gate: {note}", file=sys.stderr)
    if remediation is not None and state.get("issueTracker") is False:
        wanted, problems = theme_remediation(state, remediation, themes or [])
        if state["triage"] is False:
            problems.insert(0, "the last audit is not triaged yet")
        if problems:
            print(status_line(state))
            for problem in problems:
                print(f"refused: {problem}")
            return 1
        print(f"Audit gate: remediation of {report} ({', '.join(wanted)})")
        return 0
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
    problems = triage_problems(text, gate["triageHeading"], open_numbers, has_tracker(gate))
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
    p_start.add_argument("--remediation", help='blocking issues this remediation spec fixes, e.g. "#3,#4"; without '
                         'an issue tracker, the blocking themes of the triage table, e.g. "T1,T3"')
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
            state = compute(repo, gate, ref)
            themes = (blocking_themes(repo, gate, state)
                      if args.remediation is not None and not has_tracker(gate) else None)
            return start_line(state, args.remediation, themes)

        passed, state, notes = check_pr(repo, gate, args.base, args.head)
        print(status_line(state))
        for note in notes:
            print(f"audit-gate: {note}")
        return 0 if passed else 1
    except quality_profile.MissingProfile:
        print(f"audit-gate: {quality_profile.MISSING}")
        return 0
    except (GateError, quality_profile.ProfileError, OSError) as exc:
        print(f"audit-gate: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
