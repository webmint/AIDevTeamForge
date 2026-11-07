# 117 — Configure Empty-Value Setters Plan

**Created**: 2026-09-25
**Status**: Stub — problem statement only. The plan body (findings, decisions, phases) is to be authored.

## Problem

`/devforge:configure` Phase 2 says `AC_RUNTIME_URL`, `AC_RUNTIME_API_BASE`, `AC_RUNTIME_CLI_COMMAND` and `E2E_COMMAND` are the empty string when nothing is detected and are applied via their setters, but each setter exits 2 with "value cannot be empty". Spec and helper disagree on how an undetected value is recorded.

## Origin

Observed during a full setup-chain run (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) on a wrapper install over an npm-workspaces Node/TypeScript monorepo with Terraform-only packages.
