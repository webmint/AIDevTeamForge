# Changelog

All notable changes to this template will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-03-19

### Added
- `/fix` command — lightweight bug-fixing workflow for small, localized bugs (1-5 files)
  - Diagnosis phase with **runtime-debugger** agent for runtime errors or manual tracing for logic bugs
  - Hard gate on diagnosis — user must confirm root cause before any code changes
  - Scope guard — automatically recommends `/specify` if bug affects more than 5 files
  - **code-reviewer** agent runs on all changed files after fix
  - **qa-engineer** agent assesses test impact and writes regression tests when warranted
  - Self-repair loop (up to 3 attempts) on verification failure — same pattern as `/execute-task`
  - Full crash recovery with WIP markers and git checkpoints
  - Wrapper mode awareness (Source Root scoping, isolation checks)
  - Memory update for bug patterns and pitfalls
- `/refactor` command — focused code refactoring workflow for behavior-preserving restructuring (1-5 files)
  - Supports both IDE-injected context (active file/selection from WebStorm) and manual file path with optional line range
  - Structured analysis phase scans 9 refactoring categories: long functions, deep nesting, SOLID/DRY violations, type safety, naming, dead code, pattern mismatches, complexity
  - Auto-selects execution agent based on file layer (**architect**, **frontend-engineer**, or **backend-engineer**)
  - Hard gate on proposal — user sees detailed before/after for each opportunity and can approve all, specific items, or cancel
  - Partial approval supported — approve individual refactoring actions by number
  - **code-reviewer** agent validates refactored code
  - **qa-engineer** agent verifies tests still pass (behavior-preserving guarantee)
  - Self-repair loop, crash recovery, constitution enforcement, and memory updates — same patterns as `/fix`

### Changed
- Command count: 9 → 11
- CLAUDE.md template updated with `/fix` and `/refactor` in workflow commands section
- Template manifest updated to include `fix.md` and `refactor.md` as template-owned

## [1.3.0] - 2026-03-19

### Added
- **Wrapper mode** — setup wizard now detects nested git repos and offers wrapper mode for projects where AI usage must be invisible to the client
  - Wrapper repo holds all Claude artifacts (`.claude/`, `CLAUDE.md`, `constitution.md`, `specs/`, `docs/`)
  - Inner folder is the client's separate git repo with zero Claude traces
  - Auto-detection: scans for nested `.git/` directories at depth 1
  - New `{{SOURCE_ROOT}}` and `{{WRAPPER_MODE_SECTION}}` placeholders in CLAUDE.md template
  - New `{{WORKSPACE_MODE}}` placeholder in memory template
  - Inner project folder automatically added to wrapper's `.gitignore`
  - Git auto-commits apply to wrapper repo only; source code commits are manual
- All 9 commands now read Source Root from CLAUDE.md and scope source scanning accordingly
- `/execute-task` Phase 3.3 includes wrapper isolation check (no Claude artifacts inside Source Root)
- `install.sh` now supports `--wrapper` flag for pre-configuring wrapper mode during installation

### Changed
- `/setup-wizard` Step 0 is now Workspace Mode Detection; original greenfield detection moved to Step 0.5
- `/constitute` scans Source Root instead of workspace root when in wrapper mode
- `/onboard` uses Source Root as starting point for tree scan
- Settings template type-check command prefixed with `cd SOURCE_ROOT &&` in wrapper mode

## [1.2.0] - 2026-03-19

### Added
- `/execute-task` self-repair loop — when post-execution verification fails (tsc, lint, done-conditions), automatically launches a repair agent to fix errors (up to 3 attempts) before stopping
- `/execute-task` multi-task arguments:
  - `1,3,5` — execute specific tasks sequentially
  - `1-5` — execute a range of tasks
  - `all` — execute all pending tasks in active feature
- Phase 8 (Multi-Task Continuation) — chains task cycles, checks dependencies between tasks, produces batch summary
- Auto-compact in multi-task mode — at heavy context load (6+ tasks), automatically compacts without asking

### Changed
- `/execute-task` Phase 3.3 now includes self-repair before escalating to user
- Important Rules updated: "one task at a time" → "one task per cycle", added self-repair and hard-stop rules
- Context hygiene rule updated: auto-compact at heavy load in multi-task mode

## [1.1.0] - 2026-03-19

### Added
- `/onboard` command — deep codebase scan and documentation generation for existing projects
  - Delegates all scanning and writing to the tech-writer agent in onboarding mode
  - Context-safe: uses subagent parallelism, smart extraction, and fixed-size output contracts
  - Size-based scan strategies: direct (< 50 files), subagent-per-module (50-200), two-pass (200-1000), sample-based (1000+)
  - Generates real `docs/` content: `overview.md`, `architecture.md`, `features/*.md`, `api/*.md`
  - Enriches `.claude/memory/MEMORY.md` with module boundaries, dependency warnings, and complexity areas
  - Run once after `/constitute` for existing projects

### Changed
- Tech-writer agent template now supports two operating modes: Normal (task docs) and Onboarding (deep scan)
- Workflow updated: `/setup-wizard` → `/constitute` → `/onboard` → `/clarify` → `/specify` → ...
- `/constitute` now recommends `/onboard` as next step for existing projects
- `/setup-wizard` next steps mention `/onboard` for existing projects
- `/execute-task` Phase 1.2 clarifies that `docs/` is populated by `/onboard` for existing projects
- CLAUDE.md template updated with `/onboard` in workflow diagram and command list
- Template manifest updated to include `onboard.md` as template-owned

## [1.0.0] - 2026-03-17

### Added
- 8 workflow commands: setup-wizard, constitute, clarify, specify, plan, breakdown, execute-task, verify
- 14 specialized agent templates (code-reviewer, qa-engineer, runtime-debugger, tech-writer, frontend-engineer, backend-engineer, architect, db-engineer, devops-engineer, design-auditor, api-designer, performance-analyst, security-reviewer, migration-engineer)
- 6 configuration templates (CLAUDE.md, constitution, spec, memory, settings, storage-rules)
- MCP server integrations (Context7, Chrome DevTools)
- Hard gates at every workflow phase transition
- PostToolUse hooks for automated type checking
- Persistent memory system
- Session continuity via fixed-size sliding window
- Crash recovery with WIP checkpoints
- Greenfield project support
- Template update system (update.sh) with manifest-based file categorization
- install.sh for fresh project installation