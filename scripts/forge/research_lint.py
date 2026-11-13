#!/usr/bin/env python3
"""Lint a /research report: coverage of the closure, verified quotes, the ten facets, the two search routes.

Language-neutral: quotes are verified as text (spec_refs / verify_citations), the closure comes from the ledger
(research_closure.py, closure_check.closure_state). research_check.py runs this and closure_check.py as one command
with one definition index; standalone, pass the same --depth and --budget-share as closure_check.py.

Usage:
  python3 scripts/forge/research_lint.py <research/<report>.md> [--ledger <path>] [--depth N] [--budget-share F]
                                        [--index auto|ctags|regex|none] [--root <dir>]

Findings (`L<n>` is the report line):
  no_ledger                 blocking  the ledger cannot be read, so the closure is unknown
  no_coverage_section       blocking  no `## Coverage` section
  no_coverage_row           blocking  a closure item (in or over budget) without a Coverage bullet
  coverage_bad_status       blocking  a Coverage bullet that is not `— read`, `— excluded` or
                                      `— not covered: over budget` (`over cap` is read the same)
  over_budget_in_budget     blocking  `not covered: over budget` on an item that is in budget
  quoted_over_budget        blocking  an item over budget whose definition or body lines the report cites or quotes
                                      anywhere outside its own Coverage row: read it instead
  excluded_without_reason   blocking  `— excluded` with no reason after it
  read_without_quote        blocking  a `read` row without a quoted `path:N[-M]` citation after the definition
  read_quote_not_on_item    blocking  a `read` row whose verified quotes all lie outside the item: another file,
                                      or outside its ledger body range when it has a ledger entry
  <citation reason>         blocking  a citation on a read row or a facet that fails (file_missing, line_oob,
                                      quote_mismatch, … as in verify_citations.py)
  facet_missing             blocking  facet <n> (1..10) has no `- **<n>. …**` bullet under `## Facets`
  facet_unsupported         blocking  facet <n> has neither a verified quoted citation nor `none — searched: …`
  no_search_routes          blocking  no `## Search routes` section, or no top-down or bottom-up bullet in it
  seed_kind_missing         blocking  a seed kind (duplicates, callers, siblings, test infrastructure) with no
                                      `- <kind>:` bullet under `## Search routes`, or with neither a ledger seed of
                                      that kind (`duplicate …`/`facet 9`, `caller of …`, `sibling of …`,
                                      `test infra`/`facet 8`) nor `none — searched: …` on its bullet
  claim_without_quote       advisory  a line outside Coverage, Facets, Search routes, External Research, References
                                      and the quoted request (`>` lines), with a behaviour word (does not, never, always,
                                      strict, trim, normalise, validate, reject, throws, defaults, lowercase,
                                      case-sensitive, passthrough, unchanged, testable, sanitise, escape) and no
                                      quoted citation
Output: `<report>-research-lint.txt` next to the report, also printed; then `research-lint: <b> blocking, <a> advisory`.
Exit codes: 0 no blocking finding; 1 at least one; 2 bad arguments, an unreadable report or an unwritable output.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import closure_check  # noqa: E402  (sibling module; path set above)
import research_closure as rc  # noqa: E402
import spec_refs  # noqa: E402
import verify_citations  # noqa: E402

FACETS = (
    "entry point", "authorisation path", "data path", "data model", "validators and normalisers",
    "error mapping", "runtime limits and configuration", "test infrastructure", "duplicates",
    "contracts and docs",
)
_FACET_RE = re.compile(r"^\s*[-*+]\s+\**\s*(\d{1,2})[.)]")
_TOP_BULLET_RE = re.compile(r"^[-*+]\s+")
_NONE_SEARCHED_RE = re.compile(r"\bnone\s*[—–:-]+\s*searched\s*:\s*\S", re.IGNORECASE)
_EXCLUDED_RE = re.compile(r"[—–-]\s*excluded\s*(?:[—–:-]\s*)?(?P<reason>.*)$", re.IGNORECASE)
_CLAIM_RE = re.compile(
    r"\b(does not|doesn't|do not|never|always|strict(?:ly)?|trim\w*|normali[sz]\w*|validat\w*|reject\w*|"
    r"throws?|raises|defaults? to|lower-?case\w*|upper-?case\w*|case[- ](?:in)?sensitive|pass-?through|"
    r"unchanged|testable|sanitis\w*|sanitiz\w*|escapes?)\b", re.IGNORECASE)
_SKIP_SECTIONS = ("coverage", "facets", "search routes", "external research", "references")
_SEARCH_ROUTES = ("top-down", "bottom-up")
SEED_KIND_BULLETS = (("duplicate", r"duplicates?"), ("caller", r"callers?"), ("sibling", r"siblings?"),
                     ("test infra", r"test[ -]infra(?:structure)?"))


def _read(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def _quoted(line: str) -> List[spec_refs.Citation]:
    return [c for c in spec_refs.iter_citations(line) if c.quote is not None or c.unclosed]


def _with_lineno(cit: spec_refs.Citation, lineno: int) -> spec_refs.Citation:
    return cit._replace(line=lineno)


def _on_item(cit: spec_refs.Citation, candidates: List[str], def_real: Optional[str],
             entry: Optional[rc.Entry]) -> bool:
    """The citation lies in the item's file and, when the item has a ledger entry, inside its body range."""
    if not def_real or def_real not in {os.path.realpath(c) for c in candidates}:
        return False
    if entry is None:
        return True
    last = cit.end if cit.end is not None else cit.start
    end = entry.body.end if entry.body.end is not None else entry.body.start
    return entry.body.start <= cit.start and last <= end


