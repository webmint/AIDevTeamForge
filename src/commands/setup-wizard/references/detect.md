# Detection

This reference defines the detection phase of `/setup-wizard`. Detection inspects the project read-only via filesystem scans; writes are confined to `.devforge/`. The phase populates `.devforge/detection_report.yaml` incrementally via `.devforge/lib/detect_report` setter subcommands, with each user answer immediately persisted to the report file before the next prompt. Later phases read the completed file directly — no conversational-memory handoff for structured detection values.

## Outputs of this phase

- `project_root` — directory the framework operates on, relative to the install root. `.` for standalone (project and install share the root); inner folder name for wrapper mode (e.g., `client-project`)
- `workspace_mode` — install layout: `standalone` or `wrapper`
- `project_state` — codebase maturity: `empty` or `brownfield`
- `default_branch` — git default branch name (e.g., `main`)
- `packages_detected` — array of per-package records: `{ path, manifest }`; defines the canonical package index (record position = package identifier); `path` is the package folder relative to project root (or `.` for projects without distinct packages); empty `[]` for projects without manifests
- `languages` — array of `{ value, path }` per package (`value` = language; ordered to match `packages_detected`)
- `frameworks` — array of `{ value, path }` per package (`value` = framework; `"N/A"` if no framework, `null` if unresolvable; ordered to match `packages_detected`)
- `build_tools` — array of `{ value, path }` per package (`value` = build tool, e.g. `"Vite"`, `"Cargo"`, `"Poetry"`; `"N/A"` if no build step, `null` if unresolvable; ordered to match `packages_detected`)
- `build_commands` — array of `{ value, path }` per package (`value` = build command, e.g. `"npm run build"`, `"cargo build"`; `"N/A"` if no build step, `null` if unresolvable; ordered to match `packages_detected`)
- `type_check_commands` — array of `{ value, path }` per package (`value` = type-check command, e.g. `"tsc --noEmit"`, `"mypy ."`, `"cargo check"`; `"N/A"` if no type checker, `null` if unresolvable; ordered to match `packages_detected`)
- `lint_commands` — array of `{ value, path }` per package (`value` = lint command, e.g. `"eslint ."`, `"ruff check ."`, `"cargo clippy"`; `"N/A"` if no linter, `null` if unresolvable; ordered to match `packages_detected`)
- `primary_language` — the project's main language (string; equals the most-common value in `languages`, ties broken by `packages_detected` order; user-overridable)
- Field types, value spaces, and case conventions are owned by the `.devforge/lib/detect_report` helper; its subcommand specs define them when added. Inline examples above illustrate expected shape, not an exhaustive enum.

## Step 1: Workspace Mode Detection

Determines `workspace_mode` and `project_root` by asking the user, then drilling into source-root resolution only when the project is a wrapper workspace.

### 1.1: Ask Workspace Mode

Use AskUserQuestion: "Is this a standalone project, or a wrapper workspace around a client project folder?"
- `Standalone project` (Recommended)
- `Wrapper workspace`

**If the user picks `Standalone project`:** invoke `.devforge/lib/detect_report set-workspace-mode standalone` then `.devforge/lib/detect_report set-project-root .`. Step 1 is complete; skip §1.2.

**If the user picks `Wrapper workspace`:** proceed to §1.2.

### 1.2: Resolve Wrapper Source Root

This substep runs only in the wrapper case. It scans for nested git repositories to suggest the source root, then has three branches based on the candidate count: exactly one, zero, or multiple.

Invoke `.devforge/lib/detect_report find-nested-git` to enumerate directories at depth 1 (direct children of the install root) that contain a `.git/` directory. The helper applies its built-in skip rules (hidden directories plus a fixed list of common dependency / build directories — see `NESTED_GIT_SKIP` in the helper for the authoritative set) and returns the candidate list.

**If exactly one nested `.git` directory is found:**
Use AskUserQuestion (replace `<folder-name>` with the path from the scan above): "I found a nested git repository at `<folder-name>/`. Is this the wrapper's source root?"
- `Yes, wrapper around <folder-name>` (Recommended)
- `No, the source root is a different folder`

If `Yes`, invoke `.devforge/lib/detect_report set-workspace-mode wrapper` then `.devforge/lib/detect_report set-project-root <folder-name>`. If `No`, follow up with a plain free-text prompt: "Which folder contains the client's source code?", then invoke `.devforge/lib/detect_report set-workspace-mode wrapper` then `.devforge/lib/detect_report set-project-root <answer>`.

**If zero nested `.git` directories are found:**
Use a plain free-text prompt: "Which folder contains the client's source code?", then invoke `.devforge/lib/detect_report set-workspace-mode wrapper` then `.devforge/lib/detect_report set-project-root <answer>`.

