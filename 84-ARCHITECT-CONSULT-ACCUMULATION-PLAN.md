# 84 — Architect Consult Accumulation Plan

**Status: CLOSED — NO CHANGE. Phase 0 ratified 2026-08-21: D1 (including its D1a tie-break sub-question), D2, D3, D4, D5 and OQ-1–OQ-3 all resolved. D1's `insufficient sample` arm FIRED — the 2026-08-21 machine-wide sweep found no consumer install with ≥ 5 completed `plan.md` features (best available: 1), so no U was ever computed. Phases 1–4 correctly never ran; their non-execution IS the close, not an open item. One ratified carve-out shipped the same day: D4's separable rename-keep-the-number fix to `src/agents/architect.md` Rule 9's heading — see D4's disposition and `## Phase 0 close record`.**

Branch: `develop-2.0-init`. This document contains no private-client identifiers
and is intended to be **committed normally**, unlike the untracked plans 73/74/75.

---

## Problem

The `/devforge:plan` architect consult has grown monotonically across seven plans
(seven built the orchestrator's sub-question block; counting the Rule 9 side,
plan 81 makes eight — see *Provenance*) with no eviction mechanism, on **both
sides of the same consult** — the orchestrator's brief and the architect's own
Rule 9.

**No single addition was wrong.** Each was individually justified, separately
reviewed, and shipped behind this repo's review loops. The defect is emergent
across seven correct decisions: nothing in the process ever asks what comes OUT
when something goes in.

**This plan does not relitigate any of those seven decisions.** It is about the
aggregate. A phase arguing whether plan 66 should have added pure-builder
targets, or whether plan 71's dead-code rows were worth their words, has left
this plan's scope.

---

## Verified facts

Every row was confirmed by opening the named file (2026-08-17). Rows 2, 5, 11
and 14 are what the cost argument rests on; re-check those before ratifying.

**Re-verified 2026-08-21** against the post-plans-81/82/83 tree (commit
`532b8d1`): rows 2, 5 and 14 hold as written, and row 11 was re-measured upward
— see the row. Every `src/commands/plan/main.md` anchor below was refreshed the
same day: those lines shifted **+2/+3** at the head of the file (fact 7) and
**+24/+25** from the file-list block onward (facts 1–6, 8–10).
`src/agents/architect.md`'s rule lines (`:147`, `:150`, `:153`) did not move,
while its invoked-by lines shifted **−1** (fact 14); fact 16's `_profile`
anchors were re-read unchanged.

**Terminology, fixed here and used throughout:** *the five conditional
sub-questions* are **7, 8, 9, 10 and 11** — the ones whose applicability varies
by feature. Together they are **1439 w** (fact 2). That total, not the 1343 that
excludes sub-question 8, is the figure the accumulation argument rests on.

