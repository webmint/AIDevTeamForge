"""Cross-record + filesystem validation at validate-time.

Field-level set-time validation lives in `_validation.py` (this name is
intentionally close — that module enforces type/format at the CLI
boundary, while THIS module enforces semantic invariants that span
multiple records and require filesystem access).

Whitespace normalization rules (applied to both the source-file slice
and the registered snippet before comparison):

- Strip trailing whitespace per line.
- Normalize CRLF -> LF.
- Strip leading and trailing fully-blank lines from BOTH sides.

These rules are deliberately permissive so an LLM that lifts a snippet
verbatim into the helper does not get rejected for a trailing-newline
or CRLF-vs-LF mismatch that has no semantic meaning.

Validation rules collected in `validate_package`:

1. Required fields populated (overview / directory_tree /
   primary_language).
2. At least one export.
3. At least one dependency.
4. Per-CodeBlock filesystem checks: cite.file exists + readable; line
   range within file bounds.
5. Per-CodeBlock snippet matches the cited line range verbatim modulo
   the whitespace rules above.
6. Internal Dependency target resolution (registered package OR
   on-disk directory).
7. Enum membership re-check (paranoia layer over set-time validation
   to catch state-file corruption).
8. No `[TODO` substring in the rendered skeleton — catches setters that
   were never called for required fields.

Errors are collected and returned as a list of dicts. The CLI handler
prints each on its own line and exits 2 if any errors. The pure
function `validate_package` returns the list so `render-package-doc`
can short-circuit when validation fails.

Stdlib only. Targets Python 3.8+.

Size note: at ~426 lines this module sits in the "plan-a-split" zone
(> 400) per the Design discipline threshold in `python-engineer.md`.
The cohesion case (all validation rules share the collect-errors
idiom and require filesystem + state access) was evaluated and
accepted. A meaningful future split would be `_validators_codeblock.py`
(filesystem + snippet checks) vs `_validators_semantic.py` (required
fields, deps, enums, todo-check). Split when this file approaches the
600-line hard threshold.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from generate_docs_schema import (
    DEPENDENCY_KINDS,
    EXPORT_KINDS,
    HAZARD_CATEGORIES,
)

from ._render import (
    REQUIRED_FIELD_TODO_MARKERS,
    _atomic_write_text,
    _project_root,
    render_package_skeleton,
)
from ._state import StateLoadError, _die, _load_state, _require_package


def _err(rule: str, field: str, message: str, **extra: Any) -> Dict[str, Any]:
    """Build a structured error dict with a stable shape."""
    out: Dict[str, Any] = {"rule": rule, "field": field, "message": message}
    out.update(extra)
    return out


def _check_required_fields(pkg: Dict[str, Any]) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    for fname, setter in (
        ("overview", "set-package-overview"),
        ("directory_tree", "set-package-tree"),
        ("primary_language", "set-package-language"),
    ):
        value = pkg.get(fname)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            errors.append(_err(
                "required-fields", fname,
                "PackageDoc.{0} is unset (call {1})".format(fname, setter),
            ))
    return errors


def _check_at_least_one_export(pkg: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not (pkg.get("exports") or []):
        return [_err(
            "exports-nonempty", "exports",
            "package has no registered exports; call add-package-export "
            "at least once",
        )]
    return []


def _check_at_least_one_dependency(pkg: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not (pkg.get("dependencies") or []):
        return [_err(
            "dependencies-nonempty", "dependencies",
            "package has no registered dependencies; call add-package-dep "
            "at least once",
        )]
    return []


def _normalize_for_compare(text: str) -> str:
    """Apply the whitespace normalization rules.

    See module docstring for the ruleset. Implemented here as a
    deterministic pure function so both sides of the comparison go
    through the same code path.
    """
    # Normalize CRLF -> LF (covers '\r\n' AND lone '\r' from old Macs).
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip per-line trailing whitespace.
    lines = [ln.rstrip() for ln in text.split("\n")]
    # Trim leading + trailing fully-blank lines.
    start = 0
    end = len(lines)
    while start < end and lines[start] == "":
        start += 1
    while end > start and lines[end - 1] == "":
        end -= 1
    return "\n".join(lines[start:end])


def _slice_snippet_diff(expected: str, actual: str) -> str:
    """Build a small diff fragment for a STALE snippet error.

    Truncated to ~5 lines per side so the error message stays readable
    when a long snippet drifts.
    """
    e_lines = expected.split("\n")[:5]
    a_lines = actual.split("\n")[:5]
    return (
        "expected (from source):\n  "
        + "\n  ".join(e_lines)
        + "\nactual (registered):\n  "
        + "\n  ".join(a_lines)
    )


def _check_codeblock(
    code: Dict[str, Any], field: str, project_root: Path,
) -> List[Dict[str, Any]]:
    """Filesystem + verbatim-match checks for a single CodeBlock dict."""
    cite = code.get("cite") or {}
    cite_file = cite.get("file")
    cite_start = cite.get("start")
    cite_end = cite.get("end")
    if not isinstance(cite_file, str) or cite_file.strip() == "":
        return [_err("cite-file-missing", field,
                     "{0}.cite.file is unset".format(field))]
    if not isinstance(cite_start, int) or not isinstance(cite_end, int):
        return [_err("cite-range-malformed", field,
                     "{0}.cite.start/end must be ints".format(field))]
    src_path = project_root / cite_file
    if not src_path.exists():
        return [_err("cite-file-not-found", field,
                     "{0}.cite.file {1!r} does not exist under project root "
                     "{2}".format(field, cite_file, project_root))]
    try:
        text = src_path.read_text(encoding="utf-8")
    except OSError as err:
        return [_err("cite-file-unreadable", field,
                     "{0}.cite.file {1!r} cannot be read: {2}".format(
                         field, cite_file, err))]
    file_lines = text.split("\n")
    # `split('\n')` produces N+1 items for files ending in '\n'.
    file_line_count = len(file_lines) - 1 if text.endswith("\n") else len(file_lines)
    if cite_end > file_line_count:
        return [_err("cite-range-out-of-bounds", field,
                     "{0}.cite.end ({1}) exceeds file line count ({2}) for "
                     "{3!r}".format(field, cite_end, file_line_count, cite_file))]
    expected_slice = "\n".join(file_lines[cite_start - 1:cite_end])
    expected_norm = _normalize_for_compare(expected_slice)
    actual_norm = _normalize_for_compare(code.get("snippet") or "")
    if expected_norm != actual_norm:
        return [_err("snippet-verbatim", field,
                     "{0}: snippet does not match {1}:{2}-{3}".format(
                         field, cite_file, cite_start, cite_end),
                     diff=_slice_snippet_diff(expected_norm, actual_norm))]
    return []


def _check_all_codeblocks(
    pkg: Dict[str, Any],
    project_root: Path,
) -> List[Dict[str, Any]]:
    """Run filesystem + verbatim-match checks across every CodeBlock in
    the record (exports, usage_example, consumer_pattern)."""
    errors: List[Dict[str, Any]] = []
    for idx, export in enumerate(pkg.get("exports") or []):
        code = export.get("code")
        if not isinstance(code, dict):
            errors.append(_err(
                "export-code-malformed", "exports[{0}].code".format(idx),
                "Export.code missing or not a dict",
            ))
            continue
        errors.extend(_check_codeblock(
            code, "exports[{0}].code".format(idx), project_root,
        ))
    if pkg.get("usage_example"):
        errors.extend(_check_codeblock(
            pkg["usage_example"], "usage_example", project_root,
        ))
    if pkg.get("consumer_pattern"):
        errors.extend(_check_codeblock(
            pkg["consumer_pattern"], "consumer_pattern", project_root,
        ))
    return errors


def _check_internal_deps(
    state: Dict[str, Any],
    pkg: Dict[str, Any],
    project_root: Path,
) -> List[Dict[str, Any]]:
    """Every internal dep must resolve to either another registered
    package OR an on-disk directory under the project root."""
    errors: List[Dict[str, Any]] = []
    registered_names = {
        rec.get("name") for rec in state.get("packages", {}).values()
    }
    registered_paths = set(state.get("packages", {}).keys())
    for idx, dep in enumerate(pkg.get("dependencies") or []):
        if dep.get("kind") != "internal":
            continue
        name = dep.get("name", "")
        # Try resolution as a registered package's name OR path.
        if name in registered_names or name in registered_paths:
            continue
        # Fall back to on-disk directory check.
        candidate = project_root / name
        if candidate.is_dir():
            continue
        errors.append(_err(
            "internal-dep-unresolved",
            "dependencies[{0}]".format(idx),
            "internal dependency {0!r} does not match any registered "
            "package name/path and no directory exists at {1}".format(
                name, candidate,
            ),
        ))
    return errors


def _check_enums(pkg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Re-verify enum membership for exports / dependencies / hazards.

    Field-level setters check this at boundary; we re-check at
    validate-time as a state-file-corruption guard.
    """
    errors: List[Dict[str, Any]] = []
    for idx, export in enumerate(pkg.get("exports") or []):
        kind = export.get("kind")
        if kind not in EXPORT_KINDS:
            errors.append(_err(
                "export-kind-invalid", "exports[{0}].kind".format(idx),
                "Export.kind {0!r} is not one of {1}".format(
                    kind, list(EXPORT_KINDS),
                ),
            ))
    for idx, dep in enumerate(pkg.get("dependencies") or []):
        kind = dep.get("kind")
        if kind not in DEPENDENCY_KINDS:
            errors.append(_err(
                "dep-kind-invalid", "dependencies[{0}].kind".format(idx),
                "Dependency.kind {0!r} is not one of {1}".format(
                    kind, list(DEPENDENCY_KINDS),
                ),
            ))
    for idx, hazard in enumerate(pkg.get("hazards") or []):
        category = hazard.get("category")
        if category not in HAZARD_CATEGORIES:
            errors.append(_err(
                "hazard-category-invalid",
                "hazards[{0}].category".format(idx),
                "Hazard.category {0!r} is not one of {1}".format(
                    category, list(HAZARD_CATEGORIES),
                ),
            ))
    return errors


