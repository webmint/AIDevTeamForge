"""Thin entry-point shim for profile_helper -- see _profile/ for implementation.

Standalone diagnostic tool (plan 70) -- not wired to any /devforge:<name>
slash command.

Transcript wall-clock profiler (plan 70): reads a Claude Code session
transcript (or auto-locates the latest one for the project) and reports,
per pipeline command, the wall-clock split into LLM turn time, Bash/helper
time, agent sub-session time, and human-answer time.  Diagnostic only --
no pass/fail semantics, no runtime hooks, no pipeline wiring.  All logic
lives in `_profile/`; this shim provides the stable POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_profile` importable when this file is run as
# `python3 profile_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.profile_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _profile._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
