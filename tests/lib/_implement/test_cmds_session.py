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

  cmd_update_session_state (integration, real tempdir):
    - session-state.md created on first call.
    - session-state.md FULLY overwritten on second call (not appended).
    - session-state.md is ≤ 40 lines after each call.
    - Sliding window: 5 tasks passed → only last 3 in session-state.md.
    - --timestamp injected → appears in session-state.md (deterministic).
    - --feature required → exit 1 on absence.
    - --completed-count must be integer → exit 1 on non-integer.
    - --recent-tasks invalid JSON → exit 1.
    - --recent-decisions invalid JSON → exit 1.
    - Output JSON is {"updated": true}.
    - .devforge/memory.md is never created or touched by this command
      (plan 79 Phase 2 removed the per-task memory-receipt writer; the
      "## Task Outcomes" section it wrote to is excluded from every memory
      read as of plan 79 Phase 1, so the write was a dead end).

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
        self.assertIn("# Session State — /devforge:implement", content)
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

    def test_memory_md_never_created(self):
        """cmd_update_session_state never creates .devforge/memory.md.

        Plan 79 Phase 2 removed the per-task memory-receipt writer (the
        "## Task Outcomes" append) because plan 79 Phase 1 excludes that
        section from every memory read -- the write was feeding a dead end.
        .devforge/session-state.md already tracks the last 3 tasks.
        """
        self.assertFalse(self.memory_path.exists())

        args = _make_fake_args(root=str(self.root))
        rc = cmd_update_session_state(args)
        self.assertEqual(rc, EXIT_OK)

        self.assertFalse(
            self.memory_path.exists(),
            "cmd_update_session_state must not create .devforge/memory.md",
        )

    def test_memory_md_untouched_when_pre_existing(self):
        """A pre-existing memory.md is left byte-identical after the call."""
        existing = "- **[Old entry]**: something old.\n"
        self.memory_path.write_text(existing)

        args = _make_fake_args(root=str(self.root))
        rc = cmd_update_session_state(args)
        self.assertEqual(rc, EXIT_OK)

        self.assertEqual(self.memory_path.read_text(), existing)


if __name__ == "__main__":
    unittest.main()
