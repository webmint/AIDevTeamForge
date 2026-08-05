"""allocate-feature-dir + render-branch-command CLI verbs.

68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 1 -- thin wrappers over the shared
_shared/feature_alloc.py substrate.  Both verbs are STATELESS (args-only):
neither reads nor writes research-state.json / research-report.json.  They
exist so a future /research command spec (Phase 2, not built here) can
allocate specs/NNN-slug/ and decide the branch action at intake finalize
time (plan 68 D1), the same capability /specify already has via
specify_helper create-branch.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import sys

from _shared.feature_alloc import (  # type: ignore[import]
    allocate_feature_dir,
    decide_branch_action,
)


def cmd_allocate_feature_dir(args: argparse.Namespace) -> int:
    """Allocate a fresh specs/NNN-<slug>/ directory; print the result as JSON.

    Exit 0 with a JSON object on stdout (keys: path, number,
    formatted_number, slug, dirname, created) on success.
    Exit 2 with a message on stderr on failure (invalid slug, or the
    computed target directory already exists -- see
    _shared.feature_alloc.allocate_feature_dir for the full error catalog).
    """
    result, error = allocate_feature_dir(args.devforge_dir, args.slug)
    if error is not None:
        sys.stderr.write(
            "research_helper: allocate-feature-dir: {0}\n".format(error)
        )
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_render_branch_command(args: argparse.Namespace) -> int:
    """Print the branch-decision line (checkout command or informational
    comment) for the given current/default branch + spec number/slug.

    Exit 0 with the line on stdout on success (whether or not a checkout
    was actually emitted -- decide_branch_action's "keep" arms are success,
    not failure).
    Exit 2 with a message on stderr when --number/--slug are required (the
    session is on the default branch) but were not supplied.
    """
    decision, line, error = decide_branch_action(
        args.current_branch, args.default_branch, args.number, args.slug,
    )
    if error is not None:
        sys.stderr.write(
            "research_helper: render-branch-command: {0}\n".format(error)
        )
        return 2
    sys.stdout.write(line + "\n")
    return 0
