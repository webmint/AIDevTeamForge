"""memory.py -- single source of truth for .devforge/memory.md path + reads.

Problem this module closes
---------------------------
The ".devforge/memory.md" path literal is duplicated across every command
helper that preflights persistent cross-session memory, and it has already
drifted: some preflights read a path that exists in NO consumer install.
Two call sites even carry hand-written "DO NOT change this path" comments --
direct evidence that convention alone did not hold the invariant.

This module is the ONE place the path literal, the "is this file actually
useful" predicate, and the bounded-read shapes live. A later phase re-points
every existing caller at this module; this module itself does not touch any
caller (purely additive).

Public surface
--------------
  MEMORY_RELATIVE_PATH               -- the relative path, ".devforge/memory.md"
  memory_path(workspace_root)        -- join MEMORY_RELATIVE_PATH onto a root
  MEMORY_STATE_KEY                   -- canonical key/token: "memory_state"
  MEMORY_STATE_ABSENT / _STUB / _POPULATED
  MEMORY_STATE_ENUM                  -- (ABSENT, STUB, POPULATED) in that order
  probe_memory_state(workspace_root) -- -> one of MEMORY_STATE_ENUM
  memory_present(workspace_root)     -- -> bool
  read_memory_excerpt(workspace_root, n=DEFAULT_EXCERPT_LINES) -- -> str
  read_memory_digest(workspace_root, n=DEFAULT_DIGEST_LINES)   -- -> Optional[str]
  read_memory_context(workspace_root, excerpt_lines=DEFAULT_EXCERPT_LINES)
                                      -- -> dict with "present" / MEMORY_STATE_KEY
                                         / "excerpt", derived from a SINGLE
                                         read. Use this when a call site needs
                                         more than one of the values above --
                                         see "Single-scan combined accessor".

Why a three-state probe and not an existence check
----------------------------------------------------
The installer ships a fixed multi-line stub into EVERY install (headings +
HTML-comment placeholders, zero actual lessons). ".devforge/memory.md"
therefore almost always EXISTS, so a bare existence check is near-vacuous --
it would report "populated" for every fresh install. The three states
distinguish "no file at all" from "file present but nobody has filled it in
yet" from "file present and carries at least one real line", mirroring the
same shape used for the constitution's populate-guard detection.

A line counts as POPULATED content when it is: non-blank, AND does not start
with "#" after stripping (a markdown heading of any level), AND is not part
of a whole-line or multi-line HTML comment ("<!-- ... -->"). Multi-line
comments -- where the opening "<!--" and the closing "-->" are on DIFFERENT
lines -- are handled by tracking open/close state ACROSS the scan, not by
judging each line in isolation: an interior line of a multi-line comment
carries neither delimiter and must not be scored as content just because it
looks, line-by-line, like an ordinary line. A file with zero populated lines
is a "stub" (present, structurally empty of lessons); a file that cannot be
opened at all is "absent".

Design choice -- present-but-empty (0 bytes, or blank lines only) probes as
STUB, not ABSENT. Rationale: from a caller's point of view ("can I trust
this excerpt for context?"), a 0-byte file and the shipped stub are
indistinguishable in usefulness -- both carry zero lessons. ABSENT is
reserved for "no file at this path at all", a categorically different
condition (wrong workspace_root, pre-install state, deleted file). See
tests/lib/_shared/test_memory.py for the case that pins this choice.

Known, accepted scope boundary -- a "#" inside a fenced or indented code
block (e.g. a markdown code fence containing a shell comment like
"    # not a heading") strips to a leading "#" and is classified as a
heading, not content. This is a false NEGATIVE (a populated file could
probe as "stub"), which is the conservative, safe direction for this
module's purpose -- unlike a false POSITIVE, it never causes a structurally
empty file to be trusted as populated. This module does not parse markdown
code-fence context; this is an accepted limitation, not a defect.

Bounded reads -- byte-identical to existing callers
-----------------------------------------------------
Two shapes are already in use across existing preflights and must not
diverge when those callers are later re-pointed at this module:

  excerpt: first N RAW lines (line terminators preserved) joined with "",
           i.e. "".join(fh.readlines()[:N]), default N=40.
           Absent/unreadable -> "".

  digest:  first N NON-BLANK lines (terminators stripped) joined with
           "\\n", default N=5. Absent/unreadable -> None.
           Present-but-no-non-blank-lines -> "".
           Blank lines interleaved between real lines are SKIPPED, not
           counted toward N.

Single-scan combined accessor
------------------------------
Every existing preflight opens memory.md ONCE and derives both "is it
present" and "what does it say" from that single read. read_memory_context()
is the combined accessor for a call site that needs more than one of
present / state / excerpt -- it performs exactly one _read_lines() call and
derives every value from that one list, so a later correction to the scan
(or a concurrent-writer inconsistency between separate opens) only has to be
verified in one place, not at every call site that wires the three
single-purpose functions separately. The three single-purpose functions
(memory_present / probe_memory_state / read_memory_excerpt) stay -- they are
the right surface for a caller that needs only one value.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

# ---------------------------------------------------------------------------
# The path
# ---------------------------------------------------------------------------

# Relative path of the persistent cross-session memory file, joined against
# a workspace_root (the install root -- .devforge/ always lives there, even
# in wrapper mode, since it is install-root-scoped runtime state). This is
# the ONLY place this literal should live once callers are re-pointed here.
#
# Hardcoded forward-slash literal -- NOT os.path.join(".devforge", "memory.md").
# Every other path literal in this framework (command specs, schema constants
# like _specify/_schema.py's PHASE1_MANDATORY_READS, storage-rules.md, ...)
# uses the forward-slash convention, and at least one consumer of this
# constant does an EXACT STRING COMPARISON against it (not just a path join)
# to detect the memory-file slot. os.path.join is platform-dependent --
# on native Windows it would silently produce ".devforge\\memory.md", which
# no longer equals the forward-slash literal every comparison site expects.
# A pure join consumer (memory_path() below, or a pathlib Path / os.path.join
# caller) tolerates either separator, so this change is behavior-preserving
# for those; an exact-string-equality consumer is not, which is exactly why
# the literal must be pinned rather than platform-derived.
MEMORY_RELATIVE_PATH = ".devforge/memory.md"


def memory_path(workspace_root):
    # type: (str) -> str
    """Return the absolute-or-relative path to memory.md under workspace_root.

    No existence check is performed -- this is a pure path join.
    """
    return os.path.join(workspace_root, MEMORY_RELATIVE_PATH)


# ---------------------------------------------------------------------------
# Three-state probe
# ---------------------------------------------------------------------------

MEMORY_STATE_ABSENT = "absent"
MEMORY_STATE_STUB = "stub"
MEMORY_STATE_POPULATED = "populated"

# Stable order; also usable as a validation set.
MEMORY_STATE_ENUM = (MEMORY_STATE_ABSENT, MEMORY_STATE_STUB, MEMORY_STATE_POPULATED)

# Canonical key/token this value is carried under. This name is designed to
# be the stable key that downstream command specs and a maintainer-side gate
# will key on -- treat it as a stable public name, not an implementation
# detail, even though nothing keys on it yet.
MEMORY_STATE_KEY = "memory_state"

# Matches a line that is a whole-line HTML comment, e.g.
#   <!-- Populated during constitute -- records WHY decisions were made -->
_HTML_COMMENT_RE = re.compile(r"^<!--.*-->$")


def _is_populated_line(line):
    # type: (str) -> bool
    """True when `line` counts as real memory CONTENT.

    False for: blank lines, markdown headings (any level), and whole-line
    HTML comments. True for anything else non-blank (bullets, prose,
    tables, ...).

    Also used internally by _scan_lines() to judge the non-comment SEGMENTS
    of a line once any HTML comment spans have been carved out -- a segment
    is just a string, and the same blank/heading/whole-comment predicate
    applies to it unchanged.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return False
    if _HTML_COMMENT_RE.match(stripped):
        return False
    return True


