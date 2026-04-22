# AGENTS.md

Project instructions for Codex CLI.

## Project Overview

{{PROJECT_DESCRIPTION}}

- **Name**: {{PROJECT_NAME}}
- **Type**: {{PROJECT_TYPE}}
- **Framework**: {{FRAMEWORK}}
- **Language**: {{LANGUAGE}}
- **Build Tool**: {{BUILD_TOOL}}
- **Build Command**: `{{BUILD_COMMAND}}`
- **Type Check Command**: `{{TYPE_CHECK_COMMAND}}`
- **Lint Command**: `{{LINT_COMMAND}}`
- **Source Root**: {{SOURCE_ROOT}}

{{WRAPPER_MODE_SECTION}}

## Project Structure

{{PROJECT_STRUCTURE}}

## Development Commands

{{DEV_COMMANDS}}

## Architecture

{{ARCHITECTURE_DETAILS}}

## Workflow

### Spec-Driven Development Flow

```
$setup-wizard → $constitute → $onboard → $research → $specify → $plan → $breakdown → $execute-task → $review → $verify → $summarize → $finalize
   (once)         (once)       (once)    (optional)  (per feat)  (per feat) (per feat)   (per task)    (per feat) (per feat) (per feat)  (per feat)
```

- `$specify "feature"` — Create spec with acceptance criteria → `specs/NNN-name/spec.md`
- `$plan` — Technical plan from approved spec → `specs/NNN-name/plan.md`
- `$breakdown` — Atomic tasks with dependencies → `specs/NNN-name/tasks/`
- `$execute-task N` — Implement one task with assigned agent
- `$review` — Security + performance + test review → findings report
- `$verify` — Check acceptance criteria against spec
- `$finalize` — Squash WIP commits, generate docs, clean commit

Standalone (no spec required):
- `$fix "bug"` — Localized bug fix (1-5 files)
- `$refactor path "goal"` — Behavior-preserving restructuring (1-5 files)
- `$security [target]` — On-demand security review
- `$audit` — Adversarial whole-codebase quality review
- `$research "topic"` — Feasibility check before specifying

See `.agents/skills/*/SKILL.md` for detailed command instructions.

## Available Agents

{{AGENT_LIST}}

Agent selection is automatic in `$execute-task` based on the task's assigned agent.

## Enforced Quality Gates

### Hard Gates (block until approved)
- Spec approval → before `$plan` can run
- Plan approval → before `$breakdown` can run
- Task breakdown approval → before `$execute-task` can start
- Acceptance criteria → verified in `$verify`

### Verification (explicit, scope-aware — no runtime hooks)

Verification runs at task boundaries (end of `$execute-task`, `$fix`, `$refactor`, etc.), not after every file edit. Both Claude and Codex behave identically — no runtime hooks, no auto-execution after Edit/Write. Verification is **scope-aware**: the phase reads `PACKAGE_STACKS` (see `## Packages` above) to determine which type-check / lint / build commands apply to each file touched during the task.

**Scope-aware verification flow**:

1. Identify files touched during the task (git diff against the task-start checkpoint).
2. For each touched file, find its package via `PACKAGE_STACKS` path lookup (longest path prefix wins; e.g., `services/api/users.py` matches the `services/api` package).
3. Run that package's `type_check_command` and `lint_command` (stored in `.devforge/project-config.json`). Skip `"N/A"` commands silently (no-op; not a failure).
4. Build (`build_command`) typically runs once per task at the end, aggregated across touched packages when multiple are edited.
5. For files not inside any detected package (top-level scripts, misc files): fall back to the primary-stack commands (`TYPE_CHECK_COMMANDS[0]` / `LINT_COMMANDS[0]` / `BUILD_COMMANDS[0]`).
6. **Self-repair loop**: if type check or lint fails, attempt up to 3 auto-repair iterations before stopping and reporting. Code-review findings are reported to the user, not auto-repaired.

**Pre-flight check** (before each task): read `constitution.md` and `.devforge/memory.md` so the task starts with the right context. Applies to both runtimes equally.

Full specification in `$execute-task`.

## Key Rules

### Always
1. **Read before write** — always read files before modifying them
2. **Constitution is law** — `constitution.md` rules override everything except user instructions
3. **Minimal changes** — every change should impact as little code as possible
4. **Memory is persistent** — check `.devforge/memory.md` for lessons from past sessions
5. **Specs are contracts** — once approved, implementation must satisfy every acceptance criterion
6. **One task at a time** — execute tasks sequentially following the dependency graph
7. **Document new code** — all new functions/variables must have clear documentation
8. **Lint everything** — linting must pass on all changed files before task completion
9. **Handle both paths** — every fallible operation must handle success AND error cases
10. **Validate at boundaries** — validate external input (user input, API responses, env vars); trust internal code
11. **SOLID, DRY, KISS** — single responsibility, don't repeat logic 3+ times, keep it simple
12. **Search before building** — before writing anything generic/reusable, search the codebase for existing utilities, helpers, or components that already do it
13. **Session state** — after each `$execute-task`, overwrite `.devforge/session-state.md` with a fixed-size snapshot of current progress. At session start, read it first if it exists.
14. **Crash recovery** — `$execute-task` writes a WIP marker (`.devforge/wip.md`) before execution and creates git checkpoints at each phase. If interrupted, the next run detects it and offers resume/rollback/skip options.

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
  YYYY-MM-DD-topic-slug.md        # Research reports ($research) — exploratory, pre-spec

specs/
  001-feature-name/            # Numbered feature directories
    spec.md                    # $specify output
    plan.md                    # $plan output
    research.md                # $plan research (optional)
    data-model.md              # $plan data model (optional)
    contracts.md               # $plan API contracts (optional)
    tasks/                     # $breakdown output
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
- See `.devforge/storage-rules.md` for full conventions
- **Wrapper mode**: All artifacts (`specs/`, `docs/`, `constitution.md`) live in the wrapper root, NOT inside `{{SOURCE_ROOT}}`

## Session Continuity

At the start of each session, read `.devforge/session-state.md` if it exists. It contains a compact snapshot from the last completed task — current feature, progress, recent decisions, and recently modified files.

This file is:
- **Fixed-size** — always fully overwritten, never appended, max ~40 lines
- **A sliding window** — only tracks the last 3 tasks' modifications and last 3 decisions
- **Not a history log** — history lives in task completion notes (`specs/`) and `MEMORY.md`
- **Updated automatically** by `$execute-task` (Phase 7)

If context is compacted or a new session starts, session-state.md ensures the next `$execute-task` can bootstrap without re-discovering state.

### Crash Recovery

If a task execution is interrupted (power loss, terminal crash, network drop), the next `$execute-task` will detect the interrupted state via `.devforge/wip.md` and offer recovery options: resume from where it stopped, rollback and retry, rollback and skip, or keep changes for manual handling. The WIP marker includes a `Command` field identifying which command (`$execute-task`, `$fix`, or `$refactor`) was interrupted — if you run a different command, it will detect the mismatch and ask you to resolve the previous session first. Git checkpoint commits (`[WIP]` prefix) preserve partial work and are squashed into a clean feature commit by `$finalize` when the feature is approved.

## References

- [Constitution](constitution.md) — Project rules and patterns
- [Specs](specs/) — Feature specifications, plans, and tasks
- [Memory](.devforge/memory.md) — Persistent learnings
- [Project Config](.devforge/project-config.json) — Wizard answers
