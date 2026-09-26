"""declare-grounded-overlap: the D5 exit-2 declaration route.

Plan 105 (Hypothesis-Suppression Precision Plan) D5 ratified two admissible
exits from verify-hypothesis-suppression's exit 2: record-gap (move the
mechanism into an open question and drop it from the rationale), or an
explicit declaration that the overlap is legitimate, anchored to a recorded
evidence row. This module owns the second exit's setter,
cmd_declare_grounded_overlap, and the grounding-value helper it validates
--grounded-in against. The gate itself (cmd_verify_hypothesis_suppression,
_cmds_render_verify.py) reads report["overlap_declarations"] and treats a
declared token of the matching hypothesis as accepted -- a declaration only
ever subtracts from the overlap; it can never make the gate fire.

_grounded_declaration_values names a WIDER set of rows than the gate's own
_suppression_evidence_tokens (_cmds_render_verify.py) -- deliberately: a
declared token has already survived the gate's subtraction, so it can only
be grounded in a row the subtraction does not itself read (e.g. a recorded
fix_path_helpers[].qn, which the gate's subtraction never tokenizes).
"""

from __future__ import annotations

import argparse
import json

from _shared.text_overlap import tokenize_for_overlap as _tokenize_hypothesis
from ._cmds_render_verify import _SUPPRESSION_MIN_SPECIFIC_TOKEN_LEN
from ._state import _state_transaction
from ._validators import _die, _validate_scalar, _validate_string_array_json


def _grounded_declaration_values(report):
    # type: (dict) -> set
    """Return every non-empty string a declaration's --grounded-in may cite.

    The union of: consumer_chain[].consumer_qn / .value / .file_line;
    value_semantics[].value / .evidence (any classification -- unlike the
    gate's own evidence-token subtraction, which admits only invariant-
    classified .evidence, a declaration may ground against any row that
    genuinely exists); dead_siblings[].method_qn / .class_qn;
    fix_path_helpers[].qn / .file_line; findings[].file_line. Non-dict rows
    are skipped (legacy direct-JSON writes carry no typed row to read a
    value from); a field value that is not itself a string (e.g. a list,
    dict, or int -- direct state mutation could put anything there) is
    also skipped -- --grounded-in is compared by exact string equality
    against this set, so a non-string value could never match it anyway,
    and adding one unguarded would crash comparisons downstream (an int
    is hashable so `values.add(v)` alone would not raise, but a list or
    dict field value would -- guard on the type once here rather than on
    each shape a caller might inject).
    """
    values = set()
    for row in report.get("consumer_chain") or []:
        if not isinstance(row, dict):
            continue
        for key in ("consumer_qn", "value", "file_line"):
            v = row.get(key)
            if isinstance(v, str) and v:
                values.add(v)
    for row in report.get("value_semantics") or []:
        if not isinstance(row, dict):
            continue
        for key in ("value", "evidence"):
            v = row.get(key)
            if isinstance(v, str) and v:
                values.add(v)
    for row in report.get("dead_siblings") or []:
        if not isinstance(row, dict):
            continue
        for key in ("method_qn", "class_qn"):
            v = row.get(key)
            if isinstance(v, str) and v:
                values.add(v)
    for row in report.get("fix_path_helpers") or []:
        if not isinstance(row, dict):
            continue
        for key in ("qn", "file_line"):
            v = row.get(key)
            if isinstance(v, str) and v:
                values.add(v)
    for row in report.get("findings") or []:
        if not isinstance(row, dict):
            continue
        v = row.get("file_line")
        if isinstance(v, str) and v:
            values.add(v)
    return values


