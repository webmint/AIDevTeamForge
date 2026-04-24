# Multi-Runtime Support — Branch Plan (rev 11)

Branch: `feature/codex-support`
Main: Claude-only, unchanged. **This branch never merges to main** — it's a separate multi-runtime experiment that will ship differently (its own product, long-lived branch, or archived).
Strategic posture: **maximum differentiation** — accept maintenance cost in exchange for positioning.

---

## 1. What we're building

This repo is a **template installer**. `install.sh` scaffolds a target project with everything needed to run spec-driven workflows via any supported LLM CLI.

Target goal: after one install, a developer can open **any supported CLI** (Claude Code today; Codex CLI next; later Cursor, Gemini) in their project and run every README workflow identically.

### Two types of work

1. **Structural/tooling work** — generator, install.sh, emitters, update.sh. Code that produces runtime-specific files from a neutral source.
2. **Content/prose work** — annotating the 24 commands and 16 agent templates with variation markers so each emitter renders them correctly for its runtime.

---

## 2. Architecture (locked)

### Source of truth: `src/`

```
src/
├── commands/               ← active commands (setup-wizard.md currently; rest in _pending/)
├── _pending/commands/      ← 22 commands awaiting annotation + promotion
├── agents/                 ← 16 universal agent sources (fenced-yaml meta + markdown body)
├── files/
│   ├── coreLLM/
│   │   ├── SOURCE.md       ← single source → generates CLAUDE.md + AGENTS.md
│   │   └── desiredOutput/  ← reference examples of generated output
│   ├── mcp.json                  ← Claude MCP config (context7 pre-loaded)
│   ├── settings.template.json    ← Claude settings (hooks + minimal permissions)
│   └── config.toml               ← Codex full settings: MCP + model + sandbox + approval
├── devforge/               ← cross-runtime scaffolding → installed to .devforge/
│   ├── project-config.json ← empty scaffold (null keys), wizard populates
│   ├── memory.md           ← persistent learnings (flat file, cross-runtime)
│   └── storage-rules.md    ← artifact storage conventions (LLM-neutral)
└── manifest.json           ← update.sh source-of-truth for what's template-owned vs project-owned
```

### install.sh: copy + delegate

`install.sh` is intentionally thin:
- Validates args (target dir, wrapper mode)
- Delegates to `scripts/generate.sh` for coreLLM + agents + runtime-specific emission
- Copies `.devforge/` scaffolding
- Copies runtime config files (`.mcp.json`, `.claude/settings.json`, `.codex/config.toml`)

Adding a new runtime does **not** touch install.sh (except MCP config if the runtime has one).

### Generator pipeline

```
scripts/
├── generate-corellm.py         ← reads SOURCE.md, produces CLAUDE.md + AGENTS.md
├── generate-agents.py          ← reads src/agents/*.md, produces .claude/agents/*.md + .codex/agents/*.toml
├── generate.sh                 ← orchestrator: coreLLM → agents → per-runtime emitters
├── emitters/
│   ├── claude.py               ← commands → target/.claude/commands/
│   └── codex.py                ← commands → target/.agents/skills/
│   └── (future) cursor.py, gemini.py
└── lib/
    └── frontmatter.py          ← stdlib markdown+YAML parser for command frontmatter
```

Python 3, stdlib only. No PyYAML, no requirements.txt.

### Agent generator (`src/agents/*.md` → per-runtime native)

Each agent source is a **universal** file — intentionally *not* shaped like any runtime's native format. Format:

```
```yaml
name: architect
description: "..."
model_tier: think      # think | do | verify — semantic, not runtime-specific
```

<markdown body>
```

The fenced `yaml` block (not `---`/`---` frontmatter) prevents the source from mimicking Claude's native agent format, forcing every runtime emission to be constructed from scratch. `model_tier` translates to runtime-specific placeholders:
- Claude: `model: {{CLAUDE_TIER_THINK}}`
- Codex: `model = "{{CODEX_TIER_THINK}}"` + `model_reasoning_effort = "{{CODEX_REASONING_THINK}}"`

Codex TOML body uses multi-line literal `'''...'''` — no escaping of backslashes, backticks, or quotes. Adding a runtime = one `RUNTIMES` dict entry.

### CoreLLM generator (SOURCE.md → CLAUDE.md + AGENTS.md)

Single source file with two marker types:
- `{{output.X}}` — simple substitution (filename, intro, sigil). 3 values per runtime.
- `{{#runtime}}...{{/runtime}}` — conditional blocks for structurally different sections.
- `{{UPPERCASE}}` markers pass through untouched — wizard substitutes them post-install.

Adding a new runtime = one dict entry in `generate-corellm.py`. Source file doesn't change.

### Three substitution stages (different lifecycles)

| Stage | Substituted by | Substitutes what | When |
|---|---|---|---|
| CoreLLM markers | generate-corellm.py | `{{output.filename}}`, `{{output.sigil}}`, `{{output.intro}}`, `{{#claude}}...{{/claude}}` | Install time (pre-emitter) |
| Runtime markers | Emitters (claude.py, codex.py) | `{{cli.sigil}}`, `{{cli.attribution}}`, `{{ask}}` blocks in commands | Install time (emitter) |
| User-answer placeholders | Wizard | `{{FRAMEWORK}}`, `{{LANGUAGE}}`, `{{ARCHITECTURE_DETAILS}}`, etc. | Wizard run time |

### Wizard's role (revised)

The wizard has two modes in a single run:
1. **Populate** (STEP 5): Substitute `{{PLACEHOLDER}}` markers in already-placed files (CLAUDE.md, AGENTS.md, MCP configs, project-config.json). Save baselines.
2. **Generate** (STEP 6): Curate agents (decide which to keep, delete the rest, populate kept ones). Future: constitution, settings, memory.

### Cross-runtime paths (.devforge/)

All shared state lives in `.devforge/` — not `.claude/` or `.codex/`:
- `.devforge/project-config.json` — canonical wizard answers record
- `.devforge/memory.md` — persistent learnings (flat file)
- `.devforge/storage-rules.md` — artifact storage conventions
- `.devforge/session-state.md` — session snapshot (created at runtime by commands)
- `.devforge/wip.md` — WIP marker (created at runtime by commands)
- `.devforge/baseline/` — baselines for three-way merge in update.sh

### Acceptance: B (structural match)

Same user answers → same file set, same paths, same semantic content, regardless of which CLI ran the wizard. LLM-level detection variance absorbed at the user-confirmation layer.

---

## 3. Progress so far

### ✅ Phase 0 — Pre-flight

Three load-bearing assumptions resolved via docs analysis (see `phase-0/REPORT.md`):
- `@path` imports do not port across runtimes → generator required.
- `.agents/skills/` is a real Codex scan path.
- Codex `PostToolUse` fires on Bash only → prose-level verify replaces auto-hooks.
- Codex custom prompts removed in CLI 0.117.0 → skills are the only Codex command mechanism.

### ✅ Phase R — Repo reshape

- Template sources moved from `.claude/` → `src/`.
- `.claude/` retains only maintainer's own Claude usage (`release.md`, `settings.local.json`, `memory/`).
- Version marker → `VERSION` at repo root.
- Manifest restructured to pair-based `files: [{source, target}]`.
- install.sh + update.sh updated for new paths.

### ✅ Phase A (partial) — Generator + emitters

- `scripts/generate-corellm.py` — CoreLLM generator: single SOURCE.md → CLAUDE.md + AGENTS.md.
- `scripts/generate-agents.py` — Agent generator: universal fenced-yaml source → per-runtime native (`.claude/agents/*.md` + `.codex/agents/*.toml`). Neither runtime is pass-through; both built from scratch. `model_tier` (think/do/verify) translates into wizard placeholders `{{CLAUDE_TIER_*}}` and `{{CODEX_TIER_*}}` + `{{CODEX_REASONING_*}}`.
- `scripts/emitters/claude.py` — Claude emitter (commands to `.claude/commands/`).
- `scripts/emitters/codex.py` — Codex emitter (commands to `.agents/skills/`).
- `scripts/generate.sh` — orchestrator: coreLLM → agents → per-runtime emitters.
- `install.sh` narrowed: coreLLM + agents + setup-wizard command + `.devforge/` + runtime configs. Tested end-to-end: 16 agents per runtime + 9 other files.

### ✅ Phase A (partial) — Agent source neutralization

- All 16 agent sources renamed `*.template.md` → `*.md` and rewritten in the universal fenced-yaml format.
- Scanned sources for Claude-specific leakage: removed "Your Tools" lists naming `**Bash**`, `**File tools (Read, Grep, Glob)**`, `**TaskCreate/TaskUpdate**`; replaced with runtime-neutral "Your Capabilities" (Shell access, Codebase search & read, Task tracking).
- Inline prose replaced: `Use Grep to find` → `Search the codebase for`, `Use Read to open` → `Open`, `Bash curl` → `shell curl`, `via Bash` → `in the shell`. "subagent" terminology kept (standard across both runtimes now).

### ✅ Phase A (partial) — CoreLLM files (CLAUDE.md + AGENTS.md)

- Single SOURCE.md with `{{output.*}}` markers and `{{#runtime}}` conditional blocks.
- CLAUDE.md (235 lines): verbose workflow command descriptions, PostToolUse hooks.
- AGENTS.md (180 lines, ~9 KiB — under 32 KiB Codex limit): compact workflow with skill pointers, explicit verification.
- Shared sections: Project Overview (bullets), Architecture (`{{ARCHITECTURE_DETAILS}}` — dynamic, not hardcoded web fields), Key Rules (14 Always + 6 Never), Commit Convention (full), Artifact Storage (full tree), Session Continuity, Crash Recovery, References.
- All cross-runtime paths unified to `.devforge/` (memory, session-state, wip, baselines).
- `{{PROJECT_DESCRIPTION}}` added to both files (new Q1 in wizard).
- desiredOutput/ directory with reference examples.

### ✅ Phase A (partial) — Cross-runtime scaffolding (.devforge/)

