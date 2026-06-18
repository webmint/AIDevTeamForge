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

  Phase 3 — squash (git-mutating verb):
    - standalone: several [WIP] commits → squash --confirm → exactly ONE resulting commit
    - standalone: squashed file changes preserved (reset --soft keeps the staged tree)
    - standalone: commit subject == install_message (passed by caller)
    - standalone: COMMIT_ATTRIBUTION appended when config says Yes
    - standalone: no attribution when config is absent/No
    - wrapper mode: install repo → ONE commit with attribution; source repo → ONE commit
      with [TICKET-ID] - Description subject and NO Co-Authored-By/trace
    - source repo NEVER receives attribution regardless of config (D5 hard invariant)
    - already-pushed refusal: branch on tracking remote → refused, HEAD unchanged
    - --confirm gate: without --confirm → dry-run (no mutation), HEAD unchanged
    - dry-run: returns preview JSON with install/source messages, confirmed=false
    - idempotent no-op: strategy="none" (no WIP/checkpoint commits) → no mutation
    - root-commit-checkpoint error case → surfaced in error, no mutation
    - dangerous-state detection: danger_state=True when reset succeeds but commit fails
    - cmd_squash CLI handler: dry-run case emits JSON, exits 0
    - cmd_squash CLI handler: --confirm case mutates, emits result JSON
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
    squash,
    cmd_resolve_squash_base,
    cmd_check_pushed,
    cmd_squash,
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
# Test helpers used by Phase 3 tests
# ---------------------------------------------------------------------------


def _make_feature_branch_repo_with_files(tmpdir):
    # type: (str,) -> dict
    """Repo with a base commit on 'main' and a feature branch with [WIP] commits.

    Creates file changes on the feature branch so we can assert the squash
    preserves them (reset --soft keeps the staging area).

    Returns {base_sha, feature_branch, wip1_content, wip2_content}.
    """
    _init_repo(tmpdir)

    _write_file(tmpdir, "base.txt", "base\n")
    base_sha = _commit(tmpdir, "initial: base")

    _git(["checkout", "-b", "spec/001-my-feature"], cwd=tmpdir)
    _write_file(tmpdir, "feat_a.py", "# feat_a\n")
    _commit(tmpdir, "[WIP] add feat_a")

    _write_file(tmpdir, "feat_b.py", "# feat_b\n")
    _commit(tmpdir, "[WIP] add feat_b")

    return {
        "base_sha":      base_sha,
        "feature_branch": "spec/001-my-feature",
    }


def _write_project_config(repo_root, attribution_value=None):
    # type: (str, Optional[str]) -> None
    """Write a minimal .devforge/project-config.json to repo_root.

    When attribution_value is None, writes an empty config (no COMMIT_ATTRIBUTION key).
    When attribution_value is a string, writes it as COMMIT_ATTRIBUTION.
    """
    import json as _json
    devforge = os.path.join(repo_root, ".devforge")
    os.makedirs(devforge, exist_ok=True)
    config = {}  # type: dict
    if attribution_value is not None:
        config["COMMIT_ATTRIBUTION"] = attribution_value
    with open(os.path.join(devforge, "project-config.json"), "w", encoding="utf-8") as fh:
        _json.dump(config, fh)


def _commit_count(repo_root, since_sha):
    # type: (str, str) -> int
    """Count commits on HEAD since (but not including) since_sha."""
    result = _git(["log", "--oneline", "{0}..HEAD".format(since_sha)], cwd=repo_root)
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    return len(lines)


def _head_sha(repo_root):
    # type: (str,) -> str
    return _git(["rev-parse", "HEAD"], cwd=repo_root).stdout.strip()


def _commit_message(repo_root, sha="HEAD"):
    # type: (str, str) -> str
    return _git(["log", "-1", "--format=%B", sha], cwd=repo_root).stdout.strip()


# ---------------------------------------------------------------------------
# TestSquashStandalone — standalone mode, various confirmation/no-op paths
# ---------------------------------------------------------------------------


