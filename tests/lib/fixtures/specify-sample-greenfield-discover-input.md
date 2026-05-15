# Discover: scheduled-export-jobs

**Date**: 2026-05-14
**Topic**: scheduled-export-jobs
**Verdict**: Proceed — extend existing job runner

## Summary

Tenants need recurring data exports. The workspace already runs a generic job runner under `src/jobs/`; the recommendation is to extend it with an exports module rather than introducing a new scheduler service.

## Rubric

| Dimension | Notes |
|---|---|
| functional_scope | Recurring export of tenant data to a result file |
| users | Tenants with admin role |
| inputs_outputs | Inputs: export schedule + format; Outputs: result file via storage hook |
| integration_points | Existing job runner + storage hook |
| constraints | Constitution Section 7 scaffolding rules; auth middleware required |
| non_goals | Ad-hoc on-demand exports; UI redesign of the admin panel |
| success_criteria | A tenant can register a schedule and receive the file at the cadence |
| edge_cases | Concurrent exports per tenant; partial-failure resumption |

## Prior Art

| Source | Path | Notes |
|---|---|---|
| internal | src/jobs/registry.ts | existing job-runner registry that accepts new modules |
| internal | src/jobs/sample.ts | shape of a runner module |
| internal | docs/architecture.md | jobs layer described under "Background runners" |

## Integration Surface

- Job runner registry — module registration entrypoint
- Storage hook — already exposes signed-URL writeback for runner results
- Auth middleware — enforces tenant scope on registration endpoint

## Fit Assessment

| Axis | Rating |
|---|---|
| Feature fit | Strong |
| Effort | Small |
| Risk | Low |

## Design Options

### Option A: Extend existing job runner with an exports module
- **Description**: Drop a new module under `src/jobs/exports.ts` that the registry picks up automatically.
- **Pros**: reuses runner; no new scheduler service; matches constitution Section 7 scaffolding
- **Cons**: ties exports lifecycle to job-runner upgrade cadence
- **Complexity**: Low

### Option B: Introduce a separate cron scheduler service
- **Description**: New process / container dedicated to cron with its own queue
- **Pros**: isolated; clearer scaling story
- **Cons**: new infra surface; duplicates job-runner functionality; conflicts with constitution Section 7
- **Complexity**: Med

**Recommended option**: Option A: Extend existing job runner with an exports module — uses existing surfaces from src/jobs/registry.ts and src/jobs/sample.ts; satisfies constitution Section 7 scaffolding rules.

## Build vs Buy

Build. No off-the-shelf solution covers tenant-scoped recurring exports against the workspace's storage hook.

## Derisk Plan

- Stand up the new module behind a feature flag for one tenant first.
- Add an e2e covering schedule → enqueue → result-file write.
- Watch for storage-hook contention under concurrent exports.

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| Section 7 — Scaffolding Guide | Forces module placement under `src/jobs/` |
| Auth middleware rule | Forces tenant-scope enforcement on registration endpoint |

## Next step

Copy the block below into a new `/specify` session manually. No automation — user controls when (or if) `/specify` runs.

~~~
/specify "Scheduled export jobs for tenant data — register a recurring export and receive the result file via the existing storage hook"

Discover reference: discover/2026-05-14-scheduled-export-jobs.md
Key facts:
- Recommended option: Option A: Extend existing job runner with an exports module
- Internal prior art: src/jobs/registry.ts, src/jobs/sample.ts
- Build vs buy: Build (no off-the-shelf fit)
- Constitution constraints: Section 7 scaffolding, auth middleware
- Open uncertainties: 0 (see discover doc §Open Uncertainties)
~~~
