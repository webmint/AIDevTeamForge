"""Tests for src/devforge/lib/_pr_review/_output.py.

Coverage:
  TestComputeSlopScore: empty, mixed, capped at 100.
  TestComputeBlastRiskScore: empty blast, unfilled probes, filled probes.
  TestComputeDriftSummary: empty bullets, bullets+coverage, bullets without coverage.
  TestSortFindings: severity order; same severity sorted by location.
  TestCountByCategory: counts, unknown categories, empty.
  TestRenderFinding: standard; missing fix_hint; missing source_heuristic.
  TestRenderSummary: zero-count categories omitted; aggregate scores rendered.
  TestRenderFindingsMd: empty findings message; populated findings.
  TestRunHappyPath: state with smells + findings -> findings.md written, JSON correct.
  TestRunNoStateFile: missing state.json -> raises ValueError.
  TestRunEmptyFindings: empty findings -> writes findings.md with empty marker.
"""

import dataclasses
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

from _pr_review._output import (  # noqa: E402
    _compute_slop_score,
    _compute_blast_risk_score,
    _compute_drift_summary,
    _sort_findings,
    _count_by_severity,
    _count_by_category,
    _render_finding,
    _render_summary,
    _render_findings_md,
    _SEVERITY_ORDER,
    run,
)
from _pr_review._state import PRReviewState, state_path  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

def _make_finding(severity="medium", location="src/foo.py:10", category="smell",
                  evidence="evidence text", fix_hint="fix it",
                  source_heuristic="my-heuristic"):
    return {
        "severity": severity,
        "location": location,
        "category": category,
        "evidence": evidence,
        "fix_hint": fix_hint,
        "source_heuristic": source_heuristic,
    }


def _make_state(pr_number=42, repo="acme/app", findings=None, blast=None, drift=None,
                smells=None):
    return PRReviewState(
        pr_number=pr_number,
        repo=repo,
        findings=findings if findings is not None else [],
        blast=blast if blast is not None else [],
        drift=drift if drift is not None else {},
        smells=smells if smells is not None else [],
    )


def _write_state(tmp_dir, state, pr_number=None):
    """Write a PRReviewState to the expected path under tmp_dir."""
    pn = pr_number if pr_number is not None else state.pr_number
    devforge = os.path.join(tmp_dir, ".devforge")
    sp = state_path(devforge, pn)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(dataclasses.asdict(state), fh, indent=2)
        fh.write("\n")
    return sp


# ---------------------------------------------------------------------------
# TestComputeSlopScore
# ---------------------------------------------------------------------------

class TestComputeSlopScore(unittest.TestCase):
    def test_empty_is_zero(self):
        by_sev = {"high": 0, "medium": 0, "low": 0, "nit": 0}
        self.assertEqual(_compute_slop_score(by_sev), 0)

    def test_single_high(self):
        by_sev = {"high": 1, "medium": 0, "low": 0, "nit": 0}
        self.assertEqual(_compute_slop_score(by_sev), 30)

    def test_single_medium(self):
        by_sev = {"high": 0, "medium": 1, "low": 0, "nit": 0}
        self.assertEqual(_compute_slop_score(by_sev), 10)

    def test_single_low(self):
        by_sev = {"high": 0, "medium": 0, "low": 1, "nit": 0}
        self.assertEqual(_compute_slop_score(by_sev), 3)

    def test_single_nit(self):
        by_sev = {"high": 0, "medium": 0, "low": 0, "nit": 1}
        self.assertEqual(_compute_slop_score(by_sev), 1)

    def test_mixed_severities(self):
        by_sev = {"high": 1, "medium": 2, "low": 1, "nit": 3}
        # 30 + 20 + 3 + 3 = 56
        self.assertEqual(_compute_slop_score(by_sev), 56)

    def test_capped_at_100(self):
        by_sev = {"high": 10, "medium": 0, "low": 0, "nit": 0}
        # 300 -> capped at 100
        self.assertEqual(_compute_slop_score(by_sev), 100)

    def test_empty_dict(self):
        self.assertEqual(_compute_slop_score({}), 0)

    def test_unknown_severity_ignored(self):
        by_sev = {"critical": 5, "high": 0, "medium": 0, "low": 0, "nit": 0}
        # "critical" not in weights -> 0
        self.assertEqual(_compute_slop_score(by_sev), 0)


