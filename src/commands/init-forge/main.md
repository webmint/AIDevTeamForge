---
name: init-forge
description: Bootstrap project — captures structural fields, hands off to /devforge:generate-docs
disable-model-invocation: true
---

# /devforge:init-forge — Project Bootstrap

`/devforge:init-forge` captures five structural fields about the target project and persists them to `.devforge/init.yaml` via the `.devforge/lib/init_helper` setter helpers. It performs no classification — no language inference, no framework detection, no library categorization, no architectural shape inference. Those fields stay at their helper-default empty values; later commands populate them.

## Outputs of this phase

- `project_root` — directory the framework operates on, relative to the install root. `.` for standalone (project and install share the root); inner folder name for wrapper mode (e.g., `client-project`)
- `workspace_mode` — install layout: `standalone` or `wrapper`
- `project_state` — codebase maturity: `empty` or `brownfield`
- `default_branch` — git default branch name (e.g., `main`)
- `packages_detected` — array of per-package records: `{ path, manifest }`; `path` is the package folder relative to project root (or `.` for projects without distinct packages); `manifest` is the package's manifest filename, or `null` for a manifest-less package registered at Step 4; empty `[]` when Step 4 registers no package
- `.devforge/index.json` — machine-readable per-package structural index (file listings, manifest scripts, manifest deps); produced by Step 6's `build-index`
- `docs/structure.md` — human-readable workspace map; produced by Step 6's `build-index`

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

**If the user hands this choice back to you** ("you decide", "up to you", or the same in any language — including one typed as free text instead of an option): take `Standalone project`, apply it exactly as above, and name it in Step 5's delegated-values lines.

### 1.2: Resolve Wrapper Source Root

This substep runs only in the wrapper case. It scans for nested git repositories to suggest the source root, then has three branches based on the candidate count: exactly one, zero, or multiple.

Invoke `.devforge/lib/init_helper find-nested-git` to enumerate directories at depth 1 (direct children of the install root) that contain a `.git/` directory. The helper applies its built-in skip rules (hidden directories plus a fixed list of common dependency / build directories — see `NESTED_GIT_SKIP` in the helper for the authoritative set) and returns the candidate list.

**If exactly one nested `.git` directory is found:**
Use AskUserQuestion (replace `<folder-name>` with the path from the scan above): "I found a nested git repository at `<folder-name>/`. Is this the wrapper's source root?"
- `Yes` — wrapper around `<folder-name>` (Recommended)
- `No` — the source root is a different folder

If `Yes`, invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <folder-name>`. If `No`, follow up with a plain free-text prompt: "Which folder contains the client's source code?", then invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <answer>`. If the user hands this choice back to you, take `Yes`, apply it exactly as above, and name it in Step 5's delegated-values lines.

