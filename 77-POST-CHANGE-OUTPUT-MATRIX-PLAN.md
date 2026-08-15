# 77 — Post-Change Output Matrix: closing the discovery→action gap

**Status:** **DONE (build) 2026-08-15** — Phase 0 is RATIFIED, Phase 2 SHIPPED instruction-only into `src/`, and Phases 1 and 3 are **WAIVED — not deferred; they will not run** — so this mechanism is build-verified and NOT consumer-validated, and the original 2026-08-12 status text that follows on this line is retained unedited as a dated record, not a live claim (see the dated lines below and *Amendment 2026-08-15 (second)*). No code, no `src/` edit, no `main.md` edit, no `src/agents/` edit has been made for this plan. Every decision below is a recommendation carrying its counter-argument.
**2026-08-13 amendment:** maintainer pre-ratification inputs **R1–R3** and one recorded follow-on are recorded in *Amendment 2026-08-13* below; they decide the production stage, the acceptance criteria and one added rule. **Phase 0 is still required** for D1–D6 and OQ-1–OQ-6 **as amended**. Still NOT STARTED: no `src/` file has been edited, and none may be before Phase 1 runs.
**2026-08-15 amendment:** a pre-implementation verification pass against the working tree **falsified R1's carrier** — `research-report.md` is helper-composed and LLM-uneditable, so a required section of it cannot be instruction-only. The **sibling-file replacement (`specs/<dirname>/emission-matrix.md`) is ratified 2026-08-15**; five further findings, **A2–A6**, are recorded corrections that go to **Phase 0** with everything else. See *Amendment 2026-08-15* below. **Still NOT STARTED: no `src/` file has been edited.**
**2026-08-15, second amendment — the plan's state CHANGES:** **Phase 0 is RATIFIED**, **Phases 1 and 3 are WAIVED** by the maintainer — not deferred, and they will not run — and **Phase 2 has SHIPPED into `src/`**. **This plan is no longer NOT STARTED**; `src/` files HAVE been edited; the **Type** line's two measurement arms are gone, so this is a BUILD plan with no measurement. Every sentence above asserting that no `src/` file has been edited, and the Status line's own NOT STARTED, are **dated and superseded on those points** — the residual line-3 text following the new Status marker, and every other such sentence above, are retained unedited per this file's annotate-don't-swap convention, while the leading NOT STARTED marker itself was **replaced** rather than annotated: the one deliberate exception to that convention, taken because a stale leading Status marker misinforms every reader before reaching this correction, and it is **not** to be restored. See *Amendment 2026-08-15 (second)* below.
**Type:** DESIGN + BUILD plan, with a **measurement arm that gates the build** (Phase 1) and a **measurement arm that decides whether the build survives** (Phase 3). The phase order is deliberately inverted relative to this repo's norm — see D5.
**Branch:** `develop-2.0-init`
**Created:** 2026-08-12.
**Privacy constraint governing this file:** the originating evidence is a benchmark against a private client codebase. This file is **mechanism-only**. It contains no ticket ID, commit SHA, branch name, company or product name, feature name, source symbol, function name, parameter name, component name, file path or enum value from that codebase, and none may be added. Where an example is needed, it is invented and neutral. `CHANGELOG.md:32` records that plan docs are exempt from the identifier scrub; that exemption covers pre-existing historical references in other files and licenses nothing new here. Any identifier introduced into this file is a hard error, not a style nit.
**Evidence provenance (added 2026-08-13):** the amendment section below restates a maintainer-delivered handoff document, `77-EVIDENCE-DISCOVERY-TO-LOCK-INVERSION.md` (present at repo root, verified 2026-08-13). **That file is UNTRACKED, it carries private-client identifiers, and it must never be quoted, excerpted, or committed into this file or any other tracked file** — it stays untracked for the same reason plans 73, 74 and 75 do, and it is cited here by filename only. Everything the amendment restates from it is sanitized; where a fact cannot be stated without an identifier, it is not stated rather than paraphrased around.

---

## Why 77 and not 76

`ls [0-9]*-*.md` at repo root returns files up to **75**; no `76-*` file exists. The number 76 is nevertheless **occupied as an identity**: repo-root `CLAUDE.md` carries an index entry labelled `76 — UNDRAFTED FINDING: the intake rubrics' blanket escape flag`, whose own text reads "NO `76-*-PLAN.md` FILE EXISTS at repo root — do not grep for one." Creating `76-POST-CHANGE-OUTPUT-MATRIX-PLAN.md` would make that sentence mechanically false and would make a grep for `76-*-PLAN.md` return a file about an unrelated subject — and this plan is scoped to exactly one new file, so it cannot repair the index entry in the same change. 77 is therefore the first number that is free in both senses. If the maintainer prefers 76, the fix is a `git mv` plus an edit to that index entry, in that order.

---

## The problem — measured, not theorized

### The benchmark result

Ten runs, four harnesses, one brownfield maintenance ticket. The ticket's defining property: **a shared function had a second consumer that no obvious reading of the ticket surfaces** — a hidden coupling. Two probes were scored independently: did the run **discover** the coupling, and did the run's change **handle** the hidden surface correctly.

| Arm | Runs | Discovery | Handling |
|---|---|---|---|
| Three competing harnesses (3 runs each) | 9 | **0/9** | **0/9** |
| This framework, v1.28 (shipped on `main`) | 2 | **2/2** | **0/2** |
| A reference run using the same commands | 1 | pass | pass |

**So this framework is the only harness that finds the hidden coupling, and it still designs as if it hadn't.** That sentence is the entire opportunity and the plan is built on it exactly as written: **the gap is discovery→action, not discovery.** Any phase that proposes to improve discovery is out of scope by construction — discovery already scores 2/2 and there is no headroom there.

**[Amended 2026-08-13 — see *Amendment 2026-08-13* → *A fuller evidence set*.]** The table above stands as recorded and no figure in it is withdrawn. A larger sample of the same frozen ticket — **16 runs across 6 harnesses** — is recorded in the amendment below, together with the mechanism behind the handling column, the ordering of the harmful artifacts it produced, and the null results that bound what any fix here may claim. The two records are **not** re-mapped run by run.

### The universal reflex

Nine of the ten runs solved "stop emitting some values for one caller of a shared function" the same way: **add an optional flag parameter to the callee and pass it from the one caller they knew about.** Two independent competing harnesses converged on the same parameter name.

The reference run did something structurally different: it **keyed the guard on a state value the function already receives** — a value the function already computed a few lines below the guard site.

The difference is not stylistic. An opt-in flag covers only the call sites someone enumerated. A guard keyed on already-received state covers **every** caller, including the ones nobody found. That single difference produced the entire probe result.

### Why a taste instruction would NOT have worked — load-bearing, do not soften

The losing runs did not fail to *consider* the intrinsic approach. One of them **explicitly rejected it**, in a single line of its plan's Alternatives Rejected section, on the grounds that generalizing a particular flag was impossible because one code path passes an undefined value.

That claim was **true of the symbol it named and irrelevant to the approach that actually works** — the state value the winning design keyed on takes different inputs entirely, and the losing plan never mentioned it.

The lesson generalizes past this incident: **a preference instruction dies against one confident, unfalsifiable sentence.** A rejection that costs one line to write and cannot be checked will be written whenever it is convenient. So the requirement this plan imposes is not that the intrinsic form be *preferred*. It is that **a rejection be checkable** — rule 5 below.

### Why MORE RULES and MORE ARTIFACTS would not have worked either

One competing harness produced **nine planning artifacts per run** and found the coupling **zero times in three runs**, on the same underlying model. Volume was not the constraint.

Worse, two rules that already existed were satisfied by compliant-looking sentences that **inverted their own purpose**:

- one run cited a section as proof that all consumers had been verified — where that section was titled as a list of consumers that must NOT change;
- another filed a backward-compatibility observation ("the new parameters are optional, so no consumer needs updating") as **impact analysis**.

Both sentences pass a reader who is checking that the rule was answered. Both are the opposite of the analysis the rule exists to force.

### The bar — a named, quotable criterion

Every rule this plan proposes, and every rule any successor plan proposes in this area, must clear this:

> **The visibility bar: does the rule produce an artifact that is visibly wrong when the analysis wasn't done?**

Two candidate rules that FAIL it, recorded so they are not re-proposed:

- **"Enumerate the consumers."** A list of consumers that must not change satisfies it. So does a list of the consumers you already knew about. Nothing in the artifact reads wrong.
- **"Count for completeness"** — require the row count to equal the call-site count. A matrix with every row marked "live" passes the count and hides the defect perfectly. Completeness of *rows* is not completeness of *analysis*.

The matrix's **filled rows** clear the bar for one specific reason: **a wrongly-filled row reads wrong on its face.** A row that says an unintended caller still emits the value being removed does not need a design principle to look wrong to a human reading the approval gate.

**That defence covers row CONTENT, not row PRESENCE**, and the distinction is not decorative: rules 2, 3 and 5 below clear the bar on content grounds, and **rule 1 does not**. Rule 1 is the enumeration floor those rules stand on — strictly better than no enumeration, and not self-verifying. Its bound is stated with the rules below and must not be read as covered by this paragraph.

---

## Amendment 2026-08-13 — maintainer pre-ratification inputs (R1–R3) and a fuller evidence set

**What this section is.** Three maintainer inputs — **R1**, **R2**, **R3** — ratified 2026-08-13 ahead of Phase 0; one follow-on recorded as deliberately out of scope; and a larger evidence set for the Problem section above. **Nothing above or below is withdrawn, reworded or renumbered.** Each section these inputs amend carries a one-line pointer back here.

**What this section is NOT.** It is not Phase 0. R1–R3 decide the production stage, the acceptance criteria and one added rule; **D2, D3, D5, D6, OQ-2, OQ-5, OQ-6 and the rest of D1 remain unratified**, and no `src/` file has been edited.

**Placement.** It sits after the Problem section because it supplies a larger evidence set for it, and before *The proposed change*, *Decisions*, *Open questions* and the phases because it amends all four.

### A fuller evidence set — 16 runs, 6 harnesses

A maintainer-delivered 2026-08-13 handoff reports the **same frozen brownfield ticket** at larger scale: **16 runs across 6 harnesses**. The ticket's property is unchanged from the Problem section — it removes some emitted values from one named surface, a second and unnamed surface reaches the same shared builder, and a frozen probe asserts the second surface stops emitting the removed values.

- **Discovery.** Competing harnesses named the hidden surface's file in **1/10 runs**, and that single hit was one passing mention. This framework's v1 named it in **6/6**.
- **Handling.** **5 of 6** v1 runs then produced *actively harmful* lock artifacts. In ascending order of harm: (1) an "explicitly NOT modified" list containing the hidden surface's exact file; (2) a hard spec constraint forbidding the one discriminator that would have covered both surfaces; (3) an acceptance criterion asserting the removed values are still present on the hidden path; (4) a review whose top-priority action item was to **add** a spec pinning the removed values as still present.

**The framing this evidence adds, and the reason the amendment exists:**

> An unseen coupling is a bug someone finds later. A coupling that has been examined, named, constrained by a written rule, and covered by a passing regression test is a bug the audit trail has made permanent. The frameworks that never looked left the defect **discoverable**; v1 left it **defended**.

**The one passing run** made the same blast-radius finding as the others and framed it differently: *both paths need the change for consistent behavior*. It pre-empted the "that path is defensive-only in practice" objection and kept the path in scope, keyed the guard on a state value the shared function already receives, and **fixed the hidden surface without editing the hidden surface's file at all**.

**The mechanism, in one sentence:** v1's blast-radius analysis has exactly one exit — **protect** — and no path to **include**; "shared code" resolves to "risk" and never to "consistency".

**Null results, which bound what any fix here may claim:**

- Planning-artifact volume varied **24×** across runs with **zero** effect on the probe.
- Test volume varied **14×** with **zero** effect.
- Investigation depth **inverted** the expected relationship — deeper investigation produced the harm escalation, not the fix.
- **15/16** runs added a caller-side opt-out parameter to the shared function.
- The **only** axis that predicted the probe outcome was **guard shape**, reported at **17/17**.

**Counts caveat — read the mechanism, not the arithmetic.** The **arm** totals reconcile — 10 competitor runs plus 6 v1 runs is the 16 — and the repo-root `CLAUDE.md` index entry for this plan records that reading. Two finer figures do not: the per-**harness** split as delivered does not sum to those arm totals, and guard shape is reported at **17/17** against a 16-run total. Neither is reconciled here and neither is invented around, so the composition is restated only at the level that is unambiguous — competing harnesses run one to three times each, this framework's v1 run six times across two template sets. **Treat every per-run count in this subsection as approximate.** The mechanism findings — the single exit, the lock-artifact ordering, the passing run's guard shape — are the load-bearing content and none of them depends on an exact denominator.

**A known internal tension, recorded rather than smoothed.** The handoff's own summary table scores this framework "fixed: 0/6" while its mechanism section describes one of those six runs as passing. The maintainer was asked and did not resolve it. The full form of the tension is recorded in the untracked evidence file; it is not resolved here, and no figure above is adjusted to conceal it.

**Relationship to the Problem section's table — NOT re-mapped run by run.** That table records ten runs across four harnesses; this is a larger sample of the same ticket. The repo-root `CLAUDE.md` index entry for this plan records the reconciliation as an **enlargement of the same arms** — 2 v1 runs → 6, 9 competitor runs → 10 — and records one wording difference that matters: the newer figures are stated in terms of **naming the hidden surface's file**, which is not word-for-word the earlier probe's *discovering the hidden coupling*. That difference is the likeliest reason the competitor arm reads 0/9 there and 1/10 here on one passing mention. **It is not resolved in this file, and neither figure is withdrawn** — a session needing the exact run-by-run mapping goes to the untracked handoff, not to this file and not to the index.

**What the larger set changes above, and what it does not.** It strengthens *Why a taste instruction would NOT have worked* and *Why MORE RULES and MORE ARTIFACTS would not have worked either* — the volume null results reproduce at larger scale, and the harm ordering shows the failure is not merely inaction. It **does not** change the visibility bar, the artifact's shape, or the non-goal on discovery: discovery scores 6/6 here, which is the same finding with a bigger denominator.

### R1 — Production stage moves to `/devforge:research` (RATIFIED 2026-08-13)

**The matrix is produced at `/devforge:research`, not at `/devforge:plan`.**

**Why.** `/devforge:specify` writes acceptance criteria, so a matrix produced at `/devforge:plan` arrives **after** the lock artifact can already have been written — harm artifact (3) is an AC. Two supporting facts:

- **(a) The lock artifacts in the evidence are research-time and spec-time artifacts, not plan-time ones.** A mechanism landing downstream of them is measured against a decision already recorded.
- **(b) The row source is native to `/devforge:research`.** The plan-67/69 caller-enumeration machinery already lives there — `record-fix-path-helper`, `record-inbound-caller`, `classify-caller-scope` and `declare-caller-total` are all invoked from `src/commands/research/main.md` (verified 2026-08-13 by grep of that file), all mode-independent since plan 67. And `/devforge:research` already produces a **recommended approach** (`set-recommended-approach`, same file), which is the "proposed change" the matrix's *emits after the change* column is evaluated against. Nothing new has to be paid for to fill the rows.

*Counter-argument, recorded:* this plan's most-verified section is *Verified state*, and every anchor in it is at `/devforge:plan`. R1 moves production to a site this file has verified almost nothing about, so the plan's evidentiary base now covers the consumption half and not the production half — a real, knowingly-accepted cost, flagged in that section and paid at drafting time by reading `src/commands/research/main.md` first. *A second counter:* a matrix produced at research is produced against the recommended approach, and the approach can change at `/devforge:plan`, so a carried matrix can go stale. The mitigation is the consumption role below — sub-question 7's already-mandated fresh inbound trace is what re-checks it — and that mitigation is an instruction, not a check.

**Four consequences, each annotated on the section it affects:**

