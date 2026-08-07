"""Tests for src/devforge/lib/_audit/_report.py.

Coverage:
  render_report     — section headers in order; finding details present;
                      bucketing by declared category (system_design, best_practice,
                      duplication, security, mislogic);
                      [CONSTITUTION-VIOLATION] tag overrides declared category;
                      category-less finding defaults to mislogic (backward-compat);
                      blind_spot category shares the mislogic bucket;
                      architect agent with category:mislogic goes to mislogic
                        (proves agent-name heuristic is dead);
                      Top-10 vs Top-5 (narrow mode) selection;
                      empty findings renders without crash;
                      discard_counts present in Summary;
                      next_candidates rendered in hotspot mode;
                      recurring table rendered;
                      file-grouped layout: one ### per file, files path-sorted,
                        within-sub-group severity sort, severity inline on finding line;
                      high-hallucination warning when quote_mismatch > 5;
                      Not-Audited section has updated performance wording.
  compute_out_path  — base path free; collision suffix -2, -3.
  write_report      — creates .gitignore on first run;
                      does NOT clobber existing .gitignore;
                      atomic write produces the file;
                      returns correct path.
  ensure_gitignore  — idempotent; does not clobber existing content.
"""

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

from _audit._report import (  # noqa: E402
    compute_out_path,
    ensure_gitignore,
    render_report,
    write_report,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_critical_mislogic_finding(finding_id="F-001"):
    return {
        "finding_id": finding_id,
        "agent": "code-reviewer",
        "severity": "Critical",
        "file": "src/auth.py",
        "line": 42,
        "pattern": "null check bypass in login handler",
        "confidence": "Certain",
        "evidence": "if user is not None:\n    return user",
        "why": "The condition allows None to pass through on the else branch.",
        "remediation": "Add explicit None check before returning.",
        "tags": [],
    }


def _make_high_security_finding(finding_id="F-002"):
    return {
        "finding_id": finding_id,
        "agent": "security-reviewer",
        "severity": "High",
        "file": "src/api/routes.py",
        "line": 99,
        "pattern": "SQL injection via unsanitised input",
        "confidence": "Likely",
        "evidence": "query = 'SELECT * FROM users WHERE id=' + user_id",
        "why": "String concatenation with user input enables SQL injection.",
        "remediation": "Use parameterised queries.",
        "tags": ["[CROSS-AGENT]"],
    }


def _make_constitution_finding(finding_id="F-003"):
    return {
        "finding_id": finding_id,
        "agent": "code-reviewer",
        "severity": "Critical",
        "file": "src/core.py",
        "line": 10,
        "pattern": "Missing error handling violates constitution rule 1",
        "confidence": "Certain",
        "evidence": "result = fetch(url)  # no try/except",
        "why": "Violates rule: never swallow errors.",
        "remediation": "Wrap in try/except and log with reason.",
        "tags": ["[CONSTITUTION-VIOLATION]"],
    }


def _make_architect_finding(finding_id="F-004"):
    return {
        "finding_id": finding_id,
        "agent": "architect",
        "severity": "High",
        "file": "src/services/user.py",
        "line": 55,
        "pattern": "cross-module coupling: service imports model directly",
        "confidence": "Likely",
        "evidence": "from models.user import User",
        "why": "Direct model import creates tight coupling.",
        "remediation": "Use repository pattern.",
        "tags": [],
    }


def _make_finding(**overrides):
    """Return a minimal valid finding dict with stable defaults.

    Any kwarg overrides the corresponding key.  Always injects finding_id
    so the dict is recognised as a pre-labelled finding (use raw dicts
    without finding_id to exercise the auto-assignment path instead).
    """
    base = {
        "finding_id": "F-001",
        "agent": "code-reviewer",
        "severity": "High",
        "file": "src/example.py",
        "line": 10,
        "pattern": "example pattern",
        "confidence": "Likely",
        "evidence": "some code snippet",
        "why": "This is wrong because X.",
        "remediation": "Do Y instead.",
        "tags": [],
    }
    base.update(overrides)
    return base


def _make_report_dict(mode="broad", findings=None, top10=None):
    if findings is None:
        findings = [
            _make_critical_mislogic_finding("F-001"),
            _make_high_security_finding("F-002"),
            _make_constitution_finding("F-003"),
            _make_architect_finding("F-004"),
        ]
    if top10 is None:
        top10 = ["F-003", "F-001", "F-002", "F-004"]

    return {
        "mode": mode,
        "audit_date": "2026-01-15",
        "scope_description": "full codebase",
        "scope_files": ["src/auth.py", "src/api/routes.py", "src/core.py"],
        "agents_run": ["code-reviewer", "security-reviewer", "architect"],
        "agents_skipped": ["qa-engineer"],
        "agents_failed": [],
        "findings": findings,
        "top10": top10,
        "source_root": "/workspace/myapp",
        "framework": "Django",
        "language": "Python",
        "recurring_resolved": [
            {"review": "specs/001-auth/review.md", "description": "Old race condition", "status": "RESOLVED"},
        ],
        "recurring_unresolved": [
            {"review": "specs/002-api/review.md", "description": "Null check bypass in X", "status": "STILL PRESENT, SPREAD TO 4 FILES"},
        ],
        "recurring_reviews_consulted": ["specs/001-auth/review.md", "specs/002-api/review.md"],
        "discard_counts": {
            "file_missing": 2,
            "line_oob": 1,
            "quote_mismatch": 3,
            "evidence_empty": 0,
            "pattern_missing": 1,
        },
        "consensus": {
            "F-002": ["code-reviewer", "security-reviewer"],
        },
        "next_candidates": [],
        "blind_spots": [],
    }


# ---------------------------------------------------------------------------
# render_report — section header ordering
# ---------------------------------------------------------------------------

class TestRenderReportSectionOrder(unittest.TestCase):
    """Required section headers must appear in the correct order."""

    def setUp(self):
        self.report = render_report(_make_report_dict())

    def _assert_order(self, *headers):
        positions = []
        for h in headers:
            pos = self.report.find(h)
            self.assertGreater(
                pos, -1, "Expected section header not found: {!r}".format(h)
            )
            positions.append(pos)
        self.assertEqual(
            positions, sorted(positions),
            "Section headers are not in expected order: {}".format(headers),
        )

    def test_header_block_present(self):
        self.assertIn("# Audit Report — 2026-01-15", self.report)

    def test_top10_section_present(self):
        self.assertIn("## Top 10 Priorities", self.report)

    def test_findings_by_file_section_present(self):
        self.assertIn("## Findings by File", self.report)

    def test_no_severity_tier_sections(self):
        # The old severity-grouped layout is gone
        self.assertNotIn("## Critical Findings", self.report)
        self.assertNotIn("## High Findings", self.report)
        self.assertNotIn("## Medium Findings", self.report)
        self.assertNotIn("## Info / Observations", self.report)

    def test_recurring_section_present(self):
        self.assertIn("## Recurring Issues Status", self.report)

    def test_not_audited_section_present(self):
        self.assertIn("## Not Audited", self.report)

    def test_summary_section_present(self):
        self.assertIn("## Summary", self.report)

    def test_methodology_section_present(self):
        self.assertIn("## Methodology", self.report)

    def test_section_order_top10_findings_recurring_summary(self):
        self._assert_order(
            "## Top 10 Priorities",
            "## Findings by File",
            "## Recurring Issues Status",
            "## Not Audited",
            "## Summary",
            "## Methodology",
        )


# ---------------------------------------------------------------------------
# render_report — finding details
# ---------------------------------------------------------------------------

class TestRenderReportFindingDetails(unittest.TestCase):
    def setUp(self):
        self.report = render_report(_make_report_dict())

    def test_critical_mislogic_finding_present(self):
        self.assertIn("null check bypass in login handler", self.report)
        # Line appears inline on the finding line (:42)
        self.assertIn(":42", self.report)

    def test_security_finding_present(self):
        self.assertIn("SQL injection via unsanitised input", self.report)
        self.assertIn(":99", self.report)

    def test_constitution_finding_present(self):
        self.assertIn("Missing error handling violates constitution rule 1", self.report)
        self.assertIn(":10", self.report)

    def test_architect_finding_present(self):
        self.assertIn("cross-module coupling", self.report)
        self.assertIn(":55", self.report)

    def test_evidence_blocks_present(self):
        self.assertIn("null check bypass", self.report)
        self.assertIn("if user is not None:", self.report)

    def test_confidence_values_present(self):
        self.assertIn("Certain", self.report)
        self.assertIn("Likely", self.report)

    def test_severity_inline_on_finding_line(self):
        # Critical finding: "[Critical]" must appear on the finding bullet line
        # (not under a ## Critical Findings header, but inline in the bullet)
        self.assertIn("[Critical]", self.report)
        self.assertIn("[High]", self.report)

    def test_file_path_appears_as_section_header(self):
        # Under the new layout, file paths are ### headers, not in finding bullets
        self.assertIn("### src/auth.py", self.report)
        self.assertIn("### src/api/routes.py", self.report)
        self.assertIn("### src/core.py", self.report)
        self.assertIn("### src/services/user.py", self.report)


# ---------------------------------------------------------------------------
# render_report — file-grouped layout
# ---------------------------------------------------------------------------

class TestRenderReportFileGrouped(unittest.TestCase):
    """File-grouped layout: one ### per file, correct order, category sub-groups."""

    def setUp(self):
        # Two findings in same file (src/multi.py), one in a different file
        self.f_a = _make_finding(
            finding_id="F-001",
            severity="High",
            file="src/multi.py",
            line=10,
            pattern="issue A in multi",
            category="mislogic",
        )
        self.f_b = _make_finding(
            finding_id="F-002",
            severity="Medium",
            file="src/multi.py",
            line=20,
            pattern="issue B in multi",
            category="system_design",
        )
        self.f_c = _make_finding(
            finding_id="F-003",
            severity="Critical",
            file="src/other.py",
            line=5,
            pattern="issue in other",
            category="security",
        )
        findings = [self.f_a, self.f_b, self.f_c]
        rd = _make_report_dict(
            findings=findings,
            top10=["F-001", "F-002", "F-003"],
        )
        self.report = render_report(rd)

    def test_findings_by_file_section_present(self):
        self.assertIn("## Findings by File", self.report)

    def test_two_findings_same_file_one_header(self):
        # src/multi.py must appear exactly once as a ### header
        count = self.report.count("### src/multi.py")
        self.assertEqual(count, 1)

    def test_both_findings_under_single_file_header(self):
        # Extract only the ## Findings by File section to avoid matching
        # the Top-N section (which also contains the finding patterns).
        fbf_start = self.report.find("## Findings by File")
        self.assertGreater(fbf_start, -1)
        fbf_section = self.report[fbf_start:]

        multi_pos = fbf_section.find("### src/multi.py")
        other_pos = fbf_section.find("### src/other.py")
        self.assertGreater(multi_pos, -1)
        self.assertGreater(other_pos, -1)

        issue_a_pos = fbf_section.find("issue A in multi")
        issue_b_pos = fbf_section.find("issue B in multi")
        # Both must appear after the multi.py header and before other.py header
        self.assertGreater(issue_a_pos, multi_pos)
        self.assertGreater(issue_b_pos, multi_pos)
        self.assertLess(issue_a_pos, other_pos)
        self.assertLess(issue_b_pos, other_pos)

    def test_files_path_sorted(self):
        # src/multi.py < src/other.py alphabetically -> multi before other
        multi_pos = self.report.find("### src/multi.py")
        other_pos = self.report.find("### src/other.py")
        self.assertGreater(multi_pos, -1)
        self.assertGreater(other_pos, -1)
        self.assertLess(multi_pos, other_pos)

    def test_category_subgroups_as_level4_headers(self):
        # Mislogic sub-group for src/multi.py (f_a)
        self.assertIn("#### Mislogic", self.report)
        # System Design sub-group for src/multi.py (f_b)
        self.assertIn("#### System Design", self.report)
        # Security sub-group for src/other.py (f_c)
        self.assertIn("#### Security", self.report)

    def test_only_non_empty_subgroups_rendered(self):
        # Duplication and Best Practices have no findings in this report
        self.assertNotIn("#### Duplication", self.report)
        self.assertNotIn("#### Best Practices", self.report)

    def test_severity_inline_in_finding_bullet(self):
        # F-001 is High, F-002 Medium, F-003 Critical
        self.assertIn("[High]", self.report)
        self.assertIn("[Medium]", self.report)
        self.assertIn("[Critical]", self.report)

    def test_file_path_not_repeated_in_finding_bullet(self):
        # The old format included "src/multi.py:10" in the bullet line.
        # New format: file path is the ### header, bullet line has only ":10".
        # The Top-N section legitimately includes "src/multi.py:10" (for context),
        # so scope this check to the ## Findings by File section only.
        fbf_start = self.report.find("## Findings by File")
        self.assertGreater(fbf_start, -1)
        fbf_section = self.report[fbf_start:]
        # Within the file-grouped section, path+colon+line should NOT appear
        # (the path is the ### header, the bullet only has ":10").
        self.assertNotIn("src/multi.py:10", fbf_section)
        self.assertNotIn("src/multi.py:20", fbf_section)


class TestRenderReportWithinSubgroupSeveritySort(unittest.TestCase):
    """Within a sub-group, Critical must appear before High."""

    def test_critical_before_high_in_same_subgroup(self):
        f_high = _make_finding(
            finding_id="F-001",
            severity="High",
            file="src/z.py",
            line=1,
            pattern="high finding",
            category="mislogic",
        )
        f_critical = _make_finding(
            finding_id="F-002",
            severity="Critical",
            file="src/z.py",
            line=2,
            pattern="critical finding",
            category="mislogic",
        )
        # F-001 (High) is listed first in findings, but F-002 (Critical) should sort first
        rd = _make_report_dict(findings=[f_high, f_critical], top10=[])
        report = render_report(rd)

        high_pos = report.find("high finding")
        critical_pos = report.find("critical finding")
        self.assertGreater(high_pos, -1)
        self.assertGreater(critical_pos, -1)
        # critical must appear before high within the same sub-group
        self.assertLess(critical_pos, high_pos)


class TestRenderReportPathSortedFiles(unittest.TestCase):
    """Files render in lexicographic path order (tree order)."""

    def test_zzz_file_sorts_last(self):
        f_aaa = _make_finding(
            finding_id="F-001",
            severity="High",
            file="src/aaa.py",
            line=1,
            pattern="aaa pattern",
        )
        f_zzz = _make_finding(
            finding_id="F-002",
            severity="High",
            file="src/zzz.py",
            line=2,
            pattern="zzz pattern",
        )
        rd = _make_report_dict(findings=[f_zzz, f_aaa], top10=[])
        report = render_report(rd)

        aaa_pos = report.find("### src/aaa.py")
        zzz_pos = report.find("### src/zzz.py")
        self.assertGreater(aaa_pos, -1)
        self.assertGreater(zzz_pos, -1)
        # aaa must appear before zzz
        self.assertLess(aaa_pos, zzz_pos)

    def test_unknown_file_sorts_last(self):
        f_known = _make_finding(
            finding_id="F-001",
            severity="High",
            file="src/known.py",
            line=1,
            pattern="known pattern",
        )
        f_unknown = _make_finding(
            finding_id="F-002",
            severity="High",
            file="",  # empty -> (unknown file)
            line=2,
            pattern="unknown pattern",
        )
        rd = _make_report_dict(findings=[f_known, f_unknown], top10=[])
        report = render_report(rd)

        known_pos = report.find("### src/known.py")
        unknown_pos = report.find("### (unknown file)")
        self.assertGreater(known_pos, -1)
        self.assertGreater(unknown_pos, -1)
        # known file must appear before (unknown file)
        self.assertLess(known_pos, unknown_pos)


# ---------------------------------------------------------------------------
# render_report — bucketing into sub-sections
# ---------------------------------------------------------------------------

class TestRenderReportBucketing(unittest.TestCase):
    """Findings must appear in the correct #### sub-group under their file.

    The default report dict uses category-less findings (no 'category' key).
    Without a declared category all findings fall to the mislogic bucket
    EXCEPT those with [CONSTITUTION-VIOLATION] tags (override always wins).
    The architect-agent and security-reviewer-agent no longer drive bucketing.
    """

    def setUp(self):
        self.report = render_report(_make_report_dict())

    def test_constitution_violation_in_constitution_subgroup(self):
        # Constitution Violations sub-group must appear as a level-4 header
        self.assertIn("#### Constitution Violations", self.report)

    def test_constitution_subgroup_under_correct_file(self):
        # The constitution finding is in src/core.py
        core_pos = self.report.find("### src/core.py")
        const_pos = self.report.find("#### Constitution Violations")
        self.assertGreater(core_pos, -1)
        self.assertGreater(const_pos, core_pos)

    def test_category_less_finding_goes_to_mislogic(self):
        # The fixtures have no 'category' key — they go to Mislogic bucket
        self.assertIn("#### Mislogic", self.report)

    def test_no_severity_section_headers(self):
        # Old severity-tier headers are gone
        self.assertNotIn("## Critical Findings", self.report)
        self.assertNotIn("## High Findings", self.report)
        self.assertNotIn("### Mislogic / Logic Contradictions", self.report)
        self.assertNotIn("### System Design", self.report)

    def test_constitution_not_in_mislogic_subgroup(self):
        # The constitution finding should be under Constitution Violations, not Mislogic
        # Confirm by checking that constitution heading is not the same position
        const_pos = self.report.find("#### Constitution Violations")
        mislogic_pos = self.report.find("#### Mislogic")
        self.assertGreater(const_pos, -1)
        self.assertNotEqual(const_pos, mislogic_pos)


# ---------------------------------------------------------------------------
# render_report — Top-5 vs Top-10 by mode
# ---------------------------------------------------------------------------

class TestRenderReportTopN(unittest.TestCase):
    def test_broad_mode_shows_top_10_header(self):
        report = render_report(_make_report_dict(mode="broad"))
        self.assertIn("## Top 10 Priorities", report)

    def test_narrow_mode_shows_top_5_header(self):
        report = render_report(_make_report_dict(mode="narrow"))
        self.assertIn("## Top 5 Priorities", report)

    def test_narrow_mode_limits_to_5_entries(self):
        # Create 10 findings
        findings = []
        top10 = []
        for i in range(10):
            fid = "F-{0:03d}".format(i + 1)
            findings.append({
                "finding_id": fid,
                "agent": "code-reviewer",
                "severity": "High",
                "file": "src/x.py",
                "line": i + 1,
                "pattern": "issue {0}".format(i),
                "confidence": "Likely",
                "evidence": "code {0}".format(i),
                "why": "reason {0}".format(i),
                "remediation": "fix {0}".format(i),
                "tags": [],
            })
            top10.append(fid)

        rd = _make_report_dict(mode="narrow", findings=findings, top10=top10)
        report = render_report(rd)

        # Count the numbered priority lines "1. [" ... "5. ["
        # The 6th "6. [" should NOT appear in top section
        top5_section_start = report.find("## Top 5 Priorities")
        top5_section_end = report.find("\n## ", top5_section_start + 1)
        top5_section = report[top5_section_start:top5_section_end]
        # Only entries 1-5 should appear
        self.assertIn("1. ", top5_section)
        self.assertIn("5. ", top5_section)
        self.assertNotIn("6. ", top5_section)

    def test_broad_mode_allows_up_to_10_entries(self):
        findings = []
        top10 = []
        for i in range(10):
            fid = "F-{0:03d}".format(i + 1)
            findings.append({
                "finding_id": fid,
                "agent": "code-reviewer",
                "severity": "High",
                "file": "src/y.py",
                "line": i + 1,
                "pattern": "issue {0}".format(i),
                "confidence": "Likely",
                "evidence": "code {0}".format(i),
                "why": "reason {0}".format(i),
                "remediation": "fix {0}".format(i),
                "tags": [],
            })
            top10.append(fid)

        rd = _make_report_dict(mode="broad", findings=findings, top10=top10)
        report = render_report(rd)
        top10_section_start = report.find("## Top 10 Priorities")
        top10_section_end = report.find("\n## ", top10_section_start + 1)
        top10_section = report[top10_section_start:top10_section_end]
        self.assertIn("10. ", top10_section)


# ---------------------------------------------------------------------------
# render_report — discard_counts in Summary
# ---------------------------------------------------------------------------

class TestRenderReportDiscardCounts(unittest.TestCase):
    def setUp(self):
        self.report = render_report(_make_report_dict())

    def test_total_discarded_present(self):
        # 2+1+3+0+1 = 7 total
        self.assertIn("7 total", self.report)

    def test_file_missing_count_present(self):
        self.assertIn("Failed file-exists check: 2", self.report)

    def test_line_oob_count_present(self):
        self.assertIn("Failed line-number sanity: 1", self.report)

    def test_quote_mismatch_count_present(self):
        self.assertIn("Failed verbatim-quote check: 3", self.report)

    def test_no_hallucination_warning_when_under_threshold(self):
        # quote_mismatch = 3, below 5
        self.assertNotIn("agents may be hallucinating", self.report)

    def test_hallucination_warning_when_over_threshold(self):
        rd = _make_report_dict()
        rd["discard_counts"]["quote_mismatch"] = 6
        report = render_report(rd)
        self.assertIn("agents may be hallucinating", report)

    def test_evidence_empty_and_pattern_missing_lines_present(self):
        # evidence_empty=0 and pattern_missing=1 lines were previously untested
        rd = _make_report_dict(
            findings=[],
            top10=[],
        )
        rd["discard_counts"] = {
            "file_missing": 2,
            "line_oob": 1,
            "quote_mismatch": 3,
            "evidence_empty": 0,
            "pattern_missing": 1,
        }
        report = render_report(rd)
        self.assertIn("Failed evidence-non-empty check: 0", report)
        self.assertIn("Failed pattern-field check: 1", report)


# ---------------------------------------------------------------------------
# render_report — recurring issues table
# ---------------------------------------------------------------------------

class TestRenderReportRecurring(unittest.TestCase):
    def setUp(self):
        self.report = render_report(_make_report_dict())

    def test_recurring_table_header_present(self):
        self.assertIn("| Past Review | Finding | Status |", self.report)

    def test_unresolved_row_present(self):
        self.assertIn("specs/002-api/review.md", self.report)
        self.assertIn("STILL PRESENT", self.report)

    def test_resolved_row_present(self):
        self.assertIn("specs/001-auth/review.md", self.report)
        self.assertIn("RESOLVED", self.report)


# ---------------------------------------------------------------------------
# render_report — empty findings
# ---------------------------------------------------------------------------

class TestRenderReportEmptyFindings(unittest.TestCase):
    def test_empty_findings_no_crash(self):
        rd = _make_report_dict(findings=[], top10=[])
        report = render_report(rd)
        # Must still have all structural sections
        for header in (
            "# Audit Report",
            "## Top 10 Priorities",
            "## Findings by File",
            "## Recurring Issues Status",
            "## Not Audited",
            "## Summary",
            "## Methodology",
        ):
            self.assertIn(header, report, "Missing header: {!r}".format(header))

    def test_empty_findings_renders_none_line(self):
        rd = _make_report_dict(findings=[], top10=[])
        report = render_report(rd)
        # Empty findings -> "(none)" under ## Findings by File
        findings_pos = report.find("## Findings by File")
        self.assertGreater(findings_pos, -1)
        # "(none)" must appear after the section header
        none_pos = report.find("(none)", findings_pos)
        self.assertGreater(none_pos, findings_pos)

    def test_empty_findings_no_severity_tiers(self):
        rd = _make_report_dict(findings=[], top10=[])
        report = render_report(rd)
        # Old severity-tier headers must not appear
        self.assertNotIn("## Critical Findings", report)
        self.assertNotIn("## High Findings", report)
        self.assertNotIn("## Medium Findings", report)

    def test_empty_findings_summary_shows_zeros(self):
        rd = _make_report_dict(findings=[], top10=[])
        rd["discard_counts"] = {
            "file_missing": 0, "line_oob": 0,
            "quote_mismatch": 0, "evidence_empty": 0, "pattern_missing": 0,
        }
        report = render_report(rd)
        self.assertIn("Critical: 0 | High: 0 | Medium: 0 | Info: 0", report)


# ---------------------------------------------------------------------------
# render_report — hotspot next_candidates
# ---------------------------------------------------------------------------

class TestRenderReportNextCandidates(unittest.TestCase):
    def test_next_candidates_rendered_in_hotspot_mode(self):
        rd = _make_report_dict(mode="hotspot")
        rd["next_candidates"] = [
            {"rank": 11, "file": "src/heavy.py", "score": 0.72,
             "churn": 5, "callers": 12, "size_loc": 300},
            {"rank": 12, "file": "src/other.py", "score": 0.65,
             "churn": 3, "callers": 8, "size_loc": 200},
        ]
        report = render_report(rd)
        self.assertIn("## Next Candidates", report)
        self.assertIn("src/heavy.py", report)
        self.assertIn("src/other.py", report)
        self.assertIn("0.72", report)

    def test_next_candidates_not_rendered_in_broad_mode(self):
        rd = _make_report_dict(mode="broad")
        rd["next_candidates"] = [
            {"rank": 11, "file": "src/heavy.py", "score": 0.72,
             "churn": 5, "callers": 12, "size_loc": 300},
        ]
        report = render_report(rd)
        # Not rendered in broad mode
        self.assertNotIn("## Next Candidates", report)

    def test_empty_next_candidates_no_section(self):
        rd = _make_report_dict(mode="hotspot")
        rd["next_candidates"] = []
        report = render_report(rd)
        self.assertNotIn("## Next Candidates", report)


# ---------------------------------------------------------------------------
# render_report — header fields present
# ---------------------------------------------------------------------------

class TestRenderReportHeader(unittest.TestCase):
    def setUp(self):
        self.report = render_report(_make_report_dict())

    def test_scope_description_present(self):
        self.assertIn("**Scope**: full codebase", self.report)

    def test_files_audited_count_present(self):
        self.assertIn("**Files audited**: 3", self.report)

    def test_source_root_present(self):
        self.assertIn("**Source Root**: /workspace/myapp", self.report)

    def test_framework_language_present(self):
        self.assertIn("**Framework / Language**: Django / Python", self.report)

    def test_agents_skipped_noted_inline(self):
        self.assertIn("qa-engineer", self.report)
        self.assertIn("skipped", self.report)

    def test_recurring_consulted_present(self):
        self.assertIn(
            "specs/001-auth/review.md", self.report
        )


# ---------------------------------------------------------------------------
# compute_out_path
# ---------------------------------------------------------------------------

class TestComputeOutPath(unittest.TestCase):
    def test_base_path_when_dir_empty(self):
        with tempfile.TemporaryDirectory() as d:
            path = compute_out_path(d, "2026-01-15")
            self.assertEqual(
                path,
                os.path.join(d, "2026-01-15-audit.md"),
            )

    def test_collision_suffix_2(self):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "2026-01-15-audit.md")
            open(base, "w").close()  # create the file
            path = compute_out_path(d, "2026-01-15")
            self.assertEqual(
                path,
                os.path.join(d, "2026-01-15-audit-2.md"),
            )

    def test_collision_suffix_3(self):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "2026-01-15-audit.md")
            base2 = os.path.join(d, "2026-01-15-audit-2.md")
            open(base, "w").close()
            open(base2, "w").close()
            path = compute_out_path(d, "2026-01-15")
            self.assertEqual(
                path,
                os.path.join(d, "2026-01-15-audit-3.md"),
            )

    def test_different_dates_no_collision(self):
        with tempfile.TemporaryDirectory() as d:
            path1 = compute_out_path(d, "2026-01-15")
            path2 = compute_out_path(d, "2026-01-16")
            self.assertNotEqual(path1, path2)
            self.assertIn("2026-01-15", path1)
            self.assertIn("2026-01-16", path2)


