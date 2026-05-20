"""CLI integration tests for discover_helper finalize-handoff + append-outcome.

Uses tmp_path (via tempfile.TemporaryDirectory) for filesystem isolation.
Round-trips through real state shape (write JSON -> invoke handler -> parse output).
Stdlib only. No third-party dependencies for the test itself; test runner is pytest.
"""

import dataclasses
import io
import json
import sys
import tempfile
import types
import unittest
import unittest.mock
from pathlib import Path

# ---------------------------------------------------------------------------
# Import path setup.
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_LIB = _HERE.parent.parent / "src" / "devforge" / "lib"
sys.path.insert(0, str(_LIB / "_discover"))
sys.path.insert(0, str(_LIB))

from _discover import handoff_schema as hs  # noqa: E402
from _discover._cmds_handoff import cmd_finalize_handoff, cmd_append_outcome  # noqa: E402
from _discover._state import _atomic_write_json, MEMO_FILE_NAME, REPORT_FILE_NAME  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers.
# ---------------------------------------------------------------------------


def _make_memo(
    topic="Audit Log Persistence",
    topic_slug="audit-log-persistence",
    date="2026-05-20",
    override_recorded=False,
):
    return {
        "topic": topic,
        "topic_slug": topic_slug,
        "date": date,
        "dimensions": {
            "functional_scope": {"value": "Persist audit events to DB", "state": "Clear", "turns": 1},
            "users": {"value": "Backend services", "state": "Clear", "turns": 1},
            "inputs_outputs": {"value": "AuditEvent -> DB", "state": "Clear", "turns": 1},
            "integration_points": {"value": "ORM layer", "state": "Clear", "turns": 1},
            "constraints": {"value": "100ms p99 write latency", "state": "Clear", "turns": 1},
            "non_goals": {"value": "No real-time alerting", "state": "Clear", "turns": 1},
            "success_criteria": {"value": "All state changes logged", "state": "Clear", "turns": 1},
            "edge_cases": {"value": "DB down: queue and retry", "state": "Clear", "turns": 1},
        },
        "references": [],
        "gaps": [],
        "override_recorded": override_recorded,
        "conflicts": [],
    }


def _make_report(
    verdict="Worth pursuing",
    overall_fit="Good",
    effort_estimate="Low",
    summary="Audit log persistence system",
    fit_rationale="Straightforward ORM extension",
    date="2026-05-20",
    topic_slug="audit-log-persistence",
    design_options=None,
    recommended_option=None,
    prior_art=None,
    build_vs_buy=None,
    derisk_plan=None,
    constitution_constraints=None,
    open_uncertainties=None,
    integration_touchpoints=None,
    fit_assessments=None,
    recommendation=None,
    next_step_text=None,
):
    if design_options is None:
        design_options = [
            {"name": "PostgreSQL table", "shape": "ORM table", "pros": ["Simple"], "cons": ["Single DB"], "complexity": "Low"}
        ]
    if recommended_option is None and verdict != "Reconsider":
        recommended_option = {"name": "PostgreSQL table", "rationale": "Lowest complexity"}
    # Default recommendation and next_step_text so cmd_verify Rule A + E pass by default.
    if recommendation is None and verdict in ("Worth pursuing", "Promising with caveats"):
        recommendation = "Use the PostgreSQL table approach as the primary design option."
    if next_step_text is None and verdict in ("Worth pursuing", "Promising with caveats"):
        next_step_text = "Run /specify audit-log-persistence"
    # Default derisk_plan with 1 entry so cmd_verify Rule F passes by default.
    if derisk_plan is None and verdict in ("Worth pursuing", "Promising with caveats"):
        derisk_plan = [{"risk": "DB unavailable during write", "mitigation": "Queue and retry with exponential back-off"}]
    return {
        "topic": "Audit Log Persistence",
        "date": date,
        "topic_slug": topic_slug,
        "summary": summary,
        "prior_art": prior_art or [],
        "integration_touchpoints": integration_touchpoints or [
            {"name": "ORM layer", "module_path": "src/db/orm.py", "reason": "Audit writes through ORM"}
        ],
        "fit_assessments": fit_assessments or [],
        "overall_fit": overall_fit,
        "effort_estimate": effort_estimate,
        "fit_rationale": fit_rationale,
        "design_options": design_options,
        "recommended_option": recommended_option,
        "build_vs_buy": build_vs_buy or {
            "recommendation": "Build",
            "build": "Extend ORM",
            "buy": "Third-party library",
            "reasoning": "ORM already in place",
        },
        "derisk_plan": derisk_plan or [],
        "constitution_constraints": constitution_constraints or [],
        "verdict": verdict,
        "recommendation": recommendation,
        "next_step_text": next_step_text,
        "open_uncertainties": open_uncertainties or [],
    }


