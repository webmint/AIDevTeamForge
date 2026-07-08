"""Tests for src/devforge/lib/_shared/_verify.py.

Coverage (all functions):

route_refutation:
  - Refuter is never the author (basic case).
  - Priority order: code-reviewer is preferred first unless it is the author.
  - code-reviewer's own findings route to architect (code-reviewer excluded as
    author; architect is the next priority).
  - Only present finders are eligible refuters.
  - Sole-finder self-refute fires only when the author is the ONLY present
    finder (no other finder available).
  - A finding whose author is absent from present_finders still gets a valid
    non-author refuter (the first present finder in priority order is not the
    absent author either).
  - Empty findings input returns [].
  - Groups are ordered by first refuter assignment.

consume_verdicts:
  - Parses header + per-verdict blocks correctly (round-trip of the real
    preamble format).
  - Handles # Status: failed + # Reason: line.
  - Handles a clean / zero-verdict file (declared count 0).
  - Returns 'complete' status when blocks are present.
  - Missing required field in a verdict block → block skipped (not crashed).
  - Empty text returns clean status.

apply_verdicts (round-trip via consume_verdicts parse):
  - confirmed finding → confirmed bucket, carries verify_confidence="confirmed".
  - dismissed finding (counter-quote present) → dismissed bucket.
  - dismissed finding (no counter-quote, literal marker) → dismissed bucket.
  - HIGH-stakes uncertain (category == "security") → contested bucket.
  - HIGH-stakes uncertain ([CONSTITUTION-VIOLATION] tag) → contested bucket.
  - LOW-stakes uncertain (mislogic) → uncertain bucket.
  - dismissed verdict on a [CONSTITUTION-VIOLATION] finding → contested (carve-out).
  - Verdict matching no finding → skipped (not crashed); unmatched finding uses
    no-verdict default (uncertain / contested by category).
  - Empty inputs behave (no crash, all buckets empty lists).
  - Multiple verdicts for the same key: highest-precedence wins.

CLI smoke tests:
  - route-refutation exits 2 when --findings missing.
  - consume-verdicts exits 2 when --verdicts file does not exist.
  - apply-verdicts exits 0 and emits four bucket keys.

route_refutation priority= parameter (new in _shared extraction):
  - priority=None (default) uses _REFUTER_PRIORITY — byte-identical to
    pre-extraction behaviour.
  - Explicit priority list overrides the default and changes refuter selection.
  - Sole-finder and empty-priority edge cases handled correctly.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared._verify import (  # noqa: E402
    VERDICT_STATUS_CLEAN,
    VERDICT_STATUS_COMPLETE,
    VERDICT_STATUS_FAILED,
    _REFUTER_PRIORITY,
    apply_verdicts,
    consume_verdicts,
    render_verify_brief,
    route_refutation,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

# A minimal finding dict matching ParsedFinding shape (dict form after
# dataclasses.asdict).
def _finding(agent="code-reviewer", file="src/a.py", line=10,
             pattern="Naming lie", category="mislogic", tags=None):
    return {
        "agent": agent,
        "file": file,
        "line": line,
        "pattern": pattern,
        "severity": "High",
        "confidence": "Likely",
        "evidence": "x = bad_code()",
        "why": "why text",
        "remediation": "fix it",
        "category": category,
        "tags": tags if tags is not None else [],
    }


def _verdict_file(refuter="code-reviewer", status="complete", verdicts=None,
                  reason=""):
    """Build a verdict file string matching the refutation-preamble.md contract."""
    if verdicts is None:
        verdicts = []

    count = len(verdicts)
    lines = [
        "# Refuter: {0}".format(refuter),
        "# Status: {0}".format(status),
    ]
    if reason:
        lines.append("# Reason: {0}".format(reason))
    lines.append("# Verdict count: {0}".format(count))
    lines.append("")

    for i, v in enumerate(verdicts, 1):
        lines.append("## Verdict {0}".format(i))
        lines.append("File: {0}".format(v.get("file", "src/a.py")))
        lines.append("Line: {0}".format(v.get("line", 10)))
        lines.append("Pattern: {0}".format(v.get("pattern", "Naming lie")))
        lines.append("Agent: {0}".format(v.get("agent", "code-reviewer")))
        lines.append("Verdict: {0}".format(v.get("verdict", "dismissed")))
        lines.append("Justification: {0}".format(v.get("justification", "no defect")))
        lines.append("Evidence:")
        lines.append("```")
        lines.append(v.get("evidence", "(no counter-quote — finding is not demonstrable)"))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tests: route_refutation
# ---------------------------------------------------------------------------

class TestRouteRefutationBasic(unittest.TestCase):

    def test_refuter_is_never_the_author(self):
        """Basic: the assigned refuter must differ from the finding's author."""
        findings = [_finding(agent="code-reviewer")]
        present = ["code-reviewer", "architect", "qa-reviewer", "security-reviewer"]
        groups = route_refutation(findings, present)
        self.assertEqual(len(groups), 1)
        refuter = groups[0]["refuter"]
        self.assertNotEqual(refuter, "code-reviewer")

    def test_priority_order_code_reviewer_first(self):
        """Non-code-reviewer author: code-reviewer should be selected first."""
        findings = [_finding(agent="security-reviewer")]
        present = ["code-reviewer", "architect", "qa-reviewer", "security-reviewer"]
        groups = route_refutation(findings, present)
        self.assertEqual(groups[0]["refuter"], "code-reviewer")

    def test_code_reviewer_own_findings_route_to_architect(self):
        """code-reviewer's findings are excluded from itself; architect is next."""
        findings = [_finding(agent="code-reviewer")]
        present = ["code-reviewer", "architect", "qa-reviewer", "security-reviewer"]
        groups = route_refutation(findings, present)
        self.assertEqual(groups[0]["refuter"], "architect")

    def test_only_present_finders_are_eligible(self):
        """If code-reviewer and architect are absent, qa-reviewer takes over."""
        findings = [_finding(agent="security-reviewer")]
        present = ["qa-reviewer", "security-reviewer"]
        groups = route_refutation(findings, present)
        # code-reviewer not present; architect not present; qa-reviewer is present and != author
        self.assertEqual(groups[0]["refuter"], "qa-reviewer")

    def test_sole_finder_self_refutes(self):
        """Sole-finder edge case: author is the only present finder → self-refute."""
        findings = [_finding(agent="qa-reviewer")]
        present = ["qa-reviewer"]  # sole finder
        groups = route_refutation(findings, present)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["refuter"], "qa-reviewer")

    def test_sole_finder_fires_only_when_truly_sole(self):
        """Sole-finder does NOT fire when another present finder is available."""
        findings = [_finding(agent="qa-reviewer")]
        present = ["qa-reviewer", "architect"]
        groups = route_refutation(findings, present)
        # architect is present and != qa-reviewer; code-reviewer absent; architect is next
        self.assertEqual(groups[0]["refuter"], "architect")

    def test_absent_author_gets_valid_refuter(self):
        """A finding whose agent is not in present_finders still gets a valid refuter."""
        # author = "backend-engineer" (not a known finder, not in present list)
        findings = [_finding(agent="backend-engineer")]
        present = ["qa-reviewer", "security-reviewer"]
        groups = route_refutation(findings, present)
        # code-reviewer absent, architect absent, qa-reviewer present and != backend-engineer
        self.assertEqual(groups[0]["refuter"], "qa-reviewer")

    def test_empty_findings_returns_empty(self):
        """Empty findings list returns an empty routing map."""
        groups = route_refutation([], ["code-reviewer", "architect"])
        self.assertEqual(groups, [])

    def test_groups_by_refuter(self):
        """Multiple findings with different authors group correctly by refuter."""
        f1 = _finding(agent="qa-reviewer", line=1)
        f2 = _finding(agent="security-reviewer", line=2)
        present = ["code-reviewer", "architect", "qa-reviewer", "security-reviewer"]
        groups = route_refutation([f1, f2], present)
        # Both qa-reviewer and security-reviewer are authored by present finders.
        # f1 (qa-reviewer) → code-reviewer (first present non-author)
        # f2 (security-reviewer) → code-reviewer (first present non-author)
        # So both map to code-reviewer → one group with 2 findings.
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["refuter"], "code-reviewer")
        self.assertEqual(len(groups[0]["findings"]), 2)

    def test_different_refuters_form_separate_groups(self):
        """Findings by code-reviewer and architect each get their own refuter."""
        f1 = _finding(agent="code-reviewer", line=1)
        f2 = _finding(agent="architect", line=2)
        present = ["code-reviewer", "architect", "qa-reviewer", "security-reviewer"]
        groups = route_refutation([f1, f2], present)
        refuters = [g["refuter"] for g in groups]
        # f1 (code-reviewer) → architect
        # f2 (architect) → code-reviewer
        self.assertIn("architect", refuters)
        self.assertIn("code-reviewer", refuters)
        self.assertEqual(len(groups), 2)

    def test_groups_ordered_by_first_assignment(self):
        """Groups appear in the order the refuter was first assigned."""
        f1 = _finding(agent="code-reviewer", line=1)
        f2 = _finding(agent="security-reviewer", line=2)
        f3 = _finding(agent="code-reviewer", line=3)
        present = ["code-reviewer", "architect", "qa-reviewer", "security-reviewer"]
        groups = route_refutation([f1, f2, f3], present)
        # f1 → architect (first assigned)
        # f2 → code-reviewer (second assigned)
        # f3 → architect (already in group)
        self.assertEqual(groups[0]["refuter"], "architect")
        self.assertEqual(groups[1]["refuter"], "code-reviewer")
        self.assertEqual(len(groups[0]["findings"]), 2)  # f1 and f3

    def test_empty_present_finders_self_refute_fallback(self):
        """With empty present_finders, uses author as fallback refuter."""
        findings = [_finding(agent="code-reviewer")]
        groups = route_refutation(findings, [])
        # No present finders → sole-finder fallback → author self-refutes
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["refuter"], "code-reviewer")