# ---------------------------------------------------------------------------
# write_report
# ---------------------------------------------------------------------------

class TestWriteReport(unittest.TestCase):
    def test_creates_gitignore_on_first_run(self):
        with tempfile.TemporaryDirectory() as d:
            audits_dir = os.path.join(d, "audits")
            write_report(audits_dir, "2026-01-15", "# content\n")
            gi_path = os.path.join(audits_dir, ".gitignore")
            self.assertTrue(os.path.exists(gi_path))
            with open(gi_path, "r") as fh:
                content = fh.read()
            self.assertIn(".tmp-*.md", content)

    def test_does_not_clobber_existing_gitignore(self):
        with tempfile.TemporaryDirectory() as d:
            audits_dir = os.path.join(d, "audits")
            os.makedirs(audits_dir)
            gi_path = os.path.join(audits_dir, ".gitignore")
            existing_content = "# existing\n*.log\n"
            with open(gi_path, "w") as fh:
                fh.write(existing_content)

            write_report(audits_dir, "2026-01-15", "# report\n")
            with open(gi_path, "r") as fh:
                after = fh.read()
            self.assertEqual(after, existing_content)

    def test_atomic_write_produces_file(self):
        with tempfile.TemporaryDirectory() as d:
            audits_dir = os.path.join(d, "audits")
            content = "# Audit Report — 2026-01-15\n\nsome content\n"
            out_path = write_report(audits_dir, "2026-01-15", content)
            self.assertTrue(os.path.exists(out_path))
            with open(out_path, "r") as fh:
                written = fh.read()
            self.assertEqual(written, content)

    def test_returns_correct_path(self):
        with tempfile.TemporaryDirectory() as d:
            audits_dir = os.path.join(d, "audits")
            out_path = write_report(audits_dir, "2026-01-15", "x\n")
            self.assertTrue(out_path.endswith("2026-01-15-audit.md"))

    def test_collision_suffix_on_second_write(self):
        with tempfile.TemporaryDirectory() as d:
            audits_dir = os.path.join(d, "audits")
            p1 = write_report(audits_dir, "2026-01-15", "first\n")
            p2 = write_report(audits_dir, "2026-01-15", "second\n")
            self.assertNotEqual(p1, p2)
            self.assertIn("-2", p2)

    def test_no_tmp_files_left_after_write(self):
        with tempfile.TemporaryDirectory() as d:
            audits_dir = os.path.join(d, "audits")
            write_report(audits_dir, "2026-01-15", "content\n")
            # No .tmp-*.md files should remain
            import glob
            tmp_files = glob.glob(os.path.join(audits_dir, ".tmp-*.md"))
            self.assertEqual(tmp_files, [])


