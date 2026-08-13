"""Tests for src/devforge/lib/_research/handoff_schema.py.

Covers all 34 test cases enumerated in RESEARCH-HANDOFF-PLAN.md Step 1 Verify block.
Grouped into 6 test classes mirroring the plan's categorisation:
  TestBase (6), TestV2DataFlow (5), TestV2Stability (5), TestV3LiteralArchaeology (8), TestV3CallShape (10).

(Plan's "V2" split is into TestV2DataFlow + TestV2Stability for 5+5=10 total; plan's "V3" split is
into TestV3LiteralArchaeology + TestV3CallShape for 8+10=18 total; total = 6+10+18 = 34.)

Stdlib only. No third-party dependencies.
"""

import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Load via importlib from an explicit path under a UNIQUE module name: five
# source files share the name "handoff_schema.py" across subpackages, so a bare
# `import handoff_schema` would let pytest-session sys.modules caching serve a
# different subpackage's schema to a later test. (Both schema modules import
# stdlib only, so no sys.path entry is needed.)
# ---------------------------------------------------------------------------

import importlib.util

_HERE = Path(__file__).resolve().parent
_RESEARCH_DIR = _HERE.parent.parent / "src" / "devforge" / "lib" / "_research"

_spec = importlib.util.spec_from_file_location(
    "research_handoff_schema",  # unique name — never "handoff_schema"; avoids sys.modules collision
    _RESEARCH_DIR / "handoff_schema.py",
)
hs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hs)


# ---------------------------------------------------------------------------
# Builder helpers — each returns a valid default; tests override one field.
# ---------------------------------------------------------------------------


def _intent(symptom="User sees wrong data on screen", desired="Correct data shown", scope="file-local"):
    return hs.Intent(
        symptom_summary=symptom,
        desired_summary=desired,
        scope=scope,
    )


def _constraint(kind="follow", content="Follow existing patterns", **kwargs):
    return hs.Constraint(kind=kind, content=content, **kwargs)


def _affected_area(area="ui", files=None, impact="visible to user"):
    if files is None:
        files = ["src/foo.vue:10"]
    return hs.AffectedArea(area=area, files=list(files), impact=impact)


def _affected_area_py(area="service", files=None, impact="internal"):
    if files is None:
        files = ["src/service.py:42"]
    return hs.AffectedArea(area=area, files=list(files), impact=impact)


def _risk(risk_text="Regression", likelihood="Low", impact="Low", mitigation="Tests cover it"):
    return hs.Risk(risk=risk_text, likelihood=likelihood, impact=impact, mitigation=mitigation)


def _open_question(question="Is this blocking?", blocking=False):
    return hs.OpenQuestion(question=question, blocking=blocking)


def _data_flow_chain(
    handler_qn="MyComponent.handleClick",
    write_boundary_qn="ApiService.save",
    intermediate_qns=None,
    trace_mode="calls",
):
    if intermediate_qns is None:
        intermediate_qns = []
    return hs.DataFlowChain(
        handler_qn=handler_qn,
        write_boundary_qn=write_boundary_qn,
        intermediate_qns=intermediate_qns,
        trace_mode=trace_mode,
    )


def _value_semantics(value="bqItemId", classification="preference", stable_across_calls=None):
    return hs.ValueSemantics(
        value=value,
        classification=classification,
        stable_across_calls=stable_across_calls,
    )


def _value_production_site(value="bqItemId", file_line="src/adapter.ts:5", is_stable=True):
    return hs.ValueProductionSite(value=value, file_line=file_line, is_stable=is_stable)


def _literal_archaeology(
    literal="false",
    file_line="src/foo.vue:42",
    introduced_by="bd47a12",
    introduced_when="2023-12-12",
    commit_subject="add gate",
    intent="placeholder",
    use="fix-layer",
):
    return hs.LiteralArchaeology(
        literal=literal,
        file_line=file_line,
        introduced_by=introduced_by,
        introduced_when=introduced_when,
        commit_subject=commit_subject,
        intent=intent,
        use=use,
    )


def _complexity(changes="Low", risk="Low", verify_cost="Low"):
    return hs.Complexity(changes=changes, risk=risk, verify_cost=verify_cost)


def _spec_seeds(
    affected_areas=None,
    constraints=None,
    risks=None,
    open_questions=None,
    value_semantics=None,
    value_production_sites=None,
    literal_archaeology=None,
    data_flow_chain=None,
    spec_type_hint="bug_fix",
    design_anchor=None,
):
    return hs.SpecSeeds(
        spec_type_hint=spec_type_hint,
        constraints=constraints if constraints is not None else [_constraint()],
        affected_areas=affected_areas if affected_areas is not None else [_affected_area()],
        risks=risks if risks is not None else [_risk()],
        open_questions=open_questions if open_questions is not None else [_open_question()],
        design_anchor=design_anchor if design_anchor is not None else hs.DesignAnchor(),
        value_semantics=value_semantics if value_semantics is not None else [],
        value_production_sites=value_production_sites if value_production_sites is not None else [],
        literal_archaeology=literal_archaeology if literal_archaeology is not None else [],
        data_flow_chain=data_flow_chain,
    )


def _cited_pattern(qn="some.QualifiedName", file_line="src/example.ts:10"):
    return hs.CitedPattern(qn=qn, file_line=file_line)


def _alternative(id="alt_a", summary="Alternative A", rejected_reason="Too complex"):
    return hs.Alternative(id=id, summary=summary, rejected_reason=rejected_reason)


def _fix_path_helper(qn="config.load", file_line="src/config.py:42"):
    return hs.FixPathHelper(qn=qn, file_line=file_line)


def _inbound_caller(helper_qn="config.load", caller_qn="main.startup", file_line="src/main.py:15",
                     surface="", scope="", justification=""):
    return hs.InboundCaller(
        helper_qn=helper_qn, caller_qn=caller_qn, file_line=file_line,
        surface=surface, scope=scope, justification=justification,
    )


def _caller_enumeration(
    fix_path_helpers=None,
    inbound_callers=None,
    no_shared_callers_justification=None,
):
    return hs.CallerEnumeration(
        fix_path_helpers=fix_path_helpers if fix_path_helpers is not None else [],
        inbound_callers=inbound_callers if inbound_callers is not None else [],
        no_shared_callers_justification=no_shared_callers_justification,
    )


def _plan_seeds(
    recommended_approach_id="fix_literal",
    recommended_approach_summary="Fix the bug by updating the affected logic",
    layer_destination="ui",
    layer_justification="The fix is scoped to the presentation layer",
    complexity=None,
    cited_canonical_patterns=None,
    alternatives_considered=None,
    proposed_call_shape=None,
    correctness_vetted=False,
    caller_enumeration=None,
):
    return hs.PlanSeeds(
        recommended_approach_id=recommended_approach_id,
        recommended_approach_summary=recommended_approach_summary,
        layer_destination=layer_destination,
        layer_justification=layer_justification,
        complexity=complexity if complexity is not None else _complexity(),
        cited_canonical_patterns=cited_canonical_patterns if cited_canonical_patterns is not None else [],
        alternatives_considered=alternatives_considered if alternatives_considered is not None else [],
        proposed_call_shape=proposed_call_shape,
        correctness_vetted=correctness_vetted,
        caller_enumeration=caller_enumeration if caller_enumeration is not None else _caller_enumeration(),
    )


def _feasibility_check(
    data_shape_only=False,
    auth_required=False,
    network_dependent=False,
    timing_dependent=False,
    is_test_code=False,
):
    return hs.FeasibilityCheck(
        data_shape_only=data_shape_only,
        auth_required=auth_required,
        network_dependent=network_dependent,
        timing_dependent=timing_dependent,
        is_test_code=is_test_code,
    )


def _discriminator(
    primary_confirms_if="Test passes with fix applied",
    runner_up_confirms_if="Alternate hypothesis test passes",
    both_disproved_if="Neither test passes",
    production_site_check=None,
):
    return hs.Discriminator(
        primary_confirms_if=primary_confirms_if,
        runner_up_confirms_if=runner_up_confirms_if,
        both_disproved_if=both_disproved_if,
        production_site_check=production_site_check,
    )


def _probe(
    tier="3",
    actor="user",
    test_framework=None,
    test_path=None,
    script_path=None,
    is_first_test_for_file=False,
    discriminator=None,
    feasibility_check=None,
):
    return hs.Probe(
        tier=tier,
        actor=actor,
        discriminator=discriminator if discriminator is not None else _discriminator(),
        feasibility_check=feasibility_check if feasibility_check is not None else _feasibility_check(),
        test_framework=test_framework,
        test_path=test_path,
        script_path=script_path,
        is_first_test_for_file=is_first_test_for_file,
    )


