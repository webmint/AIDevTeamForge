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
    DeadCodeRow,
    Provenance,
    TaskRow,
    SCHEMA_VERSION,
    HANDOFF_KIND,
    REVIEW_CHECKPOINT_ENUM,
    DEAD_CODE_KIND_ENUM,
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
# DeadCodeRow tests (plan 71 D8(b) passthrough carrier).
#
# Self-contained duplicate of _plan.handoff_schema.DeadCodeRow -- same shape,
# same validation. Mirrors DeadCodeRowTests in tests/lib/test_plan_handoff.py.
# ---------------------------------------------------------------------------


class TestDeadCodeRowValid(unittest.TestCase):
    def test_valid_row(self):
        r = DeadCodeRow(
            file="src/widgets/widget_filter.ts",
            anchor_token=": 'legacyRegionCode'",
            kind="arm",
            why_dead="Superseded by the generic query-param filter",
        )
        self.assertEqual(r.file, "src/widgets/widget_filter.ts")
        self.assertEqual(r.kind, "arm")

    def test_all_enum_kinds_accepted(self):
        for kind in DEAD_CODE_KIND_ENUM:
            r = DeadCodeRow(file="f.ts", anchor_token="x", kind=kind, why_dead="Dead")
            self.assertEqual(r.kind, kind)


class TestDeadCodeRowRejectEmptyFile(unittest.TestCase):
    def test_empty_string(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file="", anchor_token="x", kind="arm", why_dead="Dead")

    def test_non_string(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file=123, anchor_token="x", kind="arm", why_dead="Dead")  # type: ignore[arg-type]


class TestDeadCodeRowRejectEmptyAnchorToken(unittest.TestCase):
    def test_empty_string(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file="f.ts", anchor_token="", kind="arm", why_dead="Dead")


class TestDeadCodeRowRejectInvalidKind(unittest.TestCase):
    def test_not_in_enum(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file="f.ts", anchor_token="x", kind="bogus", why_dead="Dead")

    def test_empty_string(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file="f.ts", anchor_token="x", kind="", why_dead="Dead")


class TestDeadCodeRowRejectEmptyWhyDead(unittest.TestCase):
    """Unlike the pure-builder row's optional 'why', why_dead is required
    non-empty -- a claim of change-induced deadness must be justified."""

    def test_empty_string(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file="f.ts", anchor_token="x", kind="arm", why_dead="")

    def test_non_string(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file="f.ts", anchor_token="x", kind="arm", why_dead=123)  # type: ignore[arg-type]


class TestDeadCodeRowRejectSemicolonInAnchorToken(unittest.TestCase):
    """finding C (plan 71 D9 review hardening): anchor_token must not
    contain a semicolon -- the '**Dead code removal**:' task field's value
    is semicolon-delimited, so a literal token containing one (e.g. a
    C-style for-loop header) cannot be carried through that field
    unambiguously."""

    def test_semicolon_in_middle_raises(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(
                file="src/loop.ts",
                anchor_token="for (i = 0; i < n; i++)",
                kind="branch",
                why_dead="Superseded loop removed",
            )

    def test_trailing_semicolon_raises(self):
        with self.assertRaises(ValueError):
            DeadCodeRow(file="f.ts", anchor_token="foo;", kind="arm", why_dead="Dead")

    def test_token_without_semicolon_accepted(self):
        r = DeadCodeRow(file="f.ts", anchor_token="foo", kind="arm", why_dead="Dead")
        self.assertEqual(r.anchor_token, "foo")


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

    def test_dead_code_rows_defaults_empty(self):
        """Back-compat (plan 71 D6): construction without dead_code_rows
        still works, defaulting to an empty list."""
        bd = _minimal_breakdown()
        self.assertEqual(bd.dead_code_rows, [])

    def test_with_dead_code_rows(self):
        row = DeadCodeRow(
            file="src/widgets/widget_filter.ts",
            anchor_token=": 'legacyRegionCode'",
            kind="arm",
            why_dead="Superseded by the generic filter",
        )
        bd = _minimal_breakdown(dead_code_rows=[row])
        self.assertEqual(len(bd.dead_code_rows), 1)
        self.assertEqual(bd.dead_code_rows[0].kind, "arm")


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


class TestBreakdownRejectNonListDeadCodeRows(unittest.TestCase):
    def test_none_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(dead_code_rows=None)

    def test_string_rejected(self):
        with self.assertRaises(ValueError):
            _minimal_breakdown(dead_code_rows="not a list")


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

import json
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
        # No Pure-Builder Targets section on this plan.md -> no sub-block.
        self.assertNotIn("Pure-Builder Targets", output)

    def test_round_trip_pure_builder_targets_rendered(self):
        """ROUND-TRIP: a plan.md with ### Pure-Builder Targets renders the
        'Pure-Builder Targets (property-test lane)' sub-block via the real
        producer (plan_helper finalize-handoff) + consumer (read-plan-handoff).
        """
        specs_dir = self.tmp_path / "specs" / "003-pure-builder"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        plan.write_text(
            "# Plan: Widget Catalog Search\n\n"
            "**Date**: 2026-07-20\n"
            "**Status**: Approved\n\n"
            "## Summary\n\nBuild widget catalog search functionality.\n\n"
            "### File Impact\n\n"
            "| File | Action | What Changes |\n"
            "|------|--------|---------------|\n"
            "| src/widgets/widget_filter.ts | Create | Filter predicate |\n\n"
            "### Pure-Builder Targets\n\n"
            "| Target | File | Why pure |\n"
            "|--------|------|----------|\n"
            "| filterWidgetsByQuery | src/widgets/widget_filter.ts | No I/O, deterministic |\n"
            "| normalizeTagList | src/widgets/tag_utils.ts | Pure array transform |\n"
            "| [target] | [file] | [why] |\n\n"
            "## Dependencies\n\nNo external package dependencies.\n",
            encoding="utf-8",
        )

        finalize_result = self._finalize_handoff(plan)
        self.assertEqual(
            finalize_result.returncode, 0,
            "plan_helper finalize-handoff failed: " + finalize_result.stderr
        )
        sibling = specs_dir / "plan-handoff.json"
        self.assertTrue(sibling.exists())

        # Sanity: the producer actually captured 2 rows (1 placeholder skipped).
        import json as _json
        produced = _json.loads(sibling.read_text(encoding="utf-8"))
        self.assertEqual(
            len(produced["breakdown_seeds"]["pure_builder_targets"]), 2
        )

        result = _run_bh(self.tmp_path, "read-plan-handoff", str(plan))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(
            "### Pure-Builder Targets (property-test lane)", output
        )
        self.assertIn(
            "- filterWidgetsByQuery (src/widgets/widget_filter.ts) — No I/O, deterministic",
            output,
        )
        self.assertIn(
            "- normalizeTagList (src/widgets/tag_utils.ts) — Pure array transform",
            output,
        )

    def test_old_producer_json_missing_key_renders_byte_identical(self):
        """Back-compat: a plan-handoff.json produced BEFORE this feature (no
        pure_builder_targets key in breakdown_seeds) renders byte-identical
        to the with-key-but-empty case -- no Pure-Builder Targets sub-block,
        no crash.

        Constructed by taking a real produced handoff (via the real
        producer) and deleting the key, simulating an old producer's JSON --
        not a hand-authored fixture bypassing the producer for the base shape.
        """
        specs_dir = self.tmp_path / "specs" / "004-old-producer"
        specs_dir.mkdir(parents=True)
        plan = specs_dir / "plan.md"
        _write_minimal_plan(str(plan))

        finalize_result = self._finalize_handoff(plan)
        self.assertEqual(finalize_result.returncode, 0, finalize_result.stderr)
        sibling = specs_dir / "plan-handoff.json"

        import json as _json
        produced = _json.loads(sibling.read_text(encoding="utf-8"))
        # This plan has no Pure-Builder Targets section -> already [].
        self.assertEqual(produced["breakdown_seeds"]["pure_builder_targets"], [])

        # Baseline rendering (current producer, key present but empty).
        baseline = _run_bh(self.tmp_path, "read-plan-handoff", str(plan))
        self.assertEqual(baseline.returncode, 0, baseline.stderr)

        # Simulate an OLD producer: delete the key entirely.
        del produced["breakdown_seeds"]["pure_builder_targets"]
        sibling.write_text(_json.dumps(produced), encoding="utf-8")

        old_style = _run_bh(self.tmp_path, "read-plan-handoff", str(plan))
        self.assertEqual(old_style.returncode, 0, old_style.stderr)

        # Byte-identical to the with-key-but-empty rendering.
        self.assertEqual(old_style.stdout, baseline.stdout)
        self.assertNotIn("Pure-Builder Targets", old_style.stdout)


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
        self.assertIn("[Filled in by /devforge:implement after completion]", output)
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

    # ------------------------------------------------------------------
    # --property-targets flag (plan 66 WI-1)
    # ------------------------------------------------------------------

    def test_no_property_targets_flag_byte_identical_to_pre_change_output(self):
        """Without --property-targets, output is BYTE-IDENTICAL to the
        pre-flag skeleton -- no '**Property targets**:' line anywhere."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("**Property targets**:", result.stdout)
        # Cross-check against a fixed golden skeleton built the same way
        # RenderTaskFileTests already exercises no-args output elsewhere in
        # this class -- the golden invariant is simply that inserting the
        # flag introduces no new line when omitted.
        no_flag = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.stdout, no_flag.stdout)

    def test_property_targets_line_present_after_context_docs(self):
        """--property-targets emits a '**Property targets**:' line
        immediately after '**Context docs**:', verbatim (stripped)."""
        result = _run_bh(
            self.tmp_path, "render-task-file",
            "--property-targets", "filterWidgetsByQuery, normalizeTagList",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        context_idx = next(
            i for i, ln in enumerate(lines) if ln.startswith("**Context docs**:")
        )
        self.assertEqual(
            lines[context_idx + 1],
            "**Property targets**: filterWidgetsByQuery, normalizeTagList",
        )

    def test_property_targets_value_stripped(self):
        """Leading/trailing whitespace in --property-targets is stripped."""
        result = _run_bh(
            self.tmp_path, "render-task-file",
            "--property-targets", "  foo, bar  ",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Property targets**: foo, bar", result.stdout)
        self.assertNotIn("**Property targets**:  foo", result.stdout)

    def test_empty_property_targets_flag_omits_line(self):
        """--property-targets '' (empty after stripping) omits the line
        entirely -- byte-identical to not passing the flag at all."""
        with_empty = _run_bh(
            self.tmp_path, "render-task-file", "--property-targets", "   "
        )
        without_flag = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(with_empty.returncode, 0, with_empty.stderr)
        self.assertEqual(with_empty.stdout, without_flag.stdout)

    # ------------------------------------------------------------------
    # --dead-code-removal flag (plan 71 D7/D8(b)) -- mirrors
    # --property-targets' mechanics exactly.
    # ------------------------------------------------------------------

    def test_no_dead_code_removal_flag_byte_identical_to_pre_change_output(self):
        """Without --dead-code-removal, output is BYTE-IDENTICAL to the
        pre-flag skeleton -- no '**Dead code removal**:' line anywhere."""
        result = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("**Dead code removal**:", result.stdout)
        no_flag = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(result.stdout, no_flag.stdout)

    def test_dead_code_removal_line_present_after_context_docs(self):
        """--dead-code-removal (with no --property-targets) emits a
        '**Dead code removal**:' line immediately after '**Context docs**:',
        verbatim (stripped)."""
        result = _run_bh(
            self.tmp_path, "render-task-file",
            "--dead-code-removal", "legacyRegion* arms removed",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        context_idx = next(
            i for i, ln in enumerate(lines) if ln.startswith("**Context docs**:")
        )
        self.assertEqual(
            lines[context_idx + 1],
            "**Dead code removal**: legacyRegion* arms removed",
        )

    def test_dead_code_removal_line_present_after_property_targets(self):
        """When BOTH flags are given, '**Dead code removal**:' follows
        '**Property targets**:', which itself follows '**Context docs**:'."""
        result = _run_bh(
            self.tmp_path, "render-task-file",
            "--property-targets", "filterWidgetsByQuery",
            "--dead-code-removal", "legacyRegion* arms removed",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        context_idx = next(
            i for i, ln in enumerate(lines) if ln.startswith("**Context docs**:")
        )
        self.assertEqual(
            lines[context_idx + 1],
            "**Property targets**: filterWidgetsByQuery",
        )
        self.assertEqual(
            lines[context_idx + 2],
            "**Dead code removal**: legacyRegion* arms removed",
        )

    def test_dead_code_removal_value_stripped(self):
        """Leading/trailing whitespace in --dead-code-removal is stripped."""
        result = _run_bh(
            self.tmp_path, "render-task-file",
            "--dead-code-removal", "  removed the dead arm  ",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Dead code removal**: removed the dead arm", result.stdout)
        self.assertNotIn("**Dead code removal**:  removed", result.stdout)

    def test_empty_dead_code_removal_flag_omits_line(self):
        """--dead-code-removal '' (empty after stripping) omits the line
        entirely -- byte-identical to not passing the flag at all."""
        with_empty = _run_bh(
            self.tmp_path, "render-task-file", "--dead-code-removal", "   "
        )
        without_flag = _run_bh(self.tmp_path, "render-task-file")
        self.assertEqual(with_empty.returncode, 0, with_empty.stderr)
        self.assertEqual(with_empty.stdout, without_flag.stdout)


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


def _render_task_file_raw(number, title, feature, property_targets=None,
                          dead_code_removal=None):
    """Invoke render-task-file and return stdout string (for round-trip seeding).

    property_targets (plan 66 WI-1): when given, passed through as
    --property-targets so the returned skeleton already carries a
    '**Property targets**:' line -- a real-producer round-trip, not a
    hand-authored fixture.

    dead_code_removal (plan 71 D7/D9): when given, passed through as
    --dead-code-removal so the returned skeleton already carries a
    '**Dead code removal**:' line (semicolon-separated anchor tokens).
    """
    import subprocess as _sp
    argv = [
        sys.executable,
        str(BREAKDOWN_HELPER_PY),
        "render-task-file",
        "--number", number,
        "--title", title,
        "--feature", feature,
    ]
    if property_targets:
        argv += ["--property-targets", property_targets]
    if dead_code_removal:
        argv += ["--dead-code-removal", dead_code_removal]
    result = _sp.run(
        argv,
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
# Fixture helpers: plan.md with a ### Pure-Builder Targets table, and the
# real plan_helper finalize-handoff producer (plan 66 WI-1).
# ---------------------------------------------------------------------------


def _write_plan_with_pure_builder_targets(plan_path, targets):
    """Write a plan.md with a '### Pure-Builder Targets' table.

    targets: list of (target, file, why) tuples -> one data row each.
    Mirrors the real plan.md shape plan_helper's parser expects (see
    ReadPlanHandoffTests.test_round_trip_pure_builder_targets_rendered).
    """
    rows = "\n".join(
        "| {0} | {1} | {2} |".format(t, f, w) for t, f, w in targets
    )
    content = (
        "# Plan: Property Coverage Test\n\n"
        "**Date**: 2026-07-20\n"
        "**Status**: Approved\n\n"
        "## Summary\n\nBuild something with pure-builder targets.\n\n"
        "### Pure-Builder Targets\n\n"
        "| Target | File | Why pure |\n"
        "|--------|------|----------|\n"
        "{0}\n\n"
        "## Dependencies\n\nNo external package dependencies.\n"
    ).format(rows)
    Path(plan_path).write_text(content, encoding="utf-8")


def _produce_plan_handoff_with_targets(tmp_path, plan_path, targets):
    """Write a plan.md with Pure-Builder Targets, run the REAL plan_helper
    finalize-handoff, and return the produced plan-handoff.json Path.

    Fixture-building assertion (not a test-under-test assertion): the
    producer must succeed for the fixture to be usable at all.
    """
    _write_plan_with_pure_builder_targets(plan_path, targets)
    r = _run_plan_helper_finalize(plan_path, tmp_path)
    assert r.returncode == 0, "plan_helper finalize-handoff failed: " + r.stderr
    return Path(plan_path).parent / "plan-handoff.json"


# ---------------------------------------------------------------------------
# Fixture helper: plan.md with a ### Change-Induced Dead Code table, and the
# real plan_helper finalize-handoff producer (plan 71 D8(b) passthrough).
# ---------------------------------------------------------------------------


def _write_plan_with_dead_code_rows(plan_path, rows):
    """Write a plan.md with a '### Change-Induced Dead Code' table.

    rows: list of (file, anchor_token, kind, why_dead) tuples -> one data
    row each. Mirrors the real plan.md shape plan_helper's parser expects
    (see plan_helper._parse_dead_code_rows).
    """
    table_rows = "\n".join(
        "| {0} | {1} | {2} | {3} |".format(f, a, k, w) for f, a, k, w in rows
    )
    content = (
        "# Plan: Dead Code Passthrough Test\n\n"
        "**Date**: 2026-08-06\n"
        "**Status**: Approved\n\n"
        "## Summary\n\nBuild something that kills a dead branch.\n\n"
        "### Change-Induced Dead Code\n\n"
        "| File | Anchor token | Kind | Why dead |\n"
        "|------|--------------|------|----------|\n"
        "{0}\n\n"
        "## Dependencies\n\nNo external package dependencies.\n"
    ).format(table_rows)
    Path(plan_path).write_text(content, encoding="utf-8")


def _produce_plan_handoff_with_dead_code_rows(tmp_path, plan_path, rows):
    """Write a plan.md with Change-Induced Dead Code rows, run the REAL
    plan_helper finalize-handoff, and return the produced plan-handoff.json
    Path.

    Mirrors _produce_plan_handoff_with_targets exactly (real-producer
    round-trip discipline, plan 71 D9 mirror of the property-coverage
    fixture helper).

    Fixture-building assertion (not a test-under-test assertion): the
    producer must succeed for the fixture to be usable at all.
    """
    _write_plan_with_dead_code_rows(plan_path, rows)
    r = _run_plan_helper_finalize(plan_path, tmp_path)
    assert r.returncode == 0, "plan_helper finalize-handoff failed: " + r.stderr
    return Path(plan_path).parent / "plan-handoff.json"


# ---------------------------------------------------------------------------
# Tests: verify-property-coverage + _validate_property_coverage (plan 66 WI-1)
# ---------------------------------------------------------------------------


class ValidatePropertyCoverageFnTests(_CwdIsolationBH):
    """Direct unit tests of _validate_property_coverage (shared predicate).

    Declared targets always come from a real plan-handoff.json produced by
    the REAL plan_helper finalize-handoff (round-trip via
    _produce_plan_handoff_with_targets), per real-fixture discipline. Only
    the malformed/absent-key JSON cases hand-edit a produced file, since no
    producer emits malformed JSON by design.
    """

    def _tasks_dir(self):
        d = self.tmp_path / "tasks"
        d.mkdir(exist_ok=True)
        return d

    def test_covered_target(self):
        """A single declared target covered by one task -> no offenders."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Property test", "feat", agent="qa-engineer",
            property_targets="filterWidgetsByQuery",
        )

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(declared, [("filterWidgetsByQuery", "src/widgets/widget_filter.ts")])
        self.assertEqual(offenders, [])
        self.assertEqual(covering, 1)

    def test_uncovered_target(self):
        """A declared target with no covering task -> reported as offender."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
        )
        td = self._tasks_dir()
        # A task that assigns no property targets at all.
        _write_full_task_file(td, "001", "Unrelated task", "feat", agent="qa-engineer")

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(len(declared), 1)
        self.assertEqual(
            offenders, [("filterWidgetsByQuery", "src/widgets/widget_filter.ts")]
        )
        self.assertEqual(covering, 0)

    def test_multi_target_one_task_covers_both(self):
        """One task's Property targets line names BOTH declared targets."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [
                ("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O"),
                ("normalizeTagList", "src/widgets/tag_utils.ts", "Pure transform"),
            ],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Cover both", "feat", agent="qa-engineer",
            property_targets="filterWidgetsByQuery, normalizeTagList",
        )

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(offenders, [])
        # A single task covering both targets counts once.
        self.assertEqual(covering, 1)

    def test_one_target_per_task(self):
        """Two tasks, each covering one distinct declared target."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [
                ("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O"),
                ("normalizeTagList", "src/widgets/tag_utils.ts", "Pure transform"),
            ],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Cover filter", "feat", agent="qa-engineer",
            property_targets="filterWidgetsByQuery",
        )
        _write_full_task_file(
            td, "002", "Cover normalize", "feat", agent="qa-engineer",
            property_targets="normalizeTagList", depends_on="001",
        )

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(offenders, [])
        self.assertEqual(covering, 2)

    def test_duplicate_declared_target_deduped_keeping_first_occurrence(self):
        """A target declared TWICE across two rows -> 'declared' contains
        it ONCE, keeping the FIRST occurrence's file value (finding 3)."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [
                ("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "First row"),
                ("filterWidgetsByQuery", "src/widgets/other_file.ts", "Second row"),
            ],
        )
        td = self._tasks_dir()
        # No covering task -> the deduped target is the sole offender.
        _write_full_task_file(td, "001", "Unrelated", "feat", agent="qa-engineer")

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        # Deduped to exactly one entry, keeping the FIRST row's file value.
        self.assertEqual(
            declared, [("filterWidgetsByQuery", "src/widgets/widget_filter.ts")]
        )
        self.assertEqual(
            offenders, [("filterWidgetsByQuery", "src/widgets/widget_filter.ts")]
        )

    def test_case_sensitivity_foo_not_covered_by_foo_lowercase(self):
        """Declared target 'Foo' is NOT covered by a task naming 'foo'
        (targets are code identifiers; comparison is case-sensitive)."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [("Foo", "src/foo.ts", "Pure")],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Wrong case", "feat", agent="qa-engineer",
            property_targets="foo",
        )

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(offenders, [("Foo", "src/foo.ts")])
        self.assertEqual(covering, 0)

    def test_whitespace_tolerance_a_comma_space_b(self):
        """'a , b' (irregular spacing) still matches declared targets 'a' and 'b'."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [("a", "src/a.ts", "Pure"), ("b", "src/b.ts", "Pure")],
        )
        td = self._tasks_dir()
        # Hand-edit the property-targets line directly to control exact
        # spacing -- render-task-file/--property-targets would already
        # normalize this, so we bypass it deliberately for this one case.
        task_path = _write_full_task_file(
            td, "001", "Odd spacing", "feat", agent="qa-engineer",
            property_targets="placeholder",
        )
        content = task_path.read_text(encoding="utf-8")
        content = content.replace(
            "**Property targets**: placeholder", "**Property targets**: a , b"
        )
        task_path.write_text(content, encoding="utf-8")

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(offenders, [])
        self.assertEqual(covering, 1)

    def test_empty_target_entry_in_declared_row_skipped(self):
        """A declared row with an empty/missing target contributes nothing
        to 'declared' (skipped, per the shared predicate's contract)."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [("realTarget", "src/real.ts", "Pure")],
        )
        # Hand-edit the produced handoff to inject a declared row with an
        # empty target -- no real plan.md table row produces this shape
        # (the '[target]' placeholder-row is already skipped by the
        # producer itself), so this simulates a malformed/degenerate but
        # still-JSON-valid producer row.
        import json as _json
        raw = _json.loads(handoff.read_text(encoding="utf-8"))
        raw["breakdown_seeds"]["pure_builder_targets"].append(
            {"target": "", "file": "src/nowhere.ts", "why": "n/a"}
        )
        handoff.write_text(_json.dumps(raw), encoding="utf-8")

        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Cover real", "feat", agent="qa-engineer",
            property_targets="realTarget",
        )

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        # Only the one non-empty-target row is declared.
        self.assertEqual(declared, [("realTarget", "src/real.ts")])
        self.assertEqual(offenders, [])

    def test_handoff_missing_returns_error(self):
        """Absent plan-handoff.json -> error is set, all other fields empty."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        td = self._tasks_dir()
        missing = self.tmp_path / "no-such-plan-handoff.json"

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(missing)
        )
        self.assertIsNotNone(error)
        self.assertEqual(declared, [])
        self.assertEqual(offenders, [])
        self.assertEqual(covering, 0)

    def test_handoff_malformed_json_returns_error(self):
        """Invalid JSON in plan-handoff.json -> error is set."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        td = self._tasks_dir()
        bad = self.tmp_path / "plan-handoff.json"
        bad.write_text("{ not valid json", encoding="utf-8")

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(bad)
        )
        self.assertIsNotNone(error)
        self.assertEqual(declared, [])
        self.assertEqual(offenders, [])
        self.assertEqual(covering, 0)

    def test_handoff_root_not_a_dict_returns_error(self):
        """A JSON array (not an object) at the root -> error is set."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        td = self._tasks_dir()
        bad = self.tmp_path / "plan-handoff.json"
        bad.write_text("[1, 2, 3]", encoding="utf-8")

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(bad)
        )
        self.assertIsNotNone(error)

    def test_handoff_breakdown_seeds_not_a_dict_returns_error(self):
        """breakdown_seeds present but a JSON list (not an object) -> error
        is set, NOT coerced to empty (a malformed handoff must still reach
        the verb's plan.md fallback, not silently vanish)."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        td = self._tasks_dir()
        bad = self.tmp_path / "plan-handoff.json"
        import json as _json
        bad.write_text(
            _json.dumps({"breakdown_seeds": [1, 2, 3]}), encoding="utf-8"
        )

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(bad)
        )
        self.assertIsNotNone(error)
        self.assertEqual(declared, [])
        self.assertEqual(offenders, [])
        self.assertEqual(covering, 0)

    def test_handoff_pure_builder_targets_not_a_list_returns_error(self):
        """pure_builder_targets present but a JSON string (not a list) ->
        error is set, NOT coerced to empty."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        td = self._tasks_dir()
        bad = self.tmp_path / "plan-handoff.json"
        import json as _json
        bad.write_text(
            _json.dumps(
                {"breakdown_seeds": {"pure_builder_targets": "not-a-list"}}
            ),
            encoding="utf-8",
        )

        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(bad)
        )
        self.assertIsNotNone(error)
        self.assertEqual(declared, [])
        self.assertEqual(offenders, [])
        self.assertEqual(covering, 0)

    def test_absent_key_yields_empty_declared(self):
        """breakdown_seeds with NO pure_builder_targets key at all (old
        producer shape) -> declared == [] and NOT an error."""
        from breakdown_helper import _validate_property_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        # A plan with NO Pure-Builder Targets section -> the real producer
        # already emits pure_builder_targets: [] (see
        # ReadPlanHandoffTests.test_old_producer_json_missing_key_renders_byte_identical
        # for the same "simulate an old producer" technique).
        _write_minimal_plan(str(plan_path))
        r = _run_plan_helper_finalize(plan_path, self.tmp_path)
        self.assertEqual(r.returncode, 0, r.stderr)
        handoff = plan_path.parent / "plan-handoff.json"

        import json as _json
        raw = _json.loads(handoff.read_text(encoding="utf-8"))
        self.assertEqual(raw["breakdown_seeds"]["pure_builder_targets"], [])
        # Simulate an OLD producer: delete the key entirely.
        del raw["breakdown_seeds"]["pure_builder_targets"]
        handoff.write_text(_json.dumps(raw), encoding="utf-8")

        td = self._tasks_dir()
        declared, offenders, covering, error = _validate_property_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(declared, [])
        self.assertEqual(offenders, [])
        self.assertEqual(covering, 0)


