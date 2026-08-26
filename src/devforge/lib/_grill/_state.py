"""Session state for grill_helper.

Owns the GrillState schema, path helper, and atomic read/write.

/grill is a per-feature command. State is stored alongside the feature's
other artifacts at:

    <feature_dir>/grill-state.json

where <feature_dir> is the path to the feature directory passed by the
orchestrator (e.g. specs/001-auth/).  This follows the precedent set by
`_review/_state.py`, which scopes state to the per-entity directory
rather than a global singleton like `_audit`'s `audits/.state.json`.

The grill flow is: scope -> attack -> validate -> refute -> classify ->
report.  The phase field is updated by each verb to record which phase
the run is currently in.

Precedent followed: `_review/_state.py` (per-entity scoped state) —
state path rooted in the per-feature dir, not a global `audits/` dir.

Name collision warning -- `status` vs `adversary_status`
----------------------------------------------------------
`GrillState.status` is the SESSION lifecycle field: "in_progress" ->
"complete". `GrillState.adversary_status` (added below) is a DIFFERENT,
unrelated thing: the adversary dispatch OUTCOME, one of
`_shared._consume`'s four literal values ("complete", "clean", "failed",
"missing"). Both fields can independently hold the string "complete" at
the same time and mean two different things. Do not merge them, do not
read one to infer the other, and do not rename either field to something
a future reader could conflate with the other.
"""

import dataclasses
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional


_STATE_FILENAME = "grill-state.json"

# Recognised phase labels for documentation; not enforced at write-time
# so future phases can be added without a schema migration.
GRILL_PHASES = ("scope", "attack", "validate", "refute", "classify", "report")

# The two adversary_status values that count as "the adversary ran" per
# adversary_ran() below. adversary_status may also hold "failed" or
# "missing" (mirroring _shared._consume's STATUS_FAILED / STATUS_MISSING)
# but those need no named constant here: adversary_ran() treats anything
# outside this tuple -- including "failed", "missing", the unset "", and
# any unrecognised value -- as "did not run", so there is nothing else for
# a symbol to name. Not imported from _shared._consume -- see
# adversary_ran()'s docstring for why this module keeps its own copy of
# these two literals rather than depending on _shared at import time.
_ADVERSARY_RAN_STATUSES = ("complete", "clean")


@dataclass
class GrillState:
    """Per-feature grill session state stored at <feature_dir>/grill-state.json.

    Fields are populated by successive verb invocations across phases.
    Defaults represent the empty/unset sentinel for each field type.
    """

    phase: str = ""              # grill phase label (e.g. "scope", "attack", "1".."6")
    feature_dir: str = ""        # path to feature directory (e.g. specs/001-auth/)
    status: str = "in_progress"  # SESSION lifecycle: in_progress -> complete.
                                  # NOT the adversary outcome -- see adversary_status.
    out_path: str = ""           # target path for the grill report (specs/.../grill.md)
    scope_files: List[str] = field(default_factory=list)
    agent_assignments: List[str] = field(default_factory=list)
    adversary_status: str = ""   # ADVERSARY DISPATCH OUTCOME, one of "complete" / "clean" /
                                  # "failed" / "missing" (mirrors _shared._consume's STATUS_*
                                  # constants). Default "" is the unset sentinel and MUST be
                                  # treated as "the adversary has not run" -- never default
                                  # this to a satisfying value. Unrelated to `status` above
                                  # despite sharing the literal "complete"; see the module
                                  # docstring's name-collision warning. Read via
                                  # adversary_ran(), never by comparing this field directly
                                  # against a literal in caller code.
    plan_sha256: str = ""        # sha256 hex digest (over plan.md's raw bytes) of the
                                  # plan.md this grill run actually saw. Recorded so a
                                  # reader can tell a report about the CURRENT plan from one
                                  # about a superseded plan -- see compute_plan_sha256()
                                  # below. This value is RECORDED ONLY: nothing in this
                                  # module (or elsewhere in this phase) compares it against
                                  # a fresh re-hash. Default "" is the unset sentinel.


