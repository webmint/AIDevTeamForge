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
      - Confirmed Medium finding (non-constitution) → NEEDS WORK (D3 — any-confirmed-Medium gates)
      - 2-AC/1-fail (50%, failing_count=1 < 2 threshold) → NEEDS WORK (not REJECTED)
      - 1-AC/1-fail (100%, failing_count=1 < 2 threshold) → NEEDS WORK (not REJECTED)
      - 1-FAIL/1-UNVERIFIED (1 verifiable, 100%, failing_count=1) → NEEDS WORK (not REJECTED)
    Medium-finding gate paths (D3 — any-confirmed-Medium → NEEDS WORK; D4 — hygiene stays advisory):
      - One confirmed Medium non-constitution finding → NEEDS WORK, medium_finding blocker present
      - Info-severity finding only → APPROVED (Info non-gating)
      - Confirmed High → still NEEDS WORK (unchanged behavior)
      - Confirmed constitution violation → REJECTED (unchanged; constitution path, not medium path)
      - Plan-34 regression: clean feature with only hygiene flags (scope_creep /
        leftover_artifacts) → APPROVED (hygiene advisory, not blocking; Medium gate
        does NOT re-block on hygiene)
      - CONTESTED Medium (in contested, not confirmed) → APPROVED if nothing else blocks
        (confirmed-only per D3; contested Medium does not gate)
      - Medium that is also a constitution violation → handled by constitution path,
        not double-counted as plain medium_finding
      - Multiple confirmed Medium findings → single medium_finding blocker, detail lists up to 3
      - More than 3 confirmed Medium findings → truncated summary with "+ N more"
    Hygiene advisory paths (NEVER block verdict):
      - scope_creep non-empty, everything else clean → APPROVED (hygiene is advisory)
      - leftover_artifacts non-empty, everything else clean → APPROVED (hygiene is advisory)
      - scope_creep + leftover_artifacts both non-empty, everything else clean → APPROVED
      - hygiene_flags type NEVER appears in blockers
      - hygiene advisory reason appears in reasons when hygiene flags present
      - hygiene flags + real blocker (FAIL AC) → NEEDS WORK driven by real blocker, not hygiene
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


def _constitution_finding():
    """A constitution violation finding (confirmed-style — place in review["confirmed"] or ["contested"] explicitly)."""
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

    def test_medium_finding_blocks_needs_work(self):
        """D3: confirmed Medium finding → NEEDS WORK (not APPROVED as before D3)."""
        review = _empty_review()
        review["confirmed"] = [_finding(severity="Medium")]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("medium_finding", blocker_types)

    def test_scope_creep_is_advisory_not_blocking(self):
        """Hygiene change: scope_creep alone must NOT block — result is APPROVED."""
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["src/unrelated.py"]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")
        # hygiene_flags must NOT appear in blockers
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertNotIn("hygiene_flags", blocker_types)
        # hygiene advisory reason IS present
        reasons_text = " ".join(result["reasons"])
        self.assertIn("advisory", reasons_text.lower())

    def test_leftover_artifacts_is_advisory_not_blocking(self):
        """Hygiene change: leftover_artifacts alone must NOT block — result is APPROVED."""
        hygiene = _empty_hygiene()
        hygiene["leftover_artifacts"] = [{"file": "src/a.py", "line": 5, "artifact": "console.log"}]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertNotIn("hygiene_flags", blocker_types)

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


