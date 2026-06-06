"""Tests for src/devforge/lib/_implement/_state.py.

Coverage:
  - Valid ImplementState construction (all phases, with/without checkpoint_sha).
  - Frozen: assignment raises FrozenInstanceError.
  - Reject non-Path feature_dir.
  - Reject empty task_number, task_title, agent_name.
  - Reject non-list touched_files.
  - Reject invalid phase string.
  - Reject non-Path wip_marker_path.
  - Reject non-string checkpoint_sha (when not None).
  - Reject empty-string checkpoint_sha.
  - Null checkpoint_sha is accepted.
  - All eight valid phase values are accepted.

Stdlib only. Python 3.8+.
"""

import dataclasses
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _implement._state import ImplementState, _VALID_PHASES  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_state(**overrides):
    """Return a valid ImplementState with all required fields set."""
    defaults = dict(
        feature_dir=Path("/tmp/specs/001-widget"),
        task_number="001",
        task_title="Define widget types",
        agent_name="backend-engineer",
        touched_files=[],
        phase="preflight",
        wip_marker_path=Path("/tmp/.devforge/wip.md"),
        checkpoint_sha=None,
    )
    defaults.update(overrides)
    return ImplementState(**defaults)


# ---------------------------------------------------------------------------
# Valid construction
# ---------------------------------------------------------------------------

class TestImplementStateValid(unittest.TestCase):
    """Valid ImplementState construction."""

    def test_minimal_no_checkpoint(self):
        state = _minimal_state()
        self.assertIsInstance(state, ImplementState)
        self.assertEqual(state.task_number, "001")
        self.assertIsNone(state.checkpoint_sha)

    def test_with_checkpoint_sha(self):
        state = _minimal_state(checkpoint_sha="abc1234")
        self.assertEqual(state.checkpoint_sha, "abc1234")

    def test_touched_files_populated(self):
        state = _minimal_state(touched_files=["src/a.py", "src/b.py"])
        self.assertEqual(state.touched_files, ["src/a.py", "src/b.py"])

    def test_all_eight_phases(self):
        """Every valid phase string is accepted."""
        for phase in [
            "preflight", "agent", "verify", "review",
            "forcing_functions", "gate", "commit", "complete",
        ]:
            with self.subTest(phase=phase):
                state = _minimal_state(phase=phase)
                self.assertEqual(state.phase, phase)

    def test_valid_phases_constant_size(self):
        """_VALID_PHASES has exactly 8 entries (no accidental additions or drops)."""
        self.assertEqual(len(_VALID_PHASES), 8)

    def test_feature_dir_is_path(self):
        state = _minimal_state(feature_dir=Path("/some/feature/dir"))
        self.assertIsInstance(state.feature_dir, Path)

    def test_wip_marker_path_is_path(self):
        state = _minimal_state(wip_marker_path=Path("/devforge/wip.md"))
        self.assertIsInstance(state.wip_marker_path, Path)


# ---------------------------------------------------------------------------
# Frozen
# ---------------------------------------------------------------------------

class TestImplementStateFrozen(unittest.TestCase):
    """ImplementState is frozen -- attribute assignment raises."""

    def test_cannot_assign_task_number(self):
        state = _minimal_state()
        with self.assertRaises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            state.task_number = "002"  # type: ignore[misc]

    def test_cannot_assign_phase(self):
        state = _minimal_state()
        with self.assertRaises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            state.phase = "agent"  # type: ignore[misc]

    def test_dataclasses_replace_works(self):
        """dataclasses.replace creates a new instance with updated fields."""
        state = _minimal_state(phase="preflight")
        state2 = dataclasses.replace(state, phase="agent")
        self.assertEqual(state2.phase, "agent")
        self.assertEqual(state.phase, "preflight")  # original unchanged


# ---------------------------------------------------------------------------
# feature_dir validation
# ---------------------------------------------------------------------------

