# 38 — Breakdown Agent-Roster Validation Plan

**Status:** **Phases 1–5 SHIPPED 2026-06-24** (working tree) on `develop-2.0-init`; only **Phase 6 (testForge20 / consumer e2e) remains, user-driven.** Built behind python-engineer→python-reviewer (helper) + instruction-author→instruction-reviewer + claude-code-guide (main.md) loops; 974 breakdown/implement tests pass.

**Shipped scope (A+B, user-chosen):**
- **A:** `breakdown_helper verify-agent-roster <tasks-dir>` (shared `_validate_agent_roster`) — globs `.claude/agents/*.md`, HARD-halts at `/breakdown` Phase 3.5 on any uninstalled assigned agent; folded into `finalize-handoff` as a chokepoint. Fail-closed on absent/empty roster (`is_file()` excludes `.md`-named dirs). Default `--agents-dir .claude/agents` correct in standalone + wrapper (roster lives in install root, not Source Root — spec passes no `--agents-dir`). Phase 5 best-effort clause split by channel (offenders→stdout, no-roster→stderr) so a roster violation hard-halts; Phase 3.5 preamble's Risk-Assessment bypass carved out (roster gate = no bypass).
- **B:** Agent Assignment table row for host/runtime-entrypoint code (Electron main, desktop `main`, CLI entry, Tauri core) → owning package's stack implementer per `PACKAGE_STACKS`, not `backend-engineer` by default.
- Docs reconciled: `handoff_schema.py` `TaskRow` docstring (points at helper-layer check), CHANGELOG, repo-root CLAUDE.md plan list + plan-14 cross-ref, `src/CLAUDE.md` `/breakdown` entry.

## Why this plan exists

A consumer install (mintEnvoy, a desktop Electron app with no backend stack) ran `/implement` on task 010 and halted:

```
Error: Agent type 'backend-engineer' not found. Available agents: ac-verifier,
api-designer, architect, ..., frontend-engineer, ..., qa-engineer, ...
```

`/breakdown` had assigned `backend-engineer` to `src/main/index.ts` (an Electron **main-process** one-liner: `minWidth: 720`). That agent was never generated for the project. The `/implement` missing-agent guard fired correctly and halted — but **far too late**: the poisoned assignment was already written into the task file + `breakdown-handoff.json`, and the human had moved on from decomposition.

**Two distinct defects, confirmed in code:**

- **A — Absent agent silently scheduled.** `/breakdown` assigns agents from a static table (`src/commands/breakdown/main.md:234` "Agent Assignment table") and the split-or-escalate rule (`main.md:255`) is **prose only**. `breakdown_helper finalize-handoff` validates the `**Agent**:` line is present + non-placeholder + non-empty (`src/devforge/lib/breakdown_helper.py:1722-1728`) but **never checks the agent exists in the installed roster**. `src/devforge/lib/_breakdown/handoff_schema.py:98` documents the gap verbatim: *"the roster is NOT validated here — only [non-empty]"*. A prose rule failed exactly as the framework's own forcing-function philosophy predicts (`feedback_helper_owns_contract_filesystem_forcing`: *spec prose can't enforce a check; only a mandatory gate that walks the filesystem is a reliable forcing function*).

- **B — Electron-main → `backend-engineer` mis-map.** The Agent Assignment table has **no row** for non-server host/runtime-entrypoint code (Electron main, CLI `main`, Tauri core). The "Unclear or mixed → split/escalate" row should have caught it, but the LLM force-fit Electron-main to the closest row ("server-side logic → backend-engineer") because main-process ≈ "not UI ≈ server-ish". Verified: `grep -i "electron|tauri|host process|entrypoint|main process" src/commands/breakdown/main.md` → **0 hits**.

## What the fix is NOT

- NOT a change to the `/implement` missing-agent guard — it worked. This plan moves the failure **left** (catch at `/breakdown`, where the orchestrator + architect are already engaged in routing) so a poisoned agent never reaches a written handoff.
- NOT an agent-name enum in `handoff_schema.py`. Per plan 14 (line 101/180), `TaskRow.agent` is validated non-empty only and intentionally carries no enum — the roster is **runtime, per-project** (`.claude/agents/*.md`), not a fixed list, so the check must glob the live install, not match a hardcoded set.

