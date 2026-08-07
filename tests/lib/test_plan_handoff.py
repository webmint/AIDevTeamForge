"""Tests for plan_helper finalize-handoff + _plan/handoff_schema.py.

Round-trip discipline: the primary happy-path test writes a realistic plan.md
modelled on the /plan Phase 2 template, runs finalize-handoff via subprocess
(real producer invocation), reloads the written plan-handoff.json through
_dict_to_dataclass from _specify/_cmds_handoff.py, and asserts structural
invariants.  No hand-authored plan-handoff.json fixtures.

For provenance tests that require a sibling specify handoff.json:
  _produce_specify_handoff from test_plan_helper.py conventions is replicated
  here (inline) to avoid cross-test-file coupling while still using the real
  specify_helper finalize-handoff producer.

Anonymous content: all domain terms use the "widget catalog search" theme
consistent with the existing fixture family; no real project names.

Stdlib only.
"""

import dataclasses
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER_PY = REPO_ROOT / "src" / "devforge" / "lib" / "plan_helper.py"
_LIB_DIR = REPO_ROOT / "src" / "devforge" / "lib"
SPECIFY_HELPER_PY = REPO_ROOT / "src" / "devforge" / "lib" / "specify_helper.py"
FIXTURE_PLAN = REPO_ROOT / "tests" / "lib" / "fixtures" / "plan_handoff_fixture.md"

# Add lib dir to sys.path so schema imports resolve.
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))
if str(_LIB_DIR / "_plan") not in sys.path:
    sys.path.insert(0, str(_LIB_DIR / "_plan"))
if str(_LIB_DIR / "_specify") not in sys.path:
    sys.path.insert(0, str(_LIB_DIR / "_specify"))

# Import schema after path setup.
from _plan.handoff_schema import (  # noqa: E402
    BreakdownSeeds,
    ConsultRow,
    DeadCodeRow,
    DecisionRow,
    DocImpactRow,
    FileImpactRow,
    Handoff,
    LayerRow,
    Provenance,
    PureBuilderRow,
    RiskRow,
    SCHEMA_VERSION,
    HANDOFF_KIND,
)
# Import _dict_to_dataclass from specify cmds_handoff (shared utility).
from _specify._cmds_handoff import (  # noqa: E402
    _dict_to_dataclass,
    cmd_finalize_handoff as _specify_finalize_handoff,
)
from _specify._state import _atomic_write_json  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _run(*args, cwd=None):
    """Invoke plan_helper.py as a subprocess."""
    return subprocess.run(
        [sys.executable, str(HELPER_PY)] + list(args),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )


def _load_handoff(path):
    # type: (Path) -> Handoff
    """Load a plan-handoff.json from disk and reconstruct the Handoff dataclass."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _dict_to_dataclass(Handoff, raw)


def _make_specify_state():
    # type: () -> Dict[str, Any]
    """Return a minimal valid specify state dict for _specify_finalize_handoff."""
    return {
        "topic": "widget-catalog-search",
        "topic_slug": "widget-catalog-search",
        "date": "2026-05-22",
        "spec_number": "009",
        "feature_name": "widget-catalog-search",
        "feature_slug": "widget-catalog-search",
        "spec_type": "feature_addition",
        "spec_type_rationale": "Adding full-text search to the widget catalog",
        "spec_type_seeded_by_upstream": False,
        "status": "Draft",
        "overview": "Add full-text search capability to the widget catalog API.",
        "current_state": None,
        "desired_behavior": None,
        "affected_areas": [
            {"area": "WidgetService", "files": ["src/services/widget_service.py"],
             "impact": "Search logic added here"}
        ],
        "acceptance_criteria": [
            {
                "ac_id": "AC-1",
                "subsection": "behavior_change",
                "ears_variant": "event_driven",
                "statement": "WHEN a search query is submitted, the system shall return matching widgets.",
                "verification_command": "pytest tests/test_widget_search.py",
                "test_anchor": "test_search_returns_results",
                "n_a_reason": "",
            }
        ],
        "ac_subsection_na": {"ci_pipeline": "No CI changes required"},
        "out_of_scope": [
            {"content": "Real-time search indexing", "finding_ref": ""}
        ],
        "constraints": [
            {"kind": "nfr", "content": "Search must respond within 200ms",
             "quantifier": "p99 < 200ms"}
        ],
        "open_questions": [
            {"question_id": "OQ-1", "content": "Which search backend to use?",
             "category_no_dp_reason": ""}
        ],
        "risks": [
            {"risk": "Index staleness under heavy write load",
             "likelihood": "Low", "impact": "Med",
             "mitigation": "Async index refresh with TTL"}
        ],
        "approval_summary": None,
        "plan_handoff_block": None,
        "open_question_resolutions": [],
        "conflicts": [],
        "source": {
            "handoff_path": None,
            "handoff_kind": None,
            "research_completed_at": None,
            "discover_completed_at": None,
            "discover_recommended_summary": None,
        },
        "input_reads": [],
        "phase1_finalized": False,
        "findings": [],
        "source_no_items_relevant": {},
        "findings_finalized": False,
        "decision_points": [],
        "dp_finalized": False,
        "mode": None,
        "mandatory_reads": [],
        "discretionary_reads": [],
        "phase3_finalized": False,
        "current_branch": None,
        "default_branch": None,
        "branch_decision": None,
        "branch_created": None,
    }


def _produce_specify_handoff(tmp_root, handoff_path=None, handoff_kind=None,
                              research_completed_at=None):
    # type: (Path, Any, Any, Any) -> Path
    """Produce a real specify handoff.json using the real producer.

    Returns the Path to the written handoff.json.
    """
    devforge_dir = tmp_root / ".devforge"
    devforge_dir.mkdir(parents=True, exist_ok=True)
    state = _make_specify_state()
    state["source"]["handoff_path"] = handoff_path
    state["source"]["handoff_kind"] = handoff_kind
    state["source"]["research_completed_at"] = research_completed_at
    _atomic_write_json(state, devforge_dir / "specify-state.json")

    emit_path = tmp_root / "specs" / "009-widget-catalog-search" / "handoff.json"
    emit_path.parent.mkdir(parents=True, exist_ok=True)

    ns = types.SimpleNamespace()
    ns.devforge_dir = str(devforge_dir)
    ns.emit_handoff_json = str(emit_path)
    ns.specs_root = "specs"
    ns.completed_at = "2026-05-22T10:00:00Z"

    rc = _specify_finalize_handoff(ns)
    if rc != 0:
        raise RuntimeError("specify finalize-handoff failed rc={0}".format(rc))
    return emit_path


# ---------------------------------------------------------------------------
# Tests: _plan/handoff_schema.py — schema dataclasses unit tests.
# ---------------------------------------------------------------------------


class SchemaConstantsTests(unittest.TestCase):
    """Schema constants have the expected values."""

    def test_schema_version(self):
        self.assertEqual(SCHEMA_VERSION, "1.0")

    def test_handoff_kind(self):
        self.assertEqual(HANDOFF_KIND, "plan")


class LayerRowTests(unittest.TestCase):
    def test_valid_row(self):
        r = LayerRow(layer="Domain", what="Types and interfaces", files="src/types.ts")
        self.assertEqual(r.layer, "Domain")

    def test_empty_layer_raises(self):
        with self.assertRaises(ValueError):
            LayerRow(layer="", what="What", files="f.ts")

    def test_empty_what_raises(self):
        with self.assertRaises(ValueError):
            LayerRow(layer="Domain", what="", files="f.ts")

    def test_files_may_be_empty_string(self):
        # files is optional content; empty string is allowed.
        r = LayerRow(layer="Domain", what="Types", files="")
        self.assertEqual(r.files, "")

    def test_non_string_layer_raises(self):
        with self.assertRaises(ValueError):
            LayerRow(layer=123, what="What", files="f.ts")  # type: ignore[arg-type]


class DecisionRowTests(unittest.TestCase):
    def test_valid_row(self):
        r = DecisionRow(
            decision="Filter location",
            chosen_approach="Client-side",
            why="Spec §7 forbids new endpoint",
            alternatives_rejected="Server-side",
        )
        self.assertEqual(r.decision, "Filter location")

    def test_empty_decision_raises(self):
        with self.assertRaises(ValueError):
            DecisionRow(decision="", chosen_approach="X", why="Y", alternatives_rejected="Z")

    def test_empty_chosen_approach_raises(self):
        with self.assertRaises(ValueError):
            DecisionRow(decision="D", chosen_approach="", why="Y", alternatives_rejected="Z")

    def test_empty_why_raises(self):
        with self.assertRaises(ValueError):
            DecisionRow(decision="D", chosen_approach="X", why="", alternatives_rejected="Z")

    def test_alternatives_may_be_empty_string(self):
        r = DecisionRow(decision="D", chosen_approach="X", why="Y", alternatives_rejected="")
        self.assertEqual(r.alternatives_rejected, "")


class FileImpactRowTests(unittest.TestCase):
    def test_valid_row(self):
        r = FileImpactRow(file="src/a.py", action="Modify", what_changes="Add function")
        self.assertEqual(r.file, "src/a.py")

    def test_empty_file_raises(self):
        with self.assertRaises(ValueError):
            FileImpactRow(file="", action="Modify", what_changes="Add function")

    def test_empty_action_raises(self):
        with self.assertRaises(ValueError):
            FileImpactRow(file="src/a.py", action="", what_changes="Add function")

    def test_what_changes_may_be_empty(self):
        r = FileImpactRow(file="src/a.py", action="Modify", what_changes="")
        self.assertEqual(r.what_changes, "")


class DocImpactRowTests(unittest.TestCase):
    def test_valid_row(self):
        r = DocImpactRow(
            doc_file="docs/widgets/overview.md",
            action="Update",
            what_changes="Document new search capability",
        )
        self.assertEqual(r.doc_file, "docs/widgets/overview.md")

    def test_empty_doc_file_raises(self):
        with self.assertRaises(ValueError):
            DocImpactRow(doc_file="", action="Update", what_changes="X")

    def test_empty_action_raises(self):
        with self.assertRaises(ValueError):
            DocImpactRow(doc_file="docs/a.md", action="", what_changes="X")


class RiskRowTests(unittest.TestCase):
    def test_valid_row(self):
        r = RiskRow(risk="Cache stale", likelihood="Low", impact="Med", mitigation="TTL")
        self.assertEqual(r.risk, "Cache stale")

    def test_empty_risk_raises(self):
        with self.assertRaises(ValueError):
            RiskRow(risk="", likelihood="Low", impact="Med", mitigation="TTL")

    def test_empty_likelihood_raises(self):
        with self.assertRaises(ValueError):
            RiskRow(risk="R", likelihood="", impact="Med", mitigation="TTL")

    def test_empty_impact_raises(self):
        with self.assertRaises(ValueError):
            RiskRow(risk="R", likelihood="Low", impact="", mitigation="TTL")

    def test_empty_mitigation_raises(self):
        with self.assertRaises(ValueError):
            RiskRow(risk="R", likelihood="Low", impact="Med", mitigation="")


class ConsultRowTests(unittest.TestCase):
    def test_valid_row_accepted(self):
        r = ConsultRow(
            specialist="backend-engineer",
            sub_question="Server-side?",
            input_summary="No — spec §7 forbids",
            verdict="accepted",
            cites="spec.md §7",
        )
        self.assertEqual(r.verdict, "accepted")

    def test_all_verdict_values(self):
        for v in ("accepted", "modified", "rejected", "no-response"):
            r = ConsultRow(
                specialist="S", sub_question="Q", input_summary="I",
                verdict=v, cites="own-reasoning",
            )
            self.assertEqual(r.verdict, v)

    def test_invalid_verdict_raises(self):
        with self.assertRaises(ValueError):
            ConsultRow(
                specialist="S", sub_question="Q", input_summary="I",
                verdict="unknown", cites="X",
            )

    def test_empty_specialist_raises(self):
        with self.assertRaises(ValueError):
            ConsultRow(
                specialist="", sub_question="Q", input_summary="I",
                verdict="accepted", cites="X",
            )


class PureBuilderRowTests(unittest.TestCase):
    def test_valid_row(self):
        r = PureBuilderRow(
            target="filterWidgetsByQuery",
            file="src/widgets/widget_filter.ts",
            why="No I/O, deterministic",
        )
        self.assertEqual(r.target, "filterWidgetsByQuery")

    def test_empty_target_raises(self):
        with self.assertRaises(ValueError):
            PureBuilderRow(target="", file="f.ts", why="Pure")

    def test_empty_file_raises(self):
        with self.assertRaises(ValueError):
            PureBuilderRow(target="fn", file="", why="Pure")

    def test_why_may_be_empty_string(self):
        r = PureBuilderRow(target="fn", file="f.ts", why="")
        self.assertEqual(r.why, "")

    def test_non_string_why_raises(self):
        with self.assertRaises(ValueError):
            PureBuilderRow(target="fn", file="f.ts", why=123)  # type: ignore[arg-type]

    def test_non_string_target_raises(self):
        with self.assertRaises(ValueError):
            PureBuilderRow(target=123, file="f.ts", why="Pure")  # type: ignore[arg-type]


class DeadCodeRowTests(unittest.TestCase):
    def test_valid_row(self):
        r = DeadCodeRow(
            file="src/widgets/widget_filter.ts",
            anchor_token=": 'legacyRegionCode'",
            kind="arm",
            why_dead="Superseded by the generic query-param filter",
        )
        self.assertEqual(r.file, "src/widgets/widget_filter.ts")
        self.assertEqual(r.kind, "arm")

    def test_empty_file_raises(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file="", anchor_token="x", kind="arm", why_dead="Dead")

    def test_empty_anchor_token_raises(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file="f.ts", anchor_token="", kind="arm", why_dead="Dead")

    def test_empty_why_dead_raises(self):
        """Unlike PureBuilderRow.why, why_dead is required non-empty."""
        with self.assertRaises(ValueError):
            DeadCodeRow(file="f.ts", anchor_token="x", kind="arm", why_dead="")

    def test_invalid_kind_raises(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file="f.ts", anchor_token="x", kind="bogus", why_dead="Dead")

    def test_all_enum_kinds_accepted(self):
        for kind in ("arm", "function", "param", "import", "branch"):
            r = DeadCodeRow(file="f.ts", anchor_token="x", kind=kind, why_dead="Dead")
            self.assertEqual(r.kind, kind)

    def test_non_string_file_raises(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file=123, anchor_token="x", kind="arm", why_dead="Dead")  # type: ignore[arg-type]

    def test_non_string_why_dead_raises(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file="f.ts", anchor_token="x", kind="arm", why_dead=123)  # type: ignore[arg-type]

    def test_semicolon_in_anchor_token_raises(self):
        """finding C (plan 71 D9 review hardening): anchor_token must not
        contain a semicolon -- the '**Dead code removal**:' task field's
        value is semicolon-delimited, so a literal token containing one
        (e.g. a C-style for-loop header) cannot be carried unambiguously."""
        with self.assertRaises(ValueError):
            DeadCodeRow(
                file="src/loop.ts",
                anchor_token="for (i = 0; i < n; i++)",
                kind="branch",
                why_dead="Superseded loop removed",
            )

    def test_token_without_semicolon_accepted(self):
        r = DeadCodeRow(file="f.ts", anchor_token="foo", kind="arm", why_dead="Dead")
        self.assertEqual(r.anchor_token, "foo")


class ProvenanceTests(unittest.TestCase):
    def test_both_none_valid(self):
        p = Provenance(upstream_handoff_path=None, upstream_handoff_kind=None)
        self.assertIsNone(p.upstream_handoff_path)
        self.assertIsNone(p.upstream_handoff_kind)

    def test_both_set_valid(self):
        p = Provenance(
            upstream_handoff_path="specs/009/handoff.json",
            upstream_handoff_kind="specify",
        )
        self.assertEqual(p.upstream_handoff_kind, "specify")

    def test_path_set_kind_none_raises_covary(self):
        with self.assertRaises(ValueError):
            Provenance(
                upstream_handoff_path="specs/009/handoff.json",
                upstream_handoff_kind=None,
            )

    def test_kind_set_path_none_raises_covary(self):
        with self.assertRaises(ValueError):
            Provenance(
                upstream_handoff_path=None,
                upstream_handoff_kind="specify",
            )

    def test_invalid_upstream_kind_raises(self):
        with self.assertRaises(ValueError):
            Provenance(
                upstream_handoff_path="specs/009/handoff.json",
                upstream_handoff_kind="research",  # not a valid plan upstream kind
            )

    def test_spec_path_optional(self):
        p = Provenance(spec_path="specs/009/spec.md")
        self.assertEqual(p.spec_path, "specs/009/spec.md")

    def test_spec_path_none(self):
        p = Provenance(spec_path=None)
        self.assertIsNone(p.spec_path)


class HandoffSchemaTests(unittest.TestCase):
    def _make_minimal_handoff(self, **overrides):
        defaults = dict(
            schema_version=SCHEMA_VERSION,
            handoff_kind=HANDOFF_KIND,
            plan_path="specs/009/plan.md",
            plan_completed_at="2026-05-22T10:00:00Z",
            provenance=Provenance(),
            breakdown_seeds=BreakdownSeeds(
                layer_map=[],
                key_design_decisions=[],
                file_impact=[],
                doc_impact=[],
                risks=[],
                specialist_consultation=[],
                dependencies=[],
            ),
        )
        defaults.update(overrides)
        return Handoff(**defaults)

    def test_minimal_handoff_valid(self):
        h = self._make_minimal_handoff()
        self.assertEqual(h.handoff_kind, "plan")
        self.assertEqual(h.schema_version, "1.0")

    def test_wrong_handoff_kind_raises(self):
        with self.assertRaises(ValueError):
            self._make_minimal_handoff(handoff_kind="specify")

    def test_wrong_schema_version_raises(self):
        with self.assertRaises(ValueError):
            self._make_minimal_handoff(schema_version="2.0")

    def test_empty_plan_path_raises(self):
        with self.assertRaises(ValueError):
            self._make_minimal_handoff(plan_path="")

    def test_empty_plan_completed_at_raises(self):
        with self.assertRaises(ValueError):
            self._make_minimal_handoff(plan_completed_at="")

    def test_provenance_wrong_type_raises(self):
        with self.assertRaises(ValueError):
            self._make_minimal_handoff(provenance={"key": "val"})  # type: ignore[arg-type]

    def test_breakdown_seeds_wrong_type_raises(self):
        with self.assertRaises(ValueError):
            self._make_minimal_handoff(breakdown_seeds={"key": "val"})  # type: ignore[arg-type]

    def test_breakdown_seeds_non_list_field_raises(self):
        with self.assertRaises(ValueError):
            BreakdownSeeds(
                layer_map="not a list",  # type: ignore[arg-type]
                key_design_decisions=[],
                file_impact=[],
                doc_impact=[],
                risks=[],
                specialist_consultation=[],
                dependencies=[],
            )

    def test_breakdown_seeds_constructible_without_pure_builder_targets(self):
        """Back-compat: the old 7-positional-arg construction still works,
        with pure_builder_targets defaulting to an empty list."""
        seeds = BreakdownSeeds(
            layer_map=[],
            key_design_decisions=[],
            file_impact=[],
            doc_impact=[],
            risks=[],
            specialist_consultation=[],
            dependencies=[],
        )
        self.assertEqual(seeds.pure_builder_targets, [])

    def test_breakdown_seeds_with_pure_builder_targets(self):
        """pure_builder_targets accepts a list of PureBuilderRow."""
        row = PureBuilderRow(target="fn", file="f.ts", why="Pure")
        seeds = BreakdownSeeds(
            layer_map=[],
            key_design_decisions=[],
            file_impact=[],
            doc_impact=[],
            risks=[],
            specialist_consultation=[],
            dependencies=[],
            pure_builder_targets=[row],
        )
        self.assertEqual(len(seeds.pure_builder_targets), 1)
        self.assertEqual(seeds.pure_builder_targets[0].target, "fn")

    def test_breakdown_seeds_pure_builder_targets_non_list_raises(self):
        with self.assertRaises(ValueError):
            BreakdownSeeds(
                layer_map=[],
                key_design_decisions=[],
                file_impact=[],
                doc_impact=[],
                risks=[],
                specialist_consultation=[],
                dependencies=[],
                pure_builder_targets="not a list",  # type: ignore[arg-type]
            )

    def test_breakdown_seeds_constructible_without_dead_code_rows(self):
        """Back-compat: construction without dead_code_rows still works,
        with dead_code_rows defaulting to an empty list (plan 71 D6)."""
        seeds = BreakdownSeeds(
            layer_map=[],
            key_design_decisions=[],
            file_impact=[],
            doc_impact=[],
            risks=[],
            specialist_consultation=[],
            dependencies=[],
        )
        self.assertEqual(seeds.dead_code_rows, [])

    def test_breakdown_seeds_with_dead_code_rows(self):
        """dead_code_rows accepts a list of DeadCodeRow."""
        row = DeadCodeRow(
            file="src/widgets/widget_filter.ts",
            anchor_token=": 'legacyRegionCode'",
            kind="arm",
            why_dead="Superseded by the generic filter",
        )
        seeds = BreakdownSeeds(
            layer_map=[],
            key_design_decisions=[],
            file_impact=[],
            doc_impact=[],
            risks=[],
            specialist_consultation=[],
            dependencies=[],
            dead_code_rows=[row],
        )
        self.assertEqual(len(seeds.dead_code_rows), 1)
        self.assertEqual(seeds.dead_code_rows[0].kind, "arm")

    def test_breakdown_seeds_dead_code_rows_non_list_raises(self):
        with self.assertRaises(ValueError):
            BreakdownSeeds(
                layer_map=[],
                key_design_decisions=[],
                file_impact=[],
                doc_impact=[],
                risks=[],
                specialist_consultation=[],
                dependencies=[],
                dead_code_rows="not a list",  # type: ignore[arg-type]
            )

    def test_dict_to_dataclass_old_plan_handoff_json_without_dead_code_rows(self):
        """Old-JSON back-compat (plan 71 D6): a plan-handoff.json dict built
        BEFORE dead_code_rows existed (no such key in breakdown_seeds)
        reconstructs via _dict_to_dataclass with dead_code_rows == []."""
        old_dict = {
            "schema_version": SCHEMA_VERSION,
            "handoff_kind": HANDOFF_KIND,
            "plan_path": "specs/009/plan.md",
            "plan_completed_at": "2026-05-22T10:00:00Z",
            "provenance": {
                "upstream_handoff_path": None,
                "upstream_handoff_kind": None,
                "spec_path": None,
            },
            "breakdown_seeds": {
                "layer_map": [],
                "key_design_decisions": [],
                "file_impact": [],
                "doc_impact": [],
                "risks": [],
                "specialist_consultation": [],
                "dependencies": [],
                "pure_builder_targets": [],
                # dead_code_rows key intentionally absent (pre-plan-71 shape).
            },
        }
        h = _dict_to_dataclass(Handoff, old_dict)
        self.assertEqual(h.breakdown_seeds.dead_code_rows, [])


# ---------------------------------------------------------------------------
# Tests: finalize-handoff CLI — round-trip via real producer.
# ---------------------------------------------------------------------------


class FinalizeHandoffHappyPathTests(unittest.TestCase):
    """Round-trip: write realistic plan.md -> finalize-handoff -> reload + assert."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_fixture_plan(self, dest_dir):
        # type: (Path) -> Path
        """Copy the checked-in fixture plan to dest_dir/plan.md."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        plan_path = dest_dir / "plan.md"
        plan_path.write_text(
            FIXTURE_PLAN.read_text(encoding="utf-8"), encoding="utf-8"
        )
        return plan_path

    def test_finalize_handoff_exit_0_writes_file(self):
        """finalize-handoff on fixture plan exits 0 and writes plan-handoff.json."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)

        result = _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        self.assertEqual(result.returncode, 0, result.stderr)
        expected = plan_dir / "plan-handoff.json"
        self.assertTrue(expected.is_file(), "plan-handoff.json not written")
        # stdout should contain the written path.
        self.assertIn("plan-handoff.json", result.stdout)

    def test_finalize_handoff_handoff_kind_is_plan(self):
        """Reloaded handoff has handoff_kind == 'plan'."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertEqual(h.handoff_kind, "plan")

    def test_finalize_handoff_schema_version(self):
        """Reloaded handoff has schema_version == '1.0'."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertEqual(h.schema_version, "1.0")

    def test_finalize_handoff_plan_path_is_absolute(self):
        """Reloaded handoff.plan_path is an absolute path to the plan file."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertTrue(
            os.path.isabs(h.plan_path),
            "plan_path should be absolute, got: {0}".format(h.plan_path),
        )

    def test_finalize_handoff_completed_at_default_is_set(self):
        """plan_completed_at is set (non-empty) when --completed-at is not passed."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertTrue(h.plan_completed_at.strip(), "plan_completed_at must be non-empty")

    def test_finalize_handoff_completed_at_override(self):
        """--completed-at is reflected in plan_completed_at."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run(
            "finalize-handoff", str(plan_path),
            "--completed-at", "2026-05-22T12:34:56Z",
            cwd=self.tmp,
        )

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertEqual(h.plan_completed_at, "2026-05-22T12:34:56Z")

    def test_finalize_handoff_layer_map_rows_parsed(self):
        """Fixture plan has 2 real Layer Map rows (1 placeholder skipped)."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        # Fixture has 2 real rows + 1 [placeholder] row that must be skipped.
        self.assertEqual(len(h.breakdown_seeds.layer_map), 2)
        layers = [r.layer for r in h.breakdown_seeds.layer_map]
        self.assertIn("Presentation", layers)

    def test_finalize_handoff_key_design_decisions_parsed(self):
        """Fixture plan has 2 real Decision rows (1 placeholder skipped)."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        # Fixture has 2 real rows + 1 [decision] placeholder row.
        self.assertEqual(len(h.breakdown_seeds.key_design_decisions), 2)
        decisions = [r.decision for r in h.breakdown_seeds.key_design_decisions]
        self.assertIn("Filter location", decisions)
        self.assertIn("Match strategy", decisions)

    def test_finalize_handoff_file_impact_rows_parsed(self):
        """Fixture plan has 4 real File Impact rows (1 placeholder skipped)."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        # Fixture has 4 real rows + 1 [path] placeholder row.
        self.assertEqual(len(h.breakdown_seeds.file_impact), 4)
        files = [r.file for r in h.breakdown_seeds.file_impact]
        self.assertIn("src/widgets/widget_filter.ts", files)
        # All rows must have non-empty file and action.
        for row in h.breakdown_seeds.file_impact:
            self.assertTrue(row.file.strip(), "file must be non-empty")
            self.assertTrue(row.action.strip(), "action must be non-empty")

    def test_finalize_handoff_doc_impact_rows_parsed(self):
        """Fixture plan has 2 real Documentation Impact rows (1 placeholder skipped)."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        # Fixture has 2 real rows + 1 [path] placeholder row.
        self.assertEqual(len(h.breakdown_seeds.doc_impact), 2)
        doc_files = [r.doc_file for r in h.breakdown_seeds.doc_impact]
        self.assertIn("docs/widgets/overview.md", doc_files)

    def test_finalize_handoff_risk_rows_parsed(self):
        """Fixture plan has 2 real Risk Assessment rows (1 placeholder skipped)."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        # Fixture has 2 real rows + 1 [risk] placeholder row.
        self.assertEqual(len(h.breakdown_seeds.risks), 2)
        risks = [r.risk for r in h.breakdown_seeds.risks]
        self.assertIn("Large catalogs make client-side filtering janky", risks)
        for row in h.breakdown_seeds.risks:
            self.assertTrue(row.likelihood.strip())
            self.assertTrue(row.impact.strip())
            self.assertTrue(row.mitigation.strip())

    def test_finalize_handoff_specialist_consultation_parsed(self):
        """Fixture plan has 1 real Specialist row; (none) + template + invalid-verdict rows skipped."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        # Fixture: 'backend-engineer' row (verdict=accepted) is real.
        # 'db-engineer' row has <the specific sub-question> placeholder -> skipped.
        # '(none)' row -> skipped.
        self.assertEqual(len(h.breakdown_seeds.specialist_consultation), 1)
        self.assertEqual(
            h.breakdown_seeds.specialist_consultation[0].specialist, "backend-engineer"
        )
        self.assertEqual(
            h.breakdown_seeds.specialist_consultation[0].verdict, "accepted"
        )

    def test_finalize_handoff_pure_builder_targets_parsed(self):
        """Fixture plan has 2 real Pure-Builder Targets rows (1 placeholder skipped)."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        # Fixture has 2 real rows + 1 [target] placeholder row.
        self.assertEqual(len(h.breakdown_seeds.pure_builder_targets), 2)
        targets = [r.target for r in h.breakdown_seeds.pure_builder_targets]
        self.assertIn("filterWidgetsByQuery", targets)
        self.assertIn("normalizeTagList", targets)
        for row in h.breakdown_seeds.pure_builder_targets:
            self.assertTrue(row.target.strip(), "target must be non-empty")
            self.assertTrue(row.file.strip(), "file must be non-empty")

    def test_finalize_handoff_dead_code_rows_parsed(self):
        """Fixture plan has 2 real Change-Induced Dead Code rows (1 placeholder skipped)."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        # Fixture has 2 real rows + 1 [file] placeholder row.
        self.assertEqual(len(h.breakdown_seeds.dead_code_rows), 2)
        anchors = [r.anchor_token for r in h.breakdown_seeds.dead_code_rows]
        self.assertIn(": 'legacyRegionCode'", anchors)
        self.assertIn("applyLegacyTagFilter", anchors)
        for row in h.breakdown_seeds.dead_code_rows:
            self.assertTrue(row.file.strip(), "file must be non-empty")
            self.assertTrue(row.anchor_token.strip(), "anchor_token must be non-empty")
            self.assertIn(row.kind, ("arm", "function", "param", "import", "branch"))
            self.assertTrue(row.why_dead.strip(), "why_dead must be non-empty")

    def test_finalize_handoff_warns_on_skipped_dead_code_row(self):
        """plan 71 D9 finding-C UX close: a plan.md dead-code row whose
        anchor_token contains a semicolon fails DeadCodeRow construction and
        is silently absent from dead_code_rows -- finalize-handoff WARNs on
        stderr naming the row + reason (mirroring breakdown_helper's own
        WARN style) instead of leaving the author to a declared-but-
        unsubstantiated chokepoint remedy ('re-run finalize-handoff') that
        can never succeed for this row. A second, VALID row in the same
        table still parses through cleanly (exit 0, no chokepoint)."""
        plan_dir = self.tmp / "specs" / "010-loop-cleanup"
        plan_dir.mkdir(parents=True)
        plan_path = plan_dir / "plan.md"
        plan_path.write_text(
            "# Plan: Loop Cleanup\n\n"
            "**Date**: 2026-08-06\n"
            "**Status**: Draft\n\n"
            "## Summary\n\nRemove a dead loop.\n\n"
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "|------|--------------|------|----------|\n"
            "| src/loop.ts | for (i = 0; i < n; i++) | branch | Superseded loop removed |\n"
            "| src/other.ts | goodToken | arm | Fine row |\n\n"
            "## Dependencies\n\nNone.\n",
            encoding="utf-8",
        )

        result = _run("finalize-handoff", str(plan_path), cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plan_helper: finalize-handoff: WARN:", result.stderr)
        self.assertIn("src/loop.ts", result.stderr)
        self.assertIn("semicolon", result.stderr)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        anchors = [r.anchor_token for r in h.breakdown_seeds.dead_code_rows]
        self.assertEqual(anchors, ["goodToken"])

    def test_finalize_handoff_dependencies_parsed(self):
        """Fixture plan has 2 non-blank dependency lines."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertGreater(len(h.breakdown_seeds.dependencies), 0)
        # Should not include blank lines.
        for dep in h.breakdown_seeds.dependencies:
            self.assertTrue(dep.strip(), "dependency line must be non-blank")

    def test_finalize_handoff_idempotent(self):
        """Running finalize-handoff twice exits 0 both times; JSON content is identical.

        --completed-at is pinned to the same timestamp so the timestamp field
        does not introduce a spurious diff between the two runs.
        """
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        handoff_file = plan_dir / "plan-handoff.json"

        r1 = _run("finalize-handoff", str(plan_path),
                  "--completed-at", "2026-05-22T12:00:00Z", cwd=self.tmp)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        h1 = json.loads(handoff_file.read_text(encoding="utf-8"))

        r2 = _run("finalize-handoff", str(plan_path),
                  "--completed-at", "2026-05-22T12:00:00Z", cwd=self.tmp)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        h2 = json.loads(handoff_file.read_text(encoding="utf-8"))

        # stdout paths must match (same file written both times).
        self.assertEqual(r1.stdout.strip(), r2.stdout.strip())
        # JSON content must be identical (idempotent parse + serialize).
        self.assertEqual(h1, h2)

    def test_finalize_handoff_output_is_valid_json(self):
        """Written plan-handoff.json is valid JSON."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_fixture_plan(plan_dir)
        _run("finalize-handoff", str(plan_path), cwd=self.tmp)

        raw = (plan_dir / "plan-handoff.json").read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            self.fail("plan-handoff.json is not valid JSON: {0}".format(e))
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("handoff_kind"), "plan")


class FinalizeHandoffProvenanceTests(unittest.TestCase):
    """Provenance resolution: with and without sibling specify handoff.json."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_plan(self, plan_dir):
        # type: (Path) -> Path
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_path = plan_dir / "plan.md"
        plan_path.write_text(
            FIXTURE_PLAN.read_text(encoding="utf-8"), encoding="utf-8"
        )
        return plan_path

    def test_no_sibling_handoff_provenance_both_none(self):
        """Without sibling handoff.json, provenance upstream fields are both None."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_plan(plan_dir)

        result = _run("finalize-handoff", str(plan_path), cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertIsNone(h.provenance.upstream_handoff_path)
        self.assertIsNone(h.provenance.upstream_handoff_kind)

    def test_with_sibling_specify_handoff_provenance_set(self):
        """With a real sibling specify handoff.json, provenance is populated.

        Round-trip: produce a real specify handoff via the real producer,
        place plan.md in the same directory, then finalize-handoff and
        assert provenance fields.
        """
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"

        # Produce real specify handoff INTO plan_dir (as handoff.json sibling).
        specify_emit = _produce_specify_handoff(self.tmp)
        # specify_emit is in tmp/specs/009-widget-catalog-search/handoff.json
        # which IS the same dir as plan_dir.
        plan_path = self._write_plan(plan_dir)

        result = _run("finalize-handoff", str(plan_path), cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)

        h = _load_handoff(plan_dir / "plan-handoff.json")

        # upstream_handoff_path should point at the specify handoff.json.
        self.assertIsNotNone(h.provenance.upstream_handoff_path)
        self.assertIn(
            "handoff.json", h.provenance.upstream_handoff_path,
            "upstream_handoff_path should reference handoff.json",
        )
        self.assertEqual(h.provenance.upstream_handoff_kind, "specify")

    def test_sibling_spec_md_sets_spec_path(self):
        """If a sibling spec.md exists, provenance.spec_path is set."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_plan(plan_dir)
        # Create a sibling spec.md.
        sibling_spec = plan_dir / "spec.md"
        sibling_spec.write_text("# Spec: widget-catalog-search\n\n**Status**: Approved\n",
                                 encoding="utf-8")

        result = _run("finalize-handoff", str(plan_path), cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertIsNotNone(h.provenance.spec_path)
        self.assertIn("spec.md", h.provenance.spec_path)

    def test_no_sibling_spec_md_spec_path_is_none(self):
        """Without a sibling spec.md, provenance.spec_path is None."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_plan(plan_dir)

        result = _run("finalize-handoff", str(plan_path), cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertIsNone(h.provenance.spec_path)

    def test_non_specify_sibling_json_ignored(self):
        """A sibling handoff.json with handoff_kind != 'specify' is ignored -> provenance None."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_plan(plan_dir)
        # Write a sibling handoff.json with wrong kind.
        (plan_dir / "handoff.json").write_text(
            json.dumps({"handoff_kind": "discover", "other_field": "x"}),
            encoding="utf-8",
        )

        result = _run("finalize-handoff", str(plan_path), cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertIsNone(h.provenance.upstream_handoff_path)
        self.assertIsNone(h.provenance.upstream_handoff_kind)

    def test_malformed_sibling_json_ignored(self):
        """A sibling handoff.json with invalid JSON is ignored -> provenance None."""
        plan_dir = self.tmp / "specs" / "009-widget-catalog-search"
        plan_path = self._write_plan(plan_dir)
        (plan_dir / "handoff.json").write_text("{not valid json", encoding="utf-8")

        result = _run("finalize-handoff", str(plan_path), cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertIsNone(h.provenance.upstream_handoff_path)


class FinalizeHandoffErrorTests(unittest.TestCase):
    """Error paths: missing file, schema failures."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_plan_path_exits_2(self):
        """Non-existent plan path -> exit 2."""
        result = _run("finalize-handoff", "/nonexistent/path/plan.md", cwd=self.tmp)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("plan not found", result.stderr)

    def test_empty_plan_file_produces_empty_seeds_exit_0(self):
        """An empty plan.md has no tables -> all seeds are empty -> exit 0."""
        plan_dir = self.tmp / "specs" / "000-empty"
        plan_dir.mkdir(parents=True)
        plan_path = plan_dir / "plan.md"
        plan_path.write_text("# Plan: Empty\n\n## Summary\n\nNothing here.\n",
                              encoding="utf-8")

        result = _run("finalize-handoff", str(plan_path), cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertEqual(h.breakdown_seeds.layer_map, [])
        self.assertEqual(h.breakdown_seeds.file_impact, [])
        self.assertEqual(h.breakdown_seeds.risks, [])
        # Pure-Builder Targets section is absent from this plan.md ->
        # pure_builder_targets must be empty (real producer, no section).
        self.assertEqual(h.breakdown_seeds.pure_builder_targets, [])

    def test_plan_with_only_placeholder_rows_empty_seeds(self):
        """A plan.md with only placeholder rows -> all seeds empty -> exit 0."""
        plan_dir = self.tmp / "specs" / "000-placeholder"
        plan_dir.mkdir(parents=True)
        plan_path = plan_dir / "plan.md"
        plan_path.write_text(
            "# Plan: Placeholder\n\n"
            "## Risk Assessment\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "| --- | --- | --- | --- |\n"
            "| [risk] | Low/Med/High | Low/Med/High | [how to handle] |\n\n"
            "### File Impact\n\n"
            "| File | Action | What Changes |\n"
            "| --- | --- | --- |\n"
            "| [path] | Create/Modify | [brief description] |\n",
            encoding="utf-8",
        )

        result = _run("finalize-handoff", str(plan_path), cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)

        h = _load_handoff(plan_dir / "plan-handoff.json")
        self.assertEqual(h.breakdown_seeds.risks, [])
        self.assertEqual(h.breakdown_seeds.file_impact, [])

    def test_finalize_handoff_appears_in_help(self):
        """finalize-handoff is listed in top-level --help output."""
        result = _run("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("finalize-handoff", result.stdout)


# ---------------------------------------------------------------------------
# Tests: plan parsing helpers — unit tests (import plan_helper directly).
# ---------------------------------------------------------------------------


# Ensure plan_helper is importable.
if str(HELPER_PY.parent) not in sys.path:
    sys.path.insert(0, str(HELPER_PY.parent))
import plan_helper  # noqa: E402


class ParseLayerMapTests(unittest.TestCase):
    """Unit tests for _parse_layer_map."""

    def test_parses_two_rows(self):
        content = (
            "### Layer Map\n\n"
            "| Layer | What | Files (existing or new) |\n"
            "| --- | --- | --- |\n"
            "| Domain | Types | src/types.ts |\n"
            "| Presentation | Component | src/comp.ts |\n"
        )
        rows = plan_helper._parse_layer_map(content)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].layer, "Domain")
        self.assertEqual(rows[1].layer, "Presentation")

    def test_placeholder_row_skipped(self):
        content = (
            "### Layer Map\n\n"
            "| Layer | What | Files |\n"
            "| --- | --- | --- |\n"
            "| Domain | Types | src/types.ts |\n"
            "| [placeholder] | [placeholder] | [placeholder] |\n"
        )
        rows = plan_helper._parse_layer_map(content)
        self.assertEqual(len(rows), 1)

    def test_section_absent_returns_empty(self):
        rows = plan_helper._parse_layer_map("## Summary\n\nNothing.\n")
        self.assertEqual(rows, [])

    def test_section_stops_at_next_heading(self):
        """Layer Map section does not bleed into the next ### section."""
        content = (
            "### Layer Map\n\n"
            "| Layer | What | Files |\n"
            "| --- | --- | --- |\n"
            "| Domain | Types | src/types.ts |\n\n"
            "### Key Design Decisions\n\n"
            "| Decision | Chosen Approach | Why | Alternatives Rejected |\n"
            "| --- | --- | --- | --- |\n"
            "| D | A | W | R |\n"
        )
        rows = plan_helper._parse_layer_map(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].layer, "Domain")


class ParseKeyDesignDecisionsTests(unittest.TestCase):
    def test_parses_two_rows(self):
        content = (
            "### Key Design Decisions\n\n"
            "| Decision | Chosen Approach | Why | Alternatives Rejected |\n"
            "| --- | --- | --- | --- |\n"
            "| Filter location | Client-side | Spec §7 | Server-side |\n"
            "| Match strategy | Substring | Simple | Fuzzy |\n"
        )
        rows = plan_helper._parse_key_design_decisions(content)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].decision, "Filter location")

    def test_placeholder_row_skipped(self):
        content = (
            "### Key Design Decisions\n\n"
            "| Decision | Chosen Approach | Why | Alternatives Rejected |\n"
            "| --- | --- | --- | --- |\n"
            "| Filter location | Client-side | Spec §7 | Server-side |\n"
            "| [decision] | [approach] | [rationale] | [alternatives] |\n"
        )
        rows = plan_helper._parse_key_design_decisions(content)
        self.assertEqual(len(rows), 1)

    def test_section_absent_returns_empty(self):
        rows = plan_helper._parse_key_design_decisions("## Summary\n\nNo decisions.\n")
        self.assertEqual(rows, [])