# ---------------------------------------------------------------------------
# TestComputeBlastRiskScore
# ---------------------------------------------------------------------------

class TestComputeBlastRiskScore(unittest.TestCase):
    def test_empty_blast_is_zero(self):
        state = _make_state(blast=[])
        self.assertEqual(_compute_blast_risk_score(state), 0)

    def test_none_blast_is_zero(self):
        state = _make_state(blast=None)
        self.assertEqual(_compute_blast_risk_score(state), 0)

    def test_unfilled_probes_base_score(self):
        # 2 unfilled probes: 2 * 3 = 6
        blast = [
            {"symbol": "foo", "filled": False},
            {"symbol": "bar", "filled": False},
        ]
        state = _make_state(blast=blast)
        score = _compute_blast_risk_score(state)
        self.assertEqual(score, 6)

    def test_filled_probe_with_callers(self):
        # 1 probe (base=3) + max callers=5 -> 3 + 5*2 = 13
        blast = [
            {
                "symbol": "compute",
                "filled": True,
                "callers": ["a", "b", "c", "d", "e"],
            }
        ]
        state = _make_state(blast=blast)
        score = _compute_blast_risk_score(state)
        self.assertEqual(score, 13)

    def test_filled_probe_no_callers(self):
        blast = [{"symbol": "x", "filled": True, "callers": []}]
        state = _make_state(blast=blast)
        score = _compute_blast_risk_score(state)
        self.assertEqual(score, 3)

    def test_capped_at_100(self):
        # 20 probes (20*3=60) + callers=20 (20*2=40) = 100
        blast = [
            {"symbol": "s{0}".format(i), "filled": False}
            for i in range(20)
        ]
        blast[0]["filled"] = True
        blast[0]["callers"] = ["c{0}".format(i) for i in range(20)]
        state = _make_state(blast=blast)
        score = _compute_blast_risk_score(state)
        self.assertLessEqual(score, 100)

    def test_multiple_filled_uses_max(self):
        # Two filled probes with different caller counts: max wins
        blast = [
            {"symbol": "a", "filled": True, "callers": ["x", "y"]},   # 2
            {"symbol": "b", "filled": True, "callers": ["p", "q", "r"]},  # 3
        ]
        state = _make_state(blast=blast)
        # base=2*3=6, max_callers=3, 6 + 3*2 = 12
        score = _compute_blast_risk_score(state)
        self.assertEqual(score, 12)


# ---------------------------------------------------------------------------
# TestComputeDriftSummary
# ---------------------------------------------------------------------------