def _outcome(
    hypothesis_confirmed="primary",
    evidence_source="test-result",
    evidence_cite="tests/test_foo.spec.ts line 42",
    actual_fix_path="src/foo.vue:290",
    delta_from_recommendation=None,
    confirmed_date="2026-05-19",
    confirmed_commit_sha=None,
    confidence_grade="HIGH",
):
    return hs.Outcome(
        hypothesis_confirmed=hypothesis_confirmed,
        evidence_source=evidence_source,
        evidence_cite=evidence_cite,
        actual_fix_path=actual_fix_path,
        delta_from_recommendation=delta_from_recommendation,
        confirmed_date=confirmed_date,
        confirmed_commit_sha=confirmed_commit_sha,
        confidence_grade=confidence_grade,
    )


def _downstream_links():
    return hs.DownstreamLinks()


def _evidence_lanes(static_graph=False, text_search=False, runtime_probe=False, history=False):
    return hs.EvidenceLanes(
        static_graph=static_graph,
        text_search=text_search,
        runtime_probe=runtime_probe,
        history=history,
    )


def _handoff(
    mode="bug",
    spec_seeds=None,
    plan_seeds=None,
    probe=None,
    outcome=None,
    **overrides,
):
    """Build a fully-valid Handoff with mode=bug and vue-file affected areas.

    Individual tests mutate/replace fields to trigger rejection.
    By default uses a data_flow_chain (required for bug+presentation-layer).
    """
    if spec_seeds is None:
        spec_seeds = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
        )
    if plan_seeds is None:
        plan_seeds = _plan_seeds()
    if probe is None:
        probe = _probe()

    return hs.Handoff(
        schema_version=overrides.get("schema_version", hs.SCHEMA_VERSION),
        research_path=overrides.get("research_path", "research/2026-05-19-test.md"),
        research_completed_at=overrides.get("research_completed_at", "2026-05-19T10:00:00Z"),
        mode=mode,
        intent=overrides.get("intent", _intent()),
        spec_seeds=spec_seeds,
        plan_seeds=plan_seeds,
        probe=probe,
        downstream_links=overrides.get("downstream_links", _downstream_links()),
        outcome=outcome,
        evidence_lanes=overrides.get("evidence_lanes", _evidence_lanes()),
    )


# ---------------------------------------------------------------------------
# TestBase — 6 test cases.
# ---------------------------------------------------------------------------


class TestBase(unittest.TestCase):
    """Base schema tests: happy path + core rejection cases."""

    def test_valid_handoff_full_bug(self):
        """Construct a complete Handoff with mode=bug, all required fields. No exception."""
        # Build with primary+runner_up hypothesis support (discriminator fields).
        disc = _discriminator(
            primary_confirms_if="Unit test confirms fix corrects output",
            runner_up_confirms_if="Alternate test shows race condition",
            both_disproved_if="Both tests fail — wrong hypothesis",
        )
        p = _probe(tier="3", actor="user", discriminator=disc)
        h = _handoff(mode="bug", probe=p)
        self.assertIsInstance(h, hs.Handoff)
        self.assertEqual(h.mode, "bug")
        self.assertIsNone(h.outcome)

    def test_reject_kind_use_constraint(self):
        """Constraint(kind='use', ...) raises ValueError mentioning all 3 replacement kinds."""
        with self.assertRaises(ValueError) as ctx:
            _constraint(kind="use", content="Use this library")
        msg = str(ctx.exception)
        self.assertIn("use", msg.lower())
        # Check that all 3 replacement kinds are mentioned.
        self.assertIn("nfr", msg)
        self.assertIn("constitution_anchor", msg)
        self.assertIn("external_system", msg)

    def test_reject_tier_1_when_is_test_code(self):
        """Probe with feasibility_check.is_test_code=True and tier='1' raises ValueError."""
        fc = _feasibility_check(is_test_code=True)
        with self.assertRaises(ValueError) as ctx:
            _probe(
                tier="1",
                test_framework="pytest",
                test_path="tests/test_foo.py",
                feasibility_check=fc,
            )
        self.assertIn("test_code", str(ctx.exception))

    def test_reject_tier_1_without_test_framework(self):
        """tier='1' with test_framework=None raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _probe(tier="1", test_framework=None, test_path="tests/test_foo.py")
        self.assertIn("test_framework", str(ctx.exception))

    def test_reject_tier_1_5_with_test_framework(self):
        """tier='1.5' with test_framework set raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _probe(
                tier="1.5",
                test_framework="vitest",
                script_path="research/001/probe.sh",
            )
        self.assertIn("test_framework", str(ctx.exception))

    def test_valid_outcome_appended(self):
        """Start with outcome=None Handoff, build Outcome, attach, verify grade computed."""
        h = _handoff(mode="bug")
        self.assertIsNone(h.outcome)

        # Build a tier-3 user-observation outcome — expected grade is LOW.
        o = _outcome(
            hypothesis_confirmed="primary",
            evidence_source="user-observation",
            confidence_grade="LOW",
        )
        # Build new handoff with outcome attached (probe tier=3).
        h2 = _handoff(mode="bug", outcome=o)
        self.assertIsNotNone(h2.outcome)
        self.assertEqual(h2.outcome.confidence_grade, "LOW")


# ---------------------------------------------------------------------------
# TestV2DataFlow — 5 test cases.
# ---------------------------------------------------------------------------