def _write_state(devforge_dir, memo, report):
    """Write memo + report JSON files to devforge_dir."""
    dp = Path(devforge_dir)
    dp.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(memo, dp / MEMO_FILE_NAME)
    _atomic_write_json(report, dp / REPORT_FILE_NAME)


def _make_args(**kwargs):
    """Create a simple Namespace from kwargs."""
    ns = types.SimpleNamespace()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _finalize_args(devforge_dir, emit_path=None):
    return _make_args(devforge_dir=str(devforge_dir), emit_handoff_json=emit_path)


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# finalize-handoff tests.
# ---------------------------------------------------------------------------


class TestFinalizeHandoffRoundTrip(unittest.TestCase):
    """write memo+report -> finalize-handoff -> parse handoff.json -> schema-valid."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_round_trip(self):
        devforge = self.tmp / ".devforge"
        emit = self.tmp / "discover" / "2026-05-20-audit-log-persistence.handoff.json"
        memo = _make_memo()
        report = _make_report()
        _write_state(devforge, memo, report)

        args = _finalize_args(devforge, str(emit))
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0)
        self.assertTrue(emit.is_file())

        data = _load_json(emit)
        self.assertEqual(data["handoff_kind"], "discover")
        self.assertEqual(data["schema_version"], "1.0")
        self.assertIn("intent", data)
        self.assertIn("spec_seeds", data)
        self.assertIn("plan_seeds", data)
        self.assertIn("discovery_block", data)
        self.assertIsNone(data.get("outcome"))

    def test_internal_fields_stripped_from_plan_seeds(self):
        devforge = self.tmp / ".devforge"
        emit = self.tmp / "out.handoff.json"
        _write_state(devforge, _make_memo(), _make_report())
        args = _finalize_args(devforge, str(emit))
        cmd_finalize_handoff(args)
        data = _load_json(emit)
        plan_seeds = data["plan_seeds"]
        self.assertNotIn("_effort_estimate", plan_seeds)
        self.assertNotIn("_overall_fit", plan_seeds)
        self.assertNotIn("_derisk_count", plan_seeds)


class TestFinalizeHandoffDefaultTargetPath(unittest.TestCase):
    """Default target: discover/<date>-<slug>.handoff.json under CWD."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_default_path_created(self):
        import os
        devforge = self.tmp / ".devforge"
        _write_state(devforge, _make_memo(date="2026-05-20", topic_slug="my-feature"), _make_report(date="2026-05-20", topic_slug="my-feature"))
        args = _finalize_args(devforge, emit_path=None)
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmp))
            rc = cmd_finalize_handoff(args)
        finally:
            os.chdir(orig_cwd)
        self.assertEqual(rc, 0)
        expected = self.tmp / "discover" / "2026-05-20-my-feature.handoff.json"
        self.assertTrue(expected.is_file(), "default path file not found: {0}".format(expected))


