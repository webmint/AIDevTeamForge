# 67 — Decouple Caller-Enumeration Gate from Bug/Enhancement Mode

**Status:** PHASE 0 DONE 2026-08-04 — D1–D7 RATIFIED as recommended (maintainer bulk sign-off): D1 = Option D with an UNCONDITIONAL mode-independent trigger + `--no-shared-callers-justification` auditable escape; D2 = no detection signal (the bootstrap question dissolves — every run records ≥1 helper or files the justification); D3 = classifier UNCHANGED (moot post-decouple; removal stays ambiguous→ask-user) → Phase 4 SKIPPED; D4 = anti-truncation MOOT (2026-08-04 sweep: 0 `grep | head` hits in research/plan/breakdown/discover specs) → Phase 5 SKIPPED; D5 = CONFIRMED; D6 = carry-in-handoff, absent→empty, justification text rides the handoff too; D7 = check 8b STAYS bug-gated. `/discover` out-of-scope CONFIRMED (no detect-mode / fix_path / inbound_caller machinery). **PHASES 1–3 SHIPPED 2026-08-04 (working tree)** behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops: **Phase 1** = check 8 mode-independent + `record-no-shared-callers-justification` verb + BOTH-direction contradiction guards (`_cmds_render_verify.py`, `_cmds_dataflow.py`, `_cli.py`, `_state.py`; 440 research tests incl. the headline enhancement-mode regression); **Phase 2** = `research/main.md` 2.4c prose reconciled (header `(MANDATORY — mode-independent)`, `:515` gate list, no-shared-callers escape block, Phase 3 Verify paragraph; 2.4d/2.5b untouched); **Phase 3** = typed `CallerEnumeration` carry (`_research/handoff_schema.py` `PlanSeeds.caller_enumeration`, `_handoff_build.py::_build_caller_enumeration` verbatim copy, `plan_helper::_render_research_plan_seeds` render with byte-identical old-handoff fallback, `plan/main.md` Phase 1.3 consumption pointer; 31 new tests). Phases 4+5 SKIPPED (moot per D3/D4). **Phase 6 (fixture regression + e2e) DEFERRED by the maintainer 2026-08-04 (will test later — not blocking; the check-8 matrix unit tests already cover the headline regression at the helper level). Plan CLOSED pending that opportunistic e2e.**
**Type:** BUILD plan (verify-gate trigger change in `_research` helper + research-handoff carry) + small DECISION component (removal-token classifier).
**Branch:** `develop-2.0-init`.
**Created:** 2026-08-03, seeded from a forensic trace of a real v1 harness run (session `e3878771-1bb0-443e-86b7-f43884f9b5ef`, feature `specs/021-suggested-customer-filters` in the mintEnvoy wrapper workspace) that nearly missed a second UI surface.
**Rewritten:** 2026-08-03 (v2) — the believed-state checklist was verified against `src/` (one correction: check 9 is NOT mode-gated); the five-solution comparison matrix is folded in as headline evidence; the plan-66 handoff seam is absorbed as a new work item. Phases now name their mandatory agent loops per repo convention.

---

## Problem

The `/research` Phase 2.4c caller-enumeration mechanism — `fix_path_helpers` + `inbound_callers`, the machinery that surfaces EVERY inbound caller of a helper a change touches — is the thing that prevents shipping an incomplete fix when the change modifies a **shared helper with more than one caller**. But its *enforcement* is gated on `memo.mode == "bug"` (see Verified state for the exact gate surface).

And the mode is **auto-detected by a deterministic token classifier**, not set by the user: bug-only tokens → `bug`; enhancement-only tokens → `enhancement`; **both or neither → `None` → orchestrator asks the user to disambiguate.**