class TestV2DataFlow(unittest.TestCase):
    """V2 Patch 6 — data_flow_chain field validation."""

    def test_valid_handoff_with_data_flow_chain(self):
        """Populated DataFlowChain with all fields accepts without error."""
        chain = _data_flow_chain(
            handler_qn="InvoiceSummaryPanel.handleSubmit",
            write_boundary_qn="OrderRepo.save",
            intermediate_qns=["OrderService.process", "OrderMapper.toEntity"],
            trace_mode="data_flow",
        )
        ss = _spec_seeds(affected_areas=[_affected_area()], data_flow_chain=chain)
        h = _handoff(spec_seeds=ss)
        self.assertEqual(h.spec_seeds.data_flow_chain.trace_mode, "data_flow")

    def test_require_data_flow_chain_when_bug_presentation_layer(self):
        """mode=bug + .vue file affected area + data_flow_chain=None → ValueError."""
        ss = _spec_seeds(
            affected_areas=[_affected_area(files=["src/components/Order.vue:10"])],
            data_flow_chain=None,
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(mode="bug", spec_seeds=ss)
        self.assertIn("data_flow_chain", str(ctx.exception))

    def test_accept_null_data_flow_chain_when_domain_layer_symptom(self):
        """mode=bug + .py/.go files only → data_flow_chain=None accepted."""
        ss = _spec_seeds(
            affected_areas=[
                _affected_area_py(files=["src/service.py:42"]),
                _affected_area_py(files=["src/repo.go:10"]),
            ],
            data_flow_chain=None,
        )
        h = _handoff(mode="bug", spec_seeds=ss)
        self.assertIsNone(h.spec_seeds.data_flow_chain)

    def test_reject_invalid_trace_mode_enum(self):
        """trace_mode='foo' → ValueError at DataFlowChain construction."""
        with self.assertRaises(ValueError) as ctx:
            _data_flow_chain(trace_mode="foo")
        self.assertIn("trace_mode", str(ctx.exception))

    def test_require_production_site_check_when_unstable_value(self):
        """value_production_sites has is_stable=False row + production_site_check=None → ValueError."""
        vps = _value_production_site(value="uid", file_line="src/adapter.ts:5", is_stable=False)
        vs = _value_semantics(value="uid", classification="invariant", stable_across_calls="false")
        disc = _discriminator(production_site_check=None)  # None → should reject
        p = _probe(discriminator=disc)
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            value_semantics=[vs],
            value_production_sites=[vps],
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(spec_seeds=ss, probe=p)
        self.assertIn("production_site_check", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestV2Stability — 5 test cases.
# ---------------------------------------------------------------------------


class TestV2Stability(unittest.TestCase):
    """V2 Patch 7 — value_semantics stability axis + value_production_sites validation."""

    def test_require_stable_across_calls_when_invariant_presentation_layer(self):
        """value_semantics invariant + .tsx affected area + stable_across_calls=None → ValueError."""
        vs = _value_semantics(value="itemId", classification="invariant", stable_across_calls=None)
        ss = _spec_seeds(
            affected_areas=[_affected_area(files=["src/components/Item.tsx:30"])],
            data_flow_chain=_data_flow_chain(),
            value_semantics=[vs],
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(spec_seeds=ss)
        self.assertIn("stable_across_calls", str(ctx.exception))

    def test_accept_unknown_stable_when_domain_layer_symptom(self):
        """value_semantics invariant + .py area only + stable_across_calls=None → accepted."""
        vs = _value_semantics(value="orderId", classification="invariant", stable_across_calls=None)
        ss = _spec_seeds(
            affected_areas=[_affected_area_py(files=["src/order_service.py:55"])],
            data_flow_chain=None,
            value_semantics=[vs],
        )
        h = _handoff(mode="bug", spec_seeds=ss)
        self.assertEqual(h.spec_seeds.value_semantics[0].stable_across_calls, None)

    def test_require_production_site_when_stable_false(self):
        """value_semantics stable_across_calls='false' with no matching production site → ValueError."""
        vs = _value_semantics(value="uid", classification="invariant", stable_across_calls="false")
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            value_semantics=[vs],
            value_production_sites=[],  # no matching site
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(spec_seeds=ss)
        self.assertIn("ValueProductionSite", str(ctx.exception))

    def test_append_only_distinct_file_line_dedupe_production_sites(self):
        """Two value_production_sites rows with same (value, file_line) → ValueError."""
        vps1 = _value_production_site(value="uid", file_line="src/adapter.ts:5", is_stable=True)
        vps2 = _value_production_site(value="uid", file_line="src/adapter.ts:5", is_stable=False)
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(value_production_sites=[vps1, vps2])
        self.assertIn("duplicate", str(ctx.exception))

    def test_require_test_result_evidence_for_high_confidence_when_production_site_path(self):
        """Outcome with production_site_check set + primary confirmed + user-observation + HIGH → ValueError."""
        disc = _discriminator(production_site_check="src/adapter.ts:5 — check Math.random rewriter")
        p = _probe(tier="3", discriminator=disc)
        # production_site_check present + primary + non-test-result → should be MEDIUM, not HIGH
        o = _outcome(
            hypothesis_confirmed="primary",
            evidence_source="user-observation",
            confidence_grade="HIGH",  # wrong — should be MEDIUM
        )
        vps = _value_production_site(value="uid", file_line="src/adapter.ts:5", is_stable=False)
        vs = _value_semantics(value="uid", classification="invariant", stable_across_calls="false")
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            value_semantics=[vs],
            value_production_sites=[vps],
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(spec_seeds=ss, probe=p, outcome=o)
        self.assertIn("confidence_grade", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestV3LiteralArchaeology — 8 test cases.
# ---------------------------------------------------------------------------


class TestV3LiteralArchaeology(unittest.TestCase):
    """V3 Patch 8 — literal_archaeology field validation."""

    def test_valid_handoff_with_literal_archaeology(self):
        """Full literal_archaeology row with intent=placeholder, valid SHA, valid date accepts.

        The summary intentionally avoids the literal-replacement regex trigger (uses 'using'
        rather than 'with'/'to'), so proposed_call_shape is not required for this valid-path test.
        """
        la = _literal_archaeology(
            literal="false",
            file_line="src/InvoiceSummaryPanel.vue:290",
            introduced_by="bd47a12e5f6a9c3",
            introduced_when="2023-12-12",
            commit_subject="TICKET-2044 extract loadData wrapper",
            intent="placeholder",
        )
        # For placeholder intent, escalation required in summary.
        ps = _plan_seeds(
            recommended_approach_summary="Replace literal using wrapper default parameter",
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[la],
        )
        h = _handoff(spec_seeds=ss, plan_seeds=ps)
        self.assertEqual(h.spec_seeds.literal_archaeology[0].intent, "placeholder")

    def test_require_literal_archaeology_when_bug_with_literal_replacement(self):
        """mode=bug + 'Replace `false` with `isExternal`' summary + empty literal_archaeology → ValueError.

        Bug-mode path is unchanged by plan 73 D1 (which widened the check to
        also fire outside bug mode — see
        test_require_literal_archaeology_when_enhancement_with_literal_replacement
        below).
        """
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `isExternal` in loadData call"
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[],  # empty — should be rejected
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps)
        self.assertIn("literal_archaeology", str(ctx.exception))

    def test_require_literal_archaeology_when_enhancement_with_literal_replacement(self):
        """mode=feature_addition (enhancement) + literal-replacement summary +
        empty literal_archaeology → ValueError.

        Plan 73 D1 widened PlanSeeds._validate_cross_field's literal_archaeology
        presence check from `mode == "bug" and is_literal_replacement` to
        `is_literal_replacement` alone — the finalize-handoff chokepoint mirror
        of the mode-decoupled verify check 17. "feature_addition" is the
        handoff-schema mode _handoff_build.py maps research_helper's
        "enhancement" onto (MODE_TRANSLATE, _handoff_build.py:63).
        """
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `isExternal` in loadData call"
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            literal_archaeology=[],  # empty — should be rejected
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(mode="feature_addition", spec_seeds=ss, plan_seeds=ps)
        self.assertIn("literal_archaeology", str(ctx.exception))

    def test_literal_archaeology_present_passes_in_enhancement_mode(self):
        """mode=feature_addition + literal-replacement summary + a matching
        literal_archaeology row → no ValueError (back-compat proof: the
        widened check accepts a satisfied row exactly like bug mode does).
        """
        la = _literal_archaeology(
            literal="false",
            file_line="src/foo.vue:10",
            intent="deliberate",
        )
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `isExternal` in loadData call"
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            literal_archaeology=[la],
        )
        h = _handoff(mode="feature_addition", spec_seeds=ss, plan_seeds=ps)
        self.assertEqual(h.mode, "feature_addition")

    def test_reject_invalid_intent_enum_value(self):
        """intent='random_word' raises ValueError at LiteralArchaeology construction."""
        with self.assertRaises(ValueError) as ctx:
            _literal_archaeology(intent="random_word")
        self.assertIn("intent", str(ctx.exception))

    def test_reject_short_commit_sha_introduced_by(self):
        """introduced_by='abc' (< 7 chars) raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _literal_archaeology(introduced_by="abc")
        self.assertIn("introduced_by", str(ctx.exception))

    def test_reject_non_hex_commit_sha_introduced_by(self):
        """introduced_by='zzzzzzz' (non-hex) raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _literal_archaeology(introduced_by="zzzzzzz")
        self.assertIn("introduced_by", str(ctx.exception))

    def test_reject_non_iso_date_introduced_when(self):
        """introduced_when='not-a-date' raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _literal_archaeology(introduced_when="not-a-date")
        self.assertIn("introduced_when", str(ctx.exception))

    def test_reject_none_sentinel_file_line_in_archaeology(self):
        """file_line='(none)' raises ValueError at LiteralArchaeology construction."""
        with self.assertRaises(ValueError) as ctx:
            _literal_archaeology(file_line="(none)")
        self.assertIn("(none)", str(ctx.exception))

    def test_distinct_literal_file_line_dedupe(self):
        """Two archaeology rows with same (literal, file_line) → ValueError."""
        la1 = _literal_archaeology(literal="false", file_line="src/foo.vue:42", intent="placeholder")
        la2 = _literal_archaeology(literal="false", file_line="src/foo.vue:42", intent="deliberate")
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(literal_archaeology=[la1, la2])
        self.assertIn("duplicate", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestV3CallShape — 10 test cases.
# ---------------------------------------------------------------------------


class TestV3CallShape(unittest.TestCase):
    """V3 Patch 9 — proposed_call_shape parsing + escalation cite rules."""

    def test_require_proposed_call_shape_when_single_layer_bug(self):
        """mode=bug + 'single-layer' in layer_justification + proposed_call_shape=None → ValueError."""
        ps = _plan_seeds(
            layer_justification="This is a single-layer fix confined to the vue component",
            proposed_call_shape=None,
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps)
        self.assertIn("proposed_call_shape", str(ctx.exception))

    def test_require_proposed_call_shape_when_literal_replacement(self):
        """mode=bug + recommended_approach_summary matches literal-replacement regex + proposed_call_shape=None → ValueError."""
        # Also need literal_archaeology since literal-replacement is detected.
        la = _literal_archaeology(intent="deliberate")
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `isExternalUser.value`",
            proposed_call_shape=None,  # missing
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[la],
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps)
        self.assertIn("proposed_call_shape", str(ctx.exception))

    def test_reject_argument_duplication_in_proposed_call_shape(self):
        """proposed_call_shape='loadData(isExternalUser.value, isExternalUser.value)' → ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _plan_seeds(
                proposed_call_shape="loadData(isExternalUser.value, isExternalUser.value)"
            )
        msg = str(ctx.exception)
        self.assertIn("isExternalUser", msg)
        self.assertIn("duplicate", msg)

    def test_accept_optional_chaining_identifier_in_call_shape(self):
        """proposed_call_shape='fetch(a?.b?.c)' — parser accepts the optional-chain identifier."""
        ps = _plan_seeds(proposed_call_shape="fetch(a?.b?.c)")
        self.assertFalse(ps._proposed_call_shape_parse_failed)

    def test_fail_soft_on_nested_call_shape(self):
        """proposed_call_shape='wrap(inner(x))' — fails first-gate → fail-soft accept, parse_failed flag set."""
        ps = _plan_seeds(proposed_call_shape="wrap(inner(x))")
        self.assertTrue(ps._proposed_call_shape_parse_failed)

    def test_require_escalation_cite_when_intent_inherited_refactor(self):
        """intent=inherited-refactor + summary lacks escalation tokens → ValueError."""
        la = _literal_archaeology(intent="inherited-refactor")
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `isExternal.value` at call site",
            proposed_call_shape="loadData(isExternal.value)",
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[la],
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps)
        msg = str(ctx.exception)
        self.assertIn("escalation", msg)
        self.assertIn("inherited-refactor", msg)

    def test_require_escalation_cite_when_intent_forgotten(self):
        """intent=forgotten + summary lacks escalation tokens → ValueError."""
        la = _literal_archaeology(intent="forgotten")
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `isExternal.value` at call site",
            proposed_call_shape="loadData(isExternal.value)",
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[la],
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps)
        msg = str(ctx.exception)
        self.assertIn("escalation", msg)

    def test_require_escalation_cite_when_intent_placeholder(self):
        """intent=placeholder + summary lacks escalation tokens → ValueError."""
        la = _literal_archaeology(intent="placeholder")
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `isExternal.value` at call site",
            proposed_call_shape="loadData(isExternal.value)",
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[la],
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps)
        msg = str(ctx.exception)
        self.assertIn("escalation", msg)

    def test_accept_direct_replacement_when_intent_deliberate(self):
        """intent=deliberate + summary with no escalation tokens → accepted (no escalation required)."""
        la = _literal_archaeology(intent="deliberate")
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `true` — the fix is intentional policy change",
            proposed_call_shape="loadData(true)",
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[la],
        )
        # Should not raise — deliberate intent does not require escalation cite.
        h = _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps)
        self.assertIsNotNone(h)

    def test_accept_generated_intent_without_escalation_check(self):
        """intent=generated + summary lacks escalation tokens → accepted."""
        la = _literal_archaeology(intent="generated")
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `true` in scaffold fixture",
            proposed_call_shape="setup(true)",
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[la],
        )
        h = _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps)
        self.assertIsNotNone(h)

    def test_accept_migrated_intent_without_escalation_check(self):
        """intent=migrated + summary with literal-replacement pattern but NO escalation tokens → accepted.

        _INTENTS_REQUIRING_ESCALATION correctly excludes 'migrated'; this test verifies
        that exclusion. The summary uses 'Replace ... with ...' to trigger the
        literal-replacement detector (so proposed_call_shape is required), but contains
        no 'default'/'wrapper'/'caller'/'escalat' substrings.
        """
        la = _literal_archaeology(intent="migrated")
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `isLegacy` at migration boundary",
            proposed_call_shape="loadData(isLegacy)",
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[la],
        )
        h = _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps)
        self.assertIsNotNone(h)


