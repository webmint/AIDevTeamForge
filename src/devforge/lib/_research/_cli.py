"""argparse parser + dispatch + main entry for research_helper.

build_parser composes the top-level + subparsers. _register_subcommands
attaches every cmd_* handler. main parses argv + dispatches.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from ._constants import (
    CONFIDENCE_VS_PRIMARY_ENUM,
    COMPLEXITY_ENUM,
    FRAMING_ENUM,
    MODE_ENUM,
    RUBRIC_DIMENSIONS,
    RUBRIC_STATE_ENUM,
)
from ._cmds_basic import (
    cmd_preflight,
    cmd_read_memo,
    cmd_read_report,
    cmd_reset_memo,
    cmd_reset_report,
    cmd_set_date,
    cmd_set_topic,
    cmd_set_verbatim_prompt,
    cmd_summary,
)
from ._cmds_phase0 import (
    _make_dim_setter,
    _make_scope_setter,
    cmd_check_conflicts,
    cmd_detect_mode,
    cmd_record_conflict_resolution,
    cmd_record_gap,
    cmd_symptom_coverage,
    cmd_symptom_finalize,
)
from ._cmds_phase1 import (
    cmd_classify_finding_literal,
    cmd_record_contributing_factor,
    cmd_record_finding,
    cmd_record_hypothesis,
    cmd_record_runner_up_framing,
    cmd_set_confidence,
    cmd_set_root_cause_hypothesis,
    cmd_set_root_cause_systemic,
    cmd_set_trigger,
    cmd_set_verify_step,
)
from ._cmds_approach import cmd_set_approach, cmd_set_recommended_approach
from ._cmds_phase2 import (
    cmd_set_complexity,
    cmd_set_constitution_constraints,
    cmd_set_next_step_text,
    cmd_set_summary,
    cmd_set_verdict,
)
from ._cmds_dataflow import (
    cmd_classify_caller_scope,
    cmd_declare_caller_total,
    cmd_record_consumer_chain,
    cmd_record_data_flow_chain,
    cmd_record_dead_sibling,
    cmd_record_fix_path_helper,
    cmd_record_inbound_caller,
    cmd_record_literal_archaeology,
    cmd_record_no_shared_callers_justification,
    cmd_record_probe_script,
    cmd_record_value_production_site,
    cmd_set_value_semantics,
)
from ._cmds_render_verify import cmd_render, cmd_verify, cmd_verify_hypothesis_suppression
from ._cmds_intake import (
    INTAKE_KIND_ENUM,
    cmd_record_intake_classification,
    cmd_render_intake_echo,
)
from ._cmds_handoff import (
    cmd_append_outcome,
    cmd_check_outcome,
    cmd_finalize_handoff,
    cmd_set_probe_feasibility,
)
from ._cmds_design_anchor import cmd_set_design_anchor
from ._cmds_evidence_lanes import cmd_set_evidence_lanes
from ._cmds_feature_alloc import (
    cmd_allocate_feature_dir,
    cmd_render_branch_command,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research_helper",
        description="State + render helper for /devforge:research. Owns research artifact shape.",
    )
    parser.add_argument(
        "--devforge-dir",
        default=".devforge",
        help="Path to the .devforge directory (default: .devforge in CWD).",
    )
    parser.add_argument(
        "--install-root",
        default=None,
        help=(
            "Path to the install root (project root for standalone, wrapper "
            "root for wrapper mode). Default: parent of --devforge-dir."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers) -> None:
    """All cmd_* handlers attached here. Implemented in sibling modules."""
    # Plumbing
    sp = subparsers.add_parser("reset-memo", help="Write a fresh defaults memo state.")
    sp.set_defaults(func=cmd_reset_memo)

    sp = subparsers.add_parser("reset-report", help="Write a fresh defaults report state.")
    sp.set_defaults(func=cmd_reset_report)

    sp = subparsers.add_parser("read-memo", help="Print research-state.json (or defaults) as JSON.")
    sp.set_defaults(func=cmd_read_memo)

    sp = subparsers.add_parser("read-report", help="Print research-report.json (or defaults) as JSON.")
    sp.set_defaults(func=cmd_read_report)

    sp = subparsers.add_parser(
        "preflight",
        help="Hard-gate check: 4 setup-chain artefacts present + non-empty.",
    )
    sp.set_defaults(func=cmd_preflight)

    sp = subparsers.add_parser(
        "set-topic",
        help="Set report.topic + auto-derive memo.topic_slug.",
    )
    sp.add_argument("--value", required=True, help="Topic text (user's original input).")
    sp.set_defaults(func=cmd_set_topic)

    sp = subparsers.add_parser(
        "set-verbatim-prompt",
        help=(
            "Persist the full raw prompt text to memo.verbatim_prompt. "
            "Called at Phase 0.3 right after set-topic, before the rubric. "
            "Distinct from set-topic: carries the full $ARGUMENTS including any "
            "'Suspected cause:' tail or other context the one-sentence topic loses."
        ),
    )
    sp.add_argument(
        "--value",
        required=True,
        help="Full raw prompt text (verbatim, multi-sentence ok).",
    )
    sp.set_defaults(func=cmd_set_verbatim_prompt)

    sp = subparsers.add_parser(
        "set-date",
        help="Set report.date (YYYY-MM-DD).",
    )
    sp.add_argument("--value", required=True, help="Date in YYYY-MM-DD format.")
    sp.set_defaults(func=cmd_set_date)

    sp = subparsers.add_parser(
        "summary",
        help="Render combined memo + report summary to stdout. Read-only.",
    )
    sp.set_defaults(func=cmd_summary)

    # Phase 0 setters — 5 non-scope dims built uniformly in the loop;
    # scope built separately below with the evidence gate.
    for dim in RUBRIC_DIMENSIONS:
        if dim == "scope":
            continue
        sp_name = "set-" + dim.replace("_", "-")
        sp = subparsers.add_parser(sp_name, help="Set {0} dimension.".format(dim))
        sp.add_argument("--value", required=True, help="Value text (verbatim).")
        sp.add_argument(
            "--state",
            default="Clear",
            choices=list(RUBRIC_STATE_ENUM),
            help="State after this set (default: Clear).",
        )
        sp.add_argument(
            "--increment-turn",
            action="store_true",
            help="Increment turn counter (use for follow-ups that didn't fully clear).",
        )
        sp.set_defaults(func=_make_dim_setter(dim))

    # Scope setter — special-cased to add --evidence gate for "one place".
    sp = subparsers.add_parser(
        "set-scope",
        help=(
            "Set scope dimension. "
            "--evidence is required when --value normalizes to 'one place'."
        ),
    )
    sp.add_argument("--value", required=True, help="Value text (verbatim).")
    sp.add_argument(
        "--state",
        default="Clear",
        choices=list(RUBRIC_STATE_ENUM),
        help="State after this set (default: Clear).",
    )
    sp.add_argument(
        "--increment-turn",
        action="store_true",
        help="Increment turn counter (use for follow-ups that didn't fully clear).",
    )
    sp.add_argument(
        "--evidence",
        default=None,
        help=(
            "file:line citation proving the bug is localized. "
            "Required when --value normalizes to 'one place'; ignored otherwise."
        ),
    )
    sp.set_defaults(func=_make_scope_setter())

    # Plan 53 Phase 1 — design-anchor capture (optional; not gated by
    # symptom-finalize; see _cmds_design_anchor.py docstring).
    sp = subparsers.add_parser(
        "set-design-anchor",
        help=(
            "Capture design intent: kind + file (parsed from --value "
            "'<scheme>:<target>' via parse_design_source) + selectors (JSON "
            "array of intent selector strings). Optional — an empty/unset "
            "anchor is the valid default (plan 53 D3/D5)."
        ),
    )
    sp.add_argument(
        "--value",
        required=True,
        help="'<scheme>:<target>' (scheme one of html|figma|screenshot) or the literal 'none'.",
    )
    sp.add_argument(
        "--selectors",
        required=True,
        help='JSON array of intent selector strings (may be "[]").',
    )
    sp.add_argument(
        "--state",
        default="Clear",
        choices=list(RUBRIC_STATE_ENUM),
        help="State after this set (default: Clear). Informational only — not gated.",
    )
    sp.set_defaults(func=cmd_set_design_anchor)

    sp = subparsers.add_parser(
        "detect-mode",
        help="Detect bug vs enhancement from symptom tokens, optionally with --override.",
    )
    sp.add_argument("--override", default=None, choices=list(MODE_ENUM), help="Force a mode.")
    sp.set_defaults(func=cmd_detect_mode)

    sp = subparsers.add_parser(
        "finalize-handoff",
        help="Emit research-handoff.json from research state (terminal phase).",
    )
    sp.add_argument(
        "--feature-dir",
        default=None,
        dest="feature_dir",
        help=(
            "specs/NNN-slug feature dir (plan 68 D1/D2/D7). Derives the "
            "default --emit-handoff-json target (<feature-dir>/"
            "research-handoff.json) and the default research_path "
            "(<feature-dir>/research-report.md). Mutually exclusive with "
            "--emit-handoff-json -- exactly one of the two is required."
        ),
    )
    sp.add_argument(
        "--emit-handoff-json",
        default=None,
        dest="emit_handoff_json",
        help=(
            "Explicit handoff.json target path. Mutually exclusive with "
            "--feature-dir -- exactly one of the two is required. When "
            "used without --feature-dir, research_path still defaults to "
            "a sibling research-report.md next to this path (unless "
            "--research-md-path overrides it)."
        ),
    )
    sp.add_argument(
        "--research-md-path",
        default=None,
        dest="research_md_path",
        help=(
            "Override research_path in the handoff (default: a sibling "
            "research-report.md next to the resolved --feature-dir / "
            "--emit-handoff-json target)."
        ),
    )
    sp.set_defaults(func=cmd_finalize_handoff)

    sp = subparsers.add_parser(
        "set-probe-feasibility",
        help="Record probe-feasibility flags (5 booleans) before finalize-handoff.",
    )
    for _flag in (
        "--data-shape-only",
        "--auth-required",
        "--network-dependent",
        "--timing-dependent",
        "--is-test-code",
    ):
        sp.add_argument(_flag, required=True, choices=("true", "false"))
    sp.set_defaults(func=cmd_set_probe_feasibility)

    # Plan 73 D7 — self-declared evidence-lane record (not-covered
    # evidence-lane declaration). Gate on the declaration EXISTING, never
    # per-lane: all four flags are required on THIS call so the record is
    # atomic, and finalize-handoff (_cmds_handoff.py) refuses to run until
    # this setter has been called at least once (a call-happened check, not
    # a per-lane-value check — see _cmds_evidence_lanes.py module
    # docstring).
    sp = subparsers.add_parser(
        "set-evidence-lanes",
        help=(
            "Record which evidence lanes this run consulted (4 booleans: "
            "static graph / text search / runtime probe / history) before "
            "finalize-handoff."
        ),
    )
    for _flag in (
        "--static-graph",
        "--text-search",
        "--runtime-probe",
        "--history",
    ):
        sp.add_argument(_flag, required=True, choices=("true", "false"))
    sp.set_defaults(func=cmd_set_evidence_lanes)

    sp = subparsers.add_parser(
        "record-gap",
        help="Record a [NEEDS CLARIFICATION] gap for a dimension and accept exit.",
    )
    sp.add_argument("--dimension", required=True, choices=list(RUBRIC_DIMENSIONS))
    sp.add_argument("--description", required=True, help="Gap description.")
    sp.set_defaults(func=cmd_record_gap)

    sp = subparsers.add_parser(
        "check-conflicts",
        help="Scan dimensions for direct contradictions; emit JSON list.",
    )
    sp.set_defaults(func=cmd_check_conflicts)

    sp = subparsers.add_parser(
        "record-conflict-resolution",
        help="Log user resolution for a previously detected conflict.",
    )
    sp.add_argument("--index", required=True, type=int, help="0-based index into conflicts list.")
    sp.add_argument("--resolution", required=True, help="Resolution label.")
    sp.add_argument(
        "--rewrite-dimension",
        default=None,
        choices=list(RUBRIC_DIMENSIONS),
        help="Optional dimension whose value to clear (loser of direct conflict).",
    )
    sp.set_defaults(func=cmd_record_conflict_resolution)

    sp = subparsers.add_parser(
        "symptom-coverage",
        help="Emit JSON coverage map per dimension + counts.",
    )
    sp.set_defaults(func=cmd_symptom_coverage)

    sp = subparsers.add_parser(
        "symptom-finalize",
        help=(
            "Validate memo: all Clear OR override_recorded; no blocked conflicts. "
            "Exit 0 = ready for Phase 1; non-zero otherwise."
        ),
    )
    sp.add_argument(
        "--accept-gaps",
        action="store_true",
        help="User explicitly accepted Partial/Missing dimensions; record override.",
    )
    sp.set_defaults(func=cmd_symptom_finalize)

    # Phase 1 setters
    sp = subparsers.add_parser(
        "record-finding",
        help="Append a {surface, file_line, relevance, framing} Finding to report.findings.",
    )
    sp.add_argument("--surface", required=True)
    sp.add_argument("--file-line", required=True, dest="file_line")
    sp.add_argument("--relevance", required=True)
    sp.add_argument(
        "--framing",
        default="primary",
        choices=list(FRAMING_ENUM),
        dest="framing",
        help="Which framing this finding supports (default: primary).",
    )
    sp.add_argument(
        "--rests-on-literal",
        default=None,
        dest="rests_on_literal",
        help=(
            "Optional (plan 73 D4): '<file:line>' when this finding's "
            "grounds rest on a primitive literal's VALUE as evidence for a "
            "scope call (dead/live, keep/delete) -- the file:line where "
            "that literal lives -- or the literal 'none' when they do not. "
            "Not required here (record-finding's 74 subprocess call sites "
            "predate this flag); verify's check 20 forces every finding to "
            "answer it, and any file:line answer requires a matching "
            "record-literal-archaeology row at that file_line. To answer "
            "this on a finding already recorded (this flag omitted, or a "
            "pre-plan-73 report), use classify-finding-literal instead of "
            "re-calling record-finding, which would append a duplicate."
        ),
    )
    sp.set_defaults(func=cmd_record_finding)

    sp = subparsers.add_parser(
        "classify-finding-literal",
        help=(
            "Update rests_on_literal on an already-recorded Finding, "
            "identified by (--surface, --file-line) (plan 73 HIGH-finding "
            "fix). Sibling setter to record-finding, mirroring "
            "classify-caller-scope: record-finding is pure-append with no "
            "update path, so this is the repair route for a finding "
            "recorded before --rests-on-literal existed (a pre-upgrade "
            "report.json) or one recorded with the flag omitted -- without "
            "reset-report, which would wipe all Phase 2/3 state."
        ),
    )
    sp.add_argument(
        "--surface", required=True,
        help="Must match an existing report.findings[].surface for the same row.",
    )
    sp.add_argument(
        "--file-line", required=True, dest="file_line",
        help="Must match an existing report.findings[].file_line for the same row.",
    )
    sp.add_argument(
        "--rests-on-literal",
        required=True,
        dest="rests_on_literal",
        help=(
            "'<file:line>' when this finding's grounds rest on a primitive "
            "literal's VALUE as evidence for a scope call (dead/live, "
            "keep/delete) -- the file:line where that literal lives -- or "
            "the literal 'none' when they do not. Same validation as "
            "record-finding's own --rests-on-literal."
        ),
    )
    sp.add_argument(
        "--all",
        action="store_true",
        help=(
            "(surface, file_line) is not a unique key -- more than one "
            "recorded finding can share it while resting on DIFFERENT "
            "literals. When more than one row matches, this call REJECTS "
            "(exit 2) unless --all is passed to confirm the SAME "
            "--rests-on-literal answer genuinely applies to every "
            "matching row, and update them all. A single matching row "
            "always updates without --all."
        ),
    )
    sp.set_defaults(func=cmd_classify_finding_literal)

    sp = subparsers.add_parser(
        "record-runner-up-framing",
        help=(
            "Set report.runner_up_framing {frame, falsifier, confidence_vs_primary}. "
            "Overwrites any prior value (last call wins). "
            "Required before Phase 2.4 searches start."
        ),
    )
    sp.add_argument("--frame", required=True, dest="frame",
                    help="One-sentence alternative root cause.")
    sp.add_argument("--falsifier", required=True, dest="falsifier",
                    help="Concrete evidence that would confirm this framing over the primary.")
    sp.add_argument(
        "--confidence-vs-primary",
        required=True,
        dest="confidence_vs_primary",
        choices=list(CONFIDENCE_VS_PRIMARY_ENUM),
        help="Confidence of runner-up vs primary: lower|comparable|higher.",
    )
    sp.set_defaults(func=cmd_record_runner_up_framing)

    sp = subparsers.add_parser(
        "record-hypothesis",
        help="Append a {cause, falsifier, runtime_probe_needed} Hypothesis to report.hypotheses.",
    )
    sp.add_argument("--cause", required=True)
    sp.add_argument("--falsifier", required=True)
    sp.add_argument(
        "--runtime-probe-needed",
        choices=("yes", "no"),
        required=True,
        dest="runtime_probe_needed",
    )
    sp.set_defaults(func=cmd_record_hypothesis)

    sp = subparsers.add_parser(
        "set-root-cause-hypothesis",
        help="Set primary root-cause-hypothesis text on report.",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_root_cause_hypothesis)

    sp = subparsers.add_parser(
        "set-confidence",
        help="Set confidence enum (Confirmed | Hypothesis | Speculative).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_confidence)

    sp = subparsers.add_parser(
        "set-trigger",
        help="Set structured-root-cause trigger (bug-mode + confidence ≥ Hypothesis only).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_trigger)

    sp = subparsers.add_parser(
        "set-root-cause-systemic",
        help="Set structured-root-cause systemic flaw (bug-mode + confidence ≥ Hypothesis only).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_root_cause_systemic)

    sp = subparsers.add_parser(
        "record-contributing-factor",
        help="Append a contributing factor (bug-mode + confidence ≥ Hypothesis; max 3).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_record_contributing_factor)

    sp = subparsers.add_parser(
        "set-verify-step",
        help="Set verify-step 3 sub-fields (probe + reproduction + discriminator).",
    )
    sp.add_argument("--probe", required=True)
    sp.add_argument("--reproduction", required=True)
    sp.add_argument("--discriminator", required=True)
    sp.set_defaults(func=cmd_set_verify_step)

    # Phase 2 setters
    sp = subparsers.add_parser(
        "set-approach",
        help="Append an Approach to report.approaches.",
    )
    sp.add_argument("--name", required=True)
    sp.add_argument("--description", required=True)
    sp.add_argument(
        "--addresses-hypotheses",
        required=True,
        dest="addresses",
        help='JSON array of hypothesis-index strings (e.g. ["A","B"]).',
    )
    sp.add_argument(
        "--does-not-cover",
        required=True,
        dest="does_not_cover",
        help='JSON array of hypothesis-index strings.',
    )
    sp.add_argument("--pros", required=True, help='JSON array of pros strings.')
    sp.add_argument("--cons", required=True, help='JSON array of cons strings.')
    sp.add_argument("--complexity", required=True, choices=list(COMPLEXITY_ENUM))
    sp.set_defaults(func=cmd_set_approach)

    sp = subparsers.add_parser(
        "set-recommended-approach",
        help="Set recommended approach. Must cite hypotheses + respect unchanged_behavior.",
    )
    sp.add_argument("--name", required=True, help="Must match an existing approach.name.")
    sp.add_argument("--rationale", required=True)
    sp.add_argument(
        "--hypotheses-addressed",
        required=True,
        dest="hypotheses_addressed",
        help="JSON array of hypothesis-index strings.",
    )
    sp.add_argument(
        "--hypotheses-not-covered",
        required=True,
        dest="hypotheses_not_covered",
        help="JSON array of hypothesis-index strings.",
    )
    sp.add_argument(
        "--single-layer-justification",
        default=None,
        dest="single_layer_justification",
        help=(
            "Prose justification for a single-layer recommendation. Required when all "
            "fix_path_helpers resolve to the same package (single-layer detection) "
            "AND the symptom is NOT a presentation-layer file. "
            "Path is only available for non-presentation-layer symptoms; "
            "presentation-layer symptoms must trace through a package boundary (see check 8b). "
            "Must be accompanied by --cites citing recorded evidence rows."
        ),
    )
    sp.add_argument(
        "--cites",
        default=None,
        dest="cites",
        help=(
            "JSON array of cite tokens (consumer_chain.consumer_qn, value_semantics.value, "
            "value_semantics.evidence, or dead_siblings.method_qn) proving the symptom is "
            "layer-local. Required when --single-layer-justification is provided."
        ),
    )
    sp.add_argument(
        "--proposed-call-shape",
        default=None,
        dest="proposed_call_shape",
        help=(
            "Exact post-fix call as it would appear at the fix site. "
            "REQUIRED when --single-layer-justification is set OR --rationale "
            "contains literal-replacement prose (mode-independent -- plan 69 "
            "D6/WI-F). Helper checks for argument duplication (same identifier "
            "appearing >1 time) — duplication signals the default-source "
            "belongs at a different layer (wrapper signature / state-init / "
            "use-case default) and rejects."
        ),
    )
    sp.set_defaults(func=cmd_set_recommended_approach)

    sp = subparsers.add_parser(
        "set-constitution-constraints",
        help="Append (rule, impact) record to constitution_constraints.",
    )
    sp.add_argument("--rule", required=True)
    sp.add_argument("--impact", required=True)
    sp.set_defaults(func=cmd_set_constitution_constraints)

    sp = subparsers.add_parser(
        "set-complexity",
        help="Set complexity sub-fields (codebase_changes + risk + verify_cost).",
    )
    sp.add_argument("--codebase-changes", required=True, dest="codebase_changes",
                    choices=list(COMPLEXITY_ENUM))
    sp.add_argument("--codebase-notes", required=True, dest="codebase_notes")
    sp.add_argument("--risk", required=True, choices=list(COMPLEXITY_ENUM))
    sp.add_argument("--risk-notes", required=True, dest="risk_notes")
    sp.add_argument("--verify-cost", required=True, dest="verify_cost",
                    choices=list(COMPLEXITY_ENUM))
    sp.add_argument("--verify-notes", required=True, dest="verify_notes")
    sp.set_defaults(func=cmd_set_complexity)

    sp = subparsers.add_parser(
        "set-verdict",
        help="Set verdict (mode-aware enum). Rejects values outside mode's allowed set.",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_verdict)

    sp = subparsers.add_parser(
        "set-summary",
        help="Set summary (3-5 sentence opener).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_summary)

    sp = subparsers.add_parser(
        "set-next-step-text",
        help="Compose next-step text from memo + report; only when verdict proceeds.",
    )
    sp.add_argument(
        "--research-path",
        default=None,
        dest="research_path",
        help=(
            "Feature-dir-relative research-report.md path to cite in the "
            "'Research reference' line (plan 68 -- known only when the "
            "caller has already allocated the feature dir). Omit to render "
            "a path-free placeholder instead."
        ),
    )
    sp.set_defaults(func=cmd_set_next_step_text)

    sp = subparsers.add_parser(
        "render",
        help="Walk schema + state; emit research report md to stdout.",
    )
    sp.set_defaults(func=cmd_render)

    sp = subparsers.add_parser(
        "verify",
        help="Cross-check report state for required invariants. Exit 0 pass / 2 violations.",
    )
    sp.set_defaults(func=cmd_verify)

    sp = subparsers.add_parser(
        "verify-hypothesis-suppression",
        help=(
            "Gate: exit 2 when any unverified hypothesis cause overlaps the "
            "recommended-approach rationale (MEDIUM/LOW probe tier or unresolved "
            "feasibility discriminator). Exit 0 when clean or tier is HIGH."
        ),
    )
    sp.set_defaults(func=cmd_verify_hypothesis_suppression)

    # Phase 2.4c setters
    sp = subparsers.add_parser(
        "record-fix-path-helper",
        help="Append a {qn, file_line} helper entry to fix_path_helpers (deduped on qn).",
    )
    sp.add_argument("--helper-qn", required=True, dest="helper_qn")
    sp.add_argument(
        "--file-line",
        required=True,
        dest="file_line",
        help=(
            "Helper definition location as file:line (from search_graph result). "
            "Must be a real path — sentinel '(none)' is rejected here because "
            "the file_line is used for package extraction in check 8b."
        ),
    )
    sp.set_defaults(func=cmd_record_fix_path_helper)

    sp = subparsers.add_parser(
        "record-no-shared-callers-justification",
        help=(
            "Record the check-8 escape: an explicit prose justification asserting "
            "the change touches no existing shared symbol with other callers."
        ),
    )
    sp.add_argument(
        "--justification",
        required=True,
        help=(
            "Prose explaining why the touched change has zero shared callers to "
            "enumerate (e.g. purely additive in a new module). Rejected when "
            "fix_path_helpers is already non-empty (contradictory)."
        ),
    )
    sp.set_defaults(func=cmd_record_no_shared_callers_justification)

    sp = subparsers.add_parser(
        "record-inbound-caller",
        help="Append a {helper_qn, caller_qn, file_line} record to inbound_callers.",
    )
    sp.add_argument("--helper-qn", required=True, dest="helper_qn")
    sp.add_argument("--caller-qn", required=True, dest="caller_qn")
    sp.add_argument("--file-line", required=True, dest="file_line")
    sp.set_defaults(func=cmd_record_inbound_caller)

    sp = subparsers.add_parser(
        "declare-caller-total",
        help=(
            "Declare the trace_path row count for a fix-path helper "
            "(plan 69 D1/WI-A). Check 9 requires the recorded "
            "inbound_callers row count to equal this declared total."
        ),
    )
    sp.add_argument(
        "--helper-qn",
        required=True,
        dest="helper_qn",
        help="Must match an existing fix_path_helpers[].qn entry.",
    )
    sp.add_argument(
        "--total",
        required=True,
        type=int,
        help=(
            "Integer >= 1. Counting rule (must match Phase 2.4c Step 2's "
            "prose): total = the number of inbound caller rows returned "
            "by trace_path(<helper-qn>, mode=calls, direction=inbound) at "
            "depth 1, INCLUDING the symptom site's own function when it "
            "appears as a caller."
        ),
    )
    sp.set_defaults(func=cmd_declare_caller_total)

    sp = subparsers.add_parser(
        "classify-caller-scope",
        help=(
            "Classify a recorded inbound_callers row with its user-facing "
            "surface + in/out scope + justification (plan 69 D5/WI-E). "
            "Append-then-classify: the (helper_qn, caller_qn) pair must "
            "already be recorded via record-inbound-caller."
        ),
    )
    sp.add_argument(
        "--helper-qn", required=True, dest="helper_qn",
        help="Must match an existing inbound_callers[].helper_qn.",
    )
    sp.add_argument(
        "--caller-qn", required=True, dest="caller_qn",
        help="Must match an existing inbound_callers[].caller_qn for the same row.",
    )
    sp.add_argument(
        "--surface",
        required=True,
        help=(
            "User-facing entry point (component/route/CLI command) this "
            "caller is reachable from, traced UP from the caller. The "
            "literal 'none' is legal for a caller with no user-facing "
            "surface (e.g. a background job)."
        ),
    )
    sp.add_argument(
        "--scope",
        required=True,
        choices=("in", "out"),
        help="Whether this caller is in-scope (affected) or out-of-scope for the change.",
    )
    sp.add_argument(
        "--justification",
        required=True,
        help="Prose explaining why this caller is in/out of scope for the change.",
    )
    sp.set_defaults(func=cmd_classify_caller_scope)

    sp = subparsers.add_parser(
        "record-dead-sibling",
        help="Append a {class_qn, method_qn, verified_via} record to dead_siblings.",
    )
    sp.add_argument("--class-qn", required=True, dest="class_qn")
    sp.add_argument("--method-qn", required=True, dest="method_qn")
    sp.add_argument(
        "--verified-via",
        required=True,
        dest="verified_via",
        choices=("trace_path", "search_code"),
    )
    sp.set_defaults(func=cmd_record_dead_sibling)

    sp = subparsers.add_parser(
        "record-consumer-chain",
        help="Append a {value, consumer_qn, file_line, role} record to consumer_chain.",
    )
    sp.add_argument("--value", required=True)
    sp.add_argument("--consumer-qn", required=True, dest="consumer_qn")
    sp.add_argument("--file-line", required=True, dest="file_line")
    sp.add_argument("--role", required=True)
    sp.set_defaults(func=cmd_record_consumer_chain)

    sp = subparsers.add_parser(
        "set-value-semantics",
        help="Upsert a {value, classification, evidence} record in value_semantics.",
    )
    sp.add_argument("--value", required=True)
    sp.add_argument(
        "--classification",
        required=True,
        choices=("preference", "invariant", "unclassified"),
    )
    sp.add_argument("--evidence", required=True)
    sp.add_argument(
        "--stable-across-calls",
        default=None,
        choices=("true", "false", "unknown"),
        dest="stable_across_calls",
        help=(
            "Stability axis for the value across the operation chain. "
            "REQUIRED when --classification invariant. "
            "Optional for other classifications (ignored if set)."
        ),
    )
    sp.set_defaults(func=cmd_set_value_semantics)

    sp = subparsers.add_parser(
        "record-value-production-site",
        help=(
            "Append a {value, file_line, is_stable} record to value_production_sites. "
            "Dedupes by (value, file_line) pair; multiple file_lines per value allowed."
        ),
    )
    sp.add_argument("--value", required=True, help="Symbol whose production site is being recorded.")
    sp.add_argument(
        "--file-line",
        required=True,
        dest="file_line",
        help="path:line where the value is randomized/rewritten (must not be (none)).",
    )
    sp.add_argument(
        "--is-stable",
        required=True,
        dest="is_stable",
        choices=("true", "false"),
        help="Whether the value is stable at this production site.",
    )
    sp.set_defaults(func=cmd_record_value_production_site)

    sp = subparsers.add_parser(
        "record-data-flow-chain",
        help=(
            "Record the data-flow chain from click handler to write-boundary call. "
            "Each intermediate must have a prior Finding row referencing it."
        ),
    )
    sp.add_argument(
        "--handler-qn",
        required=True,
        dest="handler_qn",
        help="Qualified name of the user-action handler (entry point).",
    )
    sp.add_argument(
        "--write-boundary-qn",
        required=True,
        dest="write_boundary_qn",
        help="Qualified name of the persistence / write-boundary call.",
    )
    sp.add_argument(
        "--intermediate-qns",
        required=True,
        dest="intermediate_qns",
        help=(
            "JSON array of intermediate transformer/adapter QNs between handler and "
            "write-boundary. May be empty list '[]' for direct handler→boundary calls."
        ),
    )
    sp.set_defaults(func=cmd_record_data_flow_chain)

    sp = subparsers.add_parser(
        "record-literal-archaeology",
        help=(
            "Record git-archaeology of a hardcoded literal that the recommended approach "
            "proposes to replace. Dedupes by (literal, file_line)."
        ),
    )
    sp.add_argument("--literal", required=True, help="Literal token as it appears in source (e.g. 'false', '0', \"''\").")
    sp.add_argument(
        "--file-line",
        required=True,
        dest="file_line",
        help="path:line where the literal lives (must not be (none)).",
    )
    sp.add_argument(
        "--introduced-by",
        required=True,
        dest="introduced_by",
        help="Commit SHA (7-40 hex chars) of the commit that introduced the literal.",
    )
    sp.add_argument(
        "--introduced-when",
        required=True,
        dest="introduced_when",
        help="ISO date YYYY-MM-DD when the introducing commit landed.",
    )
    sp.add_argument(
        "--commit-subject",
        required=True,
        dest="commit_subject",
        help="One-line subject from the introducing commit.",
    )
    sp.add_argument(
        "--intent",
        required=True,
        choices=("placeholder", "migrated", "deliberate", "forgotten", "inherited-refactor", "generated"),
        help="Classification of the literal's historical intent.",
    )
    sp.add_argument(
        "--use",
        required=True,
        choices=("fix-layer", "evidence"),
        help=(
            "Why this row is being recorded (plan 73 OQ-5): 'fix-layer' -- the "
            "literal IS the thing the recommended approach replaces (the "
            "original use case; requires an escalation cite in the summary "
            "for placeholder/forgotten/inherited-refactor intent). 'evidence' "
            "-- the literal's current value was cited as grounds for a scope "
            "call (dead/live, keep/delete); nothing is being replaced, so no "
            "escalation cite is required."
        ),
    )
    sp.add_argument(
        "--supply-changing-commits",
        default=None,
        dest="supply_changing_commits",
        help=(
            "OPTIONAL (plan 73 Phase 1): JSON array of {sha, subject} objects "
            "-- commits found by the widened `git log <introduced-by>..HEAD` "
            "sweep over this literal's file AND its already-enumerated "
            "inbound callers that changed HOW the value is SUPPLIED (a prop "
            "removed from a parent, a default relocated, a flag stripped "
            "from a caller). Omit this flag entirely when the sweep was not "
            "run for this literal -- that is a normal, unpenalized outcome, "
            "recorded as None end to end. Pass '[]' when the sweep ran and "
            "found nothing since --introduced-by. This is a SEARCH-STEP "
            "carrier, never a gate: no run fails because this flag was "
            "omitted or resolved empty."
        ),
    )
    sp.set_defaults(func=cmd_record_literal_archaeology)

    sp = subparsers.add_parser(
        "record-probe-script",
        help="Record a Tier-1.5 standalone probe script path + runtime + inlined-from sources.",
    )
    sp.add_argument("--script-path", required=True, dest="script_path")
    sp.add_argument(
        "--runtime",
        required=True,
        choices=("node", "python", "ruby", "deno", "bun"),
    )
    sp.add_argument(
        "--inlines-from",
        required=True,
        dest="inlines_from",
        help='JSON array of "path:line" tokens whose code the script inlines verbatim.',
    )
    sp.set_defaults(func=cmd_record_probe_script)

    # Step 5 — intake-interrogation gate.
    sp = subparsers.add_parser(
        "record-intake-classification",
        help=(
            "Persist a per-statement binary intake classification "
            "(requirement vs hypothesis) + the minimal_fix for that statement. "
            "Called once per statement in the verbatim prompt. "
            "Re-recording the same statement replaces its entry (idempotent)."
        ),
    )
    sp.add_argument(
        "--statement",
        required=True,
        help="The prompt statement being classified (verbatim or paraphrased).",
    )
    sp.add_argument(
        "--kind",
        required=True,
        choices=list(INTAKE_KIND_ENUM),
        help="Binary classification: 'requirement' or 'hypothesis'.",
    )
    sp.add_argument(
        "--minimal-fix",
        default=None,
        dest="minimal_fix",
        help=(
            "The simplest change that satisfies this statement's desired outcome. "
            "Optional; pass for requirement statements. For hypothesis statements "
            "the fix is 'verify first', not a code change."
        ),
    )
    sp.set_defaults(func=cmd_record_intake_classification)

    sp = subparsers.add_parser(
        "render-intake-echo",
        help=(
            "Render the intake echo-back block (requirements / hypotheses-to-verify / "
            "minimal scope) to stdout. Orchestrator copies verbatim to user before "
            "one confirmation. Proportional: no hypothesis section when none recorded."
        ),
    )
    sp.set_defaults(func=cmd_render_intake_echo)

    # Step 7 — append-outcome.
    sp = subparsers.add_parser(
        "append-outcome",
        help="Record the post-probe outcome into handoff.json (Step 7).",
    )
    sp.add_argument("--handoff-path", required=True, dest="handoff_path",
                    help="Path to the handoff.json file (e.g. specs/NNN-slug/research-handoff.json).")
    sp.add_argument(
        "--hypothesis-confirmed",
        required=True,
        dest="hypothesis_confirmed",
        choices=("primary", "runner_up", "none", "inconclusive"),
        help="Which hypothesis the evidence confirmed.",
    )
    sp.add_argument(
        "--evidence-source",
        required=True,
        dest="evidence_source",
        choices=("test-result", "llm-ui-session-log", "user-observation"),
        help="Source of the evidence.",
    )
    sp.add_argument("--evidence-cite", required=True, dest="evidence_cite",
                    help="Path, SHA, or verbatim observation that evidences the outcome.")
    sp.add_argument("--actual-fix-path", required=True, dest="actual_fix_path",
                    help="Path(s) actually modified by the fix.")
    sp.add_argument("--delta-from-recommendation", default=None, dest="delta_from_recommendation",
                    help="Optional: how the actual fix diverged from the recommendation.")
    sp.add_argument("--confirmed-commit-sha", default=None, dest="confirmed_commit_sha",
                    help="Optional: 7-40 char hex SHA of the commit that applied the fix.")
    sp.set_defaults(func=cmd_append_outcome)

    # Step 7 — check-outcome.
    sp = subparsers.add_parser(
        "check-outcome",
        help="Print 'unmarked' or 'marked: <details>' for a handoff.json outcome block.",
    )
    sp.add_argument("--handoff-path", required=True, dest="handoff_path",
                    help="Path to the handoff.json file.")
    sp.set_defaults(func=cmd_check_outcome)

    # Plan 68 Phase 1 — feature-dir allocation substrate (stateless verbs;
    # see _cmds_feature_alloc.py).
    sp = subparsers.add_parser(
        "allocate-feature-dir",
        help="Allocate a fresh specs/NNN-<slug>/ directory; print result as JSON.",
    )
    sp.add_argument("--slug", required=True, help="2-4 word lowercase kebab-case feature slug.")
    sp.add_argument(
        "--ticket", default=None,
        help=(
            "Optional ticket ID (e.g. 'PROJ-123', uppercase letters only). "
            "Required only when REQUIRE_TICKET is enabled in "
            "project-config.json -- see _shared.feature_alloc.normalize_ticket "
            "for the format and _shared.feature_alloc.read_require_ticket for "
            "the config key this verb reads."
        ),
    )
    sp.set_defaults(func=cmd_allocate_feature_dir)

    sp = subparsers.add_parser(
        "render-branch-command",
        help="Print the branch-decision line (checkout command or informational comment).",
    )
    sp.add_argument(
        "--slug", required=True,
        help=(
            "Feature slug for the branch name -- the fallback identity "
            "used when no --ticket is supplied (91-FEATURE-DIR-IDENTITY-"
            "AND-PROVENANCE-PLAN.md D5). Consumed only by the 'create' arm "
            "(current branch == default branch) -- CLI-required "
            "regardless, because plan 68 D1's finalize ordering guarantees "
            "allocation always precedes this call, so the caller always has "
            "it on hand."
        ),
    )
    sp.add_argument(
        "--ticket", default=None,
        help=(
            "Optional ticket ID (e.g. 'PROJ-123'), taking priority over "
            "--slug on the 'create' arm (91-FEATURE-DIR-IDENTITY-AND-"
            "PROVENANCE-PLAN.md D5: the branch is spec/<ticket> when one "
            "is given, else spec/<slug>). Pass the SAME normalized value "
            "allocate-feature-dir's own --ticket already validated and "
            "echoed back in its 'ticket' JSON key -- this verb performs "
            "no format validation of its own (decide_branch_action takes "
            "the value verbatim)."
        ),
    )
    sp.add_argument(
        "--number",
        default=None,
        help=(
            "ACCEPTED BUT IGNORED (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-"
            "PLAN.md Phase 3, D5/D6): a NEW branch is never named "
            "spec/<NNN>-<slug> any more, so this value is never read -- "
            "see _shared.feature_alloc.decide_branch_action for the "
            "ticket-or-slug rule that replaced it. Kept only so "
            "src/commands/research/main.md's existing render-branch-command "
            "call (which still passes --number) does not break; no longer "
            "required."
        ),
    )
    sp.add_argument("--current-branch", required=True, dest="current_branch")
    sp.add_argument("--default-branch", required=True, dest="default_branch")
    sp.set_defaults(func=cmd_render_branch_command)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    if args.install_root is None:
        args.install_root = str(Path(args.devforge_dir).resolve().parent)
    return args.func(args)
