#!/usr/bin/env python3
"""Check a research call ledger: is the closure read, and did a read body call anything the ledger does not name?

Language-neutral: the research runner reads the code and writes the ledger; this script only follows the ledger's
edges, looks identifier tokens up in a definition index and compares. Formats: research_closure.py.

Usage:
  python3 scripts/forge/closure_check.py <research/<report>.md> [--ledger <path>] [--depth N] [--budget-share F]
                                        [--index auto|ctags|regex|none] [--root <dir>]
      --ledger        default: <report>-ledger.md next to the report
      --depth         closure depth from the seeds (default 2)
      --budget-share  the depth-N `other` items share a line budget of F × the depth < N entry lines (default 0.5)
      --index         definition index: Universal Ctags when installed (auto), the regex fallback, or none
      --root          project root that cited paths resolve against (default: the current directory)
research_check.py runs this and research_lint.py as one command; research_query.py prints bodies in batches.

The report may not exist yet (the check also runs while the runner is still reading); its `## Coverage` section,
when present, and the ledger's optional `## Excluded` section (`- `<symbol>` `<path:N>` — <reason>`, the exclusions
planned before the report exists) supply the `excluded` items.

Items (research_closure.py): depth < --depth items are read in full; depth-N `access` and `data` items are always
in; depth-N `other` items are kept smallest first within the line budget, the rest are `over budget`. Containers
(a `[container]` tag, or a class/module/… kind in the index) need no entry and cost no budget: their members are the
items.

Findings (one line each; blocking ones first):
  ledger_*      blocking  the ledger has no `## Seeds` or `## Read` section, a malformed seed, entry or edge (an
                          edge target is `path:N`, `external`, or `ignored — <reason>`), a seed or entry without a
                          role tag (`ledger_no_role`), or a citation whose file does not resolve or whose lines are
                          out of range
  not_read      blocking  a closure item at depth < --depth, not a container, with no ledger `### ` entry (its
                          callees are unknown) and not `excluded` in the report's Coverage
  container_no_entry  blocking  a container at depth < --depth with no `### ` entry (its members are unknown)
                          and not `excluded`; a container's entry lists the members that matter as edges, and
                          they stand at the container's own depth
  missed_ref    blocking with the ctags index, `advisory` with the regex index: an identifier token in the body
                          (`path:N-M`; comments and string literals dropped, code interpolated into a string
                          kept) of the ledger entry of a closure item below --depth (containers skipped), that the
                          index defines outside that body, and that is neither an edge or `ignored` token of the
                          entry (compared on the last name segment), nor defined at an edge's target or an
                          `excluded` row's line or at the definition that line names (ctags: the innermost
                          definition containing it, else the first after it). The entry's own name
                          on its head is not a use. With ctags it is advisory too when every use of the token is
                          a member or qualified access (after `.`, `->`, `::`, `?.`: `repo.get()`, Go `pkg.F()`,
                          `mod::f()`) and every definition is in another file: name lookup cannot tell these from
                          namesakes, so check each advisory line
  excluded_not_in_closure  advisory  a ledger `## Excluded` line that names no closure item (a wrong line?)
  note          an ambiguous path (first candidate used), a missing report
Output: `<report>-closure.txt` next to the report, also printed: a header (depth, budget, seeds, items), one line
per closure item (`D<depth> `<symbol>` <path:N> [<role>] — <state>`), the findings, then
`closure-check: <b> blocking, <a> advisory`.
Exit codes: 0 no blocking finding; 1 at least one; 2 bad arguments, an unreadable ledger, an unwritable output, or a
forced ctags index that is missing or fails.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

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
    """Missed-reference lines for the entries of the closure items in budget below max_depth, containers skipped.
    `excluded`: the raw (realpath, line) of the Coverage rows marked excluded."""
    out: List[str] = []
    done: Set[int] = set()
    def_lines = _def_lines(index)
    excluded = _anchors(excluded, index, def_lines)
    for node in nodes:
        entry = node.entry
        if entry is None or node.container or not node.in_cap or node.depth >= max_depth or id(entry) in done:
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


class Closure(NamedTuple):
    ledger: rc.Ledger
    nodes: List[rc.Node]
    budget: rc.Budget
    coverage: Dict[Tuple[str, int], rc.CoverageRow]
    excluded: Set[Tuple[str, int]]  # item keys excluded in Coverage or in the ledger's `## Excluded`
    excluded_raw: Set[Tuple[str, int]]  # the (realpath, line) those rows name, as written


def closure_state(ledger: rc.Ledger, report: Optional[str], res: rc.Resolver, index: rc.Index, max_depth: int,
                  share: float) -> Closure:
    """The closure with its budget applied, the report's Coverage rows by item key ({} without a report), and the
    excluded items (Coverage `excluded` rows and the ledger's `## Excluded`)."""
    nodes = rc.compute_closure(ledger, res, max_depth, index.containers)
    nodes, budget = rc.apply_budget(nodes, res, index, max_depth, share)
    rows = (rc.parse_coverage(report) or []) if report is not None else []
    coverage = rc.coverage_by_key(rows, res, ledger.entries, index.containers)
    refs = [row.ref for row in coverage.values() if row.status == "excluded"] + [ref for ref, _r in ledger.excluded]
    excluded: Set[Tuple[str, int]] = set()
    excluded_raw: Set[Tuple[str, int]] = set()
    for ref in refs:
        key = rc._key(ref, res, ledger.entries, index.containers)
        if key is not None:
            excluded.add(key)
            excluded_raw.add((key[0], ref.start))
    return Closure(ledger, nodes, budget, coverage, excluded, excluded_raw)


def item_state(node: rc.Node, excluded: Set[Tuple[str, int]], max_depth: int) -> str:
    if not node.in_cap:
        return "not covered: over budget (%d lines)" % node.size
    if node.key in excluded:
        return "excluded"
    if node.container and (node.entry is not None or node.depth >= max_depth):
        return "container: its members are the items (Coverage: read or excluded)"
    if node.container:
        return "CONTAINER WITHOUT ENTRY"
    if node.entry is not None:
        return "read in ledger"
    if node.depth >= max_depth:
        return "leaf (depth %d): coverage row only" % max_depth
    return "NOT READ"


def item_line(node: rc.Node, state: str) -> str:
    role = "container" if node.container else node.role
    return "D%d `%s` %s:%d [%s] — %s" % (node.depth, node.symbol, node.rel, node.line, role, state)


def run(report_path: str, ledger_path: str, root: str, max_depth: int, share: float, index_mode: str,
        index: Optional[rc.Index] = None) -> Tuple[str, int]:
    """(output text, blocking count). Raises OSError for an unreadable ledger or a failed forced index. `index`: a
    definition index already built (research_check.py shares one); else built from index_mode."""
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
        notes.append("note no report at %s yet: exclusions only from the ledger's `## Excluded`" %
                     os.path.relpath(report_path, root))
    if index is None:
        index = rc.build_index(root, index_mode)
    state = closure_state(ledger, report, res, index, max_depth, share)
    items: List[str] = []
    for node in state.nodes:
        st = item_state(node, state.excluded, max_depth)
        if st == "NOT READ":
            blocking.append("not_read D%d `%s` %s:%d — no ledger entry and not excluded" % (
                node.depth, node.symbol, node.rel, node.line))
        elif st == "CONTAINER WITHOUT ENTRY":
            blocking.append("container_no_entry D%d `%s` %s:%d — write its `[container]` entry with the members that "
                            "matter as edges, or exclude it" % (node.depth, node.symbol, node.rel, node.line))
        items.append(item_line(node, st))
    keys = {n.key for n in state.nodes}
    for ref, _reason in ledger.excluded:
        key = rc._key(ref, res, ledger.entries, index.containers)
        if key is not None and key not in keys:
            advisory.append("advisory excluded_not_in_closure L%d `%s:%d` — no closure item at this line; use the "
                            "line the item list prints" % (ref.line, ref.path, ref.start))
    found = missed_refs(state.nodes, index, res, state.excluded_raw, max_depth)
    for line in found:
        (advisory if line.startswith("advisory ") else blocking).append(line)
    b = state.budget
    head = ["closure: depth %d; seeds %d; items %d (%d over budget)" % (
        max_depth, len(ledger.seeds), len(state.nodes), b.over),
        "budget: depth-%d `other` items get %d lines (%.2f × %d depth<%d entry lines); used %d" % (
            max_depth, b.limit, b.share, b.base, max_depth, b.used),
        "index: " + index.note]
    body = head + items + blocking + advisory + notes
    body.append("closure-check: %d blocking, %d advisory" % (len(blocking), len(advisory)))
    return "\n".join(body) + "\n", len(blocking)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check a research call ledger and its closure.")
    parser.add_argument("report", help="research/<report>.md")
    parser.add_argument("--ledger")
    parser.add_argument("--depth", type=int, default=rc.DEFAULT_DEPTH)
    parser.add_argument("--budget-share", type=float, default=rc.DEFAULT_BUDGET_SHARE)
    parser.add_argument("--index", choices=("auto", "ctags", "regex", "none"), default="auto")
    parser.add_argument("--root", default=os.getcwd())
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if args.depth < 0 or not 0 <= args.budget_share <= 100:
        print("error: --depth must be >= 0 and --budget-share between 0 and 100", file=sys.stderr)
        return 2
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("error: --root is not a directory: %s" % root, file=sys.stderr)
        return 2
    report, ledger, out_path = report_paths(args.report, args.ledger)
    try:
        output, n_blocking = run(report, ledger, root, args.depth, args.budget_share, args.index)
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
