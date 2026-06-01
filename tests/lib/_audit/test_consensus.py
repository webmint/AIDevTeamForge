"""Tests for src/devforge/lib/_audit/_consensus.py.

Coverage:
  compute_consensus:
    - Two agents same (file, line, pattern) → merged, [CROSS-AGENT], severity bumped
    - Severity bump: High → Critical (one level, capped at Critical)
    - Same agent twice → NOT consensus (passes through as-is)
    - Different pattern → not merged (two separate findings)
    - Punctuation/case normalisation proven:
        "Naming lie!" vs "naming lie" → same hash key → merged
    - Critical capped: Critical + another agent → stays Critical
    - Severity kept as highest of the group (Critical + High → Critical kept)
    - Consensus map only contains merged-group keys
    - Empty input → empty output
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit._consensus import (  # noqa: E402
    _bump_severity,
    _make_hash_key,
    _normalise_pattern,
    compute_consensus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(agent, severity="High", file="src/auth.py", line=10,
                  pattern="Naming lie", confidence="Certain"):
    return {
        "agent": agent,
        "severity": severity,
        "file": file,
        "line": line,
        "pattern": pattern,
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
# _normalise_pattern
# ---------------------------------------------------------------------------

class TestNormalisePattern(unittest.TestCase):
    def test_lowercase(self):
        self.assertEqual(_normalise_pattern("Naming Lie"), "naming lie")

    def test_strip_punctuation(self):
        self.assertEqual(_normalise_pattern("Naming lie!"), "naming lie")

    def test_mixed_case_and_punct(self):
        self.assertIn("naming", _normalise_pattern("Naming Lie!"))

    def test_same_result_for_variants(self):
        a = _normalise_pattern("Naming lie!")
        b = _normalise_pattern("naming lie")
        self.assertEqual(a, b)


# ---------------------------------------------------------------------------
# _make_hash_key
# ---------------------------------------------------------------------------

class TestMakeHashKey(unittest.TestCase):
    def test_same_inputs_same_key(self):
        f1 = _make_finding("agent-a", pattern="Naming lie!")
        f2 = _make_finding("agent-b", pattern="naming lie")
        self.assertEqual(_make_hash_key(f1), _make_hash_key(f2))

    def test_different_file_different_key(self):
        f1 = _make_finding("agent-a", file="src/a.py", pattern="X")
        f2 = _make_finding("agent-a", file="src/b.py", pattern="X")
        self.assertNotEqual(_make_hash_key(f1), _make_hash_key(f2))

    def test_different_line_different_key(self):
        f1 = _make_finding("agent-a")
        f1 = dict(f1, line=10)
        f2 = dict(f1, line=11)
        self.assertNotEqual(_make_hash_key(f1), _make_hash_key(f2))


# ---------------------------------------------------------------------------
# compute_consensus — cross-agent merge
# ---------------------------------------------------------------------------

class TestCrossAgentMerge(unittest.TestCase):
    def test_two_different_agents_same_finding_merged(self):
        findings = [
            _make_finding("code-reviewer", severity="High", pattern="Naming lie"),
            _make_finding("architect", severity="High", pattern="Naming lie"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(len(result["findings"]), 1)

    def test_merged_finding_has_cross_agent_tag(self):
        findings = [
            _make_finding("code-reviewer", severity="High", pattern="Naming lie"),
            _make_finding("architect", severity="High", pattern="Naming lie"),
        ]
        result = compute_consensus(findings)
        self.assertIn("[CROSS-AGENT]", result["findings"][0]["tags"])

    def test_merged_finding_severity_bumped_one_level(self):
        findings = [
            _make_finding("code-reviewer", severity="High", pattern="Naming lie"),
            _make_finding("architect", severity="High", pattern="Naming lie"),
        ]
        result = compute_consensus(findings)
        # High → Critical
        self.assertEqual(result["findings"][0]["severity"], "Critical")

    def test_merged_severity_capped_at_critical(self):
        findings = [
            _make_finding("code-reviewer", severity="Critical", pattern="Bug"),
            _make_finding("qa-engineer", severity="Critical", pattern="Bug"),
        ]
        result = compute_consensus(findings)
        # Critical + bump → still Critical
        self.assertEqual(result["findings"][0]["severity"], "Critical")

    def test_highest_severity_kept_before_bump(self):
        # One agent says High, other says Medium → merged keeps High → bump to Critical
        findings = [
            _make_finding("code-reviewer", severity="High", pattern="Bad code"),
            _make_finding("architect", severity="Medium", pattern="Bad code"),
        ]
        result = compute_consensus(findings)
        # High is kept (higher than Medium), then bumped → Critical
        self.assertEqual(result["findings"][0]["severity"], "Critical")

    def test_consensus_map_contains_merged_key(self):
        findings = [
            _make_finding("code-reviewer", pattern="Off by one"),
            _make_finding("security-reviewer", pattern="Off by one"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(len(result["consensus_map"]), 1)
        agents_in_consensus = list(result["consensus_map"].values())[0]
        self.assertIn("code-reviewer", agents_in_consensus)
        self.assertIn("security-reviewer", agents_in_consensus)

    def test_punctuation_case_normalisation_causes_merge(self):
        # "Naming lie!" (with punct, title case) vs "naming lie" (lowercase, no punct)
        # → same hash key → should merge
        findings = [
            _make_finding("code-reviewer", pattern="Naming lie!"),
            _make_finding("architect", pattern="naming lie"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("[CROSS-AGENT]", result["findings"][0]["tags"])


class TestSameAgentNotConsensus(unittest.TestCase):
    def test_same_agent_twice_no_merge(self):
        findings = [
            _make_finding("code-reviewer", severity="High", pattern="X"),
            _make_finding("code-reviewer", severity="High", pattern="X"),
        ]
        result = compute_consensus(findings)
        # Two entries from same agent → NOT consensus → both pass through
        self.assertEqual(len(result["findings"]), 2)

    def test_same_agent_twice_no_cross_agent_tag(self):
        findings = [
            _make_finding("code-reviewer", severity="High", pattern="Y"),
            _make_finding("code-reviewer", severity="Medium", pattern="Y"),
        ]
        result = compute_consensus(findings)
        for f in result["findings"]:
            self.assertNotIn("[CROSS-AGENT]", f.get("tags", []))

    def test_same_agent_no_consensus_map_entry(self):
        findings = [
            _make_finding("code-reviewer", pattern="Z"),
            _make_finding("code-reviewer", pattern="Z"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(len(result["consensus_map"]), 0)


class TestDifferentPatternNotMerged(unittest.TestCase):
    def test_different_patterns_not_merged(self):
        findings = [
            _make_finding("code-reviewer", pattern="Pattern A"),
            _make_finding("architect", pattern="Pattern B"),
        ]
        result = compute_consensus(findings)
        self.assertEqual(len(result["findings"]), 2)

    def test_different_patterns_no_cross_agent_tag(self):
        findings = [
            _make_finding("code-reviewer", pattern="P1"),
            _make_finding("architect", pattern="P2"),
        ]
        result = compute_consensus(findings)
        for f in result["findings"]:
            self.assertNotIn("[CROSS-AGENT]", f.get("tags", []))


class TestEmptyInput(unittest.TestCase):
    def test_empty_findings_returns_empty(self):
        result = compute_consensus([])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["consensus_map"], {})


class TestThreeAgentsMerge(unittest.TestCase):
    def test_three_distinct_agents_same_finding_merged_once(self):
        findings = [
            _make_finding("code-reviewer", severity="Medium", pattern="Bad pattern"),
            _make_finding("architect", severity="High", pattern="Bad pattern"),
            _make_finding("security-reviewer", severity="Info", pattern="Bad pattern"),
        ]
        result = compute_consensus(findings)
        # All three collapse to one merged finding
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("[CROSS-AGENT]", result["findings"][0]["tags"])
        # Highest severity before bump = High; after bump = Critical
        self.assertEqual(result["findings"][0]["severity"], "Critical")


if __name__ == "__main__":
    unittest.main()
