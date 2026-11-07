#!/usr/bin/env python3
"""Ratchet baselines: a mechanical check the code base cannot pass yet may not get worse.

Each ratchet is a named metric (a shell command that prints one integer, last line of stdout) and a committed baseline.
The metric may not grow. When it drops, the lower value is committed with `update`, so progress is locked in and legacy
violations stay visible as a number, never as silence. Generic: names, commands and the baseline file live in the
project binding `.claude/quality-profile.json` (`ratchets`, `baselineFile`); this script knows no tool. A count
command may run any tool the project uses, e.g. a clone detector such as jscpd or a lint run counted by a filter.

Usage:
  python3 scripts/forge/ratchet.py check  [name ...] [--profile <path>]   # exit 1 on growth, a missing baseline or a failed command
  python3 scripts/forge/ratchet.py update [name ...] [--profile <path>]   # lower baselines; set missing ones; never raises one
  python3 scripts/forge/ratchet.py report [name ...] [--previous <audit report>] [--locations <n>] [--profile <path>]
      # the measurements of an audit's Structure section: a Markdown table with the count, the baseline, the count in
      # the previous audit's Structure section and the trend, then the top <n> locations of every ratchet with a
      # `locationsCommand`; exit 1 when a command fails
  python3 scripts/forge/ratchet.py copies [name ...] --files <path>... [--min-copies <n>] [--added-since <rev>] [--fail]
      # third-copy trigger: the copy groups (`groupsCommand` of the clone ratchets) with at least <n> copies
      # (default 2) that have a copy in one of the given files. --added-since keeps only the groups whose copy in a
      # given file overlaps lines added since <rev> (the diff, untracked files whole). --fail exits 1 when any group
      # is listed. A plan runs it on its File Impact files; `/review` and task reviews run it on the diff. The files
      # are relative to the source root (`SOURCE_ROOT`; a `<SOURCE_ROOT>/` prefix is accepted) and the added lines are
      # read with git there; a file in neither the source repository nor its working tree exits 2

Output, one line per ratchet: `<name>=<count> (baseline <n>, delta <d>)` plus `ok`, `LOWER` (commit the new baseline with
`update`) or `GREW`. Raising a baseline is a reviewed edit of the baseline file, never an `update`.
When `ratchets` is unset (`[]` or absent), every mode prints one line saying so and exits 0 (the manual form).
Exit codes: 0 all ratchets hold, or `ratchets` unset; 1 a ratchet failed; 2 the profile (invalid) or the
baseline file is unusable. A missing binding file counts as every key unset: one line (`no .claude/quality-profile.json; run python3
scripts/forge/quality_profile.py init`) and exit 0.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)

COMMAND_TIMEOUT_SECONDS = 600
# The audit report section whose measurements table `report` writes and reads back as the previous audit's counts.
STRUCTURE_HEADING = "## Structure"
TABLE_HEADER = "| Ratchet | Count | Baseline | Previous audit | Trend |"
DEFAULT_LOCATIONS = 20


class RatchetError(Exception):
    """The profile, the baseline file or a ratchet definition is unusable."""


def repo_of(profile_path: str) -> str:
    """The repository root is the parent of the directory that holds the profile (`.claude/`)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(profile_path)))


def load_ratchets(profile: dict) -> tuple[list[dict], str]:
    """Return the ratchet definitions and the baseline file path (relative to the repo)."""
    ratchets = profile.get("ratchets")
    baseline_file = profile.get("baselineFile")
    if not isinstance(ratchets, list) or not ratchets:
        raise RatchetError("profile has no ratchets")
    if not isinstance(baseline_file, str):
        raise RatchetError("profile has no baselineFile")
    return ratchets, baseline_file


# The one line every mode prints when `ratchets` is unset: no ratchet runs, and the measurements are made by hand.
UNSET = "ratchet: ratchets is unset in the quality profile; no ratchet runs (the manual form: measure by hand)"


def configured_ratchets(profile_path: str) -> tuple[list[dict], str] | None:
    """Load and validate the binding; return the ratchets and the baseline file, or None when `ratchets` is unset.
    Raise RatchetError when the binding is invalid."""
    profile = quality_profile.load(profile_path)
    problems = quality_profile.validate(profile, repo=repo_of(profile_path))
    if problems:
        raise RatchetError("quality profile: " + "; ".join(problems))
    if quality_profile.is_unset("ratchets", profile.get("ratchets", [])):
        return None
    return load_ratchets(profile)


