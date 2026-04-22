# Phase 3 — Population

This reference covers the file-substitution phase of the setup-wizard flow, loaded by the wizard orchestrator when Phase 3 executes. All files are already in place; this phase only populates placeholders and, conditionally, appends MCP / permission entries. **Do not create new files.**

## Files modified by this phase

- `CLAUDE.md` — placeholder substitution (if present)
- `AGENTS.md` — placeholder substitution (if present)
- `constitution.md` — header-placeholder substitution only (§5.7). Body sections stay untouched — `/constitute` (separate command) fills them later.
- `docs/overview.md` — placeholder substitution only (§5.8). Body sections stay untouched — `/constitute`, `/onboard`, and the tech-writer agent fill them later.
- `docs/architecture.md` — placeholder substitution only (§5.8). Body sections stay untouched — same deferred-fill pattern.
- `.claude/settings.json` — conditional permissions only, no placeholder substitution (if present)
- `.codex/config.toml` — placeholder substitution + conditional MCP entry (if present)
- `.mcp.json` — conditional MCP entry (if present, Claude only)
- `.devforge/baseline/CLAUDE.md` — new baseline copy
- `.devforge/baseline/AGENTS.md` — new baseline copy
- `.devforge/baseline/constitution.md` — new baseline copy
- `.devforge/baseline/docs/overview.md` — new baseline copy
- `.devforge/baseline/docs/architecture.md` — new baseline copy
- `.devforge/memory.md` — pre-populate with Phase 1 detection findings (single shared file; both runtimes read it)
- `.devforge/project-config.json` — populate null values with collected answers

Each file is presence-guarded: if an install was single-runtime (`--runtime claude` or `--runtime codex`), only that runtime's files exist. Skip missing files silently without error.

---

## Drift-risk literals

These values depend on upstream defaults or package names that change without notice. Treat them as the single source of truth for this file — §5.2 and §5.4 below reference them by name instead of repeating the literal. Review on every Codex or Anthropic-MCP integration touch; update the literal and the `last verified` date here in one place.

- **`CODEX_DEFAULT_MODEL`** = `"gpt-5.4"` — Codex CLI's documented default model at the time of authoring. Used when Q10b leaves `CODEX_TIER_DO_MODEL` as `null`. Last verified: 2026-04-22.
- **`CHROME_DEVTOOLS_MCP_PACKAGE`** = `"chrome-devtools-mcp"` — the Anthropic-authored Chrome DevTools MCP server npm package (unscoped). Verified via `npm view` on 2026-04-22.

If either literal goes stale, both the emitted `.codex/config.toml` / `.mcp.json` entries become wrong in the same run. When updating, also update the `last verified` date.

---

## How to run this phase

All files are already in place. Your job is substitution only — **do not create new files**. Read each file, replace every `{{PLACEHOLDER}}` marker with the corresponding value, and write it back.

**Single-runtime installs:** if install was run with `--runtime claude` or `--runtime codex`, only that runtime's files exist. For each file mentioned below, check presence first; skip the file if it doesn't exist. Do not error.

## 5.1: Populate CLAUDE.md and AGENTS.md

Read `CLAUDE.md` and `AGENTS.md` at project root — **whichever exist**. Each contains the same `{{PLACEHOLDER}}` markers; substitute ALL of them with the same values:

- `{{PROJECT_DESCRIPTION}}` — Q1 answer: the 1-3 sentence project description
- `{{PROJECT_NAME}}` — Q0 answer: project name
- `{{PROJECT_TYPE}}` — Q2 answer (e.g., "Frontend application", "Backend API", "Full-stack web application")
- `{{FRAMEWORK}}` — render from the full `FRAMEWORKS` array captured in Q3, joined with `, ` (e.g., `"Next.js"` for single-stack, `"Next.js, FastAPI"` for multi-stack, `"Next.js, FastAPI, Swift"` for three stacks). Preserve the full stack list (not just the primary) so both `CLAUDE.md` and `AGENTS.md` give their respective runtimes — Claude and Codex — complete project context. Each file is the project-context source for its own runtime; they receive the same substituted value but are otherwise independent. Skip `null` entries in the array.
- `{{LANGUAGE}}` — render from the full `LANGUAGES` array captured in Q3, joined with `, ` (e.g., `"TypeScript"` for single-stack, `"TypeScript, Python"` for multi-stack).
- `{{BUILD_TOOL}}` — render from `BUILD_TOOLS` array (see per-stack rendering rule below). Single-stack: `BUILD_TOOLS[0]`. Multi-stack: paired rendering inline.
- `{{BUILD_COMMAND}}` — render from `BUILD_COMMANDS` array (see per-stack rendering rule below). Single-stack: `BUILD_COMMANDS[0]`. Multi-stack: paired rendering inline.
- `{{TYPE_CHECK_COMMAND}}` — render from `TYPE_CHECK_COMMANDS` array (see per-stack rendering rule below). Single-stack: `TYPE_CHECK_COMMANDS[0]`. Multi-stack: paired rendering inline.
- `{{LINT_COMMAND}}` — render from `LINT_COMMANDS` array (see per-stack rendering rule below). Single-stack: `LINT_COMMANDS[0]`. Multi-stack: paired rendering inline.

**Per-stack rendering rule for the 4 placeholders above** (applies when `len(LANGUAGES) > 1`):

Each element pairs with its language identifier so readers can tell which command applies where:

