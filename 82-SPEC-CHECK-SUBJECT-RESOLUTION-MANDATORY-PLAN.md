# 82 — `/devforge:spec-check`: subject resolution + mandatory run

**Status:** ✅ **DONE (build) 2026-08-19** (Phases 0–6, commits `55fa1ab` / `b6d834b` / `e1ba862` / `5d56a47` / `45bc760` / `5b73269` / `24256c5`); **Phase 7 consumer e2e DEFERRED 2026-08-20 — maintainer intends to run it (NOT waived; build-verified, NOT consumer-validated; the five known-answer cases in Phase 7 are the anchor).** Phase 0 ratified all items (D5 sub-fork = a-ii, D7 = c, D6 with the narrow reading confirmed); Phase 6 delivered the in-place D14 amendment + the full cross-reference sweep.
**Branch:** `develop-2.0-init`
**Created:** 2026-08-17.
**Premises re-verified:** 2026-08-19 against the shipped plan 81 and the created plan 85 — the two with a substantive touchpoint here. **Plans 79 and 80 shipped alongside plan 81 on 2026-08-18 and were checked: no premise in this file rests on either, and neither reaches a site this plan reads or edits** (verified 2026-08-19 — zero `memory` references in `src/devforge/lib/_spec_check/`, `src/agents/spec-formalizer.md` and `src/commands/spec-check/main.md`, and plan 79's memory prose in `src/commands/plan/main.md` is a different site from the PHASE-0a block Phase 5 adds; file overlap is not site overlap). Stale premises are corrected in place with dated markers; **no D-item, no OQ and no recommendation moved, and the plan is still NOT STARTED** — a re-verification is not a ratification. *(That last clause described the state at re-verification time and was superseded hours later the same day: Phase 0 closed on 2026-08-19 and every D-item and OQ is now ratified. The point it makes is unchanged — the re-verification itself ratified nothing; the separate per-item confirmation recorded below did.)*

This plan document contains no private-client identifiers and is intended to be
**committed normally**, unlike the deliberately-untracked plans 73/74/75.

## ABSOLUTE CONSTRAINT ON EVIDENCE

Two evidence files sit at repo root and are **UNTRACKED private-client records**:
`81-EVIDENCE-V2-BENCHMARK-RUN.md` and `77-EVIDENCE-DISCOVERY-TO-LOCK-INVERSION.md`.
Neither may be committed, and **neither may be quoted, excerpted or cited by content
into this file or any other tracked file** — plan 78's delete-at-v2-go-live route, not
a scrub. This plan refers to the benchmark ONLY at the abstraction level the TRACKED
`PLAN-STATUS-ARCHIVE.md` plan-81 entry already uses: *an AC over a state no reachable
construction site produces*, *the hidden second UI surface reaching a shared builder*,
*CONSISTENT 12/12*. No ticket ID, slug, SHA, branch, company, product, component,
function, parameter, path or enum value from that codebase appears here, and none may
be added — not in an example, not in a table, not in a grep pattern. **If a sentence
only works with a real identifier, rewrite the sentence.** An `81-*` glob returns
exactly two files — the evidence file and `81-INFERENCE-RULES-PLAN.md`. An unrelated
plan briefly carried that number and has been renumbered to
`83-DOWNSTREAM-REENTRY-SEED-PLAN.md`, so that collision no longer exists and the old
name must not be re-added from stale text; it is recorded in repo-root `CLAUDE.md` and
is not this plan's subject.

---

## Origin — the maintainer's directive, recorded verbatim

> spec-check: add subject resolution to the formalizer. Every AC subject must resolve
> to a construction site in the code. An AC whose subject doesn't resolve is a
> formalization failure — reported as UNRESOLVED-SUBJECT, not formalized into a
> constraint and not counted toward coverage. Then the mandatory question gets answered
> the same way as grill's: ship the fix, make it mandatory, auto-accept the clean
> verdict.

Two changes in one directive, and they are separable: **subject resolution** (D1–D4,
D8) is a formalization-quality change, **mandatory + auto-accept** (D5–D7) is a
pipeline-position change that reverses plan 62's ratified D14. The second half is the
one the maintainer must ratify with its full cost visible; the first half stands on its
own if the second is declined (see D6's separability note).

The directive's final clause — *"the same way as grill's"* — named a precedent this repo
does not record. **OQ-1 owned that discrepancy and is RESOLVED (2026-08-17): the
precedent is a maintainer decision made the same day, which has landed nowhere in the
repository.** The sentence that authorizes the whole second half therefore points at no
prior art — **D6 is a first-of-its-kind decision and Phase 0 must argue it as one**,
never as the application of an existing precedent.

---

## The motivating incident

The TRACKED `PLAN-STATUS-ARCHIVE.md` plan-81 entry records a seven-step causal chain
from one intake mislabel. Step 3 is this command:

- `/devforge:specify` wrote a preservation AC over **a state no reachable construction
  site produces**;
- `/devforge:spec-check` returned **CONSISTENT 12/12 — correctly**. An unfalsifiable AC
  cannot conflict with anything; Z3 was `sat` on both quorum passes;
- the phantom AC then became the operative design constraint for the rest of the run.

**The prover did its job and the report was still wrong on its face.** Nothing in the
current design distinguishes *"these ACs are mutually consistent"* from *"one of these
ACs asserts something about a state that does not exist, so it cannot conflict with
anything."* Both render as `sat`, both recommend CONSISTENT, and the coverage ledger
records the phantom AC as `formalized` — the most confident status the ledger has.

**Subject resolution changes the failure from a sound proof over a phantom into a
refusal to formalize the phantom.** The AC leaves the constraint set, the report grows
an `UNRESOLVED SUBJECTS` section naming it and what was searched, and the verdict stops
being clean — which under D5 is exactly the condition that fires the human gate.

**It clears plan 77's visibility bar, which plan 81 established as the governing
criterion and which is meant to be quoted:**

> **does the rule produce an artifact that is visibly wrong when the analysis wasn't
> done?**

An `UNRESOLVED SUBJECTS` section naming an AC, the search that was performed, and the
absence of a construction site reads wrong on its face — no design principle needed to
see it. **Its honest bound, stated here and not buried:** a formalizer that resolves a
subject to a *plausible-but-irrelevant* construction site passes every mechanical check
in D3 and produces a resolved AC. **D3 validates that a citation EXISTS and points at
real text; nothing validates that it is the RIGHT site.** This narrows the failure
class; it does not close it.

---

## Verified mechanics (2026-08-17)

Every row was confirmed by opening the named file. **The quoted token is the anchor;
the digit is a dated hint** — this repo has documented anchor rot, so grep the string,
never the `:NNN`.

| # | Fact | Evidence |
|---|------|----------|
| 1 | `COVERAGE_STATUSES = ("formalized", "skipped_prose", "skipped_unsupported")` — the tuple a fourth status joins | `src/devforge/lib/_spec_check/ir_schema.py:49` |
| 2 | `Variable` is the IR's co-reference anchor (plan 62 D8) and the natural home for a per-subject record | `ir_schema.py:85` |
| 3 | **`_SKIPPED_STATUSES` exists in TWO copies** — `("skipped_prose", "skipped_unsupported")` — and every status branch is keyed on `== "formalized"` or `in _SKIPPED_STATUSES` | `src/devforge/lib/_spec_check/_consume.py:314`; `src/devforge/lib/_spec_check/_report.py:72` |
| 4 | `validate_ir(ir, ac_ids)` is collect-all cross-record validation returning a sorted, deduped error list; an empty list means valid | `_consume.py:363` |
| 5 | **The agreement rule a new status falls straight through:** `formalized` with zero constraints is an error, a `_SKIPPED_STATUSES` status with ≥1 constraint is an error — **and a status that is neither is checked by nothing.** A fourth status carrying a constraint would pass validation silently | `_consume.py:445`–`:450` |
| 6 | The coverage line renders `**Checked {n} of {m} acceptance criteria** ({k} unformalizable).` where `n` counts `status == "formalized"`, `k` counts `status in _SKIPPED_STATUSES`, and `m = len(acs)`. **A fourth status is counted in neither `n` nor `k` and silently vanishes from the ledger's headline** | `_report.py:306`–`:333` (counts `:316`–`:326`, the line `:330`–`:333`) |
| 7 | `SPEC_CHECK_DISPOSITIONS = ("CONSISTENT", "REVISE-SPEC", "DISMISS")` — the 3-way disposition D1 does NOT grow | `_report.py:53` |
| 8 | `QUORUM_VERDICTS = ("confirmed_unsat", "unstable", "consistent")`; `analyze_quorum(solve_results, k)` reproduces an unsat core across a **strict majority**; `synthesize_solve_result` maps `unstable → sat` (the D13 cry-wolf rule) | `src/devforge/lib/_spec_check/_quorum.py:55`, `:63`, `:173` |
| 9 | The brief's `## OUTPUT CONTRACT` names the three coverage statuses and requires every AC id to appear exactly once in `coverage` | `src/devforge/lib/_spec_check/_brief.py:77`, `:138`, `:141`–`:145` |
| 10 | **The formalizer agent is ALREADY tool-capable of searching the consumer codebase** — `tools: Read, Grep, Glob`, read-only, no `Edit`/`Write`. **No tools change is needed for subject resolution** | `src/agents/spec-formalizer.md:4` |
| 11 | **…but the agent is currently INSTRUCTED NOT TO LOOK** — *"Produce the IR from that input alone — you translate the ACs in front of you"*. **That sentence becomes false under D1**, so the agent file is a mandatory Phase-2 target, not an optional one | `src/agents/spec-formalizer.md:26` |
| 12 | The agent's `## Approach` is a numbered procedural list, steps 1–6 | `spec-formalizer.md:28`–`:33` |
| 13 | `disable-model-invocation: true`, and the `description` ends *"Opt-in — never an auto-gate."* | `src/commands/spec-check/main.md:5`, `:3` |
| 14 | The opt-in stance is restated in the body and as Rule 1 | `spec-check/main.md:22`, `:273` |
| 15 | PHASE 5 displays the report VERBATIM then fires `AskUserQuestion` with three options; PHASE 6 writes the seed only on a matching `Revise spec` pick; PHASE 7 WIP-commits unconditionally | `spec-check/main.md:219`–`:235`, `:237`–`:247`, `:249`–`:257` |
| 16 | **`plan_helper` has NO preflight verb.** Twelve verbs: `pick-spec`, `render-pick-summary`, `list-specs`, `check-status-and-flip`, `render-findings-from-spec`, `render-breakdown-handoff`, `read-specify-handoff`, `render-consultation-block`, `render-plan-seeds`, `finalize-handoff`, `stakes-hint`, `read-memory` | `src/devforge/lib/plan_helper.py:2373`–`:2509` |
| 17 | **`/devforge:plan`'s "hard gate" is PROSE, not a helper call** — PHASE 0 reads `constitution.md` and stops on the unpopulated sentinel. A fail-closed mechanical preflight would be the FIRST in this command | `src/commands/plan/main.md:9` (the claim), `:134` (the actual guard) |
| 18 | **The gate shape D5 needs already exists one command upstream:** `specify_helper find-handoffs --require` exits 2 with a BLOCKED message on zero hits, and the text says *"This gate is mandatory, with no override."* Plan 48 independently names it the closest forward-precondition analogue | `src/commands/specify/main.md:99`, `:109`, `:115`; `48-REVIEW-MANDATORY-GATE-PLAN.md:14` |
| 19 | Plan 63's ratified carve-out is **13 drop / 7 keep**, and `grill`+`spec-check` are kept explicitly because *"their own descriptions say 'Opt-in — never an auto-gate'; auto-start would contradict plans 23/62"*. The same resolution measured `spec-check ~200w` as an oversized description | `63-SKILL-COLLISION-SUPPRESSION-PLAN.md:228`–`:237`, `:214` |
| 20 | `install.sh` contains **zero** occurrences of `z3` or `pip install` — plan 62 D10's stdlib-clean stance is live, not aspirational | `install.sh` (grep, zero hits) |
| 21 | `_PROMOTED` carries 20 command names; the emitter does not read or write `disable-model-invocation` — that field lives only in each command's own frontmatter (7 files carry it) | `scripts/emitters/claude.py:57`; `grep -rl disable-model-invocation src/commands/` → 7 files |

**Claude Code authoring surface, verified against current docs** (fetched 2026-08-17
from `https://code.claude.com/docs/en/slash-commands`, which now serves the merged
*"Extend Claude with skills"* page — *"Custom commands have been merged into skills"* —
Frontmatter reference section):

- `disable-model-invocation` — *"Set to `true` to prevent Claude from automatically
  loading this skill. Use for workflows you want to trigger manually with `/name`. Also
  prevents the skill from being preloaded into subagents. … Default: `false`."*
- `description` — *"What the skill does and when to use it. Claude uses this to decide
  when to apply the skill."* The combined `description` + `when_to_use` text is
  **truncated at 1,536 characters in the skill listing.**
- All frontmatter fields are optional; only `description` is recommended.

**Consequence Phase 5 must carry:** removing the flag puts spec-check's `description`
into the always-on skill listing. At ~200 words (fact 19) it is one of the two largest
in the set, and plan 63's OQ-1 resolution trimmed every model-invocable command's
description to ≈40 words for exactly this reason. **The flip drags a description trim;
it is not a one-line edit.**

---

## Decisions — ratify at Phase 0, none is settled *(ALL RATIFIED 2026-08-19)*

Each carries a recommendation and the argument against it. **Each now also opens with a
dated `**Ratified 2026-08-19:**` paragraph recording the maintainer's pick and its
one-sentence reason.** The recommendation, options and counter-argument prose below each
of those paragraphs is the drafting record and was deliberately left unedited — the
ratification is layered on top of it, never substituted for it.

### D1 — What subject resolution IS *(RATIFIED 2026-08-19)*

**Ratified 2026-08-19:** CONFIRMED as recommended — the per-VARIABLE
`subject_resolution` record (a citation, or `unresolved` with the search record), plus the
fourth coverage status `unresolved_subject` carrying all three consequences: **(a)** a
dedicated report section framed as a formalization failure, **(b)** `validate_ir`
rejecting an `unresolved_subject` entry that carries a constraint, **(c)** a third
coverage-line term with `M` unchanged. *Reason:* the variable is the co-reference anchor —
one resolution per real-world quantity — and the recorded counter-argument's two
consequences are both correct.

**The rule.** The `spec-formalizer`'s job gains a step that runs **before**
formalization: for each IR variable — equivalently, each AC's subject state — the
formalizer must **RESOLVE the subject**, establishing what in the code produces or
constructs that state.

**Recommendation — the record lives per VARIABLE, not per AC.** The IR's `variables[]`
block is the co-reference anchor (plan 62 D8, fact 2): the same real-world quantity
appearing in three ACs is ONE variable by construction, so a per-variable record is
resolved once and shared, while a per-AC record would ask the same question three times
and could answer it three different ways. Each `Variable` gains a `subject_resolution`
record that is either:

- a **citation** — repo-relative path + symbol (or line) + a one-line statement of what
  was found; or
- **`unresolved`** — plus a record of what was searched (the terms, the paths, the
  bound), so a human can falsify the miss.

**A fourth coverage status `unresolved_subject` joins `COVERAGE_STATUSES`** (fact 1). An
AC whose subject fails to resolve is:

- **(a) reported** under a dedicated `## UNRESOLVED SUBJECTS` report heading, framed as
  a **FORMALIZATION FAILURE** — not as a spec defect the solver proved;
- **(b) NOT formalized** into constraints. `validate_ir` must reject an
  `unresolved_subject` AC that carries a constraint. **Fact 5 is why this is a build
  requirement and not a description:** the agreement rule at `_consume.py:445`–`:450`
  branches on `"formalized"` and `_SKIPPED_STATUSES` only, so a fourth status carrying a
  constraint passes validation today with no error at all;
- **(c) accounted separately in the coverage ledger.** Per fact 6 the headline is
  `Checked N of M acceptance criteria (K unformalizable)`, where `M = len(acs)`, `N`
  counts `formalized` and `K` counts the two skip statuses. **`M` does NOT change** — it
  is the total AC count and must stay so. An unresolved-subject AC is counted in neither
  `N` nor `K`; the line grows a third term: `Checked N of M acceptance criteria (K
  unformalizable; J unresolved subjects)`. Without this the AC vanishes from the ledger
  silently, which is the current behavior of any unrecognized status.

**An unresolved subject drives the recommendation toward REVISE-SPEC** — the AC is
unfalsifiable as written, which is the incident's exact shape. **Dispositions stay
3-way** (fact 7): `DISMISS` remains the escape when the human knows the construction
site the search missed, and that escape is load-bearing here precisely because the
negative claim is soft (D4).

*Counter-argument, recorded:* a per-variable record is one indirection away from the
thing being reported. The report names ACs (the human reads ACs, the unsat core is
labelled by `ac_id`), so a per-variable record must be joined back to ACs through the
constraint set to render `## UNRESOLVED SUBJECTS` — and an AC that was going to be
`skipped_prose` anyway has no variable at all, so it can never carry an unresolved
subject. The defence is that both consequences are correct: a prose AC genuinely has no
subject state to resolve, and the join is one lookup the report layer already performs
(`_report.py` maps constraints by `ac_id` to render the contradiction section).

### D2 — Scope: the greenfield fork *(RATIFIED 2026-08-19 — the load-bearing decision)*

**Ratified 2026-08-19:** CONFIRMED as recommended — two-arm resolution: **arm (a)** a
construction site in the EXISTING code, **arm (b)** the spec's own new-behavior
declaration, with **preservation ACs arm-(a)-only**, keyed on the `behavior_preservation`
role now shipped at `/devforge:specify` Step 4.4. *Reason:* the directive's literal rule
fails every greenfield spec, and arm (b)'s self-attestation escape is accepted as the
recorded honest bound rather than argued away.

**The directive's literal rule cannot survive contact with greenfield ACs, and this must
be argued rather than smoothed over.** `/devforge:spec-check` runs between
`/devforge:specify` and `/devforge:plan` — **before any implementation exists**. An AC
describing behavior this feature INTRODUCES has no construction site **by definition**.
Under the literal rule, every new-behavior AC is `unresolved_subject`; under D5's
mandatory + auto-accept regime, **the clean verdict then NEVER fires on a greenfield
spec** and the gate degrades into ritual noise — the cry-wolf failure plan 19's
refutation stage and plan 62's D14 both exist to prevent.

**Recommendation — a subject resolves via EITHER arm:**

- **arm (a) — a construction site in the EXISTING code.** Required for any AC asserting
  a presently-existing state: every preservation AC, and any AC whose statement
  presupposes existing behavior.
- **arm (b) — the spec's own new-behavior declaration.** The state is INTRODUCED by this
  feature; the resolution citation points at the spec section or AC that introduces it.

**Preservation ACs are arm-(a)-only.** A preservation AC whose subject resolves only via
arm (b) is self-contradictory — it claims to preserve a state that this feature is
introducing — and that is precisely the phantom shape. Keying this on the
`behavior_preservation` role is the natural join (see D8 and OQ-3), and **as of
2026-08-19 that role-keyed admission rule is SHIPPED — plan 81's F3 landed it at
`/devforge:specify` Step 4.4 on 2026-08-18 (`59b5152`), so the join target is live
emitted text rather than a proposal.** Phase 2 writes the formalizer's rule against what
that step actually says; read it, do not infer it from this paragraph.

*Counter-argument, recorded, and it is real:* **arm (b) is a self-attestation escape
valve.** An author, or the formalizer itself, can misroute an existing-state claim
through it — "this is new behavior" is a claim the command cannot check. The mitigation
is the preservation-role restriction, which covers both benchmark sibling shapes; it
**narrows the dodge surface without closing it**, which is the same honest bound plan
81's OQ-2 records for prose triggers generally. Do not report the role restriction as a
solution.

*Second counter, recorded:* arm (b) makes the resolution record's TYPE heterogeneous —
one arm cites code, the other cites the spec — so a reader scanning the record must read
the arm before reading the citation. The alternative (resolve-or-skip with no arm (b))
was rejected on the greenfield argument above, and the heterogeneity is the price.

### D3 — Citations are mechanically validated *(RATIFIED 2026-08-19)*

**Ratified 2026-08-19:** CONFIRMED as recommended — arm-(a) citations are mechanically
validated (the file exists AND the cited symbol or text is present in it), a citation that
fails validation is treated as **unresolved**, and the negative claim stays soft.
**Placement stays a build decision for the python-engineer loop** — `validate_ir` vs a
sibling function vs a new `_resolve.py` — exactly as the build-shaping note below records
it. *Reason:* it raises the floor from "any string" to "points at real text"; relevance
checking is out of this framework's reach, and that bound is recorded rather than closed.

**Recommendation.** The soft LLM search's **POSITIVE** claim is made hard-checkable:
validation verifies that every arm-(a) citation's file exists and that the cited symbol
or text is actually present in it — a deterministic file check, no LLM. **A citation
that fails mechanical validation is treated as unresolved, not trusted.** The
**NEGATIVE** claim — a reported miss — stays soft, because "not found" is not
mechanically checkable without redoing the search. That asymmetry is what D4 is built
on.

**Build-shaping note, so Phase 1 does not discover it late:** `validate_ir` (fact 4) is
pure cross-record validation over in-memory dataclasses; a file check needs a workspace
root and touches the filesystem. `_consume.py` already reads the filesystem in
`extract_acs` (`:95`, path-or-text), so the module is not I/O-free — but whether the
check belongs in `validate_ir`, in a sibling function, or in a new `_resolve.py` is a
**build decision for the python-engineer loop**, recorded here as a known fork rather
than pre-decided.

*Counter-argument, recorded:* an existence check is cheap to satisfy and cheap to fake.
A formalizer that cites a real file and a real symbol that has nothing to do with the AC
passes every check and produces a resolved subject. **This is stated in the incident
section as the mechanism's honest bound and must not be argued away** — D3 raises the
floor from "any string" to "a string that points at real text", which is strictly better
than the free-text `--surface` value plan 81's F4 identifies as the upstream root, and
strictly weaker than relevance checking, which nothing in this framework can do.

### D4 — Quorum polarity for resolution is INVERTED vs the unsat-core quorum *(RATIFIED 2026-08-19)*

**Ratified 2026-08-19:** CONFIRMED as recommended — **any-pass resolution polarity**:
resolved in ANY pass is resolved, `UNRESOLVED-SUBJECT` is reported only when ALL k passes
miss, and each pass's search is shown. The inversion against the strict-majority
unsat-core rule is **deliberate** and stays visibly separate in code. *Reason:* existence
claims and defect claims have opposite one-off semantics, and unifying them manufactures
false positives.

**Recommendation.** Resolution is an **existence claim**. One pass finding a
mechanically-valid construction site **proves existence**, regardless of the other pass
missing it — so **resolved-in-ANY-pass = resolved**. `UNRESOLVED-SUBJECT` is reported
**only when ALL k passes fail to resolve**, and the report shows what each pass searched,
per plan 62 D4's falsifiable-human-check discipline.

**This is the OPPOSITE polarity from D13's strict-majority core reproduction (fact 8),
and the plan says so explicitly so a future session does not "unify" them.** The unsat
core is a claim that something IS wrong, where a one-off must not become a
recommendation (cry-wolf); resolution is a claim that something EXISTS, where a one-off
find is proof and a one-off miss is noise. **Unifying the two polarities would convert
every single-pass search miss into a reported failure** — the exact false-positive
machine D14 feared.

*Counter-argument, recorded:* an any-pass rule means the weaker of two formalizations
sets the outcome, so a single hallucinated-but-file-valid citation (D3's bound) is enough
to resolve a genuinely-phantom subject. Accepted: the two rules compose to
*"unresolved unless some pass produced a citation that points at real text"*, which is
the honest statement of what the mechanism proves.

### D5 — Mandatory wiring mechanics *(RATIFIED 2026-08-19)*

**Ratified 2026-08-19:** CONFIRMED **option (a)** — a `/devforge:plan` Phase-0 hard
preflight: a new `plan_helper` verb plus a new PHASE 0a.x block, modeled on
`specify_helper find-handoffs --require` (exit 2, BLOCKED, no override flag).
**Sub-fork: (a-ii) is RATIFIED** — `disable-model-invocation: true` STAYS on
`/devforge:spec-check`, and the blocked message names `/devforge:spec-check` for the user
to type. *Reason:* (a-ii) preserves plan 63's ratified 13/7 carve-out and the description
budget at zero cost, the two-turn round trip through the user is accepted, and "mandatory"
means the check RAN — which (a-ii) satisfies.

**(AMENDED 2026-09-03 — plan 93.)** (a-ii)'s FLAG clause is reversed:
`disable-model-invocation: true` no longer sits on `/devforge:spec-check`, and the blocked
message names the command for the orchestrator to OFFER and run on the user's agreement —
one agreement per command, `/devforge:plan` re-run proposed as its own step (plan 93 D2).
(a-ii)'s GATE half is untouched: the `plan_helper` preflight verb, exit 2, BLOCKED, no
override flag, presence + freshness only, never the verdict. The "zero cost" clause below
is superseded by the description-budget cost plan 93 D3 accepted; plan 63's carve-out WAS
reopened, by plan 93; and Phase 5's `disable-model-invocation` grep now returns the four
setup files, not the seven.

**Auto-accept semantics: ratified as recommended.** CLEAN = quorum-stable `consistent`
**AND** zero `unresolved_subject` **AND** zero mechanical-validation failures → **no human
gate fires**, with the report still rendered, still written and still WIP-committed.
Anything else fires the existing `AskUserQuestion` gate with the dispositions unchanged.

**The no-solvable-IR escape question: ratified as the recommended framing.** A run that
produces no solvable IR still writes a report recording that fact, and **that report
satisfies the gate** — the check RAN. No `--skip-spec-check` flag is added.

*(a-ii)'s zero-cost claim re-verified against current docs 2026-08-19 —
`https://code.claude.com/docs/en/slash-commands` (the merged "Extend Claude with skills"
page), whose invocation-control table states that with `disable-model-invocation: true`
the skill's **description is not in context** and only the user can invoke it. Keeping the
flag therefore consumes none of the skill-listing budget, which the same page documents as
scaling at 1% of the model's context window with each entry's combined `description` +
`when_to_use` capped at 1,536 characters.)*

**Options.**

- **(a) `/devforge:plan` Phase-0 hard preflight (RECOMMENDED).** A mechanical gate fails
  closed when `specs/<dir>/spec-check.md` is absent OR stale (staleness predicate =
  OQ-2), and the command names `/devforge:spec-check` as the required next step.
- **(b) `/devforge:specify` tail-runs the spec-check chain before finalize.**

**Recommendation: (a)**, on two grounds. First, **the gate belongs to the consumer
stage** — the stage protected from a bad spec — which is how every other handoff gate in
this pipeline sits, and fact 18 is the shipped precedent one command upstream:
`specify_helper find-handoffs --require` blocks `/devforge:specify` until an intake
handoff exists, exits 2 with a BLOCKED message, and states *"mandatory, with no
override."* Second, **(b) misses a hand-edited spec**: a spec edited after `/devforge:specify`
finalized never re-enters that command, so a tail-run there proves nothing about the file
`/devforge:plan` actually reads.

**Two build costs (a) carries that must be visible at ratification:**

1. **`plan_helper` has no preflight verb (fact 16) and `/devforge:plan` has no
   mechanical gate at all (fact 17)** — its setup-chain "hard gate" is prose. So (a)
   means **a NEW helper verb plus a new PHASE 0a.x block**, and it would be the first
   fail-closed mechanical preflight in that command. This is a real addition, not a
   wiring change.
2. **The model-invocability sub-question, which is its own fork:**
   - **(a-i) — flip `disable-model-invocation: true` → model-invocable (the brief's
     recommendation).** The model can then run `/devforge:spec-check` itself once the
     user agrees. Cost: reopens plan 63's ratified 13/7 carve-out for one of the seven
     (13/7 → 14/6 — *the counts as of 2026-08-19; Phase 5 reads them LIVE rather than
     applying this delta, see its Verify*), and drags a description trim, because the flip puts a ~200-word
     description into the always-on skill listing (fact 19 + the verified frontmatter
     semantics above).
   - **(a-ii) — keep the flag; `/devforge:plan` names the command and the user types
     it.** Costs nothing in plan 63's terms, adds no context, preserves the carve-out —
     and is strictly slower, since every blocked `/devforge:plan` becomes a two-turn
     round trip through the user. **This option is recorded as genuinely competitive and
     the ratifier should choose deliberately**; "mandatory" is satisfied by either, since
     what becomes mandatory is that the check RAN (see D6), not who typed it.

**Auto-accept semantics (both sub-options).** A **CLEAN verdict** =
quorum-stable `consistent` **AND** zero `unresolved_subject` **AND** zero
mechanical-validation failures. On clean: **no human gate fires** — the report is still
rendered, still written, and still WIP-committed (plan 37 discipline; fact 15's PHASE 7
is already unconditional), and the run proceeds. Anything else — `confirmed_unsat`,
`unstable`, any unresolved subject, any citation that failed validation — fires the
existing `AskUserQuestion` human gate with the D3 dispositions unchanged and `DISMISS`
surviving as the false-positive escape.

**The gate checks presence + freshness ONLY — never the verdict.** A `REVISE-SPEC`
report does not itself block `/devforge:plan`; the human owns that call (plan 62 D3), and
a `REVISE-SPEC` the user acts on produces a rewritten `spec.md`, which invalidates the
report under OQ-2's freshness predicate and re-blocks the gate until the check re-runs.
**A gate that read the verdict would be the blocking-on-a-stochastic-formalizer design
D14 correctly refused; this one is not that.**

*Counter-argument to auto-accept, recorded:* plan 62 D4 says the command MUST surface the
full formalization for human confirmation before a contradiction is treated as real, and
auto-accept skips that surfacing. The reconciliation is that D4's trigger is a
contradiction — **on a clean verdict there is nothing to confirm**, and the human-check
loop exists to stop a mistranslation from becoming a false alarm, which cannot happen
when no alarm is raised. A ratifier who disagrees should say so at Phase 0, because the
alternative (always show, never ask) is a coherent third position.

*Counter-argument to (a), recorded:* a fail-closed preflight in `/devforge:plan` blocks a
pipeline stage on an artifact produced by a stochastic step. If the formalizer is
persistently unable to produce a valid IR for some spec — every pass hitting the PHASE-2.3
retry cap, which today exits 2 at `quorum-core` with an empty passes array — the user
cannot plan at all. **Phase 0 must decide whether that state has an escape**, and the
zero-escape-hatch policy makes "add a `--skip-spec-check` flag" the wrong answer.
Recommended framing: a run that produces no solvable IR still writes a report recording
that fact, and that report satisfies the gate — the check RAN. Record the decision either
way.

### D6 — D14 is REVERSED by explicit maintainer directive *(RATIFIED 2026-08-19)*

**Ratified 2026-08-19 — with the narrow reading confirmed explicitly.** Plan 62's D14 is
reversed, by a formal in-place amendment written at Phase 6. **What is mandatory is that
the check RAN and that its report is FRESH — the verdict NEVER binds:** the human owns
every non-clean disposition, and a clean verdict auto-accepts. The amendment records **why
the calculus changed** (the new regime interrupts only on findings, against D14's
interrupt-on-every-run reading) and **the four narrowing mechanisms** (D2's arms, D3's
mechanical validation, D4's any-pass polarity, the surviving `DISMISS`).
**Separability, confirmed:** a decline would have kept Phases 1–4 standing and dropped
Phases 5–6 — **D6 was NOT declined**, so all six build phases stand (the drafting record's
own *"Separability, recorded"* paragraph below states the same rule and is unedited).
**First-of-its-kind per OQ-1** — ratified on the maintainer's own
directive, with no precedent cited and none available. *Reason:* the new regime interrupts
only on findings, which is on the other side of D14's actual hazard.

Plan 62's D14 (`62-SMT-REQUIREMENTS-CONSISTENCY-PLAN.md:123`–`:124`) says
`/devforge:spec-check` *"MUST NEVER become a blocking/mandatory gate"* and *"A future
session must not 'strengthen' it into a gate."* **This plan crosses that line on an
explicit maintainer directive, and the crossing is recorded as a formal
post-ratification amendment to plan 62** — the same in-place-amendment mechanism that
plan already used for its own D9 (`:89`, rewritten in place when the decision record
contradicted the shipped code).

**The amendment must record WHY the calculus changed, not merely that it changed:**

- **Original D14 equated "mandatory" with "interrupt on every run atop a stochastic
  formalizer."** Under that reading a mistranslation hard-stops a correct specification
  on every run — cry-wolf at maximum severity, and the objection was right.
- **The new regime interrupts ONLY on findings.** A clean verdict is auto-accepted (D5),
  so the correct-spec case pays a report and a commit, never a question.
- **What is mandatory is that the check RAN and its report is FRESH — never that its
  verdict binds.** The human still owns every disposition. This is the load-bearing
  distinction, and D14's actual hazard lives entirely on the other side of it.
- **The false-positive surface D14 feared is narrowed by four mechanisms this plan
  adds:** D2's arm structure (greenfield ACs resolve rather than false-fail), D3's
  mechanical citation validation, D4's any-pass resolution polarity, and the surviving
  `DISMISS` escape.

**What does NOT change, and must be stated in the amendment so no future session reads
the reversal as broader than it is:** the human owns every non-clean verdict; the command
never edits `spec.md`; plan 62's D11 under-promise boundaries stand verbatim (consistency
prover, not mind-reader; the D9 permission boundary; no bare "deterministic proof of your
spec"); and D13's quorum stays a fixed k=2 with strict-majority core reproduction.

**Separability, recorded:** D1–D4 and D8 ship coherently under the CURRENT opt-in stance.
If D6 is declined at Phase 0, Phases 1–4 still stand and Phases 5–6 are dropped. **A
Phase-0 rejection of D6 is not a rejection of the plan.**

**Cross-reference sweep this reversal drags (Phase 6 executes it; this list is NOT
certified exhaustive — Phase 6 opens with `grep -rn "D14\|never an auto-gate\|Opt-in"
src/ *.md`):**

- `62-SMT-REQUIREMENTS-CONSISTENCY-PLAN.md` — D14 (`:123`–`:124`) and the opening
  status/framing lines that call the command opt-in;
- `src/commands/spec-check/main.md` — the frontmatter `description`'s closing *"Opt-in —
  never an auto-gate."* (`:3`), the body's opt-in framing (`:22`), Rule 1 (`:273`), and —
  under D5(a-i) only — `disable-model-invocation: true` (`:5`);
- `src/CLAUDE.md` — the Workflow chain's bracketed `[/devforge:spec-check]` and the
  bracket legend, the *"Seven are human-typed only"* sentence, the `/devforge:spec-check`
  bullet in the one-line command list, the *"Seven commands … are human-typed only"*
  sentence introducing `### Command Details`, and the `#### /devforge:spec-check`
  entry itself (cited by section, not by line — that file's line numbers are not verified
  here);
- `FINDINGS.md:29` — finding 4's clause *"a MANDATORY refusal of this shape has no owner
  today"*, whose stated reason is that spec-check is opt-in per D14. **AMEND, do not
  delete**, and do not renumber any finding or touch finding 4's `NOTE ON THIS ENTRY'S
  SHAPE` paragraph — finding 5 back-references it;
- `81-INFERENCE-RULES-PLAN.md` — the line *"`/devforge:spec-check` stays opt-in and
  ADVISORY per its ratified D14, and this plan proposes no change to it"* (`:129`), the
  non-goal bullet *"Any change to `/devforge:spec-check`"* (`:201`), and D4 (`:183`) where
  F3's ownership claim interacts with D8 — **all three are SHIPPED, ratified text as of
  2026-08-18, not draft; digits re-verified 2026-08-19, and the quoted strings are still
  the anchors**;
- `PLAN-STATUS-ARCHIVE.md` — the plan-62 entry and the plan-81 entry;
- repo-root `CLAUDE.md` — the plan-62 index line's *"NEVER strengthen into a gate
  (D14)"*, and the plan-81 index line's spec-check sentence;
- **under D5(a-i) only:** `63-SKILL-COLLISION-SUPPRESSION-PLAN.md`'s OQ-2 resolution
  (`:228`–`:237`), which enumerates the keep-7 by name and gives spec-check's reason; the
  13/7 counts in repo-root `CLAUDE.md`'s "Where to find what" emitter row; and plan 63's
  OQ-1 description-budget resolution (`:213`–`:220`).

*Counter-argument, recorded and not resolved by this plan:* D14 was ratified after a
design critique that specifically weighed and rejected an earlier "make it blocking"
push. Reversing it on a directive rather than on new evidence means the reversal rests on
the same kind of reasoning the original rested on — and the incident behind this plan is
**one run**, which is the attribution bound plan 81's D6 records for itself. The defence
is that the reversal is narrower than the thing D14 refused (run-mandatory, not
verdict-binding), and that the four narrowing mechanisms did not exist when D14 was
written. **The ratifier should confirm the narrow reading explicitly**, because a future
session reading "D14 reversed" without it will over-generalize.

### D7 — The z3 / D10 collision *(RATIFIED 2026-08-19 — unaddressed by the directive)*

**Ratified 2026-08-19:** CONFIRMED **option (c)** — fail closed: `/devforge:plan` blocks
with the one-time `pip install z3-solver` message until it is installed. **Option (a)**
(`install.sh` installs `z3-solver`) is recorded as the **named fallback** if consumer
friction proves too high at Phase 7; **option (b) stays REJECTED.** *Reason:* (c) is
honest, carries no escape hatch, reuses the message the preflight already emits, and plan
62 D10's stdlib-clean stance survives.

Plan 62 D10 (`:97`–`:101`): `install.sh` stays stdlib-clean, and `/devforge:spec-check`
preflights `import z3` and exits with a clean one-time `pip install z3-solver` message.
**Fact 20 confirms that is live: `install.sh` has zero z3 references.** That was sound
for an opt-in command — the dependency burdened only invokers. **A mandatory gate forces
the dependency on every consumer, or blocks `/devforge:plan` on every unprovisioned
machine.**

**Options.**

- **(a)** `install.sh` installs `z3-solver` — reverses D10's stdlib-clean stance for the
  whole install.
- **(b)** z3-absent degrades the gate to a warning. **REJECT** — it is an escape hatch,
  which collides with this repo's zero-escape-hatch policy, and it **silently
  un-mandatories the gate on exactly the machines that never provisioned it**, which is
  the worst possible distribution of the failure.
- **(c) RECOMMENDED — fail closed.** `/devforge:plan` blocks with the one-time
  `pip install z3-solver` message until it is installed.

**Recommendation: (c)** — honest, one-time, no escape hatch, and it reuses the message
the preflight already emits. **Record (a) as the named fallback** if consumer friction
proves too high at Phase 7; changing the answer later is an `install.sh` edit, not a
redesign.

*Counter-argument, recorded:* (c) means a fresh consumer install cannot run
`/devforge:plan` at all until an unrelated pip command is run — a first-run cliff on the
pipeline's most central command, for a check that command does not itself use. (a) trades
that for ~30MB and the first third-party pip dependency in a deliberately stdlib-clean
install path, which the forcing-functions family (pre-commit hooks, setup-chain helpers)
depends on staying clean. **Neither option is free and Phase 0 must pick one on the
merits, not by deferring.**

### D8 — Plan 81 interplay: defence in depth, not supersession *(RATIFIED 2026-08-19)*

**Ratified 2026-08-19:** CONFIRMED as recommended — **defence in depth with plan 81's
SHIPPED F3, not supersession.** This plan is the mechanical, formalization-side
counterpart to F3's authoring-side admission rule, and **the pins-a-removed-value bound
stands as stated**: code-grounded resolution makes shared binding more likely, not
guaranteed. **Phase 6 writes the further additive `FINDINGS.md` finding-4 amendment**, with
the split stated unambiguously — **F3 = admission at authoring; this plan = refusal at
formalization.** *Reason:* F3's own record is of a present, correct prose rule being
dodged, so the mechanical catch at the next stage is exactly the point.

**(AMENDED 2026-08-19 — this decision's premise was stale.)** **Plan 81's Phases 0–6
SHIPPED 2026-08-18, so its F3 is no longer a proposal.** Phase 4 landed the authoring-side
preservation-AC admission rule at `/devforge:specify` **Step 4.4** (`59b5152`), keyed on
the shipped `add-ac --subsection behavior_preservation` role: an AC entering §5.2 must
cite the construction site producing its subject state, and an uncitable subject state
routes to Open Questions + Risks instead of entering as an AC. **Its Phase 7 consumer e2e
is DEFERRED — F3 is build-verified, NOT consumer-validated** — so nothing below may rest
on F3 having been observed to work.

**Recommendation — both, and in this order of effect:**

- **F3 is shipped and is not superseded.** It refuses the phantom AC at the point of
  writing; it is instruction-only and cheap. **This plan catches its survivors mechanically
  at the next stage, and that role is STRONGER against a shipped rule than it was against a
  proposed one, not weaker.** Plan 81's own recorded failure shape is a `/devforge:specify`
  directive that was present, correct and shipped, and was dodged by framing; **plan 81's**
  ratified OQ-2 says the role key **narrows the dodge surface without closing it** and must
  never be reported as a solution. **A survivor of F3 is therefore a live class by that
  plan's own ratified record, not a hypothetical** — and it is exactly the class a
  formalization-time refusal that reads the code is built for. **Bound, stated so the
  argument is not overread:** D2's
  preservation-arm-(a)-only rule keys on the SAME author-declared role, so this plan
  narrows that dodge again and does not close it either — D2's first recorded counter names
  arm (b) as the surviving self-attestation escape.
- **Subject resolution directly catches the unreachable-subject sibling** — an AC over a
  state no reachable construction site produces is exactly what fails to resolve.
- **The pins-a-removed-value sibling is caught by Z3 only when the formalizer binds the
  removal AC and the pin AC to shared variables.** Code-grounded resolution makes shared
  binding **more likely** — both subjects resolving to the same construction site is a
  strong pull toward one variable — **but does not guarantee it.** State this bound
  plainly; do not write subject resolution as closing that finding.

**(AMENDED 2026-08-19.) Plan 81's F3-ownership claim (its D4) is RATIFIED, and
`FINDINGS.md` finding 4 was ALREADY amended in place by plan 81's own Phase 6 on
2026-08-18** — an additive, dated amendment recording that ownership is settled and that
the class moved from unowned-and-prose to **owned-and-prose**. **So this plan's Phase 6
writes a FURTHER additive dated amendment on top of that one**, still contingent on Phase
0 ratification *(contingency DISCHARGED 2026-08-19 — Phase 0 closed and D8 was confirmed,
so Phase 6 writes that amendment unconditionally)*: F3 keeps ownership of the
authoring-side rule, and this plan is recorded
as the mechanical counterpart. **The clause this plan answers survives verbatim in finding
4's original text** — *"so a MANDATORY refusal of this shape has no owner today"* — **and
its stated reason is that `/devforge:spec-check` is opt-in per D14, which is precisely
what a ratified D6 changes.** Plan 81's amendment did not close that clause and does not
claim to; do not read it as having done so.

*Counter-argument, recorded:* two plans owning one finding is how ownership becomes
nobody's. And **plan 81 ratified first and its statement that it proposes no change to
`/devforge:spec-check` is now SHIPPED, ratified text (`:129`, `:201`)** — so its non-goal
and this plan's subject collide in the record LIVE, even though they do not collide in
substance. **The contingency this paragraph used to carry is gone (amended 2026-08-19):
Phase 6 writes the split against a shipped sentence, not a draft one, and it must be
unambiguous** — F3 = admission at authoring; this plan = refusal at formalization.

---

## Open questions (Phase 0)

### OQ-1 — The grill-precedent discrepancy *(RESOLVED 2026-08-17)*

The directive says the mandatory question *"gets answered the same way as grill's."*
**No repo record of a grill-mandatory decision exists.**

*Resolved:* 2026-08-17, by maintainer statement, recorded verbatim:

> side note - i decided to make grill mandatory.

**The answer is neither of the two options the discrepancy was drafted against.** It is a
third: **the grill precedent is a FRESH maintainer decision that has landed nowhere in
the repository.** There is no prior session to read, no ratified argument to inherit and
nothing shipped — as of this writing `src/commands/grill/main.md` still carries
`disable-model-invocation: true` (`:5`) and its Rule 1 still reads *"Opt-in, never an
auto-gate … there is NO forced gate on every `/devforge:plan` run"* (`:391`). The
evidence that framed the discrepancy is therefore not overturned; it becomes the record
of **what has not yet moved**, verified 2026-08-17:

- `/devforge:grill` carries `disable-model-invocation: true` (it is one of the seven);
- plan 23's archive entry records that **the USER owns the verdict at the
  `/devforge:breakdown` gate**;
- `48-REVIEW-MANDATORY-GATE-PLAN.md` — the one mandatory-gate push in the repo, aimed at
  `/devforge:review` — is **SHELVED** (`:3`), keep-the-warning, not built;
- a repo-wide case-insensitive grep for grill within 80 characters of *mandator* returns
  **one** hit: `src/CLAUDE.md`'s `/devforge:grill` bullet saying *"not a mandatory gate."*

**What this settles for D6.** The sentence authorizing this plan's second half points at a
same-day decision, not at prior art, so **D6 is a first-of-its-kind decision and must be
argued as one** — no precedent's reasoning can be read into it, and *"grill did it too"* is
not an argument available to the ratifier. The concurrency cuts both ways:
**`85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md` cannot cite THIS plan's D6 as its precedent
either, because neither has been ratified** *(re-verified 2026-08-19 — both were NOT
STARTED at that check; **this plan's Phase 0 ratified later the same day and plan 85's did
not**, so the symmetry no longer holds. What a ratified D6 is or is not worth to plan 85's
own first-of-its-kind argument is plan 85's Phase 0 to decide and is NOT settled here;
what is settled is that D6 itself was argued and ratified with no precedent cited.)*.

**A sibling grill-mandatory change IS intended, it stays OUT of this plan's scope, and
that plan now EXISTS** *(recorded 2026-08-19)*: **`85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md`,
created 2026-08-17, NOT STARTED, awaiting its own Phase-0 ratification.** No phase here
builds it (see `## Non-goals`). **Why it cannot ride along, on structural grounds rather
than scheduling:**

- **`/devforge:grill` is soft all the way down.** Its findings are LLM-produced and
  filtered through the `_shared/` refutation engine (`_grill/_cli.py` imports
  `route-refutation` / `render-verify-brief` / `consume-verdicts` from `_shared`), and
  **no deterministic Z3-analog layer exists anywhere in it.** So grill's analog of D5's
  CLEAN verdict is *"no finding survived refutation"* — **a weaker claim with a different
  false-positive profile** than *"the solver was `sat` and every subject resolved."* The
  auto-accept rule cannot be copied across without re-deriving what clean means there.
- **A different disposition set and a different pipeline seat.** Grill is **4-way**
  (`PROCEED` | `REVISE-PLAN` | `RE-ENTER-UPSTREAM` | `KILL`, `grill/main.md:322`) against
  this command's 3-way (fact 7), and it sits between `/devforge:plan` and
  `/devforge:breakdown` rather than between `/devforge:specify` and `/devforge:plan`. Gate
  host, blocked-arm message and seed interaction are all a different design, not a
  re-parameterization of D5.
- **The cost shape is different and must be measured, not assumed.** Mandatory grill puts
  the **full finder + refuter fan-out on every feature**, with **no cheap deterministic
  core** to absorb the common case. **That plan's Phase 0 owes a wall-clock cost line**
  (cf. plan 70, which exists because per-command wall-clock was never measured); OQ-3 is
  this plan's analogous obligation and does not transfer.

**What DOES transfer:** the SHAPE of D5's auto-accept — **interrupt the human only when a
finding exists**, and render + commit the artifact unconditionally either way. That half
is reusable precisely because it says nothing about how either command decides a finding
exists.

**This resolution ratifies nothing else in this plan.** D1–D8 and OQ-2–OQ-3 are still
open, and D6 in particular is now harder to ratify, not easier. *(Status clause superseded
2026-08-19 — D1–D8, OQ-2 and OQ-3 were all ratified that day. The sentence stands as the
record of what OQ-1's own resolution established, which is unchanged: it supplied no
precedent, and D6 was accordingly argued and ratified as first-of-its-kind.)*

### OQ-2 — The staleness predicate for the `/devforge:plan` gate *(RESOLVED 2026-08-19)*

*Resolved:* 2026-08-19 — **the CONTENT HASH of `spec.md`, recorded in `spec-check.md` at
render time and re-hashed by the gate.** Not mtime, and not the sibling-JSON-stamp third
option the counter-argument below prices. **Ratified identically with
`85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md`'s D4 predicate**, per the coordination constraint
recorded at the end of this section — the CARRIER still differs per plan (this plan's
rendered report vs plan 85's `grill-state.json`), the PREDICATE does not. *Reason:* mtime
is fragile across checkouts, clones and branch switches, this repo already keys drift on
content rather than timestamps, and a recorded hash makes the report self-describing — it
says which spec it proved over.

Candidates: `spec.md` mtime vs report mtime; a content hash of `spec.md` recorded in
`spec-check.md` at render time and re-hashed by the gate.

*Recommendation: the content hash.* **mtime is fragile across checkouts, clones and
branch switches**, and this repo already distrusts mtime-adjacent signals — the
`cbm_sync` drift check keys on git SHAs, and plan 74's memory probe keys on content
state, not timestamps. A recorded hash also makes the report self-describing: the report
says which spec it proved over.

*Counter-argument:* a hash in the report means the report's own bytes carry a field the
gate parses, which couples two commands through a rendered markdown artifact rather than
through a JSON handoff. **The alternative — a sibling JSON stamp — is a third option
Phase 0 may prefer**, at the cost of a new artifact in the feature dir and a
`storage-rules.md` row.

**Coordination, recorded 2026-08-19 — this OQ can no longer be ratified alone.**
`85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md`'s D4 adopts the **same PREDICATE** (a content
hash, not mtime) on a **different CARRIER** — `specs/[feature]/grill-state.json`, which
already exists, is helper-owned and is already committed, so that plan does not pay the
new-artifact cost the counter above prices — and it states that **both plans must ratify
the predicate identically**, because two gates in one pipeline disagreeing about what
"stale" means is itself the defect. **This OQ's ratification record must name plan 85's
D4, and plan 85's must name this OQ.** The carrier may still differ per plan; the
predicate may not.

### OQ-3 — Mandatory cost, and how the search is bounded *(RESOLVED 2026-08-19)*

*Resolved:* 2026-08-19 — **the per-subject search is BOUNDED explicitly in the emitted
instruction**, in the spirit of the shipped bounded-hops walk at `/devforge:research`
Step 2b. **The exact bound is chosen at Phase 2**, where the instruction is written and the
reference examples sit, and **Phase 7 records the observed false-UNRESOLVED rate on the
greenfield case** — the bound and the false-positive rate are the same dial. *Reason:* an
unbounded per-variable search on a mandatory command is the known wall-clock failure mode,
and plan 70 exists because per-command wall-clock was never measured.

Every feature now pays **k=2 formalizer passes PLUS per-subject code search on every
pass.** Today the formalizer reads only its brief (fact 11); under D1 it searches the
consumer codebase per variable, twice.

*Recommendation: bound the search per subject explicitly in the emitted instruction*,
in the same spirit as the shipped bounded-hops walk `/devforge:research` Step 2b already
performs. **The exact bound is a build decision** — it must be chosen where the
instruction is written, with the reference examples, not guessed here.

**Record why this matters:** an unbounded search instruction is how wall-clock blows up,
and plan 70 exists because the pipeline's per-command wall-clock was never measured. A
mandatory command with an unbounded per-variable search is the worst possible place to
find that out.

*Counter-argument:* a hop bound that is too tight produces `unresolved` on subjects that
a slightly wider search would have found — and under D4 an all-pass miss is a reported
failure, so a tight bound manufactures false UNRESOLVED-SUBJECT findings. **The bound and
the false-positive rate are the same dial**, and Phase 7 is the only place its setting is
observed.

---

## Phases

### Phase 0 — Ratification *(HARD stop; no `src/` edit)* — **CLOSED 2026-08-19**

**RATIFIED 2026-08-19 — Phase 0 is CLOSED and Phases 1–6 may proceed.** The maintainer
ratified **every item** — D1–D8 plus OQ-2 and OQ-3 — in an **explicit per-item interactive
confirmation**, and each pick is recorded under its own heading above in a dated
`**Ratified 2026-08-19:**` / `*Resolved:*` paragraph with its one-sentence reason. **The
three forks this phase forbade deferring were each picked explicitly:**

- **D5's model-invocability sub-fork → (a-ii)** — `disable-model-invocation: true` stays on
  `/devforge:spec-check`, and `/devforge:plan`'s blocked message names the command for the
  user to type. Plan 63's carve-out is therefore **not** reopened, and Phase 5's
  `disable-model-invocation` grep must return the **same** file list it returned before.
  **(Amended 2026-09-03 — plan 93 reversed the flag clause; the grep now returns the four
  setup files. The gate is unchanged.)**
- **D7 → (c)** — fail closed on an absent `z3-solver`, with (a) recorded as the named
  Phase-7 fallback and (b) still rejected.
- **D6 → ratified WITH the narrow reading confirmed** — mandatory means the check RAN and
  its report is FRESH; **the verdict never binds** — **and with the separability note
  recorded**: a decline would have kept Phases 1–4 and dropped Phases 5–6, and D6 was not
  declined.

The phase specification below, and its Verify block, are left as written; the satisfied
record follows them.

The maintainer resolves D1–D8 and OQ-2–OQ-3, recording under each the chosen option plus
one sentence of reason. **OQ-1 is already resolved** (2026-08-17) and its answer removes
the precedent D5–D7 were assumed to inherit — **read it before ratifying D6**, which is
now a first-of-its-kind decision. D5's model-invocability sub-fork (a-i / a-ii) and D7's
z3 option are each an explicit pick, not a deferral.

Re-check facts 3, 5, 6, 11, 16, 17 and 18 before ratifying — they are the cost argument,
and each is a `file:line` checkable in under a minute.

**Verify:**

- `grep -n "^### D[1-8] " 82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md` returns
  eight lines and **none of them contains `(OPEN`** — the marker is written `*(OPEN)*` on
  D1/D3/D4/D5/D6/D8 and qualified on D2 (`*(OPEN — the load-bearing decision)*`) and D7
  (`*(OPEN — unaddressed by the directive)*`), so match the substring, not the exact
  token. Each heading's decision carries a recorded confirm-or-override.
- OQ-2 and OQ-3 each open with a `*Resolved:*` sentence, in the form OQ-1 already
  carries; D5's sub-fork and D7's option are each named explicitly.
- **The D6 pick is recorded together with the narrow reading** — mandatory means the
  check RAN and is FRESH, never that its verdict binds. A bare "D14 reversed" records a
  broader claim than the ratifier made.
- **The D6 separability note is recorded**: whether a decline of D6 keeps Phases 1–4.
- The status line at the top of this file names the ratification date.
- `git status` shows no `src/` file modified for this plan.

**All six checks SATISFIED 2026-08-19.** The eight `^### D[1-8] ` headings now read
`*(RATIFIED 2026-08-19)*`, with D2's and D7's qualifiers preserved
(`*(RATIFIED 2026-08-19 — the load-bearing decision)*` and
`*(RATIFIED 2026-08-19 — unaddressed by the directive)*`), so no heading contains `(OPEN`;
the bullet above keeps naming the pre-ratification marker shapes because it is the record
of what that grep was written against. OQ-2 and OQ-3 each open with a `*Resolved:*`
sentence; D5's sub-fork **(a-ii)** and D7's option **(c)** are each named; D6's narrow
reading and its separability note are both recorded under D6 and again in this phase's
opening paragraph; the status line names 2026-08-19; and this ratification edited one file
— this one.

---

### Phase 1 — IR schema + mechanical citation validation

**Route: python-engineer → python-reviewer, test-first. Every function gets a test that
actually runs, in the same turn, with production input shapes** (round-trip through the
real producer, not hand-authored fixtures, wherever a producer exists).

Scope:

- `ir_schema.py` — the `subject_resolution` record on `Variable` (D1's per-variable
  shape, with the D2 arm discriminator), and `unresolved_subject` appended to
  `COVERAGE_STATUSES` (`:49`).
- `_consume.py` — parse the new record; extend `validate_ir` (`:363`) so the agreement
  rule at `:445`–`:450` has a **third branch**: `unresolved_subject` with ≥1 constraint is
  an error (D1(b)). Add the D3 mechanical citation check per the fork recorded in D3.
- **Both `_SKIPPED_STATUSES` copies (fact 3) are visited**, and the decision recorded in
  code comments: `unresolved_subject` is deliberately NOT a skip status, because a skip
  means "no logic here" while an unresolved subject means "the logic has no referent".

**Verify:**

- `python3 -m unittest` over `tests/lib/_spec_check/` passes, and the `_shared` +
  `_grill` + `_verify` suites are green (nothing outside `_spec_check` was touched).
- A test asserts an `unresolved_subject` coverage entry carrying a constraint is
  **rejected** — the exact hole fact 5 documents.
- A test asserts an arm-(a) citation naming a nonexistent file is treated as unresolved,
  and one naming a real file whose text lacks the cited symbol likewise.
- A test asserts an arm-(b) resolution does NOT trigger the file check.
- The IR serde round-trip `parse_ir(dataclasses.asdict(ir)) == ir` still holds exactly
  across every shape, including the new record — that invariant is load-bearing for the
  whole scratch chain.
- `grep -rn "_SKIPPED_STATUSES" src/devforge/lib/_spec_check/` returns both copies and
  both were read.

---

### Phase 2 — The resolution duty: brief, agent, and guidance

**Route: instruction-author → instruction-reviewer + claude-code-guide.**
`src/agents/spec-formalizer.md` ships to a consumer's `.claude/agents/`, so the
claude-code-guide check is required, not optional.

Scope, all three sites stating ONE standard:

- `_brief.py`'s `## OUTPUT CONTRACT` (`:77`, `:138`, `:141`–`:145`) — the fourth coverage
  status and the `subject_resolution` field shape. **This is Python that emits
  instruction text; it routes through python-engineer → python-reviewer for the code and
  instruction-author for the wording** — say so in the dispatch, because a brief edit
  looks like prose and is not.
- `src/agents/spec-formalizer.md` — **the mandatory target fact 11 identifies.** The
  sentence *"Produce the IR from that input alone"* (`:26`) becomes false and must be
  rewritten; the resolution duty, the two arms, the preservation-arm-(a)-only rule, and
  the searched-record requirement on `unresolved` land in the `## Approach` list. **Its
  steps are numbered 1–6 (`:28`–`:33`) and resolution runs BEFORE formalization**, so
  whether to insert or append is a real authoring question: **grep for external
  references to those step numbers before renumbering**, and if any exist, append and
  order by prose instead.
- `references/formalization-guidance.md` — worked examples for both arms, including one
  unresolved case showing what the searched-record looks like.

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean.
- **The agent's `tools:` line is byte-unchanged** — `Read, Grep, Glob` (fact 10). A diff
  that adds a tool has misread the plan.
- `grep -n "from that input alone" src/agents/spec-formalizer.md` returns **zero** lines.
- The brief, the agent body and the guidance state the SAME standard for the same value —
  read all three as landed, not from this plan's description of them.
- The preservation-arm-(a)-only rule appears in the emitted text, and so does the honest
  bound that a cited construction site is not proof of exhaustive reachability (static
  trace is bounded by dynamic dispatch — plan 81's F3 carries the same bound).
- **No plan vocabulary in emitted text** — "D1", "arm (a)", "Phase 2" and this plan's
  number are maintainer vocabulary. Emitted text names only the command's own phases and
  the agent's own steps.

---

### Phase 3 — Quorum merge, report section, clean-verdict predicate

**Route: python-engineer → python-reviewer, test-first**, plus instruction-author for
`references/report-format.md`.

Scope:

- `_quorum.py` — an **any-pass resolution merge** (D4 polarity), kept visibly separate
  from `analyze_quorum`'s strict-majority core logic (`:63`), with a comment stating the
  inversion and why. **Do not fold the two into one helper.**
- `_report.py` — the `## UNRESOLVED SUBJECTS` section (naming the AC, the subject, and
  what was searched); the coverage line extended to
  `Checked N of M acceptance criteria (K unformalizable; J unresolved subjects)` per D1(c)
  and fact 6, with `M = len(acs)` unchanged; and the clean-verdict predicate (D5) exposed
  so the command can branch on it rather than re-deriving it in prose.
- `references/report-format.md` — its `## Sections (in render order)` list gains the new
  section. **The reference goes stale the moment the renderer changes**, so it lands in
  this phase, not in Phase 6.

**Verify:**

- `tests/lib/_spec_check/` green; a full-string-equality test pins the rendered coverage
  line for all four combinations (with/without unformalizable, with/without unresolved).
- A test asserts **resolved-in-one-pass-only ⇒ resolved** and **unresolved-in-all-passes
  ⇒ reported**, and a comment in the test names the inversion vs the unsat-core quorum so
  a future reader cannot "fix" it.
- A test asserts the clean predicate is **false** when the quorum is `consistent` but one
  subject is unresolved — the incident's exact shape, and the single most important test
  in this plan.
- `render_report`'s existing signature contract still holds; a report with zero
  unresolved subjects renders **byte-identically** to today (pinned by a full-string test,
  the same way the `stability=None` back-compat was pinned).
- `grep -n "Checked .* of" src/devforge/lib/_spec_check/_report.py` and the
  `report-format.md` section list agree.

---

### Phase 4 — `main.md` rewiring: auto-accept-clean

**Route: instruction-author → instruction-reviewer + claude-code-guide** (this file ships
to `.claude/commands/devforge/spec-check.md`).

Scope, in `src/commands/spec-check/main.md`:

- PHASE 4 — render the clean-verdict signal alongside the existing ack.
- PHASE 5 (`:219`–`:235`) — **two arms.** Clean → surface the report path and the coverage
  line, fire **no** `AskUserQuestion`, and proceed. Non-clean → the existing verbatim
  report display + the existing three-option gate, unchanged (2–4 options, no authored
  "Other" — the tool auto-injects it).
- PHASE 6 (`:237`–`:247`) — **a leading no-pick clause, then unchanged.** Its shipped
  condition presupposes a PHASE-5 pick exists (*"ONLY when the user's PHASE-5 pick is
  `Revise spec` AND the recommended disposition was REVISE-SPEC"*), and its "any other
  pick" enumeration is over picks — **on the clean arm no pick was captured at all.** So
  the phase opens by naming that case: no PHASE-5 pick → **write NO seed, go straight to
  PHASE 7.** The `Revise spec` matching logic below it is otherwise unchanged, and the
  seed is still written only on a matching pick, which a clean run cannot reach.
- PHASE 7 (`:249`–`:257`) — untouched: the WIP commit was already unconditional.
- The `## Outputs of this command` section and the phase-list prose, wherever they
  describe the human gate as unconditional.

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean.
- `grep -n "AskUserQuestion" src/commands/spec-check/main.md` returns lines **inside the
  non-clean arm only**. Capture the pre-change output first.
- The clean arm still **writes and commits** the report — a diff that skips either has
  broken plan 37's per-command artifact discipline.
- **PHASE 6 no longer presupposes that a PHASE-5 pick exists.** Its shipped text names the
  no-pick case FIRST — clean arm → no seed → PHASE 7 — ahead of the `Revise spec`
  condition, and instruction-reviewer confirms that leading clause is present. Left
  byte-identical, PHASE 6 would test a variable the clean path never binds.
- The non-clean arm's option set is still exactly three named options with no authored
  "Other".
- Plan 62 D4's human-check text survives on the non-clean arm verbatim in substance; the
  clean arm carries the one-sentence reconciliation (nothing to confirm when nothing is
  alleged).

---

### Phase 5 — Mandatory wiring per D5

**Route: python-engineer → python-reviewer for the helper verb; instruction-author →
instruction-reviewer + claude-code-guide for `main.md` and any frontmatter.** Under
D5(a-i) the `disable-model-invocation` removal **IS** a Claude-Code-integration surface —
claude-code-guide is mandatory for it, and the fetched-doc citation belongs in the phase
record.

**Ratified arm, recorded 2026-08-19: (a-ii).** Every "Under D5(a-i)" clause below is a
**dead branch** — it is retained as the record of what was weighed, and executing it
departs from Phase 0. `src/commands/spec-check/main.md`'s frontmatter is NOT touched in
this phase, no description trim is owed, and repo-root `CLAUDE.md`'s model-invocable
counts need no reconciliation. OQ-2's ratified predicate for the verb below is the
**content hash of `spec.md`** recorded in `spec-check.md` at render time.

Scope:

- A new `plan_helper` verb (fact 16 — there is no preflight to extend) implementing the
  presence + freshness gate per OQ-2's ratified predicate, failing closed with a stderr
  message the command copies VERBATIM. **Model it on `specify_helper find-handoffs
  --require`** (fact 18): exit 2, BLOCKED message, no override flag.
- A new `/devforge:plan` PHASE 0a.x block calling it, placed with the other 0a gates
  (`:30`–`:113`) and before PHASE 0b's status flip — **a spec that cannot be planned must
  not be flipped to Approved.**
- Under **D5(a-i) only**: remove `disable-model-invocation: true` from
  `src/commands/spec-check/main.md:5` and **trim the description** to the ≈40-word budget
  plan 63's OQ-1 resolution set for model-invocable commands, keeping the D11 + D9
  under-promise substance.
- Under **D5(a-ii) only**: the blocked-arm text names the command for the user to type,
  and the frontmatter is untouched.

**Verify:**

- `tests/lib/` green, with the new verb's own tests covering: report absent → exit 2;
  report present and fresh → exit 0; report present and stale → exit 2; feature dir
  missing → the same failure shape as the sibling gates.
- The blocked run does **not** flip the spec's `**Status**:` — verified by ordering, and
  by a test if the flip is reachable from the helper layer.
- Under D5(a-i): `grep -rn "disable-model-invocation" src/commands/` returns **exactly one
  file fewer than the same grep returned before this phase's edit** — capture the
  pre-change list first; the description is under the trimmed budget; and repo-root
  `CLAUDE.md`'s model-invocable counts are reconciled **in this phase**, not deferred —
  they are false the moment the flag is removed. **Coordination rule, recorded 2026-08-19:
  read the counts and that grep's total LIVE at execution time and write what is observed
  — never apply this plan's own `13/7 → 14/6` delta, and do not expect a hard-coded six.**
  `85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md`'s D6 arm may remove the flag from
  `/devforge:grill` first, and repo-root `CLAUDE.md`'s plan-85 index line already carries
  the rule that whichever of plans 82/85 ships second reads the counts live.
- Under D5(a-ii): that grep returns the **same** file list it returned before this phase
  (seven as of 2026-08-19, but compare against the captured pre-change list, not the
  digit) and the frontmatter diff is empty.
- `scripts/verify-agent-reachability.py` and `scripts/verify-memory-lane.py` pass
  (nothing here touches either, so a failure means something unintended moved).

---

### Phase 6 — The D14 amendment + the full cross-reference sweep

**Route: instruction-author → instruction-reviewer** for every `src/` and plan-document
edit; **claude-code-guide** for any file shipping into `.claude/`.

Open the phase with `grep -rn "D14\|never an auto-gate\|Opt-in" src/ *.md` and reconcile
the result against D6's list, which is **explicitly not certified exhaustive** — treat a
hit not named there as an omission in this plan, not as a new defect.

Scope: every item in D6's sweep list, plus:

- `CHANGELOG.md` — an entry. **Re-verified 2026-08-19: a `## [Unreleased]` section EXISTS
  (`CHANGELOG.md:8`; the next `##` heading below it is `## [2.0.9] - 2026-08-17`, with
  populated `###` subsections in between), reversing this plan's 2026-08-17 record that
  there was none.** The entry lands there. **Keep the conditional below anyway — that
  fact has now rotted in both directions inside two days:** add the entry under
  `## [Unreleased]` if that section exists when this phase runs, otherwise
  under the release section this change ships in — do not create a stray heading on the
  strength of an older plan's wording.
- repo-root `CLAUDE.md` and `PLAN-STATUS-ARCHIVE.md` — this plan's entries move from NOT
  STARTED to the shipped wording.
- `src/devforge/storage-rules.md` — **only if** OQ-2's ratified predicate introduced a new
  artifact (the sibling-JSON-stamp option). If it did not, the no-op is recorded as
  deliberate.

**Verify:**

- The sweep returns zero dangling references; full test suite green.
- **Plan 62's D14 is AMENDED IN PLACE with the reason**, not deleted and not
  contradicted from a distance — the same mechanism that plan used for its own D9. The
  amendment carries the narrow reading (run-mandatory, not verdict-binding) and the list
  of what did NOT change.
- **`FINDINGS.md` finding 4 is amended, not replaced**: its ordinal, its original text
  and its `NOTE ON THIS ENTRY'S SHAPE` paragraph all survive; the amendment is additive
  and dated; no finding is renumbered.
- **Plan 81's `:129` and `:201` are reconciled** (digits re-verified 2026-08-19; grep the
  quoted claims first), and the reconciliation states which plan owns which half (F3 =
  authoring-side admission; this plan = formalization-side refusal). **Plan 81 ratified and
  shipped on 2026-08-18, so there is no unratified contingency left to write** — the
  reconciliation is written against live text.
- `grep -rn "never an auto-gate" src/` returns only lines that are true after the change.
- No plan vocabulary leaked into any file under `src/`.

---

### Phase 7 — Consumer e2e *(user-driven HARD GATE)*

**Known-answer anchor.** The correct outcome is known in advance for all three cases, so
this is a regression anchor and not an exploratory run.

1. **The phantom case.** A spec carrying a benchmark-shaped preservation AC — an AC over
   a state with no reachable construction site — **MUST** come back
   `UNRESOLVED-SUBJECT`, **MUST NOT** appear in the constraint set, and **MUST** block
   auto-accept so the human gate fires.
2. **The clean case.** A spec whose ACs all resolve and whose quorum is consistent
   **MUST** auto-accept: report written, report committed, **no human gate**,
   `/devforge:plan` proceeds.
3. **The greenfield case.** A spec whose ACs are all new behavior **MUST** resolve via arm
   (b) and **MUST NOT** false-fail. This is D2's whole justification and the case that
   decides whether the mandatory gate is usable at all.
4. **The gate.** With no `spec-check.md` present, `/devforge:plan` blocks with the
   verbatim helper message; after a spec-check run it proceeds; after editing `spec.md` it
   blocks again (OQ-2's freshness predicate).
5. **The z3 path (D7(c)).** On a machine without `z3-solver`, `/devforge:plan` blocks
   with the one-time install message and proceeds once installed.

**Verify:**

- Each of the five is scored **explicitly** — stated, not summarized — and case 1 records
  whether the `## UNRESOLVED SUBJECTS` section named the right AC and showed what was
  searched.
- **The observed false-positive rate on case 3 is recorded**, since OQ-3's bound and the
  false-UNRESOLVED rate are the same dial and this is the only place its setting is
  observed.
- Record the result in `REGRESSION-ANCHORS.md`, naming the Phase-3 clean-predicate test
  alongside the observed behavior.
- **If it fails**, record the negative here with the artifacts and identify which
  mechanism produced it before proposing anything further — a false UNRESOLVED on case 3
  is a D2/OQ-3 finding, a missed phantom on case 1 is a D1/D4 finding, and they have
  different fixes.

---

## Non-goals

- **Making `/devforge:grill` mandatory.** OQ-1 records the maintainer's 2026-08-17
  decision to do it, and the structural reasons it cannot ride along here; **that work is
  `85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md`'s subject** *(created 2026-08-17, NOT STARTED —
  recorded here 2026-08-19)* **and no phase here builds it**, and a phase that starts
  editing `src/commands/grill/` has left this plan.
- **Re-opening or amending any of plan 81's F1–F6** *(rewritten 2026-08-19: all six
  SHIPPED 2026-08-18, so "building" them is no longer the available mistake)*. **The
  non-goal is to leave them alone** — no phase above edits a site plan 81 landed, and a
  phase that starts rewriting `/devforge:specify` Step 4.4 has left this plan. **File
  overlap is not site overlap:** Phase 5 adds a NEW PHASE-0a block to
  `src/commands/plan/main.md`, which plan 81 also edited at other sites, and that is in
  scope. **The two
  plans stay independent**: D8 records the interplay, and neither is a precondition for
  the other. Plan 81's instruction-only tripwire binds ITS files and says nothing about
  this one, which legitimately writes Python under `src/devforge/lib/_spec_check/`.
- **Vacuity or gap detection.** Plan 62 D7 deferred both past v1 and this plan does not
  revive them. An unresolved subject is a *formalization* failure, not a vacuity proof —
  do not let the words converge.
- **A second adversarial-LLM formalization verifier.** Plan 62 D8 flagged it for v2 and
  it stays there; D3's mechanical check is deliberately NOT a second opinion, it is a
  file check.
- **Growing the disposition set.** Three dispositions (fact 7), unchanged. An unresolved
  subject drives the recommendation toward `REVISE-SPEC`; it does not become a fourth
  verdict.
- **Making the `/devforge:plan` gate read the verdict.** D5 is explicit: presence +
  freshness only. A gate that blocks on `REVISE-SPEC` is the design D14 refused.
- **Arithmetic over multiple variables, or any other v1 IR limit** (plan 62 D6). The
  supported logic is unchanged.
- **Touching plan 71's dead-code chain or plan 77's emission-matrix accounting.** Neither
  is fed or read by anything here.

---

## Dependencies + related

- **Plan 62** (`62-SMT-REQUIREMENTS-CONSISTENCY-PLAN.md`) — the command itself. **D14 is
  the boundary this plan crosses (D6); D10 is the constraint D7 collides with; D3, D4,
  D8, D9, D11 and D13 all survive unchanged**, and D9's *"asserted reachable"* principle
  is the direct ancestor of subject resolution one layer down.
- **Plan 81** (`81-INFERENCE-RULES-PLAN.md`) — F3 is the authoring-side sibling (D8), its
  archive entry supplies the incident at the abstraction level this file uses, and its
  `:129` / `:201` are Phase-6 reconcile targets *(digits re-verified 2026-08-19)*.
  **SHIPPED (build) 2026-08-18, Phases 0–6, one commit per phase; its Phase 7 consumer
  e2e is DEFERRED — treat all six fixes as shipped and none of them as
  consumer-validated.**
- **Plan 77** (`77-POST-CHANGE-OUTPUT-MATRIX-PLAN.md`) — the **visibility bar** this
  plan's mechanism is measured against. Its own mechanism rests on reasoning, not
  evidence (Phases 1 and 3 WAIVED); do not cite it as validated.
- **Plan 63** (`63-SKILL-COLLISION-SUPPRESSION-PLAN.md`) — the 13/7 carve-out D5(a-i)
  reopens for one command, and the description-budget rule that flip inherits.
- **Plan 48** (`48-REVIEW-MANDATORY-GATE-PLAN.md`) — SHELVED, and the closest prior art
  for a mandatory-gate argument in this repo. Its `:14` names the
  `/devforge:specify` forward-precondition as the canonical shape, which is what D5(a)
  adopts. **Note its `:8` claim that "Every forge command sets
  `disable-model-invocation: true`" is stale post-plan-63 — recorded, not owned, not
  fixed here.**
- **Plan 37** — the per-command artifact WIP-commit discipline the clean arm must not
  drop.
- **Plan 19** — the cry-wolf precision stance D2 and D4 are both written against.
- **`FINDINGS.md` finding 4** — the file-less finding whose *"a MANDATORY refusal of this
  shape has no owner today"* clause this plan answers for one of its two sibling shapes
  (D8). Amended, not replaced, at Phase 6.

---

## Context for next session

**The one sentence that governs everything here:** the prover returned a correct verdict
over an AC that could not be violated, so the fix is not a better prover — it is a
refusal to formalize a subject the code does not produce.

**Trap 1 — reading the directive's literal rule as buildable.** *"Every AC subject must
resolve to a construction site in the code"* cannot hold at a stage that runs before any
code is written. D2 is the whole content of that correction, and a build session that
ships the literal rule ships a gate that fails every greenfield spec.

**Trap 2 — unifying the two quorum polarities.** They are deliberately opposite (D4).
Strict majority for the unsat core because a one-off contradiction must not become a
recommendation; any-pass for resolution because a one-off find is proof of existence.
The code must keep them visibly separate and say why.

**Trap 3 — over-reading the D14 reversal.** What becomes mandatory is that the check RAN
and its report is FRESH. **The verdict never binds.** A future session reading "spec-check
is mandatory now" without that qualifier will build the verdict-blocking gate D14
correctly refused, and will be able to cite this plan while doing it.

**Trap 4 — treating three facts as one.** The agent is *tool-capable* of searching
(`tools: Read, Grep, Glob`), is *instructed not to* (`"from that input alone"`), and
therefore needs an *instruction* change and **no tools change**. Missing the middle fact
produces a plan that edits the tools line for no reason; missing the third produces one
that adds `Bash`.

**Trap 5 — assuming `/devforge:plan` has a preflight to extend.** It does not (facts 16,
17). D5(a) writes a new verb and a new phase block, and it is the first fail-closed
mechanical gate in that command. Budget for it.

**Trap 6 — believing a fourth coverage status is additive.** It is not. Three shipped
sites branch on `"formalized"` or `_SKIPPED_STATUSES` (facts 3, 5, 6), `_SKIPPED_STATUSES`
exists twice, and an unrecognized status currently passes validation and vanishes from the
coverage headline **without any error**. Every one of those is a Phase-1 edit site.

**Corrected 2026-08-19: the plan-79 / plan-80 / plan-81 work this file cites is
COMMITTED** (plan 81 one commit per phase, F3 at `59b5152`), so the earlier reading —
*the working tree is uncommitted throughout, and any "shipped" claim means
reviewed-but-uncommitted rather than released* — no longer describes them. **The standing
instruction survives unchanged and is the point of this paragraph: re-check every claim
from the code rather than from a Status line**, including the ones dated 2026-08-19 —
that discipline is how this paragraph's own premise was caught.

**Discovered while drafting, NOT owned by this plan and not fixed here:**
`48-REVIEW-MANDATORY-GATE-PLAN.md:8` states *"Every forge command sets
`disable-model-invocation: true`"*, which plan 63 falsified (13 of 20 dropped it, verified
2026-08-17: seven files under `src/commands/` carry the flag). Route it separately; no
phase above touches that file.

**Discovered while BUILDING (2026-08-19), recorded and NOT fixed here.** Four items, none
of which any phase above owns; each is stated so a later session finds it rather than
rediscovering it.

1. **`src/devforge/lib/_spec_check/_cli.py` is 1300 lines** (measured 2026-08-19; the
   package totals 4574 across nine modules, with `_consume.py` at 747 and `_report.py` at
   609 the next two). This is
   **PRE-EXISTING debt that Phases 1–3 grew rather than created** — the subject-resolution
   record, the fourth coverage status, the any-pass merge and the new report section all
   landed in modules that were already oversized. **The split was DEFERRED deliberately:**
   doing it in the same change-set as a behavior change would have made the diff
   unreviewable and put the `_spec_check` regression suite's value at risk exactly when it
   was the only net under a semantic change. Candidate follow-up plan; nothing here depends
   on it.
2. **A pre-existing zero-byte representative-IR defect in PHASE 4.** The representative-IR
   picker resolves to `ir-canon-1.json` whenever the quorum verdict is not
   `confirmed_unsat`. When pass 1 exhausted its PHASE-2.3 retry cap and pass 2 succeeded,
   that file exists but is ZERO BYTES (the `>` redirect creates it even on a non-zero
   `consume-ir` exit), so `render-report --ir-file` gets an unparseable file and exits 2 —
   a hard stop on a run that HAD a solvable IR. **It predates this plan** (the picker and
   the redirect behaviour are both shipped v1) and this plan did NOT fix it; the sibling
   `ir-files.json` assembly guards the identical case with a `try`/`except`, which is where
   a fix would take its shape from.
3. **The consumer-side CBM discovery-gate `PreToolUse` hook blocks the formalizer's FIRST
   `Read`/`Grep`/`Glob` of a session as a retryable error.** Subject resolution makes the
   `spec-formalizer` a tool user for the first time, so it now meets that gate. **Left
   unhandled deliberately** — the hook passes every subsequent matched call in the same
   session, so the expected consequence is one retried tool call, not a failure; inventing
   a carve-out before observing the behaviour would be speculative. **Phase 7 observes it**
   and records what actually happened.
4. **`plan_helper verify-spec-check --spec <path>` takes a NAMED flag where every other
   verb in that file takes its spec/plan path POSITIONALLY.** The departure is deliberate
   and is commented in the code at the verb's `add_parser` registration, with the recorded
   reason: *a named `--spec` reads unambiguously in `plan/main.md`'s Phase 0a.8 bash
   block, which already emits `--spec` explicitly.* Recorded here so a later consistency
   pass does not "fix" it into a positional and break that phase's invocation.

---

## When resuming work

1. Read this file in full, then **Verified mechanics** again — twenty-one rows, each
   checkable in under a minute. **If rows 3, 5, 6, 11, 16, 17 or 18 no longer hold, stop
   and re-derive**: they are the cost argument, and D1's build shape and D5's option pick
   both rest on them. **(AMENDED 2026-08-19 — Phases 1–6 are BUILT, so SEVEN rows are now
   deliberately false and must NOT trigger that stop.** The whole table is a PRE-BUILD
   record. Rows **1**, **5** and **6** describe the three-status ledger the build replaced
   with four (`COVERAGE_STATUSES` now carries `unresolved_subject`, the agreement rule has
   its third branch, and the coverage headline has its third term); row **3**'s two
   `_SKIPPED_STATUSES` copies still exist with their original value, but its closing claim
   that *every* status branch keys on `== "formalized"` or `in _SKIPPED_STATUSES` no longer
   holds; row **11** quotes the *"from that input alone"* sentence Phase 2 deleted (that
   grep returns zero); rows **13** and **14** quote the opt-in strings Phase 6 rewrote; and rows
   **16** and **17** — no `plan_helper` preflight verb, no mechanical gate in
   `/devforge:plan` — were falsified by Phase 5, which added exactly those. Row **10**
   (`tools: Read, Grep, Glob`) is still true and must stay true. **The stop-and-re-derive
   rule now applies only to a row that changed for a reason OTHER than this plan's own
   build** — re-derive from the code, never from this table.**)**
2. Read **plan 62 in full** — not just D14. D3, D4, D9, D10, D11 and D13 all constrain
   what this plan may do, and D9 is subject resolution's direct ancestor.
3. Read the **`PLAN-STATUS-ARCHIVE.md` plan-81 entry** for the incident. **Do not open
   `81-EVIDENCE-V2-BENCHMARK-RUN.md`** to enrich this file — the abstraction level in the
   tracked entry is the ceiling, by the constraint at the top.
4. **Re-verify every anchor before use. Grep the quoted string, never the `:NNN`** —
   `COVERAGE_STATUSES`, `_SKIPPED_STATUSES`, `marked formalized but has no constraint`,
   `Checked {0} of {1}`, `from that input alone`, `find-handoffs --require`,
   `disable-model-invocation`.
5. **Start at Phase 7 — Phases 0–6 are DONE 2026-08-19 (see the status line's commits);
   nothing is left to ratify or build.** Phase 7 is the user-driven consumer e2e — the
   five known-answer cases — DEFERRED 2026-08-20, not waived. *(This step read "Start at
   Phase 0, and read OQ-1's resolution before ratifying D6" until 2026-08-19, then "Start
   at Phase 1 — Phase 0 CLOSED 2026-08-19 and nothing is left to ratify" until 2026-08-20;
   each rewrite is recorded rather than deleted, because a resuming session that re-opens
   ratification would re-litigate settled picks, and one that re-enters Phase 1 would
   rebuild shipped code.)* **Read every
   `**Ratified 2026-08-19:**` paragraph before scoring Phase 7 or touching anything
   nearby** — they are the contract the shipped build implements, and three of them bound
   what a Phase-7 result may be blamed on: **D5(a-ii)** KEPT
   `disable-model-invocation: true`, so Phase 5's frontmatter diff was EMPTY and the
   plan-63 carve-out is untouched; **D7(c)** fails closed on absent `z3-solver` with no
   `install.sh` change, which is exactly what case 5 exercises, so a block there is the
   ratified design and not a finding; **D6** is run-mandatory only, never verdict-binding —
   a run that blocks `/devforge:plan` on a REVISE-SPEC verdict is a DEFECT, not the
   feature. The intended
   sibling grill-mandatory change is `85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md`, not this
   one *(recorded 2026-08-19: it exists, is NOT STARTED, and awaits its own Phase 0)* —
   **and OQ-2's ratified content-hash predicate is now a standing constraint on that
   plan's D4**, which must ratify the same predicate.
6. **D5's sub-fork is DECIDED: (a-ii).** *(This step read "Decide D5's sub-fork
   explicitly" until 2026-08-19.)* (a-i) is NOT the ratified option — a build session that
   removes `disable-model-invocation: true` or trims the description has departed from the
   ratification, and that is exactly how the plan-63 carve-out gets reopened by accident.
7. Route every edit through the house loops: **python-engineer → python-reviewer,
   test-first** for helpers; **instruction-author → instruction-reviewer + claude-code-guide**
   for anything shipping into a consumer's `.claude/` — which includes
   `src/agents/spec-formalizer.md` (Phase 2), `src/commands/spec-check/main.md` (Phase 4)
   and `src/commands/plan/main.md`'s new PHASE-0a block (Phase 5). *(Corrected 2026-08-19:
   this step named "the frontmatter flip (Phase 5)" while D5's sub-fork was open. Under the
   ratified (a-ii) there is no frontmatter flip; the claude-code-guide obligation attaches
   to the command-body edits instead, which ship to `.claude/` just the same.)*
8. Re-read the evidence constraint at the top before writing a sentence into this file,
   into any `src/` file, or into a commit message. **It binds execution, not just
   drafting.**
