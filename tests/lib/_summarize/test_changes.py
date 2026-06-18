"""Tests for src/devforge/lib/_summarize/_changes.py.

Real-producer round-trip discipline:
  All tests build REAL git repositories in temporary directories via subprocess
  git commands.  No hand-authored diff fixtures.

Coverage:
  gather_change_data — happy path: file list, by_directory, insertions/deletions
  gather_change_data — multi-directory grouping (>=2 dirs)
  gather_change_data — insertions+deletions non-zero when lines are added/removed
  gather_change_data — zero-changes case (HEAD == merge-base, but separate branch)
  gather_change_data — explicit --base ref
  gather_change_data — error: not a git repo
  gather_change_data — wrapper mode: source_changes populated when source_root != install_root
  gather_change_data — standalone: source_changes is None when source_root == install_root

  _group_by_directory — root files grouped under "."
  _group_by_directory — nested paths grouped by top-level dir
  _group_by_directory — empty input
  _diff_stat — parse insertions + deletions from a real git diff --stat output
  _diff_stat — no changes yields (0, 0, "")

  cmd_gather_change_data (CLI handler):
    - missing --feature-dir exits 2
    - happy path: emits valid JSON to stdout

  Summary Scope heading: scope_block contains "=== Summary Scope ===" (not "Review Scope")
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

from _summarize._changes import (  # noqa: E402
    _diff_stat,
    _group_by_directory,
    gather_change_data,
    cmd_gather_change_data,
)


# ---------------------------------------------------------------------------
# Git fixture helpers (mirroring tests/lib/_shared/test_feature_scope.py)
# ---------------------------------------------------------------------------


def _run(args, cwd, check=True):
    # type: (List[str], str, bool) -> subprocess.CompletedProcess
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=check)


def _git(args, cwd, check=True):
    # type: (List[str], str, bool) -> subprocess.CompletedProcess
    return _run(["git"] + args, cwd, check=check)


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
    # type: (str) -> dict
    """Create a repo with base on 'main' and a feature branch spanning >=2 dirs.

    Files touched on the feature branch:
      src/alpha.py      (new, 3 lines)
      src/beta.py       (new, 2 lines)
      tests/test_a.py   (new, 1 line)

    Returns {"base_sha": ..., "head_sha": ...}
    """
    _init_repo(tmpdir)

    # Base commit on main.
    _write_file(tmpdir, "base.txt", "base\n")
    base_sha = _commit(tmpdir, "initial: base")

    # Feature branch.
    _git(["checkout", "-b", "spec/001-feat"], cwd=tmpdir)

    # WIP 1: add src/alpha.py (3 lines).
    _write_file(tmpdir, "src/alpha.py", "# alpha\nline2\nline3\n")
    _commit(tmpdir, "[WIP] add alpha")

    # WIP 2: add src/beta.py (2 lines) + tests/test_a.py (1 line).
    _write_file(tmpdir, "src/beta.py", "# beta\nline2\n")
    _write_file(tmpdir, "tests/test_a.py", "# test\n")
    _commit(tmpdir, "[WIP] add beta + test")

    head_result = _git(["rev-parse", "HEAD"], cwd=tmpdir)
    head_sha = head_result.stdout.strip()

    return {"base_sha": base_sha, "head_sha": head_sha}


# ---------------------------------------------------------------------------
# TestGroupByDirectory
# ---------------------------------------------------------------------------


class TestGroupByDirectory(unittest.TestCase):
    """Unit tests for _group_by_directory (no git required)."""

    def test_empty_input(self):
        self.assertEqual(_group_by_directory([]), {})

    def test_root_files_grouped_under_dot(self):
        result = _group_by_directory(["README.md", "setup.py"])
        self.assertIn(".", result)
        self.assertCountEqual(result["."], ["README.md", "setup.py"])

    def test_nested_paths_grouped_by_top_dir(self):
        files = ["src/a.py", "src/b.py", "tests/test_a.py"]
        result = _group_by_directory(files)
        self.assertIn("src", result)
        self.assertIn("tests", result)
        self.assertCountEqual(result["src"], ["src/a.py", "src/b.py"])
        self.assertCountEqual(result["tests"], ["tests/test_a.py"])

    def test_mixed_root_and_nested(self):
        files = ["Makefile", "src/main.py"]
        result = _group_by_directory(files)
        self.assertIn(".", result)
        self.assertIn("src", result)

    def test_sorted_keys(self):
        files = ["z/z.py", "a/a.py", "m/m.py"]
        result = _group_by_directory(files)
        self.assertEqual(list(result.keys()), ["a", "m", "z"])


# ---------------------------------------------------------------------------
# TestDiffStat
# ---------------------------------------------------------------------------


class TestDiffStat(unittest.TestCase):
    """Tests for _diff_stat using real git repos."""

    def test_zero_changes(self):
        """When merge_base == head, diff --stat returns 0 insertions/deletions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "a.txt", "hello\n")
            sha = _commit(tmpdir, "initial")
            # Diffing sha..sha → no changes.
            ins, dels, summary = _diff_stat(sha, sha, tmpdir)
            self.assertEqual(ins, 0)
            self.assertEqual(dels, 0)
            # Summary may be empty or missing.

    def test_nonzero_insertions(self):
        """Adding lines produces nonzero insertions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "a.txt", "line1\n")
            base_sha = _commit(tmpdir, "initial")

            _write_file(tmpdir, "b.txt", "new_line_1\nnew_line_2\nnew_line_3\n")
            _commit(tmpdir, "add b.txt")
            head_sha = _git(["rev-parse", "HEAD"], cwd=tmpdir).stdout.strip()

            ins, dels, summary = _diff_stat(base_sha, head_sha, tmpdir)
            self.assertGreater(ins, 0)
            self.assertEqual(dels, 0)
            self.assertIn("insertion", summary)

    def test_deletions(self):
        """Deleting lines produces nonzero deletions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "a.txt", "line1\nline2\nline3\n")
            base_sha = _commit(tmpdir, "initial")

            _write_file(tmpdir, "a.txt", "line1\n")  # truncate to 1 line
            _commit(tmpdir, "truncate a.txt")
            head_sha = _git(["rev-parse", "HEAD"], cwd=tmpdir).stdout.strip()

            ins, dels, summary = _diff_stat(base_sha, head_sha, tmpdir)
            self.assertGreater(dels, 0)


