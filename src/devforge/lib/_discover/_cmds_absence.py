"""Absence-claim provenance lane (plan 73 D6 / Phase 4).

`/discover` is a greenfield survey: its load-bearing negative claim is
"nothing exists for this -> build new", not a hardcoded literal (that is
the `/research` lane plan 73's GAP 2 targets -- see
`_research/_cmds_dataflow.py::cmd_record_literal_archaeology`). An absence
is exactly the claim git history can refute: the thing may not exist
because it was DELIBERATELY DELETED, and a survey that never checks will
confidently recommend rebuilding what someone removed on purpose.

record-absence-probe records the outcome of running `git log -S
"<symbol>"` and/or `git log --diff-filter=D -- <path>` against one
absence claim (the model runs the query; this setter only records what it
found -- same division as record-literal-archaeology, which the shape of
this command's arguments mirrors). requires_absence_probe() names the
trigger condition consumed by cmd_finalize_handoff's declaration-exists
guard (_cmds_handoff.py): it fires when report.build_vs_buy.recommendation
== "Build" AND the report records zero internal prior-art hits
(report.prior_art has no source="internal:<path>" entry) -- the same
"nothing exists internally" signal Step 2.0's own cite-back rule
(cmd_verify's Rule G, _cmds_core.py) already keys on. A "Build"
recommendation grounded in >=1 internal hit is not a bare absence claim --
Rule G already forces that case to reason about the existing code -- so it
is excluded from the trigger.

The guard this predicate feeds checks only that the probe HAPPENED
(report.absence_probes is non-empty); it never inspects what any probe
FOUND. A "found nothing" outcome is recorded as a first-class value
(--found false), not as an absent record -- the same None-vs-False
distinction plan 73 Phase 3's EvidenceLanes work made for the research
lane, applied here to a per-claim row instead of a per-run declaration.
"""

from __future__ import annotations

import argparse
import json
import re

from ._state import _state_transaction
from ._validators import _die, _validate_scalar

_COMMIT_SHA_RE = re.compile(r"[0-9a-fA-F]{7,40}")

_NONE_SENTINEL = "none"


