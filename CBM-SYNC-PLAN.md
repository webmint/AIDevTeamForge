# CBM-SYNC-PLAN

Goal: keep each developer's local CBM (codebase-memory-mcp) index aligned with the parent repo's current HEAD in both wrapper and solo modes, without installing anything into the parent repo's `.git/` directory.

## Context for next session

- **Problem**: CBM stores its graph DB in a per-machine location (`.codegraph/`, observed untracked in repo root as of 2026-05-11). Each developer's index drifts independently. After a `git pull` or `git checkout` to a sibling branch, the local CBM graph references stale code; queries (`search_graph`, `trace_path`, `get_code_snippet`) return wrong locations and broken chains.
- **Constraint** (wrapper mode): DevForge must not install anything into the parent repo's `.git/hooks/` or anywhere outside DevForge-owned surfaces (`.claude/`, `.devforge/`). Native git hooks are therefore out of scope.
- **Constraint** (install parity): the CBM-sync mechanism must be installed by the same DevForge installer flow that ships commands and agents — single install path covering wrapper and solo.
- **Approach chosen** (option A from chat 2026-05-11): stamp file + Claude Code SessionStart hook. The hook compares parent HEAD to the stamp and emits drift context to Claude on every session boot. Claude (in the main conversation, where MCP is reliably connected) executes `detect_changes` / `index_repository` and then writes the new stamp via a small DevForge Python helper. Layer B (command-boundary stamp check) added to catch mid-session pulls.
- **Why not git hooks**: parent-`.git/` footprint forbidden in wrapper mode. SessionStart hook is owned by DevForge install surface (`.claude/settings.json`), so wrapper + solo share one mechanism.
- **Why not cloud-hosted CBM** (raised in chat 2026-05-11): code-upload compliance blocker, per-branch reindex coordination, query latency, and multi-tenant auth are all out of scope. If the team eventually needs cross-machine code graph, that's Sourcegraph territory, not DevForge.
- **Authoritative SessionStart facts** (verified via claude-code-guide agent 2026-05-11, sourced from `code.claude.com/docs/en/hooks.md`):
  - Fires on `startup`, `resume`, `clear`, `compact` (all distinguished by hook input `source` field).
  - Two output protocols: plain stdout (auto-injected as context) or JSON with `hookSpecificOutput.additionalContext`.
  - **MCP tools at SessionStart are unreliable** — MCP servers typically have not finished connecting when the hook fires. Plan uses stdout context emission, not direct MCP calls from the hook.
  - Hook is non-blocking — session always starts even if hook errors.
  - Subagent SessionStart firing **not documented** — plan does not rely on it.
- **Existing CBM hook substrate** (Track 1 F.11, shipped 2026-05-09): `src/hooks/` already contains four single-purpose hook scripts (`cbm-code-discovery-gate`, `bash-ban-raw-tools`, `cbm-mcp-marker`, `cbm-session-reminder`). `install.sh:167-169` copies the whole directory to target `.claude/hooks/` and chmods +x. `src/settings.template.json` already wires each hook (including a SessionStart entry for `cbm-session-reminder`). This plan adds a 5th hook (`cbm-sync-session-start`) and a 2nd SessionStart array entry — no installer / emitter changes.
- **Helper invocation convention** (verified 2026-05-11): existing helpers ship as a POSIX-launcher shim (no extension) plus a `.py` sidecar at `src/devforge/lib/<name>` + `<name>.py`. Installed to target's `.devforge/lib/`. Command specs and hooks invoke them as `.devforge/lib/<helper> <subcommand>` (or `$CLAUDE_PROJECT_DIR/.devforge/lib/<helper>` from hook context). The plan uses this exact pattern — no `python -m` invocation.

## Design summary

Three pieces, all DevForge-owned:

1. **Stamp file** at `.devforge/cbm-last-indexed-sha`. JSON: `{"git_sha": "<sha>", "indexed_at": "<iso8601>"}`. Schema-version field deliberately omitted (resolved 2026-05-11 — defer until empirical need).
2. **Python helper** `src/devforge/lib/cbm_sync_helper.py` + POSIX launcher `src/devforge/lib/cbm_sync_helper` (shim copied from existing `init_helper` shim, `PY_FILE` repointed). Two subcommands: `check` (compares parent HEAD to stamp, prints `current` / `drift <stamp>..<head>` / `missing` / `not-a-git-repo`) and `write` (reads parent HEAD via `git rev-parse HEAD`, writes stamp atomically).
3. **SessionStart hook script** `src/hooks/cbm-sync-session-start` (extensionless, matching existing hook-file naming convention). Calls `$CLAUDE_PROJECT_DIR/.devforge/lib/cbm_sync_helper check` and emits a drift-instruction context block via stdout when state is `drift` or `missing`. Silent when `current` or `not-a-git-repo`.