def check_coverage(report: str, ledger: Optional[rc.Ledger], res: rc.Resolver, cites: verify_citations.Result,
                   index: rc.Index, max_depth: int, share: float) -> List[str]:
    out: List[str] = []
    rows = rc.parse_coverage(report)
    if rows is None:
        out.append("no_coverage_section L0 -")
    if ledger is None:
        out.append("no_ledger L0 -")
    rows = rows or []
    entries = ledger.entries if ledger is not None else []
    for row in rows:
        if row.status == "unknown":
            out.append("coverage_bad_status L%d %s" % (row.line, row.text.strip()))
        elif row.status == "excluded":
            m = _EXCLUDED_RE.search(row.text)
            if not m or not m.group("reason").strip():
                out.append("excluded_without_reason L%d `%s`" % (row.line, row.symbol))
        elif row.status == "read":
            quoted = _quoted(row.text)
            if not quoted:
                out.append("read_without_quote L%d `%s`" % (row.line, row.symbol))
                continue
            def_real = res.file(row.ref.path)[0]
            entry = rc.entry_for((def_real, row.ref.start), entries, res, index.containers) if def_real else None
            verified, on_item = False, False
            for cit in quoted:
                ok, candidates = cites.verify_full("L%d" % row.line, _with_lineno(cit, row.line))
                verified = verified or ok
                on_item = on_item or (ok and _on_item(cit, candidates, def_real, entry))
            if verified and not on_item:
                out.append("read_quote_not_on_item L%d `%s` — no verified quote in %s%s" % (
                    row.line, row.symbol, row.ref.path, " inside its ledger body" if entry is not None else ""))
    if ledger is None:
        return out
    state = closure_check.closure_state(ledger, report, res, index, max_depth, share)
    over: List[rc.Node] = []
    for node in state.nodes:
        row = state.coverage.get(node.key)
        if row is None:
            out.append("no_coverage_row D%d `%s` %s:%d%s" % (
                node.depth, node.symbol, node.rel, node.line, "" if node.in_cap else " (over budget)"))
        elif row.status == "over budget" and node.in_cap:
            out.append("over_budget_in_budget L%d `%s`" % (row.line, row.symbol))
        if not node.in_cap:
            over.append(node)
    out += check_quoted_over_budget(report, over, state.coverage, res)
    return out


def check_quoted_over_budget(report: str, over: List[rc.Node], coverage: Dict[Tuple[str, int], rc.CoverageRow],
                             res: rc.Resolver) -> List[str]:
    """An over-budget item's lines (definition to body end) cited anywhere in the report, its own row aside."""
    if not over:
        return []
    own = {coverage[n.key].line for n in over if n.key in coverage}
    out: List[str] = []
    seen = set()
    for cit in spec_refs.iter_citations(report):
        if cit.line in own:
            continue
        real = res.file(cit.path)[0]
        if not real:
            continue
        last = cit.end if cit.end is not None else cit.start
        for node in over:
            n_end = node.key[1] + max(node.size, 1) - 1
            if node.key[0] == real and cit.start <= n_end and last >= node.key[1] and (node.key, cit.line) not in seen:
                seen.add((node.key, cit.line))
                out.append("quoted_over_budget L%d `%s` %s:%d — the report cites %s:%d%s; read the item instead" % (
                    cit.line, node.symbol, node.rel, node.line, cit.path, cit.start,
                    "-%d" % cit.end if cit.end is not None else ""))
    return out