class TestSquashStandaloneConfirm(unittest.TestCase):
    """squash verb in standalone mode with --confirm."""

    def test_exactly_one_commit_after_squash(self):
        """Several [WIP] commits → squash → exactly ONE commit since the base."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_feature_branch_repo_with_files(tmpdir)
            result = squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001-my-feature): implement widget",
                source_message="",  # standalone — not used
                confirm=True,
                default_branch="main",
            )
            self.assertIsNone(result.get("error"), msg=result)
            repo_out = result["install_repo"]
            self.assertIsNotNone(repo_out)
            self.assertFalse(repo_out.get("refused"), msg=repo_out)
            self.assertFalse(repo_out.get("danger_state"), msg=repo_out)
            self.assertIsNone(repo_out.get("error"), msg=repo_out)
            # Exactly one commit since the merge-base.
            self.assertEqual(
                _commit_count(tmpdir, info["base_sha"]),
                1,
                msg="Expected exactly 1 commit since the merge-base after squash",
            )

    def test_squashed_commit_subject_matches_install_message(self):
        """The squashed commit message must match install_message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo_with_files(tmpdir)
            squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001-my-feature): implement widget",
                source_message="",
                confirm=True,
                default_branch="main",
            )
            msg = _commit_message(tmpdir)
            self.assertIn("feat(001-my-feature): implement widget", msg)

    def test_file_changes_preserved_after_squash(self):
        """reset --soft keeps the working tree; files introduced by WIP commits exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo_with_files(tmpdir)
            squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001-my-feature): implement widget",
                source_message="",
                confirm=True,
                default_branch="main",
            )
            # Both files created by the WIP commits must be tracked in the squashed commit.
            result = _git(
                ["show", "--name-only", "--format=", "HEAD"],
                cwd=tmpdir,
            )
            tracked = result.stdout
            self.assertIn("feat_a.py", tracked)
            self.assertIn("feat_b.py", tracked)

    def test_attribution_appended_when_config_says_yes(self):
        """When COMMIT_ATTRIBUTION is set, the squashed commit body includes it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo_with_files(tmpdir)
            attribution = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
            _write_project_config(tmpdir, attribution_value=attribution)
            squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001-my-feature): widget",
                source_message="",
                confirm=True,
                default_branch="main",
            )
            msg = _commit_message(tmpdir)
            self.assertIn("Co-Authored-By", msg,
                          msg="Attribution must appear in commit when COMMIT_ATTRIBUTION is set")

    def test_no_attribution_when_config_absent(self):
        """When no COMMIT_ATTRIBUTION config, the squashed commit has no trailer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo_with_files(tmpdir)
            # No .devforge/project-config.json written — attribution absent.
            squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001-my-feature): widget",
                source_message="",
                confirm=True,
                default_branch="main",
            )
            msg = _commit_message(tmpdir)
            self.assertNotIn("Co-Authored-By", msg,
                             msg="No Co-Authored-By trailer expected when attribution absent")

    def test_head_sha_returned_in_result(self):
        """After a successful squash, head_sha in the result matches repo HEAD."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo_with_files(tmpdir)
            result = squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001-my-feature): widget",
                source_message="",
                confirm=True,
                default_branch="main",
            )
            repo_out = result["install_repo"]
            actual_head = _head_sha(tmpdir)
            self.assertEqual(repo_out["head_sha"], actual_head)


# ---------------------------------------------------------------------------
# TestSquashDryRun — without --confirm: preview, no mutation
# ---------------------------------------------------------------------------


class TestSquashDryRun(unittest.TestCase):
    """squash without --confirm must emit a preview JSON and mutate nothing."""

    def test_dry_run_does_not_mutate_head(self):
        """Without --confirm, HEAD must be unchanged after squash call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo_with_files(tmpdir)
            head_before = _head_sha(tmpdir)
            squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001-my-feature): widget",
                source_message="",
                confirm=False,  # no --confirm
                default_branch="main",
            )
            head_after = _head_sha(tmpdir)
            self.assertEqual(head_before, head_after,
                             msg="HEAD must not change in dry-run mode")

    def test_dry_run_confirmed_false(self):
        """Dry-run result must have confirmed=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo_with_files(tmpdir)
            result = squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001-my-feature): widget",
                source_message="",
                confirm=False,
                default_branch="main",
            )
            self.assertFalse(result["confirmed"])

    def test_dry_run_returns_preview_message(self):
        """Dry-run must return the install_message in the preview so the orchestrator can show it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo_with_files(tmpdir)
            result = squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001-my-feature): implement widget catalog",
                source_message="",
                confirm=False,
                default_branch="main",
            )
            repo_out = result["install_repo"]
            self.assertIsNotNone(repo_out)
            # The message_used in the preview should include the install_message.
            self.assertIn(
                "feat(001-my-feature): implement widget catalog",
                repo_out.get("message_used", ""),
            )

    def test_dry_run_returns_squash_base(self):
        """Dry-run must return the resolved squash_base so the orchestrator can confirm."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_feature_branch_repo_with_files(tmpdir)
            result = squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001-my-feature): widget",
                source_message="",
                confirm=False,
                default_branch="main",
            )
            repo_out = result["install_repo"]
            self.assertEqual(repo_out.get("squash_base"), info["base_sha"])


# ---------------------------------------------------------------------------
# TestSquashAlreadyPushedRefusal
# ---------------------------------------------------------------------------


def _make_remote_feature_branch_repo(tmpdir):
    # type: (str,) -> dict
    """Create a bare remote and a clone with a FEATURE BRANCH whose [WIP] commit
    has been pushed to origin so that origin/spec/001-feat exists.

    This is the already-pushed scenario: all feature-branch commits are on the
    remote, so check_pushed will see is_pushed=True and the squash verb must refuse.

    Layout:
      tmpdir/remote.git  — bare repo
      tmpdir/clone       — working clone, on feature branch, commits pushed

    Returns:
        {
            "clone_dir":   str  — path to the working clone (on the feature branch),
            "default_branch": "main",
        }
    """
    remote_path = os.path.join(tmpdir, "remote.git")
    clone_path  = os.path.join(tmpdir, "clone")
    os.makedirs(remote_path, exist_ok=True)
    os.makedirs(clone_path, exist_ok=True)

    # Init bare remote.
    _git(["init", "--bare", "-b", "main", "."], cwd=remote_path)

    # Init clone with a base commit on main, push to remote.
    _init_repo(clone_path)
    _write_file(clone_path, "base.txt", "base\n")
    _commit(clone_path, "initial: base")
    _git(["remote", "add", "origin", remote_path], cwd=clone_path)
    _git(["push", "-u", "origin", "main"], cwd=clone_path)

    # Create a feature branch with a [WIP] commit, PUSH it to origin.
    _git(["checkout", "-b", "spec/001-feat"], cwd=clone_path)
    _write_file(clone_path, "feat.py", "# feat\n")
    _commit(clone_path, "[WIP] add feat")
    _git(["push", "-u", "origin", "spec/001-feat"], cwd=clone_path)

    return {"clone_dir": clone_path, "default_branch": "main"}