# ---------------------------------------------------------------------------
# Plan 73 OQ-5 — `use` discriminator + schema_version-scoped presence gate.
# ---------------------------------------------------------------------------


class TestV3LiteralArchaeologyUse(unittest.TestCase):
    """Plan 73 OQ-5: LiteralArchaeology.use discriminator + Finding-1/Finding-2 fixes."""

    def test_use_defaults_to_fix_layer_when_omitted(self):
        """Constructing LiteralArchaeology without `use=` defaults to 'fix-layer'."""
        la = hs.LiteralArchaeology(
            literal="false",
            file_line="src/foo.vue:42",
            introduced_by="bd47a12",
            introduced_when="2023-12-12",
            commit_subject="add gate",
            intent="placeholder",
        )
        self.assertEqual(la.use, "fix-layer")

    def test_reject_invalid_use_enum_value(self):
        """use='bogus' raises ValueError mentioning 'use'."""
        with self.assertRaises(ValueError) as ctx:
            _literal_archaeology(use="bogus")
        self.assertIn("use", str(ctx.exception))

    def test_evidence_use_row_exempt_from_escalation_cite(self):
        """Finding 1 fix: use='evidence' + intent='inherited-refactor' + a deletion-shaped
        summary (no escalation tokens) → accepted, no ValueError.

        Mirrors test_require_escalation_cite_when_intent_inherited_refactor but with
        use='evidence' instead of the default 'fix-layer' — the escalation-cite loop
        must not fire for an evidence-use row, since nothing is being replaced.
        """
        la = _literal_archaeology(intent="inherited-refactor", use="evidence")
        ps = _plan_seeds(
            recommended_approach_summary="Swap the literal `true` with removing the dead branch entirely",
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[la],
        )
        h = _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps)
        self.assertIsNotNone(h)
        self.assertEqual(h.spec_seeds.literal_archaeology[0].use, "evidence")

    def test_fix_layer_use_row_still_requires_escalation_cite(self):
        """The fix-layer counterpart of the above still DEMANDS escalation prose —
        Finding 1's fix must not gut the validator for the case it was built for.
        """
        la = _literal_archaeology(intent="inherited-refactor", use="fix-layer")
        ps = _plan_seeds(
            recommended_approach_summary="Swap the literal `true` with removing the dead branch entirely",
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[la],
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps)
        msg = str(ctx.exception)
        self.assertIn("escalation", msg)
        self.assertIn("inherited-refactor", msg)

    def test_presence_gate_exempts_old_schema_version_enhancement_empty_archaeology(self):
        """Finding 2 fix: schema_version='1.1' (predates plan 73 D1) + mode='feature_addition'
        + a replacement-shaped summary + EMPTY literal_archaeology → accepted, no ValueError.

        This is exactly Finding 2's shape: a handoff.json legally written before plan 73
        D1 shipped (presence was bug-mode-gated then) must not newly fail reconstruction
        after the code upgrades and re-validates it (e.g. specify's import-handoff, via
        _dict_to_dataclass, re-runs Handoff.__post_init__ on already-persisted JSON).
        """
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `isExternal` in loadData call"
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            literal_archaeology=[],
        )
        h = _handoff(mode="feature_addition", spec_seeds=ss, plan_seeds=ps, schema_version="1.1")
        self.assertIsNotNone(h)
        self.assertEqual(h.schema_version, "1.1")

    def test_presence_gate_still_fires_for_current_schema_version_enhancement_empty_archaeology(self):
        """Same shape at the CURRENT (post-plan-73) schema_version → still raises.

        Proves the Finding-2 fix does not weaken the gate for a NEWLY-written handoff —
        only a handoff stamped with a version predating plan 73 D1 is exempted.
        """
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `isExternal` in loadData call"
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            literal_archaeology=[],
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(mode="feature_addition", spec_seeds=ss, plan_seeds=ps, schema_version=hs.SCHEMA_VERSION)
        self.assertIn("literal_archaeology", str(ctx.exception))

    def test_presence_gate_old_schema_version_bug_mode_empty_archaeology_still_rejects(self):
        """schema_version='1.1' + mode='bug' + empty archaeology + replacement summary →
        still raises — byte-identical to pre-plan-73 bug-mode behavior. The schema_version
        carve-out only relaxes the mode-independent WIDENING; it does not touch the
        original bug-mode requirement that existed before plan 73.
        """
        ps = _plan_seeds(
            recommended_approach_summary="Replace `false` with `isExternal` in loadData call"
        )
        ss = _spec_seeds(
            affected_areas=[_affected_area()],
            data_flow_chain=_data_flow_chain(),
            literal_archaeology=[],
        )
        with self.assertRaises(ValueError) as ctx:
            _handoff(mode="bug", spec_seeds=ss, plan_seeds=ps, schema_version="1.1")
        self.assertIn("literal_archaeology", str(ctx.exception))


# ---------------------------------------------------------------------------
# Additional edge cases discovered during implementation.
# ---------------------------------------------------------------------------


