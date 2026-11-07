# 114 — Glossary CBM Project Argument Plan

**Created**: 2026-09-25
**Status**: Stub — problem statement only. The plan body (findings, decisions, phases) is to be authored.

## Problem

`build-glossary-bundles` (`_generate_docs/_glossary.py`) calls `codebase-memory-mcp cli query_graph` / `search_graph` without a `project` field. The current CBM CLI rejects that with "project not found or not indexed", so every term classifies as prose-only and the glossary gets zero code anchors. With `project` supplied, `labels(n)` still comes back empty, so the label check would also fail. CBM 0.11 also deprecates the raw-JSON positional argument of `cli <tool>` and prints query tools in a compact non-JSON format by default, so every `codebase-memory-mcp cli` caller in the helpers needs checking.

## Origin

Observed during a full setup-chain run (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) on a wrapper install over an npm-workspaces Node/TypeScript monorepo with Terraform-only packages.
