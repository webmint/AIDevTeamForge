# Changelog

All notable changes to this template will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.16.4] - 2026-03-25

### Fixed
- **M1**: `/setup-wizard` now writes `.claude/setup-complete` marker at end of generation — allows detecting interrupted setups
- **M2**: `/execute-task` Phase 1.2 file reading budgeted — if task files exceed 500 lines total, reads only relevant sections instead of all files fully
- **M3**: `/execute-task` Phase 7.5.1 now verifies session-state.md line count after writing — trims oldest entries if over 40 lines
- **M4**: `/fix` and `/refactor` now update `.claude/session-state.md` after completion (new Phase 10) — prevents stale session state after non-execute-task workflows
- **M5**: Wrapper mode isolation check expanded to include `bugs/`, `research/`, `.mcp.json` — previously only checked 6 artifact types, now covers 9
- **M6**: Reconciled compaction contradiction between Phase 7.5.2 (advisory) and Phase 8 (pause) — added explicit note that the difference is intentional: single-task = recommend, multi-task = pause
- **M7**: `/breakdown` contract rules now require literal source code strings — "has a getter" style contracts replaced with guidance to reference declaration patterns (e.g., "`get cartTotals()`")
- **M8**: Documented `update.sh` `merge_sections()` limitation — only splits on `##` headers; custom `###` or `#` sections merge into preceding `##` body
- **M9**: `/specify` Phase 0.0 prerequisite added — verifies git repository exists before branch operations, prevents cryptic errors in non-git directories
- **M10**: Fixed research filename example from `24-03-26-` to `2026-03-26-` to match the YYYY-MM-DD format specification

### Changed
- Template version: 1.16.3 → 1.16.4

## [1.16.3] - 2026-03-25

### Fixed
- **H1**: `/execute-task` Phase 3.3 now runs affected tests (`*.test.*`, `*.spec.*`) as verification step 7 — test failures enter the self-repair loop
- **H2**: `/breakdown` agent assignment table expanded from 6 → 11 agent types — added db-engineer, api-designer, devops-engineer, migration-engineer, design-auditor
- **H3**: Standardized MEMORY.md entry format (`- **[AREA]**: [observation] _(Task N / Feature NNN)_`) across execute-task, fix, refactor, and verify commands
- **H4**: Unified spec branch/directory numbering in `/specify` — branch creation deferred to Phase 4 so both use the same NNN from `specs/` scan
- **H5**: `/verify` Phase 9 approval message no longer references non-existent `/commit` command
- **H6**: `/fix` Phase 6 code review loop limited to max 1 additional cycle when BLOCKED — prevents infinite fix→review loops
- **H7**: Standardized all date formats to ISO 8601 (`YYYY-MM-DD`) — removed `DD-MM-YY`, `DD-MM-YYYY HH:MM Ukrainian time` variants from plan, research, and clarify commands
- **H8**: Removed redundant Phase 3.3 from `/onboard` that tried to add already-existing `/onboard` entry to CLAUDE.md

### Changed
- Template version: 1.16.2 → 1.16.3
- Updated README.md, DEVELOPMENT-STATUS.md, CLAUDE.template.md, and storage-rules.md to reflect H1 (test execution) and H7 (date format) fixes

## [1.16.2] - 2026-03-25

### Fixed
- **C1**: Context handling pauses execution and prompts user-initiated compaction for heavy task loads instead of silently continuing
- **C2**: Commands now guard against empty `constitution.md` — prompts user to run `/constitute` first
- **C3**: Project mode detection uses `project-config.json` flag instead of re-counting files each time, preventing contradictory greenfield/existing behavior
- **C4**: `install.sh` no longer copies `settings.local.json` to target projects — file is project-owned, not part of template install
- **C5**: Replaced all 18 `git add -A` instances with scoped staging across `execute-task`, `fix`, `refactor`, and `verify` commands — prevents accidentally committing secrets/unwanted files
- **C6**: Pre-squash safety check added to all three workflow commands — verifies WIP commits haven't been pushed before `git reset --soft` to avoid rewriting shared history
- **C7**: `/constitute` now reads `constitution.template.md` and copies all `[universal]` sections (3.5–3.7, 4.1–4.3, 6.1–6.4) verbatim instead of regenerating them

