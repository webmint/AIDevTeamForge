# Research: tasks-not-saving

**Date**: 2026-05-14
**Topic**: tasks-not-saving
**Mode**: Bug
**Verdict**: Root cause hypothesis (needs repro)

## Summary

Tasks created in the workspace view never round-trip to the persistence layer; recommended fix is to await the persistence promise before clearing the form state.

## Symptom

| Dimension | Value |
|---|---|
| Symptom | Newly-created task disappears on view refresh |
| Affected area | Workspace > Tasks > Create flow |
| Repro / Current | Click Create, refill form, refresh view |
| Desired | Task persists across refresh |
| Scope | One feature module |

## Codebase Findings (WHERE)

| Surface | File:line | Relevance |
|---|---|---|
| tasks store | src/workspace/tasksStore.ts:88 | clears local state before await resolves |
| create handler | src/workspace/Tasks.vue:142 | fires-and-forgets the persistence call |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: persistence promise is not awaited; local state clears optimistically while network call is still in flight.

**Confidence**: Hypothesis

### Structured root cause

| Field | Value |
|---|---|
| trigger | User submits the Create form |
| root_cause | Store mutation runs before await on the persistence call returns |
| contributing_factors | 1. No e2e covers the persist-then-refresh flow 2. Handler uses .then() without error path |

## Hypothesis Enumeration

| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |
|---|---|---|
| missing await on persistence call | inject an await; verify task survives refresh | no |
| optimistic store cleared on rejection | mock a network failure; verify task remains visible | yes |

## Recommended Verify Step

| Sub-field | Value |
|---|---|
| probe | console.log persistence-response at tasksStore.ts:88 |
| reproduction | Open Tasks; create task; refresh page within 200ms |
| discriminator | if persistence-response arrives after refresh then await missing; if response arrives before but task missing then store reset bug |

## Approaches (HOW to change)

### Option A: Await persistence in handler before clearing local state
- **Description**: Add an `await` to the create handler so local state clears only after the persistence resolves.
- **Addresses hypothesis**: missing await on persistence call
- **Does NOT cover**: optimistic store cleared on rejection
- **Pros**: small diff; mirrors existing edit handler shape
- **Cons**: handler becomes async-only
- **Complexity**: Low

### Option B: Move clear-state to a persistence-success callback
- **Description**: Only clear the form when the persistence call confirms success; surface errors otherwise.
- **Addresses hypothesis**: missing await on persistence call, optimistic store cleared on rejection
- **Does NOT cover**: (none)
- **Pros**: covers both hypotheses; adds error surface
- **Cons**: extra branch; needs error UI
- **Complexity**: Med

**Recommended approach**: Option B: Move clear-state to a persistence-success callback — closes both hypotheses; surfaces failures so future regressions are visible

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| Rule 4.2 — UI mutations must reflect persisted state | Forces the success-callback ordering |

## Complexity Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Codebase changes | Low | 1 module |
| Risk | Low | edit handler untouched |
| Verify cost | Med | needs e2e for persist-then-refresh |

## Next step

Copy the block below into a new `/devforge:specify` session manually. No automation — user controls when (or if) `/devforge:specify` runs.

~~~
/devforge:specify "Tasks created in workspace view disappear on refresh — make new tasks persist across refresh"

Research reference: research/2026-05-14-tasks-not-saving.md
Key facts:
- Mode: Bug
- Symptom: Newly-created task disappears on view refresh
- Desired: Task persists across refresh
- Recommended approach: Option B: Move clear-state to a persistence-success callback
- Hypothesis addressed: missing await on persistence call, optimistic store cleared on rejection
- Hypotheses NOT covered: (none)
- Open uncertainties: 0 (see research doc §Open Uncertainties)
~~~
