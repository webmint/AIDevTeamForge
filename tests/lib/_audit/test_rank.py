"""Tests for src/devforge/lib/_audit/_rank.py.

Coverage:
  force_rank:
    - Score math exact for known findings (verify multiplication)
    - Ordering descending
    - Top 10 vs Top 5 (--narrow)
    - Cross-agent bonus applied
    - Recurring bonuses applied

  map_recurring_issues:
    - RESOLVED: fingerprint not in any current finding → status RESOLVED
    - [RECURRING]: fingerprint in current finding at SAME file → +1 sev, tag
    - [RECURRING-SPREAD]: fingerprint in current finding at DIFFERENT file → +2 sev, tag
    - Exact-substring only — partial/fuzzy miss → RESOLVED
    - Both file AND fingerprint must match for RECURRING
    - Only fingerprint matches (different file) → RECURRING-SPREAD
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit._rank import (  # noqa: E402
    _score_finding,
    force_rank,
    map_recurring_issues,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(agent="code-reviewer", severity="High", confidence="Certain",
                  file="src/auth.py", line=10, pattern="Bad pattern",
                  tags=None):
    return {
        "agent": agent,
        "severity": severity,
        "confidence": confidence,
        "file": file,
        "line": line,
        "pattern": pattern,
        "evidence": "some code",
        "why": "Bad.",
        "remediation": "Fix.",
        "tags": list(tags) if tags else [],
    }


# ---------------------------------------------------------------------------
# _score_finding
# ---------------------------------------------------------------------------

class TestScoreFinding(unittest.TestCase):
    def test_critical_certain_no_bonuses(self):
        f = _make_finding(severity="Critical", confidence="Certain")
        # 8 * 3 * 1.0 * 1.0 = 24.0
        self.assertAlmostEqual(_score_finding(f), 24.0)

    def test_high_likely_no_bonuses(self):
        f = _make_finding(severity="High", confidence="Likely")
        # 4 * 2 * 1.0 * 1.0 = 8.0
        self.assertAlmostEqual(_score_finding(f), 8.0)

    def test_medium_speculative_no_bonuses(self):
        f = _make_finding(severity="Medium", confidence="Speculative")
        # 2 * 1 * 1.0 * 1.0 = 2.0
        self.assertAlmostEqual(_score_finding(f), 2.0)

    def test_info_certain_no_bonuses(self):
        f = _make_finding(severity="Info", confidence="Certain")
        # 1 * 3 * 1.0 * 1.0 = 3.0
        self.assertAlmostEqual(_score_finding(f), 3.0)

    def test_cross_agent_bonus(self):
        f = _make_finding(severity="High", confidence="Certain", tags=["[CROSS-AGENT]"])
        # 4 * 3 * 1.5 * 1.0 = 18.0
        self.assertAlmostEqual(_score_finding(f), 18.0)

    def test_recurring_bonus(self):
        f = _make_finding(severity="High", confidence="Certain", tags=["[RECURRING]"])
        # 4 * 3 * 1.0 * 1.5 = 18.0
        self.assertAlmostEqual(_score_finding(f), 18.0)

    def test_recurring_spread_bonus(self):
        f = _make_finding(severity="High", confidence="Certain", tags=["[RECURRING-SPREAD]"])
        # 4 * 3 * 1.0 * 2.0 = 24.0
        self.assertAlmostEqual(_score_finding(f), 24.0)

    def test_cross_agent_and_recurring_both_applied(self):
        f = _make_finding(
            severity="Critical", confidence="Certain",
            tags=["[CROSS-AGENT]", "[RECURRING]"]
        )
        # 8 * 3 * 1.5 * 1.5 = 54.0
        self.assertAlmostEqual(_score_finding(f), 54.0)

    def test_cross_agent_and_recurring_spread(self):
        f = _make_finding(
            severity="Critical", confidence="Certain",
            tags=["[CROSS-AGENT]", "[RECURRING-SPREAD]"]
        )
        # 8 * 3 * 1.5 * 2.0 = 72.0
        self.assertAlmostEqual(_score_finding(f), 72.0)


# ---------------------------------------------------------------------------
# force_rank
# ---------------------------------------------------------------------------

class TestForceRank(unittest.TestCase):
    def _make_varied_findings(self):
        """Return 12 findings with distinct severity/confidence combos."""
        findings = []
        specs = [
            ("Critical", "Certain"),    # score 24 → highest
            ("Critical", "Likely"),     # score 16
            ("Critical", "Speculative"),# score 8
            ("High", "Certain"),        # score 12
            ("High", "Likely"),         # score 8
            ("High", "Speculative"),    # score 4
            ("Medium", "Certain"),      # score 6
            ("Medium", "Likely"),       # score 4
            ("Medium", "Speculative"),  # score 2
            ("Info", "Certain"),        # score 3
            ("Info", "Likely"),         # score 2
            ("Info", "Speculative"),    # score 1
        ]
        for i, (sev, conf) in enumerate(specs):
            findings.append(_make_finding(
                severity=sev,
                confidence=conf,
                file="src/file{0}.py".format(i),
                line=i + 1,
            ))
        return findings

    def test_top10_returns_10_findings(self):
        findings = self._make_varied_findings()
        result = force_rank(findings, narrow=False)
        self.assertEqual(len(result["top"]), 10)

    def test_top5_narrow_returns_5_findings(self):
        findings = self._make_varied_findings()
        result = force_rank(findings, narrow=True)
        self.assertEqual(len(result["top"]), 5)

    def test_ordering_descending_by_score(self):
        findings = self._make_varied_findings()
        result = force_rank(findings, narrow=False)
        scores = [entry["score"] for entry in result["top"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_highest_score_first(self):
        findings = self._make_varied_findings()
        result = force_rank(findings, narrow=False)
        # Critical + Certain = 24.0 should be first
        self.assertAlmostEqual(result["top"][0]["score"], 24.0)

    def test_finding_dict_present_in_output(self):
        findings = [_make_finding(severity="High", confidence="Certain")]
        result = force_rank(findings, narrow=False)
        self.assertIn("finding", result["top"][0])
        self.assertIn("score", result["top"][0])

    def test_fewer_than_10_findings_returns_all(self):
        findings = [_make_finding(severity="High", confidence="Certain")]
        result = force_rank(findings, narrow=False)
        self.assertEqual(len(result["top"]), 1)

    def test_empty_findings_returns_empty(self):
        result = force_rank([], narrow=False)
        self.assertEqual(result["top"], [])

    def test_cross_agent_bonus_changes_rank(self):
        # Two findings: one High/Certain (score=12), one Medium/Certain+CROSS-AGENT (score=6*1.5=9)
        # Cross-agent doesn't make Medium rank above High here
        f_high = _make_finding(severity="High", confidence="Certain", file="src/a.py")
        f_med_cross = _make_finding(
            severity="Medium", confidence="Certain",
            file="src/b.py", tags=["[CROSS-AGENT]"]
        )
        result = force_rank([f_high, f_med_cross], narrow=False)
        self.assertAlmostEqual(result["top"][0]["score"], 12.0)
        self.assertAlmostEqual(result["top"][1]["score"], 9.0)

    def test_score_includes_recurring_spread_bonus(self):
        f = _make_finding(
            severity="High", confidence="Certain",
            tags=["[RECURRING-SPREAD]"]
        )
        result = force_rank([f], narrow=False)
        # 4 * 3 * 1.0 * 2.0 = 24.0
        self.assertAlmostEqual(result["top"][0]["score"], 24.0)

    def test_deterministic_tie_break_by_file(self):
        # Two identical scores, different files → alphabetically first file wins
        f1 = _make_finding(severity="High", confidence="Certain", file="src/z.py", line=1)
        f2 = _make_finding(severity="High", confidence="Certain", file="src/a.py", line=1)
        result = force_rank([f1, f2], narrow=False)
        # "src/a.py" comes before "src/z.py" alphabetically
        self.assertEqual(result["top"][0]["finding"]["file"], "src/a.py")
        self.assertEqual(result["top"][1]["finding"]["file"], "src/z.py")


# ---------------------------------------------------------------------------
# force_rank — (file, line) deduplication
# ---------------------------------------------------------------------------

class TestForceRankDedup(unittest.TestCase):
    """Deduplication-by-(file,line) behaviour added to force_rank."""

    def test_same_location_keeps_higher_scored(self):
        # Two findings at identical (file, line); different patterns and scores.
        # Higher-scored one must appear in top; lower-scored must be absent.
        f_high = _make_finding(
            severity="Critical", confidence="Certain",
            file="src/foo.py", line=245,
            pattern="null pointer dereference — access without check",
        )
        f_low = _make_finding(
            severity="High", confidence="Likely",
            file="src/foo.py", line=245,
            pattern="potential NPE via unguarded member access",
        )
        # f_high score = 8*3 = 24; f_low score = 4*2 = 8
        result = force_rank([f_high, f_low], narrow=False)
        top_patterns = [e["finding"]["pattern"] for e in result["top"]]
        self.assertIn(f_high["pattern"], top_patterns)
        self.assertNotIn(f_low["pattern"], top_patterns)

    def test_freed_slot_filled_by_next_distinct_location(self):
        # 4 findings total; two share (file, line).  With top_n=3, the
        # slot freed by the duplicate must be filled by the 4th finding
        # so that top still has 3 entries.
        f1 = _make_finding(
            severity="Critical", confidence="Certain",
            file="src/a.py", line=10, pattern="pattern A",
        )
        # f2 same location as f1, lower score — should be skipped
        f2 = _make_finding(
            severity="High", confidence="Likely",
            file="src/a.py", line=10, pattern="pattern A dup",
        )
        f3 = _make_finding(
            severity="High", confidence="Certain",
            file="src/b.py", line=20, pattern="pattern B",
        )
        f4 = _make_finding(
            severity="Medium", confidence="Certain",
            file="src/c.py", line=30, pattern="pattern C",
        )
        # Scores: f1=24, f3=12, f4=6, f2=8
        # Without dedup top-3 would be f1, f3, f2 (scores 24,12,8).
        # With dedup: f2 skipped → f4 fills the slot → top=[f1,f3,f4].
        # Actually sorted order: f1(24), f3(12), f2(8), f4(6).
        # After dedup: f1 taken, f3 taken, f2 skipped (same loc as f1),
        # f4 taken → top has 3 entries: f1, f3, f4.
        result = force_rank([f1, f2, f3, f4], narrow=False)
        # Slice N is effectively 10 here; but we check the dedup logic:
        top_patterns = [e["finding"]["pattern"] for e in result["top"]]
        self.assertIn("pattern A", top_patterns)
        self.assertNotIn("pattern A dup", top_patterns)
        self.assertIn("pattern B", top_patterns)
        self.assertIn("pattern C", top_patterns)
        # All three distinct locations present
        self.assertEqual(len(result["top"]), 3)

    def test_freed_slot_fills_to_target_length(self):
        # 11 findings where two of the top-scored share (file, line).
        # top_n=10 should still yield 10 entries (slot filled from 11th).
        findings = []
        # Finding 0+1 share location; rest are distinct
        findings.append(_make_finding(
            severity="Critical", confidence="Certain",
            file="src/dup.py", line=1, pattern="dup-high",
        ))
        findings.append(_make_finding(
            severity="Critical", confidence="Likely",
            file="src/dup.py", line=1, pattern="dup-low",
        ))
        for i in range(9):
            findings.append(_make_finding(
                severity="High", confidence="Certain",
                file="src/file{0}.py".format(i), line=i + 100,
                pattern="distinct {0}".format(i),
            ))
        result = force_rank(findings, narrow=False)
        self.assertEqual(len(result["top"]), 10)
        # The dup-low pattern should not appear
        top_patterns = [e["finding"]["pattern"] for e in result["top"]]
        self.assertNotIn("dup-low", top_patterns)
        self.assertIn("dup-high", top_patterns)

    def test_distinct_locations_not_collapsed(self):
        # Same file, DIFFERENT lines — both must appear.
        f1 = _make_finding(
            severity="High", confidence="Certain",
            file="src/foo.py", line=10, pattern="issue at line 10",
        )
        f2 = _make_finding(
            severity="High", confidence="Certain",
            file="src/foo.py", line=20, pattern="issue at line 20",
        )
        result = force_rank([f1, f2], narrow=False)
        self.assertEqual(len(result["top"]), 2)
        top_patterns = [e["finding"]["pattern"] for e in result["top"]]
        self.assertIn("issue at line 10", top_patterns)
        self.assertIn("issue at line 20", top_patterns)

    def test_determinism_same_input_same_order(self):
        # Two calls with the same input must produce identical top order.
        findings = []
        for i in range(6):
            findings.append(_make_finding(
                severity="High", confidence="Certain",
                file="src/f{0}.py".format(i), line=i,
                pattern="pat {0}".format(i),
            ))
        # Add a duplicate-location pair
        findings.append(_make_finding(
            severity="Critical", confidence="Certain",
            file="src/f0.py", line=0, pattern="pat 0 dup",
        ))
        result1 = force_rank(findings, narrow=False)
        result2 = force_rank(findings, narrow=False)
        orders1 = [(e["finding"]["file"], e["finding"]["line"]) for e in result1["top"]]
        orders2 = [(e["finding"]["file"], e["finding"]["line"]) for e in result2["top"]]
        self.assertEqual(orders1, orders2)

    def test_narrow_top5_also_dedups(self):
        # With narrow=True (top 5), duplicate locations are still removed.
        findings = []
        # Two findings at the same location
        findings.append(_make_finding(
            severity="Critical", confidence="Certain",
            file="src/dup.py", line=1, pattern="dup-high narrow",
        ))
        findings.append(_make_finding(
            severity="High", confidence="Certain",
            file="src/dup.py", line=1, pattern="dup-low narrow",
        ))
        # 4 more distinct locations
        for i in range(4):
            findings.append(_make_finding(
                severity="High", confidence="Certain",
                file="src/other{0}.py".format(i), line=i + 50,
                pattern="other {0}".format(i),
            ))
        result = force_rank(findings, narrow=True)
        self.assertEqual(len(result["top"]), 5)
        top_patterns = [e["finding"]["pattern"] for e in result["top"]]
        self.assertIn("dup-high narrow", top_patterns)
        self.assertNotIn("dup-low narrow", top_patterns)

    def test_finding_missing_line_not_deduped(self):
        # A finding with no line should not be collapsed with another
        # no-line finding — each occupies its own slot.
        f1 = _make_finding(
            severity="High", confidence="Certain",
            file="src/foo.py", line=None, pattern="no-line-1",
        )
        f2 = _make_finding(
            severity="High", confidence="Certain",
            file="src/foo.py", line=None, pattern="no-line-2",
        )
        # Force line=None explicitly (helper defaults to int; override)
        f1["line"] = None
        f2["line"] = None
        result = force_rank([f1, f2], narrow=False)
        self.assertEqual(len(result["top"]), 2)
        top_patterns = [e["finding"]["pattern"] for e in result["top"]]
        self.assertIn("no-line-1", top_patterns)
        self.assertIn("no-line-2", top_patterns)

    def test_finding_missing_file_not_deduped(self):
        # A finding with no file is not deduplicated against another no-file finding.
        f1 = _make_finding(
            severity="High", confidence="Certain",
            file=None, line=10, pattern="no-file-1",
        )
        f2 = _make_finding(
            severity="High", confidence="Certain",
            file=None, line=10, pattern="no-file-2",
        )
        f1["file"] = None
        f2["file"] = None
        result = force_rank([f1, f2], narrow=False)
        self.assertEqual(len(result["top"]), 2)
        top_patterns = [e["finding"]["pattern"] for e in result["top"]]
        self.assertIn("no-file-1", top_patterns)
        self.assertIn("no-file-2", top_patterns)

    def test_finding_line_minus1_not_deduped(self):
        # line == -1 is the "unspecified" sentinel — two such findings in the
        # same file are NOT confirmed co-located, so neither is dropped.
        f1 = _make_finding(
            severity="High", confidence="Certain",
            file="src/foo.py", line=10, pattern="sentinel-1",
        )
        f2 = _make_finding(
            severity="High", confidence="Certain",
            file="src/foo.py", line=10, pattern="sentinel-2",
        )
        f1["line"] = -1
        f2["line"] = -1
        result = force_rank([f1, f2], narrow=False)
        self.assertEqual(len(result["top"]), 2)
        top_patterns = [e["finding"]["pattern"] for e in result["top"]]
        self.assertIn("sentinel-1", top_patterns)
        self.assertIn("sentinel-2", top_patterns)


# ---------------------------------------------------------------------------
# map_recurring_issues
# ---------------------------------------------------------------------------

class TestMapRecurringIssues(unittest.TestCase):
    def test_resolved_when_no_match(self):
        findings = [_make_finding(file="src/auth.py", pattern="Some pattern")]
        past = [{"file": "src/auth.py", "fingerprint": "completely different issue"}]
        result = map_recurring_issues(findings, past)
        self.assertEqual(len(result["recurring_status"]), 1)
        self.assertEqual(result["recurring_status"][0]["status"], "RESOLVED")

    def test_resolved_when_no_findings_match(self):
        past = [{"file": "src/old.py", "fingerprint": "sql injection"}]
        findings = [_make_finding(file="src/new.py", pattern="XSS problem")]
        result = map_recurring_issues(findings, past)
        self.assertEqual(result["recurring_status"][0]["status"], "RESOLVED")

    def test_recurring_same_file(self):
        # fingerprint is substring of pattern, file matches
        findings = [_make_finding(file="src/auth.py", pattern="sql injection flaw")]
        past = [{"file": "src/auth.py", "fingerprint": "sql injection"}]
        result = map_recurring_issues(findings, past)
        self.assertEqual(result["recurring_status"][0]["status"], "RECURRING")
        tagged = result["findings"][0]
        self.assertIn("[RECURRING]", tagged["tags"])

    def test_recurring_severity_bumped_one_level(self):
        findings = [_make_finding(
            file="src/auth.py", pattern="sql injection", severity="High"
        )]
        past = [{"file": "src/auth.py", "fingerprint": "sql injection"}]
        result = map_recurring_issues(findings, past)
        self.assertEqual(result["findings"][0]["severity"], "Critical")

    def test_recurring_spread_different_file(self):
        # fingerprint matches pattern but file is DIFFERENT
        findings = [_make_finding(file="src/newfile.py", pattern="sql injection problem")]
        past = [{"file": "src/auth.py", "fingerprint": "sql injection"}]
        result = map_recurring_issues(findings, past)
        self.assertEqual(result["recurring_status"][0]["status"], "RECURRING-SPREAD")
        self.assertIn("[RECURRING-SPREAD]", result["findings"][0]["tags"])

    def test_recurring_spread_severity_bumped_two_levels(self):
        findings = [_make_finding(
            file="src/new.py", pattern="sql injection problem", severity="High"
        )]
        past = [{"file": "src/auth.py", "fingerprint": "sql injection"}]
        result = map_recurring_issues(findings, past)
        # High + 2 levels = Critical
        self.assertEqual(result["findings"][0]["severity"], "Critical")

    def test_exact_substring_only_not_fuzzy(self):
        # "sql injectin" (typo) is NOT a substring of "sql injection"
        findings = [_make_finding(file="src/auth.py", pattern="sql injection")]
        past = [{"file": "src/auth.py", "fingerprint": "sql injectin"}]
        result = map_recurring_issues(findings, past)
        self.assertEqual(result["recurring_status"][0]["status"], "RESOLVED")

    def test_originals_not_mutated(self):
        original_finding = _make_finding(file="src/auth.py", pattern="sql injection")
        original_tags_before = list(original_finding["tags"])
        past = [{"file": "src/auth.py", "fingerprint": "sql injection"}]
        map_recurring_issues([original_finding], past)
        # The original should NOT be mutated (map_recurring_issues works on copies)
        self.assertEqual(original_finding["tags"], original_tags_before)

    def test_multiple_past_entries(self):
        findings = [
            _make_finding(file="src/auth.py", pattern="sql injection flaw"),
            _make_finding(file="src/api.py", pattern="xss vulnerability here"),
        ]
        past = [
            {"file": "src/auth.py", "fingerprint": "sql injection"},
            {"file": "src/api.py", "fingerprint": "xss vulnerability"},
            {"file": "src/old.py", "fingerprint": "buffer overflow"},
        ]
        result = map_recurring_issues(findings, past)
        statuses = {e["status"] for e in result["recurring_status"]}
        self.assertIn("RECURRING", statuses)
        self.assertIn("RESOLVED", statuses)

    def test_empty_past_findings(self):
        findings = [_make_finding()]
        result = map_recurring_issues(findings, [])
        self.assertEqual(result["recurring_status"], [])
        # Finding unchanged
        self.assertEqual(result["findings"][0]["tags"], [])

    def test_empty_current_findings(self):
        past = [{"file": "src/auth.py", "fingerprint": "sql injection"}]
        result = map_recurring_issues([], past)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["recurring_status"][0]["status"], "RESOLVED")

    def test_recurring_spread_severity_capped_at_critical(self):
        findings = [_make_finding(
            file="src/new.py", pattern="sql injection problem", severity="Critical"
        )]
        past = [{"file": "src/auth.py", "fingerprint": "sql injection"}]
        result = map_recurring_issues(findings, past)
        # Critical + 2 → still Critical
        self.assertEqual(result["findings"][0]["severity"], "Critical")

    def test_file_substring_match(self):
        # past file = "auth" should match "src/auth.py" (substring)
        findings = [_make_finding(file="src/auth.py", pattern="token leak")]
        past = [{"file": "auth", "fingerprint": "token leak"}]
        result = map_recurring_issues(findings, past)
        self.assertEqual(result["recurring_status"][0]["status"], "RECURRING")

    # Fix 4 regression tests: empty/missing past_file → [RECURRING] not [RECURRING-SPREAD]

    def test_empty_past_file_gives_recurring_not_spread(self):
        # past entry with file="" + matching fingerprint → [RECURRING] (+1 sev),
        # NOT [RECURRING-SPREAD] (+2 sev).  An empty past_file cannot confirm that
        # the issue spread to a different file.
        findings = [_make_finding(file="src/auth.py", pattern="sql injection flaw", severity="High")]
        past = [{"file": "", "fingerprint": "sql injection"}]
        result = map_recurring_issues(findings, past)
        self.assertEqual(result["recurring_status"][0]["status"], "RECURRING")
        tagged = result["findings"][0]
        self.assertIn("[RECURRING]", tagged["tags"])
        self.assertNotIn("[RECURRING-SPREAD]", tagged["tags"])
        # Severity bumped by 1 (High → Critical), not by 2
        self.assertEqual(tagged["severity"], "Critical")

    def test_missing_past_file_key_gives_recurring_not_spread(self):
        # past entry with no "file" key at all → [RECURRING], not [RECURRING-SPREAD].
        findings = [_make_finding(file="src/utils.py", pattern="buffer overread", severity="Medium")]
        past = [{"fingerprint": "buffer overread"}]  # "file" key absent
        result = map_recurring_issues(findings, past)
        self.assertEqual(result["recurring_status"][0]["status"], "RECURRING")
        tagged = result["findings"][0]
        self.assertIn("[RECURRING]", tagged["tags"])
        self.assertNotIn("[RECURRING-SPREAD]", tagged["tags"])
        # Severity bumped by 1 (Medium → High)
        self.assertEqual(tagged["severity"], "High")

    def test_nonempty_different_file_still_gives_spread(self):
        # Confirm that a non-empty past_file that differs from current still yields SPREAD.
        findings = [_make_finding(file="src/newfile.py", pattern="sql injection flaw", severity="High")]
        past = [{"file": "src/auth.py", "fingerprint": "sql injection"}]
        result = map_recurring_issues(findings, past)
        self.assertEqual(result["recurring_status"][0]["status"], "RECURRING-SPREAD")
        self.assertIn("[RECURRING-SPREAD]", result["findings"][0]["tags"])


if __name__ == "__main__":
    unittest.main()
