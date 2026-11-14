#!/usr/bin/env python3
"""Check the code comments a change adds (TR-27 in `.claude/checklists/task-review.md`).

The comment rule: a doc comment goes on exported or public API only, when its name and types do not say everything,
in at most 2 lines (about 6 for a contract or invariant); no ids, `§`, history, dates, branches, runbooks or quoted
dependency internals in any comment. This script checks the mechanical part; the reviewer judges the rest.

Usage:
  python3 scripts/forge/comment_lint.py [--base <rev>] [--ratio <percent>] [--profile <path>]
  python3 scripts/forge/comment_lint.py stats [--base <rev>] [--profile <path>]

The base defaults to the merge base of HEAD with `integrationRef` (`.claude/quality-profile.json`); without a profile
or an `integrationRef`, pass `--base`. The change is the working tree against the base (committed, uncommitted and
untracked files). Git runs in the source root (`SOURCE_ROOT` in `.claude/project-config.json`, see
quality_profile.py): in a wrapper project the base is a revision of the nested source repository; paths are relative
to the source root.

Which lines are judged: only comment blocks that hold at least one added line. C1-C3 judge only the added lines of
such a block, so an old id in an untouched line is not reported. C4 applies to a doc comment whose lines are all added;
an edited old doc comment over the limit is A6.

Blocking (a TR-27 Critical, unless the reviewer marks the line `false positive: <reason>`):
  C1  an id in a comment: `AC-<n>`; after `spec`/`task`: a number of 1-3 digits; after `plan`, `decision`, `finding`
      or `escape`: an upper-case id like `K14`, `Q-11`, `D1-D5` (the cue word in any case, the id upper-case); the
      project's `ISSUE_KEY_PATTERN` (`project-config.json`) when it starts with a literal prefix (`AP-[0-9]+`; a
      generic Jira or `#<n>` pattern is not used)
  C2  `§` in a comment
  C3  a date next to a provenance word (verified, as of, since, checked, updated, on, until) within 3 words, or a
      branch name (`feature/`, `bugfix/`, `hotfix/` or `release/` with a ticket-like or numbered name, `spec/NNN-`)
  C4  a new doc comment of more than 6 description lines (tag lines such as `@param` and the lines after the first
      tag, and docstring sections such as `Args:`, do not count); in a TypeScript file, `@param {...}` with a type
Advisory (the reviewer judges):
  A1  a doc comment of 3-6 description lines: it must state a contract or invariant
  A2  a file whose added lines (at least 20 non-blank) are more than --ratio percent comment lines (default 35,
      provisional)
  A3  history words in a comment (previously, was changed, review round, no longer, refactored)
  A4  a quoted dependency path in a comment (node_modules/, site-packages/, vendor/)
  A5  a plain (non-doc) comment block of more than 6 whole lines
  A6  an edited old doc comment over the C4 limit
  A7  a ticket-like key (`ABC-123`) that is not a known standard name, when no ISSUE_KEY_PATTERN applies
Doc comments: `/** */` (JS, TS, Java, Kotlin, PHP, Scala, Dart, Swift, and the `<script>` part of Vue and Svelte),
`///` (C#, Rust, Swift, Dart), `//!` (Rust), a whole-line `//` block on the line directly above a Go `func`, `type`,
`var` or `const`, a Python docstring (the first statement of a module, or of a `def`/`class` body, decorators and
multi-line signatures included). A licence header (the first block of a file, starting in its first 3 lines and
mentioning copyright, license or SPDX) is not checked. An extension the table does not know is skipped and named on
the summary line.
The scan is lexical, not a parser. Handled: '' "" `` strings with backslash escapes, triple-quoted text blocks (Java,
Kotlin, Scala, Swift, Dart, Python), Rust lifetimes (`'a`), a `/* */` comment followed by code on its line. Not
handled: a comment marker inside a regex literal, a heredoc, or a string spanning lines other than the above; such a
line can be miscounted. CSS takes `/* */` only.

Output: one line `<path>:<line>: <code> <text>` per finding, then `comment-lint: C<n> A<n> files=<n>` (plus
`skipped=<extensions>`). Exit 1 when there is a C line, 0 otherwise, 2 on a usage or git error.
`stats` prints the measures of a change (added lines, comment lines and share, lines in blocks of 6 or more, C1 lines,
doc blocks), split into source and test files; it exits 0, or 2 on a usage or git error.
"""
from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import stat
import subprocess
import sys
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)

