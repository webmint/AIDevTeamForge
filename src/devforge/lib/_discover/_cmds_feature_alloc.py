"""allocate-feature-dir + render-branch-command CLI verbs.

68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 1 -- thin wrappers over the shared
_shared/feature_alloc.py substrate.  Both verbs are STATELESS (args-only):
neither reads nor writes discover-scope.json / discover-report.json.  They
exist so a future /discover command spec (Phase 3, not built here) can
allocate specs/NNN-slug/ and decide the branch action at intake finalize
time (plan 68 D1), the same capability /specify already has via
specify_helper create-branch.

91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 2 -- allocate-feature-dir
gained an optional --ticket argument.  This verb reads REQUIRE_TICKET via
read_require_ticket(args.devforge_dir) itself (the one place per plan 91 D4's
substrate docstring that reads that config key for this call) and passes
both the ticket and that boolean through to allocate_feature_dir, which
stays a pure function of its arguments -- see that function's own docstring
for the validation/refusal rules this wrapper does not duplicate.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import sys

from _shared.feature_alloc import (  # type: ignore[import]
    allocate_feature_dir,
    decide_branch_action,
    read_require_ticket,
)


def cmd_allocate_feature_dir(args: argparse.Namespace) -> int:
    """Allocate a fresh specs/<YYYY>/<MM>/<leaf>/ directory; print the result as JSON.

    91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 3: this wrapper's
    body is unchanged -- it still forwards whatever
    _shared.feature_alloc.allocate_feature_dir returns. What changed is
    that dict's own key set (see that function's docstring): exit 0 with a
    JSON object on stdout (keys: path, relative_path, slug, ticket, year,
    month, leaf, created) on success. `number`, `formatted_number` and
    `dirname` -- present before Phase 3 -- are ABSENT now; a caller must
    not assume they exist.
    Exit 2 with a message on stderr on failure (invalid slug, a supplied
    ticket that fails normalize_ticket, REQUIRE_TICKET enabled with no
    valid ticket supplied, or the computed target directory already exists
    -- see _shared.feature_alloc.allocate_feature_dir for the full error
    catalog).
    """
    require_ticket = read_require_ticket(args.devforge_dir)
    result, error = allocate_feature_dir(
        args.devforge_dir, args.slug, ticket=args.ticket, require_ticket=require_ticket,
    )
    if error is not None:
        sys.stderr.write(
            "discover_helper: allocate-feature-dir: {0}\n".format(error)
        )
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_render_branch_command(args: argparse.Namespace) -> int:
    """Print the branch-decision line (checkout command or informational
    comment) for the given current/default branch + ticket-or-slug.

    91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 3 (D5): passes
    (args.ticket, args.slug) through to decide_branch_action -- the
    'create' arm names the branch spec/<ticket> when one was given, else
    spec/<slug>. --number is ACCEPTED BUT IGNORED (see build_parser's own
    comment on that argument for why it is kept rather than removed).

    Exit 0 with the line on stdout on success (whether or not a checkout
    was actually emitted -- decide_branch_action's "keep" arms are success,
    not failure).
    Exit 2 with a message on stderr when neither --ticket nor --slug can
    supply an identity (the session is on the default branch).
    """
    decision, line, error = decide_branch_action(
        args.current_branch, args.default_branch, args.ticket, args.slug,
    )
    if error is not None:
        sys.stderr.write(
            "discover_helper: render-branch-command: {0}\n".format(error)
        )
        return 2
    sys.stdout.write(line + "\n")
    return 0