class ParseFileImpactRowsTests(unittest.TestCase):
    def test_parses_real_rows(self):
        content = (
            "### File Impact\n\n"
            "| File | Action | What Changes |\n"
            "| --- | --- | --- |\n"
            "| src/a.py | Modify | Add function |\n"
            "| src/b.py | Create | New module |\n"
            "| [path] | Create/Modify | [brief description] |\n"
        )
        rows = plan_helper._parse_file_impact_rows(content)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].file, "src/a.py")
        self.assertEqual(rows[1].action, "Create")

    def test_section_absent_returns_empty(self):
        rows = plan_helper._parse_file_impact_rows("## Summary\n\nNothing.\n")
        self.assertEqual(rows, [])

    def test_boundary_stops_before_risk_assessment(self):
        """File Impact rows do not bleed into Risk Assessment."""
        content = (
            "### File Impact\n\n"
            "| File | Action | What Changes |\n"
            "| --- | --- | --- |\n"
            "| src/a.py | Modify | Change |\n\n"
            "## Risk Assessment\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "| --- | --- | --- | --- |\n"
            "| Something | Low | Low | Mitigation |\n"
        )
        rows = plan_helper._parse_file_impact_rows(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].file, "src/a.py")


class ParsePureBuilderTargetsTests(unittest.TestCase):
    def test_parses_real_rows(self):
        content = (
            "### Pure-Builder Targets\n\n"
            "| Target | File | Why pure |\n"
            "| --- | --- | --- |\n"
            "| filterWidgetsByQuery | src/widgets/widget_filter.ts | No I/O |\n"
            "| normalizeTagList | src/widgets/tag_utils.ts | Pure transform |\n"
            "| [target] | [file] | [why] |\n"
        )
        rows = plan_helper._parse_pure_builder_targets(content)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].target, "filterWidgetsByQuery")
        self.assertEqual(rows[1].file, "src/widgets/tag_utils.ts")

    def test_why_column_optional_defaults_empty(self):
        """A row with only Target + File columns (no Why) still parses."""
        content = (
            "### Pure-Builder Targets\n\n"
            "| Target | File |\n"
            "| --- | --- |\n"
            "| fn | f.ts |\n"
        )
        rows = plan_helper._parse_pure_builder_targets(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].why, "")

    def test_section_absent_returns_empty(self):
        rows = plan_helper._parse_pure_builder_targets("## Summary\n\nNothing.\n")
        self.assertEqual(rows, [])

    def test_placeholder_row_skipped(self):
        content = (
            "### Pure-Builder Targets\n\n"
            "| Target | File | Why pure |\n"
            "| --- | --- | --- |\n"
            "| fn | f.ts | Pure |\n"
            "| [target] | [file] | [why] |\n"
        )
        rows = plan_helper._parse_pure_builder_targets(content)
        self.assertEqual(len(rows), 1)

    def test_boundary_stops_before_risk_assessment(self):
        """Pure-Builder Targets rows do not bleed into Risk Assessment."""
        content = (
            "### Pure-Builder Targets\n\n"
            "| Target | File | Why pure |\n"
            "| --- | --- | --- |\n"
            "| fn | f.ts | Pure |\n\n"
            "## Risk Assessment\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "| --- | --- | --- | --- |\n"
            "| Something | Low | Low | Mitigation |\n"
        )
        rows = plan_helper._parse_pure_builder_targets(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].target, "fn")

    def test_case_insensitive_heading(self):
        """Heading matching is case-insensitive, matching sibling parsers."""
        content = (
            "### pure-builder targets\n\n"
            "| Target | File | Why pure |\n"
            "| --- | --- | --- |\n"
            "| fn | f.ts | Pure |\n"
        )
        rows = plan_helper._parse_pure_builder_targets(content)
        self.assertEqual(len(rows), 1)