GIT_TIMEOUT = 60
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
DOC_LIMIT = 6
DOC_SHORT = 2
DEFAULT_RATIO = 35.0
RATIO_MIN_LINES = 20  # A2 needs this many added non-blank lines in the file: a small file is trivially comment-heavy

C_LIKE = {"js", "jsx", "mjs", "cjs", "ts", "tsx", "mts", "cts", "java", "kt", "kts", "scala", "swift", "go", "rs",
          "cs", "php", "dart", "c", "h", "cc", "cpp", "hpp", "m", "css", "scss", "less"}
HASH = {"py", "rb", "sh", "bash", "zsh", "yaml", "yml", "toml", "r", "pl", "ps1", "tf", "dockerfile"}
DASH = {"sql", "lua"}
MARKUP = {"html", "htm", "xml", "svg", "vue", "svelte"}
KNOWN = C_LIKE | HASH | DASH | MARKUP
TS_EXT = {"ts", "tsx", "mts", "cts"}
SLASH_DOC = {"cs", "rs", "swift", "dart"}
STAR_DOC = {"js", "jsx", "mjs", "cjs", "ts", "tsx", "mts", "cts", "java", "kt", "kts", "scala", "swift", "php", "dart",
            "vue", "svelte"}
TRIPLE_QUOTE = {"java", "kt", "kts", "scala", "swift", "dart"}
NO_LINE_COMMENT = {"css"}
LINE_OPENERS = ("//", "///", "//!", "#", "--")

ID_ALWAYS = re.compile(r"\bAC-\d+[a-z]?\b")
ID_NUMBERED = re.compile(r"\b(?:spec|task)s?\s+#?\d{1,3}\b", re.IGNORECASE)
ID_CUED = re.compile(r"\b(?:plan|decision|finding|escape)s?\s+([A-Za-z]{1,2}-?\d+)\b", re.IGNORECASE)
# The cue word may be in any case, but the id after it must be upper-case ("plan K14", not "plan b2"):
CUED_ID = re.compile(r"^[A-Z]{1,2}-?\d+$")
GENERIC_KEY = re.compile(r"\b([A-Z][A-Z0-9]{1,9})-\d{1,6}\b")
STANDARD_NAMES = frozenset("SHA UTF ISO RFC CVE ECMA ES TLS SSL HTTP IEEE ASCII UTC GMT IPV X CWE OWASP PEP JSR "
                           "BCP AES RSA MD H W3C WCAG ANSI POSIX JIS GB EN DIN IEC".split())
DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
PROVENANCE_WORDS = frozenset(("verified", "since", "checked", "updated", "on", "until"))
BRANCH = re.compile(r"\b(?:feature|bugfix|hotfix|release)/[A-Za-z]*-?\d+|\bspec/\d{3}-")
HISTORY = re.compile(r"\b(?:previously|was changed|review round|no longer|refactored)\b", re.IGNORECASE)
DEPENDENCY = re.compile(r"(?:node_modules|site-packages|vendor)/")
LICENCE = re.compile(r"copyright|licen[cs]e|spdx", re.IGNORECASE)
PY_SECTION = re.compile(r"^(?:Args|Arguments|Parameters|Returns|Return|Yields|Raises|Examples?|Notes?|Attributes|"
                        r"See Also|References)\s*:?\s*$")
