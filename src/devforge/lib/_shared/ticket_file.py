"""ticket_file.py -- write ticket captures to tickets/NNN-*.md in storage-rules.md format.

Sibling to bug_file.py (95-TICKET-CAPTURE-LANE-PLAN.md D3, OQ-1's ratified
PROMOTE arm).  A "ticket file" is a local capture document -- either a
noticed non-bug work item or pasted tracker-ticket text -- distinct from a
"ticket ID" (the tracker identifier TICKET_RE validates in
_shared/feature_alloc.py).  See src/devforge/storage-rules.md's
disambiguation rule (D2) for the two senses of "ticket" once that phase
lands; until then this module is its own authority for the shape.

Public surface
--------------
  file_ticket(tickets_dir, item, date, source) -> str
      Scan tickets_dir for the highest existing NNN prefix (its OWN
      sequence -- OQ-3 -- a populated bugs/ sibling never shifts this
      numbering), write ONE tickets/NNN-<slug>.md in the EXACT
      ticket-file format below, and return its path.  A ticket run
      writes exactly one file -- there is no batch form and no
      Related-Issues cross-linking (unlike file_bugs).

      Parameters
      ----------
      tickets_dir : str
          Path to the tickets/ directory.  Created if absent.
      item : dict
            {
              title:  str  -- optional.  Falls back to the first
                               non-empty line of body, then the literal
                               "Untitled ticket" (mirrors _format_bug's
                               own "Untitled bug" fallback).
              body:   str  -- the idea, or the pasted tracker text,
                               VERBATIM.  Never paraphrased or
                               re-wrapped; trimmed only by a trailing-
                               newline normalization (body.rstrip("\\n")
                               -- internal newlines are untouched).
              type:   str  -- enhancement | task | imported.  Vocabulary
                               is enforced by the caller (the CLI); this
                               module renders whatever string it is
                               given, matching file_bugs's own
                               trust-the-caller convention for severity.
              ticket: str  -- a tracker ID already shape-validated by
                               the caller via
                               _shared.feature_alloc.normalize_ticket,
                               or "" / absent -- rendered as "(none)".
            }
          Missing keys default to empty string (never guessed).
      date : str
          YYYY-MM-DD.  REQUIRED -- never call the clock.
      source : str
          Value for the **Source** field (manual | paste).  Vocabulary
          is enforced by the caller; this module renders it as given.

      Returns
      -------
      str  Path of the ticket file written.

Ticket file format
-------------------
  # Ticket NNN: [Short Title]

  **Status**: Open
  **Type**: enhancement | task | imported
  **Source**: manual | paste
  **Ticket**: [ID or (none)]
  **Reported**: [YYYY-MM-DD]

  [body, verbatim]

Numbering
---------
  Its OWN sequence, scanned ONCE from tickets_dir via the shared
  scan_highest_number() (promoted from bug_file.py -- OQ-1's ratified
  PROMOTE arm).  bugs/ and tickets/ never share a counter (OQ-3): both
  directories independently start at 001, which is why every reference
  to a ticket file names the directory (tickets/NNN-<slug>.md) rather
  than a bare NNN.

Slug sanitisation
------------------
  Reuses slugify() (promoted from bug_file.py -- OQ-1).  Same rule:
  lowercase, non-alphanumeric runs -> hyphen, collapse, strip, 30-char
  cap cut at a word boundary, never empty (an all-symbol title still
  slugifies to slugify()'s own literal fallback, unchanged by this
  promotion -- see bug_file.py).

  The title used for the filename slug is the SAME resolved title
  rendered in the H1 -- this module computes the title-with-fallback
  once (_resolve_title) and reuses it for both.  This is a deliberate
  divergence from bug_file.py's file_bugs/_format_bug pair, which
  independently default the slug source ("bug") and the H1 ("Untitled
  bug") to two different literals; that split is pre-existing behavior
  in bug_file.py and is left untouched there (OQ-1's promote arm is
  behavior-preserving), but this new module has no such history to
  preserve and uses one title everywhere.

Stdlib only.  Python 3.8+.  Atomic writes (mkstemp + os.replace),
matching file_bugs's convention.
"""

from __future__ import annotations

import os
import tempfile
from typing import Dict

from _shared.bug_file import scan_highest_number, slugify

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_title(item):
    # type: (Dict) -> str
    """Resolve the H1 / slug-source title.

    --title (item["title"]) wins when non-empty.  Otherwise falls back
    to the first non-empty line of the body -- a multi-paragraph pasted
    ticket body would make an absurd H1 verbatim, so only its first
    non-empty line is used.  When body is also empty or whitespace-only,
    falls back to the literal "Untitled ticket" (mirrors _format_bug's
    own "Untitled bug" pattern in bug_file.py).
    """
    title = (item.get("title") or "").strip()
    if title:
        return title
    body = item.get("body") or ""
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped:
            return stripped
    return "Untitled ticket"


def _format_ticket(number, item, date, source):
    # type: (int, Dict, str, str) -> str
    """Render a single ticket file in the format documented above."""
    title = _resolve_title(item)
    ticket_type = (item.get("type") or "").strip()
    ticket_id = (item.get("ticket") or "").strip()
    body = (item.get("body") or "").rstrip("\n")

    lines = []  # type: list
    lines.append("# Ticket {0:03d}: {1}".format(number, title))
    lines.append("")
    lines.append("**Status**: Open")
    lines.append("**Type**: {0}".format(ticket_type))
    lines.append("**Source**: {0}".format(source))
    lines.append("**Ticket**: {0}".format(ticket_id or "(none)"))
    lines.append("**Reported**: {0}".format(date))
    lines.append("")
    lines.append(body)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# file_ticket
# ---------------------------------------------------------------------------


def file_ticket(tickets_dir, item, date, source):
    # type: (str, Dict, str, str) -> str
    """Write one ticket file in tickets/NNN-<slug>.md format.

    See the module docstring for the item shape and the format.
    """
    os.makedirs(tickets_dir, exist_ok=True)

    # Scan ONCE for the highest existing ticket number -- its own
    # sequence, independent of any bugs/ sibling (OQ-3).
    highest = scan_highest_number(tickets_dir)
    number = highest + 1

    title = _resolve_title(item)
    slug = slugify(title)
    filename = "{0:03d}-{1}.md".format(number, slug)
    out_path = os.path.join(tickets_dir, filename)

    content = _format_ticket(number=number, item=item, date=date, source=source)

    # Atomic write
    tickets_abs_dir = os.path.dirname(out_path) or "."
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-ticket-",
        suffix=".md",
        dir=tickets_abs_dir,
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return out_path
