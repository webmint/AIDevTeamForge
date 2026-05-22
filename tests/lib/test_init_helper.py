"""Tests for src/devforge/lib/init_helper.py.

Covers the closed-shape yaml emitter+parser, all 8 subcommands, set-time
validation, atomic writes, the find-nested-git read-only scan, the
launcher script, and DEVFORGE_DIR env override.

Each test runs in its own `tempfile.TemporaryDirectory` and points the
helper at it via the `DEVFORGE_DIR` environment variable, so the repo's
real `.devforge/` is never touched. The env override is restored in
tearDown so tests can't bleed into each other.

Pure-function tests (`emit_yaml`, `parse_yaml`, `_output_file_path`)
import the module directly. End-to-end CLI tests invoke the .py file as
a subprocess, exercising the real argparse + dispatch path. Round-trip
tests parse the yaml the helper actually produced (no hand-authored
fixtures) — the parser sees only what the emitter emits.

Stdlib only.
"""

import json
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
_HELPER_PY = _LIB_DIR / "init_helper.py"
_LAUNCHER = _LIB_DIR / "init_helper"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import init_helper  # noqa: E402


def _run_cli(devforge_dir, *args):
    """Invoke `init_helper.py <args>` as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_launcher(devforge_dir, *args):
    """Invoke the POSIX shell launcher as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        ["sh", str(_LAUNCHER)] + list(args),
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
        self.output_file = self.devforge_dir / init_helper.OUTPUT_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def _read_state(self):
        return init_helper.parse_yaml(
            self.output_file.read_text(encoding="utf-8")
        )


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
            path = init_helper._output_file_path()
            self.assertEqual(path, Path(tmp) / init_helper.OUTPUT_FILE_NAME)

    def test_no_env_falls_back_to_helper_location(self):
        path = init_helper._output_file_path()
        expected_dir = Path(init_helper.__file__).resolve().parent.parent
        self.assertEqual(path, expected_dir / init_helper.OUTPUT_FILE_NAME)

    def test_resolution_is_per_call_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp_a:
            os.environ["DEVFORGE_DIR"] = tmp_a
            first = init_helper._output_file_path()
        with tempfile.TemporaryDirectory() as tmp_b:
            os.environ["DEVFORGE_DIR"] = tmp_b
            second = init_helper._output_file_path()
        self.assertNotEqual(first, second)

    def test_output_filename_is_init_yaml(self):
        self.assertEqual(init_helper.OUTPUT_FILE_NAME, "init.yaml")


# ---------------------------------------------------------------------------
# DefaultStateTests
# ---------------------------------------------------------------------------


class DefaultStateTests(unittest.TestCase):

    def test_default_state_shape(self):
        s = init_helper.default_state()
        self.assertEqual(
            s,
            {
                "workspace_mode": None,
                "project_root": None,
                "project_state": None,
                "default_branch": None,
                "packages_detected": [],
                "test_infra": {
                    "frontend": None,
                    "backend": None,
                    "e2e": None,
                    "status": "absent",
                },
            },
        )

    def test_field_schema_order_is_locked(self):
        names = [name for name, _ in init_helper.FIELD_SCHEMA]
        self.assertEqual(
            names,
            [
                "workspace_mode",
                "project_root",
                "project_state",
                "default_branch",
                "packages_detected",
                "test_infra",
            ],
        )


# ---------------------------------------------------------------------------
# EmitParseRoundTripTests
# ---------------------------------------------------------------------------


class EmitParseRoundTripTests(unittest.TestCase):

    def test_defaults_round_trip(self):
        s = init_helper.default_state()
        text = init_helper.emit_yaml(s)
        s2 = init_helper.parse_yaml(text)
        self.assertEqual(s, s2)

    def test_field_order_in_emit(self):
        text = init_helper.emit_yaml(init_helper.default_state())
        # Lines come in FIELD_SCHEMA order.
        lines = text.splitlines()
        self.assertEqual(lines[0], "workspace_mode: null")
        self.assertEqual(lines[1], "project_root: null")
        self.assertEqual(lines[2], "project_state: null")
        self.assertEqual(lines[3], "default_branch: null")
        self.assertEqual(lines[4], "packages_detected: []")
        # test_infra block follows.
        self.assertEqual(lines[5], "test_infra:")
        self.assertEqual(lines[6], "  frontend: null")
        self.assertEqual(lines[7], "  backend: null")
        self.assertEqual(lines[8], "  e2e: null")
        self.assertEqual(lines[9], "  status: absent")

    def test_emit_ends_with_newline(self):
        text = init_helper.emit_yaml(init_helper.default_state())
        self.assertTrue(text.endswith("\n"))

    def test_round_trip_all_fields_populated(self):
        s = {
            "workspace_mode": "wrapper",
            "project_root": "client-app",
            "project_state": "brownfield",
            "default_branch": "main",
            "packages_detected": [
                {"path": ".", "manifest": "package.json"},
                {"path": "apps/web", "manifest": "package.json"},
            ],
            "test_infra": {
                "frontend": "vitest",
                "backend": "pytest",
                "e2e": "playwright",
                "status": "present",
            },
        }
        text = init_helper.emit_yaml(s)
        s2 = init_helper.parse_yaml(text)
        self.assertEqual(s, s2)

    def test_emit_quotes_reserved_words(self):
        s = init_helper.default_state()
        s["default_branch"] = "null"
        text = init_helper.emit_yaml(s)
        self.assertIn("default_branch: \"null\"", text)
        s2 = init_helper.parse_yaml(text)
        self.assertEqual(s2["default_branch"], "null")

    def test_emit_quotes_special_chars(self):
        s = init_helper.default_state()
        s["default_branch"] = "feature/foo bar"
        text = init_helper.emit_yaml(s)
        self.assertIn("default_branch: \"feature/foo bar\"", text)
        s2 = init_helper.parse_yaml(text)
        self.assertEqual(s2["default_branch"], "feature/foo bar")

    def test_emit_quotes_purely_numeric(self):
        s = init_helper.default_state()
        s["default_branch"] = "42"
        text = init_helper.emit_yaml(s)
        self.assertIn("default_branch: \"42\"", text)
        s2 = init_helper.parse_yaml(text)
        self.assertEqual(s2["default_branch"], "42")

    def test_emit_quotes_hex_number_like(self):
        # `0x1a` parses as 26 under real YAML libraries — must be quoted on
        # emit even though our closed-shape parser would accept it bare.
        s = init_helper.default_state()
        s["default_branch"] = "0x1a"
        text = init_helper.emit_yaml(s)
        self.assertIn("default_branch: \"0x1a\"", text)
        self.assertNotIn("default_branch: 0x1a\n", text)
        s2 = init_helper.parse_yaml(text)
        self.assertEqual(s2["default_branch"], "0x1a")

    def test_emit_quotes_octal_prefix_number_like(self):
        s = init_helper.default_state()
        s["default_branch"] = "0o77"
        text = init_helper.emit_yaml(s)
        self.assertIn("default_branch: \"0o77\"", text)
        self.assertNotIn("default_branch: 0o77\n", text)
        s2 = init_helper.parse_yaml(text)
        self.assertEqual(s2["default_branch"], "0o77")

    def test_emit_quotes_binary_prefix_number_like(self):
        s = init_helper.default_state()
        s["default_branch"] = "0b11"
        text = init_helper.emit_yaml(s)
        self.assertIn("default_branch: \"0b11\"", text)
        self.assertNotIn("default_branch: 0b11\n", text)
        s2 = init_helper.parse_yaml(text)
        self.assertEqual(s2["default_branch"], "0b11")

    def test_emit_quotes_leading_zero_octal_like(self):
        # Leading-zero octal form (`077`) — `int("077", 0)` accepts only
        # "0" or "0o..." forms in py3, but `077` triggers ValueError under
        # base 0. We still expect quoting because `float("077")` succeeds.
        # Guard against regressions either way.
        s = init_helper.default_state()
        s["default_branch"] = "077"
        text = init_helper.emit_yaml(s)
        self.assertIn("default_branch: \"077\"", text)
        self.assertNotIn("default_branch: 077\n", text)
        s2 = init_helper.parse_yaml(text)
        self.assertEqual(s2["default_branch"], "077")

    def test_emit_escapes_backslash_and_quote(self):
        s = init_helper.default_state()
        s["default_branch"] = 'has\\backslash"and"quote'
        text = init_helper.emit_yaml(s)
        s2 = init_helper.parse_yaml(text)
        self.assertEqual(s2["default_branch"], 'has\\backslash"and"quote')

    def test_packages_detected_block_form(self):
        s = init_helper.default_state()
        s["packages_detected"] = [{"path": "apps/web", "manifest": "package.json"}]
        text = init_helper.emit_yaml(s)
        self.assertIn("packages_detected:\n  - path: apps/web\n    manifest: package.json", text)