GO_DECL = re.compile(r"^(?:func|type|var|const)\b")
PY_HEADER = re.compile(r"^(?:async\s+)?(?:def|class)\b")
TEST_PATH = re.compile(r"(?:^|/)(?:tests?|__tests__|spec)/|\.(?:test|spec)\.[a-z]+$|(?:^|/)test_[^/]*\.py$|_test\.go$")


class LintError(Exception):
    """Git or the configuration cannot answer."""


class Block(NamedTuple):
    path: str
    start: int  # 1-based first line
    lines: List[Tuple[int, str]]  # (line number, comment text without markers)
    doc: bool
    whole: bool  # every piece of the block is a comment-only line (no code before or after it)


class Finding(NamedTuple):
    path: str
    line: int
    code: str
    text: str


# ---------------------------------------------------------------------------------------------------------------------
# Git

def git(repo: str, *args: str) -> str:
    try:
        done = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=off", *args], capture_output=True,
                              timeout=GIT_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LintError(f"git {' '.join(args)}: {exc}") from exc
    if done.returncode != 0:
        raise LintError(f"git {' '.join(args)}: {done.stderr.decode('utf-8', 'replace').strip()}")
    return done.stdout.decode("utf-8", "replace")


def _diff_path(header: str) -> Optional[str]:
    """The path of a `+++ ` header: `b/<path>`, or git's quoted form; a trailing tab (paths with spaces) is dropped."""
    target = header[4:].rstrip("\n")
    if target.endswith("\t"):
        target = target[:-1]
    if target.startswith('"') and target.endswith('"'):
        target = codecs.decode(target[1:-1].encode("latin-1", "backslashreplace"), "unicode_escape")
        target = target.encode("latin-1", "replace").decode("utf-8", "replace")
    return target[2:] if target.startswith("b/") else None


def _line_count(text: str) -> int:
    """Lines as git counts them (newline-separated)."""
    return 0 if not text else len(text.split("\n")) - (1 if text.endswith("\n") else 0)


def added_line_numbers(repo: str, base: str) -> Dict[str, Set[int]]:
    """Path -> the line numbers the working tree adds against the base; untracked files count as wholly added."""
    diff = git(repo, "diff", "--no-color", "--unified=0", "--no-renames", "--relative", base, "--")
    added: Dict[str, Set[int]] = {}
    path: Optional[str] = None
    number = 0
    in_header = False
    for raw in diff.split("\n"):
        if raw.startswith("diff --git "):
            path, in_header = None, True
        elif in_header and raw.startswith("+++ "):
            path = _diff_path(raw)
        elif raw.startswith("@@"):
            in_header = False
            found = HUNK.match(raw)
            number = int(found.group(1)) if found else 0
        elif not in_header and raw.startswith("+") and path:
            added.setdefault(path, set()).add(number)
            number += 1
    for rel in git(repo, "ls-files", "-z", "--others", "--exclude-standard").split("\0"):
        if not rel:
            continue
        full = os.path.join(repo, rel)
        try:
            if not stat.S_ISREG(os.lstat(full).st_mode):
                continue
            with open(full, encoding="utf-8", errors="replace") as handle:
                count = _line_count(handle.read())
        except OSError:
            continue
        added[rel] = set(range(1, count + 1))
    return added


# ---------------------------------------------------------------------------------------------------------------------
# Comment scanning (lexical)

Piece = List  # [line number, text, whole-line, opener, comment id]; a list, so a later close can clear `whole`


def extension(path: str) -> str:
    base = os.path.basename(path).lower()
    if base == "dockerfile":
        return "dockerfile"
    return base.rsplit(".", 1)[-1] if "." in base else ""


class _Ids:
    def __init__(self) -> None:
        self.value = 0

    def next(self) -> int:
        self.value += 1
        return self.value


def _skip_quoted(line: str, i: int, quote: str) -> int:
    """Index after a one-line string that opens at `i` (backslash escapes honoured); the line's end when unclosed."""
    j = i + 1
    n = len(line)
    while j < n and line[j] != quote:
        j += 2 if line[j] == "\\" else 1
    return min(j + 1, n)


