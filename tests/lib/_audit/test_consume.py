"""Tests for src/devforge/lib/_audit/_consume.py.

Coverage:
  parse_agent_tmp — well-formed 2-finding file → exact ParsedFinding fields
  Status cases: failed (+ reason), clean (count 0), complete (count > 0)
  Malformed finding block (missing required field) → skipped
  Fenced Evidence with internal backticks handled
  Top-5-Priorities trailer ignored by finding parser
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import argparse
import io
import json
import os
import tempfile

from _audit._consume import (  # noqa: E402
    ParsedFinding,
    STATUS_CLEAN,
    STATUS_COMPLETE,
    STATUS_FAILED,
    STATUS_MISSING,
    parse_agent_tmp,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WELL_FORMED_TMP = """\
# Agent: code-reviewer
# Status: complete
# Finding count: 2

## Finding 1
Severity: High
File: src/auth.py
Line: 42
Pattern: Naming lie
Confidence: Certain
Evidence:
```
def validate_token(t):
    return True  # never validates
```
Why it's wrong: The function name implies validation but always returns True.
Remediation: Implement actual token validation logic.

## Finding 2
Severity: Medium
File: src/utils.py
Line: 10
Pattern: Dead branch
Confidence: Likely
Evidence:
```
if False:
    do_cleanup()
```
Why it's wrong: Unreachable code — condition is always False.
Remediation: Remove the dead branch or fix the condition.

## Top 5 Priorities (this agent only)
1. Finding #1 — Naming lie in validate_token
2. Finding #2 — Dead branch in utils
"""


class TestParseWellFormed(unittest.TestCase):
    def setUp(self):
        self.result = parse_agent_tmp(_WELL_FORMED_TMP, agent_name="code-reviewer")

    def test_status_complete(self):
        self.assertEqual(self.result["status"], STATUS_COMPLETE)

    def test_agent_from_header(self):
        self.assertEqual(self.result["agent"], "code-reviewer")

    def test_finding_count(self):
        self.assertEqual(self.result["finding_count"], 2)

    def test_two_findings_parsed(self):
        self.assertEqual(len(self.result["findings"]), 2)

    def test_finding1_severity(self):
        self.assertEqual(self.result["findings"][0]["severity"], "High")

    def test_finding1_file(self):
        self.assertEqual(self.result["findings"][0]["file"], "src/auth.py")

    def test_finding1_line(self):
        self.assertEqual(self.result["findings"][0]["line"], 42)

    def test_finding1_pattern(self):
        self.assertEqual(self.result["findings"][0]["pattern"], "Naming lie")

    def test_finding1_confidence(self):
        self.assertEqual(self.result["findings"][0]["confidence"], "Certain")

    def test_finding1_evidence_contains_code(self):
        ev = self.result["findings"][0]["evidence"]
        self.assertIn("validate_token", ev)

    def test_finding1_why(self):
        self.assertIn("always returns True", self.result["findings"][0]["why"])

    def test_finding1_remediation(self):
        self.assertIn("actual token validation", self.result["findings"][0]["remediation"])

    def test_finding1_agent(self):
        self.assertEqual(self.result["findings"][0]["agent"], "code-reviewer")

    def test_finding1_tags_empty(self):
        self.assertEqual(self.result["findings"][0]["tags"], [])

    def test_finding2_severity(self):
        self.assertEqual(self.result["findings"][1]["severity"], "Medium")

    def test_finding2_file(self):
        self.assertEqual(self.result["findings"][1]["file"], "src/utils.py")

    def test_finding2_pattern(self):
        self.assertEqual(self.result["findings"][1]["pattern"], "Dead branch")

    def test_top5_trailer_not_in_findings(self):
        # The Top 5 Priorities section must not produce a Finding
        self.assertEqual(len(self.result["findings"]), 2)

    def test_reason_empty_on_complete(self):
        self.assertEqual(self.result["reason"], "")


class TestStatusFailed(unittest.TestCase):
    def test_failed_with_reason(self):
        text = "# Agent: qa-engineer\n# Status: failed\n# Reason: Context exceeded\n"
        result = parse_agent_tmp(text, agent_name="qa-engineer")
        self.assertEqual(result["status"], STATUS_FAILED)
        self.assertEqual(result["reason"], "Context exceeded")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["finding_count"], 0)

    def test_failed_no_reason_has_default(self):
        text = "# Agent: qa-engineer\n# Status: failed\n"
        result = parse_agent_tmp(text)
        self.assertEqual(result["status"], STATUS_FAILED)
        self.assertIsInstance(result["reason"], str)
        self.assertTrue(len(result["reason"]) > 0)

    def test_agent_from_hint_when_header_missing(self):
        text = "# Status: failed\n# Reason: boom\n"
        result = parse_agent_tmp(text, agent_name="architect")
        self.assertEqual(result["agent"], "architect")


class TestStatusClean(unittest.TestCase):
    def test_count_zero_no_blocks(self):
        text = "# Agent: architect\n# Status: complete\n# Finding count: 0\n"
        result = parse_agent_tmp(text)
        self.assertEqual(result["status"], STATUS_CLEAN)
        self.assertEqual(result["finding_count"], 0)
        self.assertEqual(result["findings"], [])


class TestStatusComplete(unittest.TestCase):
    def test_single_finding(self):
        text = """\
