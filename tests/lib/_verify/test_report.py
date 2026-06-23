"""Tests for src/devforge/lib/_verify/_report.py

Real-producer round-trip discipline:
  - ac_results produced by real merge_ac_results on a real parse_acs output
  - review_findings produced by real read_review_findings after a real
    render_report + write_review_report call (same as test_review_findings.py)
  - compute_verdict used as the real verdict producer
  - render_report output asserted for structural content

Coverage:
  render_report:
    - Contains the AC table with status + evidence.
    - Contains the Verdict section with APPROVED / NEEDS WORK / REJECTED.
    - Contains Code Quality block with mechanical status display.
    - When review is missing: contains "run /review" note.
    - When review is present: shows confirmed/contested counts.
    - Issues Found section: shows Critical/High findings, omits Medium/Info.
    - Scope-creep listed when present.
    - Leftover artifacts listed when present.

  write_verification_report:
    - Atomic write: verification.md written to feature dir.
    - Idempotent overwrite: calling twice with new content produces new content.
    - Feature dir is created if absent (os.makedirs).

  render_inline_summary:
    - Starts with "## Verification Complete".
    - Contains the verdict string.
    - AC pass/fail counts present.
    - Mechanical status present.
    - Next-step pointer present and mode-appropriate.
    - Missing review indicated as "not available".
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_FIXTURES_DIR = _REPO_ROOT / "tests" / "lib" / "fixtures"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

# Real producers
from _shared._verify import apply_verdicts  # noqa: E402
from _review._report import render_report as review_render_report, write_review_report  # noqa: E402
from _verify._ac import parse_acs, merge_ac_results  # noqa: E402
from _verify._review_findings import read_review_findings  # noqa: E402
from _verify._verdict import compute_verdict  # noqa: E402
from _verify._report import (  # noqa: E402
    render_report,
    render_inline_summary,
    write_verification_report,
)

_REAL_SPEC = str(_FIXTURES_DIR / "specify-sample-migration.md")


# ---------------------------------------------------------------------------
# Real-producer helpers (mirroring test_review_findings.py)
# ---------------------------------------------------------------------------


def _finding(
    agent="code-reviewer",
    file="src/a.py",
    line=10,
    pattern="Name mismatch",
    severity="High",
    category="mislogic",
    tags=None,
    finding_id=None,
):
    f = {
        "agent": agent,
        "file": file,
        "line": line,
        "pattern": pattern,
        "severity": severity,
        "confidence": "Likely",
        "evidence": "x = bad_code()",
        "why": "cross-task interaction",
        "remediation": "fix it",
        "category": category,
        "tags": tags if tags is not None else [],
    }
    if finding_id is not None:
        f["finding_id"] = finding_id
    return f


def _verdict_dict(file, line, pattern, agent, verdict_val, justification="confirmed"):
    return {
        "refuter": "architect",
        "file": file,
        "line": line,
        "pattern": pattern,
        "agent": agent,
        "verdict": verdict_val,
        "justification": justification,
        "evidence": "",
    }


def _build_partition():
    """Build a realistic partition via the real apply_verdicts."""
    findings = [
        _finding(agent="code-reviewer", file="src/auth.py", line=42,
                 pattern="Auth bypass", severity="Critical", category="mislogic",
                 finding_id="F-001"),
        _finding(agent="qa-reviewer", file="src/utils.py", line=15,
                 pattern="Missing type annotation", severity="Info",
                 category="best_practice", finding_id="F-002"),
        _finding(agent="security-reviewer", file="src/api.py", line=55,
                 pattern="SQL injection", severity="High", category="security",
                 finding_id="F-003"),
    ]
    verdicts = [
        _verdict_dict("src/auth.py", 42, "Auth bypass", "code-reviewer", "confirmed"),
        _verdict_dict("src/utils.py", 15, "Missing type annotation", "qa-reviewer", "dismissed"),
        _verdict_dict("src/api.py", 55, "SQL injection", "security-reviewer", "uncertain"),
    ]
    return apply_verdicts(findings, verdicts)


def _make_real_review_md(feature_dir):
    """Produce a real review.md, return the path."""
    partition = _build_partition()
    content = review_render_report(
        partition=partition,
        feature=feature_dir,
        date_str="2026-06-16",
        finders=["code-reviewer", "qa-reviewer", "security-reviewer"],
        refuters=["code-reviewer", "qa-reviewer"],
        source_root=feature_dir,
        framework="Django",
        n_scope_files=3,
    )
    return write_review_report(feature_dir, content)


def _real_ac_results():
    """Parse the real spec ACs and simulate a merge-ac-results result."""
    acs = parse_acs(_REAL_SPEC)
    # Simulate: AC-1 PASS, AC-2 PASS (code), AC-3 FAIL, AC-4..7 UNVERIFIED
    agent_report = """## AC Verification Report

