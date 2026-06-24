"""Tests for src/devforge/lib/_implement/_handoff_reader.py.

Coverage:
  read_breakdown_handoff:
    - Happy path: valid breakdown-handoff.json is parsed into Breakdown.
    - File not found raises ValueError.
    - Malformed JSON raises ValueError.
    - Wrong handoff_kind raises ValueError.
    - Missing 'tasks' key raises ValueError.
    - Non-dict root raises ValueError.
    - Provenance validation failure raises ValueError.
    - TaskRow validation failure raises ValueError.
    - Empty feature_dir (no file) raises ValueError.
    - Round-trip: real breakdown_helper finalize-handoff producer → reader
      validates resulting Breakdown is a proper schema instance.

  task_row:
    - Returns the matching TaskRow when the number exists.
    - Raises ValueError when the number does not exist.
    - Works with a Breakdown that has multiple tasks.

Real-producer test discipline:
  The round-trip test runs the REAL 'breakdown_helper finalize-handoff'
  subprocess to produce breakdown-handoff.json, then asserts that
  read_breakdown_handoff returns a valid Breakdown with the expected tasks.
  The fixture is NOT a hand-authored JSON blob -- it is produced by the
  real producer, ensuring schema fidelity.

  The schema-fixture tests (error paths) construct their inputs using the
  live _breakdown.handoff_schema dataclasses constants (HANDOFF_KIND,
  SCHEMA_VERSION) so any schema change breaks the tests immediately.

Stdlib only. Python 3.8+.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_BREAKDOWN_HELPER_PY = _LIB_DIR / "breakdown_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _implement._handoff_reader import read_breakdown_handoff, task_row  # noqa: E402
from _breakdown.handoff_schema import (  # noqa: E402
    Breakdown,
    TaskRow,
    Provenance,
    HANDOFF_KIND,
    SCHEMA_VERSION,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_minimal_task_dict(**overrides):
    """Return a dict representing a valid TaskRow JSON object."""
    defaults = dict(
        number="001",
        title="Define widget types",
        agent="backend-engineer",
        depends_on=[],
        blocks=[],
        touched_files=["src/widget.py"],
        expects=[],
        produces=["Widget dataclass defined in src/widget.py"],
        ac_addressed=["AC-1"],
        doc_refs=[],
        review_checkpoint=False,
    )
    defaults.update(overrides)
    return defaults


def _make_minimal_provenance_dict(**overrides):
    """Return a dict representing a valid Provenance JSON object."""
    defaults = dict(
        upstream_handoff_path=None,
        upstream_handoff_kind=None,
        plan_path=None,
        spec_path=None,
    )
    defaults.update(overrides)
    return defaults


def _make_valid_breakdown_dict(**overrides):
    """Return a dict representing a valid top-level breakdown-handoff JSON object.

    The dict uses constants from the live _breakdown.handoff_schema so any
    schema constant change breaks this fixture immediately.
    """
    defaults = dict(
        schema_version=SCHEMA_VERSION,
        handoff_kind=HANDOFF_KIND,
        tasks_dir="specs/001-widget/tasks",
        breakdown_completed_at="2026-06-01T12:00:00Z",
        provenance=_make_minimal_provenance_dict(),
        tasks=[_make_minimal_task_dict()],
        additions=[],
        dependency_graph="",
    )
    defaults.update(overrides)
    return defaults


def _write_breakdown_json(feature_dir, data):
    """Write a breakdown-handoff.json to feature_dir from a dict."""
    path = Path(feature_dir) / "breakdown-handoff.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Real-producer task and plan file fixtures for the round-trip test.
# ---------------------------------------------------------------------------

def _write_minimal_plan(path):
    """Write a minimal plan.md with frontmatter."""
    content = (
        "# Plan: Widget Catalog\n\n"
        "**Date**: 2026-06-01\n"
        "**Status**: Approved\n"
        "**Author**: Claude + User\n\n"
        "## Summary\n\nBuild widget catalog.\n\n"
        "### File Impact\n\n"
        "| File | Action | What Changes |\n"
        "|------|--------|---------------|\n"
        "| src/widget.py | Create | Widget dataclass |\n\n"
        "### Layer Map\n\n"
        "| Layer | What | Files |\n"
        "|-------|------|-------|\n"
        "| Domain | Widget types | src/widget.py |\n\n"
        "## Risk Assessment\n\n"
        "| Risk | Likelihood | Impact | Mitigation |\n"
        "|------|-----------|--------|------------|\n"
        "| Schema drift | Low | High | Pin versions |\n\n"
        "## Specialist Consultation\n\n"
        "| Specialist | Sub-question | Input summary | Verdict | Cites |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| (none) | — | — | — | — |\n\n"
        "## Dependencies\n\n"
        "- No external dependencies.\n"
    )
    Path(path).write_text(content, encoding="utf-8")


def _write_minimal_task_file(path, number="001", title="Define widget types",
                              agent="backend-engineer"):
    """Write a minimal task file conforming to the breakdown task format."""
    content = (
        "# Task {number}: {title}\n\n"
        "**Feature**: 001-widget-catalog\n"
        "**Agent**: {agent}\n"
        "**Status**: Pending\n"
        "**Depends on**: None\n"
        "**Blocks**: None\n"
        "**Spec criteria**: AC-1\n"
        "**Review checkpoint**: No\n"
        "**Context docs**: None\n\n"
        "## Files\n\n"
        "| File | Action | Description |\n"
        "|------|--------|-------------|\n"
        "| src/widget.py | Create | Widget dataclass |\n\n"
        "## Description\n\n"
        "Define the Widget dataclass.\n\n"
        "## Change Details\n\n"
        "- In `src/widget.py`:\n"
        "  - Add Widget dataclass\n\n"
        "## Contracts\n\n"
        "### Expects (checked before execution)\n"
        "- src/widget.py does not exist\n\n"
        "### Produces (checked after execution)\n"
        "- Widget dataclass is defined in src/widget.py\n\n"
        "## Done When\n\n"
        "- [ ] Widget dataclass exists\n"
        "- [ ] No debug artifacts left in changed files\n"
        "- [ ] Type checker passes on changed files (see Development Commands section)\n"
        "- [ ] Linter passes on changed files (see Development Commands section)\n"
        "- [ ] No new secrets or credentials in code\n\n"
        "## Completion Notes\n\n"
        "[Filled in by execute-task after completion]\n"
        "**Completed**: [date/time]\n"
        "**Files changed**: [actual files]\n"
        "**Contract**: Expects [X/Y verified] | Produces [X/Y verified]\n"
        "**Notes**: [deviations or observations]\n"
    ).format(number=number, title=title, agent=agent)
    Path(path).write_text(content, encoding="utf-8")


def _write_minimal_readme(path):
    """Write a minimal tasks/README.md with a dependency graph."""
    content = (
        "# Tasks: Widget Catalog\n\n"
        "**Spec**: specs/001-widget-catalog/spec.md\n"
        "**Plan**: specs/001-widget-catalog/plan.md\n"
        "**Generated**: 2026-06-01\n"
        "**Total tasks**: 1\n\n"
        "## Dependency Graph\n\n"
        "```\n"
        "001 (Define widget types)\n"
        "```\n\n"
        "## Task Index\n\n"
        "| # | Title | Agent | Depends on | Status |\n"
        "|---|-------|-------|-----------|--------|\n"
        "| 001 | Define widget types | backend-engineer | None | Pending |\n\n"
        "## Additions to Spec\n\n"
        "[Files or changes discovered that weren't in the original spec]\n\n"
        "## Risk Assessment\n\n"
        "| Task | Risk | Reason |\n"
        "|------|------|--------|\n"
        "| 001 | Low | Straightforward dataclass |\n\n"
        "## Review Checkpoints\n\n"
        "| Before Task | Reason | What to Review |\n"
        "|-------------|--------|----------------|\n"
        "| [NNN] | [convergence / layer crossing / high risk] | [what to verify before proceeding] |\n"
    )
    Path(path).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Helper: run breakdown_helper finalize-handoff as subprocess
# ---------------------------------------------------------------------------

def _ensure_agents_dir(tmp_dir, agent_stems=None):
    """Create .claude/agents/ in tmp_dir with stub *.md files for each stem.

    Satisfies breakdown_helper's roster-validation gate, which fails closed
    when no *.md agent files are present.
    """
    if agent_stems is None:
        agent_stems = ["backend-engineer", "frontend-engineer"]
    agents_dir = Path(tmp_dir) / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    for stem in agent_stems:
        stub = agents_dir / (stem + ".md")
        if not stub.exists():
            stub.write_text("# {0}\n".format(stem), encoding="utf-8")
    return agents_dir


def _run_finalize_handoff(tmp_dir, plan_path):
    """Run breakdown_helper finalize-handoff on the given plan.md.

    Returns the subprocess.CompletedProcess result.
    The breakdown-handoff.json is written as a sibling to plan.md by the helper.
    Creates a minimal .claude/agents/ roster so the new roster-validation gate
    (verify-agent-roster inside finalize-handoff) passes.
    """
    agents_dir = _ensure_agents_dir(tmp_dir)
    return subprocess.run(
        [
            sys.executable, str(_BREAKDOWN_HELPER_PY), "finalize-handoff",
            str(plan_path),
            "--agents-dir", str(agents_dir),
        ],
        cwd=str(tmp_dir),
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Test: read_breakdown_handoff -- happy path (schema-fixture approach)
# ---------------------------------------------------------------------------

class TestReadBreakdownHandoffHappyPath(unittest.TestCase):
    """Schema-fixture tests: build valid dicts using live schema constants."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_valid_breakdown_returns_Breakdown_instance(self):
        """Valid breakdown-handoff.json produces a Breakdown instance."""
        data = _make_valid_breakdown_dict()
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        result = read_breakdown_handoff(feature_dir)

        self.assertIsInstance(result, Breakdown)

    def test_handoff_kind_is_breakdown(self):
        """Returned Breakdown has handoff_kind == 'breakdown'."""
        data = _make_valid_breakdown_dict()
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        result = read_breakdown_handoff(feature_dir)
        self.assertEqual(result.handoff_kind, HANDOFF_KIND)

    def test_tasks_list_contains_TaskRow_instances(self):
        """tasks[] is a list of TaskRow instances."""
        data = _make_valid_breakdown_dict(
            tasks=[_make_minimal_task_dict(number="001"),
                   _make_minimal_task_dict(number="002", title="Implement service")]
        )
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        result = read_breakdown_handoff(feature_dir)
        self.assertEqual(len(result.tasks), 2)
        for row in result.tasks:
            self.assertIsInstance(row, TaskRow)

    def test_task_fields_roundtrip(self):
        """TaskRow fields survive the JSON round-trip intact."""
        task = _make_minimal_task_dict(
            number="003",
            title="Add API endpoint",
            agent="frontend-engineer",
            depends_on=["001", "002"],
            touched_files=["src/api.py"],
            ac_addressed=["AC-2", "AC-3"],
            review_checkpoint=True,
        )
        data = _make_valid_breakdown_dict(tasks=[task])
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        result = read_breakdown_handoff(feature_dir)
        row = result.tasks[0]
        self.assertEqual(row.number, "003")
        self.assertEqual(row.title, "Add API endpoint")
        self.assertEqual(row.agent, "frontend-engineer")
        self.assertEqual(row.depends_on, ["001", "002"])
        self.assertEqual(row.touched_files, ["src/api.py"])
        self.assertEqual(row.ac_addressed, ["AC-2", "AC-3"])
        self.assertTrue(row.review_checkpoint)

    def test_accepts_string_feature_dir(self):
        """feature_dir may be passed as a string."""
        data = _make_valid_breakdown_dict()
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        result = read_breakdown_handoff(str(feature_dir))
        self.assertIsInstance(result, Breakdown)

    def test_empty_tasks_list_is_accepted(self):
        """Breakdown with no tasks is valid at schema level."""
        data = _make_valid_breakdown_dict(tasks=[])
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        result = read_breakdown_handoff(feature_dir)
        self.assertEqual(result.tasks, [])

    def test_provenance_with_upstream_set(self):
        """Provenance with both upstream fields set is accepted."""
        data = _make_valid_breakdown_dict(
            provenance=_make_minimal_provenance_dict(
                upstream_handoff_path="/specs/001/plan-handoff.json",
                upstream_handoff_kind="plan",
                plan_path="/specs/001/plan.md",
                spec_path="/specs/001/spec.md",
            )
        )
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        result = read_breakdown_handoff(feature_dir)
        self.assertEqual(result.provenance.upstream_handoff_kind, "plan")
        self.assertIsNotNone(result.provenance.upstream_handoff_path)