# ---------------------------------------------------------------------------
# ParserErrorTests
# ---------------------------------------------------------------------------


class ParserErrorTests(unittest.TestCase):

    def test_unknown_field_rejected(self):
        with self.assertRaises(init_helper.YamlParseError):
            init_helper.parse_yaml("bogus: value\n")

    def test_unsupported_anchor_rejected(self):
        with self.assertRaises(init_helper.YamlParseError):
            init_helper.parse_yaml("workspace_mode: &anchor x\n")

    def test_unsupported_flow_mapping_rejected(self):
        with self.assertRaises(init_helper.YamlParseError):
            init_helper.parse_yaml("workspace_mode: {a: b}\n")

    def test_single_quotes_rejected(self):
        with self.assertRaises(init_helper.YamlParseError):
            init_helper.parse_yaml("workspace_mode: 'standalone'\n")

    def test_unterminated_double_quote_rejected(self):
        with self.assertRaises(init_helper.YamlParseError):
            init_helper.parse_yaml("workspace_mode: \"unterminated\n")

    def test_bad_indent_rejected(self):
        with self.assertRaises(init_helper.YamlParseError):
            init_helper.parse_yaml("   workspace_mode: x\n")


# ---------------------------------------------------------------------------
# ResetTests
# ---------------------------------------------------------------------------


class ResetTests(_EnvIsolationMixin, unittest.TestCase):

    def test_reset_creates_file(self):
        self.assertFalse(self.output_file.exists())
        proc = _run_cli(self.devforge_dir, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.output_file.exists())

    def test_reset_creates_devforge_dir_when_absent(self):
        # Use a nested path that doesn't yet exist as our DEVFORGE_DIR.
        nested = self.devforge_dir / "deeper"
        proc = _run_cli(nested, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((nested / init_helper.OUTPUT_FILE_NAME).exists())

    def test_reset_contents_are_defaults(self):
        proc = _run_cli(self.devforge_dir, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), init_helper.default_state())

    def test_reset_is_idempotent_byte_identical(self):
        _run_cli(self.devforge_dir, "reset")
        first = self.output_file.read_bytes()
        _run_cli(self.devforge_dir, "reset")
        second = self.output_file.read_bytes()
        self.assertEqual(first, second)

    def test_reset_overwrites_populated_state(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-workspace-mode", "wrapper")
        _run_cli(self.devforge_dir, "set-project-root", "client")
        _run_cli(
            self.devforge_dir, "add-package", "--path", ".", "--manifest", "package.json"
        )
        proc = _run_cli(self.devforge_dir, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), init_helper.default_state())

    def test_reset_does_not_delete_file(self):
        _run_cli(self.devforge_dir, "reset")
        self.assertTrue(self.output_file.exists())
        _run_cli(self.devforge_dir, "reset")
        self.assertTrue(self.output_file.exists())

    def test_no_subcommand_returns_2(self):
        proc = _run_cli(self.devforge_dir)
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# SetWorkspaceModeTests
# ---------------------------------------------------------------------------