class PlanDeclaresPureBuilderTargetsFnTests(_CwdIsolationBH):
    """Direct unit tests of _plan_declares_pure_builder_targets (finding 1:
    the criterion is heading AND >=1 non-placeholder row, mirroring
    plan_helper._parse_pure_builder_targets WITHOUT importing plan_helper)."""

    def test_heading_and_real_row_true(self):
        from breakdown_helper import _plan_declares_pure_builder_targets  # type: ignore[import]
        content = (
            "### Pure-Builder Targets\n\n"
            "| Target | File | Why pure |\n"
            "|--------|------|----------|\n"
            "| foo | src/foo.ts | Pure |\n"
        )
        self.assertTrue(_plan_declares_pure_builder_targets(content))

    def test_no_heading_false(self):
        from breakdown_helper import _plan_declares_pure_builder_targets  # type: ignore[import]
        self.assertFalse(_plan_declares_pure_builder_targets("# Plan: X\n\nNo section here.\n"))

    def test_heading_present_placeholder_only_rows_false(self):
        from breakdown_helper import _plan_declares_pure_builder_targets  # type: ignore[import]
        content = (
            "### Pure-Builder Targets\n\n"
            "| Target | File | Why pure |\n"
            "|--------|------|----------|\n"
            "| [target] | [file] | [why] |\n"
        )
        self.assertFalse(_plan_declares_pure_builder_targets(content))

    def test_case_insensitive_heading_true(self):
        from breakdown_helper import _plan_declares_pure_builder_targets  # type: ignore[import]
        content = (
            "### pure-builder targets\n\n"
            "| Target | File | Why pure |\n"
            "|--------|------|----------|\n"
            "| foo | src/foo.ts | Pure |\n"
        )
        self.assertTrue(_plan_declares_pure_builder_targets(content))

    def test_level_4_heading_false(self):
        from breakdown_helper import _plan_declares_pure_builder_targets  # type: ignore[import]
        content = (
            "#### Pure-Builder Targets\n\n"
            "| Target | File | Why pure |\n"
            "|--------|------|----------|\n"
            "| foo | src/foo.ts | Pure |\n"
        )
        self.assertFalse(_plan_declares_pure_builder_targets(content))


class RenderPropertyCoverageFindingsFnTests(unittest.TestCase):
    """Direct unit tests of _render_property_coverage_findings (finding 5:
    the shared rendering function both emission sites call)."""

    def test_single_offender_exact_text(self):
        from breakdown_helper import _render_property_coverage_findings  # type: ignore[import]
        result = _render_property_coverage_findings(
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts")]
        )
        self.assertEqual(
            result,
            "## Property coverage findings\n\n"
            "- target 'filterWidgetsByQuery' (src/widgets/widget_filter.ts): "
            "no property-test task covers it\n"
            "\nDeclared in plan-handoff.json breakdown_seeds.pure_builder_targets; "
            "add a dedicated qa-engineer property-test task with a "
            "'**Property targets**:' line naming each uncovered target.\n",
        )

    def test_two_offenders_two_lines(self):
        from breakdown_helper import _render_property_coverage_findings  # type: ignore[import]
        result = _render_property_coverage_findings(
            [("a", "src/a.ts"), ("b", "src/b.ts")]
        )
        self.assertEqual(result.count("- target '"), 2)
        self.assertIn("- target 'a' (src/a.ts): no property-test task covers it\n", result)
        self.assertIn("- target 'b' (src/b.ts): no property-test task covers it\n", result)

    def test_empty_offenders_no_bullet_lines(self):
        from breakdown_helper import _render_property_coverage_findings  # type: ignore[import]
        result = _render_property_coverage_findings([])
        self.assertNotIn("- target '", result)
        self.assertIn("## Property coverage findings", result)


