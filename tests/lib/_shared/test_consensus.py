"""Tests for src/devforge/lib/_shared/_consensus.py.

Coverage:
  _bump_severity:
    - Info+1 → Medium, Medium+1 → High, High+1 → Critical, Critical+1 → Critical
    - Unknown unchanged, multi-level bump.

  _make_group_key:
    - Same (file, line, category) → same key regardless of pattern wording.
    - Different file → different key.
    - Different line → different key.
    - Different category → different key (over-merge guard).
    - Missing category defaults to "mislogic".

  compute_consensus — new (file, line, category) keying:
    - Three agents, same (file, line), same category, DIFFERENT pattern wordings
      → ONE merged finding, [CROSS-AGENT], severity bumped, merged_count == 3,
      consensus_map has an entry.
    - Same-agent duplicates (same (file, line, category), one agent)
      → ONE finding, merged_count == N, NO [CROSS-AGENT], NO bump,
      NOT in consensus_map.
    - Same (file, line), DIFFERENT category → stay separate (no over-merge).
    - True singleton → merged_count == 1, no [CROSS-AGENT] tag, not in
      consensus_map.
    - Determinism: representative selection is stable (highest severity,
      then alphabetically first agent).
    - Two agents, different category same line → separate findings each
      without [CROSS-AGENT].
    - Cross-agent Critical capped: Critical + Critical + bump stays Critical.
    - Severity kept as highest before bump: High + Medium → Critical (not High+1).
    - Empty input → empty output.
    - consensus_map key format is "<file>:<line>:<category>".

Note: this exact-match consensus bump is intentional and distinct from
`_merge.py`'s tolerant (TOL±3) cross-pass merge, which does NOT bump
severity (location proximity is too permissive to justify escalation).
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared._consensus import (  # noqa: E402
    _bump_severity,
    _make_group_key,
    compute_consensus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(agent, severity="High", file="src/auth.py", line=10,
                  pattern="Naming lie", category="mislogic",
                  confidence="Certain"):
    return {
        "agent": agent,
        "severity": severity,
        "file": file,
        "line": line,
        "pattern": pattern,
        "category": category,
        "confidence": confidence,
        "evidence": "def validate(): return True",
        "why": "Always returns True.",
        "remediation": "Fix it.",
        "tags": [],
    }


# ---------------------------------------------------------------------------
# _bump_severity
# ---------------------------------------------------------------------------

class TestBumpSeverity(unittest.TestCase):
    def test_info_bumped_one_to_medium(self):
        self.assertEqual(_bump_severity("Info", 1), "Medium")

    def test_medium_bumped_one_to_high(self):
        self.assertEqual(_bump_severity("Medium", 1), "High")

    def test_high_bumped_one_to_critical(self):
        self.assertEqual(_bump_severity("High", 1), "Critical")

    def test_critical_capped(self):
        self.assertEqual(_bump_severity("Critical", 1), "Critical")

    def test_medium_bumped_two_to_critical(self):
        self.assertEqual(_bump_severity("Medium", 2), "Critical")

    def test_info_bumped_two_to_high(self):
        self.assertEqual(_bump_severity("Info", 2), "High")

    def test_unknown_severity_unchanged(self):
        self.assertEqual(_bump_severity("Unknown", 1), "Unknown")


# ---------------------------------------------------------------------------
# _make_group_key
# ---------------------------------------------------------------------------

class TestMakeGroupKey(unittest.TestCase):
    def test_same_file_line_category_same_key_regardless_of_pattern(self):
        f1 = _make_finding("agent-a", pattern="Missing return — silent path",
                           category="mislogic")
        f2 = _make_finding("agent-b", pattern="Early-return omission",
                           category="mislogic")
        self.assertEqual(_make_group_key(f1), _make_group_key(f2))

    def test_different_file_different_key(self):
        f1 = _make_finding("agent-a", file="src/a.py", category="mislogic")
        f2 = _make_finding("agent-a", file="src/b.py", category="mislogic")
        self.assertNotEqual(_make_group_key(f1), _make_group_key(f2))

    def test_different_line_different_key(self):
        f1 = dict(_make_finding("agent-a", category="mislogic"), line=10)
        f2 = dict(_make_finding("agent-a", category="mislogic"), line=11)
        self.assertNotEqual(_make_group_key(f1), _make_group_key(f2))

    def test_different_category_different_key(self):
        f1 = _make_finding("agent-a", category="mislogic")
        f2 = _make_finding("agent-a", category="security")
        self.assertNotEqual(_make_group_key(f1), _make_group_key(f2))

    def test_missing_category_defaults_to_mislogic(self):
        f = {"agent": "a", "file": "x.py", "line": 1, "pattern": "p"}
        key = _make_group_key(f)
        self.assertEqual(key[2], "mislogic")

    def test_none_category_defaults_to_mislogic(self):
        f = {"agent": "a", "file": "x.py", "line": 1,
             "pattern": "p", "category": None}
        key = _make_group_key(f)
        self.assertEqual(key[2], "mislogic")

    def test_key_is_tuple_of_three(self):
        f = _make_finding("a")
        key = _make_group_key(f)
        self.assertIsInstance(key, tuple)
        self.assertEqual(len(key), 3)


# ---------------------------------------------------------------------------
# compute_consensus — primary dedup test cases (spec §1–§4)
# ---------------------------------------------------------------------------

class TestThreeAgentsDifferentWordingsMerge(unittest.TestCase):
    """Spec §1: three agents, same (file, line, category), different wording."""

    def setUp(self):
        # Three wording variants of the same bug, three distinct agents
        self.findings = [
            _make_finding("code-reviewer", severity="High",
                          pattern="Missing return — silent path",
                          category="mislogic"),
            _make_finding("architect", severity="Medium",
                          pattern="Missing return on happy path",
                          category="mislogic"),
            _make_finding("qa-reviewer", severity="Info",
                          pattern="Early-return omission",
                          category="mislogic"),
        ]
        self.result = compute_consensus(self.findings)

    def test_collapses_to_one_finding(self):
        self.assertEqual(len(self.result["findings"]), 1)

    def test_representative_has_cross_agent_tag(self):
        self.assertIn("[CROSS-AGENT]", self.result["findings"][0]["tags"])

    def test_severity_bumped_from_highest_high_to_critical(self):
        # Highest in group is High → bump to Critical
        self.assertEqual(self.result["findings"][0]["severity"], "Critical")

    def test_merged_count_equals_three(self):
        self.assertEqual(self.result["findings"][0]["merged_count"], 3)

    def test_consensus_map_has_entry(self):
        self.assertEqual(len(self.result["consensus_map"]), 1)

    def test_consensus_map_has_all_three_agents(self):
        agents = list(self.result["consensus_map"].values())[0]
        self.assertIn("code-reviewer", agents)
        self.assertIn("architect", agents)
        self.assertIn("qa-reviewer", agents)


class TestSameAgentDuplicatesDedup(unittest.TestCase):
    """Spec §2: same-agent duplicates collapse but get no corroboration signals."""

    def setUp(self):
        # Three variants from ONE agent (wording-varied self-duplicates)
        self.findings = [
            _make_finding("code-reviewer", severity="High",
                          pattern="Missing return — silent path",
                          category="mislogic"),
            _make_finding("code-reviewer", severity="Medium",
                          pattern="Missing return on happy path",
                          category="mislogic"),
            _make_finding("code-reviewer", severity="Info",
                          pattern="Early-return omission",
                          category="mislogic"),
        ]
        self.result = compute_consensus(self.findings)

    def test_collapses_to_one_finding(self):
        self.assertEqual(len(self.result["findings"]), 1)

    def test_no_cross_agent_tag(self):
        self.assertNotIn("[CROSS-AGENT]",
                         self.result["findings"][0].get("tags", []))

    def test_no_severity_bump(self):
        # Best representative is High (highest in group); no bump → stays High
        self.assertEqual(self.result["findings"][0]["severity"], "High")

    def test_merged_count_equals_three(self):
        self.assertEqual(self.result["findings"][0]["merged_count"], 3)

    def test_not_in_consensus_map(self):
        self.assertEqual(len(self.result["consensus_map"]), 0)


class TestDifferentCategoryNotMerged(unittest.TestCase):
    """Spec §3: same (file, line) but DIFFERENT category → separate findings."""

    def setUp(self):
        self.findings = [
            _make_finding("code-reviewer", category="mislogic"),
            _make_finding("security-reviewer", category="security"),
        ]
        self.result = compute_consensus(self.findings)

    def test_stays_separate(self):
        self.assertEqual(len(self.result["findings"]), 2)

    def test_neither_has_cross_agent_tag(self):
        for f in self.result["findings"]:
            self.assertNotIn("[CROSS-AGENT]", f.get("tags", []))

    def test_neither_in_consensus_map(self):
        # No group has ≥2 distinct agents
        self.assertEqual(len(self.result["consensus_map"]), 0)


class TestTrueSingleton(unittest.TestCase):
    """Spec §4: a single unique finding is unchanged."""

    def setUp(self):
        self.findings = [
            _make_finding("code-reviewer", severity="High", category="mislogic"),
        ]
        self.result = compute_consensus(self.findings)

    def test_single_finding_passes_through(self):
        self.assertEqual(len(self.result["findings"]), 1)

    def test_merged_count_is_one(self):
        self.assertEqual(self.result["findings"][0]["merged_count"], 1)

    def test_no_cross_agent_tag(self):
        self.assertNotIn("[CROSS-AGENT]",
                         self.result["findings"][0].get("tags", []))

    def test_no_severity_change(self):
        self.assertEqual(self.result["findings"][0]["severity"], "High")

    def test_not_in_consensus_map(self):
        self.assertEqual(len(self.result["consensus_map"]), 0)


# ---------------------------------------------------------------------------
# compute_consensus — additional coverage
# ---------------------------------------------------------------------------

class TestDeterministicRepresentativeSelection(unittest.TestCase):
    """Determinism: highest severity wins; alphabetically first agent breaks tie."""

    def test_highest_severity_selected_as_representative(self):
        findings = [
            _make_finding("zebra-agent", severity="Info", category="mislogic"),
            _make_finding("alpha-agent", severity="Critical", category="mislogic"),
            _make_finding("beta-agent", severity="Medium", category="mislogic"),
        ]
        result = compute_consensus(findings)
        rep = result["findings"][0]
        # The Critical finding (alpha-agent) is the representative before bump.
        # After cross-agent bump Critical → Critical (capped).
        self.assertEqual(rep["severity"], "Critical")

    def test_alphabetically_first_agent_breaks_severity_tie(self):
        findings = [
            _make_finding("zebra-reviewer", severity="High", category="mislogic"),
            _make_finding("alpha-reviewer", severity="High", category="mislogic"),
        ]
        result = compute_consensus(findings)
        rep = result["findings"][0]
        # Both High → alpha-reviewer wins tie-break (alphabetically first).
        self.assertEqual(rep["agent"], "alpha-reviewer")

    def test_representative_stable_across_input_order(self):
        """Re-ordering input doesn't change which finding is selected."""
        f_a = _make_finding("alpha-agent", severity="High", category="mislogic")
        f_b = _make_finding("beta-agent", severity="High", category="mislogic")
        result1 = compute_consensus([f_a, f_b])
        result2 = compute_consensus([f_b, f_a])
        self.assertEqual(result1["findings"][0]["agent"],
                         result2["findings"][0]["agent"])


