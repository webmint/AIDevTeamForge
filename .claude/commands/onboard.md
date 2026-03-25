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

Launch the tech-writer agent using the Agent tool (Task tool) with the prompt built below. The tech-writer does ALL the heavy lifting.

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

**These instructions are included verbatim in the tech-writer agent prompt.**

**Source Root**: All source code scanning targets the Source Root specified in `CLAUDE.md`. For wrapper mode projects, this is a subfolder (e.g., `client-project/`). Claude artifacts (`specs/`, `docs/`, `constitution.md`) are at the workspace root.

### A.1: Scanning Rules — Protecting Context

You are scanning a potentially large codebase. Context is a finite resource. Follow these rules strictly:

#### Smart Extraction — What to Read from Each File Type

| File Type | What to Extract | What to Skip |
|---|---|---|
| **Type/interface definitions** (`.d.ts`, `types.ts`, `interfaces/`, `entities/`) | Read full content — highest information density | Nothing |
| **Index/barrel files** (`index.ts`, `__init__.py`, `mod.rs`) | Read full content — defines module boundaries | Nothing |
| **Route/API definitions** (routes, controllers, endpoints) | Read full content — defines API surface | Nothing |
| **Config files** (`.env.example`, config modules) | Read full content | `.env` (secrets) |
| **Implementation files** (services, repositories, helpers) | Function/method signatures, class definitions, imports, exports | Function bodies (skip internal logic) |
| **Components** (`.vue`, `.tsx`, `.svelte`) | Props/interface, template structure, emits/events, composable/hook usage | Template HTML details, CSS |
| **Test files** | `describe`/`it`/`test` names only — these reveal WHAT the code does | Test bodies, assertions, mocks |
| **Migrations/schemas** | Schema definitions, table structures | Individual migration steps |
| **Generated/vendored code** | Skip entirely | Everything |
| **Assets** (images, fonts, static) | Skip entirely | Everything |

#### Subagent Usage (for 50+ file projects)

When the scan strategy requires subagents, launch them using the Agent tool (Task tool). Each subagent scans ONE module.

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
- Skip: generated files, assets, node_modules, dist

## Return Format (STRICT — do not deviate)

### Module: [name]
**Path**: [directory path]
**Purpose**: [one sentence — what this module is responsible for]

**Key Types/Interfaces**:
- `TypeName` — [one-line description]

**Exports** (public API of this module):
- `functionName(params): ReturnType` — [one-line description]
- `ClassName` — [one-line description]

**Internal Dependencies** (other project modules this imports from):
- `[module-name]` — [what it uses from that module]

