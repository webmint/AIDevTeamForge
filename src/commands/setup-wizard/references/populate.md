# Phase 3 — Population

This reference covers the file-substitution phase of the setup-wizard flow, loaded by the wizard orchestrator when Phase 3 executes. **All file writes are owned by the `scripts/lib/wizard_render` helper.** Your job is to compose values (per-stack rendering, multi-line prose, conditional sections) and pass them to the helper via field-by-field CLI calls. The helper validates, substitutes, and writes — atomically — when you call `compose`. You never read or write the populated files directly.

## Why a helper owns the writes

Placeholder substitution, sentinel preservation, atomic write, and "no `{{...}}` markers remain" validation are mechanical concerns. Doing them in the LLM burns tokens, allows drift between runs, and risks failure modes (forgot to escape a backtick, dropped a placeholder, double-substituted) that gate-language can't fully prevent. The helper produces byte-identical output every run for the same inputs. You compose values; it owns shape.

This mirrors the Phase 1 pattern: `scripts/lib/detect_report set <field> --value <X>` → `compose`. Same shape; same discipline.

## Files written by `wizard_render compose`

- `CLAUDE.md` — placeholder substitution (if present)
- `constitution.md` — header-placeholder substitution + strip 2 authoring blockquotes (§5.7). Body sentinels stay untouched.
- `docs/overview.md`, `docs/architecture.md` — placeholder substitution only (§5.8). Body sentinels stay untouched.
- `.claude/settings.json` — conditional permissions append only, no placeholder substitution (if present)
- `.mcp.json` — conditional chrome-devtools entry (if present)
- `.devforge/baseline/CLAUDE.md`, `.devforge/baseline/constitution.md`, `.devforge/baseline/docs/overview.md`, `.devforge/baseline/docs/architecture.md` — baseline copies
- `.devforge/baseline/agents/<name>.md` — per-kept-agent baseline copies (Phase 4)
- `.devforge/memory.md` — pre-populate with seed prose above the constitute sentinel
- `.devforge/project-config.json` — assembled from state + detection report
- `.devforge/setup-complete` — completion marker

Each file is presence-guarded: helper skips missing files silently without error.

---

## Drift-risk literals

These values depend on upstream defaults or package names that change without notice. The helper has its own copy in `scripts/lib/wizard_render.py` (constant `CHROME_DEVTOOLS_MCP_PACKAGE`); review on every Anthropic-MCP integration touch and update both copies in lock-step.

- **`CHROME_DEVTOOLS_MCP_PACKAGE`** = `"chrome-devtools-mcp"` — the Anthropic-authored Chrome DevTools MCP server npm package (unscoped). Verified via `npm view` on 2026-04-22.

---

## How to run this phase

Execute in two stages here in Phase 3, then defer the compose call to Phase 4:

1. **Compose values** — work through §5.1–§5.8 below. For each placeholder or per-stack array, compose the value following the rules in that section, then call `wizard_render set <field> --value <v>`, `wizard_render set-render <field> --stdin` (preferred for multi-line), or the appropriate `add-*` call. Order doesn't matter; the helper accumulates state across calls.
2. **Status check (no compose yet)** — run `scripts/lib/wizard_render status`. Confirm Phase 3 fields are set (✓). Status will report `agents_kept` as unset at this point — that's correct, because Phase 4 hasn't run yet. **Do NOT run `wizard_render compose` here** — see "End of Phase 3" at the bottom of this file for why; the canonical compose call is in `references/agents.md` §6.7.

**Phase 4 (agents) builds on Phase 3's state.** Phase 4's `references/agents.md` describes how to build the agent-substitutions JSON at the canonical path `.devforge/.agents-apply.json` and call `wizard_render apply-agents --substitutions-file .devforge/.agents-apply.json`. After that single `apply-agents` call, Phase 4 §6.7 runs `compose`, which atomically writes everything Phase 3 + Phase 4 set up.

---

## 5.1: CLAUDE.md placeholders

