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

### Spec-Driven Development Flow

```
/setup-wizard → /constitute → /onboard → /research → /specify → /plan → /breakdown → /execute-task → /review → /verify → /summarize → /finalize
   (once)         (once)       (once)    (optional)  (per feat)  (per feat) (per feat)   (per task)    (per feat) (per feat) (per feat)  (per feat)
```

### `/research "topic or idea"` (optional)
Quick feasibility check for vague ideas. Investigates the codebase for related patterns, optionally researches external approaches (signal-based), and displays the full report in the console. You're then asked whether to save — if yes, saves to `research/YYYY-MM-DD-[topic-slug].md`. Does NOT create specs or modify code. Use before `/specify` when you're unsure whether an idea is viable or how it fits.

### `/specify "feature description"`
Creates a structured specification with acceptance criteria. Asks clarifying questions as needed (no artificial limit — the AI judges how many based on input clarity). Analyzes affected code, saves spec to `specs/[feature]/spec.md`. **Requires approval before proceeding.** Auto-creates a `spec/NNN-short-desc` branch when on the default branch.

### `/plan [spec-file]`
Takes an approved spec and produces a technical plan: architecture decisions, data model, API contracts, research. Saves to `specs/[feature]/plan.md`. **Requires approval before breakdown.**

### `/breakdown [spec-file]`
Takes an approved plan and generates ordered, atomic tasks with dependencies, agent assignments and waves (2–4 consecutive tasks run together). Saves to `specs/[feature]/tasks/`. **Requires approval before execution.**

### `/execute-task [number]`
Executes a single task from the breakdown using the assigned specialized agent. Follows enforced workflow:
1. Pre-flight check (constitution, memory, file state, contract preconditions)
2. Agent execution with scope constraints (agent writes code + inline docs)
3. Post-execution verification (tsc, lint, build, done conditions, self-repair)
4. Code review (code-reviewer agent — findings reported to user, critical issues block)
5. Memory update
Also takes a range (`1-3`), a wave (`W2`) or `all`. In a batch, the full build and the full test suite run once after the last task (batch gate). WIP commits accumulate across tasks and are squashed by `/finalize` when the feature is approved.

### `/review [spec-file]`
Launches specialist review agents (security, performance, test assessment) on completed feature code. Produces a structured review report saved to `specs/[feature]/review.md` for `/verify` to incorporate into its verdict. Does not render a verdict — findings only.

### `/verify [spec-file]`
Verifies all completed tasks against the spec's acceptance criteria. When AC verification is enabled (`AC_VERIFICATION` in project-config.json), launches the **ac-verifier** agent to test acceptance criteria against the running app via Chrome DevTools MCP and/or API calls — falls back to code reading when MCP is not available. Incorporates `/review` findings if available (warns if missing). Performs cross-task integration check (not full code review — that was done per-task). Updates memory with lessons learned.

### `/summarize [spec-file]`
Generates a concise, PR-ready summary of a completed feature. Reads spec, plan, tasks, and git history. Saves to `specs/[feature]/summary.md`. Run after `/verify` approves, before `/finalize`.

### `/finalize [spec-file]`
Generates feature-level documentation via tech-writer, then squashes all WIP commits into a single clean feature commit. Gate-checked: spec must be Complete (set by `/verify`). The last step before creating a PR.

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

### `/security [file|dir|--full]`
On-demand security review. Targets a specific file (with optional line range), directory, uncommitted changes (default), or the full codebase (`--full`). Launches the security-reviewer agent with constitution and memory context. Reports findings by severity (Critical/High/Medium/Info) with CWE identifiers and remediation suggestions. Read-only — does not modify code. Full codebase mode uses module-based subagents for large projects.

### `/audit [--full | --uncommitted | path]`
Standalone adversarial whole-codebase audit for periodic "second opinion" quality reviews. Launches code-reviewer, architect, qa-engineer, and security-reviewer in **adversarial mode** with a structured Mislogic Hunt Checklist (naming-vs-behavior mismatches, lying comments, off-by-one errors, dead branches, cross-file contradictions, contradictory configs). Reads up to 5 recent `specs/*/review.md` files to track recurring/unresolved issues across features. Anti-hallucination grounding: every finding must include a verbatim Evidence quote from the actual code; Phase 4 validation re-reads cited files and discards ungrounded findings. Writes dated reports to `audits/YYYY-MM-DD-audit.md` and prints inline summary. Read-only, not auto-committed, **NOT part of any workflow chain** — invoke manually after several specs ship.

### `/conduct ["feature" | specs/NNN-feature]` (autonomous mode only)
Opt-in autonomous delivery: with `DELIVERY_MODE: autonomous` in `.claude/project-config.json`, the main session drives the whole spec cycle, one subagent per phase, and the runners decide where the commands would ask (`.claude/commands/_autonomous-mode.md`). A HARD GATE self-approves only after its independent gate ran with no open Critical; `DELIVERY_GATES` keeps chosen points interactive. The user is asked only at STOP conditions; only the user merges.

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

```
research/
  YYYY-MM-DD-topic-slug.md        # Research reports (/research) — exploratory, pre-spec

specs/
  001-feature-name/            # Numbered feature directories
    spec.md                    # /specify output
    plan.md                    # /plan output
    research.md                # /plan research (optional)
    data-model.md              # /plan data model (optional)
    contracts.md               # /plan API contracts (optional)
    tasks/                     # /breakdown output
      README.md                # Task index with dependency graph
      001-define-types.md      # Individual task files
      002-create-repo.md
      003-build-component.md
    gates/                     # Independent gate reports (/specify, /plan, /breakdown)
    escapes.md                 # Escape analysis (/finalize)

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
- See `.claude/storage-rules.md` for full conventions
- **Wrapper mode**: All artifacts (`specs/`, `docs/`, `constitution.md`) live in the wrapper root, NOT inside `{{SOURCE_ROOT}}`

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