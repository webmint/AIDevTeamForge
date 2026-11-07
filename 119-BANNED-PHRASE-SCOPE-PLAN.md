# 119 — Banned-Phrase Scope Plan

**Created**: 2026-09-25
**Status**: Stub — problem statement only. The plan body (findings, decisions, phases) is to be authored.

## Problem

`validate-doc` applies `_BANNED_PHRASES_RE` (`some`, `other`, `many`, …) to the whole document body, including verbatim fenced code snippets in Patterns / Cross-Cuts and verbatim mechanical inputs (project tree, key commands, test paths). A real code snippet or path containing one of those words fails validation although it must stay verbatim.

## Origin

Observed during a full setup-chain run (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) on a wrapper install over an npm-workspaces Node/TypeScript monorepo with Terraform-only packages.