def _scan_c_like(lines: List[str], ext: str, ids: _Ids, start: int = 0, stop: Optional[int] = None) -> List[Piece]:
    """Comment pieces of C-like code; openers '/**', '/*', '///', '//!', '//'. One /* */ comment yields one piece per
    line, all with the same comment id."""
    pieces: List[Piece] = []
    in_block: Optional[str] = None
    in_template = False
    in_text_block: Optional[str] = None
    cid = 0
    line_comments = ext not in NO_LINE_COMMENT
    triple = ext in TRIPLE_QUOTE
    end = len(lines) if stop is None else stop
    for idx in range(start, end):
        line = lines[idx]
        number = idx + 1
        i, n = 0, len(line)
        code_before = False
        if in_block and n == 0:
            pieces.append([number, "", True, in_block, cid])  # a blank line inside a /* */ comment
        while i < n:
            if in_block:
                close = line.find("*/", i)
                pieces.append([number, line[i:close if close >= 0 else n], not code_before, in_block, cid])
                if close < 0:
                    i = n
                    break
                in_block, i = None, close + 2
                if line[i:].strip() and not line[i:].lstrip().startswith(("//", "/*")):
                    pieces[-1][2] = False  # code follows the comment on its line
                continue
            if in_template:
                j = i
                while j < n and line[j] != "`":
                    j += 2 if line[j] == "\\" else 1
                if j >= n:
                    i = n
                    break
                in_template, i, code_before = False, j + 1, True
                continue
            if in_text_block:
                close = line.find(in_text_block, i)
                if close < 0:
                    i = n
                    break
                in_text_block, i, code_before = None, close + 3, True
                continue
            ch = line[i]
            if triple and (line.startswith('"""', i) or (ext == "dart" and line.startswith("'''", i))):
                in_text_block, i, code_before = line[i:i + 3], i + 3, True
                continue
            if ch == "'" and ext == "rs" and not re.match(r"'(?:\\.[^']*|[^'\\])'", line[i:]):
                i += 1  # a Rust lifetime (`'a`), not a character literal
                code_before = True
                continue
            if ch in "'\"":
                i, code_before = _skip_quoted(line, i, ch), True
                continue
            if ch == "`":
                in_template, i, code_before = True, i + 1, True
                continue
            if line_comments and line.startswith("//", i):
                if line.startswith("///", i) and not line.startswith("////", i):
                    opener = "///"
                elif line.startswith("//!", i):
                    opener = "//!"
                else:
                    opener = "//"
                pieces.append([number, line[i + len(opener):], not code_before, opener, ids.next()])
                break
            if line.startswith("/*", i):
                opener = "/**" if line.startswith("/**", i) and not line.startswith("/**/", i) else "/*"
                in_block, i, cid = opener, i + len(opener), ids.next()
                if i >= n:
                    pieces.append([number, "", not code_before, in_block, cid])
                continue
            if not ch.isspace():
                code_before = True
            i += 1
    return pieces


