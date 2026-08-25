"""Tests for src/devforge/lib/_grill/_merge.py.

Coverage:
  merge_two_passes — a finding present in exactly ONE pass survives; an
                      identical finding in BOTH passes collapses to ONE
                      entry; two genuinely different findings yield TWO
                      entries; the SAME defect (file+line) with two
                      differently-worded `pattern` strings deliberately
                      survives as TWO entries (pins the declared
                      failure-direction trade-off — see _merge.py's
                      docstring); a real consume_agent_tmp/validate_findings
                      round trip exercises the production-shaped dict.
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _grill._merge import merge_two_passes  # noqa: E402


def _finding(file="src/auth/login.py", line=42, pattern="SQL injection",
             why="Some reason.", evidence="def login(user):"):
    return {
        "agent": "devils-advocate",
        "severity": "High",
        "file": file,
        "line": line,
        "pattern": pattern,
        "confidence": "Certain",
        "evidence": evidence,
        "why": why,
        "remediation": "Some fix.",
        "category": "security",
        "tags": [],
    }


class TestMergeSoloSurvivor(unittest.TestCase):
    def test_finding_in_exactly_one_pass_survives(self):
        only_in_a = _finding(pattern="only-in-a")
        merged = merge_two_passes([only_in_a], [])
        self.assertEqual(len(merged), 1)
        self.assertIn(only_in_a, merged)

        only_in_b = _finding(pattern="only-in-b")
        merged_2 = merge_two_passes([], [only_in_b])
        self.assertEqual(len(merged_2), 1)
        self.assertIn(only_in_b, merged_2)


class TestMergeDedup(unittest.TestCase):
    def test_identical_finding_in_both_passes_yields_one_entry(self):
        # Same (file, line, pattern) identity key in both passes, even
        # though `why` differs slightly (as an honest re-report might).
        a = _finding(pattern="XSS via innerHTML", why="First-pass wording.")
        b = _finding(pattern="XSS via innerHTML", why="Second-pass wording.")
        merged = merge_two_passes([a], [b])
        self.assertEqual(len(merged), 1)
        # pass_a's copy wins (kept in place; pass_b's duplicate is dropped).
        self.assertEqual(merged[0]["why"], "First-pass wording.")


class TestMergeDistinctFindings(unittest.TestCase):
    def test_two_different_findings_yield_two_entries(self):
        a = _finding(file="src/auth/login.py", line=42, pattern="SQL injection")
        b = _finding(file="src/auth/session.py", line=10, pattern="Session fixation")
        merged = merge_two_passes([a], [b])
        self.assertEqual(len(merged), 2)
        self.assertIn(a, merged)
        self.assertIn(b, merged)

    def test_same_file_different_line_yields_two_entries(self):
        a = _finding(file="src/auth/login.py", line=42, pattern="SQL injection")
        b = _finding(file="src/auth/login.py", line=99, pattern="Timing attack")
        merged = merge_two_passes([a], [b])
        self.assertEqual(len(merged), 2)

    def test_same_defect_differently_worded_pattern_yields_two_entries(self):
        """Pins the declared trade-off: SAME (file, line) — the same real
        defect — but two honest passes phrase `pattern` differently. This
        is NOT deduped: the docstring's identity key includes `pattern`, so
        this survives as two visible entries (a human-visible duplicate)
        rather than silently vanishing. Without this test, a later
        "simplification" to a file+line-only key would flip the failure
        direction (silent collapse instead of a visible duplicate) with
        nothing here to catch it.
        """
        a = _finding(
            file="src/auth/login.py", line=42,
            pattern="SQL injection via string concatenation",
        )
        b = _finding(
            file="src/auth/login.py", line=42,
            pattern="Unsanitized query building",
        )
        merged = merge_two_passes([a], [b])
        self.assertEqual(len(merged), 2)


class TestMergeEmptyPools(unittest.TestCase):
    def test_both_empty_yields_empty(self):
        self.assertEqual(merge_two_passes([], []), [])

    def test_pure_function_does_not_mutate_inputs(self):
        a = [_finding(pattern="a")]
        b = [_finding(pattern="b")]
        a_copy = list(a)
        b_copy = list(b)
        merge_two_passes(a, b)
        self.assertEqual(a, a_copy)
        self.assertEqual(b, b_copy)


class TestMergeRealProducerRoundTrip(unittest.TestCase):
    """Round-trip through the real producers: parse_agent_tmp +
    validate_findings, the exact pipeline stage that feeds this merge in
    /devforge:grill (consume-tmp → validate-findings → [this merge]).
    """

    _TMP_TEXT = """# Agent: devils-advocate
# Status: complete
# Finding count: 1

## Finding 1
Severity: High
File: sample.py
Line: 1
Pattern: Hardcoded secret
Confidence: Certain
Evidence:
```
API_KEY = "hunter2"
```
Why it's wrong:
Secrets must not be committed in plaintext.
Remediation:
Load from an environment variable instead.
"""

    def test_two_passes_of_the_same_real_finding_dedup_to_one(self):
        from _shared._consume import parse_agent_tmp  # noqa: E402
        from _shared._validate import validate_findings  # noqa: E402
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as td:
            sample_path = os.path.join(td, "sample.py")
            with open(sample_path, "w", encoding="utf-8") as fh:
                fh.write('API_KEY = "hunter2"\n')

            parsed_a = parse_agent_tmp(self._TMP_TEXT, agent_name="devils-advocate")
            parsed_b = parse_agent_tmp(self._TMP_TEXT, agent_name="devils-advocate")

            validated_a = validate_findings(parsed_a["findings"], td)["passed"]
            validated_b = validate_findings(parsed_b["findings"], td)["passed"]

            self.assertEqual(len(validated_a), 1)
            self.assertEqual(len(validated_b), 1)

            merged = merge_two_passes(validated_a, validated_b)
            self.assertEqual(len(merged), 1)


if __name__ == "__main__":
    unittest.main()
