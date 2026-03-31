# /breakdown — Task Breakdown from Specification

Takes an approved specification and breaks it into ordered, atomic tasks with dependencies and agent assignments.

## Usage
```
/breakdown [spec-file]
```

## Arguments
- `$ARGUMENTS` — Optional path to a spec file in `specs/`. If empty, use the most recently modified spec file in `specs/`.

## Prerequisites

1. A spec must exist in `specs/[feature-name]/spec.md` with **Status: Approved**
2. A plan must exist in `specs/[feature-name]/plan.md` with **Status: Approved**
3. If the spec is not approved: "Run `/specify` first, then get it approved."
4. If the plan is not approved: "Run `/plan` first, then get it approved."

## PHASE 1: Load Context

Read these files in order:
1. The feature's `spec.md` (from `$ARGUMENTS` or most recent feature directory in `specs/`)
2. The feature's `plan.md` — technical decisions and file impact
3. The feature's supporting docs if they exist: `research.md`, `data-model.md`, `contracts.md`
4. `constitution.md` — architecture rules and constraints
   - **Guard**: If `constitution.md` contains `_Run /constitute to populate_`, stop: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/breakdown`."
5. `.claude/memory/MEMORY.md` — past lessons
6. `CLAUDE.md` — project structure and available agents

Verify both spec AND plan are approved. If not, stop and inform the user.

## PHASE 2: Deep File Analysis

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, all source file paths are relative to the workspace root (e.g., `SOURCE_ROOT/src/components/...`). Claude artifact paths (`specs/`, `docs/`) remain at the workspace root.

### If existing codebase:
For every file listed in the spec's "Affected Areas" section:
1. **Read the file** completely
2. **Map its dependencies**: What does it import? What imports it?
3. **Identify the change points**: Exactly which lines/functions/blocks need to change
4. **Estimate scope**: How many lines will change? Is it a simple rename or a logic change?
5. **Check for cascading effects**: Will changing this file require changes in other files not listed in the spec?
6. **Identify verifiable semantics**: What exports, interfaces, functions, or call patterns must exist after the change? What must be imported from where? These become the basis for cross-task contracts.

If you discover files that should have been in the spec but weren't, note them as additions.

### If greenfield (creating new files):
For every file listed in the spec's "Affected Areas" section:
1. **Check if the file exists** — if not, this is a "create" task
2. **Read the constitution's scaffolding guide** — verify the file will be in the correct directory per the architecture rules
3. **Identify the pattern reference** — find the closest pattern example from the constitution's Section 7.2
4. **Map required dependencies** — what types, interfaces, or modules must be created first?
5. **Check for infrastructure needs** — does this feature need new directories, config changes, or package installations?
6. **Identify verifiable semantics** — what exports, interfaces, or functions must exist after each creation step? These become cross-task contracts.

**Greenfield task ordering is different** — instead of "types first, then core, then UI", it's:
1. **Infrastructure** — create directories, install packages, add config
2. **Types/interfaces** — define the data shapes
3. **Core logic** — domain/business logic, use cases, repositories
4. **Presentation** — UI components, views, routes
5. **Integration** — wire everything together (DI, routing, store registration)

## PHASE 3: Generate Task Breakdown

Create atomic tasks following these rules:

### Task Granularity Rules
- **One task = one logical change** that can be verified independently
- A task should touch **1-3 files** maximum (exception: rename/replace across many files)
- Each task must have a clear **done condition**
- Tasks should take **5-30 minutes** to implement (not hours)
- If a task would take longer, break it into sub-tasks

### Task Ordering Rules
- **Types/interfaces first** — define the data shapes before using them
- **Core/domain before presentation** — business logic before UI
- **Data layer before domain** — repositories before use cases
- **Independent tasks before dependent ones**
- **Riskiest changes first** — catch problems early

### Agent Assignment Rules
Assign each task to the most appropriate agent based on the files it touches:

| Files in... | Agent |
|-------------|-------|
| Core/domain/data layers, business logic, API, types | architect |
| UI components, styles, routes, composables, stores | frontend-engineer |
| Mobile screens, navigation, native modules, platform-specific code, app lifecycle | mobile-engineer |
| Both core + UI (tightly coupled change) | architect first, then frontend-engineer |
| Bug investigation with runtime symptoms | runtime-debugger |
| Performance-critical path or optimization task | performance-analyst |
| Auth, secrets, input validation, security hardening | security-reviewer |
| Database schemas, migrations, queries, seed data | db-engineer |
| API contract design, OpenAPI specs, endpoint structure | api-designer |
| CI/CD, Docker, deployment config, infrastructure | devops-engineer |
| Data migration scripts, backward compatibility layers | migration-engineer |
| Accessibility, design system compliance, UI audit | design-auditor |

**Note**: `performance-analyst` and `security-reviewer` also run automatically during `/verify` on all changed files. Assign them to individual tasks only when the task itself is primarily about performance or security work.

### Task Format

For each task, generate:

```markdown
### Task [N]: [Short imperative title]

