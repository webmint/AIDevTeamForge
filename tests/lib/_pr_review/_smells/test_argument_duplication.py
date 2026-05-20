"""Tests for src/devforge/lib/_pr_review/_smells/argument_duplication.py
and src/devforge/lib/_shared/literal_call_shape.py (canonical).

Coverage:
    _shared/literal_call_shape (canonical):
        LITERAL_TOKEN_RE          — numeric, float, quoted-string, boolean, no-match-in-ident
        _normalize_call_shape     — whitespace collapse
        _detect_arg_duplication   — duplicate ident, no dup, nested bail, numeric excluded

    argument_duplication.run():
        positive — diff line with duplicate identifier arg → finding
        negative — no duplicate → no finding
        multi    — 2 call shapes with duplication → 2 findings
        nested   — f(g(x), y, y) → no finding (nested unsupported)
        cap      — more than _MAX_CALL_SHAPES shapes → stops at cap
        empty    — empty/None diff → no finding
        schema   — correct keys + location format
        no_numeric_prefix — "5(a, a)" does NOT fire (word-boundary guard)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared.literal_call_shape import (  # noqa: E402
    LITERAL_TOKEN_RE,
    _detect_arg_duplication,
    _normalize_call_shape,
)
from _pr_review._smells.argument_duplication import (  # noqa: E402
    _MAX_CALL_SHAPES,
    run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state_from_added_lines(*lines: str) -> SimpleNamespace:
    """Build a state with a diff containing the given lines as added lines."""
    diff_lines = [
        "diff --git a/foo.py b/foo.py",
        "--- a/foo.py",
        "+++ b/foo.py",
        "@@ -1,0 +1,{n} @@".format(n=len(lines)),
    ]
    for line in lines:
        diff_lines.append("+" + line)
    return SimpleNamespace(diff="\n".join(diff_lines) + "\n")


# ---------------------------------------------------------------------------
# LITERAL_TOKEN_RE
# ---------------------------------------------------------------------------


class TestLiteralTokenRE(unittest.TestCase):
    def test_numeric_integer(self):
        matches = LITERAL_TOKEN_RE.findall("x = 365")
        self.assertIn("365", matches)

    def test_numeric_float(self):
        matches = LITERAL_TOKEN_RE.findall("timeout = 1.5")
        self.assertIn("1.5", matches)

    def test_single_quoted_string(self):
        matches = LITERAL_TOKEN_RE.findall("name = 'hello'")
        self.assertIn("'hello'", matches)

    def test_double_quoted_string(self):
        matches = LITERAL_TOKEN_RE.findall('name = "world"')
        self.assertIn('"world"', matches)

    def test_backtick_string(self):
        matches = LITERAL_TOKEN_RE.findall("name = `foo`")
        self.assertIn("`foo`", matches)

    def test_boolean_literals_match(self):
        """Canonical LITERAL_TOKEN_RE matches booleans (unlike prior duplicate)."""
        matches = LITERAL_TOKEN_RE.findall("enabled = True")
        self.assertIn("True", matches)

    def test_hex_literal_matches(self):
        """Canonical LITERAL_TOKEN_RE matches hex literals."""
        matches = LITERAL_TOKEN_RE.findall("mask = 0xFF")
        self.assertIn("0xFF", matches)

    def test_standalone_zero(self):
        matches = LITERAL_TOKEN_RE.findall("x = 0")
        self.assertIn("0", matches)

    def test_empty_string_no_match(self):
        matches = LITERAL_TOKEN_RE.findall("")
        self.assertEqual(matches, [])


# ---------------------------------------------------------------------------
# _normalize_call_shape
# ---------------------------------------------------------------------------


class TestNormalizeCallShape(unittest.TestCase):
    def test_strips_outer_whitespace(self):
        self.assertEqual(_normalize_call_shape("  fn(a, b)  "), "fn(a, b)")

    def test_collapses_internal_whitespace(self):
        self.assertEqual(_normalize_call_shape("fn (  a ,  b  )"), "fn ( a , b )")

    def test_already_normalized_unchanged(self):
        self.assertEqual(_normalize_call_shape("fn(a, b)"), "fn(a, b)")

    def test_empty_string(self):
        self.assertEqual(_normalize_call_shape(""), "")


# ---------------------------------------------------------------------------
# _detect_arg_duplication (canonical — takes full call shape string)
# ---------------------------------------------------------------------------


class TestDetectArgDuplication(unittest.TestCase):
    def test_duplicate_identifier(self):
        result = _detect_arg_duplication("fn(makeId, value, value)")
        self.assertIsNotNone(result)
        ident, count = result
        self.assertEqual(ident, "value")
        self.assertEqual(count, 2)

    def test_no_duplicate(self):
        self.assertIsNone(_detect_arg_duplication("fn(makeId, value)"))

    def test_empty_call_shape(self):
        self.assertIsNone(_detect_arg_duplication(""))

    def test_single_arg(self):
        self.assertIsNone(_detect_arg_duplication("fn(x)"))

    def test_nested_call_returns_none(self):
        """Nested call shape fails CALL_SHAPE_RE → None."""
        self.assertIsNone(_detect_arg_duplication("f(g(x), y, y)"))

    def test_numeric_tokens_excluded(self):
        """Numbers are not identifiers; two '1' args don't count as duplicate."""
        result = _detect_arg_duplication("fn(1, 1)")
        self.assertIsNone(result)

    def test_first_duplicate_returned(self):
        """When multiple duplicates exist, the first one found is returned."""
        result = _detect_arg_duplication("fn(a, b, a, b)")
        self.assertIsNotNone(result)
        ident, count = result
        self.assertEqual(ident, "a")

    def test_three_copies(self):
        result = _detect_arg_duplication("fn(x, x, x)")
        self.assertIsNotNone(result)
        self.assertEqual(result[1], 3)

    def test_no_match_for_malformed_input(self):
        """Input that does not match anchored CALL_SHAPE_RE → None."""
        self.assertIsNone(_detect_arg_duplication("not a call shape"))

    def test_no_numeric_prefix_false_positive(self):
        """'5(a, a)' must NOT match — numeric prefix excluded by canonical RE."""
        self.assertIsNone(_detect_arg_duplication("5(a, a)"))


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestArgumentDuplicationRun(unittest.TestCase):
    def test_positive_duplicate_fires(self):
        """fetchOrder(makeId, value, value) → finding."""
        state = _make_state_from_added_lines("fetchOrder(makeId, value, value)")
        findings = run(state)
        self.assertEqual(len(findings), 1)
        self.assertIn("value", findings[0]["evidence"])
        self.assertIn("2x", findings[0]["evidence"])

    def test_negative_no_duplicate_no_finding(self):
        state = _make_state_from_added_lines("fetchOrder(makeId, value)")
        findings = run(state)
        self.assertEqual(findings, [])

    def test_multi_call_shapes_two_findings(self):
        state = _make_state_from_added_lines(
            "fetchOrder(makeId, value, value)",
            "buildUrl(host, host)",
        )
        findings = run(state)
        self.assertEqual(len(findings), 2)

    def test_nested_call_no_finding(self):
        """f(g(x), y, y) — _FUNCTION_CALL_RE matches inner 'g(x)' only (no outer paren).
        'g(x)' has no duplicate args.  Outer 'f(...)' not matched since the inner ')'
        terminates the [^)]* pattern before the outer closing paren."""
        state = _make_state_from_added_lines("f(g(x), y, y)")
        findings = run(state)
        # g(x) → no duplicates; outer shape not captured by _FUNCTION_CALL_RE.
        self.assertEqual(findings, [])

    def test_cap_at_max_shapes(self):
        """More call shapes than _MAX_CALL_SHAPES → stops at cap (no crash)."""
        # Generate 110 added lines, each with a call shape that has a duplicate.
        lines = ["fn_{i}(x, x)".format(i=i) for i in range(110)]
        state = _make_state_from_added_lines(*lines)
        findings = run(state)
        self.assertLessEqual(len(findings), _MAX_CALL_SHAPES)

    def test_empty_diff_no_finding(self):
        state = SimpleNamespace(diff="")
        findings = run(state)
        self.assertEqual(findings, [])

    def test_none_diff_no_finding(self):
        state = SimpleNamespace(diff=None)
        findings = run(state)
        self.assertEqual(findings, [])

    def test_diff_with_only_removals_no_finding(self):
        diff = (
            "diff --git a/foo.py b/foo.py\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1,1 +1,0 @@\n"
            "-fn(a, a)\n"
        )
        state = SimpleNamespace(diff=diff)
        findings = run(state)
        self.assertEqual(findings, [])

    def test_no_numeric_prefix_false_positive(self):
        """'5(a, a)' must NOT fire — word-boundary guard in _FUNCTION_CALL_RE."""
        state = _make_state_from_added_lines("x = 5(a, a)")
        findings = run(state)
        self.assertEqual(findings, [])