# ---------------------------------------------------------------------------
# ensure_gitignore
# ---------------------------------------------------------------------------

class TestEnsureGitignore(unittest.TestCase):
    def test_creates_gitignore(self):
        with tempfile.TemporaryDirectory() as d:
            ensure_gitignore(d)
            gi_path = os.path.join(d, ".gitignore")
            self.assertTrue(os.path.exists(gi_path))
            with open(gi_path, "r") as fh:
                self.assertIn(".tmp-*.md", fh.read())

    def test_idempotent_second_call(self):
        with tempfile.TemporaryDirectory() as d:
            ensure_gitignore(d)
            ensure_gitignore(d)  # second call should not raise
            gi_path = os.path.join(d, ".gitignore")
            self.assertTrue(os.path.exists(gi_path))

    def test_does_not_clobber_existing_content(self):
        with tempfile.TemporaryDirectory() as d:
            gi_path = os.path.join(d, ".gitignore")
            existing = "# do not touch me\n"
            with open(gi_path, "w") as fh:
                fh.write(existing)
            ensure_gitignore(d)
            with open(gi_path, "r") as fh:
                after = fh.read()
            self.assertEqual(after, existing)

    def test_creates_audits_dir_if_needed(self):
        with tempfile.TemporaryDirectory() as d:
            new_dir = os.path.join(d, "audits")
            self.assertFalse(os.path.exists(new_dir))
            ensure_gitignore(new_dir)
            self.assertTrue(os.path.isdir(new_dir))


