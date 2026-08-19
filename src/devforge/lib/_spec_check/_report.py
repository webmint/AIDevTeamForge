"""_report.py -- render the /spec-check report + atomic write to disk.

Renders ``spec-check.md`` from an already-solved IR: the two-layer surface
(D4) that separates "here is how I read your ACs as logic" (SOFT -- the
LLM's English-to-logic translation, which the human is asked to CHECK) from
"given that reading, these ACs are provably incompatible" (HARD -- the Z3
proof), plus the coverage honesty ledger (D6) and the recommended-not-final
disposition (D3).

Provides:

  SPEC_CHECK_DISPOSITIONS
      The three valid disposition strings: "CONSISTENT", "REVISE-SPEC",
      "DISMISS".

  recommend_disposition(solve_result) -> str
      Maps a solver status to a recommended disposition. Never returns
      "DISMISS" -- that is a human-only override made later, when a human
      judges the *translation* (not the proof) to be wrong.

  render_report(feature, date_str, solve_result, ir, acs, recommended_disposition,
                stability=None, unresolved_subjects=None, spec_sha256=None) -> str
      Full markdown report. Pure rendering -- no solve, no parse, no I/O.
      ``feature`` + ``date_str`` lead the signature, matching the sibling
      renderers (``_grill``/``_review``/``_verify``) so the report can
      self-identify. ``unresolved_subjects`` (Plan 82 D4) is the merged
      "unresolved" list from ``_quorum.merge_subject_resolutions`` -- when
      given and non-empty, renders a ``## UNRESOLVED SUBJECTS`` section;
      omitted/empty renders nothing extra (byte-identical to a report
      produced before this mechanism existed). ``spec_sha256`` (Plan 82
      OQ-2), when given, renders a greppable ``**Spec hash**`` header
      line the finalize gate re-hashes and compares.

  write_spec_check_report(feature_dir, content) -> str
      Atomic write (mkstemp + os.replace) to <feature_dir>/spec-check.md.
      Mirrors _grill/_report.py's write_grill_report.

No LLM call, no z3 call, no CLI wiring here -- this module only renders an
already-built SolveResult + SpecCheckIR (both received as arguments, never
constructed here). Stdlib only -- deliberately does NOT import
``_spec_check._solve`` (which depends on the third-party ``z3`` package) so this
report-rendering module stays dependency-free; ``SolveResult`` is referenced
only in type comments, never imported.

Stdlib only. Python 3.8+. Explicit typing.List / typing.Dict per house
convention -- no PEP 604 / PEP 585 syntax, no ``from __future__ import
annotations``.
"""

import os
import tempfile
from typing import Dict, List

from _spec_check.ir_schema import Atom, Constraint, SpecCheckIR

# ---------------------------------------------------------------------------
# Disposition constants.
# ---------------------------------------------------------------------------

SPEC_CHECK_DISPOSITIONS = ("CONSISTENT", "REVISE-SPEC", "DISMISS")

# The D11 scope boundary line -- rendered verbatim near the top of every
# report.
_SCOPE_LINE = (
    "> **Scope:** /devforge:spec-check is a consistency prover, not a mind-reader. "
    "It checks whether your acceptance criteria contradict *each other* -- "
    "not whether they are what you *meant*. A single coherent-but-wrong AC "
    "will pass."
)

# The D9 reachability honesty note -- rendered whenever the IR contains at
# least one "implication" constraint.
_REACHABILITY_NOTE = (
    "> Note: conditional (IF/WHEN) acceptance criteria are checked under "
    "the assumption their trigger can fire -- the solver does not "
    "independently verify reachability."
)

_SKIPPED_STATUSES = ("skipped_prose", "skipped_unsupported")

# Plan 82 D4: "unresolved_subject" is a FOURTH coverage status, distinct
# from both "formalized" and _SKIPPED_STATUSES above -- every branch below
# that keys off status must be walked to confirm an unresolved_subject row
# lands in neither the formalized nor the skipped bucket. It gets its own
# per-row rendering (with the named subject) in _render_coverage, and its
# own count (J) on the Coverage section's header line.


# ---------------------------------------------------------------------------
# recommend_disposition.
# ---------------------------------------------------------------------------


