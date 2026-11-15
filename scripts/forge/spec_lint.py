#!/usr/bin/env python3
"""Mechanical checks of a feature's spec.md, and the hash that tells /plan whether the spec changed after its review.

Four verbs. `lint` runs the blocking checks B1-B5 and the advisory checks A1-A4; `labels` runs the label checks B5 and
A4 (and B4) on one file, a Format 2 `plan.md`; `scope` prints the size signals of a Format 2 spec; `hash` computes,
records and checks the spec hash kept in the spec-gate report (the hash leaves out the `**Status**:` and
`Self-approved (autonomous mode` header lines).

Usage:
  python3 scripts/forge/spec_lint.py lint <feature-dir> [--root <dir>]
  python3 scripts/forge/spec_lint.py labels <file> [--root <dir>]
  python3 scripts/forge/spec_lint.py scope <feature-dir> [--root <dir>]
  python3 scripts/forge/spec_lint.py hash <feature-dir> [--root <dir>] [--record | --unreviewed "<ids>" | --check]
      --root <dir>   project root; the feature dir (`specs/<KEY|NNN>-name`) or the file is resolved against it, and its
                     `.claude/project-config.json` gives the ticket keys of B5 and A4 (default: the current dir)
  `hash` takes at most one of its three flags; without one it prints `sha256:<hex>` and writes nothing.

Blocking (B) and advisory (A) checks, all on `<feature-dir>/spec.md` (the `## Request (verbatim)` section, fenced code
blocks and, where noted, code spans and quoted text are skipped; heading lines are checked):
  B1  AC ids: `- [ ]` / `- [x]` lines whose bold id is `**AC-N**` (text may follow the id before the colon; ACs may
      sit under bold sub-headings). A duplicated id, a gap in 1..max, no AC at all, or a line that looks like an AC
      definition (`**AC-3:**`, `**AC-3a**`, no checkbox) but not in the `- [ ] **AC-N**:` form.
  B2  an `AC-N` outside the AC definitions that names no AC of the spec. Not checked: a reference qualified by the
      token right before it (a 3-digit spec number, a ticket key such as `PROJ-1301`, `spec`, `ticket`, `brief`,
      `contract`).
  B3  a `§N`, `§Na` or `§N.M` with no heading of that number (`## 2.`, `## 2a.`, `### 3.4 ...`). Not checked: a
      reference whose preceding word, separated from the `§` by whitespace alone, names another document (any word
      but a short list of function words) or is a 3-digit spec number (`054 §9.9`) or a ticket key
      (`PROJ-1301 §3`; not a standard name such as `UTF-8`). `(§9)`, `Source: §9`, `[§9]`
      are the spec's own. A list of references (`§7.3, §8`, `§3 / §4`) takes the qualification of its first member.
  B4  a fenced code block that is never closed (the lines after its opening were not checked).
  A1  numerical consistency: one noun with two or more numbers (a heuristic: two quantities with the same unit are a
      false positive).
  A2  a vague non-functional phrase in a sentence of Desired Behavior, Acceptance Criteria or Technical Constraints
      (a `## ` title containing one of these; a Format 2 spec's "Behaviour and Acceptance Criteria" too), with no number
      plus unit and no named standard in the same sentence.
  A3  evidence shape: a code span that looks like a path citation but has a bad line part (`:0`, `:L12`, `#L12`,
      `:12-`, a reversed range), and a `## 2a. Prior art` table row whose evidence cell has no `file:line`.
Label checks, only in a file with the header line `**Format**: 2` (before the first `## ` heading); code spans and
quoted text are skipped. A label-shaped id is capitals, an optional hyphen, then digits (`KD-2`, `D1`). It is known when
its prefix is a label of `.claude/storage-rules.md` "Labels" (AC, DEC, Q, RISK, CRIT, WARN, NOTE) or a multi-letter
standard name (`UTF-8`, `SHA-256`), when it is a short standard or product name (`S3`, `EC2`, `P95`, `HTML5`), or when
it is a ticket key of the project's `ISSUE_KEY_PATTERN` (`project-config.json`; only a pattern that starts with a
literal prefix, `PROJ-[0-9]+`, as in comment_lint.py; the generic Jira pattern would match `KD-2` and is not used).
Outside a definition a Forge machine id is known too (checklist ids `SG-26`, lint codes `B3-9`, escape `E1`, audit
`T1`, `F-3`, `S2`, gate counts and older finding ids `C<n> W<n> N<n> S<n>`, `W-1`, waves `W2`); Forge never defines
one in a spec or plan, so a definition of `S9`, `T2` or `W-3` is B5.
  B5  a label definition with an id that is not known: a list item that opens with the bold id (`- **KD-2** ...`,
      `- [ ] **D1** ...`), a heading that opens with the id (`### D1 ...`), or the first cell of a row in a table under
      a heading naming decisions, risks or questions, or with an `Id` or `#` header cell (`| KD-1 | ... |`).
  A4  the first cell of a row in any other table that opens with an id that is not known (product and standard names
      often sit there), and such an id anywhere else. Not checked: a reference qualified by the token right before it,
      as in B2 (`spec 001 D-3`).

Size signals (`scope`, `.claude/storage-rules.md` → "Feature Size"; only a spec with the `**Format**: 2` header line).
The thresholds are the SCOPE_* constants below, starting values. The `**Type**:` header line says which signals apply:
  feature     more than SCOPE_MAX_CRITERIA acceptance criteria (distinct `AC-N` definitions, the loose forms B1
              reports included)
  structural  more than SCOPE_MAX_AREA_ROWS rows in the `## ` section whose title holds "Affected Areas": the data rows
              of its tables, or its top-level list items when it has no table. A row naming many files counts once.
  Any other Type is read as feature. For information it also prints the distinct paths named there (in table rows,
the Files column when the table has one, else the whole row, and in list items, not in paragraphs; `x/{a,b}.ts` names
two; a `:line` part is dropped); they are no signal.
Parts (feature, SCOPE_MIN_PARTS or more) and layers (structural, SCOPE_MIN_LAYERS or more) are the agent's judgement:
the verb names them and does not count them. It also prints the spec's `**Scope**:` header line as recorded.

Spec hash: SHA-256 of spec.md without two header lines, both only before the first `## ` heading: the `**Status**:`
line and any line starting `Self-approved (autonomous mode` (the HARD GATE approval and the autonomous self-approval
add or edit them). A `**Status**:` line in the body counts.
  --record            write or replace `**Spec hash**: sha256:<hex>` in `gates/spec-gate.md` (after its header lines)
                      and drop any `**Unreviewed changes**:` line; keep a byte copy of the spec as reviewed,
                      `gates/spec.reviewed-<first 12 hex of the hash>.md` (kept once per hash; a damaged one is rewritten), which
                      `verify_citations.py report` checks finding citations of the spec against
  --unreviewed "<ids>"  write or replace `**Unreviewed changes**: <ids>` there
  --check             compare the spec with the recorded hash; print and write `gates/spec-hash.txt`:
                      `spec unchanged since its last review (sha256:...)` (exit 0: hash matches and no Unreviewed
                      line), `spec unchanged since its last review round; unreviewed changes: <ids>` (hash matches,
                      Unreviewed line present) or
                      `spec changed after its last review; unreviewed changes: <ids | none recorded>` (exit 1)
  Edits of spec-gate.md are atomic (temp file + os.replace) and touch only those two lines.

Output: `lint` writes `<feature-dir>/gates/spec-lint.txt` (a BLOCKING and an ADVISORY section, each line
`<code>-<spec.md line> <message>` (e.g. `B3-9`), then `spec-lint: B<n> A<n>`) and prints the same text. `labels` prints
the same form, ending `labels: B<n> A<n>` (line numbers of its file), and writes nothing; a file without the Format line
prints `labels: not checked (...)`. `scope` prints one line per signal and ends `scope: <signals> fired` or
`scope: no counted signal fired`, or prints `scope: not checked (...)` for a spec without the Format line; it writes
nothing.
Exit codes: lint and labels 0 no blocking finding (or not checked), 1 at least one; scope 0 whatever the signals; hash
--check 0 unchanged, 1
changed; every verb 2 for bad arguments or an unreadable or unwritable file, and --check 2 when there is no spec-gate
report or no recorded hash.
Stdlib only; Python 3.9+.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import shutil
import tempfile
from typing import Dict, List, NamedTuple, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comment_lint  # noqa: E402  (sibling module; path set above)
import spec_refs  # noqa: E402

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
# A ticket key (another spec or ticket) right before a reference qualifies it; an `AC-N` before another is a list.
_TICKET_BEFORE_RE = re.compile(r"(?<![A-Za-z0-9-])(?!AC-)([A-Z][A-Z0-9]+)-\d+(?:['’]s)?[*_]*\s+[*_]*$")
# Standard names with a number (`UTF-8`, `SHA-256`, `ISO-8601`) are not tickets.
_STANDARD_PREFIXES = frozenset("UTF SHA ISO RFC CVE CWE ECMA ES TLS SSL HTTP IEEE PEP JSR AES RSA MD W3C WCAG IEC".split())
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
# Labels (`.claude/storage-rules.md` "Labels"), checked only in a file with the `**Format**: 2` header line
_FORMAT2_RE = re.compile(r"^\*\*Format\*\*:[ \t]*2(?![\w.])")
_LABEL_PREFIXES = frozenset("AC DEC Q RISK CRIT WARN NOTE".split())
# Forge's machine ids: checklist ids (`SG-26`, `PG-`, `BG-`, `TR-`, `TL-`), lint codes (`B3-9`, `A1`, `C1`), escape
# ids (`E1`), audit theme, finding and lens ids (`T1`, `F-3`, `S2`), the `**Gate**:` counts and older finding ids
# (`C<n> W<n> N<n> S<n>`, `W-1`), and waves (`W2`)
_FORGE_ID_PREFIXES = frozenset("SG PG BG TR TL B A C E T F S W N".split())
# Standard and product names for the label checks: multi-letter prefixes (comment_lint.py's STANDARD_NAMES added), and
# exact tokens for the short ones, so that a single letter (`S9`, `X-1`) does not pass as a definition
_LABEL_STANDARD_PREFIXES = _STANDARD_PREFIXES | frozenset(
    "ASCII UTC GMT IPV OWASP BCP ANSI POSIX JIS GB EN DIN".split())
_LABEL_STANDARD_TOKENS = frozenset("S3 EC2 H264 H265 X509 P50 P90 P95 P99 SOC2 HTML5 CSS3".split())
# a table whose first cells define labels: under a heading naming one of these words, or with this header cell
_LABEL_TABLE_WORDS_RE = re.compile(r"\b(?:decisions?|risks?|questions?)\b", re.IGNORECASE)
_LABEL_TABLE_HEADERS = frozenset(("id", "#"))
_LABEL_RE = re.compile(r"(?<![\w-])([A-Z]+)-?\d+(?!\w)")
_LABEL_LIST_DEF_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?\*\*")
_LABEL_HEADING_DEF_RE = re.compile(r"^ {0,3}#{1,6}[ \t]+(?:\*\*)?")
_LABEL_ROW_DEF_RE = re.compile(r"^\s*\|\s*(?:\*\*)?")
_LABEL_SET = "AC, DEC, Q, RISK, CRIT, WARN, NOTE"
# Size signals (`.claude/storage-rules.md` → "Feature Size"): starting values, recalibrated on project data
SCOPE_MAX_CRITERIA = 20  # a feature spec: more acceptance criteria than this
SCOPE_MAX_AREA_ROWS = 15  # a structural spec: more rows in "Affected Areas" than this
SCOPE_MIN_PARTS = 3  # a feature spec: this many parts that can be delivered and checked separately (agent's judgement)
SCOPE_MIN_LAYERS = 3  # a structural spec: this many layers at once (agent's judgement)
_TYPE_RE = re.compile(r"^\*\*Type\*\*:[ \t]*[*_`]*([A-Za-z]+)")
_SCOPE_LINE_RE = re.compile(r"^\*\*Scope\*\*:")
_FILES_HEADERS = frozenset(("files", "file", "file(s)", "paths", "path"))
_PATH_SEPARATORS = " \t,;"
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_BRACE_RE = re.compile(r"\{([^{}]*)\}")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
_PATH_EXT_RE = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,9}$")
_PATH_LINE_PART_RE = re.compile(r"(?::\d+(?:-\d+)?|#L\d+(?:-L?\d+)?)+$")
_NOT_PATHS = frozenset(("e.g", "i.e", "etc", "vs"))
_AC_ID_RE = re.compile(r"AC-(\w+)")


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


def _ticket_before(text: str) -> bool:
    """True when `text` ends with a ticket key (`PROJ-1301`, `PROJ-1301's`) and whitespace; not a standard name."""
    m = _TICKET_BEFORE_RE.search(text)
    return bool(m) and m.group(1) not in _STANDARD_PREFIXES


def _qualifier(text: str, pos: int) -> bool:
    """True when the word before `pos`, separated from it by whitespace alone, names another document (B3)."""
    m = _QUALIFIER_RE.search(text[:pos])
    if not m:
        return False
    word = m.group(1)
    if _SPEC_NUMBER_RE.match(word) or _ticket_before(text[:pos]):
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
            if _SPEC_NUMBER_RE.match(word) or word in _AC_QUALIFIERS or _ticket_before(text[:m.start()]):
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


def is_format2(text: str) -> bool:
    """True when a header line (before the first `## ` heading) is `**Format**: 2`."""
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if _H2_RE.match(raw):
            return False
        if _FORMAT2_RE.match(raw):
            return True
    return False


# ---------------------------------------------------------------------------
# Size signals
# ---------------------------------------------------------------------------

class Scope(NamedTuple):
    kind: str  # "feature" | "structural"
    criteria: int
    rows: int  # rows of "Affected Areas": table data rows, else list items
    files: int  # distinct paths named there (information only)
    scope_line: Optional[str]  # the `**Scope**:` header line as recorded, or None
    fired: List[str]  # "criteria", "rows"


def _header(text: str) -> List[str]:
    """The lines before the first `## ` heading."""
    out: List[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if _H2_RE.match(raw):
            break
        out.append(raw)
    return out


def _words(text: str) -> List[str]:
    """`text` split at spaces, commas and semicolons outside `{...}`; each `{a,b}` expanded (`x/{a,b}.ts` names two)."""
    words, word, depth = [], "", 0
    for ch in _BR_RE.sub(" ", text.replace("](", " ")) + " ":
        depth += (ch == "{") - (ch == "}" and depth > 0)
        if ch in _PATH_SEPARATORS and depth == 0:
            words.append(word)
            word = ""
        else:
            word += ch
    out: List[str] = []
    for word in words:
        todo = [word]
        while todo:
            item = todo.pop()
            m = _BRACE_RE.search(item)
            if m is None or "," not in m.group(1) or len(out) + len(todo) > 1000:
                out.append(item)
                continue
            todo.extend(item[:m.start()] + part + item[m.end():] for part in m.group(1).split(","))
    return out


def _path_tokens(text: str, code: bool) -> List[str]:
    """Paths named in `text`: a token with a file extension or ending in `/`; in a code span also one with a `/` after
    its first character (`/plan` is a command); in plain text one holding two `/` (so `and/or` is not one)."""
    found = []
    for token in _words(text):
        token = token.strip("()[]{}<>*_\"'`").rstrip(".:")
        token = _PATH_LINE_PART_RE.sub("", token)
        if token.startswith("./"):
            token = token[2:]
        if not token or token.lower() in _NOT_PATHS or "://" in token:
            continue
        ext = bool(_PATH_EXT_RE.search(token))
        if (code and "/" in token.lstrip("/")) or ext or token.endswith("/") or token.count("/") >= 2:
            found.append(token)
    return found


def _affected_areas(lines: List[Line]) -> Tuple[int, set]:
    """(rows, distinct paths) of the "Affected Areas" section. Rows: its tables' data rows, or its top-level list items
    (no leading indent) when it has no table. Paths: in its table rows (the Files column when the table has one, else the whole row) and list items; a
    paragraph is commentary and is not counted."""
    paths: set = set()
    table_rows = items = 0
    last_row, column = -1, None
    for line in lines:
        if "affected areas" not in line.section.lower() or line.heading:
            continue
        is_row = line.text.lstrip().startswith("|")
        cells = _table_cells(line.text) if is_row else []
        if is_row and last_row != line.number - 1:  # the header row of a new table
            names = [c.strip("*").strip().lower() for c in cells]
            column = next((i for i, n in enumerate(names) if n in _FILES_HEADERS), None)
            last_row = line.number
            continue
        last_row = line.number if is_row else -1
        if (is_row and NUMERIC_TABLE_SEP_RE.match(line.text)) or not (is_row or _LIST_ITEM_RE.match(line.text)):
            continue
        if is_row:
            table_rows += 1
        elif not line.text[:1].isspace():  # a nested item belongs to the row above it
            items += 1
        text = cells[column] if is_row and column is not None and column < len(cells) else line.text
        for _s, _e, content in spec_refs.code_spans(text):
            paths.update(_path_tokens(content, True))
        paths.update(_path_tokens(_without_code(text), False))
    return (table_rows or items), paths


def scope(text: str) -> Optional[Scope]:
    """The size signals of a Format 2 spec; None for another."""
    if not is_format2(text):
        return None
    header = _header(text)
    kinds = [m.group(1).lower() for m in (_TYPE_RE.match(l) for l in header) if m]
    kind = "structural" if kinds and kinds[0] == "structural" else "feature"
    scope_line = next((l.rstrip() for l in header if _SCOPE_LINE_RE.match(l)), None)
    lines, _unclosed = _scan(text)
    criteria = len({m.group(1) for m in (_AC_ID_RE.search(l.text) for l in lines if _AC_DEF_RE.match(l.text)
                                         or _loose_ac(l)) if m})
    rows, paths = _affected_areas(lines)
    fired = []
    if kind == "feature" and criteria > SCOPE_MAX_CRITERIA:
        fired.append("criteria")
    if kind == "structural" and rows > SCOPE_MAX_AREA_ROWS:
        fired.append("rows")
    return Scope(kind, criteria, rows, len(paths), scope_line, fired)


def render_scope(result: Scope) -> str:
    def signal(name: str, applies: bool, limit: int) -> str:
        if not applies:
            return "(not a signal for a {} spec)".format(result.kind)
        return "(signal: more than {}): {}".format(limit, "fired" if name in result.fired else "not fired")
    feature = result.kind == "feature"
    judge = ("{} or more parts that can be delivered and checked separately".format(SCOPE_MIN_PARTS) if feature else
             "{} or more layers at once (database, API, interface, another module)".format(SCOPE_MIN_LAYERS))
    out = [
        "type: {}".format(result.kind),
        "criteria: {} {}".format(result.criteria, signal("criteria", feature, SCOPE_MAX_CRITERIA)),
        "rows in Affected Areas: {} {}".format(result.rows, signal("rows", not feature, SCOPE_MAX_AREA_ROWS)),
        "files named in Affected Areas: {} (information, not a signal)".format(result.files),
        "agent's judgement: {}".format(judge),
        result.scope_line or "Scope line: none",
        "scope: {} fired".format(", ".join(result.fired)) if result.fired else "scope: no counted signal fired",
    ]
    return "\n".join(out) + "\n"


def project_key(root: str) -> Optional["re.Pattern[str]"]:
    """`ISSUE_KEY_PATTERN` of `<root>/.claude/project-config.json` when it starts with a literal prefix, else None."""
    try:
        with open(os.path.join(root, ".claude", "project-config.json"), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    value = data.get("ISSUE_KEY_PATTERN", "") if isinstance(data, dict) else ""
    return comment_lint.issue_key_regex(value) if isinstance(value, str) else None


def _known_label(token: str, prefix: str, key: Optional["re.Pattern[str]"], definition: bool) -> bool:
    """A label, a ticket key or a standard name; outside a definition also a Forge machine id."""
    return (prefix in _LABEL_PREFIXES or prefix in _LABEL_STANDARD_PREFIXES or token in _LABEL_STANDARD_TOKENS
            or (key is not None and key.fullmatch(token) is not None)
            or (not definition and prefix in _FORGE_ID_PREFIXES))


def _label_table(heading: str, header_row: str) -> bool:
    """True when a table defines labels in its first cells (a Decisions, Risks or Questions heading, or an `Id` / `#`
    header cell)."""
    cells = _table_cells(header_row)
    first = cells[0].strip("*").strip().lower() if cells else ""
    return bool(_LABEL_TABLE_WORDS_RE.search(heading)) or first in _LABEL_TABLE_HEADERS


def _check_labels(lines: List[Line], key: Optional["re.Pattern[str]"]) -> Tuple[List[Finding], List[Finding]]:
    """(B5, A4) of a Format 2 file: label definitions and references outside the label set."""
    blocking: List[Finding] = []
    advisory: List[Finding] = []
    heading, last_row, defining_table = "", -1, False
    for line in lines:
        if line.heading:
            heading = line.text
        is_row = line.text.lstrip().startswith("|")
        if is_row and last_row != line.number - 1:  # the header row of a new table
            defining_table = _label_table(heading, line.text)
        last_row = line.number if is_row else -1
        text = _without_code(line.text, _MASK)
        text = _blank_spans(text, [(m.start(), m.end()) for m in _QUOTED_RE.finditer(text)], _MASK)
        defined_at, what = -1, ""
        for regex, kind in ((_LABEL_LIST_DEF_RE, "item"), (_LABEL_HEADING_DEF_RE, "heading"),
                            (_LABEL_ROW_DEF_RE, "row")):
            m = regex.match(text)
            if m and _LABEL_RE.match(text, m.end()):
                defined_at, what = m.end(), kind
                break
        blocks = what in ("item", "heading") or (what == "row" and defining_table)
        for m in _LABEL_RE.finditer(text):
            token = m.group(0)
            definition = m.start() == defined_at
            if _known_label(token, m.group(1), key, definition and blocks):
                continue
            if definition and blocks:
                blocking.append(("B5", line.number, "`{}` defines a label outside `.claude/storage-rules.md` "
                                 "\"Labels\" ({}, or the project's ticket keys); a product or standard name: reword so "
                                 "the {} does not open with it".format(token, _LABEL_SET, what)))
                continue
            if definition:
                advisory.append(("A4", line.number, "table row opens with `{}`, not a label of "
                                 "`.claude/storage-rules.md` \"Labels\" (a product or standard name is fine)".format(
                                     token)))
                continue
            word = _preceding_word(text, m.start()).lower()
            if _SPEC_NUMBER_RE.match(word) or word in _AC_QUALIFIERS or _ticket_before(text[:m.start()]):
                continue
            advisory.append(("A4", line.number, "`{}` is not a label of `.claude/storage-rules.md` \"Labels\"; use "
                             "one, or name its source (`spec 001 D-3`)".format(token)))
    return blocking, advisory


def labels(text: str, key: Optional["re.Pattern[str]"] = None) -> Tuple[List[Finding], List[Finding]]:
    """The label checks alone (B5, A4, and B4 for a fence never closed) of a Format 2 file; ([], []) for another."""
    if not is_format2(text):
        return [], []
    lines, unclosed = _scan(text)
    blocking, advisory = _check_labels(lines, key)
    if unclosed is not None:
        blocking.append(_unclosed_finding(unclosed))
    order = lambda f: (f[1], f[0])  # noqa: E731
    return sorted(blocking, key=order), sorted(advisory, key=order)


def _unclosed_finding(unclosed: Tuple[int, bool]) -> Finding:
    return ("B4", unclosed[0], "code fence opened on line {}{} is never closed; the lines after it were not "
            "checked".format(unclosed[0], " in the Request section" if unclosed[1] else ""))


def lint(text: str, key: Optional["re.Pattern[str]"] = None) -> Tuple[List[Finding], List[Finding]]:
    """All checks; B5 and A4 only in a Format 2 spec. `key` is the project's ticket-key pattern (`project_key`)."""
    lines, unclosed = _scan(text)
    blocking, defined = _check_ac_ids(lines)
    blocking += _check_ac_refs(lines, defined)
    blocking += _check_section_refs(lines, _heading_numbers(lines))
    if unclosed is not None:
        blocking.append(_unclosed_finding(unclosed))
    advisory = _check_numbers(lines) + _check_vague(lines) + _check_evidence(lines)
    if is_format2(text):
        label_blocking, label_advisory = _check_labels(lines, key)
        blocking += label_blocking
        advisory += label_advisory
    order = lambda f: (f[1], f[0])  # noqa: E731
    return sorted(blocking, key=order), sorted(advisory, key=order)


