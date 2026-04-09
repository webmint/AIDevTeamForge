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
  - **Comma-separated** (e.g. `1,3,5`): Execute these specific tasks sequentially in the active feature. Each task gets the full Phase 0–7 treatment.
  - **Range** (e.g. `1-5`): Execute tasks 1 through 5 sequentially. Equivalent to `1,2,3,4,5`.
  - **`all`**: Execute all pending tasks in the active feature, in dependency order.

## Prerequisites

1. Task files must exist in `specs/NNN-feature/tasks/`
2. The specified task's dependencies must all be completed (status: Complete)
3. If dependencies are not met, inform the user which tasks must be completed first

## Source Repo Auto-Commit (Wrapper Mode)

Skip this section entirely when `SOURCE_ROOT` is `.` (standalone mode).

**Checkpoint**: At the start of execution, create an empty checkpoint in the source repo:
`git -C $SOURCE_ROOT commit -m "[WIP] checkpoint" --allow-empty` → store hash as `$SOURCE_CHECKPOINT`

**WIP commit**: After code passes verification (Phase 3.3), commit all source changes:
`git -C $SOURCE_ROOT add -A && git -C $SOURCE_ROOT diff --cached --quiet || git -C $SOURCE_ROOT commit -m "[WIP] source changes"`

**Squash**: For execute-task, source WIP commits are NOT squashed here — they accumulate across tasks and are squashed by `/finalize` when the feature is approved.

**Recovery**: Phase 0 checks source repo state via wip.md's `## Source Repo Checkpoint` section. Rollback resets source: `git -C $SOURCE_ROOT reset --hard $SOURCE_CHECKPOINT`.

## PHASE 0: Recovery Check

Before anything else, check if a previous task execution was interrupted.

Read `.claude/wip.md`. If it does NOT exist, skip to PHASE 1.

If it exists, read `.claude/commands/_recovery.md` and follow its instructions with `CALLING_COMMAND = execute-task`.

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

**If `$ARGUMENTS` matches the pattern `number-number`** (e.g. `1-5`, `01-10` — both parts must be numeric):
- Parse as range: start number to end number (inclusive)
- Task queue = expanded range in order
- Skip any tasks in the range that are already Complete

**If `$ARGUMENTS` is a single number** (e.g. `3`):
- Task queue = `[that number]` (single task)

**If `$ARGUMENTS` is empty**:
- Task queue = `[next pending task]` (lowest number with all dependencies satisfied)

**If `$ARGUMENTS` matches none of the above patterns**:
- STOP with: "Unrecognized argument format: `[input]`. Expected: a task number (e.g. `3`), range (`1-5`), comma list (`1,3,5`), `all`, or feature/task (`001/3`)."

### 1.1.1: Validate Task Queue

After building the task queue, validate every task number in it before proceeding:

1. For each task number in the queue, check that a matching task file exists in `specs/NNN-feature/tasks/` (glob for `NNN-*.md` where NNN matches the task number, zero-padded).
2. If any task number has no matching file, STOP with: "Task [N] does not exist in `specs/[feature]/tasks/`. Available tasks: [list available task numbers and titles]."
3. If the task queue is empty after filtering (e.g., all tasks in a range are already Complete), inform the user: "No pending tasks match the requested range/selection."

For multi-task queues: the current task is always the first item. After it completes (Phase 4), the remaining queue is processed via Phase 5.3 (Multi-Task Continuation).

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
7. **Read referenced documentation**: If the task file has a `Context docs` field with specific file paths, read those files. Do not search `docs/` broadly — the breakdown already identified which docs are relevant for this task.
8. **Read prior task completion notes**: For each completed task in this feature (check task index for tasks with Status: Complete), read the `## Completion Notes` section from their task file. This provides context about what earlier tasks decided, which files they actually changed, and any deviations from the plan. For features with many completed tasks (10+), read only the completion notes from tasks listed in the current task's "Depends on" field and the 3 most recently completed tasks.

Verify:
- Task exists and is not already completed
- All dependencies (listed in "Depends on") are marked complete
- The assigned agent matches what's available

## PHASE 2: Pre-Flight Check

Before writing code, verify:

