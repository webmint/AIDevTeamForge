#!/usr/bin/env python3
"""CoreLLM generator for AIDevTeamForge.

Reads src/files/coreLLM/SOURCE.md and produces CLAUDE.md.

Marker types processed here (lowercase/dot namespace):
  - {{output.X}} — simple substitution from OUTPUT_VALUES

Marker types NOT processed here (UPPERCASE namespace):
  - {{PROJECT_NAME}}, {{FRAMEWORK}}, etc. — wizard substitutes these post-install

Usage:
  python3 scripts/generate-corellm.py --src src/files/coreLLM --out <target-dir>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


OUTPUT_VALUES: dict[str, str] = {
    "output.filename": "CLAUDE.md",
    "output.intro": "This file provides guidance to Claude Code when working with code in this repository.",
    "output.sigil": "/",
}


_SUBST_RE = re.compile(r"\{\{output\.(\w+)\}\}")


def render(source: str, values: dict[str, str]) -> str:
    def _subst_handler(m: re.Match) -> str:
        key = f"output.{m.group(1)}"
        if key in values:
            return values[key]
        # Unknown marker — leave it for debugging visibility.
        return m.group(0)

    return _SUBST_RE.sub(_subst_handler, source)


def main() -> int:
    parser = argparse.ArgumentParser(description="CoreLLM generator")
    parser.add_argument(
        "--src", type=Path, required=True,
        help="Directory containing SOURCE.md",
    )
    parser.add_argument(
        "--out", type=Path, required=True,
        help="Directory to write CLAUDE.md",
    )
    args = parser.parse_args()

    source_file = args.src / "SOURCE.md"
    if not source_file.is_file():
        print(f"error: {source_file} not found", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    rendered = render(source_file.read_text(), OUTPUT_VALUES)
    out_path = args.out / "CLAUDE.md"
    out_path.write_text(rendered)
    print(f"  claude → {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
