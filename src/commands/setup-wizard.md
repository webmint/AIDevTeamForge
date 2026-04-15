# {{cli.sigil}}setup-wizard — Project Initialization Wizard

You are running the initial setup wizard for AIDevTeamForge. Your job is:

1. Analyze the current project.
2. Ask the user targeted questions via confirm / override / defer.
3. Substitute the user's answers into the `{{PLACEHOLDER}}` markers in every target file that has them. `install.sh` has already placed all files — **you do NOT create new files**.
4. Where specific files have designated project-specific sections (e.g., CLAUDE.md / AGENTS.md architecture notes, agent files with project paths, constitution custom clauses), append content derived from detection + user answers to those sections only. **Never rewrite whole files.**
5. Write the answers record to `target/.devforge/project-config.json` (which `install.sh` placed as an empty scaffold with all keys set to `null`) so later commands and `update.sh` can consume user decisions.

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
- Wrapper workspace (if chosen, follow up with: "Which folder contains the client's source code?")
{{/ask}}

**If multiple nested `.git` directories are found:**

{{ask "I found multiple nested git repositories: [list]. Is this a wrapper workspace? If so, which folder is the primary source root?"}}
- Standalone
- Wrapper around one of the listed folders (have the user pick)
{{/ask}}

### 0.3: Set Source Root

Store the result for use in all subsequent steps:
- **Standalone**: `SOURCE_ROOT = "."`
- **Wrapper**: `SOURCE_ROOT = "[folder-name]"` (e.g., `client-project`)

Track `SOURCE_ROOT` in your working context throughout the rest of the wizard; at the end it's persisted to `target/.devforge/project-config.json` along with all other collected answers.

If wrapper mode:
- Inform the user: "Wrapper mode activated. Source root: `[folder-name]/`. All template artifacts will live in the wrapper root. I'll scan the source code inside `[folder-name]/`."
- Verify the inner folder exists and contains files

## STEP 0.5: Greenfield Detection

Look at what's inside SOURCE_ROOT. Skip `.git/`, hidden directories, and any obvious dependency or build-artifact directory — use your knowledge of the ecosystem (e.g. `node_modules/`, `vendor/`, `target/`, `venv/`, `.venv/`, `__pycache__/`, `build/`, `dist/`, `out/`, `.gradle/`, `.next/`, `.nuxt/`, `.cache/`). Decide which of these three states best describes the project:

- **Empty** — essentially nothing there (fresh `mkdir` then install). No manifests, no source, no config.
- **Greenfield** — just a fresh scaffold from a starter tool (e.g. output of `npm create vite`, `cargo new`, `flutter create`, `django-admin startproject`, or similar for any ecosystem). Files present are template boilerplate, not meaningful custom code.
- **Existing** — real in-progress project with custom code and conventions.

Use your judgment on the greenfield-vs-existing boundary. If genuinely unsure, mark as uncertain and raise it with the user in STEP 2.

**If empty or greenfield:**
- Skip pattern detection that requires real code to scan (architecture, error handling, state management, etc.) — there isn't any.
- Inspect whatever scaffold / config files ARE present (e.g. `package.json`, `Cargo.toml`, `tsconfig.json`, `pyproject.toml`) to extract language, framework, and tooling hints.
- In STEP 2, ask MORE questions since there's less to auto-detect.
- In STEP 3, use framework best-practice defaults instead of extracted patterns.
- When generating the project instructions file, use the constitution's scaffolding section for project structure.
- When generating agents, use framework-idiomatic patterns instead of project-specific ones.

Inform the user briefly: "This appears to be an [empty / greenfield / existing] project. I'll [ask you about your intended stack / analyze your existing codebase] to set things up."

## STEP 1: Auto-Detect Project Structure

**All scanning in this step targets the SOURCE_ROOT directory.** For standalone projects this is the workspace root (`.`). For wrapper projects this is the inner folder (e.g., `client-project/`). Resolve all file paths relative to SOURCE_ROOT.

