# 77 — Post-Change Output Matrix: closing the discovery→action gap

**Status:** **NOT STARTED — decisions drafted, awaiting Phase-0 ratification.** No code, no `src/` edit, no `main.md` edit, no `src/agents/` edit has been made for this plan. Every decision below is a recommendation carrying its counter-argument.
**Type:** DESIGN + BUILD plan, with a **measurement arm that gates the build** (Phase 1) and a **measurement arm that decides whether the build survives** (Phase 3). The phase order is deliberately inverted relative to this repo's norm — see D5.
**Branch:** `develop-2.0-init`
**Created:** 2026-08-12.
**Privacy constraint governing this file:** the originating evidence is a benchmark against a private client codebase. This file is **mechanism-only**. It contains no ticket ID, commit SHA, branch name, company or product name, feature name, source symbol, function name, parameter name, component name, file path or enum value from that codebase, and none may be added. Where an example is needed, it is invented and neutral. `CHANGELOG.md:32` records that plan docs are exempt from the identifier scrub; that exemption covers pre-existing historical references in other files and licenses nothing new here. Any identifier introduced into this file is a hard error, not a style nit.

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

## The proposed change

### The artifact

For any decision that **removes or suppresses an emitted value**, require this artifact BEFORE the decision is recorded:

A **post-change output matrix** for the function being changed, **one row per call site**:

| Call site (file:line) | Inputs it passes | Emits after the change | Verdict | Note |
|---|---|---|---|---|
| [caller path + line] | [the inputs the proposed guard reads] | [traced, not asserted] | live / dead | [required when the row still emits the value being removed, or when the verdict is dead] |

The decision table's `Why` column then **cites matrix rows** rather than restating them.

### The five rules

1. **Every call site appears**, found mechanically and cited by file and line. No sampling.
2. **The "emits after" cell is evaluated per row against the proposed change — traced, not asserted.**
3. **Any row that still emits the value being removed must be justified in one sentence, or the design is wrong.**
4. **If a branch becomes unreachable, the constitution's No-dead-code rule applies: delete it, do not guard it.**
5. **Any alternative rejected as impossible must name the arguments the function actually receives and show the claim against them.**

Rule 5 is the direct answer to the one-line unfalsifiable rejection described above. Rule 4 is already built (see Verified state) and this plan reuses it rather than rebuilding it.

**Rule 1's honest bound — an accepted residual, not a solved problem.** Rules 2, 3 and 5 clear the visibility bar on **content** grounds: a cell that is filled wrongly reads wrong. Rule 1 cannot clear it that way, because it is an enumeration-completeness rule — the same shape as the "enumerate the consumers" candidate rejected above. **A silently missing row is indistinguishable from a complete matrix to a human at the approval gate:** when the mandated inbound trace fails to surface a call site (graph incompleteness, dynamic dispatch, reflection, an indirect call pattern), nothing in the artifact reads wrong. So rule 1's completeness is bounded by the completeness of the mechanical enumeration it rests on, and it is **not independently checkable by the reader**. *This is distinct from D4's counter,* which is that nothing mechanically checks the matrix against a known call-site count; this bound holds even when the matrix faithfully transcribes a trace that looked complete. **Rule 1 stays as written** — a mechanically-sourced enumeration is strictly better than none, and it is the floor the other rules stand on — but it is a floor, not a self-verifying artifact, and this bound is accepted rather than closed. OQ-5 records the one narrower, named instance of it.

### Why this yields the right design without naming it

Filling the matrix honestly makes a wrong row **self-evident**. A row showing an unintended caller still emitting the removed value needs no design principle to look wrong — and **the only change that flips that row without editing that caller is the intrinsic one**: a guard keyed on state the function already receives. Rule 4 then closes it: once the branch is unreachable, deletion is required rather than a guard.

This is why the plan proposes **no new preference rule**. The preference is a consequence of the artifact, not an instruction the artifact carries. See OQ-4 for what that implies about the constitution.

---

## Verified state (2026-08-12)

Verified against the working tree this session by reading the files, not by trusting the originating brief or any plan's Status line. **Line numbers drift — grep the quoted tokens.** This repo has documented anchor rot (plan 75 records plan 73 re-keying its own anchors six times), so every `:NNN` below is a dated hint and the quoted string is the real anchor.

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

