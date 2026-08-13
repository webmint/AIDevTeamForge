"""Evidence-lanes capture command handler for research_helper (plan 73 D7).

One setter: set-evidence-lanes. Records a self-declared 4-boolean snapshot
of which evidence lanes this investigation consulted -- static graph (CBM)
/ text search / runtime probe / history (git archaeology) -- into
research-report.json (report.evidence_lanes) for finalize-handoff to emit
into handoff_schema.EvidenceLanes.

Mirrors cmd_set_probe_feasibility's shape (all-required-boolean-flags,
canonical lowercase "true"/"false" via _validate_enum) rather than
record-literal-archaeology's shape: evidence_lanes is a single per-run
STATE snapshot overwritten wholesale on each call, not an append-only row
list, so it takes the "set-*" verb family, not "record-*".

Gate on the declaration EXISTING, never on any lane's VALUE (D7): this
setter's field defaults are None (unset) -- see default_report_state() in
_state.py -- so finalize-handoff can tell "the setter was never called"
apart from "the setter was called and every lane was declared false"
(_cmds_handoff.py's evidence_lanes completeness guard, mirroring
set-probe-feasibility's "missing flags" guard). That guard asks ONLY
whether this setter was called at least once -- it never inspects which
lane values were recorded, so it is a call-happened check, not a
per-lane-value check (Phase 3's Verify criterion "no per-lane gate exists
anywhere in the diff" still holds). handoff_schema.EvidenceLanes itself
stays non-Optional bools (unchanged) -- _handoff_build.py's
_build_evidence_lanes() does `bool(rec.get(...))`, which coerces a None
report-state value to False for the persisted schema object; only the
report-state layer needed the tri-state.
"""

from __future__ import annotations

import argparse
import sys

from ._state import _state_transaction
from ._validators import _die, _validate_enum

# Report-state field name -> CLI flag field name (both snake_case; kept as
# an ordered tuple so the parse loop and the CLI registration in _cli.py
# iterate identically).
EVIDENCE_LANE_FIELDS = ("static_graph", "text_search", "runtime_probe", "history")


def cmd_set_evidence_lanes(args: argparse.Namespace) -> int:
    """Write evidence_lanes flags (4 booleans) to research-report.json.

    All four flags are required. Each accepts only lowercase "true" or
    "false" (argparse exact-match) -- same idiom as set-probe-feasibility.
    Last-call-wins per field on re-call.
    """
    devforge_dir = args.devforge_dir
    flag_names = [
        ("static_graph", args.static_graph),
        ("text_search", args.text_search),
        ("runtime_probe", args.runtime_probe),
        ("history", args.history),
    ]
    parsed = {}
    for field_name, raw in flag_names:
        try:
            canonical = _validate_enum(raw, "set-evidence-lanes --{0}".format(
                field_name.replace("_", "-")
            ), ("true", "false"))
        except ValueError as err:
            return _die(str(err), code=2)
        parsed[field_name] = (canonical == "true")

    with _state_transaction(devforge_dir, "report") as report:
        lanes = report.get("evidence_lanes")
        if not isinstance(lanes, dict):
            lanes = {name: None for name in EVIDENCE_LANE_FIELDS}
        for field_name, value in parsed.items():
            lanes[field_name] = value
        report["evidence_lanes"] = lanes

    sys.stdout.write("evidence_lanes written: {0}\n".format(parsed))
    return 0