def recommend_disposition(solve_result):
    # type: (object) -> str
    """Map a solve_result.status to a recommended disposition.

    solve_result is a _spec_check._solve.SolveResult (or any object exposing a
    ``.status`` attribute in {"sat", "unsat", "unknown"}) -- typed as
    ``object`` here (type comment only) so this module does not import
    ``_spec_check._solve`` (see the module docstring).

    "unsat"    -> "REVISE-SPEC" (a contradiction was proven)
    "sat"      -> "CONSISTENT"
    "unknown"  -> "CONSISTENT" (no contradiction was proven -- but see the
                  report's unknown caveat line; none was ruled out either)

    Never returns "DISMISS" -- that is a human-only override made when a
    human judges the *translation* wrong, not something the solver output
    can recommend.
    """
    if solve_result.status == "unsat":
        return "REVISE-SPEC"
    return "CONSISTENT"


# ---------------------------------------------------------------------------
# Atom / constraint readable renderers (D4 layer-a: "how I read it").
# ---------------------------------------------------------------------------


def _atom_to_str(atom):
    # type: (Atom) -> str
    """Render one Atom as a human-readable logic fragment.

    Dispatches on atom.value's Python type (bool is checked before
    int/float since bool is an int subclass):
      - bool value True  -> "<var>"
      - bool value False -> "NOT <var>"
      - str value        -> Enum: "<var> = <value>" / "<var> != <value>"
      - int/float value  -> numeric: "<var> <op> <value>"
    """
    if isinstance(atom.value, bool):
        return atom.var if atom.value else "NOT {0}".format(atom.var)
    # str (Enum) and int/float (numeric) atoms render identically:
    # "<var> <op> <value>".
    return "{0} {1} {2}".format(atom.var, atom.op, atom.value)


def _constraint_to_str(constraint):
    # type: (Constraint) -> str
    """Render one Constraint as a human-readable logic line.

    assertion   -> consequent atoms joined with " AND "
    implication -> "IF <antecedent AND-joined> THEN <consequent AND-joined>"
    """
    consequent_str = " AND ".join(_atom_to_str(a) for a in constraint.consequent)
    if constraint.kind == "assertion":
        return consequent_str
    antecedent_str = " AND ".join(_atom_to_str(a) for a in (constraint.antecedent or []))
    return "IF {0} THEN {1}".format(antecedent_str, consequent_str)


# ---------------------------------------------------------------------------
# render_report -- section helpers.
# ---------------------------------------------------------------------------


def _coverage_map(ir):
    # type: (SpecCheckIR) -> Dict[str, object]
    """Build ac_id -> Coverage, last-write-wins (defensive; validate_ir
    upstream should already guarantee uniqueness)."""
    table = {}
    for cov in ir.coverage:
        table[cov.ac_id] = cov
    return table


def _constraints_by_ac_id(ir):
    # type: (SpecCheckIR) -> Dict[str, List[Constraint]]
    table = {}  # type: Dict[str, List[Constraint]]
    for c in ir.constraints:
        table.setdefault(c.ac_id, []).append(c)
    return table


def _render_stability(stability, out):
    # type: (Dict, List[str]) -> None
    """Render the optional D13 quorum stability line/caveat.

    stability is {"reproduced_in": j, "of": k, "verdict": str}. For any
    verdict other than "unstable", renders a single reproduced-in-j/k
    line. For "unstable", renders a prominent caveat instead -- the
    instability is surfaced here, never folded into the recommended
    disposition (see _quorum.synthesize_solve_result's D13 cry-wolf
    rule).
    """
    reproduced_in = stability["reproduced_in"]
    of = stability["of"]
    if stability.get("verdict") == "unstable":
        out.append(
            "**Formalization unstable:** a contradiction appeared in some "
            "but not a majority of {0}/{1} passes -- NOT treated as "
            "confirmed; re-run `/devforge:spec-check` or inspect the "
            "formalization.".format(reproduced_in, of)
        )
    else:
        out.append(
            "**Formalization stability:** contradiction core reproduced "
            "in {0}/{1} formalization passes.".format(reproduced_in, of)
        )