| # | Fact | Evidence |
|---|------|----------|
| 1 | The consult's sub-question list is **11 numbered sub-questions**. The surrounding block, including its two `Use the carried … (do not re-derive it)` preambles, runs `:384-398` | `src/commands/plan/main.md:384-394` (the list), `:396` + `:398` (the preambles) |
| 2 | **Measured word counts** (`wc -w` over the extracted line ranges). Whole block `:384-398` = **2398 w**. First five sub-questions `:384-388` = **120 w**. The five conditional sub-questions 7–11 (`:390-394`) = **1439 w**, of which 7, 9, 10 and 11 are **1343 w** and sub-question 8 (`:391`) is **96 w** — the conditional set carries **~12×** the five originals. **Priced individually:** 7 (`:390`) = **277 w**, 8 (`:391`) = **96 w**, 9 (`:392`) = **323 w**, 10 (`:393`) = **396 w**, 11 (`:394`) = **347 w**, summing to the 1439 | 2398 / 120 / 1343 measured 2026-08-17; sub-question 8's 96 measured 2026-08-18, after this plan was first drafted; those three totals **re-verified IDENTICAL 2026-08-21** (`wc -w`: 2398 / 120 / 1439) and the four remaining per-sub-question counts measured that same day with that same instrument — plans 81/82/83 moved this block, they did not edit it. **Not re-derived in this document** |
| 3 | Four sub-questions carry an explicit **no-op** clause for the inapplicable case | `:390` "A decision that restricts no shared code returns nothing here"; `:391` "a feature with no pure builders returns nothing here"; `:393` "A decision that rests on no literal's value returns nothing here"; `:394` "When the file is absent, return nothing here" |
| 4 | **Sub-question 9 is not one of them.** Its empty answer is a REQUIRED LITERAL: "a decision that kills nothing returns the literal `renders nothing unreachable`, and silence is not an answer" | `:392` |
| 5 | **Exactly ONE of the five conditional sub-questions has a precondition checkable BEFORE the architect is dispatched.** Sub-question 11 keys on whether `specs/<feature>/emission-matrix.md` exists. Sub-questions 7, 8, 9 and 10 key on properties of Key Design Decisions or of the drafted design — which do not exist until the architect returns | `:394` ("Does this feature have an emission matrix — `specs/<feature>/emission-matrix.md`"); contrast `:390` "Does any **Key Design Decision** RESTRICT…", `:391` "from the Layer Map / File Impact **under design**", `:392` "Does any **Key Design Decision** render existing code UNREACHABLE", `:393` "Does any **Key Design Decision** rest on the VALUE of a hardcoded literal" |
| 6 | **Conditional admission already exists in this block — for FILES.** Four of the brief's seven file-list entries are conditioned on existence | `:371` (`research.md` "if exists"), `:372` (`data-model.md` "if drafted at 1.1"), `:373` (`contracts.md` "if drafted at 1.2"), `:374` (`emission-matrix.md` "if exists") |
| 7 | **A whole conditional PHASE already exists in this file**, gated on a glob, with an explicit no-op arm | `:100` "PHASE 0a.7: … (conditional — skip if no seed)", `:115` (the no-op arm). Re-read 2026-08-21: plan 83 widened that arm's glob from `grill-seed.json` to `specs/*/*-seed.json`, and the conditional shape this row records is intact |
| 8 | **Downstream conditional consumers in the same file.** Three plan-template subsections and four approval-summary lines are conditional-include, keyed to sub-question output | `:479` (sq8), `:489` (sq9), `:499` (sq9); `:584` (sq8), `:585` + `:586` (sq9), `:587` (sq11) |
| 9 | **PHASE 2.5 carries read-side backstops for sub-questions 6, 7 and 11** which RE-INVOKE the architect on a missing answer. **Sub-questions 8, 9 and 10 have none.** The backstop for sub-question 11 is already conditioned on the same file-existence check as sub-question 11 itself ("When the feature has no emission matrix, this step has no work"). **Two numbering schemes coexist in that file** — PHASE 2.5 numbers its own steps, and its step 8 backs sub-question 11, NOT sub-question 8 | `:562` (backs sq6), `:563` (backs sq7), `:564` (backs sq11) |
| 10 | `/devforge:plan` cites the architect's rule NUMBERS in **five** places, and `src/agents/architect.md` cites Rule 9 once internally | `plan/main.md:389`, `:467` (the plan template's `[Rule 5:]` bracket, citing Rule 6 + Rule 9), `:471`, `:561`, `:562`; plus `architect.md:85` ("escalate per the Out-of-scope-respect step in Rule 9"). Neither `:467` nor `:85` was in the original list; the row reached completeness only on the reviewer's 2026-08-21 sweep — see the caveat below |
| 11 | Rule 9 is **1280 words in one numbered rule** whose stated subject is "**Minimal scope.** Decide what the task requires, not what might be nice to design. No speculative architecture." | `src/agents/architect.md:153`, measured 2026-08-21 (`wc -w`); it was **1105 w** on 2026-08-17, and the growth is plan 81's F1 (shipped 2026-08-18) widening the Rejected-alternative checkability step in place |
| 12 | **Six** bold forcing steps are filed under that heading — Out-of-scope-respect, State-cardinality, Narrowing, Consequence, Emission-matrix, Rejected-alternative checkability. Only the first is plausibly about minimal scope. All six name a `/devforge:plan` artifact as their recording site (a Key Design Decision, the Key Design Decisions table, or a decision's `Why` column); **exactly two — Consequence and Rejected-alternative — OPEN with the literal phrase "Key Design Decision"**, and the counting method matters because a looser one (anywhere in the first sentence) gives four | `architect.md:153` |
| 13 | **One of the six is ALREADY precondition-gated on the agent side**: the Emission-matrix step opens "when your brief carries an emission matrix" | `architect.md:153` |
| 14 | **The architect is dispatched by TWO commands**, so Rule 9's words are paid at `/devforge:plan` AND `/devforge:breakdown`, while the orchestrator brief is paid once | `architect.md:21-22` |
| 15 | `/devforge:plan` has **no `references/` directory** — the whole command is one `main.md` | verified 2026-08-17: `src/commands/plan/references` does not exist |
| 16 | `profile_helper` is shipped, has two verbs (`run`, `aggregate`), parses transcripts **post-hoc**, and is explicitly "a diagnostic, not a gate". Its `agent_busy_s` column is "deliberately excluded" from the four buckets that sum to wall — non-summing and potentially overlapping | `src/devforge/lib/_profile/_cli.py:7-18`; `src/devforge/lib/_profile/_report.py:7-11` |
| 17 | **This repo has no `specs/` tree.** Any artifact-based measurement runs against a consumer install, not here | verified 2026-08-17: `specs/` does not exist at repo root |

**This list is NOT certified exhaustive.** It was compiled by opening
`src/commands/plan/main.md`, `src/agents/architect.md` and two `_profile`
modules — not by a repo-wide sweep, because the drafting session's `rg`-backed
`Grep`/`Glob` were unavailable and no `Bash` tool was present. **Fact 10
especially:** other rule-number citations may exist in
`src/commands/breakdown/main.md` or elsewhere. Treat a hit not named above as an
omission here, not as a new defect.

**Fact 10 took three passes, and how it failed is worth recording.** The
2026-08-17/18 draft named four `plan/main.md` sites; the grep-equipped
2026-08-21 re-pass added `architect.md:85` and **still missed
`plan/main.md:467`**; the list reached completeness only on the reviewer's
independent 2026-08-21 sweep — `grep "Rule [0-9]"` returning **five** lines in
`plan/main.md` (389, 467, 471, 561, 562) and **two** in `architect.md` (85,
153). Missing tooling explains the first gap; it does not explain the second.
One nuance any renumbering pass must carry: that grep matches prose CITATIONS
only, so the numbered-rule definition sites at `architect.md:147`, `:150` and
`:153` do not appear in it and need the hand-read D4 already requires.

### Provenance

Per the repo-root `CLAUDE.md` plan index: **66** (sq8, pure builders, plus the
Narrowing rule sq7 depends on), **67** (sq7, caller enumeration), **69** (sq7
extension, WI-C), **71** (sq9, change-induced dead code), **73** (sq10, literal
provenance), **75** (sq10 extension, supply-changing commits), **77** (sq11,
emission matrix, plus widened sq6 and sq7). Sub-question 6's own origin was
**not** established this session; it is named only as a surface plan 77 widened.

**An eighth contributor, agent-side only, added 2026-08-21:** plan **81**'s F1
(shipped 2026-08-18) widened Rule 9's Rejected-alternative checkability step in
place, which is the whole of fact 11's 1105 → 1280 w growth. It did **not**
touch the orchestrator's sub-question block — that block's counts re-verified
identical the same day (fact 2). The *Problem* section's "seven plans"
accordingly still names the block's contributors exactly; on the Rule 9 side,
plan 81 is one more.

**Stated once for scale:** plan 63 spent an entire plan trimming ~1.9K words from
the always-on consumer overlay (3383 → 2806); this surface accumulated ~1.4K on
the orchestrator side alone (fact 2) with no equivalent discipline.

---

## The forcing-function objection

**Read this before ratifying anything.** It sits here rather than inside a
decision because it **disqualifies** candidates rather than merely arguing
against them.

These sub-questions are **forcing functions**. Making any of them conditional
risks the gate not firing when it should.

**Plan 73 exists because exactly that happened.** Per the repo-root `CLAUDE.md`
plan-73 entry, GAP 1 (cite the index — the plan document is untracked and slated
for deletion at v2 go-live): `/devforge:research`'s literal-archaeology lane was
gated on `mode == "bug"` at three sites. Removal and cleanup tickets classify as
**enhancements**, so the lane went inert exactly where literal provenance was
load-bearing. The gate was correct; its **precondition** was wrong, and nothing
surfaced the skip. **Plan 75's D2** separately rejected configured investigation
depth in favour of discovered depth, because depth requirements vary WITHIN a
codebase, not just between codebases.

**Fact 5 sharpens the objection past both.** Four of the five conditional
sub-questions have **post-decision triggers** — properties of decisions that do not
exist until the architect has returned. Any precondition evaluated before
dispatch is therefore a **PROXY for the trigger, not the trigger**, and a proxy
that mis-evaluates silently skips a mandatory check, which is strictly worse than
the context cost. Only sub-question 11's precondition IS its trigger (a file
exists or it does not) — which is why that one is already conditioned in three
separate places (facts 6, 9, 13).

