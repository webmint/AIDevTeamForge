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

  merge_subject_resolutions (Plan 82 D4, real-fixture: every per-pass IR
  is built via _consume.parse_ir over a dict, the same path consume-ir
  itself uses):
    resolved-in-one-pass-only          -> resolved overall (D4 polarity)
    unresolved-in-all-passes           -> reported, one "passes" entry
                                           per pass
    name-mismatch-across-passes        -> degrades to per-pass treatment
                                           (the documented bound, no crash)
    citation-failure-in-one-pass,
      valid-citation-in-another        -> resolved overall, but the
                                           failure still surfaces in
                                           "citation_failures"
    ac_ids union across passes' Coverage rows for the SAME unresolved
      variable
    empty irs / length-mismatched citation_errors_by_pass -> ValueError

  is_clean_verdict:
    consistent quorum + zero unresolved + zero citation failures -> True
    consistent quorum + ONE unresolved subject -> False (the single most
      important case -- the exact incident this predicate exists to catch)
    consistent quorum + a citation failure (even with unresolved==[])
      -> False
    confirmed_unsat / unstable quorum -> False regardless of merge
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _spec_check._consume import parse_ir, validate_citations  # noqa: E402
from _spec_check._quorum import (  # noqa: E402
    QUORUM_VERDICTS,
    analyze_quorum,
    is_clean_verdict,
    merge_subject_resolutions,
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


# ---------------------------------------------------------------------------
# merge_subject_resolutions -- Plan 82 D4.
#
# Every per-pass IR below is built via _consume.parse_ir over a plain
# dict -- the SAME producer consume-ir itself uses to build the canonical
# IR merge_subject_resolutions consumes in production (real-fixture
# testing, not a hand-authored dataclass bypass).
# ---------------------------------------------------------------------------


def _pass_ir(variables_raw, coverage_raw=None):
    return parse_ir(
        {
            "variables": variables_raw,
            "constraints": [],
            "coverage": coverage_raw or [],
        }
    )


def _var_unresolved(name, searched, gloss=None):
    return {
        "name": name,
        "sort": "Bool",
        "gloss": gloss or ("gloss-" + name),
        "subject_resolution": {"status": "unresolved", "searched": searched},
    }


def _var_resolved_code(name, citation, locator, gloss=None):
    return {
        "name": name,
        "sort": "Bool",
        "gloss": gloss or ("gloss-" + name),
        "subject_resolution": {
            "status": "resolved",
            "arm": "code",
            "citation": citation,
            "locator": locator,
            "note": "found it",
        },
    }


def _var_resolved_spec(name, citation, gloss=None):
    return {
        "name": name,
        "sort": "Bool",
        "gloss": gloss or ("gloss-" + name),
        "subject_resolution": {
            "status": "resolved",
            "arm": "spec",
            "citation": citation,
            "note": "spec introduces it",
        },
    }


class TestMergeSubjectResolutionsResolvedInAnyPass(unittest.TestCase):
    """D4's whole point: resolved in ANY pass = resolved overall -- the
    polarity-inverted twin of analyze_quorum's majority-reproduction rule
    (a comment in _quorum.py names this inversion explicitly; a future
    reader must not "unify" merge_subject_resolutions with analyze_quorum
    -- they intentionally disagree on how many witnesses are enough)."""

    def test_resolved_in_one_pass_only_is_resolved_overall(self):
        pass1 = _pass_ir([_var_unresolved("X", "grepped src/, 0 hits")])
        pass2 = _pass_ir([_var_resolved_code("X", "src/x.py", "def x")])
        merge = merge_subject_resolutions([pass1, pass2], [[], []])
        self.assertEqual(merge["unresolved"], [])
        self.assertEqual(merge["resolved"], ["X"])

    def test_resolved_via_spec_arm_in_second_pass_also_counts(self):
        pass1 = _pass_ir([_var_unresolved("Y", "nothing found")])
        pass2 = _pass_ir([_var_resolved_spec("Y", "AC-3")])
        merge = merge_subject_resolutions([pass1, pass2], [[], []])
        self.assertEqual(merge["unresolved"], [])
        self.assertEqual(merge["resolved"], ["Y"])


class TestMergeSubjectResolutionsUnresolvedInAllPasses(unittest.TestCase):
    def test_unresolved_in_every_pass_is_reported(self):
        pass1 = _pass_ir([_var_unresolved("Z", "searched terms A, 0 hits")])
        pass2 = _pass_ir([_var_unresolved("Z", "searched terms B, 0 hits")])
        merge = merge_subject_resolutions([pass1, pass2], [[], []])
        self.assertEqual(len(merge["unresolved"]), 1)
        entry = merge["unresolved"][0]
        self.assertEqual(entry["variable"], "Z")
        self.assertEqual(entry["gloss"], "gloss-Z")
        # One "passes" entry per pass, in pass order, each carrying that
        # pass' OWN searched text (D4's "each pass's searched record").
        self.assertEqual(
            entry["passes"],
            [
                {
                    "pass": 1,
                    "outcome": "unresolved",
                    "searched": "searched terms A, 0 hits",
                    "citation_error": None,
                },
                {
                    "pass": 2,
                    "outcome": "unresolved",
                    "searched": "searched terms B, 0 hits",
                    "citation_error": None,
                },
            ],
        )
        self.assertEqual(merge["resolved"], [])

    def test_ac_ids_unioned_across_passes_coverage_rows(self):
        pass1 = _pass_ir(
            [_var_unresolved("W", "s1")],
            [{"ac_id": "AC-5", "status": "unresolved_subject", "subject": "W"}],
        )
        pass2 = _pass_ir(
            [_var_unresolved("W", "s2")],
            [{"ac_id": "AC-9", "status": "unresolved_subject", "subject": "W"}],
        )
        merge = merge_subject_resolutions([pass1, pass2], [[], []])
        self.assertEqual(merge["unresolved"][0]["ac_ids"], ["AC-5", "AC-9"])


class TestMergeSubjectResolutionsNameMismatchBound(unittest.TestCase):
    """The documented, honest bound: two passes modeling the SAME
    underlying subject under DIFFERENT variable names are treated as two
    UNRELATED variables -- a genuine cross-pass resolution is missed, but
    the merge degrades to per-pass treatment rather than crashing."""

    def test_different_names_do_not_help_each_other(self):
        pass1 = _pass_ir([_var_unresolved("shipped_state", "grepped, 0 hits")])
        pass2 = _pass_ir([_var_resolved_code("order_shipped", "src/o.py", "def o")])
        merge = merge_subject_resolutions([pass1, pass2], [[], []])
        # "shipped_state" is unresolved in pass 1, and pass 2 never even
        # mentions that NAME -- pass 2's resolution of "order_shipped"
        # does not reach it.
        self.assertEqual(
            [e["variable"] for e in merge["unresolved"]], ["shipped_state"]
        )
        self.assertEqual(merge["resolved"], ["order_shipped"])


class TestMergeSubjectResolutionsCitationFold(unittest.TestCase):
    """D4 rule 2: a failing citation folds a claimed "resolved" record
    into a MISS for THAT pass only -- real validate_citations() output
    against a real tmp-dir workspace root, not a hand-authored error
    string."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.workspace_root = self._tmpdir.name

    def test_citation_failure_in_one_pass_valid_in_another_resolves_overall(self):
        # Pass 1's citation points at a file that does not exist under
        # workspace_root -- validate_citations() genuinely fails it.
        pass1 = _pass_ir([_var_resolved_code("Q", "src/missing.py", "def q")])
        errors1 = validate_citations(pass1, self.workspace_root)
        self.assertEqual(len(errors1), 1)
        self.assertIn("does not exist", errors1[0])

        # Pass 2's citation is real and matches.
        real_path = os.path.join(self.workspace_root, "src")
        os.makedirs(real_path, exist_ok=True)
        with open(os.path.join(real_path, "real.py"), "w", encoding="utf-8") as fh:
            fh.write("def q():\n    pass\n")
        pass2 = _pass_ir([_var_resolved_code("Q", "src/real.py", "def q")])
        errors2 = validate_citations(pass2, self.workspace_root)
        self.assertEqual(errors2, [])

        merge = merge_subject_resolutions([pass1, pass2], [errors1, errors2])
        # Resolved overall (pass 2 is a clean witness) --
        self.assertEqual(merge["unresolved"], [])
        self.assertEqual(merge["resolved"], ["Q"])
        # -- but the citation failure itself still surfaces, independent
        # of the overall per-variable outcome (is_clean_verdict reads
        # this field on its own).
        self.assertEqual(merge["citation_failures"], errors1)

    def test_citation_failure_in_only_pass_is_reported_unresolved(self):
        pass1 = _pass_ir([_var_resolved_code("R", "src/nope.py", "def r")])
        errors1 = validate_citations(pass1, self.workspace_root)
        merge = merge_subject_resolutions([pass1], [errors1])
        self.assertEqual(len(merge["unresolved"]), 1)
        entry = merge["unresolved"][0]
        self.assertEqual(entry["variable"], "R")
        self.assertEqual(entry["passes"][0]["outcome"], "citation_failed")
        self.assertEqual(entry["passes"][0]["citation_error"], errors1[0])
        self.assertEqual(merge["citation_failures"], errors1)


class TestMergeSubjectResolutionsNoOpinion(unittest.TestCase):
    def test_pass_without_subject_resolution_is_neither_hit_nor_miss(self):
        # A Variable with subject_resolution=None (historical / not yet
        # recorded) contributes nothing either way.
        pass1 = _pass_ir([{"name": "V", "sort": "Int", "gloss": "g"}])
        merge = merge_subject_resolutions([pass1], [[]])
        self.assertEqual(merge["unresolved"], [])
        self.assertEqual(merge["resolved"], [])


class TestMergeSubjectResolutionsErrors(unittest.TestCase):
    def test_empty_irs_raises_value_error(self):
        with self.assertRaises(ValueError):
            merge_subject_resolutions([], [])

    def test_length_mismatch_raises_value_error(self):
        pass1 = _pass_ir([_var_unresolved("X", "s")])
        with self.assertRaises(ValueError):
            merge_subject_resolutions([pass1], [[], []])


# ---------------------------------------------------------------------------
# is_clean_verdict -- Plan 82 D5.
# ---------------------------------------------------------------------------


class TestIsCleanVerdict(unittest.TestCase):
    def test_consistent_and_fully_clean_merge_is_clean(self):
        merge = {"unresolved": [], "resolved": ["X"], "citation_failures": []}
        self.assertTrue(is_clean_verdict({"verdict": "consistent"}, merge))

    def test_consistent_quorum_but_one_unresolved_subject_is_not_clean(self):
        # THE SINGLE MOST IMPORTANT CASE: this is the exact motivating
        # incident's shape -- Z3 found nothing wrong (verdict=consistent)
        # ONLY because an AC's subject was never formalized in the first
        # place. This predicate exists specifically to catch it.
        merge = {
            "unresolved": [
                {
                    "variable": "shipped_state",
                    "gloss": "order has shipped",
                    "ac_ids": ["AC-4"],
                    "passes": [
                        {
                            "pass": 1,
                            "outcome": "unresolved",
                            "searched": "grepped, 0 hits",
                            "citation_error": None,
                        }
                    ],
                }
            ],
            "resolved": [],
            "citation_failures": [],
        }
        self.assertFalse(is_clean_verdict({"verdict": "consistent"}, merge))

    def test_consistent_quorum_but_citation_failure_is_not_clean(self):
        # A citation failure fails the predicate on its OWN dimension,
        # independent of "unresolved" -- even when the variable it named
        # ended up resolved overall via a different pass.
        merge = {
            "unresolved": [],
            "resolved": ["Q"],
            "citation_failures": [
                "variable 'Q': cited file 'src/missing.py' does not exist "
                "under workspace root"
            ],
        }
        self.assertFalse(is_clean_verdict({"verdict": "consistent"}, merge))

    def test_confirmed_unsat_quorum_is_not_clean_even_with_empty_merge(self):
        merge = {"unresolved": [], "resolved": [], "citation_failures": []}
        self.assertFalse(is_clean_verdict({"verdict": "confirmed_unsat"}, merge))

    def test_unstable_quorum_is_not_clean_even_with_empty_merge(self):
        merge = {"unresolved": [], "resolved": [], "citation_failures": []}
        self.assertFalse(is_clean_verdict({"verdict": "unstable"}, merge))

    def test_end_to_end_via_real_merge_and_analyze_quorum(self):
        # Real producers on both sides: analyze_quorum for the quorum
        # verdict, merge_subject_resolutions for the merge.
        quorum = analyze_quorum([{"status": "sat", "unsat_core": []}], 1)
        pass1 = _pass_ir([_var_resolved_code("S", "src/s.py", "def s")])
        merge = merge_subject_resolutions([pass1], [[]])
        self.assertTrue(is_clean_verdict(quorum, merge))
        # This same real-producer call doubles as confirmation that the
        # existing caller shapes (analyze_quorum's own return dict, and
        # _cli.py's --stability-file-narrowed dict which also always
        # carries "verdict") never trip the new shape check below.

    def test_quorum_missing_verdict_key_raises_type_error(self):
        merge = {"unresolved": [], "resolved": [], "citation_failures": []}
        with self.assertRaises(TypeError):
            is_clean_verdict({"reproduced_in": 2, "of": 2}, merge)

    def test_quorum_not_a_dict_raises_type_error(self):
        merge = {"unresolved": [], "resolved": [], "citation_failures": []}
        with self.assertRaises(TypeError):
            is_clean_verdict(["consistent"], merge)

    def test_merge_missing_unresolved_key_raises_type_error(self):
        with self.assertRaises(TypeError):
            is_clean_verdict(
                {"verdict": "consistent"}, {"citation_failures": []}
            )

    def test_merge_missing_citation_failures_key_raises_type_error(self):
        with self.assertRaises(TypeError):
            is_clean_verdict({"verdict": "consistent"}, {"unresolved": []})

    def test_merge_not_a_dict_raises_type_error(self):
        with self.assertRaises(TypeError):
            is_clean_verdict({"verdict": "consistent"}, ["not", "a", "dict"])

    def test_existing_cli_caller_shapes_do_not_raise(self):
        # Confirms the render-report CLI caller's exact shapes (see
        # _cli.py cmd_render_report: _stability_from_data()'s narrowed
        # {"reproduced_in", "of", "verdict"} dict, and
        # merge_subject_resolutions()'s full return dict) both pass the
        # new shape check cleanly -- this predicate is not gated behind
        # the full analyze_quorum() shape.
        stability_like = {"reproduced_in": 2, "of": 2, "verdict": "consistent"}
        pass1 = _pass_ir([_var_resolved_code("T", "src/t.py", "def t")])
        merge = merge_subject_resolutions([pass1], [[]])
        try:
            is_clean_verdict(stability_like, merge)
        except TypeError:
            self.fail("is_clean_verdict raised TypeError on a valid caller shape")


if __name__ == "__main__":
    unittest.main()
