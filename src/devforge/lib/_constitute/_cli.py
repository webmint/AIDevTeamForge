"""argparse parser + dispatch + main entry for constitute_helper.

Dispatcher-only. All cmd_* handler bodies live in sibling modules:
  _cmds_set     — cmd_reset + 10 cmd_set_* / cmd_add_* setters
  _cmds_read    — read-init / read-configure / read-docs / read-glossary
  _cmds_render  — cmd_render + cmd_verify + cmd_summary
  _cmds_quality — cmd_validate + cmd_verify_universal_defaults
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from ._cmds_quality import cmd_validate, cmd_verify_universal_defaults
from ._forcing_functions._magic_enum._cmd import cmd_verify_magic_enum
from ._forcing_functions._cross_layer._cmd import cmd_verify_cross_layer_imports
from ._cmds_read import (
    cmd_read_configure,
    cmd_read_docs,
    cmd_read_glossary,
    cmd_read_init,
)
from ._cmds_render import cmd_render, cmd_summary, cmd_verify
from ._cmds_set import (
    cmd_add_code_example,
    cmd_add_pattern_rule,
    cmd_add_rule,
    cmd_add_section,
    cmd_add_table,
    cmd_reset,
    cmd_set_dates,
    cmd_set_mode,
    cmd_set_project_identity,
    cmd_set_project_name,
    cmd_set_scaffolding_guide,
)
from ._schema import _PATTERN_SCOPE_TO_SUFFIX, _SECTION_BUCKET_TO_KEY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="constitute_helper",
        description="State + render helper for /constitute. Owns constitution.md shape.",
    )
    parser.add_argument(
        "--devforge-dir",
        default=".devforge",
        help="Path to the .devforge directory (default: .devforge in CWD).",
    )
    parser.add_argument(
        "--install-root",
        default=None,
        help=(
            "Path to the install root (project root for standalone, wrapper root "
            "for wrapper mode). Default: parent of --devforge-dir."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    sp = subparsers.add_parser(
        "reset",
        help="Write a fresh defaults state file. Idempotent.",
    )
    sp.set_defaults(func=cmd_reset)

    sp = subparsers.add_parser(
        "read-init",
        help="Read .devforge/init.yaml and emit JSON to stdout.",
    )
    sp.set_defaults(func=cmd_read_init)

    sp = subparsers.add_parser(
        "read-configure",
        help="Read .devforge/configure.yaml and emit JSON to stdout.",
    )
    sp.set_defaults(func=cmd_read_configure)

    sp = subparsers.add_parser(
        "read-docs",
        help="Parse docs/overview.md + docs/architecture.md and emit JSON.",
    )
    sp.set_defaults(func=cmd_read_docs)

    sp = subparsers.add_parser(
        "read-glossary",
        help="Parse docs/glossary.md and emit JSON list of term records.",
    )
    sp.set_defaults(func=cmd_read_glossary)

    # -----------------------------------------------------------------------
    # Step 2 setters.
    # -----------------------------------------------------------------------

    sp = subparsers.add_parser(
        "set-project-name",
        help="Set project_name scalar.",
    )
    sp.add_argument("--value", required=True, help="Project name.")
    sp.set_defaults(func=cmd_set_project_name)

    sp = subparsers.add_parser(
        "set-mode",
        help="Set mode enum (existing-codebase | greenfield).",
    )
    sp.add_argument("--value", required=True, help="Mode value.")
    sp.set_defaults(func=cmd_set_mode)

    sp = subparsers.add_parser(
        "set-dates",
        help="Set generated_date and last_updated (both YYYY-MM-DD).",
    )
    sp.add_argument("--generated", required=True, help="Generated date (YYYY-MM-DD).")
    sp.add_argument("--updated", required=True, help="Last updated date (YYYY-MM-DD).")
    sp.set_defaults(func=cmd_set_dates)

    sp = subparsers.add_parser(
        "set-project-identity",
        help="Set project_identity record (name, type, domain, stack). Replaces prior value.",
    )
    sp.add_argument("--name", required=True, help="Project identity name.")
    sp.add_argument("--type", required=True, help="Project identity type.")
    sp.add_argument("--domain", required=True, help="Project identity domain.")
    sp.add_argument("--stack", required=True, help="Project identity stack.")
    sp.set_defaults(func=cmd_set_project_identity)

    sp = subparsers.add_parser(
        "add-section",
        help="Add (or update metadata of) a section in a bucket. Idempotent on (bucket, number).",
    )
    sp.add_argument(
        "--bucket",
        required=True,
        choices=list(_SECTION_BUCKET_TO_KEY.keys()),
        help="Section bucket (architecture | code-quality | domain | workflow).",
    )
    sp.add_argument("--number", required=True, help="Section number (e.g. '2', '2.1').")
    sp.add_argument("--title", required=True, help="Section title.")
    sp.add_argument(
        "--tag",
        default=None,
        help="Section tag (universal | project-specific | greenfield-only). Optional.",
    )
    sp.add_argument("--description", default=None, help="Section description. Optional.")
    sp.set_defaults(func=cmd_add_section)

    sp = subparsers.add_parser(
        "add-rule",
        help="Append a rule to the section identified by --section number.",
    )
    sp.add_argument("--section", required=True, help="Section number to append rule to.")
    sp.add_argument(
        "--tag",
        required=True,
        help="Rule tag (extracted | enforced | universal | project-specific).",
    )
    sp.add_argument("--text", required=True, help="Rule text.")
    sp.set_defaults(func=cmd_add_rule)

    sp = subparsers.add_parser(
        "add-table",
        help="Append a table to the section identified by --section number.",
    )
    sp.add_argument("--section", required=True, help="Section number to append table to.")
    sp.add_argument(
        "--columns",
        required=True,
        help="Column names as comma-separated string or JSON array.",
    )
    sp.add_argument(
        "--rows-json",
        required=True,
        dest="rows_json",
        help="Rows as JSON array of arrays of strings.",
    )
    sp.set_defaults(func=cmd_add_table)

    sp = subparsers.add_parser(
        "add-code-example",
        help="Append a code example to the section identified by --section number.",
    )
    sp.add_argument("--section", required=True, help="Section number to append code example to.")
    sp.add_argument(
        "--label",
        required=True,
        help="Code example label (CORRECT | WRONG | EXAMPLE).",
    )
    sp.add_argument("--language", required=True, help="Programming language.")
    sp.add_argument("--code", required=True, help="Code content (multi-line OK).")
    sp.add_argument("--annotation", default=None, help="Optional annotation text.")
    sp.set_defaults(func=cmd_add_code_example)

    sp = subparsers.add_parser(
        "add-pattern-rule",
        help="Append a rule to a patterns_and_antipatterns bucket.",
    )
    sp.add_argument(
        "--bucket",
        required=True,
        choices=["always", "never", "prefer"],
        help="Pattern bucket (always | never | prefer).",
    )
    sp.add_argument(
        "--scope",
        required=True,
        choices=list(_PATTERN_SCOPE_TO_SUFFIX.keys()),
        help="Scope (universal | project-specific).",
    )
    sp.add_argument(
        "--tag",
        required=True,
        help="Rule tag (extracted | enforced | universal | project-specific).",
    )
    sp.add_argument("--text", required=True, help="Pattern rule text.")
    sp.set_defaults(func=cmd_add_pattern_rule)

    sp = subparsers.add_parser(
        "set-scaffolding-guide",
        help="Set scaffolding_guide record (starter_directories + sample_files). Replaces prior value.",
    )
    sp.add_argument(
        "--starter-dirs",
        required=True,
        dest="starter_dirs",
        help="Starter directories as comma-separated string or JSON array.",
    )
    sp.add_argument(
        "--sample-files-json",
        required=True,
        dest="sample_files_json",
        help='Sample files as JSON array of {path, language, content} objects.',
    )
    sp.set_defaults(func=cmd_set_scaffolding_guide)

    # -----------------------------------------------------------------------
    # Step 3: render / verify / summary.
    # -----------------------------------------------------------------------

    sp = subparsers.add_parser(
        "render",
        help=(
            "Walk schema, concatenate constitution.md, atomic write to "
            "<install_root>/constitution.md."
        ),
    )
    sp.set_defaults(func=cmd_render)

    sp = subparsers.add_parser(
        "verify",
        help=(
            "Cross-check constitute.json for correctness + round-trip identity. "
            "Exit 0 = pass; exit 2 = violations (stderr enumerates)."
        ),
    )
    sp.set_defaults(func=cmd_verify)

    sp = subparsers.add_parser(
        "summary",
        help=(
            "Render constitute summary to stdout. Read-only. "
            "Exit 0 = success (incl. missing state → all-unset). "
            "Exit 1 = state file present but corrupted JSON."
        ),
    )
    sp.set_defaults(func=cmd_summary)

    sp = subparsers.add_parser(
        "validate",
        help=(
            "4-dimension content quality check: slot-fill, citation validity, "
            "code-example syntax, rule-tag enum. "
            "Exit 0 = composite >= 0.95. Exit 2 = below threshold. "
            "Exit 1 = state file unreadable."
        ),
    )
    sp.set_defaults(func=cmd_validate)

    # -----------------------------------------------------------------------
    # Consumer-facing forcing-function verbs.
    # -----------------------------------------------------------------------

    sp = subparsers.add_parser(
        "verify-magic-enum",
        help=(
            "Scan consumer source for string literals that duplicate generated "
            "enum member values instead of importing the enum. "
            "Exit 0 = clean or disabled. Exit 2 = violations found."
        ),
    )
    sp.add_argument(
        "--root",
        default=None,
        help="Consumer project root (default: current working directory).",
    )
    sp.add_argument(
        "--config",
        default=None,
        help=(
            "Path to constitute.json (default: <root>/.devforge/constitute.json)."
        ),
    )
    sp.set_defaults(func=cmd_verify_magic_enum)

    sp = subparsers.add_parser(
        "verify-cross-layer-imports",
        help=(
            "Scan consumer source for import statements that cross declared layer "
            "boundaries. Exit 0 = clean or disabled. Exit 2 = violations found or "
            "malformed layer_graph config."
        ),
    )
    sp.add_argument(
        "--root",
        default=None,
        help="Consumer project root (default: current working directory).",
    )
    sp.add_argument(
        "--config",
        default=None,
        help=(
            "Path to constitute.json (default: <root>/.devforge/constitute.json)."
        ),
    )
    sp.set_defaults(func=cmd_verify_cross_layer_imports)

    # -----------------------------------------------------------------------
    # forge-internal subcommands.
    # -----------------------------------------------------------------------

    sp = subparsers.add_parser(
        "forge-internal:verify-universal-defaults",
        help=(
            "Diff consumer .devforge/constitute.json universal sections vs "
            "canonical src/constitution.md. Maintainer-only."
        ),
    )
    sp.add_argument(
        "--consumer-path",
        required=True,
        dest="consumer_path",
        help="Consumer project root containing .devforge/constitute.json.",
    )
    sp.add_argument(
        "--canonical-path",
        default="src/constitution.md",
        dest="canonical_path",
        help="Canonical constitution.md path (default: src/constitution.md).",
    )
    sp.set_defaults(func=cmd_verify_universal_defaults)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2

    from pathlib import Path
    if args.install_root is None:
        args.install_root = str(Path(args.devforge_dir).resolve().parent)

    return args.func(args)