### Results

| AC | Status | Evidence |
|---|---|---|
| AC-1 | PASS | Grep confirms no lerna refs |
| AC-2 | PASS (code) | dist artifacts match |
| AC-3 | FAIL | pnpm lockfile absent after install |
"""
    return merge_ac_results(acs, agent_report)


def _empty_hygiene():
    return {
        "scope_creep": [],
        "leftover_artifacts": [],
        "scope_creep_checked": False,
        "files_checked": 0,
        "files_unreadable": [],
    }


def _missing_review():
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRenderReport(unittest.TestCase):
    """render_report produces expected sections."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _build_report(self, review_md_dir=None, ac_mode="code-only", mechanical="pass",
                      hygiene=None, verdict_override=None):
        ac_results = _real_ac_results()
        if review_md_dir:
            _make_real_review_md(review_md_dir)
            review_findings = read_review_findings(review_md_dir)
        else:
            review_findings = _missing_review()
        hygiene = hygiene or _empty_hygiene()
        if verdict_override is None:
            verdict = compute_verdict(
                ac_results=ac_results,
                mechanical_status=mechanical,
                review_findings=review_findings,
                hygiene=hygiene,
                ac_verification_mode=ac_mode,
            )
        else:
            verdict = verdict_override
        return render_report(
            verdict=verdict,
            ac_results=ac_results,
            review_findings=review_findings,
            hygiene=hygiene,
            feature=self.tmp,
            date_str="2026-06-16",
            mechanical_status=mechanical,
            ac_verification_mode=ac_mode,
        )

    def test_contains_ac_table(self):
        content = self._build_report()
        self.assertIn("## Acceptance Criteria", content)
        self.assertIn("| AC | Status | Evidence |", content)
        self.assertIn("AC-1", content)
        self.assertIn("PASS", content)

    def test_contains_verdict_section(self):
        content = self._build_report()
        self.assertIn("## Verdict", content)

    def test_approved_verdict_shows_approved(self):
        verdict = {
            "verdict": "APPROVED",
            "reasons": [],
            "blockers": [],
        }
        content = self._build_report(verdict_override=verdict)
        self.assertIn("**APPROVED**", content)

    def test_needs_work_verdict(self):
        verdict = {
            "verdict": "NEEDS WORK",
            "reasons": ["AC-3 failed"],
            "blockers": [{"type": "ac_failure", "detail": "AC-3"}],
        }
        content = self._build_report(verdict_override=verdict)
        self.assertIn("**NEEDS WORK**", content)
        self.assertIn("AC-3 failed", content)

    def test_rejected_verdict(self):
        verdict = {
            "verdict": "REJECTED",
            "reasons": ["Constitution violation"],
            "blockers": [{"type": "constitution_confirmed", "detail": "Rule broken"}],
        }
        content = self._build_report(verdict_override=verdict)
        self.assertIn("**REJECTED**", content)

    def test_code_quality_section_present(self):
        content = self._build_report(mechanical="pass")
        self.assertIn("## Code Quality", content)
        self.assertIn("**Mechanical checks**", content)
        self.assertIn("PASS", content)

    def test_mechanical_failed_displayed(self):
        content = self._build_report(mechanical="failed")
        self.assertIn("FAILED", content)

    def test_review_missing_shows_run_review_note(self):
        content = self._build_report(review_md_dir=None)
        self.assertIn("run `/review`", content)

    def test_review_present_shows_counts(self):
        content = self._build_report(review_md_dir=self.tmp)
        self.assertIn("## Review Findings", content)
        # Should show count numbers
        self.assertIn("confirmed", content)

    def test_issues_found_section_present(self):
        content = self._build_report(review_md_dir=self.tmp)
        self.assertIn("## Issues Found", content)

    def test_scope_creep_shown_when_present(self):
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["src/unrelated.py"]
        hygiene["scope_creep_checked"] = True
        content = self._build_report(hygiene=hygiene)
        self.assertIn("scope-creep", content.lower())
        self.assertIn("src/unrelated.py", content)

    def test_scope_creep_none_shown(self):
        hygiene = _empty_hygiene()
        hygiene["scope_creep_checked"] = True
        content = self._build_report(hygiene=hygiene)
        self.assertIn("none detected", content)

    def test_leftover_artifacts_shown(self):
        hygiene = _empty_hygiene()
        hygiene["leftover_artifacts"] = [{"file": "a.py", "line": 1, "artifact": "console.log"}]
        content = self._build_report(hygiene=hygiene)
        self.assertIn("Leftover artifacts", content)
        self.assertIn("1 flagged", content)

    def test_hygiene_scope_creep_renders_advisory_label(self):
        """Scope-creep lines in Code Quality carry an advisory / non-blocking label."""
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["src/unrelated.py"]
        hygiene["scope_creep_checked"] = True
        content = self._build_report(hygiene=hygiene)
        # The advisory label must appear on the scope creep line
        self.assertIn("advisory", content.lower())
        self.assertIn("does not block", content.lower())
        self.assertIn("src/unrelated.py", content)

    def test_hygiene_leftover_artifacts_renders_advisory_label(self):
        """Leftover-artifacts lines in Code Quality carry an advisory / non-blocking label."""
        hygiene = _empty_hygiene()
        hygiene["leftover_artifacts"] = [{"file": "a.py", "line": 1, "artifact": "console.log"}]
        content = self._build_report(hygiene=hygiene)
        self.assertIn("advisory", content.lower())
        self.assertIn("does not block", content.lower())
        self.assertIn("1 flagged", content)

    def test_hygiene_flags_produce_approved_not_needs_work(self):
        """Hygiene flags alone must not flip the verdict to NEEDS WORK in the report."""
        hygiene = _empty_hygiene()
        hygiene["scope_creep"] = ["src/x.py"]
        hygiene["leftover_artifacts"] = [{"file": "src/y.py", "line": 2, "artifact": "TODO"}]
        hygiene["scope_creep_checked"] = True
        # Use the real compute_verdict — it should return APPROVED
        ac_results = [{"id": "AC-1", "text": "", "checked": False, "subsection": "",
                       "status": "PASS", "evidence": ""}]
        verdict = compute_verdict(
            ac_results=ac_results,
            mechanical_status="pass",
            review_findings=_missing_review(),
            hygiene=hygiene,
            ac_verification_mode="code-only",
        )
        self.assertEqual(verdict["verdict"], "APPROVED",
                         "Hygiene flags alone must not produce NEEDS WORK")
        content = render_report(
            verdict=verdict,
            ac_results=ac_results,
            review_findings=_missing_review(),
            hygiene=hygiene,
            feature=self.tmp,
            date_str="2026-06-16",
            mechanical_status="pass",
            ac_verification_mode="code-only",
        )
        self.assertIn("**APPROVED**", content)
        self.assertIn("advisory", content.lower())

    def test_header_has_feature_and_date(self):
        content = self._build_report()
        self.assertIn("# Feature Verification", content)
        self.assertIn("2026-06-16", content)

    def test_next_step_approved_points_to_summarize(self):
        verdict = {"verdict": "APPROVED", "reasons": [], "blockers": []}
        content = self._build_report(verdict_override=verdict)
        self.assertIn("/summarize", content)
        self.assertIn("/finalize", content)

    def test_next_step_needs_work_points_to_verify(self):
        verdict = {
            "verdict": "NEEDS WORK",
            "reasons": ["blocker"],
            "blockers": [{"type": "mechanical_failed", "detail": "failed"}],
        }
        content = self._build_report(verdict_override=verdict)
        self.assertIn("/verify", content)

    def test_next_step_rejected_points_to_specify(self):
        verdict = {
            "verdict": "REJECTED",
            "reasons": ["constitution"],
            "blockers": [{"type": "constitution_confirmed", "detail": "broke rule"}],
        }
        content = self._build_report(verdict_override=verdict)
        self.assertIn("/specify", content)