def _scan_hash(lines: List[str], python: bool, ids: _Ids) -> List[Piece]:
    """`#` comments outside strings; a Python docstring is a piece with the triple-quote opener. Python logical lines
    (bracket depth, decorators, multi-line signatures) decide whether a triple-quoted string is a docstring."""
    pieces: List[Piece] = []
    in_triple: Optional[str] = None
    triple_doc = False
    cid = 0
    depth = 0
    logical: List[str] = []  # code text (strings and comments dropped) of the current logical line
    last_logical = ""  # the last complete logical line
    seen_statement = False
    for idx, line in enumerate(lines):
        number = idx + 1
        stripped = line.strip()
        if in_triple:
            close = line.find(in_triple)
            if triple_doc:
                pieces.append([number, line[:close] if close >= 0 else line, True, '"""', cid])
            if close < 0:
                continue
            in_triple = None
            line = line[close + 3:]
            stripped = line.strip()
            if not stripped:
                continue
        if python and depth == 0:
            m = re.match(r"^[rRuUbBfF]{0,2}(\"\"\"|''')", stripped)
            if m:
                quote = m.group(1)
                is_doc = (not seen_statement) or bool(PY_HEADER.match(last_logical) and last_logical.endswith(":"))
                rest = stripped[m.end():]
                close = rest.find(quote)
                cid = ids.next()
                if is_doc:
                    pieces.append([number, rest[:close] if close >= 0 else rest, True, '"""', cid])
                if close < 0:
                    in_triple, triple_doc = quote, is_doc
                seen_statement = True
                last_logical = "<string>"
                continue
        i, n = 0, len(line)
        code_before = False
        code: List[str] = []
        while i < n:
            ch = line[i]
            if ch in "'\"":
                if python and line.startswith(ch * 3, i):
                    close = line.find(ch * 3, i + 3)
                    if close < 0:
                        in_triple, triple_doc = ch * 3, False
                        i = n
                        break
                    i, code_before = close + 3, True
                    code.append("s")
                    continue
                i, code_before = _skip_quoted(line, i, ch), True
                code.append("s")
                continue
            if ch == "#":
                pieces.append([number, line[i + 1:], not code_before, "#", ids.next()])
                break
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth = max(0, depth - 1)
            if not ch.isspace():
                code_before = True
            code.append(ch)
            i += 1
        if code_before:
            logical.append("".join(code).strip())
            if depth == 0 and not line.rstrip().endswith("\\"):
                joined = " ".join(logical).strip()
                if not joined.startswith("@"):
                    last_logical = joined
                    seen_statement = True
                logical = []
    return pieces


def _scan_dash(lines: List[str], ids: _Ids) -> List[Piece]:
    pieces: List[Piece] = []
    in_block = False
    cid = 0
    for idx, line in enumerate(lines):
        number = idx + 1
        i, n = 0, len(line)
        code_before = False
        if in_block and n == 0:
            pieces.append([number, "", True, "/*", cid])
        while i < n:
            if in_block:
                close = line.find("*/", i)
                pieces.append([number, line[i:close if close >= 0 else n], not code_before, "/*", cid])
                if close < 0:
                    i = n
                    break
                in_block, i = False, close + 2
                if line[i:].strip() and not line[i:].lstrip().startswith("--"):
                    pieces[-1][2] = False
                continue
            ch = line[i]
            if ch == "'":
                i, code_before = _skip_quoted(line, i, "'"), True
                continue
            if line.startswith("--", i):
                pieces.append([number, line[i + 2:], not code_before, "--", ids.next()])
                break
            if line.startswith("/*", i):
                in_block, i, cid = True, i + 2, ids.next()
                if i >= n:
                    pieces.append([number, "", not code_before, "/*", cid])
                continue
            if not ch.isspace():
                code_before = True
            i += 1
    return pieces


def _scan_markup(lines: List[str], ext: str, ids: _Ids) -> Tuple[List[Piece], bool]:
    """`<!-- -->` comments; in a Vue or Svelte file a `<script>` part is scanned as JS or TS. Returns the pieces and
    whether a `<script lang="ts">` part was seen."""
    pieces: List[Piece] = []
    in_comment = False
    ts = False
    cid = 0
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not in_comment and ext in ("vue", "svelte") and re.match(r"^\s*<script\b", line):
            ts = ts or bool(re.search(r"lang=[\"'](?:ts|tsx)[\"']", line))
            if "</script>" in line:  # a one-line script (`<script src=…></script>`)
                idx += 1
                continue
            stop = next((j for j in range(idx + 1, len(lines)) if re.match(r"^\s*</script>", lines[j])), len(lines))
            pieces.extend(_scan_c_like(lines, "ts" if ts else "js", ids, idx + 1, stop))
            idx = stop + 1
            continue
        i, n = 0, len(line)
        code_before = False
        if in_comment and n == 0:
            pieces.append([idx + 1, "", True, "<!--", cid])
        while i < n:
            if in_comment:
                close = line.find("-->", i)
                pieces.append([idx + 1, line[i:close if close >= 0 else n], not code_before, "<!--", cid])
                if close < 0:
                    i = n
                    break
                in_comment, i = False, close + 3
                if line[i:].strip():
                    pieces[-1][2] = False
                continue
            if line.startswith("<!--", i):
                in_comment, i, cid = True, i + 4, ids.next()
                if i >= n:
                    pieces.append([idx + 1, "", not code_before, "<!--", cid])
                continue
            if not line[i].isspace():
                code_before = True
            i += 1
        idx += 1
    return pieces, ts


