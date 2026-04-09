# Multi-Task Continuation

This file is read by `/execute-task` when the task queue (built in Phase 1.1) contains more than one task. Read this after Phase 5.2 (context maintenance) completes for the current task.

Context from the caller: the remaining task queue, the current feature directory.

## Queue Processing

After Phase 5.2 completes for the current task:

1. Remove the completed task from the queue
2. If the queue is empty → report the Multi-Task Final Report below.
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
      - If heavy (6+ tasks): **pause execution** and present the compaction command:
        ```
        🔴 CONTEXT HEALTH PAUSE — [N] tasks completed this session (heavy context load).
        Strongly recommended: Run /compact before continuing.

        /compact Preserve: (1) Current task statuses from specs/[feature]/tasks/README.md, (2) All entries from .claude/memory/MEMORY.md, (3) Constitution rules referenced during this session, (4) Next task's file list and change details from its task file, (5) Session state from .claude/session-state.md, (6) Inline documentation rule: implementing agents write JSDoc/docstrings for new public APIs, code-reviewer verifies this in Phase 3.3. Feature-level docs in docs/ are handled by the tech-writer at /finalize time, (7) Completion Notes sections from all completed task files in specs/[feature]/tasks/ — these contain prior decisions, actual files changed, and deviations that inform later tasks. Discard: file contents already committed, old error outputs, superseded diffs, resolved discussions.

        Then resume with: /execute-task [remaining-task-ids]
        ```
        Stop execution here. Do NOT continue to the next task without user-initiated compaction.
      - If light/moderate: continue without compaction.
   c. **Loop back** to Phase 1 for the next task in the queue. The task queue carries over — do not re-parse `$ARGUMENTS`.

## Multi-Task Final Report

When all queued tasks are complete (or execution stops due to failure/blocked dependency):

```
## Batch Execution Complete

**Tasks completed**: [list with status]
**Tasks skipped/blocked**: [list with reason, if any]
**Total verification**: [all passed / N repair cycles needed]

**Feature progress**: [X of Y tasks complete]
**Next pending**: Task [N] — [title] (ready / blocked by [M])

**Next steps**: Run `/review` → `/verify` → `/summarize` → `/finalize`
```
