"""Tests for src/devforge/lib/generate_docs_helper.py (sub-step 1.2a).

Scope: state persistence + per-field setters + status +
extract-package-scripts. Sub-step 1.2b's render/validate subcommands have
their own test additions in a separate change.

Each test runs in its own `tempfile.TemporaryDirectory` and points the
helper at it via `DEVFORGE_DIR`. Pure-function tests import the module
directly. End-to-end CLI tests invoke the .py file as a subprocess so
the real argparse + dispatch path is exercised. Round-trip tests build
state via the real CLI before reading it back, so the on-disk JSON is
always produced by the helper itself (no hand-authored state fixtures).

Stdlib only.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "generate_docs_helper.py"
_LAUNCHER = _LIB_DIR / "generate_docs_helper"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import generate_docs_helper as gdh  # noqa: E402


def _run_cli(devforge_dir, *args, project_root=None, cwd=None):
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    if project_root is not None:
        env["DEVFORGE_PROJECT_ROOT"] = str(project_root)
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(args),
        env=env,
        cwd=str(cwd) if cwd is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_launcher(devforge_dir, *args):
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        ["sh", str(_LAUNCHER)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class _EnvIsolationMixin:

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name)
        self.state_file = self.devforge_dir / gdh.STATE_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def _read_state(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# StateFilePathTests
# ---------------------------------------------------------------------------


class StateFilePathTests(unittest.TestCase):

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
            path = gdh._state_file_path()
            self.assertEqual(path, Path(tmp) / gdh.STATE_FILE_NAME)

    def test_default_path_under_helper_parent(self):
        path = gdh._state_file_path()
        expected = Path(gdh.__file__).resolve().parent.parent / gdh.STATE_FILE_NAME
        self.assertEqual(path, expected)

    def test_state_file_distinct_from_onboard(self):
        # The onboard helper uses `.onboard-state.json`; ours must differ.
        self.assertNotEqual(gdh.STATE_FILE_NAME, ".onboard-state.json")
        self.assertEqual(gdh.STATE_FILE_NAME, ".generate-docs-state.json")


# ---------------------------------------------------------------------------
# DefaultStateTests
# ---------------------------------------------------------------------------


class DefaultStateTests(unittest.TestCase):

    def test_default_state_shape(self):
        s = gdh.default_state()
        self.assertEqual(s, {"version": 1, "packages": {}})

    def test_default_package_record_initializes_all_fields(self):
        rec = gdh.default_package_record("foo", "apps/foo")
        self.assertEqual(rec["name"], "foo")
        self.assertEqual(rec["path"], "apps/foo")
        self.assertIsNone(rec["overview"])
        self.assertIsNone(rec["directory_tree"])
        self.assertIsNone(rec["primary_language"])
        self.assertIsNone(rec["framework"])
        self.assertIsNone(rec["build_tool"])
        self.assertEqual(rec["scripts"], {})
        self.assertEqual(rec["exports"], [])
        self.assertEqual(rec["dependencies"], [])
        self.assertEqual(rec["hazards"], [])
        self.assertIsNone(rec["usage_example"])
        self.assertIsNone(rec["consumer_pattern"])
        self.assertEqual(rec["concerns"], {})


# ---------------------------------------------------------------------------
# ValidatorTests (pure functions, no I/O)
# ---------------------------------------------------------------------------


class ValidatorTests(unittest.TestCase):

    def test_validate_string_rejects_empty(self):
        with self.assertRaises(ValueError):
            gdh._validate_string("", "f")

    def test_validate_string_rejects_whitespace_only(self):
        with self.assertRaises(ValueError):
            gdh._validate_string("   ", "f")

    def test_validate_string_rejects_non_str(self):
        with self.assertRaises(ValueError):
            gdh._validate_string(42, "f")

    def test_validate_string_rejects_newline_singleline(self):
        with self.assertRaises(ValueError):
            gdh._validate_string("ab\ncd", "f", multiline=False)

    def test_validate_string_rejects_tab_singleline(self):
        with self.assertRaises(ValueError):
            gdh._validate_string("ab\tcd", "f", multiline=False)

    def test_validate_string_rejects_cr_singleline(self):
        with self.assertRaises(ValueError):
            gdh._validate_string("ab\rcd", "f", multiline=False)

    def test_validate_string_rejects_null_byte(self):
        with self.assertRaises(ValueError):
            gdh._validate_string("ab\x00cd", "f", multiline=False)
        with self.assertRaises(ValueError):
            gdh._validate_string("ab\x00cd", "f", multiline=True)

    def test_validate_string_rejects_del_byte(self):
        with self.assertRaises(ValueError):
            gdh._validate_string("ab\x7fcd", "f", multiline=True)

    def test_validate_string_accepts_newline_multiline(self):
        # Multi-line fields permit \n, \r, \t.
        gdh._validate_string("line1\nline2", "f", multiline=True)
        gdh._validate_string("line1\r\nline2", "f", multiline=True)
        gdh._validate_string("col1\tcol2", "f", multiline=True)

    def test_validate_optional_string_treats_empty_as_none(self):
        self.assertIsNone(gdh._validate_optional_string("", "f"))
        self.assertIsNone(gdh._validate_optional_string(None, "f"))

    def test_validate_optional_string_passes_valid(self):
        self.assertEqual(gdh._validate_optional_string("ok", "f"), "ok")

    def test_validate_in_enum_accepts_member(self):
        gdh._validate_in_enum("function", gdh.EXPORT_KINDS, "f")

    def test_validate_in_enum_rejects_non_member(self):
        with self.assertRaises(ValueError):
            gdh._validate_in_enum("BOGUS", gdh.EXPORT_KINDS, "f")

    def test_validate_line_range_accepts_single_line(self):
        gdh._validate_line_range(1, 1, "cite")
        gdh._validate_line_range(5, 12, "cite")

    def test_validate_line_range_rejects_zero_start(self):
        with self.assertRaises(ValueError):
            gdh._validate_line_range(0, 5, "cite")

    def test_validate_line_range_rejects_end_lt_start(self):
        with self.assertRaises(ValueError):
            gdh._validate_line_range(5, 4, "cite")

    def test_validate_line_range_rejects_bool(self):
        # bool is a subclass of int; we explicitly reject it.
        with self.assertRaises(ValueError):
            gdh._validate_line_range(True, 5, "cite")


# ---------------------------------------------------------------------------
# ResetTests
# ---------------------------------------------------------------------------


class ResetTests(_EnvIsolationMixin, unittest.TestCase):

    def test_reset_when_absent_succeeds(self):
        self.assertFalse(self.state_file.exists())
        proc = _run_cli(self.devforge_dir, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_reset_creates_devforge_dir_when_absent(self):
        nested = self.devforge_dir / "deeper"
        proc = _run_cli(nested, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Reset only deletes a present file; it doesn't create one.
        # But the parent dir is mkdir'd defensively.
        self.assertTrue(nested.exists())

    def test_reset_after_populated_state_clears_it(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")
        self.assertTrue(self.state_file.exists())
        proc = _run_cli(self.devforge_dir, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_reset_is_idempotent(self):
        _run_cli(self.devforge_dir, "reset")
        _run_cli(self.devforge_dir, "reset")
        # No file should exist; both calls succeed.
        self.assertFalse(self.state_file.exists())


# ---------------------------------------------------------------------------
# AddPackageTests
# ---------------------------------------------------------------------------


class AddPackageTests(_EnvIsolationMixin, unittest.TestCase):

    def test_happy_path(self):
        proc = _run_cli(
            self.devforge_dir, "add-package",
            "--path", "apps/web", "--name", "web",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(state["version"], 1)
        self.assertIn("apps/web", state["packages"])
        self.assertEqual(state["packages"]["apps/web"]["name"], "web")
        self.assertEqual(state["packages"]["apps/web"]["path"], "apps/web")

    def test_empty_path_rejected(self):
        proc = _run_cli(
            self.devforge_dir, "add-package",
            "--path", "", "--name", "web",
        )
        self.assertEqual(proc.returncode, 2)

    def test_empty_name_rejected(self):
        proc = _run_cli(
            self.devforge_dir, "add-package",
            "--path", "apps/web", "--name", "",
        )
        self.assertEqual(proc.returncode, 2)

    def test_newline_in_path_rejected(self):
        proc = _run_cli(
            self.devforge_dir, "add-package",
            "--path", "apps\nweb", "--name", "web",
        )
        self.assertEqual(proc.returncode, 2)

    def test_duplicate_path_rejected(self):
        _run_cli(
            self.devforge_dir, "add-package",
            "--path", "apps/web", "--name", "web",
        )
        proc = _run_cli(
            self.devforge_dir, "add-package",
            "--path", "apps/web", "--name", "web",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"already registered", proc.stderr)

    def test_two_distinct_packages_coexist(self):
        _run_cli(
            self.devforge_dir, "add-package",
            "--path", "apps/web", "--name", "web",
        )
        _run_cli(
            self.devforge_dir, "add-package",
            "--path", "services/api", "--name", "api",
        )
        state = self._read_state()
        self.assertEqual(set(state["packages"].keys()),
                         {"apps/web", "services/api"})

    def test_missing_path_arg_errors(self):
        proc = _run_cli(self.devforge_dir, "add-package", "--name", "web")
        self.assertEqual(proc.returncode, 2)

    def test_missing_name_arg_errors(self):
        proc = _run_cli(self.devforge_dir, "add-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# SetScalarTests (overview / tree / language / framework / build_tool)
# ---------------------------------------------------------------------------


class SetScalarTests(_EnvIsolationMixin, unittest.TestCase):

    def _add_pkg(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")

    def test_set_overview_happy_path(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-overview",
            "--path", "apps/web", "--text", "A web app.",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages"]["apps/web"]["overview"],
            "A web app.",
        )

    def test_set_overview_accepts_multiline(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-overview",
            "--path", "apps/web", "--text", "Line 1\nLine 2\nLine 3",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(
            "Line 1\nLine 2",
            self._read_state()["packages"]["apps/web"]["overview"],
        )

    def test_set_overview_rejects_unregistered_package(self):
        proc = _run_cli(
            self.devforge_dir, "set-package-overview",
            "--path", "apps/web", "--text", "X",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"not registered", proc.stderr)

    def test_set_overview_rejects_empty_text(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-overview",
            "--path", "apps/web", "--text", "",
        )
        self.assertEqual(proc.returncode, 2)

    def test_set_overview_overwrites(self):
        self._add_pkg()
        _run_cli(self.devforge_dir, "set-package-overview",
                 "--path", "apps/web", "--text", "v1")
        _run_cli(self.devforge_dir, "set-package-overview",
                 "--path", "apps/web", "--text", "v2")
        self.assertEqual(
            self._read_state()["packages"]["apps/web"]["overview"], "v2"
        )

    def test_set_tree_happy_path(self):
        self._add_pkg()
        tree = "apps/web/\n  src/\n    index.ts\n  package.json"
        proc = _run_cli(
            self.devforge_dir, "set-package-tree",
            "--path", "apps/web", "--text", tree,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages"]["apps/web"]["directory_tree"], tree
        )

    def test_set_language_happy_path(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-language",
            "--path", "apps/web", "--value", "TypeScript",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages"]["apps/web"]["primary_language"],
            "TypeScript",
        )

    def test_set_language_rejects_newline(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-language",
            "--path", "apps/web", "--value", "TypeScript\nJavaScript",
        )
        self.assertEqual(proc.returncode, 2)

    def test_set_framework_happy_path(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-framework",
            "--path", "apps/web", "--value", "React",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages"]["apps/web"]["framework"], "React"
        )

    def test_set_framework_empty_clears_field(self):
        self._add_pkg()
        _run_cli(self.devforge_dir, "set-package-framework",
                 "--path", "apps/web", "--value", "React")
        proc = _run_cli(
            self.devforge_dir, "set-package-framework",
            "--path", "apps/web", "--value", "",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIsNone(
            self._read_state()["packages"]["apps/web"]["framework"]
        )

    def test_set_build_tool_happy_path(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-build-tool",
            "--path", "apps/web", "--value", "vite",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages"]["apps/web"]["build_tool"], "vite"
        )

    def test_set_build_tool_empty_clears_field(self):
        self._add_pkg()
        _run_cli(self.devforge_dir, "set-package-build-tool",
                 "--path", "apps/web", "--value", "vite")
        proc = _run_cli(
            self.devforge_dir, "set-package-build-tool",
            "--path", "apps/web", "--value", "",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIsNone(
            self._read_state()["packages"]["apps/web"]["build_tool"]
        )


# ---------------------------------------------------------------------------
# AddPackageScriptTests
# ---------------------------------------------------------------------------


class AddPackageScriptTests(_EnvIsolationMixin, unittest.TestCase):

    def _add_pkg(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")

    def test_happy_path(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-script",
            "--path", "apps/web",
            "--script-name", "build",
            "--command", "vite build",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state()["packages"]["apps/web"]["scripts"],
            {"build": "vite build"},
        )

    def test_two_scripts_coexist(self):
        self._add_pkg()
        _run_cli(self.devforge_dir, "add-package-script",
                 "--path", "apps/web", "--script-name", "build",
                 "--command", "vite build")
        _run_cli(self.devforge_dir, "add-package-script",
                 "--path", "apps/web", "--script-name", "test",
                 "--command", "vitest")
        scripts = self._read_state()["packages"]["apps/web"]["scripts"]
        self.assertEqual(scripts, {"build": "vite build", "test": "vitest"})

    def test_duplicate_script_name_rejected(self):
        self._add_pkg()
        _run_cli(self.devforge_dir, "add-package-script",
                 "--path", "apps/web", "--script-name", "build",
                 "--command", "vite build")
        proc = _run_cli(
            self.devforge_dir, "add-package-script",
            "--path", "apps/web", "--script-name", "build",
            "--command", "webpack",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"already registered", proc.stderr)

    def test_unregistered_package_rejected(self):
        proc = _run_cli(
            self.devforge_dir, "add-package-script",
            "--path", "apps/web", "--script-name", "build",
            "--command", "vite build",
        )
        self.assertEqual(proc.returncode, 2)

    def test_empty_script_name_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-script",
            "--path", "apps/web", "--script-name", "",
            "--command", "vite build",
        )
        self.assertEqual(proc.returncode, 2)

    def test_empty_command_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-script",
            "--path", "apps/web", "--script-name", "build",
            "--command", "",
        )
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# AddPackageExportTests
# ---------------------------------------------------------------------------


class AddPackageExportTests(_EnvIsolationMixin, unittest.TestCase):

    def _add_pkg(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")

    def _export_args(self, **overrides):
        defaults = {
            "--path": "apps/web",
            "--name": "fetchUser",
            "--kind": "function",
            "--signature": "fetchUser(id: string): Promise<User>",
            "--description": "Fetches a user by id.",
            "--language": "typescript",
            "--code-snippet": "export async function fetchUser(id) {}",
            "--cite-file": "src/api.ts",
            "--cite-start": "10",
            "--cite-end": "12",
        }
        defaults.update(overrides)
        flat = []
        for k, v in defaults.items():
            flat += [k, v]
        return flat

    def test_happy_path(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        exports = self._read_state()["packages"]["apps/web"]["exports"]
        self.assertEqual(len(exports), 1)
        self.assertEqual(exports[0]["name"], "fetchUser")
        self.assertEqual(exports[0]["kind"], "function")
        self.assertEqual(exports[0]["code"]["cite"]["file"], "src/api.ts")
        self.assertEqual(exports[0]["code"]["cite"]["start"], 10)
        self.assertEqual(exports[0]["code"]["cite"]["end"], 12)

    def test_signature_optional_empty_becomes_none(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(**{"--signature": ""}),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        exports = self._read_state()["packages"]["apps/web"]["exports"]
        self.assertIsNone(exports[0]["signature"])

    def test_invalid_kind_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(**{"--kind": "BOGUS"}),
        )
        self.assertEqual(proc.returncode, 2)

    def test_unregistered_package_rejected(self):
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(),
        )
        self.assertEqual(proc.returncode, 2)

    def test_zero_cite_start_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(**{"--cite-start": "0"}),
        )
        self.assertEqual(proc.returncode, 2)

    def test_end_before_start_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(**{"--cite-start": "10", "--cite-end": "5"}),
        )
        self.assertEqual(proc.returncode, 2)

    def test_duplicate_export_same_name_file_start_rejected(self):
        self._add_pkg()
        _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(),
        )
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(),
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"already registered", proc.stderr)

    def test_same_name_different_cite_allowed(self):
        # Overload-like cases: same export name in two files / two starts.
        self._add_pkg()
        _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(),
        )
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(**{
                "--cite-file": "src/api2.ts",
                "--cite-start": "5",
                "--cite-end": "8",
            }),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            len(self._read_state()["packages"]["apps/web"]["exports"]), 2
        )

    def test_empty_description_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(**{"--description": ""}),
        )
        self.assertEqual(proc.returncode, 2)

    def test_empty_code_snippet_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(**{"--code-snippet": ""}),
        )
        self.assertEqual(proc.returncode, 2)

    def test_multiline_code_snippet_accepted(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            *self._export_args(**{
                "--code-snippet": "function f() {\n  return 1;\n}",
            }),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


# ---------------------------------------------------------------------------
# AddPackageDepTests
# ---------------------------------------------------------------------------


class AddPackageDepTests(_EnvIsolationMixin, unittest.TestCase):

    def _add_pkg(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")

    def test_happy_path_external(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-dep",
            "--path", "apps/web",
            "--name", "react",
            "--kind", "external",
            "--version", "18.2.0",
            "--purpose", "UI rendering library.",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        deps = self._read_state()["packages"]["apps/web"]["dependencies"]
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["name"], "react")
        self.assertEqual(deps[0]["kind"], "external")
        self.assertEqual(deps[0]["version"], "18.2.0")
        self.assertEqual(deps[0]["consumer_locations"], [])

    def test_happy_path_internal_with_consumer_locations(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-dep",
            "--path", "apps/web",
            "--name", "@workspace/shared",
            "--kind", "internal",
            "--version", "",
            "--purpose", "Shared utilities.",
            "--consumer-location", "src/utils.ts:5",
            "--consumer-location", "src/api.ts:12",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        deps = self._read_state()["packages"]["apps/web"]["dependencies"]
        self.assertEqual(deps[0]["kind"], "internal")
        self.assertIsNone(deps[0]["version"])
        self.assertEqual(
            deps[0]["consumer_locations"],
            ["src/utils.ts:5", "src/api.ts:12"],
        )

    def test_invalid_kind_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-dep",
            "--path", "apps/web",
            "--name", "react",
            "--kind", "BOGUS",
            "--version", "",
            "--purpose", "X",
        )
        self.assertEqual(proc.returncode, 2)

    def test_unregistered_package_rejected(self):
        proc = _run_cli(
            self.devforge_dir, "add-package-dep",
            "--path", "apps/web",
            "--name", "react",
            "--kind", "external",
            "--version", "",
            "--purpose", "X",
        )
        self.assertEqual(proc.returncode, 2)

    def test_duplicate_name_rejected(self):
        self._add_pkg()
        _run_cli(
            self.devforge_dir, "add-package-dep",
            "--path", "apps/web",
            "--name", "react",
            "--kind", "external",
            "--version", "",
            "--purpose", "X",
        )
        proc = _run_cli(
            self.devforge_dir, "add-package-dep",
            "--path", "apps/web",
            "--name", "react",
            "--kind", "external",
            "--version", "",
            "--purpose", "Y",
        )
        self.assertEqual(proc.returncode, 2)

    def test_empty_purpose_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-dep",
            "--path", "apps/web",
            "--name", "react",
            "--kind", "external",
            "--version", "",
            "--purpose", "",
        )
        self.assertEqual(proc.returncode, 2)

    def test_consumer_location_with_newline_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-dep",
            "--path", "apps/web",
            "--name", "react",
            "--kind", "external",
            "--version", "",
            "--purpose", "X",
            "--consumer-location", "ok",
            "--consumer-location", "bad\nentry",
        )
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# AddPackageHazardTests
# ---------------------------------------------------------------------------


class AddPackageHazardTests(_EnvIsolationMixin, unittest.TestCase):

    def _add_pkg(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")

    def test_happy_path_no_cite(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-hazard",
            "--path", "apps/web",
            "--category", "naming",
            "--description", "Inconsistent casing.",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        hazards = self._read_state()["packages"]["apps/web"]["hazards"]
        self.assertEqual(len(hazards), 1)
        self.assertEqual(hazards[0]["category"], "naming")
        self.assertIsNone(hazards[0]["cite"])

    def test_happy_path_with_cite(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-hazard",
            "--path", "apps/web",
            "--category", "performance",
            "--description", "N+1 query.",
            "--cite-file", "src/db.ts",
            "--cite-start", "20",
            "--cite-end", "30",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        hazards = self._read_state()["packages"]["apps/web"]["hazards"]
        self.assertEqual(hazards[0]["cite"]["file"], "src/db.ts")
        self.assertEqual(hazards[0]["cite"]["start"], 20)
        self.assertEqual(hazards[0]["cite"]["end"], 30)

    def test_partial_cite_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-hazard",
            "--path", "apps/web",
            "--category", "performance",
            "--description", "N+1 query.",
            "--cite-file", "src/db.ts",
            "--cite-start", "20",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"--cite-end", proc.stderr)

    def test_invalid_category_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "add-package-hazard",
            "--path", "apps/web",
            "--category", "BOGUS",
            "--description", "X",
        )
        self.assertEqual(proc.returncode, 2)

    def test_unregistered_package_rejected(self):
        proc = _run_cli(
            self.devforge_dir, "add-package-hazard",
            "--path", "apps/web",
            "--category", "naming",
            "--description", "X",
        )
        self.assertEqual(proc.returncode, 2)

    def test_two_hazards_appended(self):
        self._add_pkg()
        _run_cli(self.devforge_dir, "add-package-hazard",
                 "--path", "apps/web", "--category", "naming",
                 "--description", "Issue 1.")
        _run_cli(self.devforge_dir, "add-package-hazard",
                 "--path", "apps/web", "--category", "duplication",
                 "--description", "Issue 2.")
        hazards = self._read_state()["packages"]["apps/web"]["hazards"]
        self.assertEqual(len(hazards), 2)


# ---------------------------------------------------------------------------
# SetPackageUsageExampleTests
# ---------------------------------------------------------------------------


class SetPackageUsageExampleTests(_EnvIsolationMixin, unittest.TestCase):

    def _add_pkg(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")

    def test_happy_path(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-usage-example",
            "--path", "apps/web",
            "--language", "typescript",
            "--code-snippet", "import { foo } from './foo';\nfoo();",
            "--cite-file", "examples/usage.ts",
            "--cite-start", "1",
            "--cite-end", "2",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ue = self._read_state()["packages"]["apps/web"]["usage_example"]
        self.assertEqual(ue["language"], "typescript")
        self.assertEqual(ue["cite"]["file"], "examples/usage.ts")

    def test_overwrite_allowed(self):
        self._add_pkg()
        _run_cli(self.devforge_dir, "set-package-usage-example",
                 "--path", "apps/web", "--language", "typescript",
                 "--code-snippet", "v1",
                 "--cite-file", "a.ts", "--cite-start", "1", "--cite-end", "1")
        _run_cli(self.devforge_dir, "set-package-usage-example",
                 "--path", "apps/web", "--language", "typescript",
                 "--code-snippet", "v2",
                 "--cite-file", "b.ts", "--cite-start", "1", "--cite-end", "1")
        ue = self._read_state()["packages"]["apps/web"]["usage_example"]
        self.assertEqual(ue["snippet"], "v2")
        self.assertEqual(ue["cite"]["file"], "b.ts")

    def test_unregistered_package_rejected(self):
        proc = _run_cli(
            self.devforge_dir, "set-package-usage-example",
            "--path", "apps/web", "--language", "ts",
            "--code-snippet", "x",
            "--cite-file", "a.ts", "--cite-start", "1", "--cite-end", "1",
        )
        self.assertEqual(proc.returncode, 2)

    def test_empty_language_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-usage-example",
            "--path", "apps/web", "--language", "",
            "--code-snippet", "x",
            "--cite-file", "a.ts", "--cite-start", "1", "--cite-end", "1",
        )
        self.assertEqual(proc.returncode, 2)

    def test_zero_start_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-usage-example",
            "--path", "apps/web", "--language", "ts",
            "--code-snippet", "x",
            "--cite-file", "a.ts", "--cite-start", "0", "--cite-end", "1",
        )
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# StatusTests
# ---------------------------------------------------------------------------


class StatusTests(_EnvIsolationMixin, unittest.TestCase):

    def test_status_when_state_missing(self):
        proc = _run_cli(self.devforge_dir, "status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(b"missing", proc.stdout)
        self.assertIn(b".generate-docs-state.json", proc.stdout)

    def test_status_after_add_package(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")
        proc = _run_cli(self.devforge_dir, "status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn("packages: 1", out)
        self.assertIn("apps/web:", out)
        self.assertIn("overview: UNSET", out)
        self.assertIn("scripts: 0", out)
        self.assertIn("exports: 0", out)

    def test_status_after_setters_shows_set(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")
        _run_cli(self.devforge_dir, "set-package-overview",
                 "--path", "apps/web", "--text", "An app.")
        _run_cli(self.devforge_dir, "set-package-language",
                 "--path", "apps/web", "--value", "TypeScript")
        _run_cli(self.devforge_dir, "set-package-framework",
                 "--path", "apps/web", "--value", "React")
        _run_cli(self.devforge_dir, "add-package-script",
                 "--path", "apps/web", "--script-name", "build",
                 "--command", "vite build")
        proc = _run_cli(self.devforge_dir, "status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn("overview: SET", out)
        self.assertIn("primary_language: SET", out)
        self.assertIn("framework: SET (React)", out)
        self.assertIn("scripts: 1", out)

    def test_status_lists_packages_alphabetically(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "z-app", "--name", "z")
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "a-app", "--name", "a")
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "m-app", "--name", "m")
        proc = _run_cli(self.devforge_dir, "status")
        out = proc.stdout.decode("utf-8")
        a_idx = out.index("a-app:")
        m_idx = out.index("m-app:")
        z_idx = out.index("z-app:")
        self.assertTrue(a_idx < m_idx < z_idx)

    def test_status_reads_corrupt_state_as_error(self):
        # Hand-write garbage JSON to force the parse error path.
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text("not-json{{{", encoding="utf-8")
        proc = _run_cli(self.devforge_dir, "status")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"corrupt", proc.stderr)


# ---------------------------------------------------------------------------
# StateAtomicityTests
# ---------------------------------------------------------------------------


class StateAtomicityTests(_EnvIsolationMixin, unittest.TestCase):

    def test_repeat_setter_state_is_stable(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")
        _run_cli(self.devforge_dir, "set-package-overview",
                 "--path", "apps/web", "--text", "X")
        first = self.state_file.read_bytes()
        _run_cli(self.devforge_dir, "set-package-overview",
                 "--path", "apps/web", "--text", "X")
        second = self.state_file.read_bytes()
        self.assertEqual(first, second)

    def test_no_temp_files_left_behind_on_success(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")
        leftovers = [
            p for p in self.devforge_dir.iterdir()
            if p.name.startswith(".generate-docs-state-")
            and p.name.endswith(".json")
            and p.name != gdh.STATE_FILE_NAME
        ]
        self.assertEqual(leftovers, [])

    def test_corrupt_state_load_surfaces_error(self):
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text("{not json", encoding="utf-8")
        proc = _run_cli(
            self.devforge_dir, "set-package-overview",
            "--path", "apps/web", "--text", "X",
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"corrupt", proc.stderr)

    def test_packages_wrong_type_raises_state_load_error(self):
        """packages field present-but-wrong-type must raise StateLoadError,
        not silently reset.

        Regression guard for Finding 1: a corrupt state file with
        `packages` set to a non-object value (e.g., a list) used to be
        silently coerced back to `{}`, discarding whatever was already
        on disk. The loader now raises so the CLI exits 1 with a clear
        diagnostic.
        """
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps({"version": 1, "packages": ["corrupted"]}),
            encoding="utf-8",
        )
        proc = _run_cli(
            self.devforge_dir, "set-package-overview",
            "--path", "apps/web", "--text", "X",
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"must be an object", proc.stderr)


# ---------------------------------------------------------------------------
# StateConcurrencyTests
#
# Regression guard for the testForge20 2026-04-30 incident: 11 sequential
# (per LLM intent) `add-package-script` invocations registered cleanly to
# stderr but the on-disk state file showed `scripts: {}`. Root cause was
# an unsynchronized read-modify-write cycle that lost data when multiple
# helper processes overlapped. Fixed by `_state._state_transaction()` —
# an exclusive POSIX file lock around the whole RMW. These tests pin the
# fix with concurrent invocations + the abort-skips-write contract.
# ---------------------------------------------------------------------------


class StateConcurrencyTests(_EnvIsolationMixin, unittest.TestCase):

    def _spawn_concurrent(self, args_list):
        """Launch each command in `args_list` as a thread + wait for all.

        Each entry is a tuple of CLI args (without devforge_dir wiring).
        Returns the list of (returncode, stderr) per command.
        """
        import threading
        results = [None] * len(args_list)

        def runner(idx, args):
            proc = _run_cli(self.devforge_dir, *args)
            results[idx] = (proc.returncode, proc.stderr)

        threads = [
            threading.Thread(target=runner, args=(i, a))
            for i, a in enumerate(args_list)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return results

    def test_concurrent_add_package_script_preserves_all(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "pkg/foo", "--name", "foo")
        commands = [
            ("add-package-script", "--path", "pkg/foo",
             "--script-name", "s{0}".format(i),
             "--command", "echo {0}".format(i))
            for i in range(20)
        ]
        results = self._spawn_concurrent(commands)
        for rc, stderr in results:
            self.assertEqual(
                rc, 0,
                "add-package-script returned {0}; stderr={1!r}".format(
                    rc, stderr,
                ),
            )
        state = self._read_state()
        self.assertEqual(len(state["packages"]["pkg/foo"]["scripts"]), 20)

    def test_concurrent_mixed_setters_preserves_all_fields(self):
        """Even mixed-setter concurrency cannot clobber unrelated fields.

        This is the exact bug shape observed in testForge20: scripts
        registered by one process disappeared after a different setter
        (export / dep) wrote-back stale state from before the scripts
        landed.
        """
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "pkg/foo", "--name", "foo")
        # Stage a real source file so add-package-export's cite is
        # well-formed enough for set-time validation. Validate-time
        # filesystem checks are NOT exercised here; we're only pinning
        # the persistence contract.
        src_dir = self.devforge_dir.parent / "pkg" / "foo"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "src.ts").write_text(
            "line1\nline2\nline3\nline4\n", encoding="utf-8",
        )
        commands = []
        for i in range(5):
            commands.append((
                "add-package-script", "--path", "pkg/foo",
                "--script-name", "s{0}".format(i),
                "--command", "echo {0}".format(i),
            ))
        for i in range(5):
            commands.append((
                "add-package-dep", "--path", "pkg/foo",
                "--name", "dep{0}".format(i),
                "--kind", "external",
                "--purpose", "purpose {0}".format(i),
            ))
        results = self._spawn_concurrent(commands)
        for rc, stderr in results:
            self.assertEqual(rc, 0, "rc={0} stderr={1!r}".format(rc, stderr))
        state = self._read_state()
        pkg = state["packages"]["pkg/foo"]
        self.assertEqual(len(pkg["scripts"]), 5)
        self.assertEqual(len(pkg["dependencies"]), 5)

    def test_lock_file_created_alongside_state(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "pkg/foo", "--name", "foo")
        lock = self.devforge_dir / (gdh.STATE_FILE_NAME + ".lock")
        self.assertTrue(
            lock.exists(),
            "lock sidecar {0} should exist after a setter".format(lock),
        )

    def test_abort_transaction_does_not_write_state(self):
        """Add-package on an already-registered path must not rewrite state.

        Confirms `_AbortTransaction` propagates out of `_state_transaction()`
        cleanly without triggering `_write_state`. (mtime-stable check.)
        """
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "pkg/foo", "--name", "foo")
        first_mtime = self.state_file.stat().st_mtime_ns
        # On HFS+/APFS macOS mtime can have second-level resolution; pad
        # by sleeping briefly so a second write would be detectable.
        import time
        time.sleep(0.05)
        proc = _run_cli(self.devforge_dir, "add-package",
                        "--path", "pkg/foo", "--name", "foo")
        self.assertEqual(proc.returncode, 2)
        second_mtime = self.state_file.stat().st_mtime_ns
        self.assertEqual(
            first_mtime, second_mtime,
            "abort path should NOT touch state file mtime",
        )

    def test_duplicate_script_abort_does_not_clobber(self):
        """Add a script, attempt re-add, ensure original entry survives."""
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "pkg/foo", "--name", "foo")
        _run_cli(self.devforge_dir, "add-package-script",
                 "--path", "pkg/foo",
                 "--script-name", "build", "--command", "make build")
        # Duplicate attempt with different command should be rejected,
        # leaving the original `make build` intact.
        proc = _run_cli(self.devforge_dir, "add-package-script",
                        "--path", "pkg/foo",
                        "--script-name", "build", "--command", "make NEW")
        self.assertEqual(proc.returncode, 2)
        state = self._read_state()
        self.assertEqual(
            state["packages"]["pkg/foo"]["scripts"]["build"],
            "make build",
        )


# ---------------------------------------------------------------------------
# ExtractPackageScriptsTests
# ---------------------------------------------------------------------------


class ExtractPackageScriptsTests(unittest.TestCase):
    """`extract-package-scripts` is read-only — no DEVFORGE_DIR needed.

    We point each test at a `tempfile.TemporaryDirectory` and write a
    minimal manifest into it, then invoke the subcommand with `--path
    <tmpdir>` and parse the JSON dict from stdout.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pkg_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, *extra):
        env = os.environ.copy()
        env.pop("DEVFORGE_DIR", None)
        return subprocess.run(
            [sys.executable, str(_HELPER_PY), "extract-package-scripts",
             "--path", str(self.pkg_dir), *extra],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_no_manifest_errors(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"no manifest found", proc.stderr)

    def test_invalid_path_errors(self):
        env = os.environ.copy()
        env.pop("DEVFORGE_DIR", None)
        proc = subprocess.run(
            [sys.executable, str(_HELPER_PY), "extract-package-scripts",
             "--path", "/nonexistent/path/here"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(proc.returncode, 2)

    def test_js_ts_package_json_with_scripts(self):
        (self.pkg_dir / "package.json").write_text(json.dumps({
            "name": "web",
            "scripts": {"build": "vite build", "test": "vitest"},
        }), encoding="utf-8")
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts, {"build": "vite build", "test": "vitest"})

    def test_js_ts_package_json_no_scripts_block(self):
        (self.pkg_dir / "package.json").write_text(json.dumps({
            "name": "web",
        }), encoding="utf-8")
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts, {})

    def test_js_ts_package_json_invalid_json(self):
        (self.pkg_dir / "package.json").write_text("{bad", encoding="utf-8")
        proc = self._run()
        # Manifest exists; we attempt to parse and gracefully return {}.
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts, {})

    def test_rust_default_scripts(self):
        (self.pkg_dir / "Cargo.toml").write_text(
            "[package]\nname = \"x\"\nversion = \"0.1\"\n", encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertIn("build", scripts)
        self.assertEqual(scripts["build"], "cargo build")
        self.assertEqual(scripts["test"], "cargo test")
        self.assertEqual(scripts["clippy"], "cargo clippy")

    def test_python_default_scripts(self):
        (self.pkg_dir / "pyproject.toml").write_text(
            "[project]\nname = \"x\"\n", encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertIn("install", scripts)
        self.assertEqual(scripts["install"], "pip install -e .")
        self.assertEqual(scripts["test"], "pytest")

    def test_python_pyproject_project_scripts_section(self):
        """`[project.scripts]` (PEP 621) entries are extracted via regex.

        Regression guard for Finding 2: Python pyproject.toml used to
        ignore the file content and emit hardcoded defaults. The
        regex-based extractor now picks up real entry points so the
        LLM doesn't have to register every console script manually.
        """
        (self.pkg_dir / "pyproject.toml").write_text(
            "[project]\n"
            "name = \"x\"\n"
            "version = \"0.1.0\"\n"
            "\n"
            "[project.scripts]\n"
            "mycli = \"mypkg.cli:main\"\n"
            "myhelper = \"mypkg.helper:run\"\n",
            encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(
            scripts,
            {"mycli": "mypkg.cli:main", "myhelper": "mypkg.helper:run"},
        )

    def test_python_pyproject_poetry_scripts_section(self):
        """`[tool.poetry.scripts]` entries are extracted via regex.

        Poetry-managed projects use this section instead of (or in
        addition to) PEP 621's `[project.scripts]`. Both shapes are
        recognized by the same extractor.
        """
        (self.pkg_dir / "pyproject.toml").write_text(
            "[tool.poetry]\n"
            "name = \"x\"\n"
            "version = \"0.1.0\"\n"
            "\n"
            "[tool.poetry.scripts]\n"
            "serve = \"mypkg.server:main\"\n",
            encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts, {"serve": "mypkg.server:main"})

    def test_python_pyproject_no_scripts_section_falls_back_to_defaults(self):
        """No `[project.scripts]` AND no `[tool.poetry.scripts]` -> defaults.

        The fallback preserves the helper's pre-Finding-2 behavior so
        users with bare-bones pyproject files still get a useful
        starting set without manual registration.
        """
        (self.pkg_dir / "pyproject.toml").write_text(
            "[project]\n"
            "name = \"x\"\n"
            "version = \"0.1.0\"\n"
            "\n"
            "[build-system]\n"
            "requires = [\"setuptools\"]\n",
            encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(
            scripts, {"install": "pip install -e .", "test": "pytest"},
        )

    def test_ruby_rakefile_tasks_extracted(self):
        """`task :foo` and `task "bar"` are statically parsed from Rakefile.

        Regression guard for Finding 2: Ruby detection used to ignore
        Rakefile entirely. Top-level Rake tasks now surface as
        `bundle exec rake <task>` script entries alongside the bundle
        defaults so the LLM has a real task list, not just defaults.
        """
        (self.pkg_dir / "Rakefile").write_text(
            "task :foo do\n"
            "  puts 'foo'\n"
            "end\n"
            "\n"
            "task \"bar\" do\n"
            "  puts 'bar'\n"
            "end\n",
            encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts.get("foo"), "bundle exec rake foo")
        self.assertEqual(scripts.get("bar"), "bundle exec rake bar")
        # Defaults remain present alongside the discovered tasks.
        self.assertEqual(scripts.get("install"), "bundle install")
        self.assertEqual(scripts.get("exec"), "bundle exec")

    def test_ruby_gemfile_only_emits_defaults_only(self):
        """Gemfile without Rakefile -> bundle defaults only, no rake tasks.

        Confirms the Rakefile parser does not read non-existent files
        and the defaults shape is what callers see when only the
        dependency manifest is present.
        """
        (self.pkg_dir / "Gemfile").write_text(
            "source 'https://rubygems.org'\n"
            "gem 'rails', '~> 7.0'\n",
            encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(
            scripts, {"install": "bundle install", "exec": "bundle exec"},
        )

    def test_go_default_scripts(self):
        (self.pkg_dir / "go.mod").write_text(
            "module example.com/x\n", encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts["build"], "go build ./...")
        self.assertEqual(scripts["vet"], "go vet ./...")

    def test_maven_default_scripts(self):
        (self.pkg_dir / "pom.xml").write_text(
            "<project></project>\n", encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts["compile"], "mvn compile")
        self.assertEqual(scripts["package"], "mvn package")

    def test_gradle_default_scripts(self):
        (self.pkg_dir / "build.gradle").write_text(
            "task hello { doLast { println 'hi' } }\n", encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts["build"], "./gradlew build")

    def test_gradle_kts_default_scripts(self):
        (self.pkg_dir / "build.gradle.kts").write_text(
            "tasks.register(\"hello\") {}\n", encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts["build"], "./gradlew build")

    def test_dotnet_csproj_default_scripts(self):
        (self.pkg_dir / "x.csproj").write_text("<Project/>\n", encoding="utf-8")
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts["build"], "dotnet build")

    def test_ruby_default_scripts(self):
        (self.pkg_dir / "Gemfile").write_text(
            "source 'https://rubygems.org'\n", encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts["install"], "bundle install")

    def test_php_composer_with_scripts(self):
        (self.pkg_dir / "composer.json").write_text(json.dumps({
            "name": "vendor/pkg",
            "scripts": {"test": "phpunit"},
        }), encoding="utf-8")
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts, {"test": "phpunit"})

    def test_priority_js_ts_over_rust(self):
        # If both manifests are present, JS/TS wins per the priority order.
        (self.pkg_dir / "package.json").write_text(json.dumps({
            "scripts": {"build": "vite build"},
        }), encoding="utf-8")
        (self.pkg_dir / "Cargo.toml").write_text(
            "[package]\nname = \"x\"\n", encoding="utf-8",
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        scripts = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(scripts, {"build": "vite build"})
        # Secondary-detection warning surfaces on stderr.
        self.assertIn(b"multiple manifests", proc.stderr)


# ---------------------------------------------------------------------------
# ExtractSnippetTests — language-agnostic line-range byte extraction.
#
# Behavioral contract: piping `extract-snippet --file F --start S --end E`
# into `add-package-export --code-snippet "$(...)"` must produce a
# validate-clean export every time. The integration test at the end of
# this class exercises that round-trip end-to-end.
#
# CRLF policy: `extract-snippet` PRESERVES line endings verbatim. The
# downstream validator (`_validators._normalize_for_compare`) normalizes
# CRLF -> LF before equality comparison, so either choice round-trips
# cleanly. Preserving keeps `extract-snippet` purely mechanical.
# ---------------------------------------------------------------------------


class ExtractSnippetTests(_EnvIsolationMixin, unittest.TestCase):

    def _write_lines(self, name, lines, line_ending="\n"):
        """Helper: write a fixture file with controlled line endings.

        Returns the absolute path. `lines` is a list of line bodies (no
        trailing newline). The file ends with `line_ending` after the
        last line so line-count math matches the human view.
        """
        path = self.devforge_dir / name
        path.write_text(line_ending.join(lines) + line_ending, encoding="utf-8")
        return path

    def test_extract_snippet_basic_range(self):
        path = self._write_lines(
            "f.txt", ["line1", "line2", "line3", "line4", "line5",
                     "line6", "line7", "line8", "line9", "line10"],
        )
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(path),
            "--start", "3",
            "--end", "5",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Inclusive range — lines 3, 4, 5 (each with trailing '\n').
        self.assertEqual(
            proc.stdout.decode("utf-8"),
            "line3\nline4\nline5\n",
        )

    def test_extract_snippet_single_line(self):
        path = self._write_lines(
            "f.txt", ["a", "b", "c", "d", "e", "f", "target", "h", "i", "j"],
        )
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(path),
            "--start", "7",
            "--end", "7",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.decode("utf-8"), "target\n")

    def test_extract_snippet_indented_content_preserved(self):
        # CRITICAL regression test — the citation-mismatch failure mode
        # this subcommand was built to close. Source file has indented
        # content; output must preserve every leading space verbatim.
        path = self.devforge_dir / "f.ts"
        body = (
            "function outer() {\n"
            "    const x = 1;\n"
            "    if (x > 0) {\n"
            "        return x;\n"
            "    }\n"
            "}\n"
        )
        path.write_text(body, encoding="utf-8")
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(path),
            "--start", "2",
            "--end", "5",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Every leading space preserved bit-for-bit.
        expected = (
            "    const x = 1;\n"
            "    if (x > 0) {\n"
            "        return x;\n"
            "    }\n"
        )
        self.assertEqual(proc.stdout.decode("utf-8"), expected)

    def test_extract_snippet_crlf_input_preserved(self):
        # Behavior choice: line endings are preserved verbatim. The
        # downstream `[snippet-verbatim]` validator normalizes CRLF -> LF
        # before comparison, so this is round-trip safe.
        path = self.devforge_dir / "f.txt"
        # Write raw bytes so the OS doesn't translate line endings.
        path.write_bytes(b"a\r\nb\r\nc\r\nd\r\n")
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(path),
            "--start", "2",
            "--end", "3",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Verbatim CRLF preservation. (We compare bytes, not str, to
        # avoid any decoder-level normalization.)
        self.assertEqual(proc.stdout, b"b\r\nc\r\n")

    def test_extract_snippet_end_before_start_fails(self):
        path = self._write_lines("f.txt", ["1", "2", "3", "4", "5"])
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(path),
            "--start", "10",
            "--end", "5",
        )
        self.assertEqual(proc.returncode, 2)
        # Error message must clearly explain the range issue.
        msg = proc.stderr.decode("utf-8")
        self.assertIn("end", msg)
        self.assertIn("start", msg)

    def test_extract_snippet_line_range_out_of_bounds(self):
        path = self._write_lines("f.txt", ["1", "2", "3", "4", "5"])
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(path),
            "--start", "1",
            "--end", "100",
        )
        self.assertEqual(proc.returncode, 2)
        msg = proc.stderr.decode("utf-8")
        # Error mentions exceeded line count and the actual count.
        self.assertIn("exceeds", msg)
        self.assertIn("5", msg)

    def test_extract_snippet_start_out_of_bounds(self):
        path = self._write_lines("f.txt", ["1", "2", "3"])
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(path),
            "--start", "10",
            "--end", "12",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"exceeds", proc.stderr)

    def test_extract_snippet_missing_file(self):
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(self.devforge_dir / "nonexistent.txt"),
            "--start", "1",
            "--end", "1",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"does not exist", proc.stderr)

    def test_extract_snippet_directory_path_fails(self):
        # `--file` pointing at a directory: clear error, exit 2.
        sub = self.devforge_dir / "subdir"
        sub.mkdir()
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(sub),
            "--start", "1",
            "--end", "1",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"not a regular file", proc.stderr)

    def test_extract_snippet_zero_start_rejected(self):
        path = self._write_lines("f.txt", ["1", "2", "3"])
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(path),
            "--start", "0",
            "--end", "1",
        )
        self.assertEqual(proc.returncode, 2)

    def test_extract_snippet_round_trip_validates_against_add_export(self):
        # End-to-end integration test proving the whole point of this
        # subcommand: extract-snippet output piped into add-package-export
        # always produces a validate-clean export, eliminating the
        # snippet-verbatim error class.
        #
        # The fixture: a TypeScript file with deeply-indented content
        # (the exact shape that historically tripped the LLM transcription
        # bug when copied by hand).
        project_root = self.devforge_dir
        src_dir = project_root / "src"
        src_dir.mkdir()
        src_file = src_dir / "App.tsx"
        body = (
            "import React from 'react';\n"
            "\n"
            "export function App() {\n"
            "    return (\n"
            "        <div>\n"
            "            <p>Hello</p>\n"
            "        </div>\n"
            "    );\n"
            "}\n"
        )
        src_file.write_text(body, encoding="utf-8")

        # 1. Extract lines 3-9 (the function body) via the new subcommand.
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(src_file),
            "--start", "3",
            "--end", "9",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        snippet = proc.stdout.decode("utf-8")
        # Sanity: leading 4-space indent preserved (the bug class).
        self.assertIn("    return (", snippet)
        self.assertIn("        <div>", snippet)

        # 2. Register the package + use the extracted snippet for an
        #    export. Pass the raw bytes from extract-snippet exactly as
        #    a shell `$(...)` substitution would (no transcription).
        proc = _run_cli(
            self.devforge_dir, "add-package",
            "--path", ".", "--name", "root",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_cli(
            self.devforge_dir, "set-package-overview",
            "--path", ".", "--text", "Root.",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_cli(
            self.devforge_dir, "set-package-tree",
            "--path", ".", "--text", "src/",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_cli(
            self.devforge_dir, "set-package-language",
            "--path", ".", "--value", "TypeScript",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_cli(
            self.devforge_dir, "add-package-export",
            "--path", ".",
            "--name", "App",
            "--kind", "component",
            "--description", "App component.",
            "--language", "tsx",
            "--code-snippet", snippet,
            "--cite-file", "src/App.tsx",
            "--cite-start", "3",
            "--cite-end", "9",
            project_root=project_root,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_cli(
            self.devforge_dir, "add-package-dep",
            "--path", ".",
            "--name", "react",
            "--kind", "external",
            "--version", "18",
            "--purpose", "UI lib.",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Use extract-snippet for the usage example too so its
        # [snippet-verbatim] rule passes (the same code path the
        # orchestrator will use for every snippet).
        proc = _run_cli(
            self.devforge_dir,
            "extract-snippet",
            "--file", str(src_file),
            "--start", "3",
            "--end", "3",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        usage_snippet = proc.stdout.decode("utf-8")
        proc = _run_cli(
            self.devforge_dir, "set-package-usage-example",
            "--path", ".",
            "--language", "tsx",
            "--code-snippet", usage_snippet,
            "--cite-file", "src/App.tsx",
            "--cite-start", "3",
            "--cite-end", "3",
            project_root=project_root,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        # 3. Validate. Crucially the [snippet-verbatim] rule must NOT
        #    fire — that's the whole motivation for this subcommand.
        proc = _run_cli(
            self.devforge_dir, "validate-package",
            "--path", ".",
            project_root=project_root,
        )
        # Even if validate-package surfaces other findings (decomposition,
        # missing concerns, etc.), [snippet-verbatim] must not be among
        # them. The strict assertion is the absence of that rule tag.
        out = proc.stdout.decode("utf-8") + proc.stderr.decode("utf-8")
        self.assertNotIn("snippet-verbatim", out)


# ---------------------------------------------------------------------------
# RoundTripTests — register a package, run setters, run status, observe
# expected output. Catches integration regressions where a setter writes
# an inconsistent shape that status can't parse.
# ---------------------------------------------------------------------------


class RoundTripTests(_EnvIsolationMixin, unittest.TestCase):

    def test_full_package_round_trip(self):
        # Register, fill every setter, run status — verify all SET lines.
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")
        _run_cli(self.devforge_dir, "set-package-overview",
                 "--path", "apps/web", "--text", "Web app.")
        _run_cli(self.devforge_dir, "set-package-tree",
                 "--path", "apps/web", "--text", "tree")
        _run_cli(self.devforge_dir, "set-package-language",
                 "--path", "apps/web", "--value", "TypeScript")
        _run_cli(self.devforge_dir, "set-package-framework",
                 "--path", "apps/web", "--value", "React")
        _run_cli(self.devforge_dir, "set-package-build-tool",
                 "--path", "apps/web", "--value", "vite")
        _run_cli(self.devforge_dir, "add-package-script",
                 "--path", "apps/web", "--script-name", "build",
                 "--command", "vite build")
        _run_cli(self.devforge_dir, "add-package-export",
                 "--path", "apps/web", "--name", "App", "--kind", "component",
                 "--signature", "App(): JSX.Element",
                 "--description", "Root component.",
                 "--language", "tsx",
                 "--code-snippet", "export function App() { return <div/>; }",
                 "--cite-file", "src/App.tsx",
                 "--cite-start", "1", "--cite-end", "1")
        _run_cli(self.devforge_dir, "add-package-dep",
                 "--path", "apps/web", "--name", "react",
                 "--kind", "external", "--version", "18",
                 "--purpose", "UI lib.")
        _run_cli(self.devforge_dir, "add-package-hazard",
                 "--path", "apps/web", "--category", "naming",
                 "--description", "Mixed casing.")
        _run_cli(self.devforge_dir, "set-package-usage-example",
                 "--path", "apps/web", "--language", "tsx",
                 "--code-snippet", "<App />",
                 "--cite-file", "examples/usage.tsx",
                 "--cite-start", "1", "--cite-end", "1")
        proc = _run_cli(self.devforge_dir, "status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8")
        self.assertIn("overview: SET", out)
        self.assertIn("directory_tree: SET", out)
        self.assertIn("primary_language: SET", out)
        self.assertIn("framework: SET (React)", out)
        self.assertIn("build_tool: SET (vite)", out)
        self.assertIn("scripts: 1", out)
        self.assertIn("exports: 1", out)
        self.assertIn("dependencies: 1", out)
        self.assertIn("hazards: 1", out)
        self.assertIn("usage_example: SET", out)


# ---------------------------------------------------------------------------
# CLISurfaceTests
# ---------------------------------------------------------------------------


class CLISurfaceTests(_EnvIsolationMixin, unittest.TestCase):

    def test_help_lists_subcommands(self):
        proc = _run_cli(self.devforge_dir, "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for sub in (
            b"reset",
            b"add-package",
            b"set-package-overview",
            b"set-package-tree",
            b"set-package-language",
            b"set-package-framework",
            b"set-package-build-tool",
            b"add-package-script",
            b"add-package-export",
            b"add-package-dep",
            b"add-package-hazard",
            b"set-package-usage-example",
            b"status",
            b"extract-package-scripts",
        ):
            self.assertIn(sub, proc.stdout)

    def test_no_subcommand_returns_2(self):
        proc = _run_cli(self.devforge_dir)
        self.assertEqual(proc.returncode, 2)

    def test_unknown_subcommand_errors(self):
        proc = _run_cli(self.devforge_dir, "do-something-bogus")
        self.assertNotEqual(proc.returncode, 0)


# ---------------------------------------------------------------------------
# LauncherTests
# ---------------------------------------------------------------------------


class LauncherTests(_EnvIsolationMixin, unittest.TestCase):

    def test_launcher_dispatches_help(self):
        proc = _run_launcher(self.devforge_dir, "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(b"reset", proc.stdout)

    def test_launcher_dispatches_status(self):
        proc = _run_launcher(self.devforge_dir, "status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(b"missing", proc.stdout)

    def test_launcher_dispatches_add_package(self):
        proc = _run_launcher(
            self.devforge_dir, "add-package",
            "--path", "apps/web", "--name", "web",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.state_file.exists())


# ---------------------------------------------------------------------------
# SetPackageConsumerPatternTests (sub-step 1.2b)
# ---------------------------------------------------------------------------


class SetPackageConsumerPatternTests(_EnvIsolationMixin, unittest.TestCase):

    def _add_pkg(self):
        _run_cli(self.devforge_dir, "add-package",
                 "--path", "apps/web", "--name", "web")

    def test_happy_path(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-consumer-pattern",
            "--path", "apps/web",
            "--language", "typescript",
            "--code-snippet", "import { Web } from './web';\n<Web />",
            "--cite-file", "examples/consumer.tsx",
            "--cite-start", "3",
            "--cite-end", "5",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        cp = self._read_state()["packages"]["apps/web"]["consumer_pattern"]
        self.assertEqual(cp["language"], "typescript")
        self.assertEqual(cp["cite"]["file"], "examples/consumer.tsx")
        self.assertEqual(cp["cite"]["start"], 3)
        self.assertEqual(cp["cite"]["end"], 5)

    def test_overwrite_allowed(self):
        self._add_pkg()
        _run_cli(self.devforge_dir, "set-package-consumer-pattern",
                 "--path", "apps/web", "--language", "ts",
                 "--code-snippet", "v1",
                 "--cite-file", "a.ts", "--cite-start", "1", "--cite-end", "1")
        _run_cli(self.devforge_dir, "set-package-consumer-pattern",
                 "--path", "apps/web", "--language", "ts",
                 "--code-snippet", "v2",
                 "--cite-file", "b.ts", "--cite-start", "2", "--cite-end", "2")
        cp = self._read_state()["packages"]["apps/web"]["consumer_pattern"]
        self.assertEqual(cp["snippet"], "v2")
        self.assertEqual(cp["cite"]["file"], "b.ts")

    def test_zero_start_rejected(self):
        self._add_pkg()
        proc = _run_cli(
            self.devforge_dir, "set-package-consumer-pattern",
            "--path", "apps/web", "--language", "ts",
            "--code-snippet", "x",
            "--cite-file", "a.ts", "--cite-start", "0", "--cite-end", "1",
        )
        self.assertEqual(proc.returncode, 2)

    def test_unregistered_package_rejected(self):
        proc = _run_cli(
            self.devforge_dir, "set-package-consumer-pattern",
            "--path", "apps/web", "--language", "ts",
            "--code-snippet", "x",
            "--cite-file", "a.ts", "--cite-start", "1", "--cite-end", "1",
        )
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# RenderPackageSkeletonTests (sub-step 1.2b)
# ---------------------------------------------------------------------------


class _RenderTestBase(_EnvIsolationMixin, unittest.TestCase):
    """Shared setUp: separate project_root + devforge_dir.

    Render/validate need a project root (where cite files live). To
    keep the on-disk state next to a fixed-content source tree, we
    create a project_root tmpdir with a `.devforge/` subdir; the
    helper reads state from `.devforge/` and resolves cite-file paths
    relative to the project_root.
    """

    def setUp(self):
        self._saved_devforge = os.environ.pop("DEVFORGE_DIR", None)
        self._saved_root = os.environ.pop("DEVFORGE_PROJECT_ROOT", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self._tmp.name)
        self.devforge_dir = self.project_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.devforge_dir / gdh.STATE_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_devforge is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_devforge
        if self._saved_root is None:
            os.environ.pop("DEVFORGE_PROJECT_ROOT", None)
        else:
            os.environ["DEVFORGE_PROJECT_ROOT"] = self._saved_root

    def _run(self, *args):
        return _run_cli(self.devforge_dir, *args, project_root=self.project_root)

    def _add_pkg(self, path="apps/web", name="web"):
        self._run("add-package", "--path", path, "--name", name)

    def _write_source(self, rel_path, lines):
        """Write a source file under project_root and return its Path."""
        full = self.project_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return full


class RenderPackageSkeletonTests(_RenderTestBase):

    def test_empty_package_has_all_todos(self):
        self._add_pkg()
        proc = self._run("render-package-skeleton", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out_path = self.project_root / "docs" / "apps/web" / "index.md.skeleton"
        self.assertTrue(out_path.exists(), "skeleton not written")
        text = out_path.read_text(encoding="utf-8")
        self.assertIn("# web", text)
        self.assertIn("## Overview", text)
        self.assertIn("[TODO: 1-2 paragraphs", text)
        self.assertIn("## Directory Structure", text)
        self.assertIn("[TODO: ascii tree", text)
        self.assertIn("## Tech Stack", text)
        self.assertIn("[TODO]", text)
        self.assertIn("## Scripts", text)
        self.assertIn("[TODO: enumerate via add-package-script", text)
        self.assertIn("## Main Exports", text)
        self.assertIn("[TODO: enumerate package exports", text)
        # Types section omitted entirely when empty.
        self.assertNotIn("## Types", text)
        self.assertIn("## Dependencies", text)
        self.assertIn("[TODO: enumerate via add-package-dep", text)
        self.assertIn("## Hazards", text)
        self.assertIn("## Usage Example", text)
        self.assertIn("[TODO: lift a real usage example", text)
        self.assertIn("## Consumer Pattern", text)
        self.assertIn("[TODO: lift a representative consumer call", text)

    def test_partial_state_mixes_values_and_todos(self):
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "An app.")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "TypeScript")
        proc = self._run("render-package-skeleton", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = (self.project_root / "docs" / "apps/web" / "index.md.skeleton").read_text(
            encoding="utf-8"
        )
        self.assertIn("An app.", text)
        self.assertIn("TypeScript", text)
        # Unset fields still surface as [TODO].
        self.assertIn("[TODO: ascii tree", text)
        self.assertIn("[TODO: enumerate via add-package-script", text)

    def test_full_state_no_todos(self):
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "Web app.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/\n  index.ts")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "TypeScript")
        self._run("set-package-framework",
                  "--path", "apps/web", "--value", "React")
        self._run("set-package-build-tool",
                  "--path", "apps/web", "--value", "vite")
        self._run("add-package-script",
                  "--path", "apps/web", "--script-name", "build",
                  "--command", "vite build")
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "App",
                  "--kind", "component",
                  "--signature", "App(): JSX.Element",
                  "--description", "Root component.",
                  "--language", "tsx",
                  "--code-snippet", "export function App() {}",
                  "--cite-file", "src/App.tsx",
                  "--cite-start", "1", "--cite-end", "1")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "18",
                  "--purpose", "UI lib.")
        self._run("add-package-hazard",
                  "--path", "apps/web", "--category", "naming",
                  "--description", "Mixed casing.")
        self._run("set-package-usage-example",
                  "--path", "apps/web", "--language", "tsx",
                  "--code-snippet", "<App />",
                  "--cite-file", "examples/usage.tsx",
                  "--cite-start", "1", "--cite-end", "1")
        self._run("set-package-consumer-pattern",
                  "--path", "apps/web", "--language", "tsx",
                  "--code-snippet", "<App />",
                  "--cite-file", "examples/cp.tsx",
                  "--cite-start", "1", "--cite-end", "1")
        proc = self._run("render-package-skeleton", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = (self.project_root / "docs" / "apps/web" / "index.md.skeleton").read_text(
            encoding="utf-8"
        )
        # No [TODO markers should remain.
        self.assertNotIn("[TODO", text)
        # Tech-stack values populated.
        self.assertIn("TypeScript", text)
        self.assertIn("React", text)
        self.assertIn("vite", text)
        # Export rendered with cite comment.
        self.assertIn("### `App` — component", text)
        self.assertIn("<!-- src/App.tsx:1-1 -->", text)

    def test_idempotent(self):
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "X.")
        self._run("render-package-skeleton", "--path", "apps/web")
        out = (self.project_root / "docs" / "apps/web" / "index.md.skeleton").read_bytes()
        self._run("render-package-skeleton", "--path", "apps/web")
        out2 = (self.project_root / "docs" / "apps/web" / "index.md.skeleton").read_bytes()
        self.assertEqual(out, out2)

    def test_missing_package_errors(self):
        proc = self._run("render-package-skeleton", "--path", "apps/missing")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"not registered", proc.stderr)

    def test_types_section_appears_when_type_export_present(self):
        self._add_pkg()
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "User",
                  "--kind", "type",
                  "--signature", "type User = { id: string }",
                  "--description", "User row.",
                  "--language", "ts",
                  "--code-snippet", "type User = { id: string }",
                  "--cite-file", "src/types.ts",
                  "--cite-start", "1", "--cite-end", "1")
        self._run("render-package-skeleton", "--path", "apps/web")
        text = (self.project_root / "docs" / "apps/web" / "index.md.skeleton").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Types", text)
        self.assertIn("### `User` — type", text)

    def test_dependencies_split_into_internal_and_external(self):
        self._add_pkg()
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "18",
                  "--purpose", "UI lib.")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "@workspace/shared",
                  "--kind", "internal", "--version", "",
                  "--purpose", "Shared utilities.")
        self._run("render-package-skeleton", "--path", "apps/web")
        text = (self.project_root / "docs" / "apps/web" / "index.md.skeleton").read_text(
            encoding="utf-8"
        )
        self.assertIn("### Workspace-internal", text)
        self.assertIn("### External", text)
        self.assertIn("@workspace/shared", text)
        self.assertIn("react", text)

    def test_skeleton_atomic_no_temp_leftovers(self):
        self._add_pkg()
        self._run("render-package-skeleton", "--path", "apps/web")
        out_dir = self.project_root / "docs" / "apps/web"
        leftovers = [p for p in out_dir.iterdir() if p.name.startswith(".")]
        self.assertEqual(leftovers, [])


# ---------------------------------------------------------------------------
# ValidatePackageTests (sub-step 1.2b)
# ---------------------------------------------------------------------------


class ValidatePackageTests(_RenderTestBase):

    def _fill_minimum_valid(self, src_lines=None):
        """Register a package with required fields filled + a real source
        file at src/api.ts:1-3, ready to be cited by exports/usage_example
        /consumer_pattern."""
        if src_lines is None:
            src_lines = [
                "export function fetchUser(id) {",
                "  return db.users.get(id);",
                "}",
            ]
        self._write_source("src/api.ts", src_lines)
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "Web.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/\n  api.ts")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "TypeScript")
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "fetchUser",
                  "--kind", "function",
                  "--signature", "",
                  "--description", "Fetches a user.",
                  "--language", "ts",
                  "--code-snippet", "\n".join(src_lines),
                  "--cite-file", "src/api.ts",
                  "--cite-start", "1", "--cite-end", "3")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "18",
                  "--purpose", "UI lib.")

    def test_valid_package_passes(self):
        self._fill_minimum_valid()
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_missing_required_fields_reported(self):
        self._add_pkg()
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        # All three required fields should be flagged.
        self.assertIn(b"PackageDoc.overview", proc.stderr)
        self.assertIn(b"PackageDoc.directory_tree", proc.stderr)
        self.assertIn(b"PackageDoc.primary_language", proc.stderr)

    def test_no_exports_reported(self):
        self._write_source("src/x.ts", ["a"])
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "X.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "ts")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "1",
                  "--purpose", "UI.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"no registered exports", proc.stderr)

    def test_no_dependencies_reported(self):
        self._write_source("src/api.ts", ["a", "b", "c"])
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "X.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "ts")
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "f", "--kind", "function",
                  "--signature", "", "--description", "X.",
                  "--language", "ts", "--code-snippet", "a\nb\nc",
                  "--cite-file", "src/api.ts",
                  "--cite-start", "1", "--cite-end", "3")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"no registered dependencies", proc.stderr)

    def test_cite_file_does_not_exist_reported(self):
        # Ref file is registered but not written to disk.
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "X.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "ts")
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "f",
                  "--kind", "function",
                  "--signature", "", "--description", "X.",
                  "--language", "ts", "--code-snippet", "x",
                  "--cite-file", "src/missing.ts",
                  "--cite-start", "1", "--cite-end", "1")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "1",
                  "--purpose", "UI.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"does not exist", proc.stderr)

    def test_cite_range_out_of_bounds_reported(self):
        self._write_source("src/api.ts", ["only one line"])
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "X.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "ts")
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "f", "--kind", "function",
                  "--signature", "", "--description", "X.",
                  "--language", "ts", "--code-snippet", "x",
                  "--cite-file", "src/api.ts",
                  "--cite-start", "1", "--cite-end", "99")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "1",
                  "--purpose", "UI.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"exceeds file line count", proc.stderr)

    def test_snippet_mismatch_reported_with_diff(self):
        self._write_source("src/api.ts", [
            "export function fetchUser(id) {",
            "  return db.users.get(id);",
            "}",
        ])
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "X.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "ts")
        # Register a snippet that DOES NOT match the source.
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "f", "--kind", "function",
                  "--signature", "", "--description", "X.",
                  "--language", "ts",
                  "--code-snippet", "different content entirely",
                  "--cite-file", "src/api.ts",
                  "--cite-start", "1", "--cite-end", "3")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "1",
                  "--purpose", "UI.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"does not match", proc.stderr)
        # Diff fragment should be present.
        self.assertIn(b"expected (from source)", proc.stderr)

    def test_snippet_whitespace_normalized_passes(self):
        # Source has CRLF + trailing spaces; registered snippet uses LF
        # without trailing spaces. Verbatim-match should still pass.
        crlf_source = "line one  \r\nline two\r\nline three   \r\n"
        (self.project_root / "src").mkdir(parents=True, exist_ok=True)
        (self.project_root / "src" / "api.ts").write_bytes(
            crlf_source.encode("utf-8")
        )
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "X.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "ts")
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "f", "--kind", "function",
                  "--signature", "", "--description", "X.",
                  "--language", "ts",
                  "--code-snippet", "line one\nline two\nline three",
                  "--cite-file", "src/api.ts",
                  "--cite-start", "1", "--cite-end", "3")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "1",
                  "--purpose", "UI.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_internal_dep_unresolved_reported(self):
        self._fill_minimum_valid()
        # Add an internal dep that targets neither a registered package
        # nor an existing directory.
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "@workspace/missing",
                  "--kind", "internal", "--version", "",
                  "--purpose", "Should fail.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"internal dependency", proc.stderr)
        self.assertIn(b"@workspace/missing", proc.stderr)

    def test_internal_dep_as_registered_package_passes(self):
        self._fill_minimum_valid()
        # Register a second package; first package's internal dep
        # should resolve to it by name.
        self._run("add-package",
                  "--path", "packages/shared", "--name", "@workspace/shared")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "@workspace/shared",
                  "--kind", "internal", "--version", "",
                  "--purpose", "Shared utils.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_internal_dep_as_directory_passes(self):
        self._fill_minimum_valid()
        # Create a directory at packages/shared (under project root)
        # but DO NOT register it as a package.
        (self.project_root / "packages" / "shared").mkdir(parents=True)
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "packages/shared",
                  "--kind", "internal", "--version", "",
                  "--purpose", "Shared utils.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_todo_marker_detected_when_required_field_missing(self):
        # Skip the language setter — the rendered skeleton will still
        # have [TODO] in the Tech Stack table.
        self._write_source("src/api.ts", ["a", "b", "c"])
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "X.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/")
        # primary_language NOT set, so render-skeleton emits [TODO].
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "f", "--kind", "function",
                  "--signature", "", "--description", "X.",
                  "--language", "ts", "--code-snippet", "a\nb\nc",
                  "--cite-file", "src/api.ts",
                  "--cite-start", "1", "--cite-end", "3")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "1",
                  "--purpose", "UI.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        # required-fields rule fires AND todo-marker rule fires.
        self.assertIn(b"primary_language", proc.stderr)

    def test_multiple_errors_collected_not_short_circuited(self):
        # Empty package: required fields missing + no exports + no deps.
        # All three rules should fire in a single invocation.
        self._add_pkg()
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        stderr = proc.stderr.decode("utf-8")
        # required-fields (3 fields) + exports-nonempty + deps-nonempty
        # -> rule labels visible.
        self.assertIn("required-fields", stderr)
        self.assertIn("exports-nonempty", stderr)
        self.assertIn("dependencies-nonempty", stderr)

    def test_missing_package_returns_2(self):
        proc = self._run("validate-package", "--path", "apps/missing")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"not registered", proc.stderr)

    def test_validate_idempotent(self):
        self._fill_minimum_valid()
        proc1 = self._run("validate-package", "--path", "apps/web")
        proc2 = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc1.returncode, proc2.returncode)
        self.assertEqual(proc1.stderr, proc2.stderr)

    def test_enum_recheck_rejects_corrupted_state(self):
        """Rule 7: a corrupted state record with an invalid enum is
        rejected at validate-time."""
        from _generate_docs._validators import validate_package
        from _generate_docs._state import (
            default_state,
            default_package_record,
        )

        state = default_state()
        pkg = default_package_record("web", "apps/web")
        pkg["overview"] = "X"
        pkg["directory_tree"] = "src/"
        pkg["primary_language"] = "ts"
        # Inject an invalid kind directly (bypasses set-time validation).
        pkg["exports"] = [{
            "kind": "INVALID_KIND",
            "name": "f",
            "signature": None,
            "description": "test",
            "code": {
                "language": "ts",
                "snippet": "x",
                "cite": {"file": "src/f.ts", "start": 1, "end": 1},
            },
        }]
        pkg["dependencies"] = [{
            "kind": "external",
            "name": "react",
            "version": "1.0.0",
            "purpose": "ui framework",
            "consumer_locations": [],
        }]
        state["packages"]["apps/web"] = pkg

        errors = validate_package(state, "apps/web", self.project_root)
        rule_names = {e["rule"] for e in errors}
        self.assertIn("export-kind-invalid", rule_names)

    def test_optional_render_bug_scripts_caught(self):
        """Rule 9 (defense-in-depth): if state has scripts populated but
        the render emits the optional [TODO], it's a render bug.

        Synthetic test — we patch the render function to simulate the
        bug. Without this validator rule, the render bug surfaces as a
        silently-malformed final doc with [TODO] next to populated state.
        """
        from _generate_docs import _validators_package as v
        from _generate_docs._state import (
            default_state,
            default_package_record,
        )
        from _generate_docs._render import _TODO_SCRIPTS

        state = default_state()
        pkg = default_package_record("web", "apps/web")
        pkg["overview"] = "X"
        pkg["directory_tree"] = "src/"
        pkg["primary_language"] = "ts"
        pkg["scripts"] = {"build": "make build"}
        pkg["exports"] = [{
            "kind": "function", "name": "f", "signature": None,
            "description": "x",
            "code": {
                "language": "ts", "snippet": "x",
                "cite": {"file": "src/f.ts", "start": 1, "end": 1},
            },
        }]
        pkg["dependencies"] = [{
            "kind": "external", "name": "react", "version": "1",
            "purpose": "ui", "consumer_locations": [],
        }]
        state["packages"]["apps/web"] = pkg

        # Patch render to simulate a regression where scripts are dropped.
        original = v.render_package_skeleton

        def buggy_render(s, p):
            text = original(s, p)
            # Replace the scripts table with the optional-section [TODO]
            # to mimic a render path that lost the data.
            return text.split("## Scripts")[0] + "## Scripts\n\n" + _TODO_SCRIPTS + "\n"

        v.render_package_skeleton = buggy_render
        try:
            errors = v.validate_package(state, "apps/web", self.project_root)
        finally:
            v.render_package_skeleton = original
        rule_names = {e["rule"] for e in errors}
        self.assertIn("optional-section-render-bug", rule_names)
        # The error names the offending field.
        bug_errors = [e for e in errors if e["rule"] == "optional-section-render-bug"]
        self.assertEqual(bug_errors[0]["field"], "scripts")

    def test_optional_render_bug_silent_when_state_empty(self):
        """Empty state + [TODO] in render is a LEGITIMATE optional skip.

        The defense-in-depth rule must NOT fire here — the schema
        declares scripts/hazards/usage_example/consumer_pattern
        optional and a doc that omits them is valid.
        """
        self._fill_minimum_valid()
        # All four optional fields stay empty; render naturally emits
        # their [TODO] markers.
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # No optional-section-render-bug surfaced even though the
        # rendered skeleton contains the optional [TODO]s.
        self.assertNotIn(b"optional-section-render-bug", proc.stderr)


