# 47 — `/breakdown` Architect Implementability Sub-Question Plan

**Status:** ✅ Steps 0–3 DONE 2026-06-30 on `develop-2.0-init` (Step 0 signed off; edit authored + reviewed clean). Only **Step 4 (testForge20 e2e) remains, user-driven (HARD GATE).** Four sites in `breakdown/main.md` carry the 4th sub-question; instruction-reviewer (2 findings applied: line-186 escalation-output clause + determinism-not-brevity carve-out) + claude-code-guide (pure body-prose, convention-clean) both green; grep confirms no stale 3-item enumeration. Pure prose to the already-emitted command — no helper/test/emitter change.
**Owner file:** `src/commands/breakdown/main.md` (LLM instruction file — ships into `.claude/`, so all edits route through instruction-author → instruction-reviewer + claude-code-guide).

## Problem

`/breakdown`'s Phase-2 mandatory architect consult validates task **structure** but not task-prose **implementability**. Its three always-asked sub-questions (`breakdown/main.md:204-206`) are:

1. Task atomicity boundaries / bundling
2. Dependency ordering & direction
3. Contract-chain integrity (semantic identifiers)

None asks whether the assigned engineer can actually execute a task from what's written without guessing a decision the plan never made. The framework verifies each task's **outcome** (the `one clear done condition` clause in sub-q 1 + semantic `Expects`/`Produces` + the `verify-contract-chain` forcing-function) — which is mechanically checkable — but an *underspecified intent* (a missing input the steps assume, an unstated choice between valid implementations, a done-condition more than one diff could satisfy) is caught only downstream at the per-task review panel or `/verify`, after code is written, or by the human at the breakdown approval gate.

This closes that gap at the cheapest correct point: one added sub-question on the consult that already runs every breakdown, by the right specialist (the architect), before any task file is written.

## Why this and not the alternatives (settled before drafting)

- **NOT a separate prose-reviewer agent / pass.** Prose clarity is subjective — "is this clear enough?" is exactly the judgment-call slip-path the zero-escape-hatch meta-rule warns against, and a dedicated per-task pass is heavyweight for a problem the downstream panel + `/verify` already backstop. (This is the `instruction-reviewer`-for-consumer-artifacts idea, already declined: that agent is scoped to *framework* instruction files + Claude Code conventions, not consumer work artifacts.)
- **NOT a mechanical forcing-function.** Intent-completeness is not a regex/graph property; it is a judgment call. It stays a judgment check by the architect, by design — consistent with how the framework verifies outcome mechanically but leaves design judgment to the architect.
- **YES a 4th sub-question.** It rides the existing mandatory hook (no new dispatch, no new agent, no new provenance schema — the per-specialist verdict enum `accepted`/`modified`/`rejected`/`no-response` is unchanged), and the architect's `think`-tier reasoning is the right altitude for "is this task fully determined."

## Decisions

- **D1 — 4th always-asked sub-question** appended to `breakdown/main.md:204-206`. Not a separate reviewer, not a forcing-function (see above).
- **D2 — scope = intent-completeness / implementability, explicit NON-GOAL = prose style / grammar / verbosity.** A terse task that is fully determined by its contracts + the spec/plan/constitution/docs context the implementer also reads is NOT a finding. The sub-question must say so, so the architect does not manufacture findings on terse-but-determined tasks (respects `feedback_basic_path_plus_user_fallback`).
- **D3 — findings ride the existing Phase-2 revise-before-write return path** (`breakdown/main.md:186` — the architect already returns "revisions" the orchestrator applies before writing task files). An implementability finding is a 4th revision type folded into that same loop: the orchestrator either tightens the draft task, or — if the missing piece is a decision `/plan` should have made (a plan-level gap, not a wording gap) — escalates to the human, consistent with the existing escalate patterns. No new plumbing.
- **D4 — no `src/agents/architect.md` edit.** Verified (2026-06-29): the three sub-questions are enumerated ONLY in `breakdown/main.md`; `architect.md` references consultation requests generically and reads the decomposition sub-questions from the runtime brief. The architect's charter ("never write code") is unaffected — an implementability check is validation, not authoring.
- **D5 — zero-escape-hatch wording.** The sub-question names a single mandatory action ("Flag any task whose intent is underspecified") with a bounded definition + an explicit not-a-finding clause — no "use judgment" / "if reasonable" carve-out.

## The change

### Primary edit — add sub-question 4 (`breakdown/main.md:206`, after the contract-chain item)

