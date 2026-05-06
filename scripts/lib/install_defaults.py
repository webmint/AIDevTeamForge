"""Boot-safe defaults for runtime-parse-critical template fields.

Problem this solves
-------------------
`.claude/agents/*.md` is parsed by Claude Code at launch, BEFORE the wizard
runs. If those files ship with unsubstituted `{{PLACEHOLDER}}` tokens in
structural (non-prose) fields like `model:`, Claude Code may refuse to load
the agent or silently disable it.

The wizard that would substitute those placeholders can't run until Claude
is already running — chicken-and-egg.

Solution
--------
Install-time artifacts must be boot-valid from the moment they land. Any
placeholder whose presence would break runtime-parse is replaced at
generate / copy time with a boot-safe default. The wizard later OVERWRITES
these values via key-based regex replacement (not placeholder substitution)
when it has user answers — see `agents.md` §6.4.

This file is the single source of truth for those defaults.
"""

from __future__ import annotations


# ── Claude per-tier agent defaults (.claude/agents/*.md frontmatter) ───────
# Claude's `model:` field takes a short tier name (`opus`, `sonnet`, `haiku`),
# not a full model ID. Wizard's Q10a may override per tier.
CLAUDE_AGENT_DEFAULTS_BY_TIER: dict[str, str] = {
    "think":  "opus",
    "do":     "sonnet",
    "verify": "sonnet",
    "scan":   "haiku",
}
