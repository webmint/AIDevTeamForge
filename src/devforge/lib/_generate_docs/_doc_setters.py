"""F.4 — multi-tier skeleton-fill primitives + render-doc.

Subcommands:

  init-doc            --tier {concern,package-overview,package-architecture,
                              project-overview,project-architecture}
                      --target T --frontmatter <json> [--tree <text>] [--split]
  set-doc-purpose     --tier {concern,package-overview,project-overview}
                      --target T --text "..."
  set-doc-structure   --tier concern --target T --annotations <json>
  set-doc-concerns    --tier package-overview --target T --concerns <json>
  set-doc-files       --tier package-overview --target T --files <json>
  set-doc-layers      --tier {package-architecture,project-architecture}
                      --target T --layers <json>
  set-doc-patterns    --tier package-architecture --target T --patterns <json>
  set-doc-packages    --tier project-overview --target T --packages <json>
  set-doc-cross-cuts  --tier project-architecture --target T --cross-cuts <json>
  set-doc-subconcerns --tier concern --target T --subconcerns <json>   (Plan F 3a)
  render-doc          --tier T --target T [--out PATH]

Skeleton-fill design:
1. `init-doc` writes the appropriate skeleton file for the tier:
     concern               → docs/<target>/index.md.skeleton
     package-overview      → docs/<target>/overview.md.skeleton
     package-architecture  → docs/<target>/architecture.md.skeleton
   Skeleton contains frontmatter, H1, section anchors, and section
   placeholders (`<!-- TODO: purpose -->`, etc.). Concern tier also
   embeds the F.2 tree_text inside a ```text fence.
2. Setters edit the skeleton in place, replacing placeholders or
   already-filled section bodies (idempotent).
3. `render-doc` renames the skeleton to the final `.md` atomically.

The skeleton file IS the state. No separate JSON state file. Helper
owns markdown structure; orchestrator owns values via setters.

Concern docs ship `## Purpose` + `## Structure` only. Hazards moved
to /audit. Glossary tier dropped — Purpose paragraphs surface terms
in context.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._md_frontmatter import FrontmatterParseError, parse_frontmatter, render_frontmatter

_PURPOSE_PLACEHOLDER = "<!-- TODO: purpose -->"
_CONCERNS_PLACEHOLDER = "<!-- TODO: concerns -->"
_FILES_PLACEHOLDER = "<!-- TODO: files -->"
_LAYERS_PLACEHOLDER = "<!-- TODO: layers -->"
_PATTERNS_PLACEHOLDER = "<!-- TODO: patterns -->"
_PACKAGES_PLACEHOLDER = "<!-- TODO: packages -->"
_CROSS_CUTS_PLACEHOLDER = "<!-- TODO: cross-cuts -->"
_SUBCONCERNS_PLACEHOLDER = "<!-- TODO: sub-concerns -->"
# Track 4 Phase 1 — project-tier mechanical sections.
_TECH_STACK_PLACEHOLDER = "<!-- TODO: tech-stack -->"
_PROJECT_STRUCTURE_PLACEHOLDER = "<!-- TODO: project-structure -->"
_KEY_COMMANDS_PLACEHOLDER = "<!-- TODO: key-commands -->"
_TEST_FILES_PLACEHOLDER = "<!-- TODO: test-files -->"
_CROSS_MODULE_DEPS_PLACEHOLDER = "<!-- TODO: cross-module-dependencies -->"
# Track 4 Phase 2 — mixed mechanical+LLM sections (helper renders structure;
# LLM provides purpose/description/role text inside JSON input).
_ENTRY_POINTS_PLACEHOLDER = "<!-- TODO: entry-points -->"
_MODULE_MAP_PLACEHOLDER = "<!-- TODO: module-map -->"
_APPLICATION_ROUTES_PLACEHOLDER = "<!-- TODO: application-routes -->"
_NAVIGATION_GUARDS_PLACEHOLDER = "<!-- TODO: navigation-guards -->"
# Track 4 Phase 3 — architecture-tier sections (LLM-judgment heavy +
# code-snippet cite-back via CBM get_code_snippet).
_ARCH_OVERVIEW_NARRATIVE_PLACEHOLDER = "<!-- TODO: architecture-overview-narrative -->"
_MODULE_STRUCTURE_PLACEHOLDER = "<!-- TODO: module-structure -->"
_ARCH_PATTERNS_PLACEHOLDER = "<!-- TODO: architecture-patterns -->"
_CONVENTIONS_PLACEHOLDER = "<!-- TODO: conventions -->"
_DEP_DIRECTION_RULES_PLACEHOLDER = "<!-- TODO: dependency-direction-rules -->"
_DEP_OVERVIEW_MERMAID_PLACEHOLDER = "<!-- TODO: dependency-overview-mermaid -->"
_TREE_FENCE_OPEN = "```text"
_TREE_FENCE_CLOSE = "```"
_ANNOTATION_SEPARATOR = "  # "
_LEAF_CONNECTORS = ("├── ", "└── ")
_CANONICAL_AGGREGATORS = (
    "mod.rs",
    "lib.rs",
    "__init__.py",
    "index.ts",
    "index.js",
    "doc.go",
    "index.tsx",
    "index.jsx",
)

_VALID_TIERS = (
    "concern",
    "package-overview",
    "package-architecture",
    "project-overview",
    "project-architecture",
)

_TIER_DOC_FILENAMES: Dict[str, str] = {
    "concern": "index.md",
    "package-overview": "overview.md",
    "package-architecture": "architecture.md",
    "project-overview": "overview.md",
    "project-architecture": "architecture.md",
}

_PROJECT_TIERS = ("project-overview", "project-architecture")


# ── Path resolution ─────────────────────────────────────────────────────────


def _doc_path_for(args: argparse.Namespace) -> Path:
    """Resolve the doc path.

    Concern + package tiers: docs/<target>/<tier-filename>.
    Project tiers: docs/<tier-filename> (no per-target subdir; target arg
    is treated as a label only for the H1 / frontmatter).
    """
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()
    filename = _TIER_DOC_FILENAMES.get(args.tier, "index.md")
    if args.tier in _PROJECT_TIERS:
        return project_root / "docs" / filename
    return project_root / "docs" / args.target / filename


def _skeleton_path(doc_path: Path) -> Path:
    return doc_path.with_suffix(doc_path.suffix + ".skeleton")


def _load_active(doc_path: Path) -> Tuple[Optional[Path], Optional[str]]:
    """Return (path, content) for whichever of <doc>.skeleton or <doc> exists."""
    skel = _skeleton_path(doc_path)
    if skel.is_file():
        return skel, skel.read_text(encoding="utf-8")
    if doc_path.is_file():
        return doc_path, doc_path.read_text(encoding="utf-8")
    return None, None


# ── Skeleton builders (per tier) ────────────────────────────────────────────


def _build_concern_skeleton(frontmatter: Dict[str, Any], tree_text: str) -> str:
    concern_name = frontmatter.get("concern") or frontmatter.get("package") or "doc"
    body = (
        f"# {concern_name}\n\n"
        f"## Purpose\n\n"
        f"{_PURPOSE_PLACEHOLDER}\n\n"
        f"## Structure\n\n"
        f"{_TREE_FENCE_OPEN}\n"
        f"{tree_text.rstrip(chr(10))}\n"
        f"{_TREE_FENCE_CLOSE}\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


def _build_concern_split_skeleton(frontmatter: Dict[str, Any]) -> str:
    """Skeleton for a parent concern doc whose children were split-dispatched.

    Plan F 3a: parent has no `## Structure` (it's an aggregator, not a leaf).
    Sections: `## Purpose` (orchestrator-direct synthesis) + `## Sub-concerns`
    (bulleted list with links to child docs).
    """
    concern_name = frontmatter.get("concern") or frontmatter.get("package") or "doc"
    body = (
        f"# {concern_name}\n\n"
        f"## Purpose\n\n"
        f"{_PURPOSE_PLACEHOLDER}\n\n"
        f"## Sub-concerns\n\n"
        f"{_SUBCONCERNS_PLACEHOLDER}\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


def _build_package_overview_skeleton(frontmatter: Dict[str, Any]) -> str:
    name = frontmatter.get("package", "package")
    body = (
        f"# {name}\n\n"
        f"## Purpose\n\n"
        f"{_PURPOSE_PLACEHOLDER}\n\n"
        f"## Concerns\n\n"
        f"{_CONCERNS_PLACEHOLDER}\n\n"
        f"## Files\n\n"
        f"{_FILES_PLACEHOLDER}\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


def _build_package_architecture_skeleton(frontmatter: Dict[str, Any]) -> str:
    name = frontmatter.get("package", "package")
    body = (
        f"# {name} architecture\n\n"
        f"## Layers\n\n"
        f"{_LAYERS_PLACEHOLDER}\n\n"
        f"## Patterns\n\n"
        f"{_PATTERNS_PLACEHOLDER}\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


# Project-tier section ownership. /generate-docs owns these 4 anchors;
# every other `## ` anchor in `docs/overview.md` or `docs/architecture.md`
# is preserved verbatim across init-doc re-runs (e.g. anchors written by
# `/constitute`: `## What this project is for`, `## How it's used`,
# `## Architectural Decisions`, `## Layer Boundaries & Dependency Rules`,
# `## Data Flow`, `## Cross-cutting Concerns` — or any future anchor a
# user/command adds).
_PROJECT_OVERVIEW_OWNED_ANCHORS: Tuple[Tuple[str, str], ...] = (
    ("Purpose", _PURPOSE_PLACEHOLDER),
    ("Tech Stack", _TECH_STACK_PLACEHOLDER),
    ("Project Structure", _PROJECT_STRUCTURE_PLACEHOLDER),
    ("Entry Points", _ENTRY_POINTS_PLACEHOLDER),
    ("Key Commands", _KEY_COMMANDS_PLACEHOLDER),
    ("Module Map", _MODULE_MAP_PLACEHOLDER),
    ("Cross-Module Dependencies", _CROSS_MODULE_DEPS_PLACEHOLDER),
    ("Application Routes", _APPLICATION_ROUTES_PLACEHOLDER),
    ("Navigation Guards", _NAVIGATION_GUARDS_PLACEHOLDER),
    ("Test Files", _TEST_FILES_PLACEHOLDER),
    ("Packages", _PACKAGES_PLACEHOLDER),
)
_PROJECT_ARCHITECTURE_OWNED_ANCHORS: Tuple[Tuple[str, str], ...] = (
    ("Architecture Overview", _ARCH_OVERVIEW_NARRATIVE_PLACEHOLDER),
    ("Module / Package Structure", _MODULE_STRUCTURE_PLACEHOLDER),
    ("Patterns", _ARCH_PATTERNS_PLACEHOLDER),
    ("Conventions", _CONVENTIONS_PLACEHOLDER),
    ("Layers", _LAYERS_PLACEHOLDER),
    ("Cross-Cuts", _CROSS_CUTS_PLACEHOLDER),
    ("Dependency Direction Rules", _DEP_DIRECTION_RULES_PLACEHOLDER),
    ("Dependency Overview", _DEP_OVERVIEW_MERMAID_PLACEHOLDER),
)


def _merge_project_skeleton(
    doc_path: Path,
    fresh_skeleton: str,
    owned_anchors_with_placeholders: Tuple[Tuple[str, str], ...],
) -> str:
    """Merge an existing project-tier doc with a freshly built skeleton.

    Cold start (file missing or unparseable): return ``fresh_skeleton``
    verbatim — caller writes it as-is.

    Existing file (typical case): preserve the entire existing body
    EXCEPT the owned-anchor sections (those are reset to placeholders so
    setters can refill cleanly). Frontmatter is merged: existing keys
    stay; fresh keys (e.g. ``last_indexed``, ``source_stamp``) override.

    Owned anchors that don't exist in the existing file (cold-install
    stubs that haven't been touched by /generate-docs yet) are appended
    in their declared order at the end of the body.

    Owned anchors that DO exist in the existing file are reset in-place
    via the same regex `_replace_or_substitute` setters use — body
    becomes ``<!-- TODO: ... -->`` placeholder again, ready for the
    setter to replace.
    """
    # Cold start: no existing file → use fresh skeleton verbatim.
    if not doc_path.is_file():
        return fresh_skeleton
    try:
        existing_text = doc_path.read_text(encoding="utf-8")
    except OSError:
        return fresh_skeleton

    try:
        existing_fm, existing_body = parse_frontmatter(existing_text)
    except FrontmatterParseError:
        # Stub file may ship without frontmatter (install-shipped stubs at
        # docs/overview.md / docs/architecture.md have an H1 + section
        # anchors but no `---` block). Treat the whole file as body and
        # take frontmatter exclusively from the fresh skeleton.
        existing_fm = {}
        existing_body = existing_text

    try:
        fresh_fm, _fresh_body = parse_frontmatter(fresh_skeleton)
    except FrontmatterParseError:  # pragma: no cover — fresh always parses
        return fresh_skeleton

    merged_fm: Dict[str, Any] = {**existing_fm, **fresh_fm}

    # Normalize edge whitespace so re-runs are byte-stable.
    body = existing_body.strip("\n")

    # First pass: determine which declared anchors already exist in body.
    def _anchor_in_body(anchor: str, text: str) -> bool:
        return bool(re.search(
            r"^## " + re.escape(anchor) + r"( \(|$|\n)",
            text,
            re.MULTILINE,
        ))

    existing_anchors: set = {
        anchor
        for anchor, _ in owned_anchors_with_placeholders
        if _anchor_in_body(anchor, body)
    }

    # Second pass: process each declared anchor in order.
    for idx, (anchor, placeholder) in enumerate(owned_anchors_with_placeholders):
        if anchor in existing_anchors:
            # Anchor is present: reset its content to the placeholder.
            body = _replace_or_substitute(body, placeholder, anchor, placeholder)
        else:
            # Anchor is missing: find the first later-declared anchor that
            # currently exists in the body (or was already inserted).
            insertion_target: Optional[str] = None
            for later_anchor, _ in owned_anchors_with_placeholders[idx + 1:]:
                if later_anchor in existing_anchors:
                    insertion_target = later_anchor
                    break

            new_section = f"## {anchor}\n\n{placeholder}"
            if insertion_target is not None:
                # Insert immediately before the insertion_target heading.
                target_pattern = re.compile(
                    r"^## " + re.escape(insertion_target) + r"\b",
                    re.MULTILINE,
                )
                m = target_pattern.search(body)
                if m:
                    insert_pos = m.start()
                    # Ensure two newlines of separation on both sides.
                    before = body[:insert_pos].rstrip("\n")
                    after = body[insert_pos:]
                    body = before + "\n\n" + new_section + "\n\n" + after
                    # Collapse runs of 3+ newlines to exactly 2.
                    body = re.sub(r"\n{3,}", "\n\n", body)
                else:
                    # Fallback: insertion_target not found by regex → append.
                    body = body.rstrip("\n") + "\n\n" + new_section
            else:
                # No later anchor in body → append at end.
                body = body.rstrip("\n") + "\n\n" + new_section

            # Mark this anchor as now existing so subsequent missing anchors
            # can use it as an insertion target.
            existing_anchors.add(anchor)

        body = body.rstrip("\n")

    return render_frontmatter(merged_fm, "\n" + body + "\n")


def _build_project_overview_skeleton(frontmatter: Dict[str, Any], target: str) -> str:
    name = frontmatter.get("project") or target or "project"
    body = (
        f"# {name}\n\n"
        f"## Purpose\n\n"
        f"{_PURPOSE_PLACEHOLDER}\n\n"
        f"## Tech Stack\n\n"
        f"{_TECH_STACK_PLACEHOLDER}\n\n"
        f"## Project Structure\n\n"
        f"{_PROJECT_STRUCTURE_PLACEHOLDER}\n\n"
        f"## Entry Points\n\n"
        f"{_ENTRY_POINTS_PLACEHOLDER}\n\n"
        f"## Key Commands\n\n"
        f"{_KEY_COMMANDS_PLACEHOLDER}\n\n"
        f"## Module Map\n\n"
        f"{_MODULE_MAP_PLACEHOLDER}\n\n"
        f"## Cross-Module Dependencies\n\n"
        f"{_CROSS_MODULE_DEPS_PLACEHOLDER}\n\n"
        f"## Application Routes\n\n"
        f"{_APPLICATION_ROUTES_PLACEHOLDER}\n\n"
        f"## Navigation Guards\n\n"
        f"{_NAVIGATION_GUARDS_PLACEHOLDER}\n\n"
        f"## Test Files\n\n"
        f"{_TEST_FILES_PLACEHOLDER}\n\n"
        f"## Packages\n\n"
        f"{_PACKAGES_PLACEHOLDER}\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


def _build_project_architecture_skeleton(frontmatter: Dict[str, Any], target: str) -> str:
    name = frontmatter.get("project") or target or "project"
    body = (
        f"# {name} architecture\n\n"
        f"## Architecture Overview\n\n"
        f"{_ARCH_OVERVIEW_NARRATIVE_PLACEHOLDER}\n\n"
        f"## Module / Package Structure\n\n"
        f"{_MODULE_STRUCTURE_PLACEHOLDER}\n\n"
        f"## Patterns\n\n"
        f"{_ARCH_PATTERNS_PLACEHOLDER}\n\n"
        f"## Conventions\n\n"
        f"{_CONVENTIONS_PLACEHOLDER}\n\n"
        f"## Layers\n\n"
        f"{_LAYERS_PLACEHOLDER}\n\n"
        f"## Cross-Cuts\n\n"
        f"{_CROSS_CUTS_PLACEHOLDER}\n\n"
        f"## Dependency Direction Rules\n\n"
        f"{_DEP_DIRECTION_RULES_PLACEHOLDER}\n\n"
        f"## Dependency Overview\n\n"
        f"{_DEP_OVERVIEW_MERMAID_PLACEHOLDER}\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


# ── Section replacers ──────────────────────────────────────────────────────


def _replace_or_substitute(content: str, placeholder: str, anchor: str, new_text: str) -> str:
    """Replace either the placeholder OR an already-filled section body.

    Section body = lines between `## <anchor>\n\n` and the next `## ` (or EOF).
    """
    new_text = new_text.rstrip()
    if placeholder in content:
        return content.replace(placeholder, new_text, 1)
    pattern = re.compile(
        rf"(## {re.escape(anchor)}\n\n)(.*?)(\n## |\Z)",
        flags=re.DOTALL,
    )
    return pattern.sub(rf"\g<1>{new_text}\g<3>", content, count=1)


def _replace_purpose_block(content: str, new_text: str) -> str:
    return _replace_or_substitute(content, _PURPOSE_PLACEHOLDER, "Purpose", new_text)


def _replace_concerns_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _CONCERNS_PLACEHOLDER, "Concerns", bullet_text)


def _replace_files_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _FILES_PLACEHOLDER, "Files", bullet_text)


def _replace_packages_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _PACKAGES_PLACEHOLDER, "Packages", bullet_text)


def _replace_cross_cuts_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _CROSS_CUTS_PLACEHOLDER, "Cross-Cuts", bullet_text)


def _replace_layers_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _LAYERS_PLACEHOLDER, "Layers", bullet_text)


def _replace_patterns_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _PATTERNS_PLACEHOLDER, "Patterns", bullet_text)


def _replace_subconcerns_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(
        content, _SUBCONCERNS_PLACEHOLDER, "Sub-concerns", bullet_text
    )


def _replace_tech_stack_block(content: str, table_text: str) -> str:
    return _replace_or_substitute(
        content, _TECH_STACK_PLACEHOLDER, "Tech Stack", table_text
    )


def _replace_project_structure_block(content: str, fenced_text: str) -> str:
    return _replace_or_substitute(
        content, _PROJECT_STRUCTURE_PLACEHOLDER, "Project Structure", fenced_text
    )


def _replace_key_commands_block(content: str, table_text: str) -> str:
    return _replace_or_substitute(
        content, _KEY_COMMANDS_PLACEHOLDER, "Key Commands", table_text
    )


def _replace_test_files_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(
        content, _TEST_FILES_PLACEHOLDER, "Test Files", bullet_text
    )


def _replace_cross_module_deps_block(content: str, fenced_text: str) -> str:
    return _replace_or_substitute(
        content, _CROSS_MODULE_DEPS_PLACEHOLDER, "Cross-Module Dependencies", fenced_text
    )


def _replace_entry_points_block(content: str, table_text: str) -> str:
    return _replace_or_substitute(
        content, _ENTRY_POINTS_PLACEHOLDER, "Entry Points", table_text
    )


def _replace_module_map_block(content: str, body_text: str) -> str:
    return _replace_or_substitute(
        content, _MODULE_MAP_PLACEHOLDER, "Module Map", body_text
    )


def _replace_application_routes_block(content: str, table_text: str) -> str:
    return _replace_or_substitute(
        content, _APPLICATION_ROUTES_PLACEHOLDER, "Application Routes", table_text
    )


def _replace_navigation_guards_block(content: str, list_text: str) -> str:
    return _replace_or_substitute(
        content, _NAVIGATION_GUARDS_PLACEHOLDER, "Navigation Guards", list_text
    )


def _replace_arch_overview_narrative_block(content: str, prose: str) -> str:
    return _replace_or_substitute(
        content, _ARCH_OVERVIEW_NARRATIVE_PLACEHOLDER, "Architecture Overview", prose
    )


def _replace_module_structure_block(content: str, fenced_text: str) -> str:
    return _replace_or_substitute(
        content, _MODULE_STRUCTURE_PLACEHOLDER, "Module / Package Structure", fenced_text
    )


def _replace_arch_patterns_block(content: str, body_text: str) -> str:
    return _replace_or_substitute(
        content, _ARCH_PATTERNS_PLACEHOLDER, "Patterns", body_text
    )


def _replace_conventions_block(content: str, body_text: str) -> str:
    return _replace_or_substitute(
        content, _CONVENTIONS_PLACEHOLDER, "Conventions", body_text
    )


def _replace_dep_direction_rules_block(content: str, body_text: str) -> str:
    return _replace_or_substitute(
        content, _DEP_DIRECTION_RULES_PLACEHOLDER, "Dependency Direction Rules", body_text
    )


def _replace_dep_overview_mermaid_block(content: str, fenced_text: str) -> str:
    return _replace_or_substitute(
        content, _DEP_OVERVIEW_MERMAID_PLACEHOLDER, "Dependency Overview", fenced_text
    )


# ── Concern-tier annotation interleaving ───────────────────────────────────


def _annotate_leaf_line(line: str, annotations: Dict[str, str]) -> str:
    if _ANNOTATION_SEPARATOR in line:
        return line
    for connector in _LEAF_CONNECTORS:
        idx = line.rfind(connector)
        if idx < 0:
            continue
        tail = line[idx + len(connector):].rstrip()
        if not tail or tail in _CANONICAL_AGGREGATORS:
            return line
        if "." not in tail:
            return line
        annotation = annotations.get(tail)
        if not annotation:
            return line
        return f"{line.rstrip()}{_ANNOTATION_SEPARATOR}{annotation.strip()}"
    return line


def _interleave_annotations(content: str, annotations: Dict[str, str]) -> str:
    out: List[str] = []
    in_fence = False
    for line in content.split("\n"):
        if not in_fence and line.strip() == _TREE_FENCE_OPEN:
            in_fence = True
            out.append(line)
            continue
        if in_fence and line.strip() == _TREE_FENCE_CLOSE:
            in_fence = False
            out.append(line)
            continue
        if in_fence:
            out.append(_annotate_leaf_line(line, annotations))
        else:
            out.append(line)
    return "\n".join(out)


# ── Bullet-list builders ───────────────────────────────────────────────────


def _render_concerns_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, role[, cite]} → '- <name> — <role>; <cite>'."""
    lines: List[str] = []
    for e in entries:
        name = (e.get("name") or "").strip()
        role = (e.get("role") or "").strip()
        cite = (e.get("cite") or "").strip()
        if not name:
            continue
        line = f"- {name}"
        if role:
            line += f" — {role}"
        if cite:
            line += f"; {cite}"
        lines.append(line)
    return "\n".join(lines)


def _render_layers_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, role, cite} → '- <name> — <role>; <cite>'."""
    return _render_concerns_bullets(entries)


def _render_files_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, role[, cite]} → '- <name> — <role>; <cite>'.

    Same shape as concerns; cite is the project-relative file path
    (e.g. <pkg>/src/<basename>) and is optional — basenames alone are
    self-locating since they live at the package's src/ root.
    """
    return _render_concerns_bullets(entries)


