# 113 — Index Skip-List Drops Source Dirs Plan

**Created**: 2026-09-25
**Status**: Stub — problem statement only. The plan body (findings, decisions, phases) is to be authored.

## Problem

The dependency/build skip set (`"target"` in `index_helper.py`, `init_helper.py`, `detect_report.py`) matches a directory by bare name at any depth, so legitimate source directories such as `src/daos/target/` and `src/models/target/` are silently dropped from `.devforge/index.json` and therefore from the concern trees and docs. The CBM graph has the same blind spot (it also skips `target` directories), so graph queries miss these files too. CBM >= 0.11 can re-include such dirs via a `.cbmignore` negation (e.g. `!**/src/**/target/`); 0.6.x cannot.

## Origin

Observed during a full setup-chain run (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) on a wrapper install over an npm-workspaces Node/TypeScript monorepo with Terraform-only packages.
