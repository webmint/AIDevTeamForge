"""Tests for src/devforge/lib/configure_helper.py — Step 0 scaffolding.

Step 0 scope: reset subcommand only, placeholder yaml output. Step 1 tests
(read-* subcommands, FIELD_SCHEMA setters) live in a separate file when
Step 1 ships.

Each test runs in its own `tempfile.TemporaryDirectory` and points the
helper at it via the `--devforge-dir` CLI argument. `DEVFORGE_DIR` env is
scrubbed in setUp so a leaking shell env can't taint the test.

CLI tests invoke the .py file as a subprocess to exercise the real
argparse + dispatch path end-to-end. Pure-function tests import the
module directly.

Stdlib only.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Resolve the helper script + add lib dir to sys.path so we can import
# the module for pure-function tests.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "configure_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import configure_helper  # noqa: E402


class _EnvIsolationMixin:
    """Save/restore DEVFORGE_DIR around each test + provide a tmpdir."""

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name)
        self.output_file = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env


# ---------------------------------------------------------------------------
# ResetTests — end-to-end subprocess invocation.
# ---------------------------------------------------------------------------


class ResetTests(_EnvIsolationMixin, unittest.TestCase):

    def test_reset_writes_placeholder_yaml(self):
        """Subprocess reset exits 0 and writes the exact placeholder text."""
        proc = subprocess.run(
            [
                sys.executable,
                str(_HELPER_PY),
                "--devforge-dir",
                str(self.devforge_dir),
                "reset",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
        self.assertTrue(
            self.output_file.exists(),
            "configure.yaml was not created at {0}".format(self.output_file),
        )
        contents = self.output_file.read_text(encoding="utf-8")
        self.assertEqual(
            contents,
            "# configure.yaml — schema populated by Step 1 of CONFIGURE-PLAN.md\n",
        )


if __name__ == "__main__":
    unittest.main()
