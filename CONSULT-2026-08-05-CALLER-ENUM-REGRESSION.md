# Consultation Brief — v2 `/research` missed a hidden call-site (caller-enumeration gap)

**Date:** 2026-08-05 · **Audience:** a Claude dev instance working in this repo (`AIDevTeamForge`, branch `develop-2.0-init`) · **Purpose:** decide how to fix the harness so this class of miss can't recur. Related plans already drafted: `66-...` and `67-CALLER-ENUMERATION-GATE-MODE-DECOUPLE-PLAN.md`.

## TL;DR

A v2 DevForge run (`/research` → `/plan`) on a brownfield "remove filters" task **missed a second UI surface that runs the same query through a different use case**, and its plan chose a mechanism that would miss that surface even if it had been found. An earlier v1-era run on the identical task **found it**. This is a live confirmation of plan 67's thesis: caller-enumeration is gated on `mode == "bug"` and was skipped because this task auto-classified as `enhancement`.

## Background: the benchmark

`~/Projects/doosan/testframeworks/` benchmarks 5 spec-driven setups (DevForge v2, Kiro, Cursor, Spec Kit, BMAD) on ONE brownfield task, 3 runs each. The task (frozen prompt):

> "Remove the `distributionChannel`, `primaryShipToCity`, and `primaryShipToState` filters from the `searchOrganizationsV2` query on the 'Suggested' Customer search."

The task's difficulty is a **hidden second surface**. The subject repo is `db-cse-ui-strata` (Vue 3 + a `pkg-cse-core` domain layer). DevForge's run is in `testframeworks/forge/` (branch `eval/forge-run1`), currently at the plan stage (no code yet).

## The domain fact the run needed to discover

The "Suggested Customer" search runs from **two** UI surfaces, through **two different use cases**, both of which call the shared builder `OrganizationSearchConfigService.buildSearchQueryFilters`:

- **Surface A** — Customers tab → "Suggested" sub-tab → `SearchSuggestedOrganizationsV2UseCase` (the obvious one, named in the ticket).
- **Surface B** — order-detail modal `DealerToAccountNumberModal.vue` → the **accounts** `SearchOrganizationsV2UseCase` (tabType CUSTOMER, no userType). Despite the name, it drives the Customer path. This is the hidden one.

`buildSearchQueryFilters` has exactly three callers in the codebase (all in `pkg-cse-core/src/accounts/domain/cases/`): the two above plus `SearchSuggestedDealersV2UseCase`. The correct fix must cover BOTH Surface A and Surface B.

## What the v2 run actually produced (evidence)

Artifacts: `testframeworks/forge/research/2026-08-05-remove-the-distributionchannel-primaryshiptocity.md` and `testframeworks/forge/specs/001-suggested-search-filters/plan.md`.

1. **Mode auto-classified `Enhancement`** (research doc, "Mode: Enhancement"). This is the mode where `/research` Phase 2.4c caller-enumeration is OPTIONAL, not verify-gated.
2. **No exhaustive inbound-caller enumeration of `buildSearchQueryFilters` was done.** The plan's caller list (plan.md risk table) reads *"Contract, other Customer sub-tabs, Dealer, OrganizationsBLoC"* — which is **wrong and incomplete**: Contract/OrganizationsBLoC go through the *organizations* use case, which does NOT call `buildSearchQueryFilters`; and the caller that DOES matter — the **accounts `SearchOrganizationsV2UseCase`** (Surface B) — is absent from the list. The callers were reasoned from memory, not traced.
3. **Recommended mechanism (plan D2):** add a defaulted option to `buildSearchQueryFilters`, passed from `SearchSuggestedOrganizationsV2UseCase` only — a **caller-scoped flag wired to one caller**. Surface B never gets it.
4. **It explicitly rejected the layer-level approach** that would have covered both: plan D2 rejected-alternative (b), "reusing the `isInternalDealerTab` branch — overloads a dealer-scoped condition onto the customer path, semantically wrong and mis-scoping-prone." That rejected approach (an early-return keyed on the address/tab type, which every caller already passes) is what the v1 run used and it covers both surfaces by construction.

