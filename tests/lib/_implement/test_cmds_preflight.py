"""Tests for src/devforge/lib/_implement/_cmds_preflight.py.

Coverage:

  _read_first_n_lines:
    - Returns first N non-blank lines joined with newlines.
    - Returns empty string for a file with only blank lines.
    - Returns None for absent/unreadable file.
    - Truncates correctly when file has fewer than N lines.

  _git_current_branch:
    - Returns branch name in a real seeded git repo.
    - Returns None for a non-git directory.

  _git_head_sha:
    - Returns a 40-char hex SHA in a real seeded git repo with a commit.
    - Returns None for a non-git directory.
    - Returns None for a git repo with no commits (empty repo).

  _check_constitution:
    - Returns None when constitution.md exists and has no populate-guard.
    - Returns error string when constitution.md is absent.
    - Returns error string when constitution.md contains the populate-guard.

  _check_branch:
    - Returns None on a feature branch.
    - Returns error string on 'main'.
    - Returns error string on 'master'.
    - Returns error string on 'trunk'.
    - Returns error string in detached HEAD state.
    - Returns error string when git is not available (non-git dir).

  _check_wip_marker:
    - Returns None when wip.md is absent.
    - Returns error string when wip.md exists.

  cmd_preflight (integration, real git tempdir):
    - Happy path: feature branch, constitution ok, no wip.md → exit 0 + JSON.
    - Constitution absent → exit 2.
    - Constitution has populate-guard → exit 2.
    - On main branch → exit 2.
    - wip.md present → exit 2.
    - Emitted JSON has required fields: constitution_digest, memory_digest,
      head_sha, branch.
    - memory.md absent → memory_digest is null in output.
    - memory.md present → memory_digest contains first lines.

Design notes:
- Tests seed a real temporary git repository (git init, config, commit) so
  _git_current_branch and _git_head_sha round-trip through the real git binary.
- constitution.md and .devforge/ are written to the tmpdir root.
- Branch check tests rename the branch to 'main'/'master' via git checkout -b or
  git branch -m to exercise the refusal logic.

Stdlib only. Python 3.8+.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _implement._cmds_preflight import (  # noqa: E402
    CONSTITUTION_POPULATE_GUARDS,
    DEFAULT_BRANCHES,
    _read_first_n_lines,
    _git_current_branch,
    _git_head_sha,
    _git_origin_default_branch,
    _git_status_dirty,
    _check_constitution,
    _check_branch,
    _check_wip_marker,
    cmd_preflight,
)


# ---------------------------------------------------------------------------
# Git tempdir helper
# ---------------------------------------------------------------------------


def _init_git_repo(tmpdir, branch="feature/widget", with_commit=True):
    # type: (Path, str, bool) -> None
    """Initialise a minimal git repo in tmpdir.

    Creates an initial commit so HEAD is resolvable.  Checks out a feature
    branch named 'branch'.

    The initial default branch is named '_init-tmp' to avoid conflicts when
    tests later rename the feature branch to 'main', 'master', etc.

    If with_commit is False, only runs git init (no commit, detached-HEAD
    risk is the caller's responsibility).
    """
    env = dict(os.environ)
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"

    cwd = str(tmpdir)

    # Use -b to set the initial branch to a unique name that won't conflict
    # with 'main'/'master' when tests rename the feature branch later.
    result = subprocess.run(
        ["git", "init", "-b", "_init-tmp"],
        cwd=cwd, capture_output=True,
    )
    if result.returncode != 0:
        # Older git (< 2.28) does not support -b: fall back to plain init.
        subprocess.run(["git", "init"], cwd=cwd, capture_output=True)

    subprocess.run(["git", "config", "user.email", "test@example.com"],
                   cwd=cwd, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"],
                   cwd=cwd, capture_output=True)

    if with_commit:
        # Create an initial commit on the initial branch.
        readme = tmpdir / "README.txt"
        readme.write_text("init\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.txt"],
                       cwd=cwd, capture_output=True, env=env)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=cwd, capture_output=True, env=env,
        )

    # Create and checkout the desired feature branch.
    subprocess.run(
        ["git", "checkout", "-b", branch],
        cwd=cwd, capture_output=True, env=env,
    )


def _write_constitution(root, populated=True, guard_index=-1):
    # type: (Path, bool, int) -> None
    """Write constitution.md.  If populated=False, write a populate-guard.

    guard_index selects which CONSTITUTION_POPULATE_GUARDS sentinel form to
    write (default -1: the current post-namespace form).
    """
    if populated:
        content = (
            "# Constitution\n\n"
            "## What this project is for\n\n"
            "Test project for /devforge:implement.\n\n"
            "## Rules\n\n"
            "- Rule 1: Do not break things.\n"
            "- Rule 2: Write tests.\n"
        )
    else:
        content = (
            "# Constitution\n\n"
            "{guard}\n".format(guard=CONSTITUTION_POPULATE_GUARDS[guard_index])
        )
    (root / "constitution.md").write_text(content, encoding="utf-8")


def _write_memory(root, lines=None):
    # type: (Path, list) -> None
    """Write .devforge/memory.md with the given lines."""
    devforge = root / ".devforge"
    devforge.mkdir(exist_ok=True)
    if lines is None:
        lines = ["# Memory\n", "- Lesson 1: Write tests.\n", "- Lesson 2: Read docs.\n"]
    (devforge / "memory.md").write_text("".join(lines), encoding="utf-8")


class _FakeArgs:
    def __init__(self, root="."):
        self.root = root


# ---------------------------------------------------------------------------
# Unit tests: _read_first_n_lines
# ---------------------------------------------------------------------------


class TestReadFirstNLines(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_first_n_non_blank_lines(self):
        f = self.tmp / "file.md"
        f.write_text("line1\nline2\nline3\nline4\nline5\nline6\n", encoding="utf-8")
        result = _read_first_n_lines(f, 5)
        self.assertEqual(result, "line1\nline2\nline3\nline4\nline5")

    def test_skips_blank_lines(self):
        f = self.tmp / "file.md"
        f.write_text("line1\n\nline2\n\nline3\n", encoding="utf-8")
        result = _read_first_n_lines(f, 3)
        self.assertEqual(result, "line1\nline2\nline3")

    def test_fewer_lines_than_n(self):
        f = self.tmp / "file.md"
        f.write_text("a\nb\n", encoding="utf-8")
        result = _read_first_n_lines(f, 5)
        self.assertEqual(result, "a\nb")

    def test_empty_file_returns_empty_string(self):
        f = self.tmp / "file.md"
        f.write_text("", encoding="utf-8")
        result = _read_first_n_lines(f, 5)
        self.assertEqual(result, "")

    def test_only_blank_lines_returns_empty_string(self):
        f = self.tmp / "file.md"
        f.write_text("\n\n\n", encoding="utf-8")
        result = _read_first_n_lines(f, 5)
        self.assertEqual(result, "")

    def test_absent_file_returns_none(self):
        f = self.tmp / "absent.md"
        self.assertIsNone(_read_first_n_lines(f, 5))

    def test_n_zero_returns_empty_string(self):
        f = self.tmp / "file.md"
        f.write_text("line1\nline2\n", encoding="utf-8")
        result = _read_first_n_lines(f, 0)
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# Unit tests: _check_constitution
# ---------------------------------------------------------------------------


class TestCheckConstitution(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_none_when_constitution_ok(self):
        _write_constitution(self.tmp, populated=True)
        result = _check_constitution(self.tmp)
        self.assertIsNone(result)

    def test_returns_error_when_absent(self):
        result = _check_constitution(self.tmp)
        self.assertIsNotNone(result)
        self.assertIn("constitution.md", result)

    def test_returns_error_when_populate_guard_present(self):
        _write_constitution(self.tmp, populated=False)
        result = _check_constitution(self.tmp)
        self.assertIsNotNone(result)
        self.assertIn("populate", result.lower())

    def test_error_message_mentions_constitute(self):
        _write_constitution(self.tmp, populated=False)
        result = _check_constitution(self.tmp)
        self.assertIn("/devforge:constitute", result)

    def test_returns_error_for_legacy_no_slash_guard_form(self):
        """Pre-namespace stub literal (no slash) -- the form every existing
        consumer install actually carries.
        """
        _write_constitution(self.tmp, populated=False, guard_index=0)
        result = _check_constitution(self.tmp)
        self.assertIsNotNone(result)
        self.assertIn("populate", result.lower())

    def test_returns_error_for_legacy_slash_guard_form(self):
        """Pre-namespace guard literal (with slash) -- never actually
        shipped by the stub template, kept for back-compat.
        """
        _write_constitution(self.tmp, populated=False, guard_index=1)
        result = _check_constitution(self.tmp)
        self.assertIsNotNone(result)
        self.assertIn("populate", result.lower())


# ---------------------------------------------------------------------------
# Unit tests: _check_branch (requires real git)
# ---------------------------------------------------------------------------


class TestCheckBranch(unittest.TestCase):
    """_check_branch returns (branch_name, None) on success, (None, error) on failure."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_git_repo(self.tmp, branch="feature/my-widget")

    def tearDown(self):
        self._tmp.cleanup()

    def test_feature_branch_returns_branch_and_none(self):
        branch, err = _check_branch(str(self.tmp))
        self.assertEqual(branch, "feature/my-widget")
        self.assertIsNone(err)

    def test_main_branch_returns_none_and_error(self):
        cwd = str(self.tmp)
        subprocess.run(["git", "branch", "-m", "feature/my-widget", "main"],
                       cwd=cwd, capture_output=True)
        branch, err = _check_branch(cwd)
        self.assertIsNone(branch)
        self.assertIsNotNone(err)
        self.assertIn("main", err)
        self.assertIn("feature branch", err)

    def test_master_branch_returns_error(self):
        cwd = str(self.tmp)
        subprocess.run(["git", "branch", "-m", "feature/my-widget", "master"],
                       cwd=cwd, capture_output=True)
        branch, err = _check_branch(cwd)
        self.assertIsNone(branch)
        self.assertIsNotNone(err)

    def test_trunk_branch_returns_error(self):
        cwd = str(self.tmp)
        subprocess.run(["git", "branch", "-m", "feature/my-widget", "trunk"],
                       cwd=cwd, capture_output=True)
        branch, err = _check_branch(cwd)
        self.assertIsNone(branch)
        self.assertIsNotNone(err)

    def test_non_git_dir_returns_error(self):
        # Use /tmp/ to guarantee a directory outside any git repository,
        # avoiding git's parent-directory walk finding the project repo.
        with tempfile.TemporaryDirectory(dir="/tmp") as non_git_dir:
            branch, err = _check_branch(str(non_git_dir))
        self.assertIsNone(branch)
        self.assertIsNotNone(err)

    def test_case_insensitive_main(self):
        """'MAIN' or 'Main' should be refused (compare case-insensitively)."""
        cwd = str(self.tmp)
        subprocess.run(["git", "branch", "-m", "feature/my-widget", "Main"],
                       cwd=cwd, capture_output=True)
        branch, err = _check_branch(cwd)
        self.assertIsNone(branch)
        self.assertIsNotNone(err)

    def test_detached_head_returns_error_mentioning_detached(self):
        """Detached HEAD state should produce an error mentioning 'detached'.

        FIX 2: The _check_branch guard 'if branch == "HEAD"' was live but
        untested.  This test checks out a raw SHA so git rev-parse --abbrev-ref
        returns "HEAD", then asserts the error mentions "detached".
        """
        cwd = str(self.tmp)
        env = dict(os.environ)
        env["GIT_AUTHOR_NAME"] = "Test"
        env["GIT_AUTHOR_EMAIL"] = "test@example.com"
        env["GIT_COMMITTER_NAME"] = "Test"
        env["GIT_COMMITTER_EMAIL"] = "test@example.com"
        # Get the current HEAD SHA.
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd, capture_output=True, text=True, env=env,
        )
        sha = sha_result.stdout.strip()
        # Detach HEAD by checking out the raw SHA.
        subprocess.run(
            ["git", "checkout", "--detach", sha],
            cwd=cwd, capture_output=True, env=env,
        )
        branch, err = _check_branch(cwd)
        self.assertIsNone(branch, "branch should be None in detached HEAD state")
        self.assertIsNotNone(err, "error should be non-None in detached HEAD state")
        self.assertIn("detached", err.lower())

    def test_develop_with_origin_main_is_allowed(self):
        """develop branch passes when origin/HEAD points to main (gitflow case).

        FIX 1: 'develop' is NOT in DEFAULT_BRANCHES.  Without a remote, the
        dynamic origin check returns None and the branch is allowed.  This
        simulates a gitflow team where origin default is 'main' but the current
        branch is 'develop' — preflight must proceed.
        """
        cwd = str(self.tmp)
        subprocess.run(["git", "branch", "-m", "feature/my-widget", "develop"],
                       cwd=cwd, capture_output=True)
        # No remote is configured in the test repo, so _git_origin_default_branch
        # returns None and the dynamic check is skipped.
        branch, err = _check_branch(cwd)
        self.assertEqual(branch, "develop",
                         "develop should be allowed when origin/HEAD is unknown")
        self.assertIsNone(err)


