# Setup-Wizard Redo Plan

This is the execution plan for redoing the `/setup-wizard` command from scratch on top of the established framework discipline. The current setup-wizard accumulated by addition (multiple iterative steps each touching local sections); the redo writes it once, cleanly, with full forward-knowledge of every dependency and test-first discipline for all helper code.

## Why redo

Three audit cycles over multiple sessions surfaced 17+ findings — half cross-reference inconsistencies (residue of local-only edits), half code bugs (helper functions written without realistic-input tests). Both classes are preventable under tighter discipline. The cost of redo (this plan + a sequence of small commits) is less than the cost of debugging the unreliable foundation forever.

## When resuming work

Open this file first. The state of the redo is tracked in two places:
- **`## Execution log`** at the bottom of this file — most recent commit per chapter, current chapter in progress
- **`git log --oneline | grep 'setup-wizard-redo'`** — chronological commit trail

Every commit message during the redo prefixes with `setup-wizard-redo: <chapter>: <action>` so the trail is greppable.

---

## Section 1 — Frame recap (architectural decisions in force)

The redo is built against this architectural frame, all of which is established in CLAUDE.md / memory / committed code. **Do not re-litigate these during the redo** — they're decided.

### Discipline rules (CLAUDE.md "Meta-discipline" + "Code & spec discipline")
- **Default-argue:** engage critically with every non-trivial request without being asked
- **Zero-escape-hatch:** no rule contains OR / if / except / unless / use-judgment clauses
- **No-underspecification when delegating:** every agent brief includes goal, integration context, constraints, edge cases, success criteria, what NOT to do
- **Test-immediately-after-write for python helpers:** every function gets its own test that runs in the same turn, real-fixture round-trip via the producer for parsers
- **Sentence-level hallucination check for spec docs:** every sentence verifiable now / mechanically true / explicit forward-ref
- **Cross-check after every change:** grep for affected identifiers across all spec + code files; dangling references are part of the same change
- **Pre-empt future-session hallucination:** before declaring done, verify a fresh future session would not be misled
- **Verify Claude Code authoring conventions via instruction-author (which fetches docs.claude.com):** no training-knowledge-only convention claims; no agent OR docs escape

### Agents (project-level, in `.claude/agents/`)
- **`python-engineer`** — writes helper functions + their tests as one inseparable unit (Read, Write, Edit, Bash, Grep, Glob; opus)
- **`python-reviewer`** — reviews function + tests for logic, edge cases, cross-refs, future-hallucination (Read, Bash, Grep; opus)
- **`instruction-author`** — writes spec/command/agent markdown; knows AIDevTeamForge conventions; fetches docs.claude.com via WebFetch for any Claude-Code-integration uncertainty (Read, Write, Edit, Grep, Glob, WebFetch; opus)
- **`instruction-reviewer`** — reviews spec/command/agent markdown for logic, cross-refs, sentence-level hallucination (Read, Grep, Glob, WebFetch; opus)

### Helper-owns-shape principle
Helpers (`scripts/lib/*.py`) own file structure, validation, atomic writes, and deterministic output. LLMs compose only values. Spec text describing helper interaction must use setter/getter language, not "read file X then substitute Y."

