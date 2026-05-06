"""Annotation setter for the concern tier (Step A.1 of VALIDATOR-LOOP-PLAN.md).

`add-annotation` records one LLM-proposed annotation of a file-path
entry inside a concern.  The helper owns the annotation record shape;
the LLM supplies only the values.  A single annotation per
`(concern, target_path)` is stored — re-invoking at the same target
replaces the prior record so a failed/revised annotation does not
accumulate a list.

Annotation record shape (enforced here at write-time):

    {
        "label":         str,  # required, single-line, non-empty, no ctrl chars
        "confidence":    str,  # required, enum: extracted|inferred|ambiguous
        "evidence": {
            "file":      str,  # required, single-line, non-empty
            "start":     int,  # required, >= 1
            "end":       int,  # required, >= start
        },
        "model_version": str,  # required, single-line (e.g. "claude-haiku-4-5-…")
        "content_hash":  str,  # COMPUTED from cite-file slice (sha256 hex)
    }

The content_hash is computed by slicing lines [cite_start-1 : cite_end]
(1-based inclusive) from the cite-file, joining them with newlines, and
computing sha256.hexdigest().  If the cite-file is unreadable the
setter aborts with exit 2.

File resolution: cite-file is resolved via `_render._project_root()`,
which is the single source of truth for project-root resolution:
  1. `DEVFORGE_PROJECT_ROOT` env var (test override)
  2. `DEVFORGE_DIR` env var's parent (production: `DEVFORGE_DIR` is
     always set when the helper is invoked; its parent is the project root)
  3. `cwd()` (last resort)

Using the same function as the validator ensures the hash computed here
and the hash recomputed by `validate-annotation` are always based on
the same project root, regardless of which env vars are set.

Stdlib only.  Targets Python 3.8+.
"""

import argparse
import hashlib
from pathlib import Path
from typing import Any, Dict

from generate_docs_schema import ANNOTATION_CONFIDENCE_VALUES

from ._render import _project_root
from ._state import (
    StateLoadError,
    _AbortTransaction,
    _die,
    _info,
    _require_concern,
    _require_package,
    _state_transaction,
)
from ._validation import (
    _validate_in_enum,
    _validate_line_range,
    _validate_string,
)


def _compute_content_hash(path: Path, start: int, end: int) -> str:
    """Return sha256 hex of the inclusive 1-based line slice [start, end].

    Lines are joined with '\\n' (not the raw line endings) so the hash
    is CRLF-agnostic — the same source file with either line ending
    produces the same hash.  Individual line trailing whitespace is
    preserved verbatim so the hash captures the exact content within
    the slice boundary.

    Raises ValueError when `start` or `end` exceeds the file's line
    count so the caller never silently hashes an empty or truncated
    slice — which would produce a meaningless constant hash.

    Binary files are read with `errors="replace"`; their content_hash
    reflects replacement characters, not raw bytes.  The set-time gate
    accepts this.  The validate-time gate (Step A.2) is responsible for
    rejecting annotations whose cite-file is non-text.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    # `splitlines()` splits on \\n, \\r\\n, \\r and strips the ending,
    # which is the correct semantic: lines[start-1:end] matches line
    # numbers as reported by editors and as accepted by cite_start/end.
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


def cmd_add_annotation(args: argparse.Namespace) -> int:
    """Record one annotation of a tree entry inside a concern.

    All inputs are validated at the CLI boundary before state is
    touched.  The cite-file must be readable; its sha256 slice is
    computed and stored as `content_hash`.  An existing annotation at
    the same `target_path` is silently replaced (overwrite semantics).
    """
    # --- Boundary validation ---
    try:
        _validate_string(args.package, "add-annotation --package")
        _validate_string(args.concern, "add-annotation --concern")
        _validate_string(args.target_path, "add-annotation --target-path")
        _validate_string(args.label, "add-annotation --label")
        _validate_in_enum(
            args.confidence, ANNOTATION_CONFIDENCE_VALUES, "add-annotation --confidence",
        )
        _validate_string(args.cite_file, "add-annotation --cite-file")
        _validate_line_range(
            args.cite_start, args.cite_end, "add-annotation cite",
        )
        _validate_string(args.model_version, "add-annotation --model-version")
    except ValueError as err:
        return _die(str(err))

    # --- Cite-file access and hash computation (before state lock) ---
    cite_path = _project_root() / args.cite_file
    if not cite_path.exists() or not cite_path.is_file():
        return _die(
            "cite-file not readable: {0}".format(args.cite_file), code=2
        )
    try:
        content_hash = _compute_content_hash(
            cite_path, args.cite_start, args.cite_end,
        )
    except (OSError, ValueError) as err:
        return _die(
            "cite-file not readable: {0}: {1}".format(args.cite_file, err),
            code=2,
        )

    # --- State transaction ---
    annotation: Dict[str, Any] = {
        "label": args.label,
        "confidence": args.confidence,
        "evidence": {
            "file": args.cite_file,
            "start": args.cite_start,
            "end": args.cite_end,
        },
        "model_version": args.model_version,
        "content_hash": content_hash,
    }
    try:
        with _state_transaction() as state:
            concern = _require_concern(state, args.package, args.concern)
            if concern is None:
                if _require_package(state, args.package) is None:
                    raise _AbortTransaction(_die(
                        "package not registered at {0!r}; run add-package "
                        "first".format(args.package)
                    ))
                raise _AbortTransaction(_die(
                    "concern not registered: {0}/{1}; run add-concern "
                    "first".format(args.package, args.concern)
                ))
            # Backfill for any concern records that predate Step A.1.
            if "annotations" not in concern or concern["annotations"] is None:
                concern["annotations"] = {}
            # Overwrite semantics: latest call at the same target_path wins.
            concern["annotations"][args.target_path] = annotation
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)

    _info(
        "annotation recorded: {0}/{1} -> {2}".format(
            args.package, args.concern, args.target_path,
        )
    )
    return 0
