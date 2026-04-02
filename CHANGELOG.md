# Changelog

All notable changes to this template will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.24.1] - 2026-04-02

### Fixed
- **Missing Workflow sections** in implementation agent templates: `db-engineer`, `devops-engineer`, and `migration-engineer` now have `Your Workflow` sections consistent with their peers (backend-engineer, frontend-engineer, mobile-engineer)
- **Missing Output Format** in `qa-engineer` — only analysis/review agent without a structured output template. Now includes a Test Report format matching other review agents
- **Missing Output Format** in `architect` — design deliverables had no predictable structure. Now includes an Architecture Decision format (context, decision, components, dependencies, trade-offs)
- Template version: 1.24.0 → 1.24.1

## [1.24.0] - 2026-04-02

### Changed
- **Docs reading consolidated to `/specify`**: Docs are now read once at `/specify` Phase 1 and embedded into the spec's "Current State" section. `/plan` no longer reads `docs/` — it inherits docs context from the spec. `/execute-task` no longer searches `docs/` broadly — it reads only files referenced in the task's `Context docs` field
  - `/specify` Phase 3 restructured: docs-guided codebase analysis (targeted reads) when docs exist, full exploration fallback when they don't
  - Spec Section 2 explicitly instructs to capture docs context for downstream inheritance
- **New `Context docs` field in task format**: `/breakdown` now embeds specific doc file references per task (max 2), with Doc Reference Rules for when to include them (integration tasks, pattern extensions, API tasks) vs. skip (self-contained tasks)
- **`/execute-task` agent prompt** includes new `Documentation Context` section with content from task-referenced docs
- Template version: 1.23.0 → 1.24.0

## [1.23.0] - 2026-04-01

### Added
- **Tiered agent model system**: Replaced single `AGENT_MODEL` with 3 tiers — Think (opus: architect, api-designer, security-reviewer), Do (sonnet: implementation agents), Verify (sonnet: code-reviewer, ac-verifier, qa-engineer). Configurable per tier in setup wizard Question 8
  - Templates use `{{MODEL_THINK}}`, `{{MODEL_DO}}`, `{{MODEL_VERIFY}}` placeholders
  - `update.sh` auto-migrates old `AGENT_MODEL` config to tier keys on first run
- **2-dimensional agent assignment in `/breakdown`**: Tasks are now classified by nature (design-decision vs. mechanical) before assigning by file layer. Mechanical tasks go to the nearest dependency's agent instead of defaulting to architect
  - Bundling rule: mechanical tasks <30 lines with a single same-agent dependency can be merged into the parent task
- **`backend-engineer` in breakdown assignment table**: Previously had a template but no assignment rule — now assigned to API endpoints, controllers, middleware, services, and server-side logic tasks
- **Always-delegate rule in `/execute-task`**: Rule 1 now mandates every task must be executed via the Agent tool — orchestrator never writes implementation code directly, regardless of task size
- **Mobile support**: New `mobile-engineer` agent template with Flutter/React Native/Swift/Kotlin expertise. Mobile-specific sections added to design-auditor, devops-engineer, performance-analyst, and qa-engineer templates. Setup wizard detects mobile frameworks. Breakdown table includes mobile-engineer row

### Changed
- **Architect scope narrowed**: Assignment table row changed from "Core/domain/data layers, business logic, API, types" to "Domain models, interfaces, contracts, type definitions, architectural decisions" — implementation work now routes to backend-engineer
- **State management with orchestration logic** explicitly assigned to architect (BLoC with business rules, Redux reducers with logic, Pinia stores with computed logic)
- Template version: 1.22.0 → 1.23.0

### Fixed
- `backend-engineer` agent template existed but was unreachable — no breakdown assignment rule mapped to it
- Repository implementation tasks (boilerplate wrapping) over-assigned to architect instead of db-engineer
- DI registration / routing tasks over-assigned to architect instead of frontend-engineer
- Orchestrator skipping agent delegation for "trivial" tasks despite clear instructions

## [1.22.0] - 2026-03-26

### Added
- **Shared command partials**: Extracted conditional and duplicated sections into 4 reusable `_`-prefixed files in `.claude/commands/`:
  - `_recovery.md` — Phase 0 crash recovery logic, shared by `/execute-task`, `/fix`, and `/refactor` (previously duplicated ~50 lines × 3 files)
  - `_context-maintenance.md` — Phase 7.5 session state and context health management, loaded on-demand by `/execute-task`
  - `_multi-task-continuation.md` — Phase 8 queue management and batch execution, loaded only for multi-task runs
  - `_tech-writer-onboarding.md` — Full onboarding scan instructions (Section A), loaded on-demand by `/onboard`

