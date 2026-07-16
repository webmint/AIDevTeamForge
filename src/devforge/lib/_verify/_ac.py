"""_ac.py — AC-result merger for /verify.

Relocation note: ``parse_acs`` (the spec ``## Acceptance Criteria`` parser)
moved to ``_shared/spec_acs.py`` so multiple commands (``/verify``,
``/spec-check``) can consume it without cross-command coupling. It is
re-exported below (``from _shared.spec_acs import parse_acs``) as a
deliberate back-compat shim — existing callers that do
``from _verify._ac import parse_acs`` (or ``from ._ac import parse_acs``)
keep working with zero churn. This is not an accidental dual import path;
new code should prefer importing ``parse_acs`` directly from
``_shared.spec_acs``.

Public surface
--------------
  parse_acs(source) -> list[dict]
      Re-exported from ``_shared.spec_acs`` — see that module for the full
      docstring (behaviour, dict shape, edge cases).

  merge_ac_results(acs, agent_report_text) -> list[dict]
      Merge the ac-verifier agent's ``### Results`` table into the structured
      AC list produced by ``parse_acs``.

      Parameters
      ----------
      acs : list[dict]
          The structured AC list from ``parse_acs``.  Modified by copy —
          the input list is not mutated.
      agent_report_text : str
          The full text of the ac-verifier's markdown report (the
          ``## AC Verification Report`` block).  The ``### Results`` table
          is extracted from this text.

      Returns a new list[dict], one dict per AC in ``acs``, each with the
      original four fields plus:
        status   str  — agent status string (e.g. "PASS", "FAIL", "PARTIAL",
                        "MANUAL", "PASS (code)", "FAIL (code)", "PARTIAL (code)")
                        or "UNVERIFIED" when the agent produced no row for this AC.
        evidence str  — the Evidence cell from the agent's table, stripped,
                        or "" when the AC is UNVERIFIED.

      Agent rows for AC ids not present in ``acs`` are silently ignored.

Behaviour (merge_ac_results)
-----------------------------
  - The ``### Results`` section is located by scanning for the heading
    ``### Results`` (case-insensitive).  The table header row and the
    separator row (``|---|---|---|``) are skipped.  Parsing stops at the next
    ``###`` or ``##`` heading.
  - Each data row is split on ``|``; the AC id is the second cell (stripped),
    the status is the third cell (stripped), the evidence is the fourth cell
    (stripped and joined when multiple pipes exist in the evidence cell).
  - Agent rows whose AC id does not appear in ``acs`` are ignored.
  - ACs with no corresponding agent row receive ``status="UNVERIFIED"`` and
    ``evidence=""``.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from _shared.spec_acs import parse_acs  # noqa: F401  -- relocated to _shared.spec_acs; re-exported for back-compat

# ---------------------------------------------------------------------------
# merge_ac_results
# ---------------------------------------------------------------------------

# Matches the ### Results heading (case-insensitive, optional leading #s).
_RESULTS_HEADING_RE = re.compile(r"^###\s+Results\s*$", re.IGNORECASE)

# Matches any level-2 or level-3 heading — used to stop Results parsing.
_HEADING_23_RE = re.compile(r"^##")

# Matches the table separator row: lines like |---|---|---| (all dashes/pipes).
_TABLE_SEP_RE = re.compile(r"^\|[-| ]+\|$")

# Matches the table header row: | AC | Status | Evidence |
# We skip it by checking whether the first data cell looks like a header word.
_HEADER_CELL_RE = re.compile(r"^ac$", re.IGNORECASE)

# Known valid status values from ac-verifier.md Output contract.
# The (code) suffix variants are the code-reading fallback markers.
_KNOWN_STATUSES = frozenset([
    "PASS", "FAIL", "PARTIAL", "MANUAL",
    "PASS (code)", "FAIL (code)", "PARTIAL (code)",
])


def _parse_results_table(agent_report_text):
    # type: (str) -> Dict[str, Tuple[str, str]]
    """Extract per-AC status+evidence from the agent's ``### Results`` table.

    Returns a dict mapping AC id (e.g. "AC-1") → (status, evidence).
    Unknown / unparseable rows are skipped silently.
    """
    lines = agent_report_text.splitlines()
    in_results = False
    rows = {}  # type: Dict[str, Tuple[str, str]]

    for line in lines:
        stripped = line.strip()

        if not in_results:
            if _RESULTS_HEADING_RE.match(stripped):
                in_results = True
            continue

        # Stop at the next section heading (## or ###), but NOT at the first
        # line of the Results block itself (which we just passed above).
        if _HEADING_23_RE.match(stripped):
            break

        # Skip blank lines and separator rows.
        if not stripped or _TABLE_SEP_RE.match(stripped):
            continue

        # Parse a table data row: | AC | Status | Evidence |
        # Split on | to get cells between first and last pipe.
        # parts[0] = '' (before first |), parts[-1] = '' (after last |)
        # parts[1] = AC id, parts[2] = Status, parts[3..] = Evidence cells
        if not stripped.startswith("|"):
            continue
        parts = stripped.split("|")
        if len(parts) < 4:
            continue

        ac_id = parts[1].strip()
        status = parts[2].strip()
        # Evidence may contain pipes (rare but possible) — rejoin remaining cells.
        evidence = "|".join(parts[3:-1]).strip() if len(parts) > 4 else parts[3].strip()

        # Skip the header row: ac_id cell would be "AC" (the column name).
        if _HEADER_CELL_RE.match(ac_id):
            continue

        # Only accept rows with a recognisable AC id pattern.
        if not ac_id.startswith("AC-"):
            continue

        rows[ac_id] = (status, evidence)

    return rows


def merge_ac_results(acs, agent_report_text):
    # type: (List[Dict], str) -> List[Dict]
    """Merge the ac-verifier agent's per-AC results into the structured AC list.

    Parameters
    ----------
    acs : list[dict]
        The structured AC list from ``parse_acs``.  Not mutated.
    agent_report_text : str
        Full markdown text of the ac-verifier's report.  The ``### Results``
        table is extracted from this text.

    Returns
    -------
    list[dict]
        A new list.  Each dict has the original four keys (``id``, ``text``,
        ``checked``, ``subsection``) plus:
          ``status``   — from the agent's Status cell, or "UNVERIFIED".
          ``evidence`` — from the agent's Evidence cell, or "".

    Unknown agent rows (AC id not in ``acs``) are silently ignored.
    ACs with no agent row receive ``status="UNVERIFIED"`` and ``evidence=""``.
    """
    agent_rows = _parse_results_table(agent_report_text)

    merged = []  # type: List[Dict]
    for ac in acs:
        ac_id = ac["id"]
        if ac_id in agent_rows:
            status, evidence = agent_rows[ac_id]
        else:
            status = "UNVERIFIED"
            evidence = ""

        merged.append({
            "id": ac_id,
            "text": ac["text"],
            "checked": ac["checked"],
            "subsection": ac["subsection"],
            "status": status,
            "evidence": evidence,
        })

    return merged
