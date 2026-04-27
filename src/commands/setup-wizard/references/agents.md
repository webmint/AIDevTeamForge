# Phase 4 — Agent Curation

This reference covers the agent curation phase of the setup-wizard flow, loaded by the wizard orchestrator when Phase 4 executes. Install has placed all 16 agent templates under `.claude/agents/`. Your job: decide which agents this project needs, remove the rest, populate the kept ones, and update the agent list in `CLAUDE.md`.

## Files affected by this phase

- `.claude/agents/[name].md` — rejected agents deleted, kept agents populated (if present)
- `.devforge/baseline/agents/[name].md` — new baseline copies
- `CLAUDE.md` — `{{AGENT_LIST}}` placeholder replaced with kept-agents list (if present)

---

## 6.1: Select Agents

Based on Phase 1 detection and Phase 2 answers, classify each agent as **keep** or **remove**.

**Selection scope**: selection rules apply **project-wide**. For multi-package projects, a concern in ANY package is sufficient to keep its agent (e.g., if `apps/web` has a frontend layer, keep `frontend-engineer` even when other packages are backend-only). Use `PACKAGE_STACKS` (aggregated in Phase 3 — see `references/populate.md` §5.1; available by the time Phase 4 runs, built by merging Phase 1's `PACKAGES_DETECTED` with Phase 2's Q4–Q7 per-stack answers) to cross-check: inspect each package's language/framework/architecture to see which agents are relevant. **Edge case to flag**: if an agent seems relevant to only ONE dormant or legacy package (e.g., a migration tool in a package with no active development), mention this in Phase 2's selection review — the user may opt to remove it.

### Always keep (all project types):
| Agent | Why |
|-------|-----|
| `code-reviewer` | Every project needs code review |
| `qa-engineer` | Every project needs tests |
| `runtime-debugger` | Every project has runtime bugs |
| `tech-writer` | Every project needs documentation |
| `security-reviewer` | Every project needs security review |

### Keep if relevant (LLM decides based on detection):
| Agent | Keep when... |
|-------|-------------|
| `architect` | Project has significant structural complexity, or is a library/package, or both frontend + backend are present |
| `frontend-engineer` | Frontend/UI layer detected (web, desktop GUI, or any user-facing rendering) |
| `backend-engineer` | Backend/service layer detected (HTTP server, gRPC service, message consumer, any request-handling framework) |
| `mobile-engineer` | Mobile framework detected (native or cross-platform) |
| `db-engineer` | Database layer detected (any ORM, query builder, database driver, or migration tool in any language) |
| `devops-engineer` | CI/CD or containerization detected (any CI config files, Dockerfile, deployment configs) |
| `design-auditor` | Frontend project with styling/design system tooling |
| `api-designer` | Project exposes or consumes APIs (REST, GraphQL, gRPC, tRPC, or any RPC mechanism) |
| `performance-analyst` | Project has performance-sensitive paths (user-facing services, data processing, real-time systems) |
| `migration-engineer` | Existing codebase with evidence of ongoing migrations, deprecations, or major version upgrades |
| `ac-verifier` | `AC_VERIFICATION_MODE` is not `"off"` (Q11) |

**Do not hardcode framework or package names in your selection logic.** Use your knowledge of the detected ecosystem from Phase 1. If Phase 1 found a database driver you don't recognize by name, it's still a database layer — keep `db-engineer`. If it found a framework you've never seen, reason about what layer it serves.

## 6.2: Present Selection & Ask

Present the full list with your recommendation. **The reason given for each agent MUST cite concrete Phase 1 detection signals** — actual framework names, file paths, dev-dep entries you observed in this specific project. Do NOT copy reason values from the examples below; they're shape illustrations, not canonical text. Anti-hallucination rule applies — a reason without a concrete observed signal is a failure.

Prompt template (use `<placeholders>` to remind yourself to substitute project-specific signals):

> Based on your project, I recommend these agents:
>
> **Keep:**
> - `<agent-name>` — <concrete Phase 1 signal that triggered this keep-decision>
> - ... [list all with brief, project-specific reason]
>
> **Remove:**
> - `<agent-name>` — no <relevant-concern> detected in this project
> - ... [list all with brief, project-specific reason]
>
> Confirm, or override (move agents between keep/remove)?

**Example A — Python API project:**
- `backend-engineer` — FastAPI routes in `services/api/app/`
- `db-engineer` — SQLAlchemy models + Alembic migrations in `services/api/app/db/`
- `frontend-engineer` — removed (no UI layer detected)
- `code-reviewer` — always kept

