# 86 — Fowler refactoring gaps: five instruction-only closures

**Status:** IN PROGRESS — **Phase 0 RATIFIED 2026-08-23**: D2 = (a) titled bold block in §3.6; D3 = DECLARE-ALWAYS; D4 = all six smells; D5 = yes, both the plan-side guidance AND the §6.1 clarification; OQ-1 = mixed-tasks-only with the objective trigger. D1 and Phase 1 were pre-ratified by maintainer directive 2026-08-18 (*"i want close this gap"*); OQ-2 was RESOLVED 2026-08-18 from the code. **One scope AMENDMENT ratified at the same sitting: Phase 5 gains a THIRD site, `src/agents/architect.md` Rule 9** — see the amendment note under D5. Phases 1–6 are cleared to build.

**Validity re-verified 2026-08-23** against the tree after plans 81/82/83/84/87 shipped: all thirty-three `## Verified mechanics` rows still hold in substance. Four of the five fix surfaces (`src/agents/code-reviewer.md`, `src/constitution.md`, `src/commands/breakdown/main.md`, `src/commands/audit/references/best-practices-checklist.md`) were not touched at all since drafting; `src/commands/plan/main.md` was changed by plans 82 and 83, but only at PHASE 0a.7 / PHASE 0a.8, nowhere near F5's PHASE 1.3 landing site. Only DIGITS rotted (`plan/main.md` facts 19–20 shifted by roughly +24 lines: sub-question 5 now reads at `:388`, the list still runs 1–11). **Grep the quoted string, never the `:NNN`** — the plan already said so and the rot proves it.
**Branch:** `develop-2.0-init`
**Created:** 2026-08-18.

This plan document contains no private-client identifiers and is intended to be
**committed normally**, unlike the deliberately-untracked plans 73/74/75.

## Identifier constraint

The motivating incident happened in a consumer install, not in this repository. **Its
function names, feature slug and domain nouns are deliberately ABSENT from this file** and
must not be added by a later amendment — the incident is carried at the abstraction level
*"one task copied a sibling builder function into a second builder differing only in one
call option"*, which is the entire shape the five findings rest on. Nothing below needs
more resolution than that. **If a sentence only works with a real consumer identifier,
rewrite the sentence.**

The two UNTRACKED private-client evidence files at repo root
(`81-EVIDENCE-V2-BENCHMARK-RUN.md`, `77-EVIDENCE-DISCOVERY-TO-LOCK-INVERSION.md`) are
neither read nor cited by this plan, and no phase may import from them.

---

## Origin — a Fowler-grounded evaluation of the framework's refactoring discipline

The maintainer evaluated this framework against Martin Fowler's refactoring canon: the
refactoring.com definition — *"a change made to the internal structure of software to make
it easier to understand and cheaper to modify without changing its observable behavior"* —
plus five concepts from *Refactoring* 2nd ed.: **two hats** (Kent Beck — never wear the
add-feature hat and the restructure hat at the same moment), **self-testing code as a
precondition** for restructuring, the **Rule of Three**, the **code-smells catalog**, and
**preparatory refactoring** (*"make the change easy, then make the easy change"*).

**The evaluation's finding was NOT that the framework is weak here.** It found the
framework strong on five axes and short on five specific ones. Recording the strong half
matters at ratification, because three of the five fixes are additions to mechanisms that
already work rather than repairs of mechanisms that do not:

- **Behavior preservation is already first-class** — `refactor(scope):` is defined as
  *"behavior-preserving restructuring"* (fact 14), `/devforge:specify` classifies a whole
  spec type `refactor` as *"behavior preserved, structure changed"* (fact 15) and records
  preservation constraints through `record-constraint --kind not_break` rendering as
  *"Must not break"* (fact 16), and plan 77's emission matrix accounts for what a change
  stops emitting.
- **Small steps with per-task verify gates** — `/devforge:implement`'s scope-aware verify
  plus its four-reviewer panel run on every task's own diff.
- **The Rule of Three is in the constitution verbatim** — *"2 occurrences are fine — don't
  abstract prematurely. Wait for the third."* (fact 10).
- **The Long Function smell has a guideline** — the ~40-line extraction prompt (fact 11) —
  and Speculative Generality has one in the KISS bullets plus the agents' minimal-scope
  rule.
- **Duplication IS hunted at two scopes** — cross-task at `/devforge:review` (fact 4) and
  whole-codebase at `/devforge:audit` (fact 23).

**The five gaps below are what that evaluation found missing.** The maintainer directed
F1's closure explicitly (*"i want close this gap"*); F2–F5 are proposed here and are
unratified.

**The incident that exposed F1.** In a consumer install, a single task duplicated an
existing builder function into a second builder, verbatim except for one call option. That
duplication was **PLAN-DECLARED and legitimate** — a Key Design Decision carried the
decoupling rationale, the spec's risk section named it, and the plan's own DRY-alignment
line recorded it as one accepted tension. **The gap is not that run. The gap is its
UNDECLARED twin**: the same diff shape with no declaration anywhere would have been caught
by no per-task layer, and would have reached `/devforge:review` only to be ruled out of
scope there by construction (facts 4, 5).

---

## The five findings

| # | Finding | Severity | Phase | Fix surface |
|---|---------|----------|-------|-------------|
| F1 | Per-task duplication blind spot — a new function cloned inside a MODIFIED file is claimed by no layer | High | 1 | `src/agents/code-reviewer.md` |
| F2 | No two-hats rule — nothing requires a mixed behavior-change + restructure task to partition its surfaces | Medium | 2 | `src/constitution.md` + `src/commands/breakdown/main.md` + `src/agents/code-reviewer.md` |
| F3 | No regression-net precondition for restructuring untested behavior-carrying code | Medium | 3 | `src/commands/breakdown/main.md` |
| F4 | Smells vocabulary incomplete in the `/devforge:audit` hunt | Low | 4 | `src/commands/audit/references/best-practices-checklist.md` |
| F5 | No preparatory-refactoring lane | Low | 5 | `src/commands/plan/main.md` + `src/constitution.md` |

**ALL FIVE FIXES ARE INSTRUCTION-ONLY.** Zero Python, zero new validators, zero new check
numbers, zero new mechanical gates — **plan 75's tripwire, both halves**. Facts 17, 18 and
31 are why that constraint has teeth rather than being a stated preference: the task-file
header field F2 and F3 would naturally reach for is helper-emitted and flag-gated, and the
new numbered constitution subsection F2 might otherwise want is entered in a closed tuple
in helper code. **Both are Python, so both are out of bounds — and each finding's landing
site below is chosen accordingly, not by taste.**

---

## Verified mechanics (2026-08-18)

Every row was confirmed by opening the named file. **The quoted token is the anchor; the
digit is a dated hint** — this repo has documented anchor rot (facts 27, 28 are two live
examples), so grep the string, never the `:NNN`.

