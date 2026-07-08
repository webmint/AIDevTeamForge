"""Tests for _review/_ui_scope.py (resolve-ui-scope verb).

Coverage:
  Unit (resolve_ui_scope function):
    - web project -> is_ui=True, platform_hint="web"
    - mobile project -> is_ui=True, platform_hint="mobile"
    - desktop-only project -> is_ui=True, platform_hint=None
    - web+backend monorepo -> is_ui=True, platform_hint="web"
    - mobile+backend -> is_ui=True, platform_hint="mobile"
    - backend-only -> is_ui=False
    - cli-only -> is_ui=False
    - library-only -> is_ui=False
    - PROJECT_NATURES absent (key missing) -> is_ui=True (recall bias)
    - PROJECT_NATURES=[] empty array -> is_ui=True (recall bias)
    - PROJECT_NATURES=null -> is_ui=True (recall bias)
    - project-config.json missing -> is_ui=True (recall bias)
    - project-config.json malformed JSON -> is_ui=True (recall bias)
    - project-config.json is a JSON array, not object -> is_ui=True (recall bias)
    - empty --files list -> same result as non-empty (project-level signal only)
    - non-empty --files list -> same result (not used for narrowing)
    - natures field present in result matches config value
    - reason field is a non-empty string

  _match_package mirror:
    - exact match on package path
    - prefix match (file inside a package dir)
    - longest prefix wins over shorter prefix
    - no match -> None
    - empty package_stacks -> None

  CLI (resolve-ui-scope via main):
    - basic web project -> exit 0, is_ui=True JSON on stdout
    - backend-only project -> exit 0, is_ui=False JSON on stdout
    - missing config -> exit 0, is_ui=True (recall bias)
    - bad --files JSON -> exit 2, stderr message
    - default --workspace-root is CWD (doesn't crash even if no config)
    - output is valid JSON with all required keys
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _review._ui_scope import resolve_ui_scope, _match_package  # noqa: E402
from _review._cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _write_config(tmpdir, natures=None, package_stacks=None, missing_natures=False):
    """Write a minimal project-config.json to <tmpdir>/.devforge/project-config.json.

    The fixture mirrors the REAL emitted shape from configure_helper render-config:
    - Uppercase keys (PROJECT_NATURES, PACKAGE_STACKS, etc.)
    - PROJECT_NATURES is a JSON array of strings

    Parameters
    ----------
    tmpdir : str
        Directory to write into (a .devforge/ subdir is created).
    natures : list or None
        Value for PROJECT_NATURES. Pass [] for empty array, None to use
        the missing_natures flag.
    package_stacks : list or None
        Value for PACKAGE_STACKS. None -> omit the key.
    missing_natures : bool
        When True, omit PROJECT_NATURES key entirely (simulates old config).
    """
    devforge_dir = os.path.join(tmpdir, ".devforge")
    os.makedirs(devforge_dir, exist_ok=True)
    config_path = os.path.join(devforge_dir, "project-config.json")

    config = {
        "PROJECT_NAME": "test-project",
        "PROJECT_TYPE": "web-app",
    }
    if not missing_natures:
        # Pass None explicitly to emit "PROJECT_NATURES": null in JSON
        config["PROJECT_NATURES"] = natures
    if package_stacks is not None:
        config["PACKAGE_STACKS"] = package_stacks

    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
    return config_path


# ---------------------------------------------------------------------------
# Unit tests: resolve_ui_scope classification
# ---------------------------------------------------------------------------

class TestResolveUiScopeClassification(unittest.TestCase):
    """Core classification logic: PROJECT_NATURES -> is_ui/platform_hint."""

    def _call(self, natures, files=None, missing_natures=False, package_stacks=None):
        """Build a real project-config.json fixture and call resolve_ui_scope."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(
                tmpdir,
                natures=natures,
                package_stacks=package_stacks,
                missing_natures=missing_natures,
            )
            return resolve_ui_scope(files=files or [], workspace_root=tmpdir)

    # -- UI-natured projects -------------------------------------------------

    def test_web_project_is_ui_true(self):
        result = self._call(["web"])
        self.assertTrue(result["is_ui"])

    def test_web_project_platform_hint_web(self):
        result = self._call(["web"])
        self.assertEqual(result["platform_hint"], "web")

    def test_mobile_project_is_ui_true(self):
        result = self._call(["mobile"])
        self.assertTrue(result["is_ui"])

    def test_mobile_project_platform_hint_mobile(self):
        result = self._call(["mobile"])
        self.assertEqual(result["platform_hint"], "mobile")

    def test_desktop_only_is_ui_true(self):
        result = self._call(["desktop"])
        self.assertTrue(result["is_ui"])

    def test_desktop_only_platform_hint_none(self):
        """desktop has no specific a11y platform hint."""
        result = self._call(["desktop"])
        self.assertIsNone(result["platform_hint"])

    def test_web_backend_monorepo_is_ui_true(self):
        result = self._call(["web", "backend"])
        self.assertTrue(result["is_ui"])

    def test_web_backend_monorepo_platform_hint_web(self):
        """web takes priority over backend in platform_hint."""
        result = self._call(["web", "backend"])
        self.assertEqual(result["platform_hint"], "web")

    def test_mobile_backend_is_ui_true(self):
        result = self._call(["mobile", "backend"])
        self.assertTrue(result["is_ui"])

    def test_mobile_backend_platform_hint_mobile(self):
        result = self._call(["mobile", "backend"])
        self.assertEqual(result["platform_hint"], "mobile")

    # -- Non-UI-natured projects (is_ui=False only when natures present) -----

    def test_backend_only_is_ui_false(self):
        result = self._call(["backend"])
        self.assertFalse(result["is_ui"])

    def test_backend_only_platform_hint_none(self):
        result = self._call(["backend"])
        self.assertIsNone(result["platform_hint"])

    def test_cli_project_is_ui_false(self):
        result = self._call(["cli"])
        self.assertFalse(result["is_ui"])

    def test_library_project_is_ui_false(self):
        result = self._call(["library"])
        self.assertFalse(result["is_ui"])

    def test_data_ml_project_is_ui_false(self):
        result = self._call(["data", "ml"])
        self.assertFalse(result["is_ui"])

    # -- natures field in result matches the config value --------------------

    def test_natures_field_reflects_config(self):
        result = self._call(["web", "backend"])
        self.assertEqual(set(result["natures"]), {"web", "backend"})

    def test_natures_field_non_ui_project(self):
        result = self._call(["backend", "cli"])
        self.assertEqual(set(result["natures"]), {"backend", "cli"})

    # -- reason field is always a non-empty string ---------------------------

    def test_reason_is_string_ui_project(self):
        result = self._call(["web"])
        self.assertIsInstance(result["reason"], str)
        self.assertTrue(len(result["reason"]) > 0)

    def test_reason_is_string_non_ui_project(self):
        result = self._call(["backend"])
        self.assertIsInstance(result["reason"], str)
        self.assertTrue(len(result["reason"]) > 0)

    # -- Files arg does not alter classification (project-level signal) ------

    def test_empty_files_same_as_non_empty_for_web(self):
        result_empty = self._call(["web"], files=[])
        result_files = self._call(["web"], files=["src/App.tsx", "src/index.ts"])
        self.assertEqual(result_empty["is_ui"], result_files["is_ui"])
        self.assertEqual(result_empty["platform_hint"], result_files["platform_hint"])

    def test_empty_files_same_as_non_empty_for_backend(self):
        result_empty = self._call(["backend"], files=[])
        result_files = self._call(["backend"], files=["api/server.py", "api/models.py"])
        self.assertEqual(result_empty["is_ui"], result_files["is_ui"])
        self.assertEqual(result_empty["platform_hint"], result_files["platform_hint"])

    # -- web priority over mobile when both present --------------------------

    def test_web_takes_priority_over_mobile_for_platform_hint(self):
        """When both web and mobile are present, platform_hint='web'."""
        result = self._call(["mobile", "web"])
        self.assertEqual(result["platform_hint"], "web")


