"""argparse parser + dispatch + main entry for fix_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Mirrors _verify/_cli.py in structure — verb-registry pattern with
_SUBCOMMAND_REGISTRY of (verb_name, help_text, handler) triples.

Verbs (Phase 1):
  preflight         — 4-command setup-chain gate + source_root/wrapper_mode
  read-findings     — parse review.md + verification.md NEEDS-WORK issues
  resolve-scope     — map working list to narrow file set for verify-touched
  in-fix-window     — detect post-/implement, pre-/summarize window (case-3 gate)

Verbs (Phase 2, plan 83 D5):
  write-seed        — build + write fix-seed.json (scope-change backward
                      re-entry arm, target_stage="spec" fixed)

OQ decisions recorded in _fix/__init__.py and the individual submodules:
  OQ-1 persisted findings     → _findings.py
  OQ-2 narrow finding scope   → _scope.py
  OQ-4 helper verb            → _window.py
  _state.py: NOT built        → __init__.py rationale

Extension point: append to _SUBCOMMAND_REGISTRY and add the argument block
in the elif chain in _register_subcommands.
"""

from __future__ import annotations

import argparse
import json
import os
import sys


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_preflight(args):
    # type: (argparse.Namespace) -> int
    """Check setup-chain artefacts, source_root/wrapper_mode.

    Always emits JSON to stdout. Returns 0 on pass, 2 on failure.
    Does NOT read .claude/ paths (plan-22 finding F avoided — .devforge/ only).
    """
    from ._preflight import preflight_context

    workspace_root = getattr(args, "workspace_root", ".") or "."

    result = preflight_context(workspace_root)

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    if not result["setup_chain_ok"]:
        missing = result.get("missing_artefacts", [])
        sys.stderr.write(
            "fix_helper preflight: setup chain incomplete. "
            "Run the 4-command setup sequence first:\n"
            "  /devforge:init-forge → /devforge:generate-docs → /devforge:configure → "
            "/devforge:constitute\n"
            "Missing: {0}\n".format(", ".join(missing))
        )
        return 2

    if not result["constitution_populated"]:
        sys.stderr.write(
            "fix_helper preflight: constitution.md contains an unpopulated "
            "sentinel. Run /devforge:constitute to populate it before running /devforge:fix.\n"
        )
        return 2

    return 0


