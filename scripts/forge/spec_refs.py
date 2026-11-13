"""Shared citation helpers for the spec checks (verify_citations.py, spec_lint.py, spec_paths.py).

Not a CLI. Stdlib only; Python 3.9+.

Citation syntax (one definition): a code span holding `path:N` or `path:N-M`, followed on the same line by an optional
separator (`—`, `–`, `-`, `:`) and the verbatim quote as a code span (any backtick run, CommonMark matching) or in
double quotes ("..." or “...”). A span followed by a quote is a citation whatever the path shape; an unquoted one
needs a `/` or a file extension of letters in the path (so `localhost:3000` and `10.0.0.1:80` are not citations).
`\\|` inside a quote on a table row (a line starting with `|`) is read as `|`. A span followed by an unclosed backtick run is a citation with `unclosed` set.

Path resolution (`resolve`): `<root>/<path>`, then `<SOURCE_ROOT>/<path>` (`quality_profile.source_root`), then every
file under root whose path ends with `/<path>` (or equals it), pruning PRUNED_DIRS and every non-root directory
holding a `.git` FILE (worktree, submodule; a nested `.git` directory is still walked). The first two hits are final;
a suffix search can return several candidates (ambiguous). A candidate whose realpath is outside realpath(root) is
dropped.

Quote window (`check_quote`): the quote and the window are whitespace-normalised (split on whitespace, joined by one
space). `path:N-M` -> the quote is a substring of lines N..M. A single `path:N` -> the quote starts on line N and may
run on up to SINGLE_LINE_WINDOW lines. ` … ` or ` ... ` (spaces on both sides) splits a quote into fragments that
must appear in order inside the window. A leading or trailing ellipsis is dropped. An `...` without spaces stays
literal; when that fails it is retried as a gap, after dropping gap fragments shorter than MIN_FRAGMENT_CHARS
non-space characters (quote_too_short when under MIN_QUOTE_CHARS remain). Failures: quote_empty (empty, whitespace-only or `...`),
quote_too_short (fewer than MIN_QUOTE_CHARS non-space characters in total or MIN_FRAGMENT_CHARS in a fragment),
quote_mismatch, line_oob, range_too_wide (M-N > MAX_RANGE), file_missing.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Dict, Iterator, List, NamedTuple, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)

PRUNED_DIRS = frozenset({".git", "node_modules", "dist", "build", ".next", "coverage", "vendor", "__pycache__",
                         ".venv", "venv", "target", ".tox"})
SINGLE_LINE_WINDOW = 50
MAX_RANGE = 300
MIN_QUOTE_CHARS = 8
MIN_FRAGMENT_CHARS = 3

REASON_FILE_MISSING = "file_missing"
REASON_LINE_OOB = "line_oob"
REASON_QUOTE_MISMATCH = "quote_mismatch"
REASON_QUOTE_EMPTY = "quote_empty"
REASON_QUOTE_TOO_SHORT = "quote_too_short"
REASON_RANGE_TOO_WIDE = "range_too_wide"

_CITE_RE = re.compile(r"^([^\s:`]+):(\d+)(?:-(\d+))?$")
_SEP_RE = re.compile(r"\s*[—–:\-]?\s*")
_DQUOTE_RE = re.compile(r'"([^"]*)"|“([^”]*)”')
_FRAGMENT_SPLIT_RE = re.compile(r" (?:…|\.\.\.) ")


class Citation(NamedTuple):
    line: int  # 1-based line number in the text
    path: str
    start: int
    end: Optional[int]  # None for a single `path:N`
    quote: Optional[str]  # None when unquoted
    unclosed: bool = False  # an unclosed backtick run follows the span: a quote was meant but cannot be read


class Section(NamedTuple):
    title: str  # text after `## `; "" for the preamble before the first `## `
    line: int  # 1-based line of the heading (0 for the preamble)
    first: int  # 1-based line number of body[0]
    body: List[str]  # lines after the heading, up to the next `## `


def normalise(text: str) -> str:
    """Split on whitespace and join with one space."""
    return " ".join(text.split())


def atomic_write(path: str, text: str) -> None:
    """Write `text` (UTF-8, no newline translation) to `path` through a temp file in the same directory and
    os.replace. An existing file keeps its mode; a new one gets 0o666 & ~umask. Creates the directory. Raises OSError
    (the temp file is removed first)."""
    import tempfile
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    try:
        mode = os.stat(path).st_mode & 0o7777
    except OSError:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    fd, tmp = tempfile.mkstemp(prefix=".forge-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_lines(path: str) -> Optional[List[str]]:
    """Lines of a file as an editor counts them (no trailing empty element); None when unreadable."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            raw = handle.read()
    except OSError:
        return None
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

_WALK_CACHE: Dict[str, List[str]] = {}


