#!/usr/bin/env python3
"""Check a research call ledger: is the closure read, and did a read body call anything the ledger does not name?

Language-neutral: the research runner reads the code and writes the ledger; this script only follows the ledger's
edges, looks identifier tokens up in a definition index and compares. Formats: research_closure.py.

Usage:
  python3 scripts/forge/closure_check.py <research/<report>.md> [--ledger <path>] [--depth N] [--cap N]
                                        [--index auto|ctags|regex|none] [--root <dir>]
      --ledger   default: <report>-ledger.md next to the report
      --depth    closure depth from the seeds (default 2)
      --cap      closure size; items past it are listed as `over cap` (default 60)
      --index    definition index: Universal Ctags when installed (auto), the regex fallback, or none
      --root     project root that cited paths resolve against (default: the current directory)

The report may not exist yet (the check also runs while the runner is still reading); its `## Coverage` section,
when present, supplies the `excluded` items.

Findings (one line each; blocking ones first):
  ledger_*      blocking  the ledger has no `## Seeds` or `## Read` section, a malformed seed, entry or edge (an
                          edge target is `path:N`, `external`, or `ignored — <reason>`), or a citation whose file
                          does not resolve or whose lines are out of range
  not_read      blocking  a closure item within the cap at depth < --depth with no ledger `### ` entry (its callees
                          are unknown) and not `excluded` in the report's Coverage
  missed_ref    blocking with the ctags index, `advisory` with the regex index: an identifier token in the body
                          (`path:N-M`; comments and string literals dropped, code interpolated into a string
                          kept) of the ledger entry of a closure item within the cap and below --depth, that the
                          index defines outside that body, and that is neither an edge or `ignored` token of the
                          entry (compared on the last name segment), nor defined at an edge's target or an
                          `excluded` row's line or at the definition that line names (ctags: the innermost
                          definition containing it, else the first after it). The entry's own name
                          on its head is not a use. With ctags it is advisory too when every use of the token is
                          a member or qualified access (after `.`, `->`, `::`, `?.`: `repo.get()`, Go `pkg.F()`,
                          `mod::f()`) and every definition is in another file: name lookup cannot tell these from
                          namesakes, so check each advisory line
  note          an ambiguous path (first candidate used), a missing report
Output: `<report>-closure.txt` next to the report, also printed: a header, one line per closure item
(`D<depth> `<symbol>` <path:N> — <state>`), the findings, then `closure-check: <b> blocking, <a> advisory`.
Exit codes: 0 no blocking finding; 1 at least one; 2 bad arguments, an unreadable ledger, an unwritable output, or a
forced ctags index that is missing or fails.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import research_closure as rc  # noqa: E402  (sibling module; path set above)
import spec_refs  # noqa: E402


def report_paths(report: str, ledger: Optional[str]) -> Tuple[str, str, str]:
    """(report, ledger, closure output) absolute paths."""
    report = os.path.abspath(report)
    stem = report[:-3] if report.endswith(".md") else report
    return report, os.path.abspath(ledger) if ledger else stem + "-ledger.md", stem + "-closure.txt"


def _read(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def _def_lines(index: rc.Index) -> Dict[str, List[int]]:
    """realpath -> sorted definition lines of every indexed name."""
    out: Dict[str, List[int]] = {}
    for defs in index.defs.values():
        for real, line in defs:
            out.setdefault(real, []).append(line)
    for lines in out.values():
        lines.sort()
    return out


def _anchors(locs: Set[Tuple[str, int]], index: rc.Index, def_lines: Dict[str, List[int]]) -> Set[Tuple[str, int]]:
    """Each location plus the definition it names, never a whole body. With definition ends (ctags): the innermost
    definition whose lines contain it, else the first definition at or after it (a decorator or a head line). Without
    ends (regex, advisory only): the last definition at or before it and the first after it."""
    out = set(locs)
    for real, line in locs:
        lines = def_lines.get(real, [])
        if index.ends:
            inside = [n for n in lines if n <= line <= index.ends.get((real, n), n)]
            if inside:
                out.add((real, max(inside)))
                continue
            after = [n for n in lines if n >= line]
            if after:
                out.add((real, after[0]))
            continue
        before = [n for n in lines if n <= line]
        after = [n for n in lines if n > line]
        if before:
            out.add((real, before[-1]))
        if after:
            out.add((real, after[0]))
    return out


def missed_refs(nodes: List[rc.Node], index: rc.Index, res: rc.Resolver, excluded: Set[Tuple[str, int]],
                max_depth: int) -> List[str]:
    """Missed-reference lines for the entries of the closure items within the cap and below max_depth.
    `excluded`: the raw (realpath, line) of the Coverage rows marked excluded."""
    out: List[str] = []
    done: Set[int] = set()
    def_lines = _def_lines(index)
    excluded = _anchors(excluded, index, def_lines)
    for node in nodes:
        entry = node.entry
        if entry is None or not node.in_cap or node.depth >= max_depth or id(entry) in done:
            continue
        done.add(id(entry))
        real = res.file(entry.body.path)[0]
        lines = spec_refs.read_lines(real) if real else None
        if lines is None:
            continue
        start = entry.body.start
        end = entry.body.end if entry.body.end is not None else entry.body.start
        known = {rc.last_segment(e.name) for e in entry.edges}
        targets = _anchors({(res.file(e.target.path)[0], e.target.start) for e in entry.edges
                            if e.target is not None and res.file(e.target.path)[0]}, index, def_lines)
        for tok in rc.body_tokens(lines, start, end, rc.last_segment(entry.symbol)):
            if tok.name in known or tok.name.lstrip("$") in known:
                continue
            defs = [d for d in index.defs.get(tok.name, []) if not (d[0] == real and start <= d[1] <= end)]
            if not defs or any(d in targets or d in excluded for d in defs):
                continue
            advisory = index.kind != "ctags" or (tok.member_only and all(d[0] != real for d in defs))
            more = " (+%d more)" % (len(defs) - 1) if len(defs) > 1 else ""
            out.append("%smissed_ref `%s` %s:%d uses `%s` at line %d, defined at %s:%d%s%s" % (
                "advisory " if advisory else "", entry.symbol, entry.body.path, start, tok.name, tok.line,
                res.rel(defs[0][0]), defs[0][1], more,
                " (member access, defined in another file)" if advisory and index.kind == "ctags" else ""))
    return out


def run(report_path: str, ledger_path: str, root: str, max_depth: int, cap: int, index_mode: str) -> Tuple[str, int]:
    """(output text, blocking count). Raises OSError for an unreadable ledger or a failed forced index."""
    text = _read(ledger_path)
    if text is None:
        raise OSError("cannot read the ledger %s" % ledger_path)
    res = rc.Resolver(root)
    ledger = rc.parse_ledger(text)
    blocking: List[str] = list(ledger.problems)
    advisory: List[str] = []
    notes: List[str] = []
    for line in rc.ledger_ref_problems(ledger, res):
        (notes if line.startswith("note ") else blocking).append(line)
    if not ledger.seeds and not any(p.startswith("ledger_no_seeds") for p in blocking):
        blocking.append("ledger_no_seeds L0 -")
    report = _read(report_path)
    if report is None:
        notes.append("note no report at %s yet: no exclusions read" % os.path.relpath(report_path, root))
        coverage: Dict[Tuple[str, int], rc.CoverageRow] = {}
    else:
        coverage = rc.coverage_by_key(rc.parse_coverage(report) or [], res, ledger.entries)
    excluded_keys = {k for k, row in coverage.items() if row.status == "excluded"}
    excluded_raw = {(res.file(row.ref.path)[0], row.ref.start) for row in coverage.values()
                    if row.status == "excluded" and res.file(row.ref.path)[0]}
    nodes = rc.compute_closure(ledger, res, max_depth, cap)
    items: List[str] = []
    for node in nodes:
        if not node.in_cap:
            state = "not covered: over cap"
        elif node.key in excluded_keys:
            state = "excluded"
        elif node.entry is not None:
            state = "read in ledger"
        elif node.depth >= max_depth:
            state = "leaf (depth %d): coverage row only" % max_depth
        else:
            state = "NOT READ"
            blocking.append("not_read D%d `%s` %s:%d — no ledger entry and not excluded" % (
                node.depth, node.symbol, node.rel, node.line))
        items.append("D%d `%s` %s:%d — %s" % (node.depth, node.symbol, node.rel, node.line, state))
    index = rc.build_index(root, index_mode)
    found = missed_refs(nodes, index, res, excluded_raw, max_depth)
    for line in found:
        (advisory if line.startswith("advisory ") else blocking).append(line)
    in_cap = sum(1 for n in nodes if n.in_cap)
    head = ["closure: depth %d, cap %d; seeds %d; items %d (%d in cap, %d over cap)" % (
        max_depth, cap, len(ledger.seeds), len(nodes), in_cap, len(nodes) - in_cap), "index: " + index.note]
    body = head + items + blocking + advisory + notes
    body.append("closure-check: %d blocking, %d advisory" % (len(blocking), len(advisory)))
    return "\n".join(body) + "\n", len(blocking)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check a research call ledger and its closure.")
    parser.add_argument("report", help="research/<report>.md")
    parser.add_argument("--ledger")
    parser.add_argument("--depth", type=int, default=rc.DEFAULT_DEPTH)
    parser.add_argument("--cap", type=int, default=rc.DEFAULT_CAP)
    parser.add_argument("--index", choices=("auto", "ctags", "regex", "none"), default="auto")
    parser.add_argument("--root", default=os.getcwd())
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if args.depth < 0 or args.cap < 1:
        print("error: --depth must be >= 0 and --cap >= 1", file=sys.stderr)
        return 2
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("error: --root is not a directory: %s" % root, file=sys.stderr)
        return 2
    report, ledger, out_path = report_paths(args.report, args.ledger)
    try:
        output, n_blocking = run(report, ledger, root, args.depth, args.cap, args.index)
    except Exception as exc:  # noqa: BLE001  any failure is exit 2, never a false "findings" exit 1
        print("error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2
    try:
        spec_refs.atomic_write(out_path, output)
    except OSError as exc:
        print("error: cannot write %s: %s" % (out_path, exc), file=sys.stderr)
        return 2
    sys.stdout.write(output)
    return 1 if n_blocking else 0


if __name__ == "__main__":
    sys.exit(main())
