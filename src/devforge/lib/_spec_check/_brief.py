"""_brief.py -- render the LLM formalization brief for /spec-check.

Provides ``render_formalize_brief(acs) -> str``: assembles the text the
orchestrator hands to the ``spec-formalizer`` Task. The brief contains the
numbered AC list plus the exact machine-readable OUTPUT CONTRACT (the JSON
shape) so the downstream ``_consume.parse_ir`` parser can read the LLM's
response.

Pure string rendering. No I/O, no LLM call, no JSON parsing -- this module
only builds the prompt text; ``_consume.py`` (a sibling module in this same
subpackage) parses what comes back.

Worked EXAMPLES are deliberately NOT included here -- they live in a later
phase's ``references/formalization-guidance.md``, injected by the command.
This brief stays to the AC list + the machine contract + a short rules
reminder, per the phase-3 spec.

Stdlib only. Python 3.8+. Explicit typing.List / typing.Dict per house
convention -- no PEP 604 / PEP 585 syntax, no ``from __future__ import
annotations``.
"""

from typing import Dict, List

from _spec_check.ir_schema import (
    COMPARISON_OPS,
    CONSTRAINT_KINDS,
    COVERAGE_STATUSES,
    SORTS,
    SUBJECT_RESOLUTION_ARMS,
    SUBJECT_RESOLUTION_STATUSES,
)

# ---------------------------------------------------------------------------
# render_formalize_brief.
# ---------------------------------------------------------------------------


