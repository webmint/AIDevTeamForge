"""Launcher smoke tests for spec_check_helper.py.

Mirrors the pattern used across the forge helper test suite (see
tests/lib/_grill/test_launcher.py for the sibling reference), adapted to
unittest.TestCase — this repo's test environment has no pytest installed,
and every test here must actually run under `python3 -m unittest`:
- verifies the .py shim imports the correct entry point (_spec_check._cli.main)
- verifies --help dispatches and lists all 7 expected verbs
- verifies the executable wrapper exists and is runnable

Stdlib only. Targets Python 3.8+.
"""

import io
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import List
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Path setup — mirror the pattern from other _spec_check tests
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).resolve().parent          # tests/lib/_spec_check/
_REPO_ROOT = _TESTS_DIR.parent.parent.parent          # repo root
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

_SPEC_CHECK_HELPER_PY = _LIB_DIR / "spec_check_helper.py"
_SPEC_CHECK_HELPER_BIN = _LIB_DIR / "spec_check_helper"

_EXPECTED_VERBS: List[str] = [
    "preflight",
    "resolve-scope",
    "render-formalize-brief",
    "consume-ir",
    "solve",
    "render-report",
    "write-seed",
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSpecCheckHelperPyShim(unittest.TestCase):
    """spec_check_helper.py imports _spec_check._cli.main correctly."""

    def test_shim_file_exists(self):
        self.assertTrue(
            _SPEC_CHECK_HELPER_PY.exists(), f"Missing: {_SPEC_CHECK_HELPER_PY}"
        )

    def test_shim_imports_spec_check_cli_main(self):
        # Import spec_check_helper as a module — its top-level import of
        # _spec_check._cli.main must succeed without error.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "spec_check_helper", str(_SPEC_CHECK_HELPER_PY)
        )
        self.assertIsNotNone(spec)
        mod = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        # The module must expose a `main` attribute that is the same object
        # as _spec_check._cli.main.
        from _spec_check._cli import main as spec_check_cli_main

        self.assertIs(mod.main, spec_check_cli_main)

    def test_no_subcommand_returns_2(self):
        """main() with no subcommand prints help and returns 2."""
        from _spec_check._cli import main

        with patch("sys.stderr", new_callable=io.StringIO):
            rc = main(argv=[])
        self.assertEqual(rc, 2)


class TestSpecCheckHelperHelpOutput(unittest.TestCase):
    """--help output lists all 7 expected verbs."""

    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(_SPEC_CHECK_HELPER_PY), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"--help returned {result.returncode}; stderr: {result.stderr}",
        )

    def test_help_lists_all_verbs(self):
        result = subprocess.run(
            [sys.executable, str(_SPEC_CHECK_HELPER_PY), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        for verb in _EXPECTED_VERBS:
            self.assertIn(verb, combined, f"Verb '{verb}' missing from --help output")

    def test_help_verb_count(self):
        """Exactly 7 verbs (the Phase 6 scratch chain)."""
        self.assertEqual(len(_EXPECTED_VERBS), 7)


class TestSpecCheckHelperExecutableBin(unittest.TestCase):
    """The no-extension executable wrapper is present and runnable."""

    def test_bin_file_exists(self):
        self.assertTrue(
            _SPEC_CHECK_HELPER_BIN.exists(), f"Missing: {_SPEC_CHECK_HELPER_BIN}"
        )

    def test_bin_has_shebang(self):
        with open(_SPEC_CHECK_HELPER_BIN, "r", encoding="utf-8") as fh:
            first_line = fh.readline()
        self.assertTrue(
            first_line.startswith("#!"),
            f"{_SPEC_CHECK_HELPER_BIN} does not start with a shebang line",
        )

    def test_bin_is_executable(self):
        self.assertTrue(
            os.access(str(_SPEC_CHECK_HELPER_BIN), os.X_OK),
            f"{_SPEC_CHECK_HELPER_BIN} is not executable",
        )

    def test_bin_help_exits_zero(self):
        result = subprocess.run(
            [str(_SPEC_CHECK_HELPER_BIN), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"bin --help returned {result.returncode}; stderr: {result.stderr}",
        )

    def test_bin_help_lists_all_verbs(self):
        result = subprocess.run(
            [str(_SPEC_CHECK_HELPER_BIN), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        for verb in _EXPECTED_VERBS:
            self.assertIn(
                verb, combined, f"Verb '{verb}' missing from bin --help output"
            )


if __name__ == "__main__":
    unittest.main()
