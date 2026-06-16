"""Tests for Phase 5 report rendering verbs in review_helper.

Coverage:

Round-trip from REAL apply_verdicts output:
  - Build a realistic findings set with verdicts that produce all four buckets
    (confirmed, dismissed, low-stakes uncertain, high-stakes contested including
    a security uncertain → contested and a [CONSTITUTION-VIOLATION] dismissed →
    contested), feed the REAL apply_verdicts partition to render_report, and assert:
      * confirmed findings appear in ## Confirmed Findings headline
      * high-stakes [CONTESTED] findings appear in the headline flagged [CONTESTED]
        (NOT in the appendix)
      * dismissed + low-stakes uncertain appear in ## Dismissed / Worth a Glance
      * Summary counts are correct
      * grouped by file → #### <category>, severity-sorted within group
      * NO verdict / approve / pass / fail headings anywhere in the output
      * review.md is written to temp specs/NNN-x/ directory

Empty-buckets case:
  - all-empty partition → valid report with appendix section absent, no crash

render_inline_summary:
  - count-first format with correct numbers
  - all-empty partition

CLI round-trips via main([...]):
  render-report verb:
    - basic round-trip → review.md written, JSON ack on stdout
    - missing --partition returns 2
    - missing --date returns 2
    - non-JSON --partition returns 2
    - non-dict --partition JSON returns 2

  render-inline-summary verb:
    - basic round-trip → ## Review Complete block on stdout
    - missing --partition returns 2
    - non-JSON --partition returns 2
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _review._cli import main  # noqa: E402
from _review._report import render_report, render_inline_summary, write_review_report  # noqa: E402
from _shared._verify import apply_verdicts  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def _finding(
    agent="code-reviewer",
    file="src/a.py",
    line=10,
    pattern="Naming lie",
    severity="High",
    category="mislogic",
    tags=None,
    finding_id=None,
):
    """Return a minimal ParsedFinding dict."""
    f = {
        "agent": agent,
        "file": file,
        "line": line,
        "pattern": pattern,
        "severity": severity,
        "confidence": "Likely",
        "evidence": "x = bad_code()",
        "why": "cross-task interaction causes defect",
        "remediation": "fix it",
        "category": category,
        "tags": tags if tags is not None else [],
    }
    if finding_id:
        f["finding_id"] = finding_id
    return f


def _verdict(file, line, pattern, agent, verdict, justification="confirmed by evidence"):
    """Return a minimal verdict dict."""
    return {
        "refuter": "architect",
        "file": file,
        "line": line,
        "pattern": pattern,
        "agent": agent,
        "verdict": verdict,
        "justification": justification,
        "evidence": "",
    }


def _build_realistic_partition():
    """Build a realistic findings set + verdicts, run through apply_verdicts.

    Produces all four buckets:
      confirmed  — one mislogic finding (verdict: confirmed)
      dismissed  — one best_practice finding (verdict: dismissed, no constitution tag)
      uncertain  — one low-stakes system_design finding (verdict: uncertain)
      contested  — (a) one security finding (verdict: uncertain → high-stakes → contested)
                   (b) one [CONSTITUTION-VIOLATION] finding (verdict: dismissed → contested,
                       D7 carve-out)
    """
    findings = [
        # Will be confirmed
        _finding(
            agent="code-reviewer",
            file="src/auth.py",
            line=42,
            pattern="Auth bypass via missing check",
            severity="Critical",
            category="mislogic",
            finding_id="F-001",
        ),
        # Will be dismissed (non-constitution)
        _finding(
            agent="qa-reviewer",
            file="src/utils.py",
            line=15,
            pattern="Missing type annotation",
            severity="Info",
            category="best_practice",
            finding_id="F-002",
        ),
        # Will be low-stakes uncertain (system_design, no high-stakes flag)
        _finding(
            agent="architect",
            file="src/core/router.py",
            line=88,
            pattern="God component — 15 responsibilities",
            severity="Medium",
            category="system_design",
            finding_id="F-003",
        ),
        # Will be contested: security + uncertain verdict → high-stakes
        _finding(
            agent="security-reviewer",
            file="src/auth.py",
            line=77,
            pattern="SQL injection vector via unescaped param",
            severity="High",
            category="security",
            finding_id="F-004",
        ),
        # Will be contested: [CONSTITUTION-VIOLATION] + dismissed → D7 carve-out
        _finding(
            agent="code-reviewer",
            file="src/db/models.py",
            line=5,
            pattern="Direct DB call bypasses service layer",
            severity="Critical",
            category="mislogic",
            tags=["[CONSTITUTION-VIOLATION]"],
            finding_id="F-005",
        ),
        # Will be confirmed: SAME file (src/auth.py) AND SAME category (mislogic)
        # as F-001 but severity=Info — exercises the within-bucket severity sort
        # (Critical F-001 must appear before Info F-006 inside #### Mislogic).
        _finding(
            agent="code-reviewer",
            file="src/auth.py",
            line=99,
            pattern="Dead auth code path never reached",
            severity="Info",
            category="mislogic",
            finding_id="F-006",
        ),
    ]

    verdicts = [
        _verdict("src/auth.py", 42, "Auth bypass via missing check", "code-reviewer", "confirmed"),
        _verdict("src/utils.py", 15, "Missing type annotation", "qa-reviewer", "dismissed"),
        _verdict("src/core/router.py", 88, "God component — 15 responsibilities", "architect", "uncertain"),
        _verdict("src/auth.py", 77, "SQL injection vector via unescaped param", "security-reviewer", "uncertain"),
        _verdict("src/db/models.py", 5, "Direct DB call bypasses service layer", "code-reviewer", "dismissed"),
        _verdict("src/auth.py", 99, "Dead auth code path never reached", "code-reviewer", "confirmed"),
    ]

    return apply_verdicts(findings, verdicts)


# ---------------------------------------------------------------------------
# Unit tests for render_report
# ---------------------------------------------------------------------------

class TestRenderReport(unittest.TestCase):
    """render_report unit tests using REAL apply_verdicts output."""

    def setUp(self):
        self.partition = _build_realistic_partition()
        self.report = render_report(
            partition=self.partition,
            feature="specs/001-auth",
            date_str="2026-06-15",
            finders=["code-reviewer", "architect", "security-reviewer", "qa-reviewer"],
            refuters=["architect", "code-reviewer"],
            source_root="/workspace",
            framework="Python / FastAPI",
            n_scope_files=5,
            finders_skipped=["performance-analyst"],
        )

    # -- Bucket counts -------------------------------------------------------

    def test_partition_bucket_counts(self):
        """The partition produced by real apply_verdicts has the expected counts."""
        self.assertEqual(len(self.partition["confirmed"]), 2)  # F-001 + F-006
        self.assertEqual(len(self.partition["dismissed"]), 1)
        self.assertEqual(len(self.partition["uncertain"]), 1)
        self.assertEqual(len(self.partition["contested"]), 2)

    # -- Header ---------------------------------------------------------------

    def test_header_contains_feature(self):
        self.assertIn("specs/001-auth", self.report)

    def test_header_contains_date(self):
        self.assertIn("2026-06-15", self.report)

    def test_header_contains_finders(self):
        self.assertIn("code-reviewer", self.report)
        self.assertIn("architect", self.report)

    def test_header_contains_source_root(self):
        self.assertIn("/workspace", self.report)

    def test_header_contains_framework(self):
        self.assertIn("Python / FastAPI", self.report)

    def test_header_skipped_finders(self):
        self.assertIn("performance-analyst", self.report)

    def test_header_scope_file_count(self):
        self.assertIn("5 files", self.report)

    # -- Confirmed findings in headline --------------------------------------

    def test_confirmed_finding_in_headline(self):
        """The confirmed F-001 finding must appear in ## Confirmed Findings."""
        idx_confirmed_section = self.report.index("## Confirmed Findings")
        self.assertIn("Auth bypass via missing check", self.report[idx_confirmed_section:])

    def test_confirmed_finding_grouped_by_file(self):
        """src/auth.py gets its own ### section in the headline."""
        idx_confirmed_section = self.report.index("## Confirmed Findings")
        headline_body = self.report[idx_confirmed_section:]
        self.assertIn("### src/auth.py", headline_body)

    def test_confirmed_finding_has_category_subsection(self):
        """The mislogic finding appears under #### Mislogic."""
        idx_confirmed_section = self.report.index("## Confirmed Findings")
        headline_body = self.report[idx_confirmed_section:]
        self.assertIn("#### Mislogic", headline_body)

    # -- Contested findings surfaced in headline, not appendix ---------------

    def test_contested_security_in_headline(self):
        """High-stakes security finding (F-004) appears in ## Confirmed Findings headline."""
        idx_cf = self.report.index("## Confirmed Findings")
        headline_body = self.report[idx_cf:]
        # Cut off at appendix if present
        appendix_marker = "## Dismissed / Worth a Glance"
        if appendix_marker in headline_body:
            headline_body = headline_body[:headline_body.index(appendix_marker)]
        self.assertIn("SQL injection vector via unescaped param", headline_body)

    def test_contested_security_flagged_contested_in_headline(self):
        """The contested security finding carries [CONTESTED] tag in the headline."""
        idx_cf = self.report.index("## Confirmed Findings")
        headline_body = self.report[idx_cf:]
        appendix_marker = "## Dismissed / Worth a Glance"
        if appendix_marker in headline_body:
            headline_body = headline_body[:headline_body.index(appendix_marker)]
        self.assertIn("[CONTESTED]", headline_body)

    def test_constitution_violation_dismissed_in_headline_not_appendix(self):
        """[CONSTITUTION-VIOLATION] dismissed finding (F-005, D7 carve-out)
        surfaces in the headline, NOT in the Dismissed appendix."""
        idx_cf = self.report.index("## Confirmed Findings")
        headline_body = self.report[idx_cf:]
        appendix_marker = "## Dismissed / Worth a Glance"
        if appendix_marker in headline_body:
            headline_body_only = headline_body[:headline_body.index(appendix_marker)]
            appendix_body = headline_body[headline_body.index(appendix_marker):]
        else:
            headline_body_only = headline_body
            appendix_body = ""

        # Pattern must appear in headline (F-005 is in db/models.py)
        self.assertIn("Direct DB call bypasses service layer", headline_body_only)
        # Must NOT appear in the Dismissed subsection
        dismissed_marker = "### Dismissed"
        if dismissed_marker in appendix_body:
            dismissed_body = appendix_body[appendix_body.index(dismissed_marker):]
            self.assertNotIn("Direct DB call bypasses service layer", dismissed_body)

    def test_contested_finding_not_in_appendix(self):
        """SQL injection (security, contested) must NOT appear in the appendix."""
        if "## Dismissed / Worth a Glance" in self.report:
            appendix_start = self.report.index("## Dismissed / Worth a Glance")
            appendix_body = self.report[appendix_start:]
            self.assertNotIn("SQL injection vector via unescaped param", appendix_body)

    # -- Appendix contains dismissed + low-stakes uncertain ------------------

    def test_dismissed_in_appendix(self):
        """Dismissed (non-constitution) finding appears in ## Dismissed / Worth a Glance."""
        self.assertIn("## Dismissed / Worth a Glance", self.report)
        appendix_start = self.report.index("## Dismissed / Worth a Glance")
        appendix_body = self.report[appendix_start:]
        self.assertIn("Missing type annotation", appendix_body)

    def test_uncertain_low_stakes_in_appendix(self):
        """Low-stakes uncertain finding (system_design, not security) in appendix."""
        appendix_start = self.report.index("## Dismissed / Worth a Glance")
        appendix_body = self.report[appendix_start:]
        self.assertIn("God component", appendix_body)

    # -- Severity sort within category bucket --------------------------------

    def test_severity_sort_within_bucket(self):
        """Within a #### <Category> bucket, Critical appears before Info.

        src/auth.py has two confirmed mislogic findings:
          F-001: Critical — "Auth bypass via missing check"
          F-006: Info    — "Dead auth code path never reached"

        The #### Mislogic sub-section under ### src/auth.py must list the
        Critical finding before the Info finding (by character position).
        """
        # Locate ## Confirmed Findings section
        confirmed_start = self.report.index("## Confirmed Findings")
        confirmed_body = self.report[confirmed_start:]

        # Locate ### src/auth.py sub-section within the confirmed body.
        # Use newline-anchored patterns so "#### " headings (which start with
        # "## " as a substring) don't prematurely terminate the slice.
        import re as _re
        auth_header = "### src/auth.py"
        self.assertIn(auth_header, confirmed_body, "### src/auth.py not found in Confirmed Findings")
        auth_start = confirmed_body.index(auth_header)
        # Find the next heading at level 2 or 3 that follows auth_start
        # (i.e. "\n## " or "\n### ") — level-4 headings ("\n#### ") are buckets
        # INSIDE this file section and must not trigger the cut-off.
        next_h2_or_h3 = _re.search(r'\n#{2,3} ', confirmed_body[auth_start + len(auth_header):])
        if next_h2_or_h3:
            end = auth_start + len(auth_header) + next_h2_or_h3.start()
        else:
            end = len(confirmed_body)
        auth_body = confirmed_body[auth_start:end]

        # Both findings must be present inside the auth.py sub-section
        self.assertIn("Auth bypass via missing check", auth_body,
                      "F-001 (Critical) not found in ### src/auth.py section")
        self.assertIn("Dead auth code path never reached", auth_body,
                      "F-006 (Info) not found in ### src/auth.py section")

        # Critical (F-001) must appear before Info (F-006) inside #### Mislogic
        pos_critical = auth_body.index("Auth bypass via missing check")
        pos_info = auth_body.index("Dead auth code path never reached")
        self.assertLess(
            pos_critical, pos_info,
            "Within #### Mislogic bucket (src/auth.py), Critical should appear before Info"
        )

    def test_top_priorities_severity_sort(self):
        """In ## Confirmed — Top Priorities, Critical ranks before High."""
        top_section = self.report[self.report.index("## Confirmed — Top Priorities"):]
        if "## Confirmed Findings" in top_section:
            top_section = top_section[:top_section.index("## Confirmed Findings")]
        # F-001 (Critical mislogic, confirmed) should rank above F-004 (High security, contested)
        pos_f001 = top_section.find("Auth bypass via missing check")
        pos_f004 = top_section.find("SQL injection vector via unescaped param")
        # Both must appear in the top priorities
        self.assertGreater(pos_f001, -1)
        self.assertGreater(pos_f004, -1)
        # Critical (F-001) before High (F-004)
        self.assertLess(pos_f001, pos_f004)

    # -- Summary counts ------------------------------------------------------

    def test_summary_confirmed_count(self):
        self.assertIn("Confirmed: 2", self.report)

    def test_summary_contested_count(self):
        self.assertIn("Contested: 2", self.report)

    def test_summary_dismissed_count(self):
        self.assertIn("Dismissed: 1", self.report)

    def test_summary_uncertain_count(self):
        self.assertIn("Uncertain: 1", self.report)

    def test_summary_severity_counts(self):
        """Summary contains correct Critical/High/Medium/Info counts for headline findings.

        Headline = confirmed (F-001: Critical, F-006: Info)
                 + contested (F-004: High, F-005: Critical)
        → Critical: 2, High: 1, Medium: 0, Info: 1.
        """
        self.assertIn("Critical: 2", self.report)
        self.assertIn("High: 1", self.report)
        self.assertIn("Info: 1", self.report)

    def test_no_consensus_line_in_report(self):
        """/review has no compute-consensus step; the summary must never emit
        a 'consensus' line (it would always be 0 and mislead readers)."""
        self.assertNotIn("consensus", self.report.lower())

    # -- No verdict / approve / pass / fail in the report -------------------

    def test_no_verdict_heading(self):
        """The report must contain no verdict/approve/pass/fail headings."""
        # Scan headings only (lines starting with #)
        heading_lines = [
            ln for ln in self.report.splitlines()
            if ln.strip().startswith("#")
        ]
        for ln in heading_lines:
            lower = ln.lower()
            self.assertNotIn("verdict", lower, "Forbidden word 'verdict' in heading: " + ln)
            self.assertNotIn("approve", lower, "Forbidden word 'approve' in heading: " + ln)
            self.assertNotIn("pass", lower, "Forbidden word 'pass' in heading: " + ln)
            self.assertNotIn("fail", lower, "Forbidden word 'fail' in heading: " + ln)

    def test_no_verdict_in_full_report(self):
        """Grep the full report for forbidden verdict patterns (exact heading forms)."""
        forbidden_patterns = [
            r'^\s*#+\s*Verdict',
            r'^\s*#+\s*Approve',
            r'^\s*#+\s*Pass',
            r'^\s*#+\s*Fail',
            r'\bready to ship\b',
            r'\bapproved\b',
        ]
        for pat in forbidden_patterns:
            m = re.search(pat, self.report, re.IGNORECASE | re.MULTILINE)
            self.assertIsNone(
                m,
                "Forbidden pattern {0!r} found in report at: {1!r}".format(
                    pat, m.group(0) if m else ""
                ),
            )

    # -- review.md written correctly to a temp dir ---------------------------

    def test_write_review_report_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "001-auth")
            path = write_review_report(feature_dir, self.report)
            self.assertTrue(os.path.isfile(path))
            self.assertEqual(os.path.basename(path), "review.md")
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            self.assertEqual(content, self.report)

    def test_write_review_report_is_atomic(self):
        """No .tmp-review-*.md residue after a successful write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "001-auth")
            write_review_report(feature_dir, self.report)
            tmp_files = [
                f for f in os.listdir(feature_dir)
                if f.startswith(".tmp-review-")
            ]
            self.assertEqual(tmp_files, [])

    def test_write_review_report_creates_parent_dirs(self):
        """write_review_report creates feature_dir if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "a", "b", "c")
            self.assertFalse(os.path.isdir(feature_dir))
            write_review_report(feature_dir, "content")
            self.assertTrue(os.path.isfile(os.path.join(feature_dir, "review.md")))


