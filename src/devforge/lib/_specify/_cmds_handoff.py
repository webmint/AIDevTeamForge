"""Handoff subcommands: import-handoff + find-handoffs + finalize-handoff.

Pre-phase (Phase 0.4) helpers that bridge research_helper finalize-handoff
and discover_helper finalize-handoff output into specify-state.json
pre-seeded fields.

finalize-handoff (Phase 0.5 — specify -> plan producer):
  Reads specify-state.json, builds the specify Handoff dataclass,
  validates it, and writes handoff.json to specs/{N}-{slug}/ (or
  --emit-handoff-json override).  State is read-only; no mutation.

import-handoff:
  Reads a handoff.json produced by research_helper or discover_helper
  finalize-handoff, validates it via handoff_schema (schema dataclasses),
  and pre-seeds specify state with spec_type, constraints, affected_areas,
  risks, open_questions, design_anchor (plan 53 Phase 2 -- carried verbatim
  from spec_seeds.design_anchor; an empty anchor in the handoff yields an
  empty anchor in state, never an absent key).  Dispatch is on handoff_kind field:
    "discover"           -> discover branch (source has handoff_kind + discover_completed_at).
    absent / "research"  -> research branch (existing behaviour).
  Unknown explicit handoff_kind -> exit 2.
  68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4 (python-reviewer finding 1):
  also seeds state["spec_number"] / state["feature_slug"] by parsing the
  handoff's own containing dir name (e.g. "003-foo-bar") against
  SPEC_NUMBER_DIR_RE -- so a later Phase's spec.md write lands in the SAME
  dir the intake handoff already lives in, instead of a fresh NNN scan
  allocating a different one.  A non-matching dir name (pre-migration
  handoff imported from an arbitrary path) leaves both fields unseeded, no
  error -- the D5 fallback guard (assign-spec-number / the new
  set-spec-number verb) covers that case.

find-handoffs (68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4):
  One glob pass over specs/*/research-handoff.json AND
  specs/*/discover-handoff.json under the repo root (parent of .devforge
  dir), filtered to feature dirs that do NOT yet contain spec.md (D5's
  structural "pending intake" predicate).  mtime is used only to ORDER
  hits, most-recent first -- --since is accepted-but-ignored, kept only so
  pre-Phase-4 callers do not break (see cmd_find_handoffs).  Emit one line
  per hit; skip corrupt or schema-invalid files silently.  Exit 0 on zero
  hits (unless --require is passed; see cmd_find_handoffs for gate
  behavior).

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _datetime_module
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._schema import SPEC_NUMBER_DIR_RE
from ._state import _atomic_write_json, _load_state, _state_path, _state_transaction
from ._validators import _die

# ---------------------------------------------------------------------------
# handoff_schema imports — both research and discover schemas.
# Use package-qualified imports to avoid polluting sys.modules['handoff_schema']
# with either schema (which would break test_discover_handoff_schema when run
# in combined pytest invocations).
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent.parent  # src/devforge/lib/
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from _research import handoff_schema as research_handoff_schema  # noqa: E402  type: ignore[import]
from _discover import handoff_schema as discover_handoff_schema  # noqa: E402  type: ignore[import]
from . import handoff_schema as specify_handoff_schema  # noqa: E402

# Legacy alias used by the existing function signatures that reference
# handoff_schema.Handoff, handoff_schema.Constraint, etc.
handoff_schema = research_handoff_schema  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------

_SINCE_RE = re.compile(r'^(\d+)\s+(days?|hours?|minutes?)$', re.IGNORECASE)

# Map from since-unit (canonicalized) to seconds.
_UNIT_SECONDS: Dict[str, int] = {
    "day": 86400,
    "hour": 3600,
    "minute": 60,
}

def _parse_since_seconds(since: str) -> Optional[int]:
    """Parse --since string to a duration in seconds.

    Accepts: "<N> day(s)", "<N> hour(s)", "<N> minute(s)".
    Returns None if the format does not match.
    """
    m = _SINCE_RE.match(since.strip())
    if not m:
        return None
    n = int(m.group(1))
    unit_raw = m.group(2).lower().rstrip('s')  # normalize "days" → "day"
    seconds = _UNIT_SECONDS.get(unit_raw)
    if seconds is None:
        return None
    return n * seconds


def _dict_to_dataclass(cls: Any, d: Any) -> Any:
    """Recursively construct a dataclass instance from a plain dict.

    Does NOT require cls to have a from_dict method; uses dataclasses.fields
    to discover field names and recursively constructs nested dataclasses.

    Limitation: only handles dict → dataclass, list of dicts → list of
    dataclasses (using type annotations on fields). Scalars pass through.
    Raises TypeError on missing required fields; ValueError on schema errors
    raised by __post_init__.
    """
    import dataclasses
    import typing

    if not dataclasses.is_dataclass(cls):
        # Scalar or non-dataclass type — return as-is.
        return d

    if d is None:
        return None

    if not isinstance(d, dict):
        raise TypeError(
            "Expected a dict to construct {0}, got {1}".format(
                cls.__name__, type(d).__name__
            )
        )

    field_map: Dict[str, Any] = {}
    for f in dataclasses.fields(cls):
        if not f.init:
            continue
        if f.name not in d:
            if (f.default is dataclasses.MISSING
                    and f.default_factory is dataclasses.MISSING):  # type: ignore[misc]
                raise TypeError(
                    "Missing required field {0!r} in {1}".format(
                        f.name, cls.__name__
                    )
                )
            # Has default — skip (let dataclass use it).
            continue

        raw = d[f.name]
        # Resolve type hint to the actual class if possible.
        type_hint = f.type

        # Unwrap Optional[X] → X.
        origin = getattr(type_hint, '__origin__', None)
        args = getattr(type_hint, '__args__', ())

        # typing.Optional[X] is Union[X, None].
        if origin is typing.Union and len(args) == 2 and type(None) in args:
            inner = args[0] if args[1] is type(None) else args[1]
            if raw is None:
                field_map[f.name] = None
                continue
            # Recurse with inner type.
            field_map[f.name] = _dict_to_dataclass(inner, raw)
            continue

        # typing.List[X].
        if origin is list and args:
            elem_cls = args[0]
            if dataclasses.is_dataclass(elem_cls):
                field_map[f.name] = [
                    _dict_to_dataclass(elem_cls, item) for item in raw
                ]
            else:
                field_map[f.name] = raw
            continue

        # Plain dataclass field.
        if dataclasses.is_dataclass(type_hint):
            field_map[f.name] = _dict_to_dataclass(type_hint, raw)
            continue

        # Scalar.
        field_map[f.name] = raw

    return cls(**field_map)



def _root_relative(path: Path, repo_root: Path) -> str:
    """Root-relative posix-style path string when `path` is under `repo_root`.

    68-INTAKE-OWNS-FEATURE-DIR-PLAN.md D9(d): source.handoff_path (specify
    state) and downstream_links.spec_path (written back into the upstream
    handoff.json) become install-root-relative strings, matching the
    already-root-relative research_path / report_path fields the intake
    lanes write -- so /plan's render-plan-seeds provenance follow (Phase 5)
    can resolve them against the install root (cwd) instead of dying on a
    stale absolute path from a different machine/checkout.

    Falls back to the absolute path string when `path` is NOT under
    `repo_root` -- "shouldn't happen in new layout" (every intake artifact
    lives under repo_root/specs/), but a caller passing an explicit
    --emit-handoff-json outside specs/ (or a pre-migration on-disk file
    D3 never deletes) can still hit this; storing the absolute path is the
    documented, honest fallback rather than raising.
    """
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return str(path)


def _normalize_ws(s: str) -> str:
    """Collapse internal whitespace runs and strip ends.

    Used for dedupe identity-key comparison only.  Does NOT casefold — constraint
    and question text may carry case-sensitive identifiers (GET vs get, etc.).
    """
    return " ".join(s.split())


def _dedupe_seeds(
    items: List[Any],
    key_fn: Any,  # Callable[[Any], Any] — avoided to stay 3.8-compat without TYPE_CHECKING
    section: str,
) -> List[Any]:
    """Insertion-ordered first-occurrence-wins dedupe over a seed list.

    items    — list of dataclass instances (Constraint / AffectedArea / Risk /
               OpenQuestion from either the research or discover schema).
    key_fn   — callable(item) -> hashable normalized identity key.  Used for
               comparison ONLY; the original (un-normalized) field values from
               the dataclass object are logged to stderr.
    section  — human-readable section name for stderr drop lines, e.g. "constraints".

    Semantics:
    - First occurrence wins; later duplicates are dropped with a stderr log line.
    - Relative order of survivors is preserved (insertion-ordered dict).
    - The surviving object is returned verbatim (no field mutation).
    - Each dropped entry produces exactly one stderr line showing the RAW
      (pre-normalize) field values of both the dropped item AND the surviving
      first occurrence, so an operator can confirm the collapse was correct:
        import-handoff: dedupe <section> — dropped <dropped_item>
          → collapsed into surviving <surviving_item>

    Returns the deduped list (may be shorter than input).
    """
    seen: Dict[Any, Any] = {}  # normalized key -> original (first-occurrence) item
    result: List[Any] = []
    for item in items:
        key = key_fn(item)
        if key in seen:
            sys.stderr.write(
                "import-handoff: dedupe {section} — dropped {dropped}"
                " → collapsed into surviving {surviving}\n".format(
                    section=section,
                    dropped=repr(item),
                    surviving=repr(seen[key]),
                )
            )
        else:
            seen[key] = item
            result.append(item)
    return result


def _constraint_key(c: Any) -> Any:
    """Identity key for a Constraint: compound (kind, normalized content).

    kind stays literal — two same-content constraints of different kind are
    NOT duplicates.
    """
    return (c.kind, _normalize_ws(c.content))


def _affected_area_key(a: Any) -> Any:
    """Identity key for an AffectedArea: normalized area name."""
    return _normalize_ws(a.area)


def _risk_key(r: Any) -> Any:
    """Identity key for a Risk: normalized risk text."""
    return _normalize_ws(r.risk)


def _open_question_key(q: Any) -> Any:
    """Identity key for an OpenQuestion: normalized question text."""
    return _normalize_ws(q.question)


def _constraint_to_dict(c: handoff_schema.Constraint) -> Dict[str, Any]:
    """Serialize a handoff_schema.Constraint to the specify-state dict shape."""
    record: Dict[str, Any] = {"kind": c.kind, "content": c.content}
    if c.quantifier is not None:
        record["quantifier"] = c.quantifier
    if c.constitution_ref is not None:
        record["constitution_ref"] = c.constitution_ref
    if c.protocol is not None:
        record["protocol"] = c.protocol
    if c.contract_doc_ref is not None:
        record["contract_doc_ref"] = c.contract_doc_ref
    return record


def _affected_area_to_dict(a: handoff_schema.AffectedArea) -> Dict[str, Any]:
    """Serialize a research handoff_schema.AffectedArea to the specify-state dict shape."""
    return {"area": a.area, "files": list(a.files), "impact": a.impact}


def _discover_affected_area_to_dict(
    a: discover_handoff_schema.AffectedArea,
) -> Dict[str, Any]:
    """Serialize a discover handoff_schema.AffectedArea to the specify-state dict shape.

    Preserves is_internal_extension_candidate (discover-only field).
    """
    return {
        "area": a.area,
        "files": list(a.files),
        "impact": a.impact,
        "is_internal_extension_candidate": a.is_internal_extension_candidate,
    }


def _risk_to_dict(r: handoff_schema.Risk) -> Dict[str, Any]:
    """Serialize a handoff_schema.Risk to the specify-state dict shape."""
    return {
        "risk": r.risk,
        "likelihood": r.likelihood,
        "impact": r.impact,
        "mitigation": r.mitigation,
    }


def _open_question_to_dict(q: handoff_schema.OpenQuestion, idx: int) -> Dict[str, Any]:
    """Serialize a handoff_schema.OpenQuestion to the specify-state dict shape.

    Output shape matches cmd_record_open_question:
      {question_id, content, category_no_dp_reason}
    Blocking questions get a '[blocking]' suffix appended to content.
    """
    body = q.question.strip()
    if q.blocking:
        body = body + "  [blocking]"
    return {
        "question_id": "hq-{0}".format(idx + 1),
        "content": body,
        "category_no_dp_reason": "",
    }


# ---------------------------------------------------------------------------
# cmd_import_handoff.
# ---------------------------------------------------------------------------


def cmd_import_handoff(args: argparse.Namespace) -> int:
    """Pre-seed specify state from a handoff.json (research or discover — dispatch on handoff_kind field).

    Steps:
    0. Detect kind via handoff_kind field; dispatch to _import_handoff_research or _import_handoff_discover.
    1. Resolve + validate handoff-path.
    2. Read JSON and validate via handoff_schema dataclasses.
    3. Pre-seed state via _state_transaction.
    4. Idempotency: warn if user-composed content would be preserved.
    5. Mutate handoff.json downstream_links.spec_path.
    6. Atomic write handoff.json.
    7. Emit success line to stdout.
    """
    handoff_arg = getattr(args, "handoff_path", None)
    if not handoff_arg:
        sys.stderr.write("import-handoff: --handoff-path is required\n")
        return 2

    handoff_path = Path(handoff_arg)
    if not handoff_path.is_absolute():
        handoff_path = Path.cwd() / handoff_path
    handoff_path = handoff_path.resolve()

    if not handoff_path.exists():
        sys.stderr.write(
            "import-handoff: handoff-path not found: {0}\n".format(handoff_path)
        )
        return 2

    # Load and validate.
    try:
        raw_text = handoff_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write("import-handoff: cannot read file: {0}\n".format(err))
        return 2

    try:
        raw_data: Dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as err:
        sys.stderr.write(
            "import-handoff: invalid JSON in {0}: {1}\n".format(handoff_path, err)
        )
        return 2

    # Detect kind and dispatch.
    kind = raw_data.get("handoff_kind", "research")
    if kind not in ("research", "discover"):
        sys.stderr.write(
            "import-handoff: unknown handoff_kind={0!r};"
            " expected 'research' or 'discover'\n".format(kind)
        )
        return 2

    if kind == "discover":
        return _import_handoff_discover(args, handoff_path, raw_data)
    else:
        return _import_handoff_research(args, handoff_path, raw_data)


def _import_handoff_research(
    args: argparse.Namespace,
    handoff_path: Path,
    raw_data: Dict[str, Any],
) -> int:
    """Import a research handoff.json into specify state."""
    try:
        handoff = _dict_to_dataclass(handoff_schema.Handoff, raw_data)
    except (ValueError, TypeError) as err:
        sys.stderr.write(
            "import-handoff: schema validation failed: {0}\n".format(err)
        )
        return 2

    # Extract spec seeds — dedupe at source before converting to dicts.
    seeds = handoff.spec_seeds
    constraints_src = _dedupe_seeds(seeds.constraints, _constraint_key, "constraints")
    affected_areas_src = _dedupe_seeds(seeds.affected_areas, _affected_area_key, "affected_areas")
    risks_src = _dedupe_seeds(seeds.risks, _risk_key, "risks")
    open_questions_src = _dedupe_seeds(seeds.open_questions, _open_question_key, "open_questions")
    constraints = [_constraint_to_dict(c) for c in constraints_src]
    affected_areas = [_affected_area_to_dict(a) for a in affected_areas_src]
    risks = [_risk_to_dict(r) for r in risks_src]
    open_questions = [_open_question_to_dict(q, i) for i, q in enumerate(open_questions_src)]
    spec_type = seeds.spec_type_hint
    research_completed_at = handoff.research_completed_at

    # Plan 53 Phase 2 — carry the captured design_anchor across the ONE hop.
    # Deterministic: an empty anchor in the handoff (intake skipped capture)
    # yields an empty anchor in state, never an absent key (default_state()
    # already carries the same empty shape for a handoff-less manual run).
    design_anchor = {
        "kind": seeds.design_anchor.kind,
        "file": seeds.design_anchor.file,
        "selectors": list(seeds.design_anchor.selectors),
    }

    # 68-INTAKE-OWNS-FEATURE-DIR-PLAN.md D5: the feature dir was already
    # allocated by /research at intake finalize (D1) -- the handoff already
    # sits inside it. future_spec_path is simply that dir's spec.md; no NEW
    # NNN is computed here (next_spec_number is not called in this path).
    devforge_dir = Path(args.devforge_dir).resolve()
    repo_root = devforge_dir.parent
    handoff_path_rel = _root_relative(handoff_path, repo_root)
    future_spec_path = _root_relative(handoff_path.parent / "spec.md", repo_root)

    # python-reviewer finding 1 (68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4):
    # seed spec_number + feature_slug from the RESOLVED intake dir's own
    # name -- without this, main.md's unconditional assign-spec-number
    # fresh-scan on a later Phase would allocate a NEW NNN and send spec.md
    # to a *different* directory than the one the handoff (and this
    # future_spec_path) already lives in. A non-matching parent dir name
    # (e.g. a pre-migration handoff imported manually from an arbitrary
    # path) leaves both fields unseeded -- no error; the D5 fallback guard
    # (assign-spec-number / set-spec-number) covers that case downstream.
    dir_match = SPEC_NUMBER_DIR_RE.match(handoff_path.parent.name)

    # Pre-seed state; check for re-import.
    warn_user_content = False
    try:
        with _state_transaction(args.devforge_dir) as state:
            # Idempotency: check if source.handoff_path already set.
            source = state.get("source", {})
            existing_handoff = source.get("handoff_path") if source else None

            # Check user-composed content for warning.
            if existing_handoff is not None:
                if (state.get("overview")
                        or state.get("desired_behavior")
                        or state.get("acceptance_criteria")):
                    warn_user_content = True

            # Ensure "source" key exists (may be missing in old state).
            if "source" not in state:
                state["source"] = {
                    "handoff_path": None,
                    "handoff_kind": None,
                    "research_completed_at": None,
                    "discover_completed_at": None,
                    "discover_recommended_summary": None,
                }

            # Pre-seed fields (overwrite pre-seeded blocks; user content preserved).
            state["spec_type"] = spec_type
            state["spec_type_seeded_by_upstream"] = True
            state["constraints"] = constraints
            state["affected_areas"] = affected_areas
            state["risks"] = risks
            state["open_questions"] = open_questions
            state["design_anchor"] = design_anchor
            state["source"]["handoff_path"] = handoff_path_rel
            state["source"]["handoff_kind"] = "research"
            state["source"]["research_completed_at"] = research_completed_at
            if dir_match:
                state["spec_number"] = dir_match.group(1)
                state["feature_slug"] = dir_match.group(2)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write("import-handoff: state error: {0}\n".format(err))
        return 2

    if warn_user_content:
        sys.stderr.write(
            "import-handoff: warning: state has user-composed content"
            " (overview / desired_behavior / acceptance_criteria);"
            " pre-seeded blocks overwritten but user content preserved\n"
        )

    # Mutate handoff.json downstream_links.spec_path and write atomically.
    raw_data.setdefault("downstream_links", {})
    raw_data["downstream_links"]["spec_path"] = future_spec_path
    try:
        _atomic_write_json(raw_data, handoff_path)
    except OSError as err:
        sys.stderr.write(
            "import-handoff: failed to write handoff.json: {0}\n".format(err)
        )
        return 2

    sys.stdout.write(
        "imported: {0} → pre-seeded spec state"
        " (kind=research, spec_type={1}, constraints={2}, areas={3}, risks={4},"
        " open_questions={5}); downstream_links.spec_path set to {6}\n".format(
            handoff_path,
            spec_type,
            len(constraints),
            len(affected_areas),
            len(risks),
            len(open_questions),
            future_spec_path,
        )
    )
    return 0


def _inject_plan_seeds_internal_fields(raw_data: Dict[str, Any]) -> None:
    """Inject plan_seeds internal fields stripped by _asdict_handoff back before parsing.

    discover_handoff_schema.PlanSeeds has three constructor-required fields
    (_effort_estimate, _overall_fit, _derisk_count) that are stripped from the
    JSON by the handoff builder.  These must be re-injected from discovery_block
    for _dict_to_dataclass to construct PlanSeeds successfully.

    Mutates raw_data in-place.  Partial-injection: injects each field only when
    its source key is present.  When complexity exists but verify_cost is absent,
    defaults _derisk_count to 6 (High).  For fully valid handoff.json files
    (schema enforced at finalize-handoff time), all three fields are always
    present; partial-injection is fallback for corrupt/incomplete files surfaced
    via find-handoffs (which suppresses errors).
    """
    db = raw_data.get("discovery_block")
    ps = raw_data.get("plan_seeds")
    if not isinstance(db, dict) or not isinstance(ps, dict):
        return

    effort_estimate = db.get("effort_estimate")
    overall_fit = db.get("overall_fit")
    if effort_estimate is not None:
        ps["_effort_estimate"] = effort_estimate
    if overall_fit is not None:
        ps["_overall_fit"] = overall_fit

    # Derive a _derisk_count compatible with the stored complexity.verify_cost.
    complexity = ps.get("complexity")
    if isinstance(complexity, dict):
        verify_cost = complexity.get("verify_cost")
        if verify_cost == "Low":
            ps["_derisk_count"] = 1   # any value <= 2
        elif verify_cost == "Med":
            ps["_derisk_count"] = 3   # any value in 3-5
        else:
            ps["_derisk_count"] = 6   # any value > 5


def _import_handoff_discover(
    args: argparse.Namespace,
    handoff_path: Path,
    raw_data: Dict[str, Any],
) -> int:
    """Import a discover handoff.json into specify state."""
    # Inject plan_seeds internal fields stripped by the builder before parsing.
    _inject_plan_seeds_internal_fields(raw_data)
    try:
        handoff = _dict_to_dataclass(discover_handoff_schema.Handoff, raw_data)
    except (ValueError, TypeError) as err:
        sys.stderr.write(
            "import-handoff: schema validation failed: {0}\n".format(err)
        )
        return 2

    # Enforce spec_type_hint == "greenfield_feature" (schema already enforces this,
    # but guard here so the error is user-facing rather than a schema crash).
    seeds = handoff.spec_seeds
    if seeds.spec_type_hint != "greenfield_feature":
        sys.stderr.write(
            "import-handoff: discover handoff spec_type_hint must be"
            " 'greenfield_feature', got {0!r}\n".format(seeds.spec_type_hint)
        )
        return 2

    # Extract spec seeds — dedupe at source before converting to dicts.
    constraints_src = _dedupe_seeds(seeds.constraints, _constraint_key, "constraints")
    affected_areas_src = _dedupe_seeds(seeds.affected_areas, _affected_area_key, "affected_areas")
    risks_src = _dedupe_seeds(seeds.risks, _risk_key, "risks")
    open_questions_src = _dedupe_seeds(seeds.open_questions, _open_question_key, "open_questions")
    constraints = [_constraint_to_dict(c) for c in constraints_src]
    affected_areas = [_discover_affected_area_to_dict(a) for a in affected_areas_src]
    risks = [_risk_to_dict(r) for r in risks_src]
    open_questions = [_open_question_to_dict(q, i) for i, q in enumerate(open_questions_src)]
    spec_type = seeds.spec_type_hint

    # Plan 53 Phase 2 — carry the captured design_anchor across the ONE hop.
    # Deterministic: an empty anchor in the handoff (intake skipped capture)
    # yields an empty anchor in state, never an absent key.
    design_anchor = {
        "kind": seeds.design_anchor.kind,
        "file": seeds.design_anchor.file,
        "selectors": list(seeds.design_anchor.selectors),
    }

    # Discover-specific source fields.
    discover_completed_at = handoff.discover_completed_at
    plan_seeds = handoff.plan_seeds
    rationale = plan_seeds.recommended_option_rationale or ""
    bvb_rec = plan_seeds.build_vs_buy.recommendation
    discover_recommended_summary = "{0} | {1}".format(rationale, bvb_rec)

    # 68-INTAKE-OWNS-FEATURE-DIR-PLAN.md D5: the feature dir was already
    # allocated by /discover at intake finalize (D1) -- the handoff already
    # sits inside it. future_spec_path is simply that dir's spec.md; no NEW
    # NNN is computed here (next_spec_number is not called in this path;
    # handoff.intent.topic_slug is no longer consulted either).
    devforge_dir = Path(args.devforge_dir).resolve()
    repo_root = devforge_dir.parent
    handoff_path_rel = _root_relative(handoff_path, repo_root)
    future_spec_path = _root_relative(handoff_path.parent / "spec.md", repo_root)

    # python-reviewer finding 1 -- see the matching comment in
    # _import_handoff_research above; identical rationale for the discover
    # lane.
    dir_match = SPEC_NUMBER_DIR_RE.match(handoff_path.parent.name)

    # Pre-seed state; check for re-import.
    warn_user_content = False
    try:
        with _state_transaction(args.devforge_dir) as state:
            # Idempotency: check if source.handoff_path already set.
            source = state.get("source", {})
            existing_handoff = source.get("handoff_path") if source else None

            # Check user-composed content for warning.
            if existing_handoff is not None:
                if (state.get("overview")
                        or state.get("desired_behavior")
                        or state.get("acceptance_criteria")):
                    warn_user_content = True

            # Ensure "source" key exists (may be missing in old state).
            if "source" not in state:
                state["source"] = {
                    "handoff_path": None,
                    "handoff_kind": None,
                    "research_completed_at": None,
                    "discover_completed_at": None,
                    "discover_recommended_summary": None,
                }

            # Pre-seed fields.
            state["spec_type"] = spec_type
            state["spec_type_seeded_by_upstream"] = True
            state["constraints"] = constraints
            state["affected_areas"] = affected_areas
            state["risks"] = risks
            state["open_questions"] = open_questions
            state["design_anchor"] = design_anchor
            state["source"]["handoff_path"] = handoff_path_rel
            state["source"]["handoff_kind"] = "discover"
            state["source"]["discover_completed_at"] = discover_completed_at
            state["source"]["discover_recommended_summary"] = discover_recommended_summary
            if dir_match:
                state["spec_number"] = dir_match.group(1)
                state["feature_slug"] = dir_match.group(2)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write("import-handoff: state error: {0}\n".format(err))
        return 2

    if warn_user_content:
        sys.stderr.write(
            "import-handoff: warning: state has user-composed content"
            " (overview / desired_behavior / acceptance_criteria);"
            " pre-seeded blocks overwritten but user content preserved\n"
        )

    # Mutate handoff.json downstream_links.spec_path and write atomically.
    raw_data.setdefault("downstream_links", {})
    raw_data["downstream_links"]["spec_path"] = future_spec_path
    try:
        _atomic_write_json(raw_data, handoff_path)
    except OSError as err:
        sys.stderr.write(
            "import-handoff: failed to write handoff.json: {0}\n".format(err)
        )
        return 2

    sys.stdout.write(
        "imported: {0} → pre-seeded spec state"
        " (kind=discover, spec_type={1}, constraints={2}, areas={3}, risks={4},"
        " open_questions={5}); downstream_links.spec_path set to {6}\n".format(
            handoff_path,
            spec_type,
            len(constraints),
            len(affected_areas),
            len(risks),
            len(open_questions),
            future_spec_path,
        )
    )
    return 0


# ---------------------------------------------------------------------------
# cmd_find_handoffs.
# ---------------------------------------------------------------------------


def _try_research_hit(fpath: Path) -> Optional[Dict[str, Any]]:
    """Build a find-handoffs hit dict for a candidate research-handoff.json.

    Returns None (silently) when the file is absent, unreadable, corrupt, or
    schema-invalid — find-handoffs skips those rather than erroring.
    """
    if not fpath.is_file():
        return None
    try:
        mtime = fpath.stat().st_mtime
    except OSError:
        return None
    try:
        raw = json.loads(fpath.read_text(encoding="utf-8"))
        # Guard: only accept files without handoff_kind or with kind=="research".
        raw_kind = raw.get("handoff_kind", "research")
        if raw_kind != "research":
            return None
        handoff = _dict_to_dataclass(handoff_schema.Handoff, raw)
    except Exception:
        return None  # corrupt or invalid — skip silently

    mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
    mtime_iso = mtime_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    summary = handoff.plan_seeds.recommended_approach_summary
    if len(summary) > 80:
        summary = summary[:77] + "..."

    return {
        "mtime_ts": mtime,
        "mtime_iso": mtime_iso,
        "handoff_path": str(fpath),
        "kind": "research",
        "mode_or_verdict": "mode={0}".format(handoff.mode),
        "summary": summary,
    }


def _try_discover_hit(fpath: Path) -> Optional[Dict[str, Any]]:
    """Build a find-handoffs hit dict for a candidate discover-handoff.json.

    Returns None (silently) when the file is absent, unreadable, corrupt, or
    schema-invalid — find-handoffs skips those rather than erroring.
    """
    if not fpath.is_file():
        return None
    try:
        mtime = fpath.stat().st_mtime
    except OSError:
        return None
    try:
        raw = json.loads(fpath.read_text(encoding="utf-8"))
        _inject_plan_seeds_internal_fields(raw)
        handoff = _dict_to_dataclass(discover_handoff_schema.Handoff, raw)
    except Exception:
        return None  # corrupt or invalid — skip silently

    mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
    mtime_iso = mtime_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    summary = handoff.plan_seeds.recommended_option_rationale
    if not summary:
        summary = handoff.intent.feature_concept
    if len(summary) > 80:
        summary = summary[:77] + "..."

    return {
        "mtime_ts": mtime,
        "mtime_iso": mtime_iso,
        "handoff_path": str(fpath),
        "kind": "discover",
        "mode_or_verdict": "verdict={0}".format(handoff.discovery_block.verdict),
        "summary": summary,
    }


def cmd_find_handoffs(args: argparse.Namespace) -> int:
    """List feature dirs carrying a PENDING intake handoff (plan 68 D5).

    One glob pass over specs/*/research-handoff.json and
    specs/*/discover-handoff.json, filtered to feature dirs that do NOT yet
    contain spec.md — the D5 structural predicate ("an intake handoff is
    present AND the feature has not already been consumed by /specify").
    A feature dir may legitimately surface both a research hit and a
    discover hit if both files happen to be present.

    --since is DEPRECATED, accepted-but-ignored (plan 68 Phase 4 / OQ-2):
    the old --since mtime window existed to avoid resurfacing a stale
    top-level research/discover run, but under the D5 predicate a feature
    is "pending" precisely because /specify has not consumed it yet — a
    window would incorrectly BLOCK a legitimately-paused 8-day-old feature.
    When supplied, the format is still validated (so a typo like --since
    "foo" still fails loud), but the value is never applied as a filter.
    mtime remains the ORDER key only (most-recent-first) — see the sort
    below.

    --require: when set, exit 2 with a BLOCKED message on zero hits instead
      of exit 0.  Callers that need the handoff-exists precondition (e.g.
      Phase 0.4) pass --require; callers that only want the list (e.g.
      multi-pick UI) omit it.  The --require path does NOT offer an
      override or escape hatch.

    Output format (most-recent mtime first; ties broken by handoff_path for
    determinism):
      <mtime ISO> | <handoff_path> | kind=<research|discover> | <mode_or_verdict> | <summary>
    For research: mode_or_verdict = "mode=<mode>", summary from plan_seeds.recommended_approach_summary.
    For discover: mode_or_verdict = "verdict=<verdict>", summary from plan_seeds.recommended_option_rationale.
    Summary truncated to 80 chars.
    Skips corrupt or schema-invalid files silently.
    Exit 0 on zero hits (unless --require).
    """
    since_str = getattr(args, "since", None) or ""
    if since_str and _parse_since_seconds(since_str) is None:
        sys.stderr.write(
            "find-handoffs: --since must match '<N> day(s)|hour(s)|minute(s)',"
            " got {0!r}\n".format(since_str)
        )
        return 2

    devforge_dir = Path(args.devforge_dir).resolve()
    repo_root = devforge_dir.parent
    specs_root = repo_root / "specs"

    hits: List[Dict[str, Any]] = []

    if specs_root.exists() and specs_root.is_dir():
        for feature_dir in sorted(specs_root.iterdir()):
            if not feature_dir.is_dir():
                continue
            if (feature_dir / "spec.md").exists():
                continue  # D5: already consumed by /specify — not pending

            research_hit = _try_research_hit(feature_dir / "research-handoff.json")
            if research_hit is not None:
                hits.append(research_hit)

            discover_hit = _try_discover_hit(feature_dir / "discover-handoff.json")
            if discover_hit is not None:
                hits.append(discover_hit)

    # Most-recent mtime first; ties broken by handoff_path for determinism.
    hits.sort(key=lambda h: (-h["mtime_ts"], h["handoff_path"]))

    # --require gate: block when zero hits instead of exit 0.
    require = getattr(args, "require", False)
    if require and not hits:
        sys.stderr.write(
            "BLOCKED: /specify requires a pending research or discover handoff.\n"
            "No feature dir under specs/ carries an intake handoff"
            " (specs/*/research-handoff.json or specs/*/discover-handoff.json)"
            " that has not already been consumed by /specify (i.e. its"
            " spec.md does not yet exist).\n"
            "\n"
            "Run one of the following first, then retry /specify:\n"
            "  /research \"<topic>\"  — for a bug or enhancement against existing code\n"
            "  /discover \"<idea>\"   — for a greenfield feature\n"
        )
        return 2

    for h in hits:
        sys.stdout.write(
            "{0} | {1} | kind={2} | {3} | {4}\n".format(
                h["mtime_iso"],
                h["handoff_path"],
                h["kind"],
                h["mode_or_verdict"],
                h["summary"],
            )
        )

    return 0


# ---------------------------------------------------------------------------
# cmd_finalize_handoff (specify -> plan producer).
# ---------------------------------------------------------------------------


def cmd_finalize_handoff(args):
    # type: (argparse.Namespace) -> int
    """Read specify state -> build specify Handoff -> validate -> write handoff.json.

    State is read-only.  No mutation of specify-state.json.

    Trust boundary: this verb does NOT verify the user approved the spec, and
    does NOT re-run specify's content gates (verify-coverage /
    verify-ac-subsection-coverage / verify-ac-shape). It cannot: /specify
    leaves spec status "Draft" through approval (the Draft->Approved flip is
    owned by /plan), so there is no state field that proves "approved". The
    seam is the /specify Phase 5 command spec calling this verb ONLY on the
    Phase 5.3 approve branch, after Phase 4 rendered + Phase 4.9 verifiers ran.
    Re-running gates here would duplicate gate logic (a second source of
    truth). Render-completeness is still enforced: missing spec_number /
    feature_slug fails fast, and empty/partial section content fails schema
    validation (e.g. empty overview).

    Args exposed via CLI:
      --devforge-dir     (required, inherited from parent parser)
      --emit-handoff-json  (optional; default: {specs_root}/{number}-{slug}/handoff.json)
      --specs-root         (optional; default: "specs")
      --completed-at       (optional; ISO-8601 UTC string; defaults to now)
    """
    devforge_dir = args.devforge_dir
    specs_root = getattr(args, "specs_root", None) or "specs"
    completed_at_override = getattr(args, "completed_at", None)

    # Load state (read-only).
    try:
        state = _load_state(devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("finalize-handoff: cannot load state: {0}".format(err))

    # No status guard: /specify leaves status "Draft" through approval (the
    # caller -- /specify Phase 5.3 approve branch -- is the gate). Render
    # completeness is enforced below (spec_number/feature_slug) and by schema
    # validation (e.g. empty overview fails).

    # Resolve spec_path.
    spec_number = state.get("spec_number") or ""
    feature_slug = state.get("feature_slug") or ""
    if not spec_number or not feature_slug:
        return _die(
            "finalize-handoff: spec_number and feature_slug must be set in state"
            " (run assign-spec-number + assign-feature-name first)",
            code=2,
        )
    spec_path = "{0}/{1}-{2}/spec.md".format(specs_root, spec_number, feature_slug)

    # Resolve specify_completed_at.
    if completed_at_override:
        specify_completed_at = completed_at_override.strip()
    else:
        specify_completed_at = (
            _datetime_module.datetime.now(_datetime_module.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    # Build Classification. Wrapped in try/except so a corrupt/legacy
    # spec_type (not in SPEC_TYPE_ENUM) yields a clean error + exit code,
    # not a raw traceback.
    try:
        classification = specify_handoff_schema.Classification(
            spec_number=state.get("spec_number") or "",
            feature_name=state.get("feature_name") or "",
            feature_slug=state.get("feature_slug") or "",
            spec_type=state.get("spec_type") or "",
            spec_type_rationale=state.get("spec_type_rationale") or "",
            status=state.get("status") or "",
        )
    except (TypeError, ValueError) as err:
        return _die(
            "finalize-handoff: schema validation failed building classification: {0}".format(err),
            code=2,
        )

    # Build SpecSeeds — expand each list into its schema dataclass.
    try:
        acceptance_criteria = [
            specify_handoff_schema.AcceptanceCriterion(**ac)
            for ac in (state.get("acceptance_criteria") or [])
        ]
        constraints = [
            specify_handoff_schema.Constraint(**c)
            for c in (state.get("constraints") or [])
        ]
        # Whitelist to specify's AffectedArea fields. discover-seeded state
        # (via import-handoff) carries the discover-only key
        # is_internal_extension_candidate, which the specify AffectedArea
        # dataclass does not accept; /plan does not need it. Dropping it here
        # keeps the greenfield /discover -> /specify -> /plan path working.
        affected_areas = [
            specify_handoff_schema.AffectedArea(**{
                k: v for k, v in a.items()
                if k in ("area", "files", "impact")
            })
            for a in (state.get("affected_areas") or [])
        ]
        out_of_scope = [
            specify_handoff_schema.OutOfScopeItem(**o)
            for o in (state.get("out_of_scope") or [])
        ]
        open_questions = [
            specify_handoff_schema.OpenQuestion(**q)
            for q in (state.get("open_questions") or [])
        ]
        risks = [
            specify_handoff_schema.Risk(**r)
            for r in (state.get("risks") or [])
        ]
    except (TypeError, ValueError) as err:
        return _die(
            "finalize-handoff: schema validation failed building spec_seeds: {0}".format(err),
            code=2,
        )

    try:
        # design_anchor is deliberately left at its DesignAnchor() default here
        # (no design_anchor= kwarg) -- do NOT thread state["design_anchor"]
        # through this handoff. Its single source of truth is the sibling
        # specs/[feature]/design-anchor.json (plan 53 D5, park-once /
        # read-in-place); /plan reads THAT file, never spec_seeds.design_anchor.
        # Populating both would create a two-source desync D5 forbids.
        spec_seeds = specify_handoff_schema.SpecSeeds(
            overview=state.get("overview") or "",
            acceptance_criteria=acceptance_criteria,
            ac_subsection_na=dict(state.get("ac_subsection_na") or {}),
            constraints=constraints,
            affected_areas=affected_areas,
            out_of_scope=out_of_scope,
            open_questions=open_questions,
            risks=risks,
        )
    except (TypeError, ValueError) as err:
        return _die(
            "finalize-handoff: schema validation failed building SpecSeeds: {0}".format(err),
            code=2,
        )

    # Build Provenance from state["source"].
    source = state.get("source") or {}
    upstream_handoff_path = source.get("handoff_path") or None
    upstream_handoff_kind = source.get("handoff_kind") or None

    # Map completed_at from the correct source key based on kind.
    upstream_completed_at = None  # type: Optional[str]
    if upstream_handoff_kind == "research":
        upstream_completed_at = source.get("research_completed_at") or None
    elif upstream_handoff_kind == "discover":
        upstream_completed_at = source.get("discover_completed_at") or None

    try:
        provenance = specify_handoff_schema.Provenance(
            upstream_handoff_path=upstream_handoff_path,
            upstream_handoff_kind=upstream_handoff_kind,
            upstream_completed_at=upstream_completed_at,
        )
    except (TypeError, ValueError) as err:
        return _die(
            "finalize-handoff: schema validation failed building Provenance: {0}".format(err),
            code=2,
        )

    downstream_links = specify_handoff_schema.DownstreamLinks()

    # Build top-level Handoff.
    try:
        handoff = specify_handoff_schema.Handoff(
            schema_version=specify_handoff_schema.SCHEMA_VERSION,
            handoff_kind=specify_handoff_schema.HANDOFF_KIND,
            spec_path=spec_path,
            specify_completed_at=specify_completed_at,
            classification=classification,
            spec_seeds=spec_seeds,
            provenance=provenance,
            downstream_links=downstream_links,
        )
    except (TypeError, ValueError) as err:
        return _die(
            "finalize-handoff: schema validation failed: {0}".format(err),
            code=2,
        )

    # Determine emit path.
    emit_path = getattr(args, "emit_handoff_json", None)
    if not emit_path:
        emit_path = "{0}/{1}-{2}/handoff.json".format(specs_root, spec_number, feature_slug)

    target = Path(emit_path)
    if not target.is_absolute():
        target = Path.cwd() / target
    target = target.resolve()

    # Atomic write.
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(dataclasses.asdict(handoff), target)
    except OSError as err:
        return _die(
            "finalize-handoff: cannot write {0}: {1}".format(target, err)
        )

    sys.stdout.write("wrote: {0}\n".format(target))
    return 0