| # | Fact | Evidence |
|---|------|----------|
| 1 | code-reviewer's check 8 is scoped to *"each **newly created** file/module in the changeset"* and closes with *"One targeted search pass, not a full repo audit. Skip files that only edit existing modules."* | `src/agents/code-reviewer.md:33`, `:36` |
| 2 | Its verdict sentence: *"Structural-integration verdict per new file: `INTEGRATED \| INTENTIONAL_PARALLEL \| DUPLICATE`. A `DUPLICATE` is Critical (the change rewrote what already existed). An `INTENTIONAL_PARALLEL` without spec/plan justification is High."* | `src/agents/code-reviewer.md:45` |
| 3 | The output template under `### Structural Integration` is ONE line: `- [new-file]: INTEGRATED \| INTENTIONAL_PARALLEL (reason: ...) \| DUPLICATE (existing: [path])` | `src/agents/code-reviewer.md:69`, `:70` |
| 4 | `/devforge:review`'s duplication section is **cross-task by construction** — *"Multiple tasks each adding a near-identical helper…"* / *"Two DIVERGED copies…"*, and the file's opening rule says *"Every pattern here requires reading TWO OR MORE tasks together — a finding you can state from a single task's diff is out of scope"* | `src/commands/review/references/emergent-issue-checklist.md:49`–`:59`, `:5`–`:7` |
| 5 | **The `/devforge:review` preamble asserts the very coverage F1 shows is incomplete** — *"Those reviewers already had their shot at every line inside any single task"* — and then rules the single-task case out of scope: *"If a finding is fully contained within ONE task's changes, it is OUT OF SCOPE."* | `src/commands/review/references/anti-relitigation-preamble.md:10`–`:11`, `:21`–`:24` |
| 6 | **`src/agents/code-reviewer.md` is the single live source** (a repo-wide `**/code-reviewer.md` glob returns exactly one file), and both panel consumers load the persona from the consumer copy rather than inlining it — `/devforge:implement` dispatches *"`code-reviewer` (consumer `.claude/agents/code-reviewer.md`)"*, `/devforge:fix` dispatches *"each with `subagent_type: <agent>` (which loads that reviewer's persona from `.claude/agents/<agent>.md`; do NOT re-inline the persona)"* | `src/commands/implement/main.md:183`; `src/commands/fix/main.md:188` |
| 7 | The `_implement` panel tests carry `### Structural Integration` only as **fixture text inside a sample markdown blob**; the helper parses the `### Verdict:` line and nothing else | `tests/lib/_implement/test_cmds_review_loop.py:78`; `tests/lib/_implement/test_cmds_review_panel.py:81`, `:104`; `src/commands/implement/references/review-loop.md:21`–`:26` |
| 8 | The fleet-wide severity scale is `Critical / High / Medium / Info`, *"verbatim"*, anchored to `SEVERITY_ENUM` | `src/agents-AUTHORING.md:119`–`:127` |
| 9 | **Agent files must cite the constitution by concept-name, never by `§`-number** — *"A `§`-number reference is a dangling reference waiting to happen"*, and the authoring checklist repeats it. **`code-reviewer.md:37` already violates it** (*"the constitution's No dead code rule (§3.5)"*) — pre-existing, recorded, NOT owned here | `src/agents-AUTHORING.md:147`–`:149`, `:187`; `src/agents/code-reviewer.md:37` |
| 10 | The Rule of Three is in the constitution verbatim: *"2 occurrences are fine — don't abstract prematurely. Wait for the third."* | `src/constitution.md:111` |
| 11 | The Long Function guideline: *"If a function exceeds ~40 lines, look for extraction opportunities. This is a guideline, not a hard rule…"* | `src/constitution.md:92` |
| 12 | **§3.6 already carries a titled bold block appended after the SOLID/DRY/KISS triad** — `**Narrowing (restricting shared-code behavior):**` plus four bullets — so D2's shape has an in-file precedent and needs no new section number | `src/constitution.md:121`–`:125` |
| 13 | The opportunistic-refactoring ban exists twice: *"Do not refactor surrounding code."* and §6.1 *"Do not refactor, improve, or 'clean up' code outside the scope of the current task."* | `src/constitution.md:195`; `:223`–`:224` |
| 14 | `refactor(scope):` is defined as *"behavior-preserving restructuring"* | `src/CLAUDE.md:231` |
| 15 | `/devforge:specify` classifies a spec type `refactor` — *"behavior preserved, structure changed"* | `src/commands/specify/main.md:454` |
| 16 | Preservation constraints are already recordable: `record-constraint --kind not_break --content "<behavior to preserve>"`, rendered as *"Must not break"* | `src/commands/specify/main.md:723`–`:726`, `:729` |
| 17 | **Task-file header fields are HELPER-emitted and flag-gated.** `render_task_file` appends `**Property targets**:` only when `--property-targets` is passed and `**Dead code removal**:` only when `--dead-code-removal` is. **A NEW header field is a Python change and is therefore out of bounds for this plan** | `src/devforge/lib/breakdown_helper.py:1036`–`:1047` |
| 18 | **…but `## Description`, `## Change Details` and `## Contracts` (`### Expects` / `### Produces`) are free-form skeleton sections the ORCHESTRATOR fills** — *"Files table, Description, Change Details — from the Phase 1 file analysis"* and *"Contracts (`Expects` / `Produces`) — per the Contract Generation Rules"*. **Content authored into those sections is instruction-only** | `src/devforge/lib/breakdown_helper.py:1059`, `:1065`, `:1074`–`:1080`; `src/commands/breakdown/main.md:352`–`:353` |
| 19 | `plan.md` is authored by the orchestrator from an inline markdown template in `main.md` PHASE 2 — no helper render — so a new plan.md subsection is likewise instruction-only | `src/commands/plan/main.md:380`–`:384` |
| 20 | The architect sub-question list runs **1–11**. Sub-question 5 is the minimal-change baseline: *"What is the MINIMAL change that satisfies the in-scope ACs? … the baseline the Key Design Decisions must not exceed without justification."* Two plan.md subsections are gated on sub-questions 8 and 9 by name | `src/commands/plan/main.md:358`–`:370`, `:364`; `:455`, `:465` |
| 21 | `/devforge:breakdown` PHASE 1 has a **greenfield** ordering sequence (*"Infrastructure → Types / interfaces → Core logic → Presentation → Integration"*) and the `### If existing codebase` branch has **no ordering list at all** | `src/commands/breakdown/main.md:165`–`:171`; `:141`–`:152` |
| 22 | The change-induced dead-code lane is the shape F3 mirrors: a declared plan row **folds into the owning task**, carried in a named task field, with *"NEVER create a separate, dedicated deletion task for it"* argued from atomicity | `src/commands/breakdown/main.md:376`–`:392` |
| 23 | `/devforge:audit`'s hunt checklist has a `Duplication & divergence  (Category: duplication)` section with three bullets (copy-paste, diverged variants, 3+-place domain logic), each demanding a quote. The `Category` enum is fixed at six values | `src/commands/audit/references/best-practices-checklist.md:74`–`:84`, `:15`–`:16`, `:116`–`:118` |
| 24 | The checklist is injected VERBATIM into every audit agent's brief by `_scope.py`, and its tests pin only the header token `BEST-PRACTICES` and the distinctive phrase `Type-safety suppression` — **neither is touched by an added section** | `src/commands/audit/main.md:245`; `src/devforge/lib/_audit/_scope.py:601`; `tests/lib/_audit/test_scope.py:958`–`:970` |
| 25 | `code-reviewer` is also a **Batch-A hunter in `/devforge:audit`** and a **Batch-A finder in `/devforge:review`**; the `/devforge:review` finder brief injects the anti-relitigation preamble via `render-agent-brief`, so the persona's per-task instructions are scoped out there by the preamble, not by the persona | `src/commands/audit/main.md:294`; `src/commands/review/main.md:166`, `:53`, `:55` |
| 26 | Plan 05's ledger entries describe the file-only scope: *"code-reviewer §7 Structural Integration (DIR check)"* / *"Added Section 7 (Structural Integration / DIR check) … §7 placed at end of checklist for monotonic numbering"* | `CLAUDE.md:20`; `PLAN-STATUS-ARCHIVE.md:19` |
| 27 | **Live anchor rot, example 1:** `17-IMPLEMENT-PER-TASK-PANEL-PLAN.md:47` cites `src/agents/code-reviewer.md:70` for the `### Verdict: APPROVE / REQUEST CHANGES / BLOCK` line. That line is `:72` today and `:70` is the structural-integration template line. Pre-existing; recorded, NOT owned | `17-IMPLEMENT-PER-TASK-PANEL-PLAN.md:47`; `src/agents/code-reviewer.md:70`, `:72` |
| 28 | **Live anchor rot, example 2:** plans 05 and 10 call the structural-integration check **§7**; it is numbered **8** in the shipped file (fact 1), because check 9 was appended later. **So this plan APPENDS and never renumbers** — a renumber would falsify three more plan documents | `05-structural-integration-check-plan.md:37`; `10-AUDIT-COMMAND-PORT-PLAN.md:28`, `:386`; `src/agents/code-reviewer.md:33` |
| 29 | `CHANGELOG.md` **does** carry a `## [Unreleased]` section today (verified 2026-08-18) — this differs from what plans 82 and 85 recorded on 2026-08-17, so re-check rather than inheriting their note | `CHANGELOG.md:8` |
| 30 | The consumer-facing Key Rule restates DRY as *"don't repeat logic 3+ times"* — the Rule-of-Three framing F1 must not contradict | `src/CLAUDE.md:212` |
| 31 | **`_UNIVERSAL_SECTIONS` is a CLOSED literal tuple** naming the eleven constitution subsections `/devforge:constitute` extracts, `"§3.6"` among them. **A new numbered subsection would have to be added to it — which is Python, and therefore out of bounds for this plan** | `src/devforge/lib/_constitute/_schema.py:295`–`:300` |
| 32 | **§3.6 gets a special splitter.** `_split_design_principles` recognises a block by the regex `^\*\*([^*]+):\*\*\s*$` — a bold header ALONE on its line, ending `:**` — and labels the rule with the header's first word; the SOLID block is sub-split further. **Lines that match no block header are skipped**, so a §3.6 block whose header does not match that exact shape is silently absent from the extracted rule list | `src/devforge/lib/_constitute/_universal.py:79`–`:133`, `:106`, `:128` |
| 33 | **The §3.6 test already anticipates D2(a) and needs no edit**, provided the block is APPENDED AFTER Narrowing: the rule-count test asserts a `>= 8` FLOOR *"so a future legitimate §3.6 block addition doesn't break a parser-correctness test"*, and its sibling pins that the `*Backed by*` paragraph stays inside **KISS's** parsed body — a block inserted between the KISS bullets and that paragraph would move it and fail | `tests/lib/test_constitute_helper.py:3793`–`:3815`, `:3817`–`:3836`; `src/constitution.md:119`, `:121` |