Draft wording (final wording is instruction-author's to set; this is the intent contract):

> 4. **Implementability (intent completeness)**: can the assigned engineer execute each task from its done-condition + `Expects`/`Produces` without guessing a decision the plan did not already make? Flag any task whose intent is underspecified — a missing input the steps assume, an unstated choice between two valid implementations, or a done-condition more than one diff could satisfy. This is an intent-completeness check, NOT a prose-style, grammar, or verbosity judgment: a terse task that is fully determined by its contracts plus the spec / plan / constitution / docs context the implementer also reads is NOT a finding. Route a flag the same way as an atomicity/ordering/contract revision (revise the draft task before writing it); if the missing piece is a decision `/plan` should have made rather than a wording gap, escalate to the human.

### Mandatory in-file cross-ref updates (the 3→4 enumerations; grep-verified 2026-06-29)

- **`breakdown/main.md:10`** (Overview) — "validate task atomicity, dependency ordering, and contract-chain integrity" → append the implementability item.
- **`breakdown/main.md:182`** — "the specialization point for task-boundary, dependency-direction, and contract-chain-integrity calls" → append implementability.
- **`breakdown/main.md:186`** — "with your draft task set and the **three** fixed sub-questions below … revisions to atomicity / ordering / contracts" → "**four**" + add implementability to the revisions list.

No other file enumerates the sub-questions (grep over `src/` returned only `breakdown/main.md`).

## Steps

### Step 0 — maintainer sign-off (gate)

Confirm: (a) 4th sub-question over separate reviewer/forcing-function (D1), (b) the intent-completeness scope + explicit not-a-finding clause (D2), (c) the draft wording's altitude. No authoring before this.

### Step 1 — author the edit (`instruction-author`)

Add sub-question 4 + apply the three cross-ref updates (lines 10, 182, 186). Brief the author with: the exact intent-contract wording above, the four edit sites, D2's non-goal + not-a-finding clause as load-bearing, D5's no-escape-hatch constraint, and that the per-specialist verdict enum / provenance table is unchanged (do not touch Phase 3's Specialist Consultation block).

**Verify:** the four sites updated; no new placeholder/section introduced; the sub-question reads as a single mandatory check with the not-a-finding carve-out intact.

### Step 2 — review (`instruction-reviewer` + `claude-code-guide`)

`instruction-reviewer`: logical flow, the 3→4 cross-refs are internally consistent, no sentence became false, no escape hatch. `claude-code-guide`: confirm nothing about the edit violates Claude Code command-authoring conventions (it ships into `.claude/commands/breakdown/`). Apply findings, loop until clean.

**Verify:** instruction-reviewer returns no High/Medium; claude-code-guide confirms convention-clean.

### Step 3 — cross-check + emitter/install sanity

Grep `src/` again for any 3-item enumeration of the sub-questions left un-updated. Confirm `/breakdown` still emits cleanly (no new helper, no `_PROMOTED` change — pure prose edit to an existing emitted command). No test suite touches this prose.

**Verify:** grep shows all enumerations carry the 4th item; `breakdown/main.md` has no dangling "three sub-questions" / 3-item list.

### Step 4 — testForge20 e2e (user-driven, HARD GATE)

Run `/breakdown` on a feature whose plan deliberately leaves one task underspecified (an unstated choice between two valid implementations); confirm the architect flags it as an implementability finding and the orchestrator revises-or-escalates before writing task files. Confirm a terse-but-fully-determined task is NOT flagged (no false positive).

## When resuming work

Read this plan + `breakdown/main.md:176-264` (Phase 2). If Step 0 is signed off but Steps 1-2 are not done, dispatch instruction-author with the Step-1 brief. The edit is pure prose to one emitted command file — no helper, no test, no emitter change. The only correctness risk is a stale 3→4 enumeration left behind (Step 3 catches it) or escape-hatch wording creeping into the sub-question (Step 2 catches it).

## Context for next session

This extends the framework's "verify by the right specialist at the cheapest correct point" pattern (same shape as the mandatory architect consult itself). It deliberately does NOT mechanize — intent-completeness is a judgment call, so it stays a judgment check; do not let a future session "harden" it into a forcing-function (it would become a false-positive engine on terse-but-determined tasks). Originated from a 2026-06-29 design question: should generated consumer task prose be instruction-reviewed? Answer: no (wrong layer/agent) — strengthen the architect consult instead, which is this plan.
