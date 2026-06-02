"""Tests for src/devforge/lib/_audit/_merge.py.

Coverage:
  merge_passes:
    - Two passes, same defect within TOL (line 244 vs 245) → collapse to ONE,
      pass_count == 2, tag [MULTI-PASS:2] present.
    - Two genuinely distinct defects >TOL apart (line 10 vs line 20) → stay
      SEPARATE (2 outputs).
    - Defect in only one pass → pass_count == 1, NO [MULTI-PASS] tag.
    - Single pool, 2 different agents, SAME file+line → [CROSS-AGENT] tag;
      severity is NOT bumped (location-tolerant clustering is too permissive
      for a severity escalation signal; corroboration already conveyed by tag).
    - Single pool, 2 findings same agent same line → NO [CROSS-AGENT].
    - Deterministic representative selection: highest severity wins.
    - merge_passes([]) → []; merge_passes([[]]) → []; single non-empty pool.
    - TOL boundary: lines differing by exactly 3 merge; by exactly 4 do NOT.
    - line == -1 members do NOT merge with real-line members.
    - Confidence floor: pass_count >= 2 cluster whose rep was "Speculative"
      becomes "Likely"; "Certain" stays "Certain".
    - Input dicts and their tag lists are NOT mutated by the call.
"""

import copy
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit._merge import merge_passes, TOL  # noqa: E402


# ---------------------------------------------------------------------------
# Local helper — matches shape expected by merge_passes
# ---------------------------------------------------------------------------


def _make_finding(
    agent="code-reviewer",
    severity="High",
    file="src/auth.py",
    line=10,
    pattern="Naming lie",
    confidence="Certain",
    evidence="def validate(): return True",
    why="Always returns True.",
    remediation="Fix it.",
    category="mislogic",
    tags=None,
):
    # type: (...) -> dict
    return {
        "agent": agent,
        "severity": severity,
        "file": file,
        "line": line,
        "pattern": pattern,
        "confidence": confidence,
        "evidence": evidence,
        "why": why,
        "remediation": remediation,
        "category": category,
        "tags": list(tags) if tags is not None else [],
    }


# ---------------------------------------------------------------------------
# Empty / trivial inputs
# ---------------------------------------------------------------------------


class TestEmptyInputs(unittest.TestCase):
    def test_empty_pools_returns_empty(self):
        result = merge_passes([])
        self.assertEqual(result, [])

    def test_single_empty_pool_returns_empty(self):
        result = merge_passes([[]])
        self.assertEqual(result, [])

    def test_two_empty_pools_returns_empty(self):
        result = merge_passes([[], []])
        self.assertEqual(result, [])

    def test_single_non_empty_pool_one_finding(self):
        f = _make_finding(line=10)
        result = merge_passes([[f]])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["line"], 10)

    def test_single_non_empty_pool_two_findings_different_files(self):
        f1 = _make_finding(file="src/a.py", line=10)
        f2 = _make_finding(file="src/b.py", line=10)
        result = merge_passes([[f1, f2]])
        self.assertEqual(len(result), 2)


# ---------------------------------------------------------------------------
# Multi-pass clustering: same location across passes
# ---------------------------------------------------------------------------


class TestMultiPassCluster(unittest.TestCase):
    def test_two_passes_within_tol_collapse_to_one(self):
        """Pass 0 line 244, pass 1 line 245 → within TOL=3 → one finding."""
        f0 = _make_finding(line=244)
        f1 = _make_finding(line=245)
        result = merge_passes([[f0], [f1]])
        self.assertEqual(len(result), 1)

    def test_collapsed_has_pass_count_2(self):
        f0 = _make_finding(line=244)
        f1 = _make_finding(line=245)
        result = merge_passes([[f0], [f1]])
        self.assertEqual(result[0]["pass_count"], 2)

    def test_collapsed_has_multi_pass_tag(self):
        f0 = _make_finding(line=244)
        f1 = _make_finding(line=245)
        result = merge_passes([[f0], [f1]])
        self.assertIn("[MULTI-PASS:2]", result[0]["tags"])

    def test_three_passes_multi_pass_tag_k_is_3(self):
        f0 = _make_finding(line=100)
        f1 = _make_finding(line=101)
        f2 = _make_finding(line=102)
        result = merge_passes([[f0], [f1], [f2]])
        self.assertEqual(len(result), 1)
        self.assertIn("[MULTI-PASS:3]", result[0]["tags"])
        self.assertEqual(result[0]["pass_count"], 3)

    def test_single_pass_no_multi_pass_tag(self):
        f = _make_finding(line=50)
        result = merge_passes([[f]])
        self.assertEqual(result[0]["pass_count"], 1)
        # No [MULTI-PASS:...] tag should be present
        tags = result[0]["tags"]
        for t in tags:
            self.assertFalse(t.startswith("[MULTI-PASS:"), msg="Unexpected tag: " + t)


