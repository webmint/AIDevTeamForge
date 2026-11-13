"""Shared helpers for the research coverage checks (closure_check.py, research_lint.py).

Not a CLI. Stdlib only; Python 3.9+. Nothing here knows a programming language: the research runner reads the code
and writes the ledger; this module parses the ledger, computes the closure over its edges, builds a definition index
and parses the report's `## Coverage` section.

Ledger (`research/<report>-ledger.md`):
  ## Seeds
  - `<symbol>` `<path:N>` — pass <1|2> — <route or reason>
  ## Read
  ### `<symbol>` `<path:N-M>`            the body the runner read (N = the definition line)
  - `<callee>` → `<path:N>`               a repository definition the body calls or references
  - `<callee>` → external                 a library or framework symbol
  - `<token>` → ignored — <reason>        a token in the body that is not a reference
`->` is accepted for `→`. A `### ` entry with a single `path:N` covers that line only.

Closure: breadth-first from every seed over the edges whose target is a `path:N`. An edge target (or a seed) is a
node keyed by (resolved file, line); its ledger entry is the `### ` entry in the same file whose range contains the
line (the narrowest when several do). Depth = distance to the nearest seed. Nodes at depth < max_depth are expanded
through their entry; the closure lists every node up to max_depth, ordered by depth then discovery; past `cap` nodes
are `over cap`.

Coverage (`## Coverage` in the report), one bullet per closure item:
  - `<symbol>` `<path:N>` — read — `<path:N-M>` `<verbatim quote>` [<found by>]
  - `<symbol>` `<path:N>` — excluded — <reason>
  - `<symbol>` `<path:N>` — not covered: over cap
A row is matched to a closure item by its first `path:N` span (the definition), resolved like the ledger's.

Definition index (`build_index`): a ctags tag counts when its kind is a callable or type kind (CTAGS_KINDS) or it
has a signature (a method that ctags calls `member`); fields and variables do not. `auto` uses the first `ctags`,
`uctags` or `universal-ctags` on PATH whose `--version` names Universal Ctags, else the regex set; `ctags`, `regex`
and `none` force one. Indexed: the search scopes of `.claude/quality-profile.json` (`searchScopes` minus
`generatedDirs`) when set, else the root; spec_refs.PRUNED_DIRS are skipped.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)
import spec_refs  # noqa: E402

DEFAULT_DEPTH = 2
DEFAULT_CAP = 60
CTAGS_TIMEOUT = 300
MAX_INDEX_FILE_BYTES = 1_000_000
MAX_INDEX_LINE_CHARS = 2000  # minified or generated lines: skipped (the method-head pattern is slow on them)

_ARROW_RE = re.compile(r"\s*(?:→|->)\s*")
_PASS_RE = re.compile(r"\bpass\s*([12])\b", re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[-*+]\s+")
_H3_RE = re.compile(r"^ {0,3}###\s+(.*)$")
_IDENT_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_NAME_SPLIT_RE = re.compile(r"::|->|[.#\\/]")


class Ref(NamedTuple):
    """A `path:N[-M]` span as written, with where it appeared."""
    path: str
    start: int
    end: Optional[int]
    line: int  # line in the markdown file


class Edge(NamedTuple):
    name: str
    kind: str  # "def" | "external" | "ignored" | "bad"
    target: Optional[Ref]
    reason: str
    line: int


class Entry(NamedTuple):
    symbol: str
    body: Ref
    edges: List[Edge]
    line: int


class Seed(NamedTuple):
    symbol: str
    ref: Ref
    pass_no: int
    source: str
    line: int


class Ledger(NamedTuple):
    seeds: List[Seed]
    entries: List[Entry]
    problems: List[str]  # "<code> L<line> <detail>"


class Node(NamedTuple):
    key: Tuple[str, int]  # (realpath, line)
    symbol: str
    rel: str  # path as first written
    line: int
    depth: int
    in_cap: bool
    entry: Optional[Entry]


class CoverageRow(NamedTuple):
    symbol: str
    ref: Ref
    status: str  # "read" | "excluded" | "over cap" | "unknown"
    text: str  # the whole bullet line
    line: int


def last_segment(name: str) -> str:
    """`a.b`, `A::b`, `A#b`, `A->b`, `pkg/b`, `b()` -> `b` (the name a body token is compared with)."""
    name = name.strip().rstrip("()").strip()
    parts = [p for p in _NAME_SPLIT_RE.split(name) if p]
    return parts[-1] if parts else name


def _spans(line: str) -> List[str]:
    return [c for _s, _e, c in spec_refs.code_spans(line)]


def _ref(content: str, lineno: int) -> Optional[Ref]:
    m = spec_refs._CITE_RE.match(content)
    if not m:
        return None
    return Ref(m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else None, lineno)


def _first_ref(spans: List[str], lineno: int, skip: int = 0) -> Optional[Ref]:
    for content in spans[skip:]:
        ref = _ref(content, lineno)
        if ref:
            return ref
    return None


def _section_lines(text: str, title_prefix: str) -> Optional[List[Tuple[int, str]]]:
    """(line number, line) of the first `## ` section whose title starts with title_prefix (case-insensitive), fenced
    lines dropped; None when there is no such section."""
    for sec in spec_refs.split_sections(text):
        if sec.title.lower().startswith(title_prefix.lower()):
            out: List[Tuple[int, str]] = []
            fence: Optional[str] = None
            for i, line in enumerate(sec.body):
                new = spec_refs.fence_update(fence, line)
                fenced = fence is not None or new is not None
                fence = new
                if not fenced:
                    out.append((sec.first + i, line))
            return out
    return None


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

def parse_ledger(text: str) -> Ledger:
    seeds: List[Seed] = []
    entries: List[Entry] = []
    problems: List[str] = []
    seed_lines = _section_lines(text, "Seeds")
    read_lines = _section_lines(text, "Read")
    if seed_lines is None:
        problems.append("ledger_no_seeds_section L0 -")
    if read_lines is None:
        problems.append("ledger_no_read_section L0 -")
    for lineno, line in seed_lines or []:
        if not _BULLET_RE.match(line):
            continue
        spans = _spans(line)
        ref = _first_ref(spans, lineno, 1)
        if not spans or ref is None:
            problems.append("ledger_bad_seed L%d %s" % (lineno, line.strip()))
            continue
        pm = _PASS_RE.search(line)
        source = line.rsplit("—", 1)[-1].strip() if "—" in line else ""
        seeds.append(Seed(spans[0], ref, int(pm.group(1)) if pm else 1, source, lineno))
    current: Optional[Entry] = None
    for lineno, line in read_lines or []:
        h = _H3_RE.match(line)
        if h:
            spans = _spans(line)
            ref = _first_ref(spans, lineno, 1)
            if not spans or ref is None:
                problems.append("ledger_bad_entry L%d %s" % (lineno, line.strip()))
                current = None
                continue
            current = Entry(spans[0], ref, [], lineno)
            entries.append(current)
            continue
        if not _BULLET_RE.match(line) or not line.strip():
            continue
        if current is None:
            problems.append("ledger_edge_outside_entry L%d %s" % (lineno, line.strip()))
            continue
        current.edges.append(_parse_edge(line, lineno))
    for entry in entries:
        for edge in entry.edges:
            if edge.kind == "bad":
                problems.append("ledger_bad_edge L%d %s" % (edge.line, edge.reason))
    return Ledger(seeds, entries, problems)


def _split_arrow(body: str) -> Optional[Tuple[str, str]]:
    """(left, right) around the first `→`/`->` outside code spans (`$this->save` is a name, not an arrow)."""
    masked = list(body)
    for s, e, _c in spec_refs.code_spans(body):
        masked[s:e] = ["x"] * (e - s)
    m = _ARROW_RE.search("".join(masked))
    return (body[:m.start()], body[m.end():]) if m else None


def _parse_edge(line: str, lineno: int) -> Edge:
    body = _BULLET_RE.sub("", line, count=1)
    parts = _split_arrow(body)
    if parts is None:
        return Edge("", "bad", None, line.strip(), lineno)
    left, right = parts
    names = _spans(left)
    name = names[0] if names else left.strip().strip("*")
    if not name:
        return Edge("", "bad", None, line.strip(), lineno)
    rspans = _spans(right)
    ref = _first_ref(rspans, lineno)
    if ref is not None:
        return Edge(name, "def", ref, "", lineno)
    word = right.strip().strip("`*").lower()
    if word.startswith("external"):
        return Edge(name, "external", None, "", lineno)
    if word.startswith("ignored"):
        reason = re.sub(r"^ignored\s*(?:[—–:-]\s*)?", "", right.strip().strip("`*"), flags=re.IGNORECASE)
        if not reason.strip():
            return Edge(name, "bad", None, "ignored without a reason: " + line.strip(), lineno)
        return Edge(name, "ignored", None, reason.strip(), lineno)
    return Edge(name, "bad", None, line.strip(), lineno)


class Resolver:
    """Resolves `Ref`s to real files once, with their line counts."""

    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)
        self._cache: Dict[str, Tuple[Optional[str], int, int]] = {}

    def file(self, path: str) -> Tuple[Optional[str], int, int]:
        """(realpath or None, candidate count, line count)."""
        if path not in self._cache:
            cands = spec_refs.resolve(path, self.root)
            if not cands:
                self._cache[path] = (None, 0, 0)
            else:
                lines = spec_refs.read_lines(cands[0])
                self._cache[path] = (os.path.realpath(cands[0]), len(cands), len(lines) if lines is not None else 0)
        return self._cache[path]

    def check(self, ref: Ref) -> Optional[str]:
        real, _n, count = self.file(ref.path)
        if real is None:
            return spec_refs.REASON_FILE_MISSING
        last = ref.end if ref.end is not None else ref.start
        if ref.start < 1 or last < ref.start or last > count:
            return spec_refs.REASON_LINE_OOB
        return None

    def rel(self, real: str) -> str:
        return os.path.relpath(real, os.path.realpath(self.root)).replace(os.sep, "/")


def ledger_ref_problems(ledger: Ledger, res: Resolver) -> List[str]:
    """Citation problems in the ledger: unresolved files, lines out of range, ambiguous paths (advisory: `note`)."""
    out: List[str] = []
    refs: List[Ref] = [s.ref for s in ledger.seeds] + [e.body for e in ledger.entries]
    refs += [ed.target for e in ledger.entries for ed in e.edges if ed.target is not None]
    for ref in refs:
        reason = res.check(ref)
        if reason:
            out.append("ledger_%s L%d %s" % (reason, ref.line, _ref_text(ref)))
        elif res.file(ref.path)[1] > 1:
            out.append("note ledger_ambiguous L%d %s (first candidate used)" % (ref.line, _ref_text(ref)))
    return out


def _ref_text(ref: Ref) -> str:
    return "%s:%d%s" % (ref.path, ref.start, "-%d" % ref.end if ref.end is not None else "")


# ---------------------------------------------------------------------------
# Closure
# ---------------------------------------------------------------------------

def _key(ref: Ref, res: Resolver, entries: Optional[List[Entry]] = None) -> Optional[Tuple[str, int]]:
    """(realpath, line); with `entries`, a line inside an entry's body is keyed by the entry's first line, so an edge
    to a decorator or a body line and a Coverage row at the definition line name the same item."""
    real = res.file(ref.path)[0]
    if not real:
        return None
    if entries:
        entry = entry_for((real, ref.start), entries, res)
        if entry is not None:
            return (real, entry.body.start)
    return (real, ref.start)


def entry_for(key: Tuple[str, int], entries: List[Entry], res: Resolver) -> Optional[Entry]:
    best: Optional[Entry] = None
    best_span = 0
    for entry in entries:
        real = res.file(entry.body.path)[0]
        end = entry.body.end if entry.body.end is not None else entry.body.start
        if real == key[0] and entry.body.start <= key[1] <= end:
            span = end - entry.body.start
            if best is None or span < best_span:
                best, best_span = entry, span
    return best


def compute_closure(ledger: Ledger, res: Resolver, max_depth: int = DEFAULT_DEPTH,
                    cap: int = DEFAULT_CAP) -> List[Node]:
    # key, symbol, rel path, line, depth, entry (found from the line as written: two entries may share a start)
    order: List[Tuple[Tuple[str, int], str, str, int, int, Optional[Entry]]] = []
    seen: Set[Tuple[str, int]] = set()
    queue: List[int] = []

    def entry_at(ref: Ref) -> Optional[Entry]:
        real = res.file(ref.path)[0]
        return entry_for((real, ref.start), ledger.entries, res) if real else None

    for seed in ledger.seeds:
        key = _key(seed.ref, res, ledger.entries)
        if key is None or key in seen:
            continue
        seen.add(key)
        order.append((key, seed.symbol, seed.ref.path, seed.ref.start, 0, entry_at(seed.ref)))
        queue.append(len(order) - 1)
    head = 0
    while head < len(queue):
        key, _sym, _rel, _line, depth, entry = order[queue[head]]
        head += 1
        if depth >= max_depth or entry is None:
            continue
        for edge in entry.edges:
            if edge.kind != "def" or edge.target is None:
                continue
            ckey = _key(edge.target, res, ledger.entries)
            if ckey is None or ckey in seen:
                continue
            seen.add(ckey)
            order.append((ckey, edge.name, edge.target.path, edge.target.start, depth + 1, entry_at(edge.target)))
            queue.append(len(order) - 1)
    nodes: List[Node] = []
    for i, (key, sym, rel, line, depth, entry) in enumerate(order):
        nodes.append(Node(key, sym, rel, line, depth, i < cap, entry))
    return nodes


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

_STATUS_RE = re.compile(r"[—–-]\s*(read|excluded|not covered:\s*over cap)\b", re.IGNORECASE)


def parse_coverage(report: str) -> Optional[List[CoverageRow]]:
    """Coverage bullets of the report; None when there is no `## Coverage` section."""
    lines = _section_lines(report, "Coverage")
    if lines is None:
        return None
    rows: List[CoverageRow] = []
    for lineno, line in lines:
        if not _BULLET_RE.match(line):
            continue
        spans = spec_refs.code_spans(line)
        if not spans:
            continue
        ref = None
        ref_end = 0
        for _s, e, content in spans[1:]:
            ref = _ref(content, lineno)
            if ref:
                ref_end = e
                break
        if ref is None:
            continue
        m = _STATUS_RE.search(line, ref_end)
        word = m.group(1).lower() if m else "unknown"
        status = "over cap" if word.startswith("not covered") else word
        rows.append(CoverageRow(spans[0][2], ref, status, line, lineno))
    return rows


def coverage_by_key(rows: List[CoverageRow], res: Resolver,
                    entries: Optional[List[Entry]] = None) -> Dict[Tuple[str, int], CoverageRow]:
    out: Dict[Tuple[str, int], CoverageRow] = {}
    for row in rows:
        key = _key(row.ref, res, entries)
        if key is not None and key not in out:
            out[key] = row
    return out


# ---------------------------------------------------------------------------
# Definition index
# ---------------------------------------------------------------------------

CTAGS_KINDS = frozenset({
    "function", "method", "class", "struct", "interface", "trait", "enum", "macro", "func", "subroutine",
    "procedure", "singletonMethod", "constructor", "generator", "type", "typedef", "module", "object",
    "record", "protocol", "fn", "implementation",
})

NON_SOURCE_EXT = frozenset({
    ".md", ".markdown", ".txt", ".rst", ".adoc", ".json", ".lock", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".conf", ".csv", ".tsv", ".svg", ".xml", ".map", ".log", ".env", ".snap", ".pem", ".crt",
})

_MODS = (r"(?:(?:export|default|public|private|protected|internal|static|final|abstract|override|virtual|async|"
         r"synchronized|sealed|extern|unsafe|new|open|suspend|inline|partial|declare|data|pub(?:\([^)]*\))?|"
         r"readonly|const|operator|infix|tailrec|external|actual|expect)\s+)*")
_NAME = r"(?P<n>[A-Za-z_$][\w$]*[!?]?)"
_CONTROL = frozenset({
    "if", "for", "while", "switch", "catch", "function", "return", "else", "do", "try", "with", "foreach",
    "elseif", "elif", "using", "lock", "fixed", "synchronized", "until", "unless", "when", "match", "new",
    "throw", "await", "yield", "typeof", "sizeof", "defer", "go", "select", "case", "assert", "print",
})
DEF_PATTERNS = [
    re.compile(r"^\s*" + _MODS + r"function\s*\*?\s*&?\s*" + _NAME),                      # JS, PHP
    re.compile(r"^\s*" + _MODS + r"(?:def|fn|fun|func|sub|proc)\s+(?:\([^)]*\)\s*)?(?:<[^>]*>\s*)?"
               r"(?:self\.|[A-Za-z_][\w]*\.)?" + _NAME),                                  # Py, Ruby, Rust, Kt, Go
    re.compile(r"^\s*" + _MODS + r"(?:class|interface|struct|trait|enum|record|module|object|protocol|type|"
               r"impl)\s+" + _NAME),                                                      # types
    re.compile(r"^\s*" + _MODS + r"(?:const|let|var|val)\s+" + _NAME +
               r"\s*(?::[^=]+)?=\s*(?:async\s+)?(?:function\b|\([^)]*\)\s*(?::[^=]+)?=>|[A-Za-z_$][\w$]*\s*=>)"),
    re.compile(r"^\s*" + _NAME + r"\s*[:=]\s*(?:async\s+)?(?:function\b|\([^)]*\)\s*(?::[^=]+)?=>)"),
    re.compile(r"^\s*" + _MODS.replace(")*", ")+", 1) + r"(?:[\w<>\[\],.?*&]+\s+)?" + _NAME +
               r"\s*(?:<[^>]*>)?\s*\("),                                                   # modifier-led methods
    re.compile(r"^\s*(?:(?:async|static|get|set|\*)\s+)*" + _NAME +
               r"\s*\([^;]*\)\s*(?::\s*[^={;]+)?\{\s*$"),                                  # `X(…) {` method heads
    re.compile(r"^\s*[\w<>\[\],.*&?]+\s+" + _NAME + r"\s*\([^;]*\)\s*\{\s*$"),            # `T X(…) {`
]


class Index(NamedTuple):
    kind: str  # "ctags" | "regex" | "none"
    defs: Dict[str, List[Tuple[str, int]]]  # name -> [(realpath, line)]
    note: str
    ends: Dict[Tuple[str, int], int] = {}  # (realpath, line) -> last line, when the index knows it (ctags `end`)


def _scopes(root: str) -> Tuple[List[str], List[str]]:
    """(scope dirs, excluded dirs), absolute; [root] when the quality profile sets no search scopes."""
    scopes: List[str] = []
    excluded: List[str] = []
    try:
        profile = quality_profile.load(os.path.join(root, ".claude", quality_profile.BINDING_NAME))
    except (quality_profile.ProfileError, OSError):
        profile = {}
    for s in profile.get("searchScopes") or []:
        if isinstance(s, str) and os.path.isdir(os.path.join(root, s)):
            scopes.append(os.path.join(root, s))
    for d in profile.get("generatedDirs") or []:
        if isinstance(d, str):
            excluded.append(os.path.normpath(os.path.join(root, d)))
    return (scopes or [root]), excluded


def _source_files(root: str) -> List[str]:
    scopes, excluded = _scopes(root)
    out: List[str] = []
    seen: Set[str] = set()
    for scope in scopes:
        for rel in spec_refs._files_under(scope):
            full = os.path.normpath(os.path.join(scope, rel))
            if full in seen or any(full == e or full.startswith(e + os.sep) for e in excluded):
                continue
            seen.add(full)
            if os.path.splitext(full)[1].lower() in NON_SOURCE_EXT or os.path.basename(full).startswith("."):
                continue
            out.append(full)
    return out


def _is_text(path: str) -> bool:
    try:
        if os.path.getsize(path) > MAX_INDEX_FILE_BYTES:
            return False
        with open(path, "rb") as handle:
            return b"\0" not in handle.read(4096)
    except OSError:
        return False


def regex_index(root: str) -> Index:
    defs: Dict[str, List[Tuple[str, int]]] = {}
    files = 0
    for path in _source_files(root):
        if not _is_text(path):
            continue
        lines = spec_refs.read_lines(path)
        if lines is None:
            continue
        files += 1
        real = os.path.realpath(path)
        for lineno, line in enumerate(lines, 1):
            if len(line) > MAX_INDEX_LINE_CHARS or _comment_line(line):
                continue
            for pat in DEF_PATTERNS:
                m = pat.match(line)
                if m:
                    name = m.group("n").rstrip("!?")
                    if name not in _CONTROL:
                        defs.setdefault(name, []).append((real, lineno))
                    break
    return Index("regex", defs, "regex index: %d files, %d names (missed references are advisory)" % (files, len(defs)))


CTAGS_NAMES = ("ctags", "uctags", "universal-ctags")


def ctags_candidates() -> List[str]:
    """Every executable named in CTAGS_NAMES on PATH: PATH order, then name order within a directory; one per real
    file. Another ctags (Exuberant, BSD/Xcode) may come first on PATH."""
    out: List[str] = []
    seen: Set[str] = set()
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        if not folder:
            continue
        for name in CTAGS_NAMES:
            exe = shutil.which(name, path=folder)
            exe = os.path.abspath(exe) if exe else None  # ctags_index runs it with cwd=root
            if exe and os.path.realpath(exe) not in seen:
                seen.add(os.path.realpath(exe))
                out.append(exe)
    return out


def _is_universal(exe: str) -> bool:
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, encoding="utf-8", errors="replace",
                             timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return "universal ctags" in out.lower()


def universal_ctags() -> Optional[str]:
    """The first of ctags_candidates() whose `--version` names Universal Ctags, or None."""
    for exe in ctags_candidates():
        if _is_universal(exe):
            return exe
    return None


def ctags_index(root: str, exe: str) -> Index:
    scopes, excluded = _scopes(root)
    cmd = [exe, "-R", "--output-format=json", "--fields=+nKSe", "--fields=-P", "-f", "-"]
    cmd += ["--exclude=%s" % d for d in sorted(spec_refs.PRUNED_DIRS)]
    cmd += ["--exclude=%s" % os.path.relpath(e, root) for e in excluded]
    cmd += [os.path.relpath(s, root) or "." for s in scopes]
    try:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, encoding="utf-8", errors="replace",
                              timeout=CTAGS_TIMEOUT)
    except subprocess.SubprocessError as exc:
        raise OSError("ctags failed: %s" % exc) from exc
    if proc.returncode != 0:
        raise OSError("ctags failed (%d): %s" % (proc.returncode, proc.stderr.strip()[:300]))
    defs: Dict[str, List[Tuple[str, int]]] = {}
    ends: Dict[Tuple[str, int], int] = {}
    for raw in proc.stdout.splitlines():
        try:
            tag = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(tag, dict) or tag.get("_type") != "tag" or (tag.get("kind") not in CTAGS_KINDS and not tag.get("signature")):
            continue
        name, path, line = tag.get("name"), tag.get("path"), tag.get("line")
        if not isinstance(name, str) or not isinstance(path, str) or not isinstance(line, int):
            continue
        loc = (os.path.realpath(os.path.join(root, path)), line)
        defs.setdefault(name.rstrip("!?"), []).append(loc)
        end = tag.get("end")
        if isinstance(end, int) and end >= line:
            ends[loc] = max(end, ends.get(loc, end))
    if not defs:
        return Index("none", {}, "ctags found no definitions: missed-reference check skipped")
    return Index("ctags", defs, "ctags index: %d names (missed references are blocking); %s" % (len(defs), exe), ends)


def build_index(root: str, mode: str = "auto") -> Index:
    """Raises OSError when `ctags` is forced and Universal Ctags is missing or fails."""
    root = os.path.abspath(root)
    if mode == "none":
        return Index("none", {}, "no index (--index none): missed-reference check skipped")
    fallback = ""
    if mode in ("auto", "ctags"):
        exe = universal_ctags()
        if exe:
            try:
                return ctags_index(root, exe)
            except OSError as exc:
                if mode == "ctags":
                    raise
                fallback = "; fallback: %s" % exc
        else:
            others = ctags_candidates()
            checked = " (checked: %s)" % ", ".join(others) if others else ""
            if mode == "ctags":
                raise OSError("Universal Ctags not found on PATH%s (`--version` must name it)" % checked)
            fallback = "; no Universal Ctags on PATH%s" % checked
    idx = regex_index(root)
    if not idx.defs:
        return Index("none", {}, "no definitions found by the regex index: missed-reference check skipped" + fallback)
    return Index(idx.kind, idx.defs, idx.note + fallback)


# ---------------------------------------------------------------------------
# Body tokens
# ---------------------------------------------------------------------------

_LINE_COMMENT_RE = re.compile(r"^\s*(?://|#(?![\[{!])|--|\*(?:\s|/|$)|;;)")
_STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`')
_INTERP_RE = re.compile(r"\{([^{}]*)\}")  # `${x}`, `#{x}`, `{x}`: the code inside a string is kept
_TRAILING_RE = re.compile(r"\s//.*$|^//.*$|\s#(?![\[{]).*$|\s--\s.*$")
_INLINE_BLOCK_RE = re.compile(r"/\*.*?\*/")
_TRIPLE_RE = re.compile(r'"""|\'\'\'')
_MEMBER_TAILS = (".", "->", "::", "?.")


