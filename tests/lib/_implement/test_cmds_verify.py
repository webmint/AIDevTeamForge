"""Tests for src/devforge/lib/_implement/_cmds_verify.py.

Coverage:

  _match_package:
    - File inside a package → returns the package dict.
    - File at exact package path → matches (edge case).
    - File outside all packages → None.
    - Longest-prefix wins when two packages share a common prefix.
    - Empty package_stacks → None.
    - Package path with no trailing slash matches correctly.
    - Package path with trailing slash (defensive) still matches.

  _collect_commands:
    - Single file matching one package → that package's type_check + lint.
    - Multiple files matching same package → command appears once (de-duped).
    - File outside all packages → primary fallback.
    - "N/A" type_check_command silently excluded.
    - "N/A" lint_command silently excluded.
    - None type_check_command silently excluded.
    - Mixed: some package files + one non-package file → package cmds + fallback, de-duped.

  _collect_build_commands:
    - File inside package with build_command → that command included.
    - File outside package → primary_build fallback included.
    - Two files in different packages → two distinct build commands.
    - Duplicate build commands for same package de-duped.
    - "N/A" build_command silently excluded.
    - Empty touched_files + primary_build → primary build runs once.
    - Empty touched_files + no primary_build → empty list.

  cmd_verify_touched (integration, real project-config.json fixture):
    - All commands pass (using `true` as a pass command) → {status:"pass"} exit 0.
    - Failing command at iteration 0 → {status:"self_repair", iteration:0} exit 0.
    - Failing command at iteration 1 → {status:"self_repair", iteration:1} exit 0.
    - Failing command at iteration 2 → {status:"self_repair", iteration:2} exit 0.
    - Failing command at iteration 3 → {status:"failed"} exit 2.
    - "N/A" type_check_command not run (passes silently).
    - File in package-A gets package-A commands, not package-B commands.
    - File outside all packages gets primary fallback.
    - Missing project-config.json → exit 1, stderr message.
    - Invalid --files JSON → exit 1, stderr message.
    - Empty --files list + no primary commands → pass immediately.
    - De-duplication: two files in the same package → command runs once, not twice.

Design notes:
- Commands in the fixture config use 'true' (always-pass) and 'false'
  (always-fail) so no real tsc/eslint/npm is required.
- We use a real .devforge/project-config.json written to a temp directory
  (the real producer shape, not a hand-authored guess) to exercise the
  full loading path.
- The self-repair counter boundary is tested at N=0, 1, 2 (self_repair) and
  N=3 (failed/EXIT_FINDINGS), covering both sides of the cap.
- subprocess calls use shell=True inside cmd_verify_touched; 'true' and 'false'
  are POSIX built-ins available in /bin or via the shell built-in on macOS/Linux.

Stdlib only. Python 3.8+.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Path bootstrap: make _implement importable.
# ---------------------------------------------------------------------------
_LIB_DIR = str(Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _implement._cmds_verify import (  # noqa: E402
    _match_package,
    _collect_commands,
    _collect_build_commands,
    _is_tooling_unavailable,
    cmd_verify_touched,
    SELF_REPAIR_CAP,
    EXIT_OK,
    EXIT_ERR,
    EXIT_FINDINGS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Two packages with different commands + primary-stack arrays.
# Commands use POSIX 'true' / 'false' so tests run without real tsc/eslint.
_FIXTURE_CONFIG = {
    "TYPE_CHECK_COMMANDS": ["true"],
    "LINT_COMMANDS": ["true"],
    "BUILD_COMMANDS": ["true"],
    "PACKAGE_STACKS": [
        {
            "path": "services/api",
            "language": "Python",
            "framework": "FastAPI",
            "build_tool": None,
            "build_command": "true",
            "type_check_command": "true",
            "lint_command": "true",
        },
        {
            "path": "frontend",
            "language": "TypeScript",
            "framework": "React",
            "build_tool": "vite",
            "build_command": "true",
            "type_check_command": "true",
            "lint_command": "true",
        },
    ],
}

# Config where the api package has failing commands.
_FIXTURE_CONFIG_FAIL_API = {
    "TYPE_CHECK_COMMANDS": ["true"],
    "LINT_COMMANDS": ["true"],
    "BUILD_COMMANDS": ["true"],
    "PACKAGE_STACKS": [
        {
            "path": "services/api",
            "language": "Python",
            "framework": "FastAPI",
            "build_tool": None,
            "build_command": "true",
            "type_check_command": "false",
            "lint_command": "true",
        },
        {
            "path": "frontend",
            "language": "TypeScript",
            "framework": "React",
            "build_tool": "vite",
            "build_command": "true",
            "type_check_command": "true",
            "lint_command": "true",
        },
    ],
}

# Config with "N/A" commands.
_FIXTURE_CONFIG_NA = {
    "TYPE_CHECK_COMMANDS": ["N/A"],
    "LINT_COMMANDS": ["N/A"],
    "BUILD_COMMANDS": ["N/A"],
    "PACKAGE_STACKS": [
        {
            "path": "scripts",
            "language": "Python",
            "framework": None,
            "build_tool": None,
            "build_command": "N/A",
            "type_check_command": "N/A",
            "lint_command": "N/A",
        },
    ],
}


def _write_config(tmpdir, config_dict):
    """Write config_dict as .devforge/project-config.json inside tmpdir."""
    devforge = os.path.join(tmpdir, ".devforge")
    os.makedirs(devforge, exist_ok=True)
    config_path = os.path.join(devforge, "project-config.json")
    with open(config_path, "w") as f:
        json.dump(config_dict, f)
    return tmpdir


# ---------------------------------------------------------------------------
# Fake args for cmd_verify_touched
# ---------------------------------------------------------------------------


class FakeArgs:
    def __init__(self, files, root=None, iteration=0):
        self.files = files
        self.root = root
        self.iteration = iteration


def _run_verify(files_list, config, root=None, iteration=0):
    """Helper: write config to a temp dir, run cmd_verify_touched, return (rc, payload)."""
    tmpdir = tempfile.mkdtemp()
    _write_config(tmpdir, config)
    actual_root = root or tmpdir

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
        rc = cmd_verify_touched(
            FakeArgs(
                files=json.dumps(files_list),
                root=actual_root,
                iteration=iteration,
            )
        )
    output = stdout_buf.getvalue()
    payload = json.loads(output) if output.strip() else None
    return rc, payload, stderr_buf.getvalue()


# ---------------------------------------------------------------------------
# _match_package tests
# ---------------------------------------------------------------------------


class TestMatchPackage(unittest.TestCase):

    def _stacks(self):
        return [
            {"path": "services/api"},
            {"path": "frontend"},
            {"path": "services"},
        ]

    def test_file_inside_package(self):
        stacks = self._stacks()
        result = _match_package("services/api/routes.py", stacks)
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "services/api")

    def test_longest_prefix_wins(self):
        """services/api is more specific than services; it must win."""
        stacks = self._stacks()
        result = _match_package("services/api/models/user.py", stacks)
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "services/api")

    def test_shorter_prefix_wins_if_longer_does_not_match(self):
        """services/worker → matches 'services', not 'services/api'."""
        stacks = self._stacks()
        result = _match_package("services/worker/main.py", stacks)
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "services")

    def test_file_outside_all_packages(self):
        stacks = self._stacks()
        result = _match_package("top_level_script.py", stacks)
        self.assertIsNone(result)

    def test_exact_path_match(self):
        """A file whose path equals the package path exactly should match."""
        stacks = [{"path": "lib"}]
        result = _match_package("lib", stacks)
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "lib")

    def test_empty_stacks(self):
        result = _match_package("src/foo.py", [])
        self.assertIsNone(result)

    def test_package_with_no_path_skipped(self):
        stacks = [{"path": None}, {"path": "src"}]
        result = _match_package("src/main.py", stacks)
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "src")

    def test_package_path_trailing_slash_handled(self):
        """Even if a package path has a trailing slash, it should still match."""
        stacks = [{"path": "src/"}]
        result = _match_package("src/main.py", stacks)
        self.assertIsNotNone(result)

    def test_partial_name_no_false_positive(self):
        """'service' must NOT match 'services/api' (no false prefix match)."""
        stacks = [{"path": "services/api"}]
        result = _match_package("service_worker.py", stacks)
        self.assertIsNone(result)

    def test_hyphen_segment_boundary_no_false_positive(self):
        """apps/web must NOT match a file in apps/web-admin.

        The '+ /' guard in _match_package is the only defense against
        'apps/web' wrongly matching 'apps/web-admin/...'.  This regression
        test ensures the slash boundary is enforced.
        """
        stacks = [{"path": "apps/web"}, {"path": "apps/web-admin"}]
        result = _match_package("apps/web-admin/src/App.tsx", stacks)
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "apps/web-admin")


# ---------------------------------------------------------------------------
# _collect_commands tests
# ---------------------------------------------------------------------------


class TestCollectCommands(unittest.TestCase):

    def _pkg(self, path, tc="tc-cmd", lint="lint-cmd"):
        return {
            "path": path,
            "type_check_command": tc,
            "lint_command": lint,
        }

    def test_single_file_matching_package(self):
        stacks = [self._pkg("src", "tsc-src", "eslint-src")]
        tc, lint, _ = _collect_commands(["src/foo.ts"], stacks, "primary-tc", "primary-lint")
        self.assertEqual(tc, ["tsc-src"])
        self.assertEqual(lint, ["eslint-src"])

    def test_multiple_files_same_package_deduped(self):
        stacks = [self._pkg("src", "tsc-src", "eslint-src")]
        tc, lint, _ = _collect_commands(
            ["src/foo.ts", "src/bar.ts"], stacks, "primary-tc", "primary-lint"
        )
        self.assertEqual(tc, ["tsc-src"])
        self.assertEqual(lint, ["eslint-src"])

    def test_file_outside_package_uses_primary_fallback(self):
        stacks = [self._pkg("src")]
        tc, lint, _ = _collect_commands(["top_level.py"], stacks, "primary-tc", "primary-lint")
        self.assertEqual(tc, ["primary-tc"])
        self.assertEqual(lint, ["primary-lint"])

    def test_na_type_check_excluded(self):
        stacks = [self._pkg("src", tc="N/A", lint="eslint-src")]
        tc, lint, _ = _collect_commands(["src/foo.ts"], stacks, None, None)
        self.assertEqual(tc, [])
        self.assertEqual(lint, ["eslint-src"])

    def test_na_lint_excluded(self):
        stacks = [self._pkg("src", tc="tsc-src", lint="N/A")]
        tc, lint, _ = _collect_commands(["src/foo.ts"], stacks, None, None)
        self.assertEqual(tc, ["tsc-src"])
        self.assertEqual(lint, [])

    def test_none_type_check_excluded(self):
        stacks = [self._pkg("src", tc=None, lint="eslint-src")]
        tc, lint, _ = _collect_commands(["src/foo.ts"], stacks, None, None)
        self.assertEqual(tc, [])
        self.assertEqual(lint, ["eslint-src"])

    def test_mixed_package_and_non_package_files(self):
        stacks = [self._pkg("src", "tsc-src", "eslint-src")]
        tc, lint, _ = _collect_commands(
            ["src/foo.ts", "root_script.sh"], stacks, "primary-tc", "primary-lint"
        )
        # package command + primary fallback, each appears once.
        self.assertEqual(set(tc), {"tsc-src", "primary-tc"})
        self.assertEqual(set(lint), {"eslint-src", "primary-lint"})

    def test_empty_touched_files(self):
        stacks = [self._pkg("src")]
        tc, lint, _ = _collect_commands([], stacks, "primary-tc", "primary-lint")
        self.assertEqual(tc, [])
        self.assertEqual(lint, [])

    def test_two_packages_different_commands(self):
        stacks = [
            self._pkg("services/api", "api-tc", "api-lint"),
            self._pkg("frontend", "fe-tc", "fe-lint"),
        ]
        tc, lint, _ = _collect_commands(
            ["services/api/main.py", "frontend/src/App.tsx"],
            stacks,
            "primary-tc",
            "primary-lint",
        )
        self.assertEqual(set(tc), {"api-tc", "fe-tc"})
        self.assertEqual(set(lint), {"api-lint", "fe-lint"})


# ---------------------------------------------------------------------------
# _collect_build_commands tests
# ---------------------------------------------------------------------------


class TestCollectBuildCommands(unittest.TestCase):

    def _pkg(self, path, build="build-cmd"):
        return {"path": path, "build_command": build}

    def test_file_inside_package_with_build(self):
        stacks = [self._pkg("src", "npm run build:src")]
        result = _collect_build_commands(["src/foo.ts"], stacks, "primary-build")
        self.assertEqual(result, ["npm run build:src"])

    def test_file_outside_package_uses_primary_build(self):
        stacks = [self._pkg("src")]
        result = _collect_build_commands(["top.py"], stacks, "primary-build")
        self.assertIn("primary-build", result)

    def test_two_files_different_packages_two_builds(self):
        stacks = [
            self._pkg("services/api", "build-api"),
            self._pkg("frontend", "build-fe"),
        ]
        result = _collect_build_commands(
            ["services/api/m.py", "frontend/src/App.tsx"], stacks, "primary-build"
        )
        self.assertIn("build-api", result)
        self.assertIn("build-fe", result)
        self.assertNotIn("primary-build", result)

    def test_same_package_two_files_build_deduped(self):
        stacks = [self._pkg("src", "tsc")]
        result = _collect_build_commands(["src/a.ts", "src/b.ts"], stacks, "primary-build")
        self.assertEqual(result.count("tsc"), 1)

    def test_na_build_excluded(self):
        stacks = [self._pkg("src", "N/A")]
        result = _collect_build_commands(["src/foo.ts"], stacks, "primary-build")
        self.assertNotIn("N/A", result)

    def test_empty_touched_files_primary_build_runs_once(self):
        """No touched files + a primary build → build runs once (end-of-task)."""
        stacks = [self._pkg("src")]
        result = _collect_build_commands([], stacks, "primary-build")
        self.assertEqual(result, ["primary-build"])

    def test_empty_touched_files_no_primary_build(self):
        stacks = []
        result = _collect_build_commands([], stacks, None)
        self.assertEqual(result, [])

    def test_none_build_command_excluded(self):
        stacks = [{"path": "src", "build_command": None}]
        result = _collect_build_commands(["src/foo.ts"], stacks, "primary-build")
        self.assertNotIn(None, result)
        # Non-matching packages fall through to primary.
        # But our file DOES match 'src', with None build → not added.
        # Only primary would be added if the file DIDN'T match a package;
        # since it matches but build is None → no build cmd from the package.
        # Primary is NOT added here (file matched a package; primary only for non-matches).
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# cmd_verify_touched integration tests
# ---------------------------------------------------------------------------


class TestCmdVerifyTouched(unittest.TestCase):

    # --- Pass path ---

    def test_all_pass_status_pass(self):
        """All commands pass → {status: 'pass'} exit 0."""
        rc, payload, _ = _run_verify(
            ["services/api/main.py"], _FIXTURE_CONFIG, iteration=0
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "pass")
        self.assertIn("commands_run", payload)
        self.assertIn("build_commands_run", payload)
        self.assertIn("test_commands_run", payload)

    def test_pass_contains_commands_run(self):
        """Pass payload includes the list of commands that ran."""
        rc, payload, _ = _run_verify(
            ["services/api/main.py"], _FIXTURE_CONFIG, iteration=0
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertIsInstance(payload["commands_run"], list)
        self.assertIsInstance(payload["build_commands_run"], list)
        self.assertIsInstance(payload["test_commands_run"], list)

    # --- Self-repair iterations 0, 1, 2 ---

    def test_fail_at_iteration_0_self_repair(self):
        """Failing command at iteration 0 → self_repair, exit 0."""
        rc, payload, _ = _run_verify(
            ["services/api/main.py"], _FIXTURE_CONFIG_FAIL_API, iteration=0
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "self_repair")
        self.assertEqual(payload["iteration"], 0)
        self.assertIn("failed_command", payload)
        self.assertIn("output", payload)

    def test_fail_at_iteration_1_self_repair(self):
        """Failing command at iteration 1 → self_repair, exit 0."""
        rc, payload, _ = _run_verify(
            ["services/api/main.py"], _FIXTURE_CONFIG_FAIL_API, iteration=1
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "self_repair")
        self.assertEqual(payload["iteration"], 1)

    def test_fail_at_iteration_2_self_repair(self):
        """Failing command at iteration 2 → self_repair, exit 0 (still below cap=3)."""
        rc, payload, _ = _run_verify(
            ["services/api/main.py"], _FIXTURE_CONFIG_FAIL_API, iteration=2
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "self_repair")
        self.assertEqual(payload["iteration"], 2)

    def test_fail_at_iteration_3_failed_exit2(self):
        """Failing command at iteration 3 → {status:'failed'} exit 2 (cap reached)."""
        rc, payload, _ = _run_verify(
            ["services/api/main.py"], _FIXTURE_CONFIG_FAIL_API, iteration=3
        )
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertEqual(payload["status"], "failed")
        self.assertIn("failed_command", payload)
        self.assertIn("output", payload)

    def test_self_repair_cap_constant_is_3(self):
        """The SELF_REPAIR_CAP constant is 3 (not 2, not 4)."""
        self.assertEqual(SELF_REPAIR_CAP, 3)

    # --- N/A handling ---

    def test_na_commands_skipped_silently(self):
        """All N/A commands → nothing runs, result is pass."""
        rc, payload, stderr = _run_verify(
            ["scripts/deploy.sh"], _FIXTURE_CONFIG_NA, iteration=0
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "pass")
        # No error output.
        self.assertEqual(stderr, "")

    # --- Package selection ---

    def test_file_in_api_uses_api_commands(self):
        """File in services/api → api commands, not frontend commands."""
        # Use a config where api has 'true' commands and frontend has 'false'.
        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [
                {
                    "path": "services/api",
                    "type_check_command": "true",
                    "lint_command": "true",
                    "build_command": "true",
                    "language": "Python",
                    "framework": None,
                    "build_tool": None,
                },
                {
                    "path": "frontend",
                    "type_check_command": "false",
                    "lint_command": "false",
                    "build_command": "false",
                    "language": "TypeScript",
                    "framework": "React",
                    "build_tool": "vite",
                },
            ],
        }
        rc, payload, _ = _run_verify(
            ["services/api/routes.py"], config, iteration=0
        )
        # Only api commands ran (all 'true') → pass.
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "pass")

    def test_file_outside_packages_uses_primary_fallback(self):
        """File not in any package → primary fallback commands."""
        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [
                {
                    "path": "services/api",
                    "type_check_command": "false",  # would fail if run
                    "lint_command": "false",
                    "build_command": "false",
                    "language": "Python",
                    "framework": None,
                    "build_tool": None,
                },
            ],
        }
        # top_level.py is outside 'services/api' → uses primary fallback (true).
        rc, payload, _ = _run_verify(
            ["top_level.py"], config, iteration=0
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "pass")

    def test_deduplication_two_files_same_package_one_command(self):
        """Two files in the same package → each command runs once (not twice).

        Uses distinct command strings per slot (tc-api, lint-api, build-api)
        so we can count per-command invocations unambiguously.
        """
        # Config with distinct command names per slot so counting is unambiguous.
        config = {
            "TYPE_CHECK_COMMANDS": ["primary-tc"],
            "LINT_COMMANDS": ["primary-lint"],
            "BUILD_COMMANDS": ["primary-build"],
            "PACKAGE_STACKS": [
                {
                    "path": "services/api",
                    "type_check_command": "tc-api",
                    "lint_command": "lint-api",
                    "build_command": "build-api",
                    "language": "Python",
                    "framework": None,
                    "build_tool": None,
                },
            ],
        }

        commands_called = []

        def mock_run(cmd, cwd, extra_paths=None):
            commands_called.append(cmd)
            return 0, ""

        import _implement._cmds_verify as verify_mod
        original = verify_mod._run_command
        verify_mod._run_command = mock_run
        try:
            tmpdir = tempfile.mkdtemp()
            _write_config(tmpdir, config)
            cmd_verify_touched(
                FakeArgs(
                    files=json.dumps(
                        ["services/api/a.py", "services/api/b.py"]
                    ),
                    root=tmpdir,
                    iteration=0,
                )
            )
        finally:
            verify_mod._run_command = original

        # Count how many times each distinct command was called.
        from collections import Counter
        counts = Counter(commands_called)
        # Each command must appear exactly once (de-duped within its slot).
        self.assertEqual(
            counts.get("tc-api", 0), 1,
            msg="tc-api should run exactly once",
        )
        self.assertEqual(
            counts.get("lint-api", 0), 1,
            msg="lint-api should run exactly once",
        )
        self.assertEqual(
            counts.get("build-api", 0), 1,
            msg="build-api should run exactly once",
        )
        # Primary fallback commands must NOT run (both files matched the package).
        self.assertNotIn("primary-tc", commands_called)
        self.assertNotIn("primary-lint", commands_called)
        self.assertNotIn("primary-build", commands_called)

    # --- Error paths ---

    def test_missing_project_config_exit1(self):
        """No .devforge/project-config.json → exit 1, message on stderr."""
        tmpdir = tempfile.mkdtemp()
        # Don't create the config file.
        stderr_buf = io.StringIO()
        with patch("sys.stderr", stderr_buf):
            rc = cmd_verify_touched(
                FakeArgs(
                    files="[]",
                    root=tmpdir,
                    iteration=0,
                )
            )
        self.assertEqual(rc, EXIT_ERR)
        self.assertIn("project-config.json", stderr_buf.getvalue())

    def test_invalid_files_json_exit1(self):
        """Non-JSON --files → exit 1, message on stderr."""
        tmpdir = tempfile.mkdtemp()
        _write_config(tmpdir, _FIXTURE_CONFIG)
        stderr_buf = io.StringIO()
        with patch("sys.stderr", stderr_buf):
            rc = cmd_verify_touched(
                FakeArgs(
                    files="not-json",
                    root=tmpdir,
                    iteration=0,
                )
            )
        self.assertEqual(rc, EXIT_ERR)
        self.assertIn("files", stderr_buf.getvalue().lower())

    def test_files_not_list_exit1(self):
        """--files that is valid JSON but not an array → exit 1."""
        tmpdir = tempfile.mkdtemp()
        _write_config(tmpdir, _FIXTURE_CONFIG)
        stderr_buf = io.StringIO()
        with patch("sys.stderr", stderr_buf):
            rc = cmd_verify_touched(
                FakeArgs(
                    files=json.dumps({"key": "val"}),
                    root=tmpdir,
                    iteration=0,
                )
            )
        self.assertEqual(rc, EXIT_ERR)

    def test_empty_files_list_no_primary_commands(self):
        """Empty touched files + no primary commands → pass with empty lists."""
        config = {
            "TYPE_CHECK_COMMANDS": [],
            "LINT_COMMANDS": [],
            "BUILD_COMMANDS": [],
            "PACKAGE_STACKS": [],
        }
        rc, payload, _ = _run_verify([], config, iteration=0)
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["commands_run"], [])
        self.assertEqual(payload["build_commands_run"], [])

    def test_output_is_valid_json(self):
        """Emitted stdout is always valid JSON regardless of outcome."""
        tmpdir = tempfile.mkdtemp()
        _write_config(tmpdir, _FIXTURE_CONFIG)
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            cmd_verify_touched(
                FakeArgs(
                    files=json.dumps(["services/api/main.py"]),
                    root=tmpdir,
                    iteration=0,
                )
            )
        output = stdout_buf.getvalue()
        parsed = json.loads(output)
        self.assertIsInstance(parsed, dict)
        self.assertIn("status", parsed)

    def test_failed_payload_includes_failed_command_and_output(self):
        """Failed payload has failed_command and output fields."""
        rc, payload, _ = _run_verify(
            ["services/api/main.py"], _FIXTURE_CONFIG_FAIL_API, iteration=3
        )
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIn("failed_command", payload)
        self.assertIn("output", payload)
        self.assertIsInstance(payload["failed_command"], str)
        self.assertIsInstance(payload["output"], str)

    def test_self_repair_payload_includes_iteration(self):
        """Self-repair payload includes the iteration number from --iteration arg."""
        rc, payload, _ = _run_verify(
            ["services/api/main.py"], _FIXTURE_CONFIG_FAIL_API, iteration=1
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["iteration"], 1)


# ---------------------------------------------------------------------------
# Wrapper-mode integration tests
# ---------------------------------------------------------------------------


def _make_wrapper_install(source_repo_name="src-repo"):
    # type: (str) -> tuple
    """Create a two-repo wrapper fixture in a temp directory.

    Layout:
      <install_dir>/
        .devforge/project-config.json   (PROJECT_ROOT = source_repo_name)
        <source_repo_name>/             (source root — where commands should run)
          seed.txt

    Returns (install_dir_str, source_dir_str) as strings.
    The caller is responsible for cleanup (shutil.rmtree).
    """
    import shutil
    install_dir = tempfile.mkdtemp()
    devforge = os.path.join(install_dir, ".devforge")
    os.makedirs(devforge, exist_ok=True)
    config = {"PROJECT_ROOT": source_repo_name}
    with open(os.path.join(devforge, "project-config.json"), "w") as f:
        json.dump(config, f)

    source_dir = os.path.join(install_dir, source_repo_name)
    os.makedirs(source_dir, exist_ok=True)
    # Write a seed file so the source dir looks like a real project.
    with open(os.path.join(source_dir, "seed.txt"), "w") as f:
        f.write("initial\n")

    return install_dir, source_dir


class TestCmdVerifyTouchedWrapper(unittest.TestCase):
    """Wrapper-mode integration tests for cmd_verify_touched."""

    def setUp(self):
        self.install_dir, self.source_dir = _make_wrapper_install("src-repo")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.install_dir, ignore_errors=True)

    def _write_config(self, config_dict):
        """Write config_dict as .devforge/project-config.json (overwrite)."""
        devforge = os.path.join(self.install_dir, ".devforge")
        os.makedirs(devforge, exist_ok=True)
        # Merge PROJECT_ROOT into the config so resolve_workspace still sees it.
        merged = dict(config_dict)
        if "PROJECT_ROOT" not in merged:
            merged["PROJECT_ROOT"] = "src-repo"
        config_path = os.path.join(devforge, "project-config.json")
        with open(config_path, "w") as f:
            json.dump(merged, f)

    def _run(self, files_list, config_dict, iteration=0):
        """Write config to install root, run cmd_verify_touched, return (rc, payload)."""
        self._write_config(config_dict)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            rc = cmd_verify_touched(
                FakeArgs(
                    files=json.dumps(files_list),
                    root=self.install_dir,
                    iteration=iteration,
                )
            )
        output = stdout_buf.getvalue()
        payload = json.loads(output) if output.strip() else None
        return rc, payload, stderr_buf.getvalue()

    def test_wrapper_command_runs_with_cwd_source_root(self):
        """Wrapper mode: commands run with cwd = source_root.

        We use a command that writes the current working directory to a temp
        file, then assert the written path equals source_root.
        """
        cwd_record = os.path.join(self.install_dir, "recorded_cwd.txt")
        # The command writes $(pwd) to a file.  It runs with shell=True in
        # cmd_verify_touched, so $(pwd) resolves correctly.
        record_cmd = "pwd > {0}".format(cwd_record)

        config = {
            "TYPE_CHECK_COMMANDS": [record_cmd],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [
                {
                    "path": ".",
                    "language": "TypeScript",
                    "framework": None,
                    "build_tool": None,
                    "build_command": "true",
                    "type_check_command": record_cmd,
                    "lint_command": "true",
                },
            ],
        }
        rc, payload, stderr = self._run(["src/widget.ts"], config, iteration=0)
        self.assertEqual(rc, EXIT_OK, msg="expected pass; stderr={0!r}".format(stderr))
        self.assertEqual(payload["status"], "pass")

        # Read the recorded cwd.
        self.assertTrue(
            os.path.exists(cwd_record),
            "record file must exist after command ran; source_dir={0!r}".format(
                self.source_dir
            ),
        )
        with open(cwd_record) as f:
            recorded = f.read().strip()
        # The recorded path must be the (resolved) source_root.
        self.assertEqual(
            os.path.realpath(recorded),
            os.path.realpath(self.source_dir),
            "Command must run with cwd = source_root"
            "; recorded={0!r}, expected={1!r}".format(recorded, self.source_dir),
        )

    def test_wrapper_non_package_file_primary_fallback_in_source_root(self):
        """Wrapper mode: non-package file uses primary-stack fallback, still cwd=source_root."""
        cwd_record = os.path.join(self.install_dir, "fallback_cwd.txt")
        primary_cmd = "pwd > {0}".format(cwd_record)

        config = {
            "TYPE_CHECK_COMMANDS": [primary_cmd],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [
                {
                    "path": "services/api",
                    "language": "Python",
                    "framework": None,
                    "build_tool": None,
                    "build_command": "true",
                    "type_check_command": "false",  # would fail if run
                    "lint_command": "false",
                },
            ],
        }
        # top_level.py doesn't match services/api → uses primary fallback.
        rc, payload, stderr = self._run(["top_level.py"], config, iteration=0)
        self.assertEqual(rc, EXIT_OK, msg="expected pass; stderr={0!r}".format(stderr))
        self.assertEqual(payload["status"], "pass")

        self.assertTrue(os.path.exists(cwd_record), "Primary fallback must have run")
        with open(cwd_record) as f:
            recorded = f.read().strip()
        self.assertEqual(
            os.path.realpath(recorded),
            os.path.realpath(self.source_dir),
            "Primary-stack fallback must also run with cwd = source_root"
            "; recorded={0!r}, expected={1!r}".format(recorded, self.source_dir),
        )

    def test_wrapper_isolation_failure_on_forge_artifact(self):
        """Wrapper mode: a forge artifact inside source_root → isolation_failure exit 2."""
        # Plant a CLAUDE.md inside the source repo (simulating agent pollution).
        claude_md = os.path.join(self.source_dir, "CLAUDE.md")
        with open(claude_md, "w") as f:
            f.write("# CLAUDE\nPolluted by agent.\n")

        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload, _ = self._run(["src/widget.ts"], config, iteration=0)
        self.assertEqual(rc, EXIT_FINDINGS, "isolation failure must exit 2")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "isolation_failure")
        self.assertIn("artifacts", payload)
        self.assertIn("CLAUDE.md", payload["artifacts"])

    def test_wrapper_isolation_failure_on_specs_dir(self):
        """Wrapper mode: a specs/ directory inside source_root → isolation_failure."""
        specs_dir = os.path.join(self.source_dir, "specs")
        os.makedirs(specs_dir, exist_ok=True)
        with open(os.path.join(specs_dir, "001-widget.md"), "w") as f:
            f.write("# Spec\n")

        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload, _ = self._run([], config, iteration=0)
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertEqual(payload["status"], "isolation_failure")
        self.assertIn("specs", payload["artifacts"])

    def test_wrapper_isolation_failure_on_dot_claude(self):
        """Wrapper mode: a .claude/ directory inside source_root → isolation_failure."""
        dot_claude = os.path.join(self.source_dir, ".claude")
        os.makedirs(dot_claude, exist_ok=True)

        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload, _ = self._run([], config, iteration=0)
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertEqual(payload["status"], "isolation_failure")
        self.assertIn(".claude", payload["artifacts"])

    def test_wrapper_clean_source_root_passes(self):
        """Wrapper mode: no forge artifacts in source_root → verification proceeds normally."""
        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload, stderr = self._run([], config, iteration=0)
        self.assertEqual(rc, EXIT_OK, msg="expected pass; stderr={0!r}".format(stderr))
        self.assertEqual(payload["status"], "pass")

    def test_standalone_isolation_check_skipped_with_claude_md(self):
        """Standalone: CLAUDE.md in root does NOT trigger isolation failure.

        A standalone repo legitimately contains CLAUDE.md, .claude/, specs/, etc.
        The isolation check must be skipped entirely (is_wrapper is False).
        """
        # Overwrite config with NO PROJECT_ROOT → standalone.
        devforge = os.path.join(self.install_dir, ".devforge")
        os.makedirs(devforge, exist_ok=True)
        standalone_config = {
            # No PROJECT_ROOT → resolve_workspace returns standalone.
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        with open(os.path.join(devforge, "project-config.json"), "w") as f:
            json.dump(standalone_config, f)

        # Plant a CLAUDE.md in the install_root (a LEGITIMATE standalone file).
        claude_md = os.path.join(self.install_dir, "CLAUDE.md")
        with open(claude_md, "w") as f:
            f.write("# CLAUDE\nLegitimate standalone file.\n")

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            rc = cmd_verify_touched(
                FakeArgs(
                    files=json.dumps([]),
                    root=self.install_dir,
                    iteration=0,
                )
            )
        output = stdout_buf.getvalue()
        payload = json.loads(output) if output.strip() else None
        self.assertEqual(rc, EXIT_OK, "standalone with CLAUDE.md must NOT fail isolation check")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "pass",
                         "isolation check must be skipped in standalone mode")

    def test_isolation_failure_reported_before_commands_run(self):
        """Wrapper isolation failure is emitted before running type-check commands.

        Use a failing type-check command and plant a forge artifact.
        The isolation failure must be reported (not a self_repair from the
        failing command), proving the isolation check runs first.
        """
        claude_md = os.path.join(self.source_dir, "CLAUDE.md")
        with open(claude_md, "w") as f:
            f.write("# Polluted\n")

        config = {
            "TYPE_CHECK_COMMANDS": ["false"],   # would trigger self_repair if reached
            "LINT_COMMANDS": ["false"],
            "BUILD_COMMANDS": ["false"],
            "PACKAGE_STACKS": [],
        }
        rc, payload, _ = self._run([], config, iteration=0)
        # Must be isolation_failure, NOT self_repair.
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertEqual(payload["status"], "isolation_failure",
                         "isolation check must run before type-check commands")


class TestCheckWrapperIsolation(unittest.TestCase):
    """Unit tests for _check_wrapper_isolation."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.source_root = Path(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _import_check(self):
        from _implement._cmds_verify import _check_wrapper_isolation
        return _check_wrapper_isolation

    def test_clean_source_root_returns_empty(self):
        check = self._import_check()
        result = check(self.source_root)
        self.assertEqual(result, [])

    def test_claude_md_found(self):
        check = self._import_check()
        (self.source_root / "CLAUDE.md").write_text("# C\n")
        result = check(self.source_root)
        self.assertIn("CLAUDE.md", result)

    def test_dot_claude_dir_found(self):
        check = self._import_check()
        (self.source_root / ".claude").mkdir()
        result = check(self.source_root)
        self.assertIn(".claude", result)

    def test_specs_dir_found(self):
        check = self._import_check()
        (self.source_root / "specs").mkdir()
        result = check(self.source_root)
        self.assertIn("specs", result)

    def test_constitution_md_found(self):
        check = self._import_check()
        (self.source_root / "constitution.md").write_text("# C\n")
        result = check(self.source_root)
        self.assertIn("constitution.md", result)

    def test_mcp_json_found(self):
        check = self._import_check()
        (self.source_root / ".mcp.json").write_text("{}\n")
        result = check(self.source_root)
        self.assertIn(".mcp.json", result)

    def test_docs_overview_found(self):
        check = self._import_check()
        docs = self.source_root / "docs"
        docs.mkdir()
        (docs / "overview.md").write_text("# Docs\n")
        result = check(self.source_root)
        self.assertIn("docs/overview.md", result)

    def test_multiple_artifacts_all_reported(self):
        check = self._import_check()
        (self.source_root / "CLAUDE.md").write_text("# C\n")
        (self.source_root / "specs").mkdir()
        result = check(self.source_root)
        self.assertIn("CLAUDE.md", result)
        self.assertIn("specs", result)

    def test_unrelated_files_not_reported(self):
        check = self._import_check()
        (self.source_root / "src").mkdir()
        (self.source_root / "src" / "widget.ts").write_text("export {};\n")
        result = check(self.source_root)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# _is_tooling_unavailable unit tests
