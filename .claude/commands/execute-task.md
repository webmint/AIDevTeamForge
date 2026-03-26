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

If it DOES exist, a previous execution was interrupted. First check the `## Command` field:
- If `Command: execute-task` → this is a previous task execution. Continue with recovery below.
- If the `## Command` field is **missing** (pre-v3 format) → assume it belongs to the current command. Continue with recovery below.
- If `Command: fix` or `Command: refactor` → a different command was interrupted. Inform the user: "A previous `/[command]` session was interrupted (see .claude/wip.md). Clear it first by running `/[command]` to resume or recover, or delete `.claude/wip.md` manually to discard it." STOP — do not proceed.

Read the WIP marker to determine:
- Which task was being executed (feature + task number)
- Which phase it was in when interrupted
- What files were being modified

### 0.2: Assess State

Run these checks:
1. `git status` — are there uncommitted changes?
2. `git log --oneline -5` — are there `[WIP]` commits?
3. Read the task file — is it marked `in_progress`?
4. Read `specs/[feature]/tasks/README.md` — current task statuses
5. **Source repo state** (if wip.md has a `## Source Repo Checkpoint` section with a commit hash):
   - `git -C $SOURCE_ROOT status` — uncommitted source changes?
   - `git -C $SOURCE_ROOT log --oneline -5` — source WIP commits?

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
- Run the Type Check Command from CLAUDE.md, the Lint Command, and the build command (if Build Command is specified in CLAUDE.md) on all files listed in the WIP marker
- If they pass, jump to the phase AFTER the interrupted phase (e.g., if interrupted in Phase 3, jump to Phase 4: Mark Complete)
- If they fail, inform the user — the code is in a broken state. Recommend option 2 (rollback and retry).

**If Rollback and retry:**
- `git stash` any uncommitted changes (save them just in case, user can `git stash pop` later)
- `git reset --hard` to the commit before the first `[WIP]` commit (find it via `git log --oneline | grep -v "\[WIP\]" | head -1`)
- **Source repo rollback** (if `$SOURCE_CHECKPOINT` exists in wip.md): `git -C $SOURCE_ROOT reset --hard $SOURCE_CHECKPOINT`
- Delete `.claude/wip.md`
- Re-run `/execute-task [same task number]` from PHASE 1

**If Rollback and skip:**
- Same git reset as above (including source repo rollback if applicable)
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
   - **Check workspace mode**: Read the Source Root from `CLAUDE.md`. If it is not `.`, this is a wrapper project. All source code lives under the Source Root path. Verify no Claude artifacts are created inside the Source Root during post-agent verification (Phase 3.3).
     - **Source repo tracking** (wrapper mode only): Record the source repo's current HEAD as `$SOURCE_CHECKPOINT` (`git -C $SOURCE_ROOT rev-parse HEAD`) and the source branch name (`git -C $SOURCE_ROOT branch --show-current`). These are needed for WIP commits and recovery.
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
6. Read files listed in the task's "Files" section. If total estimated lines exceed 500, read only the sections relevant to the change (use Change Details to identify which functions/blocks to focus on). For smaller file sets, read them fully.
7. **Read relevant documentation**: Search `docs/` for files related to the area this task touches. These docs are the knowledge base for all agents — populated by `/onboard` for existing projects or built incrementally by the tech-writer for new projects. Read only docs that are directly relevant — not all docs.

Verify:
- Task exists and is not already completed
- All dependencies (listed in "Depends on") are marked complete
- The assigned agent matches what's available

## PHASE 2: Pre-Flight Check

Before writing ANY code, verify:

