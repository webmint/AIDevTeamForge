# 121 — Helper Syntax Warnings Plan

**Created**: 2026-09-25
**Status**: Stub — problem statement only. The plan body (findings, decisions, phases) is to be authored.

## Problem

Helpers print `SyntaxWarning: invalid escape sequence` on every invocation under Python 3.12+ (seen in `_generate_docs/_md_frontmatter.py` and `_configure/_lint_ignore.py` docstrings), polluting stderr that commands are told to surface verbatim.

## Origin

Observed during a full setup-chain run (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) on a wrapper install over an npm-workspaces Node/TypeScript monorepo with Terraform-only packages.