# ---------------------------------------------------------------------------


class TestIsToolingUnavailable(unittest.TestCase):
    """Unit tests for the _is_tooling_unavailable classifier.

    Each anchored signal is tested positively; then negative/false-positive
    cases confirm generic substrings (e.g. TS diagnostics) do NOT trigger.
    """

    # --- Positive: returncode 127 ---

    def test_rc127_empty_output_true(self):
        """rc=127 with no shell message is still tooling-unavailable."""
        self.assertTrue(_is_tooling_unavailable(127, ""))

    def test_rc127_with_command_not_found_message(self):
        """rc=127 + 'command not found' in output → True."""
        self.assertTrue(
            _is_tooling_unavailable(127, "/bin/sh: vue-tsc: command not found")
        )

    # --- Positive: anchored shell message strings ---

    def test_command_not_found_rc1_true(self):
        """'command not found' substring triggers regardless of returncode."""
        self.assertTrue(
            _is_tooling_unavailable(1, "sh: 1: vue-tsc: command not found\n")
        )

    def test_rc127_triggers_regardless_of_output_content(self):
        """rc=127 alone is sufficient to classify as tooling-unavailable.

        The signal strings are not operative for rc=127 — the returncode check
        is unconditional.  This test uses a neutral output to confirm the
        returncode branch is what fires, independent of any string match.
        """
        self.assertTrue(
            _is_tooling_unavailable(127, "sh: vue-tsc: not found\n")
        )

    def test_colon_not_found_rc0_is_false(self):
        """': not found' with rc=0 → False.

        In production, cmd_verify_touched invokes this classifier only inside
        `if rc != 0:`, so rc=0 is structurally unreachable from the loop.
        This test exercises the classifier's own contract independently.

        ': not found' was removed from _TOOLING_UNAVAILABLE_SIGNALS because
        it appears in real bundler/loader diagnostics (Webpack, Vite) and
        would cause false-positive tooling_unavailable results for agent-fixable
        config errors.  With rc=0 and no other signal, the result is False.
        """
        self.assertFalse(_is_tooling_unavailable(0, "mybin: not found"))

    def test_colon_not_found_rc1_is_false(self):
        """': not found' with rc=1 (bundler/loader diagnostic) → False.

        This is the core false-positive guard for Finding 2.  Webpack outputs
        "Error: Loader: not found for .vue files" (exit 1), Vite outputs
        "Plugin: not found: @vitejs/plugin-vue" (exit 1) — neither is a
        missing-binary case.  ': not found' must NOT trigger tooling_unavailable.
        """
        self.assertFalse(
            _is_tooling_unavailable(1, "Error: Loader: not found for .vue files\n")
        )

    def test_vite_plugin_not_found_is_false(self):
        """Vite 'Plugin: not found' diagnostic with rc=1 → False."""
        self.assertFalse(
            _is_tooling_unavailable(1, "Plugin: not found: @vitejs/plugin-vue\n")
        )

    def test_windows_not_recognized_signal_true(self):
        """Windows 'not recognized as an internal or external command' → True."""
        self.assertTrue(
            _is_tooling_unavailable(
                1,
                "'vue-tsc' is not recognized as an internal or external command,\r\n"
                "operable program or batch file.\r\n",
            )
        )

    def test_case_insensitive_command_not_found(self):
        """Signal matching is case-insensitive ('Command Not Found' → True)."""
        self.assertTrue(
            _is_tooling_unavailable(127, "Command Not Found: vue-tsc")
        )

    def test_case_insensitive_not_recognized(self):
        """Windows signal is matched case-insensitively."""
        self.assertTrue(
            _is_tooling_unavailable(
                1, "'FOO' Is Not Recognized As An Internal Or External Command"
            )
        )

    # --- Negative: generic 'not found' must NOT trigger ---

    def test_typescript_cannot_find_module_false(self):
        """tsc 'Cannot find module' must NOT be classified as tooling-unavailable."""
        ts_output = (
            "src/index.ts(1,20): error TS2307: Cannot find module 'react'\n"
            "    or its corresponding type declarations.\n"
        )
        self.assertFalse(_is_tooling_unavailable(1, ts_output))

    def test_typescript_cannot_find_name_false(self):
        """tsc 'Cannot find name' must NOT be classified as tooling-unavailable."""
        ts_output = (
            "src/widget.ts(5,10): error TS2304: Cannot find name 'MyComponent'\n"
        )
        self.assertFalse(_is_tooling_unavailable(2, ts_output))

    def test_eslint_no_such_rule_false(self):
        """ESLint 'Definition not found' text must NOT trigger."""
        eslint_output = "Definition not found for rule: react-hooks/rules-of-hooks\n"
        self.assertFalse(_is_tooling_unavailable(1, eslint_output))

    def test_rc1_no_shell_signal_false(self):
        """Non-zero rc with real compiler output → False."""
        self.assertFalse(_is_tooling_unavailable(1, "error: type mismatch on line 10\n"))

    def test_rc2_no_shell_signal_false(self):
        """rc=2 (common for tsc strict mode) with no shell signal → False."""
        self.assertFalse(
            _is_tooling_unavailable(2, "Found 3 errors in 2 files.\n")
        )

    def test_rc0_clean_output_false(self):
        """rc=0 with clean output → False (success, not tooling-unavailable)."""
        self.assertFalse(_is_tooling_unavailable(0, ""))

    def test_generic_not_found_alone_false(self):
        """'not found' alone (without the ': ' prefix) must NOT trigger.

        This guards against the unanchored-substring anti-pattern.
        'Cannot find module' contains 'not found' but must return False.
        """
        self.assertFalse(_is_tooling_unavailable(1, "File not found: config.json\n"))

    def test_partial_not_found_phrase_false(self):
        """'not found' in a message about a missing config file → False."""
        self.assertFalse(
            _is_tooling_unavailable(1, "tsconfig.json not found in project root\n")
        )


