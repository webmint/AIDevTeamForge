"""Tests for src/devforge/lib/_review/_scope.py.

All tests use real git repositories built in temporary directories via
subprocess git commands — no hand-authored diff fixtures.  This round-trips
through the actual git producer so the tests validate the real integration.

Coverage:
  resolve_feature_scope — happy path (WIP commits union)
  resolve_feature_scope — wrapper mode (source-root subdir, prefixed paths)
  resolve_feature_scope — no-changes case (HEAD == merge-base)
  resolve_feature_scope — auto-detect-base precedence (only 'develop' exists)
  resolve_feature_scope — no-base-found error (exit 2 path)
  resolve_feature_scope — not-a-git-repo error
  resolve_feature_scope — bad --base ref error
  resolve_feature_scope — detached HEAD (still works — HEAD SHA resolves)
  render_scope_block helpers — scope block shape
  cmd_resolve_feature_scope — CLI integration via argparse round-trip
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import types
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

from _review._scope import (  # noqa: E402
    _autodetect_base,
    _diff_name_only,
    _is_git_repo,
    _prefix_paths,
    _ref_exists,
    _render_scope_block,
    _resolve_head_sha,
    _resolve_origin_head,
    cmd_resolve_feature_scope,
    resolve_feature_scope,
)


# ---------------------------------------------------------------------------
# Git fixture helpers
# ---------------------------------------------------------------------------


def _run(args, cwd, check=True):
    # type: (List[str], str, bool) -> subprocess.CompletedProcess
    """Run a git command in cwd and return the result."""
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _git(args, cwd, check=True):
    # type: (List[str], str, bool) -> subprocess.CompletedProcess
    return _run(["git"] + args, cwd, check=check)


def _init_repo(path, initial_branch="main"):
    # type: (str, str) -> None
    """Initialise a git repo with a signed-off identity for test commits."""
    _git(["init", "-b", initial_branch, "."], cwd=path)
    _git(["config", "user.email", "test@example.com"], cwd=path)
    _git(["config", "user.name", "Test User"], cwd=path)
    _git(["config", "commit.gpgsign", "false"], cwd=path)


def _commit(path, message, files=None):
    # type: (str, str, Optional[List[str]]) -> str
    """Stage all changes (or specific files) and commit.  Returns the SHA."""
    if files:
        _git(["add"] + files, cwd=path)
    else:
        _git(["add", "."], cwd=path)
    _git(["commit", "-m", message], cwd=path)
    result = _git(["rev-parse", "HEAD"], cwd=path)
    return result.stdout.strip()


def _write_file(root, relpath, content="x\n"):
    # type: (str, str, str) -> str
    """Write content to a file, creating parent dirs as needed."""
    abs_path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return abs_path


def _make_simple_feature_repo(tmpdir):
    # type: (str) -> dict
    """Create a repo with:
      - a base commit on 'main'
      - a feature branch 'spec/001-x' with 3 WIP commits touching different files

    Returns metadata dict.
    """
    _init_repo(tmpdir)

    # Base commit on main.
    _write_file(tmpdir, "base.txt", "base")
    base_sha = _commit(tmpdir, "initial: base commit")

    # Feature branch.
    _git(["checkout", "-b", "spec/001-x"], cwd=tmpdir)

    # WIP commit 1.
    _write_file(tmpdir, "src/alpha.py", "# alpha")
    wip1_sha = _commit(tmpdir, "[WIP] feat: add alpha")

    # WIP commit 2.
    _write_file(tmpdir, "src/beta.py", "# beta")
    _write_file(tmpdir, "tests/test_alpha.py", "# test")
    wip2_sha = _commit(tmpdir, "[WIP] feat: add beta + test")

    # WIP commit 3 — modify alpha (should still appear once in diff).
    _write_file(tmpdir, "src/alpha.py", "# alpha v2")
    wip3_sha = _commit(tmpdir, "[WIP] feat: revise alpha")

    head_result = _git(["rev-parse", "HEAD"], cwd=tmpdir)
    head_sha = head_result.stdout.strip()

    return {
        "base_sha": base_sha,
        "wip1_sha": wip1_sha,
        "wip2_sha": wip2_sha,
        "wip3_sha": wip3_sha,
        "head_sha": head_sha,
    }


# ---------------------------------------------------------------------------
# TestIsGitRepo
# ---------------------------------------------------------------------------


class TestIsGitRepo(unittest.TestCase):
    def test_git_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            self.assertTrue(_is_git_repo(tmpdir))

    def test_not_git_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertFalse(_is_git_repo(tmpdir))


# ---------------------------------------------------------------------------
# TestRefExists
# ---------------------------------------------------------------------------


class TestRefExists(unittest.TestCase):
    def test_main_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")
            self.assertTrue(_ref_exists("main", tmpdir))

    def test_nonexistent_ref(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")
            self.assertFalse(_ref_exists("no-such-branch", tmpdir))


# ---------------------------------------------------------------------------
# TestAutodetectBase
# ---------------------------------------------------------------------------


class TestAutodetectBaseOnlyDevelop(unittest.TestCase):
    """When only 'develop' exists as a local branch, it must be chosen."""

    def test_only_develop_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Init with 'develop' as the initial branch name.
            _init_repo(tmpdir, initial_branch="develop")
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")

            # Branch off to a feature branch (so develop != HEAD ref).
            _git(["checkout", "-b", "spec/001-x"], cwd=tmpdir)
            _write_file(tmpdir, "g.txt")
            _commit(tmpdir, "[WIP] wip")

            detected = _autodetect_base(tmpdir)
            self.assertEqual(detected, "develop")

    def test_main_takes_precedence_over_develop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Init on 'main', create 'develop' too.
            _init_repo(tmpdir, initial_branch="main")
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")
            _git(["checkout", "-b", "develop"], cwd=tmpdir)
            _write_file(tmpdir, "g.txt")
            _commit(tmpdir, "develop commit")
            _git(["checkout", "main"], cwd=tmpdir)

            detected = _autodetect_base(tmpdir)
            # 'main' should win over 'develop'.
            self.assertEqual(detected, "main")


class TestAutodetectBaseNoBase(unittest.TestCase):
    """When no known base ref exists, returns None."""

    def test_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Init on a branch that doesn't match any candidate.
            _init_repo(tmpdir, initial_branch="trunk")
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")

            detected = _autodetect_base(tmpdir)
            self.assertIsNone(detected)


# ---------------------------------------------------------------------------
# TestResolveFeatureScope — happy path (WIP commits union)
# ---------------------------------------------------------------------------


class TestResolveFeatureScopeWipUnion(unittest.TestCase):
    """The headline behavior: UNION of all WIP commit files is returned."""

    def test_wip_commits_union(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertIsNone(error, msg="Expected no error, got: {0}".format(error))

            # All three unique files touched across the 3 WIP commits.
            expected_files = sorted(["src/alpha.py", "src/beta.py", "tests/test_alpha.py"])
            self.assertEqual(result["files"], expected_files)
            self.assertEqual(result["file_count"], 3)

    def test_result_dict_has_all_required_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertIsNone(error)
            required_keys = {
                "feature_dir", "source_root", "base", "merge_base",
                "head", "files", "files_for_finders", "file_count", "scope_block",
            }
            self.assertEqual(required_keys, set(result.keys()))

    def test_base_recorded_in_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertEqual(result["base"], "main")

    def test_head_sha_matches_git_rev_parse(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = _make_simple_feature_repo(tmpdir)

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertEqual(result["head"], meta["head_sha"])

    def test_merge_base_sha_is_base_commit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = _make_simple_feature_repo(tmpdir)

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            # The merge-base of main and feature branch HEAD should be the
            # initial commit on main (the only common ancestor).
            self.assertEqual(result["merge_base"], meta["base_sha"])

    def test_scope_block_contains_key_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            block = result["scope_block"]
            self.assertIn("=== Review Scope ===", block)
            self.assertIn("Feature dir", block)
            self.assertIn("Source root", block)
            self.assertIn("File count  : 3", block)
            self.assertIn("src/alpha.py", block)

    def test_files_are_sorted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertEqual(result["files"], sorted(result["files"]))

    def test_autodetect_base(self):
        """When --base is omitted and 'main' exists, it is auto-detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            # No base passed — should auto-detect 'main'.
            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
            )

            self.assertIsNone(error)
            self.assertEqual(result["base"], "main")
            expected_files = sorted(["src/alpha.py", "src/beta.py", "tests/test_alpha.py"])
            self.assertEqual(result["files"], expected_files)


