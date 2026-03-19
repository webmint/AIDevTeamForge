# /constitute — Generate Project Constitution

You are generating the project's constitution — a persistent document that captures non-negotiable rules, architecture decisions, quality standards, and domain knowledge. This document is referenced by ALL other commands and agents.

## Prerequisites

- `/setup-wizard` must have been run first
- `CLAUDE.md` must exist at project root
- `.claude/agents/` must contain at least one agent

If any prerequisite is missing, inform the user and suggest running `/setup-wizard` first.

## MODE DETECTION

Before starting, determine which mode to use:

1. **Read `CLAUDE.md`** to check the **Source Root** field. If it is not `.`, this is a wrapper project — scan the Source Root path instead of the workspace root for all source code operations.
2. **Count source files** in the Source Root (exclude `node_modules`, `.git`, `dist`, `build`, `__pycache__`, `.next`, `.nuxt`, `vendor`)
3. If there are **fewer than 10 source files** (or the project has only boilerplate/scaffold files like a fresh `create-vite` or `create-next-app`), use **GREENFIELD MODE**
4. If there are **10+ meaningful source files**, use **EXISTING CODEBASE MODE**

Inform the user which mode you're using:
- Greenfield: "This looks like a new project. I'll build the constitution from your preferences and framework best practices."
- Existing: "This project has an established codebase. I'll analyze it to extract patterns and rules."

---

## GREENFIELD MODE (new project, no codebase yet)

### G-PHASE 1: Interview the User

Since there's no code to analyze, you need to understand the user's intentions. Ask targeted questions using AskUserQuestion. Batch into 2-3 rounds maximum.

#### Round 1: Architecture & Patterns

Ask these questions (adapt based on what `/setup-wizard` already captured):

**Question 1: Architecture Pattern**
"What architecture pattern do you want to follow?"
- Clean Architecture (layers: data → domain → presentation)
- Feature-based / Modular (self-contained feature folders)
- MVC / MVVM
- Simple / Flat (no formal architecture)
- Other