1. **Constitution populated**: If `constitution.md` contains `_Run /constitute to populate_`, stop immediately and inform the user: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/execute-task`."
2. **Constitution compliance**: Does the planned change violate any NON-NEGOTIABLE rules?
3. **Memory check**: Does MEMORY.md have any warnings about similar changes?
4. **File state check**:
   - **Existing files**: Are the target files in the expected state? (No unexpected changes since the breakdown was created)
   - **New files (greenfield)**: Does the target directory exist? If not, it should be created as part of this task or a prior task
5. **Type safety**: Read the type definitions involved and verify the change is type-safe on paper. For greenfield, verify the proposed types align with the constitution's patterns
6. **Contract preconditions**: Read the task's `## Contracts → ### Expects` section. For each precondition:
   - Verify each condition holds in the current codebase. For simple existence checks (export exists, function exists), Grep is sufficient. For structural checks (interface has specific fields, function has specific signature), Read the file and verify the full structure — do not rely on Grep alone for structural contracts
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

### 3.1: Launch Agent

**MANDATORY**: You MUST use the Agent tool to launch the assigned agent for every task, regardless of task size or complexity. You are the orchestrator — your role is to delegate, verify, and coordinate, never to write implementation code yourself. Even if the task is a single line change, a boilerplate file, or "trivial" — launch the agent. Skipping the agent launch violates the team's division of responsibilities: you manage the process, agents write the code.

Use the Agent tool to launch the agent specified in the task's "Agent" field.

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
6. Add inline documentation (JSDoc/docstrings) to every new public function, class, type, or interface you create. This is part of writing the code, not a separate step

