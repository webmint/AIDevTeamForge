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

Subcommand summary (Phase 0 / 1 / 1.5 / 2 / 3 / 4 / 5 + downstream
+ cross-phase)
-----------------------------------------------------------------

  Plumbing     reset-state, read-state, preflight
  Phase 1      record-input-read, phase1-finalize
  Phase 1.5    record-finding, mark-source-no-items-relevant,
               verify-findings, render-findings, findings-finalize
  Phase 2      detect-mode, record-decision-point, set-dp-answer,
               set-dp-default-applied, set-dp-deferral, dp-coverage,
               rubric-coverage, verify-decision-coverage,
               rubric-finalize, dp-finalize
  Phase 3      classify-spec-type, record-mandatory-read,
               verify-mandatory-reads, phase3-finalize
  Phase 4      assign-spec-number, assign-feature-name, set-date,
               create-branch, record-affected-area, set-overview,
               set-current-state, set-desired-behavior, add-ac,
               record-out-of-scope, record-constraint,
               record-open-question, record-risk, verify-coverage,
               verify-numerical-consistency,
               verify-ac-subsection-coverage, verify-ac-shape,
               check-constitution-compliance, render
  Phase 5      render-summary, set-status, render-plan-handoff,
               check-constitution-compliance (re-runs)
  Downstream   resolve-open-question
  Cross-phase  summary

Misalignment subcommands (`check-conflicts`,
`record-conflict-resolution`) deferred until /specify orchestrator
needs them; the underlying `state["conflicts"]` field is provisioned
already.

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

# Phase 4 — feature-name kebab-case validator (2-4 segments, lower-case,
# digits permitted but not as first char of a segment-start; locked here
# so assign-feature-name + render share one source of truth).
FEATURE_NAME_RE: "re.Pattern[str]" = re.compile(
    r"^[a-z][a-z0-9]*(?:-[a-z0-9]+){1,3}$"
)
SPECS_ROOT_DEFAULT = "specs"
SPEC_NUMBER_WIDTH = 3
SPEC_NUMBER_DIR_RE = re.compile(r"^(\d{3})-")

# Phase 4 §5 — AC subsection heading labels (v3-verbatim).
SUBSECTION_HEADING_BY_KEY: Dict[str, Tuple[str, str]] = {
    "tooling_artifact_presence": ("5.1", "Tooling / artifact presence and absence"),
    "behavior_preservation":     ("5.2", "Behavior preservation"),
    "behavior_change":           ("5.3", "Behavior change"),
    "ci_pipeline":               ("5.4", "CI / pipeline"),
    "hooks_gates":               ("5.5", "Hooks / gates"),
    "documentation":             ("5.6", "Documentation"),
    "hygiene":                   ("5.7", "Hygiene"),
}

# Phase 4 §5 framing (v3 verbatim — Appendix A "LLM-facing prose blocks").
AC_FRAMING_LINE = (
    "Each AC must be testable and unambiguous. **Cover each category "
    "that applies. Mark non-applicable categories with \"N/A — [reason]\".**"
)

# Phase 4 §6 — Coverage rule banner (v3 verbatim).
COVERAGE_RULE_BANNER = (
    "**Coverage rule (v3)**: For each Phase 1.5 finding, the finding "
    "either (a) becomes an AC in §5, (b) becomes a Constraint in §7, "
    "(c) is explicitly listed here as out of scope, OR (d) is in §9 "
    "Risks with documented mitigation. Unlanded finding = hard error — "
    "re-verify Phase 1.5 enumeration is complete before saving."
)

# Phase 4 §7 — constraint-kind render labels (v3 verbatim).
CONSTRAINT_KIND_LABEL: Dict[str, str] = {
    "follow":    "Must follow",
    "not_break": "Must not break",
    "use":       "Must use",
}

# Phase 4 — numerical-verification regexes.
# Conservative seed: a digit run followed by one whitespace + an alpha
# noun (≥1 char). Headings (^#+) and table separators (^|---|) skipped.
# Group by lowercased noun; flag noun appearing ≥2 times with distinct
# numeric values. Refine in Step 8 empirical run.
NUMERIC_DIGIT_NOUN_RE: "re.Pattern[str]" = re.compile(
    r"\b(\d+)\s+([a-zA-Z]+)\b"
)
NUMERIC_HEADING_RE: "re.Pattern[str]" = re.compile(r"^\s*#+\s")
NUMERIC_TABLE_SEP_RE: "re.Pattern[str]" = re.compile(
    r"^\s*\|[-:|\s]+\|\s*$"
)

# Phase 4 — constitution-recheck rule extractor + token tooling.
# Match MUST / MUST NOT / SHALL / SHALL NOT lines (case-insensitive).
CONSTITUTION_RULE_RE: "re.Pattern[str]" = re.compile(
    r"\b(MUST\s+NOT|MUST|SHALL\s+NOT|SHALL)\b", re.IGNORECASE,
)
# Stopwords for token-overlap scan. Conservative — high-precision-but-
# moderate-recall. Refine on empirical signal.
CONSTITUTION_STOPWORDS: frozenset = frozenset({
    "the", "and", "or", "of", "to", "in", "on", "for", "with", "by",
    "not", "this", "that", "must", "shall", "will", "do", "does",
    "any", "all", "no", "yes", "than", "then", "from", "into", "are",
    "is", "be", "been", "have", "has", "had", "what", "when", "where",
    "which", "who", "why", "how", "as", "at", "an", "a", "it", "its",
    "if", "but", "so", "such", "may", "can", "could", "should", "would",
})

# Downstream — resolve-open-question phase enum.
RESOLUTION_PHASE_ENUM: Tuple[str, ...] = ("plan", "breakdown")


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
# Phase 2 — mode detection + decision-point coverage.
# ---------------------------------------------------------------------------


def detect_mode(
    env: Dict[str, str],
    auto_flag: bool,
    reminder_text: str,
) -> str:
    """C-strict mode detection (Variance rule #8). Three signals:

      - DEVFORGE_AUTO_MODE env var == "1"
      - --auto flag set
      - case-insensitive substring of any AUTO_MODE_REMINDER_SUBSTRINGS in
        the supplied reminder_text (orchestrator passes the latest
        <system-reminder> block content)

    No LLM judgment — defaults to "interactive" when no signal fires.
    """
    if env.get(AUTO_MODE_ENV_VAR) == "1":
        return "auto"
    if auto_flag:
        return "auto"
    if reminder_text:
        haystack = reminder_text.lower()
        for needle in AUTO_MODE_REMINDER_SUBSTRINGS:
            if needle in haystack:
                return "auto"
    return "interactive"


def cmd_detect_mode(args: argparse.Namespace) -> int:
    """Resolve mode from C-strict signals, persist, print to stdout."""
    mode = detect_mode(
        os.environ,
        bool(args.auto),
        args.reminder_text or "",
    )
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["mode"] = mode
    except (OSError, json.JSONDecodeError) as err:
        return _die("detect-mode: {0}".format(err))
    sys.stdout.write(mode + "\n")
    return 0


def _next_dp_id(state: Dict[str, Any], category: str) -> str:
    prefix = "DP-{0}-".format(category)
    n = 1 + sum(
        1 for d in state["decision_points"]
        if d.get("dp_id", "").startswith(prefix)
    )
    return "{0}{1}".format(prefix, n)


def _find_dp(state: Dict[str, Any], dp_id: str) -> Optional[Dict[str, Any]]:
    for d in state["decision_points"]:
        if d.get("dp_id") == dp_id:
            return d
    return None


