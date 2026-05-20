"""argparse parser + dispatch + main entry for pr_review_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches every cmd_* handler (real or stub).
main parses argv + dispatches.

Step 2 verbs (ensure-cbm-index, detect-forge-state) are fully implemented.
The remaining 9 verb stubs return exit 1 with a "not yet implemented"
message; concrete behavior lands in PR-REVIEW-PLAN Steps 3-9.
"""

from __future__ import annotations

import argparse
import json
import os
import sys


# ---------------------------------------------------------------------------
# Step 2 handlers — real implementations replacing stubs.
# ---------------------------------------------------------------------------


def cmd_ensure_cbm_index(args: argparse.Namespace) -> int:
    """Phase -1: ensure CBM index is current before review.

    Invokes cbm_sync_helper check and emits a structured JSON dict to
    stdout. The LLM reads the JSON to decide whether to run detect_changes
    or index_repository before proceeding.

    Returns 0 on success, 1 on subprocess / I/O error.
    """
    from ._ensure_cbm import run as _run_ensure_cbm

    target = getattr(args, "target", None) or os.getcwd()
    devforge_dir = getattr(args, "devforge_dir", ".devforge")
    try:
        result = _run_ensure_cbm(target=target, devforge_dir=devforge_dir)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            "pr_review_helper ensure-cbm-index: error: {0}\n".format(exc)
        )
        return 1
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_detect_forge_state(args: argparse.Namespace) -> int:
    """Phase 0: detect forge-tier (full/partial/none) for the target repo.

    Pure filesystem scan — no subprocess, no network. Emits a structured
    JSON dict to stdout classifying the repo's forge state.

    Returns 0 on success, 1 on I/O error.
    """
    from ._detect_tier import run as _run_detect_tier

    target = getattr(args, "target", None) or os.getcwd()
    devforge_dir = getattr(args, "devforge_dir", ".devforge")
    try:
        result = _run_detect_tier(target=target, devforge_dir=devforge_dir)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            "pr_review_helper detect-forge-state: error: {0}\n".format(exc)
        )
        return 1
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_intake(args: argparse.Namespace) -> int:
    sys.stderr.write(
        "pr_review_helper intake: not yet implemented"
        " (PR-REVIEW-PLAN Step 3 pending)\n"
    )
    return 1


def cmd_detect_smells(args: argparse.Namespace) -> int:
    sys.stderr.write(
        "pr_review_helper detect-smells: not yet implemented"
        " (PR-REVIEW-PLAN Step 4 pending)\n"
    )
    return 1


def cmd_compute_blast_radius(args: argparse.Namespace) -> int:
    sys.stderr.write(
        "pr_review_helper compute-blast-radius: not yet implemented"
        " (PR-REVIEW-PLAN Step 5 pending)\n"
    )
    return 1


def cmd_bundle_context(args: argparse.Namespace) -> int:
    sys.stderr.write(
        "pr_review_helper bundle-context: not yet implemented"
        " (PR-REVIEW-PLAN Step 6 pending)\n"
    )
    return 1


def cmd_import_handoffs(args: argparse.Namespace) -> int:
    sys.stderr.write(
        "pr_review_helper import-handoffs: not yet implemented"
        " (PR-REVIEW-PLAN Step 6 pending)\n"
    )
    return 1


def cmd_check_scope_drift(args: argparse.Namespace) -> int:
    sys.stderr.write(
        "pr_review_helper check-scope-drift: not yet implemented"
        " (PR-REVIEW-PLAN Step 7 pending)\n"
    )
    return 1


def cmd_dispatch_review(args: argparse.Namespace) -> int:
    sys.stderr.write(
        "pr_review_helper dispatch-review: not yet implemented"
        " (PR-REVIEW-PLAN Step 8 pending)\n"
    )
    return 1


def cmd_finalize_output(args: argparse.Namespace) -> int:
    sys.stderr.write(
        "pr_review_helper finalize-output: not yet implemented"
        " (PR-REVIEW-PLAN Step 9 pending)\n"
    )
    return 1


def cmd_append_to_replay_corpus(args: argparse.Namespace) -> int:
    sys.stderr.write(
        "pr_review_helper append-to-replay-corpus: not yet implemented"
        " (PR-REVIEW-PLAN Step 9 pending)\n"
    )
    return 1


# ---------------------------------------------------------------------------
# Parser construction.
# ---------------------------------------------------------------------------

# Registry: (verb, help-text, handler).
# Adding a new subcommand = append a tuple here; no other edits needed.
_SUBCOMMAND_REGISTRY = [
    (
        "ensure-cbm-index",
        "Ensure CBM index is current before review (Step 2).",
        cmd_ensure_cbm_index,
    ),
    (
        "detect-forge-state",
        "Detect forge-tier (full/partial/none) for the target repo (Step 2).",
        cmd_detect_forge_state,
    ),
    (
        "intake",
        "Fetch PR metadata + diff and write initial state (Step 3).",
        cmd_intake,
    ),
    (
        "detect-smells",
        "Run AI-slop heuristics over the diff and record smells (Step 4).",
        cmd_detect_smells,
    ),
    (
        "compute-blast-radius",
        "Trace changed symbols to dependents and record blast list (Step 5).",
        cmd_compute_blast_radius,
    ),
    (
        "bundle-context",
        "Assemble concern docs + architecture context bundle (Step 6).",
        cmd_bundle_context,
    ),
    (
        "import-handoffs",
        "Import relevant /research + /discover handoff docs (Step 6).",
        cmd_import_handoffs,
    ),
    (
        "check-scope-drift",
        "Compare diff scope against PR body / linked issue and flag drift (Step 7).",
        cmd_check_scope_drift,
    ),
    (
        "dispatch-review",
        "Assemble reviewer brief and dispatch review agent (Step 8).",
        cmd_dispatch_review,
    ),
    (
        "finalize-output",
        "Render review findings to console + save output artefact (Step 9).",
        cmd_finalize_output,
    ),
    (
        "append-to-replay-corpus",
        "Append this PR review to the replay corpus for regression tests (Step 9).",
        cmd_append_to_replay_corpus,
    ),
]


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="pr_review_helper",
        description=(
            "State + review helper for /pr-review. "
            "Personal-overlay PR review of foreign repos; "
            "AI-slop + blast-radius + scope-drift detection."
        ),
    )
    parser.add_argument(
        "--devforge-dir",
        default=".devforge",
        help="Path to the .devforge directory (default: .devforge in CWD).",
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers) -> None:
    """Attach all handlers from _SUBCOMMAND_REGISTRY.

    Step 2 verbs (ensure-cbm-index, detect-forge-state) also receive a
    --target argument. All other verbs get no extra arguments until their
    step lands.
    """
    _STEP2_VERBS = frozenset(["ensure-cbm-index", "detect-forge-state"])
    for verb, help_text, handler in _SUBCOMMAND_REGISTRY:
        sp = subparsers.add_parser(verb, help=help_text)
        if verb in _STEP2_VERBS:
            sp.add_argument(
                "--target",
                default=os.getcwd(),
                help=(
                    "Absolute path to the repository root to inspect "
                    "(default: current working directory)."
                ),
            )
        sp.set_defaults(func=handler)


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    """Parse argv and dispatch to the selected subcommand handler.

    Returns the handler's exit code (0 = success, non-zero = error).
    When no subcommand is given, prints help and returns 2.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help(sys.stderr)
        return 2

    return args.func(args)