**Example B — Rust CLI:**
- `backend-engineer` — removed (no service layer, CLI only)
- `performance-analyst` — `benches/` directory with Criterion benchmarks in `Cargo.toml`
- `frontend-engineer` — removed (CLI tool, no UI)
- `code-reviewer` — always kept

The two examples deliberately span different project shapes so you don't anchor on one ecosystem's vocabulary. Derive your reasons from THIS project's detected signals, not from these examples.

The user may:
- Confirm the selection
- Move agents from remove → keep ("actually, keep `api-designer`, we're adding a REST API soon")
- Move agents from keep → remove ("don't need `performance-analyst` for this project")

## 6.3: Mark Rejected Agents for Removal

Helper-owned. Don't delete agent files manually. Add each rejected agent's name to the `"removed"` list in the apply-agents JSON (see §6.4 below). `compose` deletes the files atomically as part of its Phase 4 work — see §6.7 for the full compose responsibilities.

## 6.4: Populate Kept Agents

Agent population is helper-driven. After §6.1 selection and §6.2 user confirmation, the LLM passes a single JSON file describing kept + removed agents to `wizard_render apply-agents`; `wizard_render compose` then derives all per-agent substitutions, applies them, regex-replaces the `model:` line per Q10 tier choices, and saves baselines.

### apply-agents JSON shape

**Canonical path:** `.devforge/.agents-apply.json` (leading dot — matches the ephemeral-file convention used by `.detection-report-state.json` and `.wizard-render-state.json`). Write your JSON to this exact path:

```
wizard_render apply-agents --substitutions-file .devforge/.agents-apply.json
```

The helper deletes this file after successfully consuming it during `compose` (mirroring how `compose` deletes its own state file on success). This keeps `.devforge/` clean across re-runs.

**Tier assignment per agent.** The agent → tier mapping lives in `references/questions.md` Q10's table:
- **Think tier:** `architect`, `api-designer`, `security-reviewer`
- **Do tier:** `backend-engineer`, `frontend-engineer`, `mobile-engineer`, `db-engineer`, `devops-engineer`, `migration-engineer`, `runtime-debugger`, `performance-analyst`, `design-auditor`
- **Verify tier:** `code-reviewer`, `ac-verifier`, `qa-engineer`

The `tech-writer` agent is hardcoded to `sonnet` per Q10's preamble, regardless of Q10 tier choices — when included in apply-agents JSON, the tier value passed has no effect on its model. Q10's table in questions.md remains the canonical source of truth; replicated here only because §6.4's apply-agents JSON construction needs the mapping inline. If you add or rename an agent, update Q10's table first, then this list.

When you write the JSON below, look up each kept agent's tier from this list (or Q10's source-of-truth table) and use that as the `"tier"` value.

JSON shape:

```json
{
  "kept": {
    "architect": { "tier": "think" },
    "code-reviewer": { "tier": "verify" },
    "backend-engineer": { "tier": "do" },
    "frontend-engineer": { "tier": "do" }
  },
  "removed": ["mobile-engineer", "design-auditor"]
}
```

Each kept entry is `{ "tier": "think|do|verify" }`. Tier maps to Q10's `CLAUDE_TIER_<TIER>` value (the helper looks it up from state — you don't pass the model name).

**Optional `substitutions` field** — for the rare case where an agent template introduces a `{{PLACEHOLDER}}` the helper doesn't know how to derive (e.g., a brand-new agent with novel placeholder names not yet in the registry), pass it explicitly:

```json
{
  "kept": {
    "novel-agent": {
      "tier": "do",
      "substitutions": { "NOVEL_PLACEHOLDER": "value" }
    }
  },
  "removed": []
}
```

LLM-supplied `substitutions` override helper-derived values for the same key. If the helper finds a `{{KEY}}` in a template that it can't derive AND the LLM didn't supply, `compose` errors with a clear message naming the agent and the missing key.

### What the helper derives

The helper auto-derives values for these placeholders by scanning each kept agent's template for `{{KEY}}` markers and looking up `KEY` in its registry (`scripts/lib/wizard_render.py` → `derive_placeholder`):