**Any conditional-admission option must answer all three:**

1. What makes each precondition's evaluation **falsifiable** rather than a
   judgment call the orchestrator makes silently?
2. How does a **mis-evaluation surface** rather than silently skipping?
3. For the four post-decision triggers, what justifies a proxy at all — given
   that PHASE 2.5's backstops (fact 9) re-invoke the architect only for
   sub-questions 6, 7 and 11, leaving 8, 9 and 10 with no read-side catch?

An option that cannot answer these is not a candidate.

---

## Decisions

Nothing below is ratified. Each carries a recommendation and the argument
against it. **D3 is deliberately HELD** — see its own note.

### D1 — What is measured, and what threshold justifies acting *(RESOLVED 2026-08-21)*

**The threshold is stated here, before the data. A threshold chosen after seeing
the data is not a threshold.**

Define **U** = for one feature, the count of the five conditional sub-questions
(7–11) that the feature left **unexercised**. U ∈ [0, 5].

**Option A — static only.** Word counts of the brief and Rule 9. Cheapest;
measures nothing about real features. **Option B (recommended) — static +
artifact-derived U over the available consumer features**, plus the near-free
counterfactual (what a conditional brief would have admitted); no pipeline run,
inputs are `plan.md` files already on disk. **Option C — B plus a paired A/B
answer-quality run** (full brief vs trimmed brief, same feature, same architect).

**Pre-committed threshold, under Option B:**

- **median U ≥ 3** across ≥ 5 features → **act**; proceed to Phase 2.
- **median U ≤ 2** → **close with no change.**
- **fewer than 5 features available** → report `insufficient sample` and
  **close with no change.**

**D1a — the even-N tie-break *(RESOLVED 2026-08-21).*** U is an integer
in [0, 5] and nothing constrains N to be odd, so an even N whose two middle
values are 2 and 3 yields a median of **2.5**, which satisfies neither branch
above. Left unanswered, the most plausible even-N sample reaches Phase 1 with no
defined next step and forces an after-the-fact tie-break — precisely the bias D1
exists to prevent. *Recommendation:* **2.5 resolves to close with no change**,
because close is this plan's stated default and an ambiguous signal should not be
what triggers a redesign. *Counter-argument:* that rounds the one genuinely
borderline case toward inaction, a thumb on the scale in the other direction, and
it makes the act arm harder to reach than `median ≥ 3` looks on the page.
Alternatives a ratifier may pick instead: take the LOWER of the two middle
values as the median, or require N odd by dropping the oldest feature from the
sample.

*Resolved:* a median of exactly **2.5 resolves to close with no change** — close
is this plan's stated default, and an ambiguous signal must not be what triggers
a redesign. The recommendation as drafted, over both alternatives.

*Counter-argument to Option B (D1a has its own, above):* U measures
**applicability**, not cost and not quality. A
feature can leave four sub-questions unexercised and still have paid a trivial
share of the architect's total work, most of which is its own tracing. A median
over five features from one consumer install is one project's shape, not a
population. And U's inputs are **uneven**: sub-questions 8 and 9 leave a
mechanically-detectable heading in `plan.md` (fact 8) and 11 keys on a file's
existence (fact 5), but 7 and 10 land only as prose in `Why` cells (`:390`,
`:393`) and must be hand-read — two-fifths of U is the measurer's judgment.

*Against Option C:* it is the only option that measures what the plan actually
cares about — whether answer quality degrades with brief length — and also the
option most likely to be waived, which is plan 77's exact failure. A quality
difference on ONE feature is an anecdote, not a result.

