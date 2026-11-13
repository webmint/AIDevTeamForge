"""Shared helpers for the research coverage checks (closure_check.py, research_lint.py).

Not a CLI. Stdlib only; Python 3.9+. Nothing here knows a programming language: the research runner reads the code
and writes the ledger; this module parses the ledger, computes the closure over its edges, builds a definition index
and parses the report's `## Coverage` section.

Ledger (`research/<report>-ledger.md`):
  ## Seeds
  - `<symbol>` `<path:N>` — pass <1|2> — <reason> [<role>]
  ## Read
  ### `<symbol>` `<path:N-M>` [<role>]   the body the runner read (N = the definition line)
  - `<callee>` → `<path:N>` [<role>]      a repository definition the body calls or references (role optional)
  - `<callee>` → external                 a library or framework symbol
  - `<token>` → ignored — <reason>        a token in the body that is not a reference
  ## Excluded                             optional: items the runner will exclude, before the report exists
  - `<symbol>` `<path:N>` — <reason>      (the report's Coverage repeats them as `excluded` rows)
`->` is accepted for `→`. A `### ` entry with a single `path:N` covers that line only. Roles (outside code spans):
`[access]` (authorisation or scope path), `[data]` (read/write path: queries, keys, path builders, normalisers),
`[other]`, `[container]` (a class or module body); required on seeds and entries. Seed reasons that name a seed kind:
`duplicate …` / `facet 9`, `caller of …`, `sibling of …`, `test infra` / `facet 8`.

Closure: breadth-first from every seed over the edges whose target is a `path:N`. An edge target (or a seed) is a
node keyed by (resolved file, line); its ledger entry is the narrowest non-container `### ` entry in the same file
whose range contains the line (a container entry keys only its own head line, so its members stay items of their
own). Depth = distance to the nearest seed; nodes at depth < max_depth are expanded through their entry. A
container's entry is expanded at any depth up to max_depth, and its members stand at the container's own depth.
An item's role is the strongest of its tags (access > data > other);
`container` (a tag, or a container kind in the index) marks a container. Budget (`apply_budget`): items at depth <
max_depth and `access`/`data` items are always in; depth-max_depth `other` items share a line budget of `share` ×
the depth < max_depth entry lines (containers left out), filled smallest body first; the rest are `over budget`.
Containers cost no budget; below max_depth one needs an entry (its members as edges) or an exclusion.

Coverage (`## Coverage` in the report), one bullet per closure item:
  - `<symbol>` `<path:N>` — read — `<path:N-M>` `<verbatim quote>` [<found by>]
  - `<symbol>` `<path:N>` — excluded — <reason>
  - `<symbol>` `<path:N>` — not covered: over budget        (`over cap`, from 1.37.1-step3, is read the same)
A row is matched to a closure item by its first `path:N` span (the definition), resolved like the ledger's.

Body ends (`item_end`): the ctags `end` field when the index has it, else `body_end`'s language-neutral rule: brace
balance from the head, else indentation, else the head line alone; `uncertain` when none applies.

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
from collections import deque
from typing import Deque, Dict, List, NamedTuple, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)
import spec_refs  # noqa: E402

DEFAULT_DEPTH = 2
DEFAULT_BUDGET_SHARE = 0.5
CTAGS_TIMEOUT = 300
ROLES = ("access", "data", "other", "container")
_ROLE_RANK = {"access": 3, "data": 2, "other": 1}
SEED_KINDS = ("duplicate", "caller", "sibling", "test infra")
UNCERTAIN_LINES = 30  # an `uncertain` body end shows at most this many lines
MAX_INDEX_FILE_BYTES = 1_000_000
MAX_INDEX_LINE_CHARS = 2000  # minified or generated lines: skipped (the method-head pattern is slow on them)

_ARROW_RE = re.compile(r"\s*(?:→|->)\s*")
_PASS_RE = re.compile(r"\bpass\s*([12])\b", re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[-*+]\s+")
_H3_RE = re.compile(r"^ {0,3}###\s+(.*)$")
_IDENT_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_NAME_SPLIT_RE = re.compile(r"::|->|[.#\\/]")
_ROLE_RE = re.compile(r"\[(access|data|other|container)\]", re.IGNORECASE)
_SEED_REASON_RE = re.compile(r"\bpass\s*[12]\s*[—–-]+\s*(.*)$", re.IGNORECASE)


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
    role: str = ""  # "" when the edge carries no role tag


class Entry(NamedTuple):
    symbol: str
    body: Ref
    edges: List[Edge]
    line: int
    role: str = ""


class Seed(NamedTuple):
    symbol: str
    ref: Ref
    pass_no: int
    source: str  # the reason after `pass N —`, role tag removed
    line: int
    role: str = ""
    kind: str = ""  # one of SEED_KINDS, or ""


class Ledger(NamedTuple):
    seeds: List[Seed]
    entries: List[Entry]
    problems: List[str]  # "<code> L<line> <detail>"
    excluded: List[Tuple[Ref, str]] = []  # `## Excluded`: (definition, reason), planned before the report exists


class Node(NamedTuple):
    key: Tuple[str, int]  # (realpath, line)
    symbol: str
    rel: str  # path as first written
    line: int
    depth: int
    in_cap: bool  # in budget (apply_budget); True straight out of compute_closure
    entry: Optional[Entry]
    role: str = "other"  # access | data | other (the strongest tag)
    container: bool = False
    size: int = 0  # body lines, set by apply_budget for the items it sizes


class Budget(NamedTuple):
    share: float
    base: int  # body lines of the depth < max_depth entries, containers left out
    limit: int  # int(share * base)
    used: int  # lines of the depth-max_depth `other` items kept in
    over: int  # items over budget


class CoverageRow(NamedTuple):
    symbol: str
    ref: Ref
    status: str  # "read" | "excluded" | "over budget" | "unknown"
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
        role = role_tag(line)
        rm = _SEED_REASON_RE.search(_masked(line))
        if rm:
            source = _ROLE_RE.sub("", line[rm.start(1):]).strip()
        else:  # no `pass N —`: the text after the first dash past the path span
            cspans = spec_refs.code_spans(line)
            tail = line[cspans[1][1]:] if len(cspans) > 1 else ""
            dash = re.search(r"[—–]", tail)
            source = _ROLE_RE.sub("", tail[dash.end():]).strip() if dash else ""
        if not role:
            problems.append("ledger_no_role L%d %s" % (lineno, line.strip()))
        seeds.append(Seed(spans[0], ref, int(pm.group(1)) if pm else 1, source, lineno, role, seed_kind(source)))
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
            role = role_tag(line)
            if not role:
                problems.append("ledger_no_role L%d %s" % (lineno, line.strip()))
            current = Entry(spans[0], ref, [], lineno, role)
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
    excluded: List[Tuple[Ref, str]] = []
    for lineno, line in _section_lines(text, "Excluded") or []:
        if not _BULLET_RE.match(line):
            continue
        ref = _first_ref(_spans(line), lineno, 1)
        dash = list(re.finditer(r"[—–]|\s-\s", _masked(line)))
        reason = line[dash[-1].end():].strip() if dash else ""
        if ref is None or not reason:
            problems.append("ledger_bad_exclusion L%d %s" % (lineno, line.strip()))
            continue
        excluded.append((ref, reason))
    return Ledger(seeds, entries, problems, excluded)


def _masked(text: str) -> str:
    """`text` with every code span replaced by `x`s of the same length (positions kept)."""
    masked = list(text)
    for s, e, _c in spec_refs.code_spans(text):
        masked[s:e] = ["x"] * (e - s)
    return "".join(masked)


def role_tag(line: str) -> str:
    """The first `[access|data|other|container]` tag outside code spans, lowercased; "" when none."""
    m = _ROLE_RE.search(_masked(line))
    return m.group(1).lower() if m else ""


def seed_kind(source: str) -> str:
    """The SEED_KINDS member a seed reason names (`facet 9` is a duplicate, `facet 8` test infra), else ""."""
    low = source.strip().lower()
    if low.startswith("duplicate") or re.match(r"facet\s*9\b", low):
        return "duplicate"
    if low.startswith("caller"):
        return "caller"
    if low.startswith("sibling"):
        return "sibling"
    if low.startswith(("test infra", "test-infra")) or re.match(r"facet\s*8\b", low):
        return "test infra"
    return ""


def _split_arrow(body: str) -> Optional[Tuple[str, str]]:
    """(left, right) around the first `→`/`->` outside code spans (`$this->save` is a name, not an arrow)."""
    m = _ARROW_RE.search(_masked(body))
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
        return Edge(name, "def", ref, "", lineno, role_tag(right))
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
    refs += [ref for ref, _reason in ledger.excluded]
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

Key = Tuple[str, int]


def is_container_entry(entry: Entry, res: Resolver, containers: Set[Key] = frozenset()) -> bool:
    real = res.file(entry.body.path)[0]
    return entry.role == "container" or (real, entry.body.start) in containers


def _key(ref: Ref, res: Resolver, entries: Optional[List[Entry]] = None,
         containers: Set[Key] = frozenset()) -> Optional[Key]:
    """(realpath, line); with `entries`, a line inside an entry's body is keyed by the entry's first line, so an edge
    to a decorator or a body line and a Coverage row at the definition line name the same item."""
    real = res.file(ref.path)[0]
    if not real:
        return None
    if entries:
        entry = entry_for((real, ref.start), entries, res, containers)
        if entry is not None:
            return (real, entry.body.start)
    return (real, ref.start)


def entry_for(key: Key, entries: List[Entry], res: Resolver, containers: Set[Key] = frozenset()) -> Optional[Entry]:
    """The narrowest entry whose range holds the line; a container entry only for its own head line."""
    best: Optional[Entry] = None
    best_span = 0
    for entry in entries:
        real = res.file(entry.body.path)[0]
        end = entry.body.end if entry.body.end is not None else entry.body.start
        if real != key[0] or not entry.body.start <= key[1] <= end:
            continue
        if key[1] != entry.body.start and is_container_entry(entry, res, containers):
            continue
        span = end - entry.body.start
        if best is None or span < best_span:
            best, best_span = entry, span
    return best


def _stronger(a: str, b: str) -> str:
    return a if _ROLE_RANK.get(a, 0) >= _ROLE_RANK.get(b, 0) else b


def compute_closure(ledger: Ledger, res: Resolver, max_depth: int = DEFAULT_DEPTH,
                    containers: Set[Key] = frozenset()) -> List[Node]:
    """Closure items in depth then discovery order, all `in_cap` (apply_budget sets it). `containers`: definition
    keys the index knows as container kinds."""
    # key -> [symbol, rel path, line, depth, entry, discovery index]; entry is found from the line as written (two
    # entries may share a start). 0-1 breadth-first: a container's members stand at its own depth, so they go to the
    # front of the queue; a node reached again at a smaller depth is lowered and expanded again.
    info: Dict[Key, list] = {}
    queue: Deque[Tuple[Key, int]] = deque()
    tags: Dict[Key, Set[str]] = {}

    def entry_at(ref: Ref) -> Optional[Entry]:
        real = res.file(ref.path)[0]
        return entry_for((real, ref.start), ledger.entries, res, containers) if real else None

    def tag(key: Key, role: str) -> None:
        if role:
            tags.setdefault(key, set()).add(role)

    def is_container(key: Key, entry: Optional[Entry]) -> bool:
        return key in containers or "container" in tags.get(key, ()) or (
            entry is not None and entry.body.start == key[1] and is_container_entry(entry, res, containers))

    for seed in ledger.seeds:
        key = _key(seed.ref, res, ledger.entries, containers)
        if key is None:
            continue
        tag(key, seed.role)
        if key not in info:
            info[key] = [seed.symbol, seed.ref.path, seed.ref.start, 0, entry_at(seed.ref), len(info)]
            queue.append((key, 0))
    while queue:
        key, depth = queue.popleft()
        if info[key][3] != depth:
            continue  # lowered since it was queued
        entry = info[key][4]
        container = is_container(key, entry)
        if entry is None or (depth >= max_depth and not container):
            continue
        child_depth = depth if container else depth + 1
        for edge in entry.edges:
            if edge.kind != "def" or edge.target is None:
                continue
            ckey = _key(edge.target, res, ledger.entries, containers)
            if ckey is None:
                continue
            tag(ckey, edge.role)
            if ckey not in info:
                info[ckey] = [edge.name, edge.target.path, edge.target.start, child_depth, entry_at(edge.target),
                              len(info)]
            elif child_depth < info[ckey][3]:
                info[ckey][3] = child_depth
            else:
                continue
            if child_depth == depth:
                queue.appendleft((ckey, child_depth))
            else:
                queue.append((ckey, child_depth))
    order = sorted(((k, v[0], v[1], v[2], v[3], v[4], v[5]) for k, v in info.items()), key=lambda o: (o[4], o[6]))
    nodes: List[Node] = []
    for key, sym, rel, line, depth, entry, _i in order:
        roles = set(tags.get(key, set()))
        if entry is not None:
            roles.add(entry.role)
        container = "container" in roles or key in containers or (
            entry is not None and is_container_entry(entry, res, containers) and entry.body.start == key[1])
        role = "other"
        for r in roles:
            if r in _ROLE_RANK:
                role = _stronger(r, role)
        nodes.append(Node(key, sym, rel, line, depth, True, entry, role, container))
    return nodes


def _entry_lines(entry: Entry) -> int:
    return (entry.body.end if entry.body.end is not None else entry.body.start) - entry.body.start + 1


def apply_budget(nodes: List[Node], res: Resolver, index: "Index", max_depth: int = DEFAULT_DEPTH,
                 share: float = DEFAULT_BUDGET_SHARE) -> Tuple[List[Node], Budget]:
    """Sets `in_cap` and `size`: depth < max_depth items, `access`/`data` items and containers are in; depth-max_depth
    `other` items are kept smallest first while their lines fit share × the depth < max_depth entry lines."""
    base = 0
    counted: Set[int] = set()
    for node in nodes:
        if node.depth < max_depth and node.entry is not None and not node.container and id(node.entry) not in counted:
            counted.add(id(node.entry))
            base += _entry_lines(node.entry)
    limit = int(share * base)
    sized: List[Tuple[int, int]] = []  # (size, position) of the budgeted items
    out = list(nodes)
    for i, node in enumerate(nodes):
        if node.depth >= max_depth and node.role == "other" and not node.container:
            if node.entry is not None:
                size = _entry_lines(node.entry)
            else:
                size = item_end(node.key[0], node.key[1], index)[0] - node.key[1] + 1
            out[i] = node._replace(size=size)
            sized.append((size, i))
    used, over = 0, 0
    for size, i in sorted(sized):
        if used + size <= limit:
            used += size
        else:
            out[i] = out[i]._replace(in_cap=False)
            over += 1
    return out, Budget(share, base, limit, used, over)


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

_STATUS_RE = re.compile(r"[—–-]\s*(read|excluded|not covered:\s*over (?:budget|cap))\b", re.IGNORECASE)


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
        status = "over budget" if word.startswith("not covered") else word
        rows.append(CoverageRow(spans[0][2], ref, status, line, lineno))
    return rows


def coverage_by_key(rows: List[CoverageRow], res: Resolver, entries: Optional[List[Entry]] = None,
                    containers: Set[Key] = frozenset()) -> Dict[Key, CoverageRow]:
    out: Dict[Key, CoverageRow] = {}
    for row in rows:
        key = _key(row.ref, res, entries, containers)
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
CONTAINER_KINDS = frozenset({
    "class", "struct", "interface", "trait", "enum", "module", "namespace", "package", "object", "record",
    "protocol", "implementation", "union",
})
_TYPE_PATTERN = 2  # DEF_PATTERNS index of the type forms: its matches are containers

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
    containers: Set[Tuple[str, int]] = frozenset()  # definitions of a container kind (class, module, …)

    def names_at(self) -> Dict[Tuple[str, int], str]:
        """(realpath, line) -> the first name defined there."""
        out: Dict[Tuple[str, int], str] = {}
        for name, locs in self.defs.items():
            for loc in locs:
                out.setdefault(loc, name)
        return out


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
    containers: Set[Tuple[str, int]] = set()
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
            for i, pat in enumerate(DEF_PATTERNS):
                m = pat.match(line)
                if m:
                    name = m.group("n").rstrip("!?")
                    if name not in _CONTROL:
                        defs.setdefault(name, []).append((real, lineno))
                        if i == _TYPE_PATTERN:
                            containers.add((real, lineno))
                    break
    return Index("regex", defs, "regex index: %d files, %d names (missed references are advisory)" % (files, len(defs)),
                 {}, containers)


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
    containers: Set[Tuple[str, int]] = set()
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
        if tag.get("kind") in CONTAINER_KINDS:
            containers.add(loc)
        end = tag.get("end")
        if isinstance(end, int) and end >= line:
            ends[loc] = max(end, ends.get(loc, end))
    if not defs:
        return Index("none", {}, "ctags found no definitions: missed-reference check skipped; %s" % exe)
    return Index("ctags", defs, "ctags index: %d names (missed references are blocking); %s" % (len(defs), exe),
                 ends, containers)


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
    return idx._replace(note=idx.note + fallback)


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


# ---------------------------------------------------------------------------
# Body ends
# ---------------------------------------------------------------------------

HEAD_LINES = 8  # a signature may run over this many more lines before its body opens
_CLOSER_RE = re.compile(r"^\s*(?:end\b|[}\])]|fi\b|done\b|esac\b)")


def _indent(line: str) -> int:
    return len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip())


def _code_part(line: str, in_block: bool) -> Tuple[str, bool]:
    """The code of a line for brace counting: comments and string literals dropped; (code, still in a block)."""
    if in_block:
        close = line.find("*/")
        if close < 0:
            return "", True
        line = line[close + 2:]
    if _comment_line(line):
        return "", False
    line = _INLINE_BLOCK_RE.sub(" ", line)
    line = _STRING_RE.sub(" ", line)
    line = _TRAILING_RE.sub(" ", line)
    opened = line.find("/*")
    if opened >= 0:
        return line[:opened], True
    return line, False


def _next_code_line(lines: List[str], after: int) -> int:
    """The first line after `after` (1-based) that is neither blank nor a comment line, or 0."""
    for j in range(after + 1, len(lines) + 1):
        if lines[j - 1].strip() and not _comment_line(lines[j - 1]):
            return j
    return 0


def body_end(lines: List[str], start: int) -> Tuple[int, str]:
    """(last line, how) of the definition whose head is line `start`, without knowing the language:
    `brace` — the first `{` outside parentheses in the head (or its continuation lines) and its matching `}`;
    `indent` — a head ending in `:`, or a head followed by more-indented lines: the lines indented deeper than the
    head, plus a closer (`end`, `}`, `)`) at the head's indentation; `line` — the head alone (`;`-terminated or not
    followed by a deeper line); `uncertain` — the braces never balance (at most UNCERTAIN_LINES are given)."""
    total = len(lines)
    if start < 1 or start > total:
        return start, "uncertain"
    base = _indent(lines[start - 1])
    paren = 0
    in_block = False
    for i in range(start, min(total, start + HEAD_LINES) + 1):
        code, in_block = _code_part(lines[i - 1], in_block)
        for pos, ch in enumerate(code):
            if ch in "([":
                paren += 1
            elif ch in ")]":
                paren -= 1
            elif ch == "{" and paren <= 0:
                return _brace_end(lines, i, code[pos:], in_block, start)
        tail = code.rstrip()
        if paren > 0 or (not tail and i == start):
            continue
        if tail.endswith(":"):
            return _indent_end(lines, i, base)
        if tail.endswith(";"):
            return i, "line"
        opener = _later_opener(lines, i, in_block, base)
        if opener:
            return _brace_end(lines, opener[0], opener[1], opener[2], start)
        nxt = _next_code_line(lines, i)
        if nxt and _indent(lines[nxt - 1]) > base:
            return _indent_end(lines, i, base)
        return i, "line"
    return start, "uncertain"


def _later_opener(lines: List[str], head_end: int, in_block: bool, base: int) -> Optional[Tuple[int, str, bool]]:
    """A body brace on a later line: the first code line within HEAD_LINES that starts with `{` at the head's
    indentation or less (Allman, PHP PSR-12, a C function, a Rust `where` clause before it). It stops at a `;`-ended
    line, a line that closes more braces than it opens, or the head of another definition. (line, code from the
    brace, block state)."""
    for j in range(head_end + 1, min(len(lines), head_end + HEAD_LINES) + 1):
        code, in_block = _code_part(lines[j - 1], in_block)
        stripped = code.strip()
        if not stripped:
            continue
        if stripped.startswith("{"):
            return (j, stripped, in_block) if _indent(lines[j - 1]) <= base else None
        if stripped.endswith(";") or stripped.count("}") > stripped.count("{") or _is_def_head(code):
            return None
    return None


def _is_def_head(code: str) -> bool:
    for pat in DEF_PATTERNS:
        m = pat.match(code)
        if m and m.group("n").rstrip("!?") not in _CONTROL:
            return True
    return False


def _brace_end(lines: List[str], line_no: int, rest: str, in_block: bool, start: int) -> Tuple[int, str]:
    depth = rest.count("{") - rest.count("}")
    if depth <= 0:
        return line_no, "brace"
    for j in range(line_no + 1, len(lines) + 1):
        code, in_block = _code_part(lines[j - 1], in_block)
        depth += code.count("{") - code.count("}")
        if depth <= 0:
            return j, "brace"
    return min(len(lines), start + UNCERTAIN_LINES - 1), "uncertain"


def _indent_end(lines: List[str], head_end: int, base: int) -> Tuple[int, str]:
    """Lines deeper than `base` after the head; a comment line and the lines of a triple-quoted block count as body
    whatever their indentation, when deeper lines follow them."""
    end = head_end
    in_triple = False
    deep_triple = False  # the open triple-quoted block started on a body line
    for j in range(head_end + 1, len(lines) + 1):
        line = lines[j - 1]
        marks = len(_TRIPLE_RE.findall(line))
        if in_triple:
            in_triple = marks % 2 == 0
            if deep_triple:
                end = j
            continue
        if marks % 2 == 1:
            if _indent(line) <= base:
                break  # a block opened at the head's indentation is after the body
            in_triple = deep_triple = True
            end = j
            continue
        if not line.strip() or (_comment_line(line) and _indent(line) <= base):
            continue
        if _indent(line) > base:
            end = j
            continue
        if _indent(line) == base and _CLOSER_RE.match(line):
            end = j
        break
    return end, "indent" if end > head_end else "line"


_LINES_CACHE: Dict[str, Optional[List[str]]] = {}


def file_lines(real: str) -> Optional[List[str]]:
    if real not in _LINES_CACHE:
        _LINES_CACHE[real] = spec_refs.read_lines(real)
    return _LINES_CACHE[real]


def item_end(real: str, line: int, index: Index) -> Tuple[int, str]:
    """(last line, how) of the definition at (real, line): the index's end (`ctags`) or body_end's rule."""
    end = index.ends.get((real, line))
    if end is not None:
        return end, "ctags"
    lines = file_lines(real)
    if lines is None:
        return line, "uncertain"
    return body_end(lines, line)
