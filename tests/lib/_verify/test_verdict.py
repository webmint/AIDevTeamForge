"""Tests for src/devforge/lib/_verify/_verdict.py

Coverage:
  compute_verdict:
    Happy paths:
      - All clean → APPROVED
      - All clean with off mode and AC failures → APPROVED (advisory)
    NEEDS WORK paths:
      - FAIL AC in non-off mode → NEEDS WORK
      - PARTIAL AC in non-off mode → NEEDS WORK
      - mechanical_status="failed" → NEEDS WORK
      - mechanical_status="self_repair" → NEEDS WORK
      - mechanical_status="tooling_unavailable" → NEEDS WORK
      - mechanical_status="isolation_failure" → NEEDS WORK
      - Contested [CONSTITUTION-VIOLATION] finding → NEEDS WORK (D7: never APPROVED)
      - Critical finding in review_findings → NEEDS WORK
      - High finding in review_findings → NEEDS WORK
      - scope_creep non-empty → NEEDS WORK
      - leftover_artifacts non-empty → NEEDS WORK
      - 2-AC/1-fail (50%, failing_count=1 < 2 threshold) → NEEDS WORK (not REJECTED)
      - 1-AC/1-fail (100%, failing_count=1 < 2 threshold) → NEEDS WORK (not REJECTED)
      - 1-FAIL/1-UNVERIFIED (1 verifiable, 100%, failing_count=1) → NEEDS WORK (not REJECTED)
    REJECTED paths:
      - Confirmed [CONSTITUTION-VIOLATION] → REJECTED (D7: ALWAYS)
      - failing_count>=2 AND failure_rate>=50% → REJECTED (2-AC/2-fail = 100%)
      - 3-AC/2-fail (66%, failing_count=2) → REJECTED
      - 4-AC/2-fail (50%, failing_count=2) → REJECTED
      - D7 invariant: confirmed constitution violation NEVER yields APPROVED
    Mode-specific:
      - off mode: FAIL AC is advisory → NOT in blockers, not blocking
      - off mode: FAIL ACs do not trigger REJECTED even at ≥50%
      - code-only mode: FAIL AC blocks
      - tests mode: FAIL AC blocks
    Edge cases:
      - Empty ac_results → clean (no AC checks)
      - None mechanical_status → treated as passing
      - Empty string mechanical_status → treated as passing
      - review_findings with missing=True → not blocking
      - Empty hygiene → no hygiene flags
      - None hygiene → no hygiene flags
      - UNVERIFIED ACs excluded from failure rate
      - MANUAL ACs excluded from failure rate
      - Multiple constitution violations (confirmed + contested)
      - Constitution violation via category field (not tag)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _verify._verdict import compute_verdict  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _empty_review():
    """A clean review_findings dict (no findings, review present)."""
    return {
        "missing": False,
        "confirmed": [],
        "contested": [],
        "summary": {
            "critical": 0, "high": 0, "medium": 0, "info": 0,
            "confirmed_count": 0, "contested_count": 0,
            "dismissed_count": 0, "uncertain_count": 0,
        },
    }


def _missing_review():
    """A review_findings dict where the review.md was absent."""
    return {
        "missing": True,
        "confirmed": [],
        "contested": [],
        "summary": {
            "critical": 0, "high": 0, "medium": 0, "info": 0,
            "confirmed_count": 0, "contested_count": 0,
            "dismissed_count": 0, "uncertain_count": 0,
        },
    }


def _empty_hygiene():
    return {
        "scope_creep": [],
        "leftover_artifacts": [],
        "scope_creep_checked": False,
        "files_checked": 0,
        "files_unreadable": [],
    }


def _ac(status, ac_id="AC-1"):
    """Minimal AC result dict."""
    return {"id": ac_id, "text": "test", "checked": False, "subsection": "", "status": status, "evidence": ""}


def _finding(severity="High", tags=None, category="mislogic"):
    """Minimal review finding dict."""
    return {
        "severity": severity,
        "file": "src/a.py",
        "line": 10,
        "pattern": "Test finding",
        "category": category,
        "tags": tags or [],
        "confidence": "Likely",
    }


def _constitution_finding(verdict_bucket="confirmed", contested=False):
    """A constitution violation finding."""
    return {
        "severity": "High",
        "file": "src/a.py",
        "line": 5,
        "pattern": "Rule broken",
        "category": "constitution",
        "tags": ["[CONSTITUTION-VIOLATION]"],
        "confidence": "Certain",
    }


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestComputeVerdictApproved(unittest.TestCase):
    """All-clean paths should produce APPROVED."""

    def test_all_clean_approved(self):
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")
        self.assertEqual(result["blockers"], [])

    def test_no_acs_approved(self):
        result = compute_verdict(
            ac_results=[],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_pass_code_variant_approved(self):
        result = compute_verdict(
            ac_results=[_ac("PASS (code)")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_unverified_ac_does_not_block(self):
        """UNVERIFIED ACs don't count as failures."""
        result = compute_verdict(
            ac_results=[_ac("UNVERIFIED"), _ac("PASS", "AC-2")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_manual_ac_does_not_block(self):
        """MANUAL ACs don't count as failures."""
        result = compute_verdict(
            ac_results=[_ac("MANUAL")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_missing_review_not_blocking(self):
        """Missing review report is noted but not blocking."""
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_missing_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")
        self.assertEqual(result["blockers"], [])
        # But it should mention it in reasons
        reasons_text = " ".join(result["reasons"])
        self.assertIn("review", reasons_text.lower())

    def test_none_mechanical_status_approved(self):
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status=None,
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_empty_mechanical_status_approved(self):
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_off_mode_fail_ac_is_advisory_approved(self):
        """Under off mode, FAIL ACs are advisory — result can still be APPROVED."""
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("PASS", "AC-2")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="off",
        )
        self.assertEqual(result["verdict"], "APPROVED")
        # Advisory reason should mention off mode
        reasons_text = " ".join(result["reasons"])
        self.assertIn("advisory", reasons_text.lower())
        # Should NOT be in blockers
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertNotIn("ac_failure", blocker_types)

    def test_off_mode_all_fail_no_rejected(self):
        """Under off mode, even 100% AC failure does not trigger REJECTED."""
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("FAIL", "AC-2"), _ac("FAIL", "AC-3")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="off",
        )
        self.assertEqual(result["verdict"], "APPROVED")


class TestComputeVerdictNeedsWork(unittest.TestCase):
    """Blocker conditions that produce NEEDS WORK."""

    def test_fail_ac_needs_work(self):
        # 1 FAIL out of 3 verifiable = 33% < 50% threshold → NEEDS WORK (not REJECTED)
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("PASS", "AC-2"), _ac("PASS", "AC-3")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("ac_failure", blocker_types)

    def test_1_ac_spec_single_fail_needs_work(self):
        """1-AC spec with 1 FAIL (100% rate, failing_count=1) → NEEDS WORK not REJECTED.

        This is the primary use-case for the new rule: a single-AC spec with one
        failure is a task bug, not a spec-level regression requiring /specify→/plan.
        """
        result = compute_verdict(
            ac_results=[_ac("FAIL")],  # 1/1 = 100%, but failing_count = 1
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        # Still a blocker
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("ac_failure", blocker_types)

    def test_partial_ac_needs_work(self):
        # 1 PARTIAL out of 3 verifiable = 33% < 50% → NEEDS WORK
        result = compute_verdict(
            ac_results=[_ac("PARTIAL"), _ac("PASS", "AC-2"), _ac("PASS", "AC-3")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_partial_code_ac_needs_work(self):
        # 1 PARTIAL (code) out of 3 verifiable = 33% < 50% → NEEDS WORK
        result = compute_verdict(
            ac_results=[_ac("PARTIAL (code)"), _ac("PASS", "AC-2"), _ac("PASS", "AC-3")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_fail_code_ac_needs_work(self):
        # 1 FAIL (code) out of 3 = 33% < 50% → NEEDS WORK
        result = compute_verdict(
            ac_results=[_ac("FAIL (code)"), _ac("PASS", "AC-2"), _ac("PASS", "AC-3")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_mechanical_failed_needs_work(self):
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="failed",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("mechanical_failed", blocker_types)

    def test_mechanical_self_repair_needs_work(self):
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="self_repair",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_mechanical_tooling_unavailable_needs_work(self):
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="tooling_unavailable",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_mechanical_isolation_failure_needs_work(self):
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="isolation_failure",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_critical_finding_needs_work(self):
        review = _empty_review()
        review["confirmed"] = [_finding(severity="Critical")]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("critical_high_finding", blocker_types)

    def test_high_finding_needs_work(self):
        review = _empty_review()
        review["confirmed"] = [_finding(severity="High")]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_medium_finding_not_blocking(self):
        """Medium/Info findings alone do NOT block."""
        review = _empty_review()
        review["confirmed"] = [_finding(severity="Medium")]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_scope_creep_needs_work(self):
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["src/unrelated.py"]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("hygiene_flags", blocker_types)

    def test_leftover_artifacts_needs_work(self):
        hygiene = _empty_hygiene()
        hygiene["leftover_artifacts"] = [{"file": "src/a.py", "line": 5, "artifact": "console.log"}]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_contested_constitution_violation_needs_work(self):
        """D7 invariant: contested [CONSTITUTION-VIOLATION] → NEEDS WORK, never APPROVED."""
        review = _empty_review()
        review["contested"] = [_constitution_finding()]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("constitution_contested", blocker_types)

    def test_fail_ac_tests_mode_blocks(self):
        """In tests mode, FAIL ACs are blockers (not advisory) — 1/3 = 33% < 50% → NEEDS WORK."""
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("PASS", "AC-2"), _ac("PASS", "AC-3")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="tests",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("ac_failure", blocker_types)

    def test_fail_ac_runtime_assisted_mode_blocks(self):
        # 1/3 = 33% < 50% → NEEDS WORK
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("PASS", "AC-2"), _ac("PASS", "AC-3")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="runtime-assisted",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_high_finding_in_contested_needs_work(self):
        """High finding in contested (not constitution) → NEEDS WORK."""
        review = _empty_review()
        review["contested"] = [_finding(severity="High")]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")


class TestComputeVerdictRejected(unittest.TestCase):
    """Conditions that produce REJECTED."""

    def test_confirmed_constitution_violation_rejected(self):
        """D7: confirmed [CONSTITUTION-VIOLATION] → ALWAYS REJECTED."""
        review = _empty_review()
        review["confirmed"] = [_constitution_finding()]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "REJECTED")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("constitution_confirmed", blocker_types)

    def test_constitution_violation_via_category_rejected(self):
        """Constitution violation via category='constitution' also triggers REJECTED."""
        review = _empty_review()
        # No [CONSTITUTION-VIOLATION] tag, but category="constitution"
        f = _finding(severity="High", tags=[], category="constitution")
        review["confirmed"] = [f]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "REJECTED")

    def test_1_fail_2_ac_needs_work_not_rejected(self):
        """1-FAIL/2-AC (50% rate, failing_count=1 < 2) → NEEDS WORK, not REJECTED.

        REJECTED requires BOTH failing_count>=2 AND failure_rate>=50%.
        A single AC failure is a task bug, not a spec-level problem.
        """
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("PASS", "AC-2")],  # 1/2 = 50%, but only 1 absolute fail
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        # It IS a blocker (ac_failure) — just not severe enough for REJECTED
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("ac_failure", blocker_types)

    def test_2_fail_2_ac_rejected(self):
        """2-FAIL/2-AC (100% rate, failing_count=2 >= 2) → REJECTED."""
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("FAIL", "AC-2")],  # 2/2 = 100%, 2 absolute fails
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "REJECTED")

    def test_4_ac_2_fail_rejected(self):
        """4-AC/2-fail (50% rate, failing_count=2 >= 2) → REJECTED.

        Both thresholds met: 2 absolute failures AND 50% rate.
        """
        result = compute_verdict(
            ac_results=[
                _ac("FAIL"),
                _ac("FAIL", "AC-2"),
                _ac("PASS", "AC-3"),
                _ac("PASS", "AC-4"),
            ],  # 2/4 = 50%, 2 absolute fails
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "REJECTED")

    def test_over_50_percent_failure_rate_rejected(self):
        """More than 50% failure rate → REJECTED."""
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("FAIL", "AC-2"), _ac("PASS", "AC-3")],  # 2/3
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "REJECTED")

    def test_under_50_percent_failure_rate_needs_work(self):
        """Less than 50% failure rate → NEEDS WORK (not REJECTED)."""
        result = compute_verdict(
            # 1/3 ≈ 33% < 50%
            ac_results=[_ac("FAIL"), _ac("PASS", "AC-2"), _ac("PASS", "AC-3")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_unverified_excluded_from_failure_rate(self):
        """UNVERIFIED ACs don't count in failure rate denominator.

        1 FAIL + 1 UNVERIFIED: failure_rate = 1/1 = 100% among verifiable.
        But failing_count = 1 < 2 absolute threshold → NEEDS WORK (not REJECTED).
        Under the new rule, REJECTED requires BOTH failing_count >= 2 AND rate >= 50%.
        """
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("UNVERIFIED", "AC-2")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        # failing_count=1 < 2 → NEEDS WORK despite 100% rate
        self.assertEqual(result["verdict"], "NEEDS WORK")
        # Still a blocker
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("ac_failure", blocker_types)

    def test_2_fail_1_unverified_rejected(self):
        """2 FAIL + 1 UNVERIFIED: failing_count=2, rate=2/2=100% → REJECTED.

        UNVERIFIED excluded from denominator, so verifiable_count=2, failure_rate=100%.
        Both thresholds met: failing_count>=2 AND rate>=50%.
        """
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("FAIL", "AC-2"), _ac("UNVERIFIED", "AC-3")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "REJECTED")

    def test_off_mode_50_percent_failure_not_rejected(self):
        """Under off mode, ≥50% AC failure does NOT trigger REJECTED."""
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("FAIL", "AC-2")],  # 2/2 = 100%
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="off",
        )
        # Should be APPROVED (all clean except advisory ACs)
        self.assertEqual(result["verdict"], "APPROVED")

    def test_constitution_violation_always_rejected_even_with_passing_acs(self):
        """D7: APPROVED is never possible when constitution_confirmed is set."""
        review = _empty_review()
        review["confirmed"] = [_constitution_finding()]
        result = compute_verdict(
            ac_results=[_ac("PASS"), _ac("PASS", "AC-2")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertNotEqual(result["verdict"], "APPROVED")
        self.assertEqual(result["verdict"], "REJECTED")

    def test_constitution_violation_not_approved_in_any_mode(self):
        """D7: confirmed constitution violation → REJECTED in all modes including off."""
        for mode in ("code-only", "tests", "runtime-assisted", "off"):
            with self.subTest(mode=mode):
                review = _empty_review()
                review["confirmed"] = [_constitution_finding()]
                result = compute_verdict(
                    ac_results=[_ac("PASS")],
                    mechanical_status="pass",
                    review_findings=review,
                    hygiene=_empty_hygiene(),
                    ac_verification_mode=mode,
                )
                self.assertEqual(
                    result["verdict"], "REJECTED",
                    msg="Mode {0}: expected REJECTED, got {1}".format(
                        mode, result["verdict"]
                    ),
                )


class TestComputeVerdictD7Invariant(unittest.TestCase):
    """Explicit D7 invariant tests: constitution violations block APPROVED."""

    def test_confirmed_constitution_never_approved(self):
        """D7 test: confirmed [CONSTITUTION-VIOLATION] NEVER yields APPROVED."""
        review = _empty_review()
        review["confirmed"] = [
            {
                "severity": "High",
                "file": "src/a.py",
                "line": 1,
                "pattern": "Breaks architecture rule",
                "category": "constitution",
                "tags": ["[CONSTITUTION-VIOLATION]"],
                "confidence": "Certain",
            }
        ]
        result = compute_verdict(
            ac_results=[_ac("PASS"), _ac("PASS", "AC-2")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertNotEqual(result["verdict"], "APPROVED",
                            "D7 VIOLATED: confirmed constitution violation yielded APPROVED")
        self.assertEqual(result["verdict"], "REJECTED")

    def test_contested_constitution_never_approved(self):
        """D7 test: contested [CONSTITUTION-VIOLATION] → at least NEEDS WORK, never APPROVED."""
        review = _empty_review()
        review["contested"] = [
            {
                "severity": "Medium",
                "file": "src/b.py",
                "line": 5,
                "pattern": "Possible architecture drift",
                "category": "constitution",
                "tags": ["[CONSTITUTION-VIOLATION]", "[CONTESTED]"],
                "confidence": "Likely",
            }
        ]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertNotEqual(result["verdict"], "APPROVED",
                            "D7 VIOLATED: contested constitution violation yielded APPROVED")
        # Must be NEEDS WORK or REJECTED (not APPROVED)
        self.assertIn(result["verdict"], {"NEEDS WORK", "REJECTED"})


class TestComputeVerdictEdgeCases(unittest.TestCase):
    """Edge cases and boundary values."""

    def test_none_review_findings(self):
        """None review_findings treated as missing — no crash, not blocking."""
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=None,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_none_hygiene(self):
        """None hygiene — no crash, not blocking."""
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=None,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_empty_ac_results_list_approved(self):
        result = compute_verdict(
            ac_results=[],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_only_unverified_no_failure_rate_trigger(self):
        """All ACs UNVERIFIED → verifiable_count=0 → failure_rate check skipped."""
        result = compute_verdict(
            ac_results=[_ac("UNVERIFIED"), _ac("UNVERIFIED", "AC-2")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")

    def test_multiple_blockers_needs_work(self):
        """Multiple non-REJECTED blockers → NEEDS WORK when failure rate < 50%."""
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["src/extra.py"]
        # 1/3 = 33% < 50% failure rate → NEEDS WORK (not REJECTED) despite multiple blockers
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("PASS", "AC-2"), _ac("PASS", "AC-3")],
            mechanical_status="self_repair",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_1_fail_2_pass_under_threshold(self):
        """1 FAIL out of 3 verifiable = 33% → NEEDS WORK, not REJECTED."""
        result = compute_verdict(
            ac_results=[
                _ac("FAIL"),
                _ac("PASS", "AC-2"),
                _ac("PASS", "AC-3"),
            ],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")

    def test_result_structure(self):
        """Return value always has verdict, reasons, blockers keys."""
        result = compute_verdict(
            ac_results=[],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertIn("verdict", result)
        self.assertIn("reasons", result)
        self.assertIn("blockers", result)
        self.assertIsInstance(result["reasons"], list)
        self.assertIsInstance(result["blockers"], list)

    def test_off_mode_reasons_mention_off(self):
        """Under off mode with failing ACs, reasons mention off/advisory."""
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("FAIL", "AC-2")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=_empty_hygiene(),
            ac_verification_mode="off",
        )
        reasons_text = " ".join(result["reasons"]).lower()
        self.assertIn("off", reasons_text)

    def test_constitution_violation_via_tag_only(self):
        """[CONSTITUTION-VIOLATION] tag without category='constitution' still triggers D7."""
        review = _empty_review()
        review["confirmed"] = [
            _finding(severity="High", tags=["[CONSTITUTION-VIOLATION]"], category="mislogic")
        ]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "REJECTED")

    def test_blocker_types_for_constitution_confirmed(self):
        """constitution_confirmed blocker type is in blockers on REJECTED."""
        review = _empty_review()
        review["confirmed"] = [_constitution_finding()]
        result = compute_verdict(
            ac_results=[],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        types = [b["type"] for b in result["blockers"]]
        self.assertIn("constitution_confirmed", types)


if __name__ == "__main__":
    unittest.main()