1. **Constitution populated**: If `constitution.md` contains `_Run /constitute to populate_`, stop immediately and inform the user: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/execute-task`."
2. **Constitution compliance**: Does the planned change violate any NON-NEGOTIABLE rules?
3. **Memory check**: Does MEMORY.md have any warnings about similar changes?
4. **File state check**:
   - **Existing files**: Are the target files in the expected state? (No unexpected changes since the breakdown was created)
   - **New files (greenfield)**: Does the target directory exist? If not, it should be created as part of this task or a prior task
5. **Type safety**: Read the type definitions involved and verify the change is type-safe on paper. For greenfield, verify the proposed types align with the constitution's patterns
6. **Contract preconditions**: Read the task's `## Contracts → ### Expects` section. For each precondition:
   - Use Grep or Read to verify the condition holds in the current codebase (e.g., check that an export exists, an interface has expected fields, a function exists with the expected name)
   - If a precondition fails:
     - Identify which upstream task should have produced it (check the task's "Depends on" and the upstream task's "Produces")
     - If the upstream task is marked Complete but its postcondition is not met, report: **"Contract violation: Task [N] expects [X] but it's not present. Task [M] (which should have produced it) is marked Complete. Task [M]'s output may be semantically incorrect. Review Task [M]'s code before proceeding."**
     - If the precondition references something that should already exist in the codebase (no upstream task), report: **"Contract violation: Task [N] expects [X] but it's not present in the codebase. The breakdown may be based on stale assumptions."**
     - STOP execution — do not proceed to Phase 3

If ANY pre-flight check fails, stop and inform the user with specifics.

### 2.5: Create WIP Marker and Clean Checkpoint

1. Create a git checkpoint BEFORE any changes:
   ```
   git commit -m "[checkpoint] Pre-task [N]: [title]" --allow-empty
   ```
   This gives us a clean rollback point.

2. **Source repo checkpoint** (wrapper mode only, `SOURCE_ROOT != "."`):
   - Check for pre-existing uncommitted source changes: `git -C $SOURCE_ROOT status --porcelain`. If there are uncommitted changes, warn: "Source repo has uncommitted changes. These will be included in the WIP commits. Stash or commit them first if you want them separate." Let the user decide to proceed or stop.
   - Create source checkpoint:
     ```
     git -C $SOURCE_ROOT commit -m "[WIP] checkpoint" --allow-empty
     ```
   - Record this hash as `$SOURCE_CHECKPOINT`.

3. Write `.claude/wip.md`:
   ```markdown
   # Work In Progress

   ## Command
   execute-task

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

   ## Source Repo Checkpoint
   Commit: [source-checkpoint-hash or N/A for standalone]
   Branch: [source-branch-name or N/A]
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
4. Every file you change must pass the project's type checker (see Type Check Command in CLAUDE.md)
5. Every file you change must pass the project's linter (see Lint Command in CLAUDE.md)
6. Document any new functions/variables you create

## Contract: What This Task Must Produce
[Items from the task's Contracts → Produces section]
These postconditions will be independently verified after you complete.

## Done When
[Done conditions from breakdown]

## Do NOT
- Refactor surrounding code
- Add features not in the task
- Change files not listed above (unless absolutely necessary for compilation)
- Skip the project's type checker or linter
```

After the agent completes, immediately create a WIP git commit to preserve the work:
```
git add [files you modified] .claude/wip.md && git commit -m "[WIP] Task [N]: [title] — agent execution complete"
```

**Source repo WIP** (wrapper mode only, `SOURCE_ROOT != "."`):
```
git -C $SOURCE_ROOT add -A && git -C $SOURCE_ROOT diff --cached --quiet || git -C $SOURCE_ROOT commit -m "[WIP] task execution"
```

Update `.claude/wip.md` — change Phase to `4 (Mark Complete)`.

### 3.3: Post-Agent Verification (with Self-Repair)

After the agent completes, run verification:

