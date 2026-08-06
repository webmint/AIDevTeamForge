# Research — Two proposed gates: "sufficiency of context" (idea 1) and "post-change consequence" (idea 2)

**Date:** 2026-08-05 · **Branch:** `develop-2.0-init` · **Status:** RESOLVED 2026-08-06 — both ideas routed to plans; this doc is now the rationale record, not the recommendation of record.

> **Resolution (2026-08-06):** Plan 67 SHIPPED before this doc's recommendations could apply (`e22317c`, release 2.0.7) — the "reframe plan 67" recommendation below is therefore impossible as written. **Idea 1** → folded into `69-CALLER-ENUM-RESIDUAL-HARDENING-PLAN.md` as **WI-F** (checks 8b + 18 mode-widened per OQ-A's structural/runtime split; caller-enumeration facets already covered by 67 + 69 WI-A/WI-E). **Idea 2** → `71-POST-CHANGE-CONSEQUENCE-PLAN.md` (the "new plan 68" named below — that number was taken by the intake plan; 71 is the actual home). Plan 69 SHIPPED+CLOSED 2026-08-06; plan 71 Phases 0–6 SHIPPED 2026-08-06 (e2e pending).
**Seed:** forge benchmark run (`testframeworks/forge`, `eval/forge-run1`) parametrized a shared helper at a low-context layer AND left the branch its change orphaned in place. Companion to plans 66, 67, and `CONSULT-2026-08-05-CALLER-ENUM-REGRESSION.md`.

---

## The two ideas (as stated by maintainer)

**Idea 1 — sufficiency of context before applying a change.** Before applying a change at a code location, check whether that location has *enough data/context* to make the change correctly and completely. If not, **trace UP to the first caller (layer) that does** — and only *then* decide where/how to apply it. (Prevents "parametrize a shared low-context helper with a flag the caller must remember to set.")

**Idea 2 — evaluate whether a change enhances the environment, and whether related follow-on enhancements are now possible.** After determining a change: does it *simplify/enhance* the codebase? Does it render other code **dead** or enable **related cleanups/consolidations**? Surface and apply them. (Prevents "guard-and-leave" — the primaryShipTo* branch left dead in `buildSearchQueryFilters`.)

---

## Grounding — the forge run exhibits BOTH failures

- **Idea-1 failure:** v2 chose to parametrize `buildSearchQueryFilters` (a shared, low-context builder) with `{ includeAddressFields }`, threading the scope decision *down* via a flag the suggested use case sets. The layer that actually *has* the context to decide "this is a Suggested Customer search" is the use case (it knows `relationType == SHIP_TO`), not the builder. The change was applied at a location without sufficient context; the correct layer was one hop up. (See `CONSULT-...-CALLER-ENUM-REGRESSION.md`.)
- **Idea-2 failure:** the same change makes the `: 'primaryShipToCity'` / `: 'primaryShipToState'` arms of the address-builder unreachable for the customer/SHIP_TO case, yet leaves them in place — the address-builder now "works only half." The clean solution (v1 / solution A) *simplified*: it deleted those arms and collapsed the builder to BILL_TO-only. v2's parametrization is additive-only; it never asked "what did my change just kill?"

---

## Research findings — what the harness ALREADY has

### Idea 1 is ~80% built — but bug-mode-only

The `/research` Phase 2.4c "fix-path helper" machinery is almost exactly idea 1, gated to bug mode:

- **`fix-path helper`** = "a helper whose signature carries the symptom value, or any value the symptom value derives from" (`research/main.md:433`). Finding *where* to apply the change.
- **Stopping rule — layer-boundary trace-up** (`:435`): "Trace AT MOST 2 layer boundaries above the symptom site, following dependency-inversion (outer→inner)… cross application/domain package boundaries." **This is idea 1's "trace up until the right layer," already implemented.**
- **check 8b (cross-layer rule)**: rejects a report where all fix-path helpers sit in the symptom's own package when the symptom is presentation-layer — forces a cross-boundary trace-up.
- **check 13 (single-layer recommendation gate)**: when all helpers resolve to one package, demands explicit justification — pushes toward the right layer.
- **check 18 (argument-duplication) + Phase 2.5b (literal archaeology)** (`:858`, `:676`): **the parametrization-smell detector.** "Argument duplication signals the default-source belongs at a different layer… escalate the default-source upstream (wrapper signature / state initialization / **use-case default**)." This is precisely the "don't thread a flag down; put the default at the layer that owns the decision" instinct — already coded.

**The gap:** every one of these is `MANDATORY in bug mode` and optional/absent in enhancement mode (`:515`). The MIG-2957 task classified as **Enhancement** (plan 67 §Problem), so *none of this fired*. Additionally, the machinery is framed around **the symptom value and where it derives from** (bug tracing), not around the more general **"does this location have sufficient context to make this change"** — which is the enhancement-relevant framing.

**Conclusion (idea 1):** this is not a new mechanism — it is **plan 67's reframe, widened.** Plan 67 currently decouples only the *caller-enumeration* facet from mode. Idea 1 is the *same decoupling applied to the whole fix-path-helper trace-up*, under a unifying principle: **sufficiency of context.** Recommend folding idea 1 into a reframed plan 67 (below), not a separate plan.

### Idea 2 is a genuine gap

- **`dead_siblings`** (`:484`): the harness *does* detect dead code — but only **pre-existing** dead code found during investigation ("siblings with 0 inbound callers AND 0 textual call sites"). There is **no mechanism for code the proposed change will render dead.**
- **Constitution §3.5 "No dead code"** (`constitution.md:64`): "Delete unused functions, variables, imports… Do not comment them out." A *rule*, enforced nowhere as a *phase* against change-induced deadness.
- There is **no phase** that evaluates: (a) does this change orphan a downstream branch, (b) does it simplify/enhance, (c) does it enable related follow-on cleanups/consolidations.

