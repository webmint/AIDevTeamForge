# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

{{PROJECT_DESCRIPTION}}

- **Name**: {{PROJECT_NAME}}
- **Type**: {{PROJECT_TYPE}}
- **Frameworks**: {{FRAMEWORK}}
- **Languages**: {{LANGUAGE}}
- **Build Tool**: {{BUILD_TOOL}}
- **Build Command**: `{{BUILD_COMMAND}}`
- **Type Check Command**: `{{TYPE_CHECK_COMMAND}}`
- **Lint Command**: `{{LINT_COMMAND}}`
- **Project Root**: {{PROJECT_ROOT}}

{{WRAPPER_MODE_SECTION}}

## Project Structure

{{PROJECT_STRUCTURE}}

## Development Commands

{{DEV_COMMANDS}}

## Architecture

{{ARCHITECTURE_DETAILS}}

{{PACKAGE_STACKS_SECTION}}

## Workflow

### Spec-Driven Development Flow

```
/setup-wizard → /constitute → /onboard → /research → /specify → /plan → /breakdown → /execute-task → /review → /verify → /summarize → /finalize
   (once)         (once)       (once)    (optional)  (per feat)  (per feat) (per feat)   (per task)    (per feat) (per feat) (per feat)  (per feat)
```

- `/specify "feature"` — Create spec with acceptance criteria → `specs/NNN-name/spec.md`
- `/plan` — Technical plan from approved spec → `specs/NNN-name/plan.md`
- `/breakdown` — Atomic tasks with dependencies → `specs/NNN-name/tasks/`
- `/execute-task N` — Implement one task with assigned agent
- `/review` — Security + performance + test review → findings report
- `/verify` — Check acceptance criteria against spec
- `/finalize` — Squash WIP commits, generate docs, clean commit

Standalone (no spec required):
- `/fix "bug"` — Localized bug fix (1-5 files)
- `/refactor path "goal"` — Behavior-preserving restructuring (1-5 files)
- `/security [target]` — On-demand security review
- `/audit` — Adversarial whole-codebase quality review
- `/research "topic"` — Feasibility check before specifying

### Command Details

#### `/research "topic or idea"` (optional)
Quick feasibility check for vague ideas. Investigates the codebase for related patterns, optionally researches external approaches (signal-based), and displays the full report in the console. You're then asked whether to save — if yes, saves to `research/YYYY-MM-DD-[topic-slug].md`. Does NOT create specs or modify code. Use before `/specify` when you're unsure whether an idea is viable or how it fits.

#### `/specify "feature description"`
Creates a structured specification with acceptance criteria. Asks clarifying questions as needed (no artificial limit — the AI judges how many based on input clarity). Analyzes affected code, saves spec to `specs/[feature]/spec.md`. **Requires approval before proceeding.** Auto-creates a `spec/NNN-short-desc` branch when on the default branch.

#### `/plan [spec-file]`
Takes an approved spec and produces a technical plan: architecture decisions, data model, API contracts, research. Saves to `specs/[feature]/plan.md`. **Requires approval before breakdown.**

#### `/breakdown [spec-file]`
Takes an approved plan and generates ordered, atomic tasks with dependencies and agent assignments. Saves to `specs/[feature]/tasks/`. **Requires approval before execution.**

#### `/execute-task [number]`
Executes a single task from the breakdown using the assigned specialized agent. Follows enforced workflow:
1. Pre-flight check (constitution, memory, file state, contract preconditions)
2. Agent execution with scope constraints (agent writes code + inline docs)
3. Post-execution verification (tsc, lint, build, done conditions, self-repair)
4. Code review (code-reviewer agent — findings reported to user, critical issues block)
5. Memory update
WIP commits accumulate across tasks and are squashed by `/finalize` when the feature is approved.

#### `/review [spec-file]`
Launches specialist review agents (security, performance, test assessment) on completed feature code. Produces a structured review report saved to `specs/[feature]/review.md` for `/verify` to incorporate into its verdict. Does not render a verdict — findings only.