---

## Decisions — ratify at Phase 0

Each carries a recommendation and the argument against it. **D1 is PRE-RATIFIED by
maintainer directive and is listed for the record, not for decision.**

### D1 — Function-level `DUPLICATE` is High; file-level stays Critical *(PRE-RATIFIED 2026-08-18)*

**The rule.** A verbatim-or-near-verbatim clone of a sibling function, added inside a
MODIFIED file and differing only in literals or a single argument, is reported as
`DUPLICATE` at **High**. The existing file-level verdict semantics are untouched: a
duplicated new FILE stays **Critical** (fact 2).

**Why not Critical.** A within-file clone is cheaper to fix than a parallel module — the
existing function is right there, the call sites are local, and the remedy is usually one
parameter. Critical is reserved in this fleet for *"the change rewrote what already
existed"* at module scale, and flattening the two into one severity would either inflate
the cheap case or deflate the expensive one. **High is inside the fleet-wide enum**
(fact 8), so this introduces no vocabulary.

*Counter-argument, recorded:* severity is what drives the panel's repair loop, and High vs
Critical changes nothing mechanically — `merge-review-panel` branches on the `### Verdict:`
token, not on per-finding severity (fact 7). So the distinction is communicative only. That
is accepted: it tells a human reader how much this costs to fix, which is the whole job of
a severity tier in a report nothing gates on.

**The declare-and-justify escape is preserved and is load-bearing.** A clone the task file,
plan or spec DECLARES and JUSTIFIES classifies as `INTENTIONAL_PARALLEL (reason: …)` and
**passes**. The motivating incident is exactly that case, and it was correct — a rule that
failed it would be a rule that punishes the framework's own working discipline.

### D2 — Where the two-hats rule lives in the constitution *(RATIFIED 2026-08-23 — option (a))*

**Options.** (a) a new titled bold block inside `### 3.6 Design Principles`, alongside the
existing `**Narrowing (restricting shared-code behavior):**` block; (b) a new numbered
subsection (§3.9 or similar).

**RECOMMENDATION: (a), and option (b) is not merely worse — it is out of bounds.** Three
grounds, in ascending order of force:

1. **In-file precedent (fact 12).** §3.6 already ends with a titled block appended after the
   SOLID/DRY/KISS triad, with the same shape the two-hats rule needs — a bold title, a short
   bullet list, no new numbering — so (a) mirrors an existing form rather than inventing one.
   §3.6 is also where the DRY-versus-premature-abstraction tension already lives (fact 10),
   and two-hats is the sequencing rule for that same tension.
2. **(b) requires Python, which this plan does not write (fact 31).** `_UNIVERSAL_SECTIONS`
   is a closed literal tuple; a §3.9 that is not in it is simply not extracted by
   `/devforge:constitute`, and adding it is a helper edit. **This alone decides the
   decision** under the plan's own constraint.
3. **(a) requires no code change and no test change (facts 32, 33).** The §3.6 splitter
   already handles arbitrary bold-header blocks, and the rule-count test was deliberately
   written as a `>= 8` floor *"so a future legitimate §3.6 block addition doesn't break a
   parser-correctness test"*. **The two-hats block becomes a ninth extracted rule for free.**

**RATIFIED 2026-08-23 — option (a), the titled bold block inside §3.6.** Fact 31 was
re-verified from the code at ratification: `_UNIVERSAL_SECTIONS` is still a closed literal
tuple of eleven `§`-strings, so option (b) would require a helper edit this plan does not
make. The decision is forced by that constraint, not chosen on taste.

**Two formatting requirements fall out of facts 32 and 33, and Phase 2 must honour both:**

- **The block header must be a bold title alone on its line, with the colon INSIDE the bold
  markers** — exactly the shape the Narrowing and KISS headers already use. Anything else is
  skipped by the splitter and the block is **silently absent** from the extracted rule list.
  Silent absence, not an error. Copy the Narrowing header's punctuation character-for-
  character and change only the words.
- **Append the block AFTER the Narrowing block, at the end of §3.6.** The `*Backed by*`
  paragraph at `src/constitution.md:119` parses as part of **KISS's** body, and a test pins
  it there (fact 33). A block inserted between the KISS bullets and that paragraph would
  capture it and fail that test.

*Counter-argument, recorded:* a titled block inside §3.6 is less findable than a numbered
section, and §3.6 is already the constitution's longest universal subsection (SOLID + DRY +
KISS + a forcing-functions backing note + Narrowing). Adding a fifth block makes it longer
still. The defence is that findability in this framework comes from grep and from the
command text that cites the rule by concept-name, neither of which improves with a number —
and that `src/commands/plan/main.md:471` cites `§3.5` by number while agent files are
forbidden to cite `§`-numbers at all (fact 9), so a new number would land in a convention
this repo is already moving away from.

### D3 — F3's single mandatory action: DECLARE ALWAYS *(RATIFIED 2026-08-23 — declare-always)*

**RATIFIED 2026-08-23 — DECLARE-ALWAYS, and the declaration is checked by NOTHING.** The
obligation is *declare*; only the CONTENT varies between "net precedes" and "window
accepted". The `OR` phrasing is forbidden by name under the zero-escape-hatch policy, which
is why no arm-choosing form was available to ratify. **This ratification claims visibility,
not enforcement** — a reading of it as "regression nets are now required" claims more than
this plan builds, and Phase 6's ledger entry must not drift into that claim.

**The trap this decision exists to avoid.** The obvious phrasing — *"the net task precedes
the restructuring task, OR the window is declared"* — is an OR-clause, and this repo's
zero-escape-hatch policy forbids it by name. Every restructuring task would take the
cheaper arm.

**RECOMMENDATION — one rule, no OR.** When `plan.md` declares behavior-preserving
restructuring of existing code that has no covering tests, the restructuring task **MUST
carry a regression-net declaration**. The declaration always exists; only its CONTENT
varies, and both contents are a statement of fact rather than a choice of obligation:

- `Regression net: precedes — task NNN` (the net task is upstream in the dependency graph),
  or
- `Regression net: window accepted — <reason>` (no net precedes; the exposure is named).

**Net-first is the stated DEFAULT the architect departs from only by writing the second
form.** The rule is *declare*, not *choose*: an author who writes nothing has broken one
rule, not picked an arm.

**Where the declaration lives, and this is forced rather than preferred.** Facts 17 and 18
are the constraint: a new `**Regression net**:` header field would need a new
`render-task-file` flag, which is Python, which this plan does not write. So the
declaration lands in the task's free-form `## Change Details` section, authored with the
fixed literal prefix `Regression net:` so it is greppable by a human without any validator
existing to grep it.

*Counter-argument, recorded, and it is the strongest one in this file:* a declaration with
no mechanical check is a sentence, and the second form (*window accepted*) is a
self-attestation an author can write in four words. **This rule does not prevent the
uncovered window; it makes the window NAMED at the point of decomposition instead of
discovered by a reviewer afterwards.** That is the honest claim and it must not be
overstated at Phase 6's ledger entry. It clears plan 77's visibility bar — a restructuring
task file with no `Regression net:` line reads wrong on its face, and no design principle
is needed to see it — but the bar is visibility, not enforcement.

*Second counter, recorded:* the trigger — *"existing code that has no covering tests"* —
is a claim about test coverage that nobody in `/devforge:breakdown` computes. The architect
answers it from the Phase 1 file analysis, which reads the files but does not run coverage.
So the rule fires on the architect's belief about coverage. Accepted: the alternative is a
coverage tool invocation, which is a mechanical gate, which is out of bounds by the plan's
own constraint. Say so rather than implying the trigger is measured.

### D4 — The smells shortlist *(RATIFIED 2026-08-23 — all six)*

**RATIFIED 2026-08-23 — ALL SIX, named: Feature Envy, Data Clumps, Primitive Obsession,
Message Chains, Shotgun Surgery, Divergent Change.** The trim to the three
mechanically-recognizable ones was a real option and was declined; the counter-argument
below stands unanswered rather than refuted, and **Phase 7 case 5's dismissal count is the
evidence that decides whether the trim happens later**.

| Smell | Category | Why this Category |
|-------|----------|-------------------|
| Feature Envy | `system_design` | a method reaching across an object boundary for another's data is a responsibility-placement defect |
| Data Clumps | `best_practice` | the same field group travelling together un-typed is a local idiom fix |
| Primitive Obsession | `best_practice` | a primitive standing in for a domain concept is a local idiom fix |
| Message Chains | `best_practice` | a long navigation chain is a local coupling idiom |
| Shotgun Surgery | `system_design` or `duplication` per the finding's evidence | one conceptual change forcing many small edits is either a placement defect or a copy-set |
| Divergent Change | `system_design` or `duplication` per the finding's evidence | one module changing for several unrelated reasons is either cohesion or a copy-set |