# ---------------------------------------------------------------------------
# InternalDepResolutionTests
#
# Third resolution path: `<devforge>/init.yaml`'s `packages_detected[]`.
# Previous behavior relied on (1) registered packages in current state +
# (2) on-disk dir at `<project_root>/<dep_name>`. Both fail when an LLM
# is documenting one package at a time AND the monorepo nests packages
# inside a workspace folder (e.g., testForge20's
# `db-cse-ui-strata/packages/pkg-cse-core`). The new check uses the
# init.yaml that /init-forge already writes.
#
# Note: the validator's regex parser is BEST EFFORT — malformed init.yaml
# silently falls through to existing checks. Tests here cover happy-path
# resolution + the malformed/missing fall-through.
# ---------------------------------------------------------------------------


class InternalDepResolutionTests(_RenderTestBase):

    def _write_init_yaml(self, content):
        """Write `.devforge/init.yaml` with `content` (bytes-or-str)."""
        path = self.devforge_dir / "init.yaml"
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")

    def _fill_minimum_valid(self, src_lines=None):
        """Mirror ValidatePackageTests._fill_minimum_valid but local
        (the base class is _RenderTestBase, which doesn't provide it).

        Registers `apps/web` with the minimum required content so adding
        a single internal dep is the only thing standing between state
        and a passing validate-package call.
        """
        if src_lines is None:
            src_lines = [
                "export function fetchUser(id) {",
                "  return db.users.get(id);",
                "}",
            ]
        self._write_source("src/api.ts", src_lines)
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "Web.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/\n  api.ts")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "TypeScript")
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "fetchUser",
                  "--kind", "function",
                  "--signature", "",
                  "--description", "Fetches a user.",
                  "--language", "ts",
                  "--code-snippet", "\n".join(src_lines),
                  "--cite-file", "src/api.ts",
                  "--cite-start", "1", "--cite-end", "3")

    # -- Happy-path resolution via init.yaml --------------------------

    def test_internal_dep_resolves_against_init_yaml_packages_detected_basename(self):
        # Init.yaml has `db-cse-ui-strata/packages/pkg-cse-core`.
        # Internal dep is registered with bare basename `pkg-cse-core`
        # and should resolve via init.yaml even though no directory
        # exists at <project_root>/pkg-cse-core and no other package
        # is registered.
        self._fill_minimum_valid()
        self._write_init_yaml(
            "version: 1\n"
            "workspace_mode: wrapper\n"
            "project_root: db-cse-ui-strata\n"
            "project_state: brownfield\n"
            "default_branch: dev\n"
            "packages_detected:\n"
            "  - path: db-cse-ui-strata/packages/pkg-cse-core\n"
            "    manifest: package.json\n"
        )
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "pkg-cse-core",
                  "--kind", "internal", "--version", "",
                  "--purpose", "Core lib.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Sanity: the internal-dep-unresolved error did NOT fire.
        self.assertNotIn(b"internal-dep-unresolved", proc.stderr)

    def test_internal_dep_resolves_against_init_yaml_packages_detected_fullpath(self):
        # Same fixture, but the LLM registered the dep using the full
        # workspace-relative path verbatim. Match on full path string.
        self._fill_minimum_valid()
        self._write_init_yaml(
            "version: 1\n"
            "workspace_mode: wrapper\n"
            "project_root: db-cse-ui-strata\n"
            "project_state: brownfield\n"
            "default_branch: dev\n"
            "packages_detected:\n"
            "  - path: db-cse-ui-strata/packages/pkg-cse-core\n"
            "    manifest: package.json\n"
        )
        self._run("add-package-dep",
                  "--path", "apps/web",
                  "--name", "db-cse-ui-strata/packages/pkg-cse-core",
                  "--kind", "internal", "--version", "",
                  "--purpose", "Core lib.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn(b"internal-dep-unresolved", proc.stderr)

    # -- Fall-through behavior ----------------------------------------

    def test_internal_dep_unresolved_when_init_yaml_missing_and_no_other_match(self):
        # No init.yaml; no registered sibling package; no on-disk dir.
        # The error must surface (the new check is additive, not a
        # silent skip).
        self._fill_minimum_valid()
        # Sanity: ensure init.yaml is genuinely absent.
        self.assertFalse((self.devforge_dir / "init.yaml").exists())
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "pkg-no-match",
                  "--kind", "internal", "--version", "",
                  "--purpose", "Should fail.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"internal-dep-unresolved", proc.stderr)
        self.assertIn(b"pkg-no-match", proc.stderr)

    def test_internal_dep_unresolved_when_init_yaml_missing_path_doesnt_match(self):
        # init.yaml present but no `pkg-cse-core` entry. Existing
        # checks also fail. The error must still surface.
        self._fill_minimum_valid()
        self._write_init_yaml(
            "version: 1\n"
            "workspace_mode: wrapper\n"
            "project_root: db-cse-ui-strata\n"
            "project_state: brownfield\n"
            "default_branch: dev\n"
            "packages_detected:\n"
            "  - path: db-cse-ui-strata/packages/pkg-something-else\n"
            "    manifest: package.json\n"
        )
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "pkg-cse-core",
                  "--kind", "internal", "--version", "",
                  "--purpose", "Should fail.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"internal-dep-unresolved", proc.stderr)
        self.assertIn(b"pkg-cse-core", proc.stderr)

    def test_init_yaml_malformed_falls_back_to_existing_checks(self):
        # Garbage init.yaml (not even close to a yaml file). The
        # regex extractor must NOT raise; it just returns []. The
        # other two checks run and (since they also fail) the error
        # surfaces normally — proves malformed input degrades
        # gracefully without crashing the validator.
        self._fill_minimum_valid()
        self._write_init_yaml(
            "<<< this is not yaml >>>\n"
            "@@@ binary garbage @@@\n"
            "{[(unmatched delimiters\n"
        )
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "pkg-cse-core",
                  "--kind", "internal", "--version", "",
                  "--purpose", "Should fail.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"internal-dep-unresolved", proc.stderr)

    # -- Existing checks unaffected by the new third path ------------

    def test_existing_state_match_still_works_when_init_yaml_present(self):
        # Init.yaml exists but doesn't contain the dep. The dep is a
        # registered package's name. Resolution must come from check
        # #1 (registered packages) — proves the new check is additive.
        self._fill_minimum_valid()
        self._write_init_yaml(
            "version: 1\n"
            "workspace_mode: standalone\n"
            "project_root: .\n"
            "project_state: brownfield\n"
            "default_branch: main\n"
            "packages_detected:\n"
            "  - path: some-other-pkg\n"
            "    manifest: package.json\n"
        )
        self._run("add-package",
                  "--path", "packages/shared", "--name", "@workspace/shared")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "@workspace/shared",
                  "--kind", "internal", "--version", "",
                  "--purpose", "Shared utils.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_existing_directory_match_still_works_when_init_yaml_present(self):
        # Init.yaml exists but doesn't contain the dep. The dep DOES
        # match an on-disk directory under project_root. Resolution
        # must come from check #2.
        self._fill_minimum_valid()
        self._write_init_yaml(
            "version: 1\n"
            "workspace_mode: standalone\n"
            "project_root: .\n"
            "project_state: brownfield\n"
            "default_branch: main\n"
            "packages_detected: []\n"
        )
        (self.project_root / "packages" / "shared").mkdir(parents=True)
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "packages/shared",
                  "--kind", "internal", "--version", "",
                  "--purpose", "Shared utils.")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    # -- Synthetic testForge20 reproducer -----------------------------

    def test_synthetic_testforge20_shape_resolves_all_internal_deps(self):
        # Reproduces the exact scenario from the bug report: 19
        # workspace-internal deps registered against `apps/app-web`,
        # all of which live inside `db-cse-ui-strata/packages/<name>`
        # in init.yaml, none of which are registered as packages and
        # none of which exist as `<project_root>/<dep_name>`. Before
        # the fix, this produced 19 errors. After the fix, 0 errors.
        self._fill_minimum_valid()
        nested_pkgs = [
            "pkg-cse-core",
            "pkg-cse-quote",
            "pkg-cse-identity",
            "pkg-cse-billing",
            "pkg-cse-claims",
            "pkg-cse-policy",
            "pkg-cse-broker",
            "pkg-cse-payment",
            "pkg-cse-document",
            "pkg-cse-notification",
            "pkg-cse-audit",
            "pkg-cse-config",
            "pkg-cse-shared",
            "pkg-cse-ui",
            "pkg-cse-form",
            "pkg-cse-validation",
            "pkg-cse-data",
            "pkg-cse-event",
            "pkg-cse-storage",
        ]
        init_lines = [
            "version: 1",
            "workspace_mode: wrapper",
            "project_root: db-cse-ui-strata",
            "project_state: brownfield",
            "default_branch: dev",
            "packages_detected:",
        ]
        for name in nested_pkgs:
            init_lines.append(
                "  - path: db-cse-ui-strata/packages/{0}".format(name)
            )
            init_lines.append("    manifest: package.json")
        # Plus app-web (the package being documented) lives under the
        # workspace too — round out the fixture realistically.
        init_lines.append("  - path: db-cse-ui-strata/apps/app-web")
        init_lines.append("    manifest: package.json")
        self._write_init_yaml("\n".join(init_lines) + "\n")

        for name in nested_pkgs:
            self._run("add-package-dep",
                      "--path", "apps/web", "--name", name,
                      "--kind", "internal", "--version", "",
                      "--purpose", "Workspace lib.")

        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn(b"internal-dep-unresolved", proc.stderr)