# Agent: security-reviewer
# Status: complete
# Finding count: 1

## Finding 1
Severity: Critical
File: src/login.py
Line: 5
Pattern: SQL injection
Confidence: Certain
Evidence:
```
query = "SELECT * FROM users WHERE id = " + user_id
```
Why it's wrong: String concatenation in SQL query allows injection.
Remediation: Use parameterised queries.
"""
        result = parse_agent_tmp(text)
        self.assertEqual(result["status"], STATUS_COMPLETE)
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["severity"], "Critical")


class TestMalformedFindingBlock(unittest.TestCase):
    def test_missing_severity_skipped(self):
        text = """\
# Agent: code-reviewer
# Status: complete
# Finding count: 1

## Finding 1
File: src/foo.py
Line: 1
Pattern: Something bad
Confidence: Certain
Evidence:
```
code here
```
Why it's wrong: Bad code.
Remediation: Fix it.
"""
        result = parse_agent_tmp(text)
        # Finding is skipped because Severity is missing
        self.assertEqual(len(result["findings"]), 0)

    def test_missing_file_skipped(self):
        text = """\
# Agent: code-reviewer
# Status: complete
# Finding count: 1

## Finding 1
Severity: High
Line: 1
Pattern: Something bad
Confidence: Certain
Evidence:
```
code here
```
Why it's wrong: Bad code.
Remediation: Fix it.
"""
        result = parse_agent_tmp(text)
        self.assertEqual(len(result["findings"]), 0)

    def test_missing_line_skipped(self):
        text = """\
# Agent: code-reviewer
# Status: complete
# Finding count: 1

## Finding 1
Severity: High
File: src/foo.py
Pattern: Something bad
Confidence: Certain
Evidence:
```
code here
```
Why it's wrong: Bad.
Remediation: Fix.
"""
        result = parse_agent_tmp(text)
        self.assertEqual(len(result["findings"]), 0)

    def test_missing_pattern_skipped(self):
        text = """\
# Agent: code-reviewer
# Status: complete
# Finding count: 1

## Finding 1
Severity: High
File: src/foo.py
Line: 5
Confidence: Certain
Evidence:
```
code here
```
Why it's wrong: Bad.
Remediation: Fix.
"""
        result = parse_agent_tmp(text)
        self.assertEqual(len(result["findings"]), 0)

    def test_valid_finding_alongside_malformed_is_kept(self):
        text = """\
# Agent: code-reviewer
# Status: complete
# Finding count: 2

## Finding 1
Severity: High
File: src/auth.py
Line: 10
Pattern: Off by one
Confidence: Likely
Evidence:
```
for i in range(n+1):
```
Why it's wrong: Off by one.
Remediation: Use range(n).

## Finding 2
File: src/other.py
Line: 20
Pattern: Missing severity
Confidence: Certain
Evidence:
```
some code
```
Why it's wrong: Bad.
Remediation: Fix.
"""
        result = parse_agent_tmp(text)
        # Finding 1 is valid; Finding 2 is missing Severity → skipped
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["pattern"], "Off by one")


class TestFencedEvidenceWithInternalBackticks(unittest.TestCase):
    def test_evidence_with_internal_backticks(self):
        # Evidence block contains a backtick-style inline code inside the fence.
        # The outer fence uses ``` and the inner content uses single backticks.
        text = """\
# Agent: architect
# Status: complete
# Finding count: 1

