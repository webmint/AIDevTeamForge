#!/usr/bin/env python3
"""verify-agent-reachability.py — maintainer-side CLI for the agent-executor check.

Runs the reachability check from ``scripts/lib/agent_reachability.py`` against
the live ``src/`` tree in this repository, prints a human-readable report, and
exits non-zero if any orphan, unknown assignment, or relay-only violation is found.

Exit codes
----------
0  — all clear (every roster agent has an executor; no unknown assignments)
1  — one or more violations found (report printed to stdout)
2  — internal error (e.g., src/ directory not found)

SCOPE (D5/D8)
-------------
This check covers type-1 (orphaned agent) and unknown-assignment only.
It does NOT cover type-2 forward-prose ("verified at X") or type-3
finding-inertness.  A passing run MUST NOT be read as full orphan coverage.

Usage
-----
    python3 scripts/verify-agent-reachability.py [<repo-root>]

If ``<repo-root>`` is omitted the parent directory of this script's location
is used (which is the repo root when the script lives at ``scripts/``).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution: make scripts/lib importable
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent
_SCRIPTS_LIB = _SCRIPTS_DIR / "lib"
if str(_SCRIPTS_LIB) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_LIB))

from agent_reachability import find_orphans, RELAY_ONLY_ALLOWLIST  # noqa: E402


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

    result = find_orphans(repo_root)

    orphans = result["orphan_agents"]
    unknowns = result["unknown_assignments"]
    relay_only = result["relay_only"]

    has_violation = bool(orphans or unknowns or relay_only)

    # -----------------------------------------------------------------------
    # Report
    # -----------------------------------------------------------------------
    print("Agent-executor reachability check")
    print("Repo root : {}".format(repo_root))
    print("Scope     : type-1 (orphaned agent) + unknown-assignment only.")
    print("            Does NOT cover type-2 forward-prose or type-3 finding-inertness.")
    print()

    if orphans:
        print("FAIL — orphaned agents (roster agent with no executor path):")
        for name in orphans:
            relay_note = " [relay-only, no real executor]" if name in relay_only else ""
            print("  - {}{}".format(name, relay_note))
        print()
    else:
        print("PASS — all roster agents have at least one executor path.")

    if relay_only:
        already_listed = set(orphans)  # these also appear in orphan_agents
        relay_only_not_orphaned = [r for r in relay_only if r not in already_listed]
        if relay_only_not_orphaned:
            print("FAIL — relay-only agents (reachable ONLY via relay, not an executor):")
            for name in relay_only_not_orphaned:
                print("  - {}".format(name))
            print()
        if RELAY_ONLY_ALLOWLIST:
            print("INFO — relay-only allowlist (these agents are exempt):")
            for name in sorted(RELAY_ONLY_ALLOWLIST):
                print("  - {}".format(name))
            print()

    if unknowns:
        print("FAIL — unknown assignments in /breakdown table (not in roster):")
        for name in unknowns:
            print("  - {}".format(name))
        print()
    else:
        print("PASS — all /breakdown Agent Assignment table names exist in the roster.")

    print()
    if has_violation:
        print("Result: FAIL ({} orphan(s), {} unknown(s), {} relay-only violation(s))".format(
            len(orphans), len(unknowns), len(relay_only)
        ))
        return 1
    else:
        print("Result: PASS — no orphans, no unknown assignments, no relay-only violations.")
        return 0


if __name__ == "__main__":
    sys.exit(_main())
