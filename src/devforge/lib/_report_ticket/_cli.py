"""argparse parser + dispatch + main entry for report_ticket_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Mirrors _report_bug/_cli.py in structure -- verb-registry pattern with
_SUBCOMMAND_REGISTRY of (verb_name, help_text, handler) triples.

Verbs:
  preflight     -- resolve workspace via resolve_workspace (fail-soft);
                    emit JSON {tickets_dir, root, is_wrapper} to stdout;
                    exit 0.
  write-ticket  -- validate args, build one item dict, call
                    file_ticket() from _shared/ticket_file.py, emit the
                    written path as a JSON array; exit 0 ok, exit 2 arg
                    error, exit 1 I/O error.

⚠ write-ticket's body argument deliberately diverges from write-bug's
inline --description: the body travels as --body-file <path> (or "-" on
stdin) ONLY (95-TICKET-CAPTURE-LANE-PLAN.md OQ-6, ratified).  A pasted
ticket body routinely contains backticks and $(...) sequences, which are
command substitution inside a double-quoted shell argument -- there is
NO inline --body, and adding one re-opens OQ-6 by omission.

Extension point: append to _SUBCOMMAND_REGISTRY and add the argument block
in the elif chain in _register_subcommands.
"""

from __future__ import annotations

import argparse
import json
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_TYPES = ("enhancement", "task", "imported")
_VALID_SOURCES = ("manual", "paste")


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_preflight(args):
    # type: (argparse.Namespace) -> int
    """Resolve workspace and emit tickets/ directory context.

    Always emits JSON to stdout.  Returns 0 -- this verb never fails;
    workspace resolution is fail-soft (standalone on any config error).
    tickets_dir = <install_root>/tickets (created on write, not on
    preflight).

    JSON shape:
      {
        "tickets_dir": "<absolute path>/tickets",
        "root":        "<absolute install_root>",
        "is_wrapper":  bool
      }
    """
    # Resolve _implement._workspace lazily so import errors surface here.
    from _implement._workspace import resolve_workspace

    workspace_root = getattr(args, "workspace_root", ".") or "."

    ws = resolve_workspace(workspace_root)

    tickets_dir = str(ws.install_root / "tickets")

    result = {
        "tickets_dir": tickets_dir,
        "root": str(ws.install_root),
        "is_wrapper": ws.is_wrapper,
    }

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_write_ticket(args):
    # type: (argparse.Namespace) -> int
    """Build one item dict and write it via file_ticket().

    Argument errors (missing --tickets-dir/--date/--body-file/--type,
    bad --type/--source, bad --ticket, empty --body-file content) -> exit
    2, and nothing is written.  I/O errors (cannot read --body-file,
    cannot create tickets_dir, cannot write) -> exit 1.  Success -> emit
    the written path as a JSON array, exit 0.
    """
    from _shared.feature_alloc import normalize_ticket
    from _shared.ticket_file import file_ticket

    # --- Required argument validation (arg-shape only, no I/O yet) -----------

    tickets_dir = getattr(args, "tickets_dir", None) or ""
    if not tickets_dir:
        sys.stderr.write(
            "report_ticket_helper write-ticket: --tickets-dir is required\n"
        )
        return 2

    date = getattr(args, "date", None) or ""
    if not date:
        sys.stderr.write(
            "report_ticket_helper write-ticket: --date is required "
            "(YYYY-MM-DD)\n"
        )
        return 2

    body_file = getattr(args, "body_file", None) or ""
    if not body_file:
        sys.stderr.write(
            "report_ticket_helper write-ticket: --body-file is required "
            "(pass - to read from stdin)\n"
        )
        return 2

    ticket_type = getattr(args, "type", None) or ""
    if ticket_type not in _VALID_TYPES:
        sys.stderr.write(
            "report_ticket_helper write-ticket: --type must be one of "
            "{0}; got: {1!r}\n".format(", ".join(_VALID_TYPES), ticket_type)
        )
        return 2

    source = getattr(args, "source", None) or "manual"
    if source not in _VALID_SOURCES:
        sys.stderr.write(
            "report_ticket_helper write-ticket: --source must be one of "
            "{0}; got: {1!r}\n".format(", ".join(_VALID_SOURCES), source)
        )
        return 2

    # --- --ticket: shape-validate via the single owner, never re-declared ----

    raw_ticket = getattr(args, "ticket", None)
    ticket_id = ""
    if raw_ticket is not None:
        normalized, error = normalize_ticket(raw_ticket)
        if error:
            sys.stderr.write(
                "report_ticket_helper write-ticket: --ticket {0}\n".format(error)
            )
            return 2
        ticket_id = normalized

    title = getattr(args, "title", None) or ""

    # --- Read the body (the one I/O operation this verb performs before ------
    # --- the write itself) ----------------------------------------------------

    if body_file == "-":
        body = sys.stdin.read()
    else:
        try:
            with open(body_file, "r", encoding="utf-8", newline="") as fh:
                body = fh.read()
        except OSError as exc:
            sys.stderr.write(
                "report_ticket_helper write-ticket: cannot read --body-file: "
                "{0}\n".format(exc)
            )
            return 1

    if not body.strip():
        sys.stderr.write(
            "report_ticket_helper write-ticket: --body-file content is empty\n"
        )
        return 2

    # --- Build item dict --------------------------------------------------

    item = {
        "title": title,
        "body": body,
        "type": ticket_type,
        "ticket": ticket_id,
    }

    # --- Write via the shared writer ------------------------------------------
    try:
        written = file_ticket(
            tickets_dir=tickets_dir,
            item=item,
            date=date,
            source=source,
        )
    except OSError as exc:
        sys.stderr.write(
            "report_ticket_helper write-ticket: I/O error writing ticket "
            "file: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps([written], indent=2) + "\n")
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
            "Resolve workspace (install_root / source_root / is_wrapper) "
            "via resolve_workspace; emit JSON {tickets_dir, root, "
            "is_wrapper} to stdout.  Fail-soft to standalone on any "
            "config error."
        ),
        cmd_preflight,
    ),
    (
        "write-ticket",
        (
            "Build a single item dict and write it to "
            "tickets/NNN-<slug>.md via the shared file_ticket() writer. "
            "The body travels as --body-file <path> (or - for stdin) "
            "only.  Emits the written path as a JSON array to stdout."
        ),
        cmd_write_ticket,
    ),
]


