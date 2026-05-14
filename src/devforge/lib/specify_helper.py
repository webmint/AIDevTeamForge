"""specify_helper — state helper for /specify.

Owns the shape of `.devforge/specify-state.json` — the full SpecDoc
container plus per-phase progress flags. Mirrors the helper-owns-shape
pattern from research_helper / discover_helper / constitute_helper /
configure_helper.

/specify converts an approved feature/bug/refactor request into a 9-section
spec.md under `specs/NNN-feature-name/` with categorized acceptance
criteria (7 subsections), EARS-formatted statements, and a coverage rule
that traces every Phase 1.5 finding to a landing in §5/§6/§7/§9.

State file
----------

  .devforge/specify-state.json — full SpecDoc + phase progress.

Subcommand summary (Phase 0 / 1 / 1.5 — this session)
----------------------------------------------------

  Plumbing     reset-state, read-state, preflight
  Phase 1      record-input-read, phase1-finalize
  Phase 1.5    record-finding, mark-source-no-items-relevant,
               verify-findings, render-findings, findings-finalize

Phase 2-5 subcommands (decision points, codebase analysis, spec render,
approval) ship in a subsequent session per SPECIFY-REDESIGN-PLAN.md
Work order.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

try:
    import fcntl
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX fallback
    _HAVE_FCNTL = False


# ---------------------------------------------------------------------------
# Schema constants — single source of truth.
# ---------------------------------------------------------------------------

STATE_FILE_NAME = "specify-state.json"

# Hard-gate prereqs (mirrors discover_helper / research_helper). The
# SPECIFY-REDESIGN-PLAN.md Prerequisites table cites `manifest.json` /
# `project-config.json`, but the shipped /init-forge writes
# `.devforge/init.yaml` and /configure writes `.devforge/configure.yaml`
# (project-config.json is a downstream render). Matching the existing
# helpers — single source of truth.
PREFLIGHT_PREREQS: Tuple[Tuple[str, str], ...] = (
    (".devforge/init.yaml", "/init-forge"),
    ("docs/architecture.md", "/generate-docs"),
    (".devforge/configure.yaml", "/configure"),
    ("constitution.md", "/constitute"),
)

# Constitution populate-guard literal (v3 verbatim). Preflight refuses to
# pass when this string is present in constitution.md.
CONSTITUTION_POPULATE_GUARD = "_Run /constitute to populate_"

# Phase 1 — source_origin enum (auto-tagged from file path).
SOURCE_ORIGIN_ENUM: Tuple[str, ...] = (
    "discover", "research", "prior_spec", "context",
)

# Spec status lifecycle (v3 verbatim).
SPEC_STATUS_ENUM: Tuple[str, ...] = (
    "Draft", "Approved", "In Progress", "Complete",
)
SPEC_STATUS_DEFAULT = "Draft"

# Spec type — v3's 4 + v3.1 greenfield (Open Question #7 closed 2026-05-11).
SPEC_TYPE_ENUM: Tuple[str, ...] = (
    "migration_tooling", "feature_addition", "bug_fix", "refactor",
    "greenfield_feature",
)

# Phase 1.5 — Variance rule #5 finding-landing tracker.
LANDED_IN_ENUM: Tuple[str, ...] = (
    "AC", "Constraint", "OOS", "Risk", "unlanded",
)
LANDED_IN_DEFAULT = "unlanded"

# Phase 2 — decision-point categories (Variance rule #1, v3 verbatim,
# locked order). Tests enforce identity.
DP_CATEGORY_ENUM: Tuple[str, ...] = (
    "scope_boundaries", "existing_behavior", "data_flow_state",
    "edge_cases", "ui_ux_details", "breaking_changes",
    "tooling_configuration",
)
DP_STATUS_ENUM: Tuple[str, ...] = (
    "pending", "answered", "default_applied",
    "deferred_OOS", "deferred_open_question",
    "no_DP_in_category",
)
DP_COVERAGE_STATE_ENUM: Tuple[str, ...] = (
    "Clear", "Partial", "Missing", "NoDPInCategory",
)
DP_TURN_CAP = 3

# Phase 4 — AC subsection enum (Variance rule #4, v3 verbatim, locked
# order: 5.1 → 5.7).
AC_SUBSECTION_ENUM: Tuple[str, ...] = (
    "tooling_artifact_presence",  # 5.1
    "behavior_preservation",      # 5.2
    "behavior_change",            # 5.3
    "ci_pipeline",                # 5.4
    "hooks_gates",                # 5.5
    "documentation",              # 5.6
    "hygiene",                    # 5.7
)
# Subsections that may use only the Ubiquitous EARS variant + require
# verification_command (Variance rule #10, Open Question #9 closed).
AC_UBIQUITOUS_ONLY_SUBSECTIONS: Tuple[str, ...] = (
    "tooling_artifact_presence", "hygiene",
)

# EARS notation variants (Kiro / IEEE 29148-2018; Variance rule #10).
EARS_VARIANT_ENUM: Tuple[str, ...] = (
    "ubiquitous", "event_driven", "state_driven", "optional", "unwanted",
)
EARS_REGEX: Dict[str, "re.Pattern[str]"] = {
    "ubiquitous":   re.compile(r"^The [^.]+ shall [^.]+\.$"),
    "event_driven": re.compile(r"^WHEN [^,]+,? the [^.]+ shall [^.]+\.$"),
    "state_driven": re.compile(r"^WHILE [^,]+,? the [^.]+ shall [^.]+\.$"),
    "optional":     re.compile(r"^WHERE [^,]+,? the [^.]+ shall [^.]+\.$"),
    "unwanted":     re.compile(r"^IF [^,]+, THEN the [^.]+ shall [^.]+\.$"),
}

# Misalignment classification (mirrors /discover + /research).
CONFLICT_TYPE_ENUM: Tuple[str, ...] = ("direct", "drift", "refinement")

# Phase 4 — Risk-table enums.
LIKELIHOOD_ENUM: Tuple[str, ...] = ("Low", "Med", "High")
IMPACT_ENUM: Tuple[str, ...] = ("Low", "Med", "High")

# Constraint kind enum (Phase 4 §7).
CONSTRAINT_KIND_ENUM: Tuple[str, ...] = ("follow", "not_break", "use")

# Mode-detection signals (Variance rule #8, Open Question #8 C-strict).
AUTO_MODE_ENV_VAR = "DEVFORGE_AUTO_MODE"
AUTO_MODE_REMINDER_SUBSTRINGS: Tuple[str, ...] = (
    "auto mode is active", "auto mode still active",
)


# ---------------------------------------------------------------------------
# Topic-token + filename-match helpers (Phase 1 adapter; Variance rule #5).
# ---------------------------------------------------------------------------

_TOPIC_TOKEN_RE = re.compile(r"[a-z0-9]+")
_TOPIC_MIN_TOKEN_LEN = 3
# Common date-prefix tokens that exist on every dated filename — match on
# these alone yields false positives. Suppress whole-numeric tokens of
# length 4 (year-like) — keeps month/day digits out too since both are
# shorter than the min-length cutoff.
_TOPIC_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "into", "this", "that",
})


def topic_tokens(topic: str) -> List[str]:
    """Tokens from a free-form topic string (≥3 alnum chars, not stopword)."""
    out = []
    for t in _TOPIC_TOKEN_RE.findall(topic.lower()):
        if len(t) < _TOPIC_MIN_TOKEN_LEN:
            continue
        if t in _TOPIC_STOPWORDS:
            continue
        if t.isdigit() and len(t) == 4:
            continue
        out.append(t)
    return out


def filename_tokens(filename: str) -> List[str]:
    """Tokens from a filename stem (extension dropped)."""
    stem = Path(filename).stem.lower()
    out = []
    for t in _TOPIC_TOKEN_RE.findall(stem):
        if len(t) < _TOPIC_MIN_TOKEN_LEN:
            continue
        if t in _TOPIC_STOPWORDS:
            continue
        if t.isdigit() and len(t) == 4:
            continue
        out.append(t)
    return out


def filename_matches_topic(filename: str, topic: str) -> bool:
    """Filename has ≥1 token overlap with task-topic tokens.

    Deterministic; no LLM. Used by orchestrator (or callers) to decide
    which research/, discover/, specs/ files to enumerate in Phase 1.
    Variance rule #5: no LLM re-interpretation in adapter — filename only,
    no content match.
    """
    return bool(set(topic_tokens(topic)) & set(filename_tokens(filename)))


# ---------------------------------------------------------------------------
# Source-origin path tagging (Phase 1; v3.1 path-based, no content parse).
# ---------------------------------------------------------------------------


def source_origin_for_path(path: str) -> str:
    """Auto-tag source_origin from file path. Variance rule #5."""
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
    if p.startswith("discover/"):
        return "discover"
    if p.startswith("research/"):
        return "research"
    if p.startswith("specs/"):
        return "prior_spec"
    return "context"


