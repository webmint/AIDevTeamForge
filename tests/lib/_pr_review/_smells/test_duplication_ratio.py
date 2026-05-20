"""Tests for src/devforge/lib/_pr_review/_smells/duplication_ratio.py.

Coverage:
    _split_diff_blocks         — helper, isolated
    _extract_new_files         — positive (new file), negative (modified file), ext filter
    _find_candidate_files      — sorted by basename similarity, cap at _MAX_CANDIDATES
    _best_match                — highest-ratio candidate cited; below threshold → None
    run()                      — positive, negative, tiny file skip, no target, empty diff
    Finding schema             — correct keys, ratio in evidence
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._smells.duplication_ratio import (  # noqa: E402
    _DUPLICATION_THRESHOLD,
    _MAX_CANDIDATES,
    _MIN_LINES_FOR_CHECK,
    _best_match,
    _extract_new_files,
    _find_candidate_files,
    _split_diff_blocks,
    run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_new_file_diff(rel_path: str, lines: list) -> str:
    """Build a synthetic unified diff that adds a new file."""
    content_lines = "\n".join("+" + ln for ln in lines)
    return (
        "diff --git a/{path} b/{path}\n"
        "new file mode 100644\n"
        "index 0000000..1111111\n"
        "--- /dev/null\n"
        "+++ b/{path}\n"
        "@@ -0,0 +1,{n} @@\n"
        "{content}\n"
    ).format(path=rel_path, n=len(lines), content=content_lines)


def _make_modified_file_diff(rel_path: str, added_lines: list) -> str:
    """Build a synthetic unified diff that modifies an existing file."""
    content_lines = "\n".join("+" + ln for ln in added_lines)
    return (
        "diff --git a/{path} b/{path}\n"
        "index abc..def 100644\n"
        "--- a/{path}\n"
        "+++ b/{path}\n"
        "@@ -1,0 +1,{n} @@\n"
        "{content}\n"
    ).format(path=rel_path, n=len(added_lines), content=content_lines)


def _make_state(diff: str, target: str = "") -> SimpleNamespace:
    return SimpleNamespace(diff=diff, target=target)


def _write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _50_lines() -> list:
    return ["line {i}".format(i=i) for i in range(50)]


def _90_percent_copy(lines: list) -> str:
    """Return a file content that is ~90% similar to the joined lines."""
    # Take the first 45 lines verbatim, then change the rest slightly.
    kept = lines[:45]
    changed = ["CHANGED line {i}".format(i=i) for i in range(5)]
    return "\n".join(kept + changed)


# ---------------------------------------------------------------------------
# _split_diff_blocks
# ---------------------------------------------------------------------------


class TestSplitDiffBlocks(unittest.TestCase):
    def test_empty_diff_returns_empty_list(self):
        self.assertEqual(_split_diff_blocks(""), [])

    def test_single_block(self):
        diff = "diff --git a/foo.py b/foo.py\n+content\n"
        blocks = _split_diff_blocks(diff)
        self.assertEqual(len(blocks), 1)
        self.assertIn("diff --git", blocks[0])

    def test_two_blocks(self):
        diff = (
            "diff --git a/foo.py b/foo.py\n+a\n"
            "diff --git a/bar.py b/bar.py\n+b\n"
        )
        blocks = _split_diff_blocks(diff)
        self.assertEqual(len(blocks), 2)
        self.assertIn("foo.py", blocks[0])
        self.assertIn("bar.py", blocks[1])


# ---------------------------------------------------------------------------
# _extract_new_files
# ---------------------------------------------------------------------------


class TestExtractNewFiles(unittest.TestCase):
    def test_new_python_file_extracted(self):
        lines = _50_lines()
        diff = _make_new_file_diff("src/foo.py", lines)
        result = _extract_new_files(diff)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "src/foo.py")

    def test_modified_file_not_extracted(self):
        diff = _make_modified_file_diff("src/foo.py", _50_lines())
        result = _extract_new_files(diff)
        self.assertEqual(result, [])

    def test_non_code_extension_excluded(self):
        diff = _make_new_file_diff("README.md", _50_lines())
        result = _extract_new_files(diff)
        self.assertEqual(result, [])

    def test_ts_extension_included(self):
        diff = _make_new_file_diff("src/app.ts", _50_lines())
        result = _extract_new_files(diff)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "src/app.ts")

    def test_multiple_new_files(self):
        diff = (
            _make_new_file_diff("a.py", _50_lines()) +
            _make_new_file_diff("b.py", _50_lines())
        )
        result = _extract_new_files(diff)
        self.assertEqual(len(result), 2)

    def test_content_reconstructed_from_added_lines(self):
        lines = ["import os", "def foo(): pass"] + ["line {i}".format(i=i) for i in range(50)]
        diff = _make_new_file_diff("src/foo.py", lines)
        result = _extract_new_files(diff)
        self.assertIn("import os", result[0][1])


# ---------------------------------------------------------------------------
# _best_match
# ---------------------------------------------------------------------------


class TestBestMatch(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_high_similarity_returns_match(self):
        lines = _50_lines()
        new_content = "\n".join(lines)
        existing_path = os.path.join(self.tmpdir, "existing.py")
        # 90% similar: same first 45 lines, last 5 changed.
        similar_content = _90_percent_copy(lines)
        _write_file(existing_path, similar_content)

        result = _best_match(new_content, [existing_path])
        self.assertIsNotNone(result)
        match_path, ratio = result
        self.assertEqual(match_path, existing_path)
        self.assertGreaterEqual(ratio, _DUPLICATION_THRESHOLD)

    def test_low_similarity_returns_none(self):
        new_content = "\n".join("line {i}".format(i=i) for i in range(50))
        existing_path = os.path.join(self.tmpdir, "unrelated.py")
        _write_file(existing_path, "completely different content here\n" * 50)

        result = _best_match(new_content, [existing_path])
        self.assertIsNone(result)

    def test_multiple_candidates_highest_ratio_cited(self):
        lines = _50_lines()
        new_content = "\n".join(lines)

        # 40% similar file.
        low_path = os.path.join(self.tmpdir, "low.py")
        _write_file(low_path, "x = 1\n" * 50)

        # 90% similar file.
        high_path = os.path.join(self.tmpdir, "high.py")
        _write_file(high_path, _90_percent_copy(lines))

        result = _best_match(new_content, [low_path, high_path])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], high_path)

    def test_unreadable_candidate_skipped(self):
        new_content = "\n".join(_50_lines())
        result = _best_match(new_content, ["/nonexistent/path/file.py"])
        self.assertIsNone(result)

    def test_empty_candidate_list_returns_none(self):
        self.assertIsNone(_best_match("content", []))


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestAddedContentLineRENoBlankCross(unittest.TestCase):
    """F3: blank added line between two code-added lines must not cause cross-line merging."""

    def test_blank_added_line_does_not_merge_adjacent_content(self):
        """A blank '+\\n' line between code lines must not consume the next line's '+'."""
        from _pr_review._smells.duplication_ratio import _ADDED_CONTENT_LINE_RE
        diff_fragment = "+first_line\n+\n+second_line\n"
        matches = _ADDED_CONTENT_LINE_RE.findall(diff_fragment)
        # Should match 'first_line' and 'second_line'; blank line '+\n' must not
        # consume the newline and merge with '+second_line'.
        self.assertIn("first_line", matches)
        self.assertIn("second_line", matches)
        # No match should contain a newline character.
        for m in matches:
            self.assertNotIn("\n", m)


