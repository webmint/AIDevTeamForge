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
6. Internal Dependency target resolution (registered package, on-disk
   directory under project_root, OR `packages_detected[].path` entry
   in `<devforge>/init.yaml` matched by basename or full path).
7. Enum membership re-check (paranoia layer over set-time validation
   to catch state-file corruption).
8. No `[TODO` substring in the rendered skeleton — catches setters that
   were never called for required fields.

Errors are collected and returned as a list of dicts. The CLI handler
prints each on its own line and exits 2 if any errors. The pure
function `validate_package` returns the list so `render-package-doc`
can short-circuit when validation fails.

Stdlib only. Targets Python 3.8+.

Size note: at ~1020 lines (Phase 3.1 added concern-tier validation +
the decomposition gate) this module is well past the 600-line hard
threshold per the Design discipline guideline in `python-engineer.md`.
The cohesion case (all validation rules share the collect-errors
idiom and require filesystem + state access) was evaluated and
accepted. The init-yaml-consuming third resolution path
(`_load_packages_detected_paths` + `_resolve_internal_dep`) added in
2026-04 keeps the surface in this single module rather than fanning
out into per-rule files prematurely. The Phase 3.1 concern validators
(`_check_concern_*`) and the decomposition gate (`_check_decomposition`)
share `_check_codeblock` + the `_err` shape with the package-tier
checks, so splitting now would force the shared helpers up to a third
shared module without payoff.

Planned future split (deferred): `_validators_shared.py`
(`_check_codeblock` + `_err` shape + cross-tier helpers) +
`_validators_package.py` (package-only rules) +
`_validators_concern.py` (concern-only rules) +
`_validators_decomposition.py` (the gate's filesystem walk +
allowlist). Concrete trigger: any new validation rule set landing in
Phase 3.2+ that pushes this module past 1100 lines is the hard
split-point — at that line count the cohesion case no longer
outweighs the navigation cost. Do not let "the cohesion case still
holds" defer the split a third time past 1100; the trigger is
mechanical.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from generate_docs_schema import (
    DEPENDENCY_KINDS,
    EXPORT_KINDS,
    HAZARD_CATEGORIES,
)

from ._render import (
    CONCERN_OPTIONAL_SECTION_MARKERS,
    CONCERN_REQUIRED_FIELD_TODO_MARKERS,
    OPTIONAL_SECTION_MARKERS,
    REQUIRED_FIELD_TODO_MARKERS,
    _atomic_write_text,
    _project_root,
    render_concern_skeleton,
    render_package_skeleton,
)
from ._state import (
    StateLoadError,
    _die,
    _load_state,
    _require_concern,
    _require_package,
    _state_file_path,
)


# ---------------------------------------------------------------------------
# Decomposition gate (Phase 3.1).
#
# A package is "decomposed" if every substantive subfolder under
# `<package_path>/src/` is registered as a concern. The gate walks the
# top-level subfolders only (no recursion) and compares against
# `pkg["concerns"]`. Substantive = ≥2 files OR a known architectural-
# role basename. Trivial leaves (assets, dist, etc.) are skipped
# unconditionally.
#
# These lists are intentionally small KISS extension points. Match by
# basename (folder name), not by detected language — a Java project
# with a `services/` folder gets the same treatment as a Python project
# with `services/`. Add to the lists on evidence; do not preemptively
# expand.
# ---------------------------------------------------------------------------


_ARCH_ROLE_FOLDER_NAMES: Tuple = (
    # JS/TS
    "components", "composables", "services", "routing", "router",
    "stores", "plugins", "helpers", "hooks",
    # Python
    "handlers", "models", "repositories", "views", "serializers",
    # Go
    "middleware", "repository", "service",
    # Rust
    "traits",
    # Java/Kotlin
    "controllers", "entities",
)


_TRIVIAL_LEAF_FOLDER_NAMES: Tuple = (
    "assets", "static", "node_modules", "__pycache__", "target", "dist",
    "build", "vendor", "locales", "i18n", "fixtures", "__tests__",
    "test", "tests",
)


