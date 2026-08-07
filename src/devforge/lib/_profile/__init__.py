"""Internal package for profile_helper (transcript wall-clock profiling, plan 70).

Submodules are underscore-prefixed. External callers invoke via the POSIX
launcher `profile_helper` or `profile_helper.main`.

Public entry point is `main` (re-exported below).  Subcommand verbs
(`run`, `aggregate`) are wired in `_cli.py`; `main` dispatches to the
selected handler.

Self-contained by design (plan 70 constraint): this package imports
nothing from any other `_xxx/` command subpackage (no cross-command
coupling) -- only stdlib.
"""

from ._cli import main

__all__ = ["main"]
