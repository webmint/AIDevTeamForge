"""constitute_helper — composes the constitution.md state file for /constitute.

Owns the shape of `.devforge/constitute.json` (canonical state) and
`<install_root>/constitution.md` (render artifact). Schema-anchored:
helper owns markdown structure, LLM provides values via setters. Mirrors
the helper-owns-shape pattern established by init_helper / configure_helper /
generate_docs_helper.

`/constitute` is the fourth and last command in the 4-command pivot
(init-forge → generate-docs → configure → constitute).

Step 0 (this commit): scaffolding — argparse + `reset` subcommand only.
The state file format is JSON (not YAML — see CONSTITUTE-PLAN.md Open
Decisions): constitute data is 2-3 levels deep (Section → rules + tables +
code_examples per bucket per scope) and JSON's native nesting fits cleaner
than extending the configure-style YAML emitter to handle the depth.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Union


OUTPUT_FILE_NAME = "constitute.json"


def _output_file_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    """Return the canonical state file path for the given devforge dir."""
    return Path(devforge_dir) / OUTPUT_FILE_NAME


def default_state() -> dict:
    """Return a fresh defaults state dict.

    Step 0 stub: skeleton only. Step 1 fills FIELD_SCHEMA-driven defaults
    (project_identity / mode / dates / 5 section buckets / patterns_and_
    antipatterns 6-bucket struct / scaffolding_guide nullable).
    """
    return {
        "project_name": None,
        "generated_date": None,
        "last_updated": None,
        "mode": None,
        "project_identity": None,
        "architecture_rules": [],
        "code_quality_standards": [],
        "patterns_and_antipatterns": {
            "always_universal": [],
            "always_project_specific": [],
            "never_universal": [],
            "never_project_specific": [],
            "prefer_universal": [],
            "prefer_project_specific": [],
        },
        "domain_rules": [],
        "workflow_rules": [],
        "scaffolding_guide": None,
    }


def _write_state(state: dict, devforge_dir: Union[str, "os.PathLike[str]"]) -> None:
    """Atomically write `state` to the output JSON path.

    Uses tempfile.mkstemp in the same directory as the target so
    os.replace is atomic on a single filesystem. flush + fsync before
    os.replace adds a durability barrier. On any failure, attempts to
    remove the temp file and re-raises.
    """
    target = _output_file_path(devforge_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="constitute-",
        suffix=".json.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def cmd_reset(args: argparse.Namespace) -> int:
    """Write a fresh defaults state file. Idempotent: byte-identical re-runs."""
    _write_state(default_state(), args.devforge_dir)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="constitute_helper",
        description="State + render helper for /constitute. Owns constitution.md shape.",
    )
    parser.add_argument(
        "--devforge-dir",
        default=".devforge",
        help="Path to the .devforge directory (default: .devforge in CWD).",
    )
    parser.add_argument(
        "--install-root",
        default=None,
        help=(
            "Path to the install root (project root for standalone, wrapper root "
            "for wrapper mode). Default: parent of --devforge-dir."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    sp = subparsers.add_parser(
        "reset",
        help="Write a fresh defaults state file. Idempotent.",
    )
    sp.set_defaults(func=cmd_reset)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2

    if args.install_root is None:
        args.install_root = str(Path(args.devforge_dir).resolve().parent)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
