# Multi-Task Continuation

This file is read by `/execute-task` when the task queue (built in Phase 1.1) contains more than one task. Read this after Phase 5.2 (context maintenance) completes for the current task.

Context from the caller: the remaining task queue, the current feature directory.

## Queue Processing

After Phase 5.2 completes for the current task:

1. Remove the completed task from the queue
2. If the queue is empty → run the **Batch Gate** below, then report the Multi-Task Final Report.
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
   a3. **Wave boundary**: if the task just completed is the last task of its wave and more tasks remain in the queue, run the **Batch Gate** now (before the next wave starts).
   b. **Context health**: The context guard hook (`.claude/hooks/forge/context-guard.py`) adds a `CONTEXT GUARD` message to a tool result when the main-session context passes its thresholds (default 75 % / 85 % of the window).
      - If a `CONTEXT GUARD` **stop** message appeared since the current task started: do not run the Batch Gate; record `Batch gate pending:` as described there, then **pause execution** and present the compaction command below.
      - If a `CONTEXT GUARD` **wind-down** message appeared, **or** — when the guard is not installed — 6+ tasks were completed this session (the "Tasks completed this session" count in session-state.md): run the **Batch Gate** over the tasks completed so far, then **pause execution** and present the compaction command:
        ```
        🔴 CONTEXT HEALTH PAUSE — [N] tasks completed this session (heavy context load).
        Strongly recommended: Run /compact before continuing.

        /compact Preserve: (1) Current task statuses from specs/[feature]/tasks/README.md, (2) All entries from .claude/memory/MEMORY.md, (3) Constitution rules referenced during this session, (4) Next task's file list and change details from its task file, (5) Session state from .claude/session-state.md, (6) Inline documentation rule: implementing agents write JSDoc/docstrings for new public APIs, code-reviewer verifies this in Phase 3.3. Feature-level docs in docs/ are handled by the tech-writer at /finalize time, (7) Completion Notes sections from all completed task files in specs/[feature]/tasks/ — these contain prior decisions, actual files changed, and deviations that inform later tasks. Discard: file contents already committed, old error outputs, superseded diffs, resolved discussions.

        Then resume with: /execute-task [remaining-task-ids]
        ```
        Stop execution here. Do NOT continue to the next task without user-initiated compaction.
      - Otherwise: continue without compaction.
   c. **Loop back** to Phase 1 for the next task in the queue. The task queue carries over — do not re-parse `$ARGUMENTS`.

## Batch Gate

**When it runs**:
- after the last task of each wave in the queue (the "Waves" table in `tasks/README.md`), so a queue that spans several waves (`all`, a long range) is still checked at every wave boundary; without a Waves table, after the last task of the queue;
- when execution stops early (blocked dependency, Critical, wind-down), over the tasks completed so far;
- **not** on a context-guard STOP: then finish the current task, write `Batch gate pending: [task numbers]` into `.claude/session-state.md`, and stop. The next batch gate (or the build of the next single-task run) covers those tasks too; remove the line once a gate has passed.

**Covers**: every task completed since the last passing batch gate, including tasks listed in a `Batch gate pending:` line of session-state.md.

**Steps**:

1. Run the Build Command from CLAUDE.md through `scripts/forge/gate.sh batch-build -- <command>` (skip if none is configured), with the cache-bypass flag when a build cache is in use (see `/execute-task` 3.2 "Build caches").
2. Run the project's full test suite through `scripts/forge/gate.sh batch-test -- <command>` (the test command from CLAUDE.md's Development Commands, or the test script detected from package.json / the build file). Skip if the project has no test runner.
3. If either fails, enter the same self-repair loop as `/execute-task` 3.2 (max 3 attempts; WIP commit after each repair: `[WIP] Batch gate: repair attempt [M]/3`). Give the repair agent the failing output and the files changed by the batch's tasks.
4. If it still fails after 3 attempts, STOP. Set **Status** back to `In Progress` in the task files of the tasks this gate covers (and in `tasks/README.md`), add `Batch gate failed: [summary]` to their Completion Notes, and report the failure in the Final Report. Tasks must not stay `Complete` on code that does not build or pass its tests.

## Multi-Task Final Report

When all queued tasks are complete (or execution stops due to failure/blocked dependency):

```
## Batch Execution Complete

**Tasks completed**: [list with status]
**Tasks skipped/blocked**: [list with reason, if any]
**Total verification**: [all passed / N repair cycles needed]
**Batch gate**: [build + full tests passed / repaired in N attempts / FAILED: summary]

**Feature progress**: [X of Y tasks complete]
**Next pending**: Task [N] — [title] (ready / blocked by [M])

**Next steps**: Run `/review` → `/verify` → `/summarize` → `/finalize`
```
