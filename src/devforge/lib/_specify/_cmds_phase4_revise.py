"""cmd_revise_ac: in-place revision of one already-recorded Acceptance
Criterion (102-SPECIFY-IN-PLACE-REVISION-PLAN.md D2).

A new sibling module rather than a new function beside cmd_add_ac in
_cmds_phase4_setters.py: that module is already 695 lines -- past the
600-line automatic-HIGH module-split threshold -- and this verb needs
none of its private helpers (_next_ac_id, _flip_findings, the
finding-ref trio). It only needs the validators, state I/O and schema
constants _cmds_phase4_setters.py itself merely IMPORTS from
._validators / ._state / ._schema, which a sibling module shares
equally (plan 102's Phase 0 close record, Question 2).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from ._schema import (
    AC_UBIQUITOUS_ONLY_SUBSECTIONS,
    EARS_REGEX,
    EARS_VARIANT_ENUM,
)
from ._state import _load_state, _state_transaction
from ._validators import _die, _validate_enum, _validate_scalar


def cmd_revise_ac(args: argparse.Namespace) -> int:
    """Revise ONLY the fields passed on the AC entry addressed by --ac-id.

    Every field flag (--statement / --ears-variant / --verification-command
    / --test-anchor) defaults to None at the CLI, so "passed" is
    distinguishable from "not passed" -- an explicit empty string IS a
    pass. --verification-command / --test-anchor accept an empty string
    to CLEAR that field; --statement and --ears-variant reject an empty
    value, via the same validators add-ac uses for each.

    The entry keeps its list position and its ac_id -- render order (F12)
    and every landed finding's landed_ref stay valid (F10), because this
    verb never touches state["findings"] (OQ-2) and never touches
    --subsection (OQ-1). It never adds a key: the entry's key set stays
    exactly the seven AcceptanceCriterion fields (F16, Trap 12) -- an
    extra key would make finalize-handoff's AcceptanceCriterion(**ac)
    raise TypeError.

    Re-validates the RESULTING entry exactly as add-ac validates a new
    one, with the same error shapes prefixed "revise-ac:" instead of
    "add-ac:": the AC_UBIQUITOUS_ONLY_SUBSECTIONS rule (against the
    entry's unchanged subsection) and EARS_REGEX[resulting_variant]
    against the resulting statement -- so a bare --ears-variant change
    re-validates the KEPT statement, and a bare --verification-command ""
    clears the field before the ubiquitous-only rule is checked against
    the result.

    All of this runs on a read-only load, before the write transaction
    opens -- the same "no partial write is structurally possible" rule
    _cmds_phase4_setters.py already states for its own pre-validated
    setters. The transaction body then assigns only the fields that were
    actually passed, looping over the list and matching by ac_id the same
    shape _flip_findings already uses to mutate a matched entry in place.

    Not in the plan's text (102-SPECIFY-IN-PLACE-REVISION-PLAN.md D2):
    more than one entry sharing --ac-id is reachable only on a state
    written before D4's add-ac duplicate rejection, or a hand-edited
    state file. Rather than revise an arbitrary one of them, this exits 2
    naming the ac_id and the match count -- an orchestrator build
    decision the plan's own text does not make. The same class of
    hand-edited-or-corrupted state can also leave an entry's
    ears_variant outside EARS_REGEX; rather than let the subsequent
    EARS_REGEX[new_ears_variant] lookup raise KeyError (surfacing as a
    traceback and exit 1, not this verb's exit-2 contract), an unknown
    resulting variant exits 2 via _die before the EARS match runs --
    mirroring cmd_verify_ac_shape's own `if variant not in EARS_REGEX`
    guard (_cmds_phase4_verify.py). A valid --ears-variant passed in the
    same call still repairs the entry: that path is validated by
    _validate_enum first, so the guard only fires when no valid variant
    results. python-reviewer finding (HIGH), reproduced live.
    """
    statement_passed = args.statement is not None
    ears_variant_passed = args.ears_variant is not None
    verification_command_passed = args.verification_command is not None
    test_anchor_passed = args.test_anchor is not None
    if not (
        statement_passed or ears_variant_passed
        or verification_command_passed or test_anchor_passed
    ):
        return _die(
            "revise-ac: at least one of --statement / --ears-variant / "
            "--verification-command / --test-anchor is required",
            code=2,
        )

    ac_id = (args.ac_id or "").strip()
    if not ac_id:
        return _die("revise-ac: --ac-id is required and non-empty", code=2)

    try:
        ro_state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("revise-ac: {0}".format(err))

    matches: List[Dict[str, Any]] = [
        a for a in ro_state.get("acceptance_criteria", [])
        if a.get("ac_id") == ac_id
    ]
    if not matches:
        return _die(
            "revise-ac: no acceptance criterion with ac_id {0!r}".format(
                ac_id,
            ),
            code=2,
        )
    if len(matches) > 1:
        return _die(
            "revise-ac: {0} entries share ac_id {1!r} -- refusing to "
            "revise an arbitrary one (state written before duplicate "
            "rejection, or hand-edited)".format(len(matches), ac_id),
            code=2,
        )
    existing = matches[0]

    new_statement = existing.get("statement", "")
    if statement_passed:
        try:
            new_statement = _validate_scalar(args.statement, "statement")
        except ValueError as err:
            return _die("revise-ac: {0}".format(err), code=2)

    new_ears_variant = existing.get("ears_variant", "")
    if ears_variant_passed:
        try:
            new_ears_variant = _validate_enum(
                args.ears_variant, "ears_variant", EARS_VARIANT_ENUM,
            )
        except ValueError as err:
            return _die("revise-ac: {0}".format(err), code=2)

    new_verification_command = existing.get("verification_command", "")
    if verification_command_passed:
        new_verification_command = args.verification_command.strip()

    new_test_anchor = existing.get("test_anchor", "")
    if test_anchor_passed:
        new_test_anchor = args.test_anchor.strip()

    subsection = existing.get("subsection", "")
    if subsection in AC_UBIQUITOUS_ONLY_SUBSECTIONS:
        if new_ears_variant != "ubiquitous":
            return _die(
                "revise-ac: subsection {0!r} requires ears_variant "
                "'ubiquitous' (Variance rule #10); got {1!r}".format(
                    subsection, new_ears_variant,
                ),
                code=2,
            )
        if not new_verification_command:
            return _die(
                "revise-ac: subsection {0!r} requires non-empty "
                "--verification-command (Variance rule #10)".format(
                    subsection,
                ),
                code=2,
            )

    if new_ears_variant not in EARS_REGEX:
        return _die(
            "revise-ac: ac_id {0!r} has ears_variant {1!r}, which is not "
            "a known EARS variant -- state is hand-edited or corrupted; "
            "pass --ears-variant to repair it".format(
                ac_id, new_ears_variant,
            ),
            code=2,
        )

    if not EARS_REGEX[new_ears_variant].match(new_statement):
        return _die(
            "revise-ac: statement does not match EARS regex for variant "
            "{0!r}: {1!r}".format(new_ears_variant, new_statement),
            code=2,
        )

    try:
        with _state_transaction(args.devforge_dir) as state:
            for a in state["acceptance_criteria"]:
                if a.get("ac_id") != ac_id:
                    continue
                if statement_passed:
                    a["statement"] = new_statement
                if ears_variant_passed:
                    a["ears_variant"] = new_ears_variant
                if verification_command_passed:
                    a["verification_command"] = new_verification_command
                if test_anchor_passed:
                    a["test_anchor"] = new_test_anchor
                break
    except (OSError, json.JSONDecodeError) as err:
        return _die("revise-ac: {0}".format(err))
    sys.stdout.write(ac_id + "\n")
    return 0