def cmd_record_absence_probe(args: argparse.Namespace) -> int:
    """Append one absence-probe row to report.absence_probes.

    --symbol / --path: the search string passed to `git log -S` / the path
    passed to `git log --diff-filter=D --`, respectively. Either may be
    the literal "none" when this probe ran only the other query; both
    cannot be "none" (a probe recording neither query's target records
    nothing meaningful).

    --found: whether either query surfaced a prior deletion. "false" is a
    first-class, equally valid outcome to "true" -- "genuinely never
    existed" settles the absence claim exactly as informatively as "was
    deleted on <date>"; only their downstream implication differs (see
    module docstring).

    --deleted-commit-sha / --deleted-commit-subject are REQUIRED when
    --found true and FORBIDDEN when --found false -- bidirectional
    mutual exclusivity, matching the codebase's existing
    match-flag-implies-required-detail pairing (e.g.
    append-outcome's --internal-extension-followed / --delta-from-
    recommendation): a "false" row must not carry stray commit info a
    caller forgot to omit, and a "true" row must not omit the evidence
    that makes it a "true" row.

    Pure append, no dedup: unlike record-literal-archaeology's
    (literal, file_line) dedup -- which exists because a downstream check
    there (research check 17) demands per-row semantic content the
    setter must protect from silent overwrite -- nothing downstream reads
    absence_probes for per-row correctness, only for presence (see
    requires_absence_probe below). Two rows recording the same claim are
    harmless, so no dedup key is needed.
    """
    try:
        claim = _validate_scalar(args.claim, "record-absence-probe.claim")
        symbol = _validate_scalar(args.symbol, "record-absence-probe.symbol")
        path = _validate_scalar(args.path, "record-absence-probe.path")
    except ValueError as err:
        return _die(str(err), code=2)

    # Case-insensitive "none" sentinel, canonicalized to lowercase before
    # storage -- matches the research-side precedent
    # (_research/_validators.py::_validate_rests_on_literal, comparing via
    # RESTS_ON_LITERAL_NONE). Without this, "--symbol None" would compare
    # unequal to the lowercase sentinel below, the "cannot both be none"
    # guard would never fire for a capitalized pair, and the stored row
    # would carry "None" verbatim -- reading as though it named a real
    # git target when it was meant to signal "no target for this query".
    if symbol.lower() == _NONE_SENTINEL:
        symbol = _NONE_SENTINEL
    if path.lower() == _NONE_SENTINEL:
        path = _NONE_SENTINEL

    if symbol == _NONE_SENTINEL and path == _NONE_SENTINEL:
        return _die(
            "record-absence-probe: --symbol and --path cannot both be "
            "'none' -- at least one git query must have named a real "
            "target",
            code=2,
        )

    found = args.found == "true"
    sha_raw = getattr(args, "deleted_commit_sha", None)
    subject_raw = getattr(args, "deleted_commit_subject", None)

    if found:
        if not sha_raw or not sha_raw.strip():
            return _die(
                "record-absence-probe: --deleted-commit-sha is required "
                "when --found true",
                code=2,
            )
        sha = sha_raw.strip()
        if not _COMMIT_SHA_RE.fullmatch(sha):
            return _die(
                "record-absence-probe: --deleted-commit-sha {0!r} must be "
                "a 7-40 char hex commit SHA".format(sha_raw),
                code=2,
            )
        try:
            subject = _validate_scalar(
                subject_raw or "", "record-absence-probe.deleted_commit_subject"
            )
        except ValueError as err:
            return _die(
                "record-absence-probe: --deleted-commit-subject is "
                "required when --found true ({0})".format(err),
                code=2,
            )
    else:
        if sha_raw is not None and sha_raw.strip():
            return _die(
                "record-absence-probe: --deleted-commit-sha must be "
                "omitted when --found false",
                code=2,
            )
        if subject_raw is not None and subject_raw.strip():
            return _die(
                "record-absence-probe: --deleted-commit-subject must be "
                "omitted when --found false",
                code=2,
            )
        sha = None
        subject = None

    entry = {
        "claim": claim,
        "symbol": symbol,
        "path": path,
        "found": found,
        "deleted_commit_sha": sha,
        "deleted_commit_subject": subject,
    }
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("absence_probes", []).append(entry)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-absence-probe: {0}".format(err))
    return 0


def _has_internal_prior_art(report: dict) -> bool:
    """Return True when report.prior_art carries >=1 'internal:<path>' hit.

    Same substring test as cmd_verify's Rule G (_cmds_core.py) -- kept as
    an independent boolean-only helper rather than a shared import, since
    Rule G needs the actual path list (to cite in its violation message)
    and this predicate needs only presence.
    """
    for entry in report.get("prior_art") or []:
        if not isinstance(entry, dict):
            continue
        source = entry.get("source") or ""
        if (
            isinstance(source, str)
            and source.startswith("internal:")
            and source[len("internal:"):].strip()
        ):
            return True
    return False


def requires_absence_probe(report: dict) -> bool:
    """Return True when this report records an absence-founded Build conclusion.

    Plan 73 D6's trigger: report.build_vs_buy.recommendation == "Build"
    AND zero internal prior-art hits recorded. Together those assert
    "nothing exists internally for this -> build new" -- the exact
    greenfield absence claim git history can refute (a deliberate prior
    deletion) or corroborate (a real, verifiable absence). Consulted only
    by cmd_finalize_handoff's declaration-exists guard, which checks
    whether report.absence_probes is non-empty -- it never inspects this
    function's caller's build_vs_buy/prior_art values again, and this
    function never inspects absence_probes.
    """
    bvb = report.get("build_vs_buy")
    if not isinstance(bvb, dict):
        return False
    if bvb.get("recommendation") != "Build":
        return False
    return not _has_internal_prior_art(report)
