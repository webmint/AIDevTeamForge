"""Phase 1 (investigation) command handlers.

Findings + runner-up framing + hypotheses + structured root cause +
confidence + verify-step setters.
"""

from __future__ import annotations

import argparse
import json

from ._constants import (
    CONFIDENCE_ENUM,
    CONFIDENCE_VS_PRIMARY_ENUM,
    FRAMING_ENUM,
)
from ._state import _load_report, _state_transaction
from ._validators import (
    _die,
    _validate_enum,
    _validate_file_line,
    _validate_rests_on_literal,
    _validate_scalar,
    _validate_verbatim,
)


def cmd_record_finding(args: argparse.Namespace) -> int:
    """Append a {surface, file_line, relevance, framing[, rests_on_literal]} Finding.

    rests_on_literal (plan 73 D4, sub-option b) is OPTIONAL here, unlike
    the other three fields -- record-finding has 74 subprocess call sites
    across four out-of-package test fixtures (the plan-69 D1/D5 frozen-
    signature precedent), so it cannot become a required argparse arg the
    way record-literal-archaeology's --use did. The field is instead
    FORCED AT VERIFY by check 20: every finding must answer it (a
    file:line or the explicit 'none'), and any file:line answer must
    match a recorded literal_archaeology row. When --rests-on-literal is
    omitted, the finding dict carries no rests_on_literal key at all
    (rather than a null placeholder) -- check 20 treats an absent key and
    an empty answer identically, and old findings recorded before this
    field existed look exactly like a finding that skipped it, which is
    the correct back-compat shape for report.json (ephemeral per-run
    state, not a durable cross-version artifact like handoff.json).

    This function is pure-append with no update path: calling it again
    for the same (surface, file_line) appends a SECOND finding rather
    than answering the first. To repair rests_on_literal on a finding
    already recorded -- this flag omitted, or a report.json upgraded
    mid-investigation whose findings predate this field entirely -- use
    the sibling setter classify_finding_literal / classify-finding-
    literal below, NOT a re-call of this function.
    """
    try:
        surface = _validate_scalar(args.surface, "finding.surface")
        file_line = _validate_file_line(args.file_line, "finding.file_line")
        relevance = _validate_scalar(args.relevance, "finding.relevance")
        framing = _validate_enum(
            getattr(args, "framing", "primary") or "primary",
            "finding.framing",
            FRAMING_ENUM,
        )
        rests_on_literal_raw = getattr(args, "rests_on_literal", None)
        rests_on_literal = None
        if rests_on_literal_raw is not None:
            rests_on_literal = _validate_rests_on_literal(
                rests_on_literal_raw, "finding.rests_on_literal"
            )
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            finding = {
                "surface": surface,
                "file_line": file_line,
                "relevance": relevance,
                "framing": framing,
            }
            if rests_on_literal is not None:
                finding["rests_on_literal"] = rests_on_literal
            report.setdefault("findings", []).append(finding)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-finding: {0}".format(err))
    return 0


