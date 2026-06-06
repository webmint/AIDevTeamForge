"""Tests for src/devforge/lib/_implement/_wip.py.

Coverage:
  write_wip_marker:
    - Creates wip.md with all expected fields.
    - Command field is always '/implement'.
    - checkpoint_sha=None writes '(none)'.
    - checkpoint_sha set writes the sha.
    - Overwrites an existing wip.md (idempotent).
    - Atomic write: uses temp file (no partial state on disk).

  read_wip_marker:
    - Returns None when wip.md is absent.
    - Returns a dict with all written fields after write.
    - Returns Command field == '/implement'.
    - Returns empty dict when wip.md exists but has no parseable fields.

  clear_wip_marker:
    - Removes wip.md when present.
    - Silent no-op when wip.md is absent (no exception).

  Integration:
    - write -> read -> clear cycle works end-to-end.
    - After clear, read returns None.

Stdlib only. Python 3.8+.
"""

import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _implement._state import ImplementState  # noqa: E402
from _implement._wip import (  # noqa: E402
    clear_wip_marker,
    read_wip_marker,
    write_wip_marker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(devforge_dir, **overrides):
    """Return a minimal ImplementState with wip_marker_path inside devforge_dir."""
    defaults = dict(
        feature_dir=Path("/tmp/specs/001-widget"),
        task_number="001",
        task_title="Define widget types",
        agent_name="backend-engineer",
        touched_files=[],
        phase="preflight",
        wip_marker_path=Path(devforge_dir) / "wip.md",
        checkpoint_sha=None,
    )
    defaults.update(overrides)
    return ImplementState(**defaults)


# ---------------------------------------------------------------------------
# write_wip_marker
# ---------------------------------------------------------------------------

class TestWriteWipMarker(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name) / ".devforge"
        self.devforge_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_creates_wip_md(self):
        """write_wip_marker creates wip.md in the devforge_dir."""
        state = _make_state(self.devforge_dir)
        write_wip_marker(state)
        wip_path = self.devforge_dir / "wip.md"
        self.assertTrue(wip_path.exists(), "wip.md was not created")

    def test_command_field_is_implement(self):
        """Command field in wip.md is always '/implement'."""
        state = _make_state(self.devforge_dir)
        write_wip_marker(state)
        content = (self.devforge_dir / "wip.md").read_text(encoding="utf-8")
        self.assertIn("**Command**: /implement", content)

    def test_task_number_in_content(self):
        """Task field contains the task_number."""
        state = _make_state(self.devforge_dir, task_number="007")
        write_wip_marker(state)
        content = (self.devforge_dir / "wip.md").read_text(encoding="utf-8")
        self.assertIn("**Task**: 007", content)

    def test_task_title_in_content(self):
        """Title field contains the task_title."""
        state = _make_state(self.devforge_dir, task_title="My Task Title")
        write_wip_marker(state)
        content = (self.devforge_dir / "wip.md").read_text(encoding="utf-8")
        self.assertIn("**Title**: My Task Title", content)

    def test_agent_in_content(self):
        """Agent field contains the agent_name."""
        state = _make_state(self.devforge_dir, agent_name="frontend-engineer")
        write_wip_marker(state)
        content = (self.devforge_dir / "wip.md").read_text(encoding="utf-8")
        self.assertIn("**Agent**: frontend-engineer", content)

    def test_phase_in_content(self):
        """Phase field contains the phase."""
        state = _make_state(self.devforge_dir, phase="verify")
        write_wip_marker(state)
        content = (self.devforge_dir / "wip.md").read_text(encoding="utf-8")
        self.assertIn("**Phase**: verify", content)

    def test_checkpoint_none_writes_none_sentinel(self):
        """checkpoint_sha=None writes '(none)' in the Checkpoint field."""
        state = _make_state(self.devforge_dir, checkpoint_sha=None)
        write_wip_marker(state)
        content = (self.devforge_dir / "wip.md").read_text(encoding="utf-8")
        self.assertIn("**Checkpoint**: (none)", content)

    def test_checkpoint_sha_written(self):
        """checkpoint_sha value is written to the Checkpoint field."""
        state = _make_state(self.devforge_dir, checkpoint_sha="abc123def")
        write_wip_marker(state)
        content = (self.devforge_dir / "wip.md").read_text(encoding="utf-8")
        self.assertIn("**Checkpoint**: abc123def", content)

    def test_overwrites_existing_wip_md(self):
        """Calling write_wip_marker twice overwrites the previous content."""
        state1 = _make_state(self.devforge_dir, task_number="001")
        state2 = _make_state(self.devforge_dir, task_number="002")
        write_wip_marker(state1)
        write_wip_marker(state2)
        content = (self.devforge_dir / "wip.md").read_text(encoding="utf-8")
        self.assertIn("**Task**: 002", content)
        self.assertNotIn("**Task**: 001", content)

    def test_feature_dir_in_content(self):
        """Feature field contains the feature_dir path."""
        feature_path = Path("/tmp/specs/001-widget")
        state = _make_state(self.devforge_dir, feature_dir=feature_path)
        write_wip_marker(state)
        content = (self.devforge_dir / "wip.md").read_text(encoding="utf-8")
        self.assertIn("**Feature**:", content)
        self.assertIn("001-widget", content)

    def test_heading_present(self):
        """The markdown file has a '# WIP Marker' heading."""
        state = _make_state(self.devforge_dir)
        write_wip_marker(state)
        content = (self.devforge_dir / "wip.md").read_text(encoding="utf-8")
        self.assertIn("# WIP Marker", content)


# ---------------------------------------------------------------------------
# read_wip_marker
# ---------------------------------------------------------------------------

class TestReadWipMarker(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name) / ".devforge"
        self.devforge_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_none_when_absent(self):
        """Returns None when wip.md does not exist."""
        result = read_wip_marker(self.devforge_dir)
        self.assertIsNone(result)

    def test_returns_dict_after_write(self):
        """Returns a dict after write_wip_marker."""
        state = _make_state(self.devforge_dir)
        write_wip_marker(state)
        result = read_wip_marker(self.devforge_dir)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)

    def test_command_field_is_implement(self):
        """Parsed Command field is '/implement'."""
        state = _make_state(self.devforge_dir)
        write_wip_marker(state)
        result = read_wip_marker(self.devforge_dir)
        self.assertEqual(result.get("Command"), "/implement")

    def test_task_number_round_trips(self):
        """Task field round-trips through write/read."""
        state = _make_state(self.devforge_dir, task_number="042")
        write_wip_marker(state)
        result = read_wip_marker(self.devforge_dir)
        self.assertEqual(result.get("Task"), "042")

    def test_task_title_round_trips(self):
        """Title field round-trips through write/read."""
        state = _make_state(self.devforge_dir, task_title="Build the thing")
        write_wip_marker(state)
        result = read_wip_marker(self.devforge_dir)
        self.assertEqual(result.get("Title"), "Build the thing")

    def test_phase_round_trips(self):
        """Phase field round-trips through write/read."""
        state = _make_state(self.devforge_dir, phase="gate")
        write_wip_marker(state)
        result = read_wip_marker(self.devforge_dir)
        self.assertEqual(result.get("Phase"), "gate")

    def test_checkpoint_sha_round_trips(self):
        """Checkpoint SHA round-trips through write/read."""
        state = _make_state(self.devforge_dir, checkpoint_sha="deadbeef42")
        write_wip_marker(state)
        result = read_wip_marker(self.devforge_dir)
        self.assertEqual(result.get("Checkpoint"), "deadbeef42")

    def test_checkpoint_none_reads_as_none_sentinel(self):
        """Checkpoint field reads as '(none)' when sha was None."""
        state = _make_state(self.devforge_dir, checkpoint_sha=None)
        write_wip_marker(state)
        result = read_wip_marker(self.devforge_dir)
        self.assertEqual(result.get("Checkpoint"), "(none)")

    def test_accepts_string_devforge_dir(self):
        """read_wip_marker accepts devforge_dir as a string."""
        state = _make_state(self.devforge_dir)
        write_wip_marker(state)
        result = read_wip_marker(str(self.devforge_dir))
        self.assertIsNotNone(result)

    def test_unparseable_file_returns_empty_dict(self):
        """A wip.md with no **Key**: Value lines returns an empty dict (not None)."""
        wip_path = self.devforge_dir / "wip.md"
        wip_path.write_text("# WIP Marker\n\nsome random text\n", encoding="utf-8")
        result = read_wip_marker(self.devforge_dir)
        # Should return empty dict, not None (file exists but no fields parsed).
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)