class TestEdgeCases(unittest.TestCase):
    """Edge cases not listed in the plan but required for completeness."""

    def test_schema_version_mismatch_rejects(self):
        """schema_version outside accepted set raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _handoff(schema_version="2.0")
        self.assertIn("schema_version", str(ctx.exception))

    def test_nfr_constraint_requires_quantifier(self):
        """kind='nfr' without quantifier raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _constraint(kind="nfr", content="Performance NFR")
        self.assertIn("quantifier", str(ctx.exception))

    def test_nfr_constraint_with_quantifier_accepts(self):
        """kind='nfr' with quantifier set accepts."""
        c = _constraint(kind="nfr", content="Response time NFR", quantifier="p99 < 200ms")
        self.assertEqual(c.kind, "nfr")

    def test_constitution_anchor_requires_constitution_ref(self):
        """kind='constitution_anchor' without constitution_ref raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _constraint(kind="constitution_anchor", content="Follow arch rule")
        self.assertIn("constitution_ref", str(ctx.exception))

    def test_external_system_requires_protocol_or_contract_doc_ref(self):
        """kind='external_system' without protocol or contract_doc_ref raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _constraint(kind="external_system", content="Integrate with payment API")
        self.assertIn("protocol", str(ctx.exception))

    def test_external_system_accepts_with_protocol_only(self):
        """kind='external_system' with protocol only accepts."""
        c = _constraint(kind="external_system", content="Integrate with payment API", protocol="REST/JSON")
        self.assertEqual(c.kind, "external_system")

    def test_external_system_accepts_with_contract_doc_ref_only(self):
        """kind='external_system' with contract_doc_ref only accepts."""
        c = _constraint(kind="external_system", content="Integrate with payment API",
                        contract_doc_ref="docs/payment-api-contract.md")
        self.assertEqual(c.kind, "external_system")

    def test_compute_confidence_grade_tier1_test_result(self):
        """compute_confidence_grade tier=1 + test-result + primary → HIGH."""
        grade = hs.compute_confidence_grade("1", "test-result", "primary", False)
        self.assertEqual(grade, "HIGH")

    def test_compute_confidence_grade_tier3_any(self):
        """compute_confidence_grade tier=3 → LOW regardless of other fields."""
        grade = hs.compute_confidence_grade("3", "user-observation", "primary", False)
        self.assertEqual(grade, "LOW")

    def test_compute_confidence_grade_production_site_check_primary_non_test(self):
        """production_site_check + primary + user-observation → MEDIUM downgrade."""
        grade = hs.compute_confidence_grade("3", "user-observation", "primary", True)
        self.assertEqual(grade, "MEDIUM")

    def test_value_production_site_rejects_none_sentinel(self):
        """ValueProductionSite with file_line='(none)' raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _value_production_site(file_line="(none)")
        self.assertIn("(none)", str(ctx.exception))

    def test_tier_1_5_requires_script_path(self):
        """tier='1.5' without script_path raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _probe(tier="1.5", script_path=None)
        self.assertIn("script_path", str(ctx.exception))

    def test_mode_feature_addition_accepts_no_data_flow_chain(self):
        """mode='feature_addition' + no data_flow_chain + vue file → accepted (only bug mode triggers)."""
        ss = _spec_seeds(
            affected_areas=[_affected_area(files=["src/components/Feature.vue:1"])],
            data_flow_chain=None,
        )
        ps = _plan_seeds()
        h = _handoff(mode="feature_addition", spec_seeds=ss, plan_seeds=ps)
        self.assertEqual(h.mode, "feature_addition")

    def test_compute_grade_inconclusive_from_test_result_is_medium(self):
        """compute_confidence_grade tier-1+test-result+inconclusive → MEDIUM (not LOW fallback).

        Tier-1 test ran but couldn't discriminate — stronger than no-probe-ran (LOW)
        but not confirmatory (HIGH). Verifies the new rule for tier '1' and '1.5'.
        """
        grade_tier1 = hs.compute_confidence_grade("1", "test-result", "inconclusive", False)
        self.assertEqual(grade_tier1, "MEDIUM")

        grade_tier15 = hs.compute_confidence_grade("1.5", "test-result", "inconclusive", False)
        self.assertEqual(grade_tier15, "MEDIUM")

    def test_affected_area_rejects_non_string_files_element(self):
        """AffectedArea.files element that is not a str raises ValueError mentioning type and area name."""
        with self.assertRaises(ValueError) as ctx:
            hs.AffectedArea(area="service", files=["src/foo.py:10", 42], impact="internal")
        msg = str(ctx.exception)
        self.assertIn("int", msg)
        self.assertIn("service", msg)


# ---------------------------------------------------------------------------
# TestVerbatimPrompt — Step 1 (18-SCOPE-FIDELITY-AND-PROMPT-INTAKE-PLAN.md)
# Tests for Intent.verbatim_prompt: validation, round-trip, back-compat.
# ---------------------------------------------------------------------------


class TestVerbatimPrompt(unittest.TestCase):
    """Tests for Intent.verbatim_prompt field added in schema v1.1."""

    # --- Intent.verbatim_prompt field-level validation ---

    def test_verbatim_prompt_none_tolerated(self):
        """Intent with verbatim_prompt=None does not raise (back-compat default)."""
        i = _intent()  # uses default verbatim_prompt=None
        self.assertIsNone(i.verbatim_prompt)

    def test_verbatim_prompt_nonempty_accepted(self):
        """Intent with a non-empty verbatim_prompt is accepted."""
        full_prompt = (
            "Config value not applied at startup. "
            "Suspected cause: env var read before process env is populated by the launcher."
        )
        i = hs.Intent(
            symptom_summary="Config value not applied",
            desired_summary="Config applied correctly",
            scope="file-local",
            verbatim_prompt=full_prompt,
        )
        self.assertEqual(i.verbatim_prompt, full_prompt)

    def test_verbatim_prompt_empty_string_rejected(self):
        """Intent with verbatim_prompt='' raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            hs.Intent(
                symptom_summary="Config value not applied",
                desired_summary="Config applied correctly",
                scope="file-local",
                verbatim_prompt="",
            )
        self.assertIn("verbatim_prompt", str(ctx.exception))

    def test_verbatim_prompt_whitespace_only_rejected(self):
        """Intent with verbatim_prompt='   ' (whitespace only) raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            hs.Intent(
                symptom_summary="Config value not applied",
                desired_summary="Config applied correctly",
                scope="file-local",
                verbatim_prompt="   ",
            )
        self.assertIn("verbatim_prompt", str(ctx.exception))

    # --- Round-trip: full prompt with "Suspected cause:" tail ---

    def test_verbatim_prompt_carried_into_handoff_distinct_from_topic(self):
        """verbatim_prompt survives Handoff construction unchanged.

        The full prompt contains a 'Suspected cause:' tail that the topic
        field would not carry. Assert intent.verbatim_prompt equals the full
        prompt, not the paraphrased topic.
        """
        full_prompt = (
            "Config value not applied at startup. "
            "Suspected cause: env var read before process env is populated by the launcher."
        )
        topic_only = "Config value not applied at startup."  # shorter — what set-topic stores

        intent_with_full_prompt = hs.Intent(
            symptom_summary="Config value not applied at startup",
            desired_summary="Config applied correctly on first read",
            scope="file-local",
            verbatim_prompt=full_prompt,
        )
        h = _handoff(intent=intent_with_full_prompt)
        self.assertEqual(h.intent.verbatim_prompt, full_prompt)
        self.assertNotEqual(h.intent.verbatim_prompt, topic_only)

    # --- Back-compat: v1.0 handoff dict loads without verbatim_prompt ---

    def test_back_compat_v1_0_handoff_dict_loads_without_verbatim_prompt(self):
        """A handoff dict with schema_version='1.0' and no verbatim_prompt key loads.

        Simulates _dict_to_dataclass reconstructing a pre-v1.1 handoff.json
        that lacks the verbatim_prompt key. The Intent must tolerate the absent
        field (Optional[str] = None default).
        """
        # Construct an Intent without verbatim_prompt — simulates what
        # _dict_to_dataclass does when the key is absent from JSON.
        i = hs.Intent(
            symptom_summary="Old symptom text",
            desired_summary="Old desired state",
            scope="file-local",
            # verbatim_prompt intentionally omitted — default None
        )
        self.assertIsNone(i.verbatim_prompt)

        # Also verify Handoff accepts schema_version="1.0".
        h = _handoff(schema_version="1.0", intent=i)
        self.assertEqual(h.schema_version, "1.0")
        self.assertIsNone(h.intent.verbatim_prompt)

    def test_schema_version_1_0_accepted(self):
        """schema_version='1.0' is accepted (back-compat — frozenset allows both 1.0 and 1.1)."""
        h = _handoff(schema_version="1.0")
        self.assertEqual(h.schema_version, "1.0")

    def test_schema_version_1_1_accepted(self):
        """schema_version='1.1' is the current version and must be accepted."""
        h = _handoff(schema_version="1.1")
        self.assertEqual(h.schema_version, "1.1")