# ---------------------------------------------------------------------------
# render_report — bucketing override: [CONSTITUTION-VIOLATION] beats agent
# ---------------------------------------------------------------------------

class TestRenderReportBucketingOverride(unittest.TestCase):
    """[CONSTITUTION-VIOLATION] tag must win over agent=="security-reviewer"."""

    def test_constitution_tag_wins_over_security_agent(self):
        # A security-reviewer finding tagged [CONSTITUTION-VIOLATION] must land
        # in Constitution Violations sub-group, NOT Security sub-group.
        f = _make_finding(
            agent="security-reviewer",
            severity="Critical",
            tags=["[CONSTITUTION-VIOLATION]"],
        )
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        report = render_report(rd)
        self.assertIn("#### Constitution Violations", report)
        self.assertNotIn("#### Security", report)


# ---------------------------------------------------------------------------
# render_report — category-driven bucketing (Step 2)
# ---------------------------------------------------------------------------

class TestRenderReportCategoryBucketing(unittest.TestCase):
    """Each declared category routes to the correct #### sub-group header."""

    def _render_single(self, category, severity="High", tags=None):
        """Render a report with one finding carrying the given category."""
        f = _make_finding(
            finding_id="F-001",
            severity=severity,
            tags=tags or [],
            category=category,
        )
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        return render_report(rd)

    def test_system_design_category_renders_under_system_design_subgroup(self):
        report = self._render_single("system_design")
        self.assertIn("#### System Design", report)
        self.assertNotIn("#### Mislogic", report)

    def test_best_practice_category_renders_under_best_practices_subgroup(self):
        report = self._render_single("best_practice")
        self.assertIn("#### Best Practices", report)
        self.assertNotIn("#### Mislogic", report)

    def test_duplication_category_renders_under_duplication_subgroup(self):
        report = self._render_single("duplication")
        self.assertIn("#### Duplication", report)
        self.assertNotIn("#### Mislogic", report)

    def test_security_category_renders_under_security_subgroup(self):
        report = self._render_single("security")
        self.assertIn("#### Security", report)
        self.assertNotIn("#### Mislogic", report)

    def test_mislogic_category_renders_under_mislogic_subgroup(self):
        report = self._render_single("mislogic")
        self.assertIn("#### Mislogic", report)

    def test_unknown_category_value_defaults_to_mislogic(self):
        # A present-but-unmapped category value falls back to mislogic
        report = self._render_single("future_unknown")
        self.assertIn("#### Mislogic", report)

    def test_blind_spot_category_shares_mislogic_bucket(self):
        # blind_spot is a category value but renders in the mislogic display bucket
        report = self._render_single("blind_spot")
        self.assertIn("#### Mislogic", report)
        # Must NOT create a new "#### Blind Spot" section
        self.assertNotIn("#### Blind Spot", report)

    def test_no_category_key_defaults_to_mislogic(self):
        # Backward-compat: a finding dict with no 'category' key at all still renders.
        f = _make_finding(finding_id="F-001", severity="High")
        # Ensure no 'category' key in the dict
        f.pop("category", None)
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        report = render_report(rd)
        self.assertIn("#### Mislogic", report)

    def test_constitution_tag_overrides_non_constitution_category(self):
        # A finding with [CONSTITUTION-VIOLATION] tag AND category:"system_design"
        # must still land in Constitution Violations (tag override wins).
        f = _make_finding(
            finding_id="F-001",
            severity="Critical",
            tags=["[CONSTITUTION-VIOLATION]"],
            category="system_design",
        )
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        report = render_report(rd)
        self.assertIn("#### Constitution Violations", report)
        self.assertNotIn("#### System Design", report)

    def test_architect_agent_with_mislogic_category_goes_to_mislogic(self):
        # Proves the agent-name heuristic is dead: an architect finding with
        # category:"mislogic" must appear in Mislogic sub-group, NOT System Design.
        f = _make_finding(
            finding_id="F-001",
            agent="architect",
            severity="High",
            tags=[],
            category="mislogic",
        )
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        report = render_report(rd)
        self.assertIn("#### Mislogic", report)
        self.assertNotIn("#### System Design", report)


