# 59 — LLM Verdict Reproducibility (Correct the Anchor, Bound the Rest)

**Status:** SKELETON — NOT STARTED. Phase 0 (ratify the corrected framing) is the gate. No code beyond Phase 1's documentation fix.
**Type:** MOSTLY DECISION / DOCUMENT plan — NOT a "make the LLM deterministic" plan. Read the honesty framing before scoping any build.
**Branch:** `develop-2.0-init`.
**Created:** 2026-07-10, seeded from an enterprise-readiness gap analysis (part of the 57–61 batch).
**Rewritten:** 2026-07-14 to target the real, code-grounded problem. The original plan anchored reproducibility in a "human-owned `/verify` verdict" that the code proves does not exist; the rewrite retracts that anchor and re-points every phase at the genuine gap.

---

## Problem

The framework reasons about reproducibility using an anchor it does **not** actually have.

The original framing of this plan (and, by extension, the way the framework talks about its own gates) asserted that reproducibility is *"anchored in the human + mechanical layer — the human-owned verdict (plan 17/22)."* Reading the code proves that claim is **false for `/verify`** — the one command whose verdict matters most, because it is the gate that transitions a feature to `Complete`.

Three verified facts (see the verified-facts section below for citations):

1. `/verify`'s verdict is **machine-final and auto-acting**. `compute-verdict` deterministically emits APPROVED / NEEDS WORK / REJECTED, and on APPROVED the command **automatically** flips `spec.md` `**Status**:` → `Complete` and ticks the passed AC boxes. There is **no human re-gate at `/verify`** before that flip.
2. The verdict is produced by a **pure function** (`compute_verdict`, `_verify/_verdict.py`). Same inputs → identical output, bit-for-bit. This is a genuine, auditable reproducible anchor — but it is currently **undocumented**.
3. The verdict's **inputs are non-deterministic**: it consumes the LLM finder+refutation ensemble output from `/review` and the ac-verifier agent output. A run that surfaces a Critical/High finding and a run that does not will flip the verdict **category** (APPROVED ↔ NEEDS WORK) through the perfectly-pure function — and at `/verify` nothing human catches that flip before the spec auto-flips to `Complete`.

