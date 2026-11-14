#!/usr/bin/env python3
"""Decision records check: a frozen history log plus one fragment file per unit of work.

Every unit of work (a feature spec, a fix, a chore) records its autonomous decisions in its own fragment file, so
parallel branches never append to the same lines of one shared log. The binding `decisionRecords` in
`.claude/quality-profile.json` names:
  log           the frozen history log: a markdown table (`| Date | ... |`) that no branch appends to any more
  frozenOn      the freeze date (YYYY-MM-DD): rows dated on or before it may still land in the log (branches opened
                before the freeze); a row dated later, or without a date, fails the check
  fragments     the directory of fragment files, one per unit of work
  fragmentName  a regular expression every fragment's base name (without `.md`) must match
The integration ref is the binding's `integrationRef` (or `--base`).

Example binding (the values are the project's own; units here are `specs/<KEY|NNN>-name/` directories and fixes):
  "decisionRecords": {"log": "docs/decision-log.md", "frozenOn": "2026-01-31", "fragments": "docs/decisions",
                      "fragmentName": "^(\\d{3}-[a-z0-9-]+|[A-Z][A-Z0-9]+-\\d+-[a-z0-9-]+|fix-[a-z0-9-]+)$"}

The check fails when
  - the working tree adds a table row to the log, relative to the merge base of HEAD with the integration ref, and
    the row is dated after `frozenOn` (or carries no date);
  - a fragment's name does not match `fragmentName`;
  - a fragment has no table whose header row equals the log's header row, a row has fewer cells than the header, a
    row's first cell is not a valid date, or the fragment has no row.

Lookup: `--list` prints every row of the log and of the fragments, sorted by date (stable: log order first, then
fragment name), as `<source> | <row>`; `--grep <regex>` keeps the rows that match (case-insensitive). The lookup does
not run the check.

When `decisionRecords` is unset (absent or `{}`) there are no records: the check and the lookup print one line saying
so and exit 0. When `integrationRef` is unset and no `--base` is given, the log-freeze check has no range and is
skipped (the summary line says so); the fragments are still checked.

Usage: python3 scripts/forge/check-decision-records.py [--profile <path>] [--base <ref>] [--list [--grep <regex>]]
Exit codes: 0 the records hold, or `decisionRecords` is unset (lookup: printed, possibly nothing); 1 problems (one line
each); 2 the profile, the log or the base ref is unusable, or the regex is invalid.
A missing binding file counts as every key unset: one line (`no .claude/quality-profile.json; run python3
scripts/forge/quality_profile.py init`) and exit 0.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)

PREFIX = "decision-records"


def cells(line: str) -> list[str]:
    """Return the cells of a markdown table line."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator(line: str) -> bool:
    """Whether a table line is the header separator (`|---|:--|`)."""
    return set(line.strip()) <= set("|-: ") and "-" in line