def _render_recommendation(solve_result, ir, recommended_disposition, stability, out):
    # type: (object, SpecCheckIR, str, object, List[str]) -> None
    out.append("## Recommendation")
    out.append("")

    nothing_formalized = not any(cov.status == "formalized" for cov in ir.coverage)

    if recommended_disposition == "REVISE-SPEC":
        core = ", ".join("`{0}`".format(ac_id) for ac_id in solve_result.unsat_core)
        out.append(
            "**{0}** -- ACs {1} are provably incompatible (see "
            "Contradiction).".format(recommended_disposition, core)
        )
    elif recommended_disposition == "CONSISTENT":
        if nothing_formalized:
            reason = "No formalizable logic found -- nothing was proven."
        else:
            reason = "No contradiction found over the formalized subset."
        out.append("**{0}** -- {1}".format(recommended_disposition, reason))
        if solve_result.status == "unknown":
            out.append(
                "> The solver could not decide (returned `unknown`); no "
                "contradiction was proven, but none was ruled out."
            )
    else:
        # recommended_disposition == "DISMISS" -- never emitted by
        # recommend_disposition(), but render_report validates only against
        # SPEC_CHECK_DISPOSITIONS, so a caller-supplied DISMISS is legal
        # input: it means a human already judged the translation wrong.
        out.append(
            "**{0}** -- the formalized reading was judged incorrect by a "
            "human reviewer; no automated proof backs this "
            "disposition.".format(recommended_disposition)
        )

    if stability is not None:
        _render_stability(stability, out)

    out.append("")


def _render_reading(ir, acs, out):
    # type: (SpecCheckIR, List[Dict], List[str]) -> None
    out.append("## How your ACs were read as logic")
    out.append("")
    out.append(
        "This is the translation to verify -- check that each reading "
        "below actually says what you meant. The proof in the next section "
        "(when present) is only as good as this reading."
    )
    out.append("")

    for var in ir.variables:
        if var.sort == "Enum" and var.domain:
            domain_str = " domain [{0}]".format(", ".join(var.domain))
        else:
            domain_str = ""
        out.append(
            "- `{0}` ({1}) -- {2}{3}".format(var.name, var.sort, var.gloss, domain_str)
        )
    out.append("")

    coverage = _coverage_map(ir)
    constraints = _constraints_by_ac_id(ir)
    has_implication = any(c.kind == "implication" for c in ir.constraints)

    for ac in acs:
        ac_id = ac.get("id", "")
        cov = coverage.get(ac_id)
        if cov is None or cov.status != "formalized":
            continue
        ac_text = ac.get("text", "")
        for c in constraints.get(ac_id, []):
            out.append(
                '- **{0}** "{1}" -> `{2}`'.format(
                    ac_id, ac_text, _constraint_to_str(c)
                )
            )

    out.append("")

    if has_implication:
        out.append(_REACHABILITY_NOTE)
        out.append("")


def _render_contradiction(solve_result, ir, acs, out):
    # type: (object, SpecCheckIR, List[Dict], List[str]) -> None
    if solve_result.status != "unsat":
        return

    text_by_id = {ac.get("id", ""): ac.get("text", "") for ac in acs}

    out.append("## Contradiction")
    out.append("")
    out.append(
        "Given that reading, these acceptance criteria cannot all hold at "
        "once:"
    )
    out.append("")

    constraints = _constraints_by_ac_id(ir)
    for ac_id in solve_result.unsat_core:
        ac_text = text_by_id.get(ac_id, "")
        out.append('- **{0}** "{1}"'.format(ac_id, ac_text))
        for c in constraints.get(ac_id, []):
            out.append("  - `{0}`".format(_constraint_to_str(c)))
    out.append("")
    out.append(
        "This is a deterministic proof over the formalization shown above "
        "-- not a judgment about whether that formalization is what you "
        "meant."
    )
    out.append("")


def _render_coverage(ir, acs, out):
    # type: (SpecCheckIR, List[Dict], List[str]) -> None
    coverage = _coverage_map(ir)

    # Scope N/K/J to acs -- a Coverage entry whose ac_id is not one of the
    # acs (a "ghost" entry) must not inflate these counts past M = len(acs).
    # This mirrors the opposite defensive case in the per-row loop below
    # (an AC present in acs with no matching Coverage entry renders
    # "uncovered" rather than crashing).
    ac_id_set = {ac.get("id", "") for ac in acs}
    n_formalized = sum(
        1
        for cov in ir.coverage
        if cov.ac_id in ac_id_set and cov.status == "formalized"
    )
    n_skipped = sum(
        1
        for cov in ir.coverage
        if cov.ac_id in ac_id_set and cov.status in _SKIPPED_STATUSES
    )
    # Plan 82 D4: J, the third coverage-line term. Computed the SAME way
    # as N/K above -- from THIS report's single representative ir.coverage,
    # not the cross-pass merge (the merge feeds the separate "## UNRESOLVED
    # SUBJECTS" section instead; the two can legitimately disagree when a
    # variable unresolved in the representative pass was resolved in a
    # DIFFERENT, non-representative pass -- see render_report's docstring).
    n_unresolved = sum(
        1
        for cov in ir.coverage
        if cov.ac_id in ac_id_set and cov.status == "unresolved_subject"
    )
    m_total = len(acs)

    out.append("## Coverage")
    out.append("")
    # Back-compat (Plan 82 D4): when n_unresolved == 0, this line renders
    # BYTE-IDENTICAL to the pre-D4 format -- the J term is added ONLY when
    # n_unresolved > 0. The K term (n_skipped) is, and always was,
    # unconditional -- it renders even when zero ("0 unformalizable").
    if n_unresolved > 0:
        subject_noun = "subject" if n_unresolved == 1 else "subjects"
        paren = "({0} unformalizable; {1} unresolved {2}).".format(
            n_skipped, n_unresolved, subject_noun
        )
    else:
        paren = "({0} unformalizable).".format(n_skipped)
    out.append(
        "**Checked {0} of {1} acceptance criteria** {2}".format(
            n_formalized, m_total, paren
        )
    )
    out.append("")

    for ac in acs:
        ac_id = ac.get("id", "")
        cov = coverage.get(ac_id)
        if cov is None:
            out.append("- {0}: uncovered".format(ac_id))
        elif cov.status in _SKIPPED_STATUSES:
            out.append(
                "- {0}: {1} ({2})".format(ac_id, cov.status, cov.reason or "")
            )
        elif cov.status == "unresolved_subject":
            out.append(
                "- {0}: {1} (subject: {2})".format(ac_id, cov.status, cov.subject)
            )
        else:
            out.append("- {0}: {1}".format(ac_id, cov.status))
    out.append("")