## Finding 1
Severity: Medium
File: src/example.py
Line: 3
Pattern: Misuse of eval
Confidence: Speculative
Evidence:
```
result = eval(`user_input`)
```
Why it's wrong: eval is dangerous.
Remediation: Use ast.literal_eval.
"""
        result = parse_agent_tmp(text)
        self.assertEqual(len(result["findings"]), 1)
        ev = result["findings"][0]["evidence"]
        self.assertIn("eval", ev)


class TestTopPrioritiesTrailerIgnored(unittest.TestCase):
    def test_trailer_does_not_create_finding(self):
        result = parse_agent_tmp(_WELL_FORMED_TMP)
        # Only 2 findings despite the Top 5 Priorities section
        self.assertEqual(len(result["findings"]), 2)

    def test_trailer_content_not_in_finding_fields(self):
        result = parse_agent_tmp(_WELL_FORMED_TMP)
        for f in result["findings"]:
            self.assertNotIn("Priorities", f.get("pattern", ""))


class TestEmptyInput(unittest.TestCase):
    def test_empty_string(self):
        result = parse_agent_tmp("")
        # No findings, status inferred as complete with 0 count
        self.assertIn(result["status"], (STATUS_CLEAN, STATUS_COMPLETE))
        self.assertEqual(result["findings"], [])

    def test_none_input(self):
        result = parse_agent_tmp(None)
        self.assertEqual(result["findings"], [])


# ---------------------------------------------------------------------------
# Fix 2 regression — STATUS_MISSING from cmd_consume_tmp
# ---------------------------------------------------------------------------


class TestConsumeTmpStatusMissing(unittest.TestCase):
    """Fix 2: cmd_consume_tmp emits status="missing" when --tmp file does not exist."""

    def _run_consume_tmp(self, tmp_path, agent=""):
        """Invoke cmd_consume_tmp via argparse Namespace; return (stdout_json, exit_code)."""
        from _audit._cli import cmd_consume_tmp

        ns = argparse.Namespace(tmp=tmp_path, agent=agent)
        captured = []
        original_write = sys.stdout.write

        def _capture(s):
            captured.append(s)

        sys.stdout.write = _capture
        try:
            code = cmd_consume_tmp(ns)
        finally:
            sys.stdout.write = original_write

        output = "".join(captured)
        parsed = json.loads(output) if output.strip() else {}
        return parsed, code

    def test_nonexistent_tmp_path_gives_status_missing(self):
        # Use a path that definitely does not exist
        nonexistent = os.path.join(tempfile.gettempdir(), "audit_no_such_file_xyz_123.md")
        if os.path.exists(nonexistent):
            os.unlink(nonexistent)

        result, code = self._run_consume_tmp(nonexistent, agent="code-reviewer")
        self.assertEqual(result["status"], STATUS_MISSING)
        self.assertEqual(result["finding_count"], 0)
        self.assertEqual(result["findings"], [])
        self.assertEqual(code, 2)

    def test_missing_status_string_value(self):
        nonexistent = os.path.join(tempfile.gettempdir(), "audit_no_such_file_xyz_456.md")
        if os.path.exists(nonexistent):
            os.unlink(nonexistent)

        result, _ = self._run_consume_tmp(nonexistent)
        self.assertEqual(result["status"], "missing")


# ---------------------------------------------------------------------------
# Fix 3 regression — finding_count always equals len(findings)
# ---------------------------------------------------------------------------


class TestFindingCountConsistency(unittest.TestCase):
    """Fix 3: finding_count in returned dict always equals len(findings)."""

    def test_header_count_zero_but_real_blocks_present(self):
        # Malformed file: header says 0 but there is one valid finding block.
        # finding_count should be 1 (actual parsed), not 0 (declared).
        text = """\
# Agent: code-reviewer
# Status: complete
# Finding count: 0

## Finding 1
Severity: High
File: src/auth.py
Line: 42
Pattern: Naming lie
Confidence: Certain
Evidence:
```
def validate_token(t):
    return True
```
Why it's wrong: Always returns True.
Remediation: Implement validation.
"""
        result = parse_agent_tmp(text, agent_name="code-reviewer")
        # The declared count is 0 but one block was parsed
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["finding_count"], len(result["findings"]),
                         "finding_count must equal len(findings)")
        self.assertEqual(result["finding_count"], 1)

    def test_header_count_matches_parsed_no_change(self):
        # Normal case: header count == actual parsed. finding_count == 2.
        result = parse_agent_tmp(_WELL_FORMED_TMP)
        self.assertEqual(result["finding_count"], len(result["findings"]))

    def test_finding_count_equals_len_for_single_finding(self):
        text = """\
# Agent: security-reviewer
# Status: complete
# Finding count: 1

## Finding 1
Severity: Critical
File: src/login.py
Line: 5
Pattern: SQL injection
Confidence: Certain
Evidence:
```
query = "SELECT * FROM users WHERE id = " + user_id
```
Why it's wrong: String concatenation in SQL query allows injection.
Remediation: Use parameterised queries.
"""
        result = parse_agent_tmp(text)
        self.assertEqual(result["finding_count"], len(result["findings"]))
        self.assertEqual(result["finding_count"], 1)


# ---------------------------------------------------------------------------
# Step 3 — Category field parsing
# ---------------------------------------------------------------------------

# A finding block template used by category tests.
# Slots: {category_line}
_FINDING_BLOCK_TEMPLATE = """\
# Agent: code-reviewer
# Status: complete
# Finding count: 1