## Decisions

- **D1 — Mechanical gate, not more prose.** The prose rule already failed in production (mintEnvoy). The fix is a forcing function that walks `.claude/agents/`. Mirrors the existing `verify-contract-chain` / `verify-ac-coverage` breakdown forcing-functions.
- **D2 — Both a standalone verb AND a finalize chokepoint.** A standalone `verify-agent-roster` verb (callable as an explicit `/breakdown` phase gate, consistent with the other `verify-*` verbs) **and** the same validation folded into `finalize-handoff` (defense-in-depth — `breakdown-handoff.json` physically cannot be written with an absent agent). Single shared validation function, two call sites.
- **D3 — Roster path passed explicitly (`--agents-dir`), default `.claude/agents`.** Keeps the helper pure of workspace coupling, consistent with `finalize-handoff` taking explicit paths. In **wrapper mode** `.claude/agents/` lives in the install root; `/breakdown` main.md passes the resolved path. Default `.claude/agents` (relative to cwd) covers standalone.
- **D4 — Scope = A + B (gate + table row).** User directive 2026-06-23. Add a host/runtime-entrypoint table row alongside the mechanical gate. The gate is the robust safety net (catches any absent-agent assignment regardless of cause); the table row fixes the specific mis-map at its source.
- **D5 — Halt message mirrors `/implement`.** On failure the verb lists each offending `task → assigned-agent` plus the available roster (the same shape `/implement` prints), so the orchestrator can re-route in place.
- **D6 — Table source is single-site.** `src/_pending/commands/_agent-assignment.md` (the plan-14 inline source) is **GONE** — verified. The table lives only in `src/commands/breakdown/main.md:234`. Half B edits one file, not two.

## Open questions

- **OQ-1 — Primary-stack resolution for the host-entrypoint row.** "Routes to the app's primary stack implementer" — how does the orchestrator know the primary stack? Candidate: `## Packages` / `PACKAGE_STACKS` in the consumer `CLAUDE.md` (the table already cites it). The row should point there, not hardcode `frontend-engineer`. Resolve during Phase 4 authoring.
- **OQ-2 — Should the gate also run at `verify`-chain time?** The standalone verb could additionally be a `/verify` or `/implement` PHASE-1 sanity check. Deferred — the breakdown chokepoint + `/implement`'s existing guard already double-cover; YAGNI until evidence.
- **OQ-3 — Empty `.claude/agents/` dir.** If `--agents-dir` is absent/empty (mis-install), should the verb fail-closed (halt, "no roster found") or fail-soft (warn, pass)? Recommend **fail-closed** — an empty roster means every assignment is unsatisfiable; better to halt loudly. Confirm in Phase 1.

## Phases

### Phase 0 — Ratify (user sign-off gate)
No code. This plan reviewed + approved. Scope confirmed A + B (done — D4).

### Phase 1 — `verify-agent-roster` helper verb
Built via **python-engineer → python-reviewer** (test-first; real `.claude/agents/*.md` fixture dir, not hand-authored strings).

- Add `verify-agent-roster <tasks-dir> [--agents-dir <path>]` to `src/devforge/lib/breakdown_helper.py`.
- Reuse the existing task-file `**Agent**:` parser (the helpers at `breakdown_helper.py:1052+` shared by `verify-contract-chain` / `finalize-handoff`).
- Build the installed set from `glob(<agents-dir>/*.md)` stems.
- For each task: if its agent ∉ installed set → collect `(task-file, agent)`.
- Exit 0 + `{"ok": true}` if all satisfied; exit non-zero + a deterministic block listing each offending `task → agent` and the sorted available roster (D5) if any missing.
- Resolve OQ-3 (empty/absent `--agents-dir` → fail-closed).

**Verify:** unit tests — all-installed → exit 0; one absent agent → exit non-zero, offender + roster in output; empty agents-dir → fail-closed; wrapper path passed via `--agents-dir` resolves. Round-trip the task files via `render-task-file` (real producer), not hand-built fixtures.

### Phase 2 — Fold roster check into `finalize-handoff`
Built via **python-engineer → python-reviewer**.