def render_lint(blocking: List[Finding], advisory: List[Finding], name: str = "spec-lint") -> str:
    def block(title: str, items: List[Finding]) -> List[str]:
        return [title] + (["{}-{} {}".format(*f) for f in items] if items else ["(none)"])
    out = block("BLOCKING", blocking) + [""] + block("ADVISORY", advisory) + [
        "", "{}: B{} A{}".format(name, len(blocking), len(advisory))]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------

def read_spec_bytes(spec_path: str) -> bytes:
    try:
        with open(spec_path, "rb") as handle:
            return handle.read()
    except OSError as err:
        raise SpecError("cannot read {}: {}".format(spec_path, err))


def spec_hash(spec_path: str, raw: Optional[bytes] = None) -> str:
    """The spec hash of the file, or of `raw` (its bytes, already read) when given."""
    if raw is None:
        raw = read_spec_bytes(spec_path)
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


def snapshot_path(spec_path: str, digest: str) -> str:
    """`gates/spec.reviewed-<first 12 hex>.md` next to the spec-gate report."""
    hex_part = digest.split(":", 1)[-1][:12]
    return os.path.join(os.path.dirname(spec_path), "gates", "spec.reviewed-{}.md".format(hex_part))


def write_snapshot(spec_path: str, digest: str, raw: bytes) -> str:
    """Keep `raw` (the bytes that were hashed) as the spec as reviewed. A valid snapshot of the same hash (one whose own
    bytes hash to it) is kept, so it stays the copy the first review of that version read; the HARD GATE's Status and
    self-approval edits do not change the hash. A damaged or foreign file of that name is replaced."""
    target = snapshot_path(spec_path, digest)
    try:
        if not os.path.islink(target) and os.path.isfile(target):
            with open(target, "rb") as handle:
                if spec_hash(target, handle.read()) == digest:
                    return target
        folder = os.path.dirname(target)
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".spec.reviewed-", suffix=".tmp", dir=folder)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
            shutil.copymode(spec_path, tmp)
            os.replace(tmp, target)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    except OSError as err:
        raise SpecError("cannot write {}: {}".format(target, err))
    return target


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
    lint_p = sub.add_parser("lint", help="run the blocking B1-B5 and advisory A1-A4 checks")
    lint_p.add_argument("feature_dir")
    labels_p = sub.add_parser("labels", help="run the label checks B5 and A4 on one Format 2 file (a plan.md)")
    labels_p.add_argument("file")
    scope_p = sub.add_parser("scope", help="print the size signals of a Format 2 spec (always exit 0)")
    scope_p.add_argument("feature_dir")
    hash_p = sub.add_parser("hash", help="print, record or check the spec hash (the Status and self-approval header lines are excluded)")
    hash_p.add_argument("feature_dir")
    group = hash_p.add_mutually_exclusive_group()
    group.add_argument("--record", action="store_true", help="record the hash in gates/spec-gate.md")
    group.add_argument("--unreviewed", metavar="IDS", help="record the ids of fixes made after the recorded hash")
    group.add_argument("--check", action="store_true", help="compare the spec with the recorded hash")
    for p in (lint_p, labels_p, scope_p, hash_p):
        p.add_argument("--root", default=".", help="project root (default: the current directory)")
    return parser