class TestSquashAlreadyPushedRefusal(unittest.TestCase):
    """squash must refuse when the feature branch is already pushed to origin."""

    def test_pushed_branch_refused(self):
        """Commits already on origin → refused=True, HEAD unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_remote_feature_branch_repo(tmpdir)
            clone_dir = info["clone_dir"]

            head_before = _head_sha(clone_dir)
            result = squash(
                install_root=clone_dir,
                source_root=clone_dir,
                install_message="feat(001-feat): widget",
                source_message="",
                confirm=True,
                default_branch="main",
            )
            head_after = _head_sha(clone_dir)

            # HEAD must NOT have changed.
            self.assertEqual(head_before, head_after,
                             msg="HEAD must not change when commits are already pushed")

            repo_out = result["install_repo"]
            self.assertTrue(repo_out["refused"],
                            msg="refused must be True when commits are already pushed")
            self.assertIsNone(repo_out["head_sha"],
                              msg="head_sha must be None when refused")

    def test_no_danger_state_on_pushed_refusal(self):
        """An already-pushed refusal is clean — no danger_state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_remote_feature_branch_repo(tmpdir)
            clone_dir = info["clone_dir"]

            result = squash(
                install_root=clone_dir,
                source_root=clone_dir,
                install_message="feat(001-feat): widget",
                source_message="",
                confirm=True,
                default_branch="main",
            )
            repo_out = result["install_repo"]
            self.assertFalse(repo_out.get("danger_state", False))


# ---------------------------------------------------------------------------
# TestSquashIdempotentNoOp
# ---------------------------------------------------------------------------


class TestSquashIdempotentNoOp(unittest.TestCase):
    """squash no-ops cleanly when there is nothing to squash."""

    def test_no_wip_commits_on_feature_branch_with_no_base_divergence(self):
        """Feature branch with NO [WIP]/[checkpoint] commits: resolve_squash_base
        returns a valid base but the repo has only regular commits — squash produces
        ONE clean commit from whatever commits exist between base and HEAD.

        The true idempotent no-op case is when strategy='none' (no base found at all)
        — that is the on-DEFAULT_BRANCH path with no [checkpoint] commits.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "base.txt", "base\n")
            _commit(tmpdir, "initial: base")
            # Stay on main; add a plain commit with no [WIP]/[checkpoint] prefix.
            _write_file(tmpdir, "plain.py", "# plain\n")
            _commit(tmpdir, "plain commit — no checkpoint or WIP")

            # On main with no [checkpoint] commits → strategy='none'.
            result = squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001): widget",
                source_message="",
                confirm=True,
                default_branch="main",
            )
            repo_out = result["install_repo"]
            self.assertIsNone(result.get("error"), msg=result)
            # No mutation — the refusal reason should describe "nothing to squash".
            self.assertIsNone(repo_out.get("head_sha"),
                              msg="head_sha should be None on no-op path")
            self.assertFalse(repo_out.get("danger_state", False))


# ---------------------------------------------------------------------------
# TestSquashRootCommitCheckpointError
# ---------------------------------------------------------------------------


class TestSquashRootCommitCheckpointError(unittest.TestCase):
    """When resolve_squash_base returns an error (root-commit-checkpoint), no mutation."""

    def test_root_commit_checkpoint_surfaced_no_mutation(self):
        """Single-commit [checkpoint] repo → error surfaced, no mutation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "base.txt", "base\n")
            _commit(tmpdir, "[checkpoint] Pre-feat: initial")

            head_before = _head_sha(tmpdir)
            result = squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001): widget",
                source_message="",
                confirm=True,
                default_branch="main",
            )
            head_after = _head_sha(tmpdir)

            # HEAD must not change.
            self.assertEqual(head_before, head_after)

            # The top-level error must be set.
            self.assertIsNotNone(result.get("error"),
                                 msg="top-level error must be set for root-commit-checkpoint case")
            # No install_repo/source_repo outcomes (error path exits early).
            self.assertIsNone(result.get("install_repo"))


# ---------------------------------------------------------------------------
# TestSquashWrapperMode
# ---------------------------------------------------------------------------


