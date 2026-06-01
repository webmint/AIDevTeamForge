"""Tests for src/devforge/lib/_audit/_scope.py.

Coverage:
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
        for agent in ("code-reviewer", "architect", "qa-engineer", "security-reviewer"):
            brief = self._make_brief(agent)
            self.assertIn(
                "Type-safety suppression",
                brief,
                "Agent {0}: best-practices checklist missing distinctive phrase".format(agent),
            )

    def test_mislogic_distinctive_substring_present(self):
        """A distinctive phrase from mislogic-checklist.md is in every brief."""
        for agent in ("code-reviewer", "architect", "qa-engineer", "security-reviewer"):
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
        for agent in ("code-reviewer", "architect", "qa-engineer", "security-reviewer"):
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
        for agent in ("code-reviewer", "architect", "qa-engineer", "security-reviewer"):
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

    def test_qa_engineer_has_blind_spot_category(self):
        self.assertIn("Category: blind_spot", _FOCUS_BLOCKS["qa-engineer"])

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
        for agent in ("code-reviewer", "architect", "qa-engineer", "security-reviewer"):
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


if __name__ == "__main__":
    unittest.main()
