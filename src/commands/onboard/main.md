# {{cli.sigil}}onboard — Deep Codebase Onboarding & Documentation Generation

You are running the onboarding process for an existing codebase. This command scans the project's structure and a representative sample of its source to generate comprehensive documentation that serves as the **knowledge base for all agents**. Scan depth scales by project size — see §1.3.

This command is typically run once after `{{cli.sigil}}setup-wizard` for brownfield projects — the wizard's Phase 5 summary suggests running it when `PROJECT_STATE` is `brownfield`. You can re-run it later when the codebase changes substantially (new modules, major refactor, new framework introduced); the pre-scan check in §1.0 protects existing docs on re-runs. It delegates the scan and `docs/` writing to the **tech-writer agent** operating in **onboarding mode**; the orchestrator handles pre-scan checks, post-scan verification, and memory updates.

## Prerequisites

1. `{{cli.sigil}}setup-wizard` must have been run — the runtime primer (`{{cli.primer}}`), agents directory, runtime config, and `.devforge/` scaffold must exist
2. `docs/` folder must exist (placed by install, populated by setup wizard)
3. This is an **existing project** — check `.devforge/project-config.json` for `"PROJECT_STATE": "brownfield"`. For `"greenfield"` or `"empty"` projects, skip onboard — the wizard's Phase 5 summary already routes these cases to `{{cli.sigil}}constitute` + `{{cli.sigil}}specify`, and docs emerge per-task as features ship.

If any prerequisite is missing, inform the user and suggest running the missing command first.

## PHASE 1: Prepare Onboarding Context

### 1.0: Existing-Documentation Check (pre-scan)

Before proceeding with the scan, check whether `docs/overview.md` and `docs/architecture.md` contain non-stub content. The wizard places them as stubs with placeholders substituted; an updated "real" version means someone edited them post-install.

**Non-stub detection** (diff against baseline — deterministic):

For each of `docs/overview.md` and `docs/architecture.md`, compare the current file against its snapshot at `.devforge/baseline/docs/<name>.md` (the wizard saves these in populate.md §5.3 as just-after-populate baselines). If the current file differs beyond trivial whitespace, treat it as **modified** — someone edited it post-install, so it has non-stub content.