def read_baselines(path: str) -> dict[str, int]:
    """Read `{ "baselines": { name: int } }`; a missing file is an empty baseline set."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise RatchetError(f"baseline file is not valid JSON: {path}: {exc}") from exc
    values = data.get("baselines") if isinstance(data, dict) else None
    if not isinstance(values, dict) or not all(isinstance(v, int) and not isinstance(v, bool) for v in values.values()):
        raise RatchetError(f"baseline file must be an object with a 'baselines' map of integers: {path}")
    return dict(values)


def write_baselines(path: str, baselines: dict[str, int]) -> None:
    """Write the baselines sorted by name so a diff shows only real changes."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"baselines": dict(sorted(baselines.items()))}, handle, indent=2)
        handle.write("\n")


def measure(command: str, repo: str) -> int:
    """Run a count command from the repo root and parse the last non-empty stdout line as an integer."""
    result = subprocess.run(
        command, shell=True, cwd=repo, capture_output=True, text=True, timeout=COMMAND_TIMEOUT_SECONDS, check=False
    )
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        raise RatchetError(f"count command failed (exit {result.returncode}): {command}: {' | '.join(tail)}")
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    try:
        return int(lines[-1])
    except (IndexError, ValueError) as exc:
        raise RatchetError(f"count command did not print an integer: {command}") from exc


def list_locations(command: str, repo: str) -> list[str]:
    """Run a locations command from the repo root; return its non-empty stdout lines (largest first, as printed)."""
    result = subprocess.run(
        command, shell=True, cwd=repo, capture_output=True, text=True, timeout=COMMAND_TIMEOUT_SECONDS, check=False
    )
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        raise RatchetError(f"locations command failed (exit {result.returncode}): {command}: {' | '.join(tail)}")
    return [line.rstrip() for line in result.stdout.splitlines() if line.strip()]


def previous_counts(report_text: str) -> dict[str, int]:
    """The counts of the measurements table in a report's Structure section; empty when the report has none."""
    counts: dict[str, int] = {}
    inside = in_table = False
    for line in report_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            inside = stripped == STRUCTURE_HEADING
            in_table = False
            continue
        if not inside:
            continue
        if not stripped.startswith("|"):
            in_table = False
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and cells[0] == "Ratchet":
            in_table = True
        elif in_table and len(cells) >= 2 and cells[1].isdigit():
            counts[cells[0].strip("`")] = int(cells[1])
    return counts


def trend(count: int, previous: int | None) -> str:
    """The trend of one count against the previous audit: first measurement, unchanged, fixed, grown, shrinking."""
    if previous is None:
        return "first measurement"
    if count == previous:
        return "unchanged"
    if count == 0:
        return f"fixed (-{previous})"
    return f"grown (+{count - previous})" if count > previous else f"shrinking ({count - previous})"


def report(names: list[str], profile_path: str, previous_path: str | None, top: int) -> int:
    """Print the Structure measurements of an audit; return the process exit code."""
    try:
        loaded = configured_ratchets(profile_path)
        if loaded is None:
            print(UNSET)
            return 0
        ratchets, baseline_file = loaded
        repo = repo_of(profile_path)
        baselines = read_baselines(os.path.join(repo, baseline_file))
        previous: dict[str, int] = {}
        if previous_path:
            with open(previous_path, encoding="utf-8") as handle:
                previous = previous_counts(handle.read())
    except quality_profile.MissingProfile:
        print(f"ratchet: {quality_profile.MISSING}")
        return 0
    except (quality_profile.ProfileError, RatchetError, OSError) as exc:
        print(f"ratchet: {exc}", file=sys.stderr)
        return 2
    unknown = [name for name in names if name not in {entry["name"] for entry in ratchets}]
    if unknown:
        print(f"ratchet: unknown ratchet: {', '.join(unknown)}", file=sys.stderr)
        return 2

    failed = False
    rows: list[str] = [TABLE_HEADER, "|---|---:|---:|---:|---|"]
    sections: list[str] = []
    for entry in ratchets:
        name = entry["name"]
        if names and name not in names:
            continue
        baseline = baselines.get(name)
        before = previous.get(name)
        try:
            count = measure(entry["countCommand"], repo)
        except (RatchetError, subprocess.TimeoutExpired) as exc:
            rows.append(f"| {name} | ERROR | {baseline if baseline is not None else '-'} | "
                        f"{before if before is not None else '-'} | {exc} |")
            failed = True
            continue
        rows.append(f"| {name} | {count} | {baseline if baseline is not None else '-'} | "
                    f"{before if before is not None else '-'} | {trend(count, before)} |")
        command = entry.get("locationsCommand")
        if not command:
            continue
        try:
            locations = list_locations(command, repo)
        except (RatchetError, subprocess.TimeoutExpired) as exc:
            sections.append(f"Locations of {name}: ERROR {exc}")
            failed = True
            continue
        shown = locations[:top]
        sections.append("\n".join([f"Locations of {name} (top {len(shown)} of {len(locations)}):",
                                    *(f"- {line}" for line in shown)]))
    print("\n\n".join(["\n".join(rows), *sections]))
    return 1 if failed else 0