# ---------------------------------------------------------------------------
# Default state builder.
# ---------------------------------------------------------------------------


def default_state() -> Dict[str, Any]:
    """Fresh SpecDoc state. Full Step 2 schema shape — all phase buckets."""
    return {
        # --- Header / classification ---------------------------------------
        "topic": None,
        "topic_slug": None,
        "date": None,
        "spec_number": None,
        "feature_name": None,
        "feature_slug": None,
        "spec_type": None,
        "spec_type_rationale": None,
        "spec_type_seeded_by_upstream": False,
        "status": SPEC_STATUS_DEFAULT,

        # --- Phase 0 — branch state ----------------------------------------
        "current_branch": None,
        "default_branch": None,
        "branch_decision": None,
        "branch_created": None,

        # --- Phase 1 — input reads -----------------------------------------
        # [{path, source_origin, read_timestamp}]
        "input_reads": [],
        "phase1_finalized": False,

        # --- Phase 1.5 — findings ------------------------------------------
        # [{finding_id, source_path, source_section, content,
        #   landed_in, landed_ref}]
        "findings": [],
        # Path-keyed marker for sources read but irrelevant to task.
        "source_no_items_relevant": {},
        "findings_finalized": False,

        # --- Phase 2 — decision points -------------------------------------
        # [{dp_id, category, description, valid_implementations,
        #   status, user_answer, default_applied, deferral_reason, turns}]
        "decision_points": [],
        "dp_finalized": False,
        "mode": None,  # "auto" / "interactive" (helper-recorded after detect)

        # --- Phase 3 — codebase analysis -----------------------------------
        # [{spec_type, read_path, n_a_reason}]
        "mandatory_reads": [],
        # [{path, tool, note}]
        "discretionary_reads": [],
        "phase3_finalized": False,

        # --- Phase 4 — spec sections ---------------------------------------
        "overview": None,
        "current_state": None,
        "desired_behavior": None,
        # [{area, files, impact}]
        "affected_areas": [],
        # Full AC schema per AcceptanceCriterion (subsection, ears_variant,
        # statement, verification_command, test_anchor, n_a_reason)
        "acceptance_criteria": [],
        # {subsection: reason}  for explicit N/A on a whole subsection
        "ac_subsection_na": {},
        # [{content, finding_ref}]
        "out_of_scope": [],
        # [{kind, content}]  kind ∈ CONSTRAINT_KIND_ENUM
        "constraints": [],
        # [{question_id, content, category_no_dp_reason}]
        "open_questions": [],
        # [{risk, likelihood, impact, mitigation}]
        "risks": [],

        # --- Phase 5 — approval + handoff ----------------------------------
        "approval_summary": None,
        "plan_handoff_block": None,

        # --- Downstream — /plan + /breakdown resolve-open-question audit ---
        # [{question_id, resolution_text, resolution_phase, resolution_timestamp}]
        "open_question_resolutions": [],

        # --- Misalignment log ----------------------------------------------
        # [{conflict_type, anchor, drift_target, resolution}]
        "conflicts": [],
    }


