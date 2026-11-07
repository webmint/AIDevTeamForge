# 116 — Configure Workspace Commands Plan

**Created**: 2026-09-25
**Status**: Stub — problem statement only. The plan body (findings, decisions, phases) is to be authored.

## Problem

`/devforge:configure` Phase 2 composes per-package commands from each package's own `scripts` (verbatim) or an ecosystem default (`npm run build` even when no build script exists), while `implement_helper verify-touched` runs every command with cwd = source root. In an npm-workspaces monorepo the composed commands are either not runnable from the source root or fail on a missing script.

## Origin

Observed during a full setup-chain run (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) on a wrapper install over an npm-workspaces Node/TypeScript monorepo with Terraform-only packages.