def _is_substantive_subfolder(subdir: Path) -> bool:
    """Return True if `subdir` qualifies as a substantive subfolder.

    Rules (in order):
    1. Trivial-leaf basename -> always-skip (return False even if
       file count would otherwise qualify).
    2. Architectural-role basename -> always-substantive (return True
       even when the folder contains a single file — e.g., a `services/`
       directory holding one service file is still architecturally
       meaningful).
    3. Otherwise: substantive iff direct child file count is ≥ 2.

    File count walks only direct children (top-level) — sub-files inside
    nested subdirectories don't count. This keeps the gate's behavior
    predictable: a folder with one file plus several deep subfolders
    would NOT register as substantive without the role-name override,
    matching the operator's mental model that "≥2 files in this folder"
    means an architectural cluster.
    """
    name = subdir.name
    if name in _TRIVIAL_LEAF_FOLDER_NAMES:
        return False
    if name in _ARCH_ROLE_FOLDER_NAMES:
        return True
    try:
        entries = [p for p in subdir.iterdir() if p.is_file()]
    except OSError:
        # Permission errors are surfaced indirectly: an unreadable
        # subfolder cannot be substantive (we have no signal). The
        # operator can intervene if needed.
        return False
    return len(entries) >= 2


def _scan_substantive_subfolders(src_dir: Path) -> List[str]:
    """Return sorted basenames of substantive subfolders under `src_dir`.

    No recursion — only top-level. Stable sort so error messages are
    deterministic. Returns `[]` when `src_dir` doesn't exist (the
    decomposition gate becomes a no-op for flat-layout packages).
    """
    if not src_dir.is_dir():
        return []
    found: List[str] = []
    try:
        children = sorted(src_dir.iterdir(), key=lambda p: p.name)
    except OSError:
        return []
    for child in children:
        if not child.is_dir():
            continue
        if _is_substantive_subfolder(child):
            found.append(child.name)
    return found


def _check_decomposition(
    pkg: Dict[str, Any],
    package_path: str,
    project_root: Path,
) -> List[Dict[str, Any]]:
    """Verify registered concerns cover every substantive subfolder.

    No-op when `<project_root>/<package_path>/src/` doesn't exist (some
    ecosystems use a flat package layout). When `src/` exists, every
    substantive top-level subfolder must be registered as a concern.

    The gate emits one error record per missing concern (no truncation —
    LLMs need the full list to fix in one pass).
    """
    src_dir = project_root / package_path / "src"
    substantive = _scan_substantive_subfolders(src_dir)
    if not substantive:
        return []
    registered = set((pkg.get("concerns") or {}).keys())
    errors: List[Dict[str, Any]] = []
    for subfolder in substantive:
        if subfolder in registered:
            continue
        # Include the subfolder name in the message text AND as a
        # structured `subfolder` extra. The CLI's text output (consumed
        # by the LLM running /generate-docs) renders the message text
        # only — keeping the name in the message keeps it visible at
        # the prompt without forcing the consumer to parse a JSON tail.
        errors.append(_err(
            "decomposition", "concerns",
            "missing concern for substantive subfolder {0!r} under "
            "{1}/src/; run add-concern --package {1} --concern "
            "{0}".format(subfolder, package_path),
            subfolder=subfolder,
        ))
    return errors


# Name of the bootstrap artifact written by /init-forge. Living next to
# the helper's own state file under `<devforge>/`. Read-only here — this
# module never writes to init.yaml; init_helper owns that artifact's shape.
INIT_YAML_FILE_NAME = "init.yaml"


