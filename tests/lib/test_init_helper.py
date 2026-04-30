"""Tests for src/devforge/lib/init_helper.py.

Covers the closed-shape yaml emitter+parser, all 7 subcommands, set-time
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

    def test_help_lists_seven_subcommands(self):
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


if __name__ == "__main__":
    unittest.main()
