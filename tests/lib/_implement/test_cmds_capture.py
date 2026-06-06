"""Tests for src/devforge/lib/_implement/_cmds_capture.py.

Coverage:

  _validate_sha:
    - Valid full 40-char SHA → True.
    - Valid abbreviated 7-char SHA → True.
    - Valid 4-char minimum SHA → True.
    - Empty string → False.
    - Non-hex chars → False.
    - Too short (3 chars) → False.
    - Too long (41 chars) → False.

  _git_diff_files (real git tempdir):
    - Returns empty list when no changes since checkpoint.
    - Returns modified tracked file after edit.
    - Does NOT return untracked files (those come from _git_untracked_files).
    - Raises RuntimeError for an invalid SHA.

  _git_untracked_files (real git tempdir):
    - Returns empty list when no untracked files.
    - Returns newly created file that was never staged.
    - Does NOT return tracked files (they appear in diff, not status ??).

  cmd_capture_touched_files (integration, real git tempdir):
    - Happy path: checkpoint sha, modify a tracked file + add an untracked file
      → both appear in the JSON output list.
    - Checkpoint only captures diff-and-new; unchanged tracked files absent.
    - Empty change (nothing modified since checkpoint) → empty list.
    - Modified and then staged file still appears (git diff catches staged changes).
    - --checkpoint with invalid SHA → exit 2, stderr message.
    - Missing --root is interpreted as cwd (no error in a git repo).
    - Output is valid JSON array.
    - Paths are relative to repo root (no leading slash).
    - De-duplication: a file appearing in both diff and (somehow) status is not repeated.

Design notes:
- Tests create a real temporary git repository using subprocess git commands
  (git init, git config, git add, git commit) so round-trip is through the
  real binary, matching the production path.
- Each test creates its own tempdir to avoid cross-test contamination.
- The sys.path manipulation at module load allows importing _implement directly
  from the test runner's working directory.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap: make _implement importable.
# ---------------------------------------------------------------------------
_LIB_DIR = str(Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _implement._cmds_capture import (  # noqa: E402
    _validate_sha,
    _git_diff_files,
    _git_untracked_files,
    cmd_capture_touched_files,
    EXIT_OK,
    EXIT_ERR,
    EXIT_USAGE,
)


# ---------------------------------------------------------------------------
# Git tempdir helper
# ---------------------------------------------------------------------------


def _init_git_repo(tmpdir):
    """Initialise a git repo in tmpdir with a single root commit.

    Returns the SHA of the initial commit (suitable as a checkpoint).
    """
    cwd = str(tmpdir)

    def run(*cmd):
        result = subprocess.run(
            list(cmd),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "git command failed: {0}\nstdout: {1}\nstderr: {2}".format(
                    " ".join(cmd), result.stdout, result.stderr
                )
            )
        return result.stdout.strip()

    run("git", "init", "-b", "feature-branch")
    run("git", "config", "user.email", "test@example.com")
    run("git", "config", "user.name", "Test User")
    # Create an initial file and commit it.
    seed_file = os.path.join(cwd, "seed.txt")
    with open(seed_file, "w") as f:
        f.write("initial content\n")
    run("git", "add", "seed.txt")
    run("git", "commit", "-m", "initial commit")
    # Return the current HEAD sha.
    sha = run("git", "rev-parse", "HEAD")
    return sha


def _write_file(tmpdir, relpath, content="modified content\n"):
    """Write content to a file in tmpdir, creating parent dirs as needed."""
    full = os.path.join(str(tmpdir), relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)
    return full


def _git_add(tmpdir, relpath):
    subprocess.run(
        ["git", "add", relpath],
        cwd=str(tmpdir),
        check=True,
        capture_output=True,
    )


def _git_commit(tmpdir, message="wip commit"):
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(tmpdir),
        check=True,
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# _validate_sha
# ---------------------------------------------------------------------------


class TestValidateSha(unittest.TestCase):

    def test_valid_full_sha(self):
        self.assertTrue(
            _validate_sha("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2")
        )

    def test_valid_abbreviated_7(self):
        self.assertTrue(_validate_sha("a1b2c3d"))

    def test_valid_minimum_4(self):
        self.assertTrue(_validate_sha("dead"))

    def test_empty_string(self):
        self.assertFalse(_validate_sha(""))

    def test_non_hex_chars(self):
        self.assertFalse(_validate_sha("ghijklm"))

    def test_too_short_3(self):
        self.assertFalse(_validate_sha("abc"))

    def test_too_long_41(self):
        # 41 chars → False (max 40)
        self.assertFalse(_validate_sha("a" * 41))

    def test_uppercase_hex_valid(self):
        self.assertTrue(_validate_sha("ABCDEF1234"))

    def test_mixed_case_valid(self):
        self.assertTrue(_validate_sha("aBcDeF0123"))


# ---------------------------------------------------------------------------
# _git_diff_files
# ---------------------------------------------------------------------------


class TestGitDiffFiles(unittest.TestCase):

    def _make_repo(self):
        d = tempfile.mkdtemp()
        sha = _init_git_repo(d)
        return d, sha

    def test_no_changes_returns_empty(self):
        tmpdir, sha = self._make_repo()
        result = _git_diff_files(sha, tmpdir)
        self.assertEqual(result, [])

    def test_modified_tracked_file_appears(self):
        tmpdir, sha = self._make_repo()
        # Modify the tracked seed.txt.
        _write_file(tmpdir, "seed.txt", "changed\n")
        result = _git_diff_files(sha, tmpdir)
        self.assertIn("seed.txt", result)

    def test_untracked_file_not_in_diff(self):
        tmpdir, sha = self._make_repo()
        # Create a new untracked file (never git add'd).
        _write_file(tmpdir, "new_untracked.txt", "new\n")
        result = _git_diff_files(sha, tmpdir)
        self.assertNotIn("new_untracked.txt", result)

    def test_staged_file_appears_in_diff(self):
        tmpdir, sha = self._make_repo()
        # Write and stage a new file (staged but not committed).
        _write_file(tmpdir, "staged.txt", "staged\n")
        _git_add(tmpdir, "staged.txt")
        result = _git_diff_files(sha, tmpdir)
        self.assertIn("staged.txt", result)

    def test_invalid_sha_raises_runtime_error(self):
        tmpdir, _ = self._make_repo()
        with self.assertRaises(RuntimeError):
            _git_diff_files("deadbeefdeadbeef", tmpdir)

    def test_committed_since_checkpoint_appears(self):
        tmpdir, sha = self._make_repo()
        # Commit a new file AFTER the checkpoint.
        _write_file(tmpdir, "post_commit.txt", "after checkpoint\n")
        _git_add(tmpdir, "post_commit.txt")
        _git_commit(tmpdir, "post checkpoint commit")
        result = _git_diff_files(sha, tmpdir)
        self.assertIn("post_commit.txt", result)


# ---------------------------------------------------------------------------
# _git_untracked_files
# ---------------------------------------------------------------------------


class TestGitUntrackedFiles(unittest.TestCase):

    def _make_repo(self):
        d = tempfile.mkdtemp()
        sha = _init_git_repo(d)
        return d, sha

    def test_no_untracked_returns_empty(self):
        tmpdir, _ = self._make_repo()
        result = _git_untracked_files(tmpdir)
        self.assertEqual(result, [])

    def test_new_untracked_file_appears(self):
        tmpdir, _ = self._make_repo()
        _write_file(tmpdir, "brand_new.txt", "brand new\n")
        result = _git_untracked_files(tmpdir)
        self.assertIn("brand_new.txt", result)

    def test_tracked_file_not_in_untracked(self):
        tmpdir, _ = self._make_repo()
        # Modify existing tracked file; it should NOT appear in untracked.
        _write_file(tmpdir, "seed.txt", "modified\n")
        result = _git_untracked_files(tmpdir)
        self.assertNotIn("seed.txt", result)

    def test_staged_new_file_not_in_untracked(self):
        tmpdir, _ = self._make_repo()
        # Stage a new file → it moves out of '??' and into 'A '.
        _write_file(tmpdir, "staged_new.txt", "staged\n")
        _git_add(tmpdir, "staged_new.txt")
        result = _git_untracked_files(tmpdir)
        self.assertNotIn("staged_new.txt", result)

    def test_multiple_untracked_files(self):
        tmpdir, _ = self._make_repo()
        _write_file(tmpdir, "alpha.txt")
        _write_file(tmpdir, "beta.txt")
        result = _git_untracked_files(tmpdir)
        self.assertIn("alpha.txt", result)
        self.assertIn("beta.txt", result)

    def test_untracked_file_with_space_in_name_no_quote_chars(self):
        """git --porcelain quotes paths with spaces; _git_untracked_files must strip the quotes.

        git status --porcelain emits '?? "my file.ts"' (with literal double-quote
        chars) for files whose names contain spaces.  The returned path must be
        'my file.ts' — no surrounding quote characters — so it prefix-matches its
        package correctly in verify-touched.
        """
        tmpdir, _ = self._make_repo()
        spaced_name = "my file.ts"
        _write_file(tmpdir, spaced_name, "export {};\n")
        result = _git_untracked_files(tmpdir)
        self.assertIn(spaced_name, result, msg="Path with space must appear (no quote wrapping)")
        # None of the returned paths should start/end with a literal double-quote char.
        for path in result:
            self.assertFalse(
                path.startswith('"') or path.endswith('"'),
                msg="Path must not retain surrounding quote chars: {0!r}".format(path),
            )


# ---------------------------------------------------------------------------
# cmd_capture_touched_files (integration)
# ---------------------------------------------------------------------------


class FakeArgs:
    """Minimal args namespace for cmd_capture_touched_files."""
    def __init__(self, checkpoint, root=None):
        self.checkpoint = checkpoint
        self.root = root


class TestCmdCaptureTouchedFiles(unittest.TestCase):

    def _make_repo(self):
        d = tempfile.mkdtemp()
        sha = _init_git_repo(d)
        return d, sha

    def _capture(self, checkpoint, root=None):
        """Run cmd_capture_touched_files; return (exit_code, parsed_output)."""
        import io
        from unittest.mock import patch

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = cmd_capture_touched_files(FakeArgs(checkpoint=checkpoint, root=root))
        output = buf.getvalue()
        if output.strip():
            return rc, json.loads(output)
        return rc, None

    def test_happy_path_modified_and_untracked(self):
        """Modified tracked file + new untracked file both appear."""
        tmpdir, sha = self._make_repo()

        # Modify the tracked seed.txt.
        _write_file(tmpdir, "seed.txt", "modified\n")
        # Create a new untracked file.
        _write_file(tmpdir, "new_feature.py", "print('hello')\n")

        rc, result = self._capture(checkpoint=sha, root=tmpdir)
        self.assertEqual(rc, EXIT_OK)
        self.assertIsInstance(result, list)
        self.assertIn("seed.txt", result)
        self.assertIn("new_feature.py", result)

    def test_no_changes_empty_list(self):
        """Nothing modified since checkpoint → empty list."""
        tmpdir, sha = self._make_repo()
        rc, result = self._capture(checkpoint=sha, root=tmpdir)
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(result, [])

    def test_unchanged_file_not_in_result(self):
        """seed.txt not modified → not in result."""
        tmpdir, sha = self._make_repo()
        # Only add a new untracked file; don't touch seed.txt.
        _write_file(tmpdir, "extra.ts", "export {};\n")
        rc, result = self._capture(checkpoint=sha, root=tmpdir)
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("extra.ts", result)
        self.assertNotIn("seed.txt", result)

    def test_staged_file_captured(self):
        """Staged new file appears in output (via git diff)."""
        tmpdir, sha = self._make_repo()
        _write_file(tmpdir, "staged.ts", "const x = 1;\n")
        _git_add(tmpdir, "staged.ts")
        rc, result = self._capture(checkpoint=sha, root=tmpdir)
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("staged.ts", result)

    def test_invalid_sha_exits_2(self):
        """Invalid SHA → exit 2 (usage error)."""
        tmpdir, _ = self._make_repo()
        import io
        from unittest.mock import patch

        err_buf = io.StringIO()
        with patch("sys.stderr", err_buf):
            rc = cmd_capture_touched_files(FakeArgs(checkpoint="INVALID!", root=tmpdir))
        self.assertEqual(rc, EXIT_USAGE)
        self.assertIn("checkpoint", err_buf.getvalue().lower())

    def test_output_is_valid_json_array(self):
        """Emitted output is always a valid JSON array."""
        tmpdir, sha = self._make_repo()
        import io
        from unittest.mock import patch

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = cmd_capture_touched_files(FakeArgs(checkpoint=sha, root=tmpdir))
        self.assertEqual(rc, EXIT_OK)
        parsed = json.loads(buf.getvalue())
        self.assertIsInstance(parsed, list)

    def test_paths_are_relative_no_leading_slash(self):
        """Emitted paths must be relative (no leading '/')."""
        tmpdir, sha = self._make_repo()
        _write_file(tmpdir, "src/lib/foo.ts", "export const x = 1;\n")
        _git_add(tmpdir, "src/lib/foo.ts")
        rc, result = self._capture(checkpoint=sha, root=tmpdir)
        self.assertEqual(rc, EXIT_OK)
        for path in result:
            self.assertFalse(
                path.startswith("/"),
                msg="Path should be relative, got: {0}".format(path),
            )

    def test_nested_path_included(self):
        """Files in subdirectories are correctly captured."""
        tmpdir, sha = self._make_repo()
        _write_file(tmpdir, "services/api/handler.py", "def handle(): pass\n")
        _git_add(tmpdir, "services/api/handler.py")
        rc, result = self._capture(checkpoint=sha, root=tmpdir)
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("services/api/handler.py", result)

    def test_deduplication_no_repeats(self):
        """Same file does not appear twice in the result."""
        tmpdir, sha = self._make_repo()
        # Modify a file AND stage it (it would appear in diff both times if not de-duped).
        _write_file(tmpdir, "seed.txt", "changed\n")
        _git_add(tmpdir, "seed.txt")
        rc, result = self._capture(checkpoint=sha, root=tmpdir)
        self.assertEqual(rc, EXIT_OK)
        # No duplicates.
        self.assertEqual(len(result), len(set(result)))

    def test_empty_checkpoint_sha_exits_2(self):
        """Empty string checkpoint → exit 2."""
        tmpdir, _ = self._make_repo()
        import io
        from unittest.mock import patch

        err_buf = io.StringIO()
        with patch("sys.stderr", err_buf):
            rc = cmd_capture_touched_files(FakeArgs(checkpoint="", root=tmpdir))
        self.assertEqual(rc, EXIT_USAGE)

    def test_committed_after_checkpoint_appears(self):
        """Files committed AFTER the checkpoint appear (git diff walks history)."""
        tmpdir, sha = self._make_repo()
        _write_file(tmpdir, "committed_later.py", "x = 1\n")
        _git_add(tmpdir, "committed_later.py")
        _git_commit(tmpdir, "after checkpoint")
        rc, result = self._capture(checkpoint=sha, root=tmpdir)
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("committed_later.py", result)


# ---------------------------------------------------------------------------
# Shared wrapper-mode fixture helpers
# ---------------------------------------------------------------------------


def _init_wrapper_install(install_dir, source_repo_name="src-repo"):
    # type: (str, str) -> str
    """Create a wrapper install structure.

    Creates:
      <install_dir>/.devforge/project-config.json  (PROJECT_ROOT = source_repo_name)
      <install_dir>/<source_repo_name>/             (a real git repo with one commit)

    Returns the SHA of the source repo's initial commit (suitable as a checkpoint).
    """
    # Write .devforge/project-config.json.
    devforge = os.path.join(install_dir, ".devforge")
    os.makedirs(devforge, exist_ok=True)
    config_path = os.path.join(devforge, "project-config.json")
    import json as _json
    with open(config_path, "w") as fh:
        _json.dump({"PROJECT_ROOT": source_repo_name}, fh)

    # Create the nested source git repo.
    source_dir = os.path.join(install_dir, source_repo_name)
    os.makedirs(source_dir, exist_ok=True)
    sha = _init_git_repo(source_dir)
    return sha


# ---------------------------------------------------------------------------
# Wrapper-mode tests: cmd_capture_touched_files
# ---------------------------------------------------------------------------


class TestCmdCaptureTouchedFilesWrapper(unittest.TestCase):
    """Wrapper-mode: git ops target the source repo, not the install root."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.install_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _capture(self, checkpoint, root=None):
        """Run cmd_capture_touched_files; return (exit_code, parsed_output)."""
        import io
        from unittest.mock import patch

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = cmd_capture_touched_files(FakeArgs(checkpoint=checkpoint, root=root))
        output = buf.getvalue()
        if output.strip():
            return rc, json.loads(output)
        return rc, None

    def test_wrapper_returns_only_source_relative_paths(self):
        """Changed source file + dirty install root → only source-relative path returned.

        This is the exact bug from the live testForge20 run:
        - Source file changed in the nested repo.
        - Install root has unrelated dirty files (forge churn).
        - capture must return ONLY the source-relative path, NOT install churn
          and NOT the nested dir as a single entry.

        We stage the source change (so it appears via git diff rather than
        git status --porcelain as a directory entry) to get an exact file path
        in the output regardless of whether git reports the file or its parent
        directory as untracked.
        """
        sha = _init_wrapper_install(self.install_dir, "src-repo")

        # Dirty the install root (forge churn — should NOT appear in output).
        _write_file(self.install_dir, "specs/001-widget/task.md", "dirty forge file\n")
        _write_file(self.install_dir, ".devforge/session-state.md", "session state\n")

        # Change a file in the source repo (this IS the task's work).
        # Stage it so git diff sees it as an exact file path (not a directory entry).
        source_dir = os.path.join(self.install_dir, "src-repo")
        _write_file(source_dir, "src/widget.ts", "export const x = 1;\n")
        _git_add(source_dir, "src/widget.ts")

        rc, result = self._capture(checkpoint=sha, root=self.install_dir)
        self.assertEqual(rc, EXIT_OK)
        self.assertIsInstance(result, list)

        # The source-relative path must appear.
        self.assertIn("src/widget.ts", result,
                      "Source-relative path must be captured")

        # Install-root paths and the source dir entry must NOT appear.
        for p in result:
            self.assertFalse(
                p.startswith("specs/"),
                "Install-root forge files must not appear: {0}".format(p),
            )
            self.assertFalse(
                p.startswith(".devforge/"),
                "Install-root .devforge files must not appear: {0}".format(p),
            )
            self.assertFalse(
                p == "src-repo" or p == "src-repo/",
                "Nested source dir must not appear as a single entry: {0}".format(p),
            )

    def test_wrapper_untracked_source_file_captured(self):
        """Untracked file in the source repo is captured (source-relative)."""
        sha = _init_wrapper_install(self.install_dir, "src-repo")
        source_dir = os.path.join(self.install_dir, "src-repo")

        # Untracked new file in source repo.
        _write_file(source_dir, "new_component.tsx", "export default () => null;\n")

        rc, result = self._capture(checkpoint=sha, root=self.install_dir)
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("new_component.tsx", result)

    def test_wrapper_no_source_change_empty_list(self):
        """No source repo changes → empty list, even if install root is dirty."""
        sha = _init_wrapper_install(self.install_dir, "src-repo")

        # Dirty the install root only.
        _write_file(self.install_dir, "specs/001/notes.md", "notes\n")

        rc, result = self._capture(checkpoint=sha, root=self.install_dir)
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(result, [])

    def test_wrapper_install_root_equals_source_root_standalone(self):
        """Standalone (PROJECT_ROOT=".") behaves identically to before: sees install-root changes."""
        # Write standalone config.
        devforge = os.path.join(self.install_dir, ".devforge")
        os.makedirs(devforge, exist_ok=True)
        config_path = os.path.join(devforge, "project-config.json")
        with open(config_path, "w") as fh:
            json.dump({"PROJECT_ROOT": "."}, fh)

        # Init a real git repo AT the install dir itself.
        sha = _init_git_repo(self.install_dir)

        # Modify a file in the install/source repo.
        _write_file(self.install_dir, "seed.txt", "changed for standalone\n")

        rc, result = self._capture(checkpoint=sha, root=self.install_dir)
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("seed.txt", result)

    def test_wrapper_invalid_sha_still_exits_2(self):
        """SHA validation runs before workspace resolution; invalid SHA → exit 2."""
        _init_wrapper_install(self.install_dir, "src-repo")
        import io
        from unittest.mock import patch

        errbuf = io.StringIO()
        with patch("sys.stderr", errbuf):
            rc = cmd_capture_touched_files(FakeArgs(checkpoint="BAD!", root=self.install_dir))
        self.assertEqual(rc, EXIT_USAGE)

    def test_wrapper_source_committed_after_checkpoint(self):
        """Files committed in the source repo after checkpoint appear (git diff walks history)."""
        sha = _init_wrapper_install(self.install_dir, "src-repo")
        source_dir = os.path.join(self.install_dir, "src-repo")

        # Commit a new file to the source repo after the checkpoint.
        _write_file(source_dir, "services/api.ts", "export {};\n")
        _git_add(source_dir, "services/api.ts")
        _git_commit(source_dir, "post-checkpoint source change")

        rc, result = self._capture(checkpoint=sha, root=self.install_dir)
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("services/api.ts", result)

    def test_wrapper_paths_are_source_relative_no_leading_slash(self):
        """Emitted paths are source-relative (no leading '/', no 'src-repo/' prefix)."""
        sha = _init_wrapper_install(self.install_dir, "src-repo")
        source_dir = os.path.join(self.install_dir, "src-repo")
        _write_file(source_dir, "lib/util.py", "def f(): pass\n")
        _git_add(source_dir, "lib/util.py")

        rc, result = self._capture(checkpoint=sha, root=self.install_dir)
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("lib/util.py", result)
        for p in result:
            self.assertFalse(p.startswith("/"))
            # The source_repo_name prefix must NOT appear.
            self.assertFalse(p.startswith("src-repo"))

    def test_wrapper_missing_source_root_exits_1_with_clear_message(self):
        """FIX 1: wrapper config with non-existent source_root → clear error, not 'git not found'.

        When PROJECT_ROOT points at a directory that has not been cloned,
        subprocess.run(cwd=<missing>) raises FileNotFoundError.  The old
        handler reported 'git not found on PATH', misdirecting the user.
        The fixed handler detects the missing directory before the subprocess
        call and emits a message naming the path + pointing at PROJECT_ROOT.
        """
        # Write a wrapper config pointing at a source dir that does NOT exist.
        devforge = os.path.join(self.install_dir, ".devforge")
        os.makedirs(devforge, exist_ok=True)
        config_path = os.path.join(devforge, "project-config.json")
        import json as _json
        with open(config_path, "w") as fh:
            _json.dump({"PROJECT_ROOT": "no-such-repo"}, fh)
        # Do NOT create the "no-such-repo" directory.

        import io
        from unittest.mock import patch

        sha = "abcd1234"  # valid SHA format; SHA validation passes first
        errbuf = io.StringIO()
        with patch("sys.stderr", errbuf):
            rc = cmd_capture_touched_files(FakeArgs(checkpoint=sha, root=self.install_dir))

        self.assertEqual(rc, EXIT_ERR,
                         "missing source root must exit EXIT_ERR (1), got {0}".format(rc))
        err_msg = errbuf.getvalue()
        # Must NOT say "git not found" — that misdirects to PATH debugging.
        self.assertNotIn("git not found", err_msg,
                         "error must not claim git is missing from PATH: {0!r}".format(err_msg))
        # Must mention the missing path.
        self.assertIn("source root does not exist", err_msg,
                      "error must name the problem clearly: {0!r}".format(err_msg))
        # Must reference project-config.json so the user knows where to fix it.
        self.assertIn("project-config.json", err_msg,
                      "error must reference project-config.json: {0!r}".format(err_msg))

    def test_wrapper_untracked_new_subdir_captured_as_dir_entry(self):
        """FIX 2: git status --porcelain returns 'src/' (dir entry) for a wholly-new untracked subdir.

        When the agent creates a brand-new subdirectory with files but never
        stages them, git --porcelain reports the directory as '?? src/' (a
        directory entry, not individual file paths).  After rstrip('/') this
        becomes 'src'.  This test locks the known behavior against regression.
        """
        sha = _init_wrapper_install(self.install_dir, "src-repo")
        source_dir = os.path.join(self.install_dir, "src-repo")
        os.makedirs(os.path.join(source_dir, "src", "newpkg"))
        _write_file(source_dir, "src/newpkg/index.ts", "export {};\n")

        rc, result = self._capture(checkpoint=sha, root=self.install_dir)
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("src", result,
                      "directory entry 'src' must appear in captured paths")
        # Paths must NOT be prefixed with the source repo name.
        for p in result:
            self.assertFalse(
                p.startswith("src-repo"),
                "captured path must not have src-repo prefix: {0!r}".format(p),
            )


if __name__ == "__main__":
    unittest.main()
