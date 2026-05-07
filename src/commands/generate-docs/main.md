---
description: TEMPORARY (Plan E iteration) — index the project via codebase-memory-mcp. Full skeleton-fill spec stashed in git history.
---

# /generate-docs — TEMPORARY: index project (Plan E iteration mode)

**Status (2026-05-07)**: this command is in single-purpose iteration mode while Plan E (`CBM-INTEGRATION-PLAN.md`) is built up. The full skeleton-fill spec lives in git history — restore via `git show <prior-sha>:src/commands/generate-docs/main.md > src/commands/generate-docs/main.md` once Plan E components E.2–E.4 land.

## What this run does

One thing: refresh the codebase-memory-mcp graph for the current project, including the Vue compiled-mirror at `.devforge/vue-tmp/`. No skeleton rendering, no concern fill, no validation.

The graph is what Plan E's batched concern-composer will query against; this command exists so the user can drive an index-then-probe loop while E.2 (the `query-concern` helper that consumes the graph) is being built.

---

## Phase 0 — Pre-flight

1. Confirm `.devforge/index.json` exists (this is /init-forge's output and the file list driver for downstream phases):
   ```
   test -f .devforge/index.json
   ```
   If non-zero → ABORT: "missing .devforge/index.json — run /init-forge first to register the project's file list, then re-run /generate-docs."

2. Confirm the `codebase-memory-mcp` binary is on PATH:
   ```
   command -v codebase-memory-mcp >/dev/null
   ```
   If non-zero → ABORT with install instructions:
   > Install codebase-memory-mcp first:
   > `curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash`
   > then restart Claude Code and re-run /generate-docs.

---

## Phase 1 — Vue mirror pre-pass (skip if no .vue files)

Read the file list from `.devforge/index.json` and check for any `*.vue` entry. The list is authoritative — do not walk the filesystem; it includes the same skip rules /init-forge applied (node_modules, dist, etc.).

```
jq -e '[.packages[].files[] | select(endswith(".vue"))] | length > 0' .devforge/index.json >/dev/null
```

- Exit 0 → at least one `.vue` registered → run vue-extract:
  ```
  ./.devforge/lib/vue-extract
  ```
  Mirror lands at `.devforge/vue-tmp/<rel-source-path>/<file>.vue.ts(.map)`. Safe to delete; regenerable.
- Exit 1 → no `.vue` files indexed → skip with the message "no .vue files in .devforge/index.json; skipping vue-extract".

If `vue-extract` exits non-zero (typically @vue/compiler-sfc not resolvable in any nested `node_modules`) → surface the launcher's stderr verbatim and ABORT. The user must install the Vue compiler in the project first.

---

## Phase 2 — Index via codebase-memory-mcp CLI

```
codebase-memory-mcp cli index_repository "$(printf '{"repo_path":"%s"}' "$(pwd)")"
```

Absolute path is required — the README's troubleshooting section calls this out (`index_repository fails | Pass absolute path`).

Capture stdout JSON. Surface the returned `nodes`, `edges`, and `size_bytes` counts to the user. On non-zero exit, surface stderr verbatim and ABORT.

---

## Phase 3 — Verify

1. Project is registered:
   ```
   codebase-memory-mcp cli list_projects
   ```
   Find the entry whose `root_path` matches `$(pwd)`. Capture its `name` field (e.g., `Users-mykolakudlyk-Projects-testForge20`) into a shell variable for the next probe.

2. Vue mirror coverage probe (only if Phase 1 ran vue-extract):
   ```
   codebase-memory-mcp cli search_graph "$(printf '{"project":"%s","label":"File","name_pattern":".*\\\\.vue\\\\.ts$","limit":3}' "$NAME")"
   ```
   Use `name_pattern` (regex on the File node's `name`/`file_path`), NOT `file_pattern` — `file_pattern` does not filter File-label nodes. `total > 0` → mirror picked up. `total == 0` → mirror not indexed; report it but do not abort (investigate before relying on .vue.ts queries downstream).

3. Print a 4-line summary:
   - `nodes/edges` from Phase 2
   - vue-extract status (ran / skipped / failed)
   - vue-mirror coverage from Phase 3 step 2
   - the project `name` to use for downstream `cli` probes

---

## Restoring the full flow

```
git log --oneline -- src/commands/generate-docs/main.md
git show <last-full-sha>:src/commands/generate-docs/main.md > src/commands/generate-docs/main.md
```

Last full-spec commit: `bdae59d` (CBM-INTEGRATION-PLAN.md commit; the Plan E doc was committed alongside the prior generate-docs body).