### Nothing matrix-shaped exists

`grep -niE "matrix|live or dead|reachability|call site" src/commands/plan/main.md` → **0 hits.** Widening the pattern to include `post-change` returns exactly **one** line, `:350`, inside sub-question 9's own anchor-token definition. The read-side backstops at PHASE 2.5 run steps 1–7 (`:507`–`:517`); step 7 is the Narrowing backstop and mirrors step 6's shape.

### The structural reading — state it, but do not treat it as established

The matrix sits at the **join of two existing sub-questions**: its **row source** is sub-question 7's already-mandated inbound trace, and its **dead rows** feed sub-question 9's shipped downstream machinery unchanged — though **not column-for-column**: the two shapes differ, so the row-to-row transform is something Phase 2 must state rather than something the join supplies for free. On that reading the change is substantially a **rewiring**, not new construction.

**Do not treat "it's only a rewiring" as a reason to skip Phase 1.** The rewiring claim describes build cost. It says nothing about whether the artifact changes the outcome, and the measurement warning below is about exactly that.

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

---

## Decisions (ratify at Phase 0 — each carries its counter-argument)

### D1 — The artifact and its five rules, as stated above

What is being ratified is the **shape**: five columns, one row per call site, five rules, `Why` cites rows.

*Counter-argument, recorded:* a five-column table is more structure than any other single sub-question in PHASE 1.3 produces, and the repo's own evidence (the nine-artifact harness scoring 0/3) is that structure volume does not buy outcomes. The defence is that this artifact is selected against the visibility bar and the nine were not — but that defence is an argument, not a measurement, which is why Phase 3 exists.

### D2 — Relationship to sub-question 9

Three options, and the pick has a coverage consequence that must be decided here rather than discovered mid-build.

- **(a) Replace.** The matrix subsumes sub-question 9. *Cost:* sub-question 9's trigger is **every Key Design Decision**; the matrix's trigger is decisions that remove or suppress an emitted value. Those are different sets. A straight replace **narrows** the dead-code lane and orphans the shipped `DeadCodeRow` → `verify-dead-code-coverage` → `check-dead-code-removal` chain for every kill that is not a value suppression (removing a call, deleting a flag branch). Making (a) coherent requires widening the matrix's trigger to every decision, which converts it into a per-decision artifact and walks straight into OQ-2's cardinality problem.
- **(b) Supersede on the trigger — RECOMMENDED.** Sub-question 9 stays as the general kill-declaration question. What changes is that its bare empty answer is **no longer accepted** for a decision that removes or suppresses an emitted value: for those decisions the matrix is the required evidence, and the matrix's `dead` rows are what populate the existing `### Change-Induced Dead Code` table — by an explicit transform Phase 2 states, since the two shapes do not map column-for-column. *Why:* the documented failure is specifically that the **empty answer** is unfalsifiable, not that the question is wrong. This targets the failure and leaves the general trigger and the whole downstream chain byte-unchanged. *Counter:* it leaves sub-question 9's weak empty answer in force for every decision outside the suppression trigger — a real, knowingly-accepted residual.
- **(c) Two independent questions**, unrelated. *Cost:* two adjacent questions a reader must distinguish under time pressure, with overlapping subject matter and no stated relationship — the exact reader burden OQ-1 is about.

### D3 — Sub-question 7's output filtering is widened under EVERY option

Independent of D2 and OQ-1: `plan/main.md:348`'s in-scope-only output for the caller-scoped branch is where the hidden surface is lost after being found. **The full inbound-trace result must survive to a table.** This is not one of the options — every option depends on it, because without it the matrix has no honest row source.

*Counter:* widening the output makes sub-question 7's answer longer for every restricting decision, including the ones with a large caller set. That is the same cardinality pressure as OQ-2 and takes the same answer.

### D4 — Instruction-only v1; no Python, so deletion is cheap

Under D2(b) + OQ-3's recommended answer, the entire change is **two markdown files**: `src/commands/plan/main.md` (a sub-question, a conditional template subsection, a PHASE-2.5 read-side backstop step, an approval-summary line) and `src/agents/architect.md` (a forcing step inside Rule 9). No schema field, no helper verb, no parser.

