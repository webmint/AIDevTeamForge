"""Shared loader + path rewriter for command sources in AIDevTeamForge.

Handles both flat and folder-based command sources from src/commands/:

    Flat:    src/commands/fix.md
    Folder:  src/commands/setup-wizard/
               main.md
               references/
                 detect.md
                 questions.md
                 populate.md
                 agents.md

The folder pattern is for commands too large to be comfortable in one file —
orchestrator in main.md, phase guides in references/. References are loaded
on-demand by the LLM at runtime.

Path rewriting (runtime-parametric)
-----------------------------------
In source, reference files cite each other by RELATIVE path (`references/X.md`)
so the physical source layout is self-consistent. At emit time, paths are
rewritten to the runtime-native target location. Each emitter specifies its
own target prefix so references live alongside the main command in each
runtime's native layout:

    Claude: references/detect.md → .claude/commands/<cmd>/references/detect.md
    Codex:  references/detect.md → .agents/skills/<cmd>/references/detect.md

Emitters then:

  * Claude: write main body → .claude/commands/<cmd>.md
            write refs     → .claude/commands/<cmd>/references/*.md
  * Codex:  write main body → .agents/skills/<cmd>/SKILL.md (YAML-wrapped)
            write refs     → .agents/skills/<cmd>/references/*.md

Each runtime gets its own copy of references (same text, different internal
paths) so cross-references between helpers stay consistent within the runtime.
Duplication is intentional; cost is negligible (~KB scale).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple


# Match `references/<filename>.md` where filename may contain alphanumerics,
# underscores, dashes, and dots. Anchored on the literal `references/` prefix
# so we don't accidentally rewrite similar-looking paths elsewhere.
_REFS_RE = re.compile(r"\breferences/([A-Za-z0-9_\-.]+\.md)\b")


@dataclass
class CommandSource:
    """Raw command source — main body + reference contents, no rewrites applied."""

    name: str
    body: str
    references: Dict[str, str] = field(default_factory=dict)
    is_folder: bool = False


def rewrite_refs(text: str, target_prefix: str) -> str:
    """Rewrite `references/<h>.md` → `<target_prefix>/<h>.md`.

    `target_prefix` is a project-relative path (e.g.,
    `.claude/commands/setup-wizard/references`). Idempotent: running on
    already-rewritten text is a no-op (the pattern no longer matches the
    expanded form).
    """
    return _REFS_RE.sub(
        lambda m: f"{target_prefix}/{m.group(1)}",
        text,
    )


def load(src_commands: Path, cmd_name: str) -> Optional[CommandSource]:
    """Load a command source from src/commands/, folder or flat.

    Returns None if neither src/commands/<name>.md nor src/commands/<name>/main.md
    exists. Content is returned RAW — no path rewriting applied. Use `processed()`
    to get rewritten content for a specific runtime's target.
    """
    folder = src_commands / cmd_name
    flat = src_commands / f"{cmd_name}.md"

    # Folder takes precedence over flat if both exist during transition.
    if folder.is_dir():
        main_file = folder / "main.md"
        if not main_file.is_file():
            return None
        body = main_file.read_text()
        references: Dict[str, str] = {}
        refs_dir = folder / "references"
        if refs_dir.is_dir():
            for ref in sorted(refs_dir.glob("*.md")):
                references[ref.name] = ref.read_text()
        return CommandSource(
            name=cmd_name,
            body=body,
            references=references,
            is_folder=True,
        )

    if flat.is_file():
        return CommandSource(
            name=cmd_name,
            body=flat.read_text(),
            references={},
            is_folder=False,
        )

    return None


def processed(
    source: CommandSource, target_prefix: str
) -> Tuple[str, Dict[str, str]]:
    """Return (body, references_dict) with all `references/X.md` paths rewritten.

    `target_prefix` is the runtime-native project-relative path where references
    will live — e.g., `.claude/commands/setup-wizard/references`. Both the main
    body AND every reference file's content get rewritten (helpers cross-reference
    each other).
    """
    body = rewrite_refs(source.body, target_prefix)
    refs = {
        name: rewrite_refs(content, target_prefix)
        for name, content in source.references.items()
    }
    return body, refs


def write_references(refs: Dict[str, str], target_dir: Path) -> int:
    """Write each reference file to `<target_dir>/<filename>`.

    Creates the target directory (and any parents) if needed. Returns the count
    of files written. No-op (returns 0) when refs is empty.
    """
    if not refs:
        return 0
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in refs.items():
        (target_dir / filename).write_text(content)
    return len(refs)
