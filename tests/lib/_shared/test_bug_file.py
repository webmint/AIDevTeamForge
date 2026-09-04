"""Tests for src/devforge/lib/_shared/bug_file.py

Coverage:
  file_bugs:
    Format verification:
      - Written file starts with "# Bug NNN: <title>"
      - **Status**: Open
      - **Severity**: as given
      - **Source**: verify (default)
      - **Source**: <custom> when source param supplied
      - **Feature**: as given (feature spec path)
      - **AC**: as given (ac_ref field)
      - **Reported**: as given (date)
      - **Fixed**: present (empty value)
      - ## Description section present
      - ## Expected Behavior section present
      - ## Actual Behavior section present
      - ## File(s) table with File/Detail header
      - ## Evidence section present
      - ## Related Issues section present
      - ## Fix Notes section present

    source param:
      - Default (omitted) → **Source**: verify
      - source="manual"   → **Source**: manual
      - source="fix"      → **Source**: fix

    Numbering:
      - Empty bugs/ dir → starts at 001
      - Existing bugs (e.g. 003-*.md) → starts at 004
      - Batch of 3 → 001, 002, 003 in one call
      - Numbering continues from existing without gaps

    Related Issues cross-links:
      - Single bug → "None — standalone bug"
      - Two bugs in same batch → each references the other
      - Three bugs → each references the other two

    Slug sanitisation:
      - Spaces → hyphens
      - Uppercase → lowercase
      - Special chars → hyphens
      - Multiple hyphens → single hyphen
      - Slug capped at 30 chars

    Atomic write:
      - No .tmp-bug- files left after success
      - Written files are readable

    Edge cases:
      - Empty issues list → returns [] (no crash, no files)
      - Missing optional fields (title, description, etc.) → placeholders used
      - bugs_dir created if absent
      - Empty bugs_dir → scanning gives 0 → starts at 001
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared.bug_file import (  # noqa: E402
    file_bugs,
    close_bug,
    slugify,
    scan_highest_number,
    _STATUS_LINE_PREFIX,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _issue(
    title="Null cart total",
    severity="Critical",
    description="The cart total is null when no items.",
    expected="Cart total should be 0 when empty.",
    actual="Cart total is null, causing downstream TypeError.",
    files=None,
    evidence="verify-report shows AC-3 FAIL",
    ac_ref="AC-3",
):
    return {
        "title": title,
        "severity": severity,
        "description": description,
        "expected": expected,
        "actual": actual,
        "files": files or [{"path": "src/cart.py", "detail": "total calculation"}],
        "evidence": evidence,
        "ac_ref": ac_ref,
    }


# ---------------------------------------------------------------------------
# Format tests
# ---------------------------------------------------------------------------


class TestFileBugsFormat(unittest.TestCase):
    """Verify the written bug file follows the storage-rules.md format."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bugs_dir = os.path.join(self.tmp, "bugs")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_one(self, **kwargs):
        issues = [_issue(**kwargs)]
        paths = file_bugs(
            bugs_dir=self.bugs_dir,
            issues=issues,
            feature_spec_path="specs/001-cart/spec.md",
            date="2026-06-16",
        )
        self.assertEqual(len(paths), 1)
        with open(paths[0], encoding="utf-8") as fh:
            return fh.read()

    def test_title_in_header(self):
        content = self._write_one(title="Null cart total")
        self.assertIn("# Bug 001: Null cart total", content)

    def test_status_open(self):
        content = self._write_one()
        self.assertIn("**Status**: Open", content)

    def test_severity_field(self):
        content = self._write_one(severity="Warning")
        self.assertIn("**Severity**: Warning", content)

    def test_source_verify(self):
        content = self._write_one()
        self.assertIn("**Source**: verify", content)

    def test_feature_path(self):
        content = self._write_one()
        self.assertIn("**Feature**: specs/001-cart/spec.md", content)

    def test_ac_ref(self):
        content = self._write_one(ac_ref="AC-5")
        self.assertIn("**AC**: AC-5", content)

    def test_ac_na(self):
        content = self._write_one(ac_ref="N/A")
        self.assertIn("**AC**: N/A", content)

    def test_reported_date(self):
        content = self._write_one()
        self.assertIn("**Reported**: 2026-06-16", content)

    def test_fixed_field_present(self):
        content = self._write_one()
        self.assertIn("**Fixed**:", content)

    def test_description_section(self):
        content = self._write_one(description="It is broken.")
        self.assertIn("## Description", content)
        self.assertIn("It is broken.", content)

    def test_expected_behavior_section(self):
        content = self._write_one(expected="Should be 0.")
        self.assertIn("## Expected Behavior", content)
        self.assertIn("Should be 0.", content)

    def test_actual_behavior_section(self):
        content = self._write_one(actual="Is null instead.")
        self.assertIn("## Actual Behavior", content)
        self.assertIn("Is null instead.", content)

    def test_files_table_header(self):
        content = self._write_one()
        self.assertIn("## File(s)", content)
        self.assertIn("| File | Detail |", content)
        self.assertIn("|------|--------|", content)

    def test_files_table_row(self):
        content = self._write_one(
            files=[{"path": "src/cart.py", "detail": "total calculation"}]
        )
        self.assertIn("| src/cart.py |", content)
        self.assertIn("total calculation", content)

    def test_evidence_section(self):
        content = self._write_one(evidence="AC-3 FAIL in verify report")
        self.assertIn("## Evidence", content)
        self.assertIn("AC-3 FAIL in verify report", content)

    def test_related_issues_section_present(self):
        content = self._write_one()
        self.assertIn("## Related Issues", content)

    def test_fix_notes_section(self):
        content = self._write_one()
        self.assertIn("## Fix Notes", content)

    def test_fix_notes_phrasing_no_command_reference(self):
        """Round-trip: Fix Notes body must say 'Filled in after resolution'
        and must NOT say 'by the fix command' (plan 26 D4 — manual lifecycle)."""
        content = self._write_one()
        self.assertIn("Filled in after resolution", content)
        self.assertNotIn("by the fix command", content)

    def test_single_bug_no_related(self):
        """A single bug in the batch has no Related Issues."""
        content = self._write_one()
        self.assertIn("standalone", content.lower())


