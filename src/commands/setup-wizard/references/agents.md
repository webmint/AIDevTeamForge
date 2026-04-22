# Phase 4 — Agent Curation

This reference covers the agent curation phase of the setup-wizard flow, loaded by the wizard orchestrator when Phase 4 executes. Install has placed all 16 agent templates for both runtimes (`.claude/agents/` and `.codex/agents/`). Your job: decide which agents this project needs, remove the rest, populate the kept ones, and update the agent list in the core-LLM files.

## Files affected by this phase

- `.claude/agents/[name].md` — rejected agents deleted, kept agents populated (if present)
- `.codex/agents/[name].toml` — rejected agents deleted, kept agents populated (if present)
- `.devforge/baseline/agents/[name].md` — new baseline copies (Claude)
- `.devforge/baseline/agents/[name].toml` — new baseline copies (Codex)
- `CLAUDE.md` — `{{AGENT_LIST}}` placeholder replaced with kept-agents list (if present)
- `AGENTS.md` — `{{AGENT_LIST}}` placeholder replaced with kept-agents list (if present)

Single-runtime installs skip the missing runtime's files silently.

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

## 6.3: Remove Rejected Agents

Delete the rejected agent files from both runtime directories:
- `.claude/agents/[name].md`
- `.codex/agents/[name].toml`

## 6.4: Populate Kept Agents

For each kept agent, read the file and substitute all `{{PLACEHOLDER}}` markers per the rules below.

**Placement contract (for agent-template authors).** The 10 stack-aware placeholders — `{{FRAMEWORK}}`, `{{LANGUAGE}}`, `{{ARCHITECTURE}}`, `{{ERROR_HANDLING}}`, `{{API_LAYER}}`, `{{TESTING}}`, `{{BUILD_TOOL}}`, `{{BUILD_COMMAND}}`, `{{TYPE_CHECK_COMMAND}}`, `{{LINT_COMMAND}}` — and `{{TYPE_SAFETY_RULES}}` may expand into multi-line content (paired bullets per stack, language-grouped sub-headers). They MUST appear in each agent template as **stand-alone block-level elements** — their own paragraph, list item, or section — not inline within a running sentence. Inline placement silently breaks Markdown rendering for multi-stack projects (sub-headers and bullets collapse into a sentence). If an agent template needs a short inline mention of, e.g., the primary language, author a separate single-value placeholder for that purpose rather than reusing these.

### Per-agent rendering rules for stack-aware placeholders

Ten placeholders read from per-stack arrays: `{{FRAMEWORK}}`, `{{LANGUAGE}}`, `{{ARCHITECTURE}}`, `{{ERROR_HANDLING}}`, `{{API_LAYER}}`, `{{TESTING}}`, `{{BUILD_TOOL}}`, `{{BUILD_COMMAND}}`, `{{TYPE_CHECK_COMMAND}}`, `{{LINT_COMMAND}}`. Rendering depends on both the agent and the stack count.

**Architect-exception** (applies when substituting into `architect.md`):

- **Single-stack** (`len(LANGUAGES) == 1`): render primary-only (`[0]` index) — same as other agents. No special formatting.
- **Multi-stack** (`len(LANGUAGES) > 1`):
  - `{{FRAMEWORK}}` / `{{LANGUAGE}}` render as **joined-comma** — e.g., `"Next.js, FastAPI"`, `"TypeScript, Python"`. They ARE the stack identifier; joining them plainly is unambiguous. Matches CLAUDE.md rendering (Phase 3 in `references/populate.md`, section 5.1).
  - The remaining **eight** placeholders (`{{ARCHITECTURE}}`, `{{ERROR_HANDLING}}`, `{{API_LAYER}}`, `{{TESTING}}`, `{{BUILD_TOOL}}`, `{{BUILD_COMMAND}}`, `{{TYPE_CHECK_COMMAND}}`, `{{LINT_COMMAND}}`) render as **paired rendering** — each element paired with its stack identifier so architect can tell which value applies to which stack:
    - **2 stacks**: single-line, comma-separated pairs in the form `"<value> (<language>/<framework>)"`.
      - Example `{{ARCHITECTURE}}`: `"hexagonal (Python/FastAPI), feature-sliced (TypeScript/Next.js)"`
      - Example `{{BUILD_COMMAND}}` (commands in backticks, label plain): `` `npm run build` (TypeScript/Next.js), `poetry run build` (Python/FastAPI) ``
    - **3+ stacks**: multiline bullet list, one bullet per stack.
      - Example `{{TYPE_CHECK_COMMAND}}`:
        ```
        - `tsc --noEmit --pretty 2>&1 | head -20` (TypeScript/Next.js)
        - `mypy .` (Python/FastAPI)
        - `swift build` (Swift/SwiftUI)
        ```
    - Skip `"TBD"` entries entirely (user deferred; nothing actionable). For the 4 command/tool placeholders `"TBD"` doesn't apply — they're detection-driven, no user defer.
    - Keep `"N/A"` entries with their stack label (e.g., `` "`N/A` (TypeScript/shared-lib)" `` for a library package with no build command) so architect knows where a concern doesn't apply.
    - If `FRAMEWORKS[i]` is `null` for a given stack, show only language: `"hexagonal (Python)"` or `` "`poetry run build` (Python)" ``.

