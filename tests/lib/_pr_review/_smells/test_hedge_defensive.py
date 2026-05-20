"""Tests for src/devforge/lib/_pr_review/_smells/hedge_defensive.py.

Coverage:
  Positive — each of the 5 patterns fires
  Positive — multiple matches in one diff (multiple findings)
  Negative — code without those patterns
  Triple-assign — a = b = c = foo → 1 finding; a = b = foo → 0 findings
  Edge — empty diff
  Finding schema — correct keys + location format
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._smells.hedge_defensive import run  # noqa: E402
from _pr_review._state import PRReviewState  # noqa: E402


def _make_state_from_added_lines(*lines: str) -> PRReviewState:
    """Build a PRReviewState whose diff contains the given lines as added lines.

    Each string in `lines` becomes a '+<line>' entry in a minimal diff block.
    """
    diff_lines = [
        "diff --git a/foo.js b/foo.js",
        "--- a/foo.js",
        "+++ b/foo.js",
        "@@ -1,0 +1,{n} @@".format(n=len(lines)),
    ]
    for line in lines:
        diff_lines.append("+" + line)
    return PRReviewState(diff="\n".join(diff_lines) + "\n")


# ---------------------------------------------------------------------------
# Pattern-by-pattern positive tests.
# ---------------------------------------------------------------------------


class TestHedgeDefensivePatterns(unittest.TestCase):
    def test_string_empty_fallback_single_quotes(self):
        state = _make_state_from_added_lines("const x = foo || '';")
        findings = run(state)
        self.assertEqual(len(findings), 1)

    def test_string_empty_fallback_double_quotes(self):
        state = _make_state_from_added_lines('const x = foo || "";')
        findings = run(state)
        self.assertEqual(len(findings), 1)

    def test_string_empty_fallback_backticks(self):
        state = _make_state_from_added_lines("const x = foo || ``;")
        findings = run(state)
        self.assertEqual(len(findings), 1)

    def test_zero_fallback(self):
        state = _make_state_from_added_lines("const x = foo || 0;")
        findings = run(state)
        self.assertEqual(len(findings), 1)

    def test_array_empty_fallback(self):
        state = _make_state_from_added_lines("const items = foo || [];")
        findings = run(state)
        self.assertEqual(len(findings), 1)

    def test_object_empty_fallback(self):
        state = _make_state_from_added_lines("const obj = foo || {};")
        findings = run(state)
        self.assertEqual(len(findings), 1)

    def test_triple_assignment_chain(self):
        """a = b = c = foo → 1 finding."""
        state = _make_state_from_added_lines("a = b = c = foo;")
        findings = run(state)
        self.assertEqual(len(findings), 1)


# ---------------------------------------------------------------------------
# Multi-pattern / multi-finding tests.
# ---------------------------------------------------------------------------


class TestHedgeDefensiveMultipleFindings(unittest.TestCase):
    def test_two_patterns_on_one_line_two_findings(self):
        """|| '' || 0 on one line → 2 findings."""
        state = _make_state_from_added_lines("const x = a || '' || 0;")
        findings = run(state)
        self.assertEqual(len(findings), 2)

    def test_same_pattern_on_two_lines_two_findings(self):
        state = _make_state_from_added_lines(
            "const x = foo || '';",
            "const y = bar || '';",
        )
        findings = run(state)
        self.assertEqual(len(findings), 2)

    def test_three_hedge_patterns_across_diff(self):
        state = _make_state_from_added_lines(
            "const x = foo || '';",
            "const y = bar || 0;",
            "const z = baz || [];",
        )
        findings = run(state)
        self.assertEqual(len(findings), 3)


# ---------------------------------------------------------------------------
# Negative tests (no findings expected).
# ---------------------------------------------------------------------------


class TestHedgeDefensiveNegative(unittest.TestCase):
    def test_clean_code_no_findings(self):
        state = _make_state_from_added_lines(
            "function greet(name: string): string {",
            "  return `Hello, ${name}`;",
            "}",
        )
        findings = run(state)
        self.assertEqual(findings, [])

    def test_double_assignment_only_no_finding(self):
        """a = b = foo — only 2-deep, threshold is 3-deep."""
        state = _make_state_from_added_lines("a = b = foo;")
        findings = run(state)
        self.assertEqual(findings, [])

    def test_equality_check_not_assignment(self):
        """== is not bare = ; should not trigger triple-assignment."""
        state = _make_state_from_added_lines("if (a == b == c) { return; }")
        findings = run(state)
        self.assertEqual(findings, [])

    def test_or_with_false_literal_no_match(self):
        """|| false does not match any pattern."""
        state = _make_state_from_added_lines("const x = foo || false;")
        findings = run(state)
        self.assertEqual(findings, [])

    def test_removed_lines_not_checked(self):
        """Lines starting with '-' are not added lines; should not trigger."""
        diff = (
            "diff --git a/foo.js b/foo.js\n"
            "--- a/foo.js\n"
            "+++ b/foo.js\n"
            "@@ -1,1 +1,0 @@\n"
            "-const x = foo || '';\n"
        )
        state = PRReviewState(diff=diff)
        findings = run(state)
        self.assertEqual(findings, [])

    def test_context_lines_not_checked(self):
        """Context lines (no prefix) are not added lines."""
        diff = (
            "diff --git a/foo.js b/foo.js\n"
            "--- a/foo.js\n"
            "+++ b/foo.js\n"
            "@@ -1,1 +1,1 @@\n"
            " const x = foo || '';\n"  # space = context line
        )
        state = PRReviewState(diff=diff)
        findings = run(state)
        self.assertEqual(findings, [])


# ---------------------------------------------------------------------------
# Edge cases.
# ---------------------------------------------------------------------------


class TestHedgeDefensiveEdgeCases(unittest.TestCase):
    def test_empty_diff_no_findings(self):
        state = PRReviewState(diff="")
        findings = run(state)
        self.assertEqual(findings, [])

    def test_none_diff_no_findings(self):
        state = PRReviewState(diff=None)  # type: ignore[arg-type]
        findings = run(state)
        self.assertEqual(findings, [])

    def test_diff_with_only_file_headers_no_findings(self):
        diff = (
            "diff --git a/foo.js b/foo.js\n"
            "+++ b/foo.js\n"
            "--- a/foo.js\n"
        )
        state = PRReviewState(diff=diff)
        findings = run(state)
        self.assertEqual(findings, [])

    def test_zero_fallback_not_triggered_by_number_prefix(self):
        """|| 0.5 should not match the || 0 pattern (0 followed by digit)."""
        state = _make_state_from_added_lines("const x = foo || 0.5;")
        findings = run(state)
        self.assertEqual(findings, [])

    def test_blank_added_line_does_not_cross_into_next_line(self):
        """Regression: bare '+\\n' blank added line must not cause _ADDED_LINE_RE to
        consume the newline and capture content of the following line.

        A diff with a blank added line followed by a hedge-pattern line must produce
        exactly one finding (for the hedge line only), not two, and the finding must
        reference the hedge line's evidence, not stray content from the blank line.
        """
        state = PRReviewState(diff="+\n+const x = foo || 0;\n")
        findings = run(state)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["evidence"], "|| 0")


# ---------------------------------------------------------------------------
# Finding schema.
# ---------------------------------------------------------------------------


class TestHedgeDefensiveFindingSchema(unittest.TestCase):
    def setUp(self):
        self.state = _make_state_from_added_lines("const x = foo || '';")
        self.findings = run(self.state)

    def test_one_finding_returned(self):
        self.assertEqual(len(self.findings), 1)

    def test_finding_name(self):
        self.assertEqual(self.findings[0]["name"], "hedge_defensive")

    def test_finding_severity_low(self):
        self.assertEqual(self.findings[0]["severity"], "low")

    def test_finding_location_format(self):
        """Location must be 'diff:line+<N>'."""
        self.assertRegex(self.findings[0]["location"], r"^diff:line\+\d+$")

    def test_finding_location_is_line_0(self):
        """The pattern is on the 1st added line → diff:line+0 (0-indexed)."""
        self.assertEqual(self.findings[0]["location"], "diff:line+0")

    def test_finding_evidence_contains_matched_substring(self):
        self.assertIn("||", self.findings[0]["evidence"])

    def test_finding_location_second_line(self):
        """Pattern on second added line → diff:line+1 (0-indexed)."""
        state = _make_state_from_added_lines(
            "const clean = 'x';",
            "const x = foo || '';",
        )
        findings = run(state)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["location"], "diff:line+1")


if __name__ == "__main__":
    unittest.main()