Read dependency manifests, lockfiles, config files, and top-level directory layout at SOURCE_ROOT to identify the project's tech stack. Typical starting points: dependency manifests like `package.json`, `pyproject.toml`, `requirements.txt`, `Pipfile`, `go.mod`, `Cargo.toml`, `pubspec.yaml`, `Gemfile`, `composer.json`, `*.csproj`, `mix.exs`, `deno.json`; config files like `tsconfig.json`, `.eslintrc.*`, `tailwind.config.*`, `pyrightconfig.json`; and structural markers like `Dockerfile`, `.github/workflows/`, workspace/monorepo files (`pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`, Cargo workspace, Go workspaces).

For existing projects, also scan a few representative source files to infer architectural patterns (layered / feature-modular / MVC / BLoC / hexagonal / etc.) and error-handling conventions (Either-style results / typed exceptions / traditional try-catch / HTTP-error patterns / etc.).

Based on what you find, identify each of the following. Mark any category that genuinely doesn't apply as **N/A**. If you're uncertain, note the uncertainty and raise it with the user in STEP 2 rather than guessing.

- **Primary language(s)** and **runtime**
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

## STEP 2: Present Findings & Ask Questions

Present what you detected in a clear summary, then walk the user through each question. Every question is labeled with exactly one of three markers:

- **REQUIRED** — must be answered. Offer **confirm / override**. Defer is not allowed; downstream commands depend on the value.
- **OPTIONAL** — user may answer or explicitly defer. Offer **confirm / override / defer**. "Defer" marks the field as `TBD` and downstream commands will ask when the field becomes relevant (e.g., when `{{cli.sigil}}specify` needs an architecture decision for a specific feature). A small number of OPTIONAL questions are free-text only (e.g. "anything else I should know?") — those are noted explicitly and allow an empty response.
- **CONDITIONAL** — may not apply to this project. If it doesn't apply, skip it and record the natural default (this is the one case where a silent default is permitted; the marker acknowledges it). If it does apply, treat as REQUIRED (confirm / override — no silent guess).

For every question that applies, do NOT silently default. Do NOT infer answers. The user's confirmed answers are the canonical input across all runtimes — that's what keeps outputs consistent between Claude, Codex, and any future runtime.

