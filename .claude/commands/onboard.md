# /onboard — Deep Codebase Onboarding & Documentation Generation

You are running the onboarding process for an existing codebase. This command performs a deep scan of the entire project and generates comprehensive documentation that serves as the **knowledge base for all Claude Code agents**.

This is a **one-time command** run after `/constitute`. It delegates ALL scanning and documentation work to the **tech-writer agent** operating in **onboarding mode**.

## Prerequisites

1. `/setup-wizard` must have been run — `CLAUDE.md`, agents, settings, memory must exist
2. `/constitute` must have been run — `constitution.md` must exist and be approved
3. `docs/` folder must exist (created by setup wizard)
4. This is an **existing project** — check `.claude/project-config.json` for `"PROJECT_MODE": "existing"`. If missing, verify 6+ source files exist. For greenfield projects, docs are built incrementally via `/execute-task`

If any prerequisite is missing, inform the user and suggest running the missing command first.

## PHASE 1: Prepare Onboarding Context

### 1.1: Gather Project Knowledge

Read the following files and extract the key information the tech-writer will need:

1. **`CLAUDE.md`** — project name, type, framework, language, project structure, dev commands
2. **`constitution.md`** — architecture rules, layer boundaries, naming conventions, domain entities, key patterns
3. **`.claude/memory/MEMORY.md`** — any pre-seeded knowledge from setup wizard

Compile a **project brief** — a concise summary (~50 lines max) containing:
- Project name, type, stack
- Architecture pattern and layer boundaries
- Key domain entities and relationships (from constitution)
- Naming conventions
- Error handling pattern
- Module/directory organization

### 1.2: Map Project Structure

**Source Root awareness**: If `CLAUDE.md` specifies a Source Root other than `.`, use that path as the starting point for the source tree scan. All module paths will be relative to the workspace root (e.g., `SOURCE_ROOT/src/auth/`, not `src/auth/`). Claude artifacts (`specs/`, `docs/`) remain at the workspace root.

Get the full directory tree of source files. **Exclude**: `node_modules`, `.git`, `dist`, `build`, `__pycache__`, `.next`, `.nuxt`, `vendor`, `coverage`, `.claude`, `specs`, `docs`, lock files, binary/asset files.

From the tree, identify **module boundaries** — top-level source directories or feature directories that represent distinct areas of the codebase. Examples:
- `src/auth/`, `src/cart/`, `src/orders/` → 3 modules
- `src/components/`, `src/hooks/`, `src/services/`, `src/utils/` → 4 modules
- `packages/api/`, `packages/web/`, `packages/shared/` → 3 modules (monorepo)
- `app/models/`, `app/views/`, `app/controllers/` → 3 modules (MVC)

### 1.3: Determine Scan Strategy

Based on total source file count:

| Source Files | Strategy | Subagents |
|---|---|---|
| **< 50** | Single tech-writer scans everything directly | 0 (direct scan) |
| **50–200** | Split by top-level source dirs, one subagent per module | 1 per module |
| **200–1000** | Two-pass: structural scan first, then subagents with smart extraction | 1 per module |
| **1000+** | Sample-based: entry points + type files + 2-3 representative files per module | 1 per module |

## PHASE 2: Execute Onboarding Scan

Launch the tech-writer agent using the Agent tool with the prompt built below. The tech-writer does ALL the heavy lifting.

**CRITICAL**: The tech-writer agent prompt must include:
1. The project brief from Phase 1.1
2. The module map from Phase 1.2
3. The scan strategy from Phase 1.3
4. The complete onboarding instructions (Section A below)

### Prompt Template for Tech-Writer Agent

Build the agent prompt using this structure:

