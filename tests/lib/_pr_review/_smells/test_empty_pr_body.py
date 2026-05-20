"""Tests for src/devforge/lib/_pr_review/_smells/empty_pr_body.py.

Coverage:
  Positive: empty body, whitespace-only body, body <= 30 chars
  Negative: body > 30 chars with actual content
  Finding schema: correct keys present when fires
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._smells.empty_pr_body import run  # noqa: E402
from _pr_review._state import PRReviewState  # noqa: E402


def _make_state(pr_body: str) -> PRReviewState:
    return PRReviewState(pr_body=pr_body)


class TestEmptyPrBodyPositive(unittest.TestCase):
    """Cases where the heuristic should fire."""

    def test_empty_body_produces_finding(self):
        findings = run(_make_state(""))
        self.assertEqual(len(findings), 1)

    def test_whitespace_only_body_produces_finding(self):
        findings = run(_make_state("   \n\t  "))
        self.assertEqual(len(findings), 1)

    def test_body_of_10_spaces_produces_finding(self):
        """10 spaces stripped = 0 chars (well below threshold)."""
        findings = run(_make_state(" " * 10))
        self.assertEqual(len(findings), 1)

    def test_short_body_fix_bug_produces_finding(self):
        findings = run(_make_state("Fix bug"))
        self.assertEqual(len(findings), 1)

    def test_body_exactly_30_chars_produces_finding(self):
        """Threshold is <=30, so 30 chars fires."""
        body = "a" * 30
        findings = run(_make_state(body))
        self.assertEqual(len(findings), 1)

    def test_body_of_1_char_produces_finding(self):
        findings = run(_make_state("x"))
        self.assertEqual(len(findings), 1)

    def test_body_of_29_chars_produces_finding(self):
        findings = run(_make_state("a" * 29))
        self.assertEqual(len(findings), 1)


class TestEmptyPrBodyNegative(unittest.TestCase):
    """Cases where the heuristic should NOT fire."""

    def test_body_of_31_chars_no_finding(self):
        findings = run(_make_state("a" * 31))
        self.assertEqual(findings, [])

    def test_body_of_50_chars_with_content_no_finding(self):
        body = "Fixes the spinner animation delay on mobile devices"
        self.assertGreater(len(body), 30)
        findings = run(_make_state(body))
        self.assertEqual(findings, [])

    def test_body_with_newlines_counted_stripped(self):
        """Stripping removes leading/trailing whitespace; 50-char content passes."""
        body = "\n\n" + "A" * 50 + "\n"
        findings = run(_make_state(body))
        self.assertEqual(findings, [])


class TestEmptyPrBodyFindingSchema(unittest.TestCase):
    """The finding dict has the correct schema when the heuristic fires."""

    def setUp(self):
        self.findings = run(_make_state("short"))

    def test_finding_has_name_key(self):
        self.assertIn("name", self.findings[0])

    def test_finding_name_is_empty_pr_body(self):
        self.assertEqual(self.findings[0]["name"], "empty_pr_body")

    def test_finding_has_severity_key(self):
        self.assertIn("severity", self.findings[0])

    def test_finding_severity_is_low(self):
        self.assertEqual(self.findings[0]["severity"], "low")

    def test_finding_has_location_key(self):
        self.assertIn("location", self.findings[0])

    def test_finding_location_is_star(self):
        self.assertEqual(self.findings[0]["location"], "*")

    def test_finding_has_evidence_key(self):
        self.assertIn("evidence", self.findings[0])

    def test_finding_evidence_contains_char_count(self):
        """Evidence string mentions the actual body length."""
        # "short" stripped = 5 chars
        self.assertIn("5", self.findings[0]["evidence"])

    def test_finding_exactly_one_returned(self):
        """Only one finding emitted even on zero-length body."""
        findings = run(_make_state(""))
        self.assertEqual(len(findings), 1)


if __name__ == "__main__":
    unittest.main()
