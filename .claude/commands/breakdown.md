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

If you discover files that should have been in the spec but weren't, note them as additions.

### If greenfield (creating new files):
For every file listed in the spec's "Affected Areas" section:
1. **Check if the file exists** — if not, this is a "create" task
2. **Read the constitution's scaffolding guide** — verify the file will be in the correct directory per the architecture rules
3. **Identify the pattern reference** — find the closest pattern example from the constitution's Section 7.2
4. **Map required dependencies** — what types, interfaces, or modules must be created first?
5. **Check for infrastructure needs** — does this feature need new directories, config changes, or package installations?

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
| Both core + UI (tightly coupled change) | architect first, then frontend-engineer |
| Bug investigation with runtime symptoms | runtime-debugger |
| Performance-critical path or optimization task | performance-analyst |
| Auth, secrets, input validation, security hardening | security-reviewer |

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
- [ ] TypeScript compiles without errors
- [ ] ESLint passes on changed files

**Spec criteria addressed**: AC-[numbers]
```

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
```

## PHASE 5: User Approval

**HARD GATE**: The task breakdown MUST be approved before execution begins.

Present a summary:

"I've broken down the spec into **[N] tasks** at `specs/[NNN-feature]/tasks/`:

[List each task: number, title, agent, and dependency info — one line each]

Dependency chain: [simplified graph]

Riskiest tasks: [list high-risk tasks and why]

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