class TestFinalizeHandoffCustomEmitPath(unittest.TestCase):
    """--emit-handoff-json overrides default path."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_custom_path_used(self):
        devforge = self.tmp / ".devforge"
        custom = self.tmp / "custom" / "output.handoff.json"
        _write_state(devforge, _make_memo(), _make_report())
        args = _finalize_args(devforge, str(custom))
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0)
        self.assertTrue(custom.is_file())


class TestFinalizeHandoffRejectsMissingTopicSlug(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_exits_2_when_topic_slug_missing(self):
        devforge = self.tmp / ".devforge"
        emit = self.tmp / "out.handoff.json"
        memo = _make_memo(topic_slug="")
        report = _make_report()
        _write_state(devforge, memo, report)
        args = _finalize_args(devforge, str(emit))
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 2)
        self.assertFalse(emit.is_file())


class TestFinalizeHandoffRejectsMissingVerdict(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_exits_2_when_verdict_missing(self):
        devforge = self.tmp / ".devforge"
        emit = self.tmp / "out.handoff.json"
        report = _make_report()
        report["verdict"] = None
        _write_state(devforge, _make_memo(), report)
        args = _finalize_args(devforge, str(emit))
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 2)


class TestFinalizeHandoffRejectsWhenGMirrorViolation(unittest.TestCase):
    """Internal prior-art exists but rationale doesn't cite internal path -> exit 2."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_exits_2_when_g_mirror_violation(self):
        devforge = self.tmp / ".devforge"
        emit = self.tmp / "out.handoff.json"
        report = _make_report(
            prior_art=[
                {"reference": "BaseRepo", "kind": "pattern",
                 "source": "internal:src/db/base_repo.py", "relevance": "Extend this"},
            ],
            recommended_option={
                "name": "PostgreSQL table",
                # Deliberately does NOT mention "internal:src/db/base_repo.py"
                "rationale": "Use PostgreSQL for simplicity",
            },
        )
        _write_state(devforge, _make_memo(), report)
        args = _finalize_args(devforge, str(emit))
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 2)
        self.assertFalse(emit.is_file())


# ---------------------------------------------------------------------------
# append-outcome tests.
# ---------------------------------------------------------------------------


def _make_handoff_json(tmp, verdict="Worth pursuing", has_internal=False, recommended_id="A"):
    """Build a valid handoff.json and return its path."""
    prior_art = []
    if has_internal:
        prior_art.append({
            "reference": "BaseRepo",
            "kind": "pattern",
            "source": "internal:src/db/base_repo.py",
            "relevance": "Extend this",
            "is_internal": True,
        })
    else:
        prior_art.append({
            "reference": "SQLAlchemy",
            "kind": "library",
            "source": "https://sqlalchemy.org",
            "relevance": "ORM used",
            "is_internal": False,
        })

    # Rationale must cite internal source when internal prior art exists.
    rationale = "Lowest complexity option"
    if has_internal:
        rationale = "Extend existing implementation at internal:src/db/base_repo.py"

    design_options = [{"id": recommended_id, "name": "PostgreSQL table", "shape": "ORM", "pros": ["Simple"], "cons": ["DB dep"], "complexity": "Low"}]
    if recommended_id != "A":
        # Put A first then the target letter
        design_options = [
            {"id": "A", "name": "Other option", "shape": "Other", "pros": ["Fast"], "cons": ["Complex"], "complexity": "High"},
            {"id": recommended_id, "name": "PostgreSQL table", "shape": "ORM", "pros": ["Simple"], "cons": ["DB dep"], "complexity": "Low"},
        ]

    data = {
        "schema_version": "1.0",
        "handoff_kind": "discover",
        "report_path": "discover/2026-05-20-audit-log-persistence.md",
        "discover_completed_at": "2026-05-20T10:00:00+00:00",
        "intent": {
            "feature_concept": "Audit Log Persistence",
            "topic": "Audit Log Persistence",
            "topic_slug": "audit-log-persistence",
            "scope_summary": "Persist audit events",
        },
        "spec_seeds": {
            "spec_type_hint": "greenfield_feature",
            "constraints": [],
            "affected_areas": [],
            "risks": [],
            "open_questions": [],
        },
        "plan_seeds": {
            "design_options": design_options,
            "build_vs_buy": {
                "recommendation": "Build",
                "build_path": "Extend ORM",
                "buy_path": "Third-party lib",
                "reasoning": "ORM already in place",
            },
            "cited_canonical_patterns": prior_art,
            "complexity": {"changes": "Low", "risk": "Low", "verify_cost": "Low"},
            "recommended_option_id": recommended_id,
            "recommended_option_rationale": rationale,
        },
        "discovery_block": {
            "overall_fit": "Good",
            "effort_estimate": "Low",
            "fit_rationale": "Straightforward ORM extension",
            "fit_assessments": [],
            "verdict": verdict,
            "override_recorded": False,
            "memo_dimensions": {
                "functional_scope": {"state": "Clear", "turns": 1, "value": "Persist audit events"},
                "users": {"state": "Clear", "turns": 1, "value": "Backend services"},
                "inputs_outputs": {"state": "Clear", "turns": 1, "value": "AuditEvent -> DB"},
                "integration_points": {"state": "Clear", "turns": 1, "value": "ORM layer"},
                "constraints": {"state": "Clear", "turns": 1, "value": "100ms latency"},
                "non_goals": {"state": "Clear", "turns": 1, "value": "No alerting"},
                "success_criteria": {"state": "Clear", "turns": 1, "value": "All changes logged"},
                "edge_cases": {"state": "Clear", "turns": 1, "value": "DB down: retry"},
            },
            "references": [],
            "gaps": [],
        },
        "downstream_links": {"spec_path": None, "plan_path": None, "execute_task_commit_shas": []},
        "outcome": None,
    }
    path = tmp / "handoff.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


