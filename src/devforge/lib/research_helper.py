"""research_helper — state + render helper for /research.

Owns the shape of two state files under .devforge/ and the rendered
research report md. Mirrors the helper-owns-shape pattern from
init_helper / configure_helper / constitute_helper.

State files
-----------

  .devforge/research-state.json   — Phase 0 SymptomMemo (rubric Q&A).
  .devforge/research-report.json  — Phase 1 + 2 ResearchReport (findings,
                                    hypotheses, approaches, verdict, etc).

Each has its own state-transaction context so memo and report progress
independently. Phase 0 finalizes (symptom-finalize → exit 0) before
Phase 1 dispatch; Phase 1+2 build on a frozen memo snapshot.

Phases (target order per REDESIGN-RESEARCH-PLAN.md)
---------------------------------------------------

  PHASE 0  Symptom clarification     — 6 rubric dimensions, mode detection,
                                       conflict detection, gaps recording.
  PHASE 1  Investigation             — findings, hypotheses (≥2 enforced),
                                       structured root cause (bug-mode),
                                       verify-step (3 sub-fields).
  PHASE 2  Report drafting           — approaches, recommended approach,
                                       constitution constraints, complexity,
                                       verdict (mode-aware enum), summary,
                                       next-step text.
  PHASE 3  Save + recommend          — render artifact + ask-to-save handled
                                       by orchestrator; helper renders + verifies.

Subcommand summary (43)
-----------------------

  Plumbing (8)   reset-memo, reset-report, read-memo, read-report,
                 preflight, summary, set-topic, set-date
  Phase 0  (12)  set-symptom, set-affected-area, set-repro-or-current,
                 set-desired, set-scope, set-unchanged-behavior,
                 detect-mode, record-gap, check-conflicts,
                 record-conflict-resolution, symptom-coverage,
                 symptom-finalize
  Phase 2.3b (1) record-runner-up-framing
  Phase 2.4c (5) record-fix-path-helper, record-inbound-caller,
                 record-dead-sibling, record-consumer-chain,
                 set-value-semantics
  Phase 1  (8)   record-finding, record-hypothesis,
                 set-root-cause-hypothesis, set-confidence,
                 set-trigger, set-root-cause-systemic,
                 record-contributing-factor, set-verify-step
  Phase 2  (9)   set-approach, set-recommended-approach,
                 set-constitution-constraints, set-complexity,
                 set-verdict, set-summary, set-next-step-text,
                 render, verify

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import contextlib
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

MEMO_FILE_NAME = "research-state.json"
REPORT_FILE_NAME = "research-report.json"

# Phase 0 rubric — 6 dimensions, neutral over bug vs enhancement. Locked
# order: this is the order symptom-coverage emits, render uses, and tests
# verify.
RUBRIC_DIMENSIONS = (
    "symptom",
    "affected_area",
    "repro_or_current",
    "desired",
    "scope",
    "unchanged_behavior",
)

# Per-dimension state machine. Helper transitions Missing→Partial→Clear
# as setters fire; "Partial" is reached when a dimension has a value but
# the bounded-turn cap (TURN_CAP) has been hit without explicit Clear.
RUBRIC_STATE_ENUM = ("Clear", "Partial", "Missing")
RUBRIC_STATE_DEFAULT = "Missing"

# Bounded follow-ups per dimension. Plan §"Bounded turns": 2 follow-ups
# per dimension (lighter than /discover's 3). After cap, dimension logs
# as Partial.
TURN_CAP = 2

# Mode enum (auto-detected from symptom tokens or user-set via override).
MODE_ENUM = ("bug", "enhancement")

# Confidence enum (Phase 1).
CONFIDENCE_ENUM = ("Confirmed", "Hypothesis", "Speculative")

# Verdict enum, mode-aware. Helper `set-verdict` enforces value ∈
# verdicts-allowed-for-current-mode; non-zero exit on mismatch.
VERDICT_ENUM = {
    "bug": (
        "Root cause confirmed",
        "Root cause hypothesis (needs repro)",
        "Multiple plausible causes",
    ),
    "enhancement": (
        "Feasible",
        "Feasible with caveats",
        "Not Recommended",
    ),
}

# Verdict subset that allows proceeding to /specify — next-step text emits
# only on these values.
VERDICT_PROCEEDING = {
    "bug": {"Root cause confirmed", "Root cause hypothesis (needs repro)"},
    "enhancement": {"Feasible", "Feasible with caveats"},
}

# Complexity rating enum (used in 3 sub-fields: codebase_changes, risk,
# verify_cost).
COMPLEXITY_ENUM = ("Low", "Med", "High")

# Confidence-vs-primary enum for runner-up framing.
CONFIDENCE_VS_PRIMARY_ENUM = ("lower", "comparable", "higher")

# Framing tag enum for findings.
FRAMING_ENUM = ("primary", "runner-up")

# Conflict type enum (Phase 0 misalignment detection).
CONFLICT_TYPE_ENUM = ("direct", "drift", "refinement", "mode-flip")

# Hard-gate prerequisites checked by `preflight` subcommand. Tuple of
# (relative-path-from-install-root, label). Order matters for stderr
# enumeration. constitution.md lives at install-root; the rest under
# .devforge/ + docs/.
PREFLIGHT_PREREQS = (
    (".devforge/init.yaml", "/init-forge"),
    ("docs/architecture.md", "/generate-docs"),
    (".devforge/configure.yaml", "/configure"),
    ("constitution.md", "/constitute"),
)

# Mode detection tokens. Case-insensitive substring match against the
# symptom field. Mixed-signal (both sets hit) → returns None and
# orchestrator asks user to disambiguate.
_BUG_TOKENS = (
    "fail", "broken", "wrong", "missing", "error",
    "crash", "bug", "regress", "doesn't work", "not working",
    "freezes", "hangs", "stuck",
)
_ENHANCEMENT_TOKENS = (
    "slow", "faster", "optimize", "support", "add",
    "integrate", "should", "enhance", "improve", "expand",
    "extend",
)


# ---------------------------------------------------------------------------
# Default-state builders.
# ---------------------------------------------------------------------------


def _empty_dimension() -> dict:
    """Return a fresh rubric-dimension record."""
    return {"value": None, "state": RUBRIC_STATE_DEFAULT, "turns": 0}


def default_memo_state() -> dict:
    """Return a fresh SymptomMemo state matching schema."""
    return {
        "mode": None,
        "topic_slug": None,
        "dimensions": {d: _empty_dimension() for d in RUBRIC_DIMENSIONS},
        "gaps": [],
        "override_recorded": False,
        "conflicts": [],
    }


def default_report_state() -> dict:
    """Return a fresh ResearchReport state matching schema.

    Mirrors SymptomMemo by copying mode + symptom snapshot at Phase 1
    dispatch time; orchestrator is responsible for snapshotting.
    """
    return {
        "topic": None,
        "date": None,
        "mode": None,
        "symptom_snapshot": {d: None for d in RUBRIC_DIMENSIONS},
        "summary": None,
        "findings": [],
        "hypotheses": [],
        "root_cause_hypothesis": None,
        "confidence": None,
        "structured_root_cause": None,
        "verify_step": None,
        "approaches": [],
        "recommended_approach": None,
        "constitution_constraints": [],
        "complexity": None,
        "open_uncertainties": [],
        "verdict": None,
        "next_step_text": None,
        # Phase 2.3b — runner-up framing. None until record-runner-up-framing fires;
        # overwritten (last call wins) if called more than once.
        "runner_up_framing": None,
        # Phase 2.4c — helper-API surface enumeration fields.
        "fix_path_helpers": [],
        "inbound_callers": [],
        "dead_siblings": [],
        "consumer_chain": [],
        "value_semantics": [],
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
        prefix="research-",
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
    """Load research-state.json. Missing → default_memo_state()."""
    path = _memo_path(devforge_dir)
    if not path.exists():
        return default_memo_state()
    return json.loads(path.read_text(encoding="utf-8"))


def _load_report(devforge_dir: Union[str, "os.PathLike[str]"]) -> dict:
    """Load research-report.json. Missing → default_report_state()."""
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

    `which` ∈ {"memo", "report"}. On POSIX, fcntl.flock(LOCK_EX) on the
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
    sys.stderr.write("research_helper: {0}\n".format(message))
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


def _validate_enum(value: str, field_name: str, allowed: tuple) -> str:
    """Case-insensitive match → canonical-cased member of allowed.

    Raises ValueError if empty or no match (enumerates allowed in message).
    """
    stripped = _validate_scalar(value, field_name)
    if stripped in allowed:
        return stripped
    lower_to_canonical = {member.lower(): member for member in allowed}
    if stripped.lower() in lower_to_canonical:
        return lower_to_canonical[stripped.lower()]
    raise ValueError(
        "{0}: invalid value {1!r}; allowed: {2}".format(
            field_name, stripped, list(allowed)
        )
    )


def _validate_string_array_json(value: str, field_name: str) -> List[str]:
    """Parse value as JSON array of strings. Reject empty array / non-string items.

    Used for fields where items may contain commas (rule text, hypothesis
    falsifier). Caller passes a JSON-array string like '["a", "b"]'.
    """
    try:
        decoded = json.loads(value)
    except ValueError as err:
        raise ValueError(
            "{0}: JSON-array form is malformed: {1}".format(field_name, err)
        )
    if not isinstance(decoded, list):
        raise ValueError(
            "{0}: must decode to a list, got {1}".format(
                field_name, type(decoded).__name__
            )
        )
    out = []
    for item in decoded:
        if not isinstance(item, str):
            raise ValueError(
                "{0}: items must be strings, got {1}".format(
                    field_name, type(item).__name__
                )
            )
        stripped = item.strip()
        if not stripped:
            raise ValueError("{0}: item cannot be empty".format(field_name))
        out.append(stripped)
    return out


def _validate_verbatim(value: str, field_name: str) -> str:
    """Reject all-whitespace; preserve internal whitespace verbatim.

    Used for multi-line fields (summary, root-cause-hypothesis, code blocks)
    where leading/trailing newlines matter for round-trip.
    """
    if not value.strip():
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return value


def _validate_file_line(value: str, field_name: str) -> str:
    """Validate path:line format OR literal sentinel '(none)'.

    Accepted forms:
      - The literal string "(none)" (sentinel meaning no grounding available).
      - "<non-empty-path>:<positive-integer>" — e.g. "src/foo.ts:42".

    Raises ValueError on any other form.
    """
    stripped = value.strip()
    if stripped == "(none)":
        return stripped
    # Must contain at least one colon separator.
    colon_idx = stripped.rfind(":")
    if colon_idx <= 0:
        raise ValueError(
            "{0}: must be '<path>:<line>' or '(none)', got {1!r}".format(field_name, stripped)
        )
    path_part = stripped[:colon_idx]
    line_part = stripped[colon_idx + 1:]
    if not path_part:
        raise ValueError(
            "{0}: path portion is empty in {1!r}".format(field_name, stripped)
        )
    try:
        line_num = int(line_part)
    except ValueError:
        raise ValueError(
            "{0}: line portion {2!r} is not an integer in {1!r}".format(
                field_name, stripped, line_part
            )
        )
    if line_num <= 0:
        raise ValueError(
            "{0}: line number must be positive, got {1} in {2!r}".format(
                field_name, line_num, stripped
            )
        )
    return stripped


# ---------------------------------------------------------------------------
# Layer-boundary path utilities (used by check 8b in cmd_verify).
# ---------------------------------------------------------------------------

# Presentation-layer file extensions.
_PRESENTATION_EXTENSIONS = {".vue", ".tsx", ".jsx"}

# Presentation-layer path fragments — must appear as full path components
# (i.e., preceded by '/') to avoid matching 'subviews/' when '/views/' is
# the intended sentinel.
_PRESENTATION_PATH_FRAGMENTS = ("/views/", "/components/", "/pages/", "/screens/", "/ui/")

# Presentation-layer path prefixes (normalized, no leading slash).
_PRESENTATION_PATH_PREFIXES = ("apps/app-web/", "apps/web/", "apps/frontend/")


def _is_presentation_layer(file_path: str) -> bool:
    """Return True iff file_path is a presentation-layer file.

    Heuristics (case-sensitive, in order):
    1. Extension ∈ {.vue, .tsx, .jsx}.
    2. Normalized path contains a presentation fragment (/views/, /components/,
       /pages/, /screens/, /ui/) — the leading '/' guards against false matches
       on e.g. 'subviews/'.
    3. Normalized path starts with a presentation prefix (apps/app-web/, etc.).

    None or empty → False.
    """
    if not file_path:
        return False
    # Extension check.
    _, ext = os.path.splitext(file_path)
    if ext in _PRESENTATION_EXTENSIONS:
        return True
    # Normalize: strip leading './' but keep leading '/' so fragment checks work.
    normalized = file_path
    if normalized.startswith("./"):
        normalized = normalized[2:]
    # Prepend '/' so fragment checks work on paths that start at the first
    # component (e.g. 'src/views/Foo.ts' → '/src/views/Foo.ts').
    slashed = "/" + normalized if not normalized.startswith("/") else normalized
    for frag in _PRESENTATION_PATH_FRAGMENTS:
        if frag in slashed:
            return True
    # Prefix check against normalized (leading '/' already stripped by logic above).
    normed_no_slash = normalized.lstrip("/")
    for prefix in _PRESENTATION_PATH_PREFIXES:
        if normed_no_slash.startswith(prefix):
            return True
    return False


def _extract_package(file_path: str) -> str:
    """Derive a two-component package key from file_path.

    Rules:
    - Strip a leading '/' or './' prefix.
    - Split on '/'; take the first two components when both are present.
    - When only one component exists (no '/'), return it as-is.
    - None, empty, or whitespace-only → empty string.

    Examples:
      'apps/app-web/src/foo.vue' → 'apps/app-web'
      'pkg-cse-core/utils.ts'    → 'pkg-cse-core'  (file at index 1)
      'src/admin/Products.vue'   → 'src/admin'
      'foo.vue'                  → 'foo.vue'
      './apps/web/x.ts'          → 'apps/web'
      '/apps/web/x.ts'           → 'apps/web'
      ''                         → ''
    """
    if not file_path or not file_path.strip():
        return ""
    # Strip leading './' or '/'.
    normalized = file_path
    if normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    parts = normalized.split("/")
    # Filter out empty segments (shouldn't arise after strip, but be safe).
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if len(parts) == 1:
        # Single component — no directory structure, return as-is.
        return parts[0]
    # Two components: if the second is a file (contains '.'), the first
    # component IS the package (flat-package layout like pkg-cse-core/utils.ts).
    # If the second has no dot it's a directory → return both (src/admin).
    if len(parts) == 2 and "." in parts[1]:
        return parts[0]
    # Three or more components, or two components where the second is a
    # directory: return first two.
    return parts[0] + "/" + parts[1]


# ---------------------------------------------------------------------------
# Check 8b predicate — shared between cmd_verify and cmd_set_recommended_approach.
# ---------------------------------------------------------------------------


def _compute_check_8b_would_fire(report: dict, bug_mode: bool) -> bool:
    """Return True iff check 8b's conditions are fully met.

    Conditions (all must hold):
    - bug_mode is True
    - fix_path_helpers is non-empty
    - The first primary finding's file_line resolves to a presentation-layer path
      (per _is_presentation_layer)
    - Every fix_path_helper's file_line resolves to the SAME package as the
      primary symptom (i.e., no helper crosses a package boundary)

    Used by cmd_verify (to decide whether check 13 is suppressed) and by
    cmd_set_recommended_approach (to decide whether the single-layer gate
    should be enforced). When check 8b would fire, check 13 / the setter gate
    are structurally unavailable — the LLM's only recovery path is to add
    cross-layer helpers, not to supply single_layer_justification.
    """
    if not bug_mode:
        return False
    fix_path_helpers = report.get("fix_path_helpers") or []
    if not fix_path_helpers:
        return False
    # Identify the primary symptom path from findings.
    primary_path = None  # type: Optional[str]
    for f in (report.get("findings") or []):
        framing_val = f.get("framing") or "primary"
        if framing_val == "primary":
            fl = f.get("file_line") or ""
            colon_pos = fl.rfind(":")
            primary_path = fl[:colon_pos] if colon_pos > 0 else (fl if fl else None)
            break
    if not primary_path or not _is_presentation_layer(primary_path):
        return False
    symptom_pkg = _extract_package(primary_path)
    # All helpers must be in the same package as the symptom for 8b to fire.
    for h in fix_path_helpers:
        if not isinstance(h, dict):
            continue
        helper_file_line = h.get("file_line") or ""
        colon_pos = helper_file_line.rfind(":")
        helper_file = helper_file_line[:colon_pos] if colon_pos > 0 else helper_file_line
        if _extract_package(helper_file) != symptom_pkg:
            return False
    return True


# ---------------------------------------------------------------------------
# Topic slug derivation (used for filename + state record).
# ---------------------------------------------------------------------------


_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def derive_topic_slug(topic: str, max_words: int = 4) -> str:
    """Lowercase + kebab-case + truncate to N words.

    Empty input or no-alnum-chars → "topic" as fallback. Used for
    research/YYYY-MM-DD-<slug>.md filename + memo.topic_slug field.
    """
    lowered = topic.lower().strip()
    cleaned = _SLUG_NON_ALNUM.sub("-", lowered).strip("-")
    if not cleaned:
        return "topic"
    parts = [p for p in cleaned.split("-") if p]
    if not parts:
        return "topic"
    return "-".join(parts[:max_words])


# ---------------------------------------------------------------------------
# Mode detection (token-overlap; deterministic, no LLM).
# ---------------------------------------------------------------------------


def detect_mode_from_symptom(symptom_text: str) -> Optional[str]:
    """Return "bug" / "enhancement" / None based on token presence.

    "bug" if at least one bug token and no enhancement tokens.
    "enhancement" if at least one enhancement token and no bug tokens.
    None if both sets hit (mixed-signal — orchestrator asks user) OR
    neither set hits (no signal — orchestrator asks user).
    """
    if not symptom_text:
        return None
    lower = symptom_text.lower()
    bug_hit = any(tok in lower for tok in _BUG_TOKENS)
    enh_hit = any(tok in lower for tok in _ENHANCEMENT_TOKENS)
    if bug_hit and not enh_hit:
        return "bug"
    if enh_hit and not bug_hit:
        return "enhancement"
    return None


# ---------------------------------------------------------------------------
# Conflict detection (token-overlap rules; deterministic).
# ---------------------------------------------------------------------------

# Antagonist regex pairs. Each entry: (dim_a, regex_a, dim_b, regex_b,
# description). Detector reports a conflict when BOTH regexes match
# their respective dimensions' values. Patterns are case-insensitive.
# Intentionally short list — covers the most common contradictions for
# UI/data symptoms. Extend as empirical data surfaces new pairs.
_CONFLICT_PATTERNS: Tuple[Tuple[str, str, str, str, str], ...] = (
    # alphabetical sort vs numeric/insertion order regression scope
    (
        "desired", r"\b(alphabetical|alpha\s*sort|name[- ]?sort|a[-→ ]+z)\b",
        "unchanged_behavior", r"\b(numeric|insert(ion)?|current|original)\s+order\b",
        "alphabetical sort would replace numeric/insertion order listed as unchanged",
    ),
    # ascending vs descending
    (
        "desired", r"\bascending\b",
        "unchanged_behavior", r"\bdescending\b",
        "ascending sort contradicts descending order required in unchanged behavior",
    ),
    (
        "desired", r"\bdescending\b",
        "unchanged_behavior", r"\bascending\b",
        "descending sort contradicts ascending order required in unchanged behavior",
    ),
    # async migration vs sync requirement
    (
        "desired", r"\basync(hronous)?\b",
        "unchanged_behavior", r"\bsync(hronous)?\b",
        "async transition contradicts synchronous requirement in unchanged behavior",
    ),
    # speed increase vs latency budget
    (
        "desired", r"\b(under|less than|<)\s*\d+\s*(ms|s|sec|second)",
        "unchanged_behavior", r"\b(under|less than|<)\s*\d+\s*(ms|s|sec|second)",
        "two conflicting latency budgets between desired and unchanged",
    ),
)


def detect_direct_conflicts(memo: dict) -> List[dict]:
    """Scan memo dimensions for direct contradictions; return conflict records.

    Each returned dict matches Conflict schema (type=direct). Used by
    `check-conflicts` setter to surface hard-block items to the
    orchestrator. Refinement / drift / mode-flip live in LLM-side logic;
    the helper only catches deterministic value-on-value contradictions.
    """
    conflicts = []  # type: List[dict]
    dims = memo.get("dimensions", {})

    def _val(name: str) -> str:
        rec = dims.get(name, {})
        if not isinstance(rec, dict):
            return ""
        v = rec.get("value")
        return v if isinstance(v, str) else ""

    for dim_a, rx_a, dim_b, rx_b, desc in _CONFLICT_PATTERNS:
        val_a = _val(dim_a)
        val_b = _val(dim_b)
        if not val_a or not val_b:
            continue
        if re.search(rx_a, val_a, re.IGNORECASE) and re.search(rx_b, val_b, re.IGNORECASE):
            conflicts.append(
                {
                    "type": "direct",
                    "dimensions": [dim_a, dim_b],
                    "description": desc,
                    "resolution": "blocked-pending-user",
                }
            )
    return conflicts


# ---------------------------------------------------------------------------
# Coverage helper (used by symptom-coverage + symptom-finalize).
# ---------------------------------------------------------------------------


def _compute_coverage(memo: dict) -> Tuple[Dict[str, str], int, int, int]:
    """Return (per-dim state map, clear_count, partial_count, missing_count).

    State per dim: derived from the stored {state, turns, value} record.
    Missing → no value yet. Partial → has value but turns >= cap with no
    explicit Clear marker, OR explicitly set to Partial. Clear → set to Clear.
    """
    dims = memo.get("dimensions", {})
    state_map = {}
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
# Argparse + main — populated after subcommand handlers.
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research_helper",
        description="State + render helper for /research. Owns research artifact shape.",
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
    """All cmd_* handlers attached here. Implemented below."""
    # Plumbing
    sp = subparsers.add_parser("reset-memo", help="Write a fresh defaults memo state.")
    sp.set_defaults(func=cmd_reset_memo)

    sp = subparsers.add_parser("reset-report", help="Write a fresh defaults report state.")
    sp.set_defaults(func=cmd_reset_report)

    sp = subparsers.add_parser("read-memo", help="Print research-state.json (or defaults) as JSON.")
    sp.set_defaults(func=cmd_read_memo)

    sp = subparsers.add_parser("read-report", help="Print research-report.json (or defaults) as JSON.")
    sp.set_defaults(func=cmd_read_report)

    sp = subparsers.add_parser(
        "preflight",
        help="Hard-gate check: 4 setup-chain artefacts present + non-empty.",
    )
    sp.set_defaults(func=cmd_preflight)

    sp = subparsers.add_parser(
        "set-topic",
        help="Set report.topic + auto-derive memo.topic_slug.",
    )
    sp.add_argument("--value", required=True, help="Topic text (user's original input).")
    sp.set_defaults(func=cmd_set_topic)

    sp = subparsers.add_parser(
        "set-date",
        help="Set report.date (YYYY-MM-DD).",
    )
    sp.add_argument("--value", required=True, help="Date in YYYY-MM-DD format.")
    sp.set_defaults(func=cmd_set_date)

    sp = subparsers.add_parser(
        "summary",
        help="Render combined memo + report summary to stdout. Read-only.",
    )
    sp.set_defaults(func=cmd_summary)

    # Phase 0 setters — 5 non-scope dims built uniformly in the loop;
    # scope built separately below with the evidence gate.
    for dim in RUBRIC_DIMENSIONS:
        if dim == "scope":
            continue
        sp_name = "set-" + dim.replace("_", "-")
        sp = subparsers.add_parser(sp_name, help="Set {0} dimension.".format(dim))
        sp.add_argument("--value", required=True, help="Value text (verbatim).")
        sp.add_argument(
            "--state",
            default="Clear",
            choices=list(RUBRIC_STATE_ENUM),
            help="State after this set (default: Clear).",
        )
        sp.add_argument(
            "--increment-turn",
            action="store_true",
            help="Increment turn counter (use for follow-ups that didn't fully clear).",
        )
        sp.set_defaults(func=_make_dim_setter(dim))

    # Scope setter — special-cased to add --evidence gate for "one place".
    sp = subparsers.add_parser(
        "set-scope",
        help=(
            "Set scope dimension. "
            "--evidence is required when --value normalizes to 'one place'."
        ),
    )
    sp.add_argument("--value", required=True, help="Value text (verbatim).")
    sp.add_argument(
        "--state",
        default="Clear",
        choices=list(RUBRIC_STATE_ENUM),
        help="State after this set (default: Clear).",
    )
    sp.add_argument(
        "--increment-turn",
        action="store_true",
        help="Increment turn counter (use for follow-ups that didn't fully clear).",
    )
    sp.add_argument(
        "--evidence",
        default=None,
        help=(
            "file:line citation proving the bug is localized. "
            "Required when --value normalizes to 'one place'; ignored otherwise."
        ),
    )
    sp.set_defaults(func=_make_scope_setter())

    sp = subparsers.add_parser(
        "detect-mode",
        help="Detect bug vs enhancement from symptom tokens, optionally with --override.",
    )
    sp.add_argument("--override", default=None, choices=list(MODE_ENUM), help="Force a mode.")
    sp.set_defaults(func=cmd_detect_mode)

    sp = subparsers.add_parser(
        "record-gap",
        help="Record a [NEEDS CLARIFICATION] gap for a dimension and accept exit.",
    )
    sp.add_argument("--dimension", required=True, choices=list(RUBRIC_DIMENSIONS))
    sp.add_argument("--description", required=True, help="Gap description.")
    sp.set_defaults(func=cmd_record_gap)

    sp = subparsers.add_parser(
        "check-conflicts",
        help="Scan dimensions for direct contradictions; emit JSON list.",
    )
    sp.set_defaults(func=cmd_check_conflicts)

    sp = subparsers.add_parser(
        "record-conflict-resolution",
        help="Log user resolution for a previously detected conflict.",
    )
    sp.add_argument("--index", required=True, type=int, help="0-based index into conflicts list.")
    sp.add_argument("--resolution", required=True, help="Resolution label.")
    sp.add_argument(
        "--rewrite-dimension",
        default=None,
        choices=list(RUBRIC_DIMENSIONS),
        help="Optional dimension whose value to clear (loser of direct conflict).",
    )
    sp.set_defaults(func=cmd_record_conflict_resolution)

    sp = subparsers.add_parser(
        "symptom-coverage",
        help="Emit JSON coverage map per dimension + counts.",
    )
    sp.set_defaults(func=cmd_symptom_coverage)

    sp = subparsers.add_parser(
        "symptom-finalize",
        help=(
            "Validate memo: all Clear OR override_recorded; no blocked conflicts. "
            "Exit 0 = ready for Phase 1; non-zero otherwise."
        ),
    )
    sp.add_argument(
        "--accept-gaps",
        action="store_true",
        help="User explicitly accepted Partial/Missing dimensions; record override.",
    )
    sp.set_defaults(func=cmd_symptom_finalize)

    # Phase 1 setters
    sp = subparsers.add_parser(
        "record-finding",
        help="Append a {surface, file_line, relevance, framing} Finding to report.findings.",
    )
    sp.add_argument("--surface", required=True)
    sp.add_argument("--file-line", required=True, dest="file_line")
    sp.add_argument("--relevance", required=True)
    sp.add_argument(
        "--framing",
        default="primary",
        choices=list(FRAMING_ENUM),
        dest="framing",
        help="Which framing this finding supports (default: primary).",
    )
    sp.set_defaults(func=cmd_record_finding)

    sp = subparsers.add_parser(
        "record-runner-up-framing",
        help=(
            "Set report.runner_up_framing {frame, falsifier, confidence_vs_primary}. "
            "Overwrites any prior value (last call wins). "
            "Required before Phase 2.4 searches start."
        ),
    )
    sp.add_argument("--frame", required=True, dest="frame",
                    help="One-sentence alternative root cause.")
    sp.add_argument("--falsifier", required=True, dest="falsifier",
                    help="Concrete evidence that would confirm this framing over the primary.")
    sp.add_argument(
        "--confidence-vs-primary",
        required=True,
        dest="confidence_vs_primary",
        choices=list(CONFIDENCE_VS_PRIMARY_ENUM),
        help="Confidence of runner-up vs primary: lower|comparable|higher.",
    )
    sp.set_defaults(func=cmd_record_runner_up_framing)

    sp = subparsers.add_parser(
        "record-hypothesis",
        help="Append a {cause, falsifier, runtime_probe_needed} Hypothesis to report.hypotheses.",
    )
    sp.add_argument("--cause", required=True)
    sp.add_argument("--falsifier", required=True)
    sp.add_argument(
        "--runtime-probe-needed",
        choices=("yes", "no"),
        required=True,
        dest="runtime_probe_needed",
    )
    sp.set_defaults(func=cmd_record_hypothesis)

    sp = subparsers.add_parser(
        "set-root-cause-hypothesis",
        help="Set primary root-cause-hypothesis text on report.",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_root_cause_hypothesis)

    sp = subparsers.add_parser(
        "set-confidence",
        help="Set confidence enum (Confirmed | Hypothesis | Speculative).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_confidence)

    sp = subparsers.add_parser(
        "set-trigger",
        help="Set structured-root-cause trigger (bug-mode + confidence ≥ Hypothesis only).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_trigger)

    sp = subparsers.add_parser(
        "set-root-cause-systemic",
        help="Set structured-root-cause systemic flaw (bug-mode + confidence ≥ Hypothesis only).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_root_cause_systemic)

    sp = subparsers.add_parser(
        "record-contributing-factor",
        help="Append a contributing factor (bug-mode + confidence ≥ Hypothesis; max 3).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_record_contributing_factor)

    sp = subparsers.add_parser(
        "set-verify-step",
        help="Set verify-step 3 sub-fields (probe + reproduction + discriminator).",
    )
    sp.add_argument("--probe", required=True)
    sp.add_argument("--reproduction", required=True)
    sp.add_argument("--discriminator", required=True)
    sp.set_defaults(func=cmd_set_verify_step)

    # Phase 2 setters
    sp = subparsers.add_parser(
        "set-approach",
        help="Append an Approach to report.approaches.",
    )
    sp.add_argument("--name", required=True)
    sp.add_argument("--description", required=True)
    sp.add_argument(
        "--addresses-hypotheses",
        required=True,
        dest="addresses",
        help='JSON array of hypothesis-index strings (e.g. ["A","B"]).',
    )
    sp.add_argument(
        "--does-not-cover",
        required=True,
        dest="does_not_cover",
        help='JSON array of hypothesis-index strings.',
    )
    sp.add_argument("--pros", required=True, help='JSON array of pros strings.')
    sp.add_argument("--cons", required=True, help='JSON array of cons strings.')
    sp.add_argument("--complexity", required=True, choices=list(COMPLEXITY_ENUM))
    sp.set_defaults(func=cmd_set_approach)

    sp = subparsers.add_parser(
        "set-recommended-approach",
        help="Set recommended approach. Must cite hypotheses + respect unchanged_behavior.",
    )
    sp.add_argument("--name", required=True, help="Must match an existing approach.name.")
    sp.add_argument("--rationale", required=True)
    sp.add_argument(
        "--hypotheses-addressed",
        required=True,
        dest="hypotheses_addressed",
        help="JSON array of hypothesis-index strings.",
    )
    sp.add_argument(
        "--hypotheses-not-covered",
        required=True,
        dest="hypotheses_not_covered",
        help="JSON array of hypothesis-index strings.",
    )
    sp.add_argument(
        "--single-layer-justification",
        default=None,
        dest="single_layer_justification",
        help=(
            "Prose justification for a single-layer recommendation. Required when all "
            "fix_path_helpers resolve to the same package (single-layer detection) "
            "AND the symptom is NOT a presentation-layer file. "
            "Path is only available for non-presentation-layer symptoms; "
            "presentation-layer symptoms must trace through a package boundary (see check 8b). "
            "Must be accompanied by --cites citing recorded evidence rows."
        ),
    )
    sp.add_argument(
        "--cites",
        default=None,
        dest="cites",
        help=(
            "JSON array of cite tokens (consumer_chain.consumer_qn, value_semantics.value, "
            "value_semantics.evidence, or dead_siblings.method_qn) proving the symptom is "
            "layer-local. Required when --single-layer-justification is provided."
        ),
    )
    sp.set_defaults(func=cmd_set_recommended_approach)

    sp = subparsers.add_parser(
        "set-constitution-constraints",
        help="Append (rule, impact) record to constitution_constraints.",
    )
    sp.add_argument("--rule", required=True)
    sp.add_argument("--impact", required=True)
    sp.set_defaults(func=cmd_set_constitution_constraints)

    sp = subparsers.add_parser(
        "set-complexity",
        help="Set complexity sub-fields (codebase_changes + risk + verify_cost).",
    )
    sp.add_argument("--codebase-changes", required=True, dest="codebase_changes",
                    choices=list(COMPLEXITY_ENUM))
    sp.add_argument("--codebase-notes", required=True, dest="codebase_notes")
    sp.add_argument("--risk", required=True, choices=list(COMPLEXITY_ENUM))
    sp.add_argument("--risk-notes", required=True, dest="risk_notes")
    sp.add_argument("--verify-cost", required=True, dest="verify_cost",
                    choices=list(COMPLEXITY_ENUM))
    sp.add_argument("--verify-notes", required=True, dest="verify_notes")
    sp.set_defaults(func=cmd_set_complexity)

    sp = subparsers.add_parser(
        "set-verdict",
        help="Set verdict (mode-aware enum). Rejects values outside mode's allowed set.",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_verdict)

    sp = subparsers.add_parser(
        "set-summary",
        help="Set summary (3-5 sentence opener).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_summary)

    sp = subparsers.add_parser(
        "set-next-step-text",
        help="Compose next-step text from memo + report; only when verdict proceeds.",
    )
    sp.set_defaults(func=cmd_set_next_step_text)

    sp = subparsers.add_parser(
        "render",
        help="Walk schema + state; emit research report md to stdout.",
    )
    sp.set_defaults(func=cmd_render)

    sp = subparsers.add_parser(
        "verify",
        help="Cross-check report state for required invariants. Exit 0 pass / 2 violations.",
    )
    sp.set_defaults(func=cmd_verify)

    # Phase 2.4c setters
    sp = subparsers.add_parser(
        "record-fix-path-helper",
        help="Append a {qn, file_line} helper entry to fix_path_helpers (deduped on qn).",
    )
    sp.add_argument("--helper-qn", required=True, dest="helper_qn")
    sp.add_argument(
        "--file-line",
        required=True,
        dest="file_line",
        help=(
            "Helper definition location as file:line (from search_graph result). "
            "Must be a real path — sentinel '(none)' is rejected here because "
            "the file_line is used for package extraction in check 8b."
        ),
    )
    sp.set_defaults(func=cmd_record_fix_path_helper)

    sp = subparsers.add_parser(
        "record-inbound-caller",
        help="Append a {helper_qn, caller_qn, file_line} record to inbound_callers.",
    )
    sp.add_argument("--helper-qn", required=True, dest="helper_qn")
    sp.add_argument("--caller-qn", required=True, dest="caller_qn")
    sp.add_argument("--file-line", required=True, dest="file_line")
    sp.set_defaults(func=cmd_record_inbound_caller)

    sp = subparsers.add_parser(
        "record-dead-sibling",
        help="Append a {class_qn, method_qn, verified_via} record to dead_siblings.",
    )
    sp.add_argument("--class-qn", required=True, dest="class_qn")
    sp.add_argument("--method-qn", required=True, dest="method_qn")
    sp.add_argument(
        "--verified-via",
        required=True,
        dest="verified_via",
        choices=("trace_path", "search_code"),
    )
    sp.set_defaults(func=cmd_record_dead_sibling)

    sp = subparsers.add_parser(
        "record-consumer-chain",
        help="Append a {value, consumer_qn, file_line, role} record to consumer_chain.",
    )
    sp.add_argument("--value", required=True)
    sp.add_argument("--consumer-qn", required=True, dest="consumer_qn")
    sp.add_argument("--file-line", required=True, dest="file_line")
    sp.add_argument("--role", required=True)
    sp.set_defaults(func=cmd_record_consumer_chain)

    sp = subparsers.add_parser(
        "set-value-semantics",
        help="Upsert a {value, classification, evidence} record in value_semantics.",
    )
    sp.add_argument("--value", required=True)
    sp.add_argument(
        "--classification",
        required=True,
        choices=("preference", "invariant", "unclassified"),
    )
    sp.add_argument("--evidence", required=True)
    sp.set_defaults(func=cmd_set_value_semantics)


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
    """Print research-state.json as JSON to stdout (defaults if missing)."""
    try:
        state = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("read-memo: {0}".format(err))
    json.dump(state, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_read_report(args: argparse.Namespace) -> int:
    """Print research-report.json as JSON to stdout (defaults if missing)."""
    try:
        state = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("read-report: {0}".format(err))
    json.dump(state, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    """4-artefact hard gate. Non-zero exit 2 + BLOCKED message on missing.

    Checks each PREFLIGHT_PREREQS path relative to --install-root for
    existence + non-empty (size > 0). On any failure, emits a single
    BLOCKED message naming the missing artefact + the producer command
    and exits 2.

    Distinct from generate_docs_helper preflight (which refreshes the
    CBM index stamp). This gate enforces that the 4-command setup chain
    is complete before /research runs.
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
            "BLOCKED: /research requires the full 4-command setup chain.\n"
        )
        for rel, producer in missing:
            sys.stderr.write("Missing: {0} (produced by {1})\n".format(rel, producer))
        sys.stderr.write(
            "Run: /init-forge → /generate-docs → /configure → /constitute, "
            "then retry /research.\n"
        )
        return 2
    return 0