**If zero nested `.git` directories are found:**
Use a plain free-text prompt: "Which folder contains the client's source code?", then invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <answer>`.

**If two or more nested `.git` directories are found:**
Use AskUserQuestion (replace each `<folder-N>` with the corresponding path from the scan above; omit option lines that have no corresponding candidate): "I found multiple nested git repositories. Which folder is the wrapper's primary source root?"
- `<folder-1>` (Recommended)
- `<folder-2>`
- `<folder-3>`
- `None of these — let me type the path`

If the user picks `<folder-N>`, invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <folder-N>`. If the user picks `None of these`, follow up with a plain free-text prompt: "Which folder contains the client's source code?", then invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <answer>`. If the user hands this choice back to you, take `<folder-1>`, apply it exactly as above, and name it in Step 5's delegated-values lines.

**Multi-root rejection:** If a free-text answer in this substep names more than one folder (e.g., separated by `and`, `&`, or a comma between path-like tokens — illustrative, not exhaustive; lean toward triggering when ambiguous, since a false-positive costs one re-prompt while a false-negative corrupts `project_root`), reply in first person: "I noticed your answer names more than one folder. Multi-root coordination across nested repos isn't supported — please name a single primary source root." Then re-issue the same free-text prompt: "Which folder contains the client's source code?". Allow up to 2 retries (3 total attempts). After the third invalid answer, extract the first folder from the most recent answer by splitting on the same multi-root separators (`and`, `&`, comma, whitespace between path-like tokens) and taking the leading non-empty token (strip a trailing slash if present). Warn the user ("I'll proceed with `<first-folder>`; re-run `/devforge:init-forge` if that's wrong"), then invoke `.devforge/lib/init_helper set-workspace-mode wrapper` then `.devforge/lib/init_helper set-project-root <first-folder>`.

**Delegated folder answer:** A reply to the free-text prompt "Which folder contains the client's source code?" that hands the answer back to you is not a folder name — never pass it to `set-project-root`. That prompt runs only after the user rejected every detected candidate or when none was found, so there is no value to apply on their behalf: ask the same prompt once more, and if the second reply again names no folder, end the turn without invoking `set-workspace-mode` or `set-project-root`, telling the user to re-run `/devforge:init-forge` once they know which folder holds the client's source code.

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

If the user hands this choice back to you, take `main`, apply it exactly as above, and name it in Step 5's delegated-values lines. A reply to the free-text prompt "What's the default branch name?" that hands the answer back to you is not a branch name — never pass it to `set-default-branch`; that prompt runs only after the user rejected `main` and `master`, so ask it once more, and if the second reply again names no branch, end the turn without invoking `set-default-branch`, telling the user to re-run `/devforge:init-forge` once they know the default branch name.

## Step 4: Discover packages

Registers the packages under `project_root` in three passes: directories holding a recognized package manifest (§4.1), manifest-less candidates the helper detects (§4.2), and manifest-less directories the user declares (§4.3). §4.2 and §4.3 register with `add-package --no-manifest`, which records `manifest: null`. When an `add-package --no-manifest` call exits non-zero, surface its stderr to the user and move on — the helper leaves `init.yaml` unchanged for that path, and re-running `/devforge:init-forge` asks again. `packages_detected` stays `[]` only when no pass registers a package.

### 4.1: Walk Package Manifests

Walk the directory tree under `project_root` (depth limit 4 — covers typical monorepo nesting like `apps/<name>/` or `packages/<scope>/<sub>/`) for any standard package-manifest file (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pubspec.yaml`, `Gemfile`, `*.gemspec`, `composer.json`, `mix.exs`, `build.gradle`, `build.gradle.kts`, `pom.xml`, `*.csproj` — use your knowledge of which ecosystem uses which). Skip dependency / build / hidden directories (e.g., `node_modules/`, `vendor/`, `target/`, `build/`, `dist/`, `.venv/`, `venv/`, `__pycache__/`, and any directory whose name starts with `.`).

If you encounter a file whose ecosystem you cannot confidently identify as a recognized package manifest, skip it rather than calling `add-package` — a missing entry is recoverable by a re-run, but a misclassified entry corrupts the canonical package index that downstream commands consume.

For each manifest, invoke `.devforge/lib/init_helper add-package --path <package-dir-relative-to-project-root> --manifest <filename>`.

If Step 2 classified the project as `empty`, Step 4 ends here — skip §4.2 and §4.3.

### 4.2: Register Manifest-less Candidates

Invoke `.devforge/lib/init_helper detect-manifest-less` to propose manifest-less package directories. It detects one kind — Terraform root modules, recognized by their `*.tf` files — and never proposes a registered package or a directory inside a registered package other than `.` (see `cmd_detect_manifest_less` in the helper for the authoritative rules). It writes no state and prints one candidate path per line, relative to `project_root`, sorted; exit 0 with no output means no candidate.

**If the helper exits non-zero:** surface its stderr to the user verbatim and continue at §4.3 without a candidate question.

**If it printed no candidate:** continue at §4.3.

**If it printed one or more candidates:**
Use AskUserQuestion (replace `<candidates>` with every path the helper printed, each in backticks, comma-separated — the list can run past four entries, so the candidates go in the question text and never become options): "I found directories holding Terraform `*.tf` files that are not registered as packages: <candidates>. Should I register them as packages with no manifest?"
- `Register all` (Recommended)
- `Let me choose which`
- `Register none`

If the user picks `Register all`, invoke `.devforge/lib/init_helper add-package --path <candidate> --no-manifest` for each candidate. If the user picks `Let me choose which`, follow up with a plain free-text prompt: "Which of the listed directories should I register?", then invoke `.devforge/lib/init_helper add-package --path <candidate> --no-manifest` for each named directory that is on the candidate list; skip any named directory that is not, and tell the user it was skipped. If the user picks `Register none`, register no candidate. If the user hands this choice back to you ("you decide", "up to you", or the same in any language — including one typed as free text instead of an option): take `Register all`, apply it exactly as above, and name it in Step 5's delegated-values lines.

A reply to the free-text prompt "Which of the listed directories should I register?" that hands the answer back to you names no directory — never pass it to `add-package`. Ask the prompt once more, and if the second reply again hands it back, apply `Register all` exactly as above and name it in Step 5's delegated-values lines. Unlike Step 3's free-text prompt, which ends the turn on a second hand-back, this prompt has a value to apply on the user's behalf: the detected candidates.

