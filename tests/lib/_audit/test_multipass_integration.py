"""Integration tests for the multi-pass pass_count signal.

Covers Tasks 3 and 4 from the pass_count wiring spec:

  Task 3 — ranking nudge (_rank._score_finding pass_bonus):
    - pass_bonus monotonic: pass_count 1 < 2 < 3
    - pass_count=1 and missing key both give unchanged score (equality assertion
      against the pre-nudge value for a known finding)

  Task 4 — integration test:
    - build a small pool list
    - run through merge_passes (real producer) to get findings with real pass_count/tags
    - feed through map_recurring_issues + force_rank/_score_finding WITHOUT error
    - assert multi-pass-confirmed (pass_count=2) ranks ABOVE single-pass (pass_count=1)
      of otherwise-equal base score
    - assert no-op invariant: findings all with pass_count=1 rank in the SAME order
      as the identical findings with the pass_count key removed entirely

Also covers report rendering for the multi-pass Summary line (Task 2 subset):
    - [MULTI-PASS:2] tag renders on Tags line
    - Summary line appears when passes_run >= 2 with correct count
    - Summary line ABSENT (byte-identical) when passes_run == 1

Python 3.8+. Stdlib only. unittest style (matches test_rank.py house style).
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit._rank import _score_finding, force_rank, map_recurring_issues  # noqa: E402
from _audit._merge import merge_passes  # noqa: E402
from _audit._report import render_report  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding(agent="code-reviewer", severity="High", confidence="Certain",
             file_="src/a.py", line=10, pattern="bad pattern", tags=None,
             **extra):
    """Return a minimal valid finding dict."""
    f = {
        "agent": agent,
        "severity": severity,
        "confidence": confidence,
        "file": file_,
        "line": line,
        "pattern": pattern,
        "evidence": "some code here",
        "why": "It is wrong.",
        "remediation": "Fix it.",
        "tags": list(tags) if tags else [],
        "category": "mislogic",
    }
    f.update(extra)
    return f


def _minimal_report_dict(findings=None, passes_run=None):
    """Return a minimal report_dict suitable for render_report."""
    if findings is None:
        findings = []
    d = {
        "mode": "broad",
        "audit_date": "2026-06-01",
        "scope_description": "full codebase",
        "scope_files": ["src/a.py"],
        "agents_run": ["code-reviewer"],
        "agents_skipped": [],
        "findings": findings,
        "top10": [],
        "source_root": "/repo",
        "framework": "pytest",
        "language": "Python",
        "recurring_resolved": [],
        "recurring_unresolved": [],
        "recurring_reviews_consulted": [],
        "discard_counts": {},
        "consensus": {},
        "next_candidates": [],
    }
    if passes_run is not None:
        d["passes_run"] = passes_run
    return d


# ---------------------------------------------------------------------------
# Task 3: ranking pass_bonus monotonicity and single-pass invariant
# ---------------------------------------------------------------------------

class TestPassBonusMonotonic(unittest.TestCase):
    """pass_bonus = 1.0 + 0.25 * (min(pc, 3) - 1)"""

    def _base_score(self):
        """Score without any pass_count key (same as pass_count=1)."""
        f = _finding(severity="High", confidence="Certain")
        return _score_finding(f)

    def test_pass_count_missing_equals_pass_count_1(self):
        """Missing pass_count key → score identical to explicit pass_count=1."""
        f_missing = _finding(severity="High", confidence="Certain")
        f_one = _finding(severity="High", confidence="Certain", pass_count=1)
        self.assertAlmostEqual(_score_finding(f_missing), _score_finding(f_one))

    def test_pass_count_1_score_unchanged(self):
        """pass_count=1 → pass_bonus=1.0 → score unchanged vs no-pass_count."""
        base = self._base_score()
        f = _finding(severity="High", confidence="Certain", pass_count=1)
        # High/Certain base = 4*3*1.0*1.0*1.0 = 12.0
        self.assertAlmostEqual(_score_finding(f), base)
        self.assertAlmostEqual(base, 12.0)

    def test_pass_count_2_score_higher_than_1(self):
        """pass_count=2 → pass_bonus=1.25 → score > pass_count=1."""
        f1 = _finding(severity="High", confidence="Certain", pass_count=1)
        f2 = _finding(severity="High", confidence="Certain", pass_count=2)
        self.assertGreater(_score_finding(f2), _score_finding(f1))

    def test_pass_count_3_score_higher_than_2(self):
        """pass_count=3 → pass_bonus=1.5 → score > pass_count=2."""
        f2 = _finding(severity="High", confidence="Certain", pass_count=2)
        f3 = _finding(severity="High", confidence="Certain", pass_count=3)
        self.assertGreater(_score_finding(f3), _score_finding(f2))

    def test_pass_count_4_capped_at_3(self):
        """pass_count=4 is capped at 3 → same score as pass_count=3."""
        f3 = _finding(severity="High", confidence="Certain", pass_count=3)
        f4 = _finding(severity="High", confidence="Certain", pass_count=4)
        self.assertAlmostEqual(_score_finding(f3), _score_finding(f4))

    def test_exact_values(self):
        """Verify exact multipliers: 1.0, 1.25, 1.5."""
        base = 4.0 * 3.0  # High/Certain, no bonuses from tags
        f1 = _finding(severity="High", confidence="Certain", pass_count=1)
        f2 = _finding(severity="High", confidence="Certain", pass_count=2)
        f3 = _finding(severity="High", confidence="Certain", pass_count=3)
        self.assertAlmostEqual(_score_finding(f1), base * 1.0)
        self.assertAlmostEqual(_score_finding(f2), base * 1.25)
        self.assertAlmostEqual(_score_finding(f3), base * 1.5)

    def test_pass_count_zero_equals_missing(self):
        """pass_count=0 in a raw dict → same score as no pass_count key (no penalty)."""
        f_missing = _finding(severity="High", confidence="Certain")
        f_zero = _finding(severity="High", confidence="Certain", pass_count=0)
        self.assertAlmostEqual(_score_finding(f_missing), _score_finding(f_zero))

    def test_pass_count_negative_equals_missing(self):
        """pass_count=-1 in a raw dict → same score as no pass_count key (no penalty)."""
        f_missing = _finding(severity="High", confidence="Certain")
        f_neg = _finding(severity="High", confidence="Certain", pass_count=-1)
        self.assertAlmostEqual(_score_finding(f_missing), _score_finding(f_neg))


class TestSinglePassNoOpInvariant(unittest.TestCase):
    """All pass_count=1 findings rank identically to findings with no pass_count key."""

    def test_ranking_order_identical(self):
        """force_rank order must be identical whether pass_count=1 or absent."""
        specs = [
            ("Critical", "Certain"),
            ("High", "Certain"),
            ("Medium", "Likely"),
            ("Info", "Certain"),
        ]
        # Findings without pass_count key
        no_key = [
            _finding(severity=sev, confidence=conf,
                     file_="src/f{0}.py".format(i), line=i + 1,
                     pattern="p{0}".format(i))
            for i, (sev, conf) in enumerate(specs)
        ]
        # Same findings with explicit pass_count=1
        with_one = [dict(f, pass_count=1) for f in no_key]

        result_no_key = force_rank(no_key, narrow=False)
        result_with_one = force_rank(with_one, narrow=False)

        # Scores must match exactly
        scores_no_key = [e["score"] for e in result_no_key["top"]]
        scores_with_one = [e["score"] for e in result_with_one["top"]]
        for s1, s2 in zip(scores_no_key, scores_with_one):
            self.assertAlmostEqual(s1, s2)

        # File order (tie-break) must also match
        files_no_key = [e["finding"]["file"] for e in result_no_key["top"]]
        files_with_one = [e["finding"]["file"] for e in result_with_one["top"]]
        self.assertEqual(files_no_key, files_with_one)


# ---------------------------------------------------------------------------
# Task 4: end-to-end pipeline through merge_passes (real producer)
# ---------------------------------------------------------------------------

class TestMergePassesIntegration(unittest.TestCase):
    """Round-trip: pool list → merge_passes → force_rank, no errors."""

    def _make_pool_1(self):
        return [
            _finding(agent="code-reviewer", severity="High",
                     confidence="Certain", file_="src/a.py", line=10,
                     pattern="null check missing"),
            _finding(agent="architect", severity="Medium",
                     confidence="Likely", file_="src/b.py", line=20,
                     pattern="tight coupling in service"),
        ]

    def _make_pool_2(self):
        # Same findings as pool_1 (same file+line proximity) — will merge into
        # pass_count=2 clusters. Different agents to exercise cross-agent too.
        return [
            _finding(agent="security-reviewer", severity="High",
                     confidence="Likely", file_="src/a.py", line=11,
                     pattern="null check missing"),   # line 11, within TOL=3
            _finding(agent="qa-engineer", severity="Medium",
                     confidence="Speculative", file_="src/b.py", line=20,
                     pattern="tight coupling in service"),
        ]

    def test_merge_produces_pass_count(self):
        """merge_passes sets pass_count on each merged finding."""
        pools = [self._make_pool_1(), self._make_pool_2()]
        merged = merge_passes(pools)
        self.assertGreater(len(merged), 0)
        for f in merged:
            self.assertIn("pass_count", f)
            self.assertIsInstance(f["pass_count"], int)
            self.assertGreaterEqual(f["pass_count"], 1)

    def test_merge_corroborated_finding_has_pass_count_2(self):
        """src/a.py:10-11 (TOL=3) merges into pass_count=2."""
        pools = [self._make_pool_1(), self._make_pool_2()]
        merged = merge_passes(pools)
        a_findings = [f for f in merged if f.get("file") == "src/a.py"]
        self.assertEqual(len(a_findings), 1)
        self.assertEqual(a_findings[0]["pass_count"], 2)

    def test_merge_corroborated_finding_has_multipass_tag(self):
        """pass_count=2 implies [MULTI-PASS:2] in tags."""
        pools = [self._make_pool_1(), self._make_pool_2()]
        merged = merge_passes(pools)
        a_findings = [f for f in merged if f.get("file") == "src/a.py"]
        self.assertIn("[MULTI-PASS:2]", a_findings[0].get("tags", []))

    def test_force_rank_runs_on_merged_without_error(self):
        """force_rank must accept merged findings (which carry pass_count) cleanly."""
        pools = [self._make_pool_1(), self._make_pool_2()]
        merged = merge_passes(pools)
        # Should not raise
        result = force_rank(merged, narrow=False)
        self.assertIn("top", result)
        self.assertGreater(len(result["top"]), 0)

    def test_map_recurring_runs_on_merged_without_error(self):
        """map_recurring_issues must accept merged findings (which carry pass_count)."""
        pools = [self._make_pool_1(), self._make_pool_2()]
        merged = merge_passes(pools)
        past = [{"file": "src/a.py", "fingerprint": "null check missing"}]
        result = map_recurring_issues(merged, past)
        self.assertIn("findings", result)

    def test_multipass_finding_ranks_above_singlepass_equal_base(self):
        """A pass_count=2 finding ranks above pass_count=1 of equal base score.

        Equal base: same severity, confidence, no tags other than [MULTI-PASS:k].
        Multi-pass cluster: two separate passes of the same finding on src/a.py.
        Single-pass: one occurrence of the same severity/confidence on src/c.py.
        """
        # Two pools: pool_1 has findings at a.py:10 AND c.py:50.
        # pool_2 has ONLY a finding at a.py:10 (same location = merged).
        # => a.py:10 gets pass_count=2; c.py:50 stays pass_count=1.
        pool_1 = [
            _finding(agent="code-reviewer", severity="High",
                     confidence="Certain", file_="src/a.py", line=10,
                     pattern="equal base pattern"),
            _finding(agent="code-reviewer", severity="High",
                     confidence="Certain", file_="src/c.py", line=50,
                     pattern="equal base pattern single pass"),
        ]
        pool_2 = [
            _finding(agent="code-reviewer", severity="High",
                     confidence="Certain", file_="src/a.py", line=10,
                     pattern="equal base pattern"),
        ]
        merged = merge_passes([pool_1, pool_2])

        a_entries = [f for f in merged if f.get("file") == "src/a.py"]
        c_entries = [f for f in merged if f.get("file") == "src/c.py"]
        self.assertEqual(len(a_entries), 1)
        self.assertEqual(len(c_entries), 1)

        a_finding = a_entries[0]
        c_finding = c_entries[0]

        # Verify setup: a has pass_count=2, c has pass_count=1
        self.assertEqual(a_finding["pass_count"], 2)
        self.assertEqual(c_finding["pass_count"], 1)

        score_a = _score_finding(a_finding)
        score_c = _score_finding(c_finding)
        self.assertGreater(score_a, score_c,
                           "pass_count=2 finding should score higher than pass_count=1")

        # Also verify via force_rank ordering
        result = force_rank(merged, narrow=False)
        top_files = [e["finding"]["file"] for e in result["top"]]
        idx_a = top_files.index("src/a.py")
        idx_c = top_files.index("src/c.py")
        self.assertLess(idx_a, idx_c,
                        "src/a.py (pass_count=2) should rank before src/c.py (pass_count=1)")

    def test_noop_invariant_single_pass_identical_order(self):
        """findings all pass_count=1 rank identically to findings with no pass_count key."""
        # Use a single pool (no merging) so pass_count is absent from results.
        pool = [
            _finding(agent="code-reviewer", severity="Critical",
                     confidence="Certain", file_="src/x.py", line=1),
            _finding(agent="code-reviewer", severity="High",
                     confidence="Likely", file_="src/y.py", line=2),
            _finding(agent="code-reviewer", severity="Medium",
                     confidence="Certain", file_="src/z.py", line=3),
        ]
        # merge_passes with a single pool: each finding gets pass_count=1
        merged_single = merge_passes([pool])

        # Baseline: rank the original pool (no pass_count key)
        result_no_key = force_rank(pool, narrow=False)
        # After merge: rank the merged result (pass_count=1 for all)
        result_merged = force_rank(merged_single, narrow=False)

        scores_no_key = [e["score"] for e in result_no_key["top"]]
        scores_merged = [e["score"] for e in result_merged["top"]]

        self.assertEqual(len(scores_no_key), len(scores_merged))
        for s1, s2 in zip(scores_no_key, scores_merged):
            self.assertAlmostEqual(s1, s2)

        files_no_key = [e["finding"]["file"] for e in result_no_key["top"]]
        files_merged = [e["finding"]["file"] for e in result_merged["top"]]
        self.assertEqual(files_no_key, files_merged)


# ---------------------------------------------------------------------------
# Task 2 (report rendering) — multi-pass tag on Tags line + Summary line guard
# ---------------------------------------------------------------------------

class TestReportMultipassTag(unittest.TestCase):
    """[MULTI-PASS:k] renders on the Tags / Confidence line."""

    def test_multipass_tag_renders_in_finding_body(self):
        """A finding with [MULTI-PASS:2] in tags must render that tag in output."""
        finding = _finding(
            severity="High", confidence="Certain",
            file_="src/a.py", line=10,
            pattern="some issue",
            tags=["[MULTI-PASS:2]"],
        )
        report = render_report(_minimal_report_dict(findings=[finding]))
        self.assertIn("[MULTI-PASS:2]", report)

    def test_multipass_tag_on_confidence_line(self):
        """Tags string appears on the Confidence line (same line as Confidence:)."""
        finding = _finding(
            severity="High", confidence="Certain",
            file_="src/a.py", line=10,
            pattern="some issue",
            tags=["[MULTI-PASS:2]"],
        )
        report = render_report(_minimal_report_dict(findings=[finding]))
        # The confidence line format: "  Confidence: Certain  Tags: [MULTI-PASS:2]"
        conf_line = next(
            (ln for ln in report.splitlines() if "Confidence:" in ln),
            None,
        )
        self.assertIsNotNone(conf_line)
        self.assertIn("[MULTI-PASS:2]", conf_line)

    def test_multipass_tag_alongside_cross_agent(self):
        """Both [MULTI-PASS:2] and [CROSS-AGENT] render when both are in tags."""
        finding = _finding(
            severity="High", confidence="Certain",
            file_="src/a.py", line=10,
            pattern="some issue",
            tags=["[CROSS-AGENT]", "[MULTI-PASS:2]"],
        )
        report = render_report(_minimal_report_dict(findings=[finding]))
        self.assertIn("[CROSS-AGENT]", report)
        self.assertIn("[MULTI-PASS:2]", report)


class TestReportMultipassSummaryLine(unittest.TestCase):
    """Summary line for passes_run is guarded: only appears when passes_run >= 2."""

    def _passes_line(self, report_text):
        # type: (str) -> str
        """Return the line containing 'Passes run:' or empty string."""
        for ln in report_text.splitlines():
            if "Passes run:" in ln:
                return ln
        return ""

    def test_single_pass_no_passes_line(self):
        """Default (no passes_run key) → no 'Passes run:' line in Summary."""
        report = render_report(_minimal_report_dict())
        self.assertEqual(self._passes_line(report), "")

    def test_passes_run_1_explicit_no_passes_line(self):
        """Explicit passes_run=1 → no 'Passes run:' line."""
        report = render_report(_minimal_report_dict(passes_run=1))
        self.assertEqual(self._passes_line(report), "")

    def test_passes_run_2_shows_passes_line(self):
        """passes_run=2 → 'Passes run: 2 ...' line appears in Summary."""
        report = render_report(_minimal_report_dict(passes_run=2))
        line = self._passes_line(report)
        self.assertNotEqual(line, "")
        self.assertIn("Passes run: 2", line)

    def test_passes_run_3_shows_passes_line(self):
        """passes_run=3 → 'Passes run: 3 ...' line appears."""
        report = render_report(_minimal_report_dict(passes_run=3))
        self.assertIn("Passes run: 3", report)

    def test_multipass_confirmed_count_zero_when_no_multipass_findings(self):
        """passes_run=2 but no findings have pass_count >= 2 → count is 0."""
        finding = _finding(tags=[])  # no pass_count key
        report = render_report(_minimal_report_dict(
            findings=[finding], passes_run=2
        ))
        line = self._passes_line(report)
        self.assertIn("Multi-pass-confirmed findings: 0", line)

    def test_multipass_confirmed_count_correct(self):
        """passes_run=2, one finding has pass_count=2 → count is 1."""
        f_multi = _finding(file_="src/a.py", line=1, pattern="multi",
                           pass_count=2, tags=["[MULTI-PASS:2]"])
        f_single = _finding(file_="src/b.py", line=2, pattern="single")
        report = render_report(_minimal_report_dict(
            findings=[f_multi, f_single], passes_run=2
        ))
        line = self._passes_line(report)
        self.assertIn("Multi-pass-confirmed findings: 1", line)

    def test_multipass_confirmed_counts_multiple(self):
        """passes_run=2, two findings have pass_count >= 2 → count is 2."""
        f1 = _finding(file_="src/a.py", line=1, pattern="multi-1",
                      pass_count=2, tags=["[MULTI-PASS:2]"])
        f2 = _finding(file_="src/b.py", line=2, pattern="multi-2",
                      pass_count=3, tags=["[MULTI-PASS:3]"])
        f3 = _finding(file_="src/c.py", line=3, pattern="single")
        report = render_report(_minimal_report_dict(
            findings=[f1, f2, f3], passes_run=2
        ))
        line = self._passes_line(report)
        self.assertIn("Multi-pass-confirmed findings: 2", line)

    def test_single_pass_report_byte_identical_to_no_passes_run(self):
        """When passes_run=1, the report is byte-identical to the default (no key).

        This is the critical no-op invariant check.
        """
        finding = _finding(severity="High", confidence="Certain",
                           file_="src/a.py", line=10, pattern="issue")
        report_default = render_report(_minimal_report_dict(findings=[finding]))
        report_explicit1 = render_report(
            _minimal_report_dict(findings=[finding], passes_run=1)
        )
        self.assertEqual(report_default, report_explicit1)


# ---------------------------------------------------------------------------
# Schema: pass_count field on Finding dataclass
# ---------------------------------------------------------------------------

class TestFindingPassCount(unittest.TestCase):
    """Schema-level tests for the pass_count field."""

    def _make_finding(self, **overrides):
        from _audit.findings_schema import Finding
        defaults = dict(
            finding_id="F-001",
            agent="code-reviewer",
            severity="High",
            file="src/main.py",
            line=42,
            title="Off-by-one",
            explanation="Loop runs once too many.",
            suggested_fix="Change <= to <.",
            references=[],
            source_pass="mislogic-hunt",
        )
        defaults.update(overrides)
        return Finding(**defaults)

    def test_default_pass_count_is_1(self):
        """Omitting pass_count defaults to 1."""
        f = self._make_finding()
        self.assertEqual(f.pass_count, 1)

    def test_valid_int_1_accepted(self):
        f = self._make_finding(pass_count=1)
        self.assertEqual(f.pass_count, 1)

    def test_valid_int_2_accepted(self):
        f = self._make_finding(pass_count=2)
        self.assertEqual(f.pass_count, 2)

    def test_valid_large_int_accepted(self):
        f = self._make_finding(pass_count=99)
        self.assertEqual(f.pass_count, 99)

    def test_pass_count_0_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._make_finding(pass_count=0)
        self.assertIn("pass_count", str(ctx.exception))

    def test_pass_count_negative_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._make_finding(pass_count=-1)
        self.assertIn("pass_count", str(ctx.exception))

    def test_pass_count_bool_rejected(self):
        """True/False are bool, which are subclasses of int — must reject."""
        with self.assertRaises(ValueError) as ctx:
            self._make_finding(pass_count=True)
        self.assertIn("pass_count", str(ctx.exception))

    def test_pass_count_bool_false_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._make_finding(pass_count=False)
        self.assertIn("pass_count", str(ctx.exception))

    def test_pass_count_float_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._make_finding(pass_count=1.5)
        self.assertIn("pass_count", str(ctx.exception))

    def test_pass_count_string_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._make_finding(pass_count="2")
        self.assertIn("pass_count", str(ctx.exception))

    def test_without_pass_count_arg_still_works(self):
        """Constructing Finding without pass_count kwarg must succeed (backward compat)."""
        import dataclasses
        f = self._make_finding()
        d = dataclasses.asdict(f)
        self.assertIn("pass_count", d)
        self.assertEqual(d["pass_count"], 1)

    def test_round_trip_with_pass_count_2(self):
        """pass_count=2 survives asdict → reconstruct."""
        import dataclasses
        from _audit.findings_schema import Finding
        f = self._make_finding(pass_count=2)
        d = dataclasses.asdict(f)
        self.assertEqual(d["pass_count"], 2)
        reconstructed = Finding(**d)
        self.assertEqual(reconstructed.pass_count, 2)


if __name__ == "__main__":
    unittest.main()
