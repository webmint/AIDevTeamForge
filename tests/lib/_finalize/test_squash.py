"""Tests for src/devforge/lib/_finalize/_squash.py.

Real-producer round-trip discipline:
  All git-touching tests build REAL git repositories in temporary directories.
  No hand-authored subprocess output or mocked git calls.

Coverage:

  resolve_squash_base:
    - feature-branch arm: returns merge-base SHA (not None)
    - feature-branch arm: strategy == "merge-base"
    - feature-branch arm: is_feature_branch == True
    - on-DEFAULT_BRANCH arm: oldest [checkpoint] parent returned
    - on-DEFAULT_BRANCH arm: strategy == "checkpoint-parent"
    - on-DEFAULT_BRANCH arm: is_feature_branch == False
    - on-DEFAULT_BRANCH arm: no [checkpoint] commits → strategy == "none"
    - explicit --default-branch override used when provided
    - bad default-branch ref → error in result dict
    - wrapper mode: source_squash_base populated (not None)
    - standalone: source_squash_base is None

  check_pushed:
    - unpushed branch: is_pushed=False, commit_count > 0
    - pushed branch: is_pushed=True, commit_count == 0
    - no upstream (origin/<branch> doesn't exist): no_upstream=True, is_pushed=False
    - no remote configured: no_upstream=True, is_pushed=False
    - detached HEAD: branch=None, no_upstream=True

  _extract_ticket_id import:
    - verify the function is importable from _finalize._squash (not re-authored)
    - verify PROJ-123 extraction works (exercises the imported logic)

  cmd_resolve_squash_base (CLI handler):
    - happy path: emits JSON (exit 0) on a feature-branch repo
    - error case (bad install_root): emits JSON (exit 2)

  cmd_check_pushed (CLI handler):
    - no-upstream case: emits JSON (exit 0) with no_upstream=True
    - pushed case: emits JSON (exit 0) with is_pushed=True

  NO git reset --soft / git commit in _squash.py (Phase 3 gate):
    - static check: grep the source file to confirm absence
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

from _finalize._squash import (  # noqa: E402
    resolve_squash_base,
    check_pushed,
    cmd_resolve_squash_base,
    cmd_check_pushed,
    # _extract_ticket_id is imported inside _squash; we re-import here to verify
    _extract_ticket_id,  # type: ignore[attr-defined]
)


# ---------------------------------------------------------------------------
# Git fixture helpers
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


def _make_feature_branch_repo(tmpdir):
    # type: (str,) -> dict
    """Repo with a base commit on 'main' and a feature branch with WIP commits.

    Returns:
        {
            "base_sha":   str  — SHA of the initial main commit (the expected merge-base),
            "head_sha":   str  — SHA of the latest feature commit,
        }
    """
    _init_repo(tmpdir)

    # Trunk commit.
    _write_file(tmpdir, "base.txt", "base\n")
    base_sha = _commit(tmpdir, "initial: base")

    # Feature branch.
    _git(["checkout", "-b", "spec/001-feat"], cwd=tmpdir)
    _write_file(tmpdir, "a.py", "# a\n")
    _commit(tmpdir, "[WIP] add a")

    _write_file(tmpdir, "b.py", "# b\n")
    _commit(tmpdir, "[WIP] add b")

    head_sha = _git(["rev-parse", "HEAD"], cwd=tmpdir).stdout.strip()
    return {"base_sha": base_sha, "head_sha": head_sha}


def _make_on_default_branch_with_checkpoints(tmpdir):
    # type: (str,) -> dict
    """Repo on DEFAULT_BRANCH with [checkpoint] commits.

    Creates:
      commit A — "initial: base" (the expected squash base parent)
      commit B — "[checkpoint] Pre-feat: start"
      commit C — "[WIP] feat: work"
      commit D — "[checkpoint] Pre-feat: another"  (oldest = B → parent = A)

    Returns:
        {
            "squash_base_sha": str  — commit A SHA (parent of oldest [checkpoint]),
            "head_sha":        str  — commit D SHA,
        }
    """
    _init_repo(tmpdir)

    # stays on main (the default branch)
    _write_file(tmpdir, "base.txt", "base\n")
    base_sha = _commit(tmpdir, "initial: base")

    _write_file(tmpdir, "step1.py", "# step1\n")
    _commit(tmpdir, "[checkpoint] Pre-feat: start")

    _write_file(tmpdir, "work.py", "# work\n")
    _commit(tmpdir, "[WIP] feat: work")

    _write_file(tmpdir, "step2.py", "# step2\n")
    head_sha = _commit(tmpdir, "[checkpoint] Pre-feat: another")

    return {"squash_base_sha": base_sha, "head_sha": head_sha}


def _make_remote_repo(tmpdir):
    # type: (str,) -> dict
    """Create a bare remote and a clone with some local-only commits.

    Layout:
      tmpdir/remote.git  — bare repo (the "origin")
      tmpdir/clone       — working clone

    The clone starts in sync with remote (pushed state), then we add a local
    [WIP] commit so origin/main..HEAD is non-empty.

    Returns:
        {
            "clone_dir":   str  — path to the working clone,
            "pushed_sha":  str  — SHA that was pushed to remote,
        }
    """
    remote_path = os.path.join(tmpdir, "remote.git")
    clone_path = os.path.join(tmpdir, "clone")
    os.makedirs(remote_path, exist_ok=True)
    os.makedirs(clone_path, exist_ok=True)

    # Init bare remote.
    _git(["init", "--bare", "-b", "main", "."], cwd=remote_path)

    # Init clone with an initial commit, then push to remote.
    _init_repo(clone_path)
    _write_file(clone_path, "base.txt", "base\n")
    pushed_sha = _commit(clone_path, "initial: base")
    _git(["remote", "add", "origin", remote_path], cwd=clone_path)
    _git(["push", "-u", "origin", "main"], cwd=clone_path)

    return {"clone_dir": clone_path, "pushed_sha": pushed_sha}


# ---------------------------------------------------------------------------
# TestExtractTicketIdImport
# ---------------------------------------------------------------------------


class TestExtractTicketIdImport(unittest.TestCase):
    """Verify _extract_ticket_id is IMPORTED (not re-authored) from _implement._cmds_commit."""

    def test_importable_from_squash_module(self):
        """_extract_ticket_id must be importable from _finalize._squash."""
        from _finalize._squash import _extract_ticket_id as fn
        self.assertTrue(callable(fn))

    def test_extracts_jira_ticket(self):
        """Verify the imported function extracts PROJ-123 from branch names."""
        self.assertEqual(_extract_ticket_id("spec/PROJ-123-slugify"), "PROJ-123")
        self.assertEqual(_extract_ticket_id("feature/ABC-99-do-thing"), "ABC-99")
        self.assertEqual(_extract_ticket_id("MIG-42"), "MIG-42")

    def test_fallback_when_no_ticket(self):
        """When no [A-Z]+-[0-9]+ token exists, returns the full branch name."""
        self.assertEqual(_extract_ticket_id("develop-2.0-init"), "develop-2.0-init")
        self.assertEqual(_extract_ticket_id("main"), "main")

    def test_imported_not_reauthored(self):
        """Verify the _squash module imports from _implement._cmds_commit (not redefined)."""
        import _finalize._squash as squash_mod
        import _implement._cmds_commit as commit_mod

        # They must be the same function object.
        self.assertIs(
            squash_mod._extract_ticket_id,
            commit_mod._extract_ticket_id,
            msg="_extract_ticket_id must be imported from _implement._cmds_commit, not re-authored",
        )


# ---------------------------------------------------------------------------
# TestResolveSquashBase — feature-branch arm
# ---------------------------------------------------------------------------


class TestResolveSquashBaseFeatureBranch(unittest.TestCase):
    """resolve_squash_base on a feature branch: uses git merge-base."""

    def test_returns_merge_base_sha(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_feature_branch_repo(tmpdir)
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch="main",
            )
            self.assertIsNone(result["error"])
            self.assertEqual(result["install_squash_base"], info["base_sha"])

    def test_strategy_is_merge_base(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo(tmpdir)
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch="main",
            )
            self.assertIsNone(result["error"])
            self.assertEqual(result["strategy"], "merge-base")

    def test_is_feature_branch_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo(tmpdir)
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch="main",
            )
            self.assertIsNone(result["error"])
            self.assertTrue(result["is_feature_branch"])

    def test_default_branch_name_in_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo(tmpdir)
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch="main",
            )
            self.assertEqual(result["default_branch"], "main")

    def test_source_squash_base_none_in_standalone(self):
        """In standalone (source_root == install_root), source_squash_base is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo(tmpdir)
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch="main",
            )
            self.assertIsNone(result["error"])
            self.assertIsNone(result["source_squash_base"])

    def test_auto_detect_default_branch(self):
        """When default_branch=None, it should auto-detect 'main'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo(tmpdir)
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch=None,  # should auto-detect
            )
            self.assertIsNone(result["error"])
            self.assertIsNotNone(result["install_squash_base"])
            self.assertEqual(result["strategy"], "merge-base")


# ---------------------------------------------------------------------------
# TestResolveSquashBase — on-DEFAULT_BRANCH arm
# ---------------------------------------------------------------------------


class TestResolveSquashBaseOnDefaultBranch(unittest.TestCase):
    """resolve_squash_base on DEFAULT_BRANCH: uses oldest [checkpoint] parent."""

    def test_checkpoint_parent_returned(self):
        """The squash base should be the commit before the oldest [checkpoint]."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_on_default_branch_with_checkpoints(tmpdir)
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch="main",
            )
            self.assertIsNone(result["error"])
            self.assertEqual(result["install_squash_base"], info["squash_base_sha"])

    def test_strategy_is_checkpoint_parent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_on_default_branch_with_checkpoints(tmpdir)
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch="main",
            )
            self.assertIsNone(result["error"])
            self.assertEqual(result["strategy"], "checkpoint-parent")

    def test_is_feature_branch_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_on_default_branch_with_checkpoints(tmpdir)
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch="main",
            )
            self.assertIsNone(result["error"])
            self.assertFalse(result["is_feature_branch"])

    def test_no_checkpoint_commits_strategy_none(self):
        """When no [checkpoint] commits exist on DEFAULT_BRANCH, strategy is 'none'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "base.txt", "base\n")
            _commit(tmpdir, "initial: base")
            _write_file(tmpdir, "a.py", "# a\n")
            _commit(tmpdir, "[WIP] add a — no checkpoint at all")
            # Still on main, no [checkpoint] commit exists.
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch="main",
            )
            self.assertIsNone(result["error"])
            self.assertEqual(result["strategy"], "none")
            self.assertIsNone(result["install_squash_base"])


# ---------------------------------------------------------------------------
# TestResolveSquashBase — error paths
# ---------------------------------------------------------------------------


class TestResolveSquashBaseRootCommitCheckpoint(unittest.TestCase):
    """Finding 1: root-commit [checkpoint] must produce a distinguishable error.

    When the ONLY commit in the repo has a [checkpoint] message, the repo has
    no parent to squash back to.  resolve_squash_base must return a non-None
    error — NOT a silent strategy='none' (which is indistinguishable from the
    "no checkpoints exist" no-op).
    """

    def test_root_commit_is_checkpoint_returns_error(self):
        """Single-commit repo whose commit IS [checkpoint] → distinguishable error, not silent no-op.

        The disambiguation between "no checkpoints exist" (strategy='none', error=None)
        and "oldest checkpoint IS the root commit" (strategy='none', error=<message>)
        is via error — a non-None error means [checkpoint] commits were found but
        the squash is structurally impossible.  A None error + strategy='none' is
        the silent "nothing to do" path.  Both states return the same strategy value.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            # The ONLY commit has a [checkpoint] prefix — it is both the HEAD
            # and the initial (root) commit with no parent.
            _write_file(tmpdir, "base.txt", "base\n")
            _commit(tmpdir, "[checkpoint] Pre-feat: initial")

            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch="main",
            )

            # The key distinguisher: error must be non-None.
            # (strategy stays "none" in both the "no checkpoints" and root-commit-error
            # paths — but error=None vs error=<message> is the unambiguous discriminant.)
            self.assertIsNotNone(
                result["error"],
                msg=(
                    "root-commit [checkpoint] must set result['error'] to a non-None message "
                    "to distinguish it from the silent 'no checkpoints exist' no-op "
                    "(which also returns strategy='none' but with error=None)"
                ),
            )
            # The error message should mention the root/initial commit situation.
            self.assertTrue(
                any(
                    phrase in result["error"].lower()
                    for phrase in ("initial commit", "no parent", "root")
                ),
                msg="error message should describe the root-commit situation; got: {0!r}".format(
                    result["error"]
                ),
            )
            # Confirm the "no checkpoints" no-op test covers the error=None counterpart
            # (verified by TestResolveSquashBaseOnDefaultBranch.test_no_checkpoint_commits_strategy_none).
            # This test covers the other fork: checkpoints exist but squash is impossible.