1. **Files changed match task scope**: Check `git diff --name-only` (or `git status` for new files) against the task's file list. If extra files were changed, investigate why.
2. **Type checker passes**: Run the Type Check Command from CLAUDE.md (e.g. `tsc --noEmit` for TypeScript, `mypy` for Python, `go vet` for Go). The PostToolUse hook should catch this, but verify explicitly.
3. **Linter passes**: Run the Lint Command from CLAUDE.md on all changed files
4. **Project builds** (if Build Command is specified in CLAUDE.md): Run the build command. For wrapper mode projects, run inside the Source Root directory. Skip this check if no Build Command is configured.
5. **Done conditions met**: Check each "Done when" item from the task
6. **Contract postconditions**: Read the task's `## Contracts → ### Produces` section. For each postcondition, use Grep or Read to verify it holds in the codebase (e.g., verify the export exists, the interface has the expected fields, the function has the expected name). Track pass/fail for each postcondition.
7. **Run affected tests**: Search for test files (`*.test.*`, `*.spec.*`) in the same directories as changed files. If test files exist and a test runner is available (check CLAUDE.md for Test Command, or detect via package.json scripts), run them. If no test files or test runner exist, skip this check. Test failures are treated the same as other verification failures.
8. **Wrapper isolation check** (wrapper mode only): Verify no Claude artifacts were created inside the Source Root. Scan `SOURCE_ROOT/` for files matching: `.claude/`, `specs/`, `docs/overview.md`, `docs/architecture.md`, `constitution.md`, `CLAUDE.md`, `bugs/`, `research/`, `.mcp.json`. If any are found, flag as a verification failure.

**If ALL checks pass** → proceed to Phase 4.

**If any check fails** → enter the self-repair loop (max 3 attempts):

For each repair attempt:
1. Collect all error output (tsc errors, lint errors, build errors, test failures, unmet done-conditions, contract postcondition failures)
2. Launch a **repair agent** (using the Task tool) with:
   - The original task description and scope constraints
   - The specific errors to fix (full error output)
   - For contract failures: include the exact postcondition that failed and what was found instead (e.g., "Expected export `cartTotals` in CartBLoC.ts but found `getCartTotal`")
   - The list of files that were changed
   - Clear instruction: **"Fix ONLY these errors. Do not add features, refactor, or change scope. Stay within the files listed."**
3. After the repair agent completes, commit:
   ```
   git add [files you modified] .claude/wip.md && git commit -m "[WIP] Task [N]: [title] — repair attempt [M]/3"
   ```
   **Source repo WIP** (wrapper mode only): `git -C $SOURCE_ROOT add -A && git -C $SOURCE_ROOT diff --cached --quiet || git -C $SOURCE_ROOT commit -m "[WIP] repair"`
4. Re-run ALL verification checks above

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
   - In the **Done When** section, change every `- [ ]` to `- [x]` for conditions that were verified as met
   - Fill in the Completion Notes section:
     ```
     **Completed**: [date/time]
     **Files changed**: [actual files that changed]
     **Contract**: Expects [X/Y verified] | Produces [X/Y verified]
     **Notes**: [any deviations from plan or things to watch]
     ```
3. Update the task index (`specs/NNN-feature/tasks/README.md`) — mark this task's status as Complete

After marking the task complete in task files, commit:
```
git add specs/ .claude/wip.md && git commit -m "[WIP] Task [N]: [title] — marked complete"
```

Update `.claude/wip.md` — change Phase to `5 (Documentation Update)`.

## PHASE 5: Documentation Update (MANDATORY)

After code is verified, launch the **tech-writer** agent to update documentation.

### 5.0: Load Tech-Writer Agent

Read `.claude/agents/tech-writer.md` and include its **full content** as the opening section of the agent prompt. This file contains the tech-writer's complete Normal Mode workflow (6 steps, 2-layer documentation model, skip/include criteria, formatting rules).

If `.claude/agents/tech-writer.md` does not exist, warn: "⚠️ Tech-writer agent file not found — documentation quality may be reduced. Run `/setup-wizard` to generate agent files." Proceed with the inline prompt alone.

### 5.1: Build and Launch Tech-Writer Prompt

Construct the tech-writer prompt with two parts:

**Part 1** (if agent file exists): The full content of `.claude/agents/tech-writer.md` (this gives the agent its complete workflow and rules — it will auto-select Normal Mode).