1. **OQ-1 is SUPERSEDED IN FRAME, not answered.** It asked which `/devforge:plan` sub-question hosts the matrix; that question no longer has a subject. New frame: the production home is `/devforge:research`'s recommended-approach phase, and **the trigger stays fact-keyed** — "the recommended approach removes or suppresses an emitted value". OQ-1's belief-vs-fact argument is **not** withdrawn: it survives intact and now supports the research-side trigger, since a trigger keyed on a property of the change is exactly what does not depend on the author's belief about caller count.
2. **`/devforge:plan` becomes CONSUMER and VERIFIER.** Sub-question 7's already-mandated fresh inbound trace verifies the carried matrix is still current, and the matrix's `dead` rows populate sub-question 9's `### Change-Induced Dead Code` table. **D2(b)'s transform analysis stands unchanged** — it now reads from a carried matrix instead of a locally-authored one. **D2 and D3 remain Phase-0 ratification items**, with their existing analysis intact on the consumption side.
   **[Amended 2026-08-15 — see Amendment A3.]** Both clauses are corrected: the matrix carries no `dead` rows — it supplies the `affected` set sub-question 9 must account for — and D2(b)'s transform analysis does **not** stand unchanged, because there is no row-to-row transform left to perform. The verification half of this consequence is unaffected.
3. **The OQ-3 / D4 interlock resolves in favour of cheap deletion.** The carrier is a **required section of `research-report.md`** — a document artifact inside the feature dir `/devforge:research` allocates at intake finalize (plan 68) — **read in place downstream**, following plan 53's park-once/read-in-place precedent. It is **not** a handoff schema field. `/devforge:specify` and `/devforge:plan` are directed to read that section, instruction-only. No Python, no schema change, no new verb; deletion stays a markdown revert, which is the property D4 and D6 both depend on. **OQ-3's existing counter carries over unchanged and is not softened by this resolution:** a document section is unverifiable downstream, and nothing mechanical prevents a short matrix.
   **[Amended 2026-08-15 — see Amendment A1.]** The `research-report.md` carrier named here is falsified; the matrix lands in a sibling file instead, and the interlock's substance is unchanged.
4. **Phase 2's file set re-scopes** to `src/commands/research/main.md` (production), `src/commands/specify/main.md` (R3's read directive), `src/commands/plan/main.md` (consumption, verification, dead-row population). Whether `src/agents/architect.md` still needs an edit is the drafting session's call, and would be consumption-side only. **The accumulation tripwire binds unchanged across every one of those files** — see *What this does to the accumulation tripwire* below.

**Phase 1 also gains a research-side item:** the baseline reading records whether the baseline run's research artifacts contain any emits-after-style analysis at all, and whether the hidden surface's classification survives from research into the plan — alongside the three plan-side facts Phase 1 already names.

**For a resuming session:** read `src/commands/research/main.md` in full before drafting Phase 2. This file names five verbs and one document from it and nothing else; that file's phase numbers, section names and rubric structure are **unverified here** and must not be guessed.

### R2 — Stricter acceptance criteria (RATIFIED 2026-08-13)

Amends the probes in *The measurement design*, Phase 1 and Phase 3. **Both arms are scored under these criteria**, or the before/after is not like-for-like.

**1. The handling probe passes only if the hidden surface stops emitting the removed values WITHOUT its file appearing in the diff.** Correct coverage is a predicate change inside the shared function, not a call-site sweep. This is the criterion the passing run met and the criterion the opt-out-parameter reflex structurally cannot meet.

**A named partial outcome: *discovered-and-swept*.** A run that fixes the hidden surface by editing that surface's file directly is recorded under this label. **It is not a pass.** The label exists so the result is described accurately in the record — **it is not a third path around D6**, and a session reading a swept result as a partial success is precisely the behaviour D6's counter-argument names.

*Counter-argument, recorded:* a diff-shaped criterion is a **proxy** for the design property and can be wrong in both directions. A legitimate design might touch the second surface's file for an unrelated reason (an import, a rename, a formatting pass), and a run could avoid that file while hard-coding a per-caller condition inside the shared function that is morally a sweep. The proxy is accepted because it is cheap, mechanical, and reads identically for both arms; it is read **alongside** the guard-shape observation, which this evidence set reports as the only predictive axis, and the partial label exists so a file-touching fix is recorded rather than forced into a binary it does not fit.

**2. A secondary signature check, on both arms.** Grep the run's own pipeline artifacts for **any assertion that a value the ticket removes is still present, or still emitted, on some path**. In the evidence, that assertion shape is the signature of the lock reflex — it is what harm artifacts (3) and (4) are made of. Its presence or absence is recorded whichever branch the arm lands in. It is an **observation, not a probe**: it does not by itself pass or fail an arm.

*Bound:* this check is stated as a shape rather than as a pattern, because no field name, symbol or literal from the source codebase exists in this file and none may be invented to make the grep look concrete. The session running it composes the pattern from the frozen ticket's own vocabulary at run time and does not write that pattern back into this file.

### R3 — Rule 6, derived exclusions (RATIFIED 2026-08-13)

**Added to D1's rule set. The set is now six rules; rules 1–5 are unchanged and unrenumbered.**

> **6. Derived exclusions.** Any "explicitly not modified" or out-of-scope entry for a **caller of the changed function** is valid **only** when that caller's matrix row shows the intersection of the values it still emits and the values the ticket removes is **empty**, stated in the row. A non-empty intersection **invalidates the entry** and escalates as a **product question**. It may not be resolved by inferring intent from the ticket's silence.

**Why it clears the visibility bar.** Like rules 2, 3 and 5, it clears on **content** grounds: a row declaring a caller out of scope while its own cells show that caller still emits a value being removed **reads wrong on its face**, with no design principle needed. It is aimed at harm artifact (1) — the "explicitly NOT modified" list naming the hidden surface — which the evidence ranks as the **lowest-harm** of the four and which is the first point at which the exclusion becomes written record. *No claim is made here that the other three were derived from it; the evidence orders them by harm, not by causation.*

**Companion `/devforge:specify` directive — same Phase-2 edit set, instruction-only.** When writing acceptance criteria, read the matrix section. **An AC asserting the continued presence of a value the ticket removes may not be written from inferred intent; it requires quoted product intent.** This is aimed at harm artifact (3).

**Explicitly out of scope: anything MECHANICAL for that class.** A solver check, a grep-shaped verifier, or any other automated detector of the inferred-intent AC is **not** in this plan. That possibility is recorded as a **file-less finding in repo-root `CLAUDE.md`**, not here, so this plan's measurement stays a measurement of one instruction-only mechanism.

**Artifact (2) is tracked as well, and deliberately not here.** The hard spec constraint forbidding the one discriminator that covered both surfaces is owned by a **second file-less finding in repo-root `CLAUDE.md`**, recorded 2026-08-13, whose subject is that *a hard constraint that eliminates a candidate discriminator is not required to record what that candidate would have achieved* — so the eliminated candidate leaves no trace a reviewer can weigh. Two things about it belong here and not only there. **First, it must not be folded into Phase 2**: that finding's own text says so, for this plan's reason — Phase 2 is measurement-locked, and a Phase 3 measuring two mechanisms attributes nothing. **Second, its caution is stated in this file's own vocabulary and should be read before anyone drafts it:** the naive form of that rule likely **fails the visibility bar**, because an absent or perfunctory cost note does not read wrong on its face — the same defect for which *The bar* records "enumerate the consumers" and a completeness count as rejected candidates.

**With that, every lock artifact in the evidence has a recorded owner:** **(1)** → rule 6 above; **(2)** → the hard-constraint file-less finding just named; **(3)** → the `/devforge:specify` directive above, with any mechanical detector for it carved out to its own file-less finding (recorded the same day, subject: *an AC that pins a value the same spec removes is a conflict flag, not a regression pin*); **(4)** → the *Recorded follow-on* below. **Only (1) and (3) are owned by this plan, and only in their instruction-only halves** — a reading of this amendment as covering the lock reflex end-to-end is wrong.

*Counter-argument, recorded:* rule 6 is the first rule binding the matrix to a document the matrix does not own — the out-of-scope list — and the companion directive is a **second command's edit** justified by one evidence class, which is exactly the shape the accumulation tripwire warns about. The defence is that both are single instruction-only sentences with no mechanism behind them, and that the tripwire's own test is *"Phase 3 cannot be read without it"*: three of the four lock artifacts are written at or after spec time, so a Phase 2 confined to the production site would be measured against the artifact that defeats it. That is a measurement justification rather than a completeness one — but it is an argument, and Phase 3 is what tests it.

### Recorded follow-on — the review-side question (NOT in scope; conditional on Phase 3 passing)

**The candidate:** one review-side question that reads the **emission matrix** rather than the ACs — the one question capable of invalidating an AC.

**Why it is a candidate at all:** the evidence shows this framework's review stage is **structurally unable** to catch this class, because it grades against the spec's ACs. It asks *"did we do what we said"* and never *"was the invariant right"*. Harm artifact (4) is that stage working correctly and producing the most harmful artifact in the set.

**Why it is EXCLUDED from Phase 2**, on two stated grounds:

1. **The plan's own non-goal** on the review/verify commands, which a good idea does not suspend.
2. **Measurement attribution.** A Phase 3 that measures two changes attributes nothing — the same reasoning that produced D5's baseline arm.

**If and only if Phase 3 passes**, this becomes a **separate plan with its own measurement**. It is recorded here so it is neither re-derived from scratch later nor quietly folded into Phase 2 now.

### OQ-4 — recorded input, and the decision not to edit `src/constitution.md` now

**The larger evidence set strengthens BOTH sides of OQ-4, and must not be reported as settling it.**

