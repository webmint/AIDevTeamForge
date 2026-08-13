#!/usr/bin/env python3
"""verify-memory-lane.py — maintainer-side CLI for the memory-lane coverage check.

Runs the coverage check from ``scripts/lib/memory_lane.py`` against the live
``src/`` tree in this repository, prints a human-readable report, and exits
non-zero if any coverage gap is found.

Exit codes
----------
0  — all clear (every READS command reads memory AND names the field it
     reads; every N/A command carries none of the memory tokens; no dead
     path literal under src/)
1  — one or more violations found (report printed to stdout)
2  — internal error (e.g. src/ or scripts/emitters/claude.py not found)

SCOPE — honest non-coverage
----------------------------
This check verifies that a memory read is PERFORMED for READS commands AND
that a consuming surface NAMES the field it reads. Rule 2 is CONJUNCTIVE —
both halves must hold; a command whose only memory touchpoint is a helper
preflight that nobody reads back still FAILS. It does NOT verify that the
consumption is substantive, that the right memory entries were selected,
or that memory.md's content is accurate. A PASS is not a claim about
memory quality — see scripts/lib/memory_lane.py's module docstring for the
full statement.

Usage
-----
    python3 scripts/verify-memory-lane.py [<repo-root>]

If ``<repo-root>`` is omitted the parent directory of this script's
location is used (which is the repo root when the script lives at
``scripts/``).
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution: make scripts/lib importable
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent
_SCRIPTS_LIB = _SCRIPTS_DIR / "lib"
if str(_SCRIPTS_LIB) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_LIB))

from memory_lane import DISPOSITIONS, find_gaps  # noqa: E402


def _main(argv=None):
    # type: (object) -> int
    if argv is None:
        argv = sys.argv[1:]

    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    # Determine repo root
    if argv:
        repo_root = Path(argv[0])
    else:
        # scripts/ lives directly under the repo root
        repo_root = _SCRIPTS_DIR.parent

    src_dir = repo_root / "src"
    if not src_dir.is_dir():
        sys.stderr.write(
            "error: src/ not found under {}\n".format(repo_root)
        )
        return 2

    emitter_path = repo_root / "scripts" / "emitters" / "claude.py"
    if not emitter_path.is_file():
        sys.stderr.write(
            "error: scripts/emitters/claude.py not found under {}\n".format(repo_root)
        )
        return 2

    result = find_gaps(repo_root)

    no_disposition = result["no_disposition"]
    empty_reason = result["empty_reason"]
    missing_read = result["reads_missing_helper_read"]
    missing_named = result["reads_missing_consumption"]
    na_leaks = result["na_leaks_memory"]
    dead_path = result["dead_path_literal"]

    has_violation = any([
        no_disposition, empty_reason, missing_read, missing_named,
        na_leaks, dead_path,
    ])

    # -------------------------------------------------------------------
    # Report
    # -------------------------------------------------------------------
    print("Memory-lane coverage check")
    print("Repo root : {}".format(repo_root))
    print("Scope     : verifies a memory READ is performed for READS commands AND that a")
    print("            consuming surface NAMES the field it reads (memory_excerpt /")
    print("            memory_digest / memory_state). Rule 2 is CONJUNCTIVE — both must")
    print("            hold; a preflight-only touchpoint with nobody reading it back FAILS.")
    print("            Verifies N/A commands carry none of those tokens. Verifies the dead")
    print("            '.claude/memory' path literal is absent from src/.")
    print("Does NOT verify: that a named field's consumption is SUBSTANTIVE, that the right")
    print("            memory entries were selected, or that memory.md's content is")
    print("            accurate. A PASS is not a claim about memory quality.")
    print()

    if no_disposition or empty_reason:
        if no_disposition:
            print("FAIL — commands in _PROMOTED with no disposition (Rule 1a):")
            for name in no_disposition:
                print("  - {}".format(name))
            print()
        if empty_reason:
            print("FAIL — commands with a disposition but an empty reason (Rule 1b):")
            for name in empty_reason:
                print("  - {}".format(name))
            print()
    else:
        print("PASS — every _PROMOTED command has exactly one disposition with a reason.")

    if missing_read or missing_named:
        if missing_read:
            print("FAIL — READS commands performing NO memory read at all (Rule 2a):")
            for name in missing_read:
                print("  - {}".format(name))
            print()
        if missing_named:
            print("FAIL — READS commands with no consuming surface naming the field it reads (Rule 2b):")
            for name in missing_named:
                if name in missing_read:
                    note = " [also fails Rule 2a — no read performed at all]"
                else:
                    note = " [a preflight/resolver reads it, nobody names it — the orphaned-payload case]"
                print("  - {}{}".format(name, note))
            print()
    else:
        print("PASS — every READS command performs a read AND names the field it reads.")

    if na_leaks:
        print("FAIL — N/A commands carrying a memory token (Rule 3):")
        for name in na_leaks:
            print("  - {}".format(name))
        print()
    else:
        print("PASS — no N/A command carries memory_excerpt / memory_digest / memory_state.")

    if dead_path:
        print("FAIL — dead '.claude/memory' literal found under src/ (Rule 4):")
        for hit in dead_path:
            print("  - {}".format(hit))
        print()
    else:
        print("PASS — no '.claude/memory' literal under src/.")

    print()
    if has_violation:
        n = (
            len(no_disposition) + len(empty_reason) + len(missing_read)
            + len(missing_named) + len(na_leaks) + len(dead_path)
        )
        print("Result: FAIL ({} violation(s))".format(n))
        return 1
    else:
        print("Result: PASS — no memory-lane coverage gaps found.")
        return 0


if __name__ == "__main__":
    sys.exit(_main())
