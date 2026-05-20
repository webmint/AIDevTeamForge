"""Smell-heuristic package for pr_review_helper Step 4 (detect-smells).

This __init__.py is the single registration point.  It imports each heuristic
module and calls _catalog.register() to add them in the order they appear here.
That order is the order run_all() dispatches them.

Public API consumed by _cli.py:
    from _pr_review import _smells
    findings = _smells._catalog.run_all(state)
"""

from __future__ import annotations

from . import _catalog
from . import empty_pr_body
from . import atomic_dump
from . import hedge_defensive
from . import verbose_commit_msg

_catalog.register("empty_pr_body", "low", empty_pr_body.run)
_catalog.register("atomic_dump", "medium", atomic_dump.run)
_catalog.register("hedge_defensive", "low", hedge_defensive.run)
_catalog.register("verbose_commit_msg", "nit", verbose_commit_msg.run)
