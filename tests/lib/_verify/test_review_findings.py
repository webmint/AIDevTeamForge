"""Tests for src/devforge/lib/_verify/_review_findings.py and the
read-review-findings CLI verb.

Real-producer round-trip discipline:
  A real review.md is produced by calling the actual _review._report
  render_report + write_review_report (the same functions review_helper
  render-report calls under the hood) on a realistic partition dict built
  through the REAL _shared.apply_verdicts function.  The resulting file is
  then parsed by read_review_findings.  No hand-authored review.md text.

Coverage:
  read_review_findings (function level):
    - Missing file → {missing: True, confirmed: [], contested: [], summary: {...zeros}}.
    - Directory path → review.md appended automatically.
    - Happy path: real review.md (produced by render_report) → confirmed + contested
      findings extracted, summary counts correct.
    - Confirmed findings have severity, file, category, pattern, confidence.
    - [CONTESTED] findings land in contested, not confirmed.
    - Summary partition counts match the apply_verdicts buckets.
    - Summary severity counts (Critical, High, …) are extracted.

  CLI round-trip via main([...]):
    - read-review-findings --feature <dir-containing-review.md> → JSON on stdout, exit 0.
    - missing → JSON with missing=True, exit 0.
    - --feature <dir> (directory variant) resolves review.md correctly.
    - Missing --feature flag → non-zero exit (argparse requires it).
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

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

# Import real producers: _shared apply_verdicts + _review render_report / write_review_report
from _shared._verify import apply_verdicts  # noqa: E402
from _review._report import render_report, write_review_report  # noqa: E402
from _verify._review_findings import read_review_findings  # noqa: E402
from _verify._verdict import compute_verdict  # noqa: E402
from _verify._cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# Real-producer fixture helpers (mirrors test_report.py in _review)
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
    """Minimal ParsedFinding dict — same shape as the _review tests use."""
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
    if finding_id is not None:
        f["finding_id"] = finding_id
    return f


def _verdict(file, line, pattern, agent, verdict_val, justification="confirmed by evidence"):
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


def _build_realistic_partition():
    """Build a realistic partition with all four buckets via the real apply_verdicts.

    Buckets:
      confirmed  — one Critical mislogic finding
      dismissed  — one Info best_practice finding (non-constitution)
      uncertain  — one Medium system_design finding (low-stakes)
      contested  — (a) one High security finding (uncertain → high-stakes → contested)
                   (b) one Critical [CONSTITUTION-VIOLATION] finding (dismissed → contested)
    """
    findings = [
        _finding(
            agent="code-reviewer",
            file="src/auth.py",
            line=42,
            pattern="Auth bypass via missing null check",
            severity="Critical",
            category="mislogic",
            finding_id="F-001",
        ),
        _finding(
            agent="qa-reviewer",
            file="src/utils.py",
            line=15,
            pattern="Missing type annotation",
            severity="Info",
            category="best_practice",
            finding_id="F-002",
        ),
        _finding(
            agent="architect",
            file="src/core/router.py",
            line=88,
            pattern="God component with 15 responsibilities",
            severity="Medium",
            category="system_design",
            finding_id="F-003",
        ),
        _finding(
            agent="security-reviewer",
            file="src/api/query.py",
            line=55,
            pattern="SQL injection via unescaped param",
            severity="High",
            category="security",
            finding_id="F-004",
        ),
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
    ]

    verdicts = [
        _verdict("src/auth.py", 42, "Auth bypass via missing null check", "code-reviewer", "confirmed"),
        _verdict("src/utils.py", 15, "Missing type annotation", "qa-reviewer", "dismissed"),
        _verdict("src/core/router.py", 88, "God component with 15 responsibilities", "architect", "uncertain"),
        _verdict("src/api/query.py", 55, "SQL injection via unescaped param", "security-reviewer", "uncertain"),
        _verdict("src/db/models.py", 5, "Direct DB call bypasses service layer", "code-reviewer", "dismissed"),
    ]

    return apply_verdicts(findings, verdicts)


def _make_real_review_md(feature_dir):
    # type: (str) -> str
    """Produce a real review.md by calling the actual render_report + write_review_report.

    Returns the path written.  This is the REAL producer round-trip.
    """
    partition = _build_realistic_partition()
    content = render_report(
        partition=partition,
        feature=feature_dir,
        date_str="2026-06-16",
        finders=["code-reviewer", "architect", "security-reviewer", "qa-reviewer"],
        refuters=["architect", "code-reviewer"],
        source_root="/workspace",
        framework="Python / FastAPI",
        n_scope_files=5,
        finders_skipped=[],
    )
    return write_review_report(feature_dir, content)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture(argv):
    """Run main(argv) with captured stdout/stderr. Returns (stdout, stderr, rc)."""
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = buf_out, buf_err
    try:
        rc = main(argv)
    except SystemExit as exc:
        rc = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return buf_out.getvalue(), buf_err.getvalue(), rc


# ---------------------------------------------------------------------------
# Tests — missing review.md
# ---------------------------------------------------------------------------


class TestReadReviewFindingsMissing(unittest.TestCase):
    """read_review_findings returns a missing=True dict when review.md is absent."""

    def setUp(self):
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.td, ignore_errors=True)

    def test_missing_file_path(self):
        result = read_review_findings(os.path.join(self.td, "review.md"))
        self.assertTrue(result["missing"])

    def test_missing_directory_variant(self):
        """When given a directory with no review.md, missing=True."""
        result = read_review_findings(self.td)
        self.assertTrue(result["missing"])

    def test_missing_empty_confirmed(self):
        result = read_review_findings(os.path.join(self.td, "review.md"))
        self.assertEqual(result["confirmed"], [])

    def test_missing_empty_contested(self):
        result = read_review_findings(os.path.join(self.td, "review.md"))
        self.assertEqual(result["contested"], [])

    def test_missing_summary_zeros(self):
        result = read_review_findings(os.path.join(self.td, "review.md"))
        s = result["summary"]
        self.assertEqual(s["critical"], 0)
        self.assertEqual(s["high"], 0)
        self.assertEqual(s["medium"], 0)
        self.assertEqual(s["info"], 0)
        self.assertEqual(s["confirmed_count"], 0)
        self.assertEqual(s["contested_count"], 0)
        self.assertEqual(s["dismissed_count"], 0)
        self.assertEqual(s["uncertain_count"], 0)

    def test_missing_has_required_keys(self):
        result = read_review_findings(os.path.join(self.td, "review.md"))
        for key in ("missing", "confirmed", "contested", "summary"):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# Tests — real-producer round-trip
# ---------------------------------------------------------------------------


class TestReadReviewFindingsRealProducer(unittest.TestCase):
    """Round-trip: real render_report output → read_review_findings parser."""

    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.mkdtemp()
        cls.feature_dir = os.path.join(cls.td, "specs", "001-auth")
        os.makedirs(cls.feature_dir, exist_ok=True)
        cls.review_path = _make_real_review_md(cls.feature_dir)
        cls.result = read_review_findings(cls.review_path)
        cls.partition = _build_realistic_partition()

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.td, ignore_errors=True)

    # --- Top-level structure ---

    def test_not_missing(self):
        self.assertFalse(self.result["missing"])

    def test_has_required_keys(self):
        for key in ("missing", "confirmed", "contested", "summary"):
            self.assertIn(key, self.result)

    def test_review_md_was_written(self):
        self.assertTrue(os.path.isfile(self.review_path))

    # --- Confirmed findings ---

    def test_confirmed_is_list(self):
        self.assertIsInstance(self.result["confirmed"], list)

    def test_confirmed_count_matches_partition(self):
        """Confirmed count in the parsed result matches the real apply_verdicts bucket."""
        expected = len(self.partition["confirmed"])
        actual = len(self.result["confirmed"])
        self.assertEqual(
            actual, expected,
            "Expected {0} confirmed, got {1}".format(expected, actual),
        )

    def test_confirmed_findings_have_severity(self):
        for f in self.result["confirmed"]:
            self.assertIn("severity", f)
            self.assertIn(f["severity"], ("Critical", "High", "Medium", "Info"))

    def test_confirmed_findings_have_file(self):
        for f in self.result["confirmed"]:
            self.assertIn("file", f)

    def test_confirmed_findings_have_pattern(self):
        for f in self.result["confirmed"]:
            self.assertIn("pattern", f)

    def test_confirmed_findings_have_category(self):
        for f in self.result["confirmed"]:
            self.assertIn("category", f)

    def test_confirmed_findings_have_confidence(self):
        for f in self.result["confirmed"]:
            self.assertIn("confidence", f)

    def test_no_contested_in_confirmed(self):
        """No [CONTESTED]-tagged finding should be in confirmed."""
        for f in self.result["confirmed"]:
            tags = f.get("tags") or []
            self.assertNotIn("[CONTESTED]", tags)

    def test_confirmed_auth_file_present(self):
        """The auth.py Critical finding should appear in confirmed."""
        files = [f.get("file", "") for f in self.result["confirmed"]]
        self.assertTrue(
            any("auth.py" in fp for fp in files),
            "Expected auth.py finding in confirmed; got files: {0}".format(files),
        )

    # --- Contested findings ---

    def test_contested_is_list(self):
        self.assertIsInstance(self.result["contested"], list)

    def test_contested_count_matches_partition(self):
        """Contested count matches the real apply_verdicts bucket."""
        expected = len(self.partition["contested"])
        actual = len(self.result["contested"])
        self.assertEqual(
            actual, expected,
            "Expected {0} contested, got {1}".format(expected, actual),
        )

    def test_contested_findings_tagged(self):
        """All findings in the contested list carry [CONTESTED] tag."""
        for f in self.result["contested"]:
            tags = f.get("tags") or []
            self.assertIn(
                "[CONTESTED]", tags,
                "Contested finding missing [CONTESTED] tag: {0}".format(f),
            )

    def test_contested_security_finding_present(self):
        """The High security finding (uncertain → contested) is in the contested list."""
        patterns = [f.get("pattern", "") for f in self.result["contested"]]
        self.assertTrue(
            any("SQL injection" in p or "query" in p.lower() or "security" in p.lower()
                for p in patterns),
            "Expected security finding in contested; patterns: {0}".format(patterns),
        )

    # --- Finding 3 fix: [CONSTITUTION-VIOLATION] parsed into tags ---

    def test_constitution_violation_tag_parsed_from_first_line(self):
        """[CONSTITUTION-VIOLATION] in the rendered first line is extracted into tags.

        The real producer (_review/_report.py _render_finding_body) emits
        [CONSTITUTION-VIOLATION] in the finding's first line when the finding's
        tags list contains it.  This test verifies the parser (_parse_confirmed_findings)
        captures it in the parsed finding's 'tags' field.

        F-005 (Direct DB call bypasses service layer) has [CONSTITUTION-VIOLATION]
        in its input tags and a 'dismissed' verdict → D7 elevates it to 'contested'.
        So it appears in contested, and its first line must carry [CONSTITUTION-VIOLATION].
        """
        # Find the constitution violation finding in the contested bucket
        contested = self.result["contested"]
        cv_findings = [
            f for f in contested
            if "[CONSTITUTION-VIOLATION]" in (f.get("tags") or [])
        ]
        self.assertTrue(
            len(cv_findings) >= 1,
            "Expected at least one contested finding with [CONSTITUTION-VIOLATION] tag "
            "in parsed tags, but none found. Contested tags: {0}".format(
                [f.get("tags") for f in contested]
            ),
        )

    def test_constitution_violation_finding_has_both_tags(self):
        """The constitution finding should carry both [CONTESTED] and [CONSTITUTION-VIOLATION] tags.

        F-005 was dismissed → D7 makes it contested → it appears in the contested section
        with both [CONTESTED] and [CONSTITUTION-VIOLATION] in its first line.
        """
        contested = self.result["contested"]
        cv_findings = [
            f for f in contested
            if "[CONSTITUTION-VIOLATION]" in (f.get("tags") or [])
        ]
        if not cv_findings:
            self.skipTest("No [CONSTITUTION-VIOLATION] finding found in contested — check fixture")
        f = cv_findings[0]
        self.assertIn("[CONTESTED]", f.get("tags", []),
                      "Constitution finding in contested should also carry [CONTESTED] tag")
        self.assertIn("[CONSTITUTION-VIOLATION]", f.get("tags", []))

    def test_d7_constitution_violation_blocks_approved_via_compute_verdict(self):
        """End-to-end D7: contested [CONSTITUTION-VIOLATION] parsed finding blocks APPROVED.

        This test drives the full path:
          real render_report → real read_review_findings → compute_verdict
        and asserts that a contested [CONSTITUTION-VIOLATION] finding (from F-005)
        causes compute_verdict to return at least NEEDS WORK, never APPROVED.

        Before the Finding 3 fix, [CONSTITUTION-VIOLATION] was NOT parsed into tags,
        so _is_constitution_violation() (which checks tags OR category=='constitution')
        would not detect it if the Category: detail line was absent or parsed differently —
        creating a D7 crack.  With the fix, the tag is extracted from the first line
        directly, closing the gap.
        """
        # Feed the real parsed result into compute_verdict with all-passing ACs
        # and a clean mechanical status.
        from _verify._verdict import compute_verdict as _cv

        empty_hygiene = {
            "scope_creep": [],
            "leftover_artifacts": [],
            "scope_creep_checked": False,
            "files_checked": 0,
            "files_unreadable": [],
        }

        result = _cv(
            ac_results=[{"id": "AC-1", "text": "test", "checked": False,
                         "subsection": "", "status": "PASS", "evidence": ""}],
            mechanical_status="pass",
            review_findings=self.result,
            hygiene=empty_hygiene,
            ac_verification_mode="code-only",
        )

        self.assertNotEqual(
            result["verdict"], "APPROVED",
            "D7 VIOLATED: compute_verdict returned APPROVED despite a "
            "contested [CONSTITUTION-VIOLATION] finding in the review. "
            "Contested findings: {0}".format(
                [(f.get("pattern"), f.get("tags")) for f in self.result["contested"]]
            ),
        )

    # --- Summary ---

    def test_summary_is_dict(self):
        self.assertIsInstance(self.result["summary"], dict)

    def test_summary_has_required_keys(self):
        required = {
            "critical", "high", "medium", "info",
            "confirmed_count", "contested_count", "dismissed_count", "uncertain_count",
        }
        self.assertTrue(required <= set(self.result["summary"].keys()))

    def test_summary_confirmed_count(self):
        """summary.confirmed_count parsed from ## Summary matches apply_verdicts."""
        expected = len(self.partition["confirmed"])
        self.assertEqual(self.result["summary"]["confirmed_count"], expected)

    def test_summary_contested_count(self):
        expected = len(self.partition["contested"])
        self.assertEqual(self.result["summary"]["contested_count"], expected)

    def test_summary_dismissed_count(self):
        expected = len(self.partition["dismissed"])
        self.assertEqual(self.result["summary"]["dismissed_count"], expected)

    def test_summary_uncertain_count(self):
        expected = len(self.partition["uncertain"])
        self.assertEqual(self.result["summary"]["uncertain_count"], expected)

    def test_summary_severity_critical_nonzero(self):
        """At least one Critical finding is in the headline (confirmed or contested)."""
        self.assertGreater(self.result["summary"]["critical"], 0)

    def test_summary_high_nonzero(self):
        """The security finding is High → summary.high >= 1."""
        self.assertGreater(self.result["summary"]["high"], 0)

    # --- Directory path variant ---

    def test_directory_path_resolves_review_md(self):
        """read_review_findings(<feature_dir>) appends /review.md automatically."""
        result_by_dir = read_review_findings(self.feature_dir)
        self.assertFalse(result_by_dir["missing"])
        self.assertEqual(
            len(result_by_dir["confirmed"]),
            len(self.result["confirmed"]),
        )