def _files_under(root: str) -> List[str]:
    root = os.path.abspath(root)
    if root not in _WALK_CACHE:
        found: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            # a `.git` FILE marks a worktree or submodule (pruned); a `.git` directory is a nested repo (walked)
            dirnames[:] = sorted(
                d for d in dirnames
                if d not in PRUNED_DIRS and not os.path.isfile(os.path.join(dirpath, d, ".git")))
            for name in sorted(filenames):
                found.append(os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/"))
        _WALK_CACHE[root] = found
    return _WALK_CACHE[root]


def _inside(path: str, real_root: str) -> bool:
    real = os.path.realpath(path)
    return real == real_root or real.startswith(real_root + os.sep)


def resolve(path: str, root: str) -> List[str]:
    """Absolute candidate files for a cited path: [] missing, one resolved, several ambiguous."""
    root = os.path.abspath(root)
    real_root = os.path.realpath(root)
    if os.path.isabs(path):
        return [path] if os.path.isfile(path) and _inside(path, real_root) else []
    rel = path[2:] if path.startswith("./") else path
    direct = os.path.join(root, rel)
    if os.path.isfile(direct):
        return [direct] if _inside(direct, real_root) else []
    try:
        src = quality_profile.source_root(root)
    except quality_profile.ProfileError:
        src = None
    if src:
        via_src = os.path.join(src, rel)
        if os.path.isfile(via_src):
            return [via_src] if _inside(via_src, real_root) else []
    if not rel or rel.endswith("/"):
        return []
    needle = rel.replace(os.sep, "/")
    return [c for c in (os.path.join(root, f) for f in _files_under(root)
                        if f == needle or f.endswith("/" + needle)) if _inside(c, real_root)]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def code_spans(line: str) -> List[Tuple[int, int, str]]:
    """CommonMark code spans of one line: (start, end, content). A backtick run closes only on a run of equal length;
    an unclosed run is literal text; `\\`` outside a span is a literal backtick."""
    spans: List[Tuple[int, int, str]] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch == "\\" and i + 1 < n and line[i + 1] == "`":
            i += 2
            continue
        if ch != "`":
            i += 1
            continue
        j = i
        while j < n and line[j] == "`":
            j += 1
        run = j - i
        k = j
        close = -1
        while k < n:
            if line[k] == "`":
                m = k
                while m < n and line[m] == "`":
                    m += 1
                if m - k == run:
                    close = k
                    break
                k = m
            else:
                k += 1
        if close < 0:
            i = j
            continue
        content = line[j:close]
        if len(content) >= 2 and content[0] == " " and content[-1] == " " and content.strip(" "):
            content = content[1:-1]
        spans.append((i, close + run, content))
        i = close + run
    return spans


def _quote_after(line: str, end: int, spans: List[Tuple[int, int, str]]) -> Tuple[Optional[str], bool]:
    """(quote or None, unclosed) for the text after a citation span that ends at `end`."""
    pos = _SEP_RE.match(line, end).end()
    for s, _e, content in spans:
        if s == pos:
            return _unescape(content, line), False
    if pos < len(line) and line[pos] == "`":
        return None, True
    m = _DQUOTE_RE.match(line, pos)
    if m:
        return _unescape(m.group(1) if m.group(1) is not None else m.group(2), line), False
    return None, False


def _unescape(quote: str, line: str) -> str:
    """`\\|` is `|` on a markdown table row (a line starting with `|`); elsewhere it stays (`grep 'a\\|b'`)."""
    return quote.replace("\\|", "|") if line.lstrip().startswith("|") else quote


_EXT_RE = re.compile(r"\.[A-Za-z][A-Za-z0-9]*$")


def iter_citations(text: str) -> Iterator[Citation]:
    """Citations in the text, in order (see the module docstring for the syntax)."""
    for lineno, line in enumerate(text.split("\n"), 1):
        if "`" not in line:
            continue
        spans = code_spans(line)
        for _s, e, content in spans:
            m = _CITE_RE.match(content)
            if not m:
                continue
            path = m.group(1)
            quote, unclosed = _quote_after(line, e, spans)
            if quote is None and not unclosed:
                if "/" not in path and not _EXT_RE.search(path):
                    continue
            end = int(m.group(3)) if m.group(3) else None
            yield Citation(lineno, path, int(m.group(2)), end, quote, unclosed)


_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_H2_RE = re.compile(r"^ {0,3}##[ \t]+(.*)$")


def fence_update(fence: Optional[str], line: str) -> Optional[str]:
    """The fence state after `line`: the opening run while inside a fenced code block, else None. A fence closes only
    on a run of the same character at least as long as the opener, with nothing after it. A line is fenced (part of
    the block, its first and last line included) when the state before or after it is not None."""
    m = _FENCE_RE.match(line)
    if fence is None:
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            return m.group(1)
        return None
    if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
        return None
    return fence


def split_sections(markdown: str) -> List[Section]:
    """`## ` level-2 sections in order (the heading may be indented up to 3 spaces); text before the first one is a
    Section with title "" (omitted when empty). A `## ` line inside a fenced code block is not a heading."""
    sections: List[Section] = []
    title, heading, first, body = "", 0, 1, []  # type: str, int, int, List[str]
    fence: Optional[str] = None
    for lineno, line in enumerate(markdown.split("\n"), 1):
        new = fence_update(fence, line)
        fenced = fence is not None or new is not None
        fence = new
        if not fenced:
            m = _H2_RE.match(line)
            if m:
                if heading or any(b.strip() for b in body):
                    sections.append(Section(title, heading, first, body))
                title, heading, first, body = m.group(1).strip(), lineno, lineno + 1, []
                continue
        body.append(line)
    if heading or any(b.strip() for b in body):
        sections.append(Section(title, heading, first, body))
    return sections


# ---------------------------------------------------------------------------
# Checking
# ---------------------------------------------------------------------------

_BARE_ELLIPSIS = ("…", "...")


def _nospace(text: str) -> int:
    return len("".join(text.split()))


def _match(window: str, fragments: List[str], first_len: Optional[int]) -> bool:
    pos = 0
    for index, frag in enumerate(fragments):
        found = window.find(frag, pos)
        if found < 0:
            return False
        # a single `path:N` quote must start on line N: its first fragment starts before first_len
        if index == 0 and first_len is not None and found >= first_len:
            return False
        pos = found + len(frag)
    return True


def check_quote(file_lines: List[str], start: int, end: Optional[int], quote: str) -> Optional[str]:
    """None when the quote verifies, else a REASON_QUOTE_* string. Lines must be in range."""
    norm = normalise(quote)
    if not norm or norm in _BARE_ELLIPSIS:
        return REASON_QUOTE_EMPTY
    while True:  # a leading or trailing ellipsis is dropped
        trimmed = re.sub(r"^(?:…|\.\.\.)\s+|\s+(?:…|\.\.\.)$", "", norm)
        if trimmed == norm:
            break
        norm = trimmed
    if not norm or norm in _BARE_ELLIPSIS:
        return REASON_QUOTE_EMPTY
    fragments = _FRAGMENT_SPLIT_RE.split(norm)
    if any(not f or f in _BARE_ELLIPSIS for f in fragments):
        return REASON_QUOTE_EMPTY
    if _nospace(norm) < MIN_QUOTE_CHARS or any(_nospace(f) < MIN_FRAGMENT_CHARS for f in fragments):
        return REASON_QUOTE_TOO_SHORT
    if end is None:
        window_lines = file_lines[start - 1:start - 1 + SINGLE_LINE_WINDOW]
        first_len = len(normalise(window_lines[0])) if window_lines else 0
    else:
        window_lines = file_lines[start - 1:end]
        first_len = None
    window = normalise("\n".join(window_lines))
    if _match(window, fragments, first_len):
        return None
    if "..." in norm:  # an ellipsis without spaces is literal; when that fails it is a gap
        gaps = [f.strip() for f in norm.split("...") if f.strip()]
        if gaps and gaps != fragments:
            gaps = [g for g in gaps if _nospace(g) >= MIN_FRAGMENT_CHARS]  # tiny fragments match anywhere: dropped
            if sum(_nospace(g) for g in gaps) < MIN_QUOTE_CHARS:
                return REASON_QUOTE_TOO_SHORT
            if _match(window, gaps, first_len):
                return None
    return REASON_QUOTE_MISMATCH


def check_lines(line_count: int, start: int, end: Optional[int]) -> Optional[str]:
    """REASON_LINE_OOB unless 1 <= start <= end <= line_count; REASON_RANGE_TOO_WIDE when end - start > MAX_RANGE."""
    last = start if end is None else end
    if start < 1 or start > last or last > line_count:
        return REASON_LINE_OOB
    if last - start > MAX_RANGE:
        return REASON_RANGE_TOO_WIDE
    return None


def verify_citation(cit: Citation, root: str) -> Tuple[Optional[str], List[str]]:
    """(reason or None, candidates). Several candidates (ambiguous suffix match): passes when any candidate passes;
    when none does, the reason is the first candidate's. A citation without a quote checks the file and lines only."""
    candidates = resolve(cit.path, root)
    if not candidates:
        return REASON_FILE_MISSING, []
    first_reason: Optional[str] = None
    for cand in candidates:
        lines = read_lines(cand)
        if lines is None:
            reason: Optional[str] = REASON_FILE_MISSING
        else:
            reason = check_lines(len(lines), cit.start, cit.end)
            if reason is None and cit.quote is not None:
                reason = check_quote(lines, cit.start, cit.end, cit.quote)
        if reason is None:
            return None, candidates
        if first_reason is None:
            first_reason = reason
    return first_reason, candidates
