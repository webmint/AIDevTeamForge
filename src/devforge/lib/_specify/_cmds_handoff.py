"""Handoff subcommands: import-handoff + find-handoffs.

Pre-phase (Phase 0.4) helpers that bridge research_helper finalize-handoff
and discover_helper finalize-handoff output into specify-state.json
pre-seeded fields.

import-handoff:
  Reads a handoff.json produced by research_helper or discover_helper
  finalize-handoff, validates it via handoff_schema (schema dataclasses),
  and pre-seeds specify state with spec_type, constraints, affected_areas,
  risks, open_questions.  Dispatch is on handoff_kind field:
    "discover"           -> discover branch (source has handoff_kind + discover_completed_at).
    absent / "research"  -> research branch (existing behaviour).
  Unknown explicit handoff_kind -> exit 2.

find-handoffs:
  Glob research/**/handoff.json AND discover/*.handoff.json under the repo
  root (parent of .devforge dir).  Filter by mtime within a --since window.
  Emit one line per hit; skip corrupt or schema-invalid files silently.
  Exit 0 even on zero hits.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._schema import SPEC_NUMBER_DIR_RE, SPEC_NUMBER_WIDTH, SPECS_ROOT_DEFAULT
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

# Research-path slug extraction — matches two common patterns:
#   research/YYYY-MM-DD-<slug>.md
#   research/YYYY-MM-DD-<slug>/handoff.json
_RESEARCH_PATH_SLUG_RE = re.compile(
    r'\d{4}-\d{2}-\d{2}-([^/\\]+?)(?:\.md|/.*)?$'
)


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



def _extract_slug_from_research_path(research_path: str) -> str:
    """Derive a feature slug from the research_path field in handoff.json.

    Matches patterns:
      research/YYYY-MM-DD-<slug>.md
      research/YYYY-MM-DD-<slug>/handoff.json
    Falls back to a sanitized version of the basename.
    """
    m = _RESEARCH_PATH_SLUG_RE.search(research_path)
    if m:
        return m.group(1)
    # Fallback: use basename without extension, strip leading date pattern.
    base = Path(research_path).stem
    # Remove leading YYYY-MM-DD- prefix if present.
    base = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', base)
    # Replace non-alnum/hyphen characters with hyphens and lower-case.
    base = re.sub(r'[^a-z0-9-]', '-', base.lower()).strip('-')
    return base or "unknown"


def _next_spec_number(devforge_dir: Path) -> int:
    """Compute the next NNN spec number by scanning the specs/ directory.

    Looks for subdirectories matching NNN-* pattern under repo root / specs/.
    Returns 1 if none exist.
    """
    # Repo root is the parent of the .devforge dir.
    repo_root = Path(devforge_dir).parent
    specs_root = repo_root / SPECS_ROOT_DEFAULT
    if not specs_root.exists() or not specs_root.is_dir():
        return 1
    existing: List[int] = []
    for entry in specs_root.iterdir():
        if entry.is_dir():
            m = SPEC_NUMBER_DIR_RE.match(entry.name)
            if m:
                existing.append(int(m.group(1)))
    return (max(existing) + 1) if existing else 1



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

    # Extract spec seeds.
    seeds = handoff.spec_seeds
    constraints = [_constraint_to_dict(c) for c in seeds.constraints]
    affected_areas = [_affected_area_to_dict(a) for a in seeds.affected_areas]
    risks = [_risk_to_dict(r) for r in seeds.risks]
    open_questions = [_open_question_to_dict(q, i) for i, q in enumerate(seeds.open_questions)]
    spec_type = seeds.spec_type_hint
    research_completed_at = handoff.research_completed_at

    # Compute future spec_path.
    devforge_dir = Path(args.devforge_dir).resolve()
    nnn = _next_spec_number(devforge_dir)
    slug = _extract_slug_from_research_path(handoff.research_path)
    nnn_str = str(nnn).zfill(SPEC_NUMBER_WIDTH)
    future_spec_path = "specs/{0}-{1}/spec.md".format(nnn_str, slug)

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
            state["source"]["handoff_path"] = str(handoff_path)
            state["source"]["handoff_kind"] = "research"
            state["source"]["research_completed_at"] = research_completed_at
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

    # Extract spec seeds.  Converters are compatible (same field names).
    constraints = [_constraint_to_dict(c) for c in seeds.constraints]
    affected_areas = [_discover_affected_area_to_dict(a) for a in seeds.affected_areas]
    risks = [_risk_to_dict(r) for r in seeds.risks]
    open_questions = [_open_question_to_dict(q, i) for i, q in enumerate(seeds.open_questions)]
    spec_type = seeds.spec_type_hint

    # Discover-specific source fields.
    discover_completed_at = handoff.discover_completed_at
    plan_seeds = handoff.plan_seeds
    rationale = plan_seeds.recommended_option_rationale or ""
    bvb_rec = plan_seeds.build_vs_buy.recommendation
    discover_recommended_summary = "{0} | {1}".format(rationale, bvb_rec)

    # Compute future spec_path using intent.topic_slug (discover has no research_path).
    devforge_dir = Path(args.devforge_dir).resolve()
    nnn = _next_spec_number(devforge_dir)
    slug = handoff.intent.topic_slug
    nnn_str = str(nnn).zfill(SPEC_NUMBER_WIDTH)
    future_spec_path = "specs/{0}-{1}/spec.md".format(nnn_str, slug)

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
            state["source"]["handoff_path"] = str(handoff_path)
            state["source"]["handoff_kind"] = "discover"
            state["source"]["discover_completed_at"] = discover_completed_at
            state["source"]["discover_recommended_summary"] = discover_recommended_summary
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


def cmd_find_handoffs(args: argparse.Namespace) -> int:
    """Glob research/**/handoff.json and discover/*.handoff.json; filter by mtime.

    --since accepts: "<N> day(s)", "<N> hour(s)", "<N> minute(s)".
    Output format (newest first):
      <mtime ISO> | <handoff_path> | kind=<research|discover> | <mode_or_verdict> | <summary>
    For research: mode_or_verdict = "mode=<mode>", summary from plan_seeds.recommended_approach_summary.
    For discover: mode_or_verdict = "verdict=<verdict>", summary from plan_seeds.recommended_option_rationale.
    Summary truncated to 80 chars.
    Skips corrupt or schema-invalid files silently.
    Exit 0 even on zero hits.
    """
    since_str = getattr(args, "since", None) or ""
    since_seconds = _parse_since_seconds(since_str)
    if since_seconds is None:
        sys.stderr.write(
            "find-handoffs: --since must match '<N> day(s)|hour(s)|minute(s)',"
            " got {0!r}\n".format(since_str)
        )
        return 2

    devforge_dir = Path(args.devforge_dir).resolve()
    repo_root = devforge_dir.parent

    now_ts = datetime.now(timezone.utc).timestamp()
    cutoff_ts = now_ts - since_seconds

    hits: List[Dict[str, Any]] = []

    # --- Walk research/**/handoff.json ---
    research_dir = repo_root / "research"
    if research_dir.exists():
        for root_dir, dirs, files in os.walk(str(research_dir)):
            dirs.sort()  # deterministic traversal
            for fname in files:
                if fname != "handoff.json":
                    continue
                fpath = Path(root_dir) / fname
                try:
                    mtime = fpath.stat().st_mtime
                except OSError:
                    continue  # skip inaccessible files

                if mtime < cutoff_ts:
                    continue

                # Try to parse and validate — skip silently on failure.
                try:
                    raw = json.loads(fpath.read_text(encoding="utf-8"))
                    # Guard: only accept files without handoff_kind or with kind=="research".
                    raw_kind = raw.get("handoff_kind", "research")
                    if raw_kind != "research":
                        continue
                    handoff = _dict_to_dataclass(handoff_schema.Handoff, raw)
                except Exception:
                    continue  # corrupt or invalid — skip silently

                mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                mtime_iso = mtime_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

                summary = handoff.plan_seeds.recommended_approach_summary
                if len(summary) > 80:
                    summary = summary[:77] + "..."

                hits.append({
                    "mtime_ts": mtime,
                    "mtime_iso": mtime_iso,
                    "handoff_path": str(fpath),
                    "kind": "research",
                    "mode_or_verdict": "mode={0}".format(handoff.mode),
                    "summary": summary,
                })

    # --- Walk discover/*.handoff.json ---
    discover_dir = repo_root / "discover"
    if discover_dir.exists():
        for fpath in sorted(discover_dir.iterdir()):
            if not fpath.is_file():
                continue
            if not fpath.name.endswith(".handoff.json"):
                continue

            try:
                mtime = fpath.stat().st_mtime
            except OSError:
                continue  # skip inaccessible files

            if mtime < cutoff_ts:
                continue

            # Try to parse and validate — skip silently on failure.
            try:
                raw = json.loads(fpath.read_text(encoding="utf-8"))
                _inject_plan_seeds_internal_fields(raw)
                handoff = _dict_to_dataclass(discover_handoff_schema.Handoff, raw)
            except Exception:
                continue  # corrupt or invalid — skip silently

            mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
            mtime_iso = mtime_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            summary = handoff.plan_seeds.recommended_option_rationale
            if not summary:
                summary = handoff.intent.feature_concept
            if len(summary) > 80:
                summary = summary[:77] + "..."

            hits.append({
                "mtime_ts": mtime,
                "mtime_iso": mtime_iso,
                "handoff_path": str(fpath),
                "kind": "discover",
                "mode_or_verdict": "verdict={0}".format(
                    handoff.discovery_block.verdict
                ),
                "summary": summary,
            })

    # Sort newest first (across both lists merged).
    hits.sort(key=lambda h: h["mtime_ts"], reverse=True)

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