*Why it matters:* the measurement design requires that deletion be genuinely cheap, or the sunk-cost pull will keep a mechanism the probe did not validate. Two markdown reverts is cheap; a schema field with back-compat tests and a parser is not.

*Counter:* an instruction-only artifact cannot be mechanically checked for completeness — nothing stops a three-row matrix on a five-caller function. The bar's own reasoning absorbs most of this (a completeness count fails the bar anyway), but not all of it, and the residual is real. If OQ-3 flips to a carrier, Python enters via `_plan/handoff_schema.py` + `plan_helper finalize-handoff`, and the loop becomes python-engineer → python-reviewer as well.

### D5 — Measure before building; the baseline arm gates

Phase 1 is a measurement phase that runs **before** any `src/` edit. This inverts this repo's near-universal convention, in which the consumer/testForge20 e2e is the LAST phase and the build precedes it.

*Why:* without a v2 baseline, a passing Phase 3 is unattributable, and an unattributable pass is what keeps unmeasured mechanisms alive forever.

*Counter:* the inversion costs a real run before there is anything to show for it, and the repo's own history shows e2e phases sliding (numerous plans carry a deferred user-driven e2e). A Phase 1 that slides blocks everything behind it — where a trailing e2e that slides at least leaves shipped code. That is the honest trade, and it is the maintainer's to make.

### D6 — The delete branch is a first-class outcome, not a failure

If Phase 3's probe does not flip, Phase 2's two edits are reverted and this plan closes as a **measured negative**. A measured negative about a plausible mechanism is a durable output: it removes a candidate from the survey permanently and tells the next plan where not to look.

*Counter:* none on the merits. The risk is not intellectual, it is behavioural — a session that has just built something will look for a reading of the result that keeps it. That is why the delete branch is written into Phase 3's Verify rather than left as a sentiment.

---

## Open questions

- **OQ-1 — Where the trigger lives, and it does not nest cleanly.** Sub-question 7 fires on "restricts existing behavior of shared code"; the matrix fires on "removes or suppresses an emitted value". **Suppressing an emitted value is always a restriction, but a restriction is not always a suppressed value — the sets overlap without one containing the other.**

  *The originating brief's lean:* widen sub-question 7's output rather than add a second adjacent trigger a reader must distinguish under time pressure, since 7 already pays the enumeration cost.

  *This plan's recommendation diverges, and the reason is specific:* **sub-question 7's trigger is keyed on a belief, and the matrix's trigger is keyed on a fact.** `constitution.md:121` and `plan/main.md:348` define shared code as code "with multiple callers" — so a decision only fires sub-question 7 if its author already believes the function has more than one caller. **A belief about caller count is exactly what is wrong in the failure mode this plan exists for.** The author of the losing design believed it was wiring the one caller that mattered. By contrast, "does this change remove or suppress a value the function emits?" is a property of the change the author knows for certain before tracing anything.

  So the recommendation is **(b) the matrix carries its own trigger, keyed on the change, and reuses sub-question 7's enumeration as its row source** — appended as sub-question 11 per the repo's append-never-renumber convention (plan 73 appended sub-question 10 for this reason; `plan/main.md` currently runs 1–10 at `:342`–`:351`).

  *Counter, which is real and is the brief's:* two adjacent questions about overlapping subject matter is a reader cost, and under time pressure a reader distinguishes them wrongly or answers one twice. **Option (a) remains fully viable** and its cost is bounded: folding into 7 loses only the single-caller-belief case, which is arguably rare — except that it is the observed case. Maintainer decides; this is flagged as a divergence from the brief's lean, not as a settled reading.

  Under **all three** options, D3 holds: 7's output filtering is widened regardless.

