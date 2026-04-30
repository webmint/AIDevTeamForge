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


def _run_cli(devforge_dir, *args, project_root=None):
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    if project_root is not None:
        env["DEVFORGE_PROJECT_ROOT"] = str(project_root)
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(args),
        env=env,
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
        # Required-field TODOs must NOT appear; optional-section TODOs
        # (scripts / hazards / usage_example / consumer_pattern) are
        # acceptable in the .md when the LLM elected not to fill them.
        self.assertNotIn("[TODO: 1-2 paragraphs", text)
        self.assertNotIn("[TODO: ascii tree", text)
        self.assertNotIn("[TODO: enumerate package exports", text)
        self.assertNotIn("[TODO: enumerate via add-package-dep", text)
        # Required Tech Stack [TODO] (primary_language) must not appear.
        self.assertIn("TypeScript", text)

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


if __name__ == "__main__":
    unittest.main()
