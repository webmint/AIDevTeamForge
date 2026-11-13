#!/usr/bin/env python3
"""Mechanical checks of a feature's spec.md, and the hash that tells /plan whether the spec changed after its review.

Two verbs. `lint` runs the blocking checks B1-B4 and the advisory checks A1-A3; `hash` computes, records and checks
the spec hash kept in the spec-gate report (the hash leaves out the `**Status**:` and `Self-approved (autonomous mode`
header lines).

Usage:
  python3 scripts/forge/spec_lint.py lint <feature-dir> [--root <dir>]
  python3 scripts/forge/spec_lint.py hash <feature-dir> [--root <dir>] [--record | --unreviewed "<ids>" | --check]
      --root <dir>   project root; the feature dir (`specs/NNN-name`) is resolved against it (default: the current dir)
  `hash` takes at most one of its three flags; without one it prints `sha256:<hex>` and writes nothing.

Blocking (B) and advisory (A) checks, all on `<feature-dir>/spec.md` (the `## Request (verbatim)` section, fenced code
blocks and, where noted, code spans and quoted text are skipped; heading lines are checked):
  B1  AC ids: `- [ ]` / `- [x]` lines whose bold id is `**AC-N**` (text may follow the id before the colon; ACs may
      sit under bold sub-headings). A duplicated id, a gap in 1..max, no AC at all, or a line that looks like an AC
      definition (`**AC-3:**`, `**AC-3a**`, no checkbox) but not in the `- [ ] **AC-N**:` form.
  B2  an `AC-N` outside the AC definitions that names no AC of the spec. Not checked: a reference qualified by the
      token right before it (a 3-digit spec number, `spec`, `ticket`, `brief`, `contract`).
  B3  a `§N`, `§Na` or `§N.M` with no heading of that number (`## 2.`, `## 2a.`, `### 3.4 ...`). Not checked: a
      reference whose preceding word, separated from the `§` by whitespace alone, names another document (any word
      but a short list of function words) or is a 3-digit spec number (`054 §9.9`). `(§9)`, `Source: §9`, `[§9]`
      are the spec's own. A list of references (`§7.3, §8`, `§3 / §4`) takes the qualification of its first member.
  B4  a fenced code block that is never closed (the lines after its opening were not checked).
  A1  numerical consistency: one noun with two or more numbers (a heuristic: two quantities with the same unit are a
      false positive).
  A2  a vague non-functional phrase in a sentence of Desired Behavior, Acceptance Criteria or Technical Constraints,
      with no number plus unit and no named standard in the same sentence.
  A3  evidence shape: a code span that looks like a path citation but has a bad line part (`:0`, `:L12`, `#L12`,
      `:12-`, a reversed range), and a `## 2a. Prior art` table row whose evidence cell has no `file:line`.

Spec hash: SHA-256 of spec.md without two header lines, both only before the first `## ` heading: the `**Status**:`
line and any line starting `Self-approved (autonomous mode` (the HARD GATE approval and the autonomous self-approval
add or edit them). A `**Status**:` line in the body counts.
  --record            write or replace `**Spec hash**: sha256:<hex>` in `gates/spec-gate.md` (after its header lines)
                      and drop any `**Unreviewed changes**:` line
  --unreviewed "<ids>"  write or replace `**Unreviewed changes**: <ids>` there
  --check             compare the spec with the recorded hash; print and write `gates/spec-hash.txt`:
                      `spec unchanged since its last review (sha256:...)` (exit 0: hash matches and no Unreviewed
                      line), `spec unchanged since its last review round; unreviewed changes: <ids>` (hash matches,
                      Unreviewed line present) or
                      `spec changed after its last review; unreviewed changes: <ids | none recorded>` (exit 1)
  Edits of spec-gate.md are atomic (temp file + os.replace) and touch only those two lines.

Output: `lint` writes `<feature-dir>/gates/spec-lint.txt` (a BLOCKING and an ADVISORY section, each line
`<code>-<spec.md line> <message>` (e.g. `B3-9`), then `spec-lint: B<n> A<n>`) and prints the same text.
Exit codes: lint 0 no blocking finding, 1 at least one; hash --check 0 unchanged, 1 changed; every verb 2 for bad
arguments or an unreadable or unwritable file, and --check 2 when there is no spec-gate report or no recorded hash.
Stdlib only; Python 3.9+.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from typing import Dict, List, NamedTuple, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_refs  # noqa: E402  (sibling module; path set above)

# ---------------------------------------------------------------------------
# Constants ported verbatim from the 2.0 branch (develop-2.0-init @ dac1624)
# ---------------------------------------------------------------------------

# src/devforge/lib/_specify/_schema.py. The line part of PATH_EVIDENCE_RE is widened to accept `N-M` ranges here.
PATH_EVIDENCE_RE = re.compile(r"[^\s:]+:[1-9][0-9]*(?:-[1-9][0-9]*)?")
# Departure from 2.0: the trailing `\b` is `(?!\w)`, because `\b` after `%` or `$` needs a word character next to it
# and so never matched "99%" at the end of a sentence.
NFR_NUMERIC_THRESHOLD_RE: "re.Pattern[str]" = re.compile(
    r"\d+\s*(ms|s|sec|min|hr|users?|req/s|rps|qps|tps|GB|MB|KB|TB|%|\$|connections?|rows?|records?)(?!\w)",
    re.IGNORECASE,
)
NFR_VAGUE_BLOCKLIST: frozenset = frozenset({
    "high", "low", "fast", "slow", "scalable", "good", "acceptable",
    "reasonable", "robust", "performant", "efficient", "secure", "reliable",
})
NFR_NAMED_CLASS_RE: "re.Pattern[str]" = re.compile(
    r"\b(PCI-DSS|SOC\s*2|ISO\s*\d{4,5}|GDPR|HIPAA|FedRAMP|FIPS|NIST)\b",
    re.IGNORECASE,
)
NUMERIC_DIGIT_NOUN_RE: "re.Pattern[str]" = re.compile(
    r"\b(\d+)\s+([a-zA-Z]+)\b"
)
NUMERIC_HEADING_RE: "re.Pattern[str]" = re.compile(r"^\s*#+\s")
NUMERIC_TABLE_SEP_RE: "re.Pattern[str]" = re.compile(
    r"^\s*\|[-:|\s]+\|\s*$"
)

# src/devforge/lib/_banned_phrases.py (BANNED_PHRASES)
BANNED_PHRASES = (
    "handles",
    "manages",
    "processes",
    "validates",
    "various",
    "etc",
    "responsible for",
)

# ---------------------------------------------------------------------------
# Local rules (not in 2.0)
# ---------------------------------------------------------------------------

# 2.0's _shared/spec_acs.py `_AC_LINE_RE` widened: text may follow the bold id before the colon.
_AC_DEF_RE = re.compile(r"^\s*[-*]\s+\[([xX ])\]\s+\*\*AC-(\d+)\*\*")
# loose forms of an AC definition: with a checkbox (the id may be plain), or bold without one inside the AC section
_AC_LOOSE_BOX_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[[ xX]\]\s+(?:\*\*)?AC-\w+")
_AC_LOOSE_BARE_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\*\*AC-\w+")
_AC_REF_RE = re.compile(r"\bAC-(\d+[a-z]?)\b")
_SPEC_NUMBER_RE = re.compile(r"^\d{3}(?:'s)?$")
_AC_QUALIFIERS = frozenset({"spec", "ticket", "brief", "contract"})
_SECTION_REF_RE = re.compile(r"§(\d+[a-z]?(?:\.\d+)*)(?![A-Za-z0-9])")
_H2_RE = re.compile(r"^ {0,3}##[ \t]+(.*)$")
_HEADING_LINE_RE = re.compile(r"^ {0,3}#{1,6}[ \t]")
_QUALIFIER_RE = re.compile(r"([A-Za-z0-9'’]+)[*_]*\s+[*_]*$")
_MASK = "\x01"  # placeholder for a code span or quote when looking for a qualifier (not a space, not a word char)
_HEADING_NUMBER_RE = re.compile(r"^ {0,3}#{2,6}\s+(\d+[a-z]?(?:\.\d+)*)\.?(?:\s|$)")
_FUNCTION_WORDS = frozenset("in see and or of per from to under by at the its this also with on as cf".split())
_LIST_JOINER_RE = re.compile(r"^(?:\s*(?:,|/|&|and|or|to|–|-|—|\d+(?:\.\d+)*)\s*)+$", re.IGNORECASE)
_THOUSANDS_RE = re.compile(r"(?<=\d),(?=\d{3}\b)")
_NOUN_STOPWORDS = _FUNCTION_WORDS | frozenset({"a", "an", "is", "are", "was", "be", "it", "if", "for", "not", "but"})
# a straight quote opens a quoted span only when no word character precedes it (`5" screen` is an inch mark) and
# closes it only when none follows
_QUOTED_RE = re.compile(r'(?<!\w)"[^"\n]*?"(?!\w)|“[^”\n]*”')
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_NFR_SECTIONS = ("desired behavior", "acceptance criteria", "technical constraints")
_STATUS_PREFIX = b"**Status**:"
_SELF_APPROVED_PREFIX = b"Self-approved (autonomous mode"
_H2_BYTES_RE = re.compile(rb"^ {0,3}##[ \t]")
_HASH_PREFIX = "**Spec hash**:"
_UNREVIEWED_PREFIX = "**Unreviewed changes**:"
_HASH_VALUE_RE = re.compile(r"^\*\*Spec hash\*\*:\s*(sha256:[0-9a-f]{64})\s*$")
_BAD_LINE_PART = (
    r"(?::0+(?:-\d+)?|:L\d+(?:-L?\d+)?|#L\d+(?:-L?\d+)?|:\d+-|:\d+-0+)"
)
_BAD_CITE_RE = re.compile(r"^(?P<path>[^\s:#`]*[^\s:#`/][^\s:#`]*)(?P<bad>" + _BAD_LINE_PART + r")$")
_REVERSED_RE = re.compile(r"^(?P<path>[^\s:#`]+):(?P<a>\d+)-(?P<b>\d+)$")
_PATHLIKE_RE = re.compile(r"(?:/|\.[A-Za-z][A-Za-z0-9]*$)")


class SpecError(Exception):
    """Bad input or an unreadable / unwritable file: exit code 2."""


class Line(NamedTuple):
    number: int  # 1-based line in spec.md
    text: str
    section: str  # title of the enclosing `## ` section ("" before the first)
    heading: bool  # a `#` heading line


def _atomic_write(path: str, text: str) -> None:
    try:
        spec_refs.atomic_write(path, text)
    except OSError as err:
        raise SpecError("cannot write {}: {}".format(path, err))


def _read_text(path: str, strict: bool = False) -> str:
    try:
        with open(path, "rb") as handle:
            return handle.read().decode("utf-8", errors="strict" if strict else "replace")
    except (OSError, UnicodeDecodeError) as err:
        raise SpecError("cannot read {}: {}".format(path, err))


# ---------------------------------------------------------------------------
# Spec reading
# ---------------------------------------------------------------------------

def _scan(text: str) -> Tuple[List[Line], Optional[Tuple[int, bool]]]:
    """(lines outside the Request section and outside fenced code blocks, (the line a fence opened on that is never
    closed, whether it is in the Request) or None). Heading lines are kept. A fence left open inside the Request is
    closed at the next `## ` heading and is not reported; one still open at the end of the file is."""
    lines: List[Line] = []
    section, in_request = "", False
    fence: Optional[str] = None
    opened = 0
    for number, raw in enumerate(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"), 1):
        if fence is not None and in_request and _H2_RE.match(raw):
            fence = None  # a fence left open in the Request ends at the next `## ` heading
        new = spec_refs.fence_update(fence, raw)
        fenced = fence is not None or new is not None
        if fence is None and new is not None:
            opened = number
        fence = new
        if fenced:
            continue
        m = _H2_RE.match(raw)
        if m:
            section = m.group(1).strip()
            in_request = section.lower().startswith("request")
        if not in_request:
            lines.append(Line(number, raw, section, bool(_HEADING_LINE_RE.match(raw))))
    return lines, ((opened, in_request) if fence is not None else None)


def _blank_spans(text: str, spans: List[Tuple[int, int]], fill: str = " ") -> str:
    chars = list(text)
    for start, end in spans:
        for i in range(start, end):
            chars[i] = fill
    return "".join(chars)


def _without_code(text: str, fill: str = " ") -> str:
    """The line with its code spans replaced by `fill` (columns are kept)."""
    return _blank_spans(text, [(s, e) for s, e, _c in spec_refs.code_spans(text)], fill)


def _heading_numbers(lines: List[Line]) -> set:
    numbers = set()
    for line in lines:
        m = _HEADING_NUMBER_RE.match(line.text) if line.heading else None
        if m:
            numbers.add(m.group(1))
    return numbers


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

Finding = Tuple[str, int, str]  # (code, spec line, message)


def _loose_ac(line: "Line") -> Optional["re.Match[str]"]:
    """The loose AC-definition match of a line, or None (the bare bold form counts only in the AC section)."""
    m = _AC_LOOSE_BOX_RE.match(line.text)
    if m is None and "acceptance criteria" in line.section.lower():
        m = _AC_LOOSE_BARE_RE.match(line.text)
    return m


def _check_ac_ids(lines: List[Line]) -> Tuple[List[Finding], set]:
    found: List[Finding] = []
    seen: Dict[int, int] = {}
    for line in lines:
        m = _AC_DEF_RE.match(line.text)
        if not m:
            if _loose_ac(line):
                found.append(("B1", line.number, "AC definition not in the `- [ ] **AC-N**:` form"))
            continue
        number = int(m.group(2))
        if number in seen:
            found.append(("B1", line.number, "AC-{} is defined twice (first on line {})".format(number, seen[number])))
        else:
            seen[number] = line.number
    if not seen:
        return found + [("B1", 1, "no acceptance criterion found (`- [ ] **AC-N** ...` lines)")], set()
    missing = [str(n) for n in range(1, max(seen) + 1) if n not in seen]
    if missing:
        found.append(("B1", seen[max(seen)], "AC ids are not contiguous: missing AC-{}".format(", AC-".join(missing))))
    return found, {"AC-{}".format(n) for n in seen}


def _preceding_word(text: str, pos: int) -> str:
    """The word right before `pos`, looking past one to three punctuation characters (used for B2's qualifiers)."""
    before = text[:pos].rstrip()
    if not before:
        return ""
    m = re.search(r"([A-Za-z0-9'’]+)[^\w]{0,3}$", before) if before[-1] in "(\"“'[*_:" else re.search(
        r"([A-Za-z0-9'’]+)$", before)
    return m.group(1) if m else ""


def _qualifier(text: str, pos: int) -> bool:
    """True when the word before `pos`, separated from it by whitespace alone, names another document (B3)."""
    m = _QUALIFIER_RE.search(text[:pos])
    if not m:
        return False
    word = m.group(1)
    if _SPEC_NUMBER_RE.match(word):
        return True
    return not word.isdigit() and word.lower() not in _FUNCTION_WORDS


def _check_ac_refs(lines: List[Line], defined: set) -> List[Finding]:
    found: List[Finding] = []
    for line in lines:
        text = _without_code(line.text)
        def_match = _loose_ac(line)
        for m in _AC_REF_RE.finditer(text):
            if def_match and m.start() <= def_match.end():
                continue  # the bold id of the definition itself
            ref = "AC-{}".format(m.group(1))
            if ref in defined:
                continue
            word = _preceding_word(text, m.start()).lower()
            if _SPEC_NUMBER_RE.match(word) or word in _AC_QUALIFIERS:
                continue
            found.append(("B2", line.number, "{} names no AC of this spec".format(ref)))
    return found


def _check_section_refs(lines: List[Line], numbers: set) -> List[Finding]:
    found: List[Finding] = []
    for line in lines:
        text = _without_code(line.text, _MASK)
        text = _blank_spans(text, [(m.start(), m.end()) for m in _QUOTED_RE.finditer(text)], _MASK)
        qualified_until = -1  # end of the last qualified reference of a list
        last_end = -1
        for m in _SECTION_REF_RE.finditer(text):
            joined = last_end >= 0 and _LIST_JOINER_RE.match(text[last_end:m.start()] or "x") is not None
            last_end_prev, last_end = last_end, m.end()
            if joined and qualified_until == last_end_prev:
                qualified_until = m.end()
                continue
            if _qualifier(text, m.start()):
                qualified_until = m.end()
                continue
            if m.group(1) in numbers:
                continue
            found.append(("B3", line.number, "§{} matches no heading of this spec; name the document it means "
                          "(e.g. `contract §{}`)".format(m.group(1), m.group(1))))
    return found


def _check_numbers(lines: List[Line]) -> List[Finding]:
    groups: Dict[str, Dict[str, List[int]]] = {}
    for line in lines:
        if NUMERIC_HEADING_RE.match(line.text) or NUMERIC_TABLE_SEP_RE.match(line.text):
            continue
        text = _THOUSANDS_RE.sub("", _SECTION_REF_RE.sub(" ", _without_code(line.text)))
        for m in NUMERIC_DIGIT_NOUN_RE.finditer(text):
            if m.group(2).lower() in _NOUN_STOPWORDS:
                continue
            groups.setdefault(m.group(2).lower(), {}).setdefault(m.group(1), []).append(line.number)
    found: List[Finding] = []
    for noun in sorted(groups):
        values = groups[noun]
        if len(values) < 2:
            continue
        parts = ", ".join("{} (line{} {})".format(v, "s" if len(set(ls)) > 1 else "", ",".join(
            str(n) for n in sorted(set(ls)))) for v, ls in sorted(values.items(), key=lambda kv: kv[1][0]))
        first = min(ls[0] for ls in values.values())
        found.append(("A1", first, "'{}' appears with different numbers: {}".format(noun, parts)))
    return found


def _vague_hits(sentence: str) -> List[str]:
    lowered = sentence.lower()
    hits = [w for w in sorted(NFR_VAGUE_BLOCKLIST) if re.search(r"(?<![\w])" + re.escape(w) + r"(?![\w])", lowered)]
    hits += [p for p in BANNED_PHRASES if re.search(r"(?<![\w])" + re.escape(p) + r"(?![\w])", lowered)]
    return hits


def _check_vague(lines: List[Line]) -> List[Finding]:
    found: List[Finding] = []
    for line in lines:
        if not any(key in line.section.lower() for key in _NFR_SECTIONS):
            continue
        if NUMERIC_HEADING_RE.match(line.text) or NUMERIC_TABLE_SEP_RE.match(line.text):
            continue
        for sentence in _SENTENCE_SPLIT_RE.split(_without_code(line.text)):
            hits = _vague_hits(sentence)
            if not hits:
                continue
            if NFR_NUMERIC_THRESHOLD_RE.search(sentence) or NFR_NAMED_CLASS_RE.search(sentence):
                continue
            found.append(("A2", line.number, "vague phrase {} with no number or named standard: {}".format(
                ", ".join("'{}'".format(h) for h in hits), " ".join(sentence.split())[:100])))
    return found


def _table_cells(text: str) -> List[str]:
    """Cells of a table row; a `|` inside a code span or escaped as `\\|` does not split."""
    protected = [(s, e) for s, e, _c in spec_refs.code_spans(text)]
    cells: List[str] = []
    start = 0
    stripped = text.strip()
    offset = text.index(stripped) if stripped else 0
    body = stripped
    base = offset
    for i, ch in enumerate(body):
        pos = base + i
        if ch == "|" and not (i > 0 and body[i - 1] == "\\") and not any(s <= pos < e for s, e in protected):
            cells.append(body[start:i].strip())
            start = i + 1
    cells.append(body[start:].strip())
    if body.startswith("|"):
        cells = cells[1:]
    if body.endswith("|") and cells:
        cells = cells[:-1]
    return cells


def _check_evidence(lines: List[Line]) -> List[Finding]:
    found: List[Finding] = []
    for line in lines:
        for _s, _e, content in spec_refs.code_spans(line.text):
            m = _BAD_CITE_RE.match(content)
            if m and _PATHLIKE_RE.search(m.group("path")) and "//" not in m.group("path") and re.search(
                    r"[A-Za-z]", m.group("path")):
                found.append(("A3", line.number, "`{}` has a bad line part '{}'".format(content, m.group("bad"))))
                continue
            r = _REVERSED_RE.match(content)
            if r and _PATHLIKE_RE.search(r.group("path")) and int(r.group("a")) > int(r.group("b")) >= 1:
                found.append(("A3", line.number, "`{}` is a reversed line range".format(content)))
    # `## 2a. Prior art` table: the evidence cell must carry a file:line
    column: Optional[int] = None
    in_table = False
    for line in lines:
        if "prior art" not in line.section.lower():
            continue
        if not line.text.lstrip().startswith("|"):
            in_table, column = False, None
            continue
        cells = _table_cells(line.text)
        if not in_table:
            in_table = True
            idx = [i for i, c in enumerate(cells) if "evidence" in c.lower()]
            column = idx[0] if idx else len(cells) - 1
            continue
        if NUMERIC_TABLE_SEP_RE.match(line.text) or column is None or column >= len(cells):
            continue
        if not PATH_EVIDENCE_RE.search(cells[column]):
            found.append(("A3", line.number, "prior-art row without a `file:line` in its evidence cell: {}".format(
                cells[0][:60])))
    return found


def lint(text: str) -> Tuple[List[Finding], List[Finding]]:
    lines, unclosed = _scan(text)
    blocking, defined = _check_ac_ids(lines)
    blocking += _check_ac_refs(lines, defined)
    blocking += _check_section_refs(lines, _heading_numbers(lines))
    if unclosed is not None:
        blocking.append(("B4", unclosed[0], "code fence opened on line {}{} is never closed; the lines after it were "
                         "not checked".format(unclosed[0], " in the Request section" if unclosed[1] else "")))
    advisory = _check_numbers(lines) + _check_vague(lines) + _check_evidence(lines)
    key = lambda f: (f[1], f[0])  # noqa: E731
    return sorted(blocking, key=key), sorted(advisory, key=key)


def render_lint(blocking: List[Finding], advisory: List[Finding]) -> str:
    def block(title: str, items: List[Finding]) -> List[str]:
        return [title] + (["{}-{} {}".format(*f) for f in items] if items else ["(none)"])
    out = block("BLOCKING", blocking) + [""] + block("ADVISORY", advisory) + [
        "", "spec-lint: B{} A{}".format(len(blocking), len(advisory))]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------

def spec_hash(spec_path: str) -> str:
    try:
        with open(spec_path, "rb") as handle:
            raw = handle.read()
    except OSError as err:
        raise SpecError("cannot read {}: {}".format(spec_path, err))
    kept: List[bytes] = []
    in_header, dropped = True, False
    for line in raw.splitlines(keepends=True):
        if in_header and _H2_BYTES_RE.match(line):
            in_header = False
        if in_header and ((not dropped and line.startswith(_STATUS_PREFIX)) or line.startswith(_SELF_APPROVED_PREFIX)):
            dropped = dropped or line.startswith(_STATUS_PREFIX)
            continue
        kept.append(line)
    return "sha256:" + hashlib.sha256(b"".join(kept)).hexdigest()


def _insertion_index(lines: List[str]) -> int:
    """Index after the header lines (the `**Field**:` lines before the first `## ` heading)."""
    end = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
    bold = [i for i in range(1, end) if lines[i].startswith("**")]
    return bold[-1] + 1 if bold else 0


def _set_line(lines: List[str], prefix: str, value: Optional[str], after: Optional[str]) -> None:
    """Replace the line starting with `prefix` by `value`, delete it when value is None, else insert it after the
    line starting with `after` (or after the header lines)."""
    idx = next((i for i, l in enumerate(lines) if l.startswith(prefix)), None)
    if value is None:
        if idx is not None:
            del lines[idx]
        return
    if idx is not None:
        lines[idx] = value
        return
    anchor = next((i for i, l in enumerate(lines) if after and l.startswith(after)), None)
    if anchor is not None:
        lines.insert(anchor + 1, value)
        return
    at = _insertion_index(lines)
    if at == 0:  # no header lines: after the title and its blank line
        at = 2 if len(lines) > 1 and lines[1] == "" else min(1, len(lines))
        lines.insert(at, value)
        if at == 1:
            lines.insert(2, "")
        return
    lines.insert(at, value)


def edit_gate_report(gate_path: str, spec_value: Optional[str], unreviewed: Optional[str], clear_unreviewed: bool
                     ) -> None:
    """Rewrite the Spec hash and / or Unreviewed changes line of the report, atomically; nothing else changes."""
    if not os.path.isfile(gate_path):
        raise SpecError("no spec-gate report at {}".format(gate_path))
    raw = _read_text(gate_path, strict=True)
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.split(nl)
    if spec_value is not None:
        _set_line(lines, _HASH_PREFIX, "{} {}".format(_HASH_PREFIX, spec_value), None)
    if clear_unreviewed:
        _set_line(lines, _UNREVIEWED_PREFIX, None, None)
    if unreviewed is not None:
        _set_line(lines, _UNREVIEWED_PREFIX, "{} {}".format(_UNREVIEWED_PREFIX, unreviewed), _HASH_PREFIX)
    _atomic_write(gate_path, nl.join(lines))


def check_hash(spec_path: str, gate_path: str) -> Tuple[int, str]:
    if not os.path.isfile(gate_path):
        return 2, "no spec-gate report at {}".format(gate_path)
    lines = _read_text(gate_path).splitlines()
    recorded = None
    unreviewed = None
    for line in lines:
        m = _HASH_VALUE_RE.match(line)
        if m and recorded is None:
            recorded = m.group(1)
        if line.startswith(_UNREVIEWED_PREFIX):
            unreviewed = line[len(_UNREVIEWED_PREFIX):].strip() or "none recorded"
    if recorded is None:
        return 2, "no `**Spec hash**:` line in {}".format(gate_path)
    current = spec_hash(spec_path)
    if current != recorded:
        return 1, "spec changed after its last review; unreviewed changes: {}".format(unreviewed or "none recorded")
    if unreviewed is not None:
        return 1, "spec unchanged since its last review round; unreviewed changes: {}".format(unreviewed)
    return 0, "spec unchanged since its last review ({})".format(recorded)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="spec_lint.py", description="Mechanical checks and hash of a spec.md")
    sub = parser.add_subparsers(dest="verb", required=True)
    lint_p = sub.add_parser("lint", help="run the blocking B1-B4 and advisory A1-A3 checks")
    lint_p.add_argument("feature_dir")
    hash_p = sub.add_parser("hash", help="print, record or check the spec hash (the Status and self-approval header lines are excluded)")
    hash_p.add_argument("feature_dir")
    group = hash_p.add_mutually_exclusive_group()
    group.add_argument("--record", action="store_true", help="record the hash in gates/spec-gate.md")
    group.add_argument("--unreviewed", metavar="IDS", help="record the ids of fixes made after the recorded hash")
    group.add_argument("--check", action="store_true", help="compare the spec with the recorded hash")
    for p in (lint_p, hash_p):
        p.add_argument("--root", default=".", help="project root (default: the current directory)")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    feature = os.path.join(os.path.abspath(args.root), args.feature_dir)
    spec_path = os.path.join(feature, "spec.md")
    gate_path = os.path.join(feature, "gates", "spec-gate.md")
    try:
        if not os.path.isfile(spec_path):
            raise SpecError("no spec.md at {}".format(spec_path))
        if args.verb == "lint":
            blocking, advisory = lint(_read_text(spec_path))
            report = render_lint(blocking, advisory)
            _atomic_write(os.path.join(feature, "gates", "spec-lint.txt"), report)
            sys.stdout.write(report)
            return 1 if blocking else 0
        current = spec_hash(spec_path)
        if args.record:
            edit_gate_report(gate_path, current, None, True)
            print("recorded {}".format(current))
        elif args.unreviewed is not None:
            if not args.unreviewed.strip():
                raise SpecError("--unreviewed needs at least one id")
            edit_gate_report(gate_path, None, " ".join(args.unreviewed.split()), False)
            print("unreviewed changes: {}".format(" ".join(args.unreviewed.split())))
        elif args.check:
            code, message = check_hash(spec_path, gate_path)
            if code == 2:
                raise SpecError(message)
            _atomic_write(os.path.join(feature, "gates", "spec-hash.txt"), message + "\n")
            print(message)
            return code
        else:
            print(current)
        return 0
    except SpecError as err:
        sys.stderr.write("spec_lint: {}\n".format(err))
        return 2


if __name__ == "__main__":
    sys.exit(main())
