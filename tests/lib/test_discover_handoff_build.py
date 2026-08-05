"""Pure-function tests for src/devforge/lib/_discover/_handoff_build.py.

Covers all 9 cases specified in 03-DISCOVER-HANDOFF-PLAN.md:
- test_build_handoff_worth_pursuing_full
- test_build_handoff_reconsider_minimal
- test_build_handoff_override_recorded
- test_build_internal_prior_art_flags_propagate
- test_build_recommended_option_id_resolves_from_name
- test_build_asdict_strips_internal_underscore_fields
- test_build_constraints_lifts_constitution_constraints_with_constitution_anchor_kind
- test_build_risks_lifts_derisk_plan_and_blockers
- test_build_open_questions_lifts_uncertainties_and_gaps

No filesystem I/O. All functions are pure.
Stdlib only. No third-party dependencies.
"""

import sys
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Import path setup.
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_LIB = _HERE.parent.parent / "src" / "devforge" / "lib"
sys.path.insert(0, str(_LIB / "_discover"))
sys.path.insert(0, str(_LIB))

from _discover import handoff_schema as hs  # noqa: E402
from _discover._handoff_build import (  # noqa: E402
    _asdict_handoff,
    _build_affected_areas,
    _build_constraints,
    _build_handoff_from_state,
    _build_open_questions,
    _build_risks,
)


# ---------------------------------------------------------------------------
# Fixture helpers.
# ---------------------------------------------------------------------------


def _make_memo(
    topic="Audit Log Persistence",
    topic_slug="audit-log-persistence",
    date="2026-05-20",
    dims=None,
    references=None,
    gaps=None,
    override_recorded=False,
):
    """Build a realistic memo dict mimicking discover-scope.json shape."""
    if dims is None:
        dims = {
            "functional_scope": {"value": "Persist structured audit events to durable storage", "state": "Clear", "turns": 2},
            "users": {"value": "Backend services writing audit events", "state": "Clear", "turns": 1},
            "inputs_outputs": {"value": "AuditEvent struct -> PostgreSQL audit_log table", "state": "Clear", "turns": 1},
            "integration_points": {"value": "ORM layer, DB connection pool", "state": "Clear", "turns": 1},
            "constraints": {"value": "Writes must complete within 100ms p99", "state": "Clear", "turns": 1},
            "non_goals": {"value": "No real-time alerting on audit events", "state": "Clear", "turns": 1},
            "success_criteria": {"value": "All state changes logged with timestamp + actor", "state": "Clear", "turns": 1},
            "edge_cases": {"value": "DB down: queue audit events in memory, retry on reconnect", "state": "Clear", "turns": 1},
        }
    return {
        "topic": topic,
        "topic_slug": topic_slug,
        "date": date,
        "dimensions": dims,
        "references": references or [],
        "gaps": gaps or [],
        "override_recorded": override_recorded,
        "conflicts": [],
    }


def _make_report(
    verdict="Worth pursuing",
    overall_fit="Good",
    effort_estimate="Low",
    design_options=None,
    recommended_option=None,
    prior_art=None,
    integration_touchpoints=None,
    fit_assessments=None,
    build_vs_buy=None,
    derisk_plan=None,
    constitution_constraints=None,
    open_uncertainties=None,
    date="2026-05-20",
    topic_slug="audit-log-persistence",
    summary="Detailed audit log persistence system",
    fit_rationale="Straightforward extension of existing ORM layer",
):
    """Build a realistic report dict mimicking discover-report.json shape."""
    if design_options is None:
        design_options = [
            {
                "name": "PostgreSQL append-only table",
                "shape": "Add audit_log table via ORM",
                "pros": ["Simple", "ACID"],
                "cons": ["Single DB dependency"],
                "complexity": "Low",
            }
        ]
    if recommended_option is None and verdict != "Reconsider":
        recommended_option = {
            "name": "PostgreSQL append-only table",
            "rationale": "Lowest complexity; existing ORM already supports it",
        }
    return {
        "topic": "Audit Log Persistence",
        "date": date,
        "topic_slug": topic_slug,
        "summary": summary,
        "prior_art": prior_art or [],
        "integration_touchpoints": integration_touchpoints or [
            {"name": "ORM layer", "module_path": "src/db/orm.py", "reason": "Audit writes go through ORM"}
        ],
        "fit_assessments": fit_assessments or [],
        "overall_fit": overall_fit,
        "effort_estimate": effort_estimate,
        "fit_rationale": fit_rationale,
        "design_options": design_options,
        "recommended_option": recommended_option,
        "build_vs_buy": build_vs_buy or {
            "recommendation": "Build",
            "build": "Extend ORM with audit_log table",
            "buy": "Use third-party audit library",
            "reasoning": "Existing ORM infra minimizes build cost",
        },
        "derisk_plan": derisk_plan or [],
        "constitution_constraints": constitution_constraints or [],
        "verdict": verdict,
        "recommendation": None,
        "next_step_text": None,
        "open_uncertainties": open_uncertainties or [],
    }


