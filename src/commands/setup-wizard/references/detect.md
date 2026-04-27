# Phase 1 — Detection

This reference covers the read-only / confirm-level detection work of the setup-wizard flow, loaded by the wizard orchestrator when Phase 1 executes. Read it fully, then execute STEPs 0 through 3 in order.

## Outputs of this phase

This phase produces the following structured values. They are written to `.devforge/detection_report.yaml` via the `scripts/lib/detect_report` CLI helper (see "Detection Report — Phase 1 output" below). Phase 2 (questions), Phase 3 (population), and Phase 4 (agents) read these values from the file, not from conversation memory:

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

**Storage note for the 4 command/tool arrays.** `BUILD_TOOLS` / `BUILD_COMMANDS` / `TYPE_CHECK_COMMANDS` / `LINT_COMMANDS` are NOT written to `.devforge/detection_report.yaml` — the Report schema carries only top-level scalar fallbacks (`build_command`, `type_check_command`, `lint_command`) plus per-package commands inside `packages[]`. These per-stack arrays live in LLM working memory between Phase 1 and Phase 3, where Phase 3's `wizard_render add-build-tool` / `add-build-command` / `add-type-check-command` / `add-lint-command` setters land them in `wizard_render` state for compose-time use. If the wizard session is interrupted between phases, re-derive these arrays from `detection_report.packages[].*_command` (per-package fields, which ARE persisted) before resuming Phase 3.

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
{{/ask}}

AskUserQuestion caps options at 4; show Standalone + the 3 most-likely wrapper candidates (rank by file count under each folder, descending). Additional candidates are reachable via the auto "Other" affordance — the user types the folder name. If 4 or fewer candidates exist, list all of them.

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

Count source files under SOURCE_ROOT using this **canonical algorithm** (deterministic across runs — same project, same count):

**Excluded directories** (canonical list — no extensions to it):
- VCS / tooling: `.git/`, any directory starting with `.` (e.g., `.idea/`, `.vscode/`, `.devforge/`, `.husky/`)
- Dependency trees: `node_modules/`, `vendor/`, `.venv/`, `venv/`, `__pycache__/`, `.gradle/`, `target/`, `Pods/`, `DerivedData/`
- Build artifacts: `dist/`, `build/`, `out/`, `.next/`, `.nuxt/`, `coverage/`, `.turbo/`, `.cache/`

