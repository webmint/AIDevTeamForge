"""Tests for src/devforge/lib/_implement/_cmds_complete.py.

Coverage:

  _set_status_complete:
    - Status: Pending → Status: Complete.
    - Status: In Progress → Status: Complete.
    - Status: Skipped → Status: Complete.
    - No Status line → Status: Complete prepended.

  _tick_done_when_boxes:
    - All `- [ ]` in Done When section → `- [x]`.
    - Checkboxes outside Done When section (e.g. in Description) are NOT ticked.
    - No Done When section → text unchanged.
    - Mixed already-ticked + unticked → only unticked are ticked.

  _fill_completion_notes:
    - Skeleton replaced with real values.
    - completed_at, files_changed, expects_met, produces_met, notes all present.
    - No Completion Notes section → block appended.

  _update_readme_row (region-aware):
    - Matching row has Status cell updated to Complete.
    - Non-matching rows are unchanged.
    - Row not found → EXIT_FINDINGS, stderr message naming task number.
    - Number "001" does not match "011".
    - Title containing a literal pipe still updates correctly (region-aware
      parsing doesn't rely on column count).
    - Risk Assessment row with the same ``| NNN |`` prefix is NOT touched.
    - Task Index section absent → EXIT_FINDINGS.

  _build_completion_notes_block:
    - Correct heading and all fields present.

  cmd_mark_complete (integration, real task file):
    - Round-trip via real breakdown render-task-file skeleton:
        * Status set to Complete.
        * All Done-When boxes ticked.
        * Completion Notes filled with injected values.
    - README.md row updated from Pending to Complete.
    - Atomic write: original file replaced.
    - --completed-at injected for determinism (no datetime.now call in tests).
    - Missing task file → exit 2, stderr.
    - Missing index file → exit 2, stderr.
    - --number required → exit 2 on absence.
    - Invalid --files JSON → exit 1.

Real-producer test discipline:
  The task file fixture is produced by calling the REAL
  `breakdown_helper render-task-file` subprocess, not by hand-authoring.
  The README fixture is produced by calling the REAL
  `breakdown_helper render-tasks-index` subprocess.

Stdlib only. Python 3.8+.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------

_LIB_DIR = str(Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib")
_BREAKDOWN_HELPER_PY = Path(_LIB_DIR) / "breakdown_helper.py"

if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _implement._cmds_complete import (  # noqa: E402
    _set_status,
    _set_status_complete,
    _tick_done_when_boxes,
    _fill_completion_notes,
    _update_readme_row,
    _build_completion_notes_block,
    cmd_mark_complete,
    cmd_mark_skipped,
    EXIT_OK,
    EXIT_ERR,
    EXIT_FINDINGS,
    _UNVERIFIED_ANNOTATION,
)


# ---------------------------------------------------------------------------
# Real-producer fixture helpers
# ---------------------------------------------------------------------------


def _render_task_file(number="001", title="Define types", feature="001-widget"):
    """Run the real breakdown_helper render-task-file and return its output."""
    result = subprocess.run(
        [
            sys.executable, str(_BREAKDOWN_HELPER_PY),
            "render-task-file",
            "--number", number,
            "--title", title,
            "--feature", feature,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _render_tasks_index(feature="001-widget"):
    """Run the real breakdown_helper render-tasks-index and return its output."""
    result = subprocess.run(
        [
            sys.executable, str(_BREAKDOWN_HELPER_PY),
            "render-tasks-index",
            "--feature", feature,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _make_fake_args(**kwargs):
    class _Args:
        pass
    a = _Args()
    a.task_file = kwargs.get("task_file", "")
    a.index = kwargs.get("index", "")
    a.number = kwargs.get("number", "001")
    a.files = kwargs.get("files", "[]")
    a.expects_met = kwargs.get("expects_met", "2/2")
    a.produces_met = kwargs.get("produces_met", "2/2")
    a.notes = kwargs.get("notes", "No deviations.")
    a.completed_at = kwargs.get("completed_at", "2026-06-01T12:00:00Z")
    a.root = kwargs.get("root", ".")
    return a


# ---------------------------------------------------------------------------
# Unit tests — _set_status_complete
# ---------------------------------------------------------------------------


class TestSetStatusComplete(unittest.TestCase):

    def test_pending_becomes_complete(self):
        text = "**Status**: Pending\n"
        result = _set_status_complete(text)
        self.assertIn("**Status**: Complete", result)
        self.assertNotIn("Pending", result)

    def test_in_progress_becomes_complete(self):
        text = "**Feature**: foo\n**Status**: In Progress\n"
        result = _set_status_complete(text)
        self.assertIn("**Status**: Complete", result)
        self.assertNotIn("In Progress", result)

    def test_skipped_becomes_complete(self):
        text = "**Status**: Skipped\n"
        result = _set_status_complete(text)
        self.assertIn("**Status**: Complete", result)

    def test_no_status_line_appended(self):
        text = "# Task 001: Foo\n\n**Feature**: bar\n"
        result = _set_status_complete(text)
        self.assertIn("**Status**: Complete", result)


# ---------------------------------------------------------------------------
# Unit tests — _tick_done_when_boxes
# ---------------------------------------------------------------------------


class TestTickDoneWhenBoxes(unittest.TestCase):

    def test_all_boxes_ticked_in_section(self):
        text = (
            "## Done When\n\n"
            "- [ ] Condition A\n"
            "- [ ] Condition B\n"
            "- [ ] No debug artifacts\n"
        )
        result = _tick_done_when_boxes(text)
        self.assertIn("- [x] Condition A", result)
        self.assertIn("- [x] Condition B", result)
        self.assertIn("- [x] No debug artifacts", result)
        self.assertNotIn("- [ ]", result)

    def test_boxes_outside_section_not_ticked(self):
        # A checkbox in Description section must not be ticked.
        text = (
            "## Description\n\n"
            "- [ ] This is a description item\n\n"
            "## Done When\n\n"
            "- [ ] Real condition\n\n"
            "## Completion Notes\n\n"
            "nothing\n"
        )
        result = _tick_done_when_boxes(text)
        # Done When box must be ticked.
        self.assertIn("- [x] Real condition", result)
        # Description box must NOT be ticked.
        self.assertIn("- [ ] This is a description item", result)

    def test_no_done_when_section_unchanged(self):
        text = "## Description\n\n- [ ] Some item\n"
        result = _tick_done_when_boxes(text)
        self.assertEqual(result, text)

    def test_already_ticked_stays_ticked(self):
        text = (
            "## Done When\n\n"
            "- [x] Already ticked\n"
            "- [ ] Unticked\n"
        )
        result = _tick_done_when_boxes(text)
        self.assertIn("- [x] Already ticked", result)
        self.assertIn("- [x] Unticked", result)


# ---------------------------------------------------------------------------
# Unit tests — _build_completion_notes_block
# ---------------------------------------------------------------------------


class TestBuildCompletionNotesBlock(unittest.TestCase):

    def test_block_structure(self):
        block = _build_completion_notes_block(
            "2026-06-01T12:00:00Z",
            "src/widget.py, src/api.py",
            "2/2",
            "2/2",
            "No deviations.",
        )
        self.assertIn("## Completion Notes", block)
        self.assertIn("**Completed**: 2026-06-01T12:00:00Z", block)
        self.assertIn("**Files changed**: src/widget.py, src/api.py", block)
        self.assertIn("**Contract**: Expects 2/2 | Produces 2/2", block)
        self.assertIn("**Notes**: No deviations.", block)


# ---------------------------------------------------------------------------
# Unit tests — _fill_completion_notes
# ---------------------------------------------------------------------------


class TestFillCompletionNotes(unittest.TestCase):

    def _make_task_with_notes_skeleton(self):
        """Build a minimal task file with the exact skeleton from storage-rules."""
        return (
            "# Task 001: Define types\n\n"
            "**Status**: Pending\n\n"
            "## Done When\n\n"
            "- [ ] Condition A\n\n"
            "## Completion Notes\n\n"
            "[Filled in by /implement after completion]\n"
            "**Completed**: [date/time]\n"
            "**Files changed**: [actual files]\n"
            "**Contract**: Expects [X/Y verified] | Produces [X/Y verified]\n"
            "**Notes**: [deviations or observations]\n"
        )

    def test_skeleton_replaced_with_values(self):
        text = self._make_task_with_notes_skeleton()
        result = _fill_completion_notes(
            text,
            completed_at="2026-06-01T12:00:00Z",
            files_changed="src/widget.py",
            expects_met="3/3",
            produces_met="2/3",
            notes="One deviation noted.",
        )
        self.assertIn("**Completed**: 2026-06-01T12:00:00Z", result)
        self.assertIn("**Files changed**: src/widget.py", result)
        self.assertIn("**Contract**: Expects 3/3 | Produces 2/3", result)
        self.assertIn("**Notes**: One deviation noted.", result)
        # Placeholder text must not remain.
        self.assertNotIn("[date/time]", result)
        self.assertNotIn("[actual files]", result)
        self.assertNotIn("[X/Y verified]", result)

    def test_no_completion_notes_section_appended(self):
        text = "# Task 001\n\n**Status**: Pending\n"
        result = _fill_completion_notes(
            text,
            completed_at="2026-06-01T12:00:00Z",
            files_changed="src/f.py",
            expects_met="1/1",
            produces_met="1/1",
            notes="OK",
        )
        self.assertIn("## Completion Notes", result)
        self.assertIn("**Completed**: 2026-06-01T12:00:00Z", result)


# ---------------------------------------------------------------------------
# Unit tests — _update_readme_row
# ---------------------------------------------------------------------------


class TestUpdateReadmeRow(unittest.TestCase):

    def _make_readme_with_rows(self, rows):
        """Build a minimal README table with the given rows under ## Task Index."""
        header = (
            "## Task Index\n\n"
            "| # | Title | Agent | Depends on | Status |\n"
            "|---|-------|-------|-----------|--------|\n"
        )
        row_lines = ""
        for r in rows:
            row_lines += "| {0} | {1} | {2} | {3} | {4} |\n".format(
                r["number"], r["title"], r["agent"], r["depends"], r["status"]
            )
        return header + row_lines

    def test_matching_row_status_updated(self):
        text = self._make_readme_with_rows([
            {"number": "001", "title": "Define types", "agent": "backend-engineer",
             "depends": "None", "status": "Pending"},
        ])
        result, rc = _update_readme_row(text, "001", "Complete")
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("| 001 |", result)
        self.assertIn("Complete", result)
        self.assertNotIn("Pending", result)

    def test_non_matching_row_unchanged(self):
        text = self._make_readme_with_rows([
            {"number": "001", "title": "Define types", "agent": "backend-engineer",
             "depends": "None", "status": "Complete"},
            {"number": "002", "title": "Build form", "agent": "frontend-engineer",
             "depends": "001", "status": "Pending"},
        ])
        result, rc = _update_readme_row(text, "002", "Complete")
        self.assertEqual(rc, EXIT_OK)
        # Row 001 must still be Complete.
        self.assertIn("| 001 |", result)
        # Row 002 must be updated to Complete.
        lines = [l for l in result.splitlines() if "| 002 |" in l]
        self.assertEqual(len(lines), 1)
        self.assertIn("Complete", lines[0])

    def test_row_not_found_returns_exit_findings(self):
        """Row not found → EXIT_FINDINGS, stderr names task number."""
        import io
        text = self._make_readme_with_rows([
            {"number": "001", "title": "A", "agent": "X", "depends": "None",
             "status": "Pending"},
        ])
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            result, rc = _update_readme_row(text, "999", "Complete")
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIn("999", err)

    def test_number_match_is_exact(self):
        """'001' must not match '011' or '0011'."""
        import io
        text = self._make_readme_with_rows([
            {"number": "011", "title": "B", "agent": "Y", "depends": "None",
             "status": "Pending"},
        ])
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            result, rc = _update_readme_row(text, "001", "Complete")
        finally:
            sys.stderr = old_stderr
        self.assertEqual(rc, EXIT_FINDINGS)
        # Row 011 must NOT have been updated.
        lines = [l for l in result.splitlines() if "| 011 |" in l]
        self.assertEqual(len(lines), 1)
        self.assertIn("Pending", lines[0])

    def test_title_with_pipe_still_updates_correctly(self):
        """A title containing a literal pipe character updates correctly.

        Region-aware parsing is immune to pipe-in-title fragility because
        the region is bounded by heading markers, not column count.
        The first cell (task number) is always cells[1] regardless of how
        many extra pipes the title contains.
        """
        # Build a row whose title contains a pipe: "Foo | Bar"
        # This produces: | 001 | Foo | Bar | backend-engineer | None | Pending |
        # which has 8 pipe tokens (6 data columns) — the old 7-token heuristic
        # would have skipped this row; the region-aware scan updates it.
        text = (
            "## Task Index\n\n"
            "| # | Title | Agent | Depends on | Status |\n"
            "|---|-------|-------|-----------|--------|\n"
            "| 001 | Foo | Bar | backend-engineer | None | Pending |\n"
        )
        result, rc = _update_readme_row(text, "001", "Complete")
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("Complete", result)
        self.assertNotIn("Pending", result)

    def test_risk_assessment_row_not_touched(self):
        """A Risk Assessment row with the same task number is NOT updated.

        The Risk Assessment table lives under ``## Risk Assessment``, which
        is a different region from ``## Task Index``.  The region-aware
        scan must leave it untouched.
        """
        text = (
            "## Task Index\n\n"
            "| # | Title | Agent | Depends on | Status |\n"
            "|---|-------|-------|-----------|--------|\n"
            "| 001 | Define types | backend-engineer | None | Pending |\n"
            "\n"
            "## Risk Assessment\n\n"
            "| Task | Risk | Reason |\n"
            "|------|------|--------|\n"
            "| 001 | Low | straightforward |\n"
        )
        result, rc = _update_readme_row(text, "001", "Complete")
        self.assertEqual(rc, EXIT_OK)
        # The Task Index row must be updated.
        task_index_lines = [
            l for l in result.splitlines()
            if l.startswith("| 001 |") and "backend-engineer" in l
        ]
        self.assertEqual(len(task_index_lines), 1)
        self.assertIn("Complete", task_index_lines[0])
        # The Risk Assessment row must NOT have been touched.
        risk_lines = [
            l for l in result.splitlines()
            if l.startswith("| 001 |") and "Low" in l
        ]
        self.assertEqual(len(risk_lines), 1)
        self.assertIn("Low", risk_lines[0])
        self.assertNotIn("Complete", risk_lines[0])

    def test_task_index_section_absent_returns_exit_findings(self):
        """When ## Task Index heading is absent, EXIT_FINDINGS is returned."""
        import io
        text = (
            "# Tasks: 001-widget\n\n"
            "Some content without a Task Index heading.\n"
            "| 001 | Something | X | None | Pending |\n"
        )
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            result, rc = _update_readme_row(text, "001", "Complete")
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIn("Task Index", err)