def _render_patterns_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, rule, cite} → '- <name> — <rule>; <cite>'."""
    lines: List[str] = []
    for e in entries:
        name = (e.get("name") or "").strip()
        rule = (e.get("rule") or "").strip()
        cite = (e.get("cite") or "").strip()
        if not name:
            continue
        line = f"- {name}"
        if rule:
            line += f" — {rule}"
        if cite:
            line += f"; {cite}"
        lines.append(line)
    return "\n".join(lines)


def _render_subconcerns_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, purpose_summary, doc_path} →
    '- <name> — <purpose_summary> ([→](<doc_path>))'.

    Plan F 3a: parent concern doc lists each split sub_concern with a
    1-line summary + link to its child index.md. ALL THREE fields
    (name, purpose_summary, doc_path) are required — entries missing
    any of them are skipped silently. The 3a.5 validate-doc parser
    expects the full ``<name> — <summary> ([→](<path>))`` shape; partial
    bullets would fail that regex, so we don't emit them at all.
    """
    lines: List[str] = []
    for e in entries:
        name = (e.get("name") or "").strip()
        summary = (e.get("purpose_summary") or "").strip()
        doc_path = (e.get("doc_path") or "").strip()
        if not (name and summary and doc_path):
            continue
        lines.append(f"- {name} — {summary} ([→]({doc_path}))")
    return "\n".join(lines)


