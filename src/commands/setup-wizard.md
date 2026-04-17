# {{cli.sigil}}setup-wizard — Project Initialization Wizard

You are running the initial setup wizard for AIDevTeamForge. Your job is:

1. Analyze the current project.
2. Ask the user targeted questions via confirm / override / defer.
3. Substitute the user's answers into the `{{PLACEHOLDER}}` markers in every target file that has them. All files are already in place — **you do NOT create new files**.
4. Where specific files have designated project-specific sections (e.g., CLAUDE.md / AGENTS.md architecture notes, agent files with project paths, constitution custom clauses), append content derived from detection + user answers to those sections only. **Never rewrite whole files.**
5. Write the answers record to `.devforge/project-config.json` so later commands and `update.sh` can consume user decisions.

## STEP 0: Workspace Mode Detection

Before scanning source code, determine whether this is a standalone project or a wrapper workspace.

### 0.1: Auto-Detect Nested Git Repos

Scan for directories at depth 1 (direct children of the workspace root) that contain a `.git/` directory. Skip `.git` itself, hidden directories (starting with `.`), and any obvious dependency or build-artifact directory — use your knowledge of the ecosystem (e.g. `node_modules/`, `vendor/`, `target/`, `venv/`, `.venv/`, `__pycache__/`, `build/`, `dist/`, `.gradle/`, `out/`).

### 0.2: Present Finding & Ask

**If exactly one nested `.git` directory is found** (e.g., `client-project/.git`):

{{ask "I found a nested git repository at `[folder-name]/`. Is this a wrapper workspace where template artifacts live at the outer root and the actual source code lives in that subfolder?"}}
- Yes, this is a wrapper around `[folder-name]`
- No, this is a standalone project
{{/ask}}

**If zero nested `.git` directories are found:**

{{ask "Is this a standalone project, or a wrapper workspace around a client project folder?"}}
- Standalone project
- Wrapper workspace
{{/ask}}

If the user picks "Wrapper workspace", follow up with a second ask: "Which folder contains the client's source code?"

**If multiple nested `.git` directories are found:**

{{ask "I found multiple nested git repositories: [list folder names]. Is this a wrapper workspace? If yes, which folder is the primary source root?"}}
- Standalone (treat the outer root as the source)
- Wrapper around [folder-1]
- Wrapper around [folder-2]
- Wrapper around [folder-3]
- ... (one wrapper option per detected folder)
{{/ask}}

Multi-root wrapper (coordinating across several of the nested repos simultaneously) is not currently supported. If the user indicates that's what they want, tell them to pick one primary root for now and raise the multi-root case as a feature request.

### 0.3: Set Source Root

Store the result for use in all subsequent steps:
- **Standalone**: `SOURCE_ROOT = "."`
- **Wrapper**: `SOURCE_ROOT = "[folder-name]"` (e.g., `client-project`)

Track `SOURCE_ROOT` in your working context throughout the rest of the wizard; at the end it's persisted to `.devforge/project-config.json` along with all other collected answers.

If wrapper mode:
- Inform the user: "Wrapper mode activated. Source root: `[folder-name]/`. All template artifacts will live in the wrapper root. I'll scan the source code inside `[folder-name]/`."
- Verify the inner folder exists and contains files

## STEP 1: Project State

{{ask "What state is this project in?"}}
- Empty / brand new — no code, no config files, directory was just created
- Greenfield / just scaffolded — ran a starter tool (e.g. npm create, cargo new, flutter create, django-admin startproject), only boilerplate present, no custom code yet
- Brownfield / existing — real codebase with custom code, established patterns and conventions
{{/ask}}

Store the result as `PROJECT_STATE`. This controls detection depth in STEP 3 and question behavior in STEP 4:

- **Empty**: skip STEP 3 entirely — there's nothing to scan. All project info comes from user answers in STEP 4.
- **Greenfield**: STEP 3 does a light scan — read config/manifest files only (e.g. `package.json`, `Cargo.toml`, `tsconfig.json`, `pyproject.toml`) to extract language, framework, and tooling. Skip source-code scanning for patterns. In STEP 4, ask MORE questions since there's less to auto-detect. In STEP 5, use framework best-practice defaults instead of extracted patterns.
- **Brownfield**: STEP 3 does a full scan — read configs + representative source files to detect architecture, error handling, conventions. In STEP 5, use project-specific patterns extracted from real code.

## STEP 2: Default Branch

{{ask "What is the default branch for this project?"}}
- main (most common)
- master
- develop
- Other — user specifies
{{/ask}}

Store as `DEFAULT_BRANCH`. This is used during scanning (STEP 3), population (STEP 5) and generation (STEP 6), and by downstream commands for git operations.

