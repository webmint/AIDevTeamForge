# {{cli.sigil}}onboard — Codebase Documentation Generation

You are running the onboarding process for an existing codebase. This command produces comprehensive documentation in `docs/` that serves as the **knowledge base for all agents**. Every agent reads from `docs/` before making changes; the quality and coverage of your documentation directly determines how well agents understand and work with this codebase.

This command runs once after `{{cli.sigil}}setup-wizard` for brownfield projects. Re-run when the codebase changes substantially; the pre-scan check (§1.0) protects user-edited docs across re-runs.

## CORE PRINCIPLE — COVER ALL CODE

**Every package, every meaningful source folder, every external interface gets a documentation home.** No sample-based silence. No skipping at scale. No "we'll cluster these into one file" merges that drop substance.

If the project has 23 packages, the result is 23 package docs. If it has 4 large composite packages, the result is 4 doc folders, each with sub-docs for internal concerns. The depth adapts; the coverage does not.

The docs are a **substitute for first-pass code reading**. An agent should be able to read `docs/<package>/index.md` and:
- Know what the package provides (Overview)
- See real code (lifted, not paraphrased) for every public export
- Identify "to add a new X, I touch Y" — from the doc alone
- Know the dependencies before importing
- See a real consumer pattern before writing new consumer code

…all without opening source files. Source becomes a verification step, not a discovery step.

## Prerequisites

1. `{{cli.sigil}}setup-wizard` must have been run — runtime primer (`{{cli.primer}}`), agents directory, runtime config, and `.devforge/` scaffold must exist.
2. `docs/` folder must exist (placed by install, populated by setup wizard).
3. Project is **brownfield** — `.devforge/project-config.json` has `"PROJECT_STATE": "brownfield"`. Greenfield/empty projects skip onboard; the wizard's Phase 5 summary routes those to `{{cli.sigil}}constitute` + `{{cli.sigil}}specify`.

If any prerequisite is missing, inform the user and suggest running the missing command first.

---

## PHASE 1: Prepare Onboarding Context

### 1.0: Pre-scan Baseline Check (across all `docs/*` outputs)

Before any scan, check whether `docs/` carries user-edited content from a prior onboard run.

**Detection** (deterministic — diff against baseline):

For every existing file under `docs/` (recursive), compare against its snapshot at `.devforge/baseline/docs/<...same-relative-path...>`. If the file differs beyond trivial whitespace, treat it as **user-modified**.

If a baseline file is missing for an existing `docs/` file, do NOT silently assume stub-or-modified. Ask the user: "I can't determine whether `docs/<path>` carries pre-existing content — the baseline snapshot is missing. How should I proceed?" Offer the same three options below; fail closed.

**If user-modified content is detected anywhere under `docs/`**, pause and ask the user once for the whole set:

- **Overwrite** — discard existing content; regenerate from scan.
- **Merge** — preserve user-edited prose; regenerate only sections matching the baseline.
- **Abort** — skip onboard; user reconciles manually.

Default when uncertain: abort. Do not proceed silently.

**If only stubs are detected** (or `docs/` is empty beyond what the wizard placed), proceed to §1.1.

### 1.1: Gather Project Knowledge

Read the following and extract what the tech-writer needs:

1. **Runtime primer** (`{{cli.primer}}`) — project name, type, framework, language, project structure, dev commands.
2. **`constitution.md`** — project identity (Section 1, populated by setup-wizard) and universal coding rules. The `[project-specific]` sections are sentinel-marked at this stage; `{{cli.sigil}}constitute` populates them later from onboard's findings + user preferences.
3. **`.devforge/project-config.json`** — wizard-detected facts: `LANGUAGES[]`, `FRAMEWORKS[]`, `WORKSPACE_MODE` (`standalone`/`wrapper`), `SOURCE_ROOT`, `manifest_count`, `packages[]`, etc.
4. **`.devforge/memory.md`** — pre-seeded knowledge from setup wizard (cross-runtime shared file).

Compile a **project brief** — concise summary (~30 lines max) of what's already known: project name, type, stack, architecture pattern (if wizard captured), error handling pattern, API layer, testing framework, pre-seeded findings.

Do NOT include layer boundaries, domain entities, or naming conventions — those are the tech-writer's job to DISCOVER during scan, not preconditions.

### 1.2: Discover Documentation Units

Read `.devforge/detection_report.yaml` (or `project-config.json` if the wizard exposes it differently) to get the `packages[]` array. Each entry has a `path` field — the actual filesystem location of a manifest (package.json, Cargo.toml, pyproject.toml, go.mod, pom.xml, *.csproj, Gemfile, composer.json).