# ---------------------------------------------------------------------------
# TestMergeBaseIsolation — trunk commits after fork must be excluded
# ---------------------------------------------------------------------------


class TestMergeBaseIsolation(unittest.TestCase):
    """Regression: git diff diffs from the frozen merge-base SHA, so a trunk
    commit made AFTER the feature forked must NOT appear in the feature scope."""

    def test_trunk_advance_excluded_from_feature_scope(self):
        """Trunk advances after fork — trunk_advance.py must not appear in result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir, initial_branch="main")

            # Step 1: base commit — the fork point.
            _write_file(tmpdir, "base.txt", "base")
            _commit(tmpdir, "initial: base commit")

            # Step 2: feature branch diverges from main here.
            _git(["checkout", "-b", "feature/x"], cwd=tmpdir)
            _write_file(tmpdir, "feature.py", "# feature code")
            _commit(tmpdir, "feat: add feature.py")

            # Step 3: trunk advances AFTER the feature forked.
            _git(["checkout", "main"], cwd=tmpdir)
            _write_file(tmpdir, "trunk_advance.py", "# trunk only")
            _commit(tmpdir, "chore: trunk advance after fork")

            # Step 4: back on feature branch.
            _git(["checkout", "feature/x"], cwd=tmpdir)

            # Step 5: compute feature scope.
            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertIsNone(error, msg="Expected no error, got: {0}".format(error))

            # Step 6: trunk_advance.py must NOT appear — it is on trunk, not feature.
            self.assertNotIn(
                "trunk_advance.py",
                result["files"],
                msg="trunk_advance.py committed to trunk after fork must be excluded",
            )

            # Step 7: feature.py MUST appear — it IS part of the feature.
            self.assertIn(
                "feature.py",
                result["files"],
                msg="feature.py committed on feature branch must be included",
            )


# ---------------------------------------------------------------------------
# TestResolveFeatureScope — no-changes case
# ---------------------------------------------------------------------------


class TestResolveFeatureScopeNoChanges(unittest.TestCase):
    """HEAD == merge-base: empty file list is a valid result, not an error."""

    def test_empty_diff_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "base.txt", "base")
            _commit(tmpdir, "initial commit")

            # HEAD IS main — no feature commits yet.
            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertIsNone(error)
            self.assertEqual(result["files"], [])
            self.assertEqual(result["file_count"], 0)

    def test_scope_block_shows_none_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "base.txt", "base")
            _commit(tmpdir, "initial commit")

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertIn("none", result["scope_block"].lower())


# ---------------------------------------------------------------------------
# TestResolveFeatureScope — wrapper mode
# ---------------------------------------------------------------------------


class TestResolveFeatureScopeWrapperMode(unittest.TestCase):
    """Source tree in a subdir of the install root — paths must be prefixed."""

    def _make_wrapper_repo(self, tmpdir):
        # type: (str) -> str
        """Create a wrapper layout:
          tmpdir/             ← install root (where specs/, .devforge/ live)
            my-project/      ← source root (the inner git repo)
              ...
        """
        source_root = os.path.join(tmpdir, "my-project")
        os.makedirs(source_root)
        _init_repo(source_root)

        # Base commit on main.
        _write_file(source_root, "base.txt", "base")
        _commit(source_root, "initial commit")

        # Feature branch with WIP commits.
        _git(["checkout", "-b", "spec/001-x"], cwd=source_root)
        _write_file(source_root, "src/widget.ts", "// widget")
        _commit(source_root, "[WIP] add widget")
        _write_file(source_root, "src/util.ts", "// util")
        _commit(source_root, "[WIP] add util")

        return source_root

    def test_files_for_finders_are_prefixed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = self._make_wrapper_repo(tmpdir)

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=source_root,
                install_root=tmpdir,
                base="main",
            )

            self.assertIsNone(error)
            # Source-relative files are the raw diff paths.
            self.assertIn("src/widget.ts", result["files"])
            self.assertIn("src/util.ts", result["files"])

            # Finder-facing files have the 'my-project/' prefix.
            for fp in result["files_for_finders"]:
                self.assertTrue(
                    fp.startswith("my-project/"),
                    msg="Expected 'my-project/' prefix, got: {0!r}".format(fp)
                )

    def test_source_relative_files_unchanged(self):
        """files (source-relative) must NOT have the wrapper prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = self._make_wrapper_repo(tmpdir)

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=source_root,
                install_root=tmpdir,
                base="main",
            )

            for fp in result["files"]:
                self.assertFalse(
                    fp.startswith("my-project/"),
                    msg="Source-relative file should NOT have prefix: {0!r}".format(fp)
                )

    def test_standalone_no_prefix(self):
        """When install_root == source_root, files_for_finders == files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                install_root=tmpdir,
                base="main",
            )

            self.assertEqual(result["files"], result["files_for_finders"])

    def test_standalone_none_install_root(self):
        """When install_root is None (default), files_for_finders == files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                install_root=None,
                base="main",
            )

            self.assertEqual(result["files"], result["files_for_finders"])

    def test_git_runs_in_source_root(self):
        """Git must run in the source_root (inner repo), not the install root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = self._make_wrapper_repo(tmpdir)

            # If git ran in install_root (tmpdir), it would fail — tmpdir is
            # not a git repo.  A successful result proves git ran in source_root.
            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=source_root,
                install_root=tmpdir,
                base="main",
            )

            self.assertIsNone(error, msg="Git must run in source_root, not install_root")
            self.assertGreater(result["file_count"], 0)

    def test_scope_block_uses_prefixed_paths(self):
        """The scope block must display finder-facing (prefixed) paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = self._make_wrapper_repo(tmpdir)

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=source_root,
                install_root=tmpdir,
                base="main",
            )

            block = result["scope_block"]
            # Scope block should show prefixed path (for finders).
            self.assertIn("my-project/src/widget.ts", block)


