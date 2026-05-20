"""Tests for src/devforge/lib/_pr_review/_ensure_cbm.py.

Covers:
  run()                   — subprocess-mocked state token mapping
  _estimate_indexing_cost — file-count heuristic + cap
  _parse_token            — raw stdout parsing
  _token_to_result        — pure mapping (all four token shapes)
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._ensure_cbm import (  # noqa: E402
    _COST_FILE_CAP,
    _COST_EXTENSIONS,
    _estimate_indexing_cost,
    _parse_token,
    _token_to_result,
    run,
)


# ---------------------------------------------------------------------------
# _parse_token — raw stdout normalization.
# ---------------------------------------------------------------------------


class TestParseToken(unittest.TestCase):
    def test_strips_newline(self):
        self.assertEqual(_parse_token("current\n"), "current")

    def test_strips_whitespace(self):
        self.assertEqual(_parse_token("  missing  \n"), "missing")

    def test_multiline_takes_first_line(self):
        self.assertEqual(_parse_token("drift abc..def\nsome other line"), "drift abc..def")

    def test_empty_string_returns_empty(self):
        self.assertEqual(_parse_token(""), "")

    def test_whitespace_only_returns_empty(self):
        self.assertEqual(_parse_token("   \n  "), "")


# ---------------------------------------------------------------------------
# _token_to_result — pure mapping (no filesystem, no subprocess).
# ---------------------------------------------------------------------------


class TestTokenToResult(unittest.TestCase):
    _TARGET = "/tmp/test-repo"

    def test_current_maps_to_ok(self):
        result = _token_to_result("current", self._TARGET, None)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["next_action"], "none")
        self.assertIsNone(result["mcp_tool_hint"])
        self.assertIsNone(result["cost_estimate_usd"])
        self.assertEqual(result["cbm_state_token"], "current")

    def test_drift_maps_to_stale(self):
        result = _token_to_result("drift abc123..def456", self._TARGET, None)
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["next_action"], "run-detect-changes")
        self.assertEqual(
            result["mcp_tool_hint"], "mcp__codebase-memory-mcp__detect_changes"
        )
        self.assertIsNone(result["cost_estimate_usd"])

    def test_missing_maps_to_absent(self):
        result = _token_to_result("missing", self._TARGET, 2.50)
        self.assertEqual(result["status"], "absent")
        self.assertEqual(result["next_action"], "run-index-repository")
        self.assertEqual(
            result["mcp_tool_hint"], "mcp__codebase-memory-mcp__index_repository"
        )
        self.assertEqual(result["cost_estimate_usd"], 2.50)

    def test_not_a_git_repo_maps_to_setup_cbm(self):
        result = _token_to_result("not-a-git-repo", self._TARGET, None)
        self.assertEqual(result["status"], "not-a-git-repo")
        self.assertEqual(result["next_action"], "setup-cbm")
        self.assertIsNone(result["mcp_tool_hint"])
        self.assertIsNone(result["cost_estimate_usd"])

    def test_target_path_is_absolute(self):
        result = _token_to_result("current", self._TARGET, None)
        self.assertTrue(os.path.isabs(result["target_path"]))

    def test_all_required_keys_present(self):
        required = {
            "cbm_state_token",
            "cost_estimate_usd",
            "mcp_tool_hint",
            "next_action",
            "status",
            "target_path",
        }
        result = _token_to_result("current", self._TARGET, None)
        self.assertEqual(set(result.keys()), required)


# ---------------------------------------------------------------------------
# _estimate_indexing_cost — file-count heuristic.
# ---------------------------------------------------------------------------


class TestEstimateIndexingCost(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _make_file(self, relpath: str) -> None:
        full = os.path.join(self._tmp, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write("")

    def test_empty_dir_cost_is_zero(self):
        result = _estimate_indexing_cost(self._tmp)
        self.assertEqual(result, 0.0)

    def test_non_matching_extensions_ignored(self):
        self._make_file("README.md")
        self._make_file("config.yaml")
        self._make_file("Makefile")
        result = _estimate_indexing_cost(self._tmp)
        self.assertEqual(result, 0.0)

    def test_small_repo_cost_small(self):
        # 5 .py files → 5/1000 * $1 = $0.01
        for i in range(5):
            self._make_file("file_{0}.py".format(i))
        result = _estimate_indexing_cost(self._tmp)
        self.assertLess(result, 0.50)
        self.assertGreater(result, 0.0)
        self.assertEqual(result, round(5 / 1000.0, 2))

    def test_mixed_extensions_counted(self):
        self._make_file("a.py")
        self._make_file("b.ts")
        self._make_file("c.go")
        self._make_file("d.md")  # not counted
        result = _estimate_indexing_cost(self._tmp)
        self.assertEqual(result, round(3 / 1000.0, 2))

    def test_result_is_float_rounded_to_2_decimals(self):
        for i in range(7):
            self._make_file("f_{0}.rs".format(i))
        result = _estimate_indexing_cost(self._tmp)
        self.assertIsInstance(result, float)
        # round-trip through str to check decimal places
        decimals = len(str(result).rstrip("0").split(".")[-1]) if "." in str(result) else 0
        self.assertLessEqual(decimals, 2)

    def test_cost_cap_at_10000(self):
        """Verify cap logic by patching os.walk to simulate 11000 matching files."""
        large_filelist = ["file_{0}.py".format(i) for i in range(11000)]

        def _fake_walk(path):
            yield (path, [], large_filelist)

        with patch("_pr_review._ensure_cbm.os.walk", side_effect=_fake_walk):
            result = _estimate_indexing_cost(self._tmp)

        expected = round(_COST_FILE_CAP / 1000.0, 2)
        self.assertEqual(result, expected)

    def test_exactly_at_cap_returns_cap_cost(self):
        """10000 files → cap cost exactly."""
        filelist = ["f_{0}.py".format(i) for i in range(_COST_FILE_CAP)]

        def _fake_walk(path):
            yield (path, [], filelist)

        with patch("_pr_review._ensure_cbm.os.walk", side_effect=_fake_walk):
            result = _estimate_indexing_cost(self._tmp)

        self.assertEqual(result, round(_COST_FILE_CAP / 1000.0, 2))


# ---------------------------------------------------------------------------
# run() — subprocess mocked.
# ---------------------------------------------------------------------------


def _make_subprocess_result(stdout: str, returncode: int = 0) -> MagicMock:
    mock_result = MagicMock()
    mock_result.stdout = stdout
    mock_result.returncode = returncode
    return mock_result


class TestRunEnsureCbm(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_ok_when_stamp_current(self):
        with patch("_pr_review._ensure_cbm.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result("current\n")
            result = run(self._tmp)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["next_action"], "none")
        self.assertIsNone(result["mcp_tool_hint"])
        self.assertIsNone(result["cost_estimate_usd"])

    def test_stale_when_drift(self):
        with patch("_pr_review._ensure_cbm.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result("drift abc123..def456\n")
            result = run(self._tmp)
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["next_action"], "run-detect-changes")
        self.assertEqual(
            result["mcp_tool_hint"], "mcp__codebase-memory-mcp__detect_changes"
        )
        self.assertIsNone(result["cost_estimate_usd"])

    def test_absent_when_missing(self):
        with patch("_pr_review._ensure_cbm.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result("missing\n")
            result = run(self._tmp)
        self.assertEqual(result["status"], "absent")
        self.assertEqual(result["next_action"], "run-index-repository")
        self.assertEqual(
            result["mcp_tool_hint"], "mcp__codebase-memory-mcp__index_repository"
        )
        # cost_estimate_usd is a float (even if 0.0 for empty tmp dir)
        self.assertIsInstance(result["cost_estimate_usd"], float)

    def test_not_a_git_repo(self):
        with patch("_pr_review._ensure_cbm.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result("not-a-git-repo\n")
            result = run(self._tmp)
        self.assertEqual(result["status"], "not-a-git-repo")
        self.assertEqual(result["next_action"], "setup-cbm")
        self.assertIsNone(result["mcp_tool_hint"])
        self.assertIsNone(result["cost_estimate_usd"])

    def test_cbm_state_token_preserved(self):
        token = "drift oldsha..newsha"
        with patch("_pr_review._ensure_cbm.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result(token + "\n")
            result = run(self._tmp)
        self.assertEqual(result["cbm_state_token"], token)

    def test_target_path_absolute_in_result(self):
        with patch("_pr_review._ensure_cbm.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result("current\n")
            result = run(self._tmp)
        self.assertTrue(os.path.isabs(result["target_path"]))

    def test_devforge_dir_passed_as_env(self):
        """DEVFORGE_DIR env var is set correctly in subprocess call."""
        with patch("_pr_review._ensure_cbm.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result("current\n")
            run(self._tmp, devforge_dir=".custom-forge")
        call_env = mock_run.call_args.kwargs.get("env") or mock_run.call_args[1].get("env", {})
        expected_devforge = os.path.join(os.path.abspath(self._tmp), ".custom-forge")
        self.assertEqual(call_env.get("DEVFORGE_DIR"), expected_devforge)

    def test_all_required_keys_present(self):
        required = {
            "cbm_state_token",
            "cost_estimate_usd",
            "mcp_tool_hint",
            "next_action",
            "status",
            "target_path",
        }
        with patch("_pr_review._ensure_cbm.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result("current\n")
            result = run(self._tmp)
        self.assertEqual(set(result.keys()), required)

    def test_cost_estimate_positive_when_py_files_exist(self):
        """When status is absent and .py files exist, cost > 0."""
        # Create some .py files in tmp dir
        for i in range(10):
            path = os.path.join(self._tmp, "mod_{0}.py".format(i))
            with open(path, "w") as f:
                f.write("")
        with patch("_pr_review._ensure_cbm.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result("missing\n")
            result = run(self._tmp)
        self.assertGreater(result["cost_estimate_usd"], 0.0)

    def test_cwd_passed_as_target(self):
        """subprocess.run is called with cwd=abs_target so git commands run in the right repo."""
        with patch("_pr_review._ensure_cbm.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result("current\n")
            run(self._tmp)
        cwd = mock_run.call_args.kwargs.get("cwd") or mock_run.call_args[1].get("cwd")
        self.assertEqual(cwd, os.path.abspath(self._tmp))

    def test_subprocess_crash_maps_to_not_a_git_repo(self):
        """Non-zero exit + empty stdout is explicitly mapped to not-a-git-repo."""
        with patch("_pr_review._ensure_cbm.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=1, stderr="some error")
            result = run(self._tmp)
        self.assertEqual(result["status"], "not-a-git-repo")
        self.assertEqual(result["next_action"], "setup-cbm")


if __name__ == "__main__":
    unittest.main()