# ── Track 4 Phase 1 — project-overview mechanical render helpers ───────────


def _render_tech_stack_table(entries: List[Dict[str, str]]) -> str:
    """Each entry: {layer, technology} → markdown table row."""
    lines = ["| Layer | Technology |", "|---|---|"]
    for e in entries:
        layer = (e.get("layer") or "").strip()
        tech = (e.get("technology") or "").strip()
        if not (layer and tech):
            continue
        lines.append(f"| {layer} | {tech} |")
    return "\n".join(lines)


def _render_key_commands_table(entries: List[Dict[str, str]]) -> str:
    """Each entry: {command, description} → markdown table row.

    Command cell wrapped in backticks for shell-style rendering. Description
    is empty-string-tolerant; absent description renders as empty cell.
    """
    lines = ["| Command | Description |", "|---|---|"]
    for e in entries:
        cmd = (e.get("command") or "").strip()
        desc = (e.get("description") or "").strip()
        if not cmd:
            continue
        lines.append(f"| `{cmd}` | {desc} |")
    return "\n".join(lines)


def _render_test_files_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {path[, description]} → '- `<path>` — <description>'."""
    lines: List[str] = []
    for e in entries:
        path = (e.get("path") or "").strip()
        desc = (e.get("description") or "").strip()
        if not path:
            continue
        line = f"- `{path}`"
        if desc:
            line += f" — {desc}"
        lines.append(line)
    return "\n".join(lines)


def _render_fenced_text(text: str, language: str = "text") -> str:
    """Wrap text in a fenced code block. Default language tag is `text`."""
    body = text.rstrip("\n")
    return f"```{language}\n{body}\n```"


# ── Track 4 Phase 2 — mixed mechanical+LLM render helpers ──────────────────


def _render_entry_points_table(entries: List[Dict[str, str]]) -> str:
    """Each entry: {label, path, purpose} → table row.

    Path cell wrapped in backticks. Skip rows missing label OR path; allow
    empty purpose (renders as empty cell).
    """
    lines = ["| Entry Point | Path | Purpose |", "|---|---|---|"]
    for e in entries:
        label = (e.get("label") or "").strip()
        path = (e.get("path") or "").strip()
        purpose = (e.get("purpose") or "").strip()
        if not (label and path):
            continue
        lines.append(f"| {label} | `{path}` | {purpose} |")
    return "\n".join(lines)


def _render_application_routes_table(entries: List[Dict[str, str]]) -> str:
    """Each entry: {path, component, description} → table row.

    Path + component cells in backticks. Skip rows missing path.
    """
    lines = ["| Route | Component | Description |", "|---|---|---|"]
    for e in entries:
        path = (e.get("path") or "").strip()
        component = (e.get("component") or "").strip()
        description = (e.get("description") or "").strip()
        if not path:
            continue
        component_cell = f"`{component}`" if component else ""
        lines.append(f"| `{path}` | {component_cell} | {description} |")
    return "\n".join(lines)


def _render_navigation_guards_list(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, role} → numbered list item.

    Format: `1. **<name>** — <role>`. The `**bold**` matches cse-strata bar
    convention. Numbering reflects guard chain order from input.
    """
    lines: List[str] = []
    for i, e in enumerate(entries, start=1):
        name = (e.get("name") or "").strip()
        role = (e.get("role") or "").strip()
        if not name:
            continue
        line = f"{i}. **{name}**"
        if role:
            line += f" — {role}"
        lines.append(line)
    return "\n".join(lines)