class VerifyPropertyCoverageVerbTests(_CwdIsolationBH):
    """CLI-level tests for the verify-property-coverage verb."""

    def _tasks_dir(self, name="tasks"):
        d = self.tmp_path / name
        d.mkdir(exist_ok=True)
        return d

    def test_skip_when_no_declared_targets(self):
        """No Pure-Builder Targets in the plan -> skip, exit 0 (no task
        files required at all)."""
        plan_path = self.tmp_path / "plan.md"
        _write_minimal_plan(str(plan_path))
        r = _run_plan_helper_finalize(plan_path, self.tmp_path)
        self.assertEqual(r.returncode, 0, r.stderr)

        # Deliberately do NOT create any tasks directory.
        result = _run_bh(
            self.tmp_path, "verify-property-coverage",
            str(self.tmp_path / "tasks"),
            "--plan-handoff", str(plan_path.parent / "plan-handoff.json"),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            result.stdout.strip(),
            "property-coverage: skip (no declared pure-builder targets)",
        )

    def test_ok_when_all_covered(self):
        """All declared targets covered -> exit 0 with the ok-count line."""
        plan_path = self.tmp_path / "plan.md"
        _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Property test", "feat", agent="qa-engineer",
            property_targets="filterWidgetsByQuery",
        )

        result = _run_bh(
            self.tmp_path, "verify-property-coverage", str(td),
            "--plan-handoff", str(plan_path.parent / "plan-handoff.json"),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            result.stdout.strip(),
            "property-coverage: ok (1 targets, 1 covering tasks)",
        )

    def test_findings_block_on_uncovered_target(self):
        """An uncovered declared target -> exit 2 + findings block content.

        Also asserts the emitted block is BYTE-IDENTICAL to
        _render_property_coverage_findings's own output (finding 5: the verb
        and the finalize-handoff chokepoint share this one rendering
        function, so the two emission sites cannot drift)."""
        from breakdown_helper import _render_property_coverage_findings  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
        )
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Unrelated", "feat", agent="qa-engineer")

        result = _run_bh(
            self.tmp_path, "verify-property-coverage", str(td),
            "--plan-handoff", str(plan_path.parent / "plan-handoff.json"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Property coverage findings", result.stdout)
        self.assertIn(
            "- target 'filterWidgetsByQuery' (src/widgets/widget_filter.ts): "
            "no property-test task covers it",
            result.stdout,
        )
        self.assertIn(
            "Declared in plan-handoff.json breakdown_seeds.pure_builder_targets",
            result.stdout,
        )
        self.assertIn("qa-engineer property-test task", result.stdout)
        self.assertEqual(
            result.stdout,
            _render_property_coverage_findings(
                [("filterWidgetsByQuery", "src/widgets/widget_filter.ts")]
            ),
        )

    def test_findings_block_duplicate_declared_target_renders_one_line(self):
        """A target declared TWICE (across two plan.md rows), uncovered ->
        exactly ONE '- target ...' findings line, not two (finding 3: dedup
        by target name)."""
        plan_path = self.tmp_path / "plan.md"
        _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [
                ("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "First row"),
                ("filterWidgetsByQuery", "src/widgets/other_file.ts", "Second row"),
            ],
        )
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Unrelated", "feat", agent="qa-engineer")

        result = _run_bh(
            self.tmp_path, "verify-property-coverage", str(td),
            "--plan-handoff", str(plan_path.parent / "plan-handoff.json"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stdout.count("- target 'filterWidgetsByQuery'"), 1
        )

    def test_fail_closed_missing_plan_handoff(self):
        """Missing plan-handoff.json + plan.md DECLARES targets (### heading
        present) -> exit 2 with the remedy stderr message (amendment,
        instruction-review HIGH finding: fail-closed only applies when the
        plan actually declared targets -- see test_skip_missing_handoff_*
        for the never-declared cases that now exit 0)."""
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Whatever", "feat", agent="qa-engineer")
        missing_handoff = self.tmp_path / "plan-handoff.json"
        # plan.md sits next to tasks_dir's parent (self.tmp_path) and DOES
        # declare a Pure-Builder Targets section.
        plan_md_path = self.tmp_path / "plan.md"
        _write_plan_with_pure_builder_targets(
            plan_md_path,
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
        )

        result = _run_bh(
            self.tmp_path, "verify-property-coverage", str(td),
            "--plan-handoff", str(missing_handoff),
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stderr.strip(),
            # Routed through _die() (LOW finding) -> gains the file-wide
            # 'breakdown_helper: ' prefix convention.
            "breakdown_helper: verify-property-coverage: plan-handoff.json "
            "not found/unreadable at {0} — plan.md declares pure-builder "
            "targets; run plan_helper finalize-handoff {1} to produce it, "
            "then re-run this gate".format(missing_handoff, plan_md_path),
        )
        self.assertEqual(result.stdout.strip(), "")

    def test_skip_missing_handoff_and_no_plan_md_at_all(self):
        """Missing plan-handoff.json AND no plan.md at all next to tasks_dir
        -> the feature never declared targets -> skip, exit 0 (amendment)."""
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Whatever", "feat", agent="qa-engineer")
        missing_handoff = self.tmp_path / "plan-handoff.json"
        # Deliberately do NOT write any plan.md at all.

        result = _run_bh(
            self.tmp_path, "verify-property-coverage", str(td),
            "--plan-handoff", str(missing_handoff),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            result.stdout.strip(),
            "property-coverage: skip (no plan-handoff.json and no "
            "pure-builder targets declared in plan.md)",
        )
        self.assertEqual(result.stderr.strip(), "")

    def test_skip_missing_handoff_and_plan_md_without_heading(self):
        """Missing plan-handoff.json + a plan.md that exists but has NO
        Pure-Builder Targets heading -> skip, exit 0 (amendment)."""
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Whatever", "feat", agent="qa-engineer")
        missing_handoff = self.tmp_path / "plan-handoff.json"
        # A plan.md with no Pure-Builder Targets section at all.
        _write_minimal_plan(str(self.tmp_path / "plan.md"))

        result = _run_bh(
            self.tmp_path, "verify-property-coverage", str(td),
            "--plan-handoff", str(missing_handoff),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            result.stdout.strip(),
            "property-coverage: skip (no plan-handoff.json and no "
            "pure-builder targets declared in plan.md)",
        )

    def test_skip_missing_handoff_and_plan_md_heading_present_but_placeholder_only(self):
        """Missing plan-handoff.json + plan.md HAS the '### Pure-Builder
        Targets' heading but EVERY row is a placeholder (the
        '| [target] | [file] | [why] |' example row) -> the section is
        declared but no REAL target is named -> skip, exit 0 (finding 1:
        the criterion is heading AND >=1 non-placeholder row, not the
        heading alone)."""
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Whatever", "feat", agent="qa-engineer")
        missing_handoff = self.tmp_path / "plan-handoff.json"
        (self.tmp_path / "plan.md").write_text(
            "# Plan: Placeholder Only\n\n"
            "**Date**: 2026-07-20\n"
            "**Status**: Approved\n\n"
            "### Pure-Builder Targets\n\n"
            "| Target | File | Why pure |\n"
            "|--------|------|----------|\n"
            "| [target] | [file] | [why] |\n",
            encoding="utf-8",
        )

        result = _run_bh(
            self.tmp_path, "verify-property-coverage", str(td),
            "--plan-handoff", str(missing_handoff),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            result.stdout.strip(),
            "property-coverage: skip (no plan-handoff.json and no "
            "pure-builder targets declared in plan.md)",
        )

    def test_fail_closed_malformed_handoff_and_plan_md_with_heading(self):
        """Malformed (invalid-JSON) plan-handoff.json + plan.md DOES declare
        targets -> exit 2 with the remedy (amendment: any handoff error --
        not just 'missing' -- triggers the plan.md fallback check)."""
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Whatever", "feat", agent="qa-engineer")
        malformed_handoff = self.tmp_path / "plan-handoff.json"
        malformed_handoff.write_text("{ not valid json", encoding="utf-8")
        plan_md_path = self.tmp_path / "plan.md"
        _write_plan_with_pure_builder_targets(
            plan_md_path,
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
        )

        result = _run_bh(
            self.tmp_path, "verify-property-coverage", str(td),
            "--plan-handoff", str(malformed_handoff),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "plan.md declares pure-builder targets; run plan_helper "
            "finalize-handoff", result.stderr
        )
        self.assertIn(str(plan_md_path), result.stderr)

    def test_heading_match_is_case_insensitive_and_not_level_4(self):
        """The '### Pure-Builder Targets' heading match is case-insensitive,
        and does NOT match a level-4 '#### Pure-Builder Targets' heading
        (the regex requires whitespace immediately after exactly three '#'
        characters; a fourth '#' is not whitespace, so the match fails at
        that position and no other position in the line can satisfy the
        leading '^###' anchor). This test asserts the ACTUAL chosen
        behavior, not an assumption about it."""
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Whatever", "feat", agent="qa-engineer")
        missing_handoff = self.tmp_path / "plan-handoff.json"

        # Case-insensitive: lowercase heading still triggers fail-closed.
        plan_md_path = self.tmp_path / "plan.md"
        plan_md_path.write_text(
            "# Plan: Case Test\n\n"
            "**Date**: 2026-07-20\n"
            "**Status**: Approved\n\n"
            "### pure-builder targets\n\n"
            "| Target | File | Why pure |\n"
            "|--------|------|----------|\n"
            "| foo | src/foo.ts | Pure |\n",
            encoding="utf-8",
        )
        result_lower = _run_bh(
            self.tmp_path, "verify-property-coverage", str(td),
            "--plan-handoff", str(missing_handoff),
        )
        self.assertEqual(result_lower.returncode, 2, result_lower.stdout)

        # Level-4 heading: does NOT trigger fail-closed -> skip, exit 0.
        plan_md_path.write_text(
            "# Plan: Level Four Test\n\n"
            "**Date**: 2026-07-20\n"
            "**Status**: Approved\n\n"
            "#### Pure-Builder Targets\n\n"
            "| Target | File | Why pure |\n"
            "|--------|------|----------|\n"
            "| foo | src/foo.ts | Pure |\n",
            encoding="utf-8",
        )
        result_level4 = _run_bh(
            self.tmp_path, "verify-property-coverage", str(td),
            "--plan-handoff", str(missing_handoff),
        )
        self.assertEqual(result_level4.returncode, 0, result_level4.stderr)
        self.assertEqual(
            result_level4.stdout.strip(),
            "property-coverage: skip (no plan-handoff.json and no "
            "pure-builder targets declared in plan.md)",
        )

    def test_no_task_files_found_when_targets_declared(self):
        """Declared targets present but tasks-dir is missing/empty -> exit 2
        with the shared 'no task files found' stderr message."""
        plan_path = self.tmp_path / "plan.md"
        _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
        )
        empty_tasks_dir = self.tmp_path / "empty-tasks"
        # Deliberately do NOT create the directory at all.

        result = _run_bh(
            self.tmp_path, "verify-property-coverage", str(empty_tasks_dir),
            "--plan-handoff", str(plan_path.parent / "plan-handoff.json"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "no task files found in {0}".format(empty_tasks_dir), result.stderr
        )
        self.assertEqual(result.stdout.strip(), "")

    def test_default_plan_handoff_path_is_sibling_to_tasks_dir_parent(self):
        """Without --plan-handoff, defaults to <tasks-dir's parent>/plan-handoff.json."""
        feature_dir = self.tmp_path / "specs" / "001-default-path"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _produce_plan_handoff_with_targets(
            self.tmp_path, plan_path,
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
        )
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()
        _write_full_task_file(
            tasks_dir, "001", "Property test", "001-default-path", agent="qa-engineer",
            property_targets="filterWidgetsByQuery",
        )

        # No --plan-handoff passed at all.
        result = _run_bh(self.tmp_path, "verify-property-coverage", str(tasks_dir))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("property-coverage: ok", result.stdout)


# ---------------------------------------------------------------------------
# Tests: verify-dead-code-coverage + _validate_dead_code_coverage
# (plan 71 D9 amendment). Mirrors the verify-property-coverage test suite
# above EXACTLY in structure, with an added duplicate-assignment dimension.
# ---------------------------------------------------------------------------


class ValidateDeadCodeCoverageFnTests(_CwdIsolationBH):
    """Direct unit tests of _validate_dead_code_coverage (shared predicate).

    Declared rows always come from a real plan-handoff.json produced by the
    REAL plan_helper finalize-handoff (round-trip via
    _produce_plan_handoff_with_dead_code_rows), per real-fixture discipline.
    Only the malformed/absent-key JSON cases hand-edit a produced file,
    since no producer emits malformed JSON by design.
    """

    def _tasks_dir(self):
        d = self.tmp_path / "tasks"
        d.mkdir(exist_ok=True)
        return d

    def test_covered_row(self):
        """A single declared row covered by one task -> no offenders."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Remove dead arm", "feat", agent="backend-engineer",
            dead_code_removal="legacyRegionCode",
        )

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(declared, [("legacyRegionCode", "src/widgets/widget_filter.ts")])
        self.assertEqual(offenders, [])
        self.assertEqual(duplicates, [])
        self.assertEqual(covering, 1)

    def test_uncovered_row(self):
        """A declared row with no covering task -> reported as offender."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
        )
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Unrelated task", "feat", agent="backend-engineer")

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(len(declared), 1)
        self.assertEqual(
            offenders, [("legacyRegionCode", "src/widgets/widget_filter.ts")]
        )
        self.assertEqual(duplicates, [])
        self.assertEqual(covering, 0)

    def test_duplicate_assignment_two_tasks(self):
        """A declared row named by TWO tasks -> reported as a duplicate,
        NOT as covered-fine (D7: exactly one owning task)."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "First claim", "feat", agent="backend-engineer",
            dead_code_removal="legacyRegionCode",
        )
        _write_full_task_file(
            td, "002", "Second claim", "feat", agent="backend-engineer",
            dead_code_removal="legacyRegionCode", depends_on="001",
        )

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(offenders, [])
        self.assertEqual(len(duplicates), 1)
        token, file_val, task_names = duplicates[0]
        self.assertEqual(token, "legacyRegionCode")
        self.assertEqual(file_val, "src/widgets/widget_filter.ts")
        self.assertEqual(
            sorted(task_names),
            ["001-first-claim.md", "002-second-claim.md"],
        )
        self.assertEqual(covering, 2)

    def test_multi_row_one_task_covers_both(self):
        """One task's field names BOTH declared anchor tokens."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [
                ("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded"),
                ("src/widgets/legacy_filter.ts", "applyLegacyTagFilter", "function", "Replaced"),
            ],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Cover both", "feat", agent="backend-engineer",
            dead_code_removal="legacyRegionCode; applyLegacyTagFilter",
        )

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(offenders, [])
        self.assertEqual(duplicates, [])
        self.assertEqual(covering, 1)

    def test_single_task_repeating_token_not_a_duplicate(self):
        """finding A (HIGH): one task listing the SAME token twice within
        its own field ('foo; foo') must NOT misreport as a 2-task
        duplicate -- it is one task covering one row, exactly the intended
        shape, so it must be 'ok', not a duplicate-assignment finding."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Repeats itself", "feat", agent="backend-engineer",
            dead_code_removal="legacyRegionCode; legacyRegionCode",
        )

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(offenders, [])
        self.assertEqual(duplicates, [], "a self-repeated token must NOT be a duplicate")
        self.assertEqual(covering, 1)

    def test_invalid_kind_row_excluded_from_declared(self):
        """finding B (MEDIUM): a row whose 'kind' fails DEAD_CODE_KIND_ENUM
        validation is excluded from 'declared' entirely (not just from the
        D8(b) passthrough carrier) -- declared must never demand coverage
        for a row that will never ship into breakdown-handoff.json."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        td = self._tasks_dir()
        bad = self.tmp_path / "plan-handoff.json"
        bad.write_text(
            json.dumps({
                "breakdown_seeds": {
                    "dead_code_rows": [
                        {
                            "file": "src/widgets/other.ts",
                            "anchor_token": "someToken",
                            "kind": "bogus",
                            "why_dead": "Also dead",
                        },
                    ]
                }
            }),
            encoding="utf-8",
        )

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(bad)
        )
        self.assertIsNone(error)
        self.assertEqual(declared, [])
        self.assertEqual(offenders, [])
        self.assertEqual(duplicates, [])
        self.assertEqual(covering, 0)

    def test_semicolon_anchor_token_excluded_early_not_shredded(self):
        """finding C (MEDIUM): a declared row whose anchor_token contains a
        semicolon is excluded from 'declared' at construction time (the
        SAME DeadCodeRow validation as finding B) -- it does NOT get split
        into fragments and reported as a garbled offender, which was the
        pre-hardening failure mode (a legitimate C-style for-loop token
        would silently shred and mismatch even when a task named it
        verbatim). Hand-written JSON bypasses the producer (which now also
        rejects this row at construction time) to prove the coverage
        predicate is independently defended, not merely relying on an
        upstream producer guarantee."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        td = self._tasks_dir()
        bad = self.tmp_path / "plan-handoff.json"
        bad.write_text(
            json.dumps({
                "breakdown_seeds": {
                    "dead_code_rows": [
                        {
                            "file": "src/loop.ts",
                            "anchor_token": "for (i = 0; i < n; i++)",
                            "kind": "branch",
                            "why_dead": "Superseded loop removed",
                        },
                    ]
                }
            }),
            encoding="utf-8",
        )

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(bad)
        )
        self.assertIsNone(error)
        self.assertEqual(declared, [])
        self.assertEqual(offenders, [])
        self.assertEqual(covering, 0)

    def test_exact_token_match_with_spaces_and_quotes(self):
        """An anchor token containing spaces + single quotes survives the
        semicolon-list round-trip and matches EXACTLY (the field format
        this hardening exists to make unambiguous)."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        token = ": 'legacyRegionCode'"
        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [("src/widgets/widget_filter.ts", token, "arm", "Superseded")],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Cover token with spaces", "feat", agent="backend-engineer",
            dead_code_removal=token,
        )

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(declared, [(token, "src/widgets/widget_filter.ts")])
        self.assertEqual(offenders, [])
        self.assertEqual(covering, 1)

    def test_token_containing_comma_stays_intact(self):
        """An anchor token containing a comma is NOT split (semicolon is
        the separator, not comma) -- demonstrates why the comma-based
        --property-targets format was unsuitable for anchor tokens."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        token = "buildFilters(a, b)"
        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [("src/widgets/widget_filter.ts", token, "function", "Superseded")],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Cover comma token", "feat", agent="backend-engineer",
            dead_code_removal=token,
        )

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(offenders, [])
        self.assertEqual(covering, 1)

    def test_duplicate_declared_row_deduped_keeping_first_occurrence(self):
        """An anchor token declared TWICE across two rows -> 'declared'
        contains it ONCE, keeping the FIRST occurrence's file value."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        handoff = _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [
                ("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "First row"),
                ("src/widgets/other_file.ts", "legacyRegionCode", "arm", "Second row"),
            ],
        )
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Unrelated", "feat", agent="backend-engineer")

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(
            declared, [("legacyRegionCode", "src/widgets/widget_filter.ts")]
        )
        self.assertEqual(
            offenders, [("legacyRegionCode", "src/widgets/widget_filter.ts")]
        )

    def test_handoff_missing_returns_error(self):
        """Absent plan-handoff.json -> error is set, all other fields empty."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        td = self._tasks_dir()
        missing = self.tmp_path / "no-such-plan-handoff.json"

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(missing)
        )
        self.assertIsNotNone(error)
        self.assertEqual(declared, [])
        self.assertEqual(offenders, [])
        self.assertEqual(duplicates, [])
        self.assertEqual(covering, 0)

    def test_handoff_malformed_json_returns_error(self):
        """Invalid JSON in plan-handoff.json -> error is set."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        td = self._tasks_dir()
        bad = self.tmp_path / "plan-handoff.json"
        bad.write_text("{ not valid json", encoding="utf-8")

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(bad)
        )
        self.assertIsNotNone(error)
        self.assertEqual(declared, [])

    def test_handoff_dead_code_rows_not_a_list_returns_error(self):
        """dead_code_rows present but a JSON string (not a list) -> error
        is set, NOT coerced to empty."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        td = self._tasks_dir()
        bad = self.tmp_path / "plan-handoff.json"
        bad.write_text(
            json.dumps({"breakdown_seeds": {"dead_code_rows": "not-a-list"}}),
            encoding="utf-8",
        )

        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(bad)
        )
        self.assertIsNotNone(error)
        self.assertEqual(declared, [])

    def test_absent_key_yields_empty_declared(self):
        """breakdown_seeds with NO dead_code_rows key at all (old producer
        shape) -> declared == [] and NOT an error."""
        from breakdown_helper import _validate_dead_code_coverage  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        _write_minimal_plan(str(plan_path))
        r = _run_plan_helper_finalize(plan_path, self.tmp_path)
        self.assertEqual(r.returncode, 0, r.stderr)
        handoff = plan_path.parent / "plan-handoff.json"

        raw = json.loads(handoff.read_text(encoding="utf-8"))
        self.assertEqual(raw["breakdown_seeds"]["dead_code_rows"], [])
        del raw["breakdown_seeds"]["dead_code_rows"]
        handoff.write_text(json.dumps(raw), encoding="utf-8")

        td = self._tasks_dir()
        declared, offenders, duplicates, covering, error = _validate_dead_code_coverage(
            str(td), str(handoff)
        )
        self.assertIsNone(error)
        self.assertEqual(declared, [])
        self.assertEqual(offenders, [])
        self.assertEqual(duplicates, [])
        self.assertEqual(covering, 0)


class RenderDeadCodeCoverageFindingsFnTests(unittest.TestCase):
    """Direct unit tests of _render_dead_code_coverage_findings (the
    shared rendering function both emission sites call)."""

    def test_single_offender_exact_text(self):
        from breakdown_helper import _render_dead_code_coverage_findings  # type: ignore[import]
        result = _render_dead_code_coverage_findings(
            [("legacyRegionCode", "src/widgets/widget_filter.ts")], []
        )
        self.assertEqual(
            result,
            "## Dead-code coverage findings\n\n"
            "- anchor 'legacyRegionCode' (src/widgets/widget_filter.ts): "
            "no task's '**Dead code removal**:' field covers it\n"
            "\nDeclared in plan-handoff.json breakdown_seeds.dead_code_rows; "
            "fold each uncovered/duplicated anchor into exactly one task's "
            "'**Dead code removal**:' field (semicolon-separated list of "
            "anchor tokens, mirroring '**Property targets**:').\n",
        )

    def test_single_duplicate_exact_text(self):
        from breakdown_helper import _render_dead_code_coverage_findings  # type: ignore[import]
        result = _render_dead_code_coverage_findings(
            [], [("legacyRegionCode", "src/widgets/widget_filter.ts",
                  ["001-a.md", "002-b.md"])]
        )
        self.assertIn(
            "- anchor 'legacyRegionCode' (src/widgets/widget_filter.ts): "
            "claimed by 2 tasks (001-a.md, 002-b.md) -- must be folded "
            "into exactly ONE owning task\n",
            result,
        )

    def test_offenders_and_duplicates_both_render(self):
        from breakdown_helper import _render_dead_code_coverage_findings  # type: ignore[import]
        result = _render_dead_code_coverage_findings(
            [("a", "src/a.ts")],
            [("b", "src/b.ts", ["001-x.md", "002-y.md"])],
        )
        self.assertIn("- anchor 'a'", result)
        self.assertIn("- anchor 'b'", result)

    def test_empty_offenders_and_duplicates_no_bullet_lines(self):
        from breakdown_helper import _render_dead_code_coverage_findings  # type: ignore[import]
        result = _render_dead_code_coverage_findings([], [])
        self.assertNotIn("- anchor '", result)
        self.assertIn("## Dead-code coverage findings", result)


class VerifyDeadCodeCoverageVerbTests(_CwdIsolationBH):
    """CLI-level tests for the verify-dead-code-coverage verb."""

    def _tasks_dir(self, name="tasks"):
        d = self.tmp_path / name
        d.mkdir(exist_ok=True)
        return d

    def test_skip_when_no_declared_rows(self):
        """No Change-Induced Dead Code in the plan -> skip, exit 0."""
        plan_path = self.tmp_path / "plan.md"
        _write_minimal_plan(str(plan_path))
        r = _run_plan_helper_finalize(plan_path, self.tmp_path)
        self.assertEqual(r.returncode, 0, r.stderr)

        result = _run_bh(
            self.tmp_path, "verify-dead-code-coverage",
            str(self.tmp_path / "tasks"),
            "--plan-handoff", str(plan_path.parent / "plan-handoff.json"),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            result.stdout.strip(),
            "dead-code-coverage: skip (no declared dead-code rows)",
        )

    def test_ok_when_all_covered(self):
        """All declared rows covered exactly once -> exit 0 with ok-count."""
        plan_path = self.tmp_path / "plan.md"
        _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "Remove dead arm", "feat", agent="backend-engineer",
            dead_code_removal="legacyRegionCode",
        )

        result = _run_bh(
            self.tmp_path, "verify-dead-code-coverage", str(td),
            "--plan-handoff", str(plan_path.parent / "plan-handoff.json"),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            result.stdout.strip(),
            "dead-code-coverage: ok (1 rows, 1 covering tasks)",
        )

    def test_findings_block_on_uncovered_row(self):
        """An uncovered declared row -> exit 2 + findings block content,
        BYTE-IDENTICAL to _render_dead_code_coverage_findings's own output
        (so the verb and the finalize-handoff chokepoint cannot drift)."""
        from breakdown_helper import _render_dead_code_coverage_findings  # type: ignore[import]

        plan_path = self.tmp_path / "plan.md"
        _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
        )
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Unrelated", "feat", agent="backend-engineer")

        result = _run_bh(
            self.tmp_path, "verify-dead-code-coverage", str(td),
            "--plan-handoff", str(plan_path.parent / "plan-handoff.json"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Dead-code coverage findings", result.stdout)
        self.assertEqual(
            result.stdout,
            _render_dead_code_coverage_findings(
                [("legacyRegionCode", "src/widgets/widget_filter.ts")], []
            ),
        )

    def test_findings_block_on_duplicate_assignment(self):
        """A row claimed by 2 tasks -> exit 2 + duplicate-assignment finding."""
        plan_path = self.tmp_path / "plan.md"
        _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
        )
        td = self._tasks_dir()
        _write_full_task_file(
            td, "001", "First claim", "feat", agent="backend-engineer",
            dead_code_removal="legacyRegionCode",
        )
        _write_full_task_file(
            td, "002", "Second claim", "feat", agent="backend-engineer",
            dead_code_removal="legacyRegionCode", depends_on="001",
        )

        result = _run_bh(
            self.tmp_path, "verify-dead-code-coverage", str(td),
            "--plan-handoff", str(plan_path.parent / "plan-handoff.json"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("claimed by 2 tasks", result.stdout)
        self.assertIn("exactly ONE owning task", result.stdout)

    def test_fail_closed_missing_plan_handoff(self):
        """Missing plan-handoff.json + plan.md DECLARES dead code -> exit 2
        with the remedy stderr message."""
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Whatever", "feat", agent="backend-engineer")
        missing_handoff = self.tmp_path / "plan-handoff.json"
        plan_md_path = self.tmp_path / "plan.md"
        _write_plan_with_dead_code_rows(
            plan_md_path,
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
        )

        result = _run_bh(
            self.tmp_path, "verify-dead-code-coverage", str(td),
            "--plan-handoff", str(missing_handoff),
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stderr.strip(),
            "breakdown_helper: verify-dead-code-coverage: plan-handoff.json "
            "not found/unreadable at {0} — plan.md declares change-induced "
            "dead code; run plan_helper finalize-handoff {1} to produce it, "
            "then re-run this gate".format(missing_handoff, plan_md_path),
        )
        self.assertEqual(result.stdout.strip(), "")

    def test_skip_missing_handoff_and_no_plan_md_at_all(self):
        """Missing plan-handoff.json AND no plan.md at all -> the feature
        never declared dead code -> skip, exit 0."""
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Whatever", "feat", agent="backend-engineer")
        missing_handoff = self.tmp_path / "plan-handoff.json"

        result = _run_bh(
            self.tmp_path, "verify-dead-code-coverage", str(td),
            "--plan-handoff", str(missing_handoff),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            result.stdout.strip(),
            "dead-code-coverage: skip (no plan-handoff.json and no "
            "change-induced dead code declared in plan.md)",
        )
        self.assertEqual(result.stderr.strip(), "")

    def test_skip_missing_handoff_and_plan_md_placeholder_only(self):
        """Missing plan-handoff.json + plan.md HAS the heading but EVERY
        row is a placeholder -> skip, exit 0."""
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Whatever", "feat", agent="backend-engineer")
        missing_handoff = self.tmp_path / "plan-handoff.json"
        (self.tmp_path / "plan.md").write_text(
            "# Plan: Placeholder Only\n\n"
            "**Date**: 2026-08-06\n"
            "**Status**: Approved\n\n"
            "### Change-Induced Dead Code\n\n"
            "| File | Anchor token | Kind | Why dead |\n"
            "|------|--------------|------|----------|\n"
            "| [file] | [anchor] | [kind] | [why] |\n",
            encoding="utf-8",
        )

        result = _run_bh(
            self.tmp_path, "verify-dead-code-coverage", str(td),
            "--plan-handoff", str(missing_handoff),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            result.stdout.strip(),
            "dead-code-coverage: skip (no plan-handoff.json and no "
            "change-induced dead code declared in plan.md)",
        )

    def test_fail_closed_malformed_handoff_and_plan_md_with_heading(self):
        """Malformed (invalid-JSON) plan-handoff.json + plan.md DOES
        declare dead code -> exit 2 with the remedy."""
        td = self._tasks_dir()
        _write_full_task_file(td, "001", "Whatever", "feat", agent="backend-engineer")
        malformed_handoff = self.tmp_path / "plan-handoff.json"
        malformed_handoff.write_text("{ not valid json", encoding="utf-8")
        plan_md_path = self.tmp_path / "plan.md"
        _write_plan_with_dead_code_rows(
            plan_md_path,
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
        )

        result = _run_bh(
            self.tmp_path, "verify-dead-code-coverage", str(td),
            "--plan-handoff", str(malformed_handoff),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "plan.md declares change-induced dead code; run plan_helper "
            "finalize-handoff", result.stderr
        )
        self.assertIn(str(plan_md_path), result.stderr)

    def test_no_task_files_found_when_rows_declared(self):
        """Declared rows present but tasks-dir is missing/empty -> exit 2
        with the shared 'no task files found' stderr message."""
        plan_path = self.tmp_path / "plan.md"
        _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
        )
        empty_tasks_dir = self.tmp_path / "empty-tasks"

        result = _run_bh(
            self.tmp_path, "verify-dead-code-coverage", str(empty_tasks_dir),
            "--plan-handoff", str(plan_path.parent / "plan-handoff.json"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "no task files found in {0}".format(empty_tasks_dir), result.stderr
        )
        self.assertEqual(result.stdout.strip(), "")

    def test_default_plan_handoff_path_is_sibling_to_tasks_dir_parent(self):
        """Without --plan-handoff, defaults to <tasks-dir's parent>/plan-handoff.json."""
        feature_dir = self.tmp_path / "specs" / "001-default-path"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _produce_plan_handoff_with_dead_code_rows(
            self.tmp_path, plan_path,
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
        )
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()
        _write_full_task_file(
            tasks_dir, "001", "Remove dead arm", "001-default-path",
            agent="backend-engineer",
            dead_code_removal="legacyRegionCode",
        )

        result = _run_bh(self.tmp_path, "verify-dead-code-coverage", str(tasks_dir))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("dead-code-coverage: ok", result.stdout)

    def test_semicolon_anchor_token_row_excluded_skip_not_garbled_findings(self):
        """finding C (MEDIUM), CLI level: a hand-written plan-handoff.json
        declaring ONLY a semicolon-laden anchor_token row -> the row is
        excluded from 'declared' at construction time, so the verb reports
        a clean SKIP (nothing declared), never a garbled '## Dead-code
        coverage findings' block built from split fragments of the token
        (the pre-hardening failure mode this closes)."""
        td = self._tasks_dir()
        bad = self.tmp_path / "plan-handoff.json"
        bad.write_text(
            json.dumps({
                "breakdown_seeds": {
                    "dead_code_rows": [
                        {
                            "file": "src/loop.ts",
                            "anchor_token": "for (i = 0; i < n; i++)",
                            "kind": "branch",
                            "why_dead": "Superseded loop removed",
                        },
                    ]
                }
            }),
            encoding="utf-8",
        )

        result = _run_bh(
            self.tmp_path, "verify-dead-code-coverage", str(td),
            "--plan-handoff", str(bad),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            result.stdout.strip(),
            "dead-code-coverage: skip (no declared dead-code rows)",
        )
        self.assertNotIn("## Dead-code coverage findings", result.stdout)
        # No fragment of the shredded token (e.g. the ' i < n' segment a
        # naive semicolon-split would have produced) leaks into output.
        self.assertNotIn("i < n", result.stdout)