- `src/devforge/project-config.json` — empty scaffold with all wizard answer keys (including agent tiers, AC follow-ups, workflow enforcement).
- `src/devforge/memory.md` — flat file (no subfolder, no UPPERCASE naming).
- `src/devforge/storage-rules.md` — moved from `src/files/`, neutralized (no CLI sigils, no hardcoded `.ts` extensions, no JS-specific debug artifacts, commands referenced without sigils).
- install.sh copies `src/devforge/` → `target/.devforge/`.

### ✅ Phase A (partial) — Runtime config templates

Per-runtime native config files — no forced symmetry between Claude JSON and Codex TOML. Each runtime gets what it natively uses:

- `src/files/mcp.json` — Claude MCP servers (`.mcp.json` at target root).
- `src/files/settings.template.json` — Claude settings: hooks (`PostToolUse` → `{{TYPE_CHECK_COMMAND}}`), minimal `permissions.allow[]` (core Claude tools + context7). chrome-devtools entries stripped; wizard STEP 5.4 adds them conditionally.
- `src/files/config.toml` — Codex full settings: `model = "{{CODEX_MODEL_DEFAULT}}"`, `model_reasoning_effort = "{{CODEX_REASONING_DEFAULT}}"`, `approval_policy = "{{CODEX_APPROVAL_POLICY}}"`, `sandbox = "none"`, MCP servers (context7).
- install.sh places all three files. Wizard STEP 5.2 populates placeholders.
- Classification: `.claude/settings.json` and `.codex/config.toml` are **projectOwned** in the manifest — user customizes, update.sh never overwrites.
- Wizard STEP 5.4 adds chrome-devtools MCP to both `.mcp.json` and `.codex/config.toml`, AND appends `mcp__chrome-devtools__*` entries to Claude's `permissions.allow[]` (Claude-only; Codex uses `approval_policy` instead).

### ✅ Phase A (partial) — Runtime selection flag

`install.sh --runtime <csv>` lets users install only the runtimes they actually use. Default (no flag) installs all registered runtimes.

- `install.sh`: `--runtime claude,codex,...` with validation (unknown name → fail fast). `has_runtime()` helper gates per-runtime config-file copies. `.devforge/` stays unconditional (cross-runtime). `RUNTIMES` env var forwarded to `generate.sh` when a filter is active.
- `scripts/generate.sh`: forwards `$RUNTIMES` to `generate-corellm.py` and `generate-agents.py` via `--runtimes` (was only used by per-runtime emitter loop previously).
- `scripts/generate-corellm.py` and `scripts/generate-agents.py`: accept `--runtimes` (space-separated). Empty = all registered runtimes. Unknown runtime name → error.
- `setup-wizard.md` STEP 5: "if file exists" guards in 5.1, 5.2, 5.3, 5.4 so single-runtime installs don't fail when the other runtime's files are absent.
- Closing message: per-runtime launch hints — Claude Code gets `/setup-wizard`, Codex CLI gets "ask it to run the setup-wizard skill" (Codex skills have no slash-command syntax).

Tested 3 install modes:
- default → 41 files, both runtimes
- `--runtime claude` → 23 files, no `.codex/`, no `AGENTS.md`
- `--runtime codex` → 22 files, no `.claude/`, no `.mcp.json`, no `CLAUDE.md`

### ✅ Phase A (partial) — /plan: Algorithmic Pattern Scan

Content-level improvement to `src/_pending/commands/plan.md` (not yet promoted). Adds conditional Phase 1.4 that catches classical algorithmic pattern wins when spec operations hit non-trivial scale. Trigger table covers hash set/map, two-pointer, sliding window, prefix sum / Fenwick, trie, BFS / Dijkstra / 0-1 BFS, heap, union-find, sweep line, DP / memoization, binary search on answer. Explicit skip rule for small fixed sets, pure CRUD/UI, no traversal — "pattern over premature optimization."

Plan template gains an "Algorithmic Patterns" table (naive → pattern → complexity win → scale justification). Section omitted entirely when no material win.

### ✅ Phase A (partial) — setup-wizard.md STEPs 0–7

**STEPs 0–4** (detection + questions): fully audited and rewritten across multiple sessions. 24+ issues resolved.

**STEP 5** (Populate Placed Files): full placeholder-to-answer mapping with construction rules for dynamic values. Substeps:
- 5.1: Populate CLAUDE.md + AGENTS.md (same values, both files; includes `{{PACKAGE_STACKS_SECTION}}` for multi-package projects)
- 5.2: Populate runtime config files — `.claude/settings.json` is static (no placeholders); `.codex/config.toml` substitutes `{{CODEX_MODEL_DEFAULT}}`, `{{CODEX_REASONING_DEFAULT}}`, `{{CODEX_APPROVAL_POLICY}}`
- 5.3: Save baselines to `.devforge/baseline/` (only for CLAUDE.md + AGENTS.md — runtime configs are projectOwned, no baseline)
- 5.4: Add chrome-devtools MCP + Claude permission entries conditionally (triggers when `AC_RUNTIME_URL` is set — covers Q11 web-frontend AND full-stack branches)
- 5.5: Populate `.devforge/project-config.json` (includes per-stack arrays, PACKAGE_STACKS, CODEX_REASONING_* derivation for Q10b → emitter-placeholder resolution)
- 5.6: Pre-populate `.devforge/memory.md` with Phase 1 detection findings (cross-runtime shared)

**STEP 6** (Curate & Populate Agents): LLM-driven agent selection. Substeps:
- 6.1: Select agents (5 always-keep + 11 conditional, no hardcoded framework lists)
- 6.2: Present keep/remove list, user confirms/overrides
- 6.3: Remove rejected agents from both runtime dirs
- 6.4: Populate kept agents (substitute placeholders, add project patterns)
- 6.5: Save agent baselines
- 6.6: Update `{{AGENT_LIST}}` in CLAUDE.md and AGENTS.md

**STEP 7** (Summary): stub, needs development.

**Questions Q0–Q11:**
- Q0: Project Name (detected from manifest or asked)
- Q1: Project Description (from README or asked)
- Q2: Project Type
- Q3: Languages & Frameworks (produces parallel `LANGUAGES` / `FRAMEWORKS` arrays; Array re-sync on override keeps per-stack arrays consistent)
- Q4: Architecture Pattern (per-stack array with cross-stack shortcut)
- Q5: Error Handling Convention (per-stack array)
- Q6: API Layer (per-stack array)
- Q7: Testing Framework (per-stack array)
- Q8: Workflow Enforcement Level (stored but no command reads it yet — flagged)
- Q9: AI Attribution in Commits
- Q10: Agent Model Assignments — Q10a Claude tiers (`CLAUDE_TIER_*` = model names), Q10b Codex tiers (`CODEX_TIER_*` = reasoning enums, `CODEX_TIER_*_MODEL` = optional overrides)
- Q11: Acceptance Criteria Verification (with total Q2→Q11 branch mapping — no project-type falls off the edge)

### ✅ Phase A (partial) — setup-wizard refactor + logical-gap audit (rev 10)

**Structural refactor**: `src/commands/setup-wizard.md` split into `main.md` (orchestrator) + `references/detect|questions|populate|agents.md` so each phase is loadable on demand. Emitters rewritten (new `scripts/lib/command_source.py`) to materialize this multi-file layout per-runtime.

**Logical-gap audit (3 passes, 19 findings, 17 resolved)** — see commit `d53efce`. Highest-impact fixes:

- Corrected hallucinated MCP package name (`@anthropic/chrome-devtools-mcp` → `chrome-devtools-mcp`; `npm view` confirms the scoped name 404s)
- Replaced hallucinated agent-frontmatter placeholders `{{MODEL_THINK/DO/VERIFY}}` with the runtime-qualified names `generate-agents.py` actually emits (`{{CLAUDE_TIER_*}}` / `{{CODEX_TIER_*}}` / `{{CODEX_REASONING_*}}`). Added matching `CODEX_REASONING_*` keys to `project-config.json` and documented the Q10b → emitter-placeholder derivation in populate.md §5.5. Without this, Q10 answers never reached the installed agent files.
- Built a total Q2→Q11 mapping for runtime-assisted AC verification (library / ML / ETL / IaC / plugin / docs routed to a "no automatable runtime" branch instead of silently falling off)
- `setup-complete` marker's `Populated files:` now computed from presence checks (single-runtime installs no longer claim to populate files that don't exist)
- Consolidated drift-risk literals (`CODEX_DEFAULT_MODEL`, `CHROME_DEVTOOLS_MCP_PACKAGE`) into one reviewable block with last-verified dates
- STEP 2 default-branch now detects via `git symbolic-ref` before asking
- Per-stack tool detection now specifies command-runner selection from lockfiles (pnpm/yarn/bun/npm, poetry/hatch/pdm/uv, bundle exec) so commands land correctly for the project's actual toolchain

Two findings deferred by user: architect template expansion to include BUILD/LINT/TYPECHECK placeholders; `{{cli.sigil}}specify` / `{{cli.sigil}}verify` wizard-prose references to `_pending/` commands (resolves when those commands promote).

### ✅ Phase A (partial) — constitution.md + docs/ install-time placement (rev 11)

Applied the "install places, wizard populates" pattern to two more files that previously had no install path:

- **`constitution.md`** — renamed from `constitution.template.md`; install.sh copies it to target root (brownfield-presence-guarded). Wizard §5.7 substitutes header placeholders (name / type / framework / language / workspace mode / source root + `{{ERROR_HANDLING}}` and `{{TESTING}}` pattern lines). Body `[project-specific]` sentinels stay untouched — `/constitute` fills those.
- **`docs/overview.md`** and **`docs/architecture.md`** — two stub files placed by install.sh (per-file presence-guarded; brownfield keeps any existing content). Wizard §5.8 substitutes placeholders. `features/`, `api/`, `guides/` subdirectories are NOT scaffolded — they emerge lazily when tech-writer creates the first file inside them. No empty `.gitkeep` dirs.

