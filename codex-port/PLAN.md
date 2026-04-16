# Multi-Runtime Support — Branch Plan (rev 6)

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
├── agents/                 ← 16 agent templates (markdown + YAML frontmatter)
├── files/                  ← CLAUDE.template, settings.template, memory.template, constitution.template, storage-rules
└── manifest.json           ← update.sh source-of-truth for what's template-owned vs project-owned
```

### install.sh: copy + delegate

`install.sh` is intentionally thin:
- Validates args (target dir, wrapper mode)
- Copies shared scaffolding (`specs/`, `bugs/`, `research/`, `scripts/`, `.mcp.json`)
- Delegates to `scripts/generate.sh` for all runtime-specific emission
- Writes the template version marker

Adding a new runtime does **not** touch install.sh.

### Generator: orchestrator + per-runtime emitters

```
scripts/
├── generate.sh                 ← orchestrator (bash, loops over RUNTIMES="claude codex")
├── emitters/
│   ├── claude.py               ← writes target/.claude/, CLAUDE.md
│   └── codex.py                ← writes target/.codex/, target/.agents/skills/, AGENTS.md
│   └── (future) cursor.py, gemini.py
└── lib/
    └── frontmatter.py          ← stdlib markdown+YAML parser shared across emitters
```

Python 3, stdlib only. No PyYAML, no requirements.txt.

### Two substitution stages (different lifecycles)

| Stage | Substituted by | Substitutes what | When |
|---|---|---|---|
| Runtime markers | Emitters (claude.py, codex.py) | `{{cli.sigil}}`, `{{cli.name}}`, `{{cli.attribution}}`, `{{path.X}}`, `{{ask}}` blocks | Install time |
| User-answer placeholders | Wizard | `{{FRAMEWORK}}`, `{{LANGUAGE}}`, `{{CLAUDE_TIER_THINK}}`, etc. | Wizard run time |

### Wizard's role (revised)

The wizard does NOT generate files. `install.sh` places all files via emitters. Wizard's job:
1. Analyze the project (LLM reads files, presents findings).
2. Ask the user targeted questions via confirm / override / defer.
3. **Substitute** user answers into `{{PLACEHOLDER}}` markers in already-placed files.
4. **Append** project-specific content to designated sections (CLAUDE.md/AGENTS.md architecture notes, agent project paths, constitution custom clauses).
5. Write answers to `target/.devforge/project-config.json` (placed by install.sh as an empty scaffold).

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

- `scripts/emitters/claude.py` — Claude emitter (pass-through to `.claude/`).
- `scripts/emitters/codex.py` — Codex emitter (skills + TOML agents + AGENTS.md).
- `scripts/generate.sh` — orchestrator, default `RUNTIMES="claude codex"`.
- `install.sh` delegates to generator. Tested: single install produces `.claude/`, `.codex/`, `.agents/skills/`, `AGENTS.md`.

### ✅ Phase A (partial) — setup-wizard.md STEPs 0–4 audit (24 issues)

Four commits on `feature/codex-support`:

```
34ba317 setup-wizard: add STEP 2 (Default Branch), renumber, delete cascade (#15)
f2c27b0 setup-wizard: renumber steps, project-state selection, issues #10–#14
09cac1b setup-wizard: resolve critical-bucket logic issues (#1–#9)
cae6535 Neutralize setup-wizard.md for multi-runtime support
```

**What was done:**

STEPs 0–4 of setup-wizard.md fully audited and rewritten. 24 issues found → 15 fixed, 4 dropped (YAGNI), 1 deferred (STEP 5–6), 4 closed (duplicates/already-resolved). Highlights:

- **STEP 1 (Project State)**: replaced LLM file-counting/classification with direct user ask (empty / greenfield / brownfield). Zero token cost.
- **STEP 2 (Default Branch)**: replaced 5-step git detection cascade with direct user ask.
- **STEP 3 (Auto-Detect)**: removed ~90 lines of hardcoded JS/TS framework enumeration; LLM now uses ecosystem knowledge to detect any stack.
- **STEP 4 (Questions Q1–Q9)**: confirm/override/defer pattern; REQUIRED/OPTIONAL/CONDITIONAL markers; anti-hallucination rule; per-runtime model-tier sub-blocks (Q8a Claude, Q8b Codex); AC verification modes universal + per-project-type branches (Q9).
- **Variation markers applied**: `{{cli.sigil}}` (14 instances), `{{cli.attribution}}`, `{{ask "..."}}...{{/ask}}` blocks (4 instances).
- **Step renumbering**: STEP 0 → 0, 0.5 → 1, new STEP 2, old 1 → 3, old 2 → 4, old 3 → 5, old 4 → 6. Single responsibility per step.
- **Tier key naming unified**: `{{RUNTIME}}_TIER_{{ROLE}}` with optional `_MODEL` suffix.
- **Project-config location**: `.devforge/project-config.json` (neutral, cross-runtime).

**What was NOT done (deferred):**

- **STEP 5 (Generate Configuration Files)** — ~240 lines of Claude-native prose. Needs fundamental rewrite: "generate from templates" → "substitute placeholders in already-placed files." Contains ~30 Claude-path references, stale placeholder names, JS-centric detection logic, PostToolUse hook setup. This is the next major content work.
- **STEP 6 (Cleanup & Summary)** — ~30 lines. Remove "delete templates?" question (moot); update summary to list all runtimes; fix setup-complete marker path.
- **IMPORTANT RULES section** — ~8 lines. Update Claude-specific references.

---

## 4. What's next

### Immediate (next session)
- **Rewrite STEP 5 + 6** of setup-wizard.md to match the substitute+append model. This is the largest remaining prose chunk.
- **Implement variation-marker substitution in emitters** — `claude.py` and `codex.py` need to process `{{cli.sigil}}`, `{{cli.name}}`, `{{cli.attribution}}`, `{{path.X}}`, `{{file.X}}`, and `{{ask}}...{{/ask}}` blocks before writing to target.

### After that
- Test: install into `testSpawn`, run wizard under Claude, verify output.
- Promote next command from `src/_pending/` (probably `/fix` — simplest workflow command).
- Eventually: run wizard under Codex, compare parity.
- Constitution.md emission, Codex baselines, Codex config.toml, AGENTS.md size enforcement.

### Medium-term
- Promote remaining 22 commands one-by-one.
- **IMPORTANT: Wire WORKFLOW_ENFORCEMENT into every gated command.** Currently collected by wizard (Q5: strict/moderate/light) and stored in `.devforge/project-config.json`, but NO command reads it — all commands are hardcoded to strict flow. Each command with gates (execute-task, specify, plan, breakdown, verify, fix, refactor) needs to read `WORKFLOW_ENFORCEMENT` and branch: strict = all gates, moderate = spec + breakdown gates only, light = spec gate only.
- Parity test harness.
- update.sh multi-runtime support.

### Longer-term
- Cursor / Gemini emitters.
- Collapse `templates/` intermediate in target (write directly to final paths).

---

## 5. Locked architectural decisions

1. **Authoring source under `src/`** — template-neutral location.
2. **install.sh is copy + delegate** — no runtime logic, no detection.
3. **install.sh does NOT detect** — wizard does via LLM with user as arbiter.
4. **Generator = orchestrator + per-runtime emitters** — open/closed.
5. **Python + stdlib only** for emitters.
6. **Emitters substitute runtime markers; wizard substitutes user-answer placeholders.** Two stages, two lifecycles.
7. **Phase A acceptance = B (structural match)** under identical wizard answers.
8. **Branch never merges to main.**
9. **Codex commands = skills** (prompts removed in 0.117.0).
10. **Verification in prose-hooks, not runtime hooks.**
11. **Source files carry variation markers** — `{{cli.sigil}}`, `{{cli.name}}`, `{{cli.attribution}}`, `{{path.X}}`, `{{file.X}}`, `{{ask}}...{{/ask}}`. Lowercase/dot namespace distinct from `{{UPPERCASE}}` user-answer placeholders.
12. **Uniform tier key naming**: `{{RUNTIME}}_TIER_{{ROLE}}` with optional `_MODEL` suffix for overrides.
13. **Incremental command migration** via `src/_pending/commands/`.
14. **`.devforge/project-config.json`** is the canonical cross-runtime answers record. Every CLI reads from it.
15. **Wizard asks, never infers** for project state (empty/greenfield/brownfield) and default branch. LLM detection reserved for tech-stack scanning only.

---

## 6. Open decisions

1. Constitution.md emission — shared step or per-emitter?
2. Codex baselines — add now or defer until update.sh multi-runtime?
3. Extensions file (`.devforge/extensions.yml`) — name/location, lower priority.
4. Test target for parity — `testSpawn` or scaffold fresh?
5. Codex CLI installed + authenticated?

---

## 7. Out of scope

- Cursor / Gemini support (later phase)
- Codex cloud mode (network sandbox breaks MCP)
- Gemma / local models
- Merging to main