# ---------------------------------------------------------------------------
# Tests: consume_verdicts
# ---------------------------------------------------------------------------

class TestConsumeVerdictsComplete(unittest.TestCase):

    def test_parses_complete_single_verdict(self):
        """A well-formed complete file with one verdict parses correctly."""
        text = _verdict_file(
            refuter="architect",
            verdicts=[{
                "file": "src/foo.py",
                "line": 42,
                "pattern": "Naming lie",
                "agent": "code-reviewer",
                "verdict": "dismissed",
                "justification": "code is correct",
                "evidence": "(no counter-quote — finding is not demonstrable)",
            }],
        )
        result = consume_verdicts(text)
        self.assertEqual(result["status"], VERDICT_STATUS_COMPLETE)
        self.assertEqual(result["refuter"], "architect")
        self.assertEqual(result["verdict_count"], 1)
        v = result["verdicts"][0]
        self.assertEqual(v["refuter"], "architect")
        self.assertEqual(v["file"], "src/foo.py")
        self.assertEqual(v["line"], 42)
        self.assertEqual(v["pattern"], "Naming lie")
        self.assertEqual(v["agent"], "code-reviewer")
        self.assertEqual(v["verdict"], "dismissed")
        self.assertEqual(v["justification"], "code is correct")

    def test_parses_confirmed_verdict_with_evidence(self):
        """A confirmed verdict parses and evidence block is captured."""
        text = _verdict_file(
            refuter="code-reviewer",
            verdicts=[{
                "file": "src/auth.py",
                "line": 10,
                "pattern": "Dead branch",
                "agent": "architect",
                "verdict": "confirmed",
                "justification": "off-by-one clearly present",
                "evidence": "if n > len(arr):  # should be >= len(arr)",
            }],
        )
        result = consume_verdicts(text)
        self.assertEqual(result["status"], VERDICT_STATUS_COMPLETE)
        v = result["verdicts"][0]
        self.assertEqual(v["verdict"], "confirmed")
        # evidence carries the verbatim code quote; justification carries "off-by-one"
        self.assertIn("off-by-one", v["justification"])
        self.assertIn("len(arr)", v["evidence"])

    def test_parses_uncertain_verdict(self):
        """An uncertain verdict parses correctly."""
        text = _verdict_file(
            refuter="qa-reviewer",
            verdicts=[{
                "file": "src/b.py",
                "line": 5,
                "pattern": "Missing guard",
                "agent": "security-reviewer",
                "verdict": "uncertain",
                "justification": "cannot determine from code",
                "evidence": "cannot resolve: external auth service unknown",
            }],
        )
        result = consume_verdicts(text)
        v = result["verdicts"][0]
        self.assertEqual(v["verdict"], "uncertain")

    def test_parses_multiple_verdicts(self):
        """Multiple verdict blocks all parse into the verdicts list."""
        text = _verdict_file(
            refuter="architect",
            verdicts=[
                {"file": "src/a.py", "line": 1, "pattern": "P1", "agent": "code-reviewer", "verdict": "dismissed"},
                {"file": "src/b.py", "line": 2, "pattern": "P2", "agent": "code-reviewer", "verdict": "confirmed",
                 "evidence": "x = 1"},
                {"file": "src/c.py", "line": 3, "pattern": "P3", "agent": "code-reviewer", "verdict": "uncertain"},
            ],
        )
        result = consume_verdicts(text)
        self.assertEqual(result["verdict_count"], 3)
        verdicts = result["verdicts"]
        self.assertEqual(verdicts[0]["verdict"], "dismissed")
        self.assertEqual(verdicts[1]["verdict"], "confirmed")
        self.assertEqual(verdicts[2]["verdict"], "uncertain")

    def test_count_is_actual_parsed_count(self):
        """verdict_count always reflects actual parsed blocks, not declared count."""
        # The _verdict_file helper sets count = len(verdicts); here we craft one
        # with a declared count of 5 but only 1 real block.
        text = (
            "# Refuter: code-reviewer\n"
            "# Status: complete\n"
            "# Verdict count: 5\n"
            "\n"
            "## Verdict 1\n"
            "File: src/a.py\n"
            "Line: 10\n"
            "Pattern: Naming lie\n"
            "Agent: architect\n"
            "Verdict: dismissed\n"
            "Justification: no defect\n"
            "Evidence:\n"
            "```\n"
            "(no counter-quote — finding is not demonstrable)\n"
            "```\n"
        )
        result = consume_verdicts(text)
        self.assertEqual(result["verdict_count"], 1)

    def test_invalid_verdict_value_skips_block(self):
        """A block with Verdict: bogusvalue is skipped (not crashed)."""
        text = (
            "# Refuter: architect\n"
            "# Status: complete\n"
            "# Verdict count: 1\n"
            "\n"
            "## Verdict 1\n"
            "File: src/a.py\n"
            "Line: 10\n"
            "Pattern: Naming lie\n"
            "Agent: code-reviewer\n"
            "Verdict: bogusvalue\n"
            "Justification: should be skipped\n"
            "Evidence:\n"
            "```\n"
            "some code\n"
            "```\n"
        )
        result = consume_verdicts(text)
        # bogus verdict → block skipped; 0 verdicts parsed
        self.assertEqual(result["verdict_count"], 0)
        self.assertEqual(result["verdicts"], [])


class TestConsumeVerdictsClean(unittest.TestCase):

    def test_clean_zero_verdict_file(self):
        """A complete file with declared count 0 and no blocks → clean status."""
        text = (
            "# Refuter: code-reviewer\n"
            "# Status: complete\n"
            "# Verdict count: 0\n"
        )
        result = consume_verdicts(text)
        self.assertEqual(result["status"], VERDICT_STATUS_CLEAN)
        self.assertEqual(result["verdict_count"], 0)
        self.assertEqual(result["verdicts"], [])

    def test_empty_text_returns_clean_or_complete(self):
        """Empty text: no status, no count → falls to complete with 0 verdicts."""
        result = consume_verdicts("")
        # No status header → raw_status == "" → proceeds to block scan.
        # No blocks → 0 verdicts.  declared_count is None (not 0) so NOT clean.
        # Falls through to VERDICT_STATUS_COMPLETE with 0 verdicts.
        # Acceptable behavior: status complete or clean, 0 verdicts.
        self.assertEqual(result["verdict_count"], 0)
        self.assertEqual(result["verdicts"], [])


