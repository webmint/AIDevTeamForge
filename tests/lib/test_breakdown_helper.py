"""Tests for src/devforge/lib/_breakdown/handoff_schema.py.

Phase 0 schema tests only. This file will grow in later phases as
breakdown_helper.py verbs are implemented.

Coverage:
  - Valid construction of TaskRow (empty lists, populated lists)
  - Valid construction of Provenance (both-None, both-set with kind="plan")
  - Valid construction of a full Breakdown record
  - Every rejection path for TaskRow
  - Every rejection path for Provenance
  - Every rejection path for Breakdown

Stdlib only.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_LIB_DIR = REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _breakdown.handoff_schema import (  # noqa: E402
    Breakdown,
    Provenance,
    TaskRow,
    SCHEMA_VERSION,
    HANDOFF_KIND,
    REVIEW_CHECKPOINT_ENUM,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_task_row(**overrides):
    """Return a valid TaskRow with minimal populated fields."""
    defaults = dict(
        number="001",
        title="Define types",
        agent="backend-engineer",
        depends_on=[],
        blocks=[],
        touched_files=[],
        expects=[],
        produces=[],
        ac_addressed=[],
        doc_refs=[],
        review_checkpoint=False,
    )
    defaults.update(overrides)
    return TaskRow(**defaults)


def _minimal_provenance(**overrides):
    """Return a valid Provenance (all-None by default)."""
    defaults = dict(
        upstream_handoff_path=None,
        upstream_handoff_kind=None,
        plan_path=None,
        spec_path=None,
    )
    defaults.update(overrides)
    return Provenance(**defaults)


def _minimal_breakdown(**overrides):
    """Return a valid Breakdown record."""
    defaults = dict(
        schema_version=SCHEMA_VERSION,
        handoff_kind=HANDOFF_KIND,
        tasks_dir="specs/001-widget-catalog/tasks",
        breakdown_completed_at="2026-05-24T12:00:00Z",
        provenance=_minimal_provenance(),
        tasks=[],
        additions=[],
        dependency_graph="",
    )
    defaults.update(overrides)
    return Breakdown(**defaults)


# ---------------------------------------------------------------------------
# TaskRow tests
# ---------------------------------------------------------------------------


class TestTaskRowValid(unittest.TestCase):
    """TaskRow valid construction."""

    def test_empty_lists(self):
        row = _minimal_task_row()
        self.assertEqual(row.number, "001")
        self.assertEqual(row.title, "Define types")
        self.assertEqual(row.agent, "backend-engineer")
        self.assertEqual(row.depends_on, [])
        self.assertEqual(row.blocks, [])
        self.assertEqual(row.touched_files, [])
        self.assertEqual(row.expects, [])
        self.assertEqual(row.produces, [])
        self.assertEqual(row.ac_addressed, [])
        self.assertEqual(row.doc_refs, [])
        self.assertIs(row.review_checkpoint, False)

    def test_populated_lists(self):
        row = _minimal_task_row(
            number="002",
            title="Create repository layer",
            agent="architect",
            depends_on=["001"],
            blocks=["003", "004"],
            touched_files=["src/repo.py", "src/models.py"],
            expects=["TypeDefinitions"],
            produces=["RepositoryInterface"],
            ac_addressed=["AC-1", "AC-2"],
            doc_refs=["docs/architecture.md"],
            review_checkpoint=True,
        )
        self.assertEqual(row.number, "002")
        self.assertEqual(row.depends_on, ["001"])
        self.assertEqual(row.blocks, ["003", "004"])
        self.assertEqual(row.touched_files, ["src/repo.py", "src/models.py"])
        self.assertEqual(row.ac_addressed, ["AC-1", "AC-2"])
        self.assertIs(row.review_checkpoint, True)

    def test_review_checkpoint_true(self):
        row = _minimal_task_row(review_checkpoint=True)
        self.assertIs(row.review_checkpoint, True)

    def test_review_checkpoint_false(self):
        row = _minimal_task_row(review_checkpoint=False)
        self.assertIs(row.review_checkpoint, False)


class TestTaskRowRejectEmptyNumber(unittest.TestCase):
    def test_empty_string(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(number="")

    def test_whitespace_only(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(number="   ")

    def test_non_string(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(number=1)


class TestTaskRowRejectEmptyTitle(unittest.TestCase):
    def test_empty_string(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(title="")

    def test_whitespace_only(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(title="\t\n")

    def test_non_string(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(title=None)


class TestTaskRowRejectEmptyAgent(unittest.TestCase):
    def test_empty_string(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(agent="")

    def test_whitespace_only(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(agent=" ")

    def test_non_string(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(agent=42)


class TestTaskRowRejectNonListFields(unittest.TestCase):
    """All seven list fields must be lists."""

    def test_depends_on_not_list(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(depends_on="001")

    def test_blocks_not_list(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(blocks="002")

    def test_touched_files_not_list(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(touched_files="src/foo.py")

    def test_expects_not_list(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(expects="SomeContract")

    def test_produces_not_list(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(produces="SomeOutput")

    def test_ac_addressed_not_list(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(ac_addressed="AC-1")

    def test_doc_refs_not_list(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(doc_refs="docs/overview.md")

    def test_depends_on_none(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(depends_on=None)

    def test_blocks_tuple(self):
        # tuple is not a list
        with self.assertRaises(ValueError):
            _minimal_task_row(blocks=("002",))

    def test_ac_addressed_dict(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(ac_addressed={"AC-1": True})


class TestTaskRowRejectNonBoolReviewCheckpoint(unittest.TestCase):
    """review_checkpoint must be a strict bool; int must be rejected."""

    def test_int_one_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(review_checkpoint=1)

    def test_int_zero_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(review_checkpoint=0)

    def test_string_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(review_checkpoint="true")

    def test_none_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_task_row(review_checkpoint=None)


# ---------------------------------------------------------------------------
# Provenance tests
# ---------------------------------------------------------------------------


class TestProvenanceValid(unittest.TestCase):
    def test_all_none(self):
        prov = _minimal_provenance()
        self.assertIsNone(prov.upstream_handoff_path)
        self.assertIsNone(prov.upstream_handoff_kind)
        self.assertIsNone(prov.plan_path)
        self.assertIsNone(prov.spec_path)

    def test_both_set_kind_plan(self):
        prov = _minimal_provenance(
            upstream_handoff_path="specs/001-widget-catalog/plan-handoff.json",
            upstream_handoff_kind="plan",
        )
        self.assertEqual(prov.upstream_handoff_path, "specs/001-widget-catalog/plan-handoff.json")
        self.assertEqual(prov.upstream_handoff_kind, "plan")

    def test_plan_path_and_spec_path_populated(self):
        prov = _minimal_provenance(
            upstream_handoff_path="specs/001/plan-handoff.json",
            upstream_handoff_kind="plan",
            plan_path="specs/001/plan.md",
            spec_path="specs/001/spec.md",
        )
        self.assertEqual(prov.plan_path, "specs/001/plan.md")
        self.assertEqual(prov.spec_path, "specs/001/spec.md")

    def test_plan_path_only_no_upstream(self):
        # plan_path set without upstream is fine (both independent of co-vary)
        prov = _minimal_provenance(plan_path="specs/001/plan.md")
        self.assertEqual(prov.plan_path, "specs/001/plan.md")
        self.assertIsNone(prov.upstream_handoff_path)


class TestProvenanceRejectKindNotInEnum(unittest.TestCase):
    def test_kind_specify_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_provenance(
                upstream_handoff_path="specs/001/plan-handoff.json",
                upstream_handoff_kind="specify",
            )

    def test_kind_breakdown_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_provenance(
                upstream_handoff_path="specs/001/plan-handoff.json",
                upstream_handoff_kind="breakdown",
            )

    def test_kind_empty_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_provenance(
                upstream_handoff_path="specs/001/plan-handoff.json",
                upstream_handoff_kind="",
            )
        self.assertIn("non-empty", str(ctx.exception))


class TestProvenanceRejectCoVaryViolation(unittest.TestCase):
    """path set + kind None, or kind set + path None — both rejected."""

    def test_path_set_kind_none(self):
        with self.assertRaises(ValueError):
            _minimal_provenance(
                upstream_handoff_path="specs/001/plan-handoff.json",
                upstream_handoff_kind=None,
            )

    def test_kind_set_path_none(self):
        with self.assertRaises(ValueError):
            _minimal_provenance(
                upstream_handoff_path=None,
                upstream_handoff_kind="plan",
            )


class TestProvenanceRejectEmptyPlanPath(unittest.TestCase):
    """plan_path must be non-empty when not None (Fix 2)."""

    def test_empty_string_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_provenance(plan_path="")

    def test_whitespace_only_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_provenance(plan_path="   ")

    def test_none_accepted(self):
        # None is the canonical absent sentinel — must be accepted.
        prov = _minimal_provenance(plan_path=None)
        self.assertIsNone(prov.plan_path)

    def test_valid_path_accepted(self):
        prov = _minimal_provenance(plan_path="specs/001/plan.md")
        self.assertEqual(prov.plan_path, "specs/001/plan.md")


class TestProvenanceRejectEmptySpecPath(unittest.TestCase):
    """spec_path must be non-empty when not None (Fix 2)."""

    def test_empty_string_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_provenance(spec_path="")

    def test_whitespace_only_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_provenance(spec_path="   ")

    def test_none_accepted(self):
        # None is the canonical absent sentinel — must be accepted.
        prov = _minimal_provenance(spec_path=None)
        self.assertIsNone(prov.spec_path)

    def test_valid_path_accepted(self):
        prov = _minimal_provenance(spec_path="specs/001/spec.md")
        self.assertEqual(prov.spec_path, "specs/001/spec.md")


# ---------------------------------------------------------------------------
# Breakdown top-level tests
# ---------------------------------------------------------------------------


class TestBreakdownValid(unittest.TestCase):
    def test_minimal_empty(self):
        bd = _minimal_breakdown()
        self.assertEqual(bd.schema_version, SCHEMA_VERSION)
        self.assertEqual(bd.handoff_kind, HANDOFF_KIND)
        self.assertEqual(bd.tasks_dir, "specs/001-widget-catalog/tasks")
        self.assertEqual(bd.breakdown_completed_at, "2026-05-24T12:00:00Z")
        self.assertIsInstance(bd.provenance, Provenance)
        self.assertEqual(bd.tasks, [])
        self.assertEqual(bd.additions, [])
        self.assertEqual(bd.dependency_graph, "")

    def test_with_tasks(self):
        task = _minimal_task_row(
            number="001",
            title="Define types",
            agent="architect",
            ac_addressed=["AC-1"],
        )
        bd = _minimal_breakdown(tasks=[task])
        self.assertEqual(len(bd.tasks), 1)
        self.assertEqual(bd.tasks[0].number, "001")

    def test_with_additions_and_graph(self):
        bd = _minimal_breakdown(
            additions=["Note: schema migration required"],
            dependency_graph="001 -> 002 -> 003",
        )
        self.assertEqual(bd.additions, ["Note: schema migration required"])
        self.assertEqual(bd.dependency_graph, "001 -> 002 -> 003")

    def test_with_full_provenance(self):
        prov = _minimal_provenance(
            upstream_handoff_path="specs/001/plan-handoff.json",
            upstream_handoff_kind="plan",
            plan_path="specs/001/plan.md",
            spec_path="specs/001/spec.md",
        )
        bd = _minimal_breakdown(provenance=prov)
        self.assertEqual(bd.provenance.upstream_handoff_kind, "plan")


class TestBreakdownRejectWrongSchemaVersion(unittest.TestCase):
    def test_wrong_version(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(schema_version="2.0")

    def test_empty_version(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(schema_version="")

    def test_none_version(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(schema_version=None)


class TestBreakdownRejectWrongHandoffKind(unittest.TestCase):
    def test_kind_plan_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(handoff_kind="plan")

    def test_kind_specify_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(handoff_kind="specify")

    def test_empty_kind_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(handoff_kind="")


class TestBreakdownRejectEmptyTasksDir(unittest.TestCase):
    def test_empty_string(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(tasks_dir="")

    def test_whitespace_only(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(tasks_dir="  ")

    def test_non_string(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(tasks_dir=None)


class TestBreakdownRejectEmptyCompletedAt(unittest.TestCase):
    def test_empty_string(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(breakdown_completed_at="")

    def test_whitespace_only(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(breakdown_completed_at="\n")

    def test_non_string(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(breakdown_completed_at=0)


class TestBreakdownRejectNonProvenanceProvenance(unittest.TestCase):
    def test_dict_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(provenance={"upstream_handoff_path": None})

    def test_none_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(provenance=None)

    def test_string_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(provenance="specs/001/plan-handoff.json")


class TestBreakdownRejectNonListTasks(unittest.TestCase):
    def test_none_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(tasks=None)

    def test_tuple_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(tasks=())

    def test_string_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(tasks="[]")


class TestBreakdownRejectNonListAdditions(unittest.TestCase):
    def test_none_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(additions=None)

    def test_string_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(additions="some note")


class TestBreakdownRejectNonStringDependencyGraph(unittest.TestCase):
    def test_none_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(dependency_graph=None)

    def test_list_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(dependency_graph=["001 -> 002"])

    def test_int_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(dependency_graph=0)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants(unittest.TestCase):
    def test_schema_version(self):
        self.assertEqual(SCHEMA_VERSION, "1.0")

    def test_handoff_kind(self):
        self.assertEqual(HANDOFF_KIND, "breakdown")

    def test_review_checkpoint_enum(self):
        self.assertEqual(REVIEW_CHECKPOINT_ENUM, (True, False))


# ---------------------------------------------------------------------------
# Phase 1 — breakdown_helper.py verb tests
# ---------------------------------------------------------------------------
#
# All CLI tests invoke breakdown_helper.py as a subprocess from a temporary
# directory (mirrors test_plan_helper.py conventions).
# The round-trip test for read-plan-handoff runs the REAL
# `plan_helper finalize-handoff` to produce plan-handoff.json, then asserts
# the rendered block matches the seeded content.

import os
import re
import subprocess
import tempfile
import time

REPO_ROOT_P1 = Path(__file__).resolve().parents[2]
BREAKDOWN_HELPER_PY = REPO_ROOT_P1 / "src" / "devforge" / "lib" / "breakdown_helper.py"
BREAKDOWN_HELPER_SHIM = REPO_ROOT_P1 / "src" / "devforge" / "lib" / "breakdown_helper"
PLAN_HELPER_PY = REPO_ROOT_P1 / "src" / "devforge" / "lib" / "plan_helper.py"
_LIB_DIR_P1 = REPO_ROOT_P1 / "src" / "devforge" / "lib"

if str(_LIB_DIR_P1) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR_P1))


def _run_bh(cwd, *args):
    """Invoke breakdown_helper.py as a subprocess from cwd."""
    return subprocess.run(
        [sys.executable, str(BREAKDOWN_HELPER_PY)] + list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _write_minimal_plan(path, status="Draft"):
    """Write a minimal plan.md with frontmatter at the given path.

    Includes a ### File Impact table with 2 data rows and a
    ### Risk Assessment table with 1 data row so row-count assertions
    can verify non-zero values.
    """
    content = (
        "# Plan: Test Feature\n\n"
        "**Date**: 2026-01-01\n"
        "**Status**: {status}\n"
        "**Author**: Claude + User\n\n"
        "## Summary\n\nSome planned work.\n\n"
        "### Layer Map\n\n"
        "| Layer | What | Files |\n"
        "|-------|------|-------|\n"
        "| Domain | Define types | src/types.py |\n"
        "| Service | Add logic | src/service.py |\n\n"
        "### File Impact\n\n"
        "| File | Action | What Changes |\n"
        "|------|--------|---------------|\n"
        "| src/types.py | Create | New type definitions |\n"
        "| src/service.py | Modify | Add new method |\n\n"
        "### Key Design Decisions\n\n"
        "| Decision | Chosen Approach | Why | Alternatives Rejected |\n"
        "|----------|----------------|-----|-----------------------|\n"
        "| Data model | Use dataclass | Type-safe | dict (untyped) |\n\n"
        "## Risk Assessment\n\n"
        "| Risk | Likelihood | Impact | Mitigation |\n"
        "|------|-----------|--------|------------|\n"
        "| Schema drift | Low | High | Pin versions |\n\n"
        "## Dependencies\n\n"
        "- No external dependencies.\n\n"
        "## Specialist Consultation\n\n"
        "| Specialist | Sub-question | Input summary | Verdict | Cites |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| (none) | — | — | — | — |\n"
    ).format(status=status)
    Path(path).write_text(content, encoding="utf-8")


def _write_rich_plan(path, status="Approved"):
    """Write a richer plan.md used for the finalize-handoff round-trip test.

    Sections are populated so plan_helper finalize-handoff produces non-empty
    breakdown_seeds (layer_map, file_impact, key_design_decisions, risks,
    dependencies).  Section headings match plan_helper's parser patterns exactly.
    """
    content = (
        "# Plan: Widget Catalog Search\n\n"
        "**Date**: 2026-05-24\n"
        "**Status**: {status}\n"
        "**Author**: Claude + User\n\n"
        "## Summary\n\nBuild widget catalog search functionality.\n\n"
        "### Layer Map\n\n"
        "| Layer | What | Files |\n"
        "|-------|------|-------|\n"
        "| Domain | Widget entity + search contract | src/widgets/types.py |\n"
        "| Repository | WidgetRepo implementation | src/widgets/repo.py |\n"
        "| Service | Search orchestration | src/widgets/service.py |\n\n"
        "### Key Design Decisions\n\n"
        "| Decision | Chosen Approach | Why | Alternatives Rejected |\n"
        "|----------|----------------|-----|-----------------------|\n"
        "| Storage | SQLite FTS5 | Built-in, no deps | Postgres (infra cost) |\n"
        "| API shape | REST GET /widgets?q= | Standard | GraphQL (overkill) |\n\n"
        "### File Impact\n\n"
        "| File | Action | What Changes |\n"
        "|------|--------|---------------|\n"
        "| src/widgets/types.py | Create | Widget dataclass + SearchQuery |\n"
        "| src/widgets/repo.py | Create | WidgetRepo with FTS5 queries |\n"
        "| src/widgets/service.py | Modify | Add search_widgets method |\n\n"
        "### Documentation Impact\n\n"
        "| Doc File | Action | What Changes |\n"
        "|----------|--------|---------------|\n"
        "| docs/widgets/overview.md | Modify | Add search section |\n\n"
        "## Risk Assessment\n\n"
        "| Risk | Likelihood | Impact | Mitigation |\n"
        "|------|-----------|--------|------------|\n"
        "| FTS5 not available | Low | High | Check at startup |\n"
        "| Query injection | Med | High | Parameterized queries |\n\n"
        "## Specialist Consultation\n\n"
        "| Specialist | Sub-question | Input summary | Verdict | Cites |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| (none) | — | — | — | — |\n\n"
        "## Dependencies\n\n"
        "- Python sqlite3 stdlib FTS5 module.\n"
        "- No new third-party packages.\n"
    ).format(status=status)
    Path(path).write_text(content, encoding="utf-8")


class _CwdIsolationBH(unittest.TestCase):
    """Base class that restores cwd and provides a tmp dir."""

    def setUp(self):
        self._saved_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        os.chdir(self._saved_cwd)
        self._tmp.cleanup()


# ---------------------------------------------------------------------------
# Tests: pick-plan
# ---------------------------------------------------------------------------


class PickPlanTests(_CwdIsolationBH):

    def test_pick_plan_explicit_valid_path(self):
        """Explicit plan.md path → prints absolute path, exit 0."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "pick-plan", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(plan.resolve()))

    def test_pick_plan_explicit_directory_rejected(self):
        """Directory path → exit 2 with descriptive stderr."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)

        result = _run_bh(self.tmp_path, "pick-plan", str(specs_dir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("directory", result.stderr.lower())

    def test_pick_plan_explicit_wrong_basename_rejected(self):
        """File with basename != plan.md → exit 2."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        spec = specs_dir / "spec.md"
        spec.write_text("# not a plan\n", encoding="utf-8")

        result = _run_bh(self.tmp_path, "pick-plan", str(spec))
        self.assertEqual(result.returncode, 2)
        self.assertIn("plan.md", result.stderr)

    def test_pick_plan_explicit_nonexistent_exits_2(self):
        """Non-existent path → exit 2."""
        result = _run_bh(self.tmp_path, "pick-plan", "no/such/plan.md")
        self.assertEqual(result.returncode, 2)

    def test_pick_plan_no_arg_picks_most_recent(self):
        """Two plans under specs/; highest mtime is auto-picked."""
        specs_dir = self.tmp_path / "specs"
        older_dir = specs_dir / "001-older"
        newer_dir = specs_dir / "002-newer"
        older_dir.mkdir(parents=True)
        newer_dir.mkdir(parents=True)

        older = older_dir / "plan.md"
        newer = newer_dir / "plan.md"
        _write_minimal_plan(str(older))
        _write_minimal_plan(str(newer))

        # Force mtime difference.
        old_time = time.time() - 3600
        os.utime(str(older), (old_time, old_time))
        new_time = time.time()
        os.utime(str(newer), (new_time, new_time))

        result = _run_bh(self.tmp_path, "pick-plan")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(newer.resolve()))

    def test_pick_plan_no_arg_no_specs_exits_2(self):
        """No specs/ dir → exit 2."""
        result = _run_bh(self.tmp_path, "pick-plan")
        self.assertEqual(result.returncode, 2)

    def test_pick_plan_no_arg_empty_specs_exits_2(self):
        """Empty specs/ dir → exit 2."""
        (self.tmp_path / "specs").mkdir()
        result = _run_bh(self.tmp_path, "pick-plan")
        self.assertEqual(result.returncode, 2)

    def test_pick_plan_explicit_relative_path(self):
        """Relative path resolved against cwd."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "pick-plan", "specs/001-test/plan.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(plan.resolve()))


# ---------------------------------------------------------------------------
# Tests: render-pick-summary
# ---------------------------------------------------------------------------


class RenderPickSummaryPlanTests(_CwdIsolationBH):

    def _parse_summary(self, stdout):
        """Parse the 5-line summary into a dict."""
        result = {}
        for line in stdout.splitlines():
            if line.startswith("**Plan**:"):
                result["plan"] = line.split(":", 1)[1].strip()
            elif line.startswith("**Status**:"):
                result["status"] = line.split(":", 1)[1].strip()
            elif line.startswith("**File-impact rows**:"):
                result["fi_rows"] = line.split(":", 1)[1].strip()
            elif line.startswith("**Risk rows**:"):
                result["risk_rows"] = line.split(":", 1)[1].strip()
            elif line.startswith("**Last modified**:"):
                result["last_modified"] = line.split(":", 1)[1].strip()
        return result

    def test_render_pick_summary_five_lines(self):
        """Output has exactly 5 non-blank lines."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "render-pick-summary", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(len(lines), 5)

    def test_render_pick_summary_exact_keys(self):
        """All 5 expected keys present in output."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "render-pick-summary", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = self._parse_summary(result.stdout)
        for key in ("plan", "status", "fi_rows", "risk_rows", "last_modified"):
            self.assertIn(key, parsed, "missing key: " + key)

    def test_render_pick_summary_status_draft(self):
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan), status="Draft")

        result = _run_bh(self.tmp_path, "render-pick-summary", str(plan))
        parsed = self._parse_summary(result.stdout)
        self.assertEqual(parsed["status"], "Draft")

    def test_render_pick_summary_status_approved(self):
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan), status="Approved")

        result = _run_bh(self.tmp_path, "render-pick-summary", str(plan))
        parsed = self._parse_summary(result.stdout)
        self.assertEqual(parsed["status"], "Approved")

    def test_render_pick_summary_status_missing_shows_unknown(self):
        """Plan without **Status**: line reports 'unknown'."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        plan.write_text(
            "# Plan: No Status\n\n**Date**: 2026-01-01\n\n## Summary\n\nWork.\n",
            encoding="utf-8",
        )
        result = _run_bh(self.tmp_path, "render-pick-summary", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = self._parse_summary(result.stdout)
        self.assertEqual(parsed["status"], "unknown")

    def test_render_pick_summary_row_counts_correct(self):
        """Row counts match the data rows in the minimal plan fixture (2 FI, 1 risk)."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "render-pick-summary", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = self._parse_summary(result.stdout)
        self.assertEqual(parsed["fi_rows"], "2")
        self.assertEqual(parsed["risk_rows"], "1")

    def test_render_pick_summary_zero_rows_on_empty_plan(self):
        """Plan with no File Impact or Risk Assessment tables → both counts = 0."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        plan.write_text(
            "# Plan: Minimal\n\n**Date**: 2026-01-01\n**Status**: Draft\n\n## Summary\n\nWork.\n",
            encoding="utf-8",
        )
        result = _run_bh(self.tmp_path, "render-pick-summary", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = self._parse_summary(result.stdout)
        self.assertEqual(parsed["fi_rows"], "0")
        self.assertEqual(parsed["risk_rows"], "0")

    def test_render_pick_summary_missing_file_exits_2(self):
        result = _run_bh(self.tmp_path, "render-pick-summary", "no/such/plan.md")
        self.assertEqual(result.returncode, 2)

    def test_render_pick_summary_plan_path_in_output(self):
        """**Plan**: line contains the given path."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "render-pick-summary", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(plan), result.stdout)


# ---------------------------------------------------------------------------
# Tests: list-plans
# ---------------------------------------------------------------------------


class ListPlansTests(_CwdIsolationBH):

    def test_list_plans_sorted_by_mtime_desc(self):
        """3 plans; output order matches mtime desc."""
        specs_dir = self.tmp_path / "specs"
        for name in ("001-alpha", "002-beta", "003-gamma"):
            d = specs_dir / name
            d.mkdir(parents=True)
            _write_minimal_plan(str(d / "plan.md"))

        base = time.time()
        os.utime(str(specs_dir / "001-alpha" / "plan.md"), (base - 200, base - 200))
        os.utime(str(specs_dir / "002-beta" / "plan.md"), (base - 100, base - 100))
        os.utime(str(specs_dir / "003-gamma" / "plan.md"), (base, base))

        result = _run_bh(self.tmp_path, "list-plans")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(len(lines), 3)
        self.assertIn("003-gamma", lines[0])
        self.assertIn("002-beta", lines[1])
        self.assertIn("001-alpha", lines[2])

    def test_list_plans_empty_specs_dir(self):
        """Empty specs/ → exit 0, no output."""
        (self.tmp_path / "specs").mkdir()
        result = _run_bh(self.tmp_path, "list-plans")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_list_plans_missing_specs_dir_exits_2(self):
        """No specs/ dir → exit 2."""
        result = _run_bh(self.tmp_path, "list-plans")
        self.assertEqual(result.returncode, 2)

    def test_list_plans_output_format(self):
        """Lines follow '<N>) <relative-path> [Status: <X>]' format."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        _write_minimal_plan(str(specs_dir / "plan.md"), status="Draft")

        result = _run_bh(self.tmp_path, "list-plans")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertTrue(line.startswith("1)"), line)
        self.assertIn("[Status:", line)
        self.assertIn("Draft", line)

    def test_list_plans_only_plan_md_found(self):
        """spec.md files are NOT listed (only plan.md)."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        # Write a spec.md but NOT plan.md.
        (specs_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

        result = _run_bh(self.tmp_path, "list-plans")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")


# ---------------------------------------------------------------------------
# Tests: check-status-and-flip (on plan.md)
# ---------------------------------------------------------------------------


class CheckStatusAndFlipPlanTests(_CwdIsolationBH):

    def test_flip_draft_to_approved(self):
        """Draft plan → file rewritten to Approved, stdout 'flipped'."""
        plan = self.tmp_path / "plan.md"
        _write_minimal_plan(str(plan), status="Draft")

        result = _run_bh(self.tmp_path, "check-status-and-flip", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "flipped")

        disk = plan.read_text(encoding="utf-8")
        self.assertIn("**Status**: Approved", disk)
        self.assertNotIn("**Status**: Draft", disk)

    def test_already_approved_idempotent(self):
        """Approved plan → stdout 'already-approved', no file change."""
        plan = self.tmp_path / "plan.md"
        _write_minimal_plan(str(plan), status="Approved")
        mtime_before = os.path.getmtime(str(plan))

        result = _run_bh(self.tmp_path, "check-status-and-flip", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "already-approved")

        mtime_after = os.path.getmtime(str(plan))
        self.assertAlmostEqual(mtime_before, mtime_after, delta=0.01)

    def test_complete_no_rewrite(self):
        """Complete plan → stdout 'complete', no file change."""
        plan = self.tmp_path / "plan.md"
        _write_minimal_plan(str(plan), status="Complete")

        result = _run_bh(self.tmp_path, "check-status-and-flip", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "complete")
        disk = plan.read_text(encoding="utf-8")
        self.assertIn("**Status**: Complete", disk)

    def test_unknown_status_no_flip(self):
        """Unknown status → stdout 'unknown-status:<value>', no rewrite."""
        plan = self.tmp_path / "plan.md"
        _write_minimal_plan(str(plan), status="In Review")
        mtime_before = plan.stat().st_mtime_ns

        result = _run_bh(self.tmp_path, "check-status-and-flip", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "unknown-status:In Review")
        self.assertEqual(plan.stat().st_mtime_ns, mtime_before)

    def test_missing_status_inserts_after_date(self):
        """Plan without Status → inserts Approved after Date, stdout 'inserted'."""
        content = (
            "# Plan: Test\n\n"
            "**Date**: 2026-01-01\n"
            "**Author**: Claude\n\n"
            "## Summary\n\nWork.\n"
        )
        plan = self.tmp_path / "plan.md"
        plan.write_text(content, encoding="utf-8")

        result = _run_bh(self.tmp_path, "check-status-and-flip", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "inserted")

        disk = plan.read_text(encoding="utf-8")
        self.assertIn("**Status**: Approved", disk)
        date_pos = disk.index("**Date**:")
        status_pos = disk.index("**Status**: Approved")
        self.assertGreater(status_pos, date_pos)

    def test_malformed_no_date_no_status_exits_2(self):
        """Plan with neither Date nor Status → exit 2."""
        plan = self.tmp_path / "plan.md"
        plan.write_text(
            "# Plan: Bad\n\nNo frontmatter.\n\n## Summary\n\nWork.\n",
            encoding="utf-8",
        )
        result = _run_bh(self.tmp_path, "check-status-and-flip", str(plan))
        self.assertEqual(result.returncode, 2)
        self.assertIn("malformed", result.stderr.lower())

    def test_missing_file_exits_2(self):
        result = _run_bh(self.tmp_path, "check-status-and-flip", "no/plan.md")
        self.assertEqual(result.returncode, 2)

    def test_atomic_no_tmp_file_survives(self):
        """After successful flip, no temp file survives in plan directory."""
        plan = self.tmp_path / "plan.md"
        _write_minimal_plan(str(plan), status="Draft")

        result = _run_bh(self.tmp_path, "check-status-and-flip", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)

        survivors = [p.name for p in self.tmp_path.iterdir()]
        self.assertIn("plan.md", survivors)
        for name in survivors:
            self.assertFalse(name.endswith(".tmp"), "tmp file survived: " + name)


# ---------------------------------------------------------------------------
# Tests: read-plan-handoff
# ---------------------------------------------------------------------------


class ReadPlanHandoffTests(_CwdIsolationBH):

    def _finalize_handoff(self, plan_path):
        """Run real plan_helper finalize-handoff on the given plan.md path.

        Returns the subprocess result. The handoff JSON is written as a sibling
        to plan.md (plan-handoff.json) by plan_helper.
        """
        return subprocess.run(
            [sys.executable, str(PLAN_HELPER_PY), "finalize-handoff", str(plan_path)],
            cwd=str(self.tmp_path),
            capture_output=True,
            text=True,
        )

    def test_no_sibling_prints_no_handoff(self):
        """No sibling plan-handoff.json → stdout 'no-handoff', exit 0."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "read-plan-handoff", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "no-handoff")

    def test_missing_plan_exits_2(self):
        """Non-existent plan path → exit 2."""
        result = _run_bh(self.tmp_path, "read-plan-handoff", "no/plan.md")
        self.assertEqual(result.returncode, 2)

    def test_malformed_json_sibling_exits_2(self):
        """Sibling plan-handoff.json with invalid JSON → exit 2."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))
        (specs_dir / "plan-handoff.json").write_text(
            "{ not valid json", encoding="utf-8"
        )

        result = _run_bh(self.tmp_path, "read-plan-handoff", str(plan))
        self.assertEqual(result.returncode, 2)

    def test_wrong_handoff_kind_exits_2(self):
        """Sibling with handoff_kind != 'plan' → exit 2."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))
        import json as _json
        (specs_dir / "plan-handoff.json").write_text(
            _json.dumps({
                "schema_version": "1.0",
                "handoff_kind": "specify",   # wrong kind
            }),
            encoding="utf-8",
        )

        result = _run_bh(self.tmp_path, "read-plan-handoff", str(plan))
        self.assertEqual(result.returncode, 2)
        self.assertIn("wrong kind", result.stderr)

    def test_wrong_schema_version_exits_2(self):
        """Sibling with schema_version != '1.0' → exit 2."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))
        import json as _json
        (specs_dir / "plan-handoff.json").write_text(
            _json.dumps({
                "schema_version": "2.0",    # wrong version
                "handoff_kind": "plan",
            }),
            encoding="utf-8",
        )

        result = _run_bh(self.tmp_path, "read-plan-handoff", str(plan))
        self.assertEqual(result.returncode, 2)
        self.assertIn("wrong schema_version", result.stderr)

    def test_round_trip_valid_handoff_renders_block(self):
        """ROUND-TRIP: plan_helper finalize-handoff → plan-handoff.json →
        read-plan-handoff renders ## Upstream plan seeds block.

        This test uses the REAL producer (plan_helper finalize-handoff) to
        produce plan-handoff.json from a synthetic rich plan.md, then
        exercises the consumer (breakdown_helper read-plan-handoff) and
        asserts the rendered block structure.
        """
        specs_dir = self.tmp_path / "specs" / "001-widget-catalog"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_rich_plan(str(plan), status="Approved")

        # PRODUCER: run real plan_helper finalize-handoff.
        finalize_result = self._finalize_handoff(plan)
        self.assertEqual(
            finalize_result.returncode, 0,
            "plan_helper finalize-handoff failed: " + finalize_result.stderr
        )
        sibling = specs_dir / "plan-handoff.json"
        self.assertTrue(sibling.exists(), "plan-handoff.json not created by finalize-handoff")

        # CONSUMER: run breakdown_helper read-plan-handoff.
        result = _run_bh(self.tmp_path, "read-plan-handoff", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        # Structural assertions.
        self.assertIn("## Upstream plan seeds", output)
        self.assertIn("### Layer Map", output)
        self.assertIn("### File Impact", output)
        self.assertIn("### Key Design Decisions", output)
        self.assertIn("### Dependencies", output)
        self.assertIn("### Risks", output)

        # The synthetic plan has seeded rows — they must appear in the output.
        # Layer Map: 3 rows: Domain, Repository, Service.
        self.assertIn("Domain", output)
        self.assertIn("Repository", output)
        self.assertIn("Service", output)

        # File Impact: 3 rows — src/widgets/types.py etc.
        self.assertIn("src/widgets/types.py", output)
        self.assertIn("src/widgets/repo.py", output)

        # Key Design Decisions: 2 rows.
        self.assertIn("SQLite FTS5", output)

        # Dependencies: 2 non-blank lines.
        self.assertIn("sqlite3", output)

        # Risks: 2 rows.
        self.assertIn("FTS5 not available", output)

        # Fix 3 guard: no double-bullet "- - " anywhere in the rendered block.
        self.assertNotIn("- - ", output)
        # The first dependency line must appear exactly once, not doubled.
        self.assertEqual(output.count("- Python sqlite3"), 1)

    def test_round_trip_empty_sections_render_none(self):
        """Round-trip on a minimal plan with placeholder-only tables renders _(none)_."""
        specs_dir = self.tmp_path / "specs" / "002-minimal"
        specs_dir.mkdir(parents=True)
        # Write a plan with NO data tables at all (no File Impact, no risks).
        plan = specs_dir / "plan.md"
        plan.write_text(
            "# Plan: Minimal\n\n"
            "**Date**: 2026-05-24\n"
            "**Status**: Approved\n\n"
            "## Summary\n\nMinimal work.\n\n"
            "## Risk Assessment\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "|------|-----------|--------|------------|\n"
            "| _(none)_ | | | |\n\n"
            "## Specialist Consultation\n\n"
            "| Specialist | Sub-question | Input summary | Verdict | Cites |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| (none) | — | — | — | — |\n\n"
            "## Dependencies\n\n",
            encoding="utf-8",
        )

        finalize_result = self._finalize_handoff(plan)
        self.assertEqual(
            finalize_result.returncode, 0,
            "plan_helper finalize-handoff failed: " + finalize_result.stderr
        )

        result = _run_bh(self.tmp_path, "read-plan-handoff", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn("## Upstream plan seeds", output)
        # All sub-sections should show _(none)_ when no data rows.
        self.assertIn("_(none)_", output)


# ---------------------------------------------------------------------------
# Spec fixture helper for Phase 2 tests.
# ---------------------------------------------------------------------------


def _write_minimal_spec(path, ac_count=3):
    """Write a minimal spec.md with ac_count ACs in section 5."""
    ac_lines = []
    for i in range(1, ac_count + 1):
        ac_lines.append(
            "- [ ] **AC-{0}**: The system does thing {0} correctly".format(i)
        )
    content = (
        "# Spec: Test Feature\n\n"
        "**Date**: 2026-01-01\n"
        "**Status**: Approved\n\n"
        "## 1. Overview\n\nOverview text.\n\n"
        "## 2. Current State\n\nCurrent state.\n\n"
        "## 3. Desired Behavior\n\nDesired behavior.\n\n"
        "## 4. Affected Areas\n\nAffected areas.\n\n"
        "## 5. Acceptance Criteria\n\n"
        "### 5.1 Core Behavior\n\n"
        "{ac_lines}\n\n"
        "## 6. Out of Scope\n\nOut of scope.\n\n"
        "## 7. Technical Constraints\n\nConstraints.\n\n"
        "## 8. Open Questions\n\nQuestions.\n\n"
        "## 9. Risks\n\nRisks.\n"
    ).format(ac_lines="\n".join(ac_lines))
    Path(path).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests: render-findings-from-plan (Phase 2, Verb 1)
# ---------------------------------------------------------------------------


class RenderFindingsFromPlanTests(_CwdIsolationBH):

    def test_file_impact_rows_appear_with_task_coverage_marker(self):
        """File Impact rows from plan.md appear with [TASK COVERAGE: ?]."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "render-findings-from-plan", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        # Minimal plan has 2 File Impact rows: src/types.py and src/service.py
        self.assertIn("src/types.py", output)
        self.assertIn("src/service.py", output)
        # Both must carry the marker
        self.assertIn("[TASK COVERAGE: ?]", output)
        # Count of markers for file impact rows
        self.assertGreaterEqual(output.count("[TASK COVERAGE: ?]"), 2)

    def test_layer_map_rows_appear_with_task_coverage_marker(self):
        """Layer Map rows from plan.md appear with [TASK COVERAGE: ?]."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "render-findings-from-plan", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        # Minimal plan has 2 Layer Map rows: Domain and Service
        self.assertIn("Domain", output)
        self.assertIn("Service", output)

    def test_file_impact_row_format(self):
        """File Impact rows follow '- <file> (<action>) [TASK COVERAGE: ?]' format."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "render-findings-from-plan", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        # Check for the exact format: "- src/types.py (Create) [TASK COVERAGE: ?]"
        self.assertIn("- src/types.py (Create) [TASK COVERAGE: ?]", output)
        self.assertIn("- src/service.py (Modify) [TASK COVERAGE: ?]", output)

    def test_layer_map_row_format(self):
        """Layer Map rows follow '- <layer>: <what> [TASK COVERAGE: ?]' format."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "render-findings-from-plan", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        # Minimal plan: "| Domain | Define types | src/types.py |"
        self.assertIn("- Domain: Define types [TASK COVERAGE: ?]", output)

    def test_no_spec_path_emits_deferral_line(self):
        """Without spec-path, AC coverage section emits the deferral sentinel."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "render-findings-from-plan", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        # The deferral line (no spec provided)
        self.assertIn("no spec provided", output)
        self.assertIn("verify-ac-coverage", output)
        # No [ADDRESSED BY: ?] markers when no spec is given
        self.assertNotIn("[ADDRESSED BY: ?]", output)

    def test_with_spec_path_acs_appear_with_addressed_by_marker(self):
        """With spec-path, each AC appears with [ADDRESSED BY: ?]."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        spec = specs_dir / "spec.md"
        _write_minimal_plan(str(plan))
        _write_minimal_spec(str(spec), ac_count=3)

        result = _run_bh(
            self.tmp_path, "render-findings-from-plan", str(plan), str(spec)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn("AC-1", output)
        self.assertIn("AC-2", output)
        self.assertIn("AC-3", output)
        self.assertEqual(output.count("[ADDRESSED BY: ?]"), 3)

    def test_with_spec_path_ac_snippet_appears(self):
        """The AC text snippet appears alongside the AC number."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        spec = specs_dir / "spec.md"
        _write_minimal_plan(str(plan))
        _write_minimal_spec(str(spec), ac_count=2)

        result = _run_bh(
            self.tmp_path, "render-findings-from-plan", str(plan), str(spec)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        # Spec fixture AC-1 text: "The system does thing 1 correctly"
        self.assertIn("The system does thing 1 correctly", output)

    def test_missing_plan_exits_2(self):
        """Non-existent plan path → exit 2."""
        result = _run_bh(self.tmp_path, "render-findings-from-plan", "no/plan.md")
        self.assertEqual(result.returncode, 2)

    def test_missing_plan_not_found_in_stderr(self):
        """stderr mentions the bad path."""
        result = _run_bh(self.tmp_path, "render-findings-from-plan", "no/plan.md")
        self.assertIn("no/plan.md", result.stderr)

    def test_header_present(self):
        """Output begins with '## Findings from Plan'."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "render-findings-from-plan", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            result.stdout.startswith("## Findings from Plan"),
            "Output did not start with expected header: " + result.stdout[:60],
        )

    def test_plan_with_no_file_impact_emits_none_sentinel(self):
        """Plan without a File Impact table emits a 'none' sentinel line."""
        plan = self.tmp_path / "plan.md"
        plan.write_text(
            "# Plan: Minimal\n\n**Date**: 2026-01-01\n**Status**: Draft\n\n## Summary\n\nWork.\n",
            encoding="utf-8",
        )
        result = _run_bh(self.tmp_path, "render-findings-from-plan", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        # Sentinel: "_(none — no File Impact table found in plan)_"
        self.assertIn("_(none —", result.stdout)

    def test_section_headers_present(self):
        """Output contains '### File Impact' and '### Layer Map' and '### AC Coverage'."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        result = _run_bh(self.tmp_path, "render-findings-from-plan", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn("### File Impact", output)
        self.assertIn("### Layer Map", output)
        self.assertIn("### AC Coverage", output)

    def test_unreadable_spec_path_gracefully_defers(self):
        """spec_path given but file does not exist → exit 0, deferral sentinel,
        no [ADDRESSED BY: ?] markers (Fix 2)."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        nonexistent_spec = str(specs_dir / "does-not-exist-spec.md")
        result = _run_bh(
            self.tmp_path,
            "render-findings-from-plan",
            str(plan),
            nonexistent_spec,
        )
        # Must exit 0 (graceful deferral, not an error).
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        # Sentinel phrases from the deferral path.
        self.assertIn("spec not readable", output)
        self.assertIn("verify-ac-coverage", output)
        # Must NOT emit AC coverage lines (no spec was parsed).
        self.assertNotIn("[ADDRESSED BY: ?]", output)

    def test_zero_ac_spec_emits_no_acs_sentinel(self):
        """Spec file with no ACs in §5 → exit 0, 'no ACs found in spec §5' sentinel,
        no [ADDRESSED BY: ?] markers (Fix 3)."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        spec = specs_dir / "spec.md"
        _write_minimal_plan(str(plan))
        # ac_count=0 produces a spec with §5 section but zero AC lines.
        _write_minimal_spec(str(spec), ac_count=0)

        result = _run_bh(
            self.tmp_path,
            "render-findings-from-plan",
            str(plan),
            str(spec),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        # Sentinel for the zero-AC path.
        self.assertIn("no ACs found in spec", output)
        # Must NOT emit any [ADDRESSED BY: ?] markers.
        self.assertNotIn("[ADDRESSED BY: ?]", output)


# ---------------------------------------------------------------------------
# Tests: render-task-file (Phase 2, Verb 2)
# ---------------------------------------------------------------------------


class RenderTaskFileTests(_CwdIsolationBH):

    def test_exit_0_no_args(self):
        """No arguments → exit 0 (pure emitter)."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_all_section_headers_present(self):
        """All required section headers appear in the output."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        for header in (
            "## Files",
            "## Description",
            "## Change Details",
            "## Contracts",
            "### Expects (checked before execution)",
            "### Produces (checked after execution)",
            "## Done When",
            "## Completion Notes",
        ):
            self.assertIn(header, output, "missing header: " + header)

    def test_four_fixed_done_when_lines_verbatim(self):
        """The four helper-owned Done-When lines appear verbatim."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        for line in (
            "No debug artifacts left in changed files",
            "Type checker passes on changed files (see Development Commands section)",
            "Linter passes on changed files (see Development Commands section)",
            "No new secrets or credentials in code",
        ):
            self.assertIn(line, output, "missing Done-When line: " + line)

    def test_task_specific_placeholder_lines_present(self):
        """Both distinct task-specific Done-When placeholders appear verbatim
        (matches storage-rules.md §Task File Format lines 126-127)."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("- [ ] [Testable condition specific to this task]", output)
        self.assertIn("- [ ] [Another task-specific condition]", output)
        # The two lines must be distinct — the old double-identical bug is gone.
        self.assertNotEqual(
            output.count("[Testable condition specific to this task]"),
            0,
        )
        self.assertNotEqual(
            output.count("[Another task-specific condition]"),
            0,
        )

    def test_completion_notes_skeleton_present(self):
        """Completion Notes skeleton includes the four placeholder lines."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("[Filled in by /implement after completion]", output)
        self.assertIn("**Completed**:", output)
        self.assertIn("**Files changed**:", output)
        self.assertIn("**Contract**: Expects", output)
        self.assertIn("**Notes**:", output)

    def test_status_is_pending(self):
        """**Status**: line is 'Pending' (the only valid initial status)."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Status**: Pending", result.stdout)

    def test_number_arg_stamped_in_heading(self):
        """--number NNN appears in '# Task NNN:' heading."""
        result = _run_bh(self.tmp_path, "render-task-file", "--number", "042")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# Task 042:", result.stdout)

    def test_title_arg_stamped_in_heading(self):
        """--title TITLE appears in the heading."""
        result = _run_bh(self.tmp_path, "render-task-file", "--title", "Build the thing")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Build the thing", result.stdout)

    def test_feature_arg_stamped_in_feature_field(self):
        """--feature FEAT appears in **Feature**: line."""
        result = _run_bh(self.tmp_path, "render-task-file", "--feature", "001-widget-catalog")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Feature**: 001-widget-catalog", result.stdout)

    def test_number_placeholder_when_omitted(self):
        """Without --number, '[NNN]' placeholder appears in heading."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[NNN]", result.stdout)

    def test_title_placeholder_when_omitted(self):
        """Without --title, '[Title]' placeholder appears in heading."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[Title]", result.stdout)

    def test_feature_placeholder_when_omitted(self):
        """Without --feature, '[feature directory name]' placeholder appears."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[feature directory name]", result.stdout)

    def test_all_three_args_together(self):
        """--number + --title + --feature all stamped together."""
        result = _run_bh(
            self.tmp_path,
            "render-task-file",
            "--number", "007",
            "--title", "Add search",
            "--feature", "001-catalog",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("# Task 007: Add search", output)
        self.assertIn("**Feature**: 001-catalog", output)

    def test_files_table_present(self):
        """## Files section contains a markdown table header."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("| File | Action | Description |", output)
        self.assertIn("|------|--------|-------------|", output)