class TestResolveSquashBaseErrors(unittest.TestCase):
    """Error conditions for resolve_squash_base."""

    def test_bad_default_branch_returns_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "base.txt", "base\n")
            _commit(tmpdir, "initial: base")
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch="nonexistent-branch",
            )
            self.assertIsNotNone(result["error"])
            self.assertIn("nonexistent-branch", result["error"])

    def test_no_auto_detect_in_empty_repo_returns_error(self):
        """In a repo with no main/develop/master, auto-detect fails → error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # init with a non-standard branch so main/develop/master don't exist
            _git(["init", "-b", "my-weird-branch", "."], cwd=tmpdir)
            _git(["config", "user.email", "t@t.com"], cwd=tmpdir)
            _git(["config", "user.name", "T"], cwd=tmpdir)
            _git(["config", "commit.gpgsign", "false"], cwd=tmpdir)
            _write_file(tmpdir, "a.txt", "a\n")
            _commit(tmpdir, "initial")
            result = resolve_squash_base(
                install_root=tmpdir,
                source_root=tmpdir,
                default_branch=None,
            )
            self.assertIsNotNone(result["error"])


# ---------------------------------------------------------------------------
# TestResolveSquashBase — wrapper mode
# ---------------------------------------------------------------------------


class TestResolveSquashBaseWrapperMode(unittest.TestCase):
    """resolve_squash_base in wrapper mode: source_squash_base populated."""

    def _make_wrapper_repos(self, tmpdir):
        # type: (str,) -> tuple
        """Create install_root with a feature branch, and source_root (inner) on its own feature."""
        install_root = os.path.join(tmpdir, "wrapper")
        source_root  = os.path.join(tmpdir, "wrapper", "myproject")
        os.makedirs(install_root, exist_ok=True)
        os.makedirs(source_root, exist_ok=True)

        # Install repo: feature branch.
        _init_repo(install_root)
        _write_file(install_root, "install-base.txt", "base\n")
        _commit(install_root, "initial: install base")
        _git(["checkout", "-b", "spec/001-feat"], cwd=install_root)
        _write_file(install_root, "spec.md", "# spec\n")
        _commit(install_root, "[WIP] install wip")

        # Source repo (inner): its own feature branch.
        _init_repo(source_root)
        _write_file(source_root, "main.py", "# main\n")
        _commit(source_root, "initial: source base")
        _git(["checkout", "-b", "spec/001-feat"], cwd=source_root)
        _write_file(source_root, "src/feat.py", "# feat\n")
        _commit(source_root, "[WIP] source wip")

        return install_root, source_root

    def test_source_squash_base_populated_in_wrapper_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_root, source_root = self._make_wrapper_repos(tmpdir)
            result = resolve_squash_base(
                install_root=install_root,
                source_root=source_root,
                default_branch="main",
            )
            self.assertIsNone(result["error"])
            # Both should be populated (the source repo has a 'main' branch).
            self.assertIsNotNone(result["install_squash_base"])
            self.assertIsNotNone(result["source_squash_base"])


# ---------------------------------------------------------------------------
# TestCheckPushed — core arms
# ---------------------------------------------------------------------------


class TestCheckPushedUnpushed(unittest.TestCase):
    """check_pushed when local commits are NOT yet pushed."""

    def test_unpushed_commits_is_pushed_false(self):
        """When local commits exist ahead of origin, is_pushed=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_remote_repo(tmpdir)
            clone_dir = info["clone_dir"]

            # Add a local-only commit.
            _write_file(clone_dir, "local.py", "# local\n")
            _commit(clone_dir, "[WIP] local only commit")

            result = check_pushed(clone_dir)
            self.assertIsNone(result["error"])
            self.assertFalse(result["is_pushed"])
            self.assertGreater(result["commit_count"], 0)
            self.assertFalse(result["no_upstream"])
            self.assertEqual(result["branch"], "main")

    def test_pushed_commits_is_pushed_true(self):
        """When no local commits ahead of origin, is_pushed=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_remote_repo(tmpdir)
            clone_dir = info["clone_dir"]
            # Clone is in sync with origin (no local commits added yet).
            result = check_pushed(clone_dir)
            self.assertIsNone(result["error"])
            self.assertTrue(result["is_pushed"])
            self.assertEqual(result["commit_count"], 0)
            self.assertFalse(result["no_upstream"])


class TestCheckPushedNoUpstream(unittest.TestCase):
    """check_pushed when there is no remote tracking branch."""

    def test_no_remote_at_all(self):
        """A repo with no remote configured → no_upstream=True, is_pushed=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "a.txt", "a\n")
            _commit(tmpdir, "initial")
            result = check_pushed(tmpdir)
            self.assertIsNone(result["error"])
            self.assertTrue(result["no_upstream"])
            self.assertFalse(result["is_pushed"])

    def test_remote_exists_but_branch_not_pushed(self):
        """A remote exists but origin/<branch> was never pushed → no_upstream=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            remote_path = os.path.join(tmpdir, "remote.git")
            clone_path  = os.path.join(tmpdir, "clone")
            os.makedirs(remote_path, exist_ok=True)
            os.makedirs(clone_path, exist_ok=True)

            _git(["init", "--bare", "-b", "main", "."], cwd=remote_path)
            _init_repo(clone_path)
            _write_file(clone_path, "a.txt", "a\n")
            _commit(clone_path, "initial")
            _git(["remote", "add", "origin", remote_path], cwd=clone_path)
            # NOT pushing — origin/main doesn't exist yet.

            result = check_pushed(clone_path)
            self.assertIsNone(result["error"])
            self.assertTrue(result["no_upstream"])
            self.assertFalse(result["is_pushed"])

    def test_detached_head(self):
        """Detached HEAD → branch=None, no_upstream=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "a.txt", "a\n")
            sha = _commit(tmpdir, "initial")
            # Detach the HEAD.
            _git(["checkout", "--detach", sha], cwd=tmpdir)
            result = check_pushed(tmpdir)
            self.assertIsNone(result["error"])
            self.assertIsNone(result["branch"])
            self.assertTrue(result["no_upstream"])
            self.assertFalse(result["is_pushed"])


