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


# ---------------------------------------------------------------------------
# LibraryCategorySetterTests
# ---------------------------------------------------------------------------


# Derive (subcommand-name, field-name) pairs from the helper's source-of-truth
# constant so the test file can't drift from the schema. Adding a new
# library-category field to `LIBRARY_CATEGORY_FIELDS` automatically extends the
# parity sweep below; removing one shrinks it. The CLI flag name follows the
# convention `set-<field-with-underscores-to-dashes>`.
_LIBRARY_SUBCOMMANDS = tuple(
    ("set-" + name.replace("_", "-"), name)
    for name in detect_report.LIBRARY_CATEGORY_FIELDS
)


class LibraryCategorySetterTests(_EnvIsolationMixin, unittest.TestCase):
    """The 7 library-category setters share one shared implementation
    (`_set_library_category`); we exercise the full path on `set-auth-layer`
    and spot-check parity on two more setters.
    """

    def _read_state(self):
        return detect_report.parse_yaml(self.output_file.read_text(encoding="utf-8"))

    # -- Full sweep on set-auth-layer --------------------------------------

    def test_value_with_evidence_writes_both(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-auth-layer",
            "--value", "NextAuth",
            "--evidence", "package.json: next-auth dep + src/auth/[...nextauth]/route.ts",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["auth_layer"], "NextAuth")
        self.assertEqual(
            state["auth_layer_evidence"],
            "package.json: next-auth dep + src/auth/[...nextauth]/route.ts",
        )

    def test_value_na_alone_writes_na_and_null_evidence(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-auth-layer",
            "--value", "N/A",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["auth_layer"], "N/A")
        self.assertIsNone(state["auth_layer_evidence"])

    def test_null_alone_writes_both_none(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-auth-layer",
            "--null",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertIsNone(state["auth_layer"])
        self.assertIsNone(state["auth_layer_evidence"])

    def test_value_without_evidence_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-auth-layer",
            "--value", "NextAuth",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"auth_layer", proc.stderr)
        self.assertIn(b"--evidence", proc.stderr)
        # State unchanged.
        state = self._read_state()
        self.assertIsNone(state["auth_layer"])
        self.assertIsNone(state["auth_layer_evidence"])

    def test_null_with_evidence_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-auth-layer",
            "--null",
            "--evidence", "should not be here",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"auth_layer", proc.stderr)
        self.assertIn(b"--evidence", proc.stderr)
        state = self._read_state()
        self.assertIsNone(state["auth_layer"])
        self.assertIsNone(state["auth_layer_evidence"])

    def test_value_na_with_evidence_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-auth-layer",
            "--value", "N/A",
            "--evidence", "should not be here",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"auth_layer", proc.stderr)
        self.assertIn(b"--evidence", proc.stderr)
        state = self._read_state()
        self.assertIsNone(state["auth_layer"])

    def test_value_and_null_mutually_exclusive(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-auth-layer",
            "--value", "NextAuth",
            "--null",
        )
        self.assertNotEqual(proc.returncode, 0)
        # argparse mutex error.
        self.assertTrue(
            b"--null" in proc.stderr or b"--value" in proc.stderr,
            proc.stderr,
        )

    def test_evidence_whitespace_only_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-auth-layer",
            "--value", "NextAuth",
            "--evidence", "   ",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"non-empty", proc.stderr)

    def test_evidence_control_char_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-auth-layer",
            "--value", "NextAuth",
            "--evidence", "line1\nline2",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"control characters", proc.stderr)

    # -- Parity spot-check: set-styling (multi-layer value with " + ") -----

    def test_styling_multi_layer_value(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-styling",
            "--value", "Tailwind + CSS Modules",
            "--evidence", "tailwind.config.js + *.module.css under src/",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["styling"], "Tailwind + CSS Modules")
        self.assertEqual(
            state["styling_evidence"], "tailwind.config.js + *.module.css under src/"
        )

    # -- Parity spot-check: set-error-handling-pattern (no manifest dep) ----

    def test_error_handling_pattern_value_with_evidence(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-error-handling-pattern",
            "--value", "try/catch",
            "--evidence", "src/api/*.ts: try { ... } catch (err) { ... }",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["error_handling_pattern"], "try/catch")
        self.assertEqual(
            state["error_handling_pattern_evidence"],
            "src/api/*.ts: try { ... } catch (err) { ... }",
        )

    def test_error_handling_pattern_null(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-error-handling-pattern",
            "--null",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertIsNone(state["error_handling_pattern"])
        self.assertIsNone(state["error_handling_pattern_evidence"])

    # -- All 7 setter subcommands are dispatchable -------------------------

    def test_all_seven_setters_accept_null(self):
        # Loop-driven sanity: each library-category setter responds to --null
        # with rc=0 and writes both fields as None. Catches missing dispatch
        # wiring or schema field misnames in one shot.
        for sub_name, field_name in _LIBRARY_SUBCOMMANDS:
            _run_cli(self.devforge_dir, "reset")
            proc = _run_cli(self.devforge_dir, sub_name, "--null")
            self.assertEqual(
                proc.returncode, 0, "{0} failed: {1!r}".format(sub_name, proc.stderr)
            )
            state = self._read_state()
            self.assertIsNone(
                state[field_name], "{0}: value field not None".format(sub_name)
            )
            self.assertIsNone(
                state[field_name + "_evidence"],
                "{0}: evidence field not None".format(sub_name),
            )


# ---------------------------------------------------------------------------
# ArchitectureShapeSetterTests
# ---------------------------------------------------------------------------


class ArchitectureShapeSetterTests(_EnvIsolationMixin, unittest.TestCase):

    def _read_state(self):
        return detect_report.parse_yaml(self.output_file.read_text(encoding="utf-8"))

    def test_other_without_evidence_succeeds(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-architecture-shape",
            "--value", "other",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["architecture_shape"], "other")
        self.assertIsNone(state["architecture_evidence"])

    def test_other_with_evidence_succeeds(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-architecture-shape",
            "--value", "other",
            "--evidence", "no canonical signal — bespoke layout",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["architecture_shape"], "other")
        self.assertEqual(
            state["architecture_evidence"], "no canonical signal — bespoke layout"
        )

    def test_clean_with_evidence_succeeds(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-architecture-shape",
            "--value", "clean",
            "--evidence", "src/{domain,data,presentation}/ triad observed",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["architecture_shape"], "clean")
        self.assertEqual(
            state["architecture_evidence"],
            "src/{domain,data,presentation}/ triad observed",
        )

    def test_clean_without_evidence_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-architecture-shape",
            "--value", "clean",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"architecture_shape", proc.stderr)
        self.assertIn(b"--evidence", proc.stderr)
        # State unchanged.
        state = self._read_state()
        self.assertIsNone(state["architecture_shape"])
        self.assertIsNone(state["architecture_evidence"])

    def test_invalid_enum_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-architecture-shape",
            "--value", "spaghetti",
            "--evidence", "noodly",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"architecture_shape", proc.stderr)
        # State unchanged.
        state = self._read_state()
        self.assertIsNone(state["architecture_shape"])

    def test_all_eleven_enum_values_accepted(self):
        # Loop-driven enum coverage. `other` is the only value where
        # --evidence is optional; all others require it.
        all_values = sorted(detect_report.ENUM_FIELDS["architecture_shape"])
        self.assertEqual(len(all_values), 11)
        for v in all_values:
            _run_cli(self.devforge_dir, "reset")
            if v == "other":
                proc = _run_cli(
                    self.devforge_dir,
                    "set-architecture-shape",
                    "--value", v,
                )
            else:
                proc = _run_cli(
                    self.devforge_dir,
                    "set-architecture-shape",
                    "--value", v,
                    "--evidence", "evidence for {0}".format(v),
                )
            self.assertEqual(
                proc.returncode, 0, "{0} failed: {1!r}".format(v, proc.stderr)
            )
            state = self._read_state()
            self.assertEqual(state["architecture_shape"], v)


