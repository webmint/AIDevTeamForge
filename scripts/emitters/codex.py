#!/usr/bin/env python3
"""Codex emitter for AIDevTeamForge.

Reads src/ (template authoring source) and writes Codex-runtime files into
the target project. Codex uses skills (not slash commands — prompts were
removed in 0.117.0).

Responsibilities:
  - src/commands/setup-wizard/main.md  → target/.agents/skills/setup-wizard/SKILL.md
  - src/commands/setup-wizard/references/*.md
                                       → target/.agents/skills/setup-wizard/references/*.md
  (both flat and folder-based sources supported during migration)

Handled by other generators, not this emitter:
  - CoreLLM files (AGENTS.md)        → scripts/generate-corellm.py
  - Subagents (.codex/agents/*.toml) → scripts/generate-agents.py

Does NOT substitute {{PLACEHOLDERS}} — wizard handles that post-install. Does
rewrite `references/<h>.md` cross-references to project-relative
`.agents/skills/<cmd>/references/<h>.md` paths (via shared helper). References
live as siblings to SKILL.md per Codex's canonical skill layout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Import shared helpers. We're in scripts/emitters/codex.py;
# lib/ lives in scripts/lib/, so add scripts/ to sys.path.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
from lib.frontmatter import parse as parse_frontmatter  # noqa: E402
from lib.command_source import (  # noqa: E402
    load as load_command,
    processed as process_source,
    write_references,
)
# from lib.codex_rewrite import transform_command  # noqa: E402  # TODO: not yet implemented


# ── YAML double-quoted escaping (for SKILL.md frontmatter emission) ──────
# Mirror of frontmatter._unescape_double_quoted: re-escape actual chars back
# to YAML escape sequences so the emitted frontmatter is valid YAML.

def _yaml_escape_double(s: str) -> str:
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    return "".join(out)


# ── Description derivation ────────────────────────────────────────────────

def _derive_description(md_text: str, fallback_name: str) -> str:
    """Choose a short description for a skill/agent when source lacks one.

    Order of preference:
      1. 'description' field in source frontmatter (if any)
      2. First H1 heading in the body, with leading '# ' stripped
      3. Generic fallback: "AIDevTeamForge command: <name>"
    """
    fm, body, _ = parse_frontmatter(md_text)
    if fm.get("description"):
        return fm["description"]
    # Scan body for first '# ' heading
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return f"AIDevTeamForge command: {fallback_name}"


# ── Emitters ──────────────────────────────────────────────────────────────

def _write_skill(source, skills_dir: Path) -> int:
    """Emit a single command source as a Codex skill directory.

    Returns reference count written. References live as siblings to SKILL.md
    per Codex's canonical skill layout.
    """
    skill_dir = skills_dir / source.name
    skill_dir.mkdir(parents=True, exist_ok=True)
    refs_dir = skill_dir / "references"
    refs_prefix = f".agents/skills/{source.name}/references"

    body, refs = process_source(source, refs_prefix)
    description = _derive_description(body, source.name)
    # Apply Claude→Codex transformations: rewrite AskUserQuestion calls
    # to prose, swap .claude/ paths to .codex/, rename CLAUDE.md → AGENTS.md,
    # etc. See scripts/lib/codex_rewrite.py for the rule list.
    # body = transform_command(body)  # TODO: not yet implemented
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        f"name: {source.name}\n"
        f'description: "{_yaml_escape_double(description)}"\n'
        "---\n\n"
        + body
    )
    return write_references(refs, refs_dir)


# ── Main ──────────────────────────────────────────────────────────────────

def emit(src: Path, target: Path) -> None:
    skills_dir = target / ".agents" / "skills"

    # 1. Setup-wizard skill only (folder-based after migration; flat still supported).
    source = load_command(src / "commands", "setup-wizard")
    if source is not None:
        n_refs = _write_skill(source, skills_dir)
        if source.is_folder:
            print(f"    setup-wizard skill: yes ({n_refs} references)")
        else:
            print(f"    setup-wizard skill: yes (flat)")

    # ── Commented out: will be restored when commands are promoted ───────────
    # Agents are handled by scripts/generate-agents.py, not this emitter.
    #
    # src_commands = src / "commands"
    # if src_commands.is_dir():
    #     for entry in sorted(src_commands.iterdir()):
    #         name = entry.stem if entry.is_file() else entry.name
    #         if name == "setup-wizard":
    #             continue  # already emitted above
    #         src_obj = load_command(src_commands, name)
    #         if src_obj is None:
    #             continue
    #         _write_skill(src_obj, skills_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Codex runtime emitter")
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