# ---------------------------------------------------------------------------
# TestCmdResolveSquashBaseCLI
# ---------------------------------------------------------------------------


class TestCmdResolveSquashBaseCLI(unittest.TestCase):
    """CLI handler for resolve-squash-base."""

    def _make_args(self, install_root=".", source_root=None, default_branch=None):
        class _Args:
            pass
        args = _Args()
        args.install_root = install_root
        args.source_root = source_root or install_root
        args.default_branch = default_branch
        return args

    def test_happy_path_emits_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo(tmpdir)
            args = self._make_args(install_root=tmpdir, default_branch="main")
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = cmd_resolve_squash_base(args)
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0)
            data = json.loads(captured.getvalue())
            self.assertIn("install_squash_base", data)
            self.assertEqual(data["strategy"], "merge-base")

    def test_bad_install_root_exits_2_with_json(self):
        """Bad install_root should emit JSON to stdout AND exit 2."""
        args = self._make_args(
            install_root="/nonexistent/path/12345",
            default_branch="nonexistent",
        )
        captured_out = io.StringIO()
        captured_err = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = captured_out, captured_err
        try:
            rc = cmd_resolve_squash_base(args)
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
        self.assertEqual(rc, 2)
        # JSON must still be emitted to stdout so orchestrator can read it.
        data = json.loads(captured_out.getvalue())
        self.assertIsNotNone(data.get("error"))