### AskUserQuestion contract (defined in setup-wizard main.md)
- Every interactive question (literal `{{ask}}` markers AND prose-described questions) invokes the AskUserQuestion tool
- 2-4 options per call; "Other" auto-injected by tool, never explicit
- `multiSelect: true` for multi-pick
- Free-text-only or >4-option questions bypass the tool (use plain `>` blockquote prompts)
- Recommended option goes first with `(Recommended)` suffix
- One question per AskUserQuestion call (except Q10's batched 3 tier picks)

### Phase structure (preserved from current setup-wizard)
- **Phase 0:** Reset (helper state cleanup before any setters fire)
- **Phase 1:** Detection (read-only scan + `detect_report compose`)
- **Phase 2:** Questions (interactive Q0-Q11)
- **Phase 3:** Population (LLM composes values via `wizard_render` setters; defers compose to Phase 4)
- **Phase 4:** Agent curation (selection + `apply-agents` + `wizard_render compose`)
- **Phase 5:** Summary (user-facing recap)

### State / file conventions
- Helper state: `.devforge/.<helper>-state.json` (ephemeral; deleted on compose success)
- LLM-written intermediate file: `.devforge/.agents-apply.json` (ephemeral; deleted by compose after consumption)
- Setup completion marker: `.devforge/setup-complete` (written by `wizard_render compose`)
- All wizard-output files live at outer-root in wrapper mode (never inside SOURCE_ROOT)
- Atomic writes: temp file + os.replace; never partial-write artifacts

### Helper subcommand conventions (matching existing detect_report.py pattern)
- POSIX launcher (`scripts/lib/<name>`) shells to python with portable interpreter selection
- Python file (`scripts/lib/<name>.py`) uses argparse subparsers
- Standard subcommands: `reset`, `set`, `add-*`, `status`, `compose`
- Validation table approach: required-scalar list + required-non-empty-list + enum maps
- Output helpers: `info()` to stderr, `die()` for errors with exit 2
- Stdlib only

---

## Section 2 — Inventory of current state (reuse vs. redo)

### Reuse as-is (no changes during redo)
- **`scripts/lib/detect_report` (POSIX launcher)** — works correctly, well-tested by the audit smoke tests
- **`scripts/lib/wizard_render` (POSIX launcher)** — works correctly, identical pattern to detect_report
- **`scripts/lib/detect_report.py`** — large but mostly correct after the audit fixes (empty-project validation branch, reset subcommand). Keep but add tests where missing.

### Reuse with verification (existing code, must gain test coverage)
- All existing functions in `detect_report.py` that don't currently have explicit tests — verify each via real-input test (round-trip via `compose` → file → re-read) per the test-first rule. Test-coverage gap from initial development.
- Existing functions in `wizard_render.py` that survive the redo (atomic_write, info, die, basic state RW) — same: gain explicit tests.

### Redo (rewrite from scratch with test-first discipline)
- **`scripts/lib/wizard_render.py`** — ~1200 lines, much of it never had real-input tests. Rewrite incrementally, function by function, each with its own test that runs against producer output.
- **All 5 spec files for setup-wizard** — `main.md`, `references/{detect,questions,populate,agents}.md`. Rewrite each chapter against the established frame. The current versions are aligned (after audits) but were never written holistically; the redo produces them in one coherent pass.

### Keep with minor edits as discovered
- **`src/agents/*.md`** — agent templates. Placeholder set is correct after the type-safety-rules drop. If the redo discovers a new placeholder need or an existing placeholder needs a rendering rule change, edit then; otherwise leave.

### Existing `.devforge/` contents in target projects
Not affected by redo — those are install-time artifacts, not framework code.

---

## Section 3 — Spec outline (chapter-by-chapter)

The redo proceeds chapter by chapter. Each chapter writes one cohesive section of spec; helper functions are written inline as the spec demands them.

**Chapter conventions:**
- Each chapter has: scope, items it covers, anticipated helpers it needs, verification criterion
- Items within a chapter can be written in one `instruction-author` invocation if cohesive, or split if substantial
- After every chapter: `instruction-reviewer` reviews; commit at chapter boundary
- Commit message format: `setup-wizard-redo: <chapter-id>: <action>`

### Chapter group A — main.md (orchestrator entry)

**A1. Variation markers contract**
- Items: `{{ask}}` semantics (AskUserQuestion contract), `{{UPPERCASE}}` placeholder semantics
- Helpers needed: none
- Verify: spec self-consistent; AskUserQuestion constraints documented (2-4 options, no explicit Other, multiSelect for multi, bypass conditions); all 6 sub-rules from existing main.md preserved

**A2. Execution flow (Phase 0–5 listing)**
- Items: Phase 0 reset section, Phase 1 description with detect.md pointer, Phase 2 with questions.md pointer, Phase 3 with populate.md pointer, Phase 4 with agents.md pointer, Phase 5 summary intro
- Helpers needed: none
- Verify: each phase points to its reference file; no execution-order ambiguity

**A3. Phase 5 summary block**
- Items: `## Setup Complete` markdown template with `{VALUE}` placeholders for LLM substitution; conditional Next Steps block branching on PROJECT_STATE; reference to `.devforge/setup-complete` marker (helper-written, no LLM action)
- Helpers needed: none
- Verify: substitution placeholders defined; brownfield/greenfield/empty branches all complete

**A4. IMPORTANT RULES (global)**
- Items: 8 numbered rules covering never-guess, file-placement-vs-population, real-paths/commands, validation-helper-owned, wrapper-isolation, same-values-CLAUDE-vs-config, references-not-optional, AskUserQuestion-semantics
- Helpers needed: none
- Verify: each rule has a clear scope; no rule contradicts another; no rule reintroduces a discipline-rule escape hatch

### Chapter group B — references/detect.md (Phase 1)

**B1. Outputs section**
- Items: list of structured outputs (workspace_mode, source_root, project_state, default_branch, languages, frameworks, primary_language, packages_detected, build_tools/commands/etc., aggregated categories); storage note for the 4 working-memory-only command/tool arrays; empty-project compose note
- Helpers needed: none (documents what subsequent steps produce)
- Verify: every named output appears in detect_report's schema reference at section bottom; storage notes accurate vs detect_report.py validation rules

**B2. STEP 0: Workspace Mode Detection**
- Items: 0.1 nested-git scan; 0.2 ask user (AskUserQuestion with conditional shape: 2 options for 1 nested git, 2 options for 0 nested git, capped 4 options for multiple); 0.3 set source_root + workspace_mode
- Helpers needed: none for detection logic; existing `detect_report set workspace_mode --value <x>` and `set source_root --value <x>` setters used
- Verify: 4-option cap handled correctly for multi-git case; auto-Other path documented

**B3. STEP 1: Project State (count + classify)**
- Items: 1.1 canonical file-counting algorithm (excluded dirs, excluded files, counted extensions); 1.2 classification (0 = empty, 1-5 + scaffold sig = greenfield, 6+ = brownfield, ambiguous → ask); state-specific behavior pointers
- Helpers needed: file-count algorithm (canonical extension list, excluded dirs/files) — needs verification helper functions if we introduce them; for now, LLM-followed-algorithm is the spec
- Verify: file-count algorithm deterministic across runs; scaffold signatures listed; state classification rules complete

**B4. STEP 2: Default Branch**
- Items: detection signals in priority order (git symbolic-ref refs/remotes/origin/HEAD → git symbolic-ref HEAD → git branch --show-current); confirm-or-ask flow; wrapper-mode `git -C` targeting rule
- Helpers needed: none (LLM runs git commands directly)
- Verify: 3-signal priority documented; wrapper-mode `-C` rule applies to all phases

**B5. STEP 3: Auto-Detect Project Structure (brownfield only)**
- Items: package-root detection (manifest scan); per-stack tool detection; aggregated categories; SFC-container collapsing; threshold rule for new language stacks
- Helpers needed: none for detection (LLM-driven); existing `detect_report add-package`, `add-language`, `add-framework`, `add-enforcement-tool` setters used
- Verify: every aggregated category mapped to a detect_report field or storage note

**B6. Detection Report — Phase 1 output (rules + compose protocol)**
- Items: 9 rules for the report (every required field set explicitly, dep+usage double-check, architecture bucket enumerated, per-package commands per-package-specific, workspace members vs utility manifests, wrapper-mode prefix, evidence required, runtime_url dev-server config, README scope); compose protocol (`status` then `compose`)
- Helpers needed: detect_report `compose` (already exists; verify empty-project branch covered by test)
- Verify: every rule has a corresponding validation in detect_report.py OR is a documented LLM responsibility

**B7. Schema reference**
- Items: top-level scalars table; nested scalars table; lists table
- Helpers needed: none (mirrors detect_report.py dataclass)
- Verify: every dataclass field appears; types match; required-vs-optional matches detect_report.py validation

### Chapter group C — references/questions.md (Phase 2)

**C1. Outputs to retain**
- Items: list of working-memory variables (PROJECT_NAME through Q11 follow-ups); naming convention; storage destination (`.devforge/project-config.json` via Phase 3 setters)
- Helpers needed: none
- Verify: every named variable appears in Phase 3 §5.5 setter coverage table

**C2. How to run this phase + preflight**
- Items: REQUIRED/OPTIONAL/CONDITIONAL marker semantics; anti-hallucination rule for findings; preflight (read detection_report.yaml; bail to Phase 1 if missing)
- Helpers needed: none
- Verify: marker semantics consistent across all 12 questions

**C3. Q0 — Project Name**
- Items: detect from manifest if available (AskUserQuestion 2-option confirm/override); else plain prompt
- Helpers needed: none
- Verify: AskUserQuestion 2-option case fits the contract (no explicit Other)

**C4. Q1 — Project Description**
- Items: README-found path (plain prompt with quote — bypass AskUserQuestion per audit-resolved contract violation); no-README path (plain prompt)
- Helpers needed: none
- Verify: tool-bypass reasoning explicit (no "Write my own" duplicating auto-Other)

**C5. Q2 — Project Type (funnel)**
- Items: L1 conditional shape (2 options when Phase 1 has guess; skip L1 entirely when no guess); L2 plain-prose 13-category list when L1 selects "Pick from full list"; storage rule
- Helpers needed: none
- Verify: skip-L1-when-no-guess logic explicit (no doomed single-option AskUserQuestion call); 13 categories canonical for Q11 mapping table

**C6. Q3 — Languages & Frameworks**
- Items: empty-project branch (free-text intended-stack); single-language branch (confirm/override); multi-language branch (ordering confirm/override); array re-sync rules (reorder/remove/add cases); parallel-array invariant
- Helpers needed: none for the question itself; existing `wizard_render add-language` used in Phase 3
- Verify: array re-sync rules cover all 4 per-stack arrays (FRAMEWORKS, ARCHITECTURES, ERROR_HANDLINGS, API_LAYERS, TESTINGS) plus the 4 command/tool arrays

**C7. Q4 — Architecture Pattern (OPTIONAL, per-stack)**
- Items: single-stack vs multi-stack branching; cross-stack shortcut; Clean-Architecture vs hexagonal disambiguation; defer semantics (TBD)
- Helpers needed: none
- Verify: TBD handling consistent with Phase 3 rendering rules

**C8. Q5 — Error Handling Convention (OPTIONAL, per-stack)**
- Items: Phase 1 findings as primary source; per-stack iteration rules; cross-cutting convention shortcut
- Helpers needed: none
- Verify: lightweight supplemental scan rule preserves Phase 1 8-10 file cap

**C9. Q6 — API Layer (OPTIONAL, per-stack)**
- Items: detection-driven defaults; N/A for non-API projects; per-stack iteration
- Helpers needed: none
- Verify: N/A semantics distinguish "no API for this stack" from "user deferred"

**C10. Q7 — Testing Framework (OPTIONAL, per-stack)**
- Items: Phase 1 test-runner findings as primary; per-stack iteration; N/A for no-test-yet
- Helpers needed: none
- Verify: per-stack arrays land via `wizard_render add-testing`

**C11. Q8 — Workflow Enforcement (REQUIRED)**
- Items: 3 options (Strict / Moderate / Light); recommendation; downstream consumers list
- Helpers needed: none for question; `wizard_render set workflow_enforcement` for Phase 3
- Verify: 3-option AskUserQuestion fits contract; consumer list accurate vs current commands

**C12. Q9 — AI Attribution (REQUIRED)**
- Items: 2 options (No / Yes); storage as lowercase string
- Helpers needed: none for question; `wizard_render set ai_attribution` for Phase 3
- Verify: case-sensitive storage rule documented

**C13. Q10 — Agent Model Assignments (REQUIRED, batched)**
- Items: tier table (think/do/verify mapping to specific agents); tech-writer hardcoded-sonnet exception; recommended defaults; AskUserQuestion batched call (3 questions in 1 call per main.md exception)
- Helpers needed: none for question; `wizard_render set-tier` ×3 for Phase 3
- Verify: tier mapping table is single source of truth (referenced from agents.md §6.4)

**C14. Q11 — AC Verification (REQUIRED, multi-select)**
- Items: 4 options with `multiSelect: true` (Code-only / Tests / Runtime-assisted / Off); off-exclusivity post-validation; storage as JSON array; runtime-assisted follow-ups (web frontend / backend / full-stack / CLI / mobile-desktop-game / no-automatable-runtime); Q2→follow-up branch mapping table
- Helpers needed: `wizard_render add-ac-mode` (per selected mode); `wizard_render set ac_runtime_url` / `set ac_runtime_api_base` / `set ac_runtime_cli_command` (conditional)
- Verify: off-exclusivity enforced both in spec (LLM drops other modes silently) AND in helper validation (compose rejects off + others); Q2 mapping table covers all 13 categories

### Chapter group D — references/populate.md (Phase 3)

**D1. Why a helper owns the writes + Files written by compose + Drift-risk literals**
- Items: rationale for helper-owns-shape; complete list of files compose writes; CHROME_DEVTOOLS_MCP_PACKAGE drift literal
- Helpers needed: none
- Verify: file list matches what compose actually writes; drift literal matches helper's constant

**D2. How to run this phase**
- Items: 2 stages (compose values + status check); explicit "do NOT call compose here" with reason; pointer to agents.md §6.7 for canonical compose call
- Helpers needed: none
- Verify: defer-compose rule explicit and unambiguous

**D3. §5.1 CLAUDE.md placeholders — direct-value scalars**
- Items: 3 placeholders (PROJECT_NAME, PROJECT_DESCRIPTION, PROJECT_TYPE); helper-derived placeholders (SOURCE_ROOT, WRAPPER_MODE_SECTION) note
- Helpers needed: `wizard_render set project_name/description/type` (existing setters)
- Verify: setter syntax in spec matches helper

**D4. §5.1 helper-derived stack-aware placeholders**
- Items: 6 derivable placeholders (FRAMEWORK, LANGUAGE, BUILD_TOOL, BUILD_COMMAND, TYPE_CHECK_COMMAND, LINT_COMMAND); per-stack array setter calls (`add-language`, `add-build-tool`, `add-build-command`, `add-type-check-command`, `add-lint-command`); rendering rules; null/N/A/TBD semantics
- Helpers needed: `derive_placeholder` function in wizard_render.py + the 4 add-* setters
- Verify: derive_placeholder handles single-stack + multi-stack + architect-context + CLAUDE.md-context; tested with real per-stack arrays

**D5. §5.1 composed multi-line renders**
- Items: PROJECT_STRUCTURE composition rules (single-package / multi-package / >10-package collapsing); DEV_COMMANDS rules (per-package monorepo / orchestrator shortcut); ARCHITECTURE_DETAILS rules (single-stack flat / multi-stack grouped); PACKAGE_STACKS_SECTION (aggregation step + monorepo collapse rule + 2-table format)
- Helpers needed: `wizard_render set-render <field> --stdin` for each (existing setter)
- Verify: per-stack rendering rules consistent with derive_placeholder behavior

**D6. §5.1 helper-derived special placeholders (WRAPPER_MODE_SECTION, COMMIT_ATTRIBUTION, AGENT_LIST)**
- Items: WRAPPER_MODE_SECTION rendering (helper from workspace_mode + source_root); COMMIT_ATTRIBUTION rendering (helper from ai_attribution); AGENT_LIST staging string (replaced by helper in §6.6)
- Helpers needed: `render_wrapper_mode_section`, `render_commit_attribution`, agent-list staging logic in compose
- Verify: each helper function has its own test (wrapper/standalone, yes/no attribution, agent-list staging swap)

**D7. §5.2 .claude/settings.json**
- Items: no placeholder substitution; only conditional permissions append (in §5.4)
- Helpers needed: none specific to this section
- Verify: heading is file-named (`.claude/settings.json`); body matches actual helper behavior

**D8. §5.3 Baseline copies**
- Items: helper-owned; runs AFTER §6.6 swap-back so baselines capture final state; settings.json projectOwned exception
- Helpers needed: baseline-copy block in compose (deferred to after §6.6 per audit fix)
- Verify: order note explicit; tested via end-to-end compose run

**D9. §5.4 MCP servers + permissions (conditional)**
- Items: helper-owned; conditional on ac_runtime_url; chrome-devtools entry into .mcp.json + permissions into .claude/settings.json
- Helpers needed: `inject_chrome_devtools_mcp`, `append_chrome_devtools_permissions`
- Verify: each helper tested with present + missing source files

**D10. §5.5 .devforge/project-config.json + setter coverage table**
- Items: helper-owned assembly; comprehensive Setter coverage from Phase 2 answers table (Q0-Q11 + Phase 1 per-stack arrays)
- Helpers needed: `write_project_config`
- Verify: table covers every required field that compose validates; setter syntax matches helper

**D11. §5.6 .devforge/memory.md seed + Other observations spillover**
- Items: seed composition rules; structured bullets (Languages, Frameworks, etc.); spillover bullet (cap 5, signal-cite required); examples (multi-stack, single-stack, empty)
- Helpers needed: `insert_memory_seed`
- Verify: helper inserts above sentinel; LLM-side composition rules apply discipline (cap, citation)

**D12. §5.7 constitution.md header**
- Items: helper-owned substitution + blockquote stripping; placeholder list; body sentinels untouched
- Helpers needed: `strip_authoring_blockquotes`, `compose_constitution_subs`, paired-or-scalar rendering
- Verify: each helper tested; body sentinels preserved; placeholder list matches constitution.md template

**D13. §5.8 docs/overview.md and docs/architecture.md**
- Items: helper-owned substitution; per-file placeholder list; body sentinels untouched
- Helpers needed: substitution loop in compose
- Verify: each file's placeholder list matches its template

**D14. End of Phase 3 — defer compose**
- Items: status-only rule; no compose call; pointer to agents.md §6.7
- Helpers needed: none
- Verify: explicit "Do NOT call compose here" + reason

### Chapter group E — references/agents.md (Phase 4)

**E1. Files affected by this phase**
- Items: list of files compose modifies during Phase 4 (agent files, AGENT_LIST in CLAUDE.md, agent baselines, possible deletions)
- Helpers needed: none
- Verify: list matches what compose actually does

**E2. §6.1 Select Agents**
- Items: always-keep set; conditional-keep set with selection criteria; PACKAGE_STACKS cross-check; do-not-hardcode-framework-names rule
- Helpers needed: none for selection (LLM-driven)
- Verify: selection rules don't reintroduce escape hatches

**E3. §6.2 Present Selection & Ask**
- Items: prompt template; reason-must-cite-Phase-1-signal rule; user override mechanism
- Helpers needed: none
- Verify: anti-hallucination rule for reasons explicit; AskUserQuestion fits contract for confirm/override

**E4. §6.3 Mark Rejected Agents for Removal**
- Items: helper-owned via apply-agents JSON `removed` list; no manual deletion
- Helpers needed: deletion handled in compose
- Verify: spec doesn't tell LLM to rm files

**E5. §6.4 apply-agents JSON shape + tier mapping**
- Items: canonical path (.devforge/.agents-apply.json); JSON shape (kept dict + removed list); tier assignment per agent (mapping inline + Q10 source-of-truth pointer); tech-writer exception; helper-derives-everything table; adding new placeholder process
- Helpers needed: `cmd_apply_agents` (validation + state recording); helper auto-deletes file after consumption
- Verify: every placeholder in agent templates appears in derive_placeholder OR is in apply-agents substitutions section; tier mapping matches Q10 table

**E6. §6.5 Save Agent Baselines (helper-owned)**
- Items: compose copies kept agents to .devforge/baseline/agents/; no LLM action
- Helpers needed: agent-baseline copy block in compose
- Verify: baseline copied AFTER per-agent substitution + model: regex (so baseline = final state)

**E7. §6.6 Update AGENT_LIST (helper-owned)**
- Items: compose reads each kept agent's description from frontmatter; renders bullet list; replaces staging string in CLAUDE.md
- Helpers needed: `parse_agent_description`, `render_agent_list`
- Verify: each helper tested; bullet format matches spec example

**E8. §6.7 Compose protocol (canonical compose call site)**
- Items: status + compose call; complete validation list; complete responsibility list (every section compose touches)
- Helpers needed: `cmd_compose` orchestration
- Verify: every responsibility item maps to actual compose code; validation list complete

### Chapter group F — main.md cross-cutting (touch as needed during chapter writing)

**F1. Phase 0 reset section**
- Items: instruction to call detect_report reset + wizard_render reset before any setters
- Helpers needed: `detect_report reset`, `wizard_render reset` (existing)
- Verify: rationale explicit (silent duplication risk on re-run)

---

## Section 4 — Helper interface anticipation

Best-guess of helper functions the redo will write or verify. Actual implementation deferred to inline discovery during chapter writing (per the spec-driven workflow).

### `scripts/lib/wizard_render.py` — anticipated structure

**Subcommands (CLI surface):**
- `reset` → cmd_reset (delete state file)
- `set <field> --value <v>` → cmd_set (scalar fields with optional enum validation)
- `set-tier <tier> --value <v>` → cmd_set_tier (think/do/verify → opus/sonnet/haiku)
- `set-render <field> --stdin|--value <v>` → cmd_set_render (multi-line LLM-composed renders)
- `add-language --name <s> [--framework <s>]` → cmd_add_language
- `add-architecture/error-handling/api-layer/testing/build-tool/build-command/type-check-command/lint-command --value <v>` → per-stack adders (factory)
- `add-ac-mode --value <v>` → cmd_add_ac_mode (with enum validation)
- `apply-agents --substitutions-file <path>` → cmd_apply_agents (JSON validation + state recording)
- `status` → cmd_status (compose readiness check)
- `compose` → cmd_compose (orchestrates all writes)

**Internal functions (anticipated):**
- State RW: load_state, save_state, clear_state, default_state
- Atomic writes: write_atomic
- YAML reader: read_detection_report (with wrapper-key unwrap), _parse_yaml_subset (with list-of-dicts handling), _coerce_yaml_scalar
- Substitution engine: apply_substitutions, PLACEHOLDER_RE
- Derivers: derive_placeholder, _join_non_null, _primary, _paired, _STACK_ARRAY_FIELD map
- Compose helpers: compose_claude_md_subs, compose_constitution_subs
- Special-case renderers: render_wrapper_mode_section, render_commit_attribution, render_agent_list
- Substitution post-processors: strip_authoring_blockquotes, replace_model_line, parse_agent_description
- File-specific writers: write_project_config, insert_memory_seed, inject_chrome_devtools_mcp, append_chrome_devtools_permissions, write_setup_complete
- Validation: validate_for_compose, _check_required (or equivalent)
- Output helpers: info, die

**Constants:**
- DEVFORGE_DIR, STATE_FILE, PROJECT_CONFIG, MEMORY_FILE, BASELINE_DIR, AGENT_BASELINE_DIR, AGENTS_DIR, SETTINGS_FILE, MCP_FILE, CLAUDE_MD, CONSTITUTION_MD, DOCS_OVERVIEW, DOCS_ARCHITECTURE
- CHROME_DEVTOOLS_MCP_PACKAGE (drift-risk literal)
- MEMORY_SENTINEL
- _TIERS, _TIER_VALUES, _AC_MODES, _WORKFLOW, _ATTRIBUTION (enum sets)
- _SCALAR_FIELDS, _RENDER_FIELDS, _REQUIRED_SCALARS, _REQUIRED_RENDERS

### `scripts/lib/detect_report.py` — already exists, audit needs

Already-correct subcommands stay. The redo verifies test coverage gaps:
- Every existing function gains an explicit test if not already covered (per test-first rule)
- Empty-project compose branch tested end-to-end (already tested during audit)
- Reset subcommand tested (already added)

---

## Section 5 — Workflow rules

### Spec-driven loop

For each chapter:
1. **Brief instruction-author** with: chapter scope (from Section 3), integration context (which prior chapters / helpers it depends on), specific items to cover, anticipated helper dependencies
2. **instruction-author writes the chapter**
3. **If chapter requires a new helper or helper change** that doesn't exist:
   a. Pause spec writing
   b. **Brief python-engineer** with: function signature, behavior, inputs/outputs, edge cases known, integration context, success criterion (specific test that must pass)
   c. python-engineer writes function + test, runs test
   d. **Brief python-reviewer** with: function code, test code, integration context, files to cross-reference
   e. python-reviewer reviews; if findings, send back to python-engineer for fix
   f. Integrate the helper (commit at this point if substantial)
   g. **Re-spawn instruction-author** with: chapter-in-progress (what was written so far) + new helper context (function signature + behavior + how to invoke from spec)
4. When chapter complete: **brief instruction-reviewer** with: chapter file path(s), changes summary, related files for cross-reference
5. instruction-reviewer reviews; fixes findings if any
6. **Commit** at chapter boundary with message `setup-wizard-redo: <chapter-id>: <action>`
7. **Update Execution log** at the bottom of this PLAN file

### Resume mechanism (after helper interruption)

When spec writing pauses for helper work and resumes:
- **Re-spawn instruction-author** (option (i) per session decision) — does not rely on prior agent session being alive
- Brief includes: chapter-in-progress content (paste current state) + new helper context (signature + invocation pattern) + reminder of chapter scope and remaining items

### Agent dispatch protocol

- **Default sequential.** Each agent invocation completes before the next starts.
- **Parallel only with explicit reason.** Justification required: tasks share zero state AND orchestrator can use the parallel time productively AND benefit > 2x token cost.
- **Most chapters won't have parallel opportunities** — chapters are sequential by design (chapter B depends on chapter A's output via cross-references).

