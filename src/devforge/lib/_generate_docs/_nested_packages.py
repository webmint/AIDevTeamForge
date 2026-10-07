"""Registered packages nested below a fallback package (plan 112, OQ-5).

A fallback concern is rooted at `<pkg>/`, so a package registered below it
would be documented twice. This module reads the registered package paths
from `index.json`, bridges them to the install root exactly as preflight
does, and answers which directories of a fallback package belong to a nested
package. Package paths returned are PACKAGE-relative POSIX directories, the
form the `index.json` `files[]` entries and the concern walk's package-relative
paths share.

Stdlib only. Targets Python 3.8+.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

from ._concern_root import is_fallback_concern

_INDEX_FILE_NAME = "index.json"


def load_index(devforge_dir: Path) -> Optional[Dict[str, Any]]:
    """Parse `<devforge_dir>/index.json`; None when missing or malformed."""
    index_path = devforge_dir / _INDEX_FILE_NAME
    if not index_path.exists():
        return None
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return index if isinstance(index, dict) else None


def bridge_prefix(index: Dict[str, Any], project_root: Path) -> str:
    """Prefix turning an `index.json` package key into an install-root path.

    Package keys are relative to the index's own `project_root`, which in
    wrapper installs sits below the install root (`project_root`, the
    directory holding `.devforge/`). Returns `""` or `"<rel>/"`.
    """
    raw_index_root = index.get("project_root")
    if not isinstance(raw_index_root, str) or not raw_index_root:
        return ""
    try:
        index_root = Path(raw_index_root).resolve()
        if index_root != project_root:
            return index_root.relative_to(project_root).as_posix() + "/"
    except (ValueError, OSError):
        return ""
    return ""


def nested_package_rels(devforge_dir: Path, pkg: str) -> List[str]:
    """Package-relative dirs of registered packages nested strictly below `pkg`.

    `pkg` is the install-root-relative package path. Sorted; empty when the
    index is missing or `pkg` has no nested package.
    """
    index = load_index(devforge_dir)
    if index is None:
        return []
    packages = index.get("packages")
    if not isinstance(packages, dict):
        return []
    prefix = bridge_prefix(index, devforge_dir.parent.resolve())
    base = PurePosixPath(pkg)
    out = set()
    for key in packages:
        try:
            tail = PurePosixPath(prefix + key).relative_to(base)
        except ValueError:
            continue
        if str(tail) != ".":
            out.add(str(tail))
    return sorted(out)


def fallback_excluded_rels(devforge_dir: Path, pkg: str, concern: str) -> List[str]:
    """Nested-package dirs to exclude from `concern`; [] unless it is `pkg`'s fallback.

    `src/` concerns keep today's non-exclusion.
    """
    if not is_fallback_concern(devforge_dir.parent, pkg, concern):
        return []
    return nested_package_rels(devforge_dir, pkg)


def under_any(rel_path: str, dir_rels: List[str]) -> bool:
    """True when `rel_path` lies inside one of the package-relative `dir_rels`."""
    return any(rel_path == d or rel_path.startswith(d + "/") for d in dir_rels)
