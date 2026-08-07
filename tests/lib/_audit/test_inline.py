"""Tests for src/devforge/lib/_audit/_inline.py.

Coverage:
  render_inline_summary — ## Audit Complete header present;
                           count-first line (Findings: N Critical ...) present;
                           Top 5 names present;
                           agents-skipped rendered / "none" when empty;
                           discarded count + verbatim-quote-failures called out;
                           report path present;
                           "Not committed" note present;
                           adversarial NOTE present;
                           empty findings no crash;
                           top_ids < 5 renders correctly.
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit._inline import render_inline_summary  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_findings(count=5):
    findings = []
    severities = ["Critical", "Critical", "High", "High", "Medium"]
    for i in range(count):
        sev = severities[i] if i < len(severities) else "Info"
        findings.append({
            "finding_id": "F-{0:03d}".format(i + 1),
            "agent": "code-reviewer",
            "severity": sev,
            "file": "src/module{0}.py".format(i + 1),
            "line": (i + 1) * 10,
            "pattern": "critical issue {0}".format(i + 1),
            "confidence": "Certain",
            "evidence": "code snippet {0}".format(i + 1),
            "why": "Why it is wrong {0}".format(i + 1),
            "remediation": "Fix it {0}".format(i + 1),
            "tags": [],
        })
    return findings


def _make_report_dict(
    mode="broad",
    agents_skipped=None,
    discard_counts=None,
    findings=None,
    top10=None,
    out_path="audits/2026-01-15-audit.md",
):
    if agents_skipped is None:
        agents_skipped = ["qa-engineer"]
    if discard_counts is None:
        discard_counts = {
            "file_missing": 1,
            "line_oob": 0,
            "quote_mismatch": 4,
            "evidence_empty": 0,
            "pattern_missing": 1,
        }
    if findings is None:
        findings = _make_findings(5)
    if top10 is None:
        top10 = ["F-001", "F-002", "F-003", "F-004", "F-005"]

    return {
        "mode": mode,
        "scope_description": "full codebase",
        "findings": findings,
        "top10": top10,
        "agents_run": ["code-reviewer", "architect"],
        "agents_skipped": agents_skipped,
        "discard_counts": discard_counts,
        "consensus": {
            "F-001": ["code-reviewer", "architect"],
        },
        "recurring_unresolved": [
            "specs/001-auth/review.md | null check bypass | STILL PRESENT",
        ],
        "out_path": out_path,
    }


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

class TestInlineSummaryStructure(unittest.TestCase):
    def setUp(self):
        self.summary = render_inline_summary(_make_report_dict())

    def test_audit_complete_header(self):
        self.assertIn("## Audit Complete", self.summary)

    def test_scope_line_present(self):
        self.assertIn("**Scope**: full codebase", self.summary)

    def test_top_5_section_header(self):
        self.assertIn("### Top 5 Priorities", self.summary)

    def test_not_committed_note(self):
        self.assertIn("Not committed", self.summary)

    def test_adversarial_note_present(self):
        self.assertIn("NOTE: /devforge:audit is adversarial", self.summary)

    def test_adversarial_note_mentions_verbatim_grounding(self):
        # The NOTE now describes the grounding + cross-examination model instead
        # of the old "bias toward false positives" framing (plan 19 Change D).
        self.assertIn("verbatim", self.summary)

    def test_adversarial_note_mentions_speculative(self):
        self.assertIn("Speculative", self.summary)


# ---------------------------------------------------------------------------
# Count-first discipline (CLAUDE.md audit format)
# ---------------------------------------------------------------------------

class TestInlineSummaryCountFirst(unittest.TestCase):
    def test_findings_count_line_present(self):
        summary = render_inline_summary(_make_report_dict())
        # Must have: **Findings**: N Critical, N High, N Medium, N Info
        self.assertIn("**Findings**:", summary)

    def test_findings_count_correct(self):
        # 2 Critical, 2 High, 1 Medium from _make_findings(5)
        summary = render_inline_summary(_make_report_dict())
        self.assertIn("2 Critical", summary)
        self.assertIn("2 High", summary)
        self.assertIn("1 Medium", summary)
        self.assertIn("0 Info", summary)

    def test_findings_count_line_before_top5(self):
        summary = render_inline_summary(_make_report_dict())
        findings_pos = summary.find("**Findings**:")
        top5_pos = summary.find("### Top 5 Priorities")
        self.assertGreater(findings_pos, -1)
        self.assertGreater(top5_pos, -1)
        self.assertLess(findings_pos, top5_pos)

    def test_cross_agent_consensus_line_present(self):
        summary = render_inline_summary(_make_report_dict())
        self.assertIn("**Cross-agent consensus**: 1", summary)

    def test_recurring_unresolved_count_present(self):
        summary = render_inline_summary(_make_report_dict())
        self.assertIn("**Recurring (unresolved)**: 1", summary)


# ---------------------------------------------------------------------------
# Top 5 priorities
# ---------------------------------------------------------------------------

class TestInlineSummaryTop5(unittest.TestCase):
    def test_top5_entries_present(self):
        summary = render_inline_summary(_make_report_dict())
        # All 5 finding descriptions should appear
        for i in range(1, 6):
            self.assertIn(
                "critical issue {0}".format(i), summary,
                "Missing top-5 entry for F-{0:03d}".format(i),
            )

    def test_top5_uses_finding_description(self):
        summary = render_inline_summary(_make_report_dict())
        self.assertIn("critical issue 1", summary)

    def test_top5_includes_file_location(self):
        summary = render_inline_summary(_make_report_dict())
        self.assertIn("src/module1.py:10", summary)

    def test_top5_ranked_1_to_5(self):
        summary = render_inline_summary(_make_report_dict())
        self.assertIn("1. ", summary)
        self.assertIn("5. ", summary)

    def test_top5_does_not_show_6th_entry(self):
        # Even if top10 has 10 IDs, inline shows only 5
        findings = _make_findings(10)
        top10 = ["F-{0:03d}".format(i + 1) for i in range(10)]
        summary = render_inline_summary(
            _make_report_dict(findings=findings, top10=top10)
        )
        # Find the Top 5 Priorities section
        start = summary.find("### Top 5 Priorities")
        end = summary.find("\n\n", start + 1)
        if end == -1:
            end = len(summary)
        section = summary[start:end]
        self.assertNotIn("6. ", section)


# ---------------------------------------------------------------------------
# Agents skipped
# ---------------------------------------------------------------------------

class TestInlineSummaryAgentsSkipped(unittest.TestCase):
    def test_agents_skipped_listed(self):
        summary = render_inline_summary(_make_report_dict())
        self.assertIn("**Agents skipped**: qa-engineer", summary)

    def test_agents_skipped_none_when_empty(self):
        summary = render_inline_summary(
            _make_report_dict(agents_skipped=[])
        )
        self.assertIn("**Agents skipped**: none", summary)

    def test_multiple_skipped_agents(self):
        summary = render_inline_summary(
            _make_report_dict(agents_skipped=["qa-engineer", "architect"])
        )
        self.assertIn("qa-engineer", summary)
        self.assertIn("architect", summary)


# ---------------------------------------------------------------------------
# Discard counts
# ---------------------------------------------------------------------------

class TestInlineSummaryDiscardCounts(unittest.TestCase):
    def test_discarded_total_present(self):
        # 1+0+4+0+1 = 6 total
        summary = render_inline_summary(_make_report_dict())
        self.assertIn("6", summary)
        self.assertIn("**Findings discarded by validation**:", summary)

    def test_verbatim_quote_failures_called_out(self):
        summary = render_inline_summary(_make_report_dict())
        self.assertIn("verbatim-quote failures: 4", summary)

    def test_zero_discarded(self):
        dc = {
            "file_missing": 0, "line_oob": 0,
            "quote_mismatch": 0, "evidence_empty": 0, "pattern_missing": 0,
        }
        summary = render_inline_summary(_make_report_dict(discard_counts=dc))
        self.assertIn("verbatim-quote failures: 0", summary)


# ---------------------------------------------------------------------------
# Report path
# ---------------------------------------------------------------------------

class TestInlineSummaryReportPath(unittest.TestCase):
    def test_report_path_present(self):
        summary = render_inline_summary(_make_report_dict())
        self.assertIn("audits/2026-01-15-audit.md", summary)

    def test_full_report_label(self):
        summary = render_inline_summary(_make_report_dict())
        self.assertIn("Full report:", summary)

    def test_no_report_path_when_empty(self):
        summary = render_inline_summary(_make_report_dict(out_path=""))
        self.assertNotIn("Full report:", summary)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestInlineSummaryEdgeCases(unittest.TestCase):
    def test_empty_findings_no_crash(self):
        summary = render_inline_summary(
            _make_report_dict(findings=[], top10=[])
        )
        self.assertIn("## Audit Complete", summary)
        self.assertIn("0 Critical", summary)

    def test_fewer_than_5_top_ids(self):
        # Only 2 findings in top10
        findings = _make_findings(2)
        top10 = ["F-001", "F-002"]
        summary = render_inline_summary(
            _make_report_dict(findings=findings, top10=top10)
        )
        self.assertIn("1. ", summary)
        self.assertIn("2. ", summary)
        # No 3rd entry
        top5_start = summary.find("### Top 5 Priorities")
        top5_end = summary.find("\n\n", top5_start + 1)
        section = summary[top5_start:top5_end if top5_end != -1 else len(summary)]
        self.assertNotIn("3. ", section)

    def test_missing_fields_no_crash(self):
        # Minimal dict — only required structure
        summary = render_inline_summary({})
        self.assertIn("## Audit Complete", summary)
        self.assertIn("NOTE: /devforge:audit is adversarial", summary)


# ---------------------------------------------------------------------------
# Auto-assigned finding_id consistency between report and inline
# ---------------------------------------------------------------------------

class TestInlineSummaryAutoAssignedId(unittest.TestCase):
    """render_inline_summary must assign finding_ids identically to render_report.

    Convention: 1st finding in the list -> F-001, 2nd -> F-002, etc.
    top10/top5 referencing F-002 must resolve to the 2nd finding in the list.
    """

    def test_auto_assigned_id_maps_to_correct_finding_in_top5(self):
        # Two raw dicts WITHOUT finding_id.
        # Auto-assign: first -> F-001 (a.py), second -> F-002 (b.py).
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
        # F-002 is second dict (b.py/High); it should be rank 1 in Top-5.
        rd = _make_report_dict(
            findings=[first, second],
            top10=["F-002", "F-001"],
        )
        summary = render_inline_summary(rd)
        # Rank 1 entry must reference b.py line 2 (the auto-assigned F-002).
        self.assertIn("1. [High] b.py:2", summary)


# ---------------------------------------------------------------------------
# Confidence-gate counts (plan 19 Change D / Edit 3)
# ---------------------------------------------------------------------------

class TestInlineConfidenceCounts(unittest.TestCase):
    """The inline block must report confirmed / contested / dismissed / uncertain counts."""

    def _make_report_with_confidence(
        self,
        headline_findings=None,
        dismissed=None,
        uncertain=None,
    ):
        """Build a report_dict with the given headline/dismissed/uncertain splits."""
        if headline_findings is None:
            headline_findings = []
        if dismissed is None:
            dismissed = []
        if uncertain is None:
            uncertain = []
        rd = _make_report_dict(findings=headline_findings, top10=[])
        rd["dismissed"] = dismissed
        rd["uncertain"] = uncertain
        return rd

    def test_confirmed_count_line_present(self):
        """**Confirmed**: N line is present in the inline block."""
        rd = self._make_report_with_confidence(
            headline_findings=_make_findings(2),
        )
        summary = render_inline_summary(rd)
        self.assertIn("**Confirmed**:", summary)

    def test_contested_count_line_present(self):
        """**Contested**: N line is present in the inline block."""
        rd = self._make_report_with_confidence()
        summary = render_inline_summary(rd)
        self.assertIn("**Contested**:", summary)

    def test_dismissed_count_line_present(self):
        """**Dismissed**: N line is present in the inline block."""
        rd = self._make_report_with_confidence()
        summary = render_inline_summary(rd)
        self.assertIn("**Dismissed**:", summary)

    def test_uncertain_count_line_present(self):
        """**Uncertain**: N line is present in the inline block."""
        rd = self._make_report_with_confidence()
        summary = render_inline_summary(rd)
        self.assertIn("**Uncertain**:", summary)

    def test_all_four_counts_on_same_line(self):
        """All four confidence counts appear on a single line (| separated)."""
        rd = self._make_report_with_confidence()
        summary = render_inline_summary(rd)
        for line in summary.splitlines():
            if "**Confirmed**:" in line and "**Contested**:" in line:
                self.assertIn("**Dismissed**:", line)
                self.assertIn("**Uncertain**:", line)
                return
        self.fail("Confidence counts not found on a single line in:\n" + summary)

    def test_confirmed_count_correct(self):
        """Confirmed count = headline findings minus [CONTESTED]-tagged findings."""
        # 3 headline findings: 2 without [CONTESTED], 1 with [CONTESTED]
        f1 = {
            "finding_id": "F-001", "agent": "code-reviewer", "severity": "High",
            "file": "src/a.py", "line": 1, "pattern": "P1", "confidence": "Certain",
            "evidence": "e1", "why": "w1", "remediation": "r1",
            "category": "mislogic", "tags": [],
        }
        f2 = dict(f1, finding_id="F-002", tags=[])
        f3 = dict(f1, finding_id="F-003", tags=["[CONTESTED]"])
        rd = self._make_report_with_confidence(headline_findings=[f1, f2, f3])
        summary = render_inline_summary(rd)
        self.assertIn("**Confirmed**: 2", summary)
        self.assertIn("**Contested**: 1", summary)

    def test_dismissed_count_correct(self):
        """Dismissed count = len(dismissed list)."""
        dismissed = [
            {"finding_id": "D-001", "agent": "code-reviewer", "severity": "High",
             "file": "src/d.py", "line": 1, "pattern": "P_dis", "confidence": "Likely",
             "evidence": "e", "why": "w", "remediation": "r", "category": "mislogic", "tags": []},
            {"finding_id": "D-002", "agent": "code-reviewer", "severity": "Medium",
             "file": "src/e.py", "line": 2, "pattern": "P_dis2", "confidence": "Likely",
             "evidence": "e", "why": "w", "remediation": "r", "category": "mislogic", "tags": []},
        ]
        rd = self._make_report_with_confidence(dismissed=dismissed)
        summary = render_inline_summary(rd)
        self.assertIn("**Dismissed**: 2", summary)

    def test_uncertain_count_correct(self):
        """Uncertain count = len(uncertain list)."""
        uncertain = [
            {"finding_id": "U-001", "agent": "architect", "severity": "Medium",
             "file": "src/u.py", "line": 5, "pattern": "P_unc", "confidence": "Speculative",
             "evidence": "e", "why": "w", "remediation": "r", "category": "system_design", "tags": []},
        ]
        rd = self._make_report_with_confidence(uncertain=uncertain)
        summary = render_inline_summary(rd)
        self.assertIn("**Uncertain**: 1", summary)

    def test_all_zero_when_empty(self):
        """All four confidence counts are zero when findings/dismissed/uncertain are empty."""
        rd = self._make_report_with_confidence()
        summary = render_inline_summary(rd)
        self.assertIn("**Confirmed**: 0", summary)
        self.assertIn("**Contested**: 0", summary)
        self.assertIn("**Dismissed**: 0", summary)
        self.assertIn("**Uncertain**: 0", summary)

    def test_backward_compat_absent_keys(self):
        """When dismissed/uncertain keys absent, counts default to 0 (no crash)."""
        rd = _make_report_dict()
        rd.pop("dismissed", None)
        rd.pop("uncertain", None)
        summary = render_inline_summary(rd)
        self.assertIn("**Dismissed**: 0", summary)
        self.assertIn("**Uncertain**: 0", summary)

    def test_confidence_count_line_before_top5(self):
        """Confidence count line appears before ### Top 5 Priorities."""
        rd = self._make_report_with_confidence()
        summary = render_inline_summary(rd)
        confirmed_pos = summary.find("**Confirmed**:")
        top5_pos = summary.find("### Top 5 Priorities")
        self.assertGreater(confirmed_pos, -1)
        self.assertGreater(top5_pos, -1)
        self.assertLess(confirmed_pos, top5_pos)


class TestInlineNoteUpdated(unittest.TestCase):
    """NOTE in inline block reflects new grounding model (not 'bias toward FP')."""

    def setUp(self):
        self.summary = render_inline_summary(_make_report_dict())

    def test_no_bias_toward_false_positives_in_note(self):
        """'biases toward false positives over false negatives' must not appear in NOTE."""
        self.assertNotIn("biases toward false positives over false", self.summary)

    def test_note_mentions_verbatim(self):
        """NOTE must mention verbatim grounding."""
        self.assertIn("verbatim", self.summary)

    def test_note_mentions_speculative(self):
        """NOTE must retain the 'Speculative' findings caveat."""
        self.assertIn("Speculative", self.summary)

    def test_adversarial_note_still_present(self):
        """NOTE: /devforge:audit is adversarial line must still be present."""
        self.assertIn("NOTE: /devforge:audit is adversarial", self.summary)


if __name__ == "__main__":
    unittest.main()
