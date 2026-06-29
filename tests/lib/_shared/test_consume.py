"""Tests for src/devforge/lib/_shared/_consume.py.

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

from _shared._consume import (  # noqa: E402
    ParsedFinding,
    STATUS_CLEAN,
    STATUS_COMPLETE,
    STATUS_FAILED,
    STATUS_MISSING,
    _normalize_label_lines,
    _strip_inline_code,
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


# ---------------------------------------------------------------------------
# [CONSTITUTION-VIOLATION] tag lifting (tag-plumbing fix)
# ---------------------------------------------------------------------------

# Template for constitution-violation tag tests.
# Slots: {pattern_line}, {why_line}
_CV_BLOCK_TEMPLATE = """\
# Agent: architect
# Status: complete
# Finding count: 1

## Finding 1
Severity: High
File: src/orders/use_case.py
Line: 38
Pattern: {pattern_line}
Category: system_design
Confidence: Certain
Evidence:
```
const data = localStorage.getItem('cart');
```
Why it's wrong: {why_line}
Remediation: Route through the domain service layer.
"""


class TestConstitutionViolationTagLifting(unittest.TestCase):
    """[CONSTITUTION-VIOLATION] marker emitted by agents (inline in Pattern or Why)
    must be lifted into the structured ParsedFinding.tags list so that:
      - _report._bucket_finding routes to the Constitution Violations bucket, and
      - _verify._has_constitution_tag / _is_high_stakes fire for the D7 carve-out.
    """

    def _parse(self, pattern_line, why_line):
        text = _CV_BLOCK_TEMPLATE.format(
            pattern_line=pattern_line,
            why_line=why_line,
        )
        result = parse_agent_tmp(text, agent_name="architect")
        self.assertEqual(len(result["findings"]), 1)
        return result["findings"][0]

    # --- happy paths ----------------------------------------------------------

    def test_marker_in_pattern_yields_tag(self):
        """Pattern contains the exact bracketed marker → tags includes it."""
        f = self._parse(
            pattern_line="Domain use case reads directly from localStorage — constitution layer violation [CONSTITUTION-VIOLATION]",
            why_line="Presentation-layer storage accessed in the use-case layer.",
        )
        self.assertIn("[CONSTITUTION-VIOLATION]", f["tags"])

    def test_marker_in_why_yields_tag(self):
        """Pattern is clean; Why text contains the marker → tags includes it."""
        f = self._parse(
            pattern_line="Direct localStorage access in use-case layer",
            why_line="This crosses a layer boundary and is a [CONSTITUTION-VIOLATION].",
        )
        self.assertIn("[CONSTITUTION-VIOLATION]", f["tags"])

    def test_marker_in_both_pattern_and_why_idempotent(self):
        """Marker present in both Pattern and Why → exactly one tag entry."""
        f = self._parse(
            pattern_line="Layer violation [CONSTITUTION-VIOLATION]",
            why_line="Direct storage access [CONSTITUTION-VIOLATION] breaks the domain boundary.",
        )
        self.assertEqual(
            f["tags"].count("[CONSTITUTION-VIOLATION]"),
            1,
            "tag must appear at most once even when marker is in both fields",
        )

    # --- no-marker cases (precision guards) ----------------------------------

    def test_no_marker_yields_empty_tags(self):
        """A finding with NO marker in Pattern or Why → tags == []."""
        f = self._parse(
            pattern_line="Direct localStorage access in use-case layer",
            why_line="Presentation-layer storage accessed in the use-case layer.",
        )
        self.assertEqual(f["tags"], [])

    def test_prose_without_brackets_does_not_match(self):
        """Prose 'constitution violation' without brackets → tags == [] (no false positive)."""
        f = self._parse(
            pattern_line="This is a constitution violation without brackets",
            why_line="The naming convention violates the constitution rules here.",
        )
        self.assertEqual(
            f["tags"],
            [],
            "prose 'constitution violation' without brackets must NOT produce the tag",
        )

    def test_case_variant_does_not_match(self):
        """[constitution-violation] (lowercase) is NOT the exact marker → tags == []."""
        f = self._parse(
            pattern_line="Layer breach [constitution-violation] lowercase",
            why_line="Some explanation.",
        )
        self.assertEqual(f["tags"], [])

    # --- existing no-marker finding stays clean ------------------------------

    def test_existing_well_formed_fixture_tags_unchanged(self):
        """Existing _WELL_FORMED_TMP findings (no marker) still have tags == []."""
        result = parse_agent_tmp(_WELL_FORMED_TMP, agent_name="code-reviewer")
        for f in result["findings"]:
            self.assertEqual(f["tags"], [])

    # --- evidence is NOT scanned for the marker ------------------------------

    def test_marker_in_evidence_only_does_not_produce_tag(self):
        """Marker appearing only inside the Evidence fenced block is NOT lifted.

        Evidence contains verbatim source code; a [CONSTITUTION-VIOLATION] token
        there would be coincidental (e.g., a comment in code being audited),
        not a deliberate agent signal.
        """
        text = """\