**Other agents** (everything except `architect`): render primary-only (`[0]` index from each array) for all ten stack-aware placeholders. As each agent is reviewed individually, it may be migrated to its own array-rendering rule (following the same paired/joined pattern as architect or a simpler variant appropriate to that agent's scope).

### Placeholders

- `{{FRAMEWORK}}` — from `FRAMEWORKS` array (Q3). Architect per rule above (joined-comma for multi-stack). Other agents: `FRAMEWORKS[0]`.
- `{{LANGUAGE}}` — from `LANGUAGES` array (Q3). Architect per rule above (joined-comma for multi-stack). Other agents: `LANGUAGES[0]`.
- `{{ARCHITECTURE}}` — from `ARCHITECTURES` array (Q4). Architect per rule above (paired for multi-stack). Other agents: `ARCHITECTURES[0]` (or `"TBD"` if deferred).
- `{{ERROR_HANDLING}}` — from `ERROR_HANDLINGS` array (Q5). Architect per rule above (paired for multi-stack). Other agents: `ERROR_HANDLINGS[0]` (or `"TBD"` if deferred).
- `{{API_LAYER}}` — from `API_LAYERS` array (Q6). Architect per rule above (paired for multi-stack). Other agents: `API_LAYERS[0]` (or `"N/A"` / `"TBD"`). Only appears in `api-designer`, `architect`, `backend-engineer`.
- `{{TESTING}}` — from `TESTINGS` array (Q7). Architect per rule above (paired for multi-stack). Other agents: `TESTINGS[0]`.
- `{{PROJECT_PATHS}}` — actual source paths from the project (scan SOURCE_ROOT)
- `{{BUILD_TOOL}}` — from `BUILD_TOOLS` array (Phase 1 detection). Architect per rule above (paired for multi-stack). Other agents: `BUILD_TOOLS[0]` (or `"N/A"` if the primary stack has no build tool).
- `{{BUILD_COMMAND}}` — from `BUILD_COMMANDS` array (Phase 1 detection). Architect per rule above (paired for multi-stack). Other agents: `BUILD_COMMANDS[0]` (or `"N/A"`).
- `{{TYPE_CHECK_COMMAND}}` — from `TYPE_CHECK_COMMANDS` array (Phase 1 detection). Architect per rule above (paired for multi-stack). Other agents: `TYPE_CHECK_COMMANDS[0]` (or `"N/A"` if the primary language has no type checker).
- `{{LINT_COMMAND}}` — from `LINT_COMMANDS` array (Phase 1 detection). Architect per rule above (paired for multi-stack). Other agents: `LINT_COMMANDS[0]` (or `"N/A"`).
- `{{STYLING}}` — detected styling approach (only in `frontend-engineer`, `design-auditor`)
- `{{STATE_MANAGEMENT}}` — detected state management (only in `frontend-engineer`, `mobile-engineer`)
- `{{TYPE_SAFETY_RULES}}` — generate per the agent's language scope:
  - **Non-architect agents** (primary-only scope): generate 3-5 bullet points based on `LANGUAGES[0]` (primary language). Cover escape-hatch types to avoid, null/optional safety, unsafe casts, language-specific concerns. If the primary language is unfamiliar, generate generic rules.
  - **Architect, single-stack** (`len(LANGUAGES) == 1`): same as above — 3-5 bullets for the single language.
  - **Architect, multi-stack** (`len(LANGUAGES) > 1`): generate a grouped block with 2-3 bullets per language, under a language-named sub-header. Type systems are structurally different across languages (TS structural + optional chaining, Python dynamic + optional typing, Rust ownership, etc.) — a flat shared list is either too generic to help or too long to be actionable. Example:

    ```
    **TypeScript type safety:**
    - Avoid `any`; use `unknown` and narrow explicitly
    - Use `?.` / `??` for optional chaining; never `!` assertion on values that could be null
    - Prefer discriminated unions over enums for runtime-checked variants

    **Python type safety:**
    - Annotate all public function signatures (`def foo(x: int) -> str:`)
    - Use `Optional[T]` not bare `None` returns; never `cast()` without justification
    - Run `mypy --strict` on domain modules
    ```

    For unfamiliar languages in the list, generate generic rules under that language's sub-header (do not omit it).
**Agent-frontmatter model placeholders** (emitted by `scripts/generate-agents.py` at install time, one per agent based on its `model_tier: think | do | verify`). The wizard substitutes them during Phase 4 using Q10 answers. Placeholder names are **runtime-qualified** — Claude stores model names, Codex stores reasoning enums separately from model-name overrides, so the keys cannot collapse into a single `{{MODEL_*}}` shape.

- `{{CLAUDE_TIER_THINK}}` / `{{CLAUDE_TIER_DO}}` / `{{CLAUDE_TIER_VERIFY}}` — Claude agent frontmatter `model:` field (in `.claude/agents/*.md`). Substitute Q10a's `CLAUDE_TIER_THINK` / `CLAUDE_TIER_DO` / `CLAUDE_TIER_VERIFY` (Claude model names, e.g., `"opus"`, `"sonnet"`, `"haiku"`). Each generated agent file contains exactly one of these based on its declared tier.
- `{{CODEX_TIER_THINK}}` / `{{CODEX_TIER_DO}}` / `{{CODEX_TIER_VERIFY}}` — Codex agent TOML `model =` field (in `.codex/agents/*.toml`). Substitute Q10b's **model override** keys: `CODEX_TIER_THINK_MODEL` / `CODEX_TIER_DO_MODEL` / `CODEX_TIER_VERIFY_MODEL` if set; else `CODEX_DEFAULT_MODEL` from populate.md's "Drift-risk literals" section. Note the intentional asymmetry with Claude: Q10b stores the model override under a `_MODEL` suffix so the symmetric `CODEX_TIER_*` key can carry the reasoning-effort enum instead.
- `{{CODEX_REASONING_THINK}}` / `{{CODEX_REASONING_DO}}` / `{{CODEX_REASONING_VERIFY}}` — Codex agent TOML `model_reasoning_effort =` field. Substitute Q10b's `CODEX_TIER_THINK` / `CODEX_TIER_DO` / `CODEX_TIER_VERIFY` (reasoning-effort enums, e.g., `"high"`, `"medium"`, `"low"`).

**Q10 → emitter-placeholder summary table:**

| Emitted placeholder (in agent file)   | Wizard substitutes from              | Value shape                   |
|---------------------------------------|--------------------------------------|-------------------------------|
| `{{CLAUDE_TIER_<TIER>}}`              | `CLAUDE_TIER_<TIER>` (Q10a)          | Claude model name             |
| `{{CODEX_TIER_<TIER>}}`                | `CODEX_TIER_<TIER>_MODEL` or `CODEX_DEFAULT_MODEL` | Codex model name  |
| `{{CODEX_REASONING_<TIER>}}`          | `CODEX_TIER_<TIER>` (Q10b)           | Codex reasoning-effort enum   |

**Must also add to `.devforge/project-config.json`:** the Codex reasoning keys above — `CODEX_REASONING_THINK`, `CODEX_REASONING_DO`, `CODEX_REASONING_VERIFY` — populated from Q10b's `CODEX_TIER_THINK` / `CODEX_TIER_DO` / `CODEX_TIER_VERIFY`. This lets downstream commands (and `update.sh`) read the resolved reasoning enum by the same key name the emitter used. Add matching entries to `src/devforge/project-config.json`.

**Preserve ALL template content.** The templates contain carefully designed workflows, steps, and rules. Substitution replaces placeholders — it never removes or condenses sections.

**Add project-specific patterns** discovered during Phase 1 detection (brownfield) or framework best-practice patterns (greenfield). Append these as new subsections — never replace existing template content.

For placeholders that don't apply to a specific agent (e.g., `{{STYLING}}` in a backend-only project that kept `frontend-engineer` by user override), use `"N/A"`.

## 6.5: Save Agent Baselines

For each kept agent, save a baseline copy:
- `.devforge/baseline/agents/[name].md` (Claude version)
- `.devforge/baseline/agents/[name].toml` (Codex version)

Create `.devforge/baseline/agents/` if it doesn't exist. These are the wizard output before manual user edits — `update.sh` uses them for three-way merge.

## 6.6: Update AGENT_LIST

Now that agents are finalized, go back to CLAUDE.md and AGENTS.md and replace the `{{AGENT_LIST}}` placeholder (set to `"(pending Phase 4 curation)"` in Phase 3, section 5.1) with the actual list of kept agents. Format:

```markdown
- `architect` — Design decisions, architecture planning (Think tier)
- `backend-engineer` — Backend implementation (Do tier)
- `code-reviewer` — Code review (Verify tier)
- ...
```

---

Agent curation phase complete. Proceed to Phase 5 (summary).
