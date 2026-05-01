"""Concern-tier field setters (Phase 3.1).

Mirrors `_setters.py` shape for the ConcernDoc schema (see
`generate_docs_schema.ConcernDoc`). Each handler reads state, locates
the (package, concern) target, validates input field-by-field via
`_validation`, mutates the concern record, and writes state atomically
through `_state_transaction`.

Why a sibling module rather than appending to `_setters.py`: the prior
file sat at ~580 lines (in the documented "plan-a-split" zone, hard
threshold 600). Adding ~400 lines of concern-tier setters would push
it well past the threshold, so per its own splitting plan we land
concern-tier code here. Package-tier setters keep their home in
`_setters.py`; the two modules are siblings of equal status.

Idempotency policy mirrors the package tier:

- `add-concern` for an already-registered (package, concern_name) pair
  is rejected (exit 2).
- Single-field setters (`set-concern-overview`, `set-concern-tree`,
  `set-concern-usage-example`) ARE idempotent — latest value wins.
- Append-shaped setters (`add-concern-export`, `add-concern-type`,
  `add-concern-dep`, `add-concern-hazard`) reject duplicates by their
  natural key:
    - export: `(name, cite_file, cite_start)`
    - type:   `(cite_file, cite_start)`
    - dep:    `name`
    - hazard: `(category, description, cite_file, cite_start)`.

  Note: this hazard-dedup policy diverges INTENTIONALLY from package-tier
  `add-package-hazard`, which always appends (no dedup) — see
  `_setters.py` docstring. Concern-tier dedup was added because per-
  concern hazard lists tend to be smaller and an accidental
  re-invocation duplicates a single bullet visibly; package-tier hazard
  lists span the full package and treat repeated observations as
  separate findings. Two hazards with the same 4-tuple are dedup'd
  here; two with the same prose but different cites remain distinct.

Stdlib only. Targets Python 3.8+.
"""

import argparse
from typing import Any, Dict, List, Optional

from generate_docs_schema import (
    DEPENDENCY_KINDS,
    EXPORT_KINDS,
    HAZARD_CATEGORIES,
)

from ._state import (
    StateLoadError,
    _AbortTransaction,
    _die,
    _info,
    _require_concern,
    _require_package,
    _state_transaction,
    default_concern_record,
)
from ._validation import (
    _validate_in_enum,
    _validate_line_range,
    _validate_optional_string,
    _validate_string,
)


# ---------------------------------------------------------------------------
# Subcommand: add-concern.
# ---------------------------------------------------------------------------


def cmd_add_concern(args: argparse.Namespace) -> int:
    """Register a concern under a package. Idempotency: re-adding the
    same (package, concern_name) is rejected (exit 2)."""
    try:
        _validate_string(args.package, "add-concern --package")
        _validate_string(args.concern, "add-concern --concern")
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.package)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.package)
                ))
            # Phase 3.1 migration: defensive backfill for any in-memory
            # state that hasn't gone through `_load_state` yet.
            if "concerns" not in pkg or pkg["concerns"] is None:
                pkg["concerns"] = {}
            if args.concern in pkg["concerns"]:
                raise _AbortTransaction(_die(
                    "concern {0!r} already registered under {1}; use a "
                    "different name or reset".format(
                        args.concern, args.package,
                    )
                ))
            pkg["concerns"][args.concern] = default_concern_record(args.concern)
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info("add-concern {0} under {1}".format(args.concern, args.package))
    return 0


# ---------------------------------------------------------------------------
# Per-concern scalar setters.
# ---------------------------------------------------------------------------