# ---------------------------------------------------------------------------
# render_report — Not Audited section wording (Step 2)
# ---------------------------------------------------------------------------

class TestRenderReportNotAuditedWording(unittest.TestCase):
    """Not-Audited section must contain updated wording from Step 2."""

    def setUp(self):
        self.report = render_report(_make_report_dict())

    def test_ui_design_out_of_scope_line_present(self):
        self.assertIn("UI/design consistency (out of scope)", self.report)

    def test_performance_wording_updated(self):
        # New wording: runtime profiling out of scope, idiom smells are in scope
        self.assertIn(
            "Runtime performance profiling (out of scope — use /devforge:review); "
            "static performance-idiom smells are in scope",
            self.report,
        )

    def test_old_performance_wording_absent(self):
        # The old blanket "Performance (out of scope — use /review)" is gone
        self.assertNotIn("Performance (out of scope — use /review)", self.report)


# ---------------------------------------------------------------------------
# render_report — auto-assigned finding_id in Top-N ranking
# ---------------------------------------------------------------------------

class TestRenderReportAutoAssignedIdTopN(unittest.TestCase):
    """Auto-assignment: 1st finding -> F-001, 2nd -> F-002, etc.
    top10=["F-002","F-001"] means F-002 (2nd finding) ranks first.
    """

    def test_auto_assigned_id_maps_to_correct_finding_in_top10(self):
        # Two raw dicts WITHOUT finding_id — auto-assigned F-001 and F-002.
        first = {
            "agent": "code-reviewer",
            "severity": "Critical",
            "file": "a.py",
            "line": 1,
            "pattern": "issue A",
            "confidence": "Certain",
            "evidence": "code A",
            "why": "reason A",
            "remediation": "fix A",
            "tags": [],
        }
        second = {
            "agent": "code-reviewer",
            "severity": "High",
            "file": "b.py",
            "line": 2,
            "pattern": "issue B",
            "confidence": "Likely",
            "evidence": "code B",
            "why": "reason B",
            "remediation": "fix B",
            "tags": [],
        }
        # F-002 is second dict (b.py/High); it should appear as rank 1.
        rd = _make_report_dict(findings=[first, second], top10=["F-002", "F-001"])
        report = render_report(rd)
        # Rank 1 entry must reference b.py line 2 (the auto-assigned F-002).
        self.assertIn("1. [High] b.py:2", report)


# ---------------------------------------------------------------------------
# render_report — finding line format: line omitted when -1
# ---------------------------------------------------------------------------

class TestRenderReportFindingLineFormat(unittest.TestCase):
    """Finding bullet line format: severity inline, `:line` omitted if -1."""

    def test_line_present_when_valid(self):
        f = _make_finding(finding_id="F-001", severity="High", file="src/f.py", line=42)
        rd = _make_report_dict(findings=[f], top10=[])
        report = render_report(rd)
        # ":42" must appear in the finding bullet
        self.assertIn(":42", report)

    def test_line_omitted_when_minus_one(self):
        f = _make_finding(finding_id="F-001", severity="High", file="src/f.py", line=-1)
        rd = _make_report_dict(findings=[f], top10=[])
        report = render_report(rd)
        # ":-1" must NOT appear
        self.assertNotIn(":-1", report)

    def test_severity_inline_format(self):
        f = _make_finding(finding_id="F-001", severity="Critical", file="src/f.py", line=5)
        rd = _make_report_dict(findings=[f], top10=[])
        report = render_report(rd)
        # "[Critical]" must appear on the finding bullet line
        # (not under a ## Critical Findings header)
        self.assertIn("[Critical]", report)
        self.assertNotIn("## Critical Findings", report)


# ---------------------------------------------------------------------------
# render_report — Summary: Cross-agent consensus count from [CROSS-AGENT] tags
# ---------------------------------------------------------------------------

class TestRenderReportCrossAgentSummaryCount(unittest.TestCase):
    """Summary line 'Cross-agent consensus findings: N' must count
    findings whose tags list contains '[CROSS-AGENT]', not len(consensus).

    This is correct for both modes:
    - Multi-pass: consensus={} but merger tags findings with [CROSS-AGENT].
    - Single-pass: compute-consensus both populates consensus AND tags findings;
      the count of [CROSS-AGENT]-tagged findings equals len(consensus groups),
      so the displayed number is byte-identical to pre-fix output.
    """

    def _summary_line(self, report):
        # type: (str) -> str
        """Extract the Cross-agent consensus line from the Summary section."""
        for line in report.splitlines():
            if "Cross-agent consensus findings:" in line:
                return line
        self.fail("Cross-agent consensus findings line not found in report")
        return ""  # unreachable; satisfies type checker

    def test_multipass_no_consensus_dict_but_tagged_findings_shows_correct_count(self):
        """Multi-pass style: consensus={}, 3 of 5 findings tagged [CROSS-AGENT]."""
        findings = [
            _make_finding(finding_id="F-001", tags=["[CROSS-AGENT]"]),
            _make_finding(finding_id="F-002", tags=["[CROSS-AGENT]"]),
            _make_finding(finding_id="F-003", tags=["[CROSS-AGENT]"]),
            _make_finding(finding_id="F-004", tags=[]),
            _make_finding(finding_id="F-005", tags=[]),
        ]
        rd = _make_report_dict(findings=findings, top10=[])
        rd["consensus"] = {}  # empty — simulate multi-pass (no compute-consensus run)
        report = render_report(rd)
        line = self._summary_line(report)
        self.assertIn("3", line,
                      "Expected count 3 in line: {!r}".format(line))

    def test_multipass_was_showing_zero_before_fix_now_shows_correct_count(self):
        """Explicit regression: the old code returned 0 when consensus={}.
        This is the exact symptom reported (49 [CROSS-AGENT] findings, showed 0).
        """
        findings = [
            _make_finding(finding_id="F-{0:03d}".format(i), tags=["[CROSS-AGENT]"])
            for i in range(1, 6)
        ]
        rd = _make_report_dict(findings=findings, top10=[])
        rd["consensus"] = {}
        report = render_report(rd)
        line = self._summary_line(report)
        # Must NOT show 0 when [CROSS-AGENT]-tagged findings are present
        self.assertNotIn(": 0", line,
                         "Still showing 0 for [CROSS-AGENT]-tagged findings: {!r}".format(line))
        self.assertIn("5", line)

    def test_singlepass_count_unchanged_equals_consensus_group_count(self):
        """Single-pass style: consensus populated with K groups, same K findings
        tagged [CROSS-AGENT]. New count must equal K (byte-identical behaviour).
        """
        findings = [
            _make_finding(finding_id="F-001", tags=["[CROSS-AGENT]"]),
            _make_finding(finding_id="F-002", tags=["[CROSS-AGENT]"]),
            _make_finding(finding_id="F-003", tags=[]),
        ]
        rd = _make_report_dict(findings=findings, top10=[])
        # Two consensus groups (K=2), same two findings tagged [CROSS-AGENT]
        rd["consensus"] = {
            "F-001": ["code-reviewer", "architect"],
            "F-002": ["security-reviewer", "architect"],
        }
        report = render_report(rd)
        line = self._summary_line(report)
        self.assertIn(": 2", line,
                      "Expected count 2 (K=2 groups, K=2 tagged) in line: {!r}".format(line))

    def test_finding_without_cross_agent_tag_not_counted(self):
        """A finding with tags but no [CROSS-AGENT] must not be counted."""
        findings = [
            _make_finding(finding_id="F-001", tags=["[CONSTITUTION-VIOLATION]"]),
            _make_finding(finding_id="F-002", tags=["[SOME-OTHER-TAG]"]),
            _make_finding(finding_id="F-003", tags=[]),
        ]
        rd = _make_report_dict(findings=findings, top10=[])
        rd["consensus"] = {}
        report = render_report(rd)
        line = self._summary_line(report)
        self.assertIn(": 0", line,
                      "Expected count 0 for findings without [CROSS-AGENT]: {!r}".format(line))

    def test_zero_cross_agent_findings_shows_zero(self):
        """Zero [CROSS-AGENT] findings (no tags at all) shows 0."""
        findings = [
            _make_finding(finding_id="F-001", tags=[]),
            _make_finding(finding_id="F-002", tags=[]),
        ]
        rd = _make_report_dict(findings=findings, top10=[])
        rd["consensus"] = {}
        report = render_report(rd)
        line = self._summary_line(report)
        self.assertIn(": 0", line,
                      "Expected 0 in Summary line: {!r}".format(line))

    def test_zero_findings_shows_zero(self):
        """Empty findings list shows 0 (no crash on empty)."""
        rd = _make_report_dict(findings=[], top10=[])
        rd["consensus"] = {}
        report = render_report(rd)
        line = self._summary_line(report)
        self.assertIn(": 0", line,
                      "Expected 0 with no findings: {!r}".format(line))

    def test_existing_fixture_single_pass_count_is_one(self):
        """The standard _make_report_dict fixture has 1 [CROSS-AGENT] finding (F-002)
        and consensus={F-002: [...]}.  Old count was 1; new count must also be 1.
        Confirms the standard test fixture produces the same output as before the fix.
        """
        rd = _make_report_dict()  # F-002 has tags=["[CROSS-AGENT]"], consensus has F-002
        report = render_report(rd)
        line = self._summary_line(report)
        self.assertIn(": 1", line,
                      "Standard fixture: expected count 1 in line: {!r}".format(line))


