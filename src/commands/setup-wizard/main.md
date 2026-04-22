# {{cli.sigil}}setup-wizard — Project Initialization Wizard

You are running the initial setup wizard for AIDevTeamForge. Your job is:

1. Analyze the current project.
2. Ask the user targeted questions via confirm / override / defer.
3. Substitute the user's answers into the `{{PLACEHOLDER}}` markers in every target file that has them. All files are already in place — **you do NOT create new files**.
4. Where specific files have designated project-specific sections (e.g., CLAUDE.md / AGENTS.md architecture notes, agent files with project paths), append content derived from detection + user answers to those sections only. **Never rewrite whole files.**
5. Write the answers record to `.devforge/project-config.json` so later commands and `update.sh` can consume user decisions.

## Variation markers (template syntax)

This wizard and its reference files use a small set of variation markers that the install-time emitter processes per-runtime. When the emitter has run, you (the LLM executing the wizard) should see these already substituted. If you encounter any of them unsubstituted, treat them as follows rather than emitting the literal `{{...}}` text to the user:

- `{{ask "question text"}}` … `{{/ask}}` — interactive user-question block. Pose the question to the user and wait for the answer, using your runtime's natural question mechanism.

Any `{{UPPERCASE}}` marker (e.g., `{{PROJECT_NAME}}`, `{{LANGUAGE}}`) is a wizard-substitution placeholder — the wizard itself fills these with user answers or detection values during Phase 3. Do NOT emit them literally to user-visible output; substitute before presenting.

## Execution Flow

Execute these phases in order. Each phase's detailed instructions live in a dedicated reference file; **read the reference file fully before executing the phase.** Do not attempt any phase from memory or guesses.

### Phase 1 — Detection (read-only)

**Read `references/detect.md` and follow it.** Covers:

- STEP 0: Workspace Mode Detection (wrapper vs standalone)
- STEP 1: Project State (empty / greenfield / brownfield)
- STEP 2: Default Branch
- STEP 3: Auto-Detect Project Structure (languages, frameworks, tooling)

Retain all detection outputs in conversational memory for use in later phases (keys enumerated in `references/detect.md`).

### Phase 2 — Questions (interactive)

**Read `references/questions.md` and follow it.** Covers Q0 through Q11 (project name, description, type, languages/frameworks confirmation, architecture pattern, error handling convention, API layer, testing framework, workflow enforcement, AI attribution, per-runtime agent model assignments, AC verification). Questions Q3–Q7 produce per-stack arrays (`LANGUAGES`, `FRAMEWORKS`, `ARCHITECTURES`, `ERROR_HANDLINGS`, `API_LAYERS`, `TESTINGS`) — each parallel-indexed so downstream phases can reason per stack.

Retain every captured answer in conversational memory under the keys documented in `references/questions.md`.

### Phase 3 — Population (file substitution)

**Read `references/populate.md` and follow it.** Covers STEP 5: populating CLAUDE.md / AGENTS.md / runtime configs / baselines / MCP permissions / project config / memory seed / constitution header (§5.7) / docs stubs (§5.8), using the answers from Phase 2 and the detection data from Phase 1.

### Phase 4 — Agent Curation

**Read `references/agents.md` and follow it.** Covers STEP 6: selecting, removing, populating, and baselining agents for the project.

### Phase 5 — Summary

Present this summary to the user. **Substitute each `{VALUE}` placeholder below with the actual captured value from conversational memory** — do NOT emit the literal `{VALUE}` text. For `{N}` in the Packages line, compute `len(PACKAGES_DETECTED)`. Labels use plurals so they read naturally whether the project has one or many stacks. Include the `Packages:` line only when `PACKAGES_DETECTED` has 2 or more entries (multi-package project) — omit it for single-package projects.