# --- Phase 0 setter factory --------------------------------------------------


def _make_dim_setter(dim_name: str):
    """Build a setter handler for one rubric dimension.

    Each setter validates value (verbatim non-empty) + state enum +
    optionally increments turn counter, then writes back into
    memo.dimensions[dim_name]. As a side-effect, setting the `symptom`
    dimension auto-derives memo.topic_slug if not already set.
    """
    def handler(args: argparse.Namespace) -> int:
        try:
            value = _validate_verbatim(args.value, dim_name)
            state = _validate_enum(args.state, dim_name + ".state", RUBRIC_STATE_ENUM)
        except ValueError as err:
            return _die(str(err), code=2)
        try:
            with _state_transaction(args.devforge_dir, "memo") as memo:
                rec = memo["dimensions"].get(dim_name) or _empty_dimension()
                rec["value"] = value
                # Bounded-turn cap: once turns >= TURN_CAP and the caller
                # didn't explicitly mark Clear, dimension stays Partial.
                if args.increment_turn:
                    rec["turns"] = int(rec.get("turns", 0)) + 1
                if state == "Clear":
                    rec["state"] = "Clear"
                elif rec["turns"] >= TURN_CAP and state != "Clear":
                    rec["state"] = "Partial"
                else:
                    rec["state"] = state
                memo["dimensions"][dim_name] = rec
                if dim_name == "symptom" and not memo.get("topic_slug"):
                    memo["topic_slug"] = derive_topic_slug(value)
        except (OSError, json.JSONDecodeError) as err:
            return _die("set-{0}: {1}".format(dim_name, err))
        return 0
    handler.__name__ = "cmd_set_" + dim_name
    return handler