def cmd_classify_finding_literal(args: argparse.Namespace) -> int:
    """Update rests_on_literal on an already-recorded Finding (plan 73 HIGH fix).

    Sibling setter to record-finding, mirroring classify-caller-scope's
    (plan 69 D5/WI-E) append-then-classify shape. record-finding is
    pure-append with no update path (see its docstring above) -- so a
    Finding recorded before this plan's --rests-on-literal flag existed,
    or recorded with the flag simply omitted, had no in-place repair
    route short of reset-report, which wipes ALL Phase 2/3 state
    (findings, hypotheses, approaches, recommended_approach, verdict).
    That was tolerable for an ordinary same-session omission but not for
    the case that made it urgent: a research-report.json upgraded
    mid-investigation (via update.sh, or a surgical .devforge/lib copy)
    whose EXISTING findings predate check 20 and can never satisfy it
    without destroying the investigation -- report.json deliberately
    survives compaction/resume/clear within one still-open invocation,
    and check 20 (plan 73 D2/D4) is mode-independent, so every such
    upgrade mid-run hits this.

    Identity key: (--surface, --file-line), matched EXACTLY against
    report.findings[]. This is not an arbitrary choice: it is the same
    pair check 20's own violation message names ("finding (surface=...,
    file_line=...) has not answered rests_on_literal"), so the LLM
    reading a check-20 failure calls this setter with the exact values
    verify already printed.

    record-finding has no dedup on (surface, file_line) -- like
    inbound_callers, two distinct Finding rows can legitimately share
    the pair (e.g. two record-finding calls describing the same site
    under different framings, or a plain re-recording).

    LIMITATION -- unlike classify-caller-scope, blanket-updating every
    matching row is NOT always safe here, and this setter refuses it by
    default when more than one row matches. classify-caller-scope's key
    (helper_qn, caller_qn) names one call EDGE -- duplicate rows on that
    key almost always share one true classification, so its
    unconditional every-match update is correct. (surface, file_line)
    carries no such invariant: surface and relevance are free text
    describing an OBSERVATION, not an edge identity, so two rows can
    legitimately share the pair while resting on DIFFERENT literals
    (e.g. two record-finding calls both surfaced "flag check" @
    src/admin/Flag.vue:12 -- one grounded by a literal at src/x.ts:5,
    the other, on a later pass, by an unrelated literal at src/y.ts:9).
    Blanket-updating every match on a divergent duplicate FABRICATES an
    answer for whichever row did not actually supply it -- the same
    silent-manufactured-value failure this plan exists to catch,
    reproduced inside its own repair setter instead of caught by it.
    So: with more than one matching row, this call REJECTS (code 2) by
    default, printing each matching row's relevance + current
    rests_on_literal (surface and file_line are, by definition,
    identical across them, so they cannot disambiguate the rows).
    Recovery is one of: (a) re-word one finding's --surface so future
    record-finding calls for that observation key uniquely, keeping the
    pair from colliding again; or (b) pass --all to confirm the SAME
    answer genuinely applies to every matching row and perform the
    update across all of them -- this plan's ORIGINAL every-match
    behaviour, now opt-in and explicit rather than the unconditional
    default. A single matching row always updates without --all; that
    path is unambiguous and untouched by this guard.

    Rejects (code 2) when no report.findings[] row matches the given
    (surface, file_line) pair -- mirrors classify-caller-scope's
    pre-transaction existence check, so this setter cannot silently
    manufacture an answer for a Finding that was never recorded.
    --rests-on-literal is validated through the same
    _validate_rests_on_literal record-finding itself uses, so a
    malformed value or the wrong none-sentinel is rejected identically
    at either call site -- no new path lets a Finding acquire an
    unvalidated answer.

    Idempotent: re-calling with the same arguments (including --all,
    when more than one row matches) re-applies the same value to the
    same row(s); report.findings length never changes.

    Does NOT eagerly cross-check the file:line answer against
    literal_archaeology -- like record-finding's own --rests-on-literal,
    that cross-check is check 20's job at verify time, not this
    setter's (plan 73 D4: optional-at-record / mandatory-at-verify).
    """
    try:
        surface = _validate_scalar(args.surface, "classify_finding_literal.surface")
        file_line = _validate_file_line(args.file_line, "classify_finding_literal.file_line")
        rests_on_literal = _validate_rests_on_literal(
            args.rests_on_literal, "classify_finding_literal.rests_on_literal"
        )
    except ValueError as err:
        return _die(str(err), code=2)

    # Pre-transaction existence check (mirrors classify-caller-scope /
    # record-data-flow-chain / set-value-semantics — validation runs
    # against a snapshot BEFORE entering the transaction so the state
    # file is never rewritten on a rejection). Safe to check against a
    # pre-lock snapshot with respect to a CONCURRENT record-finding:
    # EXISTENCE is monotonic across the snapshot-then-lock window
    # against that setter specifically, because record-finding only
    # ever appends, so "at least one match" can only become MORE true
    # between the snapshot and the lock, never less. NOT safe with
    # respect to a concurrent reset-report (_cmds_basic.py), which
    # bypasses _state_transaction (and so the fcntl lock) entirely via
    # a direct _atomic_write_json(default_report_state(), ...) wholesale
    # replace, zeroing findings to [] out from under this check -- a
    # pre-existing unlocked design property of reset-report, orthogonal
    # to this fix, and a known theoretical gap under this repo's
    # single-session serial-invocation actor model. (The MULTI-MATCH
    # count check below has no monotonicity guarantee even against
    # record-finding and is re-derived inside the lock instead — see
    # its comment.)
    try:
        report_snapshot = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("classify-finding-literal: {0}".format(err))
    findings_snapshot = report_snapshot.get("findings") or []
    if not any(
        f.get("surface") == surface and f.get("file_line") == file_line
        for f in findings_snapshot
    ):
        known_pairs = sorted({
            "({0}, {1})".format(f.get("surface"), f.get("file_line"))
            for f in findings_snapshot
        })
        return _die(
            "classify-finding-literal: no recorded findings row for "
            "(surface={0!r}, file_line={1!r}); call record-finding first. "
            "Recorded (surface, file_line) pairs: {2!r}".format(
                surface, file_line, known_pairs
            ),
            code=2,
        )

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            # (surface, file_line) is NOT a unique key -- two distinct
            # findings can legitimately share it while resting on
            # DIFFERENT literals (see the docstring LIMITATION above).
            # Re-derive the match count from THIS freshly-locked
            # `report`, NOT the pre-lock snapshot above: unlike the
            # existence check above, a COUNT threshold is not
            # monotonic-safe across the snapshot-then-lock window -- a
            # concurrent record-finding call appending a second row
            # between the snapshot and the lock would flip the count
            # from safe (1) to unsafe (>1), and checking the stale
            # snapshot would let the update below apply one answer to
            # both now-current rows: the exact fabrication this guard
            # exists to close. Mirrors cmd_record_contributing_factor's
            # `len(factors) >= 3` check, which re-derives its count
            # inside the lock for the identical reason. Checked BEFORE
            # any mutation below -- an early return here still runs
            # _state_transaction's post-yield write, but it re-persists
            # `report` UNCHANGED (no mutation happened yet), so it is
            # safe.
            current_matches = [
                f for f in report.get("findings") or []
                if f.get("surface") == surface and f.get("file_line") == file_line
            ]
            if len(current_matches) > 1 and not args.all:
                rows_desc = "; ".join(
                    "row {0}: relevance={1!r}, current rests_on_literal={2!r}".format(
                        idx + 1,
                        f.get("relevance"),
                        f.get("rests_on_literal", "(unanswered)"),
                    )
                    for idx, f in enumerate(current_matches)
                )
                return _die(
                    "classify-finding-literal: {0} finding rows share "
                    "(surface={1!r}, file_line={2!r}); refusing to guess "
                    "whether they share one true rests_on_literal answer "
                    "-- surface and file_line are identical across them "
                    "by definition, so the key alone cannot tell them "
                    "apart. Matching rows: {3}. Recover by either (a) "
                    "re-wording one finding's --surface so future "
                    "record-finding calls for that observation key "
                    "uniquely, disambiguating the pair; or (b) "
                    "re-running this exact call with --all if the SAME "
                    "rests_on_literal answer genuinely applies to every "
                    "matching row.".format(
                        len(current_matches), surface, file_line, rows_desc
                    ),
                    code=2,
                )
            # No `break` -- update EVERY matching row, not just the
            # first. Reached only when exactly one row matched the key,
            # or --all confirmed the blanket update is intentional (see
            # docstring LIMITATION). record-finding is append-only with
            # no dedup on (surface, file_line), so a duplicate pair's
            # second row would otherwise stay permanently unrepairable
            # short of reset-report. Idempotent: an unmatched pair is
            # already rejected by the existence check above.
            for f in current_matches:
                f["rests_on_literal"] = rests_on_literal
    except (OSError, json.JSONDecodeError) as err:
        return _die("classify-finding-literal: {0}".format(err))
    return 0