# ---------------------------------------------------------------------------
# Integration tests — cmd_mark_complete (real producer)
# ---------------------------------------------------------------------------


class TestCmdMarkComplete(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.tmpdir) / "tasks"
        self.tasks_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_real_task_file(self, number="001", title="Define types", feature="001-widget"):
        """Write a real task file produced by breakdown_helper render-task-file."""
        content = _render_task_file(number=number, title=title, feature=feature)
        path = self.tasks_dir / "{0}-{1}.md".format(number, title.replace(" ", "-").lower())
        path.write_text(content)
        return path

    def _write_real_readme(self, feature="001-widget"):
        """Write a real README.md produced by breakdown_helper render-tasks-index.

        The skeleton emits a placeholder row `| 001 | [title] | [agent] | None | Pending |`.
        We patch the first row to use our real task number for row-update testing.
        """
        content = _render_tasks_index(feature=feature)
        # Replace the placeholder row with a real row for testing.
        content = content.replace(
            "| 001 | [title] | [agent] | None | Pending |",
            "| 001 | Define types | backend-engineer | None | Pending |",
        )
        path = self.tasks_dir / "README.md"
        path.write_text(content)
        return path

    def test_status_set_to_complete(self):
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        args = _make_fake_args(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            completed_at="2026-06-01T12:00:00Z",
        )
        rc = cmd_mark_complete(args)
        self.assertEqual(rc, EXIT_OK)

        result_text = task_file.read_text()
        self.assertIn("**Status**: Complete", result_text)
        self.assertNotIn("**Status**: Pending", result_text)

    def test_done_when_boxes_ticked(self):
        """All Done When checkboxes must be ticked in the real task file."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        # Confirm the skeleton has unchecked boxes.
        original = task_file.read_text()
        self.assertIn("- [ ]", original, "Task skeleton must have unchecked boxes")

        args = _make_fake_args(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            completed_at="2026-06-01T12:00:00Z",
        )
        rc = cmd_mark_complete(args)
        self.assertEqual(rc, EXIT_OK)

        result_text = task_file.read_text()
        # No unchecked boxes should remain in the Done When section.
        lines = result_text.splitlines()
        in_done_when = False
        for line in lines:
            if line.startswith("## Done When"):
                in_done_when = True
            elif line.startswith("## ") and in_done_when:
                in_done_when = False
            if in_done_when:
                self.assertNotIn("- [ ]", line,
                                 "Unchecked box found in Done When section after mark-complete")

    def test_completion_notes_filled(self):
        """Completion Notes skeleton must be replaced with real values."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        args = _make_fake_args(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            files=json.dumps(["src/widget.py"]),
            expects_met="3/3",
            produces_met="2/2",
            notes="Minor refactor noted.",
            completed_at="2026-06-01T12:00:00Z",
        )
        rc = cmd_mark_complete(args)
        self.assertEqual(rc, EXIT_OK)

        result_text = task_file.read_text()
        self.assertIn("**Completed**: 2026-06-01T12:00:00Z", result_text)
        self.assertIn("**Files changed**: src/widget.py", result_text)
        self.assertIn("**Contract**: Expects 3/3 | Produces 2/2", result_text)
        self.assertIn("**Notes**: Minor refactor noted.", result_text)
        # Skeleton placeholders must not remain.
        self.assertNotIn("[date/time]", result_text)
        self.assertNotIn("[actual files]", result_text)

    def test_readme_row_status_updated(self):
        """The matching README.md row must be updated to Complete."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        args = _make_fake_args(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            completed_at="2026-06-01T12:00:00Z",
        )
        rc = cmd_mark_complete(args)
        self.assertEqual(rc, EXIT_OK)

        readme_text = readme.read_text()
        # The Task Index row for 001 (5 data columns) must now show Complete.
        # Note: the real render-tasks-index also emits a Risk Assessment row
        # `| 001 | Low/Med/High | [why] |` (3 columns) — we check only the
        # 5-column Task Index row (7 pipe tokens including leading/trailing empty).
        all_001_rows = [l for l in readme_text.splitlines() if l.startswith("| 001 |")]
        # Filter to rows with exactly 5 data cells (7 pipe-delimited tokens).
        task_index_rows = [r for r in all_001_rows if len(r.split("|")) == 7]
        self.assertEqual(len(task_index_rows), 1, "Exactly one Task Index row for task 001")
        self.assertIn("Complete", task_index_rows[0])
        self.assertNotIn("Pending", task_index_rows[0])

    def test_completed_at_injected_for_determinism(self):
        """--completed-at is respected; no live datetime.now in the output."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        args = _make_fake_args(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            completed_at="2099-01-01T00:00:00Z",
        )
        cmd_mark_complete(args)

        result_text = task_file.read_text()
        self.assertIn("2099-01-01T00:00:00Z", result_text)

    def test_files_list_appears_in_completion_notes(self):
        """Multiple files in --files are comma-joined in 'Files changed'."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        args = _make_fake_args(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            files=json.dumps(["src/a.py", "src/b.py"]),
            completed_at="2026-06-01T12:00:00Z",
        )
        cmd_mark_complete(args)

        result_text = task_file.read_text()
        self.assertIn("src/a.py", result_text)
        self.assertIn("src/b.py", result_text)

    def test_atomic_write_replaces_original(self):
        """After mark-complete the task file is the updated version (not a temp file)."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()
        original_inode = task_file.stat().st_ino

        args = _make_fake_args(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            completed_at="2026-06-01T12:00:00Z",
        )
        cmd_mark_complete(args)

        # The path still exists.
        self.assertTrue(task_file.exists())
        # No leftover temp files in the directory.
        temp_files = list(self.tasks_dir.glob("mark-complete-*.tmp"))
        self.assertEqual(len(temp_files), 0, "No temp files must remain after atomic write")

    def test_missing_task_file_exit_findings(self):
        """Missing task file → exit EXIT_FINDINGS, stderr message."""
        readme = self._write_real_readme()

        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args(
                task_file=str(self.tasks_dir / "nonexistent.md"),
                index=str(readme),
                number="001",
                completed_at="2026-06-01T12:00:00Z",
            )
            rc = cmd_mark_complete(args)
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIn("not found", err)

    def test_missing_index_file_exit_findings(self):
        """Missing index file → exit EXIT_FINDINGS, stderr message."""
        task_file = self._write_real_task_file()

        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args(
                task_file=str(task_file),
                index=str(self.tasks_dir / "nonexistent-README.md"),
                number="001",
                completed_at="2026-06-01T12:00:00Z",
            )
            rc = cmd_mark_complete(args)
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIn("not found", err)

    def test_invalid_files_json_exit_err(self):
        """Invalid --files JSON → exit EXIT_ERR."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args(
                task_file=str(task_file),
                index=str(readme),
                number="001",
                files="not-json",
                completed_at="2026-06-01T12:00:00Z",
            )
            rc = cmd_mark_complete(args)
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_ERR)

    def test_emits_json_marked_true(self):
        """Successful call emits {"marked": true} JSON to stdout."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            args = _make_fake_args(
                task_file=str(task_file),
                index=str(readme),
                number="001",
                completed_at="2026-06-01T12:00:00Z",
            )
            rc = cmd_mark_complete(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        self.assertEqual(rc, EXIT_OK)
        result = json.loads(output.strip())
        self.assertTrue(result["marked"])

    def test_idempotent_double_call(self):
        """Calling mark-complete twice does not corrupt the task file."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        args = _make_fake_args(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            completed_at="2026-06-01T12:00:00Z",
        )
        rc1 = cmd_mark_complete(args)
        rc2 = cmd_mark_complete(args)

        self.assertEqual(rc1, EXIT_OK)
        self.assertEqual(rc2, EXIT_OK)

        result_text = task_file.read_text()
        # Status must be exactly one occurrence of Complete.
        self.assertEqual(result_text.count("**Status**: Complete"), 1)


# ---------------------------------------------------------------------------
# Unit tests — _set_status (generalised setter; underlying _set_status_complete)
# ---------------------------------------------------------------------------


class TestSetStatus(unittest.TestCase):

    def test_pending_becomes_skipped(self):
        text = "**Status**: Pending\n"
        result = _set_status(text, "Skipped")
        self.assertIn("**Status**: Skipped", result)
        self.assertNotIn("Pending", result)

    def test_in_progress_becomes_skipped(self):
        text = "**Feature**: foo\n**Status**: In Progress\n"
        result = _set_status(text, "Skipped")
        self.assertIn("**Status**: Skipped", result)
        self.assertNotIn("In Progress", result)

    def test_no_status_line_appended_skipped(self):
        text = "# Task 001: Foo\n\n**Feature**: bar\n"
        result = _set_status(text, "Skipped")
        self.assertIn("**Status**: Skipped", result)

    def test_set_status_complete_delegate(self):
        """_set_status_complete still works via _set_status under the hood."""
        text = "**Status**: Pending\n"
        result = _set_status_complete(text)
        self.assertIn("**Status**: Complete", result)

    def test_idempotent_skipped(self):
        """Setting Skipped on an already-Skipped file is a no-op in effect."""
        text = "**Status**: Skipped\n"
        result = _set_status(text, "Skipped")
        self.assertIn("**Status**: Skipped", result)
        self.assertEqual(result.count("**Status**: Skipped"), 1)


# ---------------------------------------------------------------------------
# Integration tests — cmd_mark_skipped
# ---------------------------------------------------------------------------


def _make_fake_args_skipped(**kwargs):
    class _Args:
        pass
    a = _Args()
    a.task_file = kwargs.get("task_file", "")
    a.index = kwargs.get("index", "")
    a.number = kwargs.get("number", "001")
    a.root = kwargs.get("root", ".")
    return a


class TestCmdMarkSkipped(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.tmpdir) / "tasks"
        self.tasks_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_task_file(self, status="Pending"):
        """Write a minimal task .md file with a given status."""
        content = (
            "# Task 001: Define types\n\n"
            "**Feature**: 001-widget\n"
            "**Agent**: backend-engineer\n"
            "**Status**: {status}\n\n"
            "## Done When\n\n"
            "- [ ] Widget exists\n\n"
            "## Completion Notes\n\n"
            "[Filled in by /implement after completion]\n"
            "**Completed**: [date/time]\n"
            "**Files changed**: [actual files]\n"
            "**Contract**: Expects [X/Y verified] | Produces [X/Y verified]\n"
            "**Notes**: [deviations or observations]\n"
        ).format(status=status)
        path = self.tasks_dir / "001-define-types.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_readme(self, status="Pending"):
        """Write a minimal tasks/README.md with a Task Index row."""
        content = (
            "# Tasks: 001-widget\n\n"
            "## Task Index\n\n"
            "| # | Title | Agent | Depends on | Status |\n"
            "|---|-------|-------|-----------|--------|\n"
            "| 001 | Define types | backend-engineer | None | {status} |\n\n"
            "## Risk Assessment\n\n"
            "| Task | Risk | Reason |\n"
            "|------|------|--------|\n"
            "| 001 | Low | Simple |\n"
        ).format(status=status)
        path = self.tasks_dir / "README.md"
        path.write_text(content, encoding="utf-8")
        return path

    def test_status_flips_to_skipped(self):
        """**Status**: Pending → **Status**: Skipped in the task file."""
        task_file = self._write_task_file(status="Pending")
        readme = self._write_readme(status="Pending")

        args = _make_fake_args_skipped(
            task_file=str(task_file),
            index=str(readme),
            number="001",
        )
        rc = cmd_mark_skipped(args)
        self.assertEqual(rc, EXIT_OK)

        text = task_file.read_text(encoding="utf-8")
        self.assertIn("**Status**: Skipped", text)
        self.assertNotIn("**Status**: Pending", text)

    def test_readme_row_status_updated_to_skipped(self):
        """The Task Index row in README.md is updated to Skipped."""
        task_file = self._write_task_file()
        readme = self._write_readme()

        args = _make_fake_args_skipped(
            task_file=str(task_file),
            index=str(readme),
            number="001",
        )
        rc = cmd_mark_skipped(args)
        self.assertEqual(rc, EXIT_OK)

        readme_text = readme.read_text(encoding="utf-8")
        # Find the Task Index row.
        task_index_rows = [
            l for l in readme_text.splitlines()
            if l.startswith("| 001 |") and "backend-engineer" in l
        ]
        self.assertEqual(len(task_index_rows), 1)
        self.assertIn("Skipped", task_index_rows[0])
        self.assertNotIn("Pending", task_index_rows[0])

    def test_risk_assessment_row_not_touched(self):
        """The Risk Assessment row for task 001 must NOT be updated (region-aware)."""
        task_file = self._write_task_file()
        readme = self._write_readme()

        args = _make_fake_args_skipped(
            task_file=str(task_file),
            index=str(readme),
            number="001",
        )
        cmd_mark_skipped(args)

        readme_text = readme.read_text(encoding="utf-8")
        # Risk Assessment rows contain "Low" — should be unchanged.
        risk_rows = [
            l for l in readme_text.splitlines()
            if l.startswith("| 001 |") and "Low" in l
        ]
        self.assertEqual(len(risk_rows), 1)
        self.assertNotIn("Skipped", risk_rows[0])

    def test_completion_notes_not_touched(self):
        """Completion Notes skeleton must NOT be filled (skip ≠ complete)."""
        task_file = self._write_task_file()
        readme = self._write_readme()

        args = _make_fake_args_skipped(
            task_file=str(task_file),
            index=str(readme),
            number="001",
        )
        cmd_mark_skipped(args)

        text = task_file.read_text(encoding="utf-8")
        # Skeleton placeholders must still be present.
        self.assertIn("[Filled in by /implement after completion]", text)
        self.assertIn("[date/time]", text)
        self.assertIn("[actual files]", text)

    def test_done_when_boxes_not_ticked(self):
        """Done-When checkboxes must NOT be ticked (mark-skipped does not verify)."""
        task_file = self._write_task_file()
        readme = self._write_readme()

        args = _make_fake_args_skipped(
            task_file=str(task_file),
            index=str(readme),
            number="001",
        )
        cmd_mark_skipped(args)

        text = task_file.read_text(encoding="utf-8")
        self.assertIn("- [ ] Widget exists", text)

    def test_idempotent_double_call(self):
        """Calling mark-skipped twice leaves the file in valid Skipped state."""
        task_file = self._write_task_file()
        readme = self._write_readme()

        args = _make_fake_args_skipped(
            task_file=str(task_file),
            index=str(readme),
            number="001",
        )
        rc1 = cmd_mark_skipped(args)
        rc2 = cmd_mark_skipped(args)
        self.assertEqual(rc1, EXIT_OK)
        self.assertEqual(rc2, EXIT_OK)

        text = task_file.read_text(encoding="utf-8")
        self.assertEqual(text.count("**Status**: Skipped"), 1)

    def test_missing_row_returns_exit_findings(self):
        """Row not found in Task Index → EXIT_FINDINGS, stderr message."""
        task_file = self._write_task_file()
        readme = self._write_readme()

        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args_skipped(
                task_file=str(task_file),
                index=str(readme),
                number="099",  # No such row.
            )
            rc = cmd_mark_skipped(args)
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIn("099", err)

    def test_missing_task_file_returns_exit_findings(self):
        """Task file not found → EXIT_FINDINGS, stderr message."""
        readme = self._write_readme()

        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args_skipped(
                task_file=str(self.tasks_dir / "nonexistent.md"),
                index=str(readme),
                number="001",
            )
            rc = cmd_mark_skipped(args)
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIn("not found", err)

    def test_missing_index_file_returns_exit_findings(self):
        """Index file not found → EXIT_FINDINGS, stderr message."""
        task_file = self._write_task_file()

        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args_skipped(
                task_file=str(task_file),
                index=str(self.tasks_dir / "no-readme.md"),
                number="001",
            )
            rc = cmd_mark_skipped(args)
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIn("not found", err)

    def test_emits_json_marked_skipped_true(self):
        """Successful call emits {"marked_skipped": true} to stdout."""
        task_file = self._write_task_file()
        readme = self._write_readme()

        import io, contextlib
        buf = io.StringIO()
        args = _make_fake_args_skipped(
            task_file=str(task_file),
            index=str(readme),
            number="001",
        )
        with contextlib.redirect_stdout(buf):
            rc = cmd_mark_skipped(args)

        self.assertEqual(rc, EXIT_OK)
        result = json.loads(buf.getvalue().strip())
        self.assertTrue(result["marked_skipped"])

    def test_no_temp_files_remain_after_write(self):
        """No mark-skipped-*.tmp files left after write (F3: prefix is mark-skipped-)."""
        task_file = self._write_task_file()
        readme = self._write_readme()

        args = _make_fake_args_skipped(
            task_file=str(task_file),
            index=str(readme),
            number="001",
        )
        cmd_mark_skipped(args)

        # After F3: mark-skipped uses prefix "mark-skipped-", not "mark-complete-".
        skipped_temp_files = list(self.tasks_dir.glob("mark-skipped-*.tmp"))
        self.assertEqual(
            len(skipped_temp_files), 0,
            "No mark-skipped-*.tmp files must remain after atomic write",
        )
        # Also confirm mark-complete-*.tmp was never written by mark-skipped.
        complete_temp_files = list(self.tasks_dir.glob("mark-complete-*.tmp"))
        self.assertEqual(
            len(complete_temp_files), 0,
            "mark-skipped must not leave mark-complete-*.tmp temp files",
        )


# ---------------------------------------------------------------------------
# Unit tests — _tick_done_when_boxes with --unverified-box logic
# ---------------------------------------------------------------------------


_MULTI_BOX_SECTION = (
    "## Done When\n\n"
    "- [ ] Type checker passes on changed files\n"
    "- [ ] Lint passes on changed files\n"
    "- [ ] Unit tests pass\n"
    "- [ ] No debug artifacts remain\n"
    "\n"
    "## Completion Notes\n\n"
    "nothing\n"
)


class TestTickDoneWhenBoxesUnverified(unittest.TestCase):
    """Tests for the new unverified_substrings parameter of _tick_done_when_boxes."""

    # -------------------------------------------------------------------
    # 1. Default (no unverified_substrings): byte-identical to pre-change
    #    all-tick behavior for a multi-box fixture.
    # -------------------------------------------------------------------

    def test_default_no_unverified_all_ticked(self):
        """Default call (no arg): every box ticked, no annotations."""
        text = _MULTI_BOX_SECTION
        result = _tick_done_when_boxes(text)
        self.assertIn("- [x] Type checker passes on changed files", result)
        self.assertIn("- [x] Lint passes on changed files", result)
        self.assertIn("- [x] Unit tests pass", result)
        self.assertIn("- [x] No debug artifacts remain", result)
        self.assertNotIn("- [ ]", result.split("## Completion Notes")[0])
        self.assertNotIn(_UNVERIFIED_ANNOTATION, result)

    def test_default_byte_identical_to_pre_change_behavior(self):
        """No unverified_substrings: output is byte-identical to old all-tick path.

        The old code ticked only `- [ ]` boxes via _UNCHECKED_BOX.sub.
        The new fast path must produce the exact same output.
        """
        # Build a fixture with mixed already-ticked and unticked boxes.
        text = (
            "## Done When\n\n"
            "- [x] Already done\n"
            "- [ ] Still to do\n"
            "\n"
            "## Completion Notes\n"
        )
        result_none = _tick_done_when_boxes(text, None)
        result_empty = _tick_done_when_boxes(text, [])
        # Both must be identical.
        self.assertEqual(result_none, result_empty)
        # Already-ticked box untouched; unticked box ticked.
        self.assertIn("- [x] Already done", result_none)
        self.assertIn("- [x] Still to do", result_none)
        self.assertNotIn(_UNVERIFIED_ANNOTATION, result_none)

    # -------------------------------------------------------------------
    # 2. One --unverified-box matching exactly one box.
    # -------------------------------------------------------------------

    def test_one_unverified_box_annotated_rest_ticked(self):
        """One matching substring: that box stays unticked + annotated; others ticked."""
        text = _MULTI_BOX_SECTION
        result = _tick_done_when_boxes(text, ["Type checker"])
        # Matching box: unticked + annotated.
        self.assertIn(
            "- [ ] Type checker passes on changed files" + _UNVERIFIED_ANNOTATION,
            result,
        )
        # Non-matching boxes: ticked, no annotation.
        self.assertIn("- [x] Lint passes on changed files", result)
        self.assertNotIn(
            "- [x] Lint passes on changed files" + _UNVERIFIED_ANNOTATION,
            result,
        )
        self.assertIn("- [x] Unit tests pass", result)
        self.assertIn("- [x] No debug artifacts remain", result)

    # -------------------------------------------------------------------
    # 3. Multiple --unverified-box values.
    # -------------------------------------------------------------------

    def test_multiple_unverified_boxes_all_annotated(self):
        """Two substrings matching two different boxes: both left unticked + annotated."""
        text = _MULTI_BOX_SECTION
        result = _tick_done_when_boxes(text, ["Type checker", "Lint passes"])
        self.assertIn(
            "- [ ] Type checker passes on changed files" + _UNVERIFIED_ANNOTATION,
            result,
        )
        self.assertIn(
            "- [ ] Lint passes on changed files" + _UNVERIFIED_ANNOTATION,
            result,
        )
        # Remaining boxes ticked.
        self.assertIn("- [x] Unit tests pass", result)
        self.assertIn("- [x] No debug artifacts remain", result)

    # -------------------------------------------------------------------
    # 4. Substring matching MULTIPLE boxes.
    # -------------------------------------------------------------------

    def test_substring_matches_multiple_boxes(self):
        """A substring that matches several boxes leaves ALL of them unticked + annotated."""
        text = (
            "## Done When\n\n"
            "- [ ] Type checker passes on changed files\n"
            "- [ ] Type checker passes on all files\n"
            "- [ ] Lint passes\n"
            "\n"
        )
        result = _tick_done_when_boxes(text, ["Type checker"])
        self.assertIn(
            "- [ ] Type checker passes on changed files" + _UNVERIFIED_ANNOTATION,
            result,
        )
        self.assertIn(
            "- [ ] Type checker passes on all files" + _UNVERIFIED_ANNOTATION,
            result,
        )
        # Non-matching box ticked.
        self.assertIn("- [x] Lint passes", result)

    # -------------------------------------------------------------------
    # 5. Substring that matches NO box: all ticked, no error.
    # -------------------------------------------------------------------

    def test_unmatched_substring_all_ticked_no_error(self):
        """Substring matching no box: all boxes ticked, no annotation, no error."""
        text = _MULTI_BOX_SECTION
        result = _tick_done_when_boxes(text, ["nonexistent-gate-xyz"])
        self.assertIn("- [x] Type checker passes on changed files", result)
        self.assertIn("- [x] Lint passes on changed files", result)
        self.assertIn("- [x] Unit tests pass", result)
        self.assertNotIn(_UNVERIFIED_ANNOTATION, result)

    # -------------------------------------------------------------------
    # 6. Idempotency / repair re-run semantics.
    # -------------------------------------------------------------------

    def test_idempotent_same_unverified_no_double_append(self):
        """Re-running with same --unverified-box does NOT double-append the annotation."""
        text = _MULTI_BOX_SECTION
        first = _tick_done_when_boxes(text, ["Type checker"])
        second = _tick_done_when_boxes(first, ["Type checker"])
        # Annotation must appear exactly once per matching line.
        ann = _UNVERIFIED_ANNOTATION
        for line in second.splitlines():
            if "Type checker" in line:
                count = line.count(ann)
                self.assertEqual(
                    count, 1,
                    "Annotation must appear exactly once, got {0} in: {1!r}".format(count, line),
                )

    def test_repair_rerun_strips_annotation_when_now_verified(self):
        """Re-running WITHOUT the substring ticks the box AND strips the annotation."""
        text = _MULTI_BOX_SECTION
        # First run: mark Type checker as unverified.
        after_first = _tick_done_when_boxes(text, ["Type checker"])
        self.assertIn(
            "- [ ] Type checker passes on changed files" + _UNVERIFIED_ANNOTATION,
            after_first,
        )
        # Second run: no unverified_substrings — everything now verified.
        after_second = _tick_done_when_boxes(after_first, [])
        self.assertIn("- [x] Type checker passes on changed files", after_second)
        self.assertNotIn(_UNVERIFIED_ANNOTATION, after_second)

    def test_idempotent_already_ticked_box_with_unverified_becomes_unticked(self):
        """If a box is already `- [x]` and matched as unverified, it is forced unticked."""
        text = (
            "## Done When\n\n"
            "- [x] Type checker passes on changed files\n"
            "- [ ] Lint passes\n"
            "\n"
        )
        result = _tick_done_when_boxes(text, ["Type checker"])
        self.assertIn(
            "- [ ] Type checker passes on changed files" + _UNVERIFIED_ANNOTATION,
            result,
        )
        # Lint ticked (not in unverified list).
        self.assertIn("- [x] Lint passes", result)

    # -------------------------------------------------------------------
    # 7. Boxes outside Done When section are never touched.
    # -------------------------------------------------------------------

    def test_boxes_outside_done_when_not_touched_with_unverified(self):
        """Boxes in Description or other sections are never touched even with unverified."""
        text = (
            "## Description\n\n"
            "- [ ] Type checker not a condition here\n\n"
            "## Done When\n\n"
            "- [ ] Type checker passes on changed files\n"
            "- [ ] Lint passes\n\n"
            "## Completion Notes\n\n"
            "nothing\n"
        )
        result = _tick_done_when_boxes(text, ["Type checker"])
        # Description box must remain untouched (not ticked, not annotated).
        self.assertIn("- [ ] Type checker not a condition here", result)
        # The Description box must not have the annotation.
        desc_line = [
            l for l in result.splitlines()
            if "Type checker not a condition here" in l
        ]
        self.assertEqual(len(desc_line), 1)
        self.assertNotIn(_UNVERIFIED_ANNOTATION, desc_line[0])
        # Done When box matched: unticked + annotated.
        self.assertIn(
            "- [ ] Type checker passes on changed files" + _UNVERIFIED_ANNOTATION,
            result,
        )
        # Lint: ticked.
        self.assertIn("- [x] Lint passes", result)

    # -------------------------------------------------------------------
    # 8. CRLF fixture: consistent line endings after annotation.
    # -------------------------------------------------------------------

    def test_crlf_fixture_consistent_line_endings_with_unverified(self):
        """CRLF input: matched box stays CRLF after annotation; no mixed endings.

        When the section text uses \\r\\n endings, the _ANY_BOX regex (re.MULTILINE
        with ``.*``) captures the trailing \\r into group(1).  The fix strips the \\r
        before matching/rewriting and re-attaches it at the end, so the result
        is consistently \\r\\n throughout.
        """
        # Build a CRLF section manually.  The Done When heading + boxes use \\r\\n.
        crlf = "\r\n"
        text = (
            "## Done When" + crlf +
            crlf +
            "- [ ] Type checker passes on changed files" + crlf +
            "- [ ] Lint passes on changed files" + crlf +
            crlf +
            "## Completion Notes" + crlf +
            "nothing" + crlf
        )

        result = _tick_done_when_boxes(text, ["Type checker"])

        # Split on \n to get raw lines (each will end with \r for CRLF lines).
        raw_lines = result.split("\n")
        # Gather all lines that contain a checkbox (ticked or unticked).
        box_lines = [l for l in raw_lines if "- [" in l]
        self.assertTrue(box_lines, "Must have box lines in the result")

        for raw_line in box_lines:
            # Every box line must end with \r (CRLF, before the \n was split off).
            self.assertTrue(
                raw_line.endswith("\r"),
                "Box line must end with \\r to preserve \\r\\n: {0!r}".format(raw_line),
            )

        # The matched box must be unticked and annotated (annotation before the \r).
        matched = [l for l in raw_lines if "Type checker" in l]
        self.assertEqual(len(matched), 1)
        core = matched[0].rstrip("\r")
        self.assertTrue(
            core.startswith("- [ ] Type checker"),
            "Matched box must be unticked: {0!r}".format(core),
        )
        self.assertTrue(
            core.endswith(_UNVERIFIED_ANNOTATION),
            "Matched box must carry annotation: {0!r}".format(core),
        )

        # Lint box must be ticked and end with \r.
        lint_lines = [l for l in raw_lines if "Lint passes" in l]
        self.assertEqual(len(lint_lines), 1)
        self.assertTrue(
            lint_lines[0].startswith("- [x] Lint passes"),
            "Lint box must be ticked: {0!r}".format(lint_lines[0]),
        )
        self.assertTrue(
            lint_lines[0].endswith("\r"),
            "Lint box must end with \\r: {0!r}".format(lint_lines[0]),
        )


# ---------------------------------------------------------------------------
# Integration tests — cmd_mark_complete with --unverified-box
# ---------------------------------------------------------------------------


def _make_fake_args_with_unverified(**kwargs):
    """Like _make_fake_args but includes unverified_box."""
    a = _make_fake_args(**kwargs)
    # unverified_box is a list (from action="append") or None.
    a.unverified_box = kwargs.get("unverified_box", None)
    return a


class TestCmdMarkCompleteUnverifiedBox(unittest.TestCase):
    """Integration tests for mark-complete with --unverified-box."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.tmpdir) / "tasks"
        self.tasks_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_real_task_file(self, number="001", title="Define types", feature="001-widget"):
        content = _render_task_file(number=number, title=title, feature=feature)
        path = self.tasks_dir / "{0}-{1}.md".format(number, title.replace(" ", "-").lower())
        path.write_text(content)
        return path

    def _write_real_readme(self, feature="001-widget"):
        content = _render_tasks_index(feature=feature)
        content = content.replace(
            "| 001 | [title] | [agent] | None | Pending |",
            "| 001 | Define types | backend-engineer | None | Pending |",
        )
        path = self.tasks_dir / "README.md"
        path.write_text(content)
        return path

    def _first_done_when_box_line(self, task_text):
        """Return the first complete box line (e.g. '- [ ] ...') in the Done When section."""
        in_dw = False
        for line in task_text.splitlines():
            if line.startswith("## Done When"):
                in_dw = True
            elif line.startswith("## ") and in_dw:
                break
            if in_dw and line.startswith("- [ ]"):
                return line
        return None

    def test_no_unverified_box_all_ticked_default_behavior(self):
        """Without --unverified-box the default all-tick behavior is preserved."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        args = _make_fake_args_with_unverified(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            completed_at="2026-06-01T12:00:00Z",
            unverified_box=None,
        )
        rc = cmd_mark_complete(args)
        self.assertEqual(rc, EXIT_OK)

        result_text = task_file.read_text()
        # No unchecked boxes in Done When.
        in_done_when = False
        for line in result_text.splitlines():
            if line.startswith("## Done When"):
                in_done_when = True
            elif line.startswith("## ") and in_done_when:
                in_done_when = False
            if in_done_when:
                self.assertNotIn("- [ ]", line)
        # No annotations.
        self.assertNotIn(_UNVERIFIED_ANNOTATION, result_text)

    def test_unverified_box_arg_leaves_box_unticked_and_annotated(self):
        """--unverified-box matching a substring leaves that box unticked + annotated."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        # Use a substring from the real render-task-file Done When boxes.
        # The skeleton has known static boxes such as:
        #   "- [ ] Type checker passes on changed files ..."
        # Use a literal substring that definitely appears in the rendered output.
        # We use a known stable box from the skeleton.
        original = task_file.read_text()
        box_line = self._first_done_when_box_line(original)
        self.assertIsNotNone(box_line, "Skeleton must have at least one Done When box")

        # substring: first 12 chars of the box line content (after "- [ ] ").
        # We use the whole box line content up to 12 chars as a substring to
        # match against the full line (which includes "- [ ] " prefix).
        box_content = box_line[len("- [ ] "):]  # strip the checkbox prefix exactly
        # Use a 12-char prefix of the content as the unverified substring.
        substring = box_content[:12]

        args = _make_fake_args_with_unverified(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            completed_at="2026-06-01T12:00:00Z",
            unverified_box=[substring],
        )
        rc = cmd_mark_complete(args)
        self.assertEqual(rc, EXIT_OK)

        result_text = task_file.read_text()
        # The targeted box must be unticked and have the annotation.
        # We check: a line that (a) contains "- [ ] ", (b) contains box_content,
        # and (c) contains _UNVERIFIED_ANNOTATION.
        matching_lines = [
            l for l in result_text.splitlines()
            if box_content in l and _UNVERIFIED_ANNOTATION in l
        ]
        self.assertTrue(
            matching_lines,
            "Targeted box must be unticked and annotated; box_content={0!r}; "
            "substring={1!r}".format(box_content, substring),
        )
        # Also confirm the box is unticked (- [ ]).
        self.assertTrue(
            any(l.startswith("- [ ]") for l in matching_lines),
            "Targeted box must be unticked (- [ ])",
        )

    def test_emits_json_marked_true_with_unverified_box(self):
        """--unverified-box does not change the exit code or stdout JSON shape."""
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        import io
        original = task_file.read_text()
        box_line = self._first_done_when_box_line(original)
        substring = box_line[len("- [ ] "):][:12] if box_line else "no-op-xyz"

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            args = _make_fake_args_with_unverified(
                task_file=str(task_file),
                index=str(readme),
                number="001",
                completed_at="2026-06-01T12:00:00Z",
                unverified_box=[substring],
            )
            rc = cmd_mark_complete(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        self.assertEqual(rc, EXIT_OK)
        result = json.loads(output.strip())
        self.assertTrue(result["marked"])

    def test_empty_string_unverified_box_is_filtered_all_ticked(self):
        """unverified_box=[""] is filtered: all boxes are ticked, no annotations.

        An empty string would match every box via ``"" in x``.  The filter in
        cmd_mark_complete strips whitespace-only substrings before passing the
        list to _tick_done_when_boxes, so the result is identical to the default
        no-flag behavior.
        """
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        args = _make_fake_args_with_unverified(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            completed_at="2026-06-01T12:00:00Z",
            unverified_box=[""],
        )
        rc = cmd_mark_complete(args)
        self.assertEqual(rc, EXIT_OK)

        result_text = task_file.read_text()
        # All Done When boxes must be ticked (empty string was filtered out).
        in_done_when = False
        for line in result_text.splitlines():
            if line.startswith("## Done When"):
                in_done_when = True
            elif line.startswith("## ") and in_done_when:
                in_done_when = False
            if in_done_when:
                self.assertNotIn(
                    "- [ ]", line,
                    "Empty-string unverified_box must not leave any box unticked",
                )
        # No annotation must appear.
        self.assertNotIn(
            _UNVERIFIED_ANNOTATION,
            result_text,
            "Empty-string unverified_box must not add any annotation",
        )

    def test_repair_rerun_strips_annotation_when_verified(self):
        """File-I/O repair-rerun: first call annotates; second call (no flag) ticks and strips.

        Workflow:
          1. cmd_mark_complete with unverified_box=[<substring>] — box left
             unticked + annotated.
          2. cmd_mark_complete with unverified_box=None — box ticked, annotation
             stripped from file.

        After step 2 the file must have the box ticked and no annotation present.
        """
        task_file = self._write_real_task_file()
        readme = self._write_real_readme()

        original = task_file.read_text()
        box_line = self._first_done_when_box_line(original)
        self.assertIsNotNone(box_line, "Skeleton must have at least one Done When box")
        box_content = box_line[len("- [ ] "):]
        substring = box_content[:12]

        # --- First call: mark the box unverified. ---
        args_first = _make_fake_args_with_unverified(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            completed_at="2026-06-01T12:00:00Z",
            unverified_box=[substring],
        )
        rc1 = cmd_mark_complete(args_first)
        self.assertEqual(rc1, EXIT_OK)

        after_first = task_file.read_text()
        # The targeted box must be unticked and annotated.
        self.assertTrue(
            any(
                box_content in l and _UNVERIFIED_ANNOTATION in l
                for l in after_first.splitlines()
            ),
            "After first call: box must be annotated",
        )

        # --- Second call: no unverified_box → repair path. ---
        # The README row was already updated to Complete; we need a fresh one
        # for the second call to succeed.  Rewrite the README with the row back
        # to Complete (the re-run is idempotent on README status).
        # Simply use the same index — _update_readme_row's second pass is a no-op
        # once the row already shows Complete (it still returns EXIT_OK).
        args_second = _make_fake_args_with_unverified(
            task_file=str(task_file),
            index=str(readme),
            number="001",
            completed_at="2026-06-01T12:00:00Z",
            unverified_box=None,
        )
        rc2 = cmd_mark_complete(args_second)
        self.assertEqual(rc2, EXIT_OK)

        after_second = task_file.read_text()
        # The box must now be ticked.
        self.assertTrue(
            any(
                "- [x]" in l and box_content in l
                for l in after_second.splitlines()
            ),
            "After second call: box must be ticked; box_content={0!r}".format(box_content),
        )
        # The annotation must be gone.
        self.assertNotIn(
            _UNVERIFIED_ANNOTATION,
            after_second,
            "After second call: annotation must be stripped",
        )


if __name__ == "__main__":
    unittest.main()
