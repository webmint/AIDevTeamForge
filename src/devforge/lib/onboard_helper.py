"""onboard_helper — registers documentation artifacts for /onboard.

This helper accepts per-package and per-concern doc registrations from the
/onboard command, validates the cumulative state against structural gates,
and atomically composes `docs/` from the validated registrations. The
register-then-compose pattern enforces per-unit dispatch and prevents
bulk-script doc generation.

Stdlib only. No third-party dependencies.

REBUILD IN PROGRESS: subcommands are added incrementally during the spec
migration in .vault/. The reference implementation (with known issues) is
preserved at .vault/devforge/lib/onboard_helper.py.
"""

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onboard_helper",
        description="Register and compose onboard documentation artifacts.",
    )
    # Subcommands are registered here as they are implemented during spec
    # migration. See .vault/devforge/lib/onboard_helper.py for reference shape;
    # audit-identified anti-patterns must NOT be reproduced (see python-engineer
    # agent: Patterns to avoid).
    return parser


def main(argv=None):
    parser = build_parser()
    parser.parse_args(argv)
    sys.stderr.write(
        "onboard_helper: no subcommands registered yet. "
        "This helper is being rebuilt incrementally during the spec migration. "
        "Reference: .vault/devforge/lib/onboard_helper.py\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