def _check_no_todos(
    state: Dict[str, Any],
    package_path: str,
) -> List[Dict[str, Any]]:
    """Render the skeleton in-memory and assert no required-field
    `[TODO]` markers remain.

    Optional-section TODOs (scripts / hazards / usage_example /
    consumer_pattern) are deliberately ignored — those fields are
    schema-optional and a doc that omits them is still valid. Only
    markers from `REQUIRED_FIELD_TODO_MARKERS` (overview / directory
    tree / primary_language / exports / dependencies) gate the doc.
    """
    try:
        markdown = render_package_skeleton(state, package_path)
    except KeyError:
        # Package-existence check is the caller's job; don't
        # double-report.
        return []
    errors: List[Dict[str, Any]] = []
    for marker in REQUIRED_FIELD_TODO_MARKERS:
        if marker in markdown:
            errors.append(_err(
                "todo-marker-present", "rendered-skeleton",
                "rendered skeleton still contains a required-field [TODO] "
                "marker ({0!r}); one or more required setters has not "
                "been called".format(marker[:40]),
            ))
    return errors


def validate_package(
    state: Dict[str, Any],
    package_path: str,
    project_root: Path,
) -> List[Dict[str, Any]]:
    """Return a list of error dicts (empty list = valid).

    All rules run unconditionally; errors are collected so the LLM
    sees the full picture in one pass instead of fix-one-rerun-find-
    next loops.
    """
    pkg = _require_package(state, package_path)
    if pkg is None:
        return [_err(
            "package-not-registered", "package",
            "package not registered at {0!r}; run add-package first".format(
                package_path,
            ),
        )]
    errors: List[Dict[str, Any]] = []
    errors.extend(_check_required_fields(pkg))
    errors.extend(_check_at_least_one_export(pkg))
    errors.extend(_check_at_least_one_dependency(pkg))
    errors.extend(_check_all_codeblocks(pkg, project_root))
    errors.extend(_check_internal_deps(state, pkg, project_root))
    errors.extend(_check_enums(pkg))
    errors.extend(_check_no_todos(state, package_path))
    return errors