### Changed
- Template version: 1.16.1 → 1.16.2

## [1.16.1] - 2026-03-25

### Changed
- Tech-writer agent model hardcoded to `sonnet` instead of `{{AGENT_MODEL}}` — docs generation doesn't need opus, sonnet is faster and cheaper
- `/release` command added for automating version bumps, changelog, and documentation updates in the template repo

### Fixed
- Artifact Storage tree in CLAUDE.md template showed `research/` nested under `specs/` — corrected to project root, matching `/research` command behavior since v1.13.0

## [1.16.0] - 2026-03-25

### Added
- `/setup-wizard` now saves **baselines** during generation (Steps 3.1.1 and 3.2.1)
  - CLAUDE.md baseline saved to `.claude/.baseline/CLAUDE.md`
  - Agent baselines saved to `.claude/agents/.baseline/[name].md`
  - Enables `update.sh` three-way merge immediately after setup — no bootstrap run needed

### Changed
- Template version: 1.15.0 → 1.16.0

## [1.15.0] - 2026-03-24

### Added
- **Configurable agent model** — `/setup-wizard` Question 8 asks preferred model for agents (default: `opus`)
  - All 14 agent templates now use `{{AGENT_MODEL}}` placeholder instead of hardcoded model
  - Stored in `.claude/project-config.json` (`AGENT_MODEL` key)
  - To switch models (e.g., when rate-limited): change `AGENT_MODEL` in `project-config.json` and re-run `/setup-wizard` or edit agent files directly
- **Three-way merge for agents and CLAUDE.md** — `update.sh` now uses `git merge-file` instead of section-merge or full replacement
  - Applies only the actual template diff (baseline → new) to current files
  - Preserves ALL project customizations: wizard-added framework-specific items, custom sections, manual edits
  - Baselines stored in `.claude/agents/.baseline/` and `.claude/.baseline/`
  - First update saves baselines (files unchanged); subsequent updates three-way merge
- **Placeholder validation** — `update.sh` validates no `{{PLACEHOLDER}}` remains after substitution; skips file if unresolved (prevents destroying working agents with raw placeholders)
- **Config validation** — `update.sh` warns when `project-config.json` values themselves contain raw `{{PLACEHOLDER}}` patterns
- `AGENT_MODEL` extraction in `update.sh` migration (reads `model:` from agent frontmatter, defaults to `opus`)

### Changed
- Templates (`.claude/templates/**`) no longer copied to target projects during update — removed from `templateOwned` patterns
- CLAUDE.md moved from section-merge to three-way merge (same approach as agents)
- Removed `sectionMerge` category from manifest (replaced by three-way merge)
- Template version: 1.14.0 → 1.15.0

### Fixed
- **Agents overwritten with raw `{{PLACEHOLDER}}`** — when `project-config.json` had broken values (e.g., `"PROJECT_PATHS": "{{PROJECT_PATHS}}"`), agents were destroyed. Now validates before writing.
- **Templates pushed to target projects** — `.claude/templates/**` was in `templateOwned`, causing raw template files to appear in target projects
- **CLAUDE.md custom sections deleted** — section-merge dropped user-added sections (e.g., `## Figma Plugin Architecture Notes`). Three-way merge preserves them.

## [1.14.0] - 2026-03-24

### Added
- **Commit Convention** section in CLAUDE.md template — consolidates all commit rules (format, attribution, general rules) in one place
- **AI attribution control** — `/setup-wizard` Question 7 asks whether commits should include Claude co-author attribution (`Co-Authored-By` trailer)
  - Default is **No** — no AI/Claude mention in commit titles, body, trailers, or git identity
  - Opt-in: appends `Co-Authored-By: Claude <noreply@anthropic.com>` to every commit
  - Stored in `CLAUDE.md` (Commit Convention > Attribution section) and `.claude/project-config.json` (`COMMIT_ATTRIBUTION` key)