def check_seed_kinds(report: str, ledger: Optional[rc.Ledger]) -> List[str]:
    lines = rc._section_lines(report, "Search routes")
    if lines is None:
        return []  # no_search_routes already says so
    kinds = {s.kind for s in ledger.seeds} if ledger is not None else set()
    out: List[str] = []
    for kind, label in SEED_KIND_BULLETS:
        bullet = [text for _l, text in lines if re.match(r"^\s*[-*+]\s+\**%s\**\s*:" % label, text, re.I)]
        name = {"test infra": "test infrastructure"}.get(kind, kind + "s")
        if not bullet:
            out.append("seed_kind_missing L0 %s: no `- %s:` bullet under ## Search routes" % (name, name))
        elif kind not in kinds and not any(_NONE_SEARCHED_RE.search(t) for t in bullet):
            out.append("seed_kind_missing L0 %s: no `%s` seed in the ledger and no `none — searched:`" % (
                name, kind))
    return out


def _facet_blocks(lines: List[Tuple[int, str]]) -> Dict[int, List[Tuple[int, str]]]:
    blocks: Dict[int, List[Tuple[int, str]]] = {}
    current: Optional[int] = None
    for lineno, line in lines:
        m = _FACET_RE.match(line)
        if m:
            current = int(m.group(1))
            blocks.setdefault(current, []).append((lineno, line))
        elif _TOP_BULLET_RE.match(line) or line.startswith("#"):
            current = None
        elif current is not None and line.strip():
            blocks[current].append((lineno, line))
    return blocks


def check_facets(report: str, cites: verify_citations.Result) -> List[str]:
    lines = rc._section_lines(report, "Facets")
    if lines is None:
        return ["facet_missing L0 all (no `## Facets` section)"]
    out: List[str] = []
    blocks = _facet_blocks(lines)
    for n, name in enumerate(FACETS, 1):
        block = blocks.get(n)
        if not block:
            out.append("facet_missing L0 %d. %s" % (n, name))
            continue
        if any(_NONE_SEARCHED_RE.search(text) for _l, text in block):
            continue
        verified = False
        for lineno, text in block:
            for cit in _quoted(text):
                if cites.verify("L%d" % lineno, _with_lineno(cit, lineno)):
                    verified = True
        if not verified:
            out.append("facet_unsupported L%d %d. %s" % (block[0][0], n, name))
    return out


def check_search_routes(report: str) -> List[str]:
    lines = rc._section_lines(report, "Search routes")
    if lines is None:
        return ["no_search_routes L0 -"]
    text = "\n".join(line.lower() for _l, line in lines)
    return ["no_search_routes L0 no %s bullet" % r for r in _SEARCH_ROUTES
            if not re.search(r"^\s*[-*+]\s+\**%s" % r, text, re.MULTILINE)]


def check_claims(report: str) -> List[str]:
    out: List[str] = []
    for sec in spec_refs.split_sections(report):
        if sec.title.lower().startswith(_SKIP_SECTIONS):
            continue
        fence: Optional[str] = None
        for i, line in enumerate(sec.body):
            new = spec_refs.fence_update(fence, line)
            fenced = fence is not None or new is not None
            fence = new
            stripped = line.strip()
            if fenced or not stripped or stripped.startswith((">", "#")) or set(stripped) <= set("|-: "):
                continue
            prose = line
            for s, e, _c in reversed(spec_refs.code_spans(line)):  # identifiers in code spans are not claims
                prose = prose[:s] + " " + prose[e:]
            m = _CLAIM_RE.search(prose)
            if m and not _quoted(line):
                excerpt = stripped if len(stripped) <= 120 else stripped[:117] + "..."
                out.append("advisory claim_without_quote L%d (%s) %s" % (sec.first + i, m.group(1), excerpt))
    return out


def run(report_path: str, ledger_path: str, root: str, max_depth: int, share: float, index_mode: str = "auto",
        index: Optional[rc.Index] = None) -> Tuple[str, int]:
    report = _read(report_path)
    if report is None:
        raise OSError("cannot read the report %s" % report_path)
    res = rc.Resolver(root)
    cites = verify_citations.Result(root)
    ledger_text = _read(ledger_path)
    ledger = rc.parse_ledger(ledger_text) if ledger_text is not None else None
    if index is None:
        index = rc.build_index(root, index_mode)
    blocking = check_coverage(report, ledger, res, cites, index, max_depth, share)
    blocking += check_facets(report, cites)
    blocking += check_search_routes(report)
    blocking += check_seed_kinds(report, ledger)
    blocking += cites.failures
    advisory = check_claims(report)
    body = blocking + advisory + cites.notes
    body.append("citations: %d checked, %d failed" % (cites.checked, len(cites.failures)))
    body.append("research-lint: %d blocking, %d advisory" % (len(blocking), len(advisory)))
    return "\n".join(body) + "\n", len(blocking)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Lint a /research report's coverage, facets and search routes.")
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
    report = os.path.abspath(args.report)
    stem = report[:-3] if report.endswith(".md") else report
    ledger = os.path.abspath(args.ledger) if args.ledger else stem + "-ledger.md"
    out_path = stem + "-research-lint.txt"
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
