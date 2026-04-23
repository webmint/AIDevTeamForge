# {{cli.sigil}}onboard — Deep Codebase Onboarding & Documentation Generation

You are running the onboarding process for an existing codebase. This command performs a deep scan of the entire project and generates comprehensive documentation that serves as the **knowledge base for all agents**.

This command is typically run once after `{{cli.sigil}}setup-wizard` for brownfield projects — the wizard's Phase 5 summary suggests running it when `PROJECT_STATE` is `brownfield`. You can re-run it later when the codebase changes substantially (new modules, major refactor, new framework introduced); the pre-scan check in §1.0 protects existing docs on re-runs. It delegates ALL scanning and documentation work to the **tech-writer agent** operating in **onboarding mode**.

## Prerequisites

1. `{{cli.sigil}}setup-wizard` must have been run — the runtime primer (`{{cli.primer}}`), agents directory, runtime config, and `.devforge/` scaffold must exist
2. `docs/` folder must exist (placed by install, populated by setup wizard)
3. This is an **existing project** — check `.devforge/project-config.json` for `"PROJECT_STATE": "brownfield"`. For `"greenfield"` or `"empty"` projects, skip onboard — docs are built incrementally via `{{cli.sigil}}execute-task` as features ship.

If any prerequisite is missing, inform the user and suggest running the missing command first.

## PHASE 1: Prepare Onboarding Context

### 1.0: Existing-Documentation Check (pre-scan)

Before proceeding with the scan, check whether `docs/overview.md` and `docs/architecture.md` contain non-stub content. The wizard places them as stubs with placeholders substituted; an updated "real" version means someone edited them post-install.

**Heuristic for "non-stub"**:

- `docs/overview.md` exceeds ~10 lines of content OR contains prose beyond the two template paragraphs (what+who / why).
- `docs/architecture.md` contains module-map entries, dependency rules beyond the sentinel "_Populated by ..._" stubs, or cross-cutting-concerns content — none of which the wizard places.

**If real content is detected** in either file, pause and ask the user:

- **Overwrite** — discard existing content; regenerate from scan
- **Merge** — keep existing content; tech-writer appends / updates only where safe, leaves user prose intact
- **Abort** — skip onboard entirely

Default when uncertain: abort and let the user decide. Do not proceed silently.

**If only stubs are detected**, proceed with the scan normally (§1.1).

### 1.1: Gather Project Knowledge

Read the following files and extract the key information the tech-writer will need:

1. **Runtime primer** (`{{cli.primer}}`) — project name, type, framework, language, project structure, dev commands.
2. **`constitution.md`** — project identity (Section 1, populated by setup-wizard) and universal coding rules (Sections 3.5–3.7, 4.1–4.3, 6.1–6.4 — installed verbatim). The `[project-specific]` sections (§2 Architecture, §3.1 Type Safety, §3.3 Naming, §4.1.1/4.2.1/4.3.1 patterns, §5 Domain Rules, §6.5/6.6 workflow) are still sentinel-marked at this stage — those get populated later by `{{cli.sigil}}constitute`, which reads onboard's findings (in `docs/` and `.devforge/memory.md`) plus user-stated preferences.
3. **`.devforge/memory.md`** — any pre-seeded knowledge from setup wizard (cross-runtime shared file — both Claude and Codex read the same memory)

Compile a **project brief** — a concise summary (~30 lines max) containing only what's already extractable at this stage:

- Project name, type, stack (from runtime primer + `.devforge/project-config.json`)
- Architecture pattern (wizard Q4 answer, stored as `ARCHITECTURES[]`)
- Error handling pattern (wizard Q5 answer, stored as `ERROR_HANDLINGS[]`)
- API layer (wizard Q6 answer, stored as `API_LAYERS[]`)
- Testing framework (wizard Q7 answer, stored as `TESTINGS[]`)
- Module / directory organization (from the directory tree computed in §1.2)
- Any pre-seeded findings from `.devforge/memory.md`

Do NOT include layer boundaries, domain entities, or naming conventions — those are sentinel-marked in `constitution.md` and are the tech-writer's job to DISCOVER during scan, not preconditions for the scan.

