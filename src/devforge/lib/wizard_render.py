"""wizard_render — composes Phase 3 + Phase 4 file population for /setup-wizard.

This helper substitutes user-supplied values into template files (CLAUDE.md,
constitution.md, agent files, docs/) and atomically writes the populated
results. It is the bridge between user answers (collected in Phase 2) and
the on-disk state of the configured project.

Stdlib only. No third-party dependencies.

REBUILD IN PROGRESS: subcommands are added incrementally during the spec
migration in .vault/setup-wizard/. The reference implementation (with known
issues) is preserved at .vault/devforge/lib/wizard_render.py.
"""

import argparse
import os
import sys
from pathlib import Path

# State file name (leading dot keeps it hidden in `.devforge/` listings).
STATE_FILE_NAME = ".wizard-render-state.json"


def _state_file_path():
    """Resolve the state file path at call time (not import time).

    Honors the `DEVFORGE_DIR` environment variable when set — used by tests
    and by unusual install layouts. When unset, computes the path from this
    script's own location: `<target>/.devforge/lib/wizard_render.py` lives
    one directory below `<target>/.devforge/`, where the state file belongs.

    Returning a fresh Path each call (rather than caching at import) keeps
    tests free of monkey-patching: each test sets `DEVFORGE_DIR` and the
    next resolution sees the override.
    """
    env_dir = os.environ.get("DEVFORGE_DIR")
    if env_dir:
        return Path(env_dir) / STATE_FILE_NAME
    return Path(__file__).resolve().parent.parent / STATE_FILE_NAME


def cmd_reset(args):
    """Delete the state file. Idempotent.

    - Missing state file: exit 0, no output (clean no-op).
    - Existing state file (any content): unlink, exit 0.
    - State path is a directory or unlinking fails: write a clear error to
      stderr naming the path and the OS error, return non-zero.

    Reset never reads the file's contents — empty, valid JSON, and invalid
    JSON are all handled identically by `os.unlink`.
    """
    path = _state_file_path()
    try:
        os.unlink(str(path))
    except FileNotFoundError:
        # Idempotent: nothing to delete.
        return 0
    except OSError as err:
        sys.stderr.write(
            "wizard_render reset: cannot delete {0}: {1}\n".format(str(path), err)
        )
        return 1
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wizard_render",
        description="Compose Phase 3 + Phase 4 file population for /setup-wizard.",
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    reset_parser = subparsers.add_parser(
        "reset",
        help="Delete the helper's state file. Idempotent.",
    )
    reset_parser.set_defaults(func=cmd_reset)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        sys.stderr.write(
            "wizard_render: no subcommands registered yet. "
            "This helper is being rebuilt incrementally during the spec migration. "
            "Reference: .vault/devforge/lib/wizard_render.py\n"
        )
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
