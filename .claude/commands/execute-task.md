# /execute-task — Execute Tasks from Breakdown

Picks up one or more tasks from the breakdown, selects the assigned agent for each, and executes them with the full enforced workflow. Includes automatic self-repair when verification catches errors.

## Usage
```
/execute-task                         # next pending task in active feature
/execute-task 3                       # specific task in active feature
/execute-task 001/3                   # explicit feature/task (e.g. 001/3 or user-auth/3)
/execute-task 1,3,5                   # specific tasks, executed sequentially
/execute-task 1-5                     # range of tasks, executed sequentially
/execute-task all                     # all pending tasks in active feature
```

## Arguments
- `$ARGUMENTS` — What to execute. Supports these formats:
  - **Empty**: Execute the next pending task (lowest number with all dependencies satisfied) from the active feature.
  - **Single number** (e.g. `3`): Execute that specific task in the active feature.
  - **Feature/task** (e.g. `001/3` or `user-auth/3`): Execute a specific task in a specific feature.
  - **Comma-separated** (e.g. `1,3,5`): Execute these specific tasks sequentially in the active feature. Each task gets the full Phase 0–7.5 treatment.
  - **Range** (e.g. `1-5`): Execute tasks 1 through 5 sequentially. Equivalent to `1,2,3,4,5`.
  - **`all`**: Execute all pending tasks in the active feature, in dependency order.

## Prerequisites

1. Task files must exist in `specs/NNN-feature/tasks/`
2. The specified task's dependencies must all be completed (status: Complete)
3. If dependencies are not met, inform the user which tasks must be completed first

## PHASE 0: Recovery Check

Before anything else, check if a previous task execution was interrupted.

### 0.1: Check for WIP Marker

Read `.claude/wip.md`. If it does NOT exist, skip to PHASE 1 (normal flow).

If it DOES exist, a previous task was interrupted. Read the WIP marker to determine:
- Which task was being executed (feature + task number)
- Which phase it was in when interrupted
- What files were being modified

### 0.2: Assess State

Run these checks:
1. `git status` — are there uncommitted changes?
2. `git log --oneline -5` — are there `[WIP]` commits?
3. Read the task file — is it marked `in_progress`?
4. Read `specs/[feature]/tasks/README.md` — current task statuses

### 0.3: Present Recovery Options

Report findings to the user and offer exactly these options:

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

Wait for user to choose. Execute their choice:

**If Resume:**
- Run `tsc --noEmit` and lint on all files listed in the WIP marker
- If they pass, jump to the phase AFTER the interrupted phase (e.g., if interrupted in Phase 3, jump to Phase 4: Mark Complete)
- If they fail, inform the user — the code is in a broken state. Recommend option 2 (rollback and retry).

**If Rollback and retry:**
- `git stash` any uncommitted changes (save them just in case, user can `git stash pop` later)
- `git reset --hard` to the commit before the first `[WIP]` commit (find it via `git log --oneline | grep -v "\[WIP\]" | head -1`)
- Delete `.claude/wip.md`
- Re-run `/execute-task [same task number]` from PHASE 1

**If Rollback and skip:**
- Same git reset as above
- Update the task file: set status back to `Pending`
- Delete `.claude/wip.md`
- Inform user the task is pending and they can run `/execute-task` when ready

**If Keep changes, mark manual:**
- Delete `.claude/wip.md` only
- Do nothing else
- Inform user: "WIP marker cleared. Git state untouched. Task file still shows in_progress — update it manually when done."

## PHASE 1: Load Task Context

### 1.1: Resolve Feature Directory and Build Task Queue

First, resolve the **active feature** (used by all formats except `feature/task`):
- Scan all feature directories in `specs/` and find the one with incomplete tasks (at least one task not marked Complete)
- If multiple features have incomplete tasks, use the **lowest numbered** one (finish earlier features first)
- If all features are complete, inform the user there are no pending tasks