class ParseDeadCodeRowsTests(unittest.TestCase):
    def test_parses_real_rows(self):
        content = (
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "| --- | --- | --- | --- |\n"
            "| src/widgets/widget_filter.ts | : 'legacyRegionCode' | arm | Superseded |\n"
            "| src/widgets/legacy_filter.ts | applyLegacyTagFilter | function | Replaced |\n"
            "| [file] | [anchor] | [kind] | [why] |\n"
        )
        rows = plan_helper._parse_dead_code_rows(content)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].file, "src/widgets/widget_filter.ts")
        self.assertEqual(rows[0].kind, "arm")
        self.assertEqual(rows[1].anchor_token, "applyLegacyTagFilter")
        self.assertEqual(rows[1].kind, "function")

    def test_section_absent_returns_empty(self):
        rows = plan_helper._parse_dead_code_rows("## Summary\n\nNothing.\n")
        self.assertEqual(rows, [])

    def test_placeholder_row_skipped(self):
        content = (
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "| --- | --- | --- | --- |\n"
            "| f.ts | tok | arm | Dead |\n"
            "| [file] | [anchor] | [kind] | [why] |\n"
        )
        rows = plan_helper._parse_dead_code_rows(content)
        self.assertEqual(len(rows), 1)

    def test_invalid_kind_row_skipped(self):
        """A row whose Kind is not in DEAD_CODE_KIND_ENUM fails DeadCodeRow
        construction and is silently skipped (mirrors sibling parsers'
        try/except-around-construction malformed-row handling)."""
        content = (
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "| --- | --- | --- | --- |\n"
            "| f.ts | tok | arm | Dead |\n"
            "| f2.ts | tok2 | bogus-kind | Dead too |\n"
        )
        rows = plan_helper._parse_dead_code_rows(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].file, "f.ts")

    def test_empty_why_dead_row_skipped(self):
        """A row with an empty Why dead column fails DeadCodeRow
        construction (why_dead is required non-empty) and is skipped."""
        content = (
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind |\n"
            "| --- | --- | --- |\n"
            "| f.ts | tok | arm |\n"
        )
        rows = plan_helper._parse_dead_code_rows(content)
        self.assertEqual(rows, [])

    def test_boundary_stops_before_risk_assessment(self):
        """Change-Induced Dead Code rows do not bleed into Risk Assessment."""
        content = (
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "| --- | --- | --- | --- |\n"
            "| f.ts | tok | arm | Dead |\n\n"
            "## Risk Assessment\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "| --- | --- | --- | --- |\n"
            "| Something | Low | Low | Mitigation |\n"
        )
        rows = plan_helper._parse_dead_code_rows(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].file, "f.ts")

    def test_case_insensitive_heading(self):
        """Heading matching is case-insensitive, matching sibling parsers."""
        content = (
            "### change-induced dead code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "| --- | --- | --- | --- |\n"
            "| f.ts | tok | arm | Dead |\n"
        )
        rows = plan_helper._parse_dead_code_rows(content)
        self.assertEqual(len(rows), 1)


