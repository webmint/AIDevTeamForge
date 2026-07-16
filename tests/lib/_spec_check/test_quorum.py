"""Tests for src/devforge/lib/_spec_check/_quorum.py.

Coverage:
  analyze_quorum:
    k=2 both-agree unsat            -> confirmed_unsat, reproduced_in 2/2
    k=2 one-unsat-one-sat           -> unstable, reproduced_in 1/2
    k=3 two-agree-one-diverges      -> confirmed_unsat, reproduced_in 2/3
    k=3 all-different unsat cores   -> unstable
    all sat                        -> consistent, all_cores []
    k=1 single unsat               -> confirmed_unsat 1/1 (degenerate case)
    empty solve_results            -> ValueError
    all_cores ordering (count-desc, sorted-tuple tie-break)
    confirmed_core always sorted

  synthesize_solve_result:
    confirmed_unsat -> unsat + core
    consistent      -> sat
    unstable        -> sat (the load-bearing D13 cry-wolf rule)
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _spec_check._quorum import (  # noqa: E402
    QUORUM_VERDICTS,
    analyze_quorum,
    synthesize_solve_result,
)


def _unsat(core):
    return {"status": "unsat", "unsat_core": list(core)}


def _sat():
    return {"status": "sat", "unsat_core": []}


def _unknown():
    return {"status": "unknown", "unsat_core": []}


# ---------------------------------------------------------------------------
# analyze_quorum
# ---------------------------------------------------------------------------


class TestAnalyzeQuorumConfirmedUnsat(unittest.TestCase):
    def test_k2_both_agree(self):
        results = [_unsat(["AC-8", "AC-3"]), _unsat(["AC-3", "AC-8"])]
        quorum = analyze_quorum(results, 2)
        self.assertEqual(quorum["verdict"], "confirmed_unsat")
        self.assertEqual(quorum["confirmed_core"], ["AC-3", "AC-8"])
        self.assertEqual(quorum["stability"], {"reproduced_in": 2, "of": 2})

    def test_k3_two_agree_one_diverges(self):
        results = [_unsat(["A", "B"]), _unsat(["B", "A"]), _unsat(["C"])]
        quorum = analyze_quorum(results, 3)
        self.assertEqual(quorum["verdict"], "confirmed_unsat")
        self.assertEqual(quorum["confirmed_core"], ["A", "B"])
        self.assertEqual(quorum["stability"], {"reproduced_in": 2, "of": 3})
        # all_cores lists both distinct cores, count-desc.
        cores = quorum["all_cores"]
        self.assertEqual(len(cores), 2)
        self.assertEqual(cores[0], {"core": ["A", "B"], "count": 2})
        self.assertEqual(cores[1], {"core": ["C"], "count": 1})

    def test_k1_single_unsat_degenerate_case(self):
        results = [_unsat(["AC-1"])]
        quorum = analyze_quorum(results, 1)
        self.assertEqual(quorum["verdict"], "confirmed_unsat")
        self.assertEqual(quorum["confirmed_core"], ["AC-1"])
        self.assertEqual(quorum["stability"], {"reproduced_in": 1, "of": 1})

    def test_confirmed_core_is_sorted(self):
        results = [_unsat(["AC-9", "AC-2", "AC-5"]), _unsat(["AC-5", "AC-9", "AC-2"])]
        quorum = analyze_quorum(results, 2)
        self.assertEqual(quorum["confirmed_core"], ["AC-2", "AC-5", "AC-9"])


class TestAnalyzeQuorumUnstable(unittest.TestCase):
    def test_k2_one_unsat_one_sat(self):
        results = [_unsat(["AC-1"]), _sat()]
        quorum = analyze_quorum(results, 2)
        self.assertEqual(quorum["verdict"], "unstable")
        self.assertIsNone(quorum["confirmed_core"])
        self.assertEqual(quorum["stability"], {"reproduced_in": 1, "of": 2})

    def test_k3_all_different_unsat_cores(self):
        results = [_unsat(["A"]), _unsat(["B"]), _unsat(["C"])]
        quorum = analyze_quorum(results, 3)
        self.assertEqual(quorum["verdict"], "unstable")
        self.assertIsNone(quorum["confirmed_core"])
        self.assertEqual(quorum["stability"], {"reproduced_in": 1, "of": 3})
        self.assertEqual(len(quorum["all_cores"]), 3)


class TestAnalyzeQuorumConsistent(unittest.TestCase):
    def test_all_sat(self):
        results = [_sat(), _sat()]
        quorum = analyze_quorum(results, 2)
        self.assertEqual(quorum["verdict"], "consistent")
        self.assertIsNone(quorum["confirmed_core"])
        self.assertEqual(quorum["stability"], {"reproduced_in": 0, "of": 2})
        self.assertEqual(quorum["all_cores"], [])

    def test_all_unknown(self):
        results = [_unknown(), _unknown()]
        quorum = analyze_quorum(results, 2)
        self.assertEqual(quorum["verdict"], "consistent")

    def test_mixed_sat_and_unknown_no_unsat(self):
        results = [_sat(), _unknown(), _sat()]
        quorum = analyze_quorum(results, 3)
        self.assertEqual(quorum["verdict"], "consistent")


class TestAnalyzeQuorumOrderingAndTieBreak(unittest.TestCase):
    def test_all_cores_ordering_count_desc_then_sorted_tuple(self):
        # Two distinct 1-count cores with an unrelated majority winner --
        # confirms the non-winners are still sorted deterministically
        # (sorted-tuple order) among themselves.
        results = [
            _unsat(["X", "Y"]),
            _unsat(["X", "Y"]),
            _unsat(["X", "Y"]),
            _unsat(["Z"]),
            _unsat(["A"]),
        ]
        quorum = analyze_quorum(results, 5)
        self.assertEqual(quorum["verdict"], "confirmed_unsat")
        self.assertEqual(quorum["confirmed_core"], ["X", "Y"])
        cores = quorum["all_cores"]
        self.assertEqual(cores[0], {"core": ["X", "Y"], "count": 3})
        # Both remaining have count 1 -- sorted-tuple order: ["A"] < ["Z"].
        self.assertEqual(cores[1], {"core": ["A"], "count": 1})
        self.assertEqual(cores[2], {"core": ["Z"], "count": 1})


class TestAnalyzeQuorumDeclaredK(unittest.TestCase):
    """F1: a declared/actual pass-count mismatch is never silently
    absorbed -- the actual count still drives the math, but "declared_k"
    surfaces the discrepancy in the returned dict."""

    def test_declared_k_matches_actual_when_no_mismatch(self):
        results = [_unsat(["AC-1"]), _unsat(["AC-1"])]
        quorum = analyze_quorum(results, 2)
        self.assertEqual(quorum["declared_k"], 2)
        self.assertEqual(quorum["stability"]["of"], 2)

    def test_declared_k_defaults_to_actual_when_k_is_none(self):
        results = [_unsat(["AC-1"]), _sat()]
        quorum = analyze_quorum(results, None)
        self.assertEqual(quorum["declared_k"], 2)
        self.assertEqual(quorum["stability"]["of"], 2)

    def test_declared_k3_actual2_dropped_pass_visible(self):
        # A dropped pass: 3 were declared, only 2 solve-result dicts made
        # it into the array. The math still runs on the actual count (2)
        # -- but declared_k=3 stays visible so a downstream consumer
        # (or a human reading the JSON) can see the quorum was
        # incomplete, instead of reading "reproduced in 2/2" as if it
        # were a full 3-pass quorum.
        results = [_unsat(["AC-1", "AC-2"]), _unsat(["AC-2", "AC-1"])]
        quorum = analyze_quorum(results, 3)
        self.assertEqual(quorum["declared_k"], 3)
        self.assertEqual(quorum["stability"], {"reproduced_in": 2, "of": 2})
        self.assertEqual(quorum["verdict"], "confirmed_unsat")

    def test_declared_k_present_on_consistent_verdict(self):
        results = [_sat(), _sat()]
        quorum = analyze_quorum(results, 5)
        self.assertEqual(quorum["declared_k"], 5)
        self.assertEqual(quorum["verdict"], "consistent")

    def test_declared_k_present_on_unstable_verdict(self):
        results = [_unsat(["A"]), _sat()]
        quorum = analyze_quorum(results, 4)
        self.assertEqual(quorum["declared_k"], 4)
        self.assertEqual(quorum["verdict"], "unstable")


class TestAnalyzeQuorumEmpty(unittest.TestCase):
    def test_empty_raises_value_error(self):
        with self.assertRaises(ValueError):
            analyze_quorum([], 2)


class TestQuorumVerdictsConstant(unittest.TestCase):
    def test_expected_values(self):
        self.assertEqual(
            set(QUORUM_VERDICTS), {"confirmed_unsat", "unstable", "consistent"}
        )


# ---------------------------------------------------------------------------
# synthesize_solve_result
# ---------------------------------------------------------------------------


class TestSynthesizeSolveResult(unittest.TestCase):
    def test_confirmed_unsat_maps_to_unsat_with_core(self):
        quorum = {
            "verdict": "confirmed_unsat",
            "confirmed_core": ["AC-1", "AC-2"],
            "stability": {"reproduced_in": 2, "of": 2},
            "all_cores": [{"core": ["AC-1", "AC-2"], "count": 2}],
        }
        result = synthesize_solve_result(quorum)
        self.assertEqual(result, {"status": "unsat", "unsat_core": ["AC-1", "AC-2"]})

    def test_consistent_maps_to_sat(self):
        quorum = {
            "verdict": "consistent",
            "confirmed_core": None,
            "stability": {"reproduced_in": 0, "of": 2},
            "all_cores": [],
        }
        result = synthesize_solve_result(quorum)
        self.assertEqual(result, {"status": "sat", "unsat_core": []})

    def test_unstable_maps_to_sat_not_unsat(self):
        # Load-bearing D13 cry-wolf rule: an unstable (non-reproducing)
        # contradiction must NOT synthesize to unsat/REVISE-SPEC.
        quorum = {
            "verdict": "unstable",
            "confirmed_core": None,
            "stability": {"reproduced_in": 1, "of": 2},
            "all_cores": [{"core": ["AC-1"], "count": 1}, {"core": [], "count": 1}],
        }
        result = synthesize_solve_result(quorum)
        self.assertEqual(result, {"status": "sat", "unsat_core": []})
        self.assertNotEqual(result["status"], "unsat")


if __name__ == "__main__":
    unittest.main()
