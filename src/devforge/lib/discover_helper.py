"""discover_helper — state helper for /discover.

Owns the shape of two state files under .devforge/ for the /discover
command. Mirrors the helper-owns-shape pattern from research_helper /
constitute_helper / configure_helper.

/discover investigates whether a new feature or change is worth pursuing
against the existing codebase — sizing fit, integration complexity, design
options, and a go/no-go verdict — before /specify is run.

State files
-----------

  .devforge/discover-scope.json   — Phase 0 ScopingMemo (rubric Q&A across
                                    8 dimensions: functional_scope, users,
                                    inputs_outputs, integration_points,
                                    constraints, non_goals, success_criteria,
                                    edge_cases).
  .devforge/discover-report.json  — Phase 2 DiscoveryReport (prior art,
                                    integration touchpoints, fit assessments,
                                    design options, build-vs-buy, derisk plan,
                                    constitution constraints, verdict).

Each has its own state-transaction context so memo and report progress
independently.

Subcommand summary
------------------

  Plumbing     reset-memo, reset-report, read-memo, read-report, preflight
  Shared       set-topic, set-date
  Phase 0      set-scope-<dimension> (x8), record-references, record-gap,
               check-conflicts, record-conflict-resolution,
               scope-coverage, scope-finalize
  Phase 1      record-prior-art, record-integration-touchpoint,
               record-fit-assessment, set-overall-fit,
               set-effort-estimate, set-fit-rationale
  Phase 2      set-summary, set-design-option, set-recommended-option,
               set-build-vs-buy, set-derisk-plan,
               set-constitution-constraints, set-verdict,
               set-recommendation, set-next-step-text
  Render       render
  Verify       verify

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
from typing import Dict, Iterator, List, Optional, Tuple, Union

try:
    import fcntl
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX fallback
    _HAVE_FCNTL = False


# ---------------------------------------------------------------------------
# Schema constants — single source of truth.
# ---------------------------------------------------------------------------

MEMO_FILE_NAME = "discover-scope.json"
REPORT_FILE_NAME = "discover-report.json"

# Phase 0 rubric — 8 dimensions. Locked order: this is the order
# coverage emits, render uses, and tests verify.
RUBRIC_DIMENSIONS = (
    "functional_scope",
    "users",
    "inputs_outputs",
    "integration_points",
    "constraints",
    "non_goals",
    "success_criteria",
    "edge_cases",
)

# Per-dimension state machine. Helper transitions Missing→Partial→Clear
# as setters fire.
RUBRIC_STATE_ENUM = ("Clear", "Partial", "Missing")
RUBRIC_STATE_DEFAULT = "Missing"

# Conflict type enum (Phase 0 misalignment detection).
CONFLICT_TYPE_ENUM = ("direct", "drift", "refinement")

# Complexity rating enum.
COMPLEXITY_ENUM = ("Low", "Med", "High")

# Effort enum (used in fit assessments).
EFFORT_ENUM = ("Low", "Medium", "High", "Major refactor required")

# Overall fit enum.
OVERALL_FIT_ENUM = ("Good", "Acceptable", "Strained", "Misfit")

# Prior-art kind enum (Phase 1 record-prior-art).
PRIOR_ART_KIND_ENUM = ("library", "product", "pattern")

# Verdict enum (go/no-go verdict at Phase 2 close).
VERDICT_ENUM = ("Worth pursuing", "Promising with caveats", "Reconsider")

# Build vs Buy recommendation enum.
BUILD_VS_BUY_ENUM = ("Build", "Buy", "Hybrid")

# Hard-gate prerequisites checked by `preflight`. Tuple of
# (relative-path-from-install-root, producer-label). Mirrors
# research_helper.PREFLIGHT_PREREQS exactly.
PREFLIGHT_PREREQS = (
    (".devforge/init.yaml", "/init-forge"),
    ("docs/architecture.md", "/generate-docs"),
    (".devforge/configure.yaml", "/configure"),
    ("constitution.md", "/constitute"),
)


# ---------------------------------------------------------------------------
# Default-state builders.
# ---------------------------------------------------------------------------


def _empty_dimension() -> dict:
    """Return a fresh rubric-dimension record."""
    return {"value": None, "state": RUBRIC_STATE_DEFAULT, "turns": 0}


def default_memo_state() -> dict:
    """Return a fresh ScopingMemo state matching schema."""
    return {
        "topic": None,
        "topic_slug": None,
        "date": None,
        "dimensions": {d: _empty_dimension() for d in RUBRIC_DIMENSIONS},
        "references": [],
        "gaps": [],
        "override_recorded": False,
        "conflicts": [],
    }


def default_report_state() -> dict:
    """Return a fresh DiscoveryReport state matching schema."""
    return {
        "topic": None,
        "date": None,
        "topic_slug": None,
        "summary": None,
        "prior_art": [],
        "integration_touchpoints": [],
        "fit_assessments": [],
        "overall_fit": None,
        "effort_estimate": None,
        "fit_rationale": None,
        "design_options": [],
        "recommended_option": None,
        "build_vs_buy": None,
        "derisk_plan": [],
        "constitution_constraints": [],
        "verdict": None,
        "recommendation": None,
        "next_step_text": None,
        "open_uncertainties": [],
    }


# ---------------------------------------------------------------------------
# State-file plumbing (load / dump / transaction).
# ---------------------------------------------------------------------------


def _memo_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    return Path(devforge_dir) / MEMO_FILE_NAME


def _report_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    return Path(devforge_dir) / REPORT_FILE_NAME


def _atomic_write_json(state: dict, target: Path) -> None:
    """Atomically write state as JSON to target.

    Uses tempfile.mkstemp in the same directory + os.replace.
    flush + fsync precede os.replace for durability.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="discover-",
        suffix=".json.tmp",
        dir=str(target.parent),
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


def _load_memo(devforge_dir: Union[str, "os.PathLike[str]"]) -> dict:
    """Load discover-scope.json. Missing → default_memo_state()."""
    path = _memo_path(devforge_dir)
    if not path.exists():
        return default_memo_state()
    return json.loads(path.read_text(encoding="utf-8"))


def _load_report(devforge_dir: Union[str, "os.PathLike[str]"]) -> dict:
    """Load discover-report.json. Missing → default_report_state()."""
    path = _report_path(devforge_dir)
    if not path.exists():
        return default_report_state()
    return json.loads(path.read_text(encoding="utf-8"))


def _lock_path(state_path: Path) -> Path:
    return state_path.parent / (state_path.name + ".lock")