class TestConsumeVerdictsFailed(unittest.TestCase):

    def test_failed_status_with_reason(self):
        """# Status: failed + # Reason: line → VERDICT_STATUS_FAILED with reason."""
        text = (
            "# Refuter: qa-reviewer\n"
            "# Status: failed\n"
            "# Reason: could not read the file\n"
        )
        result = consume_verdicts(text)
        self.assertEqual(result["status"], VERDICT_STATUS_FAILED)
        self.assertEqual(result["reason"], "could not read the file")
        self.assertEqual(result["refuter"], "qa-reviewer")
        self.assertEqual(result["verdicts"], [])

    def test_failed_status_without_reason(self):
        """# Status: failed without # Reason: uses a default reason string."""
        text = (
            "# Refuter: security-reviewer\n"
            "# Status: failed\n"
        )
        result = consume_verdicts(text)
        self.assertEqual(result["status"], VERDICT_STATUS_FAILED)
        self.assertTrue(len(result["reason"]) > 0)

    def test_missing_block_field_skipped_not_crashed(self):
        """A verdict block missing 'Agent:' is skipped, rest parses fine."""
        text = (
            "# Refuter: architect\n"
            "# Status: complete\n"
            "# Verdict count: 2\n"
            "\n"
            "## Verdict 1\n"
            "File: src/a.py\n"
            "Line: 10\n"
            "Pattern: Naming lie\n"
            # Agent: field MISSING — block should be skipped
            "Verdict: dismissed\n"
            "Justification: no defect\n"
            "Evidence:\n"
            "```\n"
            "(no counter-quote — finding is not demonstrable)\n"
            "```\n"
            "\n"
            "## Verdict 2\n"
            "File: src/b.py\n"
            "Line: 20\n"
            "Pattern: Dead branch\n"
            "Agent: code-reviewer\n"
            "Verdict: confirmed\n"
            "Justification: clearly wrong\n"
            "Evidence:\n"
            "```\n"
            "if False: pass\n"
            "```\n"
        )
        result = consume_verdicts(text)
        self.assertEqual(result["verdict_count"], 1)
        self.assertEqual(result["verdicts"][0]["file"], "src/b.py")


# ---------------------------------------------------------------------------
# Tests: apply_verdicts (round-trip from consume_verdicts parsed output)
# ---------------------------------------------------------------------------

