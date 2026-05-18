# Spec: monorepo-pnpm-migration

**Date**: 2026-05-15
**Status**: Draft
**Author**: Claude + User

## 1. Overview

Migrate the monorepo from lerna with yarn to pnpm workspaces using corepack.

## 2. Current State

Workspace uses lerna for orchestration and yarn for package install. Lockfiles are yarn.lock files.

## 3. Desired Behavior

Workspace uses pnpm workspaces for orchestration. Lockfile is pnpm-lock.yaml. Corepack pins pnpm version.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| Root tooling | package.json, pnpm-workspace.yaml | switch package manager and workspace layout |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [ ] **AC-1**: The repository shall contain no occurrences of `lerna`.
  > Verification: grep -rE 'lerna' . returns no matches

### 5.2 Behavior preservation

- [ ] **AC-2**: The build system shall produce the same dist artifacts as before.

### 5.3 Behavior change

- [ ] **AC-3**: WHEN the developer runs install, the workspace shall use the pnpm lockfile.

### 5.4 CI / pipeline

- [ ] **AC-4**: The CI pipeline shall install dependencies via pnpm.

### 5.5 Hooks / gates

- [ ] **AC-5**: IF a yarn lockfile is committed, THEN the pre-commit hook shall reject the commit.

### 5.6 Documentation

- [ ] **AC-6**: The README shall describe pnpm install steps.

### 5.7 Hygiene

- [ ] **AC-7**: The repository shall contain no leftover yarn lockfiles.
  > Verification: find . -name 'yarn-lock' returns no matches

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Migrating CI runner base image
- NOT included: Migrating off TypeScript

## 7. Technical Constraints

- Must follow: Use pnpm workspace-protocol for intra-repo dependencies
- Must not break: Existing dist output paths
- Must integrate with external system (corepack): Corepack to pin pnpm version

## 8. Open Questions

- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-data_flow_state-1** [no DP in category data_flow_state]: no relevant decision point for data_flow_state
- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-ui_ux_details-1** [no DP in category ui_ux_details]: no relevant decision point for ui_ux_details

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Phantom dependency surfacing after install switch | Med | Med | Run typecheck and tests on each package before merge |
