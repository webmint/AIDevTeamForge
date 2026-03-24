# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**Name**: {{PROJECT_NAME}}
**Type**: {{PROJECT_TYPE}}
**Framework**: {{FRAMEWORK}}
**Language**: {{LANGUAGE}}
**Build Tool**: {{BUILD_TOOL}}
**Build Command**: {{BUILD_COMMAND}}
**Source Root**: {{SOURCE_ROOT}}

{{WRAPPER_MODE_SECTION}}

## Project Structure

{{PROJECT_STRUCTURE}}

## Development Commands

{{DEV_COMMANDS}}

## Architecture

**Pattern**: {{ARCHITECTURE}}
**Error Handling**: {{ERROR_HANDLING}}
**API Layer**: {{API_LAYER}}
**State Management**: {{STATE_MANAGEMENT}}
**Styling**: {{STYLING}}
**Monorepo**: {{MONOREPO_TOOL}}

## Workflow Commands

### Spec-Driven Development Flow

```
/setup-wizard → /constitute → /onboard → /research → /clarify → /specify → /plan → /breakdown → /execute-task → /verify
   (once)         (once)       (once)    (optional)  (optional)  (per feature)         (auto)      (per task)     (per task)
```

### `/research "topic or idea"` (optional)
Quick feasibility check for vague ideas. Investigates the codebase for related patterns, optionally researches external approaches (signal-based), and displays the full report in the console. You're then asked whether to save — if yes, saves to `research/DD-MM-YY-[topic-slug].md`. Does NOT create specs or modify code. Use before `/specify` when you're unsure whether an idea is viable or how it fits.

### `/clarify "feature description"` (optional)
Scans requirements against 9 ambiguity categories, asks up to 5 multiple-choice questions. Saves decisions to `specs/[feature]/clarifications.md`. Use when requirements are vague.

### `/specify "feature description"`
Creates a structured specification with acceptance criteria. Analyzes affected code, saves spec to `specs/[feature]/spec.md`. **Requires approval before proceeding.** Auto-creates a `spec/NNN-short-desc` branch when on the default branch.

### `/plan [spec-file]`
Takes an approved spec and produces a technical plan: architecture decisions, data model, API contracts, research. Saves to `specs/[feature]/plan.md`. **Requires approval before breakdown.**

### `/breakdown [spec-file]`
Takes an approved plan and generates ordered, atomic tasks with dependencies and agent assignments. Saves to `specs/[feature]/tasks/`. **Requires approval before execution.**

### `/execute-task [number]`
Executes a single task from the breakdown using the assigned specialized agent. Follows enforced workflow:
1. Pre-flight check (constitution, memory, docs, file state)
2. Agent execution with scope constraints
3. Post-execution verification (tsc, lint, build, done conditions)
4. Documentation update (tech-writer agent)
5. Memory update

### `/verify [spec-file]`
Verifies all completed tasks against the spec's acceptance criteria. Performs code review against constitution rules. Updates memory with lessons learned.

### `/constitute`
One-time deep codebase analysis (or interview for greenfield projects) that generates `constitution.md` — non-negotiable rules, architecture decisions, patterns.

### `/onboard`
One-time deep codebase scan for existing projects. Uses the tech-writer agent to generate comprehensive documentation in `docs/` — the knowledge base for all agents. Run once after `/constitute`.

### `/fix "bug description"`
Lightweight bug-fix workflow for small, localized bugs (1-5 files). Bypasses the full spec→plan→breakdown pipeline. Phases:
1. Diagnosis (runtime-debugger agent for runtime errors, manual tracing for logic bugs)
2. User confirms root cause (hard gate)
3. Apply minimal fix with WIP checkpoint
4. Verification (tsc, lint, build, self-repair loop)
5. Code review (code-reviewer agent)
6. Test assessment (qa-engineer agent)
7. Clean commit + memory update

If the bug grows beyond 5 files, recommends escalating to `/specify`.

### `/refactor path/to/file.ts "goal"`
Focused code refactoring workflow for behavior-preserving restructuring (1-5 files). Supports IDE-injected context (active file/selection from WebStorm) or manual file path. Phases:
1. Analysis (detect refactoring opportunities against constitution rules — long functions, SOLID/DRY/KISS violations, type safety, naming, dead code, pattern mismatches)
2. User approves proposal with specific items (hard gate, partial approval supported)
3. Apply refactoring with auto-selected agent (architect, frontend-engineer, or backend-engineer based on file layer)
4. Verification (tsc, lint, build, tests, self-repair loop)
5. Code review (code-reviewer agent)
6. Test assessment (qa-engineer agent — tests must pass unchanged since refactoring is behavior-preserving)
7. Clean commit + memory update

If the refactoring grows beyond 5 files, recommends escalating to `/specify`.

### Additional Commands

- `/setup-wizard` — Re-run initial project setup (regenerates config files)

## Available Agents

{{AGENT_LIST}}

**Agent Selection** is automatic in `/execute-task` based on the task's assigned agent. You can also launch agents directly using the Task tool.

## Enforced Quality Gates

### Hard Gates (block until approved)
- Spec approval → before `/plan` can run
- Plan approval → before `/breakdown` can run
- Task breakdown approval → before `/execute-task` can start
- Acceptance criteria → verified in `/verify`