# ---------------------------------------------------------------------------
# TestCmdCheckPushedCLI
# ---------------------------------------------------------------------------


class TestCmdCheckPushedCLI(unittest.TestCase):
    """CLI handler for check-pushed."""

    def _make_args(self, repo_root="."):
        class _Args:
            pass
        args = _Args()
        args.repo_root = repo_root
        return args

    def test_no_upstream_emits_json_exit_0(self):
        """A repo with no remote should emit JSON with no_upstream=True (exit 0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "a.txt", "a\n")
            _commit(tmpdir, "initial")
            args = self._make_args(repo_root=tmpdir)
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = cmd_check_pushed(args)
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0)
            data = json.loads(captured.getvalue())
            self.assertTrue(data["no_upstream"])
            self.assertFalse(data["is_pushed"])

    def test_pushed_case_emits_json(self):
        """A repo in sync with origin emits is_pushed=True (exit 0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_remote_repo(tmpdir)
            args = self._make_args(repo_root=info["clone_dir"])
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = cmd_check_pushed(args)
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0)
            data = json.loads(captured.getvalue())
            self.assertTrue(data["is_pushed"])
            self.assertFalse(data["no_upstream"])


# ---------------------------------------------------------------------------
# TestNoGitMutationInSquashPy — static check (Phase 3 guard)
# ---------------------------------------------------------------------------


