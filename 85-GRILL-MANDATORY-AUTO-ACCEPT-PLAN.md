# 85 — `/devforge:grill`: mandatory run + auto-accept the clean verdict

**Status:** ✅ **DONE (build) 2026-08-26 — Phases 0–4 shipped** (`10cc8ec` + `ad0cd50` Phase 0 / `3f86a58` phase reconciliation / `56f7a74` Phase 1 / `58e01be` Phase 2 verb / `63262d3` Phase 2b CLI / `143be80` Phase 3 / `c0711b3` the PROCEED wording fix / `1b6b27a` Phase 4 + the gate WIRING / `4c08908` the stakes hint). **Phase 5 consumer e2e DEFERRED — user-driven HARD GATE, NOT run. The maintainer stated 2026-08-26 that it will be run AFTER the implementations queued behind it, as one batch; it is NOT WAIVED, and the plan closes as DONE (build) on that basis.** This is **BUILD-VERIFIED, NOT CONSUMER-VALIDATED** and no phase above may claim otherwise. **PHASE 0 IS CLOSED: every D-item and OQ ratified (D3 + D4 on 2026-08-24; D1, D2, D5–D8 and OQ-1–OQ-3 on 2026-08-25).** Two ratifications DIVERGE from this file's own recommendations and both are argued at their decision: **D3** (the fail-closed freshness gate is REJECTED — it penalizes acting on findings) and **D2** (a 2-pass quorum IS built, over this plan's recommendation of none). ⚠ **D3 was ratified AGAINST its own drafted recommendation** — the fail-closed presence+freshness gate is REJECTED because it creates a loop that penalizes acting on findings (see D3's ratification block). One precondition was discharged in the same session: the corpus-wide `update.sh` remedy claim was corrected across five sites (see D3's `## Discharged precondition` note). No other `src/` edit before the remaining items close. **AMENDED 2026-08-23 — reconciled against three plans that shipped AFTER this file was drafted: plan 81 (F6, 2026-08-18), plan 82 (DONE build 2026-08-19) and plan 83 (DONE build 2026-08-20). Nothing was ratified by that pass.** What it changed: **D4's predicate and OQ-1's hand-off shape are now externally CONSTRAINED** — plan 82 ratified the content hash (its OQ-2) and the name-it-for-the-user arm (its D5(a-ii)), so both stop being open forks and become confirm-or-diverge-with-an-argument; **the plan-83 coordination debt this plan inherited is recorded DISCHARGED as a verified no-op**; and **D6's sweep list is refreshed** against the surfaces plans 82/83 created or rewrote. Every dated note below narrows a decision space; **none picks an option, and every D/OQ heading keeps its `*(OPEN…)*` marker.**
**Branch:** `develop-2.0-init`
**Created:** 2026-08-17.

This plan document contains no private-client identifiers and is intended to be
**committed normally**, unlike the deliberately-untracked plans 73/74/75.

**Numbered 85, not 83.** The brief that commissioned this file named `83-`; at drafting
time `83-DOWNSTREAM-REENTRY-SEED-PLAN.md` and `84-ARCHITECT-CONSULT-ACCUMULATION-PLAN.md`
both already existed at repo root (verified 2026-08-17 by a repo-root `[0-9]*.md` glob), so
`83-` would have re-created exactly the duplicate-number collision repo-root `CLAUDE.md`
had just resolved for `81-`. **85 is the next free number.** A session looking for this
plan under `83-` is looking for a file that never existed.

## Evidence constraint

Two evidence files sit at repo root and are **UNTRACKED private-client records**:
`81-EVIDENCE-V2-BENCHMARK-RUN.md` and `77-EVIDENCE-DISCOVERY-TO-LOCK-INVERSION.md`.
Neither may be committed, and neither may be quoted, excerpted or cited by content into
this file or any other tracked file.

**This plan needs neither.** Its motivation is not an incident: it is a maintainer
decision plus structural symmetry with plan 82. **Nothing here rests on benchmark data,
and no phase may import any** — if a future amendment finds itself reaching for a
benchmark number to justify a decision, that is a signal the decision is unargued, not a
licence to open the evidence file.

---

## Origin — the maintainer's statements, recorded verbatim

Two statements, 2026-08-17, in the session that ratification-drafted plan 82:

> side note - i decided to make grill mandatory

> i will need draft plan for grill also

That is the entire authorization. **There is no incident behind this plan, no failing
run, and no measured cost** — and the plan is written so that a ratifier can see that
plainly rather than inferring an evidentiary base that does not exist.

**Its sibling is `82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md`, which must be read
first.** That plan's OQ-1 records the same maintainer statement, resolves it, and then
argues on three structural grounds why grill could NOT ride along inside it — soft
findings with no deterministic layer, a 4-way disposition at a different pipeline seat,
and a cost shape that must be measured rather than assumed. **This plan is the sibling
those three grounds called for.** What plan 82's OQ-1 says transfers is the SHAPE of its
D5 and nothing else:

> **interrupt the human only when a finding exists**, and render + commit the artifact
> unconditionally either way.

Everything below is the work of deciding what "a finding exists" means for a command that
has no prover.

---

## What is actually being added

**A grill gate at `/devforge:breakdown` does not exist today and is not being
strengthened — it is being created.** Verified 2026-08-17: a case-insensitive grep for
`grill` across `src/commands/breakdown/` returns **zero** matches. Plan 23's design note
(`23-ADVERSARIAL-GRILLING-PLAN.md:18`) says *"the human makes the final call at the
existing `/breakdown` approval gate"*, and that sentence describes an intent, not a
mechanism: `/devforge:breakdown`'s PHASE 4 user-approval gate approves the TASK
BREAKDOWN and carries no grill content of any kind.

**So this plan does three separable things**, and Phase 0 may ratify them independently:

1. **A freshness-stamped grill report** (Phase 1) — useful under the current opt-in stance
   on its own, because it lets any reader tell a report about the current `plan.md` from a
   report about a superseded one.
2. **A fail-closed gate at `/devforge:breakdown`** (Phase 2) — what makes the run
   mandatory.
3. **Auto-accept of the clean verdict** (Phase 3) — what keeps (2) from being pure
   friction, plus the frontmatter/description consequences that follow (Phase 4).

**(1) stands alone. (2) without (3) is a gate that interrupts every feature. (3) without
(2) is a nicety.** A Phase-0 decline of (2)+(3) keeps Phase 1; say so at ratification
rather than treating the plan as all-or-nothing (this mirrors plan 82's D6 separability
note, and the same reasoning applies).

---

## Verified mechanics (2026-08-17)

Every row was confirmed by opening the named file. **The quoted token is the anchor; the
digit is a dated hint** — this repo has documented anchor rot, so grep the string, never
the `:NNN`.

| # | Fact | Evidence |
|---|------|----------|
| 1 | `/devforge:grill` carries `disable-model-invocation: true` — it is one of plan 63's keep-7 | `src/commands/grill/main.md:5` |
| 2 | Its `description` ends *"Opt-in — never an auto-gate."* and is one unbroken paragraph of roughly 70 words (hand-counted at drafting; **measure it mechanically at build**) | `src/commands/grill/main.md:3` |
| 3 | Rule 1 reads *"Opt-in, never an auto-gate — `/devforge:grill` runs only by invocation (like `/devforge:audit`); it never auto-runs, and there is NO forced gate on every `/devforge:plan` run."* | `src/commands/grill/main.md:391` |
| 4 | The body restates it twice more — *"Opt-in by construction — never an auto-gate"* and *"Skipping `/devforge:grill` leaves the `/devforge:plan → /devforge:breakdown` chain byte-unchanged"* | `src/commands/grill/main.md:16` (both) |
| 5 | `DISPOSITION_VERDICTS = ("PROCEED", "REVISE-PLAN", "RE-ENTER-UPSTREAM", "KILL")` — the 4-way set, validated by `render_report` | `src/devforge/lib/_grill/_report.py:81`, `:510` |
| 6 | Phases: 0 preflight · 1 resolve-scope · 2 attack (`devils-advocate`) · 3 validate (grounding gate) · 4 refute (cross-examination) · 5 classify · 6 report + WIP-commit · 7 human gate | `src/commands/grill/main.md` `## PHASE 0`–`## PHASE 7` headings |
| 7 | **`apply-verdicts` partitions into FOUR buckets** — `confirmed`, `dismissed`, `uncertain`, `contested` — written to `$WORKDIR/partition.json`; the report headline is `confirmed` + `contested`, and `dismissed` + low-stakes `uncertain` ride a `## Dismissed / Worth a Glance` appendix | `src/commands/grill/main.md:259`–`:264`, `:326` |
| 8 | **PROCEED is reachable with findings present.** PHASE 3 routes to PROCEED when `validated.json` is `[]`, and PHASE 5 says *"PROCEED is the no-surviving-attack / all-accepted-as-risk case … reach it here too when every survivor is accepted as risk"* — so **`disposition == PROCEED` is strictly weaker than "no finding survived"** | `src/commands/grill/main.md:194`, `:283` |
| 9 | The seed is written ONLY inside PHASE 7's matching re-entry arm (plan 39's rule), never for Proceed, Kill, or a cross-pick | `src/commands/grill/main.md:29`, `:357`–`:364` |
| 10 | **PHASE 7 also owns the single scratch sweep**, and Rule 10 states it: *"all intermediate scratch lives in `$WORKDIR` … swept by the single `rm -rf "$WORKDIR"` at the end of PHASE 7, never mid-run."* **A design that skips PHASE 7 outright strands `$WORKDIR`** | `src/commands/grill/main.md:382`–`:387`, `:400` |
| 11 | PHASE 6 WIP-commits `grill.md` + `grill-state.json` UNCONDITIONALLY via `artifact_helper commit-artifacts`, then advances state with `check-status-and-flip --to report --status complete` | `src/commands/grill/main.md:328`–`:340` |
| 12 | **`specs/[feature]/grill-state.json` already exists**, is helper-owned, per-feature, advanced by `check-status-and-flip --feature-dir`, and is **already committed by PHASE 6** — a JSON sibling with a zero-cost home for a stamp | `src/commands/grill/main.md:31`, `:92`, `:331` |
| 13 | **`_grill/` has NO quorum mechanism** — a repo-scoped case-insensitive grep for `quorum` under `src/devforge/lib/_grill/` returns **zero** hits. PHASE 2 dispatches **ONE** adversary, once; there is no `--passes` analog | `src/devforge/lib/_grill/` (grep, zero hits); `src/commands/grill/main.md:142` |
| 14 | **`src/commands/breakdown/` contains ZERO grill references** (case-insensitive grep) — the gate is new | `src/commands/breakdown/` (grep, zero hits) |
| 15 | **`/devforge:breakdown`'s only entry-side guard is PROSE** — PHASE 0b reads `constitution.md` and stops on the unpopulated sentinel; there is no helper call behind it | `src/commands/breakdown/main.md:76` |
| 16 | **Its mechanical `verify-*` family is all FINALIZE-side**, in `## PHASE 3.5: Integrity gates` — `verify-contract-chain`, `verify-ac-coverage`, `verify-agent-roster`, `verify-manifest-present`, `verify-property-coverage`, `verify-dead-code-coverage`; four are HARD with no Risk-Assessment bypass | `src/commands/breakdown/main.md:448`–`:525` |
| 17 | `breakdown_helper` exposes 18 verbs; **none is a preflight or an upstream-artifact precondition.** `pick-plan` exits 2 when no valid plan is found (its own input), and `read-plan-handoff` returns `no-handoff` GRACEFULLY rather than failing | `src/devforge/lib/breakdown_helper.py:3575`–`:3881` (the `sub.add_parser` block); `src/commands/breakdown/main.md:38`, `:67` |
| 18 | So a fail-closed precondition at `/devforge:breakdown` would be **the first entry-side mechanical gate in that command** — the same "first in this command" cost plan 82's D5 records for `/devforge:plan` | facts 15–17 together |
| 19 | The gate SHAPE already exists in the pipeline: `.devforge/lib/specify_helper find-handoffs --require` is a fail-closed forward precondition whose surrounding text states it carries no override. Plan 48 independently names `/devforge:specify`'s gate the closest forward-precondition analogue | `src/commands/specify/main.md:99` (the verb call), `:115`/`:119` (the no-override text); `48-REVIEW-MANDATORY-GATE-PLAN.md:14` |
| 20 | **Plan 48 — the repo's one mandatory-gate push — is SHELVED**, keep-the-warning, not built; its revival trigger is an OBSERVED `/devforge:review` skip | `48-REVIEW-MANDATORY-GATE-PLAN.md:3` |
| 21 | **Plan 48's OQ-1 already framed the exact freshness problem this plan's D4 answers** — a presence check is satisfied by a stale report that never saw the current code, and *"a future session … may FALSELY believe the gate guarantees the verdict reflects a review of the CURRENT code"* | `48-REVIEW-MANDATORY-GATE-PLAN.md:30` |
| 22 | Plan 63's ratified carve-out is **13 drop / 7 keep**, and grill is kept BY NAME because *"their own descriptions say 'Opt-in — never an auto-gate'; auto-start would contradict plans 23/62"* | `63-SKILL-COLLISION-SUPPRESSION-PLAN.md:228`–`:233` |
| 23 | Plan 63's OQ-1 resolution sets a **≈40-word description budget** for the 13 model-invocable commands and leaves the 7 carved-out commands their full `src/CLAUDE.md` catalog entries as *"their only model-facing awareness source"* | `63-SKILL-COLLISION-SUPPRESSION-PLAN.md:213`–`:220` |
| 24 | `_PROMOTED` carries 20 command names and **the emitter never reads or writes `disable-model-invocation`** — that field lives only in each command's own frontmatter | `scripts/emitters/claude.py:57`, `:73` |
| 25 | Plan 70's problem statement already prices the chain that would grow: *"A full pre-implement chain (`/research` → `/specify` → `/plan` → `/breakdown`, plus optional `/grill` / `/spec-check`) takes the maintainer ~2h wall-clock"* — **with grill OPTIONAL** | `70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md:10` |
| 26 | **Plan 70's Phase 2 (real-run diagnosis) is DEFERRED to post-release**, so **no per-command wall-clock number for `/devforge:grill` exists anywhere in this repo** | `70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md:3` |
| 27 | Grill's no-arg run resolves the `specs/NNN-*` directory whose `plan.md` was modified most recently (plan 64) | `src/commands/grill/main.md:76`, `:125` |
| 28 | `src/CLAUDE.md` carries four grill-opt-in surfaces: the bracketed `[/devforge:grill]` chain step, the bracket legend, the seven-human-typed-only sentences, and the catalog entries (the `####` entry says *"it is NOT a mandatory gate"* and *"The USER owns the final verdict at the `/devforge:breakdown` approval gate"*). **AMENDED 2026-08-23 — all six anchors re-verified and all hold, but plan 82 moved the surrounding ground:** `/devforge:spec-check` is now UNBRACKETED in the chain, so **`[/devforge:grill]` is the ONLY bracketed step left** and the legend has exactly one referent; plan 82 also ADDED a `## Enforced Quality Gates` Hard-Gates row for spec-check (`:152`) that this row's four-surface count predates. See D6's sweep list for what each of those means for Phase 4 | `src/CLAUDE.md:44`, `:47`, `:49`, `:62`, `:79`, `:99`–`:100`; the two additions `:44` (unbracketed spec-check) + `:152` |
| 29 | **`src/commands/plan/main.md` is a sweep target the gate falsifies.** Its PHASE-4 `stakes-hint` block says the hint *"never gates `/devforge:breakdown`"* and *"`/devforge:grill` remains opt-in"* — **the first clause becomes FALSE under D3.** The hint itself (advisory, always exit 0) is untouched by this plan. **AMENDED 2026-08-23 — the stakes-hint half HOLDS and its digit moved (`:615` → `:640`, both clauses still in one sentence); the PHASE-0a.7 half is RETIRED.** Plan 83 rewrote that no-seed branch on 2026-08-20 and it no longer contains *"`/devforge:grill` is opt-in"* — the live sentence says the project-wide glob accepts a seed from any `source` and that *"`/devforge:grill`'s REVISE-PLAN arm is the only one that emits that target today"*, which **stays TRUE under this plan** (D3 changes WHEN grill runs, never which `target_stage` its arms emit). **It is no longer a sweep target; do not go looking for the retired clause.** A THIRD site in the same file is new to this row — see D6's sweep list | `src/commands/plan/main.md:640` (live, both clauses); `:115` (the rewritten no-seed branch — quote re-read 2026-08-23) |

