#!/usr/bin/env python3
"""Claude emitter for AIDevTeamForge.

Reads from src/ (template authoring source) and writes the Claude-native
runtime files into the target project.

Responsibilities:
  - src/commands/setup-wizard.md   → target/.claude/commands/setup-wizard.md

Handled by other generators, not this emitter:
  - CoreLLM files (CLAUDE.md)      → scripts/generate-corellm.py
  - Subagents (.claude/agents/*)   → scripts/generate-agents.py

Does NOT substitute {{PLACEHOLDERS}} — wizard does that post-install with
user answers.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def emit(src: Path, target: Path) -> None:
    """Emit Claude-runtime files into target from src."""
    commands_dir = target / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    # 1. Setup-wizard command.
    wizard_src = src / "commands" / "setup-wizard.md"
    if wizard_src.is_file():
        shutil.copy2(wizard_src, commands_dir / "setup-wizard.md")

    # ── Commented out: will be restored when commands are promoted ───────────
    # Agents are handled by scripts/generate-agents.py, not this emitter.
    #
    # src_commands = src / "commands"
    # if src_commands.is_dir():
    #     for md_file in sorted(src_commands.glob("*.md")):
    #         shutil.copy2(md_file, commands_dir / md_file.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Claude runtime emitter")
    parser.add_argument("--src", type=Path, required=True, help="Template src/ directory")
    parser.add_argument("--target", type=Path, required=True, help="Target project directory")
    args = parser.parse_args()

    if not args.src.is_dir():
        print(f"error: --src '{args.src}' is not a directory", file=sys.stderr)
        return 1
    if not args.target.is_dir():
        print(f"error: --target '{args.target}' is not a directory", file=sys.stderr)
        return 1

    emit(args.src, args.target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