CLAUDE.md is the primary populated document. It contains 17 distinct `{{PLACEHOLDER}}` markers; this section names each one and the value (or composition rule) you pass to the helper.

### Direct-value scalars

For each, call `wizard_render set <field> --value <v>`:

| Placeholder | Field | Source |
|---|---|---|
| `{{PROJECT_NAME}}` | `project_name` | Q0 answer |
| `{{PROJECT_DESCRIPTION}}` | `project_description` | Q1 answer |
| `{{PROJECT_TYPE}}` | `project_type` | Q2 answer |

`{{SOURCE_ROOT}}` and `{{WRAPPER_MODE_SECTION}}` are derived by the helper from `detection_report.yaml`'s `source_root` + `workspace_mode` fields — you don't pass them.

### Helper-derived stack-aware placeholders

`{{FRAMEWORK}}`, `{{LANGUAGE}}`, `{{BUILD_TOOL}}`, `{{BUILD_COMMAND}}`, `{{TYPE_CHECK_COMMAND}}`, `{{LINT_COMMAND}}` are **derived by the helper** from the per-stack arrays you populate via `add-language` + `add-build-tool` / `add-build-command` / `add-type-check-command` / `add-lint-command`. You don't compose the rendered form — the helper applies the right rendering rule (joined-comma for FRAMEWORK/LANGUAGE; paired multi-stack with `(<language>)` label for the 4 commands; primary scalar for single-stack). Same registry handles per-agent rendering with the architect-exception (paired with `(<language>/<framework>)` label) — see `references/agents.md` §6.4.

**Per-stack array setters you must call** (once per stack, in declaration order to preserve parallel indexing):

```
wizard_render add-language --name "TypeScript" --framework "Next.js"
wizard_render add-language --name "Python" --framework "FastAPI"
wizard_render add-build-tool --value "Vite"
wizard_render add-build-tool --value "Poetry"
wizard_render add-build-command --value "npm run build"
wizard_render add-build-command --value "poetry run build"
wizard_render add-type-check-command --value "tsc --noEmit --pretty 2>&1 | head -20"
wizard_render add-type-check-command --value "mypy ."
wizard_render add-lint-command --value "eslint ."
wizard_render add-lint-command --value "ruff check ."
```

The helper enforces parallel-indexing at compose time (`len(languages) == len(frameworks)`); per-stack invariant checking for the other arrays is the LLM's responsibility.

**Runner prefix source for all command values** (applies to the 4 command arrays + per-package commands you compose for `{{PACKAGE_STACKS_SECTION}}` + `{{DEV_COMMANDS}}`):

When composing any command string, the runner prefix (`npm` / `yarn` / `pnpm` / `bun` / `poetry` / `hatch` / etc.) comes from `detection_report.package_manager.tool` in `.devforge/detection_report.yaml`. Phase 1 already selected the runner from observable lockfile signals at SOURCE_ROOT (see `detect.md` → "Command-runner selection") and encoded it in the Report. Re-deriving the runner here — from defaults, heuristics, or re-inspecting lockfiles — opens a drift surface against the Report's authoritative value.

- Multi-command ecosystems (`npm` / `yarn` / `pnpm` / `bun` / `poetry` / `hatch` / `pdm` / `uv` / `bundle exec` for Ruby): render as `<runner> run <script>` or `<runner> <script>` per the ecosystem convention (e.g., `yarn build:raw`, `poetry run build`, `bundle exec rake test`).
- Single-command ecosystems (`cargo`, `go`, `swift`): bare command, no runner prefix (e.g., `cargo build`, `go build ./...`, `swift build`).

Phase 1's per-stack command arrays already carry the correct runner prefix per stack — use them verbatim when calling the `add-*-command` setters.

**`null` / `"N/A"` / `"TBD"` semantics** (the helper distinguishes all three):

