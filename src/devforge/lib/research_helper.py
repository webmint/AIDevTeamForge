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

Subcommand summary (49)
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
  Phase 2.4d (1) record-data-flow-chain
  Phase 2.5  (1) record-value-production-site
  Phase 2.5b (1) record-literal-archaeology
  Step 5     (1) record-probe-script
  Step 7     (2) append-outcome, check-outcome
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
import dataclasses
import datetime
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# handoff_schema import — path injection so stdlib-only helpers can import
# the schema from the _research sub-package without package install.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_RESEARCH_DIR = _HERE / "_research"
if str(_RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(_RESEARCH_DIR))
import handoff_schema  # noqa: E402

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

# Patch 8 (V3) — literal-token regex. Matches recognizable primitive literals
# as they appear in source code. Used by record-literal-archaeology's --literal
# validation AND by LITERAL_REPLACEMENT_RE to extract the <X> target from
# recommended-approach prose. Array / object / regex / function literals are
# OUT OF SCOPE (rarely surface as the "bug literal" in /research practice).
LITERAL_TOKEN_RE = re.compile(
    r"""
    (?:
        true | false | True | False        # JS/TS + Python booleans
      | null | undefined | None             # null-likes
      | -?0x[0-9a-fA-F]+                   # hex int (must come before decimal — share '-' prefix)
      | -?\d+n                              # BigInt
      | -?\d+(?:\.\d+)?[eE][+-]?\d+        # scientific
      | -?\d+(?:\.\d+)?                    # decimal int/float
      | "[^"]*"                             # double-quoted string
      | '[^']*'                             # single-quoted string
      | `[^`]*`                             # backtick template (no ${} interpolation)
    )
    """,
    re.VERBOSE,
)

# Literal-replacement prose patterns. Used by check 17 + Patch 9's
# proposed-call-shape gate. Anchors on LITERAL_TOKEN_RE to extract <X>.
# Three pattern forms (case-insensitive on the verb):
#   - "replace <X> with <Y>"
#   - "change <X> to <Y>"
#   - "<X> -> <Y>"  (also "<X> => <Y>")
# Captures <X> in group 1; <Y> capture not required for check 17 (only need
# the source literal to look up its archaeology row).
LITERAL_REPLACEMENT_RE = re.compile(
    r"""
    (?:
        (?:replace|change|swap) \s+ (?:the\s+literal\s+)? .*? (?P<src1>{LITERAL}) [^,\n]*? \s+ (?:with|to|for) \s+
      |
        (?P<src2>{LITERAL}) \s* (?:->|=>) \s*
    )
    """.replace("{LITERAL}", LITERAL_TOKEN_RE.pattern),
    re.VERBOSE | re.IGNORECASE,
)


def _detect_literal_replacement(text: str) -> Optional[str]:
    """Scan prose for a literal-replacement pattern. Returns the source
    literal (the <X> being replaced) if found, else None.

    Used by check 17 to decide whether literal-archaeology is required.
    Over-matching (false positives) is acceptable per plan §Patch 8 notes —
    better to require archaeology on a few non-literal fixes than miss
    actual literal-replacement cases.
    """
    if not text:
        return None
    m = LITERAL_REPLACEMENT_RE.search(text)
    if not m:
        return None
    return m.group("src1") or m.group("src2")


# Patch 9 (V3) — function-call-shape parser. Matches an identifier (with
# optional dotted member access) followed by a parenthesized arg list.
# Multi-line collapsed via whitespace-normalize before matching.
#
# Limitation: the inner arg-list match `[^)]*` stops at the first `)`,
# so any shape containing a nested function call in its arg list
# (e.g. `fetchOrder(makeId(user), value, value)`) fails to match and
# `_detect_arg_duplication` returns None (fail-soft, no block). The
# `_split_top_level_args` helper tracks `([{` depth correctly, but it
# is unreachable for nested-call shapes — CALL_SHAPE_RE rejects them
# first. This is by-design per plan §Patch 9 "fragile by design"
# clause; documented to prevent future-session confusion.
CALL_SHAPE_RE = re.compile(r"^[A-Za-z_][\w.]*\(([^)]*)\)$")

# Identifier-with-optional-chaining regex. Matches:
#   - bare identifier `x`
#   - dotted member access `a.b.c`
#   - optional chaining `a?.b?.c` (modern JS/TS)
# Does NOT match: function calls `f()`, bracket access `a[0]`, literals,
# arithmetic expressions. These appear in arg lists but are not the
# "duplicate identifier" pattern Patch 9 targets.
IDENT_CHAIN_RE = re.compile(r"^[A-Za-z_]\w*(?:\??\.[A-Za-z_]\w*)*$")


def _normalize_call_shape(text):
    # type: (Optional[str]) -> str
    """Collapse multi-line whitespace + strip surrounding whitespace.

    Patch 9 supports multi-line call shapes (LLM may format the proposed
    fix as multiline for readability). Normalize before regex match.
    """
    if text is None:
        return ""
    return " ".join(text.split())


def _split_top_level_args(arg_list_text):
    # type: (Optional[str]) -> Optional[List[str]]
    """Split an arg-list string on top-level commas (commas outside
    nested parens / brackets / braces). Returns list of trimmed arg
    strings, OR None on imbalanced delimiters (parser failure — caller
    should fail-soft per plan §Patch 9 'fragile by design' note).

    Empty input returns []. Single arg returns [arg]. Whitespace-only
    args are kept (caller decides if they signify a parser bug).
    """
    if arg_list_text is None:
        return []
    text = arg_list_text.strip()
    if not text:
        return []
    args = []  # type: List[str]
    depth = 0
    buf = []  # type: List[str]
    for ch in text:
        if ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                return None
            buf.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if depth != 0:
        return None
    args.append("".join(buf).strip())
    return args


