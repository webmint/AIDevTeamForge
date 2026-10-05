"""Tests for src/devforge/lib/_implement/_wip.py.

Coverage (clear_wip_marker, the module's one function):
  - Removes wip.md when present.
  - Silent no-op when wip.md is absent (no exception).
  - Accepts devforge_dir as a string.
  - Idempotent on a double clear.
  - _cmds_commit resolves the same function object by import.

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

from _implement import _cmds_commit  # noqa: E402
from _implement._wip import clear_wip_marker  # noqa: E402


def _seed_marker(devforge_dir):
    """Write a marker file directly (the orchestrator is its only writer)."""
    (Path(devforge_dir) / "wip.md").write_text(
        "# WIP Marker — /implement\n\n**Command**: /implement\n",
        encoding="utf-8",
    )


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
        _seed_marker(self.devforge_dir)
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
        _seed_marker(self.devforge_dir)
        clear_wip_marker(str(self.devforge_dir))
        self.assertFalse((self.devforge_dir / "wip.md").exists())

    def test_idempotent_double_clear(self):
        """Calling clear twice does not raise."""
        _seed_marker(self.devforge_dir)
        clear_wip_marker(self.devforge_dir)
        try:
            clear_wip_marker(self.devforge_dir)  # second call -- file absent
        except Exception as exc:
            self.fail("Second clear raised: {0}".format(exc))

    def test_resolves_from_cmds_commit(self):
        """_cmds_commit imports this same clear_wip_marker (live caller)."""
        self.assertIs(_cmds_commit.clear_wip_marker, clear_wip_marker)


if __name__ == "__main__":
    unittest.main()
