"""Intake re-run marker substrate shared by /research, /discover, /specify.

Provenance: 109-REENTRY-CHAIN-CONTINUITY-PLAN.md D3 (self-clearing marker),
D6 (consumed-seed record), OQ-1 (marker filename), OQ-4 (no marker when
spec.md is absent).

The defect this serves: /grill writes grill-seed.json with target_stage
"research" or "discovery"; the intake command re-runs in attach mode into
the same feature dir and rewrites its handoff, but /specify's pending
predicate then blocks (spec.md exists and no seed targets "spec").  The
intake helpers' finalize-handoff write `intake-rerun.json` here when spec.md
exists; specify_helper's find-handoffs arm (c) reads it via marker_admits.

Self-clearing rule.  Arm (c) admits a dir while the marker's recorded
spec_sha256 equals the CURRENT sha256 of spec.md.  Once /specify re-renders
a changed spec.md the hashes diverge and arm (c) closes by itself; the
marker is never deleted.

Honest bounds.  A hand edit to spec.md (even whitespace) closes arm (c); a
byte-identical re-render leaves it open; a byte-identical rewrite of
grill-seed.json is read as already consumed by seed_consumed.

The marker is the consumer's record of its OWN consumption: the seed file is
never touched or mutated by anything here.

The marker filename deliberately does NOT end in `-seed.json`: three
`*-seed.json` globs (_has_spec_reentry_seed in _specify, /specify Phase 0.5,
and /plan's project-wide find-feature-artifacts) must not pick it up.

This module imports nothing from _specify, _research, _discover or any
helper: it is the shared substrate, so no helper depends on another.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

MARKER_FILENAME = "intake-rerun.json"
MARKER_VERSION = 1
SEED_FILENAME = "grill-seed.json"
INTAKE_SEED_STAGES = ("research", "discovery")

_SPEC_FILENAME = "spec.md"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    """Hex sha256 of the file's RAW bytes. Raises OSError on read failure."""
    return _sha256_bytes(Path(path).read_bytes())


def compose_marker(spec_sha256: str, seed_sha256: Optional[str]) -> Dict[str, Any]:
    """Build the marker record (pure; no I/O, no run-varying field)."""
    return {
        "marker_version": MARKER_VERSION,
        "seed_sha256": seed_sha256,
        "spec_sha256": spec_sha256,
    }


def _matching_seed_sha256(seed_path: Path, seed_target_stage: str) -> Optional[str]:
    """sha256 of seed_path's raw bytes iff it parses as a dict whose
    target_stage equals seed_target_stage; else None. Never raises."""
    try:
        raw = seed_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    # UnicodeDecodeError/JSONDecodeError are ValueErrors; deeply nested JSON
    # raises RecursionError (a RuntimeError).
    except (OSError, ValueError, RecursionError):
        return None
    if isinstance(parsed, dict) and parsed.get("target_stage") == seed_target_stage:
        return _sha256_bytes(raw)
    return None


def write_marker(feature_dir: Path, seed_target_stage: str) -> Optional[Path]:
    """Write feature_dir/intake-rerun.json; return its path, or None.

    Returns None and writes NOTHING when spec.md does not exist (OQ-4: arm (a)
    already admits that dir).  Uses .exists(), the same test cmd_find_handoffs
    applies for arm (a).  If spec.md exists but grill-seed.json is absent,
    unreadable, corrupt, or targets another stage, the marker is STILL written
    with the spec hash and a null seed hash.  The seed is read once and never
    modified.

    Output is deterministic (sorted keys, no timestamp): unchanged inputs give
    a byte-identical file.  The write is atomic (mkstemp in feature_dir +
    os.replace); the temp file is removed on failure and the OSError
    propagates.  ValueError if seed_target_stage is not in INTAKE_SEED_STAGES.
    """
    if seed_target_stage not in INTAKE_SEED_STAGES:
        raise ValueError(
            "seed_target_stage must be one of {0}, got {1!r}".format(
                INTAKE_SEED_STAGES, seed_target_stage
            )
        )
    feature_dir = Path(feature_dir)
    spec_path = feature_dir / _SPEC_FILENAME
    if not spec_path.exists():
        return None
    spec_sha = file_sha256(spec_path)
    seed_sha = _matching_seed_sha256(feature_dir / SEED_FILENAME, seed_target_stage)
    record = compose_marker(spec_sha, seed_sha)
    content = json.dumps(record, indent=2, sort_keys=True) + "\n"

    marker_path = feature_dir / MARKER_FILENAME
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-intake-rerun-", suffix=".json", dir=str(feature_dir)
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, str(marker_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return marker_path.resolve()


def _read_marker(feature_dir: Path) -> Optional[Dict[str, Any]]:
    """Marker as a dict, or None for absent/unreadable/corrupt/non-dict."""
    try:
        parsed = json.loads(
            (Path(feature_dir) / MARKER_FILENAME).read_text(encoding="utf-8")
        )
    except (OSError, ValueError, RecursionError):
        return None
    return parsed if isinstance(parsed, dict) else None


def marker_admits(feature_dir: Path) -> bool:
    """Arm (c)'s read: True iff the marker's spec_sha256 (a str) equals the
    current sha256 of spec.md, which must exist.

    READ-ONLY and never raises: a missing/corrupt/unreadable/non-dict marker,
    a non-str spec_sha256, or an absent/unreadable spec.md all give False.
    Matches on the spec_sha256 field only (marker_version is not required) --
    the same documented tolerance as _has_spec_reentry_seed: a record that
    is irregular on some OTHER field is irrelevant to this predicate, and
    re-validating the whole record would fail the pending-feature scan for
    reasons unrelated to re-entry routing.  Does NOT check for an intake
    handoff; that conjunction belongs to cmd_find_handoffs.
    """
    marker = _read_marker(feature_dir)
    if marker is None:
        return False
    recorded = marker.get("spec_sha256")
    if not isinstance(recorded, str):
        return False
    try:
        return file_sha256(Path(feature_dir) / _SPEC_FILENAME) == recorded
    except OSError:
        return False


def seed_consumed(seed_path: Path) -> bool:
    """D6's consumed-check read: True iff the marker beside seed_path records
    a seed_sha256 (str) equal to the sha256 of seed_path's CURRENT raw bytes.

    READ-ONLY and never raises: absent/corrupt/unreadable/non-dict marker, a
    null/absent/non-str seed_sha256, or an unreadable seed all give False
    ("not consumed").  Bound: a byte-identical rewrite of the seed reads as
    already consumed.
    """
    seed_path = Path(seed_path)
    marker = _read_marker(seed_path.parent)
    if marker is None:
        return False
    recorded = marker.get("seed_sha256")
    if not isinstance(recorded, str):
        return False
    try:
        return file_sha256(seed_path) == recorded
    except OSError:
        return False