# ---------------------------------------------------------------------------
# _render_unresolved_subjects -- Plan 82 D4: the cross-pass MERGED
# unresolved-subjects section.
# ---------------------------------------------------------------------------


def _render_unresolved_subjects(unresolved_subjects, out):
    # type: (List[Dict], List[str]) -> None
    """Render the '## UNRESOLVED SUBJECTS' section.

    unresolved_subjects is the "unresolved" list from
    _quorum.merge_subject_resolutions -- ALREADY merged across every
    formalization pass (D4's any-pass-resolves polarity), so an entry
    here means EVERY pass that discussed the variable failed to resolve
    it. Framed as a FORMALIZATION FAILURE, not a solver result: these
    ACs carry no constraint at all (D1), so Z3 never reasoned about them
    -- this is the honesty gap the whole mechanism exists to surface (see
    ir_schema.SubjectResolution's module docstring for the motivating
    incident).

    Renders ONLY when unresolved_subjects is a non-empty list. None or []
    renders nothing extra -- byte-identical to a report produced before
    this mechanism existed (Plan 82 D4 back-compat).
    """
    if not unresolved_subjects:
        return

    out.append("## UNRESOLVED SUBJECTS")
    out.append("")
    out.append(
        "The acceptance criteria below could NOT be formalized: across "
        "every formalization pass, nothing in the codebase or the spec's "
        "own new-behavior declarations resolves what their subject IS. "
        "This is a FORMALIZATION FAILURE, not a solver result -- these "
        "ACs were never reasoned about by Z3, and any CONSISTENT verdict "
        "elsewhere in this report says nothing about them."
    )
    out.append("")

    for entry in unresolved_subjects:
        ac_ids_str = (
            ", ".join("`{0}`".format(a) for a in entry["ac_ids"])
            or "(none named)"
        )
        out.append(
            "- `{0}` ({1}) -- ACs: {2}".format(
                entry["variable"], entry["gloss"], ac_ids_str
            )
        )
        for p in entry["passes"]:
            if p["outcome"] == "unresolved":
                out.append(
                    "  - pass {0}: searched -- {1}".format(
                        p["pass"], p["searched"]
                    )
                )
            else:
                out.append(
                    "  - pass {0}: claimed resolved, but the citation "
                    "check failed -- {1}".format(
                        p["pass"], p["citation_error"]
                    )
                )
    out.append("")


# ---------------------------------------------------------------------------
# render_report.
# ---------------------------------------------------------------------------