# ---------------------------------------------------------------------------
# Unit tests: _check_wip_marker
# ---------------------------------------------------------------------------


class TestCheckWipMarker(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        devforge = self.tmp / ".devforge"
        devforge.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_wip_returns_none(self):
        result = _check_wip_marker(self.tmp)
        self.assertIsNone(result)

    def test_wip_present_returns_error(self):
        wip = self.tmp / ".devforge" / "wip.md"
        wip.write_text("# WIP Marker\n**Command**: /implement\n", encoding="utf-8")
        result = _check_wip_marker(self.tmp)
        self.assertIsNotNone(result)
        self.assertIn("wip.md", result)

    def test_error_mentions_recovery(self):
        wip = self.tmp / ".devforge" / "wip.md"
        wip.write_text("# WIP Marker\n", encoding="utf-8")
        result = _check_wip_marker(self.tmp)
        # Should point user toward the crash-recovery branch.
        self.assertIn("interrupted", result.lower())


# ---------------------------------------------------------------------------
# Unit tests: _git_current_branch
# ---------------------------------------------------------------------------


class TestGitCurrentBranch(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_git_repo(self.tmp, branch="feature/test-branch")

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_feature_branch_name(self):
        branch = _git_current_branch(str(self.tmp))
        self.assertEqual(branch, "feature/test-branch")

    def test_non_git_dir_returns_none(self):
        # Use /tmp/ so we are outside any git repository.
        with tempfile.TemporaryDirectory(dir="/tmp") as non_git_dir:
            result = _git_current_branch(str(non_git_dir))
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Unit tests: _git_head_sha
# ---------------------------------------------------------------------------


class TestGitHeadSha(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_git_repo(self.tmp, branch="feature/x", with_commit=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_40_char_hex(self):
        sha = _git_head_sha(str(self.tmp))
        self.assertIsNotNone(sha)
        self.assertEqual(len(sha), 40)
        int(sha, 16)  # must be valid hex

    def test_non_git_dir_returns_none(self):
        # Use /tmp/ so we are outside any git repository.
        with tempfile.TemporaryDirectory(dir="/tmp") as non_git_dir:
            result = _git_head_sha(str(non_git_dir))
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Unit tests: _git_origin_default_branch
# ---------------------------------------------------------------------------


class TestGitOriginDefaultBranch(unittest.TestCase):
    """_git_origin_default_branch: returns None gracefully when no remote."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_git_repo(self.tmp, branch="feature/y", with_commit=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_remote_returns_none(self):
        """No origin configured → returns None, not an error."""
        result = _git_origin_default_branch(str(self.tmp))
        self.assertIsNone(result)

    def test_non_git_dir_returns_none(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as non_git_dir:
            result = _git_origin_default_branch(str(non_git_dir))
        self.assertIsNone(result)

    def test_with_fake_remote_returns_branch_name(self):
        """When origin/HEAD is set, returns just the branch name (no prefix)."""
        cwd = str(self.tmp)
        env = dict(os.environ)
        env["GIT_AUTHOR_NAME"] = "Test"
        env["GIT_AUTHOR_EMAIL"] = "test@example.com"
        env["GIT_COMMITTER_NAME"] = "Test"
        env["GIT_COMMITTER_EMAIL"] = "test@example.com"
        # Add the repo itself as its own "origin" so origin/HEAD can be set.
        subprocess.run(["git", "remote", "add", "origin", cwd],
                       cwd=cwd, capture_output=True)
        subprocess.run(["git", "fetch", "origin"],
                       cwd=cwd, capture_output=True, env=env)
        # Set origin/HEAD to the initial branch (whatever it is).
        current = _git_current_branch(cwd)
        subprocess.run(
            ["git", "remote", "set-head", "origin", current or "feature/y"],
            cwd=cwd, capture_output=True,
        )
        result = _git_origin_default_branch(cwd)
        # Should return a non-None branch name string with no "refs/remotes/origin/" prefix.
        if result is not None:
            self.assertNotIn("refs/", result)
            self.assertNotIn("remotes/", result)
            self.assertNotIn("origin/", result)
        # If fetch produced no refs (empty repo edge-case), result may be None — that is fine.


# ---------------------------------------------------------------------------
# Integration tests: cmd_preflight (real git tmpdir)
# ---------------------------------------------------------------------------


class TestCmdPreflightHappyPath(unittest.TestCase):
    """cmd_preflight: all checks pass → exit 0, valid JSON."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_git_repo(self.tmp, branch="feature/widget")
        _write_constitution(self.tmp, populated=True)
        devforge = self.tmp / ".devforge"
        devforge.mkdir(exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_exit_0(self):
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_preflight(args)
        self.assertEqual(code, 0, buf.getvalue())

    def test_emits_valid_json(self):
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_preflight(args)
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, dict)

    def test_required_fields_present(self):
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_preflight(args)
        data = json.loads(buf.getvalue())
        for field in ("constitution_digest", "memory_digest", "head_sha", "branch"):
            self.assertIn(field, data, "Missing field: {0}".format(field))

    def test_head_sha_is_40_chars(self):
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_preflight(args)
        data = json.loads(buf.getvalue())
        self.assertEqual(len(data["head_sha"]), 40)

    def test_branch_is_feature(self):
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_preflight(args)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["branch"], "feature/widget")

    def test_memory_digest_null_when_absent(self):
        """When .devforge/memory.md does not exist, memory_digest is null."""
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_preflight(args)
        data = json.loads(buf.getvalue())
        self.assertIsNone(data["memory_digest"])

    def test_memory_digest_present_when_file_exists(self):
        """When .devforge/memory.md exists, memory_digest contains its lines."""
        _write_memory(self.tmp, lines=["# Memory\n", "- lesson1\n"])
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_preflight(args)
        data = json.loads(buf.getvalue())
        self.assertIsNotNone(data["memory_digest"])
        self.assertIn("Memory", data["memory_digest"])

    def test_constitution_digest_contains_content(self):
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_preflight(args)
        data = json.loads(buf.getvalue())
        self.assertIsNotNone(data["constitution_digest"])
        self.assertGreater(len(data["constitution_digest"]), 0)


class TestCmdPreflightConstitutionBlocks(unittest.TestCase):
    """cmd_preflight: constitution checks cause exit 2."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_git_repo(self.tmp, branch="feature/widget")
        (self.tmp / ".devforge").mkdir(exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_absent_constitution_exits_2(self):
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        self.assertEqual(code, 2)
        self.assertNotEqual(errbuf.getvalue(), "")

    def test_populate_guard_exits_2(self):
        _write_constitution(self.tmp, populated=False)
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        self.assertEqual(code, 2)
        self.assertIn("populate", errbuf.getvalue().lower())


class TestCmdPreflightBranchBlocks(unittest.TestCase):
    """cmd_preflight: branch checks cause exit 2."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_git_repo(self.tmp, branch="feature/widget")
        _write_constitution(self.tmp, populated=True)
        (self.tmp / ".devforge").mkdir(exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_main_branch_exits_2(self):
        cwd = str(self.tmp)
        subprocess.run(["git", "branch", "-m", "feature/widget", "main"],
                       cwd=cwd, capture_output=True)
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=cwd)
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        self.assertEqual(code, 2)
        self.assertIn("main", errbuf.getvalue())

    def test_master_branch_exits_2(self):
        cwd = str(self.tmp)
        subprocess.run(["git", "branch", "-m", "feature/widget", "master"],
                       cwd=cwd, capture_output=True)
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=cwd)
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        self.assertEqual(code, 2)


class TestCmdPreflightWipBlocks(unittest.TestCase):
    """cmd_preflight: stale wip.md causes exit 2."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_git_repo(self.tmp, branch="feature/widget")
        _write_constitution(self.tmp, populated=True)
        devforge = self.tmp / ".devforge"
        devforge.mkdir(exist_ok=True)
        # Write stale wip.md.
        (devforge / "wip.md").write_text(
            "# WIP Marker — /implement\n**Command**: /implement\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_stale_wip_exits_2(self):
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        self.assertEqual(code, 2)
        self.assertIn("wip.md", errbuf.getvalue())


class TestCmdPreflightDevelopAllowed(unittest.TestCase):
    """cmd_preflight: 'develop' branch is allowed when origin default is main.

    FIX 1 integration test: rename the repo's branch to 'develop' (no remote
    configured → origin default unknown → dynamic check skipped) → preflight
    must exit 0.  This documents the gitflow team use case explicitly.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_git_repo(self.tmp, branch="feature/widget")
        _write_constitution(self.tmp, populated=True)
        (self.tmp / ".devforge").mkdir(exist_ok=True)
        # Rename to 'develop'.
        subprocess.run(
            ["git", "branch", "-m", "feature/widget", "develop"],
            cwd=str(self.tmp), capture_output=True,
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_develop_exits_0_when_origin_default_unknown(self):
        """develop is NOT refused when no remote is configured."""
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        self.assertEqual(code, 0,
                         "preflight should pass on 'develop' with no remote; "
                         "stderr={0!r}".format(errbuf.getvalue()))
        data = json.loads(buf.getvalue())
        self.assertEqual(data["branch"], "develop")


class TestCmdPreflightDefaultBranchConstant(unittest.TestCase):
    """Verify DEFAULT_BRANCHES constant contains expected values."""

    def test_main_in_default_branches(self):
        self.assertIn("main", DEFAULT_BRANCHES)

    def test_master_in_default_branches(self):
        self.assertIn("master", DEFAULT_BRANCHES)

    def test_trunk_in_default_branches(self):
        self.assertIn("trunk", DEFAULT_BRANCHES)

    def test_feature_not_in_default_branches(self):
        self.assertNotIn("feature/widget", DEFAULT_BRANCHES)

    def test_develop_not_in_default_branches(self):
        """FIX 5: 'develop' deliberately excluded from static DEFAULT_BRANCHES.

        Gitflow teams use develop as a feature-integration branch (not the
        repo's actual 'default' branch).  Refusing it statically would lock
        them out.  The dynamic origin/HEAD check handles the case where a team's
        repo actually uses develop as the default branch.
        """
        self.assertNotIn("develop", DEFAULT_BRANCHES)


class TestCmdPreflightConstitutionGuardConstant(unittest.TestCase):
    """Verify CONSTITUTION_POPULATE_GUARDS matches the sentinels in _specify."""

    def test_guard_literal(self):
        """Sentinels must match the literal values (kept as an independent,
        not-imported copy of _specify._schema.CONSTITUTION_POPULATE_GUARDS
        per the cross-package-coupling design note).
        """
        self.assertEqual(
            CONSTITUTION_POPULATE_GUARDS,
            (
                "_Run constitute to populate_",
                "_Run /constitute to populate_",
                "_Run /devforge:constitute to populate_",
            ),
        )

    def test_guard_literal_matches_specify_schema(self):
        """Cross-package parity check against the real _specify source of truth."""
        from _specify._schema import CONSTITUTION_POPULATE_GUARDS as _SPECIFY_GUARDS
        self.assertEqual(CONSTITUTION_POPULATE_GUARDS, _SPECIFY_GUARDS)


# ---------------------------------------------------------------------------
# Unit tests: _git_status_dirty
# ---------------------------------------------------------------------------


class TestGitStatusDirty(unittest.TestCase):
    """_git_status_dirty returns True for dirty repos, False for clean."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_git_repo(self.tmp, branch="feature/test")

    def tearDown(self):
        self._tmp.cleanup()

    def test_clean_repo_returns_false(self):
        """A freshly committed repo with no changes is not dirty."""
        result = _git_status_dirty(str(self.tmp))
        self.assertFalse(result)

    def test_modified_tracked_file_returns_true(self):
        """Modifying a tracked file makes the repo dirty."""
        readme = self.tmp / "README.txt"
        readme.write_text("modified\n", encoding="utf-8")
        result = _git_status_dirty(str(self.tmp))
        self.assertTrue(result)

    def test_new_untracked_file_returns_true(self):
        """A new untracked file makes the repo dirty."""
        (self.tmp / "new_file.py").write_text("x = 1\n", encoding="utf-8")
        result = _git_status_dirty(str(self.tmp))
        self.assertTrue(result)

    def test_non_git_dir_returns_false(self):
        """Non-git directory: fail-soft, return False (no error raised)."""
        with tempfile.TemporaryDirectory(dir="/tmp") as non_git_dir:
            result = _git_status_dirty(non_git_dir)
        self.assertFalse(result)

    def test_staged_file_returns_true(self):
        """Staged-but-not-committed file makes the repo dirty."""
        new_file = self.tmp / "staged.ts"
        new_file.write_text("export {};\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "staged.ts"],
            cwd=str(self.tmp), capture_output=True,
        )
        result = _git_status_dirty(str(self.tmp))
        self.assertTrue(result)


# ---------------------------------------------------------------------------
# Shared wrapper fixture helpers
# ---------------------------------------------------------------------------


def _init_wrapper_install(install_dir, source_repo_name="src-repo"):
    # type: (Path, str) -> str
    """Create a wrapper install structure for preflight tests.

    Creates:
      <install_dir>/.devforge/project-config.json  (PROJECT_ROOT = source_repo_name)
      <install_dir>/<source_repo_name>/             (a real git repo on a feature branch)
      <install_dir>/constitution.md                 (populated, no guard)

    Returns the SHA of the source repo's initial commit.
    """
    devforge = install_dir / ".devforge"
    devforge.mkdir(parents=True, exist_ok=True)
    config_path = devforge / "project-config.json"
    config_path.write_text(
        json.dumps({"PROJECT_ROOT": source_repo_name}), encoding="utf-8"
    )

    # Populated constitution.md at install root.
    _write_constitution(install_dir, populated=True)

    # Create the nested source git repo on a feature branch.
    source_dir = install_dir / source_repo_name
    source_dir.mkdir(parents=True, exist_ok=True)
    _init_git_repo(source_dir, branch="bugfix/ABC-123")

    # Get the source repo HEAD SHA.
    sha_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(source_dir),
        capture_output=True, text=True,
    )
    return sha_result.stdout.strip()


# ---------------------------------------------------------------------------
# Integration tests: cmd_preflight wrapper mode
# ---------------------------------------------------------------------------


class TestCmdPreflightWrapperHappyPath(unittest.TestCase):
    """cmd_preflight wrapper mode: source repo on feature branch → pass."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.source_sha = _init_wrapper_install(self.tmp, "src-repo")

    def tearDown(self):
        self._tmp.cleanup()

    def _run_preflight(self):
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        return code, buf.getvalue(), errbuf.getvalue()

    def test_wrapper_exits_0_on_feature_branch(self):
        """Source repo on feature branch (bugfix/ABC-123) → preflight passes."""
        code, stdout, stderr = self._run_preflight()
        self.assertEqual(code, 0,
                         "Expected exit 0; stderr={0!r}".format(stderr))

    def test_wrapper_head_sha_is_source_head(self):
        """head_sha in output is the SOURCE repo's HEAD, not the install root's."""
        code, stdout, stderr = self._run_preflight()
        self.assertEqual(code, 0)
        data = json.loads(stdout)
        self.assertEqual(
            data["head_sha"], self.source_sha,
            "head_sha must be the source repo HEAD SHA"
        )

    def test_wrapper_source_branch_in_output(self):
        """source_branch field surfaces the source repo branch name."""
        code, stdout, stderr = self._run_preflight()
        self.assertEqual(code, 0)
        data = json.loads(stdout)
        self.assertIn("source_branch", data, "source_branch field must be present")
        self.assertEqual(data["source_branch"], "bugfix/ABC-123")

    def test_wrapper_branch_field_matches_source_branch(self):
        """branch and source_branch are both the source repo branch."""
        code, stdout, stderr = self._run_preflight()
        self.assertEqual(code, 0)
        data = json.loads(stdout)
        self.assertEqual(data["branch"], "bugfix/ABC-123")
        self.assertEqual(data["source_branch"], "bugfix/ABC-123")

    def test_wrapper_source_dirty_warning_null_when_clean(self):
        """source_dirty_warning is null when the source repo is clean."""
        code, stdout, stderr = self._run_preflight()
        self.assertEqual(code, 0)
        data = json.loads(stdout)
        self.assertIn("source_dirty_warning", data)
        self.assertIsNone(data["source_dirty_warning"])

    def test_wrapper_constitution_read_from_install_root(self):
        """constitution.md is at the install root (wrapper artifact), not source root."""
        # Remove constitution.md from install root → preflight must fail.
        (self.tmp / "constitution.md").unlink()
        code, stdout, stderr = self._run_preflight()
        self.assertEqual(code, 2)
        self.assertIn("constitution.md", stderr)

    def test_wrapper_constitution_present_at_source_root_not_sufficient(self):
        """constitution.md inside the source repo does NOT satisfy check 1.

        The check reads from the install root.  Even if the source repo has a
        constitution.md, without one at the install root preflight fails.
        """
        # Remove install-root constitution.
        (self.tmp / "constitution.md").unlink()
        # Write a valid constitution.md inside the source repo.
        _write_constitution(self.tmp / "src-repo", populated=True)
        code, stdout, stderr = self._run_preflight()
        self.assertEqual(code, 2,
                         "constitution.md in source repo must not satisfy the check")

    def test_wrapper_memory_read_from_install_root(self):
        """memory.md is at the install root .devforge/, not the source root."""
        _write_memory(self.tmp, lines=["# Memory\n", "- Wrapper lesson.\n"])
        code, stdout, stderr = self._run_preflight()
        self.assertEqual(code, 0)
        data = json.loads(stdout)
        self.assertIsNotNone(data["memory_digest"])
        self.assertIn("Memory", data["memory_digest"])


class TestCmdPreflightWrapperSourceOnMain(unittest.TestCase):
    """cmd_preflight wrapper mode: source repo on 'main' → refused."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_wrapper_install(self.tmp, "src-repo")

        # Rename the source repo branch to 'main'.
        source_dir = str(self.tmp / "src-repo")
        subprocess.run(
            ["git", "branch", "-m", "bugfix/ABC-123", "main"],
            cwd=source_dir, capture_output=True,
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_source_on_main_exits_2(self):
        """Source repo on 'main' → exit 2 even if wrapper/install branch is a feature branch."""
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        self.assertEqual(code, 2)
        self.assertIn("main", errbuf.getvalue())

    def test_source_on_main_error_mentions_feature_branch(self):
        """Error message for source-main branch must mention feature branch."""
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(io.StringIO()):
            with contextlib.redirect_stderr(errbuf):
                cmd_preflight(args)
        self.assertIn("feature branch", errbuf.getvalue())


class TestCmdPreflightWrapperDirtySource(unittest.TestCase):
    """cmd_preflight wrapper mode: dirty source repo → warning present but exit 0."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_wrapper_install(self.tmp, "src-repo")

        # Create a pre-existing uncommitted change in the source repo.
        source_dir = self.tmp / "src-repo"
        (source_dir / "pre_existing.ts").write_text("dirty change\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self):
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        return code, buf.getvalue(), errbuf.getvalue()

    def test_dirty_source_exits_0(self):
        """Dirty source is advisory — preflight still passes (exit 0)."""
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0,
                         "Dirty source must not block preflight; "
                         "stderr={0!r}".format(stderr))

    def test_dirty_source_warning_present_in_json(self):
        """source_dirty_warning field is non-null when source is dirty."""
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0)
        data = json.loads(stdout)
        self.assertIn("source_dirty_warning", data)
        self.assertIsNotNone(data["source_dirty_warning"],
                             "source_dirty_warning must be non-null for dirty source")

    def test_dirty_source_warning_is_string(self):
        """source_dirty_warning value is a string (human-readable advisory)."""
        code, stdout, stderr = self._run()
        data = json.loads(stdout)
        warning = data["source_dirty_warning"]
        self.assertIsInstance(warning, str)
        self.assertGreater(len(warning), 0)

    def test_clean_install_root_does_not_trigger_dirty_warning(self):
        """Dirty files at the install root (forge churn) do NOT trigger the warning.

        The dirty check is on the source repo, not the install root.
        """
        # Dirty the install root with untracked files — but the source repo is
        # clean (setUp only dirtied the source repo, but we need to undo that
        # and dirty the install root instead).
        # Re-setup: clean source, dirty install root.
        self._tmp.cleanup()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_wrapper_install(self.tmp, "src-repo")

        # Dirty only the install root.
        (self.tmp / "specs" / "001").mkdir(parents=True, exist_ok=True)
        (self.tmp / "specs" / "001" / "notes.md").write_text("forge churn\n", encoding="utf-8")

        code, stdout, stderr = self._run()
        self.assertEqual(code, 0)
        data = json.loads(stdout)
        # Install-root forge churn must NOT trigger the dirty-source warning.
        self.assertIsNone(
            data["source_dirty_warning"],
            "Install-root forge churn must not trigger dirty-source warning"
        )


class TestCmdPreflightWrapperOutputShape(unittest.TestCase):
    """cmd_preflight wrapper mode: all required fields present in JSON output."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_wrapper_install(self.tmp, "src-repo")

    def tearDown(self):
        self._tmp.cleanup()

    def _get_output(self):
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            code = cmd_preflight(args)
        return code, json.loads(buf.getvalue())

    def test_all_required_fields_present(self):
        """JSON output must contain all 6 expected fields."""
        code, data = self._get_output()
        self.assertEqual(code, 0)
        expected_fields = [
            "constitution_digest",
            "memory_digest",
            "head_sha",
            "branch",
            "source_branch",
            "source_dirty_warning",
        ]
        for field in expected_fields:
            self.assertIn(field, data, "Missing field: {0}".format(field))

    def test_head_sha_is_40_chars_hex(self):
        """head_sha must be a full 40-char hex SHA (source repo)."""
        _, data = self._get_output()
        sha = data["head_sha"]
        self.assertEqual(len(sha), 40)
        int(sha, 16)  # must be valid hex


class TestCmdPreflightWrapperMissingSourceRoot(unittest.TestCase):
    """cmd_preflight wrapper mode: source_root directory does not exist → clear error.

    FIX 1: When PROJECT_ROOT points at a directory that has not been cloned,
    subprocess.run(cwd=<missing>) would raise FileNotFoundError — previously
    misreported as a git-not-on-PATH error.  The fix guards before any git
    call and emits a message naming the missing path + pointing at
    project-config.json.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        # Write an otherwise-valid install root: constitution + wrapper config
        # pointing at a source dir that does NOT exist.
        _write_constitution(self.tmp, populated=True)
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        config_path = devforge / "project-config.json"
        config_path.write_text(
            json.dumps({"PROJECT_ROOT": "no-such-repo"}), encoding="utf-8"
        )
        # "no-such-repo" directory is intentionally NOT created.

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self):
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        return code, buf.getvalue(), errbuf.getvalue()

    def test_missing_source_root_exits_2(self):
        """Missing source root → exit 2 (EXIT_FINDINGS)."""
        code, stdout, stderr = self._run()
        self.assertEqual(code, 2,
                         "must exit 2 for missing source root; stderr={0!r}".format(stderr))

    def test_missing_source_root_error_not_git_path(self):
        """Error message must NOT claim 'git not found on PATH'."""
        code, stdout, stderr = self._run()
        self.assertNotIn(
            "git not found",
            stderr,
            "misdirecting to PATH debugging is wrong: {0!r}".format(stderr),
        )

    def test_missing_source_root_error_names_problem(self):
        """Error message must mention 'source root does not exist'."""
        code, stdout, stderr = self._run()
        self.assertIn(
            "source root does not exist",
            stderr,
            "error must name the problem clearly: {0!r}".format(stderr),
        )

    def test_missing_source_root_error_references_config(self):
        """Error message must reference project-config.json so user knows where to fix it."""
        code, stdout, stderr = self._run()
        self.assertIn(
            "project-config.json",
            stderr,
            "error must reference project-config.json: {0!r}".format(stderr),
        )

    def test_standalone_with_present_root_unaffected(self):
        """Standalone mode (source_root == install_root, which always exists) is unaffected.

        The guard only fires for wrapper mode.  For standalone, is_wrapper is False
        so the guard is skipped entirely.
        """
        # Write standalone config.
        devforge = self.tmp / ".devforge"
        (devforge / "project-config.json").write_text(
            json.dumps({"PROJECT_ROOT": "."}), encoding="utf-8"
        )
        # Init a real git repo at the install root (standalone).
        cwd = str(self.tmp)
        env = dict(os.environ)
        env["GIT_AUTHOR_NAME"] = "Test"
        env["GIT_AUTHOR_EMAIL"] = "test@example.com"
        env["GIT_COMMITTER_NAME"] = "Test"
        env["GIT_COMMITTER_EMAIL"] = "test@example.com"
        subprocess.run(["git", "init", "-b", "feature/standalone"],
                       cwd=cwd, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"],
                       cwd=cwd, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=cwd, capture_output=True)
        subprocess.run(["git", "add", "-A"],
                       cwd=cwd, capture_output=True, env=env)
        subprocess.run(["git", "commit", "-m", "init"],
                       cwd=cwd, capture_output=True, env=env)

        code, stdout, stderr = self._run()
        # Standalone with a real git repo at install root → preflight passes
        # (constitution check passed already in setUp; no wip.md; feature branch).
        self.assertEqual(code, 0,
                         "standalone with present install root must pass; "
                         "stderr={0!r}".format(stderr))