class TestApplyVerdictsBasic(unittest.TestCase):

    def _parse_and_apply(self, findings, verdict_spec_list, refuter="architect"):
        """Round-trip helper: build verdict file → consume_verdicts → apply_verdicts."""
        text = _verdict_file(refuter=refuter, verdicts=verdict_spec_list)
        cv = consume_verdicts(text)
        verdicts = cv["verdicts"]
        return apply_verdicts(findings, verdicts)

    def test_confirmed_finding_in_confirmed_bucket(self):
        """A confirmed verdict lands in the confirmed bucket with verify_confidence."""
        f = _finding(agent="architect", file="src/a.py", line=10, pattern="P1", category="mislogic")
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/a.py", "line": 10, "pattern": "P1", "agent": "architect", "verdict": "confirmed",
              "evidence": "bad_code()"}],
            refuter="code-reviewer",
        )
        self.assertEqual(len(buckets["confirmed"]), 1)
        self.assertEqual(buckets["dismissed"], [])
        self.assertEqual(buckets["uncertain"], [])
        self.assertEqual(buckets["contested"], [])
        self.assertEqual(buckets["confirmed"][0]["verify_confidence"], "confirmed")

    def test_dismissed_finding_in_dismissed_bucket(self):
        """A dismissed verdict (counter-quote present) lands in dismissed."""
        f = _finding(agent="qa-reviewer", file="src/b.py", line=20, pattern="P2", category="mislogic")
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/b.py", "line": 20, "pattern": "P2", "agent": "qa-reviewer", "verdict": "dismissed",
              "evidence": "guard_that_makes_it_right()"}],
            refuter="code-reviewer",
        )
        self.assertEqual(buckets["dismissed"], [f])
        self.assertEqual(buckets["confirmed"], [])
        self.assertEqual(buckets["uncertain"], [])
        self.assertEqual(buckets["contested"], [])

    def test_dismissed_no_counter_quote_in_dismissed_bucket(self):
        """A dismissed verdict with the literal no-counter-quote marker lands in dismissed."""
        f = _finding(agent="qa-reviewer", file="src/c.py", line=30, pattern="P3", category="best_practice")
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/c.py", "line": 30, "pattern": "P3", "agent": "qa-reviewer", "verdict": "dismissed",
              "evidence": "(no counter-quote — finding is not demonstrable)"}],
            refuter="architect",
        )
        self.assertEqual(len(buckets["dismissed"]), 1)
        self.assertEqual(buckets["confirmed"], [])
        self.assertEqual(buckets["uncertain"], [])
        self.assertEqual(buckets["contested"], [])

    def test_low_stakes_uncertain_in_uncertain_bucket(self):
        """An uncertain verdict on a mislogic finding goes to the uncertain bucket."""
        f = _finding(agent="architect", file="src/d.py", line=5, pattern="P4", category="mislogic")
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/d.py", "line": 5, "pattern": "P4", "agent": "architect", "verdict": "uncertain",
              "evidence": "cannot resolve from code"}],
            refuter="code-reviewer",
        )
        self.assertEqual(len(buckets["uncertain"]), 1)
        self.assertEqual(buckets["confirmed"], [])
        self.assertEqual(buckets["dismissed"], [])
        self.assertEqual(buckets["contested"], [])

    def test_low_stakes_uncertain_system_design(self):
        """Uncertain on system_design → uncertain bucket (not high-stakes)."""
        f = _finding(agent="architect", file="src/e.py", line=1, pattern="P5", category="system_design")
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/e.py", "line": 1, "pattern": "P5", "agent": "architect", "verdict": "uncertain",
              "evidence": "cannot resolve"}],
            refuter="code-reviewer",
        )
        self.assertEqual(len(buckets["uncertain"]), 1)

    def test_high_stakes_uncertain_security_in_contested(self):
        """An uncertain verdict on a security finding goes to the contested bucket (D7)."""
        f = _finding(agent="security-reviewer", file="src/f.py", line=15, pattern="P6", category="security")
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/f.py", "line": 15, "pattern": "P6", "agent": "security-reviewer", "verdict": "uncertain",
              "evidence": "cannot resolve security implication"}],
            refuter="code-reviewer",
        )
        self.assertEqual(len(buckets["contested"]), 1)
        self.assertEqual(buckets["confirmed"], [])
        self.assertEqual(buckets["dismissed"], [])
        self.assertEqual(buckets["uncertain"], [])

    def test_high_stakes_uncertain_constitution_tag_in_contested(self):
        """Uncertain on a [CONSTITUTION-VIOLATION]-tagged finding → contested (D7)."""
        f = _finding(
            agent="code-reviewer", file="src/g.py", line=7, pattern="P7",
            category="mislogic",
            tags=["[CONSTITUTION-VIOLATION]"],
        )
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/g.py", "line": 7, "pattern": "P7", "agent": "code-reviewer", "verdict": "uncertain",
              "evidence": "cannot resolve rule"}],
            refuter="architect",
        )
        self.assertEqual(len(buckets["contested"]), 1)
        self.assertEqual(buckets["uncertain"], [])

    def test_dismissed_constitution_violation_carve_out(self):
        """D7 carve-out: dismissed verdict on a [CONSTITUTION-VIOLATION] finding → contested."""
        f = _finding(
            agent="qa-reviewer", file="src/h.py", line=9, pattern="P8",
            category="best_practice",
            tags=["[CONSTITUTION-VIOLATION]"],
        )
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/h.py", "line": 9, "pattern": "P8", "agent": "qa-reviewer", "verdict": "dismissed",
              "evidence": "(no counter-quote — finding is not demonstrable)"}],
            refuter="code-reviewer",
        )
        # Dismissed on a [CONSTITUTION-VIOLATION] finding → contested, NOT dismissed.
        self.assertEqual(len(buckets["contested"]), 1)
        self.assertEqual(buckets["dismissed"], [])

    def test_dismissed_security_no_constitution_tag_in_dismissed_bucket(self):
        """D7 carve-out does NOT widen to all security findings.

        A dismissed verdict on a category="security" finding that carries NO
        [CONSTITUTION-VIOLATION] tag must land in the dismissed bucket, not
        contested.  The D7 carve-out is tag-gated, not category-gated.
        """
        f = _finding(
            agent="security-reviewer", file="src/q.py", line=55, pattern="P9",
            category="security",
            tags=[],  # no [CONSTITUTION-VIOLATION] tag
        )
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/q.py", "line": 55, "pattern": "P9",
              "agent": "security-reviewer", "verdict": "dismissed",
              "evidence": "(no counter-quote — finding is not demonstrable)"}],
            refuter="code-reviewer",
        )
        self.assertEqual(len(buckets["dismissed"]), 1)
        self.assertEqual(buckets["contested"], [])

    def test_no_verdict_match_low_stakes_default_uncertain(self):
        """A finding with no matching verdict: low-stakes → uncertain bucket."""
        f = _finding(agent="code-reviewer", file="src/i.py", line=1, pattern="UnmatchedP", category="duplication")
        # No verdicts provided for this finding
        buckets = apply_verdicts([f], [])
        self.assertEqual(len(buckets["uncertain"]), 1)
        self.assertEqual(buckets["confirmed"], [])
        self.assertEqual(buckets["dismissed"], [])
        self.assertEqual(buckets["contested"], [])

    def test_no_verdict_match_high_stakes_security_default_contested(self):
        """No-verdict finding with category=security → contested bucket."""
        f = _finding(agent="security-reviewer", file="src/j.py", line=1, pattern="NoVerdictSec", category="security")
        buckets = apply_verdicts([f], [])
        self.assertEqual(len(buckets["contested"]), 1)
        self.assertEqual(buckets["uncertain"], [])

    def test_no_verdict_match_constitution_tag_default_contested(self):
        """No-verdict finding with [CONSTITUTION-VIOLATION] tag → contested bucket."""
        f = _finding(
            agent="code-reviewer", file="src/k.py", line=1, pattern="NoVerdictConst",
            category="mislogic",
            tags=["[CONSTITUTION-VIOLATION]"],
        )
        buckets = apply_verdicts([f], [])
        self.assertEqual(len(buckets["contested"]), 1)

    def test_unmatched_verdict_skipped_not_crashed(self):
        """A verdict that matches no finding is ignored (no crash, no empty bucket)."""
        f = _finding(agent="architect", file="src/l.py", line=5, pattern="RealP", category="mislogic")
        # Build a verdict that does NOT match f (different file)
        text = _verdict_file(
            refuter="code-reviewer",
            verdicts=[{
                "file": "src/DIFFERENT.py",
                "line": 99,
                "pattern": "WrongPattern",
                "agent": "architect",
                "verdict": "confirmed",
                "evidence": "some code",
            }],
        )
        cv = consume_verdicts(text)
        buckets = apply_verdicts([f], cv["verdicts"])
        # f has no matching verdict → low-stakes → uncertain
        self.assertEqual(len(buckets["uncertain"]), 1)
        # The unmatched verdict is just ignored; total findings = 1 across all buckets
        total = sum(len(buckets[k]) for k in ["confirmed", "dismissed", "uncertain", "contested"])
        self.assertEqual(total, 1)

    def test_empty_findings_and_verdicts(self):
        """Empty inputs: all buckets are empty lists, no crash."""
        buckets = apply_verdicts([], [])
        self.assertEqual(buckets["confirmed"], [])
        self.assertEqual(buckets["dismissed"], [])
        self.assertEqual(buckets["uncertain"], [])
        self.assertEqual(buckets["contested"], [])

    def test_empty_verdicts_all_findings_use_default(self):
        """All findings without verdicts route by their category."""
        f1 = _finding(agent="code-reviewer", file="src/m.py", line=1, pattern="X", category="mislogic")
        f2 = _finding(agent="security-reviewer", file="src/n.py", line=2, pattern="Y", category="security")
        buckets = apply_verdicts([f1, f2], [])
        self.assertEqual(len(buckets["uncertain"]), 1)
        self.assertEqual(len(buckets["contested"]), 1)

    def test_multiple_verdicts_for_same_key_highest_precedence_wins(self):
        """If two verdicts match the same finding, confirmed > uncertain > dismissed."""
        f = _finding(agent="architect", file="src/o.py", line=3, pattern="Multi", category="mislogic")
        # Two verdicts for the same key: dismissed then confirmed
        v_dismissed = {
            "refuter": "code-reviewer", "file": "src/o.py", "line": 3,
            "pattern": "Multi", "agent": "architect", "verdict": "dismissed",
            "justification": "no defect", "evidence": "(no counter-quote — finding is not demonstrable)",
        }
        v_confirmed = {
            "refuter": "qa-reviewer", "file": "src/o.py", "line": 3,
            "pattern": "Multi", "agent": "architect", "verdict": "confirmed",
            "justification": "defect confirmed", "evidence": "bad_code()",
        }
        buckets = apply_verdicts([f], [v_dismissed, v_confirmed])
        # confirmed beats dismissed → finding in confirmed bucket
        self.assertEqual(len(buckets["confirmed"]), 1)
        self.assertEqual(buckets["dismissed"], [])

    def test_multiple_uncertain_vs_dismissed_uncertain_wins(self):
        """uncertain > dismissed in precedence for the same key."""
        f = _finding(agent="qa-reviewer", file="src/p.py", line=8, pattern="Unc", category="mislogic")
        v_dismissed = {
            "refuter": "code-reviewer", "file": "src/p.py", "line": 8,
            "pattern": "Unc", "agent": "qa-reviewer", "verdict": "dismissed",
            "justification": "", "evidence": "(no counter-quote — finding is not demonstrable)",
        }
        v_uncertain = {
            "refuter": "architect", "file": "src/p.py", "line": 8,
            "pattern": "Unc", "agent": "qa-reviewer", "verdict": "uncertain",
            "justification": "cannot resolve", "evidence": "unclear",
        }
        buckets = apply_verdicts([f], [v_dismissed, v_uncertain])
        # uncertain > dismissed → uncertain bucket (low-stakes)
        self.assertEqual(len(buckets["uncertain"]), 1)
        self.assertEqual(buckets["dismissed"], [])

    def test_all_four_buckets_present_in_output(self):
        """apply_verdicts always returns all four bucket keys, even if empty."""
        buckets = apply_verdicts([], [])
        self.assertIn("confirmed", buckets)
        self.assertIn("dismissed", buckets)
        self.assertIn("uncertain", buckets)
        self.assertIn("contested", buckets)

    def test_confirmed_security_not_intercepted_by_category(self):
        """F1: category='security' with 'confirmed' verdict lands in confirmed, not contested.

        The confirmed branch has no category interception — only the uncertain
        branch checks _HIGH_STAKES_CATEGORIES to route to contested.  A confirmed
        finding goes to confirmed regardless of category.
        """
        f = _finding(
            agent="security-reviewer",
            file="src/sec.py",
            line=99,
            pattern="SQL injection",
            category="security",
            tags=[],
        )
        buckets = self._parse_and_apply(
            [f],
            [{
                "file": "src/sec.py",
                "line": 99,
                "pattern": "SQL injection",
                "agent": "security-reviewer",
                "verdict": "confirmed",
                "evidence": "query = 'SELECT * FROM ' + user_id",
            }],
            refuter="code-reviewer",
        )
        self.assertEqual(len(buckets["confirmed"]), 1)
        self.assertEqual(buckets["contested"], [])
        self.assertEqual(buckets["uncertain"], [])
        self.assertEqual(buckets["dismissed"], [])
        self.assertEqual(buckets["confirmed"][0]["verify_confidence"], "confirmed")

    def test_blind_spot_no_verdict_routes_to_uncertain_not_contested(self):
        """F2: category='blind_spot' with no matching verdict routes to uncertain.

        blind_spot is NOT in _HIGH_STAKES_CATEGORIES, so the no-verdict default
        is the LOW-stakes path: uncertain bucket (not contested).
        """
        f = _finding(
            agent="code-reviewer",
            file="src/svc.py",
            line=5,
            pattern="Potential gap",
            category="blind_spot",
            tags=[],
        )
        buckets = apply_verdicts([f], [])
        self.assertEqual(len(buckets["uncertain"]), 1)
        self.assertEqual(buckets["contested"], [])
        self.assertEqual(buckets["confirmed"], [])
        self.assertEqual(buckets["dismissed"], [])


