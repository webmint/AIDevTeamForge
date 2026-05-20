"""Tests for src/devforge/lib/_pr_review/_smells/verbose_commit_msg.py.

Coverage:
  Positive — subject matching each verbose pattern
  Positive — subject exceeding word-count threshold (no pattern match)
  Negative — clean concise commit message
  Edge — empty commit_subjects list → no findings
  Edge — empty/blank subject string → no finding for that entry
  Finding schema — correct keys
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._smells.verbose_commit_msg import run  # noqa: E402
from _pr_review._state import PRReviewState  # noqa: E402


def _make_state(commit_subjects) -> PRReviewState:
    return PRReviewState(commit_subjects=commit_subjects)


# ---------------------------------------------------------------------------
# Positive tests — pattern matching.
# ---------------------------------------------------------------------------


class TestVerboseCommitMsgPatternMatch(unittest.TestCase):
    def test_refactor_improve_and_pattern(self):
        """'Refactor ... to improve ... and ...' fires."""
        subject = "Refactor order address components to improve internal order experience and clarity"
        findings = run(_make_state([subject]))
        self.assertEqual(len(findings), 1)

    def test_update_to_handle_pattern(self):
        """'Update ... to handle ...' fires."""
        subject = "Update spinner component to handle async loading states"
        findings = run(_make_state([subject]))
        self.assertEqual(len(findings), 1)

    def test_improve_for_pattern(self):
        """'Improve ... for ...' fires."""
        subject = "Improve error messages for better user experience"
        findings = run(_make_state([subject]))
        self.assertEqual(len(findings), 1)

    def test_pattern_match_case_insensitive(self):
        """Patterns are case-insensitive."""
        subject = "refactor payment module to improve performance and security"
        findings = run(_make_state([subject]))
        self.assertEqual(len(findings), 1)


# ---------------------------------------------------------------------------
# Positive tests — word-count threshold.
# ---------------------------------------------------------------------------


class TestVerboseCommitMsgWordCount(unittest.TestCase):
    def test_13_word_subject_fires(self):
        """13 words (> 12 threshold) with no pattern match fires."""
        subject = "add new feature to support bulk actions in the admin panel here now"
        words = subject.split()
        self.assertEqual(len(words), 13)
        findings = run(_make_state([subject]))
        self.assertEqual(len(findings), 1)

    def test_15_word_subject_fires(self):
        subject = "this is a very long commit subject line that has way too many words in it"
        self.assertGreater(len(subject.split()), 12)
        findings = run(_make_state([subject]))
        self.assertEqual(len(findings), 1)


# ---------------------------------------------------------------------------
# Negative tests.
# ---------------------------------------------------------------------------


class TestVerboseCommitMsgNegative(unittest.TestCase):
    def test_concise_fix_subject_no_finding(self):
        findings = run(_make_state(["fix: spinner on refresh"]))
        self.assertEqual(findings, [])

    def test_exactly_12_words_no_finding(self):
        """12 words — threshold is >12, so no finding."""
        subject = " ".join(["word"] * 12)
        self.assertEqual(len(subject.split()), 12)
        findings = run(_make_state([subject]))
        self.assertEqual(findings, [])

    def test_conventional_commit_format_short_no_finding(self):
        findings = run(_make_state(["feat(auth): add JWT refresh token support"]))
        self.assertEqual(findings, [])

    def test_clean_chore_commit_no_finding(self):
        findings = run(_make_state(["chore: update dependencies"]))
        self.assertEqual(findings, [])


# ---------------------------------------------------------------------------
# Edge cases.
# ---------------------------------------------------------------------------


class TestVerboseCommitMsgEdgeCases(unittest.TestCase):
    def test_empty_commit_subjects_list(self):
        findings = run(_make_state([]))
        self.assertEqual(findings, [])

    def test_none_commit_subjects_treated_as_empty(self):
        state = PRReviewState(commit_subjects=None)  # type: ignore[arg-type]
        findings = run(state)
        self.assertEqual(findings, [])

    def test_empty_string_subject_skipped(self):
        """Empty string subjects are not included in output."""
        findings = run(_make_state(["", "", ""]))
        self.assertEqual(findings, [])

    def test_multiple_subjects_one_verbose(self):
        subjects = [
            "fix: spinner on refresh",
            "Refactor cart module to improve checkout and reduce errors",
            "docs: update README",
        ]
        findings = run(_make_state(subjects))
        self.assertEqual(len(findings), 1)

    def test_multiple_verbose_subjects_multiple_findings(self):
        subjects = [
            "Refactor cart module to improve checkout and reduce errors",
            "Update payment flow to handle declined card edge cases",
        ]
        findings = run(_make_state(subjects))
        self.assertEqual(len(findings), 2)

    def test_pattern_match_does_not_double_count_with_word_threshold(self):
        """A subject matching pattern AND exceeding word count produces ONE finding."""
        # "Refactor ... to improve ... and ..." with 15+ words.
        subject = (
            "Refactor the user address form components to improve the overall "
            "internal checkout experience and reduce duplication"
        )
        self.assertGreater(len(subject.split()), 12)
        findings = run(_make_state([subject]))
        self.assertEqual(len(findings), 1)


# ---------------------------------------------------------------------------
# Finding schema.
# ---------------------------------------------------------------------------


class TestVerboseCommitMsgFindingSchema(unittest.TestCase):
    def setUp(self):
        self.findings = run(_make_state(
            ["Refactor order components to improve experience and reduce code"]
        ))

    def test_finding_name(self):
        self.assertEqual(self.findings[0]["name"], "verbose_commit_msg")

    def test_finding_severity_nit(self):
        self.assertEqual(self.findings[0]["severity"], "nit")

    def test_finding_location_format(self):
        """Location is 'commit:<index>' where index is the 0-based position."""
        self.assertRegex(self.findings[0]["location"], r"^commit:\d+$")

    def test_finding_location_index_zero(self):
        """First commit (index 0) → 'commit:0'."""
        self.assertEqual(self.findings[0]["location"], "commit:0")

    def test_finding_location_second_commit(self):
        """Verbose subject at index 1 → 'commit:1'."""
        subjects = [
            "fix: clean commit",
            "Update all the things to handle every possible edge case here",
        ]
        findings = run(_make_state(subjects))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["location"], "commit:1")

    def test_finding_evidence_is_the_subject(self):
        subject = "Refactor order components to improve experience and reduce code"
        findings = run(_make_state([subject]))
        self.assertEqual(findings[0]["evidence"], subject)


if __name__ == "__main__":
    unittest.main()