# ---------------------------------------------------------------------------
# Tests — CLI round-trip
# ---------------------------------------------------------------------------


class TestReadReviewFindingsCLI(unittest.TestCase):
    """CLI round-trip tests for read-review-findings verb."""

    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.mkdtemp()
        cls.feature_dir = os.path.join(cls.td, "specs", "001-cli-test")
        os.makedirs(cls.feature_dir, exist_ok=True)
        _make_real_review_md(cls.feature_dir)

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.td, ignore_errors=True)

    def test_exit_0_with_existing_review(self):
        _, _, rc = _capture(["read-review-findings", "--feature", self.feature_dir])
        self.assertEqual(rc, 0)

    def test_stdout_is_valid_json(self):
        out, _, rc = _capture(["read-review-findings", "--feature", self.feature_dir])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIsInstance(data, dict)

    def test_has_required_keys(self):
        out, _, _ = _capture(["read-review-findings", "--feature", self.feature_dir])
        data = json.loads(out)
        for key in ("missing", "confirmed", "contested", "summary"):
            self.assertIn(key, data)

    def test_not_missing(self):
        out, _, _ = _capture(["read-review-findings", "--feature", self.feature_dir])
        data = json.loads(out)
        self.assertFalse(data["missing"])

    def test_missing_dir_exit_0(self):
        """Non-existent feature dir → exit 0, missing=True in JSON."""
        out, _, rc = _capture(["read-review-findings", "--feature", "/no/such/dir"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["missing"])

    def test_missing_feature_flag(self):
        """Omitting --feature → non-zero exit (argparse requires it)."""
        _, _, rc = _capture(["read-review-findings"])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Tests — read-ac-config CLI verb
# ---------------------------------------------------------------------------


class TestReadAcConfigCLI(unittest.TestCase):
    """CLI round-trip tests for read-ac-config verb."""

    def _capture(self, argv):
        return _capture(argv)

    def test_exit_0_no_config(self):
        """No project-config.json → exit 0 with defaults."""
        with tempfile.TemporaryDirectory() as td:
            out, _, rc = self._capture(["read-ac-config", "--root", td])
            self.assertEqual(rc, 0)

    def test_defaults_when_no_config(self):
        """Returns safe defaults when no project-config.json exists."""
        with tempfile.TemporaryDirectory() as td:
            out, _, rc = self._capture(["read-ac-config", "--root", td])
            self.assertEqual(rc, 0)
            data = json.loads(out)
            self.assertEqual(data["ac_verification_mode"], "off")
            self.assertEqual(data["ac_runtime_url"], "")
            self.assertEqual(data["ac_runtime_api_base"], "")
            self.assertEqual(data["ac_runtime_cli_command"], "")

    def test_has_required_keys(self):
        with tempfile.TemporaryDirectory() as td:
            out, _, _ = self._capture(["read-ac-config", "--root", td])
            data = json.loads(out)
            for key in (
                "ac_verification_mode",
                "ac_runtime_url",
                "ac_runtime_api_base",
                "ac_runtime_cli_command",
            ):
                self.assertIn(key, data)

    def test_reads_real_project_config(self):
        """Reads a real project-config.json with UPPERCASED keys."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = os.path.join(td, ".devforge")
            os.makedirs(devforge_dir, exist_ok=True)
            config = {
                "PROJECT_NAME": "test-project",
                "AC_VERIFICATION_MODE": "tests",
                "AC_RUNTIME_URL": "http://localhost:3000",
                "AC_RUNTIME_API_BASE": "http://localhost:8000",
                "AC_RUNTIME_CLI_COMMAND": "npm test",
            }
            config_path = os.path.join(devforge_dir, "project-config.json")
            with open(config_path, "w", encoding="utf-8") as fh:
                import json as _json
                _json.dump(config, fh)

            out, _, rc = self._capture(["read-ac-config", "--root", td])
            self.assertEqual(rc, 0)
            data = json.loads(out)
            self.assertEqual(data["ac_verification_mode"], "tests")
            self.assertEqual(data["ac_runtime_url"], "http://localhost:3000")
            self.assertEqual(data["ac_runtime_api_base"], "http://localhost:8000")
            self.assertEqual(data["ac_runtime_cli_command"], "npm test")

    def test_partial_config_uses_defaults_for_missing(self):
        """Keys absent from config fall back to defaults."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = os.path.join(td, ".devforge")
            os.makedirs(devforge_dir, exist_ok=True)
            config = {"AC_VERIFICATION_MODE": "code-only"}
            config_path = os.path.join(devforge_dir, "project-config.json")
            with open(config_path, "w", encoding="utf-8") as fh:
                import json as _json
                _json.dump(config, fh)

            out, _, rc = self._capture(["read-ac-config", "--root", td])
            self.assertEqual(rc, 0)
            data = json.loads(out)
            self.assertEqual(data["ac_verification_mode"], "code-only")
            self.assertEqual(data["ac_runtime_url"], "")

    def test_corrupted_config_uses_defaults(self):
        """Corrupted project-config.json → falls back to defaults, exit 0."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = os.path.join(td, ".devforge")
            os.makedirs(devforge_dir, exist_ok=True)
            config_path = os.path.join(devforge_dir, "project-config.json")
            with open(config_path, "w", encoding="utf-8") as fh:
                fh.write("not valid json {{{")

            out, _, rc = self._capture(["read-ac-config", "--root", td])
            self.assertEqual(rc, 0)
            data = json.loads(out)
            self.assertEqual(data["ac_verification_mode"], "off")


if __name__ == "__main__":
    unittest.main()