class TestAppendOutcomeRoundTripHighConfidence(unittest.TestCase):
    """Full-match path -> HIGH grade written."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_high_confidence_full_match(self):
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing", has_internal=False, recommended_id="A")
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Shipped the PostgreSQL append-only table approach",
            build_vs_buy_actual="Build",
            shipped_commit_sha="abc1234",
            delta_from_recommendation=None,
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 0)
        data = _load_json(hpath)
        outcome = data["outcome"]
        self.assertIsNotNone(outcome)
        self.assertEqual(outcome["confidence_grade"], "HIGH")
        self.assertTrue(outcome["matches_recommendation"])
        self.assertTrue(outcome["matches_build_vs_buy_recommendation"])
        self.assertTrue(outcome["verdict_held"])
        self.assertIsNone(outcome["internal_extension_followed"])

    def test_outcome_written_atomically(self):
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing", has_internal=False)
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Shipped PostgreSQL approach",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 0)
        # File must be valid JSON after write.
        data = json.loads(hpath.read_text(encoding="utf-8"))
        self.assertIn("outcome", data)


class TestAppendOutcomeMediumConfidenceDesignDiverged(unittest.TestCase):
    """Different design option shipped -> MEDIUM + delta required."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_medium_confidence_when_design_diverged(self):
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing", has_internal=False, recommended_id="A")
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="B",  # diverges from recommended A
            design_option_shipped_summary="Shipped external event store instead",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation="Chose option B because PostgreSQL latency was higher than expected",
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 0)
        outcome = _load_json(hpath)["outcome"]
        self.assertEqual(outcome["confidence_grade"], "MEDIUM")
        self.assertFalse(outcome["matches_recommendation"])
        self.assertIsNotNone(outcome["delta_from_recommendation"])