*(Facts 23 and 28 as of 2026-09-03: plan 93 moved `grill`, `spec-check` and `fix` under
OQ-1's ≈40-word budget and cut their `src/CLAUDE.md` catalog entries to the short form, so
the human-typed-only sentences now name FOUR commands, not seven, and those four are the
carved-out set still carrying full entries.)*

### Re-verification pass, 2026-08-23

**The eight rows `## When resuming work` names as the cost and scope argument — 8, 10, 13,
14, 15, 16, 17 and 26 — were re-checked against the live tree, and all eight HOLD.** With
their digits, so a reader can spot-check without re-deriving: the hand-written
four-empty-bucket `printf` literal (`grill/main.md:198`), PHASE 3's empty-`validated.json`
→ PROCEED route (`:194`) and PHASE 5's *"all-accepted-as-risk"* clause (`:283`); the single
end-of-run sweep (`:386`) and Rule 10 naming it as the only one (`:400`); **zero** `quorum`
hits under `src/devforge/lib/_grill/`; **zero** `grill` hits under `src/commands/breakdown/`;
breakdown's prose-only PHASE-0b constitution guard (`breakdown/main.md:76`) with
`## PHASE 3.5: Integrity gates` still holding the entire `verify-*` family (`:448`) and the
PHASE 0a → 0a.5 → 0b structure still putting the `**Status**:` flip at 0b (`:30`, `:57`,
`:74`); `breakdown_helper` still exposing **18** `sub.add_parser` verbs with **none** a
preflight or upstream-artifact precondition; and plan 70's Phase 2 still DEFERRED
(`70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md:3`), so **no per-command grill wall-clock number
exists anywhere in this repo** and D7's obligation is unchanged.

**Two digits drifted; neither claim did.** Fact 9's PHASE-7 anchor moved — the `write-seed`
call now sits at `grill/main.md:369`, not inside the quoted `:357`–`:364` range (its first
anchor `:29` holds) — and fact 17's parser block shifted two lines to
`breakdown_helper.py:3577`–`:3883`. **Grep the quoted string; the table's digits are dated
hints, exactly as its own preamble says.** For orientation, `src/commands/grill/main.md`'s
phase headings now open at PHASE 6 `:297` and PHASE 7 `:342`.

**One CONTENT change since drafting, and it touches nothing this plan decides.** Plan 81's
F6 (2026-08-18) widened PHASE 5's RE-ENTER-UPSTREAM attribution sentence IN PLACE
(`grill/main.md:280`): `specs/[feature]/research-handoff.json` and
`specs/[feature]/discover-handoff.json` became MANDATORY trace inputs where present, and
`spec` is the introducing stage ONLY when the invalidated conclusion has no upstream
source. **No phase was added, renamed or renumbered, and no heading moved — fact 6's
eight-phase list stands unchanged.** D1 reads the partition, D3 reads presence + freshness,
D5 rewires PHASE 7's entry; none of the three reads the attribution sentence. Recorded so a
build session does not mistake the widened paragraph for drift this plan owes a
reconciliation on.

### Claude Code authoring surface, verified against current docs

Fetched 2026-08-17 from `https://code.claude.com/docs/en/slash-commands`, which now serves
the merged **"Extend Claude with skills"** page — *"Custom commands have been merged into
skills. A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md`
both create `/deploy` and work the same way."* From its Frontmatter reference table:

- **`disable-model-invocation`** — *"Set to `true` to prevent Claude from automatically
  loading this skill. Use for workflows you want to trigger manually with `/name`. Also
  prevents the skill from being preloaded into subagents. As of v2.1.196, also prevents
  the skill from running when a scheduled task fires with the skill as its prompt.
  Default: `false`."*
- **`description`** — *"What the skill does and when to use it. Claude uses this to decide
  when to apply the skill. … Put the key use case first: the combined `description` and
  `when_to_use` text is truncated at 1,536 characters in the skill listing to reduce
  context usage."*
- **All fields are optional**; only `description` is recommended.
- The visibility table states the context consequence precisely: with
  `disable-model-invocation: true` → *"Description not in context, full skill loads when
  you invoke"*; at the default → *"Description always in context, full skill loads when
  invoked."*

**One fact plan 82 did not record, and it sharpens D6.** The same page's *"Skill
descriptions are cut short"* section states that the listing has a **budget scaling at 1%
of the model's context window**, and — the load-bearing sentence — *"When the listing
overflows, Claude Code drops descriptions starting with the skills you invoke least, so
the skills you use most keep their full text."* **A rarely-invoked command is first in
line to lose its description.** Grill is, by construction, among the least-invoked
commands in the set. So the (a-i) flip does not reliably buy model awareness; it buys a
listing entry that is dropped first under pressure. The tunables named there —
`skillListingBudgetFraction`, `SLASH_COMMAND_TOOL_CHAR_BUDGET`, `skillListingMaxDescChars`,
and `skillOverrides` `"name-only"` — are consumer settings this framework does not own,
and **this plan proposes touching none of them** (see `## Non-goals`).

---

## Decisions — ratify at Phase 0, none is settled

Each carries a recommendation and the argument against it.

### D1 — What CLEAN means for a command with no deterministic layer *(RATIFIED 2026-08-25 — option (a), STRICT)*

> **RATIFIED 2026-08-25 — (a) STRICT: CLEAN when `confirmed`, `contested` AND `uncertain`
> are all empty.** `dismissed` may be non-empty. The intermediate option this decision
> names (tolerate `uncertain`) was on the table and was DECLINED.
>
> **Scope narrowed by D3's ratification — read this before applying D1 anywhere.** The gate
> reads `adversary_status`, never cleanliness, so **D1 no longer governs the gate at all.**
> It governs exactly one thing: whether PHASE 7's HUMAN GATE fires (D5's auto-accept arm).
> A build session that wires the CLEAN predicate into the `breakdown_helper` verb has
> misread both decisions.
>
> **Why `uncertain` blocks — the asymmetry argument, which is stronger than the plan's own.**
> An `uncertain` finding is one the refuter could not resolve. Auto-accepting on it means
> **the weakest evidence state produces the strongest action** — no human ever sees it. That
> is backwards on its face, independent of how often it happens.
>
> **Why (b) was rejected: fact 8 makes it unsafe, not merely weaker.** PROCEED is reachable
> via the all-accepted-as-risk branch, where findings SURVIVED refutation and the classifier
> judged none plan-fatal. Under (b) such a run would auto-accept and the human would never
> see confirmed findings — the exact inverse of what a report with a headline is for.
>
> ⚠ **Interaction with D2's ratified quorum, recorded so it is not discovered at e2e.** D1
> STRICT and a union-merged 2-pass quorum push the SAME way: both make CLEAN harder to
> reach. Together they may make auto-accept fire so rarely that this plan ships the friction
> of a mandatory gate with none of the smoothing that was supposed to justify it. **This is
> measurable and Phase 5 MUST measure it** — see OQ-2's ratified anchor 4. It is an accepted
> risk with a named observation, not an oversight.



**The problem, stated exactly.** Plan 82's D5 could define clean as *"the solver was `sat`
and every subject resolved"* — a claim with a deterministic core. **Grill has no such
core** (fact 13): every finding is LLM output, filtered by a grounding gate (PHASE 3) and
a refutation pass (PHASE 4) that are themselves LLM work. Its only honest analog is *"no
finding survived cross-examination."*

**Two candidate definitions.**

- **(a) STRICT — nothing survived.** CLEAN when the PHASE-4 partition's `confirmed`,
  `contested` and `uncertain` buckets are ALL empty. `dismissed` may be non-empty — a
  dismissed finding is precisely one that did NOT survive.
- **(b) RECOMMENDATION-BASED.** CLEAN when the PHASE-5 disposition is `PROCEED`.

**RECOMMENDATION: (a), and fact 8 is why the fork is real rather than academic.** PROCEED
is reachable in two ways today, and only one of them means "nothing survived": the
empty-`validated.json` branch, and PHASE 5's *"all-accepted-as-risk"* branch, where
findings survived refutation and the orchestrator judged none of them plan-destroying.
**Under (b), a run with confirmed findings that the classifier deemed non-fatal would
auto-accept and the human would never see them** — the exact opposite of what a report
with a headline is for. (a) auto-accepts only when there is literally nothing for a human
to look at, which is the same bar plan 82's D5 sets with its zero-unresolved-subjects
clause.

**Why `uncertain` is in the blocking set.** An `uncertain` finding is one the refuter
could not resolve (fact 7). It was not confirmed, but it was not dismissed either — it did
not survive refutation so much as refutation failed to reach it. Under a rule whose whole
content is *"no finding survived cross-examination,"* an unresolved finding is a survivor.

*Counter-argument, recorded:* (a) re-interrupts the human for minor findings, adding back
exactly the friction mandatory-plus-auto-accept was supposed to smooth, and the
`uncertain` clause makes a refuter's indecision cost the user a turn. **Accepted.** The
human-owns-the-verdict principle is PHASE 7's own title (fact 6), and it bends only where
the report is empty. A ratifier who wants the friction lower should pick the intermediate
position deliberately — CLEAN = `confirmed` empty AND `contested` empty, with `uncertain`
tolerated — and record it as a third option rather than letting it arrive by drift.

*Second counter, recorded:* the predicate reads `partition.json`, which PHASE 3's
empty-findings branch writes BY HAND (`printf` of a four-empty-bucket literal, fact 8's
first anchor). So the clean predicate is evaluated over a file the orchestrator sometimes
authors itself. That is fine — the hand-written literal is exactly the all-empty case —
but a build session must not "simplify" by having the predicate re-derive from
`validated.json`, because the two paths converge on `partition.json` and nothing else.

### D2 — The honest bound: auto-accept certifies THIS RUN, not the plan *(RATIFIED 2026-08-25 — a quorum IS built, DIVERGING from the recommendation below)*

