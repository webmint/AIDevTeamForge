"""argparse wiring + dispatch for the generate_docs helper.

This module is the Controller (per GRASP): a single entry point
(`main`) parses the CLI, looks up the handler in a registry, and
calls it. Subcommands are appended to `_SUBCOMMANDS` — adding a new
one means writing a parser-factory + handler in the appropriate
sibling module (`_setters` / `_setters_concern` for state mutation,
`_status` for read-only state inspection, `_manifest` for ecosystem
manifest extraction, `_render` for skeleton emission, `_validators`
for validation + final render) and adding one tuple here. The
dispatch path stays closed against modification (OCP).

The `_add_cite_args` factory is shared by eight subcommands — four
package-tier (`add-package-export`, `add-package-hazard`,
`set-package-usage-example`, `set-package-consumer-pattern`) and four
concern-tier (`add-concern-export`, `add-concern-type`,
`add-concern-hazard`, `set-concern-usage-example`) — all of which
accept the `--cite-file / --cite-start / --cite-end` triple.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import sys
from typing import Callable, List, Optional, Tuple

from ._manifest import cmd_extract_package_scripts
from ._render import (
    cmd_render_concern_skeleton,
    cmd_render_package_skeleton,
)
from ._setters import (
    cmd_add_package,
    cmd_add_package_dep,
    cmd_add_package_export,
    cmd_add_package_hazard,
    cmd_add_package_script,
    cmd_reset,
    cmd_set_package_build_tool,
    cmd_set_package_consumer_pattern,
    cmd_set_package_framework,
    cmd_set_package_language,
    cmd_set_package_overview,
    cmd_set_package_tree,
    cmd_set_package_usage_example,
)
from ._setters_concern import (
    cmd_add_concern,
    cmd_add_concern_dep,
    cmd_add_concern_export,
    cmd_add_concern_hazard,
    cmd_add_concern_type,
    cmd_set_concern_overview,
    cmd_set_concern_tree,
    cmd_set_concern_usage_example,
)
from ._status import cmd_status
from ._validators import (
    cmd_render_concern_doc,
    cmd_render_package_doc,
    cmd_validate_concern,
    cmd_validate_package,
)


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


def _build_set_package_consumer_pattern(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_status(p: argparse.ArgumentParser) -> None:
    pass


def _build_extract_package_scripts(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)


def _build_render_package_skeleton(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)


def _build_validate_package(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)


def _build_render_package_doc(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)


# ---------------------------------------------------------------------------
# Concern-tier parser factories (Phase 3.1).
#
# All concern subcommands take `--package` (the path of the parent
# package) and `--concern` (the concern_name). The two-key form
# distinguishes concerns from package-tier subcommands which use
# `--path`. A concern is uniquely identified by the `(package, concern)`
# pair across the state file.
# ---------------------------------------------------------------------------


def _build_add_concern(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)


def _build_set_concern_overview(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--text", required=True)


def _build_set_concern_tree(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--text", required=True)


def _build_add_concern_export(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--signature", default="")
    p.add_argument("--description", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_add_concern_type(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_add_concern_dep(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--version", default="")
    p.add_argument("--purpose", required=True)
    p.add_argument("--consumer-location", action="append", default=None)


def _build_add_concern_hazard(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--category", required=True)
    p.add_argument("--description", required=True)
    _add_cite_args(p, optional=True)


def _build_set_concern_usage_example(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_render_concern_skeleton(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)


def _build_validate_concern(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)


def _build_render_concern_doc(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)


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
    ("set-package-consumer-pattern", _build_set_package_consumer_pattern, cmd_set_package_consumer_pattern),
    ("status", _build_status, cmd_status),
    ("extract-package-scripts", _build_extract_package_scripts, cmd_extract_package_scripts),
    ("render-package-skeleton", _build_render_package_skeleton, cmd_render_package_skeleton),
    ("validate-package", _build_validate_package, cmd_validate_package),
    ("render-package-doc", _build_render_package_doc, cmd_render_package_doc),
    # Concern-tier subcommands (Phase 3.1).
    ("add-concern", _build_add_concern, cmd_add_concern),
    ("set-concern-overview", _build_set_concern_overview, cmd_set_concern_overview),
    ("set-concern-tree", _build_set_concern_tree, cmd_set_concern_tree),
    ("add-concern-export", _build_add_concern_export, cmd_add_concern_export),
    ("add-concern-type", _build_add_concern_type, cmd_add_concern_type),
    ("add-concern-dep", _build_add_concern_dep, cmd_add_concern_dep),
    ("add-concern-hazard", _build_add_concern_hazard, cmd_add_concern_hazard),
    ("set-concern-usage-example", _build_set_concern_usage_example, cmd_set_concern_usage_example),
    ("render-concern-skeleton", _build_render_concern_skeleton, cmd_render_concern_skeleton),
    ("validate-concern", _build_validate_concern, cmd_validate_concern),
    ("render-concern-doc", _build_render_concern_doc, cmd_render_concern_doc),
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