class SetWorkspaceModeTests(_EnvIsolationMixin, unittest.TestCase):

    def test_accepts_standalone(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-workspace-mode", "standalone")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["workspace_mode"], "standalone")

    def test_accepts_wrapper(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-workspace-mode", "wrapper")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["workspace_mode"], "wrapper")

    def test_rejects_uppercase(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-workspace-mode", "STANDALONE")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"workspace_mode", proc.stderr)
        self.assertIsNone(self._read_state()["workspace_mode"])

    def test_rejects_unknown_mode(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-workspace-mode", "wrapper-thing")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"workspace_mode", proc.stderr)
        self.assertIsNone(self._read_state()["workspace_mode"])

    def test_rejects_empty(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-workspace-mode", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIsNone(self._read_state()["workspace_mode"])

    def test_rejects_control_chars(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir, "set-workspace-mode", "stand\nalone"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIsNone(self._read_state()["workspace_mode"])


# ---------------------------------------------------------------------------
# SetProjectRootTests
# ---------------------------------------------------------------------------


class SetProjectRootTests(_EnvIsolationMixin, unittest.TestCase):

    def test_accepts_dot(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", ".")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["project_root"], ".")

    def test_accepts_subfolder(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", "client-app")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["project_root"], "client-app")

    def test_accepts_nested_path(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", "src/app")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["project_root"], "src/app")

    def test_normalizes_trailing_slash(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", "client-app/")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["project_root"], "client-app")

    def test_rejects_empty(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIsNone(self._read_state()["project_root"])

    def test_rejects_control_chars(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", "bad\nname")
        self.assertEqual(proc.returncode, 2)
        self.assertIsNone(self._read_state()["project_root"])

    def test_rejects_null_byte(self):
        # Null bytes can't survive subprocess argv (POSIX exec rejects
        # them), so this is an in-process validator test rather than a
        # CLI round-trip. Null bytes have ord() < 0x20 so
        # `_has_control_chars` flags them via `_validate_string`.
        with self.assertRaises(ValueError):
            init_helper._validate_path("bad\x00name", "project_root")

    def test_rejects_absolute_path(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", "/etc/passwd")
        self.assertEqual(proc.returncode, 2)
        self.assertIsNone(self._read_state()["project_root"])

    def test_rejects_traversal(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-root", "../escape")
        self.assertEqual(proc.returncode, 2)
        self.assertIsNone(self._read_state()["project_root"])


# ---------------------------------------------------------------------------
# SetProjectStateTests
# ---------------------------------------------------------------------------


class SetProjectStateTests(_EnvIsolationMixin, unittest.TestCase):

    def test_accepts_empty(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-state", "empty")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["project_state"], "empty")

    def test_accepts_brownfield(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-state", "brownfield")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["project_state"], "brownfield")

    def test_rejects_other(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-state", "legacy")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"project_state", proc.stderr)
        self.assertIsNone(self._read_state()["project_state"])

    def test_rejects_uppercase(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-project-state", "EMPTY")
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# SetDefaultBranchTests
# ---------------------------------------------------------------------------


class SetDefaultBranchTests(_EnvIsolationMixin, unittest.TestCase):

    def test_accepts_main(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-default-branch", "main")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["default_branch"], "main")

    def test_accepts_master(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-default-branch", "master")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["default_branch"], "master")

    def test_accepts_develop(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-default-branch", "develop")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["default_branch"], "develop")

    def test_accepts_feature_slash_name(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir, "set-default-branch", "feature/foo"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state()["default_branch"], "feature/foo")

    def test_rejects_empty(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "set-default-branch", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIsNone(self._read_state()["default_branch"])

    def test_rejects_control_chars(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir, "set-default-branch", "main\nbranch"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIsNone(self._read_state()["default_branch"])


# ---------------------------------------------------------------------------
# AddPackageTests
# ---------------------------------------------------------------------------


class AddPackageTests(_EnvIsolationMixin, unittest.TestCase):

    def test_happy_path_root_package(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path",
            ".",
            "--manifest",
            "package.json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages_detected"],
            [{"path": ".", "manifest": "package.json"}],
        )

    def test_happy_path_nested_package(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path",
            "apps/web",
            "--manifest",
            "package.json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages_detected"],
            [{"path": "apps/web", "manifest": "package.json"}],
        )

    def test_multiple_packages_appended_in_order(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(
            self.devforge_dir,
            "add-package",
            "--path",
            "apps/web",
            "--manifest",
            "package.json",
        )
        _run_cli(
            self.devforge_dir,
            "add-package",
            "--path",
            "services/api",
            "--manifest",
            "pyproject.toml",
        )
        self.assertEqual(
            self._read_state()["packages_detected"],
            [
                {"path": "apps/web", "manifest": "package.json"},
                {"path": "services/api", "manifest": "pyproject.toml"},
            ],
        )

    def test_duplicate_path_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(
            self.devforge_dir,
            "add-package",
            "--path",
            "apps/web",
            "--manifest",
            "package.json",
        )
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path",
            "apps/web",
            "--manifest",
            "package.json",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"already present", proc.stderr)

    def test_duplicate_path_rejection_uses_normalized_compare(self):
        # `apps/web` and `apps/web/` should collide.
        _run_cli(self.devforge_dir, "reset")
        _run_cli(
            self.devforge_dir,
            "add-package",
            "--path",
            "apps/web",
            "--manifest",
            "package.json",
        )
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path",
            "apps/web/",
            "--manifest",
            "package.json",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"already present", proc.stderr)

    def test_missing_path_arg_errors(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir, "add-package", "--manifest", "package.json"
        )
        self.assertEqual(proc.returncode, 2)

    def test_missing_manifest_arg_errors(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir, "add-package", "--path", "apps/web"
        )
        self.assertEqual(proc.returncode, 2)

    def test_path_with_traversal_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path",
            "../escape",
            "--manifest",
            "package.json",
        )
        self.assertEqual(proc.returncode, 2)

    def test_empty_manifest_rejected(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path",
            "apps/web",
            "--manifest",
            "",
        )
        self.assertEqual(proc.returncode, 2)

    def test_normalized_storage_strips_trailing_slash(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "add-package",
            "--path",
            "apps/web/",
            "--manifest",
            "package.json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages_detected"][0]["path"], "apps/web"
        )


# ---------------------------------------------------------------------------
# FindNestedGitTests
# ---------------------------------------------------------------------------


class FindNestedGitTests(unittest.TestCase):
    """find-nested-git resolves install root as `parent of .devforge/`.

    To exercise the scan, we create a temp dir layout:
      tmp/.devforge/        ← DEVFORGE_DIR points here
      tmp/<candidate>/.git/ ← scan should find these

    The `_output_file_path().parent` returns DEVFORGE_DIR; its parent
    is the install root (=tmp). Children of tmp are scanned.
    """

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.install_root = Path(self._tmp.name)
        # DEVFORGE_DIR must be a child of install_root for the scan to
        # see the right install root.
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def _create_nested_git(self, name):
        d = self.install_root / name
        d.mkdir()
        (d / ".git").mkdir()
        return d

    def _create_plain_dir(self, name):
        d = self.install_root / name
        d.mkdir()
        return d

    def test_empty_install_root_no_output(self):
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Only `.devforge` lives in install_root; it's a hidden dir, so
        # nothing should be reported.
        self.assertEqual(proc.stdout, b"")

    def test_skip_listed_dirs_filtered(self):
        # All children are in the skip list; even with a `.git` they are
        # ignored.
        self._create_nested_git("node_modules")
        self._create_nested_git("dist")
        self._create_nested_git("__pycache__")
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"")

    def test_valid_candidate_listed(self):
        self._create_nested_git("client")
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"client\n")

    def test_mixed_valid_and_skip(self):
        self._create_nested_git("client")
        self._create_nested_git("node_modules")
        self._create_nested_git("server")
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # sorted alphabetical: client, server (node_modules filtered)
        self.assertEqual(proc.stdout, b"client\nserver\n")

    def test_hidden_dirs_skipped(self):
        self._create_nested_git(".hidden")
        self._create_nested_git(".another")
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"")

    def test_dir_without_git_skipped(self):
        # Plain directory without a `.git/` child is not a candidate.
        self._create_plain_dir("not-a-repo")
        self._create_nested_git("real-repo")
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"real-repo\n")

    def test_find_nested_git_does_not_write_state(self):
        # The output yaml should not be created by find-nested-git.
        output_file = self.devforge_dir / init_helper.OUTPUT_FILE_NAME
        self.assertFalse(output_file.exists())
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(output_file.exists())

    def test_git_as_file_not_dir_skipped(self):
        # If `.git` is a file (e.g., submodule pointer), it's not a
        # directory — should NOT match.
        d = self.install_root / "submodule-pointer"
        d.mkdir()
        (d / ".git").write_text("gitdir: ../something\n")
        proc = _run_cli(self.devforge_dir, "find-nested-git")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"")


# ---------------------------------------------------------------------------
# CLISurfaceTests
# ---------------------------------------------------------------------------


class CLISurfaceTests(_EnvIsolationMixin, unittest.TestCase):

    def test_help_lists_core_subcommands(self):
        proc = _run_cli(self.devforge_dir, "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        for sub in (
            b"reset",
            b"set-workspace-mode",
            b"set-project-root",
            b"set-project-state",
            b"set-default-branch",
            b"add-package",
            b"find-nested-git",
            b"summary",
            b"verify",
            b"detect-test-infra",
            b"set-test-infra",
        ):
            self.assertIn(sub, out)

    def test_unknown_subcommand_errors(self):
        proc = _run_cli(self.devforge_dir, "do-something-bogus")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"invalid choice", proc.stderr)


# ---------------------------------------------------------------------------
# LauncherTests
# ---------------------------------------------------------------------------


class LauncherTests(_EnvIsolationMixin, unittest.TestCase):

    def test_launcher_dispatches_help(self):
        proc = _run_launcher(self.devforge_dir, "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(b"reset", proc.stdout)

    def test_launcher_dispatches_reset(self):
        proc = _run_launcher(self.devforge_dir, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.output_file.exists())


# ---------------------------------------------------------------------------
# DevforgeDirEnvTests
# ---------------------------------------------------------------------------


class DevforgeDirEnvTests(_EnvIsolationMixin, unittest.TestCase):

    def test_env_dir_is_used_for_output_file(self):
        # Run reset against a deeply nested DEVFORGE_DIR; the artifact
        # must land at <env>/init.yaml, not at any other location.
        nested = self.devforge_dir / "a" / "b" / "c"
        proc = _run_cli(nested, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((nested / "init.yaml").exists())
        # No init.yaml outside the env path.
        self.assertFalse((self.devforge_dir / "init.yaml").exists())

    def test_no_env_uses_helper_relative(self):
        # When DEVFORGE_DIR is unset, the helper resolves to its
        # own location's parent. We verify this in-process to avoid
        # writing to the real repo (subprocess would hit the real
        # `.devforge/`).
        os.environ.pop("DEVFORGE_DIR", None)
        path = init_helper._output_file_path()
        expected_dir = Path(init_helper.__file__).resolve().parent.parent
        self.assertEqual(path, expected_dir / "init.yaml")


# ---------------------------------------------------------------------------
# SummaryTests
# ---------------------------------------------------------------------------


class SummaryTests(_EnvIsolationMixin, unittest.TestCase):
    """`summary` subcommand: render init.yaml to deterministic stdout.

    Round-trip tests build state via the real CLI (reset + setters +
    add-package) before invoking `summary`, so the parser sees only what
    the emitter emits.
    """

    def _populate_three_packages(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-workspace-mode", "wrapper")
        _run_cli(self.devforge_dir, "set-project-root", "client-app")
        _run_cli(self.devforge_dir, "set-project-state", "brownfield")
        _run_cli(self.devforge_dir, "set-default-branch", "main")
        _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", ".",
            "--manifest", "package.json",
        )
        _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "scripts",
            "--manifest", "package.json",
        )
        _run_cli(
            self.devforge_dir,
            "add-package",
            "--path", "apps/web",
            "--manifest", "package.json",
        )

    def test_happy_path_three_packages(self):
        self._populate_three_packages()
        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        # Header + workspace block.
        self.assertIn("## Init Report", out)
        self.assertIn("### Workspace", out)
        self.assertIn("- workspace_mode: wrapper", out)
        self.assertIn("- project_root: client-app", out)
        self.assertIn("- project_state: brownfield", out)
        self.assertIn("- default_branch: main", out)
        # Packages block.
        self.assertIn("### Packages (3 detected)", out)
        # Manifest column aligned: max path is "apps/web" (8 chars),
        # so col_width = 10. Each line: "- " + path + padding + manifest.
        self.assertIn("- .         package.json", out)
        self.assertIn("- scripts   package.json", out)
        self.assertIn("- apps/web  package.json", out)

    def test_empty_packages(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-workspace-mode", "standalone")
        _run_cli(self.devforge_dir, "set-project-root", ".")
        _run_cli(self.devforge_dir, "set-project-state", "empty")
        _run_cli(self.devforge_dir, "set-default-branch", "main")
        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn("### Packages (0 detected)", out)
        self.assertIn("- no packages detected", out)

    def test_default_state_renders_null_scalars(self):
        # After reset only — all 4 scalars are None, 0 packages.
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn("- workspace_mode: null", out)
        self.assertIn("- project_root: null", out)
        self.assertIn("- project_state: null", out)
        self.assertIn("- default_branch: null", out)
        self.assertIn("### Packages (0 detected)", out)
        self.assertIn("- no packages detected", out)

    def test_26_packages_all_present(self):
        # Mirrors the testForge20 monorepo scenario. All paths must
        # appear in output and the count line must be correct.
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-workspace-mode", "wrapper")
        _run_cli(self.devforge_dir, "set-project-root", "module")
        _run_cli(self.devforge_dir, "set-project-state", "brownfield")
        _run_cli(self.devforge_dir, "set-default-branch", "dev")
        paths = [".", "scripts"] + [
            "packages/pkg-{0:02d}".format(i) for i in range(23)
        ] + ["apps/app-web"]
        self.assertEqual(len(paths), 26)
        for p in paths:
            _run_cli(
                self.devforge_dir,
                "add-package",
                "--path", p,
                "--manifest", "package.json",
            )
        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn("### Packages (26 detected)", out)
        for p in paths:
            self.assertIn(p, out)

    def test_long_path_column_alignment(self):
        # Paths of varying lengths should align manifests in one column.
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-workspace-mode", "wrapper")
        _run_cli(self.devforge_dir, "set-project-root", "root")
        _run_cli(self.devforge_dir, "set-project-state", "brownfield")
        _run_cli(self.devforge_dir, "set-default-branch", "main")
        _run_cli(
            self.devforge_dir,
            "add-package", "--path", ".",
            "--manifest", "package.json",
        )
        _run_cli(
            self.devforge_dir,
            "add-package", "--path", "packages/very-long-package-name",
            "--manifest", "package.json",
        )
        _run_cli(
            self.devforge_dir,
            "add-package", "--path", "apps/web",
            "--manifest", "package.json",
        )
        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        # Find each package line and confirm "package.json" starts at
        # the same column index across all 3.
        pkg_lines = [
            line for line in out.splitlines()
            if line.startswith("- ") and line.endswith("package.json")
            and "Packages" not in line
        ]
        self.assertEqual(len(pkg_lines), 3)
        manifest_columns = [line.index("package.json") for line in pkg_lines]
        self.assertEqual(len(set(manifest_columns)), 1,
                         "manifest column not aligned: {0}".format(manifest_columns))

    def test_missing_file_errors_with_helpful_stderr(self):
        # No reset — init.yaml absent.
        self.assertFalse(self.output_file.exists())
        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"init.yaml not found", proc.stderr)
        self.assertIn(str(self.output_file).encode("utf-8"), proc.stderr)

    def test_summary_malformed_yaml_returns_error_with_helpful_stderr(self):
        # Hand-write a malformed init.yaml (bypasses the emitter on
        # purpose) and confirm cmd_summary surfaces a parse error
        # rather than crashing or producing partial output.
        self.output_file.write_text("bogus: [unclosed\n", encoding="utf-8")
        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"cannot parse", proc.stderr)
        self.assertIn(str(self.output_file).encode("utf-8"), proc.stderr)

    def test_output_ends_with_single_newline(self):
        self._populate_three_packages()
        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertTrue(out.endswith("\n"))
        self.assertFalse(out.endswith("\n\n"),
                         "output ends with multiple trailing newlines")

    def test_field_order_locked_against_dict_shuffle(self):
        # Build a state dict in a deliberately shuffled order; the
        # renderer must still emit fields in SUMMARY_WORKSPACE_FIELDS
        # order (not insertion order).
        shuffled = {}
        shuffled["packages_detected"] = []
        shuffled["default_branch"] = "main"
        shuffled["project_state"] = "brownfield"
        shuffled["workspace_mode"] = "wrapper"
        shuffled["project_root"] = "client-app"
        out = init_helper._render_summary(shuffled)
        # Find the index of each field's row in the rendered output.
        lines = out.splitlines()
        idx = {field: None for field in init_helper.SUMMARY_WORKSPACE_FIELDS}
        for i, line in enumerate(lines):
            for field in idx:
                if line.startswith("- {0}:".format(field)):
                    idx[field] = i
        # All fields must appear, and in locked order.
        order = [idx[f] for f in init_helper.SUMMARY_WORKSPACE_FIELDS]
        self.assertEqual(order, sorted(order),
                         "fields not in locked order: {0}".format(idx))
        self.assertEqual(
            order,
            [order[0] + i for i in range(len(order))],
            "fields not contiguous in render: {0}".format(idx),
        )

    def test_render_summary_pure_function(self):
        # Direct unit test on the pure renderer (no subprocess, no file I/O).
        state = {
            "workspace_mode": "standalone",
            "project_root": ".",
            "project_state": "empty",
            "default_branch": "main",
            "packages_detected": [
                {"path": ".", "manifest": "package.json"},
            ],
        }
        out = init_helper._render_summary(state)
        expected = (
            "## Init Report\n"
            "\n"
            "### Workspace\n"
            "- workspace_mode: standalone\n"
            "- project_root: .\n"
            "- project_state: empty\n"
            "- default_branch: main\n"
            "\n"
            "### Packages (1 detected)\n"
            "- .  package.json\n"
        )
        self.assertEqual(out, expected)

    def test_no_leading_blank_line(self):
        self._populate_three_packages()
        proc = _run_cli(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertTrue(out.startswith("## Init Report"),
                        "output should start with header, no leading blank line")


# ---------------------------------------------------------------------------
# VerifyTests
# ---------------------------------------------------------------------------


class VerifyTests(unittest.TestCase):
    """verify subcommand — state-integrity gate for /init-forge.

    Setup mirrors FindNestedGitTests: DEVFORGE_DIR is a child of the
    install_root so `_output_file_path().parent.parent` resolves to a
    stable temp directory. Real setter helpers build the YAML (real-producer
    pattern); hand-authored YAML is used only for failure-injection cases
    that the setters cannot produce (e.g. empty field, invalid enum).
    """

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.install_root = Path(self._tmp.name)
        # DEVFORGE_DIR must be a child of install_root so the verify
        # handler resolves project_root relative to install_root correctly.
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir()
        self.output_file = self.devforge_dir / init_helper.OUTPUT_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    # --- helpers ---

    def _populate_valid_state(self, project_root_rel="."):
        """Build a fully-valid init.yaml via real setters.

        project_root_rel should be a relative path that actually exists
        under self.install_root (the caller is responsible for creating it).
        """
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-workspace-mode", "standalone")
        _run_cli(self.devforge_dir, "set-project-root", project_root_rel)
        _run_cli(self.devforge_dir, "set-project-state", "empty")
        _run_cli(self.devforge_dir, "set-default-branch", "main")
        # packages_detected stays [] — valid per schema

    def _write_yaml(self, text):
        """Directly write hand-authored YAML to the output file."""
        self.output_file.write_text(text, encoding="utf-8")

    def _make_index_artifacts(self):
        """Create the two index artifacts that Step 6 produces."""
        index_json = self.devforge_dir / "index.json"
        index_json.write_text("{}", encoding="utf-8")
        docs_dir = self.install_root / "docs"
        docs_dir.mkdir(exist_ok=True)
        (docs_dir / "structure.md").write_text("# Structure\n", encoding="utf-8")

    # --- test cases ---

    def test_verify_happy_path(self):
        """All fields valid, both index artifacts present → exit 0, no stderr."""
        self._populate_valid_state(project_root_rel=".")
        self._make_index_artifacts()
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
        self.assertEqual(proc.stderr, b"")

    def test_verify_missing_workspace_mode(self):
        """workspace_mode empty → exit 2, stderr names the field."""
        self._populate_valid_state()
        self._make_index_artifacts()
        # Inject empty workspace_mode by hand-writing YAML (setters reject empty).
        self._write_yaml(
            "workspace_mode: null\n"
            "project_root: .\n"
            "project_state: empty\n"
            "default_branch: main\n"
            "packages_detected: []\n"
        )
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"workspace_mode", proc.stderr)

    def test_verify_invalid_workspace_mode(self):
        """workspace_mode set to an invalid value → exit 2, stderr names the field."""
        self._populate_valid_state()
        self._make_index_artifacts()
        self._write_yaml(
            "workspace_mode: garbage\n"
            "project_root: .\n"
            "project_state: empty\n"
            "default_branch: main\n"
            "packages_detected: []\n"
        )
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"workspace_mode", proc.stderr)

    def test_verify_project_root_does_not_exist(self):
        """project_root points at a path that doesn't exist → exit 2, stderr names it."""
        self._populate_valid_state()
        self._make_index_artifacts()
        self._write_yaml(
            "workspace_mode: standalone\n"
            "project_root: nonexistent-dir-xyz\n"
            "project_state: empty\n"
            "default_branch: main\n"
            "packages_detected: []\n"
        )
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"project_root", proc.stderr)

    def test_verify_missing_default_branch(self):
        """default_branch null → exit 2, stderr names the field."""
        self._populate_valid_state()
        self._make_index_artifacts()
        self._write_yaml(
            "workspace_mode: standalone\n"
            "project_root: .\n"
            "project_state: empty\n"
            "default_branch: null\n"
            "packages_detected: []\n"
        )
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"default_branch", proc.stderr)

    def test_verify_packages_detected_empty_but_manifest_found(self):
        """packages_detected [] but a manifest exists at depth ≤2 → exit 2."""
        # project_root = "." means install_root; place a manifest at depth 2.
        self._populate_valid_state(project_root_rel=".")
        self._make_index_artifacts()
        # packages_detected is already [] from _populate_valid_state.
        # Create a package.json at depth 2 (foo/package.json).
        sub = self.install_root / "foo"
        sub.mkdir()
        (sub / "package.json").write_text('{"name": "foo"}', encoding="utf-8")
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"packages_detected", proc.stderr)

    def test_verify_missing_index_json(self):
        """.devforge/index.json absent → exit 2."""
        self._populate_valid_state()
        # Only create structure.md; leave index.json absent.
        docs_dir = self.install_root / "docs"
        docs_dir.mkdir(exist_ok=True)
        (docs_dir / "structure.md").write_text("# Structure\n", encoding="utf-8")
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"index.json", proc.stderr)

    def test_verify_missing_structure_md(self):
        """docs/structure.md absent → exit 2."""
        self._populate_valid_state()
        # Only create index.json; leave structure.md absent.
        (self.devforge_dir / "index.json").write_text("{}", encoding="utf-8")
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"structure.md", proc.stderr)

    def test_verify_missing_init_yaml(self):
        """init.yaml absent → exit 2 immediately with unreadable message."""
        # Don't call reset — no init.yaml at all.
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"init.yaml", proc.stderr)

    def test_verify_all_violations_enumerated(self):
        """Multiple violations in one run — all field names appear on stderr."""
        self._make_index_artifacts()
        self._write_yaml(
            "workspace_mode: null\n"
            "project_root: null\n"
            "project_state: null\n"
            "default_branch: null\n"
            "packages_detected: []\n"
        )
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        stderr = proc.stderr.decode("utf-8")
        for field in ("workspace_mode", "project_root", "project_state", "default_branch"):
            self.assertIn(field, stderr, "expected {0} in stderr".format(field))

    def test_verify_stderr_format(self):
        """Each violation line must start with 'verify: '."""
        self._make_index_artifacts()
        self._write_yaml(
            "workspace_mode: null\n"
            "project_root: .\n"
            "project_state: empty\n"
            "default_branch: main\n"
            "packages_detected: []\n"
        )
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        lines = proc.stderr.decode("utf-8").strip().splitlines()
        for line in lines:
            self.assertTrue(
                line.startswith("verify: "),
                "violation line does not start with 'verify: ': {0!r}".format(line),
            )

    def test_verify_is_readonly(self):
        """verify must not mutate init.yaml."""
        self._populate_valid_state()
        self._make_index_artifacts()
        before = self.output_file.read_bytes()
        _run_cli(self.devforge_dir, "verify")
        after = self.output_file.read_bytes()
        self.assertEqual(before, after)

    def test_verify_subcommand_listed_in_help(self):
        """'verify' must appear in the top-level --help output."""
        proc = _run_cli(self.devforge_dir, "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(b"verify", proc.stdout)

    def test_verify_manifest_at_depth_1_triggers_anticorruption(self):
        """A manifest directly under project_root (depth 1) also triggers violation."""
        self._populate_valid_state(project_root_rel=".")
        self._make_index_artifacts()
        # Place manifest directly under install_root (depth 1).
        (self.install_root / "package.json").write_text('{}', encoding="utf-8")
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"packages_detected", proc.stderr)

    def test_verify_manifest_at_depth_3_does_not_trigger(self):
        """A manifest deeper than depth 2 must NOT trigger the anti-corruption check."""
        self._populate_valid_state(project_root_rel=".")
        self._make_index_artifacts()
        # Place manifest at depth 3 (a/b/package.json) — beyond the scan limit.
        deep = self.install_root / "a" / "b"
        deep.mkdir(parents=True)
        (deep / "package.json").write_text('{}', encoding="utf-8")
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))

    def test_verify_packages_detected_nonempty_with_manifest_passes(self):
        """packages_detected populated AND manifest found → no anti-corruption violation."""
        self._populate_valid_state(project_root_rel=".")
        self._make_index_artifacts()
        sub = self.install_root / "foo"
        sub.mkdir()
        (sub / "package.json").write_text('{}', encoding="utf-8")
        # Register the package so packages_detected is non-empty.
        _run_cli(self.devforge_dir, "add-package", "--path", "foo", "--manifest", "package.json")
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))

    def test_verify_invalid_project_state_enum(self):
        """project_state with invalid enum value → exit 2."""
        self._populate_valid_state()
        self._make_index_artifacts()
        self._write_yaml(
            "workspace_mode: standalone\n"
            "project_root: .\n"
            "project_state: legacy\n"
            "default_branch: main\n"
            "packages_detected: []\n"
        )
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"project_state", proc.stderr)


