"""Forcing-functions subparser registration — register_subparsers(subparsers).

Moved out of ``_constitute/_cli.py`` in a behavior-preserving restructure
(plan 104 Phase 3 Unit D follow-up): that module was pushed past the
600-line automatic-HIGH-finding threshold. Mirrors the
``_register_subcommands(subparsers)`` pattern other packages' ``_cli.py``
use (e.g. ``_research/_cli.py``); called from ``_constitute._cli.build_parser``
at the exact position this block occupied, so subcommand registration ORDER
is unchanged.

Covers the six verbs whose handlers live under this package: the four
consumer-facing scan verbs (``verify-magic-enum``, ``verify-cross-layer-
imports``, ``verify-any-leak``, ``verify-design-tokens``) and the two
forcing-functions config setters (``set-forcing-functions``,
``list-forcing-functions``). ``forge-internal:verify-forcing-function-keys``
is NOT here — its registration sits in ``_constitute/_cli.py``'s
"forge-internal subcommands" block (alongside
``forge-internal:verify-universal-defaults``) and its handler
(``cmd_verify_forcing_function_keys``) lives in ``_cmds_quality.py``, not
under this package.
"""

from __future__ import annotations

from ._any_leak._cmd import cmd_verify_any_leak
from ._cmds_forcing_functions import cmd_list_forcing_functions, cmd_set_forcing_functions
from ._cross_layer._cmd import cmd_verify_cross_layer_imports
from ._design_tokens._cmd import cmd_verify_design_tokens
from ._magic_enum._cmd import cmd_verify_magic_enum


def register_subparsers(subparsers) -> None:
    """Attach the six forcing-functions subcommands to `subparsers`."""

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

    sp = subparsers.add_parser(
        "verify-any-leak",
        help=(
            "Scan consumer source for explicit ``any`` annotations / casts / "
            "generics in files that import from declared generated-types dirs. "
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
    sp.set_defaults(func=cmd_verify_any_leak)

    sp = subparsers.add_parser(
        "verify-design-tokens",
        help=(
            "Scan component style sources (CSS / styled-components / CSS-in-JS) "
            "for design-token provenance violations: hardcoded color literals, "
            "var() fallbacks, undefined tokens, and missing :hover/:focus-visible "
            "states. "
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
    sp.set_defaults(func=cmd_verify_design_tokens)

    # -----------------------------------------------------------------------
    # Forcing-functions config setters.
    # -----------------------------------------------------------------------

    sp = subparsers.add_parser(
        "set-forcing-functions",
        help=(
            "Write or update a forcing_functions.<rule> block in "
            ".devforge/constitute.json. "
            "Validates per-rule required fields."
        ),
    )
    from .._schema import FORCING_FUNCTION_RULES as _FF_RULES
    sp.add_argument(
        "--rule",
        required=True,
        choices=sorted(_FF_RULES),
        help=(
            "Rule to configure: any_with_generated_available | cross_layer_imports | "
            "design_token_provenance | magic_enum_duplication."
        ),
    )
    sp.add_argument(
        "--enabled",
        required=True,
        choices=["true", "false"],
        help="Enable or disable the rule.",
    )
    sp.add_argument(
        "--generated-types-dirs",
        default=None,
        dest="generated_types_dirs",
        help=(
            "Comma-separated list of generated-types source dirs (relative to "
            "project root). Required when --enabled=true for "
            "magic_enum_duplication and any_with_generated_available."
        ),
    )
    sp.add_argument(
        "--allowlist-paths",
        default=None,
        dest="allowlist_paths",
        help="Comma-separated list of glob patterns for path-level exemptions.",
    )
    sp.add_argument(
        "--layer-graph-json",
        default=None,
        dest="layer_graph_json",
        help=(
            "JSON object: layer name → list of layer names it may import from. "
            "Required when --enabled=true for cross_layer_imports."
        ),
    )
    sp.add_argument(
        "--layer-dirs-json",
        default=None,
        dest="layer_dirs_json",
        help=(
            "JSON object: layer name → glob pattern for that layer's source dirs. "
            "Keys must match --layer-graph-json. "
            "Required when --enabled=true for cross_layer_imports."
        ),
    )
    sp.add_argument(
        "--token-source-css",
        default=None,
        dest="token_source_css",
        help=(
            "Path (relative to project root) to the CSS token source file "
            "(e.g., design/styles.css). Optional for design_token_provenance. "
            "Used by Check 3 (undefined token)."
        ),
    )
    sp.add_argument(
        "--manifest-path",
        default=None,
        dest="manifest_path",
        help=(
            "Path (relative to project root) to a disposition manifest JSON "
            "(design_token_provenance only). Retained for config back-compat only "
            "-- the disposition-manifest consumer (formerly Check 5) was retired "
            "in plan 53 Phase 7a; this value is stored but no longer read."
        ),
    )
    sp.add_argument(
        "--config",
        default=None,
        help=(
            "Path to constitute.json "
            "(default: <cwd>/.devforge/constitute.json)."
        ),
    )
    sp.set_defaults(func=cmd_set_forcing_functions)

    sp = subparsers.add_parser(
        "list-forcing-functions",
        help=(
            "List configured forcing-function rule names, one per line. "
            "Machine-readable for use by the pre-commit hook. "
            "Exit 0 = success (zero or more lines). "
            "Exit 1 = config present but unreadable."
        ),
    )
    sp.add_argument(
        "--enabled",
        action="store_true",
        dest="enabled_only",
        default=False,
        help="Print only rules with enabled: true.",
    )
    sp.add_argument(
        "--format",
        default="key",
        choices=["key", "verb"],
        dest="format",
        help=(
            "Output format: 'key' (config key, default) or 'verb' "
            "(CLI verb accepted by constitute_helper, e.g. verify-magic-enum). "
            "Used by the pre-commit hook."
        ),
    )
    sp.add_argument(
        "--config",
        default=None,
        help=(
            "Path to constitute.json "
            "(default: <cwd>/.devforge/constitute.json)."
        ),
    )
    sp.set_defaults(func=cmd_list_forcing_functions)
