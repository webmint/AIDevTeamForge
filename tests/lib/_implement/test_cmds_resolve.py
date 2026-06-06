"""Tests for src/devforge/lib/_implement/_cmds_resolve.py.

Coverage:

  _read_task_status:
    - Status line present → returns stripped value.
    - No Status line → returns None.
    - File unreadable → returns None.

  _is_complete:
    - Complete → True.
    - Skipped → True.
    - Pending → False.
    - In Progress → False.
    - None (absent) → False.
    - Unknown string → False.

  _task_number_sort_key:
    - '001' → 1
    - '010' → 10
    - 'abc' → maxint (non-numeric)

  _feature_sort_key:
    - '001-slug' → 1
    - '012-slug' → 12
    - 'no-prefix' → maxint

  _read_task_statuses:
    - Reads status for each number from tasks/*.md.
    - Number with no matching file → None.
    - File present but no Status → None.

  _resolve_task:
    - All tasks complete → ("all-complete", []).
    - One incomplete task with no deps → that task returned.
    - Incomplete task whose dep is complete → returned.
    - Incomplete task whose dep is incomplete → blocked.
    - Multiple ready tasks → lowest-numbered returned.
    - Dep is Skipped → treated as satisfied (ready).

  cmd_resolve_next_task (integration, using real producer):
    - No specs/ dir → all-complete (exit 0).
    - Feature dir present but no breakdown-handoff.json → all-complete.
    - Real breakdown-handoff.json + Pending tasks → returns task JSON.
    - All tasks Complete → all-complete.
    - Feature with blocked tasks (dep Pending) → blocked (exit 2).
    - Two features: first has all Complete, second has Pending → returns
      task from second feature.
    - Task with Skipped dep → not blocked (dep counts as satisfied).

Real-producer test discipline:
  Round-trip tests run the REAL breakdown_helper finalize-handoff subprocess
  to produce breakdown-handoff.json, then call cmd_resolve_next_task.
  Task files are written in the format breakdown emits (Status: Pending).

Stdlib only. Python 3.8+.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_BREAKDOWN_HELPER_PY = _LIB_DIR / "breakdown_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _implement._cmds_resolve import (  # noqa: E402
    COMPLETE_STATUSES,
    _read_task_status,
    _is_complete,
    _task_number_sort_key,
    _feature_sort_key,
    _read_task_statuses,
    _locate_task_file,
    _count_progress,
    _resolve_task,
    cmd_resolve_next_task,
)
from _breakdown.handoff_schema import (  # noqa: E402
    Breakdown,
    Provenance,
    TaskRow,
    HANDOFF_KIND,
    SCHEMA_VERSION,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_task_row(number="001", title="Define types", agent="backend-engineer",
                   depends_on=None, blocks=None, touched_files=None,
                   expects=None, produces=None, ac_addressed=None,
                   doc_refs=None, review_checkpoint=False):
    # type: (...) -> TaskRow
    """Return a minimal valid TaskRow for testing."""
    return TaskRow(
        number=number,
        title=title,
        agent=agent,
        depends_on=depends_on or [],
        blocks=blocks or [],
        touched_files=touched_files or ["src/widget.py"],
        expects=expects or [],
        produces=produces or ["Widget defined"],
        ac_addressed=ac_addressed or ["AC-1"],
        doc_refs=doc_refs or [],
        review_checkpoint=review_checkpoint,
    )


def _make_breakdown(tasks_list, tasks_dir="specs/001-widget/tasks"):
    # type: (list, str) -> Breakdown
    """Build a minimal valid Breakdown with the given tasks."""
    return Breakdown(
        schema_version=SCHEMA_VERSION,
        handoff_kind=HANDOFF_KIND,
        tasks_dir=tasks_dir,
        breakdown_completed_at="2026-06-01T12:00:00Z",
        provenance=Provenance(),
        tasks=tasks_list,
        additions=[],
        dependency_graph="",
    )


def _write_breakdown_json(feature_dir, breakdown):
    # type: (Path, Breakdown) -> None
    """Serialize a Breakdown and write breakdown-handoff.json."""
    import dataclasses
    data = dataclasses.asdict(breakdown)
    path = feature_dir / "breakdown-handoff.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_task_md(tasks_dir, number, title, agent, depends_on_str="None",
                   status="Pending"):
    # type: (Path, str, str, str, str, str) -> None
    """Write a task markdown file in the exact format breakdown emits."""
    filename = "{0}-{1}.md".format(number, title.lower().replace(" ", "-"))
    content = (
        "# Task {number}: {title}\n\n"
        "**Feature**: 001-widget-catalog\n"
        "**Agent**: {agent}\n"
        "**Status**: {status}\n"
        "**Depends on**: {depends_on}\n"
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
    ).format(
        number=number, title=title, agent=agent, status=status,
        depends_on=depends_on_str,
    )
    (tasks_dir / filename).write_text(content, encoding="utf-8")


def _write_minimal_plan(path, feature_name="Widget Catalog"):
    # type: (Path, str) -> None
    """Write a minimal Approved plan.md."""
    content = (
        "# Plan: {feature}\n\n"
        "**Date**: 2026-06-01\n"
        "**Status**: Approved\n"
        "**Author**: Claude + User\n\n"
        "## Summary\n\nBuild {feature}.\n\n"
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
    ).format(feature=feature_name)
    path.write_text(content, encoding="utf-8")


def _write_minimal_readme(path, task_rows):
    # type: (Path, List[Dict]) -> None
    """Write a tasks/README.md with rows for each task."""
    row_lines = []
    for row in task_rows:
        row_lines.append(
            "| {number} | {title} | {agent} | {dep} | {status} |".format(
                number=row.get("number", "001"),
                title=row.get("title", "Define types"),
                agent=row.get("agent", "backend-engineer"),
                dep=row.get("depends_on", "None"),
                status=row.get("status", "Pending"),
            )
        )
    content = (
        "# Tasks: Widget Catalog\n\n"
        "**Spec**: specs/001-widget-catalog/spec.md\n"
        "**Plan**: specs/001-widget-catalog/plan.md\n"
        "**Generated**: 2026-06-01\n"
        "**Total tasks**: {count}\n\n"
        "## Dependency Graph\n\n"
        "```\n"
        "001 (Define types)\n"
        "```\n\n"
        "## Task Index\n\n"
        "| # | Title | Agent | Depends on | Status |\n"
        "|---|-------|-------|-----------|--------|\n"
        "{rows}\n\n"
        "## Additions to Spec\n\n"
        "[Files or changes discovered that weren't in the original spec]\n\n"
        "## Risk Assessment\n\n"
        "| Task | Risk | Reason |\n"
        "|------|------|--------|\n"
        "| 001 | Low | Straightforward dataclass |\n\n"
        "## Review Checkpoints\n\n"
        "| Before Task | Reason | What to Review |\n"
        "|-------------|--------|----------------|\n"
        "| [NNN] | [convergence] | [what to verify] |\n"
    ).format(count=len(task_rows), rows="\n".join(row_lines))
    path.write_text(content, encoding="utf-8")


def _run_finalize_handoff(tmp_dir, plan_path):
    """Run breakdown_helper finalize-handoff as subprocess."""
    return subprocess.run(
        [sys.executable, str(_BREAKDOWN_HELPER_PY), "finalize-handoff", str(plan_path)],
        cwd=str(tmp_dir),
        capture_output=True,
        text=True,
    )


class _FakeArgs:
    """Minimal argparse namespace for unit tests."""
    def __init__(self, root="."):
        self.root = root


# ---------------------------------------------------------------------------
# Unit tests: _read_task_status
# ---------------------------------------------------------------------------


class TestReadTaskStatus(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_status_present_returns_value(self):
        """Status line is present → returns the stripped status token."""
        f = self.tmp / "001-task.md"
        f.write_text("# Task 001: Something\n\n**Status**: Pending\n", encoding="utf-8")
        self.assertEqual(_read_task_status(f), "Pending")

    def test_status_complete(self):
        f = self.tmp / "001-task.md"
        f.write_text("# Task 001: Thing\n\n**Status**: Complete\n", encoding="utf-8")
        self.assertEqual(_read_task_status(f), "Complete")

    def test_status_skipped(self):
        f = self.tmp / "001-task.md"
        f.write_text("# Task 001: Thing\n\n**Status**: Skipped\n", encoding="utf-8")
        self.assertEqual(_read_task_status(f), "Skipped")

    def test_status_in_progress(self):
        f = self.tmp / "001-task.md"
        f.write_text("**Status**: In Progress\n", encoding="utf-8")
        self.assertEqual(_read_task_status(f), "In Progress")

    def test_status_absent_returns_none(self):
        """No **Status**: line → None."""
        f = self.tmp / "001-task.md"
        f.write_text("# Task 001: No status\n\n## Description\n", encoding="utf-8")
        self.assertIsNone(_read_task_status(f))

    def test_file_absent_returns_none(self):
        """Unreadable/absent file → None."""
        f = self.tmp / "nonexistent.md"
        self.assertIsNone(_read_task_status(f))

    def test_status_strips_trailing_whitespace(self):
        f = self.tmp / "001-task.md"
        f.write_text("**Status**: Pending  \n", encoding="utf-8")
        self.assertEqual(_read_task_status(f), "Pending")


# ---------------------------------------------------------------------------
# Unit tests: _is_complete
# ---------------------------------------------------------------------------


class TestIsComplete(unittest.TestCase):

    def test_complete_is_true(self):
        self.assertTrue(_is_complete("Complete"))

    def test_skipped_is_true(self):
        self.assertTrue(_is_complete("Skipped"))

    def test_pending_is_false(self):
        self.assertFalse(_is_complete("Pending"))

    def test_in_progress_is_false(self):
        self.assertFalse(_is_complete("In Progress"))

    def test_none_is_false(self):
        self.assertFalse(_is_complete(None))

    def test_unknown_string_is_false(self):
        self.assertFalse(_is_complete("whatever"))

    def test_empty_string_is_false(self):
        self.assertFalse(_is_complete(""))


# ---------------------------------------------------------------------------
# Unit tests: _task_number_sort_key
# ---------------------------------------------------------------------------


class TestTaskNumberSortKey(unittest.TestCase):

    def test_zero_padded_001(self):
        self.assertEqual(_task_number_sort_key("001"), 1)

    def test_zero_padded_010(self):
        self.assertEqual(_task_number_sort_key("010"), 10)

    def test_unpadded(self):
        self.assertEqual(_task_number_sort_key("3"), 3)

    def test_non_numeric_returns_large(self):
        key = _task_number_sort_key("abc")
        self.assertGreater(key, 1000000)

    def test_ordering(self):
        keys = [_task_number_sort_key(n) for n in ["003", "001", "010", "002"]]
        self.assertEqual(sorted(range(4), key=lambda i: keys[i]), [1, 3, 0, 2])


# ---------------------------------------------------------------------------
# Unit tests: _feature_sort_key
# ---------------------------------------------------------------------------


class TestFeatureSortKey(unittest.TestCase):

    def test_001_slug(self):
        self.assertEqual(_feature_sort_key(Path("specs/001-slug")), 1)

    def test_012_slug(self):
        self.assertEqual(_feature_sort_key(Path("specs/012-slug")), 12)

    def test_no_prefix(self):
        key = _feature_sort_key(Path("specs/no-prefix"))
        self.assertGreater(key, 1000000)

    def test_ordering(self):
        dirs = [Path("specs/003-x"), Path("specs/001-y"), Path("specs/002-z")]
        dirs.sort(key=_feature_sort_key)
        self.assertEqual([d.name for d in dirs], ["001-y", "002-z", "003-x"])


# ---------------------------------------------------------------------------
# Unit tests: _read_task_statuses
# ---------------------------------------------------------------------------


class TestReadTaskStatuses(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.tasks_dir = self.tmp / "tasks"
        self.tasks_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_reads_existing_status(self):
        _write_task_md(self.tasks_dir, "001", "define types", "backend-engineer",
                       status="Pending")
        statuses = _read_task_statuses(self.tasks_dir, ["001"])
        self.assertEqual(statuses["001"], "Pending")

    def test_missing_file_returns_none(self):
        statuses = _read_task_statuses(self.tasks_dir, ["001"])
        self.assertIsNone(statuses["001"])

    def test_reads_complete_status(self):
        _write_task_md(self.tasks_dir, "001", "define types", "backend-engineer",
                       status="Complete")
        statuses = _read_task_statuses(self.tasks_dir, ["001"])
        self.assertEqual(statuses["001"], "Complete")

    def test_reads_multiple_statuses(self):
        _write_task_md(self.tasks_dir, "001", "define types", "backend-engineer",
                       status="Complete")
        _write_task_md(self.tasks_dir, "002", "build repo", "backend-engineer",
                       status="Pending")
        statuses = _read_task_statuses(self.tasks_dir, ["001", "002"])
        self.assertEqual(statuses["001"], "Complete")
        self.assertEqual(statuses["002"], "Pending")

    def test_tasks_dir_absent_returns_none(self):
        absent_dir = self.tmp / "absent"
        statuses = _read_task_statuses(absent_dir, ["001"])
        self.assertIsNone(statuses["001"])


# ---------------------------------------------------------------------------
# Unit tests: _locate_task_file
# ---------------------------------------------------------------------------


class TestLocateTaskFile(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.tasks_dir = self.tmp / "tasks"
        self.tasks_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_finds_matching_md_file(self):
        """File 001-define-types.md → returns its absolute Path."""
        f = self.tasks_dir / "001-define-types.md"
        f.write_text("**Status**: Pending\n", encoding="utf-8")
        result = _locate_task_file(self.tasks_dir, "001")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "001-define-types.md")

    def test_returns_none_for_missing_number(self):
        """No matching file → None."""
        result = _locate_task_file(self.tasks_dir, "099")
        self.assertIsNone(result)

    def test_ignores_readme(self):
        """README.md is not matched even if its name starts with digits."""
        readme = self.tasks_dir / "README.md"
        readme.write_text("# Tasks\n", encoding="utf-8")
        # No other file; asking for "001" should return None.
        result = _locate_task_file(self.tasks_dir, "README")
        self.assertIsNone(result)

    def test_absent_tasks_dir_returns_none(self):
        """Non-existent tasks directory → None (no exception)."""
        absent = self.tmp / "nonexistent"
        result = _locate_task_file(absent, "001")
        self.assertIsNone(result)

    def test_returns_absolute_path(self):
        """Returned path should be absolute (resolved)."""
        f = self.tasks_dir / "002-build-repo.md"
        f.write_text("x\n", encoding="utf-8")
        result = _locate_task_file(self.tasks_dir, "002")
        self.assertIsNotNone(result)
        self.assertTrue(result.is_absolute())

    def test_zero_padded_match(self):
        """File '1-something.md' matches number '001' (zero-padded equivalence)."""
        f = self.tasks_dir / "1-something.md"
        f.write_text("x\n", encoding="utf-8")
        result = _locate_task_file(self.tasks_dir, "001")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "1-something.md")


# ---------------------------------------------------------------------------
# Unit tests: _count_progress
# ---------------------------------------------------------------------------


class TestCountProgress(unittest.TestCase):

    def test_all_pending(self):
        statuses = {"001": "Pending", "002": "Pending"}
        completed, total = _count_progress(statuses)
        self.assertEqual(completed, 0)
        self.assertEqual(total, 2)

    def test_all_complete(self):
        statuses = {"001": "Complete", "002": "Complete"}
        completed, total = _count_progress(statuses)
        self.assertEqual(completed, 2)
        self.assertEqual(total, 2)

    def test_mixed_complete_and_pending(self):
        statuses = {"001": "Complete", "002": "Pending", "003": "Complete"}
        completed, total = _count_progress(statuses)
        self.assertEqual(completed, 2)
        self.assertEqual(total, 3)

    def test_skipped_counts_as_completed(self):
        """Skipped counts toward completed_count (matches dependency semantics)."""
        statuses = {"001": "Skipped", "002": "Pending"}
        completed, total = _count_progress(statuses)
        self.assertEqual(completed, 1)
        self.assertEqual(total, 2)

    def test_none_status_does_not_count(self):
        """None (absent Status line) is incomplete."""
        statuses = {"001": None, "002": "Complete"}
        completed, total = _count_progress(statuses)
        self.assertEqual(completed, 1)
        self.assertEqual(total, 2)

    def test_empty_statuses(self):
        completed, total = _count_progress({})
        self.assertEqual(completed, 0)
        self.assertEqual(total, 0)

    def test_in_progress_does_not_count(self):
        statuses = {"001": "In Progress"}
        completed, total = _count_progress(statuses)
        self.assertEqual(completed, 0)
        self.assertEqual(total, 1)


# ---------------------------------------------------------------------------
# Unit tests: _resolve_task (pure logic)
# ---------------------------------------------------------------------------


class TestResolveTask(unittest.TestCase):

    def _statuses(self, mapping):
        # type: (Dict[str, Optional[str]]) -> Dict[str, Optional[str]]
        return mapping

    def test_all_complete_returns_all_complete(self):
        tasks = [_make_task_row("001"), _make_task_row("002")]
        statuses = {"001": "Complete", "002": "Complete"}
        selected, reason, blocking = _resolve_task(tasks, statuses)
        self.assertIsNone(selected)
        self.assertEqual(reason, "all-complete")
        self.assertEqual(blocking, [])

    def test_single_pending_no_deps_returns_task(self):
        tasks = [_make_task_row("001", depends_on=[])]
        statuses = {"001": "Pending"}
        selected, reason, blocking = _resolve_task(tasks, statuses)
        self.assertIsNotNone(selected)
        self.assertEqual(reason, "ready")
        self.assertEqual(selected.number, "001")  # type: ignore[union-attr]
        self.assertEqual(blocking, [])

    def test_dep_complete_makes_task_ready(self):
        tasks = [
            _make_task_row("001"),
            _make_task_row("002", depends_on=["001"]),
        ]
        statuses = {"001": "Complete", "002": "Pending"}
        selected, reason, blocking = _resolve_task(tasks, statuses)
        self.assertEqual(reason, "ready")
        self.assertEqual(selected.number, "002")  # type: ignore[union-attr]

    def test_dep_pending_blocks_when_all_tasks_have_unmet_deps(self):
        """A feature is blocked when EVERY incomplete task has at least one
        incomplete dep.  Here task 001 depends on 999 (nonexistent → None = incomplete)
        and task 002 depends on 001 (also incomplete).  No task is ready."""
        tasks = [
            _make_task_row("001", depends_on=["999"]),
            _make_task_row("002", depends_on=["001"]),
        ]
        statuses = {"001": "Pending", "002": "Pending", "999": None}
        selected, reason, blocking = _resolve_task(tasks, statuses)
        self.assertIsNone(selected)
        self.assertEqual(reason, "blocked")
        self.assertTrue(len(blocking) > 0)

    def test_dep_skipped_counts_as_satisfied(self):
        """A Skipped predecessor satisfies a depends_on — task should be ready."""
        tasks = [
            _make_task_row("001"),
            _make_task_row("002", depends_on=["001"]),
        ]
        statuses = {"001": "Skipped", "002": "Pending"}
        selected, reason, blocking = _resolve_task(tasks, statuses)
        self.assertEqual(reason, "ready")
        self.assertEqual(selected.number, "002")  # type: ignore[union-attr]

    def test_multiple_ready_returns_lowest_numbered(self):
        """When multiple tasks are ready, return the lowest-numbered."""
        tasks = [
            _make_task_row("001"),
            _make_task_row("002"),
            _make_task_row("003"),
        ]
        statuses = {"001": "Pending", "002": "Pending", "003": "Pending"}
        selected, reason, blocking = _resolve_task(tasks, statuses)
        self.assertEqual(reason, "ready")
        self.assertEqual(selected.number, "001")  # type: ignore[union-attr]

    def test_first_task_complete_picks_next_ready(self):
        tasks = [
            _make_task_row("001"),
            _make_task_row("002", depends_on=["001"]),
            _make_task_row("003", depends_on=["001"]),
        ]
        statuses = {"001": "Complete", "002": "Pending", "003": "Pending"}
        selected, reason, blocking = _resolve_task(tasks, statuses)
        self.assertEqual(reason, "ready")
        # Both 002 and 003 are ready; lowest wins.
        self.assertEqual(selected.number, "002")  # type: ignore[union-attr]

    def test_absent_status_treated_as_incomplete(self):
        """None status (no Status line) counts as incomplete, not complete."""
        tasks = [_make_task_row("001", depends_on=[])]
        statuses = {"001": None}
        selected, reason, blocking = _resolve_task(tasks, statuses)
        self.assertEqual(reason, "ready")
        self.assertEqual(selected.number, "001")  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Integration tests: cmd_resolve_next_task (real-producer round-trips)
# ---------------------------------------------------------------------------


class TestCmdResolveNoSpecs(unittest.TestCase):
    """cmd_resolve_next_task with no specs/ dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_specs_dir_all_complete(self):
        """No specs/ directory at all → all-complete."""
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_resolve_next_task(args)
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["state"], "all-complete")

    def test_empty_specs_dir_all_complete(self):
        """Empty specs/ dir (no feature subdirs) → all-complete."""
        (self.tmp / "specs").mkdir()
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_resolve_next_task(args)
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["state"], "all-complete")

    def test_feature_dir_without_handoff_skipped(self):
        """Feature dir present but no breakdown-handoff.json → all-complete."""
        feat = self.tmp / "specs" / "001-widget"
        feat.mkdir(parents=True)
        (feat / "plan.md").write_text("# Plan\n**Status**: Approved\n", encoding="utf-8")
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_resolve_next_task(args)
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["state"], "all-complete")


