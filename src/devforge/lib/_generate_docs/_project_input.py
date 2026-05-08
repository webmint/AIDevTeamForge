"""F.8a — project-input helper.

Walks `<project_root>/` and the project's already-rendered package
overview docs, emits batch JSON for the doc-composer dispatch under
/generate-docs Phase 4 (Plan F project tier).

Output shape:
    {
      "project": "<project-root-basename>",
      "package_seeds": [
        {"package": "<pkg-path>", "frontmatter": {...},
         "purpose_text": "<verbatim ## Purpose section content>"},
        ...
      ],
      "project_root_files": [
        {"path": "<file>", "comment_rich_span": "..."},
        ...
      ],
      "source_stamp": "<sha256-prefix-16>"
    }

`package_seeds` is the list the orchestrator uses to compose the
project overview's `## Packages` section AND inform the project
architecture's `## Layers` / `## Cross-Cuts` derivation.

Mirrors F.7a's shape one tier up: concern_seeds → package_seeds,
package_root_files → project_root_files, src_root_files dropped (not
relevant at project tier).

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._concern_input import _extract_comment_rich_span
from ._md_frontmatter import FrontmatterParseError, parse_frontmatter

_PER_FILE_SPAN_CAP = 6 * 1024
_BATCH_SPAN_CAP = 60 * 1024
_PROJECT_ROOT_FILES = (
    "README.md",
    "README.txt",
    "README",
    "CHANGELOG.md",
    "CHANGELOG.txt",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
)
_DOCS_DIR = "docs"


def _enumerate_packages_with_overviews(project_root: Path) -> List[str]:
    """List packages whose overview doc exists at docs/<pkg>/overview.md.

    Walks docs/ recursively for any `overview.md` file (excluding the
    project-tier docs/overview.md). Returns project-relative package
    paths (the dir under docs/ containing overview.md).
    """
    project_root = project_root.resolve()
    docs_dir = (project_root / _DOCS_DIR).resolve()
    if not docs_dir.is_dir():
        return []
    out: List[str] = []
    project_overview = docs_dir / "overview.md"
    for path in sorted(docs_dir.rglob("overview.md")):
        try:
            if path.resolve() == project_overview.resolve():
                continue
        except OSError:
            pass
        try:
            rel_dir = path.parent.resolve().relative_to(docs_dir).as_posix()
        except ValueError:
            continue
        if rel_dir and rel_dir != ".":
            out.append(rel_dir)
    return out


def _read_package_seed(
    project_root: Path, pkg: str
) -> Optional[Dict[str, Any]]:
    """Read frontmatter + Purpose section from a rendered package overview doc."""
    project_root = project_root.resolve()
    doc_path = project_root / _DOCS_DIR / pkg / "overview.md"
    if not doc_path.is_file():
        return None
    try:
        text = doc_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        record, body = parse_frontmatter(text)
    except FrontmatterParseError:
        return None
    purpose_lines: List[str] = []
    in_purpose = False
    for line in body.split("\n"):
        if line.startswith("## Purpose"):
            in_purpose = True
            continue
        if in_purpose and line.startswith("## "):
            break
        if in_purpose:
            purpose_lines.append(line)
    return {
        "package": pkg,
        "frontmatter": record,
        "purpose_text": "\n".join(purpose_lines).strip(),
    }


def _collect_project_root_files(
    project_root: Path,
) -> Tuple[List[Dict[str, str]], List[Tuple[str, str]]]:
    """Read top-level files at project_root (README, CHANGELOG, package.json, etc.)."""
    project_root = project_root.resolve()
    records: List[Dict[str, str]] = []
    hash_pairs: List[Tuple[str, str]] = []
    if not project_root.is_dir():
        return records, hash_pairs
    total_span_bytes = 0
    for filename in _PROJECT_ROOT_FILES:
        candidate = project_root / filename
        if not candidate.is_file():
            continue
        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = candidate.resolve().relative_to(project_root).as_posix()
        except ValueError:
            rel = candidate.as_posix()
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        hash_pairs.append((rel, content_hash))
        if total_span_bytes >= _BATCH_SPAN_CAP:
            records.append(
                {"path": rel, "comment_rich_span": "<...batch cap reached, span omitted...>"}
            )
            continue
        span = _extract_comment_rich_span(content, _PER_FILE_SPAN_CAP)
        total_span_bytes += len(span.encode("utf-8"))
        records.append({"path": rel, "comment_rich_span": span})
    return records, hash_pairs


def _compute_source_stamp(
    package_seeds: List[Dict[str, Any]],
    project_root_hashes: List[Tuple[str, str]],
) -> str:
    """Aggregate stamp over package source_stamps + project-root file hashes."""
    parts: List[str] = []
    for seed in package_seeds:
        fm = seed.get("frontmatter") or {}
        p = seed.get("package", "")
        s = fm.get("source_stamp", "")
        parts.append(f"package\t{p}\t{s}")
    for path, h in project_root_hashes:
        parts.append(f"root\t{path}\t{h}")
    parts.sort()
    blob = "\n".join(parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def cmd_project_input(args: argparse.Namespace) -> int:
    """Handler for `project-input` subcommand. Returns CLI exit code."""
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()

    pkg_paths = _enumerate_packages_with_overviews(project_root)
    if not pkg_paths:
        print(
            f"no package overviews found under {project_root / 'docs'} — "
            f"run /generate-docs through Phase 3 (package tier) first",
            file=sys.stderr,
        )
        return 2

    package_seeds: List[Dict[str, Any]] = []
    missing: List[str] = []
    for pkg in pkg_paths:
        seed = _read_package_seed(project_root, pkg)
        if seed is None:
            missing.append(pkg)
            continue
        package_seeds.append(seed)

    if not package_seeds:
        print(
            f"no readable package overviews under {project_root / 'docs'} "
            f"(every overview frontmatter parse failed)",
            file=sys.stderr,
        )
        return 2

    root_records, root_hashes = _collect_project_root_files(project_root)
    source_stamp = _compute_source_stamp(package_seeds, root_hashes)

    project_label = args.project or project_root.name
    output: Dict[str, Any] = {
        "project": project_label,
        "package_seeds": package_seeds,
        "project_root_files": root_records,
        "source_stamp": source_stamp,
    }
    if missing:
        output["missing_package_overviews"] = missing
    print(json.dumps(output, indent=2))
    return 0


def _build_project_input(p: argparse.ArgumentParser) -> None:
    """argparse factory for the `project-input` subcommand."""
    p.add_argument(
        "--project",
        default="",
        help="Optional project label (defaults to project_root basename)",
    )
    p.add_argument("--devforge-dir", default=".devforge")