# ---------------------------------------------------------------------------
# Tests: [CONTESTED] tag added to contested bucket (plan 19 Change D / Edit 1)
# ---------------------------------------------------------------------------

class TestContestedTagging(unittest.TestCase):
    """Every finding routed to the contested bucket must carry [CONTESTED] in tags.

    Cases:
      1. High-stakes uncertain (category == "security") → contested + [CONTESTED].
      2. High-stakes uncertain ([CONSTITUTION-VIOLATION] tag) → contested + [CONTESTED].
      3. Dismissed [CONSTITUTION-VIOLATION] (D7 carve-out) → contested + [CONTESTED].
      4. No-verdict-match + high-stakes (security) → contested + [CONTESTED].
      5. No-verdict-match + [CONSTITUTION-VIOLATION] tag → contested + [CONTESTED].
      6. Confirmed finding → NOT tagged [CONTESTED].
      7. Dismissed (non-constitution) → NOT tagged [CONTESTED]; in dismissed bucket.
      8. Low-stakes uncertain → NOT tagged [CONTESTED]; in uncertain bucket.
      9. Input dict is NOT mutated (shallow copy for contested findings).
     10. Tag is not added twice when [CONTESTED] is already present.
    """

    def _parse_and_apply(self, findings, verdict_spec_list, refuter="architect"):
        """Round-trip helper: build verdict file → consume_verdicts → apply_verdicts."""
        text = _verdict_file(refuter=refuter, verdicts=verdict_spec_list)
        cv = consume_verdicts(text)
        return apply_verdicts(findings, cv["verdicts"])

    def test_high_stakes_uncertain_security_carries_contested_tag(self):
        """High-stakes uncertain (security) in contested bucket carries [CONTESTED]."""
        f = _finding(agent="security-reviewer", file="src/f.py", line=15,
                     pattern="P_sec", category="security")
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/f.py", "line": 15, "pattern": "P_sec",
              "agent": "security-reviewer", "verdict": "uncertain",
              "evidence": "cannot resolve"}],
            refuter="code-reviewer",
        )
        self.assertEqual(len(buckets["contested"]), 1)
        tagged = buckets["contested"][0]
        self.assertIn("[CONTESTED]", tagged.get("tags", []))

    def test_high_stakes_uncertain_constitution_tag_carries_contested_tag(self):
        """High-stakes uncertain ([CONSTITUTION-VIOLATION]) in contested bucket carries [CONTESTED]."""
        f = _finding(agent="code-reviewer", file="src/g.py", line=7,
                     pattern="P_const", category="mislogic",
                     tags=["[CONSTITUTION-VIOLATION]"])
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/g.py", "line": 7, "pattern": "P_const",
              "agent": "code-reviewer", "verdict": "uncertain",
              "evidence": "cannot resolve rule"}],
            refuter="architect",
        )
        self.assertEqual(len(buckets["contested"]), 1)
        tagged = buckets["contested"][0]
        self.assertIn("[CONTESTED]", tagged.get("tags", []))

    def test_dismissed_constitution_carve_out_carries_contested_tag(self):
        """D7 carve-out: dismissed [CONSTITUTION-VIOLATION] → contested + [CONTESTED]."""
        f = _finding(agent="qa-reviewer", file="src/h.py", line=9,
                     pattern="P_carve", category="best_practice",
                     tags=["[CONSTITUTION-VIOLATION]"])
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/h.py", "line": 9, "pattern": "P_carve",
              "agent": "qa-reviewer", "verdict": "dismissed",
              "evidence": "(no counter-quote — finding is not demonstrable)"}],
            refuter="code-reviewer",
        )
        self.assertEqual(len(buckets["contested"]), 1)
        tagged = buckets["contested"][0]
        self.assertIn("[CONTESTED]", tagged.get("tags", []))

    def test_no_verdict_high_stakes_security_carries_contested_tag(self):
        """No-verdict-match high-stakes (security) → contested + [CONTESTED]."""
        f = _finding(agent="security-reviewer", file="src/j.py", line=1,
                     pattern="NV_sec", category="security")
        buckets = apply_verdicts([f], [])
        self.assertEqual(len(buckets["contested"]), 1)
        tagged = buckets["contested"][0]
        self.assertIn("[CONTESTED]", tagged.get("tags", []))

    def test_no_verdict_constitution_tag_carries_contested_tag(self):
        """No-verdict-match [CONSTITUTION-VIOLATION] → contested + [CONTESTED]."""
        f = _finding(agent="code-reviewer", file="src/k.py", line=1,
                     pattern="NV_const", category="mislogic",
                     tags=["[CONSTITUTION-VIOLATION]"])
        buckets = apply_verdicts([f], [])
        self.assertEqual(len(buckets["contested"]), 1)
        tagged = buckets["contested"][0]
        self.assertIn("[CONTESTED]", tagged.get("tags", []))

    def test_confirmed_finding_does_not_carry_contested_tag(self):
        """A confirmed finding in the confirmed bucket must NOT carry [CONTESTED]."""
        f = _finding(agent="architect", file="src/a.py", line=10,
                     pattern="P_conf", category="mislogic")
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/a.py", "line": 10, "pattern": "P_conf",
              "agent": "architect", "verdict": "confirmed",
              "evidence": "bad_code()"}],
            refuter="code-reviewer",
        )
        self.assertEqual(len(buckets["confirmed"]), 1)
        cf = buckets["confirmed"][0]
        self.assertNotIn("[CONTESTED]", cf.get("tags", []))
        self.assertEqual(cf.get("verify_confidence"), "confirmed")

    def test_dismissed_non_constitution_not_contested_tagged(self):
        """Dismissed (non-constitution) finding in dismissed bucket has no [CONTESTED] tag."""
        f = _finding(agent="qa-reviewer", file="src/b.py", line=20,
                     pattern="P_dis", category="mislogic")
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/b.py", "line": 20, "pattern": "P_dis",
              "agent": "qa-reviewer", "verdict": "dismissed",
              "evidence": "guard_exists()"}],
            refuter="code-reviewer",
        )
        self.assertEqual(len(buckets["dismissed"]), 1)
        df = buckets["dismissed"][0]
        self.assertNotIn("[CONTESTED]", df.get("tags", []))

    def test_low_stakes_uncertain_not_contested_tagged(self):
        """Low-stakes uncertain finding in uncertain bucket has no [CONTESTED] tag."""
        f = _finding(agent="architect", file="src/c.py", line=5,
                     pattern="P_unc", category="system_design")
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/c.py", "line": 5, "pattern": "P_unc",
              "agent": "architect", "verdict": "uncertain",
              "evidence": "cannot resolve"}],
            refuter="code-reviewer",
        )
        self.assertEqual(len(buckets["uncertain"]), 1)
        uf = buckets["uncertain"][0]
        self.assertNotIn("[CONTESTED]", uf.get("tags", []))

    def test_input_dict_not_mutated_for_contested_finding(self):
        """apply_verdicts must not mutate the input finding dict for contested findings."""
        f = _finding(agent="security-reviewer", file="src/m.py", line=3,
                     pattern="P_mut", category="security", tags=[])
        original_tags = list(f.get("tags", []))
        buckets = apply_verdicts([f], [])
        # Input dict unchanged
        self.assertEqual(f.get("tags", []), original_tags)
        self.assertNotIn("[CONTESTED]", f.get("tags", []))
        # But contested bucket entry carries the tag
        self.assertIn("[CONTESTED]", buckets["contested"][0].get("tags", []))

    def test_contested_tag_not_added_twice(self):
        """If [CONTESTED] is already in tags, _tag_contested adds it only once."""
        # Simulate a finding that already carries [CONTESTED] (e.g. pre-tagged)
        f = _finding(agent="security-reviewer", file="src/n.py", line=7,
                     pattern="P_twice", category="security",
                     tags=["[CONTESTED]"])
        buckets = apply_verdicts([f], [])
        tagged = buckets["contested"][0]
        contested_count = tagged.get("tags", []).count("[CONTESTED]")
        self.assertEqual(contested_count, 1)