- **OQ-2 — Cardinality. What bounds a row, and what bounds "relevant state"?** Callers × relevant states explodes for a widely-used helper, and **an unfillable artifact gets waived or filled reflexively** — which is the visibility bar failing in a new way rather than a new mechanism working.

  Two separate bounds are needed and they are not the same question:

  *(i) What goes in the "inputs it passes" cell.* **Recommendation: only the inputs the proposed guard condition READS**, never the caller's full argument list. Column width is then bounded by the guard's arity, not the function's. When a caller's value for a guard-read input is not statically determinable, the cell reads `varies` and the "emits after" cell must cover **both** branches, defaulting the verdict to `live`. *Counter:* `varies` is a cheap blanket escape and could swallow the whole matrix — which is the same shape as the finding recorded at repo-root `CLAUDE.md` about a blanket rubric escape flag versus the justified-escape shape the same helper package already uses elsewhere. Mitigation: a `varies` cell must state which values were considered, making it a justified escape rather than a boolean one.

  *(ii) How many rows.* Plan 69's OQ-4 probe observed a depth-1 inbound trace returning the full caller set for a function with in-degree 47; a 47-row matrix is unfillable in practice. Options: no cap and accept the cost; a cap with an explicit overflow declaration; or **row-collapse by equivalence class — recommended:** callers passing **identical** guard-read inputs collapse into one row that still enumerates every collapsed call site's `file:line`, so completeness is preserved and row count is bounded by distinct input shapes. *Counter:* collapsing is itself a judgment, and the caller that differs is precisely the one that wants its own row. Mitigation: collapse is permitted only on **identical** inputs — any difference in any guard-read input forces a separate row. This preserves the property the whole design rests on, that a wrongly-filled row reads wrong on its face.

- **OQ-3 — Carrier.** Does the matrix ride the plan→breakdown handoff, or is it a plan-document artifact the human reads at the approval gate? *Recommendation: **plan-document only for v1**.* The `dead` rows continue to carry through the **existing** `DeadCodeRow` / `BreakdownSeeds.dead_code_rows` path with no schema change. Reasons: nothing at `/devforge:breakdown` or `/devforge:verify` consumes a **live** row, so carrying one creates the same shape plan 41 named for agents, steps and findings, applied here to a schema field; and it keeps D4's cheap-deletion property, which the measurement design depends on. *Counter:* a document-only artifact is unverifiable downstream, so no mechanism prevents a short matrix. Partially absorbed by the bar (a completeness count fails it anyway) and partially real. If a downstream consumer ever appears, the carrier is a later, separable change.

- **OQ-4 — Does the constitution need changing at all?** Repo-root `CLAUDE.md` records a live, explicitly-unsettled finding that the constitution's Narrowing rule may present a **FALSE BINARY**: `src/constitution.md:122` names a **caller-scoped opt-in** and `:124` a **layer-wide policy change**, and does not name **deriving the restricting condition inside the shared function from arguments it already receives** as a first-class third form. The enumeration-independent form surfaces only inside the fallback arm at `:123` — reachable only when the needing-caller set cannot be established — and then inherits `:124`'s obligation to name every current caller. **That third form is exactly what won the benchmark.**

  The obvious response is to add it as a third form. *Recommendation: **no constitution change**,* on the grounds that this plan's own central evidence is that taste instructions lose against one confident sentence, and the matrix makes the right form self-evident without naming it. **If that holds, this plan CLOSES the FALSE BINARY finding by making it moot rather than by answering it** — and that closure is **conditional on Phase 3 passing**. If Phase 3 fails and D6's delete branch fires, the finding is untouched and still open; nothing in this plan may be read as having settled it.

  *Counter, which is not weak:* §3.6's rules are not purely taste — they are cited by `plan/main.md:348`, by `plan/main.md:517`'s PHASE-2.5 backstop and by `architect.md:153`'s Narrowing forcing step, so a rule naming only two forms **actively steers** toward one of them at three enforcement sites. "No change" is therefore not costless. Maintainer decision.

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

---

## The named risk to THIS plan — phase accumulation

The source proposal says: **ship ONE thing and measure it.**

This repo's plans have a documented tendency to accumulate phases. The index in repo-root `CLAUDE.md` carries multiple plans whose scope grew during execution — amendments added mid-build (a reviewer-driven amendment adding a mechanical gate to one plan; a work item resequenced into an earlier phase of another because a collision went live during drafting). Each accumulation was individually justified. The aggregate is the pattern, and this plan is written inside it.

**The concrete form the drift will take here:** Phase 2 will want to add a helper verb "while we're in there", or a completeness count "since the rows are already structured", or a second table for the rejected-alternative evidence of rule 5. Each is a defensible unit of work and each destroys the measurement, because a Phase 3 that measures four changes attributes nothing.

**Tripwire, stated as a Verify criterion in every build phase rather than as a note, because a note would not survive the pull:**

> **Any phase added beyond the ratified set must be justified against the MEASUREMENT, not against completeness.** "It would be more complete" is not a justification. "Phase 3 cannot be read without it" is.