# ---------------------------------------------------------------------------
# TestDetectTestInfra — unit tests for _detect_test_infra walker.
# ---------------------------------------------------------------------------


class TestDetectTestInfra(unittest.TestCase):
    """Tests for the _detect_test_infra(project_root) pure walker.

    Each test constructs a minimal filesystem layout in a temp dir and
    calls the function directly (no subprocess) to verify detection logic.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, rel_path, content):
        """Write a file at root/rel_path, creating parent dirs as needed."""
        target = self.root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    # --- 1: JS vitest in devDependencies ---

    def test_detect_test_infra_js_vitest(self):
        self._write(
            "package.json",
            '{"devDependencies": {"vitest": "^1.0.0", "vite": "^4.0.0"}}',
        )
        result = init_helper._detect_test_infra(self.root)
        self.assertEqual(result["frontend"], "vitest")
        self.assertIsNone(result["backend"])
        self.assertIsNone(result["e2e"])
        self.assertEqual(result["status"], "partial")  # 1/3 buckets

    # --- 2: JS jest + playwright ---

    def test_detect_test_infra_js_jest_playwright(self):
        self._write(
            "package.json",
            '{"devDependencies": {"jest": "^29.0.0", "playwright": "^1.30.0"}}',
        )
        result = init_helper._detect_test_infra(self.root)
        self.assertEqual(result["frontend"], "jest")
        self.assertEqual(result["e2e"], "playwright")
        self.assertIsNone(result["backend"])
        self.assertEqual(result["status"], "partial")  # 2/3 buckets

    # --- 3: Python pyproject.toml with pytest ---

    def test_detect_test_infra_py_pytest(self):
        self._write(
            "pyproject.toml",
            "[tool.poetry.dev-dependencies]\npytest = \"^7.0\"\n",
        )
        result = init_helper._detect_test_infra(self.root)
        self.assertEqual(result["backend"], "pytest")
        self.assertIsNone(result["frontend"])
        self.assertIsNone(result["e2e"])
        self.assertEqual(result["status"], "partial")

    # --- 4: Python requirements-dev.txt with pytest>=7 ---

    def test_detect_test_infra_py_requirements_pytest(self):
        self._write("requirements-dev.txt", "pytest>=7\nrequests>=2.28\n")
        result = init_helper._detect_test_infra(self.root)
        self.assertEqual(result["backend"], "pytest")

    # --- 5: Go *_test.go file ---

    def test_detect_test_infra_go(self):
        self._write("pkg/foo_test.go", "package foo\n\nfunc TestFoo(t *testing.T) {}\n")
        result = init_helper._detect_test_infra(self.root)
        self.assertEqual(result["backend"], "go-test")
        self.assertEqual(result["status"], "partial")

    # --- 6: Rust #[cfg(test)] in src/lib.rs ---

    def test_detect_test_infra_rust(self):
        self._write(
            "src/lib.rs",
            "#[cfg(test)]\nmod tests {\n    #[test]\n    fn it_works() {}\n}\n",
        )
        result = init_helper._detect_test_infra(self.root)
        self.assertEqual(result["backend"], "cargo-test")
        self.assertEqual(result["status"], "partial")

    # --- F2a: pyproject.toml skips comment lines mentioning pytest ---

    def test_detect_python_skips_pytest_in_comment(self):
        """pyproject.toml with pytest only in a comment → backend=None."""
        self._write(
            "pyproject.toml",
            "# pytest mentioned but not used\n[tool.poetry]\nname = \"myapp\"\n",
        )
        result = init_helper._detect_test_infra(self.root)
        self.assertIsNone(result["backend"])

    # --- F2b: pyproject.toml skips pytest_plugin identifier (boundary check) ---

    def test_detect_python_skips_pytest_substring_in_other_identifier(self):
        """pytest_plugin starts with 'pytest' but next char is '_' → no match."""
        self._write(
            "pyproject.toml",
            "[tool.poetry.dev-dependencies]\npytest_plugin = \"1.0\"\n",
        )
        result = init_helper._detect_test_infra(self.root)
        self.assertIsNone(result["backend"])

    # --- F3: Rust skips #[cfg(test)] in // comment lines ---

    def test_detect_rust_skips_cfg_test_in_comment(self):
        """src/lib.rs with #[cfg(test)] only in // comments → backend=None."""
        self._write(
            "src/lib.rs",
            "// #[cfg(test)]\n// mod tests {}\n\npub fn add(a: i32, b: i32) -> i32 { a + b }\n",
        )
        result = init_helper._detect_test_infra(self.root)
        self.assertIsNone(result["backend"])

    # --- 7: Ruby Gemfile with rspec ---

    def test_detect_test_infra_ruby(self):
        self._write("Gemfile", "source 'https://rubygems.org'\ngem 'rspec', '~> 3.0'\n")
        result = init_helper._detect_test_infra(self.root)
        self.assertEqual(result["backend"], "rspec")
        self.assertEqual(result["status"], "partial")

    # --- 8: Empty project (bare tempdir) ---

    def test_detect_test_infra_empty_project(self):
        result = init_helper._detect_test_infra(self.root)
        self.assertIsNone(result["frontend"])
        self.assertIsNone(result["backend"])
        self.assertIsNone(result["e2e"])
        self.assertEqual(result["status"], "absent")

    # --- 9: Mixed monorepo (JS root + Python pyproject + e2e) ---

    def test_detect_test_infra_mixed_monorepo(self):
        # Root package.json for the monorepo with vitest.
        self._write(
            "package.json",
            '{"devDependencies": {"vitest": "^1.0.0", "playwright": "^1.30.0"}}',
        )
        # Python backend uses pytest.
        self._write(
            "pyproject.toml",
            "[tool.poetry.dev-dependencies]\npytest = \"^7.0\"\n",
        )
        result = init_helper._detect_test_infra(self.root)
        self.assertEqual(result["frontend"], "vitest")
        self.assertEqual(result["backend"], "pytest")
        self.assertEqual(result["e2e"], "playwright")
        self.assertEqual(result["status"], "present")  # all 3 buckets

    # --- 10: vitest inside node_modules MUST NOT be detected ---

    def test_detect_test_infra_skips_node_modules(self):
        # Place vitest only inside node_modules — must be ignored.
        self._write(
            "node_modules/foo/package.json",
            '{"devDependencies": {"vitest": "^1.0.0"}}',
        )
        result = init_helper._detect_test_infra(self.root)
        self.assertIsNone(result["frontend"])
        self.assertEqual(result["status"], "absent")

    # --- Extra edge cases ---

    def test_detect_test_infra_monorepo_packages_dir(self):
        """vitest in packages/app/package.json (depth 2) should be detected."""
        self._write(
            "packages/app/package.json",
            '{"devDependencies": {"vitest": "^1.0.0"}}',
        )
        result = init_helper._detect_test_infra(self.root)
        self.assertEqual(result["frontend"], "vitest")

    def test_detect_test_infra_first_match_wins_per_bucket(self):
        """vitest takes priority over jest (bucket=frontend, vitest listed first)."""
        self._write(
            "package.json",
            '{"devDependencies": {"jest": "^29.0.0", "vitest": "^1.0.0"}}',
        )
        result = init_helper._detect_test_infra(self.root)
        # _TEST_INFRA_BUCKETS iteration order: vitest before jest → vitest wins.
        self.assertEqual(result["frontend"], "vitest")

    def test_detect_test_infra_rust_inside_src_subdir(self):
        """#[cfg(test)] in src/submod/tests.rs (depth 2 from src/) is detected."""
        self._write(
            "src/submod/tests.rs",
            "#[cfg(test)]\nmod tests {}\n",
        )
        result = init_helper._detect_test_infra(self.root)
        self.assertEqual(result["backend"], "cargo-test")

    def test_detect_test_infra_go_depth_cap(self):
        """*_test.go at depth 4 should NOT be detected (cap is depth 3)."""
        self._write(
            "a/b/c/d/foo_test.go",
            "package d\n",
        )
        result = init_helper._detect_test_infra(self.root)
        # a(1) / b(2) / c(3) / d(4) — depth 4 is beyond the cap.
        self.assertIsNone(result["backend"])

    def test_detect_test_infra_malformed_package_json_skipped(self):
        """A malformed package.json must be skipped without aborting detection."""
        self._write("package.json", "this is not json{{{")
        result = init_helper._detect_test_infra(self.root)
        self.assertEqual(result["status"], "absent")

    def test_detect_test_infra_requirements_txt_line_boundary(self):
        """'pytestification' must NOT trigger 'pytest' detection (prefix-match boundary)."""
        self._write("requirements.txt", "pytestification>=1.0\n")
        result = init_helper._detect_test_infra(self.root)
        self.assertIsNone(result["backend"])