# ---------------------------------------------------------------------------
# correctness_vetted provenance marker tests (Seam E fix).
# ---------------------------------------------------------------------------


class TestCorrectnessVetted(unittest.TestCase):
    """Tests for PlanSeeds.correctness_vetted — the shape-only provenance marker."""

    def test_defaults_to_false(self):
        """PlanSeeds constructs with correctness_vetted=False when the kwarg is omitted."""
        ps = _plan_seeds()
        self.assertIs(ps.correctness_vetted, False)

    def test_explicit_false_accepted(self):
        """PlanSeeds accepts explicit correctness_vetted=False."""
        ps = _plan_seeds(correctness_vetted=False)
        self.assertIs(ps.correctness_vetted, False)

    def test_explicit_true_accepted(self):
        """PlanSeeds accepts correctness_vetted=True."""
        ps = _plan_seeds(correctness_vetted=True)
        self.assertIs(ps.correctness_vetted, True)

    def test_non_bool_string_raises(self):
        """PlanSeeds rejects a string value for correctness_vetted."""
        with self.assertRaises(ValueError) as ctx:
            _plan_seeds(correctness_vetted="true")
        self.assertIn("correctness_vetted", str(ctx.exception))

    def test_none_raises(self):
        """PlanSeeds rejects None for correctness_vetted."""
        with self.assertRaises(ValueError) as ctx:
            _plan_seeds(correctness_vetted=None)
        self.assertIn("correctness_vetted", str(ctx.exception))

    def test_asdict_includes_correctness_vetted(self):
        """dataclasses.asdict on a PlanSeeds includes correctness_vetted=True in the result dict."""
        import dataclasses
        ps = _plan_seeds(correctness_vetted=True)
        d = dataclasses.asdict(ps)
        self.assertIn("correctness_vetted", d)
        self.assertIs(d["correctness_vetted"], True)

    def test_asdict_default_emits_false(self):
        """dataclasses.asdict on a default PlanSeeds emits correctness_vetted=False."""
        import dataclasses
        ps = _plan_seeds()
        d = dataclasses.asdict(ps)
        self.assertIn("correctness_vetted", d)
        self.assertIs(d["correctness_vetted"], False)

    def test_asdict_handoff_pop_pattern_preserves_correctness_vetted(self):
        """_asdict_handoff's pop(_proposed_call_shape_parse_failed) leaves correctness_vetted intact.

        The serializer (_asdict_handoff) explicitly pops _proposed_call_shape_parse_failed
        before writing JSON. correctness_vetted must survive that pop.
        """
        import dataclasses
        ps = _plan_seeds(correctness_vetted=False)
        raw = dataclasses.asdict(ps)
        # Internal flag must be in raw asdict output (asdict includes all fields).
        self.assertIn("_proposed_call_shape_parse_failed", raw)
        # After the _asdict_handoff pop (mirrored here):
        raw.pop("_proposed_call_shape_parse_failed", None)
        # correctness_vetted must survive the pop.
        self.assertIn("correctness_vetted", raw)
        # Internal flag must be gone.
        self.assertNotIn("_proposed_call_shape_parse_failed", raw)

    def test_back_compat_construction_without_field_uses_default(self):
        """Old plan_seeds dict without correctness_vetted constructs PlanSeeds with default False.

        This is the back-compat load path: _dict_to_dataclass skips absent fields
        that have a default, causing the dataclass to use its declared default (False).
        Simulated here by constructing PlanSeeds without the correctness_vetted kwarg,
        which is exactly what _dict_to_dataclass does for an absent-but-defaulted field.
        """
        ps = hs.PlanSeeds(
            recommended_approach_id="fix_cache",
            recommended_approach_summary="Clear cache on write",
            layer_destination="service",
            layer_justification="Service-layer only",
            complexity=hs.Complexity(changes="Low", risk="Low", verify_cost="Low"),
            cited_canonical_patterns=[],
            alternatives_considered=[],
            proposed_call_shape=None,
            # correctness_vetted intentionally omitted — simulates a pre-field record
        )
        self.assertIs(ps.correctness_vetted, False)

    def test_round_trip_stability_current_producer(self):
        """Current-producer PlanSeeds round-trips stably.

        Produce → asdict (minus internal flag, mirroring _asdict_handoff) → reconstruct
        → re-asdict (minus internal flag) → byte-identical dicts.

        This proves the serializer path is stable. Old handoffs (absent field) parse
        to the default — that is a distinct assertion in test_back_compat_construction_*.
        """
        import dataclasses
        ps = _plan_seeds()  # correctness_vetted=False (current-producer default)

        # First serialization (mimicking _asdict_handoff).
        d1 = dataclasses.asdict(ps)
        d1.pop("_proposed_call_shape_parse_failed", None)

        # Re-construct from d1 (simulating _dict_to_dataclass for PlanSeeds).
        ps2 = hs.PlanSeeds(
            recommended_approach_id=d1["recommended_approach_id"],
            recommended_approach_summary=d1["recommended_approach_summary"],
            layer_destination=d1["layer_destination"],
            layer_justification=d1["layer_justification"],
            complexity=hs.Complexity(**d1["complexity"]),
            cited_canonical_patterns=[
                hs.CitedPattern(**p) for p in d1["cited_canonical_patterns"]
            ],
            alternatives_considered=[
                hs.Alternative(**a) for a in d1["alternatives_considered"]
            ],
            proposed_call_shape=d1["proposed_call_shape"],
            correctness_vetted=d1["correctness_vetted"],
        )

        # Second serialization.
        d2 = dataclasses.asdict(ps2)
        d2.pop("_proposed_call_shape_parse_failed", None)

        self.assertEqual(d1, d2)


# ---------------------------------------------------------------------------
# Plan 53 Phase 1 — DesignAnchor + SpecSeeds.design_anchor.
# ---------------------------------------------------------------------------