class TestCmdResolveSinglePendingTask(unittest.TestCase):
    """cmd_resolve_next_task: one feature, one Pending task."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        # Build real breakdown-handoff.json via real producer.
        self.feat = self.tmp / "specs" / "001-widget-catalog"
        self.feat.mkdir(parents=True)
        plan_path = self.feat / "plan.md"
        _write_minimal_plan(plan_path)
        tasks_dir = self.feat / "tasks"
        tasks_dir.mkdir()
        _write_task_md(tasks_dir, "001", "define types", "backend-engineer",
                       status="Pending")
        readme_path = tasks_dir / "README.md"
        _write_minimal_readme(readme_path, [
            {"number": "001", "title": "Define types",
             "agent": "backend-engineer", "depends_on": "None", "status": "Pending"},
        ])
        proc = _run_finalize_handoff(self.tmp, plan_path)
        self._finalize_ok = (proc.returncode == 0)
        self._finalize_stderr = proc.stderr

    def tearDown(self):
        self._tmp.cleanup()

    def test_real_producer_succeeded(self):
        """finalize-handoff succeeded (prerequisite for other tests)."""
        self.assertTrue(
            self._finalize_ok,
            "finalize-handoff failed: {0}".format(self._finalize_stderr),
        )

    def test_returns_task_state(self):
        """Single Pending task → state=task JSON on stdout."""
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_resolve_next_task(args)
        self.assertEqual(code, 0, buf.getvalue())
        data = json.loads(buf.getvalue())
        self.assertEqual(data["state"], "task")
        self.assertEqual(data["number"], "001")
        self.assertIn("title", data)
        self.assertIn("agent", data)
        self.assertIn("feature_dir", data)

    def test_feature_dir_in_output(self):
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_resolve_next_task(args)
        data = json.loads(buf.getvalue())
        # feature_dir should be absolute path pointing to our feature.
        self.assertIn("001-widget-catalog", data["feature_dir"])

    def test_all_required_fields_present(self):
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_resolve_next_task(args)
        data = json.loads(buf.getvalue())
        required = {
            "state", "feature_dir", "number", "title", "agent",
            "depends_on", "touched_files", "expects", "produces",
            "ac_addressed", "doc_refs", "review_checkpoint",
            # New fields added for orchestrator convenience.
            "task_file", "index_file", "completed_count", "total_count",
        }
        for field in required:
            self.assertIn(field, data, "Missing field: {0}".format(field))

    def test_task_file_points_to_real_file(self):
        """task_file in output must point to an existing task .md file."""
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_resolve_next_task(args)
        data = json.loads(buf.getvalue())
        self.assertIsNotNone(data["task_file"], "task_file should not be None")
        self.assertTrue(
            Path(data["task_file"]).exists(),
            "task_file path does not exist: {0}".format(data["task_file"]),
        )
        self.assertTrue(
            data["task_file"].endswith(".md"),
            "task_file should be a .md file: {0}".format(data["task_file"]),
        )

    def test_index_file_points_to_readme(self):
        """index_file in output must point to tasks/README.md."""
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_resolve_next_task(args)
        data = json.loads(buf.getvalue())
        self.assertIn("README.md", data["index_file"])
        self.assertTrue(
            Path(data["index_file"]).exists(),
            "index_file path does not exist: {0}".format(data["index_file"]),
        )

    def test_progress_counts_correct_for_one_pending(self):
        """completed_count=0, total_count=1 for a single Pending task."""
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_resolve_next_task(args)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["completed_count"], 0)
        self.assertEqual(data["total_count"], 1)


class TestCmdResolveAllComplete(unittest.TestCase):
    """cmd_resolve_next_task: all tasks Complete → all-complete."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        feat = self.tmp / "specs" / "001-widget"
        feat.mkdir(parents=True)
        plan_path = feat / "plan.md"
        _write_minimal_plan(plan_path)
        tasks_dir = feat / "tasks"
        tasks_dir.mkdir()
        # Write task file with Complete status.
        _write_task_md(tasks_dir, "001", "define types", "backend-engineer",
                       status="Complete")
        _write_minimal_readme(tasks_dir / "README.md", [
            {"number": "001", "title": "Define types",
             "agent": "backend-engineer", "depends_on": "None", "status": "Complete"},
        ])
        proc = _run_finalize_handoff(self.tmp, plan_path)
        self._finalize_ok = (proc.returncode == 0)

    def tearDown(self):
        self._tmp.cleanup()

    def test_all_complete_when_tasks_complete(self):
        self.assertTrue(self._finalize_ok, "finalize-handoff setup failed")
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_resolve_next_task(args)
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["state"], "all-complete")


