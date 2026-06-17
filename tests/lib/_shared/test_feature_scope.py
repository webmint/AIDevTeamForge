"""Tests for src/devforge/lib/_shared/feature_scope.py.

All tests use real git repositories built in temporary directories via
subprocess git commands — no hand-authored diff fixtures.  This round-trips
through the actual git producer so the tests validate the real integration.

Coverage:
  resolve_feature_scope — happy path (WIP commits union)
  resolve_feature_scope — merge-base..HEAD diff (the assembled-feature shape)
  resolve_feature_scope — wrapper mode (source-root subdir, prefixed paths)
  resolve_feature_scope — no-changes case (HEAD == merge-base)
  resolve_feature_scope — auto-detect-base precedence
  resolve_feature_scope — no-base-found error
  resolve_feature_scope — not-a-git-repo error
  resolve_feature_scope — bad --base ref error
  resolve_feature_scope — heading_label parameter (default + custom)
  _prefix_paths — standalone, wrapper, empty list
  _render_scope_block — shape, heading_label override
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Path setup (mirrors the pattern in tests/lib/_shared/test_verify.py)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared.feature_scope import (  # noqa: E402
    _autodetect_base,
    _diff_name_only,
    _is_git_repo,
    _prefix_paths,
    _ref_exists,
    _render_scope_block,
    _resolve_head_sha,
    _resolve_origin_head,
    resolve_feature_scope,
)


# ---------------------------------------------------------------------------
# Git fixture helpers (mirrors tests/lib/_review/test_scope.py style)
# ---------------------------------------------------------------------------


def _run(args, cwd, check=True):
    # type: (List[str], str, bool) -> subprocess.CompletedProcess
    """Run a command in cwd and return the result."""
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

    def test_files_are_sorted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertEqual(result["files"], sorted(result["files"]))

    def test_head_sha_matches_git_rev_parse(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = _make_simple_feature_repo(tmpdir)

            result, _ = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertEqual(result["head"], meta["head_sha"])

    def test_merge_base_sha_is_fork_point(self):
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
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir, initial_branch="main")

            # Base commit — the fork point.
            _write_file(tmpdir, "base.txt", "base")
            _commit(tmpdir, "initial: base commit")

            # Feature branch diverges from main here.
            _git(["checkout", "-b", "feature/x"], cwd=tmpdir)
            _write_file(tmpdir, "feature.py", "# feature code")
            _commit(tmpdir, "feat: add feature.py")

            # Trunk advances AFTER the feature forked.
            _git(["checkout", "main"], cwd=tmpdir)
            _write_file(tmpdir, "trunk_advance.py", "# trunk only")
            _commit(tmpdir, "chore: trunk advance after fork")

            # Back on feature branch.
            _git(["checkout", "feature/x"], cwd=tmpdir)

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertIsNone(error)
            self.assertNotIn("trunk_advance.py", result["files"])
            self.assertIn("feature.py", result["files"])


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
          tmpdir/             <- install root (where specs/, .devforge/ live)
            my-project/      <- source root (the inner git repo)
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
            self.assertIn("src/widget.ts", result["files"])
            self.assertIn("src/util.ts", result["files"])

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
            _init_repo(tmpdir, initial_branch="trunk")
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
            )

            self.assertEqual(result, {})
            self.assertIsNotNone(error)
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

    def test_no_commits_returns_error(self):
        """A git repo with ZERO commits — HEAD does not resolve — must return an error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # git init only: no commits, HEAD cannot be resolved.
            _init_repo(tmpdir)

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertEqual(result, {})
            self.assertIsNotNone(error)
            # The error must mention the unresolvable HEAD / no commits.
            lower = error.lower()
            self.assertTrue(
                "cannot resolve head" in lower or "no commits" in lower,
                msg="Expected error to mention 'cannot resolve HEAD' or 'no commits', got: {0!r}".format(error),
            )


# ---------------------------------------------------------------------------
# TestDetachedHead
# ---------------------------------------------------------------------------


