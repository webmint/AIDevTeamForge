"""_quorum.py -- D13 formalization-reproducibility (quorum) analysis.

Z3 is deterministic, but the English-to-IR *formalization* step is a
stochastic LLM call: the same spec.md can formalize differently across
independent passes, and a spurious (or a genuinely fragile) contradiction
can flip the recommended disposition depending on which pass happened to
run. Mitigation (D13): the orchestrator formalizes + solves the same ACs
k times (a "quorum") and this module analyzes the k SolveResult-shaped
dicts to decide whether an "unsat" reading actually REPRODUCES across a
majority of passes, or whether the passes merely disagree.

Provides:

  analyze_quorum(solve_results, k) -> dict
      Pure analysis over k solve-result dicts. No LLM, no z3, no I/O.
      Returns a verdict ("confirmed_unsat" / "unstable" / "consistent"),
      the majority-reproduced unsat core (when any), a stability
      descriptor, every distinct unsat core seen (D4 transparency -- the
      "how your ACs were read" honesty principle extends to "how
      reproducible was that reading"), and the caller's declared pass
      count (``declared_k``) alongside the actual count used for the
      math -- a caller-declared/actual mismatch (e.g. a dropped pass) is
      never silently absorbed; it is visible in the returned dict so a
      downstream consumer can flag it (D13's whole value is a
      trustworthy count).

  synthesize_solve_result(quorum) -> dict
      Maps an analyze_quorum() verdict to a canonical
      {"status", "unsat_core"} dict compatible with
      _report.recommend_disposition / render_report's existing
      SolveResult-shaped input -- so the verdict-rendering path is reused
      unchanged. The load-bearing D13 "cry-wolf" rule lives here:
      "unstable" synthesizes to "sat" (CONSISTENT), NOT "unsat"
      (REVISE-SPEC) -- a contradiction that only some passes produced is
      NOT confirmed, and must not recommend spec revision. The
      instability itself is surfaced separately, as a report caveat
      (_report.render_report's optional ``stability`` parameter), never
      folded into the verdict.

No LLM call, no z3 call, no CLI wiring, no I/O here -- this module only
analyzes already-collected solve-result dicts (the k-loop itself is
main.md's orchestration job, per the Phase-7 scope boundary).

Stdlib only. Python 3.8+. Explicit typing.List / typing.Dict per house
convention -- no PEP 604 / PEP 585 syntax, no ``from __future__ import
annotations``.
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Verdict constants.
# ---------------------------------------------------------------------------

QUORUM_VERDICTS = ("confirmed_unsat", "unstable", "consistent")


# ---------------------------------------------------------------------------
# analyze_quorum.
# ---------------------------------------------------------------------------


def analyze_quorum(solve_results, k):
    # type: (List[Dict], int) -> Dict
    """Analyze k solve-result dicts for cross-pass reproducibility.

    Parameters
    ----------
    solve_results : list of dict
        Each dict is a solve-verb-stdout shape: {"status": str,
        "unsat_core": List[str]}. May be empty only if the caller passes
        no passes at all -- which is a caller bug (see Raises).
    k : int or None
        The DECLARED pass count. May differ from len(solve_results) (a
        caller bug, e.g. a dropped pass); this function never crashes on
        that mismatch. All majority arithmetic and the returned
        "stability"/"of" field use ``len(solve_results)`` (the ACTUAL
        count). The declared ``k`` itself is not consulted for the math
        -- but it IS carried through unchanged into the returned dict's
        "declared_k" field (falling back to the actual count when ``k``
        is None) so a caller/actual mismatch stays visible to a
        downstream consumer instead of being silently absorbed.

    Returns
    -------
    dict
        {
          "verdict": "confirmed_unsat" | "unstable" | "consistent",
          "confirmed_core": <sorted list of ac_ids> | None,
          "stability": {"reproduced_in": <int>, "of": <actual_k int>},
          "all_cores": [{"core": <sorted list>, "count": <int>}, ...],
          "declared_k": <int>,
        }

    Raises
    ------
    ValueError
        If solve_results is empty -- a quorum needs at least one pass.
    """
    if not solve_results:
        raise ValueError(
            "analyze_quorum: solve_results must not be empty (a quorum "
            "needs at least one pass)"
        )

    actual_k = len(solve_results)
    declared_k = k if k is not None else actual_k

    # Tally exact-core occurrences. A sat/unknown pass contributes no
    # core (None) and is excluded from the tally entirely.
    core_counts = {}  # type: Dict[frozenset, int]
    for result in solve_results:
        if result.get("status") == "unsat":
            core = frozenset(result.get("unsat_core") or [])
            core_counts[core] = core_counts.get(core, 0) + 1

    # all_cores: every distinct unsat core seen, count-desc then sorted
    # (sorted-tuple order) for a deterministic tie-break and stable
    # rendering (D4 transparency).
    all_cores = [
        {"core": sorted(core), "count": count}
        for core, count in core_counts.items()
    ]
    all_cores.sort(key=lambda entry: (-entry["count"], entry["core"]))

    if not core_counts:
        # Zero passes were unsat -- nothing to reproduce.
        return {
            "verdict": "consistent",
            "confirmed_core": None,
            "stability": {"reproduced_in": 0, "of": actual_k},
            "all_cores": [],
            "declared_k": declared_k,
        }

    majority_threshold = actual_k // 2
    max_count = max(core_counts.values())

    # A core is reproduced if its count is a STRICT majority of the
    # actual pass count: count > actual_k // 2. Because a strict
    # majority is unique when it exists (two disjoint core-sets cannot
    # both exceed half of the same total), at most one core can satisfy
    # this -- the tie-break (highest count, then sorted-tuple order) is
    # a defensive guard, never actually exercised by a real majority.
    if max_count > majority_threshold:
        # all_cores is already sorted count-desc then sorted-tuple order,
        # so its head is exactly the tie-broken winner.
        confirmed_core = all_cores[0]["core"]
        return {
            "verdict": "confirmed_unsat",
            "confirmed_core": confirmed_core,
            "stability": {"reproduced_in": max_count, "of": actual_k},
            "all_cores": all_cores,
            "declared_k": declared_k,
        }

    # At least one pass was unsat but no core reached majority: the
    # passes disagree on whether/where the contradiction is.
    return {
        "verdict": "unstable",
        "confirmed_core": None,
        "stability": {"reproduced_in": max_count, "of": actual_k},
        "all_cores": all_cores,
        "declared_k": declared_k,
    }


# ---------------------------------------------------------------------------
# synthesize_solve_result.
# ---------------------------------------------------------------------------


def synthesize_solve_result(quorum):
    # type: (Dict) -> Dict
    """Map an analyze_quorum() verdict to a canonical solve-result dict.

    Drives the EXISTING _report.recommend_disposition / render_report
    verdict path unchanged -- this function only decides WHICH
    (status, unsat_core) pair represents the quorum's outcome; it does
    not touch recommend_disposition itself.

      confirmed_unsat -> {"status": "unsat", "unsat_core": confirmed_core}
                          (-> recommend_disposition returns REVISE-SPEC)
      consistent       -> {"status": "sat", "unsat_core": []}
                          (-> CONSISTENT)
      unstable          -> {"status": "sat", "unsat_core": []}
                          (-> CONSISTENT -- BY DESIGN, the D13 cry-wolf
                          rule: a non-reproducing one-off contradiction
                          must NOT recommend REVISE-SPEC. The instability
                          is surfaced separately as a report caveat via
                          render_report's ``stability`` parameter, never
                          folded into the recommended disposition.)
    """
    verdict = quorum.get("verdict")
    if verdict == "confirmed_unsat":
        return {"status": "unsat", "unsat_core": quorum.get("confirmed_core") or []}
    # "consistent" and "unstable" both synthesize to sat/CONSISTENT.
    return {"status": "sat", "unsat_core": []}
