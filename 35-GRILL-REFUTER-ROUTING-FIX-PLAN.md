# 35 — GRILL REFUTER ROUTING FIX

**Status:** ✅ CLOSED 2026-06-24 — committed `06b78be` on `develop-2.0-init`. testForge20/mintEnvoy e2e DEFERRED by maintainer 2026-06-24 (not blocking — the fix is empirically validated, see below). Discovered during a mintEnvoy `/grill` run on feature `003-app-shell-layout`. Phase 1 (spec fix) shipped via instruction-author → instruction-reviewer (3 prose findings applied) → claude-code-guide (presence-check soundness → D3). Empirically validated against `_shared/_verify.py route_refutation`: old `--finders "devils-advocate"` self-refutes; new `--finders "devils-advocate,<present-refuters>"` routes to `code-reviewer`, degrades to `qa-reviewer` when code-reviewer absent. No helper changed.

## The bug

`/grill` PHASE 4.1 routes EVERY finding to the wrong refuter — the finding's own author (`devils-advocate`) self-refutes, violating the architect-excluded non-author cross-examination design (plan 23 D5). Observed in mintEnvoy: passing the spec's documented `--finders "devils-advocate"` routed all 6 findings back to `devils-advocate`. Manual workaround `--finders "devils-advocate,code-reviewer,qa-reviewer,security-reviewer"` routed correctly to `code-reviewer`.

## Root cause — SPEC bug, not helper

The helper is correct and internally consistent with the shared refutation engine:

- `src/devforge/lib/_grill/_cli.py:63` — `_GRILL_REFUTER_PRIORITY = ["code-reviewer", "qa-reviewer", "security-reviewer"]` (architect-excluded, hardcoded).
- `src/devforge/lib/_grill/_cli.py:447-448` — `route_refutation(findings, present_finders, priority=_GRILL_REFUTER_PRIORITY)`. `present_finders` is the `--finders` CLI value.
- `src/devforge/lib/_shared/_verify.py:320-321` — refuter selection: `for candidate in effective_priority: if candidate in present_set and candidate != author`. **The chosen refuter MUST be in `present_set` (= `--finders`).**

So a refuter is selectable ONLY if it is passed in `--finders`. The spec at `src/commands/grill/main.md:213` passes `--finders "devils-advocate"` only → no priority refuter is "present" → the selection loop finds nothing → falls through to the sole-finder self-refute branch (`_verify.py:325-337`) → `devils-advocate` refutes its own findings.

The spec's line 216 asserts a FALSEHOOD: *"every finding routes to the first PRESENT priority refuter"* — they were never passed as present. The author conflated `present_finders` (the eligibility gate) with the priority list (ranking among eligible). `/audit` + `/review` don't trip this because there the finders ARE the refuters, so `present_finders` already contains them. `/grill` is the only command where finder (`devils-advocate`) ≠ refuters, so it's the only one exposed.

Internal spec inconsistency confirms the gap: `main.md:299` (`render-report --finders-skipped`) expects the orchestrator to compute which refuters are ABSENT during PHASE 4 — but PHASE 4 never computes the present-refuter set nor feeds it to `route-refutation`.

## Decision

- **D1 — Fix spec-side, not helper-side.** `route_refutation` / `_shared/_verify.py` is shared by `/audit` + `/review` + `/grill`; its `present_set` gating gives correct graceful-degradation for absent agents in those commands. Do NOT touch the helper. `/grill`'s PHASE 4 must pass its present refuters in `--finders`.
- **D2 — Determine present refuters by `.claude/agents/` presence**, then pass `devils-advocate` + present-refuters CSV to `--finders`, and the absent ones to `render-report --finders-skipped`. This makes line 213 and line 299 consistent (the `--finders-skipped` machinery finally has a source). The three refuters are plan-15 core reviewers, normally all present, so the skipped list is normally empty — matching the existing line-299 framing.
- **D3 — `.claude/agents/<name>.md` file-existence is the right presence check FOR THE FORGE, despite being unsound for general Claude Code.** claude-code-guide flagged two general-case gaps: (a) a subagent's `name` lives in YAML frontmatter and need not match the filename; (b) a check limited to project `.claude/agents/` misses user-level `~/.claude/agents/`, plugins, and managed/CLI agents, so a dispatchable agent could be marked absent. Both are closed by construction in a forge install: the emitter writes each agent to project `.claude/agents/` with a canonical `<name>.md` filename, so filename==name and location==project hold. The check is also already the established convention — PHASE 2.1 uses the identical test for `devils-advocate`; diverging PHASE 4 to a frontmatter-parse would be inconsistent. claude-code-guide's "Path A: dispatch and catch the failure" was rejected because `route_refutation` must compute the present set BEFORE dispatch (it builds the routing map up front), and passing an uninstalled agent in `--finders` would make the engine select it and then fail at Task dispatch — so the presence check's conservative under-inclusion (skip an agent present only at user-level) is the safe failure mode, and does not occur in forge installs anyway.

## Phase 1 — Fix `src/commands/grill/main.md` PHASE 4

Edits (intra-file only; ships into `.claude/commands/grill/main.md` → routes through instruction-author → instruction-reviewer → claude-code-guide):

1. Add a present-refuter determination step before 4.1: for each of `[code-reviewer, qa-reviewer, security-reviewer]`, test `.claude/agents/<name>.md`; build `<present-refuters>` (CSV) + `<skipped-refuters>` (CSV).
2. Line 213 — `--finders "devils-advocate,<present-refuters>"`.
3. Line 216 — rewrite the false prose: refuters are selectable only when passed in `--finders` (the shared engine gates refuter eligibility on the present-finders list); `devils-advocate` is included as the author and correctly excluded as its own refuter via `candidate != author`; the architect is omitted entirely.
4. Line ~290/299 — `render-report --finders-skipped "<skipped-refuters>"` sourced from the step-1 check.

## Verify

- Re-read PHASE 4: `--finders` carries the present refuters; line 216 prose is true against `_shared/_verify.py` selection logic; `--finders-skipped` has a defined source.
- Cross-ref sweep: no other `grill/main.md` line claims `--finders "devils-advocate"`-only routing; no `references/*.md` repeats the false claim.
- testForge20 / mintEnvoy e2e (user-driven, HARD GATE): run `/grill` on a real `plan.md`, confirm `refutation-routes.json` routes to `code-reviewer` (not `devils-advocate`), and `grill.md` shows non-author refutation.

## When resuming work

Helper is correct — do NOT change `_shared/_verify.py` or `_grill/_cli.py`. The entire fix is in `src/commands/grill/main.md` PHASE 4. Re-read the Root cause section before editing — the present_set gating is the load-bearing fact.