- **For "no constitution change" (OQ-4's recommendation):** the null results. Guidance volume and artifact volume had **zero** measured effect on the probe. A rule added to the constitution is guidance, and this set is the strongest evidence yet that guidance volume is not the constraint.
- **Sharpening the counter:** guard shape was the **only** predictive axis. The constitution's Narrowing rule **prefers** the caller-scoped opt-in — "a parameter, option, or wrapper the affected caller passes" (`src/constitution.md:122`, as quoted by the FALSE BINARY finding in repo-root `CLAUDE.md`) — and that is structurally the **opt-out-parameter shape 15/16 runs produced and the probe rejected**, while the intrinsic form that won sits in the disfavoured fallback arm at `:123`. So the rule may not merely fail to help; it may point at the losing shape. *Bound:* "structurally the same shape" is an argument about form, not a measurement — no run was scored against the constitution's text, and the v1 arm does not carry the v2 Narrowing rule at all.

**Decision recorded 2026-08-13: `src/constitution.md` is NOT edited now.** The reason is measurement, not merit: **any `src/` edit before Phase 1 contaminates the blind baseline**, which must run against v2 exactly as it stands. This binds the constitution the same way Phase 1 already binds `src/` generally.

**OQ-4's recommendation still stands for Phase-0 ratification** and is not pre-decided by this note. The escalated evidence is **also** recorded in the repo-root `CLAUDE.md` FALSE BINARY entry — a parallel edit made separately from this file; if that entry does not carry it, the two records have drifted and this one is the later.

### What this does to the accumulation tripwire

**R1–R3 enlarge Phase 2's file set from two files to three** — four if the drafting session takes the architect edit — **without adding a mechanism.** That is stated plainly rather than assumed to be free. *(This sentence records the delta at the moment of the amendment; it is not a criterion. The edit set Phase 2 names as amended is the single authority for which files that phase touches, and a later re-scope updates it there, not here.)*

- **The tripwire's second clause is untouched and still binds:** no new mechanical check, helper verb, schema field or exit code is introduced by Phase 2. R1's carrier is a document section; R3's two additions are sentences. The Phase-2 Verify criterion enforcing that clause is unchanged.
- **The first clause is met by a measurement argument, not a completeness one:** the lock artifacts are written at research time and spec time, so a Phase 2 confined to one station would be measured against artifacts written before it exists. That is *"Phase 3 cannot be read without it"*, which is the justification the tripwire asks for.

*Counter-argument, recorded, because this is the plan's own named risk:* three files under one measurement is still more surface than the design that was drafted, and every added file widens what a flip — or a null result — is attributing. The mitigation claim is that R1–R3 are **one mechanism at three stations** (produce at research; do not re-lock at specify; verify and consume at plan), not three mechanisms. **That claim is testable and should be tested at drafting:** if the three edits cannot be written as one artifact's produce/consume path, the enlargement was accumulation after all and it returns to Phase 0.

---

## Amendment 2026-08-15 — R1's carrier falsified, and five further review findings

**What this section is.** Six findings — **A1** through **A6** — from a pre-implementation verification pass run against the working tree on **2026-08-15**, before Phase 0 has ratified anything and before any `src/` file has been edited. **A1's replacement carrier is maintainer-ratified 2026-08-15.** **A2–A6 are recorded corrections and go to Phase 0 with everything else**; writing one here does not ratify it. **Nothing above or below is withdrawn, reworded or renumbered.** Each section they amend carries a one-line pointer back here.

**What this section is NOT.** It is not Phase 0, and A1 is not a reopening of R1. R1's production stage, its fact-keyed trigger and its park-once/read-in-place carrier model are unchanged; **only the file the matrix is written to moves**, and only because the file R1 named cannot hold it. D1–D6 and OQ-1–OQ-6 as amended on 2026-08-13 remain unratified, and no `src/` file has been edited.

**Placement.** It sits after *Amendment 2026-08-13* because every finding below is downstream of R1, and before *The proposed change* because — like the amendment above it — it amends the proposal, the decisions, the open questions and the phases alike.

**Anchors into this file.** Every bare `:NNN` below cites this file **as it stood before this section was inserted**, and inserting this section shifts each of them by its own length. They are not renumbered, for the reason A6 states and `:534` set as this file's convention: a silently corrected digit leaves no trace that anything moved. **Every one of them names the text it points at**, so the quoted token is the anchor and the digit is a dated hint — the same rule *Verified state* (`:245`) applies to `src/`.

### A1 — R1's carrier is falsified; the replacement is a sibling file (RATIFIED 2026-08-15)

**R1 resolved the carrier to "a required section of `research-report.md` … No Python, no schema change, no new verb" (`:133`, `:392`, and the D4 pointer at `:346`). That is not achievable.** Verified 2026-08-15 against the working tree:

- **`src/commands/research/main.md:1114`** — the helper "walks the locked schema and emits the full research report markdown to stdout. The orchestrator does NOT compose this markdown; the helper owns the section order … heading levels, and table shapes."
- **`src/commands/research/main.md:1120`** — "The LLM does NOT edit the rendered report via Write or Edit at any point — Phase 4 writes the helper's rendered bytes verbatim and never reshapes them."
- **All eight Phase-3 setters (`src/commands/research/main.md:958`–`:1083`) take typed arguments.** There is no free-text passthrough section through which an orchestrator-composed block could enter.
- **`src/devforge/lib/_research/_render.py`** has a single composer, `_render_report_md(memo, report)`, and contains **zero** references to `inbound_callers` or `fix_path_helpers` — so the matrix's own row source is not in that report today. A matrix section there is net-new render code, not a re-label of something already rendered.
- **`src/devforge/lib/_research/handoff_schema.py:944`** — `InboundCaller` carries `helper_qn`, `caller_qn`, `file_line`, `surface`, `scope`, `justification`. The matrix's columns are not among them.

**So a required section of that report costs a schema field, a setter verb and a `_render.py` change** — which Phase 2's own Verify criterion at `:544` forbids ("No new mechanical check, helper verb, schema field or exit code appears in the diff"), which the second accumulation tripwire at `:443` says must return to Phase 0, and which would convert D6's delete branch from a markdown revert into a schema revert with back-compat tests.

**The ratified replacement: the matrix is written to a SIBLING file, `specs/<dirname>/emission-matrix.md`** — composed by the orchestrator with Write during `/devforge:research` Phase 4, beside the byte-verbatim report, and read in place downstream.

- **R1's substance is unchanged.** Production at `/devforge:research` before any acceptance criterion exists; a document artifact, not a handoff schema field; park-once, read-in-place per plan 53; cheap deletion.
- **Only the FILE changes.** D4's instruction-only property becomes **literally true rather than asserted** — the orchestrator composes a file it owns, so no helper surface is touched at all.
- **Committing it is a one-line instruction change.** `/devforge:research` Step 4.6's `commit-artifacts --paths` array is composed at runtime and already documents an optional third element for the probe script (`src/commands/research/main.md:1229`–`:1236`), so a further path is added the same way.
- **The downstream read directive is the shape R1 already scheduled.** `/devforge:specify` already reads `research-report.md` in a conditional `(if the file exists)` Phase-1 read-and-record block (`src/commands/specify/main.md:216`, `:221`, `:224`), so a second read directive there takes precisely that shape.
- **No collision.** `grep -rln "research-report.md" src/` — excluding `__pycache__`, which a naive re-run also returns, so a compiled hit is not a changed result — matches **ten** files: command specs (`specify/main.md:168`, `:216`, `:221`, `:224`; `plan/main.md:213`; `research/main.md`), helper code (`_research/_cmds_handoff.py:85`, `:111`, `:372`; `_research/_cli.py:277`, `:289`, `:299`, `:679`), one filename constant (`_specify/_topic.py:26`), two comment-and-docstring references (`_specify/_schema.py:304`; `_research/_cmds_phase2.py:110`), and documentation (`src/CLAUDE.md`, `src/devforge/storage-rules.md`). A new sibling filename collides with none of them, and no helper filename constant is touched. `grep -rn "emission-matrix" .` returned zero repo-wide when verified on 2026-08-15, before this section was written; the only occurrences now are this plan document's own uses of the string, so a re-run that hits this file has found no collision.

*Counter-argument, recorded:* a second document in the feature directory is one more artifact, and this plan's own second trap (`:624`) is that adding artifacts does not buy outcomes. **The defence is narrow and is written as such:** it replaces nothing, adds no mechanism, and is the only shape that keeps R1's production stage **and** D4's instruction-only property at the same time. A carrier that costs Python would have been a different plan with a different measurement.

**OQ-3 is re-resolved** to this sibling file. **Its existing counter carries over UNCHANGED and is not softened by the re-resolution:** a document artifact is unverifiable downstream, and nothing mechanical prevents a short matrix.

### A2 — The matrix's columns presuppose a guard that does not exist at the production stage

The column **"Emits after the change"** (`:215`–`:217`), **rule 2** (`:224`), and **OQ-2(i)**'s "only the inputs the proposed guard condition READS" (`:386`) were all specified when production was at `/devforge:plan`, where the guard is a Key Design Decision the architect authors.

**R1 moved production to `/devforge:research`, whose outputs are two-or-more enumerated approaches with one-to-two-sentence descriptions plus one recommended approach (`src/commands/research/main.md:958`–`:1083`).** The nearest thing to a designed change there is `--proposed-call-shape`, and it is required only conditionally (`src/commands/research/main.md:1017`). **Phase 0 item (h) at `:474` still asks the maintainer to ratify a guard-keyed column rule at a stage with no guard.**

**Correction — a recommendation to record, and a Phase-0 item like the rest of A2, not a ratification.** At the research stage the columns are re-keyed so they need no guard, and **the re-keying touches TWO cells, not three**:

- **`Inputs it passes` becomes what this caller emits today.**
- **`Emits after the change` becomes that caller's intersection with the set the ticket removes.** The removed set is a **per-run constant**, so it is stated once in the section's preamble rather than repeated on every row.
- **`Verdict` survives, re-keyed on its own axis: `affected` / `unaffected`**, decided by whether that intersection is empty. That is the axis **rule 6** (derived exclusions, `:158`) actually tests, and it is answerable with no guard.

A non-empty intersection is the finding, and every cell above is fillable from the caller enumeration that stage already performs. **`live` / `dead` is NOT a research-stage verdict:** reachability is a consequence of a guard that does not exist until `/devforge:plan` chooses one, so **the research matrix produces no `dead` rows at all.** The guard-keyed *emits after* evaluation becomes the **`/devforge:plan`-side VERIFICATION role** R1 already assigns to sub-question 7's fresh inbound trace. **The five-column count and the six rules are unchanged in number and in intent** — the columns are re-keyed, never added to or dropped.

*Counter-argument, recorded:* an emits-today column is weaker evidence than an emits-after one — it shows the caller is in the blast radius without showing what the proposed change does to it. The defence is that a column nobody can fill gets waived or filled reflexively, which OQ-2 at `:382` already names as the visibility bar failing in a new way; and that the intersection test is what makes a wrongly-filled row read wrong on its face, which is the property the whole design rests on. *A second counter:* splitting the verdict axis in two makes a reader hold two vocabularies for adjacent artifacts — `affected` / `unaffected` at research, `live` / `dead` at plan — which is real reader cost, and it is the same objection this plan already records against two adjacent triggers at OQ-1 (`:376`). The defence is that they are genuinely different questions asked at stages with different information, and collapsing them into one axis is what produced the contradiction this finding exists to fix.

### A3 — The dead-row population mechanism crosses a command boundary R1 introduced

Phase 2 at `:536` instructs the architect to derive `anchor_token`, `kind` and `why_dead` "from the same trace evidence already gathered to fill the row". **Before R1 the architect filled the row itself. After R1 the row is filled at `/devforge:research`, by a different command in a different session, and the architect receives a carried document — not the trace.**

**Under A2 as resolved the problem largely dissolves, because there is no carried `dead` verdict to re-trace** — the research matrix produces `affected` / `unaffected` rows and makes no reachability claim at all.

**Correction: the architect populates `### Change-Induced Dead Code` at `/devforge:plan` from sub-question 9's own trace, exactly as it does today.** What the matrix supplies is the **input set the architect must account for** — every `affected` row — not pre-made dead rows. A row's presence obliges an answer; it does not supply one.

**Why that matters mechanically:** `verify-dead-code-coverage` (`src/commands/breakdown/main.md:515`) and `check_dead_code_removal` (`src/devforge/lib/_verify/_dead_code.py:188`) both match anchor tokens by verbatim exact-match. **So an anchor token may only come from a fresh trace of the code, never from carried prose** — a token lifted from a document written in another session fails downstream, which is precisely the "a matrix whose `dead` rows reach nothing" failure the Phase-2 Verify criterion at `:547` exists to catch.

**This corrects D2(b)'s population mechanism (`:329`).** D2(b) states that the matrix's `dead` rows populate the `### Change-Induced Dead Code` table; under A2 as resolved they do not, because there are none — the matrix supplies the `affected` set, and sub-question 9 still derives the rows. **D2 is an unratified Phase-0 item, so this is a recorded correction to a proposal, not an override of a ratified decision.** The shipped chain is still fed, and still not modified.

### A4 — The Verified-state premise behind D3 is partly stale

The paragraph at `:268`–`:274` ("Sub-question 7 already performs the enumeration and then discards most of it") and **D3** at `:332`–`:336` rest on the claim that the hidden surface is lost after being found. **Verified 2026-08-15, that is only partly so.** Plan 69's WI-E classifies **every** inbound caller with `surface` / `scope` / `justification` at `/devforge:research`, and `src/devforge/lib/plan_helper.py:1128` (`_render_research_plan_seeds`, the caller line rendered at `:1247`) emits **every** caller — **including those classified `scope: out`** — into the architect brief. What sub-question 7 filters (`src/commands/plan/main.md:363`) is only the caller's appearance in the answer **ROW**.

**Consequence, recorded: D3 still holds and is still a Phase-0 item, but it buys less than the section claims**, because the full result already survives into the brief. **The actual lock point moves upstream** — it is the research-time `scope: out` classification with an unconstrained free-text justification, which is exactly the artifact class A1's matrix is aimed at.

**Recorded openly:** constraining that justification mechanically would be a helper-side change and is therefore **OUT of this plan's instruction-only scope under D4**. It is noted here as a bound on what the matrix can achieve, not as a phase.

### A5 — Phase 2's plan-side edit set is missing the architect brief file list

The architect brief's file list at **`src/commands/plan/main.md:344`–`:351`** names `spec.md`, `research.md`, `data-model.md`, `contracts.md`, `CLAUDE.md` and `constitution.md`. **It does not name the carrier.** Phase 2's plan-side bullet (`:533`) names a sub-question, a conditional template subsection, a PHASE-2.5 backstop step, an approval-summary line and D3's widening — **but not the brief file list, so as written the consumption half would silently no-op.**

**Correction: Phase 2's plan-side edit adds the carrier path to that brief file list.**

**Hazard note for the drafting session:** `specs/<feature>/research.md` is `/devforge:plan`'s **OWN** Phase-0 deep-research file (`src/commands/plan/main.md:212`, `:223`), a **different artifact** from `/devforge:research`'s output. **The two must not be conflated in the emitted text.**

### A6 — Anchor refresh, dated

Per this file's annotate-don't-swap convention (`:534`), the 2026-08-15 verified positions are recorded here **without editing the original digits in place** — a corrected number leaves no trace that the anchors moved. The quoted token remains the real anchor; every digit in both columns is a dated hint.

| Cited in this file | Verified 2026-08-15 | Status |
|---|---|---|
| `plan/main.md:342`–`:351` — sub-questions 1–10 | `:357`–`:366` | DRIFTED |
| `plan/main.md:348` — sub-question 7 | `:363` | DRIFTED |
| `plan/main.md:350` — sub-question 9 | `:365` | DRIFTED |
| `plan/main.md:517` — PHASE-2.5 step 7 | `:532` | DRIFTED |
| `breakdown/main.md:500` — `verify-dead-code-coverage` | `:515` | DRIFTED |
| `breakdown/main.md:336` — the `**Dead code removal**:` task field | `:388` | DRIFTED |
| `_verify/_dead_code.py:5` — `check_dead_code_removal` | `:188` | DRIFTED |
| `plan/main.md:447` — `### Pure-Builder Targets`; `:457` — `### Change-Induced Dead Code` | unchanged (both refreshed 2026-08-13) | STILL CORRECT |
| `plan/main.md:459` — sub-question 9's omit-condition | unchanged | STILL CORRECT |
| `_plan/handoff_schema.py:266` — `DeadCodeRow`; `:289`–`:291` — its `anchor_token` / `kind` / `why_dead`; `:337` — `BreakdownSeeds.dead_code_rows` | unchanged | STILL CORRECT |
| `verify/main.md:266` — the `check-dead-code-removal` call; `_verify/_verdict.py:475` — the `dead_code_unremoved` blocker | unchanged | STILL CORRECT |
| `constitution.md:64` — "No dead code." | unchanged | STILL CORRECT |
| `constitution.md:121`–`:125` — the Narrowing block: caller-scoped opt-in `:122`, completeness-and-fallback `:123`, layer-wide naming obligation `:124`, tie-breaker `:125` | unchanged | STILL CORRECT |
| `src/agents/architect.md:153` — Rule 9 | unchanged | STILL CORRECT |
| `69-CALLER-ENUM-RESIDUAL-HARDENING-PLAN.md:50` — the wrong-symbol `trace_path` hazard OQ-5 inherits | unchanged | STILL CORRECT |
| The roster is 19 agents, as the non-goal at `:423` states (`ls src/agents/` = 19 files) | unchanged | STILL CORRECT |
| `plan/main.md:418`–`:420` — the Key Design Decisions `Alternatives Rejected` column, rule 5's landing site | not re-verified | **NOT RE-VERIFIED — re-grep at use time, do not trust the digit** |
| `plan/main.md:536`–`:539` — the PHASE-3 approval-summary conditional lines | not re-verified | **NOT RE-VERIFIED — re-grep at use time, do not trust the digit** |
| `_plan/handoff_schema.py:55` — the `kind` enum | not re-verified | **NOT RE-VERIFIED — re-grep at use time, do not trust the digit** |

---

## Amendment 2026-08-15 (second) — Phase 0 RATIFIED, Phases 1 and 3 WAIVED, Phase 2 SHIPPED

**What this section is.** The record of three state changes made on **2026-08-15**, after the pre-implementation pass recorded in the section above: **Phase 0 ratified**, **Phases 1 and 3 waived by the maintainer**, and **Phase 2 built and landed under `src/`**. **Nothing above or below is withdrawn, reworded or renumbered.** Each section this one changes carries a one-line dated pointer back here.

**Disambiguation, because two sections now carry this date.** The section immediately above — *Amendment 2026-08-15* — is a pre-implementation verification pass that changed no state and produced findings **A1–A6**. Every pre-existing pointer in this file reading "see Amendment 2026-08-15" or naming an `A`-number means **that** section, and none of them means this one. This section is cited as *Amendment 2026-08-15 (second)* everywhere, and it is the one that moves the plan off NOT STARTED.

**What this section is NOT.** It is not a measurement result, and nothing in it may be read as one. **No arm of this plan's measurement design ever ran.** Read *Phases 1 and 3 — WAIVED* below **before** the build record, because it is the bound on everything the build record claims.

**Placement.** It sits after *Amendment 2026-08-15* because it is the later of the two same-day sections and because every state change in it is downstream of A1's ratified carrier. It sits before *The proposed change* on the same reasoning the two amendments above it use: it amends the proposal, the decisions, the open questions and the phases alike.

### Phase 0 — RATIFIED 2026-08-15

The maintainer ratified this plan's own recommendation on every open item. Each entry below is **confirmed by default** — the recommendation as written, with no counter-argument selected over it — except where the entry says otherwise. **A2–A6 carry no ratification of their own and travel with the items they correct**, named per item; A6 is anchor bookkeeping and corrects no decision.

- **D1 — the artifact and its rules — CONFIRMED as recommended.** What is ratified is D1's shape **as amended**: the rule set including R3's derived exclusions, over the five-column form, with `Why` citing rows and rule 5's checkable-rejection requirement intact.
- **D2 — option (b), supersede on the trigger — CONFIRMED**, together with **its recorded residual**: sub-question 9's weak empty answer stays in force for every decision outside the suppression trigger. That residual is knowingly accepted, not closed. Ratified **as corrected by A3** — the matrix carries no `dead` rows, so what (b) ratifies is that the matrix supplies the `affected` set the architect must account for while **sub-question 9 still derives every `### Change-Induced Dead Code` row from its own fresh trace**.
- **D3 — sub-question 7's output filtering widened — CONFIRMED**, with A4's bound recorded rather than closed: the full classified caller list already reached the architect brief, so the widening buys less than D3's own section claims, and the upstream lock point A4 names — the research-time out-of-scope classification with an unconstrained free-text justification — is untouched by this plan.
- **D4 — instruction-only, no Python — CONFIRMED, and honoured in the build.** The landed change introduces **zero Python, zero schema fields, zero helper verbs and zero exit codes**. See the edit set below.
- **D5 — measure before build — OVERRIDDEN.** Phase 1 is waived, so nothing was measured before the build and the inversion D5 exists to impose did not happen. Recorded as an **override**, not as a satisfied decision: the override acts on D5's counter — that a gating measurement phase can slide and block everything behind it — and forfeits D5's *why*, that without a v2 baseline a passing Phase 3 is unattributable. There is now no Phase 3 to be unattributable.
- **D6 — the delete branch — RETIRED with the measurement it depended on.** **A branch that fires on a probe result cannot survive the probe's cancellation.** This is not a finding that the mechanism survives on merit; it is the removal of the only test that could have ended it. Nothing replaces it. *Counter-argument, recorded:* D6's own counter named the behavioural risk — a session that has just built something will look for a reading of the result that keeps it — and a waiver reaches that same outcome without needing a reading at all. The one mitigation still standing is **D4**: the change is instruction-only, so a later session that judges the mechanism bloat reverts markdown and nothing else.
- **OQ-1 — the fact-keyed research-side trigger — CONFIRMED.** What was ratified is the trigger wording R1 left open, keyed on **the fact** — the recommended approach removes or suppresses an emitted value — and not on any belief about caller count. Per Phase 0's Verify, the divergence from the originating brief's lean is recorded as **decided**, not as noted.
- **OQ-2 — both cardinality bounds — CONFIRMED as re-keyed by A2.** The columns are A2's research-stage re-keying — what the caller emits today, its intersection with the per-run removed set, and the `affected` / `unaffected` verdict with the `varies` escape defaulting to `affected` — and the row bound is **equivalence-class collapse on identical inputs**, with every collapsed call site still enumerated by `file:line`.
- **OQ-3 — the sibling-file carrier — already ratified earlier the same day as A1**, and not re-opened here.
- **OQ-4 — no `src/constitution.md` change — CONFIRMED.** **The consequence is recorded explicitly, because it is the opposite of what OQ-4 and Phase 4 anticipate: this plan does NOT moot the FALSE BINARY finding recorded in repo-root `CLAUDE.md`.** Mooting it was conditional on a passing Phase 3, and **Phase 3 will not run**. **That finding is untouched and still open.** Nothing in this plan may be cited as having settled, closed, mooted or weakened it, and a session that finds this plan's mechanism shipped must not infer otherwise. OQ-4's own counter — that §3.6's rules are cited at three enforcement sites, so "no change" is not costless — stands unaddressed for the same reason.
- **OQ-5 — plan 69's wrong-symbol `trace_path` cross-check carried by citation — CONFIRMED**, rather than re-invented, with its honest bound intact: it detects a wholly-wrong symbol and does nothing for a partially-overlapping one, and it is a property a human reader must notice, not a check.
- **OQ-6 — one run per arm — MOOT.** There are no runs. The bound OQ-6 exists to record — that a single run cannot separate "the rule worked" from "this sample landed differently" — is superseded by a stronger one: **no run of either arm exists at all.**

**Against Phase 0's own Verify, criterion by criterion.** The confirm-or-override criterion is met — every decision and every open question carries one inline above. The D2 pick is recorded **together with its coverage consequence**, and the OQ-1 divergence is recorded as **decided**, not as noted. The "No `src/` file has been edited" criterion was true at the moment of ratification and is **superseded by Phase 2 landing**, recorded here rather than by editing that criterion. The 2026-08-13 addition — that a Phase 0 recording only "R1–R3 confirmed" has not run — is satisfied: R1–R3 are not re-opened, and **every item they left unsettled carries its own entry above**.

### Phases 1 and 3 — WAIVED 2026-08-15 by the maintainer

**Both measurement arms are WAIVED, not deferred, and the distinction is load-bearing.** This repo uses *deferred* for a check the maintainer still intends to run — the repo-root index carries many plans whose e2e gate is deferred on exactly that reading, and this file must not be read into that set. **Neither arm will run.** The blind v2 baseline was never taken; the matrix-run comparison will never be scored. **This plan is a build, not an experiment.**

**The cost, stated plainly and not softened.** This is the plan whose own evidence is that **artifact volume does not move outcomes** — artifact volume varying 24× and test volume 14× with zero effect on the probe, and investigation depth inverting the expected relationship — and whose entire design answer to that evidence was that **only a blind before/after on a frozen prompt could show whether THIS artifact is different from the artifacts that changed nothing.** That test no longer exists. What the mechanism now rests on is the argument that **a wrongly-filled row reads wrong on its face** — the visibility bar, applied by reasoning at drafting and review time. **That is reasoning, not evidence.** D1's own counter-argument already stated the ceiling of that defence, and it now stands as the plan's terminal position rather than as a temporary one: *"that defence is an argument, not a measurement, which is why Phase 3 exists."* Phase 3 does not exist.

> **A future session must not read shipped code here as a validated result.** The artifact was designed against a named criterion and reviewed against it. It has never been scored against the probe it was built for, on either arm, in any harness generation.

**The measurement remains obtainable, and that is a property of D4, not a leftover of D5.** Because no baseline ran, nothing about the baseline has been consumed or spent — it was never a resource that expires. A later session that wants the before/after can still take it: the landed change is **instruction-only markdown**, so a clean checkout, or a revert of the edit set named below, restores the pre-change harness exactly, and the frozen prompt is unchanged by anything here. **D5's ordering is gone and is not recoverable as an ordering** — the build has happened — but the two arms remain individually takeable in either order, which is the cheap-deletion property D4 was ratified for doing double duty.

*Counter-argument, recorded:* the waiver removes what this file calls **the plan's spine, not an appendix**, and D5 was written to prevent precisely the outcome now recorded — an unmeasured mechanism kept alive by the absence of a test rather than by the result of one. **No maintainer rationale is recorded in this file**; what is recorded is the decision and its cost. The strongest honest claim available for the landed artifact is that it was selected against a criterion the two rejected candidate rules — "enumerate the consumers" and a completeness count — demonstrably fail, and that claim is a design argument about form, not a measurement of outcome.

**Phase 4 is unreachable as written.** It runs "only on a flip", and there is no flip to run on. Its docs-reconcile content is performed by this section and by the repo-root `CLAUDE.md` index entry instead. **Its OQ-4 bullet is void**: the conditional closure it would have written into the FALSE BINARY entry required a passing Phase 3, so that closure is not written, and the finding stays open per the OQ-4 entry above.

### Phase 2 — SHIPPED 2026-08-15

**Built and landed under `src/` after Phase 0 ratified and WITHOUT Phase 1.** Phase 2's opening sentence conditions authoring on "Phase 1 confirms the gap"; that condition was **removed by the waiver, not met**. The gap the artifact addresses is therefore the v1 gap recorded in the Problem section and the 2026-08-13 amendment — never a v2-measured one.

**The landed edit set — the single authority for what this plan changed, superseding the amended set at the head of Phase 2:**

- **`src/commands/research/main.md` — PRODUCTION.** An `## Outputs of this phase` entry marking the artifact CONDITIONAL; an `### Emission matrix` compose step at the end of Phase 3 carrying the fact-keyed trigger, the skip clause, the file template and rules 1–4 and 6; `### Step 4.5b — Write the emission matrix (conditional)`; the matrix added to the Phase 4 opening order line; and `specs/<dirname>/emission-matrix.md` documented as an optional element of Step 4.6's `commit-artifacts --paths` array.
- **`src/commands/plan/main.md` — CONSUMPTION.** The artifact added to the architect brief's file list — **A5's finding, without which the consumption half silently no-ops** — carrying a caution that this command's own `research.md` is a different artifact from the one `/devforge:research` writes; sub-question 7's output widened per D3 so every caller survives with its classification; a new **sub-question 11** consuming the matrix; a prohibition inside **sub-question 9** forbidding an `anchor_token` from being lifted from a carried cell; a **PHASE-2.5 step 8** read-side backstop; a conditional approval-summary line; and **rule 5 labelled** at the Key Design Decisions table.
- **`src/commands/specify/main.md`** — a conditional `### 1.8` read-and-record block, **R3's acceptance-criteria directive** requiring quoted product intent, and the source-count and section-enumeration reconciliations that adding a section to that phase forced.
- **`src/agents/architect.md`** — two new Rule 9 forcing steps, `**Emission-matrix forcing step:**` and `**Rejected-alternative checkability forcing step:**`. **The optional architect edit Phase 2 left to the drafting session was taken**, and taken as two steps rather than one — the second carries rule 5's checkable-rejection requirement to the agent that authors the decisions table, complementing rule 5's landing site in `src/commands/plan/main.md`.
- **`src/CLAUDE.md`** — one Artifact Storage tree line.

**Rule placement across the two stations, recorded because it is split.** Rules 1–4 and 6 land at the **production** site, where the rows are filled. **Rule 5 lands at the consumption site**, at the Key Design Decisions table's existing `Alternatives Rejected` column — the landing site Phase 2 already specified — with its agent-side forcing step in the architect file. **No new column and no new table** was added at either station, per the tripwire.

**One recorded divergence from Phase 2's Verify, recorded rather than smoothed.** The amended criterion reads "`git diff --name-only` returns exactly the files named in the amended edit set at the head of this phase — no more and no fewer", and that set named the three command files plus the optional architect file. **`src/CLAUDE.md` is outside it.** It is a one-line docs reconciliation of the kind Phase 4 owns, landed inside Phase 2 because Phase 4 is unreachable. **The clause that actually enforces the accumulation tripwire is unaffected and holds: no new mechanical check, helper verb, schema field or exit code appears in the diff** — which is also what makes D4's confirmation above literally true rather than asserted.

**Verification performed.** An **instruction-reviewer** pass over the whole diff raised three findings, **all fixed**:

1. a **scope mismatch**, where the checkable-rejection rule sat inside a matrix-gated step and so would have gone inert on every decision that produced no matrix;
2. an **unlabelled rule 5**, which falsified the producer's claim that the two stations share one rule numbering;
3. an **incomplete parallel edit** in the specify command, where adding a section left that phase's own source-count and section-enumeration statements unreconciled.

A **claude-code-guide** pass returned **conformant** on slash-command reference syntax, body-text interpretation, agent-file body conventions and invocation behaviour.

**The honest bound on that verification: it is BUILD verification.** It establishes that the landed instructions are internally consistent, correctly placed, and conformant to Claude Code's authoring conventions. **It establishes nothing about outcomes.** Nothing here has been run in a consumer install, and **the artifact has never been produced by a real `/devforge:research` run** — so the first emission matrix any session sees will also be the first evidence that the trigger fires at all, that the table is fillable at that stage, and that a filled row reads the way the design assumes.

### Known residuals — recorded 2026-08-15, none fixed

1. **`emission-matrix.md` auto-tags as prior-spec material at `/devforge:specify`.** The helper's filename dispatch at `src/devforge/lib/_specify/_topic.py` recognises only the two intake reports before falling through, so a recorded read of the new sibling carries `source_origin = "prior_spec"` — **the exact mis-tag that dispatch exists to prevent**, and which that module's own comments name as the risk they were written against. The effect today is limited to corpus grouping. **Fixing it requires helper code, which D4's instruction-only scope excludes** — so it is recorded rather than repaired, and a session that widens the dispatch is making a scope decision this plan did not.
2. **Rule 9's `Why`-cell has no ordering convention for a third annotation.** It already defines an order for a decision that is both an established-convention departure and a multi-state type; **emission-matrix accounting is now a third annotation landing in the same cell**, and a decision that restricts shared code could carry all three at once. No order is stated for that case, and none was invented.
3. **No durable carrier distinguishes "no matrix was applicable" from "the step was skipped".** The production site documents the artifact's **absence** as meaning the trigger did not fire — true when the step ran and found nothing, false when the step never ran, and indistinguishable either way. With no file written, no helper field and no schema change permitted under D4, the distinction survives only in the run's own message to the user and is gone by the next session. *Counter, recorded:* closing it costs exactly the mechanism D4 and the second accumulation tripwire forbid, so this residual is the price of the instruction-only shape rather than an oversight in it.
4. **The feature is unmeasured** — see *Phases 1 and 3 — WAIVED* above. **This is the residual every other one above is downstream of**, and the only one that cannot be closed by a later edit to this plan's own scope.

---

## The proposed change

### The artifact

For any decision that **removes or suppresses an emitted value**, require this artifact BEFORE the decision is recorded:

A **post-change output matrix** for the function being changed, **one row per call site**:

| Call site (file:line) | Inputs it passes | Emits after the change | Verdict | Note |
|---|---|---|---|---|
| [caller path + line] | [the inputs the proposed guard reads] | [traced, not asserted] | live / dead | [required when the row still emits the value being removed, or when the verdict is dead] |

**[Amended 2026-08-15 — see Amendment A2.]** `Inputs it passes` and `Emits after the change` presuppose a guard that does not exist at R1's production stage and are re-keyed there to emits-today and its intersection with the removed set; `Verdict` survives on its own re-keyed `affected` / `unaffected` axis, and the five-column shape is unchanged. **The example row's `Note` cell re-keys the same way** — required when the intersection is non-empty, or when the verdict is `affected`.

The decision table's `Why` column then **cites matrix rows** rather than restating them.

### The five rules

1. **Every call site appears**, found mechanically and cited by file and line. No sampling.
2. **The "emits after" cell is evaluated per row against the proposed change — traced, not asserted.**
3. **Any row that still emits the value being removed must be justified in one sentence, or the design is wrong.**
4. **If a branch becomes unreachable, the constitution's No-dead-code rule applies: delete it, do not guard it.**
5. **Any alternative rejected as impossible must name the arguments the function actually receives and show the claim against them.**

Rule 5 is the direct answer to the one-line unfalsifiable rejection described above. Rule 4 is already built (see Verified state) and this plan reuses it rather than rebuilding it.

**[Amended 2026-08-13 — see Amendment R3.]** A **sixth rule — derived exclusions** was ratified on 2026-08-13 and is stated in full in the amendment above. Rules 1–5 are unchanged and unrenumbered. Rule 6 clears the visibility bar on **content** grounds, joining rules 2, 3 and 5 in the enumeration at *The bar* — that enumeration is not exhaustive of the rule set from this date. Every "five rules" phrasing elsewhere in this file — the heading above, D1's heading and body, Phase 0 item (a), and OQ-5's closing sentence — reads as **six** from 2026-08-13. **The five-COLUMN shape is unchanged:** rule 6 is filled from cells the matrix already has and adds no column.

**[Amended 2026-08-15 — see Amendment A2.]** Rule 2's "traced, not asserted" evaluation is re-keyed at R1's production stage to a stated intersection rather than an emits-after trace, and the emits-after evaluation becomes `/devforge:plan`'s verification role; the rule's number, count and intent are unchanged.

**Rule 1's honest bound — an accepted residual, not a solved problem.** Rules 2, 3 and 5 clear the visibility bar on **content** grounds: a cell that is filled wrongly reads wrong. Rule 1 cannot clear it that way, because it is an enumeration-completeness rule — the same shape as the "enumerate the consumers" candidate rejected above. **A silently missing row is indistinguishable from a complete matrix to a human at the approval gate:** when the mandated inbound trace fails to surface a call site (graph incompleteness, dynamic dispatch, reflection, an indirect call pattern), nothing in the artifact reads wrong. So rule 1's completeness is bounded by the completeness of the mechanical enumeration it rests on, and it is **not independently checkable by the reader**. *This is distinct from D4's counter,* which is that nothing mechanically checks the matrix against a known call-site count; this bound holds even when the matrix faithfully transcribes a trace that looked complete. **Rule 1 stays as written** — a mechanically-sourced enumeration is strictly better than none, and it is the floor the other rules stand on — but it is a floor, not a self-verifying artifact, and this bound is accepted rather than closed. OQ-5 records the one narrower, named instance of it.

### Why this yields the right design without naming it

Filling the matrix honestly makes a wrong row **self-evident**. A row showing an unintended caller still emitting the removed value needs no design principle to look wrong — and **the only change that flips that row without editing that caller is the intrinsic one**: a guard keyed on state the function already receives. Rule 4 then closes it: once the branch is unreachable, deletion is required rather than a guard.

This is why the plan proposes **no new preference rule**. The preference is a consequence of the artifact, not an instruction the artifact carries. See OQ-4 for what that implies about the constitution.

---

## Verified state (2026-08-12)

Verified against the working tree this session by reading the files, not by trusting the originating brief or any plan's Status line. **Line numbers drift — grep the quoted tokens.** This repo has documented anchor rot (plan 75 records plan 73 re-keying its own anchors six times), so every `:NNN` below is a dated hint and the quoted string is the real anchor.

**[Amended 2026-08-13 — see Amendment R1.]** Everything verified below is at the **consumption** site (`/devforge:plan`) and stays valid there. **The production site is now `/devforge:research`, and nothing about it is verified in this section.** Its phase numbers, section names and rubric structure are unverified as of this amendment and must be read from `src/commands/research/main.md` before drafting, not guessed. Only the following was spot-checked on 2026-08-13, and it is the whole of what this file asserts about that site: `src/commands/research/main.md` exists, it names `research-report.md`, and it invokes `record-fix-path-helper`, `record-inbound-caller`, `classify-caller-scope`, `declare-caller-total` and `set-recommended-approach`. Treat every other research-side statement as an open item.

### Rule 4 is BUILT — and it is the only one of the five that is

- **`src/commands/plan/main.md:350`** — PHASE 1.3 architect-consult **sub-question 9** asks whether any Key Design Decision renders existing code UNREACHABLE, and returns rows `file | anchor token | kind | why dead`. The **anchor token** is defined there as "a literal string lifted from the code whose ABSENCE in the post-change file proves the path was removed", must not contain `;`, and **kind** is one of `arm | function | param | import | branch`.
- **`src/commands/plan/main.md:442`** — the conditional `### Change-Induced Dead Code` plan-template subsection; **`:450`** states each row is a MUST-delete obligation under the constitution's §3.5 No-dead-code rule, folded into the owning task at `/devforge:breakdown`.
- **`src/devforge/lib/_plan/handoff_schema.py:266`** — `class DeadCodeRow` with fields `file`, `anchor_token`, `kind`, `why_dead` (`:288-291`); **`:337`** — `BreakdownSeeds.dead_code_rows`, default-empty.
- **`src/commands/breakdown/main.md:500`** — `breakdown_helper verify-dead-code-coverage <tasks-dir>`, the 6th PHASE-3.5 gate; **`:336`** — the `**Dead code removal**:` task-file header field.
- **`src/devforge/lib/_verify/_dead_code.py:5`** — `check_dead_code_removal(dead_code_rows, source_root)`, whose pass condition is the ABSENCE of each `anchor_token` in the post-change file; wired at **`src/commands/verify/main.md:266`** and folded as the `dead_code_unremoved` blocker at **`src/devforge/lib/_verify/_verdict.py:475`**.
- **`src/constitution.md:64`** — "**No dead code.**"; **`src/agents/architect.md:153`** — Rule 9's **Consequence forcing step**, which names "guard-and-leave" as the anti-pattern it exists to prevent.

**So the entire back half of rule 4 — declare, task, confirm — is shipped machinery this plan must feed, not rebuild.**

### Sub-question 9 FAILS the visibility bar

Sub-question 9 requires an **explicit empty answer** — the literal string `renders nothing unreachable`, with silence forbidden (`plan/main.md:350`, echoed in the template's omit-condition at `:444`).

That string is **byte-identical whether the architect traced every call site or merely read the lines it was editing.** An artifact that reads the same when the analysis was skipped is precisely what the bar rejects.

Its trace instruction is also scoped to "the code the decision touches" with **no direction specified** — `plan/main.md:350` names `trace_path` / `search_code` on the actual code but never says inbound. Nothing in the sentence sends the architect to the callers.

### Sub-question 7 already performs the enumeration and then discards most of it

**`src/commands/plan/main.md:348`** — sub-question 7 fires on decisions that RESTRICT existing behavior of shared code, and **`:353`** already mandates "ONE fresh `trace_path(<helper_qn>, mode=calls, direction=inbound)`" for any helper a decision restricts, to confirm the carried callers are still current.

But the OUTPUT is asymmetric. For a caller-scoped restriction, `:348` asks only for "every caller classified **in-scope**". The full current-caller list is demanded only on the **layer-wide** branch — i.e. only on the branch the constitution's Narrowing rule (`src/constitution.md:121-125`) tells you not to take.

**The hidden surface is in that trace's output and gets filtered out before it reaches any table.** The cost of finding it has already been paid; the finding is then discarded.

**[Amended 2026-08-15 — see Amendment A4.]** The full classified caller list already survives into the architect brief, so what is filtered here is only the answer row — the premise holds in narrower form than this section states.

### Nothing matrix-shaped exists

`grep -niE "matrix|live or dead|reachability|call site" src/commands/plan/main.md` → **0 hits.** Widening the pattern to include `post-change` returns exactly **one** line, `:350`, inside sub-question 9's own anchor-token definition. The read-side backstops at PHASE 2.5 run steps 1–7 (`:507`–`:517`); step 7 is the Narrowing backstop and mirrors step 6's shape.

### The structural reading — state it, but do not treat it as established

The matrix sits at the **join of two existing sub-questions**: its **row source** is sub-question 7's already-mandated inbound trace, and its **dead rows** feed sub-question 9's shipped downstream machinery unchanged — though **not column-for-column**: the two shapes differ, so the row-to-row transform is something Phase 2 must state rather than something the join supplies for free. On that reading the change is substantially a **rewiring**, not new construction.

**Do not treat "it's only a rewiring" as a reason to skip Phase 1.** The rewiring claim describes build cost. It says nothing about whether the artifact changes the outcome, and the measurement warning below is about exactly that.

**[Amended 2026-08-13 — see Amendment R1.]** **"Row source" above describes the pre-amendment framing, in which the matrix was produced at `/devforge:plan`.** Under R1 the production row source is `/devforge:research`'s own caller-enumeration machinery, and sub-question 7's inbound trace takes a **verification** role instead — it re-checks that a carried matrix is still current against the code as it stands, which is a different job from supplying the rows. **The dead-rows half of the join is unchanged:** those rows still feed sub-question 9's shipped machinery, still not column-for-column, and the transform is still Phase 2's to state. **The rewiring reading survives the move**, and so does the warning under it — it is a claim about build cost and still not a reason to skip Phase 1.

**[Amended 2026-08-15 — see Amendment A3.]** **The dead-rows half of the join is precisely what changed**, so both the paragraph above and the 2026-08-13 pointer's claim that it was unchanged are corrected here. The research matrix produces no `dead` rows, so none of its rows feed sub-question 9 and **there is no row-to-row transform for Phase 2 to state**. What reaches sub-question 9 is the `affected` set the architect must account for; sub-question 9 still derives its own rows from its own trace. **The rewiring reading survives once more** — the join is now enumeration-to-obligation rather than row-to-row — and so does the warning under it.

---

## The measurement design — the plan's spine, not an appendix

The proposal's own falsification test, stated by its author: **rerun the benchmark arm blind, frozen prompt, with only this change. Probe flips → the rule works, with a measured before/after on identical everything else. Probe doesn't flip → it is bloat, delete it.**

**But that design assumes a measured baseline for the harness being changed, and v2 has none.** Every number in the Problem section is v1.28 from `main`. v2's discovery machinery is different and later — a caller-enumeration gate (plan 67), a mode decouple (plan 67), caller-scope classification (plan 69) — and **nobody has ever run v2 against this ticket.** Land the matrix in v2, watch the probe pass, and the result is unattributable: it could be the matrix, or it could be any of three shipped changes that arrived after the measured baseline.

**So in v2 the test needs TWO arms, in order:**

1. **A blind v2 baseline run** on the frozen prompt, FIRST, with no matrix.
2. **Then the matrix run**, same frozen prompt, same everything else.

Four outcomes, all four of which must be readable as results:

- **Baseline already handles the hidden surface** → the matrix is bloat by the proposal's own rule, and it is **deleted before it is built**. Phase 2 never starts. This is a success of the method, not a wasted plan.
- **Baseline reproduces the v1.28 signature** (discovers, does not act) → the gap is confirmed in v2 and the matrix is aimed at it. Proceed to Phase 2; one more run decides.
- **Baseline neither discovers nor acts** → v2 has REGRESSED on discovery relative to v1.28's 2/2. That is a different defect in a different layer, this plan is not aimed at it, and Phase 2 must not start. Open a sibling plan.
- **Baseline discovers and acts on some element of the change but not the hidden surface** → read it as the second outcome, and record which parts moved, because that detail changes what Phase 3's probe is comparing against.

The baseline arm is a **gating phase**, not a suggestion. Its honest bound is OQ-6.

**[Amended 2026-08-13 — see Amendment R2.]** The handling probe is scored more strictly from this date: it passes **only** if the hidden surface stops emitting the removed values **without its file appearing in the diff**. A run that fixes the hidden surface by editing that surface's file is labelled **discovered-and-swept** and scores as **not a pass** — so it does not satisfy the first of the four outcomes above. A secondary signature check runs on both arms as an observation, not a probe. **Both arms are scored under the same amended criteria**, or the before/after is not like-for-like. The four outcomes above are unchanged in kind.

---

## Decisions (ratify at Phase 0 — each carries its counter-argument)

### D1 — The artifact and its five rules, as stated above

What is being ratified is the **shape**: five columns, one row per call site, five rules, `Why` cites rows.

*Counter-argument, recorded:* a five-column table is more structure than any other single sub-question in PHASE 1.3 produces, and the repo's own evidence (the nine-artifact harness scoring 0/3) is that structure volume does not buy outcomes. The defence is that this artifact is selected against the visibility bar and the nine were not — but that defence is an argument, not a measurement, which is why Phase 3 exists.

**[Amended 2026-08-13 — see Amendment R1 and R3.]** The ratified rule set is now **six**, the added rule being derived exclusions; the column shape is unchanged. R1 also moves production off `/devforge:plan`, so the counter-argument's comparison to PHASE 1.3 sub-questions now describes the **consumption** site — the volume-versus-outcome objection it makes survives the move intact and is strengthened by the amendment's null results (24× artifact volume, zero probe effect).

### D2 — Relationship to sub-question 9

Three options, and the pick has a coverage consequence that must be decided here rather than discovered mid-build.

- **(a) Replace.** The matrix subsumes sub-question 9. *Cost:* sub-question 9's trigger is **every Key Design Decision**; the matrix's trigger is decisions that remove or suppress an emitted value. Those are different sets. A straight replace **narrows** the dead-code lane and orphans the shipped `DeadCodeRow` → `verify-dead-code-coverage` → `check-dead-code-removal` chain for every kill that is not a value suppression (removing a call, deleting a flag branch). Making (a) coherent requires widening the matrix's trigger to every decision, which converts it into a per-decision artifact and walks straight into OQ-2's cardinality problem.
- **(b) Supersede on the trigger — RECOMMENDED.** Sub-question 9 stays as the general kill-declaration question. What changes is that its bare empty answer is **no longer accepted** for a decision that removes or suppresses an emitted value: for those decisions the matrix is the required evidence, and the matrix's `dead` rows are what populate the existing `### Change-Induced Dead Code` table — by an explicit transform Phase 2 states, since the two shapes do not map column-for-column. *Why:* the documented failure is specifically that the **empty answer** is unfalsifiable, not that the question is wrong. This targets the failure and leaves the general trigger and the whole downstream chain byte-unchanged. *Counter:* it leaves sub-question 9's weak empty answer in force for every decision outside the suppression trigger — a real, knowingly-accepted residual.
  **[Amended 2026-08-15 — see Amendment A3.]** The matrix carries no `dead` rows to transform — it supplies the `affected` set the architect must account for, and sub-question 9 still derives the dead rows from its own trace; a recorded correction to this unratified option's population mechanism, not an override.
- **(c) Two independent questions**, unrelated. *Cost:* two adjacent questions a reader must distinguish under time pressure, with overlapping subject matter and no stated relationship — the exact reader burden OQ-1 is about.

### D3 — Sub-question 7's output filtering is widened under EVERY option

Independent of D2 and OQ-1: `plan/main.md:348`'s in-scope-only output for the caller-scoped branch is where the hidden surface is lost after being found. **The full inbound-trace result must survive to a table.** This is not one of the options — every option depends on it, because without it the matrix has no honest row source.

*Counter:* widening the output makes sub-question 7's answer longer for every restricting decision, including the ones with a large caller set. That is the same cardinality pressure as OQ-2 and takes the same answer.

**[Amended 2026-08-15 — see Amendment A4.]** This still holds and stays a Phase-0 item, but it buys less than stated — the full classified caller list already reaches the architect brief, so the lock point sits upstream in the research-time out-of-scope justification.

### D4 — Instruction-only v1; no Python, so deletion is cheap

Under D2(b) + OQ-3's recommended answer, the entire change is **two markdown files**: `src/commands/plan/main.md` (a sub-question, a conditional template subsection, a PHASE-2.5 read-side backstop step, an approval-summary line) and `src/agents/architect.md` (a forcing step inside Rule 9). No schema field, no helper verb, no parser.

*Why it matters:* the measurement design requires that deletion be genuinely cheap, or the sunk-cost pull will keep a mechanism the probe did not validate. Two markdown reverts is cheap; a schema field with back-compat tests and a parser is not.

*Counter:* an instruction-only artifact cannot be mechanically checked for completeness — nothing stops a three-row matrix on a five-caller function. The bar's own reasoning absorbs most of this (a completeness count fails the bar anyway), but not all of it, and the residual is real. If OQ-3 flips to a carrier, Python enters via `_plan/handoff_schema.py` + `plan_helper finalize-handoff`, and the loop becomes python-engineer → python-reviewer as well.

**[Amended 2026-08-13 — see Amendment R1.]** The **instruction-only property this decision exists to protect is preserved and strengthened**: R1 resolves OQ-3 to a required section of `research-report.md` read in place, so no schema field and no verb enters, and deletion is still a markdown revert. What changes is the file set — "two markdown files" reads as R1's re-scoped set (`src/commands/research/main.md`, `src/commands/specify/main.md`, `src/commands/plan/main.md`, and `src/agents/architect.md` only if the drafting session takes it). More files is a larger revert but not a harder one, and the counter above is unaffected by the move. **On the count specifically:** "two markdown files" above — and "Two markdown reverts" in *Why it matters* — are now wrong as **numbers**, not only as lists. The authority for how many files and which is **the edit set Phase 2 names as amended** — not those sentences, and not this pointer's parenthetical, which is a convenience restatement and is not a second source of truth. What D4 ratifies is **instruction-only**, a property of the change that carries no count at all, and *Why it matters*' argument (markdown reverts are cheap, a schema field with back-compat tests is not) holds at any set size.

**[Amended 2026-08-15 — see Amendment A1.]** The `research-report.md` carrier this pointer relies on is falsified; the sibling-file replacement is what actually preserves the instruction-only property, and D4's ratified content is unchanged.

### D5 — Measure before building; the baseline arm gates

Phase 1 is a measurement phase that runs **before** any `src/` edit. This inverts this repo's near-universal convention, in which the consumer/testForge20 e2e is the LAST phase and the build precedes it.

*Why:* without a v2 baseline, a passing Phase 3 is unattributable, and an unattributable pass is what keeps unmeasured mechanisms alive forever.

*Counter:* the inversion costs a real run before there is anything to show for it, and the repo's own history shows e2e phases sliding (numerous plans carry a deferred user-driven e2e). A Phase 1 that slides blocks everything behind it — where a trailing e2e that slides at least leaves shipped code. That is the honest trade, and it is the maintainer's to make.

### D6 — The delete branch is a first-class outcome, not a failure

If Phase 3's probe does not flip, Phase 2's two edits are reverted and this plan closes as a **measured negative**. A measured negative about a plausible mechanism is a durable output: it removes a candidate from the survey permanently and tells the next plan where not to look.

*Counter:* none on the merits. The risk is not intellectual, it is behavioural — a session that has just built something will look for a reading of the result that keeps it. That is why the delete branch is written into Phase 3's Verify rather than left as a sentiment.

**[Amended 2026-08-13 — see Amendment R1.]** "Phase 2's two edits" names a count R1's re-scope makes wrong. Read it as **the edit set Phase 2 names as amended**, whatever its size — that set is stated in one place on purpose, and a count restated here would only drift again. **The point that must survive does not depend on the number:** every file in that set is markdown, no schema field and no verb enters, so the revert stays a set of markdown reverts done in one session. A larger set is a longer revert, not a harder one.

---

## Open questions

- **OQ-1 — Where the trigger lives, and it does not nest cleanly.** Sub-question 7 fires on "restricts existing behavior of shared code"; the matrix fires on "removes or suppresses an emitted value". **Suppressing an emitted value is always a restriction, but a restriction is not always a suppressed value — the sets overlap without one containing the other.**

  *The originating brief's lean:* widen sub-question 7's output rather than add a second adjacent trigger a reader must distinguish under time pressure, since 7 already pays the enumeration cost.

  *This plan's recommendation diverges, and the reason is specific:* **sub-question 7's trigger is keyed on a belief, and the matrix's trigger is keyed on a fact.** `constitution.md:121` and `plan/main.md:348` define shared code as code "with multiple callers" — so a decision only fires sub-question 7 if its author already believes the function has more than one caller. **A belief about caller count is exactly what is wrong in the failure mode this plan exists for.** The author of the losing design believed it was wiring the one caller that mattered. By contrast, "does this change remove or suppress a value the function emits?" is a property of the change the author knows for certain before tracing anything.

  So the recommendation is **(b) the matrix carries its own trigger, keyed on the change, and reuses sub-question 7's enumeration as its row source** — appended as sub-question 11 per the repo's append-never-renumber convention (plan 73 appended sub-question 10 for this reason; `plan/main.md` currently runs 1–10 at `:342`–`:351`).

  *Counter, which is real and is the brief's:* two adjacent questions about overlapping subject matter is a reader cost, and under time pressure a reader distinguishes them wrongly or answers one twice. **Option (a) remains fully viable** and its cost is bounded: folding into 7 loses only the single-caller-belief case, which is arguably rare — except that it is the observed case. Maintainer decides; this is flagged as a divergence from the brief's lean, not as a settled reading.

  Under **all three** options, D3 holds: 7's output filtering is widened regardless.

  **[Amended 2026-08-13 — see Amendment R1. SUPERSEDED IN FRAME, not answered.]** Production moved to `/devforge:research`, so "which `/devforge:plan` sub-question hosts the matrix" no longer has a subject as posed, and none of the three options above is selected. **The reasoning is not withdrawn:** the belief-versus-fact distinction survives intact and now grounds the research-side trigger, which stays keyed on the fact — "the recommended approach removes or suppresses an emitted value". **D3 still holds** on the `/devforge:plan` consumption side and remains a Phase-0 item. What is left for the maintainer at Phase 0 item (g) is confirming the research-side trigger wording, not choosing between (a), (b) and (c).

- **OQ-2 — Cardinality. What bounds a row, and what bounds "relevant state"?** Callers × relevant states explodes for a widely-used helper, and **an unfillable artifact gets waived or filled reflexively** — which is the visibility bar failing in a new way rather than a new mechanism working.

  Two separate bounds are needed and they are not the same question:

  *(i) What goes in the "inputs it passes" cell.* **Recommendation: only the inputs the proposed guard condition READS**, never the caller's full argument list. Column width is then bounded by the guard's arity, not the function's. When a caller's value for a guard-read input is not statically determinable, the cell reads `varies` and the "emits after" cell must cover **both** branches, defaulting the verdict to `live`. *Counter:* `varies` is a cheap blanket escape and could swallow the whole matrix — which is the same shape as the finding recorded at repo-root `CLAUDE.md` about a blanket rubric escape flag versus the justified-escape shape the same helper package already uses elsewhere. Mitigation: a `varies` cell must state which values were considered, making it a justified escape rather than a boolean one.

  **[Amended 2026-08-15 — see Amendment A2.]** The guard-read-inputs rule has no guard to read at R1's production stage; the cell is re-keyed there to what the caller emits today, and the `varies` escape shape carries over to the intersection statement. **The escape's default verdict is re-keyed with it: `live` is meaningless at that stage, so a `varies` cell defaults the verdict to `affected`** — the conservative case, preserving the fail-safe intent the `live` default carried. The mitigation is unchanged: a `varies` cell must state which values were considered.

  *(ii) How many rows.* Plan 69's OQ-4 probe observed a depth-1 inbound trace returning the full caller set for a function with in-degree 47; a 47-row matrix is unfillable in practice. Options: no cap and accept the cost; a cap with an explicit overflow declaration; or **row-collapse by equivalence class — recommended:** callers passing **identical** guard-read inputs collapse into one row that still enumerates every collapsed call site's `file:line`, so completeness is preserved and row count is bounded by distinct input shapes. *Counter:* collapsing is itself a judgment, and the caller that differs is precisely the one that wants its own row. Mitigation: collapse is permitted only on **identical** inputs — any difference in any guard-read input forces a separate row. This preserves the property the whole design rests on, that a wrongly-filled row reads wrong on its face.

- **OQ-3 — Carrier.** Does the matrix ride the plan→breakdown handoff, or is it a plan-document artifact the human reads at the approval gate? *Recommendation: **plan-document only for v1**.* The `dead` rows continue to carry through the **existing** `DeadCodeRow` / `BreakdownSeeds.dead_code_rows` path with no schema change. Reasons: nothing at `/devforge:breakdown` or `/devforge:verify` consumes a **live** row, so carrying one creates the same shape plan 41 named for agents, steps and findings, applied here to a schema field; and it keeps D4's cheap-deletion property, which the measurement design depends on. *Counter:* a document-only artifact is unverifiable downstream, so no mechanism prevents a short matrix. Partially absorbed by the bar (a completeness count fails it anyway) and partially real. If a downstream consumer ever appears, the carrier is a later, separable change.

  **[Amended 2026-08-13 — see Amendment R1. RESOLVED.]** The carrier is a **required section of `research-report.md`**, inside the feature dir `/devforge:research` allocates at intake finalize (plan 68), **read in place** by `/devforge:specify` and `/devforge:plan` — plan 53's park-once/read-in-place precedent — and it is **not** a handoff schema field. The recommendation's substance is unchanged (document artifact, no schema change, cheap deletion); only the document it lives in moves, because production moved. The `dead` rows still carry through the **existing** `DeadCodeRow` / `BreakdownSeeds.dead_code_rows` path with no schema change. **The counter above carries over unchanged and is not softened by the resolution.**

  **[Amended 2026-08-15 — see Amendment A1. RE-RESOLVED.]** The carrier is a sibling `specs/<dirname>/emission-matrix.md`, not a section of `research-report.md`, which the helper composes and the LLM may not edit; the document-artifact substance and the carried-over counter are both unchanged. **One vocabulary note, per Amendment A3:** "the `dead` rows" above means sub-question 9's own `DeadCodeRow` output, not the matrix's rows — the matrix emits none, and this bullet's point is that the shipped chain stays stable, which A3 affirms.

- **OQ-4 — Does the constitution need changing at all?** Repo-root `CLAUDE.md` records a live, explicitly-unsettled finding that the constitution's Narrowing rule may present a **FALSE BINARY**: `src/constitution.md:122` names a **caller-scoped opt-in** and `:124` a **layer-wide policy change**, and does not name **deriving the restricting condition inside the shared function from arguments it already receives** as a first-class third form. The enumeration-independent form surfaces only inside the fallback arm at `:123` — reachable only when the needing-caller set cannot be established — and then inherits `:124`'s obligation to name every current caller. **That third form is exactly what won the benchmark.**

  The obvious response is to add it as a third form. *Recommendation: **no constitution change**,* on the grounds that this plan's own central evidence is that taste instructions lose against one confident sentence, and the matrix makes the right form self-evident without naming it. **If that holds, this plan CLOSES the FALSE BINARY finding by making it moot rather than by answering it** — and that closure is **conditional on Phase 3 passing**. If Phase 3 fails and D6's delete branch fires, the finding is untouched and still open; nothing in this plan may be read as having settled it.

  *Counter, which is not weak:* §3.6's rules are not purely taste — they are cited by `plan/main.md:348`, by `plan/main.md:517`'s PHASE-2.5 backstop and by `architect.md:153`'s Narrowing forcing step, so a rule naming only two forms **actively steers** toward one of them at three enforcement sites. "No change" is therefore not costless. Maintainer decision.

  **[Amended 2026-08-13 — see Amendment *OQ-4 — recorded input*.]** The larger evidence set strengthens **both** sides — the null results support "no change", while guard shape being the only predictive axis sharpens the counter, since the preferred caller-scoped opt-in is structurally the opt-out-parameter shape 15/16 runs produced and the probe rejected. **A dated decision was recorded: `src/constitution.md` is NOT edited now**, on measurement grounds — any `src/` edit before Phase 1 contaminates the blind baseline. **The recommendation above still stands for Phase-0 ratification and is not pre-decided by that decision**, which is about timing, not merit.

- **OQ-5 — Row-source reliability, inherited whole.** `69-CALLER-ENUM-RESIDUAL-HARDENING-PLAN.md:50` records the live-probe finding that `trace_path` **keys on the bare function name**, and for a name shared by two functions it silently returned the OTHER symbol's callers — "a wrong-symbol trace yields a confidently wrong declared total." Its mitigation was prose-side: verify the result rows' qualified names against the recorded helper QN before counting.

  The matrix's completeness depends on that same verb, so it inherits the same weakness, and the same prose cross-check must be carried rather than re-invented. *One partial mitigation worth recording:* a wrong-symbol trace is **more** detectable in a matrix than in a count, because the "inputs it passes" cell of a foreign caller will not match the changed function's signature. *Honest bound:* that detects a wholly-wrong symbol; it does nothing for a partially-overlapping one, and it is a property a human reader must notice, not a check. This is the **narrow, named** instance of a broader bound on rule 1 — that its completeness is only as complete as the enumeration under it — which is recorded with the five rules above, not here.

- **OQ-6 — Does one run decide?** The proposal says one run decides, and that is a defensible cost stance. Its bound must be recorded rather than smoothed: **a single run cannot distinguish "the rule worked" from "this sample landed differently"**, and this repo has already shipped a mechanism on exactly that reasoning — plan 62's D13 fixed 2-pass quorum exists because a single stochastic pass is not a verdict.

  *Recommendation: keep one run per arm* (cost), record the bound in the result, and adopt one cheap hedge: **if the two arms disagree, re-run the disagreeing arm once.** Two runs total when the arms agree; three when they do not. *Counter:* even three runs is a small sample, and the honest ceiling of this measurement is "consistent with", not "demonstrates".

---

## Non-goals (explicit)

Prompt budget spent here is subtracted from the change. On every quality axis that does **not** depend on enumerating an unknown caller, v1.28 already led the benchmark field, **measured**: no duplicated logic where two competitors duplicated it; documentation maintained on methods it did not functionally change; a large mutation-proven test suite with surviving mutants closed; zero type-checker regression; and it was the only run to notice that a shared user-facing text key would publish a misleading hint on unrelated screens across every supported language.

**Do not spend prompt budget improving what is already won.** Specifically out of scope:

- **Improving discovery.** It scores 2/2. There is no headroom and this plan's whole thesis is that the gap is downstream of it.
- **Any of the other candidate mechanisms from the earlier survey**, until this one is measured. One thing, measured, is the method.
- **Strengthening the matrix into additional artifacts** — a second table, a companion checklist, a persisted report. If the matrix works, it works as one artifact; if it needs a companion to work, that is a finding for Phase 3 to report, not a phase to add.
- **Any change to the four review/verify commands.**
- **Any change to `DeadCodeRow`, `verify-dead-code-coverage`, `check-dead-code-removal`, or the `**Dead code removal**:` task field.** This plan feeds that chain; it does not touch it.
- **Any new agent.** The roster is 19 (plan 62).
- **Re-running or migrating the benchmark's source material** — it is the evidence record.
- **Settling the FALSE BINARY finding** (OQ-4). This plan may moot it, conditionally, and may not answer it.
- **[Added 2026-08-13.]** **A review-side question that reads the emission matrix rather than the ACs.** It is recorded as a follow-on and stays out of scope here, under the review/verify non-goal above **and** for measurement attribution — see *Recorded follow-on — the review-side question* in the amendment. It becomes a separate, separately-measured decision only if Phase 3 passes.
- **[Added 2026-08-13.]** **Any MECHANICAL detector of the inferred-intent AC** that R3's `/devforge:specify` directive addresses in prose — a solver check, a grep-shaped verifier, or equivalent. That possibility is recorded as a file-less finding in repo-root `CLAUDE.md`, not built here. **R3's directive itself is not covered by the review/verify non-goal:** `/devforge:specify` is not one of the four review/verify commands, and the directive adds no mechanism.

---

## The named risk to THIS plan — phase accumulation

The source proposal says: **ship ONE thing and measure it.**

This repo's plans have a documented tendency to accumulate phases. The index in repo-root `CLAUDE.md` carries multiple plans whose scope grew during execution — amendments added mid-build (a reviewer-driven amendment adding a mechanical gate to one plan; a work item resequenced into an earlier phase of another because a collision went live during drafting). Each accumulation was individually justified. The aggregate is the pattern, and this plan is written inside it.

**The concrete form the drift will take here:** Phase 2 will want to add a helper verb "while we're in there", or a completeness count "since the rows are already structured", or a second table for the rejected-alternative evidence of rule 5. Each is a defensible unit of work and each destroys the measurement, because a Phase 3 that measures four changes attributes nothing.

**Tripwire, stated as a Verify criterion in every build phase rather than as a note, because a note would not survive the pull:**

> **Any phase added beyond the ratified set must be justified against the MEASUREMENT, not against completeness.** "It would be more complete" is not a justification. "Phase 3 cannot be read without it" is.

A second tripwire, in the same spirit as plan 75's unnumbered-validator criterion: **no new mechanical check, verb, schema field or exit code is introduced by Phase 2** under the D4/OQ-3 recommended picks. If a build session finds itself needing one, it stops and returns to Phase 0 — because that is a different plan with a different measurement.

**[Amended 2026-08-13 — see Amendment *What this does to the accumulation tripwire*.]** R1–R3 enlarge Phase 2's file set from two files to three (four if the architect edit is taken) **without adding a mechanism**. Both tripwires above stand exactly as written and neither is relaxed: the second is untouched, and the first is met by a measurement argument — three of the four lock artifacts in the evidence are written at or after spec time — rather than by a completeness one. The amendment states that argument together with its counter, and names the test that falsifies it: **if the three edits cannot be written as one artifact's produce/consume path, the enlargement was accumulation and it returns to Phase 0.** *(The counts in this pointer record the delta at the moment of the amendment and are not criteria; the edit set Phase 2 names as amended is the single authority for which files that phase touches, and the falsification test applies to that set whatever its size.)*

---

## Build discipline

- `src/commands/plan/main.md` ships into a consumer's `.claude/commands/devforge/plan.md`, and `src/agents/architect.md` into `.claude/agents/architect.md`. **Both edits route through instruction-author → instruction-reviewer AND a claude-code-guide check.** No exception for size; the sub-question edit is one paragraph and still ships into `.claude/`.
- Any Python — which arrives only if OQ-3 or D4 is overridden — routes through **python-engineer → python-reviewer**, test-first.
- **Plan vocabulary NEVER ships into a consumer's `.claude/`.** "Visibility bar", "the reflex", "the discovery→action gap", D-numbers and this plan's phase numbers are maintainer vocabulary. The emitted text may reference only `/devforge:plan`'s own phases and sub-question numbers, and the constitution's own rule names.
- **The privacy constraint at the top of this file binds every phase, not just drafting.** No identifier from the benchmark's source codebase enters this file, any `src/` file, any commit message, or any test fixture. If an example is needed in emitted spec text, invent a neutral one — and verify the sentence still works: **if a sentence only works with a real identifier, rewrite the sentence.**
- Every load-bearing claim added during execution carries a `file:line` anchor **or** is marked an open item. Do not invent verb names, check numbers, counts or line numbers.
- **Re-verify every anchor in Verified state at use time.** They were correct on 2026-08-12 against an uncommitted working tree. A build-state claim about another in-flight plan in this repo has a half-life measured in hours (plan 75 records two of its own `[VERIFIED]` build-state claims going stale within a day).
- **[Added 2026-08-13 — see Amendment R1.]** `src/commands/research/main.md` and `src/commands/specify/main.md` ship into a consumer's `.claude/commands/devforge/` on the same terms as `src/commands/plan/main.md`, so **the instruction-author → instruction-reviewer + claude-code-guide loop binds every file in R1's re-scoped set** — with no exception for the single-sentence `/devforge:specify` directive, since size is not an exemption anywhere else in this list either.

---

## Phase 0 — Maintainer ratification (decision gate, no code)

Present this plan. The maintainer confirms, or overrides with a recorded reason:

**[Amended 2026-08-13 — see the amendment section.]** **R1, R2 and R3 are already ratified and are not re-opened here.** Their effect on the list below: **(a)** now covers **six** rules, R3 having added derived exclusions; **(g)** is **superseded in frame** — OQ-1's `/devforge:plan` sub-question home no longer has a subject, and what remains is confirming the research-side trigger wording; **(i)** is **resolved** to the `research-report.md` document section, with its counter carried unchanged. **(j)** carries the dated decision not to edit `src/constitution.md` before Phase 1, which is about timing and leaves OQ-4's recommendation itself still to ratify. Items **(b)–(f)**, **(h)**, **(k)** and **(l)** are unchanged and still require a recorded confirm-or-override, **as does the remainder of (a), (g), (i) and (j)**.

**[Amended 2026-08-15 — see Amendment A1, A2 and A3.]** **(b)**'s population mechanism is corrected by A3: the matrix carries no `dead` rows, so ratifying (b) ratifies that the matrix supplies the `affected` set the architect must account for while **sub-question 9 still derives every `### Change-Induced Dead Code` row from its own fresh trace** — the shipped chain is still fed unchanged, but by an obligation rather than by a row-to-row transform, and no `anchor_token` is ever lifted from a carried row. **(h)** asks the maintainer to ratify a guard-keyed column rule at a stage that has no guard and is answered by A2's re-keying; **(i)**'s resolution to a `research-report.md` section is falsified and re-resolved by A1 to a sibling file. All three still require a recorded confirm-or-override.

**[Amended 2026-08-15 (second) — see *Amendment 2026-08-15 (second)*.]** **This phase RAN and is RATIFIED 2026-08-15.** Every item below carries its recorded confirm-or-override there — including the **D5 override**, the **D6 retirement**, and the explicit recording that **OQ-4's ratification does NOT moot the FALSE BINARY finding** — and the "No `src/` file has been edited" criterion in Verify below is dated to the moment of ratification and superseded by Phase 2 landing.

(a) **D1** — the artifact shape and its five rules, including the five-column form and the rule-5 checkable-rejection requirement;
(b) **D2** — the relationship to sub-question 9: replace-and-widen (a), supersede-on-trigger (b, recommended), or two independent questions (c). **Ratifying (a) without also ratifying a widened matrix trigger ratifies a coverage loss** — the pick and its consequence go together. **Ratifying (b) also ratifies the population mechanism**, not only the trigger relationship: how a matrix `dead` row becomes a `### Change-Induced Dead Code` row (`file` from the row's `Call site` cell; `anchor_token`, `kind` and `why_dead` derived from that row's own trace evidence, per Phase 2). (b)'s whole claim is that the shipped chain is fed unchanged, and the two shapes do not map column-for-column, so the transform is part of what is being ratified;
(c) **D3** — that sub-question 7's in-scope-only output filtering is widened under every option, since that filtering is where the already-paid-for finding is discarded;
(d) **D4** — instruction-only v1, no Python, so that D6's delete branch is genuinely cheap;
(e) **D5** — measurement before build, with the honest counter that a gating measurement phase can slide and block everything behind it;
(f) **D6** — the delete branch is a first-class outcome and is written into Phase 3's Verify;
(g) **OQ-1** — trigger home, noting this plan **diverges from the originating brief's lean** and states its reason (belief-keyed vs fact-keyed trigger). A confirm-or-override here is required, not optional, because it decides where Phase 2's edit lands;
(h) **OQ-2** — both cardinality bounds: the guard-read-inputs-only column rule with its `varies` escape shape, and the identical-inputs equivalence-class row collapse;
(i) **OQ-3** — carrier: plan-document only (recommended) or handoff-carried. Interlocks with (d): a carrier pick makes the change no longer instruction-only and re-scopes Phase 2 to include a python loop;
(j) **OQ-4** — constitution unchanged (recommended), **and** the explicit recording that this plan may CLOSE the FALSE BINARY finding by mooting it only if Phase 3 passes, and closes nothing if it does not;
(k) **OQ-5** — that plan 69's wrong-symbol cross-check is carried by citation into the row-source instruction rather than re-invented;
(l) **OQ-6** — one run per arm, with the recorded bound and the disagreement re-run hedge.

Until ratification, no build phase is authored and Phase 1 does not run.

### Verify

- Every decision D1–D6 and every open question OQ-1–OQ-6 carries a recorded confirm-or-override, inline in this file.
- The D2 pick is recorded **together with its coverage consequence** — a bare "(b)" without the residual noted at D2(b) leaves the accepted gap unstated.
- The OQ-1 divergence is recorded as decided, not as noted.
- No `src/` file has been edited.
- **[Added 2026-08-13.]** R1–R3 count as recorded ratifications for what they decide, so the first criterion above is **satisfied by the amendment for those items and unsatisfied for every other one**. A Phase 0 that records only "R1–R3 confirmed" has not run.

---

## Phase 1 — Baseline measurement arm (user-driven, GATING)

**[Amended 2026-08-15 (second) — see *Amendment 2026-08-15 (second)*.]** **This phase is WAIVED, not deferred — it will not run.** No blind v2 baseline was ever taken, nothing below was executed, and none of its named outcomes landed; read the waiver's recorded cost before reading any claim this plan makes about its artifact.

**No `src/` edit precedes this phase.** This is the D5 inversion and it is the point of the plan.

Run the benchmark arm **blind**, on the **frozen prompt**, against **v2 as it stands** — no matrix, no Phase-2 edit, nothing added. Score the same two probes independently: did the run **discover** the hidden coupling, and did the run's change **handle** the hidden surface correctly.

Record the result against the four outcomes named in the measurement design. The pipeline artifacts the run produces are the evidence; record which of them named the hidden surface and which did not, because that detail is what Phase 3 compares against.

**Read the plan's own machinery as part of the baseline**, since it is the subject: whether the run's plan carries a `### Change-Induced Dead Code` subsection or the literal `renders nothing unreachable`; whether its Key Design Decisions record a caller-scoped or layer-wide Narrowing classification; and which callers its enumeration names. Those three facts, not just the probes, are what tell a later session whether the discovery→action framing survives contact with v2.

**[Amended 2026-08-13 — see Amendment R1 and R2.]** Two additions. Neither replaces anything above.

- **Score both probes under R2's criteria.** The handling probe passes only if the hidden surface stops emitting the removed values **without its file appearing in the diff**; a fix made by editing that file is recorded as **discovered-and-swept** and is **not a pass**, which means it does **not** satisfy the first of the four outcomes. Run the secondary signature check on this arm too — grep the run's own pipeline artifacts for any assertion that a value the ticket removes is still present or still emitted on some path — and record its result whichever way the arm lands. **Scoring the baseline under the same criteria as Phase 3 is what makes the before/after like-for-like**, so a baseline scored loosely invalidates the comparison rather than merely weakening it.
- **Read the research artifacts, not only the plan's.** Record whether the baseline run's research artifacts contain any emits-after-style analysis at all, and whether the hidden surface's classification survives from research into the plan. Under R1 the matrix is produced at `/devforge:research`, so those two facts are the baseline for the **production** site; the three plan-side facts above remain the baseline for the **consumption** site.

### Verify

- Both probes are scored, independently, with the run's artifacts kept as evidence.
- The outcome is mapped to one of the four named branches, explicitly — not summarized.
- **If the baseline handles the hidden surface, this plan STOPS.** Record the negative, close the plan, do not author Phase 2. The mechanism was unnecessary and that is the measurement working.
- **If the baseline neither discovers nor acts, this plan STOPS** and a sibling plan opens for the discovery regression. Phase 2 does not start.
- No `src/` file was edited during this phase.
- **[Added 2026-08-13 — R1/R2.]** The handling probe's score states explicitly **whether the hidden surface's file appears in the diff**, the secondary signature check's result is recorded, and the two research-side facts are recorded alongside the three plan-side ones. A **discovered-and-swept** result is recorded under that label rather than as a pass.

---

## Phase 2 — The artifact (instruction-author → instruction-reviewer + claude-code-guide)

**[Amended 2026-08-15 (second) — see *Amendment 2026-08-15 (second)*.]** **This phase SHIPPED 2026-08-15**, after Phase 0 ratified and **without** Phase 1, whose gap-confirmation condition below was removed by the waiver rather than met. **The landed edit set recorded there is the authority for what actually changed under `src/`**, and it carries one recorded divergence from the Verify criteria below.

Authored **only** after Phase 0 ratifies and Phase 1 confirms the gap. Both files ship into `.claude/`, so both take the full loop.

**[Amended 2026-08-13 — see Amendment R1 and R3. The file set is re-scoped and everything below moves to the consumption side.]** Production is at `/devforge:research`, so the edit set is:

- **`src/commands/research/main.md`** — **production.** The matrix section and its six rules, triggered when the recommended approach removes or suppresses an emitted value, written as a required section of `research-report.md`. Its row source is the caller enumeration already performed there.
  **[Amended 2026-08-15 — see Amendment A1.]** The landing file is a sibling `specs/<dirname>/emission-matrix.md` the orchestrator composes with Write, not a section of the helper-composed `research-report.md`; the production stage and row source are unchanged.
- **`src/commands/specify/main.md`** — **R3's companion directive.** Read the matrix section when writing acceptance criteria; an AC asserting continued presence of a value the ticket removes requires quoted product intent and may not be written from inferred intent.
- **`src/commands/plan/main.md`** — **consumption and verification.** Sub-question 7's already-mandated fresh inbound trace verifies the carried matrix is still current, and the matrix's `dead` rows populate sub-question 9's `### Change-Induced Dead Code` table by the transform stated below.
  **[Amended 2026-08-15 — see Amendment A3.]** The matrix carries no `dead` rows and there is no transform: it supplies the `affected` set the architect must account for, and sub-question 9 still derives the `### Change-Induced Dead Code` rows from its own fresh trace.
- **`src/agents/architect.md`** — the drafting session's call, and consumption-side only if taken.

**Everything below remains the specification of the consumption side**, including the population mechanism and rule 5's landing site. What changes is that the matrix **arrives carried** rather than being authored at `/devforge:plan`. **"Both files … so both take the full loop" above is superseded on its count only:** every file in this set takes the full loop (see Build discipline), and **this list is the single authority for which files Phase 2 touches** — every other count in this plan defers to it.

**[Amended 2026-08-15 — see Amendment A5.]** The `src/commands/plan/main.md` edit in this set also adds the carrier to the architect brief's file list, without which the consumption half silently no-ops; the set's membership is otherwise unchanged.

**Read the first bullet below accordingly.** Its "the sub-question carrying the matrix, at the home OQ-1 ratified" now describes the consumption-side sub-question that **reads and verifies** a carried matrix; OQ-1's home question is superseded in frame. **Whether the plan template still carries a matrix subsection of its own, or only cites the carried one, is a Phase-2 drafting question this amendment does not settle** — while D3's widening of sub-question 7's output, the PHASE-2.5 backstop step, the approval-summary line and the population mechanism below all stand as written.

- **`src/commands/plan/main.md`** — the sub-question carrying the matrix, at the home OQ-1 ratified, **appended** per the repo's append-never-renumber convention; a conditional plan-template subsection for the matrix, mirroring the shape and omit-condition of the existing conditional subsections (`### Pure-Builder Targets` at `:432`, `### Change-Induced Dead Code` at `:442`); a PHASE-2.5 read-side backstop step appended after step 7, mirroring step 7's shape (`:517`); a conditional line in the PHASE-3 approval summary, mirroring the existing conditional lines (`:536`–`:539`); and, per D3, the widening of sub-question 7's output so the full inbound-trace result survives to a table.
  - **[Amended 2026-08-13 — anchors re-verified, digits above are stale.]** On 2026-08-13, `### Pure-Builder Targets` is at `src/commands/plan/main.md:447` and `### Change-Induced Dead Code` at `:457` — not `:432` and `:442`. Per this file's own convention the **quoted heading is the real anchor and the digits are a dated hint**, which is why the stale pair is annotated rather than silently swapped: a corrected number leaves no trace that the anchors moved. **Only those two were re-verified.** Every other `:NNN` in this phase — `:517`, `:536`–`:539`, `:153`, `:418`–`:420`, `:350`, `:288`–`:291`, `:55` — carries its original 2026-08-12 date and must be re-grepped at use time.
  - **[Amended 2026-08-15 — see Amendment A5, and Amendment A6 for the refreshed digits.]** This bullet's edit list omits the architect brief's own file list, which must gain the carrier path or nothing reaches the architect to verify.
- **`src/agents/architect.md`** — a forcing step inside Rule 9 (`:153`), sitting beside the existing Narrowing and Consequence forcing steps and using their vocabulary. Under D2(b) it also states that a decision suppressing an emitted value answers sub-question 9 **from the matrix's dead rows**, not from a bare empty string.
  - **[Amended 2026-08-15 — see Amendment A3.]** The forcing step cannot answer sub-question 9 "from the matrix's dead rows" — there are none. It answers from sub-question 9's own fresh trace, with the matrix's `affected` rows as the set that must be accounted for. **The bare-empty-string point is unaffected:** a suppressing decision still may not answer with one.
  - **The population mechanism is stated explicitly, because the two shapes do not map column-for-column.** The matrix's columns are `Call site | Inputs it passes | Emits after the change | Verdict | Note`, while `DeadCodeRow` requires `file`, `anchor_token`, `kind` and `why_dead` (`src/devforge/lib/_plan/handoff_schema.py:288`–`:291`) — and **`anchor_token` and `kind` are derivable from no matrix column.** So the instruction must say: for every matrix row whose verdict is `dead`, the architect additionally records one `### Change-Induced Dead Code` row, taking `file` from that row's `Call site` cell and deriving `anchor_token`, `kind` and `why_dead` from the **same trace evidence already gathered to fill the row** — the `Note` cell, already required on a `dead` row, being the natural source for `why_dead`. `kind` stays the `arm | function | param | import | branch` enum sub-question 9 already defines (`plan/main.md:350`; `handoff_schema.py:55`): no new value, no new field, no new check. **Without this, Phase 2 can ship a matrix whose `dead` rows reach nothing** and still pass every other criterion below — the hollow-execution shape this plan exists to prevent.
    **[Amended 2026-08-15 — see Amendment A3.]** There is no carried `dead` verdict to transform: the matrix supplies the `affected` rows the architect must account for, and every `anchor_token` here comes from sub-question 9's own fresh trace, never from carried prose.
  - **A formatting judgment for the drafting session, not a ratification item and not a defect in this plan:** Rule 9 at `:153` already carries five distinct forcing concerns in one dense paragraph — minimal scope, out-of-scope respect, state cardinality, Narrowing, Consequence — and this adds a sixth. Whether the sixth warrants restructuring Rule 9 into sub-bullets is the instruction-author's call at drafting time, weighed against the repo's consistency-over-invention stance; it does not return to Phase 0 and it changes nothing above.
- **Rule 5's landing site** is the Key Design Decisions table's existing `Alternatives Rejected` column (`:418`–`:420`) — a rejection claiming impossibility must name the arguments the function actually receives and show the claim against them. **No new column and no new table**; the tripwire above forbids one.
- **Do not touch** sub-question 9's row shape, the `### Change-Induced Dead Code` table, `DeadCodeRow`, the `/devforge:breakdown` folding rule and its gate, or the `/devforge:verify` confirmation check. This phase feeds that chain and changes none of its contracts.

### Verify

- Instruction-reviewer clean; claude-code-guide clean; no plan vocabulary in the emitted text.
- **No new mechanical check, helper verb, schema field or exit code appears in the diff** — the accumulation tripwire. `git diff --stat` touches exactly two files under `src/`.
- Sub-question numbering is **appended**, not renumbered: every pre-existing sub-question keeps its number, and every cross-reference to a sub-question number elsewhere in `src/` still resolves. `grep -rn "sub-question" src/` reconciles against the file as landed.
- The dead-code chain is byte-unchanged: `grep -rn "DeadCodeRow\|verify-dead-code-coverage\|check-dead-code-removal\|Dead code removal" src/` returns the same set of files and the same claims as before the change.
- **The emitted text tells the architect how to POPULATE that unchanged shape**, not merely that it feeds it: the landed instruction states, for a matrix row whose verdict is `dead`, where `file`, `anchor_token`, `kind` and `why_dead` each come from. The criterion above checks the chain was not broken; this one checks it was actually connected — a matrix whose `dead` rows reach nothing fails this phase even when every other criterion passes.
- Cross-check sweep per this repo's discipline: every identifier, path and section number the edit touches is grepped repo-wide and no dangling reference or contradiction remains in another file.
- **No identifier from the benchmark's source codebase appears anywhere in the diff.**
- **[Added 2026-08-13 — R1. SUPERSEDES the bare count in the criterion above.]** **A correct R1-scoped Phase 2 would FAIL "exactly two files under `src/`", so that count is void as a criterion.** Replacement, still mechanical and still checkable: **`git diff --name-only` returns exactly the files named in the amended edit set at the head of this phase — no more and no fewer** — with `src/agents/architect.md` present if and only if the drafting session took that optional edit. Any file outside that set fails the phase regardless of how many files the diff touches. **No number is restated here, deliberately:** the edit set is stated once, at the head of this phase, and a count copied into a criterion is exactly what went stale the first time. The clause the original criterion carries — **no new mechanical check, helper verb, schema field or exit code in the diff** — binds unchanged and is what actually enforces the tripwire.
- **[Added 2026-08-13 — R3.]** The `/devforge:specify` directive is present and instruction-only: an AC asserting the continued presence of a value the ticket removes is refused unless product intent is quoted, and **no mechanical detector for that class appears in the diff**.
- **[Added 2026-08-13 — R1.]** The matrix's landing section in `research-report.md` is named identically in all three command files, and `grep -rn "<the section heading as landed>" src/` returns the production site and each consumer with no third spelling.
- **[Amended 2026-08-15 — see Amendment A1.]** The sibling-file carrier is what keeps the no-new-verb clause satisfiable at all — a `research-report.md` section would have cost a schema field, a setter verb and a `_render.py` change — and the landing-name criterion above reads against the sibling filename, not a section heading inside a helper-composed report.
- **[Amended 2026-08-15 — see Amendment A3. SUPERSEDES the POPULATE criterion's trigger above, and keeps its teeth.]** That criterion is keyed on "a matrix row whose verdict is `dead`", and the research matrix has none, so as written it can never fire. Replacement, same demand: **the landed instruction states, for every matrix row whose verdict is `affected`, that the architect must account for it at sub-question 9 — and that `file`, `anchor_token`, `kind` and `why_dead` all come from sub-question 9's own fresh trace of the code, never from a carried cell.** The teeth are unchanged: **a matrix whose `affected` rows reach nothing fails this phase even when every other criterion passes**, and an instruction that lets an `anchor_token` be lifted from a carried row fails it too, because a token that never came from the code cannot survive the verbatim exact-match downstream.

---

## Phase 3 — Measurement arm 2, and the delete branch (user-driven, HARD GATE)

**[Amended 2026-08-15 (second) — see *Amendment 2026-08-15 (second)*.]** **This phase is WAIVED, not deferred — it will not run.** No probe is scored, none of the three branches below lands, and **D6's delete branch is retired with it** — a branch that fires on a probe result cannot survive the probe's cancellation. The mechanism ships unmeasured; that cost is recorded there and is not softened.

Re-run the same benchmark arm, blind, on the **same frozen prompt**, with **only** the Phase-2 change relative to Phase 1's baseline. Score the same two probes.

**Read the result against Phase 1's baseline, not against v1.28's numbers.** The v1.28 figures are a different harness generation and are context, not control.

**[Amended 2026-08-13 — see Amendment R2.]** Both probes are scored under R2's criteria, identically to Phase 1's baseline. A handling-probe **pass** requires the hidden surface to stop emitting the removed values **without its file appearing in the diff**. A run that fixes it by editing that file is **discovered-and-swept**: it scores as **not a pass**, so it lands in the second branch below and **the revert fires**. The label exists to describe the result in the record — **not to open a third path around D6**. A partial outcome is exactly the shape a session reaches for to keep work alive, which is what D6's counter-argument already names. Run the secondary signature check on this arm as well and record its result whichever branch lands.

- **The handling probe flips (baseline fails it, matrix run passes it)** → the rule works, with a measured before/after on identical everything else. Proceed to Phase 4.
- **The handling probe does not flip** → **it is bloat. Revert Phase 2's two files.** Record the negative result in this file with the artifacts that show what the matrix contained and why it did not change the design. Close the plan. Under D6 this is an outcome, not a failure, and the plan is not to be kept alive by a reading of the result that preserves the work.
- **The matrix was not produced at all** (the sub-question fired and the artifact is absent or vacuous) → this is a **third result**, distinct from both: the instruction did not run. It says nothing about whether the artifact works, and it must not be read as either branch. The correct response is to establish why it did not run before re-running, and a failure to run twice is evidence about instruction placement, which is an OQ-1 question and returns to Phase 0.

**[Amended 2026-08-13 — see Amendment R1.]** "Revert Phase 2's two files" in the second branch names a count R1's re-scope makes wrong. Read it as **revert every file in the edit set Phase 2 names as amended** — all of it, in the same session as the reading, per the Verify criterion below. **The count is not what makes the branch cheap; instruction-only is** (D4), and that property is unchanged by the re-scope.

**One honest bound, recorded with whichever result lands:** a single run per arm cannot separate "the rule worked" from "this sample landed differently" (OQ-6). If the arms disagree, re-run the disagreeing arm once.

### Verify

- Both probes scored on the matrix run, with the artifacts kept.
- The result is mapped to one of the three branches above **explicitly**, and the OQ-6 bound is recorded alongside it.
- **If the probe did not flip, the revert is done in the same session as the reading** — not deferred, not left in the tree pending a second opinion.
- If the probe flipped, the run's matrix is quoted in this file (mechanism-only, identifiers stripped) as the record of what a filled matrix looks like.
- **[Added 2026-08-13 — R2.]** The handling probe's score states explicitly **whether the hidden surface's file appears in the diff**; a **discovered-and-swept** result is recorded under that label and treated as the no-flip branch; and the secondary signature check's result is recorded alongside the branch that landed.

---

## Phase 4 — Docs reconcile (conditional on Phase 3 passing)

Runs only on a flip.

- `CHANGELOG.md`; repo-root `CLAUDE.md` active-work entry.
- `src/CLAUDE.md`'s `/devforge:plan` one-liner **only if** the command's user-visible contract changed; if the matrix is an internal planning artifact with no change to what the user is asked at the approval gate, this file is untouched and that is recorded as a deliberate no-op.
- **OQ-4's conditional closure is written down here or nowhere:** if Phase 3 flipped and the maintainer ratified "no constitution change", the repo-root `CLAUDE.md` FALSE BINARY entry gains a pointer recording that this plan mooted it **without answering it** — the distinction is the whole content of that note.
- Cross-ref sweep: grep the new subsection heading, the sub-question number and any new vocabulary across `src/` and `tests/`; zero dangling.
- **[Added 2026-08-13 — R1.]** The `src/CLAUDE.md` bullet above reads across **R1's re-scoped set**, not `/devforge:plan` alone: the command whose user-visible contract is most likely to have changed is `/devforge:research`, since that is where the matrix is produced and where a user is asked for it. The same only-if-the-contract-changed test applies, and a deliberate no-op is still recorded as one.

### Verify

- Sweep returns zero dangling references; full test suite green (no test should have moved under D4, so a moved test is itself a finding).
- The FALSE BINARY note, if written, says **mooted, not answered**.
- No plan vocabulary leaked into any file under `src/`.

---

## Dependencies + related

- **Plan 71** (`71-POST-CHANGE-CONSEQUENCE-PLAN.md`) — **the direct predecessor and the machinery this plan feeds.** It built sub-question 9, the `### Change-Induced Dead Code` table, `DeadCodeRow`, the `/devforge:breakdown` folding rule and its coverage gate, and the `/devforge:verify` removal confirmation. **This plan's rule 4 is that plan, shipped.** What this plan adds is a source for the rows that is visibly wrong when unfilled — and its critique is narrow and specific: sub-question 9's *empty answer* is unfalsifiable. Nothing else in plan 71 is reopened.
- **Plan 67** (`67-CALLER-ENUMERATION-GATE-MODE-DECOUPLE-PLAN.md`) — made caller enumeration mode-independent at intake and gave `/devforge:plan` its typed caller-enumeration seed. It is one of the three post-baseline changes that make a v2 baseline necessary (D5).
- **Plan 69** (`69-CALLER-ENUM-RESIDUAL-HARDENING-PLAN.md`) — the exact-total declaration, per-caller scope classification, and the wrong-symbol trace hazard at `:50` that OQ-5 inherits. Also the honesty precedent this plan's rule 3 leans on: force the classification to exist, state openly that correctness cannot be forced.
- **Plan 66** (`66-PROPERTY-BASED-TESTING-AND-NARROWING-RULE-PLAN.md`) — authored the constitution's Narrowing rule that OQ-4 questions, and supplies the conditional-subsection template shape Phase 2 mirrors.
- **Plan 75** (`75-INVESTIGATION-SEARCH-HARNESS-PLAN.md`) — the sibling stance this plan is the mirror of. 75 argues that rigor is the floor and curiosity is the leverage, aimed at **discovery**; this plan takes discovery as already working and aims at **action**. Its standing-hazard section (gates are cheap to verify, search steps are not) applies here inverted: **this plan's artifact is checkable by a human reader and deliberately not by a machine**, which is why the accumulation tripwire forbids converting it into a check.
- **Plan 62 (D13)** — the fixed 2-pass quorum, and the repo's own precedent that a single stochastic pass is not a verdict. OQ-6's bound.
- **Plan 41** (`41-AGENT-EXECUTOR-REACHABILITY-PLAN.md`) — the orphan class OQ-3's recommendation avoids: a payload carried and consumed by nothing.
- **Plan 48** (`48-REVIEW-MANDATORY-GATE-PLAN.md`) — the shelving precedent D6's delete branch resembles: a real gap, written up in full, deliberately not built. The difference is that D6 deletes **after** a measurement rather than before a build, which is the stronger form.
- **The undrafted intake-rubric escape-flag finding** recorded in repo-root `CLAUDE.md` — cited by OQ-2 only for the **shape** of a justified escape versus a boolean one. That finding has no file and this plan does not take it up.
- **[Added 2026-08-13 — R1.]** **Plan 68** (`68-INTAKE-OWNS-FEATURE-DIR-PLAN.md`) — `/devforge:research` allocates `specs/NNN-<slug>/` at intake finalize and writes `research-report.md` inside it, which is what makes a research-side document carrier a per-feature artifact rather than a dated scratch report. **Plan 53** (`53-DESIGN-ANCHOR-FIRST-CLASS-PLAN.md`) — the **park-once, read-in-place** precedent R1's carrier pick follows: an artifact persisted once at intake and read in place downstream rather than re-carried through every handoff. And **plans 67 and 69 move from context to direct dependency** — their caller-enumeration machinery is the matrix's row source at the production site, not merely a reason a v2 baseline is needed.
- **[Added 2026-08-13.]** `77-EVIDENCE-DISCOVERY-TO-LOCK-INVERSION.md` — the maintainer-delivered handoff behind the amendment. **UNTRACKED, carries private-client identifiers, cited by filename only, never quoted into a tracked file.**

---

## Context for next session

**[Amended 2026-08-15 (second) — read this line first, ahead of the dated pointers below it, because it changes the plan's state rather than its content.]** **The plan is no longer NOT STARTED: Phase 0 is ratified, Phase 2 shipped into `src/`, and Phases 1 and 3 are WAIVED — not deferred, and they will not run.** Read *Amendment 2026-08-15 (second)* before this section and before the amendments it stacks after. **The traps below still bind, and the fourth — keeping a mechanism the probe did not validate — is now the plan's standing condition rather than a risk it guards against**, since there is no probe. The third trap's sentence *"v2 has never been run against this ticket"* is still true and is now permanent.

**[Amended 2026-08-13 — read *Amendment 2026-08-13* before this section; it re-scopes the phases below and supersedes one of the two divergences recorded further down.]** The governing sentence is unchanged, and the larger evidence set sharpens it into a mechanism: **this framework's blast-radius analysis has exactly one exit — protect — and no path to include; "shared code" resolves to "risk" and never to "consistency".** That is why the gap is discovery→action. It is also why the failure is not neutral: the harnesses that never looked left the defect **discoverable**, while this one left it **defended** — named in an out-of-scope list, pinned by a spec constraint, asserted by an acceptance criterion, and recommended for further pinning by a review.

**The one sentence that governs everything here:** this framework is the only harness that finds the hidden coupling, and it still designs as if it hadn't. **The gap is discovery→action, not discovery.** Any phase, sub-question or artifact proposed here that improves discovery is aimed at a probe that already scores 2/2 and is out of scope by construction.

**The first trap is building a preference.** The intrinsic-guard design is the right answer and it is tempting to just say so in the constitution or the architect's rules. The evidence says that loses: one losing run **explicitly rejected** the intrinsic approach in a single line, on a claim that was true of the symbol it named and irrelevant to the approach that works. A preference dies against one confident, unfalsifiable sentence. **The rejection has to be checkable, not discouraged** — that is rule 5, and it is why the plan proposes no preference at all.

**The second trap is adding artifacts.** Nine planning artifacts per run scored zero discoveries in three. Volume is not the constraint. Every candidate mechanism in this area gets held against the visibility bar — *does the rule produce an artifact that is visibly wrong when the analysis wasn't done?* — and two obvious candidates already fail it: "enumerate the consumers" (a list of consumers that must not change satisfies it) and a completeness count (a matrix with every row marked live passes a count and hides the defect).

**The third trap is treating "it's only a rewiring" as permission to skip Phase 1.** The rewiring claim is about build cost and it is probably true: the row source already exists in sub-question 7's mandated inbound trace, and the dead-row consumer already exists in plan 71's shipped chain. It says nothing about outcomes. **v2 has never been run against this ticket.** Every number in the Problem section is v1.28 from `main`, and three v2 changes landed after that baseline. A matrix that lands and then sees a passing probe has proven nothing about itself.

**The fourth trap is the one this plan is most likely to lose to: keeping a mechanism the probe did not validate.** D6 exists because a session that has just built something will find a reading of a null result that preserves it. The revert is written into Phase 3's Verify, in the same session as the reading, for that reason.

**Two things in this file diverge from the originating brief and must not be silently re-merged.** First, **OQ-1**: the brief leaned toward folding the matrix into sub-question 7; this plan recommends its own trigger, because sub-question 7's trigger is keyed on a **belief** about caller count and the matrix's is keyed on a **fact** about the change — and a wrong belief about caller count is the failure mode. Second, **D2**: the brief read the change as *replacing* sub-question 9, but sub-question 9's trigger is every Key Design Decision while the matrix's is value suppression, so a straight replace narrows the dead-code lane and orphans shipped machinery for kills that are not suppressions. Both are presented as forks for Phase 0, not as corrections.

**[Amended 2026-08-13 — see Amendment R1.]** Read that paragraph with R1 in hand. **OQ-1's fork is no longer live:** production moved to `/devforge:research`, so "own trigger versus fold into sub-question 7" has no subject as posed — though its belief-versus-fact reasoning survives and now grounds the research-side trigger. **D2's fork is still live** and still goes to Phase 0. More generally, **the whole file above was written against a `/devforge:plan` production site**; wherever it reads that way, the amendment is the correction, and no sentence above has been withdrawn to make it so.

**On what a passing Phase 3 would and would not settle.** It would show the artifact changed the design on one ticket, in one harness generation, on one run per arm. It would **not** show that it generalizes, and under OQ-4 it would moot the FALSE BINARY finding without answering it. Write the result in those terms; the repo's index already carries entries whose over-claimed status cost a later session real time.

**The working tree is uncommitted throughout** — several plans this file cites are working-tree state, so any "shipped" claim about them means reviewed-but-uncommitted, not released. Re-check each one from the code, separately, rather than from a Status line.

---

## When resuming work

1. Read this file in full, then **plan 71** (whose sub-question 9 and dead-code chain this plan rewires and must not break), then **plan 69** (whose wrong-symbol hazard OQ-5 inherits and whose honesty stance rule 3 borrows).
2. Re-verify every anchor in **Verified state** against the working tree. Line numbers drift and this repo has documented anchor rot; grep the quoted strings — `renders nothing unreachable`, `Change-Induced Dead Code`, `direction=inbound`, `anchor token`, `No dead code` — never the `:NNN`.
3. **Re-confirm the sub-question count before drafting.** `plan/main.md` carried sub-questions 1–10 on 2026-08-12 and the convention is **append, never renumber** (plan 73 appended 10 for exactly this reason). If another in-flight plan appended one first, this plan's lands after it — and any phase text naming a number is re-checked against the file as landed, not against this file.
4. Start at **Phase 0**. Items (b), (g), (i) and (j) each decide the shape of a phase below; leaving any of them to executor discretion re-opens it mid-build. **[Amended 2026-08-13.]** **R1, R2 and R3 are already decided** — read *Amendment 2026-08-13* first, since R1 moves production to `/devforge:research` and re-scopes Phase 2's file set, which changes what (b), (g) and (i) are even about. **(g)** and **(i)** are settled there, **(a)** now covers six rules, and **(j)** carries only a timing decision; **Phase 0 confirms the remainder** — (b)–(f), (h), (k), (l) and the unsettled part of (a), (g), (i) and (j). Before drafting Phase 2, read `src/commands/research/main.md` in full: this file verifies nothing about that site beyond five verb names and one document name.
   **[Amended 2026-08-15.]** Read *Amendment 2026-08-15* after *Amendment 2026-08-13*: A1's sibling-file carrier is ratified and replaces R1's `research-report.md` section, while **A2–A6 are Phase-0 items** carrying no ratification of their own.
5. **Do not start Phase 2 before Phase 1 has run and been read.** Two of Phase 1's four outcomes close this plan without any `src/` edit at all, and both of those are successes of the method.
6. Re-read the privacy constraint at the top before writing a single sentence into this file or into any `src/` file. It binds execution, not just drafting.