**Question 2: Strictness Level**
"How strict should the code rules be?"
- Maximum strictness (no `any`, no exceptions swallowed, strict linting, tests required for all logic)
- High strictness (occasional `any` with justification, tests for business logic)
- Moderate (pragmatic — strict where it matters, relaxed where it doesn't)

#### Round 2: Conventions

**Question 3: File Organization**
"How do you want files organized?"
- By layer (src/data/, src/domain/, src/presentation/)
- By feature (src/features/auth/, src/features/cart/)
- By type (src/components/, src/hooks/, src/utils/)
- Flat (everything in src/)

**Question 4: Error Handling**
"How should errors be handled?"
- Either/Result monads (functional, explicit error paths)
- Try/catch with typed error classes
- Traditional try/catch
- Framework default (let the framework handle it)

#### Round 3: Preferences (optional, only if needed)

**Question 5: Naming Conventions**
"Any specific naming preferences?"
- Framework defaults (e.g., PascalCase components for React/Vue, camelCase for functions)
- Custom (describe)

**Question 6: Testing Strategy**
"What's your testing plan?"
- TDD (tests first, always)
- Test business logic, skip UI tests
- Test everything (unit + integration + e2e)
- No tests initially (add later)

### G-PHASE 2: Research Framework Best Practices

Based on the framework detected by `/setup-wizard`, use WebSearch to find current best practices for:
- The specific framework's recommended project structure
- TypeScript/language configuration recommendations
- Recommended linting rules
- Common anti-patterns to avoid
- Official style guide (if one exists)

Combine these with the user's answers to build a best-practices-informed constitution.

### G-PHASE 3: Generate Starter Directory Structure

Based on the chosen architecture, propose a directory structure. For example:

**Clean Architecture + Vue 3:**
```
src/
  data/           # Repositories, API clients, external services
    repositories/
    mappers/
  domain/         # Use cases, entities, interfaces
    entities/
    usecases/
    interfaces/
  presentation/   # Components, views, composables, stores
    components/
    views/
    composables/
    stores/
  shared/         # Cross-cutting: types, utils, constants
    types/
    utils/
    constants/
```

**Feature-based + React:**
```
src/
  features/
    auth/
      components/
      hooks/
      api/
      types.ts
    dashboard/
      components/
      hooks/
      api/
      types.ts
  shared/
    components/
    hooks/
    utils/
    types/
```

**Ask the user**: "Here's the proposed directory structure based on your choices. Should I adjust anything?"

### G-PHASE 4: Draft Constitution

Write the constitution using:
- User's answers from the interview
- Framework best practices from research
- Proposed directory structure
- Strictness level preferences

**Key difference from Existing Codebase mode**: Instead of code examples from the project, use **framework-idiomatic examples** for the ALWAYS/NEVER/PREFER rules.

For example, for a Vue 3 + Clean Architecture project at maximum strictness:

```markdown
### 4.1 ALWAYS Do
- Always use `<script setup lang="ts">` for Vue components
- Always define props with `defineProps<{...}>()` (TypeScript generic syntax, not runtime)
- Always use `computed()` for derived state — never compute in template
- Always return `Either<Error, T>` from repository methods
- Always handle both Left and Right when consuming Either values

### 4.2 NEVER Do
- Never use `any` type — use `unknown` and type-narrow, or define a proper interface
- Never import from data layer in presentation layer (go through domain)
- Never mutate reactive state directly outside Pinia actions
- Never use `!important` in CSS without documented justification
- Never commit `.env` files or API keys
- Never use `// @ts-ignore` — fix the type instead

### 4.3 PREFER
- Prefer `composables` over mixins
- Prefer named exports over default exports
- Prefer `const` over `let`
- Prefer early returns over nested conditionals
- Prefer template refs over direct DOM manipulation
```

Mark all rules that come from best practices (not extracted from code) with a `[convention]` tag so the user knows these are chosen standards, not observed patterns:

```markdown
- [convention] Always use `<script setup lang="ts">` for Vue components
- [convention] Never use `any` type — use `unknown` and type-narrow
```

### G-PHASE 5: Include Scaffolding Guidance

Add a special section to the greenfield constitution:

```markdown
## 7. Scaffolding Guide (Greenfield)

This section applies while the project is being built. Once the codebase matures (20+ source files), run `/constitute` again to replace convention-based rules with evidence-based rules extracted from actual code.

### 7.1 First Files to Create
[Based on architecture, list the foundational files to create first]
[Example: "1. Domain entities/interfaces → 2. Data layer stubs → 3. First use case → 4. First UI component"]

### 7.2 Pattern Reference
[For each pattern the user chose, include a concrete starter example]
[These serve as "copy this pattern" templates for the first implementations]

### 7.3 When to Re-Constitute
Run `/constitute` again when:
- The project reaches 20+ source files
- A major architectural decision is made
- The team changes a core convention
- 3+ months have passed since last constitution
```

Now proceed to **PHASE 3** (User Review) below.

---

## EXISTING CODEBASE MODE (project with code)

### E-PHASE 1: Deep Codebase Analysis

Perform a thorough analysis of the entire codebase. This is the most important step — the constitution's quality depends on how well you understand the project.

#### 1.1: Architecture Mapping

**Source Root awareness**: If `CLAUDE.md` specifies a Source Root other than `.`, all source scanning paths are relative to that Source Root. Claude artifacts (`specs/`, `docs/`, `constitution.md`) remain at the workspace root, not inside the Source Root.

Scan the full source tree and identify:
- **Layer boundaries**: Where does data access live? Business logic? Presentation?
- **Dependency direction**: Which modules import from which? Are there circular dependencies?
- **Entry points**: Main application entry, route definitions, API endpoints
- **Shared code**: Utilities, helpers, shared types/interfaces
- **Configuration**: Environment variables, feature flags, build config

#### 1.2: Pattern Extraction

Read 10-15 representative source files across different parts of the codebase and extract:
- **Naming conventions**: camelCase vs snake_case, file naming, component naming
- **Import patterns**: Barrel exports, path aliases, relative vs absolute imports
- **Error handling style**: How are errors created, propagated, and displayed?
- **State management patterns**: How is state structured, updated, and consumed?
- **API patterns**: How are API calls structured? Request/response typing?
- **Testing patterns**: Test file location, naming, setup/teardown patterns
- **Component patterns**: How are UI components structured? Props, events, slots?

#### 1.3: Domain Knowledge

Identify domain-specific concepts:
- **Key entities**: What are the core business objects?
- **Workflows**: What are the main user/system workflows?
- **Business rules**: Any validation rules, calculations, or constraints visible in code?
- **External integrations**: Third-party services, APIs, SDKs
- **Authentication/Authorization**: How is auth handled?

#### 1.4: Existing Rules

Check for existing code quality rules:
- ESLint/Prettier configuration (read the actual config files)
- TypeScript strict settings
- Pre-commit hooks (`.husky/`, `.githooks/`)
- CI/CD checks (`.github/workflows/`)
- Existing `CONTRIBUTING.md` or `CODE_OF_CONDUCT.md`

### E-PHASE 2: Draft Constitution

Write `constitution.md` at the project root. Every rule must be backed by evidence from the codebase. Tag rules with their source:

- `[extracted]` — observed pattern from existing code (include file reference)
- `[enforced]` — from ESLint/TSConfig/CI rules already in place
- `[recommended]` — not currently in code but should be, based on near-misses or inconsistencies you found

Now proceed to **PHASE 3** (User Review) below.

---

## PHASE 3: User Review (both modes)

Write the constitution to `constitution.md` at project root using this structure:

```markdown
# Project Constitution — [Project Name]

Generated: [date]
Last updated: [date]
Mode: [Greenfield / Existing Codebase]

## 1. Project Identity

**Name**: [project name]
**Type**: [frontend/backend/fullstack/library]
**Domain**: [brief domain description]
**Stack**: [key technologies]

## 2. Architecture Rules (NON-NEGOTIABLE)

These rules MUST be followed in every code change. Violating these rules requires explicit user approval.

### 2.1 Layer Boundaries
[Describe the architectural layers and what belongs in each]
[Specify allowed dependency directions]
[List what is FORBIDDEN]

### 2.2 File Organization
[Where new files of each type should be created]
[Naming conventions for files, directories, components]
[File structure within components/modules]

### 2.3 Dependency Rules
[Internal dependency rules between modules/packages]
[Rules about external dependency additions]
[Import ordering and style]

## 3. Code Quality Standards

### 3.1 Type Safety
[Strictness level and specific rules]

### 3.2 Error Handling
[Which pattern, how to create/propagate/display errors]

### 3.3 Naming Conventions
[All naming rules]

### 3.4 Testing Requirements
[What must be tested, where tests live, patterns]

## 4. Patterns & Anti-Patterns

### 4.1 ALWAYS Do
[Required patterns — each tagged with source]

### 4.2 NEVER Do
[Forbidden patterns — each tagged with source]

### 4.3 PREFER
[Preferred approaches — each tagged with source]

## 5. Domain Rules

### 5.1 Key Entities
[Core domain objects and relationships]

### 5.2 Business Rules
[Critical business logic, validation, calculations]

### 5.3 External Contracts
[API contracts, third-party constraints, auth rules]

## 6. Workflow Rules

### 6.1 Minimal Changes
Every code change MUST impact as little code as possible.

### 6.2 Semantic Understanding
Before renaming or replacing any identifier, VERIFY:
1. What the identifier semantically means
2. All callers/consumers of the identifier
3. That the new name correctly represents the concept

### 6.3 Deprecation Handling
[How to handle deprecated fields/methods/APIs]

### 6.4 Documentation
[What must be documented, where, format]
```

If in greenfield mode, also include **Section 7: Scaffolding Guide** as described above.

**HARD GATE**: Present the draft to the user and explicitly ask for approval:

"I've generated the project constitution at `constitution.md`. Please review it, especially:
- **Section 2**: NON-NEGOTIABLE architecture rules
- **Section 4.2**: NEVER DO list
- **[Greenfield only] Section 7**: Scaffolding guide and directory structure

These will be enforced in all future tasks. Should I make any changes?"

## PHASE 4: Integrate (both modes)

After approval:
1. Update `.claude/memory/MEMORY.md` with a link to the constitution and key rules summary
2. Verify that `CLAUDE.md` references the constitution
3. Confirm that all agents can access the constitution path
4. **For existing projects**: Inform the user that the next step is to run `/onboard` to generate comprehensive codebase documentation that will serve as the knowledge base for all agents

## IMPORTANT RULES

1. **Greenfield: research, don't guess** — use WebSearch for framework best practices. Don't invent rules from thin air
2. **Existing: extract, don't invent** — every rule must be backed by evidence from the codebase
3. **Tag every rule** — `[convention]`/`[extracted]`/`[enforced]`/`[recommended]` so the user knows the source
4. **Be specific** — "follow best practices" is useless. "Use `Either<Error, T>` for all repository return types" is useful
5. **Prioritize** — put the most impactful rules first in each section
6. **Keep it scannable** — bullet points, not paragraphs
7. **Include examples** — for every ALWAYS/NEVER/PREFER rule, include a concrete code example
8. **Greenfield constitutions are temporary** — include the "When to Re-Constitute" section so the user knows to re-run once the codebase matures