So the real gap is twofold: the framework advertises a reproducibility anchor it lacks (a human `/verify` verdict), while the anchor it actually has (`compute-verdict`'s provable purity) is undocumented, and the residual risk that anchor cannot cover — non-deterministic LLM findings flipping the verdict *category* at the one gate that auto-acts — is unmeasured.

## The honesty framing (read before scoping)

**Do NOT set the goal as "make LLM verdicts deterministic." That goal is unachievable and pursuing it burns effort.** No amount of engineering makes an LLM finder ensemble bit-reproducible. This instinct — inherited unchanged from the original plan — is correct and stays.

The achievable, defensible goals are:

1. **Correct the false anchor claim (do-now).** Stop asserting a human owns the `/verify` verdict. State the accurate anchor: the verdict FUNCTION is deterministic and auditable (`compute-verdict`); its INPUTS are advisory and bounded (refutation / cross-examination); and the reproducible HUMAN checkpoint is **upstream** at `/implement`'s per-task gate (plan 17), not at `/verify`.
2. **Document the true anchor.** `compute-verdict`'s purity is a strong reproducibility position that already exists in the architecture — it is just undocumented. Write it down honestly.
3. **Measure the residual risk.** Quantify whether the verdict *category* actually flips on identical input at `/verify`. This is the open empirical question the framing turns on.
4. **Disclose, don't hide.** Enterprise trust comes from honest characterization ("the AI panel is advisory and bounded; the gating verdict function is deterministic; the reproducible human checkpoint is upstream at `/implement`, here is the measured category-level variance"), not a determinism claim a CISO will catch and then distrust everything.

Only **reduce** the variance if measurement (goal 3) proves the category actually flips. Do not pre-build reduction.

## Why it matters (enterprise)

- A false "a human owns the verdict" claim, once caught against the code, poisons trust in every other (true) claim the framework makes.
- Auditors accept "advisory + bounded AI panel → deterministic verdict function → reproducible human checkpoint upstream." They reject "AI decides, trust it" — and they equally reject a stated human gate that does not exist.
- Knowing the measured category-level variance lets an org set policy (e.g. "verdict-gating Critical/High findings require a higher refutation quorum") — but only if the measurement shows the category is actually unstable.

## Verified facts (ground truth — cited so every claim is checkable)

These were confirmed against the code on 2026-07-14. They are the basis for the retraction; a future session should re-read the cited lines rather than re-litigate the facts.

- **`compute_verdict` is a PURE function.** `src/devforge/lib/_verify/_verdict.py` (482 lines). Its only imports are `from __future__ import annotations` (`:106`) and `from typing import Dict, List, Optional` (`:108`). The function signature (`:177`–`:184`) takes six arguments — `ac_results`, `mechanical_status`, `review_findings`, `hygiene`, `ac_verification_mode`, `regression=None` — and its body is list comprehensions + `if` branches returning `{verdict, reasons, blockers}`. No `random`/`datetime` usage is possible (both unimported — see `:106`/`:108`); a full-body read (all 482 lines, 2026-07-14) additionally confirms no file I/O, no network calls, and no `global` statement. Same inputs → identical output, bit-for-bit. **This IS the reproducible anchor.**
- **`/verify`'s verdict is MACHINE-FINAL and AUTO-ACTS.** `src/commands/verify/main.md:387` — *"`/verify` OWNS the verdict … via the deterministic `compute-verdict` verb."* `:269` — `compute-verdict` (PHASE 5) computes APPROVED / NEEDS WORK / REJECTED deterministically. `:25` — on APPROVED, PHASE 6 **automatically** flips `spec.md` `**Status**:` → `Complete` and ticks passed AC boxes; there is no user-approval step gating this flip. (PHASE 9 lets the user *elect which bugs to file* on NEEDS WORK — that is a bug-filing choice, NOT a verdict re-gate.)
- **The verdict's INPUTS are non-deterministic.** `compute-verdict` reads `review.json` (the LLM finder + refutation ensemble output from `/review`) and `ac-results.json` (ac-verifier agent output) from the run's `${TMPDIR:-/tmp}/forge-verify` scratch dir (`verify/main.md:265`–`:266`). These are LLM-driven and vary run-to-run.
- **The real human gates are UPSTREAM, not at `/verify`.** `/implement` PHASE 7 (per-task: the human approves the ready diff before commit — plan 17), `/grill` PHASE 7 (the user owns the disposition), and the `/breakdown` approval gate. The original plan's "plan 17/22 human-owned verdict" citation is wrong to lean on for `/verify`: plan 17's gate is `/implement`, and plan 22 (`/verify`) is machine-final.

## Open questions

- OQ-1: **RESOLVED** — `compute_verdict` IS pure (verified 2026-07-14; `_verify/_verdict.py`, imports `__future__` + `typing` only). The reproducibility story is therefore "the verdict FUNCTION is deterministic; its INPUTS are advisory + bounded" — a strong position needing little build. This resolution is the pivot the whole rewrite turns on; do not re-open it.
- OQ-2 (**new, the crux**): Does the verdict **category** (APPROVED / NEEDS WORK / REJECTED) actually flip on identical input at `/verify` across N runs? Phase 2 answers this. Prose variance is expected and irrelevant; *category* flips are what would matter.
- OQ-3: How to MEASURE the variance? (Run the same feature through `/review` N times, diff the finding sets and the resulting verdict categories — a maintainer-side test harness, not a shipped product feature.)
- OQ-4: What is the disclosure artifact — a doc section, a per-run "panel confidence" note in `verification.md`, or both?
- OQ-5: IF (and only if) Phase 2 shows category flips, which reduction knob — raise the refutation quorum for verdict-gating (Critical/High) findings, or route a category-unstable feature to the `/implement` human gate? Conditional on Phase 2; do not decide it early.

## Phase skeleton (draft — refine wording in Phase 0)

- **Phase 0 — ratify + retract (the gate, no code).** Adopt the corrected problem framing. Record the three verified facts (`compute_verdict` pure; `/verify` machine-final auto-flip with no human re-gate; inputs non-deterministic). **Explicitly retract** the "human owns the `/verify` verdict" claim. Maintainer sign-off before any build.
- **Phase 1 — correct the false claim (DOCUMENTATION — the one do-now deliverable).** Grep for every place the framework asserts or implies a human owns the `/verify` verdict, and fix each to state the accurate anchor: the verdict FUNCTION is deterministic + auditable (`compute-verdict`), its INPUTS are advisory + bounded (refutation / cross-examination), and the reproducible HUMAN checkpoint is UPSTREAM at `/implement`'s per-task gate — not at `/verify`. **The specific file list is a Phase-1 discovery task** — a future session must grep; this plan does not pre-assert which files carry the mis-claim. Any edit that lands in a file shipping into `.claude/` routes through instruction-author → instruction-reviewer + claude-code-guide.
- **Phase 2 — measure (diagnostic harness, maintainer-side `scripts/`).** Quantify category-level verdict variance at `/verify` (and finding-set variance at `/review`) on identical input across N runs. Answers OQ-2. Not shipped to consumers.
- **Phase 3 — reduce (CONDITIONAL — only if Phase 2 shows category flips; do NOT pre-build).** Candidate knobs (speculative until measured): raise the refutation quorum for verdict-gating Critical/High findings; or route a feature whose verdict category is unstable to the `/implement` human gate. Left deliberately unscoped.
- **Phase 4 — disclose (SHELVED per the plan-48 precedent, alongside Phases 2–3 — build only once Phase 2 exists and justifies it).** The honest characterization (a doc section and/or a per-run "panel confidence" note in `verification.md`), built on the CORRECTED anchor from Phase 1 — never on the retracted "human owns the verdict" claim.

## Decisions to ratify (Phase 0)

- D1: Adopt the corrected problem (false-anchor + unmeasured category-variance). **Reject** "make it deterministic."
- D2: `compute-verdict` purity confirmed → it IS the reproducible anchor (documented in Phase 1). This replaces the original D2's role.
- D3: **Retract** the "human-owned `/verify` verdict" framing. The reproducible human anchor is `/implement` upstream (plan 17); `/verify` is machine-final (plan 22).
- D4: Measure-only vs measure+reduce ambition — **default measure-only** until Phase 2 justifies reduction.
- D5: Disclosure form (doc section vs per-run `verification.md` note vs both) — decided after Phase 2.

## Dependencies + related

- **Plan 48 (`48-REVIEW-MANDATORY-GATE-PLAN.md`) — the governing precedent. SHELVED 2026-06-30** because it was structural-and-theoretical, NOT a reproduced incident. **Plan 59 is the same category** — a self-generated enterprise hypothetical (the 57–61 gap analysis), with no observed category-flip incident. **Adopt the plan-48 precedent explicitly:** build only **Phase 1** (the do-now doc correction — it fixes a *real present inaccuracy in the code's own claims*, which plan 48 did not have), and **shelve Phases 2 / 3 / 4** until a real consumer need or an *observed* verdict-category flip justifies them. This is the single most important cross-plan alignment for this plan.
- **Plan 19 — the existing variance-BOUNDING machinery on `/verify`'s input path.** Plan 19's refutation / cross-examination (`_shared/_verify`, reused by `/review`), its confidence tiers, and the `[CONTESTED]` high-stakes surfacing already dampen the INPUT variance that feeds `compute-verdict` (via `review.json`). Cite this as what already bounds the non-determinism — Phase 1 documents it as the "bounded inputs" half of the anchor story. **Plan 12's multi-pass union (`_merge`) does NOT belong here:** it lives only at `_audit/_merge.py`, was never extracted to `_shared/`, and touches neither `/review` nor `/verify` (a flag-scoped grep — `--passes` / `merge-passes` / `pass_count` / `MULTI-PASS` — over `src/commands/review/main.md` returns zero; the bare word "passes" appears only as the ordinary English verb). Cite plan 12 only as a *precedent for the general technique*, never as machinery already active on `/verify`'s inputs.
- **Plan 17 — the TRUE upstream human anchor.** `/implement` PHASE 7's per-task human approval of the ready diff before commit. This is the reproducible human checkpoint Phase 1 re-points to (the retracted claim mis-attributed it to `/verify`).
- **Plan 22 — the `/verify` redesign** that made the verdict machine-final (deterministic `compute-verdict`, auto-flip on APPROVED). Cite with the CORRECTED role: `/verify` owns the verdict *mechanically*, not via a human gate.
- **Plan 58 (audit trail)** — a per-run panel-confidence disclosure note (Phase 4) is also audit evidence; the two disclosure surfaces should agree. **Note:** plan 58 independently carries the SAME retracted "human-owned `/verify` verdict" claim at its own lines 24 / 31 / 46 (its "Believed current state" + OQ-3). Phase 1's grep sweep MUST include and correct `58-COMPLIANCE-AUDIT-TRAIL-PLAN.md`, not just shipped spec/doc files — otherwise the false anchor survives in a sibling plan a maintainer is likely to open next.
- **Batch provenance:** part of the 57–61 enterprise-readiness batch, seeded from an enterprise-readiness gap analysis.

## Context for next session

**This is the smallest build of the five and the most important to get the FRAMING right — and the framing was WRONG in the original draft.** The original leaned on a "human-owned `/verify` verdict" that the code disproves. The rewrite's Phase 1 (documentation) is the only do-now work: it corrects a *real, present* inaccuracy in how the framework describes its own gate, and documents the *real* anchor (`compute-verdict`'s purity + bounded advisory inputs + the upstream `/implement` human gate).

Everything past Phase 1 is **shelved per the plan-48 precedent** — build it only when a real consumer need or an *observed* verdict-category flip appears. The temptation is still to over-engineer toward determinism or to pre-build the measurement harness; resist both. The measurement (Phase 2) becomes real only if someone reports, or a maintainer observes, a category flip on identical input — which is exactly the OQ-2 question. Don't pre-build Phase 3.

## When resuming work

1. Read this file, especially the "honesty framing" and "verified facts" sections — the retraction is the whole point.
2. First real task (Phase 1): grep the repo for any assertion that a human owns / gates the `/verify` verdict, and rewrite each to the corrected anchor (deterministic `compute-verdict` function + bounded advisory inputs + upstream `/implement` human checkpoint). Do NOT assume a file list — discover it by grep.
3. Stop after Phase 1 unless a real consumer need or an observed category-flip justifies Phases 2–4 (plan-48 precedent).

## Verify

- Phase 0 done = corrected framing adopted, the three verified facts recorded, the "human owns the `/verify` verdict" claim explicitly retracted, ambition ratified (default measure-only).
- Phase 1 done = every framework assertion of a human-owned `/verify` verdict corrected to the true anchor; `compute-verdict`'s purity documented; grep for the retracted claim returns zero live assertions.
- Plan done (Phase 1 only, per plan-48 precedent) = the false anchor is gone and the true anchor is documented. Phases 2–4 remain shelved until a real consumer need or an observed verdict-category flip revives them.