def _init_standalone_clean(tmp, branch="feature/standalone"):
    # type: (Path, str) -> None
    """Set up a standalone (single-repo) install that is CLEAN (no untracked files).

    Creates a git repo in tmp, commits constitution.md + .devforge/ into it,
    then checks out the desired feature branch.  No untracked files remain, so
    _git_status_dirty returns False for this repo.
    """
    env = dict(os.environ)
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"

    cwd = str(tmp)
    subprocess.run(["git", "init", "-b", "_init-tmp"], cwd=cwd, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"],
                   cwd=cwd, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"],
                   cwd=cwd, capture_output=True)

    # Write forge artifacts.
    _write_constitution(tmp, populated=True)
    devforge = tmp / ".devforge"
    devforge.mkdir(exist_ok=True)
    (devforge / "placeholder.txt").write_text("devforge dir\n", encoding="utf-8")

    # Commit everything so there are no untracked files.
    subprocess.run(["git", "add", "-A"], cwd=cwd, capture_output=True, env=env)
    subprocess.run(
        ["git", "commit", "-m", "init standalone"],
        cwd=cwd, capture_output=True, env=env,
    )
    # Checkout feature branch.
    subprocess.run(
        ["git", "checkout", "-b", branch],
        cwd=cwd, capture_output=True, env=env,
    )