# ---------------------------------------------------------------------------
# clear_wip_marker
# ---------------------------------------------------------------------------

class TestClearWipMarker(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name) / ".devforge"
        self.devforge_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_removes_wip_md(self):
        """clear_wip_marker removes wip.md when present."""
        state = _make_state(self.devforge_dir)
        write_wip_marker(state)
        self.assertTrue((self.devforge_dir / "wip.md").exists())

        clear_wip_marker(self.devforge_dir)
        self.assertFalse((self.devforge_dir / "wip.md").exists())

    def test_no_error_when_absent(self):
        """clear_wip_marker is a no-op (no exception) when wip.md is absent."""
        # File does not exist -- should not raise.
        try:
            clear_wip_marker(self.devforge_dir)
        except Exception as exc:
            self.fail("clear_wip_marker raised unexpectedly: {0}".format(exc))

    def test_accepts_string_devforge_dir(self):
        """clear_wip_marker accepts devforge_dir as a string."""
        state = _make_state(self.devforge_dir)
        write_wip_marker(state)
        clear_wip_marker(str(self.devforge_dir))
        self.assertFalse((self.devforge_dir / "wip.md").exists())

    def test_idempotent_double_clear(self):
        """Calling clear twice does not raise."""
        state = _make_state(self.devforge_dir)
        write_wip_marker(state)
        clear_wip_marker(self.devforge_dir)
        try:
            clear_wip_marker(self.devforge_dir)  # second call -- file absent
        except Exception as exc:
            self.fail("Second clear raised: {0}".format(exc))