## STEP 3: Auto-Detect Project Structure

**If `PROJECT_STATE` is empty, skip this step entirely and go to STEP 4.**

**All scanning in this step targets the SOURCE_ROOT directory.** For standalone projects this is the workspace root (`.`). For wrapper projects this is the inner folder (e.g., `client-project/`). Resolve all file paths relative to SOURCE_ROOT.

Read dependency manifests, lockfiles, config files, and top-level directory layout at SOURCE_ROOT to identify the project's tech stack. Typical starting points: dependency manifests like `package.json`, `pyproject.toml`, `requirements.txt`, `Pipfile`, `go.mod`, `Cargo.toml`, `pubspec.yaml`, `Gemfile`, `composer.json`, `*.csproj`, `mix.exs`, `deno.json`; config files like `tsconfig.json`, `.eslintrc.*`, `tailwind.config.*`, `pyrightconfig.json`; and structural markers like `Dockerfile`, `.github/workflows/`, workspace/monorepo files (`pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`, Cargo workspace, Go workspaces).

**Brownfield only:** also scan a few representative source files to infer architectural patterns (layered / feature-modular / MVC / BLoC / hexagonal / etc.) and error-handling conventions (Either-style results / typed exceptions / traditional try-catch / HTTP-error patterns / etc.).

Based on what you find, identify each of the following. Mark any category that genuinely doesn't apply as **N/A**. If you're uncertain, note the uncertainty and raise it with the user in STEP 4 rather than guessing.

- **Languages and runtimes** — detect all present. If multiple (monorepo, polyglot, cross-platform), order them by approximate file count descending (most files first). Note the associated runtime per language (TypeScript → Node, Python → Python 3, Dart → Flutter, etc.).
- **Primary framework(s)** (app-level, not library-level)
- **Package manager** (if applicable)
- **Testing framework(s)** (if present)
- **Linting / formatting tools** (if configured)
- **Build tool / bundler**
- **Monorepo tool** (if applicable)
- **Styling approach** (web frontends only — CSS approach, UI framework)
- **State management** (web/mobile frontends only, if detectable)
- **API layer** (REST / GraphQL / gRPC / tRPC / etc., if applicable)
- **Architecture pattern** (for existing projects with enough code to infer)
- **Error handling pattern** (for existing projects, from representative source)
- **CI/CD presence** and tooling (GitHub Actions, GitLab CI, etc.)
- **Containerization** (Dockerfile, docker-compose, buildpacks, etc.)

Do not invent details or fill categories with plausible-sounding defaults. An honest "uncertain — will ask the user" beats a confident wrong guess. Do not limit yourself to the indicators mentioned above — examine whatever is actually present, in whatever ecosystem the project uses.

## STEP 4: Present Findings & Ask Questions

Present what you detected in STEP 3 in a clear summary (or, if `PROJECT_STATE` is empty, skip the summary and go straight to questions). Walk the user through each question in order (Q0 → Q9; later questions depend on earlier answers). Every question is labeled with exactly one of three markers:

- **REQUIRED** — must be answered. Offer **confirm / override**. Defer is not allowed; downstream commands depend on the value.
- **OPTIONAL** — user may answer or explicitly defer. Offer **confirm / override / defer**. "Defer" marks the field as `TBD` and downstream commands will ask when the field becomes relevant (e.g., when `{{cli.sigil}}specify` needs an architecture decision for a specific feature). A small number of OPTIONAL questions are free-text only (e.g. "anything else I should know?") — those are noted explicitly and allow an empty response.
- **CONDITIONAL** — may not apply to this project. If it doesn't apply, skip it and record the natural default (this is the one case where a silent default is permitted; the marker acknowledges it). If it does apply, treat as REQUIRED (confirm / override — no silent guess).

For every question that applies, do NOT silently default. Do NOT infer answers. The user's confirmed answers are the canonical input across all runtimes — that's what keeps outputs consistent between Claude, Codex, and any future runtime.