class TestFeatureDirValidation(unittest.TestCase):
    def test_rejects_string_feature_dir(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(feature_dir="/tmp/specs/001-widget")  # str, not Path
        self.assertIn("feature_dir", str(ctx.exception))

    def test_rejects_none_feature_dir(self):
        with self.assertRaises((ValueError, TypeError)):
            _minimal_state(feature_dir=None)


# ---------------------------------------------------------------------------
# task_number validation
# ---------------------------------------------------------------------------

class TestTaskNumberValidation(unittest.TestCase):
    def test_rejects_empty_string(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(task_number="")
        self.assertIn("task_number", str(ctx.exception))

    def test_rejects_whitespace_only(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(task_number="   ")
        self.assertIn("task_number", str(ctx.exception))

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(task_number=1)
        self.assertIn("task_number", str(ctx.exception))


# ---------------------------------------------------------------------------
# task_title validation
# ---------------------------------------------------------------------------

class TestTaskTitleValidation(unittest.TestCase):
    def test_rejects_empty_string(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(task_title="")
        self.assertIn("task_title", str(ctx.exception))

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(task_title=42)
        self.assertIn("task_title", str(ctx.exception))


# ---------------------------------------------------------------------------
# agent_name validation
# ---------------------------------------------------------------------------

class TestAgentNameValidation(unittest.TestCase):
    def test_rejects_empty_string(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(agent_name="")
        self.assertIn("agent_name", str(ctx.exception))

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(agent_name=None)
        self.assertIn("agent_name", str(ctx.exception))


# ---------------------------------------------------------------------------
# touched_files validation
# ---------------------------------------------------------------------------

class TestTouchedFilesValidation(unittest.TestCase):
    def test_rejects_string_not_list(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(touched_files="src/a.py")
        self.assertIn("touched_files", str(ctx.exception))

    def test_rejects_none(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(touched_files=None)
        self.assertIn("touched_files", str(ctx.exception))

    def test_accepts_empty_list(self):
        state = _minimal_state(touched_files=[])
        self.assertEqual(state.touched_files, [])


# ---------------------------------------------------------------------------
# phase validation
# ---------------------------------------------------------------------------

class TestPhaseValidation(unittest.TestCase):
    def test_rejects_unknown_phase(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(phase="unknown_phase")
        self.assertIn("phase", str(ctx.exception))

    def test_rejects_empty_phase(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(phase="")
        self.assertIn("phase", str(ctx.exception))

    def test_rejects_non_string_phase(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(phase=None)
        # phase is validated against _VALID_PHASES; None is not in it
        self.assertIn("phase", str(ctx.exception))


# ---------------------------------------------------------------------------
# wip_marker_path validation
# ---------------------------------------------------------------------------

class TestWipMarkerPathValidation(unittest.TestCase):
    def test_rejects_string_not_path(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(wip_marker_path="/devforge/wip.md")  # str, not Path
        self.assertIn("wip_marker_path", str(ctx.exception))

    def test_rejects_none(self):
        with self.assertRaises((ValueError, TypeError)):
            _minimal_state(wip_marker_path=None)


# ---------------------------------------------------------------------------
# checkpoint_sha validation
# ---------------------------------------------------------------------------

class TestCheckpointShaValidation(unittest.TestCase):
    def test_accepts_none(self):
        state = _minimal_state(checkpoint_sha=None)
        self.assertIsNone(state.checkpoint_sha)

    def test_accepts_valid_sha(self):
        state = _minimal_state(checkpoint_sha="deadbeef1234567890")
        self.assertEqual(state.checkpoint_sha, "deadbeef1234567890")

    def test_rejects_empty_string(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(checkpoint_sha="")
        self.assertIn("checkpoint_sha", str(ctx.exception))

    def test_rejects_whitespace_only(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(checkpoint_sha="   ")
        self.assertIn("checkpoint_sha", str(ctx.exception))

    def test_rejects_int(self):
        with self.assertRaises(ValueError) as ctx:
            _minimal_state(checkpoint_sha=12345)
        self.assertIn("checkpoint_sha", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