- `null` at index `i` means "unresolved for this stack" — helper skips the entry in joined-comma and paired rendering. `{{PACKAGE_STACKS_SECTION}}` (which you compose) falls back to `"—"` for `null`.
- `"N/A"` means "user-confirmed absence" (e.g., plain JavaScript has no type checker) — helper skips in paired rendering, displays verbatim in `{{PACKAGE_STACKS_SECTION}}`.
- `"TBD"` means "user deferred" — helper skips in paired rendering for the 8 stack-aware non-FRAMEWORK/LANGUAGE placeholders, displays verbatim in `{{PACKAGE_STACKS_SECTION}}`.

### Composed multi-line renders

For each of the multi-line renders below, compose the prose per the rules in its subsection, then pass via stdin:

```
wizard_render set-render <field> --stdin <<'EOF'
<your composed prose>
EOF
```

Field names: `project_structure`, `dev_commands`, `architecture_details`, `package_stacks_section`.

### `{{WRAPPER_MODE_SECTION}}` (helper-derived — you don't pass it)

The helper checks `detection_report.workspace_mode`. Standalone → empty string. Wrapper → it emits a fixed prose block with `{{SOURCE_ROOT}}` substituted. No LLM composition needed.

### `{{PROJECT_STRUCTURE}}` (`set-render project_structure --stdin`)

Generate a project-structure tree readable as an orientation aid. Branch on `len(packages)` (read from `detection_report.packages`).

#### Single-package or no-manifest projects (`len(packages) <= 1`)

Flat tree of SOURCE_ROOT. Show directories and key files (entry points, configs, manifests). Collapse large directories (e.g., `src/components/ (47 files)`). **Keep under 30 lines.**

Example:
```
src/
  app/
    layout.tsx
    page.tsx
  components/ (23 files)
  lib/
    api.ts
    utils.ts
  styles/
    globals.css
public/
package.json
tsconfig.json
```

#### Multi-package (monorepo) projects (`len(packages) >= 2`)

Use `packages[]` from the Detection Report as the structural anchor. For each package, render:
- Package path + manifest filename (or short label after `#`)
- 2–5 most-salient files within the package (entry point, key modules)
- Collapsed counts for large subdirectories

**Budget**: ~50 lines for 2–5 packages (≤10 lines per package); ~80 lines for 6+ packages (≤10 lines per major package, one line per shared library).

For projects with **more than ~10 packages**:
- Render **top-level directory groups** with package counts (e.g., `apps/ (3 packages)`, `services/ (4 packages)`, `packages/ (6 shared libraries)`)
- **Expand detail** for the most-substantive packages (largest file count, or user-designated primary from Q3)
- **Collapse shared libraries** to one line each: `packages/<name>/ — <language>, <framework or "library">`

#### Greenfield / empty projects

Show whatever exists (possibly just the manifest file and a `src/` stub). Same ≤30-line cap as the single-package case. For empty monorepos, list the workspace root + any placeholder directories the user may have scaffolded.

### `{{DEV_COMMANDS}}` (`set-render dev_commands --stdin`)

Extract actual dev / build / test / lint commands. Branch primarily on `len(packages)` (package count), not language count — a monorepo with 3 all-TypeScript packages is structurally "multi-package single-stack" and needs per-package rendering.

#### Single-package (`len(packages) <= 1`)

Flat markdown list from the single package's (or SOURCE_ROOT's) manifest scripts. Use `BUILD_COMMANDS[0]` / `TYPE_CHECK_COMMANDS[0]` / `LINT_COMMANDS[0]` from Phase 1 for non-dev commands; extract `scripts.dev` (or the language equivalent — e.g., `pyproject.toml [tool.poetry.scripts]` for Python, Procfile `dev:` target for Ruby, etc.) from the manifest for the dev-server command. Apply the runner prefix per "Runner prefix source" above.

Example:
```markdown
- `npm run dev` — Start development server
- `npm run build` — Production build
- `npm test` — Run test suite
- `npm run lint` — Run linter
```

#### Multi-package (`len(packages) >= 2`) — regardless of language count

Grouped per-package blocks, one sub-section per package. Label each sub-section with the package path + language + framework. Use that package's commands — from its own manifest scripts when declared, else fall back to its `PACKAGE_STACKS` record's per-package command fields. If the package has no dev server (e.g., a library package), omit the dev-server entry (keep build / test / lint).