class TestArgumentDuplicationFindingSchema(unittest.TestCase):
    def setUp(self):
        state = _make_state_from_added_lines("fetchOrder(makeId, value, value)")
        self.findings = run(state)

    def test_one_finding(self):
        self.assertEqual(len(self.findings), 1)

    def test_name(self):
        self.assertEqual(self.findings[0]["name"], "argument_duplication")

    def test_severity_medium(self):
        self.assertEqual(self.findings[0]["severity"], "medium")

    def test_location_format(self):
        """Location must be 'diff:line+<N>'."""
        self.assertRegex(self.findings[0]["location"], r"^diff:line\+\d+$")

    def test_location_first_added_line(self):
        self.assertEqual(self.findings[0]["location"], "diff:line+0")

    def test_evidence_contains_call_shape(self):
        self.assertIn("fetchOrder", self.findings[0]["evidence"])

    def test_evidence_contains_ident_and_count(self):
        ev = self.findings[0]["evidence"]
        self.assertIn("value", ev)
        self.assertIn("2x", ev)

    def test_location_second_line(self):
        """Pattern on second added line → diff:line+1."""
        state = _make_state_from_added_lines(
            "cleanLine(x, y)",              # no duplicate → no finding
            "buildUrl(host, host)",         # duplicate → finding at index 1
        )
        findings = run(state)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["location"], "diff:line+1")


if __name__ == "__main__":
    unittest.main()