def cmd_record_runner_up_framing(args: argparse.Namespace) -> int:
    """Set report.runner_up_framing. Overwrites any prior value (last call wins)."""
    try:
        frame = _validate_scalar(args.frame, "runner_up_framing.frame")
        falsifier = _validate_scalar(args.falsifier, "runner_up_framing.falsifier")
        confidence = _validate_enum(
            args.confidence_vs_primary,
            "runner_up_framing.confidence_vs_primary",
            CONFIDENCE_VS_PRIMARY_ENUM,
        )
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["runner_up_framing"] = {
                "frame": frame,
                "falsifier": falsifier,
                "confidence_vs_primary": confidence,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-runner-up-framing: {0}".format(err))
    return 0


def _hypothesis_label(index):
    # type: (int) -> str
    """Convert a zero-based hypothesis index to an uppercase letter label.

    Index 0 → "A", 1 → "B", ..., 25 → "Z", 26 → "AA", 27 → "AB", etc.
    Follows spreadsheet-column naming for indices beyond 25 (unlikely in
    practice but avoids a silent failure on long hypothesis lists).
    """
    label = ""
    n = index
    while True:
        label = chr(ord("A") + (n % 26)) + label
        n = n // 26 - 1
        if n < 0:
            break
    return label


def cmd_record_hypothesis(args: argparse.Namespace) -> int:
    """Append a {label, cause, falsifier, runtime_probe_needed} Hypothesis.

    label is auto-assigned in record order: first hypothesis → "A",
    second → "B", etc. The label is what recommended_approach.hypotheses_addressed
    references so the verify-hypothesis-suppression exemption can match by
    label rather than by cause text (which would couple the setter and the
    verify check to a fragile string-equality comparison).
    """
    try:
        cause = _validate_scalar(args.cause, "hypothesis.cause")
        falsifier = _validate_scalar(args.falsifier, "hypothesis.falsifier")
    except ValueError as err:
        return _die(str(err), code=2)
    runtime = args.runtime_probe_needed == "yes"
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            existing = report.setdefault("hypotheses", [])
            label = _hypothesis_label(len(existing))
            existing.append(
                {
                    "label": label,
                    "cause": cause,
                    "falsifier": falsifier,
                    "runtime_probe_needed": runtime,
                }
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-hypothesis: {0}".format(err))
    return 0


def cmd_set_root_cause_hypothesis(args: argparse.Namespace) -> int:
    """Set root_cause_hypothesis free text."""
    try:
        value = _validate_verbatim(args.value, "root_cause_hypothesis")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["root_cause_hypothesis"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-root-cause-hypothesis: {0}".format(err))
    return 0


def cmd_set_confidence(args: argparse.Namespace) -> int:
    """Set confidence enum."""
    try:
        value = _validate_enum(args.value, "confidence", CONFIDENCE_ENUM)
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["confidence"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-confidence: {0}".format(err))
    return 0


def _ensure_structured_root_cause(report: dict) -> dict:
    """Lazily create the structured_root_cause record on the report."""
    rec = report.get("structured_root_cause")
    if rec is None:
        rec = {"trigger": None, "root_cause_systemic": None, "contributing_factors": []}
        report["structured_root_cause"] = rec
    return rec


def cmd_set_trigger(args: argparse.Namespace) -> int:
    """Set structured_root_cause.trigger (caller is responsible for mode gate)."""
    try:
        value = _validate_verbatim(args.value, "trigger")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rec = _ensure_structured_root_cause(report)
            rec["trigger"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-trigger: {0}".format(err))
    return 0


def cmd_set_root_cause_systemic(args: argparse.Namespace) -> int:
    """Set structured_root_cause.root_cause_systemic."""
    try:
        value = _validate_verbatim(args.value, "root_cause_systemic")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rec = _ensure_structured_root_cause(report)
            rec["root_cause_systemic"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-root-cause-systemic: {0}".format(err))
    return 0


def cmd_record_contributing_factor(args: argparse.Namespace) -> int:
    """Append a contributing factor (max 3)."""
    try:
        value = _validate_scalar(args.value, "contributing_factor")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rec = _ensure_structured_root_cause(report)
            factors = rec.setdefault("contributing_factors", [])
            if len(factors) >= 3:
                return _die(
                    "record-contributing-factor: max 3 entries; already have {0}".format(
                        len(factors)
                    ),
                    code=2,
                )
            factors.append(value)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-contributing-factor: {0}".format(err))
    return 0


def cmd_set_verify_step(args: argparse.Namespace) -> int:
    """Set verify_step record. 3 sub-fields all required."""
    try:
        probe = _validate_verbatim(args.probe, "verify_step.probe")
        reproduction = _validate_verbatim(args.reproduction, "verify_step.reproduction")
        discriminator = _validate_verbatim(args.discriminator, "verify_step.discriminator")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["verify_step"] = {
                "probe": probe,
                "reproduction": reproduction,
                "discriminator": discriminator,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-verify-step: {0}".format(err))
    return 0