## Finding 1
Severity: High
File: src/foo.py
Line: 10
Pattern: Some pattern
{category_line}Confidence: Certain
Evidence:
```
code here
```
Why it's wrong: Bad code.
Remediation: Fix it.
"""


def _make_finding_with_category(category_value):
    """Return a well-formed tmp-file text with the given Category: line."""
    line = "Category: {0}\n".format(category_value)
    return _FINDING_BLOCK_TEMPLATE.format(category_line=line)


def _make_finding_no_category():
    """Return a well-formed tmp-file text with no Category: line at all."""
    return _FINDING_BLOCK_TEMPLATE.format(category_line="")


class TestCategoryValidDeclared(unittest.TestCase):
    """A finding with a valid Category: value carries that value in the dict."""

    def test_system_design(self):
        result = parse_agent_tmp(_make_finding_with_category("system_design"))
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["category"], "system_design")

    def test_best_practice(self):
        result = parse_agent_tmp(_make_finding_with_category("best_practice"))
        self.assertEqual(result["findings"][0]["category"], "best_practice")

    def test_duplication(self):
        result = parse_agent_tmp(_make_finding_with_category("duplication"))
        self.assertEqual(result["findings"][0]["category"], "duplication")

    def test_security(self):
        result = parse_agent_tmp(_make_finding_with_category("security"))
        self.assertEqual(result["findings"][0]["category"], "security")

    def test_blind_spot(self):
        result = parse_agent_tmp(_make_finding_with_category("blind_spot"))
        self.assertEqual(result["findings"][0]["category"], "blind_spot")

    def test_mislogic_explicit(self):
        result = parse_agent_tmp(_make_finding_with_category("mislogic"))
        self.assertEqual(result["findings"][0]["category"], "mislogic")


class TestCategoryKeyPresent(unittest.TestCase):
    """The key 'category' is always present in the output dict regardless of Category: line."""

    def test_key_present_with_valid_category(self):
        result = parse_agent_tmp(_make_finding_with_category("security"))
        self.assertIn("category", result["findings"][0])

    def test_key_present_with_no_category_line(self):
        result = parse_agent_tmp(_make_finding_no_category())
        self.assertIn("category", result["findings"][0])


class TestCategoryInvalidDefaultsMislogic(unittest.TestCase):
    """An invalid Category: value silently defaults to 'mislogic'."""

    def test_bogus_value(self):
        result = parse_agent_tmp(_make_finding_with_category("bogus_value"))
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["category"], "mislogic")

    def test_empty_ish_spaces(self):
        # A Category: line with only spaces after the colon
        text = _FINDING_BLOCK_TEMPLATE.format(category_line="Category:   \n")
        result = parse_agent_tmp(text)
        self.assertEqual(result["findings"][0]["category"], "mislogic")

    def test_typo_value(self):
        result = parse_agent_tmp(_make_finding_with_category("SystemDesign"))
        self.assertEqual(result["findings"][0]["category"], "mislogic")


class TestCategoryMissingDefaultsMislogic(unittest.TestCase):
    """A finding block with no Category: line defaults to 'mislogic'."""

    def test_no_category_line(self):
        result = parse_agent_tmp(_make_finding_no_category())
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["category"], "mislogic")

    def test_existing_well_formed_fixture_defaults_mislogic(self):
        # The existing _WELL_FORMED_TMP fixture has no Category: lines.
        result = parse_agent_tmp(_WELL_FORMED_TMP)
        for f in result["findings"]:
            self.assertEqual(f["category"], "mislogic")


class TestCategoryBetweenPatternAndConfidence(unittest.TestCase):
    """Category: sitting between Pattern: and Confidence: does not bleed into either."""

    _TEXT = """\
# Agent: architect
# Status: complete
# Finding count: 1

## Finding 1
Severity: Medium
File: src/layer.py
Line: 5
Pattern: Layer violation
Category: system_design
Confidence: Likely
Evidence:
```
import ui from db
```
Why it's wrong: Presentation imports storage layer directly.
Remediation: Introduce a service layer.
"""

    def setUp(self):
        self.result = parse_agent_tmp(self._TEXT)

    def test_one_finding_parsed(self):
        self.assertEqual(len(self.result["findings"]), 1)

    def test_category_correct(self):
        self.assertEqual(self.result["findings"][0]["category"], "system_design")

    def test_pattern_not_contaminated(self):
        # Pattern should be exactly "Layer violation", not include "Category:..."
        self.assertEqual(self.result["findings"][0]["pattern"], "Layer violation")

    def test_confidence_not_contaminated(self):
        # Confidence should be exactly "Likely", not include "system_design..."
        self.assertEqual(self.result["findings"][0]["confidence"], "Likely")

    def test_why_correct(self):
        self.assertIn("storage layer", self.result["findings"][0]["why"])


if __name__ == "__main__":
    unittest.main()
