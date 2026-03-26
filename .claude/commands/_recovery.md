# Recovery: Interrupted Command Session

This file is read by `/execute-task`, `/fix`, and `/refactor` when `.claude/wip.md` exists at the start of execution. The calling command provides `CALLING_COMMAND` (one of: `execute-task`, `fix`, `refactor`).

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

Report findings to the user. The option labels vary by command:

**For execute-task:**
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

**For fix / refactor:**
```
Interrupted [fix|refactoring] detected: [description]
Interrupted during: Phase [N] — [phase name]

Git state:
- Uncommitted changes: [yes/no] ([list files])
- WIP commits found: [yes/no] ([count])

Options:
1. **Resume** — Re-run verification on current state and continue from the interrupted phase.
2. **Rollback and retry** — Reset to the last clean checkpoint, then re-execute from scratch.
3. **Rollback and abandon** — Reset to pre-WIP state. You handle it manually.
4. **Keep changes, clear marker** — Keep current git state as-is, delete WIP marker only.
```

Wait for user to choose.

## 0.4: Execute Choice

**If Resume:**
- Run the Type Check Command from CLAUDE.md, the Lint Command, and the build command (if specified) on all files listed in the WIP marker
- If they pass, jump to the phase AFTER the interrupted phase
- If they fail, inform the user — the code is in a broken state. Recommend option 2 (rollback and retry).

**If Rollback and retry:**
- `git stash` any uncommitted changes (save them just in case)
- `git reset --hard` to the commit before the first `[WIP]` commit (find via `git log --oneline | grep -v "\[WIP\]" | head -1`)
- **Source repo rollback** (if `$SOURCE_CHECKPOINT` exists in wip.md): `git -C $SOURCE_ROOT reset --hard $SOURCE_CHECKPOINT`
- Delete `.claude/wip.md`
- Re-run the calling command from PHASE 1:
  - `execute-task`: re-run `/execute-task [same task number]`
  - `fix`: re-run `/fix [same arguments]`
  - `refactor`: re-run `/refactor [same arguments]`

**If Rollback and skip/abandon:**
- Same git reset as above (including source repo rollback if applicable)
- **execute-task only**: Update the task file — set status back to `Pending`. Inform user the task is pending.
- **fix/refactor**: Inform user the state is cleared and they can handle it manually.
- Delete `.claude/wip.md`

**If Keep changes, mark manual / clear marker:**
- Delete `.claude/wip.md` only
- Do nothing else
- **execute-task**: Inform user: "WIP marker cleared. Git state untouched. Task file still shows in_progress — update it manually when done."
- **fix/refactor**: Inform user: "WIP marker cleared. Git state untouched."