**A documentation unit is one of:**

- Each entry in `packages[]` (one unit per detected manifest).
- If `packages[]` is empty or has only one entry pointing to the workspace/source root, **the project itself is the single unit** (single-source-tree projects).

**The unit's doc location** = `docs/<unit-path>/index.md`, mirroring whatever path the wizard found:

- npm package at `packages/pkg-foo/` → `docs/packages/pkg-foo/index.md`
- Rust crate at root (`my-cli/`) → `docs/my-cli/index.md`
- Rust crate in custom folder (`workspace/crates/my-lib/`) → `docs/workspace/crates/my-lib/index.md`
- Go module at root (path = `.`) → `docs/index.md`
- Java module at `services/billing/` → `docs/services/billing/index.md`
- Single-app project (`packages[]` = `[{path: "."}]`) → `docs/index.md`

**WORKSPACE_MODE** (`standalone` or `wrapper`) is irrelevant to unit discovery — it encodes only whether LLM tooling lives inside or alongside the project folder.

### 1.3: Determine Subagent Strategy

| Source files | Strategy |
|---|---|
| < 50 | Direct: orchestrator writes everything itself, no subagents. |
| 50–500 | One subagent per documentation unit. Sequential or small parallel batches respecting runtime concurrency limits. |
| 500+ | One subagent per unit, parallel batches. |

**Subagent dispatch rule**: invoke subagents WITHOUT full-history fork. Each subagent receives a self-contained prompt with: unit identifier, scope path, project brief from §1.1, per-doc template (Section A.2), write target. They do not need the orchestrator's conversation history.

---

## PHASE 2: Execute Onboarding Scan

Launch the tech-writer agent via `{{cli.subagent}}` with the prompt below. The tech-writer handles the scan + `docs/` writing per the mirror-folder shape derived in §1.2. Verification (§3) and memory-append (§3.6) stay in the orchestrator's lane.

For each documentation unit, dispatch one subagent (or, for small projects, run direct).

### Prompt template

```
You are operating in ONBOARDING MODE. This is NOT your normal task-documentation workflow. You are performing a one-time deep scan of an existing codebase to generate comprehensive project documentation.

## Project Brief

[Insert project brief from §1.1]

## Documentation Unit Assigned

Unit path: [absolute or workspace-relative path]
Write target: docs/<unit-path>/

## Your Mission

Generate complete documentation for this unit at the write target. Every agent reads docs/ before making changes; the quality of your documentation directly determines how well agents understand and work with this codebase.

## CORE MANDATE — COVER ALL CODE

Every meaningful source folder under this unit gets a documentation home. No sample-based silence. No skipping at scale. No "we'll cluster these into one file" merges that drop substance.

Density adapts to size — a small utility folder gets a short section; a complex multi-concern subfolder gets its own file with substantive depth — but every meaningful source folder is documented.

If you are tempted to merge two distinct concerns into one doc with a compound name (e.g. "auth-and-routing.md", "stores-and-services.md"), STOP — that's the failure mode this command is designed to prevent. Each distinct concern gets its own file. Compound names with "and" are a red flag; split them.

## Mode

[Insert mode from §1.0: overwrite | merge | fresh]

## Documentation Shape

Mirror the unit's folder structure under docs/<unit-path>/.

1. The unit gets `docs/<unit-path>/index.md` — the unit's main doc.
2. Within the unit, find the source root by ecosystem convention (the LLM observes per language):
   - JS/TS/PHP-PSR4: src/
   - Rust: src/
   - Ruby: lib/
   - Java/Kotlin: src/main/java/<groupId>/<pkg>/ (collapse boilerplate path segments to start at the meaningful level)
   - Python: src/<pkg>/ or <pkg>/
   - Go: unit root (no source-folder convention; subfolders like cmd/, pkg/, internal/ are direct concerns)
   - C#/.NET: project folder directly
3. Mirror the source root's substantive subfolders as sub-docs at `docs/<unit-path>/<concern>.md` (or `docs/<unit-path>/<concern>/index.md` + further sub-docs when the concern has its own substantial sub-tree).
4. Trivial subfolders (1-2 files, single-purpose utilities) fold into the parent doc rather than getting their own files.
5. Stop at file granularity. Files don't get individual docs; they're enumerated within their folder's doc.

## Per-Doc Template (required sections, in order)

For each `docs/<unit-path>/index.md` and each meaningful concern sub-doc:

1. `# <unit or concern name>`
2. `## Overview` — 1 paragraph: what this provides, who consumes it.
3. `## Directory Structure` — annotated tree of the source layout (the actual paths). Mark non-exported subdirs explicitly (e.g., "`<subdir>/` — internal, not exported").
4. `## Main Exports` (or `Public Surface`, `Public API`) — every exported symbol grouped by concern. For each: signature + a code block lifted from real source with a `<!-- path/file.ext:line-range -->` reference comment. Group by concern (CRUD, lifecycle, validation, etc.) so an agent adding a parallel operation can locate the nearest pattern.
5. `## Types` (or `Data Shapes`) — principal types this exposes, full inline definitions. Not "see types.ts" — the actual type definitions inline.
6. `## Dependencies` — workspace-internal and external dependencies. Workspace-internal entries hyperlink to their docs (e.g., `[pkg-bar](../pkg-bar/index.md)`); each entry gets one line about what's used. External deps named with version, no link.
7. `## Usage Example` — lifted from a real consumer file in the codebase. End-to-end pattern showing how the unit is consumed.