# ---------------------------------------------------------------------------
# RuntimeUrlSetterTests
# ---------------------------------------------------------------------------


class RuntimeUrlSetterTests(_EnvIsolationMixin, unittest.TestCase):

    def setUp(self):
        super().setUp()
        # find-nested-git's install root resolution = parent of devforge_dir.
        # We use the same convention here: install_root is `devforge_dir.parent`.
        # Replace the tmp setup so install_root is the tmp dir AND
        # devforge_dir is `<tmp>/.devforge`.
        self._install_root_tmp = tempfile.TemporaryDirectory()
        self.install_root = Path(self._install_root_tmp.name)
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir()
        self.output_file = self.devforge_dir / detect_report.OUTPUT_FILE_NAME

    def tearDown(self):
        self._install_root_tmp.cleanup()
        super().tearDown()

    def _read_state(self):
        return detect_report.parse_yaml(self.output_file.read_text(encoding="utf-8"))

    # -- Shape A: --value + --source -------------------------------------

    def test_set_with_existing_relative_path_standalone(self):
        # project_root = "." ; resolve <install_root>/<source>.
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-project-root", ".")
        # Plant a real file at install_root.
        config_path = self.install_root / "vite.config.ts"
        config_path.write_text("// vite config")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:5173",
            "--source", "vite.config.ts",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["runtime_url_value"], "http://localhost:5173")
        self.assertEqual(state["runtime_url_source"], "vite.config.ts")

    def test_set_with_nonexistent_relative_path_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-project-root", ".")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:5173",
            "--source", "nope/vite.config.ts",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"does not exist", proc.stderr)
        # State unchanged.
        state = self._read_state()
        self.assertIsNone(state["runtime_url_value"])

    def test_set_with_framework_default_no_path_check(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-project-root", ".")
        # Note: NO file is planted; framework-default literal must NOT trigger
        # path validation.
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:3000",
            "--source", "framework-default",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["runtime_url_value"], "http://localhost:3000")
        self.assertEqual(state["runtime_url_source"], "framework-default")

    def test_set_with_absolute_existing_path(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-project-root", ".")
        # Plant a real file using an absolute path inside the install_root.
        config_path = self.install_root / "vite.config.ts"
        config_path.write_text("// vite config")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:5173",
            "--source", str(config_path),  # absolute
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["runtime_url_value"], "http://localhost:5173")
        self.assertEqual(state["runtime_url_source"], str(config_path))

    def test_set_with_absolute_nonexistent_path_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-project-root", ".")
        bogus = self.install_root / "no-such-file.ts"
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:5173",
            "--source", str(bogus),
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"does not exist", proc.stderr)

    def test_set_with_wrapper_relative_path(self):
        # project_root = "client-app" ; resolve <install_root>/client-app/<source>.
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-project-root", "client-app")
        client_dir = self.install_root / "client-app"
        client_dir.mkdir()
        (client_dir / "vite.config.ts").write_text("// vite")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:5173",
            "--source", "vite.config.ts",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["runtime_url_value"], "http://localhost:5173")
        self.assertEqual(state["runtime_url_source"], "vite.config.ts")

    def test_set_with_wrapper_relative_path_missing_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-project-root", "client-app")
        # Don't plant the file — must reject.
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:5173",
            "--source", "vite.config.ts",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"does not exist", proc.stderr)

    def test_set_relative_without_project_root_rejected(self):
        # No project_root set yet; relative-path resolution can't proceed.
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:5173",
            "--source", "vite.config.ts",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"project_root", proc.stderr)

    def test_set_relative_parent_traversal_rejected_even_if_exists(self):
        # Audit-found gap: relative paths with `..` segments would bypass shape
        # validation if the resolved file existed. Plant a real file one level
        # above install_root and confirm the helper still rejects the source.
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-project-root", ".")
        # install_root.parent is the OS-tempdir parent. Plant `sneaky.ts` there.
        sneaky = self.install_root.parent / "sneaky.ts"
        sneaky.write_text("// planted")
        try:
            proc = _run_cli(
                self.devforge_dir,
                "set-runtime-url",
                "--value", "http://localhost:5173",
                "--source", "../sneaky.ts",
            )
        finally:
            try:
                sneaky.unlink()
            except OSError:
                pass
        self.assertNotEqual(proc.returncode, 0)
        # `_validate_path` raises with `parent-directory traversal '..'`.
        self.assertIn(b"..", proc.stderr)
        # State unchanged.
        state = self._read_state()
        self.assertIsNone(state["runtime_url_value"])
        self.assertIsNone(state["runtime_url_source"])

    def test_set_relative_embedded_parent_segment_rejected(self):
        # `foo/../bar` has an interior `..` segment — also rejected even though
        # it doesn't escape the project root in practice. `_validate_path` is
        # purely shape-based.
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-project-root", ".")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:5173",
            "--source", "foo/../bar",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"..", proc.stderr)
        state = self._read_state()
        self.assertIsNone(state["runtime_url_value"])

    # -- Shape B: --null + --reason --------------------------------------

    def test_null_with_reason_succeeds(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--null",
            "--reason", "CLI tool — no HTTP runtime",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertIsNone(state["runtime_url_value"])
        self.assertEqual(
            state["runtime_url_source"], "CLI tool — no HTTP runtime"
        )

    def test_null_without_reason_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--null",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"--reason", proc.stderr)

    def test_null_reason_whitespace_only_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--null",
            "--reason", "   ",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"non-empty", proc.stderr)

    # -- Cross-shape mutex --------------------------------------------------

    def test_value_and_null_mutually_exclusive(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:5173",
            "--null",
        )
        self.assertNotEqual(proc.returncode, 0)
        # argparse mutex.
        self.assertTrue(
            b"--null" in proc.stderr or b"--value" in proc.stderr,
            proc.stderr,
        )

    def test_value_with_reason_rejected(self):
        # --reason is only valid with --null. Combining --value with --reason
        # is an explicit rejection in our handler (not argparse).
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-project-root", ".")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:5173",
            "--source", "framework-default",
            "--reason", "should-not-be-here",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"--reason", proc.stderr)

    def test_value_without_source_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--value", "http://localhost:5173",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"--source", proc.stderr)

    def test_null_with_source_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-runtime-url",
            "--null",
            "--reason", "CLI tool",
            "--source", "vite.config.ts",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"--source", proc.stderr)


