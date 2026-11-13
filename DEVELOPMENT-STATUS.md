# AIDevTeamForge — Development Status

## What This Is

A reusable spec-driven development template for Claude Code. Combines a structured intake flow (research → specify → plan → breakdown → execute → review → verify → summarize → finalize) with enforced quality gates, specialized agents, and automated hooks.

## What's Built

### Commands (22 commands + 7 shared partials in `.claude/commands/`)
- `setup-wizard.md` — Interactive project setup, auto-detects stack or interviews for greenfield; saves baselines for three-way merge on first run; detects DEFAULT_BRANCH; conditionally adds Chrome MCP based on AC_VERIFICATION setting
- `constitute.md` — Generates constitution from codebase analysis (existing) or interview (greenfield)
- `onboard.md` — Deep codebase scan for existing projects, generates comprehensive `docs/` via tech-writer agent
- `research.md` — Quick feasibility check for vague ideas; investigates codebase and docs/ for related patterns, signal-based external research (Context7 first for libraries, WebSearch for comparisons), displays full report in console and optionally saves to `research/YYYY-MM-DD-[topic-slug].md`; the report keeps the request (and a named issue's text) verbatim, and the next step is `/specify <report path>` (1.36.0)
- `specify.md` — Creates feature specs with acceptance criteria; clarifies requirements in rounds of up to 5 questions (no artificial limit); auto-creates `spec/NNN-short-desc` branch when on default branch; keeps the user's request verbatim in the spec's `## Request (verbatim)` section (1.36.0)
- `plan.md` — Technical plan between spec and breakdown (architecture, data model, contracts); signal-based research with tightened triggers (not-in-project qualifier); Context7 first for library docs; Phase 2.5 cross-references plan against spec ACs before presenting to user
- `breakdown.md` — Splits plan into sequential atomic tasks in individual files; generates cross-task contracts (Expects/Produces) and auto-places review checkpoints; references shared `_agent-assignment.md` for agent selection
- `execute-task.md` — 6-phase workflow: load context → pre-flight (contracts) → execute (agent → verify → code review) → complete & report → bookkeeping (memory + context + multi-task). Per-task code review reports findings to user. No per-task squash — WIP commits deferred to /finalize
- `review.md` — Expert code review: launches specialist agents (security-reviewer, performance-analyst, qa-engineer) on all changed files. Produces structured review report saved to `specs/[feature]/review.md`. No verdict — findings only
- `verify.md` — Validates all tasks against spec acceptance criteria; cross-task integration check (not full code review — done per-task); incorporates `/review` findings if available; renders verdict (APPROVED/NEEDS WORK/REJECTED); Phase 9 presents issues with batch bug filing — does not invoke /fix; Phase 3.5 intent check (1.36.0, `_intent-check.md`): a fresh auditor sees only the verbatim request, the code diff and the code, never the spec, and each surface the request describes that the change leaves as before is a question to the user
- `summarize.md` — Generates concise, PR-ready feature summary from spec, plan, tasks, and git history; reads DEFAULT_BRANCH from config; wrapper mode source repo handling. Run after `/verify`, before `/finalize`
- `finalize.md` — Feature documentation via tech-writer + feature squash using `git merge-base`; closes `session-state.md` after the squash (1.34.0). Gate-checked: spec must be Complete. The last step before creating a PR
- `fix.md` — Lightweight bug-fix workflow: diagnose → delegate to agent → verify → code review → test → doc update, with runtime-debugger, code-reviewer, qa-engineer, and tech-writer agents; accepts enriched bug file paths from `bugs/`; agent selection via shared `_agent-assignment.md`
- `report-bug.md` — Creates structured bug report files in `bugs/` for later fixing via `/fix` or `/specify`
- `refactor.md` — Focused refactoring workflow: analyze → propose → approve → delegate to agent → verify → code review → test → doc update, with auto-selected agent via `_agent-assignment.md`, code-reviewer, qa-engineer, and tech-writer agents
- `refresh-docs.md` — Lightweight documentation refresh using git delta; invokes tech-writer in Refresh Mode on changed files only
- `security.md` — On-demand security review: targeted (file, directory, uncommitted changes) or full codebase (`--full`). Launches security-reviewer agent with constitution context. Module-based subagents for large codebases. Read-only
- `audit.md` — Standalone adversarial whole-codebase audit for periodic "second opinion" reviews. Launches code-reviewer + architect + qa-engineer + security-reviewer in adversarial mode with a structured Mislogic Hunt Checklist; reads recent `specs/*/review.md` for recurring-issue tracking. Anti-hallucination grounding via verbatim Evidence requirement + Phase 4 validation that re-reads cited files and discards ungrounded findings. Algorithmic-only cross-agent and recurring merging (no LLM similarity judgment). Writes dated reports to `audits/YYYY-MM-DD-audit.md`. Read-only, not auto-committed, NOT part of any workflow chain — invoke manually
- `review-pr.md` (1.32.0) — strict review of a pull request without a spec: code-reviewer constitution/architecture pass plus the `/review` agents, the linked issue as acceptance criteria; code host commands and issue tracker set by the developer in `project-config.json` (Question 11); PR head read from fetched refs, never the working tree; read-only, report in chat
- `conduct.md` (1.31.0) — opt-in autonomous delivery: the main session drives the spec cycle, one subagent per phase, reads only result blocks, parks blocked specs and continues with the roadmap, keeps a local ledger; `disable-model-invocation: true`; since 1.37.0 the spec-gate and the plan-gate run in their own runner, `/summarize` is its own phase on haiku, and the wave runner runs on `MODEL_LIGHT` (missing = `haiku`)
- `release.md` — Meta-command for the template repo itself: automates version bump, changelog, and documentation updates after making changes

Shared partials (`_`-prefixed, loaded on-demand by parent commands; hidden from the `/` menu and the model's skill listing by `disable-model-invocation` + `user-invocable: false` since 1.35.1):
- `_recovery.md` — Phase 0 crash recovery with deterministic hash-based rollback, shared by execute-task, fix, and refactor
- `_context-maintenance.md` — Phase 5.2 session state and context health (execute-task)
- `_multi-task-continuation.md` — Phase 5.3 batch queue management (execute-task multi-task mode)
- `_tech-writer-onboarding.md` — Full onboarding scan instructions Section A (onboard)
- `_agent-assignment.md` — Shared file-layer→agent mapping table, referenced by breakdown, fix, and refactor
- `_autonomous-mode.md` (1.31.0) — rules for conductor runners: interactive points and their autonomous behaviour, self-approval after a clean gate, STOP conditions, runner rules, result block, pull requests
- `_intent-check.md` (1.36.0) — the Request record rules and `/verify`'s intent check: auditor prompt, DIRECT/BROADER handling, autonomous STOP 1 and resume with the user's answers
- `_independent-gate.md` (1.30.0) — fresh-context gate reviewer before the HARD GATE of specify (spec-gate), plan (plan-gate, three lenses) and breakdown (breakdown-gate); one fix loop on Criticals, open ones shown at the gate

Structural-quality layer (1.30.0): `/research` Reuse or Extend; `/specify` audit gate start line, Prior Art, spec type `feature | structural`; `/plan` 1.4–1.6 (Migration, Reuse Map, seams, Copies and Hubs, open themes); `/breakdown` `**Reuse**:` field; `/execute-task` Reuse check, New exports and Copies review inputs; `/fix` Class Sweep; `/review` 4.5 Adoption Check and 4.6 Structural Check; `/finalize` 1.5 escape analysis and 1.6 structural hand-off; `/audit` `--since-last`, structural lens, themes, triage and learning step

### Agent Templates (16 files in `.claude/templates/agents/`)
Each has a `tools:` line (1.37.0), which applies when the agent is launched by its type.
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
- `.claude/storage-rules.md` (moved out of `templates/` in 1.29.0; template-owned) — Full storage conventions for specs, tasks (with contracts and review checkpoint fields), bugs, docs, and the Memory Entry Rules

### Update System
- `update.sh` — Manifest-driven update script with 4 strategies: overwrite (template-owned), three-way merge via `git merge-file` (agents + CLAUDE.md), smart merge (JSON/text), copy-if-missing
- **Three-way merge**: stores baseline snapshots of substituted templates in `.claude/agents/.baseline/` and `.claude/.baseline/`. On update, computes diff (baseline → new template) and applies it to current file — preserves all project customizations while propagating template improvements
- **Placeholder validation**: after substitution, checks for remaining `{{...}}` patterns; skips file if found (prevents destroying agents with broken config values)
- `.claude/project-config.json` — Machine-readable config written by `/setup-wizard`, stores all template variable values (including `TYPE_CHECK_COMMAND`, `LINT_COMMAND`, `COMMIT_ATTRIBUTION`, `MODEL_THINK`, `MODEL_DO`, `MODEL_VERIFY`) for `update.sh` placeholder substitution
- `.claude/template-manifest.json` — Defines file ownership categories and update strategies; self-updates (template-owned)
- One-time migration: extracts config from existing `CLAUDE.md` and agent files when `project-config.json` is missing. Config migrations (extraction, `AGENT_MODEL`, `DEFAULT_BRANCH`) edit a working copy written only after confirmation
- **Template checksums** (1.29.0): `.claude/template-checksums` records the sha256 of every template-owned file (`./update.sh --write-checksums`, last step of `/release`). Each file gets a status (ADD / UPDATE / UNCHANGED / LOCAL / UNKNOWN); LOCAL and UNKNOWN files are backed up to `.claude/.update-backup/<from>-to-<to>-<timestamp>/` before overwrite
- **Forge-owned namespaces** (1.29.0): Forge ships scripts only under `scripts/forge/` and hooks only under `.claude/hooks/forge/`; the rest of `scripts/` and `.claude/hooks/` is project-owned. Hook entries ship as `.claude/hooks/forge/settings-hooks.json` and are merged into `settings.json` per entry (`hookFragments` in the manifest)
- **Installer tests**: `tests/installer/test_install_update.sh`, `tests/scripts/test_gate.sh`, `tests/hooks/test_context_guard.py`, `tests/scripts/forge/` (repo-only)
- **Command size budget** (test in `tests/installer/test_install_update.sh`): a file in `.claude/commands/` stays within 20,000 bytes, because after a compaction Claude Code re-attaches only the start of an invoked command (5,000 tokens). The six files already over it (`audit`, `setup-wizard`, `execute-task`, `fix`, `refactor`, `plan`) have ceilings at their 1.35.1 size and may not grow; lower a ceiling when its file shrinks

### Forge Scripts and Hooks (1.29.0–1.35.0)
- `scripts/forge/gate.sh` — runs a check with its output in `.claude/.gate-logs/`, prints only the result and first errors; `-C <dir>` relative to the project root (1.34.0); machine-wide slots for heavy runs, `FORGE_GATE_SLOT_DIR` to share them across clones
- `.claude/hooks/forge/context-guard.py` — PostToolUse hook; wind-down at 75 %, stop at 85 % of `FORGE_CONTEXT_WINDOW`
- Quality scripts (1.30.0, Python 3.9+, stdlib): `quality_profile.py` (loader/validator of `.claude/quality-profile.json`; `init`, `validate`, `consumers`, `scopes`), `ratchet.py`, `count-tools.py`, `audit-gate.py`, `hub-files.py`, `new-exports.py`, `check-canonical-sources.py`, `check-enforcement-map.py`, `check-task-evidence.py`, `check-decision-records.py`. Unset or missing binding = the command's manual form (one line, exit 0); wrapper mode inspects the Source Root repository. Tests in `tests/scripts/forge/`
- Autonomous delivery (1.31.0): `.claude/hooks/forge/push-guard.py` (PreToolUse, G1–G7, active only with `DELIVERY_MODE: autonomous`), `scripts/forge/wave-preflight.py` (pre-wave check), `scripts/forge/spec-cost.py` + `model-prices.json` (tokens, cost, wall time per spec and phase; subagent runs attributed by their prompt's `Branch:` field since 1.35.0). Tests in `tests/hooks/` and `tests/scripts/forge/`
- Nested-wait guard (1.33.0): `.claude/hooks/forge/nested-wait-guard.py` (PreToolUse `SubagentHandback`, autonomous mode only) refuses a runner's hand-back while its launched work is pending; `scripts/forge/nested-pending.py` and `wave-preflight.py --runner` give the conductor the same check
- `.claude/checklists/` (1.30.0, copy-if-missing, project-owned) — spec-gate, plan-gate, breakdown-gate, task-review, test-lens; `**Gate**: on | off`; grown by `/finalize` and `/audit` learning steps; field items added in 1.35.0 reach existing installs only by hand

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
20. **Waves and a batch gate instead of a full build per task** (1.29.0) — `/breakdown` groups tasks into waves of 2–4; in a batch each task keeps type check, lint and affected tests, and the full build plus the full test suite run once per wave. A failed batch gate puts the covered tasks back to In Progress
21. **Consolidation over minimal change** (1.29.0) — a copy is never the minimal change: a change that touches copied logic reuses or extracts the shared definition; agents record a Reuse check per new export and the code reviewer treats semantic duplicates as Critical
22. **Field changes from a testbed project** (1.29.0) — 1.29.0 is the first of three releases (1.29 foundation and fixes, 1.30 independent gates and structural quality, 1.31 opt-in autonomous delivery) that upstream generic harness changes proven in a real project; project-specific parts stay out
23. **Independent gates before user approval** (1.30.0) — the author never reviews its own artifact: a fresh agent (a different model where possible; since 1.37.0 the breakdown-gate on sonnet and the plan-gate architect lens on `MODEL_ARCHITECT_LENS`) works to a project-owned checklist before each HARD GATE; the user still approves. Checklists learn from escapes (`/finalize`) and audit root causes (`/audit`)
24. **One project binding, manual form when unset** (1.30.0) — every project-specific value of the structural mechanisms lives in `.claude/quality-profile.json`; commands and scripts name concepts only, and an empty key runs the same step by hand, so the mechanisms install on any stack and grow with the project
25. **Audit gate on by default** (1.30.0) — an audit is due after every 3 finished features, while patterns are still cheap to fix; the user may start a spec anyway with a recorded reason. The issue tracker is optional
26. **Autonomy is opt-in and earned per gate** (1.31.0) — interactive delivery stays the default; `/conduct` self-approves a HARD GATE only after its independent gate ran clean, and keeps the user for STOP conditions and merges. The push guard is the safety net that makes this acceptable
27. **A thin conductor** (1.31.0) — the main session never reads sources or artifacts; one subagent per phase, result blocks only, a local ledger that is never committed (it would otherwise land in squashes and open pull requests)
28. **Hosts and trackers are configuration, not code** (1.32.0) — `/review-pr` and `/research` name no host or tracker in their steps: the developer supplies the PR commands (presets for GitHub and GitLab) and the tracker (`jira` via a named MCP server, `github`, `none`); an unset key stops the command or skips the step and says so, never falls back to a guess
29. **A runner rule that failed as text becomes a hook** (1.33.0) — "wait for nested agents" was written down and still broken in field use; the nested-wait guard checks it from the runner's own transcript, fails open, and leaves the real STOP and a loop guard as exits

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