def comment_blocks(path: str, text: str) -> Tuple[List[Block], bool]:
    """The comment blocks of a file (extension in KNOWN), and whether its doc comments follow TypeScript rules. The
    pieces of one comment form one block; consecutive whole-line line comments with the same opener join it."""
    ext = extension(path)
    lines = text.split("\n")
    ts = ext in TS_EXT
    ids = _Ids()
    if ext in C_LIKE:
        pieces = _scan_c_like(lines, ext, ids)
    elif ext in HASH:
        pieces = _scan_hash(lines, ext == "py", ids)
    elif ext in DASH:
        pieces = _scan_dash(lines, ids)
    else:
        pieces, ts_script = _scan_markup(lines, ext, ids)
        ts = ts or ts_script
    blocks: List[Block] = []
    current: List[Piece] = []

    def flush() -> None:
        if not current:
            return
        opener = current[0][3]
        whole = all(p[2] for p in current)
        doc = opener in ('"""', "//!") or (opener == "/**" and ext in STAR_DOC) or (opener == "///" and ext in SLASH_DOC)
        if ext == "go" and opener == "//":
            last = current[-1][0]
            following = lines[last].strip() if last < len(lines) else ""
            doc = whole and bool(GO_DECL.match(following))
        blocks.append(Block(path, current[0][0], [(p[0], p[1]) for p in current], doc, whole))
        current.clear()

    for piece in pieces:
        if current:
            prev = current[-1]
            joined = piece[4] == prev[4] or (piece[3] in LINE_OPENERS and piece[3] == prev[3] and piece[2] and prev[2]
                                             and piece[0] == prev[0] + 1)
            if not joined:
                flush()
        current.append(piece)
    flush()
    return blocks, ts


# ---------------------------------------------------------------------------------------------------------------------
# Checks

def description_lines(block: Block) -> List[Tuple[int, str]]:
    """The doc comment's description lines: non-blank text before the first tag (`@...`) or docstring section."""
    out: List[Tuple[int, str]] = []
    for number, text in block.lines:
        body = text.strip().lstrip("*").strip()
        if not body or body in ("/**", "*/", '"""', "'''"):
            continue
        if body.startswith("@") or PY_SECTION.match(body):
            break
        out.append((number, body))
    return out


def issue_key_regex(pattern: str) -> Optional[re.Pattern]:
    """The project key pattern, used only when it starts with a literal prefix such as `AP-`."""
    if not pattern or not re.match(r"^[A-Za-z][A-Za-z0-9]*-", pattern):
        return None
    try:
        return re.compile(r"(?<![A-Za-z0-9])(?:" + pattern + r")(?![0-9])")
    except re.error:
        return None


def _provenance_date(text: str) -> Optional[str]:
    """The first date with a provenance word among the 3 words before it, else None."""
    for m in DATE.finditer(text):
        before = re.findall(r"[A-Za-z]+", text[:m.start()].lower())[-3:]
        if PROVENANCE_WORDS.intersection(before) or "as of" in " ".join(before):
            return m.group(0)
    return None