**Anti-hallucination rule for findings.** When presenting findings to the user (anywhere you'd fill `[findings]`, `[observed indicators]`, `[pattern indicators]`, `[detected framework]`, etc.), quote ONLY concrete observed facts: exact file paths, exact package names, exact config keys, exact imports or symbols you actually read. Do NOT invent indicators to make the prose flow. If detection surfaced nothing for a category, say so plainly (e.g. "I found no framework dependencies, so I can't infer the stack — could you tell me what you're using?") instead of fabricating plausibles.

**Where answers are stored.** As you walk through the questions below, track the user's answers in your working context. At the end of the wizard, every collected answer is written to `.devforge/project-config.json`. That file is the canonical record — every command under every CLI (Claude, Codex, and later runtimes), plus `update.sh`, reads from it. Use the variable names noted in each question (e.g. `SOURCE_ROOT`, `PROJECT_NAME`, `CLAUDE_TIER_THINK`) as the keys.

### Question 0: Project Name (REQUIRED)

**If a manifest file exists at SOURCE_ROOT** (`package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `pubspec.yaml`, `*.csproj`, `mix.exs`, `deno.json`, or equivalent) **and contains a name field:**

> I found the project name `[detected name]` in `[manifest file]`. Confirm or override.

**If no manifest or no name field:**

> What is this project called?

Store as `PROJECT_NAME`.

### Question 1: Project Description (REQUIRED)

**If README.md (or README.rst, README.txt) exists at SOURCE_ROOT and contains a meaningful description (not just a scaffolded heading):**

> I found this in your README:
>
> > [quote the first paragraph or summary section — max ~3 sentences]
>
> Does this describe the project well? Confirm, or give me a better description in 1-3 sentences — what does it do, who is it for?

**If no README or README is empty/boilerplate:**

> Describe this project in 1-3 sentences — what does it do, who is it for?

Store as `PROJECT_DESCRIPTION`. This is placed in the Project Overview section of CLAUDE.md / AGENTS.md and gives every downstream command and agent domain context for design decisions, naming, error messages, and UX choices.

### Question 2: Project Type (REQUIRED)

Present the question to the user. If STEP 3 detection surfaced concrete indicators, quote them explicitly; if nothing was detected (or `PROJECT_STATE` is empty), say so plainly and just ask. Do not invent.

**If concrete indicators were found:**

> Based on what I found — [quote 2–5 specific observed facts: exact dep names, exact file paths, exact config markers] — this looks like a [proposed type]. What type of project is this?
>
> Options:
> - Frontend / web application
> - Backend API / service
> - Full-stack web application
> - Mobile application (native or cross-platform)
> - Desktop application (Electron, Tauri, native)
> - CLI tool / script
> - Library / package / SDK
> - Plugin / extension / add-on
> - Data pipeline / ETL / batch job
> - ML / data science / AI model
> - Game
> - Infrastructure-as-code / config management
> - Documentation / static site
> - Other — user describes their own category (e.g., "firmware", "Figma plugin", "browser extension", "Slack bot")

**If nothing was detected (empty / greenfield / unclear):**

> I couldn't detect enough from the files alone to guess. What type of project is this?
>
> Options: [same list as above]

### Question 3: Languages & Frameworks (REQUIRED)

**If a single language dominates:**

> I found [language] with [framework]. Confirm, override, or describe if different.

**If multiple languages are present (monorepo, polyglot, cross-platform):**

> I found multiple languages, ordered by approximate file count:
> - [language 1] (~[n] files) with [framework 1]
> - [language 2] (~[n] files) with [framework 2]
> - ...
>
> The first in the list is treated as the project's "primary" language for downstream defaults (default agent, default type-check command, etc.). Commands still operate correctly on files in other languages — "primary" only controls what to pick when no file or context is specified.
>
> Options:
> - Confirm this ordering
> - Override — reorder, or specify a different primary

Store as:
- `LANGUAGES` = ordered array of detected language strings (e.g. `["TypeScript", "Python"]`)
- `FRAMEWORKS` = parallel array; each element is the dominant framework for the language at the same index (or `null` if none)
- `PRIMARY_LANGUAGE` = first element of `LANGUAGES` (or the user's explicit pick if they overrode the ordering)

Accept free-text for override — no hardcoded framework list.

### Question 4: Architecture Pattern (OPTIONAL)

**If detection identified a pattern with reasonable confidence (existing project):**

> I see [specific folders/files you observed]. This looks like [detected pattern]. Confirm, override, or defer.
>
> Options:
> - Confirm: [detected pattern]
> - Override — name a different pattern
> - Defer — establish the pattern as the project evolves

**If detection was uncertain or the project has no clear pattern (existing project):**

> I scanned the code but couldn't identify a clear architecture pattern. Which does this project follow?
>
> Options:
> - Name a pattern (e.g., Clean Architecture, MVC, feature-modular, hexagonal, layered, flat)
> - Defer — establish the pattern as the project evolves

**If the project is empty or greenfield:**

> Which architecture pattern do you want to follow?
>
> Options:
> - Name a pattern (Clean Architecture, MVC, feature-modular, hexagonal, etc.)
> - Defer — decide as features get built

### Question 5: Error Handling Convention (OPTIONAL)

Error handling is typically project-specific, not just language-specific. Even in languages with a dominant default (Go's `(value, error)` returns, Python's exceptions, Rust's `Result<T, E>`), projects commonly layer library-level conventions on top — `pkg/errors` / `hashicorp/go-multierror` for Go; `returns` / `rustedpy/result` for Python; `anyhow` / `thiserror` / `eyre` for Rust; Either-style libraries or custom error hierarchies for TypeScript; etc.

Before asking, scan a few representative source files for error-handling imports and patterns. Quote what you actually saw (anti-hallucination rule applies).

**Existing projects:**

> I saw [specific imports or patterns observed in source, e.g. `thiserror` derives on error types in `src/error.rs`, `?` operator throughout]. How does this project handle errors?
>
> Options:
> - Confirm: [your summary of what you saw]
> - Override — name a different convention
> - Defer — establish the pattern as the project evolves

**Empty / greenfield projects:**

> How should this project handle errors?
>
> Options:
> - Name a convention (e.g. "language default", "`thiserror` + `?` for Rust", "`returns` Result in Python", "Either/Result via neverthrow", "HTTP-codes at boundary + typed results internally")
> - Defer — decide during the first spec

### Question 6: Workflow Enforcement Level (REQUIRED)

This controls how many user-approval gates appear in the workflow and how strict post-edit verification is. The underlying verification mechanism varies per runtime — on some runtimes it's automatic after every edit, on others it's an explicit `{{cli.sigil}}verify` step — but the behaviors below are the same regardless.

> How strict should workflow enforcement be?
>
> Options:
> - **Strict** — user approval required at every phase gate (specify → plan → breakdown → execute → verify). Verification runs after every code-writing step.
> - **Moderate** — user approval at spec and task-breakdown gates only. Verification runs after every code-writing step, but running `{{cli.sigil}}verify` explicitly is optional.
> - **Light** — user approval at the initial spec only. Verification runs, but fewer interactive gates.

Recommend Strict for new users. This field is required because it directly shapes downstream command behavior.

Store as `WORKFLOW_ENFORCEMENT`. This value is consumed by every command that has gates (execute-task, specify, plan, breakdown, verify, fix, refactor) — each command reads it from `.devforge/project-config.json` at runtime to decide whether to show approval gates or skip them.

### Question 7: AI Attribution in Commits (REQUIRED)

> Should commits created by the AI assistant include co-author attribution?
>
> Options:
> - No — commits will have no AI attribution (recommended default)
> - Yes — commits will include the trailer: `{{cli.attribution}}`

### Question 8: Agent Model Assignments (per-runtime)

Specialized agents are grouped into three tiers based on the reasoning they require. Ask the sub-question for each supported runtime (since install produces artifacts for every enabled runtime, all sub-questions are asked by default). Use **confirm / override / defer** semantics from the STEP 4 preamble — don't silently default.

**Tiers (shared across runtimes):**

| Tier | Agents | Purpose |
|------|--------|---------|
| **Think** | `architect`, `api-designer`, `security-reviewer` | Design decisions, interface contracts, security analysis — deep reasoning |
| **Do** | `backend-engineer`, `frontend-engineer`, `mobile-engineer`, `db-engineer`, `devops-engineer`, `migration-engineer`, `runtime-debugger`, `performance-analyst`, `design-auditor` | Implementation following established patterns — benefits from speed |
| **Verify** | `code-reviewer`, `ac-verifier`, `qa-engineer` | Code review, AC verification, test generation — understands intent, doesn't design from scratch |

The `tech-writer` agent is hardcoded to a lightweight default regardless of tier choices — documentation generation doesn't benefit from heavier reasoning.

- Under Claude: tech-writer uses `sonnet`.
- Under Codex: tech-writer uses `medium` reasoning effort.

**Key naming convention (uniform across runtimes):** tier values are stored under `{{RUNTIME}}_TIER_{{ROLE}}` (e.g. `CLAUDE_TIER_THINK`, `CODEX_TIER_DO`). The VALUE under each key is runtime-specific — a model name for Claude, a reasoning-effort enum for Codex — but the KEY SHAPE is symmetric so consumers (update.sh, agent materializer, future runtimes) can iterate uniformly. Model-override secondary keys use a `_MODEL` suffix: `CODEX_TIER_THINK_MODEL`.

#### 8a: Claude model tiers

Claude exposes three named models: `opus` (heaviest reasoning), `sonnet` (balanced), `haiku` (fastest).

> **Think tier:** opus (default) / sonnet / haiku
> **Do tier:** sonnet (default) / opus / haiku
> **Verify tier:** sonnet (default) / opus / haiku

Recommended defaults: opus / sonnet / sonnet. Store in config as:
- `CLAUDE_TIER_THINK` = model name (e.g. `"opus"`)
- `CLAUDE_TIER_DO` = model name
- `CLAUDE_TIER_VERIFY` = model name

#### 8b: Codex model tiers

Codex tunes agent behavior via `model_reasoning_effort` rather than named model tiers. Valid values: `minimal | low | medium | high | xhigh` (with `xhigh` requiring a Responses-API-capable model). Model selection is separate and defaults to the Codex CLI's current default (e.g. `gpt-5.4` or the latest coding-optimized model available at install time).

> **Think tier reasoning effort:** high (default) / xhigh / medium
> **Do tier reasoning effort:** medium (default) / low / high
> **Verify tier reasoning effort:** medium (default) / low / high

Recommended defaults: high / medium / medium. Store in config as:
- `CODEX_TIER_THINK` = reasoning-effort enum (e.g. `"high"`)
- `CODEX_TIER_DO` = reasoning-effort enum
- `CODEX_TIER_VERIFY` = reasoning-effort enum

Override the underlying model per tier only if the user explicitly asks — otherwise leave the Codex default. Store optional overrides as:
- `CODEX_TIER_THINK_MODEL` = model name or `null`
- `CODEX_TIER_DO_MODEL` = model name or `null`
- `CODEX_TIER_VERIFY_MODEL` = model name or `null`

### Question 9: Acceptance Criteria Verification (REQUIRED)

When the user runs `{{cli.sigil}}verify` after a task completes, how should acceptance criteria be checked? Pick one mode:

> Options:
> - **Code-only** — verify by reading code against the AC spec. No execution. Works for any project type; safe pick if unsure.
> - **Tests** — run the project's test suite; failures indicate AC violations. Good fit when the project has meaningful tests.
> - **Runtime-assisted** — run the built artifact and interact with it. Good fit when the artifact is easily launchable (web app, backend, CLI) and AC is observable at runtime.
> - **Off** — skip AC verification; user handles manually. Only choose this if the user explicitly wants to opt out.

Store the chosen mode as `AC_VERIFICATION_MODE`.

#### Runtime-assisted follow-ups (only if that mode was chosen)

Branch by the project type confirmed in Q2 (not what STEP 3 detected — Q2's answer is canonical). If Q2's answer was "Other" or ambiguous, ask the user for a specific category; if still unclear, fall back to **Code-only**.

**Web frontend:**

> What URL does the dev server serve the app on? (e.g. http://localhost:5173)

Store the URL as `AC_RUNTIME_URL`. Flag for STEP 5: the wizard needs to add the chrome-devtools MCP server to `.mcp.json` and `.codex/config.toml`.

**Backend with HTTP API:**

> What base URL should `{{cli.sigil}}verify` use for API endpoints? (e.g. http://localhost:3000, http://localhost:8000)

Store as `AC_RUNTIME_API_BASE`.

**CLI tool:**

> What command launches the built tool? (e.g. `./target/release/myapp`, `python -m mypackage`, `node dist/cli.js`, `go run ./cmd/myapp`)

Store as `AC_RUNTIME_CLI_COMMAND`.

**Mobile / desktop / game / other non-automatable:**

> Runtime-assisted verification for this project type is largely manual — `{{cli.sigil}}verify` will describe what to check, but the user will run the checks themselves. Confirm Runtime-assisted mode, or switch to Code-only / Tests.

No follow-up storage needed beyond `AC_VERIFICATION_MODE` in this case.

## STEP 5: Populate Placed Files

All files are already in place. Your job is substitution only — **do not create new files**. Read each file, replace every `{{PLACEHOLDER}}` marker with the corresponding value, and write it back.

### 5.1: Populate CLAUDE.md and AGENTS.md

Read `CLAUDE.md` and `AGENTS.md` at project root. Both files contain the same `{{PLACEHOLDER}}` markers. Substitute ALL of them with the same values:

- `{{PROJECT_DESCRIPTION}}` — Q1 answer: the 1-3 sentence project description
- `{{PROJECT_NAME}}` — Q0 answer: project name
- `{{PROJECT_TYPE}}` — Q2 answer (e.g., "Frontend application", "Backend API", "Full-stack web application")
- `{{FRAMEWORK}}` — Q3 answer: primary framework (e.g., "Vue 3", "FastAPI", "Next.js"). If multiple, use the primary one.
- `{{LANGUAGE}}` — Q3 answer: primary language (e.g., "TypeScript", "Python", "Rust")
- `{{BUILD_TOOL}}` — detected in STEP 3: the build tool name (e.g., "Vite", "Webpack", "Cargo", "Go"). If none detected, `"N/A"`.
- `{{BUILD_COMMAND}}` — detected in STEP 3: the actual build command. Use your knowledge of the detected ecosystem to determine the correct command (e.g., `npm run build`, `cargo build`, `go build ./...`, `make build`). For wrapper mode, prefix with `cd SOURCE_ROOT &&`. If none detected, `"N/A"`.
- `{{TYPE_CHECK_COMMAND}}` — detected in STEP 3: the type-check command for the project's language (e.g., `tsc --noEmit --pretty 2>&1 | head -20`, `mypy .`, `cargo check 2>&1 | head -20`, `go vet ./...`). For wrapper mode, prefix with `cd SOURCE_ROOT &&`. If the language has no type checker, `"N/A"`.
- `{{LINT_COMMAND}}` — detected in STEP 3: the lint command (e.g., `eslint .`, `ruff check .`, `golangci-lint run`). For wrapper mode, prefix with `cd SOURCE_ROOT &&`. If none detected, `"N/A"`.
- `{{SOURCE_ROOT}}` — STEP 0 answer: `.` for standalone, or the inner folder name for wrapper (e.g., `client-project`)
- `{{WRAPPER_MODE_SECTION}}` — see below
- `{{PROJECT_STRUCTURE}}` — see below
- `{{DEV_COMMANDS}}` — see below
- `{{ARCHITECTURE_DETAILS}}` — see below
- `{{AGENT_LIST}}` — `"No agents installed. Agents will be added in a future update."` (agents are not yet part of the install scope)
- `{{COMMIT_ATTRIBUTION}}` — see below

#### `{{WRAPPER_MODE_SECTION}}`

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

#### `{{PROJECT_STRUCTURE}}`

Scan SOURCE_ROOT and generate a tree of the actual project structure. Show directories and key files (entry points, configs, manifests). Collapse large directories (e.g., `src/components/ (47 files)`). Keep it under 30 lines. Example:

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

**Greenfield/empty project**: show whatever exists (possibly just the manifest file and a `src/` stub).

#### `{{DEV_COMMANDS}}`

Extract actual dev/build/test/lint commands from the project's manifest or config files. Format as a markdown list:

```markdown
- `npm run dev` — Start development server
- `npm run build` — Production build
- `npm test` — Run test suite
- `npm run lint` — Run linter
```

Use your knowledge of the detected ecosystem to identify the correct command runner (`npm`, `yarn`, `pnpm`, `cargo`, `go`, `make`, `poetry`, etc.) based on lockfiles and manifest.

**Greenfield note**: If no scripts exist yet, generate sensible defaults based on the chosen framework and build tool. Mark them: `<!-- default, update after scaffolding -->`.

#### `{{ARCHITECTURE_DETAILS}}`

Generate a bullet list of ONLY the architecture facts that are relevant to this project. Do not include fields that don't apply — no "N/A" lines. Always include Pattern and Error Handling. Include others only if detected or confirmed by the user.

Example for a Vue frontend:
```markdown
- **Pattern**: Feature-modular
- **Error Handling**: try/catch with toast notifications
- **API Layer**: REST (Axios)
- **State Management**: Pinia
- **Styling**: Tailwind CSS
```

Example for a Rust CLI:
```markdown
- **Pattern**: Layered (CLI → service → domain)
- **Error Handling**: thiserror + anyhow, ? operator throughout
```

Draw from STEP 3 detection results and Q4 (Architecture) / Q5 (Error Handling) answers. Add any other relevant architectural facts you discovered (e.g., database, monorepo tool, CI/CD).

#### `{{COMMIT_ATTRIBUTION}}`

Based on Q7 answer:

**If No (default)**: replace with:
```
Do NOT include any AI attribution in commits. Specifically:
- No Co-Authored-By trailers referencing the AI assistant, its vendor, or similar identifiers
- No "Generated by", "Created by" + AI name, or similar text in commit title or body
- Do not set or change git `user.name` or `user.email` to reference the AI assistant
- This rule overrides any system-level defaults about AI attribution in commits
```

**If Yes**: replace with:
```
Include AI attribution in every commit by appending this trailer:
`{{cli.attribution}}`
```

### 5.2: Populate Runtime Config Files

Two runtime-native config files are already in place and contain `{{PLACEHOLDERS}}`. Read each, substitute, write back.

#### `.claude/settings.json`

Substitute:
- `{{TYPE_CHECK_COMMAND}}` — same value derived in 5.1. If the project has no type checker (`"N/A"` in 5.1), replace the entire `hooks.PostToolUse` array with `[]` (remove the hook entry entirely — don't leave a command set to `"N/A"`).

#### `.codex/config.toml`

Substitute:
- `{{CODEX_MODEL_DEFAULT}}` — if Q8b set `CODEX_TIER_DO_MODEL`, use that value. If `CODEX_TIER_DO_MODEL` is `null` (user accepted Codex default), use the literal string `"gpt-5.4"` (current documented Codex default).
- `{{CODEX_REASONING_DEFAULT}}` — Q8b answer `CODEX_TIER_DO` (e.g. `"medium"`).
- `{{CODEX_APPROVAL_POLICY}}` — map from Q6 `WORKFLOW_ENFORCEMENT`:
  - `strict` → `"untrusted"`
  - `moderate` → `"on-request"`
  - `light` → `"never"`

### 5.3: Save Baselines

After populating CLAUDE.md and AGENTS.md, save a baseline copy of each to `.devforge/baseline/`:
1. Copy the just-populated `CLAUDE.md` → `.devforge/baseline/CLAUDE.md`
2. Copy the just-populated `AGENTS.md` → `.devforge/baseline/AGENTS.md`

Create `.devforge/baseline/` if it doesn't exist. These baselines are the wizard output before any manual user edits. `update.sh` uses them for three-way merge: old baseline vs new template → diff → apply to user's customized file without losing their edits.

**Note:** `.claude/settings.json` and `.codex/config.toml` are **projectOwned** — update.sh never overwrites them — so they don't need baselines.

### 5.4: Add MCP Servers + Permissions (conditional)

Both `.mcp.json` (Claude) and `.codex/config.toml` (Codex) are already placed with the context7 MCP server. If Q9 selected **runtime-assisted** AC verification for a **web frontend**, add the chrome-devtools server and its permissions across all three runtime config files:

**1. Add to `.mcp.json` (Claude MCP servers):**
```json
"chrome-devtools": {
  "command": "npx",
  "args": ["-y", "@anthropic/chrome-devtools-mcp"]
}
```

**2. Add to `.codex/config.toml` (Codex MCP servers):**
```toml
[mcp_servers.chrome-devtools]
command = "npx"
args = ["-y", "@anthropic/chrome-devtools-mcp"]
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

If Q9 did not select runtime-assisted for a web frontend, skip this entire step.

### 5.5: Populate Project Config

Read `.devforge/project-config.json`. Replace every `null` value with the corresponding answer collected during STEPs 0–4. Use the same values you substituted into the files above. Keys match the placeholder names without `{{ }}`.

New keys this file includes for runtime configs: `CODEX_MODEL_DEFAULT`, `CODEX_REASONING_DEFAULT`, `CODEX_APPROVAL_POLICY`. Use the same substituted values from 5.2.

For values that don't apply to this project, use `"N/A"`. For multi-line values (like `ARCHITECTURE_DETAILS`, `COMMIT_ATTRIBUTION`), use `\n` for newlines in the JSON string.

## STEP 6: Curate & Populate Agents

Install has placed all 16 agent templates for both runtimes (`.claude/agents/` and `.codex/agents/`). Your job: decide which agents this project needs, remove the rest, populate the kept ones.

### 6.1: Select Agents

Based on STEP 3 detection and STEP 4 answers, classify each agent as **keep** or **remove**.

#### Always keep (all project types):
| Agent | Why |
|-------|-----|
| `code-reviewer` | Every project needs code review |
| `qa-engineer` | Every project needs tests |
| `runtime-debugger` | Every project has runtime bugs |
| `tech-writer` | Every project needs documentation |
| `security-reviewer` | Every project needs security review |

#### Keep if relevant (LLM decides based on detection):
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
| `ac-verifier` | `AC_VERIFICATION_MODE` is not `"off"` (Q9) |

**Do not hardcode framework or package names in your selection logic.** Use your knowledge of the detected ecosystem from STEP 3. If STEP 3 found a database driver you don't recognize by name, it's still a database layer — keep `db-engineer`. If it found a framework you've never seen, reason about what layer it serves.

### 6.2: Present Selection & Ask

Present the full list with your recommendation:

> Based on your project, I recommend these agents:
>
> **Keep:**
> - `code-reviewer` — code review (always)
> - `backend-engineer` — [detected: FastAPI service layer]
> - `db-engineer` — [detected: SQLAlchemy + Alembic migrations]
> - ... [list all with brief reason]
>
> **Remove:**
> - `frontend-engineer` — no frontend layer detected
> - `mobile-engineer` — no mobile framework detected
> - `design-auditor` — no styling tooling detected
> - ... [list all with brief reason]
>
> Confirm, or override (move agents between keep/remove)?

The user may:
- Confirm the selection
- Move agents from remove → keep ("actually, keep `api-designer`, we're adding a REST API soon")
- Move agents from keep → remove ("don't need `performance-analyst` for this project")

### 6.3: Remove Rejected Agents

Delete the rejected agent files from both runtime directories:
- `.claude/agents/[name].md`
- `.codex/agents/[name].toml`

### 6.4: Populate Kept Agents

For each kept agent, read the file and substitute all `{{PLACEHOLDER}}` markers:

- `{{FRAMEWORK}}` — Q3 answer: primary framework
- `{{LANGUAGE}}` — Q3 answer: primary language
- `{{ARCHITECTURE}}` — Q4 answer: architecture pattern (or "TBD" if deferred)
- `{{ERROR_HANDLING}}` — Q5 answer: error handling convention (or "TBD" if deferred)
- `{{PROJECT_PATHS}}` — actual source paths from the project (scan SOURCE_ROOT)
- `{{TESTING}}` — detected test framework from STEP 3
- `{{BUILD_TOOL}}` — detected build tool from STEP 3
- `{{STYLING}}` — detected styling approach (only in `frontend-engineer`, `design-auditor`)
- `{{STATE_MANAGEMENT}}` — detected state management (only in `frontend-engineer`, `mobile-engineer`)
- `{{API_LAYER}}` — detected API layer (only in `api-designer`, `architect`, `backend-engineer`)
- `{{TYPE_SAFETY_RULES}}` — generate 3-5 bullet points based on `{{LANGUAGE}}`. Use your knowledge of the language's type system: escape-hatch types to avoid, null/optional safety, unsafe casts, language-specific concerns. If the language is unfamiliar, generate generic rules.
- `{{MODEL_THINK}}` — Q8 answer: model for Think-tier agents (`architect`, `api-designer`, `security-reviewer`)
- `{{MODEL_DO}}` — Q8 answer: model for Do-tier agents (`backend-engineer`, `frontend-engineer`, `mobile-engineer`, `db-engineer`, `devops-engineer`, `migration-engineer`, `runtime-debugger`, `performance-analyst`, `design-auditor`)
- `{{MODEL_VERIFY}}` — Q8 answer: model for Verify-tier agents (`code-reviewer`, `ac-verifier`, `qa-engineer`)

**Preserve ALL template content.** The templates contain carefully designed workflows, steps, and rules. Substitution replaces placeholders — it never removes or condenses sections.

**Add project-specific patterns** discovered during STEP 3 detection (brownfield) or framework best-practice patterns (greenfield). Append these as new subsections — never replace existing template content.

For placeholders that don't apply to a specific agent (e.g., `{{STYLING}}` in a backend-only project that kept `frontend-engineer` by user override), use `"N/A"`.

### 6.5: Save Agent Baselines

For each kept agent, save a baseline copy:
- `.devforge/baseline/agents/[name].md` (Claude version)
- `.devforge/baseline/agents/[name].toml` (Codex version)

Create `.devforge/baseline/agents/` if it doesn't exist. These are the wizard output before manual user edits — `update.sh` uses them for three-way merge.

### 6.6: Update AGENT_LIST

Now that agents are finalized, go back to CLAUDE.md and AGENTS.md and replace the `{{AGENT_LIST}}` placeholder (which was set to "No agents installed" in STEP 5) with the actual list of kept agents. Format:

```markdown
- `architect` — Design decisions, architecture planning (Think tier)
- `backend-engineer` — Backend implementation (Do tier)
- `code-reviewer` — Code review (Verify tier)
- ...
```

## STEP 7: Summary

Present a summary:

```
## Setup Complete

### Populated Files:
- CLAUDE.md — Project instructions for Claude Code
- AGENTS.md — Project instructions for Codex CLI
- .devforge/project-config.json — Answers record

### Project:
- Description: [PROJECT_DESCRIPTION]
- Type: [PROJECT_TYPE]
- Framework: [FRAMEWORK]
- Language: [LANGUAGE]

### Workspace Mode:
- Mode: [standalone / wrapper]
- Source Root: [SOURCE_ROOT]

### Next Steps:
1. Review CLAUDE.md and AGENTS.md — adjust if needed
2. Start working with {{cli.sigil}}specify "your first feature"
```

## IMPORTANT RULES

1. **Never guess** — if you can't detect something, ask
2. **STEP 5 never creates files** — all files are already placed; STEP 5 only populates. STEP 6 creates files explicitly when generation is added.
3. **Use real paths** — all paths must point to actual directories in the project
4. **Use real commands** — all commands must come from the project's actual scripts
5. **Validate after population** — read back each file to verify no unresolved `{{PLACEHOLDER}}` markers remain
6. **Wrapper isolation** — in wrapper mode, never create any artifact inside SOURCE_ROOT
7. **Same values in both files** — CLAUDE.md and AGENTS.md get identical substitutions; `.devforge/project-config.json` gets the same values as JSON
