#!/usr/bin/env python3
"""Onboard Helper for the /onboard command.

The onboard LLM (and its dispatched tech-writer subagents) calls this tool
to register documentation artifacts: per-package docs, per-concern docs,
the workspace architecture doc, and memory findings. The helper is the
*only* sanctioned path to write under docs/. Bulk-script-write is
unrepresentable in the API surface — this is the forcing function for
per-unit dispatch + per-concern decomposition.

Verbs:
  set                   Set a top-level scalar (e.g. mode = overwrite|merge|fresh)
  add-package-doc       Register one package's index.md content
  add-concern-doc       Register one concern doc inside a package
  add-architecture-doc  Register the workspace architecture.md (single call)
  add-memory-finding    Register one memory observation (multiple calls)
  status                Print machine-readable progress
  compose-onboard       Validate + atomically write all registered docs

This is a Step 1.1 SKELETON. All subcommand handlers are stubs that print
"not implemented" and exit 2. Schema, state, validation, and write
implementation land in subsequent steps.

Stdlib only. No third-party dependencies. Target Python: 3.8+.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ─── Paths ───────────────────────────────────────────────────────────────────
# The onboard command invokes this tool from the target project root.
# `.devforge/` is created by install.sh; we mkdir defensively for ad-hoc / test
# use (added in Step 1.2 alongside state file RW).

DEVFORGE_DIR = Path(".devforge")
STATE_FILE = DEVFORGE_DIR / ".onboard-state.json"
DOCS_DIR = Path("docs")
BASELINE_DIR = DEVFORGE_DIR / "baseline" / "docs"


# ─── Subcommand handlers (stubs — Step 1.1) ──────────────────────────────────


def _not_implemented(name: str) -> int:
    print(f"onboard_helper: '{name}' not implemented yet (Step 1.1 skeleton).", file=sys.stderr)
    return 2


def cmd_set(args: argparse.Namespace) -> int:
    return _not_implemented("set")


def cmd_add_package_doc(args: argparse.Namespace) -> int:
    return _not_implemented("add-package-doc")


def cmd_add_concern_doc(args: argparse.Namespace) -> int:
    return _not_implemented("add-concern-doc")


def cmd_add_architecture_doc(args: argparse.Namespace) -> int:
    return _not_implemented("add-architecture-doc")


def cmd_add_memory_finding(args: argparse.Namespace) -> int:
    return _not_implemented("add-memory-finding")


def cmd_status(args: argparse.Namespace) -> int:
    return _not_implemented("status")


def cmd_compose_onboard(args: argparse.Namespace) -> int:
    return _not_implemented("compose-onboard")


# ─── Argparse setup ──────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onboard_helper",
        description=(
            "Register onboard documentation artifacts (per-package, per-concern, "
            "architecture, memory) and atomically compose them into docs/. "
            "Bulk-script-write is unsupported by design."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser(
        "set",
        help="Set a top-level scalar (e.g. mode).",
    )
    p_set.add_argument("field", help="Field name (e.g. mode).")
    p_set.add_argument("--value", required=True, help="Value to set.")
    p_set.set_defaults(func=cmd_set)

    p_pkg = sub.add_parser(
        "add-package-doc",
        help="Register one package's index.md content.",
    )
    p_pkg.add_argument("--unit", required=True, help="Package/unit name.")
    p_pkg.add_argument("--path", required=True, help="Package's source path relative to SOURCE_ROOT (e.g. packages/pkg-foo).")
    p_pkg.add_argument("--content", required=True, help="Full markdown content for docs/<path>/index.md.")
    p_pkg.add_argument("--block-count", type=int, required=True, help="Self-reported count of fenced code blocks in content.")
    p_pkg.add_argument("--ref-count", type=int, required=True, help="Self-reported count of <!-- path:line --> references in content. Must equal block-count.")
    p_pkg.set_defaults(func=cmd_add_package_doc)

    p_concern = sub.add_parser(
        "add-concern-doc",
        help="Register one concern doc inside a package.",
    )
    p_concern.add_argument("--unit", required=True, help="Parent package/unit name (must be already registered via add-package-doc).")
    p_concern.add_argument("--concern", required=True, help="Concern name (subfolder name, e.g. components, services, routing).")
    p_concern.add_argument("--content", required=True, help="Full markdown content for docs/<unit-path>/<concern>.md.")
    p_concern.add_argument("--block-count", type=int, required=True, help="Self-reported count of fenced code blocks in content.")
    p_concern.add_argument("--ref-count", type=int, required=True, help="Self-reported count of <!-- path:line --> references in content. Must equal block-count.")
    p_concern.set_defaults(func=cmd_add_concern_doc)

    p_arch = sub.add_parser(
        "add-architecture-doc",
        help="Register the workspace architecture.md (single call). Distinct prompt template — NOT the per-package template.",
    )
    p_arch.add_argument("--content", required=True, help="Full markdown content for docs/architecture.md.")
    p_arch.add_argument("--block-count", type=int, required=True, help="Self-reported count of fenced code blocks in content.")
    p_arch.add_argument("--ref-count", type=int, required=True, help="Self-reported count of <!-- path:line --> references in content. Must equal block-count.")
    p_arch.set_defaults(func=cmd_add_architecture_doc)

    p_mem = sub.add_parser(
        "add-memory-finding",
        help="Register one memory observation. Multiple calls. Findings collected during a separate source-reading pass, NOT summarized from generated docs.",
    )
    p_mem.add_argument(
        "--category",
        required=True,
        choices=["module-boundaries", "dependency-warnings", "complexity", "inconsistencies"],
        help="Memory category (maps to scaffold subsection).",
    )
    p_mem.add_argument("--unit", required=True, help="Unit/package this finding applies to (or 'workspace' for cross-cutting).")
    p_mem.add_argument("--observation", required=True, help="The finding itself (one line).")
    p_mem.set_defaults(func=cmd_add_memory_finding)

    p_status = sub.add_parser(
        "status",
        help="Show machine-readable progress (registrations per category, missing required, validator state).",
    )
    p_status.set_defaults(func=cmd_status)

    p_compose = sub.add_parser(
        "compose-onboard",
        help="Validate state and atomically write all registered docs to docs/. Drop baselines on success. Clears state on success.",
    )
    p_compose.set_defaults(func=cmd_compose_onboard)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