## Code-Block Discipline

Every code block in the docs MUST be lifted from actual source. Add a `<!-- path/to/file.ext:line-range -->` reference comment immediately above each block. Never invent code. Never paraphrase. If the LLM-generated text reads "here's an example" but the example came from your head — delete it and find a real one in the source.

Annotate non-exported subdirs explicitly. These annotations help downstream agents avoid false leads.

## Boundary Surface, Not Implementation

Document what crosses module/package/component boundaries: exported functions, public class members, route handlers, type definitions, props/emits/slots. Do NOT document private helpers, internal-only utilities, or implementation bodies.

The visibility model is the language's, not ours. The LLM knows each language's idiomatic boundary mechanism (TS `export`, Python `_` convention / `__all__`, Vue parent-contract via `defineExpose`/`props`/`emits`, Go capitalization, Rust `pub`, C# `public`/`internal`, Java member modifiers, etc.). Apply that language's mechanism. Skip what doesn't cross the boundary.

- ✅ YES: "`ReportService.generate(input: ReportInput): Either<ReportError, Report>` — builds a report from the input. <!-- src/services/report.ts:24-38 -->"
- ❌ NO: "`generate` first validates the input, then queries the database, then renders each section by calling helper X which loops..."

## What NOT to Document

- Implementation bodies — code is the source of truth for how something works internally.
- Private helpers / internal-only functions — name them well in code; skip the doc.
- Duplicated rules from `constitution.md` — docs describe what EXISTS; constitution describes the RULES.
- Tech-stack / dev-command duplication from the runtime primer — primer is the source of truth.
- Anything the scan is uncertain about — better silent than wrong.

[Insert full Section A instructions below — A.1 Smart Extraction, A.2 Per-Doc Templates, A.3 Sigil Neutrality, A.4 Quality Checks, A.5 Memory Enrichment.]
```

After all subagents return, the orchestrator additionally produces:

- **`docs/architecture.md`** at workspace root of `docs/` — workspace-level overview, observed architectural patterns (multi-pattern when present), conventions, dependency-direction rules. See A.2 architecture.md template.
- **Optional `docs/cross-cutting/<topic>.md`** — only when the LLM observes a pattern that genuinely spans units without a folder home.

---

## PHASE 3: Process Results

### 3.1: Coverage Check (FIRST gate)

**Coverage failure blocks proceed.**

1. For every entry in `packages[]`, confirm `docs/<unit-path>/index.md` exists with substantive content (>30 lines or >2 sections beyond title).
2. For every meaningful source subfolder of every unit, confirm a corresponding doc exists (sub-doc OR section in parent's index.md covering it).
3. `docs/architecture.md` exists with substantive content.
4. Listing-diff produces miss list. Any miss = failure.

If coverage fails, do NOT silently proceed. Report which units / subfolders are missing or thin, and ask the user:

- **Re-run the tech-writer** to fill gaps.
- **Accept** — user explicitly waives the gap.
- **Abort** — user reconciles manually.

### 3.2: Structural-Completeness Check

For every generated doc file: verify it contains the required sections from A.2's per-doc template — Overview present and substantive, Main Exports section with code blocks, Types section, Dependencies, Usage Example. A doc missing types-inline OR missing real code blocks fails verification even if the file exists.

### 3.3: Code-Block Sourcing Check

Spot-check 5 random code blocks across `docs/`. Each must have a `<!-- path/file.ext:line-range -->` reference comment OR a clearly-cited source path in surrounding prose. Any unsourced block = failure.

### 3.4: Cross-Link Existence Check

Spot-check 5 random Markdown links in `docs/*.md` resolve to existing files. Broken links = failure.

### 3.5: Term + Sigil Hygiene

- **Term hygiene**: locked terminology (Glossary below) used precisely. "package", "module", "feature", "concern" — no loose interchange.
- **Sigil hygiene**: no `/<command>` or `$<command>` strings in any `docs/*.md`. Cross-runtime artifacts use bare command names. See A.3.

If any check (3.2–3.5) fails, report findings (file path + what's wrong + what to correct) and ask **Proceed** / **Re-run** / **Abort**.

### 3.6: Update Memory

If the tech-writer returned `MEMORY_ADDITIONS` — a category-keyed structure with entries — append them to `.devforge/memory.md` (cross-runtime shared file) under existing scaffold sections:

- **Module/package boundaries** → `## Architecture Decisions` as new sub-section `### Module boundaries (from onboard)`.
- **Dependency warnings** → `## Known Pitfalls`.
- **Areas of complexity** → `## Known Pitfalls`.
- **Inconsistencies** → `## Known Pitfalls`.

Scaffold has four top-level sections (Architecture Decisions, Known Pitfalls, What Worked, What Failed) — do NOT create new top-level sections; add as sub-sections.

The tech-writer mandate (per A.5): report observations from EVERY unit, not a curated subset.

### 3.7: Drop Baselines

For each generated `docs/<path>` file, copy it to `.devforge/baseline/docs/<path>` so future re-runs detect user edits.

---

## PHASE 4: Summary

Present to the user:

```
## Onboarding Complete

### Documentation Generated
- [N] documentation units mirrored under `docs/`
- `docs/architecture.md`
- [list optional `docs/cross-cutting/*` if any]

### Scan
- [count] source files across [count] units (subagent-strategy: [direct | per-unit | parallel-per-unit])

### Memory Updated
[Summarize in 1-3 lines what was appended to .devforge/memory.md.]

### Next Steps
1. Review `docs/` and adjust as needed
2. Run `{{cli.sigil}}constitute` — turn scan findings + your architectural preferences into enforceable rules in `constitution.md`
3. Start working: `{{cli.sigil}}specify "your first feature"`
```

---

## SECTION A: Tech-Writer Onboarding Instructions

These instructions are inlined into the tech-writer agent prompt at the placeholder above (Phase 2).

**Source Root**: All source code scanning targets the Source Root specified in the runtime primer (`{{cli.primer}}`), or canonically in `.devforge/project-config.json` `SOURCE_ROOT` field. For wrapper-mode projects, this is a subfolder.

### A.1: Smart Extraction — What to Read from Each File Type

Context is finite. Extract the high-information content from each file type; skip the rest.

| File Type | What to Extract | What to Skip |
|---|---|---|
| Type/interface/trait/protocol definitions (`.d.ts`, `types.ts`, `.pyi`, `interfaces/`, `entities/`; Rust `trait`/`struct`/`enum`; Python `Protocol`/`TypedDict`/dataclass; Go `type`; Swift `protocol`/`struct`; Kotlin `sealed`/`data class`) | Read full content — highest information density | Nothing |
| Index/barrel/module entry files (`index.ts`, `__init__.py`, `mod.rs`, `lib.rs`; Go `package`; Swift `@_exported import`; Java/Kotlin module-info) | Read full content — defines module boundaries | Nothing |
| Route/API definitions (HTTP routes, gRPC services, GraphQL resolvers, RPC controllers, message handlers) | Read full content — defines API surface | Nothing |
| Config files (`.env.example`, config modules, framework config) | Read full content | `.env` (secrets) |
| Implementation files (services, repositories, helpers) | Function/method signatures, class/struct/trait definitions, imports, exports | Function bodies |
| UI component files (`.vue`, `.tsx`, `.svelte`, `.dart`; Android `@Composable` + XML; SwiftUI `View`; native mobile view classes) | Props/interface, template/view structure, emits/events, composable/hook usage | Template HTML/CSS details, style internals |
| Test files (JS/TS `describe`/`it`, Python `def test_*`, Rust `#[test]`, Go `func TestXxx`, JUnit `@Test`, XCTest, RSpec) | Test names only — these reveal WHAT the code does | Test bodies, assertions, mocks |
| Migrations/schemas (SQL, Alembic, Prisma, TypeORM, ActiveRecord, Flyway, Liquibase) | Schema definitions, table/type structures | Individual migration steps |
| Generated/vendored code (protobuf outputs, GraphQL codegen, SwiftGen, vendored deps) | Skip entirely | Everything |
| Assets (images, fonts, static) | Skip entirely | Everything |

**Ignore set** (never scan, never count): `node_modules/`, `target/`, `build/`, `dist/`, `.next/`, `.nuxt/`, `vendor/`, `.gradle/`, `.cargo/`, `__pycache__/`, `.venv/`, `venv/`, `.tox/`, `.mypy_cache/`, `.ruff_cache/`, `coverage/`, `.coverage`, `.cache/`, `tmp/`, `.tmp/`, `bin/`, `obj/`, `Pods/`, `.bundle/`, `.dart_tool/`, plus the cross-runtime artifacts (`.claude/`, `.codex/`, `.devforge/`, `specs/`, `docs/`), lock files, and binary/asset files.

### A.2: Per-Doc Templates

#### A.2.1 — Per-unit / per-concern doc template

For each `docs/<unit-path>/index.md` and each meaningful concern sub-doc, the template defined in Phase 2's prompt applies (Overview / Directory Structure / Main Exports with sourced code blocks / Types inline / Dependencies with cross-links / Usage Example).

Length adapts to scope:
- Tiny utility folder: 30–80 lines (folded into parent if even smaller).
- Small library / single-concern subdir: 80–200 lines.
- Mid-size unit: 200–400 lines.
- Composite unit (multi-concern): main `index.md` is overview + directory + cross-references to sub-docs; sub-docs carry per-concern depth.

#### A.2.2 — `docs/architecture.md` template

`architecture.md` carries the project's actual architectural patterns, dependency directions, naming conventions, decision rules — observed from the codebase, not prescribed by the spec.

Required sections:

1. **Architecture overview** — what the project IS at the architectural level.
2. **Module/package structure** — workspace layout, how units relate.
3. **Patterns** — every architectural pattern observed in the codebase. **A project may legitimately have multiple coexisting patterns** (e.g., MVC in backend services + Clean Architecture in frontend; legacy procedural code being phased out alongside modern layered code; different paradigms in different microservices). When multiple patterns coexist, document each with explicit "where it applies" scope:
   ```
   ### <Pattern A> (applies in: <unit-paths or module-paths>)
   <observed description, conventions, decision rules>

   ### <Pattern B> (applies in: <other paths>)
   <observed description>
   ```
   Do NOT force-fit the project into a single pattern when more than one exists.
4. **Conventions** — naming, file organization, import style, error handling — all observed. If conventions vary across patterns, scope each accordingly.
5. **Cross-cutting concerns** — auth flow, data flow, state management, error propagation — all observed.
6. **Dependency direction rules** — observed (where inward/outward dependencies go); per-pattern when patterns diverge.
7. **Dependency overview** — high-level "who depends on whom" listing across all units. Mermaid graph OR plain bullet list. Bird's-eye view complementing per-unit `Dependencies` sections.

**Per-unit overrides**: a unit's `index.md` MAY contain a "Pattern" section when that unit follows a distinct pattern worth calling out at unit level (cross-reference `docs/architecture.md` for workspace context).

**Optional split**: when one or more patterns warrant their own deep document, split into `docs/architecture/<pattern>.md` per pattern; `docs/architecture.md` becomes the index pointing at each.

#### A.2.3 — `docs/cross-cutting/<topic>.md` (optional)

Only when the LLM observes a pattern that genuinely spans multiple units without a folder home (e.g., authentication flow that touches an auth package, a router config in an app, and middleware in another service). Each cross-cutting topic explicitly hyperlinks into every unit it touches.

### A.3: Cross-Runtime Sigil Neutrality (MANDATORY)

`docs/` is read by both Claude and Codex runtimes. Any prose in any `docs/*.md` that names a command — `onboard`, `constitute`, `specify`, `plan`, `breakdown`, `execute-task`, `verify`, or any other workflow command — must use the **bare command name**. Never prefix with `/` (Claude's sigil) or `$` (Codex's sigil). The runtime-specific sigil belongs in user-facing command output (wizard summaries, command headers), not in project documentation.

- ✅ RIGHT: "Run onboard again after significant changes."
- ❌ WRONG: "Run `/onboard` again..." or "Run `$onboard`..."

If you need to show a literal command invocation, phrase it sigil-neutrally: "invoke the `onboard` command in your runtime."

### A.4: Quality Checks (your self-check before returning)

Before returning, verify:

1. **Coverage**: every meaningful source folder under your assigned unit has a doc home. **This is the load-bearing check.**
2. **Structural completeness**: every doc has the required template sections — Overview, Directory Structure, Main Exports with sourced code blocks, Types inline, Dependencies, Usage Example.
3. **Real code only**: every code block in docs is copied from actual source with a `<!-- path/file.ext:line-range -->` reference. No invented code.
4. **Boundary surface only**: docs enumerate what crosses module/class/component boundaries. Internals stay in source.
5. **Cross-references resolve**: workspace-internal `Dependencies` entries link to their package docs; broken links not allowed.
6. **No constitution duplication**: docs describe HOW the code is organized; constitution describes the RULES.
7. **No primer duplication**: tech-stack and dev-command tables live in `{{cli.primer}}`; do not repeat them in `docs/`.
8. **Sigil neutrality**: no `/<cmd>` or `$<cmd>` strings anywhere in `docs/`.
9. **Inline annotations**: subdirs that exist in source but are NOT exported are explicitly annotated in directory trees.
10. **No source modifications**: onboarding mode does NOT modify source files. Only `docs/` and (via the orchestrator) `.devforge/memory.md`.

### A.5: Memory Enrichment

After generating docs, return a summary of findings to be added to `.devforge/memory.md`. **Cover every unit, not a curated subset.**

Include:

- **Module/package boundaries** — every unit's responsibility in 1 line.
- **Cross-package dependency warnings** — tightly coupled areas, circular imports, brittle interfaces observed.
- **Areas of complexity** — units or concerns with many dependencies, unusual patterns, or unclear conventions.
- **Inconsistencies** — self-contradictions within observed code (different error-handling styles in the same unit, divergent naming, etc.), or deviations from constitution's `[universal]` sections.

**Return format:**

```
## MEMORY_ADDITIONS

### Module/package boundaries
- <unit-1>: <one-line responsibility>
- <unit-2>: <one-line responsibility>
- ... (every unit, not a sample)

### Dependency warnings
- <observation>

### Areas of complexity
- <unit/area>: <why it's complex>

### Inconsistencies
- <what was expected vs what was found>
```

---

## Glossary (locked terminology)

These terms have precise meanings in onboard's output and downstream consumers:

| Term | Means |
|---|---|
| **package** | A self-contained unit detected by the wizard — one entry in `packages[]`. Has its own manifest (package.json, Cargo.toml, etc.). |
| **unit** (documentation unit) | A package, OR the project itself if `packages[]` has only a root entry. The thing onboard generates a `docs/<unit-path>/` folder for. |
| **concern** | A meaningful subfolder within a unit's source root (e.g., `components/`, `services/`, `routing/`, `handlers/`). Each substantive concern gets its own sub-doc. |
| **boundary surface** | Symbols that cross a file/class/component boundary (exports, public class members, props/emits/slots, route handlers). What docs enumerate. |
| **module** | Used loosely to mean a directory inside a unit; not a fixed-meaning term in this command's output. Prefer "concern" for sub-folder docs and "package"/"unit" for top-level. |

---

## IMPORTANT RULES

1. **Cover all code** — every package or meaningful source folder gets a doc home. Coverage failure is verification failure.
2. **Tech-writer owns scan + docs writing** — orchestrator handles pre-scan, post-scan verification, memory append, baseline drop.
3. **Never modify source files** — onboarding writes only to `docs/`, `.devforge/memory.md`, and `.devforge/baseline/`.
4. **Code blocks lifted from real source** — every block has a `<!-- path/file.ext:line-range -->` reference. No invented code.
5. **Boundary surface, not implementation** — what crosses module boundaries. Skip internals.
6. **Mirror folder structure** — `docs/<unit-path>/...` mirrors the source layout. Path-from-source = path-to-docs.
7. **No bundled pattern assumptions** — `architecture.md` observes the project's actual patterns; spec mandates structure not content. Document multi-pattern projects honestly.
8. **Preserve user-edited docs** — §1.0 detects user edits via baseline diff. Re-runs ask Overwrite/Merge/Abort, never silently overwrite.
9. **Sigil-neutral prose in `docs/`** — `docs/` is cross-runtime; use bare command names.
10. **No constitution / primer duplication** — docs describe what EXISTS; constitution + primer carry their own concerns.
11. **This is for agents** — primary audience is the agents running subsequent commands. Be explicit, structured, precise. Documents must be a substitute for first-pass code reading.