class Token(NamedTuple):
    name: str
    line: int  # first use
    member_only: bool  # every use follows `.`, `->`, `::` or `?.` (a method or field of some object)


def _comment_line(line: str) -> bool:
    return bool(_LINE_COMMENT_RE.match(line))


def _strip_string(m: "re.Match[str]") -> str:
    return " " + " ".join(_INTERP_RE.findall(m.group(0))) + " "


def body_tokens(lines: List[str], start: int, end: int, own_name: str = "") -> List[Token]:
    """Identifiers of lines start..end in order of first use, with comments (line, trailing, `/* … */` blocks,
    triple-quoted blocks) and string literals (double, single, backtick) dropped; code interpolated into a string
    (`{…}`) is kept. The first occurrence of `own_name` (the definition's own name on its head) is not a use.
    Identifiers shorter than 2 characters are skipped. Single-quote pairs are read as strings (a Rust lifetime
    `'a … 'b` on one line hides what lies between)."""
    order: List[str] = []
    first: Dict[str, int] = {}
    bare: Set[str] = set()
    in_triple = False
    in_block = False
    for lineno in range(start, min(end, len(lines)) + 1):
        line = lines[lineno - 1]
        if in_block:
            close = line.find("*/")
            if close < 0:
                continue
            line, in_block = line[close + 2:], False
        marks = len(_TRIPLE_RE.findall(line))
        if in_triple:
            if marks % 2 == 1:
                in_triple = False
            continue
        if marks % 2 == 1:
            in_triple = True
            line = _TRIPLE_RE.split(line)[0]
        if line.lstrip().startswith("/*"):
            close = line.find("*/")
            if close < 0:
                in_block = True
                continue
            line = line[close + 2:]
        if _comment_line(line):
            continue
        line = _INLINE_BLOCK_RE.sub(" ", line)  # before strings: `/* it's */` holds no string
        line = _STRING_RE.sub(_strip_string, line)
        line = _TRAILING_RE.sub(" ", line)  # before looking for `/*`: `// joins root/*` opens nothing
        opened = line.find("/*")
        if opened >= 0:
            line, in_block = line[:opened], True
        for m in _IDENT_RE.finditer(line):
            tok = m.group(0)
            if len(tok) < 2 or tok[0].isdigit():
                continue
            member = line[:m.start()].rstrip().endswith(_MEMBER_TAILS)
            if own_name and tok == own_name and not member:  # `@router.get` above `def get` is not the head
                own_name = ""
                continue
            if tok not in first:
                first[tok] = lineno
                order.append(tok)
            if not member:
                bare.add(tok)
    return [Token(t, first[t], t not in bare) for t in order]