### Automated Guards (run automatically)
- **PostToolUse hook**: Type checking after every file Edit/Write
- **Pre-flight check**: Constitution and memory review before each task
- **Post-execution**: tsc + lint + build on all changed files after each task

## Key Rules

### Always
1. **Read before write** — always read files before modifying them
2. **Constitution is law** — `constitution.md` rules override everything except user instructions
3. **Minimal changes** — every change should impact as little code as possible
4. **Memory is persistent** — check `.claude/memory/MEMORY.md` for lessons from past sessions
5. **Specs are contracts** — once approved, implementation must satisfy every acceptance criterion
6. **One task at a time** — execute tasks sequentially following the dependency graph
7. **Document new code** — all new functions/variables must have clear documentation
8. **Lint everything** — linting must pass on all changed files before task completion
9. **Handle both paths** — every fallible operation must handle success AND error cases
10. **Validate at boundaries** — validate external input (user input, API responses, env vars); trust internal code
11. **SOLID, DRY, KISS** — single responsibility, don't repeat logic 3+ times, keep it simple
12. **Search before building** — before writing anything generic/reusable, search the codebase for existing utilities, helpers, or components that already do it
13. **Session state** — after each `/execute-task`, overwrite `.claude/session-state.md` with a fixed-size snapshot of current progress. At session start, read it first if it exists.
14. **Crash recovery** — `/execute-task` writes a WIP marker before execution and creates git checkpoints at each phase. If interrupted, the next run detects it and offers resume/rollback/skip options.

### Never
1. **Never swallow errors** — empty catch blocks are forbidden; handle, re-throw, or log with reason
2. **Never commit secrets** — no API keys, tokens, or credentials in code
3. **Never commit debug artifacts** — no console.log, debugger, print() left behind
4. **Never leave bare TODOs** — every TODO must have context and a reference
5. **Never modify outside scope** — do not "fix" unrelated code you happen to see
6. **Never guess** — if unsure how code works, read it; if unsure what user wants, ask

## Commit Convention

### Format
- **Final commits**: Conventional Commits — `type(scope): description`
  - `feat(scope):` — new feature
  - `fix(scope):` — bug fix
  - `refactor(scope):` — behavior-preserving restructuring
  - `docs:` — documentation only
- **WIP commits**: `[WIP] Type: description — phase detail` (squashed into final commit)
- **Checkpoint commits**: `[checkpoint] Pre-type: description` (squashed into final commit)

### Attribution
{{COMMIT_ATTRIBUTION}}

### Rules
- Keep commit title under 72 characters
- No period at end of title
- Body is optional; use for non-obvious "why"
- One logical change per final commit (WIP commits get squashed)

## Artifact Storage

```
research/
  DD-MM-YY-topic-slug.md        # Research reports (/research) — exploratory, pre-spec

specs/
  001-feature-name/            # Numbered feature directories
    spec.md                    # /specify output
    clarifications.md          # /clarify output (optional)
    plan.md                    # /plan output
    research.md                # /plan research (optional)
    data-model.md              # /plan data model (optional)
    contracts.md               # /plan API contracts (optional)
    tasks/                     # /breakdown output
      README.md                # Task index with dependency graph
      001-define-types.md      # Individual task files
      002-create-repo.md
      003-build-component.md

docs/
  overview.md                  # Project overview
  architecture.md              # Architecture and patterns
  features/                    # Feature docs (one file per area)
  api/                         # API docs (one file per resource)
  guides/                      # How-to guides
```

- Feature dirs: `NNN-kebab-name`, sequential numbering (001, 002, ...)
- Task files: `NNN-short-title.md`, sequential within feature
- Everything for a feature lives in one directory
- Docs are organized by topic (not by task/date) in `docs/`
- See `.claude/templates/storage-rules.md` for full conventions
- **Wrapper mode**: All artifacts (`specs/`, `docs/`, `constitution.md`) live in the wrapper root, NOT inside `{{SOURCE_ROOT}}`

## Session Continuity

At the start of each session, read `.claude/session-state.md` if it exists. It contains a compact snapshot from the last completed task — current feature, progress, recent decisions, and recently modified files.

This file is:
- **Fixed-size** — always fully overwritten, never appended, max ~40 lines
- **A sliding window** — only tracks the last 3 tasks' modifications and last 3 decisions
- **Not a history log** — history lives in task completion notes (`specs/`) and `MEMORY.md`
- **Updated automatically** by `/execute-task` (Phase 7.5)

If you run `/clear` or context is compacted, session-state.md ensures the next `/execute-task` can bootstrap without re-discovering state.

### Crash Recovery

If a task execution is interrupted (power loss, terminal crash, network drop), the next `/execute-task` will detect the interrupted state via `.claude/wip.md` and offer recovery options: resume from where it stopped, rollback and retry, rollback and skip, or keep changes for manual handling. Git checkpoint commits (`[WIP]` prefix) preserve partial work and get squashed into a clean commit on successful completion.

## References

- [Constitution](constitution.md) — Project rules and patterns
- [Specs](specs/) — Feature specifications, plans, and tasks
- [Memory](/.claude/memory/MEMORY.md) — Persistent learnings