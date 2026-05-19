"""Handoff subcommands: import-handoff + find-handoffs.

Pre-phase (Phase 0.4) helpers that bridge research_helper finalize-handoff
output into specify-state.json pre-seeded fields.

import-handoff:
  Reads a handoff.json produced by research_helper finalize-handoff, validates
  it via handoff_schema (schema dataclasses), and pre-seeds specify state with
  spec_type, constraints, affected_areas, risks, open_questions. Records
  source.handoff_path + source.research_completed_at. Mutates downstream_links
  in the handoff.json itself with the computed future spec_path.

find-handoffs:
  Glob research/**/handoff.json under the repo root (parent of .devforge dir).
  Filter by mtime within a --since window. Emit one line per hit; skip corrupt
  or schema-invalid files silently. Exit 0 even on zero hits.

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
# handoff_schema import — path injection mirrors research_helper.py line 82.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent.parent  # src/devforge/lib/
_RESEARCH_DIR = _HERE / "_research"
if str(_RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(_RESEARCH_DIR))
import handoff_schema  # noqa: E402  type: ignore[import]


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


def _load_and_validate_handoff(handoff_path: Path) -> handoff_schema.Handoff:
    """Read handoff.json, parse JSON, validate via schema dataclasses.

    Raises:
      FileNotFoundError if path does not exist.
      json.JSONDecodeError if not valid JSON.
      ValueError / TypeError if schema validation fails.
    """
    raw = handoff_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    return _dict_to_dataclass(handoff_schema.Handoff, data)


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
    """Serialize a handoff_schema.AffectedArea to the specify-state dict shape."""
    return {"area": a.area, "files": list(a.files), "impact": a.impact}


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
    """Pre-seed specify state from a research handoff.json.

    Steps:
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
                state["source"] = {"handoff_path": None, "research_completed_at": None}

            # Pre-seed fields (overwrite pre-seeded blocks; user content preserved).
            state["spec_type"] = spec_type
            state["spec_type_seeded_by_upstream"] = True
            state["constraints"] = constraints
            state["affected_areas"] = affected_areas
            state["risks"] = risks
            state["open_questions"] = open_questions
            state["source"]["handoff_path"] = str(handoff_path)
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
        " (spec_type={1}, constraints={2}, areas={3}, risks={4},"
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
    """Glob research/**/handoff.json; filter by mtime; emit one line per hit.

    --since accepts: "<N> day(s)", "<N> hour(s)", "<N> minute(s)".
    Output format (newest first):
      <mtime ISO> | <research_path> | <mode> | <summary truncated to 80 chars>
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

    research_dir = repo_root / "research"
    if not research_dir.exists():
        # Zero hits — no research dir at all.
        return 0

    now_ts = datetime.now(timezone.utc).timestamp()
    cutoff_ts = now_ts - since_seconds

    hits: List[Dict[str, Any]] = []

    # Walk research/**/handoff.json.
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
                handoff = _dict_to_dataclass(handoff_schema.Handoff, raw)
            except Exception:
                continue  # corrupt or invalid — skip silently

            # Convert mtime to ISO string.
            mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
            mtime_iso = mtime_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            summary = handoff.plan_seeds.recommended_approach_summary
            if len(summary) > 80:
                summary = summary[:77] + "..."

            hits.append({
                "mtime_ts": mtime,
                "mtime_iso": mtime_iso,
                "research_path": handoff.research_path,
                "mode": handoff.mode,
                "summary": summary,
            })

    # Sort newest first.
    hits.sort(key=lambda h: h["mtime_ts"], reverse=True)

    for h in hits:
        sys.stdout.write(
            "{0} | {1} | {2} | {3}\n".format(
                h["mtime_iso"],
                h["research_path"],
                h["mode"],
                h["summary"],
            )
        )

    return 0