# ---------------------------------------------------------------------------
# Plan 50 P1 -- [DATA-LOSS] / [IRREVERSIBLE] high-stakes widening
#
# End-to-end: the marker originates in a real agent tmp file's Pattern line,
# is lifted into ParsedFinding.tags by parse_agent_tmp (_consume.py), and THEN
# routed by apply_verdicts -- proving the full Pattern-line -> tags -> contested
# chain, not just the _verify.py routing in isolation.
# ---------------------------------------------------------------------------

# Template mirrors _DL_BLOCK_TEMPLATE in test_consume.py (kept local + minimal
# to avoid a cross-test-module import dependency).
_DL_AGENT_TMP_TEMPLATE = """\
# Agent: architect
# Status: complete
# Finding count: 1

## Finding 1
Severity: High
File: src/migrations/0042_drop_column.py
Line: 12
Pattern: {pattern_line}
Category: system_design
Confidence: Certain
Evidence:
```
op.drop_column('orders', 'legacy_total')
```
Why it's wrong: {why_line}
Remediation: Back up the column data before dropping it.
"""


class TestDataLossHighStakesEndToEnd(unittest.TestCase):
    """Round-trip: parse_agent_tmp (real Pattern-line marker) -> apply_verdicts.

    Cases: confirmed / dismissed / uncertain x {[DATA-LOSS], [IRREVERSIBLE], neither}.
    """

    def _real_finding(self, pattern_line, why_line="The change is not reversible."):
        """Build ONE finding via the real _consume parse path (not a hand-built dict)."""
        from _shared._consume import parse_agent_tmp  # local import, mirrors test_consume.py usage
        text = _DL_AGENT_TMP_TEMPLATE.format(pattern_line=pattern_line, why_line=why_line)
        result = parse_agent_tmp(text, agent_name="architect")
        self.assertEqual(len(result["findings"]), 1)
        return result["findings"][0]

    def _parse_and_apply(self, findings, verdict_spec_list, refuter="code-reviewer"):
        text = _verdict_file(refuter=refuter, verdicts=verdict_spec_list)
        cv = consume_verdicts(text)
        return apply_verdicts(findings, cv["verdicts"])

    # --- dismissed -------------------------------------------------------------

    def test_dismissed_data_loss_routes_to_contested(self):
        """A dismissed [DATA-LOSS] finding is never silently buried -> contested."""
        f = self._real_finding("Column dropped without backup [DATA-LOSS]")
        self.assertIn("[DATA-LOSS]", f["tags"])  # sanity: the lift happened
        buckets = self._parse_and_apply(
            [f],
            [{"file": f["file"], "line": f["line"], "pattern": f["pattern"],
              "agent": f["agent"], "verdict": "dismissed",
              "evidence": "(no counter-quote — finding is not demonstrable)"}],
        )
        self.assertEqual(len(buckets["contested"]), 1)
        self.assertEqual(buckets["dismissed"], [])
        self.assertIn("[CONTESTED]", buckets["contested"][0]["tags"])

    def test_dismissed_irreversible_routes_to_contested(self):
        """A dismissed [IRREVERSIBLE] finding is never silently buried -> contested."""
        f = self._real_finding("Migration has no downgrade() path [IRREVERSIBLE]")
        self.assertIn("[IRREVERSIBLE]", f["tags"])
        buckets = self._parse_and_apply(
            [f],
            [{"file": f["file"], "line": f["line"], "pattern": f["pattern"],
              "agent": f["agent"], "verdict": "dismissed",
              "evidence": "(no counter-quote — finding is not demonstrable)"}],
        )
        self.assertEqual(len(buckets["contested"]), 1)
        self.assertEqual(buckets["dismissed"], [])
        self.assertIn("[CONTESTED]", buckets["contested"][0]["tags"])

    def test_dismissed_neither_tag_routes_to_dismissed_unchanged(self):
        """Zero-regression: a dismissed finding with NEITHER tag still routes to dismissed."""
        f = self._real_finding("Column dropped as part of routine cleanup",
                                why_line="The column is unused and safe to remove.")
        self.assertEqual(f["tags"], [])
        buckets = self._parse_and_apply(
            [f],
            [{"file": f["file"], "line": f["line"], "pattern": f["pattern"],
              "agent": f["agent"], "verdict": "dismissed",
              "evidence": "(no counter-quote — finding is not demonstrable)"}],
        )
        self.assertEqual(len(buckets["dismissed"]), 1)
        self.assertEqual(buckets["contested"], [])

    # --- uncertain ---------------------------------------------------------

    def test_uncertain_data_loss_routes_to_contested(self):
        """An uncertain [DATA-LOSS] finding routes to contested (high-stakes)."""
        f = self._real_finding("Column dropped, uncertain whether recoverable [DATA-LOSS]")
        buckets = self._parse_and_apply(
            [f],
            [{"file": f["file"], "line": f["line"], "pattern": f["pattern"],
              "agent": f["agent"], "verdict": "uncertain",
              "evidence": "cannot determine backup status from code"}],
        )
        self.assertEqual(len(buckets["contested"]), 1)
        self.assertEqual(buckets["uncertain"], [])

    def test_uncertain_irreversible_routes_to_contested(self):
        """An uncertain [IRREVERSIBLE] finding routes to contested (high-stakes)."""
        f = self._real_finding("Uncertain rollback path exists [IRREVERSIBLE]")
        buckets = self._parse_and_apply(
            [f],
            [{"file": f["file"], "line": f["line"], "pattern": f["pattern"],
              "agent": f["agent"], "verdict": "uncertain",
              "evidence": "cannot determine rollback status from code"}],
        )
        self.assertEqual(len(buckets["contested"]), 1)
        self.assertEqual(buckets["uncertain"], [])

    def test_uncertain_neither_tag_low_stakes_routes_to_uncertain_unchanged(self):
        """Zero-regression: uncertain + neither tag + non-security category -> uncertain."""
        f = self._real_finding("Column dropped, unclear if this is dead code",
                                why_line="Unclear if the column is read elsewhere.")
        buckets = self._parse_and_apply(
            [f],
            [{"file": f["file"], "line": f["line"], "pattern": f["pattern"],
              "agent": f["agent"], "verdict": "uncertain",
              "evidence": "cannot resolve from code"}],
        )
        self.assertEqual(len(buckets["uncertain"]), 1)
        self.assertEqual(buckets["contested"], [])

    # --- confirmed -----------------------------------------------------------

    def test_confirmed_data_loss_headlines_normally(self):
        """A confirmed [DATA-LOSS] finding renders in confirmed as normal (not contested)."""
        f = self._real_finding("Column dropped without backup [DATA-LOSS]")
        buckets = self._parse_and_apply(
            [f],
            [{"file": f["file"], "line": f["line"], "pattern": f["pattern"],
              "agent": f["agent"], "verdict": "confirmed",
              "evidence": "op.drop_column('orders', 'legacy_total')"}],
        )
        self.assertEqual(len(buckets["confirmed"]), 1)
        self.assertEqual(buckets["contested"], [])
        self.assertEqual(buckets["confirmed"][0]["verify_confidence"], "confirmed")

    def test_confirmed_irreversible_headlines_normally(self):
        """A confirmed [IRREVERSIBLE] finding renders in confirmed as normal (not contested)."""
        f = self._real_finding("Migration has no downgrade() path [IRREVERSIBLE]")
        buckets = self._parse_and_apply(
            [f],
            [{"file": f["file"], "line": f["line"], "pattern": f["pattern"],
              "agent": f["agent"], "verdict": "confirmed",
              "evidence": "op.drop_column('orders', 'legacy_total')"}],
        )
        self.assertEqual(len(buckets["confirmed"]), 1)
        self.assertEqual(buckets["contested"], [])

    def test_confirmed_neither_tag_headlines_normally(self):
        """Zero-regression: confirmed + neither tag -> confirmed bucket as before."""
        f = self._real_finding("Column dropped as part of routine cleanup",
                                why_line="The column is unused and safe to remove.")
        buckets = self._parse_and_apply(
            [f],
            [{"file": f["file"], "line": f["line"], "pattern": f["pattern"],
              "agent": f["agent"], "verdict": "confirmed",
              "evidence": "op.drop_column('orders', 'legacy_total')"}],
        )
        self.assertEqual(len(buckets["confirmed"]), 1)
        self.assertEqual(buckets["contested"], [])

    # --- no-verdict-match default ---------------------------------------------

    def test_no_verdict_match_data_loss_defaults_to_contested(self):
        """No matching verdict + [DATA-LOSS] -> the high-stakes no-verdict default (contested)."""
        f = self._real_finding("Column dropped without backup [DATA-LOSS]")
        buckets = apply_verdicts([f], [])
        self.assertEqual(len(buckets["contested"]), 1)
        self.assertIn("[CONTESTED]", buckets["contested"][0]["tags"])

    def test_no_verdict_match_irreversible_defaults_to_contested(self):
        """No matching verdict + [IRREVERSIBLE] -> the high-stakes no-verdict default (contested)."""
        f = self._real_finding("Migration has no downgrade() path [IRREVERSIBLE]")
        buckets = apply_verdicts([f], [])
        self.assertEqual(len(buckets["contested"]), 1)
        self.assertIn("[CONTESTED]", buckets["contested"][0]["tags"])

    # --- security zero-regression (existing high-stakes category untouched) --

    def test_security_category_still_high_stakes_without_new_tags(self):
        """Zero-regression: category=='security' alone (no new tags) is still high-stakes."""
        f = _finding(agent="security-reviewer", file="src/sec.py", line=42,
                     pattern="SQL injection", category="security")
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/sec.py", "line": 42, "pattern": "SQL injection",
              "agent": "security-reviewer", "verdict": "uncertain",
              "evidence": "cannot resolve"}],
        )
        self.assertEqual(len(buckets["contested"]), 1)

    def test_constitution_tag_still_high_stakes_without_new_tags(self):
        """Zero-regression: [CONSTITUTION-VIOLATION] alone still triggers the D7 carve-out."""
        f = _finding(agent="qa-reviewer", file="src/h.py", line=9,
                     pattern="P_carve", category="best_practice",
                     tags=["[CONSTITUTION-VIOLATION]"])
        buckets = self._parse_and_apply(
            [f],
            [{"file": "src/h.py", "line": 9, "pattern": "P_carve",
              "agent": "qa-reviewer", "verdict": "dismissed",
              "evidence": "(no counter-quote — finding is not demonstrable)"}],
        )
        self.assertEqual(len(buckets["contested"]), 1)
        self.assertEqual(buckets["dismissed"], [])


