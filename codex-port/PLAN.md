# Multi-Runtime Support — Branch Plan (rev 9)

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
- Test end-to-end: install into `testSpawn` (both with and without `--runtime` flag), run wizard under Claude, verify full output including the 5.2 substitutions and single-runtime guards.

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
