#!/usr/bin/env python3
"""Enforcement map check: every rule names the mechanism that enforces it, and that mechanism exists.

The map is a markdown table under a heading of the rules document (`enforcementMap` in `.claude/quality-profile.json`):
`| Rule | Enforcement | Notes |`. The Enforcement cell holds one or more tags, each in backticks:
  `lint:<rule id>`      the id appears in one of the lint configuration files (`lintConfigs`)
  `test:<path>`         the file exists (a glob is allowed)
  `gate:<text>`         the text appears in one of the gate files (`gateFiles`): a checklist item, a harness rule
  `ratchet:<name>`      the name is one of the profile's `ratchets` (a rule with legacy violations, counted down by
                        `scripts/forge/ratchet.py`)
  `review-only`         no machine check; must stand alone. An audit proposes a check for a review-only rule that is
                        violated in two audits in a row.
Every rule id the rules document declares (`rulePattern`, one capture group, matched per line) must have a row. The
rules document is `rulesDoc` when the map lives in a document of its own, else the map's own `doc`.

Example binding (the values are the project's own):
  "enforcementMap": {"doc": "docs/enforcement-map.md", "heading": "## Enforcement Map", "rulesDoc": "constitution.md",
                     "rulePattern": "^\\*\\*(R-\\d+)\\.", "lintConfigs": ["<the lint configuration files>"],
                     "gateFiles": [".claude/checklists/*.md", ".claude/commands/review.md"]}
When `enforcementMap` is unset (absent or `{}`) there is no map: the check prints one line saying so and exits 0.

Usage: python3 scripts/forge/check-enforcement-map.py [--profile <path>]
Exit codes: 0 the map holds, or `enforcementMap` is unset; 1 problems (one line each); 2 the profile (invalid by
`quality_profile.validate`) or the document is unusable. A missing binding file counts as every key unset: one line (`no .claude/quality-profile.json; run python3
scripts/forge/quality_profile.py init`) and exit 0.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)

TAG = re.compile(r"`([^`]+)`")
KINDS = ("lint", "test", "gate", "ratchet")


def parse_map(lines: list[str], heading: str) -> list[tuple[str, list[str]]]:
    """Return `(rule id, tags)` for each row of the first table under `heading`.

    Raises ValueError when the heading is missing or no table follows it.
    """
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration as exc:
        raise ValueError(f"heading not found: {heading}") from exc
    rows: list[tuple[str, list[str]]] = []
    in_table = False
    for line in lines[start + 1 :]:
        text = line.strip()
        if text.startswith("#") and not in_table:
            break
        if not text.startswith("|"):
            if in_table:
                break
            continue
        in_table = True
        cells = [cell.strip() for cell in text.strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: ") or cells[0].lower() == "rule":
            continue  # separator and header rows
        rows.append((cells[0].strip("` "), TAG.findall(cells[1])))
    if not rows:
        raise ValueError(f"no table rows under: {heading}")
    return rows


def read_all(repo: str, patterns: list[str]) -> str:
    """Concatenate the text of every file matching the glob patterns."""
    chunks: list[str] = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(repo, pattern), recursive=True)):
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as handle:
                    chunks.append(handle.read())
    return "\n".join(chunks)


def check(rows: list[tuple[str, list[str]]], declared: set[str], repo: str, lint_text: str, gate_text: str,
          ratchets: set[str]) -> list[str]:
    """Return one message per problem in the map."""
    problems: list[str] = []
    seen: set[str] = set()
    for rule, tags in rows:
        if rule in seen:
            problems.append(f"{rule}: listed twice")
        seen.add(rule)
        if not tags:
            problems.append(f"{rule}: no enforcement tag")
            continue
        if "review-only" in tags and len(tags) > 1:
            problems.append(f"{rule}: review-only cannot be combined with other tags")
        for tag in tags:
            if tag == "review-only":
                continue
            kind, _, value = tag.partition(":")
            if kind not in KINDS or not value:
                problems.append(f"{rule}: unknown tag `{tag}` (use lint:, test:, gate:, ratchet: or review-only)")
            elif kind == "lint":
                if not re.search(rf"(?<![\w/-]){re.escape(value)}(?![\w/-])", lint_text):
                    problems.append(f"{rule}: lint rule `{value}` is not configured in any lint config")
            elif kind == "test":
                if not glob.glob(os.path.join(repo, value), recursive=True):
                    problems.append(f"{rule}: test file `{value}` does not exist")
            elif kind == "ratchet":
                if value not in ratchets:
                    problems.append(f"{rule}: ratchet `{value}` is not defined in the profile")
            elif value not in gate_text:
                problems.append(f"{rule}: gate text `{value}` is not in any gate file")
    for rule in sorted(declared - seen):
        problems.append(f"{rule}: declared in the rules document but missing from the enforcement map")
    return problems


def run(profile_path: str) -> int:
    """Check the map named by the profile; return the process exit code."""
    try:
        profile = quality_profile.load(profile_path)
        repo = os.path.dirname(os.path.dirname(os.path.abspath(profile_path)))
        problems = quality_profile.validate(profile, repo=repo)
        if problems:
            raise quality_profile.ProfileError("quality profile: " + "; ".join(problems))
        section = profile.get("enforcementMap")
        if section is None or quality_profile.is_unset("enforcementMap", section):
            print("enforcement-map: enforcementMap is unset in the binding; no map to check")
            return 0
        with open(os.path.join(repo, section["doc"]), encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        rows = parse_map(lines, section["heading"])
        pattern = re.compile(section["rulePattern"])
        if section.get("rulesDoc"):
            with open(os.path.join(repo, section["rulesDoc"]), encoding="utf-8") as handle:
                lines = handle.read().splitlines()
    except quality_profile.MissingProfile:
        print(f"enforcement-map: {quality_profile.MISSING}")
        return 0
    except (quality_profile.ProfileError, OSError, ValueError, KeyError, re.error) as exc:
        print(f"enforcement-map: {exc}", file=sys.stderr)
        return 2

    declared = {m.group(1) for line in lines for m in [pattern.search(line)] if m}
    problems = check(
        rows, declared, repo, read_all(repo, section["lintConfigs"]), read_all(repo, section["gateFiles"]),
        {r.get("name") for r in profile.get("ratchets") or [] if isinstance(r, dict)},
    )
    for problem in problems:
        print(f"enforcement-map: {problem}")
    if problems:
        return 1
    machine = sum(1 for _, tags in rows if tags != ["review-only"])
    print(f"enforcement-map: ok ({len(rows)} rules, {machine} machine-checked, {len(rows) - machine} review-only)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", default=quality_profile.DEFAULT_PROFILE)
    return run(parser.parse_args(argv).profile)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