**If two or more nested `.git` directories are found:**
Use AskUserQuestion (replace each `<folder-N>` with the corresponding path from the scan above; omit option lines that have no corresponding candidate): "I found multiple nested git repositories. Which folder is the wrapper's primary source root?"
- `Wrapper around <folder-1>` (Recommended)
- `Wrapper around <folder-2>`
- `Wrapper around <folder-3>`
- `None of these — let me type the path`

If the user picks `Wrapper around <folder-N>`, invoke `.devforge/lib/detect_report set-workspace-mode wrapper` then `.devforge/lib/detect_report set-project-root <folder-N>`. If the user picks `None of these`, follow up with a plain free-text prompt: "Which folder contains the client's source code?", then invoke `.devforge/lib/detect_report set-workspace-mode wrapper` then `.devforge/lib/detect_report set-project-root <answer>`.

**Multi-root rejection:** If a free-text answer in this substep names more than one folder (e.g., separated by `and`, `&`, or a comma between path-like tokens — illustrative, not exhaustive; lean toward triggering when ambiguous, since a false-positive costs one re-prompt while a false-negative corrupts `project_root`), reply in first person: "I noticed your answer names more than one folder. Multi-root coordination across nested repos isn't supported — please name a single primary source root." Then re-issue the same free-text prompt: "Which folder contains the client's source code?". Allow up to 2 retries (3 total attempts). After the third invalid answer, extract the first folder from the most recent answer by splitting on the same multi-root separators (`and`, `&`, comma, whitespace between path-like tokens) and taking the leading non-empty token (strip a trailing slash if present). Warn the user ("I'll proceed with `<first-folder>`; re-run `/setup-wizard` if that's wrong"), then invoke `.devforge/lib/detect_report set-workspace-mode wrapper` then `.devforge/lib/detect_report set-project-root <first-folder>`.

## Step 2: Project State Classification

Reads the `project_root` resolved by Step 1 and classifies the project as `empty` or `brownfield`. The check is mechanical — no AskUserQuestion, no judgment about scaffold signatures or codebase maturity.

**Ignore when judging emptiness:** any dot-prefixed entry (file or directory — covers `.git/`, `.devforge/`, `.claude/`, IDE configs like `.idea/` and `.vscode/`, OS metadata like `.DS_Store`, dot-files like `.gitignore`, etc.) and the literal files `CLAUDE.md` and `constitution.md` (framework-installed at the project root).

**Standalone case** (`workspace_mode = standalone`, `project_root = .`): list the install root's top-level entries. If every entry is in the ignore set above, classify as `empty`. Otherwise classify as `brownfield`.

**Wrapper case** (`workspace_mode = wrapper`, `project_root = <folder-name>`): if the folder is absent, classify as `empty`. If the folder is present and every top-level entry is in the ignore set above, classify as `empty`. Otherwise classify as `brownfield`.

After classification, invoke `.devforge/lib/detect_report set-project-state <empty|brownfield>`.

## Step 3: Default Branch Detection

Detect first; ask only if detection fails. Run these git probes inside `project_root` (use `git -C` so wrapper mode targets the resolved root, not the install root) in order, stopping at the first that produces a branch name:

1. `git symbolic-ref refs/remotes/origin/HEAD` — canonical when a remote is configured. Parse the trailing segment of `refs/remotes/origin/<name>`.
2. `git symbolic-ref HEAD` — fallback for repos without a remote. Parse the trailing segment of `refs/heads/<name>`.
3. `git branch --show-current` — final git-based fallback. Returns the current branch name on stdout.

For all three probes, treat any non-zero exit (missing directory, non-git workspace, detached HEAD) or empty stdout as "no result" — fall through to the next probe.

**If a branch name was produced:** invoke `.devforge/lib/detect_report set-default-branch <name>`.

**If all three probes produced no result**, use AskUserQuestion: "I couldn't detect the default branch from git. What is it?"
- `main` (Recommended)
- `master`
- `None of these — let me type the name`

If the user picks `main` or `master`, invoke `.devforge/lib/detect_report set-default-branch <choice>`. If the user picks `None of these`, follow up with a plain free-text prompt: "What's the default branch name?", then invoke `.devforge/lib/detect_report set-default-branch <answer>`.

## Step 4: Per-Package Stack Detection

For each manifest found inside `project_root`, classify its package's language, framework, build tool, and the three lifecycle commands (build, type-check, lint). Use ecosystem knowledge — don't invent values you can't ground in the package's manifest, dev-deps, or language convention.

### 4.1: Discover packages