- `COMMIT_ATTRIBUTION` placeholder in CLAUDE.md template, substituted by `/setup-wizard` based on user preference
- All commit-creating commands (`/execute-task`, `/fix`, `/refactor`, `/verify`, `/refresh-docs`) now reference the Commit Convention in CLAUDE.md for format and attribution rules
- `update.sh` migration extracts `COMMIT_ATTRIBUTION` from existing CLAUDE.md; defaults to no-attribution if section not found

### Changed
- Template version: 1.13.0 → 1.14.0

## [1.13.0] - 2026-03-24

### Changed
- `/research` command now displays the full research report in the console before saving
- `/research` now asks the user whether to save the report (previously auto-saved)
- Research reports moved from `specs/research/` to `research/` at project root
- Research file naming changed from `[topic-slug].md` to `DD-MM-YY-[topic-slug].md`
- Storage rules updated to reflect new research location and naming convention

## [1.12.0] - 2026-03-24

### Fixed
- **Critical: Agents broken after update** — `update.sh` copied raw `.template.md` files with unresolved `{{PLACEHOLDER}}` variables (e.g., `{{FRAMEWORK}}`, `{{LANGUAGE}}`) into `.claude/agents/`, destroying project-specific values. Now applies placeholder substitution using `.claude/project-config.json`
- **CLAUDE.md never updated** — was classified as project-owned so `update.sh` skipped it entirely. Template-owned sections (workflow commands, key rules, quality gates, artifact storage, session continuity) now update via section-based merge while project-specific sections (project overview, structure, commands, architecture, agent list) and user-added custom sections are preserved
- **Templates and manifest not synced** — `.claude/templates/**` and `.claude/template-manifest.json` were missing from `templateOwned` patterns, causing stale copies in target projects after update

### Added
- `.claude/project-config.json` — machine-readable file storing all template variable values, written by `/setup-wizard` (Step 3.8), read by `update.sh` for placeholder substitution during updates
- **Section-based merge** strategy in `update.sh` for files with mixed template/project ownership (CLAUDE.md)
  - Template-owned sections updated from latest template
  - Project-owned sections preserved from target
  - User-added custom sections appended
- **One-time migration** in `update.sh` — for existing projects without `project-config.json`, extracts values from `CLAUDE.md` and agent files automatically
- `perl` dependency check in `update.sh` (required for multi-line placeholder substitution)
- `/setup-wizard` Step 3.8 — writes `.claude/project-config.json` after generating all config files

### Changed
- `update.sh` now requires `perl` in addition to `jq`
- Template manifest: `.claude/templates/**` and `.claude/template-manifest.json` moved to `templateOwned`; `CLAUDE.md` moved from `projectOwned` to new `sectionMerge` category
- Command count: 14 (unchanged); template version: 1.11.0 → 1.12.0 → 1.13.0

## [1.11.0] - 2026-03-23

### Added
- `/research` command — lightweight feasibility check for vague ideas before `/specify`
  - Investigates the codebase for related patterns, code, and infrastructure
  - Signal-based external research — only web searches when the idea involves new libraries, integrations, or unfamiliar tech
  - Outputs a concise report to `specs/research/[topic-slug].md` with verdict, approaches, complexity assessment, and concrete next-step recommendation
  - No code modifications, no branches, no commits — purely investigative
  - Sits before `/clarify` in the workflow: `/research` (optional) → `/clarify` (optional) → `/specify`
- `specs/research/` directory in storage rules for research report artifacts

## [1.10.0] - 2026-03-23

### Added
- `/refresh-docs` command — lightweight documentation refresh that targets only changed files
  - Uses git delta to detect source files changed since docs were last updated
  - Invokes tech-writer in new **Refresh Mode** — scoped to changed files, not full codebase scan
  - Supports `--since <commit>`, `--module <name>`, and `--all` (delegates to `/onboard`) flags
  - Captures both committed and uncommitted changes
  - Scoped `git add` (only doc-related files) instead of `git add -A`
  - Includes verification (tsc + lint on changed source files) and memory update phases