Design decision: `/constitute` retained (earlier conversation considered eliminating it). New role: **establishment phase** that takes onboard's discovery output + user interview → populates `constitution.md` body. Flow is setup-wizard → onboard (brownfield only) → constitute → specify. Wizard's Phase 5 Next Steps now branches on `PROJECT_STATE` accordingly.

### ✅ Phase A (partial) — onboard command promoted + 3-pass audit (rev 11)

Onboard command moved from `_pending/` to live at `src/commands/onboard/` with the same folder structure as setup-wizard (`main.md` + `references/tech-writer-onboarding.md`). Now emitted alongside setup-wizard via both runtime emitters.

Key structural work:
- CLI-agnostic pass across `main.md` and `references/tech-writer-onboarding.md` — replaced hardcoded Claude paths (`.claude/agents/`, `CLAUDE.md`, `Agent` tool) with runtime-neutral references.
- De-web-bias pass on `tech-writer-onboarding.md` — expanded language examples (Rust, Go, Swift, Java/Kotlin), generalized API-protocol handling (REST / gRPC / GraphQL / WebSocket / tRPC), marked UI-specific bits as conditional.
- Added new `{{cli.primer}}` and `{{cli.subagent}}` variation markers (resolves to `CLAUDE.md` / `AGENTS.md` and the `Agent` tool / subagent invocation per runtime).
- Deleted §A.2's duplicated per-file templates — now delegates to main.md's Documentation Requirements as the single source of truth.

3-pass logical-gap audit on `onboard/main.md` (20 findings fixed total) — see commits `a98261c`, `2976acb`, `a8df9e9`. Highlights:
- Added §1.0 existing-documentation check with baseline-diff detection (protects user-edited `docs/` from being clobbered on re-run).
- Fixed Q2→Q11 mapping coverage (library / ML / ETL now route to "no automatable runtime" branch).
- Corrected `PROJECT_STATE` vs stale `PROJECT_MODE` references + values.
- Replaced subjective LLM heuristics with deterministic baseline-diff comparisons.
- Made Mode user-choice (overwrite / merge / abort) propagate to the tech-writer prompt via a new `Mode` section in the prompt template.

2-pass audit on `references/tech-writer-onboarding.md` (11 findings total).

### ✅ Phase A (partial) — tech-writer agent alignment + audit (rev 11)

Aligned `src/agents/tech-writer.md` with its invoking commands (onboard + pending: finalize / execute-task / fix / refactor / refresh-docs):

