"""Phase 2 approach setters: set-approach + set-recommended-approach.

set-recommended-approach carries Patch-4 single-layer-justification +
cites gate AND Patch-9 proposed-call-shape arg-duplication gate.

The single-layer-justification+cites gate's HARD-REQUIRE (rejecting an
unsupplied justification) is bug-mode only per plan 67 D5; 8b-suppression
keeps it from misleading the LLM into a path verify cannot satisfy. Its
STORAGE, however, is mode-independent (plan 69 python-reviewer fix 1,
same ratified principle as check 18's "both sites together"): when
single-layer is detected and the fields ARE supplied, they are always
validated + stored, regardless of mode — otherwise verify check 13
(mode-independent since plan 69 D6/WI-F) can fire in enhancement mode
with no way to satisfy it, because the setter silently dropped the very
fields that would clear it.

The proposed-call-shape arg-duplication gate is fully mode-independent
(plan 69 D6/WI-F — widened together with verify check 18; a mode-gated
setter under a mode-independent verify check would be incoherent).
"""

from __future__ import annotations

import argparse
import json
import sys

from ._constants import COMPLEXITY_ENUM
from ._layer_package import _compute_check_8b_would_fire, _extract_package
from _shared.literal_call_shape import (
    CALL_SHAPE_RE,
    _detect_arg_duplication,
    _detect_literal_replacement,
    _normalize_call_shape,
)
from ._state import _load_memo, _state_transaction
from ._validators import (
    _die,
    _validate_enum,
    _validate_scalar,
    _validate_string_array_json,
    _validate_verbatim,
)