- Format per pair: `` `<command>` (<language>) `` for command-type placeholders; `<tool> (<language>)` for `BUILD_TOOL` (no backticks on a tool name).
- **Skip `"N/A"` entries entirely** — don't show languages that have no command for this concern (e.g., plain JS in the type-check array).
- **Skip `null` entries** — don't render placeholders for unresolved languages (shouldn't normally happen).
- If **all** entries are `"N/A"` or `null`, render the placeholder as `"N/A"` (single value) — graceful degradation.
- Wrapper-mode prefix (`cd SOURCE_ROOT && `) is already applied per-element in Phase 1 — do NOT re-prefix.

**Consolidated note on `null` array entries** (applies across all per-stack arrays in this section and throughout populate.md):

`null` at some index `i` in a per-stack array means "unresolved for this stack" — most commonly `FRAMEWORKS[i] == null` for a language with no framework (e.g., a plain Python CLI), or `BUILD_TOOLS[i] == null` / `BUILD_COMMANDS[i] == null` etc. when detection couldn't resolve a tool/command for that language. The handling pattern:

- **Joined-comma placeholders** (`{{FRAMEWORK}}`, `{{LANGUAGE}}` in CLAUDE.md / AGENTS.md Project Overview): skip `null` entries entirely.
- **Paired-rendering placeholders** (the 4 command/tool placeholders here in 5.1; 8 stack-aware placeholders for architect in agents.md 6.4): skip `null` entries entirely.
- **`{{PACKAGE_STACKS_SECTION}}` aggregation**: `null` in a per-stack array at the matching index → fall back to `"—"` in the per-package record (see 5.1 `{{PACKAGE_STACKS_SECTION}}` aggregation rules).
- **Architect paired rendering with `FRAMEWORKS[i] == null`** (agents.md 6.4): show language only, e.g., `` "hexagonal (Python)" `` — this is the documented behavior when framework is missing but language is present.

`null` is NOT the same as `"N/A"` (user-confirmed absence) or `"TBD"` (user deferred) — those are strings with verbatim display; `null` means "no data" and triggers skip-or-fallback logic.

Example for a TS+Python monorepo (2 stacks, both have all commands):

```
- **Build Tool**: Vite (TypeScript), Poetry (Python)
- **Build Command**: `npm run build` (TypeScript), `poetry run build` (Python)
- **Type Check Command**: `tsc --noEmit --pretty 2>&1 | head -20` (TypeScript), `mypy .` (Python)
- **Lint Command**: `eslint .` (TypeScript), `ruff check .` (Python)
```

Example for a plain JavaScript + Ruby project (no type checker in either language):

```
- **Type Check Command**: N/A
```

Single-stack example (unchanged format from before per-stack arrays):

```
- **Build Command**: `npm run build`
- **Type Check Command**: `tsc --noEmit --pretty 2>&1 | head -20`
```
- `{{SOURCE_ROOT}}` — `SOURCE_ROOT` set in Phase 1 (`.` for standalone, inner folder name for wrapper, e.g. `client-project`)
- `{{WRAPPER_MODE_SECTION}}` — see below
- `{{PROJECT_STRUCTURE}}` — see below
- `{{DEV_COMMANDS}}` — see below
- `{{ARCHITECTURE_DETAILS}}` — see below
- `{{PACKAGE_STACKS_SECTION}}` — see below (conditional: rendered only for multi-package projects)
- `{{AGENT_LIST}}` — staging placeholder: `"(pending Phase 4 curation)"`. Phase 4 (see `references/agents.md` section 6.6) replaces this with the actual curated agent list once agents are finalized.
- `{{COMMIT_ATTRIBUTION}}` — see below

### `{{WRAPPER_MODE_SECTION}}`

**If standalone project**: replace with empty string.

**If wrapper mode**: replace with:
```markdown
## Wrapper Mode

This workspace wraps a client-owned project. All workflow artifacts live here; source code lives in `{{SOURCE_ROOT}}/`.

### Wrapper Rules
1. **Never create workflow artifacts inside `{{SOURCE_ROOT}}/`** — no `.devforge/`, `specs/`, `docs/`, or `constitution.md` files
2. **All source scanning** targets `{{SOURCE_ROOT}}/` as the base path
3. **Git auto-commits** apply to both repos — wrapper gets workflow commits, source repo gets WIP commits per task that are squashed into one clean commit when finalize runs
4. **File paths** in specs and tasks use workspace-relative paths (e.g., `{{SOURCE_ROOT}}/src/components/Button.tsx`)
```

### `{{PROJECT_STRUCTURE}}`

Generate a project-structure tree readable as an orientation aid. Branch on `len(PACKAGES_DETECTED)`.

#### Single-package or no-manifest projects (`len(PACKAGES_DETECTED) <= 1`)

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

#### Multi-package (monorepo) projects (`len(PACKAGES_DETECTED) >= 2`)

Use `PACKAGES_DETECTED` as the structural anchor. For each package, render:
- Package path + manifest filename (or short label after `#`)
- 2–5 most-salient files within the package (entry point, key modules)
- Collapsed counts for large subdirectories

**Budget**: ~50 lines for 2–5 packages (≤10 lines per package); ~80 lines for 6+ packages (≤10 lines per major package, one line per shared library).

For projects with **more than ~10 packages**:
- Render **top-level directory groups** with package counts (e.g., `apps/ (3 packages)`, `services/ (4 packages)`, `packages/ (6 shared libraries)`)
- **Expand detail** for the most-substantive packages (largest file count, or user-designated primary from Q3)
- **Collapse shared libraries** to one line each: `packages/<name>/ — <language>, <framework or "library">`

