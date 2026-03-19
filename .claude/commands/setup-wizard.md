# /setup-wizard — Project Initialization Wizard

You are running the initial setup wizard for the Claude Hybrid Template. Your job is to analyze the current project, ask the user targeted questions, and generate all configuration files.

## STEP 0: Greenfield Detection

Before scanning, check if this is a new/empty project:
1. Count source files (exclude `node_modules`, `.git`, `dist`, `build`, config files at root)
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
- `express` or `fastify` or `koa` or `hono` in dependencies → Node.js backend
- `nestjs` in dependencies → NestJS
- `django` or `flask` in `requirements.txt` / `pyproject.toml` → Python backend

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

**Error handling patterns** (scan a few source files):
- `Either`, `Left`, `Right` imports → Either/Result pattern (purify-ts, fp-ts, neverthrow)
- Mostly `try/catch` → Traditional error handling

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
- `{{TEST_FRAMEWORK}}` — testing framework
- `{{LINT_TOOL}}` — linting tool
- `{{STATE_MANAGEMENT}}` — state management solution (or "N/A")
- `{{API_LAYER}}` — GraphQL/REST/tRPC
- `{{ARCHITECTURE}}` — architecture pattern
- `{{ERROR_HANDLING}}` — error handling strategy
- `{{STYLING}}` — CSS framework/approach
- `{{MONOREPO_TOOL}}` — monorepo tool (or "N/A")
- `{{PROJECT_STRUCTURE}}` — generate a tree of the actual project structure
- `{{DEV_COMMANDS}}` — actual dev/build/test/lint commands from package.json scripts
- `{{AGENT_LIST}}` — list of agents generated for this project

Fill the commands section with REAL commands from the project's `package.json` scripts (or `Makefile`, `pyproject.toml`, etc.). Do NOT use placeholder commands.

**Greenfield note**: If no scripts exist yet (empty `package.json`), generate sensible defaults based on the chosen framework and build tool (e.g., `vite dev`, `vitest`, `eslint .`). Mark them with a comment: `<!-- default, update after scaffolding -->`.

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
| Frontend detected | `frontend-engineer` |
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
| `security-reviewer` | Include when: auth library detected (passport, okta, auth0, next-auth), OR backend with API endpoints, OR user explicitly requests it. Skip for: simple frontend-only projects with no auth |

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
- Set appropriate model: `opus` for runtime-debugger, `sonnet` for others
- **Greenfield**: Use framework-idiomatic examples in agents since there's no project code to reference yet

**CRITICAL**: The generated agent file = full template content + placeholder replacements + project-specific additions. Never subtract from the template.

### 3.3: Generate settings.json

Read `.claude/templates/settings.template.json` and generate `.claude/settings.json`.

Configure PostToolUse hooks based on detected tooling:
- TypeScript project → `tsc --noEmit --pretty 2>&1 | head -20`
- Python project → `python -m py_compile` or `mypy --no-error-summary`
- Go project → `go vet ./...`
- Rust project → `cargo check 2>&1 | head -20`

Adjust the `cd` path in the hook to the actual project directory where the type checker should run. For monorepos, point to the root or the appropriate package.

### 3.4: Generate Memory

Read `.claude/templates/memory.template.md` and generate `.claude/memory/MEMORY.md`.

Pre-populate with:
- Project structure summary
- Key file paths
- Architecture pattern notes
- Any patterns you discovered during detection

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

### Next Steps:
1. Review the generated files and adjust if needed
2. Run /constitute to generate your project's constitution
3. [Existing projects only] Run /onboard to generate comprehensive codebase documentation
4. Start working with /specify "your first feature"
```

## IMPORTANT RULES

1. **Never guess** — if you can't detect something, ask
2. **Use real paths** — all generated paths must point to actual directories in the project
3. **Use real commands** — all generated commands must come from the project's actual scripts
4. **Preserve existing files** — if `CLAUDE.md` or `.claude/settings.json` already exists, warn the user and ask before overwriting
5. **Validate after generation** — read back each generated file to verify it has no unresolved `{{PLACEHOLDER}}` variables