Then, build the **task queue** based on `$ARGUMENTS`:

**If `$ARGUMENTS` contains a `/`** (e.g. `001/3`, `user-auth/3`):
- Use the part before `/` to match a feature directory in `specs/` (by number prefix or name)
- Task queue = `[part after /]` (single task)

**If `$ARGUMENTS` is `all`**:
- Task queue = all pending tasks in the active feature, sorted by number, filtered to those whose dependencies are already satisfied or will be satisfied by earlier tasks in the queue

**If `$ARGUMENTS` contains `,`** (e.g. `1,3,5`):
- Parse as comma-separated list of task numbers
- Task queue = those tasks in the given order
- Validate each task exists and is not already Complete

**If `$ARGUMENTS` contains `-` but no `/`** (e.g. `1-5`):
- Parse as range: start number to end number (inclusive)
- Task queue = expanded range in order
- Skip any tasks in the range that are already Complete

**If `$ARGUMENTS` is a single number** (e.g. `3`):
- Task queue = `[that number]` (single task)

**If `$ARGUMENTS` is empty**:
- Task queue = `[next pending task]` (lowest number with all dependencies satisfied)

For multi-task queues: the current task is always the first item. After it completes (Phase 7.5), the remaining queue is processed via the Multi-Task Continuation phase (Phase 8).

### 1.2: Load Context

0. Read `.claude/session-state.md` if it exists.
   - If it does NOT exist, this is a fresh session — proceed normally.
   - If it exists, compare the "Current Feature" field with the feature you're about to execute.
     - **Feature matches** → use the session state as-is (context load count carries over).
     - **Feature does NOT match** → reset session-state.md to the empty placeholder. This is a new feature context — previous session tracking is stale.
   - If context load is "heavy", recommend /compact to the user before proceeding.
1. Read the task index at `specs/NNN-feature/tasks/README.md`
2. Read the specific task file (e.g., `specs/NNN-feature/tasks/001-title.md`)
3. Read the feature's `spec.md` and `plan.md`
4. Read `constitution.md`
5. Read `.claude/memory/MEMORY.md`
6. Read ALL files listed in the task's "Files" section
7. **Read relevant documentation**: Search `docs/` for files related to the area this task touches. These docs are the knowledge base for all agents — populated by `/onboard` for existing projects or built incrementally by the tech-writer for new projects. Read only docs that are directly relevant — not all docs.

Verify:
- Task exists and is not already completed
- All dependencies (listed in "Depends on") are marked complete
- The assigned agent matches what's available

## PHASE 2: Pre-Flight Check

Before writing ANY code, verify:

1. **Constitution compliance**: Does the planned change violate any NON-NEGOTIABLE rules?
2. **Memory check**: Does MEMORY.md have any warnings about similar changes?
3. **File state check**:
   - **Existing files**: Are the target files in the expected state? (No unexpected changes since the breakdown was created)
   - **New files (greenfield)**: Does the target directory exist? If not, it should be created as part of this task or a prior task
4. **Type safety**: Read the type definitions involved and verify the change is type-safe on paper. For greenfield, verify the proposed types align with the constitution's patterns

If ANY pre-flight check fails, stop and inform the user with specifics.

### 2.5: Create WIP Marker and Clean Checkpoint

1. Create a git checkpoint BEFORE any changes:
   ```
   git add -A && git commit -m "[checkpoint] Pre-task [N]: [title]" --allow-empty
   ```
   This gives us a clean rollback point.

2. Write `.claude/wip.md`:
   ```markdown
   # Work In Progress

   ## Task
   Feature: [NNN-feature-name]
   Task: [N] — [title]
   Task file: specs/[feature]/tasks/[NNN-title.md]

   ## Started
   Phase: 3 (Execute)

   ## Files Being Modified
   - [list from task's "Files" section]

   ## Rollback Point
   Commit: [hash from the checkpoint commit above]
   ```

## PHASE 3: Execute