# ---------------------------------------------------------------------------
# render_report — plan 19 Change D: confidence-gate presentation
# ---------------------------------------------------------------------------

class TestRenderReportContestatedTagInHeadline(unittest.TestCase):
    """[CONTESTED]-tagged findings render IN the headline (Top-N + Findings by File).

    Contested findings are part of the report_dict["findings"] headline set and
    render WITH the [CONTESTED] tag visible in the Top-N line (in tags_str).
    """

    def _make_contested_finding(self, finding_id="F-001"):
        """A finding already tagged [CONTESTED] (as apply_verdicts would produce)."""
        return {
            "finding_id": finding_id,
            "agent": "security-reviewer",
            "severity": "High",
            "file": "src/sec.py",
            "line": 5,
            "pattern": "contested security issue",
            "confidence": "Likely",
            "evidence": "unsafe_call()",
            "why": "Could not resolve security implication.",
            "remediation": "Review manually.",
            "category": "security",
            "tags": ["[CONTESTED]"],
        }

    def test_contested_finding_appears_in_findings_by_file(self):
        """[CONTESTED]-tagged finding renders in ## Findings by File."""
        f = self._make_contested_finding("F-001")
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        report = render_report(rd)
        # The finding's pattern should appear in Findings by File
        self.assertIn("contested security issue", report)
        fbf_pos = report.find("## Findings by File")
        self.assertGreater(fbf_pos, -1)
        fbf_section = report[fbf_pos:]
        self.assertIn("contested security issue", fbf_section)

    def test_contested_tag_appears_in_top_n_line(self):
        """[CONTESTED] tag appears in the Top-N entry for a contested finding."""
        f = self._make_contested_finding("F-001")
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        report = render_report(rd)
        # Find the Top-N section
        top_n_pos = report.find("## Top 10 Priorities")
        self.assertGreater(top_n_pos, -1)
        top_n_section = report[top_n_pos: report.find("## Findings by File")]
        self.assertIn("[CONTESTED]", top_n_section)

    def test_confirmed_and_contested_both_in_headline(self):
        """Both confirmed and [CONTESTED]-tagged findings appear in the headline."""
        confirmed = {
            "finding_id": "F-001",
            "agent": "code-reviewer",
            "severity": "Critical",
            "file": "src/a.py",
            "line": 1,
            "pattern": "confirmed issue",
            "confidence": "Certain",
            "evidence": "bad_code()",
            "why": "Clearly wrong.",
            "remediation": "Fix it.",
            "category": "mislogic",
            "tags": [],
            "verify_confidence": "confirmed",
        }
        contested = self._make_contested_finding("F-002")
        rd = _make_report_dict(findings=[confirmed, contested], top10=["F-001", "F-002"])
        report = render_report(rd)
        self.assertIn("confirmed issue", report)
        self.assertIn("contested security issue", report)


class TestRenderReportDismissedAppendix(unittest.TestCase):
    """Dismissed + uncertain findings render in '## Dismissed / Worth a Glance' appendix."""

    def _dismissed_finding(self, finding_id="D-001"):
        return {
            "finding_id": finding_id,
            "agent": "code-reviewer",
            "severity": "High",
            "file": "src/dis.py",
            "line": 10,
            "pattern": "dismissed pattern",
            "confidence": "Likely",
            "evidence": "fine_code()",
            "why": "No defect demonstrable.",
            "remediation": "N/A.",
            "category": "mislogic",
            "tags": [],
        }

    def _uncertain_finding(self, finding_id="U-001"):
        return {
            "finding_id": finding_id,
            "agent": "architect",
            "severity": "Medium",
            "file": "src/unc.py",
            "line": 20,
            "pattern": "uncertain pattern",
            "confidence": "Speculative",
            "evidence": "ambiguous_code()",
            "why": "Cannot resolve from code alone.",
            "remediation": "N/A.",
            "category": "system_design",
            "tags": [],
        }

    def test_appendix_section_rendered_when_dismissed_present(self):
        """## Dismissed / Worth a Glance renders when dismissed list is non-empty."""
        d = self._dismissed_finding()
        rd = _make_report_dict(findings=[], top10=[])
        rd["dismissed"] = [d]
        rd["uncertain"] = []
        report = render_report(rd)
        self.assertIn("## Dismissed / Worth a Glance", report)
        self.assertIn("dismissed pattern", report)

    def test_appendix_section_rendered_when_uncertain_present(self):
        """## Dismissed / Worth a Glance renders when uncertain list is non-empty."""
        u = self._uncertain_finding()
        rd = _make_report_dict(findings=[], top10=[])
        rd["dismissed"] = []
        rd["uncertain"] = [u]
        report = render_report(rd)
        self.assertIn("## Dismissed / Worth a Glance", report)
        self.assertIn("uncertain pattern", report)

    def test_appendix_omitted_when_both_empty(self):
        """## Dismissed / Worth a Glance is omitted when both dismissed and uncertain are empty."""
        rd = _make_report_dict(findings=[], top10=[])
        rd["dismissed"] = []
        rd["uncertain"] = []
        report = render_report(rd)
        self.assertNotIn("## Dismissed / Worth a Glance", report)

    def test_appendix_omitted_when_keys_absent(self):
        """## Dismissed / Worth a Glance is omitted when keys are not in report_dict."""
        rd = _make_report_dict(findings=[], top10=[])
        # Don't add dismissed/uncertain keys at all (backward compat with older report dicts)
        rd.pop("dismissed", None)
        rd.pop("uncertain", None)
        report = render_report(rd)
        self.assertNotIn("## Dismissed / Worth a Glance", report)

    def test_dismissed_not_in_findings_by_file(self):
        """Dismissed findings must NOT appear in ## Findings by File headline section."""
        d = self._dismissed_finding()
        rd = _make_report_dict(findings=[], top10=[])
        rd["dismissed"] = [d]
        rd["uncertain"] = []
        report = render_report(rd)
        fbf_pos = report.find("## Findings by File")
        dismissed_pos = report.find("## Dismissed / Worth a Glance")
        self.assertGreater(fbf_pos, -1)
        self.assertGreater(dismissed_pos, -1)
        # "## Findings by File" section should not contain the dismissed pattern
        fbf_section = report[fbf_pos:dismissed_pos]
        self.assertNotIn("dismissed pattern", fbf_section)

    def test_uncertain_not_in_top_n(self):
        """Uncertain findings must NOT appear in ## Top N Priorities."""
        u = self._uncertain_finding()
        rd = _make_report_dict(findings=[], top10=[])
        rd["dismissed"] = []
        rd["uncertain"] = [u]
        report = render_report(rd)
        top_n_pos = report.find("## Top 10 Priorities")
        self.assertGreater(top_n_pos, -1)
        # No top10 ids, so Top-N shows "(no findings)" — uncertain must not leak in
        top_n_section = report[top_n_pos:report.find("## Findings by File")]
        self.assertNotIn("uncertain pattern", top_n_section)

    def test_appendix_subsections_present(self):
        """Both ### Dismissed and ### Uncertain (low-stakes) subsections render."""
        rd = _make_report_dict(findings=[], top10=[])
        rd["dismissed"] = [self._dismissed_finding()]
        rd["uncertain"] = [self._uncertain_finding()]
        report = render_report(rd)
        self.assertIn("### Dismissed", report)
        self.assertIn("### Uncertain (low-stakes)", report)

    def test_appendix_section_position_after_findings_by_file(self):
        """## Dismissed / Worth a Glance section appears after ## Findings by File."""
        d = self._dismissed_finding()
        rd = _make_report_dict(findings=[], top10=[])
        rd["dismissed"] = [d]
        rd["uncertain"] = []
        report = render_report(rd)
        fbf_pos = report.find("## Findings by File")
        app_pos = report.find("## Dismissed / Worth a Glance")
        self.assertGreater(fbf_pos, -1)
        self.assertGreater(app_pos, -1)
        self.assertLess(fbf_pos, app_pos)