# ---------------------------------------------------------------------------
# TestResolveFeatureScope — error paths
# ---------------------------------------------------------------------------


class TestResolveFeatureScopeErrors(unittest.TestCase):

    def test_not_a_git_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )
            self.assertEqual(result, {})
            self.assertIsNotNone(error)
            self.assertIn("not a git repository", error)

    def test_bad_base_ref(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="no-such-branch",
            )

            self.assertEqual(result, {})
            self.assertIsNotNone(error)
            self.assertIn("no-such-branch", error)
            self.assertIn("does not exist", error)

    def test_no_auto_detectable_base(self):
        """When no known trunk exists and --base is not given, error includes advice."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use 'trunk' so none of main/develop/master match.
            _init_repo(tmpdir, initial_branch="trunk")
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
            )

            self.assertEqual(result, {})
            self.assertIsNotNone(error)
            # Error should advise passing --base explicitly.
            self.assertIn("--base", error)

    def test_error_returns_empty_dict(self):
        """On error the result dict is always empty (not partially populated)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
            )
            self.assertIsInstance(result, dict)
            self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# TestResolveFeatureScopeDetachedHead
# ---------------------------------------------------------------------------


class TestDetachedHead(unittest.TestCase):
    """Detached HEAD still resolves — HEAD SHA is still valid."""

    def test_detached_head_works(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = _make_simple_feature_repo(tmpdir)

            # Detach HEAD to the WIP commit SHA.
            _git(["checkout", meta["wip1_sha"]], cwd=tmpdir, check=False)

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            # Detached HEAD resolves; files from wip1 only (alpha.py touched so far).
            self.assertIsNone(error)
            self.assertIn("src/alpha.py", result["files"])


# ---------------------------------------------------------------------------
# TestPrefixPaths (unit, no git needed)
# ---------------------------------------------------------------------------


class TestPrefixPaths(unittest.TestCase):
    def test_standalone_no_change(self):
        files = ["src/a.py", "tests/b.py"]
        result = _prefix_paths(files, "/repo", "/repo")
        self.assertEqual(result, files)

    def test_wrapper_adds_prefix(self):
        files = ["src/a.py", "tests/b.py"]
        result = _prefix_paths(files, "/wrapper/proj", "/wrapper")
        self.assertEqual(result, ["proj/src/a.py", "proj/tests/b.py"])

    def test_empty_file_list(self):
        result = _prefix_paths([], "/wrapper/proj", "/wrapper")
        self.assertEqual(result, [])

    def test_forward_slash_normalization(self):
        """Paths must use forward slashes regardless of os.sep."""
        files = ["src/a.py"]
        result = _prefix_paths(files, "/wrapper/proj", "/wrapper")
        for fp in result:
            self.assertNotIn("\\", fp)


# ---------------------------------------------------------------------------
# TestRenderScopeBlock (unit, no git needed)
# ---------------------------------------------------------------------------


class TestRenderScopeBlock(unittest.TestCase):
    def _block(self, files, files_for_finders=None):
        if files_for_finders is None:
            files_for_finders = files
        return _render_scope_block(
            feature_dir="specs/001-x",
            source_root="/repo",
            base="main",
            merge_base="aabbcc",
            head="ddeeff",
            files=files,
            files_for_finders=files_for_finders,
        )

    def test_header_present(self):
        block = self._block(["a.py"])
        self.assertIn("=== Review Scope ===", block)

    def test_file_count_in_block(self):
        block = self._block(["a.py", "b.py"])
        self.assertIn("File count  : 2", block)

    def test_files_listed_when_25_or_fewer(self):
        files = ["f{0}.py".format(i) for i in range(25)]
        block = self._block(files)
        for fp in files:
            self.assertIn(fp, block)

    def test_files_omitted_when_more_than_25(self):
        files = ["f{0}.py".format(i) for i in range(26)]
        block = self._block(files)
        self.assertIn("26 files", block)
        self.assertIn("omitted", block)

    def test_no_changes_message(self):
        block = self._block([])
        self.assertIn("none", block.lower())

    def test_merge_base_and_head_in_block(self):
        block = self._block(["a.py"])
        self.assertIn("aabbcc", block)
        self.assertIn("ddeeff", block)

    def test_finder_prefixed_paths_displayed(self):
        """When files_for_finders differ from files, the block shows finder paths."""
        block = _render_scope_block(
            feature_dir="specs/001-x",
            source_root="/wrapper/proj",
            base="main",
            merge_base="aa",
            head="bb",
            files=["src/a.py"],
            files_for_finders=["proj/src/a.py"],
        )
        self.assertIn("proj/src/a.py", block)
        # The raw source-relative path should not appear (finders see the prefixed one).
        # (The source_root line contains the path but as the source_root value.)


# ---------------------------------------------------------------------------
# TestCmdResolveFeatureScope — CLI integration
# ---------------------------------------------------------------------------


class TestCmdResolveFeatureScope(unittest.TestCase):
    """Test the CLI handler via a fake argparse Namespace."""

    def _make_args(self, tmpdir, source_root=None, install_root=None, base=None, feature=None):
        ns = types.SimpleNamespace()
        ns.feature = feature or "specs/001-x"
        ns.source_root = source_root or tmpdir
        ns.install_root = install_root
        ns.base = base
        return ns

    def test_success_emits_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            import io
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = cmd_resolve_feature_scope(self._make_args(tmpdir, base="main"))
            finally:
                sys.stdout = old_stdout

            self.assertEqual(rc, 0)
            data = json.loads(captured.getvalue())
            self.assertIn("files", data)
            self.assertEqual(sorted(data["files"]),
                             ["src/alpha.py", "src/beta.py", "tests/test_alpha.py"])

    def test_not_a_git_repo_exits_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import io
            captured_err = io.StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured_err
            try:
                rc = cmd_resolve_feature_scope(self._make_args(tmpdir, base="main"))
            finally:
                sys.stderr = old_stderr

            self.assertEqual(rc, 2)
            self.assertIn("not a git repository", captured_err.getvalue())

    def test_bad_base_ref_exits_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")

            import io
            captured_err = io.StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured_err
            try:
                rc = cmd_resolve_feature_scope(
                    self._make_args(tmpdir, base="no-such-branch")
                )
            finally:
                sys.stderr = old_stderr

            self.assertEqual(rc, 2)
            self.assertIn("no-such-branch", captured_err.getvalue())

    def test_no_auto_base_exits_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir, initial_branch="trunk")
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")

            import io
            captured_err = io.StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured_err
            try:
                rc = cmd_resolve_feature_scope(self._make_args(tmpdir, base=None))
            finally:
                sys.stderr = old_stderr

            self.assertEqual(rc, 2)

    def test_empty_diff_exits_0(self):
        """No feature commits yet (HEAD == merge-base) → exit 0, empty files list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")

            import io
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = cmd_resolve_feature_scope(self._make_args(tmpdir, base="main"))
            finally:
                sys.stdout = old_stdout

            self.assertEqual(rc, 0)
            data = json.loads(captured.getvalue())
            self.assertEqual(data["files"], [])
            self.assertEqual(data["file_count"], 0)

    def test_cli_via_main_dispatch(self):
        """Verify the verb is wired into _cli.py's _SUBCOMMAND_REGISTRY."""
        from _review._cli import build_parser
        parser = build_parser()
        args = parser.parse_args([
            "resolve-feature-scope",
            "--feature", "specs/001-x",
            "--base", "main",
        ])
        # Should have the func attribute pointing to our handler wrapper.
        self.assertTrue(hasattr(args, "func"))
        self.assertEqual(args.feature, "specs/001-x")
        self.assertEqual(args.base, "main")


