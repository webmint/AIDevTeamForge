"""Tests for src/devforge/lib/_implement/_cmds_commit.py.

Coverage:

  _extract_ticket_id:
    - Branch with Jira-style token in middle: PROJ-123 extracted.
    - Branch with path prefix: spec/PROJ-123-foo → PROJ-123.
    - Branch with no ticket token: returns full branch name.
    - lowercase letters in ticket prefix: not matched (pattern is [A-Z]+).
    - Ticket at start: PROJ-42-do-thing → PROJ-42.

  _compose_message:
    Task mode (fix_mode=False, default):
    - Wrapper mode: "[TICKET-ID] - <title> (Task NNN)".
    - Non-wrapper mode: "[WIP] task: <title> (Task NNN)".
    - With attribution: attribution appended verbatim.
    - Empty attribution: no trailing newline/suffix.
    Fix mode (fix_mode=True):
    - Non-wrapper: "[WIP] fix: <title>" (no Task suffix).
    - Wrapper: "[TICKET-ID] - <title>" (no Task suffix).
    - Attribution rules identical to task mode.

  _get_commit_attribution:
    - Key present with value → value returned.
    - Key absent → empty string.
    - Key present, empty string → empty string.

  cmd_wip_commit (integration, real git tempdir):
    Task mode:
    - Non-wrapper: commit message format "[WIP] task: <title> (Task NNN)".
    - Wrapper mode: commit message format "[TICKET-ID] - <title> (Task NNN)".
    - COMMIT_ATTRIBUTION honored (appended when present).
    - COMMIT_ATTRIBUTION absent → no attribution line in message.
    - ONLY named paths committed (critical safety assertion).
    - wip.md cleared after successful commit.
    - --files invalid JSON → exit 1, stderr.
    - --files as non-array JSON → exit 1, stderr.
    - Staging a non-existent file → exit 2, stderr.

    Fix mode (new):
    - Standalone fix: stages only touched_files, message "[WIP] fix: <title>", exit 0.
    - Wrapper fix: stages only touched_files in source repo, message "[TICKET-ID] - <title>", exit 0.
    - Fix mode with attribution: attribution appended in standalone; suppressed in wrapper.
    - Fix mode only named paths committed (no task/index in commit).
    - wip.md cleared after fix commit.
    - emits JSON {committed:true, head_sha, message} in fix mode.

    Mixed mode (new):
    - --task-file only (missing --index and --number) → EXIT_ERR with message naming missing args.
    - --index only → EXIT_ERR.
    - --number only → EXIT_ERR.
    - --task-file + --index (missing --number) → EXIT_ERR.

Design notes:
- Each test creates its own git tempdir to avoid cross-test contamination.
- Git tempdir is initialised with git init + git config + initial commit.
- wip.md is pre-created so clear_wip_marker has something to remove.
- The "only named paths committed" assertion is the critical safety test:
  a second file is created and left dirty (never added to --files);
  after wip-commit it must still be untracked (not in git log --name-only).
- Branch name for wrapper tests uses the pattern spec/PROJ-42-widget so
  the ticket extraction produces PROJ-42.

Stdlib only. Python 3.8+.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------

_LIB_DIR = str(Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _implement._cmds_commit import (  # noqa: E402
    _extract_ticket_id,
    _compose_message,
    _get_commit_attribution,
    cmd_wip_commit,
    EXIT_OK,
    EXIT_ERR,
    EXIT_FINDINGS,
)


# ---------------------------------------------------------------------------
# Git tempdir helpers
# ---------------------------------------------------------------------------


def _init_git_repo(tmpdir):
    """Initialise a minimal git repo in tmpdir. Returns (root_path, initial_sha)."""
    root = Path(tmpdir)
    env = _git_env()

    def run(*cmd):
        result = subprocess.run(
            list(cmd), cwd=str(root), capture_output=True, text=True,
            env=env, check=True,
        )
        return result.stdout.strip()

    run("git", "init", "-b", "main")
    run("git", "config", "user.email", "test@example.com")
    run("git", "config", "user.name", "Test User")
    # Create an initial commit so HEAD exists.
    init_file = root / "README.md"
    init_file.write_text("# Test repo\n")
    run("git", "add", "--", str(init_file))
    run("git", "commit", "-m", "init")
    sha = run("git", "rev-parse", "HEAD")
    return root, sha


def _git_env():
    """Return a clean env dict for git subprocess calls."""
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@test.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@test.com"
    return env


def _checkout_branch(root, branch):
    """Create and check out a new branch in the git repo at root."""
    env = _git_env()
    subprocess.run(
        ["git", "checkout", "-b", branch],
        cwd=str(root), capture_output=True, text=True, env=env, check=True,
    )


def _git_head_sha(root):
    env = _git_env()
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(root), capture_output=True, text=True, env=env, check=False,
    )
    return result.stdout.strip()


def _git_log_name_only(root):
    """Return the list of files in the most recent commit."""
    env = _git_env()
    result = subprocess.run(
        ["git", "log", "-1", "--name-only", "--format="],
        cwd=str(root), capture_output=True, text=True, env=env, check=False,
    )
    return [line for line in result.stdout.strip().splitlines() if line.strip()]


def _git_last_message(root):
    """Return the commit message of the most recent commit."""
    env = _git_env()
    result = subprocess.run(
        ["git", "log", "-1", "--format=%B"],
        cwd=str(root), capture_output=True, text=True, env=env, check=False,
    )
    return result.stdout.strip()


def _git_status_short(root):
    """Return `git status --short` output."""
    env = _git_env()
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(root), capture_output=True, text=True, env=env, check=False,
    )
    return result.stdout.strip()


def _write_project_config(root, workspace_mode="standalone", commit_attribution="",
                          project_root=None):
    """Write a minimal .devforge/project-config.json.

    project_root: when set, written as PROJECT_ROOT (makes resolve_workspace
    treat this as a wrapper install).  When None, PROJECT_ROOT is omitted
    (resolve_workspace treats it as standalone).
    """
    devforge = root / ".devforge"
    devforge.mkdir(exist_ok=True)
    config = {
        "WORKSPACE_MODE": workspace_mode,
        "COMMIT_ATTRIBUTION": commit_attribution,
    }
    if project_root is not None:
        config["PROJECT_ROOT"] = project_root
    (devforge / "project-config.json").write_text(json.dumps(config, indent=2))


def _init_source_repo(install_root, source_repo_name, branch_name):
    """Create a nested source git repo inside install_root on branch_name.

    Returns the source repo root Path.
    """
    source_dir = install_root / source_repo_name
    source_dir.mkdir(parents=True, exist_ok=True)
    env = _git_env()

    def run(*cmd):
        result = subprocess.run(
            list(cmd), cwd=str(source_dir), capture_output=True, text=True,
            env=env, check=True,
        )
        return result.stdout.strip()

    try:
        run("git", "init", "-b", "_init-tmp")
    except subprocess.CalledProcessError:
        run("git", "init")
    run("git", "config", "user.email", "test@example.com")
    run("git", "config", "user.name", "Test User")
    # Initial commit so HEAD exists.
    seed = source_dir / "seed.txt"
    seed.write_text("initial\n")
    run("git", "add", "--", str(seed))
    run("git", "commit", "-m", "init")
    run("git", "checkout", "-b", branch_name)
    return source_dir


def _write_wip_md(root):
    """Write a minimal wip.md so clear_wip_marker has something to clear."""
    devforge = root / ".devforge"
    devforge.mkdir(exist_ok=True)
    (devforge / "wip.md").write_text("# WIP Marker\n**Command**: /implement\n")


def _make_fake_args(**kwargs):
    """Return a simple namespace-like object for testing cmd_wip_commit."""
    class _Args:
        pass
    a = _Args()
    a.files = kwargs.get("files", "[]")
    a.task_file = kwargs.get("task_file", "")
    a.index = kwargs.get("index", "")
    a.number = kwargs.get("number", "")
    a.title = kwargs.get("title", "Define types")
    a.root = kwargs.get("root", ".")
    return a


# ---------------------------------------------------------------------------
# Unit tests — _extract_ticket_id
# ---------------------------------------------------------------------------


class TestExtractTicketId(unittest.TestCase):

    def test_branch_with_ticket_in_middle(self):
        self.assertEqual(_extract_ticket_id("PROJ-123-slugify-feature"), "PROJ-123")

    def test_branch_with_path_prefix(self):
        self.assertEqual(_extract_ticket_id("spec/PROJ-42-widget-catalog"), "PROJ-42")

    def test_branch_no_ticket_token(self):
        self.assertEqual(_extract_ticket_id("develop-2.0-init"), "develop-2.0-init")

    def test_lowercase_prefix_not_matched(self):
        # Pattern requires uppercase [A-Z]+
        self.assertEqual(_extract_ticket_id("proj-123-feature"), "proj-123-feature")

    def test_ticket_at_start(self):
        self.assertEqual(_extract_ticket_id("ABC-99"), "ABC-99")

    def test_feature_slash_with_ticket(self):
        self.assertEqual(_extract_ticket_id("feature/FEAT-7-do-thing"), "FEAT-7")

    def test_multi_digit(self):
        self.assertEqual(_extract_ticket_id("MYPROJ-1234-long-title"), "MYPROJ-1234")


# ---------------------------------------------------------------------------
# Unit tests — _compose_message
# ---------------------------------------------------------------------------


class TestComposeMessage(unittest.TestCase):

    def test_non_wrapper_no_attribution(self):
        msg = _compose_message(False, "", "Define types", "001", "")
        self.assertEqual(msg, "[WIP] task: Define types (Task 001)")

    def test_non_wrapper_with_attribution(self):
        msg = _compose_message(False, "", "Build form", "002", "\n\nCo-Authored-By: X <x@x.com>")
        self.assertEqual(msg, "[WIP] task: Build form (Task 002)\n\nCo-Authored-By: X <x@x.com>")

    def test_wrapper_with_ticket(self):
        msg = _compose_message(True, "PROJ-42", "Define types", "001", "")
        self.assertEqual(msg, "[PROJ-42] - Define types (Task 001)")

    def test_wrapper_with_attribution(self):
        msg = _compose_message(True, "ABC-7", "Build form", "002", "\n\nCo-Author: Y")
        self.assertEqual(msg, "[ABC-7] - Build form (Task 002)\n\nCo-Author: Y")

    def test_wrapper_empty_attribution_no_suffix(self):
        msg = _compose_message(True, "X-1", "Title", "003", "")
        self.assertFalse(msg.endswith("\n"), "No trailing newline when attribution is empty")

    # --- Fix mode (fix_mode=True) ---

    def test_fix_mode_non_wrapper_no_attribution(self):
        msg = _compose_message(False, "", "null guard", "", "", fix_mode=True)
        self.assertEqual(msg, "[WIP] fix: null guard")

    def test_fix_mode_non_wrapper_no_task_suffix(self):
        """Fix mode must NOT contain '(Task' in the message."""
        msg = _compose_message(False, "", "null guard", "001", "", fix_mode=True)
        self.assertNotIn("Task", msg)
        self.assertNotIn("(", msg)

    def test_fix_mode_non_wrapper_with_attribution(self):
        attr = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        msg = _compose_message(False, "", "null guard", "", attr, fix_mode=True)
        self.assertEqual(msg, "[WIP] fix: null guard" + attr)

    def test_fix_mode_wrapper_no_task_suffix(self):
        msg = _compose_message(True, "ABC-99", "null guard", "", "", fix_mode=True)
        self.assertEqual(msg, "[ABC-99] - null guard")
        self.assertNotIn("Task", msg)

    def test_fix_mode_wrapper_with_attribution(self):
        attr = "\n\nCo-Authored-By: X <x@x.com>"
        msg = _compose_message(True, "ABC-99", "null guard", "", attr, fix_mode=True)
        self.assertEqual(msg, "[ABC-99] - null guard" + attr)

    def test_task_mode_unchanged_by_fix_mode_flag_false(self):
        """Explicitly passing fix_mode=False must produce the same result as default."""
        msg_default = _compose_message(False, "", "Do thing", "007", "")
        msg_explicit = _compose_message(False, "", "Do thing", "007", "", fix_mode=False)
        self.assertEqual(msg_default, msg_explicit)


# ---------------------------------------------------------------------------
# Unit tests — _get_commit_attribution
# ---------------------------------------------------------------------------


class TestConfigHelpers(unittest.TestCase):

    def test_get_attribution_present(self):
        val = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        self.assertEqual(_get_commit_attribution({"COMMIT_ATTRIBUTION": val}), val)

    def test_get_attribution_absent(self):
        self.assertEqual(_get_commit_attribution({}), "")

    def test_get_attribution_empty_string(self):
        self.assertEqual(_get_commit_attribution({"COMMIT_ATTRIBUTION": ""}), "")


# ---------------------------------------------------------------------------
# Integration tests — cmd_wip_commit
# ---------------------------------------------------------------------------


class TestCmdWipCommit(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root, _ = _init_git_repo(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_staged_files(self, *names):
        """Create files in root, add them to git, return their relative paths."""
        env = _git_env()
        paths = []
        for name in names:
            f = self.root / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("# content of {0}\n".format(name))
            subprocess.run(
                ["git", "add", "--", str(f)],
                cwd=str(self.root), capture_output=True, env=env, check=True,
            )
            paths.append(name)
        return paths

    def _create_untracked_file(self, name, content="dirty\n"):
        """Create a file in root but do NOT add to git."""
        f = self.root / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
        return name

    def test_non_wrapper_commit_message_format(self):
        """Non-wrapper: message is '[WIP] task: <title> (Task NNN)'."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)

        # Create and pre-stage the files that will be committed.
        self._create_staged_files("tasks/001-define-types.md", "tasks/README.md")
        # Create a "source file" that will be in --files.
        (self.root / "src").mkdir(exist_ok=True)
        (self.root / "src" / "widget.py").write_text("class Widget: pass\n")
        env = _git_env()
        subprocess.run(
            ["git", "add", "--", str(self.root / "src" / "widget.py")],
            cwd=str(self.root), capture_output=True, env=env, check=True,
        )

        args = _make_fake_args(
            files=json.dumps(["src/widget.py"]),
            task_file="tasks/001-define-types.md",
            index="tasks/README.md",
            number="001",
            title="Define types",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(self.root)
        self.assertEqual(msg, "[WIP] task: Define types (Task 001)")

    def test_wrapper_commit_message_format(self):
        """Wrapper mode: message uses TICKET-ID from the SOURCE repo branch.

        The install root contains project-config.json with PROJECT_ROOT pointing
        to a nested source git repo on branch 'spec/PROJ-42-widget-catalog'.
        The commit lands in the source repo; the message is '[PROJ-42] - ...'.
        """
        source_name = "src-repo"
        source_dir = _init_source_repo(self.root, source_name, "spec/PROJ-42-widget-catalog")
        _write_project_config(
            self.root, workspace_mode="wrapper",
            project_root=source_name,
        )
        _write_wip_md(self.root)

        # Create a source file in the source repo and stage it.
        src_file = source_dir / "widget.py"
        src_file.write_text("class Widget: pass\n")
        env = _git_env()
        subprocess.run(
            ["git", "add", "--", str(src_file)],
            cwd=str(source_dir), capture_output=True, env=env, check=True,
        )

        args = _make_fake_args(
            files=json.dumps(["widget.py"]),
            task_file="tasks/001-define-types.md",
            index="tasks/README.md",
            number="001",
            title="Define types",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        # The commit lands in the SOURCE repo.
        msg = _git_last_message(source_dir)
        self.assertEqual(msg, "[PROJ-42] - Define types (Task 001)")

    def test_commit_attribution_appended(self):
        """COMMIT_ATTRIBUTION is appended when present in config."""
        attribution = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        _write_project_config(
            self.root, workspace_mode="standalone", commit_attribution=attribution
        )
        _write_wip_md(self.root)

        self._create_staged_files("tasks/001-define-types.md", "tasks/README.md")

        args = _make_fake_args(
            files=json.dumps([]),
            task_file="tasks/001-define-types.md",
            index="tasks/README.md",
            number="001",
            title="Define types",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(self.root)
        self.assertIn("Co-Authored-By: Claude", msg)

    def test_standalone_attribution_unchanged_phase6_regression(self):
        """Phase 6 regression: standalone WIP commit STILL appends attribution (byte-identical).

        The Phase 6 change must NOT strip attribution from the standalone path.
        This test proves the standalone arm is byte-identical to before Phase 6.
        """
        attribution = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        _write_project_config(
            self.root, workspace_mode="standalone", commit_attribution=attribution
        )
        _write_wip_md(self.root)

        self._create_staged_files("tasks/001-define-types.md", "tasks/README.md")

        args = _make_fake_args(
            files=json.dumps([]),
            task_file="tasks/001-define-types.md",
            index="tasks/README.md",
            number="001",
            title="Define types",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(self.root)
        # Standalone: attribution IS appended — the user opted in via ai_attribution config.
        self.assertIn("Co-Authored-By: Claude", msg,
                      "Standalone WIP commit must still carry attribution after Phase 6 (no regression)")
        # Full expected message for byte-identical verification.
        expected = "[WIP] task: Define types (Task 001)" + attribution
        self.assertEqual(msg, expected,
                         "Standalone message must be byte-identical to pre-Phase-6; "
                         "got: {0!r}".format(msg))

    def test_no_attribution_when_absent(self):
        """No Co-Authored-By line when COMMIT_ATTRIBUTION is absent."""
        _write_project_config(self.root, workspace_mode="standalone", commit_attribution="")
        _write_wip_md(self.root)

        self._create_staged_files("tasks/001-define-types.md", "tasks/README.md")

        args = _make_fake_args(
            files=json.dumps([]),
            task_file="tasks/001-define-types.md",
            index="tasks/README.md",
            number="001",
            title="Define types",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(self.root)
        self.assertNotIn("Co-Authored-By", msg)
        self.assertNotIn("Co-Author", msg)

    def test_only_named_paths_committed_critical_safety(self):
        """Critical safety: an unrelated dirty file must NOT appear in the commit."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)

        # Stage only the named files.
        self._create_staged_files("tasks/001-define-types.md", "tasks/README.md")

        # Create an UNRELATED dirty file that is NEVER added to --files.
        unrelated = "src/unrelated_dirty_file.py"
        self._create_untracked_file(unrelated, "# this must not be committed\n")

        # Confirm the dirty file (or its parent dir) is untracked BEFORE the commit.
        # git status --short may show `?? src/` at directory level when the dir is new.
        status_before = _git_status_short(self.root)
        self.assertTrue(
            "unrelated_dirty_file.py" in status_before or "src/" in status_before,
            "Unrelated file or its parent must be untracked before commit: {0!r}".format(
                status_before
            ),
        )

        args = _make_fake_args(
            files=json.dumps([]),  # <-- unrelated file NOT included
            task_file="tasks/001-define-types.md",
            index="tasks/README.md",
            number="001",
            title="Define types",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        # The unrelated file must still be dirty (untracked) after the commit.
        # git status --short may show `?? src/` at directory level.
        status_after = _git_status_short(self.root)
        self.assertTrue(
            "unrelated_dirty_file.py" in status_after or "src/" in status_after,
            "Unrelated file or its parent must remain untracked after wip-commit: {0!r}".format(
                status_after
            ),
        )

        # The commit must NOT include the unrelated file.
        committed_files = _git_log_name_only(self.root)
        for cf in committed_files:
            self.assertNotIn("unrelated_dirty_file", cf,
                             "Unrelated file must not appear in the commit")

    def test_touched_files_included_in_commit(self):
        """Files listed in --files are staged and committed."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)

        # Create a source file and pre-stage it (simulating agent output).
        (self.root / "src").mkdir(exist_ok=True)
        src_file = self.root / "src" / "widget.py"
        src_file.write_text("class Widget: pass\n")
        env = _git_env()
        subprocess.run(
            ["git", "add", "--", str(src_file)],
            cwd=str(self.root), capture_output=True, env=env, check=True,
        )
        self._create_staged_files("tasks/001-define-types.md", "tasks/README.md")

        args = _make_fake_args(
            files=json.dumps(["src/widget.py"]),
            task_file="tasks/001-define-types.md",
            index="tasks/README.md",
            number="001",
            title="Define types",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        committed = _git_log_name_only(self.root)
        self.assertIn("src/widget.py", committed)
        self.assertIn("tasks/001-define-types.md", committed)
        self.assertIn("tasks/README.md", committed)

    def test_wip_md_cleared_after_commit(self):
        """wip.md is removed after a successful commit."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)

        wip_path = self.root / ".devforge" / "wip.md"
        self.assertTrue(wip_path.exists(), "wip.md must exist before commit")

        self._create_staged_files("tasks/001-define-types.md", "tasks/README.md")

        args = _make_fake_args(
            files=json.dumps([]),
            task_file="tasks/001-define-types.md",
            index="tasks/README.md",
            number="001",
            title="Define types",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(wip_path.exists(), "wip.md must be cleared after commit")

    def test_emits_json_with_head_sha_and_message(self):
        """Output JSON contains committed, head_sha, message."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)

        self._create_staged_files("tasks/001-define-types.md", "tasks/README.md")

        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            args = _make_fake_args(
                files=json.dumps([]),
                task_file="tasks/001-define-types.md",
                index="tasks/README.md",
                number="001",
                title="Define types",
                root=str(self.root),
            )
            rc = cmd_wip_commit(args)
        finally:
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

        self.assertEqual(rc, EXIT_OK)
        result = json.loads(output.strip())
        self.assertTrue(result["committed"])
        self.assertIsInstance(result["head_sha"], str)
        self.assertGreater(len(result["head_sha"]), 0)
        self.assertIn("Define types", result["message"])

    def test_invalid_files_json_exit_err(self):
        """--files with invalid JSON returns EXIT_ERR."""
        _write_project_config(self.root)

        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args(
                files="not-json",
                task_file="tasks/001.md",
                index="tasks/README.md",
                number="001",
                title="Define types",
                root=str(self.root),
            )
            rc = cmd_wip_commit(args)
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_ERR)
        self.assertIn("not valid JSON", err)

    def test_files_non_array_json_exit_err(self):
        """--files as non-array JSON (e.g. object) returns EXIT_ERR."""
        _write_project_config(self.root)

        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args(
                files='{"key": "value"}',
                task_file="tasks/001.md",
                index="tasks/README.md",
                number="001",
                title="Define types",
                root=str(self.root),
            )
            rc = cmd_wip_commit(args)
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_ERR)

    def test_staging_nonexistent_file_exit_findings(self):
        """Staging a file that doesn't exist returns EXIT_FINDINGS."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)

        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args(
                files=json.dumps(["nonexistent/path/to/file.py"]),
                task_file="tasks/nonexistent-task.md",
                index="tasks/README.md",
                number="001",
                title="Define types",
                root=str(self.root),
            )
            rc = cmd_wip_commit(args)
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIn("staging failed", err)

    def test_no_config_file_defaults_to_non_wrapper(self):
        """When project-config.json is absent, non-wrapper format is used."""
        _write_wip_md(self.root)

        self._create_staged_files("tasks/001-define-types.md", "tasks/README.md")

        args = _make_fake_args(
            files=json.dumps([]),
            task_file="tasks/001-define-types.md",
            index="tasks/README.md",
            number="001",
            title="Define types",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(self.root)
        self.assertTrue(msg.startswith("[WIP] task:"))

    def test_wrapper_no_ticket_in_branch_uses_full_branch_name(self):
        """Wrapper + no ticket token in SOURCE branch: full branch name used as TICKET-ID."""
        source_name = "src-repo"
        source_dir = _init_source_repo(self.root, source_name, "develop-no-ticket")
        _write_project_config(
            self.root, workspace_mode="wrapper",
            project_root=source_name,
        )
        _write_wip_md(self.root)

        # Create a source file in the source repo and stage it.
        src_file = source_dir / "widget.py"
        src_file.write_text("class Widget: pass\n")
        env = _git_env()
        subprocess.run(
            ["git", "add", "--", str(src_file)],
            cwd=str(source_dir), capture_output=True, env=env, check=True,
        )

        args = _make_fake_args(
            files=json.dumps(["widget.py"]),
            task_file="tasks/001-define-types.md",
            index="tasks/README.md",
            number="001",
            title="Define types",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        # The commit lands in the SOURCE repo.
        msg = _git_last_message(source_dir)
        # Message format: "[develop-no-ticket] - Define types (Task 001)"
        self.assertIn("[develop-no-ticket]", msg)
        self.assertIn("Define types (Task 001)", msg)

    def test_nothing_to_commit_returns_exit_findings(self):
        """Calling wip-commit with --files '[]' when task_file + index are already
        committed (no staged changes) returns EXIT_FINDINGS with a descriptive
        stderr message.

        NOTE: In production this case is prevented by the mark-complete →
        wip-commit ordering (the mark-complete call always mutates task_file
        and index before wip-commit runs, so there is always something staged).
        This test exercises the git-level guard: if nothing is staged, git commit
        fails, and the helper must surface EXIT_FINDINGS — not swallow the error.
        """
        import io
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)

        # Create and commit task_file + index in the initial commit (already clean).
        env = _git_env()
        tasks_dir = self.root / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        task_file = tasks_dir / "001-define-types.md"
        index_file = tasks_dir / "README.md"
        task_file.write_text("# Task 001\n")
        index_file.write_text("# Index\n")
        subprocess.run(
            ["git", "add", "--", str(task_file), str(index_file)],
            cwd=str(self.root), capture_output=True, env=env, check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "add task files"],
            cwd=str(self.root), capture_output=True, env=env, check=True,
        )

        # Now call wip-commit with --files '[]' and the already-committed, unchanged
        # task_file + index.  There is nothing staged → git commit should fail.
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args(
                files=json.dumps([]),
                task_file="tasks/001-define-types.md",
                index="tasks/README.md",
                number="001",
                title="Define types",
                root=str(self.root),
            )
            rc = cmd_wip_commit(args)
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        self.assertEqual(rc, EXIT_FINDINGS)
        # The stderr message must be descriptive (comes from _git_commit failure).
        self.assertTrue(
            len(err.strip()) > 0,
            "Expected a descriptive stderr message when nothing to commit",
        )


# ---------------------------------------------------------------------------
# New Phase 5 wrapper-mode integration tests
# ---------------------------------------------------------------------------


class TestCmdWipCommitWrapper(unittest.TestCase):
    """Integration tests for cmd_wip_commit in true two-repo wrapper mode.

    Fixture layout:
      <install_dir>/                   (wrapper / install root)
        .devforge/
          project-config.json          (PROJECT_ROOT = "src-repo")
          wip.md
        specs/001-widget/
          tasks/
            001-define-types.md        (task file — wrapper artifact)
            README.md                  (index — wrapper artifact)
        src-repo/                      (source repo — nested git repo)
          seed.txt
          src/
            widget.ts                  (source file changed by the agent)
    """

    def setUp(self):
        self.install_tmpdir = tempfile.mkdtemp()
        self.install_root = Path(self.install_tmpdir)
        self.source_name = "src-repo"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.install_tmpdir, ignore_errors=True)

    def _setup_wrapper(self, source_branch="bugfix/ABC-123", attribution=""):
        """Set up the full two-repo wrapper fixture.

        Returns (source_dir, task_file_relpath, index_relpath).
        """
        # Create the nested source git repo.
        source_dir = _init_source_repo(
            self.install_root, self.source_name, source_branch
        )

        # Write the install-root project config.
        _write_project_config(
            self.install_root,
            workspace_mode="wrapper",
            commit_attribution=attribution,
            project_root=self.source_name,
        )

        # Write wip.md in the install root.
        _write_wip_md(self.install_root)

        # Create wrapper-side task artifacts (NOT staged; wrapper artifacts).
        tasks_dir = self.install_root / "specs" / "001-widget" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        task_file = tasks_dir / "001-define-types.md"
        index_file = tasks_dir / "README.md"
        task_file.write_text("# Task 001\nStatus: Complete\n")
        index_file.write_text("# Task Index\n- [001] Define types\n")

        # Relative paths for --task-file and --index.
        task_rel = str(task_file.relative_to(self.install_root))
        index_rel = str(index_file.relative_to(self.install_root))

        return source_dir, task_rel, index_rel

    def _stage_source_file(self, source_dir, relpath, content="// changed\n"):
        """Create and stage a file in the source repo. Returns the relpath."""
        full = source_dir / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        env = _git_env()
        subprocess.run(
            ["git", "add", "--", str(full)],
            cwd=str(source_dir), capture_output=True, env=env, check=True,
        )
        return relpath

    def test_wrapper_commit_lands_in_source_repo(self):
        """Wrapper mode: the source file commit lands in the SOURCE repo."""
        source_dir, task_rel, index_rel = self._setup_wrapper("bugfix/ABC-123")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file=task_rel,
            index=index_rel,
            number="001",
            title="Define types",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        # The source file must appear in the source repo's latest commit.
        committed = _git_log_name_only(source_dir)
        self.assertIn(src_file, committed,
                      "Source file must appear in source repo commit; got: {0!r}".format(
                          committed))

    def test_wrapper_commit_message_uses_source_branch_ticket(self):
        """Wrapper mode: commit message ticket-id comes from the SOURCE branch."""
        source_dir, task_rel, index_rel = self._setup_wrapper("bugfix/ABC-123")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file=task_rel,
            index=index_rel,
            number="001",
            title="Define types",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        msg = _git_last_message(source_dir)
        # bugfix/ABC-123 → ABC-123
        self.assertEqual(msg, "[ABC-123] - Define types (Task 001)")

    def test_wrapper_task_file_not_in_source_commit(self):
        """Wrapper mode: task_file (wrapper artifact) is NOT staged in the source repo.

        Critical D1 assertion: after wip-commit, the task file must NOT appear
        in the source repo's latest commit.
        """
        source_dir, task_rel, index_rel = self._setup_wrapper("bugfix/ABC-123")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file=task_rel,
            index=index_rel,
            number="001",
            title="Define types",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        committed = _git_log_name_only(source_dir)
        # No task file or index path should appear in the source repo commit.
        for cf in committed:
            self.assertNotIn("tasks", cf,
                             "task_file/index must NOT appear in source repo commit; "
                             "got: {0!r}".format(committed))
            self.assertNotIn("specs", cf,
                             "specs/ path must NOT appear in source repo commit; "
                             "got: {0!r}".format(committed))

    def test_wrapper_task_file_remains_on_disk_after_commit(self):
        """Wrapper mode: task_file and index remain on disk after wip-commit.

        mark-complete wrote them; wip-commit must NOT delete them.
        The 'uncommitted' / not-in-source-commit contract is enforced by
        test_wrapper_task_file_not_in_source_commit.
        """
        source_dir, task_rel, index_rel = self._setup_wrapper("bugfix/ABC-123")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        # Confirm task_file + index are NOT tracked by any git repo at the
        # install root level (the install root has no git repo in our fixture).
        # We verify this by confirming the source repo is clean of them.
        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file=task_rel,
            index=index_rel,
            number="001",
            title="Define types",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        # The task file must still exist on disk (wip-commit must not delete it).
        task_path = self.install_root / task_rel
        self.assertTrue(task_path.exists(), "task_file must remain on disk after wip-commit")
        index_path = self.install_root / index_rel
        self.assertTrue(index_path.exists(), "index must remain on disk after wip-commit")

    def test_wrapper_wip_md_cleared_in_install_root(self):
        """Wrapper mode: wip.md in the INSTALL root is cleared after source commit."""
        source_dir, task_rel, index_rel = self._setup_wrapper("bugfix/ABC-123")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        wip_path = self.install_root / ".devforge" / "wip.md"
        self.assertTrue(wip_path.exists(), "wip.md must exist before wip-commit")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file=task_rel,
            index=index_rel,
            number="001",
            title="Define types",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(wip_path.exists(), "wip.md must be cleared after wrapper wip-commit")

    def test_wrapper_emits_source_head_sha(self):
        """Wrapper mode: emitted head_sha is the SOURCE repo's new HEAD."""
        source_dir, task_rel, index_rel = self._setup_wrapper("bugfix/ABC-123")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        import io as _io
        old_stdout = sys.stdout
        sys.stdout = _io.StringIO()
        try:
            args = _make_fake_args(
                files=json.dumps([src_file]),
                task_file=task_rel,
                index=index_rel,
                number="001",
                title="Define types",
                root=str(self.install_root),
            )
            rc = cmd_wip_commit(args)
        finally:
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

        self.assertEqual(rc, EXIT_OK)
        result = json.loads(output.strip())
        emitted_sha = result["head_sha"]

        # Read the actual source repo HEAD.
        actual_source_sha = _git_head_sha(source_dir)
        self.assertEqual(
            emitted_sha, actual_source_sha,
            "Emitted head_sha must be the source repo HEAD"
        )

    def test_wrapper_install_churn_stays_uncommitted(self):
        """Wrapper mode: unrelated install-root changes are NOT swept into source commit.

        A dirty file at the install root must remain uncommitted after wip-commit.
        (The install root has no git repo in this fixture; this test confirms
        the source commit only contains the explicitly listed source files.)
        """
        source_dir, task_rel, index_rel = self._setup_wrapper("bugfix/ABC-123")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        # Create an unrelated install-root file (e.g. an audit report).
        dirty_file = self.install_root / "audits" / "2026-06-01-audit.md"
        dirty_file.parent.mkdir(exist_ok=True)
        dirty_file.write_text("# Audit\n")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file=task_rel,
            index=index_rel,
            number="001",
            title="Define types",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        # The source repo commit must NOT contain the install-root dirty file.
        committed = _git_log_name_only(source_dir)
        for cf in committed:
            self.assertNotIn("audit", cf,
                             "Install-root churn must not appear in source commit")

    def test_wrapper_source_commit_no_attribution_when_set(self):
        """Phase 6 D5: wrapper-mode SOURCE commit carries NO AI trace even when
        COMMIT_ATTRIBUTION is configured.

        This is the belt-and-suspenders guard for the already-pushed-skip edge:
        if /finalize refuses to squash (WIP commits already pushed), the source
        WIP commits must be traceless on the remote.

        Assertion flipped from the pre-Phase-6 expectation that attribution WAS
        appended (the old test name was test_wrapper_attribution_appended_in_source_commit).
        """
        attribution = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        source_dir, task_rel, index_rel = self._setup_wrapper(
            "bugfix/ABC-123", attribution=attribution
        )
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file=task_rel,
            index=index_rel,
            number="001",
            title="Define types",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        msg = _git_last_message(source_dir)
        # D5: the source repo commit must carry NO Co-Authored-By / no AI trace,
        # regardless of the COMMIT_ATTRIBUTION config value.
        self.assertNotIn("Co-Authored-By", msg,
                         "Source WIP commit must not contain Co-Authored-By (D5 traceless)")
        self.assertNotIn("Co-Author", msg,
                         "Source WIP commit must not contain any Co-Author trailer (D5)")
        # The subject line itself must be intact.
        self.assertIn("[ABC-123] - Define types (Task 001)", msg)

    def test_wrapper_source_commit_traceless_real_git_fixture(self):
        """Phase 6 D5: real two-repo git fixture — wrapper source commit has NO attribution.

        Verifies the exact format:  '[TICKET-ID] - <title> (Task NNN)' with nothing
        after it, even when COMMIT_ATTRIBUTION is a non-empty string.
        """
        attribution = "\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>"
        source_dir, task_rel, index_rel = self._setup_wrapper(
            "spec/FEAT-99-add-widget", attribution=attribution
        )
        src_file = self._stage_source_file(source_dir, "src/feature.ts")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file=task_rel,
            index=index_rel,
            number="003",
            title="Add widget",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        msg = _git_last_message(source_dir)
        # Exact format: subject only, no trailer.
        expected = "[FEAT-99] - Add widget (Task 003)"
        self.assertEqual(msg, expected,
                         "Source WIP commit message must be exactly the traceless "
                         "subject line; got: {0!r}".format(msg))

    def test_wrapper_source_branch_without_ticket_uses_full_branch(self):
        """Wrapper mode: source branch without Jira token → full branch name as TICKET-ID."""
        source_dir, task_rel, index_rel = self._setup_wrapper("feature/no-ticket-here")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file=task_rel,
            index=index_rel,
            number="001",
            title="Define types",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        msg = _git_last_message(source_dir)
        # "feature/no-ticket-here" has no [A-Z]+-[0-9]+ match → full branch used.
        self.assertIn("[feature/no-ticket-here]", msg)

    def test_standalone_unchanged_stages_source_plus_task_file_plus_index(self):
        """Standalone: source files + task_file + index all committed together.

        This is the existing behavior and must remain unchanged.
        The standalone repo is the single repo (install_root == source_root).
        """
        # Use a standard standalone fixture (no PROJECT_ROOT).
        standalone_tmpdir = tempfile.mkdtemp()
        try:
            standalone_root, _ = _init_git_repo(standalone_tmpdir)
            _write_project_config(standalone_root, workspace_mode="standalone")
            _write_wip_md(standalone_root)
            _checkout_branch(standalone_root, "feature/FEAT-1-widget")

            # Create source + task + index files.
            (standalone_root / "src").mkdir(exist_ok=True)
            src_file = standalone_root / "src" / "widget.py"
            src_file.write_text("class Widget: pass\n")
            env = _git_env()
            subprocess.run(
                ["git", "add", "--", str(src_file)],
                cwd=str(standalone_root), capture_output=True, env=env, check=True,
            )

            tasks_dir = standalone_root / "tasks"
            tasks_dir.mkdir(exist_ok=True)
            (tasks_dir / "001-define.md").write_text("# Task\n")
            (tasks_dir / "README.md").write_text("# Index\n")
            subprocess.run(
                ["git", "add", "--",
                 str(tasks_dir / "001-define.md"),
                 str(tasks_dir / "README.md")],
                cwd=str(standalone_root), capture_output=True, env=env, check=True,
            )

            args = _make_fake_args(
                files=json.dumps(["src/widget.py"]),
                task_file="tasks/001-define.md",
                index="tasks/README.md",
                number="001",
                title="Define types",
                root=str(standalone_root),
            )
            rc = cmd_wip_commit(args)
            self.assertEqual(rc, EXIT_OK)

            committed = _git_log_name_only(standalone_root)
            self.assertIn("src/widget.py", committed)
            self.assertIn("tasks/001-define.md", committed)
            self.assertIn("tasks/README.md", committed)
        finally:
            import shutil
            shutil.rmtree(standalone_tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Fix mode integration tests — standalone
# ---------------------------------------------------------------------------


class TestCmdWipCommitFixModeStandalone(unittest.TestCase):
    """Integration tests for cmd_wip_commit fix mode in a standalone repo.

    Fix mode: --files + --title present; --task-file, --index, --number all absent.
    Expected: stage only touched files, message "[WIP] fix: <title>", exit 0.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root, _ = _init_git_repo(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _stage_file(self, relpath, content="# fix\n"):
        full = self.root / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        env = _git_env()
        subprocess.run(
            ["git", "add", "--", str(full)],
            cwd=str(self.root), capture_output=True, env=env, check=True,
        )
        return relpath

    def test_fix_mode_standalone_message_format(self):
        """Standalone fix mode: message is '[WIP] fix: <title>'."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)
        self._stage_file("src/a.py")

        args = _make_fake_args(
            files=json.dumps(["src/a.py"]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(self.root)
        self.assertEqual(msg, "[WIP] fix: null guard")

    def test_fix_mode_standalone_no_task_suffix_in_message(self):
        """Fix mode message must not contain '(Task NNN)'."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)
        self._stage_file("src/a.py")
        self._stage_file("src/b.py")

        args = _make_fake_args(
            files=json.dumps(["src/a.py", "src/b.py"]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(self.root)
        self.assertNotIn("Task", msg)
        self.assertNotIn("(", msg)

    def test_fix_mode_standalone_stages_only_touched_files(self):
        """Fix mode stages ONLY the files in --files (no task/index)."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)
        self._stage_file("src/a.py")
        self._stage_file("src/b.py")

        args = _make_fake_args(
            files=json.dumps(["src/a.py", "src/b.py"]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        committed = _git_log_name_only(self.root)
        self.assertIn("src/a.py", committed)
        self.assertIn("src/b.py", committed)
        # Confirm no task/ or index-like paths crept in.
        for cf in committed:
            self.assertNotIn("tasks", cf)
            self.assertNotIn("README", cf)

    def test_fix_mode_standalone_exit_ok_json_output(self):
        """Fix mode emits {committed: true, head_sha, message} JSON on stdout."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)
        self._stage_file("src/a.py")

        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            args = _make_fake_args(
                files=json.dumps(["src/a.py"]),
                task_file="",
                index="",
                number="",
                title="null guard",
                root=str(self.root),
            )
            rc = cmd_wip_commit(args)
        finally:
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

        self.assertEqual(rc, EXIT_OK)
        result = json.loads(output.strip())
        self.assertTrue(result["committed"])
        self.assertIsInstance(result["head_sha"], str)
        self.assertGreater(len(result["head_sha"]), 0)
        self.assertEqual(result["message"], "[WIP] fix: null guard")

    def test_fix_mode_standalone_wip_cleared(self):
        """Fix mode clears wip.md on success."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)
        wip_path = self.root / ".devforge" / "wip.md"
        self.assertTrue(wip_path.exists())
        self._stage_file("src/a.py")

        args = _make_fake_args(
            files=json.dumps(["src/a.py"]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(wip_path.exists(), "wip.md must be cleared after fix commit")

    def test_fix_mode_standalone_with_attribution(self):
        """Fix mode standalone: attribution IS appended (same rule as task mode)."""
        attr = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        _write_project_config(self.root, workspace_mode="standalone",
                              commit_attribution=attr)
        _write_wip_md(self.root)
        self._stage_file("src/a.py")

        args = _make_fake_args(
            files=json.dumps(["src/a.py"]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(self.root)
        expected = "[WIP] fix: null guard" + attr
        self.assertEqual(msg, expected)

    def test_fix_mode_standalone_unrelated_file_stays_uncommitted(self):
        """Fix mode: unrelated dirty file NOT swept into commit (safety)."""
        _write_project_config(self.root, workspace_mode="standalone")
        _write_wip_md(self.root)
        self._stage_file("src/a.py")

        # Dirty unrelated file — never in --files.
        dirty = self.root / "src" / "unrelated.py"
        dirty.write_text("# not part of this fix\n")

        args = _make_fake_args(
            files=json.dumps(["src/a.py"]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        committed = _git_log_name_only(self.root)
        for cf in committed:
            self.assertNotIn("unrelated", cf,
                             "Dirty unrelated file must not be in fix commit")

        status = _git_status_short(self.root)
        self.assertTrue(
            "unrelated.py" in status or "src/" in status,
            "Unrelated file must remain untracked after fix commit: {0!r}".format(status),
        )


# ---------------------------------------------------------------------------
# Fix mode integration tests — wrapper
# ---------------------------------------------------------------------------


class TestCmdWipCommitFixModeWrapper(unittest.TestCase):
    """Integration tests for cmd_wip_commit fix mode in wrapper layout.

    Fix mode wrapper: stage ONLY source touched_files in the SOURCE repo;
    message "[TICKET-ID] - <title>" with no "(Task NNN)" suffix;
    attribution suppressed (D5 traceless).
    """

    def setUp(self):
        self.install_tmpdir = tempfile.mkdtemp()
        self.install_root = Path(self.install_tmpdir)
        self.source_name = "src-repo"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.install_tmpdir, ignore_errors=True)

    def _setup_wrapper_fix(self, source_branch="bugfix/ABC-123", attribution=""):
        """Set up wrapper fixture for fix mode (no task file / index needed)."""
        source_dir = _init_source_repo(
            self.install_root, self.source_name, source_branch
        )
        _write_project_config(
            self.install_root,
            workspace_mode="wrapper",
            commit_attribution=attribution,
            project_root=self.source_name,
        )
        _write_wip_md(self.install_root)
        return source_dir

    def _stage_source_file(self, source_dir, relpath, content="// fix\n"):
        full = source_dir / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        env = _git_env()
        subprocess.run(
            ["git", "add", "--", str(full)],
            cwd=str(source_dir), capture_output=True, env=env, check=True,
        )
        return relpath

    def test_fix_mode_wrapper_message_format(self):
        """Wrapper fix mode: message is '[TICKET-ID] - <title>' (no Task suffix)."""
        source_dir = self._setup_wrapper_fix("bugfix/ABC-456")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(source_dir)
        self.assertEqual(msg, "[ABC-456] - null guard")

    def test_fix_mode_wrapper_no_task_suffix(self):
        """Wrapper fix mode: message must NOT contain '(Task NNN)'."""
        source_dir = self._setup_wrapper_fix("bugfix/ABC-456")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(source_dir)
        self.assertNotIn("Task", msg)

    def test_fix_mode_wrapper_stages_only_source_files(self):
        """Wrapper fix mode: only source touched_files are in the source repo commit."""
        source_dir = self._setup_wrapper_fix("bugfix/ABC-456")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)

        committed = _git_log_name_only(source_dir)
        self.assertIn(src_file, committed)
        for cf in committed:
            self.assertNotIn("tasks", cf)
            self.assertNotIn("specs", cf)

    def test_fix_mode_wrapper_commit_lands_in_source_repo(self):
        """Wrapper fix mode: commit lands in the SOURCE repo, not install root."""
        source_dir = self._setup_wrapper_fix("bugfix/ABC-456")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            args = _make_fake_args(
                files=json.dumps([src_file]),
                task_file="",
                index="",
                number="",
                title="null guard",
                root=str(self.install_root),
            )
            rc = cmd_wip_commit(args)
        finally:
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

        self.assertEqual(rc, EXIT_OK)
        result = json.loads(output.strip())
        # head_sha must match the source repo's HEAD.
        actual_source_sha = _git_head_sha(source_dir)
        self.assertEqual(result["head_sha"], actual_source_sha)

    def test_fix_mode_wrapper_no_attribution_d5(self):
        """Wrapper fix mode: D5 — source commit carries NO Co-Authored-By even when configured."""
        attr = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        source_dir = self._setup_wrapper_fix("bugfix/ABC-456", attribution=attr)
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(source_dir)
        self.assertNotIn("Co-Authored-By", msg,
                         "Wrapper fix commit must be traceless (D5)")
        self.assertNotIn("Co-Author", msg)
        # Subject must be exact.
        self.assertEqual(msg, "[ABC-456] - null guard")

    def test_fix_mode_wrapper_wip_cleared_in_install_root(self):
        """Wrapper fix mode: wip.md in the INSTALL root is cleared."""
        source_dir = self._setup_wrapper_fix("bugfix/ABC-456")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        wip_path = self.install_root / ".devforge" / "wip.md"
        self.assertTrue(wip_path.exists())

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(wip_path.exists(), "wip.md must be cleared after wrapper fix commit")

    def test_fix_mode_wrapper_ticket_from_source_branch(self):
        """Wrapper fix mode: ticket-id extracted from SOURCE repo branch."""
        source_dir = self._setup_wrapper_fix("feature/FEAT-99-add-thing")
        src_file = self._stage_source_file(source_dir, "src/widget.ts")

        args = _make_fake_args(
            files=json.dumps([src_file]),
            task_file="",
            index="",
            number="",
            title="null guard",
            root=str(self.install_root),
        )
        rc = cmd_wip_commit(args)
        self.assertEqual(rc, EXIT_OK)
        msg = _git_last_message(source_dir)
        self.assertEqual(msg, "[FEAT-99] - null guard")


# ---------------------------------------------------------------------------
# Mixed mode tests — some but not all of --task-file/--index/--number given
# ---------------------------------------------------------------------------


class TestCmdWipCommitMixedMode(unittest.TestCase):
    """Tests that mixed-mode invocations are rejected with EXIT_ERR."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root, _ = _init_git_repo(self.tmpdir)
        _write_project_config(self.root, workspace_mode="standalone")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_mixed(self, **kwargs):
        """Run cmd_wip_commit and capture stderr; return (rc, stderr_text)."""
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            args = _make_fake_args(**kwargs, root=str(self.root))
            rc = cmd_wip_commit(args)
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr
        return rc, err

    def test_task_file_only_is_mixed(self):
        """--task-file alone (no --index, no --number) → EXIT_ERR mixed-mode."""
        rc, err = self._run_mixed(
            files=json.dumps([]),
            task_file="tasks/001.md",
            index="",
            number="",
            title="Do thing",
        )
        self.assertEqual(rc, EXIT_ERR)
        self.assertIn("mixed mode", err)
        self.assertIn("--index", err)
        self.assertIn("--number", err)

    def test_index_only_is_mixed(self):
        """--index alone → EXIT_ERR mixed-mode."""
        rc, err = self._run_mixed(
            files=json.dumps([]),
            task_file="",
            index="tasks/README.md",
            number="",
            title="Do thing",
        )
        self.assertEqual(rc, EXIT_ERR)
        self.assertIn("mixed mode", err)
        self.assertIn("--task-file", err)
        self.assertIn("--number", err)

    def test_number_only_is_mixed(self):
        """--number alone → EXIT_ERR mixed-mode."""
        rc, err = self._run_mixed(
            files=json.dumps([]),
            task_file="",
            index="",
            number="001",
            title="Do thing",
        )
        self.assertEqual(rc, EXIT_ERR)
        self.assertIn("mixed mode", err)
        self.assertIn("--task-file", err)
        self.assertIn("--index", err)

    def test_task_file_and_index_missing_number(self):
        """--task-file + --index but no --number → EXIT_ERR mixed-mode."""
        rc, err = self._run_mixed(
            files=json.dumps([]),
            task_file="tasks/001.md",
            index="tasks/README.md",
            number="",
            title="Do thing",
        )
        self.assertEqual(rc, EXIT_ERR)
        self.assertIn("mixed mode", err)
        self.assertIn("--number", err)

    def test_task_file_and_number_missing_index(self):
        """--task-file + --number but no --index → EXIT_ERR mixed-mode."""
        rc, err = self._run_mixed(
            files=json.dumps([]),
            task_file="tasks/001.md",
            index="",
            number="001",
            title="Do thing",
        )
        self.assertEqual(rc, EXIT_ERR)
        self.assertIn("mixed mode", err)
        self.assertIn("--index", err)

    def test_index_and_number_missing_task_file(self):
        """--index + --number but no --task-file → EXIT_ERR mixed-mode."""
        rc, err = self._run_mixed(
            files=json.dumps([]),
            task_file="",
            index="tasks/README.md",
            number="001",
            title="Do thing",
        )
        self.assertEqual(rc, EXIT_ERR)
        self.assertIn("mixed mode", err)
        self.assertIn("--task-file", err)


if __name__ == "__main__":
    unittest.main()