- De-web-bias: expanded inline-doc language coverage from TS/Python-only to 6 ecosystems (TS, Python, Rust, Go, Java/Kotlin, Swift) + "other" fallback. Replaced JSDoc-specific tag references (`@param`/`@returns`/`@example`) with pattern-pairs covering Rust `# Arguments`, Python "Returns:", KDoc `@sample`, etc.
- Runtime-neutral: replaced Claude-only `/onboard` / `/refresh-docs` with `{{cli.sigil}}` markers. Extended `scripts/generate-agents.py` to substitute `{{cli.*}}` markers at generate time — infrastructure benefit beyond this agent: every future agent source can use `{{cli.sigil}}` / `{{cli.primer}}` / `{{cli.subagent}}` / `{{cli.attribution}}` and get correct per-runtime emission.
- Alignment fixes: "two modes" → "three modes" (was missing Refresh); per-command Input You Receive contract matching all 4 invocation shapes; inline-doc responsibility split (verify-only for finalize/execute-task per execute-task's Rule 423; write path for fix/refactor); per-location doc templates matching onboard's Documentation Requirements.
- 2-pass audit: 8 findings total — see commits `8b28c8e`, `a56510a`. Structural drift fixed (orphaned heading), refresh-docs leak into Normal Mode scope removed, per-layer skip logic (Layer 1 inline vs Layer 2 docs/) disambiguated.

### ✅ Phase A (partial) — agent-level variation-marker substitution (rev 11)

`scripts/generate-agents.py` now runs `lib.variation_markers.substitute()` on agent body + description before emitting — matches the pipeline already used by `scripts/emitters/claude.py` and `scripts/emitters/codex.py` for commands. Single source of truth for `{{cli.*}}` values (`scripts/lib/variation_markers.py`) now drives all template kinds: commands, command references, and agent files. Tier placeholders (`{{CLAUDE_TIER_*}}` / `{{CODEX_TIER_*}}` / `{{CODEX_REASONING_*}}`) remain wizard-time substitutions per agents.md §6.4.

### Codex sigil verified via context7

`{{cli.sigil}}` for Codex was `""` (empty) in an earlier draft — **wrong per Codex CLI `turn/start` API docs** (verified via context7 against `/openai/codex`). Codex skills are invoked as `$<skill-name>` in user text. Corrected to `"$"` in `variation_markers.py`. generate-corellm.py already had `output.sigil: "$"` for Codex, so coreLLM output was correct all along; this brings the command/agent emitter pipeline into alignment.

---

## 4. What's next

### Context for the next session (continuing from a new terminal)

**What's been done as of this handoff**:
- `/setup-wizard`, `/onboard`, `/constitute` promoted and production-usable (commands folder, not `_pending/`).
- `tech-writer` agent reviewed + aligned. Remaining 15 agents still need the same treatment.
- First cross-runtime parity test completed (wizard phase only) — **18 divergences** logged in `codex-port/phase-R/parity-findings.md` (summary table + 6 detailed entries, sorted HIGH → MEDIUM → LOW).
- Install-time placeholder blocker fixed (`scripts/lib/install_defaults.py` + generate-agents.py + config.toml + wizard spec rewrite). Fresh installs now boot without manual patching.
- Positioning locked as Option C (portability-first) and CLI surface capped at 3 commands — see `§9` in this file.

**Test infrastructure still live** (git worktrees under `~/Projects/`):
- `testParity/` on branch `claude-parity` — post-wizard Claude-side state committed
- `testParity-codex/` on branch `codex-parity` — post-wizard Codex-side state committed
- Both share one `.git/` (at `testParity/.git/`). Source (`db-cse-ui-strata/`) duplicated in each, pinned to the same commit `9354389c6`.
- Ready for Run 2 whenever the spec fixes land. See "How to run this test again" in `codex-port/phase-R/parity-findings.md`.

### Immediate (next session)

Priority ordered — HIGH parity findings cluster at the top, single-leverage fix for Finding 3 first:

1. **Finding 3 — forced detection checklist** (single highest-leverage change; proposed fix collapses Findings 3, 6, 7, 8, 10, 14, 15, 16 — eight findings at once). Add explicit per-category checklist to `src/commands/setup-wizard/references/detect.md` that both runtimes must fill out as structured output, not free-form prose. See Finding 3's "Proposed fix" in parity-findings.md for the exact checklist template.

2. **Finding 4 — no-batching rule for `{{ask}}` blocks** (HIGH, affects every interactive command). Add prominent instruction to `setup-wizard/main.md` IMPORTANT RULES: "Each `{{ask}}` block is exactly one user-input stop. Do NOT batch multiple questions into a single prompt. For conditional sub-follow-ups (Q11 Multiple, Q11 Runtime-assisted), wait for the primary answer before computing the follow-up." Extend same rule to `constitute/main.md`, `onboard/main.md`, and any future command using `{{ask}}`.

3. **Finding 2 — wrapper-mode git commands anchor on SOURCE_ROOT** (HIGH, correctness bug). In `detect.md`, explicitly state that all git operations in wrapper mode MUST target `$SOURCE_ROOT/.git`. Add concrete command template: `git -C "$SOURCE_ROOT" rev-parse --abbrev-ref HEAD`.

4. **Finding 15 — verify which top-level build/lint command is actually correct** for the CSE source. Whichever runtime got it wrong is writing commands that will later fail. Worth resolving before Run 2 so the signal in Run 2 isn't polluted by known-wrong inputs.

5. **Run 2** — reset both worktrees (remove forge artifacts, reinstall, rerun wizard with same answer sheet). Diff against Run 1 baseline and against each other. Verify the 4 fixes above closed the findings they target, and log new findings in `parity-findings.md` under `## Run 2 — <date>`.

### After parity-batch closes

- **Continue agent review one-by-one** — 15 remaining agents in `src/agents/` need the de-web-bias + alignment treatment (same pattern as tech-writer). Priority: agents that commands dispatch to (architect, frontend/backend/db engineer, ac-verifier) before rarely-invoked ones.
- **Promote next command** from `src/_pending/` — likely `/specify` next (wizard's Phase 5 + constitute's Phase 7 both route to it as the next workflow step).
- **Run parity test against onboard + constitute phases** (Run 2 or Run 3, after the wizard-phase batch closes). Those phases weren't in Run 1's scope.

### Medium-term
- Promote remaining 20+ commands one-by-one.
- **Wire WORKFLOW_ENFORCEMENT into every gated command.** Collected by wizard (Q8) and stored in `project-config.json`, but no command currently reads it — all hardcoded to strict flow. Each gated command (execute-task, specify, plan, breakdown, verify, fix, refactor) needs to read it and branch: strict = all gates, moderate = spec + breakdown gates only, light = spec gate only.
- Parity test harness — turn the manual Run 1 workflow into a scripted re-runnable check.
- update.sh multi-runtime support (currently `expand_templateOwned_pairs` handles pair-based mappings; `templateDerived` three-way merge for `generated:agents` and `generated:coreLLM` not yet implemented).

### Longer-term
- Cursor / Gemini emitters.
- Desktop native agent (if demand emerges).
- §9 items (single-runtime default, `add <runtime>` command, packaging decision) — in that order, after agent audits + parity testing stabilize.

---

## 5. Locked architectural decisions

1. **Authoring source under `src/`** — template-neutral location.
2. **install.sh is copy + delegate** — no runtime logic, no detection.
3. **install.sh does NOT detect** — wizard does via LLM with user as arbiter.
4. **Generator = orchestrator + per-runtime emitters** — open/closed.
5. **Python + stdlib only** for emitters.
6. **Three substitution stages**: coreLLM generator → emitters → wizard. Each operates on a different marker namespace.
7. **Phase A acceptance = B (structural match)** under identical wizard answers.
8. **Branch never merges to main.**
9. **Codex commands = skills** (prompts removed in 0.117.0).
10. **Verification is prose-driven and scope-aware; no runtime hooks on either runtime.** Neither Claude nor Codex uses runtime-level hooks (e.g., Claude's `hooks.PostToolUse` is NOT populated; Codex has no equivalent). Verification runs at task boundaries (end of `/execute-task`, `/fix`, `/refactor`), not after every Edit/Write. The verification phase is **scope-aware**: it reads `PACKAGE_STACKS` (from `.devforge/project-config.json`; rendered as `## Packages` in CLAUDE.md / AGENTS.md), maps each touched file to its package via longest-path-prefix match, and runs that package's `type_check_command` / `lint_command` / `build_command`. Files outside any detected package fall back to the primary-stack commands (`TYPE_CHECK_COMMANDS[0]` / `LINT_COMMANDS[0]` / `BUILD_COMMANDS[0]`). `"N/A"` commands are skipped silently (not a failure). Self-repair loop (up to 3 attempts) wraps the checks. Rationale: runtime hooks can't do per-file routing, so they run the wrong command for non-primary-stack files in monorepos — prose-driven verification gives the LLM access to `PACKAGE_STACKS` and reasoning loop, enabling correct per-package scoping. Behavior documented in the shared `### Verification (explicit, scope-aware — no runtime hooks)` section of CLAUDE.md / AGENTS.md (generated from SOURCE.md); implemented in `/execute-task` Phase 3.2.
11. **CoreLLM: single SOURCE.md** with `{{output.*}}` markers and `{{#runtime}}` conditionals → generates per-runtime output files. Adding a runtime = one dict entry.
12. **Uniform tier key naming**: `{{RUNTIME}}_TIER_{{ROLE}}` with optional `_MODEL` suffix for overrides.
13. **Incremental command migration** via `src/_pending/commands/`.
14. **`.devforge/`** is the cross-runtime shared directory. All shared state (project-config, memory, session-state, wip, baselines, storage-rules) lives here — not in `.claude/` or `.codex/`.
15. **Wizard asks, never infers** for project state (empty/greenfield/brownfield), default branch, and project name. LLM detection reserved for tech-stack scanning only.
16. **Agent selection is LLM-driven** — "database layer detected" not "has prisma/typeorm/sequelize". No hardcoded framework lists in selection logic.
17. **MCP configs are per-runtime** — `.mcp.json` (Claude) and `.codex/config.toml` (Codex). Both pre-loaded with context7.
18. **Wizard STEP 5 populates, STEP 6 generates** — different operations, different rules. STEP 5 never creates files. STEP 6 creates/deletes files (agents, future: constitution, settings).
19. **`{{ARCHITECTURE_DETAILS}}`** is a single dynamic placeholder — wizard generates relevant fields only, no hardcoded web-centric field list.
20. **Install places all agents, wizard curates** — user sees keep/remove recommendation, confirms/overrides, wizard deletes rejected agents from both runtimes.
21. **Agent sources are universal, not Claude-shaped** — fenced `yaml` meta block (deliberately *not* `---`/`---` frontmatter) + markdown body. Neither runtime is passed through unchanged; both are constructed from scratch. `model_tier` (think/do/verify) is semantic, translated per-runtime into placeholder names.
22. **Runtime config files are per-runtime native, no forced symmetry** — Claude gets `.mcp.json` + `.claude/settings.json`; Codex gets one unified `.codex/config.toml` that covers MCP + model + sandbox + approval. Asymmetric file count is a feature, not a bug: each runtime gets the shape it natively uses.
23. **Runtime configs are projectOwned, not templateOwned** — install drops initial version with `{{PLACEHOLDERS}}`, wizard populates, user customizes thereafter; update.sh never overwrites. No baseline needed (no three-way merge).
24. **Claude `permissions.allow[]` ships minimal**; wizard adds MCP tool-names conditionally (chrome-devtools on web + runtime-AC). Mirrors existing MCP server-addition logic. Codex has no allowlist; uses `approval_policy` instead.
25. **Codex project-level config.toml doesn't set model/reasoning defaults rigidly** — `{{CODEX_MODEL_DEFAULT}}` maps from `CODEX_TIER_DO_MODEL` override or falls back to `"gpt-5.4"` (Codex's documented default). `{{CODEX_APPROVAL_POLICY}}` maps from Q6 WORKFLOW_ENFORCEMENT (strict→untrusted, moderate→on-request, light→never).
26. **Runtime selection is a first-class install option**, not a post-install trim step. `install.sh --runtime <csv>` filters at generation time (corellm, agents, emitters) and at file-copy time (MCP/settings/config). No flag = all registered runtimes. Adding a runtime: one entry in `VALID_RUNTIMES` + dict entry in each generator + one line in `installed_clis()` / `print_launch_hints()`.
27. **Closing launch instructions are per-runtime**, never generic. Claude Code uses `/setup-wizard`; Codex CLI uses natural-language skill invocation ("ask it to run the setup-wizard skill"). Codex has no slash-command syntax for skills — printing `/setup-wizard` under a Codex-only install would be wrong.
28. **Wizard STEP 5 uses presence guards, not flow branches**, to survive single-runtime installs. Each substep checks file existence before reading; missing files are silently skipped. No `if runtime == claude` conditionals in wizard prose — keeps wizard single-codepath, new runtimes don't require wizard surgery.
29. **Committee-mode `/plan` (if built) is runtime-asymmetric by design.** Claude Code executes committee members as parallel Agent invocations (tool-level parallelism). Codex either runs sequential per-package reasoning loops within a single Turn or does not ship committee mode at all (decided post-stage-1 based on evidence). Both runtime paths produce the same `plan.md` artifact shape — downstream commands (`/breakdown`, `/execute-task`, `/review`) are runtime-blind. Building multi-instance Codex orchestration (worktree-based, à la Oh My Codex) to achieve parity is out of scope — that's a different product. Rationale and verification in section 8.9.
30. **Folder-based commands use CLI-agnostic source naming; emitters rename and rewrite paths at install time, colocating references with the main command in each runtime's native layout.** When a command grows beyond a single file, it becomes a folder under `src/commands/<cmd>/` with `main.md` as the entry point and `references/*.md` as helpers (one level deep, per Codex best practice). Source filenames never hardcode runtime-specific names (no `SKILL.md` in source, no `.claude/` paths). Reference files refer to each other by relative path (`references/<helper>.md`), which emitters rewrite at emit time to the runtime's native target.

    **Emission layout (both runtimes):**

    | Source (CLI-agnostic) | Claude emit | Codex emit |
    |---|---|---|
    | `src/commands/<cmd>/main.md` | `.claude/commands/<cmd>.md` | `.agents/skills/<cmd>/SKILL.md` (YAML-frontmatter-wrapped) |
    | `src/commands/<cmd>/references/<h>.md` | `.claude/commands/<cmd>/references/<h>.md` | `.agents/skills/<cmd>/references/<h>.md` (canonical Codex sibling) |

    **Path rewriting rule:** Every occurrence of `references/<h>.md` in source main and references is rewritten per-runtime at emit time — Claude references point to `.claude/commands/<cmd>/references/<h>.md`, Codex references point to `.agents/skills/<cmd>/references/<h>.md`. Implemented in `scripts/lib/command_source.py` via `rewrite_refs(text, target_prefix)` + `processed(source, target_prefix)`. Both emitters share this helper, supplying their own target prefix.

    **Colocation rationale:** references live alongside the main command in each runtime's native layout — Codex gets canonical `SKILL.md`-sibling `references/` (preview-friendly); Claude gets nested `<cmd>/references/`. Each runtime's cross-references inside helpers resolve to its own location (self-consistent within a runtime). Duplication cost: identical text with runtime-specific paths, ~KB scale, negligible. `.devforge/` stays pure STATE (project-config, memory, session-state, wip, baselines) per decision #14 — no command CONTENT mixed in.

    **Trade-off accepted:** Claude's nested references register as namespaced slash commands (`/<cmd>:detect`, `/<cmd>:questions`, etc.) and appear in autocomplete. Cosmetic clutter, not functional. The LLM doesn't auto-invoke them; the user wouldn't either. Outweighed by Codex native preview ergonomics + semantic clarity of `.devforge/` as state-only.

    **Reference files never name the orchestrator directly** ("the wizard orchestrator" is CLI-neutral; "SKILL.md" / "main.md" is not). Established during setup-wizard split; applies to all future multi-file command migrations.

---

## 6. Open decisions

1. Constitution.md emission — shared step or per-emitter?
2. Extensions file (`.devforge/extensions.yml`) — name/location, lower priority.
3. Test target for parity — `testSpawn` or scaffold fresh?
4. Codex CLI installed + authenticated for parity testing?
5. ~~Agent templates: do they need a coreLLM-style single-source generator~~ — **resolved**: yes, universal fenced-yaml source with per-runtime emit-from-scratch. See decision #21.
6. `[notify]` hook in `.codex/config.toml` — deferred; no clear use case yet. Session-end notification is the closest analog to Claude's Stop hook.
7. **Hardcoded literals — periodic review**. A small set of vendor-specific strings are baked into the template as defaults. Each will drift as upstream evolves. Review cadence: whenever touching the relevant integration, or at minimum during any context7 snapshot version bump for the upstream tool.

    **Known literals**:
    - `"gpt-5.4"` — Codex default model, in `populate.md` 5.2 as the fallback `{{CODEX_MODEL_DEFAULT}}` when the user doesn't override. Codex's own default evolves with new releases. Docs don't explicitly document `config.toml` behavior on a missing `model` key, so we ship the literal rather than omit the field. Options when reviewing: (a) bump to the newer documented default, (b) empirically test whether omitting the `model` key makes Codex fall back to its internal default (if yes, switch to omitting), (c) externalize to a `scripts/defaults.json` for easier bumps.
    - `chrome-devtools-mcp` — Anthropic-authored chrome-devtools MCP server npm package (unscoped; verified via `npm view` 2026-04-22 — earlier drafts had a wrong `@anthropic/chrome-devtools-mcp` scoped name that 404s). Defined as `CHROME_DEVTOOLS_MCP_PACKAGE` in `populate.md`'s "Drift-risk literals" section and referenced from both the `.mcp.json` and `.codex/config.toml` entries in §5.4 (emitted when Q11 runtime-assisted AC verification is chosen for a web frontend or full-stack app). If Anthropic renames or splits the package, update the literal in one place.

---

## 7. Out of scope

- Cursor / Gemini support (later phase)
- Codex cloud mode (network sandbox breaks MCP)
- Gemma / local models
- Merging to main
- Desktop native agent (revisit if demand emerges)
- ML/data science agent (revisit if demand emerges)

---

## 8. Architect role redesign & committee pattern (design, 2026-04-20)

Design work from a long conversation refactoring the architect role. Split into (a) changes already made in this branch and (b) designed-but-unbuilt future phases. The future phases are the interesting part — they're where codex-port turns into a real refactor.

### 8.1 Changes already made (this branch)

Small, landed edits consistent with purified architect role:

- **`src/agents/architect.md`** — full rewrite as pure director. Never writes implementation code. Owns `/plan` and `/breakdown`. Consults specialists, synthesizes in own voice (no rubber-stamping), always terminates the decision chain, never consults the agent that asked. Explicit refuse-and-route script for implementation asks. Multi-stack-aware opening (labeled `Project frameworks` / `Project languages` so comma-joined values render cleanly). Core Expertise section noted as starting context with CLAUDE.md authoritative for multi-stack.
- **`src/_pending/commands/plan.md`** — added `## Role & Delegation` section: architect owns command, orchestrator invokes via Agent tool, consultation rules summarized, reference to architect.md for full rules. Also landed (from earlier in same conversation): algorithmic pattern scan (Signal Scan row, Phase 1.4, `## Algorithmic Patterns` plan template section, Rule 9).
- **`src/commands/setup-wizard.md`** — array rendering for `{{FRAMEWORK}}` and `{{LANGUAGE}}` in STEP 5.1 (CLAUDE.md) and STEP 6.4 (architect only, other agents keep primary-only pending per-agent review).

### 8.2 Designed but not built — per-stack array + per-folder mapping

Currently only `{{FRAMEWORK}}` and `{{LANGUAGE}}` render from arrays. Still single-value and lossy for multi-stack projects:

- `{{ARCHITECTURE}}` — e.g., hexagonal BE + feature-sliced FE can't be expressed
- `{{ERROR_HANDLING}}` — strongly language-bound (exceptions vs Result vs discriminated unions)
- `{{API_LAYER}}` — usually single but array-for-safety (multi-BE, BFF layers)
- `{{TESTING}}` — strongly language-bound (pytest/vitest/go-test are exclusive per stack)

**Proposal**: parallel arrays indexed by stack, same pattern as `LANGUAGES` / `FRAMEWORKS`. Rendering for architect + CLAUDE.md uses **paired rendering**: `"hexagonal (FastAPI/Python), feature-sliced (Next.js/TypeScript)"`. Auto-switches to multiline list at ≥3 stacks. Setup-wizard detects multi-stack from `len(LANGUAGES) > 1` and branches Q4/Q5/API-layer/testing to ask per-stack, with a "same across stacks" shortcut to avoid Q&A fatigue. Other agents keep primary-only until each is reviewed.

**Separate but related**: per-folder stack mapping is currently missing. setup-wizard detects "TypeScript and Python exist" but not "which folder is which." Paired rendering tells architect *what* stacks exist, not *where* they apply. Architect re-infers folder-to-stack from `{{PROJECT_STRUCTURE}}` tree every decision.

Proposed `PACKAGE_STACKS` data structure (per-folder, structured):

```jsonc
[
  { "path": "apps/web", "language": "TypeScript", "framework": "Next.js",
    "architecture": "feature-sliced", "error_handling": "Result<T,E> via neverthrow",
    "api_layer": "tRPC client", "testing": "vitest" },
  { "path": "services/api", "language": "Python", "framework": "FastAPI",
    "architecture": "hexagonal", "error_handling": "exceptions + returns.Result",
    "api_layer": "REST + OpenAPI", "testing": "pytest" }
]
```

Rendered into a new `{{PACKAGE_STACKS}}` CLAUDE.md section as a table. setup-wizard detects package roots by scanning for manifest files (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pubspec.yaml`, `*.csproj`, `mix.exs`). Each package's language/framework mostly auto-detectable from its manifest.

### 8.3 Designed but not built — architect committee pattern

**Intent**: handle multi-stack features without either (a) one architect holding all stacks shallowly, or (b) parallel per-stack architects producing incompatible outputs.

**Mechanism**: cross-cutting decisions made upfront by a lead architect BEFORE parallel per-stack architects fan out. Alignment by construction (shared contract constraints), not by retrofitting.

Real-world analog: staff engineer + domain architects. Staff engineer defines interfaces between domains (API shape, auth flow, shared data contracts); domain architects work in parallel within their boundaries.

#### Phases of `/plan` under committee mode

1. **Pre-requisite mappings** (from upstream): requirements-researcher produces per-package affected-scope mapping during `/specify`; `CLAUDE.md` carries `PACKAGE_STACKS`.
2. **Lead architect phase** (solo invocation): reads mapping + spec, identifies cross-cutting concerns, defines contracts (API shape, auth flow, shared types, data shapes, error-propagation boundaries), may consult api-designer / security-reviewer in parallel.
3. **Committee phase** (parallel per-stack architect invocations): one invocation per affected package, each scoped via user-prompt input (*"reason about `services/api` only, which uses Python + FastAPI + hexagonal; these contracts apply: [...]"*), each may consult specialists for domain depth within scope, each returns a per-package sub-plan respecting contracts.
4. **Synthesis phase** (lead architect): validates committee outputs are contract-compliant, merges into unified plan, iterates if violations found.

Single-stack case: committee of size 1, phase 2 contracts trivial, phase 4 passthrough. No complexity penalty for simple features.

#### Why this resolves earlier concerns

Earlier discussion rejected simpler "parallel per-stack architects" pattern because cross-cutting concerns would force post-hoc reconciliation, parallel architects would propose incompatible contracts, coordination overhead would exceed single-architect simplicity. The committee pattern dissolves those by making contracts the first-class coordination artifact — defined once, enforced by construction, not retrofitted.

#### Arguments for

- **Deeper per-stack reasoning** from focused-context invocations (even though agents don't have human cognitive limits, scoping is still an output-quality lever)
- **True parallelism on Claude Code** — 3-stack features see ~3× faster `/plan` (minus pre-contract phase). See 8.9 for Codex caveat — parallelism is runtime-dependent.
- **Alignment by construction** — contracts pre-defined, committee works within them
- **Dynamic committee size** — matches feature scope automatically, no over-engineering
- **Real-world proven pattern** — not speculative
- **Composable with existing design** — committee members follow consult-specialists-synthesize-in-own-voice rules we already built; fractally consistent

#### Honest concerns

- **Lead architect still holds coordination layer** — "single architect handles everything" is relocated, not eliminated. Mitigation: lead's job is smaller (contracts + validation, not full per-stack depth).
- **System prompt static across committee members** — can't dynamically vary "BE architect" vs "FE architect" at system-prompt level. Mitigation: user-prompt scoping is sufficient.
- **Complexity jump in /plan** — today one call, proposed 3 phases. Mitigation: complexity tracks feature shape; single-stack execution is passthrough.
- **Bigger prerequisite set** — requires requirements-researcher + PACKAGE_STACKS data. Both already on roadmap as independent improvements.
- **Lead architect still has generalist burden for contracts** — defining BE/FE API contract needs both-sides reasoning. Mitigation: lead consults api-designer / security-reviewer for contract definition.

### 8.4 Prerequisites for committee mode

Must exist before stage 2 is viable:

1. **`requirements-analyst` / `requirements-researcher` agent** (or equivalent mechanism in `/specify`) producing per-package affected-scope mapping as part of the spec. See `memory/project_requirements_analyst_recommendation.md` — currently deferred until evidence of spec-quality issues; committee pattern adds new justification beyond delegation consistency.
2. **`PACKAGE_STACKS` data in CLAUDE.md** — per-folder stack mapping; setup-wizard populates; single source of per-folder truth.
3. **Per-stack array rendering for `{{ARCHITECTURE}}`, `{{ERROR_HANDLING}}`, `{{API_LAYER}}`, `{{TESTING}}`** — feeds `PACKAGE_STACKS` with correct data.

Without (1): committee can't be targeted — no mapping of spec → affected packages.
Without (2): committee can't be scoped — no per-package conventions to pass.
Without (3): conventions passed would be single-value summaries, losing precision.

### 8.5 Staged implementation plan

#### Stage 1: Infrastructure (useful on its own, no committee yet)

- Extend setup-wizard Q&A for per-stack arrays (Q4/Q5 branching, Q-for-API-layer, Q-for-testing)
- Extend setup-wizard rendering rules for architect + CLAUDE.md (paired per-stack rendering)
- Build `PACKAGE_STACKS` data structure: package-root detection via manifest-file scanning, per-package stack capture, rendering into new `{{PACKAGE_STACKS}}` CLAUDE.md section
- Update single-architect `/plan` to READ these mappings and reason per-package (implicitly)
- Propagate per-agent review (each specialist agent template gets migrated from primary-only to array-rendered substitution as it's touched)

**Validate after stage 1**: does single-architect `/plan` produce better multi-stack plans with this infrastructure? If yes, stage 1 may be sufficient. If shallow/wrong, stage 2 justifies the complexity.

#### Stage 2: Activate committee mode

**Only if stage 1 is solid AND evidence shows single-architect plans getting shallow on multi-stack features.**

- Build requirements-researcher (or extend `/specify` orchestration) to produce affected-packages mapping
- Refactor `/plan` command into contracts-phase → committee fan-out → synthesis phases
- **Split `architect` into two agents** (see design note below): rename current `architect.md` → `lead-architect.md` (cross-cutting coordinator, contracts author, synthesizer, sequence-decider for Codex) and introduce new `domain-architect.md` (think-tier, per-package architecture scope, consults specialists for depth within one package, returns per-package sub-plan respecting lead's contracts)
- Define contract artifact format (serialization from contracts-phase → committee prompts)
- Define synthesis validation criteria (how synthesis-phase detects contract violations)
- Add orchestration logic in `/plan` for committee fan-out (runtime-branched per decision #29)
- Update existing memories to reflect the architect split (lead vs domain) and requirements-researcher becoming load-bearing
- Rename cascade: every reference to `architect` in `setup-wizard.md`, `plan.md`, `breakdown.md`, `execute-task.md`, `CLAUDE.md`, `AGENTS.md`, `SOURCE.md`, emitters, manifest, docs

**Design note — why split into two agents, not modes of one:**

Earlier drafts of section 8 suggested "three invocation modes (solo, lead, member) of one architect, expressed via user-prompt scoping." That framing under-weighted the role specialization. The honest position:

- **Lead architect's cognitive scope**: cross-cutting reasoning, API contracts, data flow between packages, coordination, sequencing, synthesis. System-of-systems thinking.
- **Domain architect's cognitive scope**: deep per-package architecture within one stack's idioms (hexagonal-in-Python vs feature-sliced-in-TypeScript), framework-specific patterns, package-internal layer decisions. Single-system depth.

These aren't the same cognitive scope with different attention windows — they're genuinely different framings. Real-world analog (staff engineer + domain architects) invoked in 8.3 supports role specialization, not scope variation. If the two roles weren't meaningfully different, parallelizing them wouldn't buy anything over single-architect, and the committee pattern's entire argument collapses.

So: two agents, two system prompts, each focused. Not one agent juggling three modes. The "one agent, scoped invocations" forge idiom (which applied correctly to specialists like db-engineer or code-reviewer) doesn't apply here — specialists have one scope with different inputs; lead and domain have structurally different scopes.

**What survives from the earlier "unification" argument:**

- Role sprawl is still a real concern → mitigated by this being stage-2-only. If committee mode never ships, the split never happens. Not speculative infrastructure.
- Migration cost is real → contained to one coordinated rename cascade at stage 2 build time, not piecemeal drift.
- Runtime asymmetry (decision #29) → lead and domain both exist in the roster regardless of whether Codex uses parallel or sequential committee. On Codex sequential, lead invokes domain sequentially via tool-level Agent calls within one Turn (still works).

**What this changes about current state (8.1):**

Nothing. Current `architect.md` in the main branch is the future `lead-architect.md` by content (pure director, owns `/plan` and `/breakdown`, consults specialists, synthesizes, terminates decision chains). The purification work already done IS the lead role. Domain architect is new when stage 2 builds. Treating today's `architect.md` as "proto-lead-architect" is fine — no rework needed until stage 2.

### 8.6 Open questions to resolve before building stage 2

1. **Evidence question**: concrete signals that single-architect plans are shallow on multi-stack work. Without this, stage 2 is speculative — stage 1 first, measure, then decide.
2. **Where do contracts live?** In plan.md as a top-level section? Separate `contracts.md` file (already exists for API contracts — reuse or new)?
3. **Who synthesizes, literally?** Same architect invocation (stateful across phases) or new "lead architect" call at end? State management across phases is non-trivial in agent workflows.
4. **How granular is committee membership?** Per package? Per language? Per stack-framework combo? Different granularities produce different committee sizes for the same feature.
5. **Contract revision mid-committee**: if a member discovers pre-defined contract is impossible for its stack, halt, consult lead, or raise to user?
6. **Cost**: N committee members × full context (spec, plan-so-far, CLAUDE.md, contracts) = N× token cost. Worth it for decision-quality gain, especially at scale?
7. **Is committee mode worth building even if Codex doesn't get the speed benefit?** (See 8.9.) If the structural reasoning improvement justifies it on Claude Code alone, build it there and accept the runtime asymmetry. If not, drop committee mode entirely and keep single-architect on both runtimes.
8. **Does `domain-architect` need per-stack variants eventually?** A Python domain-architect might have different framing than a TypeScript domain-architect. One prompt with CLAUDE.md driving stack-specific reasoning vs. per-stack-framework domain architects. Defer until real usage signals.

### 8.7 Memory anchors

Related memories already saved (separate from this plan):

- `~/.claude/projects/-Users-mykolakudlyk-Projects-ai-dev-team-forge/memory/project_architect_role_scope.md` — architect purification + smart hands decision
- `~/.claude/projects/-Users-mykolakudlyk-Projects-ai-dev-team-forge/memory/project_requirements_analyst_recommendation.md` — defer `requirements-analyst` until evidence

When stage 2 is built, both memories need updating to reflect new architect invocation modes and requirements-researcher becoming load-bearing.

### 8.8 Path forward when revisiting

Suggested sequence:

1. Decide on per-stack array proposal + `PACKAGE_STACKS` (section 8.2) — that's stage 1 infrastructure partway done.
2. Decide on `requirements-analyst` creation. Committee pattern adds justification beyond delegation consistency — it becomes a prerequisite for stage 2, not just a speculative addition.
3. Build stage 1 fully. Use forge with it. Observe whether single-architect multi-stack plans are sufficient or shallow.
4. If shallow: build stage 2 (committee mode) **Claude-Code-only** per runtime decision in 8.9. If sufficient: stage 2 stays designed-but-unbuilt.

**Discipline**: don't build stage 2 speculatively. Stage 1 is useful on its own. Stage 2 only pays off if there's actual evidence of single-architect shallowness on real forge usage.

---

### 8.9 Runtime caveat (Codex) — verified 2026-04-20

Initial drafts of this section assumed committee-mode parallel architect invocations work symmetrically across Claude Code and Codex. **That assumption is wrong for Codex.** Verified against official Codex docs via context7.

#### What Codex actually supports

- **Parallel tool calls** within a single Turn: YES. Controlled by `parallel_tool_calls` on the Responses API and `supports_parallel_tool_calls = true` on MCP servers. Standard tool-level concurrency.
- **Parallel Tasks/Turns within a single Codex instance**: **NO.** Codex protocol v1 explicitly states: *"only one Task can be run at a time within a single Codex instance. For applications requiring parallel tasks, it is recommended that a separate Codex instance be run for each thread of work."* Codex SDK docs reinforce: *"only one active turn consumer per client at a time."*
- **Parallel multi-agent work in Codex ecosystem**: achieved externally via multiple Codex instances with isolated git worktrees (the `Oh My Codex` / `yeachan-heo` pattern). Requires external orchestration, shared-state coordination, and worktree management.

#### Implication for committee mode

The committee pattern's parallelism advantage (section 8.3, "true parallelism — 3× faster") depends on spawning multiple architect invocations that run concurrently. On Claude Code, Agent-tool calls are tool-level and genuinely parallelizable — the design works as drafted. On Codex, architects-as-subagents would be Task/Turn-level, which Codex serializes within a single instance. To get actual parallelism on Codex, committee mode would require multi-instance worktree orchestration — substantially more infrastructure than Claude Code's in-session Agent tool model.

#### Decision: multi-instance Codex orchestration is out of scope

Building worktree-based multi-instance coordination for committee-mode parallelism is overkill for forge's scope. That's infrastructure on par with the Oh My Codex project itself — not a small addition to forge.

**Runtime strategy for committee mode (if built):**

- **Claude Code**: committee mode as designed — parallel architect invocations via Agent tool, synthesis via lead architect.
- **Codex**: committee mode falls back to **single-architect with per-package reasoning loops**. Same pattern conceptually (contracts upfront, per-package analysis, synthesis), but executed sequentially in one Turn. Loses the parallelism speed advantage; keeps the structural reasoning advantage (per-package focused context, contract-enforced alignment).

This is a meaningful design asymmetry between runtimes. Acceptable because:
- The structural benefit (focused per-package reasoning within pre-defined contracts) survives on Codex — just without the speed multiplier
- Alternative (build multi-instance Codex orchestration) adds a fundamentally different layer of infrastructure
- forge's strategic posture is "differentiation accepts maintenance cost" (section 1) — but that applies to surface-level runtime differences (skill vs command syntax, settings shape), not to deep architectural capabilities that would require building parallel-Codex-orchestration from scratch

#### Impact on stage 2 prerequisites (section 8.4)

Add to the prerequisite list:

4. **Runtime strategy decision documented in `/plan` command logic** — when committee mode activates on multi-stack features, the command branches on runtime: Claude Code path uses parallel Agent invocations, Codex path executes sequential per-package reasoning loops. Both produce the same artifact shape (unified plan.md with per-package decisions and shared contracts).

#### Impact on arguments for committee mode

The "true parallelism — ~3× faster" bullet in 8.3 is **Claude-Code-only**. Codex gets no speed benefit — only the structural reasoning benefit. Worth being honest about: on Codex, committee mode's sole value is focused-context reasoning + explicit contract enforcement, not throughput.

If that structural-only benefit isn't enough to justify the complexity (which is a legitimate position), committee mode is best scoped as a **Claude-Code-only feature** and Codex sticks with single-architect for multi-stack work indefinitely. That's a defensible asymmetry — document it as such rather than pretending symmetry.

#### Open question added to 8.6

7. **Is committee mode worth building even if Codex doesn't get the speed benefit?** If the structural reasoning improvement justifies it on Claude Code alone, build it there and accept the runtime asymmetry. If not, drop committee mode entirely and keep single-architect on both runtimes.

#### Other places in section 8 affected by this finding

- **8.3 "Phases of `/plan` under committee mode"**: phase 3 ("Committee phase (parallel per-stack architect invocations)") is parallel on Claude Code, sequential on Codex. Phase framing itself is unchanged.
- **8.5 stage 2 implementation**: "Add orchestration logic in `/plan` for committee fan-out" must include runtime branching.
- **Memory entries**: when stage 2 is actually built, `project_architect_role_scope.md` and `project_requirements_analyst_recommendation.md` should both note the runtime asymmetry explicitly.

#### Codex sequential mode — sequence definition design

On Codex, committee mode runs as a single Turn with lead architect walking packages sequentially. Three sub-questions resolved:

**1. Who decides the processing order?**

Lead architect, during the contracts phase (same phase where cross-cutting contracts are defined). No new role or invocation — coordination-layer decisions (contracts + ordering) belong together.

Output of contracts phase gains a new section for Codex sequential mode:

```
## Cross-Cutting Contracts
[API shape, auth flow, data shapes, error-propagation boundaries]

## Processing Order (Codex sequential mode only)
1. packages/shared — dependency root, others consume its types
2. services/api — defines the contract surface FE will consume
3. apps/web — consumes both
```

On Claude Code this section is omitted (parallel execution — order irrelevant).

**2. How is the order rule defined?**

Three-tier fallback:

1. **If `PACKAGE_STACKS` captures inter-package dependencies** (from workspace manifest analysis — `package.json` deps, `pyproject.toml` references, monorepo tool config), use the dependency graph. Topological sort. Packages with no dependents go first.
2. **Else architectural-layer heuristic**: shared/types → data/infrastructure → domain → api/interface → presentation. Applied per-package based on captured role in PACKAGE_STACKS.
3. **Else ask user.** If heuristics don't produce a clear order (two packages at same layer with no dep relation), lead architect presents candidates and asks user to confirm order.

Tier 1 is the common case. Tier 2 handles simpler projects. Tier 3 is the escape hatch.

**3. How does state flow between sequential passes?**

Single Codex Turn, conversational accumulation, no serialization. State between passes is "previous reasoning in the same conversation" — Codex's context window handles it natively.

Flow within the single Turn:

```
Turn start
  → Phase 2: lead architect defines contracts + processing order
  → Phase 3 pass 1: lead architect reasons about package[0] given contracts
     (may parallel-consult specialists — tool-level parallelism, Codex-supported)
  → Phase 3 pass 2: lead architect reasons about package[1] given contracts + previous decisions
  → Phase 3 pass N: ... package[N-1]
  → Phase 4: lead architect synthesizes unified plan.md
Turn end
```

No inter-instance coordination, no filesystem artifacts between passes, no external orchestration.

**Bonus — specialist consultations stay parallel on Codex.** Within each sequential package pass, lead architect can still invoke multiple specialists in parallel because consultations are tool-level, not Task-level. Codex supports parallel tool calls within a single Turn (`parallel_tool_calls = true` on MCP servers or Responses API). So the "consult db-engineer + security-reviewer + api-designer simultaneously" pattern works on Codex for specialists — just not for architect-level work. Codex committee mode keeps tool-level parallelism even though architect-level execution is serial across passes.

**What's still uncertain (for when stage 2 is built)**:

- **Dependency graph accuracy.** Getting inter-package deps right from manifest analysis is tractable for npm/pnpm workspaces, harder for mixed-language monorepos (e.g., Python service consumed by a JS app via HTTP — no declared dep). Edge cases need the heuristic or user-fallback path.
- **Order-independent packages.** Two packages with no dep relation and no cross-cutting concern serialize for no benefit. Probably acceptable overhead, but flag if observed.
- **Very large committees on Codex.** 5+ package feature means 5+ sequential passes in one Turn — context window may get crowded. May need "split into two features" guidance if observed. Hard limit unclear without real-world testing.

---

## 9. Positioning & packaging (post-MVP — deferred to launch prep)

### Positioning: Option C — portability-first

Strategic framing: this is a **CLI-portable workflow kit where portability IS the differentiator**, not a multi-runtime template that happens to also be portable.

Implications:

- **Default install behavior becomes single-runtime**, not "both." Users install for the CLI they actually use; interop becomes a visible upgrade moment via a dedicated `add <runtime>` command.
- **The wow-moment is the second-runtime add**: user runs the add command against an existing Claude-powered project and sees their state, specs, docs, constitution, memory, and agents immediately accessible from Codex. That moment is the marketable story ("your workflow just became portable") — invisible if both ship at once.
- **Marketing/README leads with the portability story**, not the "works with both" frame. "Works with your CLI — becomes portable when you want."

Current default ("install both unless `--runtime` specified") is author-convenience: we built both, easiest to ship both. Kept during development; changed before first public exposure.

### Packaging: stay curl-based during development; decide at launch

Current install: `curl | bash` template copy. No binary on PATH. Users don't re-invoke the installer in normal use, so single-command install is adequate for the current "template-install, mostly touch-and-go" model.

Packaging options at launch:

- **(a)** Stay curl-based. `add` implemented as flag: `curl ... | bash -s -- --add=codex`. No new infrastructure. UX rougher — users remember URL, no tab completion, no discoverability.
- **(b)** Drop a thin wrapper at `.devforge/bin/aidevteamforge` during install; user gets a CLI command without full packaging. Minor PATH concern. Installer self-updates the wrapper on re-run.
- **(c)** Publish as a real package. Prior art: GitHub spec-kit ships `specify-cli` installable via `uv tool install` or `pipx` (direct from GitHub — PyPI publish explicitly disclaimed). First-class CLI, upgrade via package manager, proper subcommand tree.

Deferral rationale: packaging for a user base that doesn't exist is premature. Curl-based install stays until development stabilizes; option choice happens when nearing launch.

### Prior art: GitHub spec-kit (github/spec-kit)

Relevant mechanics worth borrowing:

- **Interactive AI-CLI picker** when `--ai` / `--integration` flag omitted. Arrow-key select over available integrations, sensible default highlighted (currently `copilot`). Source: `src/specify_cli/__init__.py:1151-1158`.
- **Pluggable integration model**: each AI CLI is a `BaseIntegration` subclass (~30 integrations in `src/specify_cli/integrations/`). Maps directly to our per-runtime emitter pattern (`scripts/emitters/<runtime>.py`).
- **First-class incremental add / switch / upgrade**: `specify integration install <key>`, `uninstall`, `switch`, `upgrade`. Our proposed `aidevteamforge add <runtime>` is the direct analog.
- **Single-project centralized dir + per-agent native dirs**: spec-kit uses `.specify/` for shared state + `.claude/skills/`, `.cursor/skills/`, etc. for per-agent artifacts. We already follow this structurally (`.devforge/` shared + `.claude/` / `.codex/` / `.agents/` per-runtime).
- **`uv tool install` from GitHub direct** (no PyPI publish) — lower-friction path than full-registry publish while still giving package-manager UX.

Divergence to be explicit about:

- Spec-kit has ~30 integrations; we have 2 (Claude, Codex) planned, with Cursor/Gemini as later work. Don't over-engineer an integration abstraction for 2 — current emitter pattern is right-sized.
- Spec-kit's surface is broader (presets, workflows, extensions, skills). Our scope is tighter (one workflow: spec → plan → breakdown → execute → verify). Don't inherit surface area just because they have it.
- Spec-kit's skills-mode uses `$speckit-<cmd>` invocation under Codex; we use `$<cmd>` directly. Namespacing choice — revisit only if collision becomes a real issue.

### Maximum CLI surface — hard cap

Even at launch, the CLI surface stays minimal. **Three commands total, hard ceiling**:

1. **`install`** — scaffold template into project (what `install.sh` already does).
2. **`add <runtime>`** — retrofit existing single-runtime install with another runtime. Enables the upgrade-moment UX.
3. **`upgrade`** — pull the latest template files into an existing project (optional; only if we see demand).

**Explicitly out of scope**, even long-term:
- Integration `switch` / `uninstall` — removing a runtime isn't a workflow we need to support. User can `rm -rf .codex/` themselves.
- Extensions / plugins / presets / custom workflows — we ship one workflow, not a framework for workflows.
- Self-upgrade subcommand — `curl | bash` or `uv tool install --force` handles it if we're packaged; scripts handle it if we're not.
- Integration list / info / search — with 2 runtimes (maybe 4 later), a README table is sufficient.

The spec-kit lesson is about **install mechanism** (`uv tool install` direct-from-GitHub, no PyPI), NOT about surface area. If we end up packaging, a minimal Python entry point or a persistent shell wrapper handles 3 commands without needing Typer / Click / Rich or a plugin framework.

This cap exists to prevent future drift toward "while we're adding X, let's also add Y." The tool's value is the spec-driven workflow and the cross-runtime portability. Everything else is noise.

### Roadmap — ordered

1. **Now through end of development**: curl-based install, current default ("both"). No positioning or packaging changes.
2. **After agent audits + cross-runtime parity testing complete**: implement single-runtime default in `install.sh` (detect installed CLI, prompt interactively if ambiguous, keep `--runtime` flag for CI/scripted use). Add install-time messaging explaining what was and wasn't created.
3. **Before first public exposure**: implement `aidevteamforge add <runtime>` command (still curl-based by default). Rewrite README/landing copy around the portability narrative.
4. **Near launch (evaluate then, not now)**: decide (a) / (b) / (c) for packaging. Default answer without new evidence: **(c)** via `uv tool install` from GitHub, following spec-kit's pattern — lowest-friction path to proper CLI UX without registry publishing overhead.

No implementation work from §9 happens until §2 of this roadmap.

---

## 10. Path B — Generator-level Detection Report composition (design, not built)

**Status**: designed, not built. Decision-pending. Picked up by a new chat session when the Python-runtime-dep question is resolved.

### 10.1 Context

R3 (2026-04-24) produced asymmetric closure on Finding 23 (Detection Report YAML emit):
- **Claude-R3**: emitted the fenced YAML Report correctly (with two minor sub-issues: skipped HTML comment markers, abbreviated `packages[]` array). Finding 23 closed on Claude side.
- **Codex-R3**: did NOT emit the YAML. Folded Phase 1 detection into Q0's prompt narrative. Finding 23 still open on Codex.

Codex's post-R3 self-report (from `codex-r3-interview.md`) gave direct evidence:

> "my execution policy still prioritized conversational progress over emitting the structured handoff artifact. current textual reinforcement is not sufficient for me. My R2 prediction was too optimistic."

And Codex explicitly endorsed Path B as the forward direction:

> "Yes, a Python-composed approach would likely work better. [...] structured field-by-field prompting is more reliable than 'emit a whole YAML report now.' If the helper constrained me to fill explicit fields one at a time, I would expect lower drift at the value level too."

**Conclusion**: Path A (pure spec-text iteration) has a ceiling for Codex on emission existence. More spec prose — even with visual markers, causal framing, Phase 2 preflight, no-abbreviation rule — does not change Codex's execution policy. Path B (Python composes YAML from LLM-provided field values) is the evidence-backed next step.

### 10.2 Decision — RESOLVED YES (2026-04-24)

**Python-runtime-dep on target machine**: **YES**. Committing to `python3` as a wizard-time prerequisite.

- **Current state**: target machine already needs `python3` at install-time (install.sh invokes `scripts/generate.sh` → `generate-agents.py` / `generate-corellm.py`). This is a silent requirement today — `install.sh` does not preflight for it; failures surface as generate.sh errors. Wizard runtime (post-install) is Python-free: LLM-driven end-to-end, spec is markdown, LLM reads + reasons + emits.
- **Path B adds**: target machine needs `python3` at *wizard-time* too, not just install-time. Persists the existing dependency temporally. `scripts/lib/detect_report.py` runs during Phase 1.
- **Availability**: macOS 12.3+ ships `/usr/bin/python3`. Most Linux distros default. Windows users often need explicit install.
- **Tradeoff**: better Codex structural parity vs. one more prerequisite for some users.

**Resolution rationale**:
- Codex self-report in `codex-r3-interview.md` is direct evidence Path A has a ceiling on artifact emission ("current textual reinforcement is not sufficient for me").
- Target audience (Claude Code / Codex CLI users) has near-universal Python 3 availability.
- `install.sh` preflight gates Python presence at install time — turns silent wizard-time failure into loud install-time gate.
- 0-runtime-deps positioning tradeoff accepted for the structural-parity win.

**Windows**: in scope. Launcher (`scripts/lib/detect_report`) is a POSIX shell wrapper that selects `python3` / `py -3` / `python` — same shell-environment assumption install.sh already makes (Git Bash or WSL). No separate Windows phase needed.

**Execution plan**: see `codex-port/PATH-B-IMPLEMENTATION.md` — 37 atomic steps across 8 phases, each with approval gate.

### 10.3 Proposed design — Option B1 (field-by-field CLI, Codex's stated preference)

Protocol:
- LLM reads `detect.md` spec, performs detection reasoning (scans files, identifies libraries, applies rules).
- For each Detection Report field, LLM calls:
  ```
  python3 scripts/lib/detect_report.py set <field> --value <value>
  ```
- For each workspace package, LLM calls:
  ```
  python3 scripts/lib/detect_report.py add-package \
    --path <path> --manifest <file> \
    --language-hint <lang> --framework-hint <fw-or-null> \
    --build-command <cmd> --type-check-command <cmd> \
    --lint-command <cmd> --test-command <cmd> \
    --command-source <manifest|fallback>
  ```
- LLM calls `python3 scripts/lib/detect_report.py status` to check progress (which fields still unset).
- LLM calls `python3 scripts/lib/detect_report.py compose` when done.
- Python composer validates everything, writes `.devforge/detection_report.yaml` deterministically.
- Phase 2 preflight reads from `.devforge/detection_report.yaml` (file) instead of conversation history.

Helper state: intermediate state stored in `.devforge/.detection-report-state.json` (deleted by successful `compose`). Allows multi-call field assembly.

### 10.4 Validation rules enforced at set-time

Python composer MUST reject:
- Enum mismatches (e.g., `architecture_shape: "hexagonal-style"` when enum is `[layered, feature-modular, ..., hexagonal, ...]`)
- Required field missing at compose time
- Null value without accompanying reason string
- `add-package` with non-existent `path/manifest` filesystem check (catches hallucinations like R2's `pkg-test`)
- `packages[]` count mismatch with `manifest_count` (catches abbreviation like R3's `# ... 22 more follow same pattern`)
- Library-category field non-null without `evidence` sub-field populated
- Invalid `runtime_url.source` (must be concrete config file path when `source != framework-default`)

### 10.5 Implementation plan (5-day prototype)

**Day 1** — Python module skeleton:
- `scripts/lib/detect_report.py` with CLI dispatch (`set`, `add-package`, `status`, `compose`)
- Schema definition (Python dataclasses or nested dict)
- State file management (`.devforge/.detection-report-state.json`)
- Manual YAML emission (stdlib only — no `pyyaml` dep per locked decision #5)

**Day 2** — Validation logic:
- Enum validation per field
- Required-field tracking
- Null-with-reason enforcement
- Path/manifest filesystem check on `add-package`
- Package count vs `manifest_count` cross-check at compose

**Day 3** — Integrate into spec:
- Rewrite `detect.md` Detection Report section: replace YAML emit description with CLI protocol description
- Remove `<!-- >>> EMIT <<< -->` markers + YAML template (template becomes code, schema stays as human-readable reference)
- Add `install.sh` check for `python3 --version`, fail early if missing

**Day 4** — Downstream readers:
- Update `questions.md` Phase 2 preflight to read from `.devforge/detection_report.yaml` (file-based) not conversation memory
- Update `populate.md` §5.5 to read Report fields from file

**Day 5** — Test & iterate:
- Reinstall `testParity/` and `testParity-codex/` worktrees
- Run wizard on both sides
- Verify identical `.devforge/detection_report.yaml` on both
- Run post-wizard diffs; confirm R3 findings closed

### 10.6 Integration criteria — ship Path B if AND only if

- Prototype catches ALL of: Finding 13 hallucination (pkg-test case), Finding 23B abbreviation (3-entry + comment case), Finding 21 free-form label ("hexagonal-style" case).
- Prototype adds acceptable latency (≤5% increase in wizard runtime) — field-by-field tool calls are cheap per call; total overhead mostly acceptable.
- Python-runtime-dep decision is explicit YES.
- R4 test (wizard with Path B integrated) shows Codex-side Finding 23 CLOSED (YAML emitted) and no regression on Claude side.

**Kill Path B if**:
- Prototype reveals spec-surface complexity that duplicates Path A text (spec + code saying same things differently)
- Python-runtime-dep decision is NO
- R4 shows no structural improvement over Path A (unlikely given Codex's self-report, but possible)

### 10.7 Alternative if Python-runtime-dep NO (Path C — accept asymmetric)

- Keep current Path A spec fixes (commit `4402435` + earlier).
- Accept that Codex does not emit structured YAML Detection Report.
- Downstream phases (Phase 3 populate) continue reading detection context from conversation memory on Codex (works per R3 evidence — `project-config.json` populated correctly despite missing YAML emit).
- Cross-runtime parity at the `.devforge/detection_report.yaml` **artifact** level is not achieved; parity at `project-config.json` + `CLAUDE.md` / `AGENTS.md` **content** level is ~80–90% and improvable via continued Path A tightening.
- Document Codex's asymmetric behavior in `parity-findings.md` as a known limitation; close Finding 23 as "Path A ceiling reached; accept as-is."

Path C is honest engineering if Python-at-runtime is rejected. Not defeat.

### 10.8 Rollback strategy

Current state (pre-Path-B) is preserved in git:
- Branch: `feature/codex-support`
- Checkpoint commit: `4402435` ("setup-wizard: pre-R4 spec fixes")
- Tag (to be added): `r3-complete-path-a`

If Path B is built and fails integration:
- Delete the Path B work branch
- `feature/codex-support` is unchanged and ready for Path C framing or continued Path A iteration

If Path B is built and succeeds:
- Merge Path B branch into `feature/codex-support`
- Continue R4+ testing with Path B integrated
- Tag remains as historical anchor

### 10.9 Files Path B would touch

- **New**: `scripts/lib/detect_report.py`
- **Modified**: `src/commands/setup-wizard/references/detect.md` (Detection Report section rewritten)
- **Modified**: `src/commands/setup-wizard/references/questions.md` (Phase 2 preflight reads file)
- **Modified**: `src/commands/setup-wizard/references/populate.md` §5.5 (reads from file)
- **Maybe modified**: `install.sh` (Python 3 presence check at install time)

### 10.10 Scope — what Path B does NOT solve

- **Value-level drift**: if LLM picks `hexagonal` when evidence indicates `clean`, Python validates enum membership (both valid) but can't judge correctness. Still requires Path A's Q4 cues in `questions.md`.
- **Downstream Phase 4/5 divergences**: Path B only covers Detection Report. Phase 4 agent curation and Phase 5 summary remain fully LLM-driven.
- **Cross-runtime answer-sheet consistency**: if Claude and Codex interpret the same question differently (e.g., Q0 scaffold-default), Path B doesn't mediate. Path A only.
- **Findings 28/29/30/31** — populate.md fixes already in Path A (commit `4402435`). Path B doesn't reach these.

### 10.11 Pickup instructions for new chat

A fresh chat session taking this on should:

1. Read `codex-port/PLAN.md` §10 (this section) in full.
2. Read `codex-port/phase-R/parity-findings.md` R3 section (starts at "Run 3 — 2026-04-24") and R3 findings + Resolutions table.
3. Optionally read interview transcripts: `claude-r3-interview.md` and `codex-r3-interview.md` (in forge repo root; delete after reading — they're temporary).
4. Resolve §10.2 Python-runtime-dep decision before writing any code.
5. If YES → create new branch from `r3-complete-path-a` tag (or `feature/codex-support` HEAD at commit `4402435`) and follow §10.5 implementation plan.
6. If NO → document Path C framing per §10.7, close Finding 23 with known-limitation wording, continue Path A iteration.

No implementation work from §10 has happened yet. Everything below Path A commit `4402435` is design/analysis only.