# ---------------------------------------------------------------------------
# Distinct defects stay separate
# ---------------------------------------------------------------------------


class TestDistinctDefectsStaySeparate(unittest.TestCase):
    def test_two_findings_beyond_tol_apart_stay_separate(self):
        """line 10 and line 20 differ by 10 > TOL=3 → 2 outputs."""
        f1 = _make_finding(line=10)
        f2 = _make_finding(line=20)
        result = merge_passes([[f1, f2]])
        self.assertEqual(len(result), 2)

    def test_different_files_always_stay_separate(self):
        f1 = _make_finding(file="src/a.py", line=10)
        f2 = _make_finding(file="src/b.py", line=10)
        result = merge_passes([[f1, f2]])
        self.assertEqual(len(result), 2)
        files = {r["file"] for r in result}
        self.assertIn("src/a.py", files)
        self.assertIn("src/b.py", files)


# ---------------------------------------------------------------------------
# TOL boundary: exactly TOL merges; TOL+1 does not
# ---------------------------------------------------------------------------


class TestTolBoundary(unittest.TestCase):
    def test_exactly_tol_apart_merges(self):
        """Lines differing by exactly TOL=3 → same cluster."""
        anchor = 100
        f0 = _make_finding(line=anchor)
        f1 = _make_finding(line=anchor + TOL)  # diff == 3
        result = merge_passes([[f0], [f1]])
        self.assertEqual(len(result), 1, "Expected merge at diff=TOL")

    def test_exactly_tol_plus_one_does_not_merge(self):
        """Lines differing by TOL+1=4 → separate clusters."""
        anchor = 100
        f0 = _make_finding(line=anchor)
        f1 = _make_finding(line=anchor + TOL + 1)  # diff == 4
        result = merge_passes([[f0], [f1]])
        self.assertEqual(len(result), 2, "Expected separate clusters at diff=TOL+1")

    def test_same_line_merges(self):
        """Same line → same cluster."""
        f0 = _make_finding(line=50)
        f1 = _make_finding(line=50)
        result = merge_passes([[f0], [f1]])
        self.assertEqual(len(result), 1)

    def test_three_members_spanning_boundary_splits_correctly(self):
        """Lines anchor, anchor+TOL, anchor+TOL+1 → {anchor, anchor+TOL} and {anchor+TOL+1}."""
        anchor = 10
        f0 = _make_finding(line=anchor)
        f1 = _make_finding(line=anchor + TOL)      # diff=3, merges
        f2 = _make_finding(line=anchor + TOL + 1)  # diff=4, splits
        result = merge_passes([[f0, f1, f2]])
        self.assertEqual(len(result), 2)
        lines = sorted(r["line"] for r in result)
        self.assertEqual(lines[0], anchor)
        self.assertEqual(lines[1], anchor + TOL + 1)


# ---------------------------------------------------------------------------
# Cross-agent corroboration (tag only; severity NOT bumped in tolerant merge)
# ---------------------------------------------------------------------------