| Placeholder | Source | Architect (multi-stack) | Other agents / single-stack |
|---|---|---|---|
| `{{FRAMEWORK}}` | `state.frameworks[]` | joined-comma of all entries | primary (`[0]`) |
| `{{LANGUAGE}}` | `state.languages[]` | joined-comma of all entries | primary (`[0]`) |
| `{{ARCHITECTURE}}` | `state.architectures[]` | paired with `(<lang>/<fw>)` label | primary (`[0]`) |
| `{{ERROR_HANDLING}}` | `state.error_handlings[]` | paired with `(<lang>/<fw>)` label | primary (`[0]`) |
| `{{API_LAYER}}` | `state.api_layers[]` | paired with `(<lang>/<fw>)` label | primary (`[0]`) |
| `{{TESTING}}` | `state.testings[]` | paired with `(<lang>/<fw>)` label | primary (`[0]`) |
| `{{BUILD_TOOL}}` | `state.build_tools[]` | paired with `(<lang>/<fw>)` label | primary (`[0]`) |
| `{{BUILD_COMMAND}}` | `state.build_commands[]` | paired with `(<lang>/<fw>)` label | primary (`[0]`) |
| `{{TYPE_CHECK_COMMAND}}` | `state.type_check_commands[]` | paired with `(<lang>/<fw>)` label | primary (`[0]`) |
| `{{LINT_COMMAND}}` | `state.lint_commands[]` | paired with `(<lang>/<fw>)` label | primary (`[0]`) |
| `{{STYLING}}` | `detection_report.styling` | direct passthrough | direct passthrough |
| `{{STATE_MANAGEMENT}}` | `detection_report.state_management` | direct passthrough | direct passthrough |
| `{{PROJECT_PATHS}}` | `detection_report.packages[].path` | bullet list of all package paths (prefixed with `source_root/` in wrapper mode) | bullet list of all package paths (prefixed with `source_root/` in wrapper mode) |

**Architect-exception details:** the helper detects architect by name (`agent_name == "architect"`) AND multi-stack (`len(state.languages) > 1`). For single-stack projects, architect renders primary-only — same as other agents — there's no second stack to pair against.

