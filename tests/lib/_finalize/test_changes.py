"""Tests for src/devforge/lib/_finalize/_changes.py.

Real-producer round-trip discipline:
  All tests build REAL git repositories in temporary directories via subprocess
  git commands.  No hand-authored diff fixtures.

Coverage:
  gather_change_data — happy path: file list, scope_block, merge_base present
  gather_change_data — scope_block heading is "Finalize Scope" (not "Summary/Review/Verification Scope")
  gather_change_data — result has all required JSON contract keys
  gather_change_data — source_changes is None in standalone mode
  gather_change_data — install_root=None defaults to source_root (standalone)
  gather_change_data — multi-directory file list
  gather_change_data — wrapper mode: source_changes populated, files_for_finders prefixed
  gather_change_data — error: not a git repo returns (None, error_message)

  cmd_gather_change_data (CLI handler):
    - missing --feature-dir exits 2
    - happy path: emits valid JSON to stdout (exit 0)
    - bad source_root exits 2
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _finalize._changes import (  # noqa: E402
    gather_change_data,
    cmd_gather_change_data,
)


# ---------------------------------------------------------------------------
# Git fixture helpers (mirroring tests/lib/_summarize/test_changes.py)
# ---------------------------------------------------------------------------


def _git(args, cwd, check=True):
    # type: (List[str], str, bool) -> subprocess.CompletedProcess
    return subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True, check=check
    )


def _init_repo(path, initial_branch="main"):
    # type: (str, str) -> None
    _git(["init", "-b", initial_branch, "."], cwd=path)
    _git(["config", "user.email", "test@example.com"], cwd=path)
    _git(["config", "user.name", "Test User"], cwd=path)
    _git(["config", "commit.gpgsign", "false"], cwd=path)


def _commit(path, message, files=None):
    # type: (str, str, Optional[List[str]]) -> str
    if files:
        _git(["add"] + files, cwd=path)
    else:
        _git(["add", "."], cwd=path)
    _git(["commit", "-m", message], cwd=path)
    result = _git(["rev-parse", "HEAD"], cwd=path)
    return result.stdout.strip()


def _write_file(root, relpath, content="x\n"):
    # type: (str, str, str) -> str
    abs_path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return abs_path


def _make_feature_repo(tmpdir):
    # type: (str,) -> dict
    """Create a repo with base on 'main' and a feature branch spanning >=2 dirs.

    Files touched on the feature branch:
      src/alpha.py      (new)
      src/beta.py       (new)
      tests/test_a.py   (new)

    Returns {"base_sha": ..., "head_sha": ...}
    """
    _init_repo(tmpdir)

    # Base commit on main.
    _write_file(tmpdir, "base.txt", "base\n")
    base_sha = _commit(tmpdir, "initial: base")

    # Feature branch.
    _git(["checkout", "-b", "spec/001-feat"], cwd=tmpdir)

    # WIP 1.
    _write_file(tmpdir, "src/alpha.py", "# alpha\nline2\nline3\n")
    _commit(tmpdir, "[WIP] add alpha")

    # WIP 2.
    _write_file(tmpdir, "src/beta.py", "# beta\nline2\n")
    _write_file(tmpdir, "tests/test_a.py", "# test\n")
    _commit(tmpdir, "[WIP] add beta + test")

    head_sha = _git(["rev-parse", "HEAD"], cwd=tmpdir).stdout.strip()
    return {"base_sha": base_sha, "head_sha": head_sha}


# ---------------------------------------------------------------------------
# TestGatherChangeDataHappyPath
# ---------------------------------------------------------------------------


class TestGatherChangeDataHappyPath(unittest.TestCase):
    """Core behavior: file list, heading, and required keys."""

    def test_file_list_matches_feature_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(err, msg="Expected no error, got: {0}".format(err))
            expected = sorted(["src/alpha.py", "src/beta.py", "tests/test_a.py"])
            self.assertEqual(result["files"], expected)
            self.assertEqual(result["file_count"], 3)

    def test_scope_block_uses_finalize_scope_heading(self):
        """The scope_block MUST say 'Finalize Scope', not Summary/Review/Verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(err)
            self.assertIn("=== Finalize Scope ===", result["scope_block"])
            self.assertNotIn("Review Scope", result["scope_block"])
            self.assertNotIn("Summary Scope", result["scope_block"])
            self.assertNotIn("Verification Scope", result["scope_block"])

    def test_merge_base_is_populated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(err)
            # merge_base should be the base commit on main.
            self.assertEqual(result["merge_base"], info["base_sha"])

    def test_result_has_required_contract_keys(self):
        """All JSON contract keys must be present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(err)
            for key in [
                "feature_dir", "source_root", "base", "merge_base", "head",
                "files", "files_for_finders", "file_count", "scope_block",
                "source_changes",
            ]:
                self.assertIn(key, result, msg="Missing key: {0}".format(key))

    def test_source_changes_none_in_standalone(self):
        """In standalone mode (source_root == install_root), source_changes is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(err)
            self.assertIsNone(result["source_changes"])

    def test_install_root_none_defaults_to_source_root(self):
        """install_root=None should default to source_root (standalone mode)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=None,
                base="main",
            )
            self.assertIsNone(err)
            self.assertIsNone(result["source_changes"])
            self.assertEqual(result["file_count"], 3)

    def test_files_for_finders_equals_files_in_standalone(self):
        """In standalone, files_for_finders should equal files (no prefix)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(err)
            self.assertEqual(result["files"], result["files_for_finders"])

    def test_multi_directory_file_list(self):
        """Files from src/ and tests/ are both captured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(err)
            dirs = {f.split("/")[0] for f in result["files"]}
            self.assertIn("src", dirs)
            self.assertIn("tests", dirs)

    def test_head_sha_is_current_head(self):
        """The head field should match the current HEAD SHA."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(err)
            self.assertEqual(result["head"], info["head_sha"])