def _format_error_line(err: Dict[str, Any]) -> str:
    """Render one error dict as a plain-text line for the CLI."""
    parts = [
        "[{0}] {1}: {2}".format(
            err.get("rule", "?"),
            err.get("field", "?"),
            err.get("message", ""),
        ),
    ]
    if "diff" in err:
        parts.append("  " + err["diff"].replace("\n", "\n  "))
    return "\n".join(parts)


def _print_errors(errors: List[Dict[str, Any]]) -> None:
    for err in errors:
        sys.stderr.write(_format_error_line(err) + "\n")


def cmd_validate_package(args: argparse.Namespace) -> int:
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    errors = validate_package(state, args.path, _project_root())
    if not errors:
        return 0
    _print_errors(errors)
    return _die(
        "validate-package: {0} error(s) at {1}".format(
            len(errors), args.path,
        ),
    )


def cmd_render_package_doc(args: argparse.Namespace) -> int:
    """Render the FINAL doc to `docs/<path>/index.md`, gated by validate.

    Validation must pass with zero errors; on any error, the .md is
    NOT written and the existing .skeleton (if any) is retained. On
    success the .md is written atomically AND the .skeleton sibling
    is removed.
    """
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    if _require_package(state, args.path) is None:
        return _die(
            "package not registered at {0!r}; run add-package first".format(
                args.path,
            )
        )
    project_root = _project_root()
    errors = validate_package(state, args.path, project_root)
    if errors:
        _print_errors(errors)
        return _die(
            "render-package-doc: validation failed with {0} error(s) at "
            "{1}; .md NOT written".format(len(errors), args.path),
        )
    markdown = render_package_skeleton(state, args.path)
    out_path = project_root / "docs" / args.path / "index.md"
    try:
        _atomic_write_text(out_path, markdown)
    except OSError as err:
        return _die("cannot write {0}: {1}".format(out_path, err), code=1)
    skeleton_path = out_path.parent / "index.md.skeleton"
    if skeleton_path.exists():
        try:
            skeleton_path.unlink()
        except OSError as err:
            return _die(
                "wrote {0} but failed to remove stale {1}: {2}".format(
                    out_path, skeleton_path, err,
                ), code=1,
            )
    sys.stdout.write(str(out_path) + "\n")
    return 0
