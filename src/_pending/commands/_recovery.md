# Recovery: Interrupted Command Session

> **SUPERSEDED** — this `_pending` draft is legacy. The live crash-recovery contract is owned by `src/commands/implement/references/crash-recovery.md` (the `/implement` reference). Retained for history; not part of any emitted command.

This file *was* read by `/execute-task` when `.claude/wip.md` existed at the start of execution; the calling command provided `CALLING_COMMAND` (`execute-task`). Legacy — see the supersession note above; the live contract is `src/commands/implement/references/crash-recovery.md`.

## 0.1: Route by Command Field

Read the `## Command` field from wip.md:
- If it matches `CALLING_COMMAND` → continue with recovery below.
- If the field is **missing** → assume it belongs to the current command. Continue below.
- If it names a **different** command → inform the user: "A previous `/[command]` session was interrupted (see .claude/wip.md). Clear it first by running `/[command]` to resume or recover, or delete `.claude/wip.md` manually to discard it." STOP — do not proceed.

## 0.2: Assess State

Read the WIP marker to determine what was in progress, which phase was interrupted, and what files were being modified.

Run these checks:
1. `git status` — are there uncommitted changes?
2. `git log --oneline -5` — are there `[WIP]` commits?
3. Read relevant task/context files referenced in the WIP marker
4. **Source repo state** (if wip.md has a `## Source Repo Checkpoint` section with a commit hash):
   - `git -C $SOURCE_ROOT status` — uncommitted source changes?
   - `git -C $SOURCE_ROOT log --oneline -5` — source WIP commits?

## 0.3: Present Recovery Options

Report findings to the user:

```
⚠️ Interrupted task detected: Task [N] — [Title] (Feature: [NNN-name])
Interrupted during: Phase [N] — [phase name]

Git state:
- Uncommitted changes: [yes/no] ([list files])
- WIP commits found: [yes/no] ([count])

Options:
1. **Resume** — Continue from where it stopped. Will re-run verification (tsc, lint) on current state and continue from the interrupted phase.
2. **Rollback and retry** — Reset to the last clean checkpoint (git reset to pre-WIP state), then re-execute the task from scratch.
3. **Rollback and skip** — Reset to pre-WIP state, mark task as Pending, and let you choose what to do next.
4. **Keep changes, mark manual** — Keep current git state as-is, delete WIP marker, and let you handle it manually.
```

Wait for user to choose.

## 0.4: Execute Choice

**If Resume:**

First, check the Phase field in wip.md to determine where execution was interrupted:

- **Phase 4 (Complete)** — for `execute-task`: the task was verified, reviewed, and marked complete. Code is committed. Delete wip.md and continue to Phase 5 (bookkeeping).

- **All other phases (3, 4, etc.):**
  - Run the Type Check Command from CLAUDE.md, the Lint Command, and the build command (if specified) on all files listed in the WIP marker
  - If they pass, jump to the phase AFTER the interrupted phase
  - If they fail, inform the user — the code is in a broken state. Recommend option 2 (rollback and retry).

**If Rollback and retry:**
- `git stash` any uncommitted changes (save them just in case)
- Read the `## Rollback Point → Commit:` field from wip.md to get the checkpoint hash
- Validate the hash: `git cat-file -t [hash]`. If valid, proceed. If invalid or missing, STOP and inform the user: "Rollback point hash in wip.md is missing or invalid. Use `git log --oneline` to find the checkpoint commit manually, then run `git reset --hard [hash]`."
- `git reset --hard [checkpoint-hash-from-wip.md]`
- **Source repo rollback** (if `## Source Repo Checkpoint → Commit:` exists in wip.md and is not `N/A`): Validate with `git -C $SOURCE_ROOT cat-file -t [hash]`, then `git -C $SOURCE_ROOT reset --hard [source-checkpoint-hash]`
- Delete `.claude/wip.md`
- Re-run the calling command from PHASE 1:
  - `execute-task`: re-run `/execute-task [same task number]`

**If Rollback and skip:**
- Same git reset as above — read checkpoint hash from wip.md, validate, then reset (including source repo rollback if applicable)
- Update the task file — set status back to `Pending`. Inform user the task is pending.
- Delete `.claude/wip.md`

**If Keep changes, mark manual:**
- Delete `.claude/wip.md` only
- Do nothing else
- Inform user: "WIP marker cleared. Git state untouched. Task file still shows in_progress — update it manually when done."