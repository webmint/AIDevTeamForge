"""Tests for src/devforge/lib/detect_report.py.

Covers the closed-shape yaml emitter+parser, all 14 subcommands, set-time
validation, atomic writes, and the find-nested-git read-only scan.

Each test runs in its own `tempfile.TemporaryDirectory` and points the
helper at it via the `DEVFORGE_DIR` environment variable, so the repo's
real `.devforge/` is never touched. The env override is restored in
tearDown so tests can't bleed into each other.

Pure-function tests (`emit_yaml`, `parse_yaml`, `_output_file_path`) import
the module directly. End-to-end CLI tests invoke the .py file as a
subprocess, exercising the real argparse + dispatch path.

Stdlib only.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Resolve the helper script + add lib dir to sys.path so we can import the
# module for pure-function tests.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "detect_report.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import detect_report  # noqa: E402


def _run_cli(devforge_dir, *args):
    """Invoke `detect_report.py <args>` as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class _EnvIsolationMixin:
    """Save/restore DEVFORGE_DIR around each test + provide a tmpdir."""

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name)
        self.output_file = self.devforge_dir / detect_report.OUTPUT_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env


# ---------------------------------------------------------------------------
# OutputFilePathTests
# ---------------------------------------------------------------------------


class OutputFilePathTests(unittest.TestCase):
    """`_output_file_path` resolution rules."""

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
            path = detect_report._output_file_path()
            self.assertEqual(path, Path(tmp) / detect_report.OUTPUT_FILE_NAME)

    def test_no_env_falls_back_to_helper_location(self):
        path = detect_report._output_file_path()
        expected_dir = Path(detect_report.__file__).resolve().parent.parent
        self.assertEqual(path, expected_dir / detect_report.OUTPUT_FILE_NAME)

    def test_resolution_is_per_call_not_cached(self):
        # Setting the env var after import must be honored — proves the path
        # isn't computed at import time.
        with tempfile.TemporaryDirectory() as tmp_a:
            os.environ["DEVFORGE_DIR"] = tmp_a
            first = detect_report._output_file_path()
        with tempfile.TemporaryDirectory() as tmp_b:
            os.environ["DEVFORGE_DIR"] = tmp_b
            second = detect_report._output_file_path()
        self.assertNotEqual(first, second)


# ---------------------------------------------------------------------------
# ResetTests
# ---------------------------------------------------------------------------


