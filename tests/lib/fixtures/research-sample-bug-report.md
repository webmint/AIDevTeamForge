# Research: items-not-sorted


**Date**: 2026-05-11
**Topic**: items-not-sorted
**Mode**: Bug
**Verdict**: Root cause hypothesis (needs repro)

## Summary

Inline sort in reactive body is unstable; recommended fix is a derived computed with stable comparator. Falsifier probe added for race hypothesis.

## Symptom

| Dimension | Value |
|---|---|
| Symptom | Items not sorted in admin products list (sort fails) |
| Affected area | Admin > Products > List |
| Repro / Current | Open list with 50+ items |
| Desired | alphabetical sort by name A->Z |
| Scope | One component |

## Codebase Findings (WHERE)

| Surface | File:line | Relevance | Framing |
|---|---|---|---|
| products list component | src/admin/Products.vue:201 | inline .sort() call inside watch body | primary |
| list helper | src/admin/helpers.ts:45 | shared comparator unused here | primary |
| shared sort helper | pkg-shared/sort.ts:10 | canonical comparator used by other packages — cross-layer fix candidate | primary |
| fetch / watch race window | src/admin/Products.vue:180 | fetch can complete while watch still iterating — runner-up probe | runner-up |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: Inline .sort() in watch body uses unstable comparator while fetch mutates source list.

**Confidence**: Hypothesis

### Structured root cause

| Field | Value |
|---|---|
| trigger | User scrolls past 50 items + new item created concurrently |
| root_cause | Inline sort in reactive body without stable comparator; no shared helper |
| contributing_factors | 1. No e2e covers paginate-while-mutating 2. Component uses inline .sort() vs shared helper |

## Runner-up framing

| Field | Value |
|---|---|
| Frame | Race between fetch and watch (not comparator) |
| Falsifier | Stabilizing comparator alone fixes order under repro |
| Confidence vs primary | lower |

## Hypothesis Enumeration

| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |
|---|---|---|
| unstable comparator in inline sort | swap comparator; verify order stable | no |
| race between fetch and watch | log fetch ids before sort | yes |

## Recommended Verify Step

| Sub-field | Value |
|---|---|
| probe | console.log sort-input + sort-output at Products.vue:201/204 |
| reproduction | Open Products; sort by name; create item in another tab; switch back |
| discriminator | if sort-input randomized then race; if input ordered + output not then comparator; both ordered then render |

## Approaches (HOW to change)

### Option A: Replace inline sort with shared comparator
- **Description**: Use existing helper
- **Addresses hypothesis**: unstable comparator in inline sort
- **Does NOT cover**: race between fetch and watch
- **Pros**: small diff; reuses helper
- **Cons**: does not address race
- **Complexity**: Low

### Option B: Move sort to derived computed + stabilize comparator
- **Description**: Reactive computed instead of watch body
- **Addresses hypothesis**: unstable comparator in inline sort, race between fetch and watch
- **Does NOT cover**: (none)
- **Pros**: covers both; reactive primitive
- **Cons**: bigger refactor
- **Complexity**: Med

**Recommended approach**: Option B: Move sort to derived computed + stabilize comparator — Closes both hypotheses; preserves pagination + filter behavior

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| Rule 2.1 — UI sort logic must be deterministic | Forces stable comparator |

## Complexity Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Codebase changes | Low | 1 component |
| Risk | Low | pagination preserved |
| Verify cost | Med | needs e2e for paginate-while-mutating |

## Next step

Copy the block below into a new `/specify` session manually. No automation — user controls when (or if) `/specify` runs.

~~~
/specify "Items not sorted in admin products list (sort fails) — alphabetical sort by name A->Z"

Research reference: (path assigned when this research is saved to its feature directory)
Key facts:
- Mode: Bug
- Symptom: Items not sorted in admin products list (sort fails)
- Desired: alphabetical sort by name A->Z
- Recommended approach: Option B: Move sort to derived computed + stabilize comparator
- Hypothesis addressed: unstable comparator in inline sort, race between fetch and watch
- Hypotheses NOT covered: (none)
- Open uncertainties: 0 (see research doc §Open Uncertainties)
~~~