# ---------------------------------------------------------------------------
# InternalDepResolutionUnitTests
#
# Pure-function tests for `_load_packages_detected_paths` and
# `_resolve_internal_dep`. These run without the full CLI roundtrip so
# regressions in the helpers themselves surface fast and with precise
# stack traces.
# ---------------------------------------------------------------------------


class InternalDepResolutionUnitTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name) / ".devforge"
        self.devforge_dir.mkdir(parents=True)
        self.project_root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_init_yaml(self, content):
        (self.devforge_dir / "init.yaml").write_text(
            content, encoding="utf-8"
        )

    def test_load_paths_returns_empty_when_init_yaml_missing(self):
        from _generate_docs._validators import _load_packages_detected_paths
        self.assertEqual(
            _load_packages_detected_paths(self.devforge_dir), []
        )

    def test_load_paths_extracts_path_values(self):
        from _generate_docs._validators import _load_packages_detected_paths
        self._write_init_yaml(
            "packages_detected:\n"
            "  - path: workspace/packages/foo\n"
            "    manifest: package.json\n"
            "  - path: workspace/packages/bar\n"
            "    manifest: package.json\n"
        )
        paths = _load_packages_detected_paths(self.devforge_dir)
        self.assertEqual(
            paths,
            ["workspace/packages/foo", "workspace/packages/bar"],
        )

    def test_load_paths_handles_quoted_path(self):
        # init_helper quotes paths that contain special chars; the
        # validator must accept the quoted form too.
        from _generate_docs._validators import _load_packages_detected_paths
        self._write_init_yaml(
            "packages_detected:\n"
            "  - path: \"workspace/has space/foo\"\n"
            "    manifest: package.json\n"
        )
        self.assertEqual(
            _load_packages_detected_paths(self.devforge_dir),
            ["workspace/has space/foo"],
        )

    def test_load_paths_returns_empty_for_garbage(self):
        from _generate_docs._validators import _load_packages_detected_paths
        self._write_init_yaml("totally not yaml at all\n")
        self.assertEqual(
            _load_packages_detected_paths(self.devforge_dir), []
        )

    def test_load_paths_strips_inline_comment(self):
        # Hand-edited init.yaml with a trailing comment. init_helper
        # never emits comments but the helper should be tolerant.
        from _generate_docs._validators import _load_packages_detected_paths
        self._write_init_yaml(
            "packages_detected:\n"
            "  - path: workspace/packages/foo # primary\n"
            "    manifest: package.json\n"
        )
        self.assertEqual(
            _load_packages_detected_paths(self.devforge_dir),
            ["workspace/packages/foo"],
        )

    def test_resolve_against_basename_in_init_yaml(self):
        from _generate_docs._validators import _resolve_internal_dep
        self._write_init_yaml(
            "packages_detected:\n"
            "  - path: workspace/packages/foo\n"
            "    manifest: package.json\n"
        )
        state = {"packages": {}}
        self.assertTrue(_resolve_internal_dep(
            "foo", state, self.project_root, self.devforge_dir,
        ))

    def test_resolve_against_full_path_in_init_yaml(self):
        from _generate_docs._validators import _resolve_internal_dep
        self._write_init_yaml(
            "packages_detected:\n"
            "  - path: workspace/packages/foo\n"
            "    manifest: package.json\n"
        )
        state = {"packages": {}}
        self.assertTrue(_resolve_internal_dep(
            "workspace/packages/foo", state, self.project_root, self.devforge_dir,
        ))

    def test_resolve_returns_false_when_no_match(self):
        from _generate_docs._validators import _resolve_internal_dep
        self._write_init_yaml(
            "packages_detected:\n"
            "  - path: workspace/packages/foo\n"
            "    manifest: package.json\n"
        )
        state = {"packages": {}}
        self.assertFalse(_resolve_internal_dep(
            "nonexistent", state, self.project_root, self.devforge_dir,
        ))

    def test_resolve_check_1_takes_precedence(self):
        # Registered package match is the first check; init.yaml
        # presence/absence shouldn't matter.
        from _generate_docs._validators import _resolve_internal_dep
        state = {"packages": {"path/x": {"name": "@workspace/x"}}}
        self.assertTrue(_resolve_internal_dep(
            "@workspace/x", state, self.project_root, self.devforge_dir,
        ))

    def test_resolve_check_2_directory_match(self):
        from _generate_docs._validators import _resolve_internal_dep
        (self.project_root / "shared").mkdir()
        state = {"packages": {}}
        self.assertTrue(_resolve_internal_dep(
            "shared", state, self.project_root, self.devforge_dir,
        ))


