# Claude Hybrid Template — Development Status

## What This Is

A reusable spec-driven development template for Claude Code. Combines a structured intake flow (clarify → specify → plan → breakdown → execute → verify) with enforced quality gates, specialized agents, and automated hooks.

## What's Built

### Commands (10 files in `.claude/commands/`)
- `setup-wizard.md` — Interactive project setup, auto-detects stack or interviews for greenfield
- `constitute.md` — Generates constitution from codebase analysis (existing) or interview (greenfield)
- `onboard.md` — Deep codebase scan for existing projects, generates comprehensive `docs/` via tech-writer agent
- `clarify.md` — Optional pre-step, 9 ambiguity categories, max 5 questions
- `specify.md` — Creates feature specs with acceptance criteria
- `plan.md` — Technical plan between spec and breakdown (architecture, data model, contracts)
- `breakdown.md` — Splits plan into sequential atomic tasks in individual files
- `execute-task.md` — Runs a single task with pre-flight checks, agent execution, doc writing, verification
- `verify.md` — Validates all tasks against spec acceptance criteria
- `fix.md` — Lightweight bug-fix workflow: diagnose → fix → review → test, with runtime-debugger, code-reviewer, and qa-engineer agents

### Agent Templates (14 files in `.claude/templates/agents/`)
Always included: `code-reviewer`, `qa-engineer`, `runtime-debugger`, `tech-writer`
By project type: `frontend-engineer`, `backend-engineer`, `architect`
By detected stack: `db-engineer`, `devops-engineer`, `design-auditor`, `api-designer`, `performance-analyst`, `security-reviewer`, `migration-engineer`

Setup wizard decides which agents to generate based on detected stack.

### Supporting Templates (in `.claude/templates/`)
- `CLAUDE.template.md` — Main project config, workflow commands, key rules (Always/Never lists)
- `constitution.template.md` — Pre-populated universal rules + project-specific placeholders
- `settings.template.json` — PostToolUse type-checking hook + safe permissions
- `spec.template.md` — Feature spec template with 10 sections
- `memory.template.md` — Persistent memory with universal categories
- `storage-rules.md` — Full storage conventions for specs, tasks, and docs

### Other
- `README.md` — Full documentation with installation, workflow, pre-populated rules section
- `specs/` — Empty specs directory with .gitkeep

### Wrapper Mode
- Setup wizard detects nested git repos at depth 1 and offers wrapper mode
- `SOURCE_ROOT` variable propagated through CLAUDE.md → all commands read it
- All 9 commands scope source scanning to the Source Root path
- Wrapper repo git auto-commits only; inner repo commits are manual
- `/execute-task` Phase 3.3 verifies no Claude artifacts leak into the inner project
- `install.sh --wrapper` pre-configures the `.gitignore` entry for the inner folder
- CLAUDE.md template has conditional `{{WRAPPER_MODE_SECTION}}` (omitted for standalone)
- Memory template tracks `{{WORKSPACE_MODE}}` (standalone/wrapper) and `{{SOURCE_ROOT}}`

## Key Design Decisions

1. **User's workflow is primary** — spec-kit ideas adapted to serve hard gates + agents, not replace them
2. **Hard gates at every phase transition** — spec, plan, breakdown all require explicit user approval
3. **Per-feature storage** — everything in `specs/NNN-feature-name/` with tasks as individual numbered files in `tasks/` subfolder
4. **Sequential numbering** — features: 001, 002...; tasks within feature: 001, 002...
5. **All agents as templates, wizard selects** — 14 templates, setup wizard conditionally generates based on project
6. **Universal constitution rules pre-populated** — SOLID, DRY, KISS, error handling, code quality, workflow rules all built-in; project-specific rules added by `/constitute`
7. **Mandatory documentation** — tech-writer agent runs after every task, reads only changed code, writes to `docs/`
8. **Greenfield support** — all commands work for empty/new projects
9. **Check before build** — must search codebase for existing utilities before creating new ones
10. **Onboarding for existing projects** — `/onboard` generates comprehensive docs as the knowledge base for all agents
11. **Wrapper mode for client-invisible AI** — template wraps around existing project folder; zero Claude traces in the client's repo

### Onboarding System (`/onboard`)
- Runs after `/constitute` for existing projects — uses constitution + CLAUDE.md + memory as input
- Delegates ALL scanning and documentation to the tech-writer agent in onboarding mode
- Context-safe scanning via size-based strategies:
  - < 50 files: single agent, direct scan
  - 50-200 files: one subagent per module, parallel
  - 200-1000 files: two-pass (structure first, then depth via subagents)
  - 1000+ files: sample-based (entry points + types + 2-3 representative files per module)
- Smart extraction: types read fully, implementation files read signatures only, tests read names only
- Fixed-size output contract: each subagent returns max 50 lines per module
- Generates: `docs/overview.md`, `docs/architecture.md`, `docs/features/*.md`, `docs/api/*.md`
- Enriches memory with module boundaries, dependency warnings, and complexity areas
- Docs serve as the primary knowledge base for all agents during `/execute-task`

### Context Maintenance (Phase 7.5)
- `/execute-task` now includes Phase 7.5: Context Maintenance after each task
- Writes a fixed-size (~40 line) sliding window to `.claude/session-state.md` with current progress, recent decisions, and modified files
- Three-tier context health check: light (no action), moderate (optional /compact), heavy (strongly recommend /compact)
- Session state is gitignored — it's a runtime artifact, not project state
- CLAUDE.template.md updated with rule 13 (session state) and Session Continuity section

### Crash Recovery (Phase 0 + WIP Checkpoints)
- `/execute-task` now creates a WIP marker (`.claude/wip.md`) and git checkpoint commits during execution
- Phase 0: Recovery Check detects interrupted tasks and offers 4 options: resume, rollback+retry, rollback+skip, keep manual
- Git `[WIP]` commits preserve partial work at each phase; squashed into a clean commit on completion
- `wip.md` is gitignored — only exists during active task execution

## What's Left / Potential Enhancements

- Test the full flow end-to-end on an actual project
- The `docs/` folder structure might need adjustment per project type
- Consider adding a `/commit` command that summarizes changes
- Consider a `/status` command to show current feature progress
- The setup wizard could detect more frameworks/tools
- Agent templates use `{{PLACEHOLDER}}` variables — wizard must replace all of them
- `constitution.md` stub generation (step 3.5 in wizard) — template content TBD
- ~~Consider if tech-writer should also update inline code docs (JSDoc/docstrings) or just `docs/` folder~~ **DECIDED: both. Tech-writer updates inline docs (JSDoc/docstrings) AND `docs/` folder.**
