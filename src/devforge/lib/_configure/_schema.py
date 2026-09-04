"""Schema constants — single source of truth for field order, kind, and defaults."""

from __future__ import annotations


# Published artifact name (NOT a hidden state file — downstream commands
# read it).
OUTPUT_FILE_NAME = "configure.yaml"


# Order is locked: the emitter walks this list, so reordering changes the
# on-disk byte order. Diff stability is part of the contract.
#
# Field kinds:
#   "scalar"               — string-or-None value
#   "string_array"         — list of strings (default [])
#   "package_stack_array"  — list of per-package stack records (default [])
FIELD_SCHEMA = (
    # Identity
    ("project_name",           "scalar"),
    ("project_description",    "scalar"),
    ("project_type",           "scalar"),

    # Stack
    ("primary_language",       "scalar"),
    ("languages",              "string_array"),
    ("frameworks",             "string_array"),
    ("architectures",          "string_array"),
    # project_natures: atomic nature labels consumed by prune-agents (Phase 5a)
    # to decide which .claude/agents/*.md to delete. Clusters here with the
    # other shape-of-project arrays (languages, frameworks, architectures)
    # rather than with user-only preferences because it is detection-derivable
    # by the LLM in Phase 2 from PROJECT_TYPE + FRAMEWORKS.
    # Vocabulary (advisory, not enum-restricted at setter time): web, backend,
    # mobile, desktop, cli, library, plugin, data, ml, game, infra, docs.
    # A monorepo with both web AND backend → ["web", "backend"].
    ("project_natures",        "string_array"),
    ("error_handlings",        "string_array"),
    ("api_layers",             "string_array"),
    ("testings",               "string_array"),
    ("build_tools",            "string_array"),

    # Per-package
    ("build_commands",         "string_array"),
    ("type_check_commands",    "string_array"),
    ("lint_commands",          "string_array"),
    ("test_commands",          "string_array"),
    ("package_stacks",         "package_stack_array"),

    # Verbatim from docs/
    ("project_structure",      "scalar"),
    ("dev_commands",           "scalar"),
    ("architecture_details",   "scalar"),

    # User-only preferences
    ("workflow_enforcement",   "scalar"),
    ("ai_attribution",         "scalar"),
    ("claude_tier_think",      "scalar"),
    ("claude_tier_do",         "scalar"),
    ("claude_tier_verify",     "scalar"),

    # AC verification
    ("ac_verification_mode",   "scalar"),
    ("ac_runtime_url",         "scalar"),
    ("ac_runtime_api_base",    "scalar"),
    ("ac_runtime_cli_command", "scalar"),

    # Regression gate
    ("regression_gate",        "scalar"),

    # E2E (plan 90 D1): the one command that runs the project's e2e suite.
    # Empty string when the project has none — see FIELD_DEFAULTS below.
    # Top-level (not per-package): an e2e suite is a property of the
    # deployed product, not of a single package.
    ("e2e_command",            "scalar"),

    # Ticket identity (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md D4):
    # "no ticket, no spec" as a per-install policy, mechanical and opt-in
    # (OQ-1 — default "false"; see FIELD_DEFAULTS below). Stored as the
    # lowercase string "true"/"false" (an ENUM_FIELDS member below),
    # matching this codebase's other string-boolean config values rather
    # than a native JSON boolean — see e.g. _discover/_cli.py's own
    # `--internal-extension-followed` flag, which already uses the same
    # ("true", "false") string-literal convention.
    ("require_ticket",         "scalar"),

    # Agent effort per tier (92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md D4):
    # one enum-restricted sibling per claude_tier_* field above, ∈
    # {default, low, medium, high, xhigh, max} — see ENUM_FIELDS below.
    # "default" (FIELD_DEFAULTS baseline, see below) means "apply removes
    # the effort: line", which Claude Code defines as inheriting the
    # session's own effort level — a real, documented behavior, not an
    # unset/null sentinel. Appended last (house precedent from plans
    # 89/90/91: byte-stable diffs, no invented grouping).
    ("claude_effort_think",    "scalar"),
    ("claude_effort_do",       "scalar"),
    ("claude_effort_verify",   "scalar"),

    # Fourth tier — security (94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md
    # D3): security-reviewer is this tier's one member, so the model that
    # reviews security is the user's answer, not a framework pin.
    # claude_tier_security mirrors claude_tier_verify exactly (free-text
    # scalar, NOT enum-restricted — see the ENUM_FIELDS comment below);
    # claude_effort_security mirrors claude_effort_verify exactly (an
    # ENUM_FIELDS member with a FIELD_DEFAULTS "default" baseline below).
    # Appended last, after the existing tier/effort fields above, rather
    # than clustered beside claude_tier_verify / claude_effort_verify —
    # this pair was built as its own deliverable, independent of the
    # other three tiers' shared apply-verb machinery, and appending last
    # keeps its diff byte-stable regardless of what that other work does
    # to the earlier fields.
    ("claude_tier_security",   "scalar"),
    ("claude_effort_security", "scalar"),
)