# Agent: architect
# Status: complete
# Finding count: 1

## Finding 1
Severity: Medium
File: src/layer.py
Line: 7
Pattern: Some pattern without the marker
Category: system_design
Confidence: Likely
Evidence:
```
// [CONSTITUTION-VIOLATION] this comment exists in the source code
const x = 1;
```
Why it's wrong: The code is structured oddly.
Remediation: Restructure.
"""
        result = parse_agent_tmp(text, agent_name="architect")
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(
            result["findings"][0]["tags"],
            [],
            "marker inside Evidence (source code) must NOT produce the tag",
        )


# ---------------------------------------------------------------------------
# Plan 46 — label-tolerance & backtick-strip tests
# ---------------------------------------------------------------------------

# --- fixture helpers --------------------------------------------------------

def _make_decorated_finding(severity_line, file_line, line_line, pattern_line,
                             confidence_line, evidence_header, why_line="",
                             remediation_line=""):
    """Build a complete decorated-label finding block for tolerance tests."""
    why = why_line or "Why it's wrong: The code is wrong."
    remediation = remediation_line or "Remediation: Fix it."
    return (
        "# Agent: qa-reviewer\n"
        "# Status: complete\n"
        "# Finding count: 1\n"
        "\n"
        "## Finding 1\n"
        "{severity}\n"
        "{file}\n"
        "{line}\n"
        "{pattern}\n"
        "{confidence}\n"
        "{evidence}\n"
        "```\n"
        "some code here\n"
        "```\n"
        "{why}\n"
        "{remediation}\n"
    ).format(
        severity=severity_line,
        file=file_line,
        line=line_line,
        pattern=pattern_line,
        confidence=confidence_line,
        evidence=evidence_header,
        why=why,
        remediation=remediation,
    )


_DASH_BULLET_TMP = _make_decorated_finding(
    severity_line="- Severity: High",
    file_line="- File: src/components/RequestBar.css",
    line_line="- Line: 45",
    pattern_line="- Pattern: Hardcoded color value",
    confidence_line="- Confidence: Likely",
    evidence_header="- Evidence:",
)

_BOLD_LABEL_TMP = _make_decorated_finding(
    severity_line="**Severity**: High",
    file_line="**File**: src/components/RequestBar.css",
    line_line="**Line**: 45",
    pattern_line="**Pattern**: Hardcoded color value",
    confidence_line="**Confidence**: Likely",
    evidence_header="**Evidence**:",
)

_BOLD_COLON_INSIDE_TMP = _make_decorated_finding(
    severity_line="**Severity:** High",
    file_line="**File:** src/components/RequestBar.css",
    line_line="**Line:** 45",
    pattern_line="**Pattern:** Hardcoded color value",
    confidence_line="**Confidence:** Likely",
    evidence_header="**Evidence:**",
)

_COMBINED_DASH_BOLD_TMP = _make_decorated_finding(
    severity_line="- **Severity**: High",
    file_line="- **File**: src/components/RequestBar.css",
    line_line="- **Line**: 45",
    pattern_line="- **Pattern**: Hardcoded color value",
    confidence_line="- **Confidence**: Likely",
    evidence_header="- **Evidence**:",
)

_BACKTICK_FILE_TMP = _make_decorated_finding(
    severity_line="Severity: High",
    file_line="File: `src/RequestBar.css`",
    line_line="Line: 45",
    pattern_line="Pattern: Hardcoded color value",
    confidence_line="Confidence: Likely",
    evidence_header="Evidence:",
)

_BACKTICK_LINE_TMP = _make_decorated_finding(
    severity_line="Severity: High",
    file_line="File: src/RequestBar.css",
    line_line="Line: `12`",
    pattern_line="Pattern: Hardcoded color value",
    confidence_line="Confidence: Likely",
    evidence_header="Evidence:",
)


# --- test classes ------------------------------------------------------------

class TestDashBulletLabels(unittest.TestCase):
    """Dash-bullet prefixed labels parse to a valid finding."""

    def setUp(self):
        self.result = parse_agent_tmp(_DASH_BULLET_TMP, agent_name="qa-reviewer")

    def test_finding_count(self):
        self.assertEqual(self.result["finding_count"], 1)

    def test_severity(self):
        self.assertEqual(self.result["findings"][0]["severity"], "High")

    def test_file(self):
        self.assertEqual(self.result["findings"][0]["file"], "src/components/RequestBar.css")

    def test_line(self):
        self.assertEqual(self.result["findings"][0]["line"], 45)

    def test_pattern(self):
        self.assertEqual(self.result["findings"][0]["pattern"], "Hardcoded color value")

    def test_confidence(self):
        self.assertEqual(self.result["findings"][0]["confidence"], "Likely")

    def test_evidence_non_empty(self):
        self.assertIn("some code", self.result["findings"][0]["evidence"])


class TestBoldLabels(unittest.TestCase):
    """Bold-wrapped labels (**Label**:) parse to a valid finding."""

    def setUp(self):
        self.result = parse_agent_tmp(_BOLD_LABEL_TMP, agent_name="design-auditor")

    def test_finding_count(self):
        self.assertEqual(self.result["finding_count"], 1)

    def test_severity(self):
        self.assertEqual(self.result["findings"][0]["severity"], "High")

    def test_file(self):
        self.assertEqual(self.result["findings"][0]["file"], "src/components/RequestBar.css")

    def test_line(self):
        self.assertEqual(self.result["findings"][0]["line"], 45)

    def test_pattern(self):
        self.assertEqual(self.result["findings"][0]["pattern"], "Hardcoded color value")

    def test_confidence(self):
        self.assertEqual(self.result["findings"][0]["confidence"], "Likely")


class TestBoldColonInsideLabels(unittest.TestCase):
    """Bold labels with colon inside bold (**Label:**) parse correctly."""

    def setUp(self):
        self.result = parse_agent_tmp(_BOLD_COLON_INSIDE_TMP, agent_name="design-auditor")

    def test_finding_count(self):
        self.assertEqual(self.result["finding_count"], 1)

    def test_severity(self):
        self.assertEqual(self.result["findings"][0]["severity"], "High")

    def test_file(self):
        self.assertEqual(self.result["findings"][0]["file"], "src/components/RequestBar.css")

    def test_line(self):
        self.assertEqual(self.result["findings"][0]["line"], 45)


class TestCombinedDashBoldLabels(unittest.TestCase):
    """Combined '- **Label**:' decoration (dash bullet + bold) parses correctly."""

    def setUp(self):
        self.result = parse_agent_tmp(_COMBINED_DASH_BOLD_TMP, agent_name="qa-reviewer")

    def test_finding_count(self):
        self.assertEqual(self.result["finding_count"], 1)

    def test_severity(self):
        self.assertEqual(self.result["findings"][0]["severity"], "High")

    def test_file(self):
        self.assertEqual(self.result["findings"][0]["file"], "src/components/RequestBar.css")

    def test_line(self):
        self.assertEqual(self.result["findings"][0]["line"], 45)


class TestBacktickFileValue(unittest.TestCase):
    """File value wrapped in backticks is stripped before field regex runs."""

    def setUp(self):
        self.result = parse_agent_tmp(_BACKTICK_FILE_TMP, agent_name="code-reviewer")

    def test_finding_parsed(self):
        self.assertEqual(self.result["finding_count"], 1)

    def test_file_no_backticks(self):
        self.assertEqual(self.result["findings"][0]["file"], "src/RequestBar.css")

    def test_file_no_backtick_prefix(self):
        self.assertNotIn("`", self.result["findings"][0]["file"])


class TestBacktickLineValue(unittest.TestCase):
    """Line value wrapped in backticks is stripped so _RE_LINE (digits-only) matches."""

    def setUp(self):
        self.result = parse_agent_tmp(_BACKTICK_LINE_TMP, agent_name="code-reviewer")

    def test_finding_parsed(self):
        # RC2: without the fix, Line: `12` produces no regex match → block dropped.
        self.assertEqual(self.result["finding_count"], 1)

    def test_line_int(self):
        self.assertEqual(self.result["findings"][0]["line"], 12)


class TestBoldEvidenceHeader(unittest.TestCase):
    """Bold Evidence header (**Evidence:**) still captures the fenced code body."""

    _TEXT = (
        "# Agent: design-auditor\n"
        "# Status: complete\n"
        "# Finding count: 1\n"
        "\n"
        "## Finding 1\n"
        "**Severity**: High\n"
        "**File**: src/RequestBar.css\n"
        "**Line**: 7\n"
        "**Pattern**: Missing design token\n"
        "**Confidence**: Certain\n"
        "**Evidence:**\n"
        "```\n"
        "color: #FF5733;\n"
        "```\n"
        "**Why it's wrong**: Hardcoded color bypasses design tokens.\n"
        "**Remediation**: Use var(--color-primary) instead.\n"
    )

    def setUp(self):
        self.result = parse_agent_tmp(self._TEXT, agent_name="design-auditor")

    def test_finding_count(self):
        self.assertEqual(self.result["finding_count"], 1)

    def test_evidence_non_empty(self):
        ev = self.result["findings"][0]["evidence"]
        self.assertTrue(len(ev) > 0, "evidence must not be empty")

    def test_evidence_contains_code(self):
        self.assertIn("FF5733", self.result["findings"][0]["evidence"])

    def test_why_captured(self):
        self.assertIn("design tokens", self.result["findings"][0]["why"])

    def test_remediation_captured(self):
        self.assertIn("var(--color-primary)", self.result["findings"][0]["remediation"])


class TestFenceSafety(unittest.TestCase):
    """Lines inside a fenced Evidence block that start with '-'/'*' or contain
    '**' are passed through verbatim and must NOT be rewritten by normalization."""

    _TEXT = (
        "# Agent: code-reviewer\n"
        "# Status: complete\n"
        "# Finding count: 1\n"
        "\n"
        "## Finding 1\n"
        "Severity: Medium\n"
        "File: src/utils.py\n"
        "Line: 10\n"
        "Pattern: Defensive fence test\n"
        "Confidence: Likely\n"
        "Evidence:\n"
        "```\n"
        "- item with dash\n"
        "* item with star\n"
        "line with **bold** inside\n"
        "- **Severity**: this must NOT be rewritten\n"
        "```\n"
        "Why it's wrong: The code has structural issues.\n"
        "Remediation: Refactor.\n"
    )

    def setUp(self):
        self.result = parse_agent_tmp(self._TEXT, agent_name="code-reviewer")

    def test_finding_count(self):
        self.assertEqual(self.result["finding_count"], 1)

    def test_dash_line_verbatim(self):
        ev = self.result["findings"][0]["evidence"]
        self.assertIn("- item with dash", ev)

    def test_star_line_verbatim(self):
        ev = self.result["findings"][0]["evidence"]
        self.assertIn("* item with star", ev)

    def test_bold_inside_line_verbatim(self):
        ev = self.result["findings"][0]["evidence"]
        self.assertIn("**bold**", ev)

    def test_decorated_label_inside_fence_verbatim(self):
        # "- **Severity**: this must NOT be rewritten" must survive as-is in evidence.
        ev = self.result["findings"][0]["evidence"]
        self.assertIn("- **Severity**: this must NOT be rewritten", ev)


class TestLabelToleranceNonRegression(unittest.TestCase):
    """Bare-label findings from _WELL_FORMED_TMP parse byte-identically after
    normalization is introduced (normalization is idempotent on bare labels).
    Covers all fields including _extract_section paths (why, remediation, category)."""

    def setUp(self):
        self.result = parse_agent_tmp(_WELL_FORMED_TMP, agent_name="code-reviewer")

    def test_two_findings(self):
        self.assertEqual(self.result["finding_count"], 2)

    def test_first_finding_severity(self):
        self.assertEqual(self.result["findings"][0]["severity"], "High")

    def test_first_finding_file(self):
        self.assertEqual(self.result["findings"][0]["file"], "src/auth.py")

    def test_first_finding_line(self):
        self.assertEqual(self.result["findings"][0]["line"], 42)

    def test_first_finding_pattern(self):
        self.assertEqual(self.result["findings"][0]["pattern"], "Naming lie")

    def test_first_finding_confidence(self):
        self.assertEqual(self.result["findings"][0]["confidence"], "Certain")

    def test_first_finding_evidence(self):
        self.assertIn("validate_token", self.result["findings"][0]["evidence"])

    def test_first_finding_why(self):
        # Covers the _extract_section("Why it's wrong:") path.
        self.assertIn("always returns True", self.result["findings"][0]["why"])

    def test_first_finding_remediation(self):
        # Covers the _extract_section("Remediation:") path.
        self.assertIn("actual token validation", self.result["findings"][0]["remediation"])

    def test_first_finding_category(self):
        # No Category: line in _WELL_FORMED_TMP → default "mislogic".
        self.assertEqual(self.result["findings"][0]["category"], "mislogic")

    def test_second_finding_severity(self):
        self.assertEqual(self.result["findings"][1]["severity"], "Medium")


class TestProseNotMisdetected(unittest.TestCase):
    """Prose containing 'Severity is high' (no colon after label) inside a Why
    paragraph must NOT be mis-detected as a field line by normalization."""

    _TEXT = (
        "# Agent: code-reviewer\n"
        "# Status: complete\n"
        "# Finding count: 1\n"
        "\n"
        "## Finding 1\n"
        "Severity: High\n"
        "File: src/auth.py\n"
        "Line: 5\n"
        "Pattern: Token issue\n"
        "Confidence: Certain\n"
        "Evidence:\n"
        "```\n"
        "return True\n"
        "```\n"
        "Why it's wrong: The Severity is high in this case because the token\n"
        "validation is bypassed entirely.\n"
        "Remediation: Implement validation.\n"
    )

    def setUp(self):
        self.result = parse_agent_tmp(self._TEXT, agent_name="code-reviewer")

    def test_finding_count(self):
        self.assertEqual(self.result["finding_count"], 1)

    def test_why_contains_prose_severity(self):
        why = self.result["findings"][0]["why"]
        self.assertIn("Severity is high", why)

    def test_why_contains_full_prose(self):
        why = self.result["findings"][0]["why"]
        self.assertIn("validation is bypassed", why)


# ---------------------------------------------------------------------------
# _strip_inline_code direct unit tests
# ---------------------------------------------------------------------------

class TestStripInlineCode(unittest.TestCase):
    """Direct unit tests for the _strip_inline_code private helper."""

    def test_single_backtick_stripped(self):
        self.assertEqual(_strip_inline_code("`x`"), "x")

    def test_double_backtick_stripped(self):
        self.assertEqual(_strip_inline_code("``x``"), "x")

    def test_no_backtick_unchanged(self):
        self.assertEqual(_strip_inline_code("x"), "x")

    def test_empty_string_unchanged(self):
        self.assertEqual(_strip_inline_code(""), "")

    def test_path_value_stripped(self):
        self.assertEqual(
            _strip_inline_code("`src/RequestBar.css`"), "src/RequestBar.css"
        )

    def test_number_value_stripped(self):
        self.assertEqual(_strip_inline_code("`12`"), "12")

    def test_interior_backtick_preserved(self):
        # `a`b` — outer single backticks stripped, middle backtick survives.
        result = _strip_inline_code("`a`b`")
        self.assertEqual(result, "a`b")

    def test_mismatched_backtick_counts_unchanged(self):
        # `x`` — one backtick at start, two at end → not a matched pair → unchanged.
        self.assertEqual(_strip_inline_code("`x``"), "`x``")

    def test_triple_backtick_stripped(self):
        self.assertEqual(_strip_inline_code("```x```"), "x")

    def test_value_not_ending_in_backtick_unchanged(self):
        # No trailing backtick → no outer pair → unchanged.
        self.assertEqual(_strip_inline_code("`src/foo.py"), "`src/foo.py")

    def test_value_with_spaces_stripped(self):
        self.assertEqual(_strip_inline_code("`hello world`"), "hello world")


class TestStarPlusBulletLabels(unittest.TestCase):
    """'*' and '+' list bullets (not just '-') are tolerated as label decoration."""

    _STAR_TEXT = _make_decorated_finding(
        severity_line="* Severity: High",
        file_line="* File: src/foo.py",
        line_line="* Line: 1",
        pattern_line="* Pattern: Some issue",
        confidence_line="* Confidence: Certain",
        evidence_header="* Evidence:",
    )

    _PLUS_TEXT = _make_decorated_finding(
        severity_line="+ Severity: High",
        file_line="+ File: src/foo.py",
        line_line="+ Line: 1",
        pattern_line="+ Pattern: Some issue",
        confidence_line="+ Confidence: Certain",
        evidence_header="+ Evidence:",
    )

    def test_star_bullet_finding_count(self):
        result = parse_agent_tmp(self._STAR_TEXT, agent_name="qa-reviewer")
        self.assertEqual(result["finding_count"], 1)

    def test_star_bullet_severity(self):
        result = parse_agent_tmp(self._STAR_TEXT, agent_name="qa-reviewer")
        self.assertEqual(result["findings"][0]["severity"], "High")

    def test_plus_bullet_finding_count(self):
        result = parse_agent_tmp(self._PLUS_TEXT, agent_name="qa-reviewer")
        self.assertEqual(result["finding_count"], 1)

    def test_plus_bullet_severity(self):
        result = parse_agent_tmp(self._PLUS_TEXT, agent_name="qa-reviewer")
        self.assertEqual(result["findings"][0]["severity"], "High")


class TestWhyInEvidenceBodyScoping(unittest.TestCase):
    """F1 regression: when the evidence fenced code body contains a line that
    starts with 'Why it's wrong:' (e.g. a code comment or a string literal in
    the code being audited), _extract_section called on the full block_text
    would pick that inside-evidence occurrence before the real post-evidence
    field.  The tail-scoping fix (why_rem_text = block_text[m_ev.end():])
    excludes everything inside the matched evidence block so only the real
    post-evidence 'Why it's wrong:' and 'Remediation:' are visible."""

    # Evidence body has a plain "Why it's wrong:" line (inside the fence, so
    # _normalize_label_lines does NOT touch it — it is already bare-label form
    # from whatever source).  The real Why it's wrong: comes after the fence.
    _TEXT = (
        "# Agent: code-reviewer\n"
        "# Status: complete\n"
        "# Finding count: 1\n"
        "\n"
        "## Finding 1\n"
        "Severity: High\n"
        "File: src/auth.py\n"
        "Line: 5\n"
        "Pattern: Misleading why in evidence\n"
        "Confidence: Certain\n"
        "Evidence:\n"
        "```\n"
        "Why it's wrong: misleading line inside evidence body\n"
        "return True\n"
        "```\n"
        "Why it's wrong: REAL POST-EVIDENCE WHY\n"
        "Remediation: Real remediation.\n"
    )

    def setUp(self):
        self.result = parse_agent_tmp(self._TEXT, agent_name="code-reviewer")

    def test_finding_count(self):
        self.assertEqual(self.result["finding_count"], 1)

    def test_why_is_real_post_evidence_value(self):
        why = self.result["findings"][0]["why"]
        self.assertIn("REAL POST-EVIDENCE WHY", why,
                      "why must come from post-evidence tail, not from inside evidence body")

    def test_why_excludes_inside_evidence_body(self):
        why = self.result["findings"][0]["why"]
        self.assertNotIn("misleading line inside evidence body", why,
                         "why must not be the line that appeared inside the fenced Evidence block")


