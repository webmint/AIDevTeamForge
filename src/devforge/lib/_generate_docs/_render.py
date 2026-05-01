"""Markdown rendering for the generate_docs helper PackageDoc tier.

Renders a PackageDoc state record into a single markdown string in a
fixed section order. The same render is used by two subcommands:

- `render-package-skeleton` writes `docs/<package-path>/index.md.skeleton`.
  No validation gate — unset fields appear as `[TODO: ...]` slots so the
  LLM can see exactly which setters still need to fire.
- `render-package-doc` writes `docs/<package-path>/index.md`. Gated by
  `_validators.validate_package`; render-package-doc is gated by
  validate-package while render-package-skeleton is not. After the .md
  file is written, the .skeleton sibling (if present) is removed.

Render rules — fixed manual concatenation per the schema-anchored
generate-docs design (project_schema_anchored_generate_docs.md memory):

- No template engine, no jinja2; the helper owns shape, the LLM owns
  values. The render template here IS the public shape contract.
- Idempotent: a state record renders to byte-identical output on
  re-runs (sort orders are stable, no timestamps embedded).
- Section order is fixed (1..11 below). Section 7 (Types) is omitted
  entirely when empty rather than printed with a [TODO] — having no
  type exports is normal, not a missing-data signal.

Atomic file writes use `tempfile.mkstemp` + `os.replace` (anti-pattern
#4) so concurrent invocations and crash recovery are handled correctly.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import os
import sys
import tempfile
from html import escape as _html_escape
from pathlib import Path
from typing import Any, Dict, List, Optional


def _esc(value: str) -> str:
    """HTML-escape a NARRATIVE prose value before substitution.

    Markdown renderers pass HTML-looking sequences through as raw HTML.
    Inline TypeScript generic syntax like ``DeepReadonly<Ref<S>>`` in
    a prose field embeds ``<S>`` — the deprecated HTML strikethrough
    tag — which makes everything until a (never-emitted) ``</s>`` render
    struck through. Escaping ``<``, ``>``, ``&`` at the substitution
    point converts those characters to entity references so the
    renderer treats them as literal text.

    Use this ONLY at narrative-prose substitution points (overview,
    hazard.description, dependency.purpose, export.description). Code
    contexts — fenced blocks (``` ... ```) and inline backtick spans —
    must pass through verbatim; escaping them would corrupt code.
    ``quote=False`` keeps quote characters intact (they have no special
    meaning in markdown and need not be escaped).
    """
    return _html_escape(value, quote=False)

from ._state import (
    StateLoadError,
    _die,
    _info,
    _load_state,
    _require_package,
)


_TODO_OVERVIEW = (
    "[TODO: 1-2 paragraphs describing what this package provides "
    "and who consumes it]"
)
_TODO_TREE = "[TODO: ascii tree of source layout]"
_TODO_SCRIPTS = (
    "[TODO: enumerate via add-package-script "
    "(or run extract-package-scripts)]"
)
_TODO_EXPORTS = "[TODO: enumerate package exports via add-package-export]"
_TODO_DEPENDENCIES = "[TODO: enumerate via add-package-dep]"
_TODO_HAZARDS = (
    "[TODO: list inline observations via add-package-hazard, or "
    "run with --skip-hazards if the package has no observable mislogic]"
)
_TODO_USAGE_EXAMPLE = (
    "[TODO: lift a real usage example via set-package-usage-example]"
)
_TODO_CONSUMER_PATTERN = (
    "[TODO: lift a representative consumer call via "
    "set-package-consumer-pattern]"
)
# Tech Stack uses two sentinels: a [TODO] for the required primary
# language (caught by the no-todo rule in validate-package), and an
# em-dash for the optional framework / build_tool (so an unset
# optional field doesn't masquerade as a missing-required-field TODO).
_TODO_TECH_REQUIRED = "[TODO]"
_OPTIONAL_UNSET_PLACEHOLDER = "—"


# The required-field TODO markers — every one of these in a rendered
# skeleton indicates a required setter that has not been called.
# `_validators._check_no_todos` matches against these to raise a
# todo-marker-present error. Optional-section TODOs (scripts,
# hazards, usage_example, consumer_pattern) are NOT in this list:
# the schema declares those fields optional and validate-package must
# not block on them.
REQUIRED_FIELD_TODO_MARKERS = (
    _TODO_OVERVIEW,
    _TODO_TREE,
    _TODO_TECH_REQUIRED,
    _TODO_EXPORTS,
    _TODO_DEPENDENCIES,
)


# Optional-section markers — consumed by `_validators._check_optional_render`
# as a defense-in-depth check: if any of these markers appear in the
# rendered output AND the corresponding state field is populated, that's
# a render bug (state has the data but the rendering produced [TODO]).
# The 4-tuple shape is (state-field, marker, "is-empty" predicate).
# `is-empty` returns True when the state field is missing/empty (i.e.,
# the [TODO] is a legitimate optional skip, not a render bug).
def _scripts_empty(value: Any) -> bool:
    return not value


def _hazards_empty(value: Any) -> bool:
    return not value


def _opt_codeblock_empty(value: Any) -> bool:
    return value is None


OPTIONAL_SECTION_MARKERS = (
    ("scripts", _TODO_SCRIPTS, _scripts_empty),
    ("hazards", _TODO_HAZARDS, _hazards_empty),
    ("usage_example", _TODO_USAGE_EXAMPLE, _opt_codeblock_empty),
    ("consumer_pattern", _TODO_CONSUMER_PATTERN, _opt_codeblock_empty),
)


def _render_overview(pkg: Dict[str, Any]) -> str:
    overview = pkg.get("overview")
    # Prose substitution: HTML-escape (the [TODO] sentinel contains no
    # angle brackets and is safe to substitute either way; escaping it
    # is a no-op).
    body = _esc(overview) if overview else _TODO_OVERVIEW
    return "## Overview\n\n{0}\n".format(body)


def _render_directory_tree(pkg: Dict[str, Any]) -> str:
    tree = pkg.get("directory_tree")
    body = tree if tree else _TODO_TREE
    return "## Directory Structure\n\n```\n{0}\n```\n".format(body)


def _render_tech_stack(pkg: Dict[str, Any]) -> str:
    primary = pkg.get("primary_language") or _TODO_TECH_REQUIRED
    framework = pkg.get("framework") or _OPTIONAL_UNSET_PLACEHOLDER
    build_tool = pkg.get("build_tool") or _OPTIONAL_UNSET_PLACEHOLDER
    rows = [
        "| Field | Value |",
        "| --- | --- |",
        "| Primary Language | {0} |".format(primary),
        "| Framework | {0} |".format(framework),
        "| Build Tool | {0} |".format(build_tool),
    ]
    return "## Tech Stack\n\n" + "\n".join(rows) + "\n"


def _render_scripts(pkg: Dict[str, Any]) -> str:
    scripts = pkg.get("scripts") or {}
    if not scripts:
        return "## Scripts\n\n{0}\n".format(_TODO_SCRIPTS)
    rows = ["| Script | Command |", "| --- | --- |"]
    for name in sorted(scripts.keys()):
        rows.append("| `{0}` | `{1}` |".format(name, scripts[name]))
    return "## Scripts\n\n" + "\n".join(rows) + "\n"


def _render_code_block(code: Dict[str, Any]) -> str:
    """Render a CodeBlock dict as a fenced block with a cite comment.

    The cite comment is rendered ABOVE the fenced block (inside the
    markdown but visually grouped with the snippet) so a reader can
    trace any quoted snippet back to its source line range without
    polluting the snippet itself.
    """
    cite = code.get("cite") or {}
    cite_file = cite.get("file", "")
    cite_start = cite.get("start", "")
    cite_end = cite.get("end", "")
    language = code.get("language") or ""
    snippet = code.get("snippet") or ""
    return (
        "<!-- {0}:{1}-{2} -->\n"
        "```{3}\n"
        "{4}\n"
        "```\n"
    ).format(cite_file, cite_start, cite_end, language, snippet)


def _render_export_entry(export: Dict[str, Any]) -> str:
    """Render one export as a sub-section with header / signature /
    description / cite + fenced code."""
    parts: List[str] = []
    parts.append(
        "### `{0}` — {1}".format(export["name"], export["kind"])
    )
    parts.append("")
    if export.get("signature"):
        # Signature renders inside a fenced code block — code context,
        # NOT escaped (escaping would corrupt the displayed signature).
        parts.append("```")
        parts.append(export["signature"])
        parts.append("```")
        parts.append("")
    # Description is narrative prose — HTML-escape so generic-syntax
    # tokens like ``<S>`` do not get parsed as the HTML strikethrough
    # tag by markdown renderers.
    parts.append(_esc(export["description"]))
    parts.append("")
    parts.append(_render_code_block(export["code"]))
    return "\n".join(parts)


def _render_main_exports(pkg: Dict[str, Any]) -> str:
    exports = pkg.get("exports") or []
    # Filter out type-kind entries; types render in their own section.
    non_types = [e for e in exports if e.get("kind") != "type"]
    if not non_types:
        return "## Main Exports\n\n{0}\n".format(_TODO_EXPORTS)
    body_parts = ["## Main Exports", ""]
    for ex in non_types:
        body_parts.append(_render_export_entry(ex))
    return "\n".join(body_parts).rstrip() + "\n"


def _render_types(pkg: Dict[str, Any]) -> Optional[str]:
    """Render the Types section, or None if there are no type exports.

    Empty Types -> section omitted entirely (per spec): not having any
    type-kind exports is normal, not a missing-data signal.
    """
    exports = pkg.get("exports") or []
    types = [e for e in exports if e.get("kind") == "type"]
    if not types:
        return None
    body_parts = ["## Types", ""]
    for ex in types:
        body_parts.append(_render_export_entry(ex))
    return "\n".join(body_parts).rstrip() + "\n"


def _render_dependency_entry(dep: Dict[str, Any]) -> str:
    name = dep["name"]
    version = dep.get("version") or ""
    # Purpose is narrative prose — HTML-escape to keep angle-bracket
    # tokens from being parsed as raw HTML by markdown renderers.
    purpose = _esc(dep.get("purpose", ""))
    version_part = " ({0})".format(version) if version else ""
    locations = dep.get("consumer_locations") or []
    line = "- `{0}`{1} — {2}".format(name, version_part, purpose)
    if locations:
        loc_text = ", ".join("`{0}`".format(loc) for loc in locations)
        line = line + "  \n  consumers: {0}".format(loc_text)
    return line


def _render_dependencies(pkg: Dict[str, Any]) -> str:
    deps = pkg.get("dependencies") or []
    internal = [d for d in deps if d.get("kind") == "internal"]
    external = [d for d in deps if d.get("kind") == "external"]
    if not internal and not external:
        return "## Dependencies\n\n{0}\n".format(_TODO_DEPENDENCIES)
    parts = ["## Dependencies", ""]
    parts.append("### Workspace-internal")
    parts.append("")
    if internal:
        for dep in internal:
            parts.append(_render_dependency_entry(dep))
    else:
        parts.append("_None._")
    parts.append("")
    parts.append("### External")
    parts.append("")
    if external:
        for dep in external:
            parts.append(_render_dependency_entry(dep))
    else:
        parts.append("_None._")
    parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _render_hazards(pkg: Dict[str, Any]) -> str:
    hazards = pkg.get("hazards") or []
    if not hazards:
        return "## Hazards\n\n{0}\n".format(_TODO_HAZARDS)
    parts = ["## Hazards", ""]
    for hazard in hazards:
        # Both fields are narrative prose — HTML-escape so generic-syntax
        # tokens (e.g. ``DeepReadonly<Ref<S>>``) do not turn into HTML
        # tags. ``<S>`` is the deprecated strikethrough tag and was the
        # original visible-symptom field for this fix.
        line = "- **{0}**: {1}".format(
            _esc(hazard["category"]), _esc(hazard["description"])
        )
        cite = hazard.get("cite")
        if cite:
            line = line + "  \n  cite: `{0}:{1}-{2}`".format(
                cite["file"], cite["start"], cite["end"]
            )
        parts.append(line)
    return "\n".join(parts) + "\n"


def _render_usage_example(pkg: Dict[str, Any]) -> str:
    ue = pkg.get("usage_example")
    if not ue:
        return "## Usage Example\n\n{0}\n".format(_TODO_USAGE_EXAMPLE)
    return "## Usage Example\n\n" + _render_code_block(ue)


def _render_consumer_pattern(pkg: Dict[str, Any]) -> str:
    cp = pkg.get("consumer_pattern")
    if not cp:
        return "## Consumer Pattern\n\n{0}\n".format(_TODO_CONSUMER_PATTERN)
    return "## Consumer Pattern\n\n" + _render_code_block(cp)


def render_package_skeleton(state: Dict[str, Any], package_path: str) -> str:
    """Pure render function — assembles a markdown string from a state
    record. Does not touch the filesystem.

    Both `cmd_render_package_skeleton` and `cmd_render_package_doc` call
    this; the difference between the two is only the output path and
    whether validation gates the write.
    """
    pkg = _require_package(state, package_path)
    if pkg is None:
        raise KeyError(
            "package not registered at {0!r}".format(package_path)
        )
    sections: List[str] = []
    sections.append("# {0}".format(pkg["name"]))
    sections.append("")
    sections.append(_render_overview(pkg))
    sections.append(_render_directory_tree(pkg))
    sections.append(_render_tech_stack(pkg))
    sections.append(_render_scripts(pkg))
    sections.append(_render_main_exports(pkg))
    types_section = _render_types(pkg)
    if types_section is not None:
        sections.append(types_section)
    sections.append(_render_dependencies(pkg))
    sections.append(_render_hazards(pkg))
    sections.append(_render_usage_example(pkg))
    sections.append(_render_consumer_pattern(pkg))
    # Each section already ends with a newline; join with a blank line
    # in between so the markdown reads cleanly.
    return "\n".join(sections).rstrip() + "\n"


def _atomic_write_text(path: Path, text: str) -> None:
    """Write `text` to `path` atomically (mkstemp + os.replace).

    Per anti-pattern #4: never use a fixed-name temp file. Failure
    paths unlink the temp file before re-raising so partial writes
    don't accumulate alongside the target.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=".{0}.".format(path.name),
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _project_root() -> Path:
    """Return the project root (parent of `.devforge`).

    Honors `DEVFORGE_PROJECT_ROOT` (test override) when set; otherwise
    derives from `DEVFORGE_DIR` (parent of state file). When neither is
    set, falls back to cwd.
    """
    root_env = os.environ.get("DEVFORGE_PROJECT_ROOT")
    if root_env:
        return Path(root_env)
    devforge_dir = os.environ.get("DEVFORGE_DIR")
    if devforge_dir:
        return Path(devforge_dir).parent
    return Path.cwd()


def cmd_render_package_skeleton(args: argparse.Namespace) -> int:
    """Render the skeleton (with [TODO] slots) to
    `docs/<path>/index.md.skeleton`."""
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    pkg = _require_package(state, args.path)
    if pkg is None:
        return _die(
            "package not registered at {0!r}; run add-package first".format(
                args.path
            )
        )
    try:
        markdown = render_package_skeleton(state, args.path)
    except KeyError as err:
        return _die(str(err))
    out_path = _project_root() / "docs" / args.path / "index.md.skeleton"
    try:
        _atomic_write_text(out_path, markdown)
    except OSError as err:
        return _die("cannot write {0}: {1}".format(out_path, err), code=1)
    _info(
        "render-package-skeleton at {0} -> {1}".format(args.path, out_path)
    )
    sys.stdout.write(str(out_path) + "\n")
    return 0