If `.devforge/baseline/docs/<name>.md` is missing (file was placed outside the wizard's flow, or baseline was removed), do NOT silently assume stub-or-modified. Ask the user: "I can't determine whether `docs/<name>.md` carries pre-existing content — the wizard's baseline snapshot is missing. How should I proceed?" Offer the same three options: Overwrite / Merge / Abort. Fail closed rather than guess.

**If real content is detected** in either file, pause and ask the user:

- **Overwrite** — discard existing content; regenerate from scan
- **Merge** — keep existing content; tech-writer appends / updates only where safe, leaves user prose intact
- **Abort** — skip onboard entirely

Default when uncertain: abort and let the user decide. Do not proceed silently.

**Scope note for the user prompt**: this check covers `docs/overview.md` and `docs/architecture.md` only. Any existing files under `docs/features/` and `docs/api/` will be regenerated from scan output regardless of the choice above (features and api outputs are considered per-module/per-endpoint regenerable artifacts, not user-owned prose). If the user has hand-edited content under those directories that must be preserved, they should pick **Abort** here and reconcile manually before re-running.

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
- Any pre-seeded findings from `.devforge/memory.md`

Module/directory organization is NOT part of this brief — §1.2 computes it as a separate artifact (the module map), and §2's prompt template (line 83) feeds brief + module map to the tech-writer as distinct inputs.

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

Launch the tech-writer agent via {{cli.subagent}} with the prompt built below. The tech-writer handles the scan + `docs/` writing. Verification and memory-append stay in the orchestrator's lane — see §3.

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

## Mode

[Insert mode from §1.0: `overwrite` — fresh write, replace any existing content in docs/ with scan output | `merge` — preserve user-modified prose in docs/overview.md and docs/architecture.md; update sentinels or empty sections only; features/ and api/ write unconstrained | `fresh` — no pre-existing content detected, write normally]

## Your Mission

Generate complete project documentation in `docs/` that will serve as the **knowledge base for all agents**. Every agent reads from `docs/` before making changes. The quality of your documentation directly determines how well agents understand and work with this codebase.

## Documentation Requirements

Docs save future per-task tokens: an agent should find what it needs in docs faster than re-deriving from source. Density target varies by read frequency.

**Audience note.** The primary consumer of `docs/` is an AI agent executing downstream tasks, not a human skimmer. Humans benefit from conventions + diagrams because they explore freely with free-cost `grep` and `find`. Agents pay for every discovery read, so agent-oriented docs must **enumerate the public surface** — method / function / handler / operation names grouped by concern — not just describe conventions. An enumerated surface of ~200 lines loaded once saves thousands of discovery tokens across the hundreds of downstream tasks that touch the capability; it pays back after ~2 tasks. Staleness is self-healing in this workflow because the constitution mandates read-before-write and tech-writer updates on behavior change.

**Density policy by file type**:

- `docs/overview.md` — read every task. **Tight but not sparse.** Target 40–80 lines. Contains the navigation map (Features list) that routes the agent to the right feature file. Do NOT duplicate the runtime primer's tech-stack or project tree — those are loaded with the primer in every session anyway.
- `docs/architecture.md` — read on any task touching structure. **Conventions-level, not surface-level.** Describe layer rules, dependency direction, naming patterns, cross-cutting concerns. Do NOT enumerate per-capability surface here — that belongs in `docs/features/<capability>.md`.
- `docs/features/<capability>.md` — read only when a task touches that capability. **Surface-level, dense.** Target 100–250 lines per file. Enumerate public surface grouped by concern; the agent uses this as a navigation map before touching source.
- `docs/api/<resource>.md` — read only when a task touches that external interface. **Operation catalog + shapes.** Enumerate every externally-exposed operation with one-line purpose; include type-level request / response shapes, not every field.

**Mode handling** (honors the Mode declared above):

- **`merge`** — for `docs/overview.md` and `docs/architecture.md`, read the existing file first. Preserve any prose that diverges from the wizard's baseline (user-authored content). Update only sentinels or empty sections with scan findings. Do NOT overwrite paragraphs that carry user edits. For `features/` and `api/` files, write normally — those are regenerated outputs, not user-owned.
- **`overwrite`** or **`fresh`** — write per the Requirements below with no special preservation.

### `docs/overview.md`

The reader's **table of contents** for the whole project. Target ~40–80 lines. Required sections in order:

1. **What + who** (1 paragraph): what the project does, who uses it, what domain it serves.
2. **Why** (1 paragraph): the defining architectural decision + its rationale.
3. **Key entry points** (3–7 bullets): the first files to read to understand how the runtime starts. One file per bullet, with a one-line note about what it sets up. Adapt to the project's ecosystem — a process entry, a server bootstrap, a root module, a main executable, an init script.
4. **Features** (required): one-line-per-capability list that points to `docs/features/<capability>.md`. This is the navigation map the agent uses to decide which feature doc to load for a task. Example format: `- **[<Capability>](features/<capability>.md)** — <one-line summary>`.
5. **How to run** (1–2 lines): point to the runtime primer (`{{cli.primer}}`) for build / test / dev commands. Do not enumerate commands here.

**Forbidden in overview.md** (lives in the runtime primer — duplication rots):
- Tech-stack tables.
- Full project / source tree.
- Per-environment build command lists.
- Dependency or package lists.

If the scan didn't surface clear entry points, omit that section rather than guess. The Features list is mandatory — if no business capabilities exist (pure library, single-domain app), list the top-level modules instead.

### `docs/architecture.md`

1. **Module map**: each top-level source directory + one sentence — what it handles, what it can/can't import
2. **Layer boundaries & dependency rules**: which direction imports flow; which crossings are forbidden
3. **Conventions**: naming, file organization, import style
4. **Cross-cutting concerns** (conditional — include only if the scan surfaced clear patterns, at least 3+ concordant observations): error propagation, authentication/authorization flow, data flow, state management. Skip any concern the scan didn't resolve cleanly — better absent than speculative.

### `docs/features/<capability>.md` — one per business capability, NOT per package

A "feature" file documents a **business capability** the product offers — not a package, directory, or module. A single capability often cuts across multiple source locations; the feature doc unifies that view so an agent working on the capability has one file to load instead of discovering the surface through search.

**Capability discovery**: derive the capability list from scan signals — see `references/tech-writer-onboarding.md` §A.2.0. Do this before writing any feature file. The orchestrator's module map (Phase 1.2) is a scan-parallelism unit, not a documentation unit; do not reuse it as the feature-file list.

**Audience**: these files are primarily consumed by AI agents executing downstream tasks (`{{cli.sigil}}plan`, `{{cli.sigil}}execute-task`, etc.). Write for an agent that will use this file as a navigation map and surface reference, and will load the actual source files only for the specific function / method / type it needs to touch. **Enumerate the public surface densely.** Do not describe implementation bodies; describe what exists at the boundary.

**Target length**: 100–250 lines per capability, driven by surface size. A capability with 60+ public methods lands closer to 250; a thin capability with 5 methods lands closer to 100. Anything under 80 lines probably isn't a real capability — consider merging it into a parent capability or moving it into `shared-infrastructure.md`.

**Per-capability file** — required sections in order:

1. **What the capability does** — one sentence + one paragraph of user-facing context.
2. **Where it lives** — the source locations that implement this capability. List cross-cutting locations explicitly (a capability often spans multiple top-level directories).
3. **Public surface** — enumerated public boundary, **grouped by concern**. "Public boundary" means the project's natural external shape — the exact form depends on the ecosystem (e.g., methods on a service / controller / manager class for OO projects; exported functions and handlers for functional / procedural projects; route or command handlers for request-driven projects; message consumers for event-driven projects; public types + constructors for library projects). One line per item: name + signature (or type-level shape) + one-line purpose. Group items by responsibility (CRUD operations, state transitions, validation, computation, lifecycle, etc.) so an agent adding a parallel operation can locate the nearest pattern.
4. **Key types & data shapes** — the principal types this capability owns (domain types, state shapes, request/response shapes, event shapes — whichever apply). Type-level only, not full field lists for large types; link to the source file for exhaustive detail. The goal is for an agent to know what shape it's dealing with without reading the type definition file.
5. **API / external operations** (conditional — include only if the capability exposes operations outside its own code): enumerate route / RPC / GraphQL operation / CLI command / published event / subscription names with one-line purpose each. Do not document full payload schemas here — that's `docs/api/<resource>.md`'s job.
6. **External dependencies** — other capabilities or shared infrastructure this capability consumes. One line per dependency: what's used, for what.
7. **Extension points** — **REQUIRED**. "To add a new <X>, touch these N places." Anchors pattern-fill tasks — the single highest-value section for downstream agents doing feature work. Do NOT skip this section; if the scan genuinely surfaced no extension patterns, write a single line explaining why ("This capability exposes no add/extend pattern; modifications are ad-hoc per type-change.") rather than omitting the heading.

   For each extension scenario the capability supports, write one numbered list with concrete file paths (not abstract layer names). Derive scenarios from what you actually observed:
   - Did you see `add<X>`, `create<X>`, `register<X>` methods / handlers? Those are extension points.
   - Did you see a dispatch table, plugin registry, route list, or enum that controls feature behavior? Those are extension points.
   - Does adding a new field / operation / event require touching multiple files (type definition + handler + registration + schema)? Document that chain.

   Worked-shape examples (illustrative — adapt to the project's ecosystem and use its actual paths):
   - "To add a new operation exposing data of type `X`: (1) add the operation to the type definition in `path/to/types.ext`, (2) implement the handler in `path/to/handlers/`, (3) register it in `path/to/registry.ext`, (4) regenerate bindings via `<build command>`, (5) add a test in `path/to/tests/`."
   - "To add a new field to the <principal-type> aggregate: (1) extend the type in `path/to/entities/`, (2) add a transition method on the state container in `path/to/presentation/`, (3) extend the persistence shape in `path/to/data/`, (4) update the external operation in `path/to/schema.ext` if applicable."
   - "To add a new state transition to `<ThingBLoC>`: (1) add the use case class in `path/to/domain/cases/`, (2) inject it via the provider in `path/to/provide<Thing>.ext`, (3) call it from the presentation class in `path/to/presentation/`."
8. **Invariants or gotchas** — only things the scan actually observed (silent failures, unusual patterns, dual implementations, known TODOs in the capability's source). Skip if nothing surfaced.

**Fallback** — if capability discovery finds 0–1 business capabilities (pure library, single-domain app, infrastructure-only repo), fall back to one feature file per top-level source directory using the same section layout. Prefer fallback over inventing capabilities the code doesn't actually express.

**Pure-infrastructure consolidation** — cross-cutting infrastructure (logging, caching, error pipeline, codegen, build tooling, wiring / dependency-injection, shared base types) lives in a single `docs/features/shared-infrastructure.md`. Do not produce one file per infrastructure module — that's `docs/architecture.md`'s module-map territory.

Skip any capability the scan found nothing substantial about — better no doc than a stub.

### `docs/api/<resource>.md` — only for projects that expose an external interface

An "external interface" is any surface consumed from outside the project's own code: HTTP / REST routes, GraphQL schema, RPC services, WebSocket streams, published events, CLI subcommands, message-queue consumers / producers. The operation identifier shape varies by protocol (`METHOD /path` for HTTP, `service.method` for RPC, operation name for GraphQL, event / topic name for pub-sub, subcommand name for CLI) — see `references/tech-writer-onboarding.md` §A.2 for the per-protocol identifier form.

**Required sections** per resource / interface file:

1. **What this interface exposes** — one paragraph of scope: what the interface is for, who consumes it, what it does NOT cover.
2. **Operation catalog** — enumerated list of every externally-reachable operation, one line each: identifier + one-line purpose. Group by the natural grouping the protocol uses (resource for REST, service for RPC, root field for GraphQL, topic for pub-sub, subcommand group for CLI).
3. **Auth / authorization requirements** — which operations require what credentials / scopes / roles.
4. **Type-level request / response shapes** — the principal input and output types each operation uses. Link to the source file for exhaustive field lists; do not paste full type definitions here.
5. **Wiring** (conditional — include if the protocol involves non-trivial client / server setup): where the dispatch layer lives, how operations are registered, how generated bindings connect to handlers.
6. **Invariants or gotchas** (conditional) — cross-operation invariants, known legacy operations, TODOs in the interface layer.

**Target length**: 80–200 lines depending on operation count. The operation catalog is the reason this file exists — if it's thin, the file isn't pulling its weight.

## Depth principle

Docs cover two things:

1. **Conventions and structure** — things that persist when implementation changes. Layer rules, directory patterns, naming conventions, dependency direction. Belongs in `docs/architecture.md`.
2. **Public surface** — names of operations, methods, handlers, types, events that exist at module boundaries. Belongs in `docs/features/<capability>.md` and `docs/api/<resource>.md`. Enumerated surface is signal, not noise — it lets an agent plan a task without discovery reads.

What's explicitly OUT of scope: implementation **bodies**. A method's body (algorithm, loops, branches) is not doc material; that's what the source file is for.

- ✅ YES: "`ReportService.generate(input: ReportInput): Either<ReportError, Report>` — builds a report from the input. One of the CRUD operations in `features/reports.md`." (Names the surface; survives body changes.)
- ✅ YES: "Handlers live in `src/handlers/`; each implements the interface from `src/interfaces/`." (Convention; survives refactoring.)
- ❌ NO: "`ReportService.generate` first validates the input, then queries the database, then renders each section by calling helper X which loops over the sections..." (Implementation body leaking into docs — rots on first refactor.)

## What NOT to document

- Implementation bodies — code is the source of truth for how something works internally.
- Private helpers / internal-only functions — name the function well; skip the doc.
- Duplicated rules from `constitution.md` — docs describe what EXISTS and how it's organized; constitution describes the RULES. No overlap.
- Tech-stack / dev-command duplication from the runtime primer — primer is the source of truth for stack and commands.
- Anything the scan is uncertain about — better silent than wrong.

[Insert full Section A instructions below]
```

---

## SECTION A: Tech-Writer Onboarding Instructions

Read `references/tech-writer-onboarding.md` and include its full content in the tech-writer agent prompt where `[Insert full Section A instructions below]` appears. The path is rewritten to the runtime-native location at install time (alongside this command's main body). This file contains the complete onboarding workflow: scanning rules, smart extraction tables, subagent templates, doc generation templates (overview, architecture, features, API), quality checks, and memory enrichment.

---

## PHASE 3: Process Results

### 3.1: Verify Documentation Created

Verify the tech-writer's output matches the Documentation Requirements above. Check:

- **Presence**: `docs/overview.md` and `docs/architecture.md` exist with real content; `docs/features/*.md` files exist per substantive capability (absent is acceptable for small/monolithic projects — architecture.md suffices); `docs/api/*.md` exist only if the project has an external interface.
- **Per-file structure**: each file follows its section layout from Requirements. Specifically for `docs/features/*.md`, every file must contain all required headings in order: **Overview** (or What the capability does) · **Where it lives** · **Public surface** · **Key types / entities** · **API / external operations** (conditional) · **External dependencies** · **Extension points** · **Invariants / gotchas**. The `Extension points` section is load-bearing for downstream pattern-fill tasks — flag its absence as a verification failure even if every other section is present.
- **Cross-runtime sigil hygiene**: grep every `docs/*.md` for `/onboard`, `/constitute`, `/specify`, `/plan`, `/breakdown`, `/execute-task`, `/verify`, `$onboard`, `$constitute`, `$specify`, `$plan`, `$breakdown`, `$execute-task`, `$verify`. Any match is a failure — `docs/` is cross-runtime and must use bare command names (see `references/tech-writer-onboarding.md` §A.2.1).
- **"What NOT to document" violations**: stub markers left behind, per-file implementation detail, rules duplicated from `constitution.md`.
- **Cross-file consistency**: the project described in `overview.md` aligns with `architecture.md` and any `features/` files — obvious story conflicts suggest the scan misinterpreted something substantial.

If any check fails, report the findings to the user (file path + what's wrong + what to correct) and **ask explicitly** how to proceed, using your runtime's natural question mechanism. Offer three options:

- **Proceed** — accept the output as-is despite the issues (user's call)
- **Re-run the tech-writer** — rebuild the prompt with corrections and re-invoke the tech-writer agent for the specific files that failed verification (preserve the ones that passed)
- **Abort** — stop onboard entirely; user will investigate manually

Do NOT silently proceed to §3.2 after reporting issues. Wait for the user's explicit choice.

### 3.2: Update Memory

If the tech-writer returned `MEMORY_ADDITIONS` — a category-keyed structure with entries under each of the four categories below — append them to `.devforge/memory.md` (cross-runtime shared file — both Claude and Codex read the same memory) under the appropriate existing sections of the scaffold:

- **Module boundaries** → under `## Architecture Decisions` as a new sub-section `### Module boundaries (from onboard)` (alongside the wizard's `### Initial detection (from setup-wizard)` sub-section)
- **Dependency warnings** → under `## Known Pitfalls`
- **Areas of complexity** → under `## Known Pitfalls`
- **Inconsistencies** → under `## Known Pitfalls`

The scaffold has four top-level sections (Architecture Decisions, Known Pitfalls, What Worked, What Failed) — do NOT create new top-level sections; add content as sub-sections of existing ones.

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

1. **Tech-writer owns scan + docs writing** — this command orchestrates. The tech-writer agent handles the codebase scan and writes to `docs/`. Verification (§3.1) and memory append (§3.2) are the orchestrator's job, not the tech-writer's.
2. **Never modify source files** — onboarding writes only to `docs/` and `.devforge/memory.md`. No inline docs in source, no code changes
3. **Context safety** — follow the scan strategy thresholds strictly. Do NOT read all files in a 500-file project in a single agent
4. **Accuracy over coverage** — if you can't determine a pattern from the scan, SKIP it. Stubs and speculative content are worse than omission (better absent than speculative)
5. **Real code only** — every code example in docs must be copied from the actual codebase, never invented
6. **No constitution duplication** — docs describe HOW the code works. The constitution describes the RULES. Don't repeat constitution rules in docs
7. **Preserve existing docs** — if `docs/` already has real content (not stubs), do NOT overwrite silently. §1.0 detects non-stub content pre-scan and asks the user to pick Overwrite / Merge / Abort. All three are valid user choices; the rule is "ask, don't assume"
8. **This is for agents** — the primary audience is the agents running subsequent commands, not humans. Write docs that help an AI understand the codebase quickly: be explicit, structured, and precise. Avoid vague descriptions