**Agent**: [agent name]
**Files**: [list of files to change]
**Depends on**: [task numbers this task requires to be done first, or "None"]
**Blocks**: [task numbers that can't start until this is done]

**Description**:
[Detailed description of what to change and why]

**Change details**:
- In `path/to/file.ts`:
  - [specific change description with line numbers if possible]
  - [another change in same file]
- In `path/to/other.ts`:
  - [specific change]

**Done when**:
- [ ] [Testable condition]
- [ ] [Another testable condition]
- [ ] Type checker passes on changed files
- [ ] Linter passes on changed files

**Spec criteria addressed**: AC-[numbers]
```

### Contract Generation Rules

For each task, generate a `## Contracts` section with `### Expects` and `### Produces` subsections:

- **Expects (preconditions)**: What must be true in the codebase before this task can execute correctly. For the first task in a chain, these describe existing codebase state. For downstream tasks, these should match an upstream task's "Produces".
- **Produces (postconditions)**: What must be true in the codebase after this task completes. These are independently verified by `/execute-task` via grep/read.

**Rules**:
- 2-5 items per section. Keep them concrete and grep-verifiable.
- Reference **semantic identifiers** (function names, export names, interface names, field names) — never line numbers. Line numbers shift as earlier tasks modify files.
- Examples of good contracts:
  - `src/types/Cart.ts` exports interface `CartTotals` with fields `subtotal: number`, `total: number`
  - `CartBLoC.ts` has a public getter named `cartTotals` returning `CartTotals`
  - `CartSummary.vue` imports `CartBLoC` from `src/domain/cart/`
- Contracts must reference **literal strings that appear in source code** — export names, function names, interface names, field names, class names. Avoid referencing abstract concepts (e.g., "has a getter") — reference the literal declaration pattern instead (e.g., "`get cartTotals()`" appears in `CartBLoC.ts`).
- Examples of bad contracts:
  - "Cart totals work correctly" (not verifiable)
  - "Line 45 of CartBLoC.ts returns the right value" (line numbers shift)
  - "Performance is acceptable" (not grep-verifiable)

### Review Checkpoint Placement

For each task, set `**Review checkpoint**: Yes` or `No` in the header. Auto-place checkpoints at:

1. **Convergence points** — task depends on 2+ other tasks
2. **Layer boundary crossings** — first presentation-layer task after domain/data-layer tasks
3. **High-risk tasks** — any task rated High in the risk assessment

All other tasks get `**Review checkpoint**: No`. Users can add or remove checkpoints during the approval phase.

### Contract Consistency Check

After generating all tasks, verify contract chain integrity:
- Every "Produces" item must be consumed by at least one downstream task's "Expects" OR directly map to a spec acceptance criterion
- Every "Expects" item must either already be true in the current codebase OR be produced by an upstream task's "Produces"
- If any contract is orphaned (Produces not consumed) or unsatisfied (Expects with no source), flag it in the breakdown summary

## PHASE 4: Save the Breakdown

Create the `tasks/` directory inside the feature's spec directory and save each task as a separate numbered file.

### Output Structure

Create `specs/NNN-feature/tasks/` directory. For each task, create a separate file:

```
specs/NNN-feature/tasks/
  001-short-title.md
  002-short-title.md
  003-short-title.md
```

Each task file follows the format defined in `.claude/templates/storage-rules.md`.

Also create a `specs/NNN-feature/tasks/README.md` index file:

```markdown
# Tasks: [Feature Name]

**Spec**: [path to spec.md]
**Plan**: [path to plan.md]
**Generated**: [date and time]
**Total tasks**: [count]

## Dependency Graph

```
001 (types) ──→ 002 (core) ──→ 004 (UI)
             ──→ 003 (core) ──→ 004 (UI)
                             ──→ 005 (cleanup)
```

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | [title] | [agent] | None | Pending |
| 002 | [title] | [agent] | 001 | Pending |
| ... | ... | ... | ... | ... |

## Additions to Spec

[Files or changes discovered that weren't in the original spec]

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | Low/Med/High | [why] |

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| [NNN] | [convergence / layer crossing / high risk] | [what to verify before proceeding] |
```

## PHASE 5: User Approval

**HARD GATE**: The task breakdown MUST be approved before execution begins.

Present a summary:

"I've broken down the spec into **[N] tasks** at `specs/[NNN-feature]/tasks/`:

[List each task: number, title, agent, and dependency info — one line each]

Dependency chain: [simplified graph]

Riskiest tasks: [list high-risk tasks and why]

Review checkpoints: [count] (before tasks [list])
Contract orphans: [any Produces items not consumed by downstream Expects, or 'none']

Please review the task files. You can:
1. Approve as-is → run `/execute-task 001` to start
2. Request changes → I'll update the tasks
3. Reject → I'll revisit the plan

Tasks should be executed in order (dependencies are marked)."

## IMPORTANT RULES

1. **Atomic tasks** — each task must be independently verifiable. Never bundle unrelated changes
2. **Explicit dependencies** — if task B uses types defined in task A, mark it. Missing dependencies cause bugs
3. **Agent per task** — assign ONE agent per task. If a task needs both, split it
4. **Include verification in every task** — every task's "Done when" must include tsc + lint checks
5. **Reference spec criteria** — every task must map to at least one acceptance criterion (AC-N)
6. **All ACs covered** — every acceptance criterion from the spec must be addressed by at least one task
7. **Don't over-split** — a simple find-and-replace across 5 files is ONE task, not five tasks
8. **Contract chain integrity** — every task's "Produces" must be consumed by a downstream "Expects" or map to a spec AC. Every "Expects" must trace to an upstream "Produces" or existing codebase state. Broken chains indicate missing tasks or wrong dependencies
9. **Contracts use semantic identifiers** — reference function names, export names, interface names, field names. Never line numbers (they shift as earlier tasks modify files)