class TestComputeVerdictHygieneAdvisory(unittest.TestCase):
    """Hygiene flags are ADVISORY — they never block the verdict.

    Explicit tests for the demoted hygiene check (scope_creep / leftover_artifacts
    are never added to blockers; they appear only as advisory reason lines).
    """

    def test_scope_creep_only_approved(self):
        """scope_creep non-empty, everything else clean → APPROVED."""
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["src/unrelated.py", "src/other.py"]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")
        self.assertEqual(result["blockers"], [])

    def test_leftover_artifacts_only_approved(self):
        """leftover_artifacts non-empty, everything else clean → APPROVED."""
        hygiene = _empty_hygiene()
        hygiene["leftover_artifacts"] = [
            {"file": "src/a.py", "line": 5, "artifact": "console.log"},
            {"file": "src/b.py", "line": 12, "artifact": "TODO: fix this"},
        ]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")
        self.assertEqual(result["blockers"], [])

    def test_both_hygiene_flags_approved(self):
        """scope_creep + leftover_artifacts both non-empty, everything else clean → APPROVED."""
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["src/x.py"]
        hygiene["leftover_artifacts"] = [{"file": "src/x.py", "line": 3, "artifact": "debugger"}]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertNotIn("hygiene_flags", blocker_types)

    def test_hygiene_flags_advisory_reason_present(self):
        """When hygiene flags are set, an advisory reason line appears in reasons."""
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["src/x.py"]
        hygiene["leftover_artifacts"] = [{"file": "src/y.py", "line": 1, "artifact": "TODO"}]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        reasons_text = " ".join(result["reasons"])
        self.assertIn("advisory", reasons_text.lower())
        self.assertIn("non-blocking", reasons_text.lower())

    def test_hygiene_plus_real_blocker_needs_work(self):
        """Hygiene flags + a real blocker (FAIL AC) → NEEDS WORK driven by real blocker.

        The presence of hygiene flags is incidental — the verdict is NEEDS WORK
        because of the ac_failure blocker, not because of hygiene.
        """
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["src/unrelated.py"]
        hygiene["leftover_artifacts"] = [{"file": "src/a.py", "line": 1, "artifact": "console.log"}]
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("PASS", "AC-2"), _ac("PASS", "AC-3")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("ac_failure", blocker_types)
        self.assertNotIn("hygiene_flags", blocker_types)

    def test_hygiene_type_never_in_blockers_any_scenario(self):
        """hygiene_flags type is never emitted in blockers under any scenario."""
        scenarios = [
            # (scope_creep, leftover_artifacts, ac_status, mechanical)
            (["src/a.py"], [], "PASS", "pass"),
            ([], [{"file": "b.py", "line": 1, "artifact": "TODO"}], "PASS", "pass"),
            (["src/a.py"], [{"file": "b.py", "line": 1, "artifact": "TODO"}], "FAIL", "failed"),
            ([], [], "PASS", "pass"),
        ]
        for scope_creep, leftover, ac_status, mech in scenarios:
            with self.subTest(scope_creep=scope_creep, ac_status=ac_status, mech=mech):
                hygiene = _empty_hygiene()
                hygiene["scope_creep"] = scope_creep
                hygiene["leftover_artifacts"] = leftover
                result = compute_verdict(
                    ac_results=[_ac(ac_status)],
                    mechanical_status=mech,
                    review_findings=_empty_review(),
                    hygiene=hygiene,
                    ac_verification_mode="code-only",
                )
                blocker_types = [b["type"] for b in result["blockers"]]
                self.assertNotIn(
                    "hygiene_flags", blocker_types,
                    msg="hygiene_flags appeared in blockers for scenario: "
                        "scope_creep={0}, ac={1}, mech={2}".format(scope_creep, ac_status, mech),
                )


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
        """Real blockers (FAIL AC + mechanical) → NEEDS WORK regardless of hygiene flags."""
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["src/extra.py"]
        # 1/3 = 33% < 50% failure rate → NEEDS WORK (not REJECTED)
        # scope_creep is advisory — NEEDS WORK is driven by ac_failure + mechanical_failed
        result = compute_verdict(
            ac_results=[_ac("FAIL"), _ac("PASS", "AC-2"), _ac("PASS", "AC-3")],
            mechanical_status="self_repair",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        # Real blockers are present; hygiene_flags is NOT
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("ac_failure", blocker_types)
        self.assertIn("mechanical_failed", blocker_types)
        self.assertNotIn("hygiene_flags", blocker_types)

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


class TestComputeVerdictMediumGate(unittest.TestCase):
    """D3 / D4 — confirmed Medium findings gate the /verify verdict.

    D3 threshold: any confirmed (post-refutation) Medium non-constitution finding
    → NEEDS WORK.  Info stays advisory/non-gating.  Medium never escalates to
    REJECTED.  Contested Medium does NOT gate (confirmed-only per D3/OQ-3).

    D4: hygiene (scope_creep / leftover_artifacts) stays advisory.  The Medium gate
    reads only real CODE findings, never hygiene flags.  A clean feature with only
    hygiene flags must still be APPROVED (plan-34 regression guard).
    """

    def test_confirmed_medium_non_constitution_needs_work(self):
        """One confirmed Medium non-constitution finding → NEEDS WORK, medium_finding blocker."""
        review = _empty_review()
        review["confirmed"] = [_finding(severity="Medium", category="mislogic")]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("medium_finding", blocker_types)

    def test_medium_finding_blocker_detail_content(self):
        """medium_finding blocker detail mentions count and the pattern."""
        review = _empty_review()
        review["confirmed"] = [_finding(severity="Medium", category="best_practice")]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        blocker = next(b for b in result["blockers"] if b["type"] == "medium_finding")
        self.assertIn("1", blocker["detail"])
        self.assertIn("Medium", blocker["detail"])

    def test_info_finding_only_approved(self):
        """Info-severity finding only → APPROVED (Info stays advisory/non-gating)."""
        review = _empty_review()
        review["confirmed"] = [_finding(severity="Info", category="mislogic")]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertNotIn("medium_finding", blocker_types)

    def test_confirmed_high_still_needs_work(self):
        """Confirmed High → still NEEDS WORK (unchanged critical_high_finding behavior)."""
        review = _empty_review()
        review["confirmed"] = [_finding(severity="High", category="mislogic")]
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
        # medium_finding should NOT also appear for a High-severity finding
        self.assertNotIn("medium_finding", blocker_types)

    def test_confirmed_constitution_violation_still_rejected(self):
        """Confirmed constitution violation → REJECTED (unchanged; constitution path)."""
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

    def test_plan34_regression_hygiene_only_approved(self):
        """Plan-34 regression: clean feature with only hygiene flags → APPROVED.

        The Medium gate reads only real CODE findings, NEVER hygiene flags.
        scope_creep and leftover_artifacts stay advisory (D4).
        This is the mandatory plan-34 false-positive regression guard.
        """
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["specs/001-feature/review.md", "design/reference.html"]
        hygiene["leftover_artifacts"] = [
            {"file": "src/a.ts", "line": 5, "artifact": "console.log"},
        ]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=_empty_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertNotIn("medium_finding", blocker_types)
        self.assertNotIn("hygiene_flags", blocker_types)
        self.assertEqual(result["blockers"], [])

    def test_contested_medium_does_not_gate(self):
        """CONTESTED Medium (in contested, not confirmed) → does NOT gate (confirmed-only per D3).

        Result is APPROVED if nothing else blocks.
        """
        review = _empty_review()
        # Medium finding placed in contested, not confirmed
        review["contested"] = [_finding(severity="Medium", category="best_practice")]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "APPROVED")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertNotIn("medium_finding", blocker_types)

    def test_medium_constitution_violation_uses_constitution_path_not_medium(self):
        """A Medium-severity constitution violation is handled by constitution_confirmed,
        NOT also counted as a medium_finding blocker.

        The `not _is_constitution_violation(f)` exclusion in the medium_confirmed gather
        prevents double-counting.
        """
        review = _empty_review()
        # Medium severity but it is a constitution violation
        medium_constitution = {
            "severity": "Medium",
            "file": "src/a.py",
            "line": 10,
            "pattern": "Medium-severity constitution rule break",
            "category": "constitution",
            "tags": ["[CONSTITUTION-VIOLATION]"],
            "confidence": "Likely",
        }
        review["confirmed"] = [medium_constitution]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        # Constitution violation path fires → REJECTED
        self.assertEqual(result["verdict"], "REJECTED")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("constitution_confirmed", blocker_types)
        # medium_finding must NOT appear — the exclusion works
        self.assertNotIn("medium_finding", blocker_types)

    def test_medium_never_escalates_to_rejected(self):
        """Medium findings NEVER escalate to REJECTED (only NEEDS WORK per D3).

        Even with a large number of confirmed Medium findings, the verdict stays
        NEEDS WORK, not REJECTED.  REJECTED stays reserved for constitution violations
        and high AC failure rates.
        """
        review = _empty_review()
        review["confirmed"] = [
            _finding(severity="Medium", category="mislogic"),
            _finding(severity="Medium", category="best_practice"),
            _finding(severity="Medium", category="duplication"),
            _finding(severity="Medium", category="system_design"),
            _finding(severity="Medium", category="mislogic"),
        ]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        self.assertNotEqual(result["verdict"], "REJECTED")

    def test_multiple_medium_findings_single_blocker(self):
        """Multiple confirmed Medium findings → single medium_finding blocker."""
        review = _empty_review()
        review["confirmed"] = [
            _finding(severity="Medium", category="mislogic"),
            _finding(severity="Medium", category="best_practice"),
        ]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        medium_blockers = [b for b in result["blockers"] if b["type"] == "medium_finding"]
        # Exactly one medium_finding blocker regardless of finding count
        self.assertEqual(len(medium_blockers), 1)
        self.assertIn("2", medium_blockers[0]["detail"])

    def test_more_than_3_medium_findings_truncated_summary(self):
        """More than 3 confirmed Medium findings → summary truncated with '+ N more'."""
        review = _empty_review()
        review["confirmed"] = [
            _finding(severity="Medium", category="mislogic"),
            _finding(severity="Medium", category="best_practice"),
            _finding(severity="Medium", category="duplication"),
            _finding(severity="Medium", category="system_design"),
        ]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        reasons_text = " ".join(result["reasons"])
        self.assertIn("+ 1 more", reasons_text)

    def test_medium_with_passing_acs_needs_work(self):
        """Confirmed Medium + all ACs pass → NEEDS WORK driven by medium_finding."""
        review = _empty_review()
        review["confirmed"] = [_finding(severity="Medium")]
        result = compute_verdict(
            ac_results=[_ac("PASS"), _ac("PASS", "AC-2"), _ac("PASS", "AC-3")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("medium_finding", blocker_types)
        # Only the medium_finding blocker — no AC blocker
        self.assertNotIn("ac_failure", blocker_types)

    def test_medium_in_off_mode_still_gates(self):
        """Confirmed Medium gates the verdict in all modes, including ac_verification_mode=off.

        The Medium gate is independent of ac_verification_mode — it reads review findings,
        not AC results.
        """
        review = _empty_review()
        review["confirmed"] = [_finding(severity="Medium")]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="off",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("medium_finding", blocker_types)

    def test_medium_reason_line_present(self):
        """A confirmed Medium finding produces a reason line describing the finding."""
        review = _empty_review()
        review["confirmed"] = [_finding(severity="Medium", category="best_practice")]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        reasons_text = " ".join(result["reasons"])
        self.assertIn("Medium", reasons_text)

    def test_medium_and_high_together_both_blockers(self):
        """BOTH a confirmed High AND a confirmed Medium → NEEDS WORK (not REJECTED), both blocker types present.

        Guards against a future edit accidentally making Medium escalate to REJECTED
        when a High co-occurs.  The High fires critical_high_finding; the Medium fires
        medium_finding independently.  Neither path touches is_rejected.
        """
        review = _empty_review()
        review["confirmed"] = [
            _finding(severity="High", category="mislogic"),
            _finding(severity="Medium", category="best_practice"),
        ]
        result = compute_verdict(
            ac_results=[_ac("PASS")],
            mechanical_status="pass",
            review_findings=review,
            hygiene=_empty_hygiene(),
            ac_verification_mode="code-only",
        )
        self.assertEqual(result["verdict"], "NEEDS WORK")
        types = [b["type"] for b in result["blockers"]]
        self.assertIn("critical_high_finding", types)
        self.assertIn("medium_finding", types)


if __name__ == "__main__":
    unittest.main()
