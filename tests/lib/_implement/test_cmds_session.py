"""Tests for src/devforge/lib/_implement/_cmds_session.py.

Coverage:

  _build_session_state:
    - Header fields present (feature, progress, updated).
    - Recent task modifications section present with items.
    - Recent decisions section present with items.
    - Empty tasks → "(none)" placeholder.
    - Empty decisions → "(none)" placeholder.
    - Sliding window: >3 tasks → only last 3 kept.
    - Sliding window: >3 decisions → only last 3 kept.
    - Result is ≤ 40 lines (hard cap).

  _build_memory_entry:
    - Format: `- **[Task NNN / feature]**: <title> — completed. _(Task NNN)_`.
    - Number and feature correctly embedded.

  cmd_update_session_state (integration, real tempdir):
    - session-state.md created on first call.
    - session-state.md FULLY overwritten on second call (not appended).
    - session-state.md is ≤ 40 lines after each call.
    - memory.md gets exactly one new line per call.
    - memory.md created if absent.
    - memory.md existing content is preserved (line appended, not replaced).
    - Sliding window: 5 tasks passed → only last 3 in session-state.md.
    - --timestamp injected → appears in session-state.md (deterministic).
    - --last-task-number + --last-task-title absent → memory.md not appended.
    - --feature required → exit 1 on absence.
    - --completed-count must be integer → exit 1 on non-integer.
    - --recent-tasks invalid JSON → exit 1.
    - --recent-decisions invalid JSON → exit 1.
    - Output JSON is {"updated": true}.

Stdlib only. Python 3.8+.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------

_LIB_DIR = str(Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _implement._cmds_session import (  # noqa: E402
    _build_session_state,
    _build_memory_entry,
    _insert_line_under_section,
    _append_under_section,
    cmd_update_session_state,
    EXIT_OK,
    EXIT_ERR,
    _MAX_LINES,
    _WINDOW_SIZE,
)


# ---------------------------------------------------------------------------
# Fake args helper
# ---------------------------------------------------------------------------


def _make_fake_args(**kwargs):
    class _Args:
        pass
    a = _Args()
    a.feature = kwargs.get("feature", "001-widget-catalog")
    a.completed_count = kwargs.get("completed_count", 1)
    a.total_count = kwargs.get("total_count", 3)
    a.last_task_number = kwargs.get("last_task_number", "001")
    a.last_task_title = kwargs.get("last_task_title", "Define types")
    a.recent_tasks = kwargs.get("recent_tasks", "[]")
    a.recent_decisions = kwargs.get("recent_decisions", "[]")
    a.root = kwargs.get("root", ".")
    a.timestamp = kwargs.get("timestamp", "2026-06-01T12:00:00Z")
    return a


# ---------------------------------------------------------------------------
# Unit tests — _build_session_state
# ---------------------------------------------------------------------------


class TestBuildSessionState(unittest.TestCase):

    def _build(self, tasks=None, decisions=None, feature="001-widget",
               completed=1, total=3, timestamp="2026-06-01T12:00:00Z"):
        return _build_session_state(
            feature=feature,
            completed_count=completed,
            total_count=total,
            recent_tasks=tasks or [],
            recent_decisions=decisions or [],
            timestamp=timestamp,
        )

    def test_header_fields_present(self):
        content = self._build()
        self.assertIn("# Session State — /implement", content)
        self.assertIn("**Feature**: 001-widget", content)
        self.assertIn("**Progress**: 1/3 tasks complete", content)
        self.assertIn("**Updated**: 2026-06-01T12:00:00Z", content)

    def test_recent_tasks_section_present(self):
        tasks = [{"number": "001", "title": "Define types", "status": "Complete"}]
        content = self._build(tasks=tasks)
        self.assertIn("## Recent Task Modifications", content)
        self.assertIn("[001] Define types (Complete)", content)

    def test_recent_decisions_section_present(self):
        decisions = ["Used TypeScript strict mode."]
        content = self._build(decisions=decisions)
        self.assertIn("## Recent Decisions", content)
        self.assertIn("Used TypeScript strict mode.", content)

    def test_empty_tasks_shows_placeholder(self):
        content = self._build(tasks=[])
        self.assertIn("(none)", content)

    def test_empty_decisions_shows_placeholder(self):
        content = self._build(decisions=[])
        self.assertIn("(none)", content)

    def test_sliding_window_tasks_keeps_last_3(self):
        """More than 3 tasks: only the last 3 appear."""
        tasks = [
            {"number": "001", "title": "A", "status": "Complete"},
            {"number": "002", "title": "B", "status": "Complete"},
            {"number": "003", "title": "C", "status": "Complete"},
            {"number": "004", "title": "D", "status": "Complete"},
            {"number": "005", "title": "E", "status": "Complete"},
        ]
        content = self._build(tasks=tasks)
        # Tasks 001 and 002 must NOT appear.
        self.assertNotIn("[001]", content)
        self.assertNotIn("[002]", content)
        # Tasks 003, 004, 005 must appear.
        self.assertIn("[003]", content)
        self.assertIn("[004]", content)
        self.assertIn("[005]", content)

    def test_sliding_window_decisions_keeps_last_3(self):
        """More than 3 decisions: only the last 3 appear."""
        decisions = ["D1", "D2", "D3", "D4", "D5"]
        content = self._build(decisions=decisions)
        self.assertNotIn("D1", content)
        self.assertNotIn("D2", content)
        self.assertIn("D3", content)
        self.assertIn("D4", content)
        self.assertIn("D5", content)

    def test_result_at_most_40_lines(self):
        """Session state content must be ≤ 40 lines."""
        tasks = [
            {"number": str(i).zfill(3), "title": "T{0}".format(i), "status": "Complete"}
            for i in range(1, 6)
        ]
        decisions = ["D{0}".format(i) for i in range(1, 6)]
        content = self._build(tasks=tasks, decisions=decisions)
        line_count = len(content.splitlines())
        self.assertLessEqual(line_count, _MAX_LINES,
                             "session-state.md must be <= {0} lines, got {1}".format(
                                 _MAX_LINES, line_count))

    def test_window_size_constant_is_3(self):
        self.assertEqual(_WINDOW_SIZE, 3)

    def test_max_lines_constant_is_40(self):
        self.assertEqual(_MAX_LINES, 40)


# ---------------------------------------------------------------------------
# Unit tests — _build_memory_entry
# ---------------------------------------------------------------------------


class TestBuildMemoryEntry(unittest.TestCase):

    def test_format_matches_convention(self):
        """Entry follows the `- **[AREA]**: ... _(Task N / Feature NNN)_` convention."""
        entry = _build_memory_entry("001-widget-catalog", "001", "Define types")
        self.assertEqual(
            entry,
            "- **[Task 001 / 001-widget-catalog]**: Define types — completed. _(Task 001)_",
        )

    def test_number_embedded_correctly(self):
        entry = _build_memory_entry("002-auth", "002", "Build login form")
        self.assertIn("Task 002", entry)
        self.assertIn("002-auth", entry)
        self.assertIn("Build login form", entry)

    def test_is_single_line(self):
        entry = _build_memory_entry("001-widget", "001", "Define types")
        self.assertNotIn("\n", entry)


# ---------------------------------------------------------------------------
# Integration tests — cmd_update_session_state
# ---------------------------------------------------------------------------


class TestCmdUpdateSessionState(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        self.devforge_dir = self.root / ".devforge"
        self.devforge_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @property
    def session_state_path(self):
        return self.devforge_dir / "session-state.md"

    @property
    def memory_path(self):
        return self.devforge_dir / "memory.md"

    def test_session_state_created_on_first_call(self):
        args = _make_fake_args(root=str(self.root))
        rc = cmd_update_session_state(args)
        self.assertEqual(rc, EXIT_OK)
        self.assertTrue(self.session_state_path.exists())

    def test_session_state_fully_overwritten_on_second_call(self):
        """Second call must overwrite, not append, so the file stays fixed-size."""
        args1 = _make_fake_args(
            root=str(self.root),
            feature="001-widget",
            completed_count=1,
            total_count=3,
            timestamp="2026-06-01T10:00:00Z",
        )
        cmd_update_session_state(args1)
        first_content = self.session_state_path.read_text()

        args2 = _make_fake_args(
            root=str(self.root),
            feature="001-widget",
            completed_count=2,
            total_count=3,
            timestamp="2026-06-01T11:00:00Z",
        )
        cmd_update_session_state(args2)
        second_content = self.session_state_path.read_text()

        # Second content must not contain the first timestamp.
        self.assertNotIn("10:00:00Z", second_content)
        self.assertIn("11:00:00Z", second_content)
        # The file is NOT an accumulation of both calls.
        self.assertNotIn("10:00:00Z", second_content,
                         "session-state.md must be fully overwritten, not appended")

    def test_session_state_at_most_40_lines(self):
        args = _make_fake_args(
            root=str(self.root),
            recent_tasks=json.dumps([
                {"number": str(i).zfill(3), "title": "Task {0}".format(i), "status": "Complete"}
                for i in range(1, 6)
            ]),
            recent_decisions=json.dumps(["D{0}".format(i) for i in range(1, 6)]),
        )
        rc = cmd_update_session_state(args)
        self.assertEqual(rc, EXIT_OK)

        content = self.session_state_path.read_text()
        line_count = len(content.splitlines())
        self.assertLessEqual(line_count, _MAX_LINES,
                             "session-state.md must be <= {0} lines".format(_MAX_LINES))

    def test_memory_md_gets_one_new_entry(self):
        """Each call writes exactly one task entry line under ## Task Outcomes."""
        args = _make_fake_args(
            root=str(self.root),
            last_task_number="001",
            last_task_title="Define types",
            feature="001-widget",
        )
        rc = cmd_update_session_state(args)
        self.assertEqual(rc, EXIT_OK)

        content = self.memory_path.read_text()
        self.assertIn("## Task Outcomes", content)
        # The entry line is present.
        self.assertIn("Define types", content)
        # Exactly one task entry line (starts with "- **[Task").
        entry_lines = [
            l for l in content.splitlines()
            if l.startswith("- **[Task")
        ]
        self.assertEqual(len(entry_lines), 1)

    def test_memory_md_created_if_absent(self):
        """memory.md is created when it does not exist yet."""
        self.assertFalse(self.memory_path.exists())

        args = _make_fake_args(root=str(self.root))
        cmd_update_session_state(args)

        self.assertTrue(self.memory_path.exists())

    def test_memory_md_existing_content_preserved(self):
        """Existing memory.md content is preserved when a new entry is appended."""
        existing = "- **[Old entry]**: something old.\n"
        self.memory_path.write_text(existing)

        args = _make_fake_args(
            root=str(self.root),
            last_task_number="002",
            last_task_title="Build form",
            feature="001-widget",
        )
        cmd_update_session_state(args)

        content = self.memory_path.read_text()
        self.assertIn("something old", content)
        self.assertIn("Build form", content)

    def test_two_calls_append_two_memory_entries(self):
        """Two calls should produce two task entry lines under ## Task Outcomes."""
        args1 = _make_fake_args(
            root=str(self.root),
            last_task_number="001",
            last_task_title="Define types",
            feature="001-widget",
        )
        args2 = _make_fake_args(
            root=str(self.root),
            last_task_number="002",
            last_task_title="Build form",
            feature="001-widget",
        )
        cmd_update_session_state(args1)
        cmd_update_session_state(args2)

        content = self.memory_path.read_text()
        # Exactly two task entry lines (both start with "- **[Task").
        entry_lines = [
            l for l in content.splitlines()
            if l.startswith("- **[Task")
        ]
        self.assertEqual(len(entry_lines), 2)
        self.assertIn("Define types", entry_lines[0])
        self.assertIn("Build form", entry_lines[1])

    def test_no_last_task_number_no_memory_append(self):
        """Without --last-task-number, no memory.md entry is written."""
        args = _make_fake_args(
            root=str(self.root),
            last_task_number="",
            last_task_title="",
        )
        cmd_update_session_state(args)

        self.assertFalse(
            self.memory_path.exists(),
            "memory.md must not be created when no task number is given",
        )

    def test_sliding_window_5_tasks_only_last_3_in_session_state(self):
        """5 tasks in --recent-tasks → only last 3 appear in session-state.md."""
        tasks = [
            {"number": str(i).zfill(3), "title": "T{0}".format(i), "status": "Complete"}
            for i in range(1, 6)
        ]
        args = _make_fake_args(
            root=str(self.root),
            recent_tasks=json.dumps(tasks),
        )
        cmd_update_session_state(args)

        content = self.session_state_path.read_text()
        self.assertNotIn("[001]", content)
        self.assertNotIn("[002]", content)
        self.assertIn("[003]", content)
        self.assertIn("[004]", content)
        self.assertIn("[005]", content)

    def test_timestamp_injected_for_determinism(self):
        """--timestamp appears verbatim in session-state.md."""
        args = _make_fake_args(
            root=str(self.root),
            timestamp="2099-12-31T23:59:59Z",
        )
        cmd_update_session_state(args)

        content = self.session_state_path.read_text()
        self.assertIn("2099-12-31T23:59:59Z", content)

    def test_feature_required(self):
        """Missing --feature returns exit 1 and writes stderr."""
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args(root=str(self.root), feature="")
            rc = cmd_update_session_state(args)
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_ERR)
        self.assertIn("feature", err.lower())

    def test_invalid_recent_tasks_json_exit_err(self):
        """Invalid --recent-tasks JSON returns exit 1."""
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args(root=str(self.root), recent_tasks="not-json")
            rc = cmd_update_session_state(args)
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_ERR)

    def test_invalid_recent_decisions_json_exit_err(self):
        """Invalid --recent-decisions JSON returns exit 1."""
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args(root=str(self.root), recent_decisions="bad")
            rc = cmd_update_session_state(args)
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_ERR)

    def test_emits_json_updated_true(self):
        """Successful call emits {"updated": true} JSON to stdout."""
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            args = _make_fake_args(root=str(self.root))
            rc = cmd_update_session_state(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        self.assertEqual(rc, EXIT_OK)
        result = json.loads(output.strip())
        self.assertTrue(result["updated"])

    def test_memory_entry_format(self):
        """Memory entry follows the expected convention format, placed under ## Task Outcomes."""
        args = _make_fake_args(
            root=str(self.root),
            last_task_number="003",
            last_task_title="Wire routing",
            feature="002-auth",
        )
        cmd_update_session_state(args)

        content = self.memory_path.read_text()
        # The section heading must be present.
        self.assertIn("## Task Outcomes", content)
        # The entry line must be present verbatim.
        expected_entry = (
            "- **[Task 003 / 002-auth]**: Wire routing — completed. _(Task 003)_"
        )
        self.assertIn(expected_entry, content)
        # The entry must come AFTER the section heading.
        heading_pos = content.index("## Task Outcomes")
        entry_pos = content.index(expected_entry)
        self.assertGreater(entry_pos, heading_pos,
                           "Entry must appear after ## Task Outcomes heading")

    def test_session_state_header_content(self):
        """session-state.md has correct section headings and field values."""
        args = _make_fake_args(
            root=str(self.root),
            feature="003-search",
            completed_count=4,
            total_count=7,
            timestamp="2026-06-01T09:00:00Z",
        )
        cmd_update_session_state(args)

        content = self.session_state_path.read_text()
        self.assertIn("**Feature**: 003-search", content)
        self.assertIn("**Progress**: 4/7 tasks complete", content)
        self.assertIn("**Updated**: 2026-06-01T09:00:00Z", content)
        self.assertIn("## Recent Task Modifications", content)
        self.assertIn("## Recent Decisions", content)


# ---------------------------------------------------------------------------
# Unit tests — _insert_line_under_section (pure function, no I/O)
# ---------------------------------------------------------------------------

_STANDARD_TEMPLATE = """\
# Project Memory

## Architecture Decisions
- Used TypeScript strict mode.

## Known Pitfalls
- Avoid mutating state directly.

## What Worked
- Component isolation.

## What Failed
- Premature optimisation caused regressions.
"""


class TestInsertLineUnderSection(unittest.TestCase):
    """Tests for the pure helper _insert_line_under_section."""

    # ------------------------------------------------------------------
    # Case 1: section absent in standard template — created at EOF
    # ------------------------------------------------------------------

    def test_section_created_when_absent(self):
        """## Task Outcomes is appended when not present."""
        result = _insert_line_under_section(
            _STANDARD_TEMPLATE,
            "## Task Outcomes",
            "- **[Task 001 / 001-widget]**: Define types — completed. _(Task 001)_",
        )
        self.assertIn("## Task Outcomes", result)
        self.assertIn("Define types", result)

    def test_what_failed_section_untouched_when_section_absent(self):
        """## What Failed is not altered when the new section is appended."""
        result = _insert_line_under_section(
            _STANDARD_TEMPLATE,
            "## Task Outcomes",
            "- **[Task 001 / 001-widget]**: Define types — completed. _(Task 001)_",
        )
        # Original ## What Failed content must survive byte-for-byte.
        self.assertIn("## What Failed", result)
        self.assertIn("Premature optimisation caused regressions.", result)
        # The task entry must NOT appear under ## What Failed.
        what_failed_pos = result.index("## What Failed")
        define_types_pos = result.index("Define types")
        self.assertGreater(
            define_types_pos, what_failed_pos + len("## What Failed"),
            "Task entry appeared under ## What Failed — misfiling bug reproduced",
        )
        # Verify the task entry is AFTER ## Task Outcomes.
        task_outcomes_pos = result.index("## Task Outcomes")
        self.assertGreater(define_types_pos, task_outcomes_pos)

    # ------------------------------------------------------------------
    # Case 2: section present — line appended at end of section
    # ------------------------------------------------------------------

    def test_line_appended_at_end_of_existing_section(self):
        """New line lands after existing entries, before the next ## heading."""
        base = (
            "## Architecture Decisions\n"
            "- Decision A.\n"
            "\n"
            "## Task Outcomes\n"
            "- **[Task 001 / feat]**: First task — completed. _(Task 001)_\n"
            "\n"
            "## What Failed\n"
            "- Some failure.\n"
        )
        new_entry = "- **[Task 002 / feat]**: Second task — completed. _(Task 002)_"
        result = _insert_line_under_section(base, "## Task Outcomes", new_entry)

        # Both entries must be present.
        self.assertIn("First task", result)
        self.assertIn("Second task", result)

        # New entry must come BEFORE ## What Failed.
        new_entry_pos = result.index("Second task")
        what_failed_pos = result.index("## What Failed")
        self.assertLess(new_entry_pos, what_failed_pos,
                        "New entry must be inside ## Task Outcomes, before ## What Failed")

        # New entry must come AFTER ## Task Outcomes heading.
        section_pos = result.index("## Task Outcomes")
        self.assertGreater(new_entry_pos, section_pos)

    # ------------------------------------------------------------------
    # Case 3: two sequential inserts accumulate in order
    # ------------------------------------------------------------------

    def test_two_sequential_inserts_accumulate_in_order(self):
        """Two calls via _insert_line_under_section accumulate both entries."""
        entry1 = "- **[Task 001 / feat]**: First — completed. _(Task 001)_"
        entry2 = "- **[Task 002 / feat]**: Second — completed. _(Task 002)_"

        after_first = _insert_line_under_section(
            _STANDARD_TEMPLATE, "## Task Outcomes", entry1
        )
        after_second = _insert_line_under_section(
            after_first, "## Task Outcomes", entry2
        )

        # Both entries present.
        self.assertIn("First", after_second)
        self.assertIn("Second", after_second)

        # Entry 1 appears before entry 2 (insertion order preserved).
        pos1 = after_second.index("First")
        pos2 = after_second.index("Second")
        self.assertLess(pos1, pos2, "First entry must precede second entry")

    # ------------------------------------------------------------------
    # Case 4: file is empty (non-existent file scenario)
    # ------------------------------------------------------------------

    def test_empty_existing_creates_section_plus_line(self):
        """Empty existing content produces section heading + line, no extra blank."""
        result = _insert_line_under_section(
            "",
            "## Task Outcomes",
            "- **[Task 001 / feat]**: Alpha — completed. _(Task 001)_",
        )
        self.assertTrue(result.startswith("## Task Outcomes\n"),
                        "Empty file: section heading must be first line")
        self.assertIn("Alpha", result)

    # ------------------------------------------------------------------
    # Case 5: other sections' content byte-preserved around insertion
    # ------------------------------------------------------------------

    def test_other_sections_byte_preserved(self):
        """Sections other than ## Task Outcomes are untouched after insertion."""
        result = _insert_line_under_section(
            _STANDARD_TEMPLATE,
            "## Task Outcomes",
            "- **[Task 001 / feat]**: X — completed. _(Task 001)_",
        )
        # Every line from the original template must appear unchanged.
        for line in _STANDARD_TEMPLATE.splitlines():
            self.assertIn(line, result,
                          "Original line missing after insertion: {0!r}".format(line))

    # ------------------------------------------------------------------
    # Finding 3: trailing-space heading match
    # ------------------------------------------------------------------

    def test_trailing_space_heading_matched_no_duplicate_section(self):
        """A heading with a trailing space must match — no duplicate section created."""
        # The heading has a trailing space after "Task Outcomes".
        base = (
            "## What Worked\n"
            "- Something good.\n"
            "\n"
            "## Task Outcomes \n"
            "- first entry\n"
        )
        result = _insert_line_under_section(base, "## Task Outcomes", "- second entry")
        # The existing heading must still be present (byte-preserved).
        self.assertIn("## Task Outcomes ", result)
        # A duplicate bare heading must NOT be created.
        self.assertEqual(
            result.count("Task Outcomes"), 1,
            "Trailing-space heading must be matched so no duplicate section is created",
        )
        # Both entries must be present.
        self.assertIn("first entry", result)
        self.assertIn("second entry", result)

    # ------------------------------------------------------------------
    # Finding 4: section is the last in the file (no following ## heading)
    # ------------------------------------------------------------------

    def test_section_present_and_is_last_section_inserts_at_eof(self):
        """Section present AND is last (no following ## heading) → insert at EOF."""
        base = "## What Failed\n- bad.\n\n## Task Outcomes\n- first\n"
        result = _insert_line_under_section(base, "## Task Outcomes", "- second")
        lines = result.splitlines()
        self.assertEqual(lines[-1], "- second")
        self.assertIn("- first", result)

    # ------------------------------------------------------------------
    # Finding 1: fenced code block must not be mis-detected as a heading
    # ------------------------------------------------------------------

    def test_fenced_code_block_heading_not_mis_detected(self):
        """Lines starting with ## inside a fenced block must not be treated as headings.

        Scenario: after ## Task Outcomes, there is a fenced code block whose
        lines include one starting with '## ' (and even '## Task Outcomes').
        The real next heading is ## What Came Next.  The new line must be
        inserted before ## What Came Next, not inside the fence.
        """
        base = (
            "## Task Outcomes\n"
            "- existing entry\n"
            "```\n"
            "## This looks like a heading but is inside a fence\n"
            "## Task Outcomes\n"
            "some code here\n"
            "```\n"
            "\n"
            "## What Came Next\n"
            "- unrelated content\n"
        )
        result = _insert_line_under_section(base, "## Task Outcomes", "- new entry")

        # The fence content must be byte-preserved.
        self.assertIn("## This looks like a heading but is inside a fence", result)
        self.assertIn("some code here", result)

        # The new entry must appear before ## What Came Next.
        new_entry_pos = result.index("- new entry")
        what_came_next_pos = result.index("## What Came Next")
        self.assertLess(
            new_entry_pos, what_came_next_pos,
            "New entry must be inside ## Task Outcomes, not after the real next heading",
        )

        # The new entry must appear after the existing entry.
        existing_pos = result.index("- existing entry")
        self.assertGreater(new_entry_pos, existing_pos)

        # The new entry must NOT appear inside the fence (between the ``` delimiters).
        fence_open = result.index("```\n")
        fence_close = result.rindex("```\n")
        self.assertFalse(
            fence_open < new_entry_pos < fence_close,
            "New entry must not be inserted inside the fenced code block",
        )

    def test_fenced_block_before_target_section_not_mis_detected_as_heading(self):
        """Fenced ## lines before the target section must not mis-detect the heading index."""
        base = (
            "## Notes\n"
            "```\n"
            "## Task Outcomes\n"
            "fake heading inside fence\n"
            "```\n"
            "\n"
            "## Task Outcomes\n"
            "- real entry\n"
        )
        result = _insert_line_under_section(base, "## Task Outcomes", "- appended")

        # Only one ## Task Outcomes section (the real one) — but the fenced one
        # appears as text so count will be 2; what matters is that "appended"
        # appears after the real (second) occurrence.
        real_heading_pos = result.rindex("## Task Outcomes")
        appended_pos = result.index("- appended")
        self.assertGreater(
            appended_pos, real_heading_pos,
            "New entry must be under the real ## Task Outcomes, not the fenced one",
        )
        self.assertIn("- real entry", result)


# ---------------------------------------------------------------------------
# Integration tests — cmd_update_session_state memory.md placement
# ---------------------------------------------------------------------------


class TestUpdateSessionStateMemoryPlacement(unittest.TestCase):
    """Integration tests verifying the ## Task Outcomes placement fix."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        self.devforge_dir = self.root / ".devforge"
        self.devforge_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @property
    def memory_path(self):
        return self.devforge_dir / "memory.md"

    def test_new_entry_under_task_outcomes_not_what_failed(self):
        """Entry must land under ## Task Outcomes, not ## What Failed."""
        self.memory_path.write_text(_STANDARD_TEMPLATE)

        args = _make_fake_args(
            root=str(self.root),
            last_task_number="001",
            last_task_title="Define types",
            feature="001-widget",
        )
        rc = cmd_update_session_state(args)
        self.assertEqual(rc, EXIT_OK)

        content = self.memory_path.read_text()

        # ## Task Outcomes section must exist.
        self.assertIn("## Task Outcomes", content)

        # Entry must appear AFTER ## Task Outcomes.
        task_outcomes_pos = content.index("## Task Outcomes")
        entry_pos = content.index("Define types")
        self.assertGreater(entry_pos, task_outcomes_pos)

        # ## What Failed section content must still be there.
        self.assertIn("## What Failed", content)
        self.assertIn("Premature optimisation caused regressions.", content)

        # The entry must NOT appear between ## What Failed and EOF as the only
        # content under that section (i.e., it should not be filed under it).
        what_failed_pos = content.index("## What Failed")
        self.assertGreater(
            entry_pos, what_failed_pos,
            "Entry is before ## What Failed — that section ordering is unexpected",
        )
        # But ## Task Outcomes must come AFTER ## What Failed (it's appended at EOF).
        self.assertGreater(task_outcomes_pos, what_failed_pos,
                           "## Task Outcomes should be after ## What Failed when absent")

    def test_second_entry_stays_inside_task_outcomes(self):
        """Two sequential calls both land under ## Task Outcomes."""
        self.memory_path.write_text(_STANDARD_TEMPLATE)

        args1 = _make_fake_args(
            root=str(self.root),
            last_task_number="001",
            last_task_title="First task",
            feature="001-widget",
        )
        args2 = _make_fake_args(
            root=str(self.root),
            last_task_number="002",
            last_task_title="Second task",
            feature="001-widget",
        )
        cmd_update_session_state(args1)
        cmd_update_session_state(args2)

        content = self.memory_path.read_text()

        section_pos = content.index("## Task Outcomes")
        first_pos = content.index("First task")
        second_pos = content.index("Second task")

        self.assertGreater(first_pos, section_pos,
                           "First entry must be under ## Task Outcomes")
        self.assertGreater(second_pos, section_pos,
                           "Second entry must be under ## Task Outcomes")
        self.assertLess(first_pos, second_pos,
                        "Entries must accumulate in chronological order")

    def test_memory_created_with_task_outcomes_when_absent(self):
        """When memory.md does not exist, it is created with ## Task Outcomes."""
        self.assertFalse(self.memory_path.exists())

        args = _make_fake_args(
            root=str(self.root),
            last_task_number="001",
            last_task_title="Alpha task",
            feature="001-widget",
        )
        cmd_update_session_state(args)

        self.assertTrue(self.memory_path.exists())
        content = self.memory_path.read_text()
        self.assertIn("## Task Outcomes", content)
        self.assertIn("Alpha task", content)


if __name__ == "__main__":
    unittest.main()
