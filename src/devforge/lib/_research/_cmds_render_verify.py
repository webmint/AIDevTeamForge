"""Render + verify command handlers.

cmd_render emits the report markdown via _render_report_md. cmd_verify
runs the 18-check cross-state validator. Each check enumerated in the
cmd_verify docstring; violations accumulate then emit to stderr.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import List, Optional

from ._constants import VERDICT_ENUM
from ._layer_package import (
    _compute_check_8b_would_fire,
    _extract_package,
    _is_presentation_layer,
)
from _shared.literal_call_shape import _detect_arg_duplication, _detect_literal_replacement
from ._render import _render_report_md
from ._state import _load_memo, _load_report
from ._topic_conflicts import detect_direct_conflicts
from ._validators import _die, _has_anchor_finding


def cmd_render(args: argparse.Namespace) -> int:
    """Render report md to stdout. Caller decides where to save (Phase 3)."""
    import json as _json
    try:
        memo = _load_memo(args.devforge_dir)
        report = _load_report(args.devforge_dir)
    except (OSError, _json.JSONDecodeError) as err:
        return _die("render: {0}".format(err))
    try:
        text = _render_report_md(memo, report)
    except ValueError as err:
        return _die("render: {0}".format(err), code=2)
    sys.stdout.write(text)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Cross-check report state against required invariants.

    Checks (each violation → stderr line):
      1. Hypotheses: minimum 2 entries.
      2. Recommended approach: name resolves; hypotheses_addressed +
         hypotheses_not_covered non-empty arrays.
      3. Recommended approach respects memo.dimensions.unchanged_behavior:
         if unchanged_behavior contains a token also in approach
         description AND that token is associated with a value-flip
         pattern, flag a violation. Lightweight check — re-uses the
         antagonist patterns from detect_direct_conflicts against
         unchanged_behavior vs. recommended approach rationale.
      4. Verdict ∈ VERDICT_ENUM[mode].
      5. Structured root cause populated when mode==bug AND
         confidence ∈ {Confirmed, Hypothesis}: trigger +
         root_cause_systemic present; contributing_factors ≤ 3.
      6. Verify-step 3 sub-fields populated when any hypothesis has
         runtime_probe_needed=true.
      7. Summary, complexity, ≥1 approach present.
      8. fix_path_helpers non-empty for bug mode.
      8b. Bug mode + symptom is presentation-layer + all fix_path_helpers
          defined in same package → cross-layer trace required. Package
          derived from fix_path_helpers[].file_line (helper definition),
          NOT from inbound_callers call-sites. Check 13 is subordinate:
          when 8b fires, the single-layer-justification path cannot
          satisfy verify, so check 13 is suppressed to give the LLM a
          single actionable error.
      9. Every fix_path_helper has at least one inbound_callers row.
     10. If value_semantics has an invariant AND dead_siblings is non-empty,
         at least one approach mentions the signature change or dead-sibling QN.
     11. If value_semantics has an invariant, recommended_approach.rationale
         cites a consumer_chain entry, invariant evidence, or dead-sibling QN.
     12. If runner_up_framing is set, at least one finding must be tagged
         framing=runner-up (Phase 2.4 must probe the runner-up frame).
     13. Cross-layer recommendation enforcement: when bug mode + fix_path_helpers
         all resolve to the same package (single-layer), recommended_approach
         must carry single_layer_justification (non-empty) and cites (non-empty).
         Catches out-of-order setter calls where recommended_approach was set
         before fix_path_helpers collapsed to single-layer. Only fires when
         check 8b does NOT apply (i.e., symptom is NOT presentation-layer);
         for presentation-layer symptoms, check 8b is the blocking gate and
         the single-layer escape path is structurally unavailable.
     14. Anchor gate mirror (verify-time): every fix_path_helpers[].file_line
         must anchor to a finding (exact match OR same path within ±5 lines).
         Catches direct state mutation bypassing record-fix-path-helper setter.
         Gated on bug mode (consistent with checks 8 / 13).
     15. Data-flow chain required for bug mode + presentation-layer primary
         symptom: data_flow_chain must be non-null. Fires only when mode==bug
         AND the first primary finding's path is presentation-layer. Forces
         the LLM to trace from click handler through intermediates to the
         write-boundary call via record-data-flow-chain (Patch 6 / Gap 6).
     16. Hypothesis must cite production-site rewriter when any value_semantics
         row has stable_across_calls=false. Gated on bug mode. Fires when
         unstable value(s) exist in value_semantics AND no hypothesis cause
         contains any production-site file_line as a substring. Closes Gap 7
         — forces Phase 2.5 to enumerate the production-site rewriter (e.g.,
         Math.random, Date.now) as a candidate root cause when randomization
         is detected (Patch 7).
     17. Literal-archaeology required when recommended-approach prose contains
         a literal-replacement pattern ("replace <X> with <Y>" / "<X> -> <Y>"
         / etc.) and <X> is a primitive literal. Gated on bug mode. Fires when
         no literal_archaeology row exists whose literal == <X> AND whose
         file_line matches a recorded finding's file_line. Closes Gap 8 (V3)
         — forces git-blame archaeology before recommending literal replacement
         (Patch 8).

    Exit 0 = all pass. Exit 2 = at least one violation. Exit 1 = state
    files unreadable.
    """
    import json as _json
    try:
        memo = _load_memo(args.devforge_dir)
        report = _load_report(args.devforge_dir)
    except (OSError, _json.JSONDecodeError) as err:
        sys.stderr.write("research_helper verify: cannot load state: {0}\n".format(err))
        return 1

    violations = []  # type: List[str]

    # Check 1: ≥2 hypotheses.
    hyps = report.get("hypotheses") or []
    if len(hyps) < 2:
        violations.append(
            "hypothesis enumeration: have {0}, need at least 2".format(len(hyps))
        )

    # Check 2 + 3: recommended approach.
    rec = report.get("recommended_approach")
    approaches = report.get("approaches") or []
    if rec is None:
        violations.append("recommended_approach: unset")
    else:
        names = {a.get("name") for a in approaches}
        if rec.get("name") not in names:
            violations.append(
                "recommended_approach.name {0!r} does not match any approach".format(
                    rec.get("name")
                )
            )
        if not rec.get("hypotheses_addressed"):
            violations.append("recommended_approach.hypotheses_addressed: empty")
        # Check 3: unchanged_behavior cross-check.
        unchanged = memo.get("dimensions", {}).get("unchanged_behavior", {}).get("value") or ""
        # Build a temporary memo-like structure for the antagonist scan:
        # plug rationale into 'desired' slot so the existing
        # _CONFLICT_PATTERNS catch the same antagonisms vs unchanged.
        rationale = rec.get("rationale") or ""
        if unchanged and rationale:
            shadow = {
                "dimensions": {
                    "desired": {"value": rationale},
                    "unchanged_behavior": {"value": unchanged},
                }
            }
            for c in detect_direct_conflicts(shadow):
                violations.append(
                    "recommended_approach violates unchanged_behavior: {0}".format(
                        c.get("description")
                    )
                )

    # Check 4: verdict ∈ allowed.
    mode = report.get("mode") or memo.get("mode")
    verdict = report.get("verdict")
    if not mode:
        violations.append("mode: unset (run detect-mode)")
    elif verdict is None:
        violations.append("verdict: unset")
    elif verdict not in VERDICT_ENUM[mode]:
        violations.append(
            "verdict {0!r} not allowed for mode {1!r} (allowed: {2})".format(
                verdict, mode, list(VERDICT_ENUM[mode])
            )
        )

    # Check 5: structured root cause for bug-mode + confidence ≥ Hypothesis.
    confidence = report.get("confidence")
    src = report.get("structured_root_cause")
    if mode == "bug" and confidence in ("Confirmed", "Hypothesis"):
        if src is None:
            violations.append(
                "structured_root_cause required for mode==bug + confidence in "
                "{Confirmed, Hypothesis} but is null"
            )
        else:
            if not src.get("trigger"):
                violations.append("structured_root_cause.trigger: unset")
            if not src.get("root_cause_systemic"):
                violations.append("structured_root_cause.root_cause_systemic: unset")
            if len(src.get("contributing_factors") or []) > 3:
                violations.append(
                    "structured_root_cause.contributing_factors: max 3 (have {0})".format(
                        len(src.get("contributing_factors") or [])
                    )
                )

    # Check 6: verify-step when any hypothesis needs runtime probe.
    needs_probe = any(h.get("runtime_probe_needed") for h in hyps)
    vstep = report.get("verify_step")
    if needs_probe:
        if vstep is None:
            violations.append("verify_step required (a hypothesis needs runtime probe) but unset")
        else:
            for sub in ("probe", "reproduction", "discriminator"):
                if not vstep.get(sub):
                    violations.append("verify_step.{0}: unset".format(sub))

    # Check 7: minimum scaffolding present.
    if not report.get("summary"):
        violations.append("summary: unset")
    if report.get("complexity") is None:
        violations.append("complexity: unset")
    if not approaches:
        violations.append("approaches: empty")

    # Check 8: bug mode requires fix_path_helpers non-empty.
    fix_path_helpers = report.get("fix_path_helpers") or []
    if (report.get("mode") == "bug" or memo.get("mode") == "bug") and not fix_path_helpers:
        violations.append(
            "fix_path_helpers: empty (Phase 2.4c requires at least one helper enumerated for bug mode)"
        )

    # Check 8b: when bug mode + symptom is in a presentation-layer file, at
    # least one fix_path_helper must be defined in a DIFFERENT package
    # (cross-layer rule). Package derived from fix_path_helpers[].file_line
    # (the helper's definition location), NOT from inbound_callers call-sites.
    # Fires only when check 8 already passed (list non-empty) and mode==bug,
    # so the two checks compose without redundancy.
    if fix_path_helpers and (report.get("mode") == "bug" or memo.get("mode") == "bug"):
        findings_for_8b = report.get("findings") or []
        # Identify the primary symptom path: first finding with framing==primary
        # (or framing missing, which defaults to primary per record-finding).
        primary_path_8b = None  # type: Optional[str]
        for f in findings_for_8b:
            framing_val = f.get("framing") or "primary"
            if framing_val == "primary":
                fl = f.get("file_line") or ""
                colon_pos = fl.rfind(":")
                if colon_pos > 0:
                    primary_path_8b = fl[:colon_pos]
                elif fl:
                    primary_path_8b = fl
                break  # first primary finding only
        if primary_path_8b and _is_presentation_layer(primary_path_8b):
            symptom_pkg = _extract_package(primary_path_8b)
            has_cross_layer = False
            for h in fix_path_helpers:
                # Only dict entries carry file_line; skip bare strings
                # (legacy direct-JSON writes) — they contribute no package info.
                if not isinstance(h, dict):
                    continue
                # Derive helper package from the helper's own definition file_line.
                helper_file_line = h.get("file_line") or ""
                colon_pos = helper_file_line.rfind(":")
                if colon_pos > 0:
                    helper_file = helper_file_line[:colon_pos]
                else:
                    helper_file = helper_file_line
                if _extract_package(helper_file) != symptom_pkg:
                    has_cross_layer = True
                    break
            if not has_cross_layer:
                violations.append(
                    "fix_path_helpers: all entries in same package as "
                    "presentation-layer symptom site {0!r}; Phase 2.4c must "
                    "trace at least one helper UP to a different package "
                    "(cross-layer rule)".format(primary_path_8b)
                )

    # Check 9: every enumerated helper needs at least one inbound caller row.
    inbound_callers = report.get("inbound_callers") or []
    for h in fix_path_helpers:
        helper_qn = h.get("qn") if isinstance(h, dict) else h
        if not any(r.get("helper_qn") == helper_qn for r in inbound_callers):
            violations.append(
                "inbound_callers: no entry for helper {0!r} "
                "(record-inbound-caller required for every fix_path_helper)".format(helper_qn)
            )

    # Check 10: invariant + dead siblings demands signature-touching approach.
    value_semantics = report.get("value_semantics") or []
    dead_siblings = report.get("dead_siblings") or []
    has_invariant = any(v.get("classification") == "invariant" for v in value_semantics)
    if has_invariant and dead_siblings:
        candidate_tokens = {"signature", "drop param"}
        for ds in dead_siblings:
            mq = ds.get("method_qn") or ""
            if mq:
                candidate_tokens.add(mq.lower())
        found_approach = False
        for ap in approaches:
            haystack = (
                (ap.get("name") or "")
                + " "
                + (ap.get("description") or "")
                + " "
                + " ".join(ap.get("pros") or [])
                + " "
                + " ".join(ap.get("cons") or [])
            ).lower()
            if any(tok in haystack for tok in candidate_tokens):
                found_approach = True
                break
        if not found_approach:
            dead_qn_sample = (dead_siblings[0].get("method_qn") or "") if dead_siblings else ""
            violations.append(
                "approaches: value_semantics has invariant AND dead_siblings non-empty, "
                "but no approach mentions helper signature change or dead-sibling QN "
                "(cite signature change or {0!r} in an approach)".format(dead_qn_sample)
            )

    # Check 11: invariant requires evidence cite in recommended approach rationale.
    if has_invariant and rec is not None:
        rationale = (rec.get("rationale") or "").lower()
        consumer_chain = report.get("consumer_chain") or []
        candidate_rationale_tokens = []  # type: List[str]
        for cc_row in consumer_chain:
            cq = cc_row.get("consumer_qn") or ""
            if cq:
                candidate_rationale_tokens.append(cq.lower())
        for vs_row in value_semantics:
            if vs_row.get("classification") == "invariant":
                ev = vs_row.get("evidence") or ""
                if ev:
                    candidate_rationale_tokens.append(ev.lower())
        for ds in dead_siblings:
            mq = ds.get("method_qn") or ""
            if mq:
                candidate_rationale_tokens.append(mq.lower())
        if candidate_rationale_tokens and not any(tok in rationale for tok in candidate_rationale_tokens):
            violations.append(
                "recommended_approach.rationale: value_semantics has invariant, but rationale "
                "cites neither a consumer_chain entry, an invariant evidence string, "
                "nor a dead-sibling QN"
            )

    # Check 12a: Phase 2.3b is MANDATORY — runner_up_framing must be set.
    # Closes the spec-vs-helper gap where an LLM skipping Phase 2.3b entirely
    # would never trigger the conditional check 12b.
    runner_up_framing = report.get("runner_up_framing")
    if runner_up_framing is None:
        violations.append(
            "runner_up_framing: unset — Phase 2.3b is MANDATORY; "
            "call record-runner-up-framing before verify"
        )
    else:
        # Check 12b: when runner_up_framing is set, at least one finding must
        # be tagged framing=runner-up so Phase 2.4 probed the runner-up frame.
        findings = report.get("findings") or []
        runner_up_findings = [f for f in findings if f.get("framing") == "runner-up"]
        if len(runner_up_findings) < 1:
            violations.append(
                "runner_up_framing is set but no findings tagged framing=runner-up; "
                "Phase 2.4 must probe the runner-up frame with at least one finding "
                "(record-finding --framing runner-up ...)"
            )

    # Check 13: cross-layer recommendation enforcement. When bug mode +
    # fix_path_helpers all resolve to the same package (single-layer detection),
    # recommended_approach must carry single_layer_justification (non-empty) and
    # cites (non-empty). This catches out-of-order setter calls where
    # recommended_approach was written before fix_path_helpers collapsed to
    # single-layer. Closes Gap 4 (verify-time) in RESEARCH-FRAMING-REGRESSION-PLAN.
    # SUPPRESSION: check 13 is subordinate to check 8b. When 8b would fire
    # (presentation-layer symptom + all helpers same package), the single-layer-
    # justification escape is structurally unavailable — the only recovery is
    # adding cross-layer helpers. Skip check 13 so the LLM gets a single
    # actionable error from 8b rather than a misleading 13 violation pointing at
    # a path that cannot satisfy verify.
    check_13_suppressed = _compute_check_8b_would_fire(
        report, report.get("mode") == "bug" or memo.get("mode") == "bug"
    )
    if (
        (report.get("mode") == "bug" or memo.get("mode") == "bug")
        and rec is not None
        and fix_path_helpers
        and not check_13_suppressed
    ):
        packages_13 = set()
        for h in fix_path_helpers:
            if isinstance(h, dict) and h.get("file_line"):
                pkg = _extract_package(h["file_line"].rsplit(":", 1)[0])
                if pkg:
                    packages_13.add(pkg)
        if len(packages_13) == 1:
            if not (rec.get("single_layer_justification") or "").strip():
                violations.append(
                    "check 13: recommended_approach is single-layer (all fix_path_helpers "
                    "in package {0!r}) but single_layer_justification is missing or empty; "
                    "use set-recommended-approach --single-layer-justification to supply "
                    "a prose justification proving the symptom is layer-local".format(
                        next(iter(packages_13))
                    )
                )
            if not rec.get("cites"):
                violations.append(
                    "check 13: recommended_approach is single-layer (all fix_path_helpers "
                    "in package {0!r}) but cites is missing or empty; "
                    "use set-recommended-approach --cites '[\"token\"]' to cite at least one "
                    "consumer_chain.consumer_qn, value_semantics.value, value_semantics.evidence, "
                    "or dead_siblings.method_qn row proving the symptom is layer-local".format(
                        next(iter(packages_13))
                    )
                )

    # Check 14: anchor gate mirror — every fix_path_helpers[].file_line must
    # anchor to a finding (exact match OR same path within ±5 lines). Catches
    # state mutations that bypassed the record-fix-path-helper setter.
    # Gated on bug mode (consistent with checks 8 / 13).
    bug_mode_14 = (report.get("mode") == "bug" or memo.get("mode") == "bug")
    if bug_mode_14 and fix_path_helpers:
        all_findings_14 = report.get("findings") or []
        for h in fix_path_helpers:
            if not isinstance(h, dict):
                continue
            h_fl = h.get("file_line") or ""
            if not _has_anchor_finding(h_fl, all_findings_14):
                violations.append(
                    "check 14: fix_path_helper {0!r} has file_line {1!r} that does not "
                    "anchor to any recorded finding (exact match or same path within ±5 "
                    "lines); direct state mutation likely bypassed record-fix-path-helper "
                    "anchor gate".format(h.get("qn"), h_fl)
                )

    # Check 15: data-flow chain required for bug mode + presentation-layer symptom.
    # Fires when mode==bug AND the first primary finding's path is presentation-layer.
    # Requires data_flow_chain to be non-null (set via record-data-flow-chain).
    # NOTE: check 15 is set-time only — intermediate_qns→Finding references are
    # validated at record-data-flow-chain call time and not re-walked here.
    # Direct JSON mutation that sets an arbitrary truthy value bypasses the
    # intermediate gate. Deferred until empirical evidence shows the bypass is
    # exploited; closing it would require duplicating the substring check here.
    bug_mode_15 = (report.get("mode") == "bug" or memo.get("mode") == "bug")
    if bug_mode_15:
        # Reuse the primary finding path extraction pattern from check 8b.
        all_findings_15 = report.get("findings") or []
        primary_path_15 = None  # type: Optional[str]
        for f in all_findings_15:
            framing_val = f.get("framing") or "primary"
            if framing_val == "primary":
                fl = f.get("file_line") or ""
                colon_pos = fl.rfind(":")
                if colon_pos > 0:
                    primary_path_15 = fl[:colon_pos]
                elif fl:
                    primary_path_15 = fl
                break  # first primary finding only
        if primary_path_15 and _is_presentation_layer(primary_path_15):
            if not report.get("data_flow_chain"):
                violations.append(
                    "check 15: data_flow_chain is unset for bug-mode + presentation-layer "
                    "symptom at {0!r}; Phase 2.4d MANDATORY — trace from click handler to "
                    "write-boundary call via trace_path mode=calls and record via "
                    "record-data-flow-chain".format(primary_path_15)
                )

    # Check 16: when any value_semantics row has stable_across_calls=false, at least
    # one hypothesis must cite the production-site rewriter file:line. Closes Gap 7 —
    # forces hypothesis enumeration to surface the production-site rewriter as a
    # candidate root cause when randomization is detected.
    bug_mode_16 = (report.get("mode") == "bug" or memo.get("mode") == "bug")
    if bug_mode_16:
        unstable_values = [
            v["value"]
            for v in (report.get("value_semantics") or [])
            if v.get("stable_across_calls") == "false"
        ]
        if unstable_values:
            production_sites = report.get("value_production_sites") or []
            hypothesis_causes = [
                h.get("cause") or ""
                for h in (report.get("hypotheses") or [])
            ]
            # For all unstable values, gather their production-site file_line strings.
            all_site_file_lines = [
                s["file_line"]
                for s in production_sites
                if s.get("value") in unstable_values and s.get("file_line")
            ]
            # At least one hypothesis cause must contain at least one site file_line.
            # Use word-boundary lookahead so "src/foo.ts:5" does NOT match "src/foo.ts:50"
            # (prefix collision would let the LLM cite an adjacent-but-wrong line).
            def _cause_cites_site(cause: str, site_fl: str) -> bool:
                return bool(re.search(re.escape(site_fl) + r"(?!\d)", cause))

            cited = any(
                _cause_cites_site(cause, site_fl)
                for cause in hypothesis_causes
                for site_fl in all_site_file_lines
            )
            if not cited:
                violations.append(
                    "check 16: value_semantics has invariant-but-unstable row(s) "
                    "({0}) but no hypothesis cites the production-site rewriter "
                    "file_line ({1}); Phase 2.5 must enumerate the production-site "
                    "rewriter as a candidate root cause".format(
                        unstable_values,
                        [s.get("file_line") for s in production_sites
                         if s.get("value") in unstable_values],
                    )
                )

    # Patch 8 (V3) — Gap 8: literal-archaeology requirement on bug-mode
    # recommended approach. When the recommended approach's rationale OR the
    # linked approach.description contains a literal-replacement pattern
    # ("replace <X> with <Y>" / "<X> -> <Y>" / etc.) where <X> is a primitive
    # literal, require a matching literal_archaeology row.
    bug_mode_17 = (report.get("mode") == "bug" or memo.get("mode") == "bug")
    rec_approach = report.get("recommended_approach") or {}
    if bug_mode_17 and rec_approach:
        # Pull prose from BOTH the rationale AND the linked approach's description.
        rationale_text = rec_approach.get("rationale") or ""
        linked_name = rec_approach.get("name")
        approach_desc = ""
        if linked_name:
            for ap in report.get("approaches") or []:
                if ap.get("name") == linked_name:
                    approach_desc = ap.get("description") or ""
                    break
        combined_text = "{0} {1}".format(rationale_text, approach_desc)
        detected_literal = _detect_literal_replacement(combined_text)
        if detected_literal is not None:
            archaeology = report.get("literal_archaeology") or []
            # Collect file_lines from findings (anchor surface).
            finding_file_lines = {
                f.get("file_line") for f in (report.get("findings") or [])
                if f.get("file_line")
            }
            # Match: at least one archaeology row whose literal == detected_literal
            # AND whose file_line ∈ findings[].file_line.
            matched = any(
                row.get("literal") == detected_literal
                and row.get("file_line") in finding_file_lines
                for row in archaeology
            )
            if not matched:
                violations.append(
                    "check 17: recommended approach proposes replacing literal "
                    "{0!r} (detected in rationale or linked approach description) "
                    "but no literal_archaeology record exists for it at a recorded "
                    "finding's file_line. Run `git log -S {0!r} -- <file>` + "
                    "`git blame -L <start>,<end> <file>`; classify intent "
                    "(placeholder / migrated / deliberate / forgotten / "
                    "inherited-refactor / generated); then call "
                    "record-literal-archaeology before set-recommended-approach.".format(
                        detected_literal
                    )
                )

    # Patch 9 (V3) — Gap 9: argument-duplication shape check at verify
    # time. Mirrors the setter gate; catches state-mutation bypass where
    # someone wrote proposed_call_shape directly to JSON without going
    # through set-recommended-approach.
    bug_mode_18 = (report.get("mode") == "bug" or memo.get("mode") == "bug")
    rec_approach_18 = report.get("recommended_approach") or {}
    if bug_mode_18 and rec_approach_18:
        proposed_shape_18 = rec_approach_18.get("proposed_call_shape")
        if proposed_shape_18:
            dup_18 = _detect_arg_duplication(proposed_shape_18)
            if dup_18 is not None:
                ident_18, count_18 = dup_18
                violations.append(
                    "check 18: recommended_approach.proposed_call_shape "
                    "{0!r} contains argument duplication ({1!r} appears "
                    "{2} times). Default-source belongs at a different "
                    "layer (wrapper signature / state initialization / "
                    "use-case default); re-call set-recommended-approach "
                    "with a non-duplicating shape.".format(
                        proposed_shape_18, ident_18, count_18
                    )
                )

    if violations:
        for v in violations:
            sys.stderr.write("research_helper verify: {0}\n".format(v))
        return 2
    return 0