Example for a 3-package TS + Python monorepo:
```
apps/
  web/                                   # TypeScript / Next.js
    app/
      layout.tsx
      page.tsx
    components/ (23 files)
    package.json
    tsconfig.json
services/
  api/                                   # Python / FastAPI
    app/
      main.py
      routers/ (6 files)
    pyproject.toml
packages/
  shared/                                # TypeScript (library)
    src/index.ts
    package.json
pnpm-workspace.yaml
package.json                             # workspace root
```

#### Greenfield / empty projects

Show whatever exists (possibly just the manifest file and a `src/` stub). Same ≤30-line cap as the single-package case. For empty monorepos (workspace-root manifest present but no member packages yet), still list the workspace root + any placeholder directories the user may have scaffolded.

### `{{DEV_COMMANDS}}`

Extract actual dev / build / test / lint commands. Rendering branches primarily on `len(PACKAGES_DETECTED)` (package count), not `len(LANGUAGES)` (language count) — because a monorepo with 3 all-TypeScript packages is structurally "multi-package single-stack" and needs per-package rendering, even though the language count is 1.

#### Single-package (`len(PACKAGES_DETECTED) <= 1`)

Flat markdown list from the single package's (or SOURCE_ROOT's) manifest scripts. Use `BUILD_COMMANDS[0]` / `TYPE_CHECK_COMMANDS[0]` / `LINT_COMMANDS[0]` from Phase 1 for non-dev commands; extract `scripts.dev` (or the language equivalent — e.g., `pyproject.toml [tool.poetry.scripts]` for Python, Procfile `dev:` target for Ruby, etc.) from the manifest for the dev-server command. Use the correct command runner (`npm` / `yarn` / `pnpm` / `cargo` / `go` / `make` / `poetry`, etc.) based on lockfiles and manifest.

Example:
```markdown
- `npm run dev` — Start development server
- `npm run build` — Production build
- `npm test` — Run test suite
- `npm run lint` — Run linter
```

#### Multi-package (`len(PACKAGES_DETECTED) >= 2`) — regardless of language count

Grouped per-package blocks, one sub-section per package. Label each sub-section with the package path + language + framework. Use that package's commands — from its own manifest scripts when declared, else fall back to its `PACKAGE_STACKS` record's per-package command fields. If the package has no dev server (e.g., a library package), omit the dev-server entry (keep build / test / lint).

If a **monorepo orchestrator** is detected in Phase 1 (`nx`, `turbo`, `pnpm` workspaces, `lerna`, Cargo workspaces, Go workspaces), list the orchestrator's all-packages command at the top as a shortcut before per-package sections.

Example for an all-TypeScript monorepo (3 packages, pnpm workspaces):
```markdown
**All packages** (via pnpm workspaces):
- `pnpm -r build` — Build all packages
- `pnpm -r test` — Run all test suites

**`apps/web`** — TypeScript / Next.js:
- `pnpm --filter web dev` — Start web dev server
- `pnpm --filter web build` — Build web app
- `pnpm --filter web test` — Run web tests

**`apps/admin`** — TypeScript / Remix:
- `pnpm --filter admin dev` — Start admin dev server
- `pnpm --filter admin build` — Build admin app
- `pnpm --filter admin test` — Run admin tests

**`packages/shared`** — TypeScript (library, no dev server):
- `pnpm --filter shared build` — Build shared lib
- `pnpm --filter shared test` — Run shared tests
```

Example for a mixed TS + Python monorepo (2 packages, pnpm workspaces + Poetry):
```markdown
**All packages** (via pnpm workspaces — TS side only; Python uses Poetry):
- `pnpm -r build` — Build all TS packages

**`apps/web`** — TypeScript / Next.js:
- `pnpm --filter web dev` — Start frontend dev server
- `pnpm --filter web build` — Build web app
- `pnpm --filter web test` — Run web tests
- `eslint .` — Lint TS files

**`services/api`** — Python / FastAPI:
- `poetry run uvicorn app:main --reload` — Start backend dev server
- `poetry run build` — Build Python package
- `pytest` — Run Python tests
- `ruff check .` — Lint Python files
```

**Greenfield note** (applies to both single-package and multi-package): if no scripts exist yet, generate defaults based on the chosen framework(s) + build tool(s) per stack / per package. The Phase 1 arrays (`BUILD_COMMANDS`, `TYPE_CHECK_COMMANDS`, `LINT_COMMANDS`, `TESTINGS`) already fall back to language-standard tools in empty / greenfield projects — use those values. For multi-package greenfield, use each package's `PACKAGE_STACKS` record fields. Mark defaults inline: `<!-- default, update after scaffolding -->`.

### `{{ARCHITECTURE_DETAILS}}`

Generate a bullet list of architecture facts relevant to this project. Branch on `len(LANGUAGES)`. Do not include fields that don't apply — skip `"N/A"` and `"TBD"` entries entirely. Draw from Phase 1 detection results and Q4 (Architecture) / Q5 (Error Handling) / Q6 (API Layer) / Q7 (Testing) answers. Add any other relevant architectural facts you discovered (e.g., database, monorepo tool, CI/CD).

Sources:
- `ARCHITECTURES[i]` from Q4 (per-stack array)
- `ERROR_HANDLINGS[i]` from Q5 (per-stack array)
- `API_LAYERS[i]` from Q6 (per-stack array)
- `TESTINGS[i]` from Q7 (per-stack array)
- Detected State Management / Styling / database / CI / containerization from Phase 1 (per-stack where applicable)

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

Example for a Rust CLI:
```markdown
- **Pattern**: Layered (CLI → service → domain)
- **Error Handling**: thiserror + anyhow, ? operator throughout
- **Testing**: cargo test
```