If a **monorepo orchestrator** is detected in Phase 1 (`nx`, `turbo`, `pnpm` workspaces, `lerna`, Cargo workspaces, Go workspaces), list the orchestrator's all-packages command at the top as a shortcut before per-package sections.

**Greenfield note** (single-package and multi-package): if no scripts exist yet, generate defaults based on the chosen framework(s) + build tool(s) per stack / per package. Mark defaults inline: `<!-- default, update after scaffolding -->`.

### `{{ARCHITECTURE_DETAILS}}` (`set-render architecture_details --stdin`)

Generate a bullet list of architecture facts relevant to this project. Branch on `len(LANGUAGES)`. Skip `"N/A"` and `"TBD"` entries entirely. Draw from Phase 1 detection results and Q4–Q7 answers.

Sources:
- `ARCHITECTURES[i]` from Q4 (per-stack array)
- `ERROR_HANDLINGS[i]` from Q5 (per-stack array)
- `API_LAYERS[i]` from Q6 (per-stack array)
- `TESTINGS[i]` from Q7 (per-stack array)
- Detected State Management / Styling / database / CI / containerization from Phase 1

#### Single-stack (`len(LANGUAGES) == 1`)

Flat bullet list reading the `[0]` index of each array. Always include Pattern and Error Handling (if not `"N/A"`/`"TBD"`). Include others only if detected or confirmed.

Example for a Vue frontend:
```markdown
- **Pattern**: Feature-modular
- **Error Handling**: try/catch with toast notifications
- **API Layer**: REST (Axios)
- **Testing**: vitest
- **State Management**: Pinia
- **Styling**: Tailwind CSS
```

#### Multi-stack (`len(LANGUAGES) > 1`)

Per-stack grouped blocks. One top-level bullet per stack (language/framework label), with indented bullets for each concern pulled from the matching array index. Skip `"N/A"` / `"TBD"` indented bullets.

Cross-cutting facts (database, monorepo tool, CI/CD) go at the end as flat bullets below the stack blocks when they apply project-wide.

### `{{PACKAGE_STACKS_SECTION}}` (`set-render package_stacks_section --stdin`)

Conditional section rendering a per-package stack table for multi-package projects.

**Aggregation step (compute `PACKAGE_STACKS` before rendering):**

For each package `p` in `detection_report.packages`, compose a record by looking up the matching per-stack answer by language:

1. Find stack index: `i = LANGUAGES.indexOf(p.language_hint)` using **case-insensitive** comparison (e.g., `"TypeScript"` matches `"typescript"`).
2. Compose the record with these fields:
   - `path` — `p.path` (relative to SOURCE_ROOT)
   - `language` — `p.language_hint` (displayed verbatim as captured)
   - `framework` — `p.framework_hint` if non-null. If `p.framework_hint == null`, emit `"—"` — do NOT fall back to `FRAMEWORKS[i]`. Library packages never inherit the app's framework.
   - `architecture` — `ARCHITECTURES[i]` if `i >= 0`; else `"—"`
   - `error_handling` — `ERROR_HANDLINGS[i]` if `i >= 0`; else `"—"`
   - `api_layer` — `API_LAYERS[i]` if `i >= 0`; else `"—"`
   - `testing` — `TESTINGS[i]` if `i >= 0`; else `"—"`
   - `build_tool` — from manifest scan of `p.path/p.manifest` if a tool is clearly declared; else `BUILD_TOOLS[i]` if `i >= 0`; else `"—"`
   - `build_command` — from manifest scripts; else `BUILD_COMMANDS[i]` if `i >= 0`; else `"—"`
   - `type_check_command` — from manifest if the package declares a custom type-check (e.g., `scripts.typecheck`). If no dedicated script exists, check whether type-checking happens during the package's build step. If yes, emit `"via-build"` with the package's `build_command` as the recovery path — display as `via-build (run: <build_command>)` in the rendered table. Do NOT fall back to stack-level `TYPE_CHECK_COMMANDS[i]` (whole-project scope — wrong for per-package verification). Use `"—"` only when the package has genuinely no type-checking.
   - `lint_command` — from manifest scripts (e.g., `scripts.lint`) if custom; else `LINT_COMMANDS[i]` if `i >= 0`; else `"—"`

