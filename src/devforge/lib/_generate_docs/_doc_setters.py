"""F.4 — concern-tier setter primitives + render-doc (v0 vertical slice).

Four CLI subcommands ship under this module:

- `init-doc        --tier concern --target T --frontmatter <json>`
- `set-doc-purpose --tier concern --target T --text "..."`
- `set-doc-structure --tier concern --target T --tree "..." --annotations <json>`
- `render-doc      --tier concern --target T [--out PATH]`

Per-doc state lives at `<devforge_dir>/.f4-doc-state.json`. Setter calls
mutate the state slot for `<tier>:<target>` keyed entry; `render-doc`
emits the assembled Markdown to `docs/<target>/index.md` (or `--out`).

Helper owns markdown structure: frontmatter shape, section ordering,
tree-text + annotation interleaving. LLM owns values via the setters.
`validate-doc` (F.5) gates the rendered doc before it is final; this
helper does NOT auto-invoke validate.

Concern docs ship only `## Purpose` and `## Structure`. Hazards moved
to `/audit` (separate command). Concern tier only in this v0; package
+ project tier setters land under forthcoming F.4 expansion.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._md_frontmatter import render_frontmatter

_DOC_STATE_FILE = ".f4-doc-state.json"
_STATE_VERSION = 1
_CANONICAL_AGGREGATORS = (
    "mod.rs",
    "lib.rs",
    "__init__.py",
    "index.ts",
    "index.js",
    "doc.go",
)


def _state_path(devforge_dir: Path) -> Path:
    return devforge_dir / _DOC_STATE_FILE


def _load_state(devforge_dir: Path) -> Dict[str, Any]:
    path = _state_path(devforge_dir)
    if not path.exists():
        return {"version": _STATE_VERSION, "docs": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"f4-doc-state load failed: {exc}")
    if not isinstance(data, dict) or "docs" not in data:
        raise SystemExit("f4-doc-state malformed: missing 'docs' map")
    return data


def _save_state(devforge_dir: Path, state: Dict[str, Any]) -> None:
    path = _state_path(devforge_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _doc_key(tier: str, target: str) -> str:
    return f"{tier}:{target}"


def _ensure_concern_slot(
    state: Dict[str, Any], tier: str, target: str
) -> Dict[str, Any]:
    """Get-or-create the concern-tier slot in state. Pre-init defaults."""
    if tier != "concern":
        raise SystemExit(
            f"only tier=concern supported in this v0 (got tier={tier!r})"
        )
    key = _doc_key(tier, target)
    docs = state.setdefault("docs", {})
    slot = docs.get(key)
    if slot is None:
        slot = {
            "tier": tier,
            "target": target,
            "frontmatter": {},
            "sections": {
                "Purpose": "",
                "Structure": "",
            },
        }
        docs[key] = slot
    return slot


def _annotate_tree(tree_text: str, annotations: Dict[str, str]) -> str:
    """Append ` — <annotation>` to each leaf line of the tree.

    Tree leaves are box-drawing lines whose final entry name appears in
    the annotations map. Leaves whose name matches a canonical-aggregator
    filename get NO annotation (per F.3 spec). Header/path-line gets no
    annotation. Directory entries (lines whose name has a sub-tree below)
    get no annotation — heuristic: if the next non-empty line indented
    more than current line's leaf, treat as directory.
    """
    if not annotations:
        return tree_text
    out_lines: List[str] = []
    for line in tree_text.split("\n"):
        if " — " in line:
            # Already annotated; pass through verbatim (idempotent).
            out_lines.append(line)
            continue
        # Leaf detection: line must contain a connector (├── or └──).
        connector_idx = max(line.rfind("├── "), line.rfind("└── "))
        if connector_idx < 0:
            out_lines.append(line)
            continue
        name = line[connector_idx + 4 :].strip()
        if not name or name in _CANONICAL_AGGREGATORS:
            out_lines.append(line)
            continue
        annotation = annotations.get(name)
        if annotation:
            out_lines.append(f"{line} — {annotation}")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def _render_concern_doc(slot: Dict[str, Any]) -> str:
    """Assemble full Markdown for a concern-tier slot.

    Concern docs ship only ## Purpose + ## Structure. Hazards moved to
    /audit (separate command); not authored under /generate-docs.
    """
    frontmatter = dict(slot.get("frontmatter") or {})
    sections = slot.get("sections") or {}
    target = slot.get("target", "")
    concern_name = frontmatter.get("concern", target.split("/")[-1] if target else "")

    body_header = f"\n# {concern_name}\n\n"
    fm_block = render_frontmatter(frontmatter, body_header)

    parts: List[str] = [fm_block.rstrip("\n"), ""]
    purpose = (sections.get("Purpose") or "").strip()
    structure = (sections.get("Structure") or "").rstrip("\n")

    parts.append("## Purpose")
    parts.append(purpose if purpose else "(not yet authored)")
    parts.append("")
    parts.append("## Structure")
    parts.append(structure if structure else "(not yet authored)")
    parts.append("")

    return "\n".join(parts)


# ── Subcommand handlers ─────────────────────────────────────────────────────


def cmd_init_doc(args: argparse.Namespace) -> int:
    """Initialise (or RESET) a doc slot for `<tier>:<target>`.

    init-doc is idempotent: a re-run wipes any prior Purpose / Structure /
    Hazards content for the slot and replaces frontmatter wholesale. This
    is the contract that lets the orchestrator restart per-concern dispatch
    cycles without writing defensive state-cleanup itself.
    """
    devforge_dir = Path(args.devforge_dir)
    try:
        frontmatter = json.loads(args.frontmatter)
    except json.JSONDecodeError as exc:
        print(f"--frontmatter must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(frontmatter, dict):
        print("--frontmatter must decode to a JSON object", file=sys.stderr)
        return 2
    state = _load_state(devforge_dir)
    if args.tier != "concern":
        print(
            f"only tier=concern supported in this v0 (got tier={args.tier!r})",
            file=sys.stderr,
        )
        return 2
    key = _doc_key(args.tier, args.target)
    state.setdefault("docs", {})[key] = {
        "tier": args.tier,
        "target": args.target,
        "frontmatter": frontmatter,
        "sections": {
            "Purpose": "",
            "Structure": "",
        },
    }
    _save_state(devforge_dir, state)
    return 0


def cmd_set_doc_purpose(args: argparse.Namespace) -> int:
    devforge_dir = Path(args.devforge_dir)
    state = _load_state(devforge_dir)
    slot = _ensure_concern_slot(state, args.tier, args.target)
    slot["sections"]["Purpose"] = args.text
    _save_state(devforge_dir, state)
    return 0


def cmd_set_doc_structure(args: argparse.Namespace) -> int:
    devforge_dir = Path(args.devforge_dir)
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
    state = _load_state(devforge_dir)
    slot = _ensure_concern_slot(state, args.tier, args.target)
    slot["sections"]["Structure"] = _annotate_tree(args.tree, annotations)
    _save_state(devforge_dir, state)
    return 0


def cmd_render_doc(args: argparse.Namespace) -> int:
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()
    state = _load_state(devforge_dir)
    key = _doc_key(args.tier, args.target)
    slot = state.get("docs", {}).get(key)
    if slot is None:
        print(
            f"no state for {key!r}; call init-doc + setters before render-doc",
            file=sys.stderr,
        )
        return 2
    text = _render_concern_doc(slot)
    if args.out:
        out_path = Path(args.out)
    else:
        out_path = project_root / "docs" / args.target / "index.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(str(out_path))
    return 0


# ── argparse factories ──────────────────────────────────────────────────────


def _common_target_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--tier", required=True, choices=("concern",))
    p.add_argument("--target", required=True)
    p.add_argument("--devforge-dir", default=".devforge")


def _build_init_doc(p: argparse.ArgumentParser) -> None:
    _common_target_args(p)
    p.add_argument(
        "--frontmatter",
        required=True,
        help="JSON object of frontmatter key/value pairs",
    )


def _build_set_doc_purpose(p: argparse.ArgumentParser) -> None:
    _common_target_args(p)
    p.add_argument("--text", required=True)


def _build_set_doc_structure(p: argparse.ArgumentParser) -> None:
    _common_target_args(p)
    p.add_argument("--tree", required=True, help="Helper-supplied tree_text verbatim")
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
