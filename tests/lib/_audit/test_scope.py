"""Tests for src/devforge/lib/_audit/_scope.py.

Coverage:
  _parse_ls_files_stdout — empty, single, multi-file, blank lines, whitespace,
                           no trailing newline, submodule-prefixed paths
  _git_ls_files_dir — nonempty plain result (no nested attempt), nested-repo
                      resolution via real git topology (independent nested repo,
                      deeper subdir, workspace-relative prefix), genuinely empty
                      dir (no nested .git) → [], None semantics preserved
                      (plain git-absent or non-zero exit → None), nested git -C
                      fails gracefully → [] (not None, no crash)
  resolve_scope — broad, hotspot, file (simplified pipeline), directory via
                  git ls-files, directory non-git fallback, uncommitted,
                  scope_oversize boundary (==limit → False; ==limit+1 → True),
                  nonexistent scope_arg → error
  render_scope_block — standard rendering, error result, oversize warning,
                       >25 files, line_range
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_REFERENCES_DIR = _REPO_ROOT / "src" / "commands" / "audit" / "references"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit._scope import (  # noqa: E402
    _CLOSING_REMINDER,
    _FOCUS_BLOCKS,
    _OUTPUT_CONTRACT,
    _git_ls_files_dir,
    _parse_ls_files_stdout,
    render_agent_brief,
    render_scope_block,
    resolve_scope,
)
from _audit.findings_schema import CATEGORY_ENUM  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git_available():
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _mode_result(
    mode="narrow",
    scope_arg=None,
    uncommitted=False,
    top_n=None,
    scope_limit=200,
    line_range=None,
):
    return {
        "mode": mode,
        "scope_arg": scope_arg,
        "uncommitted": uncommitted,
        "top_n": top_n,
        "weights": None,
        "scope_limit": scope_limit,
        "line_range": line_range,
        "error": None,
    }


def _init_git_repo(dirpath):
    """Initialize a bare git repo and configure minimal user identity."""
    subprocess.run(["git", "init", dirpath], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", dirpath, "config", "user.email", "test@test.com"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", dirpath, "config", "user.name", "Test"],
        check=True, capture_output=True,
    )


def _git_add_commit(dirpath, files):
    """Stage and commit a list of filenames under dirpath."""
    subprocess.run(
        ["git", "-C", dirpath, "add"] + files,
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", dirpath, "commit", "-m", "init", "--allow-empty"],
        check=True, capture_output=True,
    )


# ---------------------------------------------------------------------------
# Tests — broad mode
# ---------------------------------------------------------------------------

@unittest.skipUnless(_git_available(), "git not available")
class TestResolveScopeBroad(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        _init_git_repo(self.tmpdir)
        # Create a few source files
        for name in ("a.py", "b.ts", "notes.md", "readme.txt"):
            p = os.path.join(self.tmpdir, name)
            with open(p, "w") as fh:
                fh.write("x\n")
        _git_add_commit(self.tmpdir, ["a.py", "b.ts", "notes.md", "readme.txt"])

    def test_broad_returns_source_files_only(self):
        mr = _mode_result(mode="broad")
        result = resolve_scope(mr, self.tmpdir)
        self.assertIsNone(result["error"])
        self.assertEqual(result["scope_kind"], "broad")
        self.assertEqual(result["pipeline"], "full")
        # enumerate_candidates filters by extension — .py and .ts are source
        # .md and .txt are NOT in _SOURCE_EXTS
        files = result["files"]
        self.assertIn("a.py", files)
        self.assertIn("b.ts", files)
        # notes.md / readme.txt not in _SOURCE_EXTS → excluded by enumerate_candidates
        self.assertNotIn("notes.md", files)
        self.assertNotIn("readme.txt", files)

    def test_broad_pipeline_is_full(self):
        mr = _mode_result(mode="broad")
        result = resolve_scope(mr, self.tmpdir)
        self.assertEqual(result["pipeline"], "full")

    def test_broad_no_oversize(self):
        """Broad mode never sets scope_oversize even if file count is large."""
        mr = _mode_result(mode="broad", scope_limit=1)
        result = resolve_scope(mr, self.tmpdir)
        self.assertFalse(result["scope_oversize"])

    def test_broad_files_sorted(self):
        mr = _mode_result(mode="broad")
        result = resolve_scope(mr, self.tmpdir)
        files = result["files"]
        self.assertEqual(files, sorted(files))


# ---------------------------------------------------------------------------
# Tests — hotspot mode
# ---------------------------------------------------------------------------

class TestResolveScopeHotspot(unittest.TestCase):
    def test_hotspot_uses_supplied_files(self):
        mr = _mode_result(mode="hotspot")
        hfiles = ["src/foo.py", "src/bar.ts"]
        result = resolve_scope(mr, "/any/root", hotspot_files=hfiles)
        self.assertIsNone(result["error"])
        self.assertEqual(result["scope_kind"], "hotspot")
        self.assertEqual(result["pipeline"], "full")
        self.assertEqual(result["files"], sorted(hfiles))

    def test_hotspot_none_gives_empty(self):
        mr = _mode_result(mode="hotspot")
        result = resolve_scope(mr, "/any/root", hotspot_files=None)
        self.assertEqual(result["files"], [])
        self.assertEqual(result["file_count"], 0)
        self.assertIsNone(result["error"])

    def test_hotspot_no_oversize(self):
        """Hotspot mode never sets scope_oversize."""
        mr = _mode_result(mode="hotspot", scope_limit=1)
        result = resolve_scope(mr, "/any/root", hotspot_files=["a.py", "b.py"])
        self.assertFalse(result["scope_oversize"])

    def test_hotspot_files_sorted(self):
        mr = _mode_result(mode="hotspot")
        result = resolve_scope(mr, "/any/root", hotspot_files=["z.py", "a.py"])
        self.assertEqual(result["files"], ["a.py", "z.py"])


# ---------------------------------------------------------------------------
# Tests — narrow / file mode
# ---------------------------------------------------------------------------

class TestResolveScopeFile(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.filepath = os.path.join(self.tmpdir, "main.py")
        with open(self.filepath, "w") as fh:
            fh.write("x = 1\n")

    def test_file_mode_simplified_pipeline(self):
        mr = _mode_result(mode="narrow", scope_arg=self.filepath)
        result = resolve_scope(mr, self.tmpdir)
        self.assertIsNone(result["error"])
        self.assertEqual(result["scope_kind"], "file")
        self.assertEqual(result["pipeline"], "simplified")

    def test_file_mode_single_file_in_list(self):
        mr = _mode_result(mode="narrow", scope_arg=self.filepath)
        result = resolve_scope(mr, self.tmpdir)
        self.assertEqual(result["file_count"], 1)
        # Path is relative to repo_root
        rel = os.path.relpath(self.filepath, self.tmpdir)
        self.assertIn(rel, result["files"])

    def test_file_no_oversize(self):
        """Single file never sets scope_oversize."""
        mr = _mode_result(mode="narrow", scope_arg=self.filepath, scope_limit=0)
        result = resolve_scope(mr, self.tmpdir)
        self.assertFalse(result["scope_oversize"])

    def test_line_range_preserved(self):
        mr = _mode_result(mode="narrow", scope_arg=self.filepath, line_range="1-20")
        result = resolve_scope(mr, self.tmpdir)
        self.assertEqual(result["line_range"], "1-20")

    def test_relative_scope_arg(self):
        """scope_arg can be relative (resolved against repo_root)."""
        mr = _mode_result(mode="narrow", scope_arg="main.py")
        result = resolve_scope(mr, self.tmpdir)
        self.assertIsNone(result["error"])
        self.assertEqual(result["scope_kind"], "file")


# ---------------------------------------------------------------------------
# Tests — narrow / directory mode (git ls-files)
# ---------------------------------------------------------------------------

@unittest.skipUnless(_git_available(), "git not available")
class TestResolveScopeDirectory(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        _init_git_repo(self.tmpdir)
        # Create src/ subdirectory with tracked polyglot files
        src = os.path.join(self.tmpdir, "src")
        os.makedirs(src)
        for name in ("a.ts", "b.sql", "c.md"):
            p = os.path.join(src, name)
            with open(p, "w") as fh:
                fh.write("content\n")
        # Create a .gitignore that excludes ignored.log
        gitignore = os.path.join(self.tmpdir, ".gitignore")
        with open(gitignore, "w") as fh:
            fh.write("*.log\n")
        ignored_file = os.path.join(src, "ignored.log")
        with open(ignored_file, "w") as fh:
            fh.write("ignored\n")
        _git_add_commit(
            self.tmpdir,
            [".gitignore", "src/a.ts", "src/b.sql", "src/c.md"],
        )

    def test_directory_returns_tracked_polyglot_files(self):
        """All tracked files in src/ are returned (no ext filtering for dir mode)."""
        src_dir = os.path.join(self.tmpdir, "src")
        mr = _mode_result(mode="narrow", scope_arg=src_dir)
        result = resolve_scope(mr, self.tmpdir)
        self.assertIsNone(result["error"])
        self.assertEqual(result["scope_kind"], "directory")
        self.assertEqual(result["pipeline"], "full")
        files = result["files"]
        # All three tracked files present regardless of extension
        self.assertTrue(any("a.ts" in f for f in files))
        self.assertTrue(any("b.sql" in f for f in files))
        self.assertTrue(any("c.md" in f for f in files))

    def test_directory_excludes_gitignored(self):
        """Gitignored files are NOT returned (git ls-files respects .gitignore)."""
        src_dir = os.path.join(self.tmpdir, "src")
        mr = _mode_result(mode="narrow", scope_arg=src_dir)
        result = resolve_scope(mr, self.tmpdir)
        files = result["files"]
        self.assertFalse(any("ignored.log" in f for f in files))

    def test_directory_files_sorted(self):
        src_dir = os.path.join(self.tmpdir, "src")
        mr = _mode_result(mode="narrow", scope_arg=src_dir)
        result = resolve_scope(mr, self.tmpdir)
        files = result["files"]
        self.assertEqual(files, sorted(files))

    def test_directory_full_pipeline(self):
        src_dir = os.path.join(self.tmpdir, "src")
        mr = _mode_result(mode="narrow", scope_arg=src_dir)
        result = resolve_scope(mr, self.tmpdir)
        self.assertEqual(result["pipeline"], "full")


# ---------------------------------------------------------------------------
# Tests — _parse_ls_files_stdout
# ---------------------------------------------------------------------------

class TestParseLsFilesStdout(unittest.TestCase):
    """Unit tests for the shared stdout-parsing helper."""

    def test_empty_string_returns_empty_list(self):
        self.assertEqual(_parse_ls_files_stdout(""), [])

    def test_single_file(self):
        self.assertEqual(_parse_ls_files_stdout("src/foo.py\n"), ["src/foo.py"])

    def test_multiple_files_sorted(self):
        stdout = "src/z.py\nsrc/a.py\nsrc/m.py\n"
        self.assertEqual(_parse_ls_files_stdout(stdout), ["src/a.py", "src/m.py", "src/z.py"])

    def test_blank_lines_ignored(self):
        stdout = "src/a.py\n\nsrc/b.py\n\n"
        self.assertEqual(_parse_ls_files_stdout(stdout), ["src/a.py", "src/b.py"])

    def test_whitespace_stripped(self):
        stdout = "  src/a.py  \n  src/b.py  \n"
        self.assertEqual(_parse_ls_files_stdout(stdout), ["src/a.py", "src/b.py"])

    def test_no_trailing_newline(self):
        stdout = "src/a.py\nsrc/b.py"
        self.assertEqual(_parse_ls_files_stdout(stdout), ["src/a.py", "src/b.py"])

    def test_submodule_prefixed_paths_preserved(self):
        """Paths with submodule prefix (e.g. db-ui/src/foo.py) are returned as-is."""
        stdout = "db-ui/src/bar.ts\ndb-ui/src/foo.ts\n"
        self.assertEqual(
            _parse_ls_files_stdout(stdout),
            ["db-ui/src/bar.ts", "db-ui/src/foo.ts"],
        )


# ---------------------------------------------------------------------------
# Tests — _git_ls_files_dir basic mock tests
# ---------------------------------------------------------------------------

class TestGitLsFilesDirBasic(unittest.TestCase):
    """Mock-based tests for _git_ls_files_dir covering normal-dir and error paths.

    The nested-repo resolution path is covered by TestGitLsFilesDirNestedRepo
    (real git topology) below.
    """

    def _make_proc(self, stdout="", returncode=0):
        """Return a mock CompletedProcess-like object."""
        proc = unittest.mock.MagicMock()
        proc.stdout = stdout
        proc.returncode = returncode
        return proc

    def test_nonempty_plain_result_returned_directly_no_nested_attempt(self):
        """When plain ls-files returns files, no nested-repo attempt is made."""
        plain_stdout = "src/a.py\nsrc/b.py\n"
        with unittest.mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = self._make_proc(stdout=plain_stdout)
            result = _git_ls_files_dir("/repo", "src")
        self.assertEqual(result, ["src/a.py", "src/b.py"])
        # Only one subprocess.run call (the plain one).
        self.assertEqual(mock_run.call_count, 1)

    def test_none_semantics_preserved_plain_file_not_found(self):
        """When git is absent for the plain call, None is returned (no nested attempt)."""
        with unittest.mock.patch(
            "subprocess.run", side_effect=FileNotFoundError("git not found")
        ) as mock_run:
            result = _git_ls_files_dir("/repo", "src")

        self.assertIsNone(result)
        # Only one call was attempted.
        self.assertEqual(mock_run.call_count, 1)

    def test_none_semantics_preserved_plain_nonzero_exit(self):
        """When plain ls-files returns non-zero exit, None is returned (no nested attempt)."""
        with unittest.mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = self._make_proc(stdout="", returncode=128)
            result = _git_ls_files_dir("/repo", "src")

        self.assertIsNone(result)
        # Only one call was attempted.
        self.assertEqual(mock_run.call_count, 1)

    def test_genuinely_empty_dir_no_nested_git_returns_empty_list(self):
        """Plain empty, no .git in ancestors → [] (no nested attempt, no crash).

        The repo_root is a non-existent path so no .git walk can find anything.
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a subdir inside tmpdir (which has no .git).
            empty_dir = os.path.join(tmpdir, "empty-dir")
            os.makedirs(empty_dir)
            with unittest.mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = self._make_proc(stdout="")
                result = _git_ls_files_dir(tmpdir, "empty-dir")

        self.assertIsNotNone(result)
        self.assertEqual(result, [])
        # Only the plain call — no nested git -C call.
        self.assertEqual(mock_run.call_count, 1)

    def test_nested_git_fails_returns_empty_list_not_none(self):
        """Plain empty, nested .git found but git -C fails → [] (not None, no crash).

        Mock: first subprocess.run (plain) → empty rc=0; second (nested git -C)
        → non-zero exit.  We place a real .git dir so the ancestor walk finds it.
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "nested")
            os.makedirs(nested_dir)
            # Plant a .git dir to fool the ancestor walk.
            os.makedirs(os.path.join(nested_dir, ".git"))

            call_count = {"n": 0}
            make_proc = self._make_proc

            def side_effect(cmd, **kwargs):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    # First call: plain git ls-files → empty
                    return make_proc(stdout="", returncode=0)
                # Second call: nested git -C → non-zero exit
                return make_proc(stdout="", returncode=128)

            with unittest.mock.patch("subprocess.run", side_effect=side_effect):
                result = _git_ls_files_dir(tmpdir, "nested")

        self.assertIsNotNone(result)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Tests — _git_ls_files_dir nested-repo resolution (real git topology)
# ---------------------------------------------------------------------------

@unittest.skipUnless(_git_available(), "git not available")
class TestGitLsFilesDirNestedRepo(unittest.TestCase):
    """Real git topology tests for nested-repo resolution in _git_ls_files_dir.

    Builds a workspace repo with a nested independent git repo (its own .git,
    NOT registered as a submodule) and verifies that _git_ls_files_dir returns
    the correct workspace-relative, prefixed paths.
    """

    def setUp(self):
        self.tmpobj = tempfile.TemporaryDirectory()
        self.tmpdir = self.tmpobj.name

        # Initialize workspace (superproject) repo.
        _init_git_repo(self.tmpdir)

        # Create the nested repo directory.
        nested_dir = os.path.join(self.tmpdir, "nested")
        os.makedirs(nested_dir)
        sub_dir = os.path.join(nested_dir, "sub")
        os.makedirs(sub_dir)

        # Initialize the nested repo independently — NOT added to the workspace.
        _init_git_repo(nested_dir)

        # Create and commit files inside the nested repo.
        with open(os.path.join(nested_dir, "a.py"), "w") as fh:
            fh.write("a = 1\n")
        with open(os.path.join(sub_dir, "b.py"), "w") as fh:
            fh.write("b = 2\n")
        _git_add_commit(nested_dir, ["a.py", "sub/b.py"])

    def tearDown(self):
        self.tmpobj.cleanup()

    def test_plain_git_ls_files_returns_zero_files_for_nested(self):
        """Sanity: plain git -C workspace ls-files -- nested/ returns 0 files."""
        proc = subprocess.run(
            ["git", "-C", self.tmpdir, "ls-files", "--", "nested"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        files = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
        self.assertEqual(files, [], "plain ls-files must return 0 for nested repo")

    def test_nested_repo_top_level_returns_workspace_relative_paths(self):
        """_git_ls_files_dir resolves nested/a.py and nested/sub/b.py."""
        result = _git_ls_files_dir(self.tmpdir, "nested")
        self.assertIsNotNone(result)
        self.assertIn("nested/a.py", result)
        self.assertIn("nested/sub/b.py", result)
        self.assertEqual(len(result), 2)

    def test_nested_repo_top_level_paths_are_sorted(self):
        """Returned paths are sorted."""
        result = _git_ls_files_dir(self.tmpdir, "nested")
        self.assertIsNotNone(result)
        self.assertEqual(result, sorted(result))

    def test_nested_repo_top_level_paths_are_workspace_relative(self):
        """Each returned path starts with 'nested/' (workspace-relative prefix)."""
        result = _git_ls_files_dir(self.tmpdir, "nested")
        self.assertIsNotNone(result)
        for path in result:
            self.assertTrue(
                path.startswith("nested/"),
                "Expected workspace-relative prefix 'nested/' but got: {0!r}".format(path),
            )

    def test_nested_repo_subdir_returns_filtered_workspace_relative_paths(self):
        """_git_ls_files_dir with nested/sub returns only nested/sub/b.py."""
        result = _git_ls_files_dir(self.tmpdir, "nested/sub")
        self.assertIsNotNone(result)
        self.assertEqual(result, ["nested/sub/b.py"])

    def test_nested_repo_subdir_does_not_include_sibling_files(self):
        """Requesting nested/sub does not return nested/a.py."""
        result = _git_ls_files_dir(self.tmpdir, "nested/sub")
        self.assertIsNotNone(result)
        self.assertNotIn("nested/a.py", result)

    def test_outer_dir_without_git_containing_nested_repo_returns_empty(self):
        """outer/ has no .git but contains outer/inner/ which is its own git repo.

        _git_ls_files_dir(workspace, "outer") must return [] — not None, no crash.
        The ancestor walk for "outer" finds no .git at the "outer" level, so the
        original empty list from the plain call is returned unchanged.
        """
        with tempfile.TemporaryDirectory() as workspace:
            _init_git_repo(workspace)

            # Create outer/ — NOT a git repo itself.
            outer_dir = os.path.join(workspace, "outer")
            inner_dir = os.path.join(outer_dir, "inner")
            os.makedirs(inner_dir)

            # Initialise inner/ as its own independent git repo.
            subprocess.run(
                ["git", "-c", "user.email=t@t.com", "-c", "user.name=T",
                 "init", inner_dir],
                check=True, capture_output=True,
            )
            inner_file = os.path.join(inner_dir, "inner.py")
            with open(inner_file, "w") as fh:
                fh.write("x = 1\n")
            subprocess.run(
                ["git", "-C", inner_dir, "-c", "user.email=t@t.com",
                 "-c", "user.name=T", "add", "inner.py"],
                check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "-C", inner_dir, "-c", "user.email=t@t.com",
                 "-c", "user.name=T", "commit", "-m", "init", "--allow-empty"],
                check=True, capture_output=True,
            )

            result = _git_ls_files_dir(workspace, "outer")

        # Must be [] (not None, not a crash) — outer itself has no .git, so the
        # ancestor walk never finds a nested-repo root and returns the plain [].
        self.assertIsNotNone(result)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Tests — directory non-git fallback
# ---------------------------------------------------------------------------

class TestResolveScopeDirectoryFallback(unittest.TestCase):
    def setUp(self):
        """Create a non-git directory with various files."""
        self.tmpdir = tempfile.mkdtemp()
        # Regular files
        for name in ("alpha.py", "beta.js"):
            p = os.path.join(self.tmpdir, name)
            with open(p, "w") as fh:
                fh.write("x\n")
        # node_modules should be excluded
        nm = os.path.join(self.tmpdir, "node_modules")
        os.makedirs(nm)
        with open(os.path.join(nm, "dep.js"), "w") as fh:
            fh.write("y\n")
        # dot-dir should be excluded
        dot_dir = os.path.join(self.tmpdir, ".cache")
        os.makedirs(dot_dir)
        with open(os.path.join(dot_dir, "cached.py"), "w") as fh:
            fh.write("z\n")

    def test_fallback_returns_root_files(self):
        # Use a non-git parent — pass a path that won't match a git repo
        mr = _mode_result(mode="narrow", scope_arg=self.tmpdir)
        result = resolve_scope(mr, self.tmpdir)
        self.assertIsNone(result["error"])
        self.assertEqual(result["scope_kind"], "directory")
        files = result["files"]
        self.assertTrue(any("alpha.py" in f for f in files))
        self.assertTrue(any("beta.js" in f for f in files))

    def test_fallback_excludes_node_modules(self):
        mr = _mode_result(mode="narrow", scope_arg=self.tmpdir)
        result = resolve_scope(mr, self.tmpdir)
        files = result["files"]
        self.assertFalse(any("node_modules" in f for f in files))

    def test_fallback_excludes_dot_dirs(self):
        mr = _mode_result(mode="narrow", scope_arg=self.tmpdir)
        result = resolve_scope(mr, self.tmpdir)
        files = result["files"]
        self.assertFalse(any(".cache" in f for f in files))

    def test_fallback_files_sorted(self):
        mr = _mode_result(mode="narrow", scope_arg=self.tmpdir)
        result = resolve_scope(mr, self.tmpdir)
        files = result["files"]
        self.assertEqual(files, sorted(files))


# ---------------------------------------------------------------------------
# Tests — uncommitted mode
# ---------------------------------------------------------------------------

@unittest.skipUnless(_git_available(), "git not available")
class TestResolveScopeUncommitted(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        _init_git_repo(self.tmpdir)
        # Create a committed file
        base = os.path.join(self.tmpdir, "existing.py")
        with open(base, "w") as fh:
            fh.write("x = 1\n")
        _git_add_commit(self.tmpdir, ["existing.py"])

    def test_uncommitted_staged_file(self):
        """A staged (cached) file appears in uncommitted scope."""
        new_file = os.path.join(self.tmpdir, "staged.py")
        with open(new_file, "w") as fh:
            fh.write("staged = True\n")
        subprocess.run(
            ["git", "-C", self.tmpdir, "add", "staged.py"],
            check=True, capture_output=True,
        )
        mr = _mode_result(mode="narrow", uncommitted=True)
        result = resolve_scope(mr, self.tmpdir)
        self.assertIsNone(result["error"])
        self.assertEqual(result["scope_kind"], "uncommitted")
        self.assertEqual(result["pipeline"], "full")
        self.assertIn("staged.py", result["files"])

    def test_uncommitted_modified_file(self):
        """An unstaged modified file appears in uncommitted scope."""
        existing = os.path.join(self.tmpdir, "existing.py")
        with open(existing, "a") as fh:
            fh.write("y = 2\n")
        mr = _mode_result(mode="narrow", uncommitted=True)
        result = resolve_scope(mr, self.tmpdir)
        self.assertIsNone(result["error"])
        self.assertIn("existing.py", result["files"])

    def test_uncommitted_no_changes_gives_empty(self):
        """A clean repo returns empty file list (not an error)."""
        mr = _mode_result(mode="narrow", uncommitted=True)
        result = resolve_scope(mr, self.tmpdir)
        self.assertIsNone(result["error"])
        self.assertEqual(result["files"], [])
        self.assertEqual(result["file_count"], 0)

    def test_uncommitted_deduped(self):
        """Files staged AND unstaged appear once."""
        f = os.path.join(self.tmpdir, "both.py")
        with open(f, "w") as fh:
            fh.write("a = 1\n")
        subprocess.run(
            ["git", "-C", self.tmpdir, "add", "both.py"],
            check=True, capture_output=True,
        )
        with open(f, "a") as fh:
            fh.write("b = 2\n")
        mr = _mode_result(mode="narrow", uncommitted=True)
        result = resolve_scope(mr, self.tmpdir)
        occurrences = result["files"].count("both.py")
        self.assertEqual(occurrences, 1)

    def test_uncommitted_files_sorted(self):
        for name in ("z.py", "a.py"):
            p = os.path.join(self.tmpdir, name)
            with open(p, "w") as fh:
                fh.write("x\n")
        subprocess.run(
            ["git", "-C", self.tmpdir, "add", "z.py", "a.py"],
            check=True, capture_output=True,
        )
        mr = _mode_result(mode="narrow", uncommitted=True)
        result = resolve_scope(mr, self.tmpdir)
        files = result["files"]
        self.assertEqual(files, sorted(files))


# ---------------------------------------------------------------------------
# Tests — scope_oversize boundary (Decision 11)
# ---------------------------------------------------------------------------

@unittest.skipUnless(_git_available(), "git not available")
class TestResolveScopeOversizeBoundary(unittest.TestCase):
    def _make_dir_with_n_files(self, n):
        """Create a tmp git repo with n tracked .py files under src/."""
        tmpdir = tempfile.mkdtemp()
        _init_git_repo(tmpdir)
        src = os.path.join(tmpdir, "src")
        os.makedirs(src)
        names = []
        for i in range(n):
            name = "src/f{0:04d}.py".format(i)
            names.append(name)
            with open(os.path.join(tmpdir, name), "w") as fh:
                fh.write("x\n")
        _git_add_commit(tmpdir, names)
        return tmpdir

    def test_at_limit_not_oversize(self):
        """file_count == scope_limit → scope_oversize is False."""
        tmpdir = self._make_dir_with_n_files(3)
        src = os.path.join(tmpdir, "src")
        mr = _mode_result(mode="narrow", scope_arg=src, scope_limit=3)
        result = resolve_scope(mr, tmpdir)
        self.assertEqual(result["file_count"], 3)
        self.assertFalse(result["scope_oversize"])

    def test_one_over_limit_is_oversize(self):
        """file_count == scope_limit + 1 → scope_oversize is True."""
        tmpdir = self._make_dir_with_n_files(4)
        src = os.path.join(tmpdir, "src")
        mr = _mode_result(mode="narrow", scope_arg=src, scope_limit=3)
        result = resolve_scope(mr, tmpdir)
        self.assertEqual(result["file_count"], 4)
        self.assertTrue(result["scope_oversize"])

    def test_single_file_never_oversize(self):
        """Single file mode never sets scope_oversize even with limit=0."""
        tmpdir = tempfile.mkdtemp()
        f = os.path.join(tmpdir, "x.py")
        with open(f, "w") as fh:
            fh.write("x\n")
        mr = _mode_result(mode="narrow", scope_arg=f, scope_limit=0)
        result = resolve_scope(mr, tmpdir)
        self.assertFalse(result["scope_oversize"])

    def test_broad_never_oversize(self):
        """Broad mode never sets scope_oversize."""
        tmpdir = self._make_dir_with_n_files(4)
        mr = _mode_result(mode="broad", scope_limit=1)
        result = resolve_scope(mr, tmpdir)
        self.assertFalse(result["scope_oversize"])


# ---------------------------------------------------------------------------
# Tests — nonexistent scope_arg
# ---------------------------------------------------------------------------

class TestResolveScopeNonexistent(unittest.TestCase):
    def test_nonexistent_path_returns_error(self):
        mr = _mode_result(mode="narrow", scope_arg="/does/not/exist/xyz.py")
        result = resolve_scope(mr, "/does/not/exist")
        self.assertIsNotNone(result["error"])
        self.assertIn("/does/not/exist/xyz.py", result["error"])
        self.assertEqual(result["scope_kind"], "error")

    def test_unknown_mode_returns_error(self):
        mr = _mode_result(mode="unknown_mode")
        result = resolve_scope(mr, "/any")
        self.assertIsNotNone(result["error"])
        self.assertIn("unknown mode", result["error"])

    def test_error_result_has_all_keys(self):
        mr = _mode_result(mode="narrow", scope_arg="/not/here")
        result = resolve_scope(mr, "/not")
        for key in (
            "scope_kind", "pipeline", "files", "file_count",
            "scope_limit", "scope_oversize", "line_range", "error",
        ):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# Tests — render_scope_block
# ---------------------------------------------------------------------------

class TestRenderScopeBlock(unittest.TestCase):
    def _base_result(self, **kwargs):
        base = {
            "scope_kind": "file",
            "pipeline": "simplified",
            "files": ["src/main.py"],
            "file_count": 1,
            "scope_limit": 200,
            "scope_oversize": False,
            "line_range": None,
            "error": None,
        }
        base.update(kwargs)
        return base

    def test_contains_scope_kind(self):
        block = render_scope_block(self._base_result(), "/repo")
        self.assertIn("file", block)

    def test_contains_pipeline(self):
        block = render_scope_block(self._base_result(), "/repo")
        self.assertIn("simplified", block)

    def test_contains_file_count(self):
        block = render_scope_block(self._base_result(), "/repo")
        self.assertIn("1", block)

    def test_contains_source_root(self):
        block = render_scope_block(self._base_result(), "/myrepo")
        self.assertIn("/myrepo", block)

    def test_file_listed_when_le_25(self):
        r = self._base_result(files=["src/a.py", "src/b.py"], file_count=2)
        block = render_scope_block(r, "/repo")
        self.assertIn("src/a.py", block)
        self.assertIn("src/b.py", block)

    def test_file_list_omitted_when_gt_25(self):
        files = ["f{0}.py".format(i) for i in range(26)]
        r = self._base_result(files=files, file_count=26)
        block = render_scope_block(r, "/repo")
        # Should NOT list individual files
        self.assertNotIn("f0.py", block)
        self.assertIn("26", block)

    def test_line_range_shown(self):
        r = self._base_result(line_range="10-50")
        block = render_scope_block(r, "/repo")
        self.assertIn("10-50", block)

    def test_oversize_warning_shown(self):
        r = self._base_result(
            scope_kind="directory",
            scope_oversize=True,
            file_count=201,
            scope_limit=200,
        )
        block = render_scope_block(r, "/repo")
        self.assertIn("WARNING", block)
        self.assertIn("201", block)

    def test_error_shown(self):
        r = self._base_result(error="something went wrong", scope_kind="error")
        block = render_scope_block(r, "/repo")
        self.assertIn("ERROR", block)
        self.assertIn("something went wrong", block)

    def test_no_oversize_no_warning(self):
        r = self._base_result(scope_oversize=False)
        block = render_scope_block(r, "/repo")
        self.assertNotIn("WARNING", block)


# ---------------------------------------------------------------------------
# Tests — _OUTPUT_CONTRACT contains Category field and enum values
# ---------------------------------------------------------------------------

class TestOutputContractCategoryField(unittest.TestCase):
    """Verify that _OUTPUT_CONTRACT declares Category: and each CATEGORY_ENUM value.

    Keeps the contract text and the schema enum in lockstep: if either side
    changes without the other, this test catches it.
    """

    def test_category_field_label_present(self):
        """The parseable 'Category:' field label must appear in the contract."""
        self.assertIn("Category:", _OUTPUT_CONTRACT)

    def test_all_enum_values_present(self):
        """Every value in CATEGORY_ENUM must appear verbatim in the contract."""
        for value in CATEGORY_ENUM:
            self.assertIn(
                value,
                _OUTPUT_CONTRACT,
                msg="CATEGORY_ENUM value {0!r} not found in _OUTPUT_CONTRACT".format(value),
            )

    def _fenced_block(self):
        """Return the substring of _OUTPUT_CONTRACT up to the closing fence of the
        per-finding format block (located structurally, not by trailing prose, so
        rewording the glossary paragraph below the fence cannot break these tests)."""
        first_fence = _OUTPUT_CONTRACT.index("````")
        closing_fence = _OUTPUT_CONTRACT.index("````", first_fence + 4)
        return _OUTPUT_CONTRACT[:closing_fence]

    def test_category_line_in_format_block(self):
        """Category: must appear inside the fenced format block, not only in prose."""
        self.assertIn(
            "Category:", self._fenced_block(),
            msg="Category: must appear inside the fenced format block",
        )

    def test_hard_rule_for_category(self):
        """The 'every finding MUST declare exactly one Category' hard rule must be present."""
        self.assertIn("Every finding MUST declare exactly one", _OUTPUT_CONTRACT)

    def test_category_positioned_after_pattern(self):
        """Category: line must come after the Pattern: line in the format block."""
        block = self._fenced_block()
        self.assertGreater(
            block.index("Category:"), block.index("Pattern:"),
            msg="Category: must appear after Pattern: in the format block",
        )

    def test_category_positioned_before_confidence(self):
        """Category: line must come before the Confidence: line in the format block."""
        block = self._fenced_block()
        self.assertLess(
            block.index("Category:"), block.index("Confidence:"),
            msg="Category: must appear before Confidence: in the format block",
        )


# ---------------------------------------------------------------------------
# Tests — render_agent_brief with both checklists (Step 6)
# ---------------------------------------------------------------------------

def _make_brief_scope_block():
    """Return a minimal pre-rendered scope block for agent brief tests."""
    scope_result = {
        "scope_kind": "file",
        "pipeline": "simplified",
        "files": ["src/main.py"],
        "file_count": 1,
        "scope_limit": 200,
        "scope_oversize": False,
        "line_range": None,
        "error": None,
    }
    return render_scope_block(scope_result, "/test/repo")


class TestRenderAgentBriefBothChecklists(unittest.TestCase):
    """Both checklists must be injected into every agent brief (always-on)."""

    def _make_brief(self, agent):
        return render_agent_brief(
            agent=agent,
            references_dir=str(_REFERENCES_DIR),
            scope_block=_make_brief_scope_block(),
            source_root="/test/repo",
        )

    def test_mislogic_checklist_present_code_reviewer(self):
        brief = self._make_brief("code-reviewer")
        self.assertIn("MISLOGIC HUNT CHECKLIST", brief)

    def test_best_practices_checklist_present_code_reviewer(self):
        brief = self._make_brief("code-reviewer")
        self.assertIn("BEST-PRACTICES", brief)

    def test_best_practices_distinctive_substring_present(self):
        """A distinctive phrase from best-practices-checklist.md is in every brief."""
        for agent in ("code-reviewer", "architect", "qa-reviewer", "security-reviewer"):
            brief = self._make_brief(agent)
            self.assertIn(
                "Type-safety suppression",
                brief,
                "Agent {0}: best-practices checklist missing distinctive phrase".format(agent),
            )

    def test_mislogic_distinctive_substring_present(self):
        """A distinctive phrase from mislogic-checklist.md is in every brief."""
        for agent in ("code-reviewer", "architect", "qa-reviewer", "security-reviewer"):
            brief = self._make_brief(agent)
            self.assertIn(
                "MISLOGIC HUNT CHECKLIST",
                brief,
                "Agent {0}: mislogic checklist missing".format(agent),
            )

    def test_focus_text_present(self):
        """Per-agent focus text is in the brief."""
        brief_cr = self._make_brief("code-reviewer")
        self.assertIn("naming-vs-behavior mismatches", brief_cr)
        brief_ar = self._make_brief("architect")
        self.assertIn("cross-module contradictions", brief_ar)

    def test_assembly_order_best_practices_after_mislogic(self):
        """Best-practices checklist must appear AFTER the mislogic checklist."""
        for agent in ("code-reviewer", "architect", "qa-reviewer", "security-reviewer"):
            brief = self._make_brief(agent)
            mislogic_pos = brief.find("MISLOGIC HUNT CHECKLIST")
            best_practices_pos = brief.find("BEST-PRACTICES")
            self.assertGreater(
                best_practices_pos,
                mislogic_pos,
                "Agent {0}: best-practices checklist does not appear after mislogic checklist".format(agent),
            )

    def test_assembly_order_best_practices_before_focus(self):
        """Best-practices checklist must appear BEFORE the per-agent focus block."""
        for agent in ("code-reviewer", "architect", "qa-reviewer", "security-reviewer"):
            brief = self._make_brief(agent)
            best_practices_pos = brief.find("BEST-PRACTICES")
            focus_text = _FOCUS_BLOCKS[agent]
            # Use first 40 chars of focus to locate it (avoids newline issues)
            focus_pos = brief.find(focus_text[:40])
            self.assertGreater(
                focus_pos,
                best_practices_pos,
                "Agent {0}: best-practices checklist does not appear before focus block".format(agent),
            )


class TestRenderAgentBriefMissingBestPracticesFile(unittest.TestCase):
    """Missing best-practices-checklist.md must raise ValueError."""

    def test_missing_best_practices_raises_value_error(self):
        """Only preamble + mislogic-checklist present; best-practices absent raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "adversarial-preamble.md"), "w") as fh:
                fh.write("preamble content\n")
            with open(os.path.join(tmpdir, "mislogic-checklist.md"), "w") as fh:
                fh.write("mislogic content\n")
            # best-practices-checklist.md intentionally absent
            with self.assertRaises(ValueError) as ctx:
                render_agent_brief(
                    agent="code-reviewer",
                    references_dir=tmpdir,
                    scope_block=_make_brief_scope_block(),
                    source_root="/repo",
                )
            self.assertIn("best-practices-checklist.md", str(ctx.exception))

    def test_missing_best_practices_error_mentions_references_dir(self):
        """ValueError message must include the references_dir path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "adversarial-preamble.md"), "w") as fh:
                fh.write("preamble\n")
            with open(os.path.join(tmpdir, "mislogic-checklist.md"), "w") as fh:
                fh.write("mislogic\n")
            with self.assertRaises(ValueError) as ctx:
                render_agent_brief(
                    agent="architect",
                    references_dir=tmpdir,
                    scope_block=_make_brief_scope_block(),
                    source_root="/repo",
                )
            self.assertIn(tmpdir, str(ctx.exception))


class TestFocusBlocksCategoryReminders(unittest.TestCase):
    """Each _FOCUS_BLOCKS entry must contain its Category: reminder."""

    def test_code_reviewer_has_best_practice_category(self):
        self.assertIn("Category: best_practice", _FOCUS_BLOCKS["code-reviewer"])

    def test_code_reviewer_has_mislogic_category(self):
        self.assertIn("Category: mislogic", _FOCUS_BLOCKS["code-reviewer"])

    def test_architect_has_system_design_category(self):
        self.assertIn("Category: system_design", _FOCUS_BLOCKS["architect"])

    def test_architect_has_duplication_category(self):
        self.assertIn("Category: duplication", _FOCUS_BLOCKS["architect"])

    def test_qa_reviewer_has_blind_spot_category(self):
        self.assertIn("Category: blind_spot", _FOCUS_BLOCKS["qa-reviewer"])

    def test_security_reviewer_has_security_category(self):
        self.assertIn("Category: security", _FOCUS_BLOCKS["security-reviewer"])

    def test_all_category_values_in_enum(self):
        """Every Category value referenced in focus blocks must be in CATEGORY_ENUM."""
        import re
        pattern = re.compile(r"`Category:\s*(\w+)`")
        for agent, text in _FOCUS_BLOCKS.items():
            for match in pattern.finditer(text):
                value = match.group(1)
                self.assertIn(
                    value,
                    CATEGORY_ENUM,
                    "Focus block for {0!r} references unknown category {1!r}".format(agent, value),
                )


# ---------------------------------------------------------------------------
# Tests — finding_cap substitution (Changes 1-3)
# ---------------------------------------------------------------------------

class TestFindingCapSubstitution(unittest.TestCase):
    """Verify __FINDING_CAP__ token is substituted correctly in rendered briefs."""

    def _make_brief(self, agent="code-reviewer", finding_cap=30, extra_context=""):
        scope_result = {
            "scope_kind": "file",
            "pipeline": "simplified",
            "files": ["src/main.py"],
            "file_count": 1,
            "scope_limit": 200,
            "scope_oversize": False,
            "line_range": None,
            "error": None,
        }
        scope_block = render_scope_block(scope_result, "/test/repo")
        return render_agent_brief(
            agent=agent,
            references_dir=str(_REFERENCES_DIR),
            scope_block=scope_block,
            source_root="/test/repo",
            extra_context=extra_context,
            finding_cap=finding_cap,
        )

    def test_default_cap_no_token_leak(self):
        """Default cap renders without the literal __FINDING_CAP__ token."""
        brief = self._make_brief()
        self.assertNotIn("__FINDING_CAP__", brief)

    def test_default_cap_contains_30(self):
        """Default cap substitutes 30 in the brief where the cap goes."""
        brief = self._make_brief()
        self.assertIn("30", brief)

    def test_custom_cap_58_no_token_leak(self):
        """finding_cap=58 renders without the literal __FINDING_CAP__ token."""
        brief = self._make_brief(finding_cap=58)
        self.assertNotIn("__FINDING_CAP__", brief)

    def test_custom_cap_58_contains_58(self):
        """finding_cap=58 substitutes 58 in the brief where the cap goes."""
        brief = self._make_brief(finding_cap=58)
        self.assertIn("58", brief)

    def test_custom_cap_58_not_30(self):
        """With finding_cap=58, the cap portion does NOT say 30."""
        brief = self._make_brief(finding_cap=58)
        # Verify substitution propagated to both locations in the brief.
        # "Cap: 58 findings" from _OUTPUT_CONTRACT must be present.
        self.assertIn("Cap: 58 findings", brief)
        # And the default 30 cap wording must be gone.
        self.assertNotIn("Cap: 30 findings", brief)

    def test_token_replaced_in_output_contract_section(self):
        """__FINDING_CAP__ is replaced in the _OUTPUT_CONTRACT part of the brief."""
        brief = self._make_brief(finding_cap=42)
        # The contract part should have 42, not the token.
        self.assertIn("Cap: 42 findings", brief)
        self.assertNotIn("__FINDING_CAP__", brief)

    def test_token_replaced_in_closing_reminder_section(self):
        """__FINDING_CAP__ is replaced in the _CLOSING_REMINDER part of the brief."""
        brief = self._make_brief(finding_cap=15)
        # The closing section says "up to __FINDING_CAP__" which should be "up to 15".
        self.assertIn("up to 15", brief)
        self.assertNotIn("__FINDING_CAP__", brief)

    def test_bad_cap_zero_falls_back_to_30(self):
        """finding_cap=0 is invalid; falls back to default 30."""
        brief = self._make_brief(finding_cap=0)
        self.assertNotIn("__FINDING_CAP__", brief)
        self.assertIn("Cap: 30 findings", brief)

    def test_bad_cap_negative_falls_back_to_30(self):
        """finding_cap=-5 is invalid; falls back to default 30."""
        brief = self._make_brief(finding_cap=-5)
        self.assertNotIn("__FINDING_CAP__", brief)
        self.assertIn("Cap: 30 findings", brief)

    def test_all_agents_no_token_leak(self):
        """No agent's brief leaks the literal __FINDING_CAP__ token."""
        for agent in ("code-reviewer", "architect", "qa-reviewer", "security-reviewer"):
            brief = self._make_brief(agent=agent)
            self.assertNotIn(
                "__FINDING_CAP__", brief,
                "Agent {0}: __FINDING_CAP__ token leaked into brief".format(agent),
            )


