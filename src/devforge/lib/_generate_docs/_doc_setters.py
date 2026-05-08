"""F.4 — multi-tier skeleton-fill primitives + render-doc.

Subcommands:

  init-doc          --tier {concern,package-overview,package-architecture}
                    --target T --frontmatter <json> [--tree <text>]
  set-doc-purpose   --tier {concern,package-overview} --target T --text "..."
  set-doc-structure --tier concern --target T --annotations <json>
  set-doc-concerns  --tier package-overview --target T --concerns <json>
  set-doc-layers    --tier package-architecture --target T --layers <json>
  set-doc-patterns  --tier package-architecture --target T --patterns <json>
  render-doc        --tier T --target T [--out PATH]

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

from ._md_frontmatter import render_frontmatter

_PURPOSE_PLACEHOLDER = "<!-- TODO: purpose -->"
_CONCERNS_PLACEHOLDER = "<!-- TODO: concerns -->"
_FILES_PLACEHOLDER = "<!-- TODO: files -->"
_LAYERS_PLACEHOLDER = "<!-- TODO: layers -->"
_PATTERNS_PLACEHOLDER = "<!-- TODO: patterns -->"
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

_VALID_TIERS = ("concern", "package-overview", "package-architecture")

_TIER_DOC_FILENAMES: Dict[str, str] = {
    "concern": "index.md",
    "package-overview": "overview.md",
    "package-architecture": "architecture.md",
}


# ── Path resolution ─────────────────────────────────────────────────────────


def _doc_path_for(args: argparse.Namespace) -> Path:
    """Resolve the doc path: docs/<target>/<tier-specific-filename>."""
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()
    filename = _TIER_DOC_FILENAMES.get(args.tier, "index.md")
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


def _replace_layers_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _LAYERS_PLACEHOLDER, "Layers", bullet_text)


def _replace_patterns_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _PATTERNS_PLACEHOLDER, "Patterns", bullet_text)


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

    if args.tier == "concern":
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
    else:  # pragma: no cover — guard above already filters
        print(f"unhandled tier {args.tier!r}", file=sys.stderr)
        return 2

    doc_path = _doc_path_for(args)
    skel_path = _skeleton_path(doc_path)
    skel_path.parent.mkdir(parents=True, exist_ok=True)
    skel_path.write_text(skeleton_text, encoding="utf-8")
    if doc_path.is_file():
        doc_path.unlink()
    print(str(skel_path))
    return 0


def cmd_set_doc_purpose(args: argparse.Namespace) -> int:
    if args.tier not in ("concern", "package-overview"):
        print(
            f"set-doc-purpose supports tier in (concern, package-overview); got {args.tier!r}",
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
    if args.tier != "package-architecture":
        print(
            f"set-doc-layers supports tier=package-architecture only; got {args.tier!r}",
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
    p.add_argument("--tree", default="", help="ASCII tree text (REQUIRED for tier=concern)")


def _build_set_doc_purpose(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("concern", "package-overview"))
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
    _common_target_args(p, ("package-architecture",))
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


def _build_render_doc(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, _VALID_TIERS)
    p.add_argument(
        "--out",
        default="",
        help="Output path override (default: docs/<target>/<tier-filename>)",
    )