# ---------------------------------------------------------------------------
# Test: read_breakdown_handoff -- error paths
# ---------------------------------------------------------------------------

class TestReadBreakdownHandoffErrors(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_raises_ValueError(self):
        """Absent breakdown-handoff.json raises ValueError."""
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)

        with self.assertRaises(ValueError) as ctx:
            read_breakdown_handoff(feature_dir)
        self.assertIn("not found", str(ctx.exception))

    def test_malformed_json_raises_ValueError(self):
        """Syntactically invalid JSON raises ValueError."""
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        (feature_dir / "breakdown-handoff.json").write_text(
            "{ not valid json }", encoding="utf-8"
        )

        with self.assertRaises(ValueError) as ctx:
            read_breakdown_handoff(feature_dir)
        self.assertIn("not valid JSON", str(ctx.exception))

    def test_wrong_handoff_kind_raises_ValueError(self):
        """handoff_kind != 'breakdown' raises ValueError."""
        data = _make_valid_breakdown_dict(handoff_kind="plan")
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        with self.assertRaises(ValueError) as ctx:
            read_breakdown_handoff(feature_dir)
        self.assertIn("wrong handoff_kind", str(ctx.exception))
        self.assertIn("plan", str(ctx.exception))

    def test_non_dict_root_raises_ValueError(self):
        """JSON root that is not an object raises ValueError."""
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        (feature_dir / "breakdown-handoff.json").write_text(
            json.dumps([1, 2, 3]), encoding="utf-8"
        )

        with self.assertRaises(ValueError) as ctx:
            read_breakdown_handoff(feature_dir)
        self.assertIn("root must be a JSON object", str(ctx.exception))

    def test_tasks_not_list_raises_ValueError(self):
        """tasks field that is not an array raises ValueError."""
        data = _make_valid_breakdown_dict(tasks="not a list")
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        with self.assertRaises(ValueError) as ctx:
            read_breakdown_handoff(feature_dir)
        self.assertIn("tasks", str(ctx.exception))

    def test_empty_task_number_raises_ValueError(self):
        """TaskRow with empty number field fails schema validation."""
        data = _make_valid_breakdown_dict(
            tasks=[_make_minimal_task_dict(number="")]
        )
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        with self.assertRaises(ValueError) as ctx:
            read_breakdown_handoff(feature_dir)
        self.assertIn("number", str(ctx.exception).lower())

    def test_empty_task_agent_raises_ValueError(self):
        """TaskRow with empty agent field fails schema validation."""
        data = _make_valid_breakdown_dict(
            tasks=[_make_minimal_task_dict(agent="")]
        )
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        with self.assertRaises(ValueError) as ctx:
            read_breakdown_handoff(feature_dir)
        self.assertIn("agent", str(ctx.exception).lower())

    def test_wrong_schema_version_raises_ValueError(self):
        """Breakdown with wrong schema_version fails validation."""
        data = _make_valid_breakdown_dict(schema_version="99.0")
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        with self.assertRaises(ValueError) as ctx:
            read_breakdown_handoff(feature_dir)
        self.assertIn("schema", str(ctx.exception).lower())

    def test_non_dict_provenance_raises_ValueError(self):
        """provenance field that is not an object raises ValueError."""
        data = _make_valid_breakdown_dict(provenance="not a dict")
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True)
        _write_breakdown_json(feature_dir, data)

        with self.assertRaises(ValueError) as ctx:
            read_breakdown_handoff(feature_dir)
        self.assertIn("provenance", str(ctx.exception))


