"""_partition -- pure predicate over a /devforge:grill apply-verdicts partition.

A grill partition (the JSON object produced by `_shared._verify.apply_verdicts`
and rendered by `_report.render_report`) has four buckets: confirmed,
dismissed, uncertain, contested. This module owns the single question
grill's own PHASE 7 disposition step needs answered from that shape: did
this run come out CLEAN, i.e. does a human need to look at any individual
finding before a disposition is picked?

This predicate is NOT read by the /devforge:breakdown entry gate. Per plan
85's ratified D1, that gate reads `GrillState.adversary_status` (via
`_state.adversary_ran()`) only -- presence + freshness of a run, never its
verdict. Wiring this module's cleanliness result into that gate would be a
misreading of both decisions; do not do it.

This module does not read or write any file; it is a pure function over an
already-parsed dict. It has no dependency on `_state.py` (a partition is
not GrillState) and no dependency on `_shared/` (the caller reads
partition.json / passes the apply-verdicts return value directly).

Stdlib only. Python 3.8+.
"""

from typing import Dict, List, Optional


# All four buckets `_shared._verify.apply_verdicts` always writes. Their
# presence is checked before anything else -- see partition_is_clean()'s
# fail-closed paragraph.
_REQUIRED_BUCKETS = ("confirmed", "dismissed", "uncertain", "contested")

# Buckets whose non-empty CONTENT means a human must be consulted.
# `dismissed` is deliberately absent from this tuple -- see
# partition_is_clean()'s docstring. (Its KEY, however, is still required --
# see _REQUIRED_BUCKETS above.)
_BLOCKING_BUCKETS = ("confirmed", "contested", "uncertain")


def partition_is_clean(partition: Dict[str, Optional[List[dict]]]) -> bool:
    """CLEAN iff confirmed == [] AND contested == [] AND uncertain == [].

    `dismissed` may be non-empty and MUST NOT affect the result: a
    dismissed finding is precisely one that did not survive refutation, so
    its presence says nothing about whether a human needs to review
    anything. This is the case most likely to be broken by a later
    "simplification" that reads an all-buckets-empty partition as the only
    clean shape -- it is not; a partition with only `dismissed` populated
    is equally clean.

    Fail-closed on a malformed shape: a partition dict missing ANY of the
    four required bucket KEYS (confirmed, dismissed, uncertain, contested)
    returns False -- never True, and never raises. The real producer
    (`_shared._verify.apply_verdicts`) always writes all four keys, so this
    branch only ever fires on already-anomalous input; treating that input
    as "not clean" routes it to a human rather than silently auto-accepting
    it (an unhandled crash mid-PHASE-7 would be worse than that -- the
    caller branches on a bool, so a bool is what this returns). This is a
    deliberate reversal of an earlier draft that tolerated a missing key as
    an empty list; that tolerance bought nothing in the happy path and only
    mattered on anomalous input, exactly where fail-closed is wanted.

    This decides whether a human is consulted at the /devforge:grill
    disposition gate (PHASE 7 -- NOT the /devforge:breakdown entry gate;
    see this module's docstring), so the predicate is exposed here rather
    than being re-derived in prose by the orchestrator or by a future
    gate's own ad-hoc bucket check.
    """
    for bucket in _REQUIRED_BUCKETS:
        if bucket not in partition:
            return False
    for bucket in _BLOCKING_BUCKETS:
        if partition.get(bucket):
            return False
    return True
