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
generate / copy time with a boot-safe default. Once configured, the
consumer-side `configure_helper apply-agent-models` verb (plan 92 D1,
built as Phase 1 Deliverable 3 of that plan) rewrites `model:` / `effort:`
per agent from `.devforge/project-config.json` — plan 92 Phases 2–3 add
the calls that invoke it, at `/devforge:configure` Phase 5.4 and on
`update.sh` respectively; see that verb's own module for the mechanism.

This file is the single source of truth for those defaults.
"""

from __future__ import annotations


# ── Claude per-tier agent defaults (.claude/agents/*.md frontmatter) ───────
# Claude's `model:` field takes a short tier name (`opus`, `sonnet`, `haiku`),
# not a full model ID. The consumer-side `configure_helper apply-agent-models`
# verb (plan 92 D1, built as Phase 1 Deliverable 3 of that plan) rewrites
# these per agent from `.devforge/project-config.json` — plan 92 Phases 2–3
# add the calls that invoke it, at `/devforge:configure` Phase 5.4 and on
# `update.sh` respectively. That verb's own copy of this default map lives
# under `src/devforge/lib/_configure/` (plan 92 D2) — a maintainer test
# pins the two literals equal.
CLAUDE_AGENT_DEFAULTS_BY_TIER: dict[str, str] = {
    "think":  "opus",
    "do":     "sonnet",
    "verify": "sonnet",
    "scan":   "haiku",
}
