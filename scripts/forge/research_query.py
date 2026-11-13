#!/usr/bin/env python3
"""Read-only queries for /research: bodies in batches, pending closure items, callers, siblings, the runner's trace.

Language-neutral: definitions come from the definition index (Universal Ctags, else the regex set; research_closure.py)
and body ends from the ctags `end` field or research_closure.body_end's rule (brace balance, else indentation, else
the head line); text matching does the rest. Writes nothing.

Usage:
  python3 scripts/forge/research_query.py bodies <item>... [--max-lines N] [--index …] [--root <dir>]
      each <item> is `path:N` (the definition holding line N; a head line works too) or a symbol name (every
      definition of its last segment, at most 5). Prints each body with line numbers under a heading that is the
      ledger entry line without its role tag: `### `<symbol>` `<path:N-M>`  (end: ctags|brace|indent|line|uncertain)`.
      A `path:N` inside a body names the innermost non-container definition holding it. `uncertain` ends show at
      most 30 lines: read on from the last line shown and correct M. A body longer than --max-lines (default 250)
      is cut, and the cut says which lines remain.
  python3 scripts/forge/research_query.py pending <research/<report>.md> [--batch N] [--ledger] [--depth N]
                                                  [--budget-share F] [--max-lines N] [--index …] [--root <dir>]
      the bodies of the closure items at depth < --depth with no ledger entry and not excluded (Coverage, or the
      ledger's `## Excluded`), closure order, at most --batch (default 20); containers without an entry as one-line
      notes. With --leaves: all in-budget depth-N items with no Coverage row instead (no --batch cut; read them
      once, after the last seeds are read).
  python3 scripts/forge/research_query.py items <research/<report>.md> [--ledger] [--depth N] [--budget-share F]
                                                [--index …] [--root <dir>]
      the closure item lines closure_check.py prints (`D<n> `<symbol>` <path:N> [<role>] — <state>`), without the
      findings and without writing anything: the item list for Coverage between check runs.
  python3 scripts/forge/research_query.py callers <symbol> [--max N] [--index …] [--root <dir>]
      every word match of the symbol's last segment in the source files (comments and string literals dropped),
      grouped by the enclosing definition (`path:N`), with the totals. A namesake is not a caller: check each.
  python3 scripts/forge/research_query.py siblings <path:N> [--terms a,b,…] [--index …] [--root <dir>]
      the other definitions in the same file as the one holding line N (for a container head: its members), with
      their ranges; `[mentions: …]` when a
      body contains a term (case-insensitive), such as the collection, table or key prefix the item touches.
  python3 scripts/forge/research_query.py trace <research/<report>.md> [--transcript <file>]
      the research runner's turns and peak context, read from the Claude Code transcript that wrote
      `<report>-ledger.md` (the newest one; a main session counts from its last `/research` command): assistant
      responses deduplicated by message id; context = input + cache write + cache read tokens. A ledger write is a
      Write/Edit/MultiEdit/NotebookEdit on a file of that name, or a shell redirect or `tee` into it. Prints
      `trace: <n> turns, peak context <k>k tokens, <m>M context tokens in all` and a `transcript: <path>` line, or
      `trace: unavailable (<reason>)`.

Exit codes: 0 printed (a query that finds nothing prints that too); 2 bad arguments, an unreadable ledger or report
for `pending`, or a forced ctags index that is missing or fails.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import closure_check  # noqa: E402  (sibling module; path set above)
import research_closure as rc  # noqa: E402
import spec_refs  # noqa: E402

MAX_SYMBOL_DEFS = 5
TRACE_MAX_AGE_S = 3 * 24 * 3600

Loc = Tuple[str, int]


# ---------------------------------------------------------------------------
# Definitions in a file
# ---------------------------------------------------------------------------

def _file_defs(index: rc.Index) -> Dict[str, List[int]]:
    out: Dict[str, List[int]] = {}
    for locs in index.defs.values():
        for real, line in locs:
            out.setdefault(real, []).append(line)
    for lines in out.values():
        lines.sort()
    return out


def enclosing(real: str, line: int, index: rc.Index, by_file: Dict[str, List[int]],
              skip_containers: bool = False) -> Optional[Tuple[int, int, str]]:
    """(head, end, how) of the innermost definition in `real` whose lines hold `line`, else None."""
    best: Optional[Tuple[int, int, str]] = None
    for head in by_file.get(real, []):
        if head > line:
            break
        if skip_containers and (real, head) in index.containers:
            continue
        end, how = rc.item_end(real, head, index)
        if head <= line <= end and (best is None or head >= best[0]):
            best = (head, end, how)
    return best


def _only_attributes(real: str, line: int, head: int) -> bool:
    """Lines line..head-1 are decorators, attributes, comments or blank: `line` belongs to the definition at head."""
    lines = rc.file_lines(real) or []
    for n in range(line, head):
        text = lines[n - 1].strip() if n <= len(lines) else ""
        if text and not text.startswith(("@", "#[", "[", "template")) and not rc._comment_line(lines[n - 1]):
            return False
    return True


def _resolve_item(item: str, res: rc.Resolver, index: rc.Index, by_file: Dict[str, List[int]],
                  names: Dict[Loc, str]) -> Tuple[List[Tuple[str, str, int, int, str]], str]:
    """([(symbol, realpath, head, end, how)], problem)."""
    text = item.strip().strip("`")
    m = spec_refs._CITE_RE.match(text)
    if m:
        real = res.file(m.group(1))[0]
        if not real:
            return [], "file not found"
        line = int(m.group(2))
        heads = by_file.get(real, [])
        if line in heads:
            end, how = rc.item_end(real, line, index)
            return [(names.get((real, line), "?"), real, line, end, how)], ""
        enc = enclosing(real, line, index, by_file, skip_containers=True)
        if enc:
            return [(names.get((real, enc[0]), "?"), real, enc[0], enc[1], enc[2])], ""
        near = [h for h in heads if line < h <= line + rc.HEAD_LINES and _only_attributes(real, line, h)]
        if near:
            end, how = rc.item_end(real, near[0], index)
            return [(names.get((real, near[0]), "?"), real, near[0], end, how)], ""
        lines = rc.file_lines(real) or []
        end, how = rc.body_end(lines, line)
        return [("?", real, line, end, how)], ""
    name = rc.last_segment(text)
    locs = sorted(index.defs.get(name, []))
    if not locs:
        return [], "no definition named `%s` in the index" % name
    out = []
    for real, head in locs[:MAX_SYMBOL_DEFS]:
        end, how = rc.item_end(real, head, index)
        out.append((name, real, head, end, how))
    problem = "%d more definitions of `%s` not shown" % (len(locs) - MAX_SYMBOL_DEFS, name) \
        if len(locs) > MAX_SYMBOL_DEFS else ""
    return out, problem


def print_body(symbol: str, real: str, head: int, end: int, how: str, res: rc.Resolver, max_lines: int) -> List[str]:
    lines = rc.file_lines(real) or []
    end = min(end, len(lines))
    rel = res.rel(real)
    out = ["### `%s` `%s:%d-%d`  (end: %s)" % (symbol, rel, head, end, how)]
    last = min(end, head + max_lines - 1)
    for n in range(head, last + 1):
        out.append("%6d  %s" % (n, lines[n - 1]))
    if last < end:
        out.append("       … cut at %d lines: read `%s:%d-%d` for the rest" % (max_lines, rel, last + 1, end))
    out.append("")
    return out


def cmd_bodies(items: List[str], res: rc.Resolver, index: rc.Index, max_lines: int) -> List[str]:
    by_file = _file_defs(index)
    names = index.names_at()
    out = ["index: " + index.note, ""]
    for item in items:
        found, problem = _resolve_item(item, res, index, by_file, names)
        if not found:
            out.append("!! %s: %s" % (item, problem))
            out.append("")
            continue
        for symbol, real, head, end, how in found:
            out += print_body(symbol, real, head, end, how, res, max_lines)
        if problem:
            out.append("!! %s: %s" % (item, problem))
            out.append("")
    return out


def _state(report: str, ledger_path: str, res: rc.Resolver, index: rc.Index, max_depth: int,
           share: float) -> "closure_check.Closure":
    text = closure_check._read(ledger_path)
    if text is None:
        raise OSError("cannot read the ledger %s" % ledger_path)
    return closure_check.closure_state(rc.parse_ledger(text), closure_check._read(report), res, index, max_depth,
                                       share)


def cmd_pending(report: str, ledger_path: str, res: rc.Resolver, index: rc.Index, max_depth: int, share: float,
                batch: int, max_lines: int, leaves: bool) -> List[str]:
    state = _state(report, ledger_path, res, index, max_depth, share)
    first: List[rc.Node] = []
    boxes: List[rc.Node] = []
    later: List[rc.Node] = []
    for node in state.nodes:
        if not node.in_cap or node.entry is not None or node.key in state.excluded:
            continue
        if node.container:
            if node.depth < max_depth:
                boxes.append(node)
        elif node.depth < max_depth:
            first.append(node)
        elif state.coverage.get(node.key) is None:
            later.append(node)
    todo = later if leaves else first
    if leaves:
        batch = max(batch, len(later))  # the leaves are read once: never cut them
    out = ["index: " + index.note,
           "pending: %d need a ledger entry, %d containers need an entry, %d depth-%d items need a Coverage row; "
           "showing %d %s" % (len(first), len(boxes), len(later), max_depth, min(batch, len(todo)),
                              "depth-%d items" % max_depth if leaves else "entries"), ""]
    for node in boxes:
        out.append("container without entry: `%s` `%s:%d` — list its members with `siblings %s:%d`" % (
            node.symbol, node.rel, node.line, node.rel, node.line))
    if boxes:
        out.append("")
    if not leaves and not first and not boxes and later:
        out.append("depth 0–%d is done: run `pending --leaves` once for the %d depth-%d items" % (
            max_depth - 1, len(later), max_depth))
    by_file = _file_defs(index)
    names = index.names_at()
    for node in todo[:batch]:
        out.append("D%d [%s] from the ledger as `%s` `%s:%d`" % (node.depth, node.role, node.symbol, node.rel,
                                                                  node.line))
        found, _problem = _resolve_item("%s:%d" % (res.rel(node.key[0]), node.key[1]), res, index, by_file, names)
        for symbol, real, head, end, how in found[:1]:
            out += print_body(node.symbol if symbol == "?" else symbol, real, head, end, how, res, max_lines)
    return out


def cmd_items(report: str, ledger_path: str, res: rc.Resolver, index: rc.Index, max_depth: int,
              share: float) -> List[str]:
    state = _state(report, ledger_path, res, index, max_depth, share)
    out = ["index: " + index.note, "items: %d (%d over budget)" % (len(state.nodes), state.budget.over)]
    out += [closure_check.item_line(n, closure_check.item_state(n, state.excluded, max_depth)) for n in state.nodes]
    return out


# ---------------------------------------------------------------------------
# Callers and siblings
# ---------------------------------------------------------------------------

def _code_line(line: str) -> str:
    if rc._comment_line(line):
        return ""
    line = rc._INLINE_BLOCK_RE.sub(" ", line)
    line = rc._STRING_RE.sub(rc._strip_string, line)
    return rc._TRAILING_RE.sub(" ", line)


def cmd_callers(symbol: str, root: str, res: rc.Resolver, index: rc.Index, max_groups: int) -> List[str]:
    name = rc.last_segment(symbol)
    word = re.compile(r"(?<![\w$])%s(?![\w$])" % re.escape(name))
    own = set(index.defs.get(name, []))
    by_file = _file_defs(index)
    names = index.names_at()
    groups: Dict[Tuple[str, int], List[Tuple[int, str]]] = {}
    uses = 0
    for path in rc._source_files(root):
        if not rc._is_text(path):
            continue
        lines = rc.file_lines(os.path.realpath(path))
        if lines is None:
            continue
        real = os.path.realpath(path)
        for n, line in enumerate(lines, 1):
            if (real, n) in own or len(line) > rc.MAX_INDEX_LINE_CHARS or not word.search(_code_line(line)):
                continue
            uses += 1
            enc = enclosing(real, n, index, by_file, skip_containers=True)
            groups.setdefault((real, enc[0] if enc else 0), []).append((n, line.strip()))
    out = ["index: " + index.note,
           "callers of `%s`: %d uses in %d definitions (word matches outside comments and strings; a namesake is not "
           "a caller)" % (name, uses, len([k for k in groups if k[1]])), ""]
    for i, ((real, head), hits) in enumerate(sorted(groups.items(), key=lambda kv: (res.rel(kv[0][0]), kv[0][1]))):
        if i >= max_groups:
            out.append("… %d more definitions not shown (--max)" % (len(groups) - max_groups))
            break
        label = "`%s` `%s:%d`" % (names.get((real, head), "?"), res.rel(real), head) if head \
            else "(top level) `%s`" % res.rel(real)
        shown = "; ".join("L%d %s" % (n, t if len(t) <= 90 else t[:87] + "...") for n, t in hits[:3])
        more = " (+%d more)" % (len(hits) - 3) if len(hits) > 3 else ""
        out.append("- %s — %d use%s: %s%s" % (label, len(hits), "" if len(hits) == 1 else "s", shown, more))
    return out


def cmd_siblings(item: str, terms: List[str], res: rc.Resolver, index: rc.Index) -> List[str]:
    text = item.strip().strip("`")
    m = spec_refs._CITE_RE.match(text)
    if not m:
        raise ValueError("siblings takes a `path:N`, not %r" % item)
    real = res.file(m.group(1))[0]
    if not real:
        raise ValueError("file not found: %s" % m.group(1))
    by_file = _file_defs(index)
    names = index.names_at()
    line = int(m.group(2))
    lines = rc.file_lines(real) or []
    inside: Optional[Tuple[int, int]] = None  # siblings of a container head: its members only
    if (real, line) in index.containers:
        own_head = line
        inside = (line, rc.item_end(real, line, index)[0])
    else:
        own = enclosing(real, line, index, by_file, skip_containers=True)
        own_head = own[0] if own else line
    out = ["index: " + index.note,
           "siblings of `%s:%d` in %s%s:" % (m.group(1), own_head, res.rel(real),
                                            " (terms: %s)" % ", ".join(terms) if terms else ""), ""]
    count = 0
    for head in by_file.get(real, []):
        if head == own_head or (inside and not inside[0] < head <= inside[1]):
            continue
        end, how = rc.item_end(real, head, index)
        kind = " [container]" if (real, head) in index.containers else ""
        body = "\n".join(lines[head - 1:end]).lower()
        hit = [t for t in terms if t.lower() in body]
        mention = " [mentions: %s]" % ", ".join(hit) if hit else ""
        out.append("- `%s` `%s:%d-%d` (%d lines, end: %s)%s%s" % (
            names.get((real, head), "?"), res.rel(real), head, end, end - head + 1, how, kind, mention))
        count += 1
    if not count:
        out.append("(no other definition in this file)")
    return out


# ---------------------------------------------------------------------------
# Trace
# ---------------------------------------------------------------------------

def projects_dir() -> str:
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "projects")


def transcript_dirs(root: str) -> List[str]:
    """The transcript dirs Claude Code may use for this root: named after the path as given and as resolved."""
    out: List[str] = []
    for path in (os.path.abspath(root), os.path.realpath(root)):
        folder = os.path.join(projects_dir(), re.sub(r"[^A-Za-z0-9]", "-", path))
        if folder not in out:
            out.append(folder)
    return out


WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def _writes_ledger(entry: dict, ledger_name: str) -> bool:
    """An assistant response that writes the ledger: a file tool on it, or a shell redirect or `tee` into it."""
    message = entry.get("message")
    if entry.get("type") != "assistant" or not isinstance(message, dict):
        return False
    content = message.get("content")
    if not isinstance(content, list):
        return False
    redirect = re.compile(r"(?:(?<![-=>])>>?|\btee\b(?:\s+-a)?|\bsed\s+-i\S*(?:\s+'[^']*'|\s+[^\s;|&]+)*?)\s*['\"]?"
                          r"(?:[^\s'\"]*/)?%s(?:['\"\s;|&)]|$)" % re.escape(ledger_name))
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use" or not isinstance(block.get("input"), dict):
            continue
        inp = block["input"]
        if block.get("name") in WRITE_TOOLS and os.path.basename(str(inp.get("file_path", ""))) == ledger_name:
            return True
        if redirect.search(str(inp.get("command", ""))):
            return True
    return False


def _entries(path: str) -> List[dict]:
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                try:
                    obj = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(obj, dict):
                    out.append(obj)
    except OSError:
        pass
    return out


def find_transcript(root: str, ledger_name: str) -> Tuple[Optional[str], str]:
    folders = [f for f in transcript_dirs(root) if os.path.isdir(f)]
    if not folders:
        return None, "no transcript dir %s" % transcript_dirs(root)[0]
    folder = folders[0]
    now = time.time()
    cands = [p for f in folders for p in glob.glob(os.path.join(f, "**", "*.jsonl"), recursive=True)
             if now - os.path.getmtime(p) < TRACE_MAX_AGE_S]
    for path in sorted(cands, key=os.path.getmtime, reverse=True):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                if ledger_name not in handle.read():
                    continue
        except OSError:
            continue
        if any(_writes_ledger(e, ledger_name) for e in _entries(path)):
            return path, ""
    return None, "no recent transcript in %s writes %s" % (folder, ledger_name)


def _is_research_command(entry: dict) -> bool:
    if entry.get("type") != "user":
        return False
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    text = content if isinstance(content, str) else json.dumps(content) if content is not None else ""
    return "<command-name>/research</command-name>" in text


def trace(path: str, ledger_name: str) -> Tuple[int, int, int]:
    """(turns, peak context, context tokens in all) of the transcript, from its last `/research` command before
    the first ledger write (a subagent transcript: from its start)."""
    entries = _entries(path)
    first_write = next((i for i, e in enumerate(entries) if _writes_ledger(e, ledger_name)), len(entries))
    start = 0
    for i in range(first_write):
        if _is_research_command(entries[i]):
            start = i
    seen: Set[str] = set()
    turns, peak, total = 0, 0, 0
    for entry in entries[start:]:
        message = entry.get("message")
        if entry.get("type") != "assistant" or not isinstance(message, dict):
            continue
        usage = message.get("usage")
        mid = message.get("id") or entry.get("uuid")
        if not isinstance(usage, dict) or not mid or mid in seen:
            continue
        seen.add(mid)
        ctx = sum(int(usage.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens",
                                                   "cache_read_input_tokens"))
        turns += 1
        peak = max(peak, ctx)
        total += ctx
    return turns, peak, total


def cmd_trace(report: str, root: str, transcript: Optional[str]) -> List[str]:
    stem = report[:-3] if report.endswith(".md") else report
    ledger_name = os.path.basename(stem) + "-ledger.md"
    path, why = (transcript, "") if transcript else find_transcript(root, ledger_name)
    if not path:
        return ["trace: unavailable (%s)" % why]
    turns, peak, total = trace(path, ledger_name)
    if not turns:
        return ["trace: unavailable (no assistant responses with usage in %s)" % path]
    return ["trace: %d turns, peak context %dk tokens, %.1fM context tokens in all" % (
        turns, round(peak / 1000), total / 1e6), "transcript: %s" % path]


# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only queries for /research.")
    sub = parser.add_subparsers(dest="cmd")

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--index", choices=("auto", "ctags", "regex", "none"), default="auto")
        p.add_argument("--root", default=os.getcwd())

    p = sub.add_parser("bodies")
    p.add_argument("items", nargs="+")
    p.add_argument("--max-lines", type=int, default=250)
    common(p)
    p = sub.add_parser("pending")
    p.add_argument("report")
    p.add_argument("--ledger")
    p.add_argument("--batch", type=int, default=20)
    p.add_argument("--depth", type=int, default=rc.DEFAULT_DEPTH)
    p.add_argument("--budget-share", type=float, default=rc.DEFAULT_BUDGET_SHARE)
    p.add_argument("--max-lines", type=int, default=250)
    p.add_argument("--leaves", action="store_true")
    common(p)
    p = sub.add_parser("items")
    p.add_argument("report")
    p.add_argument("--ledger")
    p.add_argument("--depth", type=int, default=rc.DEFAULT_DEPTH)
    p.add_argument("--budget-share", type=float, default=rc.DEFAULT_BUDGET_SHARE)
    common(p)
    p = sub.add_parser("callers")
    p.add_argument("symbol")
    p.add_argument("--max", type=int, default=60)
    common(p)
    p = sub.add_parser("siblings")
    p.add_argument("item")
    p.add_argument("--terms", default="")
    common(p)
    p = sub.add_parser("trace")
    p.add_argument("report")
    p.add_argument("--transcript")
    p.add_argument("--root", default=os.getcwd())
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if not args.cmd:
        parser.print_usage(sys.stderr)
        return 2
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("error: --root is not a directory: %s" % root, file=sys.stderr)
        return 2
    for name in ("max_lines", "batch", "max"):
        if getattr(args, name, 1) < 1:
            print("error: --%s must be >= 1" % name.replace("_", "-"), file=sys.stderr)
            return 2
    try:
        if args.cmd == "trace":
            out = cmd_trace(os.path.abspath(args.report), root, args.transcript)
        else:
            res = rc.Resolver(root)
            index = rc.build_index(root, args.index)
            if args.cmd == "bodies":
                out = cmd_bodies(args.items, res, index, args.max_lines)
            elif args.cmd in ("pending", "items"):
                report, ledger, _out = closure_check.report_paths(args.report, args.ledger)
                if args.cmd == "pending":
                    out = cmd_pending(report, ledger, res, index, args.depth, args.budget_share, args.batch,
                                      args.max_lines, args.leaves)
                else:
                    out = cmd_items(report, ledger, res, index, args.depth, args.budget_share)
            elif args.cmd == "callers":
                out = cmd_callers(args.symbol, root, res, index, args.max)
            else:
                out = cmd_siblings(args.item, [t.strip() for t in args.terms.split(",") if t.strip()], res, index)
    except Exception as exc:  # noqa: BLE001  any failure is exit 2
        print("error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2
    sys.stdout.write("\n".join(out).rstrip("\n") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