The last four fields' fallback chain is **manifest override → per-stack array → "—"**.

Three distinct sentinels at display time:
- `"TBD"` — user deferred in Phase 2
- `"N/A"` — not applicable for that stack
- `"—"` — no data (rare; usually indicates user-override in Q3 removed a language Phase 1 detected)

**Rendering rule (by package count):**

- `len(packages) == 0` → set the render to empty string. No packages means no table.
- `len(packages) == 1` → set the render to empty string. Single-package projects are covered by `{{ARCHITECTURE_DETAILS}}`.
- `len(packages) >= 2` → render the full section (header + intro + 2 tables) as below, subject to the monorepo-scale collapse rule.

**Monorepo-scale collapse rule** (large, uniform monorepos):

When `len(packages) >= 6` AND **≥80% of packages share identical non-path column values** (all of: `language`, `framework`, `architecture`, `error_handling`, `api_layer`, `testing`, `build_tool`, `build_command`, `type_check_command`, `lint_command`), collapse repetitive rows into a single defaults entry:

- Emit a single row labeled `_library packages (default)_` with the shared values for each column where ≥80% of packages agree.
- Emit one row per **deviator** (apps with `framework != null` are always deviators).
- Emit one row for the workspace root (`.`) regardless of shared-value count — semantically distinct.

If fewer than 80% of packages share identical values, render per-package rows as normal.

**Rendering format (multi-package):**

Two tables under a single `## Packages` header. Splitting into Conventions + Tools keeps each table narrow enough to read on typical screens.

```markdown
## Packages

This project is organized as a multi-package structure. Each package's technical stack and conventions are listed below. Cross-package decisions (API contracts, shared types, dependency direction) should respect these per-package boundaries.

**Architectural conventions by package:**

| Path | Language | Framework | Architecture | Error Handling | API Layer | Testing |
|---|---|---|---|---|---|---|
| `<path>` | <language> | <framework> | <architecture> | <error_handling> | <api_layer> | <testing> |

**Build / check / lint tools by package:**

| Path | Build Tool | Build Command | Type Check | Lint |
|---|---|---|---|---|
| `<path>` | <build_tool> | <build_command> | <type_check_command> | <lint_command> |
```