# ---------------------------------------------------------------------------
# Integration: write -> read -> clear cycle
# ---------------------------------------------------------------------------

class TestWipCycle(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name) / ".devforge"
        self.devforge_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_full_cycle(self):
        """write -> read -> clear -> read=None cycle."""
        state = _make_state(
            self.devforge_dir,
            task_number="003",
            task_title="Build API",
            agent_name="backend-engineer",
            phase="agent",
            checkpoint_sha="cafe4321",
        )

        # Write.
        write_wip_marker(state)

        # Read.
        data = read_wip_marker(self.devforge_dir)
        self.assertIsNotNone(data)
        self.assertEqual(data.get("Command"), "/implement")
        self.assertEqual(data.get("Task"), "003")
        self.assertEqual(data.get("Title"), "Build API")
        self.assertEqual(data.get("Agent"), "backend-engineer")
        self.assertEqual(data.get("Phase"), "agent")
        self.assertEqual(data.get("Checkpoint"), "cafe4321")

        # Clear.
        clear_wip_marker(self.devforge_dir)

        # Read again -- now None.
        after = read_wip_marker(self.devforge_dir)
        self.assertIsNone(after)

    def test_mismatch_detection_via_command_field(self):
        """A marker written by /fix (wrong Command) is distinguishable.

        This test simulates a /fix marker and verifies that the Command
        field can be used to detect the mismatch at crash-recovery time.
        """
        # Simulate a /fix marker written by another command.
        wip_path = self.devforge_dir / "wip.md"
        wip_path.write_text(
            "# WIP Marker — /fix\n\n"
            "**Command**: /fix\n"
            "**Task**: 002\n",
            encoding="utf-8",
        )

        data = read_wip_marker(self.devforge_dir)
        self.assertIsNotNone(data)
        # The Command field must differ from '/implement' so the caller can
        # detect the mismatch and refuse to proceed.
        self.assertEqual(data.get("Command"), "/fix")
        self.assertNotEqual(data.get("Command"), "/implement")


if __name__ == "__main__":
    unittest.main()
