#!/usr/bin/env python3
"""Canonical sources registry check: every registry row cites evidence that exists.

The registry is a markdown table under a heading of a document (`canonicalSources` in `.claude/quality-profile.json`).
One row per concept that must have a single definition. Required columns (matched by header text, case-insensitive):
  Concept             the concept, in the project's own terms
  Kind                one of KINDS below
  Single definition   repository paths and symbols in backticks, or a cell starting with "none" when the concept has
                      no single definition yet
  Status              single, or the copies and the tracking item (an issue, a planned item); required for a "none" row
Optional columns the check reads when present:
  Actor / axis of change   required for a `variation point` row: the evidence that the axis is confirmed
Every backticked token that looks like a repository path (contains `/`; a trailing `:<line>[-<line>]` or `#<anchor>` is
ignored) must exist, anywhere in the row; an anchor on a markdown path must match one of its headings. Every other
backticked token in the Single definition cell is a symbol and must occur in at least one of the paths of that cell,
so a rename or a moved definition fails the check. Each row must cite at least one existing path.

Example binding: `"canonicalSources": {"doc": "docs/architecture.md", "heading": "## Canonical sources"}`.

Lookup: per-task agents consult the registry by concept instead of reading the whole document.
`--concepts` prints one line per row (`<concept> | <kind>`); `--rows <regex>` prints, in full, the rows whose concept
matches the regular expression (case-insensitive). Both resolve the registry through the binding, so the agent does
not read the binding itself, and neither runs the check.

When `canonicalSources` is unset (absent or `{}`) there is no registry: the check and both lookups print one line
saying so and exit 0.

Usage: python3 scripts/forge/check-canonical-sources.py [--profile <path>] [--concepts | --rows <regex>]
Exit codes: 0 the registry holds, or `canonicalSources` is unset (lookup: printed, possibly nothing); 1 problems (one
line each); 2 the profile or the document is unusable, or the regex is invalid.
A missing binding file counts as every key unset: one line (`no .claude/quality-profile.json; run python3
scripts/forge/quality_profile.py init`) and exit 0.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)

# The kinds of concept the registry holds. Generic vocabulary, the same on every project.
KINDS = ("derived figure", "business rule", "shared helper", "closed set", "cross-cutting seam", "variation point")
TOKEN = re.compile(r"`([^`]+)`")
PATH = re.compile(r"^[\w.@-]+(?:/[\w.@\[\]-]+)+/?$")
SUFFIX = re.compile(r"(?::\d+(?:-\d+)?|#[\w-]+)$")


def parse_table(lines: list[str], heading: str) -> tuple[list[str], list[list[str]]]:
    """Return `(header cells, data rows)` of the first table under `heading`.

    Raises ValueError when the heading is missing or no table follows it.
    """
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration as exc:
        raise ValueError(f"heading not found: {heading}") from exc
    table: list[list[str]] = []
    for line in lines[start + 1 :]:
        text = line.strip()
        if text.startswith("#") and not table:
            break
        if not text.startswith("|"):
            if table:
                break
            continue
        table.append([cell.strip() for cell in text.strip("|").split("|")])
    if len(table) < 2:
        raise ValueError(f"no registry table under: {heading}")
    header, rows = table[0], [row for row in table[1:] if not set("".join(row)) <= set("-: ")]
    return header, rows


def slug(heading: str) -> str:
    """Return the anchor a markdown renderer gives a heading (lowercase, punctuation dropped, spaces to hyphens)."""
    text = re.sub(r"[^\w\s-]", "", heading.strip().lower())
    return re.sub(r"\s", "-", text)


def anchors(path: str) -> set[str]:
    """Return the heading anchors of a markdown file."""
    with open(path, encoding="utf-8") as handle:
        return {slug(m.group(1)) for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", handle.read(), re.MULTILINE)}


def path_of(token: str) -> str | None:
    """Return the repository path a backticked token names, or None when it is a symbol."""
    candidate = SUFFIX.sub("", token.strip())
    return candidate if PATH.match(candidate) else None


def check(header: list[str], rows: list[list[str]], repo: str) -> list[str]:
    """Return one message per problem in the registry."""
    columns = {name.lower(): index for index, name in enumerate(header)}
    problems: list[str] = []
    for required in ("concept", "kind", "single definition", "status"):
        if required not in columns:
            problems.append(f"missing column: {required}")
    if problems:
        return problems
    axis = next((i for name, i in columns.items() if name.startswith("actor")), None)
    seen: set[str] = set()
    for row in rows:
        cell = lambda index: row[index] if index is not None and index < len(row) else ""  # noqa: E731
        concept = cell(columns["concept"]) or "<empty concept>"
        if concept in seen:
            problems.append(f"{concept}: listed twice")
        seen.add(concept)
        kind = cell(columns["kind"]).strip("` ").lower()
        if kind not in KINDS:
            problems.append(f"{concept}: unknown kind `{kind}` (use one of: {', '.join(KINDS)})")
        if kind == "variation point" and axis is not None and not cell(axis).strip(" -—"):
            problems.append(f"{concept}: a variation point names its confirmed axis of change")

        existing: list[str] = []
        for token in TOKEN.findall(" | ".join(row)):
            path = path_of(token)
            if path is None:
                continue
            if os.path.exists(os.path.join(repo, path)):
                existing.append(path)
                anchor = token.strip().partition("#")[2]
                if anchor and path.endswith(".md") and anchor not in anchors(os.path.join(repo, path)):
                    problems.append(f"{concept}: anchor `#{anchor}` not found in {path}")
            else:
                problems.append(f"{concept}: path `{path}` does not exist")
        if not existing:
            problems.append(f"{concept}: no existing path cited as evidence")

        definition = cell(columns["single definition"])
        if definition.lower().startswith("none"):
            if not cell(columns["status"]).strip(" -—"):
                problems.append(f"{concept}: no single definition and no status naming where it will come from")
            continue
        tokens = TOKEN.findall(definition)
        paths = [p for p in (path_of(t) for t in tokens) if p and os.path.isfile(os.path.join(repo, p))]
        if not paths:
            problems.append(f"{concept}: the single definition cites no existing file")
            continue
        texts = []
        for path in paths:
            with open(os.path.join(repo, path), encoding="utf-8") as handle:
                texts.append(handle.read())
        for token in tokens:
            if path_of(token) is not None:
                continue
            symbol = token.strip().rstrip("()")
            if not any(symbol in text for text in texts):
                problems.append(f"{concept}: symbol `{symbol}` not found in {', '.join(paths)}")
    return problems


def lookup(header: list[str], rows: list[list[str]], pattern: str | None) -> list[str]:
    """Return the lookup lines: `<concept> | <kind>` per row when `pattern` is None, else the matching rows in full.

    Raises re.error when `pattern` is not a valid regular expression.
    """
    names = [name.lower() for name in header]
    concept = names.index("concept") if "concept" in names else 0
    kind = names.index("kind") if "kind" in names else None
    if pattern is None:
        return [f"{row[concept]} | {row[kind] if kind is not None and kind < len(row) else ''}".rstrip(" |")
                for row in rows if concept < len(row)]
    wanted = re.compile(pattern, re.IGNORECASE)
    head = "| " + " | ".join(header) + " |"
    hits = ["| " + " | ".join(row) + " |" for row in rows if concept < len(row) and wanted.search(row[concept])]
    return [head, *hits] if hits else []


def run(profile_path: str, concepts: bool = False, pattern: str | None = None) -> int:
    """Check the registry named by the profile, or print a lookup (`concepts`, `pattern`); return the exit code."""
    try:
        profile = quality_profile.load_valid(profile_path)
        section = profile.get("canonicalSources")
        if section is None or quality_profile.is_unset("canonicalSources", section):
            print("canonical-sources: canonicalSources is unset in the binding; no registry to check or look up")
            return 0
        repo = os.path.dirname(os.path.dirname(os.path.abspath(profile_path)))
        with open(os.path.join(repo, section["doc"]), encoding="utf-8") as handle:
            header, rows = parse_table(handle.read().splitlines(), section["heading"])
    except quality_profile.MissingProfile:
        print(f"canonical-sources: {quality_profile.MISSING}")
        return 0
    except (quality_profile.ProfileError, OSError, ValueError, KeyError) as exc:
        print(f"canonical-sources: {exc}", file=sys.stderr)
        return 2
    if concepts or pattern is not None:
        try:
            lines = lookup(header, rows, pattern)
        except re.error as exc:
            print(f"canonical-sources: invalid regex: {exc}", file=sys.stderr)
            return 2
        print("\n".join(lines) if lines else "canonical-sources: no matching row")
        return 0
    problems = check(header, rows, repo)
    for problem in problems:
        print(f"canonical-sources: {problem}")
    if problems:
        return 1
    kinds = {kind: 0 for kind in KINDS}
    for row in rows:
        kinds[row[[h.lower() for h in header].index("kind")].strip("` ").lower()] += 1
    summary = ", ".join(f"{kind} {count}" for kind, count in kinds.items() if count) or "empty registry, rows come on evidence"
    print(f"canonical-sources: ok ({len(rows)} rows: {summary})")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", default=quality_profile.DEFAULT_PROFILE)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--concepts", action="store_true", help="print `<concept> | <kind>` per row")
    mode.add_argument("--rows", metavar="REGEX", help="print the rows whose concept matches (case-insensitive)")
    args = parser.parse_args(argv)
    return run(args.profile, concepts=args.concepts, pattern=args.rows)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
