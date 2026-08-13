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
  read_memory_excerpt           -- absent, shorter-than-N, longer-than-N,
                                   exact-equality against the readlines()
                                   reference behaviour
  read_memory_digest            -- absent -> None, present-empty -> "",
                                   interleaved blank lines skipped not
                                   counted toward n
  read_memory_context            -- the combined single-read accessor;
                                   agreement with the individual functions
                                   and exactly-one-read behaviour
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

from _shared import memory as memory_module  # noqa: E402
from _shared.memory import (  # noqa: E402
    DEFAULT_DIGEST_LINES,
    DEFAULT_EXCERPT_LINES,
    MEMORY_RELATIVE_PATH,
    MEMORY_STATE_ABSENT,
    MEMORY_STATE_ENUM,
    MEMORY_STATE_KEY,
    MEMORY_STATE_POPULATED,
    MEMORY_STATE_STUB,
    _is_populated_line,
    _read_lines,
    _read_text,
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

    def test_default_n_is_40(self):
        self.assertEqual(DEFAULT_EXCERPT_LINES, 40)

    def test_shorter_than_n_returns_whole_file(self):
        content = "line1\nline2\nline3\n"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_excerpt(root, n=40)
            with open(
                os.path.join(root, MEMORY_RELATIVE_PATH), encoding="utf-8"
            ) as fh:
                expected = "".join(fh.readlines()[:40])
            self.assertEqual(result, expected)
            self.assertEqual(result, content)

    def test_longer_than_n_truncates_exactly(self):
        content = "".join("line{0}\n".format(i) for i in range(100))
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_excerpt(root, n=40)
            with open(
                os.path.join(root, MEMORY_RELATIVE_PATH), encoding="utf-8"
            ) as fh:
                expected = "".join(fh.readlines()[:40])
            self.assertEqual(result, expected)
            self.assertEqual(result.count("\n"), 40)

    def test_exact_equality_against_readlines_reference_shape(self):
        # No-trailing-newline last line, mixed content -- exercise the
        # reference behaviour "".join(fh.readlines()[:N]) exactly.
        content = "# Heading\n\n<!-- comment -->\ncontent no trailing newline"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_excerpt(root, n=2)
            with open(
                os.path.join(root, MEMORY_RELATIVE_PATH), encoding="utf-8"
            ) as fh:
                expected = "".join(fh.readlines()[:2])
            self.assertEqual(result, expected)
            self.assertEqual(result, "# Heading\n\n")

    def test_custom_n_respected(self):
        content = "a\nb\nc\nd\ne\n"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            self.assertEqual(read_memory_excerpt(root, n=2), "a\nb\n")


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
        real_stub_text = _REAL_STUB_PATH.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, real_stub_text)
            result = read_memory_context(root)
            self.assertTrue(result["present"])
            self.assertEqual(result[MEMORY_STATE_KEY], MEMORY_STATE_STUB)
            self.assertEqual(result["excerpt"], real_stub_text)

    def test_populated(self):
        content = "# Heading\n<!-- comment -->\n- A real lesson.\n"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_context(root)
            self.assertTrue(result["present"])
            self.assertEqual(result[MEMORY_STATE_KEY], MEMORY_STATE_POPULATED)
            self.assertEqual(result["excerpt"], content)

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
        content = "a\nb\nc\nd\ne\n"
        with tempfile.TemporaryDirectory() as root:
            _write(root, MEMORY_RELATIVE_PATH, content)
            result = read_memory_context(root, excerpt_lines=2)
            self.assertEqual(result["excerpt"], "a\nb\n")

    def test_agreement_with_individual_functions_across_fixtures(self):
        # Belt-and-braces against the combined accessor and the three
        # single-purpose functions drifting apart on the same content.
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


if __name__ == "__main__":
    unittest.main()