# ---------------------------------------------------------------------------
# RenderPackageDocTests (sub-step 1.2b)
# ---------------------------------------------------------------------------


class RenderPackageDocTests(_RenderTestBase):

    def _fill_minimum_valid(self):
        src_lines = [
            "export function fetchUser(id) {",
            "  return db.users.get(id);",
            "}",
        ]
        self._write_source("src/api.ts", src_lines)
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "Web.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/\n  api.ts")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "TypeScript")
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "fetchUser",
                  "--kind", "function",
                  "--signature", "",
                  "--description", "Fetches a user.",
                  "--language", "ts",
                  "--code-snippet", "\n".join(src_lines),
                  "--cite-file", "src/api.ts",
                  "--cite-start", "1", "--cite-end", "3")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "18",
                  "--purpose", "UI lib.")

    def test_valid_package_writes_md_and_removes_skeleton(self):
        self._fill_minimum_valid()
        # Pre-create a skeleton so the cleanup path is exercised.
        self._run("render-package-skeleton", "--path", "apps/web")
        skeleton = self.project_root / "docs" / "apps/web" / "index.md.skeleton"
        self.assertTrue(skeleton.exists())
        proc = self._run("render-package-doc", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        md_path = self.project_root / "docs" / "apps/web" / "index.md"
        self.assertTrue(md_path.exists())
        self.assertFalse(skeleton.exists(), "skeleton should be removed")
        text = md_path.read_text(encoding="utf-8")
        # Required-field TODOs must NOT appear in the final doc.
        self.assertNotIn("[TODO: 1-2 paragraphs", text)
        self.assertNotIn("[TODO: ascii tree", text)
        self.assertNotIn("[TODO: enumerate package exports", text)
        self.assertNotIn("[TODO: enumerate via add-package-dep", text)
        # Required Tech Stack [TODO] (primary_language) must not appear.
        self.assertIn("TypeScript", text)
        # Optional-section LLM-targeted setter-name TODOs must also NOT
        # appear in the final doc (mode="final" renders _(none)_ instead).
        self.assertNotIn("add-package-hazard", text)
        self.assertNotIn("set-package-usage-example", text)
        self.assertNotIn("set-package-consumer-pattern", text)
        self.assertNotIn("add-package-script", text)

    def test_validation_failure_blocks_md_write(self):
        # Empty package: validation fails, .md must NOT be written.
        self._add_pkg()
        # Create a stale skeleton that should be retained on failure.
        self._run("render-package-skeleton", "--path", "apps/web")
        skeleton = self.project_root / "docs" / "apps/web" / "index.md.skeleton"
        self.assertTrue(skeleton.exists())
        proc = self._run("render-package-doc", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        md_path = self.project_root / "docs" / "apps/web" / "index.md"
        self.assertFalse(md_path.exists(), ".md should NOT be written")
        self.assertTrue(skeleton.exists(), "skeleton should be retained")
        self.assertIn(b"validation failed", proc.stderr)

    def test_missing_package_errors(self):
        proc = self._run("render-package-doc", "--path", "apps/missing")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"not registered", proc.stderr)

    def test_doc_render_idempotent(self):
        self._fill_minimum_valid()
        self._run("render-package-doc", "--path", "apps/web")
        md_path = self.project_root / "docs" / "apps/web" / "index.md"
        first = md_path.read_bytes()
        self._run("render-package-doc", "--path", "apps/web")
        second = md_path.read_bytes()
        self.assertEqual(first, second)

    def test_doc_no_skeleton_present_still_succeeds(self):
        # Run render-package-doc without a pre-existing skeleton.
        self._fill_minimum_valid()
        proc = self._run("render-package-doc", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        md_path = self.project_root / "docs" / "apps/web" / "index.md"
        self.assertTrue(md_path.exists())


# ---------------------------------------------------------------------------
# CitationDisciplineRegressionTests
#
# Regression coverage for a HIGH-severity bug report: a real run produced
# a doc whose `consumer_pattern.code.snippet` differed from the cited
# source slice on a single inner line (`either` vs `import`), but
# `validate-package` exited 0. The mechanical citation-discipline rule is
# explicitly designed to make exactly this impossible.
#
# Investigation found the validate logic itself was sound for the basic
# path; these tests pin down the scenarios so future edits cannot
# regress the guarantee. Specifically they cover:
#
#   - The exact reproducer (single-word swap on an inner line of a
#     multi-line consumer_pattern snippet).
#   - The same kind of swap, but for `usage_example` (parallel field,
#     same code path, different setter).
#   - A "soft truthiness" hardening: a corrupted state record where
#     `consumer_pattern` / `usage_example` are present but malformed
#     (empty dict, non-dict scalar) used to slip past the falsy-skip
#     gate; validate now reports `*-malformed` explicitly.
#   - Multi-package isolation: validate-package on package A must
#     verify A's snippets even when a sibling package B has bad data.
# ---------------------------------------------------------------------------


class CitationDisciplineRegressionTests(_RenderTestBase):

    def _fill_minimum_for_consumer_pattern(self):
        """Set up a package with all required fields + a real source
        file at src/foo.ts:1-4 ready to host a consumer_pattern."""
        self._write_source("src/foo.ts", [
            "line1",
            "line2",
            "import real",
            "line4",
        ])
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "X.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "ts")
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "f", "--kind", "function",
                  "--signature", "", "--description", "X.",
                  "--language", "ts",
                  "--code-snippet", "line1\nline2\nimport real\nline4",
                  "--cite-file", "src/foo.ts",
                  "--cite-start", "1", "--cite-end", "4")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "1",
                  "--purpose", "UI.")

    def test_consumer_pattern_inner_line_swap_rejected(self):
        """Exact reproducer from the user's report: registered snippet
        differs from source by one word on an inner line."""
        self._fill_minimum_for_consumer_pattern()
        # Register consumer_pattern with WRONG line 3 ('either' instead
        # of 'import' — verbatim shape of the user's reported bug).
        proc = self._run("set-package-consumer-pattern",
                         "--path", "apps/web", "--language", "ts",
                         "--code-snippet",
                         "line1\nline2\neither real\nline4",
                         "--cite-file", "src/foo.ts",
                         "--cite-start", "1", "--cite-end", "4")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(
            proc.returncode, 2,
            "validate-package PASSED a consumer_pattern snippet/source "
            "mismatch (citation discipline must reject this)",
        )
        self.assertIn(b"snippet-verbatim", proc.stderr)
        self.assertIn(b"consumer_pattern", proc.stderr)
        # Diff fragment must surface both expected and actual lines so
        # the LLM can see where the drift is.
        self.assertIn(b"expected (from source)", proc.stderr)
        self.assertIn(b"import real", proc.stderr)
        self.assertIn(b"either real", proc.stderr)

    def test_usage_example_inner_line_swap_rejected(self):
        """Same shape of bug, parallel field. Iterates the second
        optional CodeBlock through the same code path as
        consumer_pattern."""
        self._fill_minimum_for_consumer_pattern()
        proc = self._run("set-package-usage-example",
                         "--path", "apps/web", "--language", "ts",
                         "--code-snippet",
                         "line1\nline2\neither real\nline4",
                         "--cite-file", "src/foo.ts",
                         "--cite-start", "1", "--cite-end", "4")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"snippet-verbatim", proc.stderr)
        self.assertIn(b"usage_example", proc.stderr)

    def test_consumer_pattern_one_char_swap_rejected(self):
        """Tightest possible mismatch: a single-character change inside
        the cited slice. Confirms the comparator is byte-exact (modulo
        the documented whitespace normalization rules) — no fuzzy
        match, no diff threshold."""
        self._fill_minimum_for_consumer_pattern()
        proc = self._run("set-package-consumer-pattern",
                         "--path", "apps/web", "--language", "ts",
                         "--code-snippet",
                         # Source is 'import real'; we register 'import realX'.
                         "line1\nline2\nimport realX\nline4",
                         "--cite-file", "src/foo.ts",
                         "--cite-start", "1", "--cite-end", "4")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"snippet-verbatim", proc.stderr)

    def test_consumer_pattern_corrupted_state_empty_dict_rejected(self):
        """Anti-pattern #2 hardening: a falsy-non-None consumer_pattern
        (empty dict) used to slip past the truthiness gate in
        `_check_all_codeblocks` and thus skip the snippet check
        silently. After the fix, the helper surfaces an explicit
        `consumer-pattern-malformed` error.

        Tested at the `_check_all_codeblocks` boundary because a
        malformed optional CodeBlock also breaks the downstream
        `render_package_skeleton` call inside `_check_no_todos` —
        rendering a non-dict CodeBlock is a separate hardening
        concern outside this fix's scope."""
        from _generate_docs._validators import _check_all_codeblocks

        self._fill_minimum_for_consumer_pattern()
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        pkg = state["packages"]["apps/web"]
        pkg["consumer_pattern"] = {}
        errors = _check_all_codeblocks(pkg, self.project_root)
        rules = {e["rule"] for e in errors}
        self.assertIn("consumer-pattern-malformed", rules)

    def test_usage_example_corrupted_state_non_dict_rejected(self):
        """Parallel hardening for usage_example."""
        from _generate_docs._validators import _check_all_codeblocks

        self._fill_minimum_for_consumer_pattern()
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        pkg = state["packages"]["apps/web"]
        pkg["usage_example"] = "not a dict"
        errors = _check_all_codeblocks(pkg, self.project_root)
        rules = {e["rule"] for e in errors}
        self.assertIn("usage-example-malformed", rules)

    def test_none_consumer_pattern_does_not_emit_error(self):
        """Counterpart sanity: None (the schema default) is the legitimate
        "absent" signal and must NOT trigger the malformed-error path."""
        from _generate_docs._validators import _check_all_codeblocks

        self._fill_minimum_for_consumer_pattern()
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        pkg = state["packages"]["apps/web"]
        self.assertIsNone(pkg["consumer_pattern"])
        errors = _check_all_codeblocks(pkg, self.project_root)
        rules = {e["rule"] for e in errors}
        self.assertNotIn("consumer-pattern-malformed", rules)
        self.assertNotIn("snippet-verbatim", rules)

    def test_multi_package_isolation_does_not_mask_mismatch(self):
        """Validate-package scopes to the named package: a sibling
        package's clean state must not let the named package's
        mismatch slip through."""
        self._fill_minimum_for_consumer_pattern()
        # Register a second, fully-valid package.
        self._write_source("packages/shared/src/util.ts", ["x", "y", "z"])
        self._run("add-package", "--path", "packages/shared", "--name", "shared")
        self._run("set-package-overview",
                  "--path", "packages/shared", "--text", "S.")
        self._run("set-package-tree",
                  "--path", "packages/shared", "--text", "src/")
        self._run("set-package-language",
                  "--path", "packages/shared", "--value", "ts")
        self._run("add-package-export",
                  "--path", "packages/shared", "--name", "g",
                  "--kind", "function",
                  "--signature", "", "--description", "X.",
                  "--language", "ts", "--code-snippet", "x\ny\nz",
                  "--cite-file", "packages/shared/src/util.ts",
                  "--cite-start", "1", "--cite-end", "3")
        self._run("add-package-dep",
                  "--path", "packages/shared", "--name", "lodash",
                  "--kind", "external", "--version", "4",
                  "--purpose", "Utils.")
        # Now corrupt apps/web's consumer_pattern.
        self._run("set-package-consumer-pattern",
                  "--path", "apps/web", "--language", "ts",
                  "--code-snippet",
                  "line1\nline2\neither real\nline4",
                  "--cite-file", "src/foo.ts",
                  "--cite-start", "1", "--cite-end", "4")
        # Validate apps/web — must FAIL.
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"snippet-verbatim", proc.stderr)
        # Validate packages/shared — must PASS (sibling unaffected).
        proc = self._run("validate-package", "--path", "packages/shared")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_validate_idempotent_on_mismatch(self):
        """Repeated validate-package invocations on the same mismatched
        state must produce the same error list. Anti-pattern #6 sanity."""
        self._fill_minimum_for_consumer_pattern()
        self._run("set-package-consumer-pattern",
                  "--path", "apps/web", "--language", "ts",
                  "--code-snippet",
                  "line1\nline2\neither real\nline4",
                  "--cite-file", "src/foo.ts",
                  "--cite-start", "1", "--cite-end", "4")
        proc1 = self._run("validate-package", "--path", "apps/web")
        proc2 = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc1.returncode, 2)
        self.assertEqual(proc1.returncode, proc2.returncode)
        self.assertEqual(proc1.stderr, proc2.stderr)