class TestSquashWrapperMode(unittest.TestCase):
    """squash in wrapper mode: install repo gets attribution; source repo NEVER does."""

    def _make_wrapper_with_wip(self, tmpdir, attribution_value=None):
        # type: (str, Optional[str]) -> dict
        """Create install_root + source_root, both with [WIP] commits on feature branches."""
        install_root = os.path.join(tmpdir, "wrapper")
        source_root  = os.path.join(tmpdir, "wrapper", "myproject")
        os.makedirs(install_root, exist_ok=True)
        os.makedirs(source_root, exist_ok=True)

        # Install repo: base + feature branch + WIP commit.
        _init_repo(install_root)
        _write_file(install_root, "install-base.txt", "install\n")
        install_base = _commit(install_root, "initial: install base")
        _git(["checkout", "-b", "spec/001-feat"], cwd=install_root)
        _write_file(install_root, "spec.md", "# spec\n")
        _commit(install_root, "[WIP] install wip")

        # Attribution config in install root.
        if attribution_value is not None:
            _write_project_config(install_root, attribution_value=attribution_value)

        # Source repo: base + feature branch + WIP commit.
        _init_repo(source_root)
        _write_file(source_root, "main.py", "# main\n")
        src_base = _commit(source_root, "initial: source base")
        _git(["checkout", "-b", "spec/001-feat"], cwd=source_root)
        _write_file(source_root, "feat.py", "# feat\n")
        _commit(source_root, "[WIP] source wip")

        return {
            "install_root": install_root,
            "source_root":  source_root,
            "install_base": install_base,
            "src_base":     src_base,
        }

    def test_install_repo_has_one_commit_after_squash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            info = self._make_wrapper_with_wip(tmpdir)
            squash(
                install_root=info["install_root"],
                source_root=info["source_root"],
                install_message="feat(001-feat): widget catalog",
                source_message="[PROJ-123] - Implement widget catalog",
                confirm=True,
                default_branch="main",
            )
            self.assertEqual(
                _commit_count(info["install_root"], info["install_base"]),
                1,
                msg="Install repo must have exactly 1 commit since base after squash",
            )

    def test_source_repo_has_one_commit_after_squash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            info = self._make_wrapper_with_wip(tmpdir)
            squash(
                install_root=info["install_root"],
                source_root=info["source_root"],
                install_message="feat(001-feat): widget catalog",
                source_message="[PROJ-123] - Implement widget catalog",
                confirm=True,
                default_branch="main",
            )
            self.assertEqual(
                _commit_count(info["source_root"], info["src_base"]),
                1,
                msg="Source repo must have exactly 1 commit since base after squash",
            )

    def test_install_message_used_in_install_repo(self):
        """Install repo commit message must match install_message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = self._make_wrapper_with_wip(tmpdir)
            squash(
                install_root=info["install_root"],
                source_root=info["source_root"],
                install_message="feat(001-feat): widget catalog",
                source_message="[PROJ-123] - Implement widget catalog",
                confirm=True,
                default_branch="main",
            )
            msg = _commit_message(info["install_root"])
            self.assertIn("feat(001-feat): widget catalog", msg)

    def test_source_message_used_in_source_repo(self):
        """Source repo commit message must match source_message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = self._make_wrapper_with_wip(tmpdir)
            squash(
                install_root=info["install_root"],
                source_root=info["source_root"],
                install_message="feat(001-feat): widget catalog",
                source_message="[PROJ-123] - Implement widget catalog",
                confirm=True,
                default_branch="main",
            )
            msg = _commit_message(info["source_root"])
            self.assertIn("[PROJ-123] - Implement widget catalog", msg)

    def test_source_repo_never_has_attribution_with_attribution_config(self):
        """D5: source repo NEVER gets Co-Authored-By, even when COMMIT_ATTRIBUTION is set."""
        attribution = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        with tempfile.TemporaryDirectory() as tmpdir:
            info = self._make_wrapper_with_wip(tmpdir, attribution_value=attribution)
            squash(
                install_root=info["install_root"],
                source_root=info["source_root"],
                install_message="feat(001-feat): widget catalog",
                source_message="[PROJ-123] - Implement widget catalog",
                confirm=True,
                default_branch="main",
            )
            src_msg = _commit_message(info["source_root"])
            self.assertNotIn(
                "Co-Authored-By", src_msg,
                msg="Source repo commit must NEVER contain Co-Authored-By (D5 hard invariant)",
            )

    def test_install_repo_has_attribution_when_config_set(self):
        """Install repo commit gets attribution trailer when COMMIT_ATTRIBUTION is set."""
        attribution = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        with tempfile.TemporaryDirectory() as tmpdir:
            info = self._make_wrapper_with_wip(tmpdir, attribution_value=attribution)
            squash(
                install_root=info["install_root"],
                source_root=info["source_root"],
                install_message="feat(001-feat): widget catalog",
                source_message="[PROJ-123] - Implement widget catalog",
                confirm=True,
                default_branch="main",
            )
            install_msg = _commit_message(info["install_root"])
            self.assertIn(
                "Co-Authored-By", install_msg,
                msg="Install repo commit must have Co-Authored-By when COMMIT_ATTRIBUTION is set",
            )

    def test_attribution_applied_flag_false_for_source_repo(self):
        """attribution_applied must be False for the source repo regardless of config."""
        attribution = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        with tempfile.TemporaryDirectory() as tmpdir:
            info = self._make_wrapper_with_wip(tmpdir, attribution_value=attribution)
            result = squash(
                install_root=info["install_root"],
                source_root=info["source_root"],
                install_message="feat(001-feat): widget",
                source_message="[PROJ-123] - widget",
                confirm=True,
                default_branch="main",
            )
            self.assertFalse(
                result["source_repo"]["attribution_applied"],
                msg="attribution_applied must always be False for the source repo",
            )


# ---------------------------------------------------------------------------
# TestSquashCmdCLI — CLI handler tests
# ---------------------------------------------------------------------------