**Excluded files** (canonical list):
- All lockfiles (`*.lock`, `*.lockb`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `Cargo.lock`, `poetry.lock`, `Gemfile.lock`, `composer.lock`)
- Manifests / config (`package.json`, `tsconfig*.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `go.sum`, `pom.xml`, `build.gradle*`, `Gemfile`, `composer.json`, `mix.exs`, `pubspec.yaml`)
- Docs / metadata (`README*`, `LICENSE*`, `CHANGELOG*`, `.gitignore`, `.gitattributes`, `.editorconfig`, `Dockerfile*`, `docker-compose*.y*ml`)

**Counted file extensions** (canonical list — count files matching ANY of these):
`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.vue`, `.svelte`, `.astro`, `.py`, `.rs`, `.go`, `.java`, `.kt`, `.kts`, `.swift`, `.rb`, `.php`, `.cs`, `.fs`, `.dart`, `.ex`, `.exs`, `.erl`, `.scala`, `.clj`, `.cljs`, `.hs`, `.ml`, `.lua`, `.r`, `.R`, `.jl`, `.zig`, `.nim`, `.cr`, `.v`, `.sol`

If you encounter an extension not in the list above, do NOT count it (treat as non-source). The list is closed — additions need a spec change, not LLM judgment. Configs, docs, assets, generated code (e.g., `*.gen.ts`, `*.g.dart`), and vendored / submoduled directories (when at SOURCE_ROOT depth > 1) are NOT counted.

The count goes into `detection_report.file_count` via `set file_count --value <N>` after summing across all `packages[]` entries (per "Aggregated categories" below).

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

Enumerate every directory under SOURCE_ROOT that contains a recognized manifest file. This gives the per-package structure used later by Phase 3 to build a `PACKAGE_STACKS` table in CLAUDE.md.

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

5. **Per-package overrides**: captured separately via `PACKAGES_DETECTED`. `BUILD_COMMANDS` etc. are stack-level (per-LANGUAGE) defaults. When downstream consumers need per-package commands (e.g., scope-aware verification in `/execute-task`), they look up the package in `PACKAGE_STACKS` and fall back to the language-level command if the package doesn't override.

### Aggregated categories

Based on what you find, identify each of the following. Mark any category that genuinely doesn't apply as **N/A**. If you're uncertain, note the uncertainty and raise it with the user in Phase 2 (`references/questions.md`) rather than guessing.

- **Languages and runtimes** — detect all present by aggregating file counts **across `PACKAGES_DETECTED`** (not flat-tree scanning of SOURCE_ROOT). For each package, enumerate source files under its `path` directory by extension, classify by language (`.ts`/`.tsx` → TypeScript, `.py` → Python, `.go` → Go, `.rs` → Rust, `.kt` → Kotlin, `.swift` → Swift, etc.), then sum per language across all packages. Order the resulting `LANGUAGES` array by total file count descending (most files first). This avoids dependency-like packages (e.g., a large generated-SDK package in TS) drowning out the smaller-but-more-critical primary package (e.g., a Python API service).

  **Canonical `runtime` value per language** (use the value below verbatim when calling `add-language --runtime <value>` — the canonical short form keeps detection output stable across runs):

  | Language | Canonical `runtime` |
  |---|---|
  | TypeScript | `Node` |
  | JavaScript | `Node` |
  | Python | `Python 3` |
  | Rust | `Rust` |
  | Go | `Go` |
  | Java | `JVM` |
  | Kotlin | `JVM` (or `Android` if Android project) |
  | Swift | `iOS` (or `macOS` if Mac project) |
  | Dart | `Flutter` (or `Dart VM` for non-Flutter) |
  | Ruby | `Ruby` |
  | PHP | `PHP` |
  | C# | `.NET` |
  | Elixir | `BEAM` |
  | Scala | `JVM` |
  | Clojure | `JVM` (or `JS` for ClojureScript) |
  | Haskell | `GHC` |

  Do NOT use compound or context-flavored values like `Node.js`, `browser + node`, `Node (Vite/vue-tsc)` — the canonical short form above is the parity-stable choice. Browser-versus-server distinction belongs in `frameworks[]` (e.g., framework `role: frontend` implies browser context), not in `runtime`. If a language not in the table appears, use the language name itself as a reasonable default (e.g., `Zig` → `Zig`).

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
- **Enforcement tooling** — populated via `add-enforcement-tool --value <s>` (one call per tool present). **Scan exhaustively**: list every tool from the canonical signal set below that has a presence signal in the project. Do NOT stop at the most obvious one (e.g., Husky alone) — missing tools cause downstream commands to skip enforcement.

  **Canonical enforcement-tooling signals** (add each present one):
  - `Husky (pre-commit)` — `.husky/` directory OR `husky` in devDependencies + a `prepare` script
  - `lint-staged` — `lint-staged` in devDependencies OR `.lintstagedrc*` config OR `lint-staged` config block in `package.json`
  - `commitlint` — `@commitlint/*` in devDependencies OR `commitlint.config.*` file
  - `ESLint` — `eslint` in devDependencies OR `.eslintrc*` / `eslint.config.*` file (mention preset/config when distinctive, e.g., `ESLint (airbnb-base + airbnb-typescript + vue plugin)`)
  - `Prettier` — `prettier` in devDependencies OR `.prettierrc*` / `prettier.config.*` file
  - `tsc strict mode` / `vue-tsc strict mode` — `"strict": true` (or any of the strict-* flags) in `tsconfig*.json`. Use `vue-tsc` when the project uses Vue + has `vue-tsc` in scripts; otherwise `tsc`.
  - `Stylelint` — `stylelint` in devDependencies OR `.stylelintrc*` / `stylelint.config.*` file
  - `mypy` (Python) — `mypy` in dev deps OR `mypy.ini` / `pyproject.toml [tool.mypy]`
  - `ruff` (Python) — `ruff` in dev deps OR `ruff.toml` / `pyproject.toml [tool.ruff]`
  - `black` (Python) — `black` in dev deps OR `pyproject.toml [tool.black]`
  - `golangci-lint` (Go) — `.golangci.y*ml` config OR project script invokes it
  - `clippy` (Rust) — `cargo clippy` invoked in CI OR root `clippy.toml`
  - `rustfmt` (Rust) — `rustfmt.toml` OR `cargo fmt` in CI

  If you find an enforcement tool not on this list, still add it (canonical signal set is non-exclusive — but treat the items above as a required minimum-scan checklist, not a sample). For each tool, the value passed to `add-enforcement-tool` should be the canonical name from the bullets above (e.g., `Husky (pre-commit)`, not just `Husky`) so re-runs produce byte-identical output.

Do not invent details or fill categories with plausible-sounding defaults. An honest "uncertain — will ask the user" beats a confident wrong guess. Do not limit yourself to the indicators mentioned above — examine whatever is actually present, in whatever ecosystem the project uses.

### SFC-container and tooling-stack collapsing — BEFORE emitting `LANGUAGES[]`

File-extension counts alone mislead when certain extensions are framework-owned container formats (Vue/Svelte SFCs) or when certain file classes are infrastructure not a separate app stack (tooling scripts). Apply these collapsing rules BEFORE emitting `LANGUAGES[]` and `FRAMEWORKS[]`:

1. **SFC-container collapse** — `.vue`, `.svelte`, `.astro` files are NOT separate languages. Count each under the embedded script language:
   - **Sampling**: read up to 5 files per package for `<script lang="...">` directives.
   - `lang="ts"` → TypeScript; `lang="js"` or no `lang` → JavaScript; sample is conclusive if ≥4 of 5 agree.
   - If inconclusive, fall back to package's `typescript` devDep + sibling `tsconfig.json` (both present → TypeScript; neither → JavaScript).
   - Vue/Svelte/Astro appear in `FRAMEWORKS[]`, never in `LANGUAGES[]`.

2. **React-family extension collapse** — `.tsx` → TypeScript, `.jsx` → JavaScript. React is a framework (goes in `FRAMEWORKS[]`), not a language.

3. **Tooling-script exclusion** — `.js` / `.mjs` / `.cjs` files located at the workspace root or under a `scripts/` directory, in a project whose package manifest declares TypeScript as primary, are tooling (build helpers, codegen, env setup) — NOT a separate application stack. Exclude from `LANGUAGES[]` aggregation. Record them in the Detection Report's `optional.tooling_scripts[]` field if the user might care.

4. **Monorepo coordinator exclusion** — monorepo coordinators (`Lerna`, `Nx`, `Turborepo`, `pnpm-workspaces`, `Cargo-workspace`, `Go-workspace`) populate the Detection Report's `monorepo_tool` field. They MUST NOT populate `FRAMEWORKS[]`. Coordinators are infrastructure, not frameworks.

5. **Threshold rule for new language stacks** — emit a new entry in `LANGUAGES[]` only when that language represents a substantive application or library surface in one or more detected packages, not incidental tooling. Rough threshold: a language should correspond to ≥1 package whose primary source files are in that language AND which is imported/consumed by the application surface. Pure tooling does NOT qualify.

**Expected outcome**: for a Vue 3 + TypeScript monorepo with Lerna coordinator, Vite build tool, and some root-level `.js` scripts, emit `LANGUAGES: [TypeScript]`, `FRAMEWORKS: [Vue 3]`, `monorepo_tool: Lerna`. Not `[TypeScript, Vue, JavaScript]` / `[Vue 3, Vite, Lerna Workspaces]`.

### Detection Report — Phase 1 output

Phase 1 ends by composing a structured Detection Report into `.devforge/detection_report.yaml` via the `scripts/lib/detect_report` CLI helper. This is the handoff from detection to Phase 2 (questions) and Phase 3 (population): both phases read fields from this file to avoid re-asking the user about things already detected, and Phase 3 reads Report fields when populating `.devforge/project-config.json`. The Report is the single source of truth for downstream phases — composing it explicitly via the helper enforces a deterministic, validated handoff.

The Report is **composed via field-by-field CLI calls**, not emitted as a YAML block in the conversation. The helper validates each field at call-time (enums, required fields, evidence, file existence) and writes the final YAML deterministically when `compose` is called.

**Rules** (apply to every report):

1. **Every required field must be set explicitly.** Call `scripts/lib/detect_report set <field> --value <value>` for each scalar; call `add-package` / `add-language` / `add-framework` / `add-enforcement-tool` for each list entry. The helper rejects `compose` if any required field is unset. "I didn't detect one" is not a valid skip — set the field to `null` (with `--reason` where the helper requires it) or to the appropriate empty value, citing the specific signals checked.

2. **Dep+usage double-check for library-category fields.** For `auth_layer`, `api_client`, `state_management`, `styling`, `routing`, `error_handling`, `validation_library`: run BOTH a dependency-manifest scan AND a source-code usage-pattern grep. Set the field to `null` only when both return empty. If either returns a hit, name the library and pass `--evidence "<dep + usage signal>"`. The helper rejects non-null library-category sets without `--evidence`.

   **Multi-layer rule for `styling`** (and any other field where multiple layers commonly coexist): if 2+ styling technologies are detected together — e.g., a utility framework + a CSS preprocessor (Tailwind + Sass), or a CSS-in-JS library + a global stylesheet system, or a UI component library + custom CSS — list ALL of them in the field value, joined by ` + ` in detection order (most prominent first). Examples: `Tailwind CSS + Sass`, `styled-components + global CSS`, `Tailwind CSS + PostCSS + CSS Modules`. Do NOT pick only the most prominent and drop the rest — downstream `CLAUDE.md` substitutions need the complete layer list to give Claude accurate styling context.

   Canonical usage patterns to grep for the harder-to-detect categories:
   - error_handling: `Either<`, `Result<`, `Maybe<`, `Task<`, `Try<`, `neverthrow`, `purify-ts`, `fp-ts`, `oxide.ts`, `ts-results`, `monet`
   - validation: `zod`, `yup`, `joi`, `ajv`, `pydantic`, `marshmallow`, `class-validator`
   - Use the same pattern for any library category — dep name shortlist + source-grep; never decide "none" from only one check.

3. **Architecture bucket is enumerated.** `architecture_shape` MUST be one of: `layered`, `feature-modular`, `monorepo`, `feature-modular-monorepo`, `clean`, `clean-feature-modular-monorepo`, `hexagonal`, `mvc`, `bloc`, `flat`, `other`. The helper rejects free-form labels (e.g., `"BLoC + use-cases + repositories"` is not valid) at set-time. If no bucket fits, use `other` and document the indicators in `architecture_evidence`.

   **Clean Architecture — specifier signals** (distinguishes `clean` from `hexagonal`): `domain/cases/` or `use-cases/` subfolder within each feature module; repository pattern with interface-in-domain + implementation-in-data split; dependency direction strictly inward (domain imports from nothing; data imports from domain; presentation imports from domain + data adapters). The `cases/` subfolder is the clearest Clean-specific artifact — distinguishes Clean from hexagonal even when both exhibit three-layer structure. When `cases/` is present alongside feature-modular monorepo layout, set `architecture_shape: clean-feature-modular-monorepo`, not `hexagonal`.

4. **Per-package commands are per-package-specific.** Each `add-package` call requires `--build-command` / `--type-check-command` / `--lint-command` / `--test-command` read from THAT package's own `scripts` block (or manifest equivalent). Use `--command-source manifest` when the values come from the package's own scripts. A generic fallback (e.g., `yarn build` applied uniformly) is allowed only if that package's manifest has no scripts AND a language default applies — set `--command-source fallback` in that case.

   **Root-scripts isolation.** Do not infer per-package commands from root / workspace-coordinator scripts when the package manifest contains its own. Root scripts are stack-level only (populate them at the top level via `set build_command`, etc.) and MUST NOT be copied into per-package `add-package` calls. If a package's manifest has its own `scripts.build` etc., pass those verbatim — never fall back to root scripts when the package has its own.

   **No abbreviation.** Call `add-package` once per workspace member, in full — no exceptions, no "similar to above" shortcuts, no name-only summary lists. The helper cross-checks `len(packages) == manifest_count` at compose time and refuses to emit if they differ. Set `manifest_count` once (`set manifest_count --value <N>`) and add exactly N packages. Even for large monorepos (25+, 50+ packages), every record is required.

5. **Workspace members vs utility manifests.** Workspace-member membership requires TWO conditions to both hold:
   - **(a)** The directory matches a workspace-declaration entry (`packages/*` glob, `apps/*` glob, or explicit listing in `package.json` `workspaces` / `pnpm-workspace.yaml` / `lerna.json` / Cargo `[workspace] members` / Go workspace `use`).
   - **(b)** The directory contains a valid manifest file (`package.json`, `Cargo.toml`, `pyproject.toml`, etc.).

   Resolution table:
   - **(a) AND (b)** → call `add-package` for it.
   - **(a) only** (glob-match with no manifest): skip entirely — neither `add-package` nor `optional.utility_manifests`. The directory is an empty placeholder, not a workspace member.
   - **(b) only** (manifest with no workspace declaration, e.g., `scripts/package.json` in a `workspaces: ["packages/*", "apps/*"]` repo): would go in `optional.utility_manifests` — note that today the CLI does not have an `add-utility-manifest` subcommand, so this list is documented in the schema but not populated by MVP. Skip these manifests for now.
   - **Neither**: skip.

   If the repo has no workspace declaration at all, every directory containing a manifest is a package (condition (a) is vacuous). The helper's `add-package` filesystem check rejects hallucinated paths — both `--path` (must be a directory) and `--path/--manifest` (must be a file) are stat'd.

   **Workspace-root exception.** When a workspace declaration exists at the root, the root directory's manifest is included via `add-package` even though the root is not matched by its own member globs (e.g., `workspaces: ["packages/*", "apps/*"]` does not glob-match `.` itself). The root's workspace-coordinator role is sufficient for inclusion. Only applies to repos WITH a workspace declaration; in single-package or non-workspace repos, the root is trivially the sole package.

6. **Wrapper-mode prefix** (`cd SOURCE_ROOT && ...`) applies to per-package commands as well as stack-level commands.

7. **Evidence is required at set-time for library-category fields** (Rule 2 enforces via `--evidence`). For other fields, evidence lives in dedicated fields:
   - `package_manager.evidence` (lockfile path)
   - `frameworks[].evidence` (set via `add-framework --evidence`)
   - `architecture_evidence` (file paths + indicators that justify the chosen `architecture_shape`)

   The helper rejects:
   - `set <library-cat-field> --value <non-null>` without `--evidence`
   - `add-package` with non-existent `--path` or `--path/--manifest`
   - `set runtime_url.value --value null` without `--reason`
   - `set runtime_url.source --value <path>` when the path doesn't exist (use `framework-default` literal if no config detected)

8. **`runtime_url` must read dev-server config** if one is present (`vite.config.ts`, `webpack.config.js` `devServer`, `next.config.js`, `angular.json` `serve`, Django `settings.py` `ALLOWED_HOSTS`, etc.). Set the two sub-fields separately:
   - `set runtime_url.value --value <url>` (or `--value null --reason "<why no web runtime>"` for backend/library projects)
   - `set runtime_url.source --value <config-file-path>` (must exist on disk) — append `: <field-descriptor>` annotation if helpful (e.g., `"vite.config.ts: server.host/port/https"`).
   - Use `--value framework-default` (literal) for `runtime_url.source` ONLY when no dev-server config is detected. Framework defaults (`http://localhost:5173`, etc.) are acceptable only in this case.

9. **README scope — descriptive prose only.** README content is authoritative ONLY where a question in `references/questions.md` explicitly names it as a source (currently: Q1 `PROJECT_DESCRIPTION` quotes README first paragraph). For every other Detection Report field — commands, architecture, package membership, runtime URL, API layer, error handling, etc. — README text is NOT an authoritative source. Structured detection values come from manifests, lockfiles, config files, and spec rules (runner selection, workspace-member rule, dep+usage check, etc.). When README and manifest-based detection agree, cite the manifest evidence; when they conflict, follow the spec rule and ignore the README. Do not let README prose concreteness bias command emission, architecture labeling, or other structured-field population.

### Compose protocol

Phase 1 ends with these calls, in order:

```
scripts/lib/detect_report status      # human-readable list of every field's set/unset state
scripts/lib/detect_report compose     # validate + write .devforge/detection_report.yaml
```

`compose` refuses if:
- Any required scalar is unset (lists every missing path)
- Required lists `languages` or `packages` are empty
- `len(packages) != manifest_count`
- (any prior validation that was deferred to compose)

On success, the helper writes `.devforge/detection_report.yaml` and deletes the intermediate state file. The wizard then proceeds to Phase 2.

### Schema reference

Top-level scalars (set via `detect_report set <name> --value <value>`):

| Field | Type | Notes |
|-------|------|-------|
| `workspace_mode` | enum | `standalone` \| `wrapper` |
| `source_root` | path | `.` for non-wrapper, inner-folder name for wrapper |
| `project_state` | enum | `empty` \| `greenfield` \| `brownfield` |
| `default_branch` | string | from `SOURCE_ROOT/.git` |
| `file_count` | int | files under SOURCE_ROOT (per STEP 1.1 exclusions) |
| `manifest_count` | int | total manifests detected; cross-checked against `len(packages)` at compose |
| `primary_language` | string | one of the `languages[].name` values |
| `monorepo_tool` | enum \| null | `Lerna` \| `Turborepo` \| `Nx` \| `pnpm-workspaces` \| `Cargo-workspace` \| `Go-workspace` \| null |
| `build_tool` | string \| null | e.g., `Vite`, `webpack` |
| `build_command` / `type_check_command` / `lint_command` / `test_runner` | string \| null | stack-level fallbacks |
| `auth_layer` / `api_client` / `state_management` / `styling` / `routing` / `validation_library` | string \| null | library-category — `--evidence` required when non-null |
| `architecture_shape` | enum | 11 values (see Rule 3) |
| `architecture_evidence` | string | file paths + indicators |
| `ci_cd` / `containerization` | string \| null | |

Nested scalars (dotted paths):

| Field | Type | Notes |
|-------|------|-------|
| `package_manager.tool` | string | `npm` \| `yarn` \| `pnpm` \| `bun` \| `pip` \| `poetry` \| `cargo` \| `go` \| ... |
| `package_manager.outer_tool` | string \| null | only set in wrapper mode if outer uses a different pm |
| `package_manager.evidence` | string | lockfile path |
| `error_handling.library` / `error_handling.usage_pattern` | string \| null | |
| `runtime_url.value` | url \| null | `null` requires `--reason` |
| `runtime_url.source` | string \| null | `<config-file-path>` (must exist), `<path>: <fields>`, or `framework-default` literal |

Lists (populated via `add-*` subcommands):

| Field | Subcommand | Notes |
|-------|-----------|-------|
| `languages[]` | `add-language --name <s> --file-count <n> --runtime <s>` | required ≥1 |
| `frameworks[]` | `add-framework --name <s> --role <enum> --evidence <s>` | role: `frontend` \| `backend` \| `library` \| `plugin` |
| `enforcement_tooling[]` | `add-enforcement-tool --value <s>` | e.g., `Husky (pre-commit)`, `lint-staged` |
| `packages[]` | `add-package --path <dir> --manifest <file> --language-hint <s> [--framework-hint <s>] [--build-command <s>] [--type-check-command <s>] [--lint-command <s>] [--test-command <s>] --command-source {manifest\|fallback}` | required ≥1; path + path/manifest must exist on disk; `len(packages)` must equal `manifest_count` at compose |

After `compose` succeeds, proceed to Phase 2 (`references/questions.md`). Phase 3 (`references/populate.md`) reads `.devforge/detection_report.yaml` when populating `.devforge/project-config.json`; the mapping from report fields to config fields is defined there.

---

Detection phase complete. Proceed to Phase 2 (`references/questions.md`).
