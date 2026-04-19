#!/usr/bin/env python3
"""CoreLLM generator for AIDevTeamForge.

Reads src/files/coreLLM/SOURCE.md and produces one output file per runtime.
Each runtime gets its own substitution values and conditional block selection.

Marker types processed here (lowercase/dot namespace):
  - {{output.X}}        — simple substitution from runtime config
  - {{#runtime}}...{{/runtime}} — conditional block, included only for that runtime

Marker types NOT processed here (UPPERCASE namespace):
  - {{PROJECT_NAME}}, {{FRAMEWORK}}, etc. — wizard substitutes these post-install

Usage:
  python3 scripts/generate-corellm.py --src src/files/coreLLM --out src/files/coreLLM

Adding a new runtime: add an entry to RUNTIMES below. No other changes needed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# ── Runtime definitions ──────────────────────────────────────────────────

RUNTIMES: dict[str, dict[str, str]] = {
    "claude": {
        "output.filename": "CLAUDE.md",
        "output.intro": "This file provides guidance to Claude Code when working with code in this repository.",
        "output.sigil": "/",
    },
    "codex": {
        "output.filename": "AGENTS.md",
        "output.intro": "Project instructions for Codex CLI.",
        "output.sigil": "$",
    },
}


# ── Processing ───────────────────────────────────────────────────────────

# Matches {{#runtime_name}}...{{/runtime_name}} including newlines.
# Non-greedy so nested blocks of different runtimes don't collide.
_BLOCK_RE = re.compile(
    r"\{\{#(\w+)\}\}\n?(.*?)\{\{/\1\}\}\n?",
    re.DOTALL,
)

# Matches {{output.key}} substitution markers.
_SUBST_RE = re.compile(r"\{\{output\.(\w+)\}\}")


def render(source: str, runtime: str, values: dict[str, str]) -> str:
    """Render SOURCE.md for a single runtime.

    1. Strip conditional blocks for OTHER runtimes; unwrap blocks for THIS runtime.
    2. Substitute {{output.X}} markers with runtime-specific values.
    """

    def _block_handler(m: re.Match) -> str:
        block_runtime = m.group(1)
        block_body = m.group(2)
        if block_runtime == runtime:
            return block_body
        return ""

    text = _BLOCK_RE.sub(_block_handler, source)

    def _subst_handler(m: re.Match) -> str:
        key = f"output.{m.group(1)}"
        if key in values:
            return values[key]
        # Unknown marker — leave it for debugging visibility.
        return m.group(0)

    text = _SUBST_RE.sub(_subst_handler, text)

    # Clean up multiple consecutive blank lines left by removed blocks.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="CoreLLM generator")
    parser.add_argument(
        "--src", type=Path, required=True,
        help="Directory containing SOURCE.md",
    )
    parser.add_argument(
        "--out", type=Path, required=True,
        help="Directory to write output files (CLAUDE.md, AGENTS.md, ...)",
    )
    parser.add_argument(
        "--runtimes", type=str, default="",
        help="Space-separated runtimes to emit. Empty = all registered runtimes.",
    )
    args = parser.parse_args()

    source_file = args.src / "SOURCE.md"
    if not source_file.is_file():
        print(f"error: {source_file} not found", file=sys.stderr)
        return 1

    # Resolve runtime filter.
    selected = [r for r in args.runtimes.split() if r]
    if selected:
        unknown = [r for r in selected if r not in RUNTIMES]
        if unknown:
            print(
                f"error: unknown runtime(s): {', '.join(unknown)}. "
                f"Known: {', '.join(RUNTIMES)}",
                file=sys.stderr,
            )
            return 1
    else:
        selected = list(RUNTIMES.keys())

    args.out.mkdir(parents=True, exist_ok=True)
    source = source_file.read_text()

    for runtime in selected:
        values = RUNTIMES[runtime]
        output_filename = values["output.filename"]
        rendered = render(source, runtime, values)
        out_path = args.out / output_filename
        out_path.write_text(rendered)
        print(f"  {runtime} → {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
