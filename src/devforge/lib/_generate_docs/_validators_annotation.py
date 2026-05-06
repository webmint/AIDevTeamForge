"""Annotation-tier mechanical validation (Steps A.2 and A.4 of VALIDATOR-LOOP-PLAN.md).

Owns the annotation-level checks that run BEYOND set-time:
  - Schema validation (field types, shapes, content_hash format)
  - Banned-phrase detection in labels
  - Cite resolution (file missing, binary, range out-of-bounds, hash drift)
  - Specificity (sibling label collision within the same concern)

Also owns the post-batch aggregator `cmd_verify_annotations` (Step A.4) which
aggregates 5 metrics over all annotations in a concern and applies four hard
gates before the spec moves to validate-concern / render-concern-doc.

`cmd_validate_annotation` exit codes (locked in VALIDATOR-LOOP-PLAN.md Step A.2):
  0 — all checks pass
  2 — banned-phrase hit OR lookup failure (not registered)
  3 — cite unresolvable (missing / range out-of-bounds / hash drift)
  4 — specificity fail (sibling label collision in same concern)
  5 — schema invalid (missing required field / bad enum / malformed evidence)
  6 — cite-file is binary (NUL byte in first 8 KB)

`cmd_verify_annotations` exit codes (locked in VALIDATOR-LOOP-PLAN.md Step A.4):
  0 — all gates pass
  2 — at least one gate failed (stderr names which)
  5 — schema/state error (concern not registered, package not registered,
      or state-corrupt confidence value)

Gate thresholds (locked constants):
  BANNED_PHRASE_TOLERANCE = 0           — no tolerance
  AMBIGUOUS_RATE_THRESHOLD = 0.10       — ≤10% ambiguous annotations
  CROSS_CONCERN_DUPLICATE_RATE_THRESHOLD = 0.05 — ≤5% cross-concern label duplicates
  VACUOUS_PASS_TOLERANCE = 0            — no vacuous passes (tree set + zero annotations)

`sibling_collision_count` and `missing_cite_count` appear in the report but do
NOT have hard gates: validate-annotation gates these on the per-record path; if
any slipped through to verify-annotations, the report surfaces them but the
build proceeds.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from _banned_phrases import BANNED_PHRASES
from generate_docs_schema import ANNOTATION_CONFIDENCE_VALUES

from ._render import _project_root
from ._state import (
    StateLoadError,
    _die,
    _load_state,
    _require_concern,
    _require_package,
)


# ---------------------------------------------------------------------------
# Gate thresholds for cmd_verify_annotations (Step A.4).
# Locked constants — do NOT add CLI --threshold flags; callers cannot tune.
# ---------------------------------------------------------------------------

BANNED_PHRASE_TOLERANCE = 0           # 0 tolerated
AMBIGUOUS_RATE_THRESHOLD = 0.10       # ≤10%
CROSS_CONCERN_DUPLICATE_RATE_THRESHOLD = 0.05  # ≤5%
VACUOUS_PASS_TOLERANCE = 0            # non-empty tree + zero annotations → fail


# Regex for a valid sha256 hex digest: exactly 64 lowercase hex chars.
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def _check_annotation_schema(annotation: Dict[str, Any]) -> Optional[str]:
    """Return None on pass, or an error message describing the first bad field.

    Validates the full annotation record shape against the schema defined
    in _setters_annotation.py. Called by `cmd_validate_annotation` to
    gate all further checks — schema must pass before anything else runs.
    """
    if not isinstance(annotation, dict):
        return "annotation record must be a dict"

    # label: non-empty single-line string, no control chars (< 0x20 or DEL).
    label = annotation.get("label")
    if not isinstance(label, str) or label.strip() == "":
        return "label: must be a non-empty string"
    for ch in label:
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            return "label: contains control character (0x{0:02X})".format(code)

    # confidence: must be in ANNOTATION_CONFIDENCE_VALUES enum.
    confidence = annotation.get("confidence")
    if confidence not in ANNOTATION_CONFIDENCE_VALUES:
        return "confidence: must be one of {0}, got {1!r}".format(
            sorted(ANNOTATION_CONFIDENCE_VALUES), confidence,
        )

    # evidence: dict with file (str, non-empty), start (int >= 1), end (int >= start).
    evidence = annotation.get("evidence")
    if not isinstance(evidence, dict):
        return "evidence: must be a dict"
    ev_file = evidence.get("file")
    if not isinstance(ev_file, str) or ev_file.strip() == "":
        return "evidence.file: must be a non-empty string"
    ev_start = evidence.get("start")
    if not isinstance(ev_start, int) or isinstance(ev_start, bool):
        return "evidence.start: must be an int"
    if ev_start < 1:
        return "evidence.start: must be >= 1, got {0}".format(ev_start)
    ev_end = evidence.get("end")
    if not isinstance(ev_end, int) or isinstance(ev_end, bool):
        return "evidence.end: must be an int"
    if ev_end < ev_start:
        return "evidence.end: must be >= start ({0}), got {1}".format(
            ev_start, ev_end,
        )

    # model_version: non-empty single-line string.
    model_version = annotation.get("model_version")
    if not isinstance(model_version, str) or model_version.strip() == "":
        return "model_version: must be a non-empty string"

    # content_hash: exactly 64 lowercase hex chars (sha256).
    content_hash = annotation.get("content_hash")
    if not isinstance(content_hash, str):
        return "content_hash: must be a string"
    if not _SHA256_HEX_RE.match(content_hash):
        return (
            "content_hash: must be a 64-character lowercase hex string "
            "(sha256), got {0!r}".format(content_hash[:80])
        )

    return None


def _check_annotation_banned_phrase(label: str) -> Optional[str]:
    """Return the matched banned phrase token, or None if the label is clean.

    Whole-word, case-insensitive match. Multi-word phrases in BANNED_PHRASES
    (e.g. 'responsible for') are matched via re.escape so spaces and other
    metacharacters are treated as literals.
    """
    for phrase in BANNED_PHRASES:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, label, flags=re.IGNORECASE):
            return phrase
    return None


def _recompute_content_hash(path: Path, start: int, end: int) -> str:
    """Recompute sha256 of the inclusive 1-based line slice [start, end].

    Duplicates the exact semantics of `_setters_annotation._compute_content_hash`:
    read text with errors='replace', split via splitlines() (strips line
    endings, handles CRLF/CR/LF uniformly), join the slice with '\\n', then
    sha256.hexdigest(). Same input -> same hash as the setter.

    Raises ValueError when start or end exceeds the file's line count so the
    caller can distinguish range-out-of-bounds from hash-drift.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    file_lines = text.splitlines()
    line_count = len(file_lines)
    if start > line_count:
        raise ValueError(
            "cite_start {0} exceeds file line count {1}".format(start, line_count)
        )
    if end > line_count:
        raise ValueError(
            "cite_end {0} exceeds file line count {1}".format(end, line_count)
        )
    slice_lines = file_lines[start - 1:end]
    joined = "\n".join(slice_lines)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _check_annotation_cite_resolves(
    annotation: Dict[str, Any], project_root: Path,
) -> Optional[Tuple[str, str]]:
    """Return (subcase, message) on failure, or None on success.

    Subcases and order:
      'missing' — file does not exist (also used for unreadable)
      'binary'  — first 8 KB contains a NUL byte (checked before hash)
      'range'   — line range out of bounds
      'hash_drift' — content changed since annotation was recorded

    The binary check precedes range/hash recompute: no point hashing a
    binary file, and the error message is more actionable.
    """
    evidence = annotation.get("evidence") or {}
    cite_file = evidence.get("file", "")
    start = evidence.get("start")
    end = evidence.get("end")
    stored_hash = annotation.get("content_hash", "")

    cite_path = project_root / cite_file

    # Sub-case 1: file not found.
    if not cite_path.exists() or not cite_path.is_file():
        return ("missing", "cite-file not found: {0}".format(cite_file))

    # Sub-case 2: binary (NUL byte in first 8192 bytes).
    try:
        with cite_path.open("rb") as fh:
            head = fh.read(8192)
    except OSError as err:
        return (
            "missing",
            "cite-file not readable: {0}: {1}".format(cite_file, err),
        )
    if b"\x00" in head:
        return (
            "binary",
            "cite-file is binary (NUL byte in first 8KB): {0}".format(cite_file),
        )

    # Sub-cases 3 & 4 require reading + hashing.
    try:
        recomputed = _recompute_content_hash(cite_path, start, end)
    except ValueError as err:
        return ("range", str(err))
    except OSError as err:
        return (
            "missing",
            "cite-file not readable: {0}: {1}".format(cite_file, err),
        )

    # Sub-case 4: hash drift.
    if recomputed != stored_hash:
        return (
            "hash_drift",
            "content_hash mismatch: cite-file changed since annotation was "
            "recorded (expected {0} got {1})".format(stored_hash, recomputed),
        )

    return None


