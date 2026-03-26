# Tech-Writer Onboarding Instructions

These instructions are included in the tech-writer agent prompt when running `/onboard`. They define how to scan an existing codebase and generate comprehensive project documentation.

**Source Root**: All source code scanning targets the Source Root specified in `CLAUDE.md`. For wrapper mode projects, this is a subfolder (e.g., `client-project/`). Claude artifacts (`specs/`, `docs/`, `constitution.md`) are at the workspace root.

## A.1: Scanning Rules — Protecting Context

You are scanning a potentially large codebase. Context is a finite resource. Follow these rules strictly:

### Smart Extraction — What to Read from Each File Type

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

### Subagent Usage (for 50+ file projects)

When the scan strategy requires subagents, launch them using the Agent tool. Each subagent scans ONE module.

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
- Do not launch more than 8 subagents in parallel (context + rate limits)
- If there are more than 8 modules, batch them: launch 8, wait for results, then launch the next batch
- Aggregate all summaries before writing any docs

### For 1000+ File Projects — Sample-Based Scanning

When sample-based strategy is selected:
1. Read ALL type/interface definition files (these are always worth reading fully)
2. Read ALL index/barrel/entry-point files
3. Read ALL route/controller/endpoint files
4. For each module: read 2-3 representative implementation files (pick the largest or most-imported ones)
5. Read test file NAMES only (not contents) — the file names reveal what features exist
6. Flag in `docs/overview.md` that this was a sample-based scan: `> Note: This documentation was generated from a structural scan. Some internal details may be incomplete. Run /onboard again after significant changes.`

## A.2: Documentation Generation

After scanning (directly or via subagent summaries), generate the following docs. Each file has a specific purpose for agents.

### `docs/overview.md` — Project Overview

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

### `docs/architecture.md` — Architecture & Patterns

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

### `docs/features/*.md` — Feature Documentation

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
- Do not create a file for `shared/` or `utils/` unless they contain significant domain logic — document them in `architecture.md` instead
- If a module is tiny (1-2 files, no domain logic), mention it in `overview.md` instead of creating a separate file
- Every code example must be copied from the actual implementation — never invent examples

### `docs/api/*.md` — API Documentation (if applicable)

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

## A.3: Quality Checks

After generating all docs, verify:

1. **Every file path mentioned exists** — use Glob to verify
2. **Every code example is from the actual codebase** — no invented code
3. **Every module in the module map has documentation** (either in `features/`, `api/`, or mentioned in `overview.md`/`architecture.md`)
4. **No docs reference non-existent files, functions, or types**
5. **Cross-references are correct** — if one doc links to another, the target exists
6. **No duplicate information** — if something is in `architecture.md`, don't repeat it in every feature doc
7. **Inline docs are NOT touched** — onboarding mode does NOT modify source files. Only `docs/` folder.

## A.4: Memory Enrichment

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
