"""Single owner of the concern-root path computation for `generate-docs`.

Every `<pkg>/src/<concern>` path the `_generate_docs` modules compute --
absolute directories, the project-relative prefix and the package-relative
prefix -- comes from this module, and the `"src"` literal lives here only
(precedent: `_shared/memory.py`, the single owner of the `.devforge/memory.md`
literal). Callers keep their own skip predicates and `.resolve()` calls.

Every function takes the project root and the package path as the caller
knows them, even where the current layout ignores one of them, so that a
future layout decision made inside this module needs no call-site change.
`project_root` is the directory holding `.devforge/` (`devforge_dir.parent`);
`pkg` is the package path relative to it (`"."` for a single-root project).
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath

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


def concern_dir(project_root: Path, pkg: str, concern: str) -> Path:
    """Absolute directory of one concern."""
    return project_root / pkg / SRC_DIR_NAME / concern


def concern_rel_prefix(project_root: Path, pkg: str, concern: str) -> str:
    """PROJECT-relative POSIX prefix of a concern, with a trailing slash.

    `PurePosixPath(".")` collapses, so `pkg="."` yields `src/<concern>/`.
    """
    return str(PurePosixPath(pkg) / SRC_DIR_NAME / concern) + "/"


def concern_pkg_prefix(project_root: Path, pkg: str, concern: str) -> str:
    """PACKAGE-relative POSIX prefix of a concern, with a trailing slash.

    Matches the package-relative `files[]` paths in `index.json`.
    """
    return "{0}/{1}/".format(SRC_DIR_NAME, concern)