# ---------------------------------------------------------------------------
# Extended round-trip tests for the new schema fields.
# ---------------------------------------------------------------------------


class ExtendedYamlRoundTripTests(unittest.TestCase):
    """Cover the 18 new fields added for §4.4–§4.6."""

    def test_all_new_fields_default_emit(self):
        # Defaults: every new scalar emits as `name: null`.
        state = detect_report.default_state()
        text = detect_report.emit_yaml(state)
        for name in (
            "auth_layer", "auth_layer_evidence",
            "state_management", "state_management_evidence",
            "styling", "styling_evidence",
            "routing", "routing_evidence",
            "validation_library", "validation_library_evidence",
            "error_handling_library", "error_handling_library_evidence",
            "error_handling_pattern", "error_handling_pattern_evidence",
            "architecture_shape", "architecture_evidence",
            "runtime_url_value", "runtime_url_source",
        ):
            self.assertIn("{0}: null".format(name), text, name)

    def test_populated_library_categories_round_trip(self):
        state = detect_report.default_state()
        state["auth_layer"] = "NextAuth"
        state["auth_layer_evidence"] = "package.json: next-auth"
        state["state_management"] = "Redux Toolkit"
        state["state_management_evidence"] = "src/store.ts uses configureStore"
        state["styling"] = "Tailwind + CSS Modules"
        state["styling_evidence"] = "tailwind.config.js + *.module.css"
        state["routing"] = "Next.js App Router"
        state["routing_evidence"] = "app/ directory with route.ts files"
        state["validation_library"] = "Zod"
        state["validation_library_evidence"] = "src/schemas/*.ts uses z.object"
        state["error_handling_library"] = "Sentry"
        state["error_handling_library_evidence"] = "package.json: @sentry/nextjs"
        state["error_handling_pattern"] = "try/catch"
        state["error_handling_pattern_evidence"] = "src/api/*.ts: try { ... }"
        text = detect_report.emit_yaml(state)
        parsed = detect_report.parse_yaml(text)
        self.assertEqual(parsed, state)

    def test_architecture_other_with_null_evidence_round_trip(self):
        state = detect_report.default_state()
        state["architecture_shape"] = "other"
        state["architecture_evidence"] = None
        text = detect_report.emit_yaml(state)
        parsed = detect_report.parse_yaml(text)
        self.assertEqual(parsed["architecture_shape"], "other")
        self.assertIsNone(parsed["architecture_evidence"])

    def test_runtime_url_null_with_non_null_source_round_trips(self):
        # The "CLI tool with no runtime" case: value=null, source=<reason>.
        state = detect_report.default_state()
        state["runtime_url_value"] = None
        state["runtime_url_source"] = "CLI tool — no HTTP runtime"
        text = detect_report.emit_yaml(state)
        parsed = detect_report.parse_yaml(text)
        self.assertIsNone(parsed["runtime_url_value"])
        self.assertEqual(
            parsed["runtime_url_source"], "CLI tool — no HTTP runtime"
        )

    def test_runtime_url_set_round_trips(self):
        state = detect_report.default_state()
        state["runtime_url_value"] = "http://localhost:3000"
        state["runtime_url_source"] = "next.config.js"
        text = detect_report.emit_yaml(state)
        parsed = detect_report.parse_yaml(text)
        self.assertEqual(parsed["runtime_url_value"], "http://localhost:3000")
        self.assertEqual(parsed["runtime_url_source"], "next.config.js")

    def test_url_value_with_special_chars_quoted(self):
        # URLs contain `:` which is in YAML_SPECIAL_CHARS, so they must be
        # double-quoted on the wire.
        state = detect_report.default_state()
        state["runtime_url_value"] = "http://localhost:5173"
        text = detect_report.emit_yaml(state)
        self.assertIn('runtime_url_value: "http://localhost:5173"', text)


