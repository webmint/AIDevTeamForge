# Tech-Writer Onboarding Instructions

These instructions are included in the tech-writer agent prompt when running `{{cli.sigil}}onboard`. They define how to scan an existing codebase and generate comprehensive project documentation.

**Source Root**: All source code scanning targets the Source Root specified in the runtime primer (`{{cli.primer}}`), or canonically in `.devforge/project-config.json` `SOURCE_ROOT` field. For wrapper mode projects, this is a subfolder (e.g., `client-project/`). Cross-runtime artifacts (`specs/`, `docs/`, `constitution.md`, `.devforge/`) are at the workspace root, not inside the Source Root.

## A.1: Scanning Rules — Protecting Context

You are scanning a potentially large codebase. Context is a finite resource. Follow these rules strictly:

### Smart Extraction — What to Read from Each File Type

| File Type | What to Extract | What to Skip |
|---|---|---|
| **Type / interface / trait / protocol definitions** (`.d.ts`, `types.ts`, `.pyi`, `interfaces/`, `entities/`; Rust `trait` / `struct` / `enum`; Python `Protocol` / `TypedDict` / dataclass; Go `type` declarations; Swift `protocol` / `struct`; Kotlin `sealed class` / `data class`) | Read full content — highest information density | Nothing |
| **Index / barrel / module entry files** (`index.ts`, `__init__.py`, `mod.rs`, `lib.rs`; Go `package` declarations, Swift `@_exported import`, Java / Kotlin module-info / re-exports) | Read full content — defines module boundaries | Nothing |
| **Route / API definitions** (HTTP routes, gRPC services, GraphQL resolvers, RPC controllers, message handlers) | Read full content — defines API surface | Nothing |
| **Config files** (`.env.example`, config modules) | Read full content | `.env` (secrets) |
| **Implementation files** (services, repositories, helpers) | Function/method signatures, class/struct/trait definitions, imports, exports | Function bodies (skip internal logic) |
| **UI component files** (UI projects only — `.vue`, `.tsx`, `.svelte`, `.dart` Flutter widgets, Android `@Composable` + XML layouts, SwiftUI `View` types, native mobile view classes) | Props / interface, template or view structure, emits / events, composable / hook usage | Template HTML / CSS details, style internals |
| **Test files** (JS/TS `describe`/`it`/`test`, Python `def test_*`, Rust `#[test]`, Go `func TestXxx`, JUnit `@Test`, XCTest methods, RSpec `describe`/`it`) | Test names only — these reveal WHAT the code does | Test bodies, assertions, mocks |
| **Migrations / schemas** (SQL migrations, Alembic, Prisma schema, TypeORM, ActiveRecord, Flyway, Liquibase) | Schema definitions, table / type structures | Individual migration steps |
| **Generated / vendored code** (protobuf outputs, GraphQL codegen, SwiftGen, vendored deps) | Skip entirely | Everything |
| **Assets** (images, fonts, static) | Skip entirely | Everything |

### Subagent Usage (for 50+ file projects)

When the scan strategy requires subagents, launch them via {{cli.subagent}}. Each subagent scans ONE module.

**Subagent prompt template:**
```
Scan the module at `[module-path]` and return a structured summary.

Project context: [1-2 lines about the project from the brief]
Architecture: [architecture pattern]

## What to Read
- ALL type/interface files in this module — full content
- ALL index/barrel files — full content
- ALL route/API files — full content
- Implementation files — signatures, imports, exports ONLY (skip function bodies)
- Test files — test names ONLY (skip test bodies)
- Skip: the ecosystem-aware ignore set from `detect.md` STEP 1 "Count source files" (build output, dependency trees, tool caches, cross-runtime artifacts across Rust / Java / .NET / Python / Ruby / Haskell ecosystems), plus generated files and assets

## Return Format

**Mandatory sections** (always include, even if short):

### Module: [name]
**Path**: [directory path]
**Purpose**: [one sentence — what this module is responsible for]

**Key Types**:
- `TypeName` — [one-line description]

**Exports** (public API of this module):
- `functionName(params): ReturnType` — [one-line description; format per project's language]
- `ClassName` — [one-line description]

**Internal Dependencies** (other project modules this imports from):
- `[module-name]` — [what it uses from that module]

**External Dependencies** (npm / pip / cargo / gem / go-mod / maven / gradle / SwiftPM / CocoaPods packages, per the project's ecosystem):
- `[package]` — [how it's used]

**Conditional sections** (include only when present in this module — OMIT the section entirely if nothing to report; do NOT write "(none)" filler):

**Patterns Used** — if the module demonstrates a non-obvious naming, error-handling, state-management, or similar convention worth recording:
- [observed pattern]

**API Surface** — if the module exposes routes / endpoints / gRPC services / GraphQL resolvers / WebSocket handlers:
- `<identifier per protocol>` — [description]

**Key Business Logic** — if domain rules or constraints are visible in types, validation, or function names:
- [rule or constraint]

**Notable** — if anything is unusual, complex, or important for someone modifying this code:
- [observation]

Do not reorder mandatory sections. Do not add sections beyond the conditional list above.
```