**The two-Category rows follow an existing convention in the sibling checklist rather than
inventing one** — `/devforge:review`'s performance section already routes one pattern to
either `system_design` or `best_practice` and requires the finding to *"State which one and
why."* Copy that requirement verbatim in substance.

**Each smell entry MUST demand quoted code evidence**, in the form the section's existing
bullets already use (*"Quote both occurrences."*, *"Quote the offending import or call that
crosses the boundary."*). A smell entry without a quote demand is a licence to report a
vibe.

**This phase must not regress plan 19's precision.** Smell findings enter the same
refutation stage as every other audit finding, unchanged, and the checklist's own Judgment
rule already forces a subjective finding to `Likely` / `Speculative` — most named smells
are judgment calls, so most will land there. **Do not add a smell-specific confidence
carve-out.**

*Counter-argument, recorded:* Feature Envy, Divergent Change and Shotgun Surgery are the
three smells with the highest false-positive rate in practice — each is a judgment about
what a module *ought* to be responsible for, and an LLM hunting them on a codebase it did
not design will find them everywhere. **A ratifier who wants a smaller blast radius should
trim to the three mechanically-recognizable ones (Data Clumps, Primitive Obsession, Message
Chains) and record the trim as deliberate**, rather than shipping six and discovering the
noise at Phase 7.

### D5 — Whether §6.1 gets the clarifying sentence *(RATIFIED 2026-08-23 — yes, both)*

**RATIFIED 2026-08-23 — YES, both the plan-side guidance AND the §6.1 clarification.**

**Scope AMENDMENT ratified at the same sitting: Phase 5 gains a THIRD site,
`src/agents/architect.md` Rule 9.** This was NOT in the plan as drafted, and it is a
reconciliation debt against plan 84, which shipped after this file was last edited. Rule 9
today is titled *"Minimal scope & the six decision-recording forcing steps."* and its body
already declares that *"this Rule's minimal-scope mandate (above) stays sovereign over that
advisory (MAY) lane"*. **F5 writes a MAY lane into `/devforge:plan`'s sub-question 5 — the
architect's own question** — so without a matching sentence in Rule 9 the architect has
textual grounds in its own Rules section to refuse the guidance it was just given. This is
the same contradiction shape D5 identifies for §6.1, one layer down. The edit is one
sentence: a restructuring unit PLANNED in `plan.md` is not the speculative architecture
Rule 9 bans. **The minimal-scope mandate itself is not weakened, and Rule 9 is NOT
renumbered** — plan 84 established that its heading name is load-bearing for five citing
sites, all of which cite by rule number or step name, never by heading text.

§6.1 currently reads, in full: *"Every code change MUST impact as little code as possible.
Do not refactor, improve, or 'clean up' code outside the scope of the current task. A bug
fix changes the bug. A feature adds the feature. Nothing more."* (fact 13). **That wording
is absolute, and a reviewer reading it against a planned preparatory task has textual
grounds to call the task a violation** — which is exactly the failure F5's fix exists to
prevent. The plan-side sentence alone would create a rule the plan says yes to and the
constitution says no to, and the constitution is the higher authority in every agent's
Rules section.

**The clarification is one sentence and it NARROWS nothing about the ban:** a restructuring
task PLANNED in `plan.md` is in scope by definition, because the ban's subject is unplanned
drive-by editing, not planned work. **The ban itself stays** (see `## Non-goals`).

*Counter-argument, recorded:* every carve-out written into an absolute rule is a crack, and
this framework's zero-escape-hatch policy exists because cracks get widened. An LLM that
reads *"a planned preparatory task is in scope"* can rationalize almost any scope creep as
preparatory. The defence is that the sentence's condition is **objective and externally
checkable** — the task exists in `plan.md`, or it does not — rather than a judgment call
like "reasonable" or "trivial". **Phase 5 must write it with that condition load-bearing**;
a version that says "preparatory work is in scope" without anchoring on the plan document
is the crack the counter-argument predicts.

---

## Open questions (Phase 0)

### OQ-1 — Does F2's partition requirement apply to ALL tasks, or only mixed ones? *(RESOLVED 2026-08-23)*

*Resolved:* **ONLY MIXED TASKS, with the objective trigger** — the task's Files table
touches an existing function it does not delete, **AND** the task also changes observable
behavior. Both conjuncts are checkable against the task file itself. The every-task
fallback was declined: it would put a degenerate line in `## Change Details` on every task
file forever, which `/devforge:implement` then reads on every task.

**Phase 5 inherits a consequence from this arm and must state it plainly**: a purely
preparatory unit changes no observable behavior, so the second conjunct is false and
**F2's partition requirement and its code-reviewer check do not apply to it at all**. Its
behavior preservation is carried by its own preservation contracts and by nothing else.
A Phase-5 sentence claiming the partition "applies trivially" is FALSE under this arm.

**The tension is real and must be resolved rather than smoothed.** "Only mixed tasks"
introduces a trigger the author evaluates about their own task, which is the shape the
zero-escape-hatch policy distrusts. "Every task" introduces a field that is degenerate on
the overwhelming majority of tasks, which is how a required field becomes ritual noise that
authors fill with a placeholder.

**Recommendation: only mixed tasks, with an OBJECTIVE trigger** — the task's Files table
touches an existing function it does not delete, **AND** the task also changes observable
behavior. Both halves are checkable against the task file itself: the Files table names the
files and its `Action` column reads Create/Modify, and the task's Spec criteria line names
the ACs whose behavior it changes.

**If the ratifier judges that trigger too fuzzy, the fallback is: the partition is
mandatory on EVERY task, trivially filled** (a pure-feature task's partition is
*"behavior-changing: all touched surfaces; behavior-preserving: none"*). **Pick one at
Phase 0.** Leaving it to Phase 2 is how a trigger with an unwritten evaluation rule ships.

*Recorded, because it decides the answer for some ratifiers:* under the every-task
fallback, the field lands in `## Change Details` on every task file in the repo, which is
strictly more text for `/devforge:implement` to read on every task, forever. The
only-mixed-tasks arm pays nothing on tasks that do not qualify.

### OQ-2 — Does F1's function-level arm also apply to `/devforge:fix`? *(RESOLVED 2026-08-18)*

*Resolved:* **YES, automatically, and it needs no `/devforge:fix` edit** — resolved at
drafting from the code rather than by a maintainer decision, which is why it needs no
Phase-0 ratification. Fact 6 is the whole answer: `/devforge:fix` PHASE 4 runs the
four-reviewer panel *"EXACTLY as `/devforge:implement` PHASE 6"* and dispatches each reviewer
with `subagent_type`, which *"loads that reviewer's persona from `.claude/agents/<agent>.md`;
do NOT re-inline the persona"*. There is no second copy of the code-reviewer checklist
anywhere under `src/` (fact 6).

**This is stated as a fact to RE-VERIFY in Phase 1's Verify, not as a fact to trust from
this file.** A future session that inlines a reviewer persona into any command would
falsify it silently.

**Two more consumers ride along, and both are fine (fact 25):**

- **`/devforge:review`** loads the same persona as a Batch-A finder, but its brief injects
  the anti-relitigation preamble, whose out-of-scope rule (fact 5) dominates: a
  single-task-contained clone is out of scope there and stays out of scope. **F1 does not
  widen `/devforge:review`.**
- **`/devforge:audit`** loads it as a Batch-A hunter with the duplication checklist already
  injected (fact 23). The function-level arm is consistent with that section's
  copy-pasted-logic bullet, not in tension with it.

---

## Phases

### Phase 0 — Ratification *(HARD stop for Phases 2–5; Phase 1 may run first)*

The maintainer resolves D2–D5 and OQ-1, recording under each the chosen option plus one
sentence of reason. **D1 is already ratified** by the 2026-08-18 directive, and **Phase 1
may execute before this phase closes** — it depends on no other decision here. **OQ-2 is
already resolved** (2026-08-18, from the code) and carries no ratification duty; Phase 1's
Verify re-verifies its fact rather than re-deciding it.

Re-check facts 1, 5, 6, 17, 18, 20 and 31 before ratifying — they are the scope and
constraint argument, and each is checkable in under a minute. **Fact 31 in particular
decides D2 on its own**: option (b) needs a helper edit this plan does not make.

**Verify:**

- `grep -n "^### D[1-5] " 86-FOWLER-REFACTORING-GAPS-PLAN.md` returns five lines and **none
  of them contains `(OPEN`** — the marker is `*(OPEN)*` on D2/D4/D5, qualified on D3
  (`*(OPEN — the load-bearing decision)*`), and D1 carries `*(PRE-RATIFIED 2026-08-18)*`,
  so match the substring, not the exact token. Each heading's decision carries a recorded
  confirm-or-override.
- **OQ-1 opens with a `*Resolved:*` sentence, in the form OQ-2 already carries**, and **its
  answer names one arm** — objective trigger or every-task — because Phase 2 cannot be
  written without it. OQ-2 needs nothing here; it is already resolved.
- **The D4 pick names the smells by name**, not "the recommended set" — a trim is a real
  option and must be legible as one.
- **The D3 pick records that the rule is DECLARE-ALWAYS**, and that the declaration is not
  mechanically checked. A ratification that reads "regression nets are now required" claims
  more than this plan builds.
- The status line at the top of this file names the ratification date.
- `git status` shows no `src/` file modified for Phases 2–5.

---

### Phase 1 — F1: the function-level arm in `code-reviewer` *(pre-ratified; may run first)*

**Route: instruction-author → instruction-reviewer + claude-code-guide.**
`src/agents/code-reviewer.md` ships into a consumer's `.claude/agents/`, so the
claude-code-guide check is required, not optional.

Scope, all in `src/agents/code-reviewer.md`:

- **Check 8 gains a function-level arm** (fact 1). For each newly ADDED function/method in
  a MODIFIED file: one targeted search of the same module plus its obvious siblings for a
  near-identical function. A verbatim or near-verbatim copy differing only in literals or a
  single argument is `DUPLICATE` at **High** (D1) **unless the task file, plan or spec
  declares and justifies it**, in which case it is `INTENTIONAL_PARALLEL (reason: …)` and
  passes.
- **The existing search bound is KEPT and EXTENDED to cover the new arm** — *"One targeted
  search pass, not a full repo audit."* The current closing sentence *"Skip files that only
  edit existing modules"* becomes false for the function-level arm and must be rewritten to
  scope to the file-level arm only. **It is the one sentence in this phase that a careless
  edit will leave contradicting the addition.**
- **The verdict sentence at `:45` gains the function-level case** — file-level `DUPLICATE`
  Critical, function-level `DUPLICATE` High, `INTENTIONAL_PARALLEL` unchanged.
- **The output template at `:70` gains a second entry shape** so a function-level finding
  has a home — e.g. `- [new-function in modified-file]: …` beside the existing
  `- [new-file]: …` line.
- **Check numbering is APPENDED-TO, never renumbered** (fact 28). Check 8 stays check 8.

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean.
- `grep -n "newly created" src/agents/code-reviewer.md` and
  `grep -n "only edit existing modules" src/agents/code-reviewer.md` return lines that are
  **true after the change** — the second is the sentence most likely to be left stale.
  Capture the pre-change output first.
- `grep -c "^[0-9]\+\. \*\*" src/agents/code-reviewer.md` returns the SAME count as before
  the change (nine numbered checks) — this phase extends check 8, it does not add a check.
- The declare-and-justify path survives verbatim in substance: a clone the task/plan/spec
  justifies is `INTENTIONAL_PARALLEL`, not a downgraded `DUPLICATE`. **This is the
  motivating incident's own path and a diff that closes it has inverted the finding.**
- `python3 -m unittest` over `tests/lib/_implement/` passes **unchanged** — fact 7 says the
  heading `### Structural Integration` is fixture text and the parser reads `### Verdict:`,
  so a test failure here means something outside this plan's scope moved.
- **OQ-2's fact is RE-VERIFIED, not assumed:** `grep -rn "code-reviewer" src/commands/`
  shows every dispatch loading the persona from the agent file, with no command inlining a
  reviewer checklist.
- **`CLAUDE.md`'s plan-05 index line is amended with a one-line plan-86 pointer** (fact 26)
  — the entry currently describes a file-only scope. **Do NOT rewrite
  `05-structural-integration-check-plan.md` itself**; a one-line pointer there is the
  maximum.
- No `§`-number constitution reference is introduced by this phase (fact 9). The
  pre-existing `§3.5` at `:37` is **left alone** and reported to the orchestrator.

---

### Phase 2 — F2: the two-hats rule

**Route: instruction-author → instruction-reviewer** for every file in this phase; **+
claude-code-guide for BOTH `src/agents/code-reviewer.md` AND `src/commands/breakdown/main.md`**
— both ship into a consumer's `.claude/` (`.claude/agents/code-reviewer.md` and
`.claude/commands/devforge/breakdown.md`), so both carry the Claude-Code-integration check.
`src/constitution.md` does not ship into `.claude/` and needs only the instruction loop.