def _check_annotation_specificity(
    annotation: Dict[str, Any],
    target_path: str,
    concern: Dict[str, Any],
) -> Optional[str]:
    """Return a sibling target_path whose normalized label matches, or None.

    Normalization: lower() + strip(). The annotation under test
    (identified by target_path) is excluded from the sibling scan.
    """
    this_label = annotation.get("label", "").lower().strip()
    annotations = concern.get("annotations") or {}
    for sibling_path, sibling_ann in annotations.items():
        if sibling_path == target_path:
            continue
        if not isinstance(sibling_ann, dict):
            continue
        sibling_label = sibling_ann.get("label", "").lower().strip()
        if sibling_label == this_label:
            return sibling_path
    return None


def cmd_validate_annotation(args: argparse.Namespace) -> int:
    """Mechanical gate for one LLM-proposed annotation record.

    Loads state, resolves the annotation at
    state['packages'][pkg]['concerns'][concern]['annotations'][target_path],
    then runs five checks in order. First failure short-circuits; on
    all-pass returns 0.

    Exit codes: see module docstring.
    """
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)

    # Resolve package (exit 2 if absent).
    if _require_package(state, args.package) is None:
        return _die(
            "package not registered at {0!r}; run add-package first".format(
                args.package,
            ),
            code=2,
        )

    # Resolve concern (exit 2 if absent).
    concern = _require_concern(state, args.package, args.concern)
    if concern is None:
        return _die(
            "concern {0!r} not registered under {1!r}; run add-concern "
            "first".format(args.concern, args.package),
            code=2,
        )

    # Resolve annotation (exit 2 if absent).
    annotations = concern.get("annotations") or {}
    annotation = annotations.get(args.target_path)
    if annotation is None:
        return _die(
            "annotation not registered at target_path {0!r} in "
            "{1}/{2}; run add-annotation first".format(
                args.target_path, args.package, args.concern,
            ),
            code=2,
        )

    # Check 1 — Schema (exit 5).
    schema_err = _check_annotation_schema(annotation)
    if schema_err is not None:
        return _die(schema_err, code=5)

    # Check 2 — Banned phrase (exit 2).
    label = annotation.get("label", "")
    banned = _check_annotation_banned_phrase(label)
    if banned is not None:
        return _die(
            "label contains banned phrase: {0!r} in {1!r}".format(banned, label),
            code=2,
        )

    # Check 3 + 6 — Cite resolution (binary -> exit 6; all other -> exit 3).
    project_root = _project_root()
    cite_result = _check_annotation_cite_resolves(annotation, project_root)
    if cite_result is not None:
        subcase, msg = cite_result
        exit_code = 6 if subcase == "binary" else 3
        return _die(msg, code=exit_code)

    # Check 4 — Specificity (exit 4).
    sibling = _check_annotation_specificity(annotation, args.target_path, concern)
    if sibling is not None:
        return _die(
            "label collides with sibling: {0!r} has same label".format(sibling),
            code=4,
        )

    return 0


