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

  merge_subject_resolutions(irs, citation_errors_by_pass) -> dict
      Plan 82 D4: merges k passes' Variable.subject_resolution records,
      matched by variable NAME, under a DELIBERATELY INVERTED polarity
      vs analyze_quorum above -- resolved in ANY pass counts as resolved
      overall; a subject is reported UNRESOLVED only when every pass that
      discusses it fails to resolve it. See the large comment ahead of
      the function for the full "why the polarity flips" rationale --
      kept as a visibly separate function from analyze_quorum on purpose.

  is_clean_verdict(quorum, merge) -> bool
      Plan 82 D5/composite predicate: CLEAN iff the quorum verdict is
      "consistent" AND merge_subject_resolutions() found zero unresolved
      subjects AND zero mechanical citation failures across all passes.
      Exposed so a caller (the render-report CLI verb) can branch on one
      mechanical boolean instead of re-deriving the three-way AND in
      prose.

No LLM call, no z3 call, no CLI wiring, no I/O here -- this module only
analyzes already-collected solve-result dicts / already-parsed IR objects
(the k-loop itself is main.md's orchestration job, per the Phase-7 scope
boundary).

Stdlib only. Python 3.8+. Explicit typing.List / typing.Dict per house
convention -- no PEP 604 / PEP 585 syntax, no ``from __future__ import
annotations``.
"""

from typing import Dict, List

from _spec_check._consume import citation_errors_by_variable
from _spec_check.ir_schema import SpecCheckIR  # noqa: F401 -- type comments only

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


# ---------------------------------------------------------------------------
# merge_subject_resolutions -- Plan 82 D4: any-pass subject-resolution
# merge.
#
# THIS IS A DIFFERENT, DELIBERATELY INVERTED POLARITY FROM analyze_quorum
# ABOVE -- kept as a SEPARATE function on purpose, never folded together:
#
#   analyze_quorum (unsat-core quorum): a CONTRADICTION is a claim that
#   something is IMPOSSIBLE. A one-off contradiction that only ONE pass
#   produced must NOT become a recommendation (D13's cry-wolf rule) -- so
#   analyze_quorum requires a STRICT MAJORITY of passes to reproduce the
#   SAME core before treating it as confirmed.
#
#   merge_subject_resolutions (this function): a subject resolution is an
#   EXISTENCE claim -- "this construction site exists" / "this spec
#   section introduces this state". Existence needs only ONE witness: if
#   even one independent formalization pass mechanically validates a
#   construction site for a variable, that variable's subject EXISTS,
#   full stop -- a second pass failing to find it (wrong search terms, or
#   simply not formalizing that AC at all) does not un-prove the first
#   pass's finding. So resolution here is RESOLVED-IN-ANY-PASS, the
#   polarity-inverted twin of the majority-reproduction rule above.
#   "UNRESOLVED-SUBJECT" is reported ONLY when every pass that even
#   discusses a subject fails to resolve it.
#
# Do not "simplify" these two into one shared quorum helper -- the
# majority-vs-any-witness split is the entire point.
# ---------------------------------------------------------------------------


def merge_subject_resolutions(irs, citation_errors_by_pass):
    # type: (List[SpecCheckIR], List[List[str]]) -> Dict
    """Merge k passes' Variable.subject_resolution records, matched by NAME.

    Parameters
    ----------
    irs : list of SpecCheckIR
        One already-parsed (consume-ir-validated) IR per pass, in pass
        order (irs[0] is pass 1, etc.). Must be non-empty.
    citation_errors_by_pass : list of list of str
        citation_errors_by_pass[i] is THAT pass's validate_citations()
        output (the D3 mechanical check) -- typically the "citation_errors"
        key already embedded in that pass's canonical IR JSON by the
        consume-ir CLI verb. Must be the same length as ``irs``; an empty
        per-pass list means "no citation errors that pass" (not "not
        checked").

    Cross-pass matching bound (HONEST, not a crash risk): variables are
    matched ACROSS passes by NAME only -- there is no semantic co-
    reference beyond the string the formalizer chose. Two independent
    passes that model the SAME underlying subject under two DIFFERENT
    variable names (e.g. pass 1's "shipped_state" vs pass 2's
    "order_shipped") are treated as two UNRELATED variables: pass 2's
    resolution of "order_shipped" does NOT help resolve pass 1's
    "shipped_state" -- the merge silently degrades to per-pass treatment
    for that pair, never crashes. This is a known, documented limit of
    name-based matching, not a defect to "fix" here.

    Returns
    -------
    dict
        {
          "unresolved": [
            {
              "variable": <name>,
              "gloss": <str, from the first pass that declared it>,
              "ac_ids": <sorted list of ac_id str, union across passes'
                         Coverage rows naming this variable as
                         unresolved_subject>,
              "passes": [
                {"pass": <1-based int>, "outcome": "unresolved"|
                 "citation_failed", "searched": <str|None>,
                 "citation_error": <str|None>},
                ...  # one entry per pass that discussed this variable
                     # and did NOT resolve it
              ],
            },
            ...
          ],  # sorted by variable name; a variable resolved in ANY pass
              # is excluded entirely, regardless of how many other
              # passes missed it (D4's whole point)
          "resolved": <sorted list of variable names resolved in at
                        least one pass>,
          "citation_failures": <sorted, deduplicated union of every
                                 citation error string across ALL passes
                                 -- unlike "unresolved" above, this is
                                 NOT folded away by a later pass's clean
                                 resolution; see is_clean_verdict's
                                 docstring for why>,
        }

    Raises
    ------
    ValueError
        If ``irs`` is empty, or ``citation_errors_by_pass`` is not the
        same length as ``irs``.
    """
    if not irs:
        raise ValueError(
            "merge_subject_resolutions: irs must not be empty (the merge "
            "needs at least one pass)"
        )
    if len(citation_errors_by_pass) != len(irs):
        raise ValueError(
            "merge_subject_resolutions: citation_errors_by_pass must be "
            "the same length as irs ({0} != {1})".format(
                len(citation_errors_by_pass), len(irs)
            )
        )

    gloss_by_name = {}  # type: Dict[str, str]
    resolved_names = set()  # type: set
    miss_entries_by_name = {}  # type: Dict[str, List[Dict]]
    ac_ids_by_name = {}  # type: Dict[str, set]

    for i, ir in enumerate(irs):
        pass_num = i + 1
        citation_map = citation_errors_by_variable(citation_errors_by_pass[i])

        for var in ir.variables:
            sr = var.subject_resolution
            if sr is None:
                # This pass has nothing to say about this variable name --
                # not a hit, not a miss. See this function's docstring on
                # the name-matching bound: a different pass may model the
                # SAME underlying subject under a different name, which is
                # indistinguishable from "not discussed" at this layer.
                continue

            if var.name not in gloss_by_name:
                gloss_by_name[var.name] = var.gloss

            citation_failed = sr.arm == "code" and var.name in citation_map
            if sr.status == "resolved" and not citation_failed:
                resolved_names.add(var.name)
                continue

            # A MISS for THIS pass: either genuinely "unresolved", or a
            # "resolved" record whose arm="code" citation failed
            # mechanical validation (D4 rule 2 -- folded into a miss for
            # this pass only; a different pass may still resolve it).
            if sr.status == "resolved":
                miss_entries_by_name.setdefault(var.name, []).append(
                    {
                        "pass": pass_num,
                        "outcome": "citation_failed",
                        "searched": None,
                        "citation_error": citation_map[var.name],
                    }
                )
            else:
                miss_entries_by_name.setdefault(var.name, []).append(
                    {
                        "pass": pass_num,
                        "outcome": "unresolved",
                        "searched": sr.searched,
                        "citation_error": None,
                    }
                )

        for cov in ir.coverage:
            if cov.status == "unresolved_subject":
                ac_ids_by_name.setdefault(cov.subject, set()).add(cov.ac_id)

    unresolved = []
    for name in sorted(miss_entries_by_name):
        if name in resolved_names:
            continue  # D4: resolved in ANY pass -> resolved overall.
        unresolved.append(
            {
                "variable": name,
                "gloss": gloss_by_name.get(name, ""),
                "ac_ids": sorted(ac_ids_by_name.get(name, set())),
                "passes": miss_entries_by_name[name],
            }
        )

    citation_failures = sorted(
        {err for errs in citation_errors_by_pass for err in errs}
    )

    return {
        "unresolved": unresolved,
        "resolved": sorted(resolved_names),
        "citation_failures": citation_failures,
    }


# ---------------------------------------------------------------------------
# is_clean_verdict -- Plan 82 D5: composite clean-verdict predicate.
# ---------------------------------------------------------------------------


def is_clean_verdict(quorum, merge):
    # type: (Dict, Dict) -> bool
    """CLEAN iff quorum-stable "consistent" AND zero unresolved subjects
    (post-merge) AND zero mechanical citation failures (across all passes).

    Parameters
    ----------
    quorum : dict
        Any dict exposing a top-level "verdict" key -- analyze_quorum()'s
        own return dict qualifies directly, as does render-report's
        already-narrowed --stability-file dict ({"reproduced_in", "of",
        "verdict"}). Only the "verdict" key is read.
    merge : dict
        merge_subject_resolutions()'s return dict. Only "unresolved" and
        "citation_failures" are read.

    THE SINGLE MOST IMPORTANT CASE this predicate exists for: a quorum
    verdict of "consistent" (Z3 proved no contradiction) is NOT, on its
    own, a clean result -- if merge["unresolved"] is non-empty, some AC's
    subject was never formalized into a constraint in the first place, so
    there was nothing for Z3 to even contradict. That is exactly the
    motivating incident this whole mechanism exists to catch (see
    ir_schema.SubjectResolution's module docstring): a preservation AC
    over a state nothing constructs, silently reported "consistent". This
    predicate MUST return False in that case, and a test pins exactly
    this shape -- do not "simplify" the AND below to just the quorum
    verdict; that would silently re-introduce the incident.

    A non-empty merge["citation_failures"] fails the predicate
    independently of merge["unresolved"] -- even a variable that ended up
    resolved via a DIFFERENT pass still had a mechanical citation failure
    SOMEWHERE (see merge_subject_resolutions' docstring: citation_failures
    is a straight union, never folded away by a later pass's clean
    resolution), and that mechanical miss is surfaced here regardless of
    whether it changed the overall per-variable outcome.

    Raises
    ------
    TypeError
        If ``quorum`` is not a dict exposing "verdict", or ``merge`` is
        not a dict exposing both "unresolved" and "citation_failures". A
        cheap shape check -- this predicate feeds a gate-adjacent boolean
        (the render-report ack's "clean" field), so a caller-side typo or
        a wrong-shaped input silently computing a plausible-looking False
        (from ``.get()`` defaults) is worse than a loud, immediate
        TypeError.
    """
    if not isinstance(quorum, dict) or "verdict" not in quorum:
        raise TypeError(
            "is_clean_verdict: quorum must be a dict with a 'verdict' "
            "key, got {0!r}".format(quorum)
        )
    if (
        not isinstance(merge, dict)
        or "unresolved" not in merge
        or "citation_failures" not in merge
    ):
        raise TypeError(
            "is_clean_verdict: merge must be a dict with 'unresolved' and "
            "'citation_failures' keys, got {0!r}".format(merge)
        )

    return (
        quorum.get("verdict") == "consistent"
        and len(merge.get("unresolved", [])) == 0
        and len(merge.get("citation_failures", [])) == 0
    )
