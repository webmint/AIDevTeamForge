"""_dead_code.py — change-induced dead-code removal confirmation for /verify.

Public surface
--------------
  check_dead_code_removal(dead_code_rows, source_root) -> dict

      Mechanically confirms that every plan-declared ``DeadCodeRow`` was
      actually removed from the post-change source tree (plan 71 D4).

      Parameters
      ----------
      dead_code_rows : list[dict] or None
          The ``dead_code_rows`` array carried on ``breakdown-handoff.json``
          (plan 71 D8(b) passthrough — copied verbatim by
          ``breakdown_helper finalize-handoff`` from the sibling
          ``plan-handoff.json``'s ``breakdown_seeds.dead_code_rows``).  Each
          row dict carries the ``DeadCodeRow`` fields:
            "file"         : str — path to the file the row applies to
                             (relative to ``source_root``, or absolute)
            "anchor_token" : str — a literal string whose ABSENCE in the
                             post-change file is the pass condition
            "kind"         : str — "arm" | "function" | "param" | "import" |
                             "branch" (informational only — not used to
                             change the check logic)
            "why_dead"     : str — human-readable rationale (informational
                             only, carried through to the row result)
          ``None`` or ``[]`` means /plan declared no change-induced dead code
          (or the sibling plan-handoff.json/breakdown-handoff.json carried
          none) — this is the legitimate "nothing to confirm" case, NOT an
          error.
      source_root : str
          Absolute path to the source tree.  Each row's ``file`` is resolved
          against this when relative.

      Returns
      -------
      dict with:
        "status"          : str  — "vacuous" | "clean" | "violation"
        "violation"       : bool — True only when status == "violation"
                             (mirrors the ``run_regression_gate`` result shape
                             so ``_verdict.py`` can fold it the same way)
        "rows"            : list[dict] — one dict per input row:
              "file"         : str — as given in the row
              "anchor_token" : str — as given in the row
              "kind"         : str — as given in the row
              "why_dead"     : str — as given in the row
              "status"       : str — "pass" | "violation"
              "note"         : str — human-readable per-row explanation
        "pass_count"      : int
        "violation_count" : int
        "total_count"     : int
        "note"            : str — overall human-readable summary

Guard-and-leave semantics
--------------------------
Per row:
  - The declared file EXISTS and still contains ``anchor_token`` as a literal
    substring → "violation" (the guard-and-leave failure — the dominating
    change shipped but the now-unreachable arm/branch/import was left in
    place).
  - The declared file is ABSENT → "pass" (deleting the whole file is a
    legitimate way to remove the dead code).
  - The declared file EXISTS and no longer contains ``anchor_token`` → "pass"
    (removal confirmed).
  - The declared file exists but cannot be read (permission error, race) →
    "pass", noted — this check prefers false negatives (a violation slips
    through) over false positives (a legitimate removal is blocked because
    the file briefly couldn't be read), matching the posture documented in
    ``_hygiene.py``.
  - A row with an empty ``file`` or an empty ``anchor_token`` → "pass",
    noted.  An empty ``anchor_token`` would trivially match every file
    (``"" in text`` is always True in Python), so this guard exists to keep
    a malformed row from masquerading as a violation — schema-validated
    producers (``breakdown_helper finalize-handoff``) never emit an empty
    ``anchor_token``, but this module reads a JSON file crossing a trust
    boundary and does not assume its shape.

Honest bound (plan 71 D4)
--------------------------
This check confirms REMOVAL of the DECLARED kill-list only — it does not,
and structurally cannot, discover deadness the architect never declared at
``/plan``.  A feature with change-induced dead code the plan missed will
pass this check cleanly; that gap is covered only by the advisory backstops
(plan 71 D5), never by this mechanical gate.  Every caller-facing string in
this module states that bound rather than implying full reachability
analysis.

A second, narrower bound (OQ-1): the presence check is a LITERAL SUBSTRING
match anywhere in the file, not a line-scoped or CBM-symbol-scoped anchor.
It does not distinguish a genuine leftover dead arm/branch/import from the
same token incidentally re-occurring elsewhere — in a comment, a quoted
string, an unrelated symbol name, or a second legitimate use.  A
"violation" result means "the literal string ``anchor_token`` is still
present somewhere in the file" — it is not, by itself, guaranteed proof of
guard-and-leave.  A line-scoped or CBM-symbol-scoped anchor variant is
deferred (OQ-1); until then, a human reviews a flagged violation rather
than treating it as an automatically-confirmed defect.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Per-row check
# ---------------------------------------------------------------------------


def _resolve_path(file_path, source_root):
    # type: (str, str) -> str
    """Resolve file_path against source_root when relative."""
    if os.path.isabs(file_path):
        return file_path
    return os.path.join(source_root, file_path)


def _check_row(row, source_root):
    # type: (Dict, str) -> Dict
    """Check a single DeadCodeRow dict against the post-change source tree.

    Never raises — any read error degrades to "pass" (see module docstring's
    Guard-and-leave semantics for the false-negative-over-false-positive
    rationale).
    """
    file_rel = (row.get("file") or "").strip()
    anchor_token = row.get("anchor_token") or ""
    kind = row.get("kind") or ""
    why_dead = row.get("why_dead") or ""

    out = {
        "file": file_rel,
        "anchor_token": anchor_token,
        "kind": kind,
        "why_dead": why_dead,
    }  # type: Dict

    if not file_rel:
        out["status"] = "pass"
        out["note"] = "row has no file path — nothing to check"
        return out

    if not anchor_token:
        # An empty anchor_token would trivially match ("" in text is always
        # True) — never let a malformed row masquerade as a violation.
        out["status"] = "pass"
        out["note"] = "row has no anchor_token — nothing to check"
        return out

    full_path = _resolve_path(file_rel, source_root)

    if not os.path.isfile(full_path):
        out["status"] = "pass"
        out["note"] = "file absent — legitimate removal (whole file deleted)"
        return out

    try:
        with open(full_path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError as exc:
        out["status"] = "pass"
        out["note"] = (
            "file unreadable ({0}) — cannot confirm; not gated".format(exc)
        )
        return out

    if anchor_token in content:
        out["status"] = "violation"
        out["note"] = (
            "anchor_token substring still present — verify it is a genuine "
            "leftover, not an incidental match"
        )
    else:
        out["status"] = "pass"
        out["note"] = "anchor_token absent — removal confirmed"

    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_dead_code_removal(dead_code_rows, source_root):
    # type: (Optional[List[Dict]], str) -> Dict
    """Confirm every declared DeadCodeRow's anchor_token is gone.  See module docstring."""
    source_root = source_root or os.getcwd()

    if not dead_code_rows:
        return {
            "status": "vacuous",
            "violation": False,
            "rows": [],
            "pass_count": 0,
            "violation_count": 0,
            "total_count": 0,
            "note": (
                "no declared dead-code rows — nothing to confirm; undeclared "
                "deadness is not checked (honest bound — plan 71 D4)."
            ),
        }

    rows_out = [_check_row(row, source_root) for row in dead_code_rows]
    violation_count = sum(1 for r in rows_out if r["status"] == "violation")
    total_count = len(rows_out)
    pass_count = total_count - violation_count

    if violation_count:
        status = "violation"
        note = (
            "{0} of {1} declared dead-code row(s) still present "
            "(guard-and-leave) — undeclared deadness is not checked "
            "(honest bound — plan 71 D4).".format(violation_count, total_count)
        )
    else:
        status = "clean"
        note = (
            "all {0} declared dead-code row(s) confirmed removed — "
            "undeclared deadness is not checked (honest bound — "
            "plan 71 D4).".format(total_count)
        )

    return {
        "status": status,
        "violation": violation_count > 0,
        "rows": rows_out,
        "pass_count": pass_count,
        "violation_count": violation_count,
        "total_count": total_count,
        "note": note,
    }