### Changed
- **Command prompt sizes reduced**: `/execute-task` 685→450 lines (-34%), `/onboard` 504→171 lines (-66%), `/fix` 520→471 lines (-9%), `/refactor` 581→531 lines (-9%) — reduces per-invocation cognitive load on Claude
- **Emphasis marker inflation reduced**: Strong markers (CRITICAL/NEVER/MUST/IMPORTANT) across the 4 main execution commands cut from 183→71 total — remaining markers reserved for genuine safety/correctness risks (data loss, workflow corruption, scope violations)
- **IMPORTANT RULES trimmed in `/execute-task`**: 11 rules→6, removing rules that duplicate inline instructions (fail-fast, agent isolation, verify-everything already enforced by their respective phases)
- **Tech-writer Part 2 prompts trimmed**: Document-when/skip-when criteria removed from `/execute-task`, `/fix`, and `/refactor` agent prompts — these already exist in the tech-writer agent file (Part 1) loaded at runtime
- **`/refresh-docs` now loads agent file**: Phase 3 follows the same Part 1 (agent file) + Part 2 (context) pattern used by all other commands, instead of embedding an inline prompt with duplicated rules
- Template version: 1.21.1 → 1.22.0

### Fixed
- Duplicated "Source repo note" paragraph in `/execute-task` Phase 6

## [1.21.1] - 2026-03-26

### Changed
- **Source auto-commit simplified**: Reduced per-command WIP commits from 5-7 (one per phase) to 1 (after verification passes only) — less context pressure, fewer points for Claude to forget
- **Squash logic deduplicated**: Extracted into a shared `Source Repo Auto-Commit` reference section at the top of each command file, replacing ~70 lines of duplicated inline logic with compact references
- **User-confirmed squash**: Source repo squash now proposes `[TICKET-ID] - Description` and asks user to confirm or edit before committing, instead of auto-committing silently
- Template version: 1.21.0 → 1.21.1

## [1.21.0] - 2026-03-26

### Added
- **`ac-verifier` agent template**: New agent that verifies acceptance criteria against a running application. Classifies each AC item as frontend (Chrome MCP), backend (API/curl), or manual, then systematically tests each one and returns a structured pass/fail report with evidence
- **Setup wizard Question 9**: AC verification mode selection — Auto (browser + API with fallback), Browser only, API only, or Off. Includes auto-detection of dev server URL and API base URL from package.json/framework defaults
- **3 new config keys**: `AC_VERIFICATION` (mode), `AC_VERIFICATION_URL` (dev server), `AC_VERIFICATION_API_BASE` (API endpoint base) — stored in project-config.json
- **MCP readiness checks**: `/execute-task` (Phase 1.3), `/fix` (Phase 1.1.5), and `/refactor` (Phase 1.1.5) now probe Chrome DevTools MCP at startup and display an informational warning if not available — non-blocking
- **13 new Chrome DevTools MCP permissions** in settings template: `navigate_page`, `take_snapshot`, `list_pages`, `select_page`, `click`, `fill`, `fill_form`, `wait_for`, `press_key`, `hover`, `list_console_messages`, `list_network_requests`, `get_network_request`

### Changed
- **`/verify` Phase 2 rewritten**: Now supports three paths — ac-verifier agent (when enabled + MCP available), code-reading fallback (when MCP unavailable or mode is "off"), and graceful degradation between them. Adds MCP availability probe and structured result merging with Category column
- **CLAUDE.template.md**: Updated `/verify` description to mention AC verification capability
- Template version: 1.20.0 → 1.21.0

## [1.20.0] - 2026-03-26

### Added
- **Source repo auto-commit in wrapper mode**: All execution commands (`execute-task`, `fix`, `refactor`) now auto-commit source changes to the inner repo with per-phase WIP commits for crash safety
- **Source repo squash**: `/verify` Phase 9.5 squashes all source WIP commits into a single clean commit when verdict is APPROVED. `/fix` and `/refactor` squash at their own Phase 8.1.1. Commit format: `[TICKET-ID] - Description` — ticket ID extracted from source branch name (`[A-Z]{2,}-[0-9]+` pattern), description from spec overview or bug/refactoring context. Falls back to user prompt if no ticket ID found
- **Source repo crash recovery**: Phase 0 in all 3 execution commands now checks and recovers source repo state. WIP marker includes `## Source Repo Checkpoint` section with commit hash and branch name
- **Pre-existing source changes warning**: Phase 2.5/3.1 warns if source repo has uncommitted changes before creating the checkpoint

### Changed
- Wrapper Rule 3 updated across setup-wizard, DEVELOPMENT-STATUS, and README — from "source commits are manual" to "auto-commit both repos with WIP + squash"
- Template version: 1.19.0 → 1.20.0

## [1.19.0] - 2026-03-26

### Changed
- **Tech-writer invocation standardized**: All commands (`execute-task`, `fix`, `refactor`, `verify`) now use the same 2-part prompt pattern — Part 1 loads `.claude/agents/tech-writer.md` (full agent workflow), Part 2 provides task-specific context
- **Documentation phase now mandatory**: `/fix` and `/refactor` Phase 7.5 changed from conditional ("if public API changed, invoke tech-writer") to mandatory — tech-writer always invoked and decides itself whether docs are needed, with explicit skip/document criteria and justification requirements
- **Post-doc verification strengthened** (`execute-task`): Now checks changed signatures on existing exports (not just new exports), detects stale doc references, and validates tech-writer skip justifications against actual diff
- Template version: 1.18.0 → 1.19.0