def cmd_set_approach(args: argparse.Namespace) -> int:
    """Append an Approach record."""
    try:
        name = _validate_scalar(args.name, "approach.name")
        desc = _validate_verbatim(args.description, "approach.description")
        addresses = _validate_string_array_json(args.addresses, "approach.addresses_hypotheses")
        not_covered = _validate_string_array_json(
            args.does_not_cover, "approach.does_not_cover"
        )
        pros = _validate_string_array_json(args.pros, "approach.pros")
        cons = _validate_string_array_json(args.cons, "approach.cons")
        complexity = _validate_enum(args.complexity, "approach.complexity", COMPLEXITY_ENUM)
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("approaches", []).append(
                {
                    "name": name,
                    "description": desc,
                    "addresses_hypotheses": addresses,
                    "does_not_cover": not_covered,
                    "pros": pros,
                    "cons": cons,
                    "complexity": complexity,
                }
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-approach: {0}".format(err))
    return 0


def cmd_set_recommended_approach(args: argparse.Namespace) -> int:
    """Set recommended approach. Name must match an existing approach.name.

    Validates: name resolves to an existing approach, hypotheses lists are
    JSON arrays of strings, rationale non-empty. Does not run the
    unchanged_behavior cross-check at set time — that runs in `verify`.

    Single-layer gate (Gap 4 — Patch 4): when all fix_path_helpers resolve
    to the same package, --single-layer-justification + non-empty --cites
    are validated and stored when supplied (any mode); the hard-require
    rejecting an unsupplied justification applies in bug mode only (plan 69
    D6/WI-F). Each cite must match a recorded consumer_chain,
    value_semantics, or dead_siblings row token, proving the symptom is
    layer-local.
    """
    try:
        name = _validate_scalar(args.name, "recommended_approach.name")
        rationale = _validate_verbatim(args.rationale, "recommended_approach.rationale")
        addressed = _validate_string_array_json(
            args.hypotheses_addressed, "recommended_approach.hypotheses_addressed"
        )
        not_covered = _validate_string_array_json(
            args.hypotheses_not_covered, "recommended_approach.hypotheses_not_covered"
        )
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            names = {a.get("name") for a in report.get("approaches", [])}
            if name not in names:
                return _die(
                    "set-recommended-approach: name {0!r} does not match an existing approach; "
                    "have {1}".format(name, sorted(names)),
                    code=2,
                )

            recommended_record = {
                "name": name,
                "rationale": rationale,
                "hypotheses_addressed": addressed,
                "hypotheses_not_covered": not_covered,
            }

            # Single-layer detection: when all fix_path_helpers are in the same package,
            # the recommendation is anchored to one layer-stack region. Require an
            # explicit prose justification + cite at least one consumer_chain /
            # value_semantics / dead_siblings row proving the symptom is layer-local.
            # Closes Gap 4 in RESEARCH-FRAMING-REGRESSION-PLAN.
            fix_path_helpers = report.get("fix_path_helpers") or []
            memo_mode = None
            try:
                memo_state = _load_memo(args.devforge_dir)
                memo_mode = memo_state.get("mode")
            except (OSError, json.JSONDecodeError):
                pass
            bug_mode = (report.get("mode") == "bug" or memo_mode == "bug")

            # Detection is mode-independent — enhancement runs CAN populate
            # fix_path_helpers (one of check 8's two satisfying paths, the
            # other being the no-shared-callers justification, since plan 67
            # made check 8 mode-independent) and verify check 13 (mode-
            # independent since plan 69 D6/WI-F) can fire against them too.
            # SUPPRESSION: when check 8b would fire (presentation-layer symptom + all helpers
            # same package), check 13 / this setter gate are structurally unreachable —
            # supplying --single-layer-justification cannot satisfy verify because 8b vetoes
            # unconditionally. Skip the gate entirely; the LLM's only recovery is to add
            # cross-layer helpers, not supply justification.
            if len(fix_path_helpers) >= 1 and not _compute_check_8b_would_fire(report):
                packages = set()
                for h in fix_path_helpers:
                    if isinstance(h, dict) and h.get("file_line"):
                        pkg = _extract_package(h["file_line"].rsplit(":", 1)[0])
                        if pkg:
                            packages.add(pkg)
                single_layer = len(packages) == 1
                if single_layer:
                    justification = getattr(args, "single_layer_justification", None)
                    cites = getattr(args, "cites", None)
                    has_justification = bool(justification and justification.strip())
                    if not has_justification:
                        # HARD-REQUIRE stays bug-mode only (plan 67 D5) — the
                        # layer-locality framing isn't a Gap-4 failure class
                        # for enhancements, so an enhancement run that
                        # supplies nothing is not rejected; it simply stores
                        # nothing here (verify check 13 will name the remedy
                        # if the report needs it to pass).
                        if bug_mode:
                            return _die(
                                "set-recommended-approach: --single-layer-justification is required when all fix_path_helpers "
                                "resolve to the same package ({0!r}). Single-layer recommendations bypass the cross-layer "
                                "trace evidence — supply a justification text explaining why the symptom is layer-local AND "
                                "cite at least one consumer_chain / value_semantics / dead_siblings row via --cites.".format(
                                    next(iter(packages))
                                ),
                                code=2,
                            )
                    else:
                        # justification WAS supplied — validate + store
                        # regardless of mode (plan 69 python-reviewer fix 1:
                        # storage is mode-independent even though the
                        # HARD-REQUIRE above stays bug-mode-only).
                        # Parse cites JSON array
                        try:
                            cites_list = _validate_string_array_json(cites or "[]", "recommended_approach.cites")
                        except ValueError as err:
                            return _die(str(err), code=2)
                        if not cites_list:
                            return _die(
                                "set-recommended-approach: --cites is required (non-empty JSON array) when "
                                "--single-layer-justification is provided. Each cite must match a recorded "
                                "consumer_chain.consumer_qn, value_semantics.value (or value_semantics.evidence), "
                                "or dead_siblings.method_qn from the report state.",
                                code=2,
                            )
                        # Validate each cite resolves to a recorded row
                        consumer_chain = report.get("consumer_chain") or []
                        value_semantics = report.get("value_semantics") or []
                        dead_siblings = report.get("dead_siblings") or []
                        valid_tokens = set()
                        for cc in consumer_chain:
                            if cc.get("consumer_qn"):
                                valid_tokens.add(cc["consumer_qn"])
                        for vs in value_semantics:
                            if vs.get("value"):
                                valid_tokens.add(vs["value"])
                            if vs.get("evidence"):
                                valid_tokens.add(vs["evidence"])
                        for ds in dead_siblings:
                            if ds.get("method_qn"):
                                valid_tokens.add(ds["method_qn"])
                        unresolved = [c for c in cites_list if c not in valid_tokens]
                        if unresolved:
                            return _die(
                                "set-recommended-approach: --cites contains tokens that do not match any recorded "
                                "consumer_chain.consumer_qn, value_semantics.value, value_semantics.evidence, or "
                                "dead_siblings.method_qn: {0!r}. Recorded tokens: {1!r}.".format(
                                    unresolved, sorted(valid_tokens)
                                ),
                                code=2,
                            )
                        # All citation checks pass — store on the recommended_approach record
                        # under new keys so render + verify can surface them.
                        recommended_record["single_layer_justification"] = justification
                        recommended_record["cites"] = cites_list

            # Patch 9 (V3) — proposed-call-shape gate. Required when
            # (single-layer-justification set OR rationale has literal-
            # replacement prose). Helper-side defense against the arg-
            # duplication failure mode (same identifier passed twice in one
            # call signals fix layer is upstream of the call site).
            # Mode-independent (plan 69 D6/WI-F — previously bug-mode only;
            # widened together with verify check 18, its mirror).
            requires_shape = False
            if getattr(args, "single_layer_justification", None):
                requires_shape = True
            # Reuse Patch 8's literal-replacement detector. Scan rationale
            # plus the linked approach.description (same scope as check 17).
            if not requires_shape:
                linked_name = name
                approach_desc = ""
                for ap in report.get("approaches") or []:
                    if ap.get("name") == linked_name:
                        approach_desc = ap.get("description") or ""
                        break
                combined = "{0} {1}".format(rationale, approach_desc)
                if _detect_literal_replacement(combined) is not None:
                    requires_shape = True
            if requires_shape:
                proposed_shape = getattr(args, "proposed_call_shape", None)
                if not proposed_shape or not proposed_shape.strip():
                    return _die(
                        "set-recommended-approach: --proposed-call-shape is required "
                        "when --single-layer-justification is set OR --rationale / "
                        "linked approach description contains literal-replacement "
                        "prose. Supply the exact post-fix call as it would appear "
                        "at the fix site so the helper can check for argument "
                        "duplication.",
                        code=2,
                    )
                dup = _detect_arg_duplication(proposed_shape)
                if dup is not None:
                    ident, count = dup
                    return _die(
                        "set-recommended-approach: --proposed-call-shape {0!r} "
                        "contains argument duplication ({1!r} appears {2} times "
                        "in the arg list). Same value passed multiple times in "
                        "one call indicates the default-source belongs at a "
                        "different layer (wrapper signature / state initialization "
                        "/ use-case default). Reconsider the fix layer and "
                        "re-draft.".format(proposed_shape, ident, count),
                        code=2,
                    )
                # Parser may fail-soft (None); store the shape regardless so
                # render + verify can surface it. Parser-failure = stderr
                # advisory only, no block (per plan §Patch 9 'fragile by
                # design' clause + 'log advisory; do NOT block /research
                # on a parser corner case'). Emit advisory only when the
                # outer CALL_SHAPE_RE fails (distinguishes parser-failure
                # from genuine no-duplication — both return None from
                # _detect_arg_duplication).
                if not CALL_SHAPE_RE.match(_normalize_call_shape(proposed_shape)):
                    sys.stderr.write(
                        "research_helper: set-recommended-approach: "
                        "--proposed-call-shape {0!r} could not be fully "
                        "parsed (nested calls / unsupported syntax); "
                        "argument-duplication check skipped, shape stored "
                        "verbatim.\n".format(proposed_shape)
                    )
                recommended_record["proposed_call_shape"] = proposed_shape

            report["recommended_approach"] = recommended_record
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-recommended-approach: {0}".format(err))
    return 0