# ---------------------------------------------------------------------------
# Tests: render_verify_brief
# ---------------------------------------------------------------------------

class TestRenderVerifyBrief(unittest.TestCase):

    def test_raises_when_preamble_missing(self):
        """render_verify_brief raises ValueError when references_dir lacks preamble."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError) as ctx:
                render_verify_brief(
                    refuter="architect",
                    findings=[],
                    references_dir=tmpdir,
                    scope_block="## Scope\n",
                    source_root=".",
                )
        self.assertIn("refutation-preamble.md", str(ctx.exception))

    def test_renders_with_real_preamble(self):
        """render_verify_brief produces a non-empty brief when preamble exists."""
        preamble_dir = str(
            _REPO_ROOT / "src" / "commands" / "audit" / "references"
        )
        if not os.path.isfile(os.path.join(preamble_dir, "refutation-preamble.md")):
            self.skipTest("refutation-preamble.md not found — not yet authored")

        f = _finding(agent="code-reviewer")
        brief = render_verify_brief(
            refuter="architect",
            findings=[f],
            references_dir=preamble_dir,
            scope_block="## Scope\nSource root: .\nFiles: (1 file)",
            source_root=".",
            tmp_path="/tmp/test-verdicts.md",
        )
        self.assertIn("## Finding 1", brief)
        self.assertIn("src/a.py", brief)
        self.assertIn("/tmp/test-verdicts.md", brief)

    def test_empty_findings_renders_no_finding_block(self):
        """render_verify_brief with no findings renders a placeholder message."""
        preamble_dir = str(
            _REPO_ROOT / "src" / "commands" / "audit" / "references"
        )
        if not os.path.isfile(os.path.join(preamble_dir, "refutation-preamble.md")):
            self.skipTest("refutation-preamble.md not found — not yet authored")

        brief = render_verify_brief(
            refuter="code-reviewer",
            findings=[],
            references_dir=preamble_dir,
            scope_block="",
            source_root=".",
        )
        self.assertIn("no findings assigned", brief)

    def test_tmp_path_default_contains_refuter_name(self):
        """When tmp_path is None, the default path includes the refuter name."""
        preamble_dir = str(
            _REPO_ROOT / "src" / "commands" / "audit" / "references"
        )
        if not os.path.isfile(os.path.join(preamble_dir, "refutation-preamble.md")):
            self.skipTest("refutation-preamble.md not found — not yet authored")

        brief = render_verify_brief(
            refuter="qa-reviewer",
            findings=[],
            references_dir=preamble_dir,
            scope_block="",
            source_root=".",
            tmp_path=None,
        )
        self.assertIn("qa-reviewer", brief)


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------

class TestCLISmoke(unittest.TestCase):

    def _run_cli(self, argv):
        """Run audit_helper CLI and return exit code, stdout, stderr."""
        from _audit._cli import main
        old_out = sys.stdout
        old_err = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            code = main(argv)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 2
        finally:
            stdout_val = sys.stdout.getvalue()
            stderr_val = sys.stderr.getvalue()
            sys.stdout = old_out
            sys.stderr = old_err
        return code, stdout_val, stderr_val

    def test_route_refutation_missing_findings_exits_2(self):
        """route-refutation without --findings returns exit code 2."""
        code, _, _ = self._run_cli(["route-refutation", "--finders", "code-reviewer"])
        self.assertEqual(code, 2)

    def test_consume_verdicts_missing_file_exits_2(self):
        """consume-verdicts with a non-existent path returns exit code 2."""
        code, out, _ = self._run_cli(["consume-verdicts", "--verdicts", "/nonexistent/path.md"])
        self.assertEqual(code, 2)
        data = json.loads(out)
        self.assertEqual(data["status"], "missing")

    def test_apply_verdicts_empty_inputs_exits_0(self):
        """apply-verdicts with empty arrays exits 0 and emits four buckets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            findings_path = os.path.join(tmpdir, "findings.json")
            verdicts_path = os.path.join(tmpdir, "verdicts.json")
            with open(findings_path, "w") as fh:
                json.dump([], fh)
            with open(verdicts_path, "w") as fh:
                json.dump([], fh)

            code, out, _ = self._run_cli([
                "apply-verdicts",
                "--findings", findings_path,
                "--verdicts", verdicts_path,
            ])
        self.assertEqual(code, 0)
        data = json.loads(out)
        for key in ("confirmed", "dismissed", "uncertain", "contested"):
            self.assertIn(key, data)
            self.assertEqual(data[key], [])

    def test_route_refutation_with_findings_exits_0(self):
        """route-refutation with valid inputs exits 0 and returns routing groups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            findings_path = os.path.join(tmpdir, "findings.json")
            findings = [_finding(agent="security-reviewer")]
            with open(findings_path, "w") as fh:
                json.dump(findings, fh)

            code, out, _ = self._run_cli([
                "route-refutation",
                "--findings", findings_path,
                "--finders", "code-reviewer,security-reviewer",
            ])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["refuter"], "code-reviewer")

    def test_consume_verdicts_with_valid_file_exits_0(self):
        """consume-verdicts with a real verdict file exits 0 and parses it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vpath = os.path.join(tmpdir, "verdicts.md")
            text = _verdict_file(
                refuter="architect",
                verdicts=[{
                    "file": "src/x.py", "line": 1, "pattern": "P",
                    "agent": "code-reviewer", "verdict": "dismissed",
                }],
            )
            with open(vpath, "w") as fh:
                fh.write(text)

            code, out, _ = self._run_cli(["consume-verdicts", "--verdicts", vpath])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "complete")
        self.assertEqual(data["verdict_count"], 1)

    def test_four_verbs_registered_in_help(self):
        """All four new verbs appear in the top-level help output."""
        code, out, err = self._run_cli([])
        # main prints help to stderr on no subcommand
        combined = out + err
        for verb in ("route-refutation", "render-verify-brief",
                     "consume-verdicts", "apply-verdicts"):
            self.assertIn(verb, combined, msg="missing verb: {0}".format(verb))