Scope, three sites stating ONE standard:

- **`src/constitution.md` §3.6** — a new titled bold block per D2, mirroring the
  `**Narrowing (restricting shared-code behavior):**` block's shape (fact 12) and
  **APPENDED AFTER it, at the end of §3.6** (fact 33). Its header must be a bold title
  alone on its line ending `:**`, or the `/devforge:constitute` splitter drops it silently
  (fact 32). Its content: when a task both restructures existing code and changes behavior,
  its task file MUST partition the touched functions/files into **behavior-changing** and
  **behavior-preserving** surfaces, and the behavior-preserving surfaces carry
  preservation-style produce-contracts.
- **`src/commands/breakdown/main.md`** — the same requirement stated once in the
  task-authoring rules around the `**Header fields**` bullet (fact 17's neighbourhood), so
  **the partition is PRODUCED at decomposition** rather than hoped for at review. Per facts
  17 and 18 it lands in `## Change Details` (the partition) and `### Produces` (the
  preservation contracts) — **not in a new header field.**
- **`src/agents/code-reviewer.md`** — ONE appended numbered check (it becomes check 10):
  verify that surfaces the task declares behavior-preserving are actually preserved by the
  diff. **Appended, never renumbered** (fact 28). **Cite the two-hats rule by concept-name,
  never by `§`-number** (fact 9).

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean.
- `grep -n "behavior-preserving" src/constitution.md src/commands/breakdown/main.md src/agents/code-reviewer.md`
  returns all three sites, and the three state the SAME standard — **read all three as
  landed, not from this plan's description of them.**
- `grep -c "^[0-9]\+\. \*\*" src/agents/code-reviewer.md` returns exactly ONE more than
  after Phase 1, and checks 1–9 carry their original numbers.
- **No new `render-task-file` flag exists** — `grep -n "add_argument" src/devforge/lib/breakdown_helper.py`
  shows the same flag set as before, and `git status` shows no `src/devforge/lib/` file
  modified. This is the plan's instruction-only constraint, checked mechanically.
- **`python3 -m unittest` over `tests/lib/test_constitute_helper.py` passes with the test
  file BYTE-UNCHANGED** (fact 33). The `>= 8` floor absorbs the ninth rule and the KISS
  `*Backed by*` guard still holds. **A failure here means the block was placed wrong** —
  before the `*Backed by*` paragraph rather than after Narrowing — not that the test needs
  updating.
- **The new block appears as an extracted §3.6 rule**, confirmed by running
  `constitute_helper._parse_universal_blocks` over `src/constitution.md` and seeing its
  label among `d["§3.6"]["rules"]` (fact 32). A block whose header shape is wrong is absent
  here **silently**, with no error anywhere.
- The preservation-contract idiom is described as riding `### Produces`, which already
  exists (fact 18) — a diff that invents a new section has misread facts 17/18.
- OQ-1's ratified trigger appears in the breakdown text in the arm Phase 0 picked, and the
  constitution block does not contradict it.
- **No `§`-number constitution reference in the agent file** (fact 9), and the constitution
  block does not cite a command by phase number.

---

### Phase 3 — F3: the regression-net declaration + net-first default

**Route: instruction-author → instruction-reviewer + claude-code-guide** (this file ships
to `.claude/commands/devforge/breakdown.md`).

Scope, in `src/commands/breakdown/main.md`:

- **The ordering default**, stated where task ordering already lives. **Fact 21 is the
  authoring constraint that shapes this**: the greenfield sequence at `:165` is a
  *greenfield* list and this rule is about EXISTING code, so it belongs with the
  `### If existing codebase` material or in the PHASE-3 task-authoring rules — **not
  appended to the greenfield five-step sequence**, which would make that list wrong for its
  own subject.
- **The declaration**, per D3's ratified shape: authored into the restructuring task's
  `## Change Details` with the fixed literal prefix `Regression net:` and one of the two
  contents. **Model the prose on the change-induced dead-code subsection** (fact 22), which
  is this file's established way of turning a plan-declared obligation into a task-level
  carry — including its habit of arguing WHY the obligation rides a particular task rather
  than becoming its own.
- **State the honest bound in the emitted text**: nothing checks the declaration. It is an
  authoring duty, and the reason it is worth having is that its absence is visible.

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean.
- `grep -n "Regression net" src/commands/breakdown/main.md` returns the authoring rule and
  the fixed prefix, with the two permitted contents both shown.
- **`grep -n "Greenfield task ordering" src/commands/breakdown/main.md` still returns the
  greenfield sequence unchanged** — the new rule did not attach itself to a list about
  creating new files (fact 21).
- **The rule reads as ONE obligation, not two arms of a choice.** Instruction-reviewer
  confirms there is no `OR` / `either … or` construction in the obligation sentence: the
  obligation is *declare*; the content varies. This is the single most likely defect in the
  phase.
- **No new `verify-*` verb, no new PHASE-3.5 gate, no new hard-fail validator** — plan 75's
  tripwire, both halves. **Grep the INVOCATION shape, not the bare verb name:**
  `grep -n "breakdown_helper verify-" src/commands/breakdown/main.md` returns exactly **six**
  lines today (verified 2026-08-18) — `verify-contract-chain`, `verify-ac-coverage`,
  `verify-agent-roster`, `verify-manifest-present`, `verify-property-coverage`,
  `verify-dead-code-coverage` — and must return the same six after this phase. A bare
  `grep -n "verify-"` returns eleven lines because five are prose mentions, so it does not
  answer this question. `git status` also shows no `src/devforge/lib/` change.
- The emitted text does not claim the declaration is enforced.

---

### Phase 4 — F4: the named-smells subsection

**Route: instruction-author → instruction-reviewer.** This file is a reference injected
verbatim into agent briefs (fact 24); it does not itself ship into `.claude/`.

Scope, in `src/commands/audit/references/best-practices-checklist.md`:

- A compact named-smells subsection carrying D4's ratified shortlist, each entry naming its
  `Category` from the existing six values and **demanding a quote in the form the file's
  existing bullets already use** (fact 23).
- The two-Category smells (Shotgun Surgery, Divergent Change, if ratified) carry the
  *"State which one and why"* requirement, copied in substance from the sibling checklist's
  performance-section convention (D4).
- Placement: adjacent to `Duplication & divergence`, before the
  `Constitution-principle adherence` section, so the file's existing order (system design →
  best practices → duplication → constitution) is not disturbed.

