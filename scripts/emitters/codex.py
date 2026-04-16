#!/usr/bin/env python3
"""Codex emitter for AIDevTeamForge.

Reads src/ (template authoring source) and writes Codex-runtime files into
the target project. Codex uses skills (not slash commands — prompts were
removed in 0.117.0).

Responsibilities:
  - src/commands/setup-wizard.md   → target/.agents/skills/setup-wizard/SKILL.md

CoreLLM files (AGENTS.md) are handled by generate-corellm.py, not this emitter.

Does NOT substitute {{PLACEHOLDERS}} — wizard handles that post-install.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Import the shared frontmatter helper. We're in scripts/emitters/codex.py;
# frontmatter lives in scripts/lib/frontmatter.py, so add scripts/ to sys.path.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
from lib.frontmatter import parse as parse_frontmatter  # noqa: E402
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

def emit_skills(src_commands: Path, target_skills_dir: Path) -> int:
    """Turn each src/commands/<name>.md into a SKILL.md under its own dir.

    Result layout:
      target/.agents/skills/fix/SKILL.md
      target/.agents/skills/specify/SKILL.md
      ...
    """
    if not src_commands.is_dir():
        return 0
    count = 0
    for md_file in sorted(src_commands.glob("*.md")):
        name = md_file.stem
        text = md_file.read_text()
        description = _derive_description(text, name)
        # Extract body (or fall back to full file if no frontmatter).
        _, body, _ = parse_frontmatter(text)
        if not body:
            body = text
        # Apply Claude→Codex transformations: rewrite AskUserQuestion calls
        # to prose, swap .claude/ paths to .codex/, rename CLAUDE.md → AGENTS.md,
        # etc. See scripts/lib/codex_rewrite.py for the rule list.
        # body = transform_command(body)  # TODO: not yet implemented
        skill_dir = target_skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "---\n"
            f"name: {name}\n"
            f'description: "{_yaml_escape_double(description)}"\n'
            "---\n\n"
            + body
        )
        count += 1
    return count


def emit_agents(src_agents: Path, target_agents_dir: Path) -> int:
    """Turn each src/agents/*.template.md into <name>.toml.

    Codex subagent TOML schema (MVP): name, description, developer_instructions.
    Placeholders like {{MODEL_THINK}}, {{FRAMEWORK}} remain visible for the
    wizard to substitute later.
    """
    if not src_agents.is_dir():
        return 0
    target_agents_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for md_file in sorted(src_agents.glob("*.template.md")):
        # Strip '.template' from the stem: architect.template.md → architect
        name = md_file.stem.replace(".template", "")
        text = md_file.read_text()
        fm, body, _ = parse_frontmatter(text)
        description = fm.get("description") or _derive_description(text, name)
        toml = _emit_toml_agent(name=name, description=description, body=body)
        out_file = target_agents_dir / f"{name}.toml"
        out_file.write_text(toml)
        count += 1
    return count


def emit_agents_md(src_agents_md: Path, target_root: Path) -> bool:
    """Write target/AGENTS.md from the AGENTS.md source.

    Direct copy. AGENTS.md is structured for Codex best practices
    (compact, <150 lines, critical content first, 32 KiB limit).
    Placeholders are substituted by the wizard post-install.
    """
    if not src_agents_md.is_file():
        return False
    content = src_agents_md.read_text()
    (target_root / "AGENTS.md").write_text(content)
    return True


# ── Main ──────────────────────────────────────────────────────────────────

def emit(src: Path, target: Path) -> None:
    skills_dir = target / ".agents" / "skills"

    # 1. Setup-wizard skill only.
    wizard_src = src / "commands" / "setup-wizard.md"
    if wizard_src.is_file():
        name = "setup-wizard"
        text = wizard_src.read_text()
        description = _derive_description(text, name)
        _, body, _ = parse_frontmatter(text)
        if not body:
            body = text
        # body = transform_command(body)  # TODO: not yet implemented
        skill_dir = skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            f"name: {name}\n"
            f'description: "{_yaml_escape_double(description)}"\n'
            "---\n\n"
            + body
        )

    print(f"    setup-wizard skill: yes")

    # ── Commented out: will be restored when commands/agents are promoted ──
    # codex_agents_dir = target / ".codex" / "agents"
    # n_skills = emit_skills(src / "commands", skills_dir)
    # n_agents = emit_agents(src / "agents", codex_agents_dir)
    # print(f"    skills: {n_skills}, codex agents: {n_agents}, AGENTS.md: ...")


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