class TestCmdSquashCLI(unittest.TestCase):
    """CLI handler cmd_squash."""

    def _make_args(
        self,
        install_root=".",
        source_root=None,
        install_message="feat(001): widget",
        source_message="[PROJ-1] - widget",
        confirm=False,
        default_branch=None,
    ):
        class _Args:
            pass
        args = _Args()
        args.install_root = install_root
        args.source_root = source_root or install_root
        args.install_message = install_message
        args.source_message = source_message
        args.confirm = confirm
        args.default_branch = default_branch
        return args

    def test_dry_run_exits_0_emits_json(self):
        """Without --confirm: exits 0, emits JSON with confirmed=false."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo_with_files(tmpdir)
            args = self._make_args(
                install_root=tmpdir,
                confirm=False,
                default_branch="main",
            )
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = cmd_squash(args)
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0)
            data = json.loads(captured.getvalue())
            self.assertFalse(data["confirmed"])
            # install_repo should be populated with a preview.
            self.assertIsNotNone(data.get("install_repo"))

    def test_confirm_exits_0_on_success(self):
        """With --confirm on a clean feature branch: exits 0, JSON has head_sha."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo_with_files(tmpdir)
            args = self._make_args(
                install_root=tmpdir,
                confirm=True,
                default_branch="main",
            )
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = cmd_squash(args)
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0)
            data = json.loads(captured.getvalue())
            self.assertTrue(data["confirmed"])
            self.assertIsNotNone(data["install_repo"]["head_sha"])

    def test_pushed_branch_exits_2(self):
        """With --confirm but commits already pushed (feature branch on remote): exits 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_remote_feature_branch_repo(tmpdir)
            clone_dir = info["clone_dir"]

            args = self._make_args(
                install_root=clone_dir,
                confirm=True,
                default_branch="main",
            )
            captured_out = io.StringIO()
            captured_err = io.StringIO()
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = captured_out, captured_err
            try:
                rc = cmd_squash(args)
            finally:
                sys.stdout, sys.stderr = old_out, old_err
            self.assertEqual(rc, 2)


# ---------------------------------------------------------------------------
# TestSquashStaticPresence — Phase 3 positive check (mutation verbs EXIST now)
# ---------------------------------------------------------------------------


class TestSquashStaticPresence(unittest.TestCase):
    """Phase 3 shipped: _squash.py MUST now contain git mutation calls.

    These tests are the INVERSE of the Phase-2 gate (which asserted absence).
    Phase 3's DoD includes the presence of the mutation verbs.
    """

    def _read_squash_source(self):
        # type: () -> str
        squash_path = _LIB_DIR / "_finalize" / "_squash.py"
        return squash_path.read_text(encoding="utf-8")

    def test_reset_soft_present(self):
        """Phase 3 must have '--soft' as a code argument token in _squash.py."""
        src = self._read_squash_source()
        self.assertIn(
            '"--soft"', src,
            msg="Phase 3: '\"--soft\"' must appear as a code token — the squash verb is now shipped",
        )

    def test_git_commit_present(self):
        """Phase 3 must have 'commit' as a git subcommand token in _squash.py."""
        import ast
        src = self._read_squash_source()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            self.fail("_squash.py has a syntax error")

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
        self.assertTrue(
            finder.found,
            msg="Phase 3: git 'commit' as a subprocess argument must appear in _squash.py",
        )

    def test_squash_function_importable(self):
        """The squash() function must be importable from _finalize._squash."""
        self.assertTrue(callable(squash))

    def test_cmd_squash_importable(self):
        """The cmd_squash() CLI handler must be importable from _finalize._squash."""
        self.assertTrue(callable(cmd_squash))


# ---------------------------------------------------------------------------
# TestSquashFinding1WrapperInstallNone — Finding 1
# Install repo on DEFAULT_BRANCH with no checkpoints (strategy="none") while
# the source repo has unpushed WIP commits on a feature branch.
# ---------------------------------------------------------------------------


class TestSquashFinding1WrapperInstallNone(unittest.TestCase):
    """Finding 1: install strategy='none' must NOT silently skip a source repo with WIP.

    Scenario:
      - install repo: on DEFAULT_BRANCH (main), no checkpoint commits → install_base=None
      - source repo:  on a feature branch with one unpushed [WIP] commit → source_base set

    Expected:
      - squash(confirm=True) squashes the SOURCE repo (head_sha changes, 1 commit since base)
      - install repo is a clean no-op (head_sha=None, refusal_reason contains "nothing to squash")
      - No top-level error
    """

    def _make_install_on_default_no_checkpoints_source_with_wip(self, tmpdir):
        # type: (str,) -> dict
        """Install repo on main with plain commits (no checkpoints), source repo on feature branch."""
        install_root = os.path.join(tmpdir, "wrapper")
        source_root  = os.path.join(tmpdir, "wrapper", "myapp")
        os.makedirs(install_root, exist_ok=True)
        os.makedirs(source_root, exist_ok=True)

        # Install repo: stays on 'main', no checkpoint commits at all.
        _init_repo(install_root)
        _write_file(install_root, "README.md", "# wrapper\n")
        _commit(install_root, "initial: wrapper setup")
        _write_file(install_root, "config.json", "{}\n")
        _commit(install_root, "add config (plain commit, no checkpoint or WIP)")
        # install HEAD is on main — _resolve_default_branch will find 'main'.
        # _oldest_checkpoint_parent will find nothing → install_base = None, strategy = "none".
        install_head_before = _head_sha(install_root)

        # Source repo: feature branch with one unpushed [WIP] commit.
        _init_repo(source_root)
        _write_file(source_root, "main.py", "# main\n")
        src_base = _commit(source_root, "initial: source base")
        _git(["checkout", "-b", "spec/001-widget"], cwd=source_root)
        _write_file(source_root, "widget.py", "# widget\n")
        _commit(source_root, "[WIP] implement widget")
        # source_root has no remote → check_pushed returns no_upstream=True → safe to squash.

        return {
            "install_root":       install_root,
            "source_root":        source_root,
            "src_base":           src_base,
            "install_head_before": install_head_before,
        }

    def test_source_repo_squashed_when_install_is_noop(self):
        """Source repo gets squashed; install repo is a clean no-op."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = self._make_install_on_default_no_checkpoints_source_with_wip(tmpdir)

            result = squash(
                install_root=info["install_root"],
                source_root=info["source_root"],
                install_message="feat(001-widget): implement widget catalog",
                source_message="[PROJ-1] - Implement widget catalog",
                confirm=True,
                default_branch="main",
            )

            # No top-level error.
            self.assertIsNone(result.get("error"), msg=result)

            # Install repo: clean no-op — head_sha=None, not refused, refusal_reason set.
            install_out = result["install_repo"]
            self.assertIsNotNone(install_out)
            self.assertIsNone(install_out["head_sha"],
                              msg="Install repo should be no-op (head_sha=None)")
            self.assertFalse(install_out.get("refused"),
                             msg="Install no-op is not a 'refused' — it is a clean nothing-to-do")
            self.assertIn("nothing to squash", install_out.get("refusal_reason", "").lower(),
                          msg="Install refusal_reason must say 'nothing to squash'")
            self.assertFalse(install_out.get("danger_state", False))

            # Install repo HEAD must be unchanged.
            self.assertEqual(_head_sha(info["install_root"]), info["install_head_before"],
                             msg="Install repo HEAD must not change when it has nothing to squash")

            # Source repo: squashed — exactly ONE commit since src_base, head_sha != None.
            source_out = result["source_repo"]
            self.assertIsNotNone(source_out)
            self.assertIsNotNone(source_out["head_sha"],
                                 msg="Source repo must have a new head_sha after squash")
            self.assertFalse(source_out.get("refused"),
                             msg="Source repo should not be refused — it has WIP to squash")
            self.assertFalse(source_out.get("danger_state", False))
            self.assertEqual(
                _commit_count(info["source_root"], info["src_base"]),
                1,
                msg="Source repo must have exactly 1 commit since its base after squash",
            )

    def test_confirm_gate_still_blocks_all_mutation_when_absent(self):
        """Without --confirm, neither install nor source repo is mutated (dry-run)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = self._make_install_on_default_no_checkpoints_source_with_wip(tmpdir)
            src_head_before = _head_sha(info["source_root"])

            result = squash(
                install_root=info["install_root"],
                source_root=info["source_root"],
                install_message="feat(001-widget): widget",
                source_message="[PROJ-1] - widget",
                confirm=False,  # no --confirm → dry-run
                default_branch="main",
            )

            # confirmed=False, no mutation in either repo.
            self.assertFalse(result["confirmed"])
            self.assertEqual(_head_sha(info["install_root"]), info["install_head_before"],
                             msg="Install repo HEAD must not change in dry-run")
            self.assertEqual(_head_sha(info["source_root"]), src_head_before,
                             msg="Source repo HEAD must not change in dry-run")

    def test_d5_source_no_traces_invariant(self):
        """D5: even in this mixed scenario, source repo commit has no attribution."""
        attribution = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        with tempfile.TemporaryDirectory() as tmpdir:
            info = self._make_install_on_default_no_checkpoints_source_with_wip(tmpdir)
            _write_project_config(info["install_root"], attribution_value=attribution)

            squash(
                install_root=info["install_root"],
                source_root=info["source_root"],
                install_message="feat(001-widget): widget",
                source_message="[PROJ-1] - widget",
                confirm=True,
                default_branch="main",
            )

            src_msg = _commit_message(info["source_root"])
            self.assertNotIn(
                "Co-Authored-By", src_msg,
                msg="Source repo must NEVER have Co-Authored-By (D5 invariant)",
            )

    def test_standalone_path_behaviorally_unchanged(self):
        """Standalone path (source_root == install_root) must behave identically to before.

        When install repo is on main with no checkpoints AND source_root == install_root,
        both the old and new code produce a no-op. Confirm the refactored code still does.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            _write_file(tmpdir, "a.txt", "a\n")
            _commit(tmpdir, "initial: base")
            _write_file(tmpdir, "b.txt", "b\n")
            _commit(tmpdir, "plain commit — no checkpoint")
            head_before = _head_sha(tmpdir)

            result = squash(
                install_root=tmpdir,
                source_root=tmpdir,  # standalone: same path
                install_message="feat(001): widget",
                source_message="",
                confirm=True,
                default_branch="main",
            )

            # No error, no mutation.
            self.assertIsNone(result.get("error"))
            self.assertEqual(_head_sha(tmpdir), head_before,
                             msg="Standalone no-op must not change HEAD")
            self.assertIsNone(result["install_repo"]["head_sha"])
            self.assertIsNone(result.get("source_repo"))  # standalone → no source_repo key


