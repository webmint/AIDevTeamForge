#!/usr/bin/env python3
"""Claude emitter for AIDevTeamForge.

Reads from src/ (template authoring source) and writes the Claude-native
runtime files into the target project.

Responsibilities:
  - src/commands/setup-wizard.md   → target/.claude/commands/setup-wizard.md

CoreLLM files (CLAUDE.md) are handled by generate-corellm.py, not this emitter.

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

    # ── Commented out: will be restored when commands/agents are promoted ──
    # templates_dir = claude_dir / "templates"
    # templates_agents_dir = templates_dir / "agents"
    # memory_dir = claude_dir / "memory"
    # templates_agents_dir.mkdir(parents=True, exist_ok=True)
    # memory_dir.mkdir(parents=True, exist_ok=True)
    #
    # # Slash commands — all (currently only setup-wizard is in src/commands/).
    # src_commands = src / "commands"
    # if src_commands.is_dir():
    #     for md_file in sorted(src_commands.glob("*.md")):
    #         shutil.copy2(md_file, commands_dir / md_file.name)
    #
    # # Agent templates — direct copy, filename preserved (includes .template).
    # src_agents = src / "agents"
    # if src_agents.is_dir():
    #     for md_file in sorted(src_agents.glob("*.template.md")):
    #         shutil.copy2(md_file, templates_agents_dir / md_file.name)
    #
    # # Project templates (CLAUDE.md, settings.template.json,
    # #    memory.template.md, constitution.template.md, storage-rules.md).
    # src_files = src / "files"
    # if src_files.is_dir():
    #     for f in sorted(src_files.iterdir()):
    #         if f.is_file():
    #             shutil.copy2(f, templates_dir / f.name)
    #
    # # Manifest — copied into .claude/ with its historical filename.
    # src_manifest = src / "manifest.json"
    # if src_manifest.is_file():
    #     shutil.copy2(src_manifest, claude_dir / "template-manifest.json")


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