**Part 2** (always included): The task-specific context below.

```
You are updating documentation after Task [N] from an approved task breakdown.

## Completed Task
[Full task description and completion notes from breakdown]

## Feature Context
[Relevant section from spec.md — what this feature does and why]

## Files Changed
[List of files actually changed, from completion notes]

## Existing Docs
[Output of Glob on docs/ — so you know what already exists]

## Instructions

You must address BOTH documentation layers:

**Layer 1 — Inline docs**: For every new or changed public export (function, class, component, type), add or update inline documentation (JSDoc/docstrings) in the source file.

**Layer 2 — docs/ folder**: Check if any existing doc in docs/ covers this area — if so, update it. If this task introduces a new feature area with no existing doc, create docs/features/[name].md.

### Document when ANY of these apply:
- A new public API, function, or component was created
- Existing behavior was changed in a way users/developers need to know
- A new architectural pattern was introduced
- A new configuration option was added
- A workflow or process changed

### Skip documentation ONLY when ALL of these apply:
- Internal refactoring with no behavior change
- Bug fixes that restore expected (already-documented) behavior
- Type-only changes with no semantic difference
- Test-only changes

If you determine documentation is not needed, you must justify by:
1. Listing which skip criteria apply
2. Confirming that NONE of the "Document when" criteria are triggered

### Before completing:
Verify every code example matches the actual implementation and every file path mentioned is correct. Cross-check inline doc signatures against the real function signatures.

## Rules
1. Only document what exists — code that is implemented and verified
2. Every new public export gets inline docs (JSDoc/docstring)
3. Match existing doc style in the project
4. Code examples must come from actual implementation
5. Do NOT modify logic, specs, or task files — only add documentation
6. Include @example for non-trivial public APIs
7. Match the existing inline doc style in the file (if other functions have JSDoc, use JSDoc)
```

Launch the tech-writer agent with the combined prompt (Part 1 + Part 2) using the Agent tool.

### 5.2: Post-Doc Verification

After the tech-writer completes, verify documentation was handled:

1. **Check for new AND changed public APIs**: Run `git diff [checkpoint-commit-hash]` (not just `--name-only`) and scan changed files for:
   - New exported functions, classes, components, or types — verify they have inline documentation
   - Changed signatures on existing public exports (parameter or return type changes) — verify inline docs are updated to match
2. **Check `docs/` for updates**: If public APIs were added, behavior changed, or architecture was restructured, verify that at least one file in `docs/` was created or modified (check `git diff --name-only` for paths starting with `docs/`).
3. **Check for stale doc references**: If any existing `docs/` file references the changed source files (search docs/ for the filenames), verify those references are still accurate.
4. **If the tech-writer reported "No documentation needed"**: Verify the justification — check that the listed skip criteria actually apply AND that none of the "Document when" criteria are triggered. If the justification is insufficient or contradicted by the diff, re-invoke the tech-writer with explicit instruction: "The following changes require documentation: [list specific APIs/behaviors]. Add inline docs and update docs/ accordingly."

### 5.3: Commit Doc Changes

If the tech-writer made any changes, commit them:
```
git add docs/ [source files with doc changes] && git commit -m "[WIP] Task [N]: [title] — documentation update"
```

**Source repo WIP** (wrapper mode only, if source files were touched): `git -C $SOURCE_ROOT add -A && git -C $SOURCE_ROOT diff --cached --quiet || git -C $SOURCE_ROOT commit -m "[WIP] docs"`

Update `.claude/wip.md` — change Phase to `6 (Report)`.

## PHASE 6: Report

Provide a concise summary to the user:

```
## Task [N] Complete: [Title]

**Changes**:
- [file]: [what changed, 1 line]
- [file]: [what changed, 1 line]

**Verification**:
- Type checker: PASS
- Linter: PASS
- Build: PASS [or SKIP if no build command configured]
- Done conditions: [all met / exceptions]
- Contracts: Expects [X/Y] | Produces [X/Y]

**Documentation**: [Updated docs/features/X.md / Created docs/api/Y.md / No docs needed]

**Spec criteria addressed**: AC-[numbers]

**Next task**: [NNN]-[title] (ready / blocked by [NNN])
```