# ---------------------------------------------------------------------------
# TestGatherChangeData — happy path
# ---------------------------------------------------------------------------


class TestGatherChangeDataHappyPath(unittest.TestCase):
    """Core behavior: file list, by_directory, +/- totals, scope_block heading."""

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

    def test_by_directory_groups_two_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(err)
            by_dir = result["by_directory"]
            self.assertIn("src", by_dir)
            self.assertIn("tests", by_dir)
            self.assertCountEqual(by_dir["src"], ["src/alpha.py", "src/beta.py"])
            self.assertCountEqual(by_dir["tests"], ["tests/test_a.py"])

    def test_insertions_nonzero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(err)
            self.assertGreater(result["insertions"], 0)
            self.assertEqual(result["deletions"], 0)

    def test_scope_block_uses_summary_scope_heading(self):
        """The scope_block must say 'Summary Scope', NOT 'Review Scope'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_repo(tmpdir)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )
            self.assertIsNone(err)
            self.assertIn("=== Summary Scope ===", result["scope_block"])
            self.assertNotIn("Review Scope", result["scope_block"])
            self.assertNotIn("Verification Scope", result["scope_block"])

    def test_source_changes_none_in_standalone(self):
        """In standalone mode, source_changes is None."""
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

    def test_result_has_required_keys(self):
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
                "by_directory", "insertions", "deletions", "stat_summary",
                "source_changes",
            ]:
                self.assertIn(key, result, msg="Missing key: {0}".format(key))

    def test_install_root_none_defaults_to_source_root(self):
        """When install_root is None, it defaults to source_root (standalone)."""
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


# ---------------------------------------------------------------------------
# TestGatherChangeDataWrapperMode
# ---------------------------------------------------------------------------


class TestGatherChangeDataWrapperMode(unittest.TestCase):
    """Wrapper mode: source_root is a sub-directory of install_root."""

    def _make_wrapper_repo(self, install_root):
        # type: (str) -> None
        """Create a wrapper structure:
            install_root/  (the forge workspace — has .devforge/, specs/, CLAUDE.md, etc.)
            install_root/myproject/  (the source repo git lives here)
        """
        source_root = os.path.join(install_root, "myproject")
        os.makedirs(source_root, exist_ok=True)
        _init_repo(source_root)

        # Base commit on main.
        _write_file(source_root, "main.py", "# main\n")
        _commit(source_root, "initial: base")

        # Feature branch in the source repo.
        _git(["checkout", "-b", "spec/001-feat"], cwd=source_root)
        _write_file(source_root, "src/feature.py", "# feature\n")
        _write_file(source_root, "lib/helper.py", "# helper\n")
        _commit(source_root, "[WIP] add feature + helper")

        return source_root

    def test_wrapper_mode_source_changes_populated(self):
        with tempfile.TemporaryDirectory() as install_root:
            source_root = self._make_wrapper_repo(install_root)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=source_root,
                install_root=install_root,
                base="main",
            )
            self.assertIsNone(err, msg="Error: {0}".format(err))
            # In wrapper mode, source_changes must NOT be None.
            self.assertIsNotNone(result["source_changes"])
            sc = result["source_changes"]
            # Source repo files should be in the source_changes file list.
            self.assertIn("src/feature.py", sc["files"])
            self.assertIn("lib/helper.py", sc["files"])

    def test_wrapper_mode_files_for_finders_prefixed(self):
        """files_for_finders in the top-level result are prefixed with 'myproject/'."""
        with tempfile.TemporaryDirectory() as install_root:
            source_root = self._make_wrapper_repo(install_root)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=source_root,
                install_root=install_root,
                base="main",
            )
            self.assertIsNone(err)
            # files_for_finders are install-root relative.
            for fp in result["files_for_finders"]:
                self.assertTrue(
                    fp.startswith("myproject/"),
                    msg="Expected 'myproject/' prefix, got: {0}".format(fp),
                )

    def test_wrapper_mode_scope_block_heading(self):
        with tempfile.TemporaryDirectory() as install_root:
            source_root = self._make_wrapper_repo(install_root)
            result, err = gather_change_data(
                feature_dir="specs/001-feat",
                source_root=source_root,
                install_root=install_root,
                base="main",
            )
            self.assertIsNone(err)
            self.assertIn("=== Summary Scope ===", result["scope_block"])


# ---------------------------------------------------------------------------
# TestGatherChangeDataErrors
# ---------------------------------------------------------------------------


class TestGatherChangeDataErrors(unittest.TestCase):
    """Error handling: not a git repo."""

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
    """CLI handler tests via argparse.Namespace simulation."""

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
            self.assertIn("by_directory", data)
            self.assertIn("insertions", data)

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
