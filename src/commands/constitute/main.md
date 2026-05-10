---
name: constitute
description: Synthesize constitution.md from /configure + /generate-docs outputs (schema-anchored)
disable-model-invocation: true
---

# /constitute — Synthesize constitution.md

**Status**: Step 0 stub. Spec authoring scheduled for CONSTITUTE-PLAN.md Step 5.

`/constitute` is the fourth and last command in the 4-command sequence (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). It consumes `.devforge/init.yaml` + `.devforge/configure.yaml` + `docs/{overview,architecture,glossary}.md` and renders `constitution.md` at the install root with 7 schema-anchored sections.

This stub is in place so `scripts/emitters/claude.py` ships the file into target projects during the helper buildout (Steps 1-4). The full Phase 0-6 contract lands in Step 5.

The legacy pre-pivot spec is preserved at `main.md.legacy` and `test-scenarios.md.legacy` for cross-reference; both will be deleted at Step 8 once the new spec ships.

See `CONSTITUTE-PLAN.md` (repo root) for the full implementation plan.