def is_date(text: str) -> bool:
    """Whether the text is one ISO date (YYYY-MM-DD)."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return False
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def header_of(text: str) -> list[str] | None:
    """Return the header cells of the first table in a markdown text, or None when it has no table."""
    lines = text.splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.strip().startswith("|") and is_separator(lines[index + 1]):
            return cells(line)
    return None


def table_rows(text: str, header: list[str]) -> tuple[bool, list[str]]:
    """Return `(header found, data row lines)` of the first table whose header equals `header` (case-insensitive)."""
    wanted = [c.lower() for c in header]
    lines = text.splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.strip().startswith("|") and [c.lower() for c in cells(line)] == wanted and is_separator(lines[index + 1]):
            rows: list[str] = []
            for row in lines[index + 2 :]:
                if not row.strip().startswith("|"):
                    break
                rows.append(row.strip())
            return True, rows
    return False, []


def check_fragment(name: str, text: str, header: list[str], pattern: re.Pattern[str]) -> list[str]:
    """Return one message per problem of one fragment file."""
    problems: list[str] = []
    stem = name[:-3] if name.endswith(".md") else name
    if not name.endswith(".md") or not pattern.fullmatch(stem):
        problems.append(f"{name}: name does not match the fragment pattern {pattern.pattern}")
    found, rows = table_rows(text, header)
    if not found:
        problems.append(f"{name}: no table with the log's header `| {' | '.join(header)} |`")
        return problems
    if not rows:
        problems.append(f"{name}: the table has no row")
    for number, row in enumerate(rows, start=1):
        row_cells = cells(row)
        if len(row_cells) < len(header):
            problems.append(f"{name}: row {number} has {len(row_cells)} cells, the header {len(header)}")
        if not is_date(row_cells[0]):
            problems.append(f"{name}: row {number} does not start with a date (YYYY-MM-DD): {row_cells[0][:40]!r}")
    return problems


def added_rows(repo: str, base: str, log: str) -> list[str]:
    """Return the table rows the working tree adds to the log since the merge base of HEAD with `base`.

    Raises ValueError when the base ref or the merge base cannot be resolved.
    """
    def git(*args: str) -> str:
        result = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
        if result.returncode != 0:
            raise ValueError(f"git {' '.join(args)}: {result.stderr.strip() or result.returncode}")
        return result.stdout

    merge_base = git("merge-base", base, "HEAD").strip()
    diff = git("diff", "--no-renames", "--unified=0", merge_base, "--", log)
    return [line[1:].strip() for line in diff.splitlines()
            if line.startswith("+") and not line.startswith("+++") and line[1:].strip().startswith("|")]


def check_log_rows(rows: list[str], header: list[str], frozen_on: str) -> list[str]:
    """Return one message per added log row that the freeze does not allow."""
    problems: list[str] = []
    wanted = [c.lower() for c in header]
    for row in rows:
        first = cells(row)[0]
        if is_separator(row) or [c.lower() for c in cells(row)] == wanted:
            continue
        if not is_date(first) or first > frozen_on:
            problems.append(f"log: a row was added after the freeze ({frozen_on}); move it to the unit's fragment: "
                            f"{row[:100]}")
    return problems


def fragment_files(repo: str, directory: str) -> list[str]:
    """Return the fragment file names in the fragments directory, sorted (none when the directory does not exist):
    the `*.md` files, without dotfiles (`.DS_Store`, `.gitkeep`) and without a `README.md` that explains the
    directory."""
    path = os.path.join(repo, directory)
    if not os.path.isdir(path):
        return []
    return sorted(name for name in os.listdir(path)
                  if name.endswith(".md") and not name.startswith(".") and name.lower() != "readme.md"
                  and os.path.isfile(os.path.join(path, name)))


def read(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def lookup(repo: str, section: dict, header: list[str], log_text: str, grep: str | None) -> int:
    """Print every decision row of the log and the fragments, sorted by date; return the exit code."""
    try:
        matcher = re.compile(grep, re.IGNORECASE) if grep else None
    except re.error as exc:
        print(f"{PREFIX}: invalid regex: {exc}", file=sys.stderr)
        return 2
    entries: list[tuple[str, int, str, str]] = []
    sources = [(section["log"], log_text)] + [
        (f"{section['fragments']}/{name}", read(os.path.join(repo, section["fragments"], name)))
        for name in fragment_files(repo, section["fragments"])
    ]
    for order, (source, text) in enumerate(sources):
        for row in table_rows(text, header)[1]:
            first = cells(row)[0]
            if matcher is None or matcher.search(row):
                entries.append((first if is_date(first) else "", order, source, row))
    for _, _, source, row in sorted(entries, key=lambda e: (e[0], e[1])):
        print(f"{source} | {row}")
    return 0


def run(profile_path: str, base: str | None, list_rows: bool, grep: str | None) -> int:
    """Check the decision records named by the profile, or print them; return the process exit code."""
    try:
        profile = quality_profile.load_valid(profile_path)
        section = profile.get("decisionRecords")
        if section is None or quality_profile.is_unset("decisionRecords", section):
            print(f"{PREFIX}: decisionRecords is unset in the binding; no decision records to check or list")
            return 0
        repo = os.path.dirname(os.path.dirname(os.path.abspath(profile_path)))
        log_text = read(os.path.join(repo, section["log"]))
        header = header_of(log_text)
        if header is None:
            raise ValueError(f"{section['log']}: no table")
        pattern = re.compile(section["fragmentName"])
        frozen_on = section["frozenOn"]
        if not is_date(frozen_on):
            raise ValueError(f"frozenOn: not a date: {frozen_on}")
    except quality_profile.MissingProfile:
        print(f"{PREFIX}: {quality_profile.MISSING}")
        return 0
    except (quality_profile.ProfileError, OSError, ValueError, KeyError, re.error) as exc:
        print(f"{PREFIX}: {exc}", file=sys.stderr)
        return 2

    if list_rows:
        return lookup(repo, section, header, log_text, grep)

    ref = base or profile.get("integrationRef")
    rows: list[str] = []
    if ref:
        try:
            if not isinstance(ref, str):
                raise ValueError("integrationRef: expected a string")
            rows = added_rows(repo, ref, section["log"])
        except ValueError as exc:
            print(f"{PREFIX}: base unusable: {exc}", file=sys.stderr)
            return 2
    problems = check_log_rows(rows, header, frozen_on)
    names = fragment_files(repo, section["fragments"])
    for name in names:
        problems.extend(check_fragment(name, read(os.path.join(repo, section["fragments"], name)), header, pattern))
    for problem in problems:
        print(f"{PREFIX}: {problem}")
    if problems:
        return 1
    added = (f"{len(rows)} row(s) added since {ref} within the grace" if ref
             else "log rows not checked: integrationRef unset and no --base")
    print(f"{PREFIX}: ok (log frozen on {frozen_on}, {added}, {len(names)} fragment(s))")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", default=quality_profile.DEFAULT_PROFILE)
    parser.add_argument("--base", help="the ref to diff against (default: the binding's integrationRef)")
    parser.add_argument("--list", action="store_true", help="print every decision row sorted by date")
    parser.add_argument("--grep", help="with --list: keep the rows matching this regular expression")
    args = parser.parse_args(argv)
    return run(args.profile, args.base, args.list, args.grep)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