A second tripwire, in the same spirit as plan 75's unnumbered-validator criterion: **no new mechanical check, verb, schema field or exit code is introduced by Phase 2** under the D4/OQ-3 recommended picks. If a build session finds itself needing one, it stops and returns to Phase 0 — because that is a different plan with a different measurement.

---

## Build discipline

- `src/commands/plan/main.md` ships into a consumer's `.claude/commands/devforge/plan.md`, and `src/agents/architect.md` into `.claude/agents/architect.md`. **Both edits route through instruction-author → instruction-reviewer AND a claude-code-guide check.** No exception for size; the sub-question edit is one paragraph and still ships into `.claude/`.
- Any Python — which arrives only if OQ-3 or D4 is overridden — routes through **python-engineer → python-reviewer**, test-first.
- **Plan vocabulary NEVER ships into a consumer's `.claude/`.** "Visibility bar", "the reflex", "the discovery→action gap", D-numbers and this plan's phase numbers are maintainer vocabulary. The emitted text may reference only `/devforge:plan`'s own phases and sub-question numbers, and the constitution's own rule names.
- **The privacy constraint at the top of this file binds every phase, not just drafting.** No identifier from the benchmark's source codebase enters this file, any `src/` file, any commit message, or any test fixture. If an example is needed in emitted spec text, invent a neutral one — and verify the sentence still works: **if a sentence only works with a real identifier, rewrite the sentence.**
- Every load-bearing claim added during execution carries a `file:line` anchor **or** is marked an open item. Do not invent verb names, check numbers, counts or line numbers.
- **Re-verify every anchor in Verified state at use time.** They were correct on 2026-08-12 against an uncommitted working tree. A build-state claim about another in-flight plan in this repo has a half-life measured in hours (plan 75 records two of its own `[VERIFIED]` build-state claims going stale within a day).

---

## Phase 0 — Maintainer ratification (decision gate, no code)

Present this plan. The maintainer confirms, or overrides with a recorded reason:

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

---

## Phase 1 — Baseline measurement arm (user-driven, GATING)

**No `src/` edit precedes this phase.** This is the D5 inversion and it is the point of the plan.

Run the benchmark arm **blind**, on the **frozen prompt**, against **v2 as it stands** — no matrix, no Phase-2 edit, nothing added. Score the same two probes independently: did the run **discover** the hidden coupling, and did the run's change **handle** the hidden surface correctly.

Record the result against the four outcomes named in the measurement design. The pipeline artifacts the run produces are the evidence; record which of them named the hidden surface and which did not, because that detail is what Phase 3 compares against.

**Read the plan's own machinery as part of the baseline**, since it is the subject: whether the run's plan carries a `### Change-Induced Dead Code` subsection or the literal `renders nothing unreachable`; whether its Key Design Decisions record a caller-scoped or layer-wide Narrowing classification; and which callers its enumeration names. Those three facts, not just the probes, are what tell a later session whether the discovery→action framing survives contact with v2.

### Verify

- Both probes are scored, independently, with the run's artifacts kept as evidence.
- The outcome is mapped to one of the four named branches, explicitly — not summarized.
- **If the baseline handles the hidden surface, this plan STOPS.** Record the negative, close the plan, do not author Phase 2. The mechanism was unnecessary and that is the measurement working.
- **If the baseline neither discovers nor acts, this plan STOPS** and a sibling plan opens for the discovery regression. Phase 2 does not start.
- No `src/` file was edited during this phase.

---

## Phase 2 — The artifact (instruction-author → instruction-reviewer + claude-code-guide)

Authored **only** after Phase 0 ratifies and Phase 1 confirms the gap. Both files ship into `.claude/`, so both take the full loop.