### Commit cadence

- One commit per chapter (after instruction-reviewer approval)
- Helper additions/changes get their own commits before the chapter completes (so the chapter's commit is spec-only)
- Each commit message: `setup-wizard-redo: <chapter-id>: <action>` (e.g., `setup-wizard-redo: A1: write variation markers contract`)

### Branch strategy

- All redo work on `develop-2.0` (current branch). The redo replaces existing setup-wizard files in place.
- The pre-redo state is preserved in commit `877ac25` (current HEAD as of plan creation). If anything goes wrong, `git revert` from that point is the rollback path.

### Verification before each commit

- **Helper commits:** function tests pass; python-reviewer approved; cross-reference grep clean
- **Spec commits:** instruction-reviewer approved (no high/medium findings unfixed); cross-reference grep clean; sentence-level hallucination check applied

### Use of Claude Code primitives

- **AskUserQuestion** — used in wizard runtime per the contract; documented in main.md
- **WebFetch** — used by instruction-author for Claude-Code-integration questions per the rule
- **Subagents** — python-engineer, python-reviewer, instruction-author, instruction-reviewer per the workflow above
- **Plan mode / TaskCreate / Hooks / Skills** — deferred; if a stable workflow pattern emerges during redo, promote then. Don't add ceremony preemptively.

---

## Execution log

Updated as chapters complete. Most recent at top.

| Date | Chapter | Commit | Status |
|---|---|---|---|
| 2026-04-27 | (plan created) | `<this commit>` | PLAN file written |

---

## Open questions / decisions deferred

- **Existing helper functions in detect_report.py — test backfill scope.** The redo focuses on wizard_render.py rewrite; detect_report.py already works (audited end-to-end). The test-first rule says every function gets a test. Do we backfill detect_report.py tests as part of this redo, or as a separate cleanup? Defer decision until after wizard_render redo lands; assess scope then.
- **Is there a value in a top-level integration test that runs the full wizard end-to-end** (Phase 1 → Phase 5 with synthetic detection inputs)? Could replace many smaller tests + serve as the "fully aligned" verification. Defer until redo is far enough along to know what to assert.