*Resolved:* **Option B** — static + artifact-derived U + the counterfactual,
with the pre-committed threshold exactly as written above. Moot in execution:
OQ-1's answer fired the `insufficient sample` arm before any U was computed.

### D2 — Are the two surfaces one problem or two? *(RESOLVED 2026-08-21)*

**Option A (recommended) — two problems, decided separately.** Different
consumers, different blast radii: Rule 9's words are paid at both
`/devforge:plan` and `/devforge:breakdown` (fact 14), the brief's once and only
at `/devforge:plan`. The brief is composed per-run by an orchestrator that can
evaluate a precondition; the agent file is a static system prompt that cannot
evaluate anything — its only available conditionality is a self-gating sentence
like fact 13's, which the model may or may not honour.

**Option B — one problem, one remedy applied to both.**

*Counter-argument, and it is substantial:* the two surfaces **duplicate each
other**. Sub-question 7 (`plan/main.md:390`) and Rule 9's Narrowing step
(`architect.md:153`) both mandate naming every in-scope caller; sub-question 9
and the Consequence step both mandate the same `file | anchor token | kind | why
dead` row shape; sub-question 11 and the Emission-matrix step both mandate
accounting for every `affected` row. Remedying one surface leaves the duplication
intact and lets the two copies **drift** — worse than either cost. A ratifier
picking Option A should say explicitly whether the duplication is in scope.

*Resolved:* **Option A** — two problems, decided separately. The brief↔Rule 9
duplication (sq7↔Narrowing, sq9↔Consequence, sq11↔Emission-matrix) is
explicitly **OUT of scope**, recorded here as a known residual: the drift risk
the counter-argument names stands unremedied.

### D3 — The remedy space *(RESOLVED 2026-08-21)*

Held deliberately: the choice is made from Phase 1's data, not at Phase 0.
**Recommendation: ratify the CANDIDATE SET and the sequencing rule, and choose
nothing yet.** The candidates:

- **(a) Conditional admission.** The orchestrator admits only the triggered
  sub-questions, evaluating preconditions it can already check: does
  `specs/<feature>/emission-matrix.md` exist (fact 5), did the carried
  `## Upstream plan-seeds` block include a `**Caller enumeration**` or a
  `**Literal provenance**` section (`plan/main.md:396`, `:398`). Only the first
  is a trigger; the other two are **proxies** (fact 5), which is exactly what
  makes all three questions in *The forcing-function objection* load-bearing for
  this candidate. **It must answer them.**
- **(b) A catalog held outside context.** BMAD-METHOD's
  `bmad-advanced-elicitation` serves a method catalog via a script so it never
  enters context whole. **Mechanism only — porting that skill is a non-goal**,
  and the repo-equivalent mechanism is an on-demand `references/` file the
  orchestrator reads with the Read tool, **not a serving script**, which the
  *Any Python* non-goal forbids. Per fact 15, `/devforge:plan` has no
  `references/` directory, so this candidate creates one. **(b) is the only
  candidate that widens Phase 2's file set** — see that phase's candidate-keyed
  bound; its extra build cost is therefore visible here at ratification rather
  than discovered at execution.
- **(c) Split Rule 9** into separately-named rules, so six obligations stop
  hiding under a heading about minimal scope. Separable — see D4.
- **(d) Do nothing.** First-class, not a failure: if Phase 1's numbers do not
  clear D1's threshold, this is the outcome.

*Counter-argument to holding:* Phase 0 would ratify a plan whose largest phase
has no shape — a blank cheque. A ratifier wanting a bounded commitment should
instead ratify **(d) as the default** and require a fresh plan for any other
remedy; that is a legitimate answer to D3 and closes it at Phase 0.

*Constraint:* adding a candidate after Phase 0 re-opens Phase 0. The set is
ratified, not merely listed.

*Resolved:* the candidate set {(a), (b), (c), (d)} and the sequencing rule are
ratified as drafted, **and** the insufficient-sample close resolves D3 to
candidate **(d) — do nothing**. Holding it to Phase 1's report would have left
it permanently open, since Phase 1 is unreachable under the close. Any future
remedy requires re-opening this plan with a fresh ≥ 5-feature sample and
re-entering at Phase 1.

### D4 — Is Rule 9's mis-filing separable? *(RESOLVED 2026-08-21)*

**Option A (recommended) — yes.** A rename/split is a legibility fix with no
intended behavior change, shippable independently of any measurement outcome,
including (d).

**Option B — no; bundle it with whatever D3 chooses.**

*Counter-argument to A, two parts.* First, "no behavior change" is an assertion
about an LLM prompt and is **not checkable** — a rule read under one heading and
the same rule read under six is not demonstrably the same input. Second, a split
**renumbers**, and the numbers are cited: `plan/main.md:389`, `:467`, `:471`,
`:561`, `:562` (fact 10) plus `architect.md`'s internal Rule 3 / Rule 6
citations at `:147`, `:150`, `:153` (confirmed unchanged 2026-08-21) and its own
Rule 9 citation at `:85`. Two of them — `architect.md:85` and
`plan/main.md:467` — were absent from the original list and surfaced only across
the 2026-08-21 passes, and the list was confirmed complete for those two files
only on that date, never swept repo-wide. That history IS the argument: a pass
that misses one ships a spec pointing at the wrong rule, the exact stale-claim
class this repo's cross-check rule exists to prevent.

*The cheaper sub-option:* **rename the heading, keep the number.** Rule 9 stops
claiming to be about minimal scope; nothing renumbers; the six steps stay put.
Most of the legibility at none of the citation risk.

