"""Thin entry-point shim for /spec-check helper -- see _spec_check/ for implementation.

Per-feature acceptance-criteria consistency prover: formalizes ACs into a
Z3-solvable IR, proves (or disproves) mutual satisfiability, and on a proven
contradiction generates spec-check-seed.json for consumption by the
/spec-check slash command's REVISE-SPEC re-entry arm.
All logic lives in `_spec_check/`; this shim provides the stable POSIX
launcher path.
"""

import sys
from pathlib import Path

# Make `_spec_check` importable when this file is run as
# `python3 spec_check_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.spec_check_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _spec_check._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