### 4.3: Declare Other Package Directories

Some package kinds have no file that reliably marks them — SQL procedure trees and workflow-definition YAML among them (`*.yaml` files, for one, are common across a repo, so a YAML marker would propose far too many directories). The user declares such directories instead.

Use AskUserQuestion: "Does the project have other package directories with no manifest file — for example a tree of SQL procedures or a folder of workflow-definition YAML?"
- `No other directories` (Recommended)
- `Yes — let me type the paths`

If the user picks `No other directories`, register nothing. If the user picks `Yes — let me type the paths`, follow up with a plain free-text prompt: "Which directories should I register? Give each path relative to the project root.", then invoke `.devforge/lib/init_helper add-package --path <path> --no-manifest` for each path the reply names. If the user hands this choice back to you, take `No other directories`, apply it exactly as above, and name it in Step 5's delegated-values lines.

A reply to the free-text prompt "Which directories should I register? Give each path relative to the project root." that hands the answer back to you names no directory — never pass it to `add-package`. Ask the prompt once more, and if the second reply again hands it back, register nothing from it and continue with Step 5 — do not end the turn.

## Step 5: Render Summary

Renders the persisted state from `.devforge/init.yaml` so the user can verify the captured fields before handoff to `/devforge:generate-docs`.

Invoke `.devforge/lib/init_helper summary`. The helper reads `.devforge/init.yaml` and prints a deterministic, human-readable report to stdout. After the helper runs, copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase).

**Delegated-values lines.** Below the fenced block, name each value this run applied because the user handed its question back to you in Step 1, Step 3 or Step 4, one line per field in the form `<field>: <value> — applied by default — you delegated`. Step 4's delegated values all belong to `packages_detected` and share its one line: the `<value>` lists the candidates registered on a §4.2 hand-back, and adds `No other directories` when the §4.3 question was handed back. When the user handed back no question, add no such line.

## Step 6: Build the structural index

After `init.yaml` is fully populated (all five fields set + `packages_detected[]` populated), invoke `index_helper build-index` to produce two artifacts the downstream commands rely on:

```bash
.devforge/lib/index_helper build-index
```

Exit code 0 is required. The helper:

- Reads `.devforge/init.yaml` to get the workspace package list
- For each package, walks the source tree (capped at 10000 files per package — `_MAX_FILES_PER_PACKAGE` in the helper), looks for a manifest file in the package directory by name (`package.json` / `Cargo.toml` / `pyproject.toml` / `go.mod` / `pom.xml` / `build.gradle` / `build.gradle.kts` / `*.csproj` / `composer.json` / `Gemfile` / `requirements.txt`) whatever `manifest` value `init.yaml` records for the package — `null` included — and extracts manifest scripts + manifest dependencies when it finds one; where it finds none, the package's index record carries no manifest, scripts or dependencies
- Writes `.devforge/index.json` (machine-readable per-package structural data) and `docs/structure.md` (human-readable workspace map)

Both writes are atomic. Re-running `build-index` is idempotent: byte-identical output across re-runs on stable input (modulo the `generated_at` timestamp).

If the helper exits non-zero, surface the stderr to the user and stop — `/devforge:init-forge` is incomplete without the index. The error is most likely one of:

- `.devforge/init.yaml` is missing or malformed → re-run `/devforge:init-forge` from the start
- A `packages_detected[]` entry points at a path that no longer exists → user reconciles, then retries
- A package's manifest file is malformed (e.g., invalid JSON in `package.json`) → the helper emits `"manifest_parse_skipped": true` for that package and continues; not a hard failure

Verify both artifacts landed:

```bash
test -f .devforge/index.json && echo "index.json exists" || echo "MISSING"
test -f docs/structure.md && echo "structure.md exists" || echo "MISSING"
```

## Step 7: Verify

```bash
.devforge/lib/init_helper verify
```

Cross-checks `.devforge/init.yaml` + `.devforge/index.json` + `docs/structure.md`: required fields populated, `packages_detected` consistent with on-disk manifests at depth ≤2 under `project_root`, both index artifacts present. Exit 0 = pass; exit 2 = stderr enumerates violations (`verify: <field>: <reason>` per line). On exit 2, surface stderr verbatim and re-run the corresponding setter (`set-workspace-mode` / `set-project-root` / etc.) before re-attempting; if `packages_detected` is the issue, re-walk Step 4.

## Closing

`/devforge:init-forge` is complete. The five structural fields are persisted in `.devforge/init.yaml`, and the structural index is materialized at `.devforge/index.json` + `docs/structure.md`. Tell the user: "Run `/devforge:generate-docs` next."