class TestNoGitMutationInSquashPy(unittest.TestCase):
    """Phase 3 gate: _squash.py must NOT contain git mutation calls yet.

    The checks look for the actual subprocess argument tokens that would
    perform git history rewriting — NOT docstring mentions of the terms
    (a comment saying 'NO git reset --soft' is fine; an actual ["reset", "--soft"]
    list token is not).
    """

    def _read_squash_source(self):
        # type: () -> str
        squash_path = _LIB_DIR / "_finalize" / "_squash.py"
        return squash_path.read_text(encoding="utf-8")

    def test_no_reset_soft_token(self):
        """The literal token '--soft' as an argument to git reset must not appear."""
        src = self._read_squash_source()
        # The docstring says "NO git reset --soft" — that contains "--soft".
        # We look for the subprocess list form: ["reset", "--soft"] which would
        # signal actual mutation code, not documentation.
        self.assertNotIn('"--soft"', src, msg="Phase 3 gate: '\"--soft\"' must not appear as a code token in _squash.py yet")

    def test_no_git_commit_as_code_token(self):
        """The 'commit' verb must not appear as a subprocess argument token."""
        src = self._read_squash_source()
        # The mutation form would be: ["commit", ...] or "commit" as a git arg.
        # Specifically reject the exact code form used by git commit calls.
        # We look for the subprocess list pattern: ["commit"] which is the
        # unique marker for a git commit subprocess call.
        import ast
        # Parse the AST and look for list literals containing just "commit"
        # as an element (which would signal a git subcommand list).
        try:
            tree = ast.parse(src)
        except SyntaxError:
            self.fail("_squash.py has a syntax error")

        # Walk the AST looking for List nodes containing "commit" as an element
        # at the first position (the git subcommand position).
        class CommitFinder(ast.NodeVisitor):
            def __init__(self):
                self.found = False

            def visit_List(self, node):
                for elt in node.elts:
                    if isinstance(elt, ast.Constant) and elt.value == "commit":
                        self.found = True
                self.generic_visit(node)

        finder = CommitFinder()
        finder.visit(tree)
        self.assertFalse(
            finder.found,
            msg="Phase 3 gate: git 'commit' as a subprocess argument must not appear in _squash.py yet",
        )


if __name__ == "__main__":
    unittest.main()
