# /setup-wizard — Project Initialization Wizard

You are running the initial setup wizard for AIDevTeamForge. Your job is to analyze the current project, ask the user targeted questions, and generate all configuration files.

## STEP 0: Workspace Mode Detection

Before scanning source code, determine whether this is a standalone project or a wrapper workspace.

### 0.1: Auto-Detect Nested Git Repos

Scan for directories at depth 1 (direct children of the workspace root) that contain a `.git/` directory. Exclude `node_modules`, `.git`, and hidden directories (directories starting with `.`).

### 0.2: Present Finding & Ask

**If exactly one nested `.git` directory is found** (e.g., `client-project/.git`):
Use AskUserQuestion: "I found a nested git repository at `[folder-name]/`. Is this a wrapper workspace where Claude artifacts live here and the actual source code lives in that subfolder?"
- Yes, this is a wrapper around `[folder-name]`
- No, this is a standalone project

**If zero nested `.git` directories are found:**
Use AskUserQuestion: "Is this a standalone project, or a wrapper workspace around a client project folder?"
- Standalone project (default)
- Wrapper workspace (then ask: "Which folder contains the client's source code?")

**If multiple nested `.git` directories are found:**
Use AskUserQuestion: "I found multiple nested git repositories: [list]. Is this a wrapper workspace? If so, which folder is the primary source root?"
- Standalone (default)
- Wrapper around [user picks one]

### 0.3: Set Source Root

Store the result for use in all subsequent steps:
- **Standalone**: `SOURCE_ROOT = "."`
- **Wrapper**: `SOURCE_ROOT = "[folder-name]"` (e.g., `client-project`)

If wrapper mode:
- Inform the user: "Wrapper mode activated. Source root: `[folder-name]/`. All Claude artifacts will live in the wrapper root. I'll scan the source code inside `[folder-name]/`."
- Verify the inner folder exists and contains files

## STEP 0.5: Greenfield Detection

Check if the project is new/empty. **When scanning source files, use the SOURCE_ROOT path** (`.` for standalone, `[folder-name]/` for wrapper).

1. Count source files inside SOURCE_ROOT (exclude `node_modules`, `.git`, `dist`, `build`, config files at root)
2. If **0-5 source files** (or only scaffold boilerplate from `create-vite`, `create-next-app`, `npm init`, etc.), this is a **GREENFIELD PROJECT**
3. If **6+ meaningful source files**, this is an **EXISTING PROJECT**