class TestDetachedHead(unittest.TestCase):
    """Detached HEAD still resolves — HEAD SHA is still valid."""

    def test_detached_head_works(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = _make_simple_feature_repo(tmpdir)

            # Detach HEAD to the first WIP commit SHA (only alpha.py exists so far).
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
# TestHeadingLabel — the Phase 0 parameterization
# ---------------------------------------------------------------------------


class TestHeadingLabel(unittest.TestCase):
    """The heading_label parameter drives the banner line of the scope block."""

    def test_default_heading_is_review_scope(self):
        """resolve_feature_scope with no heading_label → '=== Review Scope ==='."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
            )

            self.assertIsNone(error)
            self.assertIn("=== Review Scope ===", result["scope_block"])

    def test_custom_heading_label(self):
        """resolve_feature_scope with heading_label='Verification Scope'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_simple_feature_repo(tmpdir)

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=tmpdir,
                base="main",
                heading_label="Verification Scope",
            )

            self.assertIsNone(error)
            self.assertIn("=== Verification Scope ===", result["scope_block"])
            # Default heading must NOT appear when overridden.
            self.assertNotIn("=== Review Scope ===", result["scope_block"])

    def test_render_scope_block_default_heading(self):
        """_render_scope_block with no heading_label uses 'Review Scope'."""
        block = _render_scope_block(
            feature_dir="specs/001-x",
            source_root="/repo",
            base="main",
            merge_base="aabbcc",
            head="ddeeff",
            files=["a.py"],
            files_for_finders=["a.py"],
        )
        self.assertIn("=== Review Scope ===", block)

    def test_render_scope_block_custom_heading(self):
        """_render_scope_block with heading_label='Verification Scope'."""
        block = _render_scope_block(
            feature_dir="specs/001-x",
            source_root="/repo",
            base="main",
            merge_base="aabbcc",
            head="ddeeff",
            files=["a.py"],
            files_for_finders=["a.py"],
            heading_label="Verification Scope",
        )
        self.assertIn("=== Verification Scope ===", block)
        self.assertNotIn("=== Review Scope ===", block)

    def test_render_scope_block_arbitrary_label(self):
        """heading_label can be any string."""
        block = _render_scope_block(
            feature_dir="specs/001-x",
            source_root="/repo",
            base="main",
            merge_base="aa",
            head="bb",
            files=[],
            files_for_finders=[],
            heading_label="Custom Label",
        )
        self.assertIn("=== Custom Label ===", block)


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

    def test_path_with_spaces_in_names(self):
        """Paths and directory names that contain spaces must be handled correctly.

        _prefix_paths receives already-split file paths — the join/normpath
        logic must not mangle spaces.  The expected output is derived from the
        actual _prefix_paths semantics:
          rel_prefix = os.path.relpath("/wrapper/my project", "/wrapper")
                     = "my project"
          joined     = os.path.normpath(os.path.join("my project", "src/my file.py"))
                     = "my project/src/my file.py"  (forward-slash normalized)
        """
        result = _prefix_paths(["src/my file.py"], "/wrapper/my project", "/wrapper")
        self.assertEqual(result, ["my project/src/my file.py"])

    def test_path_with_spaces_integration(self):
        """Integration: a wrapper dir whose name contains a space produces prefixed paths."""
        with tempfile.TemporaryDirectory() as base_tmpdir:
            wrapper_root = os.path.join(base_tmpdir, "my project")
            source_root = os.path.join(wrapper_root, "inner-repo")
            os.makedirs(source_root)
            _init_repo(source_root)

            _write_file(source_root, "base.txt", "base")
            _commit(source_root, "initial commit")

            _git(["checkout", "-b", "spec/001-x"], cwd=source_root)
            _write_file(source_root, "src/widget.ts", "// widget")
            _commit(source_root, "[WIP] add widget")

            result, error = resolve_feature_scope(
                feature_dir="specs/001-x",
                source_root=source_root,
                install_root=wrapper_root,
                base="main",
            )

            self.assertIsNone(error)
            # files (source-relative) must be clean.
            self.assertIn("src/widget.ts", result["files"])
            # files_for_finders must be prefixed with the inner-repo dir name.
            self.assertIn("inner-repo/src/widget.ts", result["files_for_finders"])


# ---------------------------------------------------------------------------
# TestRenderScopeBlock (unit, no git needed)
# ---------------------------------------------------------------------------


class TestRenderScopeBlock(unittest.TestCase):
    def _block(self, files, files_for_finders=None, heading_label="Review Scope"):
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
            heading_label=heading_label,
        )

    def test_default_header_present(self):
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

    def test_custom_heading_label(self):
        block = self._block(["a.py"], heading_label="Verification Scope")
        self.assertIn("=== Verification Scope ===", block)
        self.assertNotIn("=== Review Scope ===", block)


# ---------------------------------------------------------------------------
# TestAutodetectBase (unit-level, real git)
# ---------------------------------------------------------------------------


class TestAutodetectBase(unittest.TestCase):
    def test_only_develop_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir, initial_branch="develop")
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")

            _git(["checkout", "-b", "spec/001-x"], cwd=tmpdir)
            _write_file(tmpdir, "g.txt")
            _commit(tmpdir, "[WIP] wip")

            detected = _autodetect_base(tmpdir)
            self.assertEqual(detected, "develop")

    def test_main_takes_precedence_over_develop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir, initial_branch="main")
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")
            _git(["checkout", "-b", "develop"], cwd=tmpdir)
            _write_file(tmpdir, "g.txt")
            _commit(tmpdir, "develop commit")
            _git(["checkout", "main"], cwd=tmpdir)

            detected = _autodetect_base(tmpdir)
            self.assertEqual(detected, "main")

    def test_returns_none_when_no_known_branch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir, initial_branch="trunk")
            _write_file(tmpdir, "f.txt")
            _commit(tmpdir, "init")

            detected = _autodetect_base(tmpdir)
            self.assertIsNone(detected)


if __name__ == "__main__":
    unittest.main()
