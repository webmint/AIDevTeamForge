# AIDevTeamForge — Development Status

## What This Is

A reusable spec-driven development template for Claude Code. Combines a structured intake flow (research → specify → plan → breakdown → execute → review → verify → summarize → finalize) with enforced quality gates, specialized agents, and automated hooks.

## What's Built

### Commands (19 commands + 5 shared partials in `.claude/commands/`)
- `setup-wizard.md` — Interactive project setup, auto-detects stack or interviews for greenfield; saves baselines for three-way merge on first run; detects DEFAULT_BRANCH; conditionally adds Chrome MCP based on AC_VERIFICATION setting
- `constitute.md` — Generates constitution from codebase analysis (existing) or interview (greenfield)
- `onboard.md` — Deep codebase scan for existing projects, generates comprehensive `docs/` via tech-writer agent
- `research.md` — Quick feasibility check for vague ideas; investigates codebase and docs/ for related patterns, signal-based external research (Context7 first for libraries, WebSearch for comparisons), displays full report in console and optionally saves to `research/YYYY-MM-DD-[topic-slug].md`
- `specify.md` — Creates feature specs with acceptance criteria; clarifies requirements in rounds of up to 5 questions (no artificial limit); auto-creates `spec/NNN-short-desc` branch when on default branch
- `plan.md` — Technical plan between spec and breakdown (architecture, data model, contracts); signal-based research with tightened triggers (not-in-project qualifier); Context7 first for library docs; Phase 2.5 cross-references plan against spec ACs before presenting to user
- `breakdown.md` — Splits plan into sequential atomic tasks in individual files; generates cross-task contracts (Expects/Produces) and auto-places review checkpoints; references shared `_agent-assignment.md` for agent selection
- `execute-task.md` — 6-phase workflow: load context → pre-flight (contracts) → execute (agent → verify → code review) → complete & report → bookkeeping (memory + context + multi-task). Per-task code review reports findings to user. No per-task squash — WIP commits deferred to /finalize
- `review.md` — Expert code review: launches specialist agents (security-reviewer, performance-analyst, qa-engineer) on all changed files. Produces structured review report saved to `specs/[feature]/review.md`. No verdict — findings only
- `verify.md` — Validates all tasks against spec acceptance criteria; cross-task integration check (not full code review — done per-task); incorporates `/review` findings if available; renders verdict (APPROVED/NEEDS WORK/REJECTED); Phase 9 presents issues with batch bug filing — does not invoke /fix
- `summarize.md` — Generates concise, PR-ready feature summary from spec, plan, tasks, and git history; reads DEFAULT_BRANCH from config; wrapper mode source repo handling. Run after `/verify`, before `/finalize`
- `finalize.md` — Feature documentation via tech-writer + feature squash using `git merge-base`. Gate-checked: spec must be Complete. The last step before creating a PR
- `fix.md` — Lightweight bug-fix workflow: diagnose → delegate to agent → verify → code review → test → doc update, with runtime-debugger, code-reviewer, qa-engineer, and tech-writer agents; accepts enriched bug file paths from `bugs/`; agent selection via shared `_agent-assignment.md`
- `report-bug.md` — Creates structured bug report files in `bugs/` for later fixing via `/fix` or `/specify`
- `refactor.md` — Focused refactoring workflow: analyze → propose → approve → delegate to agent → verify → code review → test → doc update, with auto-selected agent via `_agent-assignment.md`, code-reviewer, qa-engineer, and tech-writer agents
- `refresh-docs.md` — Lightweight documentation refresh using git delta; invokes tech-writer in Refresh Mode on changed files only
- `security.md` — On-demand security review: targeted (file, directory, uncommitted changes) or full codebase (`--full`). Launches security-reviewer agent with constitution context. Module-based subagents for large codebases. Read-only
- `release.md` — Meta-command for the template repo itself: automates version bump, changelog, and documentation updates after making changes

Shared partials (`_`-prefixed, loaded on-demand by parent commands):
- `_recovery.md` — Phase 0 crash recovery with deterministic hash-based rollback, shared by execute-task, fix, and refactor
- `_context-maintenance.md` — Phase 5.2 session state and context health (execute-task)
- `_multi-task-continuation.md` — Phase 5.3 batch queue management (execute-task multi-task mode)
- `_tech-writer-onboarding.md` — Full onboarding scan instructions Section A (onboard)
- `_agent-assignment.md` — Shared file-layer→agent mapping table, referenced by breakdown, fix, and refactor