def _detect_arg_duplication(call_shape):
    # type: (str) -> Optional[Tuple[str, int]]
    """Parse a function-call shape string + detect identifier
    duplication. Returns (duplicated_identifier, count) on duplication
    found; None on no duplication OR parser-failure (fail-soft —
    caller treats None as "no block").

    Steps:
      1. Normalize whitespace.
      2. Match top-level CALL_SHAPE_RE (function-name + paren arg list).
         On no match -> parser failure -> return None. Shapes containing
         nested function calls (e.g. `f(g(x), y)`) fail at this step
         because CALL_SHAPE_RE's inner `[^)]*` stops at the first `)` —
         documented limitation per CALL_SHAPE_RE comment block.
      3. Split arg list on top-level commas.
      4. For each arg, test against IDENT_CHAIN_RE. Args that don't
         match are ignored (not pure identifiers — won't count as
         duplicates even if textually identical, since they may be
         literals, function calls, expressions, etc.).
      5. Among identifier args, find any whose count > 1.
      6. Return (first_duplicated, count) or None.
    """
    if not call_shape or not call_shape.strip():
        return None
    normalized = _normalize_call_shape(call_shape)
    m = CALL_SHAPE_RE.match(normalized)
    if not m:
        return None
    arg_list_text = m.group(1)
    args = _split_top_level_args(arg_list_text)
    if args is None:
        return None
    identifiers = [a for a in args if IDENT_CHAIN_RE.match(a)]
    seen = {}  # type: Dict[str, int]
    for ident in identifiers:
        seen[ident] = seen.get(ident, 0) + 1
    for ident, count in seen.items():
        if count > 1:
            return (ident, count)
    return None


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
        # Patch 5 — anchor-gate rejection log. Each entry: {qn, file_line}.
        # Records (qn, file_line) combos rejected by the anchor check so that
        # sticky-reject can block post-hoc-anchor adversarial retries.
        "helper_rejection_log": [],
        # Patch 6 — data-flow chain (Gap 6: adapter tracing). None until
        # record-data-flow-chain fires; overwritten (last-write-wins) on re-call.
        "data_flow_chain": None,
        # Patch 7 — value production sites (Gap 7: id-stability axis). Each entry:
        # {value, file_line, is_stable}. Multi-site per value via distinct file_line
        # dedupe: same (value, file_line) pair is no-op; different file_lines append.
        "value_production_sites": [],
        # Patch 8 (V3) — literal archaeology rows for hardcoded literals that the
        # recommended approach proposes to replace. Each entry:
        # {literal, file_line, introduced_by, introduced_when, commit_subject, intent}.
        # Dedupe on (literal, file_line) — re-recording same pair is no-op.
        "literal_archaeology": [],
        # Step 4 — probe-tier feasibility (set by LLM via set-probe-feasibility before
        # finalize-handoff). All five booleans default None; helper rejects finalize-
        # handoff with any None when classifier runs. Closed enum: True/False/None.
        "probe_feasibility": {
            "data_shape_only": None,
            "auth_required": None,
            "network_dependent": None,
            "timing_dependent": None,
            "is_test_code": None,
        },
        # Step 5 — Tier-1.5 standalone probe scripts. Each entry:
        # {script_path, runtime, inlines_from: [list], recorded_at: ISO-UTC}.
        # Append-only; deduped by script_path (same path is no-op).
        # finalize-handoff uses probe_scripts[-1]["script_path"] when tier=1.5.
        "probe_scripts": [],
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
    """Parse value as JSON array of strings. Reject non-list input, non-string items, or blank items. Empty array `[]` IS accepted (callers like approach.does_not_cover, approach.cons, data_flow_chain.intermediate_qns rely on this).

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
# Step 5 — probe-script validators.
# ---------------------------------------------------------------------------

_PROBE_SCRIPT_INLINES_TOKEN_RE = re.compile(r"^[^:]+:\d+$")


def _validate_script_within_research_dir(script_path, research_date, topic_slug):
    # type: (str, str, str) -> None
    """Validate script_path exists on disk AND lives under research/<date>-<slug>/.

    Accepts both absolute and relative paths. The check inspects the path's
    directory parts: the immediate parent must be named '<date>-<slug>' and
    that parent's parent must be named 'research'.

    Raises ValueError with a caller-ready message on any violation.
    """
    expected_dir = "{0}-{1}".format(research_date, topic_slug)
    p = Path(script_path)
    # Check structural containment via path parts.
    # p.parent.name == expected_dir  AND  p.parent.parent.name == "research"
    structurally_valid = (
        p.parent.name == expected_dir
        and p.parent.parent.name == "research"
    )
    if not structurally_valid:
        raise ValueError(
            "record-probe-script: script-path must exist and live under "
            "research/{0}-{1}/ dir; got {2}".format(
                research_date, topic_slug, script_path
            )
        )
    if not p.is_file():
        raise ValueError(
            "record-probe-script: --script-path file does not exist: {0}".format(
                script_path
            )
        )


def _validate_runtime_on_path(runtime):
    # type: (str) -> None
    """Validate runtime is resolvable via shutil.which.

    Raises ValueError if not found on PATH.
    """
    if shutil.which(runtime) is None:
        raise ValueError(
            "record-probe-script: --runtime {0} not found on PATH".format(runtime)
        )


def _validate_inlines_from_tokens(json_string):
    # type: (str) -> List[str]
    """Parse --inlines-from as JSON array of path:line tokens.

    Raises ValueError with a caller-ready message if:
    - json_string is not valid JSON
    - decoded value is not a list
    - list is empty
    - any item does not match <non-empty-path>:<digits>
    Returns the list of validated token strings on success.
    """
    try:
        decoded = json.loads(json_string)
    except (ValueError, TypeError) as err:
        raise ValueError(
            "record-probe-script: --inlines-from must be non-empty JSON array of "
            '"path:line" tokens; got {0}'.format(err)
        )
    if not isinstance(decoded, list):
        raise ValueError(
            "record-probe-script: --inlines-from must be non-empty JSON array of "
            '"path:line" tokens; got non-list {0}'.format(type(decoded).__name__)
        )
    if not decoded:
        raise ValueError(
            "record-probe-script: --inlines-from must be non-empty JSON array of "
            '"path:line" tokens; got empty list'
        )
    validated = []
    for item in decoded:
        if not isinstance(item, str):
            raise ValueError(
                "record-probe-script: --inlines-from must be non-empty JSON array of "
                '"path:line" tokens; got non-string item {0!r}'.format(item)
            )
        if not _PROBE_SCRIPT_INLINES_TOKEN_RE.match(item):
            raise ValueError(
                "record-probe-script: --inlines-from must be non-empty JSON array of "
                '"path:line" tokens; got {0!r} (expected <path>:<line-number>)'.format(item)
            )
        validated.append(item)
    return validated


# ---------------------------------------------------------------------------
# Patch 5 — anchor-gate helpers (_split_path_line + _has_anchor_finding).
# ---------------------------------------------------------------------------

# Line-number tolerance window for anchor-gate collision (lenient to absorb
# minor CBM/trace offsets between a finding's recorded line and the helper's
# definition line as returned by search_graph). Single source of truth for
# the numeric tolerance; prose mentions of "±5" in docstrings and error
# messages are documentation and stay as literals.
_ANCHOR_LINE_WINDOW = 5


def _split_path_line(file_line: str) -> Tuple[Optional[str], Optional[int]]:
    """Split "path/to/file.ts:42" into ("path/to/file.ts", 42).

    Returns (None, None) for malformed input (no colon, non-integer line).
    Returns ("(none)", None) for the sentinel so (none) findings never
    accidentally match a real helper file_line (sentinels have no line number
    and therefore no ±5 neighbourhood).
    """
    if not file_line or not file_line.strip():
        return (None, None)
    stripped = file_line.strip()
    if stripped == "(none)":
        return ("(none)", None)
    colon_idx = stripped.rfind(":")
    if colon_idx <= 0:
        return (None, None)
    path_part = stripped[:colon_idx]
    line_part = stripped[colon_idx + 1:]
    if not path_part:
        return (None, None)
    try:
        line_num = int(line_part)
    except ValueError:
        return (None, None)
    return (path_part, line_num)


def _has_anchor_finding(target_file_line: str, findings: list) -> bool:
    """True iff some finding's file_line collides with target_file_line.

    Collision: exact match OR same path with line numbers within ±5
    (lenient to absorb minor CBM/trace offset). Sentinel (none) in
    target_file_line always returns False — (none) is not a real anchor.
    Per Patch 5 fix-path-helper anchor gate.
    """
    target_path, target_line = _split_path_line(target_file_line)
    if target_path is None or target_path == "(none)":
        return False
    for f in findings:
        if not isinstance(f, dict):
            continue
        fl = f.get("file_line") or ""
        if fl == target_file_line:
            return True
        f_path, f_line = _split_path_line(fl)
        if f_path is None or f_path == "(none)":
            continue
        if f_path == target_path and target_line is not None and f_line is not None:
            if abs(f_line - target_line) <= _ANCHOR_LINE_WINDOW:
                return True
    return False


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
        "finalize-handoff",
        help="Emit handoff.json from research state (terminal phase).",
    )
    sp.add_argument("--emit-handoff-json", required=True, dest="emit_handoff_json")
    sp.add_argument("--research-md-path", default=None, dest="research_md_path")
    sp.set_defaults(func=cmd_finalize_handoff)

    sp = subparsers.add_parser(
        "set-probe-feasibility",
        help="Record probe-feasibility flags (5 booleans) before finalize-handoff.",
    )
    for _flag in (
        "--data-shape-only",
        "--auth-required",
        "--network-dependent",
        "--timing-dependent",
        "--is-test-code",
    ):
        sp.add_argument(_flag, required=True, choices=("true", "false"))
    sp.set_defaults(func=cmd_set_probe_feasibility)

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
    sp.add_argument(
        "--proposed-call-shape",
        default=None,
        dest="proposed_call_shape",
        help=(
            "Exact post-fix call as it would appear at the bug site. "
            "REQUIRED when bug mode AND (--single-layer-justification is set "
            "OR --rationale contains literal-replacement prose). Helper checks "
            "for argument duplication (same identifier appearing >1 time) — "
            "duplication signals the default-source belongs at a different layer "
            "(wrapper signature / state-init / use-case default) and rejects."
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
    sp.add_argument(
        "--stable-across-calls",
        default=None,
        choices=("true", "false", "unknown"),
        dest="stable_across_calls",
        help=(
            "Stability axis for the value across the operation chain. "
            "REQUIRED when --classification invariant. "
            "Optional for other classifications (ignored if set)."
        ),
    )
    sp.set_defaults(func=cmd_set_value_semantics)

    sp = subparsers.add_parser(
        "record-value-production-site",
        help=(
            "Append a {value, file_line, is_stable} record to value_production_sites. "
            "Dedupes by (value, file_line) pair; multiple file_lines per value allowed."
        ),
    )
    sp.add_argument("--value", required=True, help="Symbol whose production site is being recorded.")
    sp.add_argument(
        "--file-line",
        required=True,
        dest="file_line",
        help="path:line where the value is randomized/rewritten (must not be (none)).",
    )
    sp.add_argument(
        "--is-stable",
        required=True,
        dest="is_stable",
        choices=("true", "false"),
        help="Whether the value is stable at this production site.",
    )
    sp.set_defaults(func=cmd_record_value_production_site)

    sp = subparsers.add_parser(
        "record-data-flow-chain",
        help=(
            "Record the data-flow chain from click handler to write-boundary call. "
            "Each intermediate must have a prior Finding row referencing it."
        ),
    )
    sp.add_argument(
        "--handler-qn",
        required=True,
        dest="handler_qn",
        help="Qualified name of the user-action handler (entry point).",
    )
    sp.add_argument(
        "--write-boundary-qn",
        required=True,
        dest="write_boundary_qn",
        help="Qualified name of the persistence / write-boundary call.",
    )
    sp.add_argument(
        "--intermediate-qns",
        required=True,
        dest="intermediate_qns",
        help=(
            "JSON array of intermediate transformer/adapter QNs between handler and "
            "write-boundary. May be empty list '[]' for direct handler→boundary calls."
        ),
    )
    sp.set_defaults(func=cmd_record_data_flow_chain)

    sp = subparsers.add_parser(
        "record-literal-archaeology",
        help=(
            "Record git-archaeology of a hardcoded literal that the recommended approach "
            "proposes to replace. Dedupes by (literal, file_line)."
        ),
    )
    sp.add_argument("--literal", required=True, help="Literal token as it appears in source (e.g. 'false', '0', \"''\").")
    sp.add_argument(
        "--file-line",
        required=True,
        dest="file_line",
        help="path:line where the literal lives (must not be (none)).",
    )
    sp.add_argument(
        "--introduced-by",
        required=True,
        dest="introduced_by",
        help="Commit SHA (7-40 hex chars) of the commit that introduced the literal.",
    )
    sp.add_argument(
        "--introduced-when",
        required=True,
        dest="introduced_when",
        help="ISO date YYYY-MM-DD when the introducing commit landed.",
    )
    sp.add_argument(
        "--commit-subject",
        required=True,
        dest="commit_subject",
        help="One-line subject from the introducing commit.",
    )
    sp.add_argument(
        "--intent",
        required=True,
        choices=("placeholder", "migrated", "deliberate", "forgotten", "inherited-refactor", "generated"),
        help="Classification of the literal's historical intent.",
    )
    sp.set_defaults(func=cmd_record_literal_archaeology)

    sp = subparsers.add_parser(
        "record-probe-script",
        help="Record a Tier-1.5 standalone probe script path + runtime + inlined-from sources.",
    )
    sp.add_argument("--script-path", required=True, dest="script_path")
    sp.add_argument(
        "--runtime",
        required=True,
        choices=("node", "python", "ruby", "deno", "bun"),
    )
    sp.add_argument(
        "--inlines-from",
        required=True,
        dest="inlines_from",
        help='JSON array of "path:line" tokens whose code the script inlines verbatim.',
    )
    sp.set_defaults(func=cmd_record_probe_script)

    # Step 7 — append-outcome.
    sp = subparsers.add_parser(
        "append-outcome",
        help="Record the post-probe outcome into handoff.json (Step 7).",
    )
    sp.add_argument("--handoff-path", required=True, dest="handoff_path",
                    help="Path to the handoff.json file (e.g. research/<NNN>/handoff.json).")
    sp.add_argument(
        "--hypothesis-confirmed",
        required=True,
        dest="hypothesis_confirmed",
        choices=("primary", "runner_up", "none", "inconclusive"),
        help="Which hypothesis the evidence confirmed.",
    )
    sp.add_argument(
        "--evidence-source",
        required=True,
        dest="evidence_source",
        choices=("test-result", "llm-ui-session-log", "user-observation"),
        help="Source of the evidence.",
    )
    sp.add_argument("--evidence-cite", required=True, dest="evidence_cite",
                    help="Path, SHA, or verbatim observation that evidences the outcome.")
    sp.add_argument("--actual-fix-path", required=True, dest="actual_fix_path",
                    help="Path(s) actually modified by the fix.")
    sp.add_argument("--delta-from-recommendation", default=None, dest="delta_from_recommendation",
                    help="Optional: how the actual fix diverged from the recommendation.")
    sp.add_argument("--confirmed-commit-sha", default=None, dest="confirmed_commit_sha",
                    help="Optional: 7-40 char hex SHA of the commit that applied the fix.")
    sp.set_defaults(func=cmd_append_outcome)

    # Step 7 — check-outcome.
    sp = subparsers.add_parser(
        "check-outcome",
        help="Print 'unmarked' or 'marked: <details>' for a handoff.json outcome block.",
    )
    sp.add_argument("--handoff-path", required=True, dest="handoff_path",
                    help="Path to the handoff.json file.")
    sp.set_defaults(func=cmd_check_outcome)


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

            # Patch 9 (V3) — proposed-call-shape gate. Required when bug mode
            # AND (single-layer-justification set OR rationale has
            # literal-replacement prose). Helper-side defense against the
            # arg-duplication failure mode (same identifier passed twice
            # in one call signals fix layer is upstream of the call site).
            if bug_mode:
                requires_shape = False
                if getattr(args, "single_layer_justification", None):
                    requires_shape = True
                # Reuse Patch 8's literal-replacement detector. Scan rationale
                # plus the linked approach.description (same scope as check 17).
                if not requires_shape:
                    linked_name = name
                    approach_desc = ""
                    for ap in report.get("approaches") or []:
                        if ap.get("name") == linked_name:
                            approach_desc = ap.get("description") or ""
                            break
                    combined = "{0} {1}".format(rationale, approach_desc)
                    if _detect_literal_replacement(combined) is not None:
                        requires_shape = True
                if requires_shape:
                    proposed_shape = getattr(args, "proposed_call_shape", None)
                    if not proposed_shape or not proposed_shape.strip():
                        return _die(
                            "set-recommended-approach: --proposed-call-shape is required "
                            "when bug mode AND (--single-layer-justification is set OR "
                            "--rationale / linked approach description contains "
                            "literal-replacement prose). Supply the exact post-fix call "
                            "as it would appear at the bug site so the helper can check "
                            "for argument duplication.",
                            code=2,
                        )
                    dup = _detect_arg_duplication(proposed_shape)
                    if dup is not None:
                        ident, count = dup
                        return _die(
                            "set-recommended-approach: --proposed-call-shape {0!r} "
                            "contains argument duplication ({1!r} appears {2} times "
                            "in the arg list). Same value passed multiple times in "
                            "one call indicates the default-source belongs at a "
                            "different layer (wrapper signature / state initialization "
                            "/ use-case default). Reconsider the fix layer and "
                            "re-draft.".format(proposed_shape, ident, count),
                            code=2,
                        )
                    # Parser may fail-soft (None); store the shape regardless so
                    # render + verify can surface it. Parser-failure = stderr
                    # advisory only, no block (per plan §Patch 9 'fragile by
                    # design' clause + 'log advisory; do NOT block /research
                    # on a parser corner case'). Emit advisory only when the
                    # outer CALL_SHAPE_RE fails (distinguishes parser-failure
                    # from genuine no-duplication — both return None from
                    # _detect_arg_duplication).
                    if not CALL_SHAPE_RE.match(_normalize_call_shape(proposed_shape)):
                        sys.stderr.write(
                            "research_helper: set-recommended-approach: "
                            "--proposed-call-shape {0!r} could not be fully "
                            "parsed (nested calls / unsupported syntax); "
                            "argument-duplication check skipped, shape stored "
                            "verbatim.\n".format(proposed_shape)
                        )
                    recommended_record["proposed_call_shape"] = proposed_shape

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

    Patch 5 — anchor gate: --file-line must collide with at least one
    existing finding's file_line (exact match OR same path with line within ±5).
    Once rejected for a (qn, file_line) combo, sticky-reject all future attempts
    with that combo even if a matching finding is added post-hoc — closes the
    adversarial generator path where the LLM unblocks rejection by recording a
    fabricated finding.
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

    # Collect the reject message and code outside the transaction so the
    # write (rejection log update) completes before we emit to stderr and return.
    reject_message = None  # type: Optional[str]
    reject_code = 0
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rejection_log = report.get("helper_rejection_log") or []
            # Sticky-reject: if this (qn, file_line) was previously rejected,
            # refuse even if findings now contain a collision (closes the
            # post-hoc-anchor adversarial path).
            for r in rejection_log:
                if r.get("qn") == helper_qn and r.get("file_line") == file_line:
                    reject_message = (
                        "record-fix-path-helper: this (helper_qn, file_line) combo was "
                        "previously rejected as unanchored ({0!r} at {1!r}); cannot retry "
                        "even if findings now contain a collision (sticky-reject closes "
                        "the post-hoc-anchor adversarial path). Either pick a different "
                        "--file-line that anchored to a finding at the time of THIS call, "
                        "or restart /research to clear rejection state.\n".format(
                            helper_qn, file_line
                        )
                    )
                    reject_code = 2
                    break

            if reject_code == 0:
                # Anchor check: does any finding's file_line collide?
                findings = report.get("findings") or []
                if not _has_anchor_finding(file_line, findings):
                    # Persist the rejection in the same transaction so future
                    # retries with the same (qn, file_line) are sticky-blocked.
                    rejection_log.append({"qn": helper_qn, "file_line": file_line})
                    report["helper_rejection_log"] = rejection_log
                    finding_paths = sorted({
                        f.get("file_line")
                        for f in findings
                        if f.get("file_line")
                    })
                    reject_message = (
                        "record-fix-path-helper: --file-line {0!r} does not anchor to any "
                        "recorded finding (no finding's file_line collides — exact match or "
                        "same path within ±5 lines). Fix-path helpers MUST anchor to CBM "
                        "evidence already in the report. Record the relevant finding via "
                        "record-finding FIRST (with the file:line from a search_graph or "
                        "search_code result row), then re-call record-fix-path-helper with "
                        "a DIFFERENT --file-line if you've identified a closer-anchored "
                        "helper site. Current finding file_lines: {1!r}.\n".format(
                            file_line, finding_paths
                        )
                    )
                    reject_code = 2

            if reject_code == 0:
                lst = report.setdefault("fix_path_helpers", [])
                # Dedupe on qn: skip if an entry with the same qn already exists.
                if not any(entry.get("qn") == helper_qn for entry in lst):
                    lst.append({"qn": helper_qn, "file_line": file_line})

    except (OSError, json.JSONDecodeError) as err:
        return _die("record-fix-path-helper: {0}".format(err))

    if reject_code == 2:
        sys.stderr.write(reject_message)
        return 2
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

    Last-write-wins on value key. When classification==invariant, requires:
      - --stable-across-calls (true|false|unknown) — REQUIRED for invariant.
      - At least one consumer_chain row with matching value field.
      - When --stable-across-calls==unknown AND symptom is presentation-layer,
        rejected (must investigate via Phase 2.4d data-flow chain first).
      - When --stable-across-calls==false, at least one value_production_sites
        row must already exist for this value.

    Row shape: {value, classification, evidence} for non-invariant.
               {value, classification, evidence, stable_across_calls} for invariant.
    """
    try:
        value = _validate_scalar(args.value, "value_semantics.value")
        evidence = _validate_scalar(args.evidence, "value_semantics.evidence")
    except ValueError as err:
        return _die(str(err), code=2)
    # classification is already constrained by argparse choices=
    classification = args.classification
    stable_across_calls = getattr(args, "stable_across_calls", None)

    # Invariant guards: all checked before entering the state transaction so
    # the file is never rewritten on a validation rejection.
    if classification == "invariant":
        # Gate 1: --stable-across-calls is required when classification==invariant.
        if stable_across_calls is None:
            return _die(
                "set-value-semantics: --stable-across-calls is required when "
                "--classification == 'invariant'; values invariant by kind may still be "
                "randomized per call (the production-site rewriter pattern). "
                "Pass --stable-across-calls true|false|unknown.",
                code=2,
            )

        try:
            report_snapshot = _load_report(args.devforge_dir)
        except (OSError, json.JSONDecodeError) as err:
            return _die("set-value-semantics: {0}".format(err))

        # Gate 2: --stable-across-calls==unknown + presentation-layer → reject.
        if stable_across_calls == "unknown":
            # Determine if the primary finding is presentation-layer (same pattern
            # as check 8b / check 15 in cmd_verify).
            all_findings = report_snapshot.get("findings") or []
            primary_path = None  # type: Optional[str]
            for f in all_findings:
                framing_val = f.get("framing") or "primary"
                if framing_val == "primary":
                    fl = f.get("file_line") or ""
                    colon_pos = fl.rfind(":")
                    if colon_pos > 0:
                        primary_path = fl[:colon_pos]
                    elif fl:
                        primary_path = fl
                    break
            if primary_path and _is_presentation_layer(primary_path):
                return _die(
                    "set-value-semantics: --stable-across-calls cannot be 'unknown' when "
                    "--classification is 'invariant' AND symptom is presentation-layer; "
                    "investigate the production site (where the value is assigned) "
                    "via Phase 2.4d data-flow chain (already recorded) before classifying",
                    code=2,
                )

        # Gate 3: consumer_chain row required.
        chain = report_snapshot.get("consumer_chain") or []
        if not any(r.get("value") == value for r in chain):
            return _die(
                "set-value-semantics: classification=invariant requires at least one "
                "consumer_chain entry for value={0!r}; record-consumer-chain first".format(value),
                code=2,
            )

        # Gate 4: --stable-across-calls==false requires at least one
        # value_production_sites row for this value.
        if stable_across_calls == "false":
            sites = report_snapshot.get("value_production_sites") or []
            if not any(s.get("value") == value for s in sites):
                return _die(
                    "set-value-semantics: --stable-across-calls=false for value {0!r} requires "
                    "at least one record-value-production-site call for this value first. Call "
                    "record-value-production-site with the file:line where the value is "
                    "randomized/rewritten (e.g., Math.random, Date.now, manual id reassignment), "
                    "then re-run set-value-semantics.".format(value),
                    code=2,
                )

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rows = report.setdefault("value_semantics", [])
            # Build row — include stable_across_calls only for invariant classification.
            if classification == "invariant":
                new_row = {
                    "value": value,
                    "classification": classification,
                    "evidence": evidence,
                    "stable_across_calls": stable_across_calls,
                }
            else:
                new_row = {"value": value, "classification": classification, "evidence": evidence}
            for i, row in enumerate(rows):
                if row.get("value") == value:
                    rows[i] = new_row
                    break
            else:
                rows.append(new_row)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-value-semantics: {0}".format(err))
    return 0