class ParseDeadCodeRowsFullFnTests(unittest.TestCase):
    """Direct unit tests of _parse_dead_code_rows_full (plan 71 D9 finding-C
    UX close): the (rows, warnings) pair _parse_dead_code_rows wraps."""

    def test_all_valid_rows_no_warnings(self):
        content = (
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "| --- | --- | --- | --- |\n"
            "| f.ts | tok | arm | Dead |\n"
        )
        rows, warnings = plan_helper._parse_dead_code_rows_full(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(warnings, [])

    def test_section_absent_returns_empty_rows_and_warnings(self):
        rows, warnings = plan_helper._parse_dead_code_rows_full(
            "## Summary\n\nNothing.\n"
        )
        self.assertEqual(rows, [])
        self.assertEqual(warnings, [])

    def test_semicolon_token_row_produces_one_warning_naming_the_row(self):
        """A row whose Anchor token contains a semicolon fails DeadCodeRow
        construction (finding C) -- excluded from rows, one warning naming
        the file + anchor_token + reason."""
        content = (
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "| --- | --- | --- | --- |\n"
            "| src/loop.ts | for (i = 0; i < n; i++) | branch | Superseded loop |\n"
        )
        rows, warnings = plan_helper._parse_dead_code_rows_full(content)
        self.assertEqual(rows, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("src/loop.ts", warnings[0])
        self.assertIn("semicolon", warnings[0])

    def test_invalid_kind_row_produces_one_warning(self):
        content = (
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "| --- | --- | --- | --- |\n"
            "| f.ts | tok | bogus | Dead |\n"
        )
        rows, warnings = plan_helper._parse_dead_code_rows_full(content)
        self.assertEqual(rows, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("f.ts", warnings[0])
        self.assertIn("tok", warnings[0])

    def test_mixed_valid_and_invalid_rows_one_warning_one_row(self):
        content = (
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "| --- | --- | --- | --- |\n"
            "| good.ts | goodToken | arm | Fine |\n"
            "| bad.ts | for (i = 0; i < n; i++) | branch | Also dead |\n"
        )
        rows, warnings = plan_helper._parse_dead_code_rows_full(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].file, "good.ts")
        self.assertEqual(len(warnings), 1)
        self.assertIn("bad.ts", warnings[0])

    def test_placeholder_row_produces_no_warning(self):
        """A placeholder row is skipped silently (same as _parse_dead_code_rows)
        -- it is not a malformed AUTHORED row, so it must not WARN."""
        content = (
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "| --- | --- | --- | --- |\n"
            "| [file] | [anchor] | [kind] | [why] |\n"
        )
        rows, warnings = plan_helper._parse_dead_code_rows_full(content)
        self.assertEqual(rows, [])
        self.assertEqual(warnings, [])


class ParseDocImpactRowsTests(unittest.TestCase):
    def test_parses_real_rows(self):
        content = (
            "### Documentation Impact\n\n"
            "| Doc File | Action | What Changes |\n"
            "| --- | --- | --- |\n"
            "| docs/widgets/overview.md | Update | Document new search capability |\n"
            "| docs/widgets/architecture.md | Update | Add filter predicate injection pattern |\n"
            "| [path] | Update | [brief description] |\n"
        )
        rows = plan_helper._parse_doc_impact_rows(content)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].doc_file, "docs/widgets/overview.md")
        self.assertEqual(rows[1].action, "Update")

    def test_placeholder_row_skipped(self):
        content = (
            "### Documentation Impact\n\n"
            "| Doc File | Action | What Changes |\n"
            "| --- | --- | --- |\n"
            "| [path] | Update | [brief description] |\n"
            "| _(none)_ | — | — |\n"
        )
        rows = plan_helper._parse_doc_impact_rows(content)
        self.assertEqual(rows, [])

    def test_section_absent_returns_empty(self):
        rows = plan_helper._parse_doc_impact_rows("## Summary\n\nNothing.\n")
        self.assertEqual(rows, [])

    def test_boundary_stops_before_next_section(self):
        """Documentation Impact rows do not bleed into the Risk Assessment section."""
        content = (
            "### Documentation Impact\n\n"
            "| Doc File | Action | What Changes |\n"
            "| --- | --- | --- |\n"
            "| docs/api.md | Update | Describe new endpoint |\n\n"
            "## Risk Assessment\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "| --- | --- | --- | --- |\n"
            "| Schema drift | Low | Med | Pin version |\n"
        )
        rows = plan_helper._parse_doc_impact_rows(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].doc_file, "docs/api.md")


