# 115 — Wrapper Inner Repo CBM Visibility Plan

**Created**: 2026-09-25
**Status**: Stub — problem statement only. The plan body (findings, decisions, phases) is to be authored.

## Problem

In wrapper mode the install root is its own git repo, and the natural way to keep the inner source repo out of it is an install-root `.gitignore` entry. CBM honours `.gitignore`, so the index then contains only framework files and every CBM-backed step (generate-docs, glossary, research, implement) runs against an empty graph with no warning. Nothing in install / init-forge detects or guides this (`.git/info/exclude` works). CBM >= 0.11 also honours `.git/info/exclude` (and core.excludesFile), so that workaround blinds the index completely on 0.11; a repo-local `core.excludesFile` plus a `.cbmignore` `!<inner>/` negation keeps both git and CBM correct.

## Origin

Observed during a full setup-chain run (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) on a wrapper install over an npm-workspaces Node/TypeScript monorepo with Terraform-only packages.
