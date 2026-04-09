# /refresh-docs — Refresh Stale Documentation

Detects source files that changed since documentation was last updated and invokes the tech-writer to update only the affected docs. Lightweight alternative to `/onboard` — targets the delta, not the full codebase.

## Usage
```
/refresh-docs                      # auto-detect changes since last docs update
/refresh-docs --since abc1234      # diff from a specific commit
/refresh-docs --module auth        # refresh docs for a specific module only
/refresh-docs --all                # full rescan (equivalent to re-running /onboard)
```

## Arguments
- `$ARGUMENTS` — Controls scope of the refresh:
  - **Empty**: Auto-detect. Finds the last commit that touched `docs/` and diffs source files from there to HEAD.
  - **`--since <commit>`**: Manual override. Diff source files from the given commit to HEAD.
  - **`--module <name>`**: Refresh docs for a specific module/directory only. Scans all source files in that module regardless of git history.
  - **`--all`**: Full rescan of the entire codebase. Delegates to `/onboard` (which already preserves existing docs via its rule 7). Use when docs are severely out of date.

## When to Use

| Situation | Command |
|-----------|---------|
| First time documenting a codebase | `/onboard` |
| Docs are slightly stale (a few tasks ran without doc updates) | **`/refresh-docs`** |
| Docs are severely out of date (many features behind) | `/refresh-docs --all` |
| Just completed a single task | Phase 5 of `/execute-task` handles this |
| Verification flagged missing docs | `/finalize` handles feature docs, or run `/refresh-docs` directly |

## Prerequisites

1. `docs/` folder must exist (created by `/setup-wizard` or `/onboard`)
2. Project must be a git repository
3. `CLAUDE.md` must exist (for Source Root and project context)

If `docs/` does not exist, inform the user: "No docs/ folder found. Run `/onboard` first to generate initial documentation, then use `/refresh-docs` for incremental updates."

## PHASE 1: Detect Changes

### 1.1: Load Context

Read:
1. `CLAUDE.md` — project name, Source Root, framework, dev commands
2. `constitution.md` — if it exists, for architecture rules context
3. `.claude/memory/MEMORY.md` — for any relevant notes

Determine the **Source Root** from `CLAUDE.md`. If Source Root is `.`, source files are at the project root. Otherwise, all source scanning targets the Source Root path.

### 1.2: Find the Delta

**If `--all` flag**: Skip delta detection. Delegate to `/onboard` — it already handles full rescans and preserves existing docs. Stop execution of `/refresh-docs` after delegating.

**If `--module <name>` flag**: Skip delta detection. Set the changed files list to all source files in the specified module directory.

**If `--since <commit>` flag**: Use the provided commit as the base.

**If no arguments** (auto-detect):

1. Find the last commit that touched `docs/`:
   ```
   git log -1 --format=%H -- docs/
   ```
   If no commit found (docs/ has never been committed), use the initial commit: `git rev-list --max-parents=0 HEAD`

2. Get source files changed since that commit (committed changes):
   ```
   git diff [base-commit]..HEAD --name-only -- [SOURCE_ROOT]
   ```

3. Also check for uncommitted changes:
   ```
   git diff HEAD --name-only -- [SOURCE_ROOT]
   ```
   Merge both lists (deduplicate). If there are uncommitted changes, note this in the Phase 2 scope review.

4. Filter out non-source files from the combined list: remove `node_modules/`, `dist/`, `build/`, `.git/`, lock files, binary files, `.claude/`, `specs/`, `docs/`.

5. If no changed files found, inform the user: "Documentation is up to date — no source files changed since the last docs update ([commit hash], [date])." and stop.

### 1.3: Map to Modules

Group the changed files by their top-level module directory (first directory under Source Root):

```
src/auth/auth.service.ts    → auth
src/auth/auth.guard.ts      → auth
src/cart/cart.service.ts     → cart
src/shared/utils.ts          → shared
```

Read the existing `docs/` folder structure (run Glob on `docs/`) to understand what documentation already exists.

### 1.4: Assess Scale

Count the changed files and affected modules:

| Changed Files | Strategy |
|---|---|
| **1–20** | Single tech-writer invocation with all files |
| **21–50** | Batch by module — one tech-writer invocation per affected module |
| **50+** | Recommend `/refresh-docs --all` instead (too many changes for delta approach) |

## PHASE 2: Scope Review

Present the detected scope to the user:

```
## Documentation Refresh Scope

**Base**: [commit hash] ([date] — last commit that touched docs/)
**Changed source files**: [count]
**Affected modules**: [list]

### Files by Module:
- **auth** ([count] files): auth.service.ts, auth.guard.ts, ...
- **cart** ([count] files): cart.service.ts, ...

### Existing Docs:
- docs/features/auth.md — will be updated
- docs/features/cart.md — will be updated
- docs/api/users.md — will be checked

Proceed with refresh?
```

Wait for user confirmation before proceeding.

## PHASE 3: Refresh Documentation

### 3.0: Load Tech-Writer Agent