class TestComputeDriftSummary(unittest.TestCase):
    def test_empty_drift_not_assessed(self):
        state = _make_state(drift={})
        self.assertEqual(_compute_drift_summary(state), "drift not assessed")

    def test_none_drift_not_assessed(self):
        state = _make_state(drift=None)
        self.assertEqual(_compute_drift_summary(state), "drift not assessed")

    def test_empty_bullets_not_assessed(self):
        state = _make_state(drift={"bullets": []})
        self.assertEqual(_compute_drift_summary(state), "drift not assessed")

    def test_bullets_no_coverage(self):
        drift = {
            "bullets": [{"id": "B1", "text": "x"}, {"id": "B2", "text": "y"}],
            "coverage_matrix": [],
        }
        state = _make_state(drift=drift)
        self.assertEqual(_compute_drift_summary(state), "0/2 covered")

    def test_bullets_with_satisfied(self):
        drift = {
            "bullets": [{"id": "B1"}, {"id": "B2"}, {"id": "B3"}],
            "coverage_matrix": [
                {"bullet_id": "B1", "status": "satisfied"},
                {"bullet_id": "B2", "status": "missing"},
                {"bullet_id": "B3", "status": "satisfied"},
            ],
        }
        state = _make_state(drift=drift)
        self.assertEqual(_compute_drift_summary(state), "2/3 covered")

    def test_all_satisfied(self):
        drift = {
            "bullets": [{"id": "B1"}, {"id": "B2"}],
            "coverage_matrix": [
                {"bullet_id": "B1", "status": "satisfied"},
                {"bullet_id": "B2", "status": "satisfied"},
            ],
        }
        state = _make_state(drift=drift)
        self.assertEqual(_compute_drift_summary(state), "2/2 covered")

    def test_bullets_no_coverage_matrix_key(self):
        drift = {"bullets": [{"id": "B1"}, {"id": "B2"}]}
        state = _make_state(drift=drift)
        self.assertEqual(_compute_drift_summary(state), "0/2 covered")


# ---------------------------------------------------------------------------
# TestSortFindings
# ---------------------------------------------------------------------------

class TestSortFindings(unittest.TestCase):
    def test_high_before_medium_before_low_before_nit(self):
        findings = [
            {"severity": "nit", "location": "a.py"},
            {"severity": "low", "location": "b.py"},
            {"severity": "high", "location": "c.py"},
            {"severity": "medium", "location": "d.py"},
        ]
        result = _sort_findings(findings)
        severities = [f["severity"] for f in result]
        self.assertEqual(severities, ["high", "medium", "low", "nit"])

    def test_same_severity_sorted_by_location(self):
        findings = [
            {"severity": "medium", "location": "z.py:1"},
            {"severity": "medium", "location": "a.py:5"},
            {"severity": "medium", "location": "m.py:2"},
        ]
        result = _sort_findings(findings)
        locs = [f["location"] for f in result]
        self.assertEqual(locs, ["a.py:5", "m.py:2", "z.py:1"])

    def test_unknown_severity_sorts_last(self):
        findings = [
            {"severity": "critical", "location": "a.py"},
            {"severity": "nit", "location": "b.py"},
            {"severity": "high", "location": "c.py"},
        ]
        result = _sort_findings(findings)
        self.assertEqual(result[0]["severity"], "high")
        self.assertEqual(result[1]["severity"], "nit")
        self.assertEqual(result[2]["severity"], "critical")

    def test_no_location_sorts_before_with_location(self):
        # location is an empty string when absent — "" sorts before "a.py" lexicographically.
        findings = [
            {"severity": "low", "location": "a.py"},
            {"severity": "low"},
        ]
        result = _sort_findings(findings)
        # empty string / None sorts before "a.py"
        self.assertIsNone(result[0].get("location"))

    def test_empty_list_returns_empty(self):
        self.assertEqual(_sort_findings([]), [])

    def test_single_finding_returned(self):
        findings = [{"severity": "high", "location": "x.py"}]
        self.assertEqual(_sort_findings(findings), findings)

    def test_mixed_severities_and_locations(self):
        findings = [
            {"severity": "low", "location": "z.py"},
            {"severity": "high", "location": "b.py"},
            {"severity": "medium", "location": "a.py"},
            {"severity": "high", "location": "a.py"},
            {"severity": "nit", "location": "c.py"},
        ]
        result = _sort_findings(findings)
        # high,a.py | high,b.py | medium,a.py | low,z.py | nit,c.py
        self.assertEqual(result[0], {"severity": "high", "location": "a.py"})
        self.assertEqual(result[1], {"severity": "high", "location": "b.py"})
        self.assertEqual(result[2], {"severity": "medium", "location": "a.py"})
        self.assertEqual(result[3], {"severity": "low", "location": "z.py"})
        self.assertEqual(result[4], {"severity": "nit", "location": "c.py"})


# ---------------------------------------------------------------------------
# TestCountByCategory
# ---------------------------------------------------------------------------