**The failure this creates** (empirically demonstrated): a change that touches an existing shared helper can skip mandatory caller enumeration when (a) auto-classified `enhancement`, or (b) auto-classified `None`/ambiguous and the human answers `enhancement`. In session `e3878771`, a v1-shape run investigating "remove three filters from `searchOrganizationsV2`" enumerated surfaces with a truncated `grep "SUGGESTED_CUSTOMERS" ... | head -20` that silently dropped a second UI surface (`DealerToAccountNumberModal`, which runs the same query through a *different* use case). The miss was caught only by an adjacent thread (a city/state *sort* sweep), not by the surface enumeration itself. v2's graph-based Phase 2.4c (`trace_path` inbound-caller enumeration) closes the *truncation* facet — `trace_path` is complete, not `head`-truncatable — **but only if it runs**, and its running is mode-contingent.

**Two compounding classifier facts make this task-shape land in the ungated path:**
1. The seed ticket ("**Remove** the distributionChannel / primaryShipTo* filters …") contains NO bug token AND NO enhancement token — so it returns `None` → ambiguous → human mode-call. A human who frames removal as "widen the results" picks `enhancement` → ungated.
2. Removal/deletion tasks are therefore *systematically* ambiguous: any "remove X" ticket with no other signal always defers to the human, and a reflexive "enhancement" answer silently drops the caller-enumeration gate.

## Why it matters

The headline evidence is no longer one v1 near-miss — it is **the majority outcome across five independently-built solutions to this exact ticket** (`2026-07-31-mig-2957-solution-comparison.md`, repo root; also at `cse-strata-ws-forge/research/` in the mintEnvoy wrapper workspace):

- The target query runs on **two live surfaces** (`:23`): Surface A = the Customers-tab "Suggested" sub-tab → `SearchSuggestedOrganizationsV2UseCase`; Surface B = the order-detail delivery modal `DealerToAccountNumberModal` → the accounts `SearchOrganizationsV2UseCase`. Surface B sends the city/state search terms.
- **4 of 5 tool runs left Surface B still sending city/state** (`:33` — Cursor, Claude+custom-skills, Kiro, Cursor-agent). All five were `tsc --noEmit` clean (`:35`); three of the four missers added zero new test failures (`:36`). Only the caller-enumerating spec-driven run surfaced Surface B at all.
- Honest caveat (`:109`): the ticket asked for Surface A only, so covering Surface B was a deliberate informed scope decision by that run's author, not automatically "the right fix." The gate's value is **knowing the second caller exists before the spec commits** — the human still decides what to do about it.

So the whole value of the research phase over a one-shot tool is that it finds hidden callers/surfaces BEFORE the spec commits. That edge is only reliable if caller enumeration is a **gate**, not a mode-contingent option. As currently wired, the single highest-value discovery step is mandatory for the task class (`bug`) that least needs prompting and optional for the class (`enhancement` / ambiguous removal) where a missed caller most quietly ships an incomplete fix — invisibly, past a clean type-check and a green suite.

## Verified state (2026-08-03 — replaces the believed-state checklist)

Verified against `src/` this session; re-read only if `src/` changed since.