class TestCrossAgentCorroboration(unittest.TestCase):
    def test_two_different_agents_same_file_same_line_cross_agent_tag(self):
        """Single pool, 2 agents, same file+line → [CROSS-AGENT] tag."""
        f1 = _make_finding(agent="code-reviewer", severity="High", line=50)
        f2 = _make_finding(agent="architect", severity="High", line=50)
        result = merge_passes([[f1, f2]])
        self.assertEqual(len(result), 1)
        self.assertIn("[CROSS-AGENT]", result[0]["tags"])

    def test_two_different_agents_severity_unchanged(self):
        """High + cross-agent → stays High (no bump; location-tolerant clustering
        is too permissive to justify a severity escalation).
        """
        f1 = _make_finding(agent="code-reviewer", severity="High", line=50)
        f2 = _make_finding(agent="architect", severity="High", line=50)
        result = merge_passes([[f1, f2]])
        self.assertIn("[CROSS-AGENT]", result[0]["tags"])
        self.assertEqual(result[0]["severity"], "High")

    def test_medium_finding_with_cross_agent_stays_medium(self):
        """Medium + cross-agent → stays Medium (not bumped to High)."""
        f1 = _make_finding(agent="code-reviewer", severity="Medium", line=50)
        f2 = _make_finding(agent="architect", severity="Medium", line=50)
        result = merge_passes([[f1, f2]])
        self.assertIn("[CROSS-AGENT]", result[0]["tags"])
        self.assertEqual(result[0]["severity"], "Medium")

    def test_cross_agent_critical_stays_critical(self):
        """Critical + cross-agent stays Critical (was capped before; still unchanged)."""
        f1 = _make_finding(agent="code-reviewer", severity="Critical", line=50)
        f2 = _make_finding(agent="architect", severity="Critical", line=50)
        result = merge_passes([[f1, f2]])
        self.assertIn("[CROSS-AGENT]", result[0]["tags"])
        self.assertEqual(result[0]["severity"], "Critical")

    def test_two_different_agents_highest_severity_selected_no_bump(self):
        """High + Medium across agents → rep picks High, severity stays High (no bump)."""
        f1 = _make_finding(agent="code-reviewer", severity="High", line=50)
        f2 = _make_finding(agent="architect", severity="Medium", line=50)
        result = merge_passes([[f1, f2]])
        # High selected (highest severity wins representative selection)
        # No bump applied → stays High
        self.assertEqual(result[0]["severity"], "High")

    def test_same_agent_twice_no_cross_agent_tag(self):
        """2 findings same agent same line → NOT cross-agent."""
        f1 = _make_finding(agent="code-reviewer", line=50)
        f2 = _make_finding(agent="code-reviewer", line=50)
        result = merge_passes([[f1, f2]])
        self.assertNotIn("[CROSS-AGENT]", result[0]["tags"])

    def test_same_agent_twice_severity_not_bumped(self):
        """Same agent → no bump."""
        f1 = _make_finding(agent="code-reviewer", severity="High", line=50)
        f2 = _make_finding(agent="code-reviewer", severity="High", line=50)
        result = merge_passes([[f1, f2]])
        self.assertEqual(result[0]["severity"], "High")

    def test_cross_agent_and_multi_pass_both_fire(self):
        """2 passes + 2 agents in one cluster → both [CROSS-AGENT] and [MULTI-PASS:2]."""
        f0 = _make_finding(agent="code-reviewer", severity="High", line=10)
        f1 = _make_finding(agent="architect", severity="Medium", line=11)
        result = merge_passes([[f0], [f1]])
        self.assertIn("[CROSS-AGENT]", result[0]["tags"])
        self.assertIn("[MULTI-PASS:2]", result[0]["tags"])


# ---------------------------------------------------------------------------
# Representative selection
# ---------------------------------------------------------------------------


