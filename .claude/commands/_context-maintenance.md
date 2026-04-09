# Context Maintenance: Post-Task Bookkeeping

This file is read by `/execute-task` after every task completion (Phase 5.2). It manages session state and context health.

Context from the caller: the current feature directory, the task number and title just completed.

## 7.1: Update Session State

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

After writing session-state.md, verify its line count. If over 40 lines, trim oldest entries from "Key Decisions This Session" and "Files Modified Recently" until under 40 lines.

## 7.2: Context Health Check

Read the "Tasks completed this session" count from the session-state you just wrote.

**If light (1-2 tasks):** No action. Report task completion normally.

**If moderate (3-5 tasks):** Add a recommendation after the task report:

```
💡 Context maintenance: [N] tasks completed this session.
Optional: Run /compact with these instructions:

/compact Preserve: (1) Current task statuses from specs/[feature]/tasks/README.md, (2) All entries from .claude/memory/MEMORY.md, (3) Constitution rules referenced during this session, (4) Next task's file list and change details from its task file, (5) Session state from .claude/session-state.md, (6) Inline documentation rule: implementing agents write JSDoc/docstrings for new public APIs, code-reviewer verifies this in Phase 3.3. Feature-level docs in docs/ are handled by the tech-writer at /finalize time, (7) Completion Notes sections from all completed task files in specs/[feature]/tasks/ — these contain prior decisions, actual files changed, and deviations that inform later tasks. Discard: file contents already committed, old error outputs, superseded diffs, resolved discussions.

Or continue to next task if context still feels responsive.
```

**If heavy (6+ tasks):** Strongly recommend compaction:

```
🔴 Context maintenance: [N] tasks completed this session (heavy context load).
Strongly recommended: Run /compact before continuing.

/compact Preserve: (1) Current task statuses from specs/[feature]/tasks/README.md, (2) All entries from .claude/memory/MEMORY.md, (3) Constitution rules referenced during this session, (4) Next task's file list and change details from its task file, (5) Session state from .claude/session-state.md, (6) Inline documentation rule: implementing agents write JSDoc/docstrings for new public APIs, code-reviewer verifies this in Phase 3.3. Feature-level docs in docs/ are handled by the tech-writer at /finalize time, (7) Completion Notes sections from all completed task files in specs/[feature]/tasks/ — these contain prior decisions, actual files changed, and deviations that inform later tasks. Discard: file contents already committed, old error outputs, superseded diffs, resolved discussions.
```

Do not auto-compact. Surface the recommendation and let the user decide. For single-task mode, this is advisory only.

> **Note**: Phase 7.2 (single-task) recommends compaction; Phase 8 (multi-task, heavy) pauses execution. The difference is intentional: single-task completion is advisory, multi-task continuation requires the pause to prevent context degradation across many sequential tasks.