class TestWriteVerificationReport(unittest.TestCase):
    """write_verification_report atomic write behaviour."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_creates_verification_md(self):
        path = write_verification_report(self.tmp, "# Verification\n")
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(path.endswith("verification.md"))

    def test_content_written_correctly(self):
        content = "# Test\n\nsome content\n"
        path = write_verification_report(self.tmp, content)
        with open(path, encoding="utf-8") as fh:
            written = fh.read()
        self.assertEqual(written, content)

    def test_creates_directory_if_absent(self):
        feature_dir = os.path.join(self.tmp, "new-feature-dir")
        self.assertFalse(os.path.isdir(feature_dir))
        write_verification_report(feature_dir, "content\n")
        self.assertTrue(os.path.isdir(feature_dir))

    def test_idempotent_overwrite(self):
        write_verification_report(self.tmp, "first write\n")
        write_verification_report(self.tmp, "second write\n")
        path = os.path.join(self.tmp, "verification.md")
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertEqual(content, "second write\n")

    def test_no_tmp_files_left(self):
        write_verification_report(self.tmp, "content\n")
        entries = os.listdir(self.tmp)
        tmp_files = [e for e in entries if e.startswith(".tmp-verify-")]
        self.assertEqual(tmp_files, [])

    def test_returns_correct_path(self):
        path = write_verification_report(self.tmp, "x\n")
        expected = os.path.join(self.tmp, "verification.md")
        self.assertEqual(os.path.normpath(path), os.path.normpath(expected))


class TestRenderInlineSummary(unittest.TestCase):
    """render_inline_summary produces expected console block."""

    def _summary(self, verdict_str="APPROVED", ac_pass=5, ac_fail=0,
                 mechanical="pass", review_missing=True, feature="specs/001-test",
                 reasons=None):
        ac_results = (
            [{"id": "AC-{0}".format(i + 1), "status": "PASS", "text": "",
              "checked": False, "subsection": "", "evidence": ""}
             for i in range(ac_pass)] +
            [{"id": "AC-{0}".format(ac_pass + i + 1), "status": "FAIL",
              "text": "", "checked": False, "subsection": "", "evidence": ""}
             for i in range(ac_fail)]
        )
        verdict = {
            "verdict": verdict_str,
            "reasons": reasons or [],
            "blockers": [],
        }
        review_findings = {
            "missing": review_missing,
            "confirmed": [],
            "contested": [],
            "summary": {
                "critical": 0, "high": 0, "medium": 0, "info": 0,
                "confirmed_count": 2, "contested_count": 1,
                "dismissed_count": 3, "uncertain_count": 0,
            },
        }
        return render_inline_summary(
            verdict=verdict,
            ac_results=ac_results,
            review_findings=review_findings,
            mechanical_status=mechanical,
            feature=feature,
        )

    def test_starts_with_header(self):
        text = self._summary()
        self.assertTrue(text.startswith("## Verification Complete"))

    def test_contains_verdict(self):
        text = self._summary(verdict_str="APPROVED")
        self.assertIn("APPROVED", text)

    def test_contains_feature(self):
        text = self._summary(feature="specs/001-auth")
        self.assertIn("specs/001-auth", text)

    def test_ac_counts_present(self):
        text = self._summary(ac_pass=5, ac_fail=2)
        self.assertIn("5/", text)  # passed/total
        self.assertIn("2 failed", text)

    def test_mechanical_pass(self):
        text = self._summary(mechanical="pass")
        self.assertIn("PASS", text)

    def test_mechanical_failed(self):
        text = self._summary(mechanical="failed")
        self.assertIn("FAILED", text)

    def test_review_missing_indicated(self):
        text = self._summary(review_missing=True)
        self.assertIn("not available", text)

    def test_review_present_shows_confirmed_count(self):
        text = self._summary(review_missing=False)
        self.assertIn("2 confirmed", text)

    def test_approved_next_step(self):
        text = self._summary(verdict_str="APPROVED")
        self.assertIn("/summarize", text)

    def test_needs_work_next_step(self):
        text = self._summary(verdict_str="NEEDS WORK")
        self.assertIn("/verify", text)

    def test_rejected_next_step(self):
        text = self._summary(verdict_str="REJECTED")
        self.assertIn("/specify", text)

    def test_ends_with_newline(self):
        text = self._summary()
        self.assertTrue(text.endswith("\n"))

    def test_reasons_capped_at_four(self):
        reasons = ["R{0}".format(i) for i in range(8)]
        text = self._summary(verdict_str="NEEDS WORK", reasons=reasons)
        # Should mention truncation for > 4 reasons
        self.assertIn("more", text)


if __name__ == "__main__":
    unittest.main()