**`null` / `"N/A"` / `"TBD"` semantics:**
- `null` — skipped in joined-comma and paired rendering; "N/A" emitted only if all entries are null.
- `"N/A"` — skipped in paired rendering (the concern doesn't apply for that stack); displayed verbatim as primary value.
- `"TBD"` — skipped in paired rendering for the 8 non-FRAMEWORK/LANGUAGE placeholders.
- Helper falls back to `"N/A"` when an entire array is empty or all-null.

### Adding a new placeholder to an agent template

If you add a `{{NEW_PLACEHOLDER}}` to an agent template, choose one:
1. **Helper-derives it** (preferred when the value comes from state or detection_report) — add a branch to `derive_placeholder` in `scripts/lib/wizard_render.py` so the registry knows the new key.
2. **LLM provides it** — pass via `substitutions` in apply-agents. Use only when the value isn't mechanically derivable from existing state.

Helper-discovered unknown placeholders fail compose with a clear error pointing at the offending agent and the missing key — no silent unsubstituted markers ship.

**Placement contract (for agent-template authors).** The 10 stack-aware placeholders may expand into multi-line content (paired bullets per stack for architect-multi). They MUST appear in each agent template as **stand-alone block-level elements** — their own paragraph, list item, or section — not inline within a running sentence. Inline placement silently breaks Markdown rendering for multi-stack projects.

**Type safety is intentionally not a wizard placeholder.** Project-specific type-safety rules live in `constitution.md` §3.1 (a `[project-specific]` section that `/constitute` populates). Agents consult constitution.md at task time — the agent templates contain a one-line pointer instead of an embedded `{{TYPE_SAFETY_RULES}}` placeholder. This avoids two problems: (a) baked-in rules drifting from the project's evolving conventions, (b) language-general training-knowledge rules contradicting projects with established non-default conventions (custom Result-monad libraries, disabled `strictNullChecks`, mid-migration `as`-assertion practice, etc.). Single source of truth = constitution.md.

**Agent-frontmatter model field** (emitted by `scripts/generate-agents.py` at install time with a **boot-safe default**, one per agent based on its `model_tier: think | do | verify`). This is NOT a placeholder — Claude must parse the agent file at launch, so install-time files carry real values. The wizard REPLACES the value at Phase 4 using **key-based regex replacement** (not placeholder substitution) driven by Q10 answers.

**Why this is key-replacement, not placeholder substitution**: Claude parses `.claude/agents/*.md` at launch (before the wizard can run). Shipping those files with `{{PLACEHOLDER}}` tokens in the YAML frontmatter would cause Claude to fail to load the agent — the wizard that would fix it can't execute because Claude doesn't have working agents. Defaults break the chicken-and-egg loop. The trade-off: wizard must use regex replacement instead of simple `{{X}}→Y` text substitution.

**Install-time defaults** (source of truth: `scripts/lib/install_defaults.py`):

- `.claude/agents/*.md` frontmatter:
  - `model: opus` (think tier), `model: sonnet` (do tier), `model: sonnet` (verify tier)

**Wizard replacement rules (Phase 4)**: for each kept agent file, determine the agent's tier (look at its source meta or map by name), then apply regex replacement:

`.claude/agents/<name>.md`:
- Locate the line `model: <value>` in the YAML frontmatter (anchored between the two `---` delimiters).
- Replace `<value>` with Q10's `CLAUDE_TIER_<TIER>` answer (`opus` / `sonnet` / `haiku`).

The replacement must be surgical — do NOT do broad `s/<old>/<new>/g` sweeps, because the model name literal may appear in agent prose too. Target only the `model:` line at the YAML frontmatter root.

**Preserve ALL template content.** The templates contain carefully designed workflows, steps, and rules. Substitution replaces placeholders — it never removes or condenses sections.

**Add project-specific patterns** discovered during Phase 1 detection (brownfield) or framework best-practice patterns (greenfield). Append these as new subsections — never replace existing template content.

For placeholders that don't apply to a specific agent (e.g., `{{STYLING}}` in a backend-only project that kept `frontend-engineer` by user override), use `"N/A"`.

## 6.5: Save Agent Baselines (helper-owned)

Helper handles via compose. For each kept agent, `compose` copies the populated agent file to `.devforge/baseline/agents/<name>.md` automatically (creates the directory if missing). These are the wizard output before manual user edits — `update.sh` uses them for three-way merge. No LLM action needed.

## 6.6: Update AGENT_LIST (helper-owned)

Helper handles via compose. After per-agent substitution, `compose` reads each kept agent's populated `description:` from its YAML frontmatter, formats one bullet per kept agent, and replaces the `(pending Phase 4 curation)` staging string in CLAUDE.md with the rendered list:

```markdown
- `architect` — Design decisions, architecture planning (Think tier)
- `backend-engineer` — Backend implementation (Do tier)
- `code-reviewer` — Code review (Verify tier)
- ...
```

No LLM action needed.

## 6.7: Compose protocol (canonical compose call site)

This is where `wizard_render compose` runs — once per wizard run, after Phase 3 setters AND Phase 4's `apply-agents` are both complete:

```
scripts/lib/wizard_render status      # verify ✓ ready to compose
scripts/lib/wizard_render compose     # write all files atomically
```

`compose` refuses if:
- Any required scalar (`project_name`, `project_description`, `project_type`, `workflow_enforcement`, `ai_attribution`) is unset
- Any required render (`project_structure`, `dev_commands`, `architecture_details`, `memory_seed`) is unset
- Any tier (`think` / `do` / `verify`) is unset
- `languages` is empty
- `len(languages) != len(frameworks)` (parallel-array invariant)
- `ac_modes` is empty
- `ac_modes` contains `"off"` alongside other modes
- `agents_kept` is empty (this section's `apply-agents` populates it)
- Any kept agent's template has a `{{KEY}}` the helper can't derive AND `apply-agents` didn't supply (clear error names the agent + key)

On success, `compose` does all of the following atomically:
- §5.1 — substitutes CLAUDE.md placeholders (helper derives the 6 stack-aware ones; uses LLM-composed multi-line renders for the rest)
- §5.3 — copies CLAUDE.md / constitution.md / docs/* to `.devforge/baseline/`
- §5.4 — conditionally injects chrome-devtools entry into `.mcp.json` and chrome-devtools permissions into `.claude/settings.json` (only if `ac_runtime_url` set)
- §5.5 — assembles `.devforge/project-config.json` from state + detection report
- §5.6 — inserts memory seed above the constitute sentinel in `.devforge/memory.md`
- §5.7 — strips authoring blockquotes + substitutes header placeholders in `constitution.md`
- §5.8 — substitutes placeholders in `docs/overview.md` and `docs/architecture.md`
- §6.3 — deletes rejected agent files from `.claude/agents/`
- §6.4 — substitutes placeholders + regex-replaces `model:` line for each kept agent
- §6.5 — saves agent baselines to `.devforge/baseline/agents/`
- §6.6 — replaces `{{AGENT_LIST}}` in CLAUDE.md with the kept-agents bullet list
- Writes `.devforge/setup-complete` marker
- Deletes the intermediate state file (`.devforge/.wizard-render-state.json`)

After compose succeeds, proceed to Phase 5 (summary in `main.md`).

---

Agent curation phase complete. Proceed to Phase 5 (summary).