# ---------------------------------------------------------------------------
# RenderHelpAndCLISurfaceTests — verify the new subcommands appear in --help.
# ---------------------------------------------------------------------------


class NewSubcommandsInHelpTests(_EnvIsolationMixin, unittest.TestCase):

    def test_help_lists_new_subcommands(self):
        proc = _run_cli(self.devforge_dir, "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for sub in (
            b"set-package-consumer-pattern",
            b"render-package-skeleton",
            b"validate-package",
            b"render-package-doc",
        ):
            self.assertIn(sub, proc.stdout)


# ---------------------------------------------------------------------------
# Phase2SpecSequenceTests — regression for the testForge20 2026-05-01 bug.
#
# Symptom: rendered Tech Stack showed `Framework | —` and `Build Tool | —`
# even though Phase 2 of `src/commands/generate-docs/main.md` instructs the
# LLM to invoke `set-package-framework "Vue 3"` and `set-package-build-tool
# vite`. State on disk had framework=None, build_tool=None, scripts={};
# language was set, all Phase 3 setters worked.
#
# Diagnosis: setters work correctly in isolation (existing tests prove this).
# The state shape "language=set, framework/build_tool/scripts=unset, deps/
# exports/hazards=set" is reachable only when the LLM SKIPPED Phase 2 steps
# 3-6 entirely — not a helper bug. Root cause is an upstream spec ambiguity
# in the Phase 0 "Resume" branch: it tells the LLM to "skip Phase 2's
# add-package and any scalar set-* already populated", which a strict reading
# could interpret as "skip the whole Phase 2".
#
# This regression test enforces the post-fix invariant: when ALL Phase 2
# steps run end-to-end as written in main.md lines 61-66, every targeted
# field is persisted to state. If a future setter regression breaks this,
# the test fails BEFORE it reaches the LLM in production.
# ---------------------------------------------------------------------------


class Phase2SpecSequenceTests(_EnvIsolationMixin, unittest.TestCase):
    """Mirror the exact ordered subcommand sequence from
    `src/commands/generate-docs/main.md` Phase 2, then assert every targeted
    field of the package record is populated."""

    def _project_root_with_manifest(self, scripts):
        # Build a tempdir with a package.json so extract-package-scripts
        # can succeed; mirrors how the helper resolves the manifest.
        proot = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(proot, ignore_errors=True))
        pkg_dir = proot / "db-cse-ui-strata" / "apps" / "app-web"
        pkg_dir.mkdir(parents=True)
        manifest = {
            "name": "app-web",
            "scripts": scripts,
            "dependencies": {"vue": "^3.3.4"},
            "devDependencies": {"vite": "^3.2.0", "typescript": "^5.0.0"},
        }
        (pkg_dir / "package.json").write_text(
            json.dumps(manifest), encoding="utf-8",
        )
        return proot

    def test_phase2_full_sequence_persists_all_fields(self):
        """Step-by-step replay of main.md Phase 2:

            1. add-package
            2. set-package-language
            3. set-package-framework
            4. set-package-build-tool
            5. extract-package-scripts (read-only; capture stdout)
            6. add-package-script (one per script in step-5 output)

        After step 6, the package record must have:
          - primary_language, framework, build_tool all set
          - scripts dict matching the manifest

        Failure of this test means the Phase 2 invocation chain has
        regressed in a way that produces the testForge20 2026-05-01
        bug shape (em-dash Tech Stack, [TODO] Scripts) even though
        each setter passes its isolated test.
        """
        scripts = {
            "build": "vite build",
            "dev": "vite",
            "test": "vitest",
        }
        proot = self._project_root_with_manifest(scripts)
        path = "db-cse-ui-strata/apps/app-web"

        # Step 1: add-package.
        proc = _run_cli(
            self.devforge_dir, "add-package",
            "--path", path, "--name", "app-web",
            project_root=proot, cwd=proot,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        # Step 2: set-package-language.
        proc = _run_cli(
            self.devforge_dir, "set-package-language",
            "--path", path, "--value", "typescript",
            project_root=proot, cwd=proot,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        # Step 3: set-package-framework.
        proc = _run_cli(
            self.devforge_dir, "set-package-framework",
            "--path", path, "--value", "Vue 3",
            project_root=proot, cwd=proot,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        # Step 4: set-package-build-tool.
        proc = _run_cli(
            self.devforge_dir, "set-package-build-tool",
            "--path", path, "--value", "vite",
            project_root=proot, cwd=proot,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        # Step 5: extract-package-scripts (capture JSON stdout).
        # The subcommand resolves --path against CWD, so invoke from
        # project root exactly as the LLM does in the spec.
        proc = _run_cli(
            self.devforge_dir, "extract-package-scripts",
            "--path", path,
            project_root=proot, cwd=proot,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        extracted = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(extracted, scripts)

        # Step 6: add-package-script (one call per pair).
        for name, command in extracted.items():
            proc = _run_cli(
                self.devforge_dir, "add-package-script",
                "--path", path,
                "--script-name", name,
                "--command", command,
                project_root=proot, cwd=proot,
            )
            self.assertEqual(
                proc.returncode, 0,
                "add-package-script {0!r} failed: {1}".format(
                    name, proc.stderr,
                ),
            )

        # Assert: every targeted field of the record is populated.
        rec = self._read_state()["packages"][path]
        self.assertEqual(rec["primary_language"], "typescript")
        self.assertEqual(rec["framework"], "Vue 3")
        self.assertEqual(rec["build_tool"], "vite")
        self.assertEqual(rec["scripts"], scripts)

    def test_phase2_render_skeleton_has_no_em_dash_tech_stack(self):
        """Cross-check the render: when Phase 2 sets framework + build_tool,
        the rendered skeleton's Tech Stack table shows the values, not the
        `—` em-dash placeholder. This is the user-visible symptom that
        triggered the original investigation.
        """
        proot = self._project_root_with_manifest({"build": "vite build"})
        path = "db-cse-ui-strata/apps/app-web"

        for args in (
            ("add-package", "--path", path, "--name", "app-web"),
            ("set-package-language", "--path", path, "--value", "typescript"),
            ("set-package-framework", "--path", path, "--value", "Vue 3"),
            ("set-package-build-tool", "--path", path, "--value", "vite"),
        ):
            proc = _run_cli(
                self.devforge_dir, *args, project_root=proot, cwd=proot,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

        # render-package-skeleton writes to docs/<path>/index.md.skeleton
        # under DEVFORGE_PROJECT_ROOT.
        proc = _run_cli(
            self.devforge_dir, "render-package-skeleton",
            "--path", path,
            project_root=proot, cwd=proot,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        skel = (proot / "docs" / path / "index.md.skeleton").read_text(
            encoding="utf-8",
        )
        # Tech Stack rows: Vue 3 + vite present, no em-dash on those rows.
        self.assertIn("| Framework | Vue 3 |", skel)
        self.assertIn("| Build Tool | vite |", skel)
        # Sanity: the em-dash row would look like this if the setter failed.
        self.assertNotIn("| Framework | — |", skel)
        self.assertNotIn("| Build Tool | — |", skel)


# ---------------------------------------------------------------------------
# RenderHtmlEscapeTests — regression for prose fields containing HTML-looking
# tokens (e.g. TypeScript generics ``DeepReadonly<Ref<S>>``) that markdown
# renderers would otherwise interpret as raw HTML. ``<S>`` is the deprecated
# HTML strikethrough tag, which struck through entire Hazards/Usage sections
# in the rendered docs before this fix.
# ---------------------------------------------------------------------------


class RenderHtmlEscapeTests(_RenderTestBase):

    def _render_and_read(self):
        proc = self._run("render-package-skeleton", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return (
            self.project_root / "docs" / "apps/web" / "index.md.skeleton"
        ).read_text(encoding="utf-8")

    def _slice_section(self, text, heading):
        """Return the body of the top-level ``## <heading>`` section.

        Splits on ``\\n## `` (with a trailing space) so subsection
        headings (``### ...``) inside the section are not treated as
        section terminators.
        """
        marker = "## " + heading
        head = text.split(marker, 1)[1]
        return head.split("\n## ", 1)[0]

    def test_overview_with_angle_brackets_escaped(self):
        self._add_pkg()
        self._run(
            "set-package-overview",
            "--path", "apps/web",
            "--text", "Uses DeepReadonly<Ref<S>> generics.",
        )
        text = self._render_and_read()
        # Escaped form present.
        self.assertIn("DeepReadonly&lt;Ref&lt;S&gt;&gt;", text)
        # The literal ``<S>`` token must NOT appear in the prose body
        # (would make markdown renderers strike-through everything).
        # Constrain the check to the Overview block to avoid coincidental
        # matches in unrelated sections.
        overview_block = self._slice_section(text, "Overview")
        self.assertNotIn("<S>", overview_block)
        self.assertNotIn("<Ref<S>>", overview_block)

    def test_hazard_description_with_generics_escaped(self):
        self._add_pkg()
        # Required setters so render produces a non-stub Overview, etc.,
        # but they don't matter for the hazard assertion.
        self._run(
            "add-package-hazard",
            "--path", "apps/web",
            "--category", "naming",
            "--description",
            "Both DeepReadonly<Ref<S>> and Ref<S> coexist.",
        )
        text = self._render_and_read()
        hazards_block = self._slice_section(text, "Hazards")
        self.assertIn("DeepReadonly&lt;Ref&lt;S&gt;&gt;", hazards_block)
        self.assertIn("Ref&lt;S&gt;", hazards_block)
        self.assertNotIn("<S>", hazards_block)
        self.assertNotIn("<Ref<S>>", hazards_block)

    def test_dependency_purpose_with_html_chars_escaped(self):
        self._add_pkg()
        self._run(
            "add-package-dep",
            "--path", "apps/web",
            "--name", "vue", "--kind", "external", "--version", "3",
            "--purpose", "Provides Ref<S> & DeepReadonly<T> helpers.",
        )
        text = self._render_and_read()
        deps_block = self._slice_section(text, "Dependencies")
        self.assertIn("Ref&lt;S&gt;", deps_block)
        self.assertIn("DeepReadonly&lt;T&gt;", deps_block)
        self.assertIn("&amp;", deps_block)
        self.assertNotIn("Ref<S>", deps_block)
        self.assertNotIn("DeepReadonly<T>", deps_block)

    def test_export_description_with_generics_escaped(self):
        self._add_pkg()
        self._write_source(
            "src/foo.ts", ["export function foo() {}"]
        )
        self._run(
            "add-package-export",
            "--path", "apps/web",
            "--name", "foo", "--kind", "function",
            "--signature", "foo(): Ref<S>",
            "--description", "Returns a DeepReadonly<Ref<S>> wrapper.",
            "--language", "ts",
            "--code-snippet", "export function foo() {}",
            "--cite-file", "src/foo.ts",
            "--cite-start", "1", "--cite-end", "1",
        )
        text = self._render_and_read()
        exports_block = self._slice_section(text, "Main Exports")
        # Description prose is escaped.
        self.assertIn(
            "Returns a DeepReadonly&lt;Ref&lt;S&gt;&gt; wrapper.",
            exports_block,
        )
        # The description prose line itself does NOT contain ``<S>``.
        # (The signature fence and code-block fence DO contain ``<S>``;
        # those are code contexts and intentionally left unescaped.)
        for line in exports_block.splitlines():
            if line.startswith("Returns a DeepReadonly"):
                self.assertNotIn("<S>", line)
                self.assertNotIn("<Ref<S>>", line)

    def test_signature_in_fenced_block_NOT_escaped(self):
        """Signature is rendered inside a fenced code block — code
        context, must pass through verbatim."""
        self._add_pkg()
        self._write_source("src/foo.ts", ["export function foo() {}"])
        self._run(
            "add-package-export",
            "--path", "apps/web",
            "--name", "foo", "--kind", "function",
            "--signature", "foo(): Ref<S>",
            "--description", "x",
            "--language", "ts",
            "--code-snippet", "export function foo() {}",
            "--cite-file", "src/foo.ts",
            "--cite-start", "1", "--cite-end", "1",
        )
        text = self._render_and_read()
        # Literal signature appears verbatim inside the unlabeled fence
        # that precedes the description prose.
        self.assertIn("foo(): Ref<S>", text)
        # And it is NOT html-escaped.
        self.assertNotIn("foo(): Ref&lt;S&gt;", text)

    def test_code_block_snippet_NOT_escaped(self):
        """Code-block snippets render inside fenced ``` blocks. Code is
        verbatim; escaping would corrupt it."""
        self._add_pkg()
        self._write_source(
            "src/foo.ts", ["export function foo<S>() {}"]
        )
        self._run(
            "add-package-export",
            "--path", "apps/web",
            "--name", "foo", "--kind", "function",
            "--signature", "",
            "--description", "x",
            "--language", "ts",
            "--code-snippet", "export function foo<S>() {}",
            "--cite-file", "src/foo.ts",
            "--cite-start", "1", "--cite-end", "1",
        )
        text = self._render_and_read()
        # The fenced snippet contains literal ``<S>`` — verbatim.
        self.assertIn("export function foo<S>() {}", text)
        self.assertNotIn("export function foo&lt;S&gt;() {}", text)

    def test_amp_in_prose_escaped(self):
        self._add_pkg()
        self._run(
            "set-package-overview",
            "--path", "apps/web",
            "--text", "Cats & dogs.",
        )
        text = self._render_and_read()
        overview_block = self._slice_section(text, "Overview")
        self.assertIn("Cats &amp; dogs.", overview_block)
        # Bare ``&`` (not an entity reference) must not appear in the
        # rendered prose. Slice to the literal phrase to avoid false
        # positives from the HTML entities themselves.
        self.assertNotIn("Cats & dogs.", overview_block)

    def test_directory_tree_in_fence_NOT_escaped(self):
        """Directory tree renders inside a fenced ``` block — code
        context, verbatim. Tree text is unlikely to contain ``<>`` but
        we still confirm no escaping is applied so the contract is
        explicit."""
        self._add_pkg()
        self._run(
            "set-package-tree",
            "--path", "apps/web",
            # Real-world tree text rarely has angle brackets, but if
            # one slipped in (e.g. a placeholder folder name), code
            # context means it should pass through verbatim.
            "--text", "src/\n  <generated>/",
        )
        text = self._render_and_read()
        # Literal angle brackets preserved inside the fence.
        self.assertIn("<generated>/", text)
        self.assertNotIn("&lt;generated&gt;/", text)


# ===========================================================================
# Phase 3.1 — Concern-tier subcommands.
#
# 11 new CLI subcommands extending the package-tier surface to register and
# render concern-level docs nested under packages. Tests cover:
#
# - add-concern + concern scalar/append setters (idempotency, validation,
#   isolation across packages and concerns)
# - render-concern-skeleton (path shape, [TODO] slots, `## Public Surface`)
# - validate-concern (required fields, structured errors, snippet check)
# - render-concern-doc (validation gate, idempotency)
# - validate-package decomposition gate (substantive subfolders coverage,
#   architectural-role allowlist, trivial-leaf skip-list, ecosystem-agnostic
#   matching, no-`src/` no-op)
# - state migration (load pre-3.1 state without `concerns` key)
# ===========================================================================


class _ConcernTestBase(_RenderTestBase):
    """Shared helpers for concern-tier tests.

    Every test runs in an isolated tmp project root with `.devforge/`
    underneath. Most tests register a single package + a single concern
    via `_init_pkg_concern` to avoid ceremony in every test method.
    """

    def _init_pkg_concern(self, package="apps/web", concern="auth", name="web"):
        self._run("add-package", "--path", package, "--name", name)
        self._run("add-concern", "--package", package, "--concern", concern)

    def _read_state(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))


class AddConcernTests(_ConcernTestBase):

    def test_happy_path(self):
        self._add_pkg()
        proc = self._run("add-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertIn("auth", state["packages"]["apps/web"]["concerns"])
        concern = state["packages"]["apps/web"]["concerns"]["auth"]
        # Default-record shape — every field initialized.
        self.assertEqual(concern["concern_name"], "auth")
        self.assertIsNone(concern["overview"])
        self.assertIsNone(concern["directory_tree"])
        self.assertEqual(concern["public_surface"], [])
        self.assertEqual(concern["types"], [])
        self.assertEqual(concern["dependencies"], [])
        self.assertEqual(concern["hazards"], [])
        self.assertIsNone(concern["usage_example"])
        # No `consumer_pattern` field at concern level.
        self.assertNotIn("consumer_pattern", concern)

    def test_package_not_registered_rejected(self):
        proc = self._run("add-concern",
                         "--package", "apps/missing", "--concern", "auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"package not registered", proc.stderr)

    def test_duplicate_concern_rejected(self):
        self._init_pkg_concern()
        proc = self._run("add-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"already registered", proc.stderr)

    def test_control_char_rejected(self):
        # Use \x01 (any control char other than \n/\r/\t/null is rejected
        # for single-line fields). Null bytes (\x00) cannot be passed via
        # subprocess argv on POSIX, so we use a different control byte.
        self._add_pkg()
        proc = self._run("add-concern",
                         "--package", "apps/web", "--concern", "bad\x01name")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"control character", proc.stderr)

    def test_retry_after_error_creates_record(self):
        # Reject a bad-name attempt, then a clean one should succeed.
        self._add_pkg()
        bad = self._run("add-concern",
                        "--package", "apps/web", "--concern", "bad\nname")
        self.assertEqual(bad.returncode, 2)
        good = self._run("add-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(good.returncode, 0, good.stderr)
        state = self._read_state()
        self.assertEqual(
            list(state["packages"]["apps/web"]["concerns"].keys()),
            ["auth"],
        )

    def test_two_concerns_under_same_package(self):
        self._add_pkg()
        self._run("add-concern",
                  "--package", "apps/web", "--concern", "auth")
        self._run("add-concern",
                  "--package", "apps/web", "--concern", "components")
        state = self._read_state()
        self.assertEqual(
            sorted(state["packages"]["apps/web"]["concerns"].keys()),
            ["auth", "components"],
        )


class ConcernScalarSetterTests(_ConcernTestBase):

    def test_set_overview_happy(self):
        self._init_pkg_concern()
        proc = self._run("set-concern-overview",
                         "--package", "apps/web", "--concern", "auth",
                         "--text", "Auth concern.\n\nHandles login.")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(
            state["packages"]["apps/web"]["concerns"]["auth"]["overview"],
            "Auth concern.\n\nHandles login.",
        )

    def test_set_tree_happy(self):
        self._init_pkg_concern()
        proc = self._run("set-concern-tree",
                         "--package", "apps/web", "--concern", "auth",
                         "--text", "auth/\n  login.ts\n  session.ts")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        self.assertEqual(
            state["packages"]["apps/web"]["concerns"]["auth"][
                "directory_tree"
            ],
            "auth/\n  login.ts\n  session.ts",
        )

    def test_set_overview_idempotent_latest_wins(self):
        self._init_pkg_concern()
        self._run("set-concern-overview",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "First.")
        self._run("set-concern-overview",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "Second.")
        state = self._read_state()
        self.assertEqual(
            state["packages"]["apps/web"]["concerns"]["auth"]["overview"],
            "Second.",
        )

    def test_set_overview_package_not_registered(self):
        proc = self._run("set-concern-overview",
                         "--package", "apps/missing", "--concern", "auth",
                         "--text", "X.")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"package not registered", proc.stderr)

    def test_set_overview_concern_not_registered(self):
        self._add_pkg()
        proc = self._run("set-concern-overview",
                         "--package", "apps/web", "--concern", "missing",
                         "--text", "X.")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"concern", proc.stderr)
        self.assertIn(b"not registered", proc.stderr)

    def test_set_tree_control_char_rejected(self):
        # \x00 cannot pass through subprocess argv on POSIX; use \x01
        # (a generic non-newline control byte that the multiline
        # validator must still reject).
        self._init_pkg_concern()
        proc = self._run("set-concern-tree",
                         "--package", "apps/web", "--concern", "auth",
                         "--text", "auth/\x01bad")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"control character", proc.stderr)

    def test_set_usage_example_happy(self):
        self._init_pkg_concern()
        proc = self._run("set-concern-usage-example",
                         "--package", "apps/web", "--concern", "auth",
                         "--language", "ts",
                         "--code-snippet", "login()",
                         "--cite-file", "src/auth/login.ts",
                         "--cite-start", "1", "--cite-end", "1")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        ue = state["packages"]["apps/web"]["concerns"]["auth"][
            "usage_example"
        ]
        self.assertEqual(ue["language"], "ts")
        self.assertEqual(ue["snippet"], "login()")
        self.assertEqual(ue["cite"]["file"], "src/auth/login.ts")
        self.assertEqual(ue["cite"]["start"], 1)
        self.assertEqual(ue["cite"]["end"], 1)

    def test_set_usage_example_idempotent(self):
        self._init_pkg_concern()
        self._run("set-concern-usage-example",
                  "--package", "apps/web", "--concern", "auth",
                  "--language", "ts", "--code-snippet", "first()",
                  "--cite-file", "f.ts", "--cite-start", "1",
                  "--cite-end", "1")
        self._run("set-concern-usage-example",
                  "--package", "apps/web", "--concern", "auth",
                  "--language", "ts", "--code-snippet", "second()",
                  "--cite-file", "g.ts", "--cite-start", "2",
                  "--cite-end", "2")
        state = self._read_state()
        ue = state["packages"]["apps/web"]["concerns"]["auth"][
            "usage_example"
        ]
        self.assertEqual(ue["snippet"], "second()")

    def test_set_usage_example_concern_not_registered(self):
        self._add_pkg()
        proc = self._run("set-concern-usage-example",
                         "--package", "apps/web", "--concern", "missing",
                         "--language", "ts",
                         "--code-snippet", "x", "--cite-file", "f.ts",
                         "--cite-start", "1", "--cite-end", "1")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"concern", proc.stderr)


class ConcernAppendSetterTests(_ConcernTestBase):

    def test_add_export_happy(self):
        self._init_pkg_concern()
        proc = self._run("add-concern-export",
                         "--package", "apps/web", "--concern", "auth",
                         "--name", "login", "--kind", "function",
                         "--signature", "login(): void",
                         "--description", "Logs the user in.",
                         "--language", "ts", "--code-snippet", "function login() {}",
                         "--cite-file", "src/auth/login.ts",
                         "--cite-start", "1", "--cite-end", "1")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        surface = state["packages"]["apps/web"]["concerns"]["auth"][
            "public_surface"
        ]
        self.assertEqual(len(surface), 1)
        self.assertEqual(surface[0]["name"], "login")
        self.assertEqual(surface[0]["kind"], "function")

    def test_add_export_duplicate_rejected(self):
        self._init_pkg_concern()
        self._run("add-concern-export",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "x.",
                  "--language", "ts", "--code-snippet", "x",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "1")
        proc = self._run("add-concern-export",
                         "--package", "apps/web", "--concern", "auth",
                         "--name", "login", "--kind", "function",
                         "--signature", "", "--description", "x.",
                         "--language", "ts", "--code-snippet", "x",
                         "--cite-file", "src/auth/login.ts",
                         "--cite-start", "1", "--cite-end", "1")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"already registered", proc.stderr)

    def test_add_export_same_name_different_cite_allowed(self):
        # Same name, different cite-start (overload across files).
        self._init_pkg_concern()
        self._run("add-concern-export",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "x.",
                  "--language", "ts", "--code-snippet", "x",
                  "--cite-file", "a.ts", "--cite-start", "1", "--cite-end", "1")
        proc = self._run("add-concern-export",
                         "--package", "apps/web", "--concern", "auth",
                         "--name", "login", "--kind", "function",
                         "--signature", "", "--description", "y.",
                         "--language", "ts", "--code-snippet", "y",
                         "--cite-file", "b.ts", "--cite-start", "1", "--cite-end", "1")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_add_export_invalid_kind(self):
        self._init_pkg_concern()
        proc = self._run("add-concern-export",
                         "--package", "apps/web", "--concern", "auth",
                         "--name", "login", "--kind", "not-a-kind",
                         "--signature", "", "--description", "x.",
                         "--language", "ts", "--code-snippet", "x",
                         "--cite-file", "f.ts", "--cite-start", "1",
                         "--cite-end", "1")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"--kind", proc.stderr)

    def test_add_export_bad_cite_range(self):
        self._init_pkg_concern()
        proc = self._run("add-concern-export",
                         "--package", "apps/web", "--concern", "auth",
                         "--name", "login", "--kind", "function",
                         "--signature", "", "--description", "x.",
                         "--language", "ts", "--code-snippet", "x",
                         "--cite-file", "f.ts", "--cite-start", "5",
                         "--cite-end", "1")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"end", proc.stderr)

    def test_add_type_happy(self):
        self._init_pkg_concern()
        proc = self._run("add-concern-type",
                         "--package", "apps/web", "--concern", "auth",
                         "--language", "ts",
                         "--code-snippet", "type Token = { value: string }",
                         "--cite-file", "src/auth/types.ts",
                         "--cite-start", "1", "--cite-end", "1")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        types = state["packages"]["apps/web"]["concerns"]["auth"]["types"]
        self.assertEqual(len(types), 1)
        self.assertEqual(types[0]["language"], "ts")
        self.assertEqual(types[0]["cite"]["file"], "src/auth/types.ts")

    def test_add_type_duplicate_rejected(self):
        self._init_pkg_concern()
        self._run("add-concern-type",
                  "--package", "apps/web", "--concern", "auth",
                  "--language", "ts", "--code-snippet", "type X = string",
                  "--cite-file", "f.ts", "--cite-start", "1",
                  "--cite-end", "1")
        proc = self._run("add-concern-type",
                         "--package", "apps/web", "--concern", "auth",
                         "--language", "ts",
                         "--code-snippet", "type X = string",
                         "--cite-file", "f.ts", "--cite-start", "1",
                         "--cite-end", "1")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"already registered", proc.stderr)

    def test_add_dep_happy(self):
        self._init_pkg_concern()
        proc = self._run("add-concern-dep",
                         "--package", "apps/web", "--concern", "auth",
                         "--name", "jose", "--kind", "external",
                         "--version", "5.0.0",
                         "--purpose", "JWT signing.")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        deps = state["packages"]["apps/web"]["concerns"]["auth"]["dependencies"]
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["name"], "jose")
        self.assertEqual(deps[0]["kind"], "external")

    def test_add_dep_duplicate_rejected(self):
        self._init_pkg_concern()
        self._run("add-concern-dep",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "jose", "--kind", "external", "--version", "5",
                  "--purpose", "X.")
        proc = self._run("add-concern-dep",
                         "--package", "apps/web", "--concern", "auth",
                         "--name", "jose", "--kind", "external",
                         "--version", "5", "--purpose", "Y.")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"already registered", proc.stderr)

    def test_add_hazard_happy_no_cite(self):
        self._init_pkg_concern()
        proc = self._run("add-concern-hazard",
                         "--package", "apps/web", "--concern", "auth",
                         "--category", "naming",
                         "--description", "Inconsistent.")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        hazards = state["packages"]["apps/web"]["concerns"]["auth"]["hazards"]
        self.assertEqual(len(hazards), 1)
        self.assertIsNone(hazards[0]["cite"])

    def test_add_hazard_with_cite(self):
        self._init_pkg_concern()
        proc = self._run("add-concern-hazard",
                         "--package", "apps/web", "--concern", "auth",
                         "--category", "performance",
                         "--description", "Slow path.",
                         "--cite-file", "src/auth/login.ts",
                         "--cite-start", "10", "--cite-end", "20")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self._read_state()
        cite = state["packages"]["apps/web"]["concerns"]["auth"][
            "hazards"
        ][0]["cite"]
        self.assertEqual(cite["start"], 10)
        self.assertEqual(cite["end"], 20)

    def test_add_hazard_partial_cite_rejected(self):
        self._init_pkg_concern()
        proc = self._run("add-concern-hazard",
                         "--package", "apps/web", "--concern", "auth",
                         "--category", "naming",
                         "--description", "X.",
                         "--cite-file", "f.ts", "--cite-start", "1")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"cite", proc.stderr)

    def test_add_hazard_duplicate_rejected(self):
        self._init_pkg_concern()
        self._run("add-concern-hazard",
                  "--package", "apps/web", "--concern", "auth",
                  "--category", "naming", "--description", "Bad.")
        proc = self._run("add-concern-hazard",
                         "--package", "apps/web", "--concern", "auth",
                         "--category", "naming", "--description", "Bad.")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"already registered", proc.stderr)

    def test_isolation_across_concerns_same_package(self):
        # Two concerns under the same package; an export added to one
        # must NOT appear in the other.
        self._add_pkg()
        self._run("add-concern",
                  "--package", "apps/web", "--concern", "auth")
        self._run("add-concern",
                  "--package", "apps/web", "--concern", "billing")
        self._run("add-concern-export",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "x.",
                  "--language", "ts", "--code-snippet", "x",
                  "--cite-file", "f.ts", "--cite-start", "1",
                  "--cite-end", "1")
        state = self._read_state()
        concerns = state["packages"]["apps/web"]["concerns"]
        self.assertEqual(len(concerns["auth"]["public_surface"]), 1)
        self.assertEqual(len(concerns["billing"]["public_surface"]), 0)

    def test_isolation_across_packages(self):
        # Two packages each with a concern of the same name; export
        # added to one must NOT bleed into the other.
        self._run("add-package",
                  "--path", "apps/web", "--name", "web")
        self._run("add-package",
                  "--path", "apps/api", "--name", "api")
        self._run("add-concern",
                  "--package", "apps/web", "--concern", "auth")
        self._run("add-concern",
                  "--package", "apps/api", "--concern", "auth")
        self._run("add-concern-dep",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "jose", "--kind", "external", "--version", "5",
                  "--purpose", "X.")
        state = self._read_state()
        web_deps = state["packages"]["apps/web"]["concerns"]["auth"][
            "dependencies"
        ]
        api_deps = state["packages"]["apps/api"]["concerns"]["auth"][
            "dependencies"
        ]
        self.assertEqual(len(web_deps), 1)
        self.assertEqual(len(api_deps), 0)