# ---------------------------------------------------------------------------
# TestGatherChangeDataWrapperMode
# ---------------------------------------------------------------------------


class TestGatherChangeDataWrapperMode(unittest.TestCase):
    """Wrapper mode: source_root is a sub-directory of install_root."""

    def _make_wrapper_repo(self, install_root):
        # type: (str,) -> str
        """Create install_root/myproject/ as the source git repo."""
        source_root = os.path.join(install_root, "myproject")
        os.makedirs(source_root, exist_ok=True)
        _init_repo(source_root)

        # Base commit on main.
        _write_file(source_root, "main.py", "# main\n")
        _commit(source_root, "initial: base")

        # Feature branch.
        _git(["checkout", "-b", "spec/001-feat"], cwd=source_root)
        _write_file(source_root, "src/feature.py", "# feature\n")
        _write_file(source_root, "lib/helper.py", "# helper\n")
        _commit(source_root, "[WIP] add feature + helper")

        return source_root

    def test_source_changes_populated_in_wrapper_mode(self):
        with tempfile.TemporaryDirectory() as install_root:
            source_root = self._make_wrapper_repo(install_root)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=source_root,
                install_root=install_root,
                base="main",
            )
            self.assertIsNone(err, msg="Error: {0}".format(err))
            self.assertIsNotNone(result["source_changes"])
            sc = result["source_changes"]
            self.assertIn("src/feature.py", sc["files"])
            self.assertIn("lib/helper.py", sc["files"])

    def test_files_for_finders_prefixed_in_wrapper_mode(self):
        """files_for_finders should be prefixed with 'myproject/' in wrapper mode."""
        with tempfile.TemporaryDirectory() as install_root:
            source_root = self._make_wrapper_repo(install_root)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=source_root,
                install_root=install_root,
                base="main",
            )
            self.assertIsNone(err)
            for fp in result["files_for_finders"]:
                self.assertTrue(
                    fp.startswith("myproject/"),
                    msg="Expected 'myproject/' prefix, got: {0}".format(fp),
                )

    def test_wrapper_mode_scope_block_has_finalize_scope(self):
        with tempfile.TemporaryDirectory() as install_root:
            source_root = self._make_wrapper_repo(install_root)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=source_root,
                install_root=install_root,
                base="main",
            )
            self.assertIsNone(err)
            self.assertIn("=== Finalize Scope ===", result["scope_block"])
            self.assertNotIn("Summary Scope", result["scope_block"])


# ---------------------------------------------------------------------------
# TestGatherChangeDataErrors
# ---------------------------------------------------------------------------