class TestRenderReportMethodologyUpdated(unittest.TestCase):
    """## Methodology text must reflect the new refutation model (plan 19 Change D)."""

    def setUp(self):
        self.report = render_report(_make_report_dict())

    def _methodology_section(self):
        pos = self.report.find("## Methodology")
        self.assertGreater(pos, -1, "## Methodology section not found")
        return self.report[pos:]

    def test_no_deliberate_bias_framing(self):
        """Old 'deliberate bias toward false positives' wording must be gone."""
        self.assertNotIn("deliberate bias toward false positives", self.report)

    def test_no_bias_toward_false_positives_framing(self):
        """'bias toward false positives over false negatives' must be gone."""
        self.assertNotIn("bias toward false positives over false negatives", self.report)

    def test_methodology_mentions_refutation(self):
        """New Methodology text must mention the refutation/cross-examination stage."""
        meth = self._methodology_section()
        self.assertIn("refutation", meth.lower())

    def test_methodology_mentions_confirmed(self):
        """New Methodology text must describe confirmed → headline routing."""
        meth = self._methodology_section()
        self.assertIn("confirmed", meth.lower())

    def test_methodology_mentions_dismissed_appendix(self):
        """New Methodology text must mention dismissed findings go to appendix."""
        meth = self._methodology_section()
        self.assertIn("appendix", meth.lower())

    def test_methodology_mentions_contested(self):
        """New Methodology text must mention [CONTESTED] (D7 high-stakes routing)."""
        meth = self._methodology_section()
        self.assertIn("[CONTESTED]", meth)

    def test_methodology_retains_speculative_note(self):
        """'Speculative' findings note must be retained in new Methodology."""
        meth = self._methodology_section()
        self.assertIn("Speculative", meth)

    def test_methodology_retains_verbatim_quote_note(self):
        """Verbatim-quote mention must be retained."""
        meth = self._methodology_section()
        self.assertIn("verbatim", meth.lower())


class TestRenderReportSummaryConfidenceCounts(unittest.TestCase):
    """## Summary must report confirmed/dismissed/uncertain/contested counts."""

    def _summary_section(self, report):
        pos = report.find("## Summary")
        self.assertGreater(pos, -1, "## Summary section not found")
        return report[pos:]

    def test_summary_counts_line_confirmed_dismissed_uncertain_contested(self):
        """Summary line 'Confirmed: N | Contested: N | Dismissed: N | Uncertain: N' present."""
        rd = _make_report_dict(findings=[], top10=[])
        rd["dismissed"] = []
        rd["uncertain"] = []
        report = render_report(rd)
        summary = self._summary_section(report)
        self.assertIn("Confirmed:", summary)
        self.assertIn("Contested:", summary)
        self.assertIn("Dismissed:", summary)
        self.assertIn("Uncertain:", summary)

    def test_confirmed_count_excludes_contested(self):
        """Confirmed count = headline findings minus [CONTESTED]-tagged findings."""
        f_confirmed = _make_finding(finding_id="F-001", tags=[])
        f_contested = _make_finding(finding_id="F-002", tags=["[CONTESTED]"])
        rd = _make_report_dict(findings=[f_confirmed, f_contested], top10=[])
        rd["dismissed"] = []
        rd["uncertain"] = []
        report = render_report(rd)
        summary = self._summary_section(report)
        # 1 confirmed (F-001), 1 contested (F-002)
        self.assertIn("Confirmed: 1", summary)
        self.assertIn("Contested: 1", summary)

    def test_dismissed_count_from_dismissed_list(self):
        """Dismissed count in Summary comes from report_dict['dismissed'] list length."""
        dismissed = [
            _make_finding(finding_id="D-001"),
            _make_finding(finding_id="D-002"),
        ]
        rd = _make_report_dict(findings=[], top10=[])
        rd["dismissed"] = dismissed
        rd["uncertain"] = []
        report = render_report(rd)
        summary = self._summary_section(report)
        self.assertIn("Dismissed: 2", summary)

    def test_uncertain_count_from_uncertain_list(self):
        """Uncertain count in Summary comes from report_dict['uncertain'] list length."""
        uncertain = [_make_finding(finding_id="U-001")]
        rd = _make_report_dict(findings=[], top10=[])
        rd["dismissed"] = []
        rd["uncertain"] = uncertain
        report = render_report(rd)
        summary = self._summary_section(report)
        self.assertIn("Uncertain: 1", summary)

    def test_all_zero_when_no_findings(self):
        """With no findings, all confidence counts are zero."""
        rd = _make_report_dict(findings=[], top10=[])
        rd["dismissed"] = []
        rd["uncertain"] = []
        report = render_report(rd)
        summary = self._summary_section(report)
        self.assertIn("Confirmed: 0", summary)
        self.assertIn("Contested: 0", summary)
        self.assertIn("Dismissed: 0", summary)
        self.assertIn("Uncertain: 0", summary)

    def test_backward_compat_keys_absent(self):
        """When dismissed/uncertain keys are absent, Summary counts default to 0."""
        rd = _make_report_dict(findings=[], top10=[])
        rd.pop("dismissed", None)
        rd.pop("uncertain", None)
        report = render_report(rd)
        summary = self._summary_section(report)
        self.assertIn("Dismissed: 0", summary)
        self.assertIn("Uncertain: 0", summary)


class TestRenderReportAllFourBucketsIntegration(unittest.TestCase):
    """F3: Full-integration test — all four buckets populated simultaneously.

    findings=[<confirmed>, <[CONTESTED]-tagged>] represents the confirmed ∪
    contested union passed to render_report via report_dict["findings"].
    dismissed and uncertain are passed via their own keys.

    Asserts:
      - confirmed + contested findings both appear in ## Findings by File
      - contested finding carries its [CONTESTED] tag visible in the report
      - dismissed finding appears in ## Dismissed / Worth a Glance
      - uncertain finding appears in ## Dismissed / Worth a Glance
      - dismissed finding does NOT appear in ## Findings by File
      - uncertain finding does NOT appear in ## Findings by File
    """

    def _confirmed_finding(self):
        return {
            "finding_id": "F-001",
            "agent": "code-reviewer",
            "severity": "Critical",
            "file": "src/core.py",
            "line": 10,
            "pattern": "confirmed-logic-bug",
            "confidence": "Certain",
            "evidence": "if x is None: pass  # swallowed",
            "why": "Swallowed None crashes downstream.",
            "remediation": "Raise ValueError.",
            "category": "mislogic",
            "tags": [],
            "verify_confidence": "confirmed",
        }

    def _contested_finding(self):
        return {
            "finding_id": "F-002",
            "agent": "security-reviewer",
            "severity": "High",
            "file": "src/auth.py",
            "line": 55,
            "pattern": "contested-security-issue",
            "confidence": "Likely",
            "evidence": "token = request.args.get('token')",
            "why": "Token not validated.",
            "remediation": "Validate token server-side.",
            "category": "security",
            "tags": ["[CONTESTED]"],
        }

    def _dismissed_finding(self):
        return {
            "finding_id": "D-001",
            "agent": "qa-reviewer",
            "severity": "Medium",
            "file": "src/util.py",
            "line": 30,
            "pattern": "dismissed-dead-branch",
            "confidence": "Speculative",
            "evidence": "if False: cleanup()",
            "why": "Appears dead.",
            "remediation": "Remove.",
            "category": "mislogic",
            "tags": [],
        }

    def _uncertain_finding(self):
        return {
            "finding_id": "U-001",
            "agent": "architect",
            "severity": "Low",
            "file": "src/svc.py",
            "line": 20,
            "pattern": "uncertain-coupling",
            "confidence": "Speculative",
            "evidence": "from db import session",
            "why": "Cannot determine scope without runtime trace.",
            "remediation": "N/A.",
            "category": "system_design",
            "tags": [],
        }

    def setUp(self):
        confirmed = self._confirmed_finding()
        contested = self._contested_finding()
        dismissed = self._dismissed_finding()
        uncertain = self._uncertain_finding()

        rd = _make_report_dict(
            findings=[confirmed, contested],
            top10=["F-001", "F-002"],
        )
        rd["dismissed"] = [dismissed]
        rd["uncertain"] = [uncertain]
        self.report = render_report(rd)

    def test_confirmed_finding_in_findings_by_file(self):
        fbf_start = self.report.find("## Findings by File")
        self.assertGreater(fbf_start, -1)
        fbf_end = self.report.find("\n## ", fbf_start + 1)
        fbf_section = self.report[fbf_start:fbf_end] if fbf_end > -1 else self.report[fbf_start:]
        self.assertIn("confirmed-logic-bug", fbf_section)

    def test_contested_finding_in_findings_by_file(self):
        fbf_start = self.report.find("## Findings by File")
        self.assertGreater(fbf_start, -1)
        fbf_end = self.report.find("\n## ", fbf_start + 1)
        fbf_section = self.report[fbf_start:fbf_end] if fbf_end > -1 else self.report[fbf_start:]
        self.assertIn("contested-security-issue", fbf_section)

    def test_contested_tag_visible_in_report(self):
        # [CONTESTED] tag must appear somewhere in the report (Top-N or Findings by File)
        self.assertIn("[CONTESTED]", self.report)

    def test_dismissed_in_appendix_not_in_findings_by_file(self):
        fbf_start = self.report.find("## Findings by File")
        appendix_start = self.report.find("## Dismissed / Worth a Glance")
        self.assertGreater(fbf_start, -1)
        self.assertGreater(appendix_start, -1)
        # Dismissed pattern appears in appendix
        self.assertIn("dismissed-dead-branch", self.report[appendix_start:])
        # Dismissed pattern does NOT appear before the appendix section
        self.assertNotIn("dismissed-dead-branch", self.report[:appendix_start])

    def test_uncertain_in_appendix_not_in_findings_by_file(self):
        fbf_start = self.report.find("## Findings by File")
        appendix_start = self.report.find("## Dismissed / Worth a Glance")
        self.assertGreater(fbf_start, -1)
        self.assertGreater(appendix_start, -1)
        # Uncertain pattern appears in appendix
        self.assertIn("uncertain-coupling", self.report[appendix_start:])
        # Uncertain pattern does NOT appear before the appendix section
        self.assertNotIn("uncertain-coupling", self.report[:appendix_start])

    def test_appendix_present_with_both_subsections(self):
        self.assertIn("## Dismissed / Worth a Glance", self.report)
        self.assertIn("### Dismissed", self.report)
        self.assertIn("### Uncertain (low-stakes)", self.report)


