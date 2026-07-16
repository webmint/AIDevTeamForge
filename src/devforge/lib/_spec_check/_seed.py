"""build_seed / write_seed -- /spec-check REVISE-SPEC backward re-entry seed.

Mirrors _grill/_report.py's build_seed + write_seed exactly, narrowed to
/spec-check's single fixed direction: /spec-check's only backward re-entry
target is the spec it just proved unsatisfiable, one hop back (per D3/D5)
-- there is no upstream-of-spec re-entry and no same-command revision loop
the way /grill has REVISE-PLAN vs RE-ENTER-UPSTREAM. So source and
target_stage are NOT parameters here; they are always "spec-check" and
"spec" respectively.

Semantic mapping for a /spec-check REVISE-SPEC seed:
  prior_conclusion       the spec's now-invalidated claim (the conflicting
                          AC set as originally authored)
  invalidating_evidence  the proven contradiction (the unsat-core ac_ids
                          plus the logic reading that derives it)
  must_satisfy            what the revised spec must resolve (e.g. "resolve
                          the conflict between <the named ACs>")
  provenance               pointer to specs/<feature>/spec-check.md

The command layer (a later phase) supplies those strings; build_seed only
assembles + validates via ReEntrySeed.__post_init__.

IMPORTANT -- verdict-gating is NOT done here. Per D5 / plan 39's precedent,
a seed is written ONLY when the user's human-gate pick is REVISE-SPEC; that
gating decision lives in the Phase-7 command, not in this module. write_seed
unconditionally writes whatever ReEntrySeed it is given.

Stdlib only. Python 3.8+. No I/O except write_seed.
"""

import dataclasses
import json
import os
import tempfile
from typing import List, Optional

from _shared.seed_schema import ReEntrySeed, SEED_SCHEMA_VERSION  # noqa: E402


# ---------------------------------------------------------------------------
# build_seed
# ---------------------------------------------------------------------------


def build_seed(
    feature,
    prior_conclusion,
    invalidating_evidence,
    must_satisfy,
    provenance,
    cycle_count=1,
    carried_findings=None,
):
    # type: (str, str, str, str, str, int, Optional[List[str]]) -> ReEntrySeed
    """Construct a ReEntrySeed for the /spec-check REVISE-SPEC backward handoff.

    source is always "spec-check"; target_stage is always "spec" -- the only
    backward direction /spec-check has. Delegates all field validation to
    ReEntrySeed.__post_init__ -- surfaces a clear ValueError on invalid input.

    Parameters
    ----------
    feature : str
        Feature slug / id (non-empty).
    prior_conclusion : str
        The spec's now-invalidated claim (non-empty).
    invalidating_evidence : str
        The proven contradiction -- unsat-core ac_ids plus the logic reading
        (non-empty).
    must_satisfy : str
        What the revised spec must resolve (non-empty).
    provenance : str
        Pointer to specs/<feature>/spec-check.md (non-empty).
    cycle_count : int
        Bounded-compounding-loop counter; strict int (no bool), >= 1.
        Defaults to 1.
    carried_findings : list[str] or None
        Prior findings carried forward (monotonic compounding); may be
        empty or None (treated as []).

    Returns
    -------
    ReEntrySeed  fully validated seed ready for serialization.

    Raises
    ------
    ValueError  if any field fails ReEntrySeed.__post_init__ validation.
    """
    return ReEntrySeed(
        seed_version=SEED_SCHEMA_VERSION,
        source="spec-check",
        target_stage="spec",
        feature=feature,
        prior_conclusion=prior_conclusion,
        invalidating_evidence=invalidating_evidence,
        must_satisfy=must_satisfy,
        cycle_count=cycle_count,
        carried_findings=(carried_findings or []),
        provenance=provenance,
    )


# ---------------------------------------------------------------------------
# write_seed
# ---------------------------------------------------------------------------


def write_seed(feature_dir, seed):
    # type: (str, ReEntrySeed) -> str
    """Atomic write of a ReEntrySeed as JSON to <feature_dir>/spec-check-seed.json.

    Serializes via dataclasses.asdict + json.dumps (stdlib only).
    Uses mkstemp + os.replace for crash safety.
    Creates feature_dir if it does not exist.
    Returns the path written.

    NOTE: this function does NOT gate on the user's verdict pick -- it writes
    whatever seed it is given, unconditionally. The decision of WHETHER to
    call write_seed (only on a REVISE-SPEC human pick) lives in the Phase-7
    command, not here.

    On failure, unlinks the temp file and re-raises.
    """
    os.makedirs(feature_dir, exist_ok=True)
    out_path = os.path.join(feature_dir, "spec-check-seed.json")

    payload = json.dumps(dataclasses.asdict(seed), indent=2, ensure_ascii=False)

    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-spec-check-seed-",
        suffix=".json",
        dir=feature_dir,
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.write("\n")
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return out_path