### Agent Templates (16 files in `.claude/templates/agents/`)
Always included: `code-reviewer`, `qa-engineer`, `runtime-debugger`, `tech-writer`, `security-reviewer`
By project type: `frontend-engineer`, `backend-engineer`, `architect`, `mobile-engineer`
By detected stack: `db-engineer`, `devops-engineer`, `design-auditor`, `api-designer`, `performance-analyst`, `migration-engineer`
By config: `ac-verifier` (when `AC_VERIFICATION != "off"`)

Setup wizard decides which agents to generate based on detected stack and user preferences (including AC verification mode).

### Supporting Templates (in `.claude/templates/`)
- `CLAUDE.template.md` — Main project config (including Type Check Command and Lint Command fields), workflow commands, key rules (Always/Never lists), commit convention (format + attribution)
- `constitution.template.md` — Pre-populated universal rules + project-specific placeholders; `/constitute` copies `[universal]` sections verbatim
- `settings.template.json` — PostToolUse type-checking hook + default permissions (Edit, Write, Bash, Agent, read tools, task tools, MCP tools)
- `spec.template.md` — Feature spec template with 10 sections
- `memory.template.md` — Persistent memory with universal categories
- `storage-rules.md` — Full storage conventions for specs, tasks (with contracts and review checkpoint fields), bugs, and docs

### Update System
- `update.sh` — Manifest-driven update script with 4 strategies: overwrite (template-owned), three-way merge via `git merge-file` (agents + CLAUDE.md), smart merge (JSON/text), copy-if-missing
- **Three-way merge**: stores baseline snapshots of substituted templates in `.claude/agents/.baseline/` and `.claude/.baseline/`. On update, computes diff (baseline → new template) and applies it to current file — preserves all project customizations while propagating template improvements
- **Placeholder validation**: after substitution, checks for remaining `{{...}}` patterns; skips file if found (prevents destroying agents with broken config values)
- `.claude/project-config.json` — Machine-readable config written by `/setup-wizard`, stores all template variable values (including `TYPE_CHECK_COMMAND`, `LINT_COMMAND`, `COMMIT_ATTRIBUTION`, `MODEL_THINK`, `MODEL_DO`, `MODEL_VERIFY`) for `update.sh` placeholder substitution
- `.claude/template-manifest.json` — Defines file ownership categories and update strategies; self-updates (template-owned)
- One-time migration: extracts config from existing `CLAUDE.md` and agent files when `project-config.json` is missing

### Other
- `README.md` — Full documentation with installation, workflow, pre-populated rules section
- `specs/` — Empty specs directory with .gitkeep
- `bugs/` — Empty bugs directory with .gitkeep (bug backlog for `/report-bug` and `/verify` triage)
- `research/` — Empty research directory with .gitkeep (research reports from `/research`)