class TestSeverityBumpGating(unittest.TestCase):
    """Severity bump only for ≥2 distinct agents; highest severity is base."""

    def test_two_agents_severity_bumped_one_level(self):
        findings = [
            _make_finding("code-reviewer", severity="High", category="mislogic"),
            _make_finding("architect", severity="High", category="mislogic"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(result["findings"][0]["severity"], "Critical")

    def test_critical_capped_after_cross_agent_bump(self):
        findings = [
            _make_finding("code-reviewer", severity="Critical", category="mislogic"),
            _make_finding("qa-reviewer", severity="Critical", category="mislogic"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(result["findings"][0]["severity"], "Critical")

    def test_highest_severity_in_group_is_base_for_bump(self):
        # Highest is High (not Medium), bump → Critical
        findings = [
            _make_finding("code-reviewer", severity="High", category="mislogic"),
            _make_finding("architect", severity="Medium", category="mislogic"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(result["findings"][0]["severity"], "Critical")


class TestConsensusMapKeyFormat(unittest.TestCase):
    """consensus_map key must be "<file>:<line>:<category>"."""

    def test_consensus_map_key_format(self):
        findings = [
            _make_finding("code-reviewer", file="src/foo.py", line=42,
                          category="security"),
            _make_finding("security-reviewer", file="src/foo.py", line=42,
                          category="security"),
        ]
        result = compute_consensus(findings)
        expected_key = "src/foo.py:42:security"
        self.assertIn(expected_key, result["consensus_map"])


class TestEmptyInput(unittest.TestCase):
    def test_empty_findings_returns_empty(self):
        result = compute_consensus([])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["consensus_map"], {})


class TestMergedCountField(unittest.TestCase):
    """merged_count is always present and correct."""

    def test_two_same_agent_merged_count_is_two(self):
        findings = [
            _make_finding("code-reviewer", pattern="A", category="mislogic"),
            _make_finding("code-reviewer", pattern="B", category="mislogic"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(result["findings"][0]["merged_count"], 2)

    def test_two_cross_agent_merged_count_is_two(self):
        findings = [
            _make_finding("code-reviewer", pattern="A", category="mislogic"),
            _make_finding("architect", pattern="B", category="mislogic"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(result["findings"][0]["merged_count"], 2)

    def test_singleton_merged_count_is_one(self):
        findings = [
            _make_finding("code-reviewer", category="mislogic"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(result["findings"][0]["merged_count"], 1)


class TestMultipleGroupsInSameRun(unittest.TestCase):
    """Multiple distinct (file, line, category) groups are each processed."""

    def test_two_groups_both_preserved(self):
        # Group A: src/a.py:10:mislogic — two agents → merge + CROSS-AGENT
        # Group B: src/b.py:20:security — one agent → singleton
        findings = [
            _make_finding("code-reviewer", file="src/a.py", line=10,
                          category="mislogic"),
            _make_finding("architect", file="src/a.py", line=10,
                          category="mislogic"),
            _make_finding("security-reviewer", file="src/b.py", line=20,
                          category="security"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(len(result["findings"]), 2)
        self.assertEqual(len(result["consensus_map"]), 1)

    def test_group_insertion_order_preserved(self):
        """Output order = first-appearance order of the group key."""
        findings = [
            _make_finding("code-reviewer", file="src/b.py", line=5,
                          category="mislogic"),
            _make_finding("architect", file="src/a.py", line=1,
                          category="mislogic"),
        ]
        result = compute_consensus(findings)
        # src/b.py appeared first → should be first in output
        self.assertEqual(result["findings"][0]["file"], "src/b.py")
        self.assertEqual(result["findings"][1]["file"], "src/a.py")


class TestMissingCategoryDefaultsToMislogic(unittest.TestCase):
    """Findings without a category field default to 'mislogic' for grouping."""

    def test_two_agents_no_category_merge_as_mislogic(self):
        f1 = {"agent": "code-reviewer", "file": "src/x.py", "line": 5,
              "severity": "High", "pattern": "Bug A",
              "confidence": "Certain", "evidence": "code",
              "why": "bad", "remediation": "fix", "tags": []}
        f2 = {"agent": "architect", "file": "src/x.py", "line": 5,
              "severity": "Medium", "pattern": "Bug B",
              "confidence": "Certain", "evidence": "code",
              "why": "bad", "remediation": "fix", "tags": []}
        result = compute_consensus([f1, f2])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("[CROSS-AGENT]", result["findings"][0]["tags"])

    def test_missing_category_and_explicit_mislogic_group_together(self):
        f1 = {"agent": "code-reviewer", "file": "src/x.py", "line": 5,
              "severity": "High", "pattern": "Bug A",
              "confidence": "Certain", "evidence": "code",
              "why": "bad", "remediation": "fix", "tags": []}
        f2 = _make_finding("architect", file="src/x.py", line=5,
                            category="mislogic")
        result = compute_consensus([f1, f2])
        # Both should land in the same group (mislogic default)
        self.assertEqual(len(result["findings"]), 1)


class TestCrossAgentTagNotDuplicated(unittest.TestCase):
    """[CROSS-AGENT] is not added twice if already present."""

    def test_existing_cross_agent_tag_not_duplicated(self):
        f1 = _make_finding("code-reviewer", category="mislogic")
        f1["tags"] = ["[CROSS-AGENT]"]
        f2 = _make_finding("architect", category="mislogic")
        result = compute_consensus([f1, f2])
        tags = result["findings"][0]["tags"]
        self.assertEqual(tags.count("[CROSS-AGENT]"), 1)


if __name__ == "__main__":
    unittest.main()