class ResetTests(_EnvIsolationMixin, unittest.TestCase):

    def test_reset_creates_file(self):
        self.assertFalse(self.output_file.exists())
        proc = _run_cli(self.devforge_dir, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.output_file.exists())

    def test_reset_contents_are_defaults(self):
        proc = _run_cli(self.devforge_dir, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = self.output_file.read_text(encoding="utf-8")
        state = detect_report.parse_yaml(text)
        self.assertEqual(state, detect_report.default_state())

    def test_reset_is_idempotent_byte_identical(self):
        _run_cli(self.devforge_dir, "reset")
        first = self.output_file.read_bytes()
        _run_cli(self.devforge_dir, "reset")
        second = self.output_file.read_bytes()
        self.assertEqual(first, second)

    def test_reset_overwrites_populated_state(self):
        # Populate state, then reset, then confirm defaults.
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-project-root", "myproject")
        _run_cli(
            self.devforge_dir, "add-package", "--path", ".", "--manifest", "package.json"
        )
        proc = _run_cli(self.devforge_dir, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = detect_report.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state, detect_report.default_state())

    def test_no_subcommand_returns_2(self):
        # main() has an explicit no-subcommand branch that prints help to
        # stderr and returns exit code 2.
        proc = _run_cli(self.devforge_dir)
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# ScalarSetterTests
# ---------------------------------------------------------------------------


class ScalarSetterTests(_EnvIsolationMixin, unittest.TestCase):

    def _read_state(self):
        return detect_report.parse_yaml(self.output_file.read_text(encoding="utf-8"))

    def test_set_project_root_happy(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", "client-app")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["project_root"], "client-app")

    def test_set_workspace_mode_happy_standalone(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-workspace-mode", "standalone")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["workspace_mode"], "standalone")

    def test_set_workspace_mode_happy_wrapper(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-workspace-mode", "wrapper")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["workspace_mode"], "wrapper")

    def test_set_workspace_mode_enum_violation(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-workspace-mode", "monorepo")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"workspace_mode", proc.stderr)
        # State on disk is unchanged (still default None).
        self.assertIsNone(self._read_state()["workspace_mode"])

    def test_set_project_state_happy(self):
        _run_cli(self.devforge_dir, "reset")
        for value in ("empty", "brownfield"):
            proc = _run_cli(self.devforge_dir, "set-project-state", value)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(self._read_state()["project_state"], value)

    def test_set_project_state_enum_violation(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-state", "legacy")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"project_state", proc.stderr)

    def test_set_project_state_rejects_greenfield(self):
        # Pins the enum tightening: greenfield was previously allowed and is
        # now removed. set-project-state must fail with a non-zero exit and a
        # stderr message naming the field, so a future regression that
        # re-adds "greenfield" to ENUM_FIELDS is caught.
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-state", "greenfield")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"project_state", proc.stderr)
        # State on disk is unchanged (still default None).
        self.assertIsNone(self._read_state()["project_state"])

    def test_set_default_branch_happy(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-default-branch", "main")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["default_branch"], "main")

    def test_set_primary_language_happy(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-primary-language", "TypeScript")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["primary_language"], "TypeScript")

    def test_control_char_rejected_newline(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir, "set-project-root", "value\nwith\nnewline"
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"control characters", proc.stderr)
        self.assertIsNone(self._read_state()["project_root"])

    def test_control_char_rejected_tab(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir, "set-default-branch", "main\twith\ttab"
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"control characters", proc.stderr)

    def test_whitespace_only_rejected(self):
        # Three spaces — neither empty nor control chars, but still meaningless
        # as a project root. _validate_string should reject via .strip() check.
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", "   ")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"non-empty", proc.stderr)
        self.assertIsNone(self._read_state()["project_root"])

    def test_set_scalar_without_prior_reset(self):
        # No reset called — file does not exist yet, exercises the
        # `_load_state` "file absent → defaults" branch.
        self.assertFalse(self.output_file.exists())
        proc = _run_cli(self.devforge_dir, "set-project-root", "myproject")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.output_file.exists())
        state = detect_report.parse_yaml(
            self.output_file.read_text(encoding="utf-8")
        )
        self.assertEqual(state["project_root"], "myproject")


# ---------------------------------------------------------------------------
# AddPackageTests
# ---------------------------------------------------------------------------


class AddPackageTests(_EnvIsolationMixin, unittest.TestCase):

    def _read_state(self):
        return detect_report.parse_yaml(self.output_file.read_text(encoding="utf-8"))

    def test_add_package_happy(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", ".",
            "--manifest", "package.json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages_detected"],
            [{"path": ".", "manifest": "package.json"}],
        )

    def test_add_package_duplicate_path_errors(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "client",
            "--manifest", "package.json",
        )
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "client",
            "--manifest", "package.json",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"already present", proc.stderr)
        # Only one record.
        self.assertEqual(len(self._read_state()["packages_detected"]), 1)

    def test_add_package_missing_required_arg_errors(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "add-package", "--path", ".")
        self.assertNotEqual(proc.returncode, 0)
        # argparse writes the usage + error to stderr.
        self.assertIn(b"manifest", proc.stderr)

    def test_add_package_trailing_slash_duplicate_rejected(self):
        # `client/` and `client` should be treated as the same path.
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "client/",
            "--manifest", "package.json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "client",
            "--manifest", "package.json",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"already present", proc.stderr)
        # Stored path is the normalized form (no trailing slash).
        self.assertEqual(
            self._read_state()["packages_detected"],
            [{"path": "client", "manifest": "package.json"}],
        )


# ---------------------------------------------------------------------------
# PerPackageArraySetterTests
# ---------------------------------------------------------------------------


class PerPackageArraySetterTests(_EnvIsolationMixin, unittest.TestCase):

    def _read_state(self):
        return detect_report.parse_yaml(self.output_file.read_text(encoding="utf-8"))

    def _bootstrap_packages(self, *paths):
        _run_cli(self.devforge_dir, "reset")
        for p in paths:
            _run_cli(
                self.devforge_dir,
                "add-package",
                "--path", p,
                "--manifest", "package.json",
            )

    def test_add_language_happy_appends(self):
        self._bootstrap_packages("client", "server")
        proc = _run_cli(
            self.devforge_dir,
            "add-language",
            "--path", "client",
            "--value", "TypeScript",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_cli(
            self.devforge_dir,
            "add-language",
            "--path", "server",
            "--value", "Python",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["languages"],
            [
                {"path": "client", "value": "TypeScript"},
                {"path": "server", "value": "Python"},
            ],
        )

    def test_add_language_upsert_no_duplicate(self):
        self._bootstrap_packages("client")
        _run_cli(
            self.devforge_dir,
            "add-language",
            "--path", "client",
            "--value", "JavaScript",
        )
        proc = _run_cli(
            self.devforge_dir,
            "add-language",
            "--path", "client",
            "--value", "TypeScript",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["languages"],
            [{"path": "client", "value": "TypeScript"}],
        )

    def test_add_framework_foreign_key_violation(self):
        self._bootstrap_packages("client")
        proc = _run_cli(
            self.devforge_dir,
            "add-framework",
            "--path", "server",  # not in packages_detected
            "--value", "Django",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"not found in packages_detected", proc.stderr)
        self.assertEqual(self._read_state()["frameworks"], [])

    def test_add_framework_null_flag_stores_none(self):
        self._bootstrap_packages("client")
        proc = _run_cli(
            self.devforge_dir,
            "add-framework",
            "--path", "client",
            "--null",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["frameworks"],
            [{"path": "client", "value": None}],
        )

    def test_add_type_check_command_value_na_stores_literal(self):
        self._bootstrap_packages("client")
        proc = _run_cli(
            self.devforge_dir,
            "add-type-check-command",
            "--path", "client",
            "--value", "N/A",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["type_check_commands"],
            [{"path": "client", "value": "N/A"}],
        )

    def test_add_framework_value_na_stores_literal(self):
        # Genuine add-framework path: literal "N/A" round-trips through the
        # frameworks field (where --null is the typical "no framework" path,
        # but a literal "N/A" string is also a valid value).
        self._bootstrap_packages("client")
        proc = _run_cli(
            self.devforge_dir,
            "add-framework",
            "--path", "client",
            "--value", "N/A",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["frameworks"],
            [{"path": "client", "value": "N/A"}],
        )

    def test_add_language_trailing_slash_path_normalized(self):
        # add-package with bare `client`, then add-language with `client/`
        # should succeed (FK passes) and store the normalized form.
        self._bootstrap_packages("client")
        proc = _run_cli(
            self.devforge_dir,
            "add-language",
            "--path", "client/",
            "--value", "Python",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["languages"],
            [{"path": "client", "value": "Python"}],
        )

    def test_add_framework_value_and_null_mutually_exclusive(self):
        self._bootstrap_packages("client")
        proc = _run_cli(
            self.devforge_dir,
            "add-framework",
            "--path", "client",
            "--value", "Django",
            "--null",
        )
        self.assertNotEqual(proc.returncode, 0)
        # argparse mutual-exclusion error mentions one of the args.
        self.assertTrue(
            b"--null" in proc.stderr or b"--value" in proc.stderr,
            proc.stderr,
        )


# ---------------------------------------------------------------------------
# FindNestedGitTests
# ---------------------------------------------------------------------------


class FindNestedGitTests(_EnvIsolationMixin, unittest.TestCase):
    """find-nested-git scans the install root (parent of devforge_dir).

    For these tests we treat `devforge_dir` as the `.devforge/` directory and
    its parent as the install root. So `self.devforge_dir.parent` is where we
    plant the test fixture directories.
    """

    def setUp(self):
        super().setUp()
        # Create a stable install-root tmpdir + a .devforge dir under it.
        # We replace devforge_dir to point at .devforge inside the install root.
        self._install_root_tmp = tempfile.TemporaryDirectory()
        self.install_root = Path(self._install_root_tmp.name)
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir()
        self.output_file = self.devforge_dir / detect_report.OUTPUT_FILE_NAME

    def tearDown(self):
        self._install_root_tmp.cleanup()
        super().tearDown()

    def test_empty_install_root_prints_nothing(self):
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"")

    def test_one_nested_git_prints_one_path(self):
        nested = self.install_root / "client-app"
        (nested / ".git").mkdir(parents=True)
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"client-app\n")

    def test_multiple_nested_gits_printed(self):
        for name in ("client", "server", "shared"):
            (self.install_root / name / ".git").mkdir(parents=True)
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Sorted output (lex order).
        self.assertEqual(proc.stdout, b"client\nserver\nshared\n")

    def test_skip_list_dirs_ignored(self):
        # A `.git/` inside node_modules / dist / hidden-dir is skipped.
        (self.install_root / "node_modules" / ".git").mkdir(parents=True)
        (self.install_root / "dist" / ".git").mkdir(parents=True)
        (self.install_root / ".hidden" / ".git").mkdir(parents=True)
        # And one legitimate nested repo.
        (self.install_root / "real-pkg" / ".git").mkdir(parents=True)
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"real-pkg\n")


# ---------------------------------------------------------------------------
# YamlRoundTripTests
# ---------------------------------------------------------------------------


class YamlRoundTripTests(unittest.TestCase):
    """emit_yaml(parse_yaml(emit_yaml(state))) == emit_yaml(state)."""

    def test_defaults_round_trip(self):
        state = detect_report.default_state()
        text = detect_report.emit_yaml(state)
        parsed = detect_report.parse_yaml(text)
        self.assertEqual(parsed, state)
        # And byte-identical second emit.
        self.assertEqual(detect_report.emit_yaml(parsed), text)

    def test_populated_state_round_trips(self):
        state = detect_report.default_state()
        state["project_root"] = "client-app"
        state["workspace_mode"] = "wrapper"
        state["project_state"] = "brownfield"
        state["default_branch"] = "main"
        state["primary_language"] = "TypeScript"
        state["packages_detected"] = [
            {"path": ".", "manifest": "package.json"},
            {"path": "server", "manifest": "pyproject.toml"},
        ]
        state["languages"] = [
            {"path": ".", "value": "TypeScript"},
            {"path": "server", "value": "Python"},
        ]
        state["frameworks"] = [
            {"path": ".", "value": "React"},
            {"path": "server", "value": "FastAPI"},
        ]
        state["build_tools"] = [
            {"path": ".", "value": "Vite"},
            {"path": "server", "value": "Poetry"},
        ]
        state["build_commands"] = [
            {"path": ".", "value": "npm run build"},
            {"path": "server", "value": "poetry build"},
        ]
        state["type_check_commands"] = [
            {"path": ".", "value": "tsc --noEmit"},
            {"path": "server", "value": "mypy ."},
        ]
        state["lint_commands"] = [
            {"path": ".", "value": "eslint ."},
            {"path": "server", "value": "ruff check ."},
        ]
        text = detect_report.emit_yaml(state)
        parsed = detect_report.parse_yaml(text)
        self.assertEqual(parsed, state)

    def test_sentinel_round_trip(self):
        # `None` and `"N/A"` literal must both survive.
        state = detect_report.default_state()
        state["packages_detected"] = [{"path": "rust-crate", "manifest": "Cargo.toml"}]
        state["frameworks"] = [{"path": "rust-crate", "value": None}]
        state["type_check_commands"] = [{"path": "rust-crate", "value": "N/A"}]
        text = detect_report.emit_yaml(state)
        parsed = detect_report.parse_yaml(text)
        self.assertEqual(parsed["frameworks"], [{"path": "rust-crate", "value": None}])
        self.assertEqual(
            parsed["type_check_commands"],
            [{"path": "rust-crate", "value": "N/A"}],
        )
        # Verify on-the-wire form: None → bare null; "N/A" → quoted (contains /).
        self.assertIn("value: null", text)
        self.assertIn("value: \"N/A\"", text)


# ---------------------------------------------------------------------------
# AtomicWriteTests
# ---------------------------------------------------------------------------


class AtomicWriteTests(_EnvIsolationMixin, unittest.TestCase):
    """Verify temp file is cleaned up on write failure; original yaml untouched."""

    def test_replace_failure_cleans_temp_and_preserves_original(self):
        # Set DEVFORGE_DIR via env so the in-process call resolves to our tmpdir.
        os.environ["DEVFORGE_DIR"] = str(self.devforge_dir)

        # Seed a known-good file.
        seed_state = detect_report.default_state()
        seed_state["project_root"] = "seed"
        detect_report._write_state(seed_state)
        original_bytes = self.output_file.read_bytes()

        # Monkey-patch os.replace to raise.
        import detect_report as dr
        real_replace = os.replace

        def boom(src, dst):
            raise OSError("simulated replace failure")

        dr.os.replace = boom
        try:
            with self.assertRaises(OSError):
                dr._write_state({**seed_state, "project_root": "new-value"})
        finally:
            dr.os.replace = real_replace

        # Original file untouched.
        self.assertEqual(self.output_file.read_bytes(), original_bytes)
        # No leftover .yaml.tmp files in the directory.
        leftovers = [
            p for p in self.devforge_dir.iterdir() if p.name.endswith(".yaml.tmp")
        ]
        self.assertEqual(leftovers, [])


# ---------------------------------------------------------------------------
# PathValidationTests
# ---------------------------------------------------------------------------


class PathValidationTests(_EnvIsolationMixin, unittest.TestCase):
    """`_validate_path` rejects absolute / parent-traversal paths at every CLI
    surface that takes a `--path` (add-package, add-language and the other
    value/path arrays via `_add_value_path`) plus the `set-project-root`
    positional value, since `project_root` is itself a path.
    """

    def _read_state(self):
        return detect_report.parse_yaml(self.output_file.read_text(encoding="utf-8"))

    # -- add-package --------------------------------------------------------

    def test_add_package_rejects_absolute_posix_path(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "/Users/foo",
            "--manifest", "pkg.json",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"packages_detected.path", proc.stderr)
        self.assertIn(b"/Users/foo", proc.stderr)
        # State unchanged.
        self.assertEqual(self._read_state()["packages_detected"], [])

    def test_add_package_rejects_parent_dir_only(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "..",
            "--manifest", "pkg.json",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"packages_detected.path", proc.stderr)
        self.assertIn(b"'..'", proc.stderr)
        self.assertEqual(self._read_state()["packages_detected"], [])

    def test_add_package_rejects_parent_dir_segment(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "foo/../bar",
            "--manifest", "pkg.json",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"packages_detected.path", proc.stderr)
        self.assertIn(b"foo/../bar", proc.stderr)
        self.assertEqual(self._read_state()["packages_detected"], [])

    def test_add_package_rejects_windows_drive_path(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "C:\\foo",
            "--manifest", "pkg.json",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"packages_detected.path", proc.stderr)
        self.assertIn(b"C:", proc.stderr)
        self.assertEqual(self._read_state()["packages_detected"], [])

    def test_add_package_rejects_windows_drive_path_lowercase_forward_slash(self):
        # A `c:/foo` form (lowercase drive, forward slash) must also be caught.
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "c:/foo",
            "--manifest", "pkg.json",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"packages_detected.path", proc.stderr)
        self.assertEqual(self._read_state()["packages_detected"], [])

    def test_add_package_rejects_backslash_parent_segment(self):
        # Mixed-style traversal `foo\..\bar` must be caught the same as
        # `foo/../bar` since the split recognizes both separators.
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "foo\\..\\bar",
            "--manifest", "pkg.json",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"packages_detected.path", proc.stderr)
        self.assertEqual(self._read_state()["packages_detected"], [])

    def test_add_package_accepts_dot(self):
        # Sentinel `.` is the project-root reference; must remain valid.
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", ".",
            "--manifest", "package.json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages_detected"],
            [{"path": ".", "manifest": "package.json"}],
        )

    def test_add_package_accepts_relative_nested(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "apps/web",
            "--manifest", "package.json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages_detected"],
            [{"path": "apps/web", "manifest": "package.json"}],
        )

    def test_add_package_accepts_deeper_relative(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "services/api/users",
            "--manifest", "package.json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages_detected"],
            [{"path": "services/api/users", "manifest": "package.json"}],
        )

    # -- _add_value_path (via add-language) ---------------------------------

    def test_add_language_rejects_absolute_path(self):
        # Pre-load a valid package so the FK check isn't what fails first.
        _run_cli(self.devforge_dir, "reset")
        _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "client",
            "--manifest", "package.json",
        )
        proc = _run_cli(
            self.devforge_dir,
            "add-language",
            "--path", "/Users/foo",
            "--value", "Python",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"languages.path", proc.stderr)
        self.assertIn(b"/Users/foo", proc.stderr)
        self.assertEqual(self._read_state()["languages"], [])

    def test_add_language_rejects_parent_segment(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "client",
            "--manifest", "package.json",
        )
        proc = _run_cli(
            self.devforge_dir,
            "add-language",
            "--path", "client/../etc",
            "--value", "Python",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"languages.path", proc.stderr)
        self.assertEqual(self._read_state()["languages"], [])

    # -- set-project-root ---------------------------------------------------

    def test_set_project_root_rejects_absolute_posix_path(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir, "set-project-root", "/Users/foo"
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"project_root", proc.stderr)
        self.assertIn(b"/Users/foo", proc.stderr)
        # State on disk is unchanged.
        self.assertIsNone(self._read_state()["project_root"])

    def test_set_project_root_rejects_parent_dir(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", "..")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"project_root", proc.stderr)
        self.assertIn(b"'..'", proc.stderr)
        self.assertIsNone(self._read_state()["project_root"])

    def test_set_project_root_rejects_windows_drive_path(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir, "set-project-root", "C:\\foo"
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"project_root", proc.stderr)
        self.assertIsNone(self._read_state()["project_root"])

    def test_set_project_root_accepts_dot(self):
        # Sentinel for standalone mode — must remain valid (existing test
        # already exercises `client-app`; this pins the `.` case explicitly).
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", ".")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["project_root"], ".")


# ---------------------------------------------------------------------------
# PureValidatePathTests — exercise `_validate_path` directly without the CLI.
# ---------------------------------------------------------------------------


class PureValidatePathTests(unittest.TestCase):

    def test_accepts_dot(self):
        detect_report._validate_path(".", "f")  # no raise

    def test_accepts_simple_relative(self):
        detect_report._validate_path("client-app", "f")

    def test_accepts_nested_relative(self):
        detect_report._validate_path("apps/web", "f")
        detect_report._validate_path("services/api/users", "f")

    def test_accepts_trailing_slash(self):
        # Trailing slash is permitted; storage layer normalizes it later.
        detect_report._validate_path("foo/", "f")

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("", "f")

    def test_rejects_control_char(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("foo\nbar", "f")

    def test_rejects_absolute_posix(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("/Users/foo", "f")

    def test_rejects_leading_backslash(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("\\foo", "f")

    def test_rejects_windows_drive_uppercase(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("C:\\foo", "f")

    def test_rejects_windows_drive_lowercase_forward(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("c:/foo", "f")

    def test_rejects_bare_drive(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("C:", "f")

    def test_rejects_parent_only(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("..", "f")

    def test_rejects_parent_segment(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("foo/../bar", "f")

    def test_rejects_leading_parent(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("../foo", "f")

    def test_rejects_trailing_parent(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("foo/..", "f")

    def test_rejects_backslash_parent_segment(self):
        with self.assertRaises(ValueError):
            detect_report._validate_path("foo\\..\\bar", "f")


if __name__ == "__main__":
    unittest.main()