def _render_module_map_sections(entries: Dict[str, List[Dict[str, str]]]) -> str:
    """Three sub-sections (Infrastructure / Core / Domain), each a Package table.

    Input dict: {"infrastructure": [...], "core": [...], "domain": [...]}.
    Each list entry: {name, purpose}. Sub-sections with empty lists are
    omitted entirely (cleaner render than empty headers).

    Sub-headings emit as `### Infrastructure Packages` etc., matching
    cse-strata bar literal style.
    """
    section_order = (
        ("infrastructure", "Infrastructure Packages"),
        ("core", "Core Package"),
        ("domain", "Domain Packages"),
    )
    blocks: List[str] = []
    for key, heading in section_order:
        items = entries.get(key) or []
        if not items:
            continue
        block_lines = [f"### {heading}", "", "| Package | Purpose |", "|---|---|"]
        for item in items:
            name = (item.get("name") or "").strip()
            purpose = (item.get("purpose") or "").strip()
            if not name:
                continue
            block_lines.append(f"| `{name}` | {purpose} |")
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)


def _annotate_dir_line(line: str, annotations: Dict[str, str]) -> str:
    """Augment a project-structure tree line with an annotation comment.

    Matches lines ending with `<dirname>/` (project tree dirs) — a project-
    structure tree annotates DIRECTORIES (e.g. `apps/` → "Vue 3 SPA shell"),
    where concern-tier `_annotate_leaf_line` annotates FILES. Returns the
    line unchanged when:
      - it already has an annotation (`  # ` separator present)
      - no `├──` / `└──` connector
      - the entry doesn't end with `/` (skip files in mixed trees)
      - no annotation registered for the dir basename
    """
    if _ANNOTATION_SEPARATOR in line:
        return line
    for connector in _LEAF_CONNECTORS:
        idx = line.rfind(connector)
        if idx < 0:
            continue
        tail = line[idx + len(connector):].rstrip()
        if not tail or not tail.endswith("/"):
            return line
        # Strip trailing "/" for annotations dict lookup; users register by
        # directory basename, not the rendered "name/" form.
        basename = tail.rstrip("/")
        if not basename:
            return line
        annotation = annotations.get(basename)
        if not annotation:
            return line
        return f"{line.rstrip()}{_ANNOTATION_SEPARATOR}{annotation.strip()}"
    return line