def _scan_lines(lines):
    # type: (List[str]) -> bool
    """True when ANY line in `lines` carries real POPULATED content.

    Comment-state aware: an HTML comment whose opening "<!--" and closing
    "-->" are on DIFFERENT lines (a multi-line comment block) must not have
    its interior lines scored as content just because neither delimiter is
    present on those interior lines in isolation. Whether the scan is
    currently INSIDE an unterminated comment is therefore state carried
    ACROSS the line loop, not decided per line independently.

    This is the single scan implementation. Both probe_memory_state() and
    read_memory_context() call this -- the comment-tracking logic must not
    be duplicated a second time anywhere else in this module.

    Handles, in one state machine:
      - a comment that opens and closes on the SAME line (no state change)
      - an opener with real content BEFORE it on the same line (that
        content counts; whatever follows the opener does not, unless the
        comment also closes later on the same line)
      - a closer with real content TRAILING it on the same line (that
        trailing text counts as content)
      - a comment left unterminated through EOF (everything after the
        opener is swallowed; never scores as content)
      - any number of separate comment blocks in one file
    """
    in_comment = False
    for raw_line in lines:
        remainder = raw_line
        while True:
            if in_comment:
                close_at = remainder.find("-->")
                if close_at == -1:
                    # Comment continues past this line; nothing further on
                    # this line counts as content.
                    break
                in_comment = False
                remainder = remainder[close_at + 3 :]
                continue

            open_at = remainder.find("<!--")
            if open_at == -1:
                # No comment marker anywhere in what's left of this line --
                # judge the remaining segment as ordinary content.
                if _is_populated_line(remainder):
                    return True
                break

            before = remainder[:open_at]
            if _is_populated_line(before):
                return True

            close_at = remainder.find("-->", open_at + 4)
            if close_at == -1:
                # Opens here but does not close on this same line --
                # everything from here to EOF (or the eventual closer) is
                # inside the comment.
                in_comment = True
                break

            # Closes later on this SAME line -- re-examine whatever
            # follows the closer as ordinary content.
            remainder = remainder[close_at + 3 :]
            continue
    return False