class TestAppendOutcomeLowConfidenceReconsiderShipped(unittest.TestCase):
    """Verdict was Reconsider but feature shipped anyway (commit provided) -> LOW."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_low_confidence_when_reconsider_shipped(self):
        hpath = _make_handoff_json(self.tmp, verdict="Reconsider", has_internal=False, recommended_id="A")
        # For Reconsider: design_option_shipped_id can be any valid id; verdict_held=False when sha provided
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Shipped despite Reconsider verdict",
            build_vs_buy_actual="Build",
            shipped_commit_sha="deadbeef",  # triggers verdict_held=False
            delta_from_recommendation="Shipped anyway because deadline forced it",
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 0)
        outcome = _load_json(hpath)["outcome"]
        self.assertEqual(outcome["confidence_grade"], "LOW")
        self.assertFalse(outcome["verdict_held"])


class TestAppendOutcomeRequiresDeltaWhenMatchFlagFalse(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_exit_2_when_delta_missing_but_design_diverged(self):
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing", has_internal=False)
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="B",  # diverges -- delta required
            design_option_shipped_summary="Shipped option B",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,  # missing -- should fail
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 2)

    def test_exit_2_when_delta_missing_but_bvb_diverged(self):
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing", has_internal=False)
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Shipped A but bought library",
            build_vs_buy_actual="Buy",  # diverges from Build recommendation
            shipped_commit_sha=None,
            delta_from_recommendation=None,  # missing -- should fail
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 2)


class TestAppendOutcomeRequiresInternalExtensionFlagWhenInternalPriorArt(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_exit_2_when_internal_prior_art_but_flag_omitted(self):
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing", has_internal=True)
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Shipped option A",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed=None,  # must be supplied -- should fail
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 2)

    def test_success_when_internal_prior_art_and_flag_supplied(self):
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing", has_internal=True)
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Extended BaseRepo as recommended",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed="true",
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 0)
        outcome = _load_json(hpath)["outcome"]
        self.assertTrue(outcome["internal_extension_followed"])


class TestAppendOutcomeRejectsInternalExtensionFlagWhenNoInternalPriorArt(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_exit_2_when_no_internal_prior_art_but_flag_supplied(self):
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing", has_internal=False)
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Shipped option A",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed="true",  # must be omitted -- should fail
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 2)


class TestAppendOutcomeIdempotentRewritesOutcomeBlock(unittest.TestCase):
    """Re-running overwrites the existing outcome block (last-write-wins)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_second_invocation_overwrites(self):
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing", has_internal=False)
        base_args = dict(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="First ship summary",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed=None,
        )
        cmd_append_outcome(_make_args(**base_args))
        # Second invocation with different summary.
        base_args["design_option_shipped_summary"] = "Updated summary after correction"
        rc = cmd_append_outcome(_make_args(**base_args))
        self.assertEqual(rc, 0)
        outcome = _load_json(hpath)["outcome"]
        self.assertEqual(outcome["design_option_shipped_summary"], "Updated summary after correction")


class TestAppendOutcomeAppendsMdSection(unittest.TestCase):
    """append-outcome appends ## Outcome section to parallel .md when it exists."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_appends_md_section_when_md_file_exists(self):
        # Create handoff.json with report_path pointing to an md sibling.
        discover_dir = self.tmp / "discover"
        discover_dir.mkdir()
        md_file = discover_dir / "2026-05-20-audit-log-persistence.md"
        md_file.write_text("# Discovery Report\n\n## Summary\n\nOriginal content.\n", encoding="utf-8")

        hpath = discover_dir / "handoff.json"
        data = json.loads((self.tmp / "handoff.json").read_text(encoding="utf-8")) if (self.tmp / "handoff.json").is_file() else None

        # Write handoff directly with report_path = relative path from handoff dir.
        raw_data = json.loads(_make_handoff_json(self.tmp, verdict="Worth pursuing").read_text())
        raw_data["report_path"] = "2026-05-20-audit-log-persistence.md"
        hpath.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")

        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Shipped the PostgreSQL approach",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 0)
        md_content = md_file.read_text(encoding="utf-8")
        self.assertIn("## Outcome", md_content)
        self.assertIn("confidence_grade", md_content)
        # Original content preserved.
        self.assertIn("Original content.", md_content)

    def test_skips_md_append_when_md_file_missing(self):
        """Graceful no-op when parallel .md file doesn't exist."""
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing", has_internal=False)
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Shipped option A",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed=None,
        )
        # The md file at report_path does not exist; should not raise.
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 0)
        # handoff.json must still be updated.
        outcome = _load_json(hpath)["outcome"]
        self.assertIsNotNone(outcome)


