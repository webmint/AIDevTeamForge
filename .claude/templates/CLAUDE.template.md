# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**Name**: {{PROJECT_NAME}}
**Type**: {{PROJECT_TYPE}}
**Framework**: {{FRAMEWORK}}
**Language**: {{LANGUAGE}}
**Build Tool**: {{BUILD_TOOL}}
**Build Command**: {{BUILD_COMMAND}}
**Type Check Command**: {{TYPE_CHECK_COMMAND}}
**Lint Command**: {{LINT_COMMAND}}
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

Flow: `/setup-wizard` → `/constitute` → `/onboard` (once each) → `/research` (optional) → `/specify` → `/plan` → `/breakdown` → `/execute-task` (per task) → `/review` → `/verify` → `/summarize` → `/finalize` (per feature). Standalone: `/fix` (small bugs, 1–5 files), `/refactor` (behavior-preserving, 1–5 files), `/security`, `/audit` (periodic; the audit gate makes it due), `/review-pr` (a pull request without a spec), `/refresh-docs`, `/report-bug`. Autonomous mode: `/conduct` drives the flow (see "Delivery Mode"). Each command is described in its own file under `.claude/commands/`.

## Available Agents

{{AGENT_LIST}}

**Agent Selection** is automatic in `/execute-task` based on the task's assigned agent. You can also launch agents directly using the Task tool.

## Enforced Quality Gates

### Hard Gates (block until approved)
- Spec approval → before `/plan` can run
- Plan approval → before `/breakdown` can run
- Task breakdown approval → before `/execute-task` can start
- Acceptance criteria → verified in `/verify`

### Independent Gates (run before each HARD GATE)
- An artifact the next command consumes is reviewed by someone other than its author: a fresh agent, on a different model where possible, works adversarially to `.claude/checklists/<gate>.md` (`.claude/commands/_independent-gate.md`). spec-gate runs in `/specify`, plan-gate (architect, security and qa lenses) in `/plan`, breakdown-gate in `/breakdown`; the findings are shown at the HARD GATE.
- **Test lens**: the per-task code review gets `task-review.md` and `test-lens.md`, the `/review` qa assessment `test-lens.md`: would each new or changed test fail if the feature were broken?
- **Learning**: `/finalize` records every defect of the feature in `escapes.md`, with the gate that should have caught it, and adds one generic check per escaped defect to that gate's checklist.
- **Usefulness**: a gate that catches nothing for 3 consecutive features may be lightened (fewer items, a cheaper model) or switched off on its checklist's `**Gate**:` line; a gate whose escapes keep recurring is strengthened. The `quality:` lines in `escapes.md` are the evidence.

### Delivery Mode
- **Interactive** (default): every command stops at its gates and questions.
- **Autonomous** (opt-in, `DELIVERY_MODE: autonomous`): `/conduct` runs the commands as subagents; their interactive points follow `.claude/commands/_autonomous-mode.md` (self-approval after a clean independent gate, decisions recorded, STOP conditions). The push guard (`.claude/hooks/forge/push-guard.py`) then allows only pushes of `PUSH_BRANCH_PREFIXES` branches to `PUSH_REMOTE`, and denies force pushes, tags, remote deletions, merges and settings writes. A command the user runs by hand stays interactive.

### Automated Guards (run automatically)
- **PostToolUse hook**: Type Check Command runs automatically after every file Edit/Write (Lint Command runs during explicit verification phases, not per-edit — this is intentional to avoid noise)
- **Pre-flight check**: Constitution and memory review before each task
- **Post-execution**: type check + lint + build on all changed files after each task

### Structural Checks
- The project binding `.claude/quality-profile.json` (search scopes, ratchets, hubs, audit gate; empty keys run in their manual form) feeds `/review`'s Structural Check: a grown ratchet or a third copy the plan did not decide is Critical.

## Key Rules

