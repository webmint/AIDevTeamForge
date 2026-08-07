"""_segment.py -- command-boundary detection signals for profile_helper.

Two independent signals locate a per-command span in a transcript event
stream (both documented at plan 70's OQ3 + Phase 0 RESULTS):

  1. Primary: a `user` line whose string content starts with the harness's
     command-invocation marker `<command-name>/<name></command-name>`.
     Accepts BOTH the pre-63 bare form (`/plan`) and the post-63 namespaced
     form (`/devforge:plan`) -- `match_command_marker` strips an optional
     leading `devforge:` before returning the bare command name.  `/clear`
     uses the same marker shape and is recognized the same way; the caller
     (`_bucket.py`) treats "clear" as a reset-to-preamble boundary rather
     than a named command segment.

  2. Fallback: a `Bash` tool_use whose `input.command` contains one of the
     known pipeline commands' helper-binary stem (e.g. "plan_helper").
     This covers a MODEL-invoked command (plan 63 made 13 pipeline commands
     model-invocable) whose invocation marker shape is unknown/undocumented
     -- the helper call it makes is generation-independent ground truth.
     `match_helper_fallback` uses `\\b` word-boundary matching so a stem
     that is a substring of another stem (e.g. "review_helper" inside
     "pr_review_helper") cannot cross-match: underscores are word
     characters, so `\\breview_helper\\b` does not match inside
     "pr_review_helper" (no boundary at the "_" before "review").

KNOWN_COMMANDS / HELPER_STEMS are the 20 pipeline + setup command names
from the plan's Analyzer semantics section; "init-forge" maps to the
irregular `init_helper` binary name (all others are a straightforward
hyphen-to-underscore + "_helper" transform) -- verified against the actual
`src/devforge/lib/*_helper{,.py}` file list.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Command marker regex
# ---------------------------------------------------------------------------

# Matches at the START of the user-line string content.  Captures the bare
# command name, stripping an optional "devforge:" namespace prefix (plan 63).
_COMMAND_MARKER_RE = re.compile(
    r"^<command-name>/(?:devforge:)?([A-Za-z0-9_-]+)</command-name>"
)


def match_command_marker(text):
    # type: (str) -> Optional[str]
    """Return the lowercased command name if `text` opens with a
    <command-name> marker, else None.  "clear" is a valid return value.
    """
    if not isinstance(text, str):
        return None
    m = _COMMAND_MARKER_RE.match(text)
    if not m:
        return None
    return m.group(1).lower()


# ---------------------------------------------------------------------------
# Known commands -> helper binary stem
# ---------------------------------------------------------------------------

# Verified against `ls src/devforge/lib/*_helper*` (2026-08-07): every stem
# is <name-with-underscores>_helper EXCEPT init-forge, whose binary is
# `init_helper` (not `init_forge_helper`).
HELPER_STEMS = {
    "research": "research_helper",
    "discover": "discover_helper",
    "specify": "specify_helper",
    "plan": "plan_helper",
    "breakdown": "breakdown_helper",
    "implement": "implement_helper",
    "pr-review": "pr_review_helper",
    "audit": "audit_helper",
    "review": "review_helper",
    "verify": "verify_helper",
    "summarize": "summarize_helper",
    "finalize": "finalize_helper",
    "report-bug": "report_bug_helper",
    "grill": "grill_helper",
    "spec-check": "spec_check_helper",
    "fix": "fix_helper",
    "init-forge": "init_helper",
    "generate-docs": "generate_docs_helper",
    "configure": "configure_helper",
    "constitute": "constitute_helper",
}  # type: Dict[str, str]

KNOWN_COMMANDS = tuple(sorted(HELPER_STEMS.keys()))

# One compiled word-boundary regex per stem, built once at import time.
_HELPER_STEM_PATTERNS = {
    cmd: re.compile(r"\b" + re.escape(stem) + r"\b")
    for cmd, stem in HELPER_STEMS.items()
}  # type: Dict[str, "re.Pattern"]


def match_helper_fallback(bash_command):
    # type: (str) -> Optional[str]
    """Return the known command name whose helper stem appears (as a whole
    word) in `bash_command`, or None.

    Iteration order follows KNOWN_COMMANDS (sorted); stems are disjoint
    under word-boundary matching so ordering does not affect the result in
    practice, but a deterministic order keeps behavior reproducible.
    """
    if not bash_command:
        return None
    for cmd in KNOWN_COMMANDS:
        if _HELPER_STEM_PATTERNS[cmd].search(bash_command):
            return cmd
    return None
