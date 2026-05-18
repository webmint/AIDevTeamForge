# Spec: scheduled-export-jobs

**Date**: 2026-05-15
**Status**: Draft
**Author**: Claude + User

## 1. Overview

Introduce scheduled export jobs for tenant data via the existing job runner.

## 2. Current State

Scaffolding for scheduled jobs lives under src/jobs/ per constitution Section 7; no export jobs exist yet.

## 3. Desired Behavior

Tenants can register a recurring export job and receive a result file via the existing storage hook.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| Jobs | src/jobs/exports.ts, src/jobs/registry.ts | add new job registration and runner glue |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [ ] **AC-1**: The repository shall contain a new exports job module under src/jobs/.
  > Verification: ls src/jobs/exports.ts returns the file

### 5.2 Behavior preservation

N/A — greenfield surface; nothing to preserve yet

### 5.3 Behavior change

- [ ] **AC-2**: WHEN a tenant registers an export schedule, the runner shall enqueue the job.

### 5.4 CI / pipeline

N/A — no pipeline change required

### 5.5 Hooks / gates

- [ ] **AC-3**: WHILE the export job is running, the storage hook shall hold the partial file.

### 5.6 Documentation

- [ ] **AC-4**: The exports README shall document the new registration flow.

### 5.7 Hygiene

- [ ] **AC-5**: The repository shall contain no stray TODO markers in the new job module.
  > Verification: grep -E 'TODO' src/jobs/exports.ts returns no matches

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Ad-hoc on-demand exports outside scheduling

## 7. Technical Constraints

- Must follow: Constitution Section 7 scaffolding rules
- Must follow: Existing job runner from src/jobs/registry.ts

## 8. Open Questions

- **DP-scope_boundaries-1** [default applied]: Export targets supported → default: csv and json
- **DP-tooling_configuration-1** [default applied]: Scheduler component to use → default: existing job runner
- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-data_flow_state-1** [no DP in category data_flow_state]: no relevant decision point for data_flow_state
- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-ui_ux_details-1** [no DP in category ui_ux_details]: no relevant decision point for ui_ux_details
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Storage hook contention under concurrent exports | Low | Med | Add per-tenant queue to serialize exports |