class TestCountByCategory(unittest.TestCase):
    def test_empty_findings(self):
        self.assertEqual(_count_by_category([]), {})

    def test_single_category(self):
        findings = [
            {"category": "smell"},
            {"category": "smell"},
            {"category": "blast"},
        ]
        counts = _count_by_category(findings)
        self.assertEqual(counts.get("smell"), 2)
        self.assertEqual(counts.get("blast"), 1)

    def test_missing_category_defaults_other(self):
        findings = [{"severity": "low"}]
        counts = _count_by_category(findings)
        self.assertEqual(counts.get("other"), 1)

    def test_all_categories(self):
        cats = ["smell", "blast", "drift", "convention", "hallucination", "missing-test"]
        findings = [{"category": c} for c in cats]
        counts = _count_by_category(findings)
        for c in cats:
            self.assertEqual(counts.get(c), 1)


# ---------------------------------------------------------------------------
# TestRenderFinding
# ---------------------------------------------------------------------------

class TestRenderFinding(unittest.TestCase):
    def test_standard_rendering(self):
        finding = _make_finding(
            severity="high",
            location="src/auth.py:42",
            category="smell",
            evidence="found bad pattern",
            fix_hint="refactor this",
            source_heuristic="hedge-defensive",
        )
        rendered = _render_finding(finding, 1)
        self.assertIn("### [high]", rendered)
        self.assertIn("`src/auth.py:42`", rendered)
        self.assertIn("(smell)", rendered)
        self.assertIn("**Evidence**: found bad pattern", rendered)
        self.assertIn("**Fix**: refactor this", rendered)
        self.assertIn("**Source**: hedge-defensive", rendered)
        self.assertIn("---", rendered)

    def test_missing_fix_hint_shows_none(self):
        finding = _make_finding(fix_hint="")
        rendered = _render_finding(finding, 1)
        self.assertIn("**Fix**: (none)", rendered)

    def test_missing_source_heuristic_falls_back_to_category(self):
        finding = _make_finding(category="blast", source_heuristic="")
        rendered = _render_finding(finding, 1)
        self.assertIn("**Source**: blast-heuristic", rendered)

    def test_none_values_handled(self):
        finding = {
            "severity": None,
            "location": None,
            "category": None,
            "evidence": None,
            "fix_hint": None,
            "source_heuristic": None,
        }
        rendered = _render_finding(finding, 1)
        self.assertIn("### [low]", rendered)  # default severity
        self.assertIn("(unknown)", rendered)   # default location
        self.assertIn("(none)", rendered)

    def test_severity_in_header(self):
        for sev in _SEVERITY_ORDER:
            with self.subTest(sev=sev):
                finding = _make_finding(severity=sev)
                rendered = _render_finding(finding, 1)
                self.assertIn("[{0}]".format(sev), rendered)


# ---------------------------------------------------------------------------
# TestRenderSummary
# ---------------------------------------------------------------------------

class TestRenderSummary(unittest.TestCase):
    def _make_state_obj(self):
        return _make_state(pr_number=5, repo="org/proj")

    def test_zero_count_categories_omitted(self):
        state = self._make_state_obj()
        by_sev = {"high": 0, "medium": 0, "low": 0, "nit": 0}
        by_cat = {}
        rendered = _render_summary(state, by_sev, by_cat, 0, 0, "drift not assessed")
        self.assertIn("(none)", rendered)

    def test_nonzero_categories_present(self):
        state = self._make_state_obj()
        by_sev = {"high": 1, "medium": 0, "low": 0, "nit": 0}
        by_cat = {"smell": 1}
        rendered = _render_summary(state, by_sev, by_cat, 30, 0, "0/1 covered")
        self.assertIn("smell=1", rendered)
        self.assertNotIn("blast=", rendered)

    def test_slop_score_rendered(self):
        state = self._make_state_obj()
        by_sev = {"high": 1, "medium": 0, "low": 0, "nit": 0}
        rendered = _render_summary(state, by_sev, {}, 42, 15, "drift not assessed")
        self.assertIn("Slop-score: 42", rendered)
        self.assertIn("Blast-risk-score: 15", rendered)

    def test_drift_summary_rendered(self):
        state = self._make_state_obj()
        by_sev = {"high": 0, "medium": 0, "low": 0, "nit": 0}
        rendered = _render_summary(state, by_sev, {}, 0, 0, "2/3 covered")
        self.assertIn("2/3 covered", rendered)

    def test_findings_total_rendered(self):
        state = self._make_state_obj()
        by_sev = {"high": 1, "medium": 2, "low": 0, "nit": 0}
        rendered = _render_summary(state, by_sev, {}, 50, 0, "drift not assessed")
        self.assertIn("Findings total**: 3", rendered)


