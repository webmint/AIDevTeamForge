# Research: export-performance


**Date**: 2026-05-11
**Topic**: export-performance
**Mode**: Enhancement
**Verdict**: Feasible with caveats

## Summary

Async via JobsQueue moves export off the request thread; preserves small-dataset behavior. Probe runtime breakdown first.

## Symptom

| Dimension | Value |
|---|---|
| Symptom | Export should be faster on large datasets |
| Affected area | ExportService background job |
| Repro / Current | 5 min runtime on 100K rows; synchronous |
| Desired | under 30 seconds OR async with progress |
| Scope | Feature-wide; touches DB + service + UI |

## Codebase Findings (WHERE)

| Surface | File:line | Relevance | Framing |
|---|---|---|---|
| ExportService | services/export.ts:88 | synchronous fetch + serialize on the request thread | primary |
| JobsQueue | services/jobs.ts:12 | available but unused for exports | primary |
| upstream chunked write | services/network.ts:54 | egress buffer saturates before serializer completes — runner-up probe | runner-up |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: Current synchronous design serializes on the request thread; both fetch and serialize contribute.

**Confidence**: Speculative

## Runner-up framing

| Field | Value |
|---|---|
| Frame | Network IO dominates — fetch + chunked write upstream |
| Falsifier | Profile shows CPU-bound serializer, not network |
| Confidence vs primary | lower |

## Hypothesis Enumeration

| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |
|---|---|---|
| Serial DB fetch is the bottleneck | Profile DB time vs total runtime | yes |
| Serializer hot loop dominates | Profile serializer vs fetch | yes |

## Recommended Verify Step

| Sub-field | Value |
|---|---|
| probe | Time fetch vs serialize on a 100K-row export |
| reproduction | Trigger export on 100K-row dataset |
| discriminator | if fetch > 80% then DB; if serialize > 80% then serializer; otherwise mixed |

## Approaches (HOW to change)

### Option A: Async via JobsQueue
- **Description**: Move export to background job; user polls progress
- **Addresses hypothesis**: Serial DB fetch is the bottleneck, Serializer hot loop dominates
- **Does NOT cover**: (none)
- **Pros**: unblocks UI; reuses JobsQueue
- **Cons**: progress UI required
- **Complexity**: Med

### Option B: Streaming response
- **Description**: Chunked streaming serializer
- **Addresses hypothesis**: Serializer hot loop dominates
- **Does NOT cover**: Serial DB fetch is the bottleneck
- **Pros**: no new infra
- **Cons**: request thread still busy
- **Complexity**: Low

**Recommended approach**: Option A: Async via JobsQueue — Closes both hypotheses; preserves small-dataset path

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| Rule 4.2 — long-running work must move off request thread | Pushes toward async |

## Complexity Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Codebase changes | Med | ExportService + UI + 1 new endpoint |
| Risk | Med | queue saturation if backlog |
| Verify cost | Med | load test on 100K-row dataset |

## Next step

Copy the block below into a new `/devforge:specify` session manually. No automation — user controls when (or if) `/devforge:specify` runs.

~~~
/devforge:specify "Export should be faster on large datasets — under 30 seconds OR async with progress"

Research reference: (path assigned when this research is saved to its feature directory)
Key facts:
- Mode: Enhancement
- Symptom: Export should be faster on large datasets
- Desired: under 30 seconds OR async with progress
- Recommended approach: Option A: Async via JobsQueue
- Hypothesis addressed: Serial DB fetch is the bottleneck, Serializer hot loop dominates
- Hypotheses NOT covered: (none)
- Open uncertainties: 0 (see research doc §Open Uncertainties)
~~~