def build_parser():
    # type: () -> argparse.ArgumentParser
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="report_ticket_helper",
        description=(
            "Helper for /devforge:report-ticket -- user-facing ticket "
            "capture command. Resolves the tickets/ directory under "
            "install_root and writes ticket captures in "
            "tickets/NNN-<slug>.md format via the shared file_ticket() "
            "writer."
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
                    "Workspace root to resolve.  In wrapper mode this is "
                    "the wrapper root (not the project sub-directory). "
                    "Default: CWD."
                ),
            )

        elif verb == "write-ticket":
            sp.add_argument(
                "--tickets-dir",
                required=True,
                dest="tickets_dir",
                metavar="DIR",
                help="Absolute path to the tickets/ directory (from preflight output).",
            )
            sp.add_argument(
                "--date",
                required=True,
                metavar="YYYY-MM-DD",
                help=(
                    "Report date in YYYY-MM-DD format.  REQUIRED -- "
                    "the helper never calls the clock."
                ),
            )
            sp.add_argument(
                "--body-file",
                required=True,
                dest="body_file",
                metavar="PATH",
                help=(
                    "Path to a file containing the ticket body.  Pass - "
                    "to read from stdin.  There is NO inline --body: a "
                    "pasted body must never cross a shell argument "
                    "boundary (backticks and $(...) are command "
                    "substitution inside a double-quoted argument)."
                ),
            )
            sp.add_argument(
                "--title",
                default=None,
                metavar="TEXT",
                help=(
                    "Optional short title (the H1).  Falls back to the "
                    "first non-empty line of the body when omitted."
                ),
            )
            sp.add_argument(
                "--type",
                required=True,
                choices=list(_VALID_TYPES),
                metavar="TYPE",
                help="enhancement | task | imported.",
            )
            sp.add_argument(
                "--source",
                default="manual",
                choices=list(_VALID_SOURCES),
                metavar="SOURCE",
                help="manual | paste.  Default: manual.",
            )
            sp.add_argument(
                "--ticket",
                default=None,
                metavar="ID",
                help=(
                    "Optional tracker ticket ID, shape LETTERS-NUMBER "
                    "(e.g. PROJ-123).  Validated via normalize_ticket; "
                    "absent renders (none) in the file."
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