## Documentation Context
[Content from the doc files listed in the task's Context docs field, if any. Omit this section if Context docs is "None".]

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

Update `.claude/wip.md` — change Phase to `3.2 (Verification)`.

### 3.2: Post-Agent Verification (with Self-Repair)

After the agent completes, run verification:

1. **Files changed match task scope**: Check `git diff --name-only` (or `git status` for new files) against the task's file list. If extra files were changed, investigate why.
2. **Type checker passes**: Run the Type Check Command from CLAUDE.md (e.g. `tsc --noEmit` for TypeScript, `mypy` for Python, `go vet` for Go). The PostToolUse hook should catch this, but verify explicitly.
3. **Linter passes**: Run the Lint Command from CLAUDE.md on all changed files
4. **Project builds** (if Build Command is specified in CLAUDE.md): Run the build command. For wrapper mode projects, run inside the Source Root directory. Skip this check if no Build Command is configured.
5. **Done conditions met**: Check each "Done when" item from the task
6. **Contract postconditions**: Read the task's `## Contracts → ### Produces` section. For each postcondition, verify it holds in the codebase. For simple existence checks (export exists, function exists), Grep is sufficient. For structural checks (interface has specific fields, function has specific signature), Read the file and verify the full structure. Track pass/fail for each postcondition.
7. **Run affected tests**: Search for test files (`*.test.*`, `*.spec.*`) in the same directories as changed files. If test files exist and a test runner is available (check CLAUDE.md for Test Command, or detect via package.json scripts), run them. If no test files or test runner exist, skip this check. Test failures are treated the same as other verification failures.
8. **Wrapper isolation check** (wrapper mode only): Verify no Claude artifacts were created inside the Source Root. Scan `SOURCE_ROOT/` for files matching: `.claude/`, `specs/`, `docs/overview.md`, `docs/architecture.md`, `constitution.md`, `CLAUDE.md`, `bugs/`, `research/`, `.mcp.json`. If any are found, flag as a verification failure.

**Source repo WIP** (wrapper mode only): After all checks pass, run the **WIP commit** from the Source Repo Auto-Commit section above.

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
4. Re-run ALL verification checks above

**If verification passes after any attempt** → proceed to Phase 4.

**If all 3 repair attempts are exhausted and checks still fail** → STOP execution entirely:
- Report the remaining errors to the user
- Do NOT proceed to Phase 4 or any subsequent task (even in multi-task mode)
- Keep the WIP marker and commits so the user can inspect the state
- Suggest: "Run `/execute-task [N]` again after manually fixing, or use recovery options"

### 3.3: Code Review

Update `.claude/wip.md` — change Phase to `3.3 (Code Review)`.

After verification passes, launch the **code-reviewer** agent on all files changed by the task.

Provide the agent with:
1. The list of changed files (`git diff --name-only` against the checkpoint commit)
2. The task description and scope constraints
3. The constitution's relevant rules
4. Relevant entries from `.claude/memory/MEMORY.md`

The agent will check: constitution compliance, architecture & patterns, type safety, security basics, code quality (including inline documentation on new public APIs), and memory pitfalls.

**If verdict is APPROVE or warnings only** → proceed to Phase 4. Include warnings in the task report.

**If verdict is REQUEST CHANGES or BLOCK** → report findings to the user immediately:

```
⚠️ Code review for Task [N] found issues:

#### Critical (blocks completion)
- [file:line] — [description]

#### Warning (should fix)
- [file:line] — [description]

Options:
1. **Address now** — fix the issues, then re-run review
2. **Continue** — proceed despite warnings (Critical issues CANNOT be skipped)
3. **Stop** — halt execution, keep WIP state for manual handling
```

Wait for user response:
- **Address now**: Launch a repair agent to fix the review issues. After fixes, re-run the code-reviewer once. If still BLOCK after this second review, STOP and report: "Code review issues persist after repair. Address manually and re-run `/execute-task [N]`."
- **Continue**: Only allowed if there are no Critical issues (warnings only). Proceed to Phase 4 with warnings noted.
- **Stop**: Keep WIP marker and commits. Report completed state for manual handling.

## PHASE 4: Complete & Report

Update `.claude/wip.md` — change Phase to `4 (Complete)`.

### 4.1: Mark Task Complete

1. In the task file (`specs/NNN-feature/tasks/NNN-title.md`):
   - Change **Status** to `Complete`
   - In the **Done When** section, change every `- [ ]` to `- [x]` for conditions that were verified as met
   - Fill in the Completion Notes section:
     ```
     **Completed**: [date/time]
     **Files changed**: [actual files that changed]
     **Contract**: Expects [X/Y verified] | Produces [X/Y verified]
     **Notes**: [any deviations from plan or things to watch]
     ```
2. Update the task index (`specs/NNN-feature/tasks/README.md`) — mark this task's status as Complete

### 4.2: Commit & Cleanup

Commit all changes (source files, task files, any review fixes) in a single `[WIP]` commit:
```
git add [changed source files] specs/ && git commit -m "[WIP] Task [N]: [title] — complete"
```

Delete `.claude/wip.md`.

> **No per-task squash**: WIP commits accumulate across tasks and are squashed into a clean commit by `/finalize` when the feature is approved.

### 4.3: Report

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

**Code review**: [APPROVE / APPROVE with warnings: (list) / addressed after review]

**Spec criteria addressed**: AC-[numbers]

**Next task**: [NNN]-[title] (ready / blocked by [NNN])
```

If this was the last pending task (all other tasks in the feature are Complete), replace the "Next task" line with:
```
✅ All feature tasks complete. Next: run `/review` → `/verify` → `/summarize` → `/finalize`
```

## PHASE 5: Bookkeeping

### 5.1: Memory Update

If anything unexpected happened during execution (a gotcha, a pattern discovery, a near-mistake), update `.claude/memory/MEMORY.md`.

Use the format: `- **[AREA]**: [observation] _(Task N / Feature NNN)_`. Add entries under the matching section in MEMORY.md (Known Pitfalls, What Worked, What Failed, External API Quirks, etc.).

### 5.2: Context Maintenance

Read `.claude/commands/_context-maintenance.md` and follow its instructions.
Context: the current feature directory, the task number and title just completed.

### 5.3: Multi-Task Continuation

This step only applies when the task queue (built in Phase 1.1) contains more than one task. If single-task mode, skip this step.

Read `.claude/commands/_multi-task-continuation.md` and follow its instructions.
Context: the remaining task queue, the current feature directory.

## RULES

1. **Always delegate** — NEVER write implementation code yourself. Every task MUST be executed by launching the assigned agent via the Agent tool, no matter how small or trivial the task appears. You are the orchestrator: you load context, launch agents, verify results, and coordinate. If you catch yourself about to edit a source file directly instead of delegating to an agent, stop — that is a rule violation.
2. **Scope discipline** — if the agent changes files outside the task scope, revert those changes and investigate
3. **Self-repair before escalation** — when automated verification fails (type checker, linter, build), attempt automatic repair (up to 3 times) before stopping. Code review findings are reported to the user, not auto-repaired.
4. **Hard stop on repair failure** — if all 3 repair attempts fail, stop the entire execution chain (including remaining queued tasks). Do not proceed with broken state.
5. **Inline docs are the agent's job** — the implementing agent must add inline documentation (JSDoc/docstrings) to every new public function, class, type, or interface. The code-reviewer verifies this. Feature-level docs in `docs/` are handled by the tech-writer at `/finalize` time.
6. **Crash safety** — always write .claude/wip.md before starting execution and delete it only after the final commit. If wip.md exists at the start, enter recovery flow.
7. **Context hygiene** — fully overwrite .claude/session-state.md after each task (never append). Keep it under 40 lines.
8. **No per-task squash** — WIP commits accumulate and are squashed by `/finalize`. Do not run `git reset --soft` during execute-task.
