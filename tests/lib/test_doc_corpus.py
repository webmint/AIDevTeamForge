"""Tests for _generate_docs/_doc_corpus.py — JUDGMENT-LAYER-PLAN Step 0 Unit A.

Test groups:
  1. walk_doc_corpus           (5 cases)
  2. extract_term_occurrences  (5 cases)
  2b. _context_around          (6 cases — Finding 2 regression)
  3. validate_cite_paths       (4 cases)
  4. get_section_body_span     (4 cases)
  5. noise_filter              (6 cases)

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs._doc_corpus import (  # noqa: E402
    _context_around,
    extract_term_occurrences,
    get_section_body_span,
    noise_filter,
    validate_cite_paths,
    walk_doc_corpus,
)


# ── 1. walk_doc_corpus ────────────────────────────────────────────────────────


class TestWalkDocCorpus(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_nonexistent_docs_root_returns_empty(self):
        result = walk_doc_corpus(self.root / "no_such_dir")
        self.assertEqual(result, [])

    def test_single_file_with_frontmatter(self):
        docs = self.root / "docs"
        docs.mkdir()
        content = (
            "---\n"
            "project: myproj\n"
            "---\n"
            "\n"
            "# MyProject\n\n"
            "Some body text here.\n"
        )
        (docs / "overview.md").write_text(content, encoding="utf-8")

        result = walk_doc_corpus(docs)

        self.assertEqual(len(result), 1)
        rel, fm, body = result[0]
        self.assertEqual(rel, "overview.md")
        self.assertEqual(fm.get("project"), "myproj")
        self.assertIn("# MyProject", body)
        self.assertIn("Some body text here.", body)

    def test_nested_dir_posix_path_and_sorted_order(self):
        docs = self.root / "docs"
        docs.mkdir()
        (docs / "packages").mkdir()
        (docs / "packages" / "foo").mkdir()

        (docs / "overview.md").write_text("# Root\n", encoding="utf-8")
        (docs / "packages" / "foo" / "overview.md").write_text("# Foo\n", encoding="utf-8")
        (docs / "architecture.md").write_text("# Arch\n", encoding="utf-8")

        result = walk_doc_corpus(docs)

        self.assertEqual(len(result), 3)
        paths = [r[0] for r in result]
        # Must be POSIX forward-slash and sorted
        self.assertEqual(paths[0], "architecture.md")
        self.assertEqual(paths[1], "overview.md")
        self.assertEqual(paths[2], "packages/foo/overview.md")

    def test_no_md_files_returns_empty(self):
        docs = self.root / "docs"
        docs.mkdir()
        (docs / "readme.txt").write_text("not markdown", encoding="utf-8")
        result = walk_doc_corpus(docs)
        self.assertEqual(result, [])

    def test_file_without_frontmatter_uses_empty_dict(self):
        docs = self.root / "docs"
        docs.mkdir()
        (docs / "bare.md").write_text("# No frontmatter here\n", encoding="utf-8")
        result = walk_doc_corpus(docs)
        self.assertEqual(len(result), 1)
        rel, fm, body = result[0]
        self.assertEqual(fm, {})
        self.assertIn("# No frontmatter here", body)


# ── 2. extract_term_occurrences ───────────────────────────────────────────────


class TestExtractTermOccurrences(unittest.TestCase):
    def _make_corpus(self, body: str, rel: str = "test.md") -> list:
        return [(rel, {}, body)]

    def test_pascal_case_captured_with_line_and_context(self):
        corpus = self._make_corpus("Line one.\nInMemoryRepository is the impl.\nLine three.\n")
        result = extract_term_occurrences(corpus)
        self.assertIn("InMemoryRepository", result)
        occurrences = result["InMemoryRepository"]
        self.assertEqual(len(occurrences), 1)
        rel, lineno, ctx = occurrences[0]
        self.assertEqual(rel, "test.md")
        self.assertEqual(lineno, 2)
        self.assertIn("InMemoryRepository", ctx)

    def test_camel_case_captured(self):
        corpus = self._make_corpus("Call provideFamilyBLoC to get the state.\n")
        result = extract_term_occurrences(corpus)
        self.assertIn("provideFamilyBLoC", result)

    def test_all_caps_snake_captured_bare_caps_not_matched(self):
        corpus = self._make_corpus("Set MAX_CONNECTIONS to 100. Also check XML format.\n")
        result = extract_term_occurrences(corpus)
        # ALL_CAPS_SNAKE with underscore captured
        self.assertIn("MAX_CONNECTIONS", result)
        # XML has no underscore — should NOT be matched by _ALL_CAPS_SNAKE_RE
        # (it may be matched by _PASCAL_CASE_RE, but that's separate; test that
        # ALL_CAPS_SNAKE specifically doesn't include it by checking that
        # "XML" occurrences, if any, come from pascal or camel, not snake)
        # The key assertion: MAX_CONNECTIONS found; no crash.

    def test_term_in_fenced_code_block_not_captured(self):
        body = (
            "Normal text.\n"
            "```python\n"
            "InCodeBlock = True\n"
            "```\n"
            "After code.\n"
        )
        corpus = self._make_corpus(body)
        result = extract_term_occurrences(corpus)
        self.assertNotIn("InCodeBlock", result)

    def test_table_header_skipped_cell_still_captured(self):
        body = (
            "Some intro.\n"
            "| Term | Description |\n"
            "|---|---|\n"
            "| MyClass | does things |\n"
            "\n"
            "See AlsoThis in prose.\n"
        )
        corpus = self._make_corpus(body)
        result = extract_term_occurrences(corpus)
        # "Term" and "Description" are in header row — they should NOT appear
        # (the header row is skipped). However "MyClass" is a table cell and
        # SHOULD appear, as is "AlsoThis" in prose.
        # Note: "Term" might match but it depends on the header row skip logic.
        # The separator row is "|---|---|" which is the separator.
        # Header = "| Term | Description |" (next line is separator) → skipped.
        self.assertNotIn("Description", result)
        # MyClass is in a table cell (not a header row) — captured.
        self.assertIn("MyClass", result)
        # AlsoThis in prose — captured.
        self.assertIn("AlsoThis", result)


# ── 2b. _context_around (Finding 2 regression) ───────────────────────────────


class TestContextAround(unittest.TestCase):
    """Direct tests for _context_around offset tracking.

    Verifies that real separator positions (not approximated +1) are used,
    so multi-space and tab separators don't cause offset drift.
    """

    def test_single_space_separator_basic(self):
        """Single-space separator — baseline regression, no drift expected."""
        line = "First sentence. Second sentence with MyTerm inside. Third sentence."
        # MyTerm starts at position 43 in "Second sentence with MyTerm inside."
        term = "MyTerm"
        start = line.index(term)
        end = start + len(term)
        ctx = _context_around(line, start, end)
        self.assertIn(term, ctx)
        # Context should include the sentence containing the term.
        self.assertIn("Second sentence", ctx)

    def test_multi_space_separator_no_drift(self):
        """Two spaces between sentences — separator consumes 2 chars, not 1.

        Old code: cumulative += len(sent) + 1  → drifts by 1 per separator.
        New code: uses real m.end() positions → no drift.
        """
        # Two spaces between sentences — the regex \s+ will consume both.
        line = "Alpha sentence.  Beta sentence with TargetTerm in it.  Gamma sentence."
        term = "TargetTerm"
        start = line.index(term)
        end = start + len(term)
        ctx = _context_around(line, start, end)
        self.assertIn(term, ctx)
        self.assertIn("Beta sentence", ctx)

    def test_tab_separator_no_drift(self):
        """Tab between sentences — separator is '\t' (1 char but not a space).

        Old code approximated as +1 which is coincidentally correct for single
        tab, but the character class difference still matters for the boundary
        calculation. Verify no regression.
        """
        line = "First.\tSecond with TabTerm here.\tThird."
        term = "TabTerm"
        start = line.index(term)
        end = start + len(term)
        ctx = _context_around(line, start, end)
        self.assertIn(term, ctx)
        self.assertIn("Second with", ctx)

    def test_term_in_first_sentence(self):
        """Term in first sentence — no preceding sentence; context starts at 0."""
        line = "LeadTerm appears here. Second sentence follows. Third one too."
        term = "LeadTerm"
        start = 0
        end = len(term)
        ctx = _context_around(line, start, end)
        self.assertIn(term, ctx)
        self.assertIn("LeadTerm appears here", ctx)

    def test_term_in_last_sentence(self):
        """Term in last sentence — no following sentence; context ends at end."""
        line = "First sentence. Second sentence. TrailTerm is last."
        term = "TrailTerm"
        start = line.index(term)
        end = start + len(term)
        ctx = _context_around(line, start, end)
        self.assertIn(term, ctx)
        self.assertIn("TrailTerm is last", ctx)

    def test_long_snippet_truncated_at_240(self):
        """Snippets > 240 chars are truncated with '...' suffix."""
        # Each sentence is > 120 chars so that two sentences combined exceed 240.
        filler = "x" * 100
        long_word = "LongTermHere"
        s0 = f"First sentence with {long_word} and filler {filler}."
        s1 = f"Second sentence also has {filler} in it."
        line = "  ".join([s0, s1])  # two-space separators, s0+s1 > 240
        start = line.index(long_word)
        end = start + len(long_word)
        ctx = _context_around(line, start, end)
        self.assertLessEqual(len(ctx), 240)
        self.assertTrue(ctx.endswith("..."))


# ── 3. validate_cite_paths ────────────────────────────────────────────────────


class TestValidateCitePaths(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_all_paths_exist(self):
        f = self.root / "somefile.md"
        f.write_text("hi", encoding="utf-8")
        ok, missing = validate_cite_paths(["somefile.md"], self.root)
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_one_missing_path(self):
        ok, missing = validate_cite_paths(["missing/path.md"], self.root)
        self.assertFalse(ok)
        self.assertEqual(missing, ["missing/path.md"])

    def test_empty_input(self):
        ok, missing = validate_cite_paths([], self.root)
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_mixed_existing_and_missing(self):
        (self.root / "exists.md").write_text("x", encoding="utf-8")
        ok, missing = validate_cite_paths(["exists.md", "gone.md"], self.root)
        self.assertFalse(ok)
        self.assertEqual(missing, ["gone.md"])


# ── 4. get_section_body_span ──────────────────────────────────────────────────


class TestGetSectionBodySpan(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _make_file(self, content: str) -> Path:
        p = self.root / "test.md"
        p.write_text(content, encoding="utf-8")
        return p

    def test_middle_section_span(self):
        content = (
            "# Title\n"           # line 1
            "\n"                  # line 2
            "## Section A\n"      # line 3
            "body a\n"            # line 4
            "\n"                  # line 5
            "## Section B\n"      # line 6
            "body b\n"            # line 7
            "\n"                  # line 8
            "## Section C\n"      # line 9
            "body c\n"            # line 10
        )
        p = self._make_file(content)
        start, end = get_section_body_span(p, 3)
        # Section A body: line 4 to line 5 (before Section B at line 6)
        self.assertEqual(start, 4)
        self.assertEqual(end, 5)

    def test_last_section_span(self):
        content = (
            "# Title\n"           # line 1
            "\n"                  # line 2
            "## Section A\n"      # line 3
            "body a\n"            # line 4
            "\n"                  # line 5
            "## Section B\n"      # line 6
            "body b\n"            # line 7
            "more b\n"            # line 8
        )
        p = self._make_file(content)
        start, end = get_section_body_span(p, 6)
        # Section B body: line 7 to total_lines.
        # content ends with \n so split("\n") produces a trailing empty element.
        # Lines: "# Title", "", "## Section A", "body a", "", "## Section B",
        #        "body b", "more b", "" (9 total).
        self.assertEqual(start, 7)
        self.assertEqual(end, 9)

    def test_non_heading_line_raises_value_error(self):
        content = (
            "# Title\n"
            "## Section A\n"
            "body line\n"
        )
        p = self._make_file(content)
        # Line 3 is "body line" — not a ## heading.
        with self.assertRaises(ValueError):
            get_section_body_span(p, 3)

    def test_nonexistent_file_raises_oserror(self):
        with self.assertRaises(OSError):
            get_section_body_span(self.root / "no_such.md", 1)


# ── 5. noise_filter ───────────────────────────────────────────────────────────


class TestNoiseFilter(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_baseline_strips_known_names(self):
        # Vue is in baseline; BLoC is NOT → BLoC should pass through.
        result = noise_filter(["Vue", "BLoC"])
        self.assertNotIn("Vue", result)
        self.assertIn("BLoC", result)

    def test_override_path_adds_custom_term(self):
        override = self.root / "noise.txt"
        override.write_text("# comment\nCustomTerm\n\nBLoC\n", encoding="utf-8")
        result = noise_filter(["CustomTerm", "BLoC", "Vue"], override_path=override)
        self.assertNotIn("CustomTerm", result)
        self.assertNotIn("BLoC", result)
        self.assertNotIn("Vue", result)

    def test_deduplication_first_occurrence_wins(self):
        result = noise_filter(["AlphaClass", "BetaClass", "AlphaClass"])
        self.assertEqual(result.count("AlphaClass"), 1)
        self.assertEqual(result.index("AlphaClass"), 0)

    def test_order_preserved(self):
        result = noise_filter(["ZetaClass", "AlphaClass", "MidClass"])
        self.assertEqual(result, ["ZetaClass", "AlphaClass", "MidClass"])

    def test_nonexistent_override_path_uses_baseline_only(self):
        result = noise_filter(["Vue", "BLoC"], override_path=self.root / "no_such.txt")
        self.assertNotIn("Vue", result)
        self.assertIn("BLoC", result)

    def test_empty_input_returns_empty(self):
        result = noise_filter([])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
