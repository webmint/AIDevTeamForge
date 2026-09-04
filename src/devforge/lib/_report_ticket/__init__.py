"""Internal package for report_ticket_helper (the /report-ticket command's mechanical work).

Submodules are underscore-prefixed.  External callers invoke via the POSIX
launcher `report_ticket_helper` or `report_ticket_helper.main`.

Public entry point is `main` (re-exported below).  Subcommand verbs are wired
in `_cli.py`; `main` dispatches to the selected handler.

Verbs:
  preflight     -- resolve workspace (install_root / source_root /
                    is_wrapper) via resolve_workspace (fail-soft to
                    standalone like _report_bug does); emit JSON
                    {tickets_dir, root, is_wrapper} to stdout.
  write-ticket  -- build a single item dict and call file_ticket() from
                    _shared/ticket_file.py.  The body argument is
                    --body-file <path> (or "-" for stdin) -- there is NO
                    inline --body (95-TICKET-CAPTURE-LANE-PLAN.md OQ-6).
                    Emits the written path as a JSON array to stdout.
"""

from ._cli import main

__all__ = ["main"]