### 3.1: Create Task Tracking

Use TaskCreate to create a tracking task:
- Subject: Task [N] title from the breakdown
- Description: Full description from the breakdown
- ActiveForm: "Implementing [short description]"

Set it to `in_progress`.

### 3.2: Launch Agent

Use the Task tool to launch the agent specified in the task's "Agent" field.

Provide the agent with:
1. The full task description and change details
2. The relevant section of the spec (acceptance criteria this task addresses)
3. The constitution's relevant rules
4. Any warnings from MEMORY.md
5. The list of files to change
6. Clear instruction: **make ONLY the changes described in this task, nothing more**

The agent prompt should follow this structure:

```
You are executing Task [N] from an approved task breakdown.

## Task
[Full task description from breakdown]

## Files to Change
[List from breakdown]

## Change Details
[Specific changes from breakdown]

## Rules
1. Make ONLY the changes described above — nothing more
2. Follow the project's constitution (key rules: [relevant rules])
3. Known pitfalls for this area: [from MEMORY.md]
4. Every file you change must pass TypeScript compilation
5. Every file you change must pass ESLint
6. Document any new functions/variables you create

## Done When
[Done conditions from breakdown]

## Do NOT
- Refactor surrounding code
- Add features not in the task
- Change files not listed above (unless absolutely necessary for compilation)
- Skip type checking or linting
```

After the agent completes, immediately create a WIP git commit to preserve the work:
```
git add -A && git commit -m "[WIP] Task [N]: [title] — agent execution complete"
```

Update `.claude/wip.md` — change Phase to `4 (Mark Complete)`.

### 3.3: Post-Agent Verification (with Self-Repair)

After the agent completes, run verification:

1. **Files changed match task scope**: Check `git diff --name-only` (or `git status` for new files) against the task's file list. If extra files were changed, investigate why.
2. **TypeScript compiles**: Run `tsc --noEmit` (the PostToolUse hook should catch this, but verify explicitly)
3. **ESLint passes**: Run lint on all changed files
4. **Done conditions met**: Check each "Done when" item from the task

**If ALL checks pass** → proceed to Phase 4.

**If any check fails** → enter the self-repair loop (max 3 attempts):

For each repair attempt:
1. Collect all error output (tsc errors, lint errors, unmet done-conditions)
2. Launch a **repair agent** (using the Task tool) with:
   - The original task description and scope constraints
   - The specific errors to fix (full error output)
   - The list of files that were changed
   - Clear instruction: **"Fix ONLY these errors. Do not add features, refactor, or change scope. Stay within the files listed."**
3. After the repair agent completes, commit:
   ```
   git add -A && git commit -m "[WIP] Task [N]: [title] — repair attempt [M]/3"
   ```
4. Re-run ALL four verification checks above

**If verification passes after any attempt** → proceed to Phase 4.

**If all 3 repair attempts are exhausted and checks still fail** → STOP execution entirely:
- Report the remaining errors to the user
- Do NOT proceed to Phase 4 or any subsequent task (even in multi-task mode)
- Keep the WIP marker and commits so the user can inspect the state
- Suggest: "Run `/execute-task [N]` again after manually fixing, or use recovery options"

## PHASE 4: Mark Complete

1. Update the task tracking (TaskUpdate → completed)
2. In the task file (`specs/NNN-feature/tasks/NNN-title.md`):
   - Change **Status** to `Complete`
   - Mark done conditions with `[x]`
   - Fill in the Completion Notes section:
     ```
     **Completed**: [date/time]
     **Files changed**: [actual files that changed]
     **Notes**: [any deviations from plan or things to watch]
     ```
3. Update the task index (`specs/NNN-feature/tasks/README.md`) — mark this task's status as Complete

After marking the task complete in task files, commit:
```
git add -A && git commit -m "[WIP] Task [N]: [title] — marked complete"
```

Update `.claude/wip.md` — change Phase to `5 (Documentation Update)`.