```
## Setup Complete

### Populated Files:
- CLAUDE.md — Project instructions for Claude Code
- AGENTS.md — Project instructions for Codex CLI
- .devforge/project-config.json — Answers record (includes per-stack arrays and PACKAGE_STACKS)

### Project:
- Description: {PROJECT_DESCRIPTION}
- Type: {PROJECT_TYPE}
- Frameworks: {FRAMEWORKS joined with ", "}     (single-stack: one name; multi-stack: comma-joined list)
- Languages: {LANGUAGES joined with ", "}       (same rule)
- Packages: {N} detected (see `## Packages` in CLAUDE.md / AGENTS.md)   ← include only if multi-package

### Workspace Mode:
- Mode: {WORKSPACE_MODE}                          (value: "standalone" or "wrapper")
- Source Root: {SOURCE_ROOT}

### Next Steps:
1. Review CLAUDE.md and AGENTS.md — adjust if needed
2. Start working with {{cli.sigil}}specify "your first feature"
```

**After presenting the summary**, write the setup-completion marker to `.devforge/setup-complete` with content:

```
Setup completed: {current ISO-8601 date and time, e.g., 2026-04-22T15:30:42Z}
Runtime(s) installed: {"claude" / "codex" / "claude, codex" — based on presence of .claude/agents/ and .codex/agents/}
Populated files: {comma-joined list of files the wizard actually touched this run, built from presence checks}
```

**Composing the `Populated files:` list.** Build it from actual presence / action, not a static template — single-runtime installs touch only a subset. Include each entry only if the condition holds:

- `CLAUDE.md` — include if it exists at SOURCE_ROOT (§5.1 populated it)
- `AGENTS.md` — include if it exists at SOURCE_ROOT (§5.1 populated it)
- `constitution.md` — include if it exists at the project root AND §5.7 actually substituted placeholders (wizard skips §5.7 silently if the file is missing; brownfield projects with a pre-existing constitution leave it as-is, in which case the wizard did NOT modify it and this line should be omitted)
- `docs/overview.md` — include if it exists AND §5.8 actually substituted placeholders (install is per-file presence-guarded; pre-existing overview stays untouched and is omitted from this list)
- `docs/architecture.md` — same rule as `docs/overview.md`
- `.devforge/project-config.json` — always include (§5.5 always runs)
- `.devforge/memory.md` — always include (§5.6 always runs)
- `.devforge/baseline/CLAUDE.md` / `.devforge/baseline/AGENTS.md` / `.devforge/baseline/constitution.md` — include each only if the corresponding source file existed and §5.3 copied it
- `.claude/settings.json` — include only if it exists AND §5.4 appended chrome-devtools permissions (i.e., `AC_RUNTIME_URL` is set) — skip otherwise, since §5.2 does no placeholder substitution on this file
- `.mcp.json` — include only if it exists AND §5.4 appended the chrome-devtools entry
- `.codex/config.toml` — include only if it exists (§5.2 substituted placeholders, and §5.4 may have appended chrome-devtools)
- `agent files (per Phase 4)` — include only if at least one of `.claude/agents/` or `.codex/agents/` exists (Phase 4 ran)

This marker lets downstream commands detect whether setup-wizard ran to completion. If the file is missing, setup may have been interrupted mid-execution — downstream commands should surface this to the user and offer to resume or re-run. Place at `.devforge/setup-complete` (cross-runtime shared per PLAN.md decision #14 — both Claude and Codex check the same marker).

## IMPORTANT RULES (global)

1. **Never guess** — if you can't detect something, ask
2. **Phase 3 never creates files** — all files are already placed; Phase 3 only populates. Phase 4 creates files explicitly when generation is added.
3. **Use real paths** — all paths must point to actual directories in the project
4. **Use real commands** — all commands must come from the project's actual scripts
5. **Validate after population** — read back each file to verify no unresolved `{{PLACEHOLDER}}` markers remain
6. **Wrapper isolation** — in wrapper mode, never create any artifact inside SOURCE_ROOT
7. **Same values in both files** — CLAUDE.md and AGENTS.md get identical substitutions; `.devforge/project-config.json` gets the same values as JSON
8. **References are not optional** — you MUST read each phase's reference file in full before executing that phase. Do not attempt any phase from memory of previous invocations or guesses. Missing instructions from a reference file means stopping and re-reading it, not improvising.