class RenderConcernSkeletonTests(_ConcernTestBase):

    def _render(self, package="apps/web", concern="auth"):
        return self._run("render-concern-skeleton",
                         "--package", package, "--concern", concern)

    def test_empty_concern_has_todo_slots(self):
        self._init_pkg_concern()
        proc = self._render()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out_path = (
            self.project_root / "docs" / "apps/web" / "auth"
            / "index.md.skeleton"
        )
        self.assertTrue(out_path.exists())
        text = out_path.read_text(encoding="utf-8")
        self.assertIn("# auth", text)
        self.assertIn("## Overview", text)
        self.assertIn("[TODO: 1-2 paragraphs", text)
        self.assertIn("## Directory Structure", text)
        self.assertIn("## Public Surface", text)
        # Concern uses Public Surface, NOT Main Exports.
        self.assertNotIn("## Main Exports", text)
        self.assertIn("[TODO: enumerate concern's public surface", text)
        self.assertIn("## Types", text)
        self.assertIn("## Dependencies", text)
        self.assertIn("## Hazards", text)
        self.assertIn("## Usage Example", text)

    def test_path_shape_under_package_subdir(self):
        self._init_pkg_concern()
        self._render()
        # Concern doc lives at docs/<package>/<concern>/index.md.skeleton
        out_path = (
            self.project_root / "docs" / "apps/web" / "auth"
            / "index.md.skeleton"
        )
        self.assertTrue(out_path.exists())

    def test_missing_package_errors(self):
        proc = self._render(package="apps/missing", concern="auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"package not registered", proc.stderr)

    def test_missing_concern_errors(self):
        self._add_pkg()
        proc = self._render(concern="ghost")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"concern", proc.stderr)

    def test_idempotent_byte_identical(self):
        self._init_pkg_concern()
        self._run("set-concern-overview",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "X.")
        self._render()
        out_path = (
            self.project_root / "docs" / "apps/web" / "auth"
            / "index.md.skeleton"
        )
        a = out_path.read_bytes()
        self._render()
        b = out_path.read_bytes()
        self.assertEqual(a, b)

    def test_optional_section_todos_cite_concern_setters(self):
        # Optional Dependencies/Hazards/Usage TODOs in a concern doc
        # must cite the concern-tier setter names (add-concern-dep etc),
        # NOT the package-tier names — otherwise an LLM following the
        # TODO call-site will run the wrong helper command.
        self._init_pkg_concern()
        self._render()
        text = (
            self.project_root / "docs" / "apps/web" / "auth"
            / "index.md.skeleton"
        ).read_text(encoding="utf-8")
        # Dependencies section TODO mentions add-concern-dep.
        deps_idx = text.index("## Dependencies")
        # Slice the next two paragraphs (everything until the next H2).
        deps_chunk = text[deps_idx:text.index("##", deps_idx + 1)]
        self.assertIn("add-concern-dep", deps_chunk)
        self.assertNotIn("add-package-dep", deps_chunk)
        haz_idx = text.index("## Hazards")
        haz_chunk = text[haz_idx:text.index("##", haz_idx + 1)]
        self.assertIn("add-concern-hazard", haz_chunk)
        self.assertNotIn("add-package-hazard", haz_chunk)
        usage_idx = text.index("## Usage Example")
        # Last section — slice to end.
        usage_chunk = text[usage_idx:]
        self.assertIn("set-concern-usage-example", usage_chunk)
        self.assertNotIn("set-package-usage-example", usage_chunk)

    def test_full_state_no_required_todos(self):
        # After populating all required-field setters, the skeleton must
        # not contain any required-field [TODO]. Optional Types/Hazards/
        # Usage may still show optional [TODO] markers — that's fine.
        self._init_pkg_concern()
        self._write_source("src/auth/login.ts", ["export function login() {}"])
        self._run("set-concern-overview",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "Auth.")
        self._run("set-concern-tree",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "auth/\n  login.ts")
        self._run("add-concern-export",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "Logs in.",
                  "--language", "ts",
                  "--code-snippet", "export function login() {}",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "1")
        self._render()
        text = (
            self.project_root / "docs" / "apps/web" / "auth"
            / "index.md.skeleton"
        ).read_text(encoding="utf-8")
        # No required-field markers should remain.
        self.assertNotIn("[TODO: 1-2 paragraphs", text)
        self.assertNotIn("[TODO: ascii tree", text)
        self.assertNotIn("[TODO: enumerate concern's public surface", text)


class ValidateConcernTests(_ConcernTestBase):

    def _fill_minimum_valid_concern(self):
        """Register a fully-valid concern with one matching source file."""
        self._write_source("src/auth/login.ts", [
            "export function login(id) {",
            "  return id;",
            "}",
        ])
        self._init_pkg_concern()
        self._run("set-concern-overview",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "Auth.")
        self._run("set-concern-tree",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "auth/\n  login.ts")
        self._run("add-concern-export",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "Logs in.",
                  "--language", "ts",
                  "--code-snippet",
                  "export function login(id) {\n  return id;\n}",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "3")
        # annotations-missing gate: at least one annotation required when
        # directory_tree is set.
        self._run("add-annotation",
                  "--package", "apps/web", "--concern", "auth",
                  "--target-path", "src/auth/login.ts",
                  "--label", "Auth entry point",
                  "--confidence", "extracted",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "1",
                  "--model-version", "test-model")

    def test_full_concern_passes(self):
        self._fill_minimum_valid_concern()
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_missing_required_fields_reported(self):
        self._init_pkg_concern()
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ConcernDoc.overview", proc.stderr)
        self.assertIn(b"ConcernDoc.directory_tree", proc.stderr)
        # Empty public_surface flagged too.
        self.assertIn(b"public surface", proc.stderr)

    def test_concern_not_registered(self):
        self._add_pkg()
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "ghost")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"not registered", proc.stderr)

    def test_package_not_registered(self):
        proc = self._run("validate-concern",
                         "--package", "apps/missing", "--concern", "auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"package not registered", proc.stderr)

    def test_snippet_mismatch_reported(self):
        # Fill a concern but the registered snippet doesn't match the
        # source file.
        self._write_source("src/auth/login.ts", [
            "export function login() {}",
            "export function logout() {}",
        ])
        self._init_pkg_concern()
        self._run("set-concern-overview",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "X.")
        self._run("set-concern-tree",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "X.")
        self._run("add-concern-export",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "X.",
                  "--language", "ts",
                  "--code-snippet", "wrong content",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "2")
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"does not match", proc.stderr)

    def test_concern_type_codeblock_validated(self):
        # Type codeblock cite must be checked too.
        self._write_source("src/auth/types.ts", [
            "export type Token = string",
            "export type Session = { user: string }",
        ])
        self._fill_minimum_valid_concern()
        self._run("add-concern-type",
                  "--package", "apps/web", "--concern", "auth",
                  "--language", "ts",
                  "--code-snippet", "wrong content",  # mismatched
                  "--cite-file", "src/auth/types.ts",
                  "--cite-start", "1", "--cite-end", "1")
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"types[0]", proc.stderr)

    # ------------------------------------------------------------------
    # annotations-missing gate tests (Fix D of VALIDATOR-LOOP-PLAN.md)
    # ------------------------------------------------------------------

    def test_validate_concern_fails_when_tree_set_zero_annotations(self):
        """Concern with directory_tree set but zero annotations registered
        must fail validate-concern with rule='annotations-missing'."""
        self._write_source("src/auth/login.ts", [
            "export function login(id) {",
            "  return id;",
            "}",
        ])
        self._init_pkg_concern()
        self._run("set-concern-overview",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "Auth.")
        self._run("set-concern-tree",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "src/\n  auth/login.ts")
        self._run("add-concern-export",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "Logs in.",
                  "--language", "ts",
                  "--code-snippet",
                  "export function login(id) {\n  return id;\n}",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "3")
        # No add-annotation call — annotations stays {}.
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"annotations-missing", proc.stderr)

    def test_validate_concern_passes_when_tree_unset_zero_annotations(self):
        """Empty directory_tree + no annotations must NOT fire
        annotations-missing (other rules may still fail; this specific
        rule is exempt when tree is unset)."""
        self._init_pkg_concern()
        # do NOT set directory_tree — leave it None (default).
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        # Other required-field errors will fire (overview, directory_tree,
        # public_surface), but annotations-missing must NOT be among them.
        self.assertNotIn(b"annotations-missing", proc.stderr)

    def test_validate_concern_passes_when_tree_set_with_annotations(self):
        """Concern with directory_tree set AND at least one annotation
        registered must not trigger the annotations-missing rule."""
        self._write_source("src/auth/login.ts", [
            "export function login(id) {",
            "  return id;",
            "}",
        ])
        self._init_pkg_concern()
        self._run("set-concern-overview",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "Auth.")
        self._run("set-concern-tree",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "auth/\n  login.ts")
        self._run("add-concern-export",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "Logs in.",
                  "--language", "ts",
                  "--code-snippet",
                  "export function login(id) {\n  return id;\n}",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "3")
        self._run("add-annotation",
                  "--package", "apps/web", "--concern", "auth",
                  "--target-path", "src/auth/login.ts",
                  "--label", "Auth entry",
                  "--confidence", "extracted",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "1",
                  "--model-version", "test-model")
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn(b"annotations-missing", proc.stderr)

    def test_validate_concern_passes_when_tree_whitespace_only(self):
        """directory_tree containing only whitespace is treated as unset —
        annotations-missing must NOT fire."""
        self._init_pkg_concern()
        # Directly write whitespace-only tree into state to bypass the
        # setter's blank-rejection guard (we test the validator behaviour,
        # not the setter).
        state = self._read_state()
        state["packages"]["apps/web"]["concerns"]["auth"][
            "directory_tree"
        ] = "   \n  "
        self.state_file.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        # Other errors will fire (overview unset, public_surface empty),
        # but NOT annotations-missing.
        self.assertNotIn(b"annotations-missing", proc.stderr)

    def test_validate_concern_legacy_no_annotations_key(self):
        """A concern record lacking the 'annotations' key entirely (legacy
        state predating Step A.1) with a tree set must fire annotations-missing."""
        self._write_source("src/auth/login.ts", [
            "export function login(id) {",
            "  return id;",
            "}",
        ])
        self._init_pkg_concern()
        self._run("set-concern-tree",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "auth/\n  login.ts")
        # Remove the 'annotations' key from state to simulate legacy records.
        state = self._read_state()
        del state["packages"]["apps/web"]["concerns"]["auth"]["annotations"]
        self.state_file.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"annotations-missing", proc.stderr)

    def test_validate_concern_annotations_missing_in_error_list_with_other_rules(self):
        """Concern with multiple problems (tree set + zero annotations +
        no public_surface) produces BOTH annotations-missing AND
        public-surface-nonempty errors — orchestrator sees full picture."""
        self._init_pkg_concern()
        self._run("set-concern-tree",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "auth/\n  login.ts")
        # No add-annotation, no add-concern-export.
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"annotations-missing", proc.stderr)
        self.assertIn(b"public surface", proc.stderr)