*Resolved:* **Option A, separable** — and exercised immediately via the cheaper
sub-option (rename the heading, keep the number), shipped 2026-08-21. One
divergence from that sub-option as drafted, forced by a cross-check:
`src/agents-AUTHORING.md`'s Rules-section closers fix `Minimal scope` as a
canonical closer name every agent carries, so the heading was **EXTENDED rather
than replaced** — `9. **Minimal scope.**` became
`9. **Minimal scope & the six decision-recording forcing steps.**` — keeping the
closer name while ending the rule's claim to be only about minimal scope. No
number changed and no citation was touched: all five `plan/main.md` citations
and `architect.md:85` cite by number or by step name, never by heading text
(verified 2026-08-21).

### D5 — Does Phase 1's report become a durable artifact? *(RESOLVED 2026-08-21)*

**Option A (recommended) — append the numbers to THIS file** under a
`## Phase 1 measurement record` heading: N, per-feature U, the median, which
branch of D1's threshold fired, and the date. **Option B — a separate file.**
**Option C — stdout only, recorded in the commit message.**

*Argument for A:* plan 77's Phase 1 was waived and there is now nothing to point
at — the waiver is legible only from a `CLAUDE.md` amendment. A record inside the
plan makes a waiver **visibly** a hole in the plan's own body.

*Counter-argument:* this is a plan about instruction bloat, and Option A grows
the plan. A measurement is arguably a transient input that belongs in a commit
message, not in a document future sessions read.

*Resolved:* **Option A** — the record lives in this file. Phase 1 never ran, so
the `## Phase 0 close record` section below stands in for the
`## Phase 1 measurement record` this option named.

---

## Open questions

- **OQ-1 — Is a consumer install with ≥ 5 completed `plan.md` features actually
  available, and which one?** *Resolved:* **No** — the 2026-08-21 machine-wide
  sweep (instrument: `ls specs/*/plan.md` over every project root under
  `~/Projects`) found testForge20 with 1 completed feature and jira-clone with
  1; no other install has any. D1's `insufficient sample` arm fired at Phase 0,
  closing the plan without running Phase 1. Full sweep in
  `## Phase 0 close record`. Fact 17: the sample cannot come from this repo.
  *Recommendation:* answer at Phase 0, not Phase 1 — a "no" fires D1's
  `insufficient sample` arm immediately and the plan closes without anyone
  running anything. *Counter-argument:* closing on sample scarcity leaves a real
  accumulation unaddressed for a measurement-logistics reason, not a substantive
  one.

- **OQ-2 — Does `/devforge:breakdown`'s architect dispatch carry a comparable
  brief?** *Resolved:* recorded as **unmeasured**, exactly as this bullet
  already states — no symmetry assumed, `/devforge:breakdown`'s brief was never
  measured, and fact 2's counts remain `/devforge:plan`-only. Moot for action
  under the close. Not measured this session; fact 2's counts are
  `/devforge:plan`'s only. Recorded so a future session does not assume
  symmetry — fact 14 means Rule 9 is paid there regardless.