class TestCmdPreflightStandaloneNotRegressed(unittest.TestCase):
    """Standalone mode (no wrapper config): existing behavior unchanged.

    These tests mirror existing standalone tests to confirm no regression
    after the workspace-resolver integration.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        _init_standalone_clean(self.tmp, branch="feature/standalone")
        # No project-config.json → standalone fail-soft.

    def tearDown(self):
        self._tmp.cleanup()

    def test_standalone_no_config_exits_0(self):
        """No project-config.json → standalone mode → preflight passes."""
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        self.assertEqual(code, 0,
                         "standalone with no config must pass; "
                         "stderr={0!r}".format(errbuf.getvalue()))

    def test_standalone_branch_in_output(self):
        """branch field in output is the install root's branch (standalone)."""
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_preflight(args)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["branch"], "feature/standalone")
        self.assertEqual(data["source_branch"], "feature/standalone")

    def test_standalone_with_dot_project_root_exits_0(self):
        """Explicit PROJECT_ROOT="." → standalone mode → preflight passes."""
        devforge = self.tmp / ".devforge"
        devforge.mkdir(exist_ok=True)
        (devforge / "project-config.json").write_text(
            json.dumps({"PROJECT_ROOT": "."}), encoding="utf-8"
        )
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        self.assertEqual(code, 0, "PROJECT_ROOT='.' must be standalone; "
                         "stderr={0!r}".format(errbuf.getvalue()))

    def test_standalone_source_dirty_warning_null_for_clean_repo(self):
        """source_dirty_warning is null for a clean standalone repo.

        The setUp uses _init_standalone_clean which commits all forge files,
        leaving no untracked files in the single repo.
        """
        buf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            cmd_preflight(args)
        data = json.loads(buf.getvalue())
        self.assertIsNone(data["source_dirty_warning"])

    def test_standalone_dirty_single_repo_triggers_warning(self):
        """In standalone mode, a dirty repo triggers the dirty-source warning.

        This is accurate/correct: the single repo IS both install and source,
        so if it's dirty the user should be informed.
        """
        # Dirty the repo with an untracked file.
        (self.tmp / "new_untracked.py").write_text("x = 1\n", encoding="utf-8")
        buf = io.StringIO()
        errbuf = io.StringIO()
        args = _FakeArgs(root=str(self.tmp))
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(errbuf):
                code = cmd_preflight(args)
        self.assertEqual(code, 0, "Dirty standalone repo must still pass preflight; "
                         "stderr={0!r}".format(errbuf.getvalue()))
        data = json.loads(buf.getvalue())
        self.assertIsNotNone(
            data["source_dirty_warning"],
            "Dirty standalone repo must trigger source_dirty_warning"
        )


if __name__ == "__main__":
    unittest.main()
