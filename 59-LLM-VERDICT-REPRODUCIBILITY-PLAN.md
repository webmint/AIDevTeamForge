# 59 — LLM Verdict Reproducibility (Bound, Not Eliminate)

**Status:** SKELETON — NOT STARTED. Phase 0 (investigation + ratify) is the gate. No code.
**Type:** MOSTLY DECISION / DOCUMENT plan — NOT a "make the LLM deterministic" plan. Read the honesty framing before scoping any build.
**Branch:** `develop-2.0-init`.
**Created:** 2026-07-10, seeded from an enterprise-readiness gap analysis (this session).

---

## Problem

The framework splits enforcement: a **mechanical slice** (forcing-function verbs — deterministic, bit-reproducible) and a **judgment slice** (`/audit`, `/review`, `/grill`, `/verify`'s finder+refutation ensembles — LLM-driven). The mechanical slice answers "same input → same output." The judgment slice does NOT: an LLM ensemble can return different findings/verdicts on identical input across runs.

An enterprise CISO asks: *"same PR, same gate — same verdict every time?"* For the judgment slice the honest answer is **no**, and no amount of engineering makes an LLM ensemble bit-reproducible.

## The honesty framing (read before scoping)

**Do NOT set the goal as "make LLM verdicts deterministic." That goal is unachievable and pursuing it burns effort.** The achievable, defensible goals are:

1. **Bound the variance** — measure it, cap it, make it small enough that verdict *category* (APPROVED/NEEDS-WORK/REJECTED; confirmed/dismissed) is stable even if prose differs.
2. **Anchor reproducibility in the human + mechanical layer** — the human-owned verdict (plan 17/22) and the mechanical gates ARE reproducible/attributable. The LLM ensemble is an *advisory input* to a reproducible human decision, not the decision.
3. **Disclose, don't hide** — enterprise trust comes from honest characterization ("the AI panel is advisory; the gating verdict is mechanical + human, here's the measured panel variance"), not a false determinism claim a CISO will catch and then distrust everything.

The existing design already leans this way (multi-pass union, refutation, human-owns-verdict at the end). This plan makes that stance **explicit, measured, and defensible** rather than implicit.

## Why it matters (enterprise)

- A false "it's deterministic" claim, once caught, poisons trust in every other (true) claim.
- Auditors accept "advisory AI + deterministic gate + attributed human sign-off." They reject "AI decides, trust it."
- Knowing the measured variance lets the org set policy (e.g. "high-stakes findings require 2/3 refutation agreement" — which the framework partly does already).

## Believed current state — VERIFY in Phase 0

- [ ] Confirm human-verdict ownership points are real gates, not advisory: `/implement` PHASE 7, `/verify` `compute-verdict`, `/grill` PHASE 7, `/breakdown` approval.
- [ ] Confirm the variance-dampening mechanisms already shipped: `/audit` `--passes` multi-pass union (`_merge`), refutation/cross-examination (`_shared/_verify`), confidence tiers, `[CONTESTED]` high-stakes surfacing.
- [ ] Confirm `compute-verdict` (`_verify/_verdict.py`) is DETERMINISTIC given its inputs — i.e. the non-determinism is upstream (finder/refuter outputs), the verdict *function* is pure. This is the crux: if true, the reproducible anchor already exists.
- [ ] Confirm whether any temperature/seed control is available in the agent-dispatch layer (likely not exposed — verify).

## Open questions

- OQ-1: Is `compute-verdict` provably pure (deterministic given `review.md` + AC results + hygiene)? If yes, the reproducibility story is "the verdict FUNCTION is deterministic; its INPUTS are advisory + bounded" — a strong position needing little build.
- OQ-2: How to MEASURE panel variance? (Run the same feature through `/review` N times, diff findings — a test harness, not a product feature.)
- OQ-3: Is any variance-reduction knob worth adding (seed pinning if the SDK exposes it; higher refutation quorum for gating findings)? Or is measurement + disclosure enough?
- OQ-4: What's the disclosure artifact — a doc section? a per-run "panel confidence" note in `verification.md`?

## Phase skeleton (draft — refine in Phase 0)

- **Phase 0** — Establish the honest goal (bound+anchor+disclose, NOT determinism). Verify `compute-verdict` purity (OQ-1). Ratify how far to go (measure-only vs measure+reduce). Maintainer sign-off.
- **Phase 1 (measure)** — A variance-measurement harness: same input, N runs, quantify finding/verdict stability. This is diagnostic, likely `scripts/`-side (maintainer tooling), not shipped to consumers.
- **Phase 2 (anchor — likely doc-only)** — Document the reproducibility architecture: mechanical+human verdict is the anchor; LLM panel is bounded advisory. Reconcile `src/CLAUDE.md` + a design doc.
- **Phase 3 (reduce — CONDITIONAL, only if Phase 1 shows unacceptable variance)** — Add a variance-reduction knob (quorum bump / seed pin). Do NOT build speculatively.
- **Phase 4 (disclose)** — A per-run panel-confidence disclosure in the verdict output, if Phase 0 rules it worth it.

## Decisions to ratify (Phase 0)

- D1: Adopt the bound+anchor+disclose goal explicitly (reject "make it deterministic").
- D2: `compute-verdict` purity confirmed → reproducible-anchor claim is valid.
- D3: Measure-only vs measure+reduce ambition.
- D4: Disclosure form.

## Dependencies + related

- Related: plan 58 (audit trail) — the disclosure/panel-confidence note is evidence too.
- Related: plans 12 / 19 (multi-pass + refutation precision) — the existing variance-dampening machinery this plan characterizes.
- Related: plan 17 / 22 (human-owned verdicts) — the reproducible anchor.

## Context for next session

**This is probably the smallest build of the five and the most important to get the FRAMING right.** The temptation is to over-engineer toward determinism. Resist it. The likely outcome: OQ-1 confirms `compute-verdict` is already a pure function of advisory-but-bounded inputs + a human gate — meaning the strong reproducibility story already exists in the architecture and this plan is mostly *measuring the variance and writing the honest disclosure*. If Phase 1 measurement shows category-level verdict flips on identical input, THEN Phase 3 reduction becomes real. Don't pre-build Phase 3.

## When resuming work

1. Read this file + the "honesty framing" section twice — it's the whole point.
2. First real task: verify OQ-1 (`compute-verdict` purity). Read `_verify/_verdict.py`. If pure, most of the anchor story is already true.
3. Build the measurement harness (Phase 1) before deciding whether any reduction (Phase 3) is warranted.

## Verify

- Phase 0 done = honest goal adopted, `compute-verdict` purity determined, ambition ratified.
- Plan done = measured panel variance documented + a defensible, honest reproducibility statement shipped; reduction built ONLY if measurement justified it.