class ValidateConcernOptionalRenderTests(_ConcernTestBase):
    """Tests for the concern-tier `_check_concern_optional_render` rule.

    Mirrors the package-tier `_check_optional_render` defense-in-depth
    check: state populated for a concern's optional field but render
    emits the optional [TODO] -> render bug.

    Synthetic mismatch tests patch `_validators.render_concern_skeleton`
    in-process to simulate the render regression. The empty-state and
    happy-path tests run the CLI end-to-end.
    """

    def _fill_minimum_valid_concern(self):
        """Register a fully-valid concern with one matching source file."""
        self._write_source("src/auth/login.ts", [
            "export function login(id) {",
            "  return id;",
            "}",
        ])
        self._init_pkg_concern()
        self._run("set-concern-overview",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "Auth.")
        self._run("set-concern-tree",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "auth/\n  login.ts")
        self._run("add-concern-export",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "Logs in.",
                  "--language", "ts",
                  "--code-snippet",
                  "export function login(id) {\n  return id;\n}",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "3")
        # annotations-missing gate: at least one annotation required when
        # directory_tree is set.
        self._run("add-annotation",
                  "--package", "apps/web", "--concern", "auth",
                  "--target-path", "src/auth/login.ts",
                  "--label", "Auth entry point",
                  "--confidence", "extracted",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "1",
                  "--model-version", "test-model")

    def _build_state_with_optional_fields(self):
        """Construct an in-memory state dict where every optional
        concern field is populated (types / dependencies / hazards /
        usage_example).

        Used by the patch-render mismatch tests: validate_concern is
        called directly, so we don't need on-disk source files matching
        the citations — `_check_concern_codeblocks` errors are
        ignored; we only care that the optional-render-mismatch rule
        fires for the field under test.
        """
        from _generate_docs._state import (
            default_state,
            default_package_record,
            default_concern_record,
        )
        state = default_state()
        pkg = default_package_record("web", "apps/web")
        pkg["overview"] = "X"
        pkg["directory_tree"] = "src/"
        pkg["primary_language"] = "ts"
        pkg["exports"] = [{
            "kind": "function", "name": "f", "signature": None,
            "description": "x",
            "code": {
                "language": "ts", "snippet": "x",
                "cite": {"file": "src/f.ts", "start": 1, "end": 1},
            },
        }]
        pkg["dependencies"] = [{
            "kind": "external", "name": "react", "version": "1",
            "purpose": "ui", "consumer_locations": [],
        }]
        concern = default_concern_record("auth")
        concern["overview"] = "Auth concern."
        concern["directory_tree"] = "auth/"
        concern["public_surface"] = [{
            "kind": "function", "name": "login", "signature": None,
            "description": "Logs in.",
            "code": {
                "language": "ts", "snippet": "x",
                "cite": {"file": "src/auth/login.ts", "start": 1, "end": 1},
            },
        }]
        concern["types"] = [{
            "language": "ts", "snippet": "type Token = string",
            "cite": {"file": "src/auth/types.ts", "start": 1, "end": 1},
        }]
        concern["dependencies"] = [{
            "kind": "external", "name": "jose", "version": "5",
            "purpose": "JWT.", "consumer_locations": [],
        }]
        concern["hazards"] = [{
            "category": "naming", "description": "Inconsistent.",
            "cite": None,
        }]
        concern["usage_example"] = {
            "language": "ts", "snippet": "login()",
            "cite": {"file": "src/auth/login.ts", "start": 1, "end": 1},
        }
        pkg["concerns"]["auth"] = concern
        state["packages"]["apps/web"] = pkg
        return state

    def test_happy_path_all_optional_populated_passes(self):
        """State has all 4 optional concern fields populated, source
        files match — validate-concern returns 0 with no
        concern-optional-render-mismatch error."""
        self._write_source("src/auth/login.ts", [
            "export function login(id) {",
            "  return id;",
            "}",
        ])
        self._write_source("src/auth/types.ts", [
            "export type Token = string",
        ])
        self._fill_minimum_valid_concern()
        # Add types, deps, hazards, usage_example.
        self._run("add-concern-type",
                  "--package", "apps/web", "--concern", "auth",
                  "--language", "ts",
                  "--code-snippet", "export type Token = string",
                  "--cite-file", "src/auth/types.ts",
                  "--cite-start", "1", "--cite-end", "1")
        self._run("add-concern-dep",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "jose", "--kind", "external",
                  "--version", "5.0.0",
                  "--purpose", "JWT signing.")
        self._run("add-concern-hazard",
                  "--package", "apps/web", "--concern", "auth",
                  "--category", "naming",
                  "--description", "Inconsistent.")
        self._run("set-concern-usage-example",
                  "--package", "apps/web", "--concern", "auth",
                  "--language", "ts",
                  "--code-snippet",
                  "export function login(id) {\n  return id;\n}",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "3")
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn(b"concern-optional-render-mismatch", proc.stderr)

    def test_empty_state_optional_todos_silent(self):
        """State has all 4 optional concern fields empty; render
        naturally emits the optional [TODO]s — this is a LEGITIMATE
        skip and the rule must NOT fire."""
        self._fill_minimum_valid_concern()
        # All four optional concern fields stay empty (default record).
        proc = self._run("validate-concern",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn(b"concern-optional-render-mismatch", proc.stderr)

    def _run_concern_with_buggy_render(self, state, marker_to_inject):
        """Patch render_concern_skeleton to return a string containing
        `marker_to_inject` (a `_TODO_CONCERN_*` sentinel), then call
        validate_concern directly. Returns the error list."""
        from _generate_docs import _validators_concern as v
        original = v.render_concern_skeleton

        def buggy_render(s, p, c):
            # Append the marker so the optional-render check sees it.
            # `_check_concern_no_todos` only checks REQUIRED-field TODO
            # markers, so injecting an OPTIONAL one doesn't trigger
            # noise from that rule.
            return original(s, p, c) + "\n" + marker_to_inject + "\n"

        v.render_concern_skeleton = buggy_render
        try:
            errors = v.validate_concern(
                state, "apps/web", "auth", self.project_root,
            )
        finally:
            v.render_concern_skeleton = original
        return errors

    def test_mismatch_types_caught(self):
        """State populates `types`, render emits the optional
        types-[TODO] -> rule fires for `types`."""
        from _generate_docs._render import _TODO_CONCERN_TYPES
        state = self._build_state_with_optional_fields()
        errors = self._run_concern_with_buggy_render(
            state, _TODO_CONCERN_TYPES,
        )
        rule_errors = [
            e for e in errors
            if e["rule"] == "concern-optional-render-mismatch"
        ]
        self.assertEqual(len(rule_errors), 1)
        self.assertEqual(rule_errors[0]["field"], "types")

    def test_mismatch_dependencies_caught(self):
        from _generate_docs._render import _TODO_CONCERN_DEPENDENCIES
        state = self._build_state_with_optional_fields()
        errors = self._run_concern_with_buggy_render(
            state, _TODO_CONCERN_DEPENDENCIES,
        )
        rule_errors = [
            e for e in errors
            if e["rule"] == "concern-optional-render-mismatch"
        ]
        self.assertEqual(len(rule_errors), 1)
        self.assertEqual(rule_errors[0]["field"], "dependencies")

    def test_mismatch_hazards_caught(self):
        from _generate_docs._render import _TODO_CONCERN_HAZARDS
        state = self._build_state_with_optional_fields()
        errors = self._run_concern_with_buggy_render(
            state, _TODO_CONCERN_HAZARDS,
        )
        rule_errors = [
            e for e in errors
            if e["rule"] == "concern-optional-render-mismatch"
        ]
        self.assertEqual(len(rule_errors), 1)
        self.assertEqual(rule_errors[0]["field"], "hazards")

    def test_mismatch_usage_example_caught(self):
        from _generate_docs._render import _TODO_CONCERN_USAGE_EXAMPLE
        state = self._build_state_with_optional_fields()
        errors = self._run_concern_with_buggy_render(
            state, _TODO_CONCERN_USAGE_EXAMPLE,
        )
        rule_errors = [
            e for e in errors
            if e["rule"] == "concern-optional-render-mismatch"
        ]
        self.assertEqual(len(rule_errors), 1)
        self.assertEqual(rule_errors[0]["field"], "usage_example")


class RenderConcernDocTests(_ConcernTestBase):

    def _fill_minimum_valid_concern(self):
        self._write_source("src/auth/login.ts", [
            "export function login(id) {",
            "  return id;",
            "}",
        ])
        self._init_pkg_concern()
        self._run("set-concern-overview",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "Auth.")
        self._run("set-concern-tree",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "auth/\n  login.ts")
        self._run("add-concern-export",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "Logs in.",
                  "--language", "ts",
                  "--code-snippet",
                  "export function login(id) {\n  return id;\n}",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "3")
        # annotations-missing gate: at least one annotation required when
        # directory_tree is set.
        self._run("add-annotation",
                  "--package", "apps/web", "--concern", "auth",
                  "--target-path", "src/auth/login.ts",
                  "--label", "Auth entry point",
                  "--confidence", "extracted",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "1",
                  "--model-version", "test-model")

    def test_render_doc_happy(self):
        self._fill_minimum_valid_concern()
        # Skeleton first, then doc.
        self._run("render-concern-skeleton",
                  "--package", "apps/web", "--concern", "auth")
        skel_path = (
            self.project_root / "docs" / "apps/web" / "auth"
            / "index.md.skeleton"
        )
        self.assertTrue(skel_path.exists())
        proc = self._run("render-concern-doc",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc_path = (
            self.project_root / "docs" / "apps/web" / "auth" / "index.md"
        )
        self.assertTrue(doc_path.exists())
        # Skeleton sibling removed on success.
        self.assertFalse(skel_path.exists())

    def test_render_doc_validation_blocks(self):
        # Concern has no required fields populated.
        self._init_pkg_concern()
        proc = self._run("render-concern-doc",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"validation failed", proc.stderr)
        doc_path = (
            self.project_root / "docs" / "apps/web" / "auth" / "index.md"
        )
        self.assertFalse(doc_path.exists())

    def test_render_doc_idempotent_byte_identical(self):
        self._fill_minimum_valid_concern()
        self._run("render-concern-doc",
                  "--package", "apps/web", "--concern", "auth")
        doc_path = (
            self.project_root / "docs" / "apps/web" / "auth" / "index.md"
        )
        a = doc_path.read_bytes()
        # Re-render against the same state; result must match byte-for-byte.
        self._run("render-concern-doc",
                  "--package", "apps/web", "--concern", "auth")
        b = doc_path.read_bytes()
        self.assertEqual(a, b)


# ---------------------------------------------------------------------------
# FinalModeRenderConcernTests
#
# Tests that verify the mode="final" render path for concern-tier optional
# sections. In final mode, empty optional sections must emit `_(none)_`
# instead of the LLM-targeted setter-name [TODO] markers. Required-field
# TODOs are unchanged in either mode (required-field setters cannot be
# empty after validation passes — this tests the pure-function layer
# directly, bypassing the CLI validation gate).
# ---------------------------------------------------------------------------


class FinalModeRenderConcernTests(_ConcernTestBase):
    """Unit tests for render_concern_skeleton mode="final" on optional sections.

    Tests use the pure render function directly (not the CLI subprocess) to
    isolate the mode parameter behaviour without requiring a fully-valid
    concern state that passes validate-concern.
    """

    def _make_minimal_state(self, package="apps/web", concern="auth"):
        """Build a minimal in-memory state dict with one package and one
        concern. No fields populated — all optional sections empty."""
        return {
            "packages": {
                package: {
                    "name": "web",
                    "concerns": {
                        concern: {
                            "concern_name": concern,
                            "overview": None,
                            "directory_tree": None,
                            "public_surface": [],
                            "types": [],
                            "dependencies": [],
                            "hazards": [],
                            "usage_example": None,
                        }
                    },
                }
            }
        }

    def _render_direct(self, state, mode, package="apps/web", concern="auth"):
        from _generate_docs._render import render_concern_skeleton
        return render_concern_skeleton(state, package, concern, mode=mode)

    def test_empty_hazards_final_mode_emits_none(self):
        # Empty hazards in final mode must emit _(none)_ and NOT the
        # LLM-targeted setter-name TODO.
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="final")
        self.assertIn("_(none)_", md)
        self.assertNotIn("add-concern-hazard", md)

    def test_empty_hazards_skeleton_mode_emits_todo(self):
        # Regression guard: skeleton mode must still emit the LLM-targeted
        # TODO with "add-concern-hazard" in the Hazards section.
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="skeleton")
        self.assertIn("add-concern-hazard", md)
        self.assertNotIn("_(none)_", md)

    def test_empty_usage_example_final_mode_emits_none(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="final")
        self.assertIn("_(none)_", md)
        self.assertNotIn("set-concern-usage-example", md)

    def test_empty_usage_example_skeleton_mode_emits_todo(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="skeleton")
        self.assertIn("set-concern-usage-example", md)

    def test_empty_types_final_mode_emits_none(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="final")
        self.assertIn("_(none)_", md)
        self.assertNotIn("add-concern-type", md)

    def test_empty_types_skeleton_mode_emits_todo(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="skeleton")
        self.assertIn("add-concern-type", md)

    def test_empty_dependencies_final_mode_emits_none(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="final")
        self.assertIn("_(none)_", md)
        self.assertNotIn("add-concern-dep", md)

    def test_empty_dependencies_skeleton_mode_emits_todo(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="skeleton")
        self.assertIn("add-concern-dep", md)


class FinalModeRenderConcernDocEndToEndTests(_ConcernTestBase):
    """End-to-end CLI tests for cmd_render_concern_doc final-mode output.

    Uses subprocess CLI so the real argparse + dispatch + validate + render
    path is exercised. Requires a fully valid concern state that passes
    validate-concern.
    """

    def _fill_minimum_valid_concern(self):
        self._write_source("src/auth/login.ts", [
            "export function login(id) {",
            "  return id;",
            "}",
        ])
        self._init_pkg_concern()
        self._run("set-concern-overview",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "Auth.")
        self._run("set-concern-tree",
                  "--package", "apps/web", "--concern", "auth",
                  "--text", "auth/\n  login.ts")
        self._run("add-concern-export",
                  "--package", "apps/web", "--concern", "auth",
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "Logs in.",
                  "--language", "ts",
                  "--code-snippet",
                  "export function login(id) {\n  return id;\n}",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "3")
        # annotations-missing gate: at least one annotation required when
        # directory_tree is set.
        self._run("add-annotation",
                  "--package", "apps/web", "--concern", "auth",
                  "--target-path", "src/auth/login.ts",
                  "--label", "Auth entry point",
                  "--confidence", "extracted",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "1",
                  "--model-version", "test-model")

    def test_cmd_render_concern_doc_final_output_has_none_not_todo(self):
        # End-to-end: render-concern-doc with empty optional sections
        # must produce _(none)_ in the final .md, NOT the setter-name TODO.
        self._fill_minimum_valid_concern()
        proc = self._run("render-concern-doc",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc_path = (
            self.project_root / "docs" / "apps/web" / "auth" / "index.md"
        )
        text = doc_path.read_text(encoding="utf-8")
        # Optional-section setter-name TODOs must NOT appear in the final doc.
        self.assertNotIn("add-concern-hazard", text)
        self.assertNotIn("set-concern-usage-example", text)
        self.assertNotIn("add-concern-type", text)
        self.assertNotIn("add-concern-dep", text)
        # The human-facing placeholder must appear in their place.
        self.assertIn("_(none)_", text)

    def test_cmd_render_concern_skeleton_still_emits_todos(self):
        # Regression guard: render-concern-skeleton must still emit
        # LLM-targeted setter-name TODOs (not _(none)_).
        self._init_pkg_concern()
        proc = self._run("render-concern-skeleton",
                         "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        skel_path = (
            self.project_root / "docs" / "apps/web" / "auth"
            / "index.md.skeleton"
        )
        text = skel_path.read_text(encoding="utf-8")
        # Skeleton must have the LLM-targeted TODOs.
        self.assertIn("add-concern-hazard", text)
        self.assertIn("set-concern-usage-example", text)
        # Must NOT have the final-mode _(none)_ placeholder.
        self.assertNotIn("_(none)_", text)


# ---------------------------------------------------------------------------
# FinalModeRenderPackageTests
#
# Mirror of FinalModeRenderConcernTests for the package tier.
# Covers scripts / hazards / usage_example / consumer_pattern.
# ---------------------------------------------------------------------------


class FinalModeRenderPackageTests(_RenderTestBase):
    """Unit tests for render_package_skeleton mode="final" on optional sections.

    Tests use the pure render function directly to isolate mode parameter
    behaviour without requiring a fully-valid package state.
    """

    def _make_minimal_state(self, package="apps/web"):
        """Build a minimal in-memory state dict with one empty package."""
        return {
            "packages": {
                package: {
                    "name": "web",
                    "overview": None,
                    "directory_tree": None,
                    "primary_language": None,
                    "framework": None,
                    "build_tool": None,
                    "scripts": {},
                    "exports": [],
                    "dependencies": [],
                    "hazards": [],
                    "usage_example": None,
                    "consumer_pattern": None,
                    "concerns": {},
                }
            }
        }

    def _render_direct(self, state, mode, package="apps/web"):
        from _generate_docs._render import render_package_skeleton
        return render_package_skeleton(state, package, mode=mode)

    def test_empty_hazards_final_mode_emits_none(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="final")
        self.assertIn("_(none)_", md)
        self.assertNotIn("add-package-hazard", md)

    def test_empty_hazards_skeleton_mode_emits_todo(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="skeleton")
        self.assertIn("add-package-hazard", md)
        self.assertNotIn("_(none)_", md)

    def test_empty_usage_example_final_mode_emits_none(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="final")
        self.assertIn("_(none)_", md)
        self.assertNotIn("set-package-usage-example", md)

    def test_empty_usage_example_skeleton_mode_emits_todo(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="skeleton")
        self.assertIn("set-package-usage-example", md)

    def test_empty_consumer_pattern_final_mode_emits_none(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="final")
        self.assertIn("_(none)_", md)
        self.assertNotIn("set-package-consumer-pattern", md)

    def test_empty_consumer_pattern_skeleton_mode_emits_todo(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="skeleton")
        self.assertIn("set-package-consumer-pattern", md)

    def test_empty_scripts_final_mode_emits_none(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="final")
        self.assertIn("_(none)_", md)
        self.assertNotIn("add-package-script", md)

    def test_empty_scripts_skeleton_mode_emits_todo(self):
        state = self._make_minimal_state()
        md = self._render_direct(state, mode="skeleton")
        self.assertIn("add-package-script", md)


class FinalModeRenderPackageDocEndToEndTests(_RenderTestBase):
    """End-to-end CLI tests for cmd_render_package_doc final-mode output."""

    def _fill_minimum_valid(self):
        src_lines = [
            "export function fetchUser(id) {",
            "  return db.users.get(id);",
            "}",
        ]
        self._write_source("src/api.ts", src_lines)
        self._add_pkg()
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "Web.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/\n  api.ts")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "TypeScript")
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "fetchUser",
                  "--kind", "function",
                  "--signature", "",
                  "--description", "Fetches a user.",
                  "--language", "ts",
                  "--code-snippet", "\n".join(src_lines),
                  "--cite-file", "src/api.ts",
                  "--cite-start", "1", "--cite-end", "3")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "18",
                  "--purpose", "UI lib.")

    def test_cmd_render_package_doc_final_output_has_none_not_todo(self):
        # End-to-end: render-package-doc with empty optional sections
        # must produce _(none)_ in the final .md, NOT setter-name TODOs.
        self._fill_minimum_valid()
        proc = self._run("render-package-doc", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        md_path = self.project_root / "docs" / "apps/web" / "index.md"
        text = md_path.read_text(encoding="utf-8")
        # Optional-section setter-name TODOs must NOT appear in final doc.
        self.assertNotIn("add-package-hazard", text)
        self.assertNotIn("set-package-usage-example", text)
        self.assertNotIn("set-package-consumer-pattern", text)
        self.assertNotIn("add-package-script", text)
        # The human-facing placeholder must appear in their place.
        self.assertIn("_(none)_", text)
        # Required-field content must still be correct.
        self.assertIn("TypeScript", text)
        self.assertIn("fetchUser", text)

    def test_cmd_render_package_skeleton_still_emits_todos(self):
        # Regression guard: render-package-skeleton must still emit
        # LLM-targeted setter-name TODOs (not _(none)_).
        self._add_pkg()
        proc = self._run("render-package-skeleton", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        skel_path = self.project_root / "docs" / "apps/web" / "index.md.skeleton"
        text = skel_path.read_text(encoding="utf-8")
        # Skeleton must have the LLM-targeted TODOs for all optional sections.
        self.assertIn("add-package-hazard", text)
        self.assertIn("set-package-usage-example", text)
        self.assertIn("set-package-consumer-pattern", text)
        self.assertIn("add-package-script", text)
        # Must NOT have the final-mode _(none)_ placeholder.
        self.assertNotIn("_(none)_", text)


class DecompositionGateTests(_RenderTestBase):
    """Filesystem-walk tests for `validate-package`'s decomposition gate.

    Build real subfolder structures under `<project_root>/<package>/src/`
    and check whether validate-package flags substantive subfolders that
    aren't registered as concerns.

    The package-tier baseline (overview/tree/lang/export/dep) is filled
    via `_fill_min` so the only thing being tested is the decomposition
    gate's behavior — every test passes the existing per-package gates
    by construction.
    """

    def _fill_min(self):
        # Create source file at a path that's NOT inside src/ so the
        # cite resolves but doesn't accidentally count toward
        # decomposition.
        self._write_source(
            "apps/web/manifest.ts", ["export const foo = 1"]
        )
        self._add_pkg(path="apps/web")
        self._run("set-package-overview",
                  "--path", "apps/web", "--text", "Web.")
        self._run("set-package-tree",
                  "--path", "apps/web", "--text", "src/")
        self._run("set-package-language",
                  "--path", "apps/web", "--value", "TypeScript")
        self._run("add-package-export",
                  "--path", "apps/web", "--name", "foo",
                  "--kind", "constant",
                  "--signature", "",
                  "--description", "X.",
                  "--language", "ts",
                  "--code-snippet", "export const foo = 1",
                  "--cite-file", "apps/web/manifest.ts",
                  "--cite-start", "1", "--cite-end", "1")
        self._run("add-package-dep",
                  "--path", "apps/web", "--name", "react",
                  "--kind", "external", "--version", "18",
                  "--purpose", "UI.")

    def _make_subdir(self, rel, files):
        """Create a subdir at `<project_root>/<rel>` with the given files."""
        full = self.project_root / rel
        full.mkdir(parents=True, exist_ok=True)
        for fname in files:
            (full / fname).write_text("x", encoding="utf-8")

    def test_no_src_dir_is_noop(self):
        # No `src/` directory under apps/web at all -> gate is a no-op.
        self._fill_min()
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_empty_src_dir_is_noop(self):
        self._fill_min()
        (self.project_root / "apps" / "web" / "src").mkdir(parents=True)
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_multifile_subfolder_flags_missing_concern(self):
        self._fill_min()
        self._make_subdir("apps/web/src/components", ["a.tsx", "b.tsx"])
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"decomposition", proc.stderr)
        self.assertIn(b"components", proc.stderr)

    def test_registered_concern_satisfies_gate(self):
        self._fill_min()
        self._make_subdir("apps/web/src/components", ["a.tsx", "b.tsx"])
        self._run("add-concern",
                  "--package", "apps/web", "--concern", "components")
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_single_file_non_role_folder_is_NOT_substantive(self):
        # Single file in a non-architectural-role folder -> not flagged.
        self._fill_min()
        self._make_subdir("apps/web/src/utils", ["lone.ts"])
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_single_file_architectural_role_folder_IS_substantive(self):
        # `services/` is in the role allowlist; even a single file
        # counts as substantive.
        self._fill_min()
        self._make_subdir("apps/web/src/services", ["api.ts"])
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"services", proc.stderr)

    def test_trivial_leaf_assets_skipped(self):
        # Multi-file `assets/` is in the trivial-leaf list -> NOT flagged.
        self._fill_min()
        self._make_subdir("apps/web/src/assets", ["logo.png", "style.css"])
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_ecosystem_agnostic_match_python_services(self):
        # `services/` in a python project hits the same allowlist —
        # ecosystem-agnostic basename match.
        self._fill_min()
        self._make_subdir("apps/web/src/services", ["billing.py"])
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"services", proc.stderr)

    def test_multiple_missing_concerns_all_reported(self):
        # No truncation — every missing concern surfaces.
        self._fill_min()
        self._make_subdir("apps/web/src/components", ["a.tsx", "b.tsx"])
        self._make_subdir("apps/web/src/handlers", ["h.ts"])
        self._make_subdir("apps/web/src/stores", ["s.ts"])
        proc = self._run("validate-package", "--path", "apps/web")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"components", proc.stderr)
        self.assertIn(b"handlers", proc.stderr)
        self.assertIn(b"stores", proc.stderr)


