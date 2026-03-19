# Changelog

All notable changes to this template will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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