class TestAppendOutcomeRejectsWhenHandoffSchemaInvalid(unittest.TestCase):
    """Corrupted base handoff.json -> exit 2."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_exit_2_when_not_json_object(self):
        hpath = self.tmp / "bad.handoff.json"
        hpath.write_text("[1, 2, 3]", encoding="utf-8")
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Summary",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 2)

    def test_exit_2_when_wrong_handoff_kind(self):
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing")
        data = _load_json(hpath)
        data["handoff_kind"] = "research"  # wrong kind
        hpath.write_text(json.dumps(data), encoding="utf-8")
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Summary",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 2)

    def test_exit_2_when_file_missing(self):
        args = _make_args(
            handoff_path=str(self.tmp / "nonexistent.handoff.json"),
            design_option_shipped_id="A",
            design_option_shipped_summary="Summary",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 2)


# ---------------------------------------------------------------------------
# Finding 1: finalize-handoff rejects when verify invariant B is violated.
# ---------------------------------------------------------------------------


class TestFinalizeHandoffRejectsWhenInvariantBViolated(unittest.TestCase):
    """cmd_verify is called inside finalize-handoff; invariant B (no design options) blocks emit."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_finalize_handoff_rejects_when_invariant_b_violated(self):
        """Worth pursuing + empty design_options triggers verify invariant B -> exit 2 (only Rule B).

        Isolation reasoning:
        - Rule A: recommended_option is a non-None dict -> passes the required-field check.
        - Rule B: design_options=[] -> fires (at least 1 required).
        - Rule C: recommended_option has no "name" key -> Rule C's outer condition
          `recommended_option.get("name")` is falsy -> Rule C is skipped entirely.
        - Rule E/F: next_step_text and derisk_plan are set explicitly -> pass.
        - Rule G: prior_art=[] (default) so no internal sources -> Rule G skipped.
        Result: only Rule B fires; exit must be exactly 2.
        """
        devforge = self.tmp / ".devforge"
        emit = self.tmp / "out.handoff.json"
        # recommended_option is a dict (passes Rule A) but has no "name" key (skips Rule C).
        # design_options=[] is the sole violation — only Rule B fires.
        report = _make_report(
            verdict="Worth pursuing",
            design_options=[],  # Rule B violation: requires >=1 entry
            recommended_option={"rationale": "r"},  # dict -> Rule A passes; no "name" -> Rule C skips
            recommendation="Use the event-store approach.",
            next_step_text="Run /specify feature",
            derisk_plan=[{"risk": "Latency", "mitigation": "Cache writes"}],
        )
        _write_state(devforge, _make_memo(), report)
        args = _finalize_args(devforge, str(emit))
        stderr_capture = io.StringIO()
        with unittest.mock.patch("sys.stderr", stderr_capture):
            rc = cmd_finalize_handoff(args)
        # cmd_verify runs first and returns 2 on invariant B (only).
        self.assertEqual(rc, 2, "exit code must be exactly 2 for Rule B violation")
        self.assertFalse(emit.is_file(), "handoff.json must NOT be written when verify fails")
        stderr_text = stderr_capture.getvalue()
        self.assertIn("B:", stderr_text, "stderr must name Rule B as the violation")


# ---------------------------------------------------------------------------
# Finding 2+5: append-outcome rejects missing/invalid bvb recommendation.
# ---------------------------------------------------------------------------