**Verify:**

- Instruction-reviewer clean.
- **The two `Category` enum statements at the file's head and foot are byte-unchanged**
  (fact 23), and every added entry's `Category` names a value from those six. Check by
  reading the added entries, since one existing section header legitimately reads
  `Category: matches the violated dimension` rather than an enum value — a naive
  `grep -n "Category:"` does not answer this question by itself.
- Every added smell entry contains an explicit quote demand; a grep for the added smell
  names shows each within two lines of a "Quote" instruction.
- `python3 -m unittest` over `tests/lib/_audit/` passes unchanged — fact 24 predicts it
  will, since the pinned strings (`BEST-PRACTICES`, `Type-safety suppression`) are
  untouched. **A failure here means the section header or the type-safety bullet was
  disturbed.**
- **No smell-specific confidence carve-out was added** — the file's existing Judgment rule
  covers them, and the refutation stage is unchanged (plan 19).
- `src/commands/review/references/emergent-issue-checklist.md` is **byte-unchanged** — the
  scoping decision in `## Non-goals` is verified by an empty diff, not by intent.

---

### Phase 5 — F5: the preparatory-refactoring lane

**Route: instruction-author → instruction-reviewer + claude-code-guide** (the command file
ships to `.claude/commands/devforge/plan.md`).

Scope:

- **`src/commands/plan/main.md`** — architect guidance: when the minimal change is awkward
  because the existing structure resists it, the architect MAY plan a separate preparatory
  restructuring step, sequenced FIRST, itself behavior-preserving with preservation
  contracts.
- **`src/constitution.md` §6.1** (ratified under D5) — one sentence: a restructuring
  task PLANNED in `plan.md` is in scope by definition; the ban targets unplanned drive-by
  edits. **Write the plan-document condition as the load-bearing clause** (D5's
  counter-argument).
- **`src/agents/architect.md` Rule 9** (the THIRD site, ratified 2026-08-23 as a scope
  amendment under D5) — one sentence inside the existing Rule 9, saying that a
  restructuring unit PLANNED in `plan.md` is not the speculative architecture the
  minimal-scope mandate bans. **The heading is byte-unchanged** (plan 84 fixed its wording
  and five sites cite this rule by number or by step name), **the rule is not renumbered**,
  the six forcing steps are byte-unchanged, and the minimal-scope mandate is not weakened —
  the sentence names one already-planned case as in scope, exactly as §6.1's does.
  **Cite the constitution by concept-name, never by `§`-number** (fact 9).

**How F2 interacts with a preparatory unit depends on which arm OQ-1 ratified, and the
drafted text must say which — it is NOT a trivial pass under both.** A purely preparatory
unit changes no observable behavior by construction, so:

- **OQ-1 = every-task** → the partition applies and is degenerate: **all** touched surfaces
  are behavior-preserving, none behavior-changing. F2's code-reviewer check then reads the
  whole diff against that declaration, which is the strongest form of the preservation
  claim.
- **OQ-1 = mixed-only (the recommended arm)** → the unit **fails F2's trigger**: it touches
  existing functions but changes no observable behavior, so the second conjunct is false and
  **F2's partition requirement and its code-reviewer check do not apply at all.** The
  preparatory unit's behavior-preservation is then carried by its own preservation contracts
  and by nothing else. **Write that plainly rather than implying F2 covers it** — a reader
  who believes a check is watching this unit when none is has exactly the false confidence
  this plan exists to remove.

**Two authoring forks recorded here rather than pre-decided, because both are real:**

1. **Placement in `plan/main.md`.** Sub-question 5 already asks for the MINIMAL change and
   calls its answer *"the baseline the Key Design Decisions must not exceed without
   justification"* (fact 20) — which is precisely the tension this guidance resolves, so
   extending sub-question 5 keeps the two halves of one thought together. The alternative
   is a twelfth sub-question, which renumbers nothing (fact 20 — the two gated subsections
   name sub-questions 8 and 9, and appending a twelfth leaves both true) but grows an
   already-eleven-item list. **Decide it where the text is written, with the surrounding
   sub-questions visible.**
2. **Vocabulary.** `/devforge:plan` does not author TASKS — `/devforge:breakdown` does. A
   plan expresses a preparatory unit as a Key Design Decision plus its File Impact rows,
   and `/devforge:breakdown` PHASE 2 decomposes that into a task sequenced first. **The
   emitted text must use the vocabulary of the command it lives in**; writing "plan a
   preparatory task" into `plan/main.md` would name an artifact that command does not
   produce.

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean.
- `grep -n "Do not refactor" src/constitution.md` still returns **both** ban statements
  (fact 13). The `4.2 NEVER Do` line is **byte-unchanged**, and §6.1's existing sentence is
  byte-unchanged with the clarification ADDED after it — the ban is not rewritten, only
  followed. An empty diff on the `4.2` line is how the non-goal is verified.
- The §6.1 sentence (if ratified) conditions on the task being planned in `plan.md`, and an
  instruction-reviewer read confirms it cannot be read as licensing unplanned cleanup.
- `grep -n "preparatory" src/commands/plan/main.md src/constitution.md` returns both sites
  and they agree.
- **The plan-side text uses `/devforge:plan` vocabulary** (decision / File Impact row), not
  task vocabulary (fork 2).
- **The drafted text states the OQ-1 arm's actual consequence for F2**, in the arm Phase 0
  ratified. Under the mixed-only arm it must say the preparatory unit does not meet F2's
  trigger and no F2 check applies — **a sentence claiming the partition "applies trivially"
  is FALSE under that arm** and is the specific defect this criterion exists to catch.
- The guidance is permissive (MAY), never obligatory — a mandatory preparatory step would
  be a new gate and is out of bounds.

---

### Phase 6 — Cross-reference sweep + ledger reconciliation

**Route: instruction-author → instruction-reviewer** for every `src/` and plan-document
edit.

Open the phase with
`grep -rn "newly created\|Structural Integration\|Rule of Three\|refactor surrounding\|behavior-preserving" src/ *.md`
and reconcile the result against the sites Phases 1–5 touched. **This sweep list is NOT
certified exhaustive** — treat a hit not named in this plan as an omission in this plan,
not as a new defect.

Scope:

- `CHANGELOG.md` — an entry. **Verified 2026-08-18 by reading the file: a `## [Unreleased]`
  section EXISTS at `:8`** (fact 29 — this differs from what plans 82 and 85 recorded a day
  earlier, so re-check rather than inheriting either note). Add under `## [Unreleased]`.
- repo-root `CLAUDE.md` and `PLAN-STATUS-ARCHIVE.md` — this plan's entries move from NOT
  STARTED to the shipped wording, and plan 05's index line carries the Phase-1 pointer if
  Phase 1 did not already add it.
