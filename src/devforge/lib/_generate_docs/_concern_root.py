"""Single owner of the concern-root path computation for `generate-docs`.

Every concern-root path the `_generate_docs` modules compute -- absolute
directories, the project-relative prefix and the package-relative prefix --
comes from this module, and the `"src"` literal lives here only (precedent:
`_shared/memory.py`, the single owner of the `.devforge/memory.md` literal).
Callers keep their own skip predicates and `.resolve()` calls.

Two layouts exist. A package with a `src/` directory has one concern per
`<pkg>/src/<concern>/` subdirectory. A *fallback package* -- a non-`.`
package whose directory exists but holds no `src/` directory -- has exactly
ONE concern, named after the package directory's basename and rooted at
`<pkg>/` itself (`fallback_concern`). `.` never falls back: a standalone root
keeps forge artifacts (`specs/`, `docs/`) that must not become concerns.

Every function takes the project root and the package path as the caller
knows them. The layout decision is made here, from the filesystem, so call
sites carry no layout knowledge.
`project_root` is the directory holding `.devforge/` (`devforge_dir.parent`);
`pkg` is the package path relative to it (`"."` for a single-root project).
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Optional

SRC_DIR_NAME = "src"


def package_root(project_root: Path, pkg: str) -> Path:
    """`<project_root>/<pkg>` -- the package's own root directory."""
    return project_root / pkg


def concerns_parent_dir(project_root: Path, pkg: str) -> Path:
    """Directory whose direct subdirectories are the package's concerns."""
    return project_root / pkg / SRC_DIR_NAME


def src_root_dir(project_root: Path, pkg: str) -> Path:
    """Directory whose direct files form the package's `src-root` tier."""
    return project_root / pkg / SRC_DIR_NAME


def fallback_concern(project_root: Path, pkg: str) -> Optional[str]:
    """The single concern name of a fallback package, else None.

    A fallback package is a non-`.` package whose directory exists and has no
    `src/` directory. Its concern is the package directory's basename (`tf`
    for `infra/tf`), rooted at the package directory.
    """
    posix = PurePosixPath(pkg)
    if posix == PurePosixPath("."):
        return None
    root = project_root / pkg
    if not root.is_dir() or (root / SRC_DIR_NAME).is_dir():
        return None
    return posix.name or None


def is_fallback_concern(project_root: Path, pkg: str, concern: str) -> bool:
    """True when `concern` is `pkg`'s fallback concern."""
    return fallback_concern(project_root, pkg) == concern


def concern_dir(project_root: Path, pkg: str, concern: str) -> Path:
    """Absolute directory of one concern (the package root for a fallback)."""
    if is_fallback_concern(project_root, pkg, concern):
        return project_root / pkg
    return project_root / pkg / SRC_DIR_NAME / concern


def concern_rel_prefix(project_root: Path, pkg: str, concern: str) -> str:
    """PROJECT-relative POSIX prefix of a concern, with a trailing slash.

    `PurePosixPath(".")` collapses, so `pkg="."` yields `src/<concern>/`.
    A fallback concern's prefix is `<pkg>/`.
    """
    if is_fallback_concern(project_root, pkg, concern):
        return str(PurePosixPath(pkg)) + "/"
    return str(PurePosixPath(pkg) / SRC_DIR_NAME / concern) + "/"


def concern_pkg_prefix(project_root: Path, pkg: str, concern: str) -> str:
    """PACKAGE-relative POSIX prefix of a concern, with a trailing slash.

    Matches the package-relative `files[]` paths in `index.json`. A fallback
    concern spans the whole package, so its prefix is the empty string.
    """
    if is_fallback_concern(project_root, pkg, concern):
        return ""
    return "{0}/{1}/".format(SRC_DIR_NAME, concern)
