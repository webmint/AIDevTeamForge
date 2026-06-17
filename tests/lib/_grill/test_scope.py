"""Tests for src/devforge/lib/_grill/_scope.py.

Coverage:
  resolve_target_feature   — explicit feature-dir arg, explicit plan.md path arg,
                             auto-detection (lowest-numbered with plan.md),
                             missing-plan.md dirs skipped, no candidates error,
                             missing specs_root error, explicit bad dir error,
                             tie-breaking (001 < 002), non-numeric dirs ignored
  build_scope_manifest     — happy path all paths present, handoff_path None when absent,
                             missing plan.md error, missing spec.md error,
                             feature_id is basename of feature_dir
  cmd_resolve_scope        — emits JSON on success, exit 2 on feature-resolve error,
                             exit 2 on manifest-build error
  GrillScopeManifest       — default values, dataclass field names
"""

import dataclasses
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _grill._scope import (  # noqa: E402
    GrillScopeManifest,
    _feature_sort_key,
    build_scope_manifest,
    cmd_resolve_scope,
    resolve_target_feature,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_specs(tmp_root, features):
    # type: (str, list) -> str
    """Create a specs/ directory with the given features.

    features: list of (dirname, has_plan_md, has_spec_md, has_handoff_json)
    Returns the path to specs/.
    """
    specs = os.path.join(tmp_root, "specs")
    os.makedirs(specs)
    for dirname, has_plan, has_spec, has_handoff in features:
        fdir = os.path.join(specs, dirname)
        os.makedirs(fdir)
        if has_plan:
            Path(os.path.join(fdir, "plan.md")).write_text("# plan\n")
        if has_spec:
            Path(os.path.join(fdir, "spec.md")).write_text("# spec\n")
        if has_handoff:
            Path(os.path.join(fdir, "handoff.json")).write_text('{"handoff_kind": "specify"}\n')
    return specs


def _make_workspace(tmp_root):
    # type: (str) -> str
    """Create a minimal workspace with constitution.md and CLAUDE.md."""
    Path(os.path.join(tmp_root, "constitution.md")).write_text("# constitution\n")
    Path(os.path.join(tmp_root, "CLAUDE.md")).write_text("# CLAUDE\n")
    return tmp_root


# ---------------------------------------------------------------------------
# Tests: _feature_sort_key
# ---------------------------------------------------------------------------


class TestFeatureSortKey(unittest.TestCase):
    def test_numeric_prefix_returns_int(self):
        self.assertEqual(_feature_sort_key("001-auth"), 1)
        self.assertEqual(_feature_sort_key("012-payments"), 12)
        self.assertEqual(_feature_sort_key("999-last"), 999)

    def test_no_numeric_prefix_returns_maxint(self):
        self.assertEqual(_feature_sort_key("no-number"), 2 ** 31)
        self.assertEqual(_feature_sort_key(""), 2 ** 31)

    def test_full_path_uses_basename(self):
        self.assertEqual(_feature_sort_key("/specs/003-foo"), 3)


# ---------------------------------------------------------------------------
# Tests: resolve_target_feature
# ---------------------------------------------------------------------------


class TestResolveTargetFeature(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- explicit feature-dir arg ---

    def test_explicit_feature_dir_happy_path(self):
        specs = _make_specs(self.tmp, [
            ("001-auth", True, True, False),
        ])
        fdir = os.path.join(specs, "001-auth")
        result, error = resolve_target_feature(specs, fdir)
        self.assertIsNone(error)
        self.assertEqual(result, fdir)

    def test_explicit_plan_md_path_uses_parent_dir(self):
        specs = _make_specs(self.tmp, [
            ("002-pay", True, True, False),
        ])
        plan_path = os.path.join(specs, "002-pay", "plan.md")
        result, error = resolve_target_feature(specs, plan_path)
        self.assertIsNone(error)
        self.assertEqual(result, os.path.abspath(os.path.join(specs, "002-pay")))

    def test_explicit_nonexistent_dir_returns_error(self):
        specs = _make_specs(self.tmp, [])
        result, error = resolve_target_feature(specs, os.path.join(specs, "999-ghost"))
        self.assertIsNone(result)
        self.assertIn("does not resolve to a directory", error)

    def test_explicit_path_to_nonplan_file_returns_error(self):
        """A regular file that isn't plan.md is treated as a dir arg → fails."""
        specs = _make_specs(self.tmp, [
            ("001-auth", True, True, False),
        ])
        spec_path = os.path.join(specs, "001-auth", "spec.md")
        result, error = resolve_target_feature(specs, spec_path)
        # spec.md is a file but not plan.md → treated as dir arg → not a dir → error
        self.assertIsNone(result)
        self.assertIn("does not resolve to a directory", error)

    # --- auto-detection ---

    def test_auto_picks_lowest_numbered_with_plan_md(self):
        specs = _make_specs(self.tmp, [
            ("001-auth", True, True, False),
            ("002-pay", True, True, False),
            ("003-notif", True, True, False),
        ])
        result, error = resolve_target_feature(specs, None)
        self.assertIsNone(error)
        self.assertEqual(os.path.basename(result), "001-auth")

    def test_auto_skips_dirs_without_plan_md(self):
        specs = _make_specs(self.tmp, [
            ("001-auth", False, True, False),   # no plan.md
            ("002-pay", True, True, False),     # has plan.md
        ])
        result, error = resolve_target_feature(specs, None)
        self.assertIsNone(error)
        self.assertEqual(os.path.basename(result), "002-pay")

    def test_auto_ignores_non_numeric_dirs(self):
        specs = _make_specs(self.tmp, [
            ("no-num-dir", True, True, False),  # no numeric prefix
            ("002-pay", True, True, False),
        ])
        result, error = resolve_target_feature(specs, None)
        self.assertIsNone(error)
        self.assertEqual(os.path.basename(result), "002-pay")

    def test_auto_all_missing_plan_returns_error(self):
        specs = _make_specs(self.tmp, [
            ("001-auth", False, True, False),
            ("002-pay", False, True, False),
        ])
        result, error = resolve_target_feature(specs, None)
        self.assertIsNone(result)
        self.assertIn("no feature directories with a plan.md", error)

    def test_auto_missing_specs_root_returns_error(self):
        missing = os.path.join(self.tmp, "nonexistent-specs")
        result, error = resolve_target_feature(missing, None)
        self.assertIsNone(result)
        self.assertIn("does not exist", error)

    def test_auto_empty_specs_dir_returns_error(self):
        specs = _make_specs(self.tmp, [])
        result, error = resolve_target_feature(specs, None)
        self.assertIsNone(result)
        self.assertIn("no feature directories with a plan.md", error)

    def test_auto_tie_break_001_before_002(self):
        """When both 001 and 002 have plan.md, 001 wins."""
        specs = _make_specs(self.tmp, [
            ("002-later", True, True, False),
            ("001-first", True, True, False),
        ])
        result, error = resolve_target_feature(specs, None)
        self.assertIsNone(error)
        self.assertEqual(os.path.basename(result), "001-first")

    def test_auto_result_is_absolute_path(self):
        specs = _make_specs(self.tmp, [
            ("001-auth", True, True, False),
        ])
        result, error = resolve_target_feature(specs, None)
        self.assertIsNone(error)
        self.assertTrue(os.path.isabs(result))

    def test_auto_detection_relative_specs_root_returns_absolute_path(self):
        """Auto-detection with a RELATIVE specs_root must still return an absolute path.

        The docstring guarantees "All paths are absolute."  The explicit-arg branch
        calls os.path.abspath(); the auto-detection branch must do the same.
        """
        specs = _make_specs(self.tmp, [
            ("001-auth", True, True, False),
        ])
        original_cwd = os.getcwd()
        try:
            # Change cwd to self.tmp so that "specs" is a valid relative path.
            os.chdir(self.tmp)
            result, error = resolve_target_feature("specs", None)
            self.assertIsNone(error)
            self.assertTrue(
                os.path.isabs(result),
                "Expected absolute path from auto-detection with relative specs_root, "
                "got: {0!r}".format(result),
            )
        finally:
            os.chdir(original_cwd)


# ---------------------------------------------------------------------------
# Tests: build_scope_manifest
# ---------------------------------------------------------------------------


class TestBuildScopeManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        self.specs = _make_specs(self.tmp, [
            ("001-auth", True, True, True),   # plan + spec + handoff
        ])
        self.feature_dir = os.path.join(self.specs, "001-auth")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- happy path ---

    def test_manifest_fields_set_correctly(self):
        manifest, error = build_scope_manifest(self.feature_dir, self.tmp)
        self.assertIsNone(error)
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest.feature_dir, self.feature_dir)
        self.assertEqual(manifest.feature_id, "001-auth")

    def test_plan_path_points_to_plan_md(self):
        manifest, error = build_scope_manifest(self.feature_dir, self.tmp)
        self.assertIsNone(error)
        self.assertTrue(manifest.plan_path.endswith("plan.md"))
        self.assertTrue(os.path.isfile(manifest.plan_path))

    def test_spec_path_points_to_spec_md(self):
        manifest, error = build_scope_manifest(self.feature_dir, self.tmp)
        self.assertIsNone(error)
        self.assertTrue(manifest.spec_path.endswith("spec.md"))
        self.assertTrue(os.path.isfile(manifest.spec_path))

    def test_handoff_path_present_when_file_exists(self):
        manifest, error = build_scope_manifest(self.feature_dir, self.tmp)
        self.assertIsNone(error)
        self.assertIsNotNone(manifest.handoff_path)
        self.assertTrue(manifest.handoff_path.endswith("handoff.json"))
        self.assertTrue(os.path.isfile(manifest.handoff_path))

    def test_handoff_path_none_when_absent(self):
        specs = _make_specs(self.tmp + "_no_handoff", [
            ("001-no-handoff", True, True, False),   # no handoff.json
        ])
        _make_workspace(self.tmp + "_no_handoff")
        fdir = os.path.join(specs, "001-no-handoff")
        manifest, error = build_scope_manifest(fdir, self.tmp + "_no_handoff")
        self.assertIsNone(error)
        self.assertIsNone(manifest.handoff_path)

    def test_constitution_path_under_workspace_root(self):
        manifest, error = build_scope_manifest(self.feature_dir, self.tmp)
        self.assertIsNone(error)
        self.assertEqual(
            manifest.constitution_path,
            os.path.join(self.tmp, "constitution.md"),
        )

    def test_claude_md_path_under_workspace_root(self):
        manifest, error = build_scope_manifest(self.feature_dir, self.tmp)
        self.assertIsNone(error)
        self.assertEqual(
            manifest.claude_md_path,
            os.path.join(self.tmp, "CLAUDE.md"),
        )

    def test_all_paths_are_absolute(self):
        manifest, error = build_scope_manifest(self.feature_dir, self.tmp)
        self.assertIsNone(error)
        self.assertTrue(os.path.isabs(manifest.feature_dir))
        self.assertTrue(os.path.isabs(manifest.plan_path))
        self.assertTrue(os.path.isabs(manifest.spec_path))
        self.assertTrue(os.path.isabs(manifest.constitution_path))
        self.assertTrue(os.path.isabs(manifest.claude_md_path))

    # --- constitution_path / claude_md_path are paths only, not validated ---

    def test_constitution_and_claude_md_paths_returned_even_if_absent(self):
        """constitution.md and CLAUDE.md paths are included even if files don't exist.

        The agent decides whether they're needed; _scope only validates
        plan.md and spec.md (the feature-level required artefacts).
        """
        workspace = tempfile.mkdtemp()
        try:
            specs = _make_specs(workspace, [("001-x", True, True, False)])
            fdir = os.path.join(specs, "001-x")
            manifest, error = build_scope_manifest(fdir, workspace)
            self.assertIsNone(error)
            # Paths are set even though the files don't exist in this workspace.
            self.assertTrue(manifest.constitution_path.endswith("constitution.md"))
            self.assertTrue(manifest.claude_md_path.endswith("CLAUDE.md"))
        finally:
            import shutil
            shutil.rmtree(workspace, ignore_errors=True)

    # --- error paths ---

    def test_missing_plan_md_returns_error(self):
        specs = _make_specs(self.tmp + "_np", [
            ("001-no-plan", False, True, False),  # no plan.md
        ])
        _make_workspace(self.tmp + "_np")
        fdir = os.path.join(specs, "001-no-plan")
        manifest, error = build_scope_manifest(fdir, self.tmp + "_np")
        self.assertIsNone(manifest)
        self.assertIn("plan.md", error)
        self.assertIn("required artefact missing", error)

    def test_missing_spec_md_returns_error(self):
        specs = _make_specs(self.tmp + "_ns", [
            ("001-no-spec", True, False, False),  # no spec.md
        ])
        _make_workspace(self.tmp + "_ns")
        fdir = os.path.join(specs, "001-no-spec")
        manifest, error = build_scope_manifest(fdir, self.tmp + "_ns")
        self.assertIsNone(manifest)
        self.assertIn("spec.md", error)
        self.assertIn("required artefact missing", error)

    def test_plan_missing_before_spec_checked(self):
        """plan.md is checked before spec.md — its error surfaces first."""
        specs = _make_specs(self.tmp + "_both", [
            ("001-nothing", False, False, False),
        ])
        _make_workspace(self.tmp + "_both")
        fdir = os.path.join(specs, "001-nothing")
        manifest, error = build_scope_manifest(fdir, self.tmp + "_both")
        self.assertIsNone(manifest)
        self.assertIn("plan.md", error)


# ---------------------------------------------------------------------------
# Tests: GrillScopeManifest
# ---------------------------------------------------------------------------


class TestGrillScopeManifest(unittest.TestCase):
    def test_default_values(self):
        m = GrillScopeManifest()
        self.assertEqual(m.feature_dir, "")
        self.assertEqual(m.feature_id, "")
        self.assertEqual(m.plan_path, "")
        self.assertEqual(m.spec_path, "")
        self.assertIsNone(m.handoff_path)
        self.assertEqual(m.constitution_path, "")
        self.assertEqual(m.claude_md_path, "")

    def test_is_dataclass(self):
        self.assertTrue(dataclasses.is_dataclass(GrillScopeManifest))

    def test_field_names(self):
        names = {f.name for f in dataclasses.fields(GrillScopeManifest)}
        expected = {
            "feature_dir", "feature_id", "plan_path", "spec_path",
            "handoff_path", "constitution_path", "claude_md_path",
        }
        self.assertEqual(names, expected)

    def test_asdict_roundtrip(self):
        m = GrillScopeManifest(
            feature_dir="/a",
            feature_id="001-auth",
            plan_path="/a/plan.md",
            spec_path="/a/spec.md",
            handoff_path=None,
            constitution_path="/c.md",
            claude_md_path="/CLAUDE.md",
        )
        d = dataclasses.asdict(m)
        self.assertEqual(d["feature_id"], "001-auth")
        self.assertIsNone(d["handoff_path"])


# ---------------------------------------------------------------------------
# Tests: cmd_resolve_scope
# ---------------------------------------------------------------------------


class _FakeArgs:
    """Minimal argparse.Namespace substitute for CLI tests."""
    def __init__(self, feature=None, workspace_root=None, specs_dir=None):
        self.feature = feature
        self.workspace_root = workspace_root
        self.specs_dir = specs_dir


class TestCmdResolveScope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        self.specs = _make_specs(self.tmp, [
            ("001-auth", True, True, True),
        ])

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_success_emits_json_to_stdout(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = cmd_resolve_scope(_FakeArgs(workspace_root=self.tmp))
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["feature_id"], "001-auth")
        self.assertIn("plan_path", data)
        self.assertIn("spec_path", data)
        self.assertIn("handoff_path", data)
        self.assertIn("constitution_path", data)
        self.assertIn("claude_md_path", data)

    def test_success_handoff_path_in_json(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = cmd_resolve_scope(_FakeArgs(workspace_root=self.tmp))
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertIsNotNone(data["handoff_path"])

    def test_explicit_feature_dir_used(self):
        fdir = os.path.join(self.specs, "001-auth")
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = cmd_resolve_scope(_FakeArgs(feature=fdir, workspace_root=self.tmp))
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["feature_id"], "001-auth")

    def test_exit_2_on_feature_resolve_error(self):
        """No features at all → feature-resolve error → exit 2."""
        empty_tmp = tempfile.mkdtemp()
        try:
            _make_workspace(empty_tmp)
            # specs dir doesn't exist → resolve_target_feature errors
            buf_err = io.StringIO()
            with patch("sys.stderr", buf_err):
                code = cmd_resolve_scope(_FakeArgs(workspace_root=empty_tmp))
            self.assertEqual(code, 2)
            self.assertIn("grill_helper resolve-scope", buf_err.getvalue())
        finally:
            import shutil
            shutil.rmtree(empty_tmp, ignore_errors=True)

    def test_exit_2_on_manifest_missing_plan(self):
        """Feature dir exists but plan.md missing → build_scope_manifest error → exit 2."""
        tmp2 = tempfile.mkdtemp()
        try:
            _make_workspace(tmp2)
            specs2 = _make_specs(tmp2, [
                ("001-no-plan", False, True, False),
            ])
            fdir = os.path.join(specs2, "001-no-plan")
            buf_err = io.StringIO()
            with patch("sys.stderr", buf_err):
                code = cmd_resolve_scope(_FakeArgs(feature=fdir, workspace_root=tmp2))
            self.assertEqual(code, 2)
            self.assertIn("grill_helper resolve-scope", buf_err.getvalue())
        finally:
            import shutil
            shutil.rmtree(tmp2, ignore_errors=True)

    def test_exit_2_on_manifest_missing_spec(self):
        tmp3 = tempfile.mkdtemp()
        try:
            _make_workspace(tmp3)
            specs3 = _make_specs(tmp3, [
                ("001-no-spec", True, False, False),
            ])
            fdir = os.path.join(specs3, "001-no-spec")
            buf_err = io.StringIO()
            with patch("sys.stderr", buf_err):
                code = cmd_resolve_scope(_FakeArgs(feature=fdir, workspace_root=tmp3))
            self.assertEqual(code, 2)
        finally:
            import shutil
            shutil.rmtree(tmp3, ignore_errors=True)

    def test_json_output_is_valid_json(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            cmd_resolve_scope(_FakeArgs(workspace_root=self.tmp))
        # Must parse without exception.
        json.loads(buf.getvalue())

    def test_explicit_specs_dir_override(self):
        """--specs-dir override is respected."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = cmd_resolve_scope(
                _FakeArgs(workspace_root=self.tmp, specs_dir=self.specs)
            )
        self.assertEqual(code, 0)

    def test_no_diff_computation_no_git_calls(self):
        """cmd_resolve_scope must not call subprocess (no git diff, no CBM).

        Primary guarantee: _scope.py has no `import subprocess` or `os.system`
        call at all — the module design explicitly excludes git/CBM calls (see
        module docstring).  The patch below is belt-and-suspenders only; it
        would catch a future accidental introduction but is not the canonical
        verification of the invariant.
        """
        import subprocess as _sp
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            with patch.object(_sp, "run", side_effect=AssertionError("subprocess.run called")):
                # Should succeed without touching subprocess.
                code = cmd_resolve_scope(_FakeArgs(workspace_root=self.tmp))
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
