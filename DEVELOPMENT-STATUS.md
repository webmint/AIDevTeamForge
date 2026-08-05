# AIDevTeamForge — Development Status

## What This Is

A reusable spec-driven development template for Claude Code. Combines a structured intake flow (research → specify → plan → breakdown → execute → review → verify → summarize → finalize) with enforced quality gates, specialized agents, and automated hooks.

## What's Built

### Commands (18 commands + 5 shared partials in `.claude/commands/`)
- `constitute.md` — Generates constitution from codebase analysis (existing) or interview (greenfield)
- `research.md` — Bug + enhancement investigation. Hard-gated on the 4-command setup chain. Phase 0 rubric (6 dimensions, helper-owned state at `.devforge/research-state.json`) clarifies the symptom; Phase 1 runs orchestrator-inline (no subagent dispatch) using the codebase-memory-mcp graph + `docs/` corpus with mandatory `search_graph` → `search_code` fallback chain, a parallel-pattern sweep over the primary file, and ≥2 falsifiable hypotheses; Phase 2 composes a structured report (mode-aware verdict, optional structured root cause for bugs, optional runtime-probe block, approaches with hypothesis citation, complexity); Phase 3 saves to `research/YYYY-MM-DD-<topic-slug>.md` with a copy-pasteable `/specify` handoff section; Phase 2.4c caller enumeration is **mode-independent** (plan 67 — verify check 8 rejects an empty fix-path-helper list on EVERY run, bug or enhancement, unless the auditable `record-no-shared-callers-justification` escape is recorded; bug-only runtime phases 2.4d/2.5b stay mode-gated), and the enumeration rides the research handoff as a typed `caller_enumeration` field `/plan` consumes
- `discover.md` — Greenfield-feature discovery (parallel to `/research`, but pre-`/specify` for features with no existing related code). Same 4-command setup-chain hard gate. Phase 0 pre-flight (setup-chain artefact check + CBM index refresh) + topic capture with fresh-every-run state reset. Phase 1 scopes the idea across 8 rubric dimensions (`functional_scope`, `users`, `inputs_outputs`, `integration_points`, `constraints`, `non_goals`, `success_criteria`, `edge_cases`) via helper-owned state at `.devforge/discover-scope.json`; bounded turns (3 follow-ups/dim), pre-rubric `references` capture, helper-side direct-conflict detection + LLM-side drift classification, `[NEEDS CLARIFICATION]` gap markers on accepted partial exit. Phase 2 runs three sequential orchestrator-inline steps (no subagent dispatch): Step 2.0 project-wide internal canonical-pattern search (extracts capability verbs from `functional_scope`, scans via `search_graph` + `search_code`, records `internal:<path>` prior-art BEFORE web survey), Step 2.1 web survey (WebSearch + Context7 + WebFetch) narrowed to GAP capabilities, Step 2.2 fit-check (docs layer + CBM structural chain) reconciling user-belief vs codebase-reality with mandatory `--module-path` grounding from CBM result rows. Phase 3 composes the report (summary, prior art, integration surface, fit assessment, 2-3 design options, build-vs-buy, derisk plan, constitution constraints) at `.devforge/discover-report.json` with verdict-flip rule (Strained/Misfit fit OR Major-refactor effort → `Reconsider` unless override recorded) AND invariant G cite-rule (when `internal:` prior-art exists, `recommended_option.rationale` MUST cite at least one internal path). Phase 4 saves to `discover/YYYY-MM-DD-<topic-slug>.md` with a copy-pasteable `/specify` handoff section when verdict allows proceeding
- `specify.md` — Authors a 9-section feature spec at `specs/NNN-<feature-name>/spec.md`. Hard-gated on the 4-command setup chain. Phase 0 preflight (helper `preflight` checks `.devforge/init.yaml` + `docs/architecture.md` + `.devforge/configure.yaml` + `constitution.md` + populate-guard literal) + branch detection + `.claude/session-state.md` reset. Phase 1 reads 7 mandatory input sources (constitution + MEMORY + CLAUDE + docs/ + research/ + discover/ + specs/) via `record-input-read` with path-based `source_origin` auto-tagging (`discover` / `research` / `prior_spec` / `context`); no content parsing. Phase 1.5 REQUIRED INTERMEDIATE OUTPUT — `record-finding` per item with ≥3 bullets or `mark-source-no-items-relevant` marker; `findings-finalize` gates Phase 2. Phase 2 surfaces decision points across 7 categories (`scope_boundaries`, `existing_behavior`, `data_flow_state`, `edge_cases`, `ui_ux_details`, `breaking_changes`, `tooling_configuration`) with C-strict mode detection (`DEVFORGE_AUTO_MODE=1` env / `--auto` flag / `<system-reminder>` substring) — auto path uses `set-dp-default-applied`, interactive uses `set-dp-answer` after AskUserQuestion or markdown fallback; per-DP 3-follow-up turn cap auto-defers to `[exceeded cap]` open-question; `rubric-coverage` + `dp-finalize` gate all 7 categories ∈ `{Clear, NoDPInCategory}`. Phase 3 classifies into 5 spec types (`migration_tooling` / `feature_addition` / `bug_fix` / `refactor` / `greenfield_feature`) with `/discover` path pre-seeding `greenfield_feature`; per-type `MANDATORY_READS_BY_TYPE` slot tables enforced by `verify-mandatory-reads`; CBM / Glob / Grep discretionary exploration. Phase 4 renders the 9-section spec via setters with 7-subsection AC categorization, EARS-validated `statement` (5 variants — §5.1 + §5.7 Ubiquitous-only + verification-command REQUIRED), Phase 1.5 coverage rule (`verify-coverage` — every finding landed in AC / Constraint / OOS / Risk), `verify-ac-subsection-coverage`, `verify-ac-shape` (per-variant regex), `verify-numerical-consistency`, non-blocking `check-constitution-compliance`. Phase 5 hard-gate approval via deterministic `render-summary` 4-bullet block + `render-plan-handoff` block. State at `.devforge/specify-state.json`. Downstream `resolve-open-question` callable by `/plan` + `/breakdown` for audit-trail. Auto-creates `spec/NNN-<short-desc>` branch when on default. **Requires approval before `/plan`.**
- `spec-check.md` — **Optional, opt-in** spec-tier SMT consistency prover (`62-SMT-REQUIREMENTS-CONSISTENCY-PLAN.md`, between `/specify` and `/plan`). Formalizes each acceptance criterion into a typed constraint IR via the read-only `spec-formalizer` agent (a fixed 2-pass quorum keeps the verdict reproducible), runs the Z3 SMT solver over the conjunction, and recommends CONSISTENT / REVISE-SPEC / DISMISS — the human checks the TRANSLATION and owns the verdict. Two-layer report at `specs/[feature]/spec-check.md` + a verdict-gated backward `spec-check-seed.json` (consumed by `/specify`). Honest scope: a consistency prover, not a mind-reader (catches ACs contradicting each other, not intent). Needs `z3-solver` (opt-in pip dep; neither `install.sh` nor `update.sh` installs it). Helper `spec_check_helper` (8 verbs) + `_spec_check/` subpackage
- `plan.md` — Technical plan between spec and breakdown (architecture, data model, contracts); signal-based research with tightened triggers (not-in-project qualifier); Context7 first for library docs; Phase 2.5 cross-references plan against spec ACs before presenting to user; the mandatory Phase 1.3 architect consult names pure-builder targets (property-test lane, plan 66) and classifies shared-code restrictions per the constitution's Narrowing rule, sourcing caller lists from the research handoff's carried caller enumeration with a per-restricted-helper freshness `trace_path` cross-check (plan 67)
- `breakdown.md` — **Redesigned (`09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md`, 2026-05-25)** — aligned with the redesigned chain. Consumes the approved plan's sibling `plan-handoff.json` (helper `breakdown_helper read-plan-handoff`); 11 phases mirroring `/plan` (plan resolution → upstream-handoff consume → status flip → context → deep file analysis → REQUIRED Findings-from-Plan enumeration → mandatory+scoped architect decomposition consult → write tasks → contract-chain + AC-coverage forcing-function gates → hard-gate approval → finalize). Emits human `tasks/NNN-*.md` (storage-rules format) + a structured `breakdown-handoff.json` (schema `_breakdown/handoff_schema.py`, `handoff_kind="breakdown"`) — producer side of the breakdown→`/execute-task` handoff (consumer conforms when built). Agent-assignment table **inlined** into the command (sole owner; the two standalone fast-path commands were dropped in the 2.0 cleanup — see plan 21). Helper `breakdown_helper` (13 verbs, 232 tests) owns all structural emission; a fifth Phase 3.5 integrity gate `verify-property-coverage` (+ `finalize-handoff` chokepoint) hard-halts when a `/plan`-declared pure-builder target has no covering qa-engineer property-test task (plan 66)
- `execute-task.md` — 6-phase workflow: load context → pre-flight (contracts) → execute (agent → verify → code review) → complete & report → bookkeeping (memory + context + multi-task). Per-task code review reports findings to user. No per-task squash — WIP commits deferred to /finalize
- `review.md` — Expert code review: launches specialist agents (security-reviewer, performance-analyst, qa-reviewer) on all changed files. Produces structured review report saved to `specs/[feature]/review.md`. No verdict — findings only
- `verify.md` — Proves spec acceptance criteria PASS/FAIL/PARTIAL + runs the assembled-feature mechanical checks (type-check/lint/build/test together, report-only) + folds in `/review` findings if available; renders the single verdict (APPROVED/NEEDS WORK/REJECTED); on APPROVED flips the spec to Complete + ticks the passed AC boxes; Phase 9 presents issues with batch bug filing on NEEDS WORK. Does NOT re-review — cross-task code-quality reasoning is `/review`'s job
- `summarize.md` — Generates concise, PR-ready feature summary from spec, plan, tasks, and git history; reads DEFAULT_BRANCH from config; wrapper mode source repo handling. Run after `/verify`, before `/finalize`
- `finalize.md` — Feature documentation via tech-writer + feature squash using `git merge-base`. Gate-checked: spec must be Complete. The last step before creating a PR
- `report-bug.md` — Creates structured bug report files in `bugs/` for later fixing via `/specify`
- `refresh-docs.md` — Lightweight documentation refresh using git delta; invokes tech-writer in Refresh Mode on changed files only
- `audit.md` — Standalone adversarial whole-codebase audit for periodic "second opinion" reviews. Launches code-reviewer + architect + qa-reviewer + security-reviewer in adversarial mode with a structured Mislogic Hunt Checklist; reads recent `specs/*/review.md` for recurring-issue tracking. Anti-hallucination grounding via verbatim Evidence requirement + Phase 4 validation that re-reads cited files and discards ungrounded findings. Algorithmic-only cross-agent and recurring merging (no LLM similarity judgment). After grounding/merge, a refutation / cross-examination stage (PHASE 4.2.5) routes each finding to a non-author reviewer that cross-examines it (default-dismiss unless the defect is demonstrated from quoted code); the report then separates CONFIRMED findings (headline) from DISMISSED + low-stakes uncertain findings (a Dismissed / Worth a Glance appendix), with high-stakes `security` / constitution-violation findings the refuter cannot confirm surfaced in the headline flagged `[CONTESTED]`. Writes dated reports to `audits/YYYY-MM-DD-audit.md`. Read-only, not auto-committed, NOT part of any workflow chain — invoke manually
- `release.md` — Meta-command for the template repo itself: automates version bump, changelog, and documentation updates after making changes

