"""Phase 2 setters: constitution-constraints / complexity / verdict / summary / next-step."""

from __future__ import annotations

import argparse
import json

from ._constants import COMPLEXITY_ENUM, VERDICT_ENUM, VERDICT_PROCEEDING
from ._state import _load_memo, _state_transaction
from ._validators import (
    _die,
    _validate_enum,
    _validate_scalar,
    _validate_verbatim,
)


def cmd_set_constitution_constraints(args: argparse.Namespace) -> int:
    """Append a {rule, impact} record."""
    try:
        rule = _validate_scalar(args.rule, "constitution.rule")
        impact = _validate_scalar(args.impact, "constitution.impact")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("constitution_constraints", []).append(
                {"rule": rule, "impact": impact}
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-constitution-constraints: {0}".format(err))
    return 0


def cmd_set_complexity(args: argparse.Namespace) -> int:
    """Set complexity record (3 ratings + 3 notes)."""
    try:
        cc = _validate_enum(args.codebase_changes, "complexity.codebase_changes", COMPLEXITY_ENUM)
        cn = _validate_scalar(args.codebase_notes, "complexity.codebase_notes")
        rk = _validate_enum(args.risk, "complexity.risk", COMPLEXITY_ENUM)
        rn = _validate_scalar(args.risk_notes, "complexity.risk_notes")
        vc = _validate_enum(args.verify_cost, "complexity.verify_cost", COMPLEXITY_ENUM)
        vn = _validate_scalar(args.verify_notes, "complexity.verify_notes")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["complexity"] = {
                "codebase_changes": cc,
                "codebase_notes": cn,
                "risk": rk,
                "risk_notes": rn,
                "verify_cost": vc,
                "verify_notes": vn,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-complexity: {0}".format(err))
    return 0


def cmd_set_verdict(args: argparse.Namespace) -> int:
    """Set verdict. Mode-aware: must be in VERDICT_ENUM[memo.mode]."""
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-verdict: cannot load memo: {0}".format(err))
    mode = memo.get("mode")
    if mode not in VERDICT_ENUM:
        return _die(
            "set-verdict: mode must be set before verdict (run detect-mode first); have {0!r}".format(mode),
            code=2,
        )
    try:
        value = _validate_enum(args.value, "verdict", VERDICT_ENUM[mode])
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["mode"] = mode
            report["verdict"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-verdict: {0}".format(err))
    return 0


def cmd_set_summary(args: argparse.Namespace) -> int:
    """Set summary (3-5 sentence opener)."""
    try:
        value = _validate_verbatim(args.value, "summary")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["summary"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-summary: {0}".format(err))
    return 0


def cmd_set_next_step_text(args: argparse.Namespace) -> int:
    """Compose next-step text from memo + report.

    Renders the copy-pasteable /specify prompt + key facts block. Only
    emits when verdict ∈ VERDICT_PROCEEDING[mode]. Otherwise sets
    next_step_text = None and exits 0 (no error).

    Plan 68 D1/D2 "Research reference" line — mechanism choice: every
    other dynamic value in this block (mode, symptom, desired approach,
    …) is read from already-persisted state, not an accompanying CLI arg,
    but the eventual research-report.md path cannot follow that pattern:
    this verb runs at Phase 3, and the feature dir it will live under is
    not allocated until Phase 4's save+slug confirmation (D1's fixed
    ordering) -- so there is no state field to read it from either.
    --research-path is therefore an optional CLI arg, consistent with how
    a genuinely orchestrator-known-only value is supplied elsewhere in
    this helper (e.g. record-probe-script's --script-path): pass it when
    the caller already knows the final path, omit it otherwise. When
    omitted, the line renders a path-free placeholder rather than the
    retired research/<date>-<slug>.md literal -- this text is echoed to
    the user before the save prompt (Phase 3's "Render" step), so it must
    never show a location that turns out to be wrong.
    """
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-next-step-text: cannot load memo: {0}".format(err))

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            mode = report.get("mode") or memo.get("mode")
            verdict = report.get("verdict")
            if not mode or not verdict:
                return _die(
                    "set-next-step-text: mode + verdict must be set first",
                    code=2,
                )
            if verdict not in VERDICT_PROCEEDING.get(mode, set()):
                report["next_step_text"] = None
                return 0

            symptom = memo.get("dimensions", {}).get("symptom", {}).get("value") or ""
            desired = memo.get("dimensions", {}).get("desired", {}).get("value") or ""
            rec_approach = report.get("recommended_approach") or {}
            approach_name = rec_approach.get("name") or "(approach name)"
            addressed = rec_approach.get("hypotheses_addressed") or []
            not_covered = rec_approach.get("hypotheses_not_covered") or []

            refined = (symptom + " — " + desired).strip(" —")
            refined_short = refined if refined else "topic"
            research_reference = getattr(args, "research_path", None) or (
                "(path assigned when this research is saved to its feature "
                "directory)"
            )
            text = (
                "## Next step\n\n"
                "Copy the block below into a new `/specify` session manually. "
                "No automation — user controls when (or if) `/specify` runs.\n\n"
                "~~~\n"
                "/specify \"{refined}\"\n\n"
                "Research reference: {research_reference}\n"
                "Key facts:\n"
                "- Mode: {mode}\n"
                "- Symptom: {sym}\n"
                "- Desired: {des}\n"
                "- Recommended approach: {appr}\n"
                "- Hypothesis addressed: {addr}\n"
                "- Hypotheses NOT covered: {nc}\n"
                "- Open uncertainties: {gaps} (see research doc §Open Uncertainties)\n"
                "~~~\n"
            ).format(
                refined=refined_short,
                research_reference=research_reference,
                mode="Bug" if mode == "bug" else "Enhancement",
                sym=symptom or "(unset)",
                des=desired or "(unset)",
                appr=approach_name,
                addr=", ".join(addressed) if addressed else "(none)",
                nc=", ".join(not_covered) if not_covered else "(none)",
                gaps=len(memo.get("gaps", [])),
            )
            report["next_step_text"] = text
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-next-step-text: {0}".format(err))
    return 0
