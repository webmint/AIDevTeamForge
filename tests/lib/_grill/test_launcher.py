"""Launcher smoke tests for grill_helper.py.

Mirrors the pattern used across the forge helper test suite:
- verifies the .py shim imports the correct entry point (_grill._cli.main)
- verifies --help dispatches and lists all 12 expected verbs
- verifies the executable wrapper exists and is runnable

Stdlib only. Targets Python 3.8+.
"""

import subprocess
import sys
import os
import importlib
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Path setup — mirror the pattern from other grill tests
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).resolve().parent          # tests/lib/_grill/
_REPO_ROOT = _TESTS_DIR.parent.parent.parent          # repo root
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

_GRILL_HELPER_PY = _LIB_DIR / "grill_helper.py"
_GRILL_HELPER_BIN = _LIB_DIR / "grill_helper"

_EXPECTED_VERBS: List[str] = [
    "check-status-and-flip",
    "preflight",
    "resolve-scope",
    "render-brief",
    "consume-tmp",
    "validate-findings",
    "route-refutation",
    "render-verify-brief",
    "consume-verdicts",
    "apply-verdicts",
    "render-report",
    "write-seed",
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGrillHelperPyShim:
    """grill_helper.py imports _grill._cli.main correctly."""

    def test_shim_file_exists(self) -> None:
        assert _GRILL_HELPER_PY.exists(), f"Missing: {_GRILL_HELPER_PY}"

    def test_shim_imports_grill_cli_main(self) -> None:
        # Import grill_helper as a module — its top-level import of
        # _grill._cli.main must succeed without error.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "grill_helper", str(_GRILL_HELPER_PY)
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        # The module must expose a `main` attribute that is the same object
        # as _grill._cli.main.
        from _grill._cli import main as grill_cli_main
        assert mod.main is grill_cli_main

    def test_no_subcommand_returns_2(self) -> None:
        """main() with no subcommand prints help and returns 2."""
        from _grill._cli import main
        import io
        from unittest.mock import patch
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            rc = main(argv=[])
        assert rc == 2


class TestGrillHelperHelpOutput:
    """--help output lists all 12 expected verbs."""

    def test_help_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_GRILL_HELPER_PY), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"--help returned {result.returncode}; stderr: {result.stderr}"

    def test_help_lists_all_verbs(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_GRILL_HELPER_PY), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        for verb in _EXPECTED_VERBS:
            assert verb in combined, f"Verb '{verb}' missing from --help output"

    def test_help_verb_count(self) -> None:
        """Exactly 12 verbs (one per Phase 1–5 plus refutation)."""
        assert len(_EXPECTED_VERBS) == 12


class TestGrillHelperExecutableBin:
    """The no-extension executable wrapper is present and runnable."""

    def test_bin_file_exists(self) -> None:
        assert _GRILL_HELPER_BIN.exists(), f"Missing: {_GRILL_HELPER_BIN}"

    def test_bin_is_executable(self) -> None:
        assert os.access(str(_GRILL_HELPER_BIN), os.X_OK), (
            f"{_GRILL_HELPER_BIN} is not executable"
        )

    def test_bin_help_exits_zero(self) -> None:
        result = subprocess.run(
            [str(_GRILL_HELPER_BIN), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"bin --help returned {result.returncode}; stderr: {result.stderr}"
        )

    def test_bin_help_lists_all_verbs(self) -> None:
        result = subprocess.run(
            [str(_GRILL_HELPER_BIN), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        for verb in _EXPECTED_VERBS:
            assert verb in combined, (
                f"Verb '{verb}' missing from bin --help output"
            )