@contextlib.contextmanager
def _state_transaction(
    devforge_dir: Union[str, "os.PathLike[str]"],
    which: str,
) -> Iterator[dict]:
    """Read-modify-write either memo or report under fcntl lock.

    `which` in {"memo", "report"}. On POSIX, fcntl.flock(LOCK_EX) on the
    sidecar lock file. On Windows (no fcntl), no-op locking — out of
    scope for AIDevTeamForge. Body raise → write skipped, exception
    propagates.
    """
    if which == "memo":
        state_path = _memo_path(devforge_dir)
        loader = _load_memo
    elif which == "report":
        state_path = _report_path(devforge_dir)
        loader = _load_report
    else:
        raise ValueError("unknown state {0!r}".format(which))

    devforge_path = Path(devforge_dir)
    devforge_path.mkdir(parents=True, exist_ok=True)
    lock = _lock_path(state_path)
    fd = os.open(str(lock), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if _HAVE_FCNTL:
            fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            state = loader(devforge_dir)
            yield state
            _atomic_write_json(state, state_path)
        finally:
            if _HAVE_FCNTL:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Error helpers.
# ---------------------------------------------------------------------------


def _die(message: str, code: int = 1) -> int:
    """Write error to stderr and return code (caller propagates as exit)."""
    sys.stderr.write("discover_helper: {0}\n".format(message))
    return code


# ---------------------------------------------------------------------------
# Validation helpers.
# ---------------------------------------------------------------------------


def _validate_scalar(value: str, field_name: str) -> str:
    """Strip + reject empty. Returns stripped string."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return stripped


# ---------------------------------------------------------------------------
# Topic slug derivation.
# ---------------------------------------------------------------------------

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_SLUG_MAX_CHARS = 60


def derive_topic_slug(topic: str) -> str:
    """Lowercase + kebab-case + truncate at last `-` boundary before max 60 chars.

    Empty input or no-alnum-chars → "topic" as fallback. Used for
    discover-scope filename slug + memo.topic_slug / report.topic_slug.
    """
    lowered = topic.lower().strip()
    cleaned = _SLUG_NON_ALNUM.sub("-", lowered).strip("-")
    if not cleaned:
        return "topic"
    if len(cleaned) <= _SLUG_MAX_CHARS:
        return cleaned
    # Truncate at last `-` boundary before max_chars to avoid mid-word cuts.
    head = cleaned[:_SLUG_MAX_CHARS]
    boundary = head.rsplit("-", 1)[0]
    truncated = (boundary or head).rstrip("-")
    if not truncated:
        return "topic"
    return truncated


# ---------------------------------------------------------------------------
# Token-overlap conflict detection (Phase 0, deterministic, no LLM).
# ---------------------------------------------------------------------------

# Stopwords excluded from token-overlap matching.
_CONFLICT_STOPWORDS = frozenset({
    "a", "an", "the", "or", "and", "to", "of", "for",
    "with", "in", "on", "at", "by", "is", "as", "but", "not", "no",
})

# Minimum token length (characters) for overlap matching.
_CONFLICT_MIN_TOKEN_LEN = 4

# Dimension pairs checked by check-conflicts. non_goals is the anchor;
# the second dimension is the target. Locked order.
_CONFLICT_CHECK_PAIRS = (
    ("non_goals", "integration_points"),
    ("non_goals", "functional_scope"),
    ("non_goals", "success_criteria"),
    ("non_goals", "edge_cases"),
)


def _tokenize_for_conflict(text: str) -> List[str]:
    """Split text into lowercase tokens, drop stopwords + short tokens.

    Splits on whitespace and punctuation (any non-alphanumeric character).
    Returns tokens of length >= _CONFLICT_MIN_TOKEN_LEN not in stopwords.
    """
    raw_tokens = re.split(r"[^a-zA-Z0-9]+", text.lower())
    return [
        t for t in raw_tokens
        if len(t) >= _CONFLICT_MIN_TOKEN_LEN and t not in _CONFLICT_STOPWORDS
    ]


def _detect_scope_conflicts(memo: dict) -> List[dict]:
    """Scan memo dimensions for direct contradictions via token overlap.

    For each pair in _CONFLICT_CHECK_PAIRS, checks whether any
    significant token from dim_a also appears in dim_b. Returns a list
    of conflict dicts (type=direct, resolution=None). Read-only.
    """
    dims = memo.get("dimensions", {})
    conflicts = []  # type: List[dict]

    def _val(name: str) -> str:
        rec = dims.get(name, {})
        if not isinstance(rec, dict):
            return ""
        v = rec.get("value")
        return v if isinstance(v, str) else ""

    for dim_a, dim_b in _CONFLICT_CHECK_PAIRS:
        val_a = _val(dim_a)
        val_b = _val(dim_b)
        if not val_a or not val_b:
            continue
        tokens_a = set(_tokenize_for_conflict(val_a))
        tokens_b = set(_tokenize_for_conflict(val_b))
        overlap = tokens_a & tokens_b
        if overlap:
            # Pick the lexicographically first token for deterministic output.
            token = min(overlap)
            conflicts.append({
                "type": "direct",
                "dimensions": [dim_a, dim_b],
                "description": "'{0}' appears in both {1} and {2}".format(
                    token, dim_a, dim_b
                ),
                "resolution": None,
            })
    return conflicts


# ---------------------------------------------------------------------------
# Coverage helper (used by scope-coverage + scope-finalize).
# ---------------------------------------------------------------------------


def _compute_scope_coverage(
    memo: dict,
) -> Tuple[Dict[str, str], int, int, int]:
    """Return (per-dim state map, clear_count, partial_count, missing_count)."""
    dims = memo.get("dimensions", {})
    state_map = {}  # type: Dict[str, str]
    clear = partial = missing = 0
    for d in RUBRIC_DIMENSIONS:
        rec = dims.get(d, _empty_dimension())
        st = rec.get("state", RUBRIC_STATE_DEFAULT)
        state_map[d] = st
        if st == "Clear":
            clear += 1
        elif st == "Partial":
            partial += 1
        else:
            missing += 1
    return state_map, clear, partial, missing


# ---------------------------------------------------------------------------
# Argparse + main.
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="discover_helper",
        description="State helper for /discover. Owns discover artifact shape.",
    )
    parser.add_argument(
        "--devforge-dir",
        default=".devforge",
        help="Path to the .devforge directory (default: .devforge in CWD).",
    )
    parser.add_argument(
        "--install-root",
        default=None,
        help=(
            "Path to the install root (project root for standalone, wrapper "
            "root for wrapper mode). Default: parent of --devforge-dir."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers) -> None:
    """All cmd_* handlers registered here."""
    # Plumbing
    sp = subparsers.add_parser("reset-memo", help="Write a fresh defaults memo state.")
    sp.set_defaults(func=cmd_reset_memo)

    sp = subparsers.add_parser("reset-report", help="Write a fresh defaults report state.")
    sp.set_defaults(func=cmd_reset_report)

    sp = subparsers.add_parser(
        "read-memo",
        help="Print discover-scope.json (or defaults) as JSON.",
    )
    sp.set_defaults(func=cmd_read_memo)

    sp = subparsers.add_parser(
        "read-report",
        help="Print discover-report.json (or defaults) as JSON.",
    )
    sp.set_defaults(func=cmd_read_report)

    sp = subparsers.add_parser(
        "preflight",
        help="Hard-gate check: 4 setup-chain artefacts present + non-empty.",
    )
    sp.set_defaults(func=cmd_preflight)

    sp = subparsers.add_parser(
        "set-topic",
        help="Set memo.topic + report.topic and auto-derive topic_slug in both.",
    )
    sp.add_argument("--value", required=True, help="Topic text (user's original input).")
    sp.set_defaults(func=cmd_set_topic)

    sp = subparsers.add_parser(
        "set-date",
        help="Set memo.date + report.date (YYYY-MM-DD).",
    )
    sp.add_argument("--value", required=True, help="Date in YYYY-MM-DD format.")
    sp.set_defaults(func=cmd_set_date)

    # Phase 0 — dimension setters (8, one per RUBRIC_DIMENSIONS entry).
    for _dim in RUBRIC_DIMENSIONS:
        _sp_name = "set-scope-" + _dim.replace("_", "-")
        sp = subparsers.add_parser(_sp_name, help="Set scope dimension: {0}.".format(_dim))
        sp.add_argument("--value", required=True, help="Value text (non-empty after strip).")
        sp.add_argument(
            "--state",
            default="Clear",
            choices=list(RUBRIC_STATE_ENUM),
            help="Dimension state after this set (default: Clear).",
        )
        sp.add_argument(
            "--increment-turn",
            action="store_true",
            help="Add 1 to dimensions.<dim>.turns.",
        )
        sp.set_defaults(func=_make_scope_dim_setter(_dim), dimension=_dim)

    sp = subparsers.add_parser(
        "record-references",
        help="Set memo.references to a JSON array of strings (replaces, does not append).",
    )
    sp.add_argument(
        "--values",
        required=True,
        help='JSON array of strings, e.g. \'["A","B"]\'. Use "[]" for none.',
    )
    sp.set_defaults(func=cmd_record_references)

    sp = subparsers.add_parser(
        "record-gap",
        help="Append (or replace) a {dimension, description} gap entry in memo.gaps.",
    )
    sp.add_argument(
        "--dimension",
        required=True,
        choices=list(RUBRIC_DIMENSIONS),
        help="Dimension name (underscore form).",
    )
    sp.add_argument("--description", required=True, help="Gap description (non-empty).")
    sp.set_defaults(func=cmd_record_gap)

    sp = subparsers.add_parser(
        "check-conflicts",
        help=(
            "Scan memo dimensions for direct token-overlap contradictions. "
            "Emits JSON array to stdout. Read-only."
        ),
    )
    sp.set_defaults(func=cmd_check_conflicts)

    sp = subparsers.add_parser(
        "record-conflict-resolution",
        help="Persist user resolution for a detected conflict and clear the loser dimension.",
    )
    sp.add_argument("--index", required=True, type=int, help="0-based index into conflicts list.")
    sp.add_argument("--resolution", required=True, help="Resolution label (free text).")
    sp.add_argument(
        "--rewrite-dimension",
        required=True,
        dest="rewrite_dimension",
        choices=list(RUBRIC_DIMENSIONS),
        help="Dimension whose value to clear (the loser).",
    )
    sp.set_defaults(func=cmd_record_conflict_resolution)

    sp = subparsers.add_parser(
        "scope-coverage",
        help="Emit JSON coverage report for all 8 dimensions. Read-only.",
    )
    sp.set_defaults(func=cmd_scope_coverage)

    sp = subparsers.add_parser(
        "scope-finalize",
        help=(
            "Validate memo is finalize-ready. Exit 0 = ready for Phase 1. "
            "Exit 2 if any violations remain."
        ),
    )
    sp.add_argument(
        "--accept-gaps",
        action="store_true",
        help="Accept Partial/Missing dimensions; record override_recorded=True.",
    )
    sp.set_defaults(func=cmd_scope_finalize)

    # Phase 1 — investigation setters.
    sp = subparsers.add_parser(
        "record-prior-art",
        help="Append one prior-art entry to report.prior_art.",
    )
    sp.add_argument("--reference", required=True, help="Library/product/pattern name (non-empty).")
    sp.add_argument(
        "--kind",
        required=True,
        choices=list(PRIOR_ART_KIND_ENUM),
        help="Kind: one of {0}.".format(", ".join(PRIOR_ART_KIND_ENUM)),
    )
    sp.add_argument("--relevance", required=True, help="One-line note tying it to the topic (non-empty).")
    sp.add_argument(
        "--source",
        default="",
        help="URL or Context7 library id (optional; default empty string).",
    )
    sp.set_defaults(func=cmd_record_prior_art)

    sp = subparsers.add_parser(
        "record-integration-touchpoint",
        help="Append one integration touchpoint entry to report.integration_touchpoints.",
    )
    sp.add_argument("--name", required=True, help="Touchpoint name (non-empty).")
    sp.add_argument("--module-path", required=True, dest="module_path", help="Module path (non-empty).")
    sp.add_argument("--reason", required=True, help="Why this touchpoint matters (non-empty).")
    sp.set_defaults(func=cmd_record_integration_touchpoint)

    sp = subparsers.add_parser(
        "record-fit-assessment",
        help="Append one fit-assessment entry to report.fit_assessments.",
    )
    sp.add_argument(
        "--touchpoint",
        required=True,
        help="Must match the name of an existing integration_touchpoint entry.",
    )
    sp.add_argument("--user-expected", required=True, dest="user_expected", help="User's Phase 0 belief (non-empty).")
    sp.add_argument("--reality", required=True, help="What the codebase scan found (non-empty).")
    sp.add_argument(
        "--effort",
        required=True,
        choices=list(EFFORT_ENUM),
        help="Per-touchpoint effort: one of {0}.".format(", ".join(EFFORT_ENUM)),
    )
    sp.add_argument(
        "--blockers",
        default="[]",
        help='JSON array of strings (optional; default "[]").',
    )
    sp.set_defaults(func=cmd_record_fit_assessment)

    sp = subparsers.add_parser(
        "set-overall-fit",
        help="Set report.overall_fit to an OVERALL_FIT_ENUM value.",
    )
    sp.add_argument(
        "--value",
        required=True,
        choices=list(OVERALL_FIT_ENUM),
        help="One of: {0}.".format(", ".join(OVERALL_FIT_ENUM)),
    )
    sp.set_defaults(func=cmd_set_overall_fit)

    sp = subparsers.add_parser(
        "set-effort-estimate",
        help="Set report.effort_estimate to an EFFORT_ENUM value.",
    )
    sp.add_argument(
        "--value",
        required=True,
        choices=list(EFFORT_ENUM),
        help="One of: {0}.".format(", ".join(EFFORT_ENUM)),
    )
    sp.set_defaults(func=cmd_set_effort_estimate)

    sp = subparsers.add_parser(
        "set-fit-rationale",
        help="Set report.fit_rationale to a non-empty string.",
    )
    sp.add_argument("--value", required=True, help="Rationale text (non-empty).")
    sp.set_defaults(func=cmd_set_fit_rationale)

    # Phase 2 — report drafting + render + verify.
    sp = subparsers.add_parser(
        "set-summary",
        help="Set report.summary to a non-empty string.",
    )
    sp.add_argument("--value", required=True, help="Summary text (non-empty).")
    sp.set_defaults(func=cmd_set_summary)

    sp = subparsers.add_parser(
        "set-design-option",
        help="Append one design-option entry to report.design_options.",
    )
    sp.add_argument("--name", required=True, help="Option name (unique, non-empty).")
    sp.add_argument("--shape", required=True, help="Option shape / description (non-empty).")
    sp.add_argument(
        "--pros",
        required=True,
        help="JSON array of non-empty strings (at least 1 entry).",
    )
    sp.add_argument(
        "--cons",
        required=True,
        help="JSON array of non-empty strings (at least 1 entry).",
    )
    sp.add_argument(
        "--complexity",
        required=True,
        choices=list(COMPLEXITY_ENUM),
        help="Complexity: one of {0}.".format(", ".join(COMPLEXITY_ENUM)),
    )
    sp.set_defaults(func=cmd_set_design_option)

    sp = subparsers.add_parser(
        "set-recommended-option",
        help="Set report.recommended_option; --name must match an existing design_option.name.",
    )
    sp.add_argument("--name", required=True, help="Must match an existing design_option name.")
    sp.add_argument("--rationale", required=True, help="Rationale for recommendation (non-empty).")
    sp.set_defaults(func=cmd_set_recommended_option)

    sp = subparsers.add_parser(
        "set-build-vs-buy",
        help="Set report.build_vs_buy.",
    )
    sp.add_argument("--build", required=True, help="Build-path description (non-empty).")
    sp.add_argument("--buy", required=True, help="Buy/adopt-path description (non-empty).")
    sp.add_argument(
        "--recommendation",
        required=True,
        choices=list(BUILD_VS_BUY_ENUM),
        help="Recommendation: one of {0}.".format(", ".join(BUILD_VS_BUY_ENUM)),
    )
    sp.add_argument("--reasoning", required=True, help="Reasoning text (non-empty).")
    sp.set_defaults(func=cmd_set_build_vs_buy)

    sp = subparsers.add_parser(
        "set-derisk-plan",
        help="Set report.derisk_plan to a JSON array of strings.",
    )
    sp.add_argument(
        "--items",
        required=True,
        help="JSON array of non-empty strings (at least 1 item).",
    )
    sp.set_defaults(func=cmd_set_derisk_plan)

    sp = subparsers.add_parser(
        "set-constitution-constraints",
        help="Append one entry to report.constitution_constraints.",
    )
    sp.add_argument("--rule", required=True, help="Constraint rule text (non-empty).")
    sp.add_argument("--impact", required=True, help="Impact description (non-empty).")
    sp.set_defaults(func=cmd_set_constitution_constraints)

    sp = subparsers.add_parser(
        "set-verdict",
        help="Set report.verdict to a VERDICT_ENUM value.",
    )
    sp.add_argument(
        "--value",
        required=True,
        choices=list(VERDICT_ENUM),
        help="Verdict: one of {0}.".format(", ".join(VERDICT_ENUM)),
    )
    sp.set_defaults(func=cmd_set_verdict)

    sp = subparsers.add_parser(
        "set-recommendation",
        help="Set report.recommendation.",
    )
    sp.add_argument("--action", required=True, help="Action text (non-empty).")
    sp.add_argument("--next", required=True, dest="next_text", help="Next step text (non-empty).")
    sp.set_defaults(func=cmd_set_recommendation)

    sp = subparsers.add_parser(
        "set-next-step-text",
        help=(
            "Compose and set report.next_step_text from memo + report state. "
            "Reads memo.functional_scope/users/success_criteria + report.verdict + "
            "report.recommended_option. Optional --topic supplies an LLM-distilled "
            "1-2 sentence topic for the /specify block (otherwise the helper falls "
            "back to the first sentence of memo.functional_scope)."
        ),
    )
    sp.add_argument(
        "--topic",
        required=False,
        default=None,
        help=(
            "Distilled 1-2 sentence topic to embed in the /specify \"...\" block. "
            "Overrides the helper's first-sentence fallback. Pass the same distilled "
            "string the orchestrator composed from functional_scope + users + "
            "success_criteria."
        ),
    )
    sp.set_defaults(func=cmd_set_next_step_text)

    sp = subparsers.add_parser(
        "render",
        help="Render the full discovery report as Markdown to stdout. Read-only.",
    )
    sp.set_defaults(func=cmd_render)

    sp = subparsers.add_parser(
        "verify",
        help=(
            "Cross-field invariant check. Exit 0 = clean. "
            "Exit 2 = violations (all enumerated on stderr)."
        ),
    )
    sp.set_defaults(func=cmd_verify)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    if args.install_root is None:
        args.install_root = str(Path(args.devforge_dir).resolve().parent)
    return args.func(args)


# ---------------------------------------------------------------------------
# Handler implementations.
# ---------------------------------------------------------------------------


def cmd_reset_memo(args: argparse.Namespace) -> int:
    """Write fresh defaults memo state. Idempotent."""
    try:
        _atomic_write_json(default_memo_state(), _memo_path(args.devforge_dir))
    except OSError as err:
        return _die("reset-memo: {0}".format(err))
    return 0


def cmd_reset_report(args: argparse.Namespace) -> int:
    """Write fresh defaults report state. Idempotent."""
    try:
        _atomic_write_json(default_report_state(), _report_path(args.devforge_dir))
    except OSError as err:
        return _die("reset-report: {0}".format(err))
    return 0


def cmd_read_memo(args: argparse.Namespace) -> int:
    """Print discover-scope.json as JSON to stdout (defaults if missing)."""
    try:
        state = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("read-memo: {0}".format(err))
    json.dump(state, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_read_report(args: argparse.Namespace) -> int:
    """Print discover-report.json as JSON to stdout (defaults if missing)."""
    try:
        state = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("read-report: {0}".format(err))
    json.dump(state, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    """4-artefact hard gate. Exit 2 + BLOCKED message on any missing.

    Checks each PREFLIGHT_PREREQS path relative to --install-root for
    existence + non-empty (size > 0). On any failure, emits a single
    BLOCKED: header followed by one Missing: line per absent artefact and
    exits 2. All missing artefacts are listed — not just the first.
    """
    install_root = Path(args.install_root)
    missing = []  # type: List[Tuple[str, str]]
    for rel_path, producer in PREFLIGHT_PREREQS:
        p = install_root / rel_path
        try:
            if not p.exists():
                missing.append((rel_path, producer))
                continue
            if p.stat().st_size == 0:
                missing.append((rel_path, producer))
        except OSError as err:
            return _die("preflight: stat failed on {0}: {1}".format(p, err))

    if missing:
        sys.stderr.write(
            "BLOCKED: /discover requires the full 4-command setup chain.\n"
        )
        for rel, producer in missing:
            sys.stderr.write("Missing: {0} (produced by {1})\n".format(rel, producer))
        sys.stderr.write(
            "Run: /init-forge → /generate-docs → /configure → /constitute, "
            "then retry /discover.\n"
        )
        return 2
    return 0


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def cmd_set_topic(args: argparse.Namespace) -> int:
    """Set memo.topic + report.topic and auto-derive topic_slug in both.

    Topic comes from the user's original /discover argument. Auto-deriving
    slug here means the orchestrator owns one input string; helper renders
    both topic text and filename slug.
    """
    try:
        value = _validate_scalar(args.value, "topic")
    except ValueError as err:
        return _die(str(err), code=2)
    slug = derive_topic_slug(value)
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo["topic"] = value
            memo["topic_slug"] = slug
        with _state_transaction(args.devforge_dir, "report") as report:
            report["topic"] = value
            report["topic_slug"] = slug
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-topic: {0}".format(err))
    return 0


def cmd_set_date(args: argparse.Namespace) -> int:
    """Set memo.date + report.date. Format YYYY-MM-DD enforced.

    Validates format with regex then verifies it is a real calendar date
    via datetime.date.fromisoformat to reject impossible dates like
    2026-13-01 or 2026-02-30.
    """
    if not _DATE_RE.match(args.value):
        return _die(
            "set-date: invalid date {0!r}; expected YYYY-MM-DD".format(args.value),
            code=2,
        )
    try:
        datetime.date.fromisoformat(args.value)
    except ValueError:
        return _die(
            "set-date: {0!r} is not a real calendar date".format(args.value),
            code=2,
        )
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo["date"] = args.value
        with _state_transaction(args.devforge_dir, "report") as report:
            report["date"] = args.value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-date: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Phase 0 — rubric setters + conflict / coverage / finalize handlers.
# ---------------------------------------------------------------------------


def _make_scope_dim_setter(dimension: str):
    """Closure factory for set-scope-<dim> subcommands.

    Returns a handler that writes args.value + args.state into
    memo.dimensions[dimension] and optionally increments turns.
    """

    def _handler(args: argparse.Namespace) -> int:
        try:
            value = _validate_scalar(args.value, "set-scope-" + dimension)
        except ValueError as err:
            return _die(str(err), code=2)
        try:
            with _state_transaction(args.devforge_dir, "memo") as memo:
                rec = memo["dimensions"].get(dimension)
                if not isinstance(rec, dict):
                    rec = _empty_dimension()
                rec["value"] = value
                rec["state"] = args.state
                if getattr(args, "increment_turn", False):
                    rec["turns"] = int(rec.get("turns", 0)) + 1
                memo["dimensions"][dimension] = rec
        except (OSError, json.JSONDecodeError) as err:
            return _die("set-scope-{0}: {1}".format(dimension, err))
        return 0

    return _handler


def cmd_record_references(args: argparse.Namespace) -> int:
    """Replace memo.references with a JSON-array-of-strings payload."""
    try:
        decoded = json.loads(args.values)
    except ValueError as err:
        return _die("record-references: --values is not valid JSON: {0}".format(err), code=2)
    if not isinstance(decoded, list):
        return _die(
            "record-references: --values must decode to a JSON array, got {0}".format(
                type(decoded).__name__
            ),
            code=2,
        )
    cleaned = []  # type: List[str]
    for item in decoded:
        if not isinstance(item, str):
            return _die(
                "record-references: every item must be a string, got {0}".format(
                    type(item).__name__
                ),
                code=2,
            )
        cleaned.append(item)
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo["references"] = cleaned
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-references: {0}".format(err))
    return 0


def cmd_record_gap(args: argparse.Namespace) -> int:
    """Append or replace a {dimension, description} gap entry in memo.gaps."""
    try:
        description = _validate_scalar(args.description, "record-gap.description")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            gaps = memo.get("gaps", [])
            # Replace existing gap for this dimension (idempotent), else append.
            replaced = False
            for entry in gaps:
                if isinstance(entry, dict) and entry.get("dimension") == args.dimension:
                    entry["description"] = description
                    replaced = True
                    break
            if not replaced:
                gaps.append({"dimension": args.dimension, "description": description})
            memo["gaps"] = gaps
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-gap: {0}".format(err))
    return 0


def _filter_unresolved(detected: List[dict], existing: List[dict]) -> List[dict]:
    """Drop detected conflicts whose (dimensions-pair) is already resolved."""
    resolved_pairs = set()
    for entry in existing:
        if not isinstance(entry, dict):
            continue
        if entry.get("resolution") is None:
            continue
        dims = entry.get("dimensions") or []
        if isinstance(dims, list) and len(dims) == 2:
            resolved_pairs.add((dims[0], dims[1]))
    out = []
    for c in detected:
        dims = c.get("dimensions", [])
        key = (dims[0], dims[1]) if len(dims) == 2 else None
        if key is not None and key in resolved_pairs:
            continue
        out.append(c)
    return out


def cmd_check_conflicts(args: argparse.Namespace) -> int:
    """Emit JSON array of currently-detectable direct contradictions. Read-only."""
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("check-conflicts: {0}".format(err))
    detected = _detect_scope_conflicts(memo)
    existing = memo.get("conflicts", []) or []
    filtered = _filter_unresolved(detected, existing)
    json.dump(filtered, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_record_conflict_resolution(args: argparse.Namespace) -> int:
    """Persist a user-chosen resolution and clear the loser dimension.

    If state.conflicts is empty, run detect first and append the detected
    conflicts; then apply the resolution at --index. Out-of-range index
    after that is exit 2.
    """
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            conflicts = memo.get("conflicts") or []
            if not conflicts:
                detected = _detect_scope_conflicts(memo)
                if not detected:
                    return _die(
                        "record-conflict-resolution: --index {0} out of range; "
                        "check-conflicts must be called first OR no conflicts exist.".format(
                            args.index
                        ),
                        code=2,
                    )
                conflicts = list(detected)
                memo["conflicts"] = conflicts
            if args.index < 0 or args.index >= len(conflicts):
                return _die(
                    "record-conflict-resolution: --index {0} out of range "
                    "(0..{1}); check-conflicts must be called first.".format(
                        args.index, len(conflicts) - 1
                    ),
                    code=2,
                )
            conflicts[args.index]["resolution"] = args.resolution
            memo["dimensions"][args.rewrite_dimension] = _empty_dimension()
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-conflict-resolution: {0}".format(err))
    return 0


def cmd_scope_coverage(args: argparse.Namespace) -> int:
    """Emit JSON coverage report on stdout. Read-only."""
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("scope-coverage: {0}".format(err))
    state_map, clear, partial, missing = _compute_scope_coverage(memo)
    per_dimension = {}
    dims = memo.get("dimensions", {})
    for d in RUBRIC_DIMENSIONS:
        rec = dims.get(d, _empty_dimension())
        per_dimension[d] = {
            "state": state_map[d],
            "value": rec.get("value"),
            "turns": int(rec.get("turns", 0)),
        }
    conflicts = memo.get("conflicts") or []
    open_conflicts = sum(
        1 for c in conflicts
        if isinstance(c, dict) and c.get("resolution") is None
    )
    payload = {
        "per_dimension": per_dimension,
        "counts": {"Clear": clear, "Partial": partial, "Missing": missing},
        "references_count": len(memo.get("references") or []),
        "gaps_count": len(memo.get("gaps") or []),
        "conflicts_open": open_conflicts,
    }
    json.dump(payload, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_scope_finalize(args: argparse.Namespace) -> int:
    """Validate memo is finalize-ready. Exit 0 = ready, 2 = blocked.

    Open conflicts always block (regardless of --accept-gaps).
    Partial/Missing dimensions block unless --accept-gaps is passed;
    when passed, sets memo.override_recorded = True.
    """
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            conflicts = memo.get("conflicts") or []
            open_indices = [
                i for i, c in enumerate(conflicts)
                if isinstance(c, dict) and c.get("resolution") is None
            ]
            dims = memo.get("dimensions", {})
            offending = []  # type: List[Tuple[str, str]]
            for d in RUBRIC_DIMENSIONS:
                rec = dims.get(d, _empty_dimension())
                st = rec.get("state", RUBRIC_STATE_DEFAULT)
                if st in ("Partial", "Missing"):
                    offending.append((d, st))

            violations = []  # type: List[str]
            for i in open_indices:
                violations.append(
                    "Unresolved conflict at index {0}; resolve via "
                    "record-conflict-resolution.".format(i)
                )
            if not args.accept_gaps:
                for d, st in offending:
                    violations.append(
                        "Dimension '{0}' is {1}; pass --accept-gaps to proceed.".format(
                            d, st
                        )
                    )
            else:
                if not open_indices:
                    memo["override_recorded"] = True

            if violations:
                for v in violations:
                    sys.stderr.write("scope-finalize: {0}\n".format(v))
                raise _FinalizeBlocked()
    except _FinalizeBlocked:
        return 2
    except (OSError, json.JSONDecodeError) as err:
        return _die("scope-finalize: {0}".format(err))
    return 0


class _FinalizeBlocked(Exception):
    """Sentinel to abort the scope-finalize transaction without writing."""


# ---------------------------------------------------------------------------
# Phase 1 — investigation setter handlers.
# ---------------------------------------------------------------------------


def cmd_record_prior_art(args: argparse.Namespace) -> int:
    """Append one prior-art entry to report.prior_art.

    --kind is validated by argparse choices before this handler runs.
    --reference and --relevance must be non-empty after strip.
    --source is optional; defaults to empty string.
    """
    try:
        reference = _validate_scalar(args.reference, "record-prior-art.reference")
        relevance = _validate_scalar(args.relevance, "record-prior-art.relevance")
    except ValueError as err:
        return _die(str(err), code=2)
    entry = {
        "reference": reference,
        "kind": args.kind,
        "relevance": relevance,
        "source": args.source,
    }
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["prior_art"].append(entry)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-prior-art: {0}".format(err))
    return 0


def cmd_record_integration_touchpoint(args: argparse.Namespace) -> int:
    """Append one integration-touchpoint entry to report.integration_touchpoints.

    All three fields (--name, --module-path, --reason) are required and
    must be non-empty after strip.
    """
    try:
        name = _validate_scalar(args.name, "record-integration-touchpoint.name")
        module_path = _validate_scalar(args.module_path, "record-integration-touchpoint.module_path")
        reason = _validate_scalar(args.reason, "record-integration-touchpoint.reason")
    except ValueError as err:
        return _die(str(err), code=2)
    entry = {"name": name, "module_path": module_path, "reason": reason}
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["integration_touchpoints"].append(entry)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-integration-touchpoint: {0}".format(err))
    return 0


def cmd_record_fit_assessment(args: argparse.Namespace) -> int:
    """Append one fit-assessment entry to report.fit_assessments.

    --touchpoint must match the name of an existing integration_touchpoints
    entry. --effort is validated by argparse choices. --blockers is a JSON
    array of strings (defaults to "[]").
    """
    # Decode and validate --blockers before entering the transaction.
    try:
        blockers_raw = json.loads(args.blockers)
    except ValueError as err:
        return _die(
            "record-fit-assessment: --blockers is not valid JSON: {0}".format(err),
            code=2,
        )
    if not isinstance(blockers_raw, list):
        return _die(
            "record-fit-assessment: --blockers must be a JSON array, got {0}".format(
                type(blockers_raw).__name__
            ),
            code=2,
        )
    for item in blockers_raw:
        if not isinstance(item, str):
            return _die(
                "record-fit-assessment: every blocker must be a string, got {0}".format(
                    type(item).__name__
                ),
                code=2,
            )
    try:
        user_expected = _validate_scalar(args.user_expected, "record-fit-assessment.user_expected")
        reality = _validate_scalar(args.reality, "record-fit-assessment.reality")
    except ValueError as err:
        return _die(str(err), code=2)

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            # Cross-check: touchpoint name must exist in integration_touchpoints.
            existing_names = [
                tp["name"]
                for tp in report.get("integration_touchpoints", [])
                if isinstance(tp, dict) and "name" in tp
            ]
            if args.touchpoint not in existing_names:
                return _die(
                    "fit-assessment touchpoint '{0}' does not match any "
                    "integration_touchpoint name; record-integration-touchpoint first".format(
                        args.touchpoint
                    ),
                    code=2,
                )
            entry = {
                "touchpoint": args.touchpoint,
                "user_expected": user_expected,
                "reality": reality,
                "effort": args.effort,
                "blockers": list(blockers_raw),
            }
            report["fit_assessments"].append(entry)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-fit-assessment: {0}".format(err))
    return 0


def cmd_set_overall_fit(args: argparse.Namespace) -> int:
    """Set report.overall_fit to an OVERALL_FIT_ENUM value.

    --value is validated by argparse choices before this handler runs.
    """
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["overall_fit"] = args.value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-overall-fit: {0}".format(err))
    return 0


def cmd_set_effort_estimate(args: argparse.Namespace) -> int:
    """Set report.effort_estimate to an EFFORT_ENUM value.

    --value is validated by argparse choices before this handler runs.
    """
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["effort_estimate"] = args.value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-effort-estimate: {0}".format(err))
    return 0


def cmd_set_fit_rationale(args: argparse.Namespace) -> int:
    """Set report.fit_rationale to a non-empty string."""
    try:
        value = _validate_scalar(args.value, "set-fit-rationale")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["fit_rationale"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-fit-rationale: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Phase 2 — report-drafting handlers.
# ---------------------------------------------------------------------------


def cmd_set_summary(args: argparse.Namespace) -> int:
    """Set report.summary to a non-empty string."""
    try:
        value = _validate_scalar(args.value, "set-summary")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["summary"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-summary: {0}".format(err))
    return 0


def _decode_string_array(raw: str, flag_name: str) -> Tuple[Optional[List[str]], int]:
    """Decode a JSON array of non-empty strings.

    Returns (list, 0) on success or (None, exit_code) on error.
    Caller must call _die separately — this only returns the code.
    """
    try:
        decoded = json.loads(raw)
    except ValueError as err:
        sys.stderr.write(
            "discover_helper: {0}: not valid JSON: {1}\n".format(flag_name, err)
        )
        return None, 2
    if not isinstance(decoded, list):
        sys.stderr.write(
            "discover_helper: {0}: must be a JSON array, got {1}\n".format(
                flag_name, type(decoded).__name__
            )
        )
        return None, 2
    cleaned = []  # type: List[str]
    for item in decoded:
        if not isinstance(item, str):
            sys.stderr.write(
                "discover_helper: {0}: every item must be a string, got {1}\n".format(
                    flag_name, type(item).__name__
                )
            )
            return None, 2
        if not item.strip():
            sys.stderr.write(
                "discover_helper: {0}: items must be non-empty strings\n".format(flag_name)
            )
            return None, 2
        cleaned.append(item)
    return cleaned, 0


_OPTION_LETTER_PREFIX_RE = re.compile(r"^(option\s+)?[a-z]\s*:\s*", re.IGNORECASE)

_INLINE_ESCAPE_RE = re.compile(r"(?:\\r\\n|\\n|\\r|\\t)+")


def _clean_inline_escapes(value: str) -> str:
    """Collapse literal `\\n` / `\\r` / `\\t` escape sequences to single space.

    Fix F2 — orchestrator-passed setter values sometimes carry literal
    backslash-n substrings from shell-escape leakage; these render as ugly
    literal escapes inside markdown and break shell-quoting on copy-paste of
    `/specify "..."`. Collapse contiguous runs to a single space, then trim
    repeated whitespace.
    """
    if not isinstance(value, str):
        return value
    cleaned = _INLINE_ESCAPE_RE.sub(" ", value)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def cmd_set_design_option(args: argparse.Namespace) -> int:
    """Append one design-option entry to report.design_options.

    --name must be unique among existing entries. --pros and --cons are JSON
    arrays of non-empty strings (at least 1 entry each). --complexity is
    validated by argparse choices. --name must NOT carry a letter prefix
    (`A:`, `Option B:`, `c -`, etc.) — the helper auto-assigns the letter
    based on insertion order during render. A baked-in prefix produces
    `### Option A: A: ...` double-prefix render artifacts.
    """
    try:
        name = _validate_scalar(args.name, "set-design-option.name")
        shape = _validate_scalar(args.shape, "set-design-option.shape")
    except ValueError as err:
        return _die(str(err), code=2)
    if _OPTION_LETTER_PREFIX_RE.match(name):
        return _die(
            "set-design-option: --name {0!r} starts with a letter prefix "
            "(e.g. 'A:', 'Option B:'); helper auto-assigns the letter during "
            "render. Strip the prefix and retry.".format(name),
            code=2,
        )
    pros, code = _decode_string_array(args.pros, "--pros")
    if pros is None:
        return code
    if not pros:
        return _die("set-design-option: --pros must have at least 1 entry", code=2)
    cons, code = _decode_string_array(args.cons, "--cons")
    if cons is None:
        return code
    if not cons:
        return _die("set-design-option: --cons must have at least 1 entry", code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            existing_names = [
                opt["name"]
                for opt in report.get("design_options", [])
                if isinstance(opt, dict) and "name" in opt
            ]
            if name in existing_names:
                return _die(
                    "set-design-option: name {0!r} already exists in design_options; "
                    "use a unique name".format(name),
                    code=2,
                )
            report["design_options"].append({
                "name": name,
                "shape": shape,
                "pros": pros,
                "cons": cons,
                "complexity": args.complexity,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-design-option: {0}".format(err))
    return 0


def cmd_set_recommended_option(args: argparse.Namespace) -> int:
    """Set report.recommended_option; --name must match an existing design_option name."""
    try:
        name = _validate_scalar(args.name, "set-recommended-option.name")
        rationale = _validate_scalar(args.rationale, "set-recommended-option.rationale")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            existing_names = [
                opt["name"]
                for opt in report.get("design_options", [])
                if isinstance(opt, dict) and "name" in opt
            ]
            if name not in existing_names:
                return _die(
                    "recommended-option name {0!r} does not match any design_option.name; "
                    "record design_options first".format(name),
                    code=2,
                )
            report["recommended_option"] = {"name": name, "rationale": rationale}
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-recommended-option: {0}".format(err))
    return 0


def cmd_set_build_vs_buy(args: argparse.Namespace) -> int:
    """Set report.build_vs_buy.

    All four fields required. --recommendation validated by argparse choices.
    """
    try:
        build = _validate_scalar(args.build, "set-build-vs-buy.build")
        buy = _validate_scalar(args.buy, "set-build-vs-buy.buy")
        reasoning = _validate_scalar(args.reasoning, "set-build-vs-buy.reasoning")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["build_vs_buy"] = {
                "build": build,
                "buy": buy,
                "recommendation": args.recommendation,
                "reasoning": reasoning,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-build-vs-buy: {0}".format(err))
    return 0


def cmd_set_derisk_plan(args: argparse.Namespace) -> int:
    """Set report.derisk_plan to a JSON array of non-empty strings."""
    items, code = _decode_string_array(args.items, "--items")
    if items is None:
        return code
    if not items:
        return _die("set-derisk-plan: --items must have at least 1 entry", code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["derisk_plan"] = items
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-derisk-plan: {0}".format(err))
    return 0


def cmd_set_constitution_constraints(args: argparse.Namespace) -> int:
    """Append one entry to report.constitution_constraints. Append-only (not replace)."""
    try:
        rule = _validate_scalar(args.rule, "set-constitution-constraints.rule")
        impact = _validate_scalar(args.impact, "set-constitution-constraints.impact")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["constitution_constraints"].append({"rule": rule, "impact": impact})
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-constitution-constraints: {0}".format(err))
    return 0


def cmd_set_verdict(args: argparse.Namespace) -> int:
    """Set report.verdict. --value validated by argparse choices."""
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["verdict"] = args.value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-verdict: {0}".format(err))
    return 0


def cmd_set_recommendation(args: argparse.Namespace) -> int:
    """Set report.recommendation = {action, next}. Both non-empty."""
    try:
        action = _validate_scalar(args.action, "set-recommendation.action")
        next_text = _validate_scalar(args.next_text, "set-recommendation.next")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["recommendation"] = {"action": action, "next": next_text}
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-recommendation: {0}".format(err))
    return 0


def cmd_set_next_step_text(args: argparse.Namespace) -> int:
    """Compose and set report.next_step_text from memo + report state.

    Composed (no --value). Reads memo.functional_scope, memo.users,
    memo.success_criteria, report.verdict, report.recommended_option,
    memo.topic_slug, report.date, report.gaps. Composes a copy-pasteable
    /specify block and sets report.next_step_text.

    If verdict == 'Reconsider': sets next_step_text = None. Exit 0.
    If any required input is missing: exit 2.
    """
    try:
        memo = _load_memo(args.devforge_dir)
        report = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-next-step-text: {0}".format(err))

    verdict = report.get("verdict")

    if verdict == "Reconsider":
        try:
            with _state_transaction(args.devforge_dir, "report") as rep:
                rep["next_step_text"] = None
        except (OSError, json.JSONDecodeError) as err:
            return _die("set-next-step-text: {0}".format(err))
        return 0

    # Collect required inputs; report all missing at once.
    dims = memo.get("dimensions", {})
    functional_scope_val = (dims.get("functional_scope") or {}).get("value")
    users_val = (dims.get("users") or {}).get("value")
    success_criteria_val = (dims.get("success_criteria") or {}).get("value")
    recommended_option = report.get("recommended_option")
    recommended_name = (recommended_option or {}).get("name") if isinstance(recommended_option, dict) else None

    missing = []  # type: List[str]
    if not functional_scope_val:
        missing.append("memo.functional_scope.value")
    if not users_val:
        missing.append("memo.users.value")
    if not success_criteria_val:
        missing.append("memo.success_criteria.value")
    if not recommended_option:
        missing.append("report.recommended_option")
    elif not recommended_name:
        missing.append("report.recommended_option.name")

    if missing:
        sys.stderr.write(
            "discover_helper: set-next-step-text: missing required input(s): {0}\n".format(
                ", ".join(missing)
            )
        )
        return 2

    # F1: prefer caller-supplied --topic (LLM-distilled 1-2 sentence form);
    # else fall back to first sentence of functional_scope.value split on ". ".
    topic_arg = getattr(args, "topic", None)
    if topic_arg and topic_arg.strip():
        distilled = _clean_inline_escapes(topic_arg.strip())
    else:
        parts = functional_scope_val.split(". ", 1)
        distilled = _clean_inline_escapes(parts[0])

    # F2: strip literal `\n` / `\n\n` escape sequences from setter values before
    # embedding in the next-step block. They render as ugly literal escapes
    # inside markdown and break shell-quoting on copy-paste of /specify "...".
    functional_scope_clean = _clean_inline_escapes(functional_scope_val)
    users_clean = _clean_inline_escapes(users_val)
    success_criteria_clean = _clean_inline_escapes(success_criteria_val)
    recommended_name_clean = _clean_inline_escapes(recommended_name or "")

    date = report.get("date") or memo.get("date") or "unknown-date"
    topic_slug = report.get("topic_slug") or memo.get("topic_slug") or "topic"
    gaps = memo.get("gaps") or []
    gaps_count = len(gaps)

    lines = [
        '/specify "{0}"'.format(distilled),
        "",
        "Discovery reference: discover/{0}-{1}.md".format(date, topic_slug),
        "Key facts:",
        "- Functional scope: {0}".format(functional_scope_clean),
        "- Users: {0}".format(users_clean),
        "- Success criteria: {0}".format(success_criteria_clean),
        "- Recommended option: {0}".format(recommended_name_clean),
        "- Open uncertainties: {0} (see discovery doc §Open uncertainties)".format(gaps_count),
    ]
    composed = "\n".join(lines)

    try:
        with _state_transaction(args.devforge_dir, "report") as rep:
            rep["next_step_text"] = composed
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-next-step-text: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Render helper — table builder.
# ---------------------------------------------------------------------------


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    """Build a Markdown table string (no trailing newline).

    Pipes inside cell values are escaped to \\| to keep table structure valid.
    """
    def _esc(s: str) -> str:
        return str(s).replace("|", "\\|")

    header_row = "| " + " | ".join(_esc(h) for h in headers) + " |"
    sep_row = "|" + "|".join("---" for _ in headers) + "|"
    data_rows = [
        "| " + " | ".join(_esc(cell) for cell in row) + " |"
        for row in rows
    ]
    return "\n".join([header_row, sep_row] + data_rows)


# ---------------------------------------------------------------------------
# Render handler.
# ---------------------------------------------------------------------------

_OPTION_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def cmd_render(args: argparse.Namespace) -> int:
    """Render the full discovery report Markdown to stdout. Read-only.

    Walks the locked schema. Sections are emitted in fixed order regardless
    of field population; sparse sections show placeholder text per spec.
    constitution_constraints section is omitted entirely when empty.
    Open uncertainties section is rendered only when memo.gaps is non-empty.
    """
    try:
        report = _load_report(args.devforge_dir)
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render: {0}".format(err))

    topic = report.get("topic") or "(topic not set)"
    date = report.get("date") or "(date not set)"
    verdict = report.get("verdict") or "(verdict not set)"

    lines = []  # type: List[str]

    # Header block.
    lines.append("# Discovery: {0}".format(topic))
    lines.append("")
    lines.append("**Date**: {0}".format(date))
    lines.append("**Topic**: {0}".format(topic))
    lines.append("**Verdict**: {0}".format(verdict))
    lines.append("")

    # Summary.
    lines.append("## Summary")
    lines.append("")
    summary = report.get("summary")
    lines.append(summary if summary else "*(summary not set)*")
    lines.append("")

    # Prior Art.
    lines.append("## Prior Art")
    lines.append("")
    prior_art = report.get("prior_art") or []
    if prior_art:
        rows = [
            [
                pa.get("reference", ""),
                pa.get("kind", ""),
                pa.get("relevance", ""),
                pa.get("source", ""),
            ]
            for pa in prior_art
        ]
        lines.append(_md_table(
            ["Reference", "Kind", "Relevance", "Source"],
            rows,
        ))
    else:
        lines.append("*No prior-art references recorded.*")
    lines.append("")

    # Integration Surface.
    lines.append("## Integration Surface")
    lines.append("")
    touchpoints = report.get("integration_touchpoints") or []
    if touchpoints:
        rows = [
            [tp.get("name", ""), tp.get("module_path", ""), tp.get("reason", "")]
            for tp in touchpoints
        ]
        lines.append(_md_table(["Touchpoint", "Module/file", "Why touched"], rows))
    else:
        lines.append("*No integration touchpoints recorded.*")
    lines.append("")

    # Fit Assessment.
    lines.append("## Fit Assessment")
    lines.append("")
    fit_assessments = report.get("fit_assessments") or []
    if fit_assessments:
        rows = [
            [
                fa.get("touchpoint", ""),
                fa.get("user_expected", ""),
                fa.get("reality", ""),
                fa.get("effort", ""),
                "; ".join(fa.get("blockers") or []) or "none",
            ]
            for fa in fit_assessments
        ]
        lines.append(_md_table(
            ["Touchpoint", "User expected", "Reality (scan)", "Effort", "Blockers"],
            rows,
        ))
    else:
        lines.append("*No fit assessments recorded.*")
    lines.append("")
    lines.append("**Overall fit**: {0}".format(report.get("overall_fit") or "(not set)"))
    lines.append("**Effort estimate**: {0}".format(report.get("effort_estimate") or "(not set)"))
    lines.append("**Rationale**: {0}".format(report.get("fit_rationale") or "(not set)"))
    lines.append("")

    # Design Options.
    lines.append("## Design Options")
    lines.append("")
    design_options = report.get("design_options") or []
    for i, opt in enumerate(design_options):
        letter = _OPTION_LETTERS[i] if i < len(_OPTION_LETTERS) else str(i + 1)
        lines.append("### Option {0}: {1}".format(letter, opt.get("name", "")))
        lines.append("- **Shape**:")
        lines.append("```")
        lines.append(opt.get("shape", ""))
        lines.append("```")
        pros = opt.get("pros") or []
        lines.append("- **Pros**:")
        for p in pros:
            lines.append("  - {0}".format(p))
        cons = opt.get("cons") or []
        lines.append("- **Cons**:")
        for c in cons:
            lines.append("  - {0}".format(c))
        lines.append("- **Complexity**: {0}".format(opt.get("complexity", "")))
        lines.append("")
    rec_opt = report.get("recommended_option")
    if isinstance(rec_opt, dict) and rec_opt.get("name"):
        lines.append(
            "**Recommended option**: {0} — {1}".format(
                rec_opt["name"], rec_opt.get("rationale", "")
            )
        )
    else:
        lines.append("**Recommended option**: *(not set)*")
    lines.append("")

    # Build vs Buy.
    lines.append("## Build vs Buy")
    lines.append("")
    bvb = report.get("build_vs_buy")
    if isinstance(bvb, dict):
        lines.append(_md_table(
            ["Build", "Buy/Adopt"],
            [[bvb.get("build", ""), bvb.get("buy", "")]],
        ))
        lines.append("")
        lines.append(
            "**Recommendation**: {0} — {1}".format(
                bvb.get("recommendation", ""),
                bvb.get("reasoning", ""),
            )
        )
    else:
        lines.append("*(build vs buy not set)*")
    lines.append("")

    # Derisk Plan.
    lines.append("## Derisk Plan")
    lines.append("")
    derisk = report.get("derisk_plan") or []
    for idx, item in enumerate(derisk, start=1):
        lines.append("{0}. {1}".format(idx, item))
    if not derisk:
        lines.append("*(no derisk plan recorded)*")
    lines.append("")

    # Constitution Constraints — only rendered when non-empty.
    constraints = report.get("constitution_constraints") or []
    if constraints:
        lines.append("## Constitution Constraints")
        lines.append("")
        rows = [
            [c.get("rule", ""), c.get("impact", "")]
            for c in constraints
        ]
        lines.append(_md_table(["Rule", "Impact"], rows))
        lines.append("")

    # Open Uncertainties — only when memo.gaps is non-empty.
    gaps = memo.get("gaps") or []
    if gaps:
        lines.append("## Open uncertainties")
        lines.append("")
        for gap in gaps:
            dimension = gap.get("dimension", "")
            description = gap.get("description", "")
            lines.append(
                "[NEEDS CLARIFICATION: {0} — {1}]".format(dimension, description)
            )
        lines.append("")

    # Recommendation.
    lines.append("## Recommendation")
    lines.append("")
    rec = report.get("recommendation")
    if isinstance(rec, dict):
        lines.append("**Action**: {0}".format(rec.get("action", "")))
        lines.append("**Next**: {0}".format(rec.get("next", "")))
    else:
        lines.append("*(recommendation not set)*")
    lines.append("")

    # Next step — only when next_step_text is not None.
    next_text = report.get("next_step_text")
    if next_text is not None:
        lines.append("## Next step")
        lines.append("")
        lines.append(
            "Copy the block below into a new /specify session manually. "
            "No automated handoff — user controls when /specify runs."
        )
        lines.append("")
        lines.append("~~~")
        lines.append(next_text)
        lines.append("~~~")
        lines.append("")

    output = "\n".join(lines) + "\n"
    sys.stdout.write(output)
    return 0


# ---------------------------------------------------------------------------
# Verify handler.
# ---------------------------------------------------------------------------


def cmd_verify(args: argparse.Namespace) -> int:
    """Cross-field invariant check.

    Rules:
      A. Required-field population under Worth pursuing / Promising with caveats.
      B. Design-options minimum (>=1) under Worth pursuing / Promising with caveats.
      C. Recommended-option name must match a design_option name.
      D. Verdict flip rule: Strained/Misfit overall_fit or Major refactor effort
         requires Reconsider verdict OR memo.override_recorded == True.
         memo.override_recorded is set by scope-finalize --accept-gaps and serves
         dual purpose: (1) user accepted Phase 0 coverage gaps, (2) user accepts
         an unfavorable fit verdict. Document this dual purpose here.
      E. Next-step text: Worth pursuing / Promising with caveats requires non-empty
         next_step_text; Reconsider requires None.
      F. Derisk plan: >=1 entry under Worth pursuing / Promising with caveats.
      G. Internal canonical-pattern cite rule: when any prior_art entry has
         source.startswith("internal:"), the recommended_option.rationale MUST
         contain at least one of those `internal:` file/dir paths as a substring.
         Forces the orchestrator to frame the recommended option as "extend
         existing <path>" rather than "build new <X>" when project-internal
         implementations of the capability already exist.

    Exit 0 only when all rules pass. Exit 2 on any violation.
    """
    try:
        report = _load_report(args.devforge_dir)
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify: {0}".format(err))

    violations = []  # type: List[str]

    verdict = report.get("verdict")
    overall_fit = report.get("overall_fit")
    effort_estimate = report.get("effort_estimate")
    recommended_option = report.get("recommended_option")
    design_options = report.get("design_options") or []
    override_recorded = memo.get("override_recorded", False)
    next_step_text = report.get("next_step_text")

    is_pursue = verdict in ("Worth pursuing", "Promising with caveats")
    is_reconsider = verdict == "Reconsider"

    # Rule A — required-field population.
    if is_pursue:
        required_fields = {
            "summary": report.get("summary"),
            "verdict": verdict,
            "overall_fit": overall_fit,
            "effort_estimate": effort_estimate,
            "fit_rationale": report.get("fit_rationale"),
            "recommended_option": recommended_option,
            "build_vs_buy": report.get("build_vs_buy"),
            "recommendation": report.get("recommendation"),
        }
        missing_fields = [
            k for k, v in required_fields.items()
            if v is None or (isinstance(v, str) and not v.strip())
        ]
        if missing_fields:
            violations.append(
                "A: required fields not set for verdict '{0}': {1}".format(
                    verdict, ", ".join(missing_fields)
                )
            )
    elif is_reconsider:
        # Only summary, verdict, recommendation required.
        rec_fields = {
            "summary": report.get("summary"),
            "verdict": verdict,
            "recommendation": report.get("recommendation"),
        }
        missing_fields = [
            k for k, v in rec_fields.items()
            if v is None or (isinstance(v, str) and not v.strip())
        ]
        if missing_fields:
            violations.append(
                "A: required fields not set for verdict 'Reconsider': {0}".format(
                    ", ".join(missing_fields)
                )
            )

    # Rule B — design-options minimum.
    if is_pursue and len(design_options) < 1:
        violations.append(
            "B: at least 1 design_option required when verdict is '{0}'; "
            "none recorded".format(verdict)
        )

    # Rule C — recommended-option name match.
    if isinstance(recommended_option, dict) and recommended_option.get("name"):
        rec_name = recommended_option["name"]
        existing_names = [
            opt["name"]
            for opt in design_options
            if isinstance(opt, dict) and "name" in opt
        ]
        if rec_name not in existing_names:
            violations.append(
                "C: recommended_option.name {0!r} does not match any design_option.name "
                "(design_options names: {1})".format(
                    rec_name,
                    ", ".join(repr(n) for n in existing_names) if existing_names else "(none)",
                )
            )

    # Rule D — verdict flip rule.
    if overall_fit in ("Strained", "Misfit") and not is_reconsider and not override_recorded:
        violations.append(
            "D: Verdict flip rule: overall_fit is '{0}' but verdict is '{1}'; "
            "flip to Reconsider OR record an override "
            "(scope-finalize --accept-gaps records one).".format(overall_fit, verdict)
        )
    if (
        effort_estimate == "Major refactor required"
        and not is_reconsider
        and not override_recorded
    ):
        violations.append(
            "D: Verdict flip rule: effort_estimate is 'Major refactor required' "
            "but verdict is '{0}'; flip to Reconsider OR record an override.".format(verdict)
        )

    # Rule E — next-step text presence.
    if is_pursue:
        if not next_step_text or not (isinstance(next_step_text, str) and next_step_text.strip()):
            violations.append(
                "E: verdict is '{0}' but next_step_text is not set; "
                "run set-next-step-text.".format(verdict)
            )
    elif is_reconsider:
        if next_step_text is not None:
            violations.append(
                "E: verdict is 'Reconsider' but next_step_text is set (must be None); "
                "run set-next-step-text to clear it."
            )

    # Rule F — derisk plan.
    if is_pursue and len(report.get("derisk_plan") or []) < 1:
        violations.append(
            "F: at least 1 derisk_plan entry required when verdict is '{0}'; "
            "none recorded".format(verdict)
        )

    # Rule G — internal canonical-pattern cite rule.
    prior_art = report.get("prior_art") or []
    internal_sources = []  # type: List[str]
    for entry in prior_art:
        if not isinstance(entry, dict):
            continue
        source = entry.get("source") or ""
        if isinstance(source, str) and source.startswith("internal:"):
            path = source[len("internal:"):].strip()
            if path:
                internal_sources.append(path)
    if (
        internal_sources
        and isinstance(recommended_option, dict)
        and recommended_option.get("name")
    ):
        rationale = recommended_option.get("rationale") or ""
        if not isinstance(rationale, str) or not any(
            path in rationale for path in internal_sources
        ):
            violations.append(
                "G: Internal canonical-pattern cite rule: prior_art has {0} "
                "entry(ies) with source 'internal:<path>' but recommended_option.rationale "
                "does not cite any of: {1}. Reframe rationale as 'extend existing <path>' "
                "or explicitly state which capability the existing implementation does NOT "
                "cover.".format(
                    len(internal_sources),
                    ", ".join(repr(p) for p in internal_sources),
                )
            )

    if violations:
        for v in violations:
            sys.stderr.write("verify: {0}\n".format(v))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
