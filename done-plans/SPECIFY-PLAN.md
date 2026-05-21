# /specify revisit plan

Status: **PROMOTED 2026-05-11 → [SPECIFY-REDESIGN-PLAN.md](./SPECIFY-REDESIGN-PLAN.md)** (was WATCHLIST). Historical record of trigger rationale; active execution lives in the redesign plan.
Active branch: `develop-2.0-init` (or successor — confirm at session start).

## Promotion summary (2026-05-11)

User signal combined two converging pressures:

1. **SDD-drift concern** — user heard SDD is broken / drifted. Investigation confirmed: prose-only enforcement of contract layer = ceremony / verify-fiction / closed-LLM-loop. /specify needed external anchor (helper-owns-shape + executable AC constraints).
2. **Framework parity push** — /init-forge, /generate-docs, /configure, /constitute all shipped with helper-owns-shape. /specify was the odd one out.

Triggers fired at promotion:

- **Trigger 3** (Format drift / helper-owns-shape) — fired. v1 parity test 2026-04-29 documented mean composite deviation ~15% (Obsidian `parityTest/4-way comparison results - spec 007.md`); v1→v2→v3 evolution implemented prose mitigations in cse-strata-ws-forge baseline. Promotion converts prose discipline to helper-enforced code discipline.
- **Trigger 4** (/discover integration) — scheduled fire on DISCOVER-PLAN ship; bundled into promotion.
- **Trigger 5** (/research-refactor integration) — scheduled fire on REDESIGN-RESEARCH-PLAN ship; bundled into promotion.

Triggers 1 + 2 NOT fired empirically — addressed preventively via Phase 1.5 findings enumeration (Trigger 1 surface) + Phase 2 bounded-turn rubric with 7 categories (Trigger 2 surface).

## Decision: PROMOTED (was "no change yet")

`/specify` redesigned in SPECIFY-REDESIGN-PLAN.md:

- Baseline = v3 spec at `cse-strata-ws-forge/.claude/commands/specify.md` (NOT devforge `_pending` — devforge `_pending` was wrongly used in plan rev 1 and discarded).
- Conversion = helper-owns-shape via `specify_helper.py` + SpecDoc / Finding / DecisionPoint / SpecTypeClassification schemas + per-setter persistence.
- 7-phase pipeline (Phase 0 / 1 / 1.5 / 2 / 3 / 4 / 5) mirroring v3 structure.
- 4 SDD-framework adoptions: EARS notation for AC statements (Kiro), constitution-recheck at Phase 4+5 (Spec Kit), optional `test_anchor` field (Tessl-lite), `resolve-open-question` audit subcommand (Spec Kit checklist parity).
- Variance preservation: 10 hard rules pinned. Empirical gate = re-run 4-instance × 8-run protocol on canonical input; merge only if ≤5% on 4 axes (structural / AC count / output length / decision-drift).
- Orchestrator-direct (no new subagent). Variance + 3-benefit test rationale carried forward unchanged from original WATCHLIST plan.

## Trigger conditions for revisit

Revisit `/specify` ownership / shape when any of:

1. **AC quality drop (empirical)**: ≥3 shipped specs have AC gaps caught only at `/review` or `/verify` (suggests AC drafting needs specialist).
2. **Dialogue stall**: user reports clarifying-question loop in `/specify` stalls > 5 rounds (suggests dialogue management needs structure).
3. **Format drift**: `/specify` output diverges between sessions in ways that hurt `/plan` downstream (suggests helper-owns-shape would help).
4. **`/discover` integration**: once `/discover` ships (per `DISCOVER-PLAN.md`), it produces structured output that `/specify` may need to consume as input — adapter logic required.
5. **Bug-aware `/research` integration**: once `/research` refactor ships (per `REDESIGN-RESEARCH-PLAN.md`), it produces "Root Cause Hypothesis" that `/specify` may need to consume as AC seed for bug-fix specs — adapter logic required.

Triggers 4 and 5 are **scheduled** (not speculative) — they fire automatically once `/discover` and `/research`-refactor land. Triggers 1–3 are **reactive** — they fire only on empirical signal.

## Likely actions per trigger (sketch only, not committed)

- **Trigger 1 fires** → introduce `requirements-analyst` agent for AC review (independent perspective on drafted spec). NOT full `/specify` ownership; still orchestrator-driven, agent reviews the draft.
- **Trigger 2 fires** → revise dialogue flow in spec; consider AskUserQuestion bulk-confirm pattern (per `feedback_bulk_confirmation_shortcut`) for batches of clarifications.
- **Trigger 3 fires** → introduce `specify_helper.py` with schema for spec output (helper-owns-shape per `feedback_helper_owns_shape_principle`).
- **Trigger 4 fires** → add "import from `/discover` output" step to `/specify` spec; document input adapter; greenfield AC framing.
- **Trigger 5 fires** → add "import from `/research` Root Cause" step to `/specify` spec; document input adapter; bug-fix AC framing ("when fixed, X behavior Y under Z conditions").

## Constraints (apply if revisit triggered)

- Zero-escape-hatch policy (no OR / if / except / unless / use-judgment) in any spec edit.
- Helper-owns-shape if Trigger 3 fires.
- LLM-first density in spec body.
- Triple-agent verification on every spec edit: **instruction-author** writes/edits → **instruction-reviewer** checks intra-file logical flow + cross-reference consistency + sentence-level hallucination risk → **claude-code-guide** verifies Claude Code authoring conventions. All three clean before commit.
- Test-first if helper added (per `feedback_test_first_python_helpers`).

## When resuming work

**Redirect: active execution lives in [SPECIFY-REDESIGN-PLAN.md](./SPECIFY-REDESIGN-PLAN.md).** Read this file only for historical context on why redesign was triggered.