# ---------------------------------------------------------------------------
# TestSetTestInfra — CLI subcommand tests.
# ---------------------------------------------------------------------------


class TestSetTestInfra(_EnvIsolationMixin, unittest.TestCase):
    """Tests for the set-test-infra subcommand."""

    # --- 11: set-test-infra round-trip via init.yaml ---

    def test_set_test_infra_override_writes_yaml(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-test-infra",
            "--frontend", "vitest",
            "--backend", "pytest",
            "--e2e", "playwright",
            "--status", "present",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        ti = state["test_infra"]
        self.assertEqual(ti["frontend"], "vitest")
        self.assertEqual(ti["backend"], "pytest")
        self.assertEqual(ti["e2e"], "playwright")
        self.assertEqual(ti["status"], "present")

    # --- 12: set-test-infra rejects wrong-bucket framework ---

    def test_set_test_infra_rejects_framework_bucket_mismatch(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-test-infra",
            "--frontend", "pytest",   # pytest is backend, not frontend
            "--backend", "null",
            "--e2e", "null",
            "--status", "absent",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"pytest", proc.stderr)
        # New: error names both the framework's actual bucket and the rejected bucket.
        self.assertIn(b"backend", proc.stderr)
        self.assertIn(b"frontend", proc.stderr)

    # --- 13: set-test-infra rejects invalid status ---

    def test_set_test_infra_rejects_invalid_status(self):
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-test-infra",
            "--frontend", "null",
            "--backend", "null",
            "--e2e", "null",
            "--status", "maybe",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"maybe", proc.stderr)

    def test_set_test_infra_accepts_null_for_all_frameworks(self):
        """All frameworks set to null with status=absent is valid."""
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-test-infra",
            "--frontend", "null",
            "--backend", "null",
            "--e2e", "null",
            "--status", "absent",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        ti = state["test_infra"]
        self.assertIsNone(ti["frontend"])
        self.assertIsNone(ti["backend"])
        self.assertIsNone(ti["e2e"])
        self.assertEqual(ti["status"], "absent")

    def test_set_test_infra_rejects_e2e_framework_as_backend(self):
        """cypress is an e2e framework, not backend."""
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "set-test-infra",
            "--frontend", "null",
            "--backend", "cypress",
            "--e2e", "null",
            "--status", "absent",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"cypress", proc.stderr)