def run(mode: str, names: list[str], profile_path: str) -> int:
    """Check or update the selected ratchets (all when `names` is empty); return the process exit code."""
    try:
        loaded = configured_ratchets(profile_path)
        if loaded is None:
            print(UNSET)
            return 0
        ratchets, baseline_file = loaded
        repo = repo_of(profile_path)
        baseline_path = os.path.join(repo, baseline_file)
        baselines = read_baselines(baseline_path)
    except quality_profile.MissingProfile:
        print(f"ratchet: {quality_profile.MISSING}")
        return 0
    except (quality_profile.ProfileError, RatchetError) as exc:
        print(f"ratchet: {exc}", file=sys.stderr)
        return 2

    known = {entry["name"] for entry in ratchets}
    unknown = [name for name in names if name not in known]
    if unknown:
        print(f"ratchet: unknown ratchet: {', '.join(unknown)}", file=sys.stderr)
        return 2

    failed = False
    changed = False
    for entry in ratchets:
        name = entry["name"]
        if names and name not in names:
            continue
        try:
            count = measure(entry["countCommand"], repo)
        except (RatchetError, subprocess.TimeoutExpired) as exc:
            print(f"{name}=ERROR {exc}")
            failed = True
            continue
        baseline = baselines.get(name)
        if baseline is None:
            if mode == "update":
                baselines[name] = count
                changed = True
                print(f"{name}={count} (baseline set)")
            else:
                print(f"{name}={count} (no baseline) MISSING: run `python3 scripts/forge/ratchet.py update {name}`")
                failed = True
            continue
        delta = count - baseline
        if delta > 0:
            print(f"{name}={count} (baseline {baseline}, delta +{delta}) GREW")
            failed = True
        elif delta < 0:
            if mode == "update":
                baselines[name] = count
                changed = True
                print(f"{name}={count} (baseline {baseline} -> {count}) LOWERED")
            else:
                print(f"{name}={count} (baseline {baseline}, delta {delta}) LOWER: commit it with `python3 scripts/forge/ratchet.py update {name}`")
        else:
            print(f"{name}={count} (baseline {baseline}, delta 0) ok")

    # The file records exactly what was printed: every LOWERED and `baseline set` entry is written even when another
    # ratchet grew or failed (that one keeps its baseline, so nothing is ever raised).
    if mode == "update" and changed:
        write_baselines(baseline_path, baselines)
    return 1 if failed else 0


def added_lines(source: str, rev: str, path: str) -> set[int]:
    """Line numbers of `path` (relative to the source root `source`) added since `rev`, read with git in the source
    root: an untracked file has every line added, a file deleted since `rev` none. Raise RatchetError when the diff
    fails or the path is neither in the source repository nor in its working tree."""
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", source, "-c", "core.quotepath=off", *args],
                              capture_output=True, text=True, check=False)

    full = os.path.join(source, path)
    tracked = git("ls-files", "--error-unmatch", "--", path).returncode == 0
    if not tracked:
        if os.path.isfile(full):
            with open(full, encoding="utf-8", errors="replace") as handle:
                return set(range(1, sum(1 for _ in handle) + 1))
        if git("cat-file", "-e", f"{rev}:{path}").returncode == 0:
            return set()
        raise RatchetError(f"{path}: not in the source repository {source} at {rev} nor in its working tree")
    diff = git("diff", "-U0", "--no-color", "--no-ext-diff", rev, "--", path)
    if diff.returncode != 0:
        raise RatchetError(f"git diff {rev} -- {path} failed in {source}: {diff.stderr.strip()}")
    added: set[int] = set()
    for line in diff.stdout.splitlines():
        if line.startswith("@@"):
            new_part = line.split("+", 1)[1].split(" ", 1)[0]
            start, _, count = new_part.partition(",")
            added.update(range(int(start), int(start) + (int(count) if count else 1)))
    return added