# ── Track 4 Phase 3 — architecture-tier render helpers ──────────────────────


def _render_arch_patterns_subsections(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, applies_in, rule, language, code_snippet, cite} →
    `### <name>` heading + applies-in line + rule prose + cite-back HTML
    comment + fenced code block.

    Skip entries missing `name`; allow any other field empty (renders that
    part as absent rather than failing). The cite-back HTML comment uses
    the format `<!-- <cite> -->` mirroring concern + package tier convention.
    """
    blocks: List[str] = []
    for e in entries:
        name = (e.get("name") or "").strip()
        applies_in = (e.get("applies_in") or "").strip()
        rule = (e.get("rule") or "").strip()
        language = (e.get("language") or "").strip()
        snippet = (e.get("code_snippet") or "").rstrip()
        cite = (e.get("cite") or "").strip()
        if not name:
            continue
        block_lines = [f"### {name}"]
        if applies_in:
            block_lines.append("")
            block_lines.append(f"**Applies in**: {applies_in}")
        if rule:
            block_lines.append("")
            block_lines.append(rule)
        if snippet:
            block_lines.append("")
            if cite:
                block_lines.append(f"<!-- {cite} -->")
            fence_lang = language or "text"
            block_lines.append(f"```{fence_lang}")
            block_lines.append(snippet)
            block_lines.append("```")
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)


def _render_conventions_subsections(entries: Dict[str, List[str]]) -> str:
    """Render 4 sub-sections: Naming, File Organization, Import Style, Error Handling.

    Input dict: each key maps to list of bullet-point strings. Sub-sections
    with empty lists are omitted. Sub-headings use `**bold**` paragraph form
    (cse-strata bar literal style: `**Naming**\\n- bullet\\n...`).
    """
    section_order = (
        ("naming", "Naming"),
        ("file_organization", "File Organization"),
        ("import_style", "Import Style"),
        ("error_handling", "Error Handling"),
    )
    blocks: List[str] = []
    for key, heading in section_order:
        items = entries.get(key) or []
        if not items:
            continue
        block_lines = [f"**{heading}**"]
        for item in items:
            text = str(item).strip()
            if not text:
                continue
            block_lines.append(f"- {text}")
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)


def _render_cross_cuts_detailed_subsections(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, description, language, code_snippet, cite} →
    `### <name>` heading + description prose + cite-back HTML comment +
    fenced code block.

    Phase 3 enriched shape supersedes Phase 0 Cross-Cuts bullet list when
    the orchestrator wants per-cross-cut code samples + cite-backs. Skip
    entries missing `name`.
    """
    blocks: List[str] = []
    for e in entries:
        name = (e.get("name") or "").strip()
        description = (e.get("description") or "").strip()
        language = (e.get("language") or "").strip()
        snippet = (e.get("code_snippet") or "").rstrip()
        cite = (e.get("cite") or "").strip()
        if not name:
            continue
        block_lines = [f"### {name}"]
        if description:
            block_lines.append("")
            block_lines.append(description)
        if snippet:
            block_lines.append("")
            if cite:
                block_lines.append(f"<!-- {cite} -->")
            fence_lang = language or "text"
            block_lines.append(f"```{fence_lang}")
            block_lines.append(snippet)
            block_lines.append("```")
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)


def _render_dep_direction_rules_bullets(entries: List[str]) -> str:
    """Each entry is a bullet-point rule string. Skip empty strings."""
    lines: List[str] = []
    for entry in entries:
        text = str(entry).strip()
        if not text:
            continue
        lines.append(f"- {text}")
    return "\n".join(lines)


def _interleave_dir_annotations(content: str, annotations: Dict[str, str]) -> str:
    """Walk the fenced ```text block and apply `_annotate_dir_line` per line.

    Same fenced-block boundary logic as `_interleave_annotations` but uses
    the dir variant for project structure (annotates directories, not files).
    """
    out: List[str] = []
    in_fence = False
    for line in content.split("\n"):
        if not in_fence and line.strip() == _TREE_FENCE_OPEN:
            in_fence = True
            out.append(line)
            continue
        if in_fence and line.strip() == _TREE_FENCE_CLOSE:
            in_fence = False
            out.append(line)
            continue
        if in_fence:
            out.append(_annotate_dir_line(line, annotations))
        else:
            out.append(line)
    return "\n".join(out)


# ── Subcommand handlers ─────────────────────────────────────────────────────


