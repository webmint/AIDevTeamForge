# Phase 1 — Detection

This reference covers the read-only / confirm-level detection work of the setup-wizard flow, loaded by the wizard orchestrator when Phase 1 executes. Read it fully, then execute STEPs 0 through 3 in order.

## Outputs to retain in conversational memory

This phase produces the following values. Hold them in conversational memory for use by Phase 2 (questions), Phase 3 (population), and Phase 4 (agents):

- `SOURCE_ROOT` — `.` for standalone, inner folder name for wrapper (e.g., `client-project`)
- `WORKSPACE_MODE` — `standalone` or `wrapper`
- `PROJECT_STATE` — `empty`, `greenfield`, or `brownfield`
- `DEFAULT_BRANCH` — git default branch name (e.g., `main`)
- `LANGUAGES` — ordered array of detected languages, most-files-first
- `FRAMEWORKS` — parallel array; each element is the dominant framework for the language at the same index (or `null` if none)
- `PRIMARY_LANGUAGE` — first element of `LANGUAGES` (or user's explicit pick if they overrode)
- `PACKAGES_DETECTED` — array of per-package records found via manifest-file scan. Each record: `{ path, manifest, language_hint, framework_hint }`. Empty array `[]` for projects with no manifests. Single-element array for non-monorepo projects. Used by Phase 3 to derive per-package stack mappings.
- `BUILD_TOOLS` — array parallel to `LANGUAGES`; build tool name for each stack (e.g., `"Vite"`, `"Cargo"`, `"Go"`, `"Poetry"`). `"N/A"` when the stack has no build step. `null` if unresolvable.
- `BUILD_COMMANDS` — array parallel to `LANGUAGES`; actual shell command to build each stack (e.g., `"npm run build"`, `"cargo build"`, `"go build ./..."`, `"poetry run build"`). Wrapper-mode prefix (`cd SOURCE_ROOT &&`) applied per-element when applicable. `"N/A"` if no build step.
- `TYPE_CHECK_COMMANDS` — array parallel to `LANGUAGES`; shell command to type-check each stack (e.g., `"tsc --noEmit --pretty 2>&1 | head -20"`, `"mypy ."`, `"cargo check 2>&1 | head -20"`, `"go vet ./..."`). `"N/A"` for languages with no static type checker (plain JavaScript, Ruby, PHP without static analysis).
- `LINT_COMMANDS` — array parallel to `LANGUAGES`; shell command to lint each stack (e.g., `"eslint ."`, `"ruff check ."`, `"golangci-lint run"`, `"cargo clippy"`). `"N/A"` if no linter is configured or available for that language.
- Detection outputs from STEP 3 (package manager, monorepo tool, styling, state management, API layer, architecture pattern, error handling pattern, CI/CD tooling, containerization) — each captured as a best-effort value or `uncertain — ask user`.

Where uncertainty exists, carry the uncertainty forward rather than guessing; Phase 2 is where the user resolves ambiguities.

---

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

### 0.3: Set Source Root and Workspace Mode

Store both results for use in all subsequent steps:
- **Standalone**: `SOURCE_ROOT = "."`, `WORKSPACE_MODE = "standalone"`
- **Wrapper**: `SOURCE_ROOT = "[folder-name]"` (e.g., `client-project`), `WORKSPACE_MODE = "wrapper"`

Track both `SOURCE_ROOT` and `WORKSPACE_MODE` in your working context throughout the rest of the wizard; at the end both are persisted to `.devforge/project-config.json` along with all other collected answers.

If wrapper mode:
- Inform the user: "Wrapper mode activated. Source root: `[folder-name]/`. All template artifacts will live in the wrapper root. I'll scan the source code inside `[folder-name]/`."
- Verify the inner folder exists and contains files

## STEP 1: Project State

Auto-detect project state before asking. STEP 1 is a read-only detection step — only fall back to `{{ask}}` when evidence is ambiguous. This matches the rest of Phase 1's "detect first, confirm on ambiguity" posture and avoids asking users to classify something the tool can observe directly.

### 1.1: Count source files

Count source files under SOURCE_ROOT, excluding:

- VCS / tooling directories: `.git`, hidden directories (starting with `.`)
- Dependency trees: `node_modules`, `vendor`, `.venv`, `venv`, `__pycache__`, `.gradle`, `target` (Rust/Java build output)
- Build artifacts: `dist`, `build`, `out`, `.next`, `.nuxt`, `coverage`
- Root-level config / metadata files (`package.json`, `tsconfig.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `README*`, `.gitignore`, `Dockerfile`, lockfiles, etc.)

"Source files" means actual code files (`.ts`, `.tsx`, `.js`, `.jsx`, `.py`, `.rs`, `.go`, `.java`, `.kt`, `.swift`, `.rb`, `.php`, `.cs`, `.vue`, `.svelte`, `.dart`, `.ex`, `.exs`, etc.) — not configs, not docs, not assets.

### 1.2: Classify

Apply these rules in order; first match wins:

1. **0 source files** → `PROJECT_STATE = empty`. Inform user: "No source files found — treating this as an empty project. I'll ask you about your intended stack in the next phase." No confirmation needed.
2. **1–5 source files AND the layout matches a known scaffold signature** → `PROJECT_STATE = greenfield`. Inform user: "Looks like a freshly scaffolded `<scaffold name>` project — treating this as greenfield." Known scaffold signatures (non-exhaustive, use ecosystem knowledge to extend):
   - Vite: `vite.config.*` + `index.html` + `src/main.{ts,tsx,js,jsx}`
   - Next.js `create-next-app`: `next.config.*` + `app/` or `pages/` with only template files
   - `cargo new`: `Cargo.toml` + `src/main.rs` (single file, default content) or `src/lib.rs`
   - `django-admin startproject`: `manage.py` + `<name>/settings.py` + `<name>/urls.py` + `<name>/wsgi.py`
   - `flutter create`: `pubspec.yaml` + `lib/main.dart` (default counter app)
   - `go mod init` + `main.go` (single file, default `package main`)
   - `npm init` / `bun create` / similar with only stub `index.*`
3. **6+ source files** → `PROJECT_STATE = brownfield`. Inform user: "Detected an existing codebase — I'll scan it for patterns in STEP 3."
4. **Ambiguous** (1–5 source files that don't match a recognizable scaffold, OR scaffold markers present but mixed with clearly-custom code) → fall back to explicit ask:

   {{ask "I found a small number of source files but couldn't confidently classify the project state. Which is it?"}}
   - Empty / brand new — no meaningful code
   - Greenfield / just scaffolded — only boilerplate present, no custom code yet
   - Brownfield / existing — real codebase with custom code, established patterns
   {{/ask}}

Store the result as `PROJECT_STATE`. This controls detection depth in STEP 3 and question behavior in Phase 2 (`references/questions.md`):

- **Empty**: skip STEP 3 entirely — there's nothing to scan. All project info comes from user answers in Phase 2.
- **Greenfield**: STEP 3 does a light scan — read config/manifest files only (e.g. `package.json`, `Cargo.toml`, `tsconfig.json`, `pyproject.toml`) to extract language, framework, and tooling. Skip source-code scanning for patterns. In Phase 2 (`references/questions.md`), ask MORE questions since there's less to auto-detect. In Phase 3 (`references/populate.md`), use framework best-practice defaults instead of extracted patterns.
- **Brownfield**: STEP 3 does a full scan — read configs + representative source files to detect architecture, error handling, conventions. In Phase 3 (`references/populate.md`), use project-specific patterns extracted from real code.

## STEP 2: Default Branch

Detect first, ask only if detection fails. Matches the rest of Phase 1's "detect-first, confirm on ambiguity" posture.

**Git-command targeting rule (applies to every git invocation in this phase):** use the `git -C "$SOURCE_ROOT"` form for all git commands. `$SOURCE_ROOT` is `.` in standalone mode and the inner folder name (e.g., `client-project`) in wrapper mode. The `-C` flag makes the target repo explicit in both cases so wrapper mode can't accidentally read the outer workspace's `.git`. Substitute the actual `SOURCE_ROOT` value before invoking — do NOT emit the literal string `$SOURCE_ROOT` to the shell.

### 2.1: Detect

Try these signals in order; stop at the first that produces a branch name:

1. **`git -C "$SOURCE_ROOT" symbolic-ref refs/remotes/origin/HEAD`** — canonical source when a remote is configured. Output like `refs/remotes/origin/main` → parse the trailing segment as the branch name.
2. **`git -C "$SOURCE_ROOT" symbolic-ref HEAD`** — fallback for repos without a remote. Output like `refs/heads/main` → parse the trailing segment. (On a detached HEAD this returns non-zero; fall through.)
3. **`git -C "$SOURCE_ROOT" branch --show-current`** — final git-based fallback; returns the current branch name or empty.

### 2.2: Confirm or ask

**If detection succeeded**: store the result as `DEFAULT_BRANCH` and inform the user briefly:
> Default branch detected: `<name>`.

No confirmation ask — this is observable fact, consistent with STEP 1's posture for `empty` / `brownfield` classification.

**If detection failed** (non-git workspace, detached HEAD with no remote, or all three commands returned nothing):

{{ask "I couldn't detect the default branch from git. What is it?"}}
- main (most common)
- master
- develop
- Other — user specifies
{{/ask}}

Store the answer as `DEFAULT_BRANCH`.

`DEFAULT_BRANCH` is used during scanning (STEP 3), population (Phase 3, `references/populate.md`) and agent generation (Phase 4, `references/agents.md`), and by downstream commands for git operations.

## STEP 3: Auto-Detect Project Structure

**If `PROJECT_STATE` is empty**, skip the detection scan in this step but still initialize per-stack outputs explicitly so downstream phases have consistent data:

- `PACKAGES_DETECTED = []` (no manifests to scan; Phase 3 rendering of `{{PACKAGE_STACKS_SECTION}}` suppresses the section for `len <= 1` — empty array is 0, which falls under this suppression rule)
- `LANGUAGES` / `FRAMEWORKS` / `PRIMARY_LANGUAGE` — leave unset here; populated by Q3 answers in Phase 2
- `BUILD_TOOLS` / `BUILD_COMMANDS` / `TYPE_CHECK_COMMANDS` / `LINT_COMMANDS` — leave unset here. **After** Phase 2 Q3 captures `LANGUAGES`, fall back to the language defaults by following the "Per-stack tool detection" section below (priority step 2.2: the language's standard ecosystem tool, using the guiding examples + your training knowledge per the principle-driven rule). Produce parallel-indexed arrays (once per language). Mark the values as greenfield-defaults (no manifest to confirm) and surface them in the Phase 2 findings presentation so the user can review / override.
- Brownfield-only pattern outputs (architecture, error-handling detection) — stay unset; Q4/Q5 present the "empty/greenfield" variants.

Then proceed to Phase 2 (`references/questions.md`). For non-empty projects, continue below.

**All scanning in this step targets the SOURCE_ROOT directory.** For standalone projects this is the workspace root (`.`). For wrapper projects this is the inner folder (e.g., `client-project/`). Resolve all file paths relative to SOURCE_ROOT.

Read dependency manifests, lockfiles, config files, and top-level directory layout at SOURCE_ROOT to identify the project's tech stack. Typical starting points: dependency manifests like `package.json`, `pyproject.toml`, `requirements.txt`, `Pipfile`, `go.mod`, `Cargo.toml`, `pubspec.yaml`, `Gemfile`, `composer.json`, `*.csproj`, `mix.exs`, `deno.json`; config files like `tsconfig.json`, `.eslintrc.*`, `tailwind.config.*`, `pyrightconfig.json`; and structural markers like `Dockerfile`, `.github/workflows/`, workspace/monorepo files (`pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`, Cargo workspace, Go workspaces).

**Brownfield only:** scan a small, deliberate sample of source files to infer architectural patterns (layered / feature-modular / MVC / BLoC / hexagonal / etc.) and error-handling conventions (Either-style results / typed exceptions / traditional try-catch / HTTP-error patterns / etc.).

**Sampling rules:**

- **Prefer entry points**: scan main/index files first (`main.ts`, `index.ts`, `app.py`, `main.go`, `lib.rs`, or the equivalent for the detected ecosystem) — they expose top-level structure and wiring.
- **Include 2–3 files from different major directories** that appear to be distinct modules (e.g., one from `src/domain/`, one from `src/api/`, one from `src/ui/`). Pick directories that look substantive, not leaf utilities.
- **Hard cap**: read no more than 8–10 source files total. If the project is too large to infer confidently from that sample, stop and present uncertainty to the user in Phase 2 rather than inventing confidence from a partial view.
- **Ground every claim**: any pattern or convention you report must cite specific file paths and specific indicators you actually observed in those files (class names, import statements, decorators, folder layout, etc.). Anti-hallucination rule applies — no "it looks like X" without quotable evidence.

### Package-root detection

Enumerate every directory under SOURCE_ROOT that contains a recognized manifest file. This gives the per-package structure used later by Phase 3 to build a `PACKAGE_STACKS` table in CLAUDE.md / AGENTS.md.

**Recognized manifests:** `package.json`, `pyproject.toml`, `requirements.txt`, `Pipfile`, `go.mod`, `Cargo.toml`, `pubspec.yaml`, `Gemfile`, `composer.json`, `*.csproj`, `mix.exs`, `deno.json` (extend if the ecosystem uses a manifest not listed — same recognition logic as the general manifest scan above).

**Scan rules:**

- Start at SOURCE_ROOT, recurse up to 4 directory levels deep (covers typical monorepo nesting like `apps/web/`, `packages/scope/sub/`)
- Skip the same ignore-dirs as STEP 0.1: `node_modules/`, `vendor/`, `target/`, `venv/`, `.venv/`, `__pycache__/`, `build/`, `dist/`, `.gradle/`, `out/`, plus hidden directories and anything starting with `.`
- Include workspace-root manifests (e.g., a top-level `package.json` for pnpm / npm / Turborepo / Nx workspaces) — they ARE packages even when their only purpose is workspace coordination
- Each manifest location yields ONE `PACKAGES_DETECTED` record; do not merge sibling manifests

**For each manifest found, record:**

| Field | Value |
|---|---|
| `path` | Directory relative to SOURCE_ROOT containing the manifest (e.g., `"."`, `"apps/web"`, `"services/api"`) |
| `manifest` | Filename (e.g., `"package.json"`, `"pyproject.toml"`) |
| `language_hint` | Inferred from manifest type (`package.json` → `"TypeScript"` if `tsconfig.json` sibling or `"typescript"` in deps, else `"JavaScript"`; `pyproject.toml`/`requirements.txt`/`Pipfile` → `"Python"`; `go.mod` → `"Go"`; `Cargo.toml` → `"Rust"`; `pubspec.yaml` → `"Dart"`; `*.csproj` → `"C#"`; `mix.exs` → `"Elixir"`; `Gemfile` → `"Ruby"`; `composer.json` → `"PHP"`; `deno.json` → `"TypeScript"`) |
| `framework_hint` | Parse manifest top-level dependencies (or Gradle / pom / csproj equivalents) for APP / WEB / UI framework markers — things that define app structure, routing, or runtime (Next.js, NestJS, FastAPI, Rails, Spring Boot, etc.). When a recognized framework appears by its canonical package name, record the canonical display name (e.g., `next` → `"Next.js"`, `fastapi` → `"FastAPI"`). Use your training knowledge to map dep name → canonical display name. **Scope rule** (what counts as a framework): YES for app/UI/web frameworks that structure the application; NO for utility libraries (lodash, requests, axios, httpx), test runners (jest, vitest, pytest, rspec), build tools (vite, webpack, tsc, esbuild), or linters/formatters (eslint, ruff, prettier, clippy). **Conflict rule** — pick the most specific umbrella when multiple markers appear: SvelteKit > Svelte, Expo > React Native (when Expo is present), Nuxt > Vue (for Nuxt apps). **Anti-hallucination**: if no unambiguous framework marker in top-level deps, leave `null`. Don't infer frameworks from file layout alone — manifest deps are the source of truth. Don't invent novel framework names. |

**Dep-block scope** (applies to both `language_hint` and `framework_hint` detection): when a rule says "dep present in manifest," check ALL standard dependency blocks for that manifest type. Presence in ANY counts as "present" — the block placement (runtime vs dev vs peer) doesn't change what language or framework is being used, just when.

- `package.json`: `dependencies`, `devDependencies`, `peerDependencies`, `optionalDependencies`
- `pyproject.toml`: `[project.dependencies]`, `[tool.poetry.dependencies]`, `[tool.poetry.group.*.dependencies]`, `[project.optional-dependencies]`
- `Cargo.toml`: `[dependencies]`, `[dev-dependencies]`, `[build-dependencies]`
- `go.mod`: `require` blocks (both direct and indirect)
- `Gemfile`: all `gem` declarations regardless of group
- `composer.json`: `require`, `require-dev`
- `pubspec.yaml`: `dependencies`, `dev_dependencies`
- `*.csproj`: `<PackageReference>` elements
- `mix.exs`: the `deps/0` function
- `deno.json`: `imports`

For any manifest not listed above, check the ecosystem's equivalent standard dependency sections (runtime, dev, peer, optional).

**Edge cases:**

- **No manifests found anywhere** (pure scripts, text-only project): `PACKAGES_DETECTED = []`. Phase 3 will suppress the `{{PACKAGE_STACKS_SECTION}}` rendering.
- **Single manifest at SOURCE_ROOT**: `PACKAGES_DETECTED = [{ path: ".", ... }]` — one-element array. Phase 3 renders a minimal table or inline note.
- **Monorepo with workspace-root + member manifests**: include all of them. A workspace-only root (e.g., top-level `package.json` with `"workspaces": [...]` and no app deps) still counts; flag `framework_hint: null`.
- **Duplicate manifests** (rare; e.g., both `requirements.txt` and `pyproject.toml` in the same dir): pick the more authoritative one (`pyproject.toml` > `requirements.txt` > `Pipfile`), emit one record.

### Per-stack tool detection

Capture `BUILD_TOOLS`, `BUILD_COMMANDS`, `TYPE_CHECK_COMMANDS`, `LINT_COMMANDS` as arrays parallel to `LANGUAGES`. For each language `LANGUAGES[i]`:

1. **Scan manifests for that language** (from `PACKAGES_DETECTED` when multi-package; else SOURCE_ROOT directly). Look for:
   - Build-tool declarations (`package.json` `devDependencies.vite`, `Cargo.toml` `[build]`, `go.mod`, etc.)
   - Script blocks (`package.json` `scripts.build` / `scripts.lint`, `pyproject.toml` `[tool.poetry.scripts]`, etc.)
   - Dev-dependency entries for linters / type-checkers

2. **For each field** (`build_tool`, `build_command`, `type_check_command`, `lint_command`), resolve in priority order:

   1. **Manifest-declared script or tool** if present — most specific; the project author chose it deliberately (e.g., `package.json scripts.build = "tsup src/index.ts"` → `build_command = "<runner> run build"`, where `<runner>` is resolved per the "Command-runner selection" rule below — e.g., `pnpm run build` in a pnpm monorepo, `npm run build` in an npm project).
   2. **Language's standard ecosystem tool** (from your training knowledge of that language's community conventions): the widely-adopted build command, static type checker, and linter a developer in that ecosystem would expect by default. For languages with no static type checker by convention (plain JavaScript, Ruby, PHP without static analysis), use the literal string `"N/A"` for `type_check_command`.
   3. **`null`** if you're unsure about the standard tool — don't invent a plausible-looking command.

   **Command-runner selection** (applies whenever priority step 2.1 fires — the manifest declares a script that needs to be invoked via a runner: `package.json scripts.*`, `pyproject.toml [tool.poetry.scripts]`, `Gemfile`, etc.). Pick the runner from concrete signals in this order; do NOT default to a runner the project doesn't use (e.g., don't emit `npm run build` in a pnpm repo):

   - **JS / TS**: lockfile presence decides — `pnpm-lock.yaml` → `pnpm`, `yarn.lock` → `yarn`, `bun.lockb` / `bun.lock` → `bun`, `package-lock.json` → `npm`. If no lockfile, check the `packageManager` field in `package.json`; otherwise fall back to `npm`.
   - **Python**: manifest content decides — `pyproject.toml` with `[tool.poetry]` → `poetry run`, with `[tool.hatch]` → `hatch run`, with `[tool.pdm]` → `pdm run`; `uv.lock` present → `uv run`; otherwise `python -m` direct invocation.
   - **Ruby**: `Gemfile.lock` present → prefix commands with `bundle exec`; otherwise bare command.
   - **Rust / Go / Swift / Cargo-workspace / Go-workspace**: single-runner ecosystems — use the toolchain's own command (`cargo`, `go`, `swift`) directly, no runner selection needed.
   - **JVM family**: wrapper presence decides — `./gradlew` / `gradlew.bat` → `./gradlew <task>`; `./mvnw` → `./mvnw <goal>`; `build.sbt` only → `sbt <task>`.
   - **Other ecosystems**: pick the runner that matches the manifest / lockfile actually observed in the repo. If you can't determine the runner from concrete signals, leave the command `null` rather than guess.

   **Guiding examples** (anchors, not exhaustive — use training knowledge for any language not listed):
   - **TS / JS** → Vite or Webpack + `npm run build`; type-check `tsc --noEmit --pretty 2>&1 | head -20` for TS, `"N/A"` for plain JS; lint `eslint .`
   - **Python** → Poetry / setuptools / Hatch + `poetry run build` or `python -m build`; type-check `mypy .`; lint `ruff check .`
   - **Rust** → Cargo + `cargo build`; type-check `cargo check 2>&1 | head -20`; lint `cargo clippy -- -D warnings`
   - **Go** → `go build ./...`; type-check `go vet ./...`; lint `golangci-lint run`
   - **JVM-family** (Kotlin, Scala, Java, Groovy) → Gradle / Maven / sbt + the language's standard build goal; type-check happens during compile (`./gradlew compileKotlin`, `sbt compile`); lint per language's dominant community linter (`ktlintCheck`, `scalafmtCheck`, `detekt`, etc.) if configured
   - **Swift** → Swift Package Manager + `swift build`; type-check happens during build; lint `swiftlint lint` if detected

   For other common languages (Dart/Flutter, C#/.NET, Ruby, PHP, Elixir, Haskell, Clojure, Lua, Zig, Nim, Crystal, Julia, etc.): use your training knowledge of each ecosystem's community standard.

3. **Wrapper-mode prefix**: for projects where `SOURCE_ROOT != "."`, prefix each command with `cd SOURCE_ROOT && `. Applied per-element in each array.

4. **Anti-hallucination**: if the manifest is present but the script/tool isn't named, use the language default from step 2.2. If you're unsure about the standard tool for a language, leave `null` rather than guess. Phase 3's rendering handles `null` as "no command available".

5. **Per-package overrides**: captured separately via `PACKAGES_DETECTED`. `BUILD_COMMANDS` etc. are stack-level (per-LANGUAGE) defaults. When downstream consumers need per-package commands (e.g., scope-aware verification in `{{cli.sigil}}execute-task`), they look up the package in `PACKAGE_STACKS` and fall back to the language-level command if the package doesn't override.

### Aggregated categories

Based on what you find, identify each of the following. Mark any category that genuinely doesn't apply as **N/A**. If you're uncertain, note the uncertainty and raise it with the user in Phase 2 (`references/questions.md`) rather than guessing.

- **Languages and runtimes** — detect all present by aggregating file counts **across `PACKAGES_DETECTED`** (not flat-tree scanning of SOURCE_ROOT). For each package, enumerate source files under its `path` directory by extension, classify by language (`.ts`/`.tsx` → TypeScript, `.py` → Python, `.go` → Go, `.rs` → Rust, `.kt` → Kotlin, `.swift` → Swift, etc.), then sum per language across all packages. Order the resulting `LANGUAGES` array by total file count descending (most files first). This avoids dependency-like packages (e.g., a large generated-SDK package in TS) drowning out the smaller-but-more-critical primary package (e.g., a Python API service). Note the associated runtime per language (TypeScript → Node, Python → Python 3, Dart → Flutter, etc.).

  **Scale cap**: if a package's directory contains more than ~500 source files, don't enumerate exhaustively — use the package's manifest (from `PACKAGES_DETECTED.manifest`) + `language_hint` as the primary classifier for that package, and estimate file count via a coarse signal (shell directory listing, `find` with depth limit, or single-directory scan). The goal is **ordering by magnitude**, not exact counts — off-by-10% is acceptable, wrong-by-dominant-language is not.

  **Tiebreaker for ambiguous ordering**: if two languages have comparable file counts (within ~20% of each other), prefer ordering by **manifest count** (more manifests → more active packages → likely more important to the project). Surface the resulting ordering to the user in Q3 and let them confirm/override — the user knows which language carries the critical app logic.
- **Primary framework(s)** (app-level, not library-level)
- **Package manager** (if applicable)
- **Testing framework(s)** (if present) — captured as per-stack array `TESTINGS` via Q7 (confirmed by user); detection provides initial per-stack hints from manifests
- **Linting / formatting tools** (if configured) — captured as per-stack array `LINT_COMMANDS` via detection (see "Per-stack tool detection" above)
- **Build tool / bundler** — captured as per-stack arrays `BUILD_TOOLS` + `BUILD_COMMANDS` via detection (see "Per-stack tool detection" above)
- **Monorepo tool** (if applicable)
- **Styling approach** (web frontends only — CSS approach, UI framework)
- **State management** (web/mobile frontends only, if detectable)
- **API layer** (REST / GraphQL / gRPC / tRPC / etc., if applicable)
- **Architecture pattern** (for existing projects with enough code to infer)
- **Error handling pattern** (for existing projects, from representative source)
- **CI/CD presence** and tooling (GitHub Actions, GitLab CI, etc.)
- **Containerization** (Dockerfile, docker-compose, buildpacks, etc.)

Do not invent details or fill categories with plausible-sounding defaults. An honest "uncertain — will ask the user" beats a confident wrong guess. Do not limit yourself to the indicators mentioned above — examine whatever is actually present, in whatever ecosystem the project uses.

### Detection Report — Phase 1 output

Phase 1 ends with emitting a structured Detection Report. This is the handoff from detection to Phase 2 (questions) and Phase 3 (population): both phases reference fields in the Report to avoid re-asking the user about things already detected, and Phase 3 reads Report fields to populate `.devforge/project-config.json`. A prose summary does not populate those fields — the Report is emitted as a fenced YAML code block so downstream phases can read it. Runtime-to-runtime parity of downstream artifacts (`project-config.json`, `CLAUDE.md`, `AGENTS.md`) depends on both runtimes emitting the Report in the same shape.

**Rules** (apply to every report):

1. **Every field below is required.** If a field has no value, emit `null` plus a one-line reason (as an inline YAML comment: `# reason: ...`). Never omit a field. "I didn't detect one" is not a valid outcome — emit `null` with the specific signals checked.

2. **Dep+usage double-check for library-category fields.** For `auth_layer`, `api_client`, `state_management`, `styling`, `routing`, `error_handling`, `validation_library`: run BOTH a dependency-manifest scan AND a source-code usage-pattern grep. Emit `null` only when both return empty. If either returns a hit, name the library. Canonical usage patterns to grep for the harder-to-detect categories:
   - error_handling: `Either<`, `Result<`, `Maybe<`, `Task<`, `Try<`, `neverthrow`, `purify-ts`, `fp-ts`, `oxide.ts`, `ts-results`, `monet`
   - validation: `zod`, `yup`, `joi`, `ajv`, `pydantic`, `marshmallow`, `class-validator`
   - Use the same pattern for any library category — dep name shortlist + source-grep; never decide "none" from only one check.

3. **Architecture bucket is enumerated.** `architecture_shape` MUST be one of: `layered`, `feature-modular`, `monorepo`, `feature-modular-monorepo`, `hexagonal`, `mvc`, `bloc`, `flat`, `other`. No free-form labels (e.g., `"BLoC + use-cases + repositories"` is not valid — pick the closest bucket and cite the specific indicators in `architecture_evidence`). If no bucket fits, use `other` with explicit evidence.

4. **Per-package commands are per-package-specific.** Each `packages[]` entry requires `build_command` / `lint_command` / `type_check_command` / `test_command` read from THAT package's own `scripts` block (or manifest equivalent). A generic fallback (e.g., `yarn build` applied uniformly) is allowed only if that package's manifest has no scripts AND a language default applies — in which case set `command_source: fallback`. Otherwise `command_source: manifest`.

5. **Workspace members vs utility manifests.** Only directories that are declared workspace members (in `package.json` `workspaces`, `pnpm-workspace.yaml`, `lerna.json`, Cargo workspace members, Go workspace `use` directives, etc.) go in `packages[]`. Directories with a manifest but not declared as workspace members (ad-hoc script folders, vendored tools) go in `optional.utility_manifests[]`. If the repo has no workspace declaration, every manifest location is a package.

6. **Wrapper-mode prefix** (`cd SOURCE_ROOT && ...`) applies to per-package commands as well as stack-level commands.

7. **Evidence required for every non-null value.** A file path, a dep name, or a usage-pattern excerpt — so the user (and later parity diffs) can verify. Either as an inline `# evidence: ...` comment or as a structured `evidence:` sub-field.

8. **`runtime_url` must read dev-server config** if one is present (`vite.config.ts`, `webpack.config.js` `devServer`, `next.config.js`, `angular.json` `serve`, Django `settings.py` `ALLOWED_HOSTS`, etc.). Framework defaults (`http://localhost:5173`, etc.) are acceptable ONLY when no dev-server config is detected — and must be flagged `source: framework-default`.

**Shape** (fill with actual detected values; shown here with placeholder values and the rule comments removed):

<!-- >>> EMIT THIS YAML BLOCK TO USER — VERBATIM — BEFORE PHASE 2 <<< -->

```yaml
detection_report:
  workspace_mode: standalone            # standalone | wrapper
  source_root: "."
  project_state: brownfield             # empty | greenfield | brownfield
  default_branch: main                  # from SOURCE_ROOT/.git (inner repo in wrapper mode)
  file_count: 0                         # under SOURCE_ROOT, per STEP 1.1 exclusions
  manifest_count: 0

  languages:
    - name: TypeScript
      file_count: 0
      runtime: Node
  primary_language: TypeScript

  frameworks:
    - name: Vue 3
      role: frontend                    # frontend | backend | library | plugin
      evidence: "apps/app-web/package.json: vue@^3"

  package_manager:
    tool: yarn                          # npm | yarn | pnpm | bun | pip | poetry | cargo | go | ...
    outer_tool: null                    # set only if wrapper and outer uses a different pm
    evidence: "yarn.lock at SOURCE_ROOT"
  monorepo_tool: null                   # Lerna | Turborepo | Nx | pnpm-workspaces | Cargo-workspace | null

  build_tool: null
  build_command: null
  type_check_command: null
  lint_command: null
  test_runner: null

  # Library-category fields — dep+usage double-check rule applies.
  auth_layer: null                      # e.g., "Okta" (evidence: @okta/okta-vue in deps + plugin install)
  api_client: null                      # e.g., "Apollo GraphQL" (evidence: @apollo/client + gql tags in src/)
  state_management: null                # e.g., "Pinia" (evidence: pinia in deps + defineStore in src/)
  styling: null                         # e.g., "Tailwind + SCSS"
  routing: null                         # e.g., "vue-router"
  error_handling:
    library: null                       # e.g., "purify-ts"
    usage_pattern: null                 # e.g., "Either<DataError, ...> in pkg-cse-core/src/**/data/*.ts"
  validation_library: null

  architecture_shape: flat              # enumerated — see Rule 3
  architecture_evidence: ""             # file paths + indicators

  enforcement_tooling: []               # e.g., ["Husky (pre-commit)", "lint-staged", "commitlint"]
  ci_cd: null                           # e.g., "GitHub Actions" (evidence: .github/workflows/*.yml)
  containerization: null                # e.g., "Dockerfile + docker-compose.yml"

  runtime_url:
    value: null                         # e.g., "https://app.local:8080"
    source: null                        # "vite.config.ts: server.host/port/https" | "framework-default" | null

  packages:
    - path: "."                         # workspace member, relative to SOURCE_ROOT
      manifest: package.json
      language_hint: TypeScript
      framework_hint: null
      build_command: null               # read from THIS package's scripts
      type_check_command: null
      lint_command: null
      test_command: null
      command_source: manifest          # manifest | fallback (see Rule 4)

  optional:
    utility_manifests: []               # manifests outside workspace declaration (see Rule 5)
    # plus any stack-specific slots not in the core list (e.g., mobile_platform, ml_framework).
    # Keep key names stable across runs so parity diffs stay comparable.
```

<!-- >>> END OF REQUIRED EMIT <<< -->

After emitting the report, proceed to Phase 2. Phase 3 (`references/populate.md`) reads these fields when populating `.devforge/project-config.json`; the mapping from report fields to config fields is defined there.

---

Detection phase complete. Proceed to Phase 2 (`references/questions.md`).