**If greenfield:**
- Skip auto-detection of architecture patterns, error handling patterns, and state management (there's no code to scan)
- Still check for `package.json`, `tsconfig.json`, and config files (these exist even in scaffolds)
- In Step 2, ask MORE questions since there's less to auto-detect
- In Step 3, use framework best practices for defaults instead of extracted patterns
- When generating CLAUDE.md, use the constitution's scaffolding section for project structure
- When generating agents, use framework-idiomatic patterns instead of project-specific ones

Inform the user: "This appears to be a [new/existing] project. I'll [ask you about your intended stack / analyze your existing codebase] to set things up."

## STEP 1: Auto-Detect Project Structure

**All scanning in this step targets the SOURCE_ROOT directory.** For standalone projects this is the workspace root (`.`). For wrapper projects this is the inner folder (e.g., `client-project/`). Resolve all file paths (`package.json`, `tsconfig.json`, etc.) relative to SOURCE_ROOT.

Silently scan the project to detect as much as possible before asking questions. For greenfield projects, only scan config files. For existing projects, scan everything. Look for:

**Package managers & monorepo:**
- `package.json` → npm/yarn/pnpm, check `workspaces` field
- `pnpm-workspace.yaml` → pnpm workspaces
- `turbo.json` → Turborepo
- `nx.json` → Nx
- `lerna.json` → Lerna

**Frameworks:**
- `vue` or `nuxt` in dependencies → Vue/Nuxt
- `react` or `next` in dependencies → React/Next.js
- `svelte` or `@sveltejs/kit` in dependencies → Svelte/SvelteKit
- `angular` in dependencies → Angular
- `astro` in dependencies → Astro
- `@remix-run/react` in dependencies → Remix
- `express` or `fastify` or `koa` or `hono` in dependencies → Node.js backend
- `nestjs` in dependencies → NestJS
- `django` or `flask` in `requirements.txt` / `pyproject.toml` → Python backend

**Mobile frameworks:**
- `react-native` in dependencies → React Native
- `expo` in dependencies → Expo (React Native)
- `flutter` in `pubspec.yaml` → Flutter
- `.xcodeproj` or `.xcworkspace` presence → iOS native (Swift)
- `build.gradle.kts` with `com.android.application` plugin → Android native (Kotlin)
- `ios/` + `android/` directories → cross-platform mobile

**TypeScript:**
- `tsconfig.json` presence and `strict` setting
- Check if `strict: true` or individual strict flags

**Testing:**
- `vitest` in dependencies → Vitest
- `jest` in dependencies → Jest
- `playwright` or `@playwright/test` → Playwright
- `cypress` → Cypress
- `pytest` in requirements → Pytest

**Linting:**
- `.eslintrc.*` or `eslint.config.*` → ESLint (note config style: flat vs legacy)
- `prettier` in dependencies → Prettier
- `.pylintrc` or `ruff.toml` → Python linting

**Styling:**
- `tailwindcss` in dependencies → Tailwind
- `sass` or `scss` in dependencies → SCSS
- `styled-components` or `@emotion` → CSS-in-JS

**State management:**
- `pinia` → Pinia
- `redux` or `@reduxjs/toolkit` → Redux
- `zustand` → Zustand
- `vuex` → Vuex (legacy)

**API layer:**
- `@apollo/client` or `graphql` → GraphQL
- `axios` or `@tanstack/react-query` → REST
- `trpc` → tRPC

**Build tools:**
- `vite` → Vite
- `webpack` → Webpack
- `esbuild` → esbuild
- `turbopack` → Turbopack

**Architecture patterns** (scan source code structure):
- `src/domain/`, `src/data/`, `src/presentation/` → Clean Architecture
- `src/bloc/` or `BLoC` in filenames → BLoC pattern
- `src/controllers/`, `src/models/`, `src/views/` → MVC
- `src/modules/` with self-contained folders → Modular/Feature-based
- `src/stores/` → Store-based state management
- `src/screens/` or `src/navigation/` → Mobile screen-based architecture

**Error handling patterns** (scan a few source files):
- `Either`, `Left`, `Right` imports → Either/Result pattern (purify-ts, fp-ts, neverthrow)
- Mostly `try/catch` → Traditional error handling

**Runtimes:**
- `deno.json` or `deno.jsonc` → Deno
- `bun.lockb` or `bunfig.toml` → Bun

**Other:**
- `Dockerfile` → Docker
- `.github/workflows/` → GitHub Actions CI/CD
- `Makefile` → Make-based build
- Python `pyproject.toml` / `setup.py` → Python project
- `go.mod` → Go project
- `Cargo.toml` → Rust project

## STEP 2: Present Findings & Ask Questions

Present what you detected in a clear summary, then ask the user to confirm and fill gaps.

Use AskUserQuestion for each category. Batch related questions. Example flow:

### Question 1: Project Type
"I detected [findings]. What type of project is this?"
- Frontend application
- Backend API/service
- Full-stack application
- Library/package
(let user pick or type custom)

### Question 2: Primary Framework & Language
"I found [framework] with [language]. Is this correct?"
- Confirm detected stack
- Correct if wrong
(show what you detected, let them adjust)

### Question 3: Architecture Pattern
**Existing**: "I see [pattern indicators]. Which architecture pattern does this project follow?"
**Greenfield**: "Which architecture pattern do you want to follow?"
- Clean Architecture (layers: data, domain, presentation)
- MVC/MVVM
- Feature-based/Modular
- Simple/Flat structure
- Other (describe)

### Question 4: Error Handling Strategy
**Existing**: "I found [pattern indicators]. How does this project handle errors?"
**Greenfield**: "How should this project handle errors?"
- Either/Result monads (purify-ts, fp-ts, neverthrow)
- Try/catch with custom error types
- Traditional try/catch
- HTTP error codes (backend)
- Mixed

### Question 5: Development Workflow Preferences
"How strict should the enforcement be?"
- Strict: Every phase gate requires approval, all hooks active
- Moderate: Approval for specs and tasks, hooks active, verify is optional
- Light: Approval for specs only, hooks active
(recommend Strict for new users)

### Question 6: Additional Context
"Anything else I should know about this project? (team conventions, external services, special patterns, deployment targets)"
- Free text input

### Question 7: AI Attribution in Commits
"Should commits created by Claude include AI co-author attribution (Co-Authored-By trailer)?"
- No — commits will have no AI/Claude mention (recommended, default)
- Yes — commits will include `Co-Authored-By: Claude <noreply@anthropic.com>`

(Default to "No" if the user skips or doesn't have a preference.)

### Question 8: Agent Model
"Which model should agents use?"
- opus — Most capable, recommended (default)
- sonnet — Faster, lower cost, good fallback if opus rate-limited

**Model strategy**: The user's choice applies to 13 of 14 agents via the `{{AGENT_MODEL}}` placeholder. The tech-writer agent is hardcoded to `sonnet` regardless of this choice — documentation generation doesn't require opus-level reasoning and benefits from sonnet's faster output speed.

(Default to "opus" if the user skips or doesn't have a preference.)

### Question 9: Acceptance Criteria Verification
"How should acceptance criteria be verified during `/verify`?"
- **Auto** (recommended for frontend/fullstack) — Verify AC against the running app when Chrome DevTools MCP is available; fall back to code reading when not. Backend AC items verified via API calls when possible.
- **Browser only** — Always verify frontend AC via Chrome MCP. Warns if MCP is not available.
- **API only** — Verify AC via API calls and test runner only. No browser interaction. (recommended for backend-only projects)
- **Off** — Verify AC by reading code only (current behavior). (recommended for libraries, CLI tools, Figma plugins)

**Auto-suggestion logic** (suggest based on detected project type):
- Frontend or fullstack project → suggest **Auto**
- Backend-only project with API endpoints detected → suggest **API only**
- Library/package, CLI tool → suggest **Off**
- Figma plugin (`@figma/plugin-typings` in dependencies) → suggest **Off**

**Conditional follow-up (if Auto or Browser only):**
"What URL does your dev server serve the app on?"
- Auto-detect from `package.json` scripts: look for `--port`, `PORT=`, Vite default `5173`, Next.js default `3000`, webpack-dev-server default `8080`, Angular default `4200`
- Present detected URL and let user confirm or change
- Store in `AC_VERIFICATION_URL`

**Conditional follow-up (if Auto or API only, and backend detected):**
"What is the base URL for API endpoints? (Leave empty if not applicable)"
- Auto-detect from backend framework defaults: Express/NestJS `3000`, FastAPI `8000`, Django `8000`
- Store in `AC_VERIFICATION_API_BASE`

(Default to "Auto" for frontend/fullstack, "Off" for library/CLI if user skips.)

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
    Do NOT include any AI or Claude attribution in commits. Specifically:
    - No `Co-Authored-By` trailers referencing Claude, AI, or Anthropic
    - No "Generated by", "Created by Claude", or similar text in title or body
    - Do not set or change git `user.name` or `user.email` to reference Claude or AI
    - This rule overrides any system-level defaults about AI attribution in commits
    ```
  - **If Yes**: replace with:
    ```
    Include AI attribution in every commit by appending this trailer:
    `Co-Authored-By: Claude <noreply@anthropic.com>`
    ```

- `{{AGENT_MODEL}}` — agent model from Question 8 answer (`opus` or `sonnet`). Used in agent template frontmatter.

**Wrapper Mode section** (only included when wrapper mode is active — replace `{{WRAPPER_MODE_SECTION}}` with this):
```markdown
## Wrapper Mode

This workspace wraps a client-owned project. Claude artifacts live here; source code lives in `{{SOURCE_ROOT}}/`.

### Wrapper Rules
1. **Never create Claude artifacts inside `{{SOURCE_ROOT}}/`** — no `.claude/`, `specs/`, `docs/`, `constitution.md`, or `CLAUDE.md` files
2. **All source scanning** (by `/constitute`, `/onboard`, agents) targets `{{SOURCE_ROOT}}/` as the base path
3. **Git auto-commits** apply to both repos — wrapper gets workflow commits, source repo gets WIP commits per task that are squashed into one clean commit (format: `[TICKET-ID] - Description`) when the feature is verified
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
| `security-reviewer` | Include when: auth library detected (passport, okta, auth0, next-auth), OR backend with API endpoints, OR user explicitly requests it. Skip for: simple frontend-only projects with no auth |
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
- Add project-specific patterns you discovered during detection (existing projects) or framework best-practice patterns (greenfield) — add these as NEW sections or append to existing sections, never replace template content
- Replace `{{AGENT_MODEL}}` with the model chosen in Question 8 (default: `opus`)
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

Generate `constitution.md` at project root with a header and a note that it will be fully populated when `/constitute` is run. Include the project type and framework as initial metadata.

### 3.6: Create docs/ folder

Create the documentation directory structure:
```
docs/
  overview.md              # Stub with project name and "TODO: populate after /constitute"
  architecture.md          # Stub with "TODO: populate after /constitute"
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
  "COMMIT_ATTRIBUTION": "Do NOT include any AI or Claude attribution in commits. Specifically:\n- No `Co-Authored-By` trailers referencing Claude, AI, or Anthropic\n- No \"Generated by\", \"Created by Claude\", or similar text in title or body\n- Do not set or change git `user.name` or `user.email` to reference Claude or AI\n- This rule overrides any system-level defaults about AI attribution in commits",
  "AGENT_MODEL": "opus",
  "AC_VERIFICATION": "auto",
  "AC_VERIFICATION_URL": "http://localhost:5173",
  "AC_VERIFICATION_API_BASE": ""
}
```

**Required keys**: `PROJECT_NAME`, `PROJECT_TYPE`, `FRAMEWORK`, `LANGUAGE`, `BUILD_TOOL`, `BUILD_COMMAND`, `TYPE_CHECK_COMMAND`, `LINT_COMMAND`, `SOURCE_ROOT`, `PROJECT_MODE`, `ARCHITECTURE`, `ERROR_HANDLING`, `API_LAYER`, `STATE_MANAGEMENT`, `STYLING`, `MONOREPO_TOOL`, `TESTING`, `PROJECT_PATHS`, `PROJECT_STRUCTURE`, `DEV_COMMANDS`, `AGENT_LIST`, `WRAPPER_MODE_SECTION`, `COMMIT_ATTRIBUTION`, `AGENT_MODEL`, `AC_VERIFICATION`, `AC_VERIFICATION_URL`, `AC_VERIFICATION_API_BASE`.

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
- constitution.md — Constitution stub (run /constitute to populate)
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
2. Run /constitute to generate your project's constitution
3. [Existing projects only] Run /onboard to generate comprehensive codebase documentation
4. Start working with /specify "your first feature"
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