def _read_lines(path):
    # type: (str) -> Optional[List[str]]
    """Return raw readlines() (line terminators preserved).

    Returns None when the file is missing or unreadable (any OSError).
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.readlines()
    except OSError:
        return None


def _read_text(path):
    # type: (str) -> Optional[str]
    """Return the full file text, or None when missing/unreadable."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def probe_memory_state(workspace_root):
    # type: (str) -> str
    """Return one of MEMORY_STATE_ENUM for the memory file under workspace_root.

    absent    -- file missing or unreadable.
    stub      -- present, but every line is blank, a heading, or (part of)
                 an HTML comment, including a multi-line comment block
                 (structurally empty of lessons). Includes a 0-byte file
                 and a file with only blank lines.
    populated -- present, with at least one line of real content.
    """
    lines = _read_lines(memory_path(workspace_root))
    if lines is None:
        return MEMORY_STATE_ABSENT

    if _scan_lines(lines):
        return MEMORY_STATE_POPULATED

    return MEMORY_STATE_STUB


def memory_present(workspace_root):
    # type: (str) -> bool
    """True when memory.md exists under workspace_root and can be opened."""
    return _read_lines(memory_path(workspace_root)) is not None


# ---------------------------------------------------------------------------
# Bounded reads
# ---------------------------------------------------------------------------

DEFAULT_EXCERPT_LINES = 40
DEFAULT_DIGEST_LINES = 5


def read_memory_excerpt(workspace_root, n=DEFAULT_EXCERPT_LINES):
    # type: (str, int) -> str
    """Return the first n RAW lines of memory.md, terminators preserved.

    Equivalent to "".join(fh.readlines()[:n]) on the file object.
    Absent/unreadable -> "".
    """
    lines = _read_lines(memory_path(workspace_root))
    if lines is None:
        return ""
    return "".join(lines[:n])


def read_memory_digest(workspace_root, n=DEFAULT_DIGEST_LINES):
    # type: (str, int) -> Optional[str]
    """Return the first n NON-BLANK lines of memory.md, joined with "\\n".

    Line terminators are stripped; blank lines are skipped, not counted
    toward n. Absent/unreadable -> None. Present-but-no-non-blank-lines
    -> "" (an empty string is NOT None -- it distinguishes "file exists but
    carries nothing" from "file could not be read at all").
    """
    text = _read_text(memory_path(workspace_root))
    if text is None:
        return None
    non_blank = [ln for ln in text.splitlines() if ln.strip()]
    return "\n".join(non_blank[:n])


# ---------------------------------------------------------------------------
# Single-scan combined accessor
# ---------------------------------------------------------------------------


def read_memory_context(workspace_root, excerpt_lines=DEFAULT_EXCERPT_LINES):
    # type: (str, int) -> dict
    """Return present/state/excerpt derived from a SINGLE read of memory.md.

    Performs exactly one _read_lines() call and derives every value in the
    returned dict from that one list -- a call site that needs more than
    one of memory_present() / probe_memory_state() / read_memory_excerpt()
    should use this instead of calling them separately (which would open
    the file up to three times and risk the three opens disagreeing under
    a concurrent writer).

    Returns a dict with exactly these keys:
      "present"        -- bool
      MEMORY_STATE_KEY  -- one of MEMORY_STATE_ENUM (the literal string
                           "memory_state")
      "excerpt"         -- str, same shape as read_memory_excerpt()

    Absent/unreadable -> {"present": False, MEMORY_STATE_KEY: MEMORY_STATE_ABSENT, "excerpt": ""}.
    """
    lines = _read_lines(memory_path(workspace_root))
    if lines is None:
        return {
            "present": False,
            MEMORY_STATE_KEY: MEMORY_STATE_ABSENT,
            "excerpt": "",
        }

    state = MEMORY_STATE_POPULATED if _scan_lines(lines) else MEMORY_STATE_STUB
    return {
        "present": True,
        MEMORY_STATE_KEY: state,
        "excerpt": "".join(lines[:excerpt_lines]),
    }