class TestOutputContractEnumerateEveryInstance(unittest.TestCase):
    """Verify the new enumerate-every-instance rule text is in _OUTPUT_CONTRACT."""

    def test_enumerate_every_instance_text_present(self):
        """The 'Enumerate every real, grounded instance' hard rule is in the contract."""
        self.assertIn(
            "Enumerate every real, grounded instance — do NOT collapse a recurring pattern",
            _OUTPUT_CONTRACT,
        )

    def test_enumerate_cap_token_present(self):
        """The __FINDING_CAP__ token is in _OUTPUT_CONTRACT before substitution."""
        self.assertIn("__FINDING_CAP__", _OUTPUT_CONTRACT)

    def test_exact_quote_or_drop_text_present(self):
        """The 'DROP the finding' exact-quote instruction is in the contract."""
        self.assertIn(
            "If you cannot locate and copy the EXACT bytes from the file, DROP the finding",
            _OUTPUT_CONTRACT,
        )

    def test_recall_matters_more_than_brevity_present(self):
        """The 'recall matters more than brevity' framing is present."""
        self.assertIn("recall matters more than brevity", _OUTPUT_CONTRACT)


class TestClosingReminderEnumerateText(unittest.TestCase):
    """Verify the updated _CLOSING_REMINDER text."""

    def test_enumerate_up_to_cap_text_present(self):
        """The new 'Enumerate every real instance' text is in _CLOSING_REMINDER."""
        self.assertIn(
            "Enumerate every real instance you can quote exactly, up to",
            _CLOSING_REMINDER,
        )

    def test_do_not_stop_at_one_example_present(self):
        """The 'do not stop at one example' instruction is in _CLOSING_REMINDER."""
        self.assertIn(
            "do not stop at one example of a recurring pattern",
            _CLOSING_REMINDER,
        )

    def test_drop_any_finding_text_present(self):
        """The 'drop any finding whose quote you cannot copy verbatim' is present."""
        self.assertIn(
            "drop any finding whose quote you cannot copy verbatim from the file",
            _CLOSING_REMINDER,
        )

    def test_cap_token_present(self):
        """__FINDING_CAP__ token is in _CLOSING_REMINDER before substitution."""
        self.assertIn("__FINDING_CAP__", _CLOSING_REMINDER)