# ---------------------------------------------------------------------------
# Tests: render-tasks-index (Phase 2, Verb 3)
# ---------------------------------------------------------------------------


class RenderTasksIndexTests(_CwdIsolationBH):

    def test_exit_0_no_args(self):
        """No arguments → exit 0 (pure emitter)."""
        result = _run_bh(self.tmp_path, "render-tasks-index")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_all_sections_present(self):
        """All required sections appear in the output."""
        result = _run_bh(self.tmp_path, "render-tasks-index")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        for section in (
            "## Dependency Graph",
            "## Task Index",
            "## Additions to Spec",
            "## Risk Assessment",
            "## Review Checkpoints",
        ):
            self.assertIn(section, output, "missing section: " + section)

    def test_heading_with_feature_placeholder(self):
        """Without --feature, heading contains '[Feature Name]' placeholder."""
        result = _run_bh(self.tmp_path, "render-tasks-index")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# Tasks: [Feature Name]", result.stdout)

    def test_feature_arg_stamped_in_heading(self):
        """--feature FEAT appears in '# Tasks: FEAT' heading."""
        result = _run_bh(self.tmp_path, "render-tasks-index", "--feature", "Widget Catalog")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# Tasks: Widget Catalog", result.stdout)

    def test_spec_arg_stamped(self):
        """--spec PATH appears in **Spec**: field."""
        result = _run_bh(
            self.tmp_path, "render-tasks-index", "--spec", "specs/001-test/spec.md"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Spec**: specs/001-test/spec.md", result.stdout)

    def test_plan_arg_stamped(self):
        """--plan PATH appears in **Plan**: field."""
        result = _run_bh(
            self.tmp_path, "render-tasks-index", "--plan", "specs/001-test/plan.md"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Plan**: specs/001-test/plan.md", result.stdout)

    def test_all_three_args_together(self):
        """--feature + --spec + --plan all stamped in their fields."""
        result = _run_bh(
            self.tmp_path,
            "render-tasks-index",
            "--feature", "Catalog",
            "--spec", "specs/001-catalog/spec.md",
            "--plan", "specs/001-catalog/plan.md",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("# Tasks: Catalog", output)
        self.assertIn("**Spec**: specs/001-catalog/spec.md", output)
        self.assertIn("**Plan**: specs/001-catalog/plan.md", output)

    def test_task_index_table_headers(self):
        """Task Index table has all 5 required columns."""
        result = _run_bh(self.tmp_path, "render-tasks-index")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("| # | Title | Agent | Depends on | Status |", output)

    def test_risk_assessment_table_headers(self):
        """Risk Assessment table has Task | Risk | Reason columns."""
        result = _run_bh(self.tmp_path, "render-tasks-index")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("| Task | Risk | Reason |", output)

    def test_review_checkpoints_table_headers(self):
        """Review Checkpoints table has correct columns."""
        result = _run_bh(self.tmp_path, "render-tasks-index")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("| Before Task | Reason | What to Review |", output)

    def test_dependency_graph_fenced_block(self):
        """Dependency Graph section contains a fenced code block."""
        result = _run_bh(self.tmp_path, "render-tasks-index")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        # Fenced block
        self.assertIn("```", output)

    def test_spec_placeholder_when_omitted(self):
        """Without --spec, the spec field contains a placeholder."""
        result = _run_bh(self.tmp_path, "render-tasks-index")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Spec**:", result.stdout)
        # Must contain some placeholder text
        self.assertIn("[path to spec.md]", result.stdout)

    def test_plan_placeholder_when_omitted(self):
        """Without --plan, the plan field contains a placeholder."""
        result = _run_bh(self.tmp_path, "render-tasks-index")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Plan**:", result.stdout)
        self.assertIn("[path to plan.md]", result.stdout)

    def test_generated_date_present(self):
        """**Generated**: field is present with a date-like value."""
        result = _run_bh(self.tmp_path, "render-tasks-index")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Generated**:", result.stdout)

    def test_total_tasks_placeholder_present(self):
        """**Total tasks**: field is present."""
        result = _run_bh(self.tmp_path, "render-tasks-index")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Total tasks**:", result.stdout)


# ---------------------------------------------------------------------------
# Tests: render-consultation-block (Phase 2, Verb 4)
# ---------------------------------------------------------------------------


class RenderConsultationBlockTests(_CwdIsolationBH):

    def test_exit_0_no_args(self):
        """No arguments → exit 0 (pure emitter)."""
        result = _run_bh(self.tmp_path, "render-consultation-block")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_column_headers_present(self):
        """Table header row contains all five column names."""
        result = _run_bh(self.tmp_path, "render-consultation-block")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        for col in ("Specialist", "Sub-question", "Input summary", "Verdict", "Cites"):
            self.assertIn(col, output, "missing column: " + col)

    def test_all_four_verdict_enum_strings_present(self):
        """All four verdict-enum strings appear in the output."""
        result = _run_bh(self.tmp_path, "render-consultation-block")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        for verdict in ("accepted", "modified", "rejected", "no-response"):
            self.assertIn(verdict, output, "missing verdict: " + verdict)

    def test_none_row_present(self):
        """The (none) sentinel row appears in the table."""
        result = _run_bh(self.tmp_path, "render-consultation-block")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("| (none) |", result.stdout)

    def test_byte_stable_across_two_calls(self):
        """Two calls produce identical output (deterministic)."""
        r1 = _run_bh(self.tmp_path, "render-consultation-block")
        r2 = _run_bh(self.tmp_path, "render-consultation-block")
        self.assertEqual(r1.returncode, 0)
        self.assertEqual(r2.returncode, 0)
        self.assertEqual(r1.stdout, r2.stdout)

    def test_cites_requirement_mentioned(self):
        """The output mentions the Cites requirement."""
        result = _run_bh(self.tmp_path, "render-consultation-block")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Cites", result.stdout)

    def test_verdict_rule_line_present(self):
        """The **Verdict** must be one of ... rule line is present."""
        result = _run_bh(self.tmp_path, "render-consultation-block")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Verdict** must be one of:", result.stdout)


# ---------------------------------------------------------------------------
# Task-file fixture helpers for Phase 3 tests.
# ---------------------------------------------------------------------------


def _render_task_file_raw(number, title, feature):
    """Invoke render-task-file and return stdout string (for round-trip seeding)."""
    import subprocess as _sp
    result = _sp.run(
        [
            sys.executable,
            str(BREAKDOWN_HELPER_PY),
            "render-task-file",
            "--number", number,
            "--title", title,
            "--feature", feature,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "render-task-file failed: " + result.stderr
    return result.stdout


def _fill_task_contracts(skeleton: str, expects: "List[str]", produces: "List[str]",
                         ac_ids: str = "AC-1") -> str:
    """Replace placeholder bullets in Expects/Produces sections with real content.

    Also fills in the **Spec criteria**: placeholder with ac_ids.
    expects / produces are lists of raw bullet strings (without '- ' prefix).
    """
    # Replace **Spec criteria**: placeholder.
    skeleton = re.sub(
        r"(\*\*Spec criteria\*\*:)\s*AC-\[numbers\]",
        r"\g<1> " + ac_ids,
        skeleton,
    )

    # Replace the single placeholder Expects bullet.
    expects_bullet = "\n".join("- " + e for e in expects) if expects else ""
    skeleton = re.sub(
        r"(### Expects[^\n]*\n)- \[precondition:[^\n]*\]",
        r"\g<1>" + expects_bullet,
        skeleton,
    )

    # Replace the single placeholder Produces bullet.
    produces_bullet = "\n".join("- " + p for p in produces) if produces else ""
    skeleton = re.sub(
        r"(### Produces[^\n]*\n)- \[postcondition:[^\n]*\]",
        r"\g<1>" + produces_bullet,
        skeleton,
    )

    return skeleton


def _write_task_file(tasks_dir: "Path", number: str, title: str,
                     feature: str, expects: "List[str]", produces: "List[str]",
                     ac_ids: str = "AC-1") -> "Path":
    """Write a task file seeded from render-task-file with real contract bullets.

    Uses round-trip via the real render-task-file emitter so the INPUT
    shape matches what breakdown_helper.py produces.  Then fills in
    Expects/Produces/Spec-criteria with the given values.
    """
    skeleton = _render_task_file_raw(number, title, feature)
    filled = _fill_task_contracts(skeleton, expects, produces, ac_ids)
    path = tasks_dir / "{0}-{1}.md".format(number, title.lower().replace(" ", "-"))
    path.write_text(filled, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tests: verify-contract-chain (Phase 3, Verb 1)
# ---------------------------------------------------------------------------


class VerifyContractChainTests(_CwdIsolationBH):

    def _tasks_dir(self) -> "Path":
        d = self.tmp_path / "tasks"
        d.mkdir(exist_ok=True)
        return d

    def test_clean_chain_exits_0(self):
        """Fully internal chain: task A produces X, task B expects X and produces
        nothing else → all produces are consumed → exit 0 + 'contract-chain: ok'.

        This tests the case where a chain has no 'orphan' terminal produces
        and no unsatisfied expects.  Chain-terminal produces (items produced
        but not expected by any task) are advisory findings per the spec; to
        get exit 0 the final task must produce nothing (or all its produces
        must be consumed internally).
        """
        td = self._tasks_dir()
        _write_task_file(td, "001", "Define types", "feat",
                         expects=[], produces=["TypeDefinitions exported"])
        _write_task_file(td, "002", "Build repo", "feat",
                         expects=["TypeDefinitions exported"], produces=[])

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("contract-chain: ok", result.stdout)
        self.assertIn("2 tasks", result.stdout)

    def test_ok_output_counts_correct(self):
        """ok output includes correct produce and expect counts.

        A→B→C chain where A produces X consumed by B, B produces Y consumed
        by C, C produces nothing.  All produces consumed internally → exit 0.
        """
        td = self._tasks_dir()
        _write_task_file(td, "001", "Task one", "feat",
                         expects=[], produces=["OutputA", "OutputB"])
        _write_task_file(td, "002", "Task two", "feat",
                         expects=["OutputA", "OutputB"], produces=["OutputC"])
        _write_task_file(td, "003", "Task three", "feat",
                         expects=["OutputC"], produces=[])

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        # 3 produces total (OutputA, OutputB, OutputC), 3 expects total
        self.assertIn("3 produces", result.stdout)
        self.assertIn("3 expects", result.stdout)

    def test_orphan_produces_exits_2(self):
        """Task produces X but no other task expects X → exit 2, finding names it."""
        td = self._tasks_dir()
        _write_task_file(td, "001", "Only task", "feat",
                         expects=[], produces=["OrphanOutput"])

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 2)
        self.assertIn("ORPHAN PRODUCES", result.stdout)
        self.assertIn("orphanoutput", result.stdout.lower())  # casefold in finding

    def test_orphan_produces_mentions_advisory(self):
        """Orphan finding text mentions advisory note about spec ACs."""
        td = self._tasks_dir()
        _write_task_file(td, "001", "Solo", "feat",
                         expects=[], produces=["SomeOutput"])

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 2)
        self.assertIn("advisory", result.stdout)

    def test_unsatisfied_expects_exits_2(self):
        """Task expects X but no task produces X → exit 2, finding names it."""
        td = self._tasks_dir()
        _write_task_file(td, "001", "Needs something", "feat",
                         expects=["SomeMissingState"], produces=[])

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 2)
        self.assertIn("UNSATISFIED EXPECTS", result.stdout)
        self.assertIn("somemissingstate", result.stdout.lower())

    def test_unsatisfied_expects_mentions_advisory(self):
        """Unsatisfied finding mentions existing-codebase advisory."""
        td = self._tasks_dir()
        _write_task_file(td, "001", "Expects pre", "feat",
                         expects=["PreconditionX"], produces=[])

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 2)
        self.assertIn("advisory", result.stdout)

    def test_placeholder_bullets_ignored(self):
        """A task with only placeholder bullets produces no findings.

        The skeleton from render-task-file has bracketed placeholders in both
        Expects and Produces; these must not be treated as real contracts.
        """
        td = self._tasks_dir()
        # Write a task file with only the raw skeleton (placeholder bullets intact).
        skeleton = _render_task_file_raw("001", "Skeleton task", "feat")
        # Stamp a real AC so it doesn't interfere with other tests.
        skeleton = re.sub(
            r"(\*\*Spec criteria\*\*:)\s*AC-\[numbers\]",
            r"\g<1> AC-1",
            skeleton,
        )
        path = td / "001-skeleton-task.md"
        path.write_text(skeleton, encoding="utf-8")

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("contract-chain: ok", result.stdout)
        # Counts should be 0 produces and 0 expects (placeholders not counted).
        self.assertIn("0 produces", result.stdout)
        self.assertIn("0 expects", result.stdout)

    def test_normalization_matches_across_bullet_styles(self):
        """'- Foo Bar ' (dash) matches '* foo  bar' (asterisk, extra space, casefold)."""
        td = self._tasks_dir()
        # Task A produces with extra spacing and dash marker.
        content_a = _render_task_file_raw("001", "Task A", "feat")
        content_a = _fill_task_contracts(content_a, expects=[], produces=["Foo  Bar "])
        (td / "001-task-a.md").write_text(content_a, encoding="utf-8")

        # Task B expects with asterisk marker and different case — write manually
        # because _fill_task_contracts uses '- ' marker.
        skeleton_b = _render_task_file_raw("002", "Task B", "feat")
        # Replace placeholder expects bullet with an asterisk-marker version.
        skeleton_b = re.sub(
            r"(### Expects[^\n]*\n)- \[precondition:[^\n]*\]",
            r"\g<1>* foo  bar",
            skeleton_b,
        )
        skeleton_b = re.sub(
            r"(### Produces[^\n]*\n)- \[postcondition:[^\n]*\]",
            r"\g<1>",
            skeleton_b,
        )
        skeleton_b = re.sub(
            r"(\*\*Spec criteria\*\*:)\s*AC-\[numbers\]",
            r"\g<1> AC-1",
            skeleton_b,
        )
        (td / "002-task-b.md").write_text(skeleton_b, encoding="utf-8")

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("contract-chain: ok", result.stdout)

    def test_case_insensitive_match_satisfied(self):
        """verify-contract-chain still matches case-insensitively after the
        extraction-vs-normalization split.

        Task A produces 'Module X Ready' (mixed-case).
        Task B expects 'module x ready' (all-lowercase).
        These should match → exit 0 (chain clean), because normalization is
        applied at COMPARISON TIME in verify-contract-chain.
        """
        td = self._tasks_dir()
        _write_task_file(td, "001", "Task A", "feat",
                         expects=[], produces=["Module X Ready"])
        _write_task_file(td, "002", "Task B", "feat",
                         expects=["module x ready"], produces=[])

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("contract-chain: ok", result.stdout)

    def test_finding_message_shows_original_case(self):
        """Finding messages in verify-contract-chain show the ORIGINAL-CASE
        bullet text, not the casefolded form.

        A task that produces 'computeTotals exported' (camelCase) but has no
        consumer should emit an ORPHAN PRODUCES finding that contains the
        original-case text 'computeTotals exported', not 'computetotals exported'.
        """
        td = self._tasks_dir()
        _write_task_file(td, "001", "CamelCase task", "feat",
                         expects=[], produces=["computeTotals exported"])

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 2)
        self.assertIn("ORPHAN PRODUCES", result.stdout)
        # Original-case must appear in the finding message.
        self.assertIn("computeTotals exported", result.stdout)
        # The casefolded form must NOT appear as a standalone word in the message
        # (guard against the old normalization-at-extraction bug).
        self.assertNotIn("computetotals exported", result.stdout)

    def test_missing_tasks_dir_exits_2_with_stderr(self):
        """Non-existent tasks-dir → exit 2 + stderr 'no task files found'."""
        result = _run_bh(self.tmp_path, "verify-contract-chain",
                         str(self.tmp_path / "no-such-dir"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("no task files found", result.stderr)
        # stdout should be empty (not a violations report).
        self.assertEqual(result.stdout.strip(), "")

    def test_empty_tasks_dir_exits_2_with_stderr(self):
        """Tasks-dir with no *.md files → exit 2 + stderr."""
        td = self._tasks_dir()
        # No files in the dir.
        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 2)
        self.assertIn("no task files found", result.stderr)

    def test_readme_md_ignored(self):
        """README.md in tasks-dir is excluded from parsing."""
        td = self._tasks_dir()
        # Write only a README.md.
        (td / "README.md").write_text("# Task Index\n\nSome content.\n",
                                      encoding="utf-8")
        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 2)
        self.assertIn("no task files found", result.stderr)

    def test_findings_header_present_on_violation(self):
        """Finding output starts with '## Contract chain findings'."""
        td = self._tasks_dir()
        _write_task_file(td, "001", "Has orphan", "feat",
                         expects=[], produces=["OrphanThing"])

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Contract chain findings", result.stdout)

    def test_three_task_clean_chain(self):
        """Three-task chain A→B→C with no loose ends → exit 0."""
        td = self._tasks_dir()
        _write_task_file(td, "001", "Step one", "feat",
                         expects=[], produces=["StepOneOutput"])
        _write_task_file(td, "002", "Step two", "feat",
                         expects=["StepOneOutput"], produces=["StepTwoOutput"])
        _write_task_file(td, "003", "Step three", "feat",
                         expects=["StepTwoOutput"], produces=[])

        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("3 tasks", result.stdout)

    def test_task_with_no_contracts_section_is_clean(self):
        """Task file with NO ## Contracts section → 0 contracts, exit 0.

        Confirms that _parse_expects_produces returns empty lists when the
        ## Contracts heading is entirely absent (not just empty), and that
        verify-contract-chain treats the result as a clean chain.
        """
        td = self._tasks_dir()
        (td / "001-bare.md").write_text(
            "# Task 001: Bare\n\n**Status**: Pending\n\n## Description\n\nWork.\n",
            encoding="utf-8",
        )
        result = _run_bh(self.tmp_path, "verify-contract-chain", str(td))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("0 produces", result.stdout)
        self.assertIn("0 expects", result.stdout)


# ---------------------------------------------------------------------------
# Tests: verify-ac-coverage (Phase 3, Verb 2)
# ---------------------------------------------------------------------------


class VerifyAcCoverageTests(_CwdIsolationBH):

    def _tasks_dir(self) -> "Path":
        d = self.tmp_path / "tasks"
        d.mkdir(exist_ok=True)
        return d

    def test_all_acs_covered_exits_0(self):
        """All spec ACs referenced by tasks → exit 0 + 'ac-coverage: ok'."""
        td = self._tasks_dir()
        spec = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec), ac_count=3)
        _write_task_file(td, "001", "Cover acs", "feat",
                         expects=[], produces=[], ac_ids="AC-1, AC-2")
        _write_task_file(td, "002", "Cover rest", "feat",
                         expects=[], produces=[], ac_ids="AC-3")

        result = _run_bh(self.tmp_path, "verify-ac-coverage", str(td), str(spec))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("ac-coverage: ok", result.stdout)
        self.assertIn("3 ACs all covered", result.stdout)

    def test_one_ac_uncovered_exits_2(self):
        """Spec has AC-1, AC-2, AC-3; tasks only cover AC-1 and AC-2 → exit 2."""
        td = self._tasks_dir()
        spec = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec), ac_count=3)
        _write_task_file(td, "001", "Only two", "feat",
                         expects=[], produces=[], ac_ids="AC-1, AC-2")

        result = _run_bh(self.tmp_path, "verify-ac-coverage", str(td), str(spec))
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Uncovered acceptance criteria", result.stdout)
        self.assertIn("AC-3", result.stdout)
        self.assertNotIn("AC-1", result.stdout)  # covered ACs not reported
        self.assertNotIn("AC-2", result.stdout)

    def test_uncovered_ac_snippet_included(self):
        """The snippet from the spec AC line appears alongside the AC id."""
        td = self._tasks_dir()
        spec = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec), ac_count=2)
        # Cover only AC-1; AC-2 is uncovered.
        _write_task_file(td, "001", "Cover one", "feat",
                         expects=[], produces=[], ac_ids="AC-1")

        result = _run_bh(self.tmp_path, "verify-ac-coverage", str(td), str(spec))
        self.assertEqual(result.returncode, 2)
        # The spec fixture AC-2 text: "The system does thing 2 correctly"
        self.assertIn("The system does thing 2 correctly", result.stdout)

    def test_spec_with_zero_acs_exits_0_no_acs(self):
        """Spec with no ACs in §5 → exit 0 + 'ac-coverage: no-acs' message."""
        td = self._tasks_dir()
        spec = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec), ac_count=0)
        _write_task_file(td, "001", "No acs spec", "feat",
                         expects=[], produces=[], ac_ids="AC-1")

        result = _run_bh(self.tmp_path, "verify-ac-coverage", str(td), str(spec))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("ac-coverage: no-acs", result.stdout)
        self.assertIn("no acceptance criteria", result.stdout)

    def test_missing_tasks_dir_exits_2_with_stderr(self):
        """Non-existent tasks-dir → exit 2 + stderr, stdout empty."""
        spec = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec), ac_count=2)

        result = _run_bh(self.tmp_path, "verify-ac-coverage",
                         str(self.tmp_path / "no-tasks"), str(spec))
        self.assertEqual(result.returncode, 2)
        self.assertIn("no task files found", result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_unreadable_spec_exits_2_with_stderr(self):
        """Non-existent spec path → exit 2 + stderr, stdout empty."""
        td = self._tasks_dir()
        _write_task_file(td, "001", "Task one", "feat",
                         expects=[], produces=[], ac_ids="AC-1")

        result = _run_bh(self.tmp_path, "verify-ac-coverage",
                         str(td), str(self.tmp_path / "no-spec.md"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot read spec", result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_empty_tasks_dir_exits_2_with_stderr(self):
        """Tasks-dir with no *.md files → exit 2 + stderr."""
        td = self._tasks_dir()
        spec = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec), ac_count=1)

        result = _run_bh(self.tmp_path, "verify-ac-coverage", str(td), str(spec))
        self.assertEqual(result.returncode, 2)
        self.assertIn("no task files found", result.stderr)

    def test_multiple_uncovered_acs_all_listed(self):
        """Two uncovered ACs → both appear in the finding output."""
        td = self._tasks_dir()
        spec = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec), ac_count=4)
        # Cover only AC-1 and AC-4.
        _write_task_file(td, "001", "Task a", "feat",
                         expects=[], produces=[], ac_ids="AC-1")
        _write_task_file(td, "002", "Task b", "feat",
                         expects=[], produces=[], ac_ids="AC-4")

        result = _run_bh(self.tmp_path, "verify-ac-coverage", str(td), str(spec))
        self.assertEqual(result.returncode, 2)
        self.assertIn("AC-2", result.stdout)
        self.assertIn("AC-3", result.stdout)

    def test_no_spec_criteria_line_means_no_coverage(self):
        """Task file without **Spec criteria**: → contributes no AC coverage."""
        td = self._tasks_dir()
        spec = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec), ac_count=1)
        # Write a minimal task with no Spec criteria line at all.
        (td / "001-bare.md").write_text(
            "# Task 001: Bare\n\n**Status**: Pending\n\n## Description\n\nWork.\n",
            encoding="utf-8",
        )

        result = _run_bh(self.tmp_path, "verify-ac-coverage", str(td), str(spec))
        self.assertEqual(result.returncode, 2)
        self.assertIn("AC-1", result.stdout)

    def test_ac_coverage_with_single_task_covering_all(self):
        """Single task referencing all ACs → exit 0."""
        td = self._tasks_dir()
        spec = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec), ac_count=2)
        _write_task_file(td, "001", "Full coverage", "feat",
                         expects=[], produces=[], ac_ids="AC-1, AC-2")

        result = _run_bh(self.tmp_path, "verify-ac-coverage", str(td), str(spec))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("ac-coverage: ok", result.stdout)

    def test_ac_ref_word_boundary_ac1_and_ac12_both_extracted(self):
        """'AC-1, AC-12' in Spec criteria covers AC-1 and AC-12 independently.

        Guards the word-boundary (\\b) on _AC_REF_PATTERN: with a greedy digit+
        match the regex naturally stops at the comma after AC-1 so this is
        belt-and-suspenders,
        but the test makes the intent observable and would catch a regression if
        the pattern were changed to non-greedy or the separator stripped first.

        Also confirms AC-2 is NOT spuriously covered (AC-1 prefix must not bleed
        into AC-12 and create a phantom AC-1 match that could confuse adjacent IDs).
        """
        td = self._tasks_dir()
        spec = self.tmp_path / "spec.md"
        # Write a spec with exactly AC-1 and AC-12 (skip AC-2..AC-11).
        spec.write_text(
            "# Spec: AC Boundary Test\n\n"
            "**Date**: 2026-01-01\n"
            "**Status**: Approved\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 Core Behavior\n\n"
            "- [ ] **AC-1**: First criterion\n"
            "- [ ] **AC-12**: Twelfth criterion\n",
            encoding="utf-8",
        )
        # One task covering both AC-1 and AC-12 (comma-separated, no space after dash).
        _write_task_file(td, "001", "Cover both", "feat",
                         expects=[], produces=[], ac_ids="AC-1, AC-12")
        result = _run_bh(self.tmp_path, "verify-ac-coverage", str(td), str(spec))
        # Both ACs covered → exit 0.
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("ac-coverage: ok", result.stdout)
        # Verify the coverage count is 2, not 1 (both IDs extracted).
        self.assertIn("2 ACs all covered", result.stdout)


