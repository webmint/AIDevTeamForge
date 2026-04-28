"""Tests for src/devforge/lib/wizard_render.py.

Covers the `reset` subcommand and `_state_file_path` resolution.

Each test runs in its own `tempfile.TemporaryDirectory` and points the
helper at it via the `DEVFORGE_DIR` environment variable, so the repo's
real `.devforge/` is never touched. The env override is restored in
tearDown so tests can't bleed into each other.

Pure-function tests (`_state_file_path`) import the module directly.
End-to-end CLI tests invoke the .py file as a subprocess, exercising
the real argparse + dispatch path.

Stdlib only.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Resolve the helper script + add lib dir to sys.path so we can `import
# wizard_render` for pure-function tests. The path computation is
# repo-relative, not env-dependent.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "wizard_render.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import wizard_render  # noqa: E402


def _run_reset(devforge_dir):
    """Invoke `wizard_render.py reset` as a subprocess with DEVFORGE_DIR set."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_HELPER_PY), "reset"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class StateFilePathTests(unittest.TestCase):
    """`_state_file_path` resolution rules."""

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def test_env_override_honored(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["DEVFORGE_DIR"] = tmp
            path = wizard_render._state_file_path()
            self.assertEqual(
                path, Path(tmp) / wizard_render.STATE_FILE_NAME
            )

    def test_no_env_falls_back_to_helper_location(self):
        path = wizard_render._state_file_path()
        expected_dir = Path(wizard_render.__file__).resolve().parent.parent
        self.assertEqual(path, expected_dir / wizard_render.STATE_FILE_NAME)

    def test_resolution_is_per_call_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp_a:
            os.environ["DEVFORGE_DIR"] = tmp_a
            first = wizard_render._state_file_path()
        with tempfile.TemporaryDirectory() as tmp_b:
            os.environ["DEVFORGE_DIR"] = tmp_b
            second = wizard_render._state_file_path()
        self.assertNotEqual(first, second)


class ResetSubcommandTests(unittest.TestCase):
    """End-to-end behavior of `wizard_render reset`."""

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name)
        self.state_file = self.devforge_dir / wizard_render.STATE_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def test_missing_state_file_exits_zero_silently(self):
        self.assertFalse(self.state_file.exists())
        proc = _run_reset(self.devforge_dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"")
        self.assertEqual(proc.stderr, b"")
        self.assertFalse(self.state_file.exists())

    def test_existing_valid_json_state_is_deleted(self):
        self.state_file.write_text('{"languages": ["python"]}\n')
        self.assertTrue(self.state_file.exists())
        proc = _run_reset(self.devforge_dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_empty_state_file_is_deleted(self):
        self.state_file.write_text("")
        self.assertTrue(self.state_file.exists())
        proc = _run_reset(self.devforge_dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_invalid_json_state_file_is_deleted(self):
        self.state_file.write_text("not json at all }{")
        self.assertTrue(self.state_file.exists())
        proc = _run_reset(self.devforge_dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_state_path_is_directory_returns_error(self):
        self.state_file.mkdir()
        self.assertTrue(self.state_file.is_dir())
        proc = _run_reset(self.devforge_dir)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(str(self.state_file).encode(), proc.stderr)
        self.assertTrue(self.state_file.is_dir())

    def test_devforge_dir_env_isolates_from_real_state(self):
        self.state_file.write_text('{"x": 1}')
        proc = _run_reset(self.devforge_dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.state_file.exists())
        self.assertTrue(
            str(self.state_file).startswith(str(self.devforge_dir))
        )


if __name__ == "__main__":
    unittest.main()
