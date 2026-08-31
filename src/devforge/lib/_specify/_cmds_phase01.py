"""Phase 0 + Phase 1 + Phase 1.5 cmd_* handlers + detect_mode helper."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._schema import (
    AUTO_MODE_ENV_VAR,
    AUTO_MODE_REMINDER_SUBSTRINGS,
    CONSTITUTION_POPULATE_GUARDS,
    LANDED_IN_DEFAULT,
    LANDED_IN_ENUM,
    PHASE1_MANDATORY_READS,
    PREFLIGHT_PREREQS,
    _RENDER_SECTION_ORDER,
)
from ._state import (
    _atomic_write_json,
    _load_state,
    _state_path,
    _state_transaction,
    default_state,
)
from ._topic import (
    DISCOVERY_REPORT_BASENAME,
    RESEARCH_REPORT_BASENAME,
    normalize_source_path,
    source_origin_for_path,
)
from ._validators import _die, _utc_timestamp, _validate_enum, _validate_scalar
from _shared.memory import (  # type: ignore[import]
    MEMORY_RELATIVE_PATH,
    MEMORY_STATE_ENUM,
    MEMORY_STATE_KEY,
    probe_memory_state,
)


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
    """4-artefact hard gate + constitution populate-guard."""
    install_root = Path(args.install_root)
    missing: List[Tuple[str, str]] = []
    populate_guard_present = False
    matched_guard = None
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
            for sentinel in CONSTITUTION_POPULATE_GUARDS:
                if sentinel in text:
                    populate_guard_present = True
                    matched_guard = sentinel
                    break

    if missing or populate_guard_present:
        sys.stderr.write(
            "BLOCKED: /devforge:specify requires the full 4-command setup chain.\n"
        )
        for rel, producer in missing:
            sys.stderr.write(
                "Missing: {0} (produced by {1})\n".format(rel, producer)
            )
        if populate_guard_present:
            sys.stderr.write(
                "constitution.md present but populate-guard literal "
                "{0!r} still in place — run /devforge:constitute to populate.\n".format(
                    matched_guard,
                )
            )
        sys.stderr.write(
            "Run: /devforge:init-forge → /devforge:generate-docs → /devforge:configure → "
            "/devforge:constitute, then retry /devforge:specify.\n"
        )
        return 2
    return 0


def cmd_record_input_read(args: argparse.Namespace) -> int:
    """Record one Phase 1 input read; auto-tag source_origin from path.

    Idempotent: re-recording the same path overwrites the prior entry.

    source_origin_for_path is given `root` (the install root implied by
    --devforge-dir, same convention as specs_root_for) so that an
    absolute path -- e.g. the `<feature_dir>`-token reads main.md composes
    off find-handoffs's `.resolve()`d handoff_path -- classifies exactly
    as the repo-relative spelling of the same file would (91-FEATURE-DIR-
    IDENTITY-AND-PROVENANCE-PLAN.md). `root` is inert for a relative
    `path` (the common case), so this costs one extra `Path.resolve()`
    per call and changes no relative-path classification.

    When `path` is the persistent-memory path (MEMORY_RELATIVE_PATH), the
    helper PROBES the file itself via probe_memory_state() and records the
    OBSERVED three-state result under MEMORY_STATE_KEY. This is a value the
    caller cannot supply -- there is no CLI flag for it -- because the
    entire point is that the recorded state is a fact the helper produced
    by touching the filesystem, not an assertion an LLM caller could pass
    without having read anything. cmd_phase1_finalize below relies on this
    field's presence to distinguish "declared absent/stub" (fine) from
    "claimed a read that never happened" (rejected). Every other path
    keeps the record's existing 3-key shape unchanged.
    """
    try:
        path = _validate_scalar(args.path, "record-input-read.path")
    except ValueError as err:
        return _die(str(err), code=2)
    workspace_root = Path(args.devforge_dir).resolve().parent
    origin = source_origin_for_path(path, root=str(workspace_root))
    entry: Dict[str, Any] = {
        "path": path,
        "source_origin": origin,
        "read_timestamp": _utc_timestamp(),
    }
    if path == MEMORY_RELATIVE_PATH:
        entry[MEMORY_STATE_KEY] = probe_memory_state(str(workspace_root))
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["input_reads"] = [
                r for r in state["input_reads"] if r.get("path") != path
            ]
            state["input_reads"].append(entry)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-input-read: {0}".format(err))
    return 0


def cmd_phase1_finalize(args: argparse.Namespace) -> int:
    """Gate Phase 1 → Phase 1.5. All 4 mandatory base reads required.

    The memory slot (MEMORY_RELATIVE_PATH) carries one extra requirement
    on top of mere presence: its record must also carry a
    probe-produced MEMORY_STATE_KEY value. A record with the path but no
    (or an invalid) state value means record-input-read never actually
    probed the file for it -- e.g. a specify-state.json written before
    this check existed, or any other way a bare path landed in
    input_reads without going through the probe. absent and stub are
    both LEGITIMATE observed states (most fresh installs ship the stub,
    zero lessons learned yet) and pass exactly like populated does --
    only the ABSENCE of an observed state is rejected.
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

            memory_record = next(
                (
                    r for r in state["input_reads"]
                    if r.get("path") == MEMORY_RELATIVE_PATH
                ),
                None,
            )
            memory_state = (memory_record or {}).get(MEMORY_STATE_KEY)
            if memory_state not in MEMORY_STATE_ENUM:
                sys.stderr.write(
                    "phase1-finalize: memory record carries no "
                    "probe-produced state:\n"
                )
                sys.stderr.write(
                    "  - {0}: no valid {1!r} recorded (claimed a read "
                    "the probe never performed)\n".format(
                        MEMORY_RELATIVE_PATH, MEMORY_STATE_KEY,
                    )
                )
                sys.stderr.write(
                    "  Fix: re-run `record-input-read --path {0}` so "
                    "the helper probes the file itself -- a hand-edited "
                    "or pre-upgrade state record cannot satisfy this "
                    "gate.\n".format(MEMORY_RELATIVE_PATH)
                )
                return 2

            state["phase1_finalized"] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("phase1-finalize: {0}".format(err))
    return 0


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
    """Mark a read source as having no task-relevant content."""
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