def render_report(
    feature,
    date_str,
    solve_result,
    ir,
    acs,
    recommended_disposition,
    stability=None,
    unresolved_subjects=None,
    spec_sha256=None,
):
    # type: (str, str, object, SpecCheckIR, List[Dict], str, Dict, List[Dict], str) -> str
    """Render the full /spec-check markdown report.

    Parameters
    ----------
    feature : str
        Feature identity (e.g. "specs/001-widget" or a feature slug) --
        printed in the header so the report can self-identify once it
        leaves its directory (PR description, chat paste, backward seed).
        Falls back to "(unknown)" when falsy. Matches the ``feature`` +
        ``date_str``-first parameter ordering used by the sibling
        renderers (``_grill/_report.py``, ``_review/_report.py``,
        ``_verify/_report.py``).
    date_str : str
        "YYYY-MM-DD" date string. Caller-supplied -- this module never
        calls the clock (same convention as the sibling renderers).
    solve_result : _spec_check._solve.SolveResult
        Exposes ``.status`` ("sat"/"unsat"/"unknown") and ``.unsat_core``
        (list of ac_id str, non-empty only when status == "unsat"). Typed
        as ``object`` in the type comment -- this module does not import
        ``_spec_check._solve`` (see module docstring).
    ir : SpecCheckIR
        The formalized IR that was solved.
    acs : list of dict
        The full ``extract_acs`` list (M acceptance criteria) -- used to
        juxtapose original NL text with the logic reading.
    recommended_disposition : str
        One of SPEC_CHECK_DISPOSITIONS.
    stability : dict, optional
        D13 quorum stability descriptor: {"reproduced_in": j, "of": k,
        "verdict": str}. When given, renders one extra line in the
        Recommendation section -- a reproduced-in-j/k line for any
        verdict, or a prominent "unstable" caveat when
        stability["verdict"] == "unstable". When omitted (the default,
        None), renders nothing extra -- byte-identical to the pre-D13
        report shape.
    unresolved_subjects : list of dict, optional
        Plan 82 D4: the "unresolved" list from
        ``_quorum.merge_subject_resolutions`` -- ALREADY merged across
        every formalization pass (resolved-in-any-pass counts as
        resolved; see that function's docstring for the polarity
        rationale). When given and non-empty, renders a
        ``## UNRESOLVED SUBJECTS`` section, placed right after the
        Recommendation section -- maximally visible, since this is
        exactly the case a CONSISTENT verdict can otherwise hide (an AC
        never formalized at all is not "no contradiction found", it is
        "never checked"). When omitted or empty, renders nothing extra --
        byte-identical to a report produced before this mechanism
        existed.
    spec_sha256 : str, optional
        Plan 82 OQ-2: the sha256 hex digest of the spec.md this report
        was produced over. When given, renders a single greppable
        ``**Spec hash**: <hex>`` line in the header (immediately after
        ``**Date**``) that a later gate can re-hash spec.md and compare
        against, to detect drift between when this report was produced
        and when it is consumed. When omitted (the default, None),
        renders nothing extra.

    Returns
    -------
    str
        Full markdown report (ends with a newline).

    Raises
    ------
    ValueError
        If recommended_disposition is not one of SPEC_CHECK_DISPOSITIONS.
    """
    if recommended_disposition not in SPEC_CHECK_DISPOSITIONS:
        raise ValueError(
            "recommended_disposition must be one of {0}, got {1!r}".format(
                list(SPEC_CHECK_DISPOSITIONS), recommended_disposition
            )
        )

    feature_label = feature or "(unknown)"

    out = []  # type: List[str]

    out.append("# Spec-Check: {0}".format(feature_label))
    out.append("")
    out.append("**Feature**: {0}".format(feature_label))
    out.append("**Date**: {0}".format(date_str))
    if spec_sha256:
        out.append("**Spec hash**: {0}".format(spec_sha256))
    out.append("")
    out.append(_SCOPE_LINE)
    out.append("")

    _render_recommendation(solve_result, ir, recommended_disposition, stability, out)
    # Plan 82 D4: placed right after Recommendation, before "How your ACs
    # were read" -- maximally visible, immediately adjacent to the verdict
    # it qualifies. A CONSISTENT verdict here does NOT mean these ACs were
    # checked; it means the solver never saw them.
    _render_unresolved_subjects(unresolved_subjects, out)
    _render_reading(ir, acs, out)
    _render_contradiction(solve_result, ir, acs, out)
    _render_coverage(ir, acs, out)

    return "\n".join(out).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# write_spec_check_report.
# ---------------------------------------------------------------------------


def write_spec_check_report(feature_dir, content):
    # type: (str, str) -> str
    """Atomic write of content to <feature_dir>/spec-check.md.

    Uses mkstemp + os.replace for crash safety. Creates feature_dir if it
    does not exist. Idempotent -- a second call overwrites the file.
    Returns the path written.

    On failure, unlinks the temp file and re-raises.
    """
    os.makedirs(feature_dir, exist_ok=True)
    out_path = os.path.join(feature_dir, "spec-check.md")

    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-spec-check-",
        suffix=".md",
        dir=feature_dir,
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return out_path