# ---------------------------------------------------------------------------
# render_report — merged_count annotation (dedup visibility)
# ---------------------------------------------------------------------------

class TestRenderReportMergedCount(unittest.TestCase):
    """merged_count > 1 renders '(raised by N)' in Findings by File and Top-N.

    Backward-compat contract:
      - merged_count == 1  -> NO annotation
      - merged_count absent -> NO annotation (byte-identical to pre-change output)
      - merged_count == 0  -> NO annotation (not a real dedup count)
      - merged_count not an int -> NO annotation
    """

    def _render_single_finding(self, **overrides):
        """Render a report with exactly one finding; return (report_str, finding_id)."""
        f = _make_finding(finding_id="F-001", **overrides)
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        return render_report(rd), "F-001"

    # -- Findings by File section -------------------------------------------

    def test_merged_count_3_annotates_description_line_in_findings_by_file(self):
        """merged_count=3 appends '(raised by 3)' on the finding bullet in Findings by File."""
        report, _ = self._render_single_finding(merged_count=3)

        fbf_pos = report.find("## Findings by File")
        self.assertGreater(fbf_pos, -1)
        fbf_section = report[fbf_pos:]

        # The annotation must appear in the Findings by File section
        self.assertIn("(raised by 3)", fbf_section)

    def test_merged_count_3_annotation_on_same_line_as_pattern(self):
        """The '(raised by N)' token appears on the same bullet line as the pattern."""
        f = _make_finding(
            finding_id="F-001",
            pattern="deduped finding pattern",
            merged_count=3,
        )
        rd = _make_report_dict(findings=[f], top10=[])
        report = render_report(rd)

        # Find the specific bullet line
        for line in report.splitlines():
            if "deduped finding pattern" in line:
                # The annotation must be on the SAME line
                self.assertIn("(raised by 3)", line,
                              "annotation not on the same line as pattern: {!r}".format(line))
                return
        self.fail("Pattern line not found in report")

    def test_merged_count_1_no_annotation_in_findings_by_file(self):
        """merged_count=1 renders NO '(raised by ...)' annotation."""
        report, _ = self._render_single_finding(merged_count=1)
        self.assertNotIn("raised by", report)

    def test_merged_count_absent_no_annotation_backward_compat(self):
        """No merged_count key renders NO annotation (backward-compatible)."""
        f = _make_finding(finding_id="F-001")
        f.pop("merged_count", None)  # ensure absent
        rd = _make_report_dict(findings=[f], top10=[])
        report = render_report(rd)
        self.assertNotIn("raised by", report)

    def test_merged_count_absent_is_byte_identical_to_merged_count_1(self):
        """A finding with no merged_count key and one with merged_count=1 produce
        identical output (both are the no-dedup case)."""
        f_no_key = _make_finding(finding_id="F-001")
        f_no_key.pop("merged_count", None)

        f_count_1 = _make_finding(finding_id="F-001", merged_count=1)

        rd_no_key = _make_report_dict(findings=[f_no_key], top10=[])
        rd_count_1 = _make_report_dict(findings=[f_count_1], top10=[])

        report_no_key = render_report(rd_no_key)
        report_count_1 = render_report(rd_count_1)

        self.assertEqual(report_no_key, report_count_1,
                         "Reports differ: no merged_count key vs merged_count=1")

    def test_merged_count_zero_no_annotation(self):
        """merged_count=0 renders no annotation (guard against invalid sentinel)."""
        report, _ = self._render_single_finding(merged_count=0)
        self.assertNotIn("raised by", report)

    def test_merged_count_non_int_no_annotation(self):
        """merged_count as a string renders no annotation (type guard)."""
        report, _ = self._render_single_finding(merged_count="3")
        self.assertNotIn("raised by", report)

    def test_merged_count_bool_true_no_annotation(self):
        """merged_count=True (bool) renders no annotation (bool is subclass of int;
        must be explicitly excluded to avoid '(raised by True)' output)."""
        report, _ = self._render_single_finding(merged_count=True)
        self.assertNotIn("raised by", report)

    # -- Top-N section -------------------------------------------------------

    def test_merged_count_3_annotates_top_n_entry(self):
        """merged_count=3 appends '(raised by 3)' on the Top-N entry line."""
        f = _make_finding(
            finding_id="F-001",
            pattern="top-n deduped pattern",
            merged_count=3,
        )
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        report = render_report(rd)

        top_n_pos = report.find("## Top 10 Priorities")
        self.assertGreater(top_n_pos, -1)
        fbf_pos = report.find("## Findings by File")
        top_n_section = report[top_n_pos:fbf_pos]

        self.assertIn("(raised by 3)", top_n_section,
                      "annotation missing from Top-N section")

    def test_merged_count_1_no_annotation_in_top_n(self):
        """merged_count=1 renders NO annotation in Top-N."""
        f = _make_finding(finding_id="F-001", merged_count=1)
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        report = render_report(rd)

        top_n_pos = report.find("## Top 10 Priorities")
        fbf_pos = report.find("## Findings by File")
        top_n_section = report[top_n_pos:fbf_pos]

        self.assertNotIn("raised by", top_n_section)

    def test_merged_count_absent_no_annotation_in_top_n(self):
        """No merged_count key renders NO annotation in Top-N."""
        f = _make_finding(finding_id="F-001")
        f.pop("merged_count", None)
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        report = render_report(rd)

        top_n_pos = report.find("## Top 10 Priorities")
        fbf_pos = report.find("## Findings by File")
        top_n_section = report[top_n_pos:fbf_pos]

        self.assertNotIn("raised by", top_n_section)

    # -- Both sections present simultaneously --------------------------------

    def test_merged_count_3_annotates_both_sections(self):
        """merged_count=3 appears in BOTH Findings by File AND Top-N."""
        f = _make_finding(
            finding_id="F-001",
            pattern="both-sections pattern",
            merged_count=3,
        )
        rd = _make_report_dict(findings=[f], top10=["F-001"])
        report = render_report(rd)

        top_n_pos = report.find("## Top 10 Priorities")
        fbf_pos = report.find("## Findings by File")
        self.assertGreater(top_n_pos, -1)
        self.assertGreater(fbf_pos, -1)

        top_n_section = report[top_n_pos:fbf_pos]
        fbf_section = report[fbf_pos:]

        self.assertIn("(raised by 3)", top_n_section,
                      "annotation missing from Top-N section")
        self.assertIn("(raised by 3)", fbf_section,
                      "annotation missing from Findings by File section")

    # -- Mixed: some findings deduped, some not ------------------------------

    def test_only_deduped_finding_gets_annotation(self):
        """In a mixed report, only the finding with merged_count > 1 gets the annotation."""
        f_merged = _make_finding(
            finding_id="F-001",
            pattern="deduped-pattern",
            merged_count=4,
        )
        f_single = _make_finding(
            finding_id="F-002",
            pattern="single-pattern",
            # no merged_count key
        )
        f_single.pop("merged_count", None)

        rd = _make_report_dict(findings=[f_merged, f_single], top10=["F-001", "F-002"])
        report = render_report(rd)

        # The merged finding gets the annotation
        self.assertIn("(raised by 4)", report)

        # Check per-line: single-pattern line must NOT have the annotation
        for line in report.splitlines():
            if "single-pattern" in line:
                self.assertNotIn("raised by", line,
                                 "single finding line has unexpected annotation: {!r}".format(line))

    # -- No data mutation ----------------------------------------------------

    def test_render_does_not_mutate_finding(self):
        """render_report must not mutate the finding dict (read-only contract)."""
        f = _make_finding(finding_id="F-001", merged_count=3)
        original_keys = set(f.keys())
        original_mc = f["merged_count"]

        rd = _make_report_dict(findings=[f], top10=["F-001"])
        render_report(rd)

        self.assertEqual(f["merged_count"], original_mc,
                         "merged_count was mutated during render")
        self.assertEqual(set(f.keys()), original_keys,
                         "finding dict keys changed during render")


if __name__ == "__main__":
    unittest.main()