Net: the plan, if implemented, fails an objective probe that asserts Surface B's emitted query drops city/state.

## Why v1 got it right (contrast)

The v1-era run on the same task did a broad, exhaustive `city/state` sweep across the codebase, self-corrected a wrong "dead code" read, and stumbled onto the modal. It then chose a **layer-level** mechanism (early-return keyed on SHIP_TO/tabType) that both surfaces flow through — complete even without explicitly reasoning about Surface B. Messier process, correct result.

## Root cause (three compounding factors)

1. **Mode gating:** `enhancement` classification → Phase 2.4c inbound-caller enumeration optional → the graph trace that would have returned all three `buildSearchQueryFilters` callers (incl. Surface B) never ran. *(This is exactly plan 67.)*
2. **Wrong framing axis:** the adversarial framing (Phase 2.3b) debated "scoped seam vs direct shared-builder edit" — a real axis, but not "is Suggested-Customer one surface or two?" The unknown-unknown lived outside both frames, so rigor was spent reasoning *within* a frame that had already excluded the answer.
3. **Mechanism compounds discovery:** the caller-scoped option-flag is complete only if every needing-caller is wired; a layer-level key on shared data is complete by construction. v2 chose the fragile one *and* explicitly rejected the robust one.

## The tension to resolve (this is the consult)

- **Plan 67** says: make caller-enumeration a verify gate whenever a change touches an existing shared symbol, **independent of `mode`**. This run is its live justification. → Is Option D (mandatory enumeration + auditable justification-escape) the right shape? Can "touches a pre-existing shared symbol" be derived from the fix-path-helper anchor state cheaply (plan 67 OQ-2)?
- **Plan 66 WI-2** says: *"prefer caller-scoped opt-ins over layer-wide policy changes."* This run shows that rule, absent 67's enumeration, **steers toward the incomplete fix** — v2 followed exactly that preference and missed Surface B. → Should WI-2 be conditioned on 67 ("prefer caller-scoped *once every caller is enumerated*; absent that, a layer-wide key on shared data is more failure-tolerant")? Should 66 gain a hard dependency on 67?
- **Framing:** should Phase 2.3b's adversarial framing include a **"how many entry points / surfaces reach this behavior"** axis, so surface-count becomes a frame the run must probe rather than an unknown-unknown?

## Concrete asks for the dev instance

1. Verify the plan-67 believed-state (checks 8/9 gate on `mode == "bug"`; Phase 2.4c optional for enhancement) against the ACTUAL helper code in `src/devforge/lib/_research/` — not just the command prose.
2. Assess feasibility of plan 67 Option D's trigger ("touches a pre-existing shared symbol") from existing `record-fix-path-helper` anchor state.
3. Recommend whether to (a) ship plan 67's mode-decouple, (b) add a surface-count framing axis to Phase 2.3b, (c) re-condition plan 66 WI-2 on 67 — and in what order.
4. Sanity-check the counter-risk: making caller-enumeration always-on for shared-symbol changes adds CBM `trace_path` cost to every brownfield ticket — is that acceptable against the Phase 2 CBM budget?

## Pointers

- Harness: `src/commands/research/main.md` Phase 2.4c (~L427/L455/L515/L517); `src/devforge/lib/_research/_cmds_render_verify.py` (checks 8/8b/9); `src/devforge/lib/_research/_topic_conflicts.py` (`detect_mode_from_symptom`, token lists — note "remove"/"delete" are in NEITHER list); `_constants.py` (`MODE_ENUM`).
- Plans: `66-...md`, `67-CALLER-ENUMERATION-GATE-MODE-DECOUPLE-PLAN.md`.
- Evidence run: `~/Projects/doosan/testframeworks/forge/` (branch `eval/forge-run1`).