class ParseRiskRowsTests(unittest.TestCase):
    def test_parses_real_rows(self):
        content = (
            "## Risk Assessment\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "| --- | --- | --- | --- |\n"
            "| Cache stale | Low | Med | TTL |\n"
            "| Tag missing | Low | Low | Empty string fallback |\n"
            "| [risk] | Low/Med/High | Low/Med/High | [how to handle] |\n"
        )
        rows = plan_helper._parse_risk_rows(content)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].risk, "Cache stale")

    def test_section_absent_returns_empty(self):
        rows = plan_helper._parse_risk_rows("## Summary\n\nNothing.\n")
        self.assertEqual(rows, [])


class ParseSpecialistConsultationTests(unittest.TestCase):
    def test_parses_real_row_skips_none_and_template(self):
        content = (
            "## Specialist Consultation\n\n"
            "| Specialist | Sub-question | Input summary | Verdict | Cites |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| backend-engineer | Server-side? | No — spec §7 | accepted | spec.md §7 |\n"
            "| db-engineer | <the specific sub-question> | <1-line summary> | accepted | <file:line> |\n"
            "| (none) | — | — | — | — |\n"
        )
        rows = plan_helper._parse_specialist_consultation(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].specialist, "backend-engineer")
        self.assertEqual(rows[0].verdict, "accepted")

    def test_no_real_rows_returns_empty(self):
        content = (
            "## Specialist Consultation\n\n"
            "| Specialist | Sub-question | Input summary | Verdict | Cites |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| (none) | — | — | — | — |\n"
        )
        rows = plan_helper._parse_specialist_consultation(content)
        self.assertEqual(rows, [])

    def test_section_absent_returns_empty(self):
        rows = plan_helper._parse_specialist_consultation("## Summary\n\nNo consultations.\n")
        self.assertEqual(rows, [])

    def test_all_verdict_values_accepted(self):
        for verdict in ("accepted", "modified", "rejected", "no-response"):
            content = (
                "## Specialist Consultation\n\n"
                "| Specialist | Sub-question | Input summary | Verdict | Cites |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| specialist-x | Question? | Summary. | {0} | own-reasoning |\n"
            ).format(verdict)
            rows = plan_helper._parse_specialist_consultation(content)
            self.assertEqual(len(rows), 1, "verdict={0} should be accepted".format(verdict))
            self.assertEqual(rows[0].verdict, verdict)

    def test_invalid_verdict_row_skipped(self):
        content = (
            "## Specialist Consultation\n\n"
            "| Specialist | Sub-question | Input summary | Verdict | Cites |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| backend-engineer | Q? | S. | pending | own-reasoning |\n"
        )
        rows = plan_helper._parse_specialist_consultation(content)
        self.assertEqual(rows, [])