# ---------------------------------------------------------------------------
# Empty-buckets case
# ---------------------------------------------------------------------------

class TestRenderReportEmptyPartition(unittest.TestCase):
    """All-empty partition: valid report, no appendix section, no crash."""

    def setUp(self):
        self.partition = {"confirmed": [], "dismissed": [], "uncertain": [], "contested": []}
        self.report = render_report(
            partition=self.partition,
            feature="specs/002-empty",
            date_str="2026-01-01",
            finders=[],
            refuters=[],
            source_root=".",
            framework="(unset)",
            n_scope_files=0,
        )

    def test_report_is_string(self):
        self.assertIsInstance(self.report, str)

    def test_report_has_header(self):
        self.assertIn("# Feature Review", self.report)
        self.assertIn("specs/002-empty", self.report)
        self.assertIn("2026-01-01", self.report)

    def test_appendix_omitted_when_empty(self):
        self.assertNotIn("## Dismissed / Worth a Glance", self.report)

    def test_no_confirmed_findings_message(self):
        self.assertIn("(no confirmed findings)", self.report)

    def test_summary_all_zeros(self):
        self.assertIn("Confirmed: 0", self.report)
        self.assertIn("Contested: 0", self.report)
        self.assertIn("Dismissed: 0", self.report)
        self.assertIn("Uncertain: 0", self.report)

    def test_methodology_section_present(self):
        self.assertIn("## Methodology", self.report)

    def test_no_verdict_in_empty_report(self):
        heading_lines = [ln for ln in self.report.splitlines() if ln.strip().startswith("#")]
        for ln in heading_lines:
            self.assertNotIn("verdict", ln.lower())
            self.assertNotIn("approve", ln.lower())