def _make_scope_setter():
    """Build the set-scope handler with the 'one place' evidence gate.

    Wraps _make_dim_setter("scope") with a pre-flight check: when --value
    normalizes to 'one place' (case-insensitive, whitespace-stripped), an
    --evidence flag carrying a valid file:line citation is required.
    Narrowing scope to 'one place' gates Phase 2 exploration depth before
    Phase 2 runs — forcing a citation ensures the LLM verifies locality
    before committing to the narrow framing.

    For all other scope values, --evidence is silently ignored (not stored)
    so the dim record stays shape-stable across wide vs narrow framings.
    """
    inner = _make_dim_setter("scope")

    def handler(args: argparse.Namespace) -> int:
        normalized = (args.value or "").strip().lower()
        if normalized == "one place":
            evidence = getattr(args, "evidence", None)
            # Treat empty string identically to missing.
            if not evidence or not evidence.strip():
                sys.stderr.write(
                    "set-scope: --evidence is required when --value == 'one place'. "
                    "Narrowing scope to 'one place' gates Phase 2 exploration depth "
                    "before Phase 2 runs — cite a file:line proving the symptom is "
                    "localized (typically the single symptom site).\n"
                )
                return 2
            try:
                evidence_validated = _validate_file_line(evidence.strip(), "scope.evidence")
            except ValueError as err:
                return _die(str(err), code=2)
            if evidence_validated == "(none)":
                sys.stderr.write(
                    "set-scope: --evidence cannot be '(none)' when --value == 'one place'; "
                    "narrow framing requires a concrete file:line citation.\n"
                )
                return 2
            # Write the dimension record via the inner setter.
            rc = inner(args)
            if rc != 0:
                return rc
            # Append evidence to the scope dim record (second transaction).
            try:
                with _state_transaction(args.devforge_dir, "memo") as memo:
                    rec = memo["dimensions"].get("scope") or _empty_dimension()
                    rec["evidence"] = evidence_validated
                    memo["dimensions"]["scope"] = rec
            except (OSError, json.JSONDecodeError) as err:
                return _die("set-scope: {0}".format(err))
            return 0
        # Non-narrow framing — evidence is optional and not stored.
        return inner(args)

    handler.__name__ = "cmd_set_scope"
    return handler