# --- Patch 7: value production site setter -----------------------------------


def cmd_record_value_production_site(args: argparse.Namespace) -> int:
    """Append a {value, file_line, is_stable} record to value_production_sites.

    Dedupes by (value, file_line) pair: same pair is no-op (do not append,
    do not modify). Multiple file_lines for the same value all append
    (multi-site per value, concern C5).

    Rejects (none) sentinel for file_line — production site must be a real path.
    """
    try:
        value = _validate_scalar(args.value, "value_production_sites.value")
        file_line = _validate_file_line(args.file_line, "value_production_sites.file_line")
    except ValueError as err:
        return _die(str(err), code=2)

    # Reject (none) sentinel — production site must be a real path.
    if file_line == "(none)":
        return _die(
            "record-value-production-site: --file-line cannot be (none) — "
            "production site must be a real path",
            code=2,
        )

    # args.is_stable is constrained by argparse choices=("true","false").
    # Store as string (not bool) so the field is type-consistent with
    # value_semantics.stable_across_calls ("true"/"false"/"unknown").
    is_stable_str = args.is_stable

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            sites = report.setdefault("value_production_sites", [])
            # Dedupe by (value, file_line) pair.
            for existing in sites:
                if existing.get("value") == value and existing.get("file_line") == file_line:
                    # No-op: same (value, file_line) already recorded.
                    return 0
            sites.append({"value": value, "file_line": file_line, "is_stable": is_stable_str})
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-value-production-site: {0}".format(err))
    return 0


# --- Patch 6: data-flow chain setter ----------------------------------------


