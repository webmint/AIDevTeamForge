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
)

# Enum-restricted scalars; key = field name, value = allowed set.
# Enforced at set-time by setters (Step 2). Exposed here for documentation
# and future validation; emit_yaml/parse_yaml do NOT enforce enum values.
#
# claude_tier_* fields are intentionally NOT enum-restricted: users may
# pick the recommended Claude tiers (Opus/Sonnet/Haiku) OR a custom model
# alias (Bedrock route, self-hosted, or future model name) via the Q11
# `Other` branch. The setter validates these as plain non-empty scalars.
ENUM_FIELDS = {
    "workflow_enforcement":  {"Strict", "Moderate", "Light"},
    "ai_attribution":        {"Yes", "No"},
    "ac_verification_mode":  {"code-only", "tests", "runtime-assisted", "off"},
    "regression_gate":       {"off", "full"},
    "require_ticket":        {"true", "false"},
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