def _group_for_path(path: str, root: Optional[str] = None) -> str:
    """Map a recorded input path to its render-group key.

    68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4: a feature dir's
    research-report.md and discovery-report.md (either shape -- legacy
    specs/NNN-slug/ or Phase-3 specs/YYYY/MM/<leaf>/) must still land in the
    "research/" / "discover/" render groups (matching
    source_origin_for_path's filename-aware dispatch in _topic.py), not
    fall through to the generic "specs/" prefix group shared with
    prior_spec files -- else a research/discover finding would silently
    render under the wrong heading. _RENDER_SECTION_ORDER itself needs no
    change: its group KEYS ("research/", "discover/", "specs/", ...) are
    unchanged -- only which paths map to them changed.

    91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md: shares
    normalize_source_path with source_origin_for_path so an absolute
    `path` groups exactly as the repo-relative spelling of the same file
    does -- the two functions answer DIFFERENT questions (this one a
    render-heading key, not a 4-way provenance tag; see the module-level
    comment above RESEARCH_REPORT_BASENAME for why they stay separate
    functions) but were duplicating the same strip/"./"/absolute-path
    normalization independently, which is the part that actually needed
    to be shared. When `path` is absolute and NOT under `root`,
    normalize_source_path hands back the (stripped) absolute original
    unchanged and this function -- exactly like every other path
    matching none of its prefixes -- returns it as its own private group
    key, so it renders under no shared heading it doesn't belong to.
    """
    p, in_root = normalize_source_path(path, root)
    if not in_root:
        return p
    if p.startswith("specs/"):
        basename = p.rsplit("/", 1)[-1]
        if basename == RESEARCH_REPORT_BASENAME:
            return "research/"
        if basename == DISCOVERY_REPORT_BASENAME:
            return "discover/"
    for prefix in ("research/", "discover/", "docs/", "specs/"):
        if p.startswith(prefix):
            return prefix
    return p


def cmd_render_findings(args: argparse.Namespace) -> int:
    """Emit Phase 1.5 findings section in v3-verbatim format.

    `root` (derived the same way as cmd_record_input_read's
    workspace_root: `Path(args.devforge_dir).resolve().parent`) is passed
    to _group_for_path so a recorded absolute path -- e.g. the one
    record-input-read stored verbatim from a `<feature_dir>`-token read --
    groups under the same heading its repo-relative spelling would
    (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md). --devforge-dir is a
    global argument on every specify_helper subcommand, so it is already
    in hand here exactly as it is in cmd_record_input_read.
    """
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-findings: {0}".format(err))
    workspace_root = str(Path(args.devforge_dir).resolve().parent)
    lines: List[str] = ["## Findings from Inputs", ""]
    reads_by_group: Dict[str, List[str]] = {}
    for r in state["input_reads"]:
        g = _group_for_path(r.get("path", ""), root=workspace_root)
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


def detect_mode(
    env: Dict[str, str],
    auto_flag: bool,
    reminder_text: str,
) -> str:
    """C-strict mode detection (Variance rule #8). Three signals:

      - DEVFORGE_AUTO_MODE env var == "1"
      - --auto flag set
      - case-insensitive substring of any AUTO_MODE_REMINDER_SUBSTRINGS in
        the supplied reminder_text

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