def state_path(feature_dir: str) -> str:
    """Return the absolute path to the grill state JSON file.

    Path: <feature_dir>/grill-state.json

    feature_dir may be relative or absolute; result is always absolute
    (via os.path.abspath) so callers can rely on it without knowing cwd.
    """
    abs_dir = os.path.abspath(feature_dir)
    return os.path.join(abs_dir, _STATE_FILENAME)


def read_state(path: str) -> Optional[GrillState]:
    """Read GrillState from a JSON file at path.

    Returns None on OSError (file absent, permission denied),
    json.JSONDecodeError (corrupt content), or valid JSON whose top-level
    value is not a JSON object (e.g. an array or a bare scalar) -- that
    last case round-trips through json.load() successfully but has no
    .items() to filter, so it is checked explicitly rather than left to
    raise AttributeError. Tolerates unknown keys by filtering to known
    dataclass field names before construction.
    """
    known = {f.name for f in dataclasses.fields(GrillState)}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    filtered = {k: v for k, v in raw.items() if k in known}
    return GrillState(**filtered)


def write_state(path: str, state: GrillState) -> None:
    """Atomically write state as JSON to path.

    Creates the parent directory if needed. Uses mkstemp + os.replace for
    atomicity; unlinks the temp file on failure before re-raising.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="grill-state-",
        suffix=".json.tmp",
        dir=os.path.dirname(path),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(dataclasses.asdict(state), fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def flip_phase(
    path: str, to_phase: str, to_status: Optional[str] = None
) -> GrillState:
    """Read current state (or start fresh), set phase + optional status, write back.

    Raises ValueError if to_phase is empty or whitespace.
    Returns the updated GrillState.
    """
    if not to_phase or not to_phase.strip():
        raise ValueError("to_phase must be non-empty")
    state = read_state(path)
    if state is None:
        state = GrillState()
    state.phase = to_phase
    if to_status is not None:
        state.status = to_status
    write_state(path, state)
    return state


def adversary_ran(state: GrillState) -> bool:
    """True iff the adversary dispatch actually produced a result.

    Reads state.adversary_status -- NOT state.status, which is the
    unrelated session-lifecycle field; see this module's docstring
    name-collision warning.

    True for "complete" AND for "clean" as two independently-true cases:
    "clean" means the adversary ran and grounded no attack, which is a
    successful pass, not a failure, so it counts as "ran" exactly as much
    as "complete" (a run that grounded one or more findings) does. False
    for "failed", for "missing", and for the unset sentinel "" -- a
    grill-state.json written before this field existed round-trips through
    read_state() with adversary_status == "" (read_state filters to known
    dataclass fields, and GrillState's own default for an absent field is
    the empty-string sentinel), so an old state file correctly reads as
    "the adversary has not run" rather than crashing or silently defaulting
    to satisfied.

    These two literals are kept as this module's own copy (see the
    module-level _ADVERSARY_RAN_STATUSES constant) rather than imported
    from _shared._consume, so that a bare `import _grill._state` -- with
    no _shared package on sys.path -- still works; _cli.py's callers
    already add _shared's parent directory to sys.path before importing
    anything that touches _shared, but this module has no such bootstrap
    of its own and should not need one just to answer this question.
    """
    return state.adversary_status in _ADVERSARY_RAN_STATUSES


def compute_plan_sha256(plan_path: str) -> str:
    """Return the sha256 hex digest of plan_path's raw bytes.

    Modeled on plan 82's shipped `spec_sha256` convention
    (`_spec_check/_cli.py`'s render-report handler): open the file in
    binary mode, hash the raw bytes, return hexdigest(). Same predicate,
    different artifact (plan.md here, spec.md there).

    This value is RECORDED ONLY -- see GrillState.plan_sha256's field
    comment. This function computes the hash; it does not compare it to
    anything. Per D4, the ruling is settled, not deferred: this hash is
    recorded and never enforced, no comparison helper exists in this
    package by design, and the /devforge:breakdown gate that reads
    GrillState does not read freshness at all (it reads adversary_status
    only -- see adversary_ran()).

    Propagates OSError on a missing/unreadable file; this is a pure
    library function, so translating that into a user-facing message is
    the caller's (e.g. the CLI layer's) job, matching this package's other
    library functions (e.g. write_state, write_grill_report).
    """
    with open(plan_path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()