Installer wires the hook via a second entry in `src/settings.template.json` under `hooks.SessionStart`. `install.sh` already copies both `src/hooks/*` and `src/settings.template.json` — no installer edits required.

## Phase 0 — verify substrate

Before writing any code, confirm one fact the plan still depends on.

**0.1** Verify the SessionStart hook stdin shape. The hook script reads JSON event payload from stdin. Confirm via `code.claude.com/docs/en/hooks.md` the exact stdin schema for SessionStart events — specifically the `source` field name and possible values. Do not guess. (The current MVP doesn't branch on `source`, but the verification protects against future additions.)

**Verify**: one short note captured here, citing the docs URL.

## Phase 1 — stamp helper

Add `src/devforge/lib/cbm_sync_helper.py` + POSIX launcher.

**1.1** Implement `cbm_sync_helper.py write`:
- Reads parent repo HEAD via `git rev-parse HEAD` (subprocess, cwd = `Path.cwd()` — helper assumes invocation from parent repo root, same convention as existing DevForge helpers).
- Computes ISO-8601 timestamp.
- Writes `{"git_sha": "<sha>", "indexed_at": "<ts>"}` to `.devforge/cbm-last-indexed-sha` atomically (write to `.tmp` then rename).
- Exits 0 on success, 1 on I/O failure, 2 if not in a git repo.

**1.2** Implement `cbm_sync_helper.py check`:
- Reads parent HEAD via `git rev-parse HEAD`.
- Reads stamp file. Four outcomes:
  - File missing → print `missing`, exit 0.
  - File present, `git_sha` matches HEAD → print `current`, exit 0.
  - File present, `git_sha` differs → print `drift <stamp_sha>..<head_sha>`, exit 0.
  - Not in a git repo → print `not-a-git-repo`, exit 2.
- Corrupt stamp JSON treated as `missing`.

**1.3** Ship POSIX launcher `src/devforge/lib/cbm_sync_helper`: copy the shim from `src/devforge/lib/init_helper` (lines 1-35 — already-verified shape) and change only the `PY_FILE` line to point at `cbm_sync_helper.py`. chmod +x.

**1.4** Tests in `tests/lib/test_cbm_sync_helper.py`. Per `feedback_test_first_python_helpers.md`, every function gets a test written and run in the same turn. Use `tmp_path` + real `git init` to produce real HEADs. Cover: write fresh stamp, write overwrite, check missing, check current, check drift, check corrupt-json-treated-as-missing, check not-a-git-repo, atomic-write semantics (the `.tmp` file does not survive on success).

**Verify**: `pytest tests/lib/test_cbm_sync_helper.py -v` is all green. Run once, confirm zero failures.

## Phase 2 — SessionStart hook script

Add `src/hooks/cbm-sync-session-start` (extensionless, bash). Responsibilities:

- Receive SessionStart event JSON on stdin (per Phase 0.1 verified schema).
- Invoke `$CLAUDE_PROJECT_DIR/.devforge/lib/cbm_sync_helper check`.
- Branch on output:
  - `current` → exit 0 silently. No context emitted.
  - `missing` → emit context block instructing Claude to run `index_repository` (full initial index) then `$CLAUDE_PROJECT_DIR/.devforge/lib/cbm_sync_helper write`.
  - `drift <a>..<b>` → emit context block instructing Claude to run `detect_changes` then `$CLAUDE_PROJECT_DIR/.devforge/lib/cbm_sync_helper write`.
  - `not-a-git-repo` → exit 0 silently (DevForge may be installed in a non-git project; CBM sync is a no-op there).
- Hook is non-blocking per SessionStart semantics — any unexpected error exits 1, stderr is shown only with `--verbose`, session still starts.

**2.1** Draft the context-emission strings as unambiguous, verbatim Claude instructions. Example for `drift`:

> The CBM (codebase-memory-mcp) index is stale: stamp records `<a>` but parent repo HEAD is `<b>`. Before answering structural code queries, call `mcp__codebase-memory-mcp__detect_changes`. After it completes, run `$CLAUDE_PROJECT_DIR/.devforge/lib/cbm_sync_helper write` to record the new stamp.

The exact wording matters — see `feedback_verbatim_echo_directive.md`. Use explicit verbs ("call X, then run Y"), not "consider refreshing".

**2.2** Verify the hook runs end-to-end in a real Claude session:
- Manually corrupt the stamp file (write a wrong SHA).
- Start a Claude session in this repo.
- Confirm Claude's first response acknowledges the drift context and calls `detect_changes` + `cbm_sync_helper write`.
- Re-verify stamp file now matches HEAD.

**Verify**: empirical run in real Claude session, captured outcome here. Per `feedback_helper_owns_contract_filesystem_forcing.md`, prose-only verification is insufficient — actually run it.

## Phase 3 — installer wiring

Two file edits. Zero installer code changes.

**3.1** Add a second entry to `src/settings.template.json` under `hooks.SessionStart`, alongside the existing `cbm-session-reminder` entry. Same matcher (`startup|resume|clear|compact`). Command: `$CLAUDE_PROJECT_DIR/.claude/hooks/cbm-sync-session-start`.

**3.2** Confirm `install.sh:168` (`cp -R "$TEMPLATE_DIR/src/hooks/." "$TARGET_DIR/.claude/hooks/"`) carries the new file across. No code change required — the cp is recursive.

**3.3** Confirm `install.sh:166` (`cp src/settings.template.json` → target) carries the new array entry across. No code change required.

**3.4** Mode-branched logic — **none needed**. `.claude/` is DevForge-owned in both modes; install path is identical.

**3.5** Update `install.sh` and `update.sh` end-of-run messages (the post-install summary lines) to mention the new hook so users know it's installed and what it does. One sentence each. Verify by re-running install on a test target and reading the printed summary.

**Verify**: run `./install.sh` into a test target. Confirm `.claude/hooks/cbm-sync-session-start` exists and is executable in the target. Confirm `.claude/settings.json` in the target has the 2nd SessionStart hook entry. Confirm no files written outside `.claude/` and `.devforge/` in a wrapper-mode test target.

## Phase 4 — layer B: command-boundary check

Catch the mid-session `git pull` case: SessionStart-only check misses pulls that happen while a Claude session is already running.

**4.1** Identify which `src/commands/*/main.md` specs depend on CBM being current. Start with `/generate-docs` (Phase 2 fill loop) — confirmed CBM consumer. Grep other command specs for `mcp__codebase-memory-mcp__` references to enumerate the full list.

**4.2** Add a verbatim preamble block to each identified command spec, near the top, before step 1:

> Before executing any step below, run `.devforge/lib/cbm_sync_helper check`. If output is `drift ...`, call `mcp__codebase-memory-mcp__detect_changes` then `.devforge/lib/cbm_sync_helper write` before continuing. If output is `missing`, call `mcp__codebase-memory-mcp__index_repository` then `.devforge/lib/cbm_sync_helper write` before continuing. If output is `current` or `not-a-git-repo`, proceed.

Per `feedback_verbatim_echo_directive.md`, use the explicit "run X / call Y / then run Z" form, not paraphrase.

**Verify**: pick one CBM-consuming command (start with `/generate-docs`), simulate mid-session drift (write wrong SHA to stamp), invoke the command in a real Claude session, confirm Claude refreshes CBM before doing the command's actual work.

## Phase 5 — manual /cbm-sync slash command (YAGNI-deferred)

For developers who consume CBM outside of Claude sessions (IDE plugins, direct MCP calls from other shells). **Do not build this phase until empirical demand surfaces.** Per `feedback_track_a_yagni_rollback.md`, don't build for speculative consumers.

If empirical demand arrives: `src/commands/cbm-sync/main.md` — single-step command that calls `detect_changes` (or `index_repository` if stamp is `missing`) then `cbm_sync_helper write`. Also update `scripts/emitters/claude.py` `_PROMOTED` list per `feedback_emitter_promoted_cross_check.md`.

## When resuming work

1. Re-read this plan in full.
2. Check `git log --oneline -20` for any partial implementation since the plan was drafted.
3. Check progress markers:
   - `src/devforge/lib/cbm_sync_helper.py` + `src/devforge/lib/cbm_sync_helper` exist → Phase 1 done.
   - `src/hooks/cbm-sync-session-start` exists → Phase 2 done.
   - `src/settings.template.json` has a 2nd SessionStart entry pointing at `cbm-sync-session-start` → Phase 3 done.
   - CBM-consuming command specs in `src/commands/*/main.md` have the preamble block → Phase 4 done.
4. Phases 0–4 are the MVP. Phase 5 is YAGNI-deferred until evidence.
5. Resume at the first phase whose Verify criteria are not satisfied.

## Resolution log

Resolved 2026-05-11 (chat with Mykola):
- Q1 (settings.json emission) → install.sh copies `src/settings.template.json` and `src/hooks/*` directly; no emitter changes; new hook = one file + one array entry.
- Q2 (helper invocation) → POSIX launcher + .py sidecar; invoke as `.devforge/lib/cbm_sync_helper`, never `python -m`.
- Q3 (schema version) → defer; MVP stamp = `{git_sha, indexed_at}` only.
- Q4 (hook naming) → `cbm-sync-session-start`, no extension, matches existing hook-file convention.
- Q5 (separate file vs merge) → separate file. Matches existing single-responsibility-per-hook pattern; adds 2nd SessionStart array entry.