class StateMigrationTests(_EnvIsolationMixin, unittest.TestCase):
    """Pre-3.1 state files lack the `concerns` per-package key. The
    helper must load such state without modification, treat missing
    `concerns` as `{}`, and let subsequent setters populate it cleanly.
    """

    def _write_legacy_state(self):
        # Hand-author a state file that mimics what a pre-Phase-3.1
        # writer would have produced. Note the absence of the
        # `concerns` field on each package record.
        legacy = {
            "version": 1,
            "packages": {
                "apps/web": {
                    "name": "web",
                    "path": "apps/web",
                    "overview": "An app.",
                    "directory_tree": "src/",
                    "primary_language": "ts",
                    "framework": None,
                    "build_tool": None,
                    "scripts": {},
                    "exports": [],
                    "dependencies": [],
                    "hazards": [],
                    "usage_example": None,
                    "consumer_pattern": None,
                },
            },
        }
        self.state_file.write_text(
            json.dumps(legacy, indent=2, sort_keys=True), encoding="utf-8"
        )

    def test_legacy_state_loads(self):
        self._write_legacy_state()
        # Direct-import API: _load_state reads the env-var-resolved
        # state path. The mixin pops DEVFORGE_DIR in setUp; restore it
        # for this in-process call (the subprocess-based tests in this
        # class already pass the env explicitly).
        os.environ["DEVFORGE_DIR"] = str(self.devforge_dir)
        try:
            from _generate_docs._state import _load_state
            state = _load_state()
        finally:
            os.environ.pop("DEVFORGE_DIR", None)
        self.assertIn("apps/web", state["packages"])
        self.assertEqual(state["packages"]["apps/web"]["concerns"], {})

    def test_legacy_state_status_works(self):
        self._write_legacy_state()
        proc = _run_cli(self.devforge_dir, "status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Status output now includes a concerns line per package.
        self.assertIn(b"concerns: 0", proc.stdout)

    def test_legacy_state_add_concern_works(self):
        self._write_legacy_state()
        proc = _run_cli(self.devforge_dir, "add-concern",
                        "--package", "apps/web", "--concern", "auth")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertIn("auth", state["packages"]["apps/web"]["concerns"])

    def test_default_concern_record_shape(self):
        # The factory exists and produces a fully-initialized dict.
        rec = gdh.default_concern_record("auth")
        self.assertEqual(rec["concern_name"], "auth")
        self.assertIsNone(rec["overview"])
        self.assertIsNone(rec["directory_tree"])
        self.assertEqual(rec["public_surface"], [])
        self.assertEqual(rec["types"], [])
        self.assertEqual(rec["dependencies"], [])
        self.assertEqual(rec["hazards"], [])
        self.assertIsNone(rec["usage_example"])
        # No `consumer_pattern` at concern tier.
        self.assertNotIn("consumer_pattern", rec)


class ConcernHelpTests(_EnvIsolationMixin, unittest.TestCase):
    """All 11 concern subcommands must appear in the helper's help output."""

    def test_help_lists_concern_subcommands(self):
        proc = _run_cli(self.devforge_dir, "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for sub in (
            b"add-concern",
            b"set-concern-overview",
            b"set-concern-tree",
            b"add-concern-export",
            b"add-concern-type",
            b"add-concern-dep",
            b"add-concern-hazard",
            b"set-concern-usage-example",
            b"render-concern-skeleton",
            b"validate-concern",
            b"render-concern-doc",
        ):
            self.assertIn(sub, proc.stdout, "missing %r" % sub)


# ---------------------------------------------------------------------------
# TraceLoggingTests — `<DEVFORGE_DIR>/.generate-docs-trace.log` JSONL audit.
#
# Trace is hooked into _cli.main(); every helper invocation appends one
# line. Tests cover happy path, failure path, append-only semantics,
# parallel-write atomicity, and best-effort failure absorption (an
# unwritable trace path must not break the helper run). Round-trip via
# the real CLI subprocess so the production dispatch path is exercised
# (no in-process shortcuts that could hide the cli wiring).
# ---------------------------------------------------------------------------


class TraceLoggingTests(_EnvIsolationMixin, unittest.TestCase):

    TRACE_FILE_NAME = ".generate-docs-trace.log"

    @property
    def trace_file(self):
        return self.devforge_dir / self.TRACE_FILE_NAME

    def _read_trace_lines(self):
        """Return parsed JSON objects from each line, raising on malformed."""
        text = self.trace_file.read_text(encoding="utf-8")
        lines = [ln for ln in text.split("\n") if ln.strip()]
        return [json.loads(ln) for ln in lines]

    def test_successful_invocation_produces_trace_line(self):
        proc = _run_cli(
            self.devforge_dir,
            "add-package", "--path", "apps/web", "--name", "web",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.trace_file.exists(), "trace file not created")
        records = self._read_trace_lines()
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["subcommand"], "add-package")
        self.assertEqual(rec["exit_code"], 0)
        self.assertGreaterEqual(rec["duration_ms"], 0)
        self.assertIn("package=apps/web", rec["args_summary"])
        # `--name` for add-package is the display name and is intentionally
        # NOT surfaced to the trace summary (would be redundant with
        # package= and add log noise on every package registration).
        self.assertNotIn("name=", rec["args_summary"])
        # ISO 8601 with `Z` suffix.
        self.assertTrue(
            rec["ts"].endswith("Z"),
            "ts not ISO-Z: %r" % rec["ts"],
        )
        # Format roughly: 2026-05-01T18:30:42.123Z
        self.assertRegex(
            rec["ts"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$",
        )

    def test_failed_invocation_produces_trace_line_with_correct_exit_code(self):
        # First add-package succeeds.
        proc1 = _run_cli(
            self.devforge_dir,
            "add-package", "--path", "apps/web", "--name", "web",
        )
        self.assertEqual(proc1.returncode, 0)
        # Second add-package with the same path is rejected (duplicate).
        proc2 = _run_cli(
            self.devforge_dir,
            "add-package", "--path", "apps/web", "--name", "web2",
        )
        self.assertEqual(proc2.returncode, 2)

        records = self._read_trace_lines()
        self.assertEqual(len(records), 2)
        # First trace = success, second = failure.
        self.assertEqual(records[0]["exit_code"], 0)
        self.assertEqual(records[0]["subcommand"], "add-package")
        self.assertEqual(records[1]["exit_code"], 2)
        self.assertEqual(records[1]["subcommand"], "add-package")
        # Both should have `package=apps/web` in summary regardless of
        # success / failure (summary is built from argparse args, which
        # are populated before the handler runs).
        self.assertIn("package=apps/web", records[0]["args_summary"])
        self.assertIn("package=apps/web", records[1]["args_summary"])

    def test_concurrent_invocations_produce_atomic_trace_lines(self):
        # Stress test: 8 parallel `add-concern` invocations (different
        # concern names) against the same pre-registered package. Each
        # spawns its own helper process so each holds its own fd on the
        # trace file. After all complete, the trace file MUST contain
        # exactly 8 valid JSON lines — none corrupted by interleaving.
        # Loops 5 iterations to catch atomic-write regressions.
        for iteration in range(5):
            with self.subTest(iteration=iteration):
                # Reset between iterations: drop trace file and state.
                if self.trace_file.exists():
                    self.trace_file.unlink()
                state_path = self.devforge_dir / gdh.STATE_FILE_NAME
                if state_path.exists():
                    state_path.unlink()

                # Pre-register the package.
                proc = _run_cli(
                    self.devforge_dir,
                    "add-package", "--path", "apps/web", "--name", "web",
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                # Drop the pre-registration trace so we start fresh for
                # the parallel batch count.
                self.trace_file.unlink()

                env = os.environ.copy()
                env["DEVFORGE_DIR"] = str(self.devforge_dir)
                procs = []
                for i in range(8):
                    procs.append(subprocess.Popen(
                        [
                            sys.executable, str(_HELPER_PY),
                            "add-concern",
                            "--package", "apps/web",
                            "--concern", "concern-{0}".format(i),
                        ],
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    ))
                for p in procs:
                    p.communicate()

                # Read raw text; assert each line parses as JSON.
                text = self.trace_file.read_text(encoding="utf-8")
                lines = [ln for ln in text.split("\n") if ln.strip()]
                self.assertEqual(
                    len(lines), 8,
                    "expected 8 trace lines, got %d:\n%s" % (
                        len(lines), text,
                    ),
                )
                for ln in lines:
                    try:
                        rec = json.loads(ln)
                    except json.JSONDecodeError as e:
                        self.fail(
                            "corrupted trace line (concurrent write "
                            "interleaved): %r — %s" % (ln, e)
                        )
                    self.assertEqual(rec["subcommand"], "add-concern")
                    self.assertIn(
                        "package=apps/web", rec["args_summary"],
                    )
                    self.assertIn("concern=", rec["args_summary"])

    def test_trace_write_failure_does_not_break_invocation(self):
        # Point DEVFORGE_DIR at a writable directory so state can be
        # persisted, but pre-create `.generate-docs-trace.log` AS A
        # DIRECTORY so the trace writer's `open(..., "a")` raises
        # IsADirectoryError (an OSError subclass). The helper invocation
        # should STILL succeed and the state file should still be
        # written.
        trace_path_as_dir = self.devforge_dir / self.TRACE_FILE_NAME
        trace_path_as_dir.mkdir(parents=True, exist_ok=True)

        proc = _run_cli(
            self.devforge_dir,
            "add-package", "--path", "apps/web", "--name", "web",
        )
        # Helper must still succeed despite the trace write failing.
        self.assertEqual(
            proc.returncode, 0,
            "helper failed when trace was unwritable: %s" % proc.stderr,
        )
        # State was still written.
        self.assertTrue(self.state_file.exists())
        state = self._read_state()
        self.assertIn("apps/web", state["packages"])
        # Trace path is still a directory (no rogue file write).
        self.assertTrue(trace_path_as_dir.is_dir())

    def test_args_summary_redacts_verbose_text_fields(self):
        # First register the package.
        proc1 = _run_cli(
            self.devforge_dir,
            "add-package", "--path", "apps/web", "--name", "web",
        )
        self.assertEqual(proc1.returncode, 0)
        # Reset trace so we look at just the next call.
        self.trace_file.unlink()

        long_text = "x" * 5000  # 5KB of prose
        proc2 = _run_cli(
            self.devforge_dir,
            "set-package-overview",
            "--path", "apps/web",
            "--text", long_text,
        )
        self.assertEqual(proc2.returncode, 0, proc2.stderr)

        records = self._read_trace_lines()
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["subcommand"], "set-package-overview")
        self.assertIn("package=apps/web", rec["args_summary"])
        # The `--text` value MUST NOT appear in the summary.
        self.assertNotIn("xxxx", rec["args_summary"])
        self.assertLess(
            len(rec["args_summary"]), 200,
            "args_summary too long — verbose field leaked: %r" % (
                rec["args_summary"],
            ),
        )

    def test_trace_file_append_only(self):
        # Three sequential invocations; verify each adds exactly one
        # line and earlier lines remain unchanged after later writes.
        proc = _run_cli(
            self.devforge_dir,
            "add-package", "--path", "apps/web", "--name", "web",
        )
        self.assertEqual(proc.returncode, 0)
        snapshot1 = self.trace_file.read_text(encoding="utf-8")
        self.assertEqual(snapshot1.count("\n"), 1)

        proc = _run_cli(
            self.devforge_dir,
            "add-package", "--path", "apps/api", "--name", "api",
        )
        self.assertEqual(proc.returncode, 0)
        snapshot2 = self.trace_file.read_text(encoding="utf-8")
        self.assertEqual(snapshot2.count("\n"), 2)
        # Earlier line bytes preserved verbatim.
        self.assertTrue(
            snapshot2.startswith(snapshot1),
            "second write rewrote earlier content:\n  s1=%r\n  s2=%r" % (
                snapshot1, snapshot2,
            ),
        )

        proc = _run_cli(
            self.devforge_dir,
            "status",
        )
        self.assertEqual(proc.returncode, 0)
        snapshot3 = self.trace_file.read_text(encoding="utf-8")
        self.assertEqual(snapshot3.count("\n"), 3)
        self.assertTrue(snapshot3.startswith(snapshot2))

        # Validate every line is JSON; first two are add-package, third
        # is status (no traceworthy args).
        records = self._read_trace_lines()
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["subcommand"], "add-package")
        self.assertEqual(records[1]["subcommand"], "add-package")
        self.assertEqual(records[2]["subcommand"], "status")
        self.assertEqual(records[2]["args_summary"], "")


# ---------------------------------------------------------------------------
# CircuitBreakerTests — `_circuit.check_circuit_breakers` against trace log.
#
# Breakers are evaluated BEFORE handler dispatch in `_cli.main`. Tests
# call the public entry point directly (no subprocess) for fast feedback
# on the breaker logic itself; one integration test exercises the
# end-to-end CLI exit-3 path. Tests synthesize trace files manually
# (rather than via the real CLI) because we need precise control over
# scenarios like "501 invocations" or "first ts 65 minutes ago" which
# would be slow / impossible via the real producer.
# ---------------------------------------------------------------------------


class CircuitBreakerTests(_EnvIsolationMixin, unittest.TestCase):

    TRACE_FILE_NAME = ".generate-docs-trace.log"

    def setUp(self):
        super().setUp()
        # Snapshot circuit env vars; restore in tearDown so per-test
        # overrides don't leak into other tests.
        self._saved_circuit_env = {
            k: os.environ.pop(k, None)
            for k in (
                "DEVFORGE_DISABLE_CIRCUIT_BREAKER",
                "DEVFORGE_CIRCUIT_DOOM_LOOP_THRESHOLD",
                "DEVFORGE_CIRCUIT_INVOCATION_BUDGET",
            )
        }
        # Tests need DEVFORGE_DIR set in this process so the imported
        # _circuit module's _trace_file_path() resolves to the per-test
        # tmpdir. _EnvIsolationMixin.setUp pops DEVFORGE_DIR, so put it
        # back for the in-process check (tests that subprocess the CLI
        # set it via env= already).
        os.environ["DEVFORGE_DIR"] = str(self.devforge_dir)

    def tearDown(self):
        for k, v in self._saved_circuit_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        os.environ.pop("DEVFORGE_DIR", None)
        super().tearDown()

    @property
    def trace_file(self):
        return self.devforge_dir / self.TRACE_FILE_NAME

    def _import_circuit(self):
        # _circuit lives inside the _generate_docs internal package.
        # Importing via the helper's `_LIB_DIR` path is already on
        # sys.path (set at module top). Defer the import so the
        # module-level trace path resolves under the per-test
        # DEVFORGE_DIR (set in setUp).
        from _generate_docs import _circuit as circuit
        return circuit

    def _write_trace_lines(self, records):
        """Append a list of dict records as JSONL to the trace file."""
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        with open(str(self.trace_file), "a", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")

    def _ts_now(self):
        from datetime import datetime, timezone
        raw = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        if raw.endswith("+00:00"):
            return raw[:-len("+00:00")] + "Z"
        return raw

    def _make_record(self, subcommand, exit_code=0, ts=None, args_summary=""):
        return {
            "ts": ts if ts is not None else self._ts_now(),
            "subcommand": subcommand,
            "duration_ms": 1,
            "exit_code": exit_code,
            "args_summary": args_summary,
        }

    # ---- Breaker logic tests ------------------------------------------------

    def test_no_trace_file_means_clean_proceed(self):
        circuit = self._import_circuit()
        self.assertFalse(self.trace_file.exists())
        self.assertIsNone(circuit.check_circuit_breakers("status"))

    def test_empty_trace_file_clean_proceed(self):
        circuit = self._import_circuit()
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file.write_text("", encoding="utf-8")
        self.assertIsNone(circuit.check_circuit_breakers("status"))

    def test_doom_loop_trips_on_three_consecutive_same_subcommand_exit_2(self):
        circuit = self._import_circuit()
        self._write_trace_lines([
            self._make_record("add-package", exit_code=2),
            self._make_record("add-package", exit_code=2),
            self._make_record("add-package", exit_code=2),
        ])
        msg = circuit.check_circuit_breakers("add-package")
        self.assertIsNotNone(msg)
        self.assertTrue(
            msg.startswith("circuit-breaker: doom loop detected"),
            "unexpected trip message: %r" % msg,
        )
        self.assertIn("'add-package'", msg)
        self.assertIn("exit 2", msg)

    def test_doom_loop_does_not_trip_when_break_in_sequence(self):
        circuit = self._import_circuit()
        # 4 records: fail, fail, SUCCESS, fail. The success at position
        # -2 breaks the streak (the trailing 3 are not all-same-failure).
        self._write_trace_lines([
            self._make_record("add-package", exit_code=2),
            self._make_record("add-package", exit_code=2),
            self._make_record("add-package", exit_code=0),  # success!
            self._make_record("add-package", exit_code=2),
        ])
        msg = circuit.check_circuit_breakers("add-package")
        self.assertIsNone(
            msg, "doom loop falsely tripped despite intervening success: %r" % msg,
        )

    def test_doom_loop_does_not_trip_when_different_subcommand_in_sequence(self):
        # Defensive: doom-loop requires the trailing N to all share the
        # SAME subcommand. Different subcommands (e.g., add-package then
        # status then add-package) is normal interleaved failure, not a
        # doom loop.
        circuit = self._import_circuit()
        self._write_trace_lines([
            self._make_record("add-package", exit_code=2),
            self._make_record("status", exit_code=2),
            self._make_record("add-package", exit_code=2),
        ])
        self.assertIsNone(circuit.check_circuit_breakers("add-package"))

    def test_invocation_budget_trips_at_threshold(self):
        circuit = self._import_circuit()
        # Write 501 lines — one over the default 500 budget.
        records = [self._make_record("status", exit_code=0) for _ in range(501)]
        self._write_trace_lines(records)
        msg = circuit.check_circuit_breakers("status")
        self.assertIsNotNone(msg)
        self.assertTrue(
            msg.startswith("circuit-breaker: invocation budget exceeded"),
            "unexpected trip message: %r" % msg,
        )
        self.assertIn("501", msg)
        self.assertIn("500", msg)

    def test_invocation_budget_resets_on_reset_marker(self):
        circuit = self._import_circuit()
        # 400 lines → reset → 50 lines. Current run = 51 invocations
        # (the reset itself is included in the run).
        before_reset = [self._make_record("status") for _ in range(400)]
        reset = [self._make_record("reset")]
        after_reset = [self._make_record("status") for _ in range(50)]
        self._write_trace_lines(before_reset + reset + after_reset)
        msg = circuit.check_circuit_breakers("status")
        self.assertIsNone(
            msg,
            "invocation budget falsely tripped after reset (current run "
            "should be 51 invocations, well under 500): %r" % msg,
        )

    # ---- Bypass + fail-open tests -------------------------------------------

    def test_bypass_env_var_disables_all_breakers(self):
        circuit = self._import_circuit()
        os.environ["DEVFORGE_DISABLE_CIRCUIT_BREAKER"] = "1"
        # 501 invocations: would otherwise trip the budget breaker.
        records = [self._make_record("status") for _ in range(501)]
        self._write_trace_lines(records)
        self.assertIsNone(circuit.check_circuit_breakers("status"))

    def test_bypass_zero_value_does_NOT_disable(self):
        # "0" is the explicit "off" form per `_is_disabled()`. Without
        # this guard, a user who set the env to "0" (intending false)
        # would accidentally enable the bypass.
        circuit = self._import_circuit()
        os.environ["DEVFORGE_DISABLE_CIRCUIT_BREAKER"] = "0"
        records = [self._make_record("status") for _ in range(501)]
        self._write_trace_lines(records)
        msg = circuit.check_circuit_breakers("status")
        self.assertIsNotNone(msg, "bypass should not honor '0' as truthy")

    def test_corrupt_trace_line_fails_open(self):
        circuit = self._import_circuit()
        # 2 valid lines, 1 garbage, 1 valid. The corrupt line is
        # silently dropped; remaining 3 lines do not trip any breaker.
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        with open(str(self.trace_file), "a", encoding="utf-8") as f:
            f.write(json.dumps(self._make_record("status")) + "\n")
            f.write(json.dumps(self._make_record("status")) + "\n")
            f.write("{this is not valid json\n")
            f.write(json.dumps(self._make_record("status")) + "\n")
        # Should not raise.
        msg = circuit.check_circuit_breakers("status")
        # Three valid records, all status with exit 0 — no trip.
        self.assertIsNone(msg)

    def test_threshold_overrides_via_env_var(self):
        circuit = self._import_circuit()
        os.environ["DEVFORGE_CIRCUIT_INVOCATION_BUDGET"] = "10"
        records = [self._make_record("status") for _ in range(11)]
        self._write_trace_lines(records)
        msg = circuit.check_circuit_breakers("status")
        self.assertIsNotNone(msg)
        self.assertIn("invocation budget exceeded", msg)
        self.assertIn("11", msg)
        self.assertIn("10", msg)

    def test_doom_threshold_override_via_env_var(self):
        # Drop the doom threshold to 2 so 2 consecutive failures trip.
        circuit = self._import_circuit()
        os.environ["DEVFORGE_CIRCUIT_DOOM_LOOP_THRESHOLD"] = "2"
        self._write_trace_lines([
            self._make_record("add-package", exit_code=2),
            self._make_record("add-package", exit_code=2),
        ])
        msg = circuit.check_circuit_breakers("add-package")
        self.assertIsNotNone(msg)
        self.assertTrue(msg.startswith("circuit-breaker: doom loop detected"))

    def test_malformed_threshold_env_falls_back_to_default(self):
        # Malformed env value (non-int) silently falls back to default.
        # Set INVOCATION_BUDGET to garbage; with default 500 and 11
        # records, no trip should occur.
        circuit = self._import_circuit()
        os.environ["DEVFORGE_CIRCUIT_INVOCATION_BUDGET"] = "not-a-number"
        records = [self._make_record("status") for _ in range(11)]
        self._write_trace_lines(records)
        self.assertIsNone(circuit.check_circuit_breakers("status"))

    # ---- End-to-end CLI integration ----------------------------------------

    def test_cli_returns_exit_3_on_breaker_trip(self):
        # Subprocess the helper with a pre-seeded trace that trips the
        # invocation budget. Helper must exit 3 with the trip message
        # on stderr.
        records = [self._make_record("status") for _ in range(501)]
        self._write_trace_lines(records)
        proc = _run_cli(self.devforge_dir, "status")
        self.assertEqual(
            proc.returncode, 3,
            "expected exit 3 on breaker trip, got %d (stderr: %s)" % (
                proc.returncode, proc.stderr.decode("utf-8", "replace"),
            ),
        )
        stderr = proc.stderr.decode("utf-8")
        self.assertIn("circuit-breaker: invocation budget exceeded", stderr)

    def test_cli_breaker_trip_does_not_emit_trace_line(self):
        # Documented design call: a trip aborts the invocation entirely;
        # no trace line is emitted for the trip itself. Verify the trace
        # file is unchanged (still 501 lines, not 502) after a tripped
        # invocation.
        records = [self._make_record("status") for _ in range(501)]
        self._write_trace_lines(records)
        before = self.trace_file.read_text(encoding="utf-8").count("\n")
        proc = _run_cli(self.devforge_dir, "status")
        self.assertEqual(proc.returncode, 3)
        after = self.trace_file.read_text(encoding="utf-8").count("\n")
        self.assertEqual(
            after, before,
            "tripped invocation produced a trace line (before=%d, after=%d)" % (
                before, after,
            ),
        )

    def test_cli_bypass_env_proceeds_normally(self):
        # With the bypass set, even a trace that would trip the budget
        # produces a clean exit 0 invocation (and the trace gets a new
        # line per normal trace-write logic).
        records = [self._make_record("status") for _ in range(501)]
        self._write_trace_lines(records)
        env = os.environ.copy()
        env["DEVFORGE_DIR"] = str(self.devforge_dir)
        env["DEVFORGE_DISABLE_CIRCUIT_BREAKER"] = "1"
        proc = subprocess.run(
            [sys.executable, str(_HELPER_PY), "status"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(
            proc.returncode, 0,
            "bypass should proceed cleanly; got %d, stderr: %s" % (
                proc.returncode, proc.stderr.decode("utf-8", "replace"),
            ),
        )


if __name__ == "__main__":
    unittest.main()