# ---------------------------------------------------------------------------
# Unit tests: recall-bias edge cases
# ---------------------------------------------------------------------------

class TestResolveUiScopeRecallBias(unittest.TestCase):
    """Missing/empty/malformed config must default to is_ui=True (recall bias)."""

    def test_project_natures_absent_from_config(self):
        """Key missing entirely (old config predating the field) -> is_ui=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, missing_natures=True)
            result = resolve_ui_scope(files=[], workspace_root=tmpdir)
        self.assertTrue(result["is_ui"])
        self.assertIsNone(result["platform_hint"])
        self.assertEqual(result["natures"], [])

    def test_project_natures_null_json(self):
        """PROJECT_NATURES: null in JSON -> is_ui=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, natures=None)  # writes PROJECT_NATURES: null
            result = resolve_ui_scope(files=[], workspace_root=tmpdir)
        self.assertTrue(result["is_ui"])

    def test_project_natures_empty_array(self):
        """PROJECT_NATURES: [] -> is_ui=True (can't determine, recall bias)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, natures=[])
            result = resolve_ui_scope(files=[], workspace_root=tmpdir)
        self.assertTrue(result["is_ui"])

    def test_config_file_missing(self):
        """No .devforge/project-config.json -> is_ui=True (recall bias)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Do NOT write any config file.
            result = resolve_ui_scope(files=[], workspace_root=tmpdir)
        self.assertTrue(result["is_ui"])
        self.assertIsNone(result["platform_hint"])
        self.assertEqual(result["natures"], [])
        # Reason must mention the recall bias decision.
        self.assertIn("recall bias", result["reason"].lower())

    def test_config_malformed_json(self):
        """Malformed JSON -> is_ui=True (recall bias)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            devforge_dir = os.path.join(tmpdir, ".devforge")
            os.makedirs(devforge_dir)
            config_path = os.path.join(devforge_dir, "project-config.json")
            with open(config_path, "w") as fh:
                fh.write("{ not valid json }")
            result = resolve_ui_scope(files=[], workspace_root=tmpdir)
        self.assertTrue(result["is_ui"])
        self.assertIn("recall bias", result["reason"].lower())

    def test_config_is_array_not_object(self):
        """project-config.json is a JSON array (wrong shape) -> is_ui=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            devforge_dir = os.path.join(tmpdir, ".devforge")
            os.makedirs(devforge_dir)
            config_path = os.path.join(devforge_dir, "project-config.json")
            with open(config_path, "w") as fh:
                json.dump(["not", "an", "object"], fh)
            result = resolve_ui_scope(files=[], workspace_root=tmpdir)
        self.assertTrue(result["is_ui"])
        self.assertIn("recall bias", result["reason"].lower())

    def test_recall_bias_reason_explains_field_status(self):
        """The recall-bias reason must mention the missing/empty field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, missing_natures=True)
            result = resolve_ui_scope(files=[], workspace_root=tmpdir)
        # The reason should mention either 'PROJECT_NATURES' or 'absent' or 'empty'
        reason_lower = result["reason"].lower()
        self.assertTrue(
            "project_natures" in reason_lower or "absent" in reason_lower or "empty" in reason_lower,
            "Recall-bias reason does not explain the missing/empty field: {0!r}".format(result["reason"])
        )


# ---------------------------------------------------------------------------
# Unit tests: _match_package (mirrored from _implement._cmds_verify)
# ---------------------------------------------------------------------------

class TestMatchPackage(unittest.TestCase):
    """_match_package mirrors _implement/_cmds_verify._match_package exactly."""

    def test_exact_match(self):
        stacks = [{"path": "src/web", "framework": "react"}]
        result = _match_package("src/web", stacks)
        self.assertIsNotNone(result)
        self.assertEqual(result["framework"], "react")

    def test_prefix_match(self):
        stacks = [{"path": "src/web", "framework": "react"}]
        result = _match_package("src/web/components/Button.tsx", stacks)
        self.assertIsNotNone(result)

    def test_longest_prefix_wins(self):
        stacks = [
            {"path": "src", "framework": "generic"},
            {"path": "src/web", "framework": "react"},
        ]
        result = _match_package("src/web/components/Button.tsx", stacks)
        self.assertIsNotNone(result)
        self.assertEqual(result["framework"], "react")

    def test_no_match_returns_none(self):
        stacks = [{"path": "src/web", "framework": "react"}]
        result = _match_package("api/server.py", stacks)
        self.assertIsNone(result)

    def test_empty_package_stacks_returns_none(self):
        result = _match_package("src/a.py", [])
        self.assertIsNone(result)

    def test_partial_path_component_does_not_match(self):
        """'src/webfoo' must NOT match package path 'src/web'."""
        stacks = [{"path": "src/web", "framework": "react"}]
        result = _match_package("src/webfoo/bar.ts", stacks)
        self.assertIsNone(result)

    def test_windows_slash_normalized(self):
        """Windows-style backslashes in file_path are normalized."""
        stacks = [{"path": "src/web", "framework": "react"}]
        result = _match_package("src\\web\\Button.tsx", stacks)
        self.assertIsNotNone(result)


# ---------------------------------------------------------------------------
# CLI round-trips via main([...])
# ---------------------------------------------------------------------------

class TestCLIResolveUiScope(unittest.TestCase):
    """CLI dispatch for resolve-ui-scope verb."""

    def _run(self, argv):
        """Run main([...]) capturing stdout/stderr. Returns (exit_code, stdout, stderr)."""
        old_out, old_err = sys.stdout, sys.stderr
        try:
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            try:
                code = main(argv)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 2
            out = sys.stdout.getvalue()
            err = sys.stderr.getvalue()
        finally:
            sys.stdout = old_out
            sys.stderr = old_err
        return code, out, err

    def test_web_project_returns_0_and_is_ui_true(self):
        """Web project: exit 0, is_ui=True, platform_hint=web."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, natures=["web"])
            code, out, err = self._run([
                "resolve-ui-scope",
                "--files", "[]",
                "--workspace-root", tmpdir,
            ])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertTrue(result["is_ui"])
        self.assertEqual(result["platform_hint"], "web")

    def test_backend_project_returns_0_and_is_ui_false(self):
        """Backend-only project: exit 0, is_ui=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, natures=["backend"])
            code, out, err = self._run([
                "resolve-ui-scope",
                "--files", '["api/server.py"]',
                "--workspace-root", tmpdir,
            ])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertFalse(result["is_ui"])

    def test_missing_config_returns_0_and_is_ui_true_recall_bias(self):
        """No project-config.json: exit 0 (no crash), is_ui=True (recall bias)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # No config written.
            code, out, err = self._run([
                "resolve-ui-scope",
                "--workspace-root", tmpdir,
            ])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertTrue(result["is_ui"])

    def test_bad_files_json_returns_2(self):
        """Malformed --files JSON: exit 2, stderr message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, natures=["web"])
            code, out, err = self._run([
                "resolve-ui-scope",
                "--files", "not-a-json-array",
                "--workspace-root", tmpdir,
            ])
        self.assertEqual(code, 2)
        self.assertIn("--files", err)

    def test_files_not_an_array_returns_2(self):
        """--files is a JSON object (not array): exit 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, natures=["web"])
            code, out, err = self._run([
                "resolve-ui-scope",
                "--files", '{"a": 1}',
                "--workspace-root", tmpdir,
            ])
        self.assertEqual(code, 2)

    def test_output_is_valid_json_with_all_keys(self):
        """Output JSON always has is_ui, platform_hint, natures, reason."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, natures=["web", "backend"])
            code, out, _ = self._run([
                "resolve-ui-scope",
                "--files", '["src/app.tsx"]',
                "--workspace-root", tmpdir,
            ])
        self.assertEqual(code, 0)
        result = json.loads(out)
        for key in ("is_ui", "platform_hint", "natures", "reason"):
            self.assertIn(key, result, "Missing key in result: {0}".format(key))

    def test_default_workspace_root_is_cwd(self):
        """Omitting --workspace-root doesn't crash (uses CWD, no config = recall bias)."""
        code, out, err = self._run(["resolve-ui-scope"])
        self.assertEqual(code, 0)
        result = json.loads(out)
        # Can't assert is_ui value (depends on CWD having a config), but must not crash
        self.assertIn("is_ui", result)

    def test_mobile_project_cli(self):
        """Mobile project round-trip via CLI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, natures=["mobile"])
            code, out, _ = self._run([
                "resolve-ui-scope",
                "--workspace-root", tmpdir,
            ])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertTrue(result["is_ui"])
        self.assertEqual(result["platform_hint"], "mobile")

    def test_output_ends_with_newline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, natures=["web"])
            _, out, _ = self._run([
                "resolve-ui-scope",
                "--workspace-root", tmpdir,
            ])
        self.assertTrue(out.endswith("\n"))


class TestResolveUiScopeCaseInsensitive(unittest.TestCase):
    """PROJECT_NATURES is not enum-restricted at set time and is stored
    verbatim, so a title-cased/upper-cased value must still classify as UI.
    A case-sensitive miss would silently drop the a11y audit (recall-bias
    violation)."""

    def _call(self, natures):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_config(tmpdir, natures=natures)
            return resolve_ui_scope(files=[], workspace_root=tmpdir)

    def test_titlecase_web_is_ui_true(self):
        result = self._call(["Web"])
        self.assertTrue(result["is_ui"])
        self.assertEqual(result["platform_hint"], "web")

    def test_uppercase_web_is_ui_true(self):
        result = self._call(["WEB"])
        self.assertTrue(result["is_ui"])
        self.assertEqual(result["platform_hint"], "web")

    def test_titlecase_mobile_is_ui_true(self):
        result = self._call(["Mobile"])
        self.assertTrue(result["is_ui"])
        self.assertEqual(result["platform_hint"], "mobile")

    def test_mixedcase_desktop_is_ui_true(self):
        result = self._call(["DeskTop"])
        self.assertTrue(result["is_ui"])
        self.assertIsNone(result["platform_hint"])

    def test_titlecase_backend_only_is_ui_false(self):
        # A non-UI nature in any case still classifies non-UI.
        result = self._call(["Backend"])
        self.assertFalse(result["is_ui"])

    def test_mixedcase_monorepo_web_backend_is_ui_true(self):
        result = self._call(["Backend", "Web"])
        self.assertTrue(result["is_ui"])
        self.assertEqual(result["platform_hint"], "web")


if __name__ == "__main__":
    unittest.main()