### 1.2: Map Project Structure

**Source Root awareness**: If the runtime primer specifies a Source Root other than `.` (check `{{cli.primer}}`, or `.devforge/project-config.json` `SOURCE_ROOT` field as the canonical source), use that path as the starting point for the source tree scan. All module paths will be relative to the workspace root (e.g., `SOURCE_ROOT/src/auth/`, not `src/auth/`). Cross-runtime artifacts (`specs/`, `docs/`, `.devforge/`, `constitution.md`) remain at the workspace root.

Get the full directory tree of source files. **Exclude** the ecosystem-aware ignore set setup-wizard's detection phase already uses (see `detect.md` STEP 1 "Count source files" — covers build output, dependency trees, tool caches, and cross-runtime artifacts across Rust/Java/.NET/Python/Ruby/Haskell ecosystems), plus `.claude`, `.codex`, `.devforge`, `specs`, `docs`, lock files, and binary/asset files. If the project uses an ecosystem whose build/dependency directory isn't covered there, add it to both places (canonical list lives in `detect.md`).

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

Launch the tech-writer agent via {{cli.subagent}} with the prompt built below. The tech-writer does ALL the heavy lifting.

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

Generate complete project documentation in `docs/` that will serve as the **knowledge base for all agents**. Every agent reads from `docs/` before making changes. The quality of your documentation directly determines how well agents understand and work with this codebase.

## Documentation Requirements

Docs save future per-task tokens: an agent should find what it needs in docs faster than re-deriving from source. Density target varies by read frequency — write tighter for files read often, allow more detail in files read only when relevant.

**Read-frequency map** (informs how dense to write):

- `docs/overview.md` — every task, first read (keep tight)
- `docs/architecture.md` — most tasks that touch structure (tight)
- `docs/features/<module>.md` — only tasks touching that module (can carry more detail)
- `docs/api/<resource>.md` — only tasks touching that endpoint (can carry more detail)

### `docs/overview.md`

Two paragraphs max:

- **What + who**: what the project does, who uses it, what domain it serves
- **Why**: the defining architectural decision + its rationale

### `docs/architecture.md`

1. **Module map**: each top-level source directory + one sentence — what it handles, what it can/can't import
2. **Layer boundaries & dependency rules**: which direction imports flow; which crossings are forbidden
3. **Conventions**: naming, file organization, import style
4. **Cross-cutting concerns** (conditional — include only if the scan surfaced clear patterns, at least 3+ concordant observations): error propagation, authentication/authorization flow, data flow, state management. Skip any concern the scan didn't resolve cleanly — better absent than speculative.

### `docs/features/<module>.md` — one per substantive module

Produce one file per module surfaced with enough signal during scan. Skip a module if the scan found nothing substantial — better no doc than a stub.

1. **What the module does** — one-sentence summary + one paragraph of context
2. **Public surface** — exported functions/types with one-line descriptions
3. **Key types / entities** the module owns
4. **External dependencies** — other modules, libraries, services
5. **Invariants or gotchas** that surfaced during scan (if any)

### `docs/api/<resource>.md` — only for projects with HTTP/RPC APIs

Per endpoint group:

1. **Endpoint list**: methods + paths
2. **Auth requirements**
3. **Request/response shapes** (type-level, not every field)

## Depth principle

Docs describe **conventions and structure** — things that persist when implementation changes. If code changes but the pattern holds, the doc stays valid.

- ✅ YES: "Repositories live in `src/data/repositories/`; each implements the corresponding domain interface from `src/domain/`." (Survives refactoring.)
- ❌ NO: "`UserRepository.findById()` returns a `User` or `null`." (Becomes stale the moment anyone adds caching.)

## What NOT to document

- Per-file implementation details — code is the source of truth
- Private function purposes — name the function well; skip the doc
- Duplicated rules from `constitution.md` — docs describe HOW code works; constitution describes RULES. No overlap.
- Anything the scan is uncertain about — better silent than wrong