# ---------------------------------------------------------------------------
# tooling_unavailable integration tests (via cmd_verify_touched)
# ---------------------------------------------------------------------------


class TestToolingUnavailableIntegration(unittest.TestCase):
    """Integration tests for the tooling_unavailable status through cmd_verify_touched.

    Uses monkeypatching of _run_command (same pattern as the deduplication test
    above) so we can simulate exact returncode+output combinations without
    requiring real missing binaries.
    """

    def _run_with_mock(self, files_list, config, mock_run_fn, iteration=0):
        """Write config, patch _run_command, run cmd_verify_touched, return (rc, payload)."""
        import _implement._cmds_verify as verify_mod

        tmpdir = tempfile.mkdtemp()
        _write_config(tmpdir, config)

        original = verify_mod._run_command
        verify_mod._run_command = mock_run_fn

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        try:
            with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
                rc = cmd_verify_touched(
                    FakeArgs(
                        files=json.dumps(files_list),
                        root=tmpdir,
                        iteration=iteration,
                    )
                )
        finally:
            verify_mod._run_command = original

        output = stdout_buf.getvalue()
        payload = json.loads(output) if output.strip() else None
        return rc, payload

    def test_missing_command_rc127_tooling_unavailable(self):
        """A command returning rc=127 with 'command not found' → tooling_unavailable, exit 2."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 127, "/bin/sh: vue-tsc: command not found\n"

        config = {
            "TYPE_CHECK_COMMANDS": ["vue-tsc --noEmit"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload = self._run_with_mock(["src/App.vue"], config, mock_run, iteration=0)

        self.assertEqual(rc, EXIT_FINDINGS, "tooling_unavailable must exit 2")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "tooling_unavailable")
        self.assertEqual(payload["failed_command"], "vue-tsc --noEmit")
        self.assertIn("output", payload)

    def test_missing_command_windows_signal_tooling_unavailable(self):
        """Windows 'not recognized' output → tooling_unavailable, exit 2."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 1, (
                "'vue-tsc' is not recognized as an internal or external command,\r\n"
                "operable program or batch file.\r\n"
            )

        config = {
            "TYPE_CHECK_COMMANDS": ["vue-tsc --noEmit"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload = self._run_with_mock(["src/App.vue"], config, mock_run, iteration=0)

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "tooling_unavailable")

    def test_tooling_unavailable_does_not_self_repair(self):
        """tooling_unavailable must NOT enter the self_repair path even at iteration=0."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 127, "sh: missing-linter: command not found\n"

        config = {
            "TYPE_CHECK_COMMANDS": ["missing-linter"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload = self._run_with_mock(["src/foo.ts"], config, mock_run, iteration=0)

        self.assertNotEqual(payload["status"], "self_repair",
                            "tooling_unavailable must short-circuit before self_repair logic")
        self.assertEqual(payload["status"], "tooling_unavailable")
        self.assertEqual(rc, EXIT_FINDINGS)

    def test_tooling_unavailable_stops_remaining_commands(self):
        """When the first command is tooling-unavailable, remaining commands must NOT run."""
        commands_called = []

        def mock_run(cmd, cwd, extra_paths=None):
            commands_called.append(cmd)
            if cmd == "bad-tool --check":
                return 127, "sh: bad-tool: command not found\n"
            # This second command would pass, but must never be reached.
            return 0, ""

        config = {
            "TYPE_CHECK_COMMANDS": ["bad-tool --check"],
            "LINT_COMMANDS": ["eslint ."],
            "BUILD_COMMANDS": ["npm run build"],
            "PACKAGE_STACKS": [],
        }
        rc, payload = self._run_with_mock(["src/foo.ts"], config, mock_run, iteration=0)

        self.assertEqual(payload["status"], "tooling_unavailable")
        # Only the failing command should have been called; remaining must be skipped.
        self.assertEqual(commands_called, ["bad-tool --check"],
                         "Remaining commands after tooling_unavailable must NOT run")

    def test_genuine_code_failure_still_self_repairs(self):
        """tsc exit 1 with real TS diagnostics must still produce self_repair (not tooling_unavailable)."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 1, (
                "src/widget.ts(5,10): error TS2304: Cannot find name 'MyWidget'\n"
                "Found 1 error.\n"
            )

        config = {
            "TYPE_CHECK_COMMANDS": ["npx tsc --noEmit"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload = self._run_with_mock(["src/widget.ts"], config, mock_run, iteration=0)

        self.assertEqual(rc, EXIT_OK, "self_repair must exit 0")
        self.assertEqual(payload["status"], "self_repair")
        self.assertEqual(payload["iteration"], 0)

    def test_webpack_loader_not_found_diagnostic_is_self_repair(self):
        """Webpack 'Loader: not found' diagnostic (rc=1) → self_repair, NOT tooling_unavailable.

        This is the critical false-positive guard for the ': not found' removal.
        A Webpack or Vite bundler error about a missing loader/plugin is a
        genuine, agent-fixable config error (exit 1) — not a missing binary.
        It must go through the self-repair path so the implementing agent can
        fix the config, not be short-circuited as tooling_unavailable.
        """
        def mock_run(cmd, cwd, extra_paths=None):
            return 1, "Error: Loader: not found for .vue files\n"

        config = {
            "TYPE_CHECK_COMMANDS": ["webpack --check"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload = self._run_with_mock(["src/App.vue"], config, mock_run, iteration=0)

        self.assertEqual(rc, EXIT_OK, "bundler config error must exit 0 (self_repair)")
        self.assertEqual(
            payload["status"], "self_repair",
            "': not found' in bundler output with rc=1 must NOT produce tooling_unavailable"
        )
        self.assertEqual(payload["iteration"], 0)

    def test_vite_plugin_not_found_diagnostic_is_self_repair(self):
        """Vite 'Plugin: not found' diagnostic (rc=1) → self_repair, NOT tooling_unavailable."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 1, "Plugin: not found: @vitejs/plugin-vue\nError: Build failed.\n"

        config = {
            "TYPE_CHECK_COMMANDS": ["vite build"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload = self._run_with_mock(["src/App.vue"], config, mock_run, iteration=0)

        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(
            payload["status"], "self_repair",
            "Vite plugin-not-found config error must be self_repair, not tooling_unavailable"
        )

    def test_genuine_code_failure_at_cap_fails_not_tooling_unavailable(self):
        """tsc exit 2 with real diagnostics at cap → failed (not tooling_unavailable)."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 2, "Found 3 errors in 2 files.\n"

        config = {
            "TYPE_CHECK_COMMANDS": ["npx tsc --noEmit"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload = self._run_with_mock(
            ["src/widget.ts"], config, mock_run, iteration=SELF_REPAIR_CAP
        )

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertEqual(payload["status"], "failed",
                         "real compiler errors at cap must be 'failed', not 'tooling_unavailable'")

    def test_all_pass_unchanged_after_feature(self):
        """All-pass case is unaffected by the new tooling_unavailable path."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 0, ""

        config = {
            "TYPE_CHECK_COMMANDS": ["npx tsc --noEmit"],
            "LINT_COMMANDS": ["eslint ."],
            "BUILD_COMMANDS": ["npm run build"],
            "PACKAGE_STACKS": [],
        }
        rc, payload = self._run_with_mock(["src/foo.ts"], config, mock_run, iteration=0)

        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "pass")


# ---------------------------------------------------------------------------
# Node bin resolution tests for _run_command and cmd_verify_touched
# ---------------------------------------------------------------------------


class TestNodeBinResolutionRunCommand(unittest.TestCase):
    """Unit tests for _run_command's extra_paths / PATH augmentation.

    These tests import _run_command directly and verify:
    - extra_paths=None → os.environ unchanged (no mutation check).
    - extra_paths=["/some/bin"] → those dirs appear in subprocess PATH.
    - os.environ is NOT mutated after the call.
    """

    def _import_run_command(self):
        from _implement._cmds_verify import _run_command
        return _run_command

    def test_no_extra_paths_uses_current_env(self):
        """extra_paths=None → subprocess inherits PATH unchanged; no mutation."""
        _run_command = self._import_run_command()
        original_path = os.environ.get("PATH", "")
        _run_command("true", "/tmp", extra_paths=None)
        self.assertEqual(os.environ.get("PATH", ""), original_path,
                         "os.environ must not be mutated")

    def test_extra_paths_empty_list_no_mutation(self):
        """extra_paths=[] (empty) → os.environ not mutated."""
        _run_command = self._import_run_command()
        original_path = os.environ.get("PATH", "")
        _run_command("true", "/tmp", extra_paths=[])
        self.assertEqual(os.environ.get("PATH", ""), original_path,
                         "empty extra_paths must not mutate os.environ")

    def test_extra_paths_prepended_to_path(self):
        """extra_paths prepended → a script in that dir is found and runs."""
        import tempfile as _tempfile
        import stat as _stat

        _run_command = self._import_run_command()
        tmpdir = _tempfile.mkdtemp()
        try:
            # Create a fake executable in tmpdir.
            script_path = os.path.join(tmpdir, "my-fake-tool")
            with open(script_path, "w") as fh:
                fh.write("#!/bin/sh\necho hello\n")
            os.chmod(script_path, _stat.S_IRWXU)

            # The tool is NOT on the global PATH (it's in tmpdir only).
            import shutil as _shutil
            self.assertIsNone(_shutil.which("my-fake-tool"),
                              "precondition: tool must not be on global PATH")

            rc, output = _run_command("my-fake-tool", "/tmp", extra_paths=[tmpdir])
            self.assertEqual(rc, 0, "command in extra_paths dir must succeed (rc=0)")
            self.assertIn("hello", output)
        finally:
            import shutil as _shutil
            _shutil.rmtree(tmpdir, ignore_errors=True)

    def test_os_environ_not_mutated_after_extra_paths(self):
        """os.environ PATH is exactly unchanged after _run_command with extra_paths."""
        _run_command = self._import_run_command()
        before = dict(os.environ)
        _run_command("true", "/tmp", extra_paths=["/some/fake/bin"])
        after = dict(os.environ)
        self.assertEqual(before.get("PATH"), after.get("PATH"),
                         "os.environ PATH must not be mutated after call with extra_paths")


class TestNodeBinResolutionIntegration(unittest.TestCase):
    """Integration tests for cmd_verify_touched with node_modules/.bin resolution.

    Exercises the full path from cmd_verify_touched down through _run_command:
    - Binary in <source_root>/node_modules/.bin → pass (not tooling_unavailable).
    - Binary in <source_root>/<pkg>/node_modules/.bin → pass.
    - Genuinely missing binary → tooling_unavailable (unchanged semantics).
    - os.environ is not mutated.
    """

    def setUp(self):
        import tempfile as _tempfile
        import stat as _stat
        import shutil as _shutil

        self._tmpdir = _tempfile.mkdtemp()
        self._stat = _stat
        self._shutil = _shutil

    def tearDown(self):
        self._shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _make_fake_binary(self, bin_dir, name):
        """Create a fake executable at <bin_dir>/<name>; return the path."""
        os.makedirs(bin_dir, exist_ok=True)
        path = os.path.join(bin_dir, name)
        with open(path, "w") as fh:
            fh.write("#!/bin/sh\necho ok\n")
        os.chmod(path, self._stat.S_IRWXU)
        return path

    def _write_config_and_run(self, files_list, config, iteration=0):
        """Write config to install root and run cmd_verify_touched."""
        devforge = os.path.join(self._tmpdir, ".devforge")
        os.makedirs(devforge, exist_ok=True)
        config_path = os.path.join(devforge, "project-config.json")
        with open(config_path, "w") as fh:
            json.dump(config, fh)

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            rc = cmd_verify_touched(
                FakeArgs(
                    files=json.dumps(files_list),
                    root=self._tmpdir,
                    iteration=iteration,
                )
            )
        output = stdout_buf.getvalue()
        payload = json.loads(output) if output.strip() else None
        return rc, payload

    def test_binary_in_source_root_node_modules_bin_passes(self):
        """vue-tsc in <source_root>/node_modules/.bin → pass (not tooling_unavailable).

        The binary exists ONLY as a devDependency (in node_modules/.bin),
        NOT on the global PATH.  Before this fix, it would exit as
        tooling_unavailable with rc=127.  After the fix, extra_paths is
        prepended to PATH and the command runs.
        """
        import shutil as _shutil

        # Precondition: ensure vue-tsc is not globally available.
        if _shutil.which("vue-tsc-fake-test-binary"):
            self.skipTest("vue-tsc-fake-test-binary unexpectedly on PATH")

        node_bin = os.path.join(self._tmpdir, "node_modules", ".bin")
        self._make_fake_binary(node_bin, "vue-tsc-fake-test-binary")

        config = {
            "TYPE_CHECK_COMMANDS": ["vue-tsc-fake-test-binary --noEmit"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        original_path = os.environ.get("PATH", "")
        rc, payload = self._write_config_and_run(["src/App.vue"], config)
        # os.environ must be unchanged.
        self.assertEqual(os.environ.get("PATH", ""), original_path,
                         "os.environ PATH must not be mutated")
        self.assertEqual(rc, EXIT_OK,
                         "binary in source_root/node_modules/.bin must resolve; "
                         "payload={0!r}".format(payload))
        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "pass",
                         "expected pass; got {0!r}".format(payload))

    def test_binary_in_package_node_modules_bin_passes(self):
        """Tool in <source_root>/<pkg>/node_modules/.bin → pass.

        Simulates a package-local install (npm workspaces with no hoisting).
        """
        import shutil as _shutil

        if _shutil.which("pkg-local-fake-test-binary"):
            self.skipTest("pkg-local-fake-test-binary unexpectedly on PATH")

        pkg_node_bin = os.path.join(self._tmpdir, "packages", "frontend",
                                    "node_modules", ".bin")
        self._make_fake_binary(pkg_node_bin, "pkg-local-fake-test-binary")

        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [
                {
                    "path": "packages/frontend",
                    "language": "TypeScript",
                    "framework": "Vue",
                    "build_tool": "vite",
                    "build_command": "true",
                    "type_check_command": "pkg-local-fake-test-binary --noEmit",
                    "lint_command": "true",
                },
            ],
        }
        original_path = os.environ.get("PATH", "")
        rc, payload = self._write_config_and_run(["packages/frontend/src/App.vue"], config)
        self.assertEqual(os.environ.get("PATH", ""), original_path,
                         "os.environ PATH must not be mutated")
        self.assertEqual(rc, EXIT_OK,
                         "binary in pkg node_modules/.bin must resolve; "
                         "payload={0!r}".format(payload))
        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "pass",
                         "expected pass; got {0!r}".format(payload))

    def test_genuinely_missing_binary_still_tooling_unavailable(self):
        """A binary absent from PATH AND node_modules → tooling_unavailable (unchanged)."""
        import shutil as _shutil

        if _shutil.which("totally-absent-tool-xyz"):
            self.skipTest("totally-absent-tool-xyz unexpectedly on PATH")

        # No node_modules/.bin created — binary is genuinely missing.
        config = {
            "TYPE_CHECK_COMMANDS": ["totally-absent-tool-xyz --check"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        rc, payload = self._write_config_and_run(["src/App.vue"], config)
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "tooling_unavailable",
                         "truly missing binary must still produce tooling_unavailable")

    def test_os_environ_not_mutated_during_full_verify(self):
        """os.environ PATH is unchanged after a full cmd_verify_touched run."""
        node_bin = os.path.join(self._tmpdir, "node_modules", ".bin")
        self._make_fake_binary(node_bin, "env-check-fake-binary")

        config = {
            "TYPE_CHECK_COMMANDS": ["env-check-fake-binary --noEmit"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [],
        }
        original_path = os.environ.get("PATH", "")
        self._write_config_and_run(["src/App.vue"], config)
        self.assertEqual(os.environ.get("PATH", ""), original_path,
                         "os.environ must not be mutated during cmd_verify_touched")

    def test_divergence_invariant_verify_union_passes_per_package_probe_would_fail(self):
        """Divergence invariant: verify (union) may pass where per-package probe would not.

        Design invariant direction: verify's bin-dir union can resolve a binary
        the per-package probe (resolves()) would return False for — but NEVER
        the reverse.

        Setup:
          packages/a/node_modules/.bin/shared-tool  (real executable)
          packages/b  type_check_command = "shared-tool --check"
                      (NO shared-tool in packages/b/node_modules/.bin)

        Touch files in BOTH packages/a and packages/b so that cmd_verify_touched
        unions their bin dirs.  The union includes packages/a/node_modules/.bin,
        so the command "shared-tool --check" (assigned to package B) can be
        found and runs successfully → status == "pass", NOT tooling_unavailable.

        The companion test in TestResolvesFunction
        (test_divergence_invariant_per_package_cannot_see_sibling_bin)
        confirms that resolves("shared-tool", root, "packages/b") == False,
        pinning the invariant direction.
        """
        import shutil as _shutil

        # Precondition: ensure shared-tool-divergence-fake is not on global PATH.
        if _shutil.which("shared-tool-divergence-fake"):
            self.skipTest("shared-tool-divergence-fake unexpectedly on global PATH")

        # Create shared-tool in package A's bin dir.
        bin_dir_a = os.path.join(self._tmpdir, "packages", "a", "node_modules", ".bin")
        self._make_fake_binary(bin_dir_a, "shared-tool-divergence-fake")

        # Package B has the command but no local node_modules/.bin.
        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "PACKAGE_STACKS": [
                {
                    "path": "packages/a",
                    "language": "TypeScript",
                    "framework": None,
                    "build_tool": None,
                    "build_command": "true",
                    "type_check_command": "true",
                    "lint_command": "true",
                },
                {
                    "path": "packages/b",
                    "language": "TypeScript",
                    "framework": None,
                    "build_tool": None,
                    "build_command": "true",
                    # B owns this command but has no local node_modules/.bin.
                    "type_check_command": "shared-tool-divergence-fake --check",
                    "lint_command": "true",
                },
            ],
        }
        # Touch files in BOTH packages so the union includes A's bin dir.
        rc, payload = self._write_config_and_run(
            ["packages/a/index.ts", "packages/b/index.ts"], config
        )
        self.assertEqual(
            rc, EXIT_OK,
            "verify's union of A+B bin dirs must find shared-tool-divergence-fake; "
            "payload={0!r}".format(payload),
        )
        self.assertIsNotNone(payload)
        self.assertEqual(
            payload["status"], "pass",
            "expected pass (union resolves the binary); got {0!r}".format(payload),
        )


# ---------------------------------------------------------------------------
# Phase 2: test command collection + execution tests
# ---------------------------------------------------------------------------


class TestCollectCommandsTestSlot(unittest.TestCase):
    """Unit tests for the test_command slot in _collect_commands (Phase 2)."""

    def _pkg(self, path, tc="tc-cmd", lint="lint-cmd", test=None):
        return {
            "path": path,
            "type_check_command": tc,
            "lint_command": lint,
            "test_command": test,
        }

    def test_per_package_test_command_returned(self):
        """File in package with test_command → that test_command in result."""
        stacks = [self._pkg("src", test="pytest src/")]
        _, _, test_cmds = _collect_commands(
            ["src/foo.py"], stacks, "primary-tc", "primary-lint", "primary-test"
        )
        self.assertEqual(test_cmds, ["pytest src/"])

    def test_primary_test_fallback_for_unmatched_file(self):
        """File outside any package → primary_test fallback used."""
        stacks = [self._pkg("src", test="pytest src/")]
        _, _, test_cmds = _collect_commands(
            ["top_level.py"], stacks, None, None, "primary-test-fallback"
        )
        self.assertEqual(test_cmds, ["primary-test-fallback"])

    def test_na_test_command_excluded(self):
        """test_command == 'N/A' → silently excluded, empty list."""
        stacks = [self._pkg("src", test="N/A")]
        _, _, test_cmds = _collect_commands(["src/foo.py"], stacks, None, None, None)
        self.assertEqual(test_cmds, [])

    def test_none_test_command_excluded(self):
        """test_command == None → silently excluded."""
        stacks = [self._pkg("src", test=None)]
        _, _, test_cmds = _collect_commands(["src/foo.py"], stacks, None, None, None)
        self.assertEqual(test_cmds, [])

    def test_duplicate_test_command_deduped(self):
        """Two files in the same package → test_command appears once."""
        stacks = [self._pkg("src", test="pytest src/")]
        _, _, test_cmds = _collect_commands(
            ["src/a.py", "src/b.py"], stacks, None, None, "primary-test"
        )
        self.assertEqual(test_cmds, ["pytest src/"])

    def test_two_packages_distinct_test_commands_both_collected(self):
        """Two packages with different test commands → both collected (de-duped each)."""
        stacks = [
            self._pkg("services/api", test="pytest services/api/"),
            self._pkg("frontend", test="npm test --prefix frontend"),
        ]
        _, _, test_cmds = _collect_commands(
            ["services/api/main.py", "frontend/src/App.tsx"],
            stacks,
            None,
            None,
            "primary-test",
        )
        self.assertIn("pytest services/api/", test_cmds)
        self.assertIn("npm test --prefix frontend", test_cmds)
        # Primary fallback not included — all files matched packages.
        self.assertNotIn("primary-test", test_cmds)

    def test_no_primary_test_no_package_test_empty_list(self):
        """No primary_test and no per-package test_command → empty list."""
        stacks = [self._pkg("src", test=None)]
        _, _, test_cmds = _collect_commands(
            ["top_level.py"], stacks, None, None, None
        )
        self.assertEqual(test_cmds, [])

    def test_empty_touched_files_empty_test_cmds(self):
        """No touched files → no test commands collected."""
        stacks = [self._pkg("src", test="pytest src/")]
        _, _, test_cmds = _collect_commands([], stacks, None, None, "primary-test")
        self.assertEqual(test_cmds, [])

    def test_returns_three_tuple(self):
        """_collect_commands now returns a 3-tuple (tc, lint, test)."""
        stacks = [self._pkg("src", test="pytest")]
        result = _collect_commands(["src/x.py"], stacks, None, None, None)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)


class TestCmdVerifyTouchedTestCommands(unittest.TestCase):
    """Integration tests for test command execution via cmd_verify_touched (Phase 2).

    All tests use the _run_with_mock / mock-patching pattern from the existing
    tooling-unavailable integration tests so no real test runner is needed.
    Config dicts set test_command per-package and/or TEST_COMMANDS at top level.
    """

    def _run_with_mock(self, files_list, config, mock_run_fn, iteration=0):
        """Write config, patch _run_command, run cmd_verify_touched, return (rc, payload)."""
        import _implement._cmds_verify as verify_mod

        tmpdir = tempfile.mkdtemp()
        _write_config(tmpdir, config)

        original = verify_mod._run_command
        verify_mod._run_command = mock_run_fn

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        try:
            with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
                rc = cmd_verify_touched(
                    FakeArgs(
                        files=json.dumps(files_list),
                        root=tmpdir,
                        iteration=iteration,
                    )
                )
        finally:
            verify_mod._run_command = original

        output = stdout_buf.getvalue()
        payload = json.loads(output) if output.strip() else None
        return rc, payload

    def _pass_config_with_test(self, test_command="npm test"):
        """Config with a per-package test_command and all other commands as 'true'."""
        return {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            # TEST_COMMANDS is intentionally empty so this helper exercises ONLY the
            # per-package test_command path, not the primary-fallback path (which is
            # covered by test_primary_test_command_fallback_for_non_package_file).
            "TEST_COMMANDS": [],
            "PACKAGE_STACKS": [
                {
                    "path": "services/api",
                    "language": "Python",
                    "framework": "FastAPI",
                    "build_tool": None,
                    "build_command": "true",
                    "type_check_command": "true",
                    "lint_command": "true",
                    "test_command": test_command,
                },
            ],
        }

    # --- pass payload includes test_commands_run ---

    def test_pass_payload_includes_test_commands_run(self):
        """Pass payload must include test_commands_run key."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 0, ""

        config = self._pass_config_with_test("npm test")
        rc, payload = self._run_with_mock(["services/api/main.py"], config, mock_run)

        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "pass")
        self.assertIn("test_commands_run", payload)
        self.assertIsInstance(payload["test_commands_run"], list)

    def test_per_package_test_command_in_test_commands_run(self):
        """Per-package test_command appears in test_commands_run."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 0, ""

        config = self._pass_config_with_test("pytest services/api/")
        rc, payload = self._run_with_mock(["services/api/main.py"], config, mock_run)

        self.assertEqual(payload["status"], "pass")
        self.assertIn("pytest services/api/", payload["test_commands_run"])

    def test_primary_test_command_fallback_for_non_package_file(self):
        """File outside any package → TEST_COMMANDS[0] fallback appears in test_commands_run."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 0, ""

        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "TEST_COMMANDS": ["pytest ."],
            "PACKAGE_STACKS": [
                {
                    "path": "services/api",
                    "type_check_command": "true",
                    "lint_command": "true",
                    "build_command": "true",
                    "test_command": "pytest services/api/",
                },
            ],
        }
        # top_level.py is outside 'services/api' → falls back to TEST_COMMANDS[0].
        rc, payload = self._run_with_mock(["top_level.py"], config, mock_run)

        self.assertEqual(payload["status"], "pass")
        self.assertIn("pytest .", payload["test_commands_run"])
        # Per-package test must NOT appear — the file didn't match the package.
        self.assertNotIn("pytest services/api/", payload["test_commands_run"])

    # --- N/A test_command skipped ---

    def test_na_test_command_skipped_pass_with_empty_test_commands_run(self):
        """'N/A' test_command → skipped; test_commands_run is empty."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 0, ""

        config = self._pass_config_with_test("N/A")
        rc, payload = self._run_with_mock(["services/api/main.py"], config, mock_run)

        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["test_commands_run"], [])

    # --- Duplicate test_command de-duped ---

    def test_duplicate_test_command_across_two_files_deduped(self):
        """Two files in the same package → test_command runs once (de-duped)."""
        commands_called = []

        def mock_run(cmd, cwd, extra_paths=None):
            commands_called.append(cmd)
            return 0, ""

        import _implement._cmds_verify as verify_mod
        original = verify_mod._run_command
        verify_mod._run_command = mock_run

        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "TEST_COMMANDS": [],
            "PACKAGE_STACKS": [
                {
                    "path": "services/api",
                    "type_check_command": "true",
                    "lint_command": "true",
                    "build_command": "true",
                    "test_command": "pytest services/api/",
                },
            ],
        }
        tmpdir = tempfile.mkdtemp()
        _write_config(tmpdir, config)

        try:
            stdout_buf = io.StringIO()
            with patch("sys.stdout", stdout_buf):
                cmd_verify_touched(
                    FakeArgs(
                        files=json.dumps(
                            ["services/api/a.py", "services/api/b.py"]
                        ),
                        root=tmpdir,
                        iteration=0,
                    )
                )
        finally:
            verify_mod._run_command = original

        from collections import Counter
        counts = Counter(commands_called)
        self.assertEqual(
            counts.get("pytest services/api/", 0), 1,
            "test_command must run exactly once (de-duped across two files in same package)",
        )

    # --- Failing test command → self_repair / failed ---

    def test_failing_test_command_at_iteration_0_self_repair(self):
        """Failing test_command at iteration=0 → self_repair, exit 0."""
        def mock_run(cmd, cwd, extra_paths=None):
            if cmd == "pytest services/api/":
                return 1, "FAILED test_widget.py::test_add - AssertionError\n"
            return 0, ""

        config = self._pass_config_with_test("pytest services/api/")
        rc, payload = self._run_with_mock(
            ["services/api/main.py"], config, mock_run, iteration=0
        )

        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "self_repair")
        self.assertEqual(payload["iteration"], 0)
        self.assertIn("failed_command", payload)
        self.assertIn("output", payload)

    def test_failing_test_command_at_cap_produces_failed(self):
        """Failing test_command at iteration=SELF_REPAIR_CAP → failed, exit 2."""
        def mock_run(cmd, cwd, extra_paths=None):
            if cmd == "pytest services/api/":
                return 1, "FAILED test_widget.py::test_add - AssertionError\n"
            return 0, ""

        config = self._pass_config_with_test("pytest services/api/")
        rc, payload = self._run_with_mock(
            ["services/api/main.py"], config, mock_run, iteration=SELF_REPAIR_CAP
        )

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["failed_command"], "pytest services/api/")

    # --- Missing test runner → tooling_unavailable ---

    def test_missing_test_runner_rc127_tooling_unavailable(self):
        """test_command that returns rc=127 → tooling_unavailable, exit 2."""
        def mock_run(cmd, cwd, extra_paths=None):
            if cmd == "missing-test-runner":
                return 127, "sh: missing-test-runner: command not found\n"
            return 0, ""

        config = self._pass_config_with_test("missing-test-runner")
        rc, payload = self._run_with_mock(
            ["services/api/main.py"], config, mock_run, iteration=0
        )

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertEqual(payload["status"], "tooling_unavailable")
        self.assertEqual(payload["failed_command"], "missing-test-runner")

    # --- Build failure short-circuits before test runs ---

    def test_failing_build_short_circuits_before_test(self):
        """A failing build_command must prevent test_command from running at all.

        Run order is: tc → lint → build → test.
        If build fails, test must never be called.
        """
        commands_called = []

        def mock_run(cmd, cwd, extra_paths=None):
            commands_called.append(cmd)
            if cmd == "build-fail":
                return 1, "Build error: missing module\n"
            return 0, ""

        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["build-fail"],
            "TEST_COMMANDS": [],
            "PACKAGE_STACKS": [
                {
                    "path": "services/api",
                    "type_check_command": "true",
                    "lint_command": "true",
                    "build_command": "build-fail",
                    "test_command": "should-not-run",
                },
            ],
        }
        import _implement._cmds_verify as verify_mod
        original = verify_mod._run_command
        verify_mod._run_command = mock_run

        tmpdir = tempfile.mkdtemp()
        _write_config(tmpdir, config)

        try:
            stdout_buf = io.StringIO()
            with patch("sys.stdout", stdout_buf):
                cmd_verify_touched(
                    FakeArgs(
                        files=json.dumps(["services/api/main.py"]),
                        root=tmpdir,
                        iteration=0,
                    )
                )
        finally:
            verify_mod._run_command = original

        self.assertNotIn(
            "should-not-run", commands_called,
            "test_command must NOT run when build fails (fail-fast ordering)",
        )
        # Build failure at iteration=0, exit code 1 → self_repair (not failed/tooling_unavailable).
        output = stdout_buf.getvalue()
        payload = json.loads(output) if output.strip() else None
        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "self_repair")

    # --- No test config anywhere → backward-compatible no-op ---

    def test_no_test_config_backward_compatible(self):
        """Project with no TEST_COMMANDS and no per-package test_command → pass with empty list.

        This is the backward-compatibility case: projects without test config
        must behave exactly as before Phase 2 (no test runs, no failure).
        """
        def mock_run(cmd, cwd, extra_paths=None):
            return 0, ""

        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            # No TEST_COMMANDS key at all.
            "PACKAGE_STACKS": [
                {
                    "path": "services/api",
                    "type_check_command": "true",
                    "lint_command": "true",
                    "build_command": "true",
                    # No test_command key at all.
                },
            ],
        }
        rc, payload = self._run_with_mock(["services/api/main.py"], config, mock_run)

        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["test_commands_run"], [])

    def test_empty_test_commands_array_backward_compatible(self):
        """Empty TEST_COMMANDS array + no per-package test_command → no test runs, pass."""
        def mock_run(cmd, cwd, extra_paths=None):
            return 0, ""

        config = {
            "TYPE_CHECK_COMMANDS": ["true"],
            "LINT_COMMANDS": ["true"],
            "BUILD_COMMANDS": ["true"],
            "TEST_COMMANDS": [],
            "PACKAGE_STACKS": [
                {
                    "path": "services/api",
                    "type_check_command": "true",
                    "lint_command": "true",
                    "build_command": "true",
                    "test_command": None,
                },
            ],
        }
        rc, payload = self._run_with_mock(["services/api/main.py"], config, mock_run)

        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["test_commands_run"], [])

    # --- Test runs AFTER build (ordering probe) ---

    def test_test_command_runs_after_build_in_all_pass_case(self):
        """Confirm test_command is called AFTER build_command in the all-pass case."""
        call_order = []

        def mock_run(cmd, cwd, extra_paths=None):
            call_order.append(cmd)
            return 0, ""

        config = {
            "TYPE_CHECK_COMMANDS": ["tc-cmd"],
            "LINT_COMMANDS": ["lint-cmd"],
            "BUILD_COMMANDS": ["build-cmd"],
            "TEST_COMMANDS": ["test-cmd"],
            "PACKAGE_STACKS": [],  # All files use primary fallbacks.
        }

        import _implement._cmds_verify as verify_mod
        original = verify_mod._run_command
        verify_mod._run_command = mock_run

        tmpdir = tempfile.mkdtemp()
        _write_config(tmpdir, config)

        try:
            stdout_buf = io.StringIO()
            with patch("sys.stdout", stdout_buf):
                cmd_verify_touched(
                    FakeArgs(
                        files=json.dumps(["top_level.py"]),
                        root=tmpdir,
                        iteration=0,
                    )
                )
        finally:
            verify_mod._run_command = original

        # Verify ordering: build before test.
        self.assertIn("build-cmd", call_order)
        self.assertIn("test-cmd", call_order)
        build_idx = call_order.index("build-cmd")
        test_idx = call_order.index("test-cmd")
        self.assertLess(
            build_idx, test_idx,
            "build_command must run before test_command; "
            "call_order={0!r}".format(call_order),
        )


if __name__ == "__main__":
    unittest.main()