# ---------------------------------------------------------------------------
# Test: task_row
# ---------------------------------------------------------------------------

class TestTaskRow(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _make_handoff_with_tasks(self, task_dicts):
        """Write + load a breakdown with the given task dicts."""
        data = _make_valid_breakdown_dict(tasks=task_dicts)
        feature_dir = self.tmp_path / "specs" / "001-widget"
        feature_dir.mkdir(parents=True, exist_ok=True)
        _write_breakdown_json(feature_dir, data)
        return read_breakdown_handoff(feature_dir)

    def test_returns_matching_task_row(self):
        """task_row returns the TaskRow with the given number."""
        handoff = self._make_handoff_with_tasks([
            _make_minimal_task_dict(number="001", title="First task"),
            _make_minimal_task_dict(number="002", title="Second task"),
        ])
        row = task_row(handoff, "001")
        self.assertIsInstance(row, TaskRow)
        self.assertEqual(row.number, "001")
        self.assertEqual(row.title, "First task")

    def test_returns_second_task(self):
        """task_row can return any task by number, not just the first."""
        handoff = self._make_handoff_with_tasks([
            _make_minimal_task_dict(number="001", title="First"),
            _make_minimal_task_dict(number="002", title="Second"),
            _make_minimal_task_dict(number="003", title="Third"),
        ])
        row = task_row(handoff, "003")
        self.assertEqual(row.title, "Third")

    def test_absent_number_raises_ValueError(self):
        """task_row raises ValueError when the number is not found."""
        handoff = self._make_handoff_with_tasks([
            _make_minimal_task_dict(number="001"),
        ])
        with self.assertRaises(ValueError) as ctx:
            task_row(handoff, "999")
        self.assertIn("999", str(ctx.exception))

    def test_error_message_lists_available_numbers(self):
        """ValueError message lists available task numbers."""
        handoff = self._make_handoff_with_tasks([
            _make_minimal_task_dict(number="001"),
            _make_minimal_task_dict(number="002"),
        ])
        with self.assertRaises(ValueError) as ctx:
            task_row(handoff, "005")
        msg = str(ctx.exception)
        self.assertIn("001", msg)
        self.assertIn("002", msg)

    def test_empty_tasks_list_raises_ValueError(self):
        """task_row raises ValueError on empty tasks list."""
        handoff = self._make_handoff_with_tasks([])
        with self.assertRaises(ValueError):
            task_row(handoff, "001")


# ---------------------------------------------------------------------------
# Test: REAL PRODUCER round-trip
# ---------------------------------------------------------------------------

class TestReadBreakdownHandoffRealProducer(unittest.TestCase):
    """Round-trip: real breakdown_helper finalize-handoff -> read_breakdown_handoff.

    This test exercises the FULL read path against output produced by the
    live breakdown_helper, not a hand-authored JSON blob.
    """

    def setUp(self):
        self._saved_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        os.chdir(self._saved_cwd)
        self._tmp.cleanup()

    def _build_feature_fixture(self):
        """Create specs/001-widget-catalog/{plan.md, tasks/001-*.md, tasks/README.md}.

        Returns the path to plan.md.
        """
        feature_dir = self.tmp_path / "specs" / "001-widget-catalog"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        plan_path = feature_dir / "plan.md"
        _write_minimal_plan(plan_path)

        task_path = tasks_dir / "001-define-widget-types.md"
        _write_minimal_task_file(task_path, number="001",
                                  title="Define widget types",
                                  agent="backend-engineer")

        readme_path = tasks_dir / "README.md"
        _write_minimal_readme(readme_path)

        return plan_path

    def test_round_trip_produces_valid_Breakdown(self):
        """breakdown_helper finalize-handoff -> read_breakdown_handoff returns Breakdown."""
        plan_path = self._build_feature_fixture()
        feature_dir = plan_path.parent

        # Run the REAL producer.
        result = _run_finalize_handoff(self.tmp_path, plan_path)
        self.assertEqual(
            result.returncode, 0,
            "breakdown_helper finalize-handoff failed:\n"
            "  stdout: {0}\n  stderr: {1}".format(result.stdout, result.stderr)
        )

        # Confirm the file was written.
        handoff_file = feature_dir / "breakdown-handoff.json"
        self.assertTrue(
            handoff_file.exists(),
            "breakdown-handoff.json was not created by finalize-handoff"
        )

        # Now test the consumer (our reader).
        handoff = read_breakdown_handoff(feature_dir)

        self.assertIsInstance(handoff, Breakdown)
        self.assertEqual(handoff.handoff_kind, HANDOFF_KIND)
        self.assertEqual(handoff.schema_version, SCHEMA_VERSION)

    def test_round_trip_tasks_match_fixture(self):
        """After real producer, tasks list contains 1 TaskRow for task 001."""
        plan_path = self._build_feature_fixture()
        feature_dir = plan_path.parent

        result = _run_finalize_handoff(self.tmp_path, plan_path)
        self.assertEqual(result.returncode, 0, result.stderr)

        handoff = read_breakdown_handoff(feature_dir)

        # Should have exactly 1 task from our fixture.
        self.assertEqual(len(handoff.tasks), 1)
        row = handoff.tasks[0]
        self.assertIsInstance(row, TaskRow)
        self.assertEqual(row.number, "001")
        self.assertEqual(row.agent, "backend-engineer")

    def test_round_trip_task_row_lookup(self):
        """task_row finds the task produced by the real finalize-handoff."""
        plan_path = self._build_feature_fixture()
        feature_dir = plan_path.parent

        result = _run_finalize_handoff(self.tmp_path, plan_path)
        self.assertEqual(result.returncode, 0, result.stderr)

        handoff = read_breakdown_handoff(feature_dir)
        row = task_row(handoff, "001")

        self.assertEqual(row.number, "001")
        self.assertIsInstance(row, TaskRow)

    def test_round_trip_wrong_number_raises(self):
        """task_row raises ValueError for a nonexistent number after real round-trip."""
        plan_path = self._build_feature_fixture()
        feature_dir = plan_path.parent

        result = _run_finalize_handoff(self.tmp_path, plan_path)
        self.assertEqual(result.returncode, 0, result.stderr)

        handoff = read_breakdown_handoff(feature_dir)

        with self.assertRaises(ValueError):
            task_row(handoff, "999")


if __name__ == "__main__":
    unittest.main()