class TestGatherChangeDataSourceChangesErrorShape(unittest.TestCase):
    """Finding 3: source_changes error shape when wrapper-mode source resolution fails.

    Architecture note: both the top-level and source-only calls to
    resolve_feature_scope use the same source_root, so any git-level failure
    in source_root fails the top-level too.  The {"error": str} source_changes
    shape is a purely defensive code path guarding against unexpected failures
    in the secondary source-only call (e.g. a future API change).  We test
    it by patching the secondary call to fail while the first succeeds —
    which is the only practical way to exercise this branch without the
    top-level failing alongside it.

    Assertions:
      - top-level result is (result_dict, None)  — non-fatal
      - result["source_changes"] == {"error": <str>}  — one key only
      - result["source_changes"] has no "files" key  — guards against KeyError
    """

    def test_source_changes_error_shape_on_secondary_failure(self):
        """Wrapper mode where the secondary source-only resolve_feature_scope call fails.

        Architecture note: both the primary and source-only calls share the same
        source_root, so any real git failure fails both.  We use mock.patch to
        intercept the second call — the only practical way to exercise this
        defensive code path without the top-level failing alongside it.
        """
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = os.path.join(tmpdir, "inner")
            install_root = os.path.join(tmpdir, "wrapper")
            os.makedirs(source_root, exist_ok=True)
            os.makedirs(install_root, exist_ok=True)

            # Build a real source repo on a feature branch.
            _init_repo(source_root)
            _write_file(source_root, "base.txt", "base\n")
            _commit(source_root, "initial: base")
            _git(["checkout", "-b", "spec/001-feat"], cwd=source_root)
            _write_file(source_root, "src/feat.py", "# feat\n")
            _commit(source_root, "[WIP] add feature")

            # Patch resolve_feature_scope on the _shared module so the
            # function-body `from _shared.feature_scope import resolve_feature_scope`
            # picks up the patched version.  The first call (primary) passes
            # through to the real implementation; the second (source-only) returns
            # a simulated error.
            import _shared.feature_scope as _fs_mod
            real_resolve = _fs_mod.resolve_feature_scope
            call_count = [0]

            def _patched_resolve(feature_dir, source_root, install_root=None, base=None, heading_label="Review Scope"):
                call_count[0] += 1
                if call_count[0] >= 2:
                    return {}, "simulated source-repo resolve failure"
                return real_resolve(
                    feature_dir=feature_dir,
                    source_root=source_root,
                    install_root=install_root,
                    base=base,
                    heading_label=heading_label,
                )

            with mock.patch.object(_fs_mod, "resolve_feature_scope", _patched_resolve):
                result, err = gather_change_data(
                    feature_dir="specs/001-feat",
                    source_root=source_root,
                    install_root=install_root,
                    base="main",
                )

            # Top-level must succeed (the primary call returned a real result).
            self.assertIsNone(err, msg="Expected top-level success, got error: {0!r}".format(err))
            self.assertIsNotNone(result)

            # source_changes must be the {"error": str} shape.
            sc = result["source_changes"]
            self.assertIsNotNone(sc, msg="source_changes should not be None in wrapper mode with error")
            self.assertIsInstance(sc, dict)
            self.assertIn(
                "error", sc,
                msg="source_changes must contain an 'error' key when source resolution fails",
            )
            # The error-shape dict must NOT have "files" — a consumer doing
            # sc["files"] without checking "error" first would KeyError.
            self.assertNotIn(
                "files", sc,
                msg=(
                    "source_changes error-shape must not contain 'files'; "
                    "got keys: {0}".format(sorted(sc.keys()))
                ),
            )
            self.assertEqual(
                list(sc.keys()), ["error"],
                msg="error-shape dict must have exactly one key 'error', got: {0}".format(sorted(sc.keys())),
            )


class TestGatherChangeDataErrors(unittest.TestCase):
    """Error handling: not a git repo returns (None, error_str)."""

    def test_not_a_git_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(result)
            self.assertIsNotNone(err)
            self.assertIn("git", err.lower())


# ---------------------------------------------------------------------------
# TestCmdGatherChangeDataCLI
# ---------------------------------------------------------------------------


class TestCmdGatherChangeDataCLI(unittest.TestCase):
    """CLI handler via argparse.Namespace simulation."""

    def _make_args(self, feature_dir="", source_root=".", install_root=None, base=None):
        # type: (str, str, Optional[str], Optional[str]) -> object
        class _Args:
            pass
        args = _Args()
        args.feature_dir = feature_dir
        args.source_root = source_root
        args.install_root = install_root
        args.base = base
        return args

    def test_missing_feature_dir_exits_2(self):
        args = self._make_args(feature_dir="")
        rc = cmd_gather_change_data(args)
        self.assertEqual(rc, 2)

    def test_happy_path_emits_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_repo(tmpdir)
            args = self._make_args(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            captured_out = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured_out
            try:
                rc = cmd_gather_change_data(args)
            finally:
                sys.stdout = old_stdout

            self.assertEqual(rc, 0)
            data = json.loads(captured_out.getvalue())
            self.assertIn("files", data)
            self.assertIn("merge_base", data)
            self.assertIn("scope_block", data)
            self.assertIn("=== Finalize Scope ===", data["scope_block"])

    def test_bad_source_root_exits_2(self):
        args = self._make_args(
            feature_dir="specs/001-feat",
            source_root="/nonexistent/path/that/does/not/exist",
            install_root="/nonexistent/path/that/does/not/exist",
            base="main",
        )
        captured_err = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured_err
        try:
            rc = cmd_gather_change_data(args)
        finally:
            sys.stderr = old_stderr
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