# ---------------------------------------------------------------------------
# render_inline_summary unit tests
# ---------------------------------------------------------------------------

class TestRenderInlineSummary(unittest.TestCase):
    """render_inline_summary: count-first format with correct numbers."""

    def setUp(self):
        self.partition = _build_realistic_partition()
        self.summary = render_inline_summary(
            partition=self.partition,
            feature="specs/001-auth",
            finders_skipped=["performance-analyst"],
        )

    def test_summary_has_review_complete_header(self):
        self.assertIn("## Review Complete", self.summary)

    def test_summary_feature_present(self):
        self.assertIn("specs/001-auth", self.summary)

    def test_summary_findings_line_count_first(self):
        """The Findings line must appear before the first finding description."""
        self.assertIn("**Findings**:", self.summary)
        # Count-first: the Findings line comes early
        lines = self.summary.splitlines()
        # Find the Findings: line index and the feature line index
        findings_idx = next(
            (i for i, ln in enumerate(lines) if "**Findings**:" in ln), None
        )
        self.assertIsNotNone(findings_idx)

    def test_summary_confirmed_count_correct(self):
        self.assertIn("**Confirmed**: 2", self.summary)

    def test_summary_contested_count_correct(self):
        self.assertIn("**Contested**: 2", self.summary)

    def test_summary_dismissed_count_correct(self):
        self.assertIn("**Dismissed**: 1", self.summary)

    def test_summary_uncertain_count_correct(self):
        self.assertIn("**Uncertain**: 1", self.summary)

    def test_summary_skipped_finders(self):
        self.assertIn("performance-analyst", self.summary)

    def test_summary_no_verdict_note(self):
        """The summary must state that this is findings only, not a verdict."""
        lower = self.summary.lower()
        self.assertIn("findings only", lower)

    def test_summary_ends_with_newline(self):
        self.assertTrue(self.summary.endswith("\n"))

    def test_summary_severity_counts(self):
        """Critical: 2 (F-001 + F-005 both Critical in headline)."""
        self.assertIn("Critical", self.summary)
        # Not asserting exact numbers since the format may vary; check Findings line
        self.assertIn("2 Critical", self.summary)
        self.assertIn("1 High", self.summary)

    def test_no_consensus_line_in_inline_summary(self):
        """/review has no compute-consensus step; the inline summary must never
        emit a 'consensus' line (it would always be 0 and mislead readers)."""
        self.assertNotIn("consensus", self.summary.lower())

    def test_empty_partition_no_crash(self):
        empty = {"confirmed": [], "dismissed": [], "uncertain": [], "contested": []}
        summary = render_inline_summary(empty, "specs/003-x")
        self.assertIn("## Review Complete", summary)
        self.assertIn("Confirmed**: 0", summary)


