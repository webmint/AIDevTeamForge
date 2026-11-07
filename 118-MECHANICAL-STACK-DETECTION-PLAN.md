# 118 — Mechanical Stack Detection Plan

**Created**: 2026-09-25
**Status**: Stub — problem statement only. The plan body (findings, decisions, phases) is to be authored.

## Problem

`project-input.tech_stack_candidates` reported only `Language: TypeScript` for a mixed JavaScript/TypeScript Node monorepo (no JavaScript, runtime, test runner or build tool rows), and `read-manifests` returned `build_tool_hint: null` for packages whose manifests depend on `typescript` and build with `tsc`. Downstream Tech Stack, configure values and the constitution stack line start from this thin signal.

## Origin

Observed during a full setup-chain run (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) on a wrapper install over an npm-workspaces Node/TypeScript monorepo with Terraform-only packages.