def cmd_read_findings(args):
    # type: (argparse.Namespace) -> int
    """Parse review.md + verification.md NEEDS-WORK issues → working list JSON.

    Emits JSON to stdout. Returns 0 always (missing files are noted in sources).

    OQ-1: reads PERSISTED on-disk artifacts — works in a fresh session.
    """
    from ._findings import read_findings

    feature = getattr(args, "feature", None) or ""
    source = getattr(args, "source", "both") or "both"

    if not feature:
        sys.stderr.write("fix_helper read-findings: --feature is required\n")
        return 2

    if source not in ("review", "verify", "both"):
        sys.stderr.write(
            "fix_helper read-findings: --source must be 'review', 'verify', or 'both'\n"
        )
        return 2

    result = read_findings(feature, source=source)

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_resolve_scope(args):
    # type: (argparse.Namespace) -> int
    """Map the working list → the narrow file set for verify-touched.

    Reads the working list from a JSON file (--items) or stdin ("-").
    Emits JSON to stdout. Returns 0 on success, 2 on argument error.

    OQ-2: narrow finding-targeted scope (NOT the assembled-feature diff).
    """
    from ._scope import resolve_scope

    items_path = getattr(args, "items", None) or ""

    if not items_path:
        sys.stderr.write("fix_helper resolve-scope: --items is required\n")
        return 2

    if items_path == "-":
        raw = sys.stdin.read()
    else:
        try:
            with open(items_path, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as exc:
            sys.stderr.write(
                "fix_helper resolve-scope: cannot read --items: {0}\n".format(exc)
            )
            return 2

    try:
        items = json.loads(raw)
    except ValueError as exc:
        sys.stderr.write(
            "fix_helper resolve-scope: --items JSON is invalid: {0}\n".format(exc)
        )
        return 2

    if not isinstance(items, list):
        sys.stderr.write("fix_helper resolve-scope: --items JSON must be a list\n")
        return 2

    result = resolve_scope(items)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_in_fix_window(args):
    # type: (argparse.Namespace) -> int
    """Return whether the active feature is in the post-/implement, pre-/summarize window.

    Emits JSON to stdout with {"in_window": bool, "reason": str}.
    Returns 0 when in-window, 1 when out-of-window (so callers can gate on
    exit code AND the JSON field).

    OQ-4: dedicated helper verb — keeps the always-on CLAUDE.md rule short.
    """
    from ._window import in_fix_window

    feature = getattr(args, "feature", None) or ""

    if not feature:
        sys.stderr.write("fix_helper in-fix-window: --feature is required\n")
        return 2

    result = in_fix_window(feature)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    # Exit code: 0 = in-window (offer /fix); 1 = out-of-window (file only).
    return 0 if result["in_window"] else 1


def cmd_write_seed(args):
    # type: (argparse.Namespace) -> int
    """Build + write fix-seed.json (scope-change backward re-entry arm).

    source/target_stage are fixed internally by build_seed ("fix" / "spec")
    -- /devforge:fix has exactly one backward direction in this build (plan
    83 D2), unlike /grill's multi-target write-seed. There is no
    --target-stage flag.

    Returns 0 on success (prints {"seed_path": ...} as JSON to stdout).
    Returns 2 on missing/invalid required fields.
    """
    from ._seed import build_seed, write_seed

    feature = getattr(args, "feature", None) or ""
    feature_dir = getattr(args, "feature_dir", None)
    prior_conclusion = getattr(args, "prior_conclusion", None) or ""
    invalidating_evidence = getattr(args, "invalidating_evidence", None) or ""
    must_satisfy = getattr(args, "must_satisfy", None) or ""
    provenance = getattr(args, "provenance", None) or ""
    cycle_count_raw = getattr(args, "cycle_count", None)
    if cycle_count_raw is None:
        cycle_count_raw = "1"
    carried_raw = getattr(args, "carried_findings", None)
    if carried_raw is None:
        carried_raw = "[]"

    if not feature_dir:
        sys.stderr.write(
            "fix_helper write-seed: --feature-dir <dir> required\n"
        )
        return 2
    if not prior_conclusion:
        sys.stderr.write(
            "fix_helper write-seed: --prior-conclusion required\n"
        )
        return 2
    if not invalidating_evidence:
        sys.stderr.write(
            "fix_helper write-seed: --invalidating-evidence required\n"
        )
        return 2
    if not must_satisfy:
        sys.stderr.write(
            "fix_helper write-seed: --must-satisfy required\n"
        )
        return 2
    if not provenance:
        sys.stderr.write(
            "fix_helper write-seed: --provenance required\n"
        )
        return 2

    try:
        cycle_count = int(cycle_count_raw)
    except (ValueError, TypeError):
        sys.stderr.write(
            "fix_helper write-seed: --cycle-count must be an "
            "integer, got {0!r}\n".format(cycle_count_raw)
        )
        return 2

    try:
        carried_findings = json.loads(carried_raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "fix_helper write-seed: --carried-findings must be a "
            "JSON array string: {0}\n".format(exc)
        )
        return 2
    if not isinstance(carried_findings, list):
        sys.stderr.write(
            "fix_helper write-seed: --carried-findings must decode "
            "to a JSON array, got {0}\n".format(type(carried_findings).__name__)
        )
        return 2

    try:
        seed = build_seed(
            feature=feature,
            prior_conclusion=prior_conclusion,
            invalidating_evidence=invalidating_evidence,
            must_satisfy=must_satisfy,
            provenance=provenance,
            cycle_count=cycle_count,
            carried_findings=carried_findings,
        )
    except ValueError as exc:
        sys.stderr.write("fix_helper write-seed: {0}\n".format(exc))
        return 2

    try:
        seed_path = write_seed(feature_dir, seed)
    except OSError as exc:
        sys.stderr.write(
            "fix_helper write-seed: cannot write fix-seed.json: {0}\n".format(exc)
        )
        return 2

    sys.stdout.write(json.dumps({"seed_path": seed_path}, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Registry + parser construction
# ---------------------------------------------------------------------------

# _SUBCOMMAND_REGISTRY is the extension point for new verbs.
# Each entry is a (verb_name, help_text, handler_function) triple.
# To add a future verb:
#   1. Write the cmd_<verb> function above.
#   2. Append (kebab-name, help, cmd_func) to this list.
#   3. Add the argument block for the verb in the elif chain in
#      _register_subcommands below.
_SUBCOMMAND_REGISTRY = [
    (
        "preflight",
        (
            "Gate on 4-command setup-chain artefacts + populated constitution; "
            "emit source_root/wrapper_mode context. Reads .devforge/ paths only."
        ),
        cmd_preflight,
    ),
    (
        "read-findings",
        (
            "Parse specs/[feature]/review.md confirmed/contested findings AND/OR "
            "specs/[feature]/verification.md NEEDS-WORK issues into one JSON "
            "working list (OQ-1: PERSISTED — works in a fresh session)."
        ),
        cmd_read_findings,
    ),
    (
        "resolve-scope",
        (
            "Map the working list (from read-findings) to the narrow "
            "finding-targeted file set for implement_helper verify-touched "
            "(OQ-2: NARROW — not the assembled-feature diff)."
        ),
        cmd_resolve_scope,
    ),
    (
        "in-fix-window",
        (
            "Return whether the active feature is in the post-/devforge:implement, "
            "pre-/devforge:summarize window (D2 condition 3c — the case-3 conversational "
            "offer gate). Exit 0 = in-window; exit 1 = out-of-window."
        ),
        cmd_in_fix_window,
    ),
    (
        "write-seed",
        "Build + write fix-seed.json (scope-change backward re-entry arm; "
        "target_stage=\"spec\" fixed — plan 83 D2).",
        cmd_write_seed,
    ),
]


def build_parser():
    # type: () -> argparse.ArgumentParser
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="fix_helper",
        description=(
            "Helper for /devforge:fix — proposal-only gated pipeline-remediation. "
            "Reads pipeline findings (review.md / verification.md), scopes "
            "them to the affected files, and gates on the post-/devforge:implement / "
            "pre-/devforge:summarize window. Back-half (verify-touched → review panel → "
            "forcing-functions gate → hard gate → wip-commit) is owned by the "
            "installed implement_helper binary."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers):
    # type: (...) -> None
    """Attach all handlers from _SUBCOMMAND_REGISTRY."""
    for verb, help_text, handler in _SUBCOMMAND_REGISTRY:
        sp = subparsers.add_parser(verb, help=help_text)

        if verb == "preflight":
            sp.add_argument(
                "--workspace-root",
                default=".",
                dest="workspace_root",
                metavar="DIR",
                help=(
                    "Workspace root to check for setup-chain artefacts. "
                    "In wrapper mode this is the wrapper root (not the project "
                    "sub-directory). Default: CWD."
                ),
            )

        elif verb == "read-findings":
            sp.add_argument(
                "--feature",
                required=True,
                metavar="DIR",
                help=(
                    "Feature directory path (e.g. specs/001-auth). "
                    "review.md and verification.md are resolved relative to it."
                ),
            )
            sp.add_argument(
                "--source",
                default="both",
                choices=["review", "verify", "both"],
                metavar="SOURCE",
                help=(
                    "'review' — parse review.md only; "
                    "'verify' — parse verification.md NEEDS-WORK issues only; "
                    "'both' — parse both (default)."
                ),
            )

        elif verb == "resolve-scope":
            sp.add_argument(
                "--items",
                required=True,
                metavar="PATH",
                help=(
                    "Path to JSON file containing the 'items' list from "
                    "read-findings output. Pass '-' to read from stdin."
                ),
            )

        elif verb == "in-fix-window":
            sp.add_argument(
                "--feature",
                required=True,
                metavar="DIR",
                help=(
                    "Feature directory path (e.g. specs/001-auth). "
                    "tasks/ and spec.md are resolved relative to it."
                ),
            )

        elif verb == "write-seed":
            sp.add_argument(
                "--feature",
                default="",
                metavar="STR",
                help="Feature slug / id (non-empty; passed to build_seed).",
            )
            sp.add_argument(
                "--feature-dir",
                required=True,
                dest="feature_dir",
                metavar="DIR",
                help=(
                    "Feature directory path (e.g. specs/001-auth/). "
                    "fix-seed.json is written here."
                ),
            )
            sp.add_argument(
                "--prior-conclusion",
                required=True,
                dest="prior_conclusion",
                metavar="TEXT",
                help=(
                    "The named working-list item's original diagnosis, now "
                    "proven to be a scope change."
                ),
            )
            sp.add_argument(
                "--invalidating-evidence",
                required=True,
                dest="invalidating_evidence",
                metavar="TEXT",
                help=(
                    "The quoted finding evidence plus the scope-change "
                    "classification reason (or the bare classification "
                    "judgment for a case-3 conversational defect)."
                ),
            )
            sp.add_argument(
                "--must-satisfy",
                required=True,
                dest="must_satisfy",
                metavar="TEXT",
                help="What the re-run must additionally resolve.",
            )
            sp.add_argument(
                "--provenance",
                required=True,
                metavar="PATH",
                help=(
                    "Pointer to the source report, or the literal "
                    "'conversational (in-window user report; no report "
                    "file)' for a case-3 conversational defect."
                ),
            )
            sp.add_argument(
                "--cycle-count",
                default="1",
                dest="cycle_count",
                metavar="N",
                help=(
                    "Bounded-compounding-loop counter (int >= 1). "
                    "Default: 1."
                ),
            )
            sp.add_argument(
                "--carried-findings",
                default="[]",
                dest="carried_findings",
                metavar="JSON_ARRAY",
                help=(
                    "JSON array string of prior finding descriptions "
                    "carried forward (each multi-item bounce item's own "
                    "reasoning, per plan 83 OQ-4). Default: '[]'."
                ),
            )

        sp.set_defaults(func=handler)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None):
    # type: (...) -> int
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