def _cued_id(text: str) -> Optional[str]:
    for m in ID_CUED.finditer(text):
        if CUED_ID.match(m.group(1)):
            return m.group(0)
    return None


def line_findings(text: str, key: Optional[re.Pattern]) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """(blocking, advisory) findings of one added comment line: (code, matched text)."""
    blocking: List[Tuple[str, str]] = []
    advisory: List[Tuple[str, str]] = []
    found = ID_ALWAYS.search(text) or ID_NUMBERED.search(text)
    match = found.group(0) if found else _cued_id(text)
    if match is None and key is not None:
        keyed = key.search(text)
        match = keyed.group(0) if keyed else None
    if match is not None:
        blocking.append(("C1", match))
    if "§" in text:
        blocking.append(("C2", "§"))
    dated = _provenance_date(text)
    if dated:
        blocking.append(("C3", dated))
    else:
        branch = BRANCH.search(text)
        if branch:
            blocking.append(("C3", branch.group(0)))
    history = HISTORY.search(text)
    if history:
        advisory.append(("A3", history.group(0)))
    dependency = DEPENDENCY.search(text)
    if dependency:
        advisory.append(("A4", dependency.group(0)))
    if key is None and match is None:
        for m in GENERIC_KEY.finditer(text):
            if m.group(1) not in STANDARD_NAMES:
                advisory.append(("A7", m.group(0)))
                break
    return blocking, advisory


def lint_file(path: str, text: str, added: Set[int], key: Optional[re.Pattern], ratio: float
              ) -> Tuple[List[Finding], Dict[str, int]]:
    """Findings of one file (extension in KNOWN) and its measures."""
    blocks, ts = comment_blocks(path, text)
    findings: List[Finding] = []
    lines = text.split("\n")
    added_nonblank = sum(1 for n in added if 0 < n <= len(lines) and lines[n - 1].strip())
    comment_lines: Set[int] = set()
    measures = {"added": added_nonblank, "comment": 0, "in_long_blocks": 0, "id_lines": 0, "doc_blocks": 0}
    for index, block in enumerate(blocks):
        numbers = sorted({n for n, _t in block.lines})
        touched = [n for n in numbers if n in added]
        if not touched:
            continue
        if index == 0 and block.start <= 3 and any(LICENCE.search(t) for _n, t in block.lines):
            continue
        comment_lines.update(n for n in touched if lines[n - 1].strip())
        if len(numbers) >= DOC_LIMIT:
            measures["in_long_blocks"] += len(touched)
        if block.doc:
            measures["doc_blocks"] += 1
        for number, ctext in block.lines:
            if number not in added:
                continue
            blocking, advisory = line_findings(ctext, key)
            if any(code == "C1" for code, _t in blocking):
                measures["id_lines"] += 1
            for code, match in blocking + advisory:
                findings.append(Finding(path, number, code, match))
            if ts and block.doc and re.search(r"@param\s*\{", ctext):
                findings.append(Finding(path, number, "C4", "@param with a type in TypeScript"))
        if block.doc:
            size = len(description_lines(block))
            if size > DOC_LIMIT:
                code = "C4" if all(n in added for n in numbers) else "A6"
                findings.append(Finding(path, block.start, code, f"doc comment of {size} description lines"))
            elif size > DOC_SHORT:
                findings.append(Finding(path, block.start, "A1", f"doc comment of {size} description lines"))
        elif block.whole and len(numbers) > DOC_LIMIT:
            findings.append(Finding(path, block.start, "A5", f"comment block of {len(numbers)} lines"))
    measures["comment"] = len(comment_lines)
    if added_nonblank >= RATIO_MIN_LINES and 100.0 * len(comment_lines) / added_nonblank > ratio:
        share = 100.0 * len(comment_lines) / added_nonblank
        findings.append(Finding(path, min(added), "A2", f"{share:.0f}% of the added lines are comments"))
    return findings, measures


# ---------------------------------------------------------------------------------------------------------------------
# CLI