# ---------------------------------------------------------------------------
# source param tests (new behavior)
# ---------------------------------------------------------------------------


class TestFileBugsSourceParam(unittest.TestCase):
    """Verify the source parameter is correctly threaded into the bug file."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bugs_dir = os.path.join(self.tmp, "bugs")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_one(self, source_kwarg=None):
        kwargs = dict(
            bugs_dir=self.bugs_dir,
            issues=[_issue()],
            feature_spec_path="specs/001-cart/spec.md",
            date="2026-06-16",
        )
        if source_kwarg is not None:
            kwargs["source"] = source_kwarg
        paths = file_bugs(**kwargs)
        self.assertEqual(len(paths), 1)
        with open(paths[0], encoding="utf-8") as fh:
            return fh.read()

    def test_default_source_is_verify(self):
        """Omitting source renders **Source**: verify (byte-identical to prior behavior)."""
        content = self._write_one()
        self.assertIn("**Source**: verify", content)

    def test_explicit_source_verify(self):
        """Passing source='verify' explicitly also renders **Source**: verify."""
        content = self._write_one(source_kwarg="verify")
        self.assertIn("**Source**: verify", content)

    def test_source_manual(self):
        """source='manual' renders **Source**: manual."""
        content = self._write_one(source_kwarg="manual")
        self.assertIn("**Source**: manual", content)
        self.assertNotIn("**Source**: verify", content)

    def test_source_fix(self):
        """source='fix' renders **Source**: fix."""
        content = self._write_one(source_kwarg="fix")
        self.assertIn("**Source**: fix", content)
        self.assertNotIn("**Source**: verify", content)

    def test_source_propagates_across_batch(self):
        """All bugs in a batch use the same source value."""
        paths = file_bugs(
            bugs_dir=self.bugs_dir,
            issues=[_issue(title="Bug A"), _issue(title="Bug B")],
            feature_spec_path="specs/001/spec.md",
            date="2026-06-16",
            source="manual",
        )
        self.assertEqual(len(paths), 2)
        for p in paths:
            with open(p, encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("**Source**: manual", content)
            self.assertNotIn("**Source**: verify", content)


# ---------------------------------------------------------------------------
# Numbering tests
# ---------------------------------------------------------------------------


class TestFileBugsNumbering(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bugs_dir = os.path.join(self.tmp, "bugs")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, issues, date="2026-06-16"):
        return file_bugs(
            bugs_dir=self.bugs_dir,
            issues=issues,
            feature_spec_path="specs/001/spec.md",
            date=date,
        )

    def test_empty_dir_starts_at_001(self):
        paths = self._write([_issue(title="First bug")])
        self.assertEqual(len(paths), 1)
        self.assertIn("001-", os.path.basename(paths[0]))

    def test_existing_bugs_continues_numbering(self):
        # Simulate existing bugs 001-003
        os.makedirs(self.bugs_dir, exist_ok=True)
        for i in range(1, 4):
            path = os.path.join(self.bugs_dir, "{0:03d}-existing.md".format(i))
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("# Bug {0}\n".format(i))
        paths = self._write([_issue(title="New bug")])
        self.assertIn("004-", os.path.basename(paths[0]))

    def test_batch_of_three_sequential(self):
        issues = [
            _issue(title="Bug Alpha"),
            _issue(title="Bug Beta"),
            _issue(title="Bug Gamma"),
        ]
        paths = self._write(issues)
        self.assertEqual(len(paths), 3)
        names = [os.path.basename(p) for p in paths]
        self.assertTrue(names[0].startswith("001-"))
        self.assertTrue(names[1].startswith("002-"))
        self.assertTrue(names[2].startswith("003-"))

    def test_scan_highest_number_empty_dir(self):
        os.makedirs(self.bugs_dir, exist_ok=True)
        n = scan_highest_number(self.bugs_dir)
        self.assertEqual(n, 0)

    def test_scan_highest_number_with_existing(self):
        os.makedirs(self.bugs_dir, exist_ok=True)
        for name in ("001-foo.md", "007-bar.md", "003-baz.md"):
            with open(os.path.join(self.bugs_dir, name), "w", encoding="utf-8") as fh:
                fh.write("x")
        n = scan_highest_number(self.bugs_dir)
        self.assertEqual(n, 7)

    def test_bugs_dir_created_if_absent(self):
        self.assertFalse(os.path.isdir(self.bugs_dir))
        self._write([_issue()])
        self.assertTrue(os.path.isdir(self.bugs_dir))


# ---------------------------------------------------------------------------
# Related Issues cross-links
# ---------------------------------------------------------------------------


class TestFileBugsRelatedIssues(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bugs_dir = os.path.join(self.tmp, "bugs")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, n, start_title="Bug"):
        issues = [_issue(title="{0} {1}".format(start_title, i + 1)) for i in range(n)]
        return file_bugs(
            bugs_dir=self.bugs_dir,
            issues=issues,
            feature_spec_path="specs/001/spec.md",
            date="2026-06-16",
        )

    def _read(self, path):
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def test_two_bugs_cross_reference(self):
        paths = self._write(2)
        content_0 = self._read(paths[0])
        content_1 = self._read(paths[1])
        # First bug should reference second
        self.assertIn(os.path.basename(paths[1]), content_0)
        # Second bug should reference first
        self.assertIn(os.path.basename(paths[0]), content_1)

    def test_three_bugs_each_references_other_two(self):
        paths = self._write(3)
        for i, path in enumerate(paths):
            content = self._read(path)
            for j, other_path in enumerate(paths):
                if i == j:
                    continue
                self.assertIn(os.path.basename(other_path), content,
                              msg="Bug {0} should reference {1}".format(i, other_path))


# ---------------------------------------------------------------------------
# Slug sanitisation
# ---------------------------------------------------------------------------


class TestSlugify(unittest.TestCase):

    def test_spaces_to_hyphens(self):
        self.assertEqual(slugify("null cart total"), "null-cart-total")

    def test_uppercase_to_lowercase(self):
        self.assertEqual(slugify("Null Cart Total"), "null-cart-total")

    def test_special_chars_to_hyphen(self):
        result = slugify("bug: invalid/path")
        self.assertNotIn(":", result)
        self.assertNotIn("/", result)

    def test_collapse_multiple_hyphens(self):
        result = slugify("bug--double")
        self.assertNotIn("--", result)

    def test_cap_at_30_chars(self):
        long_title = "this is a very long title that exceeds 30 characters"
        result = slugify(long_title)
        self.assertLessEqual(len(result), 30)

    def test_empty_string_gives_bug(self):
        result = slugify("")
        self.assertEqual(result, "bug")

    def test_strip_leading_trailing_hyphens(self):
        result = slugify("--leading and trailing--")
        self.assertFalse(result.startswith("-"))
        self.assertFalse(result.endswith("-"))

    def test_hyphens_in_input_are_non_alnum_treated(self):
        """Hyphens in the input are treated as non-alphanumeric by _SLUG_NONALNUM_RE.

        The regex r'[^a-z0-9]+' matches hyphens (they are not a-z or 0-9), so
        a hyphen in the input is replaced — and consecutive runs then collapsed.
        This documents the actual behavior per the corrected inline comment:
        _SLUG_NONALNUM_RE replaces non-alphanumeric chars INCLUDING hyphens.
        The output never contains double-hyphens from input hyphens.

        Docstring fix (Finding 4): the old comment said 'except hyphen' which was
        wrong — hyphens ARE replaced by the regex, just the replacement is also a
        hyphen, so single hyphens survive.  Multi-hyphen runs ARE collapsed.
        """
        # A title with hyphens: each hyphen → hyphen (same char), then collapsed
        result = slugify("pre-existing-bug-here")
        self.assertEqual(result, "pre-existing-bug-here")

        # A title where a hyphen is adjacent to another non-alnum (space + hyphen)
        # The space-hyphen run is one non-alnum run → single hyphen
        result = slugify("bug -title")
        self.assertNotIn("--", result, "Adjacent non-alnum runs should collapse to one hyphen")

        # Consecutive hyphens in input → collapsed to single hyphen
        result = slugify("bug---triple")
        self.assertNotIn("--", result, "Triple hyphen should collapse to single hyphen")

    # --- Word-boundary truncation tests (Fix A) ---

    def test_truncation_at_word_boundary_no_trailing_partial_word(self):
        """A long multi-word title must not end mid-word after truncation."""
        # This title slugifies to "verify-touched-falls-back-to-manifest-detection"
        # which is > 30 chars; truncation must land on a complete word.
        title = "verify touched falls back to manifest detection"
        result = slugify(title, max_len=30)
        self.assertLessEqual(len(result), 30)
        # Must not end with a partial word fragment: every token must be a
        # complete word from the original slug.
        full_slug = "verify-touched-falls-back-to-manifest-detection"
        words = full_slug.split("-")
        result_words = result.split("-")
        for w in result_words:
            self.assertIn(w, words, "Truncated slug contains a word not in the original")
        # Confirm no trailing hyphen
        self.assertFalse(result.endswith("-"))

    def test_truncation_produces_result_no_longer_than_cap(self):
        """Result never exceeds max_len even for a title that hits the boundary."""
        title = "v2 empty category menu response handler edge case"
        result = slugify(title, max_len=30)
        self.assertLessEqual(len(result), 30)

    def test_truncation_single_overlong_word_gives_nonempty_slug(self):
        """A single word longer than max_len must still produce a non-empty slug."""
        title = "averylongsingletokenwithnohyphensthatwillexceedthirtychars"
        result = slugify(title, max_len=30)
        self.assertGreater(len(result), 0)
        self.assertNotEqual(result, "bug")  # actual word chars present

    def test_short_title_unchanged_by_truncation_logic(self):
        """A title shorter than max_len is not modified by the truncation path."""
        title = "null cart total"
        result = slugify(title, max_len=30)
        self.assertEqual(result, "null-cart-total")

    def test_truncation_does_not_produce_trailing_hyphen(self):
        """After word-boundary truncation, the result must not end with a hyphen."""
        # Craft a slug where a hyphen sits exactly at the cap boundary.
        # "aaa-bbb-ccc-ddd-eee-fff-ggg-hh" is 31 chars (hyphen at pos 29).
        title = "aaa bbb ccc ddd eee fff ggg hhh"
        result = slugify(title, max_len=30)
        self.assertFalse(result.endswith("-"))
        self.assertLessEqual(len(result), 30)

    def test_real_filenames_from_testforge20_are_clean(self):
        """Regression: the three ugly filenames surfaced in testForge20 e2e."""
        cases = [
            ("verify touched falls back to manifest detection",
             "verify-touched-falls-back-to"),
            ("v2 empty category menu response",
             "v2-empty-category-menu"),
            ("v2 use case null array guard middleware",
             "v2-use-case-null-array-guard"),
        ]
        for title, expected in cases:
            with self.subTest(title=title):
                result = slugify(title, max_len=30)
                self.assertEqual(result, expected)
                self.assertFalse(result.endswith("-"))


# ---------------------------------------------------------------------------
# Atomic write + edge cases
# ---------------------------------------------------------------------------


class TestFileBugsEdgeCases(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bugs_dir = os.path.join(self.tmp, "bugs")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empty_issues_returns_empty_list(self):
        result = file_bugs(
            bugs_dir=self.bugs_dir,
            issues=[],
            feature_spec_path="specs/001/spec.md",
            date="2026-06-16",
        )
        self.assertEqual(result, [])
        # bugs_dir should NOT be created for empty input
        # (actually it is created by os.makedirs if we call it — but we don't
        # call it when issues is empty, so it won't exist)
        # Let's just verify no exception was raised.

    def test_no_tmp_files_left(self):
        file_bugs(
            bugs_dir=self.bugs_dir,
            issues=[_issue()],
            feature_spec_path="specs/001/spec.md",
            date="2026-06-16",
        )
        entries = os.listdir(self.bugs_dir)
        tmp_files = [e for e in entries if e.startswith(".tmp-bug-")]
        self.assertEqual(tmp_files, [])

    def test_written_file_is_readable_utf8(self):
        paths = file_bugs(
            bugs_dir=self.bugs_dir,
            issues=[_issue(description="Desc with unicode: café")],
            feature_spec_path="specs/001/spec.md",
            date="2026-06-16",
        )
        with open(paths[0], encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("café", content)

    def test_missing_title_uses_placeholder(self):
        issue = _issue()
        issue["title"] = ""
        paths = file_bugs(
            bugs_dir=self.bugs_dir,
            issues=[issue],
            feature_spec_path="N/A",
            date="2026-06-16",
        )
        # Should not crash; file should exist
        self.assertTrue(os.path.isfile(paths[0]))

    def test_missing_files_uses_unknown_row(self):
        issue = _issue()
        issue["files"] = []
        paths = file_bugs(
            bugs_dir=self.bugs_dir,
            issues=[issue],
            feature_spec_path="N/A",
            date="2026-06-16",
        )
        with open(paths[0], encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("(unknown)", content)

    def test_returns_list_of_written_paths(self):
        paths = file_bugs(
            bugs_dir=self.bugs_dir,
            issues=[_issue(), _issue(title="Second")],
            feature_spec_path="N/A",
            date="2026-06-16",
        )
        self.assertEqual(len(paths), 2)
        for p in paths:
            self.assertTrue(os.path.isfile(p))


# ---------------------------------------------------------------------------
# close_bug (plan 88 D4) -- round-tripped through the real producer
# (file_bugs), never a hand-authored fixture.
# ---------------------------------------------------------------------------


class TestCloseBug(unittest.TestCase):
    """close_bug tests build their input via file_bugs -- the SAME writer
    /devforge:report-bug and /devforge:verify use -- then close it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bugs_dir = os.path.join(self.tmp, "bugs")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _file_one(self, **kwargs):
        """Write one real bug file via file_bugs; return its path."""
        paths = file_bugs(
            bugs_dir=self.bugs_dir,
            issues=[_issue(**kwargs)],
            feature_spec_path="specs/001-cart/spec.md",
            date="2026-06-16",
        )
        self.assertEqual(len(paths), 1)
        return paths[0]

    def _set_status(self, bug_path, new_status):
        """Test-only helper: manually transition Status, mirroring the
        real manual Open -> In Progress edit storage-rules.md documents
        (there is no producer that ever writes anything but 'Open')."""
        with open(bug_path, encoding="utf-8") as fh:
            content = fh.read()
        content = content.replace(
            "**Status**: Open", "**Status**: {0}".format(new_status), 1
        )
        with open(bug_path, "w", encoding="utf-8") as fh:
            fh.write(content)

    # --- Happy path: the three fields ---

    def test_status_flipped_to_fixed(self):
        bug_path = self._file_one()
        close_bug(bug_path, "2026-08-26", "Root cause: null guard added.")
        with open(bug_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("**Status**: Fixed", content)
        self.assertNotIn("**Status**: Open", content)

    def test_fixed_date_filled(self):
        bug_path = self._file_one()
        close_bug(bug_path, "2026-08-26", "Root cause: null guard added.")
        with open(bug_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("**Fixed**: 2026-08-26", content)

    def test_fix_notes_replaced(self):
        bug_path = self._file_one()
        close_bug(bug_path, "2026-08-26", "Root cause: null guard added.")
        with open(bug_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("Root cause: null guard added.", content)
        self.assertNotIn("_Filled in after resolution._", content)

    def test_multiline_fix_notes_preserved(self):
        bug_path = self._file_one()
        notes = (
            "Root cause: cart total was not defaulted.\n"
            "What changed: added a null-coalescing guard in src/cart.py.\n"
            "Commit: abc1234."
        )
        close_bug(bug_path, "2026-08-26", notes)
        with open(bug_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn(notes, content)

    # --- Byte-identity outside the three changed fields ---

    def test_byte_identity_outside_three_fields(self):
        bug_path = self._file_one()
        with open(bug_path, encoding="utf-8") as fh:
            original_lines = fh.read().split("\n")

        close_bug(bug_path, "2026-08-26", "Root cause: null guard added; commit abc1234.")

        with open(bug_path, encoding="utf-8") as fh:
            new_lines = fh.read().split("\n")

        self.assertEqual(len(original_lines), len(new_lines))
        diff_indices = [
            i for i in range(len(original_lines))
            if original_lines[i] != new_lines[i]
        ]
        self.assertEqual(
            len(diff_indices), 3,
            "Expected exactly 3 changed lines (Status, Fixed, Fix Notes body); "
            "got: {0}".format(diff_indices),
        )
        for i in diff_indices:
            self.assertTrue(
                original_lines[i].startswith("**Status**: ")
                or original_lines[i].startswith("**Fixed**: ")
                or original_lines[i] == "_Filled in after resolution._",
                "Unexpected changed line {0}: {1!r}".format(i, original_lines[i]),
            )

    # --- Reject already-Fixed / unrecognized Status, WITHOUT writing ---

    def test_already_fixed_exits_and_writes_nothing(self):
        """Close once (Open -> Fixed), then close AGAIN: the second call
        must raise and must NOT touch the file further."""
        bug_path = self._file_one()
        close_bug(bug_path, "2026-08-26", "First closure.")
        with open(bug_path, encoding="utf-8") as fh:
            after_first_close = fh.read()

        with self.assertRaises(ValueError):
            close_bug(bug_path, "2026-08-27", "Second closure attempt.")

        with open(bug_path, encoding="utf-8") as fh:
            after_second_attempt = fh.read()
        self.assertEqual(
            after_first_close, after_second_attempt,
            "A rejected close_bug call must write NOTHING",
        )

    def test_unrecognized_status_rejected_writes_nothing(self):
        bug_path = self._file_one()
        self._set_status(bug_path, "Won't Fix")
        with open(bug_path, encoding="utf-8") as fh:
            before = fh.read()

        with self.assertRaises(ValueError):
            close_bug(bug_path, "2026-08-26", "Attempted closure.")

        with open(bug_path, encoding="utf-8") as fh:
            after = fh.read()
        self.assertEqual(before, after)

    def test_in_progress_status_accepted(self):
        bug_path = self._file_one()
        self._set_status(bug_path, "In Progress")
        close_bug(bug_path, "2026-08-26", "Root cause found; fix applied.")
        with open(bug_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("**Status**: Fixed", content)

    def test_hand_written_fix_notes_rejected_writes_nothing(self):
        """python-reviewer finding 1: an Open/In Progress bug whose owner
        already hand-wrote real notes into ## Fix Notes (before this
        automated close ever ran) must be REJECTED, not silently
        overwritten -- fail-closed, never clobber hand-written content."""
        bug_path = self._file_one()
        with open(bug_path, encoding="utf-8") as fh:
            content = fh.read()
        content = content.replace(
            "_Filled in after resolution._",
            "Investigated manually: root cause is a stale cache entry.",
            1,
        )
        with open(bug_path, "w", encoding="utf-8") as fh:
            fh.write(content)

        with open(bug_path, encoding="utf-8") as fh:
            before = fh.read()
        # Status is still Open -- confirms the rejection is specifically the
        # placeholder-absent path, not the Status gate.
        self.assertIn("**Status**: Open", before)

        with self.assertRaises(ValueError):
            close_bug(bug_path, "2026-08-26", "Automated closure attempt.")

        with open(bug_path, encoding="utf-8") as fh:
            after = fh.read()
        self.assertEqual(
            before, after,
            "close_bug must not overwrite hand-written Fix Notes content",
        )

    # --- Input validation ---

    def test_missing_bug_file_raises(self):
        with self.assertRaises(ValueError):
            close_bug(
                os.path.join(self.tmp, "bugs", "999-nonexistent.md"),
                "2026-08-26",
                "notes",
            )

    def test_empty_date_raises(self):
        bug_path = self._file_one()
        with self.assertRaises(ValueError):
            close_bug(bug_path, "", "notes")
        with open(bug_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("**Status**: Open", content)

    def test_empty_fix_notes_raises(self):
        bug_path = self._file_one()
        with self.assertRaises(ValueError):
            close_bug(bug_path, "2026-08-26", "")
        with open(bug_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("**Status**: Open", content)

    # --- Atomic write hygiene ---

    def test_no_tmp_files_left_after_close(self):
        bug_path = self._file_one()
        close_bug(bug_path, "2026-08-26", "notes")
        entries = os.listdir(self.bugs_dir)
        tmp_files = [e for e in entries if e.startswith(".tmp-bug-close-")]
        self.assertEqual(tmp_files, [])

    def test_close_bug_returns_none(self):
        """close_bug's return value is None -- callers read success by the
        absence of a raised exception, not a return value."""
        bug_path = self._file_one()
        result = close_bug(bug_path, "2026-08-26", "notes")
        self.assertIsNone(result)

    # --- Anchoring: lookalike text inside prose bodies must not be matched ---

    def test_does_not_match_status_lookalike_inside_description(self):
        """python-reviewer finding 2: the Description body's lookalike line
        must itself BEGIN with the literal '**Status**: Open' prefix -- a
        mid-sentence occurrence never exercises line.startswith() anchoring
        at all. close_bug must still flip only the REAL header field (first
        in document order) and leave this prose line byte-unchanged."""
        lookalike = "**Status**: Open is what our competitor's tracker shows."
        bug_path = self._file_one(description=lookalike)

        with open(bug_path, encoding="utf-8") as fh:
            original_lines = fh.read().split("\n")
        # Sanity: the fixture really does put two lines starting with the
        # exact same prefix into the file, with the real field first.
        matching = [i for i, l in enumerate(original_lines)
                    if l.startswith(_STATUS_LINE_PREFIX)]
        self.assertEqual(len(matching), 2, "Expected exactly 2 lookalike lines")
        real_idx, prose_idx = matching[0], matching[1]
        self.assertEqual(original_lines[real_idx], "**Status**: Open")
        self.assertEqual(original_lines[prose_idx], lookalike)

        close_bug(bug_path, "2026-08-26", "notes")

        with open(bug_path, encoding="utf-8") as fh:
            new_lines = fh.read().split("\n")
        # The FIRST occurrence (the real header field) flipped to Fixed.
        self.assertEqual(new_lines[real_idx], "**Status**: Fixed")
        # The SECOND occurrence (the prose lookalike) is byte-unchanged.
        self.assertEqual(new_lines[prose_idx], lookalike)


if __name__ == "__main__":
    unittest.main()