Read `.claude/agents/tech-writer.md` and include its **full content** as Part 1 of the agent prompt. The agent already knows about Refresh Mode (it will auto-select it when the prompt contains "REFRESH MODE"). If the file does not exist, proceed with the Part 2 prompt alone.

### 3.1: Single Invocation (1–20 files)

Construct the prompt with two parts:

**Part 1** (if agent file exists): The full content of `.claude/agents/tech-writer.md`.

**Part 2** (always included):

```
You are operating in **REFRESH MODE**. Update documentation for source files that changed since docs were last updated.

## Project Context
[Project name, framework, Source Root from CLAUDE.md]

## Changed Files (grouped by module)
### [module-name]
- [file1]: [brief — new/modified since last docs update]
- [file2]: [brief]

### [module-name]
- [file3]: [brief]

## Existing Documentation
[Glob output of docs/ — so you know what already exists]

## Instructions
1. Read each changed file listed above
2. For each file, identify:
   - New public APIs (exported functions, classes, types) that need inline docs
   - Changed public APIs whose existing inline docs are now outdated
   - Removed public APIs whose docs should be cleaned up
3. Add or update **inline documentation** (JSDoc/docstrings) for new/changed public APIs in the source files
4. For each affected module, check if a corresponding doc exists in `docs/features/` or `docs/api/`:
   - If it exists → update it with the new/changed APIs
   - If it doesn't exist but the module now has significant public APIs → create `docs/features/[module-name].md`
5. If architecture or cross-module patterns changed, update `docs/architecture.md`
6. If a public API was removed, remove it from both inline docs and `docs/` files
7. Report what you updated, what you created, and what you skipped (with reasons)
```

Launch the tech-writer agent with the combined prompt (Part 1 + Part 2).

### 3.2: Batched Invocation (21–50 files)

For each affected module, launch a separate tech-writer agent with only that module's files. Use the same prompt structure as 3.1 but scoped to one module.

Run up to 3 tech-writer agents in parallel if modules are independent.

### 3.3: Full Rescan (`--all` flag)

If `--all` was specified, this was handled in Phase 1.2 — execution was delegated to `/onboard`. This phase is not reached.

## PHASE 4: Verify & Commit

### 4.1: Verify Documentation

After the tech-writer completes:

1. **Check for updated files**: Run `git diff --name-only` to see what the tech-writer changed. If no files were changed, the tech-writer determined no updates were needed — report this to the user and skip to Phase 5.

2. **Verify no logic changes**: Run `tsc --noEmit` (or project equivalent from CLAUDE.md) and lint on all changed source files. If either fails, the tech-writer accidentally modified logic — revert the source file changes and re-invoke the tech-writer with stricter instruction.

3. **Verify inline docs**: For each source file that was changed by the tech-writer, verify that:
   - New JSDoc/docstrings match actual function signatures
   - Only doc comments were changed (no logic modifications)

4. **Verify `docs/` updates**: For each modified doc file, verify:
   - Code examples reference real functions/files
   - No broken cross-references

### 4.2: Commit

If changes were made, commit only documentation-related files:
```
git add docs/ && git diff --name-only --cached --diff-filter=M | head -0
```

For source files with inline doc updates, add them individually:
```
git add [each source file the tech-writer modified]
git commit -m "docs: refresh documentation for [list affected modules]"
```
Follow the **Commit Convention** section in CLAUDE.md (format and attribution rules).

Do NOT use `git add -A` — only add files the tech-writer was supposed to modify.

## PHASE 5: Report

```
## Documentation Refresh Complete

**Scope**: [count] source files across [count] modules
**Base commit**: [hash] ([date])

### Updated:
- [file]: [what changed — e.g., "Added JSDoc for new authenticate() function"]
- [docs/features/auth.md]: [what changed — e.g., "Added Public API section for new guard middleware"]

### Created:
- [docs/features/new-module.md]: [why — e.g., "New module with 3 public exports"]

### Skipped:
- [module]: [reason — e.g., "Internal refactoring only, no public API changes"]

### No Update Needed:
- [module]: [reason — e.g., "Existing docs already accurate"]

**Commit**: `docs: refresh documentation for [modules]`
```

## PHASE 6: Memory Update

If anything noteworthy was discovered during the refresh, update `.claude/memory/MEMORY.md`:

- **Documentation gaps**: If certain modules consistently lack docs, note the pattern
- **Stale areas**: If docs were severely out of date for specific areas, note why (e.g., "cart module had 5 undocumented public APIs — Phase 5 was skipped during execute-task all")
- **New patterns**: If the tech-writer introduced documentation for a pattern not previously documented

Keep entries concise (1-2 lines each). Only update if there's something genuinely useful for future work.

## IMPORTANT RULES

1. **Delta only** — without `--all`, only read and document files in the git delta. Do not scan the broader codebase
2. **User approval required** — always show the scope and wait for confirmation before making changes
3. **Preserve existing docs** — update, don't replace. If existing docs cover a topic accurately, leave them alone
4. **No logic changes** — the tech-writer may only add/update documentation (inline docs + docs/ files). Never modify code logic
5. **Honest reporting** — if the tech-writer skipped files, report why. Don't hide "no docs needed" decisions