```
You are operating in **ONBOARDING MODE**. This is NOT your normal task-documentation workflow. You are performing a one-time deep scan of an existing codebase to generate comprehensive project documentation.

## Project Brief

[Insert project brief from Phase 1.1]

## Module Map

[Insert module list from Phase 1.2]

## Scan Strategy

[Insert strategy from Phase 1.3: direct / subagent-per-module / two-pass / sample-based]

## Your Mission

Generate complete project documentation in `docs/` that will serve as the **knowledge base for all Claude Code agents**. Every agent reads from `docs/` before making changes. The quality of your documentation directly determines how well agents understand and work with this codebase.

## Documentation Requirements

The docs you write must answer these questions for any agent picking up a task:
1. What does this project do? (overview)
2. How is the code organized and why? (architecture)
3. What are the key modules and how do they relate? (architecture)
4. What does each feature/module do and how does it work? (features/*)
5. What API endpoints exist and what are their contracts? (api/* — if applicable)
6. What patterns must be followed when making changes? (architecture)
7. Where are the boundaries between modules? (architecture)
8. What are the key types/entities and their relationships? (architecture or features)

[Insert full Section A instructions below]
```

---

## SECTION A: Tech-Writer Onboarding Instructions

Read `.claude/commands/_tech-writer-onboarding.md` and include its full content in the tech-writer agent prompt where `[Insert full Section A instructions below]` appears. This file contains the complete onboarding workflow: scanning rules, smart extraction tables, subagent templates, doc generation templates (overview, architecture, features, API), quality checks, and memory enrichment.

---

## PHASE 3: Process Results

### 3.1: Verify Documentation Created

After the tech-writer agent completes, verify that the following files exist:
- `docs/overview.md` — must have real content (not a stub)
- `docs/architecture.md` — must have real content (not a stub)
- At least one file in `docs/features/` (unless the project has only 1-2 modules)
- Files in `docs/api/` if the project has API endpoints

If any expected file is missing, inform the user.

### 3.2: Update Memory

If the tech-writer returned `MEMORY_ADDITIONS`, append them to `.claude/memory/MEMORY.md` under appropriate sections:
- Module boundaries → under "Project Structure" or a new "Module Map" section
- Dependency warnings → under "Known Pitfalls"
- Areas of complexity → under "Known Pitfalls"
- Inconsistencies → under "Known Pitfalls"

## PHASE 4: Summary

Present to the user:

```
## Onboarding Complete

### Documentation Generated:
- `docs/overview.md` — Project overview, structure, and module map
- `docs/architecture.md` — Architecture patterns, layers, data flow, key types
- `docs/features/[list].md` — Feature documentation per module
- `docs/api/[list].md` — API endpoint documentation (if applicable)

### Scan Summary:
- Source files scanned: [count]
- Modules identified: [count]
- Strategy used: [direct / subagent-per-module / two-pass / sample-based]

### Memory Updated:
- [count] module boundaries documented
- [count] dependency warnings added
- [count] areas of complexity flagged

### Next Steps:
1. Review the generated docs and adjust if needed
2. Start working with `/specify "your first feature"`

All agents will now use these docs as their knowledge base when executing tasks.
```

## IMPORTANT RULES

1. **Tech-writer owns everything** — this command ONLY orchestrates. The tech-writer agent does all scanning and writing
2. **Never modify source files** — onboarding generates `docs/` only. No inline docs, no code changes
3. **Context safety** — follow the scan strategy thresholds strictly. Do NOT read all files in a 500-file project in a single agent
4. **Accuracy over coverage** — if you can't determine what a module does from its signatures and types, say so honestly in the docs rather than guessing
5. **Real code only** — every code example in docs must be copied from the actual codebase, never invented
6. **No constitution duplication** — docs describe HOW the code works. The constitution describes the RULES. Don't repeat constitution rules in docs
7. **Preserve existing docs** — if `docs/` already has real content (not stubs), update rather than overwrite. Ask the user before replacing non-stub content
8. **This is for agents** — the primary audience is Claude Code agents, not humans. Write docs that help an AI understand the codebase quickly: be explicit, structured, and precise. Avoid vague descriptions