# ---------------------------------------------------------------------------
# Plan-46 reproduction tests: the two confirmed silent-drop scenarios
# ---------------------------------------------------------------------------

class TestPlan46ReproductionDashBullet(unittest.TestCase):
    """Reproduction: qa-reviewer writes '- Severity:' dash-bullet fields.
    Without the fix: finding_count == 0 (silent drop).
    With the fix:    finding_count == 1.
    """

    _TEXT = (
        "# Agent: qa-reviewer\n"
        "# Status: complete\n"
        "# Finding count: 1\n"
        "\n"
        "## Finding 1\n"
        "- Severity: High\n"
        "- File: src/RequestBar.css\n"
        "- Line: 10\n"
        "- Pattern: Missing token binding\n"
        "- Confidence: Likely\n"
        "- Evidence:\n"
        "```\n"
        "color: #FF5733;\n"
        "```\n"
        "- Why it's wrong: Hardcoded color bypasses design tokens.\n"
        "- Remediation: Use var(--color-primary) instead.\n"
    )

    def test_finding_count_is_one(self):
        result = parse_agent_tmp(self._TEXT, agent_name="qa-reviewer")
        self.assertEqual(result["finding_count"], 1)

    def test_status_complete(self):
        result = parse_agent_tmp(self._TEXT, agent_name="qa-reviewer")
        self.assertEqual(result["status"], STATUS_COMPLETE)