# ---------------------------------------------------------------------------
# Tests: route_refutation priority= parameter (new in _shared extraction)
# ---------------------------------------------------------------------------

class TestRouteRefutationPriorityParam(unittest.TestCase):
    """Verify the priority= keyword param of route_refutation.

    (a) priority=None (the default) uses _REFUTER_PRIORITY — behaviour must
        be byte-identical to the pre-extraction _audit._verify version.
    (b) An explicit priority list overrides the default and drives selection.
    """

    def test_priority_none_uses_default_constant(self):
        """priority=None selects refuters using _REFUTER_PRIORITY exactly."""
        # With all four default-priority finders present:
        # a code-reviewer finding must be routed to architect (second in list).
        finding = _finding(agent="code-reviewer", file="src/a.py", line=1,
                           pattern="P", category="mislogic")
        present = _REFUTER_PRIORITY  # all four present

        # priority=None (explicit)
        groups_none = route_refutation([finding], present, priority=None)
        # priority omitted (default)
        groups_default = route_refutation([finding], present)

        self.assertEqual(len(groups_none), 1)
        self.assertEqual(len(groups_default), 1)
        # Both must choose architect as refuter for code-reviewer's finding
        self.assertEqual(groups_none[0]["refuter"], "architect")
        self.assertEqual(groups_default[0]["refuter"], "architect")
        # Results must be identical
        self.assertEqual(groups_none[0]["refuter"], groups_default[0]["refuter"])

    def test_explicit_priority_overrides_default(self):
        """An explicit priority list changes refuter selection away from _REFUTER_PRIORITY."""
        # Custom roster: security-reviewer first, then qa-reviewer
        custom_priority = ["security-reviewer", "qa-reviewer"]

        finding = _finding(agent="security-reviewer", file="src/b.py", line=5,
                           pattern="Q", category="best_practice")
        # present_finders: both security-reviewer (author) and qa-reviewer available
        present = ["security-reviewer", "qa-reviewer"]

        groups = route_refutation([finding], present, priority=custom_priority)

        # With custom_priority, author=security-reviewer is skipped,
        # next is qa-reviewer → qa-reviewer is the refuter.
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["refuter"], "qa-reviewer")

    def test_explicit_priority_different_from_default(self):
        """Explicit priority produces a different result than the default for the same input."""
        # Under default priority: code-reviewer is first, so architect's finding
        # routes to code-reviewer.
        finding = _finding(agent="architect", file="src/c.py", line=10,
                           pattern="R", category="mislogic")
        present = ["code-reviewer", "qa-reviewer", "architect", "security-reviewer"]

        groups_default = route_refutation([finding], present, priority=None)
        # Default: first in _REFUTER_PRIORITY that is not architect = code-reviewer.
        self.assertEqual(groups_default[0]["refuter"], "code-reviewer")

        # Custom priority: qa-reviewer first.
        groups_custom = route_refutation([finding], present,
                                         priority=["qa-reviewer", "code-reviewer"])
        self.assertEqual(groups_custom[0]["refuter"], "qa-reviewer")

    def test_explicit_priority_sole_finder_self_refutes(self):
        """Explicit priority sole-finder edge case: author self-refutes when only one present."""
        finding = _finding(agent="qa-reviewer", file="src/d.py", line=3,
                           pattern="S", category="duplication")
        # Only qa-reviewer present, and it IS the author.
        groups = route_refutation([finding], ["qa-reviewer"],
                                   priority=["qa-reviewer", "code-reviewer"])
        # qa-reviewer is the only present priority member → self-refute.
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["refuter"], "qa-reviewer")

    def test_explicit_priority_empty_list_falls_back_to_author(self):
        """When priority=[] and no priority member present, author is the fallback."""
        finding = _finding(agent="backend-engineer", file="src/e.py", line=2,
                           pattern="T", category="mislogic")
        groups = route_refutation([finding], ["backend-engineer"],
                                   priority=[])
        # No priority members → fallback to author.
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["refuter"], "backend-engineer")


# ---------------------------------------------------------------------------
# CLI smoke tests for validate-findings and compute-consensus lazy imports
# (Fix 2: force the lazy 'from _shared._validate/consensus import ...' paths
#  to actually execute under test, catching broken re-pointed import paths.)
# ---------------------------------------------------------------------------

class TestLazyImportSmoke(unittest.TestCase):
    """Verify that the lazy imports in _audit/_cli.py actually execute."""

    def _run_cli(self, argv):
        """Run audit_helper CLI and return exit code, stdout, stderr."""
        from _audit._cli import main
        old_out = sys.stdout
        old_err = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            code = main(argv)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 2
        finally:
            stdout_val = sys.stdout.getvalue()
            stderr_val = sys.stderr.getvalue()
            sys.stdout = old_out
            sys.stderr = old_err
        return code, stdout_val, stderr_val

    def test_validate_findings_lazy_import_executes(self):
        """validate-findings with an empty findings array exits 0.

        This forces the lazy 'from _shared._validate import validate_findings'
        inside cmd_validate_findings to actually execute, catching any broken
        import path at test time rather than at production runtime.
        An empty list is a valid input: zero findings, zero failures.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            findings_path = os.path.join(tmpdir, "findings.json")
            with open(findings_path, "w") as fh:
                json.dump([], fh)

            code, out, _ = self._run_cli([
                "validate-findings",
                "--findings", findings_path,
                "--repo-root", tmpdir,
            ])
        self.assertEqual(code, 0, "validate-findings should exit 0 for empty findings list")
        data = json.loads(out)
        self.assertIn("passed", data)
        self.assertEqual(data["passed"], [])

    def test_compute_consensus_lazy_import_executes(self):
        """compute-consensus with an empty findings array exits 0.

        This forces the lazy 'from _shared._consensus import compute_consensus'
        inside cmd_compute_consensus to actually execute, catching any broken
        import path at test time rather than at production runtime.
        An empty list is a valid input: zero findings to merge.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            findings_path = os.path.join(tmpdir, "findings.json")
            with open(findings_path, "w") as fh:
                json.dump([], fh)

            code, out, _ = self._run_cli([
                "compute-consensus",
                "--findings", findings_path,
            ])
        self.assertEqual(code, 0, "compute-consensus should exit 0 for empty findings list")
        data = json.loads(out)
        self.assertIn("findings", data)
        self.assertIn("consensus_map", data)
        self.assertEqual(data["findings"], [])
        self.assertEqual(data["consensus_map"], {})


if __name__ == "__main__":
    unittest.main()