class TestRepresentativeSelection(unittest.TestCase):
    def test_highest_severity_wins(self):
        """Critical beats High in same cluster; no bump means Critical stays Critical."""
        f_high = _make_finding(agent="architect", severity="High", line=10,
                               evidence="short")
        f_crit = _make_finding(agent="code-reviewer", severity="Critical", line=10,
                               evidence="short")
        result = merge_passes([[f_high, f_crit]])
        self.assertEqual(len(result), 1)
        # Critical rep selected; no bump → severity stays Critical
        self.assertEqual(result[0]["severity"], "Critical")

    def test_confidence_tiebreak(self):
        """Same severity → higher confidence wins."""
        f_likely = _make_finding(agent="architect", severity="High",
                                 confidence="Likely", line=10)
        f_certain = _make_finding(agent="code-reviewer", severity="High",
                                  confidence="Certain", line=10)
        result = merge_passes([[f_likely, f_certain]])
        # f_certain is rep (Certain > Likely); verify via agent field.
        self.assertEqual(result[0]["agent"], "code-reviewer")

    def test_evidence_length_tiebreak(self):
        """Same severity + confidence → longest evidence wins."""
        f_short = _make_finding(agent="architect", severity="High",
                                confidence="Certain", evidence="short", line=10)
        f_long = _make_finding(agent="code-reviewer", severity="High",
                               confidence="Certain", evidence="much longer evidence here",
                               line=10)
        result = merge_passes([[f_short, f_long]])
        self.assertEqual(result[0]["agent"], "code-reviewer")

    def test_alphabetical_agent_tiebreak(self):
        """Same sev/conf/evidence length → alphabetically-first agent wins."""
        f_z = _make_finding(agent="z-agent", severity="High", confidence="Certain",
                            evidence="same", line=10)
        f_a = _make_finding(agent="a-agent", severity="High", confidence="Certain",
                            evidence="same", line=10)
        result = merge_passes([[f_z, f_a]])
        self.assertEqual(result[0]["agent"], "a-agent")

    def test_smallest_line_tiebreak(self):
        """All equal → smallest line wins (within TOL cluster)."""
        f_12 = _make_finding(agent="agent", severity="High", confidence="Certain",
                             evidence="same", line=12)
        f_10 = _make_finding(agent="agent", severity="High", confidence="Certain",
                             evidence="same", line=10)
        result = merge_passes([[f_12, f_10]])
        # Same agent → no cross-agent; rep = f_10 (smaller line)
        self.assertEqual(result[0]["line"], 10)

    def test_insertion_index_tiebreak_is_total_and_deterministic(self):
        """Two findings equal on all 5 spec criteria (sev, conf, evidence, agent, line)
        but distinguishable by a different field (pattern/why).  Selection must be
        by insertion order (position 0 wins), and swapping input order changes the
        winner to the new position-0 member.
        """
        # Both identical on the 5 tie-break criteria; differ only on 'pattern'/'why'
        a = _make_finding(
            agent="agent",
            severity="High",
            confidence="Certain",
            evidence="same",
            line=10,
            pattern="pattern-A",
            why="why-A",
        )
        b = _make_finding(
            agent="agent",
            severity="High",
            confidence="Certain",
            evidence="same",
            line=10,
            pattern="pattern-B",
            why="why-B",
        )
        # a first → a is representative (insertion index 0 wins)
        result_ab = merge_passes([[a, b]])
        self.assertEqual(len(result_ab), 1)
        self.assertEqual(result_ab[0]["pattern"], "pattern-A")

        # b first → b is now representative (b is now insertion index 0)
        result_ba = merge_passes([[b, a]])
        self.assertEqual(len(result_ba), 1)
        self.assertEqual(result_ba[0]["pattern"], "pattern-B")


# ---------------------------------------------------------------------------
# Confidence floor for multi-pass
# ---------------------------------------------------------------------------


class TestConfidenceFloor(unittest.TestCase):
    def test_speculative_raised_to_likely_when_two_passes(self):
        f0 = _make_finding(confidence="Speculative", line=100)
        f1 = _make_finding(confidence="Speculative", line=101)
        result = merge_passes([[f0], [f1]])
        self.assertEqual(result[0]["confidence"], "Likely")

    def test_likely_stays_likely_when_two_passes(self):
        f0 = _make_finding(confidence="Likely", line=100)
        f1 = _make_finding(confidence="Likely", line=100)
        result = merge_passes([[f0], [f1]])
        self.assertEqual(result[0]["confidence"], "Likely")

    def test_certain_stays_certain_when_two_passes(self):
        f0 = _make_finding(confidence="Certain", line=100)
        f1 = _make_finding(confidence="Certain", line=101)
        result = merge_passes([[f0], [f1]])
        self.assertEqual(result[0]["confidence"], "Certain")

    def test_no_confidence_floor_for_single_pass(self):
        """Single pass: Speculative stays Speculative (no floor)."""
        f0 = _make_finding(confidence="Speculative", line=100)
        result = merge_passes([[f0]])
        self.assertEqual(result[0]["confidence"], "Speculative")


# ---------------------------------------------------------------------------
# Line sentinel (-1) handling
# ---------------------------------------------------------------------------