# ---------------------------------------------------------------------------
# Step A.4 — Post-batch aggregator: verify-annotations
# ---------------------------------------------------------------------------


def cmd_verify_annotations(args: argparse.Namespace) -> int:
    """Post-batch quality gate for all annotations in one concern.

    Aggregates 5 metrics over state['packages'][P]['concerns'][C]['annotations']
    and applies 4 hard gates. Failed gates are also named on stderr, one line each.

    Emits a structured JSON report to stdout on exit 0 (all gates pass) and exit 2
    (gate fail). Exit 5 (state error) emits only a stderr message via `_die` — no
    JSON, since there is no coherent report when state lookup fails or schema is
    corrupt.

    Exit codes:
      0 — all gates pass
      2 — at least one gate failed
      5 — schema/state error (package not registered, concern not registered,
          or state-corrupt confidence value in an annotation record)

    Gate thresholds are module-level locked constants; see BANNED_PHRASE_TOLERANCE,
    AMBIGUOUS_RATE_THRESHOLD, CROSS_CONCERN_DUPLICATE_RATE_THRESHOLD, VACUOUS_PASS_TOLERANCE.

    Metrics reported but NOT gated (diagnostic only — validate-annotation gates
    these on the per-record path; verify-annotations reports any that slipped through):
      - sibling_collision_count
      - missing_cite_count
    """
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=5)

    # Resolve package (exit 5 if absent — state error, not a lookup-miss).
    pkg = _require_package(state, args.package)
    if pkg is None:
        return _die(
            "package not registered: {0}".format(args.package), code=5,
        )

    # Resolve concern (exit 5 if absent).
    concern = _require_concern(state, args.package, args.concern)
    if concern is None:
        return _die(
            "concern not registered: {0}/{1}".format(args.package, args.concern),
            code=5,
        )

    # Annotations dict — tolerate missing key (legacy concern records from
    # before Step A.1 shipped have no "annotations" key).
    annotations = concern.get("annotations") or {}

    total = len(annotations)

    # --- Metric 1: banned_phrase_count ---
    banned_phrase_count = 0
    for ann in annotations.values():
        label = ann.get("label", "") if isinstance(ann, dict) else ""
        if _check_annotation_banned_phrase(label) is not None:
            banned_phrase_count += 1

    # --- Metric 2: sibling_collision_count ---
    # Count annotations whose normalized label collides with ANY other annotation
    # in the same concern, regardless of parent directory. Matches
    # _check_annotation_specificity semantics exactly (concern-scoped, not
    # directory-scoped). Each colliding annotation is counted once.
    sibling_collision_count = 0
    for target_path, ann in annotations.items():
        if not isinstance(ann, dict):
            continue
        this_label = ann.get("label", "").lower().strip()
        for sibling_path, sibling_ann in annotations.items():
            if sibling_path == target_path:
                continue
            if not isinstance(sibling_ann, dict):
                continue
            sibling_label = sibling_ann.get("label", "").lower().strip()
            if sibling_label == this_label:
                sibling_collision_count += 1
                break  # count each annotation at most once

    # --- Metric 3: missing_cite_count ---
    # File-exists pre-flight only (no hash recompute — that's validate-annotation).
    project_root = _project_root()
    missing_cite_count = 0
    for ann in annotations.values():
        if not isinstance(ann, dict):
            continue
        evidence = ann.get("evidence") or {}
        cite_file = evidence.get("file", "")
        if cite_file:
            cite_path = project_root / cite_file
            if not cite_path.exists() or not cite_path.is_file():
                missing_cite_count += 1

    # --- Metric 4: confidence_distribution ---
    # State-corrupt (unknown value) → exit 5.
    conf_dist = {"ambiguous": 0, "extracted": 0, "inferred": 0}
    for ann in annotations.values():
        if not isinstance(ann, dict):
            continue
        conf = ann.get("confidence")
        if conf not in ANNOTATION_CONFIDENCE_VALUES:
            return _die(
                "state-corrupt confidence value {0!r} in {1}/{2}; "
                "run add-annotation again".format(conf, args.package, args.concern),
                code=5,
            )
        conf_dist[conf] = conf_dist.get(conf, 0) + 1

    ambiguous_rate = conf_dist["ambiguous"] / total if total > 0 else 0.0

    # --- Metric 5: cross_concern_duplicate_count ---
    # Count annotations in concern C whose normalized label matches a label
    # in ANY OTHER concern of the SAME package. Cross-package comparison is
    # intentionally excluded — concerns are scoped per package.
    all_concerns = pkg.get("concerns") or {}
    other_labels = set()  # type: ignore[var-annotated]
    for other_concern_name, other_concern in all_concerns.items():
        if other_concern_name == args.concern:
            continue
        if not isinstance(other_concern, dict):
            continue
        other_annotations = other_concern.get("annotations") or {}
        for other_ann in other_annotations.values():
            if not isinstance(other_ann, dict):
                continue
            other_label = other_ann.get("label", "").lower().strip()
            if other_label:
                other_labels.add(other_label)

    cross_concern_duplicate_count = 0
    for ann in annotations.values():
        if not isinstance(ann, dict):
            continue
        label_norm = ann.get("label", "").lower().strip()
        if label_norm in other_labels:
            cross_concern_duplicate_count += 1

    cross_concern_duplicate_rate = (
        cross_concern_duplicate_count / total if total > 0 else 0.0
    )

    # --- Gate evaluation ---
    gate_banned = "pass" if banned_phrase_count == 0 else "fail"
    gate_ambiguous = (
        "pass" if ambiguous_rate <= AMBIGUOUS_RATE_THRESHOLD else "fail"
    )
    gate_cross = (
        "pass"
        if cross_concern_duplicate_rate <= CROSS_CONCERN_DUPLICATE_RATE_THRESHOLD
        else "fail"
    )

    # --- Gate: vacuous_pass ---
    # A concern with a non-empty directory_tree but zero annotations is a
    # vacuous pass: the orchestrator skipped the annotation loop entirely.
    # A concern with no tree set (None or empty string) is legitimately
    # empty — the vacuous_pass gate is "pass" in that case because the
    # concern may genuinely have no files to annotate yet.
    directory_tree = concern.get("directory_tree") or ""
    if directory_tree and total == 0:
        gate_vacuous = "fail"
    else:
        gate_vacuous = "pass"

    report = {
        "ambiguous_rate": ambiguous_rate,
        "banned_phrase_count": banned_phrase_count,
        "concern": args.concern,
        "confidence_distribution": conf_dist,
        "cross_concern_duplicate_count": cross_concern_duplicate_count,
        "cross_concern_duplicate_rate": cross_concern_duplicate_rate,
        "gates": {
            "ambiguous_rate": gate_ambiguous,
            "banned_phrase": gate_banned,
            "cross_concern_duplicate": gate_cross,
            "vacuous_pass": gate_vacuous,
        },
        "missing_cite_count": missing_cite_count,
        "package": args.package,
        "sibling_collision_count": sibling_collision_count,
        "total_annotations": total,
    }

    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")

    # Emit one stderr line per failed gate; collect all failures before exiting.
    any_fail = False

    if gate_banned == "fail":
        any_fail = True
        sys.stderr.write(
            "verify-annotations: banned_phrase gate FAIL: "
            "{0} annotation(s) contain banned phrases\n".format(banned_phrase_count)
        )

    if gate_ambiguous == "fail":
        any_fail = True
        pct = round(ambiguous_rate * 100, 1)
        sys.stderr.write(
            "verify-annotations: ambiguous_rate gate FAIL: "
            "{0}% (threshold: 10%)\n".format(pct)
        )

    if gate_cross == "fail":
        any_fail = True
        pct = round(cross_concern_duplicate_rate * 100, 1)
        sys.stderr.write(
            "verify-annotations: cross_concern_duplicate gate FAIL: "
            "{0}% (threshold: 5%)\n".format(pct)
        )

    if gate_vacuous == "fail":
        any_fail = True
        sys.stderr.write(
            "verify-annotations: vacuous_pass gate FAIL: "
            "concern has tree but zero annotations registered\n"
        )

    return 2 if any_fail else 0