def cmd_init_doc(args: argparse.Namespace) -> int:
    if args.tier not in _VALID_TIERS:
        print(f"unknown tier {args.tier!r}", file=sys.stderr)
        return 2
    try:
        frontmatter = json.loads(args.frontmatter)
    except json.JSONDecodeError as exc:
        print(f"--frontmatter must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(frontmatter, dict):
        print("--frontmatter must decode to a JSON object", file=sys.stderr)
        return 2

    is_split = bool(getattr(args, "split", False))
    if is_split and args.tier != "concern":
        print(
            f"--split is only valid with tier=concern; got tier={args.tier!r}",
            file=sys.stderr,
        )
        return 2

    if args.tier == "concern":
        if is_split:
            # Parent concern doc: aggregator with Sub-concerns + Purpose.
            # NO `## Structure` (children carry their own trees) → --tree
            # is ignored when --split true.
            skeleton_text = _build_concern_split_skeleton(frontmatter)
        else:
            if not args.tree:
                print(
                    "--tree is required for tier=concern (pass concern-input's tree_text)",
                    file=sys.stderr,
                )
                return 2
            skeleton_text = _build_concern_skeleton(frontmatter, args.tree)
    elif args.tier == "package-overview":
        skeleton_text = _build_package_overview_skeleton(frontmatter)
    elif args.tier == "package-architecture":
        skeleton_text = _build_package_architecture_skeleton(frontmatter)
    elif args.tier == "project-overview":
        skeleton_text = _build_project_overview_skeleton(frontmatter, args.target)
    elif args.tier == "project-architecture":
        skeleton_text = _build_project_architecture_skeleton(frontmatter, args.target)
    else:  # pragma: no cover — guard above already filters
        print(f"unhandled tier {args.tier!r}", file=sys.stderr)
        return 2

    doc_path = _doc_path_for(args)

    # Project-tier docs may carry user/constitute-owned anchors alongside
    # generate-docs's own. Merge instead of wholesale-overwrite so those
    # anchors survive re-runs. Concern + package tiers are 100%
    # generate-docs territory — wholesale overwrite stays correct there.
    if args.tier == "project-overview":
        skeleton_text = _merge_project_skeleton(
            doc_path, skeleton_text, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
    elif args.tier == "project-architecture":
        skeleton_text = _merge_project_skeleton(
            doc_path, skeleton_text, _PROJECT_ARCHITECTURE_OWNED_ANCHORS
        )

    skel_path = _skeleton_path(doc_path)
    skel_path.parent.mkdir(parents=True, exist_ok=True)
    skel_path.write_text(skeleton_text, encoding="utf-8")
    if doc_path.is_file():
        doc_path.unlink()
    print(str(skel_path))
    return 0


def cmd_set_doc_purpose(args: argparse.Namespace) -> int:
    if args.tier not in ("concern", "package-overview", "project-overview"):
        print(
            f"set-doc-purpose supports tier in (concern, package-overview, project-overview); "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(
            f"no skeleton or doc at {doc_path} or {_skeleton_path(doc_path)} — run init-doc first",
            file=sys.stderr,
        )
        return 2
    new_content = _replace_purpose_block(content, args.text)
    path.write_text(new_content, encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_structure(args: argparse.Namespace) -> int:
    if args.tier != "concern":
        print(
            f"set-doc-structure supports tier=concern only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    annotations: Dict[str, str] = {}
    if args.annotations:
        try:
            decoded = json.loads(args.annotations)
        except json.JSONDecodeError as exc:
            print(f"--annotations must be valid JSON: {exc}", file=sys.stderr)
            return 2
        if not isinstance(decoded, dict):
            print("--annotations must decode to a JSON object", file=sys.stderr)
            return 2
        annotations = {str(k): str(v) for k, v in decoded.items()}

    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(
            f"no skeleton or doc at {doc_path} — run init-doc first",
            file=sys.stderr,
        )
        return 2
    if _TREE_FENCE_OPEN not in content:
        print(
            f"no `{_TREE_FENCE_OPEN}` code fence in {path}; init-doc first",
            file=sys.stderr,
        )
        return 2
    new_content = _interleave_annotations(content, annotations)
    path.write_text(new_content, encoding="utf-8")
    print(str(path))
    return 0


def _decode_entry_list(arg_value: str, name: str) -> Optional[List[Dict[str, str]]]:
    """Decode a JSON list-of-objects argument; return None on parse failure (caller exits)."""
    try:
        decoded = json.loads(arg_value)
    except json.JSONDecodeError as exc:
        print(f"--{name} must be valid JSON: {exc}", file=sys.stderr)
        return None
    if not isinstance(decoded, list):
        print(f"--{name} must decode to a JSON array", file=sys.stderr)
        return None
    out: List[Dict[str, str]] = []
    for entry in decoded:
        if isinstance(entry, dict):
            out.append({k: str(v) for k, v in entry.items()})
    return out


def cmd_set_doc_concerns(args: argparse.Namespace) -> int:
    if args.tier != "package-overview":
        print(
            f"set-doc-concerns supports tier=package-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.concerns, "concerns")
    if entries is None:
        return 2
    bullet_text = _render_concerns_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_concerns_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_files(args: argparse.Namespace) -> int:
    if args.tier != "package-overview":
        print(
            f"set-doc-files supports tier=package-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.files, "files")
    if entries is None:
        return 2
    bullet_text = _render_files_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_files_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_layers(args: argparse.Namespace) -> int:
    if args.tier not in ("package-architecture", "project-architecture"):
        print(
            f"set-doc-layers supports tier in (package-architecture, project-architecture); "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.layers, "layers")
    if entries is None:
        return 2
    bullet_text = _render_layers_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_layers_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_patterns(args: argparse.Namespace) -> int:
    if args.tier != "package-architecture":
        print(
            f"set-doc-patterns supports tier=package-architecture only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.patterns, "patterns")
    if entries is None:
        return 2
    bullet_text = _render_patterns_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_patterns_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_packages(args: argparse.Namespace) -> int:
    if args.tier != "project-overview":
        print(
            f"set-doc-packages supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.packages, "packages")
    if entries is None:
        return 2
    bullet_text = _render_concerns_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_packages_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_cross_cuts(args: argparse.Namespace) -> int:
    if args.tier != "project-architecture":
        print(
            f"set-doc-cross-cuts supports tier=project-architecture only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.cross_cuts, "cross-cuts")
    if entries is None:
        return 2
    bullet_text = _render_concerns_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_cross_cuts_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_subconcerns(args: argparse.Namespace) -> int:
    """Plan F 3a: write the parent concern's `## Sub-concerns` bulleted list."""
    if args.tier != "concern":
        print(
            f"set-doc-subconcerns supports tier=concern only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.subconcerns, "subconcerns")
    if entries is None:
        return 2
    bullet_text = _render_subconcerns_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(
            f"no skeleton or doc at {doc_path} or {_skeleton_path(doc_path)} — "
            "run init-doc --split true first",
            file=sys.stderr,
        )
        return 2
    if "## Sub-concerns" not in content:
        print(
            f"{path} has no `## Sub-concerns` section — was init-doc called "
            "with --split true?",
            file=sys.stderr,
        )
        return 2
    path.write_text(_replace_subconcerns_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_tech_stack(args: argparse.Namespace) -> int:
    """Track 4 Phase 1 — write project-overview's `## Tech Stack` table."""
    if args.tier != "project-overview":
        print(
            f"set-overview-tech-stack supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.tech_stack, "tech-stack")
    if entries is None:
        return 2
    table_text = _render_tech_stack_table(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_tech_stack_block(content, table_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_key_commands(args: argparse.Namespace) -> int:
    """Track 4 Phase 1 — write project-overview's `## Key Commands` table."""
    if args.tier != "project-overview":
        print(
            f"set-overview-key-commands supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.key_commands, "key-commands")
    if entries is None:
        return 2
    table_text = _render_key_commands_table(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_key_commands_block(content, table_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_test_files(args: argparse.Namespace) -> int:
    """Track 4 Phase 1 — write project-overview's `## Test Files` bullets."""
    if args.tier != "project-overview":
        print(
            f"set-overview-test-files supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.test_files, "test-files")
    if entries is None:
        return 2
    bullet_text = _render_test_files_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_test_files_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_cross_module_deps(args: argparse.Namespace) -> int:
    """Track 4 Phase 1 — write project-overview's `## Cross-Module Dependencies` fenced block."""
    if args.tier != "project-overview":
        print(
            f"set-overview-cross-module-deps supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    fenced_text = _render_fenced_text(args.text)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_cross_module_deps_block(content, fenced_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_project_structure_tree(args: argparse.Namespace) -> int:
    """Track 4 Phase 1 — write project-overview's `## Project Structure` fenced block.

    Phase 1 writes the bare tree only — no per-leaf annotations. Phase 2
    will add a separate annotations setter that interleaves descriptions
    onto leaves of an already-set tree (mirrors concern-tier two-step
    set-doc-structure pattern).
    """
    if args.tier != "project-overview":
        print(
            f"set-overview-project-structure-tree supports tier=project-overview only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    fenced_text = _render_fenced_text(args.text)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_project_structure_block(content, fenced_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_entry_points(args: argparse.Namespace) -> int:
    """Track 4 Phase 2 — write project-overview's `## Entry Points` table."""
    if args.tier != "project-overview":
        print(
            f"set-overview-entry-points supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.entry_points, "entry-points")
    if entries is None:
        return 2
    table_text = _render_entry_points_table(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_entry_points_block(content, table_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_application_routes(args: argparse.Namespace) -> int:
    """Track 4 Phase 2 — write project-overview's `## Application Routes` table."""
    if args.tier != "project-overview":
        print(
            f"set-overview-application-routes supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.routes, "routes")
    if entries is None:
        return 2
    table_text = _render_application_routes_table(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_application_routes_block(content, table_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_navigation_guards(args: argparse.Namespace) -> int:
    """Track 4 Phase 2 — write project-overview's `## Navigation Guards` numbered list."""
    if args.tier != "project-overview":
        print(
            f"set-overview-navigation-guards supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.guards, "guards")
    if entries is None:
        return 2
    list_text = _render_navigation_guards_list(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_navigation_guards_block(content, list_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_module_map(args: argparse.Namespace) -> int:
    """Track 4 Phase 2 — write project-overview's `## Module Map` 3 sub-section tables."""
    if args.tier != "project-overview":
        print(
            f"set-overview-module-map supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    try:
        decoded = json.loads(args.modules)
    except json.JSONDecodeError as exc:
        print(f"--modules must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(decoded, dict):
        print("--modules must decode to a JSON object", file=sys.stderr)
        return 2
    # Coerce inner lists; skip any non-list value.
    sections: Dict[str, List[Dict[str, str]]] = {}
    for key in ("infrastructure", "core", "domain"):
        items = decoded.get(key)
        if isinstance(items, list):
            sections[key] = [
                {k: str(v) for k, v in item.items()}
                for item in items if isinstance(item, dict)
            ]
        else:
            sections[key] = []
    body_text = _render_module_map_sections(sections)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_module_map_block(content, body_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_project_structure_annotations(args: argparse.Namespace) -> int:
    """Track 4 Phase 2 — augment Phase 1 tree leaves with dir-level annotations.

    Mirrors concern-tier `set-doc-structure` mechanism but operates on
    directories (`<name>/` lines) not files. Phase 1 must have run first
    to plant the `## Project Structure` fenced tree; this setter walks
    the fence content and applies `<basename> → annotation` per leaf dir.
    Idempotent — re-applying overwrites any prior annotation when the
    annotation dict changes; lines not present in the dict are unchanged.
    """
    if args.tier != "project-overview":
        print(
            f"set-overview-project-structure-annotations supports tier=project-overview only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    annotations: Dict[str, str] = {}
    if args.annotations:
        try:
            decoded = json.loads(args.annotations)
        except json.JSONDecodeError as exc:
            print(f"--annotations must be valid JSON: {exc}", file=sys.stderr)
            return 2
        if not isinstance(decoded, dict):
            print("--annotations must decode to a JSON object", file=sys.stderr)
            return 2
        annotations = {str(k): str(v) for k, v in decoded.items()}

    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    if _TREE_FENCE_OPEN not in content:
        print(
            f"no `{_TREE_FENCE_OPEN}` code fence in {path}; "
            f"run set-overview-project-structure-tree first",
            file=sys.stderr,
        )
        return 2
    path.write_text(_interleave_dir_annotations(content, annotations), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_overview_narrative(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write project-architecture's `## Architecture Overview`."""
    if args.tier != "project-architecture":
        print(
            f"set-architecture-overview-narrative supports tier=project-architecture only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_arch_overview_narrative_block(content, args.text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_module_structure(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write project-architecture's `## Module / Package Structure` fenced tree."""
    if args.tier != "project-architecture":
        print(
            f"set-architecture-module-structure supports tier=project-architecture only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    fenced_text = _render_fenced_text(args.text)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_module_structure_block(content, fenced_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_patterns(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write project-architecture's `## Patterns` subsections."""
    if args.tier != "project-architecture":
        print(
            f"set-architecture-patterns supports tier=project-architecture only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.patterns, "patterns")
    if entries is None:
        return 2
    body_text = _render_arch_patterns_subsections(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_arch_patterns_block(content, body_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_conventions(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write project-architecture's `## Conventions` 4 sub-sections.

    Note: this setter targets the project-architecture tier ONLY; do not
    confuse with the package-architecture tier's `set-doc-patterns`.
    """
    if args.tier != "project-architecture":
        print(
            f"set-architecture-conventions supports tier=project-architecture only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    try:
        decoded = json.loads(args.conventions)
    except json.JSONDecodeError as exc:
        print(f"--conventions must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(decoded, dict):
        print("--conventions must decode to a JSON object", file=sys.stderr)
        return 2
    sections: Dict[str, List[str]] = {}
    for key in ("naming", "file_organization", "import_style", "error_handling"):
        items = decoded.get(key)
        if isinstance(items, list):
            sections[key] = [str(x) for x in items]
        else:
            sections[key] = []
    body_text = _render_conventions_subsections(sections)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_conventions_block(content, body_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_cross_cuts_detailed(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write enriched `## Cross-Cuts` (subsections + code snippets).

    Replaces the existing `## Cross-Cuts` body. Phase 0 callers using the
    bullet-list `set-doc-cross-cuts` setter remain functional; this setter
    targets richer per-cross-cut subsections with cite-backed code samples.
    """
    if args.tier != "project-architecture":
        print(
            f"set-architecture-cross-cuts-detailed supports tier=project-architecture only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.cross_cuts, "cross-cuts")
    if entries is None:
        return 2
    body_text = _render_cross_cuts_detailed_subsections(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_cross_cuts_block(content, body_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_dependency_direction_rules(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write `## Dependency Direction Rules` bullets."""
    if args.tier != "project-architecture":
        print(
            f"set-architecture-dependency-direction-rules supports tier=project-architecture only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    try:
        decoded = json.loads(args.rules)
    except json.JSONDecodeError as exc:
        print(f"--rules must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(decoded, list):
        print("--rules must decode to a JSON array", file=sys.stderr)
        return 2
    body_text = _render_dep_direction_rules_bullets(decoded)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_dep_direction_rules_block(content, body_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_dependency_overview_mermaid(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write `## Dependency Overview` fenced ```mermaid block.

    Mechanical input — orchestrator passes either project-input's
    `dep_graph_mermaid` verbatim OR an LLM-curated mermaid graph. Helper
    wraps as fenced ```mermaid block; markdown viewers render the diagram
    natively. No Python mermaid renderer dep.
    """
    if args.tier != "project-architecture":
        print(
            f"set-architecture-dependency-overview-mermaid supports tier=project-architecture only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    fenced_text = _render_fenced_text(args.text, language="mermaid")
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_dep_overview_mermaid_block(content, fenced_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_render_doc(args: argparse.Namespace) -> int:
    if args.tier not in _VALID_TIERS:
        print(f"unknown tier {args.tier!r}", file=sys.stderr)
        return 2
    doc_path = _doc_path_for(args)
    if args.out:
        doc_path = Path(args.out)
    skel_path = _skeleton_path(doc_path)
    if not skel_path.is_file():
        print(f"no skeleton at {skel_path} — run init-doc first", file=sys.stderr)
        return 2
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(str(skel_path), str(doc_path))
    print(str(doc_path))
    return 0


# ── argparse factories ──────────────────────────────────────────────────────


def _common_target_args(p: argparse.ArgumentParser, tiers: Tuple[str, ...]) -> None:
    p.add_argument("--tier", required=True, choices=tiers)
    p.add_argument("--target", required=True)
    p.add_argument("--devforge-dir", default=".devforge")


def _build_init_doc(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, _VALID_TIERS)
    p.add_argument("--frontmatter", required=True, help="JSON object of frontmatter key/value pairs")
    p.add_argument(
        "--tree",
        default="",
        help="ASCII tree text (REQUIRED for tier=concern unless --split true)",
    )
    p.add_argument(
        "--split",
        action="store_true",
        help=(
            "tier=concern only: emit parent-aggregator skeleton (Purpose + "
            "Sub-concerns; no Structure). Used by Plan F 3a split-dispatch."
        ),
    )


def _build_set_doc_purpose(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("concern", "package-overview", "project-overview"))
    p.add_argument("--text", required=True)


def _build_set_doc_structure(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("concern",))
    p.add_argument(
        "--annotations",
        default="",
        help="JSON object {leaf_basename: annotation_text}",
    )


def _build_set_doc_concerns(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("package-overview",))
    p.add_argument(
        "--concerns",
        required=True,
        help='JSON array [{"name": "...", "role": "...", "cite": "..."}]',
    )


def _build_set_doc_files(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("package-overview",))
    p.add_argument(
        "--files",
        required=True,
        help='JSON array [{"name": "<basename>", "role": "...", "cite": "..."}]',
    )


def _build_set_doc_layers(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("package-architecture", "project-architecture"))
    p.add_argument(
        "--layers",
        required=True,
        help='JSON array [{"name": "...", "role": "...", "cite": "..."}]',
    )


def _build_set_doc_patterns(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("package-architecture",))
    p.add_argument(
        "--patterns",
        required=True,
        help='JSON array [{"name": "...", "rule": "...", "cite": "..."}]',
    )


def _build_set_doc_packages(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--packages",
        required=True,
        help='JSON array [{"name": "<pkg-path>", "role": "...", "cite": "..."}]',
    )


def _build_set_doc_cross_cuts(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--cross-cuts",
        dest="cross_cuts",
        required=True,
        help='JSON array [{"name": "...", "role": "...", "cite": "..."}]',
    )


def _build_set_doc_subconcerns(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("concern",))
    p.add_argument(
        "--subconcerns",
        required=True,
        help=(
            'JSON array [{"name": "<>", "purpose_summary": "<>", '
            '"doc_path": "<rel-path-to-child-index.md>"}]'
        ),
    )


def _build_render_doc(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, _VALID_TIERS)
    p.add_argument(
        "--out",
        default="",
        help="Output path override (default: docs/<target>/<tier-filename>)",
    )


# ── Track 4 Phase 1 — project-overview mechanical setter factories ─────────


def _build_set_overview_tech_stack(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--tech-stack",
        dest="tech_stack",
        required=True,
        help='JSON array [{"layer": "Framework", "technology": "Vue 3"}]',
    )


def _build_set_overview_key_commands(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--key-commands",
        dest="key_commands",
        required=True,
        help='JSON array [{"command": "npm run build", "description": "..."}]',
    )


def _build_set_overview_test_files(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--test-files",
        dest="test_files",
        required=True,
        help='JSON array [{"path": "tests/", "description": "..."}]',
    )


def _build_set_overview_cross_module_deps(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--text",
        required=True,
        help="ASCII tree text rendering the cross-package dependency graph",
    )


def _build_set_overview_project_structure_tree(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--text",
        required=True,
        help="ASCII tree text of project structure (no annotations — Phase 1 bare tree)",
    )


# ── Track 4 Phase 2 — mixed mechanical+LLM setter factories ─────────────────


def _build_set_overview_entry_points(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--entry-points",
        dest="entry_points",
        required=True,
        help='JSON array [{"label": "App entry", "path": "src/main.ts", "purpose": "..."}]',
    )


def _build_set_overview_application_routes(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--routes",
        required=True,
        help='JSON array [{"path": "/quote", "component": "PageQuote.vue", "description": "..."}]',
    )


def _build_set_overview_navigation_guards(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--guards",
        required=True,
        help='JSON array [{"name": "oktaGuard", "role": "Checks Okta auth state"}]',
    )


def _build_set_overview_module_map(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--modules",
        required=True,
        help=(
            'JSON object {"infrastructure": [{name, purpose}], '
            '"core": [...], "domain": [...]}'
        ),
    )


def _build_set_overview_project_structure_annotations(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--annotations",
        default="",
        help='JSON object {dir_basename: annotation_text} — augments Phase 1 tree leaves',
    )


# ── Track 4 Phase 3 — architecture-tier setter factories ────────────────────


def _build_set_architecture_overview_narrative(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--text",
        required=True,
        help="Multi-paragraph narrative describing the architectural shape",
    )


def _build_set_architecture_module_structure(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--text",
        required=True,
        help="Annotated tree (project-architecture variant) — fenced text block",
    )


def _build_set_architecture_patterns(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--patterns",
        required=True,
        help=(
            'JSON array [{"name": "...", "applies_in": "...", "rule": "...", '
            '"language": "typescript", "code_snippet": "...", "cite": "<file>:<line>"}]'
        ),
    )


def _build_set_architecture_conventions(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--conventions",
        required=True,
        help=(
            'JSON object {"naming": [bullets], "file_organization": [bullets], '
            '"import_style": [bullets], "error_handling": [bullets]}'
        ),
    )


def _build_set_architecture_cross_cuts_detailed(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--cross-cuts",
        dest="cross_cuts",
        required=True,
        help=(
            'JSON array [{"name": "...", "description": "...", '
            '"language": "...", "code_snippet": "...", "cite": "<file>:<line>"}]'
        ),
    )


def _build_set_architecture_dependency_direction_rules(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--rules",
        required=True,
        help='JSON array of bullet-point rule strings',
    )


def _build_set_architecture_dependency_overview_mermaid(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--text",
        required=True,
        help='Mermaid graph syntax (e.g. `graph TD\\n  a-->b`); helper wraps in ```mermaid fence',
    )