def render_formalize_brief(acs):
    # type: (List[Dict]) -> str
    """Render the LLM formalization brief.

    Parameters
    ----------
    acs : list of dict
        The ``extract_acs`` output -- each dict at minimum carries ``id`` and
        ``text``. ``subsection`` (if present and non-empty) is rendered
        alongside the AC so the formalizer can apply the subsection-keyed
        preservation trigger below; ``checked`` is ignored here. A dict
        missing ``checked`` / ``subsection`` does not crash this renderer --
        an absent or empty ``subsection`` simply renders the AC as it did
        before this key existed.

    Returns
    -------
    str
        The full brief text (ends with a newline). Renders the OUTPUT
        CONTRACT even when ``acs`` is empty.
    """
    out = []  # type: List[str]

    out.append(
        "Formalize each acceptance criterion below into the constraint IR "
        "described in the OUTPUT CONTRACT. Emit exactly ONE JSON object as "
        "your response -- no prose before or after it."
    )
    out.append("")

    # -- Numbered AC list --------------------------------------------------
    out.append("## Acceptance Criteria")
    out.append("")
    if acs:
        for ac in acs:
            ac_id = ac.get("id", "")
            ac_text = ac.get("text", "")
            subsection = ac.get("subsection", "")
            if subsection:
                out.append(
                    "**{0}** ({1}): {2}".format(ac_id, subsection, ac_text)
                )
            else:
                out.append("**{0}**: {1}".format(ac_id, ac_text))
    else:
        out.append("(no acceptance criteria found)")
    out.append("")

    # -- OUTPUT CONTRACT -----------------------------------------------------
    out.append("## OUTPUT CONTRACT")
    out.append("")
    out.append(
        "Emit one JSON object with exactly these three top-level keys, each "
        "a JSON array (all three required, even if empty):"
    )
    out.append("")
    out.append("- `variables`: array of variable declarations")
    out.append("- `constraints`: array of constraint declarations")
    out.append("- `coverage`: array of per-AC coverage ledger entries")
    out.append("")

    out.append("### variables[]")
    out.append("")
    out.append(
        "Each element: `{\"name\": str, \"sort\": one of "
        + " | ".join(SORTS)
        + ", \"gloss\": str, \"domain\": [str, ...]}`."
    )
    out.append(
        "`gloss` is REQUIRED -- a plain-English description of the "
        "real-world quantity this variable represents. `domain` is required "
        "ONLY when `sort` is `Enum` (a non-empty list of member names); "
        "omit it for the other three sorts. Declare each real-world "
        "quantity ONCE and reuse the same `name` across every AC that "
        "refers to it (co-reference -- do not re-declare the same "
        "quantity under a different name in a later AC)."
    )
    out.append(
        "`subject_resolution` is REQUIRED on every variable: "
        "`{\"status\": one of "
        + " | ".join(SUBJECT_RESOLUTION_STATUSES)
        + ", ...}`. It records how the variable's subject -- what in "
        "the code or spec produces the state it models -- was resolved "
        "BEFORE this variable is used in any constraint."
    )
    out.append(
        "Resolved via the code arm (an existing construction site): "
        "`{\"status\": \"resolved\", \"arm\": \"code\", \"citation\": "
        "\"<repo-relative path>\", \"locator\": \"<symbol or short "
        "verbatim text present in that file>\", \"note\": \"<one line: "
        "what was found>\"}` -- the citation is MECHANICALLY CHECKED: "
        "the cited file must exist under the workspace root and the "
        "locator text must be present in it, or the citation does not "
        "count as a resolution."
    )
    out.append(
        "Resolved via the spec arm (state introduced by THIS feature): "
        "`{\"status\": \"resolved\", \"arm\": \"spec\", \"citation\": "
        "\"<spec section or AC id declaring the new behavior>\", "
        "\"note\": \"<one line>\"}` -- no `locator` (`arm` is one of "
        + " | ".join(SUBJECT_RESOLUTION_ARMS)
        + ")."
    )
    out.append(
        "Unresolved: `{\"status\": \"unresolved\", \"searched\": "
        "\"<the terms, paths and bound reached -- concrete enough for "
        "a human to falsify the miss>\"}`."
    )
    out.append("")
    out.append(
        "Resolve every variable's subject BEFORE writing any "
        "constraint over it. An AC whose `subsection` above is `5.2 "
        "Behavior preservation` must resolve its subject via the code "
        "arm REGARDLESS of how the AC is worded -- the subsection is "
        "the primary trigger. Additionally, an AC under any OTHER "
        "subsection whose statement presupposes presently-existing "
        "behavior must ALSO resolve via the code arm -- wording is a "
        "secondary trigger, checked whether or not the subsection "
        "trigger fired. Either way, a preservation subject resolvable "
        "only via the spec arm is UNRESOLVED. An unresolved variable "
        "must not appear in ANY constraint -- the AC over it takes "
        "coverage status `unresolved_subject` instead."
    )
    out.append("")

    out.append("### constraints[]")
    out.append("")
    out.append(
        "Each element: `{\"ac_id\": \"<id>\", \"kind\": \""
        + "\" or \"".join(CONSTRAINT_KINDS)
        + "\", \"consequent\": [atom, ...], \"antecedent\": [atom, ...]}`."
    )
    out.append(
        "`assertion` is a plain `shall` invariant (no `antecedent`). "
        "`implication` is an EARS IF/WHEN rule -- `antecedent` is the "
        "trigger/condition, `consequent` is the required outcome; "
        "`antecedent` is REQUIRED and non-empty for `implication`."
    )
    out.append("")

    out.append("### atom shapes (flat -- no nesting, no multi-variable arithmetic)")
    out.append("")
    out.append(
        "- numeric: `{\"var\": str, \"op\": one of "
        + ", ".join('"{0}"'.format(op) for op in COMPARISON_OPS)
        + ", \"value\": <number>}`"
    )
    out.append(
        "- Bool: `{\"var\": str, \"negated\": <bool>}`"
    )
    out.append(
        "- Enum: `{\"var\": str, \"op\": \"=\" or \"!=\", \"value\": "
        "\"<member>\"}`"
    )
    out.append("")

    out.append("### coverage[]")
    out.append("")
    out.append(
        "Each element: `{\"ac_id\": \"<id>\", \"status\": one of "
        + " | ".join(COVERAGE_STATUSES)
        + ", \"reason\": str, \"subject\": str}`. `reason` is REQUIRED "
        "for either `skipped_*` status. `subject` is REQUIRED for "
        "`unresolved_subject` and names the unresolved variable; "
        "omit it for every other status. `reason` is optional for "
        "`unresolved_subject` (the failure "
        "detail lives in that variable's `subject_resolution.searched` "
        "instead). EVERY AC id above MUST appear exactly once in "
        "`coverage`. Use `skipped_prose` for a vague/non-logical AC (e.g. "
        "\"the app shall feel responsive\"); use `skipped_unsupported` for "
        "logic this IR cannot express (e.g. arithmetic over two or more "
        "variables); use `unresolved_subject` when the AC's subject "
        "could not be resolved (see variables[] above)."
    )
    out.append("")

    # -- Rules reminder --------------------------------------------------------
    out.append("## Rules")
    out.append("")
    out.append("- Atoms are flat only -- one variable, one op, one value.")
    out.append("- Exactly one coverage entry per AC, no more, no fewer.")
    out.append(
        "- If you cannot formalize an AC, record it in `coverage` as "
        "`skipped_prose` or `skipped_unsupported` rather than forcing a "
        "constraint that does not actually capture it."
    )

    return "\n".join(out) + "\n"
