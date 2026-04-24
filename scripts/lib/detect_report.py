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
from dataclasses import dataclass, field
from typing import Any


# ─── Schema ──────────────────────────────────────────────────────────────────
# Dataclasses mirror the YAML template in
# src/commands/setup-wizard/references/detect.md (lines 358-427) 1:1.
# Field names, nesting, and ordering preserved so the compose-step emitter
# can produce byte-identical YAML shape.


@dataclass
class LanguageEntry:
    name: str | None = None
    file_count: int = 0
    runtime: str | None = None


@dataclass
class FrameworkEntry:
    name: str | None = None
    role: str | None = None  # frontend | backend | library | plugin
    evidence: str | None = None


@dataclass
class PackageManager:
    tool: str | None = None
    outer_tool: str | None = None
    evidence: str | None = None


@dataclass
class ErrorHandling:
    library: str | None = None
    usage_pattern: str | None = None


@dataclass
class RuntimeURL:
    value: str | None = None
    source: str | None = None


@dataclass
class Package:
    path: str | None = None
    manifest: str | None = None
    language_hint: str | None = None
    framework_hint: str | None = None
    build_command: str | None = None
    type_check_command: str | None = None
    lint_command: str | None = None
    test_command: str | None = None
    command_source: str | None = None  # manifest | fallback


@dataclass
class OptionalSection:
    utility_manifests: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)  # stack-specific slots


@dataclass
class DetectionReport:
    workspace_mode: str | None = None  # standalone | wrapper
    source_root: str | None = None
    project_state: str | None = None  # empty | greenfield | brownfield
    default_branch: str | None = None
    file_count: int = 0
    manifest_count: int = 0

    languages: list[LanguageEntry] = field(default_factory=list)
    primary_language: str | None = None

    frameworks: list[FrameworkEntry] = field(default_factory=list)

    package_manager: PackageManager = field(default_factory=PackageManager)
    monorepo_tool: str | None = None

    build_tool: str | None = None
    build_command: str | None = None
    type_check_command: str | None = None
    lint_command: str | None = None
    test_runner: str | None = None

    # Library-category fields (dep+usage double-check rule per detect.md Rule 6).
    auth_layer: str | None = None
    api_client: str | None = None
    state_management: str | None = None
    styling: str | None = None
    routing: str | None = None
    error_handling: ErrorHandling = field(default_factory=ErrorHandling)
    validation_library: str | None = None

    architecture_shape: str | None = None
    architecture_evidence: str | None = None

    enforcement_tooling: list[str] = field(default_factory=list)
    ci_cd: str | None = None
    containerization: str | None = None

    runtime_url: RuntimeURL = field(default_factory=RuntimeURL)

    packages: list[Package] = field(default_factory=list)

    optional: OptionalSection = field(default_factory=OptionalSection)


# ─── CLI handlers (still stubs) ──────────────────────────────────────────────


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