class TestCmdResolveBlocked(unittest.TestCase):
    """cmd_resolve_next_task: task has unsatisfied dep → blocked (exit 2)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        feat = self.tmp / "specs" / "001-widget"
        feat.mkdir(parents=True)
        plan_path = feat / "plan.md"
        _write_minimal_plan(plan_path)
        tasks_dir = feat / "tasks"
        tasks_dir.mkdir()
        # Task 001 is Pending (blocker), task 002 depends on 001.
        _write_task_md(tasks_dir, "001", "define types", "backend-engineer",
                       depends_on_str="None", status="Pending")
        _write_task_md(tasks_dir, "002", "build repo", "backend-engineer",
                       depends_on_str="001", status="Pending")
        # README needed for finalize-handoff.
        content = (
            "# Tasks: Widget\n\n"
            "**Spec**: specs/001-widget/spec.md\n"
            "**Plan**: specs/001-widget/plan.md\n"
            "**Generated**: 2026-06-01\n"
            "**Total tasks**: 2\n\n"
            "## Dependency Graph\n\n"
            "```\n001 (Define types) ──→ 002 (Build repo)\n```\n\n"
            "## Task Index\n\n"
            "| # | Title | Agent | Depends on | Status |\n"
            "|---|-------|-------|-----------|--------|\n"
            "| 001 | Define types | backend-engineer | None | Pending |\n"
            "| 002 | Build repo | backend-engineer | 001 | Pending |\n\n"
            "## Additions to Spec\n\n"
            "[Files or changes discovered that weren't in the original spec]\n\n"
            "## Risk Assessment\n\n"
            "| Task | Risk | Reason |\n"
            "|------|------|--------|\n"
            "| 001 | Low | Straightforward |\n\n"
            "## Review Checkpoints\n\n"
            "| Before Task | Reason | What to Review |\n"
            "|-------------|--------|----------------|\n"
            "| 002 | dep | types |\n"
        )
        (tasks_dir / "README.md").write_text(content, encoding="utf-8")
        proc = _run_finalize_handoff(self.tmp, plan_path)
        self._finalize_ok = (proc.returncode == 0)
        self._finalize_stderr = proc.stderr

    def tearDown(self):
        self._tmp.cleanup()

    def test_setup_ok(self):
        self.assertTrue(
            self._finalize_ok,
            "finalize-handoff failed: {0}".format(self._finalize_stderr),
        )

    def test_first_task_ready_not_blocked(self):
        """Task 001 has no deps → it is ready (not blocked)."""
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_resolve_next_task(args)
        data = json.loads(buf.getvalue())
        # Task 001 is Pending with no deps → should be returned as ready.
        self.assertEqual(code, 0)
        self.assertEqual(data["state"], "task")
        self.assertEqual(data["number"], "001")

    def test_skipped_dep_satisfies_downstream_task(self):
        """Mark task 001 as Skipped; task 002 depends on 001 but 001=Skipped
        counts as satisfied — so it should be READY, not blocked."""
        import io, contextlib
        # Change task 001 to Skipped status on disk.
        tasks_dir = self.tmp / "specs" / "001-widget" / "tasks"
        for f in tasks_dir.iterdir():
            if f.name.startswith("001") and f.suffix == ".md":
                text = f.read_text(encoding="utf-8")
                text = text.replace("**Status**: Pending", "**Status**: Skipped")
                f.write_text(text, encoding="utf-8")

        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_resolve_next_task(args)
        data = json.loads(buf.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(data["state"], "task")
        self.assertEqual(data["number"], "002")


class TestCmdResolveIndexFileAbsent(unittest.TestCase):
    """F2: index_file is null when tasks/README.md does not exist."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        # Build a feature with handoff + task file but NO tasks/README.md.
        self.feat = self.tmp / "specs" / "001-no-readme"
        self.feat.mkdir(parents=True)
        plan_path = self.feat / "plan.md"
        _write_minimal_plan(plan_path)
        tasks_dir = self.feat / "tasks"
        tasks_dir.mkdir()
        # Write task file (Status: Pending) — no README.md.
        _write_task_md(tasks_dir, "001", "define types", "backend-engineer",
                       status="Pending")
        # We need a breakdown-handoff.json; write it directly via the helper
        # so it is a real producer artefact.  finalize-handoff requires a
        # README.md to parse the task index — write a temporary one, run the
        # producer, then delete the README so the test sees the "no README"
        # condition that exists AFTER a README was removed (or never created
        # in a future breakdown path that skips index generation).
        _write_minimal_readme(tasks_dir / "README.md", [
            {"number": "001", "title": "Define types",
             "agent": "backend-engineer", "depends_on": "None", "status": "Pending"},
        ])
        proc = _run_finalize_handoff(self.tmp, plan_path)
        self._finalize_ok = (proc.returncode == 0)
        self._finalize_stderr = proc.stderr
        # Now remove the README so the resolve path hits the absent-index branch.
        readme = tasks_dir / "README.md"
        if readme.exists():
            readme.unlink()

    def tearDown(self):
        self._tmp.cleanup()

    def test_finalize_handoff_produced_breakdown(self):
        """Prerequisite: finalize-handoff must have succeeded."""
        self.assertTrue(
            self._finalize_ok,
            "finalize-handoff failed: {0}".format(self._finalize_stderr),
        )
        self.assertTrue(
            (self.feat / "breakdown-handoff.json").exists(),
            "breakdown-handoff.json was not created",
        )

    def test_readme_absent_before_resolve(self):
        """Confirm the README is absent so the test exercises the right branch."""
        self.assertFalse(
            (self.feat / "tasks" / "README.md").exists(),
            "README.md must be absent for this test to be valid",
        )

    def test_index_file_absent_emits_null(self):
        """Feature dir + handoff + task file but NO README → resolve exits 0,
        index_file is null in the output JSON."""
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_resolve_next_task(args)
        self.assertEqual(code, 0, "Expected exit 0 (task ready), got: {0}".format(code))
        data = json.loads(buf.getvalue())
        self.assertEqual(data["state"], "task")
        self.assertIsNone(
            data["index_file"],
            "index_file must be null when README.md does not exist, got: {0}".format(
                data["index_file"]
            ),
        )

    def test_task_file_still_populated_when_index_absent(self):
        """task_file must still point to the real task .md even if index is absent."""
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_resolve_next_task(args)
        data = json.loads(buf.getvalue())
        self.assertIsNotNone(data["task_file"])
        self.assertTrue(
            Path(data["task_file"]).exists(),
            "task_file path does not exist: {0}".format(data["task_file"]),
        )