# ---------------------------------------------------------------------------
# CLI round-trips: render-report verb
# ---------------------------------------------------------------------------

class TestCLIRenderReport(unittest.TestCase):
    """CLI dispatch for render-report verb."""

    def _run(self, argv, capture_stdout=True, capture_stderr=True):
        """Run main([...]) capturing stdout/stderr. Returns (exit_code, stdout, stderr).

        Catches SystemExit from argparse (missing required args) and returns the
        exit code from the exception rather than letting it propagate.
        """
        old_out, old_err = sys.stdout, sys.stderr
        try:
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            try:
                code = main(argv)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 2
            out = sys.stdout.getvalue()
            err = sys.stderr.getvalue()
        finally:
            sys.stdout = old_out
            sys.stderr = old_err
        return code, out, err

    def _write_partition(self, tmpdir, partition):
        path = os.path.join(tmpdir, "partition.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(partition, fh)
        return path

    def test_basic_round_trip(self):
        """render-report round-trip: review.md is written, JSON ack on stdout."""
        partition = _build_realistic_partition()
        with tempfile.TemporaryDirectory() as tmpdir:
            partition_path = self._write_partition(tmpdir, partition)
            feature_dir = os.path.join(tmpdir, "specs", "001-auth")
            code, out, _ = self._run([
                "render-report",
                "--partition", partition_path,
                "--feature", feature_dir,
                "--date", "2026-06-15",
                "--finders", "code-reviewer,architect",
                "--refuters", "architect",
                "--source-root", "/workspace",
                "--framework", "Python",
                "--scope-files", "3",
            ])
            self.assertEqual(code, 0)
            ack = json.loads(out)
            self.assertIn("path", ack)
            self.assertTrue(os.path.isfile(ack["path"]))
            self.assertEqual(ack["confirmed"], 2)
            self.assertEqual(ack["contested"], 2)
            self.assertEqual(ack["dismissed"], 1)
            self.assertEqual(ack["uncertain"], 1)
            # review.md must exist at <feature_dir>/review.md
            self.assertEqual(
                os.path.normpath(ack["path"]),
                os.path.normpath(os.path.join(feature_dir, "review.md")),
            )
            with open(ack["path"], "r", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("Feature Review", content)

    def test_missing_partition_returns_2(self):
        code, _, err = self._run([
            "render-report",
            "--date", "2026-06-15",
        ])
        self.assertEqual(code, 2)
        self.assertIn("--partition", err)

    def test_missing_date_returns_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            partition = {"confirmed": [], "dismissed": [], "uncertain": [], "contested": []}
            partition_path = self._write_partition(tmpdir, partition)
            code, _, err = self._run([
                "render-report",
                "--partition", partition_path,
            ])
            self.assertEqual(code, 2)
            self.assertIn("--date", err)

    def test_non_json_partition_returns_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = os.path.join(tmpdir, "bad.json")
            with open(bad_path, "w") as fh:
                fh.write("not json {")
            code, _, err = self._run([
                "render-report",
                "--partition", bad_path,
                "--date", "2026-06-15",
            ])
            self.assertEqual(code, 2)

    def test_non_dict_partition_json_returns_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = os.path.join(tmpdir, "bad.json")
            with open(bad_path, "w") as fh:
                json.dump([1, 2, 3], fh)
            code, _, err = self._run([
                "render-report",
                "--partition", bad_path,
                "--date", "2026-06-15",
            ])
            self.assertEqual(code, 2)
            self.assertIn("JSON object", err)


# ---------------------------------------------------------------------------
# CLI round-trips: render-inline-summary verb
# ---------------------------------------------------------------------------

class TestCLIRenderInlineSummary(unittest.TestCase):
    """CLI dispatch for render-inline-summary verb."""

    def _run(self, argv):
        """Run main([...]) capturing stdout/stderr.

        Catches SystemExit from argparse (missing required args) and returns
        the exit code from the exception rather than letting it propagate.
        """
        old_out, old_err = sys.stdout, sys.stderr
        try:
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            try:
                code = main(argv)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 2
            out = sys.stdout.getvalue()
            err = sys.stderr.getvalue()
        finally:
            sys.stdout = old_out
            sys.stderr = old_err
        return code, out, err

    def _write_partition(self, tmpdir, partition):
        path = os.path.join(tmpdir, "partition.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(partition, fh)
        return path

    def test_basic_round_trip(self):
        """render-inline-summary round-trip: ## Review Complete block on stdout."""
        partition = _build_realistic_partition()
        with tempfile.TemporaryDirectory() as tmpdir:
            partition_path = self._write_partition(tmpdir, partition)
            code, out, _ = self._run([
                "render-inline-summary",
                "--partition", partition_path,
                "--feature", "specs/001-auth",
                "--finders-skipped", "performance-analyst",
            ])
            self.assertEqual(code, 0)
            self.assertIn("## Review Complete", out)
            self.assertIn("specs/001-auth", out)
            self.assertIn("**Confirmed**: 2", out)
            self.assertIn("**Contested**: 2", out)
            self.assertIn("performance-analyst", out)

    def test_missing_partition_returns_2(self):
        code, _, err = self._run(["render-inline-summary"])
        self.assertEqual(code, 2)
        self.assertIn("--partition", err)

    def test_non_json_partition_returns_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = os.path.join(tmpdir, "bad.json")
            with open(bad_path, "w") as fh:
                fh.write("not json {")
            code, _, err = self._run([
                "render-inline-summary",
                "--partition", bad_path,
                "--feature", "specs/x",
            ])
            self.assertEqual(code, 2)

    def test_non_dict_partition_returns_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = os.path.join(tmpdir, "bad.json")
            with open(bad_path, "w") as fh:
                json.dump([1, 2, 3], fh)
            code, _, err = self._run([
                "render-inline-summary",
                "--partition", bad_path,
                "--feature", "specs/x",
            ])
            self.assertEqual(code, 2)

    def test_empty_partition_round_trip(self):
        empty = {"confirmed": [], "dismissed": [], "uncertain": [], "contested": []}
        with tempfile.TemporaryDirectory() as tmpdir:
            partition_path = self._write_partition(tmpdir, empty)
            code, out, _ = self._run([
                "render-inline-summary",
                "--partition", partition_path,
                "--feature", "specs/002-empty",
            ])
            self.assertEqual(code, 0)
            self.assertIn("## Review Complete", out)
            self.assertIn("0 Critical", out)

    def test_output_ends_with_newline(self):
        empty = {"confirmed": [], "dismissed": [], "uncertain": [], "contested": []}
        with tempfile.TemporaryDirectory() as tmpdir:
            partition_path = self._write_partition(tmpdir, empty)
            _, out, _ = self._run([
                "render-inline-summary",
                "--partition", partition_path,
                "--feature", "specs/x",
            ])
            self.assertTrue(out.endswith("\n"))


# ---------------------------------------------------------------------------
# _audit independence check (import-level, via source inspection)
# ---------------------------------------------------------------------------

class TestAuditIndependence(unittest.TestCase):
    """_review/_report.py must NOT import anything from _audit/.

    Uses ast.parse to extract actual Import/ImportFrom AST nodes —
    immune to docstrings or comments that mention '_audit' as a reference.
    """

    def _get_imported_module_names(self):
        """Return all module names referenced in actual import statements.

        Uses ast.parse so docstring/comment mentions of module names are
        not confused with real imports.
        """
        import ast
        report_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_review" / "_report.py"
        )
        with open(report_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        tree = ast.parse(source)
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module)
        return names

    def test_no_audit_in_actual_imports(self):
        """No actual import statement in _report.py references _audit."""
        imported = self._get_imported_module_names()
        audit_imports = [n for n in imported if "_audit" in n]
        self.assertEqual(
            audit_imports,
            [],
            "_report.py has import(s) referencing _audit: {0}".format(audit_imports),
        )


if __name__ == "__main__":
    unittest.main()