# ---------------------------------------------------------------------------
# TestAutodetectBasePrecedenceMatrix
# ---------------------------------------------------------------------------


class TestAutodetectBasePrecedenceMatrix(unittest.TestCase):
    """Verify precedence: main beats develop, develop beats master."""

    def _repo_with_branches(self, tmpdir, branches):
        # type: (str, List[str]) -> None
        _init_repo(tmpdir, initial_branch=branches[0])
        _write_file(tmpdir, "f.txt")
        _commit(tmpdir, "init on {0}".format(branches[0]))
        for b in branches[1:]:
            _git(["checkout", "-b", b], cwd=tmpdir)
            _write_file(tmpdir, "{0}.txt".format(b), b)
            _commit(tmpdir, "commit on {0}".format(b))
        # Switch to feature branch so base != HEAD.
        _git(["checkout", "-b", "feat"], cwd=tmpdir)
        _write_file(tmpdir, "feat.txt")
        _commit(tmpdir, "feat commit")

    def test_main_beats_develop_and_master(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._repo_with_branches(tmpdir, ["main", "develop", "master"])
            self.assertEqual(_autodetect_base(tmpdir), "main")

    def test_develop_beats_master(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._repo_with_branches(tmpdir, ["develop", "master"])
            self.assertEqual(_autodetect_base(tmpdir), "develop")

    def test_master_alone(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._repo_with_branches(tmpdir, ["master"])
            self.assertEqual(_autodetect_base(tmpdir), "master")


if __name__ == "__main__":
    unittest.main()
