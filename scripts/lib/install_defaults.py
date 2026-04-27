"""Boot-safe defaults for runtime-parse-critical template fields.

Problem this solves
-------------------
Some template files — `.codex/config.toml`, `.codex/agents/*.toml`,
`.claude/agents/*.md` — are parsed by the runtime (Codex CLI / Claude Code)
at launch, BEFORE the wizard runs. If those files ship with unsubstituted
`{{PLACEHOLDER}}` tokens in structural (non-prose) fields, the runtime
either refuses to start (Codex config.toml) or silently disables features
(Codex agent TOMLs fail to deserialize; warning printed).

The wizard that would substitute those placeholders can't run until the
runtime is already running — chicken-and-egg.

Solution
--------
Install-time artifacts must be boot-valid from the moment they land. Any
placeholder whose presence would break runtime-parse is replaced at
generate / copy time with a boot-safe default. The wizard later OVERWRITES
these values via key-based regex replacement (not placeholder substitution)
when it has user answers — see `populate.md` §5.2 (config.toml) and
`agents.md` §6.4 (agent files).

This file is the single source of truth for those defaults. Adding a new
runtime-parse-critical field:

1. Add the default here.
2. Update the generator / template file that emits that field.
3. Update the wizard spec to document the key-based replacement for the
   new field.
"""

from __future__ import annotations


# ── Codex per-tier agent defaults (.codex/agents/*.toml) ───────────────────
# `model` stays the same across tiers (project uses one model by default);
# `model_reasoning_effort` varies by tier. Wizard's Q10b may override both
# per tier.
CODEX_AGENT_DEFAULTS_BY_TIER: dict[str, dict[str, str]] = {
    "think":  {"model": "gpt-5.4", "model_reasoning_effort": "high"},
    "do":     {"model": "gpt-5.4", "model_reasoning_effort": "medium"},
    "verify": {"model": "gpt-5.4", "model_reasoning_effort": "medium"},
}


# ── Claude per-tier agent defaults (.claude/agents/*.md frontmatter) ───────
# Claude's `model:` field takes a short tier name (`opus`, `sonnet`, `haiku`),
# not a full model ID. Wizard's Q10a may override per tier.
CLAUDE_AGENT_DEFAULTS_BY_TIER: dict[str, str] = {
    "think":  "opus",
    "do":     "sonnet",
    "verify": "sonnet",
}