**Rules for subagents:**
- Each subagent returns MAX 50 lines
- Launch subagents in small batches, not all at once — respect your runtime's concurrency limits and avoid exhausting context. If module count exceeds your runtime's practical parallelism, batch: launch a chunk, wait for results, then launch the next chunk.
- Aggregate all summaries before writing any docs

### For 1000+ File Projects — Sample-Based Scanning

When sample-based strategy is selected:
1. Read ALL type/interface definition files (these are always worth reading fully)
2. Read ALL index/barrel/entry-point files
3. Read ALL route/controller/endpoint files
4. For each module: read 2-3 representative implementation files (pick the largest or most-imported ones)
5. Read test file NAMES only (not contents) — the file names reveal what features exist
6. Flag in `docs/overview.md` that this was a sample-based scan: `> Note: This documentation was generated from a structural scan. Some internal details may be incomplete. Run {{cli.sigil}}onboard again after significant changes.`

## A.2: Documentation Generation

After scanning (directly or via subagent summaries), generate the following docs:

- `docs/overview.md`
- `docs/architecture.md`
- `docs/features/<module>.md` (one per substantive module)
- `docs/api/<resource>.md` (only if the project exposes an API)

**Per-file structure and depth**: follow the **Documentation Requirements** section above in this same prompt. It specifies (a) the read-frequency map that drives density per file, (b) the per-file section layout for each of the four doc types, (c) the Depth principle (describe conventions and structure, not implementation), and (d) the "What NOT to document" list. That section is authoritative — do NOT extend, replace, or duplicate its specified structures here.

**Language / framework agnosticism**: file extensions, code-fence languages, and naming conventions referenced in the Documentation Requirements are illustrative. Adapt to the project's actual language and framework. If the project is Rust, Go, Python, Swift, Kotlin, etc., substitute the ecosystem's equivalents for file suffixes, import syntax, type-definition form, and any code examples you quote. Every code example you include in docs must be **copied** from the actual codebase — never invent examples.

**Conditional outputs**:

- `docs/features/<module>.md` — produce one per substantive module surfaced in the scan. Skip a module if the scan found nothing substantial (Documentation Requirements' "better no doc than a stub").
- `docs/api/<resource>.md` — only if the project exposes an API. Adapt the endpoint identifier to the protocol:
  - **REST**: `METHOD /path` (e.g. `GET /users/:id`), JSON payloads
  - **gRPC**: `service.method`, protobuf message types (document by name, don't paste protobuf)
  - **GraphQL**: query / mutation / subscription names, schema-typed payloads
  - **WebSocket**: event / message type names, wire format the project uses
  - **tRPC**: procedure name + input / output types

## A.3: Quality Checks

After generating all docs, verify:

1. **Every file path mentioned exists** — verify using your runtime's file-discovery mechanism (file-listing tool, glob, or shell `ls` / `find` as available)
2. **Every code example is from the actual codebase** — no invented code
3. **Every module in the module map has documentation** (either in `features/`, `api/`, or mentioned in `overview.md`/`architecture.md`)
4. **No docs reference non-existent files, functions, or types**
5. **Cross-references are correct** — if one doc links to another, the target exists
6. **No duplicate information** — if something is in `architecture.md`, don't repeat it in every feature doc
7. **Inline docs are NOT touched** — onboarding mode does NOT modify source files. Only `docs/` folder.

## A.4: Memory Enrichment

After generating docs, return a summary of findings to be added to `.devforge/memory.md` (cross-runtime shared file — both Claude and Codex read it). The summary should include:
- Key module boundaries and their responsibilities
- Cross-module dependency warnings (tightly coupled areas)
- Areas of complexity or risk (modules with many dependencies, unclear patterns)
- Any inconsistencies found (naming violations, pattern deviations from constitution)

**Return format:**
```
## MEMORY_ADDITIONS

### Module Boundaries
- [module]: [responsibility]

### Dependency Warnings
- [observation about tight coupling or circular dependencies]

### Areas of Complexity
- [module/area]: [why it's complex]

### Inconsistencies Found
- [what was expected vs what was found]
```