**Conclusion (idea 2):** genuinely new. It is about the **consequences** of a change (what it kills, what it enables), distinct from idea 1/67's concern of **correct placement/scope**. Recommend a **new plan 68**.

---

## Formulation

### Idea 1 → REFRAME plan 67 as "Sufficiency-of-Context, decoupled from mode"

Widen 67 from "make caller-enumeration mandatory on shared-symbol changes" to:

> **Before recommending where to apply a change, the pipeline must establish that the chosen site has sufficient context to make the change correctly and completely — via the Phase 2.4c fix-path-helper trace-up (layer-boundary walk + inbound-caller enumeration + the argument-duplication/upstream-default smell) — and this is MANDATORY whenever the change touches an existing shared symbol, independent of bug/enhancement mode.**

The three existing sub-mechanisms all become mode-independent for shared-symbol changes:
- **Trace-up to the sufficient-context layer** (Stopping rule + check 8b) — answers "where does the decision belong."
- **Inbound-caller enumeration** (check 9 — plan 67's current core) — answers "what surfaces does that layer serve" (completeness / Surface B).
- **Argument-duplication / upstream-default** (check 18 + literal-archaeology) — answers "am I threading a flag down that belongs at the owning layer" (the parametrization smell).

The unifying test the maintainer articulated: *"does this place have enough data to apply the change? If not, trace up until the first caller that does, then decide."* That is the fix-path-helper trace-up, made unconditional.

### Idea 2 → NEW plan 68 "Post-change consequence analysis"

Two coupled sub-gates, evaluated at `/plan` (predict) and enforced at `/verify` (confirm):

1. **Change-induced dead-code detection.** Given the recommended change, trace the code paths it renders unreachable (e.g., an early-return added above a branch dominates the branch's else-arm). Extend the `dead_siblings` notion from "already dead" to "**dead-by-this-change**." Require each such path be removed (constitution §3.5), not guarded-and-left. Verify gate: a change that adds a dominating condition upstream of a now-unreachable branch, without removing that branch, fails.
2. **Follow-on enhancement evaluation.** Evaluate whether the change is a *simplification* (removes a concept/branch/parameter) and, if so, surface the related cleanups it enables (collapse a now-trivial ternary, delete a now-single-use option, consolidate a now-redundant sibling). Distinguish MUST-do (dead code — sub-gate 1) from MAY-do (opportunistic consolidation — recommend, don't force).

---

## Recommended structure

| Idea | Home | Rationale |
|---|---|---|
| **1 — sufficiency of context** | **Reframe plan 67** (widen scope + retitle) | It IS 67's decoupling, applied to the whole fix-path-helper trace-up, not just caller-enumeration. Same mechanism, same mode-gate fix. Splitting it out would fragment one coherent change. |
| **2 — post-change consequence** | **New plan 68** | Distinct concern (consequences vs placement), distinct pipeline stage (post-recommendation), distinct mechanism (change-induced deadness + follow-on). No existing machinery beyond a rule. |

Plan 66's WI-2 ("prefer caller-scoped opt-ins") now sits *downstream* of both: it is only safe once idea 1 has established the right layer AND idea 2 has confirmed the change doesn't leave dead cruft. Add the dependency edge 66 → 67 → (66 revisited).

---

## Open questions / feasibility (for Phase 0 of the resulting plans)

- **OQ-A (idea 1):** the fix-path-helper trace-up is heavily bug-mode-coupled in the helper code (`_research/_cmds_render_verify.py`, checks 8/8b/9/13/14/18). Confirm which sub-checks generalize cleanly to enhancement mode vs which are genuinely bug-specific (e.g., value-semantics/literal-archaeology are runtime-bug-specific and should probably stay bug-gated; the layer-boundary + caller + argument-duplication checks are structural and should generalize).
- **OQ-B (idea 1):** "sufficient context" needs an operational definition. Candidate: a change site has *insufficient* context when the correct behavior at that site depends on a discriminator (which caller / which surface) not available in its own parameters — detectable as "the recommended approach adds a parameter whose value is computed by the caller from information the callee lacks." check 18 already approximates this; formalize it.
- **OQ-C (idea 2):** change-induced deadness detection is a static reachability delta (paths reachable before the change minus after). The CBM graph supports the reachability query (confirmed: `trace_path` inbound/outbound). Feasibility looks good; the hard part is computing the delta from a *proposed* (not-yet-applied) change — may need the plan's recommended-approach to be concrete enough (which check 18's `--proposed-call-shape` already pushes toward).
- **OQ-D:** cost — both add CBM traces per shared-symbol change. Same budget concern as plan 67; bound identically.
- **OQ-E:** empirical — re-run forge-run2/run3 with idea 1 folded into 67; confirm the modal surfaces and the parametrization smell fires. Then a synthetic "simplification" ticket to exercise idea 2's dead-branch detection.

## Pointers

- Existing machinery: `research/main.md` Phase 2.4c (`:429-520`), Phase 2.5b literal-archaeology (`:637-676`), checks 8b/13/18 (`:838-915`); `_research/_cmds_render_verify.py`; `dead_siblings` setter (`:487`).
- Constitution §3.5 no-dead-code (`constitution.md:64`).
- Evidence run: `testframeworks/forge` (`eval/forge-run1`).
- Related: plans 66, 67; `CONSULT-2026-08-05-CALLER-ENUM-REGRESSION.md`.