- Extract Phase-1's validation into a shared function; call it from `finalize-handoff` after the existing non-empty/non-placeholder agent checks (`breakdown_helper.py:~1722`).
- `finalize-handoff` must take/resolve the agents-dir (new optional `--agents-dir`, same default).
- Absent agent → `finalize-handoff` dies with the same offender+roster block; `breakdown-handoff.json` is NOT written.

**Verify:** test — `finalize-handoff` on a tasks dir with one absent agent exits non-zero and writes no handoff; with all-installed, byte-identical to today's output (regression net = existing finalize tests).

### Phase 3 — Wire the gate into `/breakdown` main.md
Built via **instruction-author → instruction-reviewer + claude-code-guide** (ships into `.claude/`).

- Add a gate step in Phase 3 (after task files are written with their `**Agent**:` fields, before `finalize-handoff`): run `verify-agent-roster`, copy its block VERBATIM on failure, halt + re-route before finalize.
- Wire `--agents-dir` resolution for wrapper mode (use the install-root path the command already resolves elsewhere).

**Verify:** `instruction-reviewer` clean; `claude-code-guide` confirms the gate wording + halt semantics match Claude Code command conventions; cross-ref sweep (the new verb name appears in main.md's helper-call list + nowhere stale).

### Phase 4 — Table row for host/runtime-entrypoint code (Half B)
Built via **instruction-author → instruction-reviewer + claude-code-guide**.

- Add a row to the Agent Assignment table (`src/commands/breakdown/main.md:234`): non-server host/runtime-entrypoint code (Electron main, CLI `main`, Tauri core, desktop-app main process) → **the app's primary stack implementer per `## Packages` / `PACKAGE_STACKS`** (resolve OQ-1), explicitly NOT `backend-engineer` by default.
- Sharpen the prose so "non-renderer but not a server" no longer force-maps to backend.
- Single site (D6 — inline source gone).

**Verify:** `instruction-reviewer` clean; the row resolves the mintEnvoy case (Electron-main → primary stack, not backend); no contradiction with the existing "unclear/mixed → split/escalate" row.

### Phase 5 — Docs reconcile
- Flip `src/devforge/lib/_breakdown/handoff_schema.py:98` comment ("roster is NOT validated here" → "roster validated by `verify-agent-roster` + `finalize-handoff`").
- Update CLAUDE.md breakdown-helper entry (verb list) + the "Where to find what" breakdown rows.
- `src/CLAUDE.md` `/breakdown` catalog entry if the gate changes user-facing behavior.
- CHANGELOG.md.
- Plan 14 cross-ref: add a pointer that roster-existence validation now exists as a gate (plan 14 noted "no enum"; this plan adds the runtime check it deferred).
- This plan list entry in repo-root `CLAUDE.md` (mark phases shipped).

**Verify:** `grep -rn "roster is NOT validated"` → 0 stale hits; `pre-empt-future-hallucination` pass.

### Phase 6 — testForge20 / consumer e2e (user-driven, HARD GATE)
- On a project missing an agent, run `/breakdown` with a task whose owning stack's implementer isn't installed → confirm the gate halts at `/breakdown` (not deferred to `/implement`), printing offender + roster.
- Confirm the new table row routes a host-entrypoint task to the primary stack implementer.

## Context for next session

- The bug surfaced 2026-06-23 in mintEnvoy (consumer install), not in this repo. mintEnvoy's immediate task-010 unblock was handled by the user directly; this plan is the **forge root-cause** fix only.
- The `/implement` guard (`src/commands/implement/main.md:134` + `references/agent-brief.md:23`) is the existing late catch — do NOT remove it; this plan adds an earlier catch, not a replacement.
- Single-file helper: `breakdown_helper.py` is a flat ~1750-line launcher with subcommands (not a `_cli.py` package). The `verify-*` forcing-functions and `finalize-handoff` all live in it.
- Roster source of truth = `.claude/agents/*.md` (runtime, per-project). No enum anywhere — must glob the live install.

## When resuming work

Read this plan in full, then `src/commands/breakdown/main.md:200-260` (the assignment section + table) and `src/devforge/lib/breakdown_helper.py:1617-1760` (finalize-handoff validation) before touching code. Start at the lowest un-shipped phase.