### Fixed
- **Task "Done When" checkboxes never checked**: `execute-task` Phase 4 had vague "Mark done conditions with `[x]`" — replaced with explicit instruction to change `- [ ]` to `- [x]` in the Done When section
- **Spec AC checkboxes never checked**: `/verify` Phase 7 updated spec status to "Complete" but never marked acceptance criteria checkboxes — added explicit instruction to change `- [ ]` to `- [x]` for passing ACs

## [1.18.0] - 2026-03-25

### Added
- **`/summarize` command**: New command that generates concise, PR-ready feature summaries from spec, plan, tasks, and git history — saves to `specs/[feature]/summary.md`
- **Auto-verify on feature completion**: `/execute-task` Phase 7.5.3 automatically triggers `/verify` when all tasks in the feature are marked Complete — no manual invocation needed
- **Auto-summarize on approval**: `/verify` Phase 9 automatically triggers `/summarize` when verdict is APPROVED
- **Full automated chain**: Last task completion → `/verify` → `/summarize` runs end-to-end without human intervention

### Changed
- Workflow diagrams across all commands now include `→ /summarize` as the final step
- `/verify` Phase 9 APPROVED path chains into `/summarize` instead of suggesting manual commit/PR
- `/execute-task` Phase 8 step 2 defers to Phase 7.5.3 for feature-complete detection
- Template version: 1.17.0 → 1.18.0

## [1.17.0] - 2026-03-25

### Added
- **Language-agnostic verification**: New `Type Check Command` and `Lint Command` fields in CLAUDE.template.md — commands now reference these fields instead of hardcoded `tsc --noEmit` / ESLint, supporting Python/Go/Rust/any language
- **WIP cross-command safety**: `## Command` field in `.claude/wip.md` identifies which command (execute-task, fix, refactor) created it — prevents cross-command recovery confusion with backward compatibility for pre-v3 wip.md files
- **Permissions**: Edit, Write, Bash, Agent added to `settings.template.json` default permissions — workflow no longer requires dozens of manual approval prompts per task
- **Constitution guard**: Added to `/verify` and `/clarify` — all 8 commands that read constitution now check for unpopulated placeholder
- **Framework detection**: Astro, Remix, Deno, Bun auto-detection in `/setup-wizard` Step 1
- **Review cycle cap**: `/refactor` Phase 6 code review now capped at 1 additional cycle (matching `/fix`)
- **Verify task cross-check**: `/verify` Phase 7 now confirms all tasks are Complete before marking spec Complete
- **Fix file overlap warning**: `/fix` Phase 1.2 warns when pending spec tasks target the same files
- **Release template check**: `/release` Phase 5.5 checks CLAUDE.template.md and storage-rules.md for needed updates
- **Squash error handling**: execute-task/fix/refactor now preserve wip.md if the final commit fails after `git reset --soft`

### Changed
- All verification steps in execute-task, fix, refactor, verify, breakdown, storage-rules now reference "Type Check Command from CLAUDE.md" and "Lint Command from CLAUDE.md" instead of TypeScript/ESLint
- CLAUDE.template.md Automated Guards section now language-agnostic ("type check + lint + build")
- CLAUDE.template.md workflow diagram labels corrected (each command has its own label)
- CLAUDE.template.md Crash Recovery section documents `## Command` field and cross-command detection
- CLAUDE.template.md PostToolUse hook description documents lint command asymmetry (hook runs type checker only; linter runs during explicit verification)
- `update.sh` three-way merge: baseline only updated on successful merge — previously updated unconditionally, silently losing template changes after conflicts
- `update.sh` `migrate_project_config()`: now extracts TYPE_CHECK_COMMAND, LINT_COMMAND, PROJECT_MODE with language-based fallback detection
- `update.sh`: replaced bash 4+ `${language,,}` with portable `tr '[:upper:]' '[:lower:]'` for macOS bash 3.2 compatibility
- `install.sh`: now removes `release.md` (template-repo-only command) and cleans `.claude/memory/` (template-repo-specific files) after copy
- `settings.template.json`: corrected context7 MCP tool name from `get-library-docs` to `query-docs`
- `template-manifest.json`: added `research/.gitkeep` to `copyIfMissing`
- `setup-wizard.md`: TYPE_CHECK_COMMAND and LINT_COMMAND added to required keys and example project-config.json
- Template version: 1.16.5 → 1.17.0

### Fixed
- `architect.template.md` line 15: `Te/sting` typo → `Testing`
- `onboard.md`: removed legacy "(Task tool)" parenthetical references

### Removed
- Dead `merge_sections()` Perl function (~100 lines) from `update.sh` — replaced by git merge-file three-way merge

## [1.16.5] - 2026-03-25

### Fixed
- **L1**: Documented agent model strategy in setup-wizard and README — explains why 13 agents use configurable `{{AGENT_MODEL}}` while tech-writer is hardcoded to `sonnet`
- **L6**: Removed undocumented `memory: project` field from runtime-debugger agent template — not a standard Claude Code frontmatter field, no other agent used it

### Removed
- **L3**: Deleted unused `spec.template.md` — `/specify` generates specs from an inline format, never reads this template

### Changed
- Template version: 1.16.4 → 1.16.5

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