#### `/verify [spec-file]`
Verifies all completed tasks against the spec's acceptance criteria. When AC verification is enabled (`AC_VERIFICATION` in project-config.json), launches the **ac-verifier** agent to test acceptance criteria against the running app via Chrome DevTools MCP and/or API calls — falls back to code reading when MCP is not available. Incorporates `/review` findings if available (warns if missing). Performs cross-task integration check (not full code review — that was done per-task). Updates memory with lessons learned.

#### `/summarize [spec-file]`
Generates a concise, PR-ready summary of a completed feature. Reads spec, plan, tasks, and git history. Saves to `specs/[feature]/summary.md`. Run after `/verify` approves, before `/finalize`.

#### `/finalize [spec-file]`
Generates feature-level documentation via tech-writer, then squashes all WIP commits into a single clean feature commit. Gate-checked: spec must be Complete (set by `/verify`). The last step before creating a PR.

#### `/constitute`
One-time deep codebase analysis (or interview for greenfield projects) that generates `constitution.md` — non-negotiable rules, architecture decisions, patterns.

#### `/onboard`
One-time deep codebase scan for existing projects. Uses the tech-writer agent to generate comprehensive documentation in `docs/` — the knowledge base for all agents. Run once after `/constitute`.

#### `/fix "bug description"`
Lightweight bug-fix workflow for small, localized bugs (1-5 files). Bypasses the full spec→plan→breakdown pipeline. Phases:
1. Diagnosis (runtime-debugger agent for runtime errors, manual tracing for logic bugs)
2. User confirms root cause (hard gate)
3. Apply minimal fix with WIP checkpoint
4. Verification (tsc, lint, build, self-repair loop)
5. Code review (code-reviewer agent)
6. Test assessment (qa-engineer agent)
7. Clean commit + memory update

If the bug grows beyond 5 files, recommends escalating to `/specify`.

#### `/refactor path/to/file.ts "goal"`
Focused code refactoring workflow for behavior-preserving restructuring (1-5 files). Supports IDE-injected context (active file/selection from WebStorm) or manual file path. Phases:
1. Analysis (detect refactoring opportunities against constitution rules — long functions, SOLID/DRY/KISS violations, type safety, naming, dead code, pattern mismatches)
2. User approves proposal with specific items (hard gate, partial approval supported)
3. Apply refactoring with auto-selected agent (architect, frontend-engineer, or backend-engineer based on file layer)
4. Verification (tsc, lint, build, tests, self-repair loop)
5. Code review (code-reviewer agent)
6. Test assessment (qa-engineer agent — tests must pass unchanged since refactoring is behavior-preserving)
7. Clean commit + memory update

If the refactoring grows beyond 5 files, recommends escalating to `/specify`.

#### `/security [file|dir|--full]`
On-demand security review. Targets a specific file (with optional line range), directory, uncommitted changes (default), or the full codebase (`--full`). Launches the security-reviewer agent with constitution and memory context. Reports findings by severity (Critical/High/Medium/Info) with CWE identifiers and remediation suggestions. Read-only — does not modify code. Full codebase mode uses module-based subagents for large projects.

#### `/audit [--full | --uncommitted | path]`
Standalone adversarial whole-codebase audit for periodic "second opinion" quality reviews. Launches code-reviewer, architect, qa-engineer, and security-reviewer in **adversarial mode** with a structured Mislogic Hunt Checklist (naming-vs-behavior mismatches, lying comments, off-by-one errors, dead branches, cross-file contradictions, contradictory configs). Reads up to 5 recent `specs/*/review.md` files to track recurring/unresolved issues across features. Anti-hallucination grounding: every finding must include a verbatim Evidence quote from the actual code; Phase 4 validation re-reads cited files and discards ungrounded findings. Writes dated reports to `audits/YYYY-MM-DD-audit.md` and prints inline summary. Read-only, not auto-committed, **NOT part of any workflow chain** — invoke manually after several specs ship.

#### Additional Commands

- `/setup-wizard` — Re-run initial project setup (regenerates config files)

## Available Agents

{{AGENT_LIST}}

Agent selection is automatic in `/execute-task` based on the task's assigned agent.

## Enforced Quality Gates

### Hard Gates (block until approved)
- Spec approval → before `/plan` can run
- Plan approval → before `/breakdown` can run
- Task breakdown approval → before `/execute-task` can start
- Acceptance criteria → verified in `/verify`