# ---------------------------------------------------------------------------
# TestRenderFindingsMd
# ---------------------------------------------------------------------------

class TestRenderFindingsMd(unittest.TestCase):
    def test_empty_findings_shows_no_findings_message(self):
        state = _make_state(pr_number=7, repo="org/repo", findings=[])
        rendered = _render_findings_md(state)
        self.assertIn("_No findings recorded.", rendered)
        self.assertIn("# PR Review Findings", rendered)

    def test_header_contains_pr_number(self):
        state = _make_state(pr_number=304)
        rendered = _render_findings_md(state)
        self.assertIn("PR #304", rendered)

    def test_header_contains_repo(self):
        state = _make_state(repo="DoosanICA/db-cse-ui-strata")
        rendered = _render_findings_md(state)
        self.assertIn("DoosanICA/db-cse-ui-strata", rendered)

    def test_pr_url_derived_from_state(self):
        state = _make_state(pr_number=304, repo="org/repo")
        rendered = _render_findings_md(state)
        self.assertIn("https://github.com/org/repo/pull/304", rendered)

    def test_pr_url_not_in_state_placeholder(self):
        state = _make_state(pr_number=0, repo="")
        rendered = _render_findings_md(state)
        self.assertIn("(not in state)", rendered)

    def test_populated_findings_rendered(self):
        findings = [
            _make_finding(severity="high", location="src/a.py", category="smell"),
            _make_finding(severity="nit", location="src/b.py", category="drift"),
        ]
        state = _make_state(pr_number=10, repo="foo/bar", findings=findings)
        rendered = _render_findings_md(state)
        # High before nit.
        idx_high = rendered.index("[high]")
        idx_nit = rendered.index("[nit]")
        self.assertLess(idx_high, idx_nit)
        self.assertIn("src/a.py", rendered)
        self.assertIn("src/b.py", rendered)

    def test_findings_sorted_by_severity(self):
        findings = [
            _make_finding(severity="nit", location="a.py"),
            _make_finding(severity="high", location="b.py"),
            _make_finding(severity="medium", location="c.py"),
        ]
        state = _make_state(findings=findings)
        rendered = _render_findings_md(state)
        high_pos = rendered.index("[high]")
        medium_pos = rendered.index("[medium]")
        nit_pos = rendered.index("[nit]")
        self.assertLess(high_pos, medium_pos)
        self.assertLess(medium_pos, nit_pos)

    def test_summary_section_present(self):
        state = _make_state(findings=[_make_finding()])
        rendered = _render_findings_md(state)
        self.assertIn("## Summary", rendered)
        self.assertIn("## Findings", rendered)

    def test_generated_timestamp_present(self):
        state = _make_state()
        rendered = _render_findings_md(state)
        self.assertIn("Generated**:", rendered)

    def test_findings_md_uses_pr_title_when_set(self):
        """F3: pr_title populated in state appears in findings.md header."""
        state = PRReviewState(pr_number=42, repo="org/app", pr_title="MIG-2198 fix")
        rendered = _render_findings_md(state)
        self.assertIn("**PR title**: MIG-2198 fix", rendered)
        self.assertNotIn("(not in state)", rendered.split("**PR title**:")[1].split("\n")[0])

    def test_findings_md_pr_title_placeholder_when_empty(self):
        """F3: empty pr_title falls back to (not in state) placeholder."""
        state = PRReviewState(pr_number=42, repo="org/app", pr_title="")
        rendered = _render_findings_md(state)
        self.assertIn("**PR title**: (not in state)", rendered)


