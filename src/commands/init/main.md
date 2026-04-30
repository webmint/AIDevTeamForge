---
name: init
description: Bootstrap project — captures structural fields, hands off to /generate-docs
disable-model-invocation: true
model: sonnet
---

# /init — Project Bootstrap

`/init` captures five structural fields about the target project and persists them to `.devforge/init.yaml` via the `.devforge/lib/init_helper` setter helpers. It performs no classification — no language inference, no framework detection, no library categorization, no architectural shape inference. Those fields stay at their helper-default empty values; later commands populate them.

## Outputs of this phase

- `project_root` — directory the framework operates on, relative to the install root. `.` for standalone (project and install share the root); inner folder name for wrapper mode (e.g., `client-project`)
- `workspace_mode` — install layout: `standalone` or `wrapper`
- `project_state` — codebase maturity: `empty` or `brownfield`
- `default_branch` — git default branch name (e.g., `main`)
- `packages_detected` — array of per-package records: `{ path, manifest }`; `path` is the package folder relative to project root (or `.` for projects without distinct packages); empty `[]` for projects without manifests

## Preflight — Reset helper state

```bash
.devforge/lib/init_helper reset
```

The helper creates `.devforge/` when absent and writes a fresh defaults file (every schema field reset to its null/empty default) — on re-runs, any previously persisted data is discarded.

## Step 1: Workspace Mode Detection

Determines `workspace_mode` and `project_root` by asking the user, then drilling into source-root resolution only when the project is a wrapper workspace.

### 1.1: Ask Workspace Mode

Use AskUserQuestion: "Is this a standalone project, or a wrapper workspace around a client project folder?"
- `Standalone project` (Recommended)
- `Wrapper workspace`

**If the user picks `Standalone project`:** invoke `.devforge/lib/init_helper set-workspace-mode standalone` then `.devforge/lib/init_helper set-project-root .`. Step 1 is complete; skip §1.2.

**If the user picks `Wrapper workspace`:** proceed to §1.2.

### 1.2: Resolve Wrapper Source Root

This substep runs only in the wrapper case. It scans for nested git repositories to suggest the source root, then has three branches based on the candidate count: exactly one, zero, or multiple.

Invoke `.devforge/lib/init_helper find-nested-git` to enumerate directories at depth 1 (direct children of the install root) that contain a `.git/` directory. The helper applies its built-in skip rules (hidden directories plus a fixed list of common dependency / build directories — see `NESTED_GIT_SKIP` in the helper for the authoritative set) and returns the candidate list.

**If exactly one nested `.git` directory is found:**
Use AskUserQuestion (replace `<folder-name>` with the path from the scan above): "I found a nested git repository at `<folder-name>/`. Is this the wrapper's source root?"
- `Yes` — wrapper around `<folder-name>` (Recommended)
- `No` — the source root is a different folder

If `Yes`, invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <folder-name>`. If `No`, follow up with a plain free-text prompt: "Which folder contains the client's source code?", then invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <answer>`.

**If zero nested `.git` directories are found:**
Use a plain free-text prompt: "Which folder contains the client's source code?", then invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <answer>`.

**If two or more nested `.git` directories are found:**
Use AskUserQuestion (replace each `<folder-N>` with the corresponding path from the scan above; omit option lines that have no corresponding candidate): "I found multiple nested git repositories. Which folder is the wrapper's primary source root?"
- `<folder-1>` (Recommended)
- `<folder-2>`
- `<folder-3>`
- `None of these — let me type the path`

If the user picks `<folder-N>`, invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <folder-N>`. If the user picks `None of these`, follow up with a plain free-text prompt: "Which folder contains the client's source code?", then invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <answer>`.

**Multi-root rejection:** If a free-text answer in this substep names more than one folder (e.g., separated by `and`, `&`, or a comma between path-like tokens — illustrative, not exhaustive; lean toward triggering when ambiguous, since a false-positive costs one re-prompt while a false-negative corrupts `project_root`), reply in first person: "I noticed your answer names more than one folder. Multi-root coordination across nested repos isn't supported — please name a single primary source root." Then re-issue the same free-text prompt: "Which folder contains the client's source code?". Allow up to 2 retries (3 total attempts). After the third invalid answer, extract the first folder from the most recent answer by splitting on the same multi-root separators (`and`, `&`, comma, whitespace between path-like tokens) and taking the leading non-empty token (strip a trailing slash if present). Warn the user ("I'll proceed with `<first-folder>`; re-run `/init` if that's wrong"), then invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <first-folder>`.