class TestAppendOutcomeRejectsBvbRecommendationMissingOrInvalid(unittest.TestCase):
    """append-outcome validates plan_seeds.build_vs_buy.recommendation before computing flags."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _make_handoff_without_bvb_recommendation(self, recommendation_value):
        """Write handoff.json with build_vs_buy.recommendation set to recommendation_value."""
        hpath = _make_handoff_json(self.tmp, verdict="Worth pursuing", has_internal=False)
        data = _load_json(hpath)
        data["plan_seeds"]["build_vs_buy"]["recommendation"] = recommendation_value
        hpath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return hpath

    def test_append_outcome_rejects_when_bvb_recommendation_missing(self):
        """plan_seeds.build_vs_buy.recommendation deleted (None) -> exit 2."""
        hpath = self._make_handoff_without_bvb_recommendation(None)
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Shipped option A",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 2)

    def test_append_outcome_rejects_when_bvb_recommendation_invalid_enum(self):
        """plan_seeds.build_vs_buy.recommendation = 'Maybe' (not in enum) -> exit 2."""
        hpath = self._make_handoff_without_bvb_recommendation("Maybe")
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="A",
            design_option_shipped_summary="Shipped option A",
            build_vs_buy_actual="Build",
            shipped_commit_sha=None,
            delta_from_recommendation=None,
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 2)


# ---------------------------------------------------------------------------
# Finding 3: match flags are helper-computed; argparse rejects caller override.
# ---------------------------------------------------------------------------


class TestAppendOutcomeHelperComputesMatchFlagsRejectsManualOverride(unittest.TestCase):
    """Match flags (matches_recommendation, matches_build_vs_buy_recommendation) are
    computed by the helper from handoff.json content vs caller-supplied IDs.
    The argparse surface does NOT expose flags to override them.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_match_flags_are_false_when_shipped_diverges_from_recommended(self):
        """Design option B shipped vs recommended A, Buy actual vs Build recommendation ->
        both match flags False; caller cannot override."""
        hpath = _make_handoff_json(
            self.tmp, verdict="Worth pursuing", has_internal=False, recommended_id="A"
        )
        args = _make_args(
            handoff_path=str(hpath),
            design_option_shipped_id="B",      # diverges from recommended A
            design_option_shipped_summary="Shipped option B instead",
            build_vs_buy_actual="Buy",          # diverges from Build recommendation
            shipped_commit_sha=None,
            delta_from_recommendation="Chose B/Buy due to cost constraints",
            internal_extension_followed=None,
        )
        rc = cmd_append_outcome(args)
        self.assertEqual(rc, 0)
        outcome = _load_json(hpath)["outcome"]
        self.assertFalse(outcome["matches_recommendation"])
        self.assertFalse(outcome["matches_build_vs_buy_recommendation"])

    def test_argparse_rejects_spurious_matches_recommendation_flag(self):
        """--matches-recommendation is not a registered argparse flag; parser raises SystemExit."""
        from _discover._cli import build_parser  # noqa: PLC0415
        parser = build_parser()
        with self.assertRaises(SystemExit):
            # argparse exits (code 2) when it encounters an unrecognised flag.
            parser.parse_args([
                "append-outcome",
                "--handoff-path", "some.handoff.json",
                "--design-option-shipped-id", "A",
                "--design-option-shipped-summary", "Summary",
                "--build-vs-buy-actual", "Build",
                "--matches-recommendation", "true",  # spurious flag
            ])

    def test_argparse_rejects_spurious_matches_build_vs_buy_recommendation_flag(self):
        """--matches-build-vs-buy-recommendation is not a registered argparse flag."""
        from _discover._cli import build_parser  # noqa: PLC0415
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "append-outcome",
                "--handoff-path", "some.handoff.json",
                "--design-option-shipped-id", "A",
                "--design-option-shipped-summary", "Summary",
                "--build-vs-buy-actual", "Build",
                "--matches-build-vs-buy-recommendation", "true",  # spurious flag
            ])


if __name__ == "__main__":
    unittest.main()