- **[VERIFIED] The mode-gated header is real.** `src/commands/research/main.md:427` reads "Phase 2.4c — Helper-API surface enumeration (MANDATORY for bug mode; OPTIONAL for enhancement)" verbatim. The bug-mode gate paragraph is at `:515` ("**MANDATORY in bug mode.** Skipping is forbidden when `memo.mode == \"bug\"` …") and the enhancement prose at `:517` ("For enhancement mode this phase is OPTIONAL — run it when the enhancement adds a new code path that touches an existing helper signature; skip when the enhancement is purely additive in a new module.").
- **[VERIFIED] Check 8 is bug-gated.** `_research/_cmds_render_verify.py:261-266` — the non-emptiness violation fires only under `(report.get("mode") == "bug" or memo.get("mode") == "bug")`. Check 8b (`:268-313`, the presentation-layer cross-package rule) carries the same bug-mode condition.
- **[VERIFIED — CORRECTS v1] Check 9 is NOT mode-gated.** `_cmds_render_verify.py:315-323` iterates `fix_path_helpers` unconditionally — it fires in enhancement mode too, whenever a helper was voluntarily recorded, and is merely VACUOUS when the list is empty. Only check 8's non-emptiness forcing is bug-gated. v1's "checks 8, 9 fire only in bug mode" was imprecise. Two consequences: **(a)** the decouple's blast radius shrinks to **check 8's trigger condition only** — check 9 already composes mode-free and needs no edit; **(b)** `research/main.md:515` frames check 9 under the "MANDATORY in bug mode" paragraph, misdescribing the code — Phase 2 (prose reconciliation) absorbs fixing that phrasing.
- **[VERIFIED] Partial coverage exists** (answers v1 checklist item 6): check 9 fires in enhancement mode IF helpers were recorded; nothing forces the recording. The enhancement escape runs through check 8 alone.
- **[VERIFIED] Token lists confirmed.** `_research/_topic_conflicts.py:50-59` — `_BUG_TOKENS = fail, broken, wrong, missing, error, crash, bug, regress, doesn't work, not working, freezes, hangs, stuck`; `_ENHANCEMENT_TOKENS = slow, faster, optimize, support, add, integrate, should, enhance, improve, expand, extend`. "remove" / "delete" / "drop" / "strip" appear in NEITHER list, so `detect_mode_from_symptom` (`:62-79`) returns `None` for removal tickets — they are systematically ambiguous.
- **[VERIFIED] Ambiguity routes to the human, with no silent default.** `cmd_detect_mode` (`_research/_cmds_phase0.py:135-157`) persists `memo["mode"] = None` on ambiguous, exits 0, and lets the caller decide; `research/main.md:293` routes a null mode to AskUserQuestion ("Treat this as a bug or an enhancement?") then `detect-mode --override <choice>`. No silent default to `enhancement` anywhere.
- **[VERIFIED] The truncation facet is already closed where 2.4c runs.** Phase 2.4c Step 2 (`research/main.md:455-470`) uses `trace_path(<helper_qn>, mode=calls, direction=inbound)` with verbatim-copy `file:line` grounding — no `grep | head` in the phase. Only its RUNNING is mode-contingent.
- **[VERIFIED] The bug-mode-only phases/checks are correctly bug-specific** (confirms v1 OQ-5 for the checks): Phase 2.4d's click-handler trace gate (`research/main.md:519-523`) and checks 13 / 15 / 16 in the `cmd_verify` docstring (`_cmds_render_verify.py:120-143`) are runtime-value-semantic and stay bug-gated. Phase 2.5b literal archaeology remains a spot-check note at build time, not a re-derivation.
- **[VERIFIED — half-answers OQ-2, and sharpens the fork] Recorded helpers target pre-existing code BY CONSTRUCTION.** `record-fix-path-helper` rejects the `(none)` sentinel for `--file-line` (`research/main.md:447`) AND requires anchoring to an already-recorded finding's `file_line` (`:449`, sticky-reject at `:451`). **But this exposes Option A's bootstrap problem:** A's trigger cannot read `fix_path_helpers` state, because the failure mode being gated is precisely that nothing was recorded. The trigger needs a signal independent of 2.4c state — which collapses Option A toward either C (always-on) or D. This STRENGTHENS the D leaning: "record helpers OR file an explicit `--no-shared-callers-justification`" is the only shape that gates the empty case without paying always-on cost.
- **[VERIFIED] The enumeration barely reaches the research handoff.** `inbound_callers` has **0 occurrences** in both `_research/handoff_schema.py` and `_research/_handoff_build.py` — no caller ever reaches `/plan`. `fix_path_helpers` has no typed handoff field either, but it IS read lossily: `_build_affected_areas` (`_handoff_build.py:84-100`, called at `:417-420`) groups helper `file_line`s by package into `AffectedArea{area, files, impact}` (`handoff_schema.py:339-344`), dropping the helper QN and every caller row; `_resolve_cite_to_file_line` (`:263-275`) uses the list only for cite→`file_line` resolution. (This is a correction of the v2 brief's "0 hits in both files"; the conclusion is unchanged — no typed carry of the enumeration. Feeds the new work item below.)
- **[VERIFIED 2026-08-04 at Phase 0]** `/discover` (greenfield) is correctly OUT of scope — `src/commands/discover/main.md` and `src/devforge/lib/_discover/` contain no `detect-mode`, `fix_path_helpers`, `inbound_callers`, or Phase-2.4c machinery. The gap is `/research`-only.

## Core design question (the fork)

How is the enumeration gate re-triggered independent of mode?

- **Option A — trigger on "touches existing shared symbol."** Extend check 8 to fire whenever a `fix_path_helper.file_line` resolves to a pre-existing symbol, regardless of `memo.mode`. Most direct — **but see the bootstrap problem in Verified state: A cannot key on state that the failure mode leaves empty.**
- **Option B — trigger on "modifies an existing signature."** Narrower: gate only when the change alters an existing function/method *signature*. Fewer false positives, but misses body-only changes to shared code that still need caller review.
- **Option C — always-on in `/research`.** Caller enumeration mandatory for every `/research` run (brownfield always has callers). Simplest gate; highest cost on trivial/local tickets.
- **Option D — C-shaped trigger + a cheap auditable escape.** Check 8 fires mode-independently, plus an explicit `--no-shared-callers-justification` setter the LLM must fill when it asserts the touched symbol has zero other callers (mirrors the existing `--single-layer-justification` escape pattern). Auditable opt-out instead of silent skip. **Ratification target**, reinforced by the bootstrap finding.

## New work item — carry the enumeration into the research handoff (the plan-66 seam)

Extend the research handoff so Phase 2.4c's enumeration (`fix_path_helpers` + `inbound_callers`) rides `research/<date>-<slug>/handoff.json` as a typed field — producer `research_helper finalize-handoff` / `_research/_handoff_build.py`, schema `_research/handoff_schema.py` — consumed by `/plan`, whose PHASE 0a.5 already follows `provenance.upstream_handoff_path` (`src/commands/plan/main.md:58,69`) and renders upstream seeds. The consumption lane exists; only the payload is missing.

**Motivation — the demand is LIVE, not forward-looking.** Plan 66 (Phases 0–4 SHIPPED 2026-08-03, working tree; only Phase 6 testForge20 e2e remains, user-driven) landed WI-2's Narrowing rule and its consumer sites are in `src/` today:

- `src/constitution.md:121-124` — the Narrowing rule: prefer a caller-scoped opt-in over a layer-wide policy change, and "A broadened rule inside a shared service MUST name every current caller it affects, in the plan."
- `src/commands/plan/main.md:349` — architect consult sub-question 7: for a layer-wide restriction, "return the list of every current caller it affects."
- `src/commands/plan/main.md:417` — the Key Design Decisions table note requiring the caller list in the decision's Why column; `:494` — PHASE 2.5 step 7, the read-side backstop that re-enters Phase 1.3 when the caller list is missing.
- `src/agents/architect.md:153` — Rule 9's Narrowing forcing step: "a layer-wide restriction with an unnamed caller set is not recordable."

Every one of those sites DEMANDS a caller list at `/plan` that (pre-Phase-3) had **no typed upstream source** — the architect re-derived callers through its own CBM calls, duplicating work `/research` Phase 2.4c already grounded and verified. Phase 3 closed this: the carry feeds the live consumer, and `plan/main.md`'s Phase 1.3 consult body now instructs using the carried `**Caller enumeration**` section as sub-question 7's caller-naming source instead of re-deriving — with three re-derivation triggers: helpers the section does not name, `(no inbound callers recorded)` entries, and a ONE-fresh-`trace_path` freshness cross-check per helper a Key Design Decision RESTRICTS (carried list = seed, not terminal answer); the zero-shared-callers justification form is treated as an UNVERIFIED research-time assertion. Plan 66 does not own this wiring; 67 absorbed it.

**Backward compatibility is mandatory:** absent field → empty; old handoffs parse unchanged. The in-repo precedent is plan 66's SHIPPED `BreakdownSeeds.pure_builder_targets` (`_plan/handoff_schema.py:286` — a defaulted `List[PureBuilderRow]` populated by `plan_helper finalize-handoff`); 67's carry field copies that shape.

## Division of labor vs plan 66

- **66 owns** the `/plan`-side PROSE naming rule (WI-2: caller-scoped-over-layer-wide; "name every affected caller in the plan") plus the property-testing lane and its gate. 66's Phases 0–4 are SHIPPED 2026-08-03 (working tree); only Phase 6 (testForge20 e2e, user-driven) remains.
- **67 owns** the `/research`-side MECHANICAL enumeration gate (the mode-decouple of check 8's trigger) plus the handoff carry above, which gives 66's naming rule its typed upstream source.
- **Convergence note:** 66 SHIPPED its Narrowing rule with the detector deliberately deferred — `src/commands/plan/main.md:494` states it outright: "the mechanical detector for narrowing is deliberately deferred (there is no helper verb for it — do not invent one)." The trigger 67 leans toward (pending Phase 0 ratification) — "touches a pre-existing shared symbol with recorded callers" — is the natural future backing detector for that rule. Recorded here so neither plan builds it twice, and so a future session does not read 66's deferral as an invitation to invent a verb outside this plan.
- **Cross-ref:** 66's "Dependencies + related" carries a forward pointer to 67, naming this section as the authoritative split.

## Open questions

- OQ-1 (the fork): A/B/C/D — leaning D (mode-independent trigger + auditable justification escape), now reinforced by the bootstrap finding.
- OQ-2: "pre-existing symbol" detection — **half-answered** (recorded helpers are pre-existing by construction, per Verified state). The remaining half is the bootstrap problem: what signal fires when NOTHING was recorded? Answer this before drafting Phase 1.
- OQ-3: Removal-token classifier — add "remove", "delete", "drop", "strip", and to WHICH set? Removal is genuinely bug-or-enhancement-ambiguous, so the honest move may be keeping it ambiguous (→ ask user). Decide whether the change is needed at all post-decouple (it likely becomes moot).
- OQ-4: Cost — an always-on trigger adds CBM `trace_path` calls to every brownfield ticket. Quantify against the Phase 2.1 cost gate already surfaced to the user (`research/main.md:309` — 15-30 calls one-package, up to 60-120 cross-cutting). Is one inbound-caller trace per touched helper acceptable overhead?
- OQ-5: **RESOLVED for the checks** by Verified state (checks 13/15/16 + Phase 2.4d are runtime-value-semantic and stay bug-gated). Ratify as confirmed; spot-check Phase 2.5b at build time.
- OQ-6: Anti-truncation guard — are there OTHER enumerations in `/research` (or `/plan`, `/breakdown`) that still use `grep | head` on reachability-relevant sweeps? If so, add a "never truncate a reachability enumeration; print total match count" convention.
- OQ-7 (new): Handoff-carry mechanism — carry the enumeration in `handoff.json` as a typed field, vs park-once/read-in-place (the plan 53 `design-anchor.json` precedent, where the artifact is written once and read where it sits). Leaning **carry-in-handoff**, because `/plan`'s consumption chain for upstream handoff fields already exists and the enumeration is intake-scoped, not feature-scoped. Missing/legacy-handoff behavior should copy 66's shipped `verify-property-coverage` fallback contract (`src/commands/breakdown/main.md:469-473`): never-declared → skip at exit 0, declared-but-handoff-less → fail-closed with a `plan_helper finalize-handoff` remedy, so a declared-but-unverifiable case can never silently skip.
- OQ-8 (new): Should check 8b's cross-layer condition decouple alongside check 8? Leaning **NO — 8b stays bug-gated**: its trigger is anchored on the primary SYMPTOM site being presentation-layer, and "symptom site" is a bug-mode concept; an enhancement-mode run has no symptom-anchored primary finding in the same sense, so a decoupled 8b would fire on a frame it was not designed for.

## Phases

Every `main.md` / agent / constitution edit routes through **instruction-author → instruction-reviewer**, plus **claude-code-guide** for files that ship into a consumer's `.claude/`. Every helper change routes through **python-engineer → python-reviewer**, test-first. No phase is exempt.

- **Phase 0 — Ratify (RATIFICATION-ONLY).** The verified-state table replaces the v1 checklist; the only item left to confirm is `/discover` being out of scope. Maintainer sign-off on D1–D7. Do not build before OQ-2's bootstrap half is answered.
- **Phase 1 — Verify-gate change.** Extend **check 8's trigger only** from `mode == "bug"` to the ratified condition; **check 9 needs no edit** (already mode-free — Verified state). Check 8b's bug-mode condition is untouched per D7 (leaning: stays bug-gated). Add the Option-D justification setter if ratified. `_research/_cmds_render_verify.py` + `_constants.py`. Loop: python-engineer → python-reviewer.
- **Phase 2 — Command-prose reconciliation.** `research/main.md` `:427` / `:515` / `:517` rewritten to state the mode-independent trigger, INCLUDING correcting `:515`'s framing of check 9 as bug-gated. Bug-mode-only phases (2.4d / 2.5b) unchanged. Loop: instruction-author → instruction-reviewer + claude-code-guide.
- **Phase 3 — Handoff carry (the plan-66 seam).** Typed enumeration field in `_research/handoff_schema.py` + producer wiring in `_handoff_build.py` / `finalize-handoff`, backward-compatible (absent → empty, old handoffs parse unchanged); `/plan` renders the carried callers at PHASE 0a.5. Loops: python-engineer → python-reviewer (schema + producer + tests round-tripped via the real producer, per repo discipline); instruction-author → instruction-reviewer + claude-code-guide for any `plan/main.md` render touch.
- **Phase 4 (conditional on OQ-3)** — Removal-token classifier adjustment in `_topic_conflicts.py`, only if Phase 0 decides it is still needed post-decouple. Loop: python-engineer → python-reviewer.
- **Phase 5 (conditional on OQ-6)** — Anti-truncation convention sweep across `/research` `/plan` `/breakdown` reachability enumerations. Loop: instruction-author → instruction-reviewer + claude-code-guide.
- **Phase 6 — Regression + e2e (user-driven).** A fixture ticket that (a) is a "remove X from a shared helper" enhancement/ambiguous task and (b) touches a helper with ≥2 callers: confirm `verify` now REJECTS a report missing the second caller's `inbound_callers` row, in enhancement mode, with no human "bug" answer. The direct regression for the comparison-matrix miss.

## Decisions to ratify (Phase 0)

- D1: The fork (A/B/C/D) — leaning D, reinforced by the bootstrap finding, and accepting the OQ-4 per-touched-helper trace-call overhead as the cost of closing the gap.
- D2: The trigger signal — specifically, what resolves the bootstrap problem (a trigger independent of `fix_path_helpers` state).
- D3: Removal-token classifier — change or leave (OQ-3), and whether it is moot post-decouple.
- D4: Scope of the anti-truncation convention (OQ-6) — `/research` only, or pipeline-wide.
- D5: Bug-mode-only phases stay gated — ratify as CONFIRMED (verified, not re-derived).
- D6: Handoff-carry mechanism (OQ-7) — carry-in-handoff vs park-once/read-in-place, plus the missing/legacy-handoff fallback contract (skip vs fail-closed, per 66's `verify-property-coverage` precedent).
- D7: Check 8b's cross-layer condition (OQ-8) — decouple alongside check 8, or stay bug-gated (leaning: stays bug-gated).

## Dependencies + related

- Plan 66 (property-based testing + shared-code-narrowing rule) — SIBLING; Phases 0–4 SHIPPED 2026-08-03 (working tree), only Phase 6 (testForge20 e2e, user-driven) remains. See "Division of labor vs plan 66" for the exact split and the seam 67 absorbs.
- Plan 41 (agent-executor reachability) — the walker/orphan-gate pattern this extends from agent-reachability to change-impact-reachability.
- Plan 18 (scope-fidelity + prompt intake) — established the mode-detection + intake-interrogation lane this plan tightens; the `detect-mode` ambiguous→ask-user flow is plan 18's.
- Plan 53 (design anchor first-class) — the park-once/read-in-place precedent OQ-7 weighs carry-in-handoff against.
- Plan 62 (SMT requirements consistency) — unrelated mechanism, same "make the invisible step a gate" philosophy.
- External evidence: `2026-07-31-mig-2957-solution-comparison.md` (repo root; also `cse-strata-ws-forge/research/` in the mintEnvoy wrapper workspace) — the five-solution matrix; session `e3878771-1bb0-443e-86b7-f43884f9b5ef` — the v1 truncation near-miss trace.

## Context for next session

The trap is over-fixing: do NOT rip mode out of `/research`. Mode legitimately gates the bug-specific runtime-value phases (2.4d, 2.5b, checks 13/15/16) — those stay bug-only, now verified rather than assumed. This plan touches ONE gate: **check 8's trigger**. Check 9 is already mode-free and must not be edited; the only check-9 work is fixing `research/main.md:515`'s prose, which misdescribes it as bug-gated. The load-bearing question is OQ-2's remaining half — the bootstrap problem: the trigger cannot read `fix_path_helpers`, because "nothing was recorded" is exactly the failure being gated, which is why Option A collapses toward C or D. The removal-token classifier (OQ-3) remains a red herring to resist over-investing in: once the gate is mode-independent, the bug/enhancement answer stops determining whether callers get enumerated. The new handoff-carry item must not balloon — it is a typed field plus a render, plan-53-adjacent in scope, with NO new consumer command and no new agent.

## When resuming work

1. Read this file in full. The Verified-state table replaces re-derivation — re-read `src/` only if it changed since 2026-08-03.
2. Answer OQ-2's bootstrap half before drafting the gate change — it decides D1 (C vs D).
3. Confirm the one open item (`/discover` out of scope), then ratify D1–D7 before writing any helper, schema, or prose change.

## Verify

- Phase 0 done = `/discover` scope confirmed + D1–D7 ratified (with OQ leanings confirmed or overridden), recorded here.
- Phase 1 done = on an enhancement-mode (or ambiguous, human-answered-"enhancement") ticket that touches an existing helper with ≥2 callers, `research_helper verify` REJECTS a report whose `fix_path_helpers` / `inbound_callers` omit a live caller, with NO dependence on the bug/enhancement classification; check 9 and the bug-mode-only checks are byte-unchanged; tests green.
- Phase 2 done = `research/main.md` states the mode-independent trigger at `:427` / `:515` / `:517`, and no longer describes check 9 as bug-gated.
- Phase 3 done = the typed enumeration field ships with round-trip tests via the real producer, handoffs written before the change parse unchanged (absent → empty), `/plan` renders the carried callers at PHASE 0a.5, AND `plan/main.md`'s Phase 1.3 consult body instructs using the carried section as the Narrowing rule's caller-naming source with the restricted-helper freshness cross-check (ONE fresh `trace_path` per helper a decision restricts — no silent re-derivation, no stale-list blind trust).
- Phase 4 done = `_topic_conflicts.py` token-list change (if Phase 0 ratifies it as needed) ships with tests, or Phase 0 explicitly records it moot.
- Phase 5 done = anti-truncation convention landed at the D4-ratified scope with no remaining `grep | head` on a reachability enumeration.
- Phase 6 (e2e, user-driven) done = the fixture regression above fails the gate before the fix and passes after, with the bug-mode-only runtime phases unchanged.