## PHASE 5: Documentation Update (MANDATORY)

After code is verified, launch the **tech-writer** agent to update documentation.

Provide the agent with:
1. The completed task file (with completion notes and actual files changed)
2. The feature spec
3. The list of files that were actually changed

The tech-writer will:
- Read only the task, spec, and changed files
- Determine if documentation updates are needed
- Add or update **inline documentation** (JSDoc/docstrings) in changed source files for new/changed public APIs
- Update existing docs or create new ones in `docs/`
- Skip documentation if the change doesn't warrant it (internal refactoring, bug fixes, test-only changes)

If the tech-writer determines no docs are needed, that's fine — not every task produces documentation. But the step MUST run.

## PHASE 6: Report

Provide a concise summary to the user:

```
## Task [N] Complete: [Title]

**Changes**:
- [file]: [what changed, 1 line]
- [file]: [what changed, 1 line]

**Verification**:
- TypeScript: PASS
- ESLint: PASS
- Done conditions: [all met / exceptions]

**Documentation**: [Updated docs/features/X.md / Created docs/api/Y.md / No docs needed]

**Spec criteria addressed**: AC-[numbers]

**Next task**: [NNN]-[title] (ready / blocked by [NNN])
```

### Final Commit and WIP Cleanup

1. Squash all `[WIP]` and `[checkpoint]` commits for this task into a single clean commit:
   ```
   git reset --soft [checkpoint-commit-hash]
   git commit -m "feat([feature-name]): Task [N] — [title]"
   ```

2. Delete `.claude/wip.md`

The task is now fully committed with a clean single commit and no WIP artifacts.

## PHASE 7: Memory Update

If anything unexpected happened during execution (a gotcha, a pattern discovery, a near-mistake), update `.claude/memory/MEMORY.md` with a concise note.

## PHASE 7.5: Context Maintenance

After completing a task, maintain context health to prevent degradation across sequential task executions.

### 7.5.1: Update Session State

FULLY OVERWRITE `.claude/session-state.md` with the following template. This is a fixed-size sliding window — never append, always overwrite completely. The file must not exceed ~40 lines / ~800 tokens.

When writing session-state.md, the "Tasks completed this session" counter refers to tasks completed in the current session FOR THE CURRENT FEATURE. If the feature has changed since the last write, start the counter at 1.

```
<!-- This file is a fixed-size sliding window. Always fully overwritten, never appended. Max ~40 lines. -->
# Session State
Last updated after Task [N]: [Title]

## Current Feature
[NNN-feature-name]

## Session Stats
Tasks completed this session: [N]
Estimated context load: light (<3 tasks) | moderate (3-5) | heavy (6+)

## Progress
- Last completed: Task [N] — [title]
- Next pending: Task [N] — [title] (ready | blocked by Task [N])
- Tasks remaining in feature: [count]

## Key Decisions This Session (last 3 only)
- [decision 1 — most recent, from MEMORY.md or this session]
- [decision 2]
- [decision 3]

Older decisions are persisted in .claude/memory/MEMORY.md.

## Files Modified Recently (last 3 tasks only)
- [file]: [what changed] (Task [N])
- [file]: [what changed] (Task [N])

Older modifications are tracked in each task's completion notes under specs/.

## Active Constraints
- [Any constitution rules or spec constraints actively relevant to the next task]
```

### 7.5.2: Context Health Check

Read the "Tasks completed this session" count from the session-state you just wrote.

**If light (1-2 tasks):** No action. Just report task completion normally.

**If moderate (3-5 tasks):** Add a recommendation after the task report:

```
💡 Context maintenance: [N] tasks completed this session.
Optional: Run /compact with these instructions:

/compact Preserve: (1) Current task statuses from specs/[feature]/tasks/README.md, (2) All entries from .claude/memory/MEMORY.md, (3) Constitution rules referenced during this session, (4) Next task's file list and change details from its task file, (5) Session state from .claude/session-state.md. Discard: file contents already committed, old error outputs, superseded diffs, resolved discussions.

Or continue to next task if context still feels responsive.
```