# ---------------------------------------------------------------------------
# SummarySubcommandTests
# ---------------------------------------------------------------------------


class SummarySubcommandTests(_EnvIsolationMixin, unittest.TestCase):
    """`summary` reads detection_report.yaml and prints a deterministic dump.

    Tests preseed the yaml using the real producer (`emit_yaml` via
    `_write_state`) so the summary parser sees on-the-wire state, never a
    hand-authored fixture. Stdout is byte-compared against the locked format.
    """

    def _write_yaml(self, state):
        """Persist `state` via the helper's atomic-write path."""
        target = self.devforge_dir / detect_report.OUTPUT_FILE_NAME
        target.parent.mkdir(parents=True, exist_ok=True)
        # Use the real emitter so byte-shape matches what setters would produce.
        target.write_text(detect_report.emit_yaml(state), encoding="utf-8")

    def test_full_brownfield_summary(self):
        """Realistic single-package brownfield project → byte-exact summary."""
        state = detect_report.default_state()
        state["project_root"] = "."
        state["workspace_mode"] = "standalone"
        state["project_state"] = "brownfield"
        state["default_branch"] = "main"
        state["primary_language"] = "TypeScript"
        state["packages_detected"] = [
            {"path": ".", "manifest": "package.json"},
        ]
        state["languages"] = [{"path": ".", "value": "TypeScript"}]
        state["frameworks"] = [{"path": ".", "value": "React"}]
        state["build_tools"] = [{"path": ".", "value": "Vite"}]
        state["build_commands"] = [{"path": ".", "value": "npm run build"}]
        state["type_check_commands"] = [{"path": ".", "value": "tsc --noEmit"}]
        state["lint_commands"] = [{"path": ".", "value": "eslint ."}]
        state["auth_layer"] = "Auth0"
        state["auth_layer_evidence"] = "package.json: @auth0/auth0-react"
        state["state_management"] = "Zustand"
        state["state_management_evidence"] = "package.json: zustand"
        state["styling"] = "Tailwind"
        state["styling_evidence"] = "package.json: tailwindcss"
        state["routing"] = "React-Router"
        state["routing_evidence"] = "package.json: react-router-dom"
        state["validation_library"] = "Zod"
        state["validation_library_evidence"] = "package.json: zod"
        state["error_handling_library"] = "Sentry"
        state["error_handling_library_evidence"] = "package.json: @sentry/react"
        state["error_handling_pattern"] = "Error boundaries"
        state["error_handling_pattern_evidence"] = "src/ErrorBoundary.tsx"
        state["architecture_shape"] = "layered"
        state["architecture_evidence"] = "src/ has presentation/domain/data dirs"
        state["runtime_url_value"] = "http://localhost:5173"
        state["runtime_url_source"] = "vite.config.ts"
        self._write_yaml(state)

        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        expected = (
            "## Detection Report Summary\n"
            "\n"
            "### Workspace\n"
            "- workspace_mode: standalone\n"
            "- project_root: .\n"
            "- project_state: brownfield\n"
            "- default_branch: main\n"
            "\n"
            "### Per-package classification (1 packages)\n"
            "- languages: TypeScript (1)\n"
            "- frameworks: React (1)\n"
            "- build_tools: Vite (1)\n"
            "- build_commands: npm run build (1)\n"
            "- type_check_commands: tsc --noEmit (1)\n"
            "- lint_commands: eslint . (1)\n"
            "\n"
            "### Project-level classification\n"
            "- primary_language: TypeScript\n"
            "- auth_layer: Auth0\n"
            "- state_management: Zustand\n"
            "- styling: Tailwind\n"
            "- routing: React-Router\n"
            "- validation_library: Zod\n"
            "- error_handling_library: Sentry\n"
            "- error_handling_pattern: Error boundaries\n"
            "- architecture_shape: layered\n"
            "- runtime_url_value: http://localhost:5173\n"
            "- runtime_url_source: vite.config.ts\n"
        )
        self.assertEqual(proc.stdout.decode("utf-8"), expected)

    def test_empty_project_summary(self):
        """Empty project: no packages, all per-package + project-level null."""
        state = detect_report.default_state()
        state["project_root"] = "."
        state["workspace_mode"] = "standalone"
        state["project_state"] = "empty"
        state["default_branch"] = "main"
        # primary_language and all classification fields stay None.
        # packages_detected stays [].
        self._write_yaml(state)

        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        expected = (
            "## Detection Report Summary\n"
            "\n"
            "### Workspace\n"
            "- workspace_mode: standalone\n"
            "- project_root: .\n"
            "- project_state: empty\n"
            "- default_branch: main\n"
            "\n"
            "### Per-package classification (0 packages)\n"
            "- no packages detected\n"
            "\n"
            "### Project-level classification\n"
            "- primary_language: null\n"
            "- auth_layer: null\n"
            "- state_management: null\n"
            "- styling: null\n"
            "- routing: null\n"
            "- validation_library: null\n"
            "- error_handling_library: null\n"
            "- error_handling_pattern: null\n"
            "- architecture_shape: null\n"
            "- runtime_url_value: null\n"
            "- runtime_url_source: null\n"
        )
        self.assertEqual(proc.stdout.decode("utf-8"), expected)

    def test_monorepo_27_packages_summary(self):
        """27 packages, 26 with frameworks=N/A and 1 with frameworks=Vue.

        Mimics the testForge20 monorepo shape. Per-package fields collapse:
        `frameworks: N/A (26), Vue (1)` ordered by count desc.
        """
        state = detect_report.default_state()
        state["project_root"] = "."
        state["workspace_mode"] = "standalone"
        state["project_state"] = "brownfield"
        state["default_branch"] = "main"
        state["primary_language"] = "TypeScript"

        packages = []
        languages = []
        frameworks = []
        build_tools = []
        build_commands = []
        type_check_commands = []
        lint_commands = []
        # 26 library/util packages.
        for i in range(26):
            path = "packages/lib-{0:02d}".format(i)
            packages.append({"path": path, "manifest": "package.json"})
            languages.append({"path": path, "value": "TypeScript"})
            frameworks.append({"path": path, "value": "N/A"})
            build_tools.append({"path": path, "value": "tsup"})
            build_commands.append({"path": path, "value": "tsup"})
            type_check_commands.append({"path": path, "value": "tsc --noEmit"})
            lint_commands.append({"path": path, "value": "eslint ."})
        # 1 web app with Vue.
        path = "apps/app-web"
        packages.append({"path": path, "manifest": "package.json"})
        languages.append({"path": path, "value": "TypeScript"})
        frameworks.append({"path": path, "value": "Vue"})
        build_tools.append({"path": path, "value": "Vite"})
        build_commands.append({"path": path, "value": "vite build"})
        type_check_commands.append({"path": path, "value": "vue-tsc --noEmit"})
        lint_commands.append({"path": path, "value": "eslint ."})

        state["packages_detected"] = packages
        state["languages"] = languages
        state["frameworks"] = frameworks
        state["build_tools"] = build_tools
        state["build_commands"] = build_commands
        state["type_check_commands"] = type_check_commands
        state["lint_commands"] = lint_commands
        self._write_yaml(state)

        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn(
            "### Per-package classification (27 packages)\n", out
        )
        # All-TypeScript: collapses to a single bucket.
        self.assertIn("- languages: TypeScript (27)\n", out)
        # Frameworks: 26 N/A vs 1 Vue → count desc.
        self.assertIn("- frameworks: N/A (26), Vue (1)\n", out)
        # build_tools: 26 tsup, 1 Vite.
        self.assertIn("- build_tools: tsup (26), Vite (1)\n", out)
        # build_commands: 26 tsup, 1 vite build.
        self.assertIn("- build_commands: tsup (26), vite build (1)\n", out)
        # type_check_commands: 26 tsc, 1 vue-tsc.
        self.assertIn(
            "- type_check_commands: tsc --noEmit (26), vue-tsc --noEmit (1)\n",
            out,
        )
        # lint_commands: all 27 same.
        self.assertIn("- lint_commands: eslint . (27)\n", out)

    def test_count_desc_alphabetical_tiebreak(self):
        """Tied counts → alphabetical ascending tiebreak (case-sensitive)."""
        state = detect_report.default_state()
        state["project_root"] = "."
        state["workspace_mode"] = "standalone"
        state["project_state"] = "brownfield"
        state["default_branch"] = "main"
        state["packages_detected"] = [
            {"path": "p{0}".format(i), "manifest": "package.json"} for i in range(6)
        ]
        # Three "cmd-b" then three "cmd-a" — alphabetical sort must reverse
        # the input order so cmd-a (lex < cmd-b) appears first under the
        # equal-count tiebreak.
        state["build_commands"] = [
            {"path": "p0", "value": "cmd-b"},
            {"path": "p1", "value": "cmd-b"},
            {"path": "p2", "value": "cmd-b"},
            {"path": "p3", "value": "cmd-a"},
            {"path": "p4", "value": "cmd-a"},
            {"path": "p5", "value": "cmd-a"},
        ]
        # Other per-package fields populated to satisfy "non-empty packages
        # show all six fields"; values irrelevant to the assertion.
        for fld in (
            "languages", "frameworks", "build_tools",
            "type_check_commands", "lint_commands",
        ):
            state[fld] = [
                {"path": "p{0}".format(i), "value": "x"} for i in range(6)
            ]
        self._write_yaml(state)

        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn("- build_commands: cmd-a (3), cmd-b (3)\n", out)

    def test_null_field_renders_null(self):
        """A project-level field set to None prints as `<name>: null`."""
        state = detect_report.default_state()
        state["project_root"] = "."
        state["workspace_mode"] = "standalone"
        state["project_state"] = "brownfield"
        state["default_branch"] = "main"
        state["primary_language"] = "TypeScript"
        state["packages_detected"] = [
            {"path": ".", "manifest": "package.json"}
        ]
        for fld in (
            "languages", "frameworks", "build_tools", "build_commands",
            "type_check_commands", "lint_commands",
        ):
            state[fld] = [{"path": ".", "value": "x"}]
        # auth_layer left as None (default).
        self._write_yaml(state)

        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn("- auth_layer: null\n", out)

    def test_empty_string_in_value_path_array_renders_quoted(self):
        """Empty-string `value` in a value_path_array renders as `""` (quoted).

        Bare-colon output (`- languages:  (1)`) is visually
        indistinguishable from a truncated field label; quoting
        disambiguates. Set-time validation rejects empty strings on
        normal setter paths, but a hand-edited yaml could plant one and
        the summary must not silently swallow it.
        """
        state = detect_report.default_state()
        state["project_root"] = "."
        state["workspace_mode"] = "standalone"
        state["project_state"] = "brownfield"
        state["default_branch"] = "main"
        state["packages_detected"] = [{"path": ".", "manifest": "package.json"}]
        # Empty-string value in the per-package languages array.
        state["languages"] = [{"path": ".", "value": ""}]
        # Other per-package fields populated so the section renders fully.
        for fld in (
            "frameworks", "build_tools", "build_commands",
            "type_check_commands", "lint_commands",
        ):
            state[fld] = [{"path": ".", "value": "x"}]
        self._write_yaml(state)

        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn("- languages: \"\" (1)\n", out)

    def test_evidence_siblings_hidden(self):
        """`<field>_evidence` keys are NOT emitted in summary output."""
        state = detect_report.default_state()
        state["project_root"] = "."
        state["workspace_mode"] = "standalone"
        state["project_state"] = "brownfield"
        state["default_branch"] = "main"
        state["packages_detected"] = []
        state["auth_layer"] = "Okta"
        state["auth_layer_evidence"] = "package.json: @okta/okta-auth-js"
        state["architecture_shape"] = "layered"
        state["architecture_evidence"] = "evident from src/ layout"
        self._write_yaml(state)

        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn("- auth_layer: Okta\n", out)
        self.assertNotIn("auth_layer_evidence", out)
        self.assertNotIn("architecture_evidence", out)
        self.assertNotIn("@okta/okta-auth-js", out)

    def test_missing_yaml_file_exits_nonzero(self):
        """When yaml is absent, exits with code 1 and stderr names the file."""
        # _EnvIsolationMixin gives us an empty devforge_dir — no yaml present.
        self.assertFalse(self.output_file.exists())
        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"detection_report.yaml not found", proc.stderr)
        # Path is named in the error so the operator can find what's missing.
        self.assertIn(str(self.output_file).encode("utf-8"), proc.stderr)

    def test_malformed_yaml_exits_nonzero(self):
        """Garbage in yaml file → exit 1 + stderr indicates parse error."""
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.output_file.write_text(
            "this is: not valid {{ yaml [\n  ?? broken\n", encoding="utf-8"
        )
        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"parse error", proc.stderr)

    def test_n_a_sentinel_renders_verbatim(self):
        """N/A is just a string value — rendered as `N/A (count)`, no special-case."""
        state = detect_report.default_state()
        state["project_root"] = "."
        state["workspace_mode"] = "standalone"
        state["project_state"] = "brownfield"
        state["default_branch"] = "main"
        state["packages_detected"] = [
            {"path": "a", "manifest": "package.json"},
            {"path": "b", "manifest": "package.json"},
            {"path": "c", "manifest": "package.json"},
        ]
        state["languages"] = [
            {"path": "a", "value": "TypeScript"},
            {"path": "b", "value": "TypeScript"},
            {"path": "c", "value": "TypeScript"},
        ]
        state["frameworks"] = [
            {"path": "a", "value": "N/A"},
            {"path": "b", "value": "N/A"},
            {"path": "c", "value": "Vue"},
        ]
        for fld in (
            "build_tools", "build_commands", "type_check_commands",
            "lint_commands",
        ):
            state[fld] = [
                {"path": "a", "value": "x"},
                {"path": "b", "value": "x"},
                {"path": "c", "value": "x"},
            ]
        self._write_yaml(state)

        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn("- frameworks: N/A (2), Vue (1)\n", out)

    def test_runtime_url_value_with_url_renders_correctly(self):
        """A real URL with `://`, host:port → exact line in summary."""
        state = detect_report.default_state()
        state["project_root"] = "."
        state["workspace_mode"] = "standalone"
        state["project_state"] = "brownfield"
        state["default_branch"] = "main"
        state["packages_detected"] = []
        state["runtime_url_value"] = "https://okta.example.com:8080"
        state["runtime_url_source"] = "config/auth.ts"
        self._write_yaml(state)

        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn(
            "- runtime_url_value: https://okta.example.com:8080\n", out
        )
        self.assertIn("- runtime_url_source: config/auth.ts\n", out)

    def test_deterministic_output_byte_identical(self):
        """Running summary twice on the same yaml → byte-identical stdout."""
        state = detect_report.default_state()
        state["project_root"] = "."
        state["workspace_mode"] = "standalone"
        state["project_state"] = "brownfield"
        state["default_branch"] = "main"
        state["primary_language"] = "Python"
        # Multi-package + ties to ensure the sort path is exercised.
        state["packages_detected"] = [
            {"path": "svc-a", "manifest": "pyproject.toml"},
            {"path": "svc-b", "manifest": "pyproject.toml"},
            {"path": "svc-c", "manifest": "pyproject.toml"},
        ]
        state["languages"] = [
            {"path": "svc-a", "value": "Python"},
            {"path": "svc-b", "value": "Python"},
            {"path": "svc-c", "value": "Python"},
        ]
        state["frameworks"] = [
            {"path": "svc-a", "value": "FastAPI"},
            {"path": "svc-b", "value": "Django"},
            {"path": "svc-c", "value": "Flask"},
        ]
        for fld in (
            "build_tools", "build_commands", "type_check_commands",
            "lint_commands",
        ):
            state[fld] = [
                {"path": "svc-a", "value": "v1"},
                {"path": "svc-b", "value": "v1"},
                {"path": "svc-c", "value": "v2"},
            ]
        self._write_yaml(state)

        proc1 = _run_cli(self.devforge_dir, "summary")
        proc2 = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc1.returncode, 0, proc1.stderr)
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        self.assertEqual(proc1.stdout, proc2.stdout)


if __name__ == "__main__":
    unittest.main()