# ---------------------------------------------------------------------------
# TestSquashDangerState — Finding 2
# The DANGER STATE path (reset OK, commit fails) must have an asserting test.
# ---------------------------------------------------------------------------


class TestSquashDangerState(unittest.TestCase):
    """Finding 2: test the danger-state path with a commit-failing hook.

    A pre-commit hook that unconditionally exits 1 causes git commit to fail
    after git reset --soft has succeeded. The result must report danger_state=True,
    the error message must contain 'DANGER STATE', and cmd_squash must exit 2.
    """

    def _install_failing_pre_commit_hook(self, repo_root):
        # type: (str,) -> None
        """Install a pre-commit hook that always exits 1."""
        hooks_dir = os.path.join(repo_root, ".git", "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        hook_path = os.path.join(hooks_dir, "pre-commit")
        with open(hook_path, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nexit 1\n")
        os.chmod(hook_path, 0o755)

    def _verify_hook_actually_fails_commit(self, repo_root):
        # type: (str,) -> bool
        """Return True if git commit actually fails in this environment with the hook."""
        # Write a file to have something staged.
        probe_path = os.path.join(repo_root, "_hook_probe.txt")
        with open(probe_path, "w", encoding="utf-8") as fh:
            fh.write("probe\n")
        _git(["add", "_hook_probe.txt"], cwd=repo_root)
        rc, _out, _err = subprocess.run(
            ["git", "-C", repo_root, "commit", "-m", "probe commit"],
            capture_output=True, text=True, check=False
        ).returncode, "", ""
        # Undo the staged change regardless of outcome.
        subprocess.run(
            ["git", "-C", repo_root, "reset", "HEAD", "_hook_probe.txt"],
            capture_output=True, check=False,
        )
        try:
            os.remove(probe_path)
        except OSError:
            pass
        return rc != 0

    def test_danger_state_true_when_reset_ok_commit_fails(self):
        """reset --soft succeeds, then commit fails → danger_state=True in result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Build a feature-branch repo with WIP commits.
            _make_feature_branch_repo_with_files(tmpdir)

            # Install a failing pre-commit hook.
            self._install_failing_pre_commit_hook(tmpdir)

            # Verify the hook actually makes commit fail in this environment.
            # If pre-commit hooks are not honoured (e.g. core.hooksPath override),
            # skip so we don't produce a false-pass.
            if not self._verify_hook_actually_fails_commit(tmpdir):
                self.skipTest(
                    "pre-commit hook does not make git commit fail in this environment "
                    "(hooks may be bypassed or core.hooksPath is overridden) — skip"
                )

            result = squash(
                install_root=tmpdir,
                source_root=tmpdir,
                install_message="feat(001-my-feature): widget",
                source_message="",
                confirm=True,
                default_branch="main",
            )

            repo_out = result["install_repo"]
            self.assertIsNotNone(repo_out)
            self.assertTrue(
                repo_out.get("danger_state"),
                msg="danger_state must be True when reset --soft succeeded but commit failed",
            )
            self.assertIsNotNone(repo_out.get("error"))
            self.assertIn(
                "DANGER STATE",
                repo_out["error"],
                msg="error message must contain 'DANGER STATE'",
            )
            # head_sha must be None — commit did not produce a new commit.
            self.assertIsNone(repo_out["head_sha"])

    def test_cmd_squash_exits_2_on_danger_state(self):
        """cmd_squash must exit 2 when the result contains danger_state=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_feature_branch_repo_with_files(tmpdir)
            self._install_failing_pre_commit_hook(tmpdir)

            if not self._verify_hook_actually_fails_commit(tmpdir):
                self.skipTest(
                    "pre-commit hook does not make git commit fail in this environment — skip"
                )

            class _Args:
                pass
            args = _Args()
            args.install_root = tmpdir
            args.source_root = tmpdir
            args.install_message = "feat(001-my-feature): widget"
            args.source_message = ""
            args.confirm = True
            args.default_branch = "main"

            captured_out = io.StringIO()
            captured_err = io.StringIO()
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = captured_out, captured_err
            try:
                rc = cmd_squash(args)
            finally:
                sys.stdout, sys.stderr = old_out, old_err

            self.assertEqual(rc, 2,
                             msg="cmd_squash must exit 2 when danger_state is True")
            # stderr must contain "DANGER STATE".
            self.assertIn("DANGER STATE", captured_err.getvalue(),
                          msg="stderr must contain 'DANGER STATE' message")


# ---------------------------------------------------------------------------
# TestSquashPartialWrapperInstallOKSourcePushed — Finding 3
# install repo squashed, source repo refused-because-pushed.
# Locks the partial-squash JSON contract Phase 4 reads.
# ---------------------------------------------------------------------------


def _make_wrapper_install_wip_source_pushed(tmpdir):
    # type: (str,) -> dict
    """Create a wrapper fixture where:
      - Install repo: feature branch with one unpushed [WIP] commit → squash proceeds.
      - Source repo: feature branch whose commit IS already pushed to a bare remote
                     → check_pushed returns is_pushed=True → squash is refused.

    Layout:
      tmpdir/wrapper/          — install repo
      tmpdir/wrapper/src/      — source repo (working clone)
      tmpdir/src-remote.git/   — bare remote for source repo

    Returns dict with paths and SHAs for assertions.
    """
    install_root = os.path.join(tmpdir, "wrapper")
    source_clone = os.path.join(tmpdir, "wrapper", "src")
    src_remote   = os.path.join(tmpdir, "src-remote.git")

    os.makedirs(install_root, exist_ok=True)
    os.makedirs(source_clone, exist_ok=True)
    os.makedirs(src_remote, exist_ok=True)

    # --- Bare remote for source ---
    _git(["init", "--bare", "-b", "main", "."], cwd=src_remote)

    # --- Source repo: push a [WIP] commit to the remote ---
    _init_repo(source_clone)
    _write_file(source_clone, "main.py", "# main\n")
    src_base = _commit(source_clone, "initial: source base")
    _git(["remote", "add", "origin", src_remote], cwd=source_clone)
    _git(["push", "-u", "origin", "main"], cwd=source_clone)
    # Feature branch with a [WIP] commit — PUSHED to origin.
    _git(["checkout", "-b", "spec/001-widget"], cwd=source_clone)
    _write_file(source_clone, "widget.py", "# widget\n")
    _commit(source_clone, "[WIP] implement widget")
    _git(["push", "-u", "origin", "spec/001-widget"], cwd=source_clone)
    # Now origin/spec/001-widget exists and is in sync → check_pushed sees is_pushed=True.
    src_head_before = _head_sha(source_clone)

    # --- Install repo: feature branch with one local-only [WIP] commit ---
    _init_repo(install_root)
    _write_file(install_root, "README.md", "# wrapper\n")
    install_base = _commit(install_root, "initial: install base")
    _git(["checkout", "-b", "spec/001-widget"], cwd=install_root)
    _write_file(install_root, "spec.md", "# spec\n")
    _commit(install_root, "[WIP] install wip")
    # No remote for install → check_pushed returns no_upstream=True → safe to squash.

    return {
        "install_root":   install_root,
        "source_root":    source_clone,
        "install_base":   install_base,
        "src_head_before": src_head_before,
    }


class TestSquashPartialWrapperInstallOKSourcePushed(unittest.TestCase):
    """Finding 3: partial wrapper squash — install squashed, source refused (pushed).

    This locks the JSON contract that Phase 4 reads when the install repo
    is squashed but the source repo is refused because its branch is already pushed.
    """

    def test_install_squashed_source_refused_contract(self):
        """install squashed (head_sha set), source refused (head_sha=None, refused=True)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_wrapper_install_wip_source_pushed(tmpdir)

            result = squash(
                install_root=info["install_root"],
                source_root=info["source_root"],
                install_message="feat(001-widget): implement widget catalog",
                source_message="[PROJ-1] - Implement widget catalog",
                confirm=True,
                default_branch="main",
            )

            # No top-level error.
            self.assertIsNone(result.get("error"), msg=result)

            # Install repo: squashed successfully.
            install_out = result["install_repo"]
            self.assertIsNotNone(install_out)
            self.assertIsNotNone(
                install_out["head_sha"],
                msg="install_repo.head_sha must be set — install was squashed",
            )
            self.assertFalse(install_out.get("refused"),
                             msg="install_repo.refused must be False — install squash succeeded")
            self.assertFalse(install_out.get("danger_state", False))

            # Source repo: refused because its branch is already pushed.
            source_out = result["source_repo"]
            self.assertIsNotNone(source_out)
            self.assertTrue(
                source_out["refused"],
                msg="source_repo.refused must be True — its branch is already pushed",
            )
            self.assertIsNone(
                source_out["head_sha"],
                msg="source_repo.head_sha must be None when refused",
            )
            # Source HEAD must be unchanged — no history mutation.
            self.assertEqual(
                _head_sha(info["source_root"]),
                info["src_head_before"],
                msg="Source repo HEAD must not change when refused",
            )
            # No danger state on a clean refusal.
            self.assertFalse(source_out.get("danger_state", False))

    def test_cmd_squash_exits_2_on_partial_squash(self):
        """cmd_squash exits 2 when source is refused (partial squash = not complete)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = _make_wrapper_install_wip_source_pushed(tmpdir)

            class _Args:
                pass
            args = _Args()
            args.install_root = info["install_root"]
            args.source_root  = info["source_root"]
            args.install_message = "feat(001-widget): widget"
            args.source_message  = "[PROJ-1] - widget"
            args.confirm = True
            args.default_branch = "main"

            captured_out = io.StringIO()
            captured_err = io.StringIO()
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = captured_out, captured_err
            try:
                rc = cmd_squash(args)
            finally:
                sys.stdout, sys.stderr = old_out, old_err

            self.assertEqual(
                rc, 2,
                msg="cmd_squash must exit 2 when a source repo refusal leaves squash incomplete",
            )
            # The JSON must still be emitted to stdout.
            data = json.loads(captured_out.getvalue())
            self.assertTrue(data["confirmed"])
            self.assertIsNotNone(data["install_repo"]["head_sha"])
            self.assertTrue(data["source_repo"]["refused"])


if __name__ == "__main__":
    unittest.main()