### Wrapper Mode
- Setup wizard detects nested git repos at depth 1 and offers wrapper mode
- `SOURCE_ROOT` variable propagated through CLAUDE.md → all commands read it
- All commands scope source scanning to the Source Root path
- Git auto-commits apply to both repos — wrapper gets workflow commits, source repo gets per-task WIP commits squashed into one clean commit (`[TICKET-ID] - Description`) at `/verify` (or at `/fix`/`/refactor` final commit)
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
6. **Universal constitution rules pre-populated** — SOLID, DRY, KISS, error handling, code quality, workflow rules all built-in; `/constitute` preserves these `[universal]` sections verbatim and only populates `[project-specific]` sections
7. **Two-layer documentation** — implementing agents write inline docs (JSDoc/docstrings) as part of code; code-reviewer verifies inline docs per-task; tech-writer generates feature-level docs in `docs/` at `/verify` time (once per feature, not per task). `/fix` and `/refactor` run tech-writer per-command (standalone, no /verify follows). `/refresh-docs` catches stale docs via git delta
8. **Greenfield support** — all commands work for empty/new projects
9. **Check before build** — must search codebase for existing utilities before creating new ones
10. **Onboarding for existing projects** — `/onboard` generates comprehensive docs as the knowledge base for all agents
11. **Wrapper mode for client-invisible AI** — template wraps around existing project folder; zero Claude traces in the client's repo
12. **Cross-task contracts prevent silent drift** — each task declares Expects/Produces; preconditions catch upstream semantic errors before they compound, postconditions verify the task delivered what downstream tasks need
13. **Configurable AI attribution** — commits default to no Claude/AI mention; opt-in via setup wizard. Rule stored in CLAUDE.md and enforced by all commit-creating commands
14. **Tiered agent models** — agents use 3 model tiers: Think (opus — architect, api-designer, security-reviewer), Do (sonnet — implementation agents), Verify (sonnet — review/test agents). Configurable via setup wizard (`MODEL_THINK`, `MODEL_DO`, `MODEL_VERIFY` in project-config.json)
15. **Three-way merge for updates** — `update.sh` uses `git merge-file` with baselines to apply only template diffs, preserving all project customizations (wizard-added items, custom sections, manual edits)
16. **AC verification is opt-in and project-conditional** — setup wizard asks if AC should be verified via browser (Chrome MCP), API calls, or code reading. Chrome MCP only installed for auto/browser-only projects. `/verify` Phase 2 launches the ac-verifier agent when enabled, with graceful fallback to code reading
17. **Per-task code review, integration check at epic level** — code-reviewer runs after each `/execute-task` task (findings reported to user: address/continue/stop). `/verify` does cross-task integration check only — not full code review. `/fix` and `/refactor` also report review findings to user (consistent across all commands)
18. **Language-agnostic agent templates** — type safety rules use `{{TYPE_SAFETY_RULES}}` placeholder generated by setup wizard based on detected language. No hardcoded TypeScript-specific items. Agent templates use `Inline docs` not `JSDoc`
19. **Pipeline vs standalone command lifecycle** — pipeline commands (execute-task) defer squash and feature docs to the pipeline end (/verify). Standalone commands (fix, refactor) are self-contained — handle their own squash, docs, and cleanup. Different lifecycle patterns, both correct for their context

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
- Docs serve as the primary knowledge base, consumed by `/specify` and flowed to agents through the spec → breakdown → task reference chain

### Context Maintenance (Phase 5.2)
- `/execute-task` includes Phase 5.2: Context Maintenance after each task
- Writes a fixed-size (~40 line) sliding window to `.claude/session-state.md` with current progress, recent decisions, and modified files
- Three-tier context health check: light (no action), moderate (optional /compact), heavy (strongly recommend /compact)
- Session state is gitignored — it's a runtime artifact, not project state
- CLAUDE.template.md updated with rule 13 (session state) and Session Continuity section

### Crash Recovery (Phase 0 + WIP Checkpoints)
- `/execute-task`, `/fix`, and `/refactor` create a WIP marker (`.claude/wip.md`) and git checkpoint commits during execution
- Phase 0: Recovery Check (shared via `_recovery.md`) detects interrupted sessions and offers 4 options: resume, rollback+retry, rollback+skip, keep manual. WIP markers include a `Command` field (execute-task/fix/refactor) to prevent cross-command recovery confusion
- Git `[WIP]` commits preserve partial work at each phase. For execute-task: WIP commits accumulate across tasks and are squashed by `/finalize` using `git merge-base`. For fix/refactor: squashed per-command (with pre-squash safety check — skips if commits already pushed)
- All workflow commits use scoped `git add` (specific files only, never `git add -A`) to prevent accidentally committing secrets or unwanted files
- `wip.md` is gitignored — only exists during active task execution
- In wrapper mode, WIP marker includes `## Source Repo Checkpoint` section; Phase 0 recovery also rolls back source repo WIP commits

## What's Left / Potential Enhancements

- Test the full flow end-to-end on an actual project
- The `docs/` folder structure might need adjustment per project type
- Consider adding a `/commit` command that summarizes changes
- Consider a `/status` command to show current feature progress
- The setup wizard could detect more frameworks/tools
- ~~Agent templates use `{{PLACEHOLDER}}` variables — wizard must replace all of them~~ **FIXED: `update.sh` now applies placeholder substitution using `.claude/project-config.json`**
- ~~`constitution.md` stub generation (step 3.5 in wizard) — template content TBD~~ **FIXED: wizard copies template with resolved headers, preserves sentinel strings**
- ~~`/clarify` command overlap with `/specify`~~ **RESOLVED: `/clarify` removed, clarification absorbed into `/specify` Phase 2**
- Consider spec validation agents (R1 from competitive analysis) — plan-spec cross-reference already added, spec validation is lower priority with per-task code review as safety net
- ~~Consider if tech-writer should also update inline code docs (JSDoc/docstrings) or just `docs/` folder~~ **DECIDED: both. Tech-writer updates inline docs (JSDoc/docstrings) AND `docs/` folder.**