- `src/CLAUDE.md` — **check only.** Its Key Rule 11 restates DRY as *"don't repeat logic 3+
  times"* (fact 30); nothing in this plan contradicts it, and **recording that no-op as
  deliberate** is what stops a later session from "harmonizing" it into a rule against two
  occurrences.

**Verify:**

- The sweep returns zero dangling references; `python3 -m unittest` over `tests/` is green.
- **`git status` shows ZERO files modified under `src/devforge/lib/`** across all phases —
  the instruction-only constraint, checked once at the end as well as per-phase.
- **No new check number and no new unnumbered hard-fail validator exists anywhere** — plan
  75's tripwire, both halves, verified by diff rather than by assertion. **"Check number"
  here carries the Non-goals disambiguation**: it means the Python-side PHASE-3.5 `verify-*`
  gate sequence, not `code-reviewer.md`'s prose checklist, which Phase 2 legitimately grew
  from nine items to ten.
- **No plan vocabulary in emitted text** — "D1", "F3", "Phase 2" and this plan's number are
  maintainer vocabulary. Emitted text names only the command's own phases, the agent's own
  checks, and the constitution's own concept names. **"Two hats" is NOT plan vocabulary** —
  it is the rule's concept name, in the same class as the shipped "Narrowing", "SOLID",
  "DRY" and "KISS" blocks, and it belongs in the emitted text.
- `scripts/verify-agent-reachability.py` and `scripts/verify-memory-lane.py` pass (nothing
  here touches either, so a failure means something unintended moved).
- **The two live anchor-rot items (facts 27, 28) are still recorded as NOT fixed**, or
  fixed deliberately with a note — silently repairing them inside this plan's commits makes
  them invisible to whoever owns them.

---

### Phase 7 — Consumer observation *(user-driven HARD GATE)*

**Known-answer anchors.** The correct outcome is known in advance for each case, so this is
a regression anchor rather than an exploratory run. **This is the ONLY place F1's
false-positive rate is observed**, and no phase above may claim it.

1. **The undeclared-clone case (F1).** A task that adds a near-verbatim clone of a sibling
   function inside a MODIFIED file, with **no** declaration in task/plan/spec, **MUST** come
   back `DUPLICATE` at High and **MUST** keep the panel from going clean.
2. **The declared-clone case (F1).** The same diff **with** the plan/task declaration and
   rationale present **MUST** come back `INTENTIONAL_PARALLEL (reason: …)` and **MUST**
   pass. **This is the motivating incident replayed; a failure here means the rule punishes
   the discipline it was written to protect.**
3. **The no-false-positive case (F1).** A task adding a genuinely new function beside
   same-shaped siblings (same pattern, different responsibility) **MUST NOT** be flagged.
   This is plan 05's original smoke-test shape, at function scope.
4. **The mixed-surface case (F2).** A task that both restructures and changes behavior
   **MUST** carry the partition, and the panel check **MUST** read the declared preserving
   surfaces against the diff.
5. **The smells noise check (F4).** One `/devforge:audit` run over a codebase with known
   smells: record how many smell findings survived refutation and how many were dismissed.
   **A high dismissal rate is D4's trim signal**, not a defect in the refutation stage.

**Verify:**

- Each of the five is scored **explicitly** — stated, not summarized.
- **Cases 1 and 3 are scored as a PAIR.** A rule that catches case 1 by flagging everything
  fails case 3, and the two are only meaningful together.
- **Case 5's dismissal count is recorded as a number**, even if unsurprising — an unrecorded
  number cannot be compared against later, and D4's trim option has no other evidence
  source.
- Record the result in `REGRESSION-ANCHORS.md`, naming the observed behavior against the
  Phase-1 and Phase-4 text.
- **If it fails**, record the negative here with the artifacts and identify which mechanism
  produced it before proposing anything further — a missed clone on case 1 is a D1/Phase-1
  wording finding, a false flag on case 3 is a search-bound finding, and a noisy case 5 is a
  D4 finding. They have different fixes.

---

## Non-goals

- **Removing or weakening the opportunistic-refactoring ban.** Both statements of it stay
  (fact 13). The ban guards against LLM scope creep, which is a live failure mode in this
  framework, and F5's clarification narrows nothing about it — it names one already-planned
  case as in-scope. **A phase that starts deleting "Do not refactor surrounding code" has
  left this plan.**
- **Any Python.** No new helper verb, no new `render-task-file` flag, no new validator, no
  new check number, no new mechanical gate — plan 75's tripwire, both halves. **Facts 17,
  18 and 31 mean this is a real constraint on F2 and F3, not a stylistic preference**: the
  task-file header field those findings would naturally want is Python (so they use
  free-form task sections instead), and a new numbered constitution subsection would need a
  new entry in `_UNIVERSAL_SECTIONS` (so D2 recommends a titled block instead).
  **Disambiguation, because the plan uses one word for two unrelated enumerations:**
  *"check number"* in this constraint means the Python-side PHASE-3.5 `verify-*` gate
  sequence in `/devforge:breakdown`, **not** `code-reviewer.md`'s prose checklist numbering
  — which Phase 2 **does** extend by one, from nine items to ten. The two are separate,
  unrelated enumerations, and extending the prose checklist adds no gate.
- **Any change to `/devforge:constitute`'s universal-rule extraction.** `_UNIVERSAL_SECTIONS`
  (fact 31) and `_split_design_principles` (fact 32) are read here as CONSTRAINTS on where
  F2's text may go, never as surfaces to modify. F2's block is designed to be extracted by
  the splitter exactly as it stands.
- **New `Category` enum values** (fact 23). All six smells map onto the existing six.
- **Widening `/devforge:review`'s scope.** Its checklist is emergent-cross-task by
  construction (facts 4, 5) and per-file smells belong to `/devforge:audit`. Phase 4's
  Verify pins `emergent-issue-checklist.md` byte-unchanged. **A per-task duplication finding
  reaching `/devforge:review` is a defect in F1's placement, not an argument to widen that
  command.**
- **Back-porting these rules into already-shipped consumer installs.** They arrive through
  the normal `install.sh` / `update.sh` path. No migration, no backfill, no rewrite of any
  already-rendered `constitution.md`.
- **Renumbering `code-reviewer`'s checks** (fact 28). Three plan documents already cite the
  structural-integration check by a stale ordinal; a renumber makes that worse for no gain.
- **Changing what `/devforge:audit`'s refutation stage does** (plan 19). Smell findings
  enter it unchanged; a smell-specific confidence rule is out of bounds.
- **Turning any of the five into a gate.** F3's declaration in particular is a duty, not a
  check. A future session that finds the declaration skipped has a plan-77-style visibility
  argument, not a licence to build a validator this plan's constraint forbids.

---

## Dependencies + related

- **Plan 05** (`05-structural-integration-check-plan.md`) — the check F1 extends. **Amend
  its ledger one-liner only** (fact 26); the plan document itself gets at most a one-line
  pointer. Its two pending manual smoke tests are the ancestors of Phase 7's cases 1–3.
- **Plan 71** (`71-POST-CHANGE-CONSEQUENCE-PLAN.md`) — the change-induced dead-code lane,
  which is F3's structural model (fact 22) and the source of code-reviewer's check 9. **F3
  deliberately does NOT copy its mechanical half** (the `verify-dead-code-coverage` gate),
  because a gate is out of bounds here.
- **Plan 75** — the no-new-check-number / no-new-validator tripwire that binds every phase.
- **Plan 19** — the cry-wolf precision stance D4 is written against.
- **Plan 77** (`77-POST-CHANGE-OUTPUT-MATRIX-PLAN.md`) — the **visibility bar** D3's honest
  bound is measured against. Its own mechanism rests on reasoning rather than evidence
  (Phases 1 and 3 WAIVED); **do not cite it as validated.**