- **OQ-3 — Should this plan also record a "no addition without eviction"
  convention?** *Resolved:* recorded as a **candidate convention only; nothing
  built** — it plausibly fails plan 77's visibility criterion, as the
  recommendation below argued. A budget rule would prevent recurrence
  regardless of remedy. *Recommendation:* record as a candidate, build nothing —
  it is a rule about rules, and it plausibly fails plan 77's own visibility
  criterion (*does the rule produce an artifact that is visibly wrong when the
  analysis wasn't done?*), since an un-evicted addition does not read wrong on
  its face.

---

## Phases

### Phase 0 — Ratification *(gate)*

Maintainer resolves **D1 (including its D1a tie-break sub-question), D2, D4, D5**
and **OQ-1–OQ-3**, and ratifies **D3's candidate set plus the sequencing rule**
(or closes D3 outright by ratifying candidate (d) as the default — see D3's
counter-argument). Record each disposition inline under its D or OQ, opening with
the literal marker `*Resolved:*` plus the chosen option and one sentence of
reason; that literal is what this phase's Verify greps for. Read *The
forcing-function objection* before ratifying D3's set, and re-check facts 2, 5,
11 and 14 — the cost argument.

**Verify:**

- `grep -n "^### D[1-5] " 84-ARCHITECT-CONSULT-ACCUMULATION-PLAN.md` returns five
  lines; none ends in `*(OPEN)*`; D3's ends in either
  `*(HELD — resolved at Phase 1's report)*` or a `*Resolved:*` disposition.
- **D1a carries its own `*Resolved:*` sentence.** Phase 1 cannot fire its
  threshold on an even-N sample without it, so a D1 disposition that skips D1a
  does not close this gate.
- Every OQ-1–OQ-3 bullet opens with a `*Resolved:*` sentence naming the chosen
  option.
- If OQ-1 resolved to "no install available", D1's `insufficient sample` arm is
  recorded as fired and the status line at the top of this file reads
  `CLOSED — NO CHANGE`.
- The status line names the ratification date.

---

### Phase 1 — Measure *(the spine)*

**No `src/` edit in this phase. No pipeline run. No new code.**

**What makes it cheap — say this to anyone proposing to waive it.** Every input
already exists on disk: it reads `plan.md` files a consumer install has already
produced, and `profile_helper` parses transcripts **post-hoc** (fact 16). No
pipeline run, no install step, no fixture, no agent dispatch. The expensive
option (D1 Option C's paired A/B) is deliberately NOT the recommendation,
precisely so the recommended measurement is too cheap to be worth skipping.

Procedure, under D1 Option B:

1. **Per-sub-question word counts.** Step 4's counterfactual needs each
   conditional sub-question priced separately, and **all five are already priced
   at fact 2** — 7 = 277 w, 8 = 96 w, 9 = 323 w, 10 = 396 w, 11 = 347 w, measured
   2026-08-21 (`wc -w`). What remains here is the staleness check: re-measure the
   whole block (`plan/main.md:384-398`) and confirm it still totals **2398 w**
   before reusing those figures. A moved total means the block was edited after
   2026-08-21; re-measure 7–11 individually then (`:390-394`, one line each) and
   amend fact 2 with the new counts, their date and the instrument.
2. **Enumerate features.** In the consumer install OQ-1 named, list every
   `specs/*/plan.md`. Record **N**.
3. **Compute U per feature** by these five fixed predicates — no judgment beyond
   the two labelled hand-read:

   | Sub-question | Unexercised ⟺ | Kind |
   |---|---|---|
   | 8 | `plan.md` has no `### Pure-Builder Targets` heading (fact 8, `:479`) | mechanical |
   | 9 | `plan.md` has no `### Change-Induced Dead Code` heading (fact 8, `:489`) | mechanical |
   | 11 | `specs/<feature>/emission-matrix.md` does not exist (fact 5) | mechanical |
   | 7 | no Key Design Decision `Why` cell records a caller-scoped-vs-layer-wide classification | **hand-read** |
   | 10 | no `Why` cell names a literal with an intent classification | **hand-read** |

4. **Counterfactual admitted words.** Per feature, `2398 − Σ(words of its
   unexercised sub-questions)` from step 1 — what a conditional brief would have
   admitted, computed without building one. 2398 is the WHOLE block including the
   two preambles (fact 2), so this figure is an **upper bound** on admitted words,
   not a model of any specific remedy.
5. **Transcript pass (D1 Option B's second half).** If a consumer transcript
   containing a `/devforge:plan` run exists, run
   `.devforge/lib/profile_helper run --transcript <path>` and record that
   segment's `task_s` and `agent_busy_s`; if none exists, record
   `no transcript available` and continue. **Honest bound, recorded beside the
   number:** `agent_busy_s` is non-summing and potentially overlapping (fact 16)
   and conflates brief length with the architect's own trace work, so it cannot
   isolate this plan's cost. Context, not evidence.

Then record the result per D5 and fire D1's threshold branch.

**Both outcomes are first-class:**

- **median U ≤ 2, or N < 5** → the plan **CLOSES WITH NO CHANGE**. Set the status
  line to `CLOSED — NO CHANGE`, record the numbers, and stop. This is a
  successful plan, not a failed one: the finding was real, the cost was measured,
  and the measurement said don't act.
- **median U ≥ 3** → choose the D3 candidate at the report and proceed to Phase 2.

**Verify:**

- The record required by D5 exists and states: N, per-feature U, the median, the
  per-sub-question word counts, the counterfactual admitted-word figure, and
  which threshold branch fired.
- `git diff --name-only` lists no file under `src/`.
- If the close branch fired, the status line at the top of this file reads
  `CLOSED — NO CHANGE` and no later phase was started.

---

### Phase 2 — Remedy *(shape decided at Phase 1's report — NOT specified here)*

Runs only if Phase 1's median U ≥ 3. Its content is the D3 candidate chosen at
Phase 1's report.

**File-set bound — candidate-keyed, because candidate (b) legitimately needs a
third path.** Under **(a), (c) or (d)** the editable set is exactly
`src/commands/plan/main.md` and `src/agents/architect.md` and no other file;
under **(b)** it is those two plus the new `src/commands/plan/references/`
directory and the file(s) it holds, and nothing else. `main.md` and the agent
file ship into `.claude/`, a `references/` file to `.devforge/command-refs/plan/`
— so all of them route through **instruction-author → instruction-reviewer +
claude-code-guide**.

Two things are fixed regardless of candidate: **no forcing function is removed**,
and the **no-helper-growth tripwire** — no new helper verb, schema field, exit
code or numbered check. A remedy that grows the Python surface has left this
plan's scope, because answering instruction volume with machinery reproduces the
accumulation one layer down. If candidate (a) won, the diff must answer all three
questions in *The forcing-function objection* in its own prose.

**Verify:**

- `git diff --name-only` lists only what the ratified candidate's bound permits:
  exactly the two named files under (a), (c) or (d); those two plus paths under
  `src/commands/plan/references/` under (b). Any other path FAILS this phase.
- All 11 sub-questions are still REACHABLE from `src/commands/plan/main.md` —
  under (a), (c) or (d) confirm by opening the block in that file and counting;
  under (b) by following the reference pointer to the catalog file and counting
  there. A diff that drops one FAILS this phase.
- `src/agents/architect.md` still carries all **six** bold forcing steps
  (Out-of-scope-respect, State-cardinality, Narrowing, Consequence,
  Emission-matrix, Rejected-alternative checkability). Count = 6.
- No line in the diff adds a `check-` or `verify-` verb, a `Check N` label, or an
  exit code. The check is on the diff, not on the file.
- Under D4 Option A with a renumbering: every citation in fact 10
  (`plan/main.md:389`, `:467`, `:471`, `:561`, `:562`) plus `architect.md:85`,
  `:147`, `:150`, `:153` was read by hand and updated. One left pointing at the
  old number FAILS this phase.

---

### Phase 3 — Re-measure

**Runs only if Phase 2 ran.** Under Phase 1's close branch there is no edited
brief and this phase does not exist.

Re-run **Phase 1 steps 1 and 4 only**, against the edited brief and the SAME
per-feature U data. Minutes, no new run: U is a property of the FEATURE, not of
the brief, so it does not change — only the admitted-word figure does.

**The bound, stated plainly, because it is this phase's whole honesty:** the
re-measurement proves the **admitted-word reduction** and nothing else. It does
**not** prove answer quality was preserved. The only evidence for preservation is
the check below plus Phase 4's single consumer run, and neither is a statistical
result.

**Preservation check (falsifiable, cheap).** Take the Phase-1 feature with the
LOWEST U — the one that exercised the most sub-questions — and confirm the edited
brief's preconditions **admit every sub-question that feature exercised**. One
that would not be admitted is a proven silent skip and fires the revert.

**Revert branch, first-class.** If the admitted-word figure does not move
materially, or the preservation check finds a single skip, **revert Phase 2 in
the same session**. This mirrors plan 77's D6, survivable here only because the
re-measurement is arithmetic over data already collected.

**Verify:**

- The recomputed admitted-word figure is recorded beside Phase 1's, in the same
  record.
- The preservation check names the feature used, its U, and the specific
  sub-questions checked.
- If either branch above fired, `git diff --name-only` against the pre-Phase-2
  tree is empty.

---

### Phase 4 — Consumer e2e *(user-driven — the standing manual gate)*

**Runs only if Phase 2 ran.** The "standing manual gate" label names this plan's
terminal e2e, NOT an unconditional obligation: under Phase 1's close branch
nothing changed, so there is nothing to validate and this phase does not run —
its non-execution is then correct, not an open item.

Known-answer anchor: from Phase 1's data, pick a feature whose `plan.md` shows
sub-question 7 exercised (a caller-scoped-vs-layer-wide classification in a `Why`
cell), so the correct outcome is known before the run. In a consumer install, run
`/devforge:plan` on a feature that restricts shared-code behavior.

**Verify:**

- The architect's return still carries the Narrowing classification and the named
  caller set — unchanged by any remedy in D3's set.
- PHASE 2.5's own step 7 (`plan/main.md:563` — the backstop for sub-question 7;
  the two numbering schemes coincide here by accident, see fact 9) did **not**
  fire. If it fires, sub-question 7 was not admitted and the remedy caused
  exactly the skip *The forcing-function objection* predicted.
- The result is recorded in `REGRESSION-ANCHORS.md`, naming the observed
  behavior.

---

## Non-goals

- **Removing any forcing function.** Admission and legibility, never deletion:
  all 11 sub-questions and all 6 forcing steps survive whatever Phase 2 does.
- **Revisiting plans 66, 67, 69, 71, 73, 75, 77 or 81.** Their additions were
  correct and each was separately reviewed. A phase arguing an individual
  addition's merit has left this plan's scope.
- **Porting BMAD-METHOD's `bmad-advanced-elicitation` skill.** Only its mechanism
  — a catalog served by a script so it never enters context whole — is recorded,
  as candidate (b).
- **Any Python.** No helper verb, no schema field, no test (Phase 2's tripwire).
- **Plan 79's and plan 83's subjects.** The subjects and the decisions stay
  disjoint; stated so no future session merges them. The no-shared-FILE half of
  that claim went stale after drafting and is withdrawn (2026-08-21): three
  plans have since edited `src/commands/plan/main.md` — plan 79's section-aware
  memory excerpt reshaped the memory-check preflight block at `:164-177`
  (`memory_excerpt` at `:170`, `:173`, `:175`; 2026-08-18), plan 82 added a
  spec-check preflight block backed by a new `plan_helper` verb (2026-08-19),
  and plan 83 widened PHASE 0a.7's seed glob (2026-08-20) — each of them in a
  region disjoint from the consult block (`:384-398`). The separation is
  subject-level, not file-level — Phase 2's file-set bound is unaffected, being
  a file-level bound, and those regions simply must not appear in this plan's
  diff.
- **Building plan 70's deferred Phase 2.** This plan may USE `profile_helper`
  (fact 16) as a read-only instrument; it delivers none of plan 70's own
  real-run diagnosis.

---

## Context for next session

The evidence lives in *Verified facts* and is not restated here. What follows is
only the **inferences** those facts support:

1. **The trigger and the precondition coincide for exactly one sub-question.**
   Fact 5 — the most load-bearing inference here. Sub-question 11 can be
   conditioned safely because a file either exists or does not; 7, 8, 9 and 10
   can be conditioned on nothing but a proxy. A session reading "four
   sub-questions already carry no-op clauses" (fact 3) and concluding "so they are
   already conditional" has inverted this: a no-op clause makes the ANSWER cheap,
   not the READING.

2. **Sub-question 9 is structurally different from its four neighbours** and is
   the wrong first target for any remedy. Fact 4: its empty answer is a required
   literal so silence cannot pass for compliance. Conditioning it would restore
   the exact silence plan 71 designed it to forbid.

3. **The two surfaces duplicate each other** (D2's counter-argument), so a remedy
   applied to one alone leaves a second copy of the same obligation free to drift.

4. **The plan can succeed by closing.** D1's threshold has a close branch and
   Phase 1 names it a success; treating a `median U ≤ 2` outcome as a failure to
   be argued around misreads the plan's purpose.

5. **Plan 77 is the cautionary precedent, precisely.** Built measure-first — its
   D5 inverted this repo's build-then-e2e convention, its D6 made a delete branch
   first-class — and then Phases 1 and 3, both measurement arms, were **WAIVED**
   (waived, not deferred), so the mechanism shipped into `src/` on reasoning
   alone with no baseline ever taken. This plan's defence is that its measurement
   needs **no pipeline run and no new code**; a session that finds itself waiving
   Phase 1 anyway should close under D3 candidate (d), not ship Phase 2
   unmeasured.

6. **A staleness vector the usual guard misses.** The first draft said
   sub-question 8's word count "was not measured this session and is a Phase-1
   step-1 output" — a correctly-framed forward reference, true when written. It
   went false a day later because a reviewer **measured it** (96 w). Nobody
   edited the plan; someone measured the world it describes, so "re-check after
   any edit" cannot catch it. The working guard is the one fact 2 now uses:
   date-stamp each measurement and name the instrument, so a reader can tell an
   observation with an expiry from a statement of design.

**One weakness recorded rather than hidden:** two of U's five inputs
(sub-questions 7 and 10) are hand-read from `Why` cells, so U is not fully
mechanical and two measurers could disagree — a reason to distrust a median
sitting on the threshold, not a reason to skip the measurement.

---

## When resuming work

**This plan is CLOSED — NO CHANGE (2026-08-21).** The guidance below describes
how Phase 0 was approached and is kept for historical readability; any future
remedy requires re-opening per D3's disposition — a fresh ≥ 5-feature sample,
re-entering at Phase 1 — not re-ratifying D1–D5 from scratch.

Read *Verified facts* first — seventeen evidence rows, each checkable in under
a minute. If facts 2, 5, 11 or 14 no longer hold, stop and re-derive: D1's
threshold and D2's split rest on them. Then read *The forcing-function objection*
before Phase 0 — it disqualifies candidates rather than merely arguing against
them, so it belongs before the decisions, not after.

Three things are easy to get backwards:

- **Phase 1 is a measurement; the plan pre-commits to no redesign.** D3 is HELD
  on purpose. A session arriving with a remedy already chosen has skipped the
  only phase that decides whether a remedy is warranted.
- **`U` counts what a feature did NOT exercise.** High U means the brief was
  mostly inapplicable. Reading it the other way inverts D1's threshold.
- **The measurement cannot run in this repo** (fact 17 — no `specs/` tree). Phase
  1 needs the consumer install OQ-1 identifies; settle OQ-1 at Phase 0.

---

## Phase 0 close record

**Ratified 2026-08-21.** Every decision and open question is disposed inline
under its own heading — D1 (and D1a), D2, D3, D4, D5, OQ-1, OQ-2, OQ-3 — each
opening with the literal `*Resolved:*` marker this phase's Verify greps for. D3
was resolved at Phase 0 rather than held to Phase 1's report: with Phase 1
unreachable, holding it would have left it open forever.

**Facts re-verified 2026-08-21**, tree `532b8d1`, instruments `sed` (line
extraction) and `wc -w` (counts):

- **Fact 2** — whole block `:384-398` = **2398 w**; `:384-388` = **120 w**;
  `:390-394` = **1439 w**; the five conditional sub-questions priced
  individually, 7 through 11 = **277 / 96 / 323 / 396 / 347 w**, summing to that
  1439.
- **Fact 11** — Rule 9 = **1280 w**, measured BEFORE the D4 rename recorded
  below.
- **Fact 14** — the architect is dispatched by `/devforge:plan` AND
  `/devforge:breakdown` (`architect.md:21-22`).
- **Fact 5** — the precondition contrast was re-read and holds: sub-question 11
  keys on a file's existence, while 7, 8, 9 and 10 key on properties of
  decisions that do not exist before dispatch.

**OQ-1 sweep, 2026-08-21.** Instrument: `ls specs/*/plan.md` at every project
root under `~/Projects`.

| Project root | Completed `plan.md` features |
|---|---|
| `private/testForge20` | **1** (`001-catalog-tab-order`) |
| `jira-clone` | **1** |
| `private/forge`, `private/forgeV1`, `ap`, `doosan`, `startups/dataLake` | **0** |

The largest sample available is therefore **N = 1**, and 1 < 5, so D1's
`insufficient sample` arm fired and the plan **CLOSES WITH NO CHANGE** at Phase
0. This is the route OQ-1's own recommendation named — "the plan closes without
anyone running anything". No U was computed for any feature, so **Phase 1's
Verify block does not apply**: its record, its per-feature U and its median
never existed, and their absence is the close rather than a gap. Phases 2, 3 and
4 each run only if the phase before them did, so their non-execution is likewise
correct, not an open item.

**The D4 carve-out, shipped 2026-08-21.** `src/agents/architect.md`'s Rule 9
heading was renamed in place, its number untouched:

- old: `9. **Minimal scope.**`
- new: `9. **Minimal scope & the six decision-recording forcing steps.**`

Extended rather than replaced because `src/agents-AUTHORING.md` fixes
`Minimal scope` as a canonical Rules-section closer name every agent carries;
dropping it would have broken that convention to fix this one. Zero citations
touched — the five `plan/main.md` sites (`:389`, `:467`, `:471`, `:561`, `:562`)
and `architect.md:85` cite by rule NUMBER or by step name, never by heading text.
This rename is the ONLY `src/` edit this plan produced, and it ships under D4's
separability, not under any phase — Phase 2's file-set bound never engaged.

**Facts 11 and 12 quote the PRE-rename heading.** Both are date-stamped
observations of 2026-08-21, not current-state claims, and neither row is amended
here; the current heading is the `new:` line above. That is exactly the reading
*Context for next session* point 6 prescribes for a dated measurement.

**Reading the pre-close text.** Nothing above this section was rewritten to past
tense: `## Decisions` still opens "Nothing below is ratified" and calls D3
"deliberately HELD" in the same paragraph, D3's body still opens "Held
deliberately", and *When resuming work* still says D3 is HELD. Those
sentences describe the plan's state BEFORE 2026-08-21 and are preserved as the
record of it — deliberately, so the arguments stay readable as they were made.
The inline dispositions and this section are the current state.