class TestDesignAnchor(unittest.TestCase):
    def test_empty_default_is_well_formed(self):
        da = hs.DesignAnchor()
        self.assertEqual(da.kind, "")
        self.assertEqual(da.file, "")
        self.assertEqual(da.selectors, [])

    def test_non_html_kind_is_shape_valid(self):
        """D3: kind is an OPEN discriminator -- any string is shape-valid."""
        da = hs.DesignAnchor(kind="figma", file="https://figma.com/x", selectors=[".a"])
        self.assertEqual(da.kind, "figma")
        da2 = hs.DesignAnchor(kind="some-future-tool", file="x", selectors=[])
        self.assertEqual(da2.kind, "some-future-tool")

    def test_reject_non_string_kind(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DesignAnchor(kind=123)
        self.assertIn("kind", str(ctx.exception))

    def test_reject_non_string_file(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DesignAnchor(file=123)
        self.assertIn("file", str(ctx.exception))

    def test_reject_selectors_not_a_list(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DesignAnchor(selectors="not-a-list")
        self.assertIn("selectors", str(ctx.exception))

    def test_reject_selectors_non_string_element(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DesignAnchor(selectors=[".a", 2])
        self.assertIn("selectors", str(ctx.exception))

    def test_spec_seeds_default_design_anchor_is_empty(self):
        """SpecSeeds constructed WITHOUT a design_anchor kwarg (the shape you
        get reconstructing from an old handoff.json dict missing the key)
        gets an empty DesignAnchor via the dataclass default_factory —
        proves back-compat deserialization for handoff.json predating plan 53.
        """
        ss = hs.SpecSeeds(
            spec_type_hint="bug_fix",
            constraints=[_constraint()],
            affected_areas=[_affected_area()],
            risks=[_risk()],
            open_questions=[_open_question()],
            # design_anchor intentionally omitted.
        )
        self.assertIsInstance(ss.design_anchor, hs.DesignAnchor)
        self.assertEqual(ss.design_anchor.kind, "")
        self.assertEqual(ss.design_anchor.file, "")
        self.assertEqual(ss.design_anchor.selectors, [])

    def test_spec_seeds_carries_captured_design_anchor(self):
        anchor = hs.DesignAnchor(kind="html", file="design/reference.html", selectors=[".fooBar"])
        ss = _spec_seeds(design_anchor=anchor)
        self.assertIs(ss.design_anchor, anchor)

    def test_spec_seeds_reject_design_anchor_wrong_type(self):
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(design_anchor={"kind": "html"})
        self.assertIn("design_anchor", str(ctx.exception))


# ---------------------------------------------------------------------------
# CallerEnumeration tests (plan 67 D6 — research handoff carry).
# ---------------------------------------------------------------------------


class TestFixPathHelper(unittest.TestCase):
    def test_valid_construction(self):
        h = _fix_path_helper(qn="config.load", file_line="src/config.py:42")
        self.assertEqual(h.qn, "config.load")
        self.assertEqual(h.file_line, "src/config.py:42")

    def test_reject_empty_qn(self):
        with self.assertRaises(ValueError) as ctx:
            hs.FixPathHelper(qn="", file_line="src/config.py:42")
        self.assertIn("FixPathHelper.qn", str(ctx.exception))

    def test_reject_empty_file_line(self):
        with self.assertRaises(ValueError) as ctx:
            hs.FixPathHelper(qn="config.load", file_line="")
        self.assertIn("FixPathHelper.file_line", str(ctx.exception))


class TestInboundCaller(unittest.TestCase):
    def test_valid_construction(self):
        c = _inbound_caller(
            helper_qn="config.load", caller_qn="main.startup", file_line="src/main.py:15",
        )
        self.assertEqual(c.helper_qn, "config.load")
        self.assertEqual(c.caller_qn, "main.startup")
        self.assertEqual(c.file_line, "src/main.py:15")

    def test_reject_empty_helper_qn(self):
        with self.assertRaises(ValueError) as ctx:
            hs.InboundCaller(helper_qn="", caller_qn="main.startup", file_line="src/main.py:15")
        self.assertIn("InboundCaller.helper_qn", str(ctx.exception))

    def test_reject_empty_caller_qn(self):
        with self.assertRaises(ValueError) as ctx:
            hs.InboundCaller(helper_qn="config.load", caller_qn="", file_line="src/main.py:15")
        self.assertIn("InboundCaller.caller_qn", str(ctx.exception))

    def test_reject_empty_file_line(self):
        with self.assertRaises(ValueError) as ctx:
            hs.InboundCaller(helper_qn="config.load", caller_qn="main.startup", file_line="")
        self.assertIn("InboundCaller.file_line", str(ctx.exception))

    # -- plan 69 D5/WI-E: surface/scope/justification classification fields --

    def test_defaults_classification_fields_to_empty_string(self):
        """Absent surface/scope/justification -> "" (back-compat: a row
        recorded via record-inbound-caller but never classified, or a
        handoff.json predating plan 69, is the unclassified-legacy-row
        state, not a construction error)."""
        c = hs.InboundCaller(
            helper_qn="config.load", caller_qn="main.startup", file_line="src/main.py:15",
        )
        self.assertEqual(c.surface, "")
        self.assertEqual(c.scope, "")
        self.assertEqual(c.justification, "")

    def test_valid_construction_with_classification_scope_in(self):
        c = hs.InboundCaller(
            helper_qn="config.load", caller_qn="main.startup", file_line="src/main.py:15",
            surface="Admin dashboard", scope="in",
            justification="Reachable from the admin dashboard button.",
        )
        self.assertEqual(c.surface, "Admin dashboard")
        self.assertEqual(c.scope, "in")
        self.assertEqual(c.justification, "Reachable from the admin dashboard button.")

    def test_valid_construction_with_classification_scope_out(self):
        c = hs.InboundCaller(
            helper_qn="config.load", caller_qn="main.startup", file_line="src/main.py:15",
            surface="none", scope="out",
            justification="Background job; not reachable from any UI surface.",
        )
        self.assertEqual(c.surface, "none")
        self.assertEqual(c.scope, "out")

    def test_valid_construction_with_scope_in_and_empty_surface_justification(self):
        """A schema-legal partial classification -- scope="in" with surface
        and justification left empty -- constructs cleanly.

        Unreachable via the real producer (classify-caller-scope enforces
        non-empty --surface / --justification at the setter boundary), but
        the schema itself does not re-enforce that pairing: per InboundCaller's
        docstring, "surface / justification are not non-empty-enforced here
        -- classify-caller-scope already enforces non-empty at the setter
        boundary, so this schema stays a straight verbatim carrier rather
        than re-running a check the producer already ran." This test locks
        that documented trade-off in place -- see
        CallerEnumerationRenderTests.test_classified_row_with_empty_surface_and_justification_renders_placeholders
        in test_plan_helper.py for the corresponding render-side fallback
        this partial state exercises.
        """
        c = hs.InboundCaller(
            helper_qn="config.load", caller_qn="main.startup", file_line="src/main.py:15",
            scope="in", surface="", justification="",
        )
        self.assertEqual(c.scope, "in")
        self.assertEqual(c.surface, "")
        self.assertEqual(c.justification, "")

    def test_reject_invalid_scope_value(self):
        with self.assertRaises(ValueError) as ctx:
            hs.InboundCaller(
                helper_qn="config.load", caller_qn="main.startup", file_line="src/main.py:15",
                scope="sideways",
            )
        self.assertIn("InboundCaller.scope", str(ctx.exception))

    def test_reject_non_string_surface(self):
        with self.assertRaises(ValueError) as ctx:
            hs.InboundCaller(
                helper_qn="config.load", caller_qn="main.startup", file_line="src/main.py:15",
                surface=42,
            )
        self.assertIn("InboundCaller.surface", str(ctx.exception))

    def test_reject_non_string_justification(self):
        with self.assertRaises(ValueError) as ctx:
            hs.InboundCaller(
                helper_qn="config.load", caller_qn="main.startup", file_line="src/main.py:15",
                justification=42,
            )
        self.assertIn("InboundCaller.justification", str(ctx.exception))

    def test_asdict_includes_classification_fields(self):
        import dataclasses
        c = _inbound_caller(
            surface="Admin dashboard", scope="in", justification="reachable",
        )
        d = dataclasses.asdict(c)
        self.assertEqual(d["surface"], "Admin dashboard")
        self.assertEqual(d["scope"], "in")
        self.assertEqual(d["justification"], "reachable")

    def test_asdict_default_emits_empty_classification_fields(self):
        """Default construction (no classification supplied) -> asdict shows
        the explicit "" unclassified state for all three fields -- proves
        the current producer's default shape, the honest half of the
        back-compat pair (contrast test_defaults_classification_fields_to_empty_string,
        which proves an old-shaped construction still parses)."""
        import dataclasses
        c = _inbound_caller()
        d = dataclasses.asdict(c)
        self.assertEqual(d["surface"], "")
        self.assertEqual(d["scope"], "")
        self.assertEqual(d["justification"], "")


class TestCallerEnumeration(unittest.TestCase):
    def test_default_is_empty(self):
        """Default construction -- both lists empty, justification None (back-compat shape)."""
        ce = hs.CallerEnumeration()
        self.assertEqual(ce.fix_path_helpers, [])
        self.assertEqual(ce.inbound_callers, [])
        self.assertIsNone(ce.no_shared_callers_justification)

    def test_populated_with_helpers_and_callers(self):
        h = _fix_path_helper()
        c = _inbound_caller()
        ce = hs.CallerEnumeration(fix_path_helpers=[h], inbound_callers=[c])
        self.assertEqual(ce.fix_path_helpers, [h])
        self.assertEqual(ce.inbound_callers, [c])

    def test_justification_only(self):
        ce = hs.CallerEnumeration(
            no_shared_callers_justification="purely additive in a new module",
        )
        self.assertEqual(ce.fix_path_helpers, [])
        self.assertEqual(
            ce.no_shared_callers_justification, "purely additive in a new module",
        )

    def test_reject_non_list_fix_path_helpers(self):
        with self.assertRaises(ValueError) as ctx:
            hs.CallerEnumeration(fix_path_helpers="not-a-list")
        self.assertIn("fix_path_helpers", str(ctx.exception))

    def test_reject_non_list_inbound_callers(self):
        with self.assertRaises(ValueError) as ctx:
            hs.CallerEnumeration(inbound_callers="not-a-list")
        self.assertIn("inbound_callers", str(ctx.exception))

    def test_reject_wrong_element_type_fix_path_helpers(self):
        with self.assertRaises(ValueError) as ctx:
            hs.CallerEnumeration(fix_path_helpers=[{"qn": "x", "file_line": "y:1"}])
        self.assertIn("FixPathHelper", str(ctx.exception))

    def test_reject_wrong_element_type_inbound_callers(self):
        with self.assertRaises(ValueError) as ctx:
            hs.CallerEnumeration(inbound_callers=[{"helper_qn": "x"}])
        self.assertIn("InboundCaller", str(ctx.exception))

    def test_reject_empty_string_justification(self):
        """A blank justification is rejected -- Optional means None-or-non-empty, not None-or-blank."""
        with self.assertRaises(ValueError) as ctx:
            hs.CallerEnumeration(no_shared_callers_justification="   ")
        self.assertIn("no_shared_callers_justification", str(ctx.exception))


class TestPlanSeedsCallerEnumeration(unittest.TestCase):
    """Tests for PlanSeeds.caller_enumeration -- the field wiring on the aggregate."""

    def test_defaults_to_empty_caller_enumeration(self):
        """Omitting caller_enumeration -> PlanSeeds gets an empty CallerEnumeration.

        Back-compat: old handoffs (or a state where neither Phase 2.4c path
        fired) must construct cleanly with the empty default.
        """
        ps = hs.PlanSeeds(
            recommended_approach_id="fix_literal",
            recommended_approach_summary="Fix the bug",
            layer_destination="ui",
            layer_justification="scoped",
            complexity=_complexity(),
        )
        self.assertIsInstance(ps.caller_enumeration, hs.CallerEnumeration)
        self.assertEqual(ps.caller_enumeration.fix_path_helpers, [])
        self.assertEqual(ps.caller_enumeration.inbound_callers, [])
        self.assertIsNone(ps.caller_enumeration.no_shared_callers_justification)

    def test_carries_populated_caller_enumeration(self):
        ce = _caller_enumeration(
            fix_path_helpers=[_fix_path_helper()],
            inbound_callers=[_inbound_caller()],
        )
        ps = _plan_seeds(caller_enumeration=ce)
        self.assertIs(ps.caller_enumeration, ce)
        self.assertEqual(len(ps.caller_enumeration.fix_path_helpers), 1)
        self.assertEqual(len(ps.caller_enumeration.inbound_callers), 1)

    def test_reject_wrong_type(self):
        with self.assertRaises(ValueError) as ctx:
            _plan_seeds(caller_enumeration={"fix_path_helpers": []})
        self.assertIn("caller_enumeration", str(ctx.exception))

    def test_asdict_includes_caller_enumeration(self):
        import dataclasses
        ce = _caller_enumeration(fix_path_helpers=[_fix_path_helper()])
        ps = _plan_seeds(caller_enumeration=ce)
        d = dataclasses.asdict(ps)
        self.assertIn("caller_enumeration", d)
        self.assertEqual(len(d["caller_enumeration"]["fix_path_helpers"]), 1)
        self.assertEqual(d["caller_enumeration"]["fix_path_helpers"][0]["qn"], "config.load")

    def test_asdict_default_emits_empty_caller_enumeration(self):
        import dataclasses
        ps = _plan_seeds()  # default caller_enumeration
        d = dataclasses.asdict(ps)
        self.assertEqual(d["caller_enumeration"], {
            "fix_path_helpers": [],
            "inbound_callers": [],
            "no_shared_callers_justification": None,
        })


# ---------------------------------------------------------------------------
# EvidenceLanes tests (plan 73 D7 — not-covered evidence-lane declaration).
# ---------------------------------------------------------------------------


class TestEvidenceLanes(unittest.TestCase):
    """Tests for the EvidenceLanes dataclass in isolation."""

    def test_default_construction_all_false(self):
        """Bare hs.EvidenceLanes() -- every lane defaults False."""
        el = hs.EvidenceLanes()
        self.assertFalse(el.static_graph)
        self.assertFalse(el.text_search)
        self.assertFalse(el.runtime_probe)
        self.assertFalse(el.history)

    def test_explicit_construction_round_trips(self):
        el = _evidence_lanes(static_graph=True, history=True)
        self.assertTrue(el.static_graph)
        self.assertFalse(el.text_search)
        self.assertFalse(el.runtime_probe)
        self.assertTrue(el.history)

    def test_all_four_true(self):
        el = _evidence_lanes(static_graph=True, text_search=True, runtime_probe=True, history=True)
        self.assertTrue(el.static_graph)
        self.assertTrue(el.text_search)
        self.assertTrue(el.runtime_probe)
        self.assertTrue(el.history)

    def test_reject_non_bool_static_graph(self):
        with self.assertRaises(ValueError) as ctx:
            hs.EvidenceLanes(static_graph="true")
        self.assertIn("EvidenceLanes.static_graph", str(ctx.exception))
        self.assertIn("must be a bool", str(ctx.exception))

    def test_reject_non_bool_text_search(self):
        with self.assertRaises(ValueError) as ctx:
            hs.EvidenceLanes(text_search=1)
        self.assertIn("EvidenceLanes.text_search", str(ctx.exception))

    def test_reject_non_bool_runtime_probe(self):
        with self.assertRaises(ValueError) as ctx:
            hs.EvidenceLanes(runtime_probe=None)
        self.assertIn("EvidenceLanes.runtime_probe", str(ctx.exception))

    def test_reject_non_bool_history(self):
        with self.assertRaises(ValueError) as ctx:
            hs.EvidenceLanes(history="yes")
        self.assertIn("EvidenceLanes.history", str(ctx.exception))


class TestHandoffEvidenceLanes(unittest.TestCase):
    """Tests for Handoff.evidence_lanes -- the field wiring on the top-level record."""

    def test_handoff_default_evidence_lanes_is_empty(self):
        """Handoff constructed WITHOUT an evidence_lanes kwarg (the shape you
        get reconstructing from an old handoff.json dict missing the key)
        gets an all-False EvidenceLanes via the dataclass default_factory —
        proves back-compat deserialization for handoff.json predating plan
        73 D7. Builds hs.Handoff(...) directly (bypassing the _handoff()
        test builder, which supplies an explicit default) so the dataclass
        default itself is what is under test.
        """
        h = hs.Handoff(
            schema_version=hs.SCHEMA_VERSION,
            research_path="research/2026-05-19-test.md",
            research_completed_at="2026-05-19T10:00:00Z",
            mode="bug",
            intent=_intent(),
            spec_seeds=_spec_seeds(
                affected_areas=[_affected_area_py()],
            ),
            plan_seeds=_plan_seeds(),
            probe=_probe(),
            downstream_links=_downstream_links(),
            # evidence_lanes intentionally omitted.
        )
        self.assertIsInstance(h.evidence_lanes, hs.EvidenceLanes)
        self.assertFalse(h.evidence_lanes.static_graph)
        self.assertFalse(h.evidence_lanes.text_search)
        self.assertFalse(h.evidence_lanes.runtime_probe)
        self.assertFalse(h.evidence_lanes.history)

    def test_handoff_carries_populated_evidence_lanes(self):
        el = _evidence_lanes(text_search=True, history=True)
        h = _handoff(evidence_lanes=el)
        self.assertIs(h.evidence_lanes, el)
        self.assertTrue(h.evidence_lanes.text_search)
        self.assertTrue(h.evidence_lanes.history)
        self.assertFalse(h.evidence_lanes.static_graph)

    def test_reject_wrong_type(self):
        with self.assertRaises(ValueError) as ctx:
            _handoff(evidence_lanes={"static_graph": True})
        self.assertIn("evidence_lanes", str(ctx.exception))

    def test_asdict_includes_evidence_lanes(self):
        import dataclasses
        el = _evidence_lanes(runtime_probe=True)
        h = _handoff(evidence_lanes=el)
        d = dataclasses.asdict(h)
        self.assertIn("evidence_lanes", d)
        self.assertEqual(d["evidence_lanes"], {
            "static_graph": False,
            "text_search": False,
            "runtime_probe": True,
            "history": False,
        })

    def test_asdict_default_emits_all_false_evidence_lanes(self):
        import dataclasses
        h = _handoff()  # default evidence_lanes via the test builder's own default
        d = dataclasses.asdict(h)
        self.assertEqual(d["evidence_lanes"], {
            "static_graph": False,
            "text_search": False,
            "runtime_probe": False,
            "history": False,
        })

    def test_evidence_lanes_does_not_interact_with_schema_version(self):
        """A populated evidence_lanes combined with a LEGACY schema_version
        ("1.0"/"1.1", predating plan 73 D1) still constructs cleanly --
        evidence_lanes carries no cross-field validation and is therefore
        immune to the schema_version-scoped requiredness rule that governs
        literal_archaeology (Build discipline axis (b): no previously-valid
        combination is put at risk by this purely additive field).
        """
        for version in ("1.0", "1.1", "1.2"):
            el = _evidence_lanes(static_graph=True, history=True)
            h = _handoff(schema_version=version, evidence_lanes=el)
            self.assertEqual(h.schema_version, version)
            self.assertTrue(h.evidence_lanes.static_graph)
            self.assertTrue(h.evidence_lanes.history)


if __name__ == "__main__":
    unittest.main()