def _set_concern_scalar(
    args: argparse.Namespace,
    field_name: str,
    field_label: str,
    multiline: bool,
) -> int:
    """Common path for scalar concern setters (overview, directory_tree).

    Both fields are required (no optional/empty-clears variant — the
    schema declares them required). Multi-line is `True` for both.
    """
    try:
        _validate_string(args.text, field_label, multiline=multiline)
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.package)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.package)
                ))
            concerns = pkg.get("concerns") or {}
            concern = concerns.get(args.concern)
            if concern is None:
                raise _AbortTransaction(_die(
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            concern[field_name] = args.text
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "{0} {1}/{2} ({3} chars)".format(
            field_label.split(" ")[0], args.package, args.concern,
            len(args.text),
        )
    )
    return 0


def cmd_set_concern_overview(args: argparse.Namespace) -> int:
    return _set_concern_scalar(
        args, "overview", "set-concern-overview --text", multiline=True,
    )


def cmd_set_concern_tree(args: argparse.Namespace) -> int:
    return _set_concern_scalar(
        args, "directory_tree", "set-concern-tree --text", multiline=True,
    )


# ---------------------------------------------------------------------------
# Subcommand: add-concern-export.
# ---------------------------------------------------------------------------


def cmd_add_concern_export(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.package, "add-concern-export --package")
        _validate_string(args.concern, "add-concern-export --concern")
        _validate_string(args.name, "add-concern-export --name")
        _validate_string(args.kind, "add-concern-export --kind")
        _validate_in_enum(
            args.kind, EXPORT_KINDS, "add-concern-export --kind",
        )
        signature = _validate_optional_string(
            args.signature, "add-concern-export --signature"
        )
        _validate_string(
            args.description, "add-concern-export --description",
            multiline=True,
        )
        _validate_string(args.language, "add-concern-export --language")
        _validate_string(
            args.code_snippet, "add-concern-export --code-snippet",
            multiline=True,
        )
        _validate_string(args.cite_file, "add-concern-export --cite-file")
        _validate_line_range(
            args.cite_start, args.cite_end, "add-concern-export cite",
        )
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            concern = _require_concern(state, args.package, args.concern)
            if concern is None:
                # Distinguish package-missing vs concern-missing for the
                # operator — same dual-message strategy as the scalar
                # setters above.
                if _require_package(state, args.package) is None:
                    raise _AbortTransaction(_die(
                        "package not registered at {0!r}; run add-package "
                        "first".format(args.package)
                    ))
                raise _AbortTransaction(_die(
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            for existing in concern["public_surface"]:
                if (
                    existing["name"] == args.name
                    and existing["code"]["cite"]["file"] == args.cite_file
                    and existing["code"]["cite"]["start"] == args.cite_start
                ):
                    raise _AbortTransaction(_die(
                        "export {0!r} at {1}:{2} already registered under "
                        "{3}/{4}; use a different name or different "
                        "cite".format(
                            args.name, args.cite_file, args.cite_start,
                            args.package, args.concern,
                        )
                    ))
            concern["public_surface"].append(
                {
                    "name": args.name,
                    "kind": args.kind,
                    "signature": signature,
                    "description": args.description,
                    "code": {
                        "language": args.language,
                        "snippet": args.code_snippet,
                        "cite": {
                            "file": args.cite_file,
                            "start": args.cite_start,
                            "end": args.cite_end,
                        },
                    },
                }
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "add-concern-export {0} under {1}/{2} (cite={3}:{4}-{5})".format(
            args.name, args.package, args.concern,
            args.cite_file, args.cite_start, args.cite_end,
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: add-concern-type.
#
# Concern-tier types are bare CodeBlocks (per schema:
# `ConcernDoc.types: List[CodeBlock]`) — no name/kind/signature like
# Export. Dedup by `(cite_file, cite_start)` — there is no `name` to
# include in the natural key.
# ---------------------------------------------------------------------------


def cmd_add_concern_type(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.package, "add-concern-type --package")
        _validate_string(args.concern, "add-concern-type --concern")
        _validate_string(args.language, "add-concern-type --language")
        _validate_string(
            args.code_snippet, "add-concern-type --code-snippet",
            multiline=True,
        )
        _validate_string(args.cite_file, "add-concern-type --cite-file")
        _validate_line_range(
            args.cite_start, args.cite_end, "add-concern-type cite",
        )
    except ValueError as err:
        return _die(str(err))
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
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            for existing in concern["types"]:
                cite = existing.get("cite") or {}
                if (
                    cite.get("file") == args.cite_file
                    and cite.get("start") == args.cite_start
                ):
                    raise _AbortTransaction(_die(
                        "type at {0}:{1} already registered under {2}/{3}; "
                        "use a different cite".format(
                            args.cite_file, args.cite_start,
                            args.package, args.concern,
                        )
                    ))
            concern["types"].append(
                {
                    "language": args.language,
                    "snippet": args.code_snippet,
                    "cite": {
                        "file": args.cite_file,
                        "start": args.cite_start,
                        "end": args.cite_end,
                    },
                }
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "add-concern-type under {0}/{1} (cite={2}:{3}-{4})".format(
            args.package, args.concern,
            args.cite_file, args.cite_start, args.cite_end,
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: add-concern-dep.
# ---------------------------------------------------------------------------


def cmd_add_concern_dep(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.package, "add-concern-dep --package")
        _validate_string(args.concern, "add-concern-dep --concern")
        _validate_string(args.name, "add-concern-dep --name")
        _validate_string(args.kind, "add-concern-dep --kind")
        _validate_in_enum(
            args.kind, DEPENDENCY_KINDS, "add-concern-dep --kind",
        )
        version = _validate_optional_string(
            args.version, "add-concern-dep --version"
        )
        _validate_string(
            args.purpose, "add-concern-dep --purpose", multiline=True,
        )
        consumer_locations: List[str] = []
        for idx, loc in enumerate(args.consumer_location or []):
            _validate_string(
                loc,
                "add-concern-dep --consumer-location[{0}]".format(idx),
            )
            consumer_locations.append(loc)
    except ValueError as err:
        return _die(str(err))
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
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            for existing in concern["dependencies"]:
                if existing["name"] == args.name:
                    raise _AbortTransaction(_die(
                        "dependency {0!r} already registered under {1}/{2}; "
                        "use a different name or reset".format(
                            args.name, args.package, args.concern,
                        )
                    ))
            concern["dependencies"].append(
                {
                    "name": args.name,
                    "kind": args.kind,
                    "version": version,
                    "purpose": args.purpose,
                    "consumer_locations": consumer_locations,
                }
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "add-concern-dep {0} under {1}/{2} (kind={3})".format(
            args.name, args.package, args.concern, args.kind,
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: add-concern-hazard.
# ---------------------------------------------------------------------------


def cmd_add_concern_hazard(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.package, "add-concern-hazard --package")
        _validate_string(args.concern, "add-concern-hazard --concern")
        _validate_string(args.category, "add-concern-hazard --category")
        _validate_in_enum(
            args.category, HAZARD_CATEGORIES,
            "add-concern-hazard --category",
        )
        _validate_string(
            args.description, "add-concern-hazard --description",
            multiline=True,
        )
    except ValueError as err:
        return _die(str(err))
    cite_present = (
        args.cite_file is not None
        or args.cite_start is not None
        or args.cite_end is not None
    )
    cite_complete = (
        args.cite_file is not None
        and args.cite_start is not None
        and args.cite_end is not None
    )
    if cite_present and not cite_complete:
        return _die(
            "hazard cite requires --cite-file + --cite-start + --cite-end "
            "together, or none"
        )
    cite: Optional[Dict[str, Any]] = None
    if cite_complete:
        try:
            _validate_string(
                args.cite_file, "add-concern-hazard --cite-file"
            )
            _validate_line_range(
                args.cite_start, args.cite_end, "add-concern-hazard cite"
            )
        except ValueError as err:
            return _die(str(err))
        cite = {
            "file": args.cite_file,
            "start": args.cite_start,
            "end": args.cite_end,
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
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            # Dedup natural key: (category, description, cite-file,
            # cite-start). Same-prose hazards with different cites are
            # treated as distinct observations (matches the package-tier
            # philosophy that a hazard's identity includes WHERE it was
            # observed, not just what it says).
            cite_file = cite["file"] if cite else None
            cite_start = cite["start"] if cite else None
            for existing in concern["hazards"]:
                ex_cite = existing.get("cite") or {}
                ex_file = ex_cite.get("file") if existing.get("cite") else None
                ex_start = ex_cite.get("start") if existing.get("cite") else None
                if (
                    existing["category"] == args.category
                    and existing["description"] == args.description
                    and ex_file == cite_file
                    and ex_start == cite_start
                ):
                    raise _AbortTransaction(_die(
                        "hazard ({0!r}, same description, same cite) already "
                        "registered under {1}/{2}".format(
                            args.category, args.package, args.concern,
                        )
                    ))
            concern["hazards"].append(
                {
                    "category": args.category,
                    "description": args.description,
                    "cite": cite,
                }
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "add-concern-hazard {0} under {1}/{2}".format(
            args.category, args.package, args.concern,
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: set-concern-usage-example.
# ---------------------------------------------------------------------------


def cmd_set_concern_usage_example(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.package, "set-concern-usage-example --package")
        _validate_string(args.concern, "set-concern-usage-example --concern")
        _validate_string(
            args.language, "set-concern-usage-example --language",
        )
        _validate_string(
            args.code_snippet,
            "set-concern-usage-example --code-snippet",
            multiline=True,
        )
        _validate_string(
            args.cite_file, "set-concern-usage-example --cite-file",
        )
        _validate_line_range(
            args.cite_start, args.cite_end,
            "set-concern-usage-example cite",
        )
    except ValueError as err:
        return _die(str(err))
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
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            concern["usage_example"] = {
                "language": args.language,
                "snippet": args.code_snippet,
                "cite": {
                    "file": args.cite_file,
                    "start": args.cite_start,
                    "end": args.cite_end,
                },
            }
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "set-concern-usage-example under {0}/{1} (cite={2}:{3}-{4})".format(
            args.package, args.concern,
            args.cite_file, args.cite_start, args.cite_end,
        )
    )
    return 0