- **`src/commands/plan/main.md`** — the sub-question carrying the matrix, at the home OQ-1 ratified, **appended** per the repo's append-never-renumber convention; a conditional plan-template subsection for the matrix, mirroring the shape and omit-condition of the existing conditional subsections (`### Pure-Builder Targets` at `:432`, `### Change-Induced Dead Code` at `:442`); a PHASE-2.5 read-side backstop step appended after step 7, mirroring step 7's shape (`:517`); a conditional line in the PHASE-3 approval summary, mirroring the existing conditional lines (`:536`–`:539`); and, per D3, the widening of sub-question 7's output so the full inbound-trace result survives to a table.
- **`src/agents/architect.md`** — a forcing step inside Rule 9 (`:153`), sitting beside the existing Narrowing and Consequence forcing steps and using their vocabulary. Under D2(b) it also states that a decision suppressing an emitted value answers sub-question 9 **from the matrix's dead rows**, not from a bare empty string.
  - **The population mechanism is stated explicitly, because the two shapes do not map column-for-column.** The matrix's columns are `Call site | Inputs it passes | Emits after the change | Verdict | Note`, while `DeadCodeRow` requires `file`, `anchor_token`, `kind` and `why_dead` (`src/devforge/lib/_plan/handoff_schema.py:288`–`:291`) — and **`anchor_token` and `kind` are derivable from no matrix column.** So the instruction must say: for every matrix row whose verdict is `dead`, the architect additionally records one `### Change-Induced Dead Code` row, taking `file` from that row's `Call site` cell and deriving `anchor_token`, `kind` and `why_dead` from the **same trace evidence already gathered to fill the row** — the `Note` cell, already required on a `dead` row, being the natural source for `why_dead`. `kind` stays the `arm | function | param | import | branch` enum sub-question 9 already defines (`plan/main.md:350`; `handoff_schema.py:55`): no new value, no new field, no new check. **Without this, Phase 2 can ship a matrix whose `dead` rows reach nothing** and still pass every other criterion below — the hollow-execution shape this plan exists to prevent.
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

---

## Phase 3 — Measurement arm 2, and the delete branch (user-driven, HARD GATE)

Re-run the same benchmark arm, blind, on the **same frozen prompt**, with **only** the Phase-2 change relative to Phase 1's baseline. Score the same two probes.

**Read the result against Phase 1's baseline, not against v1.28's numbers.** The v1.28 figures are a different harness generation and are context, not control.

- **The handling probe flips (baseline fails it, matrix run passes it)** → the rule works, with a measured before/after on identical everything else. Proceed to Phase 4.
- **The handling probe does not flip** → **it is bloat. Revert Phase 2's two files.** Record the negative result in this file with the artifacts that show what the matrix contained and why it did not change the design. Close the plan. Under D6 this is an outcome, not a failure, and the plan is not to be kept alive by a reading of the result that preserves the work.
- **The matrix was not produced at all** (the sub-question fired and the artifact is absent or vacuous) → this is a **third result**, distinct from both: the instruction did not run. It says nothing about whether the artifact works, and it must not be read as either branch. The correct response is to establish why it did not run before re-running, and a failure to run twice is evidence about instruction placement, which is an OQ-1 question and returns to Phase 0.

**One honest bound, recorded with whichever result lands:** a single run per arm cannot separate "the rule worked" from "this sample landed differently" (OQ-6). If the arms disagree, re-run the disagreeing arm once.

### Verify

- Both probes scored on the matrix run, with the artifacts kept.
- The result is mapped to one of the three branches above **explicitly**, and the OQ-6 bound is recorded alongside it.
- **If the probe did not flip, the revert is done in the same session as the reading** — not deferred, not left in the tree pending a second opinion.
- If the probe flipped, the run's matrix is quoted in this file (mechanism-only, identifiers stripped) as the record of what a filled matrix looks like.

---

## Phase 4 — Docs reconcile (conditional on Phase 3 passing)

Runs only on a flip.

- `CHANGELOG.md`; repo-root `CLAUDE.md` active-work entry.
- `src/CLAUDE.md`'s `/devforge:plan` one-liner **only if** the command's user-visible contract changed; if the matrix is an internal planning artifact with no change to what the user is asked at the approval gate, this file is untouched and that is recorded as a deliberate no-op.
- **OQ-4's conditional closure is written down here or nowhere:** if Phase 3 flipped and the maintainer ratified "no constitution change", the repo-root `CLAUDE.md` FALSE BINARY entry gains a pointer recording that this plan mooted it **without answering it** — the distinction is the whole content of that note.
- Cross-ref sweep: grep the new subsection heading, the sub-question number and any new vocabulary across `src/` and `tests/`; zero dangling.

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

---

## Context for next session

