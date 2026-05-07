"""F.4 — concern-tier skeleton-fill primitives + render-doc (v0).

Four CLI subcommands ship under this module:

- `init-doc        --tier concern --target T --frontmatter <json> --tree <tree_text>`
- `set-doc-purpose --tier concern --target T --text "..."`
- `set-doc-structure --tier concern --target T --annotations <json>`
- `render-doc      --tier concern --target T [--out PATH]`

Skeleton-fill design (replaces prior state-JSON approach):

1. `init-doc` writes `docs/<target>/index.md.skeleton` with frontmatter,
   `# <concern>` H1, `## Purpose` + placeholder marker, and `## Structure`
   + the F.2 tree_text wrapped in a `text` code fence. Re-running
   overwrites the skeleton wholesale.
2. `set-doc-purpose` reads the skeleton file in-place, replaces the
   `<!-- TODO: purpose -->` placeholder (or an already-filled Purpose
   section) with the supplied text.
3. `set-doc-structure` reads the skeleton in-place, walks the lines
   inside the ` ```text ` fence, and appends `  # <annotation>` to each
   leaf line whose basename matches an entry in `--annotations`.
   Idempotent: leaves already carrying `  # ` are skipped.
4. `render-doc` renames `<...>/index.md.skeleton` → `<...>/index.md`
   atomically. No content mutation.

The skeleton file IS the state. No `.f4-doc-state.json`. Helper owns
markdown structure (frontmatter, section anchors, code fence around
tree); orchestrator owns values (purpose text, leaf annotations).

Concern docs ship only `## Purpose` and `## Structure`. Hazards moved
to `/audit` (separate command).

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ._md_frontmatter import render_frontmatter

_PURPOSE_PLACEHOLDER = "<!-- TODO: purpose -->"
_TREE_FENCE_OPEN = "```text"
_TREE_FENCE_CLOSE = "```"
_ANNOTATION_SEPARATOR = "  # "  # two spaces + hash + space (matches cse-strata reference)
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


def _doc_path_for(args: argparse.Namespace) -> Path:
    """Resolve the doc skeleton/output path under <project_root>/docs/<target>/."""
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()
    return project_root / "docs" / args.target / "index.md"


def _build_skeleton(frontmatter: Dict[str, object], tree_text: str) -> str:
    """Render the full skeleton text: frontmatter + body."""
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


def _replace_purpose_block(content: str, new_text: str) -> str:
    """Replace either the placeholder OR an already-filled Purpose section."""
    new_text = new_text.strip()
    if _PURPOSE_PLACEHOLDER in content:
        return content.replace(_PURPOSE_PLACEHOLDER, new_text, 1)
    # Already filled — replace from `## Purpose\n\n` to next `## ` or EOF.
    pattern = re.compile(
        r"(## Purpose\n\n)(.*?)(\n## )",
        flags=re.DOTALL,
    )
    return pattern.sub(rf"\g<1>{new_text}\g<3>", content, count=1)


def _annotate_leaf_line(line: str, annotations: Dict[str, str]) -> str:
    """Append `  # <annotation>` to a leaf line if its basename is in `annotations`."""
    if _ANNOTATION_SEPARATOR in line:
        # Already annotated; pass through (idempotent).
        return line
    for connector in _LEAF_CONNECTORS:
        idx = line.rfind(connector)
        if idx < 0:
            continue
        tail = line[idx + len(connector):].rstrip()
        if not tail or tail in _CANONICAL_AGGREGATORS:
            return line
        # Heuristic leaf detection: tail must contain a `.` (file extension).
        if "." not in tail:
            return line
        annotation = annotations.get(tail)
        if not annotation:
            return line
        return f"{line.rstrip()}{_ANNOTATION_SEPARATOR}{annotation.strip()}"
    return line


def _interleave_annotations(content: str, annotations: Dict[str, str]) -> str:
    """Walk lines inside the ` ```text ` fence, annotate matching leaves."""
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


def _skeleton_path(doc_path: Path) -> Path:
    return doc_path.with_suffix(doc_path.suffix + ".skeleton")


def _load_active(doc_path: Path) -> Tuple[Optional[Path], Optional[str]]:
    """Return (path, content) for whichever of <doc>.md.skeleton or <doc>.md exists.

    Skeleton takes priority. Returns (None, None) when neither is present.
    """
    skel = _skeleton_path(doc_path)
    if skel.is_file():
        return skel, skel.read_text(encoding="utf-8")
    if doc_path.is_file():
        return doc_path, doc_path.read_text(encoding="utf-8")
    return None, None


# ── Subcommand handlers ─────────────────────────────────────────────────────


def cmd_init_doc(args: argparse.Namespace) -> int:
    """Render the doc skeleton with frontmatter + Purpose placeholder + fenced tree."""
    if args.tier != "concern":
        print(
            f"only tier=concern supported in this v0 (got tier={args.tier!r})",
            file=sys.stderr,
        )
        return 2
    try:
        frontmatter = json.loads(args.frontmatter)
    except json.JSONDecodeError as exc:
        print(f"--frontmatter must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(frontmatter, dict):
        print("--frontmatter must decode to a JSON object", file=sys.stderr)
        return 2
    if not args.tree:
        print("--tree is required (pass concern-input's tree_text verbatim)", file=sys.stderr)
        return 2

    doc_path = _doc_path_for(args)
    skel_path = _skeleton_path(doc_path)
    skel_path.parent.mkdir(parents=True, exist_ok=True)
    skel_path.write_text(_build_skeleton(frontmatter, args.tree), encoding="utf-8")

    # If a previous .md exists from an earlier render, blow it away — the
    # incoming run will produce a fresh one via render-doc.
    if doc_path.is_file():
        doc_path.unlink()

    print(str(skel_path))
    return 0


def cmd_set_doc_purpose(args: argparse.Namespace) -> int:
    if args.tier != "concern":
        print(f"only tier=concern supported (got {args.tier!r})", file=sys.stderr)
        return 2
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(
            f"no skeleton or doc found at {doc_path} or {_skeleton_path(doc_path)} "
            f"— run init-doc first",
            file=sys.stderr,
        )
        return 2
    new_content = _replace_purpose_block(content, args.text)
    path.write_text(new_content, encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_structure(args: argparse.Namespace) -> int:
    if args.tier != "concern":
        print(f"only tier=concern supported (got {args.tier!r})", file=sys.stderr)
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
            f"no skeleton or doc found at {doc_path} or {_skeleton_path(doc_path)} "
            f"— run init-doc first",
            file=sys.stderr,
        )
        return 2
    if _TREE_FENCE_OPEN not in content:
        print(
            f"no `{_TREE_FENCE_OPEN}` code fence found in {path}; "
            f"init-doc must run before set-doc-structure",
            file=sys.stderr,
        )
        return 2

    new_content = _interleave_annotations(content, annotations)
    path.write_text(new_content, encoding="utf-8")
    print(str(path))
    return 0


def cmd_render_doc(args: argparse.Namespace) -> int:
    """Atomic rename: <doc>.md.skeleton → <doc>.md."""
    if args.tier != "concern":
        print(f"only tier=concern supported (got {args.tier!r})", file=sys.stderr)
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


def _common_target_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--tier", required=True, choices=("concern",))
    p.add_argument("--target", required=True)
    p.add_argument("--devforge-dir", default=".devforge")


def _build_init_doc(p: argparse.ArgumentParser) -> None:
    _common_target_args(p)
    p.add_argument("--frontmatter", required=True, help="JSON object of frontmatter key/value pairs")
    p.add_argument("--tree", required=True, help="ASCII tree text (concern-input's tree_text verbatim)")


def _build_set_doc_purpose(p: argparse.ArgumentParser) -> None:
    _common_target_args(p)
    p.add_argument("--text", required=True)


def _build_set_doc_structure(p: argparse.ArgumentParser) -> None:
    _common_target_args(p)
    p.add_argument(
        "--annotations",
        default="",
        help="JSON object {leaf_basename: annotation_text}",
    )


def _build_render_doc(p: argparse.ArgumentParser) -> None:
    _common_target_args(p)
    p.add_argument(
        "--out",
        default="",
        help="Output path override (default: <project_root>/docs/<target>/index.md)",
    )