class TestLineSentinel(unittest.TestCase):
    def test_sentinel_does_not_merge_with_line_1(self):
        f_real = _make_finding(line=1)
        f_sentinel = _make_finding(line=-1)
        result = merge_passes([[f_real, f_sentinel]])
        self.assertEqual(len(result), 2)

    def test_sentinel_does_not_merge_with_line_3(self):
        """line -1 vs line 3: abs diff = 4 (after sentinel special rule) → separate."""
        f_real = _make_finding(line=3)
        f_sentinel = _make_finding(line=-1)
        result = merge_passes([[f_real, f_sentinel]])
        self.assertEqual(len(result), 2)

    def test_two_sentinels_same_file_merge(self):
        """Two -1 members in the same file → same cluster."""
        f0 = _make_finding(line=-1)
        f1 = _make_finding(line=-1)
        result = merge_passes([[f0, f1]])
        self.assertEqual(len(result), 1)

    def test_sentinel_cluster_comes_last_in_file(self):
        """Within a file, -1 cluster appears after all real-line clusters."""
        f_real = _make_finding(line=200, pattern="real finding")
        f_sentinel = _make_finding(line=-1, pattern="sentinel finding")
        result = merge_passes([[f_sentinel, f_real]])
        # real finding first (line 200), sentinel last
        self.assertEqual(result[0]["line"], 200)
        self.assertEqual(result[1]["line"], -1)

    def test_sentinel_two_passes_gets_multi_pass_tag(self):
        """Two -1 findings from different passes → pass_count=2, [MULTI-PASS:2]."""
        f0 = _make_finding(line=-1, agent="code-reviewer")
        f1 = _make_finding(line=-1, agent="code-reviewer")
        result = merge_passes([[f0], [f1]])
        self.assertEqual(result[0]["pass_count"], 2)
        self.assertIn("[MULTI-PASS:2]", result[0]["tags"])


# ---------------------------------------------------------------------------
# Tags union across members
# ---------------------------------------------------------------------------


class TestTagsUnion(unittest.TestCase):
    def test_existing_tags_from_members_preserved(self):
        """Members' existing tags appear in the representative."""
        f1 = _make_finding(agent="code-reviewer", line=10, tags=["[RECURRING]"])
        f2 = _make_finding(agent="architect", line=11, tags=["[RECURRING-SPREAD]"])
        result = merge_passes([[f1, f2]])
        # Cross-agent fires (different agents in pool 0, single pass)
        tags = result[0]["tags"]
        self.assertIn("[RECURRING]", tags)
        self.assertIn("[RECURRING-SPREAD]", tags)
        self.assertIn("[CROSS-AGENT]", tags)

    def test_tags_deduped_across_members(self):
        """Same tag on multiple members → appears only once."""
        f1 = _make_finding(agent="code-reviewer", line=10, tags=["[RECURRING]"])
        f2 = _make_finding(agent="code-reviewer", line=10, tags=["[RECURRING]"])
        result = merge_passes([[f1, f2]])
        self.assertEqual(result[0]["tags"].count("[RECURRING]"), 1)

    def test_cross_agent_tag_not_doubled(self):
        """If a member already has [CROSS-AGENT], it doesn't appear twice."""
        f1 = _make_finding(agent="code-reviewer", line=10, tags=["[CROSS-AGENT]"])
        f2 = _make_finding(agent="architect", line=10, tags=[])
        result = merge_passes([[f1, f2]])
        self.assertEqual(result[0]["tags"].count("[CROSS-AGENT]"), 1)

    def test_multi_pass_tag_not_doubled(self):
        """Multi-pass tag is not duplicated if somehow already present in members."""
        f0 = _make_finding(line=10, tags=["[MULTI-PASS:2]"])
        f1 = _make_finding(line=11)
        result = merge_passes([[f0], [f1]])
        self.assertEqual(result[0]["tags"].count("[MULTI-PASS:2]"), 1)


# ---------------------------------------------------------------------------
# Output ordering
# ---------------------------------------------------------------------------


class TestOutputOrdering(unittest.TestCase):
    def test_file_order_by_first_appearance(self):
        """Files appear in the order their first member was seen (flattened)."""
        f_b = _make_finding(file="src/b.py", line=10)
        f_a = _make_finding(file="src/a.py", line=10)
        # b.py comes first in pool 0
        result = merge_passes([[f_b, f_a]])
        self.assertEqual(result[0]["file"], "src/b.py")
        self.assertEqual(result[1]["file"], "src/a.py")

    def test_within_file_clusters_in_anchor_line_order(self):
        """Within a file, clusters are ordered by anchor line ascending."""
        f_high = _make_finding(line=100, pattern="high line")
        f_low = _make_finding(line=10, pattern="low line")
        result = merge_passes([[f_high, f_low]])
        # Both in same file; lower anchor line comes first
        self.assertEqual(result[0]["line"], 10)
        self.assertEqual(result[1]["line"], 100)

    def test_second_pass_file_order_respects_first_appearance(self):
        """If pass 0 has file A and pass 1 has file B, A comes first."""
        f_a = _make_finding(file="src/a.py", line=10)
        f_b = _make_finding(file="src/b.py", line=10)
        result = merge_passes([[f_a], [f_b]])
        self.assertEqual(result[0]["file"], "src/a.py")
        self.assertEqual(result[1]["file"], "src/b.py")