`Path` values wrap in backticks; command values in the Tools table wrap in backticks (they're shell commands). Other columns plain text. Preserve `"TBD"`, `"N/A"`, `"—"` sentinels verbatim.

### `{{COMMIT_ATTRIBUTION}}` (helper-derived from `ai_attribution`)

The helper composes the right block based on Q9's `ai_attribution` value (`"yes"` or `"no"`) — you only `set ai_attribution`. No render call needed.

### `{{AGENT_LIST}}` (helper-derived after Phase 4)

Phase 3 leaves this as `"(pending Phase 4 curation)"`. Phase 4 (`references/agents.md`) replaces it via `apply-agents` + `compose`. You don't pass it.

## 5.2: `.claude/settings.json`

**No placeholder substitution needed.** The template emits a complete static file with no `{{PLACEHOLDER}}` markers. The helper modifies it only in §5.4 below (conditional permissions append for chrome-devtools).

## 5.3: Baseline copies

Helper-owned. `compose` copies CLAUDE.md / constitution.md / docs/overview.md / docs/architecture.md to `.devforge/baseline/` for every file that exists at compose time. No LLM action needed.

`.claude/settings.json` is **projectOwned** — `update.sh` never overwrites it — so it doesn't need a baseline.

## 5.4: MCP servers + permissions (conditional)

Helper-owned. If you've called `wizard_render set ac_runtime_url --value <url>` (Q11's `AC_VERIFICATION_MODE` array included `"runtime-assisted"` AND the project's Q2 type routed through the **web frontend** or **full-stack web application** Runtime-assisted branch, which captures a frontend URL), `compose` injects the chrome-devtools entry into `.mcp.json` and appends the chrome-devtools permission allowlist into `.claude/settings.json`. Both files are presence-guarded.

If `ac_runtime_url` is not set, `compose` skips this step.

## 5.5: `.devforge/project-config.json`

Helper-owned. `compose` assembles the canonical answers record from your `set` / `add-*` calls + Phase 1's `detection_report.yaml`. No LLM rendering needed — every field has a setter.

### Setter coverage from Phase 2 answers

This table is the canonical Phase 3 setter inventory. Every Phase 2 answer needs to land via the matching `wizard_render` call here — `compose` will refuse if any required field is unset, with a clear error naming the missing field. Run through the table top-to-bottom; skip rows that don't apply to this project (e.g., the conditional Q11 follow-ups).

| Source | Setter | Required? |
|---|---|---|
| Q0 PROJECT_NAME | `wizard_render set project_name --value <s>` | yes |
| Q1 PROJECT_DESCRIPTION | `wizard_render set project_description --value <s>` | yes |
| Q2 PROJECT_TYPE | `wizard_render set project_type --value <s>` | yes |
| Q3 LANGUAGES + FRAMEWORKS | `wizard_render add-language --name <s> --framework <s\|null>` per stack | yes (≥1) |
| Q4 ARCHITECTURES | `wizard_render add-architecture --value <s>` per stack | per Q4 answer |
| Q5 ERROR_HANDLINGS | `wizard_render add-error-handling --value <s>` per stack | per Q5 answer |
| Q6 API_LAYERS | `wizard_render add-api-layer --value <s>` per stack | per Q6 answer |
| Q7 TESTINGS | `wizard_render add-testing --value <s>` per stack | per Q7 answer |
| Q8 WORKFLOW_ENFORCEMENT | `wizard_render set workflow_enforcement --value <strict\|moderate\|light>` | **yes** |
| Q9 AI_ATTRIBUTION | `wizard_render set ai_attribution --value <yes\|no>` | **yes** |
| Q10 CLAUDE_TIER_THINK / DO / VERIFY | `wizard_render set-tier think\|do\|verify --value <opus\|sonnet\|haiku>` (one call per tier) | **yes** (all three) |
| Q11 AC_VERIFICATION_MODE | `wizard_render add-ac-mode --value <code-only\|tests\|runtime-assisted\|off>` per selected mode | yes (≥1) |
| Q11 AC_RUNTIME_URL (web frontend / full-stack only) | `wizard_render set ac_runtime_url --value <url>` | conditional (triggers chrome-devtools MCP injection) |
| Q11 AC_RUNTIME_API_BASE (backend / full-stack only) | `wizard_render set ac_runtime_api_base --value <url>` | conditional |
| Q11 AC_RUNTIME_CLI_COMMAND (CLI only) | `wizard_render set ac_runtime_cli_command --value <s>` | conditional |
| Phase 1 BUILD_TOOLS / BUILD_COMMANDS / TYPE_CHECK_COMMANDS / LINT_COMMANDS (per-stack arrays) | `wizard_render add-build-tool` / `add-build-command` / `add-type-check-command` / `add-lint-command` per stack (also covered in §5.1) | yes |

The 4 multi-line renders (`project_structure`, `dev_commands`, `architecture_details`, `package_stacks_section`) are LLM-composed via `wizard_render set-render <field> --stdin` per §5.1. The `memory_seed` render is composed per §5.6.

### Concrete example calls

For a multi-stack TS+Python project answering Q4–Q7 with concrete values:

```
wizard_render add-language --name "TypeScript" --framework "Next.js"
wizard_render add-language --name "Python" --framework "FastAPI"
wizard_render add-architecture --value "feature-sliced"
wizard_render add-architecture --value "hexagonal"
wizard_render add-error-handling --value "neverthrow Result<T,E>"
wizard_render add-error-handling --value "exceptions + returns.Result"
wizard_render add-api-layer --value "tRPC client"
wizard_render add-api-layer --value "REST + OpenAPI"
wizard_render add-testing --value "vitest"
wizard_render add-testing --value "pytest"
```

AC verification (call once per selected mode; `"off"`-exclusivity is enforced at compose time):

```
wizard_render add-ac-mode --value "code-only"
wizard_render add-ac-mode --value "tests"
```

Tier model assignments:

```
wizard_render set-tier think --value opus
wizard_render set-tier do --value sonnet
wizard_render set-tier verify --value sonnet
```

**Per-stack array invariant** — `compose` rejects if `len(languages) != len(frameworks)`. Other per-stack arrays should also be parallel (one entry per language) but the helper only enforces languages/frameworks parity at the moment.

## 5.6: `.devforge/memory.md` seed

Compose the seed prose following the rules below, then call `wizard_render set-render memory_seed --stdin`. The helper inserts your prose immediately above the `<!-- Populated during constitute` sentinel in `.devforge/memory.md` (preserving the sentinel — `/constitute` reads it).

`.devforge/memory.md` is the project's shared learnings file — Claude reads it across sessions. Seeded content here is project-factual.

**Subsection content** (use Phase 1 detection + Q3-Q7 answers; emit only lines that have real data):

Insert under `## Architecture Decisions`, header `### Initial detection (from setup-wizard)`:

- `**Languages**`: comma-joined `LANGUAGES` (primary first)
- `**Frameworks**`: comma-joined `FRAMEWORKS` (parallel to languages; skip `null` entries)
- `**Architecture pattern**`: primary `ARCHITECTURES[0]` (skip line if `"TBD"`). For multi-stack, add parenthetical: `(primary; per-stack details in CLAUDE.md ## Packages)`
- `**Error handling**`: primary `ERROR_HANDLINGS[0]` (skip line if `"TBD"`). Same parenthetical for multi-stack.
- `**API layer**`: primary `API_LAYERS[0]` (skip if `"N/A"` or `"TBD"`). Same parenthetical for multi-stack.
- `**Testing**`: primary `TESTINGS[0]` (skip if `"N/A"` or `"TBD"`).
- `**Packages detected**`: `N packages` (where `N = len(packages)`). For `N >= 2`, append: `(see CLAUDE.md ## Packages for the full table)`. Omit this line entirely when `N == 0`.
- `**Key source paths**`: one bullet per package: `` `<path>/` — <language> / <framework-or-library> ``. For `N == 0` (empty project), render a single line: `none yet — greenfield project, populated via /specify`.

### Other observations (spillover bullet — capped at 5)

If your detection work surfaced project facts that don't fit the structured fields above (an unusual build pattern, a notable directory convention, a project-shape signal worth surfacing), append an **Other observations** sub-bullet at the end of the seed before passing it to `set-render memory_seed`:

```markdown
- **Other observations**:
  - <observation> (source: <file/signal>)
  - <observation> (source: <file/signal>)
```

**Discipline rules** (enforce in your composition — helper does not validate this section):

- **Cap at 5 entries.** If you have more, drop the least-load-bearing ones. Memory.md is a project-context file, not a dump.
- **Each entry must cite a concrete source signal** — file path, dep name, config key. Anti-hallucination rule applies.
- **Skip the bullet entirely if you have nothing to add.** Don't pad.
- **Don't duplicate** facts already captured in the structured bullets above (Languages, Frameworks, etc.).

This bullet exists so worthwhile detection signals aren't lost just because they don't have a structured field. It's the escape valve, not the main event.

**Example seed for a TS + Python monorepo** (multi-stack, 3 packages, with 2 spillover observations):

```markdown
### Initial detection (from setup-wizard)
- **Languages**: TypeScript, Python
- **Frameworks**: Next.js, FastAPI
- **Architecture pattern**: feature-sliced (primary; per-stack details in CLAUDE.md `## Packages`)
- **Error handling**: Result<T,E> via neverthrow (primary; per-stack details in `## Packages`)
- **API layer**: tRPC client (primary; per-stack details in `## Packages`)
- **Testing**: vitest (primary)
- **Packages detected**: 3 packages (see CLAUDE.md `## Packages` for the full table)
- **Key source paths**:
  - `apps/web/` — TypeScript / Next.js
  - `services/api/` — Python / FastAPI
  - `packages/shared/` — TypeScript / (library)
- **Other observations**:
  - Repo uses git-submodules for the shared protobuf schema in `protos/` (source: `.gitmodules`)
  - Custom Vite plugin in `tools/build-time-i18n.ts` injects translations at build (source: `apps/web/vite.config.ts`)
```

**Empty project** (greenfield, `len(packages) == 0`):

```markdown
### Initial detection (from setup-wizard)
- **Languages**: TypeScript
- **Frameworks**: Next.js (planned; greenfield, no manifest yet)
- **Architecture pattern**: (deferred — will decide during first spec)
- **Key source paths**: none yet — greenfield project, populated via /specify
```

Emit only lines that carry real data. If a concern was all-TBD/all-N/A/all-null across stacks, omit that bullet entirely.

## 5.7: `constitution.md` header

Helper-owned substitution + blockquote stripping. You don't render anything new — the helper composes the substitutions from your existing `set` / `add-*` calls + `detection_report.yaml`.

What `compose` does for `constitution.md`:

1. Strips the two informational blockquotes (`> For multi-stack projects, \`{{ERROR_HANDLING}}\` renders as paired bullets...` and the matching `\`{{TESTING}}\`` blockquote) — unconditionally, whether single-stack or multi-stack.
2. Substitutes header placeholders: `{{PROJECT_NAME}}`, `{{DATE}}` (today's ISO-8601 date), `{{PROJECT_TYPE}}`, `{{FRAMEWORK}}` (joined-comma rendering, same as CLAUDE.md), `{{LANGUAGE}}` (same), `{{WORKSPACE_MODE}}`, `{{SOURCE_ROOT}}`, `{{ERROR_HANDLING}}` (paired-or-scalar from `error_handlings[]`), `{{TESTING}}` (paired-or-scalar from `testings[]`).
3. Validates no `{{...}}` markers remain in the substituted output (body sentinels like `_Run /constitute to populate_` use `_..._` so they don't trigger).

Body sections marked `[project-specific]` with `_Run /constitute to populate_` sentinels stay untouched — `/constitute` fills them later.

If `constitution.md` doesn't exist at the project root, `compose` skips it silently.

## 5.8: `docs/overview.md` and `docs/architecture.md`

Helper-owned. `compose` substitutes:

- `docs/overview.md`: `{{PROJECT_NAME}}` and `{{PROJECT_DESCRIPTION}}`
- `docs/architecture.md`: `{{PROJECT_NAME}}` (appears twice — title heading + orientation blockquote)

Each file is presence-guarded. Body sections marked `_Populated by ..._` stay untouched.

The stub deliberately does NOT carry stack facts (`LANGUAGE`, `FRAMEWORK`, `WORKSPACE_MODE`, `SOURCE_ROOT`, `PROJECT_TYPE`) — those live in `CLAUDE.md`. `architecture.md` is the decisions / rules / flow document, not a duplicate of stack context.

---

## End of Phase 3 — defer compose to Phase 4

After all `set` / `set-render` / `set-tier` / `add-*` calls for §5.1–§5.6 are made, run **`status` only** to verify Phase 3 fields are set:

```
scripts/lib/wizard_render status      # confirm Phase 3 fields show ✓
```

Expect status to report unset `agents_kept` at this point — that's correct, because Phase 4 hasn't run yet. **Do NOT call `wizard_render compose` here.** Compose validates `agents_kept` is non-empty (Phase 4 is required to populate it via `apply-agents`), AND it deletes the state file on success — calling it now would either fail validation or wipe the Phase 3 state Phase 4 needs to extend. The single canonical compose invocation lives in `references/agents.md` §6.7, after Phase 4's `apply-agents` call.

---

Population phase complete. Proceed to Phase 4 (`references/agents.md`).
