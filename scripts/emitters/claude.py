#!/usr/bin/env python3
"""Claude emitter for AIDevTeamForge.

Reads from src/ (template authoring source) and writes the Claude-native
runtime files into the target project.

Responsibilities:
  - src/commands/init-forge/main.md    → target/.claude/commands/init-forge.md
  - src/commands/onboard/main.md       → target/.claude/commands/onboard.md
  - src/commands/onboard/references/*.md
                                       → target/.claude/commands/onboard/references/*.md
  - src/commands/generate-docs/main.md → target/.claude/commands/generate-docs.md
  - src/commands/constitute/main.md    → target/.claude/commands/constitute.md
  (both flat and folder-based sources supported during migration)

  NOTE: /setup-wizard is no longer emitted. The architecture pivot replaces
  it with /init-forge (Phase 1 detection) and the upcoming /configure
  (Phase 2-4 work). The src/commands/setup-wizard/ source tree is kept
  for reference + migration but does not ship into target projects.

Handled by other generators, not this emitter:
  - CoreLLM files (CLAUDE.md)      → scripts/generate-corellm.py
  - Subagents (.claude/agents/*)   → scripts/generate-agents.py

Does NOT substitute {{PLACEHOLDERS}} — wizard does that post-install with
user answers. Does rewrite `references/<h>.md` cross-references to project-
relative `.claude/commands/<cmd>/references/<h>.md` paths so the runtime's
file-read tool resolves them unambiguously.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Import shared command-source helpers. We're in scripts/emitters/claude.py;
# shared lib lives in scripts/lib/, so add scripts/ to sys.path.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
from lib.command_source import (  # noqa: E402
    load as load_command,
    processed as process_source,
    write_references,
)
def emit(src: Path, target: Path) -> None:
    """Emit Claude-runtime files into target from src."""
    commands_dir = target / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    # Commands promoted so far. As each command matures out of src/_pending/,
    # add it here. Full generalized iteration (loop all src/commands/ entries)
    # stays commented below until every command has passed its CLI-agnostic +
    # audit passes — premature promotion would ship broken skills.
    _PROMOTED = ("init-forge", "onboard", "generate-docs", "configure", "constitute", "research", "discover", "specify", "plan", "breakdown", "pr-review", "audit")

    for cmd_name in _PROMOTED:
        source = load_command(src / "commands", cmd_name)
        if source is None:
            continue
        refs_dir = commands_dir / source.name / "references"
        refs_prefix = f".claude/commands/{source.name}/references"
        body, refs = process_source(source, refs_prefix)
        (commands_dir / f"{source.name}.md").write_text(body)
        n_refs = write_references(refs, refs_dir)
        layout = "folder" if source.is_folder else "flat"
        print(f"    {cmd_name} command: yes ({layout}, {n_refs} references)")

    # ── Commented out: will be restored when ALL commands are promoted ───────
    # Generalized loop over src/commands/ — replaces the explicit _PROMOTED
    # list once every command has been audited.
    #
    # src_commands = src / "commands"
    # if src_commands.is_dir():
    #     for entry in sorted(src_commands.iterdir()):
    #         name = entry.stem if entry.is_file() else entry.name
    #         src_obj = load_command(src_commands, name)
    #         if src_obj is None:
    #             continue
    #         refs_dir = commands_dir / src_obj.name / "references"
    #         refs_prefix = f".claude/commands/{src_obj.name}/references"
    #         body, refs = process_source(src_obj, refs_prefix)
    #         (commands_dir / f"{src_obj.name}.md").write_text(body)
    #         write_references(refs, refs_dir)


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