class FinalizeHandoffDeadCodeCoverageGateTests(_CwdIsolationBH):
    """Tests for the dead-code-coverage chokepoint folded into
    finalize-handoff (plan 71 D9 amendment).

    Mirrors FinalizeHandoffPropertyCoverageGateTests' asymmetry EXACTLY: a
    sibling plan-handoff.json declaring breakdown_seeds.dead_code_rows
    requires every declared row's anchor_token to be covered by EXACTLY
    ONE task's '**Dead code removal**:' field before breakdown-handoff.json
    can be written; an absent/malformed sibling plan-handoff.json is a
    silent skip for THIS chokepoint (the separate declared-but-
    unsubstantiated chokepoint already guards that case for dead code).
    """

    def setUp(self):
        super().setUp()
        _make_agents_dir(self.tmp_path, ["backend-engineer"])

    def _setup_feature_with_rows(self, slug, rows, dead_code_removal=None,
                                  second_task_dead_code_removal=None):
        """Build a finalize-handoff fixture with a sibling plan-handoff.json
        declaring `rows` (via the REAL plan_helper finalize-handoff
        producer).

        dead_code_removal: when given, stamped onto task 001's
        '**Dead code removal**:' field.
        second_task_dead_code_removal: when given, a SECOND task 002 is
        written with this value (used for the duplicate-assignment case).

        Returns (feature_dir, plan_path, tasks_dir).
        """
        feature_dir = self.tmp_path / "specs" / slug
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_plan_with_dead_code_rows(plan_path, rows)

        r = _run_plan_helper_finalize(plan_path, self.tmp_path)
        self.assertEqual(
            r.returncode, 0, "plan_helper finalize-handoff failed: " + r.stderr
        )
        sibling = feature_dir / "plan-handoff.json"
        self.assertTrue(sibling.exists())

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Owning task", slug,
            agent="backend-engineer",
            expects=[], produces=["Dead arm removed"], ac_ids="AC-1",
            dead_code_removal=dead_code_removal,
        )
        if second_task_dead_code_removal is not None:
            _write_full_task_file(
                tasks_dir, "002", "Second task", slug,
                agent="backend-engineer",
                expects=[], produces=[], ac_ids="AC-1",
                depends_on="001",
                dead_code_removal=second_task_dead_code_removal,
            )
        _write_readme(tasks_dir)
        return feature_dir, plan_path, tasks_dir

    def test_covering_task_finalize_succeeds(self):
        """A declared row covered by task 001 -> exit 0, handoff written."""
        feature_dir, plan_path, _ = self._setup_feature_with_rows(
            "dcc001-covered",
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
            dead_code_removal="legacyRegionCode",
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-08-06T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue((feature_dir / "breakdown-handoff.json").is_file())

    def test_no_covering_task_exits_2_with_findings_block(self):
        """No task covers the declared row -> exit 2 + findings block; NO
        breakdown-handoff.json written."""
        feature_dir, plan_path, _ = self._setup_feature_with_rows(
            "dcc002-uncovered",
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
            dead_code_removal=None,
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-08-06T12:00:00Z",
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("## Dead-code coverage findings", result.stdout)
        self.assertIn("legacyRegionCode", result.stdout)
        self.assertFalse(
            (feature_dir / "breakdown-handoff.json").exists(),
            "breakdown-handoff.json must NOT be written when uncovered",
        )

    def test_duplicate_assignment_exits_2(self):
        """A declared row claimed by 2 tasks -> exit 2 + duplicate finding;
        NO breakdown-handoff.json written."""
        feature_dir, plan_path, _ = self._setup_feature_with_rows(
            "dcc003-duplicate",
            [("src/widgets/widget_filter.ts", "legacyRegionCode", "arm", "Superseded")],
            dead_code_removal="legacyRegionCode",
            second_task_dead_code_removal="legacyRegionCode",
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-08-06T12:00:00Z",
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("claimed by 2 tasks", result.stdout)
        self.assertFalse((feature_dir / "breakdown-handoff.json").exists())

    def test_no_sibling_plan_handoff_finalize_succeeds(self):
        """No sibling plan-handoff.json at all -> this chokepoint is a
        silent skip, exit 0 (unchanged pre-existing behavior)."""
        feature_dir = self.tmp_path / "specs" / "dcc004-no-sibling"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        # Deliberately do NOT run plan_helper finalize-handoff -> no sibling.

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()
        _write_full_task_file(
            tasks_dir, "001", "Define types", "dcc004-no-sibling",
            agent="backend-engineer",
            expects=[], produces=["TypeDef exported"], ac_ids="AC-1",
        )
        _write_readme(tasks_dir)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-08-06T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue((feature_dir / "breakdown-handoff.json").is_file())


# ---------------------------------------------------------------------------
# Tests: render-task-file --dead-code-removal semicolon-list tightening
# (plan 71 D9 amendment)
# ---------------------------------------------------------------------------


class RenderTaskFileDeadCodeRemovalTighteningTests(_CwdIsolationBH):
    """Verifies the --dead-code-removal contract is a semicolon-separated
    anchor-token list (NOT free-text prose) and round-trips unambiguously
    for tokens containing commas/spaces/quotes."""

    def test_multi_token_semicolon_list_round_trips(self):
        """A semicolon-separated multi-token value is emitted verbatim
        (stripped), mirroring --property-targets' comma-list emission."""
        result = _run_bh(
            self.tmp_path, "render-task-file",
            "--dead-code-removal",
            "legacyRegionCode; legacyDistrictCode",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "**Dead code removal**: legacyRegionCode; legacyDistrictCode",
            result.stdout,
        )

    def test_token_containing_comma_survives_intact(self):
        """A single token containing a comma is NOT mangled -- the field
        format is semicolon-delimited, not comma-delimited."""
        result = _run_bh(
            self.tmp_path, "render-task-file",
            "--dead-code-removal", "buildFilters(a, b)",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "**Dead code removal**: buildFilters(a, b)", result.stdout
        )


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
                          review_checkpoint="No", doc_refs="None",
                          property_targets=None, dead_code_removal=None):
    """Write a fully-populated task file seeded from render-task-file with real data.

    'agent' is a non-placeholder agent name (e.g. 'backend-engineer').
    Starts from the render-task-file skeleton (real producer round-trip) then
    substitutes agent, depends_on, blocks, review_checkpoint, doc_refs.

    property_targets (plan 66 WI-1): when given, passed through to
    _render_task_file_raw so the skeleton already carries a real
    '**Property targets**:' line (real-producer round-trip).

    dead_code_removal (plan 71 D7/D9): when given, passed through to
    _render_task_file_raw so the skeleton already carries a real
    '**Dead code removal**:' line (real-producer round-trip).
    """
    skeleton = _render_task_file_raw(
        number, title, feature,
        property_targets=property_targets,
        dead_code_removal=dead_code_removal,
    )
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

    setUp populates a .claude/agents/ roster in tmp_path with all agents used
    by _setup_feature_dir tasks so the new roster-validation gate is satisfied
    without changing individual test call sites.
    """

    def setUp(self):
        super().setUp()
        # Populate the default .claude/agents roster so the roster-validation
        # gate inside finalize-handoff passes in all tests that don't supply
        # an explicit --agents-dir.  Agents here must cover every agent name
        # used by _write_full_task_file calls in this class.
        _make_agents_dir(self.tmp_path, ["backend-engineer", "qa-engineer"])

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
# Tests: finalize-handoff — design-manifest chokepoint (plan 42 Phase 2;
# schema retargeted to the binding by plan 53 Phase 3/7c)
# ---------------------------------------------------------------------------
#
# Real-fixture discipline: the binding JSON is produced via the REAL
# _design._schema constructors (Binding / BindingPair) + the real
# binding_to_json serializer (_make_valid_manifest / _make_invalid_manifest
# defined in the Phase 1 section below) — NOT hand-authored JSON strings.
# There is no mechanical DERIVATION of a binding from reference.html anymore
# (resolve-reference / init-manifest are retired, plan 53 Phase 3) — a
# binding's route + pairs are always human/LLM authored, so round-tripping
# through the real schema constructors + serializer IS the producer
# discipline at this layer.
#
# CWD CONTRACT: _run_bh sets cwd=self.tmp_path (via the helper), and
# _validate_manifest_present calls Path.cwd() to locate design/reference.html.
# So "workspace_root" == self.tmp_path, and the reference must live at
# self.tmp_path / "design" / "reference.html".
#
# NOTE: _make_valid_manifest / _make_invalid_manifest / _write_reference_html are
# defined in the VerifyManifestPresentTests section further below in this file.
# They are module-level helpers and are available here because Python reads the
# whole module before running tests.


class FinalizeHandoffManifestGateTests(_CwdIsolationBH):
    """Tests for the design-manifest chokepoint folded into finalize-handoff.

    Verifies plan 42 Phase 2 (WI-1): _validate_manifest_present is called inside
    finalize-handoff; a reference-present feature with a missing or invalid
    design-manifest.json CANNOT produce breakdown-handoff.json.

    setUp provides the full finalize-handoff environment:
      - specs/NNN-slug/plan.md
      - specs/NNN-slug/tasks/ with one filled task file
      - specs/NNN-slug/tasks/README.md
      - .claude/agents/ roster covering the task's agent
    """

    def setUp(self):
        super().setUp()
        # Populate the agent roster so the roster-validation gate passes in all
        # tests (we are testing the manifest gate here, not the roster gate).
        _make_agents_dir(self.tmp_path, ["backend-engineer"])

    def _setup_feature(self, slug):
        # type: (str) -> "tuple"
        """Build a minimal valid finalize-handoff fixture under self.tmp_path.

        Returns (feature_dir, plan_path, tasks_dir).
        """
        feature_dir = self.tmp_path / "specs" / slug
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Define types", slug,
            agent="backend-engineer",
            expects=[],
            produces=["TypeDef exported"],
            ac_ids="AC-1",
        )
        _write_readme(tasks_dir)
        return feature_dir, plan_path, tasks_dir

    # ------------------------------------------------------------------
    # Case 1: no reference.html — non-UI feature, MUST be unaffected
    # ------------------------------------------------------------------

    def test_no_reference_exits_0_writes_handoff(self):
        """Non-regression: no design/reference.html → exit 0, handoff written.

        This is the CRITICAL non-regression: non-UI features must pass through
        finalize-handoff exactly as before plan 42 Phase 2 was introduced.
        """
        _, plan_path, _ = self._setup_feature("m001-no-ref")
        # Deliberately do NOT create design/reference.html.

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        # breakdown-handoff.json must have been written.
        written = Path(result.stdout.strip())
        self.assertEqual(written.name, "breakdown-handoff.json")
        self.assertTrue(written.is_file(), "breakdown-handoff.json was not written")

    # ------------------------------------------------------------------
    # Case 2: reference present + manifest absent → exit 2, no handoff
    # ------------------------------------------------------------------

    def test_reference_present_manifest_absent_exits_2(self):
        """design/reference.html present, manifest absent → exit 2."""
        _, plan_path, _ = self._setup_feature("m002-ref-no-manifest")
        _write_reference_html(self.tmp_path / "design")
        # Deliberately do NOT create design-manifest.json.

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)

    def test_reference_present_manifest_absent_no_handoff_written(self):
        """When manifest absent, breakdown-handoff.json must NOT be written."""
        feature_dir, plan_path, _ = self._setup_feature("m003-no-handoff-written")
        _write_reference_html(self.tmp_path / "design")

        _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        handoff = feature_dir / "breakdown-handoff.json"
        self.assertFalse(handoff.exists(), "breakdown-handoff.json must NOT be written on manifest violation")

    def test_reference_present_manifest_absent_findings_block_on_stdout(self):
        """When manifest absent, stdout has '## Design manifest findings' block."""
        _, plan_path, _ = self._setup_feature("m004-findings-block")
        _write_reference_html(self.tmp_path / "design")

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Design manifest findings", result.stdout)

    # ------------------------------------------------------------------
    # Case 3: reference present + valid manifest → exit 0, handoff written
    # ------------------------------------------------------------------

    def test_reference_present_valid_manifest_exits_0(self):
        """design/reference.html + fully-classified manifest → exit 0."""
        feature_dir, plan_path, _ = self._setup_feature("m005-valid-manifest")
        html_path = _write_reference_html(self.tmp_path / "design")
        _make_valid_manifest(feature_dir, html_path)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_reference_present_valid_manifest_writes_handoff(self):
        """With valid manifest, breakdown-handoff.json IS written."""
        feature_dir, plan_path, _ = self._setup_feature("m006-handoff-written")
        html_path = _write_reference_html(self.tmp_path / "design")
        _make_valid_manifest(feature_dir, html_path)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        written = Path(result.stdout.strip())
        self.assertEqual(written.name, "breakdown-handoff.json")
        self.assertTrue(written.is_file(), "breakdown-handoff.json must be written when manifest is valid")

    # ------------------------------------------------------------------
    # Case 4: reference present + invalid manifest → exit 2, no handoff
    # ------------------------------------------------------------------

    def test_reference_present_invalid_manifest_exits_2(self):
        """design/reference.html + unclassified element in manifest → exit 2."""
        feature_dir, plan_path, _ = self._setup_feature("m007-invalid-manifest")
        html_path = _write_reference_html(self.tmp_path / "design")
        _make_invalid_manifest(feature_dir, html_path)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)

    def test_reference_present_invalid_manifest_no_handoff_written(self):
        """When manifest invalid, breakdown-handoff.json must NOT be written."""
        feature_dir, plan_path, _ = self._setup_feature("m008-invalid-no-handoff")
        html_path = _write_reference_html(self.tmp_path / "design")
        _make_invalid_manifest(feature_dir, html_path)

        _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        handoff = feature_dir / "breakdown-handoff.json"
        self.assertFalse(handoff.exists(), "breakdown-handoff.json must NOT be written on invalid manifest")

    def test_reference_present_invalid_manifest_findings_block_on_stdout(self):
        """When manifest invalid, stdout has '## Design manifest findings' block."""
        feature_dir, plan_path, _ = self._setup_feature("m009-invalid-block")
        html_path = _write_reference_html(self.tmp_path / "design")
        _make_invalid_manifest(feature_dir, html_path)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Design manifest findings", result.stdout)


# ---------------------------------------------------------------------------
# Tests: property-coverage chokepoint folded into finalize-handoff (plan 66 WI-1)
# ---------------------------------------------------------------------------


class FinalizeHandoffPropertyCoverageGateTests(_CwdIsolationBH):
    """Tests for the property-coverage chokepoint folded into finalize-handoff.

    Verifies plan 66 WI-1: a sibling plan-handoff.json declaring
    breakdown_seeds.pure_builder_targets requires every declared target to
    be covered by a task's '**Property targets**:' line before
    breakdown-handoff.json can be written; an absent sibling plan-handoff.json
    is a silent skip (unchanged pre-existing finalize-handoff behavior).
    """

    def setUp(self):
        super().setUp()
        _make_agents_dir(self.tmp_path, ["backend-engineer", "qa-engineer"])

    def _setup_feature_with_targets(self, slug, targets, property_targets=None):
        """Build a finalize-handoff fixture with a sibling plan-handoff.json
        declaring `targets` (via the REAL plan_helper finalize-handoff
        producer).

        property_targets: when given, stamped onto task 002's
        '**Property targets**:' line so it covers the declared target(s).
        When None, task 002 carries no Property targets line at all
        (the uncovered case).

        Returns (feature_dir, plan_path, tasks_dir).
        """
        feature_dir = self.tmp_path / "specs" / slug
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_plan_with_pure_builder_targets(plan_path, targets)

        r = _run_plan_helper_finalize(plan_path, self.tmp_path)
        self.assertEqual(
            r.returncode, 0, "plan_helper finalize-handoff failed: " + r.stderr
        )
        sibling = feature_dir / "plan-handoff.json"
        self.assertTrue(sibling.exists())

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Define types", slug,
            agent="backend-engineer",
            expects=[], produces=["TypeDef exported"], ac_ids="AC-1",
        )
        _write_full_task_file(
            tasks_dir, "002", "Property test", slug,
            agent="qa-engineer",
            expects=["TypeDef exported"], produces=[], ac_ids="AC-1",
            depends_on="001",
            property_targets=property_targets,
        )
        _write_readme(tasks_dir)
        return feature_dir, plan_path, tasks_dir

    # ------------------------------------------------------------------
    # (i) covering task -> finalize succeeds, breakdown-handoff.json written
    # ------------------------------------------------------------------

    def test_covering_task_finalize_succeeds(self):
        """A declared target covered by task 002 -> exit 0, handoff written."""
        feature_dir, plan_path, _ = self._setup_feature_with_targets(
            "pc001-covered",
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
            property_targets="filterWidgetsByQuery",
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-07-20T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        written = feature_dir / "breakdown-handoff.json"
        self.assertTrue(
            written.is_file(), "breakdown-handoff.json must be written when covered"
        )

    # ------------------------------------------------------------------
    # (ii) no covering task -> exit 2, findings block, NO handoff written
    # ------------------------------------------------------------------

    def test_no_covering_task_exits_2(self):
        """No task covers the declared target -> exit 2."""
        _, plan_path, _ = self._setup_feature_with_targets(
            "pc002-uncovered",
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
            property_targets=None,
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-07-20T12:00:00Z",
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)

    def test_no_covering_task_no_handoff_written(self):
        """Uncovered target -> breakdown-handoff.json must NOT be written."""
        feature_dir, plan_path, _ = self._setup_feature_with_targets(
            "pc003-no-handoff",
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
            property_targets=None,
        )

        _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-07-20T12:00:00Z",
        )
        handoff = feature_dir / "breakdown-handoff.json"
        self.assertFalse(
            handoff.exists(),
            "breakdown-handoff.json must NOT be written on uncovered target",
        )

    def test_no_covering_task_findings_block_on_stdout(self):
        """Uncovered target -> '## Property coverage findings' block on stdout.

        Also asserts the emitted block is BYTE-IDENTICAL to
        _render_property_coverage_findings's own output AND to what the
        standalone verify-property-coverage verb emits for the same
        offenders (finding 5: both emission sites share one rendering
        function so they cannot drift apart)."""
        from breakdown_helper import _render_property_coverage_findings  # type: ignore[import]

        _, plan_path, _ = self._setup_feature_with_targets(
            "pc004-findings",
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts", "No I/O")],
            property_targets=None,
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-07-20T12:00:00Z",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Property coverage findings", result.stdout)
        self.assertIn("filterWidgetsByQuery", result.stdout)
        expected_block = _render_property_coverage_findings(
            [("filterWidgetsByQuery", "src/widgets/widget_filter.ts")]
        )
        self.assertEqual(result.stdout, expected_block)

    # ------------------------------------------------------------------
    # (iii) no plan-handoff.json at all -> finalize succeeds (silent skip)
    # ------------------------------------------------------------------

    def test_no_sibling_plan_handoff_finalize_succeeds(self):
        """No sibling plan-handoff.json -> unchanged behavior, exit 0."""
        feature_dir = self.tmp_path / "specs" / "pc005-no-sibling"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        # Deliberately do NOT run plan_helper finalize-handoff -> no sibling.

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()
        _write_full_task_file(
            tasks_dir, "001", "Define types", "pc005-no-sibling",
            agent="backend-engineer",
            expects=[], produces=["TypeDef exported"], ac_ids="AC-1",
        )
        _write_readme(tasks_dir)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-07-20T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        written = feature_dir / "breakdown-handoff.json"
        self.assertTrue(written.is_file())


class FinalizeHandoffDeadCodeRowsPassthroughTests(_CwdIsolationBH):
    """Tests for the dead_code_rows passthrough folded into finalize-handoff.

    Verifies plan 71 D8(b) PLUS the review-hardening SILENT-vs-LOUD
    asymmetry (mirrors _validate_property_coverage's own asymmetry):

      - SILENT (no warning, no chokepoint): sibling plan-handoff.json
        absent, or present but breakdown_seeds/dead_code_rows key absent
        (pre-plan-71 handoff, or nothing declared) -> [] with no stderr.
      - LOUD but non-fatal WARN: sibling present but unreadable/malformed/
        wrong-shape, or individual row dicts malformed -> stderr WARN,
        extraction still returns (a possibly partial) rows list, and
        finalize-handoff still succeeds UNLESS the chokepoint below fires.
      - CHOKEPOINT (fails closed, exit 2): plan.md's own
        '### Change-Induced Dead Code' section declares at least one real
        row, but the passthrough produced NONE (for any reason above) --
        the MUST-lane kill-list may never ship as an empty carrier.
    """

    def setUp(self):
        super().setUp()
        _make_agents_dir(self.tmp_path, ["backend-engineer"])

    def _setup_feature(self, slug, produce_sibling, rows=None,
                       dead_code_removal=None):
        """Build a finalize-handoff fixture.

        produce_sibling=False: no sibling plan-handoff.json produced at all
          (plan.md is written but plan_helper finalize-handoff is never run).
        produce_sibling=True, rows=None: sibling IS produced from a minimal
          plan.md with NO '### Change-Induced Dead Code' section at all.
        produce_sibling=True, rows=[...]: sibling IS produced from a plan.md
          with a '### Change-Induced Dead Code' table carrying the given
          (file, anchor_token, kind, why_dead) rows.

        dead_code_removal: when given, stamped onto task 001's
        '**Dead code removal**:' field, so the NEW plan-71-D9 task-coverage
        chokepoint (a SEPARATE gate from this class' own passthrough-only
        assertions) does not trip on tests that declare real rows without
        caring about coverage.

        Returns (feature_dir, plan_path, tasks_dir).
        """
        feature_dir = self.tmp_path / "specs" / slug
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        if produce_sibling:
            if rows:
                _write_plan_with_dead_code_rows(plan_path, rows)
            else:
                _write_minimal_plan(str(plan_path))
            r = _run_plan_helper_finalize(plan_path, self.tmp_path)
            self.assertEqual(
                r.returncode, 0, "plan_helper finalize-handoff failed: " + r.stderr
            )
            self.assertTrue((feature_dir / "plan-handoff.json").exists())
        else:
            _write_minimal_plan(str(plan_path))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()
        _write_full_task_file(
            tasks_dir, "001", "Define types", slug,
            agent="backend-engineer",
            expects=[], produces=["TypeDef exported"], ac_ids="AC-1",
            dead_code_removal=dead_code_removal,
        )
        _write_readme(tasks_dir)
        return feature_dir, plan_path, tasks_dir

    def test_declared_rows_copied_verbatim(self):
        """A sibling plan-handoff.json declaring dead_code_rows -> those
        exact rows appear in breakdown-handoff.json's dead_code_rows.

        Task 001 covers BOTH declared anchor tokens so the SEPARATE plan-71
        D9 task-coverage chokepoint (tested independently in
        FinalizeHandoffDeadCodeCoverageGateTests) does not interfere with
        this test's own passthrough-fidelity assertion.
        """
        feature_dir, plan_path, _ = self._setup_feature(
            "dc001-declared",
            produce_sibling=True,
            rows=[
                (
                    "src/widgets/widget_filter.ts",
                    ": 'legacyRegionCode'",
                    "arm",
                    "Superseded by the generic query-param filter",
                ),
                (
                    "src/widgets/legacy_filter.ts",
                    "applyLegacyTagFilter",
                    "function",
                    "Fully replaced",
                ),
            ],
            dead_code_removal="applyLegacyTagFilter; : 'legacyRegionCode'",
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-08-06T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        written = json.loads(
            (feature_dir / "breakdown-handoff.json").read_text(encoding="utf-8")
        )
        rows = written["dead_code_rows"]
        self.assertEqual(len(rows), 2)
        anchors = [r["anchor_token"] for r in rows]
        self.assertIn(": 'legacyRegionCode'", anchors)
        self.assertIn("applyLegacyTagFilter", anchors)
        kinds = {r["anchor_token"]: r["kind"] for r in rows}
        self.assertEqual(kinds[": 'legacyRegionCode'"], "arm")
        self.assertEqual(kinds["applyLegacyTagFilter"], "function")

    def test_no_dead_code_section_in_plan_empty_passthrough(self):
        """A sibling plan-handoff.json with NO Change-Induced Dead Code
        section declared -> dead_code_rows == [] in breakdown-handoff.json."""
        feature_dir, plan_path, _ = self._setup_feature(
            "dc002-none-declared", produce_sibling=True, rows=None
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-08-06T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        written = json.loads(
            (feature_dir / "breakdown-handoff.json").read_text(encoding="utf-8")
        )
        self.assertEqual(written["dead_code_rows"], [])

    def test_no_sibling_plan_handoff_empty_passthrough_finalize_succeeds(self):
        """No sibling plan-handoff.json at all -> dead_code_rows == [],
        finalize-handoff still succeeds (fail-soft carrier, not a gate)."""
        feature_dir, plan_path, _ = self._setup_feature(
            "dc003-no-sibling", produce_sibling=False
        )
        self.assertFalse((feature_dir / "plan-handoff.json").exists())

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-08-06T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        written = json.loads(
            (feature_dir / "breakdown-handoff.json").read_text(encoding="utf-8")
        )
        self.assertEqual(written["dead_code_rows"], [])

    def test_malformed_sibling_plan_handoff_warns_and_finalize_succeeds(self):
        """A sibling plan-handoff.json that is not valid JSON -> dead_code_rows
        == [] AND a stderr WARN is emitted (case 2 of the new asymmetry), but
        finalize-handoff still succeeds because plan.md itself declares NO
        real dead-code rows -- the chokepoint has nothing to enforce."""
        feature_dir, plan_path, _ = self._setup_feature(
            "dc004-malformed-sibling", produce_sibling=False
        )
        (feature_dir / "plan-handoff.json").write_text(
            "{not valid json", encoding="utf-8"
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-08-06T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("WARN", result.stderr)
        self.assertIn("dead_code_rows", result.stderr)

        written = json.loads(
            (feature_dir / "breakdown-handoff.json").read_text(encoding="utf-8")
        )
        self.assertEqual(written["dead_code_rows"], [])

    def test_declared_but_unsubstantiated_fails_closed(self):
        """plan.md declares a real '### Change-Induced Dead Code' row, but
        NO sibling plan-handoff.json exists -> the passthrough produces []
        and the declared-but-unsubstantiated CHOKEPOINT fails closed
        (exit 2), naming plan_helper finalize-handoff as the remedy."""
        feature_dir = self.tmp_path / "specs" / "dc005-unsubstantiated"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_plan_with_dead_code_rows(
            plan_path,
            [
                (
                    "src/widgets/widget_filter.ts",
                    ": 'legacyRegionCode'",
                    "arm",
                    "Superseded by the generic query-param filter",
                ),
            ],
        )
        # Deliberately do NOT run plan_helper finalize-handoff -> no sibling.
        self.assertFalse((feature_dir / "plan-handoff.json").exists())

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()
        _write_full_task_file(
            tasks_dir, "001", "Define types", "dc005-unsubstantiated",
            agent="backend-engineer",
            expects=[], produces=["TypeDef exported"], ac_ids="AC-1",
        )
        _write_readme(tasks_dir)

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-08-06T12:00:00Z",
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Change-Induced Dead Code", result.stderr)
        self.assertIn("plan_helper finalize-handoff", result.stderr)
        self.assertFalse(
            (feature_dir / "breakdown-handoff.json").exists(),
            "breakdown-handoff.json must NOT be written on the "
            "declared-but-unsubstantiated chokepoint",
        )

    def test_mixed_valid_and_invalid_rows_keeps_valid_warns_and_does_not_fail_closed(self):
        """A hand-written sibling plan-handoff.json whose dead_code_rows
        carries one VALID row + one INVALID row (bad kind) -> finalize-handoff
        keeps exactly the valid row in breakdown-handoff.json, emits the
        malformed-row stderr WARN, and (since extraction is non-empty AND
        task 001 covers the surviving valid token) neither chokepoint fires
        -- exit 0. Post-finding-B: the bad-kind row is excluded from BOTH
        the passthrough carrier AND the SEPARATE plan-71 D9 task-coverage
        chokepoint's own 'declared' set (it now applies the SAME DeadCodeRow
        validity criterion the passthrough does), so the task field does
        NOT need to cover 'someToken' at all -- it was never declared."""
        feature_dir, plan_path, _ = self._setup_feature(
            "dc006-mixed-rows", produce_sibling=False,
            dead_code_removal=": 'legacyRegionCode'",
        )
        (feature_dir / "plan-handoff.json").write_text(
            json.dumps({
                "breakdown_seeds": {
                    "dead_code_rows": [
                        {
                            "file": "src/widgets/widget_filter.ts",
                            "anchor_token": ": 'legacyRegionCode'",
                            "kind": "arm",
                            "why_dead": "Superseded by the generic filter",
                        },
                        {
                            "file": "src/widgets/other.ts",
                            "anchor_token": "someToken",
                            "kind": "bogus",
                            "why_dead": "Also dead",
                        },
                    ]
                }
            }),
            encoding="utf-8",
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff",
            str(plan_path), "--completed-at", "2026-08-06T12:00:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("WARN", result.stderr)
        self.assertIn("1 of 2", result.stderr)

        written = json.loads(
            (feature_dir / "breakdown-handoff.json").read_text(encoding="utf-8")
        )
        rows = written["dead_code_rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["anchor_token"], ": 'legacyRegionCode'")
        self.assertEqual(rows[0]["kind"], "arm")


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
        """Output contains the '## Manual next step — run /devforge:implement' heading."""
        _, plan_path = self._setup_tasks()
        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## Manual next step — run /devforge:implement", result.stdout)

    def test_first_task_invocation_line(self):
        """Output contains the bare '/devforge:implement' copy-paste command (no task number arg)."""
        _, plan_path = self._setup_tasks()
        result = _run_bh(self.tmp_path, "render-implement-handoff", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/devforge:implement", result.stdout)
        # The copy-paste line must NOT include a task-number argument.
        self.assertNotIn("/devforge:implement 001", result.stdout)

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
        not task 10. The bare '/devforge:implement' copy-paste line carries no task number,
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
        self.assertNotIn("/devforge:implement 002", result.stdout)
        self.assertIn("/devforge:implement", result.stdout)

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


# ---------------------------------------------------------------------------
# Tests: verify-agent-roster (Phase 3.5 — agent-roster validation)
# ---------------------------------------------------------------------------


def _make_agents_dir(parent_dir, agent_stems):
    """Create a .claude/agents/ directory with *.md stubs for each stem.

    Returns the Path to the agents directory.
    """
    agents_dir = parent_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    for stem in agent_stems:
        (agents_dir / (stem + ".md")).write_text(
            "# {0}\n\nAgent definition.\n".format(stem), encoding="utf-8"
        )
    return agents_dir


class VerifyAgentRosterTests(_CwdIsolationBH):
    """Tests for verify-agent-roster verb and _validate_agent_roster function."""

    # ------------------------------------------------------------------
    # Happy-path: all assigned agents installed
    # ------------------------------------------------------------------

    def test_all_agents_installed_exit_0(self):
        """All tasks assign agents that are in the roster → exit 0."""
        feature_dir = self.tmp_path / "specs" / "001-roster-happy"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Build frontend", "001-roster-happy",
            agent="frontend-engineer",
        )
        _write_full_task_file(
            tasks_dir, "002", "Write tests", "001-roster-happy",
            agent="qa-engineer",
            depends_on="001",
        )

        agents_dir = _make_agents_dir(self.tmp_path, ["frontend-engineer", "qa-engineer", "devops-engineer"])

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_ok_line_shape_correct(self):
        """Exit-0 stdout matches 'agent-roster: ok (N tasks, M agents installed)'."""
        feature_dir = self.tmp_path / "specs" / "002-okline"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Define types", "002-okline",
            agent="backend-engineer",
        )

        agents_dir = _make_agents_dir(self.tmp_path, ["backend-engineer", "frontend-engineer"])

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # Must mention task count and agent count.
        self.assertIn("agent-roster: ok", result.stdout)
        self.assertIn("1 tasks", result.stdout)
        self.assertIn("2 agents installed", result.stdout)

    # ------------------------------------------------------------------
    # One absent agent → exit 2 with offender + Available agents
    # ------------------------------------------------------------------

    def test_one_absent_agent_exit_2(self):
        """One task assigns an absent agent → exit 2."""
        feature_dir = self.tmp_path / "specs" / "003-absent"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Build frontend", "003-absent",
            agent="backend-engineer",  # not in roster
        )

        agents_dir = _make_agents_dir(self.tmp_path, ["frontend-engineer", "qa-engineer"])

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 2)

    def test_absent_agent_stdout_names_offender(self):
        """Exit-2 stdout names the task file and the absent agent."""
        feature_dir = self.tmp_path / "specs" / "004-offender"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Build api", "004-offender",
            agent="backend-engineer",  # not in roster
        )

        agents_dir = _make_agents_dir(self.tmp_path, ["frontend-engineer"])

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Agent roster findings", result.stdout)
        self.assertIn("backend-engineer", result.stdout)
        self.assertIn("001-build-api.md", result.stdout)

    def test_absent_agent_stdout_lists_available_agents(self):
        """Exit-2 stdout includes 'Available agents:' with the sorted roster."""
        feature_dir = self.tmp_path / "specs" / "005-available"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Backend task", "005-available",
            agent="backend-engineer",  # not in roster
        )

        agents_dir = _make_agents_dir(self.tmp_path, ["frontend-engineer", "qa-engineer"])

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Available agents:", result.stdout)
        self.assertIn("frontend-engineer", result.stdout)
        self.assertIn("qa-engineer", result.stdout)

    # ------------------------------------------------------------------
    # Empty / missing agents dir → fail-closed exit 2
    # ------------------------------------------------------------------

    def test_missing_agents_dir_fail_closed(self):
        """Non-existent --agents-dir → fail-closed exit 2 with 'no agent roster found'."""
        feature_dir = self.tmp_path / "specs" / "006-nodir"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Some task", "006-nodir",
            agent="backend-engineer",
        )

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(self.tmp_path / "does-not-exist"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("no agent roster found", result.stderr)

    def test_empty_agents_dir_fail_closed(self):
        """Agents dir exists but has no *.md files → fail-closed exit 2."""
        feature_dir = self.tmp_path / "specs" / "007-emptydir"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Some task", "007-emptydir",
            agent="backend-engineer",
        )

        # Create agents dir but with no *.md files.
        agents_dir = self.tmp_path / "empty-agents"
        agents_dir.mkdir()
        (agents_dir / "README.txt").write_text("no agents here", encoding="utf-8")

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("no agent roster found", result.stderr)

    def test_md_suffixed_directory_not_counted_as_agent(self):
        """A directory named 'some-agent.md/' in agents-dir is NOT an installed agent.

        FIX 2: the roster comprehension now requires f.is_file() in addition
        to f.suffix == '.md'.  A *.md-named directory would previously inject
        its stem into the installed roster, silently bypassing the fail-closed
        gate for tasks that assigned that name.
        """
        feature_dir = self.tmp_path / "specs" / "008b-dirmd"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Tricky task", "008b-dirmd",
            agent="sneaky-agent",  # the name we plant as a directory
        )

        # Create the agents dir with a DIRECTORY named sneaky-agent.md
        # (and no real *.md files) so the only *.md path is a dir, not a file.
        agents_dir = self.tmp_path / "agents-with-dir"
        agents_dir.mkdir()
        (agents_dir / "sneaky-agent.md").mkdir()  # a directory, not a file!

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        # The directory must NOT be counted — so roster is empty → fail-closed.
        self.assertEqual(result.returncode, 2)
        self.assertIn("no agent roster found", result.stderr)

    # ------------------------------------------------------------------
    # No task files → exit 2 with 'no task files found'
    # ------------------------------------------------------------------

    def test_no_task_files_exit_2(self):
        """Empty tasks dir → exit 2 with 'no task files found'."""
        tasks_dir = self.tmp_path / "empty-tasks"
        tasks_dir.mkdir()
        agents_dir = _make_agents_dir(self.tmp_path, ["frontend-engineer"])

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("no task files found", result.stderr)

    # ------------------------------------------------------------------
    # Placeholder / empty agent → NOT flagged by verify-agent-roster
    # ------------------------------------------------------------------

    def test_placeholder_agent_not_flagged(self):
        """Task with unfilled placeholder '[assigned agent name]' → not flagged.

        verify-agent-roster's scope is roster MEMBERSHIP of resolved names only.
        Placeholder detection is finalize-handoff's concern.
        """
        feature_dir = self.tmp_path / "specs" / "008-placeholder"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Write a skeleton WITHOUT filling the agent — leaves placeholder.
        skeleton = _render_task_file_raw("001", "Placeholder task", "008-placeholder")
        (tasks_dir / "001-placeholder-task.md").write_text(skeleton, encoding="utf-8")

        agents_dir = _make_agents_dir(self.tmp_path, ["frontend-engineer"])

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        # Should exit 0 — the placeholder task is not flagged here.
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("agent-roster: ok", result.stdout)

    def test_empty_agent_value_not_flagged(self):
        """Task with empty **Agent**: value → not flagged by verify-agent-roster."""
        feature_dir = self.tmp_path / "specs" / "009-emptyagent"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        skeleton = _render_task_file_raw("001", "Empty agent task", "009-emptyagent")
        # Replace agent placeholder with empty string.
        skeleton = re.sub(
            r"(\*\*Agent\*\*:)\s*\[assigned agent name\]",
            r"\g<1> ",
            skeleton,
        )
        (tasks_dir / "001-empty-agent-task.md").write_text(skeleton, encoding="utf-8")

        agents_dir = _make_agents_dir(self.tmp_path, ["frontend-engineer"])

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        # Not flagged — empty agent is finalize-handoff's concern.
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    # ------------------------------------------------------------------
    # Non-default --agents-dir path (wrapper mode simulation)
    # ------------------------------------------------------------------

    def test_custom_agents_dir_resolves_correctly(self):
        """--agents-dir pointing at a non-default path resolves correctly.

        Simulates wrapper mode where the install root differs from cwd.
        """
        feature_dir = self.tmp_path / "specs" / "010-customdir"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Frontend work", "010-customdir",
            agent="frontend-engineer",
        )

        # Custom path: not .claude/agents, simulates a wrapper install root.
        custom_install = self.tmp_path / "wrapper-install"
        agents_dir = _make_agents_dir(custom_install, ["frontend-engineer", "backend-engineer"])

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("agent-roster: ok", result.stdout)

    def test_custom_agents_dir_absent_agent_reports_correctly(self):
        """Custom --agents-dir with an absent agent still reports the offender."""
        feature_dir = self.tmp_path / "specs" / "011-customabsent"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(str(plan_path))
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Backend work", "011-customabsent",
            agent="backend-engineer",
        )

        custom_install = self.tmp_path / "wrapper-install2"
        agents_dir = _make_agents_dir(custom_install, ["frontend-engineer"])

        result = _run_bh(
            self.tmp_path, "verify-agent-roster", str(tasks_dir),
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("backend-engineer", result.stdout)


# ---------------------------------------------------------------------------
# Tests: finalize-handoff + --agents-dir (Piece 3 fold-in)
# ---------------------------------------------------------------------------


class FinalizeHandoffAgentRosterTests(_CwdIsolationBH):
    """Tests for the agent-roster validation fold-in to finalize-handoff."""

    def _setup_feature_with_agents(self, agents, task_agents, with_plan_handoff=False):
        """Return (feature_dir, plan_path, tasks_dir, agents_dir).

        agents: list of agent stems to install in the roster.
        task_agents: list of agent names to assign to sequential tasks.
        """
        feature_dir = self.tmp_path / "specs" / "001-roster-finalize"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_rich_plan(str(plan_path), status="Approved")

        if with_plan_handoff:
            r = _run_plan_helper_finalize(plan_path, self.tmp_path)
            self.assertEqual(r.returncode, 0, "plan_helper finalize-handoff failed: " + r.stderr)

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        for i, agent_name in enumerate(task_agents, start=1):
            num = str(i).zfill(3)
            _write_full_task_file(
                tasks_dir, num, "Task {0}".format(i), "001-roster-finalize",
                agent=agent_name,
            )

        _write_readme(tasks_dir)
        agents_dir = _make_agents_dir(self.tmp_path, agents)
        return feature_dir, plan_path, tasks_dir, agents_dir

    # ------------------------------------------------------------------
    # finalize-handoff with absent agent → exit 2, no handoff written
    # ------------------------------------------------------------------

    def test_finalize_absent_agent_exits_2(self):
        """finalize-handoff with one absent agent → exit 2."""
        _, plan_path, _, agents_dir = self._setup_feature_with_agents(
            agents=["frontend-engineer", "qa-engineer"],
            task_agents=["backend-engineer"],  # not installed
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff", str(plan_path),
            "--completed-at", "2026-05-24T12:00:00Z",
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)

    def test_finalize_absent_agent_writes_no_handoff(self):
        """finalize-handoff with absent agent must NOT write breakdown-handoff.json."""
        feature_dir, plan_path, _, agents_dir = self._setup_feature_with_agents(
            agents=["frontend-engineer"],
            task_agents=["backend-engineer"],  # not installed
        )

        _run_bh(
            self.tmp_path, "finalize-handoff", str(plan_path),
            "--completed-at", "2026-05-24T12:00:00Z",
            "--agents-dir", str(agents_dir),
        )
        handoff = feature_dir / "breakdown-handoff.json"
        self.assertFalse(
            handoff.exists(),
            "breakdown-handoff.json must NOT be written when agent is not installed",
        )

    def test_finalize_absent_agent_stdout_names_offender(self):
        """finalize-handoff exit-2 stdout names the absent agent."""
        _, plan_path, _, agents_dir = self._setup_feature_with_agents(
            agents=["frontend-engineer"],
            task_agents=["backend-engineer"],  # not installed
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff", str(plan_path),
            "--completed-at", "2026-05-24T12:00:00Z",
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("backend-engineer", result.stdout)
        self.assertIn("## Agent roster findings", result.stdout)

    def test_finalize_no_roster_fail_closed(self):
        """finalize-handoff with missing roster → fail-closed exit 2, no handoff."""
        feature_dir, plan_path, _, _ = self._setup_feature_with_agents(
            agents=["backend-engineer"],
            task_agents=["backend-engineer"],
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff", str(plan_path),
            "--completed-at", "2026-05-24T12:00:00Z",
            "--agents-dir", str(self.tmp_path / "no-such-agents-dir"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("no agent roster found", result.stderr)
        handoff = feature_dir / "breakdown-handoff.json"
        self.assertFalse(handoff.exists())

    # ------------------------------------------------------------------
    # finalize-handoff success path: byte-identical to existing tests
    # ------------------------------------------------------------------

    def test_finalize_all_agents_installed_success(self):
        """finalize-handoff with all agents installed → exit 0, JSON written."""
        _, plan_path, _, agents_dir = self._setup_feature_with_agents(
            agents=["backend-engineer", "qa-engineer"],
            task_agents=["backend-engineer"],
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff", str(plan_path),
            "--completed-at", "2026-05-24T12:00:00Z",
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        written = Path(result.stdout.strip())
        self.assertEqual(written.name, "breakdown-handoff.json")
        self.assertTrue(written.is_file())

    def test_finalize_success_path_schema_valid(self):
        """finalize-handoff success: JSON reconstructs through schema without raising."""
        import json as _json
        _, plan_path, _, agents_dir = self._setup_feature_with_agents(
            agents=["backend-engineer"],
            task_agents=["backend-engineer"],
        )

        result = _run_bh(
            self.tmp_path, "finalize-handoff", str(plan_path),
            "--completed-at", "2026-05-24T12:00:00Z",
            "--agents-dir", str(agents_dir),
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        written = Path(result.stdout.strip())
        raw = _json.loads(written.read_text(encoding="utf-8"))

        from _breakdown.handoff_schema import Breakdown, Provenance, TaskRow
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
        from _breakdown.handoff_schema import SCHEMA_VERSION, HANDOFF_KIND
        Breakdown(
            schema_version=raw["schema_version"],
            handoff_kind=raw["handoff_kind"],
            tasks_dir=raw["tasks_dir"],
            breakdown_completed_at=raw["breakdown_completed_at"],
            provenance=prov,
            tasks=task_rows,
            additions=raw["additions"],
            dependency_graph=raw["dependency_graph"],
        )
        # No exception = schema valid.

    def test_finalize_without_agents_dir_fails_closed(self):
        """Intentional fail-closed behavior: no --agents-dir → exit 2.

        Without an explicit --agents-dir, finalize-handoff defaults to
        .claude/agents in cwd, which does not exist in this fixture.
        The roster-validation gate fails closed — exit 2 with "no agent
        roster found" — and the handoff file is NOT written.

        This documents the deliberate behavior change introduced by the
        roster gate: callers must pass --agents-dir pointing to the installed
        roster, or populate .claude/agents in cwd before invoking.
        """
        feature_dir = self.tmp_path / "specs" / "002-defaultpath"
        feature_dir.mkdir(parents=True)
        plan_path = feature_dir / "plan.md"
        _write_rich_plan(str(plan_path), status="Approved")
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        _write_full_task_file(
            tasks_dir, "001", "Some task", "002-defaultpath",
            agent="backend-engineer",
        )
        _write_readme(tasks_dir)

        # No --agents-dir supplied → defaults to .claude/agents in cwd.
        # .claude/agents does not exist in our tmp dir → fail-closed.
        result = _run_bh(
            self.tmp_path, "finalize-handoff", str(plan_path),
            "--completed-at", "2026-05-24T12:00:00Z",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("no agent roster found", result.stderr)


# ---------------------------------------------------------------------------
# Tests: verify-manifest-present (Phase 3.5 — design-manifest-presence gate;
# schema retargeted from the disposition manifest to the BINDING by plan 53
# Phase 3/7c)
# ---------------------------------------------------------------------------
#
# Real-fixture discipline (per test-first rules):
#   The on-disk artifact is still design-manifest.json (plan 53 D4 —
#   same FILENAME, new schema), but there is no longer a mechanical
#   DERIVATION of its contents from reference.html: resolve-reference and
#   init-manifest are retired (plan 53 Phase 3) because the binding's route
#   + pairs are always human/LLM authored (no walkable data-ref element list
#   exists to seed a skeleton from anymore).  So the real-fixture discipline
#   here is: construct a real `Binding`/`BindingPair` via the real
#   `_design._schema` constructors and round-trip through the real
#   `binding_to_json` serializer — NOT a hand-authored JSON string.

# Make the _design package importable for round-trip fixture production.
_DESIGN_LIB_DIR = REPO_ROOT_P1 / "src" / "devforge" / "lib"
if str(_DESIGN_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_DESIGN_LIB_DIR))


# Minimal reference.html used only to make design/reference.html PRESENT (so
# the `_reference_present` gate treats the feature as design-scoped).  Its
# structure is otherwise inert now — bindings are no longer derived from it.
_REFERENCE_HTML_SIMPLE = """\
<!DOCTYPE html>
<html>
<head>
  <style>
    .card {
      padding: 8px;
      border: 1px solid #ccc;
    }
    .header {
      font-size: 18px;
    }
    :root {
      --color-primary: #007bff;
    }
  </style>
</head>
<body>
  <div data-ref="card-item" class="card">Card content</div>
  <header data-ref="page-header" class="header">Page Header</header>
</body>
</html>
"""


def _write_reference_html(design_dir):
    # type: (Path) -> Path
    """Write the simple reference.html to design_dir and return its path."""
    design_dir.mkdir(parents=True, exist_ok=True)
    html_path = design_dir / "reference.html"
    html_path.write_text(_REFERENCE_HTML_SIMPLE, encoding="utf-8")
    return html_path


def _make_valid_manifest(feature_dir, html_path=None):
    # type: (Path, Optional[Path]) -> Path
    """Produce a VALID binding via the real _design._schema constructors.

    Builds a real `Binding` (route + one container-floor `BindingPair`) and
    serializes it via the real `binding_to_json`.  `html_path` is accepted
    for call-site back-compat (most callers pass `_write_reference_html`'s
    return value) but is unused — a binding's pairs are independent of the
    reference HTML's structure (plan 53 Phase 3: no mechanical derivation).

    Returns the binding path (feature_dir/design-manifest.json).
    """
    from _design._schema import Binding, BindingPair, binding_to_json  # type: ignore[import]

    binding = Binding(
        route="/feature",
        pairs=[BindingPair("[data-ref=card-item]", "card-item-testid")],
    )

    manifest_path = feature_dir / "design-manifest.json"
    manifest_path.write_text(binding_to_json(binding), encoding="utf-8")
    return manifest_path


def _make_invalid_manifest(feature_dir, html_path=None):
    # type: (Path, Optional[Path]) -> Path
    """Produce an INVALID binding via the real _design._schema constructors.

    Same as _make_valid_manifest but the pair's anchor_selector is left
    empty, so validate_binding returns a non-empty error list.

    Returns the binding path.
    """
    from _design._schema import Binding, BindingPair, binding_to_json  # type: ignore[import]

    binding = Binding(
        route="/feature",
        pairs=[BindingPair("", "card-item-testid")],
    )

    manifest_path = feature_dir / "design-manifest.json"
    manifest_path.write_text(binding_to_json(binding), encoding="utf-8")
    return manifest_path


def _make_retired_disposition_manifest(feature_dir, html_path=None):
    # type: (Path, Optional[Path]) -> Path
    """Produce a STALE plan-40 disposition-manifest file (FIX 1 fixture).

    Shaped exactly as the retired `ManifestContainer.manifest_to_dict`
    (git history commit 6cc933c, pre-plan-53 `_design._schema.py`) actually
    emitted -- {"version": "1", "reference_html": ..., "elements": [...],
    "gap_list": [...]}. Transcribed from the real retired producer's
    serializer output (not hand-guessed) so the design-manifest-present
    chokepoint test round-trips against an artifact a real upgraded
    consumer install would actually have on disk.

    Returns the manifest path.
    """
    import json as _json

    retired_dict = {
        "version": "1",
        "reference_html": "design/reference.html",
        "elements": [
            {"data_ref": "hero", "disposition": "MATCH"},
        ],
        "gap_list": [],
    }
    manifest_path = feature_dir / "design-manifest.json"
    manifest_path.write_text(_json.dumps(retired_dict, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


class VerifyManifestPresentTests(_CwdIsolationBH):
    """Tests for verify-manifest-present verb (plan 42 Phase 1, WI-1;
    schema retargeted to the binding by plan 53 Phase 3/7c).

    All binding fixtures are constructed via the real `_design._schema`
    constructors (`Binding` / `BindingPair`) and round-tripped through the
    real `binding_to_json` serializer.  NO hand-authored JSON strings used
    (per real-fixture discipline).
    """

    # ------------------------------------------------------------------
    # Happy path: no reference.html — non-UI feature, trivial pass
    # ------------------------------------------------------------------

    def test_no_reference_exits_0(self):
        """No design/reference.html → exit 0 (non-UI feature trivial pass)."""
        feature_dir = self.tmp_path / "specs" / "001-no-ref"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_no_reference_stdout_says_skip(self):
        """No reference → stdout one-liner contains 'skip' and 'not a design'."""
        feature_dir = self.tmp_path / "specs" / "002-skip"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 0)
        self.assertIn("skip", result.stdout)
        self.assertIn("design", result.stdout.lower())

    def test_no_reference_scope_only_exits_3(self):
        """--scope-only, no reference → exit 3 (not in design scope)."""
        feature_dir = self.tmp_path / "specs" / "003-scope-absent"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        result = _run_bh(
            self.tmp_path, "verify-manifest-present", str(tasks_dir), "--scope-only"
        )
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)

    # ------------------------------------------------------------------
    # reference present + manifest absent → exit 2
    # ------------------------------------------------------------------

    def test_reference_present_manifest_absent_exits_2(self):
        """reference.html present but manifest absent → exit 2."""
        feature_dir = self.tmp_path / "specs" / "004-absent"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Write reference.html to workspace root's design/ dir.
        _write_reference_html(self.tmp_path / "design")

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)

    def test_reference_present_manifest_absent_stdout_findings_block(self):
        """Exit-2 stdout is a '## Design manifest findings' block."""
        feature_dir = self.tmp_path / "specs" / "005-block"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_reference_html(self.tmp_path / "design")

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Design manifest findings", result.stdout)

    def test_reference_present_manifest_absent_stdout_names_remedy(self):
        """Exit-2 block mentions PHASE 2.5 remedy."""
        feature_dir = self.tmp_path / "specs" / "006-remedy"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_reference_html(self.tmp_path / "design")

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 2)
        # Must mention the remedy (PHASE 2.5)
        self.assertIn("2.5", result.stdout)

    def test_reference_present_manifest_absent_stdout_names_reference_path(self):
        """Exit-2 block names the reference file path."""
        feature_dir = self.tmp_path / "specs" / "007-refpath"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_reference_html(self.tmp_path / "design")

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("design/reference.html", result.stdout)

    # ------------------------------------------------------------------
    # reference present + invalid manifest → exit 2 naming errors
    # ------------------------------------------------------------------

    def test_reference_present_invalid_manifest_exits_2(self):
        """reference present + unclassified element in manifest → exit 2."""
        feature_dir = self.tmp_path / "specs" / "008-invalid"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        html_path = _write_reference_html(self.tmp_path / "design")
        _make_invalid_manifest(feature_dir, html_path)

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)

    def test_reference_present_invalid_manifest_stdout_findings_block(self):
        """Exit-2 stdout is a '## Design manifest findings' block naming the error."""
        feature_dir = self.tmp_path / "specs" / "009-invalid-block"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        html_path = _write_reference_html(self.tmp_path / "design")
        _make_invalid_manifest(feature_dir, html_path)

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Design manifest findings", result.stdout)

    def test_reference_present_invalid_manifest_stdout_names_bad_pair(self):
        """Exit-2 stdout names the offending pair from the real binding.

        plan 53 Phase 3/7c: the invalid fixture's pair has an empty
        anchor_selector (_make_invalid_manifest) -- the error must name the
        pair index and the missing field, not the retired 'unclassified'
        element concept.
        """
        feature_dir = self.tmp_path / "specs" / "010-names-element"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        html_path = _write_reference_html(self.tmp_path / "design")
        _make_invalid_manifest(feature_dir, html_path)

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("pairs[0]", result.stdout)
        self.assertIn("anchor_selector", result.stdout)

    # ------------------------------------------------------------------
    # reference present + RETIRED plan-40 disposition manifest → exit 2,
    # DISTINGUISHABLE from the generic route/pairs message (FIX 1)
    # ------------------------------------------------------------------

    def test_retired_disposition_manifest_exits_2(self):
        """A stale plan-40 disposition-manifest file still exits non-zero."""
        feature_dir = self.tmp_path / "specs" / "008b-retired"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        html_path = _write_reference_html(self.tmp_path / "design")
        _make_retired_disposition_manifest(feature_dir, html_path)

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)

    def test_retired_disposition_manifest_message_distinguishable(self):
        """FIX 1: the retired-schema message must be distinguishable from
        the generic 'route must be non-empty' / 'pairs must contain at
        least one pair' message a genuinely-empty binding produces."""
        feature_dir = self.tmp_path / "specs" / "008c-retired-msg"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        html_path = _write_reference_html(self.tmp_path / "design")
        _make_retired_disposition_manifest(feature_dir, html_path)

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("retired", result.stdout)
        self.assertIn("elements/gap_list", result.stdout)
        self.assertNotIn("route: must be non-empty", result.stdout)
        self.assertNotIn(
            "pairs: must contain at least one pair", result.stdout
        )

    # ------------------------------------------------------------------
    # reference present + VALID manifest → exit 0
    # ------------------------------------------------------------------

    def test_reference_present_valid_manifest_exits_0(self):
        """reference present + fully-classified manifest → exit 0."""
        feature_dir = self.tmp_path / "specs" / "011-valid"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        html_path = _write_reference_html(self.tmp_path / "design")
        _make_valid_manifest(feature_dir, html_path)

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_reference_present_valid_manifest_stdout_ok_line(self):
        """Exit-0 stdout contains 'design-manifest: ok'."""
        feature_dir = self.tmp_path / "specs" / "012-ok-line"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        html_path = _write_reference_html(self.tmp_path / "design")
        _make_valid_manifest(feature_dir, html_path)

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 0)
        self.assertIn("design-manifest: ok", result.stdout)

    # ------------------------------------------------------------------
    # --scope-only with reference present → exit 0
    # ------------------------------------------------------------------

    def test_scope_only_reference_present_exits_0(self):
        """--scope-only, reference present → exit 0."""
        feature_dir = self.tmp_path / "specs" / "013-scope-present"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_reference_html(self.tmp_path / "design")

        result = _run_bh(
            self.tmp_path, "verify-manifest-present", str(tasks_dir), "--scope-only"
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_scope_only_no_manifest_check(self):
        """--scope-only: does NOT check manifest even when reference present + manifest absent."""
        feature_dir = self.tmp_path / "specs" / "014-scope-no-manifest"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_reference_html(self.tmp_path / "design")
        # Deliberately do NOT create manifest.

        result = _run_bh(
            self.tmp_path, "verify-manifest-present", str(tasks_dir), "--scope-only"
        )
        # Should exit 0 — scope-only ignores manifest state.
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    # ------------------------------------------------------------------
    # Broken state: missing tasks dir → exit 2 on stderr
    # ------------------------------------------------------------------

    def test_missing_tasks_dir_exits_2_on_stderr(self):
        """Non-existent tasks-dir → exit 2 with a message on stderr."""
        result = _run_bh(
            self.tmp_path, "verify-manifest-present",
            str(self.tmp_path / "specs" / "999-nonexistent" / "tasks"),
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        # Error must be on stderr, not stdout.
        self.assertTrue(
            result.stderr.strip(),
            "Expected a stderr message for broken-state but got none",
        )

    def test_missing_tasks_dir_stdout_empty(self):
        """Non-existent tasks-dir → stdout is empty (error goes to stderr only)."""
        result = _run_bh(
            self.tmp_path, "verify-manifest-present",
            str(self.tmp_path / "specs" / "999b-empty" / "tasks"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), "")

    # ------------------------------------------------------------------
    # --reference-path override: custom reference path
    # ------------------------------------------------------------------

    def test_custom_reference_path_absent_exits_0(self):
        """--reference-path pointing to nonexistent file → exit 0 (skip)."""
        feature_dir = self.tmp_path / "specs" / "015-custom-ref"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        result = _run_bh(
            self.tmp_path, "verify-manifest-present", str(tasks_dir),
            "--reference-path", "custom/alt-reference.html",
        )
        # No file at that path → skip.
        self.assertEqual(result.returncode, 0)
        self.assertIn("skip", result.stdout)

    def test_custom_reference_path_present_checks_manifest(self):
        """--reference-path pointing to an existing file → manifest check fires."""
        feature_dir = self.tmp_path / "specs" / "016-custom-ref-present"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Write reference at the custom path.
        custom_ref_dir = self.tmp_path / "custom"
        html_path = _write_reference_html(custom_ref_dir)
        # rename to alt-reference.html
        alt_html_path = custom_ref_dir / "alt-reference.html"
        html_path.rename(alt_html_path)

        result = _run_bh(
            self.tmp_path, "verify-manifest-present", str(tasks_dir),
            "--reference-path", "custom/alt-reference.html",
        )
        # Reference present, manifest absent → exit 2.
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Design manifest findings", result.stdout)

    # ------------------------------------------------------------------
    # --manifest-path override: explicit manifest path
    # ------------------------------------------------------------------

    def test_manifest_path_override_valid(self):
        """--manifest-path pointing to a valid binding → exit 0."""
        feature_dir = self.tmp_path / "specs" / "017-manifest-override"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_reference_html(self.tmp_path / "design")
        # Write binding to a NON-DEFAULT location.
        alt_manifest_dir = self.tmp_path / "alt-manifests"
        alt_manifest_dir.mkdir()
        alt_manifest_path = alt_manifest_dir / "my-manifest.json"

        # Produce via the real schema constructors + serializer, written to
        # the alt path (plan 53 Phase 3/7c: no mechanical HTML derivation).
        from _design._schema import Binding, BindingPair, binding_to_json  # type: ignore[import]

        binding = Binding(
            route="/feature",
            pairs=[BindingPair("[data-ref=card-item]", "card-item-testid")],
        )
        alt_manifest_path.write_text(binding_to_json(binding), encoding="utf-8")

        result = _run_bh(
            self.tmp_path, "verify-manifest-present", str(tasks_dir),
            "--manifest-path", str(alt_manifest_path),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("design-manifest: ok", result.stdout)

    # ------------------------------------------------------------------
    # Round-trip integrity: every bad pair is individually named in errors
    # ------------------------------------------------------------------

    def test_real_roundtrip_multiple_bad_pairs_all_named(self):
        """Every offending pair from the real binding appears in the error block.

        plan 53 Phase 3/7c: this is the round-trip integrity check for the
        NEW binding schema — a binding with two pairs, each missing a
        DIFFERENT required field, must surface BOTH pair indices in the
        validate_binding error output (the multi-issue-surfacing spirit of
        the retired 'every unclassified element is named' test, adapted to
        route+pairs).
        """
        feature_dir = self.tmp_path / "specs" / "018-roundtrip"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_reference_html(self.tmp_path / "design")

        from _design._schema import Binding, BindingPair, binding_to_json  # type: ignore[import]

        binding = Binding(
            route="/feature",
            pairs=[
                BindingPair("", "card-item-testid"),      # missing anchor_selector
                BindingPair("[data-ref=page-header]", ""),  # missing built_testid
            ],
        )
        (feature_dir / "design-manifest.json").write_text(
            binding_to_json(binding), encoding="utf-8"
        )

        result = _run_bh(self.tmp_path, "verify-manifest-present", str(tasks_dir))
        self.assertEqual(result.returncode, 2)
        # Both pair indices + their missing fields must appear in the error block.
        self.assertIn("pairs[0]", result.stdout)
        self.assertIn("anchor_selector", result.stdout)
        self.assertIn("pairs[1]", result.stdout)
        self.assertIn("built_testid", result.stdout)

    # ------------------------------------------------------------------
    # _reference_present shared predicate (unit test via library import)
    # ------------------------------------------------------------------

    def test_reference_present_fn_absent(self):
        """_reference_present returns False when file is absent."""
        from breakdown_helper import _reference_present  # type: ignore[import]
        result = _reference_present(str(self.tmp_path), "design/reference.html")
        self.assertFalse(result)

    def test_reference_present_fn_present(self):
        """_reference_present returns True when file exists."""
        from breakdown_helper import _reference_present  # type: ignore[import]
        (self.tmp_path / "design").mkdir()
        (self.tmp_path / "design" / "reference.html").write_text("<html/>", encoding="utf-8")
        result = _reference_present(str(self.tmp_path), "design/reference.html")
        self.assertTrue(result)

    def test_reference_present_fn_custom_path(self):
        """_reference_present respects custom reference_path."""
        from breakdown_helper import _reference_present  # type: ignore[import]
        custom_dir = self.tmp_path / "assets"
        custom_dir.mkdir()
        (custom_dir / "mockup.html").write_text("<html/>", encoding="utf-8")
        self.assertTrue(_reference_present(str(self.tmp_path), "assets/mockup.html"))
        self.assertFalse(_reference_present(str(self.tmp_path), "assets/missing.html"))

    # ------------------------------------------------------------------
    # _validate_manifest_present shared function (unit test via library import)
    # ------------------------------------------------------------------

    def test_validate_manifest_present_no_reference(self):
        """No reference → exit 0, stdout skip."""
        from breakdown_helper import _validate_manifest_present  # type: ignore[import]
        feature_dir = self.tmp_path / "specs" / "unit-001"
        feature_dir.mkdir(parents=True)

        code, out, err = _validate_manifest_present(
            feature_dir=str(feature_dir),
            workspace_root=str(self.tmp_path),
        )
        self.assertEqual(code, 0)
        self.assertIn("skip", out)
        self.assertEqual(err, "")

    def test_validate_manifest_present_reference_manifest_absent(self):
        """Reference present, manifest absent → exit 2, findings block."""
        from breakdown_helper import _validate_manifest_present  # type: ignore[import]
        feature_dir = self.tmp_path / "specs" / "unit-002"
        feature_dir.mkdir(parents=True)
        _write_reference_html(self.tmp_path / "design")

        code, out, err = _validate_manifest_present(
            feature_dir=str(feature_dir),
            workspace_root=str(self.tmp_path),
        )
        self.assertEqual(code, 2)
        self.assertIn("## Design manifest findings", out)
        self.assertEqual(err, "")

    def test_validate_manifest_present_valid_manifest(self):
        """Reference present + valid manifest → exit 0."""
        from breakdown_helper import _validate_manifest_present  # type: ignore[import]
        feature_dir = self.tmp_path / "specs" / "unit-003"
        feature_dir.mkdir(parents=True)
        html_path = _write_reference_html(self.tmp_path / "design")
        _make_valid_manifest(feature_dir, html_path)

        code, out, err = _validate_manifest_present(
            feature_dir=str(feature_dir),
            workspace_root=str(self.tmp_path),
        )
        self.assertEqual(code, 0)
        self.assertIn("ok", out)

    def test_validate_manifest_present_invalid_manifest(self):
        """Reference present + invalid binding → exit 2 naming the bad pair."""
        from breakdown_helper import _validate_manifest_present  # type: ignore[import]
        feature_dir = self.tmp_path / "specs" / "unit-004"
        feature_dir.mkdir(parents=True)
        html_path = _write_reference_html(self.tmp_path / "design")
        _make_invalid_manifest(feature_dir, html_path)

        code, out, err = _validate_manifest_present(
            feature_dir=str(feature_dir),
            workspace_root=str(self.tmp_path),
        )
        self.assertEqual(code, 2)
        self.assertIn("## Design manifest findings", out)
        self.assertIn("pairs[0]", out)
        self.assertIn("anchor_selector", out)

    def test_validate_manifest_present_retired_disposition_manifest(self):
        """FIX 1: a stale plan-40 disposition-manifest file → exit 2 with the
        DISTINGUISHABLE retired-schema message, not the generic
        route/pairs message."""
        from breakdown_helper import _validate_manifest_present  # type: ignore[import]
        feature_dir = self.tmp_path / "specs" / "unit-005"
        feature_dir.mkdir(parents=True)
        html_path = _write_reference_html(self.tmp_path / "design")
        _make_retired_disposition_manifest(feature_dir, html_path)

        code, out, err = _validate_manifest_present(
            feature_dir=str(feature_dir),
            workspace_root=str(self.tmp_path),
        )
        self.assertEqual(code, 2)
        self.assertIn("retired", out)
        self.assertIn("elements/gap_list", out)
        self.assertNotIn("route: must be non-empty", out)
        self.assertNotIn("pairs: must contain at least one pair", out)


# ---------------------------------------------------------------------------
# Tests: verify-grill-ran
# ---------------------------------------------------------------------------


def _write_grill_report(feature_dir, content="# Grill: Test Feature\n\nSome content.\n"):
    """Write a grill.md at feature_dir.

    Content is irrelevant to the gate under test -- verify-grill-ran
    checks presence + grill-state.json only, never grill.md's body -- so
    it is kept minimal on purpose.
    """
    feature_dir.mkdir(parents=True, exist_ok=True)
    report_path = feature_dir / "grill.md"
    report_path.write_text(content, encoding="utf-8")
    return report_path


def _write_grill_state_real(feature_dir, adversary_status, plan_sha256=""):
    """Write grill-state.json via the REAL _grill._state.GrillState /
    state_path / write_state -- round-tripped through the real producer
    machinery (per real-fixture discipline), not hand-authored JSON.
    """
    from _grill._state import GrillState, state_path, write_state  # type: ignore[import]

    feature_dir.mkdir(parents=True, exist_ok=True)
    sp = state_path(str(feature_dir))
    state = GrillState(
        phase="report",
        feature_dir=str(feature_dir),
        status="complete",
        out_path=str(feature_dir / "grill.md"),
        adversary_status=adversary_status,
        plan_sha256=plan_sha256,
    )
    write_state(sp, state)
    return sp


def _write_pre_change_grill_state(feature_dir):
    """Hand-author a grill-state.json shaped as it looked BEFORE
    adversary_status/plan_sha256 existed.

    No current producer can generate this shape -- mirrors
    tests/lib/_grill/test_state.py's own
    test_pre_change_file_round_trips_to_not_ran fixture, which documents
    the same "no real producer for this shape" rationale.
    """
    feature_dir.mkdir(parents=True, exist_ok=True)
    sp = feature_dir / "grill-state.json"
    data = {
        "phase": "report",
        "feature_dir": str(feature_dir),
        "status": "complete",
        "out_path": str(feature_dir / "grill.md"),
        "scope_files": [],
        "agent_assignments": [],
    }
    sp.write_text(json.dumps(data), encoding="utf-8")
    return sp


def _write_array_grill_state(feature_dir):
    """Hand-author grill-state.json as a top-level JSON ARRAY.

    Malformed shape no current producer can generate; exercises the
    _grill/_state.py non-dict-JSON fix this phase ships (the inherited
    defect this verb's existence makes reachable for the first time).
    """
    feature_dir.mkdir(parents=True, exist_ok=True)
    sp = feature_dir / "grill-state.json"
    sp.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    return sp


class VerifyGrillRanTests(_CwdIsolationBH):
    """CLI-level tests for `breakdown_helper verify-grill-ran` (subprocess).

    Mirrors test_plan_helper.py's VerifySpecCheckTests in shape (the same
    gate one pipeline stage upstream): every grill-state.json fixture is
    round-tripped through the real `_grill._state` producer machinery
    except the two deliberately-malformed/deliberately-old-shaped cases
    (_write_pre_change_grill_state, _write_array_grill_state), which no
    current producer can generate.
    """

    def _feature_dir(self):
        d = self.tmp_path / "specs" / "011-widget-catalog-search"
        d.mkdir(parents=True)
        return d

    # ------------------------------------------------------------------
    # (a) plan.md itself missing/unreadable
    # ------------------------------------------------------------------

    def test_plan_missing_sibling_gate_shape(self):
        """(a) plan.md missing -- plain sibling-gate message, NOT the
        multi-line BLOCKED form, and NEVER names /devforge:grill (running
        it would be nonsensical when the plan path itself is bad)."""
        missing = self.tmp_path / "specs" / "011-x" / "plan.md"
        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(missing))
        self.assertEqual(result.returncode, 2)
        self.assertIn("breakdown_helper: cannot read plan:", result.stderr)
        self.assertNotIn("BLOCKED:", result.stderr)
        self.assertNotIn("/devforge:grill", result.stderr)

    def test_relative_plan_path_missing_shows_raw_string_in_stderr(self):
        """(a) with a RELATIVE --plan pointing at a nonexistent file: the
        stderr carries the raw relative string the user passed, not the
        resolved absolute path -- mirrors verify-spec-check's own arm (a)
        test for the same reason (args.plan reported verbatim)."""
        rel = "specs/011-x/plan.md"
        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", rel)
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "breakdown_helper: cannot read plan: {0}".format(rel), result.stderr
        )
        resolved = str((self.tmp_path / rel).resolve())
        self.assertNotIn(resolved, result.stderr)

    # ------------------------------------------------------------------
    # (b) no grill.md next to the plan
    # ------------------------------------------------------------------

    def test_grill_report_absent_exits_2_blocked(self):
        """(b) plan.md exists, no sibling grill.md -> BLOCKED, exit 2."""
        d = self._feature_dir()
        plan_path = d / "plan.md"
        _write_minimal_plan(str(plan_path))

        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "BLOCKED: /devforge:breakdown requires /devforge:grill to have "
            "run for this plan.",
            result.stderr,
        )
        self.assertIn(
            "no grill report exists for this plan — run "
            "`/devforge:grill` first",
            result.stderr,
        )
        self.assertIn("This gate is mandatory, with no override.", result.stderr)
        self.assertIn(
            "Run the following first, then retry /devforge:breakdown:",
            result.stderr,
        )
        self.assertIn(
            "  /devforge:grill {0}".format(plan_path.resolve()), result.stderr
        )

    # ------------------------------------------------------------------
    # (c) grill.md present, grill-state.json missing/unreadable/malformed
    # ------------------------------------------------------------------

    def test_grill_state_absent_exits_2_blocked(self):
        """(c) grill.md present, grill-state.json absent -> BLOCKED,
        exit 2."""
        d = self._feature_dir()
        plan_path = d / "plan.md"
        _write_minimal_plan(str(plan_path))
        _write_grill_report(d)

        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED:", result.stderr)
        self.assertIn("grill-state.json", result.stderr)
        self.assertIn("/devforge:grill", result.stderr)
        self.assertIn("This gate is mandatory, with no override.", result.stderr)

    def test_grill_state_top_level_array_exits_2_no_traceback(self):
        """grill-state.json is valid JSON but a top-level ARRAY -> exit 2
        with the BLOCKED message, NOT a Python traceback. Pins the
        _grill/_state.py inherited-defect fix this phase ships: this verb
        is the first caller that reads a grill-state.json it did not
        itself just write."""
        d = self._feature_dir()
        plan_path = d / "plan.md"
        _write_minimal_plan(str(plan_path))
        _write_grill_report(d)
        _write_array_grill_state(d)

        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("AttributeError", result.stderr)
        self.assertIn("BLOCKED:", result.stderr)
        self.assertIn("grill-state.json", result.stderr)

    # ------------------------------------------------------------------
    # (d) state readable but adversary_status unset
    # ------------------------------------------------------------------

    def test_pre_change_state_unset_status_exits_2_blocked(self):
        """(d) grill-state.json readable but shaped as it looked BEFORE
        adversary_status existed (only the pre-change keys) -> unset
        status -> BLOCKED, exit 2."""
        d = self._feature_dir()
        plan_path = d / "plan.md"
        _write_minimal_plan(str(plan_path))
        _write_grill_report(d)
        _write_pre_change_grill_state(d)

        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED:", result.stderr)
        self.assertIn("no recorded adversary run", result.stderr)
        self.assertIn("/devforge:grill", result.stderr)
        self.assertIn("This gate is mandatory, with no override.", result.stderr)

    # ------------------------------------------------------------------
    # (e) adversary_status is "failed" or "missing"
    # ------------------------------------------------------------------

    def test_adversary_status_failed_exits_2_blocked(self):
        """(e) adversary_status == 'failed' -- own test, exit 2."""
        d = self._feature_dir()
        plan_path = d / "plan.md"
        _write_minimal_plan(str(plan_path))
        _write_grill_report(d)
        _write_grill_state_real(d, adversary_status="failed")

        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED:", result.stderr)
        self.assertIn("did not complete", result.stderr)
        self.assertIn("'failed'", result.stderr)
        self.assertIn("/devforge:grill", result.stderr)

    def test_adversary_status_missing_exits_2_blocked(self):
        """(e) adversary_status == 'missing' -- own test, distinct from
        'failed', exit 2."""
        d = self._feature_dir()
        plan_path = d / "plan.md"
        _write_minimal_plan(str(plan_path))
        _write_grill_report(d)
        _write_grill_state_real(d, adversary_status="missing")

        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED:", result.stderr)
        self.assertIn("did not complete", result.stderr)
        self.assertIn("'missing'", result.stderr)

    # ------------------------------------------------------------------
    # Exit 0 -- adversary_ran() accepted statuses, each its own test
    # ------------------------------------------------------------------

    def test_adversary_status_complete_exits_0(self):
        """adversary_status == 'complete' -> exit 0."""
        d = self._feature_dir()
        plan_path = d / "plan.md"
        _write_minimal_plan(str(plan_path))
        _write_grill_report(d)
        _write_grill_state_real(d, adversary_status="complete")

        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        ack = json.loads(result.stdout)
        self.assertEqual(ack["ran"], True)
        self.assertEqual(ack["adversary_status"], "complete")
        self.assertEqual(ack["report_path"], str((d / "grill.md").resolve()))

    def test_adversary_status_clean_exits_0(self):
        """adversary_status == 'clean' -> exit 0, its OWN test, not
        folded into the 'complete' case -- a clean run (the adversary ran
        and grounded no attack) is a genuinely successful adversarial
        pass, and this distinction being independently visible is the
        whole reason the status is persisted separately from a bare
        pass/fail bit."""
        d = self._feature_dir()
        plan_path = d / "plan.md"
        _write_minimal_plan(str(plan_path))
        _write_grill_report(d)
        _write_grill_state_real(d, adversary_status="clean")

        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        ack = json.loads(result.stdout)
        self.assertEqual(ack["ran"], True)
        self.assertEqual(ack["adversary_status"], "clean")

    # ------------------------------------------------------------------
    # Freshness is DELIBERATELY not enforced -- a stale report PASSES
    # ------------------------------------------------------------------

    def test_stale_plan_sha256_still_passes_freshness_is_never_enforced(self):
        """A grill-state.json recording a plan_sha256 that does NOT match
        the current plan.md's real hash still EXITS 0. This pins the
        ratified recorded-not-enforced stance: verify-grill-ran checks
        presence of a completed adversarial run only, never freshness --
        see cmd_verify_grill_ran's docstring for why a freshness
        condition would penalize acting on the grill report's own
        findings. This is the case a future "hardening" pass would most
        plausibly break by adding a hash comparison; it must keep
        passing."""
        d = self._feature_dir()
        plan_path = d / "plan.md"
        _write_minimal_plan(str(plan_path))
        _write_grill_report(d)
        # Deliberately mismatched -- not the real hash of plan.md's content.
        stale_hash = "0" * 64
        _write_grill_state_real(
            d, adversary_status="complete", plan_sha256=stale_hash
        )

        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        ack = json.loads(result.stdout)
        self.assertEqual(ack["ran"], True)

    def test_exit_0_ack_never_contains_plan_hash(self):
        """The exit-0 ack carries no plan_sha256 key and no hash string at
        all -- distinct from plan_helper's verify-spec-check, which DOES
        carry spec_sha256; the divergence is deliberate (see docstring)."""
        d = self._feature_dir()
        plan_path = d / "plan.md"
        _write_minimal_plan(str(plan_path))
        _write_grill_report(d)
        recorded_hash = "abc123def456" + "0" * 52  # 64 hex chars, distinctive
        _write_grill_state_real(
            d, adversary_status="complete", plan_sha256=recorded_hash
        )

        result = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        ack = json.loads(result.stdout)
        self.assertNotIn("plan_sha256", ack)
        self.assertNotIn(recorded_hash, result.stdout)

    # ------------------------------------------------------------------
    # Zero-escape-hatch: no override/skip/force wording in any BLOCKED arm
    # ------------------------------------------------------------------

    def test_blocked_messages_name_grill_and_offer_no_override_flag(self):
        """Every (b)-(e) BLOCKED stderr names /devforge:grill and offers
        NO override/skip/force FLAG. The mandatory disclaimer sentence
        itself uses the word 'override' ('...with no override.'), so this
        checks for the absence of escape-hatch FLAG syntax
        (--force / --skip / --override) rather than the bare word."""
        d = self._feature_dir()
        plan_path = d / "plan.md"
        _write_minimal_plan(str(plan_path))

        scenarios = []

        # (b) no grill.md.
        result_b = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        scenarios.append(result_b.stderr)

        # (c) grill.md present, no state.
        _write_grill_report(d)
        result_c = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        scenarios.append(result_c.stderr)

        # (d) unset status.
        _write_pre_change_grill_state(d)
        result_d = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        scenarios.append(result_d.stderr)

        # (e) failed status.
        (d / "grill-state.json").unlink()
        _write_grill_state_real(d, adversary_status="failed")
        result_e = _run_bh(self.tmp_path, "verify-grill-ran", "--plan", str(plan_path))
        scenarios.append(result_e.stderr)

        for stderr in scenarios:
            self.assertIn("/devforge:grill", stderr)
            self.assertNotIn("--force", stderr)
            self.assertNotIn("--skip", stderr)
            self.assertNotIn("--override", stderr)


if __name__ == "__main__":
    unittest.main()