Shared partials (`_`-prefixed, loaded on-demand by parent commands):
- `_recovery.md` — Phase 0 crash recovery with deterministic hash-based rollback for execute-task (legacy draft; the live crash-recovery contract is owned by `src/commands/implement/references/crash-recovery.md`)
- `_context-maintenance.md` — Phase 5.2 session state and context health (execute-task)
- `_multi-task-continuation.md` — Phase 5.3 batch queue management (execute-task multi-task mode)
- `_agent-assignment.md` — File-layer→agent mapping table; `/breakdown` is its sole referrer and inlines its own copy per `09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md` OQ-3

### Agent Templates (17 files in `.claude/templates/agents/`)
Always included: `code-reviewer`, `qa-engineer`, `qa-reviewer`, `runtime-debugger`, `tech-writer`, `security-reviewer`
By project type: `frontend-engineer`, `backend-engineer`, `architect`, `mobile-engineer`
By detected stack: `db-engineer`, `devops-engineer`, `design-auditor`, `api-designer`, `performance-analyst`, `migration-engineer`
By config: `ac-verifier` (when `AC_VERIFICATION != "off"`)

`install.sh` (via `generate-agents.py`) generates the full agent set from `src/agents/*.md`; `/configure` then prunes `.claude/agents/` to the project's natures based on detected stack and config (including AC verification mode).