### Final Commit and WIP Cleanup

1. Squash all `[WIP]` and `[checkpoint]` commits for this task into a single clean commit.

   First, verify WIP commits haven't been pushed to the remote:
   ```
   git log --oneline origin/$(git branch --show-current)..HEAD 2>/dev/null
   ```
   - If this shows commits (or fails because there's no upstream) → WIP commits are **local only** → safe to squash:
     ```
     git reset --soft [checkpoint-commit-hash]
     git commit -m "feat([feature-name]): Task [N] — [title]"
     ```
     If the commit fails after the reset (pre-commit hook rejection, etc.), do NOT delete `.claude/wip.md`. Inform the user: "Squash reset was applied but the commit failed. Your changes are staged. Run `git commit` manually to complete, or `git reset HEAD~0` to unstage."
   - If this shows **no commits** (HEAD matches remote) → WIP commits were already pushed → **skip squashing** and keep commits as-is.

   Follow the **Commit Convention** section in CLAUDE.md (format and attribution rules).

2. Delete `.claude/wip.md` (only after the final commit succeeds)

The task is now fully committed with a clean single commit and no WIP artifacts.

> **Source repo note** (wrapper mode): Source WIP commits are intentionally NOT squashed here. They accumulate across tasks and are squashed into a single clean commit when `/verify` approves the feature (Phase 9.5).

## PHASE 7: Memory Update

If anything unexpected happened during execution (a gotcha, a pattern discovery, a near-mistake), update `.claude/memory/MEMORY.md`.

Use the format: `- **[AREA]**: [observation] _(Task N / Feature NNN)_`. Add entries under the matching section in MEMORY.md (Known Pitfalls, What Worked, What Failed, External API Quirks, etc.).

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

After writing session-state.md, verify its line count. If over 40 lines, trim oldest entries from "Key Decisions This Session" and "Files Modified Recently" until the file is under 40 lines.

### 7.5.2: Context Health Check

Read the "Tasks completed this session" count from the session-state you just wrote.

**If light (1-2 tasks):** No action. Just report task completion normally.

**If moderate (3-5 tasks):** Add a recommendation after the task report:

```
💡 Context maintenance: [N] tasks completed this session.
Optional: Run /compact with these instructions:

/compact Preserve: (1) Current task statuses from specs/[feature]/tasks/README.md, (2) All entries from .claude/memory/MEMORY.md, (3) Constitution rules referenced during this session, (4) Next task's file list and change details from its task file, (5) Session state from .claude/session-state.md, (6) Phase 5 documentation obligation: every task MUST run the tech-writer agent and verify docs before Phase 6. Discard: file contents already committed, old error outputs, superseded diffs, resolved discussions.

Or continue to next task if context still feels responsive.
```

**If heavy (6+ tasks):** Strongly recommend compaction:

```
🔴 Context maintenance: [N] tasks completed this session (heavy context load).
Strongly recommended: Run /compact before continuing.

/compact Preserve: (1) Current task statuses from specs/[feature]/tasks/README.md, (2) All entries from .claude/memory/MEMORY.md, (3) Constitution rules referenced during this session, (4) Next task's file list and change details from its task file, (5) Session state from .claude/session-state.md, (6) Phase 5 documentation obligation: every task MUST run the tech-writer agent and verify docs before Phase 6. Discard: file contents already committed, old error outputs, superseded diffs, resolved discussions.
```

Do NOT auto-compact. Surface the recommendation and let the user decide. For single-task mode, this is advisory only — the user may choose to continue without compacting.

> **Note**: Phase 7.5.2 (single-task) recommends compaction; Phase 8 (multi-task, heavy) pauses execution. The difference is intentional: single-task completion is advisory, multi-task continuation requires the pause to prevent context degradation across many sequential tasks.

### 7.5.3: Auto-Verify on Feature Completion

After Phase 7.5.2 completes (for both single-task and multi-task paths), check whether the entire feature is now done:

1. Read `specs/[feature]/tasks/README.md` and check whether **every** task in the feature has Status: `Complete`.
2. If **all tasks are Complete**: skip the normal completion report and instead:
   ```
   ✅ All feature tasks complete — automatically running /verify
   ```
   Then invoke `/verify` with the feature's spec file path. This replaces the normal end-of-execution flow (no Multi-Task Final Report needed).
3. If any tasks remain non-Complete: continue with the normal flow (single-task completion report or Phase 8 multi-task continuation).

## PHASE 8: Multi-Task Continuation

This phase only applies when the task queue (built in Phase 1.1) contains more than one task.

After Phase 7.5 completes for the current task:

1. Remove the completed task from the queue
2. If the queue is empty → Phase 7.5.3 (Auto-Verify) already handled feature-complete detection. If it did not trigger (some tasks outside the queue are still pending), report the Multi-Task Final Report below.
3. If the queue has remaining tasks:
   a. **Dependency check**: Verify the next task's dependencies are all satisfied (marked Complete). If not, stop and report: "Task [N] is blocked by incomplete dependency Task [M]. Completed [X] of [Y] queued tasks."
   a2. **Review checkpoint gate**: Read the next task's header. If `Review checkpoint: Yes`:
      ```
      ⏸️ REVIEW CHECKPOINT before Task [N]: [title]

      Preceding tasks completed:
      - Task [X]: [1-line summary] — Contract: Expects [A/B] | Produces [C/D]
      - Task [Y]: [1-line summary] — Contract: Expects [A/B] | Produces [C/D]

      Options:
      1. **Continue** — contracts pass, proceed to Task [N]
      2. **Review** — show git diff from preceding tasks before continuing
      3. **Pause** — stop execution here, resume later with /execute-task [N]
      ```
      Wait for user response:
      - **Continue**: proceed to step b.
      - **Review**: show `git diff` for the preceding tasks' commits. After user reviews, ask again: Continue or Pause.
      - **Pause**: clean up WIP state (delete `.claude/wip.md`), stop execution. Report completed tasks so far.
   b. **Context health**: Read the "Tasks completed this session" count from session-state.md.
      - If heavy (6+ tasks): **pause execution** and present the compaction command to the user:
        ```
        🔴 CONTEXT HEALTH PAUSE — [N] tasks completed this session (heavy context load).
        Strongly recommended: Run /compact before continuing.

        /compact Preserve: (1) Current task statuses from specs/[feature]/tasks/README.md, (2) All entries from .claude/memory/MEMORY.md, (3) Constitution rules referenced during this session, (4) Next task's file list and change details from its task file, (5) Session state from .claude/session-state.md, (6) Phase 5 documentation obligation: every task MUST run the tech-writer agent and verify docs before Phase 6. Discard: file contents already committed, old error outputs, superseded diffs, resolved discussions.

        Then resume with: /execute-task [remaining-task-ids]
        ```
        Stop execution here. Do NOT continue to the next task without user-initiated compaction.
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
9. **Context hygiene** — always fully overwrite .claude/session-state.md after each task (never append). Keep it under 40 lines. Recommend /compact at moderate load. In multi-task mode, pause execution at heavy load (6+ tasks) and ask the user to run /compact before resuming.
10. **Documentation is non-negotiable** — Phase 5 MUST run for every task, including in multi-task mode. The tech-writer agent must be invoked and its output verified (new public APIs must have inline docs). Skipping Phase 5 is a workflow violation equivalent to skipping verification.
11. **Crash safety** — always write .claude/wip.md before starting execution and delete it only after the final commit. If wip.md exists at the start of execute-task, enter recovery flow. Never delete wip.md without either completing the task or explicitly rolling back.
