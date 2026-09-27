# 122 — Configure Agent List Prune Order Plan

**Created**: 2026-09-25
**Status**: Stub — problem statement only. The plan body (findings, decisions, phases) is to be authored.

## Problem

`/devforge:configure` Phase 5 runs `render-config` before `prune-agents`, so the `AGENT_LIST` it writes to `.devforge/project-config.json` — which `substitute-templates` then writes under `## Available Agents` in the installed `CLAUDE.md` — still names every agent Phase 5.2 deletes. A later `render-config` refreshes only `project-config.json`: the installed `CLAUDE.md` no longer carries the `{{AGENT_LIST}}` placeholder, so re-running `substitute-templates` leaves the stale list in place. The Phase 5 intro justifies this order as the one that prevents a stale list.

## Origin

Observed 2026-09-25 on a consumer install after `/devforge:configure`: `## Available Agents` listed all 20 agents, 7 of which Phase 5.2 had deleted (among them `frontend-engineer` and `backend-engineer`). Recorded earlier, from a planted scratch run rather than a consumer observation, as `FINDINGS.md` entry 7 (2026-09-23), which holds the verified mechanism and two candidate fix shapes.
