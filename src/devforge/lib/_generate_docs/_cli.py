"""argparse wiring + dispatch for the generate_docs helper.

This module is the Controller (per GRASP): a single entry point
(`main`) parses the CLI, looks up the handler in a registry, and
calls it. Subcommands are appended to `_SUBCOMMANDS` — adding a new
one means writing a parser-factory + handler in the appropriate
sibling module (`_setters`, `_status`, `_manifest`) and adding one
tuple here. The dispatch path stays closed against modification
(OCP).

The `_add_cite_args` factory is shared by three subcommands
(`add-package-export`, `add-package-hazard`, `set-package-usage-example`)
that all accept the `--cite-file / --cite-start / --cite-end` triple.
That's the Rule of Three threshold for DRY — three concrete sites of
the same shape — so the factory is justified rather than premature.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import sys
from typing import Callable, List, Optional, Tuple

from ._manifest import cmd_extract_package_scripts
from ._setters import (
    cmd_add_package,
    cmd_add_package_dep,
    cmd_add_package_export,
    cmd_add_package_hazard,
    cmd_add_package_script,
    cmd_reset,
    cmd_set_package_build_tool,
    cmd_set_package_framework,
    cmd_set_package_language,
    cmd_set_package_overview,
    cmd_set_package_tree,
    cmd_set_package_usage_example,
)
from ._status import cmd_status


# Each parser-factory takes the subparsers' `add_parser`-returned
# `argparse.ArgumentParser` and adds its own `--*` arguments to it.
# It returns nothing (the parser is mutated in place).
_ParserFactory = Callable[[argparse.ArgumentParser], None]
_Handler = Callable[[argparse.Namespace], int]


def _add_cite_args(parser: argparse.ArgumentParser, optional: bool) -> None:
    """Add the `--cite-file / --cite-start / --cite-end` triple.

    `optional=True` makes all three arguments default to None (used by
    `add-package-hazard`, where the cite is itself optional). Required
    sites pass `optional=False` so argparse rejects missing values.
    """
    if optional:
        parser.add_argument("--cite-file", default=None)
        parser.add_argument("--cite-start", default=None, type=int)
        parser.add_argument("--cite-end", default=None, type=int)
    else:
        parser.add_argument("--cite-file", required=True)
        parser.add_argument("--cite-start", required=True, type=int)
        parser.add_argument("--cite-end", required=True, type=int)


# ---------------------------------------------------------------------------
# Per-subcommand parser factories.
# ---------------------------------------------------------------------------


def _build_reset(p: argparse.ArgumentParser) -> None:
    pass


def _build_add_package(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--name", required=True)


def _build_set_package_overview(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--text", required=True)


def _build_set_package_tree(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--text", required=True)


def _build_set_package_language(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--value", required=True)


def _build_set_package_framework(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--value", required=True)


def _build_set_package_build_tool(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--value", required=True)


def _build_add_package_script(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--script-name", required=True)
    p.add_argument("--command", required=True)


def _build_add_package_export(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--signature", default="")
    p.add_argument("--description", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_add_package_dep(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--version", default="")
    p.add_argument("--purpose", required=True)
    p.add_argument("--consumer-location", action="append", default=None)


def _build_add_package_hazard(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--category", required=True)
    p.add_argument("--description", required=True)
    _add_cite_args(p, optional=True)


def _build_set_package_usage_example(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_status(p: argparse.ArgumentParser) -> None:
    pass


def _build_extract_package_scripts(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)


# ---------------------------------------------------------------------------
# Subcommand registry. Append to extend.
# ---------------------------------------------------------------------------


_SUBCOMMANDS: Tuple[Tuple[str, _ParserFactory, _Handler], ...] = (
    ("reset", _build_reset, cmd_reset),
    ("add-package", _build_add_package, cmd_add_package),
    ("set-package-overview", _build_set_package_overview, cmd_set_package_overview),
    ("set-package-tree", _build_set_package_tree, cmd_set_package_tree),
    ("set-package-language", _build_set_package_language, cmd_set_package_language),
    ("set-package-framework", _build_set_package_framework, cmd_set_package_framework),
    ("set-package-build-tool", _build_set_package_build_tool, cmd_set_package_build_tool),
    ("add-package-script", _build_add_package_script, cmd_add_package_script),
    ("add-package-export", _build_add_package_export, cmd_add_package_export),
    ("add-package-dep", _build_add_package_dep, cmd_add_package_dep),
    ("add-package-hazard", _build_add_package_hazard, cmd_add_package_hazard),
    ("set-package-usage-example", _build_set_package_usage_example, cmd_set_package_usage_example),
    ("status", _build_status, cmd_status),
    ("extract-package-scripts", _build_extract_package_scripts, cmd_extract_package_scripts),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_docs_helper",
        description="State + setters for /generate-docs (PackageDoc tier).",
    )
    sub = parser.add_subparsers(dest="subcommand")
    for name, factory, handler in _SUBCOMMANDS:
        p = sub.add_parser(name)
        factory(p)
        p.set_defaults(func=handler)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)