# ---------------------------------------------------------------------------
# State-file plumbing (load / dump / transaction).
# ---------------------------------------------------------------------------


def _state_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    return Path(devforge_dir) / STATE_FILE_NAME


def _atomic_write_json(state: Dict[str, Any], target: Path) -> None:
    """Atomically write state as JSON. Same pattern as discover_helper."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="specify-", suffix=".json.tmp", dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _load_state(devforge_dir: Union[str, "os.PathLike[str]"]) -> Dict[str, Any]:
    path = _state_path(devforge_dir)
    if not path.exists():
        return default_state()
    return json.loads(path.read_text(encoding="utf-8"))


def _lock_path(state_path: Path) -> Path:
    return state_path.parent / (state_path.name + ".lock")


@contextlib.contextmanager
def _state_transaction(
    devforge_dir: Union[str, "os.PathLike[str]"],
) -> Iterator[Dict[str, Any]]:
    """Read-modify-write under POSIX fcntl lock. Mirrors discover_helper."""
    state_path = _state_path(devforge_dir)
    Path(devforge_dir).mkdir(parents=True, exist_ok=True)
    lock = _lock_path(state_path)
    fd = os.open(str(lock), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if _HAVE_FCNTL:
            fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            state = _load_state(devforge_dir)
            yield state
            _atomic_write_json(state, state_path)
        finally:
            if _HAVE_FCNTL:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Error + validation helpers.
# ---------------------------------------------------------------------------


def _die(message: str, code: int = 1) -> int:
    sys.stderr.write("specify_helper: {0}\n".format(message))
    return code


def _validate_scalar(value: str, field_name: str) -> str:
    stripped = (value or "").strip()
    if not stripped:
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return stripped


def _validate_enum(
    value: str, field_name: str, allowed: Tuple[str, ...],
) -> str:
    if value not in allowed:
        raise ValueError(
            "{0}: value {1!r} not in allowed {2!r}".format(
                field_name, value, allowed,
            )
        )
    return value


def _utc_timestamp() -> str:
    """ISO-8601 UTC timestamp at second precision (deterministic format)."""
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


# ---------------------------------------------------------------------------
# Phase 0 — preflight.
# ---------------------------------------------------------------------------


def cmd_reset_state(args: argparse.Namespace) -> int:
    """Reset .devforge/specify-state.json to default. Idempotent."""
    try:
        _atomic_write_json(default_state(), _state_path(args.devforge_dir))
    except OSError as err:
        return _die("reset-state: {0}".format(err))
    return 0


def cmd_read_state(args: argparse.Namespace) -> int:
    """Dump current state as JSON to stdout."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("read-state: {0}".format(err))
    json.dump(state, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    """4-artefact hard gate + constitution populate-guard.

    Checks each PREFLIGHT_PREREQS path relative to --install-root for
    existence + non-empty (size > 0). For constitution.md, also rejects
    when the v3 populate-guard literal is still present (means /constitute
    has not run yet even though the file exists). Emits one Missing line
    per absent artefact + a populate-guard line if applicable. Exits 2 on
    any failure; lists every problem (not just the first).
    """
    install_root = Path(args.install_root)
    missing: List[Tuple[str, str]] = []
    populate_guard_present = False
    for rel_path, producer in PREFLIGHT_PREREQS:
        p = install_root / rel_path
        try:
            if not p.exists():
                missing.append((rel_path, producer))
                continue
            if p.stat().st_size == 0:
                missing.append((rel_path, producer))
                continue
        except OSError as err:
            return _die("preflight: stat failed on {0}: {1}".format(p, err))
        if rel_path == "constitution.md":
            try:
                text = p.read_text(encoding="utf-8")
            except OSError as err:
                return _die(
                    "preflight: read failed on {0}: {1}".format(p, err)
                )
            if CONSTITUTION_POPULATE_GUARD in text:
                populate_guard_present = True

    if missing or populate_guard_present:
        sys.stderr.write(
            "BLOCKED: /specify requires the full 4-command setup chain.\n"
        )
        for rel, producer in missing:
            sys.stderr.write(
                "Missing: {0} (produced by {1})\n".format(rel, producer)
            )
        if populate_guard_present:
            sys.stderr.write(
                "constitution.md present but populate-guard literal "
                "{0!r} still in place — run /constitute to populate.\n".format(
                    CONSTITUTION_POPULATE_GUARD,
                )
            )
        sys.stderr.write(
            "Run: /init-forge → /generate-docs → /configure → /constitute, "
            "then retry /specify.\n"
        )
        return 2
    return 0


# ---------------------------------------------------------------------------
# Phase 1 — input reads.
# ---------------------------------------------------------------------------

# Mandatory base reads — every project must have these regardless of
# topic. Optional dirs (research/, discover/, specs/) are not gated here;
# Phase 1.5 verify-findings handles per-source enumeration.
PHASE1_MANDATORY_READS: Tuple[str, ...] = (
    "constitution.md",
    ".claude/memory/MEMORY.md",
    "CLAUDE.md",
    "docs/architecture.md",
)


def cmd_record_input_read(args: argparse.Namespace) -> int:
    """Record one Phase 1 input read; auto-tag source_origin from path.

    Idempotent: re-recording the same path overwrites the prior entry
    (last-write wins on timestamp). Variance rule #5: no content parsing.
    """
    try:
        path = _validate_scalar(args.path, "record-input-read.path")
    except ValueError as err:
        return _die(str(err), code=2)
    origin = source_origin_for_path(path)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["input_reads"] = [
                r for r in state["input_reads"] if r.get("path") != path
            ]
            state["input_reads"].append({
                "path": path,
                "source_origin": origin,
                "read_timestamp": _utc_timestamp(),
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-input-read: {0}".format(err))
    return 0


def cmd_phase1_finalize(args: argparse.Namespace) -> int:
    """Gate Phase 1 → Phase 1.5. All 4 mandatory base reads required.

    Discretionary dirs (research/, discover/, specs/) handled downstream
    by Phase 1.5 verify-findings.
    """
    try:
        with _state_transaction(args.devforge_dir) as state:
            read_paths = {r.get("path") for r in state["input_reads"]}
            missing = [
                m for m in PHASE1_MANDATORY_READS if m not in read_paths
            ]
            if missing:
                sys.stderr.write(
                    "phase1-finalize: missing mandatory input reads:\n"
                )
                for m in missing:
                    sys.stderr.write("  - {0}\n".format(m))
                return 2
            state["phase1_finalized"] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("phase1-finalize: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Phase 1.5 — findings enumeration.
# ---------------------------------------------------------------------------


def _finding_slug(source_path: str) -> str:
    """Derive the source-slug used in F-<slug>-N finding ids."""
    stem = Path(source_path).stem.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return cleaned or "src"


def _next_finding_id(state: Dict[str, Any], source_path: str) -> str:
    slug = _finding_slug(source_path)
    prefix = "F-{0}-".format(slug)
    n = 1 + sum(
        1 for f in state["findings"]
        if f.get("finding_id", "").startswith(prefix)
    )
    return "{0}{1}".format(prefix, n)


def cmd_record_finding(args: argparse.Namespace) -> int:
    """Record one Phase 1.5 finding. Auto-clears no-items-relevant marker."""
    try:
        source_path = _validate_scalar(args.source_path, "source_path")
        content = _validate_scalar(args.content, "content")
        landed_in = args.landed_in or LANDED_IN_DEFAULT
        _validate_enum(landed_in, "landed_in", LANDED_IN_ENUM)
    except ValueError as err:
        return _die(str(err), code=2)
    source_section = (args.source_section or "").strip()
    landed_ref = (args.landed_ref or "").strip()
    try:
        with _state_transaction(args.devforge_dir) as state:
            fid = _next_finding_id(state, source_path)
            state["findings"].append({
                "finding_id": fid,
                "source_path": source_path,
                "source_section": source_section,
                "content": content,
                "landed_in": landed_in,
                "landed_ref": landed_ref,
            })
            if source_path in state["source_no_items_relevant"]:
                del state["source_no_items_relevant"][source_path]
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-finding: {0}".format(err))
    sys.stdout.write(fid + "\n")
    return 0


def cmd_mark_source_no_items_relevant(args: argparse.Namespace) -> int:
    """Mark a read source as having no task-relevant content.

    Waives the ≥3-bullet rule for that source. Refuses on unread sources
    or when findings already exist for the path (mutual exclusion).
    """
    try:
        source_path = _validate_scalar(args.source_path, "source_path")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            read_paths = {r.get("path") for r in state["input_reads"]}
            if source_path not in read_paths:
                return _die(
                    "mark-source-no-items-relevant: {0!r} not in "
                    "input_reads (record-input-read first)".format(
                        source_path,
                    ),
                    code=2,
                )
            if any(
                f.get("source_path") == source_path
                for f in state["findings"]
            ):
                return _die(
                    "mark-source-no-items-relevant: {0!r} already has "
                    "findings".format(source_path),
                    code=2,
                )
            state["source_no_items_relevant"][source_path] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("mark-source-no-items-relevant: {0}".format(err))
    return 0


def _source_coverage(
    state: Dict[str, Any], path: str,
) -> Tuple[str, int]:
    """Return (status, n_findings). status ∈ {clear, partial, marker, none}."""
    count = sum(
        1 for f in state["findings"] if f.get("source_path") == path
    )
    if count >= 3:
        return ("clear", count)
    if count >= 1:
        return ("partial", count)
    if state["source_no_items_relevant"].get(path):
        return ("marker", 0)
    return ("none", 0)


def cmd_verify_findings(args: argparse.Namespace) -> int:
    """Per-source: ≥3 findings OR no-items-relevant marker. Variance rule #3."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-findings: {0}".format(err))
    problems: List[Tuple[str, str, int]] = []
    for r in state["input_reads"]:
        path = r.get("path")
        status, count = _source_coverage(state, path)
        if status in ("partial", "none"):
            problems.append((path, status, count))
    if problems:
        sys.stderr.write(
            "verify-findings: insufficient findings per source:\n"
        )
        for path, status, count in problems:
            sys.stderr.write(
                "  - {0}: {1} ({2} findings; need ≥3 or "
                "no-items-relevant marker)\n".format(path, status, count)
            )
        return 2
    return 0


# Helper-owned render-group order (matches plan §Phase 1.5 template, with
# F3 fix — discover/ subheading inserted between research/ and CLAUDE.md).
_RENDER_SECTION_ORDER: Tuple[str, ...] = (
    "constitution.md",
    ".claude/memory/MEMORY.md",
    "research/",
    "discover/",
    "CLAUDE.md",
    "docs/",
    "specs/",
)


def _group_for_path(path: str) -> str:
    """Map a recorded input path to its render-group key."""
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
    for prefix in ("research/", "discover/", "docs/", "specs/"):
        if p.startswith(prefix):
            return prefix
    return p


def cmd_render_findings(args: argparse.Namespace) -> int:
    """Emit Phase 1.5 findings section in v3-verbatim format."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-findings: {0}".format(err))
    lines: List[str] = ["## Findings from Inputs", ""]
    reads_by_group: Dict[str, List[str]] = {}
    for r in state["input_reads"]:
        g = _group_for_path(r.get("path", ""))
        reads_by_group.setdefault(g, []).append(r["path"])

    for group in _RENDER_SECTION_ORDER:
        paths = sorted(reads_by_group.get(group, []))
        if not paths:
            continue
        for path in paths:
            lines.append("### From {0}".format(path))
            f_for_path = [
                f for f in state["findings"]
                if f.get("source_path") == path
            ]
            f_for_path.sort(key=lambda f: f.get("finding_id", ""))
            if f_for_path:
                for i, f in enumerate(f_for_path, 1):
                    lines.append("{0}. {1}".format(i, f.get("content", "")))
            elif state["source_no_items_relevant"].get(path):
                lines.append("No items relevant to this spec.")
            else:
                lines.append("_(no findings recorded yet)_")
            lines.append("")

    sys.stdout.write("\n".join(lines).rstrip() + "\n")
    return 0


def cmd_findings_finalize(args: argparse.Namespace) -> int:
    """Gate Phase 1.5 → Phase 2. Re-runs verify-findings then stamps."""
    rc = cmd_verify_findings(args)
    if rc != 0:
        return rc
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["findings_finalized"] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("findings-finalize: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# CLI parser + main.
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="specify_helper",
        description="State helper for /specify; owns "
                    ".devforge/specify-state.json shape.",
    )
    parser.add_argument(
        "--devforge-dir", default=".devforge",
        help="Path to .devforge dir (default: .devforge)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("reset-state", help="Reset state to defaults.")
    sp.set_defaults(func=cmd_reset_state)

    sp = sub.add_parser("read-state", help="Dump state JSON to stdout.")
    sp.set_defaults(func=cmd_read_state)

    sp = sub.add_parser(
        "preflight", help="Hard-gate 4-command chain + constitution guard.",
    )
    sp.add_argument("--install-root", default=".")
    sp.set_defaults(func=cmd_preflight)

    sp = sub.add_parser(
        "record-input-read",
        help="Record a Phase 1 input read (path-tagged source_origin).",
    )
    sp.add_argument("--path", required=True)
    sp.set_defaults(func=cmd_record_input_read)

    sp = sub.add_parser(
        "phase1-finalize",
        help="Gate Phase 1 → Phase 1.5 (all 4 mandatory reads recorded).",
    )
    sp.set_defaults(func=cmd_phase1_finalize)

    sp = sub.add_parser(
        "record-finding", help="Record a Phase 1.5 finding.",
    )
    sp.add_argument("--source-path", required=True, dest="source_path")
    sp.add_argument("--content", required=True)
    sp.add_argument(
        "--source-section", default="", dest="source_section",
    )
    sp.add_argument(
        "--landed-in", default=LANDED_IN_DEFAULT, dest="landed_in",
    )
    sp.add_argument("--landed-ref", default="", dest="landed_ref")
    sp.set_defaults(func=cmd_record_finding)

    sp = sub.add_parser(
        "mark-source-no-items-relevant",
        help="Mark a read source as irrelevant (waives ≥3-bullet rule).",
    )
    sp.add_argument("--source-path", required=True, dest="source_path")
    sp.set_defaults(func=cmd_mark_source_no_items_relevant)

    sp = sub.add_parser(
        "verify-findings",
        help="Per-source coverage check (≥3 findings or marker).",
    )
    sp.set_defaults(func=cmd_verify_findings)

    sp = sub.add_parser(
        "render-findings", help="Emit Phase 1.5 section to stdout.",
    )
    sp.set_defaults(func=cmd_render_findings)

    sp = sub.add_parser(
        "findings-finalize",
        help="Gate Phase 1.5 → Phase 2 (verify-findings + stamp).",
    )
    sp.set_defaults(func=cmd_findings_finalize)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