class TestCmdResolveTwoFeatures(unittest.TestCase):
    """cmd_resolve_next_task: two features, first exhausted → picks second."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        # Feature 001: task Complete.
        feat1 = self.tmp / "specs" / "001-first"
        feat1.mkdir(parents=True)
        plan1 = feat1 / "plan.md"
        _write_minimal_plan(plan1, "First Feature")
        tasks1 = feat1 / "tasks"
        tasks1.mkdir()
        _write_task_md(tasks1, "001", "define types", "backend-engineer",
                       status="Complete")
        _write_minimal_readme(tasks1 / "README.md", [
            {"number": "001", "title": "Define types",
             "agent": "backend-engineer", "depends_on": "None", "status": "Complete"},
        ])
        proc1 = _run_finalize_handoff(self.tmp, plan1)
        self._setup1_ok = (proc1.returncode == 0)

        # Feature 002: task Pending.
        feat2 = self.tmp / "specs" / "002-second"
        feat2.mkdir(parents=True)
        plan2 = feat2 / "plan.md"
        _write_minimal_plan(plan2, "Second Feature")
        tasks2 = feat2 / "tasks"
        tasks2.mkdir()
        _write_task_md(tasks2, "001", "define more types", "backend-engineer",
                       status="Pending")
        _write_minimal_readme(tasks2 / "README.md", [
            {"number": "001", "title": "Define more types",
             "agent": "backend-engineer", "depends_on": "None", "status": "Pending"},
        ])
        proc2 = _run_finalize_handoff(self.tmp, plan2)
        self._setup2_ok = (proc2.returncode == 0)

    def tearDown(self):
        self._tmp.cleanup()

    def test_setup_ok(self):
        self.assertTrue(self._setup1_ok, "finalize-handoff feature 1 failed")
        self.assertTrue(self._setup2_ok, "finalize-handoff feature 2 failed")

    def test_picks_second_feature(self):
        import io, contextlib
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_resolve_next_task(args)
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["state"], "task")
        self.assertIn("002-second", data["feature_dir"])
        # F4: counts must reflect feature 002's tasks ONLY (not summed across features).
        # Feature 002 has exactly 1 task (Pending), so total=1, completed=0.
        self.assertEqual(
            data["total_count"], 1,
            "total_count must reflect feature 002's task count only, not summed across features",
        )
        self.assertEqual(
            data["completed_count"], 0,
            "completed_count must reflect feature 002's completed tasks only",
        )


class TestCmdResolveBlockedExitCode(unittest.TestCase):
    """cmd_resolve_next_task: feature with ALL tasks having unmet deps → exit 2."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        feat = self.tmp / "specs" / "001-circ"
        feat.mkdir(parents=True)
        plan_path = feat / "plan.md"
        _write_minimal_plan(plan_path)
        tasks_dir = feat / "tasks"
        tasks_dir.mkdir()
        # Task 001 depends on 002 (AND task 002 depends on 001 — forced cycle).
        # In practice we just need: all incomplete tasks have unmet deps.
        # Simplest: ONE task whose dep is 999 (nonexistent, hence None status).
        _write_task_md(tasks_dir, "001", "build it", "backend-engineer",
                       depends_on_str="002", status="Pending")
        content = (
            "# Tasks: Circ\n\n"
            "**Spec**: s\n"
            "**Plan**: p\n"
            "**Generated**: 2026-06-01\n"
            "**Total tasks**: 1\n\n"
            "## Dependency Graph\n\n"
            "```\n002 ──→ 001\n```\n\n"
            "## Task Index\n\n"
            "| # | Title | Agent | Depends on | Status |\n"
            "|---|-------|-------|-----------|--------|\n"
            "| 001 | Build it | backend-engineer | 002 | Pending |\n\n"
            "## Additions to Spec\n\n"
            "[none]\n\n"
            "## Risk Assessment\n\n"
            "| Task | Risk | Reason |\n"
            "|------|------|--------|\n"
            "| 001 | Low | Simple |\n\n"
            "## Review Checkpoints\n\n"
            "| Before Task | Reason | What to Review |\n"
            "|-------------|--------|----------------|\n"
            "| [NNN] | [why] | [what] |\n"
        )
        (tasks_dir / "README.md").write_text(content, encoding="utf-8")
        proc = _run_finalize_handoff(self.tmp, plan_path)
        self._finalize_ok = (proc.returncode == 0)
        self._finalize_stderr = proc.stderr

    def tearDown(self):
        self._tmp.cleanup()

    def test_setup_ok(self):
        self.assertTrue(
            self._finalize_ok,
            "finalize-handoff failed: {0}".format(self._finalize_stderr),
        )

    def test_blocked_returns_exit_2(self):
        """Feature has incomplete task(s) with dep=002 (absent = None = incomplete)."""
        import io, contextlib
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_resolve_next_task(args)
        self.assertEqual(code, 2)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["state"], "blocked")
        self.assertIn("blocking_tasks", data)


# ---------------------------------------------------------------------------
# Edge-case tests: COMPLETE_STATUSES constant
# ---------------------------------------------------------------------------


class TestCompleteStatusesConstant(unittest.TestCase):

    def test_complete_and_skipped_in_set(self):
        self.assertIn("Complete", COMPLETE_STATUSES)
        self.assertIn("Skipped", COMPLETE_STATUSES)

    def test_pending_not_in_set(self):
        self.assertNotIn("Pending", COMPLETE_STATUSES)

    def test_in_progress_not_in_set(self):
        self.assertNotIn("In Progress", COMPLETE_STATUSES)

    def test_none_not_in_set(self):
        self.assertNotIn(None, COMPLETE_STATUSES)


if __name__ == "__main__":
    unittest.main()