def cmd_set_topic(args: argparse.Namespace) -> int:
    """Set report.topic + auto-derive memo.topic_slug from topic.

    Topic comes from the user's original /research argument. Auto-deriving
    slug at this layer means the orchestrator only owns one input string;
    helper renders both topic text and filename slug.
    """
    try:
        value = _validate_scalar(args.value, "topic")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["topic"] = value
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo["topic_slug"] = derive_topic_slug(value)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-topic: {0}".format(err))
    return 0


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def cmd_set_date(args: argparse.Namespace) -> int:
    """Set report.date. Format YYYY-MM-DD enforced."""
    if not _DATE_RE.match(args.value):
        return _die(
            "set-date: invalid date {0!r}; expected YYYY-MM-DD".format(args.value),
            code=2,
        )
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["date"] = args.value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-date: {0}".format(err))
    return 0


def cmd_detect_mode(args: argparse.Namespace) -> int:
    """Detect mode from symptom dimension OR apply --override.

    Stdout: JSON {"mode": "bug" | "enhancement" | null, "source": "auto" |
    "override" | "ambiguous"}. Exits 0 always (caller decides how to
    handle ambiguous result). Persists mode into memo.mode on a clear
    detection.
    """
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            if args.override:
                mode = args.override
                source = "override"
            else:
                symptom_val = memo.get("dimensions", {}).get("symptom", {}).get("value") or ""
                mode = detect_mode_from_symptom(symptom_val)
                source = "auto" if mode else "ambiguous"
            memo["mode"] = mode
    except (OSError, json.JSONDecodeError) as err:
        return _die("detect-mode: {0}".format(err))
    json.dump({"mode": mode, "source": source}, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_record_gap(args: argparse.Namespace) -> int:
    """Append a {dimension, description} gap; set dimension state to Partial."""
    try:
        desc = _validate_scalar(args.description, "gap.description")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo.setdefault("gaps", []).append(
                {"dimension": args.dimension, "description": desc}
            )
            rec = memo["dimensions"].get(args.dimension) or _empty_dimension()
            if rec.get("state") != "Clear":
                rec["state"] = "Partial"
            memo["dimensions"][args.dimension] = rec
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-gap: {0}".format(err))
    return 0


def cmd_check_conflicts(args: argparse.Namespace) -> int:
    """Scan memo for direct contradictions; emit JSON list to stdout.

    Detected conflicts are appended to memo.conflicts (idempotent on
    description text) and emitted as JSON. Caller uses the list to drive
    AskUserQuestion for direct contradictions.
    """
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            detected = detect_direct_conflicts(memo)
            existing_descs = {c.get("description") for c in memo.get("conflicts", [])}
            for c in detected:
                if c["description"] not in existing_descs:
                    memo.setdefault("conflicts", []).append(c)
                    existing_descs.add(c["description"])
            current_open = [
                c for c in memo.get("conflicts", [])
                if c.get("resolution") == "blocked-pending-user"
            ]
    except (OSError, json.JSONDecodeError) as err:
        return _die("check-conflicts: {0}".format(err))
    json.dump(current_open, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_record_conflict_resolution(args: argparse.Namespace) -> int:
    """Mark a conflict as resolved; optionally clear a loser dimension."""
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            conflicts = memo.get("conflicts", [])
            if args.index < 0 or args.index >= len(conflicts):
                return _die(
                    "record-conflict-resolution: index {0} out of range "
                    "(have {1})".format(args.index, len(conflicts)),
                    code=2,
                )
            conflicts[args.index]["resolution"] = args.resolution
            if args.rewrite_dimension:
                rec = memo["dimensions"].get(args.rewrite_dimension) or _empty_dimension()
                rec["value"] = None
                rec["state"] = RUBRIC_STATE_DEFAULT
                rec["turns"] = 0
                memo["dimensions"][args.rewrite_dimension] = rec
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-conflict-resolution: {0}".format(err))
    return 0


def cmd_symptom_coverage(args: argparse.Namespace) -> int:
    """Emit JSON coverage map + counts to stdout."""
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("symptom-coverage: {0}".format(err))
    state_map, clear, partial, missing = _compute_coverage(memo)
    out = {
        "per_dimension": state_map,
        "counts": {"Clear": clear, "Partial": partial, "Missing": missing},
        "mode": memo.get("mode"),
        "conflicts_open": sum(
            1 for c in memo.get("conflicts", [])
            if c.get("resolution") == "blocked-pending-user"
        ),
    }
    json.dump(out, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_symptom_finalize(args: argparse.Namespace) -> int:
    """Validate memo is finalize-ready.

    Exit 0 when:
      - all 6 dimensions are Clear, AND
      - no conflicts with resolution == "blocked-pending-user".

    OR exit 0 with override_recorded=true persisted when:
      - --accept-gaps passed AND no blocked conflicts.

    Exit 2 otherwise. stderr enumerates each blocker.
    """
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            state_map, clear, partial, missing = _compute_coverage(memo)
            blocked = [
                c for c in memo.get("conflicts", [])
                if c.get("resolution") == "blocked-pending-user"
            ]
            violations = []  # type: List[str]
            if blocked:
                for c in blocked:
                    violations.append(
                        "blocked conflict ({0}): {1}".format(
                            "+".join(c.get("dimensions", [])),
                            c.get("description", ""),
                        )
                    )
            if (partial or missing) and not args.accept_gaps:
                for d, st in state_map.items():
                    if st != "Clear":
                        violations.append("{0}: {1}".format(d, st))

            if violations:
                for v in violations:
                    sys.stderr.write("symptom-finalize: {0}\n".format(v))
                return 2

            if (partial or missing) and args.accept_gaps:
                memo["override_recorded"] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("symptom-finalize: {0}".format(err))
    return 0


# --- Phase 1 setters ---------------------------------------------------------


def cmd_record_finding(args: argparse.Namespace) -> int:
    """Append a {surface, file_line, relevance, framing} Finding."""
    try:
        surface = _validate_scalar(args.surface, "finding.surface")
        file_line = _validate_file_line(args.file_line, "finding.file_line")
        relevance = _validate_scalar(args.relevance, "finding.relevance")
        framing = _validate_enum(
            getattr(args, "framing", "primary") or "primary",
            "finding.framing",
            FRAMING_ENUM,
        )
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("findings", []).append(
                {
                    "surface": surface,
                    "file_line": file_line,
                    "relevance": relevance,
                    "framing": framing,
                }
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-finding: {0}".format(err))
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


def cmd_record_hypothesis(args: argparse.Namespace) -> int:
    """Append a {cause, falsifier, runtime_probe_needed} Hypothesis."""
    try:
        cause = _validate_scalar(args.cause, "hypothesis.cause")
        falsifier = _validate_scalar(args.falsifier, "hypothesis.falsifier")
    except ValueError as err:
        return _die(str(err), code=2)
    runtime = args.runtime_probe_needed == "yes"
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("hypotheses", []).append(
                {"cause": cause, "falsifier": falsifier, "runtime_probe_needed": runtime}
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


# --- Phase 2 setters ---------------------------------------------------------


def cmd_set_approach(args: argparse.Namespace) -> int:
    """Append an Approach record."""
    try:
        name = _validate_scalar(args.name, "approach.name")
        desc = _validate_verbatim(args.description, "approach.description")
        addresses = _validate_string_array_json(args.addresses, "approach.addresses_hypotheses")
        not_covered = _validate_string_array_json(
            args.does_not_cover, "approach.does_not_cover"
        )
        pros = _validate_string_array_json(args.pros, "approach.pros")
        cons = _validate_string_array_json(args.cons, "approach.cons")
        complexity = _validate_enum(args.complexity, "approach.complexity", COMPLEXITY_ENUM)
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("approaches", []).append(
                {
                    "name": name,
                    "description": desc,
                    "addresses_hypotheses": addresses,
                    "does_not_cover": not_covered,
                    "pros": pros,
                    "cons": cons,
                    "complexity": complexity,
                }
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-approach: {0}".format(err))
    return 0


def cmd_set_recommended_approach(args: argparse.Namespace) -> int:
    """Set recommended approach. Name must match an existing approach.name.

    Validates: name resolves to an existing approach, hypotheses lists are
    JSON arrays of strings, rationale non-empty. Does not run the
    unchanged_behavior cross-check at set time — that runs in `verify`.

    Single-layer gate (Gap 4 — Patch 4): when all fix_path_helpers resolve
    to the same package (bug mode), --single-layer-justification + non-empty
    --cites are required. Each cite must match a recorded consumer_chain,
    value_semantics, or dead_siblings row token, proving the symptom is
    layer-local.
    """
    try:
        name = _validate_scalar(args.name, "recommended_approach.name")
        rationale = _validate_verbatim(args.rationale, "recommended_approach.rationale")
        addressed = _validate_string_array_json(
            args.hypotheses_addressed, "recommended_approach.hypotheses_addressed"
        )
        not_covered = _validate_string_array_json(
            args.hypotheses_not_covered, "recommended_approach.hypotheses_not_covered"
        )
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            names = {a.get("name") for a in report.get("approaches", [])}
            if name not in names:
                return _die(
                    "set-recommended-approach: name {0!r} does not match an existing approach; "
                    "have {1}".format(name, sorted(names)),
                    code=2,
                )

            recommended_record = {
                "name": name,
                "rationale": rationale,
                "hypotheses_addressed": addressed,
                "hypotheses_not_covered": not_covered,
            }

            # Single-layer detection: when all fix_path_helpers are in the same package,
            # the recommendation is anchored to one layer-stack region. Require an
            # explicit prose justification + cite at least one consumer_chain /
            # value_semantics / dead_siblings row proving the symptom is layer-local.
            # Closes Gap 4 in RESEARCH-FRAMING-REGRESSION-PLAN.
            fix_path_helpers = report.get("fix_path_helpers") or []
            memo_mode = None
            try:
                memo_state = _load_memo(args.devforge_dir)
                memo_mode = memo_state.get("mode")
            except (OSError, json.JSONDecodeError):
                pass
            bug_mode = (report.get("mode") == "bug" or memo_mode == "bug")

            # Only gate bug-mode reports — enhancement mode rarely populates fix_path_helpers
            # and the layer-locality framing isn't a Gap-4 failure class for enhancements.
            # SUPPRESSION: when check 8b would fire (presentation-layer symptom + all helpers
            # same package), check 13 / this setter gate are structurally unreachable —
            # supplying --single-layer-justification cannot satisfy verify because 8b vetoes
            # unconditionally. Skip the gate entirely; the LLM's only recovery is to add
            # cross-layer helpers, not supply justification.
            if bug_mode and len(fix_path_helpers) >= 1 and not _compute_check_8b_would_fire(report, bug_mode):
                packages = set()
                for h in fix_path_helpers:
                    if isinstance(h, dict) and h.get("file_line"):
                        pkg = _extract_package(h["file_line"].rsplit(":", 1)[0])
                        if pkg:
                            packages.add(pkg)
                single_layer = len(packages) == 1
                if single_layer:
                    justification = getattr(args, "single_layer_justification", None)
                    cites = getattr(args, "cites", None)
                    if not justification or not justification.strip():
                        return _die(
                            "set-recommended-approach: --single-layer-justification is required when all fix_path_helpers "
                            "resolve to the same package ({0!r}). Single-layer recommendations bypass the cross-layer "
                            "trace evidence — supply a justification text explaining why the symptom is layer-local AND "
                            "cite at least one consumer_chain / value_semantics / dead_siblings row via --cites.".format(
                                next(iter(packages))
                            ),
                            code=2,
                        )
                    # Parse cites JSON array
                    try:
                        cites_list = _validate_string_array_json(cites or "[]", "recommended_approach.cites")
                    except ValueError as err:
                        return _die(str(err), code=2)
                    if not cites_list:
                        return _die(
                            "set-recommended-approach: --cites is required (non-empty JSON array) when "
                            "--single-layer-justification is provided. Each cite must match a recorded "
                            "consumer_chain.consumer_qn, value_semantics.value (or value_semantics.evidence), "
                            "or dead_siblings.method_qn from the report state.",
                            code=2,
                        )
                    # Validate each cite resolves to a recorded row
                    consumer_chain = report.get("consumer_chain") or []
                    value_semantics = report.get("value_semantics") or []
                    dead_siblings = report.get("dead_siblings") or []
                    valid_tokens = set()
                    for cc in consumer_chain:
                        if cc.get("consumer_qn"):
                            valid_tokens.add(cc["consumer_qn"])
                    for vs in value_semantics:
                        if vs.get("value"):
                            valid_tokens.add(vs["value"])
                        if vs.get("evidence"):
                            valid_tokens.add(vs["evidence"])
                    for ds in dead_siblings:
                        if ds.get("method_qn"):
                            valid_tokens.add(ds["method_qn"])
                    unresolved = [c for c in cites_list if c not in valid_tokens]
                    if unresolved:
                        return _die(
                            "set-recommended-approach: --cites contains tokens that do not match any recorded "
                            "consumer_chain.consumer_qn, value_semantics.value, value_semantics.evidence, or "
                            "dead_siblings.method_qn: {0!r}. Recorded tokens: {1!r}.".format(
                                unresolved, sorted(valid_tokens)
                            ),
                            code=2,
                        )
                    # All citation checks pass — store on the recommended_approach record
                    # under new keys so render + verify can surface them.
                    recommended_record["single_layer_justification"] = justification
                    recommended_record["cites"] = cites_list

            report["recommended_approach"] = recommended_record
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-recommended-approach: {0}".format(err))
    return 0


def cmd_set_constitution_constraints(args: argparse.Namespace) -> int:
    """Append a {rule, impact} record."""
    try:
        rule = _validate_scalar(args.rule, "constitution.rule")
        impact = _validate_scalar(args.impact, "constitution.impact")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("constitution_constraints", []).append(
                {"rule": rule, "impact": impact}
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-constitution-constraints: {0}".format(err))
    return 0


def cmd_set_complexity(args: argparse.Namespace) -> int:
    """Set complexity record (3 ratings + 3 notes)."""
    try:
        cc = _validate_enum(args.codebase_changes, "complexity.codebase_changes", COMPLEXITY_ENUM)
        cn = _validate_scalar(args.codebase_notes, "complexity.codebase_notes")
        rk = _validate_enum(args.risk, "complexity.risk", COMPLEXITY_ENUM)
        rn = _validate_scalar(args.risk_notes, "complexity.risk_notes")
        vc = _validate_enum(args.verify_cost, "complexity.verify_cost", COMPLEXITY_ENUM)
        vn = _validate_scalar(args.verify_notes, "complexity.verify_notes")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["complexity"] = {
                "codebase_changes": cc,
                "codebase_notes": cn,
                "risk": rk,
                "risk_notes": rn,
                "verify_cost": vc,
                "verify_notes": vn,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-complexity: {0}".format(err))
    return 0


def cmd_set_verdict(args: argparse.Namespace) -> int:
    """Set verdict. Mode-aware: must be in VERDICT_ENUM[memo.mode]."""
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-verdict: cannot load memo: {0}".format(err))
    mode = memo.get("mode")
    if mode not in VERDICT_ENUM:
        return _die(
            "set-verdict: mode must be set before verdict (run detect-mode first); have {0!r}".format(mode),
            code=2,
        )
    try:
        value = _validate_enum(args.value, "verdict", VERDICT_ENUM[mode])
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["mode"] = mode
            report["verdict"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-verdict: {0}".format(err))
    return 0


def cmd_set_summary(args: argparse.Namespace) -> int:
    """Set summary (3-5 sentence opener)."""
    try:
        value = _validate_verbatim(args.value, "summary")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["summary"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-summary: {0}".format(err))
    return 0


def cmd_set_next_step_text(args: argparse.Namespace) -> int:
    """Compose next-step text from memo + report.

    Renders the copy-pasteable /specify prompt + key facts block. Only
    emits when verdict ∈ VERDICT_PROCEEDING[mode]. Otherwise sets
    next_step_text = None and exits 0 (no error).
    """
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-next-step-text: cannot load memo: {0}".format(err))

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            mode = report.get("mode") or memo.get("mode")
            verdict = report.get("verdict")
            if not mode or not verdict:
                return _die(
                    "set-next-step-text: mode + verdict must be set first",
                    code=2,
                )
            if verdict not in VERDICT_PROCEEDING.get(mode, set()):
                report["next_step_text"] = None
                return 0

            symptom = memo.get("dimensions", {}).get("symptom", {}).get("value") or ""
            desired = memo.get("dimensions", {}).get("desired", {}).get("value") or ""
            rec_approach = report.get("recommended_approach") or {}
            approach_name = rec_approach.get("name") or "(approach name)"
            addressed = rec_approach.get("hypotheses_addressed") or []
            not_covered = rec_approach.get("hypotheses_not_covered") or []
            slug = memo.get("topic_slug") or derive_topic_slug(symptom or report.get("topic") or "")
            date = report.get("date") or "YYYY-MM-DD"

            refined = (symptom + " — " + desired).strip(" —")
            refined_short = refined if refined else "topic"
            text = (
                "## Next step\n\n"
                "Copy the block below into a new `/specify` session manually. "
                "No automation — user controls when (or if) `/specify` runs.\n\n"
                "~~~\n"
                "/specify \"{refined}\"\n\n"
                "Research reference: research/{date}-{slug}.md\n"
                "Key facts:\n"
                "- Mode: {mode}\n"
                "- Symptom: {sym}\n"
                "- Desired: {des}\n"
                "- Recommended approach: {appr}\n"
                "- Hypothesis addressed: {addr}\n"
                "- Hypotheses NOT covered: {nc}\n"
                "- Open uncertainties: {gaps} (see research doc §Open Uncertainties)\n"
                "~~~\n"
            ).format(
                refined=refined_short,
                date=date,
                slug=slug,
                mode="Bug" if mode == "bug" else "Enhancement",
                sym=symptom or "(unset)",
                des=desired or "(unset)",
                appr=approach_name,
                addr=", ".join(addressed) if addressed else "(none)",
                nc=", ".join(not_covered) if not_covered else "(none)",
                gaps=len(memo.get("gaps", [])),
            )
            report["next_step_text"] = text
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-next-step-text: {0}".format(err))
    return 0


# --- Phase 2.4c setters (helper-API surface enumeration) --------------------


def cmd_record_fix_path_helper(args: argparse.Namespace) -> int:
    """Append a {qn, file_line} entry to fix_path_helpers (deduped on qn).

    file_line is the HELPER'S DEFINITION location (from search_graph result),
    NOT the call-site. The sentinel '(none)' is explicitly rejected — the
    definition file is required for layer-boundary package extraction in check 8b.
    """
    try:
        helper_qn = _validate_scalar(args.helper_qn, "fix_path_helper.helper_qn")
        file_line = _validate_file_line(args.file_line, "fix_path_helper.file_line")
    except ValueError as err:
        return _die(str(err), code=2)
    if file_line == "(none)":
        return _die(
            "record-fix-path-helper: --file-line cannot be (none) — "
            "the helper's definition must have a real file path for "
            "layer-boundary detection",
            code=2,
        )
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            lst = report.setdefault("fix_path_helpers", [])
            # Dedupe on qn: skip if an entry with the same qn already exists.
            if not any(entry.get("qn") == helper_qn for entry in lst):
                lst.append({"qn": helper_qn, "file_line": file_line})
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-fix-path-helper: {0}".format(err))
    return 0


def cmd_record_inbound_caller(args: argparse.Namespace) -> int:
    """Append a {helper_qn, caller_qn, file_line} record to inbound_callers."""
    try:
        helper_qn = _validate_scalar(args.helper_qn, "inbound_caller.helper_qn")
        caller_qn = _validate_scalar(args.caller_qn, "inbound_caller.caller_qn")
        file_line = _validate_file_line(args.file_line, "inbound_caller.file_line")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("inbound_callers", []).append(
                {"helper_qn": helper_qn, "caller_qn": caller_qn, "file_line": file_line}
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-inbound-caller: {0}".format(err))
    return 0


def cmd_record_dead_sibling(args: argparse.Namespace) -> int:
    """Append a {class_qn, method_qn, verified_via} record to dead_siblings."""
    try:
        class_qn = _validate_scalar(args.class_qn, "dead_sibling.class_qn")
        method_qn = _validate_scalar(args.method_qn, "dead_sibling.method_qn")
    except ValueError as err:
        return _die(str(err), code=2)
    # verified_via is already constrained by argparse choices=
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            # Intentional: no dedupe. Two recordings of the same (class_qn, method_qn)
            # from different trace passes are both kept; verify checks tolerate duplicates.
            report.setdefault("dead_siblings", []).append(
                {"class_qn": class_qn, "method_qn": method_qn, "verified_via": args.verified_via}
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-dead-sibling: {0}".format(err))
    return 0


def cmd_record_consumer_chain(args: argparse.Namespace) -> int:
    """Append a {value, consumer_qn, file_line, role} record to consumer_chain."""
    try:
        value = _validate_scalar(args.value, "consumer_chain.value")
        consumer_qn = _validate_scalar(args.consumer_qn, "consumer_chain.consumer_qn")
        file_line = _validate_file_line(args.file_line, "consumer_chain.file_line")
        role = _validate_scalar(args.role, "consumer_chain.role")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("consumer_chain", []).append(
                {"value": value, "consumer_qn": consumer_qn, "file_line": file_line, "role": role}
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-consumer-chain: {0}".format(err))
    return 0


def cmd_set_value_semantics(args: argparse.Namespace) -> int:
    """Upsert a {value, classification, evidence} record in value_semantics.

    Last-write-wins on value key. When classification==invariant, requires
    at least one consumer_chain row with matching value field.
    """
    try:
        value = _validate_scalar(args.value, "value_semantics.value")
        evidence = _validate_scalar(args.evidence, "value_semantics.evidence")
    except ValueError as err:
        return _die(str(err), code=2)
    # classification is already constrained by argparse choices=
    classification = args.classification

    # Invariant guard: check before entering the state transaction so the
    # file is never rewritten on a validation rejection.
    if classification == "invariant":
        try:
            report_snapshot = _load_report(args.devforge_dir)
        except (OSError, json.JSONDecodeError) as err:
            return _die("set-value-semantics: {0}".format(err))
        chain = report_snapshot.get("consumer_chain") or []
        if not any(r.get("value") == value for r in chain):
            return _die(
                "set-value-semantics: classification=invariant requires at least one "
                "consumer_chain entry for value={0!r}; record-consumer-chain first".format(value),
                code=2,
            )

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rows = report.setdefault("value_semantics", [])
            for i, row in enumerate(rows):
                if row.get("value") == value:
                    rows[i] = {"value": value, "classification": classification, "evidence": evidence}
                    break
            else:
                rows.append({"value": value, "classification": classification, "evidence": evidence})
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-value-semantics: {0}".format(err))
    return 0


# --- Render + verify + summary ----------------------------------------------


def _render_report_md(memo: dict, report: dict) -> str:
    """Compose the research report markdown.

    Section order (locked):
      1. Title + frontmatter (Date, Topic, Mode, Verdict)
      2. Summary
      3. Symptom (5-dim table)
      4. Codebase Findings (with Framing column)
      5. Root Cause Hypothesis
      6. Structured root cause (bug-mode + confidence ≥ Hypothesis)
      6b. Runner-up framing (when runner_up_framing is set)
      7. Hypothesis Enumeration
      8. Recommended Verify Step (when present)
      9. Approaches
      10. Constitution Constraints
      11. Complexity Assessment
      12. Open Uncertainties (when gaps present)
      13. Next step (when verdict proceeds)
    """
    out = []  # type: List[str]
    topic = report.get("topic") or _derive_topic_for_render(memo, report)
    date = report.get("date") or "YYYY-MM-DD"
    mode = report.get("mode") or memo.get("mode") or "(unset)"
    mode_label = "Bug" if mode == "bug" else ("Enhancement" if mode == "enhancement" else "(unset)")
    verdict = report.get("verdict") or "(unset)"

    out.append("# Research: {0}\n".format(topic))
    out.append("")
    out.append("**Date**: {0}".format(date))
    out.append("**Topic**: {0}".format(topic))
    out.append("**Mode**: {0}".format(mode_label))
    out.append("**Verdict**: {0}".format(verdict))
    out.append("")

    out.append("## Summary")
    out.append("")
    out.append(report.get("summary") or "(summary unset)")
    out.append("")

    # Symptom table — 5 dims (drop unchanged_behavior from render per Plan;
    # it's used for verify cross-check, not user-facing report).
    out.append("## Symptom")
    out.append("")
    out.append("| Dimension | Value |")
    out.append("|---|---|")
    dim_map = memo.get("dimensions", {})
    for d, label in (
        ("symptom", "Symptom"),
        ("affected_area", "Affected area"),
        ("repro_or_current", "Repro / Current"),
        ("desired", "Desired"),
        ("scope", "Scope"),
    ):
        rec = dim_map.get(d, {})
        v = rec.get("value") or "(unset)"
        # Append evidence annotation for scope narrow-framing (evidence field
        # is set only when --value == "one place" was passed with --evidence).
        if d == "scope":
            scope_evidence = rec.get("evidence")
            if scope_evidence:
                v = "{0} (evidence: {1})".format(v, scope_evidence)
        out.append("| {0} | {1} |".format(label, _md_escape_cell(v)))
    out.append("")

    out.append("## Codebase Findings (WHERE)")
    out.append("")
    findings = report.get("findings", []) or []
    if findings:
        out.append("| Surface | File:line | Relevance | Framing |")
        out.append("|---|---|---|---|")
        for f in findings:
            out.append("| {0} | {1} | {2} | {3} |".format(
                _md_escape_cell(f.get("surface", "")),
                _md_escape_cell(f.get("file_line", "")),
                _md_escape_cell(f.get("relevance", "")),
                _md_escape_cell(f.get("framing", "primary")),
            ))
    else:
        out.append("(no findings recorded)")
    out.append("")

    out.append("## Root Cause Hypothesis (WHY)")
    out.append("")
    rch = report.get("root_cause_hypothesis") or "(unset)"
    out.append("**Primary hypothesis**: {0}".format(rch))
    out.append("")
    confidence = report.get("confidence") or "(unset)"
    out.append("**Confidence**: {0}".format(confidence))
    out.append("")

    src = report.get("structured_root_cause")
    if (
        mode == "bug"
        and confidence in ("Confirmed", "Hypothesis")
        and src is not None
    ):
        out.append("### Structured root cause")
        out.append("")
        out.append("| Field | Value |")
        out.append("|---|---|")
        out.append("| trigger | {0} |".format(_md_escape_cell(src.get("trigger") or "(unset)")))
        out.append("| root_cause | {0} |".format(_md_escape_cell(src.get("root_cause_systemic") or "(unset)")))
        factors = src.get("contributing_factors") or []
        if factors:
            joined = " ".join("{0}. {1}".format(i + 1, f) for i, f in enumerate(factors))
        else:
            joined = "(none)"
        out.append("| contributing_factors | {0} |".format(_md_escape_cell(joined)))
        out.append("")

    runner_up = report.get("runner_up_framing")
    if runner_up is not None:
        out.append("## Runner-up framing")
        out.append("")
        out.append("| Field | Value |")
        out.append("|---|---|")
        out.append("| Frame | {0} |".format(_md_escape_cell(runner_up.get("frame") or "(unset)")))
        out.append("| Falsifier | {0} |".format(_md_escape_cell(runner_up.get("falsifier") or "(unset)")))
        out.append("| Confidence vs primary | {0} |".format(
            _md_escape_cell(runner_up.get("confidence_vs_primary") or "(unset)")
        ))
        out.append("")

    out.append("## Hypothesis Enumeration")
    out.append("")
    hypotheses = report.get("hypotheses", []) or []
    if hypotheses:
        out.append("| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |")
        out.append("|---|---|---|")
        for h in hypotheses:
            out.append("| {0} | {1} | {2} |".format(
                _md_escape_cell(h.get("cause", "")),
                _md_escape_cell(h.get("falsifier", "")),
                "yes" if h.get("runtime_probe_needed") else "no",
            ))
    else:
        out.append("(no hypotheses recorded — verify will fail)")
    out.append("")

    vstep = report.get("verify_step")
    if vstep is not None:
        out.append("## Recommended Verify Step")
        out.append("")
        out.append("| Sub-field | Value |")
        out.append("|---|---|")
        out.append("| probe | {0} |".format(_md_escape_cell(vstep.get("probe") or "(unset)")))
        out.append("| reproduction | {0} |".format(_md_escape_cell(vstep.get("reproduction") or "(unset)")))
        out.append("| discriminator | {0} |".format(_md_escape_cell(vstep.get("discriminator") or "(unset)")))
        out.append("")

    out.append("## Approaches (HOW to change)")
    out.append("")
    approaches = report.get("approaches", []) or []
    rec = report.get("recommended_approach") or {}
    rec_name = rec.get("name")
    if approaches:
        for ap in approaches:
            out.append("### {0}".format(ap.get("name") or "(unnamed)"))
            out.append("- **Description**: {0}".format(ap.get("description") or "(unset)"))
            out.append("- **Addresses hypothesis**: {0}".format(
                ", ".join(ap.get("addresses_hypotheses") or []) or "(none)"
            ))
            out.append("- **Does NOT cover**: {0}".format(
                ", ".join(ap.get("does_not_cover") or []) or "(none)"
            ))
            pros = ap.get("pros") or []
            cons = ap.get("cons") or []
            out.append("- **Pros**: {0}".format("; ".join(pros) or "(none)"))
            out.append("- **Cons**: {0}".format("; ".join(cons) or "(none)"))
            out.append("- **Complexity**: {0}".format(ap.get("complexity") or "(unset)"))
            out.append("")
        if rec_name:
            out.append("**Recommended approach**: {0} — {1}".format(
                rec_name, rec.get("rationale") or "(no rationale)"
            ))
            # Single-layer justification sub-section (only when present).
            single_layer_just = rec.get("single_layer_justification")
            if single_layer_just:
                out.append("")
                out.append("**Single-layer justification:**")
                out.append(single_layer_just.strip())
                cites_list = rec.get("cites") or []
                if cites_list:
                    out.append("")
                    out.append("**Cites:**")
                    for cite in cites_list:
                        out.append("- {0}".format(cite))
            out.append("")
    else:
        out.append("(no approaches recorded)")
        out.append("")

    out.append("## Constitution Constraints")
    out.append("")
    cc = report.get("constitution_constraints", []) or []
    if cc:
        out.append("| Rule | Impact on this change |")
        out.append("|---|---|")
        for c in cc:
            out.append("| {0} | {1} |".format(
                _md_escape_cell(c.get("rule", "")),
                _md_escape_cell(c.get("impact", "")),
            ))
    else:
        out.append("(no constitution constraints recorded)")
    out.append("")

    out.append("## Complexity Assessment")
    out.append("")
    cx = report.get("complexity")
    if cx:
        out.append("| Dimension | Rating | Notes |")
        out.append("|---|---|---|")
        out.append("| Codebase changes | {0} | {1} |".format(
            cx.get("codebase_changes") or "(unset)",
            _md_escape_cell(cx.get("codebase_notes") or ""),
        ))
        out.append("| Risk | {0} | {1} |".format(
            cx.get("risk") or "(unset)",
            _md_escape_cell(cx.get("risk_notes") or ""),
        ))
        out.append("| Verify cost | {0} | {1} |".format(
            cx.get("verify_cost") or "(unset)",
            _md_escape_cell(cx.get("verify_notes") or ""),
        ))
    else:
        out.append("(complexity unset)")
    out.append("")

    gaps = memo.get("gaps") or []
    if gaps:
        out.append("## Open Uncertainties")
        out.append("")
        for g in gaps:
            out.append("- [NEEDS CLARIFICATION: {0} — {1}]".format(
                g.get("dimension", ""), g.get("description", "")
            ))
        out.append("")

    next_step = report.get("next_step_text")
    if next_step:
        out.append(next_step.rstrip("\n"))
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def _md_escape_cell(text: str) -> str:
    """Escape pipe + newline so the value survives a markdown table cell."""
    if text is None:
        return ""
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _derive_topic_for_render(memo: dict, report: dict) -> str:
    """Best-effort topic for the rendered title.

    Prefers report.topic; falls back to memo.dimensions.symptom.value;
    final fallback is "(untitled)".
    """
    t = report.get("topic")
    if t:
        return t
    sym = memo.get("dimensions", {}).get("symptom", {}).get("value")
    if sym:
        return sym
    return "(untitled)"


def cmd_render(args: argparse.Namespace) -> int:
    """Render report md to stdout. Caller decides where to save (Phase 3)."""
    try:
        memo = _load_memo(args.devforge_dir)
        report = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render: {0}".format(err))
    try:
        text = _render_report_md(memo, report)
    except ValueError as err:
        return _die("render: {0}".format(err), code=2)
    sys.stdout.write(text)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Cross-check report state against required invariants.

    Checks (each violation → stderr line):
      1. Hypotheses: minimum 2 entries.
      2. Recommended approach: name resolves; hypotheses_addressed +
         hypotheses_not_covered non-empty arrays.
      3. Recommended approach respects memo.dimensions.unchanged_behavior:
         if unchanged_behavior contains a token also in approach
         description AND that token is associated with a value-flip
         pattern, flag a violation. Lightweight check — re-uses the
         antagonist patterns from detect_direct_conflicts against
         unchanged_behavior vs. recommended approach rationale.
      4. Verdict ∈ VERDICT_ENUM[mode].
      5. Structured root cause populated when mode==bug AND
         confidence ∈ {Confirmed, Hypothesis}: trigger +
         root_cause_systemic present; contributing_factors ≤ 3.
      6. Verify-step 3 sub-fields populated when any hypothesis has
         runtime_probe_needed=true.
      7. Summary, complexity, ≥1 approach present.
      8. fix_path_helpers non-empty for bug mode.
      8b. Bug mode + symptom is presentation-layer + all fix_path_helpers
          defined in same package → cross-layer trace required. Package
          derived from fix_path_helpers[].file_line (helper definition),
          NOT from inbound_callers call-sites. Check 13 is subordinate:
          when 8b fires, the single-layer-justification path cannot
          satisfy verify, so check 13 is suppressed to give the LLM a
          single actionable error.
      9. Every fix_path_helper has at least one inbound_callers row.
     10. If value_semantics has an invariant AND dead_siblings is non-empty,
         at least one approach mentions the signature change or dead-sibling QN.
     11. If value_semantics has an invariant, recommended_approach.rationale
         cites a consumer_chain entry, invariant evidence, or dead-sibling QN.
     12. If runner_up_framing is set, at least one finding must be tagged
         framing=runner-up (Phase 2.4 must probe the runner-up frame).
     13. Cross-layer recommendation enforcement: when bug mode + fix_path_helpers
         all resolve to the same package (single-layer), recommended_approach
         must carry single_layer_justification (non-empty) and cites (non-empty).
         Catches out-of-order setter calls where recommended_approach was set
         before fix_path_helpers collapsed to single-layer. Only fires when
         check 8b does NOT apply (i.e., symptom is NOT presentation-layer);
         for presentation-layer symptoms, check 8b is the blocking gate and
         the single-layer escape path is structurally unavailable.

    Exit 0 = all pass. Exit 2 = at least one violation. Exit 1 = state
    files unreadable.
    """
    try:
        memo = _load_memo(args.devforge_dir)
        report = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write("research_helper verify: cannot load state: {0}\n".format(err))
        return 1

    violations = []  # type: List[str]

    # Check 1: ≥2 hypotheses.
    hyps = report.get("hypotheses") or []
    if len(hyps) < 2:
        violations.append(
            "hypothesis enumeration: have {0}, need at least 2".format(len(hyps))
        )

    # Check 2 + 3: recommended approach.
    rec = report.get("recommended_approach")
    approaches = report.get("approaches") or []
    if rec is None:
        violations.append("recommended_approach: unset")
    else:
        names = {a.get("name") for a in approaches}
        if rec.get("name") not in names:
            violations.append(
                "recommended_approach.name {0!r} does not match any approach".format(
                    rec.get("name")
                )
            )
        if not rec.get("hypotheses_addressed"):
            violations.append("recommended_approach.hypotheses_addressed: empty")
        # Check 3: unchanged_behavior cross-check.
        unchanged = memo.get("dimensions", {}).get("unchanged_behavior", {}).get("value") or ""
        # Build a temporary memo-like structure for the antagonist scan:
        # plug rationale into 'desired' slot so the existing
        # _CONFLICT_PATTERNS catch the same antagonisms vs unchanged.
        rationale = rec.get("rationale") or ""
        if unchanged and rationale:
            shadow = {
                "dimensions": {
                    "desired": {"value": rationale},
                    "unchanged_behavior": {"value": unchanged},
                }
            }
            for c in detect_direct_conflicts(shadow):
                violations.append(
                    "recommended_approach violates unchanged_behavior: {0}".format(
                        c.get("description")
                    )
                )

    # Check 4: verdict ∈ allowed.
    mode = report.get("mode") or memo.get("mode")
    verdict = report.get("verdict")
    if not mode:
        violations.append("mode: unset (run detect-mode)")
    elif verdict is None:
        violations.append("verdict: unset")
    elif verdict not in VERDICT_ENUM[mode]:
        violations.append(
            "verdict {0!r} not allowed for mode {1!r} (allowed: {2})".format(
                verdict, mode, list(VERDICT_ENUM[mode])
            )
        )

    # Check 5: structured root cause for bug-mode + confidence ≥ Hypothesis.
    confidence = report.get("confidence")
    src = report.get("structured_root_cause")
    if mode == "bug" and confidence in ("Confirmed", "Hypothesis"):
        if src is None:
            violations.append(
                "structured_root_cause required for mode==bug + confidence in "
                "{Confirmed, Hypothesis} but is null"
            )
        else:
            if not src.get("trigger"):
                violations.append("structured_root_cause.trigger: unset")
            if not src.get("root_cause_systemic"):
                violations.append("structured_root_cause.root_cause_systemic: unset")
            if len(src.get("contributing_factors") or []) > 3:
                violations.append(
                    "structured_root_cause.contributing_factors: max 3 (have {0})".format(
                        len(src.get("contributing_factors") or [])
                    )
                )

    # Check 6: verify-step when any hypothesis needs runtime probe.
    needs_probe = any(h.get("runtime_probe_needed") for h in hyps)
    vstep = report.get("verify_step")
    if needs_probe:
        if vstep is None:
            violations.append("verify_step required (a hypothesis needs runtime probe) but unset")
        else:
            for sub in ("probe", "reproduction", "discriminator"):
                if not vstep.get(sub):
                    violations.append("verify_step.{0}: unset".format(sub))

    # Check 7: minimum scaffolding present.
    if not report.get("summary"):
        violations.append("summary: unset")
    if report.get("complexity") is None:
        violations.append("complexity: unset")
    if not approaches:
        violations.append("approaches: empty")

    # Check 8: bug mode requires fix_path_helpers non-empty.
    fix_path_helpers = report.get("fix_path_helpers") or []
    if (report.get("mode") == "bug" or memo.get("mode") == "bug") and not fix_path_helpers:
        violations.append(
            "fix_path_helpers: empty (Phase 2.4c requires at least one helper enumerated for bug mode)"
        )

    # Check 8b: when bug mode + symptom is in a presentation-layer file, at
    # least one fix_path_helper must be defined in a DIFFERENT package
    # (cross-layer rule). Package derived from fix_path_helpers[].file_line
    # (the helper's definition location), NOT from inbound_callers call-sites.
    # Fires only when check 8 already passed (list non-empty) and mode==bug,
    # so the two checks compose without redundancy.
    if fix_path_helpers and (report.get("mode") == "bug" or memo.get("mode") == "bug"):
        findings_for_8b = report.get("findings") or []
        # Identify the primary symptom path: first finding with framing==primary
        # (or framing missing, which defaults to primary per record-finding).
        primary_path_8b = None  # type: Optional[str]
        for f in findings_for_8b:
            framing_val = f.get("framing") or "primary"
            if framing_val == "primary":
                fl = f.get("file_line") or ""
                colon_pos = fl.rfind(":")
                if colon_pos > 0:
                    primary_path_8b = fl[:colon_pos]
                elif fl:
                    primary_path_8b = fl
                break  # first primary finding only
        if primary_path_8b and _is_presentation_layer(primary_path_8b):
            symptom_pkg = _extract_package(primary_path_8b)
            has_cross_layer = False
            for h in fix_path_helpers:
                # Only dict entries carry file_line; skip bare strings
                # (legacy direct-JSON writes) — they contribute no package info.
                if not isinstance(h, dict):
                    continue
                # Derive helper package from the helper's own definition file_line.
                helper_file_line = h.get("file_line") or ""
                colon_pos = helper_file_line.rfind(":")
                if colon_pos > 0:
                    helper_file = helper_file_line[:colon_pos]
                else:
                    helper_file = helper_file_line
                if _extract_package(helper_file) != symptom_pkg:
                    has_cross_layer = True
                    break
            if not has_cross_layer:
                violations.append(
                    "fix_path_helpers: all entries in same package as "
                    "presentation-layer symptom site {0!r}; Phase 2.4c must "
                    "trace at least one helper UP to a different package "
                    "(cross-layer rule)".format(primary_path_8b)
                )

    # Check 9: every enumerated helper needs at least one inbound caller row.
    inbound_callers = report.get("inbound_callers") or []
    for h in fix_path_helpers:
        helper_qn = h.get("qn") if isinstance(h, dict) else h
        if not any(r.get("helper_qn") == helper_qn for r in inbound_callers):
            violations.append(
                "inbound_callers: no entry for helper {0!r} "
                "(record-inbound-caller required for every fix_path_helper)".format(helper_qn)
            )

    # Check 10: invariant + dead siblings demands signature-touching approach.
    value_semantics = report.get("value_semantics") or []
    dead_siblings = report.get("dead_siblings") or []
    has_invariant = any(v.get("classification") == "invariant" for v in value_semantics)
    if has_invariant and dead_siblings:
        candidate_tokens = {"signature", "drop param"}
        for ds in dead_siblings:
            mq = ds.get("method_qn") or ""
            if mq:
                candidate_tokens.add(mq.lower())
        found_approach = False
        for ap in approaches:
            haystack = (
                (ap.get("name") or "")
                + " "
                + (ap.get("description") or "")
                + " "
                + " ".join(ap.get("pros") or [])
                + " "
                + " ".join(ap.get("cons") or [])
            ).lower()
            if any(tok in haystack for tok in candidate_tokens):
                found_approach = True
                break
        if not found_approach:
            dead_qn_sample = (dead_siblings[0].get("method_qn") or "") if dead_siblings else ""
            violations.append(
                "approaches: value_semantics has invariant AND dead_siblings non-empty, "
                "but no approach mentions helper signature change or dead-sibling QN "
                "(cite signature change or {0!r} in an approach)".format(dead_qn_sample)
            )

    # Check 11: invariant requires evidence cite in recommended approach rationale.
    if has_invariant and rec is not None:
        rationale = (rec.get("rationale") or "").lower()
        consumer_chain = report.get("consumer_chain") or []
        candidate_rationale_tokens = []  # type: List[str]
        for cc_row in consumer_chain:
            cq = cc_row.get("consumer_qn") or ""
            if cq:
                candidate_rationale_tokens.append(cq.lower())
        for vs_row in value_semantics:
            if vs_row.get("classification") == "invariant":
                ev = vs_row.get("evidence") or ""
                if ev:
                    candidate_rationale_tokens.append(ev.lower())
        for ds in dead_siblings:
            mq = ds.get("method_qn") or ""
            if mq:
                candidate_rationale_tokens.append(mq.lower())
        if candidate_rationale_tokens and not any(tok in rationale for tok in candidate_rationale_tokens):
            violations.append(
                "recommended_approach.rationale: value_semantics has invariant, but rationale "
                "cites neither a consumer_chain entry, an invariant evidence string, "
                "nor a dead-sibling QN"
            )

    # Check 12a: Phase 2.3b is MANDATORY — runner_up_framing must be set.
    # Closes the spec-vs-helper gap where an LLM skipping Phase 2.3b entirely
    # would never trigger the conditional check 12b.
    runner_up_framing = report.get("runner_up_framing")
    if runner_up_framing is None:
        violations.append(
            "runner_up_framing: unset — Phase 2.3b is MANDATORY; "
            "call record-runner-up-framing before verify"
        )
    else:
        # Check 12b: when runner_up_framing is set, at least one finding must
        # be tagged framing=runner-up so Phase 2.4 probed the runner-up frame.
        findings = report.get("findings") or []
        runner_up_findings = [f for f in findings if f.get("framing") == "runner-up"]
        if len(runner_up_findings) < 1:
            violations.append(
                "runner_up_framing is set but no findings tagged framing=runner-up; "
                "Phase 2.4 must probe the runner-up frame with at least one finding "
                "(record-finding --framing runner-up ...)"
            )

    # Check 13: cross-layer recommendation enforcement. When bug mode +
    # fix_path_helpers all resolve to the same package (single-layer detection),
    # recommended_approach must carry single_layer_justification (non-empty) and
    # cites (non-empty). This catches out-of-order setter calls where
    # recommended_approach was written before fix_path_helpers collapsed to
    # single-layer. Closes Gap 4 (verify-time) in RESEARCH-FRAMING-REGRESSION-PLAN.
    # SUPPRESSION: check 13 is subordinate to check 8b. When 8b would fire
    # (presentation-layer symptom + all helpers same package), the single-layer-
    # justification escape is structurally unavailable — the only recovery is
    # adding cross-layer helpers. Skip check 13 so the LLM gets a single
    # actionable error from 8b rather than a misleading 13 violation pointing at
    # a path that cannot satisfy verify.
    check_13_suppressed = _compute_check_8b_would_fire(
        report, report.get("mode") == "bug" or memo.get("mode") == "bug"
    )
    if (
        (report.get("mode") == "bug" or memo.get("mode") == "bug")
        and rec is not None
        and fix_path_helpers
        and not check_13_suppressed
    ):
        packages_13 = set()
        for h in fix_path_helpers:
            if isinstance(h, dict) and h.get("file_line"):
                pkg = _extract_package(h["file_line"].rsplit(":", 1)[0])
                if pkg:
                    packages_13.add(pkg)
        if len(packages_13) == 1:
            if not (rec.get("single_layer_justification") or "").strip():
                violations.append(
                    "check 13: recommended_approach is single-layer (all fix_path_helpers "
                    "in package {0!r}) but single_layer_justification is missing or empty; "
                    "use set-recommended-approach --single-layer-justification to supply "
                    "a prose justification proving the symptom is layer-local".format(
                        next(iter(packages_13))
                    )
                )
            if not rec.get("cites"):
                violations.append(
                    "check 13: recommended_approach is single-layer (all fix_path_helpers "
                    "in package {0!r}) but cites is missing or empty; "
                    "use set-recommended-approach --cites '[\"token\"]' to cite at least one "
                    "consumer_chain.consumer_qn, value_semantics.value, value_semantics.evidence, "
                    "or dead_siblings.method_qn row proving the symptom is layer-local".format(
                        next(iter(packages_13))
                    )
                )

    if violations:
        for v in violations:
            sys.stderr.write("research_helper verify: {0}\n".format(v))
        return 2
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Read-only stdout summary across both state files."""
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("summary: cannot load memo: {0}".format(err), code=1)
    try:
        report = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("summary: cannot load report: {0}".format(err), code=1)

    state_map, clear, partial, missing = _compute_coverage(memo)
    lines = []  # type: List[str]
    lines.append("Phase 0 (memo):")
    lines.append("  mode: {0}".format(memo.get("mode") or "(unset)"))
    lines.append("  topic_slug: {0}".format(memo.get("topic_slug") or "(unset)"))
    for d in RUBRIC_DIMENSIONS:
        rec = memo.get("dimensions", {}).get(d, {})
        val = rec.get("value") or "(unset)"
        st = rec.get("state") or RUBRIC_STATE_DEFAULT
        turns = rec.get("turns", 0)
        line = "  {0}: state={1} turns={2} value={3!r}".format(d, st, turns, val[:80])
        # Surface evidence field for scope narrow-framing runs.
        if d == "scope":
            scope_evidence = rec.get("evidence")
            if scope_evidence:
                line += " evidence={0}".format(scope_evidence)
        lines.append(line)
    lines.append("  coverage: Clear={0} Partial={1} Missing={2}".format(clear, partial, missing))
    lines.append("  gaps: {0}".format(len(memo.get("gaps", []))))
    lines.append("  conflicts: {0}".format(len(memo.get("conflicts", []))))
    lines.append("  override_recorded: {0}".format(memo.get("override_recorded", False)))

    lines.append("")
    lines.append("Phase 1+2 (report):")
    lines.append("  mode: {0}".format(report.get("mode") or "(unset)"))
    lines.append("  verdict: {0}".format(report.get("verdict") or "(unset)"))
    lines.append("  confidence: {0}".format(report.get("confidence") or "(unset)"))
    lines.append("  findings: {0}".format(len(report.get("findings", []))))
    lines.append("  hypotheses: {0}".format(len(report.get("hypotheses", []))))
    lines.append("  approaches: {0}".format(len(report.get("approaches", []))))
    lines.append("  recommended_approach: {0}".format(
        (report.get("recommended_approach") or {}).get("name") or "(unset)"
    ))
    # Single-layer detection summary line: shown for bug mode + non-empty fix_path_helpers.
    mode_for_summary = report.get("mode") or memo.get("mode")
    fix_path_helpers_for_summary = report.get("fix_path_helpers") or []
    if mode_for_summary == "bug" and fix_path_helpers_for_summary:
        packages_summary = set()
        for h in fix_path_helpers_for_summary:
            if isinstance(h, dict) and h.get("file_line"):
                pkg = _extract_package(h["file_line"].rsplit(":", 1)[0])
                if pkg:
                    packages_summary.add(pkg)
        single_layer_label = "yes" if len(packages_summary) == 1 else "no"
        lines.append("  recommended_approach.single_layer: {0}".format(single_layer_label))
    lines.append("  structured_root_cause: {0}".format(
        "set" if report.get("structured_root_cause") else "(unset)"
    ))
    lines.append("  verify_step: {0}".format("set" if report.get("verify_step") else "(unset)"))
    lines.append("  next_step_text: {0}".format("set" if report.get("next_step_text") else "(unset)"))

    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