**External Dependencies** (npm packages, libraries):
- `[package]` — [how it's used]

**Patterns Used**:
- [naming, error handling, state management patterns observed]

**API Surface** (if this module exposes routes/endpoints):
- `METHOD /path` — [description]

**Key Business Logic** (domain rules visible in types, validation, or function names):
- [rule or constraint]

**Notable** (anything unusual, complex, or important for someone modifying this code):
- [observation]
```

**Rules for subagents:**
- Each subagent returns MAX 50 lines
- Do NOT launch more than 8 subagents in parallel (context + rate limits)
- If there are more than 8 modules, batch them: launch 8, wait for results, then launch the next batch
- Aggregate all summaries before writing any docs

#### For 1000+ File Projects — Sample-Based Scanning

When sample-based strategy is selected:
1. Read ALL type/interface definition files (these are always worth reading fully)
2. Read ALL index/barrel/entry-point files
3. Read ALL route/controller/endpoint files
4. For each module: read 2-3 representative implementation files (pick the largest or most-imported ones)
5. Read test file NAMES only (not contents) — the file names reveal what features exist
6. Flag in `docs/overview.md` that this was a sample-based scan: `> Note: This documentation was generated from a structural scan. Some internal details may be incomplete. Run /onboard again after significant changes.`

### A.2: Documentation Generation

After scanning (directly or via subagent summaries), generate the following docs. Each file has a specific purpose for agents.

#### `docs/overview.md` — Project Overview

**Purpose for agents**: First thing any agent reads. Quick orientation.

```markdown
# [Project Name]

## What This Project Does
[2-3 sentences explaining the project's purpose, who uses it, and what problem it solves]

## Tech Stack
| Layer | Technology |
|---|---|
| Language | [language + version if detectable] |
| Framework | [framework] |
| Build Tool | [build tool] |
| Testing | [test framework] |
| Styling | [styling approach — if applicable] |
| Database | [database — if applicable] |
| API Style | [REST/GraphQL/tRPC — if applicable] |

## Project Structure
[Annotated directory tree showing what each top-level directory contains]

```
src/
  auth/          # Authentication and authorization
  cart/          # Shopping cart management
  orders/        # Order processing and history
  shared/        # Cross-cutting utilities and types
```

## Entry Points
- **Application**: [main entry file and what it does]
- **Routes/API**: [where routes are defined]
- **Configuration**: [where config is loaded]

## Key Commands
[From CLAUDE.md — dev, build, test, lint commands]

## Module Map
[One-line description of each module and its responsibility]
- `auth` — User authentication, session management, role-based access
- `cart` — Cart state, pricing calculations, inventory checks
- `orders` — Order creation, payment processing, order history

## Cross-Module Dependencies
[Which modules depend on which — helps agents understand impact of changes]
- `orders` → `cart` (reads cart state), `auth` (checks permissions)
- `cart` → `auth` (user-scoped carts)
```

#### `docs/architecture.md` — Architecture & Patterns

**Purpose for agents**: Understanding HOW to write code that fits this project. Every agent reads this before making changes.

```markdown
# Architecture

## Architecture Pattern
[Pattern name and brief explanation of how it's applied in THIS project]

## Layer Boundaries
[Describe each layer and what belongs in it]
[Specify allowed dependency directions]
[Include a simple ASCII diagram if helpful]

```
Presentation → Domain → Data
     ↓            ↓        ↓
  Components   UseCases  Repositories
  Views        Entities  API Clients
  Stores       Interfaces  Mappers
```

## Module Structure
[How a typical module is organized internally]

```
src/[module-name]/
  types.ts          # Type definitions and interfaces
  [name].service.ts # Business logic
  [name].repo.ts    # Data access
  index.ts          # Public exports (barrel file)
```

## Key Patterns

### Error Handling
[How errors are created, propagated, and handled — with code example from the actual codebase]

### State Management
[How state is structured and updated — if applicable]

### API Layer
[How API calls are made — request/response patterns]

### Data Flow
[How data flows through the application — from entry point to response]

### Type Patterns
[How types are organized — shared types, module-specific types, DTOs, entities]

## Key Domain Types
[List the most important types/interfaces with brief descriptions — these help agents understand the data model]

```typescript
// Example from actual codebase
interface Order {
  id: string;
  userId: string;
  items: OrderItem[];
  status: OrderStatus;
  // ...
}
```

## Boundaries & Rules
[What agents MUST NOT do when working in this codebase — extracted from constitution]
- Never import from `data/` layer in `presentation/` — go through `domain/`
- Never mutate state directly — use store actions
- [other key boundaries]
```

#### `docs/features/*.md` — Feature Documentation

**Purpose for agents**: Understanding a specific area before modifying it. Created per logical feature area (NOT per file or per class).

Create ONE file per identified module/feature. Name: `docs/features/[module-name].md`

```markdown
# [Feature/Module Name]

## Overview
[What this module does — 2-3 sentences]

## Key Components
[List the main files/classes/functions with one-line descriptions]
- `auth.service.ts` — Core authentication logic: login, logout, token refresh
- `auth.guard.ts` — Route guard that checks authentication status
- `auth.types.ts` — User, Session, and Permission type definitions

## How It Works
[Explain the main flow — how data moves through this module]
[Include a code example from the actual implementation showing the key pattern]

## Public API
[What this module exports for other modules to use]
- `authenticate(credentials): Either<AuthError, Session>` — Validates credentials and creates a session
- `requireAuth(roles?: Role[]): Middleware` — Express middleware for route protection

## Dependencies
- **Uses**: [other modules this depends on]
- **Used by**: [other modules that depend on this]

## Key Types
[Important types defined in this module — copy from actual code]

## Business Rules
[Domain rules embedded in this module — validation, constraints, calculations]
```

**Rules for feature docs:**
- One file per logical feature area — group related files together
- Do NOT create a file for `shared/` or `utils/` unless they contain significant domain logic — document them in `architecture.md` instead
- If a module is tiny (1-2 files, no domain logic), mention it in `overview.md` instead of creating a separate file
- Every code example must be copied from the actual implementation — never invent examples

#### `docs/api/*.md` — API Documentation (if applicable)

**Only create if the project has API endpoints** (REST, GraphQL, tRPC).

Create ONE file per API resource/domain area. Name: `docs/api/[resource-name].md`

```markdown
# [Resource Name] API

## Endpoints

### `METHOD /path`
**Description**: [what it does]
**Auth**: [required/optional/none]
**Request**:
```json
{
  "field": "type — description"
}
```
**Response**:
```json
{
  "field": "type — description"
}
```
**Errors**: [error codes and when they occur]

## Types
[Request/response types from the actual codebase]

## Notes
[Rate limits, pagination, special headers, etc.]
```

### A.3: Quality Checks

After generating all docs, verify:

1. **Every file path mentioned exists** — use Glob to verify
2. **Every code example is from the actual codebase** — no invented code
3. **Every module in the module map has documentation** (either in `features/`, `api/`, or mentioned in `overview.md`/`architecture.md`)
4. **No docs reference non-existent files, functions, or types**
5. **Cross-references are correct** — if one doc links to another, the target exists
6. **No duplicate information** — if something is in `architecture.md`, don't repeat it in every feature doc
7. **Inline docs are NOT touched** — onboarding mode does NOT modify source files. Only `docs/` folder.

### A.4: Memory Enrichment

After generating docs, return a summary of findings to be added to `.claude/memory/MEMORY.md`. The summary should include:
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