### Verification (explicit, scope-aware — no per-edit hooks)

Verification runs at task boundaries (end of `/execute-task`, `/fix`, `/refactor`, etc.), not after every file edit. No per-edit hooks, no auto-execution after Edit/Write. (Runtime hooks for CBM-first discovery enforcement are described in **CBM-first Protocol Enforcement** below — those operate on Read/Grep/Glob/Bash/SessionStart, not on Edit/Write.) Verification is **scope-aware**: the phase reads `PACKAGE_STACKS` (see `## Packages` above) to determine which type-check / lint / build commands apply to each file touched during the task.

**Scope-aware verification flow**:

1. Identify files touched during the task (git diff against the task-start checkpoint).
2. For each touched file, find its package via `PACKAGE_STACKS` path lookup (longest path prefix wins; e.g., `services/api/users.py` matches the `services/api` package).
3. Run that package's `type_check_command` and `lint_command` (stored in `.devforge/project-config.json`). Skip `"N/A"` commands silently (no-op; not a failure).
4. Build (`build_command`) typically runs once per task at the end, aggregated across touched packages when multiple are edited.
5. For files not inside any detected package (top-level scripts, misc files): fall back to the primary-stack commands (`TYPE_CHECK_COMMANDS[0]` / `LINT_COMMANDS[0]` / `BUILD_COMMANDS[0]`).
6. **Self-repair loop**: if type check or lint fails, attempt up to 3 auto-repair iterations before stopping and reporting. Code-review findings are reported to the user, not auto-repaired.

**Pre-flight check** (before each task): read `constitution.md` and `.devforge/memory.md` so the task starts with the right context.

Full specification in `/execute-task`.

## CBM-first Protocol Enforcement

Four hook scripts ship at `.claude/hooks/` and are wired in `.claude/settings.json` to enforce the codebase-memory-mcp (CBM) discovery protocol at runtime. They steer code exploration toward `search_graph`, `trace_path`, `get_code_snippet`, `search_code`, and `query_graph` instead of raw `Read`/`Grep`/`Glob` or shell `grep`/`find`/`cat` over source files.

| Hook | Event | Matcher | Behavior |
|---|---|---|---|
| `cbm-code-discovery-gate` | `PreToolUse` | `Read\|Grep\|Glob` | Blocks (exit 2) on the first matched call of the session and sets the gate file, with a stderr reminder to use CBM tools; subsequent matches in the same session pass through (exit 0). Gate file: `/tmp/cbm-code-discovery-gate-$PPID`. |
| `bash-ban-raw-tools` | `PreToolUse` | `Bash` | First call per session whose `command` contains `grep`/`find`/`cat` over a source-extension file (`.py`, `.ts`, `.tsx`, `.vue`, `.go`, …) blocks (exit 2); other Bash calls and subsequent same-session matches pass through. Gate file: `/tmp/bash-ban-raw-tools-$PPID`. |
| `cbm-mcp-marker` | `PostToolUse` | `Bash\|mcp__codebase-memory-mcp__.*` | Appends `<UTC timestamp> <tool_name>` to `.devforge/cbm-usage.log` for every matched call (Bash + every CBM MCP tool); filter the log on the `mcp__` prefix to isolate the CBM-adoption signal. Always exit 0; never blocks. |
| `cbm-session-reminder` | `SessionStart` | `startup\|resume\|clear\|compact` | Stdout is injected as session context; re-states the CBM-first protocol after compaction / resume / clear. |

### Disabling individual hooks

To disable any hook, remove its entry from the corresponding event array in `.claude/settings.json`. The hook scripts under `.claude/hooks/` remain on disk but are no longer invoked. Re-running `install.sh` overwrites `.claude/settings.json` and restores the hooks.

### Why CBM-only

The hook messages reference codebase-memory-mcp tools exclusively (`search_graph`, `trace_path`, `get_code_snippet`, `search_code`, `query_graph`, `get_architecture`, `index_repository`). They do NOT reference codegraph's `agentic_*` tools — those require LLM-enabled mode that is not configured in default forge installs.

## Placeholder Convention