- **Plan 81** (`81-INFERENCE-RULES-PLAN.md`) — **added to this list 2026-08-23; the plan as
  drafted cited it nowhere.** Its F3 shipped a preservation-AC admission rule at
  `/devforge:specify` Step 4.4, keyed on the `behavior_preservation` ROLE (the §5.2
  subsection an AC is added under) and demanding a cited construction site. That is a
  SECOND, stronger preservation carrier alongside fact 16's `record-constraint --kind
  not_break`, and it operates at spec-AC level while F2/F5 operate at task-surface level.
  **Not a contradiction, and not superseded either way — but Phases 2 and 5 must reuse that
  role's vocabulary rather than invent a third**, or the framework ends up with three names
  for behavior preservation and no statement of how they relate.
- **Plan 84** (`84-ARCHITECT-CONSULT-ACCUMULATION-PLAN.md`) — **added 2026-08-23.** It
  CLOSED with a single `src/` diff: `src/agents/architect.md` Rule 9's heading became
  *"Minimal scope & the six decision-recording forcing steps."* That rule is Phase 5's
  ratified third site (D5's amendment note). Its heading is not this plan's to touch.
- **Plan 15** (`15-AGENT-STANDARDIZATION-PLAN.md`) / `src/agents-AUTHORING.md` — the agent
  authoring conventions Phases 1 and 2 must satisfy: the unified severity scale (fact 8) and
  the no-`§`-number rule (fact 9).
- **Plan 17** (`17-IMPLEMENT-PER-TASK-PANEL-PLAN.md`) — the panel F1's finding flows
  through. Its `:47` anchor into `code-reviewer.md` is already stale (fact 27) and this
  plan's edits shift that file further; **recorded, not owned.**
- **Plans 62 / 82 / 85** — the plans that argue about whether a check may become a mandatory
  gate. **None is a dependency and none is touched here.** This plan builds no gate at all,
  so nothing it does engages plan 62's D14, the reversal plan 82 SHIPPED 2026-08-19 (D14
  amended in place: run-mandatory, verdict never binding), or the one plan 85 proposes — and a
  future session must not cite this plan as precedent in either direction.
- **`FINDINGS.md` finding 1** — the §3.6 Narrowing FALSE BINARY. **Untouched.** D2 adds a
  block to §3.6 alongside Narrowing; it does not amend, weaken or resolve that finding, and
  Phase 2 must not be read as doing so.

---

## Context for next session

**The one sentence that governs everything here:** the framework already preserves behavior
well when a plan DECLARES that it is preserving behavior — all five gaps are about the case
where nobody declared anything.

**The origin incident, in the only form this file carries it.** In a consumer install, one
task duplicated an existing builder function into a second builder, verbatim except one call
option. **That duplication was plan-declared, justified, and correct** — a Key Design
Decision carried the decoupling rationale, the spec named the risk, and the plan recorded it
as an accepted DRY tension. **The gap is its undeclared twin.** A build session that reads
the incident as "the framework allowed a bad duplication" has inverted it and will write a
rule that breaks Phase 7's case 2.

**The Fowler grounding, in one line:** refactoring is behavior-preserving restructuring;
the canon adds two hats, self-testing code first, the Rule of Three, the smells catalog, and
preparatory refactoring — and this framework already had the Rule of Three verbatim, part of
the smells catalog, and behavior preservation itself. **The five gaps are the remainder, not
the whole list.**

**All five fixes are instruction-only.** No Python, no validators, no new PHASE-3.5 gate
numbers, no gates. **Phase 2 does add a tenth item to `code-reviewer.md`'s prose checklist**
— that enumeration is unrelated to the gate sequence the constraint names, and the
`## Non-goals` "Any Python" bullet disambiguates the two.

**Trap 1 — reaching for a task-file header field.** Facts 17 and 18 are the constraint that
shapes F2 and F3: `**Property targets**:` and `**Dead code removal**:` are emitted by
`render-task-file` behind flags, so a third such field is a Python change this plan does not
make. The declarations ride `## Change Details` and `### Produces`, which the orchestrator
already fills. **A phase that adds an argparse flag has left this plan.**

**Trap 2 — writing D3 as an OR.** *"Net first, or declare the window"* is an escape hatch by
construction and the zero-escape-hatch policy names that shape. The obligation is
**declare**; the declaration's CONTENT is either "net precedes" or "window accepted". One
rule, two contents.

**Trap 3 — renumbering `code-reviewer`'s checks.** Plans 05 and 10 already cite the
structural-integration check as **§7** when it is **8** (fact 28). Append only.

**Trap 4 — believing `/devforge:review` covers the F1 case.** Its preamble asserts the
per-task panel *"already had their shot at every line inside any single task"* and then
rules single-task findings out of scope (fact 5). **Both halves are true today and together
they are the gap** — the assertion is what F1 makes accurate, and the out-of-scope rule is
what must NOT be relaxed.

**Trap 5 — treating F1's arm as widening every command.** It rides into `/devforge:fix`
automatically and correctly (OQ-2, fact 6), rides into `/devforge:audit` consistently with
that command's own duplication section, and is scoped OUT of `/devforge:review` by the
injected preamble (fact 25). None of those is an edit this plan makes.

**Trap 6 — placing the §3.6 block by feel.** §3.6 has a special splitter that recognises
only bold-header-alone-on-a-line blocks and silently skips everything else (fact 32), and
the `*Backed by*` paragraph belongs to KISS's parsed body with a test pinning it there
(fact 33). **Append after Narrowing, header shape exact.** Both failure modes are quiet:
the wrong header shape produces no error at all, and the wrong position produces a test
failure that looks like the test is stale when it is not.

**Trap 7 — reading these five as a verification layer.** They are authoring and review
DUTIES. Nothing here computes anything, nothing here blocks anything, and F3's declaration
in particular is checked by no code. The claim is visibility, not enforcement, and D3 says
so in the text that ships.

**The working-tree caveat this section carried at drafting is now SPENT and is recorded
here as history rather than as a live warning.** When this file was written on 2026-08-18
the surrounding plan work was uncommitted; as of 2026-08-23 plans 81 through 87 are all
committed and the only untracked files at repo root are plan and evidence documents. **The
underlying discipline still binds**: re-check every claim about another plan from the code,
never from a Status line.

**Discovered while drafting, NOT owned by this plan and not fixed here:**

1. **`src/agents/code-reviewer.md:37` cites the constitution by `§`-number** (*"the
   constitution's No dead code rule (§3.5)"*), which `src/agents-AUTHORING.md:147`–`:149`
   forbids and whose authoring checklist (`:187`) re-states as *"No `§`-number constitution
   references"*. It sits inside check 9, the check plan 71 added
   (`71-POST-CHANGE-CONSEQUENCE-PLAN.md:65`). **Phases 1 and 2 edit this file and must not
   introduce a second one; repairing the existing one is a separate routing.**
2. **`17-IMPLEMENT-PER-TASK-PANEL-PLAN.md:47` cites `src/agents/code-reviewer.md:70`** for
   the `### Verdict:` line, which lives at `:72` today (fact 27). Phase 1 shifts that file
   further. Pre-existing anchor rot; route separately.
3. **Plans 05 and 10 call the structural-integration check `§7`** when the shipped file
   numbers it **8** (fact 28). Same class as (2); recorded so Phase 1 does not "fix" it by
   renumbering the live file.

---

## When resuming work

1. Read this file in full, then **Verified mechanics** again — thirty-three rows, each
   checkable in under a minute. **If rows 1, 5, 6, 17, 18, 20, 31 or 33 no longer hold, stop
   and re-derive**: they are the scope and constraint argument, and D2's decision, D3's
   shape, F2's landing site and OQ-2's answer all rest on them.
2. **Read Phase 0 first.** D2–D5 and OQ-1 are unratified; **OQ-2 is already resolved
   (2026-08-18, from the code) and ratifies nothing else.** **Phase 1 is the exception
   and may run before Phase 0 closes** — D1 and the phase itself are pre-ratified by the
   2026-08-18 maintainer directive, and no other decision in this file constrains it.
3. Read **`src/agents/code-reviewer.md` in full** before touching it — not just check 8.
   Check 9's shape, the `## Output` template, `## Rules` item 1's new-file search sentence,
   and the `## Boundaries & Handoffs` scope sentence all constrain what Phases 1 and 2 may
   write, and two of them mention structural integration.
4. **Re-verify every anchor before use. Grep the quoted string, never the `:NNN`** —
   `newly created`, `only edit existing modules`, `Structural Integration`,
   `Wait for the third`, `Do not refactor surrounding code`, `Greenfield task ordering`,
   `Duplication & divergence`, `Property targets`, `Dead code removal`,
   `What is the MINIMAL change`.
5. **Route every edit through the house loops.** Every file this plan touches is spec /
   command / agent / constitution markdown: **instruction-author → instruction-reviewer**,
   plus **claude-code-guide** for anything shipping into a consumer's `.claude/` — which
   includes `src/agents/code-reviewer.md` (Phases 1, 2), `src/commands/breakdown/main.md`
   (Phases 2, 3) and `src/commands/plan/main.md` (Phase 5). **No phase here dispatches
   python-engineer**; if a phase finds itself needing one, the phase has broken the
   instruction-only constraint and must stop.
6. **Decide OQ-1 explicitly at Phase 0.** The every-task and only-mixed-tasks arms produce
   different text in `/devforge:breakdown` and different noise on every task file forever;
   discovering the choice at Phase 2 is how the wrong one ships by default.
7. Re-read the identifier constraint at the top before writing a sentence into this file,
   into any `src/` file, or into a commit message. **It binds execution, not just
   drafting.**
