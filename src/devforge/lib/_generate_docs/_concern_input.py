"""F.2 — concern-input helper.

Walks the concern's source subfolder on disk, emits batch JSON for the
doc-composer agent dispatch under /generate-docs Phase 3 (Plan F).

Why filesystem and not index.json: /init-forge's index.json caps file lists
at 500 entries per package (`files_truncated: true` flag). On real
monorepos (testForge20 app-web hits the cap), the helpers/ subfolder falls
past the cap and would be invisible to a fully indexed.json-driven helper.
The trivial-leaf skip rule (`_path_contains_trivial_dir`) is applied during
the walk so node_modules/dist/etc. stay excluded.

Output shape:
    {
      "concern": "<name>",
      "package": "<package-path>",
      "subfolder": "src/<concern>/",
      "tree_text": "<ASCII tree, subfolder-relative>",
      "files": [{"path": "<project-rel>", "comment_rich_span": "<...>"}, ...],
      "source_stamp": "<sha256-prefix-16>"
    }

The tree_text is mechanical (built from index.json file list, trivial-leaf
dirs excluded). Each file's `comment_rich_span` carries the top of the file
plus any TODO/FIXME/HACK/WARNING context with surrounding lines, capped at
6 KB per file and 60 KB per batch. Vue files are read verbatim from `.vue`
source (NOT the `.devforge/vue-tmp/*.vue.ts` mirror) — template hazards are
only visible in the source.

`source_stamp` is a SHA-256 prefix over sorted (path, content_hash) pairs;
F.4 uses it for incremental skip when re-running /generate-docs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ._setters_concern import _path_contains_trivial_dir

_PER_FILE_SPAN_CAP = 6 * 1024
_BATCH_SPAN_CAP = 60 * 1024
_TOP_LINE_COUNT = 30
_HAZARD_MARKERS = ("TODO", "FIXME", "HACK", "WARNING", "XXX")
_HAZARD_CONTEXT_BEFORE = 2
_HAZARD_CONTEXT_AFTER = 2


def _build_tree(concern_files: List[str], subfolder_prefix: str) -> str:
    """Build an ASCII tree from project-relative paths under subfolder_prefix.

    The first line is the subfolder header (e.g., `src/order/`). Subsequent
    lines use box-drawing connectors (├──/└──/│) with directories grouped
    above leaves at each level.
    """
    rels = sorted(
        {f[len(subfolder_prefix):] for f in concern_files if f.startswith(subfolder_prefix)}
    )
    root: Dict[str, object] = {}
    for rel in rels:
        parts = rel.split("/")
        node: Dict[str, object] = root
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        node[parts[-1]] = None  # leaf marker

    out_lines = [subfolder_prefix.rstrip("/") + "/"]

    def _walk(branch: Dict[str, object], prefix: str) -> None:
        # Directories before leaves; alphabetical within each group.
        items = sorted(
            branch.items(),
            key=lambda kv: (kv[1] is None, kv[0]),
        )
        for i, (name, child) in enumerate(items):
            last = i == len(items) - 1
            connector = "└── " if last else "├── "
            out_lines.append(f"{prefix}{connector}{name}")
            if isinstance(child, dict):
                ext_prefix = prefix + ("    " if last else "│   ")
                _walk(child, ext_prefix)

    _walk(root, "")
    return "\n".join(out_lines)


def _extract_comment_rich_span(content: str, max_bytes: int) -> str:
    """Extract top-of-file + hazard-marker context, capped at max_bytes.

    Always returns top _TOP_LINE_COUNT lines. For each line beyond the top
    that contains a hazard marker (TODO/FIXME/HACK/WARNING/XXX), include
    a small context window. Overlapping windows merge. Output uses 1-based
    line numbers; gaps between non-adjacent windows are marked with `...`.
    """
    if not content:
        return ""
    lines = content.split("\n")
    n = len(lines)
    top_end = min(_TOP_LINE_COUNT, n)
    ranges: List[Tuple[int, int]] = [(0, top_end)]
    for idx, line in enumerate(lines):
        if idx < top_end:
            continue
        for marker in _HAZARD_MARKERS:
            if marker in line:
                start = max(0, idx - _HAZARD_CONTEXT_BEFORE)
                end = min(n, idx + _HAZARD_CONTEXT_AFTER + 1)
                ranges.append((start, end))
                break
    ranges.sort()
    merged: List[Tuple[int, int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    out: List[str] = []
    for i, (start, end) in enumerate(merged):
        if i > 0 and merged[i - 1][1] < start:
            out.append("...")
        for ln in range(start, end):
            out.append(f"{ln + 1:>4}: {lines[ln]}")
    span = "\n".join(out)
    if len(span.encode("utf-8")) > max_bytes:
        # Truncate at codepoint boundary near max_bytes.
        encoded = span.encode("utf-8")[:max_bytes]
        # Drop possibly-incomplete trailing UTF-8 byte sequence.
        try:
            span = encoded.decode("utf-8")
        except UnicodeDecodeError:
            span = encoded.decode("utf-8", errors="ignore")
        span = span.rstrip() + "\n...<file span truncated>"
    return span


def _build_spans_and_stamp(
    concern_files: List[str], project_root: Path
) -> Tuple[List[Dict[str, str]], str]:
    """Read each file, extract comment-rich span, compute aggregate stamp.

    Returns (file_records, source_stamp). source_stamp is the first 16 hex
    chars of SHA-256 over sorted `<rel>\\t<content_sha256>` lines. Stamp is
    deterministic across machines + reorderings.
    """
    file_records: List[Dict[str, str]] = []
    file_hashes: List[Tuple[str, str]] = []
    total_span_bytes = 0
    for rel in sorted(concern_files):
        abs_path = project_root / rel
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            file_hashes.append((rel, ""))
            file_records.append({"path": rel, "comment_rich_span": "<unreadable>"})
            continue
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        file_hashes.append((rel, content_hash))
        if total_span_bytes >= _BATCH_SPAN_CAP:
            file_records.append(
                {"path": rel, "comment_rich_span": "<...batch cap reached, span omitted...>"}
            )
            continue
        span = _extract_comment_rich_span(content, _PER_FILE_SPAN_CAP)
        total_span_bytes += len(span.encode("utf-8"))
        file_records.append({"path": rel, "comment_rich_span": span})

    stamp_input = "\n".join(f"{p}\t{h}" for p, h in sorted(file_hashes))
    source_stamp = hashlib.sha256(stamp_input.encode("utf-8")).hexdigest()[:16]
    return file_records, source_stamp


def _walk_concern_subfolder(
    project_root: Path, pkg: str, concern: str
) -> Tuple[Path, List[str]]:
    """Walk <project_root>/<pkg>/src/<concern>/ recursively.

    Returns (subfolder_abs, project_relative_paths). Files whose path
    contains a trivial-leaf directory (per `_path_contains_trivial_dir`)
    are skipped. Hidden dotfile-prefixed dirs are NOT skipped (callers
    supply --concern explicitly; not a wildcard scan).
    """
    subfolder_abs = (project_root / pkg / "src" / concern).resolve()
    rels: List[str] = []
    if not subfolder_abs.is_dir():
        return subfolder_abs, rels
    for path in sorted(subfolder_abs.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(project_root).as_posix()
        except ValueError:
            continue
        if _path_contains_trivial_dir(rel):
            continue
        rels.append(rel)
    return subfolder_abs, rels


def cmd_concern_input(args: argparse.Namespace) -> int:
    """Handler for `concern-input` subcommand. Returns CLI exit code."""
    devforge_dir = Path(args.devforge_dir)
    pkg = args.package
    concern = args.concern
    project_root = devforge_dir.parent.resolve()

    subfolder_abs, concern_files = _walk_concern_subfolder(project_root, pkg, concern)
    if not concern_files:
        if not subfolder_abs.is_dir():
            print(
                f"concern subfolder not found: {subfolder_abs} "
                f"(expected <project_root>/{pkg}/src/{concern}/)",
                file=sys.stderr,
            )
        else:
            print(
                f"concern {concern!r} subfolder is empty (or all files are "
                f"trivial-leaf): {subfolder_abs}",
                file=sys.stderr,
            )
        return 2

    subfolder_prefix = f"{pkg}/src/{concern}/"
    tree_text = _build_tree(concern_files, subfolder_prefix)
    spans, source_stamp = _build_spans_and_stamp(concern_files, project_root)

    output = {
        "concern": concern,
        "package": pkg,
        "subfolder": subfolder_prefix,
        "tree_text": tree_text,
        "files": spans,
        "source_stamp": source_stamp,
    }
    print(json.dumps(output, indent=2))
    return 0


def _build_concern_input(p: argparse.ArgumentParser) -> None:
    """argparse factory for the `concern-input` subcommand."""
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--devforge-dir", default=".devforge")