class ParseDependenciesTests(unittest.TestCase):
    def test_returns_non_blank_lines(self):
        content = (
            "## Dependencies\n\n"
            "No external package dependencies.\n"
            "Requires widget-core >= 1.0.\n"
        )
        deps = plan_helper._parse_dependencies(content)
        self.assertEqual(len(deps), 2)
        self.assertIn("No external package dependencies.", deps)

    def test_empty_section_returns_empty_list(self):
        content = "## Dependencies\n\n"
        deps = plan_helper._parse_dependencies(content)
        self.assertEqual(deps, [])

    def test_section_absent_returns_empty_list(self):
        deps = plan_helper._parse_dependencies("## Summary\n\nNothing.\n")
        self.assertEqual(deps, [])

    def test_blank_lines_not_included(self):
        content = (
            "## Dependencies\n\n"
            "\n"
            "widget-core >= 1.0\n"
            "\n"
        )
        deps = plan_helper._parse_dependencies(content)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0], "widget-core >= 1.0")


class IsPlaceholderCellTests(unittest.TestCase):
    def test_bracketed_placeholders(self):
        for text in ("[path]", "[decision]", "[risk]", "[any placeholder]", "[foo bar]"):
            self.assertTrue(
                plan_helper._is_placeholder_cell(text),
                "{0!r} should be placeholder".format(text),
            )

    def test_none_placeholders(self):
        self.assertTrue(plan_helper._is_placeholder_cell("_(none)_"))
        self.assertTrue(plan_helper._is_placeholder_cell("(none)"))

    def test_real_values_not_placeholder(self):
        for text in ("src/a.py", "Domain", "Cache stale", "backend-engineer"):
            self.assertFalse(
                plan_helper._is_placeholder_cell(text),
                "{0!r} should NOT be placeholder".format(text),
            )

    def test_whitespace_stripped(self):
        self.assertTrue(plan_helper._is_placeholder_cell("  [path]  "))
        self.assertTrue(plan_helper._is_placeholder_cell("  _(none)_  "))


if __name__ == "__main__":
    unittest.main()