#### Multi-stack (`len(LANGUAGES) > 1`)

Per-stack grouped blocks. One top-level bullet per stack (language/framework label), with indented bullets for Pattern / Error Handling / API Layer / Testing / State Management / Styling pulled from the matching array index. Skip any `"N/A"` / `"TBD"` indented bullet (but keep the stack's top-level bullet as long as it has at least one concrete concern).

Example for a TS frontend + Python backend monorepo:
```markdown
- **TypeScript / Next.js**
  - Pattern: feature-sliced
  - Error Handling: neverthrow Result<T,E>
  - API Layer: tRPC client
  - Testing: vitest
  - State Management: Zustand
  - Styling: Tailwind CSS

- **Python / FastAPI**
  - Pattern: hexagonal
  - Error Handling: exceptions + returns.Result
  - API Layer: REST + OpenAPI
  - Testing: pytest
```

Cross-cutting facts (database, monorepo tool, CI/CD) go at the end as flat bullets below the stack blocks when they apply project-wide:
```markdown
- **Database**: PostgreSQL via Prisma (TS) / SQLAlchemy (Python)
- **Monorepo tool**: pnpm workspaces + Poetry
- **CI**: GitHub Actions
```

### `{{PACKAGE_STACKS_SECTION}}`

Conditional section rendering a per-package stack table for multi-package projects. Matches the `{{WRAPPER_MODE_SECTION}}` pattern: the section header is part of the substituted content, not fixed in the source template.

**Aggregation step (compute `PACKAGE_STACKS` before substitution):**

For each package `p` in `PACKAGES_DETECTED` (from Phase 1), compose a record by looking up the matching per-stack answer by language:

1. Find stack index: `i = LANGUAGES.indexOf(p.language_hint)` using **case-insensitive** comparison (e.g., `"TypeScript"` matches `"typescript"`).
2. Compose the record with these fields:
   - `path` — `p.path` (relative to SOURCE_ROOT)
   - `language` — `p.language_hint` (displayed verbatim as captured)
   - `framework` — `p.framework_hint` if set; else `FRAMEWORKS[i]` if `i >= 0`; else `"—"`
   - `architecture` — `ARCHITECTURES[i]` if `i >= 0`; else `"—"`
   - `error_handling` — `ERROR_HANDLINGS[i]` if `i >= 0`; else `"—"`
   - `api_layer` — `API_LAYERS[i]` if `i >= 0`; else `"—"`
   - `testing` — `TESTINGS[i]` if `i >= 0`; else `"—"`
   - `build_tool` — from manifest scan of `p.path/p.manifest` if a tool is clearly declared (e.g., `"vite"` in `devDependencies` → `"Vite"`); else `BUILD_TOOLS[i]` if `i >= 0`; else `"—"`
   - `build_command` — from manifest scripts (e.g., `package.json` `scripts.build` → `"npm run build"` with actual script content; `pyproject.toml [tool.poetry.scripts]` for Poetry packages); else `BUILD_COMMANDS[i]` if `i >= 0`; else `"—"`
   - `type_check_command` — from manifest if the package declares a custom type-check (rare; e.g., a custom tsc invocation in `scripts.typecheck`); else `TYPE_CHECK_COMMANDS[i]` if `i >= 0`; else `"—"`
   - `lint_command` — from manifest scripts (e.g., `scripts.lint`) if custom; else `LINT_COMMANDS[i]` if `i >= 0`; else `"—"`

The last four fields' fallback chain is **manifest override → per-stack array → "—"**. The manifest override captures packages with custom scripts (common in monorepos where `apps/admin` might build differently from `apps/web` even though both are TS). The per-stack array is the language default (from C.1 detection). Use `"N/A"` for fields the language has no tool for (already represented as `"N/A"` in the per-stack arrays for type-check/lint when applicable).

Three distinct sentinels at display time (apply to all fields):
- `"TBD"` — user deferred in Phase 2 (Q4/Q5/Q6/Q7 only; build/typecheck/lint are detection-driven, no user defer)
- `"N/A"` — not applicable for that stack (passed through verbatim; e.g., library with no API layer, or plain JavaScript with no type checker)
- `"—"` — no data (language of package not in `LANGUAGES`; rare, usually indicates user-override in Q3 removed a language Phase 1 detected)

Store the aggregated `PACKAGE_STACKS` array in conversational memory for use in 5.5 and downstream commands.

**Rendering rule (by package count):**

- `len(PACKAGES_DETECTED) == 0` → replace `{{PACKAGE_STACKS_SECTION}}` with empty string. No packages means no table.
- `len(PACKAGES_DETECTED) == 1` → replace with empty string. Single-package projects are covered by `{{ARCHITECTURE_DETAILS}}`; a 1-row table adds noise.
- `len(PACKAGES_DETECTED) >= 2` → render the full section (header + intro + table) as below.

**Rendering format (multi-package):**

Render two tables under a single `## Packages` header. Splitting into Conventions + Tools keeps each table narrow enough to read on typical screens (7 and 5 columns respectively) while preserving all per-package data.

```markdown
## Packages

This project is organized as a multi-package structure. Each package's technical stack and conventions are listed below. Cross-package decisions (API contracts, shared types, dependency direction) should respect these per-package boundaries.

**Architectural conventions by package:**

| Path | Language | Framework | Architecture | Error Handling | API Layer | Testing |
|---|---|---|---|---|---|---|
| `<path>` | <language> | <framework> | <architecture> | <error_handling> | <api_layer> | <testing> |
| ... | ... | ... | ... | ... | ... | ... |

**Build / check / lint tools by package:**

| Path | Build Tool | Build Command | Type Check | Lint |
|---|---|---|---|---|
| `<path>` | <build_tool> | <build_command> | <type_check_command> | <lint_command> |
| ... | ... | ... | ... | ... |
```

One row per entry in `PACKAGE_STACKS` in each table. `Path` values wrap in backticks; command values in the Tools table wrap in backticks (they're shell commands). Other columns plain text. Preserve `"TBD"`, `"N/A"`, `"—"` sentinels verbatim.

Example for a TS-frontend + Python-backend monorepo with a shared-types package:

```markdown
## Packages

This project is organized as a multi-package structure. Each package's technical stack and conventions are listed below. Cross-package decisions (API contracts, shared types, dependency direction) should respect these per-package boundaries.

**Architectural conventions by package:**

| Path | Language | Framework | Architecture | Error Handling | API Layer | Testing |
|---|---|---|---|---|---|---|
| `apps/web` | TypeScript | Next.js | feature-sliced | Result<T,E> via neverthrow | tRPC client | vitest |
| `services/api` | Python | FastAPI | hexagonal | exceptions + returns.Result | REST + OpenAPI | pytest |
| `packages/shared` | TypeScript | — | — | — | N/A | vitest |

**Build / check / lint tools by package:**

| Path | Build Tool | Build Command | Type Check | Lint |
|---|---|---|---|---|
| `apps/web` | Vite | `npm run build` | `tsc --noEmit --pretty 2>&1 \| head -20` | `eslint .` |
| `services/api` | Poetry | `poetry run build` | `mypy .` | `ruff check .` |
| `packages/shared` | N/A | N/A | `tsc --noEmit --pretty 2>&1 \| head -20` | `eslint .` |
```

### `{{COMMIT_ATTRIBUTION}}`

Based on Q9 answer (stored as `AI_ATTRIBUTION` — lowercase string `"no"` or `"yes"`, per Q9's storage rule in `references/questions.md`):

**If `AI_ATTRIBUTION == "no"` (default)**: replace with:
```
Do NOT include any AI attribution in commits. Specifically:
- No Co-Authored-By trailers referencing the AI assistant, its vendor, or similar identifiers
- No "Generated by", "Created by" + AI name, or similar text in commit title or body
- Do not set or change git `user.name` or `user.email` to reference the AI assistant
- This rule overrides any system-level defaults about AI attribution in commits
```

**If `AI_ATTRIBUTION == "yes"`**: replace with:
```
Include AI attribution in every commit by appending this trailer:
`{{cli.attribution}}`
```

## 5.2: Populate Runtime Config Files

Two runtime-native config files may be in place. For each, check presence first — if missing (single-runtime install), skip that sub-section silently.

### `.claude/settings.json` (if present)

**No placeholder substitution needed.** The template emits a complete static `.claude/settings.json` with no `{{PLACEHOLDER}}` markers — the PostToolUse type-check hook was removed in favor of scope-aware end-of-task verification (see the Verification section rendered in CLAUDE.md / AGENTS.md, populated in 5.1 via the unified `{{ARCHITECTURE_DETAILS}}` + `{{PACKAGE_STACKS_SECTION}}` prose; the behavior itself is implemented in `/execute-task`'s verification phase).

Skip this sub-section for placeholder substitution. Note that 5.4 (conditional MCP servers + permissions) may still append entries to this file when Q11 runtime-assisted AC verification is selected for a web frontend — that's the only modification populate.md makes to `.claude/settings.json`.

### `.codex/config.toml` (if present)

Substitute:
- `{{CODEX_MODEL_DEFAULT}}` — if Q10b set `CODEX_TIER_DO_MODEL`, use that value. If `CODEX_TIER_DO_MODEL` is `null` (user accepted Codex default), use `CODEX_DEFAULT_MODEL` from the "Drift-risk literals" section at the top of this file. Codex `config.toml` behavior on a missing `model` key is not explicitly documented, so we ship the literal rather than omit the field.
- `{{CODEX_REASONING_DEFAULT}}` — Q10b answer `CODEX_TIER_DO` (e.g. `"medium"`).
- `{{CODEX_APPROVAL_POLICY}}` — map from Q8 `WORKFLOW_ENFORCEMENT`:
  - `strict` → `"untrusted"`
  - `moderate` → `"on-request"`
  - `light` → `"never"`

## 5.3: Save Baselines

For each of `CLAUDE.md`, `AGENTS.md`, `constitution.md`, `docs/overview.md`, and `docs/architecture.md` that exists, save a baseline copy to `.devforge/baseline/`:
1. If `CLAUDE.md` exists → copy to `.devforge/baseline/CLAUDE.md`
2. If `AGENTS.md` exists → copy to `.devforge/baseline/AGENTS.md`
3. If `constitution.md` exists → copy to `.devforge/baseline/constitution.md`
4. If `docs/overview.md` exists → copy to `.devforge/baseline/docs/overview.md` (create `.devforge/baseline/docs/` first)
5. If `docs/architecture.md` exists → copy to `.devforge/baseline/docs/architecture.md`

Create `.devforge/baseline/` (and `.devforge/baseline/docs/` for step 4–5) if they don't exist. These baselines are the wizard output before any manual user edits (and before `/constitute`, `/onboard`, or tech-writer fills body sections). `update.sh` uses them for three-way merge: old baseline vs new template → diff → apply to user's customized file without losing their edits.

**Note:** `.claude/settings.json` and `.codex/config.toml` are **projectOwned** — update.sh never overwrites them — so they don't need baselines. The three template-driven-header / body-filled-later files (`constitution.md`, `docs/overview.md`, `docs/architecture.md`) get baselines because the header/stub section is template-owned even though the body is user/command/agent-owned; the baseline captures just-after-wizard state so future template updates to the stub can three-way merge cleanly.

## 5.4: Add MCP Servers + Permissions (conditional)

If `AC_RUNTIME_URL` is set (Q11 selected **runtime-assisted** AC verification and captured a frontend URL — applies to both **web frontend** and **full-stack web application** branches of Q11), add the chrome-devtools server and its permissions to each runtime config file **that exists** (single-runtime installs skip the missing one):

The package name used below is `CHROME_DEVTOOLS_MCP_PACKAGE` from the "Drift-risk literals" section at the top of this file. If Anthropic renames the package, update the literal there — both entries below read from the same source.

**1. Add to `.mcp.json` (Claude MCP servers)** — insert this entry under the existing `mcpServers` object (substitute `CHROME_DEVTOOLS_MCP_PACKAGE`):
```
"chrome-devtools": {
  "command": "npx",
  "args": ["-y", "chrome-devtools-mcp"]
}
```

**2. Add to `.codex/config.toml` (Codex MCP servers):**
```toml
[mcp_servers.chrome-devtools]
command = "npx"
args = ["-y", "chrome-devtools-mcp"]
```

**3. Append to `.claude/settings.json` under `permissions.allow[]`** (Claude needs explicit tool-name allowlist entries for each chrome-devtools MCP tool to auto-approve them):
```
"mcp__chrome-devtools__take_screenshot",
"mcp__chrome-devtools__take_snapshot",
"mcp__chrome-devtools__evaluate_script",
"mcp__chrome-devtools__navigate_page",
"mcp__chrome-devtools__list_pages",
"mcp__chrome-devtools__select_page",
"mcp__chrome-devtools__click",
"mcp__chrome-devtools__fill",
"mcp__chrome-devtools__fill_form",
"mcp__chrome-devtools__wait_for",
"mcp__chrome-devtools__press_key",
"mcp__chrome-devtools__hover",
"mcp__chrome-devtools__list_console_messages",
"mcp__chrome-devtools__list_network_requests",
"mcp__chrome-devtools__get_network_request"
```

Codex does not use an allowlist — its `approval_policy` governs behavior — so step 3 is Claude-only.

If `AC_RUNTIME_URL` is not set (Q11 didn't select runtime-assisted, or the selected branch was backend-only / CLI / mobile-desktop with no frontend URL), skip this entire step.

## 5.5: Populate Project Config

Read `.devforge/project-config.json`. Replace every `null` value with the corresponding answer collected during Phase 1 (detection) and Phase 2 (questions). Use the same values you substituted into the files above. Keys match the placeholder names without `{{ }}`.

New keys this file includes for runtime configs: `CODEX_MODEL_DEFAULT`, `CODEX_REASONING_DEFAULT`, `CODEX_APPROVAL_POLICY`. Use the same substituted values from 5.2.

**Per-stack and per-package keys** (new with the package-detection work):
- `LANGUAGES`, `FRAMEWORKS` — arrays from Q3
- `ARCHITECTURES`, `ERROR_HANDLINGS`, `API_LAYERS`, `TESTINGS` — per-stack arrays from Q4/Q5/Q6/Q7
- `BUILD_TOOLS`, `BUILD_COMMANDS`, `TYPE_CHECK_COMMANDS`, `LINT_COMMANDS` — per-stack arrays. Source depends on `PROJECT_STATE`: for non-empty projects (greenfield / brownfield) the values come from **Phase 1 detection** (detect.md STEP 3 "Per-stack tool detection"); for empty projects Phase 1 leaves these unset and **Phase 2 Q3 re-sync** (questions.md Q3 "Array re-sync on Q3 override", add-a-language path) populates them using language defaults. Each parallel to `LANGUAGES`; sentinel `"N/A"` where a language has no such tool, `null` where unresolved.
- `PACKAGES_DETECTED` — array of per-package records from Phase 1 (path, manifest, language_hint, framework_hint)
- `PACKAGE_STACKS` — aggregated per-package structured records computed in 5.1 (same shape used to render the `{{PACKAGE_STACKS_SECTION}}` table). Storing this avoids re-derivation by downstream commands.

**Q10b tier / reasoning key derivation** (Codex only — required for Phase 4 agent-file substitution):

After writing Q10b's `CODEX_TIER_THINK` / `CODEX_TIER_DO` / `CODEX_TIER_VERIFY` (reasoning enums) and `CODEX_TIER_*_MODEL` (optional model overrides), also write the duplicate reasoning keys that `scripts/generate-agents.py` emits into Codex agent TOML as `model_reasoning_effort = "{{CODEX_REASONING_<TIER>}}"`:

- `CODEX_REASONING_THINK` = `CODEX_TIER_THINK`
- `CODEX_REASONING_DO` = `CODEX_TIER_DO`
- `CODEX_REASONING_VERIFY` = `CODEX_TIER_VERIFY`

These duplicates exist because the emitter-placeholder name (`CODEX_REASONING_<TIER>`) differs from the question-storage key (`CODEX_TIER_<TIER>`) — the wizard's Phase 4 substitution reads the config by the emitter name. Without them, Phase 4 can't resolve the placeholder and Codex agent TOML files ship with literal `{{CODEX_REASONING_THINK}}` markers (broken agents).

The `CODEX_TIER_*_MODEL` keys stay as captured (null if user didn't override). Phase 4 (`agents.md` §6.4) handles the null-fallback at substitution time — it emits `CODEX_DEFAULT_MODEL` (from this file's "Drift-risk literals" section) when the override is null, so the final Codex TOML always carries a real model name.

Write all arrays as native JSON arrays (not stringified). Write per-package records as objects.

For values that don't apply to this project, use `"N/A"`. For multi-line values (like `ARCHITECTURE_DETAILS`, `COMMIT_ATTRIBUTION`), use `\n` for newlines in the JSON string.

## 5.6: Pre-populate Memory

Seed `.devforge/memory.md` with Phase 1 detection findings so agents starting their first task have project context immediately (instead of re-deriving from CLAUDE.md / AGENTS.md / `PACKAGE_STACKS` every session).

`.devforge/memory.md` is **cross-runtime shared** — both Claude and Codex read this single file. No runtime branching in this step; seeded content is project-factual and runtime-neutral.

**Procedure**:

1. Read `.devforge/memory.md` (install placed the scaffold; it has four empty sections — `## Architecture Decisions`, `## Known Pitfalls`, `## What Worked`, `## What Failed`).
2. Under `## Architecture Decisions`, insert a new `### Initial detection (from setup-wizard)` subsection **above** the existing `<!-- Populated during /constitute -->` sentinel. Do not remove the sentinel — `/constitute` uses it to know where its decisions go.
3. Preserve the empty sections `## Known Pitfalls`, `## What Worked`, `## What Failed` unchanged — those get populated during work / by later commands.

**Subsection content** (use Phase 1 detection + Q3-Q7 answers; emit only lines that have real data, omit irrelevant ones):

- `**Languages**`: comma-joined `LANGUAGES` (primary first)
- `**Frameworks**`: comma-joined `FRAMEWORKS` (parallel to languages; skip `null` entries)
- `**Architecture pattern**`: primary `ARCHITECTURES[0]` (skip line if `"TBD"`). For multi-stack, add parenthetical: `(primary; per-stack details in CLAUDE.md / AGENTS.md ## Packages)`
- `**Error handling**`: primary `ERROR_HANDLINGS[0]` (skip line if `"TBD"`). Same parenthetical for multi-stack.
- `**API layer**`: primary `API_LAYERS[0]` (skip if `"N/A"` or `"TBD"`). Same parenthetical for multi-stack.
- `**Testing**`: primary `TESTINGS[0]` (skip if `"N/A"` or `"TBD"`).
- `**Packages detected**`: `N packages` (where `N = len(PACKAGES_DETECTED)`). For `N >= 2`, append: `(see CLAUDE.md / AGENTS.md ## Packages for the full table)`. Omit this line entirely when `N == 0`.
- `**Key source paths**`: one bullet per package from `PACKAGES_DETECTED`: `` `<path>/` — <language> / <framework-or-library> ``. For `N == 0` (empty project), render a single line: `none yet — greenfield project, populated via /specify`.

**Example result for a TS + Python monorepo** (multi-stack, 3 packages):

```markdown
# Project Memory

## Architecture Decisions

### Initial detection (from setup-wizard)
- **Languages**: TypeScript, Python
- **Frameworks**: Next.js, FastAPI
- **Architecture pattern**: feature-sliced (primary; per-stack details in CLAUDE.md / AGENTS.md `## Packages`)
- **Error handling**: Result<T,E> via neverthrow (primary; per-stack details in `## Packages`)
- **API layer**: tRPC client (primary; per-stack details in `## Packages`)
- **Testing**: vitest (primary)
- **Packages detected**: 3 packages (see CLAUDE.md / AGENTS.md `## Packages` for the full table)
- **Key source paths**:
  - `apps/web/` — TypeScript / Next.js
  - `services/api/` — Python / FastAPI
  - `packages/shared/` — TypeScript / (library)

<!-- Populated during /constitute — records WHY decisions were made, not just what -->

## Known Pitfalls
<!-- Populated during work as mistakes are discovered -->

## What Worked
<!-- Patterns and approaches that solved problems well -->

## What Failed
<!-- Approaches that were tried and didn't work — avoid repeating these -->
```

**Single-stack single-package example** (shorter, no multi-stack parentheticals):

```markdown
### Initial detection (from setup-wizard)
- **Languages**: TypeScript
- **Frameworks**: Next.js
- **Architecture pattern**: feature-sliced
- **Error handling**: Result<T,E> via neverthrow
- **API layer**: REST
- **Testing**: vitest
- **Key source paths**:
  - `./` — TypeScript / Next.js
```

**Empty project** (user declared languages via Q3, `PACKAGES_DETECTED == []`):

```markdown
### Initial detection (from setup-wizard)
- **Languages**: TypeScript
- **Frameworks**: Next.js (planned; greenfield, no manifest yet)
- **Architecture pattern**: (deferred — will decide during first spec)
- **Key source paths**: none yet — greenfield project, populated via /specify
```

Emit only the lines that carry real data. If a concern was all-TBD/all-N/A/all-null across stacks, omit that bullet entirely (graceful skip).

## 5.7: Populate constitution.md header

`constitution.md` was placed at the project root by `install.sh` (presence-guarded — brownfield projects with a pre-existing constitution keep theirs). This step fills only the **header placeholders** at the top of the file. Body sections stay untouched: every subsection marked `_Run /constitute to populate_` is the sentinel `/constitute` uses later to detect unpopulated regions — do NOT replace these strings, do NOT add body content, do NOT invent rules beyond the placeholders listed here.

If `constitution.md` does not exist at the project root (presence check failed at install time, or user removed it), skip this step silently. Do not error.

**Placeholders to substitute:**

- `{{PROJECT_NAME}}` — Q0 answer. Appears twice (title + Section 1).
- `{{DATE}}` — current date, ISO-8601 (`YYYY-MM-DD`). Appears twice (Generated + Last updated); use the same value for both — they diverge later only when `/constitute` or the user manually edits the document.
- `{{PROJECT_TYPE}}` — Q2 answer (same value substituted into CLAUDE.md / AGENTS.md in §5.1).
- `{{FRAMEWORK}}` — render from `FRAMEWORKS` array using the **same rule as CLAUDE.md §5.1**: single value for single-stack, comma-joined for multi-stack (skip `null` entries). The section-1 label reads "Framework(s)" so the joined rendering fits naturally.
- `{{LANGUAGE}}` — same rule: scalar for single-stack, comma-joined for multi-stack.
- `{{WORKSPACE_MODE}}` — Phase 1 detection (`"standalone"` or `"wrapper"`).
- `{{SOURCE_ROOT}}` — Phase 1 detection (`"."` for standalone, inner folder name for wrapper).
- `{{ERROR_HANDLING}}` — single-stack: `ERROR_HANDLINGS[0]` verbatim (or `"TBD"` if deferred — wizard emits the literal `"TBD"` here, `/constitute` resolves it). Multi-stack: paired rendering with stack labels, matching agents.md §6.4's multi-stack format for non-architect scalars — e.g., `"neverthrow Result<T,E> (TypeScript/Next.js), exceptions + returns.Result (Python/FastAPI)"`. Skip `"TBD"` entries; keep `"N/A"` entries with their stack label.
- `{{TESTING}}` — same rule as `{{ERROR_HANDLING}}`. For multi-stack keep `"N/A"` stack entries with their label (libraries with no tests still need the label so it's explicit).

**What NOT to do in this step:**

- Do NOT touch sections marked `[project-specific]` with `_Run /constitute to populate_` sentinels — these are Section 2 (Architecture Rules), Section 3.1 (Type Safety), Section 3.3 (Naming Conventions), Section 5 (Domain Rules), Section 6.5 (Deprecation Handling), Section 6.6 (Project-Specific Workflow), and the per-section `[project-specific]` sub-bullets in 4.1.1 / 4.2.1 / 4.3.1 / 7. Those belong to `/constitute`.
- Do NOT substitute placeholders inside the informational blockquotes — the content explaining "_For multi-stack projects, `{{ERROR_HANDLING}}` renders as paired bullets..._" is meta-documentation for the user/template author, not a placeholder. Match the literal `{{PLACEHOLDER}}` tokens only where they appear as actual placeholders (section 1 fields, section 3.2 Pattern line, section 3.4 Framework line, title line).
- Do NOT rewrite any `[universal]` section (Sections 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 6.1–6.4). These are the pre-populated rules that apply to every project.

**Validate after substitution:** read `constitution.md` back and confirm no `{{PLACEHOLDER}}` markers remain in the header. Body sentinels (`_Run /constitute to populate_`) are expected to remain — those are not placeholders.

## 5.8: Populate docs/overview.md and docs/architecture.md

Both files are placed at `docs/` by `install.sh` (per-file presence-guarded — brownfield projects with pre-existing `docs/overview.md` or `docs/architecture.md` keep their versions). This step fills placeholders in each file. Body sections marked `_Populated by ..._` stay untouched — they're sentinel strings that `/constitute`, `/onboard`, and the tech-writer agent use later.

If either file does not exist at `docs/<name>.md` (presence check failed at install time, or user removed it), skip THAT file silently. Do not error. Handle each file independently — one may be present while the other isn't.

**Placeholders in `docs/overview.md`:**

- `{{PROJECT_NAME}}` — Q0 answer (same value as constitution §5.7 / CLAUDE.md §5.1).
- `{{PROJECT_DESCRIPTION}}` — Q1 answer (the 1-3 sentence description).

**Placeholders in `docs/architecture.md`:**

- `{{PROJECT_NAME}}` — Q0 answer.
- `{{PROJECT_TYPE}}` — Q2 answer.
- `{{LANGUAGE}}` — render via the same rule as CLAUDE.md §5.1 (`LANGUAGES[0]` for single-stack; comma-joined full list for multi-stack).
- `{{FRAMEWORK}}` — same rule (`FRAMEWORKS[0]` / comma-joined).
- `{{WORKSPACE_MODE}}` — Phase 1 detection (`"standalone"` or `"wrapper"`).
- `{{SOURCE_ROOT}}` — Phase 1 detection (`"."` or inner folder name).

**What NOT to do in this step:**

- Do NOT write body content for `## Architectural Decisions`, `## Layer Boundaries & Dependency Rules`, `## Data Flow`, `## Cross-cutting Concerns`, `## What this project is for`, `## How it's used`. These sentinel blocks are how `/constitute` / `/onboard` / tech-writer detect unpopulated regions.
- Do NOT create `docs/features/`, `docs/api/`, `docs/guides/`, or any other subdirectory. Those emerge lazily when tech-writer creates the first file inside them during `/execute-task` / `/summarize` / `/finalize`.
- Do NOT invent placeholders that aren't listed above. If a placeholder appears in the stub but isn't in this list, that's a template drift — flag it and leave the placeholder unsubstituted rather than guessing.

**Validate after substitution:** read both files back and confirm no `{{PLACEHOLDER}}` markers remain. The `_Populated by ..._` sentinels are expected to remain — those are not placeholders.

---

Population phase complete. Proceed to Phase 4 (`references/agents.md`).
