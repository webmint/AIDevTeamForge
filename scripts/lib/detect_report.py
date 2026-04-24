#!/usr/bin/env python3
"""Detection Report composer for setup-wizard Phase 1.

The setup-wizard LLM calls this tool once per Detection Report field
(`set`, `add-package`), checks progress (`status`), and writes the
final YAML to `.devforge/detection_report.yaml` (`compose`).

Stdlib only. No third-party dependencies. Target Python: 3.8+.
"""

from __future__ import annotations

import argparse
import sys


def cmd_set(args: argparse.Namespace) -> int:
    print(f"set: not implemented (field={args.field}, value={args.value})", file=sys.stderr)
    return 2


def cmd_add_package(args: argparse.Namespace) -> int:
    print("add-package: not implemented", file=sys.stderr)
    return 2


def cmd_status(args: argparse.Namespace) -> int:
    print("status: not implemented", file=sys.stderr)
    return 2


def cmd_compose(args: argparse.Namespace) -> int:
    print("compose: not implemented", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="detect_report",
        description="Compose the Phase 1 Detection Report for setup-wizard.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser("set", help="Set a single Detection Report field.")
    p_set.add_argument("field", help="Field name (supports dotted paths, e.g. runtime_url.source).")
    p_set.add_argument("--value", required=True, help="Value to set.")
    p_set.add_argument("--reason", help="Required when value is null for null-allowed fields.")
    p_set.set_defaults(func=cmd_set)

    p_add = sub.add_parser("add-package", help="Append one package record to packages[].")
    p_add.add_argument("--path", required=True)
    p_add.add_argument("--manifest", required=True)
    p_add.add_argument("--language-hint", required=True)
    p_add.add_argument("--framework-hint")
    p_add.add_argument("--build-command")
    p_add.add_argument("--type-check-command")
    p_add.add_argument("--lint-command")
    p_add.add_argument("--test-command")
    p_add.add_argument("--command-source", choices=["manifest", "fallback"], required=True)
    p_add.set_defaults(func=cmd_add_package)

    p_status = sub.add_parser("status", help="Show which fields are set/unset.")
    p_status.set_defaults(func=cmd_status)

    p_compose = sub.add_parser(
        "compose",
        help="Validate and emit .devforge/detection_report.yaml; clears state on success.",
    )
    p_compose.set_defaults(func=cmd_compose)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
