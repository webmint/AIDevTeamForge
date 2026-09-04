"""Thin entry-point shim for /report-ticket helper — see _report_ticket/ for implementation.

User-facing ticket capture: resolves the tickets/ directory under install_root
(via resolve_workspace, fail-soft to standalone), builds a single item dict
from CLI arguments, and delegates writing to the shared file_ticket() writer.
All logic lives in `_report_ticket/`; this shim provides the stable POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_report_ticket` importable when this file is run as
# `python3 report_ticket_helper.py` from any cwd.  When invoked as a module
# via `python -m devforge.lib.report_ticket_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _report_ticket._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