**If heavy (6+ tasks):** Strongly recommend compaction:

```
🔴 Context maintenance: [N] tasks completed this session (heavy context load).
Strongly recommended: Run /compact before continuing.

/compact Preserve: (1) Current task statuses from specs/[feature]/tasks/README.md, (2) All entries from .claude/memory/MEMORY.md, (3) Constitution rules referenced during this session, (4) Next task's file list and change details from its task file, (5) Session state from .claude/session-state.md. Discard: file contents already committed, old error outputs, superseded diffs, resolved discussions.
```

Do NOT auto-compact — always let the user decide. Surface the recommendation with the pre-built compact instruction.

## PHASE 8: Multi-Task Continuation

This phase only applies when the task queue (built in Phase 1.1) contains more than one task.

After Phase 7.5 completes for the current task:

1. Remove the completed task from the queue
2. If the queue is empty → done. Report final summary of all tasks completed in this run.
3. If the queue has remaining tasks:
   a. **Dependency check**: Verify the next task's dependencies are all satisfied (marked Complete). If not, stop and report: "Task [N] is blocked by incomplete dependency Task [M]. Completed [X] of [Y] queued tasks."
   b. **Context health**: Read the "Tasks completed this session" count from session-state.md.
      - If heavy (6+ tasks): **auto-compact** before continuing. Run `/compact` with these preserved items: (1) Current task statuses from `specs/[feature]/tasks/README.md`, (2) All entries from `.claude/memory/MEMORY.md`, (3) Constitution rules referenced during this session, (4) Next task's file list and change details from its task file, (5) Session state from `.claude/session-state.md`. Do NOT ask — compact and continue.
      - If light/moderate: continue without compaction.
   c. **Loop back** to Phase 1 for the next task in the queue. The task queue carries over — do not re-parse `$ARGUMENTS`.

### Multi-Task Final Report

When all queued tasks are complete (or execution stops due to failure/blocked dependency), provide a summary:

```
## Batch Execution Complete

**Tasks completed**: [list with status]
**Tasks skipped/blocked**: [list with reason, if any]
**Total verification**: [all passed / N repair cycles needed]

**Feature progress**: [X of Y tasks complete]
**Next pending**: Task [N] — [title] (ready / blocked by [M])
```

## IMPORTANT RULES

1. **One task per cycle** — each task gets its own full Phase 0–7.5 treatment, even in multi-task mode. Multi-task arguments (`all`, ranges, lists) chain sequential cycles — they do not batch or parallelize tasks.
2. **Scope discipline** — if the agent changes files outside the task scope, revert those changes and investigate
3. **Fail fast** — if pre-flight checks fail, stop immediately. Don't try to work around constitution violations
4. **Agent isolation** — the agent should only know about its task, not the entire breakdown. This prevents scope creep
5. **Self-repair before escalation** — when post-execution verification fails, attempt automatic repair (up to 3 times) before stopping and reporting to the user. Never skip repair attempts.
6. **Hard stop on repair failure** — if all 3 repair attempts fail, stop the entire execution chain (including remaining queued tasks). Do not proceed with broken state.
7. **Verify everything** — trust but verify. Even if hooks ran, run explicit verification after the agent finishes
8. **Track deviations** — if the actual changes differ from the planned changes, document WHY in the task file's Completion Notes
9. **Context hygiene** — always fully overwrite .claude/session-state.md after each task (never append). Keep it under 40 lines. Recommend /compact at moderate load. In multi-task mode, auto-compact at heavy load (6+ tasks) without asking.
10. **Crash safety** — always write .claude/wip.md before starting execution and delete it only after the final commit. If wip.md exists at the start of execute-task, enter recovery flow. Never delete wip.md without either completing the task or explicitly rolling back.