# ---------------------------------------------------------------------------
# TestRunHappyPath
# ---------------------------------------------------------------------------

class TestRunHappyPath(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 42
        self._state = _make_state(
            pr_number=self._pr_number,
            repo="acme/app",
            findings=[
                _make_finding(severity="high", location="src/x.py"),
                _make_finding(severity="medium", location="src/y.py"),
                _make_finding(severity="nit", location="src/z.py"),
            ],
            smells=[{"name": "hedge-defensive", "severity": "low"}],
            blast=[{"symbol": "foo", "filled": False}],
            drift={
                "bullets": [{"id": "B1"}, {"id": "B2"}],
                "coverage_matrix": [{"bullet_id": "B1", "status": "satisfied"}],
            },
        )
        _write_state(self._tmp, self._state)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_returns_status_ok(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["status"], "ok")

    def test_findings_md_created(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertTrue(os.path.isfile(result["findings_path"]))

    def test_findings_path_under_pr_dir(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        expected_dir = os.path.join(
            self._tmp, ".devforge", "pr-reviews", str(self._pr_number)
        )
        self.assertTrue(result["findings_path"].startswith(expected_dir))

    def test_findings_total_correct(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["findings_total"], 3)

    def test_by_severity_correct(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["by_severity"]["high"], 1)
        self.assertEqual(result["by_severity"]["medium"], 1)
        self.assertEqual(result["by_severity"]["nit"], 1)
        self.assertEqual(result["by_severity"]["low"], 0)

    def test_slop_score_present(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        # 30 + 10 + 1 = 41
        self.assertEqual(result["slop_score"], 41)

    def test_blast_risk_score_positive(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertGreater(result["blast_risk_score"], 0)

    def test_drift_summary_computed(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["drift_summary"], "1/2 covered")

    def test_state_path_in_result(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertIn("state.json", result["state_path"])

    def test_findings_md_content(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        with open(result["findings_path"], "r", encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("# PR Review Findings", content)
        self.assertIn("[high]", content)

    def test_idempotent_rerun(self):
        result1 = run(self._tmp, self._pr_number, ".devforge")
        result2 = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result1["status"], "ok")
        self.assertEqual(result2["status"], "ok")
        self.assertEqual(result1["findings_total"], result2["findings_total"])


# ---------------------------------------------------------------------------
# TestRunNoStateFile
# ---------------------------------------------------------------------------

class TestRunNoStateFile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_missing_state_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            run(self._tmp, 999, ".devforge")
        self.assertIn("state.json", str(ctx.exception))

    def test_missing_state_message_mentions_intake(self):
        with self.assertRaises(ValueError) as ctx:
            run(self._tmp, 999, ".devforge")
        self.assertIn("intake", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestRunEmptyFindings
# ---------------------------------------------------------------------------

class TestRunEmptyFindings(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 7
        state = _make_state(pr_number=self._pr_number, repo="org/repo", findings=[])
        _write_state(self._tmp, state)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_findings_md_written(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertTrue(os.path.isfile(result["findings_path"]))

    def test_findings_total_zero(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["findings_total"], 0)

    def test_slop_score_zero(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["slop_score"], 0)

    def test_empty_marker_in_content(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        with open(result["findings_path"], "r", encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("No findings recorded", content)

    def test_by_severity_all_zero(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        for sev in ["high", "medium", "low", "nit"]:
            self.assertEqual(result["by_severity"][sev], 0)


if __name__ == "__main__":
    unittest.main()
