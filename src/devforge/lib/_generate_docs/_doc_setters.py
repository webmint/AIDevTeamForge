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
    ("Key Commands", _KEY_COMMANDS_PLACEHOLDER),
    ("Cross-Module Dependencies", _CROSS_MODULE_DEPS_PLACEHOLDER),
    ("Test Files", _TEST_FILES_PLACEHOLDER),
    ("Packages", _PACKAGES_PLACEHOLDER),
)
_PROJECT_ARCHITECTURE_OWNED_ANCHORS: Tuple[Tuple[str, str], ...] = (
    ("Layers", _LAYERS_PLACEHOLDER),
    ("Cross-Cuts", _CROSS_CUTS_PLACEHOLDER),
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
    for anchor, placeholder in owned_anchors_with_placeholders:
        if f"## {anchor}\n" in body or f"## {anchor} " in body or body.endswith(f"## {anchor}"):
            body = _replace_or_substitute(body, placeholder, anchor, placeholder)
        else:
            body = body.rstrip("\n") + "\n\n" + f"## {anchor}\n\n{placeholder}"
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
        f"## Key Commands\n\n"
        f"{_KEY_COMMANDS_PLACEHOLDER}\n\n"
        f"## Cross-Module Dependencies\n\n"
        f"{_CROSS_MODULE_DEPS_PLACEHOLDER}\n\n"
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
        f"## Layers\n\n"
        f"{_LAYERS_PLACEHOLDER}\n\n"
        f"## Cross-Cuts\n\n"
        f"{_CROSS_CUTS_PLACEHOLDER}\n"
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