def _run_labels(root: str, name: str) -> int:
    path = os.path.join(root, name)
    if not os.path.isfile(path):
        raise SpecError("no file at {}".format(path))
    text = _read_text(path)
    if not is_format2(text):
        print("labels: not checked ({} has no `**Format**: 2` header line)".format(name))
        return 0
    blocking, advisory = labels(text, project_key(root))
    sys.stdout.write(render_lint(blocking, advisory, "labels"))
    return 1 if blocking else 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    root = os.path.abspath(args.root)
    if args.verb == "labels":
        try:
            return _run_labels(root, args.file)
        except SpecError as err:
            sys.stderr.write("spec_lint: {}\n".format(err))
            return 2
    feature = os.path.join(root, args.feature_dir)
    spec_path = os.path.join(feature, "spec.md")
    gate_path = os.path.join(feature, "gates", "spec-gate.md")
    try:
        if not os.path.isfile(spec_path):
            raise SpecError("no spec.md at {}".format(spec_path))
        if args.verb == "scope":
            result = scope(_read_text(spec_path))
            if result is None:
                print("scope: not checked (spec.md has no `**Format**: 2` header line)")
            else:
                sys.stdout.write(render_scope(result))
            return 0
        if args.verb == "lint":
            blocking, advisory = lint(_read_text(spec_path), project_key(root))
            report = render_lint(blocking, advisory)
            _atomic_write(os.path.join(feature, "gates", "spec-lint.txt"), report)
            sys.stdout.write(report)
            return 1 if blocking else 0
        raw = read_spec_bytes(spec_path)
        current = spec_hash(spec_path, raw)
        if args.record:
            snapshot = write_snapshot(spec_path, current, raw)  # first: a recorded hash always has its snapshot
            edit_gate_report(gate_path, current, None, True)
            print("recorded {} (snapshot {})".format(current, os.path.relpath(snapshot, feature)))
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