# ---------------------------------------------------------------------------
# 68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 3: report_md_path is now a
# REQUIRED third argument to _build_handoff_from_state (no internal
# "discover/<date>-<slug>.md" fallback). This constant is a placeholder
# value for the many tests below that exercise unrelated fields and do not
# care about the exact report_path -- see TestBuildHandoffReportPath for
# the tests that DO pin report_path's exact behavior.
# ---------------------------------------------------------------------------

_DEFAULT_REPORT_MD_PATH = "specs/001-test-feature/discovery-report.md"


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


class TestBuildHandoffWorthPursuingFull(unittest.TestCase):
    """All dimensions clear, design_options=3, verdict=Worth pursuing -> fully-populated Handoff."""

    def setUp(self):
        self.memo = _make_memo()
        self.report = _make_report(
            verdict="Worth pursuing",
            overall_fit="Good",
            effort_estimate="Low",
            design_options=[
                {"name": "PostgreSQL append-only table", "shape": "Add ORM table", "pros": ["Simple"], "cons": ["Single DB"], "complexity": "Low"},
                {"name": "External event store", "shape": "Use Kafka", "pros": ["Scalable"], "cons": ["Extra infra"], "complexity": "High"},
                {"name": "File-based log rotation", "shape": "Write to rotating logs", "pros": ["Zero infra"], "cons": ["Hard to query"], "complexity": "Low"},
            ],
            recommended_option={"name": "PostgreSQL append-only table", "rationale": "Lowest complexity option"},
            prior_art=[
                {"reference": "SQLAlchemy", "kind": "library", "source": "https://sqlalchemy.org", "relevance": "ORM used throughout"},
            ],
            constitution_constraints=[{"rule": "SOLID principles apply", "impact": "Single responsibility"}],
            open_uncertainties=["Which PostgreSQL version is running in production?"],
            derisk_plan=["Validate DB latency under load", "Add circuit breaker for audit writes"],
        )

    def test_handoff_builds_successfully(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertIsInstance(handoff, hs.Handoff)
        self.assertEqual(handoff.handoff_kind, "discover")
        self.assertEqual(handoff.schema_version, "1.1")

    def test_intent_populated(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertEqual(handoff.intent.topic_slug, "audit-log-persistence")
        self.assertIn("audit", handoff.intent.feature_concept.lower())

    def test_three_design_options_auto_letter_ids(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        ids = [opt.id for opt in handoff.plan_seeds.design_options]
        self.assertEqual(ids, ["A", "B", "C"])

    def test_recommended_option_id_resolved(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertEqual(handoff.plan_seeds.recommended_option_id, "A")

    def test_constitution_constraint_lifted(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        kinds = {c.kind for c in handoff.spec_seeds.constraints}
        self.assertIn("constitution_anchor", kinds)

    def test_open_questions_lifted(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        texts = [q.question for q in handoff.spec_seeds.open_questions]
        self.assertTrue(any("PostgreSQL version" in t for t in texts))

    def test_two_risks_from_derisk_plan(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertEqual(len(handoff.spec_seeds.risks), 2)

    def test_discovery_block_verdict(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertEqual(handoff.discovery_block.verdict, "Worth pursuing")

    def test_outcome_is_none(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertIsNone(handoff.outcome)


class TestBuildHandoffReconsiderMinimal(unittest.TestCase):
    """Strained fit + Reconsider verdict -> empty design_options, recommended_option_id=None."""

    def setUp(self):
        self.memo = _make_memo()
        self.report = _make_report(
            verdict="Reconsider",
            overall_fit="Strained",
            effort_estimate="High",
            design_options=[],
            recommended_option=None,
            derisk_plan=["Address integration complexity first"],
            fit_rationale="Integration requires significant refactoring of ORM layer",
        )

    def test_handoff_builds_successfully(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertIsInstance(handoff, hs.Handoff)

    def test_design_options_empty(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertEqual(handoff.plan_seeds.design_options, [])

    def test_recommended_option_id_is_none(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertIsNone(handoff.plan_seeds.recommended_option_id)

    def test_complexity_derived_from_strained_high(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        # effort=High -> changes=High; fit=Strained -> risk=High; derisk_count=1 -> verify_cost=Low
        self.assertEqual(handoff.plan_seeds.complexity.changes, "High")
        self.assertEqual(handoff.plan_seeds.complexity.risk, "High")
        self.assertEqual(handoff.plan_seeds.complexity.verify_cost, "Low")

    def test_verdict_is_reconsider(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertEqual(handoff.discovery_block.verdict, "Reconsider")


class TestBuildHandoffOverrideRecorded(unittest.TestCase):
    """Misfit fit + override_recorded=True -> non-Reconsider verdict accepted."""

    def setUp(self):
        self.memo = _make_memo(override_recorded=True)
        self.report = _make_report(
            verdict="Worth pursuing",
            overall_fit="Misfit",
            effort_estimate="Low",
            design_options=[
                {"name": "Micro-adapter shim", "shape": "Thin shim layer", "pros": ["Minimal"], "cons": ["Brittle"], "complexity": "Low"},
            ],
            recommended_option={"name": "Micro-adapter shim", "rationale": "User explicitly overrode Reconsider verdict"},
        )

    def test_handoff_builds_with_override(self):
        # D-mirror: Misfit + Worth pursuing + override_recorded=True must not raise
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertIsInstance(handoff, hs.Handoff)
        self.assertTrue(handoff.discovery_block.override_recorded)
        self.assertEqual(handoff.discovery_block.verdict, "Worth pursuing")


class TestBuildInternalPriorArtFlagsPropagate(unittest.TestCase):
    """internal:<path> prior_art -> CitedPattern.is_internal=True + AffectedArea.is_internal_extension_candidate=True."""

    def setUp(self):
        self.memo = _make_memo()
        self.report = _make_report(
            verdict="Worth pursuing",
            prior_art=[
                {
                    "reference": "BaseRepository",
                    "kind": "pattern",
                    "source": "internal:src/db/base_repository.py",
                    "relevance": "Extend this for audit log writes",
                },
                {
                    "reference": "SQLAlchemy",
                    "kind": "library",
                    "source": "https://sqlalchemy.org",
                    "relevance": "ORM used throughout",
                },
            ],
            recommended_option={
                "name": "PostgreSQL append-only table",
                "rationale": "Extend existing implementation at internal:src/db/base_repository.py",
            },
        )

    def test_internal_cited_pattern_has_is_internal_true(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        patterns = handoff.plan_seeds.cited_canonical_patterns
        internal_patterns = [p for p in patterns if p.is_internal]
        self.assertEqual(len(internal_patterns), 1)
        self.assertEqual(internal_patterns[0].source, "internal:src/db/base_repository.py")

    def test_external_cited_pattern_has_is_internal_false(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        patterns = handoff.plan_seeds.cited_canonical_patterns
        external_patterns = [p for p in patterns if not p.is_internal]
        self.assertEqual(len(external_patterns), 1)

    def test_internal_prior_art_creates_affected_area_with_candidate_flag(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        areas = handoff.spec_seeds.affected_areas
        internal_areas = [a for a in areas if a.is_internal_extension_candidate]
        self.assertTrue(len(internal_areas) >= 1)
        area_names = [a.area for a in internal_areas]
        self.assertTrue(any("base_repository" in name for name in area_names))

    def test_rationale_cites_internal_path(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        rationale = handoff.plan_seeds.recommended_option_rationale
        # G-mirror: rationale must contain the full "internal:" source string.
        self.assertIn("internal:src/db/base_repository.py", rationale)


class TestBuildRecommendedOptionIdResolvesFromName(unittest.TestCase):
    """report.recommended_option.name matches one design_options[].name -> id correctly mapped to letter."""

    def setUp(self):
        self.memo = _make_memo()
        self.report = _make_report(
            verdict="Worth pursuing",
            design_options=[
                {"name": "Option Alpha", "shape": "Alpha shape", "pros": ["Fast"], "cons": ["Complex"], "complexity": "High"},
                {"name": "Option Beta", "shape": "Beta shape", "pros": ["Simple"], "cons": ["Slow"], "complexity": "Low"},
                {"name": "Option Gamma", "shape": "Gamma shape", "pros": ["Balanced"], "cons": ["Medium"], "complexity": "Med"},
            ],
            recommended_option={"name": "Option Beta", "rationale": "Best balance of simplicity"},
        )

    def test_recommended_id_is_b(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        self.assertEqual(handoff.plan_seeds.recommended_option_id, "B")

    def test_ids_assigned_in_order(self):
        handoff = _build_handoff_from_state(self.memo, self.report, _DEFAULT_REPORT_MD_PATH)
        ids = [opt.id for opt in handoff.plan_seeds.design_options]
        self.assertEqual(ids, ["A", "B", "C"])


class TestBuildAsdictStripsInternalUnderscoreFields(unittest.TestCase):
    """_asdict_handoff must strip _effort_estimate, _overall_fit, _derisk_count."""

    def test_asdict_strips_underscore_fields(self):
        memo = _make_memo()
        report = _make_report()
        handoff = _build_handoff_from_state(memo, report, _DEFAULT_REPORT_MD_PATH)
        result = _asdict_handoff(handoff)
        plan_seeds = result["plan_seeds"]
        self.assertNotIn("_effort_estimate", plan_seeds)
        self.assertNotIn("_overall_fit", plan_seeds)
        self.assertNotIn("_derisk_count", plan_seeds)

    def test_asdict_retains_public_fields(self):
        memo = _make_memo()
        report = _make_report()
        handoff = _build_handoff_from_state(memo, report, _DEFAULT_REPORT_MD_PATH)
        result = _asdict_handoff(handoff)
        plan_seeds = result["plan_seeds"]
        self.assertIn("design_options", plan_seeds)
        self.assertIn("build_vs_buy", plan_seeds)
        self.assertIn("complexity", plan_seeds)
        self.assertIn("recommended_option_id", plan_seeds)


class TestBuildConstraintsLiftsConstitutionConstraints(unittest.TestCase):
    """report.constitution_constraints -> Constraint with kind=constitution_anchor."""

    def test_constitution_constraint_kind(self):
        memo = _make_memo()
        report = _make_report(
            constitution_constraints=[
                {"rule": "No raw SQL outside repository layer", "impact": "All DB writes must go through ORM"},
                {"rule": "SOLID principles apply", "impact": "Keep audit writer single-responsibility"},
            ]
        )
        result = _build_constraints(memo, report)
        anchor_constraints = [c for c in result if c.kind == "constitution_anchor"]
        self.assertEqual(len(anchor_constraints), 2)
        contents = {c.content for c in anchor_constraints}
        self.assertIn("No raw SQL outside repository layer", contents)
        self.assertIn("SOLID principles apply", contents)

    def test_constitution_constraint_has_constitution_ref(self):
        memo = _make_memo()
        report = _make_report(
            constitution_constraints=[{"rule": "Follow SOLID", "impact": "SRP required"}]
        )
        result = _build_constraints(memo, report)
        anchor = next(c for c in result if c.kind == "constitution_anchor")
        self.assertEqual(anchor.constitution_ref, "constitution.md")

    def test_memo_constraints_dimension_becomes_nfr(self):
        memo = _make_memo()
        result = _build_constraints(memo, {})
        nfr_constraints = [c for c in result if c.kind == "nfr"]
        self.assertTrue(len(nfr_constraints) >= 1)

    def test_empty_constitution_constraints_produces_no_anchors(self):
        memo = _make_memo()
        result = _build_constraints(memo, {"constitution_constraints": []})
        anchor_constraints = [c for c in result if c.kind == "constitution_anchor"]
        self.assertEqual(len(anchor_constraints), 0)


class TestBuildRisksLiftsDeriskPlanAndBlockers(unittest.TestCase):
    """_build_risks lifts from report.derisk_plan and fit_assessments[*].blockers."""

    def test_risks_from_derisk_plan(self):
        report = _make_report(
            derisk_plan=["Validate DB latency under load", "Add circuit breaker"],
            fit_assessments=[],
        )
        risks = _build_risks(report)
        texts = {r.risk for r in risks}
        self.assertIn("Validate DB latency under load", texts)
        self.assertIn("Add circuit breaker", texts)

    def test_risks_from_fit_assessment_blockers(self):
        report = _make_report(
            derisk_plan=[],
            fit_assessments=[
                {
                    "touchpoint": "ORM layer",
                    "user_expected": "Direct write method",
                    "reality": "Async write queue needed",
                    "effort": "High",
                    "blockers": ["Async queue infrastructure missing", "No retry mechanism"],
                }
            ],
        )
        risks = _build_risks(report)
        texts = {r.risk for r in risks}
        self.assertIn("Async queue infrastructure missing", texts)
        self.assertIn("No retry mechanism", texts)

    def test_blocker_risks_have_high_likelihood_and_impact(self):
        report = _make_report(
            derisk_plan=[],
            fit_assessments=[
                {
                    "touchpoint": "DB layer",
                    "user_expected": "Simple write",
                    "reality": "Complex migration needed",
                    "effort": "High",
                    "blockers": ["Schema migration required"],
                }
            ],
        )
        risks = _build_risks(report)
        blocker_risks = [r for r in risks if r.risk == "Schema migration required"]
        self.assertEqual(len(blocker_risks), 1)
        self.assertEqual(blocker_risks[0].likelihood, "High")
        self.assertEqual(blocker_risks[0].impact, "High")

    def test_empty_derisk_and_no_blockers_produces_empty_risks(self):
        report = _make_report(derisk_plan=[], fit_assessments=[])
        risks = _build_risks(report)
        self.assertEqual(risks, [])


class TestBuildOpenQuestionsLiftsUncertaintiesAndGaps(unittest.TestCase):
    """_build_open_questions lifts from report.open_uncertainties and memo.gaps."""

    def test_uncertainties_lifted_as_non_blocking(self):
        memo = _make_memo()
        report = _make_report(open_uncertainties=["Which DB version?", "Async or sync writes?"])
        questions = _build_open_questions(memo, report)
        blocking_flags = {q.question: q.blocking for q in questions}
        self.assertFalse(blocking_flags.get("Which DB version?"))
        self.assertFalse(blocking_flags.get("Async or sync writes?"))

    def test_gaps_lifted_as_blocking(self):
        memo = _make_memo(
            gaps=[
                {"dimension": "inputs_outputs", "description": "Input schema format not agreed"},
            ]
        )
        report = _make_report(open_uncertainties=[])
        questions = _build_open_questions(memo, report)
        gap_questions = [q for q in questions if q.blocking]
        self.assertEqual(len(gap_questions), 1)
        self.assertIn("Input schema format not agreed", gap_questions[0].question)

    def test_combined_sources_produce_both(self):
        memo = _make_memo(gaps=[{"dimension": "users", "description": "User roles unclear"}])
        report = _make_report(open_uncertainties=["DB version?"])
        questions = _build_open_questions(memo, report)
        self.assertEqual(len(questions), 2)

    def test_empty_sources_produce_empty_list(self):
        memo = _make_memo(gaps=[])
        report = _make_report(open_uncertainties=[])
        questions = _build_open_questions(memo, report)
        self.assertEqual(questions, [])


# ---------------------------------------------------------------------------
# 68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 3: report_md_path is a required
# arg, embedded verbatim as Handoff.report_path -- no internal derivation,
# no "discover/<date>-<slug>.md" fallback.
# ---------------------------------------------------------------------------


class TestBuildHandoffReportPath(unittest.TestCase):
    def test_report_md_path_embedded_verbatim(self):
        memo = _make_memo()
        report = _make_report()
        handoff = _build_handoff_from_state(
            memo, report, "specs/007-widget-catalog/discovery-report.md"
        )
        self.assertEqual(
            handoff.report_path, "specs/007-widget-catalog/discovery-report.md"
        )

    def test_report_md_path_missing_raises_value_error_omitted(self):
        # No internal default -- omitting the third arg raises a
        # caller-contract ValueError, not a silent fall-back to the retired
        # discover/<date>-<slug>.md shape (and not a bare TypeError --
        # matches the research lane's identical guard, see
        # _research/_handoff_build.py::_build_handoff_from_state).
        memo = _make_memo()
        report = _make_report()
        with self.assertRaises(ValueError) as ctx:
            _build_handoff_from_state(memo, report)
        self.assertIn("report_md_path is required", str(ctx.exception))

    def test_report_md_path_missing_raises_value_error_explicit_none(self):
        # Same guard fires for an explicitly-passed falsy value, not just
        # omission -- the check is on the value, not on argument presence.
        memo = _make_memo()
        report = _make_report()
        with self.assertRaises(ValueError):
            _build_handoff_from_state(memo, report, None)
        with self.assertRaises(ValueError):
            _build_handoff_from_state(memo, report, "")

    def test_report_path_never_contains_old_layout_prefix(self):
        memo = _make_memo(date="2026-05-20", topic_slug="my-feature")
        report = _make_report(date="2026-05-20", topic_slug="my-feature")
        handoff = _build_handoff_from_state(
            memo, report, "specs/003-my-feature/discovery-report.md"
        )
        self.assertFalse(handoff.report_path.startswith("discover/"))


if __name__ == "__main__":
    unittest.main()
