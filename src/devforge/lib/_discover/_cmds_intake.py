"""Step 5 — intake-interrogation gate command handlers for discover_helper.

Three verbs:
  record-intake-classification  — setter: persists per-statement binary
                                   classification (requirement vs hypothesis)
                                   + the orchestrator-composed minimal_fix.
  render-intake-echo             — render verb: emits the echo-back block
                                   (requirements / scope-expanders-to-verify /
                                   minimal scope) to stdout verbatim for the
                                   orchestrator to copy to the user.
  record-intake-confirmation     — setter (plan 98 D4a): persists whether the
                                   user confirmed the echo-back block or the
                                   run proceeded on an unconfirmed reading
                                   (a non-pick, e.g. a delegated reply). The
                                   confirmation is never inferred -- the
                                   orchestrator calls this once per intake
                                   echo with the actual outcome.

DISCOVER LANE DIVERGENCE — do NOT mirror /research here:
  - A "hypothesis" in discover is a scope-expander or placement guess, not a
    suspected bug cause. The orchestrator routes it to record-gap
    --dimension integration_points, NOT to a record-hypothesis call (which
    does not exist in discover_helper).
  - The echo-back block uses "scope-expander / placement guess" wording, not
    "suspected cause" wording.
  - This divergence is documented in plan Step 5 (lines 259+) and must be
    preserved. Adding a record-hypothesis verb to discover_helper is a
    VIOLATION of that plan decision.

Helper-owns-shape: orchestrator supplies classification values; this module
owns echo-block structure and storage layout.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from ._state import _load_memo, _state_transaction
from ._validators import _die, _validate_scalar


# ---------------------------------------------------------------------------
# Enum — single source of truth for the binary classification kind.
# ---------------------------------------------------------------------------

INTAKE_KIND_ENUM = ("requirement", "hypothesis")

# Enum — single source of truth for the intake-confirmation state (plan 98
# D4a). "confirmed" is set only when the user actually picked confirm at
# the echo-back re-ask; "unconfirmed" covers every other outcome (a
# non-pick, a delegated reply, or the re-ask exhausted without a pick) --
# the model's reading proceeds, but it is never cited as "you confirmed".
INTAKE_CONFIRMATION_STATE_ENUM = ("confirmed", "unconfirmed")


# ---------------------------------------------------------------------------
# Setter handler.
# ---------------------------------------------------------------------------


def cmd_record_intake_classification(args: argparse.Namespace) -> int:
    """Append (or replace) a per-statement intake classification in memo.

    Persists {statement, kind, minimal_fix} into memo.intake_classifications.
    If an entry with the same statement already exists it is overwritten
    (idempotent re-recording on correction).

    --kind must be one of: requirement | hypothesis.
    --minimal-fix is optional. For discover, a "hypothesis" entry's minimal_fix
    is typically the minimal scope (without the speculative addition) rather
    than a code-change.

    Discover lane: a "hypothesis" kind is a scope-expander or placement guess.
    The orchestrator separately routes it to record-gap --dimension
    integration_points. This setter does NOT route it automatically.
    """
    try:
        statement = _validate_scalar(args.statement, "record-intake-classification.statement")
    except ValueError as err:
        return _die(str(err), code=2)

    kind = args.kind
    if kind not in INTAKE_KIND_ENUM:
        return _die(
            "record-intake-classification: --kind {0!r} is not valid; "
            "allowed: {1}".format(kind, list(INTAKE_KIND_ENUM)),
            code=2,
        )

    minimal_fix = None
    if args.minimal_fix is not None:
        try:
            minimal_fix = _validate_scalar(args.minimal_fix, "record-intake-classification.minimal_fix")
        except ValueError as err:
            return _die(str(err), code=2)

    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            classifications = memo.setdefault("intake_classifications", [])
            # Idempotent: replace existing entry with the same statement.
            for entry in classifications:
                if isinstance(entry, dict) and entry.get("statement") == statement:
                    entry["kind"] = kind
                    entry["minimal_fix"] = minimal_fix
                    break
            else:
                classifications.append({
                    "statement": statement,
                    "kind": kind,
                    "minimal_fix": minimal_fix,
                })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-intake-classification: {0}".format(err))
    return 0


def cmd_record_intake_confirmation(args: argparse.Namespace) -> int:
    """Persist the outcome of the intake-echo confirmation ask (plan 98 D4a).

    Persists {state, reply} into memo.intake_confirmation, overwriting any
    prior call (idempotent re-recording -- e.g. a re-ask that later gets an
    explicit pick replaces the earlier "unconfirmed" record).

    --state must be one of: confirmed | unconfirmed.
    --reply is the verbatim (or paraphrased) user reply that produced this
    state and is REQUIRED even for --state confirmed -- render() quotes it
    only on the unconfirmed path, but the field is never optional here so a
    caller cannot silently skip recording what was actually said.

    This is the ONE persisted record of whether the user confirmed the
    echoed intake reading. An "unconfirmed" record is the model's own
    reading proceeding after a non-pick (e.g. a delegated reply); it is
    never rendered or cited as the user's confirmation.
    """
    try:
        reply = _validate_scalar(args.reply, "record-intake-confirmation.reply")
    except ValueError as err:
        return _die(str(err), code=2)

    state = args.state
    if state not in INTAKE_CONFIRMATION_STATE_ENUM:
        return _die(
            "record-intake-confirmation: --state {0!r} is not valid; "
            "allowed: {1}".format(state, list(INTAKE_CONFIRMATION_STATE_ENUM)),
            code=2,
        )

    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo["intake_confirmation"] = {"state": state, "reply": reply}
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-intake-confirmation: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Render handler.
# ---------------------------------------------------------------------------


def cmd_render_intake_echo(args: argparse.Namespace) -> int:
    """Render the discover intake echo-back block to stdout (verbatim copy to user).

    Block structure:
      ## Intake interpretation

      ### Requirements (as I read your prompt)
      - <statement>
        Minimal scope: <minimal_fix>

      ### Scope-expanders to verify — NOT requirements
      These are speculative additions or placement guesses. They route to
      the scoping rubric for verification, not to implementation direction.
      - <statement>

      ### Minimal scope
      The simplest scope that satisfies the stated feature intent alone:
      <minimal_fix from the first requirement entry, else "(not set)">

    Proportionality: when there are no hypothesis/scope-expander entries
    the scope-expanders section is omitted entirely. When there are no
    requirements, the Requirements header and "*(no requirements
    classified)*" placeholder are suppressed — only the scope-expanders
    section is shown. The Minimal scope section is omitted entirely when
    there are no requirements.
    When intake_classifications is empty, emits a notice.

    Discover divergence: "scope-expander / placement guess" wording replaces
    the research "suspected cause / hypothesis" wording. Verify-route is
    record-gap --dimension integration_points, not record-hypothesis.
    """
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-intake-echo: {0}".format(err))

    classifications = memo.get("intake_classifications") or []

    if not classifications:
        sys.stdout.write(
            "<!-- intake-echo: no classifications recorded -->\n"
        )
        return 0

    requirements = [e for e in classifications if e.get("kind") == "requirement"]
    scope_expanders = [e for e in classifications if e.get("kind") == "hypothesis"]

    lines = []  # type: List[str]
    lines.append("## Intake interpretation")
    lines.append("")

    # Requirements section — rendered only when non-empty (F2: suppress header
    # and placeholder when only scope-expanders are recorded).
    if requirements:
        lines.append("### Requirements (as I read your prompt)")
        lines.append("")
        for entry in requirements:
            lines.append("- {0}".format(entry.get("statement", "")))
            mf = entry.get("minimal_fix")
            if mf:
                lines.append("  Minimal scope: {0}".format(mf))
        lines.append("")

    # Scope-expanders section — OMITTED when empty (proportionality rule).
    if scope_expanders:
        lines.append("### Scope-expanders to verify — NOT requirements")
        lines.append("")
        lines.append(
            "These are speculative additions or placement guesses. They route "
            "to the scoping rubric for verification (record-gap "
            "--dimension integration_points), not to implementation direction."
        )
        lines.append("")
        for entry in scope_expanders:
            lines.append("- {0}".format(entry.get("statement", "")))
        lines.append("")

    # Minimal scope — omitted entirely when there are no requirements (F2:
    # no noise on a hypothesis-only prompt). When present, derives from the
    # first requirement's minimal_fix, or "(not set)" when absent.
    if requirements:
        minimal_fix_for_scope = None
        for entry in requirements:
            mf = entry.get("minimal_fix")
            if mf:
                minimal_fix_for_scope = mf
                break

        lines.append("### Minimal scope")
        lines.append("")
        lines.append(
            "The simplest scope that satisfies the stated feature intent alone:"
        )
        lines.append("")
        lines.append(minimal_fix_for_scope or "(not set)")
        lines.append("")

    sys.stdout.write("\n".join(lines) + "\n")
    return 0
