"""spec_acs.py -- shared spec Acceptance Criteria parser.

Public surface
--------------
  parse_acs(source) -> list[dict]
      Parse ``- [ ] **AC-N**: …`` / ``- [x] **AC-N**: …`` lines from a spec
      text string or a path to a spec file. Returns a list of AC dicts, one
      per AC found in the ## Acceptance Criteria section.

      Each dict has:
        id        str   — "AC-1", "AC-2", …
        text      str   — the EARS sentence (first line + any continuation)
        checked   bool  — True when the box is ``- [x]``
        subsection str  — the nearest ### subsection heading above this AC,
                          e.g. "5.1 Tooling / artifact presence and absence"

Behaviour
---------
  - Only lines inside the ## Acceptance Criteria section are processed;
    other sections (## 6. Out of Scope, ## 7. Technical Constraints, …) are
    ignored.
  - Subsections (### 5.N …) are tracked and attached to every AC found below
    them. An AC that appears before any subsection heading carries an empty
    subsection string.
  - "N/A — <reason>" subsections that contain no ACs are skipped silently.
  - Non-AC lines (narrative, tables, "> Verification:" hints) are skipped.
  - Multi-line ACs: the spec format allows a continuation line (e.g. the
    "> Verification: …" hint block) directly after the checkbox. We capture
    only the first (checkbox) line as ``text`` because that line is the EARS
    sentence. This matches the AC-verifier agent's contract — it reads the
    sentence, not the hint.
  - Duplicate AC ids are accepted and returned in encounter order.
  - If the source has no ## Acceptance Criteria section, an empty list is
    returned (not an error).

Relocation note: this function originally lived in ``_verify/_ac.py``.
It moved to ``_shared/`` so multiple commands (``/verify``, ``/spec-check``)
can consume the parser without cross-command coupling — the ``_shared/``
always-copy pattern mirrors ``feature_scope.py`` and ``findings_schema.py``.
``_verify/_ac.py`` re-exports ``parse_acs`` from this module for back-compat
(its own ``merge_ac_results`` — the ``/verify``-specific AC-results table
merger — stays there, unrelated to this parser).

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches the start of the Acceptance Criteria section.
# Handles both numbered ("## 5. Acceptance Criteria") and plain variants.
_SECTION_RE = re.compile(r"^##\s+\d*\.?\s*Acceptance Criteria", re.IGNORECASE)

# Matches any level-2 section heading that would end the AC section.
# We stop when we see a new ## heading (but NOT a ### subsection heading).
_NEXT_LEVEL2_RE = re.compile(r"^##\s+", re.IGNORECASE)

# Matches a ### subsection heading inside the AC section.
_SUBSECTION_RE = re.compile(r"^###\s+(.+)$")

# Matches an AC checkbox line:
#   - [ ] **AC-N**: <text>
#   - [x] **AC-N**: <text>   (checked variant)
# The checkbox may be lowercase x or uppercase X.
_AC_LINE_RE = re.compile(
    r"^- \[([xX ])\]\s+\*\*AC-(\d+)\*\*:\s+(.*)"
)


# ---------------------------------------------------------------------------
# parse_acs
# ---------------------------------------------------------------------------


def parse_acs(source):
    # type: (str) -> List[Dict]
    """Parse AC checkboxes from a spec text or path.

    Parameters
    ----------
    source : str
        Either a path to a spec file (checked via os.path.exists) or the raw
        spec text. When it is a path, the file is read as UTF-8 text.

    Returns
    -------
    list of dict
        One dict per AC found, in encounter order. Empty list if the AC
        section is absent or contains no AC checkboxes.

    Dict shape:
        {
            "id":         "AC-N",           # e.g. "AC-1"
            "text":       "<EARS sentence>", # stripped
            "checked":    bool,             # True when - [x]
            "subsection": "<### heading>",  # e.g. "5.1 Tooling / …"
        }
    """
    # Resolve source → text.
    if os.path.exists(source):
        try:
            with open(source, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return []
    else:
        text = source

    lines = text.splitlines()
    acs = []  # type: List[Dict]

    # Locate the ## Acceptance Criteria section.
    in_section = False
    current_subsection = ""  # type: str

    for line in lines:
        # --- Section entry ---
        if not in_section:
            if _SECTION_RE.match(line):
                in_section = True
            continue

        # --- Section exit: a new ## heading ends the AC section ---
        if _NEXT_LEVEL2_RE.match(line):
            break

        # --- Track ### subsection headings ---
        sub_m = _SUBSECTION_RE.match(line)
        if sub_m:
            current_subsection = sub_m.group(1).strip()
            continue

        # --- Capture AC checkbox lines ---
        ac_m = _AC_LINE_RE.match(line)
        if ac_m:
            check_char = ac_m.group(1)
            ac_num = ac_m.group(2)
            ac_text = ac_m.group(3).strip()
            acs.append(
                {
                    "id": "AC-{0}".format(ac_num),
                    "text": ac_text,
                    "checked": check_char.lower() == "x",
                    "subsection": current_subsection,
                }
            )

    return acs