# ---------------------------------------------------------------------------
# TestTestInfraYamlRoundTrip — YAML emit+parse round-trip for test_infra.
# ---------------------------------------------------------------------------


class TestTestInfraYamlRoundTrip(unittest.TestCase):
    """YAML round-trip tests specific to the test_infra_record kind."""

    # --- 14: emit_yaml + parse_yaml preserves test_infra block ---

    def test_test_infra_yaml_round_trip(self):
        state = init_helper.default_state()
        state["test_infra"] = {
            "frontend": "jest",
            "backend": "pytest",
            "e2e": "cypress",
            "status": "present",
        }
        text = init_helper.emit_yaml(state)
        state2 = init_helper.parse_yaml(text)
        self.assertEqual(state["test_infra"], state2["test_infra"])

    def test_test_infra_yaml_round_trip_all_null(self):
        state = init_helper.default_state()
        # Defaults: all None except status=absent.
        text = init_helper.emit_yaml(state)
        state2 = init_helper.parse_yaml(text)
        self.assertEqual(state["test_infra"], state2["test_infra"])
        self.assertIsNone(state2["test_infra"]["frontend"])
        self.assertEqual(state2["test_infra"]["status"], "absent")

    def test_test_infra_emit_block_format(self):
        """test_infra block must use 2-space indent, no dash prefix."""
        state = init_helper.default_state()
        state["test_infra"] = {
            "frontend": "vitest",
            "backend": None,
            "e2e": None,
            "status": "partial",
        }
        text = init_helper.emit_yaml(state)
        self.assertIn("test_infra:\n", text)
        self.assertIn("  frontend: vitest\n", text)
        self.assertIn("  backend: null\n", text)
        self.assertIn("  status: partial\n", text)

    # --- 15: legacy init.yaml (no test_infra key) loads with default injected ---

    def test_legacy_init_yaml_loads_with_default_test_infra(self):
        """Old-shape yaml without test_infra key → _load_state injects default."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge_dir = Path(tmp)
            init_yaml = devforge_dir / init_helper.OUTPUT_FILE_NAME
            # Write old-shape YAML without test_infra.
            init_yaml.write_text(
                "workspace_mode: standalone\n"
                "project_root: .\n"
                "project_state: brownfield\n"
                "default_branch: main\n"
                "packages_detected: []\n",
                encoding="utf-8",
            )
            saved = os.environ.get("DEVFORGE_DIR")
            os.environ["DEVFORGE_DIR"] = str(devforge_dir)
            try:
                state = init_helper._load_state()
            finally:
                if saved is None:
                    os.environ.pop("DEVFORGE_DIR", None)
                else:
                    os.environ["DEVFORGE_DIR"] = saved

            # Default test_infra must be injected.
            self.assertIn("test_infra", state)
            ti = state["test_infra"]
            self.assertIsNone(ti["frontend"])
            self.assertIsNone(ti["backend"])
            self.assertIsNone(ti["e2e"])
            self.assertEqual(ti["status"], "absent")


# ---------------------------------------------------------------------------
# TestVerifyTestInfra — soft-warning and hard-fail integration with cmd_verify.
# ---------------------------------------------------------------------------


class TestVerifyTestInfra(unittest.TestCase):
    """Tests for the test_infra check added to cmd_verify.

    These tests extend the existing VerifyTests fixture pattern:
    DEVFORGE_DIR is a child of install_root.
    """

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.install_root = Path(self._tmp.name)
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir()
        self.output_file = self.devforge_dir / init_helper.OUTPUT_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def _make_index_artifacts(self):
        index_json = self.devforge_dir / "index.json"
        index_json.write_text("{}", encoding="utf-8")
        docs_dir = self.install_root / "docs"
        docs_dir.mkdir(exist_ok=True)
        (docs_dir / "structure.md").write_text("# Structure\n", encoding="utf-8")

    def _build_valid_state(self, project_root_rel="."):
        """Write a fully-valid init.yaml via real setters."""
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "set-workspace-mode", "standalone")
        _run_cli(self.devforge_dir, "set-project-root", project_root_rel)
        _run_cli(self.devforge_dir, "set-project-state", "empty")
        _run_cli(self.devforge_dir, "set-default-branch", "main")

    # --- 16: soft-warns when test_infra.status=absent but detector finds something ---

    def test_verify_soft_warns_when_packages_present_test_infra_absent_and_detected(self):
        """Fixture: packages_detected populated + test_infra absent + vitest on disk
        → exit 0 + stderr contains WARN: test_infra."""
        self._build_valid_state(project_root_rel=".")
        self._make_index_artifacts()
        # Add a package so packages_detected is non-empty.
        _run_cli(
            self.devforge_dir,
            "add-package", "--path", ".", "--manifest", "package.json",
        )
        # Ensure test_infra is absent (reset writes absent by default).
        # Place vitest package.json at project_root (=install_root=`.`).
        (self.install_root / "package.json").write_text(
            '{"devDependencies": {"vitest": "^1.0.0"}}',
            encoding="utf-8",
        )
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
        stderr = proc.stderr.decode("utf-8")
        self.assertIn("WARN: test_infra", stderr)

    # --- 17: no warn when test_infra already populated ---

    def test_verify_no_warn_when_test_infra_already_populated(self):
        """When test_infra is populated, no WARN line is emitted."""
        self._build_valid_state(project_root_rel=".")
        self._make_index_artifacts()
        # Place vitest package.json on disk at install_root so the
        # packages_detected scanner also sees it — register it so no
        # packages_detected violation fires.
        (self.install_root / "package.json").write_text(
            '{"devDependencies": {"vitest": "^1.0.0"}}',
            encoding="utf-8",
        )
        _run_cli(
            self.devforge_dir,
            "add-package", "--path", ".", "--manifest", "package.json",
        )
        # Override test_infra to populated state.
        _run_cli(
            self.devforge_dir,
            "set-test-infra",
            "--frontend", "vitest",
            "--backend", "null",
            "--e2e", "null",
            "--status", "partial",
        )
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
        stderr = proc.stderr.decode("utf-8")
        self.assertNotIn("WARN: test_infra", stderr)

    # --- 18: no warn when no detection hit ---

    def test_verify_no_warn_when_no_detection_hit(self):
        """packages_detected populated but no test files on disk → exit 0, no WARN."""
        self._build_valid_state(project_root_rel=".")
        self._make_index_artifacts()
        _run_cli(
            self.devforge_dir,
            "add-package", "--path", ".", "--manifest", "package.json",
        )
        # No test framework files at all in the temp dir.
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
        self.assertNotIn(b"WARN: test_infra", proc.stderr)

    def test_verify_existing_happy_path_still_passes_after_test_infra_extension(self):
        """Regression: existing happy-path with test_infra.status=absent,
        no detection hit → exit 0, empty stderr (no warnings, no violations)."""
        self._build_valid_state(project_root_rel=".")
        self._make_index_artifacts()
        # No test files in temp dir.
        proc = _run_cli(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
        self.assertEqual(proc.stderr, b"")


# ---------------------------------------------------------------------------
# TestDetectTestInfraCLI — CLI subcommand round-trip for detect-test-infra.
# ---------------------------------------------------------------------------


class TestDetectTestInfraCLI(_EnvIsolationMixin, unittest.TestCase):
    """CLI-level tests for the detect-test-infra subcommand."""

    def setUp(self):
        super().setUp()
        # Set up install_root layout so DEVFORGE_DIR is a child.
        self._tmp2 = tempfile.TemporaryDirectory()
        self.install_root = Path(self._tmp2.name)
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir()
        self.output_file = self.devforge_dir / init_helper.OUTPUT_FILE_NAME

    def tearDown(self):
        self._tmp2.cleanup()
        super().tearDown()

    def test_detect_test_infra_cli_writes_json_to_stdout(self):
        """detect-test-infra echoes compact JSON to stdout."""
        # Project root = a subdirectory with vitest.
        project_root = self.install_root / "app"
        project_root.mkdir()
        (project_root / "package.json").write_text(
            '{"devDependencies": {"vitest": "^1.0.0"}}',
            encoding="utf-8",
        )
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "detect-test-infra",
            "--project-root", str(project_root),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Stdout must be valid JSON.
        out = json.loads(proc.stdout.decode("utf-8").strip())
        self.assertEqual(out["frontend"], "vitest")
        self.assertEqual(out["status"], "partial")

    def test_detect_test_infra_cli_writes_to_init_yaml(self):
        """detect-test-infra updates test_infra in init.yaml."""
        project_root = self.install_root / "app"
        project_root.mkdir()
        (project_root / "package.json").write_text(
            '{"devDependencies": {"playwright": "^1.30.0"}}',
            encoding="utf-8",
        )
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "detect-test-infra",
            "--project-root", str(project_root),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = init_helper.parse_yaml(
            self.output_file.read_text(encoding="utf-8")
        )
        self.assertEqual(state["test_infra"]["e2e"], "playwright")

    def test_detect_test_infra_cli_missing_project_root_exits_2(self):
        """--project-root pointing at a non-existent dir → exit 2."""
        _run_cli(self.devforge_dir, "reset")
        proc = _run_cli(
            self.devforge_dir,
            "detect-test-infra",
            "--project-root", "/nonexistent/path/xyz123",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"does not exist", proc.stderr)


if __name__ == "__main__":
    unittest.main()