Walk the directory tree under `project_root` (depth limit 4 — covers typical monorepo nesting like `apps/<name>/` or `packages/<scope>/<sub>/`) for any standard package-manifest file (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pubspec.yaml`, `Gemfile`, `*.csproj`, etc. — use your knowledge of which ecosystem uses which). Skip dependency / build / hidden directories (e.g., `node_modules/`, `vendor/`, `target/`, `build/`, `dist/`, `.venv/`, `venv/`, `__pycache__/`, and any directory whose name starts with `.`).

For each manifest, invoke `.devforge/lib/detect_report add-package --path <package-dir-relative-to-project-root> --manifest <filename>`. If no manifests are found (which includes the empty-project case per Step 2), `packages_detected` stays `[]`.

### 4.2: Classify each package

If `packages_detected` is empty, there's nothing to iterate over — skip this substep.

For each package, determine and persist six fields. Read from the package's own manifest, its dev-deps, its lockfile (when relevant), and a quick sample of source files when extension counts disambiguate.

**Language** — derived from manifest type and sibling files (e.g., `package.json` + `tsconfig.json` → TypeScript; `package.json` without → JavaScript). Skip the `add-language` call for a package only if you can't identify its language at all. Persist via `add-language --path <p> --value <language>`.

**Framework** — parse the manifest's top-level dependencies for app-level frameworks: things that structure the application (router, request handler, UI tree, lifecycle). NOT utility libraries, test runners, build tools, linters, ORMs, or database clients. If multiple frameworks compose at the app level (e.g., Next.js with tRPC), pick the outermost — the one a developer would name first if asked "what's this built on?". If the package is a library or service with no app framework → `--value "N/A"`. If a marker is present but you don't recognize the framework → `--null` rather than guess. Persist via `add-framework`.

**Build tool, build command, type-check command, lint command** — each resolved in this priority: (1) manifest-declared script if one names the operation (e.g., `package.json scripts.build`); (2) the language ecosystem's standard tool (e.g., `cargo build` for Rust, `mypy` / `ruff` for Python); (3) `--null` if neither applies. Use `--value "N/A"` when no such tool/command exists for this package after inspection — language convention is the default (e.g., a Ruby package with no static type checker installed; plain JavaScript with no TypeScript dep), but a detected tool always wins (e.g., a Ruby package with `sorbet` in its `Gemfile` gets the `sorbet` type-check command, not `"N/A"`). For commands invoked via a runner (JS/TS, Python, Ruby), pick the runner from lockfile presence first, the manifest's runner field second; if neither signals a runner, persist the bare tool name (e.g., `tsc --noEmit`, not `npx tsc --noEmit`) and let runtime invocation resolve from PATH. Persist the command as it would run from the package's own directory; working-directory composition (cd-ing into the package's `path`) is the runtime's concern, not detection's. Persist via the corresponding `add-*` subcommand.

### 4.3: Pick primary_language

After all packages are classified, determine `primary_language`:

- If `packages_detected` is empty: skip — leave `primary_language` as its default (`null`).
- Otherwise: the most-common value across `languages[].value` wins. Ties broken by `packages_detected` order (first package wins). Persist via `set-primary-language <value>`.

## Step 5: Detection Summary & Approval Gate

This step renders Phase 1's persisted state to the user and asks for approval before handoff.

Render the summary by reading `.devforge/detection_report.yaml` (the file the prior steps have been writing to). Print a `key: value` summary, one line per field, in the order listed under "Outputs of this phase" above (12 fields total).

**If `project_state` is `empty`:** the per-package fields (`packages_detected`, `languages`, `frameworks`, `build_tools`, `build_commands`, `type_check_commands`, `lint_commands`, `primary_language`) are `[]` / `null` by design — no manifests to detect. Frame the summary as success and note: "Project is empty — `workspace_mode`, `project_root`, `default_branch`, and `project_state` are set; per-package fields are intentionally empty and will be filled in Phase 2 when you specify the intended stack."

After the summary is rendered, use AskUserQuestion: "Detection complete — does this look right?"
- `Looks right — proceed to Phase 2` (Recommended)
- `Restart detection — reset and re-run from Step 1`

**If the user picks `Looks right`:** Phase 1 is complete. Hand off to Phase 2.

**If the user picks `Restart detection`** (or replies with anything other than `Looks right`), invoke `.devforge/lib/detect_report reset` to clear the persisted state, then re-run Steps 1 through 4 in order (in-place loop within this reference; `main.md` preflight steps are NOT re-run). Allow up to 2 restarts (3 total Phase 1 runs at this gate). After the third arrival at this gate, the gate becomes proceed-only (only `Looks right` remains) — detection won't re-run a fourth time. If a value is still wrong, the user can edit `.devforge/detection_report.yaml` manually after the wizard finishes.