# ---------------------------------------------------------------------------
# Tests — render_agent_brief tmp_path parameter
# ---------------------------------------------------------------------------


class TestRenderAgentBriefTmpPath(unittest.TestCase):
    """Verify tmp_path controls the agent findings write-path in the brief."""

    _DEFAULT_PATH_TOKEN = "audits/.tmp-{agent-name}.md"
    _CUSTOM_PATH = "/tmp/forge-audit-abc/tmp-architect-p2.md"

    def _make_brief(self, agent="architect", tmp_path=None):
        # type: (str, object) -> str
        return render_agent_brief(
            agent=agent,
            references_dir=str(_REFERENCES_DIR),
            scope_block=_make_brief_scope_block(),
            source_root="/test/repo",
            tmp_path=tmp_path,
        )

    # --- default (no tmp_path): backward-compatible behavior ---

    def test_default_tmp_path_none_contains_default_path(self):
        """When tmp_path is None, the brief contains the default audits/.tmp-{agent-name}.md."""
        brief = self._make_brief(agent="architect", tmp_path=None)
        self.assertIn(self._DEFAULT_PATH_TOKEN, brief)

    def test_default_tmp_path_none_exact_sentence(self):
        """When tmp_path is None, the main sentence uses the default path verbatim."""
        brief = self._make_brief(agent="code-reviewer", tmp_path=None)
        self.assertIn(
            "Each agent writes its findings to `audits/.tmp-{agent-name}.md`",
            brief,
        )

    def test_default_tmp_path_for_all_agents(self):
        """Default path token present for every agent when tmp_path is None."""
        for agent in ("code-reviewer", "architect", "qa-reviewer", "security-reviewer"):
            brief = self._make_brief(agent=agent, tmp_path=None)
            self.assertIn(
                self._DEFAULT_PATH_TOKEN,
                brief,
                "Agent {0}: default path token missing when tmp_path=None".format(agent),
            )

    # --- custom tmp_path: path substitution ---

    def test_custom_tmp_path_present_in_brief(self):
        """When tmp_path is set, the brief contains that exact path string."""
        brief = self._make_brief(tmp_path=self._CUSTOM_PATH)
        self.assertIn(self._CUSTOM_PATH, brief)

    def test_custom_tmp_path_replaces_default_path(self):
        """When tmp_path is set, the default audits/.tmp-{agent-name}.md is gone."""
        brief = self._make_brief(tmp_path=self._CUSTOM_PATH)
        self.assertNotIn(self._DEFAULT_PATH_TOKEN, brief)

    def test_custom_tmp_path_main_sentence(self):
        """The main 'Each agent writes its findings to' sentence uses the custom path."""
        brief = self._make_brief(tmp_path=self._CUSTOM_PATH)
        self.assertIn(
            "Each agent writes its findings to `{0}`".format(self._CUSTOM_PATH),
            brief,
        )

    def test_custom_tmp_path_failure_instruction(self):
        """The failure instruction references the custom path, not 'a temp file'."""
        brief = self._make_brief(tmp_path=self._CUSTOM_PATH)
        self.assertIn(
            "write `{0}` with `# Status: failed`".format(self._CUSTOM_PATH),
            brief,
        )

    def test_custom_tmp_path_empty_file_instruction(self):
        """The empty-file instruction references the custom path, not 'a temp file'."""
        brief = self._make_brief(tmp_path=self._CUSTOM_PATH)
        self.assertIn(
            "write `{0}` with `# Status: complete`".format(self._CUSTOM_PATH),
            brief,
        )

    def test_custom_tmp_path_no_stray_default_path(self):
        """When tmp_path is set, no stray audits/.tmp- references remain."""
        brief = self._make_brief(tmp_path=self._CUSTOM_PATH)
        self.assertNotIn("audits/.tmp-", brief)

    def test_custom_tmp_path_with_pass_suffix(self):
        """Multi-pass path suffix is emitted verbatim."""
        pass_path = "/tmp/forge-run-xyz/tmp-code-reviewer-p1.md"
        brief = self._make_brief(agent="code-reviewer", tmp_path=pass_path)
        self.assertIn(pass_path, brief)
        self.assertNotIn(self._DEFAULT_PATH_TOKEN, brief)

    def test_custom_tmp_path_verbatim_no_normalization(self):
        """tmp_path is emitted verbatim: no path normalization, no quoting."""
        unusual_path = "relative/path/with spaces/tmp-qa-p3.md"
        brief = self._make_brief(agent="qa-reviewer", tmp_path=unusual_path)
        self.assertIn(unusual_path, brief)

    def test_custom_tmp_path_all_agents(self):
        """Custom tmp_path substitution works for every agent."""
        for agent in ("code-reviewer", "architect", "qa-reviewer", "security-reviewer"):
            brief = self._make_brief(agent=agent, tmp_path=self._CUSTOM_PATH)
            self.assertIn(
                self._CUSTOM_PATH,
                brief,
                "Agent {0}: custom path not found in brief".format(agent),
            )
            self.assertNotIn(
                self._DEFAULT_PATH_TOKEN,
                brief,
                "Agent {0}: default path token still present when tmp_path set".format(agent),
            )

    def test_tmp_path_combined_with_finding_cap(self):
        """tmp_path and finding_cap can both be set; both substitutions apply."""
        brief = render_agent_brief(
            agent="architect",
            references_dir=str(_REFERENCES_DIR),
            scope_block=_make_brief_scope_block(),
            source_root="/test/repo",
            finding_cap=42,
            tmp_path=self._CUSTOM_PATH,
        )
        self.assertIn(self._CUSTOM_PATH, brief)
        self.assertNotIn(self._DEFAULT_PATH_TOKEN, brief)
        self.assertNotIn("__FINDING_CAP__", brief)
        self.assertIn("Cap: 42 findings", brief)

    def test_default_behavior_byte_identical_when_tmp_path_omitted(self):
        """Brief content is identical whether tmp_path is omitted or explicitly None."""
        brief_omitted = render_agent_brief(
            agent="security-reviewer",
            references_dir=str(_REFERENCES_DIR),
            scope_block=_make_brief_scope_block(),
            source_root="/test/repo",
        )
        brief_explicit_none = render_agent_brief(
            agent="security-reviewer",
            references_dir=str(_REFERENCES_DIR),
            scope_block=_make_brief_scope_block(),
            source_root="/test/repo",
            tmp_path=None,
        )
        self.assertEqual(brief_omitted, brief_explicit_none)

    def test_constant_not_mutated_after_custom_call(self):
        """A custom tmp_path call must not mutate _OUTPUT_CONTRACT; a subsequent
        default call must still emit the default audits/.tmp-{agent-name}.md path."""
        # custom call first
        _ = self._make_brief(agent="architect", tmp_path="/tmp/forge-audit/tmp-architect-p1.md")
        # then a default call — must still contain the default path, not the custom one
        brief_after = self._make_brief(agent="architect", tmp_path=None)
        self.assertIn(self._DEFAULT_PATH_TOKEN, brief_after)
        self.assertNotIn("/tmp/forge-audit/tmp-architect-p1.md", brief_after)


if __name__ == "__main__":
    unittest.main()
