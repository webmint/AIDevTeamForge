"""Tests for src/devforge/lib/_shared/memory.py.

Real-fixture discipline: the "stub" state is proven against the ACTUAL
shipped installer stub at src/devforge/memory.md, read from disk -- not a
hand-authored approximation. If that stub's content ever grows a real
line, this is the test that must catch it.

Coverage:
  memory_path                  -- path join shape
  MEMORY_STATE_KEY / MEMORY_STATE_ENUM -- stable exported names/values
  _read_lines / _read_text     -- direct coverage of the two file-read
                                   primitives (absent -> None; present ->
                                   correct shape)
  _scan_lines                  -- the comment-state-aware content scan,
                                   incl. multi-line HTML comment blocks
  probe_memory_state           -- absent / stub (real fixture) / stub
                                   (0-byte) / stub (blank-only) / stub
                                   (multi-line comment) / populated
  memory_present                -- True/False
  read_memory_excerpt           -- absent, shorter-than-budget,
                                   longer-than-budget (single-section
                                   newest-wins truncation), custom n
  read_memory_digest            -- absent -> None, present-empty -> "",
                                   interleaved blank lines skipped not
                                   counted toward n
  read_memory_context            -- the combined single-read accessor;
                                   agreement with the individual functions
                                   and exactly-one-read behaviour
  _render_excerpt (plan 79 Phase 1) -- the section-aware excerpt renderer
                                   shared by read_memory_excerpt() and
                                   read_memory_context(): preamble drop,
                                   EXCLUDED_MEMORY_SECTIONS drop, empty-
                                   section drop, blank-edge normalization,
                                   equal-share + single-pass redistribution
                                   budget allocation, newest-lines-survive
                                   truncation with a declared marker,
                                   real-fixture stub/receipts/lesson cases
                                   (receipts fixture round-tripped through
                                   the real _implement/_cmds_session.py
                                   writer), unknown-section inclusion,
                                   budget<=0, and the two functions'
                                   agreement on identical fixtures
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# ---------------------------------------------------------------------------
# Path setup (mirrors the pattern in tests/lib/_shared/test_feature_scope.py)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _implement._cmds_session import (  # noqa: E402
    _append_under_section,
    _build_memory_entry,
)
from _shared import memory as memory_module  # noqa: E402
from _shared.memory import (  # noqa: E402
    DEFAULT_DIGEST_LINES,
    DEFAULT_EXCERPT_LINES,
    EXCLUDED_MEMORY_SECTIONS,
    MEMORY_RELATIVE_PATH,
    MEMORY_STATE_ABSENT,
    MEMORY_STATE_ENUM,
    MEMORY_STATE_KEY,
    MEMORY_STATE_POPULATED,
    MEMORY_STATE_STUB,
    _EXCERPT_TRUNCATION_MARKER,
    _is_populated_line,
    _read_lines,
    _read_text,
    _render_excerpt,
    _scan_lines,
    memory_path,
    memory_present,
    probe_memory_state,
    read_memory_context,
    read_memory_digest,
    read_memory_excerpt,
)

# The real shipped installer stub -- every consumer install starts with this
# exact file at .devforge/memory.md.
_REAL_STUB_PATH = _REPO_ROOT / "src" / "devforge" / "memory.md"


def _render(text, budget):
    # type: (str, int) -> str
    """Convenience wrapper: run _render_excerpt() over a plain text fixture
    without a temp-file round trip (used for algorithm-level assertions
    that don't need a real file on disk).
    """
    return _render_excerpt(text.splitlines(keepends=True), budget)


def _write(root, relpath, content):
    # type: (str, str, str) -> None
    full = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)


# ---------------------------------------------------------------------------
# memory_path
# ---------------------------------------------------------------------------


class TestMemoryPath(unittest.TestCase):
    def test_joins_relative_path_onto_root(self):
        # Expected value built via MEMORY_RELATIVE_PATH (memory_path()'s own
        # join input), NOT via a separately-reconstructed 3-piece
        # os.path.join -- reconstructing "root", ".devforge", "memory.md"
        # piecewise and MEMORY_RELATIVE_PATH's now-hardcoded forward-slash
        # literal are joined via different code paths and can diverge on a
        # backslash-separator platform (os.path.join(root, ".devforge/memory.md")
        # yields a MIXED-separator string there, distinct from
        # os.path.join(root, ".devforge", "memory.md")'s pure-backslash one).
        # This test's job is "memory_path() joins root onto
        # MEMORY_RELATIVE_PATH", not "MEMORY_RELATIVE_PATH looks like a
        # 3-piece join" -- that invariant is pinned separately below.
        self.assertEqual(
            memory_path("/work/install"),
            os.path.join("/work/install", MEMORY_RELATIVE_PATH),
        )

    def test_relative_path_constant_is_forward_slash_literal(self):
        # Regression pin (not just an instance check): MEMORY_RELATIVE_PATH
        # must be a hardcoded forward-slash literal, matching the
        # forward-slash convention every other path literal in this
        # framework uses -- NOT os.path.join(".devforge", "memory.md"),
        # which is platform-dependent (backslash-joined on native Windows).
        # At least one consumer (_specify/_cmds_phase01.py's
        # cmd_record_input_read) does an EXACT STRING COMPARISON against
        # this constant, which a platform-derived value cannot satisfy on
        # every platform at once. See also
        # tests/lib/test_specify_helper.py's
        # test_memory_relative_path_matches_mandatory_read_literal, which
        # pins the cross-module half of this same invariant (this constant
        # vs. _specify's PHASE1_MANDATORY_READS entry).
        self.assertEqual(MEMORY_RELATIVE_PATH, ".devforge/memory.md")
        self.assertNotIn("\\", MEMORY_RELATIVE_PATH)

    def test_relative_workspace_root(self):
        self.assertEqual(
            memory_path("relative/root"),
            os.path.join("relative/root", MEMORY_RELATIVE_PATH),
        )


# ---------------------------------------------------------------------------
# Exported state names/values
# ---------------------------------------------------------------------------


class TestStateConstants(unittest.TestCase):
    def test_memory_state_key_literal(self):
        # Downstream command specs + a maintainer-side gate key on this
        # exact string -- pin it.
        self.assertEqual(MEMORY_STATE_KEY, "memory_state")

    def test_state_enum_exactly_three_values_in_order(self):
        self.assertEqual(
            MEMORY_STATE_ENUM,
            (MEMORY_STATE_ABSENT, MEMORY_STATE_STUB, MEMORY_STATE_POPULATED),
        )
        self.assertEqual(len(MEMORY_STATE_ENUM), 3)

    def test_state_values_are_the_documented_strings(self):
        self.assertEqual(MEMORY_STATE_ABSENT, "absent")
        self.assertEqual(MEMORY_STATE_STUB, "stub")
        self.assertEqual(MEMORY_STATE_POPULATED, "populated")


# ---------------------------------------------------------------------------
# _is_populated_line predicate
# ---------------------------------------------------------------------------


class TestIsPopulatedLine(unittest.TestCase):
    def test_blank_line_false(self):
        self.assertFalse(_is_populated_line(""))
        self.assertFalse(_is_populated_line("   \n"))
        self.assertFalse(_is_populated_line("\t\n"))

    def test_heading_false(self):
        self.assertFalse(_is_populated_line("# Project Memory\n"))
        self.assertFalse(_is_populated_line("## Known Pitfalls\n"))
        self.assertFalse(_is_populated_line("###### deep heading\n"))
        self.assertFalse(_is_populated_line("  ## indented heading\n"))

    def test_html_comment_false(self):
        self.assertFalse(_is_populated_line("<!-- Populated during work -->\n"))
        self.assertFalse(_is_populated_line("  <!-- indented comment -->  \n"))

    def test_real_content_true(self):
        self.assertTrue(_is_populated_line("- Use X pattern for Y.\n"))
        self.assertTrue(_is_populated_line("Prose lesson line.\n"))

    def test_content_with_trailing_inline_comment_true(self):
        # Not a WHOLE-line comment -- real content precedes it.
        self.assertTrue(_is_populated_line("Some text <!-- note -->\n"))


# ---------------------------------------------------------------------------
# _scan_lines -- the comment-state-aware content scan
# ---------------------------------------------------------------------------


class TestScanLines(unittest.TestCase):
    def test_empty_list_false(self):
        self.assertFalse(_scan_lines([]))

    def test_same_line_open_and_close_false(self):
        # Existing behaviour (single-line comment) must not regress.
        self.assertFalse(_scan_lines(["<!-- a whole-line comment -->\n"]))

    def test_same_line_open_and_close_with_indentation_false(self):
        self.assertFalse(_scan_lines(["  <!-- indented comment -->  \n"]))

    def test_plain_content_line_true(self):
        self.assertTrue(_scan_lines(["just a plain lesson line\n"]))

    def test_heading_only_false(self):
        self.assertFalse(_scan_lines(["# Heading\n", "## Sub\n"]))

    def test_multiline_comment_interior_lines_not_scored_as_content(self):
        # The exact bug demonstrated in the review finding: a comment that
        # opens and closes on DIFFERENT lines must not have its interior
        # lines scored as content.
        lines = [
            "# Heading\n",
            "<!--\n",
            "This is interior comment text\n",
            "spanning lines\n",
            "-->\n",
        ]
        self.assertFalse(_scan_lines(lines))

    def test_opener_with_content_before_it_on_same_line_true(self):
        # Content BEFORE the opener counts, regardless of what follows.
        self.assertTrue(_scan_lines(["real content <!-- trailing\n"]))

    def test_opener_with_content_after_it_unterminated_false(self):
        # "<!-- note" with nothing before the opener and no closer at all
        # -- the "note" text is inside the (unterminated) comment and must
        # not count.
        self.assertFalse(_scan_lines(["<!-- note\n"]))

    def test_closer_with_trailing_content_counts_as_content(self):
        lines = [
            "<!--\n",
            "hidden interior text\n",
            "--> real content\n",
        ]
        self.assertTrue(_scan_lines(lines))

    def test_unterminated_comment_runs_to_eof_false(self):
        lines = [
            "<!--\n",
            "this never surfaces\n",
            "nor does this\n",
        ]
        self.assertFalse(_scan_lines(lines))

    def test_multiple_comment_blocks_with_real_content_between_true(self):
        lines = [
            "# Heading\n",
            "<!--\n",
            "comment block 1\n",
            "interior\n",
            "-->\n",
            "some real content\n",
            "<!--\n",
            "comment block 2\n",
            "-->\n",
        ]
        self.assertTrue(_scan_lines(lines))

    def test_multiple_comment_blocks_with_no_content_anywhere_false(self):
        lines = [
            "# Heading\n",
            "<!--\n",
            "comment block 1\n",
            "-->\n",
            "<!--\n",
            "comment block 2\n",
            "-->\n",
        ]
        self.assertFalse(_scan_lines(lines))


# ---------------------------------------------------------------------------
# _read_lines / _read_text -- direct coverage of the file-read primitives
# ---------------------------------------------------------------------------


class TestReadLinesPrimitive(unittest.TestCase):
    def test_absent_returns_none(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(_read_lines(os.path.join(root, "nope.md")))

    def test_present_returns_list_with_terminators_preserved(self):
        content = "line1\nline2\nline3"
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "f.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            result = _read_lines(path)
            self.assertEqual(result, ["line1\n", "line2\n", "line3"])

    def test_present_empty_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "f.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("")
            self.assertEqual(_read_lines(path), [])

    def test_unreadable_directory_returns_none(self):
        # Passing a directory path (not a file) raises OSError on open() ->
        # must return None, not propagate.
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(_read_lines(root))


class TestReadTextPrimitive(unittest.TestCase):
    def test_absent_returns_none(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(_read_text(os.path.join(root, "nope.md")))

    def test_present_returns_full_string(self):
        content = "line1\nline2\nline3\n"
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "f.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            self.assertEqual(_read_text(path), content)

    def test_present_empty_file_returns_empty_string(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "f.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("")
            self.assertEqual(_read_text(path), "")

    def test_unreadable_directory_returns_none(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(_read_text(root))


# ---------------------------------------------------------------------------
# probe_memory_state
# ---------------------------------------------------------------------------


class TestProbeMemoryState(unittest.TestCase):
    def test_absent_when_no_file(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_ABSENT)

    def test_absent_when_devforge_dir_missing_entirely(self):
        with tempfile.TemporaryDirectory() as root:
            # root exists but has nothing inside it at all.
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_ABSENT)

    def test_stub_against_real_shipped_stub_fixture(self):
        # Real-producer round-trip: read the actual installer stub bytes,
        # not a hand-authored approximation.
        self.assertTrue(
            _REAL_STUB_PATH.is_file(),
            "src/devforge/memory.md must exist for this test to be meaningful",
        )
        real_stub_text = _REAL_STUB_PATH.read_text(encoding="utf-8")

        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, real_stub_text)
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_STUB)

    def test_stub_when_file_completely_empty(self):
        # Design choice (documented in memory.py): a 0-byte present file
        # probes as STUB, not ABSENT -- indistinguishable in usefulness
        # from the shipped stub. ABSENT is reserved for "no file at all".
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, "")
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_STUB)

    def test_stub_when_file_only_blank_lines(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, "\n\n   \n\t\n")
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_STUB)

    def test_populated_with_heading_comment_and_one_content_line(self):
        content = (
            "# Project Memory\n"
            "<!-- Populated during constitute -->\n"
            "- Always validate input at the API boundary.\n"
        )
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_POPULATED)

    def test_populated_when_only_content_no_headings(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, "just a plain lesson line\n")
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_POPULATED)

    def test_stub_when_only_a_multiline_html_comment(self):
        # Regression for the review finding: a comment whose "<!--" and
        # "-->" are on DIFFERENT lines must not have its interior scored
        # as content -- this file has zero real lessons and must probe
        # "stub", not "populated".
        content = (
            "# Heading\n"
            "<!--\n"
            "This is interior comment text\n"
            "spanning lines\n"
            "-->\n"
        )
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_STUB)

    def test_populated_when_real_content_follows_a_multiline_comment(self):
        content = (
            "# Heading\n"
            "<!--\n"
            "interior comment text\n"
            "-->\n"
            "- A real lesson line.\n"
        )
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_POPULATED)


# ---------------------------------------------------------------------------
# memory_present
# ---------------------------------------------------------------------------


class TestMemoryPresent(unittest.TestCase):
    def test_false_when_absent(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(memory_present(root))

    def test_true_when_present_even_if_empty(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, "")
            self.assertTrue(memory_present(root))

    def test_true_when_populated(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, "a real lesson\n")
            self.assertTrue(memory_present(root))


# ---------------------------------------------------------------------------
# read_memory_excerpt
# ---------------------------------------------------------------------------


class TestReadMemoryExcerpt(unittest.TestCase):
    def test_absent_returns_empty_string(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(read_memory_excerpt(root), "")

    def test_default_n_is_120(self):
        # RE-PIN (was test_default_n_is_40, DEFAULT_EXCERPT_LINES == 40):
        # plan 79 OQ-1 raises the excerpt budget to 120 CONTENT lines as
        # part of moving from a positional first-N-raw-lines slice to a
        # section-aware, content-counted budget -- 40 was the old
        # positional line count, not a content-line budget, so the two
        # numbers are not directly comparable; this pins the new value.
        self.assertEqual(DEFAULT_EXCERPT_LINES, 120)

    def test_shorter_than_budget_returns_whole_section_untruncated(self):
        # Was test_shorter_than_n_returns_whole_file, pinned against a
        # headingless fixture and readlines()[:40]. Under section-aware
        # rendering a fixture with NO "## " heading is 100% preamble and
        # would render "" regardless of n (see
        # test_content_without_double_hash_heading_is_all_preamble below)
        # -- that is a DIFFERENT, now-covered case, not this one. This
        # test's surviving intent -- "content shorter than the budget
        # comes back whole, untruncated" -- is re-fixtured with a real
        # "## " section so the section-aware path is actually exercised.
        content = "## Lessons\nline1\nline2\nline3\n"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_excerpt(root, n=40)
            self.assertEqual(result, content)
            self.assertNotIn("[...", result)  # no truncation marker

    def test_longer_than_budget_keeps_last_n_content_lines(self):
        # RETIRED shape (was test_longer_than_n_truncates_exactly, which
        # pinned readlines()[:40] positional truncation and a raw
        # newline count). Plan 79 D1 removes the positional read entirely,
        # so that reference shape no longer applies. Re-fixtured as a
        # single retained section (k=1, no budget redistribution to
        # entangle with) to isolate "does within-section truncation keep
        # the newest lines and declare the drop" -- the multi-section
        # redistribution case is covered separately by
        # TestRenderExcerpt.test_budget_redistributed_in_file_order.
        content = "## Lessons\n" + "".join(
            "line{0}\n".format(i) for i in range(100)
        )
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_excerpt(root, n=40)
            expected_marker = _EXCERPT_TRUNCATION_MARKER.format(dropped=60)
            expected_kept = "".join("line{0}\n".format(i) for i in range(60, 100))
            self.assertEqual(
                result, "## Lessons\n" + expected_marker + "\n" + expected_kept
            )
            # Newest (highest-numbered, last-appended) lines survive.
            self.assertIn("line99\n", result)
            self.assertNotIn("line0\n", result)
            self.assertNotIn("line59\n", result)

    def test_trailing_newline_normalized_when_source_has_none(self):
        # RETIRED shape (was test_exact_equality_against_readlines_reference_
        # shape, which pinned "".join(fh.readlines()[:N]) exactly -- the
        # positional reference behaviour plan 79 D1 removes). Its surviving
        # intent -- exercise a no-trailing-newline last line and mixed
        # content -- is re-purposed to pin the new renderer's own
        # normalization guarantee: a non-empty result always ends with
        # exactly one "\n", even when the source's last line has none.
        content = "## Heading\n\n<!-- comment -->\ncontent no trailing newline"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_excerpt(root, n=40)
            self.assertEqual(
                result, "## Heading\n<!-- comment -->\ncontent no trailing newline\n"
            )
            self.assertTrue(result.endswith("\n"))
            self.assertFalse(result.endswith("\n\n"))

    def test_custom_n_respected(self):
        content = "## H\na\nb\nc\nd\ne\n"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            expected_marker = _EXCERPT_TRUNCATION_MARKER.format(dropped=3)
            self.assertEqual(
                read_memory_excerpt(root, n=2),
                "## H\n" + expected_marker + "\nd\ne\n",
            )


# ---------------------------------------------------------------------------
# read_memory_digest
# ---------------------------------------------------------------------------


class TestReadMemoryDigest(unittest.TestCase):
    def test_absent_returns_none(self):
        with tempfile.TemporaryDirectory() as root:
            result = read_memory_digest(root)
            self.assertIsNone(result)

    def test_default_n_is_5(self):
        self.assertEqual(DEFAULT_DIGEST_LINES, 5)

    def test_present_empty_returns_empty_string_not_none(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, "")
            result = read_memory_digest(root)
            self.assertEqual(result, "")
            self.assertIsNotNone(result)

    def test_present_only_blank_lines_returns_empty_string(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, "\n\n   \n")
            self.assertEqual(read_memory_digest(root), "")

    def test_blank_lines_interleaved_are_skipped_not_counted(self):
        # 3 real lines separated by blanks; n=3 must return all three real
        # lines, NOT stop early because blanks consumed slots.
        content = "one\n\ntwo\n\n\nthree\n\nfour\n"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_digest(root, n=3)
            self.assertEqual(result, "one\ntwo\nthree")

    def test_fewer_non_blank_lines_than_n(self):
        content = "only one real line\n\n\n"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            self.assertEqual(read_memory_digest(root, n=5), "only one real line")

    def test_terminators_stripped_and_joined_with_newline(self):
        content = "alpha\nbeta\ngamma\ndelta\nepsilon\nzeta\n"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_digest(root, n=5)
            self.assertEqual(result, "alpha\nbeta\ngamma\ndelta\nepsilon")

    def test_against_real_shipped_stub_all_lines_are_headings_or_comments(self):
        # The real stub's digest reflects that ALL of its non-blank lines
        # are headings/comments in CONTENT, but read_memory_digest does not
        # filter by that predicate -- it only skips BLANK lines. Pin the
        # distinction: digest != populated-content filtering.
        real_stub_text = _REAL_STUB_PATH.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, real_stub_text)
            result = read_memory_digest(root, n=5)
            non_blank = [ln for ln in real_stub_text.splitlines() if ln.strip()]
            expected = "\n".join(non_blank[:5])
            self.assertEqual(result, expected)


# ---------------------------------------------------------------------------
# read_memory_context -- the combined single-read accessor
# ---------------------------------------------------------------------------


class TestReadMemoryContext(unittest.TestCase):
    def test_absent(self):
        with tempfile.TemporaryDirectory() as root:
            result = read_memory_context(root)
            self.assertEqual(
                result,
                {
                    "present": False,
                    MEMORY_STATE_KEY: MEMORY_STATE_ABSENT,
                    "excerpt": "",
                },
            )

    def test_stub_against_real_shipped_stub_fixture(self):
        # RE-PINNED: the excerpt used to equal the whole stub text
        # (positional first-N-raw-lines). Under section-aware rendering
        # every one of the stub's four sections holds only a whole-line
        # HTML comment -- no populated content -- so all four are dropped
        # as empty and the excerpt is "" (a deliberate behavior change:
        # four empty headings are not content worth showing).
        real_stub_text = _REAL_STUB_PATH.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, real_stub_text)
            result = read_memory_context(root)
            self.assertTrue(result["present"])
            self.assertEqual(result[MEMORY_STATE_KEY], MEMORY_STATE_STUB)
            self.assertEqual(result["excerpt"], "")

    def test_content_without_double_hash_heading_is_all_preamble(self):
        # Was test_populated, pinned against a headingless fixture
        # ("# Heading" is a SINGLE "#", not a "## " section boundary)
        # asserting the whole file surfaced as the excerpt. Under
        # section-aware rendering, text before the first "## " heading is
        # PREAMBLE and is dropped -- since this fixture has no "## "
        # heading at all, 100% of it is preamble and the excerpt is "",
        # even though probe_memory_state() (whole-file scan, untouched by
        # this change) still reports "populated" because of the real
        # lesson line. Renamed rather than silently keeping the old name
        # once its assertion flipped.
        content = "# Heading\n<!-- comment -->\n- A real lesson.\n"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_context(root)
            self.assertTrue(result["present"])
            self.assertEqual(result[MEMORY_STATE_KEY], MEMORY_STATE_POPULATED)
            self.assertEqual(result["excerpt"], "")

    def test_stub_multiline_comment_agrees_with_probe_memory_state(self):
        # Same fixture used to pin the Fix-1 regression -- the combined
        # accessor must agree with probe_memory_state on the SAME content.
        content = (
            "# Heading\n"
            "<!--\n"
            "interior comment text\n"
            "spanning lines\n"
            "-->\n"
        )
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_context(root)
            self.assertEqual(result[MEMORY_STATE_KEY], MEMORY_STATE_STUB)
            self.assertEqual(result[MEMORY_STATE_KEY], probe_memory_state(root))

    def test_custom_excerpt_lines_respected(self):
        # Re-fixtured with a real "## " section (a headingless fixture is
        # all preamble and would render "" regardless of excerpt_lines --
        # see test_content_without_double_hash_heading_is_all_preamble).
        content = "## H\na\nb\nc\nd\ne\n"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_context(root, excerpt_lines=2)
            expected_marker = _EXCERPT_TRUNCATION_MARKER.format(dropped=3)
            self.assertEqual(result["excerpt"], "## H\n" + expected_marker + "\nd\ne\n")

    def test_agreement_with_individual_functions_across_fixtures(self):
        # Belt-and-braces against the combined accessor and the three
        # single-purpose functions drifting apart on the same content.
        # KEPT AS-IS (plan 79): none of these fixtures contain a "## "
        # heading, so under section-aware rendering every one of them is
        # 100% preamble and both sides of the excerpt comparison below
        # legitimately agree on "" -- the assertion still proves the
        # SAME-CONTRACT invariant (read_memory_context()'s excerpt must
        # equal read_memory_excerpt()'s), it just does so on headingless
        # content. Non-trivial agreement across "## "-sectioned,
        # excluded-section, and receipts fixtures is covered separately by
        # TestSectionAwareAgreement below.
        fixtures = [
            "",
            "\n\n   \n",
            "# Heading\n<!-- comment -->\n",
            "- a real lesson\n",
            "# H\n<!--\ninterior\n-->\nreal content after\n",
        ]
        for content in fixtures:
            with self.subTest(content=content):
                with tempfile.TemporaryDirectory() as root:
                    _write(root, MEMORY_RELATIVE_PATH, content)
                    combined = read_memory_context(root)
                    self.assertEqual(combined["present"], memory_present(root))
                    self.assertEqual(
                        combined[MEMORY_STATE_KEY], probe_memory_state(root)
                    )
                    self.assertEqual(combined["excerpt"], read_memory_excerpt(root))

        # Absent case too.
        with tempfile.TemporaryDirectory() as root:
            combined = read_memory_context(root)
            self.assertEqual(combined["present"], memory_present(root))
            self.assertEqual(combined[MEMORY_STATE_KEY], probe_memory_state(root))
            self.assertEqual(combined["excerpt"], read_memory_excerpt(root))

    def test_performs_exactly_one_read(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, "some content\n")
            original = memory_module._read_lines
            calls = []

            def _counting_read_lines(path):
                calls.append(path)
                return original(path)

            with mock.patch.object(
                memory_module, "_read_lines", side_effect=_counting_read_lines
            ):
                memory_module.read_memory_context(root)

            self.assertEqual(len(calls), 1)


# ---------------------------------------------------------------------------
# _render_excerpt -- the section-aware renderer, direct algorithm coverage
# (plan 79 Phase 1). Public-function-level real-fixture coverage lives in
# TestSectionAwareRealFixtures / TestSectionAwareAgreement below; this class
# isolates individual algorithm steps against small, hand-built fixtures
# (per-step assertions don't need real-producer round-tripping -- only the
# receipts case does, per the repo's real-fixture discipline).
# ---------------------------------------------------------------------------


class TestRenderExcerpt(unittest.TestCase):
    def test_budget_zero_or_negative_returns_empty_string(self):
        lines = "## H\nreal line\n".splitlines(keepends=True)
        self.assertEqual(_render_excerpt(lines, 0), "")
        self.assertEqual(_render_excerpt(lines, -5), "")

    def test_empty_lines_list_returns_empty_string(self):
        self.assertEqual(_render_excerpt([], 120), "")

    def test_preamble_before_first_heading_is_dropped(self):
        content = "Some prose before any heading.\n\n## Real Section\nreal content line\n"
        result = _render(content, 120)
        self.assertNotIn("Some prose before any heading", result)
        self.assertEqual(result, "## Real Section\nreal content line\n")

    def test_content_without_double_hash_heading_is_all_preamble(self):
        # No "## " anywhere -- the entire file is preamble, dropped whole.
        self.assertEqual(_render("just prose, no heading at all\n", 120), "")

    def test_excluded_section_dropped_before_budget_and_without_marker(self):
        # The excluded section is absent from the output ENTIRELY -- no
        # heading, no content, and (unlike a budget truncation) no marker
        # either: exclusion is a silent source-level drop (D3), distinct
        # from budget truncation, which is always declared (D4).
        content = "## Task Outcomes\n- receipt line\n\n## Real\nreal line\n"
        self.assertEqual(EXCLUDED_MEMORY_SECTIONS, ("## Task Outcomes",))
        result = _render(content, 120)
        self.assertEqual(result, "## Real\nreal line\n")
        self.assertNotIn("Task Outcomes", result)
        self.assertNotIn("receipt line", result)
        self.assertNotIn("[...", result)

    def test_empty_section_dropped_heading_included(self):
        # "## Empty" carries only a whole-line HTML comment -- no populated
        # content per _scan_lines() -- so it and its heading are dropped.
        content = "## Empty\n<!-- just a comment -->\n\n## Real\nreal line\n"
        result = _render(content, 120)
        self.assertEqual(result, "## Real\nreal line\n")
        self.assertNotIn("Empty", result)

    def test_blank_edge_lines_stripped_interior_blank_kept(self):
        content = "## S\n\n\nfirst\n\nsecond\n\n\n"
        result = _render(content, 120)
        self.assertEqual(result, "## S\nfirst\n\nsecond\n")

    def test_triple_hash_heading_is_content_not_a_section_boundary(self):
        content = "## S\n### subheading is content\nreal line\n"
        result = _render(content, 120)
        self.assertEqual(result, "## S\n### subheading is content\nreal line\n")

    def test_unknown_section_included_by_default(self):
        # D3 Option A: EXCLUDED_MEMORY_SECTIONS is a denylist, not an
        # allowlist -- a heading this module has never seen still renders.
        content = "## Something Nobody Anticipated\nA line nobody expected.\n"
        result = _render(content, 120)
        self.assertEqual(
            result, "## Something Nobody Anticipated\nA line nobody expected.\n"
        )

    def test_budget_redistributed_in_file_order(self):
        # 3 populated sections (8/6/2 content lines), budget 10:
        #   share = 10 // 3 = 3
        #   alloc = [min(8,3), min(6,3), min(2,3)] = [3, 3, 2]  (sum 8)
        #   leftover = 2, granted in FILE ORDER: section A (room=5) takes
        #   both remaining units first -> alloc = [5, 3, 2] (sum 10).
        content = (
            "## Section A\n"
            + "".join("a-line-{0}\n".format(i) for i in range(8))
            + "\n"
            + "## Section B\n"
            + "".join("b-line-{0}\n".format(i) for i in range(6))
            + "\n"
            + "## Section C\n"
            + "".join("c-line-{0}\n".format(i) for i in range(2))
            + "\n"
        )
        result = _render(content, 10)
        marker3 = _EXCERPT_TRUNCATION_MARKER.format(dropped=3)
        expected = (
            "## Section A\n"
            + marker3
            + "\n"
            + "a-line-3\na-line-4\na-line-5\na-line-6\na-line-7\n"
            + "\n"
            + "## Section B\n"
            + marker3
            + "\nb-line-3\nb-line-4\nb-line-5\n"
            + "\n"
            + "## Section C\nc-line-0\nc-line-1\n"
        )
        self.assertEqual(result, expected)
        # Newest (last-appended) lines survive; earliest are dropped.
        self.assertIn("a-line-7", result)
        self.assertNotIn("a-line-0", result)
        self.assertNotIn("a-line-2", result)
        # Section C fit entirely inside its share -- untouched, no marker
        # (already pinned by the exact `expected` equality above).
        self.assertTrue(result.endswith("## Section C\nc-line-0\nc-line-1\n"))

    def test_section_with_zero_share_renders_heading_and_marker_only(self):
        # 5 sections x 5 content lines each, budget 3: share = 3 // 5 = 0,
        # so every section starts at alloc 0; the single redistribution
        # pass (file order) grants ALL 3 leftover units to the FIRST
        # section and none to the rest -- sections B-E get alloc 0 and
        # render as heading + marker only ("recorded, not shown", D4).
        content = "".join(
            "## Section {0}\n".format(letter)
            + "content-{0}-x\ncontent-{0}-y\ncontent-{0}-z\ncontent-{0}-w\ncontent-{0}-v\n".format(
                letter
            )
            + "\n"
            for letter in "ABCDE"
        )
        result = _render(content, 3)
        marker5 = _EXCERPT_TRUNCATION_MARKER.format(dropped=5)
        # Section A absorbed the leftover: alloc 3 of 5, dropped 2.
        marker2 = _EXCERPT_TRUNCATION_MARKER.format(dropped=2)
        self.assertIn(
            "## Section A\n" + marker2 + "\ncontent-A-z\ncontent-A-w\ncontent-A-v",
            result,
        )
        # Sections B-E: heading + marker only, zero content lines shown.
        for letter in "BCDE":
            self.assertIn("## Section {0}\n{1}".format(letter, marker5), result)
            self.assertNotIn("content-{0}-".format(letter), result)

    def test_result_ends_with_exactly_one_newline_when_nonempty(self):
        result = _render("## H\ncontent no trailing newline", 120)
        self.assertTrue(result.endswith("\n"))
        self.assertFalse(result.endswith("\n\n"))

    def test_empty_result_is_empty_string_not_newline(self):
        result = _render("just prose, no heading\n", 120)
        self.assertEqual(result, "")
        self.assertNotEqual(result, "\n")


# ---------------------------------------------------------------------------
# Real-fixture section-aware excerpt cases (plan 79 Phase 1, mandatory
# groups 1/2/3a/3b/5). The receipts fixture is round-tripped through the
# REAL memory.md writer (_implement/_cmds_session.py's _build_memory_entry
# + _append_under_section), not hand-authored -- the repo's real-fixture
# discipline. That writer is deleted by plan 79 Phase 2; the resulting
# bytes are pinned as a string literal in this same test (proven
# production-shaped here, while the writer still exists, so the pin
# survives the writer's removal).
# ---------------------------------------------------------------------------


class TestSectionAwareRealFixtures(unittest.TestCase):
    def _write_real_stub(self, root):
        # type: (str) -> str
        real_stub_text = _REAL_STUB_PATH.read_text(encoding="utf-8")
        self.assertTrue(
            _REAL_STUB_PATH.is_file(),
            "src/devforge/memory.md must exist for this test to be meaningful",
        )
        _write(root, MEMORY_RELATIVE_PATH, real_stub_text)
        return real_stub_text

    def test_stub_only_excerpt_is_empty_string(self):
        # Mandatory group 1: the real shipped stub has zero populated
        # lines in every section -> all four sections drop as empty ->
        # excerpt "". State stays "stub" (probe_memory_state untouched --
        # D6/mandatory group 8).
        with tempfile.TemporaryDirectory() as root:
            self._write_real_stub(root)
            self.assertEqual(read_memory_excerpt(root), "")
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_STUB)

    # The exact bytes _append_under_section() produces for 3 receipts
    # (tasks 001-003, feature 001-widget-catalog) appended onto the real
    # stub via cmd_update_session_state's own entry format. Proven equal
    # to the real writer's live output in
    # test_receipts_only_pinned_fixture_matches_real_writer below, in the
    # SAME test, so this pin is proven production-shaped while the writer
    # (deleted by plan 79 Phase 2) still exists.
    _RECEIPTS_ONLY_PINNED = (
        "# Project Memory\n"
        "\n"
        "## Architecture Decisions\n"
        "<!-- Populated as decisions are made — records WHY, not just what -->\n"
        "\n"
        "## Known Pitfalls\n"
        "<!-- Populated during work as mistakes are discovered -->\n"
        "\n"
        "## What Worked\n"
        "<!-- Patterns and approaches that solved problems well -->\n"
        "\n"
        "## What Failed\n"
        "<!-- Approaches that were tried and didn't work — avoid repeating these -->\n"
        "\n"
        "## Task Outcomes\n"
        "- **[Task 001 / 001-widget-catalog]**: Define types — completed. _(Task 001)_\n"
        "- **[Task 002 / 001-widget-catalog]**: Create repo — completed. _(Task 002)_\n"
        "- **[Task 003 / 001-widget-catalog]**: Build component — completed. _(Task 003)_\n"
    )

    def _build_receipts_only_fixture(self, target_path):
        # type: (Path) -> None
        """Apply 3 receipts to target_path via the REAL writer functions."""
        feature = "001-widget-catalog"
        titles = {
            "001": "Define types",
            "002": "Create repo",
            "003": "Build component",
        }
        for number in ("001", "002", "003"):
            entry = _build_memory_entry(feature, number, titles[number])
            _append_under_section(target_path, "## Task Outcomes", entry)

    def test_receipts_only_pinned_fixture_matches_real_writer(self):
        # Real-producer round trip: build the fixture with the actual
        # writer, then prove it equals the pinned literal above -- in the
        # SAME test, so the pin is verified production-shaped before it is
        # relied on by any other test.
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / MEMORY_RELATIVE_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(_REAL_STUB_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            self._build_receipts_only_fixture(target)
            produced = target.read_text(encoding="utf-8")
            self.assertEqual(produced, self._RECEIPTS_ONLY_PINNED)

    def test_receipts_only_excerpt_empty_but_state_populated(self):
        # Mandatory group 2: the ONLY populated content in this fixture
        # sits under "## Task Outcomes", which is on
        # EXCLUDED_MEMORY_SECTIONS -- excerpt is "" even though the file
        # is genuinely "populated" per probe_memory_state() (whole-file
        # scan, untouched). This is the accepted D6 divergence: a
        # receipts-only file probes "populated" while its excerpt renders
        # "" -- both assertions live in this one test, named for it.
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, self._RECEIPTS_ONLY_PINNED)
            self.assertEqual(read_memory_excerpt(root), "")
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_POPULATED)
            # Agreement (mandatory group 7) on this fixture too.
            self.assertEqual(
                read_memory_context(root)["excerpt"], read_memory_excerpt(root)
            )

    _LESSON_LINES = (
        "- 2026-08-17: Verify caught a null-check regression before the merge.\n"
        "- Root cause: input validation was skipped at the API boundary.\n"
    )

    def test_lesson_under_non_excluded_heading_surfaces_receipts_do_not(self):
        # Mandatory group 3a -- the plan's whole thesis: a later lesson
        # written under a real (non-excluded) heading must be visible in
        # the excerpt, and no receipt line may leak in alongside it. A run
        # where this passes trivially because the fixture carries no
        # receipts at all does not count -- this fixture is case 2's
        # receipts PLUS the lesson.
        content = self._RECEIPTS_ONLY_PINNED.replace(
            "## What Failed\n"
            "<!-- Approaches that were tried and didn't work — avoid repeating these -->\n"
            "\n",
            "## What Failed\n"
            "<!-- Approaches that were tried and didn't work — avoid repeating these -->\n"
            + self._LESSON_LINES
            + "\n",
        )
        self.assertNotEqual(content, self._RECEIPTS_ONLY_PINNED)  # sanity: replaced
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            excerpt = read_memory_excerpt(root)
            self.assertEqual(
                excerpt,
                "## What Failed\n"
                "<!-- Approaches that were tried and didn't work — avoid repeating these -->\n"
                + self._LESSON_LINES,
            )
            self.assertIn("Verify caught a null-check regression", excerpt)
            self.assertIn("Root cause: input validation", excerpt)
            self.assertNotIn("Task 001", excerpt)
            self.assertNotIn("Task 002", excerpt)
            self.assertNotIn("Task 003", excerpt)
            self.assertNotIn("Task Outcomes", excerpt)
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_POPULATED)
            self.assertEqual(
                read_memory_context(root)["excerpt"], read_memory_excerpt(root)
            )

    def test_lesson_appended_at_bare_eof_lands_in_excluded_section(self):
        # Mandatory group 3b: the SAME lesson text, but appended at bare
        # EOF (no heading of its own) -- it lands textually inside
        # "## Task Outcomes" (the last section in the file), so it is
        # EXCLUDED from the excerpt too (ratified D3 Option A: exclusion
        # is by section membership, not by line content). State still
        # reports "populated".
        content = self._RECEIPTS_ONLY_PINNED + self._LESSON_LINES
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            excerpt = read_memory_excerpt(root)
            self.assertEqual(excerpt, "")
            self.assertNotIn("Verify caught a null-check regression", excerpt)
            self.assertNotIn("Root cause: input validation", excerpt)
            self.assertEqual(probe_memory_state(root), MEMORY_STATE_POPULATED)
            self.assertEqual(
                read_memory_context(root)["excerpt"], read_memory_excerpt(root)
            )


# ---------------------------------------------------------------------------
# Agreement across every new plan-79 fixture (mandatory group 7) -- extends
# TestReadMemoryContext.test_agreement_with_individual_functions_across_
# fixtures, which stays on its own (headingless) fixtures unchanged.
# ---------------------------------------------------------------------------


class TestSectionAwareAgreement(unittest.TestCase):
    def test_agreement_across_all_new_section_aware_fixtures(self):
        fixtures = [
            # (content, excerpt_lines)
            (_REAL_STUB_PATH.read_text(encoding="utf-8"), DEFAULT_EXCERPT_LINES),
            (
                TestSectionAwareRealFixtures._RECEIPTS_ONLY_PINNED,
                DEFAULT_EXCERPT_LINES,
            ),
            ("## Something Nobody Anticipated\nA line nobody expected.\n", 120),
            ("Some prose before any heading.\n\n## Real\nreal line\n", 120),
            (
                "## Section A\n"
                + "".join("a-line-{0}\n".format(i) for i in range(8))
                + "\n## Section B\n"
                + "".join("b-line-{0}\n".format(i) for i in range(6))
                + "\n## Section C\n"
                + "".join("c-line-{0}\n".format(i) for i in range(2))
                + "\n",
                10,
            ),
        ]
        for content, excerpt_lines in fixtures:
            with self.subTest(content=content, excerpt_lines=excerpt_lines):
                with tempfile.TemporaryDirectory() as root:
                    _write(root, MEMORY_RELATIVE_PATH, content)
                    combined = read_memory_context(root, excerpt_lines=excerpt_lines)
                    individual = read_memory_excerpt(root, n=excerpt_lines)
                    self.assertEqual(combined["excerpt"], individual)
                    self.assertEqual(
                        combined[MEMORY_STATE_KEY], probe_memory_state(root)
                    )


if __name__ == "__main__":
    unittest.main()
