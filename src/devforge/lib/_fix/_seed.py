"""build_seed / write_seed -- /devforge:fix scope-change backward re-entry seed.

Mirrors _spec_check/_seed.py exactly, which is itself a narrowing of
_grill/_report.py's build_seed + write_seed (plan 83 D5). /devforge:fix's
PHASE-1 bounce is a flat binary -- when a fix in flight turns out to need an
architectural/behavior change rather than a mechanical repair, the recommended
next step is always /devforge:specify -- so source and target_stage are NOT
parameters here; they are always "fix" and "spec" respectively (plan 83 D2:
no "breakdown" target stage ships in this build; D6: target_stage alone
carries the routing decision, no separate scope_grade field).

Semantic mapping for a /devforge:fix scope-change seed (plan 83 OQ-4):
  prior_conclusion       the named working-list item's original diagnosis
                          (what /devforge:fix was asked to remediate as a
                          mechanical repair)
  invalidating_evidence  when the item carries a written finding
                          (specs/[feature]/review.md or verification.md),
                          the finding's own "evidence" string plus the
                          one-line scope-change classification reason; for
                          the case-3 conversational defect (no written
                          finding on disk) the bare classification judgment
                          alone, since there is no finding to quote
  must_satisfy            what the re-run must additionally resolve (the
                          recommended cycle from triage.md)
  provenance               pointer to the source report, OR, for a case-3
                          conversational defect that has no report file,
                          the literal string "conversational (in-window
                          user report; no report file)" (plan 83 OQ-4)

Multi-item bounce (plan 83 OQ-4, third sub-case): when two or more working-list
items each independently trigger a scope-change bounce in the same /devforge:fix
run, D4's fixed one-file-per-source-per-directory naming (fix-seed.json) forces
option (i) -- ONE seed whose three flat strings (prior_conclusion,
invalidating_evidence, must_satisfy) synthesize across all the items, with each
item's own reasoning carried separately in carried_findings. This module does
NOT enforce that synthesis -- it is the caller's (the command layer's)
contract to compose the flat strings and populate carried_findings before
calling build_seed; build_seed and write_seed accept whatever strings and list
they are given and validate only the schema-level shape.

The command layer (a later phase, plan 83 Phase 3) supplies those strings;
build_seed only assembles + validates via ReEntrySeed.__post_init__.

IMPORTANT -- verdict-gating is NOT done here. Per plan 83 D3 (mirroring D5 /
plan 39's precedent), a seed is written ONLY on the PHASE-1 AskUserQuestion
arm that matches the bounce's own recommendation; that gating decision lives
in the /devforge:fix command layer, not in this module -- the gate itself is
built into fix/main.md at plan 83 Phase 3. write_seed
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
    """Construct a ReEntrySeed for the /devforge:fix scope-change backward handoff.

    source is always "fix"; target_stage is always "spec" -- the only backward
    direction /devforge:fix has in this build (plan 83 D2). Delegates all
    field validation to ReEntrySeed.__post_init__ -- surfaces a clear
    ValueError on invalid input.

    Parameters
    ----------
    feature : str
        Feature slug / id (non-empty).
    prior_conclusion : str
        The named working-list item's original diagnosis, now proven to be a
        scope change rather than a mechanical repair (non-empty). For a
        multi-item bounce (plan 83 OQ-4), synthesizes across all items.
    invalidating_evidence : str
        The quoted finding evidence plus the one-line scope-change
        classification reason (or, for a case-3 conversational defect, the
        bare classification judgment alone) (non-empty).
    must_satisfy : str
        What the re-run must additionally resolve (non-empty).
    provenance : str
        Pointer to the source report (specs/[feature]/review.md or
        verification.md), or the literal
        "conversational (in-window user report; no report file)" for a
        case-3 conversational defect with no report file (non-empty).
    cycle_count : int
        Bounded-compounding-loop counter; strict int (no bool), >= 1.
        Defaults to 1.
    carried_findings : list[str] or None
        Prior findings carried forward (monotonic compounding); for a
        multi-item bounce this carries each item's own reasoning. May be
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
        source="fix",
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
    """Atomic write of a ReEntrySeed as JSON to <feature_dir>/fix-seed.json.

    Serializes via dataclasses.asdict + json.dumps (stdlib only).
    Uses mkstemp + os.replace for crash safety.
    Creates feature_dir if it does not exist.
    Returns the path written.

    NOTE: this function does NOT gate on the user's PHASE-1 pick -- it writes
    whatever seed it is given, unconditionally. The decision of WHETHER to
    call write_seed (only on the arm matching the bounce's own recommendation,
    per plan 83 D3) lives in the /devforge:fix command, not here.

    On failure, unlinks the temp file and re-raises.
    """
    os.makedirs(feature_dir, exist_ok=True)
    out_path = os.path.join(feature_dir, "fix-seed.json")

    payload = json.dumps(dataclasses.asdict(seed), indent=2, ensure_ascii=False)

    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-fix-seed-",
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