Any `{{UPPERCASE}}` marker (e.g., `{{PROJECT_NAME}}`, `{{LANGUAGE}}`) in a template file is a substitution placeholder. Each marker is replaced with the user's answer or a detected value before the file is presented to the user.

Authors of template files — constitution, agent files, docs, this CLAUDE.md — may use these placeholders freely. Readers must never see literal `{{...}}` text in substituted output; if a placeholder reaches the user verbatim, the substitution step is broken or the marker name is wrong.

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
13. **Session state** — after each `/execute-task`, overwrite `.devforge/session-state.md` with a fixed-size snapshot of current progress. At session start, read it first if it exists.
14. **Crash recovery** — `/execute-task` writes a WIP marker (`.devforge/wip.md`) before execution and creates git checkpoints at each phase. If interrupted, the next run detects it and offers resume/rollback/skip options.

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

docs/
  overview.md                  # Project overview + package map (project tier)
  architecture.md              # Cross-package architecture + layering rationale
  <package>/                   # One subdir per package (from .devforge/index.json)
    overview.md                # Package role + concerns list
    architecture.md            # Package layers + patterns
    <concern>/                 # One subdir per src/ subfolder
      index.md                 # Concern: Purpose + Structure (annotated tree, fenced) — LLM-first density
```

- Feature dirs: `NNN-kebab-name`, sequential numbering (001, 002, ...)
- Task files: `NNN-short-title.md`, sequential within feature
- Everything for a feature lives in one directory
- docs/ is generated by `/generate-docs` (Plan F): bottom-up tiers (concerns → packages → project), incremental skip via `source_stamp` frontmatter
- docs/ files are LLM context source first, dev-greppable second (LLM-first density format; see `.devforge/storage-rules.md`)
- Structural queries (exports, types, callers, deps, dead code) are NOT in docs/ — query the codebase-memory-mcp graph live via MCP tools (`search_graph`, `trace_path`, `get_code_snippet`, `search_code`, `query_graph`)
- Md files are auto-indexed by codebase-memory-mcp; `search_graph(query="<fuzzy topic>")` plus `search_code(pattern)` together surface md narrative + code structure
- `docs/overview.md` carries a `## Suggested Research Starts` section — 3-6 LLM-curated research questions with scope hints and cite_paths to seed cold-start orientation for fresh sessions
- See `.devforge/storage-rules.md` for full conventions including density rules + cite-back validation
- **Wrapper mode**: All artifacts (`specs/`, `docs/`, `constitution.md`) live in the wrapper root, NOT inside `{{PROJECT_ROOT}}`

## Session Continuity

At the start of each session, read `.devforge/session-state.md` if it exists. It contains a compact snapshot from the last completed task — current feature, progress, recent decisions, and recently modified files.

This file is:
- **Fixed-size** — always fully overwritten, never appended, max ~40 lines
- **A sliding window** — only tracks the last 3 tasks' modifications and last 3 decisions
- **Not a history log** — history lives in task completion notes (`specs/`) and `MEMORY.md`
- **Updated automatically** by `/execute-task` (Phase 7)

If context is compacted or a new session starts, session-state.md ensures the next `/execute-task` can bootstrap without re-discovering state.

### Crash Recovery

If a task execution is interrupted (power loss, terminal crash, network drop), the next `/execute-task` will detect the interrupted state via `.devforge/wip.md` and offer recovery options: resume from where it stopped, rollback and retry, rollback and skip, or keep changes for manual handling. The WIP marker includes a `Command` field identifying which command (`/execute-task`, `/fix`, or `/refactor`) was interrupted — if you run a different command, it will detect the mismatch and ask you to resolve the previous session first. Git checkpoint commits (`[WIP]` prefix) preserve partial work and are squashed into a clean feature commit by `/finalize` when the feature is approved.

## References

- [Constitution](constitution.md) — Project rules and patterns
- [Specs](specs/) — Feature specifications, plans, and tasks
- [Memory](.devforge/memory.md) — Persistent learnings
- [Project Config](.devforge/project-config.json) — Wizard answers plus per-stack arrays (`LANGUAGES`, `FRAMEWORKS`, `ARCHITECTURES`, `ERROR_HANDLINGS`, `API_LAYERS`, `TESTINGS`) and per-package `PACKAGE_STACKS` records