**Anti-hallucination rule for findings.** When presenting findings to the user (anywhere you'd fill `[findings]`, `[observed indicators]`, `[pattern indicators]`, `[detected framework]`, etc.), quote ONLY concrete observed facts: exact file paths, exact package names, exact config keys, exact imports or symbols you actually read. Do NOT invent indicators to make the prose flow. If detection surfaced nothing for a category, say so plainly (e.g. "I found no framework dependencies, so I can't infer the stack — could you tell me what you're using?") instead of fabricating plausibles.

**Where answers are stored.** As you walk through the questions below, track the user's answers in your working context. At the end of the wizard, every collected answer is written to `target/.devforge/project-config.json` (which `install.sh` has already placed as an empty scaffold with all keys set to `null`). That file is the canonical record — every command under every CLI (Claude, Codex, and later runtimes), plus `update.sh`, reads from it. Use the variable names noted in each question (e.g. `SOURCE_ROOT`, `PROJECT_NAME`, `CLAUDE_MODEL_THINK`) as the keys.

### Question 1: Project Type (REQUIRED)

Present the question to the user. If STEP 1 detection surfaced concrete indicators, quote them explicitly; if nothing was detected, say so plainly and just ask. Do not invent.

**If concrete indicators were found:**

> Based on what I found — [quote 2–5 specific observed facts: exact dep names, exact file paths, exact config markers] — this looks like a [proposed type]. What type of project is this?
>
> Options:
> - Frontend application
> - Backend API/service
> - Full-stack application
> - Library / package
> - CLI tool
> - Mobile application
> - Plugin / extension
> - Other (user describes)

**If nothing was detected (empty / greenfield / unclear):**

> I couldn't detect enough from the files alone to guess. What type of project is this?
>
> Options: [same list as above]

### Question 2: Primary Framework & Language (REQUIRED)

> I found [detected framework] with [detected language]. Confirm, override, or describe if different.

Accept free-text for override — no hardcoded framework list.

### Question 3: Architecture Pattern (OPTIONAL)

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

### Question 4: Error Handling Convention (OPTIONAL)

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

### Question 5: Workflow Enforcement Level (REQUIRED)

This controls how many user-approval gates appear in the workflow and how strict post-edit verification is. The underlying verification mechanism varies per runtime — on some runtimes it's automatic after every edit, on others it's an explicit `{{cli.sigil}}verify` step — but the behaviors below are the same regardless.

> How strict should workflow enforcement be?
>
> Options:
> - **Strict** — user approval required at every phase gate (specify → plan → breakdown → execute → verify). Verification runs after every code-writing step.
> - **Moderate** — user approval at spec and task-breakdown gates only. Verification runs after every code-writing step, but running `{{cli.sigil}}verify` explicitly is optional.
> - **Light** — user approval at the initial spec only. Verification runs, but fewer interactive gates.

Recommend Strict for new users. This field is required because it directly shapes downstream command behavior.

### Question 6: Additional Context (OPTIONAL)

> Anything else I should know about this project? (team conventions, external services, special patterns, deployment targets)

Free text. User can skip.

### Question 7: AI Attribution in Commits (REQUIRED)

> Should commits created by the AI assistant include co-author attribution?
>
> Options:
> - No — commits will have no AI attribution (recommended default)
> - Yes — commits will include the trailer: `{{cli.attribution}}`

### Question 8: Agent Model Assignments (per-runtime)

Specialized agents are grouped into three tiers based on the reasoning they require. Ask the sub-question for each supported runtime (since install produces artifacts for every enabled runtime, all sub-questions are asked by default). Use **confirm / override / defer** semantics from the STEP 2 preamble — don't silently default.

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

Branch by the project type confirmed in Q1 (not what STEP 1 detected — Q1's answer is canonical). If Q1's answer was "Other" or ambiguous, ask the user for a specific category; if still unclear, fall back to **Code-only**.

**Web frontend:**

> What URL does the dev server serve the app on? (e.g. http://localhost:5173)

Store the URL as `AC_RUNTIME_URL`. Also flag for STEP 3: the target needs a browser-automation MCP server (e.g. `chrome-devtools` for Claude, the equivalent for Codex) registered in the runtime's MCP config.

**Backend with HTTP API:**

> What base URL should `{{cli.sigil}}verify` use for API endpoints? (e.g. http://localhost:3000, http://localhost:8000)

Store as `AC_RUNTIME_API_BASE`.

**CLI tool:**

> What command launches the built tool? (e.g. `./target/release/myapp`, `python -m mypackage`, `node dist/cli.js`, `go run ./cmd/myapp`)

Store as `AC_RUNTIME_CLI_COMMAND`.

**Mobile / desktop / game / other non-automatable:**

> Runtime-assisted verification for this project type is largely manual — `{{cli.sigil}}verify` will describe what to check, but the user will run the checks themselves. Confirm Runtime-assisted mode, or switch to Code-only / Tests.

No follow-up storage needed beyond `AC_VERIFICATION_MODE` in this case.

## STEP 3: Generate Configuration Files

Based on detection + user answers, generate ALL of the following files. Read each template from `.claude/templates/`, fill in the placeholders, and write the output files.

### 3.1: Generate CLAUDE.md

Read `.claude/templates/CLAUDE.template.md` and generate `CLAUDE.md` at project root.

Replace ALL placeholders:
- `{{PROJECT_NAME}}` — project name from package.json or user input
- `{{PROJECT_TYPE}}` — frontend/backend/fullstack/library
- `{{FRAMEWORK}}` — primary framework
- `{{LANGUAGE}}` — primary language
- `{{BUILD_TOOL}}` — build tool
- `{{BUILD_COMMAND}}` — actual build command. Detection: (1) `scripts.build` in package.json → `npm run build` / `yarn build` / `pnpm build` depending on lockfile, (2) `scripts["build:prod"]` → same pattern, (3) Makefile `build` target → `make build`, (4) Go project → `go build ./...`, (5) Rust project → `cargo build`, (6) None found → `N/A`. For wrapper mode, prefix with `cd SOURCE_ROOT &&`
- `{{TEST_FRAMEWORK}}` — testing framework
- `{{LINT_TOOL}}` — linting tool
- `{{STATE_MANAGEMENT}}` — state management solution (or "N/A")
- `{{API_LAYER}}` — GraphQL/REST/tRPC
- `{{ARCHITECTURE}}` — architecture pattern
- `{{ERROR_HANDLING}}` — error handling strategy
- `{{STYLING}}` — CSS framework/approach
- `{{MONOREPO_TOOL}}` — monorepo tool (or "N/A")
- `{{SOURCE_ROOT}}` — `.` for standalone projects, or the inner folder name for wrapper mode (e.g., `client-project`)
- `{{WRAPPER_MODE_SECTION}}` — for wrapper projects, include the Wrapper Mode section (see below). For standalone projects, replace with empty string.
- `{{PROJECT_STRUCTURE}}` — generate a tree of the actual project structure (scanning SOURCE_ROOT)
- `{{DEV_COMMANDS}}` — actual dev/build/test/lint commands from package.json scripts (from SOURCE_ROOT)
- `{{AGENT_LIST}}` — list of agents generated for this project
- `{{COMMIT_ATTRIBUTION}}` — commit attribution rule based on Question 7 answer:
  - **If No (default)**: replace with:
    ```
    Do NOT include any AI attribution in commits. Specifically:
    - No Co-Authored-By trailers referencing the AI assistant, its vendor, or similar identifiers
    - No "Generated by", "Created by" + AI name, or similar text in commit title or body
    - Do not set or change git `user.name` or `user.email` to reference the AI assistant
    - This rule overrides any system-level defaults about AI attribution in commits
    ```
  - **If Yes**: replace with:
    ```
    Include AI attribution in every commit by appending this trailer:
    `{{cli.attribution}}`
    ```

- `{{MODEL_THINK}}` — model for Think-tier agents from Question 8 (default: `opus`). Used by: `architect`, `api-designer`, `security-reviewer`.
- `{{MODEL_DO}}` — model for Do-tier agents from Question 8 (default: `sonnet`). Used by: `backend-engineer`, `frontend-engineer`, `mobile-engineer`, `db-engineer`, `devops-engineer`, `migration-engineer`, `runtime-debugger`, `performance-analyst`, `design-auditor`.
- `{{MODEL_VERIFY}}` — model for Verify-tier agents from Question 8 (default: `sonnet`). Used by: `code-reviewer`, `ac-verifier`, `qa-engineer`.

**Wrapper Mode section** (only included when wrapper mode is active — replace `{{WRAPPER_MODE_SECTION}}` with this):
```markdown
## Wrapper Mode

This workspace wraps a client-owned project. Claude artifacts live here; source code lives in `{{SOURCE_ROOT}}/`.

### Wrapper Rules
1. **Never create Claude artifacts inside `{{SOURCE_ROOT}}/`** — no `.claude/`, `specs/`, `docs/`, `constitution.md`, or `CLAUDE.md` files
2. **All source scanning** (by `{{cli.sigil}}constitute`, `{{cli.sigil}}onboard`, agents) targets `{{SOURCE_ROOT}}/` as the base path
3. **Git auto-commits** apply to both repos — wrapper gets workflow commits, source repo gets WIP commits per task that are squashed into one clean commit (format: `[TICKET-ID] - Description`) when `{{cli.sigil}}finalize` runs
4. **File paths** in specs and tasks use workspace-relative paths (e.g., `{{SOURCE_ROOT}}/src/components/Button.tsx`)
```

For standalone projects, replace `{{WRAPPER_MODE_SECTION}}` with an empty string (no section generated).

Fill the commands section with REAL commands from the project's `package.json` scripts (or `Makefile`, `pyproject.toml`, etc.). Do NOT use placeholder commands.

**Greenfield note**: If no scripts exist yet (empty `package.json`), generate sensible defaults based on the chosen framework and build tool (e.g., `vite dev`, `vitest`, `eslint .`). Mark them with a comment: `<!-- default, update after scaffolding -->`.

### 3.1.1: Save CLAUDE.md Baseline

After generating `CLAUDE.md`, save a baseline for three-way merge support in `update.sh`:
1. Read `.claude/templates/CLAUDE.template.md`
2. Substitute all `{{PLACEHOLDER}}` variables (same values used in 3.1)
3. Save the result to `.claude/.baseline/CLAUDE.md`

Create the `.claude/.baseline/` directory if it doesn't exist. The baseline is the template with placeholders resolved but **without** any project-specific custom sections — it represents what the template alone produces.

### 3.2: Generate Agents

Read agent templates from `.claude/templates/agents/` and generate `.claude/agents/`.

**Decide which agents to create based on project type and detected stack:**

#### Always included (all project types):
| Agent | Why |
|-------|-----|
| `code-reviewer` | Every project needs code review |
| `qa-engineer` | Every project needs tests |
| `runtime-debugger` | Every project has runtime bugs |
| `tech-writer` | Every project needs documentation |
| `security-reviewer` | Every project needs security review — not just auth projects |

#### By project type:
| Condition | Agents |
|-----------|--------|
| Frontend detected (web — has `react-dom`, `vue`, `svelte`, `angular`, etc.) | `frontend-engineer` |
| Mobile-only detected (`react-native` without `react-dom`) | `mobile-engineer` (instead of `frontend-engineer`) |
| Backend framework detected (Express, NestJS, FastAPI, etc.) | `backend-engineer` |
| Core/library without backend framework | `architect` (instead of backend-engineer) |
| Both frontend + backend | `frontend-engineer` + `backend-engineer` + `architect` |
| Library/package | `architect` |

#### By detected stack (conditional):
| Condition | Agent |
|-----------|-------|
| Database detected (prisma, typeorm, sequelize, mongoose, knex, drizzle, SQLAlchemy, etc.) | `db-engineer` |
| Docker/CI detected (Dockerfile, .github/workflows/, .gitlab-ci.yml) | `devops-engineer` |
| Frontend project with styling framework | `design-auditor` |
| API project (REST or GraphQL) | `api-designer` |
| Frontend or API project | `performance-analyst` |
| Existing codebase with deprecated code or migration keywords in recent commits | `migration-engineer` |
| Mobile framework detected (React Native, Expo, Flutter, Swift/Xcode, Kotlin/Android) | `mobile-engineer` |
| AC_VERIFICATION != "off" (Question 9) | `ac-verifier` |

For each agent:
- **Preserve ALL template content** — do NOT condense, simplify, or remove sections from the template. The templates contain carefully designed workflows, steps, and rules that must survive into the generated agent files intact
- Replace `{{FRAMEWORK}}` with actual framework
- Replace `{{LANGUAGE}}` with actual language
- Replace `{{ARCHITECTURE}}` with actual architecture pattern
- Replace `{{ERROR_HANDLING}}` with actual error handling pattern
- Replace `{{PROJECT_PATHS}}` with actual source paths from the project
- Replace `{{TESTING}}` with actual test framework
- Replace `{{LINT_CONFIG}}` with actual linting setup
- Replace `{{STYLING}}` with actual CSS approach
- Replace `{{TYPE_SAFETY_RULES}}` with language-appropriate type safety rules. Generate 3-5 bullet points covering: escape-hatch types to avoid, null/optional safety patterns, unsafe cast/assertion patterns, and any language-specific type concerns. Base these on `{{LANGUAGE}}` — use your knowledge of the language's type system. Example for TypeScript: "No `any` types without justification, use optional chaining for nullable access, no unsafe type assertions." Example for Dart: "No `dynamic` without justification, proper null safety with `late`/`required`, avoid `as` casts." For unfamiliar languages, generate generic rules: "Avoid escape-hatch types, handle nullable values explicitly, no unsafe type casts."
- Add project-specific patterns you discovered during detection (existing projects) or framework best-practice patterns (greenfield) — add these as NEW sections or append to existing sections, never replace template content
- Replace `{{MODEL_THINK}}`, `{{MODEL_DO}}`, or `{{MODEL_VERIFY}}` with the model chosen for each tier in Question 8 (defaults: opus/sonnet/sonnet). Each template uses the placeholder for its tier.
- **Greenfield**: Use framework-idiomatic examples in agents since there's no project code to reference yet

**CRITICAL**: The generated agent file = full template content + placeholder replacements + project-specific additions. Never subtract from the template.

### 3.2.1: Save Agent Baselines

After generating all agents, save a **baseline** for each — the template with placeholders substituted but **without** project-specific additions. These baselines enable `update.sh` to three-way merge on the next update (applying only template diffs while preserving project customizations).

For each generated agent:
1. Read the original template from `.claude/templates/agents/[name].template.md`
2. Substitute all `{{PLACEHOLDER}}` variables (same values used in 3.2)
3. Save the result to `.claude/agents/.baseline/[name].md`

Create the `.claude/agents/.baseline/` directory if it doesn't exist.

### 3.3: Generate settings.json

Read `.claude/templates/settings.template.json` and generate `.claude/settings.json`.

Configure PostToolUse hooks based on detected tooling:
- TypeScript project → `tsc --noEmit --pretty 2>&1 | head -20`
- Python project → `python -m py_compile` or `mypy --no-error-summary`
- Go project → `go vet ./...`
- Rust project → `cargo check 2>&1 | head -20`

Adjust the `cd` path in the hook to the actual project directory where the type checker should run. For monorepos, point to the root or the appropriate package.

**Wrapper mode**: Prefix the type-check command with `cd SOURCE_ROOT &&` so the type checker runs in the correct directory. For example: `cd client-project && tsc --noEmit --pretty 2>&1 | head -20`.

### 3.4: Generate Memory

Read `.claude/templates/memory.template.md` and generate `.claude/memory/MEMORY.md`.

Pre-populate with:
- Project structure summary
- Key file paths
- Architecture pattern notes
- Any patterns you discovered during detection

Replace `{{WORKSPACE_MODE}}` with `standalone` or `wrapper`, and `{{SOURCE_ROOT}}` with `.` or the inner folder name.

### 3.5: Create constitution.md stub

Read `.claude/templates/constitution.template.md` and copy it to `constitution.md` at project root. Replace header placeholders (`{{PROJECT_NAME}}`, `{{DATE}}`, `{{PROJECT_TYPE}}`, `{{FRAMEWORK}}`, `{{LANGUAGE}}`, `{{ERROR_HANDLING}}`, `{{TESTING}}`) with actual values from detection and user answers. Leave all `_Run {{cli.sigil}}constitute to populate_` sections and all `[universal]` sections intact — these are the sentinel strings that other commands check to verify the constitution has been populated.

### 3.6: Create docs/ folder

Create the documentation directory structure:
```
docs/
  overview.md              # Stub with project name and "TODO: populate after {{cli.sigil}}constitute"
  architecture.md          # Stub with "TODO: populate after {{cli.sigil}}constitute"
  features/                # Empty directory (created with .gitkeep)
  api/                     # Empty directory (created with .gitkeep) — only if API project
  guides/                  # Empty directory (created with .gitkeep)
```

For **existing projects**: If a `docs/` directory already exists, do NOT overwrite it. Warn the user and skip this step.

For **greenfield projects**: Create the stubs. The tech-writer agent will populate them as features are built.

### 3.7: Wrapper Mode Setup (wrapper only)

If wrapper mode is active, perform these additional steps:

1. **Add inner folder to .gitignore**: Append `[SOURCE_ROOT]/` to the wrapper's `.gitignore` file (create `.gitignore` if it doesn't exist). This prevents the wrapper repo from tracking the inner project's files.
   ```
   # Inner project (separate git repo)
   [SOURCE_ROOT]/
   ```

2. **Check for inner project's .claude/**: If the inner project already has a `.claude/` directory, warn the user: "The inner project at `[SOURCE_ROOT]/` already has its own `.claude/` directory. This wrapper's `.claude/` will take precedence for Claude Code running in the wrapper root."

### 3.8: Write Project Config

Write `.claude/project-config.json` containing **all** template variable values used during generation. This file is read by `update.sh` to apply placeholder substitution when updating agents and CLAUDE.md in future template updates.

The keys must be the exact placeholder names (without `{{ }}`). Example:

```json
{
  "PROJECT_NAME": "My App",
  "PROJECT_TYPE": "fullstack",
  "FRAMEWORK": "Next.js",
  "LANGUAGE": "TypeScript",
  "BUILD_TOOL": "next",
  "BUILD_COMMAND": "npm run build",
  "TYPE_CHECK_COMMAND": "tsc --noEmit --pretty 2>&1 | head -20",
  "LINT_COMMAND": "npx eslint --no-error-on-unmatched-pattern",
  "SOURCE_ROOT": ".",
  "PROJECT_MODE": "greenfield",
  "ARCHITECTURE": "Feature-based/Modular",
  "ERROR_HANDLING": "Try/catch with custom error types",
  "API_LAYER": "REST",
  "STATE_MANAGEMENT": "Zustand",
  "STYLING": "Tailwind CSS",
  "MONOREPO_TOOL": "N/A",
  "TESTING": "Vitest",
  "PROJECT_PATHS": "- Source: `src/`\n- Components: `src/components/`\n- ...",
  "PROJECT_STRUCTURE": "src/\n  components/\n  pages/\n  ...",
  "DEV_COMMANDS": "- `npm run dev` — Start dev server\n- `npm run build` — Production build\n- ...",
  "AGENT_LIST": "- `code-reviewer` — Code review\n- `qa-engineer` — Testing\n- ...",
  "WRAPPER_MODE_SECTION": "",
  "COMMIT_ATTRIBUTION": "Do NOT include any AI attribution in commits. Specifically:\n- No Co-Authored-By trailers referencing the AI assistant, its vendor, or similar identifiers\n- No \"Generated by\", \"Created by\" + AI name, or similar text in commit title or body\n- Do not set or change git `user.name` or `user.email` to reference the AI assistant\n- This rule overrides any system-level defaults about AI attribution in commits",
  "MODEL_THINK": "opus",
  "MODEL_DO": "sonnet",
  "MODEL_VERIFY": "sonnet",
  "AC_VERIFICATION": "auto",
  "AC_VERIFICATION_URL": "http://localhost:5173",
  "AC_VERIFICATION_API_BASE": "",
  "DEFAULT_BRANCH": "main",
  "TYPE_SAFETY_RULES": "- No `any` types without documented justification\n- Null/undefined properly handled (optional chaining, null checks)\n- Generic types used correctly\n- No unsafe type assertions"
}
```

**Detecting DEFAULT_BRANCH**: Use this cascade during Step 1:
1. `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null` → parse branch name
2. Check if `main` exists: `git show-ref --verify --quiet refs/heads/main`
3. Check if `master` exists: `git show-ref --verify --quiet refs/heads/master`
4. Check if `develop` exists: `git show-ref --verify --quiet refs/heads/develop`
5. If none found, default to `main`

**Required keys**: `PROJECT_NAME`, `PROJECT_TYPE`, `FRAMEWORK`, `LANGUAGE`, `BUILD_TOOL`, `BUILD_COMMAND`, `TYPE_CHECK_COMMAND`, `LINT_COMMAND`, `SOURCE_ROOT`, `PROJECT_MODE`, `ARCHITECTURE`, `ERROR_HANDLING`, `API_LAYER`, `STATE_MANAGEMENT`, `STYLING`, `MONOREPO_TOOL`, `TESTING`, `PROJECT_PATHS`, `PROJECT_STRUCTURE`, `DEV_COMMANDS`, `AGENT_LIST`, `WRAPPER_MODE_SECTION`, `COMMIT_ATTRIBUTION`, `MODEL_THINK`, `MODEL_DO`, `MODEL_VERIFY`, `AC_VERIFICATION`, `AC_VERIFICATION_URL`, `AC_VERIFICATION_API_BASE`, `DEFAULT_BRANCH`, `TYPE_SAFETY_RULES`.

Use the exact same values you substituted into the templates. For multi-line values, use `\n` for newlines in the JSON string. For values that don't apply, use `"N/A"` (not empty string).

## STEP 4: Cleanup & Summary

1. Ask the user: "Setup is complete. Should I remove the `.claude/templates/` directory? (It's no longer needed but can be kept for re-running the wizard.)"
2. If yes, delete `.claude/templates/`
3. Present a summary:

```
## Setup Complete

### Generated Files:
- CLAUDE.md — Project configuration and workflow
- .claude/settings.json — Hooks and plugins
- .claude/agents/[list agents].md — Specialized agents
- .claude/memory/MEMORY.md — Persistent memory (pre-seeded)
- constitution.md — Constitution stub (run {{cli.sigil}}constitute to populate)
- specs/ — Feature specifications directory
- docs/ — Project documentation directory

### Detected Stack:
- Type: [type]
- Framework: [framework]
- Language: [language]
- Testing: [test framework]
- Linting: [lint tool]
- Architecture: [pattern]

### Workspace Mode:
- Mode: [standalone / wrapper]
- Source Root: [. / folder-name]
[Wrapper only]:
- Inner project added to .gitignore
- Git auto-commits apply to wrapper repo only
- Source code in inner repo is committed manually by the developer

### Next Steps:
1. Review the generated files and adjust if needed
2. Run {{cli.sigil}}constitute to generate your project's constitution
3. [Existing projects only] Run {{cli.sigil}}onboard to generate comprehensive codebase documentation
4. Start working with {{cli.sigil}}specify "your first feature"
```

4. **Write setup completion marker**: After presenting the summary, write `.claude/setup-complete` with content:
   ```
   Setup completed: [current date and time]
   Generated files: CLAUDE.md, .claude/settings.json, agents, memory, constitution.md stub, specs/, docs/
   ```
   This marker allows other commands to detect whether setup-wizard ran to completion. If the file is missing, setup may have been interrupted mid-generation.

## IMPORTANT RULES

1. **Never guess** — if you can't detect something, ask
2. **Use real paths** — all generated paths must point to actual directories in the project
3. **Use real commands** — all generated commands must come from the project's actual scripts
4. **Preserve existing files** — if `CLAUDE.md` or `.claude/settings.json` already exists, warn the user and ask before overwriting
5. **Validate after generation** — read back each generated file to verify it has no unresolved `{{PLACEHOLDER}}` variables
6. **Wrapper isolation** — in wrapper mode, never create any Claude artifact (`.claude/`, `specs/`, `docs/`, `constitution.md`, `CLAUDE.md`) inside SOURCE_ROOT. All Claude artifacts belong in the wrapper root.