### Supporting Templates (in `.claude/templates/`)
- `CLAUDE.template.md` — Main project config (including Type Check Command and Lint Command fields), workflow commands, key rules (Always/Never lists), commit convention (format + attribution)
- `constitution.md` — Pre-populated universal rules + project-specific placeholders. Placed at project root by `install.sh` (presence-guarded for brownfield); `/configure` substitutes the header placeholders (name/type/framework/language/workspace/source-root, plus error-handling and testing summaries); `/constitute` fills the `[project-specific]` body sections later. Renamed from `constitution.template.md` as part of the "install places, `/configure` populates" alignment.
- `settings.template.json` — PostToolUse type-checking hook + default permissions (Edit, Write, Bash, Agent, read tools, task tools, MCP tools)
- `spec.template.md` — Feature spec template with 10 sections
- `storage-rules.md` — Full storage conventions for specs, tasks (with contracts and review checkpoint fields), bugs, and docs

> Persistent memory scaffold now lives at `src/devforge/memory.md` (4-section starter installed verbatim into `.devforge/memory.md`; seeded during setup). The richer `memory.template.md` with placeholders was removed as orphaned code — nothing consumed it.

### Update System
- `update.sh` — Manifest-driven update script with 4 strategies: overwrite (template-owned), three-way merge via `git merge-file` (agents + CLAUDE.md), smart merge (JSON/text), copy-if-missing
- **Three-way merge**: stores baseline snapshots of substituted templates in `.claude/agents/.baseline/` and `.claude/.baseline/`. On update, computes diff (baseline → new template) and applies it to current file — preserves all project customizations while propagating template improvements
- **Placeholder substitution**: delegates to `configure_helper substitute-file` (the single source of truth shared with `/configure`'s renderer — knows the singular↔plural aliases and composed `PACKAGE_STACKS` table); the merge gates on the verb's exit code rather than a raw `{{...}}` grep, so a legitimate `{{UPPERCASE}}` identity passthrough no longer false-skips a file while genuinely unresolved placeholders still skip it (prevents destroying agents with broken config values)
- `.devforge/project-config.json` — Machine-readable config written by `/configure`, stores all template variable values (including `TYPE_CHECK_COMMAND`, `LINT_COMMAND`, `COMMIT_ATTRIBUTION`, `MODEL_THINK`, `MODEL_DO`, `MODEL_VERIFY`) for `update.sh` placeholder substitution
- `.claude/template-manifest.json` — Defines file ownership categories and update strategies; self-updates (template-owned)
- Config rebuild: when `.devforge/project-config.json` is missing, the update script rebuilds it from `.devforge/configure.yaml` via `configure_helper render-config` before substituting (replaces the retired `CLAUDE.md`-scraping migration)
- Constitution-drift check: `update.sh` (before the equal-version bail) and `install.sh`'s brownfield "leaving as-is" branch source `scripts/constitution-drift-check.sh` to compare an already-constituted target's universal constitution sections + forcing-function config keys against the canonical defaults; WARN-only and fail-soft (never mutates `constitution.md`/`constitute.json`), telling the user to re-run `/constitute`; greenfield silent-skips

### Other
- `README.md` — Full documentation with installation, workflow, pre-populated rules section
- `specs/` — Empty specs directory with .gitkeep
- `bugs/` — Empty bugs directory with .gitkeep (bug backlog for `/report-bug` and `/verify` triage)
- `research/` — Empty research directory with .gitkeep (research reports from `/research`)
- `discover/` — Empty discovery directory with .gitkeep (discovery reports from `/discover`)

### Wrapper Mode
- `/init-forge` detects nested git repos at depth 1 and resolves the workspace mode (standalone vs wrapper)
- `SOURCE_ROOT` variable propagated through CLAUDE.md → all commands read it
- All commands scope source scanning to the Source Root path
- Git auto-commits apply to both repos — wrapper gets workflow commits, source repo gets per-task WIP commits squashed into one clean commit (`[TICKET-ID] - Description`) at `/verify`
- `/execute-task` Phase 3.3 verifies no Claude artifacts leak into the inner project
- `/init-forge` detects nested git repos and confirms adding the inner folder to `.gitignore` during STEP 0
- CLAUDE.md template has conditional `{{WRAPPER_MODE_SECTION}}` (omitted for standalone)
- Memory template tracks `{{WORKSPACE_MODE}}` (standalone/wrapper) and `{{SOURCE_ROOT}}`

### Forcing Functions (consumer-side detectors backing constitution rules)
- `constitute_helper verify-magic-enum` / `verify-cross-layer-imports` / `verify-any-leak` — mechanical detectors that back `src/constitution.md` §3.5 (Universal Code Quality — magic-enum + `any`-annotation rules) + §3.6 (Design Principles — layer-boundary rule). Substrate at `src/devforge/lib/_constitute/_forcing_functions/`; each rule gated by its `forcing_functions.<rule>.enabled` block in `.devforge/constitute.json`. Exit 2 on findings.
- `constitute_helper set-forcing-functions --rule <name> --enabled true|false [per-rule flags]` — writes/updates a `forcing_functions.<rule>` block; called three times during `/constitute` Section 3.5 (one per rule). `list-forcing-functions [--enabled] [--format key|verb]` — machine-readable rule enumeration consumed by the pre-commit hook.
- `cmd_verify` (the existing `/constitute` verify step) validates each enabled `forcing_functions.<rule>` block against per-rule required-fields in `_constitute/_schema.py`.
- Optional pre-commit hook template at `src/git-hooks/pre-commit-forcing-functions.sh` — `install.sh` copies it to `.devforge/templates/git-hooks/`; `/constitute` Phase 6.4 prompts the user to opt in (copy to `.git/hooks/pre-commit` + `chmod +x`). Silently no-ops when config or helper is absent.

## Key Design Decisions

1. **User's workflow is primary** — spec-kit ideas adapted to serve hard gates + agents, not replace them
2. **Hard gates at every phase transition** — spec, plan, breakdown all require explicit user approval
3. **Per-feature storage** — everything in `specs/NNN-feature-name/` with tasks as individual numbered files in `tasks/` subfolder
4. **Sequential numbering** — features: 001, 002...; tasks within feature: 001, 002...
5. **All agents as templates, `/configure` prunes** — `install.sh` generates the full agent set from `src/agents/*.md`; `/configure` prunes `.claude/agents/` to the project's natures
6. **Universal constitution rules pre-populated** — SOLID, DRY, KISS, error handling, code quality, workflow rules all built-in; `/constitute` preserves these `[universal]` sections verbatim and only populates `[project-specific]` sections
7. **Two-layer documentation** — implementing agents write inline docs (JSDoc/docstrings) as part of code; code-reviewer verifies inline docs per-task; tech-writer generates feature-level docs in `docs/` at `/finalize` time (once per feature, not per task). `/refresh-docs` catches stale docs via git delta
8. **Greenfield support** — all commands work for empty/new projects
9. **Check before build** — must search codebase for existing utilities before creating new ones
10. **Doc generation for existing projects** — `/generate-docs` builds the `docs/` knowledge base (concern → package → project tiers) for all agents
11. **Wrapper mode for client-invisible AI** — template wraps around existing project folder; zero Claude traces in the client's repo
12. **Cross-task contracts prevent silent drift** — each task declares Expects/Produces; preconditions catch upstream semantic errors before they compound, postconditions verify the task delivered what downstream tasks need
13. **Configurable AI attribution** — commits default to no Claude/AI mention; opt-in via the `COMMIT_ATTRIBUTION` config field that `/configure` writes. Rule stored in CLAUDE.md and enforced by all commit-creating commands
14. **Tiered agent models** — agents use 3 model tiers: Think (opus — architect, api-designer, security-reviewer), Do (sonnet — implementation agents), Verify (sonnet — review/test agents). Configurable via `/configure` (`MODEL_THINK`, `MODEL_DO`, `MODEL_VERIFY` in project-config.json)
15. **Three-way merge for updates** — `update.sh` uses `git merge-file` with baselines to apply only template diffs, preserving all project customizations (setup-added items, custom sections, manual edits)
16. **AC verification is opt-in and project-conditional** — `/configure` asks if AC should be verified via browser (Chrome MCP), API calls, or code reading (the `ac_verification_mode` config field). Chrome MCP only installed for auto/browser-only projects. `/verify` Phase 2 launches the ac-verifier agent when enabled, with graceful fallback to code reading
17. **Per-task code review, feature-level review + verdict at epic level** — code-reviewer runs after each `/execute-task` task (findings reported to user: address/continue/stop). `/review` owns the feature-level cross-task review (findings only); `/verify` owns the verdict — AC verification + assembled mechanical checks + the APPROVED/NEEDS WORK/REJECTED decision — and does NOT re-review
18. **Language-agnostic agent templates** — type safety rules use a `{{TYPE_SAFETY_RULES}}` placeholder that `/configure` substitutes based on detected language. No hardcoded TypeScript-specific items. Agent templates use `Inline docs` not `JSDoc`

### Context Maintenance (Phase 5.2)
- `/execute-task` includes Phase 5.2: Context Maintenance after each task
- Writes a fixed-size (~40 line) sliding window to `.claude/session-state.md` with current progress, recent decisions, and modified files
- Three-tier context health check: light (no action), moderate (optional /compact), heavy (strongly recommend /compact)
- Session state is gitignored — it's a runtime artifact, not project state
- CLAUDE.template.md updated with rule 13 (session state) and Session Continuity section

### Crash Recovery (Phase 0 + WIP Checkpoints)
- `/implement` creates a WIP marker (`.devforge/wip.md`) and git checkpoint commits during execution
- Recovery Check (owned by `src/commands/implement/references/crash-recovery.md`) detects interrupted sessions and offers 4 options: resume, rollback+retry, rollback+skip, keep manual. WIP markers include a `Command` field identifying which command was interrupted, to prevent cross-command recovery confusion
- Git `[WIP]` commits preserve partial work at each phase. For `/implement`: WIP commits accumulate across tasks and are squashed by `/finalize` using `git merge-base`
- All workflow commits use scoped `git add` (specific files only, never `git add -A`) to prevent accidentally committing secrets or unwanted files
- `wip.md` is gitignored — only exists during active task execution
- In wrapper mode, WIP marker includes `## Source Repo Checkpoint` section; Phase 0 recovery also rolls back source repo WIP commits

## What's Left / Potential Enhancements

- Test the full flow end-to-end on an actual project
- The `docs/` folder structure might need adjustment per project type
- Consider adding a `/commit` command that summarizes changes
- Consider a `/status` command to show current feature progress
- The setup chain could detect more frameworks/tools
- ~~Agent templates use `{{PLACEHOLDER}}` variables — setup must replace all of them~~ **FIXED: `/configure` and `update.sh` apply placeholder substitution using `.devforge/project-config.json`**
- ~~`constitution.md` stub generation during setup — template content TBD~~ **FIXED: `install.sh` copies the template with sentinel strings preserved; `/configure` substitutes the resolved headers**
- ~~`/clarify` command overlap with `/specify`~~ **RESOLVED: `/clarify` removed, clarification absorbed into `/specify` Phase 2**
- Consider spec validation agents (R1 from competitive analysis) — plan-spec cross-reference already added, spec validation is lower priority with per-task code review as safety net
- ~~Consider if tech-writer should also update inline code docs (JSDoc/docstrings) or just `docs/` folder~~ ~~**DECIDED: both. Tech-writer updates inline docs (JSDoc/docstrings) AND `docs/` folder.**~~ **REVISED (plan 21): tech-writer is verify-only for inline docs — the implementing agent writes them; tech-writer flags gaps and writes only `docs/`.**