[Insert full Section A instructions below]
```

---

## SECTION A: Tech-Writer Onboarding Instructions

Read `references/tech-writer-onboarding.md` and include its full content in the tech-writer agent prompt where `[Insert full Section A instructions below]` appears. The path is rewritten to the runtime-native location at install time (alongside this command's main body). This file contains the complete onboarding workflow: scanning rules, smart extraction tables, subagent templates, doc generation templates (overview, architecture, features, API), quality checks, and memory enrichment.

---

## PHASE 3: Process Results

### 3.1: Verify Documentation Created

Verify the tech-writer's output matches the Documentation Requirements above. Check:

- **Presence**: `docs/overview.md` and `docs/architecture.md` exist with real content; `docs/features/*.md` files exist per substantive module (absent is acceptable for small/monolithic projects — architecture.md suffices); `docs/api/*.md` exist only if the project has HTTP/RPC APIs.
- **Per-file structure**: each file follows its section layout from Requirements (overview's what+who/why paragraphs; architecture's module map + dependency rules + conventions + optional cross-cutting; features' what + public surface + types + deps + invariants; api's endpoint list + auth + shapes).
- **"What NOT to document" violations**: stub markers left behind, per-file implementation detail, rules duplicated from `constitution.md`.
- **Cross-file consistency**: the project described in `overview.md` aligns with `architecture.md` and any `features/` files — obvious story conflicts suggest the scan misinterpreted something substantial.

If any check fails, report the findings to the user (file path + what's wrong + what to correct) and **ask explicitly** how to proceed, using your runtime's natural question mechanism. Offer three options:

- **Proceed** — accept the output as-is despite the issues (user's call)
- **Re-run the tech-writer** — rebuild the prompt with corrections and re-invoke the tech-writer agent for the specific files that failed verification (preserve the ones that passed)
- **Abort** — stop onboard entirely; user will investigate manually

Do NOT silently proceed to §3.2 after reporting issues. Wait for the user's explicit choice.

### 3.2: Update Memory

If the tech-writer returned `MEMORY_ADDITIONS`, append them to `.devforge/memory.md` (cross-runtime shared file — both Claude and Codex read the same memory) under appropriate sections:
- Module boundaries → under "Project Structure" or a new "Module Map" section
- Dependency warnings → under "Known Pitfalls"
- Areas of complexity → under "Known Pitfalls"
- Inconsistencies → under "Known Pitfalls"

## PHASE 4: Summary

Present to the user:

```
## Onboarding Complete

### Documentation Generated
- `docs/overview.md`
- `docs/architecture.md`
- `docs/features/` — [N] files  [omit this line if N == 0]
- `docs/api/` — [N] files  [omit this line if N == 0]

### Scan
- [count] source files across [count] modules ([strategy])

### Memory Updated
Summarize in 1–3 lines what was appended to `.devforge/memory.md`. Group naturally by category — e.g., "4 module boundaries, 2 known pitfalls from inconsistent import patterns, 1 complexity hotspot flagged in `services/orders/`".

### Next Steps
1. Review `docs/` and adjust as needed
2. Run `{{cli.sigil}}constitute` — turn scan findings and your architectural preferences into enforceable rules populated into the `[project-specific]` sections of `constitution.md`
3. Start working: `{{cli.sigil}}specify "your first feature"`
```

## IMPORTANT RULES

1. **Tech-writer owns everything** — this command ONLY orchestrates. The tech-writer agent does all scanning and writing
2. **Never modify source files** — onboarding writes only to `docs/` and `.devforge/memory.md`. No inline docs in source, no code changes
3. **Context safety** — follow the scan strategy thresholds strictly. Do NOT read all files in a 500-file project in a single agent
4. **Accuracy over coverage** — if you can't determine a pattern from the scan, SKIP it. Stubs and speculative content are worse than omission (better absent than speculative)
5. **Real code only** — every code example in docs must be copied from the actual codebase, never invented
6. **No constitution duplication** — docs describe HOW the code works. The constitution describes the RULES. Don't repeat constitution rules in docs
7. **Preserve existing docs** — if `docs/` already has real content (not stubs), update rather than overwrite. Ask the user before replacing non-stub content
8. **This is for agents** — the primary audience is the agents running subsequent commands, not humans. Write docs that help an AI understand the codebase quickly: be explicit, structured, and precise. Avoid vague descriptions