def cmd_record_data_flow_chain(args: argparse.Namespace) -> int:
    """Record the data-flow chain from click handler to write-boundary call.

    Validates each intermediate has a prior Finding row referencing its QN
    (substring match in finding's relevance or surface). Persists
    {handler_qn, write_boundary_qn, intermediate_qns} to report state.
    Last-write-wins — subsequent calls overwrite the prior chain.

    Empty intermediate_qns list [] is valid (direct handler→write-boundary).

    Gate: each intermediate_qn must appear in at least one existing Finding's
    relevance or surface field (simple substring match). The spec instructs
    the LLM to record intermediates via record-finding --surface / --relevance
    before calling this setter.

    KNOWN GAP: intermediate-qn ↔ Finding cross-check runs only at set time.
    Direct JSON mutation that writes an arbitrary truthy `data_flow_chain`
    value bypasses this validation; verify check 15 only confirms the field
    is non-null at verify time and does NOT re-validate intermediate_qns
    against findings. Closing the gap would require a verify-time re-walk
    of the same substring check — deferred until empirical evidence shows
    the bypass is being exploited.
    """
    try:
        handler_qn = _validate_scalar(args.handler_qn, "data_flow_chain.handler_qn")
        write_boundary_qn = _validate_scalar(
            args.write_boundary_qn, "data_flow_chain.write_boundary_qn"
        )
        intermediate_qns = _validate_string_array_json(
            args.intermediate_qns, "data_flow_chain.intermediate_qns"
        )
    except ValueError as err:
        return _die(str(err), code=2)

    # Validate each intermediate has a Finding row referencing it before entering
    # the state transaction (so the file is never rewritten on validation failure).
    if intermediate_qns:
        try:
            report_snapshot = _load_report(args.devforge_dir)
        except (OSError, json.JSONDecodeError) as err:
            return _die("record-data-flow-chain: {0}".format(err))
        findings = report_snapshot.get("findings") or []
        for qn in intermediate_qns:
            referenced = any(
                qn in (f.get("relevance") or "") or qn in (f.get("surface") or "")
                for f in findings
            )
            if not referenced:
                existing_surfaces = sorted(
                    f.get("surface") or "" for f in findings if f.get("surface")
                )
                return _die(
                    "record-data-flow-chain: intermediate_qn {0!r} has no Finding row "
                    "referencing it (record-finding must be called for each intermediate "
                    "before record-data-flow-chain). Existing findings: {1!r}".format(
                        qn, existing_surfaces
                    ),
                    code=2,
                )

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["data_flow_chain"] = {
                "handler_qn": handler_qn,
                "write_boundary_qn": write_boundary_qn,
                "intermediate_qns": intermediate_qns,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-data-flow-chain: {0}".format(err))
    return 0


# --- Patch 8: literal-archaeology setter ------------------------------------


def cmd_record_literal_archaeology(args: argparse.Namespace) -> int:
    """Append a {literal, file_line, introduced_by, introduced_when, commit_subject, intent}
    record to literal_archaeology.

    Dedupes by (literal, file_line) pair: re-recording the same pair is a no-op
    (original intent is retained; no error emitted — matches record-value-production-site
    behavior). Multiple file_lines for the same literal are all appended.

    Validates:
      - --literal: non-empty + must fully match LITERAL_TOKEN_RE (primitive only).
      - --file-line: via _validate_file_line; (none) sentinel rejected.
      - --introduced-by: 7-40 hex char commit SHA.
      - --introduced-when: ISO date YYYY-MM-DD.
      - --commit-subject: non-empty.
      - --intent: enforced by argparse choices.
    """
    # Validate --literal: non-empty, then fullmatch against LITERAL_TOKEN_RE.
    literal_raw = args.literal
    if not literal_raw or not literal_raw.strip():
        return _die(
            "record-literal-archaeology: --literal value cannot be empty",
            code=2,
        )
    literal = literal_raw.strip()
    if not re.fullmatch(LITERAL_TOKEN_RE.pattern, literal, re.VERBOSE):
        return _die(
            "record-literal-archaeology: --literal {0!r} is not a recognizable literal "
            "token (expected: bool / number / null-like / quoted string; arrays / objects "
            "/ regex / function literals are out of scope — record them as findings "
            "instead).".format(literal),
            code=2,
        )

    # Validate --file-line via existing helper; then reject (none) sentinel.
    try:
        file_line = _validate_file_line(args.file_line, "literal_archaeology.file_line")
    except ValueError as err:
        return _die(str(err), code=2)
    if file_line == "(none)":
        return _die(
            "record-literal-archaeology: --file-line cannot be (none) — "
            "archaeology requires a real path",
            code=2,
        )

    # Validate --introduced-by: 7-40 hex chars.
    introduced_by = args.introduced_by.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", introduced_by):
        return _die(
            "record-literal-archaeology: --introduced-by {0!r} must be a 7-40 char hex "
            "commit SHA.".format(introduced_by),
            code=2,
        )

    # Validate --introduced-when: ISO date YYYY-MM-DD.
    introduced_when = args.introduced_when.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", introduced_when):
        return _die(
            "record-literal-archaeology: --introduced-when {0!r} must be ISO date "
            "YYYY-MM-DD.".format(introduced_when),
            code=2,
        )
    try:
        datetime.date.fromisoformat(introduced_when)
    except ValueError:
        return _die(
            "record-literal-archaeology: --introduced-when {0!r} must be ISO date "
            "YYYY-MM-DD.".format(introduced_when),
            code=2,
        )

    # Validate --commit-subject: non-empty.
    try:
        commit_subject = _validate_scalar(args.commit_subject, "literal_archaeology.commit_subject")
    except ValueError as err:
        return _die(str(err), code=2)

    # --intent is enforced by argparse choices.
    intent = args.intent

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rows = report.setdefault("literal_archaeology", [])
            # Dedupe by (literal, file_line) pair — no-op if same pair exists.
            for existing in rows:
                if existing.get("literal") == literal and existing.get("file_line") == file_line:
                    return 0
            rows.append({
                "literal": literal,
                "file_line": file_line,
                "introduced_by": introduced_by,
                "introduced_when": introduced_when,
                "commit_subject": commit_subject,
                "intent": intent,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-literal-archaeology: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Step 5 — record-probe-script command.
# ---------------------------------------------------------------------------


def cmd_record_probe_script(args: argparse.Namespace) -> int:
    """Append {script_path, runtime, inlines_from, recorded_at} to probe_scripts.

    Validates:
      - script_path exists on disk AND lives under research/<date>-<slug>/
      - runtime resolves via shutil.which
      - inlines_from is a non-empty JSON array of path:line tokens
    Idempotent: same script_path is a no-op (exit 0 + stderr notice).
    """
    devforge_dir = args.devforge_dir

    # Load report to read date + topic_slug for path validation.
    try:
        report_snapshot = _load_report(devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-probe-script: cannot load report state: {0}".format(err))

    research_date = (report_snapshot.get("date") or "").strip()
    if not research_date:
        return _die(
            "record-probe-script: report.date not set; run set-date first",
            code=2,
        )

    try:
        memo_snapshot = _load_memo(devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-probe-script: cannot load memo state: {0}".format(err))

    topic_slug = (memo_snapshot.get("topic_slug") or "").strip()
    if not topic_slug:
        return _die(
            "record-probe-script: memo.topic_slug not set; run set-topic first",
            code=2,
        )

    script_path = args.script_path

    # Validate script_path is within the research dir and exists on disk.
    try:
        _validate_script_within_research_dir(script_path, research_date, topic_slug)
    except ValueError as err:
        return _die(str(err), code=2)

    # Validate runtime on PATH.
    try:
        _validate_runtime_on_path(args.runtime)
    except ValueError as err:
        return _die(str(err), code=2)

    # Validate --inlines-from JSON tokens.
    try:
        inlines_from = _validate_inlines_from_tokens(args.inlines_from)
    except ValueError as err:
        return _die(str(err), code=2)

    runtime = args.runtime

    # F5: Pre-check idempotency BEFORE entering the transaction (avoids no-op fsync).
    try:
        report_preread = _load_report(devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-probe-script: cannot load report state: {0}".format(err))

    existing = next(
        (e for e in report_preread.get("probe_scripts", [])
         if e.get("script_path") == script_path),
        None,
    )
    if existing is not None:
        # F3: Strict-match idempotency — same path must carry same runtime + inlines_from.
        if existing.get("runtime") != runtime or existing.get("inlines_from") != inlines_from:
            return _die(
                "record-probe-script: script_path {0!r} already recorded with "
                "different runtime/inlines_from; remove via reset-report and re-record"
                .format(script_path),
                code=2,
            )
        # Exact match → no-op (true idempotent).
        sys.stderr.write(
            "record-probe-script: script_path already recorded (exact match); no-op\n"
        )
        return 0

    recorded_at = datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds"
    )

    # Append path — real work needs transaction.
    try:
        with _state_transaction(devforge_dir, "report") as report:
            report.setdefault("probe_scripts", []).append({
                "script_path": script_path,
                "runtime": runtime,
                "inlines_from": inlines_from,
                "recorded_at": recorded_at,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-probe-script: {0}".format(err))
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
      12. Value Semantics (when present)
      13. Value Production Sites (when present)
      14. Literal Archaeology (when present)
      15. Open Uncertainties (when gaps present)
      16. Next step (when verdict proceeds)
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
            # Patch 9 (V3): surface proposed_call_shape under the
            # recommended-approach section when present.
            proposed_shape_render = rec.get("proposed_call_shape")
            if proposed_shape_render:
                out.append("")
                out.append("**Proposed call shape:**")
                out.append("```")
                out.append(proposed_shape_render)
                out.append("```")
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

    # Value Semantics (Patch 7: stability column for invariant rows).
    value_semantics = report.get("value_semantics") or []
    if value_semantics:
        out.append("## Value Semantics")
        out.append("")
        out.append("| Value | Classification | Evidence | Stability |")
        out.append("|---|---|---|---|")
        for vs in value_semantics:
            # Non-invariant rows have no stability axis — render "—". Invariant rows
            # show the stable_across_calls value (or "—" if missing, which should
            # not occur post-Patch-7 but stays defensive).
            if vs.get("classification") == "invariant":
                stability = vs.get("stable_across_calls") or "—"
            else:
                stability = "—"
            out.append("| {0} | {1} | {2} | {3} |".format(
                _md_escape_cell(vs.get("value") or ""),
                _md_escape_cell(vs.get("classification") or ""),
                _md_escape_cell(vs.get("evidence") or ""),
                _md_escape_cell(stability),
            ))
        out.append("")

    # Value Production Sites (Patch 7: where values are randomized/rewritten).
    value_production_sites = report.get("value_production_sites") or []
    if value_production_sites:
        out.append("## Value Production Sites")
        out.append("")
        out.append("| Value | File:line | Is Stable |")
        out.append("|---|---|---|")
        for site in value_production_sites:
            is_stable_str = site.get("is_stable") or "false"
            out.append("| {0} | {1} | {2} |".format(
                _md_escape_cell(site.get("value") or ""),
                _md_escape_cell(site.get("file_line") or ""),
                is_stable_str,
            ))
        out.append("")

    # Literal Archaeology (Patch 8 V3: historical-intent classification for
    # hardcoded literals the recommended approach proposes to replace).
    literal_archaeology = report.get("literal_archaeology") or []
    if literal_archaeology:
        out.append("## Literal Archaeology")
        out.append("")
        out.append("| Literal | File:line | Introduced by | When | Commit subject | Intent |")
        out.append("|---|---|---|---|---|---|")
        for row in literal_archaeology:
            out.append("| {0} | {1} | {2} | {3} | {4} | {5} |".format(
                _md_escape_cell(row.get("literal") or ""),
                _md_escape_cell(row.get("file_line") or ""),
                _md_escape_cell(row.get("introduced_by") or ""),
                _md_escape_cell(row.get("introduced_when") or ""),
                _md_escape_cell(row.get("commit_subject") or ""),
                _md_escape_cell(row.get("intent") or ""),
            ))
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
     14. Anchor gate mirror (verify-time): every fix_path_helpers[].file_line
         must anchor to a finding (exact match OR same path within ±5 lines).
         Catches direct state mutation bypassing record-fix-path-helper setter.
         Gated on bug mode (consistent with checks 8 / 13).
     15. Data-flow chain required for bug mode + presentation-layer primary
         symptom: data_flow_chain must be non-null. Fires only when mode==bug
         AND the first primary finding's path is presentation-layer. Forces
         the LLM to trace from click handler through intermediates to the
         write-boundary call via record-data-flow-chain (Patch 6 / Gap 6).
     16. Hypothesis must cite production-site rewriter when any value_semantics
         row has stable_across_calls=false. Gated on bug mode. Fires when
         unstable value(s) exist in value_semantics AND no hypothesis cause
         contains any production-site file_line as a substring. Closes Gap 7
         — forces Phase 2.5 to enumerate the production-site rewriter (e.g.,
         Math.random, Date.now) as a candidate root cause when randomization
         is detected (Patch 7).
     17. Literal-archaeology required when recommended-approach prose contains
         a literal-replacement pattern ("replace <X> with <Y>" / "<X> -> <Y>"
         / etc.) and <X> is a primitive literal. Gated on bug mode. Fires when
         no literal_archaeology row exists whose literal == <X> AND whose
         file_line matches a recorded finding's file_line. Closes Gap 8 (V3)
         — forces git-blame archaeology before recommending literal replacement
         (Patch 8).

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

    # Check 14: anchor gate mirror — every fix_path_helpers[].file_line must
    # anchor to a finding (exact match OR same path within ±5 lines). Catches
    # state mutations that bypassed the record-fix-path-helper setter.
    # Gated on bug mode (consistent with checks 8 / 13).
    bug_mode_14 = (report.get("mode") == "bug" or memo.get("mode") == "bug")
    if bug_mode_14 and fix_path_helpers:
        all_findings_14 = report.get("findings") or []
        for h in fix_path_helpers:
            if not isinstance(h, dict):
                continue
            h_fl = h.get("file_line") or ""
            if not _has_anchor_finding(h_fl, all_findings_14):
                violations.append(
                    "check 14: fix_path_helper {0!r} has file_line {1!r} that does not "
                    "anchor to any recorded finding (exact match or same path within ±5 "
                    "lines); direct state mutation likely bypassed record-fix-path-helper "
                    "anchor gate".format(h.get("qn"), h_fl)
                )

    # Check 15: data-flow chain required for bug mode + presentation-layer symptom.
    # Fires when mode==bug AND the first primary finding's path is presentation-layer.
    # Requires data_flow_chain to be non-null (set via record-data-flow-chain).
    # NOTE: check 15 is set-time only — intermediate_qns→Finding references are
    # validated at record-data-flow-chain call time and not re-walked here.
    # Direct JSON mutation that sets an arbitrary truthy value bypasses the
    # intermediate gate. Deferred until empirical evidence shows the bypass is
    # exploited; closing it would require duplicating the substring check here.
    bug_mode_15 = (report.get("mode") == "bug" or memo.get("mode") == "bug")
    if bug_mode_15:
        # Reuse the primary finding path extraction pattern from check 8b.
        all_findings_15 = report.get("findings") or []
        primary_path_15 = None  # type: Optional[str]
        for f in all_findings_15:
            framing_val = f.get("framing") or "primary"
            if framing_val == "primary":
                fl = f.get("file_line") or ""
                colon_pos = fl.rfind(":")
                if colon_pos > 0:
                    primary_path_15 = fl[:colon_pos]
                elif fl:
                    primary_path_15 = fl
                break  # first primary finding only
        if primary_path_15 and _is_presentation_layer(primary_path_15):
            if not report.get("data_flow_chain"):
                violations.append(
                    "check 15: data_flow_chain is unset for bug-mode + presentation-layer "
                    "symptom at {0!r}; Phase 2.4d MANDATORY — trace from click handler to "
                    "write-boundary call via trace_path mode=calls and record via "
                    "record-data-flow-chain".format(primary_path_15)
                )

    # Check 16: when any value_semantics row has stable_across_calls=false, at least
    # one hypothesis must cite the production-site rewriter file:line. Closes Gap 7 —
    # forces hypothesis enumeration to surface the production-site rewriter as a
    # candidate root cause when randomization is detected.
    bug_mode_16 = (report.get("mode") == "bug" or memo.get("mode") == "bug")
    if bug_mode_16:
        unstable_values = [
            v["value"]
            for v in (report.get("value_semantics") or [])
            if v.get("stable_across_calls") == "false"
        ]
        if unstable_values:
            production_sites = report.get("value_production_sites") or []
            hypothesis_causes = [
                h.get("cause") or ""
                for h in (report.get("hypotheses") or [])
            ]
            # For all unstable values, gather their production-site file_line strings.
            all_site_file_lines = [
                s["file_line"]
                for s in production_sites
                if s.get("value") in unstable_values and s.get("file_line")
            ]
            # At least one hypothesis cause must contain at least one site file_line.
            # Use word-boundary lookahead so "src/foo.ts:5" does NOT match "src/foo.ts:50"
            # (prefix collision would let the LLM cite an adjacent-but-wrong line).
            def _cause_cites_site(cause: str, site_fl: str) -> bool:
                return bool(re.search(re.escape(site_fl) + r"(?!\d)", cause))

            cited = any(
                _cause_cites_site(cause, site_fl)
                for cause in hypothesis_causes
                for site_fl in all_site_file_lines
            )
            if not cited:
                violations.append(
                    "check 16: value_semantics has invariant-but-unstable row(s) "
                    "({0}) but no hypothesis cites the production-site rewriter "
                    "file_line ({1}); Phase 2.5 must enumerate the production-site "
                    "rewriter as a candidate root cause".format(
                        unstable_values,
                        [s.get("file_line") for s in production_sites
                         if s.get("value") in unstable_values],
                    )
                )

    # Patch 8 (V3) — Gap 8: literal-archaeology requirement on bug-mode
    # recommended approach. When the recommended approach's rationale OR the
    # linked approach.description contains a literal-replacement pattern
    # ("replace <X> with <Y>" / "<X> -> <Y>" / etc.) where <X> is a primitive
    # literal, require a matching literal_archaeology row.
    bug_mode_17 = (report.get("mode") == "bug" or memo.get("mode") == "bug")
    rec_approach = report.get("recommended_approach") or {}
    if bug_mode_17 and rec_approach:
        # Pull prose from BOTH the rationale AND the linked approach's description.
        rationale_text = rec_approach.get("rationale") or ""
        linked_name = rec_approach.get("name")
        approach_desc = ""
        if linked_name:
            for ap in report.get("approaches") or []:
                if ap.get("name") == linked_name:
                    approach_desc = ap.get("description") or ""
                    break
        combined_text = "{0} {1}".format(rationale_text, approach_desc)
        detected_literal = _detect_literal_replacement(combined_text)
        if detected_literal is not None:
            archaeology = report.get("literal_archaeology") or []
            # Collect file_lines from findings (anchor surface).
            finding_file_lines = {
                f.get("file_line") for f in (report.get("findings") or [])
                if f.get("file_line")
            }
            # Match: at least one archaeology row whose literal == detected_literal
            # AND whose file_line ∈ findings[].file_line.
            matched = any(
                row.get("literal") == detected_literal
                and row.get("file_line") in finding_file_lines
                for row in archaeology
            )
            if not matched:
                violations.append(
                    "check 17: recommended approach proposes replacing literal "
                    "{0!r} (detected in rationale or linked approach description) "
                    "but no literal_archaeology record exists for it at a recorded "
                    "finding's file_line. Run `git log -S {0!r} -- <file>` + "
                    "`git blame -L <start>,<end> <file>`; classify intent "
                    "(placeholder / migrated / deliberate / forgotten / "
                    "inherited-refactor / generated); then call "
                    "record-literal-archaeology before set-recommended-approach.".format(
                        detected_literal
                    )
                )

    # Patch 9 (V3) — Gap 9: argument-duplication shape check at verify
    # time. Mirrors the setter gate; catches state-mutation bypass where
    # someone wrote proposed_call_shape directly to JSON without going
    # through set-recommended-approach.
    bug_mode_18 = (report.get("mode") == "bug" or memo.get("mode") == "bug")
    rec_approach_18 = report.get("recommended_approach") or {}
    if bug_mode_18 and rec_approach_18:
        proposed_shape_18 = rec_approach_18.get("proposed_call_shape")
        if proposed_shape_18:
            dup_18 = _detect_arg_duplication(proposed_shape_18)
            if dup_18 is not None:
                ident_18, count_18 = dup_18
                violations.append(
                    "check 18: recommended_approach.proposed_call_shape "
                    "{0!r} contains argument duplication ({1!r} appears "
                    "{2} times). Default-source belongs at a different "
                    "layer (wrapper signature / state initialization / "
                    "use-case default); re-call set-recommended-approach "
                    "with a non-duplicating shape.".format(
                        proposed_shape_18, ident_18, count_18
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
    # Rejection log: surface count when non-empty (useful debug signal for anchor gate).
    rejection_log_for_summary = report.get("helper_rejection_log") or []
    if rejection_log_for_summary:
        lines.append("  helper_rejection_count: {0}".format(len(rejection_log_for_summary)))

    sys.stdout.write("\n".join(lines) + "\n")
    return 0


# ---------------------------------------------------------------------------
# finalize-handoff: private helper utilities.
# ---------------------------------------------------------------------------


def _to_snake_case(text):
    # type: (str) -> str
    """Convert arbitrary text to snake_case identifier. Strips/normalizes."""
    s = re.sub(r'[^A-Za-z0-9]+', '_', text.strip()).strip('_').lower()
    return s or "unnamed"


def _derive_scope(scope_text):
    # type: (Optional[str]) -> str
    """Best-effort enum derivation from free-text scope dimension."""
    if not scope_text:
        return "feature-wide"
    t = scope_text.lower()
    if "system" in t or "cross-package" in t or "monorepo" in t:
        return "system-wide"
    if "package" in t or "module" in t:
        return "package-local"
    if "file" in t or "function" in t or "line" in t:
        return "file-local"
    return "feature-wide"


_SPEC_TYPE_HINT_MAP = {
    "bug": "bug_fix",
    "enhancement": "feature_addition",  # research_helper MODE_ENUM uses "enhancement"
    "feature_addition": "feature_addition",
    "migration": "migration_tooling",
    "refactor": "refactor",
    "greenfield": "greenfield_feature",
}  # type: Dict[str, str]

# Map research_helper memo mode → handoff schema Handoff.mode value.
# Handoff schema _VALID_MODE = {bug, feature_addition, migration, refactor, greenfield}.
# research_helper MODE_ENUM = {bug, enhancement}.
# "enhancement" maps to "feature_addition" as the closest handoff schema equivalent.
_MEMO_MODE_TO_HANDOFF_MODE = {
    "bug": "bug",
    "enhancement": "feature_addition",
}  # type: Dict[str, str]


def _build_constraints(constitution_constraints):
    # type: (List[dict]) -> List[handoff_schema.Constraint]
    """Map report.constitution_constraints rows to Constraint dataclass list.

    State shape: {rule, impact}.
    The state has no anchor/rule_text — rule is the full text, no anchor field.
    All rows map to kind="follow" since the state has no anchor field.
    """
    result = []
    for row in constitution_constraints:
        rule_text = (row.get("rule") or "").strip()
        if not rule_text:
            continue
        result.append(handoff_schema.Constraint(kind="follow", content=rule_text))
    return result


def _build_affected_areas(fix_path_helpers, value_production_sites):
    # type: (List[dict], List[dict]) -> List[handoff_schema.AffectedArea]
    """Derive AffectedArea list by grouping file_lines by package.

    Sources: fix_path_helpers (each has file_line) and value_production_sites
    (each has file_line). Groups by package; each group becomes one AffectedArea.
    Empty both inputs → empty list.
    """
    # Collect (package, file_line) pairs from both sources.
    pkg_to_files = {}  # type: Dict[str, List[str]]
    for h in fix_path_helpers:
        fl = h.get("file_line") or ""
        if not fl:
            continue
        path_part = fl.rsplit(":", 1)[0] if ":" in fl else fl
        pkg = _extract_package(path_part)
        if not pkg:
            pkg = path_part
        pkg_to_files.setdefault(pkg, [])
        if fl not in pkg_to_files[pkg]:
            pkg_to_files[pkg].append(fl)
    for s in value_production_sites:
        fl = s.get("file_line") or ""
        if not fl:
            continue
        path_part = fl.rsplit(":", 1)[0] if ":" in fl else fl
        pkg = _extract_package(path_part)
        if not pkg:
            pkg = path_part
        pkg_to_files.setdefault(pkg, [])
        if fl not in pkg_to_files[pkg]:
            pkg_to_files[pkg].append(fl)
    if not pkg_to_files:
        return []
    return [
        handoff_schema.AffectedArea(area=pkg, files=files, impact="see findings")
        for pkg, files in sorted(pkg_to_files.items())
    ]


def _build_risks(complexity):
    # type: (Optional[dict]) -> List[handoff_schema.Risk]
    """Derive Risk list from complexity record.

    One risk entry when risk != 'Low'; empty list when complexity is None or risk is Low.
    """
    if complexity is None:
        return []
    risk_level = complexity.get("risk") or "Low"
    if risk_level == "Low":
        return []
    risk_notes = (complexity.get("risk_notes") or "").strip() or "see complexity"
    return [
        handoff_schema.Risk(
            risk=risk_notes,
            likelihood=risk_level,
            impact=risk_level,
            mitigation="tbd via /plan",
        )
    ]


def _build_value_semantics(value_semantics_rows):
    # type: (List[dict]) -> List[handoff_schema.ValueSemantics]
    """Map report.value_semantics rows to ValueSemantics dataclass list.

    State shape: {value, classification, evidence} or with stable_across_calls.
    Drops 'evidence' field (not in schema).
    """
    result = []
    for row in value_semantics_rows:
        value = (row.get("value") or "").strip()
        classification = (row.get("classification") or "").strip()
        stable_across_calls = row.get("stable_across_calls")
        if not value or not classification:
            continue
        result.append(handoff_schema.ValueSemantics(
            value=value,
            classification=classification,
            stable_across_calls=stable_across_calls,
        ))
    return result


def _build_value_production_sites(vps_rows):
    # type: (List[dict]) -> List[handoff_schema.ValueProductionSite]
    """Map report.value_production_sites rows to ValueProductionSite dataclass list.

    State stores is_stable as string "true"/"false"; schema requires bool.
    """
    result = []
    for row in vps_rows:
        value = (row.get("value") or "").strip()
        file_line = (row.get("file_line") or "").strip()
        is_stable_raw = row.get("is_stable")
        if not value or not file_line:
            continue
        # Convert string "true"/"false" to bool.
        if isinstance(is_stable_raw, bool):
            is_stable = is_stable_raw
        elif isinstance(is_stable_raw, str):
            is_stable = is_stable_raw.lower() == "true"
        else:
            is_stable = True  # safe default
        result.append(handoff_schema.ValueProductionSite(
            value=value,
            file_line=file_line,
            is_stable=is_stable,
        ))
    return result


def _build_literal_archaeology(la_rows):
    # type: (List[dict]) -> List[handoff_schema.LiteralArchaeology]
    """Map report.literal_archaeology rows to LiteralArchaeology dataclass list.

    Passes through directly; schema validates each row.
    """
    result = []
    for row in la_rows:
        result.append(handoff_schema.LiteralArchaeology(
            literal=row.get("literal") or "",
            file_line=row.get("file_line") or "",
            introduced_by=row.get("introduced_by") or "",
            introduced_when=row.get("introduced_when") or "",
            commit_subject=row.get("commit_subject") or "",
            intent=row.get("intent") or "",
        ))
    return result


def _build_data_flow_chain(dfc):
    # type: (Optional[dict]) -> Optional[handoff_schema.DataFlowChain]
    """Map report.data_flow_chain dict to DataFlowChain dataclass.

    State shape: {handler_qn, write_boundary_qn, intermediate_qns}.
    trace_mode is not in state — default to "calls" (most common case).
    """
    if dfc is None:
        return None
    return handoff_schema.DataFlowChain(
        handler_qn=dfc.get("handler_qn") or "",
        write_boundary_qn=dfc.get("write_boundary_qn") or "",
        intermediate_qns=dfc.get("intermediate_qns") or [],
        trace_mode=dfc.get("trace_mode") or "calls",
    )


def _build_open_questions(open_uncertainties):
    # type: (List[str]) -> List[handoff_schema.OpenQuestion]
    """Map open_uncertainties list of strings to OpenQuestion dataclass list."""
    result = []
    for item in open_uncertainties:
        if not isinstance(item, str):
            continue
        item = item.strip()
        if not item:
            continue
        result.append(handoff_schema.OpenQuestion(question=item, blocking=False))
    return result


def _resolve_cite_to_file_line(report, cite):
    # type: (dict, str) -> str
    """Resolve a cite QN token to a file_line via state lookup.

    Cites are QN tokens validated against fix_path_helpers / consumer_chain /
    value_semantics / dead_siblings. This walks each list in order looking
    for a token-match and returns the matched row's file_line. Falls back to
    the cite token if no match — Step 6 import-handoff surfaces unresolved
    entries.
    """
    for h in report.get("fix_path_helpers") or []:
        if isinstance(h, dict) and h.get("qn") == cite and h.get("file_line"):
            return h["file_line"]
    for c in report.get("consumer_chain") or []:
        if isinstance(c, dict) and c.get("consumer_qn") == cite and c.get("file_line"):
            return c["file_line"]
    for v in report.get("value_semantics") or []:
        if isinstance(v, dict) and v.get("value") == cite and v.get("file_line"):
            return v["file_line"]
    for d in report.get("dead_siblings") or []:
        if isinstance(d, dict) and d.get("method_qn") == cite and d.get("file_line"):
            return d["file_line"]
    return cite


def _build_cited_patterns(cites, report=None):
    # type: (List[str], Optional[dict]) -> List[handoff_schema.CitedPattern]
    """Map a list of cite tokens to CitedPattern dataclass list.

    When report is provided, resolves each cite token to a file_line via
    state lookup (_resolve_cite_to_file_line). Falls back to the cite token
    itself when no match is found.
    """
    if report is None:
        report = {}
    result = []
    for cite in cites:
        if not cite or not cite.strip():
            continue
        result.append(handoff_schema.CitedPattern(
            qn=cite.strip(),
            file_line=_resolve_cite_to_file_line(report, cite.strip()),
        ))
    return result


def _build_alternatives(approaches, recommended_name):
    # type: (List[dict], str) -> List[handoff_schema.Alternative]
    """Build alternatives list from all approaches excluding the recommended one."""
    result = []
    for ap in approaches:
        name = (ap.get("name") or "").strip()
        if name == recommended_name:
            continue
        summary = (ap.get("description") or "").strip() or "(no description)"
        result.append(handoff_schema.Alternative(
            id=_to_snake_case(name) if name else "unnamed",
            summary=summary,
            rejected_reason="not recommended; see /plan if needed",
        ))
    return result


def _find_unstable_production_site(vps_rows):
    # type: (List[handoff_schema.ValueProductionSite]) -> Optional[str]
    """Return the file_line of the first unstable production site, or None."""
    for vps in vps_rows:
        if not vps.is_stable:
            return vps.file_line
    return None


def _asdict_handoff(handoff):
    # type: (handoff_schema.Handoff) -> dict
    """Convert Handoff dataclass to dict for JSON serialization.

    Drops internal flag fields (e.g., _proposed_call_shape_parse_failed)
    before serialization. Uses dataclasses.asdict for recursive conversion.
    """
    raw = dataclasses.asdict(handoff)
    # Drop internal flag fields from plan_seeds.
    plan_seeds = raw.get("plan_seeds")
    if isinstance(plan_seeds, dict):
        plan_seeds.pop("_proposed_call_shape_parse_failed", None)
    return raw


# ---------------------------------------------------------------------------
# Step 4 — probe-tier classification utilities.
# ---------------------------------------------------------------------------

# Extension → file suffix for test_path construction.
_FRAMEWORK_EXTENSION_MAP = {
    "vitest": ".spec.ts",
    "jest": ".spec.ts",
    "mocha": ".spec.ts",
    "jasmine": ".spec.ts",
    "pytest": ".py",
    "nose2": ".py",
    "go-test": "_test.go",
    "cargo-test": ".rs",
    "rspec": "_spec.rb",
    "minitest": "_test.rb",
    "playwright": ".spec.ts",
    "cypress": ".spec.ts",
}

# Frameworks whose extension maps to .spec.ts (so they validate against handoff_schema enum).
# handoff_schema._VALID_TEST_FRAMEWORK = {vitest, jest, pytest, go-test, cargo-test, rspec}
# We must only pass these to the schema — others are not in the enum.
_SCHEMA_VALID_FRAMEWORKS = frozenset({"vitest", "jest", "pytest", "go-test", "cargo-test", "rspec"})


def _chrome_mcp_available():
    # type: () -> bool
    """Detect Chrome MCP availability via env var (test-mockable).

    Returns True when DEVFORGE_CHROME_MCP_AVAILABLE == "1", False otherwise.
    Conservative: env-var-driven for test-mockability.
    """
    return os.environ.get("DEVFORGE_CHROME_MCP_AVAILABLE", "") == "1"


def _read_test_infra_status(devforge_dir):
    # type: (Union[str, "os.PathLike[str]"]) -> Tuple[Optional[str], Optional[dict]]
    """Read .devforge/init.yaml and extract test_infra block.

    Returns (status, full_dict). On missing init.yaml / parse error → (None, None).
    """
    init_yaml = Path(devforge_dir) / "init.yaml"
    if not init_yaml.is_file():
        return (None, None)
    try:
        # Import lazily to avoid module-level circular dependency.
        if str(_HERE) not in sys.path:
            sys.path.insert(0, str(_HERE))
        import init_helper  # noqa: F401
        text = init_yaml.read_text(encoding="utf-8")
        state = init_helper.parse_yaml(text)
        ti = state.get("test_infra")
        if isinstance(ti, dict):
            return (ti.get("status"), ti)
    except (OSError, UnicodeDecodeError, init_helper.YamlParseError) as err:
        sys.stderr.write(
            "_read_test_infra_status: degraded read of {0}: {1}\n".format(init_yaml, err)
        )
    return (None, None)


def _pick_framework_from_test_infra(test_infra):
    # type: (Optional[dict]) -> Optional[str]
    """Pick a test framework from test_infra dict in priority order: frontend → backend → e2e.

    Returns the first non-None bucket value if it is in the schema-valid set,
    else None.
    """
    if not isinstance(test_infra, dict):
        return None
    for bucket in ("frontend", "backend", "e2e"):
        val = test_infra.get(bucket)
        if val and val in _SCHEMA_VALID_FRAMEWORKS:
            return val
    return None


def _classify_probe_tier(
    feasibility,        # type: dict
    test_infra_status,  # type: Optional[str]
    chrome_mcp,         # type: bool
    test_infra,         # type: Optional[dict]
    topic_slug,         # type: str
    research_date,      # type: str
):
    # type: (...) -> dict
    """Classify probe tier from feasibility flags + test_infra + chrome_mcp.

    Decision tree per RESEARCH-HANDOFF-PLAN.md Step 4:
    1. is_test_code=True → tier=3 (circular gate: tier-1 probe of test code is meaningless)
    2. data_shape_only=True AND NOT (auth_required OR network_dependent OR timing_dependent):
       - test_infra absent/None → tier=1.5
       - otherwise → tier=1
    3. auth_required=True OR network_dependent=True:
       - chrome_mcp → tier=2
       - else → tier=3
    4. fallback → tier=3

    Note: there is no override surface (finalize-handoff has no --probe-tier arg).
    Future override-handling would re-evaluate this function with user-supplied context.

    Returns a dict matching the Probe dataclass field subset:
    {tier, actor, test_framework, test_path, script_path, is_first_test_for_file,
     runner_up_confirms_if, both_disproved_if}
    """
    # Step 1: circular gate — test code cannot be tier-1 probed meaningfully.
    if feasibility.get("is_test_code") is True:
        tier = "3"
        actor = "user"
    elif (
        feasibility.get("data_shape_only") is True
        and not feasibility.get("auth_required")
        and not feasibility.get("network_dependent")
        and not feasibility.get("timing_dependent")
    ):
        # data_shape_only path — tier depends on test infra.
        if test_infra_status == "absent" or test_infra_status is None:
            tier = "1.5"
            actor = "llm"
        else:
            tier = "1"
            actor = "llm"
    elif feasibility.get("auth_required") is True or feasibility.get("network_dependent") is True:
        # Network/auth path — chrome MCP determines tier.
        if chrome_mcp:
            tier = "2"
            actor = "llm"
        else:
            tier = "3"
            actor = "user"
    else:
        # Fallback: no clear feasibility signal.
        tier = "3"
        actor = "user"

    # Populate test_framework / test_path / script_path / is_first_test_for_file.
    test_framework = None   # type: Optional[str]
    test_path = None        # type: Optional[str]
    script_path = None      # type: Optional[str]
    is_first_test_for_file = False

    if tier == "1":
        framework = _pick_framework_from_test_infra(test_infra)
        if framework is None:
            # test_infra says "present" but no recognized framework found —
            # demote to tier=1.5 (inconsistent state: status=present, all buckets empty/unknown).
            tier = "1.5"
            actor = "llm"
        else:
            ext = _FRAMEWORK_EXTENSION_MAP.get(framework, ".spec.ts")
            test_framework = framework
            test_path = "tests/research/{0}.probe{1}".format(topic_slug, ext)
            is_first_test_for_file = True  # Conservative: assume new test file.

    if tier == "1.5":
        script_path = "research/{0}-{1}/probe-script.mjs".format(research_date, topic_slug)
        test_framework = None
        is_first_test_for_file = False

    # Populate discriminator text for runner_up and both_disproved.
    if tier in ("1", "1.5"):
        runner_up_confirms_if = (
            "if test FAILS but with different assertion outcome "
            "→ runner-up applies; LLM evaluates output diff"
        )
        both_disproved_if = (
            "if test PASSES with current code "
            "→ both hypotheses are wrong; widen investigation"
        )
    else:
        runner_up_confirms_if = "tbd — manual observation required"
        both_disproved_if = "tbd"

    return {
        "tier": tier,
        "actor": actor,
        "test_framework": test_framework,
        "test_path": test_path,
        "script_path": script_path,
        "is_first_test_for_file": is_first_test_for_file,
        "runner_up_confirms_if": runner_up_confirms_if,
        "both_disproved_if": both_disproved_if,
    }


# ---------------------------------------------------------------------------
# set-probe-feasibility command.
# ---------------------------------------------------------------------------


def cmd_set_probe_feasibility(args):
    # type: (argparse.Namespace) -> int
    """Write probe_feasibility flags (5 booleans) to research-report.json.

    All five flags are required. Each accepts only lowercase "true" or "false" (argparse exact-match).
    """
    devforge_dir = args.devforge_dir
    flag_names = [
        ("data_shape_only", args.data_shape_only),
        ("auth_required", args.auth_required),
        ("network_dependent", args.network_dependent),
        ("timing_dependent", args.timing_dependent),
        ("is_test_code", args.is_test_code),
    ]
    parsed = {}
    for field_name, raw in flag_names:
        try:
            canonical = _validate_enum(raw, "set-probe-feasibility --{0}".format(
                field_name.replace("_", "-")
            ), ("true", "false"))
        except ValueError as err:
            return _die(str(err), code=2)
        parsed[field_name] = (canonical == "true")

    with _state_transaction(devforge_dir, "report") as report:
        feasibility = report.get("probe_feasibility")
        if not isinstance(feasibility, dict):
            feasibility = {
                "data_shape_only": None,
                "auth_required": None,
                "network_dependent": None,
                "timing_dependent": None,
                "is_test_code": None,
            }
        for field_name, value in parsed.items():
            feasibility[field_name] = value
        report["probe_feasibility"] = feasibility

    sys.stdout.write("probe_feasibility written: {0}\n".format(parsed))
    return 0


def _build_handoff_from_state(memo, report, research_md_path, devforge_dir=None):
    # type: (dict, dict, Optional[str], Optional[str]) -> handoff_schema.Handoff
    """Orchestrate memo + report → Handoff dataclass construction.

    Raises ValueError from schema validators if any field fails validation.

    Mode translation: research_helper uses "bug" / "enhancement"; handoff
    schema uses {bug, feature_addition, migration, refactor, greenfield}.
    "enhancement" maps to "feature_addition" as the closest schema equivalent.
    """
    memo_mode = memo["mode"]
    # Translate memo mode to handoff schema mode.
    handoff_mode = _MEMO_MODE_TO_HANDOFF_MODE.get(memo_mode, memo_mode)
    topic_slug = memo["topic_slug"]
    date = report["date"]

    # research_path
    if research_md_path:
        research_path = research_md_path
    else:
        research_path = "research/{0}-{1}.md".format(date, topic_slug)

    # intent block
    dims = memo.get("dimensions") or {}
    symptom_snap = report.get("symptom_snapshot") or {}

    symptom_text = (
        (dims.get("symptom") or {}).get("text")
        or (dims.get("symptom") or {}).get("value")
        or symptom_snap.get("symptom")
        or ""
    ).strip()
    desired_text = (
        (dims.get("desired_behavior") or {}).get("text")
        or (dims.get("desired") or {}).get("value")
        or symptom_snap.get("desired")
        or ""
    ).strip()
    scope_text = (
        (dims.get("scope") or {}).get("text")
        or (dims.get("scope") or {}).get("value")
        or symptom_snap.get("scope")
        or ""
    ).strip()

    intent = handoff_schema.Intent(
        symptom_summary=symptom_text or "(not set)",
        desired_summary=desired_text or "(not set)",
        scope=_derive_scope(scope_text),
    )

    # spec_seeds block
    # Use memo_mode for hint lookup (has "enhancement"); handoff_mode for schema.
    spec_type_hint = _SPEC_TYPE_HINT_MAP.get(memo_mode, _SPEC_TYPE_HINT_MAP.get(handoff_mode, "bug_fix"))
    constraints = _build_constraints(report.get("constitution_constraints") or [])
    value_production_sites_schema = _build_value_production_sites(
        report.get("value_production_sites") or []
    )
    affected_areas = _build_affected_areas(
        report.get("fix_path_helpers") or [],
        report.get("value_production_sites") or [],
    )
    risks = _build_risks(report.get("complexity"))
    open_questions = _build_open_questions(report.get("open_uncertainties") or [])
    data_flow_chain_schema = _build_data_flow_chain(report.get("data_flow_chain"))
    value_semantics_schema = _build_value_semantics(report.get("value_semantics") or [])
    literal_archaeology_schema = _build_literal_archaeology(
        report.get("literal_archaeology") or []
    )

    spec_seeds = handoff_schema.SpecSeeds(
        spec_type_hint=spec_type_hint,
        constraints=constraints,
        affected_areas=affected_areas,
        risks=risks,
        open_questions=open_questions,
        data_flow_chain=data_flow_chain_schema,
        value_semantics=value_semantics_schema,
        value_production_sites=value_production_sites_schema,
        literal_archaeology=literal_archaeology_schema,
    )

    # plan_seeds block
    rec = report["recommended_approach"]  # caller already validated non-None
    rec_name = (rec.get("name") or "").strip()
    rec_rationale = (rec.get("rationale") or "").strip()
    if not rec_name or not rec_rationale:
        raise ValueError(
            "recommended_approach record is missing 'name' or 'rationale' "
            "(rerun set-recommended-approach with complete args)"
        )
    complexity_raw = report["complexity"]  # caller already validated non-None
    complexity_schema = handoff_schema.Complexity(
        changes=complexity_raw.get("codebase_changes") or "Low",
        risk=complexity_raw.get("risk") or "Low",
        verify_cost=complexity_raw.get("verify_cost") or "Low",
    )

    cites = rec.get("cites") or []
    cited_patterns = _build_cited_patterns(cites, report)
    layer_dest = "tbd"
    if cites:
        first_cite = cites[0]
        path_part = first_cite.rsplit(":", 1)[0] if ":" in first_cite else first_cite
        pkg = _extract_package(path_part)
        if pkg:
            layer_dest = pkg

    plan_seeds = handoff_schema.PlanSeeds(
        recommended_approach_id=_to_snake_case(rec_name),
        recommended_approach_summary=rec_rationale,
        layer_destination=layer_dest,
        layer_justification=rec.get("single_layer_justification") or "multi-layer",
        complexity=complexity_schema,
        cited_canonical_patterns=cited_patterns,
        alternatives_considered=_build_alternatives(
            report.get("approaches") or [], rec_name
        ),
        proposed_call_shape=rec.get("proposed_call_shape"),
    )

    # probe block — Step 4 smart classifier (replaces Step 3 tier=3 stub).
    unstable_site = _find_unstable_production_site(value_production_sites_schema)
    verify_step = report.get("verify_step") or {}
    # discriminator is the PASS/FAIL criterion (what result confirms primary).
    # probe is the ACTION (what to do). primary_confirms_if matches discriminator semantics.
    primary_confirms_if = (verify_step.get("discriminator") or "").strip()
    if not primary_confirms_if:
        primary_confirms_if = "tbd — populated by Step 4 probe-tier classifier"

    # Run feasibility classifier.
    feasibility_raw = report.get("probe_feasibility") or {}
    # Read test_infra from .devforge/init.yaml (init_helper.parse_yaml).
    # devforge_dir is passed in by cmd_finalize_handoff; falls back to cwd-relative
    # ".devforge" when called directly (e.g., from tests that set up state inline).
    _classifier_devforge_dir = devforge_dir if devforge_dir else ".devforge"
    test_infra_status, test_infra = _read_test_infra_status(_classifier_devforge_dir)

    classified = _classify_probe_tier(
        feasibility=feasibility_raw,
        test_infra_status=test_infra_status,
        chrome_mcp=_chrome_mcp_available(),
        test_infra=test_infra,
        topic_slug=topic_slug,
        research_date=date,
    )

    # Step 5 — override script_path when tier=1.5 and probe_scripts recorded.
    # record-probe-script is the source-of-truth for the actual script path;
    # the deterministic default from _classify_probe_tier is only a fallback.
    effective_script_path = classified["script_path"]
    if classified["tier"] == "1.5":
        probe_scripts = report.get("probe_scripts") or []
        if probe_scripts:
            effective_script_path = probe_scripts[-1]["script_path"]

    discriminator = handoff_schema.Discriminator(
        primary_confirms_if=primary_confirms_if,
        runner_up_confirms_if=classified["runner_up_confirms_if"],
        both_disproved_if=classified["both_disproved_if"],
        production_site_check=unstable_site,
    )
    feasibility_check = handoff_schema.FeasibilityCheck(
        data_shape_only=bool(feasibility_raw.get("data_shape_only")),
        auth_required=bool(feasibility_raw.get("auth_required")),
        network_dependent=bool(feasibility_raw.get("network_dependent")),
        timing_dependent=bool(feasibility_raw.get("timing_dependent")),
        is_test_code=bool(feasibility_raw.get("is_test_code")),
    )
    probe = handoff_schema.Probe(
        tier=classified["tier"],
        actor=classified["actor"],
        discriminator=discriminator,
        feasibility_check=feasibility_check,
        test_framework=classified["test_framework"],
        test_path=classified["test_path"],
        script_path=effective_script_path,
        is_first_test_for_file=classified["is_first_test_for_file"],
    )

    # downstream_links
    downstream_links = handoff_schema.DownstreamLinks(
        spec_path=None,
        plan_path=None,
        execute_task_commit_shas=[],
    )

    return handoff_schema.Handoff(
        schema_version=handoff_schema.SCHEMA_VERSION,
        research_path=research_path,
        research_completed_at=datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(timespec="seconds"),
        mode=handoff_mode,
        intent=intent,
        spec_seeds=spec_seeds,
        plan_seeds=plan_seeds,
        probe=probe,
        downstream_links=downstream_links,
        outcome=None,
    )


# ---------------------------------------------------------------------------
# finalize-handoff command.
# ---------------------------------------------------------------------------


def cmd_finalize_handoff(args):
    # type: (argparse.Namespace) -> int
    """Read research state → build Handoff → validate → write handoff.json."""
    try:
        memo = _load_memo(args.devforge_dir)
        report = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("finalize-handoff: cannot load state: {0}".format(err))

    # Required-field guard.
    if not memo.get("mode"):
        return _die(
            "finalize-handoff: memo.mode not set (run detect-mode first)", code=2
        )
    if not memo.get("topic_slug"):
        return _die(
            "finalize-handoff: memo.topic_slug not set (run set-topic first)", code=2
        )
    if not report.get("date"):
        return _die(
            "finalize-handoff: report.date not set (run set-date first)", code=2
        )
    if report.get("recommended_approach") is None:
        return _die(
            "finalize-handoff: recommended_approach not set "
            "(run set-recommended-approach first)",
            code=2,
        )
    if report.get("complexity") is None:
        return _die(
            "finalize-handoff: complexity not set (run set-complexity first)", code=2
        )

    # Step 4: probe_feasibility completeness guard (all 5 booleans must be set
    # before the classifier runs — None means LLM skipped set-probe-feasibility).
    feasibility = report.get("probe_feasibility") or {}
    required_feas = ["data_shape_only", "auth_required", "network_dependent",
                     "timing_dependent", "is_test_code"]
    missing_feas = [k for k in required_feas if feasibility.get(k) is None]
    if missing_feas:
        return _die(
            "finalize-handoff: probe_feasibility incomplete; missing flags: {0}. "
            "Run `research_helper set-probe-feasibility --data-shape-only ... "
            "--auth-required ... --network-dependent ... --timing-dependent ... "
            "--is-test-code ...` before finalize.".format(missing_feas),
            code=2,
        )

    try:
        handoff = _build_handoff_from_state(
            memo, report, args.research_md_path, devforge_dir=args.devforge_dir
        )
    except ValueError as err:
        return _die(
            "finalize-handoff: schema validation failed: {0}".format(err), code=2
        )

    target = Path(args.emit_handoff_json).resolve()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(_asdict_handoff(handoff), target)
    except OSError as err:
        return _die(
            "finalize-handoff: cannot write {0}: {1}".format(target, err)
        )

    sys.stdout.write("wrote: {0}\n".format(target))
    return 0


# ---------------------------------------------------------------------------
# Step 7 — append-outcome + check-outcome.
# ---------------------------------------------------------------------------


def _load_handoff_json(handoff_path):
    # type: (str) -> Tuple[Optional[dict], Optional[str]]
    """Load and JSON-parse handoff.json at handoff_path.

    Returns (data_dict, None) on success, (None, error_message) on failure.
    """
    p = Path(handoff_path)
    if not p.is_file():
        return None, "handoff.json not found: {0}".format(handoff_path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        return None, "cannot read handoff.json: {0}".format(err)
    if not isinstance(data, dict):
        return None, "handoff.json must be a JSON object"
    return data, None


def _build_outcome_md_section(outcome):
    # type: (dict) -> str
    """Render a markdown '## Outcome' section from an outcome dict.

    Used by append-outcome to append to the parallel .md file.
    """
    lines = [
        "## Outcome",
        "",
        "- **hypothesis_confirmed**: {0}".format(outcome["hypothesis_confirmed"]),
        "- **evidence_source**: {0}".format(outcome["evidence_source"]),
        "- **evidence_cite**: {0}".format(outcome["evidence_cite"]),
        "- **actual_fix_path**: {0}".format(outcome["actual_fix_path"]),
        "- **confidence_grade**: {0}".format(outcome["confidence_grade"]),
        "- **confirmed_date**: {0}".format(outcome["confirmed_date"]),
    ]
    if outcome.get("delta_from_recommendation"):
        lines.append("- **delta_from_recommendation**: {0}".format(
            outcome["delta_from_recommendation"]
        ))
    if outcome.get("confirmed_commit_sha"):
        lines.append("- **confirmed_commit_sha**: {0}".format(
            outcome["confirmed_commit_sha"]
        ))
    lines.append("")
    return "\n".join(lines)


def cmd_append_outcome(args):
    # type: (argparse.Namespace) -> int
    """Record post-probe outcome into handoff.json and optionally its parallel .md.

    Idempotency: re-running OVERWRITES the existing outcome block in handoff.json
    (last-write-wins). The parallel .md file gets a NEW '## Outcome' section appended
    each time (append-only audit trail — no de-dup).

    Steps:
    1. Read and validate handoff.json schema (must be parseable dict with 'probe' block).
    2. Compute confidence_grade via handoff_schema.compute_confidence_grade().
    3. Build outcome dict; validate via handoff_schema.Outcome(**...) for enum/format errors.
    4. Mutate handoff.json: set handoff["outcome"] = outcome dict. Atomic write.
    5. If research_path is set and the parallel .md exists, append '## Outcome' section.
    6. Print confirmation with confidence_grade. Exit 0.
    """
    handoff_path_str = args.handoff_path
    data, err = _load_handoff_json(handoff_path_str)
    if err is not None:
        return _die("append-outcome: handoff.json schema validation failed: {0}".format(err), code=2)

    # Validate minimum structure: must have 'probe' with 'tier' and 'discriminator'.
    probe = data.get("probe")
    if not isinstance(probe, dict):
        return _die(
            "append-outcome: handoff.json schema validation failed: "
            "missing or non-dict 'probe' block",
            code=2,
        )
    tier = probe.get("tier")
    if not isinstance(tier, str):
        return _die(
            "append-outcome: handoff.json schema validation failed: "
            "probe.tier must be a string",
            code=2,
        )
    discriminator = probe.get("discriminator")
    if not isinstance(discriminator, dict):
        return _die(
            "append-outcome: handoff.json schema validation failed: "
            "probe.discriminator must be a dict",
            code=2,
        )

    # Compute has_production_site_check from probe.discriminator.production_site_check.
    has_production_site_check = discriminator.get("production_site_check") is not None

    # Compute confidence_grade via the schema function.
    confidence_grade = handoff_schema.compute_confidence_grade(
        tier=tier,
        evidence_source=args.evidence_source,
        hypothesis_confirmed=args.hypothesis_confirmed,
        has_production_site_check=has_production_site_check,
    )

    # Build outcome dict.
    confirmed_date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    outcome_dict = {
        "hypothesis_confirmed": args.hypothesis_confirmed,
        "evidence_source": args.evidence_source,
        "evidence_cite": args.evidence_cite,
        "actual_fix_path": args.actual_fix_path,
        "delta_from_recommendation": args.delta_from_recommendation,
        "confirmed_date": confirmed_date,
        "confirmed_commit_sha": args.confirmed_commit_sha,
        "confidence_grade": confidence_grade,
    }

    # Validate outcome via schema dataclass (catches enum / format errors).
    try:
        handoff_schema.Outcome(**outcome_dict)
    except (TypeError, ValueError) as err:
        return _die(
            "append-outcome: handoff.json schema validation failed: {0}".format(err), code=2
        )

    # Mutate and atomically write handoff.json.
    data["outcome"] = outcome_dict
    target = Path(handoff_path_str).resolve()
    try:
        _atomic_write_json(data, target)
    except OSError as err:
        return _die("append-outcome: cannot write {0}: {1}".format(target, err))

    # Optionally append '## Outcome' section to the parallel .md file.
    research_path = data.get("research_path")
    if research_path and isinstance(research_path, str):
        md_path = (Path(handoff_path_str).parent / research_path).resolve()
        if md_path.is_file():
            md_section = _build_outcome_md_section(outcome_dict)
            try:
                with open(str(md_path), "a", encoding="utf-8") as f:
                    f.write("\n")
                    f.write(md_section)
            except OSError:
                # Non-fatal: handoff.json is source of truth.
                pass

    sys.stdout.write(
        "appended outcome to {0} (confidence_grade={1})\n".format(
            handoff_path_str, confidence_grade
        )
    )
    return 0


def cmd_check_outcome(args):
    # type: (argparse.Namespace) -> int
    """Print 'unmarked' or 'marked: <details>' for the outcome block in handoff.json.

    Non-blocking: always exits 0 unless the file is missing (exit 2).

    Steps:
    1. Read handoff.json. Missing → exit 2.
    2. If outcome is None/absent → stdout "unmarked", exit 0.
    3. If outcome is present → stdout "marked: <hypothesis_confirmed> (confidence=<grade>,
       evidence=<source>)", exit 0.
    """
    data, err = _load_handoff_json(args.handoff_path)
    if err is not None:
        return _die("check-outcome: {0}".format(err), code=2)

    outcome = data.get("outcome")
    if outcome is None:
        sys.stdout.write("unmarked\n")
        return 0

    hypothesis = outcome.get("hypothesis_confirmed", "unknown")
    grade = outcome.get("confidence_grade", "unknown")
    evidence = outcome.get("evidence_source", "unknown")
    sys.stdout.write(
        "marked: {0} (confidence={1}, evidence={2})\n".format(hypothesis, grade, evidence)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