# Enum-restricted scalars; key = field name, value = allowed set.
# Enforced at set-time by setters (Step 2). Exposed here for documentation
# and future validation; emit_yaml/parse_yaml do NOT enforce enum values.
#
# claude_tier_* fields are intentionally NOT enum-restricted: users may
# pick the recommended Claude tiers (Opus/Sonnet/Haiku) OR a custom model
# alias (Bedrock route, self-hosted, or future model name) via the Q11
# `Other` branch. The setter validates these as plain non-empty scalars.
# This rule applies identically to the fourth tier, claude_tier_security
# (94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md D3) — it is exempt from
# ENUM_FIELDS for the same reason as its three siblings, not a special
# case of its own. Their claude_effort_* siblings below (all four,
# including claude_effort_security) ARE enum-restricted, and the
# asymmetry is deliberate (92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md D4):
# effort is a closed, vendor-documented enum (default/low/medium/high/
# xhigh/max), while a model name is not and never will be one. The tier
# setters (_cmd_set_claude_tier in _cmds_set.py) now additionally
# normalize the four Claude Code subagent `model:` aliases (opus/sonnet/
# haiku/fable, matched case-insensitively) to their lowercase canonical
# form before storing; any other non-empty scalar still passes through
# unchanged as a pinned model ID (plan 92 D3) — see that function's
# docstring for the full normalized-alias-vs-pin behavior split.
#
# Claude Code's documented subagent `model:` frontmatter aliases (verified
# 2026-09-03 against code.claude.com/docs/en/sub-agents.md). Lives here,
# a base schema module, rather than in `_cmds_set.py` (a `_cmds_*` command
# module) so `_agent_models.py` -- itself a base module, never a command
# module -- can import it without reversing this package's DAG (base
# modules -> `_cmds_*`, never the other direction; python-reviewer run B
# finding 4). `_cmds_set.py`'s tier setters import it from here too. A
# single module-level tuple, not duplicated per importer, so the alias
# vocabulary has one place to change. The framework stores no model
# VERSION here -- an alias floats with whatever Claude Code maps it to on
# a given day (plan 92 D3); a consumer who needs a pinned version uses
# the `Other`/pin route below instead.
CLAUDE_MODEL_ALIASES = ("opus", "sonnet", "haiku", "fable")

ENUM_FIELDS = {
    "workflow_enforcement":  {"Strict", "Moderate", "Light"},
    "ai_attribution":        {"Yes", "No"},
    "ac_verification_mode":  {"code-only", "tests", "runtime-assisted", "off"},
    "regression_gate":       {"off", "full"},
    "require_ticket":        {"true", "false"},
    "claude_effort_think":   {"default", "low", "medium", "high", "xhigh", "max"},
    "claude_effort_do":      {"default", "low", "medium", "high", "xhigh", "max"},
    "claude_effort_verify":  {"default", "low", "medium", "high", "xhigh", "max"},
    "claude_effort_security": {"default", "low", "medium", "high", "xhigh", "max"},
}

# Non-None defaults for specific scalar fields (applied by default_state() and
# _load() so every code path — fresh install, reset, and existing install —
# gets the right baseline value without explicit configuration).
# Only fields where None is NOT the right out-of-the-box value appear here.
FIELD_DEFAULTS = {
    "regression_gate": "full",
    # "" (not None) is the legitimate "no e2e suite" value (plan 90 D1);
    # the structurally simpler default over inventing a discriminator —
    # e2e_command has no analogous gating field the way ac_verification_mode
    # has. A non-None default also keeps this field out of
    # _cmds_verify.py's null-scalar check with no exemption needed.
    "e2e_command": "",
    # "false" (OQ-1, ratified): opt-in, never imposed on an install that
    # never configured it. Same mechanism as e2e_command above — a
    # non-None default keeps this field out of _cmds_verify.py's
    # null-scalar check with no exemption needed, on a fresh install AND
    # on an existing configure.yaml written before this field existed.
    "require_ticket": "false",
    # "default" (plan 92 D4): a real ENUM_FIELDS member, not a null
    # sentinel — chosen deliberately so this field needs no
    # _cmds_verify.py exemption, on a fresh install AND on an existing
    # configure.yaml written before these fields existed, same mechanism
    # as regression_gate/e2e_command/require_ticket above.
    "claude_effort_think": "default",
    "claude_effort_do": "default",
    "claude_effort_verify": "default",
    # "default" (94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md D3): the
    # fourth tier's effort field mirrors its three siblings above exactly
    # — same real ENUM_FIELDS member, same reason (no _cmds_verify.py
    # exemption needed, on a fresh install AND on an existing
    # configure.yaml written before this field existed). claude_tier_
    # security deliberately has NO entry here, mirroring claude_tier_
    # verify's own absence above — see that field's own FIELD_SCHEMA
    # comment.
    "claude_effort_security": "default",
}

# package_stack_array record field order — locked so emit is deterministic.
_PACKAGE_STACK_FIELDS = (
    "path",
    "language",
    "framework",
    "build_tool",
    "build_command",
    "type_check_command",
    "lint_command",
    "test_command",
)