# ---------------------------------------------------------------------------
# Tests: CLI shape (argparse, no subcommand, --help)
# ---------------------------------------------------------------------------


class CliShapeBreakdownTests(_CwdIsolationBH):

    def test_no_subcommand_exits_2(self):
        result = _run_bh(self.tmp_path)
        self.assertEqual(result.returncode, 2)

    def test_help_shows_all_thirteen_subcommands(self):
        result = _run_bh(self.tmp_path, "--help")
        self.assertEqual(result.returncode, 0)
        for sub in (
            "pick-plan",
            "render-pick-summary",
            "list-plans",
            "check-status-and-flip",
            "read-plan-handoff",
            "render-findings-from-plan",
            "render-task-file",
            "render-tasks-index",
            "render-consultation-block",
            "verify-contract-chain",
            "verify-ac-coverage",
            "finalize-handoff",
            "render-implement-handoff",
        ):
            self.assertIn(sub, result.stdout)


# ---------------------------------------------------------------------------
# Tests: POSIX launcher shim
# ---------------------------------------------------------------------------


class LauncherShimBreakdownTests(_CwdIsolationBH):

    def _run_shim(self, cwd, *args):
        return subprocess.run(
            [str(BREAKDOWN_HELPER_SHIM)] + list(args),
            cwd=str(cwd),
            capture_output=True,
            text=True,
        )

    def test_launcher_help(self):
        result = self._run_shim(self.tmp_path, "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("pick-plan", result.stdout)
        self.assertIn("render-task-file", result.stdout)
        self.assertIn("render-consultation-block", result.stdout)

    def test_launcher_pick_plan_nonexistent(self):
        """Launcher dispatches correctly — pick-plan nonexistent path → exit 2."""
        result = self._run_shim(self.tmp_path, "pick-plan", "no/plan.md")
        self.assertEqual(result.returncode, 2)


# ---------------------------------------------------------------------------
# Phase 4 — fixture helpers for finalize-handoff / render-implement-handoff
# ---------------------------------------------------------------------------


def _write_full_task_file(tasks_dir, number, title, feature, agent,
                          expects=None, produces=None, ac_ids="AC-1",
                          depends_on="None", blocks="None",
                          review_checkpoint="No", doc_refs="None"):
    """Write a fully-populated task file seeded from render-task-file with real data.

    'agent' is a non-placeholder agent name (e.g. 'backend-engineer').
    Starts from the render-task-file skeleton (real producer round-trip) then
    substitutes agent, depends_on, blocks, review_checkpoint, doc_refs.
    """
    skeleton = _render_task_file_raw(number, title, feature)
    # Fill contracts.
    filled = _fill_task_contracts(
        skeleton,
        expects=expects or [],
        produces=produces or [],
        ac_ids=ac_ids,
    )
    # Substitute agent placeholder.
    filled = re.sub(
        r"(\*\*Agent\*\*:)\s*\[assigned agent name\]",
        r"\g<1> " + agent,
        filled,
    )
    # Substitute depends_on placeholder.
    filled = re.sub(
        r"(\*\*Depends on\*\*:)\s*\[task numbers\] or None",
        r"\g<1> " + depends_on,
        filled,
    )
    # Substitute blocks placeholder.
    filled = re.sub(
        r"(\*\*Blocks\*\*:)\s*\[task numbers\] or None",
        r"\g<1> " + blocks,
        filled,
    )
    # Substitute review checkpoint placeholder.
    filled = re.sub(
        r"(\*\*Review checkpoint\*\*:)\s*Yes/No",
        r"\g<1> " + review_checkpoint,
        filled,
    )
    # Substitute context docs placeholder.
    filled = re.sub(
        r"(\*\*Context docs\*\*:)\s*\[doc file paths\] or None",
        r"\g<1> " + doc_refs,
        filled,
    )
    path = tasks_dir / "{0}-{1}.md".format(number, title.lower().replace(" ", "-"))
    path.write_text(filled, encoding="utf-8")
    return path


def _write_readme(tasks_dir, dep_graph="", additions=None):
    """Write a tasks/README.md seeded from render-tasks-index with real data.

    dep_graph: raw text to place inside the ``` fence under ## Dependency Graph.
    additions: list of lines to place under ## Additions to Spec (None → placeholder).
    """
    import subprocess as _sp
    result = _sp.run(
        [sys.executable, str(BREAKDOWN_HELPER_PY), "render-tasks-index"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, "render-tasks-index failed: " + result.stderr
    skeleton = result.stdout

    # Replace the placeholder dep-graph fence content.
    if dep_graph:
        skeleton = re.sub(
            r"(## Dependency Graph\n\n```\n).*?(```)",
            r"\g<1>" + dep_graph + "\n" + r"\g<2>",
            skeleton,
            flags=re.DOTALL,
        )

    # Replace Additions placeholder.
    additions_text = (
        "\n".join(additions)
        if additions
        else "[Files or changes discovered that weren't in the original spec]"
    )
    skeleton = re.sub(
        r"(## Additions to Spec\n\n)\[Files or changes discovered[^\n]*\]",
        r"\g<1>" + additions_text,
        skeleton,
    )

    readme = tasks_dir / "README.md"
    readme.write_text(skeleton, encoding="utf-8")
    return readme


def _run_plan_helper_finalize(plan_path, tmp_path):
    """Run real plan_helper finalize-handoff on the given plan.md path.

    Mirrors the helper in ReadPlanHandoffTests but returns the JSON path on success.
    """
    r = subprocess.run(
        [sys.executable, str(PLAN_HELPER_PY), "finalize-handoff", str(plan_path)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    return r


# ---------------------------------------------------------------------------
# Tests: finalize-handoff (Phase 4, Verb 1)
# ---------------------------------------------------------------------------


class FinalizeHandoffTests(_CwdIsolationBH):
    """Round-trip tests for finalize-handoff.

    Build a real feature dir (plan.md + tasks/ + README.md) using the real
    producer helpers, run finalize-handoff, then reconstruct the JSON through
    the Breakdown/TaskRow/Provenance dataclasses to prove schema validity.
    """

    def _setup_feature_dir(self, with_plan_handoff=False, with_spec=False):
        """Return (feature_dir, plan_path, tasks_dir) for a two-task feature.

        If with_plan_handoff=True, first run plan_helper finalize-handoff to
        create a sibling plan-handoff.json (provenance round-trip test).
        If with_spec=True, write a sibling spec.md.
        """
        feature_dir = self.tmp_path / "specs" / "001-widget-catalog"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_rich_plan(str(plan_path), status="Approved")

        if with_spec:
            spec_path = feature_dir / "spec.md"
            spec_path.write_text(
                "# Spec: Widget Catalog Search\n\n"
                "**Date**: 2026-05-24\n"
                "**Status**: Approved\n\n"
                "## 5. Acceptance Criteria\n\n"
                "### 5.1 Core\n\n"
                "- [ ] **AC-1**: Widget entity\n"
                "- [ ] **AC-2**: Search endpoint\n",
                encoding="utf-8",
            )

        if with_plan_handoff:
            r = _run_plan_helper_finalize(plan_path, self.tmp_path)
            self.assertEqual(r.returncode, 0, "plan_helper finalize-handoff failed: " + r.stderr)

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Task 001: Define types (no depends, review checkpoint = Yes)
        _write_full_task_file(
            tasks_dir, "001", "Define types", "001-widget-catalog",
            agent="backend-engineer",
            expects=[],
            produces=["WidgetType exported"],
            ac_ids="AC-1",
            review_checkpoint="Yes",
            doc_refs="docs/architecture.md",
        )
        # Task 002: Build search (depends on 001, blocks nothing)
        _write_full_task_file(
            tasks_dir, "002", "Build search", "001-widget-catalog",
            agent="backend-engineer",
            expects=["WidgetType exported"],
            produces=["SearchEndpoint live"],
            ac_ids="AC-1, AC-2",
            depends_on="001",
            blocks="None",
            review_checkpoint="No",
        )
        # Task 003: Write tests (depends on 002)
        _write_full_task_file(
            tasks_dir, "003", "Write tests", "001-widget-catalog",
            agent="qa-engineer",
            expects=["SearchEndpoint live"],
            produces=[],
            ac_ids="AC-2",
            depends_on="002",
        )

        _write_readme(
            tasks_dir,
            dep_graph="001 (Define types) ──→ 002 (Build search) ──→ 003 (Write tests)",
            additions=["utils/test_helpers.py: new test utilities"],
        )
        return feature_dir, plan_path, tasks_dir

    def test_happy_path_exit_0_writes_json(self):
        """Happy path: exit 0 and the JSON file is written alongside plan.md."""
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        written = Path(result.stdout.strip())
        self.assertEqual(written.name, "breakdown-handoff.json")
        self.assertTrue(written.is_file())

    def test_output_path_is_sibling_to_plan(self):
        """Written path is a sibling to plan.md (same directory).

        Both paths are resolved before comparison to handle OS-level symlinks
        (e.g. /var -> /private/var on macOS) that can produce different but
        equivalent paths for the same directory.
        """
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        written = Path(result.stdout.strip()).resolve()
        self.assertEqual(written.parent, plan_path.parent.resolve())

    def test_schema_round_trip_valid(self):
        """Reconstruct JSON through schema dataclasses — must not raise."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        written = Path(result.stdout.strip())
        raw = _json.loads(written.read_text(encoding="utf-8"))

        # Reconstruct through schema — will raise if invalid.
        from _breakdown.handoff_schema import (
            Breakdown, Provenance, TaskRow,
            SCHEMA_VERSION, HANDOFF_KIND,
        )

        prov = Provenance(
            upstream_handoff_path=raw["provenance"]["upstream_handoff_path"],
            upstream_handoff_kind=raw["provenance"]["upstream_handoff_kind"],
            plan_path=raw["provenance"]["plan_path"],
            spec_path=raw["provenance"]["spec_path"],
        )
        task_rows = [
            TaskRow(
                number=t["number"],
                title=t["title"],
                agent=t["agent"],
                depends_on=t["depends_on"],
                blocks=t["blocks"],
                touched_files=t["touched_files"],
                expects=t["expects"],
                produces=t["produces"],
                ac_addressed=t["ac_addressed"],
                doc_refs=t["doc_refs"],
                review_checkpoint=t["review_checkpoint"],
            )
            for t in raw["tasks"]
        ]
        bd = Breakdown(
            schema_version=raw["schema_version"],
            handoff_kind=raw["handoff_kind"],
            tasks_dir=raw["tasks_dir"],
            breakdown_completed_at=raw["breakdown_completed_at"],
            provenance=prov,
            tasks=task_rows,
            additions=raw["additions"],
            dependency_graph=raw["dependency_graph"],
        )

        self.assertEqual(bd.schema_version, SCHEMA_VERSION)
        self.assertEqual(bd.handoff_kind, HANDOFF_KIND)

    def test_three_tasks_parsed(self):
        """Three task files → three TaskRow records in JSON."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        self.assertEqual(len(raw["tasks"]), 3)

    def test_task_numbers_parsed_correctly(self):
        """Task numbers are zero-padded strings from filenames."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        numbers = [t["number"] for t in raw["tasks"]]
        self.assertIn("001", numbers)
        self.assertIn("002", numbers)
        self.assertIn("003", numbers)

    def test_task_titles_parsed(self):
        """Task titles are parsed from the # Task NNN: Title heading."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        titles = [t["title"] for t in raw["tasks"]]
        self.assertIn("Define types", titles)
        self.assertIn("Build search", titles)
        self.assertIn("Write tests", titles)

    def test_agent_parsed(self):
        """Agent field is correctly extracted from task files."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        # Task 001 and 002 → backend-engineer; task 003 → qa-engineer.
        task_001 = next(t for t in raw["tasks"] if t["number"] == "001")
        task_003 = next(t for t in raw["tasks"] if t["number"] == "003")
        self.assertEqual(task_001["agent"], "backend-engineer")
        self.assertEqual(task_003["agent"], "qa-engineer")

    def test_depends_on_parsed(self):
        """depends_on: task 002 depends on 001."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        task_002 = next(t for t in raw["tasks"] if t["number"] == "002")
        self.assertEqual(task_002["depends_on"], ["001"])
        # Task 001 depends on nothing.
        task_001 = next(t for t in raw["tasks"] if t["number"] == "001")
        self.assertEqual(task_001["depends_on"], [])

    def test_ac_addressed_parsed(self):
        """ac_addressed: AC ids extracted from **Spec criteria**: line."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        task_002 = next(t for t in raw["tasks"] if t["number"] == "002")
        self.assertIn("AC-1", task_002["ac_addressed"])
        self.assertIn("AC-2", task_002["ac_addressed"])

    def test_review_checkpoint_bool(self):
        """review_checkpoint: Yes → True (strict bool), No → False."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        task_001 = next(t for t in raw["tasks"] if t["number"] == "001")
        task_002 = next(t for t in raw["tasks"] if t["number"] == "002")
        self.assertIs(task_001["review_checkpoint"], True)
        self.assertIs(task_002["review_checkpoint"], False)

    def test_expects_produces_parsed(self):
        """expects/produces: round-tripped via _parse_expects_produces.

        Asserts ORIGINAL-CASE text is preserved in the JSON — the fix for the
        contract-fidelity bug where finalize-handoff was casefolding bullets
        (e.g. 'WidgetType exported' → 'widgettype exported').
        """
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        task_001 = next(t for t in raw["tasks"] if t["number"] == "001")
        # task 001 produces "WidgetType exported" — original case MUST be intact.
        self.assertIn("WidgetType exported", task_001["produces"])
        # task 001 expects nothing.
        self.assertEqual(task_001["expects"], [])
        # task 002 expects "WidgetType exported" — original case MUST be intact.
        task_002 = next(t for t in raw["tasks"] if t["number"] == "002")
        self.assertIn("WidgetType exported", task_002["expects"])

    def test_finalize_handoff_preserves_original_case_in_produces(self):
        """Regression for contract-fidelity bug: finalize-handoff must NOT casefold
        Produces bullets.  A task with Produces '- src/domain/cart.ts exports
        computeTotals' must appear in breakdown-handoff.json as exactly
        'src/domain/cart.ts exports computeTotals', not 'computetotals'.
        """
        import json as _json
        feature_dir = self.tmp_path / "specs" / "010-casefold-regression"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_rich_plan(str(plan_path), status="Approved")
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "CamelCase task", "010-casefold-regression",
            agent="backend-engineer",
            expects=[],
            produces=["src/domain/cart.ts exports computeTotals"],
            ac_ids="AC-1",
        )
        _write_readme(tasks_dir)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        task_001 = next(t for t in raw["tasks"] if t["number"] == "001")
        produces = task_001["produces"]

        # The exact original-case string must appear.
        self.assertIn(
            "src/domain/cart.ts exports computeTotals",
            produces,
            "Expected original-case symbol; got: {0!r}".format(produces),
        )
        # The lowercased form must NOT appear as a separate entry.
        self.assertNotIn(
            "src/domain/cart.ts exports computetotals",
            produces,
        )

    def test_doc_refs_parsed(self):
        """doc_refs: context-docs path extracted for task 001."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        task_001 = next(t for t in raw["tasks"] if t["number"] == "001")
        self.assertIn("docs/architecture.md", task_001["doc_refs"])

    def test_doc_refs_blank_value_produces_empty_list(self):
        """Regression for Fix 1: blank **Context docs**: line → doc_refs == [].

        Uses _write_full_task_file infra then manually overwrites the context-docs
        line to be completely blank (no value after the colon).  This guard
        ensures _CONTEXT_DOCS_RE does not swallow the newline and capture the
        next line (e.g. '## Files') as a spurious doc_ref.
        """
        import json as _json
        feature_dir = self.tmp_path / "specs" / "099-blank-docs"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_rich_plan(str(plan_path), status="Approved")
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Write one task with a real doc_refs value, then patch the file so
        # the **Context docs** line is blank (no trailing text at all).
        task_path = _write_full_task_file(
            tasks_dir, "001", "Blank docs task", "099-blank-docs",
            agent="backend-engineer",
            doc_refs="docs/architecture.md",
        )
        raw_text = task_path.read_text(encoding="utf-8")
        # Replace the populated context-docs line with a blank one.
        patched = re.sub(
            r"(\*\*Context docs\*\*:)[^\n]*",
            r"\g<1>",
            raw_text,
        )
        task_path.write_text(patched, encoding="utf-8")

        _write_readme(tasks_dir)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        data = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        task_001 = next(t for t in data["tasks"] if t["number"] == "001")
        self.assertEqual(task_001["doc_refs"], [])

    def test_doc_refs_placeholder_produces_empty_list(self):
        """Regression for Fix 2: unfilled placeholder → doc_refs == [].

        A task file with the literal '[doc file paths] or None' placeholder
        (as emitted by render-task-file before the LLM fills it in) must
        produce doc_refs == [] in the JSON, not include the bracket-wrapped
        placeholder text as a real doc path.
        """
        import json as _json
        feature_dir = self.tmp_path / "specs" / "098-placeholder-docs"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_rich_plan(str(plan_path), status="Approved")
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Passing the placeholder text as doc_refs leaves it verbatim in the
        # file (the substitution regex replaces the placeholder with itself).
        _write_full_task_file(
            tasks_dir, "001", "Placeholder docs task", "098-placeholder-docs",
            agent="backend-engineer",
            doc_refs="[doc file paths] or None",
        )

        _write_readme(tasks_dir)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        data = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        task_001 = next(t for t in data["tasks"] if t["number"] == "001")
        self.assertEqual(task_001["doc_refs"], [])

    def test_tasks_dir_in_json(self):
        """tasks_dir field is set to the resolved absolute tasks directory."""
        import json as _json
        _, plan_path, tasks_dir = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        self.assertEqual(raw["tasks_dir"], str(tasks_dir.resolve()))

    def test_completed_at_in_json(self):
        """breakdown_completed_at is stamped from --completed-at arg."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-01-15T08:30:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        self.assertEqual(raw["breakdown_completed_at"], "2026-01-15T08:30:00Z")

    def test_dependency_graph_from_readme(self):
        """dependency_graph is extracted from the fenced block in README.md."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        self.assertIn("001", raw["dependency_graph"])
        self.assertIn("002", raw["dependency_graph"])

    def test_additions_from_readme(self):
        """additions list is extracted from ## Additions to Spec in README.md."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        self.assertTrue(
            any("utils/test_helpers.py" in a for a in raw["additions"]),
            "Expected additions to contain test_helpers.py, got: {0!r}".format(
                raw["additions"]
            ),
        )

    def test_provenance_without_plan_handoff(self):
        """Without sibling plan-handoff.json: upstream fields are both None."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir(with_plan_handoff=False)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        self.assertIsNone(raw["provenance"]["upstream_handoff_path"])
        self.assertIsNone(raw["provenance"]["upstream_handoff_kind"])

    def test_provenance_with_plan_handoff_real_roundtrip(self):
        """With real plan_helper finalize-handoff output: upstream fields set to 'plan'."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir(with_plan_handoff=True)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        self.assertEqual(raw["provenance"]["upstream_handoff_kind"], "plan")
        self.assertIsNotNone(raw["provenance"]["upstream_handoff_path"])
        self.assertIn("plan-handoff.json", raw["provenance"]["upstream_handoff_path"])

    def test_provenance_with_spec_path(self):
        """With sibling spec.md: provenance.spec_path is set."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir(with_spec=True)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        self.assertIsNotNone(raw["provenance"]["spec_path"])
        self.assertIn("spec.md", raw["provenance"]["spec_path"])

    def test_provenance_without_spec_path(self):
        """Without sibling spec.md: provenance.spec_path is None."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir(with_spec=False)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        self.assertIsNone(raw["provenance"]["spec_path"])

    def test_provenance_plan_path_set(self):
        """provenance.plan_path is set to the absolute plan.md path."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        raw = _json.loads(Path(result.stdout.strip()).read_text(encoding="utf-8"))
        self.assertIsNotNone(raw["provenance"]["plan_path"])
        self.assertIn("plan.md", raw["provenance"]["plan_path"])

    def test_idempotent_second_run_overwrites(self):
        """Re-running finalize-handoff overwrites the previous JSON (idempotent)."""
        import json as _json
        _, plan_path, _ = self._setup_feature_dir()

        r1 = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T10:00:00Z",
        )
        self.assertEqual(r1.returncode, 0, r1.stderr)

        r2 = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T11:00:00Z",
        )
        self.assertEqual(r2.returncode, 0, r2.stderr)

        written = Path(r2.stdout.strip())
        raw = _json.loads(written.read_text(encoding="utf-8"))
        # Second timestamp wins.
        self.assertEqual(raw["breakdown_completed_at"], "2026-05-24T11:00:00Z")

    def test_no_tmp_files_left_on_success(self):
        """Atomic write: no .json.tmp files survive after success."""
        _, plan_path, _ = self._setup_feature_dir()

        _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        feature_dir = plan_path.parent
        survivors = [p.name for p in feature_dir.iterdir()]
        for name in survivors:
            self.assertFalse(name.endswith(".json.tmp"), "tmp file survived: " + name)

    # ----- Failure paths -----

    def test_missing_plan_exits_2(self):
        """Non-existent plan.md → exit 2."""
        result = _run_bh(self.tmp_path, "finalize-handoff", "no/plan.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("plan not found", result.stderr)

    def test_missing_tasks_dir_exits_2(self):
        """plan.md present but tasks/ directory absent → exit 2."""
        feature_dir = self.tmp_path / "specs" / "002-notasks"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))

        result = _run_bh(self.tmp_path, "finalize-handoff", str(plan_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("tasks directory not found", result.stderr)

    def test_empty_tasks_dir_exits_2(self):
        """tasks/ directory exists but has no *.md files → exit 2."""
        feature_dir = self.tmp_path / "specs" / "003-emptytasks"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        (feature_dir / "tasks").mkdir()

        result = _run_bh(self.tmp_path, "finalize-handoff", str(plan_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("no task files found", result.stderr)

    def test_placeholder_agent_exits_2_names_file(self):
        """Task file with placeholder [assigned agent name] → exit 2, names the file."""
        feature_dir = self.tmp_path / "specs" / "004-badagent"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Write a task skeleton (from render-task-file) WITHOUT filling the agent.
        skeleton = _render_task_file_raw("001", "Bad task", "004-badagent")
        # Do NOT substitute the agent placeholder — leave "[assigned agent name]".
        (tasks_dir / "001-bad-task.md").write_text(skeleton, encoding="utf-8")

        result = _run_bh(self.tmp_path, "finalize-handoff", str(plan_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("placeholder", result.stderr.lower())
        self.assertIn("001-bad-task.md", result.stderr)

    def test_empty_agent_exits_2(self):
        """Task file with empty **Agent**: value → exit 2."""
        feature_dir = self.tmp_path / "specs" / "005-emptyagent"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        skeleton = _render_task_file_raw("001", "Empty agent task", "005-emptyagent")
        # Replace agent placeholder with empty string.
        skeleton = re.sub(
            r"(\*\*Agent\*\*:)\s*\[assigned agent name\]",
            r"\g<1> ",
            skeleton,
        )
        (tasks_dir / "001-empty-agent-task.md").write_text(skeleton, encoding="utf-8")

        result = _run_bh(self.tmp_path, "finalize-handoff", str(plan_path))
        self.assertEqual(result.returncode, 2)


# ---------------------------------------------------------------------------
# Tests: render-implement-handoff (Phase 4, Verb 2)
# ---------------------------------------------------------------------------


class RenderImplementHandoffTests(_CwdIsolationBH):

    def _setup_tasks(self, count=3, with_checkpoint_on=None):
        """Return (feature_dir, plan_path) with 'count' task files in tasks/.

        with_checkpoint_on: iterable of 1-based indices (1..count) that get
        review_checkpoint=Yes.  Others get No.
        """
        feature_dir = self.tmp_path / "specs" / "001-test"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        cp_indices = set(with_checkpoint_on or [])
        for i in range(1, count + 1):
            num = str(i).zfill(3)
            rc = "Yes" if i in cp_indices else "No"
            _write_full_task_file(
                tasks_dir, num, "Task {0}".format(i), "001-test",
                agent="backend-engineer",
                review_checkpoint=rc,
            )
        return feature_dir, plan_path

    def test_exit_0_basic(self):
        """Basic invocation: exit 0."""
        _, plan_path = self._setup_tasks()
        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_block_heading_present(self):
        """Output contains the '## Manual next step — run /implement' heading."""
        _, plan_path = self._setup_tasks()
        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## Manual next step — run /implement", result.stdout)

    def test_first_task_invocation_line(self):
        """Output contains the bare '/implement' copy-paste command (no task number arg)."""
        _, plan_path = self._setup_tasks()
        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/implement", result.stdout)
        # The copy-paste line must NOT include a task-number argument.
        self.assertNotIn("/implement 001", result.stdout)

    def test_restart_reminder_present(self):
        """Output contains a restart Claude Code reminder."""
        _, plan_path = self._setup_tasks()
        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        # The restart reminder must mention restarting/relaunching.
        output_lower = result.stdout.lower()
        self.assertTrue(
            "restart" in output_lower or "relaunch" in output_lower,
            "No restart reminder found in output",
        )

    def test_total_task_count_present(self):
        """Output contains the total task count (3 tasks)."""
        _, plan_path = self._setup_tasks(count=3)
        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("3", result.stdout)

    def test_review_checkpoint_count_present(self):
        """Output contains the review checkpoint count when tasks have Yes."""
        _, plan_path = self._setup_tasks(count=3, with_checkpoint_on=[1, 3])
        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2", result.stdout)  # 2 checkpoints

    def test_zero_checkpoints_reported(self):
        """When no tasks have review checkpoint, 0 is reported."""
        _, plan_path = self._setup_tasks(count=2, with_checkpoint_on=[])
        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0", result.stdout)

    def test_first_task_is_lowest_number(self):
        """The informational line names the numerically lowest task number, not filename alpha.

        Non-zero-padded filenames expose the alpha vs numeric gap:
        '10-bar.md' sorts BEFORE '2-foo.md' alphabetically but 2 < 10 numerically.
        The emitter must select task 2 (identified as '002' after zero-padding),
        not task 10. The bare '/implement' copy-paste line carries no task number,
        but the informational 'First task' line must show the correct number.
        """
        feature_dir = self.tmp_path / "specs" / "002-ordered"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Write non-zero-padded task files: '10-task-ten.md' and '2-task-two.md'.
        # Alphabetically '10-...' < '2-...' (leading '1' < '2'), but numerically
        # 2 < 10.  The emitter must pick the numerically smallest — task 2.
        _write_full_task_file(
            tasks_dir, "10", "Task ten", "002-ordered",
            agent="architect",
        )
        _write_full_task_file(
            tasks_dir, "2", "Task two", "002-ordered",
            agent="architect",
        )
        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        # task 2 → zero-padded to '002' by _parse_task_number_from_filename.
        # The informational text (not the copy-paste line) must show '002'.
        self.assertIn("002", result.stdout)
        # The bare copy-paste command must NOT have any task-number argument.
        self.assertNotIn("/implement 002", result.stdout)
        self.assertIn("/implement", result.stdout)

    def test_missing_plan_exits_2(self):
        """Non-existent plan.md → exit 2."""
        result = _run_bh(self.tmp_path, "render-implement-handoff", "no/plan.md")
        self.assertEqual(result.returncode, 2)

    def test_missing_tasks_dir_exits_2(self):
        """plan.md present but tasks/ absent → exit 2."""
        feature_dir = self.tmp_path / "specs" / "003-notasks"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))

        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 2)

    def test_empty_tasks_dir_exits_2(self):
        """tasks/ directory exists but is empty → exit 2."""
        feature_dir = self.tmp_path / "specs" / "004-emptytasks"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        (feature_dir / "tasks").mkdir()

        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 2)

    def test_deterministic_across_two_calls(self):
        """Two calls produce identical output (deterministic emitter)."""
        _, plan_path = self._setup_tasks()
        r1 = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        r2 = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(r1.returncode, 0)
        self.assertEqual(r2.returncode, 0)
        self.assertEqual(r1.stdout, r2.stdout)


# ---------------------------------------------------------------------------
# Regression: _STATUS_PATTERN must NOT bleed across blank lines
# ---------------------------------------------------------------------------


class TestBreakdownStatusPatternNoBleed(unittest.TestCase):
    """breakdown_helper._STATUS_PATTERN uses [ \\t]* (not \\s*) so a malformed
    plan file where **Status**: appears on a line by itself does NOT capture a
    value from a subsequent non-empty line.

    Tests use both direct-module access (for pattern-level assertions) and the
    check-status-and-flip subprocess verb (for public-path round-trip coverage).
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        # Import breakdown_helper directly for pattern-level assertions.
        import importlib
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "breakdown_helper", str(BREAKDOWN_HELPER_PY)
        )
        self._bh = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(self._bh)  # type: ignore[union-attr]

    def tearDown(self):
        self._tmp.cleanup()

    # ------------------------------------------------------------------
    # Direct pattern-level tests
    # ------------------------------------------------------------------

    def test_malformed_blank_line_before_value_no_match(self):
        """**Status**: on its own line, blank line, 'Draft' on next → no match.

        Regression: \\s* matched across newlines; [ \\t]* does not.
        """
        malformed = "# Plan\n\n**Date**: 2026-01-01\n**Status**:\n\nDraft\n"
        result = self._bh._parse_frontmatter_field(
            malformed, self._bh._STATUS_PATTERN
        )
        self.assertIsNone(
            result,
            "Malformed plan (value on next line after blank) must return None; "
            "got {0!r}".format(result),
        )

    def test_malformed_immediate_next_line_no_match(self):
        """**Status**: on its own line, value immediately on next → no match."""
        malformed = "# Plan\n\n**Date**: 2026-01-01\n**Status**:\nDraft\n"
        result = self._bh._parse_frontmatter_field(
            malformed, self._bh._STATUS_PATTERN
        )
        self.assertIsNone(
            result,
            "Malformed plan (value on immediate next line) must return None; "
            "got {0!r}".format(result),
        )

    def test_well_formed_single_line_matches(self):
        """Well-formed '**Status**: Approved' is still captured."""
        content = "# Plan\n\n**Date**: 2026-01-01\n**Status**: Approved\n"
        result = self._bh._parse_frontmatter_field(
            content, self._bh._STATUS_PATTERN
        )
        self.assertEqual(result, "Approved")

    def test_well_formed_with_tab_matches(self):
        """**Status**:<TAB>Draft is a valid horizontal-ws layout."""
        content = "**Status**:\tDraft\n"
        result = self._bh._parse_frontmatter_field(
            content, self._bh._STATUS_PATTERN
        )
        self.assertEqual(result, "Draft")

    # ------------------------------------------------------------------
    # CLI-level round-trip: check-status-and-flip with malformed plan
    # ------------------------------------------------------------------

    def test_check_status_and_flip_malformed_blank_before_value_not_flipped(self):
        """check-status-and-flip on a plan whose **Status**: has no value on the
        same line does NOT misread the next line's token as the status.

        With the \\s* bug, "**Status**:\\n\\nDraft\\n" would bleed "Draft" into
        group 1 and the verb would emit 'flipped'.  With [ \\t]* the pattern
        finds no match → falls to the 'no Date or Status found' → exit 2.
        """
        malformed = (
            "# Plan: Malformed\n\n"
            "**Status**:\n\n"
            "Draft\n\n"
            "## Summary\n\nSomething.\n"
        )
        plan_file = self.tmp_path / "plan.md"
        plan_file.write_text(malformed, encoding="utf-8")

        result = _run_bh(self.tmp_path, "check-status-and-flip", str(plan_file))
        # Must NOT emit 'flipped' or 'already-approved' — the malformed layout
        # should fall through to the error path (missing both Status and Date).
        self.assertNotEqual(
            result.stdout.strip(),
            "flipped",
            "check-status-and-flip must NOT 'flip' a plan whose **Status**: "
            "value is on the next line (bleed bug); stdout={0!r}".format(result.stdout),
        )
        self.assertNotEqual(
            result.stdout.strip(),
            "already-approved",
            "check-status-and-flip must NOT report 'already-approved' for a "
            "malformed plan; stdout={0!r}".format(result.stdout),
        )


if __name__ == "__main__":
    unittest.main()