def parse_group(line: str) -> tuple[int, int, list[tuple[str, int, int]]] | None:
    """`<copies> <lines> <file>:<start>-<end> ...` as (copies, lines, regions); None for a line of another shape."""
    parts = line.split()
    if len(parts) < 3 or not parts[0].isdigit() or not parts[1].isdigit():
        return None
    regions = []
    for token in parts[2:]:
        name, _, span = token.rpartition(":")
        first, _, last = span.partition("-")
        if not name or not first.isdigit() or not last.isdigit():
            return None
        regions.append((name, int(first), int(last)))
    return int(parts[0]), int(parts[1]), regions


def copies(names: list[str], profile_path: str, files: list[str], minimum: int, since: str | None,
           fail: bool) -> int:
    """List the copy groups with at least `minimum` copies that have a copy in one of `files` (see the usage)."""
    try:
        loaded = configured_ratchets(profile_path)
        if loaded is None:
            print(UNSET)
            return 0
        ratchets, _ = loaded
    except quality_profile.MissingProfile:
        print(f"ratchet: {quality_profile.MISSING}")
        return 0
    except (quality_profile.ProfileError, RatchetError) as exc:
        print(f"ratchet: {exc}", file=sys.stderr)
        return 2
    repo = repo_of(profile_path)
    try:
        source = quality_profile.source_root(repo)
        # The given files are relative to the source root (a `<SOURCE_ROOT>/` prefix is accepted).
        wanted = [quality_profile.source_path(os.path.normpath(f), repo) for f in files]
    except quality_profile.ProfileError as exc:
        print(f"ratchet: {exc}", file=sys.stderr)
        return 2
    selected = [e for e in ratchets if e.get("groupsCommand") and (not names or e["name"] in names)]
    if not selected:
        print("ratchet: no ratchet with a groupsCommand selected", file=sys.stderr)
        return 2
    added_cache: dict[str, set[int]] = {}
    listed = 0
    for entry in selected:
        try:
            lines = list_locations(entry["groupsCommand"], repo)
        except (RatchetError, subprocess.TimeoutExpired) as exc:
            print(f"{entry['name']}=ERROR {exc}")
            return 1
        for line in lines:
            group = parse_group(line)
            if group is None or group[0] < minimum:
                continue
            hits = [(path, first, last) for name, first, last in group[2]
                    for path in wanted if path == name or path.endswith("/" + name) or name.endswith("/" + path)]
            if not hits:
                continue
            marker = ""
            if since:
                fresh = False
                for path, first, last in hits:
                    if path not in added_cache:
                        try:
                            added_cache[path] = added_lines(source, since, path)
                        except RatchetError as exc:
                            print(f"ratchet: {exc}", file=sys.stderr)
                            return 2
                    known = added_cache[path]
                    fresh = fresh or any(first <= n <= last for n in known)
                if not fresh:
                    continue
                marker = " added"
            listed += 1
            print(f"{entry['name']} copies={group[0]} lines={group[1]}{marker} "
                  + " ".join(f"{n}:{a}-{b}" for n, a, b in group[2]))
    scope = f"; lines added since {since}" if since else ""
    print(f"copies: {listed} group(s) with >= {minimum} copies in the {len(wanted)} given file(s){scope}")
    return 1 if fail and listed else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["check", "update", "report", "copies"])
    parser.add_argument("names", nargs="*", help="ratchet names (default: all)")
    parser.add_argument("--profile", default=quality_profile.DEFAULT_PROFILE)
    parser.add_argument("--previous", help="report: the previous audit report, whose Structure section holds the counts")
    parser.add_argument("--locations", type=int, default=DEFAULT_LOCATIONS, help="report: locations shown per ratchet")
    parser.add_argument("--files", nargs="+", default=[], help="copies: the files a plan or a diff touches")
    parser.add_argument("--min-copies", type=int, default=2, help="copies: the smallest group listed (default 2)")
    parser.add_argument("--added-since", help="copies: keep the groups whose copy in a given file has lines added since this revision")
    parser.add_argument("--fail", action="store_true", help="copies: exit 1 when any group is listed")
    args = parser.parse_args(argv)
    if args.mode == "copies":
        if not args.files:
            parser.error("copies needs --files")
        return copies(args.names, args.profile, args.files, max(args.min_copies, 2), args.added_since, args.fail)
    if args.files or args.added_since or args.fail:
        parser.error("--files, --added-since and --fail are valid only with copies")
    if args.mode == "report":
        return report(args.names, args.profile, args.previous, max(args.locations, 0))
    if args.previous:
        parser.error("--previous is valid only with report")
    return run(args.mode, args.names, args.profile)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
