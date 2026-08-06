"""Phase 4 setter cmd_* handlers: header / branch / sections / AC / constraints."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._schema import (
    AC_SUBSECTION_ENUM,
    AC_UBIQUITOUS_ONLY_SUBSECTIONS,
    CONSTRAINT_KIND_ENUM,
    DESIGN_SOURCE_DEFAULT,
    DESIGN_SOURCE_SCHEME_ENUM,
    EARS_REGEX,
    EARS_VARIANT_ENUM,
    FEATURE_NAME_RE,
    IMPACT_ENUM,
    LANDED_IN_ENUM,
    LIKELIHOOD_ENUM,
    SPEC_NUMBER_WIDTH,
)
from ._state import _load_state, _state_transaction
from ._validators import (
    _die,
    _validate_constitution_anchor_ref,
    _validate_enum,
    _validate_external_system,
    _validate_nfr_quantifier,
    _validate_scalar,
)
from _shared.feature_alloc import (  # type: ignore[import]
    decide_branch_action,
    next_spec_number,
)


def _parse_finding_refs(raw: Optional[List[str]]) -> List[str]:
    """Normalise the --finding-ref list: strip whitespace, drop empties."""
    if not raw:
        return []
    return [r.strip() for r in raw if r.strip()]


def _validate_finding_refs(
    state: Dict[str, Any], finding_ids: List[str],
) -> Optional[str]:
    """Return an error string if any id is not found; None on success."""
    known = {f.get("finding_id") for f in state.get("findings", [])}
    unknown = [fid for fid in finding_ids if fid not in known]
    if unknown:
        return "unknown finding id(s): {0}".format(", ".join(unknown))
    return None


def _flip_findings(
    state: Dict[str, Any],
    finding_ids: List[str],
    bucket: str,
    landed_ref: str,
) -> None:
    """Flip landed_in / landed_ref on each named finding in state.

    Pre-condition: all ids are known (caller validated with
    _validate_finding_refs before entering the transaction).
    Re-landing a finding to the same bucket is a no-op. Re-landing to a
    different bucket succeeds (the new bucket + ref overwrite the old).
    """
    for finding in state.get("findings", []):
        if finding.get("finding_id") in finding_ids:
            finding["landed_in"] = bucket
            finding["landed_ref"] = landed_ref


def cmd_assign_spec_number(args: argparse.Namespace) -> int:
    """Scan specs/ for highest NNN-* dir, persist + emit next zero-padded.

    68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4 python-reviewer finding 4:
    delegates the scan to _shared.feature_alloc.next_spec_number(devforge_dir)
    -- the SAME single-source-of-truth scan research_helper / discover_helper
    / this module's allocate_feature_dir already use -- instead of the
    formerly-duplicated local _existing_spec_numbers scan.

    --specs-root is now ACCEPTED-BUT-IGNORED: next_spec_number always scans
    repo_root/specs where repo_root = the parent of --devforge-dir, which
    is the value every existing caller already passes (src/commands/
    specify/main.md's `assign-spec-number --specs-root specs`, and every
    test in this repo) -- so no caller's observable behavior changes.
    Kept only so a caller still passing --specs-root does not break.

    With this verb's fresh-scan reachable only via the D5 fallback guard
    (import-handoff now seeds spec_number/feature_slug directly from the
    resolved intake dir on the normal path -- see _cmds_handoff.py), this
    scan runs only for a genuine cold/no-intake spec.
    """
    nxt = next_spec_number(args.devforge_dir)
    formatted = "{0:0{w}d}".format(nxt, w=SPEC_NUMBER_WIDTH)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["spec_number"] = formatted
    except (OSError, json.JSONDecodeError) as err:
        return _die("assign-spec-number: {0}".format(err))
    sys.stdout.write(formatted + "\n")
    return 0


_SPEC_NUMBER_VALUE_RE = re.compile(r"^\d{3,}$")


def cmd_set_spec_number(args: argparse.Namespace) -> int:
    """Explicit-value spec_number setter -- mirrors assign-feature-name's
    explicit-value contract (validate + persist verbatim, no scan).

    68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4 python-reviewer finding 1(b):
    covers the D5 COLD-path case -- /specify resolves an existing pending
    intake feature dir (find-handoffs), the user picks "cold" (import
    skipped), so import-handoff's directory-derived spec_number/
    feature_slug seeding never ran, yet /specify still writes spec.md into
    that resolved dir. The caller (main.md) already knows the resolved
    dir's NNN (it just parsed it to find the dir) and passes it straight
    through -- unlike assign-spec-number, this verb performs NO scan.

    --value must be 3+ digits (zero-padding OK, e.g. "001", "042", "1234").
    """
    try:
        value = _validate_scalar(args.value, "value")
    except ValueError as err:
        return _die(str(err), code=2)
    if not _SPEC_NUMBER_VALUE_RE.match(value):
        return _die(
            "set-spec-number: {0!r} is not a valid spec number (expected"
            " 3+ digits, zero-padding OK, e.g. '001', '042',"
            " '1234')".format(value),
            code=2,
        )
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["spec_number"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-spec-number: {0}".format(err))
    return 0


def cmd_assign_feature_name(args: argparse.Namespace) -> int:
    """Validate 2-4 word kebab-case + persist feature_name + feature_slug."""
    try:
        name = _validate_scalar(args.feature_name, "feature_name")
    except ValueError as err:
        return _die(str(err), code=2)
    if not FEATURE_NAME_RE.match(name):
        return _die(
            "assign-feature-name: {0!r} not 2-4 word kebab-case "
            "(pattern: lower-case alnum segments joined by '-', "
            "first char a letter, 2-4 segments).".format(name),
            code=2,
        )
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["feature_name"] = name
            state["feature_slug"] = name
    except (OSError, json.JSONDecodeError) as err:
        return _die("assign-feature-name: {0}".format(err))
    return 0


def cmd_set_date(args: argparse.Namespace) -> int:
    """Set the spec header Date (YYYY-MM-DD). Required for deterministic render."""
    try:
        date = _validate_scalar(args.date, "date")
    except ValueError as err:
        return _die(str(err), code=2)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return _die(
            "set-date: expected YYYY-MM-DD, got {0!r}".format(date),
            code=2,
        )
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["date"] = date
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-date: {0}".format(err))
    return 0


def cmd_create_branch(args: argparse.Namespace) -> int:
    """Decide branch creation based on current vs default.

    Delegates the actual decision to the shared _shared/feature_alloc.py
    decide_branch_action (plan 68 Phase 1) -- this handler's job is only
    state I/O + preserving the exact historical stdout/state contract:
    both of decide_branch_action's "keep-spec" and "keep-other" arms map
    to state["branch_decision"] = "keep" here (this call site is only ever
    reached via /specify's Phase 0.2 default-branch-or-other-non-default
    path -- see decide_branch_action's docstring for why the two "keep"
    arms render identical text either way).
    """
    current = (args.current_branch or "").strip()
    default = (args.default_branch or "").strip()
    if not current or not default:
        return _die(
            "create-branch: --current-branch and --default-branch required",
            code=2,
        )
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["current_branch"] = current
            state["default_branch"] = default
            number = state.get("spec_number")
            slug = state.get("feature_slug")
            decision, line, error = decide_branch_action(
                current, default, number, slug,
            )
            if decision == "create" and error is not None:
                return _die(
                    "create-branch: spec_number + feature_slug required "
                    "before checkout (run assign-spec-number + "
                    "assign-feature-name first)",
                    code=2,
                )
            if decision == "create":
                state["branch_decision"] = "create"
                state["branch_created"] = True
            else:
                state["branch_decision"] = "keep"
                state["branch_created"] = False
            sys.stdout.write(line + "\n")
    except (OSError, json.JSONDecodeError) as err:
        return _die("create-branch: {0}".format(err))
    return 0


def _set_string_field(
    args: argparse.Namespace, helper_name: str, field_name: str,
) -> int:
    try:
        content = _validate_scalar(args.content, "content")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state[field_name] = content
    except (OSError, json.JSONDecodeError) as err:
        return _die("{0}: {1}".format(helper_name, err))
    return 0


def cmd_set_overview(args: argparse.Namespace) -> int:
    return _set_string_field(args, "set-overview", "overview")


def cmd_set_current_state(args: argparse.Namespace) -> int:
    return _set_string_field(args, "set-current-state", "current_state")


def cmd_set_desired_behavior(args: argparse.Namespace) -> int:
    return _set_string_field(args, "set-desired-behavior", "desired_behavior")


def cmd_record_affected_area(args: argparse.Namespace) -> int:
    """Append a §4 Affected Areas row {area, files, impact}."""
    try:
        area = _validate_scalar(args.area, "area")
        impact = _validate_scalar(args.impact, "impact")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        files = json.loads(args.files or "[]")
    except json.JSONDecodeError as err:
        return _die(
            "files: not valid JSON ({0})".format(err), code=2,
        )
    if not isinstance(files, list) or not all(
        isinstance(f, str) for f in files
    ):
        return _die(
            "files: must be a JSON array of strings", code=2,
        )
    cleaned_files = [f.strip() for f in files if f.strip()]
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["affected_areas"].append({
                "area": area,
                "files": cleaned_files,
                "impact": impact,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-affected-area: {0}".format(err))
    return 0


def cmd_record_out_of_scope(args: argparse.Namespace) -> int:
    """Append a §6 OOS entry {content, finding_ref} and flip finding landed_in."""
    try:
        content = _validate_scalar(args.content, "content")
    except ValueError as err:
        return _die(str(err), code=2)
    finding_ref = (args.finding_ref or "").strip()
    finding_ids = [finding_ref] if finding_ref else []
    # Pre-validate finding refs with a read-only load before opening the
    # write transaction. This guarantees no partial write is structurally
    # possible: the transaction body only appends + flips (no error paths).
    if finding_ids:
        try:
            ro_state = _load_state(args.devforge_dir)
        except (OSError, json.JSONDecodeError) as err:
            return _die("record-out-of-scope: {0}".format(err))
        err_msg = _validate_finding_refs(ro_state, finding_ids)
        if err_msg:
            return _die("record-out-of-scope: {0}".format(err_msg), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            oos_ref = "OOS-{0}".format(len(state["out_of_scope"]) + 1)
            state["out_of_scope"].append({
                "content": content,
                "finding_ref": finding_ref,
            })
            if finding_ids:
                _flip_findings(state, finding_ids, "OOS", oos_ref)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-out-of-scope: {0}".format(err))
    return 0


def cmd_record_constraint(args: argparse.Namespace) -> int:
    """Append a §7 Constraint entry — kind-specific shape."""
    # Hard-reject legacy --kind use with explicit migration message.
    if args.kind == "use":
        sys.stderr.write(
            "record-constraint: --kind use removed. Use --kind nfr (scale/latency),\n"
            "  --kind constitution_anchor (code-pattern rules), or\n"
            "  --kind external_system (integrations). Architecture choices belong\n"
            "  in /plan, not /specify §7.\n"
        )
        return 2
    try:
        kind = _validate_enum(args.kind, "kind", CONSTRAINT_KIND_ENUM)
        content = _validate_scalar(args.content, "content")
    except ValueError as err:
        return _die(str(err), code=2)

    finding_ids = _parse_finding_refs(getattr(args, "finding_ref", None))

    record: Dict[str, Any] = {"kind": kind, "content": content}

    if kind == "nfr":
        ok, msg = _validate_nfr_quantifier(args.quantifier or "")
        if not ok:
            return _die(msg, code=2)
        record["quantifier"] = args.quantifier.strip()
    elif kind == "constitution_anchor":
        ok, msg = _validate_constitution_anchor_ref(
            args.constitution_ref or "",
            args.devforge_dir,
        )
        if not ok:
            return _die(msg, code=2)
        record["constitution_ref"] = (args.constitution_ref or "").strip()
    elif kind == "external_system":
        ok, msg = _validate_external_system(
            args.protocol or "",
            args.contract_doc_ref or "",
        )
        if not ok:
            return _die(msg, code=2)
        if (args.protocol or "").strip():
            record["protocol"] = args.protocol.strip()
        if (args.contract_doc_ref or "").strip():
            record["contract_doc_ref"] = args.contract_doc_ref.strip()

    # Pre-validate finding refs with a read-only load before opening the
    # write transaction. This guarantees no partial write is structurally
    # possible: the transaction body only appends + flips (no error paths).
    if finding_ids:
        try:
            ro_state = _load_state(args.devforge_dir)
        except (OSError, json.JSONDecodeError) as err:
            return _die("record-constraint: {0}".format(err))
        err_msg = _validate_finding_refs(ro_state, finding_ids)
        if err_msg:
            return _die("record-constraint: {0}".format(err_msg), code=2)

    try:
        with _state_transaction(args.devforge_dir) as state:
            constraint_ref = "Constraint-{0}".format(
                len(state["constraints"]) + 1,
            )
            state["constraints"].append(record)
            if finding_ids:
                _flip_findings(state, finding_ids, "Constraint", constraint_ref)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-constraint: {0}".format(err))
    return 0


def cmd_record_open_question(args: argparse.Namespace) -> int:
    """Append a §8 Open Question entry."""
    try:
        question_id = _validate_scalar(args.question_id, "question_id")
        content = _validate_scalar(args.content, "content")
    except ValueError as err:
        return _die(str(err), code=2)
    category_no_dp_reason = (args.category_no_dp_reason or "").strip()
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["open_questions"].append({
                "question_id": question_id,
                "content": content,
                "category_no_dp_reason": category_no_dp_reason,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-open-question: {0}".format(err))
    return 0


def cmd_record_risk(args: argparse.Namespace) -> int:
    """Append a §9 Risks table row."""
    try:
        risk = _validate_scalar(args.risk, "risk")
        likelihood = _validate_enum(
            args.likelihood, "likelihood", LIKELIHOOD_ENUM,
        )
        impact = _validate_enum(args.impact, "impact", IMPACT_ENUM)
        mitigation = _validate_scalar(args.mitigation, "mitigation")
    except ValueError as err:
        return _die(str(err), code=2)
    finding_ids = _parse_finding_refs(getattr(args, "finding_ref", None))
    # Pre-validate finding refs with a read-only load before opening the
    # write transaction. This guarantees no partial write is structurally
    # possible: the transaction body only appends + flips (no error paths).
    if finding_ids:
        try:
            ro_state = _load_state(args.devforge_dir)
        except (OSError, json.JSONDecodeError) as err:
            return _die("record-risk: {0}".format(err))
        err_msg = _validate_finding_refs(ro_state, finding_ids)
        if err_msg:
            return _die("record-risk: {0}".format(err_msg), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            risk_ref = "Risk-{0}".format(len(state["risks"]) + 1)
            state["risks"].append({
                "risk": risk,
                "likelihood": likelihood,
                "impact": impact,
                "mitigation": mitigation,
            })
            if finding_ids:
                _flip_findings(state, finding_ids, "Risk", risk_ref)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-risk: {0}".format(err))
    return 0


def _next_ac_id(state: Dict[str, Any]) -> str:
    n = 1 + len(state["acceptance_criteria"])
    return "AC-{0}".format(n)


def cmd_add_ac(args: argparse.Namespace) -> int:
    """Add an Acceptance Criterion (or mark whole subsection N/A)."""
    try:
        subsection = _validate_enum(
            args.subsection, "subsection", AC_SUBSECTION_ENUM,
        )
    except ValueError as err:
        return _die(str(err), code=2)

    if args.mark_na:
        try:
            reason = _validate_scalar(args.n_a_reason, "n_a_reason")
        except ValueError as err:
            return _die(str(err), code=2)
        try:
            with _state_transaction(args.devforge_dir) as state:
                state["ac_subsection_na"][subsection] = reason
        except (OSError, json.JSONDecodeError) as err:
            return _die("add-ac: {0}".format(err))
        return 0

    try:
        ears_variant = _validate_enum(
            args.ears_variant, "ears_variant", EARS_VARIANT_ENUM,
        )
        statement = _validate_scalar(args.statement, "statement")
    except ValueError as err:
        return _die(str(err), code=2)

    verification_command = (args.verification_command or "").strip()
    test_anchor = (args.test_anchor or "").strip()

    if subsection in AC_UBIQUITOUS_ONLY_SUBSECTIONS:
        if ears_variant != "ubiquitous":
            return _die(
                "add-ac: subsection {0!r} requires ears_variant "
                "'ubiquitous' (Variance rule #10); got {1!r}".format(
                    subsection, ears_variant,
                ),
                code=2,
            )
        if not verification_command:
            return _die(
                "add-ac: subsection {0!r} requires non-empty "
                "--verification-command (Variance rule #10)".format(
                    subsection,
                ),
                code=2,
            )

    if not EARS_REGEX[ears_variant].match(statement):
        return _die(
            "add-ac: statement does not match EARS regex for variant "
            "{0!r}: {1!r}".format(ears_variant, statement),
            code=2,
        )

    finding_ids = _parse_finding_refs(getattr(args, "finding_ref", None))
    # Pre-validate finding refs with a read-only load before opening the
    # write transaction. This guarantees no partial write is structurally
    # possible: the transaction body only appends + flips (no error paths).
    if finding_ids:
        try:
            ro_state = _load_state(args.devforge_dir)
        except (OSError, json.JSONDecodeError) as err:
            return _die("add-ac: {0}".format(err))
        err_msg = _validate_finding_refs(ro_state, finding_ids)
        if err_msg:
            return _die("add-ac: {0}".format(err_msg), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            ac_id = (args.ac_id or "").strip() or _next_ac_id(state)
            state["acceptance_criteria"].append({
                "ac_id": ac_id,
                "subsection": subsection,
                "ears_variant": ears_variant,
                "statement": statement,
                "verification_command": verification_command,
                "test_anchor": test_anchor,
                "n_a_reason": "",
            })
            if finding_ids:
                _flip_findings(state, finding_ids, "AC", ac_id)
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-ac: {0}".format(err))
    sys.stdout.write(ac_id + "\n")
    return 0


# ---------------------------------------------------------------------------
# Standalone landing setter (for findings not landed via §5-§9 setters)
# ---------------------------------------------------------------------------

# Accepted buckets for set-finding-landed: all of LANDED_IN_ENUM minus
# "unlanded" (the caller intends to land, not un-land).
_LANDABLE_BUCKETS: Tuple[str, ...] = tuple(
    b for b in LANDED_IN_ENUM if b != "unlanded"
)


def _validate_design_source(value: str) -> Optional[str]:
    """Return None on success; an error message string on failure.

    Valid forms:
    - The literal "none"
    - "<scheme>:<target>" where scheme ∈ DESIGN_SOURCE_SCHEME_ENUM (excluding
      "none") and target is non-empty.

    Splitting on the FIRST colon only preserves figma URLs that contain
    'https://' (which contains a second colon).
    """
    if value == "none":
        return None
    colon_pos = value.find(":")
    if colon_pos < 0:
        return (
            "set-design-source: {0!r} is not a valid design source. "
            "Valid forms: html:<path> | figma:<url> | screenshot:<path> | none"
            .format(value)
        )
    scheme = value[:colon_pos]
    target = value[colon_pos + 1:]
    # SYNC contract: "none" is a bare sentinel — "none:" or "none:<target>"
    # is invalid.  Check this before the generic "scheme not recognised" path
    # so the error message is accurate (none IS recognised, it just cannot
    # take a colon).
    if scheme == "none":
        return (
            "set-design-source: 'none' is a bare sentinel and cannot take a "
            "colon/target (e.g. 'none:something' is invalid). "
            "Valid forms: html:<path> | figma:<url> | screenshot:<path> | none"
        )
    valid_schemes = tuple(s for s in DESIGN_SOURCE_SCHEME_ENUM if s != "none")
    if scheme not in valid_schemes:
        return (
            "set-design-source: scheme {0!r} not recognised. "
            "Valid forms: html:<path> | figma:<url> | screenshot:<path> | none"
            .format(scheme)
        )
    if not target:
        return (
            "set-design-source: target (after the colon) cannot be empty for "
            "scheme {0!r}. Valid forms: html:<path> | figma:<url> | "
            "screenshot:<path> | none".format(scheme)
        )
    return None


def cmd_set_design_source(args: argparse.Namespace) -> int:
    """Set the design_source field (renders as **Design source**: in spec.md).

    --value must be the literal "none" or "<scheme>:<target>" where scheme
    is one of html / figma / screenshot and target is non-empty.
    Figma URLs containing multiple colons are handled by splitting on the
    FIRST colon only.
    """
    value = (getattr(args, "value", None) or "").strip()
    if not value:
        return _die(
            "set-design-source: --value is required and non-empty. "
            "Valid forms: html:<path> | figma:<url> | screenshot:<path> | none",
            code=2,
        )
    err = _validate_design_source(value)
    if err is not None:
        return _die(err, code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["design_source"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-design-source: {0}".format(err))
    return 0


def cmd_set_finding_landed(args: argparse.Namespace) -> int:
    """Directly flip landed_in / landed_ref on a named finding.

    Use this when the landing is not driven by a §5-§9 setter call (e.g.
    correcting a typo in landed_ref, or applying a landing that was done
    outside the helper).

    --finding-id  required; must match a recorded finding's finding_id.
    --landed-in   required; one of AC / Constraint / OOS / Risk.
    --landed-ref  optional; the id/label of the landing entry (e.g. "AC-3").
    """
    finding_id = (getattr(args, "finding_id", None) or "").strip()
    if not finding_id:
        return _die(
            "set-finding-landed: --finding-id is required and non-empty",
            code=2,
        )
    landed_in = (getattr(args, "landed_in", None) or "").strip()
    if not landed_in:
        return _die(
            "set-finding-landed: --landed-in is required and non-empty",
            code=2,
        )
    if landed_in not in _LANDABLE_BUCKETS:
        return _die(
            "set-finding-landed: --landed-in {0!r} not in {1!r}".format(
                landed_in, _LANDABLE_BUCKETS,
            ),
            code=2,
        )
    landed_ref = (getattr(args, "landed_ref", None) or "").strip()
    # Pre-validate the finding-id with a read-only load before opening the
    # write transaction. This guarantees no partial write is structurally
    # possible: the transaction body only flips (no error paths remain).
    try:
        ro_state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-finding-landed: {0}".format(err))
    err_msg = _validate_finding_refs(ro_state, [finding_id])
    if err_msg:
        return _die("set-finding-landed: {0}".format(err_msg), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            _flip_findings(state, [finding_id], landed_in, landed_ref)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-finding-landed: {0}".format(err))
    return 0