def cmd_declare_grounded_overlap(args: argparse.Namespace) -> int:
    """Record a grounded-overlap declaration for one recorded hypothesis.

    Validated, in this order (each failure -> exit 2, nothing written --
    every check below runs before report is mutated, so an early return
    inside the state transaction re-serializes the same, unchanged state):
      1. --tokens decodes as a non-empty JSON array (each entry stripped
         + lowercased).
      2. Every --tokens entry is at least _SUPPRESSION_MIN_SPECIFIC_TOKEN_LEN
         characters (the gate's own specificity floor, imported from
         _cmds_render_verify.py) -- a shorter token can never survive that
         floor, so the gate never fires on it and there is nothing for a
         declaration to accept.
      3. At least one hypothesis has been recorded (record-hypothesis).
      4. --hypothesis matches a recorded hypotheses[].label.
      5. --grounded-in equals a value _grounded_declaration_values returns
         for the current report -- rejection prints the recorded values,
         the --cites shape (_cmds_approach.py's cmd_set_recommended_approach).
      6. Every --tokens entry is a token of
         tokenize_for_overlap(--grounded-in) -- the cited row must actually
         carry the token, or the declaration is not falsifiable.
      7. Every --tokens entry is a token of tokenize_for_overlap(that
         hypothesis's own cause) -- a declaration is about THIS
         hypothesis's own overlap, not a token that happens to also be a
         cause token of some other hypothesis.

    On success, appends {hypothesis, tokens (sorted, deduped, lowercased,
    stripped), grounded_in} to report["overlap_declarations"] -- unless an
    identical record is already present, in which case the call is a
    no-op (still exit 0; idempotent on re-invocation).
    """
    try:
        hypothesis_label = _validate_scalar(
            args.hypothesis, "declare-grounded-overlap.--hypothesis"
        )
        grounded_in = _validate_scalar(
            args.grounded_in, "declare-grounded-overlap.--grounded-in"
        )
        raw_tokens = _validate_string_array_json(
            args.tokens, "declare-grounded-overlap.--tokens"
        )
    except ValueError as err:
        return _die(str(err), code=2)
    if not raw_tokens:
        return _die(
            "declare-grounded-overlap: --tokens must be a non-empty JSON array",
            code=2,
        )
    tokens = sorted({t.strip().lower() for t in raw_tokens})
    too_short = sorted(t for t in tokens if len(t) < _SUPPRESSION_MIN_SPECIFIC_TOKEN_LEN)
    if too_short:
        return _die(
            "declare-grounded-overlap: --tokens {0!r} are shorter than the "
            "gate's specificity floor ({1} characters); the gate never "
            "fires on a token shorter than {1} characters, so there is "
            "nothing to declare".format(too_short, _SUPPRESSION_MIN_SPECIFIC_TOKEN_LEN),
            code=2,
        )

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            hypotheses = report.get("hypotheses") or []
            recorded_labels = [
                h["label"] for h in hypotheses if isinstance(h, dict) and h.get("label")
            ]
            if not recorded_labels:
                return _die(
                    "declare-grounded-overlap: no hypothesis has been recorded; "
                    "call record-hypothesis first",
                    code=2,
                )
            if hypothesis_label not in recorded_labels:
                return _die(
                    "declare-grounded-overlap: --hypothesis {0!r} is not a recorded "
                    "hypothesis label; recorded labels: {1!r}".format(
                        hypothesis_label, recorded_labels
                    ),
                    code=2,
                )

            grounding_values = _grounded_declaration_values(report)
            if grounded_in not in grounding_values:
                return _die(
                    "declare-grounded-overlap: --grounded-in {0!r} does not match "
                    "any recorded evidence row (consumer_chain, value_semantics, "
                    "dead_siblings, fix_path_helpers, or findings). Recorded "
                    "values: {1!r}.".format(grounded_in, sorted(grounding_values)),
                    code=2,
                )

            row_tokens = set(_tokenize_hypothesis(grounded_in))
            not_in_row = sorted(t for t in tokens if t not in row_tokens)
            if not_in_row:
                return _die(
                    "declare-grounded-overlap: --tokens {0!r} are not tokens of "
                    "--grounded-in {1!r} (tokenizes to {2!r}); the grounding row "
                    "must carry every declared token".format(
                        not_in_row, grounded_in, sorted(row_tokens)
                    ),
                    code=2,
                )

            cause = ""
            for h in hypotheses:
                if isinstance(h, dict) and h.get("label") == hypothesis_label:
                    cause = h.get("cause") or ""
                    break
            cause_tokens = set(_tokenize_hypothesis(cause))
            not_in_cause = sorted(t for t in tokens if t not in cause_tokens)
            if not_in_cause:
                return _die(
                    "declare-grounded-overlap: --tokens {0!r} are not tokens of "
                    "hypothesis {1!r}'s cause {2!r}; a declaration only accepts "
                    "tokens of this hypothesis's own overlap".format(
                        not_in_cause, hypothesis_label, cause
                    ),
                    code=2,
                )

            record = {
                "hypothesis": hypothesis_label,
                "tokens": tokens,
                "grounded_in": grounded_in,
            }
            declarations = report.setdefault("overlap_declarations", [])
            if record not in declarations:
                declarations.append(record)
    except (OSError, json.JSONDecodeError) as err:
        return _die("declare-grounded-overlap: {0}".format(err))
    return 0