class TestPlan46ReproductionBoldBacktick(unittest.TestCase):
    """Reproduction: design-auditor writes '**Severity**:' bold labels and
    backtick-wrapped File/Line values.
    Without the fix: finding_count == 0 (silent drop — Line: `12` kills _RE_LINE).
    With the fix:    finding_count == 1, file has no backticks, line is an int.
    """

    _TEXT = (
        "# Agent: design-auditor\n"
        "# Status: complete\n"
        "# Finding count: 1\n"
        "\n"
        "## Finding 1\n"
        "**Severity**: High\n"
        "**File**: `src/RequestBar.css`\n"
        "**Line**: `12`\n"
        "**Pattern**: Hardcoded spacing value\n"
        "**Confidence**: Certain\n"
        "**Evidence:**\n"
        "```\n"
        "padding: 8px;\n"
        "```\n"
        "**Why it's wrong**: Hardcoded spacing bypasses spacing tokens.\n"
        "**Remediation**: Use var(--space-2) instead.\n"
    )

    def test_finding_count_is_one(self):
        result = parse_agent_tmp(self._TEXT, agent_name="design-auditor")
        self.assertEqual(result["finding_count"], 1)

    def test_status_complete(self):
        result = parse_agent_tmp(self._TEXT, agent_name="design-auditor")
        self.assertEqual(result["status"], STATUS_COMPLETE)

    def test_file_no_backticks(self):
        result = parse_agent_tmp(self._TEXT, agent_name="design-auditor")
        self.assertEqual(result["findings"][0]["file"], "src/RequestBar.css")

    def test_line_is_int_12(self):
        result = parse_agent_tmp(self._TEXT, agent_name="design-auditor")
        self.assertEqual(result["findings"][0]["line"], 12)


if __name__ == "__main__":
    unittest.main()