# Regex-based path extractor for init.yaml's `packages_detected[]` block.
# Matches any line that looks like `  - path: <value>` regardless of
# indentation depth. Closed shape produced by init_helper's emitter
# always uses 2-space indentation, so this matches in practice; the
# regex is intentionally permissive on indentation so a future emit-
# style tweak (e.g., 4-space) does not silently break resolution.
#
# We deliberately do NOT parse the full YAML. Stdlib has no YAML
# parser and pulling init_helper's parser in would create a circular
# import and an unwanted coupling between the validator and a different
# helper's full schema. Best-effort path extraction is the contract:
# any malformed input simply yields an empty list, callers fall back
# to the existing checks (registered packages + on-disk directory).
_PACKAGES_DETECTED_PATH_RE = re.compile(
    r"^\s*-\s*path:\s*(.+?)\s*$", re.MULTILINE
)


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
    the record (exports, usage_example, consumer_pattern).

    Optional CodeBlock fields (`usage_example`, `consumer_pattern`) are
    treated as "absent" only when the stored value is `None` (the schema
    default). A non-None value of any other shape is a corrupted record
    and surfaces an explicit `*-malformed` error instead of being
    silently skipped (anti-pattern #2: validation must NOT defer).
    """
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
    for field_name in ("usage_example", "consumer_pattern"):
        value = pkg.get(field_name)
        if value is None:
            continue
        if not isinstance(value, dict) or not value:
            errors.append(_err(
                "{0}-malformed".format(field_name.replace("_", "-")),
                field_name,
                "{0} is set but is not a non-empty dict (got {1!r})".format(
                    field_name, value,
                ),
            ))
            continue
        errors.extend(_check_codeblock(value, field_name, project_root))
    return errors


def _load_packages_detected_paths(devforge_dir: Path) -> List[str]:
    """Extract `packages_detected[].path` strings from init.yaml.

    Best-effort, regex-based. Returns `[]` when the file is missing,
    unreadable, or contains no recognizable `- path: <value>` lines.
    No exception is propagated to the caller — internal-dep resolution
    is a fall-back chain and a missing init.yaml is a normal state for
    standalone projects that never ran /init-forge.

    Why regex (not the init_helper YAML parser): pulling init_helper's
    parser into the validator would create a cross-helper coupling
    that is much heavier than the single check we need. The init.yaml
    shape is locked (init_helper owns it; emitter is deterministic),
    so a 1-line regex is safe in practice — and any input outside the
    closed shape simply yields `[]`, which falls through to the
    existing resolution checks.
    """
    init_path = devforge_dir / INIT_YAML_FILE_NAME
    if not init_path.exists():
        return []
    try:
        text = init_path.read_text(encoding="utf-8")
    except OSError:
        return []
    paths: List[str] = []
    for match in _PACKAGES_DETECTED_PATH_RE.finditer(text):
        raw = match.group(1).strip()
        if not raw:
            continue
        # Defensive: strip surrounding double-quotes if init_helper
        # had to quote the path (e.g., a path containing a special
        # char). The emitter only quotes when `_needs_quoting` returns
        # True, but the validator should accept either form. When the
        # value is double-quoted, the comment-stripping pass below is
        # skipped — `#` inside a double-quoted YAML string is a literal
        # character, not a comment introducer.
        if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
            raw = raw[1:-1]
        else:
            # Strip an unquoted YAML inline comment: `path/x # note`
            # -> `path/x`. The space-before-`#` rule is the YAML
            # convention; a bare `#` immediately after content is NOT
            # a comment in YAML. Skipping comment-strip when no leading
            # space exists keeps legitimate paths like `foo#bar`
            # (rare but legal) intact.
            comment_idx = raw.find(" #")
            if comment_idx >= 0:
                raw = raw[:comment_idx].rstrip()
        if not raw:
            continue
        paths.append(raw)
    return paths


def _resolve_internal_dep(
    dep_name: str,
    state: Dict[str, Any],
    project_root: Path,
    devforge_dir: Path,
) -> bool:
    """Return True if the internal dep name resolves via any of three
    checks; False otherwise.

    Resolution order (first match wins):

    1. Another registered package's `name` OR `path` (current state).
    2. A directory at `<project_root>/<dep_name>`.
    3. A `packages_detected[].path` entry in `<devforge>/init.yaml`,
       matched as either the full path string OR its basename.

    The third check exists for monorepos where /init-forge populated
    init.yaml with all package paths but the LLM is documenting only
    one package at a time — sibling packages aren't yet registered in
    current state, and the on-disk dir is nested below project_root
    inside a workspace folder rather than directly at
    `<project_root>/<dep_name>`. testForge20's
    `db-cse-ui-strata/packages/pkg-cse-core` shape was the concrete
    case that motivated this check.
    """
    # Check 1: registered packages in current state.
    registered_names = {
        rec.get("name") for rec in state.get("packages", {}).values()
    }
    registered_paths = set(state.get("packages", {}).keys())
    if dep_name in registered_names or dep_name in registered_paths:
        return True
    # Check 2: directory at project_root/dep_name.
    candidate = project_root / dep_name
    if candidate.is_dir():
        return True
    # Check 3: init.yaml's packages_detected[].path. Match basename
    # (covers the common case: dep is the bare package name) AND the
    # full path string (covers the case where the dep was registered
    # using its workspace-relative path verbatim).
    for path in _load_packages_detected_paths(devforge_dir):
        if path == dep_name:
            return True
        # Path-style basename: split on either `/` or `\` for safety.
        # An absolute path (defensive — init_helper rejects them at
        # set-time but parser-tolerant matching is cheap) has its
        # leading slash stripped before basename extraction.
        stripped = path.lstrip("/\\")
        normalized = stripped.replace("\\", "/")
        # Trailing-slash-tolerant: `foo/bar/` -> basename `bar`.
        normalized = normalized.rstrip("/")
        if not normalized:
            continue
        basename = normalized.rsplit("/", 1)[-1]
        if basename == dep_name:
            return True
    return False


def _check_internal_deps(
    state: Dict[str, Any],
    pkg: Dict[str, Any],
    project_root: Path,
    devforge_dir: Path,
) -> List[Dict[str, Any]]:
    """Every internal dep must resolve to either another registered
    package, an on-disk directory under the project root, OR a
    `packages_detected[]` entry in `.devforge/init.yaml`."""
    errors: List[Dict[str, Any]] = []
    for idx, dep in enumerate(pkg.get("dependencies") or []):
        if dep.get("kind") != "internal":
            continue
        name = dep.get("name", "")
        if _resolve_internal_dep(name, state, project_root, devforge_dir):
            continue
        candidate = project_root / name
        errors.append(_err(
            "internal-dep-unresolved",
            "dependencies[{0}]".format(idx),
            "internal dependency {0!r} does not match any registered "
            "package name/path, no directory exists at {1}, and no "
            "packages_detected entry in {2}/init.yaml matches".format(
                name, candidate, devforge_dir,
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


def _check_optional_render(
    state: Dict[str, Any],
    pkg: Dict[str, Any],
    package_path: str,
) -> List[Dict[str, Any]]:
    """Catch render bugs in OPTIONAL sections (scripts / hazards /
    usage_example / consumer_pattern).

    A legitimate empty state -> rendered `[TODO]` is fine (the schema
    declares those fields optional). But state populated -> rendered
    `[TODO]` is a render bug: the data is there, the rendering is
    eating it. Without this check, the bug surfaces as a final doc
    that silently shows `[TODO]` placeholders next to populated state.

    Encountered concretely on testForge20 2026-04-30: 11 add-package-script
    invocations were lost to a state-write race; the rendered doc showed
    the optional Scripts [TODO] instead of the populated table. The
    state-write race is fixed in `_state._state_transaction()`; this
    check catches future regressions in the same family.
    """
    try:
        markdown = render_package_skeleton(state, package_path)
    except KeyError:
        return []
    errors: List[Dict[str, Any]] = []
    for field, marker, is_empty_fn in OPTIONAL_SECTION_MARKERS:
        if marker not in markdown:
            continue
        if is_empty_fn(pkg.get(field)):
            continue
        errors.append(_err(
            "optional-section-render-bug", field,
            "rendered output shows the optional [{0}] placeholder but "
            "state has populated data — render is eating registered "
            "values".format(field),
        ))
    return errors


def validate_package(
    state: Dict[str, Any],
    package_path: str,
    project_root: Path,
    devforge_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Return a list of error dicts (empty list = valid).

    All rules run unconditionally; errors are collected so the LLM
    sees the full picture in one pass instead of fix-one-rerun-find-
    next loops.

    `devforge_dir` is optional: when omitted, derived from the live
    state-file location (`_state_file_path().parent`). The arg is in
    the signature so tests can pin it deterministically without
    relying on env-var ordering.
    """
    pkg = _require_package(state, package_path)
    if pkg is None:
        return [_err(
            "package-not-registered", "package",
            "package not registered at {0!r}; run add-package first".format(
                package_path,
            ),
        )]
    if devforge_dir is None:
        devforge_dir = _state_file_path().parent
    errors: List[Dict[str, Any]] = []
    errors.extend(_check_required_fields(pkg))
    errors.extend(_check_at_least_one_export(pkg))
    errors.extend(_check_at_least_one_dependency(pkg))
    errors.extend(_check_all_codeblocks(pkg, project_root))
    errors.extend(_check_internal_deps(state, pkg, project_root, devforge_dir))
    errors.extend(_check_enums(pkg))
    errors.extend(_check_no_todos(state, package_path))
    errors.extend(_check_optional_render(state, pkg, package_path))
    errors.extend(_check_decomposition(pkg, package_path, project_root))
    return errors


# ---------------------------------------------------------------------------
# Concern-tier validation (Phase 3.1).
# ---------------------------------------------------------------------------


def _check_concern_required_fields(
    concern: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """ConcernDoc required-field check: overview + directory_tree."""
    errors: List[Dict[str, Any]] = []
    for fname, setter in (
        ("overview", "set-concern-overview"),
        ("directory_tree", "set-concern-tree"),
    ):
        value = concern.get(fname)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            errors.append(_err(
                "required-fields", fname,
                "ConcernDoc.{0} is unset (call {1})".format(fname, setter),
            ))
    return errors


def _check_concern_at_least_one_public_surface(
    concern: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not (concern.get("public_surface") or []):
        return [_err(
            "public-surface-nonempty", "public_surface",
            "concern has no registered public surface; call "
            "add-concern-export at least once",
        )]
    return []


def _check_concern_codeblocks(
    concern: Dict[str, Any], project_root: Path,
) -> List[Dict[str, Any]]:
    """Per-CodeBlock filesystem + verbatim-match across the concern.

    Covers public_surface[].code, types[] (each CodeBlock directly), and
    the optional usage_example.
    """
    errors: List[Dict[str, Any]] = []
    for idx, export in enumerate(concern.get("public_surface") or []):
        code = export.get("code")
        field_label = "public_surface[{0}].code".format(idx)
        if not isinstance(code, dict):
            errors.append(_err(
                "export-code-malformed", field_label,
                "Export.code missing or not a dict",
            ))
            continue
        errors.extend(_check_codeblock(code, field_label, project_root))
    for idx, tb in enumerate(concern.get("types") or []):
        if not isinstance(tb, dict):
            errors.append(_err(
                "type-codeblock-malformed", "types[{0}]".format(idx),
                "ConcernDoc.types[{0}] must be a dict".format(idx),
            ))
            continue
        errors.extend(_check_codeblock(
            tb, "types[{0}]".format(idx), project_root,
        ))
    usage = concern.get("usage_example")
    if usage is not None:
        if not isinstance(usage, dict) or not usage:
            errors.append(_err(
                "usage-example-malformed", "usage_example",
                "usage_example is set but is not a non-empty dict (got "
                "{0!r})".format(usage),
            ))
        else:
            errors.extend(_check_codeblock(
                usage, "usage_example", project_root,
            ))
    return errors


def _check_concern_enums(concern: Dict[str, Any]) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    for idx, export in enumerate(concern.get("public_surface") or []):
        kind = export.get("kind")
        if kind not in EXPORT_KINDS:
            errors.append(_err(
                "export-kind-invalid",
                "public_surface[{0}].kind".format(idx),
                "Export.kind {0!r} is not one of {1}".format(
                    kind, list(EXPORT_KINDS),
                ),
            ))
    for idx, dep in enumerate(concern.get("dependencies") or []):
        kind = dep.get("kind")
        if kind not in DEPENDENCY_KINDS:
            errors.append(_err(
                "dep-kind-invalid", "dependencies[{0}].kind".format(idx),
                "Dependency.kind {0!r} is not one of {1}".format(
                    kind, list(DEPENDENCY_KINDS),
                ),
            ))
    for idx, hazard in enumerate(concern.get("hazards") or []):
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


def _check_concern_no_todos(
    state: Dict[str, Any], package_path: str, concern_name: str,
) -> List[Dict[str, Any]]:
    """Render the concern skeleton in-memory and assert no required-field
    `[TODO]` markers remain."""
    try:
        markdown = render_concern_skeleton(state, package_path, concern_name)
    except KeyError:
        return []
    errors: List[Dict[str, Any]] = []
    for marker in CONCERN_REQUIRED_FIELD_TODO_MARKERS:
        if marker in markdown:
            errors.append(_err(
                "todo-marker-present", "rendered-skeleton",
                "rendered concern skeleton still contains a required-field "
                "[TODO] marker ({0!r}); one or more required setters has "
                "not been called".format(marker[:40]),
            ))
    return errors


def _check_concern_optional_render(
    state: Dict[str, Any],
    concern: Dict[str, Any],
    package_path: str,
    concern_name: str,
) -> List[Dict[str, Any]]:
    """Concern-tier counterpart of `_check_optional_render` (Phase 3.1
    defense-in-depth).

    A legitimate empty state -> rendered `[TODO]` is fine (the four
    concern-tier optional fields — types / dependencies / hazards /
    usage_example — are all explicitly optional in the schema). But
    state populated -> rendered `[TODO]` is a render bug: the data is
    there, the rendering is eating it. Without this check, the bug
    surfaces as a final concern doc that silently shows `[TODO]`
    placeholders next to populated state.

    Mirrors the package-tier check added 2026-04-30 after the
    testForge20 race-condition incident; the same failure mode applies
    to concerns and would silently ship without this guard.
    """
    try:
        markdown = render_concern_skeleton(state, package_path, concern_name)
    except KeyError:
        # Existence check is the caller's job; don't double-report.
        return []
    errors: List[Dict[str, Any]] = []
    for field, marker, is_empty_fn in CONCERN_OPTIONAL_SECTION_MARKERS:
        if marker not in markdown:
            continue
        if is_empty_fn(concern.get(field)):
            continue
        errors.append(_err(
            "concern-optional-render-mismatch", field,
            "rendered concern output shows the optional [{0}] placeholder "
            "but state has populated data — render is eating registered "
            "values".format(field),
        ))
    return errors


def validate_concern(
    state: Dict[str, Any],
    package_path: str,
    concern_name: str,
    project_root: Path,
) -> List[Dict[str, Any]]:
    """Return a list of error dicts for one concern (empty list = valid)."""
    if _require_package(state, package_path) is None:
        return [_err(
            "package-not-registered", "package",
            "package not registered at {0!r}; run add-package first".format(
                package_path,
            ),
        )]
    concern = _require_concern(state, package_path, concern_name)
    if concern is None:
        return [_err(
            "concern-not-registered", "concern",
            "concern {0!r} not registered under {1!r}; run add-concern "
            "first".format(concern_name, package_path),
        )]
    errors: List[Dict[str, Any]] = []
    errors.extend(_check_concern_required_fields(concern))
    errors.extend(_check_concern_at_least_one_public_surface(concern))
    errors.extend(_check_concern_codeblocks(concern, project_root))
    errors.extend(_check_concern_enums(concern))
    errors.extend(_check_concern_no_todos(state, package_path, concern_name))
    errors.extend(_check_concern_optional_render(
        state, concern, package_path, concern_name,
    ))
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


def cmd_validate_concern(args: argparse.Namespace) -> int:
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    errors = validate_concern(
        state, args.package, args.concern, _project_root(),
    )
    if not errors:
        return 0
    _print_errors(errors)
    return _die(
        "validate-concern: {0} error(s) at {1}/{2}".format(
            len(errors), args.package, args.concern,
        ),
    )


def cmd_render_concern_doc(args: argparse.Namespace) -> int:
    """Render the FINAL concern doc to
    `docs/<package>/<concern>/index.md`, gated by validate-concern.

    Validation must pass with zero errors; on any error, the .md is
    NOT written and the existing .skeleton (if any) is retained. On
    success the .md is written atomically AND the .skeleton sibling
    is removed.
    """
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    if _require_package(state, args.package) is None:
        return _die(
            "package not registered at {0!r}; run add-package first".format(
                args.package,
            )
        )
    if _require_concern(state, args.package, args.concern) is None:
        return _die(
            "concern {0!r} not registered under {1}; run add-concern "
            "first".format(args.concern, args.package)
        )
    project_root = _project_root()
    errors = validate_concern(
        state, args.package, args.concern, project_root,
    )
    if errors:
        _print_errors(errors)
        return _die(
            "render-concern-doc: validation failed with {0} error(s) at "
            "{1}/{2}; .md NOT written".format(
                len(errors), args.package, args.concern,
            ),
        )
    markdown = render_concern_skeleton(state, args.package, args.concern)
    out_path = (
        project_root / "docs" / args.package / args.concern / "index.md"
    )
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