def cmd_record_decision_point(args: argparse.Namespace) -> int:
    """Record a new DecisionPoint. ≥2 valid_implementations required.

    Pass `--no-dp-in-category` instead of `--description` to record the
    terminal NoDPInCategory marker for a category (its valid_implementations
    list is empty by definition; description carries the no-DP rationale).
    """
    try:
        category = _validate_enum(
            args.category, "category", DP_CATEGORY_ENUM,
        )
    except ValueError as err:
        return _die(str(err), code=2)

    if args.no_dp_in_category:
        try:
            description = _validate_scalar(
                args.description, "description",
            )
        except ValueError as err:
            return _die(str(err), code=2)
        valid_implementations: List[str] = []
        status = "no_DP_in_category"
    else:
        try:
            description = _validate_scalar(
                args.description, "description",
            )
        except ValueError as err:
            return _die(str(err), code=2)
        try:
            parsed = json.loads(args.valid_implementations or "[]")
        except json.JSONDecodeError as err:
            return _die(
                "valid_implementations: not valid JSON ({0})".format(err),
                code=2,
            )
        if not isinstance(parsed, list) or not all(
            isinstance(v, str) for v in parsed
        ):
            return _die(
                "valid_implementations: must be a JSON array of strings",
                code=2,
            )
        valid_implementations = [v.strip() for v in parsed if v.strip()]
        if len(valid_implementations) < 2:
            return _die(
                "valid_implementations: ≥2 entries required (got {0})".format(
                    len(valid_implementations),
                ),
                code=2,
            )
        status = "pending"

    try:
        with _state_transaction(args.devforge_dir) as state:
            dp_id = _next_dp_id(state, category)
            state["decision_points"].append({
                "dp_id": dp_id,
                "category": category,
                "description": description,
                "valid_implementations": valid_implementations,
                "status": status,
                "user_answer": "",
                "default_applied": "",
                "deferral_reason": "",
                "turns": 0,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-decision-point: {0}".format(err))
    sys.stdout.write(dp_id + "\n")
    return 0


def cmd_set_dp_answer(args: argparse.Namespace) -> int:
    """Interactive path. Sets DP.status=answered + user_answer."""
    try:
        user_answer = _validate_scalar(args.user_answer, "user_answer")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            if state.get("mode") == "auto":
                return _die(
                    "set-dp-answer: mode=auto rejects user-answer setter "
                    "(use set-dp-default-applied)",
                    code=2,
                )
            dp = _find_dp(state, args.dp_id)
            if dp is None:
                return _die(
                    "set-dp-answer: dp_id {0!r} not found".format(args.dp_id),
                    code=2,
                )
            if dp.get("status") == "no_DP_in_category":
                return _die(
                    "set-dp-answer: {0} is no_DP_in_category (terminal)".format(
                        args.dp_id,
                    ),
                    code=2,
                )
            dp["status"] = "answered"
            dp["user_answer"] = user_answer
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-dp-answer: {0}".format(err))
    return 0


def cmd_set_dp_default_applied(args: argparse.Namespace) -> int:
    """Auto path. Sets DP.status=default_applied + default_applied."""
    try:
        default_applied = _validate_scalar(
            args.default_applied, "default_applied",
        )
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            if state.get("mode") == "interactive":
                return _die(
                    "set-dp-default-applied: mode=interactive rejects "
                    "default-applied setter (use set-dp-answer)",
                    code=2,
                )
            dp = _find_dp(state, args.dp_id)
            if dp is None:
                return _die(
                    "set-dp-default-applied: dp_id {0!r} not found".format(
                        args.dp_id,
                    ),
                    code=2,
                )
            if dp.get("status") == "no_DP_in_category":
                return _die(
                    "set-dp-default-applied: {0} is no_DP_in_category "
                    "(terminal)".format(args.dp_id),
                    code=2,
                )
            dp["status"] = "default_applied"
            dp["default_applied"] = default_applied
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-dp-default-applied: {0}".format(err))
    return 0


# Deferral-kind argument enum (subset of DP_STATUS_ENUM deferred-* values
# stripped to the kind suffix for CLI ergonomics).
DP_DEFERRAL_KIND_ENUM: Tuple[str, ...] = ("OOS", "open_question")
_DEFERRAL_KIND_TO_STATUS: Dict[str, str] = {
    "OOS": "deferred_OOS",
    "open_question": "deferred_open_question",
}
DP_TURN_CAP_REASON = "exceeded follow-up cap"


def cmd_set_dp_deferral(args: argparse.Namespace) -> int:
    """Defer a DP to OOS or open-question. Enforces per-DP turn cap.

    --increment-turn bumps the per-DP follow-up counter before deferral
    resolution. When turns >= DP_TURN_CAP after increment, helper forces
    status=deferred_open_question + deferral_reason=DP_TURN_CAP_REASON
    regardless of the supplied --deferral-kind (Variance rule #7 stop
    discipline + plan line 335-339).
    """
    try:
        kind = _validate_enum(
            args.deferral_kind, "deferral_kind", DP_DEFERRAL_KIND_ENUM,
        )
        reason = _validate_scalar(args.reason, "reason")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            dp = _find_dp(state, args.dp_id)
            if dp is None:
                return _die(
                    "set-dp-deferral: dp_id {0!r} not found".format(args.dp_id),
                    code=2,
                )
            if dp.get("status") == "no_DP_in_category":
                return _die(
                    "set-dp-deferral: {0} is no_DP_in_category "
                    "(terminal)".format(args.dp_id),
                    code=2,
                )
            if args.increment_turn:
                dp["turns"] = int(dp.get("turns", 0)) + 1
            if int(dp.get("turns", 0)) >= DP_TURN_CAP:
                dp["status"] = "deferred_open_question"
                dp["deferral_reason"] = DP_TURN_CAP_REASON
            else:
                dp["status"] = _DEFERRAL_KIND_TO_STATUS[kind]
                dp["deferral_reason"] = reason
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-dp-deferral: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Phase 2 — coverage + finalize.
# ---------------------------------------------------------------------------


_DP_CLEAR_STATUSES: Tuple[str, ...] = (
    "answered", "default_applied", "deferred_OOS", "deferred_open_question",
)


def _category_state(state: Dict[str, Any], category: str) -> str:
    """Compute per-category coverage state per plan §Phase 2 table.

    Precedence (verbatim from plan line 333-338):
      1. NoDPInCategory   — single no_DP_in_category DP recorded
      2. Clear            — ≥1 DP with status ∈ _DP_CLEAR_STATUSES
      3. Partial          — ≥1 DP pending AND no Clear yet
      4. Missing          — no DPs in this category
    """
    in_cat = [
        d for d in state["decision_points"]
        if d.get("category") == category
    ]
    if not in_cat:
        return "Missing"
    if any(d.get("status") == "no_DP_in_category" for d in in_cat):
        return "NoDPInCategory"
    if any(d.get("status") in _DP_CLEAR_STATUSES for d in in_cat):
        return "Clear"
    if any(d.get("status") == "pending" for d in in_cat):
        return "Partial"
    return "Missing"


def cmd_dp_coverage(args: argparse.Namespace) -> int:
    """Emit per-DP {dp_id: status} JSON map (debug aid)."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("dp-coverage: {0}".format(err))
    out = {
        d.get("dp_id"): d.get("status")
        for d in state["decision_points"]
    }
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def cmd_rubric_coverage(args: argparse.Namespace) -> int:
    """Emit per-category {category: state} JSON map. Deterministic order."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("rubric-coverage: {0}".format(err))
    out: Dict[str, str] = {}
    for cat in DP_CATEGORY_ENUM:
        out[cat] = _category_state(state, cat)
    # Preserve DP_CATEGORY_ENUM order (json.dump w/ sort_keys=False keeps
    # insertion order in CPython 3.7+).
    json.dump(out, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_verify_decision_coverage(args: argparse.Namespace) -> int:
    """Gate: every category state ∈ {Clear, NoDPInCategory}."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-decision-coverage: {0}".format(err))
    failing: List[Tuple[str, str]] = []
    for cat in DP_CATEGORY_ENUM:
        st = _category_state(state, cat)
        if st not in ("Clear", "NoDPInCategory"):
            failing.append((cat, st))
    if failing:
        sys.stderr.write(
            "verify-decision-coverage: categories not covered:\n"
        )
        for cat, st in failing:
            sys.stderr.write("  - {0}: {1}\n".format(cat, st))
        return 2
    return 0


def cmd_rubric_finalize(args: argparse.Namespace) -> int:
    """Same gate as verify-decision-coverage (plan line 333)."""
    return cmd_verify_decision_coverage(args)


def cmd_dp_finalize(args: argparse.Namespace) -> int:
    """Gate Phase 2 → Phase 3. Re-runs decision-coverage + stamps."""
    rc = cmd_verify_decision_coverage(args)
    if rc != 0:
        return rc
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["dp_finalized"] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("dp-finalize: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Phase 3 — spec-type classification + per-type mandatory reads.
# ---------------------------------------------------------------------------

# Mandatory-read slot table (SPECIFY-REDESIGN-PLAN §Phase 3 Step 2,
# line 412-418). Each entry is (slot_pattern, description). slot_pattern
# is matched against orchestrator-supplied --read-path via fnmatch so the
# orchestrator owns enumeration; helper just confirms every slot has at
# least one read_path (or n_a_reason) covering it.
MANDATORY_READS_BY_TYPE: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "migration_tooling": (
        ("package.json", "Root package.json"),
        (".github/workflows/*", "Every .github/workflows/ file"),
        ("**/package.json",
         "Per-package package.json with peer/deps/workspace links"),
        (".husky/*", "Husky hook configs (.husky/)"),
        (".pre-commit-config.yaml", "pre-commit config"),
        (".lefthook.yml", "lefthook config"),
        ("lerna.json", "lerna monorepo config"),
        ("turbo.json", "turbo monorepo config"),
        ("nx.json", "nx monorepo config"),
        ("pnpm-workspace.yaml", "pnpm workspace config"),
        ("rush.json", "rush monorepo config"),
        ("*lock*", "Lockfiles (note presence/size only)"),
        (".npmrc", "Root .npmrc"),
        (".yarnrc", "Root .yarnrc"),
        (".pnpmrc", "Root .pnpmrc"),
    ),
    "feature_addition": (
        ("__entry__", "Root component/entry files (router, store, app init)"),
        ("__similar_feature__",
         "Most-similar existing feature (via grep)"),
        ("__type_defs__", "Type defs for affected entities"),
        ("__api_ops__", "API/GraphQL ops for affected resources"),
        ("__test_files__", "Test files for affected area"),
    ),
    "bug_fix": (
        ("__buggy_files__", "The buggy file(s) named in request"),
        ("__direct_deps__", "Direct deps of buggy file"),
        ("__direct_callers__", "Direct callers (via grep)"),
        ("__recent_git_log__", "Recent git log on buggy file (git log -5)"),
    ),
    "refactor": (
        ("__refactored_files__", "The file(s) being refactored"),
        ("__all_callers__", "All callers (via grep)"),
        ("__all_tests__", "All tests for refactored code"),
    ),
    "greenfield_feature": (
        ("constitution.md#scaffolding-guide",
         "Constitution Section 7 (Scaffolding Guide)"),
        ("__framework_docs__",
         "Framework docs via WebSearch for feature pattern"),
        (".claude/memory/MEMORY.md",
         "MEMORY.md prior-feature lessons"),
        ("discover/*.md",
         "/discover reference md (if Phase 1 adapter loaded one)"),
    ),
}


def _slot_matches_path(slot_pattern: str, read_path: str) -> bool:
    """Return True iff `read_path` satisfies `slot_pattern`.

    Match strategy:
      - Sentinel slots (surrounded by `__`) require explicit --slot-pattern
        on record-mandatory-read; never auto-match by read-path.
      - Concrete patterns use fnmatch-style globbing
        (`Path.match` semantics) plus a substring fallback so
        `**/package.json` matches `services/api/package.json`.
    """
    if slot_pattern.startswith("__") and slot_pattern.endswith("__"):
        return False
    try:
        if Path(read_path).match(slot_pattern):
            return True
    except (ValueError, TypeError):
        pass
    # Substring fallback for path-suffix matches like `.github/workflows/*`.
    base = slot_pattern.rstrip("*").rstrip("/")
    if base and base in read_path:
        return True
    return False


def cmd_classify_spec_type(args: argparse.Namespace) -> int:
    """Set spec_type + rationale. Helper does NOT auto-derive the type."""
    try:
        spec_type = _validate_enum(
            args.spec_type, "spec_type", SPEC_TYPE_ENUM,
        )
        rationale = _validate_scalar(args.rationale, "rationale")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["spec_type"] = spec_type
            state["spec_type_rationale"] = rationale
            state["spec_type_seeded_by_upstream"] = bool(
                args.seeded_by_upstream
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("classify-spec-type: {0}".format(err))
    return 0


def cmd_record_mandatory_read(args: argparse.Namespace) -> int:
    """Record a Phase 3 per-spec-type mandatory-read entry.

    Two CLI shapes (mutually exclusive):

      --read-path PATH                      (actual file read)
      --slot-pattern PATTERN --n-a-reason TEXT   (mark slot N/A)

    spec_type pulled from state (must be set via classify-spec-type
    first). Helper only records — coverage gating is verify-mandatory-reads.
    """
    has_read = bool(args.read_path)
    has_na = bool(args.n_a_reason)
    if has_read and has_na:
        return _die(
            "record-mandatory-read: --read-path and --n-a-reason are "
            "mutually exclusive",
            code=2,
        )
    if not has_read and not has_na:
        return _die(
            "record-mandatory-read: one of --read-path / --n-a-reason "
            "required",
            code=2,
        )
    try:
        with _state_transaction(args.devforge_dir) as state:
            spec_type = state.get("spec_type")
            if not spec_type:
                return _die(
                    "record-mandatory-read: spec_type unset "
                    "(call classify-spec-type first)",
                    code=2,
                )
            entry: Dict[str, Any] = {
                "spec_type": spec_type,
                "read_path": "",
                "slot_pattern": "",
                "n_a_reason": "",
            }
            if has_read:
                entry["read_path"] = args.read_path.strip()
                entry["slot_pattern"] = (args.slot_pattern or "").strip()
            else:
                if not args.slot_pattern:
                    return _die(
                        "record-mandatory-read: --n-a-reason requires "
                        "--slot-pattern",
                        code=2,
                    )
                entry["slot_pattern"] = args.slot_pattern.strip()
                entry["n_a_reason"] = args.n_a_reason.strip()
            state["mandatory_reads"].append(entry)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-mandatory-read: {0}".format(err))
    return 0


def _slot_covered(
    state: Dict[str, Any], slot_pattern: str,
) -> bool:
    for e in state["mandatory_reads"]:
        if e.get("n_a_reason") and e.get("slot_pattern") == slot_pattern:
            return True
        rp = e.get("read_path", "")
        if not rp:
            continue
        if e.get("slot_pattern") == slot_pattern:
            return True
        if _slot_matches_path(slot_pattern, rp):
            return True
    return False


def cmd_verify_mandatory_reads(args: argparse.Namespace) -> int:
    """Walk MANDATORY_READS_BY_TYPE[spec_type]; every slot must be covered."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-mandatory-reads: {0}".format(err))
    spec_type = state.get("spec_type")
    if not spec_type:
        return _die(
            "verify-mandatory-reads: spec_type unset "
            "(call classify-spec-type first)",
            code=2,
        )
    if spec_type not in MANDATORY_READS_BY_TYPE:
        return _die(
            "verify-mandatory-reads: no mandatory-read table for "
            "spec_type {0!r}".format(spec_type),
            code=2,
        )
    missing: List[Tuple[str, str]] = []
    for slot_pattern, description in MANDATORY_READS_BY_TYPE[spec_type]:
        if not _slot_covered(state, slot_pattern):
            missing.append((slot_pattern, description))
    if missing:
        sys.stderr.write(
            "verify-mandatory-reads: missing slots for spec_type "
            "{0!r}:\n".format(spec_type)
        )
        for slot, desc in missing:
            sys.stderr.write("  - {0} — {1}\n".format(slot, desc))
        return 2
    return 0


def cmd_phase3_finalize(args: argparse.Namespace) -> int:
    """Gate Phase 3 → Phase 4. Re-runs verify-mandatory-reads + stamps."""
    rc = cmd_verify_mandatory_reads(args)
    if rc != 0:
        return rc
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["phase3_finalized"] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("phase3-finalize: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Cross-phase — summary dashboard.
# ---------------------------------------------------------------------------


def cmd_summary(args: argparse.Namespace) -> int:
    """Emit phase-progress + counts dashboard JSON."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("summary: {0}".format(err))

    dp_status_counts: Dict[str, int] = {s: 0 for s in DP_STATUS_ENUM}
    for d in state["decision_points"]:
        st = d.get("status")
        if st in dp_status_counts:
            dp_status_counts[st] += 1

    rubric: Dict[str, str] = {
        cat: _category_state(state, cat) for cat in DP_CATEGORY_ENUM
    }

    out = {
        "topic": state.get("topic"),
        "spec_type": state.get("spec_type"),
        "spec_type_seeded_by_upstream": state.get(
            "spec_type_seeded_by_upstream", False,
        ),
        "status": state.get("status"),
        "mode": state.get("mode"),
        "phase_finalized": {
            "phase1": bool(state.get("phase1_finalized")),
            "findings": bool(state.get("findings_finalized")),
            "dp": bool(state.get("dp_finalized")),
            "phase3": bool(state.get("phase3_finalized")),
        },
        "counts": {
            "input_reads": len(state.get("input_reads", [])),
            "findings": len(state.get("findings", [])),
            "decision_points": len(state.get("decision_points", [])),
            "decision_points_by_status": dp_status_counts,
            "mandatory_reads": len(state.get("mandatory_reads", [])),
            "discretionary_reads": len(state.get("discretionary_reads", [])),
            "affected_areas": len(state.get("affected_areas", [])),
            "acceptance_criteria": len(state.get("acceptance_criteria", [])),
            "out_of_scope": len(state.get("out_of_scope", [])),
            "constraints": len(state.get("constraints", [])),
            "open_questions": len(state.get("open_questions", [])),
            "risks": len(state.get("risks", [])),
            "conflicts": len(state.get("conflicts", [])),
        },
        "rubric_coverage": rubric,
    }
    json.dump(out, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 4 — header / branch setters.
# ---------------------------------------------------------------------------


def _existing_spec_numbers(specs_root: Path) -> List[int]:
    """Return all NNN prefixes already used under specs_root."""
    if not specs_root.exists() or not specs_root.is_dir():
        return []
    out: List[int] = []
    for entry in specs_root.iterdir():
        if not entry.is_dir():
            continue
        m = SPEC_NUMBER_DIR_RE.match(entry.name)
        if m:
            out.append(int(m.group(1)))
    return out


def cmd_assign_spec_number(args: argparse.Namespace) -> int:
    """Scan specs/ for highest NNN-* dir, persist + emit next zero-padded."""
    specs_root = Path(args.specs_root or SPECS_ROOT_DEFAULT)
    nums = _existing_spec_numbers(specs_root)
    nxt = (max(nums) + 1) if nums else 1
    formatted = "{0:0{w}d}".format(nxt, w=SPEC_NUMBER_WIDTH)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["spec_number"] = formatted
    except (OSError, json.JSONDecodeError) as err:
        return _die("assign-spec-number: {0}".format(err))
    sys.stdout.write(formatted + "\n")
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

    On default branch + spec_number + feature_slug present, emit
    `git checkout -b spec/NNN-<slug>` to stdout + persist
    branch_decision="create" + branch_created=true. (Orchestrator runs
    the actual git op — helper stays read-only on git.)

    On non-default branch, persist branch_decision="keep" + branch_created
    false; emit informational stdout comment.
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
            if current != default:
                state["branch_decision"] = "keep"
                state["branch_created"] = False
                sys.stdout.write(
                    "# already on non-default branch {0!r}; "
                    "no checkout emitted\n".format(current)
                )
                return 0
            number = state.get("spec_number")
            slug = state.get("feature_slug")
            if not number or not slug:
                return _die(
                    "create-branch: spec_number + feature_slug required "
                    "before checkout (run assign-spec-number + "
                    "assign-feature-name first)",
                    code=2,
                )
            branch = "spec/{0}-{1}".format(number, slug)
            state["branch_decision"] = "create"
            state["branch_created"] = True
            sys.stdout.write("git checkout -b {0}\n".format(branch))
    except (OSError, json.JSONDecodeError) as err:
        return _die("create-branch: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Phase 4 — section setters (overview / current-state / desired-behavior /
# affected-areas / oos / constraints / open-questions / risks).
# ---------------------------------------------------------------------------


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
    """Append a §6 OOS entry {content, finding_ref}."""
    try:
        content = _validate_scalar(args.content, "content")
    except ValueError as err:
        return _die(str(err), code=2)
    finding_ref = (args.finding_ref or "").strip()
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["out_of_scope"].append({
                "content": content,
                "finding_ref": finding_ref,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-out-of-scope: {0}".format(err))
    return 0


def cmd_record_constraint(args: argparse.Namespace) -> int:
    """Append a §7 Constraint entry {kind, content}."""
    try:
        kind = _validate_enum(args.kind, "kind", CONSTRAINT_KIND_ENUM)
        content = _validate_scalar(args.content, "content")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["constraints"].append({
                "kind": kind,
                "content": content,
            })
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
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["risks"].append({
                "risk": risk,
                "likelihood": likelihood,
                "impact": impact,
                "mitigation": mitigation,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-risk: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Phase 4 — add-ac (full AC schema with EARS regex + subsection constraints).
# ---------------------------------------------------------------------------


def _next_ac_id(state: Dict[str, Any]) -> str:
    n = 1 + len(state["acceptance_criteria"])
    return "AC-{0}".format(n)


def cmd_add_ac(args: argparse.Namespace) -> int:
    """Add an Acceptance Criterion (or mark whole subsection N/A).

    Two CLI shapes (mutually exclusive):

      --subsection X --mark-na --n-a-reason "reason"
          Records a whole-subsection N/A marker in ac_subsection_na.

      --subsection X --ears-variant Y --statement Z
          [--verification-command W] [--test-anchor T]
          Records a populated AC. Subsection-EARS constraint
          (Variance rule #10) enforced inside: §5.1 + §5.7 demand
          ears_variant=ubiquitous AND non-empty verification_command.
          Helper rejects on miss. Statement matched against
          EARS_REGEX[ears_variant]; reject on miss.
    """
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
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-ac: {0}".format(err))
    sys.stdout.write(ac_id + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 4 — verify subcommands.
# ---------------------------------------------------------------------------


def cmd_verify_coverage(args: argparse.Namespace) -> int:
    """Variance rule #5: every finding landed in AC/Constraint/OOS/Risk."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-coverage: {0}".format(err))
    unlanded = [
        f for f in state["findings"]
        if f.get("landed_in", "unlanded") == "unlanded"
    ]
    if unlanded:
        sys.stderr.write(
            "verify-coverage: unlanded findings (Variance rule #5):\n"
        )
        for f in unlanded:
            sys.stderr.write(
                "  - {0} (from {1}): {2}\n".format(
                    f.get("finding_id"),
                    f.get("source_path"),
                    (f.get("content", "") or "")[:80],
                )
            )
        return 2
    return 0


def cmd_verify_ac_subsection_coverage(args: argparse.Namespace) -> int:
    """Every of 7 subsections has ≥1 AC OR a non-empty N/A reason."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-ac-subsection-coverage: {0}".format(err))
    populated = {
        ac.get("subsection")
        for ac in state["acceptance_criteria"]
        if ac.get("subsection")
    }
    na = {
        sub for sub, reason in state["ac_subsection_na"].items()
        if (reason or "").strip()
    }
    missing = [
        sub for sub in AC_SUBSECTION_ENUM
        if sub not in populated and sub not in na
    ]
    if missing:
        sys.stderr.write(
            "verify-ac-subsection-coverage: subsections without AC or "
            "N/A marker:\n"
        )
        for sub in missing:
            sys.stderr.write("  - {0}\n".format(sub))
        return 2
    return 0


def cmd_verify_ac_shape(args: argparse.Namespace) -> int:
    """Variance rule #10: every AC.statement matches its EARS regex."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-ac-shape: {0}".format(err))
    bad: List[Tuple[str, str, str, str]] = []
    for ac in state["acceptance_criteria"]:
        variant = ac.get("ears_variant", "")
        statement = ac.get("statement", "")
        if variant not in EARS_REGEX:
            bad.append(
                (ac.get("ac_id", "?"), variant, statement,
                 "unknown EARS variant")
            )
            continue
        if not EARS_REGEX[variant].match(statement):
            bad.append(
                (ac.get("ac_id", "?"), variant, statement,
                 "regex mismatch")
            )
    if bad:
        sys.stderr.write(
            "verify-ac-shape: AC statements failing EARS regex:\n"
        )
        for ac_id, variant, statement, why in bad:
            sys.stderr.write(
                "  - {0} ({1}): {2} [{3}]\n".format(
                    ac_id, variant, statement[:80], why,
                )
            )
        return 2
    return 0


def cmd_verify_numerical_consistency(args: argparse.Namespace) -> int:
    """Variance rule #6: digit-prefixed nouns consistent across spec.

    Renders the spec, scans non-heading + non-table-sep lines for
    `<digit>+ <noun>` pairs, groups by lowercased noun, flags any noun
    appearing ≥2 times with distinct numeric values. Conservative seed
    — false positives on multi-occurrence singletons silenced by the
    ≥2-occurrence rule.
    """
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-numerical-consistency: {0}".format(err))
    rendered = render_spec(state)
    groups: Dict[str, Dict[str, List[int]]] = {}
    for lineno, line in enumerate(rendered.splitlines(), 1):
        if NUMERIC_HEADING_RE.match(line):
            continue
        if NUMERIC_TABLE_SEP_RE.match(line):
            continue
        for m in NUMERIC_DIGIT_NOUN_RE.finditer(line):
            num, noun = m.group(1), m.group(2).lower()
            groups.setdefault(noun, {}).setdefault(num, []).append(lineno)
    inconsistencies: List[Tuple[str, Dict[str, List[int]]]] = []
    for noun, value_map in groups.items():
        if len(value_map) >= 2:
            inconsistencies.append((noun, value_map))
    if inconsistencies:
        sys.stderr.write(
            "verify-numerical-consistency: inconsistent digit counts "
            "across rendered sections (Variance rule #6):\n"
        )
        for noun, value_map in sorted(inconsistencies):
            occurrences = ", ".join(
                "{0} (lines {1})".format(v, ",".join(str(L) for L in ls))
                for v, ls in sorted(value_map.items())
            )
            sys.stderr.write(
                "  - {0}: {1}\n".format(noun, occurrences)
            )
        return 2
    return 0


def _constitution_keywords(rule_text: str) -> set:
    """Tokenize a constitution rule, drop stopwords + short tokens."""
    tokens = re.findall(r"[a-zA-Z]{4,}", rule_text.lower())
    return {t for t in tokens if t not in CONSTITUTION_STOPWORDS}


def _body_tokens(body: str) -> set:
    return set(re.findall(r"[a-zA-Z]{4,}", (body or "").lower()))


def cmd_check_constitution_compliance(args: argparse.Namespace) -> int:
    """Token-overlap scan of constitution MUST/SHALL lines vs AC/Constraint/OOS.

    Non-blocking — exit 0 always. Surfaces overlap warnings on stderr so
    user can review before approval. Per SPECIFY-REDESIGN-PLAN Open
    Question #10, re-runs at every render (no `record-constitution-override`
    suppression — zero-escape-hatch default).
    """
    cpath = Path(args.constitution_path or "constitution.md")
    if not cpath.exists():
        sys.stderr.write(
            "check-constitution-compliance: constitution at {0!r} not "
            "found; skipping (non-blocking).\n".format(str(cpath))
        )
        return 0
    try:
        text = cpath.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "check-constitution-compliance: read failed on {0}: {1} "
            "(non-blocking)\n".format(cpath, err)
        )
        return 0
    rules: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if CONSTITUTION_RULE_RE.search(stripped):
            rules.append(stripped)
    if not rules:
        return 0
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "check-constitution-compliance: state read failed: "
            "{0} (non-blocking)\n".format(err)
        )
        return 0
    targets: List[Tuple[str, str]] = []
    for ac in state["acceptance_criteria"]:
        targets.append((
            "AC {0}".format(ac.get("ac_id", "")),
            ac.get("statement", ""),
        ))
    for c in state["constraints"]:
        targets.append((
            "Constraint ({0})".format(c.get("kind", "")),
            c.get("content", ""),
        ))
    for o in state["out_of_scope"]:
        targets.append(("OOS", o.get("content", "")))
    warnings: List[Tuple[str, str, str, List[str]]] = []
    for rule in rules:
        kws = _constitution_keywords(rule)
        if not kws:
            continue
        for tag, body in targets:
            overlap = kws & _body_tokens(body)
            if overlap:
                warnings.append((rule, tag, body, sorted(overlap)))
    if warnings:
        sys.stderr.write(
            "check-constitution-compliance: review constitution "
            "mandates overlapping with spec entries (non-blocking):\n"
        )
        for rule, tag, body, overlap in warnings:
            sys.stderr.write(
                "  - rule: {0}\n    {1}: {2}\n    overlap: {3}\n".format(
                    rule[:120], tag, (body or "")[:120], ", ".join(overlap),
                )
            )
    return 0


# ---------------------------------------------------------------------------
# Phase 4 — render.
# ---------------------------------------------------------------------------


def _render_section_acs(
    state: Dict[str, Any], subsection: str,
) -> List[str]:
    lines: List[str] = []
    acs = [
        a for a in state["acceptance_criteria"]
        if a.get("subsection") == subsection
    ]
    if acs:
        for a in acs:
            lines.append("- [ ] **{0}**: {1}".format(
                a.get("ac_id", ""), a.get("statement", ""),
            ))
            if a.get("verification_command"):
                lines.append(
                    "  > Verification: {0}".format(
                        a["verification_command"]
                    )
                )
            if a.get("test_anchor"):
                lines.append(
                    "  > Test: {0}".format(a["test_anchor"])
                )
    else:
        reason = state["ac_subsection_na"].get(subsection, "")
        if reason:
            lines.append("N/A — {0}".format(reason))
        else:
            lines.append("_(no AC recorded)_")
    return lines


def _render_open_questions_section(state: Dict[str, Any]) -> List[str]:
    """Compose §8 — explicit open questions + DP-derived entries.

    Resolutions overlay via strikethrough + audit suffix. Walk order is
    deterministic (insertion order across both source lists).
    """
    resolutions_by_id: Dict[str, Dict[str, Any]] = {
        r["question_id"]: r
        for r in state.get("open_question_resolutions", [])
    }
    lines: List[str] = ["## 8. Open Questions", ""]
    has_entry = False

    for oq in state["open_questions"]:
        has_entry = True
        qid = oq.get("question_id", "")
        body = "**{0}**: {1}".format(qid, oq.get("content", ""))
        no_dp = (oq.get("category_no_dp_reason") or "").strip()
        if no_dp:
            body = body + " _(no-DP rationale: {0})_".format(no_dp)
        if qid in resolutions_by_id:
            r = resolutions_by_id[qid]
            lines.append(
                "- ~~{0}~~ — resolved in {1} on {2}: {3}".format(
                    body,
                    r.get("resolution_phase", ""),
                    r.get("resolution_timestamp", ""),
                    r.get("resolution_text", ""),
                )
            )
        else:
            lines.append("- " + body)

    for dp in state["decision_points"]:
        status = dp.get("status")
        if status == "default_applied":
            has_entry = True
            lines.append(
                "- **{0}** [default applied]: {1} → default: {2}".format(
                    dp.get("dp_id", ""),
                    dp.get("description", ""),
                    dp.get("default_applied", ""),
                )
            )
        elif status == "deferred_open_question":
            has_entry = True
            lines.append(
                "- **{0}** [deferred to open question]: {1} ({2})".format(
                    dp.get("dp_id", ""),
                    dp.get("description", ""),
                    dp.get("deferral_reason", ""),
                )
            )
        elif status == "no_DP_in_category":
            has_entry = True
            lines.append(
                "- **{0}** [no DP in category {1}]: {2}".format(
                    dp.get("dp_id", ""),
                    dp.get("category", ""),
                    dp.get("description", ""),
                )
            )

    if not has_entry:
        lines.append("_(no open questions recorded)_")
    lines.append("")
    return lines


def render_spec(state: Dict[str, Any]) -> str:
    """Compose the 9-section spec markdown.

    Determinism: byte-identical input state → byte-identical output. No
    timestamps, no environment-dependent values. Subsections walked in
    AC_SUBSECTION_ENUM order; constraints walked in CONSTRAINT_KIND_ENUM
    order; affected_areas / out_of_scope / risks / open_questions /
    findings / decision_points walked in insertion order.
    """
    out: List[str] = []
    name = state.get("feature_name") or "Feature"
    date = state.get("date") or ""
    status = state.get("status") or SPEC_STATUS_DEFAULT

    out.append("# Spec: {0}".format(name))
    out.append("")
    out.append("**Date**: {0}".format(date))
    out.append("**Status**: {0}".format(status))
    out.append("**Author**: Claude + User")
    out.append("")

    out.append("## 1. Overview")
    out.append("")
    out.append(state.get("overview") or "_(no overview recorded)_")
    out.append("")

    out.append("## 2. Current State")
    out.append("")
    out.append(state.get("current_state") or "_(no current state recorded)_")
    out.append("")

    out.append("## 3. Desired Behavior")
    out.append("")
    out.append(
        state.get("desired_behavior") or "_(no desired behavior recorded)_"
    )
    out.append("")

    out.append("## 4. Affected Areas")
    out.append("")
    out.append("| Area | Files | Impact |")
    out.append("|------|-------|--------|")
    if state["affected_areas"]:
        for a in state["affected_areas"]:
            out.append("| {0} | {1} | {2} |".format(
                a.get("area", ""),
                ", ".join(a.get("files", [])),
                a.get("impact", ""),
            ))
    else:
        out.append("| _(none)_ | _(none)_ | _(none)_ |")
    out.append("")

    out.append("## 5. Acceptance Criteria")
    out.append("")
    out.append(AC_FRAMING_LINE)
    out.append("")
    for subsection in AC_SUBSECTION_ENUM:
        heading_num, heading_text = SUBSECTION_HEADING_BY_KEY[subsection]
        out.append("### {0} {1}".format(heading_num, heading_text))
        out.append("")
        out.extend(_render_section_acs(state, subsection))
        out.append("")

    out.append("## 6. Out of Scope")
    out.append("")
    out.append(COVERAGE_RULE_BANNER)
    out.append("")
    if state["out_of_scope"]:
        for o in state["out_of_scope"]:
            ref = (o.get("finding_ref") or "").strip()
            suffix = " — {0}".format(ref) if ref else ""
            out.append("- NOT included: {0}{1}".format(
                o.get("content", ""), suffix,
            ))
    else:
        out.append("- NOT included: _(none recorded)_")
    out.append("")

    out.append("## 7. Technical Constraints")
    out.append("")
    has_constraint = False
    for kind in CONSTRAINT_KIND_ENUM:
        for c in state["constraints"]:
            if c.get("kind") == kind:
                has_constraint = True
                out.append("- {0}: {1}".format(
                    CONSTRAINT_KIND_LABEL[kind], c.get("content", ""),
                ))
    if not has_constraint:
        out.append("- _(no constraints recorded)_")
    out.append("")

    out.extend(_render_open_questions_section(state))

    out.append("## 9. Risks")
    out.append("")
    out.append("| Risk | Likelihood | Impact | Mitigation |")
    out.append("|------|-----------|--------|------------|")
    if state["risks"]:
        for r in state["risks"]:
            out.append("| {0} | {1} | {2} | {3} |".format(
                r.get("risk", ""),
                r.get("likelihood", ""),
                r.get("impact", ""),
                r.get("mitigation", ""),
            ))
    else:
        out.append("| _(none)_ | _(none)_ | _(none)_ | _(none)_ |")
    out.append("")

    return "\n".join(out).rstrip() + "\n"


def cmd_render(args: argparse.Namespace) -> int:
    """Emit spec markdown to stdout. Pure read — no state mutation."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render: {0}".format(err))
    sys.stdout.write(render_spec(state))
    return 0


# ---------------------------------------------------------------------------
# Phase 5 — approval + /plan handoff.
# ---------------------------------------------------------------------------


def _approval_summary(state: Dict[str, Any]) -> str:
    """Compose v3 4-bullet summary (Variance rule #9, verbatim shape)."""
    number = state.get("spec_number") or "NNN"
    name = state.get("feature_name") or "feature"
    overview = (state.get("overview") or "_(no overview)_").strip()
    if len(overview) > 240:
        overview = overview[:237] + "..."
    file_count = sum(
        len(a.get("files", [])) for a in state["affected_areas"]
    )
    area_count = len(state["affected_areas"])
    ac_count = len(state["acceptance_criteria"])
    subsection_set = {
        a.get("subsection") for a in state["acceptance_criteria"]
        if a.get("subsection")
    }
    subsection_count = len(subsection_set)
    if state["out_of_scope"]:
        oos_short = "; ".join(
            (o.get("content", "") or "").strip()[:80]
            for o in state["out_of_scope"][:3]
        )
        if len(state["out_of_scope"]) > 3:
            oos_short += "; …"
    else:
        oos_short = "_(none)_"
    return (
        "I've created the specification at "
        "`specs/{n}-{f}/spec.md`. Key points:\n"
        "- **What changes**: {ov}\n"
        "- **Files affected**: {fc} files across {ac} areas\n"
        "- **Acceptance criteria**: {acc} testable criteria across "
        "{sc} AC categories\n"
        "- **Out of scope**: {oos}\n"
        "\n"
        "Please review and either approve or request changes. Once "
        "approved, run `/plan` to create the technical implementation "
        "plan."
    ).format(
        n=number, f=name, ov=overview, fc=file_count, ac=area_count,
        acc=ac_count, sc=subsection_count, oos=oos_short,
    )


def cmd_render_summary(args: argparse.Namespace) -> int:
    """Emit 4-bullet approval summary; persist to state.approval_summary."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-summary: {0}".format(err))
    summary = _approval_summary(state)
    try:
        with _state_transaction(args.devforge_dir) as state2:
            state2["approval_summary"] = summary
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-summary: {0}".format(err))
    sys.stdout.write(summary + "\n")
    return 0


def cmd_set_status(args: argparse.Namespace) -> int:
    """Set spec status; closed enum SPEC_STATUS_ENUM."""
    try:
        status = _validate_enum(args.status, "status", SPEC_STATUS_ENUM)
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["status"] = status
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-status: {0}".format(err))
    return 0


_SUBSECTION_RENDER_ORDER: Tuple[str, ...] = (
    "5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7",
)


def _plan_handoff_block(state: Dict[str, Any]) -> str:
    number = state.get("spec_number") or "NNN"
    name = state.get("feature_name") or "feature"
    spec_type = state.get("spec_type") or "<unset>"
    status = state.get("status") or "Draft"
    acs = state["acceptance_criteria"]
    ac_count = len(acs)
    sub_counts: Dict[str, int] = {sub: 0 for sub in AC_SUBSECTION_ENUM}
    for ac in acs:
        s = ac.get("subsection")
        if s in sub_counts:
            sub_counts[s] += 1
    sub_active = sum(1 for v in sub_counts.values() if v > 0)
    sub_count_strs = ", ".join(
        "{0}: {1}".format(label, sub_counts[sub])
        for sub, label in zip(
            AC_SUBSECTION_ENUM, _SUBSECTION_RENDER_ORDER,
        )
    )
    dp_by_status: Dict[str, int] = {s: 0 for s in DP_STATUS_ENUM}
    for d in state["decision_points"]:
        st = d.get("status")
        if st in dp_by_status:
            dp_by_status[st] += 1
    aff_count = len(state["affected_areas"])
    packages: List[str] = []
    seen: set = set()
    for a in state["affected_areas"]:
        for f in a.get("files", []):
            parts = (f or "").split("/")
            if len(parts) >= 2:
                pkg = parts[0]
                if pkg and pkg not in seen:
                    seen.add(pkg)
                    packages.append(pkg)
    pkg_list = ", ".join(packages) if packages else "(none)"
    return (
        "## Manual next step — run /plan\n"
        "\n"
        "No automated handoff. Restart Claude Code (exit and relaunch the "
        "CLI/app so the newly installed command is picked up), then run "
        "the command below in this repo. The spec path is explicit so "
        "/plan does not need most-recent-spec discovery:\n"
        "\n"
        "~~~\n"
        "/plan specs/{n}-{f}/spec.md\n"
        "~~~\n"
        "\n"
        "Minimum handoff data:\n"
        "- Spec status: {status}\n"
        "- Spec type: {st}\n"
        "- AC count: {acc} across {sca} subsections ({sub_counts})\n"
        "- Decision-point coverage: {ans} answered, {da} default-applied, "
        "{do} deferred-OOS, {dq} deferred-open-question\n"
        "- Affected areas: {aa} across {pk}\n"
        "- Out-of-scope items: {oos}\n"
        "- Open questions: {oq}\n"
        "- Constraints: {cn}\n"
        "- Risks: {rk}\n"
        "- Phase 1.5 finding coverage: 100% (all findings landed)\n"
        "\n"
        "Reference: specs/{n}-{f}/spec.md"
    ).format(
        n=number, f=name, status=status, st=spec_type,
        acc=ac_count, sca=sub_active, sub_counts=sub_count_strs,
        ans=dp_by_status["answered"],
        da=dp_by_status["default_applied"],
        do=dp_by_status["deferred_OOS"],
        dq=dp_by_status["deferred_open_question"],
        aa=aff_count, pk=pkg_list,
        oos=len(state["out_of_scope"]),
        oq=len(state["open_questions"]),
        cn=len(state["constraints"]),
        rk=len(state["risks"]),
    )


def cmd_render_plan_handoff(args: argparse.Namespace) -> int:
    """Emit deterministic /plan handoff block; persist to state."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-plan-handoff: {0}".format(err))
    block = _plan_handoff_block(state)
    try:
        with _state_transaction(args.devforge_dir) as state2:
            state2["plan_handoff_block"] = block
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-plan-handoff: {0}".format(err))
    sys.stdout.write(block + "\n")
    return 0


# ---------------------------------------------------------------------------
# Downstream — resolve-open-question (callable by /plan + /breakdown).
# ---------------------------------------------------------------------------


def cmd_resolve_open_question(args: argparse.Namespace) -> int:
    """Record a resolution for an §8 Open Question. Append-only audit log."""
    try:
        qid = _validate_scalar(args.question_id, "question_id")
        text = _validate_scalar(args.resolution_text, "resolution_text")
        phase = _validate_enum(
            args.resolution_phase, "resolution_phase",
            RESOLUTION_PHASE_ENUM,
        )
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["open_question_resolutions"].append({
                "question_id": qid,
                "resolution_text": text,
                "resolution_phase": phase,
                "resolution_timestamp": _utc_timestamp(),
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("resolve-open-question: {0}".format(err))
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

    # ----- Phase 2 ---------------------------------------------------------

    sp = sub.add_parser(
        "detect-mode",
        help="Resolve auto vs interactive mode from C-strict signals.",
    )
    sp.add_argument(
        "--auto", action="store_true", default=False,
        help="Force auto mode (one of three C-strict signals).",
    )
    sp.add_argument(
        "--reminder-text", default="", dest="reminder_text",
        help="Text of latest <system-reminder> block (orchestrator-supplied).",
    )
    sp.set_defaults(func=cmd_detect_mode)

    sp = sub.add_parser(
        "record-decision-point",
        help="Record a Phase 2 DecisionPoint (≥2 valid_implementations).",
    )
    sp.add_argument("--category", required=True)
    sp.add_argument("--description", required=True)
    sp.add_argument(
        "--valid-implementations", default="[]",
        dest="valid_implementations",
        help="JSON array of strings; ≥2 entries required.",
    )
    sp.add_argument(
        "--no-dp-in-category", action="store_true", default=False,
        dest="no_dp_in_category",
        help="Record terminal NoDPInCategory marker (skips ≥2-impl rule).",
    )
    sp.set_defaults(func=cmd_record_decision_point)

    sp = sub.add_parser(
        "set-dp-answer",
        help="Interactive path: mark DP answered with user_answer.",
    )
    sp.add_argument("--dp-id", required=True, dest="dp_id")
    sp.add_argument("--user-answer", required=True, dest="user_answer")
    sp.set_defaults(func=cmd_set_dp_answer)

    sp = sub.add_parser(
        "set-dp-default-applied",
        help="Auto path: mark DP default_applied with named default.",
    )
    sp.add_argument("--dp-id", required=True, dest="dp_id")
    sp.add_argument(
        "--default-applied", required=True, dest="default_applied",
    )
    sp.set_defaults(func=cmd_set_dp_default_applied)

    sp = sub.add_parser(
        "set-dp-deferral",
        help="Defer DP to OOS or open-question (auto-fires turn cap).",
    )
    sp.add_argument("--dp-id", required=True, dest="dp_id")
    sp.add_argument(
        "--deferral-kind", required=True, dest="deferral_kind",
        choices=list(DP_DEFERRAL_KIND_ENUM),
    )
    sp.add_argument("--reason", required=True)
    sp.add_argument(
        "--increment-turn", action="store_true", default=False,
        dest="increment_turn",
        help="Bump per-DP follow-up counter; turn cap may force open-question.",
    )
    sp.set_defaults(func=cmd_set_dp_deferral)

    sp = sub.add_parser(
        "dp-coverage", help="Emit per-DP {dp_id: status} JSON.",
    )
    sp.set_defaults(func=cmd_dp_coverage)

    sp = sub.add_parser(
        "rubric-coverage",
        help="Emit per-category {category: state} JSON.",
    )
    sp.set_defaults(func=cmd_rubric_coverage)

    sp = sub.add_parser(
        "verify-decision-coverage",
        help="Gate: every category ∈ {Clear, NoDPInCategory}.",
    )
    sp.set_defaults(func=cmd_verify_decision_coverage)

    sp = sub.add_parser(
        "rubric-finalize",
        help="Same gate as verify-decision-coverage (plan line 333).",
    )
    sp.set_defaults(func=cmd_rubric_finalize)

    sp = sub.add_parser(
        "dp-finalize",
        help="Gate Phase 2 → Phase 3 (verify-decision-coverage + stamp).",
    )
    sp.set_defaults(func=cmd_dp_finalize)

    # ----- Phase 3 ---------------------------------------------------------

    sp = sub.add_parser(
        "classify-spec-type",
        help="Set spec_type + rationale + (optional) seeded-by-upstream flag.",
    )
    sp.add_argument(
        "--spec-type", required=True, dest="spec_type",
        choices=list(SPEC_TYPE_ENUM),
    )
    sp.add_argument("--rationale", required=True)
    sp.add_argument(
        "--seeded-by-upstream", action="store_true", default=False,
        dest="seeded_by_upstream",
        help="Phase 1 adapter pre-seeded from /discover (path-based).",
    )
    sp.set_defaults(func=cmd_classify_spec_type)

    sp = sub.add_parser(
        "record-mandatory-read",
        help="Record a Phase 3 mandatory-read entry (--read-path or "
             "--n-a-reason+--slot-pattern).",
    )
    sp.add_argument(
        "--read-path", default="", dest="read_path",
        help="Actual file path read (mutually exclusive with --n-a-reason).",
    )
    sp.add_argument(
        "--slot-pattern", default="", dest="slot_pattern",
        help="Explicit slot pattern (required with --n-a-reason; "
             "optional with --read-path for sentinel slots).",
    )
    sp.add_argument(
        "--n-a-reason", default="", dest="n_a_reason",
        help="Reason for marking the slot N/A.",
    )
    sp.set_defaults(func=cmd_record_mandatory_read)

    sp = sub.add_parser(
        "verify-mandatory-reads",
        help="Walk MANDATORY_READS_BY_TYPE; every slot must be covered.",
    )
    sp.set_defaults(func=cmd_verify_mandatory_reads)

    sp = sub.add_parser(
        "phase3-finalize",
        help="Gate Phase 3 → Phase 4 (verify-mandatory-reads + stamp).",
    )
    sp.set_defaults(func=cmd_phase3_finalize)

    # ----- Phase 4 ---------------------------------------------------------

    sp = sub.add_parser(
        "assign-spec-number",
        help="Scan specs/ for highest NNN-*; emit + persist next.",
    )
    sp.add_argument(
        "--specs-root", default=SPECS_ROOT_DEFAULT, dest="specs_root",
        help="Path to specs/ root (default: specs).",
    )
    sp.set_defaults(func=cmd_assign_spec_number)

    sp = sub.add_parser(
        "assign-feature-name",
        help="Validate 2-4 word kebab-case + persist feature_name/slug.",
    )
    sp.add_argument("--feature-name", required=True, dest="feature_name")
    sp.set_defaults(func=cmd_assign_feature_name)

    sp = sub.add_parser(
        "set-date",
        help="Set spec header Date (YYYY-MM-DD).",
    )
    sp.add_argument("--date", required=True)
    sp.set_defaults(func=cmd_set_date)

    sp = sub.add_parser(
        "create-branch",
        help="Emit git checkout-b for spec branch when on default branch.",
    )
    sp.add_argument(
        "--current-branch", required=True, dest="current_branch",
    )
    sp.add_argument(
        "--default-branch", required=True, dest="default_branch",
    )
    sp.set_defaults(func=cmd_create_branch)

    sp = sub.add_parser(
        "record-affected-area",
        help="Append §4 row {area, files, impact}.",
    )
    sp.add_argument("--area", required=True)
    sp.add_argument(
        "--files", default="[]",
        help="JSON array of strings.",
    )
    sp.add_argument("--impact", required=True)
    sp.set_defaults(func=cmd_record_affected_area)

    sp = sub.add_parser(
        "set-overview", help="Set §1 Overview content.",
    )
    sp.add_argument("--content", required=True)
    sp.set_defaults(func=cmd_set_overview)

    sp = sub.add_parser(
        "set-current-state", help="Set §2 Current State content.",
    )
    sp.add_argument("--content", required=True)
    sp.set_defaults(func=cmd_set_current_state)

    sp = sub.add_parser(
        "set-desired-behavior",
        help="Set §3 Desired Behavior content.",
    )
    sp.add_argument("--content", required=True)
    sp.set_defaults(func=cmd_set_desired_behavior)

    sp = sub.add_parser(
        "add-ac",
        help="Add §5 Acceptance Criterion (validates EARS regex + "
             "subsection-EARS constraint).",
    )
    sp.add_argument("--ac-id", default="", dest="ac_id")
    sp.add_argument(
        "--subsection", required=True,
        choices=list(AC_SUBSECTION_ENUM),
    )
    sp.add_argument(
        "--ears-variant", default="", dest="ears_variant",
    )
    sp.add_argument("--statement", default="")
    sp.add_argument(
        "--verification-command", default="",
        dest="verification_command",
    )
    sp.add_argument(
        "--test-anchor", default="", dest="test_anchor",
    )
    sp.add_argument(
        "--n-a-reason", default="", dest="n_a_reason",
    )
    sp.add_argument(
        "--mark-na", action="store_true", default=False, dest="mark_na",
        help="Record subsection-level N/A marker (requires --n-a-reason).",
    )
    sp.set_defaults(func=cmd_add_ac)

    sp = sub.add_parser(
        "record-out-of-scope",
        help="Append §6 OOS entry {content, finding_ref?}.",
    )
    sp.add_argument("--content", required=True)
    sp.add_argument(
        "--finding-ref", default="", dest="finding_ref",
        help="Optional cross-ref to Phase 1.5 finding_id.",
    )
    sp.set_defaults(func=cmd_record_out_of_scope)

    sp = sub.add_parser(
        "record-constraint",
        help="Append §7 Constraint entry {kind, content}.",
    )
    sp.add_argument(
        "--kind", required=True, choices=list(CONSTRAINT_KIND_ENUM),
    )
    sp.add_argument("--content", required=True)
    sp.set_defaults(func=cmd_record_constraint)

    sp = sub.add_parser(
        "record-open-question",
        help="Append §8 Open Question entry.",
    )
    sp.add_argument(
        "--question-id", required=True, dest="question_id",
    )
    sp.add_argument("--content", required=True)
    sp.add_argument(
        "--category-no-dp-reason", default="",
        dest="category_no_dp_reason",
        help="Optional: per-Phase-2-category 'no DP' rationale.",
    )
    sp.set_defaults(func=cmd_record_open_question)

    sp = sub.add_parser(
        "record-risk",
        help="Append §9 Risks row {risk, likelihood, impact, mitigation}.",
    )
    sp.add_argument("--risk", required=True)
    sp.add_argument(
        "--likelihood", required=True, choices=list(LIKELIHOOD_ENUM),
    )
    sp.add_argument(
        "--impact", required=True, choices=list(IMPACT_ENUM),
    )
    sp.add_argument("--mitigation", required=True)
    sp.set_defaults(func=cmd_record_risk)

    sp = sub.add_parser(
        "verify-coverage",
        help="Variance rule #5: every finding landed in AC/Constraint/OOS/Risk.",
    )
    sp.set_defaults(func=cmd_verify_coverage)

    sp = sub.add_parser(
        "verify-numerical-consistency",
        help="Variance rule #6: digit-prefixed nouns consistent across spec.",
    )
    sp.set_defaults(func=cmd_verify_numerical_consistency)

    sp = sub.add_parser(
        "verify-ac-subsection-coverage",
        help="Every of 7 subsections has ≥1 AC or N/A reason.",
    )
    sp.set_defaults(func=cmd_verify_ac_subsection_coverage)

    sp = sub.add_parser(
        "verify-ac-shape",
        help="Variance rule #10: every AC.statement matches EARS regex.",
    )
    sp.set_defaults(func=cmd_verify_ac_shape)

    sp = sub.add_parser(
        "check-constitution-compliance",
        help="Non-blocking: surface constitution MUST/SHALL overlap warnings.",
    )
    sp.add_argument(
        "--constitution-path", default="constitution.md",
        dest="constitution_path",
        help="Path to constitution.md (default: ./constitution.md).",
    )
    sp.set_defaults(func=cmd_check_constitution_compliance)

    sp = sub.add_parser(
        "render", help="Emit 9-section spec markdown to stdout.",
    )
    sp.set_defaults(func=cmd_render)

    # ----- Phase 5 ---------------------------------------------------------

    sp = sub.add_parser(
        "render-summary",
        help="Emit 4-bullet approval summary; persist to state.",
    )
    sp.set_defaults(func=cmd_render_summary)

    sp = sub.add_parser(
        "set-status",
        help="Set spec.status; closed enum.",
    )
    sp.add_argument(
        "--status", required=True, choices=list(SPEC_STATUS_ENUM),
    )
    sp.set_defaults(func=cmd_set_status)

    sp = sub.add_parser(
        "render-plan-handoff",
        help="Emit deterministic /plan handoff block; persist to state.",
    )
    sp.set_defaults(func=cmd_render_plan_handoff)

    # ----- Downstream ------------------------------------------------------

    sp = sub.add_parser(
        "resolve-open-question",
        help="Append resolution audit entry for §8 Open Question.",
    )
    sp.add_argument(
        "--question-id", required=True, dest="question_id",
    )
    sp.add_argument(
        "--resolution-text", required=True, dest="resolution_text",
    )
    sp.add_argument(
        "--resolution-phase", required=True, dest="resolution_phase",
        choices=list(RESOLUTION_PHASE_ENUM),
    )
    sp.set_defaults(func=cmd_resolve_open_question)

    # ----- Cross-phase -----------------------------------------------------

    sp = sub.add_parser(
        "summary", help="Emit phase-progress + counts dashboard JSON.",
    )
    sp.set_defaults(func=cmd_summary)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