> **RATIFIED 2026-08-25 — grill v1 GETS a fixed 2-pass quorum. The recommendation below
> (no quorum) is OVERRIDDEN by maintainer decision.**
>
> **The mechanism is `/devforge:audit`'s, NOT `/devforge:spec-check`'s, and confusing the two
> would invert the purpose.** The decision was taken as "like spec-check"; checking the two
> mechanisms showed the analogy points at the wrong one, and the correction is recorded here
> because a future session reading "quorum" would otherwise build the wrong rule:
>
> | | spec-check (its D13) | audit `--passes` (plan 12) |
> |---|---|---|
> | rule | **majority** — a contradiction is CONFIRMED only when the same conflicting set reproduces across a majority of passes | **union** — every pass's findings are merged into one working list |
> | effect | FEWER findings, MORE clean verdicts | MORE findings, WIDER recall |
> | purpose | reproducibility of a soft English→logic FORMALIZATION | catching what a single pass missed |
>
> **spec-check's quorum has no grill analog because grill has no formalization step** — its
> quorum exists to stabilize a translation, and there is no translation here.
>
> **And majority would work AGAINST the reason for adding a quorum at all.** The strongest
> recorded objection to this whole plan is that an auto-accepted clean verdict reads as an
> endorsement. The cure for that is making CLEAN HARD to reach. A majority rule SUPPRESSES a
> finding that appeared in only one pass, making clean verdicts MORE common and the
> endorsement problem WORSE.
>
> **Ratified shape: 2 adversary passes → UNION the findings → ONE refutation pass over the
> union.** Union widens recall; refutation suppresses false positives. They are
> complementary and this exact composition already ships (plan 12's union merge feeding plan
> 19's refutation stage in `/devforge:audit`). **One refutation pass, not two** — refuting
> each pass separately triples the cost instead of doubling it and produces two partitions
> nothing reconciles.
>
> **What this buys and what it does not.** It raises detection power and directly weakens
> the endorsement objection, which the no-quorum recommendation below could only mitigate
> with copy discipline. It does NOT make the verdict deterministic — two passes are still
> two samples.
>
> **The copy rule below SURVIVES UNCHANGED and is not softened by the quorum.** The clean arm
> says *"the adversary found nothing that survived cross-examination."* It must NEVER say the
> plan is sound, proven, or validated. Two passes do not license a stronger claim than one.
>
> **Cost, stated where it compounds:** this doubles the adversary half of a command whose
> wall-clock is unmeasured, and D7 was ratified the same day as "accept the cost, measure at
> e2e". **The two decisions compound, and the number Phase 5 records is now the number for
> the 2-pass shape** — there will be no separate single-pass baseline.



**Grill has no D13-style quorum (fact 13).** One adversary, one pass. Run-to-run variance
means a second run may find what this one missed, and nothing in the design bounds that.

**This is equally true of today's opt-in PROCEED** — so making the run mandatory changes
EXPOSURE (every feature now gets one adversarial pass instead of the ones a human
remembered to grill) and does not change DETECTION POWER (one pass is still one pass).
Say that plainly; it is the whole honest claim.

**RECOMMENDATION: NO quorum mechanism for grill v1.** Two reasons, and the second is the
weaker one:

- The refutation pass is already this command's false-positive suppressor, and it is the
  mechanism plan 19's cry-wolf stance produced. A quorum would suppress a different error
  class (single-run misses), not the one the design is tuned against.
- Doubling an already-expensive fan-out is precisely the cost problem D7 records, on a
  command for which no wall-clock number exists (fact 26).

**The second reason is a cost call, not an argument that quorum would not help.** Record
it as such — a future session that finds the mandatory gate is missing real defects has a
named, un-refuted lever to pull.

**What the user-facing copy must say, and must not.** The clean arm says *"the adversary
found nothing that survived cross-examination."* It must never say the plan is sound,
proven, or validated. This is the same under-promise discipline plan 62's D11 imposes on
spec-check, applied to a command with strictly weaker grounds.

*Counter-argument, recorded:* an auto-accepted clean verdict is, in practice, read as an
endorsement no matter how the sentence is worded, and a gate that produces such a reading
on one stochastic pass may be worse than no gate — a human who skipped grill knows the
design is unattacked, whereas one who saw a clean auto-accept believes it was attacked and
held. **This is the strongest objection to the whole plan and it is not resolved here.**
The defence is that a mandatory single pass strictly dominates an optional zero passes on
detection, and that the copy rule above is the only mitigation available without a quorum.

### D3 — Gate seat: a `/devforge:breakdown` entry-side fail-closed preflight (NEW) *(RATIFIED 2026-08-24 — DIVERGING from the recommendation below)*

> **RATIFIED 2026-08-24. The recommendation below is REJECTED in its predicate and KEPT in
> its seat.** The gate still sits entry-side at `/devforge:breakdown` as a new
> `breakdown_helper` verb modelled on `plan_helper verify-spec-check`. What changes is
> WHAT IT CHECKS.
>
> **The ratified predicate:**
>
> > **The gate accepts a `grill.md` whose RECORDED ADVERSARY STATUS is `complete` or
> > `clean`. Nothing else. It never reads the disposition, and it never reads freshness.**
>
> **ONE mandatory grill run per feature. Re-runs are NEVER forced.**
>
> **Why the drafted predicate was rejected — this is the load-bearing reason and it is not
> a cost argument.** D3's own text spells the trap out: *"a human who acts on it rewrites
> `plan.md`, which invalidates the report under D4's predicate and re-blocks the gate until
> grill re-runs."* Follow the incentive that creates. **Ignore a REVISE-PLAN finding and you
> proceed immediately — the report is still fresh. Act on it and you pay another full
> adversary + refuter fan-out.** The design charges the operator for taking grill seriously,
> and it charges an unbounded number of times, because each revision re-invalidates. **A
> gate that penalizes acting on its own findings is worse than no gate**: it does not merely
> cost wall-clock, it teaches the operator to dismiss the report. This was found by the
> maintainer at ratification, not by the drafting pass, and no phase may re-introduce a
> freshness CONDITION without answering it.
>
> **The principled asymmetry with plan 82's gate, stated so nobody "harmonizes" the two.**
> `/devforge:spec-check` HAS a cheap deterministic core — a hash comparison plus a Z3 run —
> so forcing freshness there is cheap and honest. `/devforge:grill` has **no cheap core at
> all**: it is a full adversary dispatch plus a refuter fan-out, single-pass and stochastic
> (fact 13 — no quorum exists). **Enforcing freshness on a cheap check is fine; enforcing it
> on an expensive stochastic one IS the loop.** The two gates differ because the two steps
> differ in kind, not because one of them was under-designed.
>
> **Why a FAILED run must not satisfy the gate — ratified explicitly, against this plan's
> own earlier suggestion.** D3's counter-argument below proposed that a grill run failing
> for mechanical reasons still writes a report and that the report satisfies the gate
> ("the check RAN"). **REJECTED 2026-08-24.** "grill could not run, here is a report saying
> so" is an escape hatch wearing an artifact's clothes — it satisfies a mandatory gate
> without any adversarial review having happened. The distinction is already MECHANICAL and
> needs nothing invented: `consume-tmp` returns `status` ∈ (`complete` / `clean` / `failed` /
> `missing`) (`src/commands/grill/main.md`, PHASE 3). **`clean` COUNTS** — an adversary that
> ran and grounded no attack is a successful adversarial pass, and PHASE 3 already routes it
> to PROCEED. **`failed` / `missing` DO NOT COUNT** — the dispatch produced no usable output.
> The report is still written (it is useful to the human), it simply does not satisfy the
> gate.
>
> **Build consequence:** `consume-tmp` computes that status today but **nothing persists
> it**. PHASE 6 must record it — `grill-state.json` is the free carrier D4 already picked
> (fact 12) — and the new `breakdown_helper` verb reads it. That is the whole mechanism.
>
> **The absent-adversary case needed no decision and is recorded so nobody re-opens it.**
> PHASE 2.1 already ends the turn BEFORE any artifact exists when
> `.claude/agents/devils-advocate.md` is missing (*"there is no graceful-degradation
> fallback; the adversary IS the command"*). No `grill.md` is written, so the gate correctly
> keeps blocking, there is no escape hatch, and the user gets a NAMED remedy. That is a
> precondition failure with an instruction, not a cliff — the same shape
> `/devforge:audit`'s exit-3 already ships.
>
> **What is deliberately NOT built:** no retry of a failed adversary dispatch. It is a real
> improvement and it is SEPARABLE; revive it if a transient dispatch failure is OBSERVED
> more than once in practice.
>
> **## Discharged precondition (2026-08-24) — the named remedy was WRONG, corpus-wide.**
> Making grill mandatory turns PHASE 2.1's remedy into the operator's only exit, so it was
> verified rather than trusted, and it did not hold. `update.sh` restores an agent only in
> the **NEW** quadrant (in the roster, ABSENT from the snapshot). An agent that WAS installed
> and was later deleted falls through all three of its branches — the three-way merge touches
> only agents present in both snapshot and target, `NEW_AGENTS` skips it (it IS in the
> snapshot), `REMOVED_AGENTS` skips it (it IS in the roster) — and `update.sh`'s own comment
> confirms the skip is deliberate. Plan 72's `FORCE` repair does not cover it either; that
> is scoped to missing `.devforge/lib` helpers. **The advice sent the user in a circle:
> `update.sh` runs, reports success, the agent is still missing.** The claim appeared at
> FIVE sites — `grill/main.md`, `audit/main.md`, and three in `review/main.md` — and all five
> were corrected in the same session (`fix/main.md` already carried the honest *"or
> hand-fix"* form and was left alone). **A `RESTORE` branch in `update.sh` was considered and
> DECLINED as disproportionate** for this repo's install population (a few local v2 installs,
> never shipped at scale). **Revival trigger: if v2 ever ships to installs the maintainer
> does not control, build the RESTORE branch** — a hand-fix instruction does not survive
> contact with an operator who has no framework checkout.
>
> **Still OPEN at this decision:** the verb's name, its exact sub-phase seat between PHASE 0a
> and PHASE 0b, and its stderr shape. Those are Phase-2 authoring choices, all modelled on
> `plan_helper verify-spec-check`.



**RECOMMENDATION: consumer-side, at `/devforge:breakdown`'s entry.** The gate belongs to
the stage protected from a bad design — which is how every other handoff gate in this
pipeline sits, and which is the same reasoning behind plan 82's D5(a) and its cited
`specify_helper find-handoffs --require` precedent (fact 19).

**The spine sentence, and it is the one a future session will over-generalize:**

> **The gate checks PRESENCE + FRESHNESS of `specs/<dir>/grill.md`. It NEVER reads the
> verdict. What becomes mandatory is that the grill RAN against the current plan — never
> that its disposition binds.**

A `REVISE-PLAN` report does not itself block `/devforge:breakdown`; the human owns that
call at PHASE 7 (fact 6), and a human who acts on it rewrites `plan.md`, which invalidates
the report under D4's predicate and re-blocks the gate until grill re-runs. **A gate that
read the disposition would be a blocking gate on a single stochastic LLM pass** — which is
the design plan 62's D14 refused for spec-check, on grounds that apply with MORE force
here, because grill has no prover at all.

**Mechanism — a new `breakdown_helper` verb, not prose.** Fact 15 is why: breakdown's only
entry-side guard today is prose, and prose guards are the disease plans 38/41/42 closed
with mechanical verbs. Breakdown already owns a `verify-*` gate family (fact 16), so the
verb has an established naming and exit convention to follow — exit 2, a stdout findings
block or a stderr BLOCKED message the command copies VERBATIM, no override flag.

**AMENDED 2026-08-23 — the exact gate this seat needs now EXISTS one command upstream, and
it is the PRIMARY model.** Plan 82 shipped `plan_helper verify-spec-check` plus
`/devforge:plan`'s `## PHASE 0a.8: Spec-check gate (mandatory)` block on 2026-08-19
(verified live: `src/devforge/lib/plan_helper.py:2758` registers the verb,
`src/commands/plan/main.md:117`–`:136` is the block). **Every shape decision below is
already made there, in this pipeline, by a ratified plan:** the verb is **read-only** — it
*"never flips a `**Status**:` line and never writes a file"* (`plan/main.md:127`); exit 0
prints a JSON ack the command surfaces in one line; exit 2 is BLOCKED and the command
copies the helper's stderr **VERBATIM as a fenced code block, then ends the turn** (`:130`);
there is **no override flag and no skip arm**, stated as a standing prohibition (`:134`);
the blocked message **names the command for the USER to type** rather than running it
(`:132`); and the gate sits **before the Draft → Approved flip** on the stated ground that
*"a spec that cannot be planned must not be flipped to Approved"* (`:136`) — the same
ordering argument as cost 2 below, one stage earlier. **Phase 2 models the grill verb and
its block on that pair.** Fact 19's `specify_helper find-handoffs --require` remains cited
as the OLDER precedent for the no-override stance; it is no longer the closest one.

**Two costs that must be visible at ratification:**

1. **It is the first ENTRY-side mechanical gate in `/devforge:breakdown` (fact 18).** The
   six existing `verify-*` verbs all run at PHASE 3.5, after decomposition. A build
   session that assumes it is extending an existing preflight will find there is none.
2. **Seat placement is a real decision, not a detail.** The gate must fire before
   `/devforge:breakdown` does expensive work AND before PHASE 0b flips `plan.md`'s
   `**Status**:` to Approved — **a plan that cannot be decomposed must not be marked
   Approved.** That puts it after PHASE 0a's resolution (which is where the plan path
   first exists) and before PHASE 0b. Phase 2 owns the exact sub-phase label.

*Counter-argument, recorded:* a fail-closed preflight blocks a pipeline stage on an
artifact produced by a stochastic, expensive step. If a grill run cannot complete — the
adversary agent absent, the CBM graph unavailable, a refuter dispatch failing — the user
cannot break down at all. **Phase 0 must decide whether that state has an escape, and the
zero-escape-hatch policy makes `--skip-grill` the wrong answer.** Recommended framing,
symmetric with plan 82's: a grill run that produces no findings for mechanical reasons
still WRITES A REPORT recording that fact (PHASE 3's `status: failed` / `missing` path
already feeds the report per `src/commands/grill/main.md:185`), and that report satisfies
the gate — the check RAN. **Record the decision either way**; leaving it implicit is how a
first-run cliff ships.

### D4 — Staleness predicate: same PREDICATE as plan 82's OQ-2, different CARRIER *(RATIFIED 2026-08-24 — recorded, NOT enforced)*

> **RATIFIED 2026-08-24. The content hash is CONFIRMED and plan 82's OQ-2 is named here, so
> the reciprocal-naming debt that plan owes is DISCHARGED.** The carrier is
> `grill-state.json`, as recommended.
>
> **What changed: the hash is RECORDED, never ENFORCED.** Under D3's ratified predicate the
> gate does not read freshness at all, so the hash stops being a gate CONDITION and becomes
> a VISIBILITY field: `grill.md` (and its `grill-state.json` sibling) record the hash of the
> `plan.md` the run actually saw, and any reader — human or downstream command — can tell a
> report about the current plan from a report about a superseded one.
>
> **This is plan 86's D3 shape, applied one command over: the claim is VISIBILITY, not
> enforcement.** A stale report satisfies the gate; it does not hide that it is stale.
>
> **The predicate is still IDENTICAL to plan 82's** — sha256 over the artifact's raw bytes,
> recorded at render time — so the two plans do not disagree about what "stale" means. They
> disagree about what to DO about it, and that difference is D3's principled asymmetry
> (cheap deterministic core vs none), not a drift in definition.
>
> **Consequence for the three-conjunct predicate below: conjuncts that exist only to BLOCK
> are out of scope.** What survives is the recording. Phase 1 stands entirely on its own
> under this ratification — a freshness-stamped report is useful with or without any gate,
> which is exactly the separability note in `## What is actually being added`.



**Plan 82's OQ-2 recommends a content hash of the upstream artifact recorded in the report
at render time and re-hashed by the gate, over mtime — because mtime is fragile across
checkouts, clones and branch switches, and this repo already distrusts mtime-adjacent
signals.** That reasoning is general and applies here unchanged.

**RECOMMENDATION — the predicate is identical, and Phase 0 must ratify BOTH plans to the
same one.** Divergence in the PREDICATE (one plan hashing, the other stat-ing) would mean
two gates in one pipeline disagreeing about what "stale" means, which is itself the
defect. Name plan 82's OQ-2 in the ratification record.

**AMENDED 2026-08-23 — plan 82's OQ-2 is RATIFIED and SHIPPED, so the predicate is no
longer an open fork on this side.** It closed 2026-08-19 on the **content hash**, exactly
as recommended above, and the built form is live and greppable: `spec-check.md` carries a
`**Spec hash**: <sha256-hex>` header line written at render time
(`src/devforge/lib/_spec_check/_report.py:557`), and `plan_helper verify-spec-check`
re-hashes the current `spec.md` — *"sha256 over the file's raw bytes"* — and compares
(`src/commands/plan/main.md:127`). **Plan 82's own records state the two plans ratify
identically, in its words: the CARRIER differs, the PREDICATE does not — and that plan 85's
Phase 0 owes the RECIPROCAL NAMING.** So D4's decision space has collapsed from "pick a
predicate" to two obligations: **confirm the content hash, and name plan 82's OQ-2 in the
ratification record.** **Diverging now would not be a fresh fork — it would break an
identity one plan has already ratified and shipped**, which is precisely the two-gates-
disagreeing-about-stale defect the paragraph above names. A ratifier who still wants mtime
is overturning plan 82's OQ-2, not answering plan 85's D4, and owes that argument to both
files. **Everything below this note is unaffected: the CARRIER fork was never shared** —
grill's `grill-state.json` is a free sibling and stays the recommendation, and the
three-conjunct predicate with its conjunct-2 addition is untouched.

**The CARRIER differs, and this is a deliberate, argued divergence rather than drift.**
Plan 82's OQ-2 records a counter to its own recommendation — that a hash inside rendered
markdown couples two commands through a document — and offers a sibling JSON stamp as a
third option at the cost of a new artifact plus a `storage-rules.md` row. **Grill does not
pay that cost, because the sibling JSON already exists**: `specs/[feature]/grill-state.json`
is helper-owned, per-feature, and already committed by PHASE 6's artifact commit (fact 12).
So for grill the sibling-JSON option is strictly free, and the markdown-coupling counter
does not have to be accepted.

**The gate's full predicate, three conjuncts:**

1. `specs/<dir>/grill.md` exists;
2. `specs/<dir>/grill-state.json` records the run as complete — PHASE 6 already advances
   it with `check-status-and-flip --to report --status complete` (fact 11), so an
   interrupted grill is distinguishable from a finished one;
3. the `plan.md` content hash recorded at render equals the current `plan.md` hash.

**Conjunct 2 has no spec-check analog and is an ADDITION to the shared predicate, not a
divergence from it** — the shared core is conjunct 3. Say so in the ratification record so
a future session comparing the two gates does not read conjunct 2 as inconsistency.

**Build-shaping note, so Phase 1 does not discover it late.** PHASE 6's order is
`render-report` → `commit-artifacts` → `check-status-and-flip --status complete` (fact 11).
**The artifact commit happens BEFORE the final state flip**, so a stamp written by that
final flip would not be in the committed `grill-state.json`. The stamp must therefore be
written at or before `render-report`, or by a dedicated verb called before
`commit-artifacts`. **Which of those it is, is a build decision for the python-engineer
loop** — recorded here as a known fork rather than pre-decided.

*Counter-argument, recorded:* a hash makes the gate fire on any `plan.md` edit at all,
including a typo fix in a prose paragraph the grill never depended on. That is strictly
more conservative than the user needs, and it converts a one-character correction into a
full re-grill. The defence is that "which parts of `plan.md` the adversary depended on" is
not computable — the adversary reads the whole file plus a blast radius it resolves itself
(fact 6) — so any narrower predicate would be a guess presented as a check. **Plan 48's
OQ-1 (fact 21) reached the same conclusion from the other direction and deferred it as
genuinely harder than a presence check; this plan pays that cost rather than deferring it,
and the ratifier should confirm that trade explicitly.**

### D5 — Auto-accept wiring in `main.md` *(RATIFIED 2026-08-25 — as recommended)*

> **RATIFIED 2026-08-25, all three parts as recommended: PHASE 7 is ENTERED and its HUMAN
> GATE does not fire; the phase opens with a leading clause naming the clean arm; the CLEAN
> predicate is exposed by the helper, not re-derived in prose.**
>
> **Fact 10 decides the first part and it is not a style call.** PHASE 7 owns the ONLY
> `rm -rf "$WORKDIR"` sweep, and `$WORKDIR` is a FIXED literal cleared at the START of the
> next run — so "skip PHASE 7 on clean" would strand scratch **silently**, persisting
> between runs rather than accumulating visibly. Entering the phase with its gate dormant
> satisfies plan 39 (no arm entered ⇒ no seed) and Rule 10 (sweep last, exactly once)
> simultaneously; skipping cannot satisfy both.
>
> **The leading-clause requirement is load-bearing, not editorial.** PHASE 7's arms are
> enumerated over the user's PICK, and on the clean path no pick exists — so the arm where
> no pick is bound must be named FIRST or the phase tests an unbound variable. Plan 82's
> Phase 4 records the identical lesson for spec-check's PHASE 6; grill has the same defect
> in waiting plus the scratch sweep as an extra consequence.
>
> **Helper-exposed predicate, per the recommendation:** this predicate decides whether a
> human is consulted, and a prose-derived branch on a value the orchestrator computes itself
> is the softest possible form of that decision.
>
> **Amended by D2's ratified quorum:** the predicate is evaluated over the partition
> produced from the UNION of both passes — one partition, not two. Nothing about D1's
> three-bucket test changes; only its input is now the merged working list.



**Non-clean (per D1) — unchanged.** Any surviving finding, or any recommendation other
than PROCEED including KILL, and PHASE 7 fires exactly as it does today: the four-way
`AskUserQuestion`, the matching-arm seed write, the bounded re-entry loop.

**Clean — the human gate does not fire.** PHASE 6 still renders `grill.md`, still
WIP-commits `grill.md` + `grill-state.json`, still flips the state to complete (plan 37's
per-command artifact discipline; fact 11 shows that block is already unconditional). No
`AskUserQuestion`. No pick captured. No seed — and no seed is exactly right, because the
seed is written only inside a matching re-entry arm (fact 9, plan 39's rule) and on the
clean arm no arm is entered.

**⚠ DIVERGENCE FROM THE COMMISSIONING BRIEF, surfaced as a ratification item.** The brief
specified that on the clean arm *"PHASE 7 is SKIPPED entirely."* **Fact 10 falsifies that
as written:** PHASE 7 also owns the single `rm -rf "$WORKDIR"` scratch sweep, and Rule 10
states the sweep happens there and nowhere else. **Skipping PHASE 7 outright would strand
`$WORKDIR` on every clean run** — and because `$WORKDIR` is a FIXED literal
(`${TMPDIR:-/tmp}/forge-grill`) cleared at the START of the next run, the stranded scratch
would silently persist between runs rather than accumulate visibly.

**RECOMMENDED SHAPE: PHASE 7 is ENTERED; its HUMAN GATE does not fire.** The phase opens
with a leading clause naming the clean case — *clean → present the no-findings result,
write NO seed, sweep the scratch, end* — and the existing four-option gate and its arms sit
below that clause, reached only on the non-clean path. This preserves plan 39 (no arm
entered ⇒ no seed) and Rule 10 (cleanup last, exactly once) simultaneously, which
"skip the phase" cannot.

**The leading-clause requirement is the same lesson plan 82's Phase 4 records for
spec-check's PHASE 6**: a phase whose logic branches on *the user's pick* must first name
the arm where **no pick exists**, or it tests a variable the clean path never binds.
Grill's PHASE 7 has the same defect in waiting — its arms are enumerated over picks — with
the scratch sweep as an extra consequence spec-check did not have.

**Where the clean predicate is evaluated.** PHASE 5 already reads `partition.json` in
prose to classify. **RECOMMENDATION: expose the predicate from the helper** rather than
having the orchestrator re-derive a four-bucket emptiness test in prose — the
helper-owns-shape principle, and symmetric with plan 82's Phase 3, which exposes its clean
predicate *"so the command can branch on it rather than re-deriving it in prose."*

*Counter-argument, recorded:* a helper-exposed predicate is a new verb (or a new field on
an existing verb's stdout) for a test a competent orchestrator can perform by reading four
arrays. The defence is that this predicate DECIDES whether a human is consulted, and a
prose-derived branch on a value the orchestrator computes itself is the softest possible
form of that decision.

### D6 — The Rule-1 reversal is a formal amendment, lighter than plan 82's D14 reversal *(RATIFIED 2026-08-25 — keep the flag; amendment NARROWS)*

> **RATIFIED 2026-08-25 — `disable-model-invocation: true` STAYS on `/devforge:grill`, and
> the Rule-1 amendment NARROWS rather than deletes.** Plan 63's 13/7 carve-out is therefore
> NOT reopened, no description trim is owed, and this plan contributes NO count delta —
> exactly the shape plan 82 ratified at its D5(a-ii) and shipped.
>
> **The preserved list below ships IN the amendment**, so no future session reads the
> reversal as broader than it is: the USER still owns every non-clean verdict at PHASE 7;
> all four dispositions survive, KILL included; the cross-pick and Dismiss-analog arms are
> unchanged; grill still never modifies `plan.md` or `spec.md`. What becomes mandatory is
> that the grill RAN — and, per D3's ratified predicate, that it ran to a `complete` or
> `clean` adversary status.
>
> **The `src/CLAUDE.md` bracket legend is a DELETE, not an edit** — the sweep list's most
> easily-missed item. Plan 82 de-bracketed `/devforge:spec-check`, so `[/devforge:grill]` is
> the LAST bracketed step in the chain; de-bracketing it leaves ZERO, and the legend then
> describes notation the file no longer uses. **Retire the line; do not reword it.**
>
> **Wording model, ratified: plan 82's `#### /devforge:spec-check` catalog entry.** It
> already renders D3's spine and OQ-1's hand-off in consumer-facing prose. Follow it; do not
> invent a second phrasing for the same idea one entry away.
>
> **(AMENDED 2026-09-03 — plan 93.)** The flag clause is REVERSED:
> `disable-model-invocation: true` no longer sits on `/devforge:grill`; the counts are 16/4;
> a description trim WAS owed and was done by plan 93 Phase 1, replacing the frontmatter
> closing sentence this plan wrote (*"Human-typed only — `/devforge:breakdown` requires that
> it RAN, never that its disposition binds."*) with a ≈40-word description carrying the same
> RAN-not-binds clause. The listing-budget argument recorded under "One fact plan 82 did not
> record" is answered, not refuted: the skill NAME never evicts and the `/devforge:breakdown`
> gate names the command, so awareness is reliable and the description is a convenience.
> Everything else in D6 stands — the NARROWS list (the USER owns every non-clean verdict at
> PHASE 7, all four dispositions survive, cross-pick and re-entry unchanged, grill never edits
> `plan.md`/`spec.md`), the legend delete, the wording model — and a blocked
> `/devforge:breakdown` now OFFERS the grill and runs it on the user's yes, one agreement per
> command (plan 93 D2).



**What is being amended, and by what authority.** Unlike spec-check, **no ratified plan
decision forbids grill-mandatory.** Plan 62's D14 has no grill counterpart. What exists is:

- grill's own Rule 1 and its two body restatements (facts 3, 4) — command-level authoring,
  not a ratified decision record;
- the frontmatter flag (fact 1) and plan 63's keep-7 carve-out, whose stated REASON for
  keeping grill is a citation of the frontmatter `description`'s closing sentence
  (facts 2, 22) — so the carve-out's premise is what this plan changes, and the carve-out
  does not independently forbid it;
- plan 23's user-owns-the-verdict stance (`23-ADVERSARIAL-GRILLING-PLAN.md:18`).

**The amendment NARROWS; it does not delete.** After it, and this list must appear in the
amendment so no future session reads the reversal as broader than it is:

- the USER still owns every non-clean verdict at PHASE 7 — plan 23's stance is intact;
- all four dispositions survive, KILL included;
- the cross-pick and Dismiss-analog arms survive unchanged;
- `/devforge:grill` still never modifies `plan.md` or `spec.md` (Rule 8);
- what becomes mandatory is that the grill RAN against the current plan (D3's spine).

**Sweep list for Phase 4. This list is NOT certified exhaustive** — the phase opens with
`grep -rn "auto-gate\|Opt-in\|opt-in\|mandatory gate\|never gates" src/ *.md` and reconciles the result
against it; treat a hit not named here as an omission in this plan, not as a new defect.

- `src/commands/grill/main.md` — Rule 1 (fact 3), the two body restatements (fact 4), the
  `description`'s closing *"Opt-in — never an auto-gate."* (fact 2), and — under D6's
  model-invocability arm only — `disable-model-invocation: true` (fact 1).
- `src/CLAUDE.md` — **refreshed 2026-08-23 against the live file; plan 82 changed what four
  of these edits mean.** Each surface below was re-verified this session.
  - **The chain step `[/devforge:grill]` (`:44`) — and the bracket legend is now a DELETE,
    not an edit.** Plan 82 de-bracketed `/devforge:spec-check` in that same chain, so
    **grill is the ONLY bracketed step left in it.** De-bracketing grill therefore leaves
    **ZERO** bracketed steps, and the legend *"`[bracketed]` steps are optional and opt-in
    — not mandatory gates"* (`:47`) becomes a sentence describing notation the file no
    longer uses. **RETIRE the legend line; do not reword it.** A Phase 4 that edits it in
    place ships a legend with no referent.
  - **The *"Seven are **human-typed only**"* sentence (`:49`)** — it now reads *"…the
    adversarial checks `/devforge:grill` (opt-in) and `/devforge:spec-check` (whose fresh
    report `/devforge:plan` requires)…"*. **The `(opt-in)` parenthetical is the target, and
    the spec-check clause beside it is the WORDING MODEL** — plan 82 kept the command in
    the seven and re-described the obligation rather than the invocation route, which is
    exactly the narrow reading D6 requires. **Under the recommended keep-the-flag arm the
    COUNT is not touched, only the parenthetical.**
  - **The *"Seven commands … are human-typed only"* sentence introducing `### Command
    Details` (`:79`)** — a bare enumeration with no opt-in claim about grill; **under the
    keep-the-flag arm it needs no edit at all.** Named here so Phase 4 records the no-op
    deliberately.
  - **The one-line catalog bullet (`:62`)** saying *"**Optional, opt-in** … not a mandatory
    gate"*, and **the `#### /devforge:grill` entry (`:99`–`:100`)**. **Plan 82's
    `#### /devforge:spec-check` entry (`:90`–`:91`) is the ratified wording TEMPLATE for
    both** — it carries *"that gate reads PRESENCE and FRESHNESS only, never the verdict"*
    and *"When it blocks, name `/devforge:spec-check` for the user to run — never run it
    yourself"*, which are D3's spine and OQ-1's shape already rendered in consumer-facing
    prose. **Follow it; do not invent a second phrasing for the same idea one entry away.**
  - **NEW, and absent from this list before 2026-08-23: the `## Enforced Quality Gates`
    Hard-Gates list (`:148`–).** Plan 82 added a row there — *"Fresh `/devforge:spec-check`
    report for the resolved spec → before `/devforge:plan` can run (a mechanical
    precondition, not an approval: presence + freshness of `spec-check.md` only — its
    verdict never gates)"* (`:152`) — sitting immediately above the pre-existing *"Plan
    approval → before `/devforge:breakdown` can run"* row (`:153`). **D3 owes the parallel
    grill row in that list**, and the spec-check row's parenthetical is the template.
    ⚠ **That row is also why Phase 4's opening grep now returns a `never gates` hit at
    `:152` that is TRUE and must NOT be edited** — it is plan 82's, about spec-check's
    verdict, not a stale grill claim.
- `src/commands/breakdown/main.md` — the `## Context in the Workflow` chain and the
  `## Outputs of this phase` framing, which currently describe a chain with no grill step
  in it at all (fact 14).
- **`src/commands/plan/main.md` — the PHASE-4 `stakes-hint` block's *"never gates
  `/devforge:breakdown`"* and *"`/devforge:grill` remains opt-in"* (fact 29, live at
  `:640`).** The first clause is falsified by D3 and MUST be rewritten; the hint's own
  behavior (advisory, non-blocking, always exit 0) is unchanged by this plan and its
  description must stay accurate. **This file is easy to miss because the gate lives in a
  different command** — it is named here so a build session does not have to rediscover it
  from the grep. **REFRESHED 2026-08-23: the PHASE-0a.7 no-seed branch is NO LONGER a
  target** — plan 83 rewrote it on 2026-08-20 and its live sentence (`:115`) makes a claim
  about seed `target_stage` routing, not about grill's invocation stance, which stays true
  under D3 (fact 29's amendment carries the reasoning). **A `grep -n "opt-in"
  src/commands/plan/main.md` run 2026-08-23 returns five hits, and only `:640` is grill's**
  — `:390`, `:396`, `:465` and `:563` are the constitution's Narrowing rule ("an opt-in the
  affected caller passes"), untouched by this plan.

- **NEW 2026-08-23, and the reason it is called out separately: these sites are INVISIBLE
  to Phase 4's opening grep.** None of them contains `auto-gate`, `Opt-in`, `opt-in`,
  `mandatory gate` or `never gates` — verified this session (`src/commands/fix/` returns
  **zero** hits for the whole alternation). They are pipeline CHAINS that enumerate the
  commands a user should run, and **under D3 every chain ending at `/devforge:breakdown`
  now omits a step that blocks it.** The four-command re-run cycle `/devforge:specify` →
  `/devforge:spec-check` → `/devforge:plan` → `/devforge:breakdown`, created by plan 83 on
  2026-08-20, appears at `src/commands/fix/main.md:134` and `:178` (the D7 scope-change
  bounce and its seed hand-off), at `src/commands/fix/references/triage.md:22`, and in
  `src/CLAUDE.md`'s `#### /devforge:fix` catalog entry (`:112`); a longer sibling chain
  running on to `/devforge:implement` → `/devforge:review` sits at
  `src/commands/fix/main.md:85`. **Same class, different command:**
  `src/commands/plan/main.md:25`'s `## Context in the Workflow` chain names ten commands
  and omits grill entirely. **Phase 4 decides per site whether it gains the grill step or a
  qualifying clause** — this plan does not pre-decide, because a re-run cycle that lists
  grill inline is longer to read while one that omits it now understates what the user must
  do. ⚠ **`src/CLAUDE.md`'s `/devforge:fix` workflow bullet (`:67`) is NOT in this class** —
  re-read 2026-08-23, it names `/devforge:specify` as the bounce target and enumerates no
  chain, so it needs no edit on these grounds.
- `23-ADVERSARIAL-GRILLING-PLAN.md` and its `PLAN-STATUS-ARCHIVE.md` entry — amend in
  place with the narrow reading, the same mechanism plan 62 used for its own D9.
- **Plan 82's three deliberately-expiring references** — its OQ-1 sentence
  (`82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md:638`, re-verified 2026-08-23), the
  mirrored clause in repo-root `CLAUDE.md`'s plan-82 index line, and the mirrored clause in
  that plan's `PLAN-STATUS-ARCHIVE.md` entry. **All three are still correct today and all
  three are this plan's responsibility to retire** — plan 82 wrote them as dated
  observations, not as claims about the future. **AMENDED 2026-08-23 — "they become false
  the moment this plan ships" OVER-CLAIMED, and the correction is arm-conditional.** Each
  reference is a compound of three clauses, which expire differently:
  - *"`src/commands/grill/main.md` still carries `disable-model-invocation: true`"* —
    **expires ONLY under the model-invocable arm. Under D6's RECOMMENDED keep-the-flag arm
    it stays TRUE after this plan ships**, and retiring it would introduce the falsehood,
    not remove one.
  - *"its Rule 1 still reads 'Opt-in, never an auto-gate … there is NO forced gate on every
    `/devforge:plan` run'"* — **expires under EVERY arm.** D6 rewrites Rule 1 outright
    (still live at `src/commands/grill/main.md:391`).
  - *"a repo-wide grep for grill near `mandator` returns ONE hit: `src/CLAUDE.md`'s bullet
    saying 'not a mandatory gate'"* — **expires under EVERY arm**, because that bullet
    (`src/CLAUDE.md:62`) is itself in this sweep list.

  **So Phase 4 retires the second and third clauses unconditionally and touches the first
  only if the model-invocable arm was picked.** Treating the three references as
  all-or-nothing is how a true sentence gets deleted for symmetry.
- `63-SKILL-COLLISION-SUPPRESSION-PLAN.md`'s OQ-2 keep-7 enumeration (fact 22) and OQ-1
  description budget (fact 23) — **under the model-invocable arm only.**
- **`scripts/emitters/claude.py` — verified NOT a target (fact 24).** The emitter never
  touches the flag. Recording this so a build session does not go looking.

**⚠ An INHERITED coordination debt, discharged 2026-08-23 as a verified NO-OP.** Repo-root
`CLAUDE.md`'s plan-83 entry carries a standing rule: *"whichever of plans 83 and 85 ships
SECOND reads the LIVE `specify/main.md:154`-area opt-in sentence and re-derives its rewrite
from what it finds — never a pre-computed one."* **Plan 83 shipped first (2026-08-20), so
this plan owes that read, and the read was performed 2026-08-23.** What it found: plan 83's
own rewrite had already stripped every grill and opt-in claim out of that sentence. The
live text at `src/commands/specify/main.md:154` is

> When no `specs/<resolved-feature-dir>/*-seed.json` file matches `target_stage == "spec"`
> (the normal case — a producing command writes a seed only when the user picks, at that
> command's own human gate, the arm matching its recommended re-entry disposition, and most
> runs never reach one), this block is a no-op: proceed directly to Phase 1.

**That sentence stays TRUE under this plan, by construction rather than by luck.** D5's
clean arm fires no human gate AND writes no seed, so seeds still arrive only via a matching
pick at a gate that fired; and since the clean arm is the one this plan expects to be
common, *"most runs never reach one"* is if anything more true after the change. **The owed
rewrite therefore discharges as a NO-OP: nothing at `specify/main.md:154` is edited by this
plan.** ⚠ **Phase 4 must still re-confirm with a fresh live read at ship time** — that is
what the rule requires, and this note records a 2026-08-23 observation, not a permanent
finding. If a fourth plan has moved that sentence in between, re-derive from what is there.

**⚠ The plan-63 counts coordination rule, stated explicitly because two plans edit the same
numbers.** Plan 82's D5(a-i) would take the counts 13/7 → 14/6 for spec-check; this plan's
model-invocable arm would take them 13/7 → 14/6 for grill. **If both ship, the counts are
15/5.** The rule: **whichever plan ships SECOND reads the live count and updates it once,
rather than applying its own delta to a remembered number.** The counts live in repo-root
`CLAUDE.md`'s "Where to find what" emitter row and in the two `src/CLAUDE.md` sentences
above; neither is computed from anything, so both go stale silently.

**AMENDED 2026-08-23 — the 15/5 scenario is now COUNTERFACTUAL; the rule that produced it
is not.** Plan 82 ratified **D5(a-ii)**, which KEEPS `disable-model-invocation: true` on
`/devforge:spec-check`, so **that plan contributed NO count delta and did not reopen plan
63's carve-out.** The counts were re-verified live 2026-08-23 and are still **13/7** — the
*"Seven are **human-typed only**"* sentence (`src/CLAUDE.md:49`), the *"Seven commands …
are human-typed only"* sentence introducing `### Command Details` (`:79`), and repo-root
`CLAUDE.md`'s emitter row (`:106`, still reading *"13 commands model-invocable, 7
human-typed-only"* with grill and spec-check both in its seven-name list). **So the worst
case is 14/6, and only if THIS plan picks the model-invocable arm; under D6's recommended
keep-the-flag arm the counts do not move at all and no count edit is owed.** **The
read-live rule itself STANDS and is not weakened by this note** — it is what made the
scenario detectable rather than shipped, and a Phase 4 that applies a remembered delta to
13/7 will still be wrong the moment any third plan touches these numbers.

**AMENDED 2026-08-23 — plan 63's OQ-2 text is ALREADY amended, so Phase 4 edits amended
text, not the 2026-08-07 original.** Plan 82's Phase 6 appended a dated block on
2026-08-19 (`63-SKILL-COLLISION-SUPPRESSION-PLAN.md:238`, opening
*"**(AMENDED 2026-08-19 — the KEEP decision stands; one of its two quoted reasons no longer
holds.)**"*) which retires the **spec-check half** of the quoted two-command reason and
states in terms that **grill's half is untouched and still accurate**. This confirms the
second counter below rather than mooting it: the quoted reason is a shared sentence about
two commands, plan 82 replaced one half's REASON while keeping the DECISION, and this plan
owes the other half by the same mechanism. **Phase 4 must read that block live and append
to it — never re-derive an amendment against the un-amended paragraph, and never restate
plan 82's half.**

**RECOMMENDATION on the model-invocability arm itself: KEEP the flag (the a-ii analog).**
This diverges from what plan 82 records as its brief's recommendation for spec-check, and
the reason is specific to grill rather than a general preference:

- **The listing-budget fact above.** A description in the always-on listing is dropped
  first for the least-invoked skills, and grill is by construction among the least-invoked.
  The flip therefore buys unreliable awareness.
- **Grill ends in an interactive human gate.** A model-invoked grill would run a
  multi-agent fan-out and terminate in an `AskUserQuestion` inside another command's
  preflight. That is a different interaction shape from spec-check's, and nothing in this
  repo has exercised it.
- **Cost.** The flip drags a description trim to ≈40 words (fact 23) plus the plan-63
  carve-out reopening, for a command the user is being told to run anyway by a
  fail-closed gate that names it.

*Counter-argument, recorded and genuinely competitive:* keeping the flag makes every
blocked `/devforge:breakdown` a two-turn round trip through the user, which is friction on
the pipeline's central path — and OQ-1 turns on this. **"Mandatory" is satisfied either
way, because what becomes mandatory is that the check RAN, not who typed it.** Phase 0
must pick deliberately.

*Second counter, recorded:* plan 63's carve-out reason for grill is a QUOTATION of the
frontmatter `description`'s closing sentence this plan rewrites — the em-dash form
*"Opt-in — never an auto-gate."* (fact 2), NOT Rule 1's comma form (fact 3); plan 63's own
text says *"descriptions"* (fact 22). Once that description sentence no longer says
"never an auto-gate," the carve-out's stated reason is stale **whether or not the flag
moves** — so Phase 4 must amend plan 63's OQ-2 text under BOTH arms, and only the counts
are arm-conditional.

### D7 — The wall-clock cost line *(RATIFIED 2026-08-25 — accept the cost, e2e MUST record the number)*

> **RATIFIED 2026-08-25 — accept the full cost in v1; Phase 5's e2e is OBLIGATED to record
> measured wall-clock. The coherent alternative this decision names — decline D3+D5 until
> plan 70's Phase 2 produces a number, keeping only Phase 1 — was on the table and was
> DECLINED**, on the ground that plan 70's Phase 2 is itself deferred to post-release, so
> waiting is waiting without a defined end.
>
> **What D3's ratification changed, and it is why this bet is smaller than the one D7 was
> written against.** Under the rejected freshness predicate the per-feature cost was
> UNBOUNDED — every `plan.md` revision forced another full run — so an honest cost line would
> have had to be a distribution over an unknown number of revisions. It is now **exactly one
> run per feature**, so D7 needs a single measured number.
>
> **What D2's ratification changed in the other direction:** that one run is now a 2-pass
> adversary with a union merge, so the number Phase 5 records is for the 2-pass shape and
> **no single-pass baseline will exist**. The two decisions compound and both were taken the
> same day with that visible.
>
> **The revival lever is ROUTED, and this is the part that must not be lost:** if the measured
> cost proves unacceptable, the answer is profiling-driven optimization (plan 70's Phase 3,
> which opens from numbers only) — **NEVER gate dilution.** "The gate is slow" is precisely
> the argument that manufactures a carve-out when no other route is named, so the route is
> named here in advance.
>
> **The obligation this discharges:** plan 82's OQ-1 asserts in three tracked files that this
> plan's Phase 0 owes a wall-clock cost line. **This block is that line**, and its honest
> content is that the number does not exist yet and Phase 5 must produce it.
>
> **Both alternatives stay REJECTED for the reasons already recorded**: a reduced "mandatory
> profile" makes the choice between profiles an escape hatch by construction, and skipping
> refutation on mandatory runs removes the false-positive suppressor exactly where cry-wolf
> costs most — a concern D2's ratified union merge makes STRONGER, not weaker, since union
> widens the finding pool refutation has to filter.



> **NOTE 2026-08-24 — D3's ratification makes this obligation EASIER, not harder, and the
> reason is worth stating before anyone treats the missing number as a blocker.** Under the
> REJECTED fail-closed-on-freshness predicate the per-feature cost was UNBOUNDED — every
> `plan.md` revision re-invalidated the report and forced another full adversary + refuter
> fan-out, so the honest cost line would have had to be a distribution over an unknown
> number of revisions. **Under the ratified predicate the cost is exactly ONE grill run per
> feature, forever.** D7 therefore needs a single measured number, not a model of operator
> behaviour. The number still does not exist (fact 26 — plan 70's Phase 2 is deferred), and
> this plan still owes it.



**Plan 82's OQ-1 states, in the plan document and in both ledger files, that "that plan's
Phase 0 owes a wall-clock cost line (cf. plan 70)."** This is that line. If Phase 0 closes
without it, three tracked files carry a false claim about this plan.

**The cost, stated honestly.** Mandatory grill puts the full pipeline on every feature: one
`devils-advocate` dispatch with a three-ring blast-radius traversal and self-gated web
verification, a grounding-gate pass, a per-refuter cross-examination fan-out, and an
orchestrator classification pass (fact 6). **There is no cheap deterministic core to
absorb the common case** — unlike spec-check, where a Z3 call is the expensive step's
cheap half. **And no number exists:** plan 70 measured helper cold-start and built the
profiler, but its Phase 2 real-run diagnosis is deferred to post-release (fact 26), so
per-command wall-clock for `/devforge:grill` is unmeasured. What IS on record is that the
whole pre-implement chain runs ~2h **with grill optional** (fact 25).

**Alternatives considered and rejected:**

- **A reduced "mandatory profile"** (fewer refuters, a smaller Ring-1 cap, a lower finding
  cap). **REJECTED** — it doubles the spec surface into a full grill and a lite grill, and
  the choice between them becomes an escape hatch by construction: any run that feels
  expensive gets the lite profile.
- **Skipping refutation on mandatory runs.** **REJECTED** — refutation is the
  false-positive suppressor (plan 19's stance), and a gate that fires on every feature is
  exactly where cry-wolf costs the most. Removing it inverts the design.

**RECOMMENDATION: accept the full cost in v1, and make the e2e phase record wall-clock.**
If the measured cost proves unacceptable, **the revival lever is profiling-driven
optimization (plan 70's Phase 3, which opens from numbers only) — never gate dilution.**
Record that routing now, because "the gate is slow" is the argument that produces a
carve-out if no other route is named.

*Counter-argument, recorded:* accepting an unmeasured cost on the pipeline's central path
is exactly what plan 70 exists to stop, and this plan is proposing it on a maintainer
preference with no incident behind it (see `## Origin`). **A coherent Phase-0 answer is to
decline D3+D5 until plan 70's Phase 2 produces a per-command number for grill, keeping
only Phase 1.** That answer should be on the table, not treated as obstruction.

### D8 — Two mandatory adversarial stages now exist in sequence *(RATIFIED 2026-08-25 — independent, with plan 82's gate recorded as LIVE)*

> **RATIFIED 2026-08-25 — the two plans ratify and ship INDEPENDENTLY, and D8's own closing
> rule is hereby DISCHARGED: this plan was ratified with plan 82's gate already SHIPPED and
> LIVE** (`/devforge:plan` PHASE 0a.8, built 2026-08-19), not as a hypothetical.
>
> **The policy question was answered explicitly rather than by accumulation.** The pipeline
> now carries two mandatory adversarial stages, and they are NOT the same kind of thing: one
> is a hash comparison over an already-rendered report backed by a deterministic solver; the
> other is a bounded adversarial pass with no deterministic core. **The asymmetry in how they
> treat freshness is principled and is argued at D3** — it tracks whether the step has a
> cheap core, not whether one of them was under-designed.
>
> **Combined per-feature cost, recorded once so nobody meets it as a surprise:** plan 82's
> gate (negligible — a hash) plus ONE `/devforge:grill` run at D2's ratified 2-pass shape.
> Bounded, not open-ended.



> **NOTE 2026-08-24 — the policy question this decision names is now materially cheaper to
> answer, and the two gates are no longer the same KIND of thing.** After D3's ratification
> the chain costs a `/devforge:spec-check` gate that is a hash comparison over an
> already-rendered report, plus **exactly one** `/devforge:grill` run per feature. The
> asymmetry is PRINCIPLED and tracks a real property — spec-check has a cheap deterministic
> core, grill has none (fact 13) — so a ratifier deciding the pipeline policy is no longer
> weighing "two unbounded adversarial gates" but "one cheap always-fresh check plus one
> bounded adversarial pass". **D8's closing rule still binds**: this plan ratifies SECOND and
> its Phase 0 must record that it was ratified with plan 82's gate already live.



If plan 82 and this plan both ship, a feature pays a mandatory `/devforge:spec-check`
between `/devforge:specify` and `/devforge:plan`, and a mandatory `/devforge:grill`
between `/devforge:plan` and `/devforge:breakdown`.

**RECOMMENDATION: the two plans ratify and ship INDEPENDENTLY.** Neither gate references
the other, neither is a precondition for the other, and neither plan's phases touch the
other's command. The coupling is exactly two points, both already named:

- **the plan-63 counts** (D6's coordination rule), and
- **the staleness predicate** (D4 — same predicate, different carrier).

**Combined per-feature cost is the SUM, and it is recorded once here so nobody discovers
it as a surprise at e2e.** Neither plan's own cost line mentions the other's.

*Counter-argument, recorded:* two mandatory adversarial gates in a five-command
pre-implement chain is a policy decision about the pipeline, not two independent local
decisions — and ratifying them separately is how a policy gets made without anyone
deciding it. **The ratifier should decide the policy question once, explicitly**, and then
let the two plans execute independently. Whichever is ratified second should record that
it was ratified with the other's gate already known.

**AMENDED 2026-08-23 — the conditional is now settled, and the closing rule above BINDS
this plan.** Plan 82 ratified on 2026-08-19 and shipped its build the same day: the first
mandatory adversarial gate is **LIVE**, not hypothetical (`/devforge:plan`'s
`## PHASE 0a.8: Spec-check gate (mandatory)`, `src/commands/plan/main.md:117`). **This plan
therefore ratifies SECOND, so by D8's own closing sentence its Phase 0 MUST record that it
was ratified with plan 82's gate already known and shipped** — not as etiquette, but
because the policy question the counter-argument names can no longer be answered
independently: a ratifier is now deciding whether to add a second mandatory adversarial
stage to a chain that already has one, and the combined per-feature cost stops being a
projection and becomes an increment over a cost the pipeline is already paying.
**Everything else in D8 is unchanged** — the two gates still reference nothing of each
other, neither is a precondition for the other, and the two coupling points are still
exactly the plan-63 counts and the staleness predicate (both now resolved on plan 82's side;
see D6's and D4's notes). **D7's cost line is unaffected and still owed**: plan 82's gate is
a cheap presence-and-hash check on an already-rendered report, so it contributes nothing to
the grill number that still does not exist (fact 26).

---

## Open questions (Phase 0)

### OQ-1 — Does `/devforge:breakdown` auto-invoke `/devforge:grill`, or name it? *(RESOLVED 2026-08-25)*

*Resolved:* **NAME IT, never run it.** The blocked arm copies the helper's BLOCKED message
verbatim and names `/devforge:grill` as the required next step; this run is over, the user
runs grill, then re-invokes `/devforge:breakdown`.

This confirms the externally-constrained answer rather than re-deciding it: this OQ's own
text calls consistency with plan 82 *"a stated dependency, not a preference"*, and plan 82
ratified D5(a-ii) and shipped it. Picking auto-invoke would have been a deliberate override
of a stated dependency and owed an argument that two adversarial preconditions SHOULD hand
off differently. **The recorded counter is NOT withdrawn** — a named-not-run gate costs the
user a round trip — but the pipeline demonstrably already pays that cost one stage upstream,
which is evidence about its tolerability. It also composes with D6's ratified keep-the-flag:
a command that is not model-invocable cannot be auto-invoked anyway.



When the gate fails, `/devforge:breakdown` either runs `/devforge:grill` itself (possible
only under D6's model-invocable arm) or names it for the user to type.

**This mirrors plan 82's D5 a-i/a-ii sub-fork**, and the recommendation must stay
consistent with whatever shape plan 82 ratifies — **that consistency is a stated
dependency, not a preference.** Two commands blocking on adversarial preconditions with
opposite hand-off ergonomics would be a pipeline inconsistency a user feels immediately.

*Recommendation: name it (consistent with D6's keep-the-flag recommendation).* The blocked
arm copies the helper's BLOCKED message verbatim and names `/devforge:grill` as the
required next step, exactly as `specify_helper find-handoffs --require` does one lane over
(fact 19).

*Recorded, because it is the strongest argument for the other answer:* a named-not-run gate
makes the mandatory path slower than the optional path was, since the user must notice the
block, type the command, and then re-enter `/devforge:breakdown`.

**AMENDED 2026-08-23 — plan 82 has ratified its half, so by this OQ's OWN sentence the
answer is externally CONSTRAINED toward NAME IT, pending Phase 0 confirmation.** The
recommendation above was written as consistent-with-
whatever-plan-82-picks; plan 82 picked **D5(a-ii)** on 2026-08-19 and shipped it, and the
live block states the ergonomics in terms this OQ can adopt verbatim: *"`/devforge:spec-check`
is user-invoked: name it, never run it yourself. On the BLOCKED path this run is over — the
user runs `/devforge:spec-check`, then re-invokes `/devforge:plan`, which restarts at Phase
0a."* (`src/commands/plan/main.md:132`). **Because the paragraph above calls that
consistency *"a stated dependency, not a preference,"* picking auto-invoke here would now
be a deliberate override of a stated dependency and owes an argument that the two
adversarial preconditions SHOULD hand off differently — not merely a preference for fewer
turns.** The recorded counter (a named-not-run gate costs the user a round trip) is **NOT
withdrawn**; it is now a cost the pipeline demonstrably already pays one stage upstream,
which is evidence about its tolerability rather than a refutation of it. **Two consequences
worth stating so they are not rediscovered:** this also supplies D6's keep-the-flag
recommendation the consistency argument it previously lacked — plan 82 keeps
`disable-model-invocation: true` on a command whose fresh report is a hard precondition,
which is the exact shape D6 recommends for grill — and the *"mandatory is satisfied either
way, because what becomes mandatory is that the check RAN, not who typed it"* line under
D6 now has a shipped instance behind it. **This note determines nothing by itself: Phase 0
still records the pick.**

### OQ-2 — The e2e known-answer anchors *(RESOLVED 2026-08-25 — anchor 3 REPLACED, anchor 4 ADDED)*

*Resolved:* **four anchors, not three.** ⚠ **The original anchor 3 (staleness) is MOOT and
is REPLACED** — D3's ratified gate does not read freshness at all, so there is no freshness
conjunct left to fail. A build session that implements the old anchor 3 is testing a
mechanism this plan decided not to build.

The ratified set:

1. **Planted defect** — a `plan.md` carrying a disqualifying defect the adversary should
   ground MUST produce a surviving finding, MUST NOT auto-accept, and MUST fire PHASE 7.
   *Sub-question resolved as recommended:* use a defect class the adversary is KNOWN to
   catch, so this tests the GATE rather than the adversary — a failure caused by adversary
   variance would be uninterpretable.
2. **Clean** — a sound `plan.md` MUST auto-accept: report written, report committed,
   PHASE 7's human gate never fires, `$WORKDIR` swept, `/devforge:breakdown` proceeds.
3. **Failed adversary (REPLACES staleness)** — a run whose adversary status is `failed` or
   `missing` MUST NOT satisfy the gate, even though a report exists. This is D3's
   no-escape-hatch ratification made observable, and it is the anchor most likely to be
   skipped because a report IS present on disk.
4. **Stale-but-accepted, and the auto-accept RATE (NEW)** — a `grill.md` whose recorded
   plan hash no longer matches the current `plan.md` MUST still PASS the gate, and the
   staleness MUST be visible in the artifact. This pins D4's ratified
   visibility-not-enforcement stance, which nothing else observes. **In the same run,
   RECORD AS A NUMBER how often auto-accept actually fires** — D1's STRICT predicate and
   D2's union quorum both push CLEAN out of reach, and if auto-accept nearly never fires
   this plan shipped a mandatory gate's friction with none of its smoothing. That number is
   the only evidence that risk was ever checked.

**Also record wall-clock in the same run** — D7's ratified obligation, for the 2-pass shape.



Three cases whose correct outcome is known in advance, so Phase 5 is a regression anchor
rather than an exploratory run:

1. **The planted-defect case.** A `plan.md` carrying a disqualifying defect the adversary
   should ground **MUST** produce a surviving finding, **MUST NOT** auto-accept, and
   **MUST** fire PHASE 7.
2. **The clean case.** A sound `plan.md` **MUST** auto-accept: report written, report
   committed, PHASE 7's human gate never fires, `$WORKDIR` swept, `/devforge:breakdown`
   proceeds.
3. **The staleness case.** A `grill.md` produced and then invalidated by an edit to
   `plan.md` **MUST** fail the gate's freshness conjunct, and **MUST** pass again after a
   re-grill.

*Open sub-question:* whether case 1 needs a defect class the adversary is KNOWN to catch
(making it a test of the gate) or one it plausibly might miss (making it a test of the
adversary). **Recommend the former** — this plan changes when grill runs, not what it
finds, and a case-1 failure caused by adversary variance would be uninterpretable.

### OQ-3 — Does KILL need distinct gate handling? *(RESOLVED 2026-08-25 — OUT OF SCOPE)*

*Resolved:* **OUT OF SCOPE, on D3's spine rather than on convenience.** A gate that read
KILL would be a gate reading the verdict — the design D3 explicitly refuses, and the one
that would let a single stochastic pass halt a feature.

**The consequence is stated plainly rather than buried: under this plan a KILLed design does
NOT block `/devforge:breakdown`.** KILL routes through PHASE 7 to the human, who owns the
call. That is the accepted cost of a spine that never reads the verdict, and a ratifier who
finds it unacceptable is rejecting D3, not adjusting this question.



A KILL disposition arguably should block `/devforge:breakdown` harder than an absent report
does — the design was judged fatally flawed, yet under D3 the gate passes because
`grill.md` is present and fresh.

*Recommendation: OUT OF SCOPE, and the reason is D3's spine, not convenience.* KILL already
routes through PHASE 7 to the human, who owns the call. A gate that read KILL would be a
gate reading the verdict — the design D3 explicitly refuses, and the one that would let a
single stochastic pass halt a feature.

**State the consequence rather than burying it: under this plan a KILLed design does not
block `/devforge:breakdown`.** That is the accepted cost of a presence-and-freshness spine,
and a ratifier who finds it unacceptable is rejecting D3, not adjusting OQ-3.

---

## Phases

### Phase 0 — Ratification *(HARD stop; no `src/` edit)*

The maintainer resolves D1–D8 and OQ-1–OQ-3, recording under each the chosen option plus
one sentence of reason.

**Phase 0 MUST produce the D7 wall-clock cost line.** Three tracked files (plan 82's OQ-1,
repo-root `CLAUDE.md`'s plan-82 index line, and that plan's `PLAN-STATUS-ARCHIVE.md`
entry) assert this plan owes it; closing Phase 0 without it makes all three false.

Re-check facts 8, 10, 13, 14, 15, 16, 17 and 26 before ratifying — they are the cost and
scope argument, and each is checkable in under a minute.

**Verify:**

- `grep -n "^### D[1-8] " 85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md` returns eight lines and
  **none contains `(OPEN`** — the marker is `*(OPEN)*` on D2/D3/D4/D5/D6/D8 and qualified
  on D1 (`*(OPEN — the load-bearing decision)*`) and D7
  (`*(OPEN — obligatory; …)*`), so match the substring, not the exact token. Each
  heading's decision carries a recorded confirm-or-override.
- OQ-1, OQ-2 and OQ-3 each open with a `*Resolved:*` sentence.
- **The D7 cost line exists and names a number or states explicitly that none exists.**
- **The D1 pick names which buckets block auto-accept**, by bucket name. A bare "strict"
  does not determine the `uncertain` question.
- **The D6 pick is recorded together with the narrow reading** — mandatory means the grill
  RAN against the current plan, never that its disposition binds.
- **The D6 model-invocability arm is picked explicitly**, and the plan-63 counts
  coordination rule is acknowledged.
- **The separability decision is recorded** — whether a decline of D3+D5 keeps Phase 1.
- The status line at the top of this file names the ratification date.
- `git status` shows no `src/` file modified for this plan.

---

### Phase 1 — The freshness stamp + the clean predicate + the pass merge

> **RECONCILED 2026-08-25 — this phase's scope GREW and its purpose SHIFTED. The heading
> and the two original items below are kept; read this note first, because one of them is
> now used for something else.**
>
> **(a) The stamp is still built, but it is no longer a GATE INPUT.** D4 ratified the hash
> as RECORDED, NOT ENFORCED — the gate never reads freshness. The stamp is a VISIBILITY
> field. Build it exactly as described; just do not let anything downstream branch on it.
>
> **(b) NEW and REQUIRED — persist the adversary status.** D3's ratified predicate is
> `adversary_status ∈ {complete, clean}`. `consume-tmp` already COMPUTES that value
> (`status` ∈ `complete` / `clean` / `failed` / `missing`) and **nothing persists it today**.
> PHASE 6 must record it into `grill-state.json` beside the stamp. **Without this the
> Phase-2 gate has nothing to read** — it is the single load-bearing addition of the
> reconciliation.
>
> **(c) NEW — the 2-pass union merge (D2).** D2 was ratified AGAINST this plan's own
> recommendation, so no phase mentions it. Build a `_grill/` merge that unions two passes'
> validated findings into one working list, deduped. **Model it on `/devforge:audit`'s
> `merge-passes` (plan 12, `_audit/_merge.py`) for the union SHAPE only — do NOT reuse that
> module.** It clusters by file and computes CROSS-AGENT corroboration, and grill has ONE
> finder, so its cross-agent half is meaningless here. Grill's merge is purely cross-pass.
>
> **Extra Verify items for (b) and (c), in addition to the list below:**
>
> - A test asserts each of the four `consume-tmp` statuses round-trips into
>   `grill-state.json` and back — `complete` and `clean` distinctly, since the gate accepts
>   both and a merge of the two would hide the distinction the D3 ratification rests on.
> - A test asserts a state file written BEFORE this change (no status field) reads back as
>   NOT gate-satisfying rather than crashing or defaulting to satisfied. **Defaulting to
>   satisfied would be a silent escape hatch** in exactly the shape D3 refused.
> - A test asserts the merge is a UNION, not an intersection or a majority — a finding
>   present in exactly ONE pass MUST survive. This is the test that pins D2's ratified
>   mechanism against the spec-check analogy that was corrected at ratification.
> - A test asserts the merge dedups an identical finding appearing in BOTH passes to one
>   entry.


**Route: python-engineer → python-reviewer, test-first. Every function gets a test that
actually runs, in the same turn, with production input shapes** (round-trip through the
real producer, not hand-authored fixtures, wherever a producer exists).

Scope, both in `src/devforge/lib/_grill/`:

- **The stamp.** `plan.md`'s content hash recorded into `specs/[feature]/grill-state.json`
  per D4's ratified predicate, written at or before `render-report` so it lands inside
  PHASE 6's artifact commit (D4's build-shaping note — the commit precedes the final state
  flip, fact 11).
- **The clean predicate.** A helper-exposed evaluation of D1's ratified bucket test over
  `partition.json`, so PHASE 3's branch (Phase 3 below) reads a value rather than
  re-deriving one in prose.

**Verify:**

- `python3 -m unittest` over `tests/lib/_grill/` passes, and the `_shared` + `_spec_check`
  + `_verify` suites are green (nothing outside `_grill` was touched).
- A test asserts the clean predicate is **false** for each blocking bucket ratified in D1,
  individually — one test per bucket, not one combined case.
- A test asserts the clean predicate is **true** when only `dismissed` is non-empty. This
  is the case that distinguishes D1(a) from "the report is empty" and is the most likely
  to be broken by a later simplification.
- A test asserts the clean predicate is **true** for the hand-written all-empty
  `partition.json` literal PHASE 3 emits — byte-for-byte the literal in `main.md`, not a
  re-serialized equivalent.
- A test asserts the stamp survives a `render-report` → read round trip, and that a
  `plan.md` edit of a single character changes it.
- `grill.md` renders **byte-identically to today** when the stamp is absent from a
  pre-existing state file — pinned by a full-string test, so an old feature dir does not
  crash the renderer.

---

### Phase 2 — The `/devforge:breakdown` gate

**Route: python-engineer → python-reviewer, test-first, for the verb;
instruction-author → instruction-reviewer + claude-code-guide for the `main.md` wiring**
(that file ships to `.claude/commands/devforge/breakdown.md`).

**PRIMARY MODEL, named 2026-08-23 and re-verified live: `plan_helper verify-spec-check` +
`/devforge:plan`'s `## PHASE 0a.8: Spec-check gate (mandatory)`.** Plan 82 shipped that pair
on 2026-08-19 into the SAME pipeline, one stage upstream, with the SAME shape this phase
needs: a **read-only** verb (`src/devforge/lib/plan_helper.py:2758`; *"never flips a
`**Status**:` line and never writes a file"*), **exit 0** printing a JSON ack the command
surfaces in one line, **exit 2** BLOCKED with the command copying stderr **VERBATIM as a
fenced code block and ending the turn**, **no override flag and no skip arm** (stated as a
standing prohibition at `src/commands/plan/main.md:134`), the blocked message **naming the
command for the USER to type**, and the gate seated **before the status flip** on the same
argument this plan makes one stage later. **Read that block (`src/commands/plan/main.md:117`–
`:136`) and its verb before writing anything here.** Every divergence from it is a decision
this phase must state and justify — a second shape for the same job, two commands apart, is
the pipeline inconsistency OQ-1 warns about rendered in helper code.

Scope:

- A new `breakdown_helper` verb implementing **D3's RATIFIED predicate**, failing closed
  with a stderr message the command copies VERBATIM.

  > **RECONCILED 2026-08-25 — this bullet said "D4's three-conjunct predicate" and that is
  > now WRONG.** D4 was ratified as RECORDED, NOT ENFORCED, so **freshness is not a gate
  > condition at all**. The verb checks exactly two things: `specs/<dir>/grill.md` EXISTS,
  > and the recorded `adversary_status` in `grill-state.json` is `complete` or `clean`.
  > It reads neither the disposition nor the hash. A build that implements a freshness
  > conjunct has shipped the design D3 explicitly rejected — the one that penalizes acting
  > on findings. **Model it on `verify-spec-check`
  first**, then on the `verify-*` family's exit convention for naming and in-command
  placement (fact 16); `specify_helper find-handoffs --require` (fact 19) remains the older
  precedent for the no-override stance and is no longer the closest one. No `--force`, no
  `--skip` flag (zero-escape-hatch policy).
- **INHERITED DEFECT, routed here 2026-08-25 because THIS phase creates the reliance:**
  `_grill/_state.py`'s `read_state` crashes with `AttributeError` on a file that is valid
  JSON but not an object (a top-level array), while its own docstring promises it *"Returns
  None on OSError … or json.JSONDecodeError (corrupt content)"*. Pre-existing and NOT
  introduced by Phase 1 — surfaced by the Phase-1 python-reviewer, which correctly declined
  to fix it there. **It lands here because the gate is the first caller that reads a
  `grill-state.json` it did not itself just write**, so a corrupt or hand-edited state file
  becomes reachable input for the first time. Left unfixed, the gate answers a corrupt state
  file with a Python traceback instead of the BLOCKED message this phase's whole contract is
  built on. Fix it as part of the verb's input handling — an explicit non-dict check
  returning `None`, so the gate's own absent-state path handles it — and add the test.
- A new `/devforge:breakdown` entry-side gate block calling it, placed **after PHASE 0a's
  plan resolution** (where the plan path first exists) and **before PHASE 0b's status
  flip** (D3's second cost). The sub-phase label is this phase's to choose; the ordering
  is not. **`PHASE 0a.8` is taken in `/devforge:plan`, not here** — breakdown's live
  structure is PHASE 0a → 0a.5 → 0b (`src/commands/breakdown/main.md:30`, `:57`, `:74`,
  re-verified 2026-08-23), so the label is free; note the collision only so nobody assumes
  the two numbers must match.

**Verify:**

- `tests/lib/` green, with the verb's own tests covering the **RATIFIED** cases:
  `grill.md` absent → exit 2; present + `adversary_status: complete` → exit 0; present +
  `adversary_status: clean` → **exit 0** (a successful pass that grounded no attack);
  present + `adversary_status: failed` → exit 2; present + `adversary_status: missing` →
  exit 2; present with NO recorded status (a pre-change state file) → exit 2; feature dir
  missing → the same failure shape as the sibling `verify-*` gates.

  > **RECONCILED 2026-08-25 — one case in the original list was INVERTED.** It read
  > *"present but hash-diverged → exit 2"*. Under D4's ratified recorded-not-enforced
  > stance the correct assertion is **hash-diverged → exit 0**, and that case is now
  > OQ-2's e2e anchor 4. **Add it as a unit test too**, phrased so its intent is
  > unmistakable: a stale report PASSES, and the staleness is visible in the artifact.
- **The blocked run does NOT flip `plan.md`'s `**Status**:`** — verified by ordering, and
  by a test if the flip is reachable from the helper layer.
- The gate's stderr names `/devforge:grill` as the required next step, in the arm-shape
  OQ-1 ratified.
- Instruction-reviewer clean; claude-code-guide clean.
- `grep -rn "grill" src/commands/breakdown/main.md` returns lines that are all true after
  the change. **Capture the pre-change output first — it is currently empty (fact 14),
  which makes the diff trivially reviewable exactly once.**

---

### Phase 2b — CLI wiring for the Phase-1 helpers *(ADDED 2026-08-26)*

**Route: python-engineer → python-reviewer, test-first.**

**A gap in this plan, not a discovery about the code.** Phase 1 deliberately registered NO
CLI verbs (*"a later phase wires the CLI"*), and Phase 3's route is instruction-author —
**instruction-only, so it cannot write Python.** Neither phase claims the wiring, so
`partition_is_clean` and `merge_two_passes` would have shipped as library functions no
command could reach, and Phase 3's `main.md` would have referenced verbs that do not exist.
Caught before Phase 3 was authored; recorded here rather than absorbed silently, because the
same seam (a build phase and an instruction phase with no Python phase between them) can
recur.

Scope, in `src/devforge/lib/_grill/_cli.py`:

- Expose the CLEAN predicate. **Prefer riding `render-report`'s existing stdout ack over a
  new verb** — PHASE 6 already calls it, and one fewer round trip is one fewer place the
  orchestrator can re-derive the value in prose (D5's helper-owns-shape ratification). If
  the ack shape cannot carry it cleanly, a dedicated verb is acceptable; state which and why.
- Expose the 2-pass UNION merge as a verb taking two pool paths and printing the merged bare
  array, mirroring `/devforge:audit`'s `merge-passes --pools` contract closely enough that a
  reader of both sees one pattern.
- Persist `adversary_status` and `plan_sha256` — whichever verb PHASE 6 already calls to
  advance state is the natural carrier, so the write lands INSIDE the existing unconditional
  artifact commit rather than adding a second write point (fact 11).

**Verify:**

- `tests/lib/_grill/` green, with a test per verb exercising the real CLI entry point (argv
  in, exit code + stdout out), not just the underlying function.
- The clean value the CLI reports equals `partition_is_clean`'s return for the same input —
  pinned by a test, so the two cannot drift.
- **No verb exposes a hash COMPARISON**, only the recorded value (D4).
- `git status --short` shows no `src/commands/` change — this phase is helper-side only.

---

### Process observation — a two-route phase can orphan half of itself *(2026-08-26)*

**Recorded because it is repeatable, not because it was costly here.** Phase 2 owned TWO
halves with DIFFERENT routes: the `breakdown_helper` verb (python-engineer) and its
`main.md` invocation (instruction-author). Only the Python half was dispatched. It reported
success, was reviewed, and was committed — and the phase looked done, because the half that
existed was healthy and the half that did not exist emitted no signal at all.

**The verb itself was honest.** Its docstring said *"NOT YET called from
`src/commands/breakdown/main.md` as of this commit — that wiring is separately routed and
still pending"*, and a reviewer had already corrected an earlier present-tense phrasing of
exactly that sentence. It was read, approved as accurate, and it WAS accurate. **A sentence
describing an unfinished migration is not an alarm — it reads as a calm fact, which is
precisely why it is easy to walk past.**

What caught it was not vigilance but a DIFFERENT task's verification: Phase 4 was writing
prose asserting that `/devforge:breakdown` requires a grill run, and went to check whether
that was true. `grep -rn "verify-grill-ran" src/commands/` returned zero. Had Phase 4 not
had a reason to check, the prose would have shipped aspirational.

**The generalizable rule:** when a phase spans two routes, the phase is not complete when
the first route reports success. Either dispatch both before committing either, or record
the outstanding half where the phase's own Verify will trip on it — a forward-reference
docstring inside the delivered half is not that place, because nothing reads it back.

---

### Recorded debt — `_grill/` test infrastructure *(2026-08-26, NOT owned by any phase here)*

Two review findings were deliberately DEFERRED during Phases 2/2b because both are test
infrastructure and both belong to ONE split rather than to whichever diff happened to
surface them. Recorded together so they do not survive as two forgotten threads:

1. **Two duplicated `_finding()` fixture helpers** across `tests/lib/_grill/test_cli.py` and
   `tests/lib/_grill/test_cli_phase1_wiring.py`, with different signatures. If the finding
   shape ever gains or loses a required key, both copies need updating in lockstep and
   nothing enforces it.
2. **`test_cli_phase1_wiring.py` crossed 600 lines** as a direct consequence of Phase 2b's
   own fix set adding tests to it — the reviewer flagged it rather than restructuring tests
   beyond what was asked, which was the right call.

**Also recorded, and NOT this plan's to fix:** `_audit/_cli.py`'s `cmd_merge_passes` carries
the IDENTICAL non-dict-element crash that Phase 2b fixed in the grill copy — it was
inherited from the pattern grill mirrored. Repairing it inside this plan's commits would
hide it from whoever owns `/devforge:audit`.

**And a stale instruction surfaced while dispatching this plan's build:**
`.claude/agents/python-engineer.md` tells every dispatched engineer to read
`src/devforge/lib/wizard_render.py` as a conventions model (DELETED by plan 30), claims the
live helpers are stubs whose originals sit in `.vault/devforge/lib/` (that directory does
NOT exist; the helpers are 1300–1400 lines), and exempts two deleted files from its
module-split thresholds while citing a completed plan for a pending removal. **The threshold
rule ITSELF is not the stale part** — Phase 2b's process finding stands on it — but the
surrounding context misinforms every `python-engineer` dispatch. Maintainer-side file, not
emitted to consumers. Reported to the maintainer 2026-08-26; disposition not yet given.

---

### Phase 3 — `main.md` rewiring: auto-accept-clean

**Route: instruction-author → instruction-reviewer + claude-code-guide** (this file ships
to `.claude/commands/devforge/grill.md`).

Scope, in `src/commands/grill/main.md`:

- **PHASE 2 / PHASE 3 — the 2-pass quorum wiring (NEW, D2).** Dispatch the adversary
  TWICE, consume + validate each pass into its own pool, then UNION the two pools into the
  single working list PHASE 4 refutes. **One refutation pass over the union, never two** —
  refuting per-pass triples the cost and produces two partitions nothing reconciles. Model
  the per-pass file naming on `/devforge:audit`'s `validated-p<pass>.json` → `merged.json`
  (fact: that command already ships this shape), and keep every path inside `$WORKDIR` so
  the single end-of-run sweep still reaches it.
- **PHASE 6** — surface the Phase-1 clean predicate alongside the existing render ack, so
  PHASE 7 branches on a value rather than a re-derivation. **The predicate is evaluated
  over the partition derived from the UNION** (D5's ratified amendment), not per-pass.
- **PHASE 6 — record the adversary status** into `grill-state.json` (Phase 1(b)), inside
  the existing unconditional artifact commit. **When the two passes disagree — one
  `complete`, one `failed` — record the STRONGER, since a union that received real findings
  from either pass did receive adversarial review.** State that rule in the text rather
  than leaving it to the build.
- **PHASE 7 — a leading no-entry clause, then unchanged.** The phase opens by naming the
  clean case: present the no-findings result in D2's permitted wording, write NO seed,
  **sweep `$WORKDIR`**, end. The existing four-option `AskUserQuestion` and its arms sit
  below that clause and are byte-unchanged in substance (2–4 options, no authored "Other"
  — the tool auto-injects it).
- **Rule 10** — restated so "cleanup is last" remains true on both arms.
- **`## Outputs of this command`** and the opening prose, wherever they describe the human
  gate as unconditional.

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean.
- `grep -n "AskUserQuestion" src/commands/grill/main.md` returns lines **inside the
  non-clean arm only**. Capture the pre-change output first.
- **`grep -n 'rm -rf "$WORKDIR"' src/commands/grill/main.md` returns the PHASE-0.3 clear
  and exactly ONE end-of-run sweep, and the sweep is reachable from BOTH arms.** This is
  the single most important check in the phase — fact 10 is the defect this shape exists
  to avoid.
- The clean arm still **renders, writes and WIP-commits** `grill.md` + `grill-state.json`
  — a diff that skips any of the three has broken plan 37's per-command artifact
  discipline.
- **PHASE 7 no longer presupposes that a pick exists.** Its arms are enumerated over
  picks; the leading clause names the no-pick case FIRST, and instruction-reviewer
  confirms that clause is present.
- **No seed is written on the clean arm** — plan 39's rule holds by construction (no
  matching arm entered), and the text says so rather than relying on it.
- The clean arm's user-facing sentence says the adversary found nothing that survived
  cross-examination, and does **not** say the plan is sound, proven or validated (D2).

---

### Phase 4 — The Rule-1 amendment + the full cross-reference sweep

**Route: instruction-author → instruction-reviewer** for every `src/` and plan-document
edit; **claude-code-guide** for anything shipping into `.claude/`. **Under D6's
model-invocable arm the `disable-model-invocation` removal IS a Claude-Code-integration
surface — claude-code-guide is mandatory for it, and the fetched-doc citation belongs in
the phase record.**

Open the phase with `grep -rn "auto-gate\|Opt-in\|opt-in\|mandatory gate\|never gates" src/ *.md` and
reconcile against D6's sweep list, **which is explicitly not certified exhaustive** — treat
a hit not named there as an omission in this plan, not as a new defect.

**⚠ The grep is NECESSARY AND NOT SUFFICIENT, established 2026-08-23.** Two classes of site
it structurally cannot find, both already named in D6's sweep list: **(1) the pipeline
CHAINS** that enumerate commands without ever using the word "opt-in" — verified this
session, `src/commands/fix/` returns **zero** hits for the entire alternation while
carrying four chains that end at `/devforge:breakdown`; and **(2) `src/CLAUDE.md`'s bracket
LEGEND**, which the grep does find but whose correct treatment is a DELETE the grep cannot
suggest. **Work the sweep list AND the grep, not the grep alone.** Conversely, the grep now
returns hits that are TRUE and belong to plan 82 — `src/CLAUDE.md:152` and the Narrowing-rule
`opt-in` occurrences in `src/commands/plan/main.md` — so **check what each hit is about
before treating it as a target**; the reconcile rule above is about hits the list omits, not
a licence to edit every line the grep prints.

Scope: every item in D6's sweep list, plus:

- `CHANGELOG.md` — an entry. **Verified 2026-08-17 by reading the file: there is NO
  `## [Unreleased]` section; the top section is `## [2.0.9] - 2026-08-17`.** Add under
  `## [Unreleased]` if that section exists when this phase runs, otherwise under the
  release section this change ships in — **do not create a stray heading** on the strength
  of an older plan's wording. **AMENDED 2026-08-23 — that 2026-08-17 observation is now
  STALE and the bullet's first arm is the live one:** plan 83's Phase 5 created
  `## [Unreleased]` on 2026-08-20, and it is the file's top section today (`CHANGELOG.md:8`,
  with `## [2.0.9] - 2026-08-17` demoted to `:20`, re-verified 2026-08-23). **This changes
  no behavior** — the conditional wording already routed correctly either way, which is why
  it was written conditionally — **so the correction is factual only, and the
  do-not-create-a-stray-heading warning still binds: read the file, do not trust this note
  either.**
- repo-root `CLAUDE.md` and `PLAN-STATUS-ARCHIVE.md` — this plan's entries move from NOT
  STARTED to the shipped wording, and **plan 82's expiring grill clauses are retired in
  both files — CLAUSE BY CLAUSE, per D6's arm-conditional breakdown, not wholesale**
  *(qualifier added 2026-08-23; the `disable-model-invocation` clause survives under the
  recommended arm)*. **Both entries already carry an `**AMENDED 2026-08-23**` reconciliation
  clause** recording that plans 81/82/83 shipped after drafting; Phase 4 supersedes those
  clauses with the shipped wording rather than appending a third layer beside them.
- `src/devforge/storage-rules.md` — **only if** D4's ratified carrier introduced a new
  artifact. Under the recommended `grill-state.json` carrier it does not; **record the
  no-op as deliberate** rather than leaving the question unanswered.

**Verify:**

- The sweep returns zero dangling references; full test suite green.
- **`grep -rn "never an auto-gate" src/` returns only lines that are true after the
  change** — under the recommended reading, zero lines.
- **`grep -n "never gates" src/commands/plan/main.md` returns no line claiming the
  stakes-hint's non-blocking nature means `/devforge:breakdown` is ungated** (fact 29),
  and the hint's own advisory, always-exit-0 behavior is still described accurately.
- **Plan 82's three expiring references are retired CLAUSE BY CLAUSE, per D6's
  arm-conditional breakdown** *(criterion corrected 2026-08-23 — it previously demanded all
  three be retired wholesale, which under the recommended keep-the-flag arm would DELETE a
  clause that is still true)*: in all three references the Rule-1 *"Opt-in, never an
  auto-gate"* clause and the *"one hit … 'not a mandatory gate'"* clause are gone, **and the
  *"still carries `disable-model-invocation: true`"* clause is retired ONLY if the
  model-invocable arm was picked — under the recommended arm it is left standing and that
  is the correct result**, recorded as deliberate rather than missed.
- **Plan 63's OQ-2 keep-7 reason is amended under BOTH arms** (its stated reason quotes the
  rewritten `description` sentence), and the counts are amended only under the
  model-invocable arm.
- **The plan-63 counts were read live and updated at most once** — never computed by
  applying this plan's delta to a remembered 13/7 (D6's coordination rule). *(Criterion
  sharpened 2026-08-23: the "if plan 82 shipped first" condition is DISCHARGED — it did,
  2026-08-19, and it contributed NO delta because it ratified D5(a-ii), so the live counts
  are still 13/7.* **Under D6's recommended keep-the-flag arm this criterion is satisfied by
  changing nothing at all, and a diff that moves the counts under that arm is the failure.**
  *Read them live regardless; the note is dated, the file is not.)*
- `23-ADVERSARIAL-GRILLING-PLAN.md` is **amended in place with the narrow reading**, not
  deleted and not contradicted from a distance.
- **No plan vocabulary in emitted text** — "D1", "the clean predicate", "Phase 3" and this
  plan's number are maintainer vocabulary. Emitted text names only the command's own
  phases and rules.
- `scripts/verify-agent-reachability.py` and `scripts/verify-memory-lane.py` pass (nothing
  here touches either, so a failure means something unintended moved).

---

### Phase 5 — Consumer e2e *(user-driven HARD GATE — DEFERRED 2026-08-26, NOT WAIVED)*

**Standing, not cancelled.** The maintainer deferred this run on 2026-08-26 to be executed once the
implementations queued behind this plan are done, as one batch rather than per-plan. Nothing below is
discharged and nothing below has been observed; the DONE status covers the BUILD only.

**Two numbers exist NOWHERE ELSE and this run is the only thing that produces them.** First, wall-clock
for the ratified 2-pass shape (D7) — plan 70's Phase 2 is itself deferred, so no per-command figure for
`/devforge:grill` exists in this repo at all. Second, and this one checks a risk THIS PLAN CREATED: the
**rate at which auto-accept actually fires**. D1's STRICT predicate and D2's union quorum both push CLEAN
further out of reach, so if auto-accept nearly never fires, this plan shipped a mandatory gate's friction
with none of the smoothing that justified building it. **Record it as a NUMBER** — an unrecorded rate
cannot be compared against anything later.

Run OQ-2's three known-answer anchors in a consumer install.

**Verify:**

- Each of the three is scored **explicitly** — stated, not summarized.
- **Case 2 additionally confirms `$WORKDIR` is gone after the clean run.** This is the
  regression the Phase-3 grep guards statically and the only place it is observed
  dynamically.
- **Wall-clock is RECORDED for the clean run and the finding-bearing run separately** —
  D7's obligation lands here, and it is the first per-command grill number this repo will
  have (fact 26). Record it even if it is unsurprising; an unrecorded number cannot be
  compared against later.
- Record the result in `REGRESSION-ANCHORS.md`, naming the Phase-1 clean-predicate tests
  alongside the observed behavior.
- **If it fails**, record the negative here with the artifacts and identify which mechanism
  produced it before proposing anything further — an auto-accept that should not have
  fired is a D1 finding, a gate that blocked a fresh report is a D4 finding, and a stranded
  `$WORKDIR` is a D5 finding. They have different fixes.

---

## Non-goals

- **Reviving plan 48 / making `/devforge:review` mandatory.** Plan 48 is SHELVED with a
  named revival trigger — an OBSERVED `/devforge:review` skip (fact 20) — and this plan is
  not that trigger. **A ratification of grill-mandatory is not an argument that
  review-mandatory follows**, and a future session must not cite this plan as plan 48's
  precedent. Plan 48's OQ-1 is cited here for its freshness reasoning ONLY (fact 21).
- **A grill quorum, a second adversary, or a second grill pass.** D2 records the decision
  and its honest bound; do not let a later "the gate missed something" observation convert
  into a quorum without re-arguing D2.
- **Touching `/devforge:spec-check` in any way.** That is plan 82. The only contact points
  are D6's counts coordination and D4's shared predicate, and neither is an edit to that
  command.
- **Changing grill's finder or refuter internals** — the `devils-advocate` brief, the
  three-ring traversal, the grounding gate, the refutation preamble, the architect
  exclusion, the four-bucket partition, the two-question PHASE-5 tree. **This plan changes
  WHEN grill runs and WHO it interrupts, never WHAT it finds.** A phase that starts editing
  `references/design-attack-checklist.md` or `references/refutation-preamble.md` has left
  this plan.
- **Making the gate read the disposition.** D3's spine and OQ-3's consequence; a gate that
  blocks on KILL is a different plan with a different argument.
- **Growing the disposition set past four** (fact 5), or adding a fifth partition bucket.
- **Touching consumer Claude Code settings** — `skillListingBudgetFraction`,
  `SLASH_COMMAND_TOOL_CHAR_BUDGET`, `skillListingMaxDescChars`, `skillOverrides`. They are
  cited above as the mechanism behind a verified fact, not as a lever this framework pulls.
- **Any change to plan 71's dead-code chain, plan 77's emission matrix, or plan 53's design
  binding.** None is read or fed by anything here.

---

## Dependencies + related

- **Plan 82** (`82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md`) — **the sibling, and
  the structural model for this file.** Its OQ-1 records the maintainer decision behind
  this plan, resolves it, and argues why grill could not ride along. **The two plans
  ratify and ship INDEPENDENTLY (D8), with exactly two coordination points: the plan-63
  counts (D6) and the staleness predicate (D4).** **REWRITTEN 2026-08-23 — plan 82 is
  ✅ DONE (build) 2026-08-19, Phases 0–6 (`55fa1ab`..`24256c5`), Phase 7 consumer e2e
  deferred 2026-08-20; every D-item and OQ is RATIFIED, and the earlier
  do-not-treat-anything-as-ratified caveat is retired with the state it described.** The
  cross-citation foreclosure is **LIFTED**: plan 82's own OQ-1 conditioned it on *both*
  plans being unratified, and it records the release itself — *"this plan's Phase 0
  ratified later the same day and plan 85's did not, so the symmetry no longer holds"*
  (`82-…-PLAN.md:657`). **What plan 85 may now cite as shipped fact, with where each lands:**
  - **D5 = (a-ii)** — a fail-closed preflight at `/devforge:plan` PHASE 0a.8 via a new
    read-only `plan_helper verify-spec-check` (exit 2 BLOCKED, stderr copied VERBATIM, no
    override flag), with **`disable-model-invocation: true` KEPT** and the blocked message
    naming the command for the USER to type. **Plan 63's 13/7 carve-out was NOT reopened
    and plan 82 contributed NO count delta.** → constrains **OQ-1** (name it) and supplies
    **D6**'s keep-the-flag arm its consistency argument; **Phase 2**'s primary model.
  - **OQ-2 = the content hash** of `spec.md` (sha256 over raw bytes), recorded as a
    `**Spec hash**:` line in `spec-check.md` at render time and re-hashed by the gate —
    **ratified identically with this plan's D4, the CARRIER differing and the PREDICATE
    not, and plan 82's records state plan 85's Phase 0 owes the RECIPROCAL NAMING.** →
    constrains **D4**.
  - **The gate is LIVE**, so D8's "if both ship" is now "this plan ratifies second" → see
    D8's amendment.

  **What is still NOT settled by plan 82, and must not be read across:** what a ratified D6
  is worth to this plan's own first-of-its-kind argument is *"plan 85's Phase 0 to decide
  and is NOT settled here"* (same note) — plan 82's D6 was itself argued with **no
  precedent cited**, so inheriting it as precedent would launder a first-of-its-kind
  decision into a second one.
- **Plan 83** (`83-DOWNSTREAM-REENTRY-SEED-PLAN.md`) — **ADDED 2026-08-23; not a dependency
  at drafting time because it had not shipped.** ✅ DONE (build) 2026-08-20, Phases 0–5,
  Phase 6 consumer e2e deferred. It made `/devforge:fix` the **third `ReEntrySeed`
  producer** (`specs/[feature]/fix-seed.json`, `target_stage="spec"`) and, in doing so,
  touched three things this plan reads: it **rewrote `src/commands/specify/main.md:154`**
  (the sentence whose live re-read this plan owed — discharged as a verified no-op under
  D6's sweep list), it **rewrote `/devforge:plan`'s PHASE-0a.7 no-seed branch**
  (`plan/main.md:115`), which retired half of fact 29's sweep target, and it **created the
  four-command re-run cycle sites** now named as their own D6 sweep bullet. **No decision
  of this plan depends on it** — grill's own seed lifecycle is untouched (plan 39's rule,
  D5), and the fix producer hard-codes `target_stage="spec"`
  (`src/devforge/lib/_fix/_seed.py:123`, verified 2026-08-23), so a `fix-seed.json` never
  targets `plan` and never interacts with a grill arm. Cited for the three surfaces only.
- **Plan 70** (`70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md`) — **the cost lever.** Its Phase 2
  is the only route to a real grill number (fact 26), and its Phase 3 is D7's named
  revival lever if the measured cost proves unacceptable. **Gate dilution is not on that
  route.**
- **Plan 23** (`23-ADVERSARIAL-GRILLING-PLAN.md`) — the command itself, and the source of
  the user-owns-the-verdict stance D6 narrows rather than deletes. Amended in place at
  Phase 4.
- **Plan 39** — the verdict-gated seed rule (`write-seed` lives inside PHASE 7's matching
  arm). D5's shape preserves it by construction; a build session must not "helpfully" move
  the seed write.
- **Plan 37** — the per-command artifact WIP-commit discipline the clean arm must not drop.
- **Plan 63** (`63-SKILL-COLLISION-SUPPRESSION-PLAN.md`) — the 13/7 carve-out whose stated
  reason for keeping grill is a quotation of the `description` sentence D6 rewrites
  (facts 2, 22), and the ≈40-word description budget the model-invocable arm would inherit
  (fact 23).
- **Plan 48** (`48-REVIEW-MANDATORY-GATE-PLAN.md`) — SHELVED, **not revived by this plan**
  (see `## Non-goals`). Cited for two things only: the canonical fail-closed
  forward-precondition shape (fact 19) and its OQ-1 freshness reasoning (fact 21).
- **Plans 38 / 41 / 42** — the mechanical-gate-over-skippable-prose pattern breakdown's
  `verify-*` family already implements, which Phase 2's verb follows.
- **Plan 19** — the cry-wolf precision stance D2 and D7 are both written against.
- **Plan 64** — grill's most-recently-modified-`plan.md` resolution (fact 27), which the
  gate must not contradict: the gate resolves the feature from `/devforge:breakdown`'s
  already-resolved plan path, never by mtime.

---

## Context for next session

**The one sentence that governs everything here:** grill has no prover, so "clean" can
only ever mean *nothing survived cross-examination on this one pass* — and every decision
below D1 is a consequence of refusing to overstate that.

**Trap 1 — skipping PHASE 7 on the clean arm.** PHASE 7 owns the ONLY scratch sweep (fact
10) and Rule 10 says so. **Skipping the phase strands `$WORKDIR` silently**, because the
next run clears it at startup and the leak never accumulates visibly. D5's shape is
"enter the phase, do not fire the gate" for exactly this reason. **The commissioning brief
said "skip the phase"; that instruction is superseded here and the divergence is
deliberate.**

**Trap 2 — reading `disposition == PROCEED` as "no findings."** It is not (fact 8). PHASE 5
routes an all-accepted-as-risk run to PROCEED with findings present. A build session that
implements D1 as a disposition check has implemented D1(b) while believing it implemented
D1(a).

**Trap 3 — over-reading the Rule-1 reversal.** What becomes mandatory is that the grill RAN
against the current plan. **The disposition never binds, and KILL does not block
`/devforge:breakdown`** (OQ-3). A future session reading "grill is mandatory now" without
that qualifier will build the verdict-blocking gate D3 refuses, and will be able to cite
this plan while doing it.

**Trap 4 — assuming `/devforge:breakdown` has a preflight to extend.** It does not. Its
only entry-side guard is prose (fact 15) and its six mechanical `verify-*` gates all run at
PHASE 3.5, after decomposition (fact 16). Phase 2 writes a new verb and a new entry-side
block, and it is the first of its kind in that command (fact 18). Budget for it.

**Trap 5 — treating the plan-63 counts as this plan's alone.** Plan 82 edits the same two
numbers (D6). Whichever ships second reads them live; applying a remembered delta produces
14/6 when the truth is 15/5. **AMENDED 2026-08-23 — the ARITHMETIC in that last sentence is
now counterfactual; the TRAP is not.** Plan 82 ratified D5(a-ii) and kept its flag, so it
contributed **no** delta: the live counts are still **13/7** (re-verified 2026-08-23 at
`src/CLAUDE.md:49`, `:79` and repo-root `CLAUDE.md:106`), and **the worst case is 14/6 —
only if THIS plan picks the model-invocable arm; under D6's recommended arm nothing moves.**
**Read them live anyway.** The trap was never the specific number — it is that three
hand-maintained sites carry a count nothing computes, so any remembered value is stale by
construction, and this note is itself a remembered value the moment it is written.

**Trap 6 — believing this plan has evidence behind it.** It does not, and that is recorded
in `## Origin` rather than hidden. The authorization is a maintainer decision plus symmetry
with plan 82. **D7's cost is unmeasured, D2's detection claim is one pass, and the
strongest objection in the file — that an auto-accepted clean verdict reads as an
endorsement — is recorded unresolved.** Do not let a build session's momentum convert any
of those into settled ground.

**The working tree is uncommitted throughout**, and several plans this file cites are
working-tree state, so any "shipped" claim about them means reviewed-but-uncommitted rather
than released. Re-check each from the code rather than from a Status line.

**Discovered while drafting, NOT owned by this plan and not fixed here** (items 1 and 2
were resolved elsewhere on 2026-08-18 and are retained below as history; item 3 stands):

1. **RESOLVED 2026-08-18 — the correction was routed and applied; the observation is kept
   as history.** At this plan's 2026-08-17 drafting time, repo-root `CLAUDE.md`'s plan-37
   index line stated *"Phase 6 (`/grill`) done-in-tree UNCOMMITTED (entangled with
   concurrent grill work)"*, while the session-start `git status` snapshot listed only a
   modified `CLAUDE.md` plus untracked plan documents — **no `src/commands/grill/` or
   `src/devforge/lib/_grill/` entry** — so that claim appeared stale, and the drafting pass
   (which had no shell access) recorded it for separate routing instead of acting on it.
   **The routing happened:** a live `git status` on 2026-08-18 reported both grill
   directories clean, the maintainer closed plan 37 the same day (*"plan 37 delivered"*),
   and both of that plan's ledger entries — the `CLAUDE.md` index line and the
   `PLAN-STATUS-ARCHIVE.md` entry — were updated that day. **No phase above touched it,
   and nothing further is owed here.**
2. **RESOLVED 2026-08-18 — the fourth name was added; the observation is kept as history.**
   Repo-root `CLAUDE.md`'s "no ledger entry" list named `79-`, `80-` and
   `83-DOWNSTREAM-REENTRY-SEED-PLAN.md` but omitted
   `84-ARCHITECT-CONSULT-ACCUMULATION-PLAN.md`, which exists at repo root (verified
   2026-08-18). **`84-` was appended to that list on 2026-08-18**, so it now carries four
   names; the list's *"read the plan file itself"* parenthetical still covers status, so no
   ledger entry was written for plan 84 and none is owed here.
3. **`/devforge:grill` PHASE 0.2 writes a fixed `/tmp/grill-preflight-check.json`** that
   lives OUTSIDE `$WORKDIR` and is therefore never swept by PHASE 7's `rm -rf` (fact 10).
   Pre-existing, harmless, and adjacent to the sweep this plan touches — recorded so a
   Phase-3 reviewer does not mistake it for a regression this plan introduced.

---

## When resuming work

1. Read this file in full, then **Verified mechanics** again — twenty-nine rows, each
   checkable in under a minute. **If rows 8, 10, 13, 14, 15, 16, 17 or 26 no longer hold,
   stop and re-derive**: they are the cost and scope argument, and D1's definition, D3's
   seat and D7's cost line all rest on them.
2. **Read `82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md` in full, starting with its
   OQ-1.** It is this plan's structural model, it records the decision that authorizes this
   plan, and it argues the three grounds that made this a separate plan. **UPDATED
   2026-08-23 — the old instruction "do not read its D-items as ratified" is RETIRED,
   because they now are.** Plan 82 is ✅ DONE (build) 2026-08-19; read its D5, OQ-2 and D6
   **as shipped fact**, and read the SHIPPED FORM alongside the plan text —
   `src/commands/plan/main.md:117`–`:136` and `plan_helper verify-spec-check` are what
   actually landed, and the plan file is the argument, not the artifact. **Two things it
   still does not settle for this plan** (both stated in its own OQ-1): what a ratified D6
   is worth to this plan's first-of-its-kind argument, and anything about grill's cost.
   See this plan's `## Dependencies + related` for the item-by-item split.
3. Read **`src/commands/grill/main.md` in full** — not just PHASE 7. PHASE 3's
   empty-findings branch, PHASE 5's all-accepted-as-risk branch, PHASE 6's unconditional
   commit and Rule 10's sweep all constrain what D1 and D5 may do.
4. **Re-verify every anchor before use. Grep the quoted string, never the `:NNN`** —
   `disable-model-invocation`, `never an auto-gate`, `DISPOSITION_VERDICTS`,
   `all-accepted-as-risk`, `rm -rf "$WORKDIR"`, `check-status-and-flip`,
   `find-handoffs --require`, `PHASE 3.5: Integrity gates`, `never gates`. **Added
   2026-08-23, because Phase 2 is modelled on them:** `verify-spec-check`,
   `PHASE 0a.8: Spec-check gate (mandatory)`, `**Spec hash**:`. **`never gates` now returns
   a TRUE plan-82 hit at `src/CLAUDE.md:152` that this plan must not edit** — check what
   each hit is about before treating it as a target. **The whole `## Verified mechanics`
   table was re-checked 2026-08-23; read `### Re-verification pass, 2026-08-23` before
   re-deriving any row from scratch.**
5. **Start at Phase 0. Produce the D7 cost line there or three tracked files go false.**
6. **Decide D1 by naming buckets**, D6's model-invocability arm explicitly, and D8's policy
   question once. Leaving any of the three to the build phase is how a carve-out or a stale
   count ships by accident.
7. Route every edit through the house loops: **python-engineer → python-reviewer,
   test-first** for helpers; **instruction-author → instruction-reviewer +
   claude-code-guide** for anything shipping into a consumer's `.claude/` — which includes
   `src/commands/grill/main.md`, `src/commands/breakdown/main.md`, and the frontmatter
   under D6's model-invocable arm.
8. Re-read the evidence constraint at the top before writing a sentence into this file,
   into any `src/` file, or into a commit message. **It binds execution, not just
   drafting.**