**The one sentence that governs everything here:** this framework is the only harness that finds the hidden coupling, and it still designs as if it hadn't. **The gap is discovery→action, not discovery.** Any phase, sub-question or artifact proposed here that improves discovery is aimed at a probe that already scores 2/2 and is out of scope by construction.

**The first trap is building a preference.** The intrinsic-guard design is the right answer and it is tempting to just say so in the constitution or the architect's rules. The evidence says that loses: one losing run **explicitly rejected** the intrinsic approach in a single line, on a claim that was true of the symbol it named and irrelevant to the approach that works. A preference dies against one confident, unfalsifiable sentence. **The rejection has to be checkable, not discouraged** — that is rule 5, and it is why the plan proposes no preference at all.

**The second trap is adding artifacts.** Nine planning artifacts per run scored zero discoveries in three. Volume is not the constraint. Every candidate mechanism in this area gets held against the visibility bar — *does the rule produce an artifact that is visibly wrong when the analysis wasn't done?* — and two obvious candidates already fail it: "enumerate the consumers" (a list of consumers that must not change satisfies it) and a completeness count (a matrix with every row marked live passes a count and hides the defect).

**The third trap is treating "it's only a rewiring" as permission to skip Phase 1.** The rewiring claim is about build cost and it is probably true: the row source already exists in sub-question 7's mandated inbound trace, and the dead-row consumer already exists in plan 71's shipped chain. It says nothing about outcomes. **v2 has never been run against this ticket.** Every number in the Problem section is v1.28 from `main`, and three v2 changes landed after that baseline. A matrix that lands and then sees a passing probe has proven nothing about itself.

**The fourth trap is the one this plan is most likely to lose to: keeping a mechanism the probe did not validate.** D6 exists because a session that has just built something will find a reading of a null result that preserves it. The revert is written into Phase 3's Verify, in the same session as the reading, for that reason.

**Two things in this file diverge from the originating brief and must not be silently re-merged.** First, **OQ-1**: the brief leaned toward folding the matrix into sub-question 7; this plan recommends its own trigger, because sub-question 7's trigger is keyed on a **belief** about caller count and the matrix's is keyed on a **fact** about the change — and a wrong belief about caller count is the failure mode. Second, **D2**: the brief read the change as *replacing* sub-question 9, but sub-question 9's trigger is every Key Design Decision while the matrix's is value suppression, so a straight replace narrows the dead-code lane and orphans shipped machinery for kills that are not suppressions. Both are presented as forks for Phase 0, not as corrections.

**On what a passing Phase 3 would and would not settle.** It would show the artifact changed the design on one ticket, in one harness generation, on one run per arm. It would **not** show that it generalizes, and under OQ-4 it would moot the FALSE BINARY finding without answering it. Write the result in those terms; the repo's index already carries entries whose over-claimed status cost a later session real time.

**The working tree is uncommitted throughout** — several plans this file cites are working-tree state, so any "shipped" claim about them means reviewed-but-uncommitted, not released. Re-check each one from the code, separately, rather than from a Status line.

---

## When resuming work

1. Read this file in full, then **plan 71** (whose sub-question 9 and dead-code chain this plan rewires and must not break), then **plan 69** (whose wrong-symbol hazard OQ-5 inherits and whose honesty stance rule 3 borrows).
2. Re-verify every anchor in **Verified state** against the working tree. Line numbers drift and this repo has documented anchor rot; grep the quoted strings — `renders nothing unreachable`, `Change-Induced Dead Code`, `direction=inbound`, `anchor token`, `No dead code` — never the `:NNN`.
3. **Re-confirm the sub-question count before drafting.** `plan/main.md` carried sub-questions 1–10 on 2026-08-12 and the convention is **append, never renumber** (plan 73 appended 10 for exactly this reason). If another in-flight plan appended one first, this plan's lands after it — and any phase text naming a number is re-checked against the file as landed, not against this file.
4. Start at **Phase 0**. Items (b), (g), (i) and (j) each decide the shape of a phase below; leaving any of them to executor discretion re-opens it mid-build.
5. **Do not start Phase 2 before Phase 1 has run and been read.** Two of Phase 1's four outcomes close this plan without any `src/` edit at all, and both of those are successes of the method.
6. Re-read the privacy constraint at the top before writing a single sentence into this file or into any `src/` file. It binds execution, not just drafting.