def _project_key(workspace: str) -> str:
    try:
        with open(os.path.join(workspace, ".claude", "project-config.json"), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return ""
    value = data.get("ISSUE_KEY_PATTERN", "") if isinstance(data, dict) else ""
    return value if isinstance(value, str) else ""


def _resolve(base: Optional[str], profile_path: str) -> Tuple[str, str, str]:
    """(source repo, base commit, workspace)."""
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(profile_path)))
    repo = quality_profile.source_root(workspace)
    if base is None:
        try:
            profile = quality_profile.load(profile_path)
        except quality_profile.MissingProfile:
            raise LintError(f"{quality_profile.MISSING}; or pass --base")
        ref = profile.get("integrationRef") if isinstance(profile, dict) else None
        if not isinstance(ref, str) or not ref:
            raise LintError("integrationRef is unset in the quality profile; pass --base")
        base = git(repo, "merge-base", "HEAD", ref).strip()
    if not base or base.startswith("-"):
        raise LintError(f"not a revision: {base!r}")
    try:
        commit = git(repo, "rev-parse", "--verify", base + "^{commit}").strip()
    except LintError as exc:
        raise LintError(f"not a revision: {base!r} ({exc})") from exc
    return repo, commit, workspace


def run(argv: List[str]) -> int:
    stats_mode = bool(argv) and argv[0] == "stats"
    parser = argparse.ArgumentParser(prog="comment_lint.py", description="Check the code comments a change adds.")
    parser.add_argument("--base", help="the base revision (default: merge base of HEAD with integrationRef)")
    parser.add_argument("--ratio", type=float, default=DEFAULT_RATIO, help="A2 threshold in percent (default 35)")
    parser.add_argument("--profile", default=quality_profile.DEFAULT_PROFILE)
    try:
        args = parser.parse_args(argv[1:] if stats_mode else argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        repo, base, workspace = _resolve(args.base, args.profile)
        added = added_line_numbers(repo, base)
    except (LintError, quality_profile.ProfileError) as exc:
        print(f"comment-lint: {exc}", file=sys.stderr)
        return 2
    key = issue_key_regex(_project_key(workspace))
    findings: List[Finding] = []
    skipped: Set[str] = set()
    totals = {kind: {"added": 0, "comment": 0, "in_long_blocks": 0, "id_lines": 0, "doc_blocks": 0}
              for kind in ("source", "test")}
    files = 0
    for path in sorted(added):
        ext = extension(path)
        if ext not in KNOWN:
            if ext:
                skipped.add(ext)
            continue
        full = os.path.join(repo, path)
        if not os.path.isfile(full):
            continue
        try:
            with open(full, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        file_findings, measures = lint_file(path, text, added[path], key, args.ratio)
        files += 1
        findings.extend(file_findings)
        kind = "test" if TEST_PATH.search(path) else "source"
        for name, value in measures.items():
            totals[kind][name] += value
    tail = f" files={files}" + (f" skipped={','.join(sorted(skipped))}" if skipped else "")
    if stats_mode:
        for kind in ("source", "test"):
            t = totals[kind]
            share = 100.0 * t["comment"] / t["added"] if t["added"] else 0.0
            print(f"{kind}: added={t['added']} comment={t['comment']} share={share:.0f}% "
                  f"in_blocks_6plus={t['in_long_blocks']} id_lines={t['id_lines']} doc_blocks={t['doc_blocks']}")
        print(tail.strip())
        return 0
    findings.sort(key=lambda f: (f.path, f.line, f.code))
    for f in findings:
        print(f"{f.path}:{f.line}: {f.code} {f.text}")
    blocking = sum(1 for f in findings if f.code.startswith("C"))
    print(f"comment-lint: C{blocking} A{len(findings) - blocking}{tail}")
    return 1 if blocking else 0


def main(argv: Optional[List[str]] = None) -> int:
    return run(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    sys.exit(main())