## Step 2: Project State Classification

Reads the `project_root` resolved by Step 1 and classifies the project as `empty` or `brownfield`. The check is mechanical — no AskUserQuestion, no judgment about scaffold signatures or codebase maturity.

**Ignore when judging emptiness:** any dot-prefixed entry (file or directory — covers `.git/`, `.devforge/`, `.claude/`, IDE configs like `.idea/` and `.vscode/`, OS metadata like `.DS_Store`, dot-files like `.gitignore`, etc.) and the literal files `CLAUDE.md` and `constitution.md` (framework-installed at the project root).

**Standalone case** (`workspace_mode = standalone`, `project_root = .`): list the install root's top-level entries. If every entry is in the ignore set above, classify as `empty`. Otherwise classify as `brownfield`.

**Wrapper case** (`workspace_mode = wrapper`, `project_root = <folder-name>`): if the folder is absent, classify as `empty`. If the folder is present and every top-level entry is in the ignore set above, classify as `empty`. Otherwise classify as `brownfield`.

After classification, invoke `.devforge/lib/init_helper set-project-state <empty|brownfield>`.

## Step 3: Default Branch Detection

Detect first; ask only if detection fails. Run these git probes inside `project_root` (use `git -C` so wrapper mode targets the resolved root, not the install root) in order, stopping at the first that produces a branch name:

1. `git symbolic-ref refs/remotes/origin/HEAD` — canonical when a remote is configured. Parse the trailing segment of `refs/remotes/origin/<name>`.
2. `git symbolic-ref HEAD` — fallback for repos without a remote. Parse the trailing segment of `refs/heads/<name>`.
3. `git branch --show-current` — final git-based fallback. Returns the current branch name on stdout.

For all three probes, treat any non-zero exit (missing directory, non-git workspace, detached HEAD) or empty stdout as "no result" — fall through to the next probe.

**If a branch name was produced:** invoke `.devforge/lib/init_helper set-default-branch <name>`.

**If all three probes produced no result**, use AskUserQuestion: "I couldn't detect the default branch from git. What is it?"
- `main` (Recommended)
- `master`
- `None of these — let me type the name`

If the user picks `main` or `master`, invoke `.devforge/lib/init_helper set-default-branch <choice>`. If the user picks `None of these`, follow up with a plain free-text prompt: "What's the default branch name?", then invoke `.devforge/lib/init_helper set-default-branch <answer>`.

## Step 4: Discover packages

Walk the directory tree under `project_root` (depth limit 4 — covers typical monorepo nesting like `apps/<name>/` or `packages/<scope>/<sub>/`) for any standard package-manifest file (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pubspec.yaml`, `Gemfile`, `*.gemspec`, `composer.json`, `mix.exs`, `build.gradle`, `build.gradle.kts`, `pom.xml`, `*.csproj` — use your knowledge of which ecosystem uses which). Skip dependency / build / hidden directories (e.g., `node_modules/`, `vendor/`, `target/`, `build/`, `dist/`, `.venv/`, `venv/`, `__pycache__/`, and any directory whose name starts with `.`).

If you encounter a file whose ecosystem you cannot confidently identify as a recognized package manifest, skip it rather than calling `add-package` — a missing entry is recoverable by a re-run, but a misclassified entry corrupts the canonical package index that downstream commands consume.

For each manifest, invoke `.devforge/lib/init_helper add-package --path <package-dir-relative-to-project-root> --manifest <filename>`. If no manifests are found (which includes the empty-project case per Step 2), `packages_detected` stays `[]`.

## Closing

`/init` is complete; the five fields are persisted in `.devforge/init.yaml`. Tell the user: "Run `/generate-docs` next."
