# Multi-Runtime Support — Branch Plan (rev 8)

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

### ✅ Phase A (partial) — setup-wizard.md STEPs 0–7

**STEPs 0–4** (detection + questions): fully audited and rewritten across multiple sessions. 24+ issues resolved.

**STEP 5** (Populate Placed Files): full placeholder-to-answer mapping with construction rules for dynamic values. Substeps:
- 5.1: Populate CLAUDE.md + AGENTS.md (same values, both files)
- 5.2: Populate runtime config files (`.claude/settings.json` + `.codex/config.toml`) — substitute `{{TYPE_CHECK_COMMAND}}`, `{{CODEX_MODEL_DEFAULT}}`, `{{CODEX_REASONING_DEFAULT}}`, `{{CODEX_APPROVAL_POLICY}}`
- 5.3: Save baselines to `.devforge/baseline/` (only for CLAUDE.md + AGENTS.md — runtime configs are projectOwned, no baseline)
- 5.4: Add chrome-devtools MCP + Claude permission entries conditionally
- 5.5: Populate `.devforge/project-config.json`

**STEP 6** (Curate & Populate Agents): LLM-driven agent selection. Substeps:
- 6.1: Select agents (5 always-keep + 11 conditional, no hardcoded framework lists)
- 6.2: Present keep/remove list, user confirms/overrides
- 6.3: Remove rejected agents from both runtime dirs
- 6.4: Populate kept agents (substitute placeholders, add project patterns)
- 6.5: Save agent baselines
- 6.6: Update `{{AGENT_LIST}}` in CLAUDE.md and AGENTS.md

**STEP 7** (Summary): stub, needs development.

**Questions Q0–Q9:**
- Q0: Project Name (new — detected from manifest or asked)
- Q1: Project Description (new — from README or asked)
- Q2: Project Type
- Q3: Languages & Frameworks
- Q4: Architecture Pattern
- Q5: Error Handling Convention
- Q6: Workflow Enforcement Level (stored but no command reads it yet — flagged)
- Q7: AI Attribution in Commits
- Q8: Agent Model Assignments (per-runtime tiers)
- Q9: Acceptance Criteria Verification

---

## 4. What's next

### Immediate (next session)
- **Implement variation-marker substitution in command emitters** — `claude.py` and `codex.py` need to process `{{cli.sigil}}`, `{{cli.attribution}}`, and `{{ask}}...{{/ask}}` blocks in commands before writing to target. Currently these markers pass through literally. This blocks promoting commands beyond setup-wizard.
- **TYPE_CHECK_COMMAND derivation rule in wizard STEP 3** — the placeholder is referenced in 5.1 and 5.2, but the wizard hasn't formalized the detection/derivation rule (TS→`tsc --noEmit`, Py→`mypy` or `py_compile`, Go→`go vet ./...`, Rust→`cargo check`). Add as a detection output of STEP 3.
- Test end-to-end: install into `testSpawn`, run wizard under Claude, verify full output including the new 5.2 substitutions.

### After that
- Finish STEP 7 (Summary).
- Promote next command from `src/_pending/` (probably `/fix` — simplest workflow command).
- Run wizard under Codex, compare parity.

### Medium-term
- Promote remaining 22 commands one-by-one.
- **IMPORTANT: Wire WORKFLOW_ENFORCEMENT into every gated command.** Currently collected by wizard (Q6: strict/moderate/light) and stored in `.devforge/project-config.json`, but NO command reads it — all commands are hardcoded to strict flow. Each command with gates (execute-task, specify, plan, breakdown, verify, fix, refactor) needs to read `WORKFLOW_ENFORCEMENT` and branch: strict = all gates, moderate = spec + breakdown gates only, light = spec gate only.
- Constitution.md emission (shared content, cross-runtime).
- Parity test harness.
- update.sh multi-runtime support (currently `expand_templateOwned_pairs` handles pair-based mappings, but `templateDerived` three-way merge for `generated:agents` and `generated:coreLLM` sources isn't implemented yet).

### Longer-term
- Cursor / Gemini emitters.
- Desktop native agent (if demand emerges).

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
10. **Verification in prose-hooks, not runtime hooks.**
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

---

## 6. Open decisions

1. Constitution.md emission — shared step or per-emitter?
2. Extensions file (`.devforge/extensions.yml`) — name/location, lower priority.
3. Test target for parity — `testSpawn` or scaffold fresh?
4. Codex CLI installed + authenticated for parity testing?
5. ~~Agent templates: do they need a coreLLM-style single-source generator~~ — **resolved**: yes, universal fenced-yaml source with per-runtime emit-from-scratch. See decision #21.
6. `[notify]` hook in `.codex/config.toml` — deferred; no clear use case yet. Session-end notification is the closest analog to Claude's Stop hook.

---

## 7. Out of scope

- Cursor / Gemini support (later phase)
- Codex cloud mode (network sandbox breaks MCP)
- Gemma / local models
- Merging to main
- Desktop native agent (revisit if demand emerges)
- ML/data science agent (revisit if demand emerges)