class TestFindCandidateFilesHiddenDirFilter(unittest.TestCase):
    """F2: hidden directories must be pruned so os.walk never descends into them."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_hidden_dir_files_excluded(self):
        """Files inside .hidden_dir/ must NOT appear in candidates."""
        _write_file(os.path.join(self.tmpdir, ".hidden_dir", "secret.py"), "x = 1\n" * 60)
        _write_file(os.path.join(self.tmpdir, "regular_dir", "bar.py"), "x = 1\n" * 60)

        candidates = _find_candidate_files(self.tmpdir, ".py", "new.py")
        candidate_basenames = [os.path.basename(p) for p in candidates]
        self.assertIn("bar.py", candidate_basenames)
        self.assertNotIn("secret.py", candidate_basenames)

    def test_dotgit_not_walked(self):
        """.git directory (a common hidden dir) is pruned."""
        _write_file(os.path.join(self.tmpdir, ".git", "objects", "pack.py"), "pass\n" * 60)
        _write_file(os.path.join(self.tmpdir, "src", "module.py"), "x = 1\n" * 60)

        candidates = _find_candidate_files(self.tmpdir, ".py", "new.py")
        abs_paths = [os.path.abspath(p) for p in candidates]
        for p in abs_paths:
            self.assertNotIn(".git", p.split(os.sep))


class TestDuplicationRatioRun(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_positive_high_similarity_fires(self):
        """New file with 90%+ similarity to existing file → finding emitted."""
        lines = _50_lines()
        diff = _make_new_file_diff("src/newfile.py", lines)

        # Write 90% similar existing file into the temp dir.
        existing = os.path.join(self.tmpdir, "similar.py")
        _write_file(existing, _90_percent_copy(lines))

        state = _make_state(diff, target=self.tmpdir)
        findings = run(state)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["name"], "duplication_ratio")

    def test_negative_unique_file_no_finding(self):
        """New file unique to repo → no finding."""
        lines = _50_lines()
        diff = _make_new_file_diff("src/unique.py", lines)

        # Write completely different existing file.
        existing = os.path.join(self.tmpdir, "unrelated.py")
        _write_file(existing, "COMPLETELY DIFFERENT\n" * 50)

        state = _make_state(diff, target=self.tmpdir)
        findings = run(state)
        self.assertEqual(findings, [])

    def test_tiny_file_skipped(self):
        """New file < 50 lines → not scanned, no finding."""
        lines = ["line {i}".format(i=i) for i in range(10)]  # only 10 lines
        diff = _make_new_file_diff("src/small.py", lines)

        # Write identical existing file.
        existing = os.path.join(self.tmpdir, "small.py")
        _write_file(existing, "\n".join(lines))

        state = _make_state(diff, target=self.tmpdir)
        findings = run(state)
        self.assertEqual(findings, [])

    def test_no_target_no_finding(self):
        """state.target is empty → no finding (fail-soft)."""
        diff = _make_new_file_diff("src/foo.py", _50_lines())
        state = _make_state(diff, target="")
        findings = run(state)
        self.assertEqual(findings, [])

    def test_empty_diff_no_finding(self):
        state = _make_state("", target=self.tmpdir)
        findings = run(state)
        self.assertEqual(findings, [])

    def test_no_code_ext_files_in_repo_no_crash(self):
        """Repo has no Python files matching ext → no finding, no crash."""
        lines = _50_lines()
        diff = _make_new_file_diff("src/foo.py", lines)
        # Only write a markdown file.
        _write_file(os.path.join(self.tmpdir, "README.md"), "hello\n")
        state = _make_state(diff, target=self.tmpdir)
        findings = run(state)
        self.assertEqual(findings, [])

    def test_finding_schema(self):
        lines = _50_lines()
        diff = _make_new_file_diff("src/newfile.py", lines)
        existing = os.path.join(self.tmpdir, "similar.py")
        _write_file(existing, _90_percent_copy(lines))

        state = _make_state(diff, target=self.tmpdir)
        findings = run(state)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["name"], "duplication_ratio")
        self.assertEqual(f["severity"], "medium")
        self.assertEqual(f["location"], "src/newfile.py")
        self.assertIn("matches", f["evidence"])
        self.assertIn("0.", f["evidence"])  # ratio like "0.90"

    def test_multiple_new_files_highest_ratio_cited(self):
        """When multiple candidates exist, the one with the highest ratio is cited."""
        lines = _50_lines()
        diff = _make_new_file_diff("src/newfile.py", lines)

        # High similarity file.
        high = os.path.join(self.tmpdir, "high_sim.py")
        _write_file(high, _90_percent_copy(lines))

        # Low similarity file.
        low = os.path.join(self.tmpdir, "low_sim.py")
        _write_file(low, "x = 1\n" * 50)

        state = _make_state(diff, target=self.tmpdir)
        findings = run(state)
        # Should cite the high-similarity file.
        self.assertEqual(len(findings), 1)
        self.assertIn("high_sim", findings[0]["evidence"])


if __name__ == "__main__":
    unittest.main()
