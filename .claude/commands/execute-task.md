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

## Source Repo Auto-Commit (Wrapper Mode)

Skip this section entirely when `SOURCE_ROOT` is `.` (standalone mode).

**Checkpoint**: At the start of execution, create an empty checkpoint in the source repo:
`git -C $SOURCE_ROOT commit -m "[WIP] checkpoint" --allow-empty` → store hash as `$SOURCE_CHECKPOINT`

**WIP commit**: After code passes verification (Phase 3.3), commit all source changes:
`git -C $SOURCE_ROOT add -A && git -C $SOURCE_ROOT diff --cached --quiet || git -C $SOURCE_ROOT commit -m "[WIP] source changes"`

**Squash**: For execute-task, source WIP commits are NOT squashed here — they accumulate across tasks and are squashed by `/verify` Phase 9.5 when the feature is approved.

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
7. **Read referenced documentation**: If the task file has a `Context docs` field with specific file paths, read those files. Do not search `docs/` broadly — the breakdown already identified which docs are relevant for this task.

Verify:
- Task exists and is not already completed
- All dependencies (listed in "Depends on") are marked complete
- The assigned agent matches what's available

### 1.3: AC Verification Readiness Check

Read `AC_VERIFICATION` from `.claude/project-config.json`. If the value is `"off"` or the key does not exist, skip this check entirely.

If `AC_VERIFICATION` is `"auto"` or `"browser-only"`:
1. Attempt to call `mcp__chrome-devtools__list_pages` as a lightweight probe.
2. If it **fails** (MCP not available):
   - Display: "Note: Chrome DevTools MCP is not running. When `/verify` runs after this task, frontend AC items will be verified by code reading instead of browser interaction. To enable browser-based AC verification, start the WebStorm JS debugger before running `/verify`."
   - This is informational only — do not block execution.
3. If it **succeeds**: no message needed.

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
6. Document any new functions/variables you create

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

Address both documentation layers (inline docs + docs/ folder) using the document-when/skip-when criteria and rules from the tech-writer workflow (Part 1). Apply them to the task context above.

If you determine documentation is not needed, justify by listing which skip criteria apply and confirming no "Document when" criteria are triggered.
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

Read `.claude/commands/_context-maintenance.md` and follow its instructions.
Context: the current feature directory, the task number and title just completed.

## PHASE 8: Multi-Task Continuation

This phase only applies when the task queue (built in Phase 1.1) contains more than one task.

Read `.claude/commands/_multi-task-continuation.md` and follow its instructions.
Context: the remaining task queue, the current feature directory.

## RULES

1. **Always delegate** — NEVER write implementation code yourself. Every task MUST be executed by launching the assigned agent via the Agent tool, no matter how small or trivial the task appears. You are the orchestrator: you load context, launch agents, verify results, and coordinate. If you catch yourself about to edit a source file directly instead of delegating to an agent, stop — that is a rule violation.
2. **Scope discipline** — if the agent changes files outside the task scope, revert those changes and investigate
3. **Self-repair before escalation** — when verification fails, attempt automatic repair (up to 3 times) before stopping. Never skip repair attempts.
4. **Hard stop on repair failure** — if all 3 repair attempts fail, stop the entire execution chain (including remaining queued tasks). Do not proceed with broken state.
5. **Documentation is non-negotiable** — Phase 5 MUST run for every task, including in multi-task mode. The tech-writer agent must be invoked and its output verified.
6. **Crash safety** — always write .claude/wip.md before starting execution and delete it only after the final commit. If wip.md exists at the start, enter recovery flow.
7. **Context hygiene** — fully overwrite .claude/session-state.md after each task (never append). Keep it under 40 lines.