# ---------------------------------------------------------------------------
# Input mutation guard
# ---------------------------------------------------------------------------


class TestNoMutation(unittest.TestCase):
    def test_input_findings_not_mutated(self):
        """merge_passes must not mutate any input finding dict."""
        f0 = _make_finding(agent="code-reviewer", severity="High", line=10,
                           tags=["[RECURRING]"])
        f1 = _make_finding(agent="architect", severity="Medium", line=11)
        original_f0 = copy.deepcopy(f0)
        original_f1 = copy.deepcopy(f1)
        _result = merge_passes([[f0, f1]])
        self.assertEqual(f0, original_f0, "f0 was mutated")
        self.assertEqual(f1, original_f1, "f1 was mutated")

    def test_input_tags_lists_not_mutated(self):
        """The tags list on input dicts must not be mutated."""
        f0 = _make_finding(agent="code-reviewer", line=10, tags=["[RECURRING]"])
        original_tags = list(f0["tags"])
        _result = merge_passes([[f0]])
        self.assertEqual(f0["tags"], original_tags, "Input tags list was mutated")

    def test_input_pools_list_not_mutated(self):
        """merge_passes must not mutate the pools list itself."""
        f0 = _make_finding(line=10)
        pool = [f0]
        pools = [pool]
        original_pool_len = len(pool)
        _result = merge_passes(pools)
        self.assertEqual(len(pool), original_pool_len, "Pool list was mutated")

    def test_multi_pass_input_not_mutated(self):
        """Cross-pass merge must not mutate inputs."""
        f0 = _make_finding(agent="code-reviewer", severity="High", line=244,
                           confidence="Speculative", tags=["[EXISTING]"])
        f1 = _make_finding(agent="architect", severity="Medium", line=245,
                           confidence="Speculative")
        orig_f0 = copy.deepcopy(f0)
        orig_f1 = copy.deepcopy(f1)
        _result = merge_passes([[f0], [f1]])
        self.assertEqual(f0, orig_f0, "f0 mutated during cross-pass merge")
        self.assertEqual(f1, orig_f1, "f1 mutated during cross-pass merge")


# ---------------------------------------------------------------------------
# Pass count always present
# ---------------------------------------------------------------------------


class TestPassCountAlwaysPresent(unittest.TestCase):
    def test_single_finding_single_pass_has_pass_count(self):
        f = _make_finding()
        result = merge_passes([[f]])
        self.assertIn("pass_count", result[0])
        self.assertEqual(result[0]["pass_count"], 1)

    def test_two_findings_same_pass_same_line_has_pass_count(self):
        f1 = _make_finding(agent="code-reviewer", line=20)
        f2 = _make_finding(agent="code-reviewer", line=20)
        result = merge_passes([[f1, f2]])
        self.assertIn("pass_count", result[0])
        self.assertEqual(result[0]["pass_count"], 1)


# ---------------------------------------------------------------------------
# Integration scenario: line 244 vs 245 from the brief
# ---------------------------------------------------------------------------


class TestBriefScenario(unittest.TestCase):
    def test_line_244_and_245_collapse(self):
        """The brief's example: pass 0 line 244, pass 1 line 245 → one finding."""
        f0 = _make_finding(line=244, agent="code-reviewer", severity="High",
                           confidence="Likely")
        f1 = _make_finding(line=245, agent="code-reviewer", severity="High",
                           confidence="Likely")
        result = merge_passes([[f0], [f1]])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["pass_count"], 2)
        self.assertIn("[MULTI-PASS:2]", result[0]["tags"])
        # No cross-agent (same agent), so severity unchanged
        self.assertEqual(result[0]["severity"], "High")

    def test_lines_10_and_20_stay_separate(self):
        """The brief's example: distinct defects >TOL → 2 outputs."""
        f1 = _make_finding(line=10)
        f2 = _make_finding(line=20)
        result = merge_passes([[f1, f2]])
        self.assertEqual(len(result), 2)
        lines = sorted(r["line"] for r in result)
        self.assertEqual(lines, [10, 20])


if __name__ == "__main__":
    unittest.main()
