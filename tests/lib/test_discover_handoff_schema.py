"""Tests for src/devforge/lib/_discover/handoff_schema.py.

Covers all 21 test cases enumerated in 03-DISCOVER-HANDOFF-PLAN.md Step 1 Verify block.
Grouped into logical sections:

- TestHappyPath (3 cases): worth_pursuing, reconsider_verdict, override_recorded
- TestHandoffKindAndSpec (2 cases): reject handoff_kind, reject spec_type_hint
- TestDesignOptions (3 cases): letter_prefix, duplicate_ids, recommended_not_in_options
- TestComplexityEnum (2 cases): invalid complexity enum, invalid overall_fit enum
- TestDMirror (2 cases): reject strained no override, accept strained with override
- TestGMirror (1 case): reject rationale missing internal path
- TestInternalEquivalence (1 case): reject is_internal mismatch
- TestComplexityDerivation (1 case): reject inconsistent changes value
- TestOutcome (6 cases): high/medium/low confidence, delta_null rejection,
    internal_extension_followed null/non-null rejections

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
_DISCOVER_DIR = _HERE.parent.parent / "src" / "devforge" / "lib" / "_discover"

_spec = importlib.util.spec_from_file_location(
    "discover_handoff_schema",  # unique name — never "handoff_schema"; avoids sys.modules collision
    _DISCOVER_DIR / "handoff_schema.py",
)
hs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hs)


# ---------------------------------------------------------------------------
# Fixture factories -- all return valid minimal objects; tests mutate one field.
# ---------------------------------------------------------------------------


def _intent(**kwargs):
    defaults = dict(
        feature_concept="Persist audit logs to durable storage",
        topic="audit-log-persistence",
        topic_slug="audit-log-persistence",
        scope_summary="Write structured audit events to PostgreSQL on every state change",
    )
    defaults.update(kwargs)
    return hs.Intent(**defaults)


def _constraint(kind="nfr", **kwargs):
    defaults = {
        "nfr": dict(content="Writes must complete within 100ms", quantifier="p99 < 100ms"),
        "constitution_anchor": dict(content="Follow SOLID principles", constitution_ref="constitution.md#solid"),
        "external_system": dict(content="Write via REST API", protocol="REST/HTTP"),
    }
    base = defaults[kind].copy()
    base["kind"] = kind
    base.update(kwargs)
    return hs.Constraint(**base)


def _affected_area(**kwargs):
    defaults = dict(
        area="EventService",
        files=["src/services/event_service.py:42"],
        impact="Audit events written here",
        is_internal_extension_candidate=False,
    )
    defaults.update(kwargs)
    return hs.AffectedArea(**defaults)


def _risk(**kwargs):
    defaults = dict(
        risk="Database latency spikes",
        likelihood="Med",
        impact="High",
        mitigation="Use async write queue",
    )
    defaults.update(kwargs)
    return hs.Risk(**defaults)


def _open_question(**kwargs):
    defaults = dict(question="Which storage backend is preferred?", blocking=False)
    defaults.update(kwargs)
    return hs.OpenQuestion(**defaults)


def _spec_seeds(**kwargs):
    defaults = dict(
        spec_type_hint="greenfield_feature",
        constraints=[_constraint()],
        affected_areas=[_affected_area()],
        risks=[_risk()],
        open_questions=[_open_question()],
    )
    defaults.update(kwargs)
    return hs.SpecSeeds(**defaults)


def _design_option(id="A", **kwargs):
    defaults = dict(
        id=id,
        name="PostgreSQL append-only table",
        shape="Add an audit_log table with append-only semantics and write via ORM",
        pros=["Simple", "ACID"],
        cons=["Single point of failure"],
        complexity="Low",
    )
    defaults.update(kwargs)
    return hs.DesignOption(**defaults)


def _build_vs_buy(**kwargs):
    defaults = dict(
        recommendation="Build",
        build_path="Build append-only ORM layer on top of existing DB connection pool",
        buy_path="Adopt a third-party audit library such as auditlog-py",
        reasoning="Existing DB infra is already in place; build cost is minimal",
    )
    defaults.update(kwargs)
    return hs.BuildVsBuy(**defaults)


def _cited_pattern_external(**kwargs):
    defaults = dict(
        reference="SQLAlchemy ORM",
        kind="library",
        source="https://docs.sqlalchemy.org/",
        relevance="ORM used throughout project",
        is_internal=False,
    )
    defaults.update(kwargs)
    return hs.CitedPattern(**defaults)


def _cited_pattern_internal(**kwargs):
    defaults = dict(
        reference="BaseRepository",
        kind="pattern",
        source="internal:src/db/base_repository.py",
        relevance="Existing repo pattern to extend",
        is_internal=True,
    )
    defaults.update(kwargs)
    return hs.CitedPattern(**defaults)


def _complexity(**kwargs):
    defaults = dict(changes="Low", risk="Low", verify_cost="Low")
    defaults.update(kwargs)
    return hs.Complexity(**defaults)


def _plan_seeds(
    design_options=None,
    build_vs_buy=None,
    cited_canonical_patterns=None,
    complexity=None,
    recommended_option_id="A",
    recommended_option_rationale="Use the PostgreSQL append-only table pattern",
    effort_estimate="Low",
    overall_fit="Good",
    derisk_count=0,
    **kwargs,
):
    """Build a valid PlanSeeds.

    effort_estimate / overall_fit / derisk_count are source fields for the
    unconditional complexity derivation check.  Defaults (Low / Good / 0) derive
    to complexity (Low / Low / Low) which matches the default _complexity() fixture.
    Tests that supply a non-default complexity MUST also supply matching source fields.
    """
    if design_options is None:
        design_options = [_design_option()]
    if build_vs_buy is None:
        build_vs_buy = _build_vs_buy()
    if cited_canonical_patterns is None:
        cited_canonical_patterns = [_cited_pattern_external()]
    if complexity is None:
        complexity = _complexity()
    return hs.PlanSeeds(
        design_options=design_options,
        build_vs_buy=build_vs_buy,
        cited_canonical_patterns=cited_canonical_patterns,
        complexity=complexity,
        recommended_option_id=recommended_option_id,
        recommended_option_rationale=recommended_option_rationale,
        _effort_estimate=effort_estimate,
        _overall_fit=overall_fit,
        _derisk_count=derisk_count,
        **kwargs,
    )


def _dimension_record(state="Clear", turns=2, value="some value", **kwargs):
    rec = dict(state=state, turns=turns)
    if state == "Missing":
        rec["value"] = None
    else:
        rec["value"] = value
    rec.update(kwargs)
    return hs.DimensionRecord(**rec)


def _memo_dimensions(**kwargs):
    dim = _dimension_record()
    defaults = dict(
        functional_scope=dim,
        users=dim,
        inputs_outputs=dim,
        integration_points=dim,
        constraints=dim,
        non_goals=dim,
        success_criteria=dim,
        edge_cases=dim,
    )
    defaults.update(kwargs)
    return hs.MemoDimensions(**defaults)


def _fit_assessment(**kwargs):
    defaults = dict(
        touchpoint="EventService.write()",
        user_expected="Direct DB write",
        reality="Sync ORM call -- latency risk under load",
        effort="Medium",
        blockers=[],
    )
    defaults.update(kwargs)
    return hs.FitAssessment(**defaults)


def _discovery_block(verdict="Worth pursuing", overall_fit="Good", effort_estimate="Low", **kwargs):
    defaults = dict(
        overall_fit=overall_fit,
        effort_estimate=effort_estimate,
        fit_rationale="Good fit -- project already has SQLAlchemy integration",
        fit_assessments=[_fit_assessment()],
        verdict=verdict,
        override_recorded=False,
        memo_dimensions=_memo_dimensions(),
        references=["discover/2026-05-19-audit-log-persistence.md"],
        gaps=[],
    )
    defaults.update(kwargs)
    return hs.DiscoveryBlock(**defaults)


def _downstream_links(**kwargs):
    return hs.DownstreamLinks(**kwargs)


def _handoff(
    verdict="Worth pursuing",
    overall_fit="Good",
    effort_estimate="Low",
    outcome=None,
    plan_seeds=None,
    spec_seeds=None,
    discovery_block=None,
    **kwargs,
):
    """Build a fully-valid Handoff. Tests override specific fields."""
    if spec_seeds is None:
        spec_seeds = _spec_seeds()
    if plan_seeds is None:
        plan_seeds = _plan_seeds()
    if discovery_block is None:
        discovery_block = _discovery_block(
            verdict=verdict, overall_fit=overall_fit, effort_estimate=effort_estimate
        )
    return hs.Handoff(
        schema_version=kwargs.pop("schema_version", hs.SCHEMA_VERSION),
        handoff_kind=kwargs.pop("handoff_kind", "discover"),
        report_path=kwargs.pop("report_path", "discover/2026-05-19-audit-log-persistence.md"),
        discover_completed_at=kwargs.pop("discover_completed_at", "2026-05-19T14:32:00Z"),
        intent=kwargs.pop("intent", _intent()),
        spec_seeds=spec_seeds,
        plan_seeds=plan_seeds,
        discovery_block=discovery_block,
        downstream_links=kwargs.pop("downstream_links", _downstream_links()),
        outcome=outcome,
        **kwargs,
    )


def _outcome(
    design_option_shipped_id="A",
    design_option_shipped_summary="Shipped PostgreSQL append-only table",
    matches_recommendation=True,
    build_vs_buy_actual="Build",
    matches_build_vs_buy_recommendation=True,
    internal_extension_followed=None,
    verdict_held=True,
    shipped_commit_sha=None,
    shipped_date="2026-05-20",
    confidence_grade="HIGH",
    delta_from_recommendation=None,
    **kwargs,
):
    return hs.Outcome(
        design_option_shipped_id=design_option_shipped_id,
        design_option_shipped_summary=design_option_shipped_summary,
        matches_recommendation=matches_recommendation,
        build_vs_buy_actual=build_vs_buy_actual,
        matches_build_vs_buy_recommendation=matches_build_vs_buy_recommendation,
        internal_extension_followed=internal_extension_followed,
        verdict_held=verdict_held,
        shipped_commit_sha=shipped_commit_sha,
        shipped_date=shipped_date,
        confidence_grade=confidence_grade,
        delta_from_recommendation=delta_from_recommendation,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# TestHappyPath -- 3 cases.
# ---------------------------------------------------------------------------


class TestHappyPath(unittest.TestCase):
    """Happy-path round-trips for the three main verdict shapes."""

    def test_valid_handoff_full_worth_pursuing(self):
        """Construct a complete Handoff with 3 design options + internal prior art."""
        internal_cp = _cited_pattern_internal()
        opts = [
            _design_option("A"),
            _design_option("B", name="Event sourcing with Kafka"),
            _design_option("C", name="Write-ahead log drain"),
        ]
        ps = _plan_seeds(
            design_options=opts,
            cited_canonical_patterns=[internal_cp],
            recommended_option_id="A",
            recommended_option_rationale=(
                "PostgreSQL approach extends internal:src/db/base_repository.py "
                "with minimal code"
            ),
        )
        h = _handoff(plan_seeds=ps)
        self.assertIsInstance(h, hs.Handoff)
        self.assertEqual(h.handoff_kind, "discover")
        self.assertIsNone(h.outcome)

    def test_valid_handoff_reconsider_verdict(self):
        """Reconsider verdict: design_options may be empty, recommended_option may be None."""
        ps = _plan_seeds(
            design_options=[],
            recommended_option_id=None,
            recommended_option_rationale="No viable approach found -- further research needed",
        )
        h = _handoff(
            verdict="Reconsider",
            overall_fit="Misfit",
            plan_seeds=ps,
        )
        self.assertIsInstance(h, hs.Handoff)
        self.assertEqual(h.discovery_block.verdict, "Reconsider")

    def test_valid_handoff_override_recorded(self):
        """Strained fit with override_recorded=True permits non-Reconsider verdict."""
        db = _discovery_block(
            verdict="Promising with caveats",
            overall_fit="Strained",
            effort_estimate="Low",
            override_recorded=True,
        )
        h = _handoff(discovery_block=db)
        self.assertIsInstance(h, hs.Handoff)
        self.assertTrue(h.discovery_block.override_recorded)


# ---------------------------------------------------------------------------
# TestHandoffKindAndSpec -- 2 cases.
# ---------------------------------------------------------------------------


class TestHandoffKindAndSpec(unittest.TestCase):
    """Reject wrong handoff_kind or spec_type_hint."""

    def test_reject_handoff_kind_not_discover(self):
        """handoff_kind != 'discover' is rejected."""
        with self.assertRaises(ValueError) as ctx:
            _handoff(handoff_kind="research")
        self.assertIn("handoff_kind", str(ctx.exception))
        self.assertIn("discover", str(ctx.exception))

    def test_reject_spec_type_hint_other_than_greenfield_feature(self):
        """spec_type_hint other than 'greenfield_feature' is rejected."""
        with self.assertRaises(ValueError) as ctx:
            _handoff(spec_seeds=_spec_seeds(spec_type_hint="bug_fix"))
        self.assertIn("greenfield_feature", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestDesignOptions -- 3 cases.
# ---------------------------------------------------------------------------


class TestDesignOptions(unittest.TestCase):
    """DesignOption validation: letter prefix, duplicates, recommended_option_id mismatch."""

    def test_reject_design_option_letter_prefix_in_name(self):
        """DesignOption.name starting with 'A:' is rejected."""
        with self.assertRaises(ValueError) as ctx:
            _design_option(id="A", name="A: PostgreSQL table")
        self.assertIn("letter prefix", str(ctx.exception))

    def test_reject_duplicate_design_option_ids(self):
        """PlanSeeds with two DesignOptions sharing the same id is rejected."""
        opts = [_design_option("A"), _design_option("A", name="Alternate approach")]
        with self.assertRaises(ValueError) as ctx:
            _plan_seeds(design_options=opts)
        self.assertIn("duplicate", str(ctx.exception).lower())

    def test_reject_recommended_option_id_not_in_design_options(self):
        """recommended_option_id not matching any design_options[].id is rejected."""
        opts = [_design_option("A")]
        ps = _plan_seeds(design_options=opts, recommended_option_id="B")
        with self.assertRaises(ValueError) as ctx:
            _handoff(plan_seeds=ps)
        self.assertIn("recommended_option_id", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestComplexityEnum -- 2 cases.
# ---------------------------------------------------------------------------


class TestComplexityEnum(unittest.TestCase):
    """Reject invalid enum values for complexity and overall_fit."""

    def test_reject_invalid_complexity_enum_medium_not_med(self):
        """Complexity.changes='Medium' is rejected -- must be 'Med'."""
        with self.assertRaises(ValueError) as ctx:
            _complexity(changes="Medium")
        self.assertIn("Med", str(ctx.exception))

    def test_reject_invalid_overall_fit_enum(self):
        """DiscoveryBlock.overall_fit with an invalid value is rejected."""
        with self.assertRaises(ValueError) as ctx:
            _discovery_block(overall_fit="Excellent")
        self.assertIn("overall_fit", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestDMirror -- 2 cases.
# ---------------------------------------------------------------------------


class TestDMirror(unittest.TestCase):
    """D-mirror: verdict-flip gate enforced at DiscoveryBlock level."""

    def test_reject_verdict_not_reconsider_when_strained_no_override(self):
        """Strained fit without override_recorded and non-Reconsider verdict is rejected."""
        with self.assertRaises(ValueError) as ctx:
            _discovery_block(
                verdict="Worth pursuing",
                overall_fit="Strained",
                effort_estimate="Low",
                override_recorded=False,
            )
        self.assertIn("Reconsider", str(ctx.exception))

    def test_accept_verdict_not_reconsider_when_strained_with_override(self):
        """Strained fit WITH override_recorded=True permits non-Reconsider verdict."""
        db = _discovery_block(
            verdict="Worth pursuing",
            overall_fit="Strained",
            effort_estimate="Low",
            override_recorded=True,
        )
        self.assertEqual(db.verdict, "Worth pursuing")


# ---------------------------------------------------------------------------
# TestGMirror -- 1 case.
# ---------------------------------------------------------------------------


class TestGMirror(unittest.TestCase):
    """G-mirror: recommended_option_rationale must cite internal paths."""

    def test_reject_recommended_rationale_missing_internal_path_cite_when_internal_prior_art_exists(self):
        """When cited_canonical_patterns has internal entries, rationale must cite those paths."""
        internal_cp = _cited_pattern_internal()
        # Rationale does not contain the internal: source path.
        # G-mirror fires at PlanSeeds construction time (the violation is detectable then).
        with self.assertRaises(ValueError) as ctx:
            _plan_seeds(
                cited_canonical_patterns=[internal_cp],
                recommended_option_rationale="Build new append-only table without extending anything",
            )
        self.assertIn("internal:", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestInternalEquivalence -- 1 case.
# ---------------------------------------------------------------------------


class TestInternalEquivalence(unittest.TestCase):
    """CitedPattern.is_internal must match source prefix."""

    def test_reject_is_internal_true_with_non_internal_source_prefix(self):
        """is_internal=True with a non 'internal:' source is rejected."""
        with self.assertRaises(ValueError) as ctx:
            hs.CitedPattern(
                reference="SomeLib",
                kind="library",
                source="https://example.com/lib",
                relevance="Used for X",
                is_internal=True,
            )
        self.assertIn("is_internal", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestComplexityDerivation -- 1 case.
# ---------------------------------------------------------------------------


class TestComplexityDerivation(unittest.TestCase):
    """Complexity.changes must match derivation from effort_estimate."""

    def test_reject_complexity_changes_value_inconsistent_with_effort_estimate(self):
        """complexity.changes inconsistent with effort_estimate is rejected."""
        # effort_estimate=Medium -> expected changes=Med; supplying High is wrong.
        c = _complexity(changes="High", risk="Med", verify_cost="Low")
        with self.assertRaises(ValueError) as ctx:
            _plan_seeds(
                complexity=c,
                effort_estimate="Medium",
                overall_fit="Acceptable",
                derisk_count=1,
            )
        self.assertIn("changes", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestOutcome -- 6 cases.
# ---------------------------------------------------------------------------


class TestOutcome(unittest.TestCase):
    """Outcome computed-field validation."""

    def _make_worth_pursuing_handoff(self):
        """Build a valid worth-pursuing Handoff for outcome attachment tests."""
        return _handoff(verdict="Worth pursuing", overall_fit="Good", effort_estimate="Low")

    def test_accept_outcome_high_confidence_full_match(self):
        """Outcome with verdict_held + all match flags True -> HIGH confidence."""
        h = self._make_worth_pursuing_handoff()
        out = _outcome(
            design_option_shipped_id="A",
            matches_recommendation=True,
            build_vs_buy_actual="Build",
            matches_build_vs_buy_recommendation=True,
            internal_extension_followed=None,
            verdict_held=True,
            confidence_grade="HIGH",
        )
        h2 = hs.Handoff(
            schema_version=h.schema_version,
            handoff_kind=h.handoff_kind,
            report_path=h.report_path,
            discover_completed_at=h.discover_completed_at,
            intent=h.intent,
            spec_seeds=h.spec_seeds,
            plan_seeds=h.plan_seeds,
            discovery_block=h.discovery_block,
            downstream_links=h.downstream_links,
            outcome=out,
        )
        self.assertEqual(h2.outcome.confidence_grade, "HIGH")

    def test_accept_outcome_medium_confidence_design_diverged(self):
        """Outcome with verdict_held=True but matches_recommendation=False -> MEDIUM."""
        h = self._make_worth_pursuing_handoff()
        out = _outcome(
            design_option_shipped_id="B",
            design_option_shipped_summary="Used alternate approach B",
            matches_recommendation=False,
            build_vs_buy_actual="Build",
            matches_build_vs_buy_recommendation=True,
            internal_extension_followed=None,
            verdict_held=True,
            confidence_grade="MEDIUM",
            delta_from_recommendation="Chose option B due to latency concerns",
        )
        h2 = hs.Handoff(
            schema_version=h.schema_version,
            handoff_kind=h.handoff_kind,
            report_path=h.report_path,
            discover_completed_at=h.discover_completed_at,
            intent=h.intent,
            spec_seeds=h.spec_seeds,
            plan_seeds=h.plan_seeds,
            discovery_block=h.discovery_block,
            downstream_links=h.downstream_links,
            outcome=out,
        )
        self.assertEqual(h2.outcome.confidence_grade, "MEDIUM")

    def test_accept_outcome_low_confidence_verdict_reversed(self):
        """Outcome with verdict_held=False (Reconsider verdict but feature shipped anyway) -> LOW.

        Exercises the Reconsider-shipped path: discovery said Reconsider but a user override
        caused the feature to ship.  shipped_commit_sha is non-None, so verdict_held=False.
        Reconsider handoff has non-empty design_options so there is a shipped id to match against.
        Because recommended_option_id is None (Reconsider), any shipped design id != None,
        making matches_recommendation=False.
        """
        # Reconsider with design_options non-empty: Good fit permits Reconsider without D-mirror.
        # Use overall_fit="Good" + effort_estimate="Low" -- D-mirror only mandates Reconsider for
        # Strained/Misfit/Major-refactor; Good fit may also yield Reconsider by analyst judgment.
        ps = _plan_seeds(
            design_options=[_design_option("A")],
            recommended_option_id=None,
            recommended_option_rationale="No viable approach -- further research needed",
        )
        h = _handoff(
            verdict="Reconsider",
            overall_fit="Good",
            effort_estimate="Low",
            plan_seeds=ps,
        )
        out = _outcome(
            design_option_shipped_id="A",
            design_option_shipped_summary="Option A shipped despite Reconsider verdict -- user override",
            # recommended_option_id is None; A != None -> False.
            matches_recommendation=False,
            build_vs_buy_actual="Build",
            # plan_seeds.build_vs_buy.recommendation defaults to "Build".
            matches_build_vs_buy_recommendation=True,
            internal_extension_followed=None,
            verdict_held=False,
            shipped_commit_sha="abc1234abc1234",
            confidence_grade="LOW",
            delta_from_recommendation="shipped option A despite Reconsider verdict -- user override",
        )
        h2 = hs.Handoff(
            schema_version=h.schema_version,
            handoff_kind=h.handoff_kind,
            report_path=h.report_path,
            discover_completed_at=h.discover_completed_at,
            intent=h.intent,
            spec_seeds=h.spec_seeds,
            plan_seeds=h.plan_seeds,
            discovery_block=h.discovery_block,
            downstream_links=h.downstream_links,
            outcome=out,
        )
        self.assertFalse(h2.outcome.verdict_held)
        self.assertEqual(h2.outcome.confidence_grade, "LOW")

    def test_accept_outcome_medium_confidence_reconsider_correctly_not_shipped(self):
        """Outcome with verdict=Reconsider and feature not shipped -> verdict_held=True -> MEDIUM.

        When verdict=Reconsider and shipped_commit_sha is None, the Reconsider verdict held
        (feature was correctly abandoned).  Both match flags are False (no option shipped,
        no build-vs-buy executed), but verdict_held=True -> MEDIUM not LOW.
        """
        ps = _plan_seeds(
            design_options=[],
            recommended_option_id=None,
            recommended_option_rationale="No viable approach -- further research needed",
        )
        h = _handoff(
            verdict="Reconsider",
            overall_fit="Misfit",
            plan_seeds=ps,
        )
        out = _outcome(
            design_option_shipped_id="none",
            design_option_shipped_summary="Feature was abandoned post-discovery",
            matches_recommendation=False,
            build_vs_buy_actual="none",
            matches_build_vs_buy_recommendation=False,
            internal_extension_followed=None,
            verdict_held=True,
            shipped_commit_sha=None,
            confidence_grade="MEDIUM",
            delta_from_recommendation="Feature abandoned -- Reconsider was correct",
        )
        h2 = hs.Handoff(
            schema_version=h.schema_version,
            handoff_kind=h.handoff_kind,
            report_path=h.report_path,
            discover_completed_at=h.discover_completed_at,
            intent=h.intent,
            spec_seeds=h.spec_seeds,
            plan_seeds=h.plan_seeds,
            discovery_block=h.discovery_block,
            downstream_links=h.downstream_links,
            outcome=out,
        )
        self.assertEqual(h2.outcome.confidence_grade, "MEDIUM")
        self.assertTrue(h2.outcome.verdict_held)

    def test_accept_outcome_low_confidence_verdict_was_worth_pursuing_but_shipped_none(self):
        """Worth pursuing verdict but design_option_shipped_id='none' -> verdict_held=False -> LOW."""
        h = self._make_worth_pursuing_handoff()
        out = _outcome(
            design_option_shipped_id="none",
            design_option_shipped_summary="Feature abandoned after discovery",
            matches_recommendation=False,
            build_vs_buy_actual="none",
            matches_build_vs_buy_recommendation=False,
            internal_extension_followed=None,
            verdict_held=False,
            confidence_grade="LOW",
            delta_from_recommendation="Feature cancelled due to external constraints",
        )
        h2 = hs.Handoff(
            schema_version=h.schema_version,
            handoff_kind=h.handoff_kind,
            report_path=h.report_path,
            discover_completed_at=h.discover_completed_at,
            intent=h.intent,
            spec_seeds=h.spec_seeds,
            plan_seeds=h.plan_seeds,
            discovery_block=h.discovery_block,
            downstream_links=h.downstream_links,
            outcome=out,
        )
        self.assertEqual(h2.outcome.confidence_grade, "LOW")
        self.assertFalse(h2.outcome.verdict_held)

    def test_accept_outcome_low_confidence_promising_with_caveats_abandoned(self):
        """Promising with caveats verdict + design_option_shipped_id='none' -> verdict_held=False -> LOW.

        Both 'Worth pursuing' and 'Promising with caveats' verdicts imply intent-to-ship;
        abandonment of either signals verdict-not-held.  The verdict_held derivation extends to
        both proceeding-verdicts symmetrically (see handoff_schema.py Outcome._validate_computed_fields).
        """
        # Build a Promising-with-caveats handoff: needs override_recorded=True because
        # overall_fit="Strained" triggers D-mirror (must be Reconsider unless override).
        db = _discovery_block(
            verdict="Promising with caveats",
            overall_fit="Strained",
            effort_estimate="Low",
            override_recorded=True,
        )
        h = _handoff(discovery_block=db)
        out = _outcome(
            design_option_shipped_id="none",
            design_option_shipped_summary="Feature abandoned after discovery despite caveated promise",
            matches_recommendation=False,
            build_vs_buy_actual="none",
            matches_build_vs_buy_recommendation=False,
            internal_extension_followed=None,
            verdict_held=False,
            confidence_grade="LOW",
            delta_from_recommendation="Feature cancelled -- verdict was Promising with caveats but feature dropped",
        )
        h2 = hs.Handoff(
            schema_version=h.schema_version,
            handoff_kind=h.handoff_kind,
            report_path=h.report_path,
            discover_completed_at=h.discover_completed_at,
            intent=h.intent,
            spec_seeds=h.spec_seeds,
            plan_seeds=h.plan_seeds,
            discovery_block=h.discovery_block,
            downstream_links=h.downstream_links,
            outcome=out,
        )
        self.assertFalse(h2.outcome.verdict_held)
        self.assertEqual(h2.outcome.confidence_grade, "LOW")

    def test_reject_outcome_delta_null_when_match_flag_false(self):
        """delta_from_recommendation must be non-null when matches_recommendation=False."""
        with self.assertRaises(ValueError) as ctx:
            _outcome(
                design_option_shipped_id="B",
                matches_recommendation=False,
                build_vs_buy_actual="Build",
                matches_build_vs_buy_recommendation=True,
                internal_extension_followed=None,
                verdict_held=True,
                confidence_grade="MEDIUM",
                delta_from_recommendation=None,  # must be provided
            )
        self.assertIn("delta_from_recommendation", str(ctx.exception))

    def test_reject_outcome_shipped_sha_when_shipped_id_is_none(self):
        """design_option_shipped_id='none' + shipped_commit_sha non-None is rejected as contradictory."""
        # When shipped_id='none', matches_recommendation is False (recommended_option_id='A' != 'none'),
        # so delta_from_recommendation must be non-empty per existing validator.
        # Set that correctly so only the new SHA-contradiction validator fires.
        with self.assertRaises(ValueError) as ctx:
            _outcome(
                design_option_shipped_id="none",
                design_option_shipped_summary="Feature abandoned post-discovery",
                matches_recommendation=False,
                build_vs_buy_actual="none",
                matches_build_vs_buy_recommendation=False,
                internal_extension_followed=None,
                verdict_held=True,
                shipped_commit_sha="abc1234abc1234",
                confidence_grade="MEDIUM",
                delta_from_recommendation="Feature abandoned -- Reconsider was correct",
            )
        self.assertIn("design_option_shipped_id='none'", str(ctx.exception))
        self.assertIn("SHA is contradictory", str(ctx.exception))

    def test_reject_outcome_internal_extension_followed_non_null_when_no_internal_prior_art(self):
        """internal_extension_followed must be None when no internal prior art exists."""
        h = self._make_worth_pursuing_handoff()
        # plan_seeds has no internal cited patterns (external only by default).
        out = _outcome(
            internal_extension_followed=True,  # should be None
            confidence_grade="HIGH",
        )
        with self.assertRaises(ValueError) as ctx:
            hs.Handoff(
                schema_version=h.schema_version,
                handoff_kind=h.handoff_kind,
                report_path=h.report_path,
                discover_completed_at=h.discover_completed_at,
                intent=h.intent,
                spec_seeds=h.spec_seeds,
                plan_seeds=h.plan_seeds,
                discovery_block=h.discovery_block,
                downstream_links=h.downstream_links,
                outcome=out,
            )
        self.assertIn("internal_extension_followed", str(ctx.exception))

    def test_reject_outcome_internal_extension_followed_null_when_internal_prior_art_exists(self):
        """internal_extension_followed must be True/False when internal prior art exists."""
        internal_cp = _cited_pattern_internal()
        ps = _plan_seeds(
            cited_canonical_patterns=[internal_cp],
            recommended_option_rationale=(
                "Extend internal:src/db/base_repository.py with audit log support"
            ),
        )
        h = _handoff(plan_seeds=ps)
        out = _outcome(
            internal_extension_followed=None,  # should be True or False
            confidence_grade="HIGH",
        )
        with self.assertRaises(ValueError) as ctx:
            hs.Handoff(
                schema_version=h.schema_version,
                handoff_kind=h.handoff_kind,
                report_path=h.report_path,
                discover_completed_at=h.discover_completed_at,
                intent=h.intent,
                spec_seeds=h.spec_seeds,
                plan_seeds=h.plan_seeds,
                discovery_block=h.discovery_block,
                downstream_links=h.downstream_links,
                outcome=out,
            )
        self.assertIn("internal_extension_followed", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestModuleLevelHelpers -- validate predicates independently.
# ---------------------------------------------------------------------------


class TestModuleLevelHelpers(unittest.TestCase):
    """Unit tests for module-level helper functions."""

    def test_compute_confidence_grade_high(self):
        grade = hs.compute_confidence_grade(
            verdict_held=True,
            matches_recommendation=True,
            matches_build_vs_buy_recommendation=True,
            internal_extension_followed=None,
        )
        self.assertEqual(grade, "HIGH")

    def test_compute_confidence_grade_high_with_true_internal(self):
        grade = hs.compute_confidence_grade(
            verdict_held=True,
            matches_recommendation=True,
            matches_build_vs_buy_recommendation=True,
            internal_extension_followed=True,
        )
        self.assertEqual(grade, "HIGH")

    def test_compute_confidence_grade_medium_one_mismatch(self):
        grade = hs.compute_confidence_grade(
            verdict_held=True,
            matches_recommendation=False,
            matches_build_vs_buy_recommendation=True,
            internal_extension_followed=None,
        )
        self.assertEqual(grade, "MEDIUM")

    def test_compute_confidence_grade_low_verdict_not_held(self):
        grade = hs.compute_confidence_grade(
            verdict_held=False,
            matches_recommendation=True,
            matches_build_vs_buy_recommendation=True,
            internal_extension_followed=None,
        )
        self.assertEqual(grade, "LOW")

    def test_compute_complexity_changes_mapping(self):
        self.assertEqual(hs._compute_complexity_changes("Low"), "Low")
        self.assertEqual(hs._compute_complexity_changes("Medium"), "Med")
        self.assertEqual(hs._compute_complexity_changes("High"), "High")
        self.assertEqual(hs._compute_complexity_changes("Major refactor required"), "High")

    def test_compute_complexity_risk_mapping(self):
        self.assertEqual(hs._compute_complexity_risk("Good"), "Low")
        self.assertEqual(hs._compute_complexity_risk("Acceptable"), "Med")
        self.assertEqual(hs._compute_complexity_risk("Strained"), "High")
        self.assertEqual(hs._compute_complexity_risk("Misfit"), "High")

    def test_compute_complexity_verify_cost_mapping(self):
        self.assertEqual(hs._compute_complexity_verify_cost(0), "Low")
        self.assertEqual(hs._compute_complexity_verify_cost(2), "Low")
        self.assertEqual(hs._compute_complexity_verify_cost(3), "Med")
        self.assertEqual(hs._compute_complexity_verify_cost(5), "Med")
        self.assertEqual(hs._compute_complexity_verify_cost(6), "High")

    def test_is_strained_or_misfit(self):
        self.assertTrue(hs._is_strained_or_misfit("Strained", "Low"))
        self.assertTrue(hs._is_strained_or_misfit("Misfit", "High"))
        self.assertTrue(hs._is_strained_or_misfit("Good", "Major refactor required"))
        self.assertFalse(hs._is_strained_or_misfit("Good", "Low"))
        self.assertFalse(hs._is_strained_or_misfit("Acceptable", "High"))

    def test_has_internal_prior_art(self):
        ext = _cited_pattern_external()
        internal = _cited_pattern_internal()
        self.assertFalse(hs._has_internal_prior_art([ext]))
        self.assertTrue(hs._has_internal_prior_art([internal]))
        self.assertTrue(hs._has_internal_prior_art([ext, internal]))

    def test_rationale_cites_internal(self):
        internal = _cited_pattern_internal()
        self.assertTrue(
            hs._rationale_cites_internal(
                "Extend internal:src/db/base_repository.py with new writes",
                [internal],
            )
        )
        self.assertFalse(
            hs._rationale_cites_internal(
                "Build entirely new table without reusing existing code",
                [internal],
            )
        )


# ---------------------------------------------------------------------------
# TestDimensionRecord -- edge cases.
# ---------------------------------------------------------------------------


class TestDimensionRecord(unittest.TestCase):
    """DimensionRecord validation."""

    def test_valid_clear_with_value(self):
        dr = hs.DimensionRecord(state="Clear", turns=3, value="some text")
        self.assertEqual(dr.state, "Clear")

    def test_valid_missing_with_none_value(self):
        dr = hs.DimensionRecord(state="Missing", turns=0, value=None)
        self.assertIsNone(dr.value)

    def test_reject_clear_with_none_value(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DimensionRecord(state="Clear", turns=1, value=None)
        self.assertIn("value", str(ctx.exception))

    def test_reject_negative_turns(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DimensionRecord(state="Clear", turns=-1, value="text")
        self.assertIn("turns", str(ctx.exception))

    def test_reject_invalid_state_enum(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DimensionRecord(state="Unknown", turns=1, value="text")
        self.assertIn("state", str(ctx.exception))

    def test_reject_dimension_record_value_empty_string_when_clear(self):
        """DimensionRecord.value='' is rejected when state is Clear or Partial."""
        with self.assertRaises(ValueError) as ctx:
            hs.DimensionRecord(state="Clear", turns=1, value="")
        self.assertIn("value", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestConstraintValidation -- Gap A conditional requireds.
# ---------------------------------------------------------------------------


class TestConstraintValidation(unittest.TestCase):
    """Constraint kind conditional required fields."""

    def test_nfr_requires_quantifier(self):
        with self.assertRaises(ValueError) as ctx:
            hs.Constraint(kind="nfr", content="Latency SLA")
        self.assertIn("quantifier", str(ctx.exception))

    def test_constitution_anchor_requires_constitution_ref(self):
        with self.assertRaises(ValueError) as ctx:
            hs.Constraint(kind="constitution_anchor", content="Follow SOLID")
        self.assertIn("constitution_ref", str(ctx.exception))

    def test_external_system_requires_protocol_or_contract_doc_ref(self):
        with self.assertRaises(ValueError) as ctx:
            hs.Constraint(kind="external_system", content="REST API integration")
        self.assertIn("protocol", str(ctx.exception).lower())

    def test_external_system_accepts_contract_doc_ref_without_protocol(self):
        c = hs.Constraint(
            kind="external_system",
            content="REST API integration",
            contract_doc_ref="docs/api-contract.md",
        )
        self.assertEqual(c.kind, "external_system")

    def test_reject_invalid_constraint_kind(self):
        with self.assertRaises(ValueError) as ctx:
            hs.Constraint(kind="use", content="Use this library")
        self.assertIn("kind", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestVerbatimPrompt — Step 1 (18-SCOPE-FIDELITY-AND-PROMPT-INTAKE-PLAN.md)
# Tests for Intent.verbatim_prompt: validation, round-trip, back-compat.
# ---------------------------------------------------------------------------


class TestVerbatimPrompt(unittest.TestCase):
    """Tests for Intent.verbatim_prompt field added in discover schema v1.1."""

    # --- Intent.verbatim_prompt field-level validation ---

    def test_verbatim_prompt_none_tolerated(self):
        """Intent with verbatim_prompt=None (default) does not raise."""
        i = _intent()  # uses default verbatim_prompt=None
        self.assertIsNone(i.verbatim_prompt)

    def test_verbatim_prompt_nonempty_accepted(self):
        """Intent with a non-empty verbatim_prompt is accepted."""
        full_prompt = (
            "Audit log persistence. "
            "We should also track actor identity and make events queryable by resource ID."
        )
        i = hs.Intent(
            feature_concept="Audit log persistence",
            topic="audit-log-persistence",
            topic_slug="audit-log-persistence",
            verbatim_prompt=full_prompt,
        )
        self.assertEqual(i.verbatim_prompt, full_prompt)

    def test_verbatim_prompt_empty_string_rejected(self):
        """Intent with verbatim_prompt='' raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            hs.Intent(
                feature_concept="Audit log persistence",
                topic="audit-log-persistence",
                topic_slug="audit-log-persistence",
                verbatim_prompt="",
            )
        self.assertIn("verbatim_prompt", str(ctx.exception))

    def test_verbatim_prompt_whitespace_only_rejected(self):
        """Intent with verbatim_prompt='   ' (whitespace only) raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            hs.Intent(
                feature_concept="Audit log persistence",
                topic="audit-log-persistence",
                topic_slug="audit-log-persistence",
                verbatim_prompt="   ",
            )
        self.assertIn("verbatim_prompt", str(ctx.exception))

    # --- Round-trip: full prompt with "we should also" tail ---

    def test_verbatim_prompt_carried_into_handoff_distinct_from_topic(self):
        """verbatim_prompt survives Handoff construction unchanged.

        The full prompt contains 'we should also ...' additions that the topic
        field would not carry. Assert intent.verbatim_prompt equals the full
        prompt, not the paraphrased topic.
        """
        full_prompt = (
            "Audit log persistence. "
            "We should also track actor identity and make events queryable by resource ID."
        )
        topic_only = "Audit log persistence."  # shorter — what set-topic stores

        intent_with_full_prompt = hs.Intent(
            feature_concept="Audit log persistence with actor tracking",
            topic="audit-log-persistence",
            topic_slug="audit-log-persistence",
            verbatim_prompt=full_prompt,
        )
        h = _handoff(intent=intent_with_full_prompt)
        self.assertEqual(h.intent.verbatim_prompt, full_prompt)
        self.assertNotEqual(h.intent.verbatim_prompt, topic_only)

    # --- Back-compat: v1.0 handoff dict loads without verbatim_prompt ---

    def test_back_compat_v1_0_intent_loads_without_verbatim_prompt(self):
        """An Intent constructed without verbatim_prompt (pre-v1.1) loads without error.

        Simulates _dict_to_dataclass reconstructing a pre-v1.1 handoff.json
        that lacks the verbatim_prompt key. The Intent must tolerate the absent
        field (Optional[str] = None default).
        """
        i = hs.Intent(
            feature_concept="Old feature concept",
            topic="old-topic",
            topic_slug="old-topic",
            # verbatim_prompt intentionally omitted — default None
        )
        self.assertIsNone(i.verbatim_prompt)

    def test_schema_version_1_0_accepted(self):
        """schema_version='1.0' is accepted (back-compat — frozenset allows both 1.0 and 1.1)."""
        h = _handoff(schema_version="1.0")
        self.assertEqual(h.schema_version, "1.0")

    def test_schema_version_1_1_accepted(self):
        """schema_version='1.1' is the current version and must be accepted."""
        h = _handoff(schema_version="1.1")
        self.assertEqual(h.schema_version, "1.1")

    def test_schema_version_2_0_rejected(self):
        """schema_version='2.0' is rejected (outside the frozenset)."""
        with self.assertRaises(ValueError) as ctx:
            _handoff(schema_version="2.0")
        self.assertIn("schema_version", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