- **Refresh Mode** in tech-writer agent template — third operating mode alongside Normal and Onboarding
  - Reads only changed files grouped by module
  - Updates both inline docs (JSDoc/docstrings) and `docs/` folder
  - Cleans up stale doc references for removed public APIs
- `/verify` **"Fix docs now"** triage option — invokes tech-writer directly for documentation-only issues, bypassing `/fix`
  - Documentation gaps flagged during verification now record specific file paths and API names
  - Phase 10.4 summary includes "Fix docs now" count
- `/plan` now reads `docs/` during Phase 0 research — `docs/architecture.md`, `docs/features/*.md`, and `docs/api/*.md` for architectural context
- `/plan` output now includes **Documentation Impact** section — declares which docs will need updating, giving `/execute-task` Phase 5 better targets

### Changed
- `/execute-task` Phase 5 (Documentation Update) **rewritten** with stronger enforcement
  - Structured prompt template for tech-writer invocation (mirrors Phase 3.2's execution agent pattern)
  - New Phase 5.1: Post-Doc Verification — checks `git diff` for new public exports and verifies inline docs exist
  - New Phase 5.2: Commit — doc changes get their own `[WIP]` commit
  - Re-invokes tech-writer if public APIs lack documentation
- `/execute-task` compact preservation lists updated — all 3 instances (moderate, heavy, auto-compact) now include item (6): Phase 5 documentation obligation
- `/execute-task` IMPORTANT RULES: new rule 10 — "Documentation is non-negotiable" (equivalent to skipping verification)
- `/fix` now includes Phase 7.5: Documentation Update (Conditional) — launches tech-writer when public API signatures or user-facing behavior changed
  - Report template includes `**Documentation**:` line
  - Tech-writer receives `docs/` folder structure for context
- `/refactor` now includes Phase 7.5: Documentation Update (Conditional) — launches tech-writer when public API signatures, import paths, or architecture changed
  - Report template includes `**Documentation**:` line
  - Tech-writer receives `docs/` folder structure for context
- `/plan` IMPORTANT RULES: new rule 8 — "Read docs before planning"
- Command count: 13 → 14

## [1.9.0] - 2026-03-23

### Added
- **Cross-task contracts** in `/breakdown` and `/execute-task` — prevents silent error compounding between sequential tasks
  - Each task file now has a `## Contracts` section with `### Expects` (preconditions) and `### Produces` (postconditions)
  - `/breakdown` generates contracts during task creation with concrete, grep-verifiable conditions (exports, interfaces, function names — never line numbers)
  - `/execute-task` Phase 2 verifies preconditions before execution — stops with upstream tracing if a contract is violated
  - `/execute-task` Phase 3.3 verifies postconditions after execution — feeds into the existing self-repair loop on failure
  - Agent prompt includes postconditions as "What This Task Must Produce" so the agent is aware of verification expectations
  - Completion notes and reports now include contract verification results
- **Contract consistency check** in `/breakdown` — after generating all tasks, verifies every "Produces" is consumed by a downstream "Expects" and every "Expects" traces to an upstream "Produces" or existing codebase state
- **Review checkpoint gates** in `/execute-task` multi-task mode — auto-placed pause points at convergence (2+ dependencies), layer boundary crossings (domain → presentation), and high-risk tasks
  - New `**Review checkpoint**: Yes/No` field in task file headers
  - At checkpoints: user sees preceding tasks' contract results and chooses Continue / Review (git diff) / Pause
  - `/breakdown` README.md now includes a Review Checkpoints table
- Storage rules updated with Contracts section and Review checkpoint field in task file format

## [1.8.0] - 2026-03-22

### Added
- **Build verification step** in all workflow commands that run post-execution checks
  - Runs the project's actual build command (e.g., `npm run build`, `next build`, `vite build`) after tsc and lint
  - Catches bundler-specific failures that `tsc --noEmit` alone misses: import resolution, asset processing, SSR/SSG errors, ESM/CJS incompatibilities, unexpected token issues
  - Gated on `Build Command` field in CLAUDE.md — skipped if not configured or set to `N/A`
  - Included in self-repair loop — build errors get auto-fixed (up to 3 attempts) like tsc/lint errors
  - Added to: `/execute-task` (Phase 3.3), `/verify` (Phase 3), `/fix` (Phase 5), `/refactor` (Phase 5)
- `**Build Command**` field in CLAUDE.md template — stores the actual build command (distinct from `Build Tool` which is just the tool name)
- `/setup-wizard` now detects and populates `{{BUILD_COMMAND}}` — auto-detects from package.json `scripts.build`, Makefile, Go/Rust project conventions

### Changed
- Verification reports in all commands now include `Build: PASS/FAIL/SKIP` line
- CLAUDE.md template references updated: `(tsc, lint, ...)` → `(tsc, lint, build, ...)`
- Automated Guards section updated: `tsc + lint` → `tsc + lint + build`

## [1.7.0] - 2026-03-20

### Added
- `/report-bug` command — standalone bug reporting that creates structured bug files in `bugs/`
  - Accepts description, optional `--file` path, optional `--severity` (defaults to Warning)
  - Creates `bugs/NNN-short-description.md` with status lifecycle (Open → In Progress → Fixed)
  - Suggests `/fix bugs/NNN-xxx.md` or `/specify` for resolution
- `bugs/` directory — lightweight bug backlog at project root (parallel to `specs/` and `docs/`)
  - Sequential numbering (001, 002, ...) with kebab-case descriptions
  - Structured format: status, severity, source, description, file(s), evidence, fix notes
  - Created by `/report-bug` (manual) or `/verify` Phase 10 triage (automated)
  - Resolved by `/fix bugs/NNN-xxx.md` which updates status to Fixed
- `/verify` Phase 10: Issue Triage — after presenting the verification report, lets user decide per-issue what to do
  - Per-issue options: "fix now" (chains into `/fix`), "report for later" (creates bug file), "skip"
  - Batch shortcut when >5 issues: "report all remaining for later" to avoid tedious per-issue prompts
  - Bug files created for all triaged items (including "fix now") for tracking regardless of outcome
  - Only activates on NEEDS WORK verdict with Critical/Warning issues
- `/fix` now accepts bug file paths as input: `/fix bugs/003-null-check.md`
  - Phase 1.0 (Input Detection): reads bug file, extracts description and file(s), updates status to In Progress
  - Phase 8.1.5 (Update Bug File): after successful fix, marks bug as Fixed with date and fix notes
  - Existing usage (`/fix "description"`) unchanged — fully backward-compatible

### Changed
- Storage rules updated with Bug Report Rules section (naming, format, lifecycle, creation/resolution)
- Template manifest updated with `report-bug.md` (template-owned), `bugs/**` (project-owned), `bugs/.gitkeep` (copy-if-missing)
- `install.sh` now copies `bugs/` directory to target during installation
- Command count: 11 → 12

## [1.6.0] - 2026-03-19

### Changed
- `/plan` Phase 0 (Research) revamped with signal-based evaluation
  - Codebase research always runs; deep research (web search) only triggers when complexity signals are detected
  - Six signal categories: external libraries, third-party integrations, architectural forks, greenfield patterns, performance constraints, unfamiliar technology
  - Deep research compares 2-3 alternatives with pros/cons for each signal
  - Research output saved to `specs/[feature]/research.md` only when signals found; skipped for simple features
  - Reduces unnecessary web searches on simple features where codebase context is sufficient

## [1.5.0] - 2026-03-19

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
- `/specify` now auto-creates a `spec/NNN-short-desc` branch when invoked on the default branch
  - Incremental numbering based on existing `spec/*` branches (local + remote)
  - Short description (2-3 words kebab-case) generated from the feature description
  - Skips if already on a `spec/*` branch; asks user if on any other non-default branch
- Command count: 9 → 11
- CLAUDE.md template updated with `/fix`, `/refactor`, and `/specify` branch creation in workflow commands section
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