### Always
1. **Read before write** — always read files before modifying them
2. **Constitution is law** — `constitution.md` rules override everything except user instructions
3. **Minimal changes, except consolidation** — every change should impact as little code as possible, and a copy is never the minimal change. When a task touches or adds a copy of logic that already exists elsewhere, it reuses or extracts the shared definition when that stays within the task's files and their direct consumers; otherwise it reports the copy so the plan gets a consolidation task
4. **Memory is persistent** — check `.claude/memory/MEMORY.md` for lessons from past sessions
5. **Specs are contracts** — once approved, implementation must satisfy every acceptance criterion
6. **One task at a time** — execute tasks sequentially following the dependency graph
7. **Document new code** — all new functions/variables must have clear documentation
8. **Lint everything** — linting must pass on all changed files before task completion
9. **Handle both paths** — every fallible operation must handle success AND error cases
10. **Validate at boundaries** — validate external input (user input, API responses, env vars); trust internal code
11. **SOLID, DRY, KISS** — single responsibility, no copied logic (a second copy is extracted, see Always 3), keep it simple
12. **Search before building** — before writing anything generic/reusable, search the codebase for existing utilities, helpers, or components that already do it
13. **Session state** — after each `/execute-task`, overwrite `.claude/session-state.md` with a fixed-size snapshot of current progress. At session start, read it first if it exists.
14. **Crash recovery** — `/execute-task` writes a WIP marker before execution and creates git checkpoints at each phase. If interrupted, the next run detects it and offers resume/rollback/skip options.
15. **Check output stays out of context** — run type checks, lint, builds and tests through `scripts/forge/gate.sh <name> -- <command>`. It prints `<name>=<exit>` plus a few summary or error lines and writes the full output to `.claude/.gate-logs/<name>.log`; read a log only with a targeted grep, to diagnose a failure
16. **Resume agents, don't restart them** — when an agent you launched ends on an API error (timeout, server error) before it reports, first resume it with `SendMessage`: "resume where you stopped; check `git status` and what you already wrote first". Launch a fresh agent only when the resume fails. Before trusting either, check the tree for what actually landed.
17. **Reading budget** — a survey of more than ~5 files or ~30k tokens goes to Explore subagents, in parallel, each with a precise question and a `file:line` answer format. Read directly only what you quote or what a contract relies on. A generated directory is never read as the definition of what it generates.

### Never
1. **Never swallow errors** — empty catch blocks are forbidden; handle, re-throw, or log with reason
2. **Never commit secrets** — no API keys, tokens, or credentials in code
3. **Never commit debug artifacts** — no console.log, debugger, print() left behind
4. **Never leave bare TODOs** — every TODO must have context and a reference
5. **Never modify outside scope** — do not "fix" unrelated code you happen to see. A copy of the logic your task touches is not unrelated: it falls under the consolidation exception (Always 3)
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

Features live in `specs/NNN-kebab-name/` (`spec.md`, `plan.md`, optional `research.md`, `data-model.md`, `contracts.md`, `tasks/` with `README.md` and `NNN-short-title.md`, `gates/`, `escapes.md`); research reports in `research/YYYY-MM-DD-topic-slug.md`; docs by topic in `docs/` (`overview.md`, `architecture.md`, `features/`, `api/`, `guides/`). Full conventions: `.claude/storage-rules.md`. **Wrapper mode**: all artifacts (`specs/`, `docs/`, `constitution.md`) live in the wrapper root, NOT inside `{{SOURCE_ROOT}}`.

## Session Continuity

At the start of each session, read `.claude/session-state.md` if it exists. It contains a compact snapshot from the last completed task — current feature, progress, recent decisions, and recently modified files.

This file is:
- **Fixed-size** — always fully overwritten, never appended, max ~40 lines
- **A sliding window** — only tracks the last 3 tasks' modifications and last 3 decisions
- **Not a history log** — history lives in task completion notes (`specs/`) and `MEMORY.md`
- **Updated automatically** by `/execute-task` (Phase 7)

If you run `/clear` or context is compacted, session-state.md ensures the next `/execute-task` can bootstrap without re-discovering state.

### Context Guard

The `.claude/hooks/forge/context-guard.py` hook (PostToolUse) measures the main-session context. At 75 % of the window it asks you to wind down (finish the current task, start nothing new); at 85 % it asks you to stop at the nearest safe point and have the user run `/compact`. The window defaults to 200k tokens; set `FORGE_CONTEXT_WINDOW` (or absolute `FORGE_CONTEXT_WARN` / `FORGE_CONTEXT_STOP`) in the `env` block of `.claude/settings.json` to change it. `python3 .claude/hooks/forge/context-guard.py --report` prints the current size. Subagents ignore its messages.

### Crash Recovery

If a task execution is interrupted (power loss, terminal crash, network drop), the next `/execute-task` will detect the interrupted state via `.claude/wip.md` and offer recovery options: resume from where it stopped, rollback and retry, rollback and skip, or keep changes for manual handling. The WIP marker includes a `Command` field identifying which command (`/execute-task`, `/fix`, or `/refactor`) was interrupted — if you run a different command, it will detect the mismatch and ask you to resolve the previous session first. Git checkpoint commits (`[WIP]` prefix) preserve partial work and are squashed into a clean feature commit by `/finalize` when the feature is approved.

## References

- [Constitution](constitution.md) — Project rules and patterns
- [Specs](specs/) — Feature specifications, plans, and tasks
- [Memory](/.claude/memory/MEMORY.md) — Persistent learnings