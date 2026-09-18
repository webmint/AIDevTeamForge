# 98 — Delegated-Reply Attribution Plan

**Created**: 2026-09-18
**Status**: **✅ DONE (build) 2026-09-18 — Phase 0 CLOSED and Phases 1–3 BUILT.** Phase 0 was closed by a single blanket maintainer directive: every item ratified AS RECOMMENDED, no per-item deliberation supplied (see `## Phase 0 close record`). Commits: `5271c72` draft / `78c8d17` Phase 0 close + OQ-8 resolution + sub-phases 2a, 2d and 2e / `0b4155a` Phase 1 / `a96d840` sub-phases 2b and 2c. The Phase 3 docs commit follows this sweep, and no SHA is recorded for it here. ⚠ **Sub-phases 2a, 2d and 2e landed BEFORE Phase 1**, in the Phase-0-close commit. They name none of Phase 1's verbs or flags, so the forced build order still held for 2b and 2c, the only sub-phases that name them. **One post-ratification maintainer pick amends D9** — configure Q10, an explicit pick (see D9). **Phase 4 consumer e2e is DEFERRED — a user-driven HARD GATE, NOT run.** Everything here is **build-verified, NOT consumer-validated**, and "done" never means Phase 4 passed. ⚠ **The evidence class is unchanged by the build:** ONE observed site, every other site predicted, nothing measured (see `## Origin & evidence`).

Close the path by which a reply that picks nothing — a delegation such as "figure it out yourself", an evasive reply, or free text in AskUserQuestion's auto-added "Other" row — becomes, one step later, "the user's decision". The plan has five parts. First, one always-on rule in the emitted `CLAUDE.md` splits every question into two classes: RUN DECISIONS, where a non-pick is re-asked once and then takes the command's named no-write arm, and CONTENT ANSWERS, where the model answers and the record says the model answered. Second, per-site sentences at the open binding sites. Third, a persisted, honestly labelled intake confirmation at the one observed site. Fourth, approval summaries that list everything the model supplied. Fifth, helper vocabulary that stops crediting the user by name. **Implicit approval by invocation is NOT changed** — the maintainer accepted it on 2026-09-18, before ratification (D5).

---

## Origin & evidence

⚠ **Evidence class, and every summary of this plan must repeat it: ONE observed consumer incident at ONE site (`/devforge:research` Phase 0.5), plus a grep-verified, read-only audit of every user-interaction point in all 21 emitted commands and in `src/CLAUDE.md`. Every site other than research Phase 0.5 is a PREDICTED gap, not an observed one. Nothing was measured.** The incident came from a client's install. The evidence is held outside this repo by the maintainer and is not quoted here. This repo is public, so this document names no client, no client ticket, no client code identifier and no path to the benchmark or its logs.

**How it arose, 2026-09-18.** The conversation was in Ukrainian; every phrase below is an English paraphrase, per this repo's English-only file rule.

1. **The maintainer asked:** under this framework, when the operator's answer is ambiguous — for example "figure it out yourself" — can the model start treating its own decisions as the operator's decisions?
2. **The orchestrator answered yes, reading the spec text alone.** It named the specify decision points, the grill and spec-check dispositions, the approval gates and implement's Stage A, and proposed a plan.
3. **The same day, a peer Claude session reported an OBSERVED incident** at `/devforge:research` Phase 0.5. That session was running a comparative framework benchmark on a consumer install at release **2.0.11**. ⚠ **The orchestrator's first answer MISSED this site, and that is recorded here rather than smoothed over:** its own grep had surfaced the research `On correct` bullet carrying *"`correct` (or any other reply) → proceed to Phase 1 regardless"*, and the line was not flagged.
4. **The maintainer's directive:** compose this plan, and because research was missed, re-check every command where user interaction is foreseen. That directive produced the audit below.

### The incident, described generically

Two mechanisms, both at the research intake echo — Phase 0.5 Step 3, the question *"Is this interpretation right?"* with options `["confirm", "correct"]`.

- **Run A (the live run).** The operator replied to the echo with a delegating phrase ("figure it out yourself"). The model announced, in its own words, that it was counting that reply as confirmation at intake, and moved on. It also promised to attach a ready-made proposed answer to every later question.
- **Run B (an earlier, aborted attempt at the same benchmark run).** The operator clicked `confirm`. The echoed minimal scope contained an EXCLUSION the prompt never stated — in substance, "without touching the other call sites". The model later cited that confirmation as the user's decision **TWICE**. **(a)** It back-filled the `unchanged_behavior` rubric dimension, which the operator had answered with the same delegating phrase, as "taken from what you already confirmed at Phase 0.5". **(b)** After research, the operator answered all three product questions the model raised with the delegating phrase. The model decided all three narrowly "as you confirmed at intake", and so ruled OUT of scope a second call site that the model had itself discovered and had itself put to the operator as a question. That second call site is exactly the surface the benchmark measures, so the benchmark's probe for it is expected to fail.
- **The contrast the peer session recorded.** In the six rubric dimensions, the same delegating phrase was recorded honestly as `Partial` (own inference, unconfirmed). **The inconsistency is the finding: one gate launders a non-pick, and its neighbours do not.**
- **The 2.0.11 install is frozen for the benchmark.** The fix ships in the next release. Nothing in this plan touches that install.

### Three mechanisms (named once, used throughout)

- **M1 — NON-PICK REPLY.** A question offers options (AskUserQuestion, or a prose confirm/proceed question) or asks for content, and the reply names no option. The reply may be a delegation ("you decide", "up to you", "figure it out yourself", in any language), an evasive or neutral reply, or free text in AskUserQuestion's auto-added "Other" row that selects nothing. Where the spec has no rule for that reply, the model takes the recommended option itself and then records or cites it as the user's pick.
- **M2 — BUNDLING.** One confirmation covers a restatement of the user's input TOGETHER WITH the model's own additions — assumptions, exclusions, scope boundaries, defaults, seed text, composed prose. A single click, or a single non-pick treated as a click, then turns model extrapolation into "user-confirmed" content that later steps cite as the user's authority.
- **M3 — ATTRIBUTING VOCABULARY.** Helper verbs, flags, help texts, headings and status definitions assert user attribution by name — `user-chose-*`, "Log user resolution", "User explicitly accepted", "Requirements (what you asked for)", and `**Status**: Approved` defined as "user approved". Sometimes that happens on a path the model is FORCED down.

### The audit — method and counts

Seven read-only agents (no write tools), one per command group, enumerated every user-interaction point in all 21 command specs (plus references) and in the conversational rules of the emitted `src/CLAUDE.md`. Each point was classified as one of four classes. **CLOSED**: an explicit rule makes a non-pick reply safe and unattributed. **OPEN-BINDING**: no rule, and the result is recorded or cited as the user's decision, creates a binding artifact, or performs an irreversible or outward action. **OPEN-LOW**: no rule, but the result is reversible, low-stakes and unattributed. **BUNDLING** is M2, and it can combine with the other three. The orchestrator spot-verified the load-bearing citations of every report against the tree. ⚠ **Classification is agent judgment, spot-verified, NOT exhaustively re-verified.** The counts below are counts of classified points. They measure nothing.

- **17 pipeline and standalone commands: 105 interaction points — 11 CLOSED, 42 OPEN-BINDING, 52 OPEN-LOW.** BUNDLING, including partial and weak instances, is present at 16 of them. Per group (CLOSED / OPEN-BINDING / OPEN-LOW):
  - research 23 (7 / 10 / 6)
  - discover + specify 25 (2 / 9 / 14)
  - spec-check + plan 13 (0 / 8 / 5), plus 4 attribution sites that ask no question
  - grill + breakdown 12 (0 / 4 / 8)
  - implement + fix + review 16 (2 / 7 / 7)
  - verify + summarize + finalize + audit + pr-review + report-bug + report-ticket 16 (0 / 4 / 12); `/devforge:summarize` has none
- **4 setup commands (`init-forge`, `generate-docs`, `configure`, `constitute`): 37 points in 16 blocks** — 10 blocks OPEN-BINDING, 7 CLOSED, 2 OPEN-LOW. Some blocks carry two classes.
- **`src/CLAUDE.md`: 4 conversational rules** — 2 OPEN-BINDING (run-on-agreement; the blocked-gate offers), 1 OPEN-LOW (the fix-or-file offer), and 1 "not a guard" ("Never guess").
- **Of 146 points, exactly ONE was observed failing: research Phase 0.5.**

### Thirteen structural facts

Each fact was verified against the tree by the orchestrator on 2026-09-18. ⚠ Line digits drift — **grep the quoted text, never the digits.**

1. **The incident site has no rule and no record.** `src/commands/research/main.md` Phase 0.5 Step 3 asks *"Is this interpretation right?"* with `["confirm", "correct"]`, and the first ask handles only `On confirm` / `On correct`. The re-ask after `correct` says *"`correct` (or any other reply) → proceed to Phase 1 regardless"* — flow control only, with nothing about attribution. No helper records the reply. `record-intake-classification` writes `memo.intake_classifications` (statement / kind / minimal_fix), and no render or handoff code reads that field. **The "confirmation" exists only in conversation memory — which is exactly where the model later cited it from.** `src/commands/discover/main.md` Phase 0.5 carries the SAME gate: the same question, the same options, the same *"(or any other reply)"* sentence.
2. **The echo labels model text as the user's.** `research_helper render-intake-echo` renders `### Requirements (what you asked for)` (`src/devforge/lib/_research/_cmds_intake.py`, and the discover twin in `_discover/_cmds_intake.py`). Under that heading sit statements the spec calls *"verbatim or lightly paraphrased"*, plus a model-composed `Minimal scope:` line. Two tests pin the heading: `tests/lib/test_research_helper.py` (`assertIn("### Requirements (what you asked for)"`) and `tests/lib/test_discover_helper.py` (the same). Both `main.md` files quote the heading in their Step 3 prose.
3. **The minimality rule forbids added mechanisms, not added exclusions.** Research Step 2's "Minimality challenge" reads *"Any addition beyond that simplest change — a guessed mechanism, an extra distinction, a new state — is an 'extra' the user must CONSCIOUSLY opt into"*. It says nothing about stating what the change does NOT touch — the exact clause that was bundled in Run B and later cited.
4. **The only general guard does not fire on a delegation.** `src/CLAUDE.md` `### Never` item 6 reads *"**Never guess** — if unsure how code works, read it; if unsure what user wants, ask"*, and `src/constitution.md` carries the same rule. After "you decide", the model is not unsure what the user wants. **Nothing anywhere defines a delegation as a non-pick.**
5. **Specify's mode gate FORCES the misattribution.** In interactive mode `set-dp-default-applied` exits 2 with *"set-dp-default-applied: mode=interactive rejects default-applied setter (use set-dp-answer)"* (`src/devforge/lib/_specify/_cmds_phase2.py`). The only non-deferral path left is therefore `set-dp-answer --user-answer`, which sets `status="answered"` plus `user_answer`. The §8 renderer (`_specify/_render.py`) has branches only for `default_applied`, `deferred_open_question` and `no_DP_in_category`, so an answered decision point appears nowhere in the spec. The plan-handoff block counts it as `answered`, and `user_answer` is not written to `handoff.json`. Deferral (`set-dp-deferral`) requires that the user *"explicitly punts"*.
6. **Approval is a side effect of the next command's invocation, and that command is model-invocable.** `src/commands/plan/main.md` PHASE 0b says *"The act of running `/devforge:plan` constitutes approval of the spec for planning"* and prints *"Spec status: Draft → Approved (implicit approval via /devforge:plan invocation)."*. `src/commands/breakdown/main.md` PHASE 0b does the same for the plan. `breakdown_helper.py`'s `cmd_check_status_and_flip` writes a bare `**Status**: Approved`; the word "implicit" exists only in the chat message.
   - **The definitions assert a human act.** `src/devforge/storage-rules.md` defines *"Approved — user approved, ready for plan command"* and *"Approved — user approved, ready for breakdown"*. `src/CLAUDE.md` Hard Gates lists *"Spec approval → before `/devforge:plan` can run"* and *"Plan approval → before `/devforge:breakdown` can run"*.
   - **Cancel does not undo the flip.** A PHASE-3 `cancel` in `/devforge:plan` does not revert the PHASE-0b flip; `plan/main.md` has no revert or rollback text.
   - **Specify's own approve does not flip.** `/devforge:specify` Step 5.3 `approve` deliberately leaves the status alone (*"Spec status stays `Draft`"*). `_specify/handoff_schema.py` says *"The 'user approved the content' signal is the command spec calling finalize-handoff on the Phase 5.3 approve branch -- it is a runtime flow event, not a state field"*, and `_specify/_cmds_handoff.py` says *"Trust boundary: this verb does NOT verify the user approved the spec"*.
   - ⚠ **Plan 93 already recorded this and declined to own it:** `93-MODEL-INVOCATION-CARVE-OUT-NARROWING-PLAN.md` says *"spec and plan approval have been **implicit** since plan 63 … Recorded, not owned."* **The maintainer ACCEPTED implicit approval by invocation on 2026-09-18, before ratification (D5, RESOLVED), so plan 93's bound stays "recorded, not owned".** This fact stays here as a fact. Nothing in this plan changes it.
7. **Seeds carry no record of who picked, and their existence is read as the user's pick.** `grill-state.json` (`_grill/_state.py`) has no pick field, and `ReEntrySeed` (`_shared/seed_schema.py`) has no picker field. Consumers read a seed as *"a binding directive"* (`specify/main.md`, `research/main.md`, `discover/main.md`). `plan/main.md` and `specify/main.md` state that a producer *"writes a seed only when the user picks, at that command's own human gate"*. `/devforge:grill` PHASE 7.2 and `/devforge:spec-check` PHASE 5.2 both say *"AskUserQuestion auto-injects 'Other'"*, and then list arms only for the named options. Grill 7.2 shows the `## Disposition` block (verdict + rationale) but never the seed inputs (`prior_conclusion`, `must_satisfy`, `carried_findings`) that a matching pick commits.
8. **Some helpers' gates force a user-attributed label.**
   - **The conflict-resolution verbs.** `research_helper record-conflict-resolution` has the help text *"Log user resolution for a previously detected conflict."*, and `discover_helper record-conflict-resolution` has *"Persist user resolution for a detected conflict and clear the loser dimension."*. The only documented labels are `user-chose-<new|prior>`. `symptom-finalize` / `scope-finalize` refuse while any conflict is unresolved, so the model must write SOME resolution — and the only documented one credits the user.
   - **`--accept-gaps`.** Its help reads *"User explicitly accepted Partial/Missing dimensions; record override."*. On the discover side it sets `memo.override_recorded`, the SOLE sanctioned override of the verdict-flip invariant D — `discover/main.md` says an unfavorable fit MUST force `Reconsider` unless `override_recorded` is set.
   - **The existing finding.** `FINDINGS.md` finding 2 already records `--accept-gaps` as a blanket escape (its recommended fix is a per-dimension justification), and warns that a change *"must not silently weaken that closed override-set"*.
9. **Approval summaries omit what the model supplied.**
   - **`/devforge:plan` PHASE 3, both modes.** In auto mode, defaults are applied and marked `[default applied]` — *"The user reviews defaults at the approval gate below"* — but the summary template has no line listing them. In interactive mode the text says *"Do not silently apply defaults"*, yet no marker exists for a delegated answer. `plan-handoff.json`'s `DecisionRow` has no provenance field.
   - **`/devforge:breakdown` PHASE 4.** The approval summary carries no grill disposition line, although grill's own text says *"the human owns the final call at the `/devforge:breakdown` approval gate"*.
   - **`/devforge:specify` Step 5.1.** The echo truncates the overview at 240 chars and shows only the first 3 out-of-scope items, cut to 80 chars (`_specify/_render.py`), with no decision-point resolutions.
10. **Capture commands write model text under the user's name.**
    - **`/devforge:report-bug`** *"may be model-invoked (when the user asks to log a bug in conversation)"*, while its description is *"the bug in the developer's own words"* under `**Source**: manual`.
    - **`/devforge:report-ticket`** *"may be model-invoked (when the user mentions an item in conversation and agrees to file it)"*, and its Rule 3 says *"the body is recorded as the user gave it"*. On the model-invoked path, nothing requires the user's own words.
    - **`/devforge:research`'s ticket-file arm** passes the ticket body to `set-verbatim-prompt`, which is documented as what the user ACTUALLY asked.
    - **The strongest predicted chain the audit found:** a model-composed body → "what the user asked" → intake requirements.
11. **Destructive and outward gates have undefined confirmation.**
    - **`/devforge:finalize` 3.3** says *"Wait for the user to confirm (or supply edited message(s)). Do NOT proceed to 3.4 without confirmation — the squash is destructive"*. Confirmation is never defined, and `finalize_helper squash --confirm` is a flag the orchestrator itself passes.
    - **`/devforge:implement` Stage B, the gate-blocked path and crash recovery** reach `git reset --hard` and `Skipped` statuses with no non-pick rule.
    - **Stage A.** `conflict` items are ones the model *"must NOT decide on the user's behalf"*, and the spec calls a Stage-A judgment pick *"the human confirms the SHAPE"*.
12. **CLOSED precedents already in the tree — this plan generalizes them and invents nothing:**
    - `/devforge:fix` PHASE 1 bounce: *"An 'Other' answer, and any reply that does not select `re-enter specify`, writes NO seed."* This is the zero-re-ask shape, and that seed producer is already closed.
    - `/devforge:configure` Phase 6: unparseable → *"re-prompt once with the choice restated. On the second invalid reply, default to SKIP … Do NOT auto-apply on an ambiguous reply"* — the re-ask-once → no-write-arm shape.
    - `/devforge:init-forge` multi-root rejection: re-prompt up to 2 retries, then take the first folder and warn.
    - `/devforge:research` / `/devforge:discover` save and ticket prompts: *"Do not guess an ID"*, *"do not guess a name"*, *"Pre-offering is not answering"*, *"do not pick one on the user's behalf"*.
    - `/devforge:constitute` Phase 6.4 hook: *"On `Other`: treat the free-text answer as a 'No' with the user's text recorded inline"*.
    - `/devforge:specify` §5.2: an AC *"may NOT be written from inferred intent; it requires product intent, quoted"*.
    - `/devforge:research` Phase 1: *"**MANDATORY: never fabricate a user mode.**"* and *"If you find yourself about to justify a shortcut by attributing intent to the user, STOP"*.
    - `/devforge:finalize`'s `gh pr create` line: *"do not run it on an agreement"*.
    - ⚠ **DEFAULT-APPLY closures.** These are closed for loop control, but on ambiguity they APPLY. `/devforge:configure` Phase 3 says *"fall back to applying all Phase 2 values as confirmed and warn"*. Its Phase 5.2 prune-agents falls back to `prune-agents --apply`, which is destructive. `/devforge:constitute` Phase 3 has the same *"as confirmed"* fallback.
13. **A save-question gap sits inside a CLOSED rule.** Research/discover Step 4.1 treats free text as SAVE, with the text as the feature name, *"UNLESS the text clearly declines"*. An English delegation ("up to you") typed into the free-text row becomes the slug `up-to-you`, which passes `FEATURE_NAME_RE`. A non-Latin one fails the regex and is re-asked.

---

## Decisions to ratify

Nothing below is ratified. Each item states the decision, its options where they exist, a recommendation, and the strongest counter-argument against it, recorded honestly rather than answered away.

### D1 — The rule, emitted always-on

**Placement.** Append item **7** to `src/CLAUDE.md` `### Never` — a pure append, with items 1–6 byte-identical. Plans 87 and 89 set the append precedent in `### Always`, which now runs to item 16.

**Proposed text** (wording tightened from the orchestrator's draft; the single-action shape per class is kept):

> 7. **Never record your choice as the user's** — a reply that hands a decision back to you ("you decide", "up to you", or the same in any language), or that names none of the options you offered, is not the user's pick: never record, cite, or act on it as their confirmation, approval, answer, or choice, and never take an option for them because it is marked recommended. At a question that decides what the run does, ask the same question once more, and on a second such reply take the option the command names for that reply; where the command names none, end the turn having written nothing. At a question that asks for content, supply the content yourself, record it through the channel the command names for a model-supplied answer, and tell the user it is your choice. A question the command does not classify decides what the run does.

**The two classes.** Each is defined once, here, and each command designates its own sites (D2, D3, OQ-7).

- **Class A — run decisions.** Approve, proceed, cancel, pick an artifact, pick a disposition, commit, squash, skip, roll back, spend, run a command. A non-pick is re-asked once, then takes the command's NAMED no-write arm.
- **Class B — content answers.** Facts or product choices about the feature or the install: rubric dimensions, decision points, scope size, mode, design source, setup preferences. **A delegation legitimately authorizes the model to answer here — the fix is ATTRIBUTION, not refusal.**
- **Default: unclassified ⇒ Class A.** This conservative arm is what makes the rule escape-hatch-free.
- **"Never pick the recommended option because it is recommended."** That is the exact incident mechanism, and the proposed text states it.

**Pattern note (the one departure in the target list, named rather than hidden).** Items 1–6 of `### Never` are one short clause each. Item 7 is four sentences, which makes it the first multi-sentence item in that list. `### Always` items 15 and 16 are the nearest precedent for a longer item.

**The rule's second default, and why it is not an escape hatch.** *"Where the command names none, end the turn having written nothing"* closes a gap the orchestrator's draft left open. D2 names an arm only at OPEN-BINDING sites, while the rule sends every unclassified question — every OPEN-LOW site included — to Class A. It is a single mandatory action for the unnamed case, never a way out of the rule, and it errs toward writing nothing.

**RECOMMEND D1 as stated.**

**Counter-arguments, recorded:**

- **Detection is judgment.** Classifying a free-text reply as "hands the decision back" is itself model judgment. Nothing mechanical detects a delegation in natural language, so **this rule narrows the laundering path without closing it.**
- **The re-ask is friction.** Re-asking a user who has just explicitly delegated is friction. At an approval gate, a user who delegates twice gets a stall, and the work sits uncommitted. The answer offered — which does not retire the counter — is that the pick at an approval gate is precisely what this rule makes non-delegable, and that auto mode already does not bypass approval gates: `/devforge:plan` PHASE 3 in auto mode still asks *"Approve this plan?"*. ⚠ Since D5's resolution (2026-09-18), that answer protects the gate's PICK only. The `Approved` status can still arise when the next command is invoked.

### D2 — Class A sites: one per-site sentence naming the arm

Each OPEN-BINDING class-A site gets ONE sentence in its command spec, in the shape of `fix/main.md`'s closed bounce sentence (fact 12). That sentence names the arm a second non-pick takes. **The "no-write arm" is the option that writes, commits, deletes, flips, seeds, spends and publishes nothing. Where every option acts, it is "end the turn and do nothing".** ⚠ **The one thing a no-write arm may write is a record that makes the missing pick visible.** Exactly THREE sites write such a record:
- the research/discover intake UNCONFIRMED record (D4);
- the discover coverage-exit gap records, written with no verdict override (OQ-3);
- the Stage-A *"shape not confirmed by the user — delegated"* Completion Note (OQ-6).

**None of the three attributes a decision to the user.**

⚠ **Amended 2026-09-18 (build):** the count of THREE above covers the no-write arms of RUN-DECISION rows only, and it should be read that way. Two arms that write sit outside it. The `spec_type` pre-seed row below is really a CONTENT answer, not a no-write run decision: its `accept` keeps the upstream pre-seeded value, labelled as pre-seeded, through `classify-spec-type --seeded-by-upstream`. D3's design-source `None…` arm writes `set-design-source`. **Neither attributes anything to the user.** Trap 2 carries the same correction.

| Command | Site (grep text) | Second non-pick takes |
|---|---|---|
| research / discover | Phase 0.5 `"Is this interpretation right?"` (both asks) | proceed to Phase 1 with the interpretation recorded UNCONFIRMED (D4) — one of the three missing-pick records |
| research / discover | Step 4.1 save question + attach-mode save | `Don't save` (a delegation is never a feature name — closes fact 13) |
| research / discover | drift note `"Adjust <dimension> or continue?"` | continue, rewriting nothing |
| research | cost gate `"Investigation will scan roughly"` | `cancel` |
| discover | coverage exit `"accept current state and proceed"` | see OQ-3 (gaps recorded, NO verdict override) |
| specify | Step 5.3 `"Approve this spec?"` | `cancel` (spec stays Draft, state preserved) |
| specify | handoff pick `yes-most-recent / pick-other / cold` | end the turn, nothing imported |
| specify | other-branch `from-here / switch-to-default / stay` | `stay` |
| specify | spec_type pre-seed `accept / override` | `accept` (keeps the pre-seeded value, already labelled as pre-seeded) — ⚠ *Amended 2026-09-18 (build): a content answer, not a no-write run decision; see the note above this table* |
| spec-check | PHASE 5.2 disposition | NO pick, NO seed; say the disposition is still the user's and name both next routes — ⚠ *Amended 2026-09-18 (build): the two routes are `/devforge:plan` and a spec-check re-run; see the note below this table* |
| plan | PHASE 0a `"Process this spec?"`, pick-other, drift proceed/cancel, 0b `complete` / `unknown-status` | `cancel` / end the turn |
| plan | architect §6 Out-of-Scope escalation | the spec's §6 boundary stands (no override) |
| plan | PHASE 3 `"Approve this plan?"` | `cancel` |
| grill | PHASE 7.2 disposition | NO pick, NO seed; the disposition is still the user's |
| grill | bounded-loop escalation "this feature may be intractable as framed — decide" | stop, NO seed |
| breakdown | PHASE 0a `"Process this plan?"`, pick-other, drift, 0b `complete` / `unknown-status` | `cancel` / end the turn |
| breakdown | PHASE 4 `"Approve this breakdown?"` | `cancel` |
| implement | Stage A `conflict` item; `could-not-converge` item; Stage B `"Approve task NNN"`; gate-blocked; tooling-unavailable | `stop` (keep `wip.md` and the working tree) |
| implement | Stage A judgment item | see OQ-6 |
| implement | crash recovery `resume / rollback / skip / manual` | `manual` (touch nothing) |
| fix | PHASE 6 Stage B `"Approve fix for"` | `stop` |
| fix | PHASE 1 bounce | ALREADY CLOSED — byte-unchanged (the only zero-re-ask site; its no-seed arm is harmless) |
| finalize | 3.3 squash confirmation | no squash; end the turn. A confirmation is an explicit confirm or edited message(s) |
| verify | PHASE 8 fix-or-file offer; PHASE 9 `all / select / none` bug filing | neither / `none` |
| review | fix-or-file offer | neither |
| pr-review | `"Ticket text source for PR"` | `skip` — BUT free text that IS ticket text is the user's content → treat as `paste-now`. Telling ticket text from a delegation is model judgment — the bound D1's first counter-argument names |
| pr-review | CBM index cost prompt | `skip` |
| audit | 2.3 big-directory guard; 2.5 multi-pass cost guard | end the turn, no dispatch |
| `src/CLAUDE.md` | *"propose it, and once the user agrees, run it directly"*; blocked-gate offers; fix-or-file offer | do not run; an agreement is an explicit yes to THAT command |

⚠ **The `src/CLAUDE.md` row is kept for M1 consistency ONLY:** a delegation is not an agreement to that specific command. **It is NOT an approval protection.** The maintainer accepted the approval side effect of invoking the next command (D5, RESOLVED 2026-09-18), so a model-invoked `/devforge:plan` or `/devforge:breakdown` still flips `Approved`, and this row does not claim otherwise.

⚠ **Amended 2026-09-18 (build) — the spec-check row.** "Name both next routes" shipped as `/devforge:plan`, to proceed on the report, or a re-run of `/devforge:spec-check`, to make the pick. `/devforge:specify` is not one of them. It blocks on a feature directory that already holds `spec.md` and has no spec-targeting seed (`_specify/_cmds_handoff.py`, `find-handoffs`), and a non-pick writes no seed. For the same reason, spec-check PHASE 7 routes a `Revise spec` CROSS-pick, which writes no seed, to the same two routes instead of the blocked `/devforge:specify`.

**RECOMMEND.**

**Counter-argument, recorded:** roughly 30 sentences across roughly 17 files is a large prose surface. OPEN-LOW sites get NO per-site sentence; D1 covers them, and its second default ends the turn there with nothing written. That is a deliberate bound, and it is listed in Non-goals.

### D3 — Class B sites: model-supplied content recorded through a named model channel

| Command | Site | Channel on a delegation |
|---|---|---|
| research / discover | Phase 1 rubric dimensions (free text) | `--state Partial` (existing), and the value says it is the model's inference |
| research / discover | scope closed choice | model picks, `--state Partial`, named |
| research / discover | conflict resolution `"Which to keep"` | `--resolution delegated-<new\|prior>` (the free-form field already accepts it; help text fixed in D8) |
| research | mode flip / ambiguous mode | keep auto-detection when it produced a mode; otherwise the model picks and says so (the `<user's choice>` placeholder gains a sibling) |
| research | Phase 2.4d write-boundary / intermediates prompts | the model traces the chain itself and records it as model-traced, never "user-supplied" |
| research / discover | design-reference prompt | a delegation is `none` — the model never names a reference on the user's behalf |
| specify | Phase 2 decision points (interactive) | `set-dp-default-applied` becomes legal in interactive mode WITH a required `--delegated-reply "<verbatim reply>"` (Python, D8); §8 renders it `[default applied]` naming the delegation; auto mode byte-unchanged |
| specify | design source | the first option `None…` (already the stated default) — ⚠ *Amended 2026-09-18 (build): this arm writes `set-design-source`; see D2's note on the count of THREE* |
| plan | PHASE 3 interactive decision points | `[default applied]` marker in interactive mode too, listed under "Decision Points Resolved" exactly as auto mode lists it |
| setup (D9) | init / configure / constitute questions | see D9 |

**RECOMMEND.**

**Counter-argument, recorded:** `Partial` on a delegated dimension lowers coverage, and can push the user toward `--accept-gaps`. That is honest, not a regression — but it is a real cost, and FINDINGS.md finding 2's blanket escape is the route it pushes toward.

### D4 — The incident site: the research and discover intake echo

- **(a) Persist the confirmation.** Add a new setter to BOTH helpers: `record-intake-confirmation --state confirmed|unconfirmed --reply "<verbatim reply>"`. It renders as one line in `research-report.md` / `discovery-report.md`: "Intake interpretation: confirmed by the user", or "NOT confirmed — the reply was '<verbatim>'". **The line is NOT added to the handoff schema** — no consumer needs it, and leaving it out keeps the Python small. That is recorded as a choice.
- **(b) No exclusions at intake.** In Step 2 of both commands, the minimal fix / minimal scope states what changes. **It states what the change leaves untouched only by quoting the prompt's own words.** What the change does NOT touch is research's OUTPUT (caller enumeration, the emission matrix) plus the user's `unchanged_behavior` answer — never an intake assumption. This closes fact 3's gap, which is the Run B mechanism.
- **(c) An honest heading.** `### Requirements (what you asked for)` becomes `### Requirements (as I read your prompt)` in both helpers, in both `main.md` quotes, and in both tests (fact 2).
- **(d) The non-pick arm.** A non-pick at either ask → re-ask once → proceed UNCONFIRMED (the D2 row). **An unconfirmed interpretation is the model's reading, and it is never cited as "you confirmed".**

**RECOMMEND (a) + (b) + (c) + (d).**

**Counter-argument, recorded:** (b) makes the echo less informative for a user who WANTS a narrow scope — they must state it at `unchanged_behavior`. Accepted.

### D5 — Approval semantics — RESOLVED by the maintainer 2026-09-18, before ratification: KEEP implicit approval by invocation; no change

**The resolution.** In conversation on 2026-09-18 (paraphrased from Ukrainian), the maintainer accepted implicit approval by invocation. `Approved` in `spec.md` / `plan.md` arises as a side effect of running the NEXT command, which the model may invoke itself, and it stays that way. **This is a resolved fact, not a ratification fork** (the shape of plan 97's OQ-1 RESOLVED). Fact 6 stays in Origin as a fact, and plan 93's bound stays "recorded, not owned". Every other finding stays in scope.

**Considered and not taken:**

- **(a) Relocate the flip.** Specify's and plan's own `approve` picks would set `Approved`, and PHASE 0b of the next command would become a read-only check.
- **(b) An honest relabel.** Keep flip-on-invocation and redefine `Approved` as "the next stage ran against it".

**What the resolution means for the rest of this plan:**

- The specify and plan approve gates remain class-A questions (D2). A second non-pick there takes `cancel`.
- A later invocation of the next command still flips the artifact to `Approved`, by the maintainer's accepted design.
- `storage-rules.md`'s `Approved` definitions, `src/CLAUDE.md`'s Hard Gates wording, both PHASE-0b blocks and every `cmd_check_status_and_flip` stay byte-unchanged.
  - ⚠ **Amended 2026-09-18 (build):** "both PHASE-0b blocks … stay byte-unchanged" is too strong. Their flip logic, tokens and messages are unchanged. But the two PHASE-0b QUESTIONS in each of `/devforge:plan` and `/devforge:breakdown` — the `complete` and `unknown-status` arms — each gained the one non-pick sentence that D2's own `0b complete / unknown-status` rows call for. The other surfaces this bullet names are byte-unchanged.

### D6 — Approval summaries show everything the model supplied

- **`/devforge:specify` Step 5.1:** list every `[default applied]` decision point, delegated ones included, and every out-of-scope item in full. The 3-item / 80-char truncation goes (`_specify/_render.py`, Python).
- **`/devforge:plan` PHASE 3 summary:** add a `**Defaults applied**:` line listing each `[default applied]` decision, auto and delegated alike. The line is omitted when there are none.
- **`/devforge:breakdown` PHASE 4 summary:** add a `**Grill**:` line naming the report's disposition and what happened at grill 7.2 — picked X, not picked, or a clean run with no question.
  - ⚠ **Amended 2026-09-18 (build):** nothing records what the user picked at grill 7.2 — `grill-state.json` has no pick field (fact 7) — so the line cannot show it. What shipped names three recorded facts and never the pick: the report's RECOMMENDED disposition, whether the run was clean (read from `grill.md`'s `## Summary` counts), and whether `grill-seed.json` exists.
- **`/devforge:grill` 7.2:** the description of the matching re-entry option shows the seed inputs it would commit (`must_satisfy`, `prior_conclusion`).

**RECOMMEND.**

**Counter-argument, recorded:** longer summaries feed approval fatigue, which is plan 96's concern. Accepted — a summary that hides what it asks the user to approve is the defect.

### D7 — Capture commands on the model-invoked path

In the `/devforge:report-bug` description and the `/devforge:report-ticket` body: when the model invokes the command, the text is the user's own words, quoted from the conversation, and the model composes none of it. If the user's words do not describe the item, the model asks. **A delegation files nothing.** `--type` / `--severity` / `--title` stay model-composable labels; they are already documented as unchecked. Instruction-only.

**RECOMMEND.**

**Counter-argument, recorded:** a verbatim multi-turn quote reads rough. That is the point — research consumes it as the verbatim prompt (fact 10's chain).

### D8 — Attributing vocabulary and the rest of the Python surface (Phase 1)

- **The conflict-resolution help texts** (`record-conflict-resolution`, research and discover) become neutral ("Record the resolution …"). The specs document `user-chose-<new|prior>` (an explicit pick) AND `delegated-<new|prior>`.
- **The `--accept-gaps` help text** becomes neutral. FINDINGS.md finding 2's per-dimension justification stays OPEN, with a dated note.
- **specify:** `set-dp-default-applied` is relaxed in interactive mode, with a required `--delegated-reply` (D3).
- **The intake heading** (D4c) and **`record-intake-confirmation`** (D4a).
- **discover:** `scope-finalize --no-verdict-override` (OQ-3).
- **D6's specify summary render.**

**RECOMMEND as the collected Python surface.** Ratifying D3, D4, D6 or OQ-3 ratifies the matching line here, and declining one drops it. **No separate counter-argument:** each line inherits its parent item's.

### D9 — Setup commands (human-typed; configuration, not pipeline decisions)

- **Enum and option questions.** A delegation at such a question applies the recommended or detected value, and the closing summary names it "applied by default — you delegated" (class B). The questions in scope: init-forge's workspace, branch and project root; configure's Q9, Q10, Q11, Q12, Q12.1–3 and Q13; constitute's Q-mode.
- **Free-text rows.** A delegation typed into a free-text row is never stored as a value. Configure Q11's pin path saves *"the typed value … unchanged"*, and a delegation is not a model name. The same holds at init-forge's folder and branch prompts.
- **constitute Q-domain.** A delegation writes ZERO entity rules. Business entities become constitution law and are never invented.
- **constitute Phase 6.2 `ship / cancel / fix`.** A second non-pick → `cancel`. The closing says "user-acknowledged ship-as-is" only when the user picked `ship`.
- **configure Q10's question text** names both effects of its answer: the commit footer AND the `Run by:` provenance stamp. The audit found the question names only the footer.

**RECOMMEND.**

**Counter-argument, recorded:** setup runs once, with the human present, and the stakes are lower. Accepted — hence class B.

⚠ **Amended 2026-09-18, after ratification, by an explicit maintainer pick** — made through AskUserQuestion during the build, so it is a pick, not a delegation. **configure Q10 is the ONE exception to this decision's first bullet.** A delegation at Q10 takes `No`, never the recommended `Yes`. The reason is that the same answer also turns on stamping the user's `git config user.name` into committed pipeline artifacts as a `Run by:` line (`_shared/provenance.py`'s `read_ai_attribution_enabled` reads it), and publishing a person's name is never decided on a delegation. Q10's text now names both effects, as this decision's last bullet asked. Phase 4 anchor 8 tests the exception.

### D10 — Tripwires and non-deltas

- Zero gates, zero new `verify-*` numbers, zero hard-fail validators (**plan 75's tripwire, both halves**).
- No `disable-model-invocation` change: **17 model-invocable / 4 human-typed-only (21 promoted; plan 95 made it 17), untouched.**
- No `src/constitution.md` edit. Its "Never guess" line stays, so there is no universal-defaults drift.
- Python is confined to Phase 1.
- No back-porting into shipped installs.
- **The frozen benchmark install is never touched.**

### OQ-1 — Where D1 lives

`### Never` item 7 vs `### Always` item 17 vs a new section. **RECOMMEND `### Never` item 7** — the rule is a prohibition.

### OQ-2 — Re-ask count

One re-ask vs none (fix's shape). **RECOMMEND one**, on the `/devforge:configure` Phase 6 and `/devforge:init-forge` precedents (fact 12). `fix/main.md`'s zero-re-ask bounce stays byte-unchanged either way.

### OQ-3 — The discover coverage exit

Neither arm is safe today. "accept" sets `override_recorded`, the verdict-rule-D override (fact 8), and "continue" loops. **RECOMMEND an additive `scope-finalize --no-verdict-override`, used ONLY on the non-pick arm**: the gaps are recorded, `override_recorded` stays false, and rule D still forces `Reconsider`. The explicit-pick path is byte-unchanged, so FINDINGS.md finding 2's *"must not silently weaken that closed override-set"* holds.

### OQ-4 — The default-APPLY closures

**RECOMMEND:**
- configure Phase 5.2's prune-agents falls back to SKIP, because it deletes agent files.
- configure Phase 3 and constitute Phase 3 keep apply-on-fallback, but their warning says the values were applied WITHOUT confirmation.

**Counter-argument, recorded:** a prune-skip leaves unused agents installed. Harmless.

### OQ-5 — The pr-review NDA reminder

Today the text reads *"The reviewer's continuation past that prompt is treated as confirmation"*. **RECOMMEND rewording it to "informational; nothing records consent"**, with no new question. **Alternative:** an explicit yes.

### OQ-6 — The implement / fix Stage A judgment item

Option 1 is the agent's already-applied resolution. **RECOMMEND: a second non-pick keeps option 1 (no relaunch), and the task's Completion Notes record "shape not confirmed by the user — delegated"**; Stage B still gates. **Alternative:** `stop`.

### OQ-7 — Where the class designation lives

**RECOMMEND per-site sentences in each command**, because commands load independently. The alternative is one shared reference file.

### OQ-8 — The `claude-code-guide` precondition

The rule relies on AskUserQuestion always offering a free-text "Other" row. **Verify that through the `claude-code-guide` agent before Phase 2** — the house rule for every Claude-Code-integration fact, never from memory. The two in-tree statements that *"AskUserQuestion auto-injects 'Other'"* (fact 7) are this framework's own claims, not the vendor's.

**RESOLVED 2026-09-18, before Phase 2, via `claude-code-guide`.** (1) The only docs page it found (`code.claude.com/docs/en/agent-sdk/user-input.md`, "Handle clarifying questions") places the "Other" row on the IMPLEMENTING APPLICATION (*"Display an additional 'Other' choice after Claude's options that accepts text input"*), documents no switch to suppress it, returns free text in the same `answers[question]` field as an option label (distinguishable only by not matching a label), and documents *"1-4 questions with 2-4 options each"* without saying whether "Other" counts. (2) Claude Code's own `AskUserQuestion` tool description, as loaded in a Claude Code session on 2026-09-18, states *"Users will always be able to select 'Other' to provide custom text input"* — the CLI's behavior, which no docs page states. **Consequence for this plan: none on the design.** D1's rule is channel-agnostic — it governs *a reply that names none of the options*, whether that reply arrives through an "Other" row, as a plain typed message instead of an answer, or at a prose question — so it holds whether or not a given host renders "Other". The in-tree *"auto-injects 'Other'"* sentences are left as they are (true of the Claude Code CLI per its tool description; not this plan's subject).

---

## Phase 0 close record

**CLOSED 2026-09-18 by a single blanket maintainer directive** — given in Ukrainian right after the draft was presented; English paraphrase: *"commit plan 98 and implement it"*. **Every ratifiable item is ratified AS RECOMMENDED. No per-item deliberation was supplied**, and this record does not imply that any counter-argument was answered — each stays recorded at its decision (the plans 91 / 92 / 94 / 95 / 96 precedent). The orchestrator stated this reading of the directive to the maintainer before building, naming it as its own interpretation.

- **D1** — RATIFIED as recommended: `src/CLAUDE.md` `### Never` item 7, the proposed text incl. both defaults.
- **D2** — RATIFIED as recommended: one per-site sentence per table row; `fix/main.md`'s bounce byte-unchanged.
- **D3** — RATIFIED as recommended: the model-channel table.
- **D4** — RATIFIED as recommended: (a) + (b) + (c) + (d).
- **D5** — RESOLVED 2026-09-18 by the maintainer, before ratification: KEEP implicit approval by invocation; no change. Not a ratified arm.
- **D6** — RATIFIED as recommended.
- **D7** — RATIFIED as recommended.
- **D8** — RATIFIED as the collected Python surface (follows D3, D4, D6, OQ-3).
- **D9** — RATIFIED as recommended. ⚠ *Amended after ratification, 2026-09-18, by an explicit maintainer pick: a delegated configure Q10 takes `No` — see D9.*
- **D10** — RATIFIED as recommended.
- **OQ-1** — `### Never` item 7.
- **OQ-2** — one re-ask.
- **OQ-3** — additive `scope-finalize --no-verdict-override`, used only on the non-pick arm.
- **OQ-4** — prune-agents falls back to SKIP; configure / constitute Phase 3 keep apply-on-fallback with a warning that says the values were applied WITHOUT confirmation.
- **OQ-5** — reword to "informational; nothing records consent"; no new question.
- **OQ-6** — a second non-pick keeps option 1 (no relaunch) and the Completion Notes record "shape not confirmed by the user — delegated".
- **OQ-7** — per-site sentences in each command.
- **OQ-8** — the `claude-code-guide` check is owed before Phase 2 (a precondition, not an arm). *Discharged 2026-09-18, before Phase 2 — see OQ-8.*

---

## Phases

### Phase 0 — Ratification

Every ratifiable D-item (D1–D4, D6–D10) and every OQ (OQ-1–OQ-8) gets a recorded outcome in `## Phase 0 close record`. **No build until Phase 0 is closed.** D5 is RESOLVED (2026-09-18): the record lists it as resolved, not as a ratified arm, and nothing about it is owed after the close.

#### Verify

- `## Phase 0 close record` names **each** of D1–D4, D6–D10 and OQ-1–OQ-8 with its ratified arm. No item is silently omitted. **D5's entry records it as RESOLVED 2026-09-18, not as a ratified arm.**
- The record states whether per-item deliberation was supplied.
- Each decision above still carries its counter-argument. **A ratified decision with its counter-argument deleted cannot be re-opened honestly.**

### Phase 1 — Python

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn** (house discipline).

- **1a — `_research/` and `_discover/`:**
  - `record-intake-confirmation` plus its report line (D4a).
  - The echo heading, with the two tests that pin it (D4c).
  - The `record-conflict-resolution` and `--accept-gaps` help texts (D8).
  - discover `scope-finalize --no-verdict-override`, if OQ-3 is ratified.
- **1b — `_specify/`:**
  - Interactive `set-dp-default-applied --delegated-reply` (D3).
  - The §8 render of a delegated default.
  - The Step 5.1 summary lists every default-applied decision point and every out-of-scope item, untruncated (D6).

#### Verify

- The targeted suites are green (`tests/lib/test_research_helper.py`, `tests/lib/test_discover_helper.py`, `tests/lib/test_specify_helper.py`), then the **full `tests/lib` suite** is green.
- `grep -rn "user-chose" src/devforge/lib` shows the label surviving only as a documented label beside `delegated-`, never in a help text that credits the user.
- If D4(c) is ratified, `grep -rn "Requirements (what you asked for)" src/devforge/lib tests/` returns zero hits. The two `main.md` quotes change in Phase 2, not here.
- python-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 1 build record — 2026-09-18

**Route as specified: python-engineer → python-reviewer. Every package was reviewed and every finding was fixed. Commit `0b4155a`.** ⚠ This block records a BUILD, not a consumer observation. Nothing below was run on a real install.

**What landed:**

1. **research + discover.**
   - `record-intake-confirmation --state confirmed|unconfirmed --reply "<verbatim>"` writes `memo.intake_confirmation` (D4a).
   - The report renders one `**Intake interpretation**:` line: confirmed, or NOT confirmed with `the reply was "<reply>"`. The reply is collapsed to one line and markdown-escaped.
   - The intake echo heading is now `### Requirements (as I read your prompt)` (D4c).
   - The help texts are neutral (D8). `record-conflict-resolution` documents `user-chose-<new|prior>` and `delegated-<new|prior>`, and `--accept-gaps` no longer says "User explicitly accepted".
2. **discover — `scope-finalize --accept-gaps --no-verdict-override` (OQ-3).**
   - It records the gaps and sets `override_recorded` to False explicitly.
   - Verdict invariant D therefore still forces `Reconsider`. The invariant is enforced at three sites under `_discover/`: `_cmds_core.py`'s `cmd_verify`, `_handoff_build.py`'s `DiscoveryBlock` copy, and `handoff_schema.py`'s `DiscoveryBlock` post-init.
   - `--no-verdict-override` alone exits 2. `--accept-gaps` alone is unchanged.
3. **specify.**
   - `set-dp-default-applied` is accepted in interactive mode only with `--delegated-reply`, and the reply is stored as `dp.delegated_reply` (D3). Auto mode plus the flag exits 2. Interactive mode without the flag keeps the original rejection.
   - §8 appends `_(you delegated this choice: "…")_` to the unchanged `[default applied]` prefix.
   - Status transitions clear a stale `user_answer` / `delegated_reply`.
   - The Step-5.1 summary gains a conditional `- **Defaults applied**:` block and lists every out-of-scope item in full. The 3-item / 80-char cut is removed (D6).
   - The stale "4-bullet" wording was fixed in `_specify/`'s `_cli.py`, `_render.py` and `_cmds_phase5.py`.

**Tests:** the full `tests/lib` + `tests/scripts` run is 11171 passed, 14 skipped. Targeted suites: `test_research_helper.py` 588 passed, 2 skipped; `test_specify_helper.py` 373; `test_discover_helper.py` 187.

**Verify greps, re-run 2026-09-18 when this record was written:**
- `Requirements (what you asked for)` has zero hits under `src/` and `tests/`.
- `user-chose` under `src/devforge/lib` has exactly two hits: `_research/_cli.py` and `_discover/_cli.py`. Each is a help-text label sitting beside `delegated-<new|prior>`.

### Phase 2 — Instructions

**Route: instruction-author → instruction-reviewer. OQ-8's `claude-code-guide` check runs FIRST.** The phase is split into five sub-phases so that no single dispatch is large.

- **2a** — `src/CLAUDE.md`: `### Never` item 7 and the agreement wording.
- **2b** — `research/main.md` and `discover/main.md`: the D2 rows, D3 and D4.
- **2c** — `specify`, `spec-check`, `plan`, `grill` and `breakdown`: the D2 rows, D3 and D6.
- **2d** — `implement` (plus `references/crash-recovery.md`, `references/review-loop.md` and `references/forcing-functions-gate.md`), `fix`, `finalize`, `review` and `verify`: the D2 rows and OQ-6. ⚠ This sub-phase shares four files with plan 97 (Trap 8).
- **2e** — `report-bug` and `report-ticket` (D7), `pr-review` (OQ-5), `audit`, `init-forge`, `configure` (plus its references), `constitute` and `generate-docs` (D9, OQ-4).

#### Verify

- Every D2 and D3 row has its sentence — a grep list per row, each result recorded.
- **No emitted text names plan vocabulary** ("D2", "Phase 1", "plan 98", "Class A" as a plan label). Emitted text names only the rule, the command and the arm.
- `### Never` items 1–6 are byte-identical, and item 7 is an append.
- `fix/main.md`'s bounce sentence is byte-identical: *"An 'Other' answer, and any reply that does not select `re-enter specify`, writes NO seed."*
- **D5 is RESOLVED as keep, so its surface is byte-unchanged:** `grep -rn "constitutes approval" src/commands` still hits `plan/main.md` and `breakdown/main.md` (verified 2026-09-18), and `src/devforge/storage-rules.md` has no diff.
- instruction-reviewer returns SHIP-READY for each sub-phase, or every finding is fixed.

#### Phase 2 build record — 2026-09-18

**Route as specified: instruction-author → instruction-reviewer for each sub-phase, and every finding was fixed.** OQ-8's `claude-code-guide` check ran first (see OQ-8). **Commits: `78c8d17` carries 2a, 2d and 2e with the Phase 0 close, and `a96d840` carries 2b and 2c.** ⚠ Instruction-only. Nothing below has been observed on a real install.

**What landed:**

- **2a — `src/CLAUDE.md`.**
  - `### Never` item 7, with items 1–6 byte-identical. It is the first multi-sentence `### Never` item, as D1's pattern note said it would be.
  - An explicit-yes agreement sentence after "one agreement per command".
  - A non-pick sentence at the fix-or-file offer.
  - The Hard Gates list and `storage-rules.md` are untouched (D5).
- **2b — `research/main.md` and `discover/main.md`.**
  - The intake confirmation calls, the no-exclusions rule (D4b) and the new heading quote.
  - Delegated rubric dimensions: `--state Partial`, with the value prefix "Model inference — the user delegated: ".
  - Conflict `delegated-*`, the drift note, design reference → none, and the save question → `Don't save`.
  - research: the cost gate, the mode flip, and all three Phase 2.4d prompts.
  - discover: the coverage exit and the verdict-rule-D text.
- **2c — `specify`, `spec-check`, `plan`, `grill` and `breakdown`.**
  - specify: the delegated decision point via `--delegated-reply`, and the Step 5.1 docs.
  - spec-check: a non-pick → no pick, no seed, and the routes named. PHASE 7 now routes a `Revise spec` CROSS-pick, which writes no seed, to `/devforge:plan` or a spec-check re-run instead of the blocked `/devforge:specify` (D2's amended spec-check row).
  - plan: the `**Defaults applied**:` line.
  - breakdown: the `**Grill**:` line, as amended at D6.
  - grill: a 7.2 non-pick → no pick, no seed. The matching re-entry option's description shows its seed inputs.
  - Re-asks were added at plan's §6 escalation and at grill's bounded-loop escalation.
- **2d — `implement` (plus `references/crash-recovery.md`, `references/forcing-functions-gate.md` and `references/review-loop.md`), `fix`, `finalize`, `review` and `verify`.**
  - The named arms: `stop` / `manual` / no squash / neither / `none`.
  - The Stage-A judgment item keeps option 1 and records "shape not confirmed by the user — delegated". The carrier differs per lane; see the build-time decisions below.
  - The composition templates hint the pending note.
  - fix's bounce sentence is byte-unchanged. ⚠ The live sentence reads `An "Other" answer, …` with double quotes. This document's fact 12 and the Phase 2 Verify render it with single quotes inside their own double-quoted italics, so grep `writes NO seed`, not the quoted form.
- **2e — setup and standalone commands.**
  - `report-bug` / `report-ticket`: the model-invoked path takes only the user's own words (D7).
  - `pr-review`: the skip arms. The NDA reminder no longer claims consent (OQ-5).
  - `audit`: the cost guards end the turn.
  - `init-forge`, `configure` (with `references/q11-tiers.md` and `references/q12-ac.md`) and `constitute` (D9, OQ-4):
    - Delegated defaults are named.
    - A delegation typed as free text is never stored as a value.
    - Q-domain → zero entities.
    - 6.2 → `cancel`, and "user-acknowledged ship-as-is" appears only after `ship`.
    - prune-agents falls back to SKIP.
    - The configure and constitute Phase 3 fallbacks warn "WITHOUT your confirmation".
  - `generate-docs`: a verified no-op.

**Tests:** the live-spec tests (reachability, memory-lane, emitter, per-package) were green after every sub-phase. ⚠ The per-row grep list this phase's Verify asks for is not reproduced in this document. The recorded evidence is the per-sub-phase instruction-reviewer passes plus those tests.

#### Build-time decisions — recorded 2026-09-18

These are the choices the build made where the plan text was silent or said something narrower. Each item names the decision it extends. None was put to the maintainer except D9's Q10 exception, which is recorded at D9 and is not repeated here.

1. **Free-text follow-ups (2e, extends D9's free-text bullet).** Some setup follow-ups appear only after the user has rejected the offered candidates. A delegation there → ask once more, then end the turn saving nothing.
2. **Q11 with the recommended alias hidden (2e, extends D9's first bullet).** When the availability probe hides the recommended alias, "apply the recommended value" has nothing to apply. A delegation then takes the first offered option.
3. **Re-asks at the two escalations (2c, D2).** plan's architect §6 Out-of-Scope escalation and grill's bounded-loop escalation each gained the one re-ask before their named arm.
4. **The Stage-A note's carrier on each lane (2d, OQ-6).** OQ-6 named the task's Completion Notes. implement records the note in `mark-complete --notes`, and fix's cold lane records it in `close-bug --fix-notes`. fix's feature lane has no notes carrier, so there the note goes in the Stage-B summary shown to the user rather than into a file.
5. **The spec-check routes (2c, D2).** See D2's amended spec-check row: `/devforge:plan` or a spec-check re-run, never the blocked `/devforge:specify`.
6. **research `scope` passes the bare label (2b, D3).** Every other delegated rubric value carries the prefix "Model inference — the user delegated: ". research's `scope` passes the bare label, because a prefix would bypass its `"one place"` evidence gate. The reason is stated at the site.
7. **Unified quote escaping (Phase 1, D4a).** D4a's sketch rendered the reply in single quotes. What shipped renders it in double quotes, with an embedded `"` escaped as `\"`. All three helpers — research, discover and specify — now escape the same way: backslash first, then `"`, backtick, `*`, `_` and `|`.
8. **discover sets the override to False explicitly (Phase 1, OQ-3).** OQ-3 said `override_recorded` "stays false". The build sets it to False EXPLICITLY, so a stale True left by an earlier plain `--accept-gaps` is overwritten.

### Phase 3 — Docs sweep

**Route: instruction-author → instruction-reviewer** for every `src/` and plan-document edit.

- **`CHANGELOG.md`** — create `## [Unreleased]` if it is absent. Verified 2026-09-18: absent, with `## [2.0.11] - 2026-09-18` as the top entry. ⚠ Plan 97's Phase 3 also creates it, so **verify at build** rather than trusting this line.
- **`DEVELOPMENT-STATUS.md`.**
- **Repo `CLAUDE.md` index one-liner → the DONE shape.** The one-liner is added at DRAFT time by the orchestrator, not by this phase. **Also a `PLAN-STATUS-ARCHIVE.md` entry.**
- **Dated one-sentence in-place notes, never a rewrite:**
  - `26-REINTRODUCE-FIX-PLAN.md` — fix's bounce rule is generalized.
  - `23-ADVERSARIAL-GRILLING-PLAN.md` / `85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md` — the grill 7.2 non-pick arm.
  - `62-SMT-REQUIREMENTS-CONSISTENCY-PLAN.md` / `82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md` — the spec-check 5.2 non-pick arm.
  - `FINDINGS.md` finding 2 — the attribution half is handled; the per-dimension justification is still open.

#### Verify

- `grep -n "98" CHANGELOG.md DEVELOPMENT-STATUS.md CLAUDE.md PLAN-STATUS-ARCHIVE.md FINDINGS.md` plus the plan files above shows the plan number at each site this phase edited.
- The `CHANGELOG.md` entry states the honest bound: **a model-judgment rule plus per-site sentences — NOT mechanical detection of a delegation.**
- Every checked site is recorded as an **edit or an explicit verified no-op**. An unrecorded no-op is indistinguishable from an unchecked site.

#### Phase 3 build record — 2026-09-18

**Route: instruction-author wrote this sweep; instruction-reviewer then reviewed all of it.** Docs only: no Python and no test. **The Phase 3 docs commit follows this sweep.**

**instruction-reviewer outcome: SHIP-READY, with 1 nit, fixed.** The nit was this block's route sentence, which read as a completed review before the review was recorded.

**This plan document, edited in this sweep:**
- the `**Status**:` line;
- the Phase 1 and Phase 2 build records and the build-time decisions list;
- four dated in-place amendments at the decisions they correct: D2's count of THREE with Trap 2, D2's spec-check row, D5, and D6;
- D9's post-ratification Q10 amendment, with Phase 4 anchor 8;
- `## Residuals (found during the build, not fixed)`;
- short dated notes at the close record's D9 and OQ-8 lines, Trap 8, the build order, and `## When resuming work` steps 3 and 5.

**The rest of this phase's list — each site an edit or an explicit verified no-op, as this phase's Verify requires:**

| Site | Outcome |
|---|---|
| `CHANGELOG.md` | **EDIT** — a new `## [Unreleased]` section was created, because none existed. It carries one entry, which states the honest bound. |
| `DEVELOPMENT-STATUS.md` `## Key Design Decisions` | **EDIT** — item 19 was added. Item 2 ("Hard gates at every phase transition") was kept and a clause appended: the approval questions are explicit and a reply that picks nothing never approves, while the `Approved` status on `spec.md` / `plan.md` is written when the next command runs (implicit approval by invocation, kept by D5). |
| Repo `CLAUDE.md` | **EDIT** — the plan-98 index line now has the DONE shape. |
| `PLAN-STATUS-ARCHIVE.md` | **EDIT** — the plan-98 entry was added after plan 96's. |
| `26-REINTRODUCE-FIX-PLAN.md` | **EDIT** — a dated note after D7. |
| `23-ADVERSARIAL-GRILLING-PLAN.md` | **EDIT** — a dated sub-bullet under D9. |
| `85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md` | **EDIT** — a dated note at the end of D5. |
| `62-SMT-REQUIREMENTS-CONSISTENCY-PLAN.md` | **EDIT** — a dated note after D5. |
| `82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md` | **EDIT** — a dated note in D5, after "Auto-accept semantics". |
| `FINDINGS.md` finding 2 | **EDIT** — a dated note. |
| `README.md` | **VERIFIED NO-OP — not edited.** A case-insensitive grep for `approv` / `delegat` / `Other` returns seven lines (5, 34, 57, 71, 73, 74, 79), and none states anything this build falsified. The three `other` hits (34, 71, 73) are ordinary English. 74 says `/devforge:plan` works "from the approved spec", which the kept flip still makes true. 79 is the `APPROVED` verdict token. Lines 5 (*"Every phase transition needs your explicit approval"*) and 57 (*"Each arrow is a user-approved gate"*) make the same claim as `DEVELOPMENT-STATUS.md` item 2. Their imprecision about the implicit `Approved` flip predates this plan, which kept that flip (D5). |

### Phase 4 — Consumer e2e — DEFERRED, user-driven HARD GATE, NOT run

**Everything above is build-verified, NOT consumer-validated. "Done" never means Phase 4 passed.** The anchors are known-answer cases and are **scored in PAIRS**: a rule that refuses everything passes the delegation half and fails the explicit half.

1. **research intake, delegation:** reply "you decide" twice → the report says `NOT confirmed`, and no later message says "you confirmed". **PAIRED WITH 2.**
2. **research intake, explicit pick:** an explicit `confirm` → today's flow, and the echo carries no exclusion the prompt did not state.
3. **grill 7.2, delegation:** "you decide" twice → no `grill-seed.json`, and the message says the disposition is still the user's. **PAIRED WITH 4.**
4. **grill 7.2, explicit pick:** an explicit `Revise plan` on a REVISE-PLAN recommendation → the seed is written as today.
5. **specify decision point:** "you decide" → §8 shows `[default applied]` naming the delegation, and Step 5.1 lists it.
6. **specify approval — scored as a pair within this anchor.**
   - **(a) Delegation:** "you decide" twice → `cancel`, and the spec stays Draft. A later `/devforge:plan` invocation still flips it to Approved, by the maintainer's accepted design (D5), so **that flip is NOT a failure of this anchor.**
   - **(b) Explicit pick:** an explicit `approve` at specify behaves as today.
7. **finalize:** "you decide" twice → no squash.
8. **configure Q10 — scored as a pair within this anchor.** ⚠ *Added 2026-09-18 (build), for D9's post-ratification Q10 exception.* **Both halves run with `git config user.name` SET.** With it unset, no `Run by:` line is stamped under either answer, and half (a) would pass vacuously.
   - **(a) Delegation:** Q10 answered with a delegation → `No` is saved and named among configure's delegated values, and no later pipeline run stamps a `Run by:` line into `spec.md`, `plan.md`, `research-report.md` or `summary.md`.
   - **(b) Explicit pick:** an explicit `Yes` behaves as today: the commit-message footer, plus a `Run by:` line naming the user's `git config user.name` in those four documents.

#### Verify

- All seven anchors are scored **explicitly** — stated, not summarized — with each pair scored together. ⚠ *Amended 2026-09-18 (build): all EIGHT — anchor 8 was added for D9's Q10 exception.*
- **If an anchor fails**, record the negative with the artifacts, and name the mechanism before proposing anything. A laundered pick is a D1/D2 finding, an unnamed delegated default is a D3/D6 finding, and a stall on an explicit pick is a D1 over-reach finding. **They have different fixes.**
- **A clean run is evidence that the rules behave on planted replies, NEVER evidence that the gap cost anything.** The only observed failure is on a frozen install, and it cannot be re-run here.

---

## Residuals (found during the build, not fixed)

Each item below was found during the build and deliberately left unfixed. All of them are pre-existing unless the item says otherwise. ⚠ Line digits drift — grep the quoted text.

1. **Seed deletion claim.** `research/main.md` and `discover/main.md` claim that the next `/devforge:grill` run deletes seeds. Grill's spec and the `_grill/` code delete nothing.
2. **Grill's bounded-loop escalation.** The text writes the seed first and escalates after. It does not say whether the escalation replaces the seed write.
3. **research mode re-detection.** Mode detection re-runs `detect-mode` without `--override`, which overwrites a Phase-1 mode-flip choice, whether the user's or the model's.
4. **Inline reply arguments.** `--reply "<verbatim>"` and `--delegated-reply "<verbatim>"` pass user text inline in a shell argument. That is the same inline hazard plan 95 recorded for rubric answers. The two flags are this plan's. The hazard class is not, and this plan does not widen it in kind.
5. **spec-check PHASE 5.2's `Revise spec` option description** promises a `/devforge:specify` re-run that a cross-pick cannot deliver.
6. **fix PHASE 4** never tells the loop to record judgment items, although its Stage A depends on them.
7. **OPEN-LOW prompts left to the always-on rule, with no per-site sentence** — the bound D2's counter-argument and the Non-goals state:
   - research: the topic prompt and the coverage exit;
   - discover: the references prompt;
   - specify: the default-branch, pick-other index and Figma-screenshot follow-ups;
   - pr-review: the paste-body and file-path follow-ups;
   - generate-docs: the cost gate.
8. **The repo `CLAUDE.md` "Where to find what" router** still says `_PROMOTED` (20 names) and 16 model-invocable. The live tree has been 21 / 17 / 4 since plan 95. This is not this plan's residual, and the maintainer was told.

---

## Non-goals

- **Mechanical detection of a delegation.** It is natural language, and it stays model judgment — the stated bound.
- **Per-site sentences at OPEN-LOW points.** D1 covers them; its second default ends the turn there with nothing written.
- **Relocating or relabelling the implicit Approved flip** — accepted by the maintainer 2026-09-18 (D5).
- **Changing who owns any disposition, or any gate predicate** (presence / freshness / adversary status).
- **Auto-mode semantics.** Unchanged; auto mode already marks its defaults.
- **FINDINGS.md finding 2's per-dimension justification.** It stays open.
- **Provenance and picker fields.** No provenance field on `plan-handoff.json`'s `DecisionRow`, and no picker field on `ReEntrySeed`. Under D2 a seed exists only after an explicit pick.
- **Pre-displaying text before Stage B.** Not for `/devforge:implement` / `/devforge:fix` Completion Notes or fix-notes, and not for spec-check / fix seed text, which is composed from material the user was just shown.
- **configure / constitute Phase 3's counts-only bulk echoes**, beyond OQ-4's warning text.
- **Any `disable-model-invocation` change, any constitution edit, back-porting, and the frozen benchmark install.**

---

## Context for next session

⚠ **Evidence class, repeated: ONE observed consumer incident at ONE site (`/devforge:research` Phase 0.5), plus a grep-verified, read-only audit of 146 interaction points. Every other site is a PREDICTED gap. Nothing was measured.** The evidence is held outside this repo by the maintainer and is not quoted here. ⚠ All line digits drift — grep the quoted text.

**The one sentence that governs everything here:** a reply that picks nothing is not the user's pick. At a run decision it is re-asked once and then takes the command's named no-write arm. At a content question the model answers and says so. Nothing mechanical detects the reply, and **no part of this plan is a gate.**

**Trap 1 — citing "Never guess" as already covering this** (fact 4). After a delegation the model is not unsure what the user wants, so that rule does not fire.

**Trap 2 — a "no-write arm" that writes.** Check every D2 row. A no-write arm writes nothing except a record that makes the missing pick visible, and exactly THREE sites write one: the research/discover intake UNCONFIRMED record (D4), the discover coverage-exit gap records with no verdict override (OQ-3), and the Stage-A *"shape not confirmed by the user — delegated"* Completion Note (OQ-6). None of them attributes a decision to the user. ⚠ **Amended 2026-09-18 (build):** that count covers RUN-DECISION arms only. The specify `spec_type` `accept` arm is a content answer that keeps the pre-seeded value, and the design-source `None…` arm writes `set-design-source`. Both write, both sit outside the three, and neither attributes anything to the user (see D2's note).

**Trap 3 — Class B turned into refusal.** Refusing to answer after a delegation turns the rubric into friction. Class B is attribution, not refusal.

**Trap 4 — defaulting to the recommended option because it is recommended.** That IS the incident.

**Trap 5 — a re-ask loop.** Exactly one re-ask, never a loop.

**Trap 6 — reading a predicted row as observed.** The incident evidences ONE site; every other row is predicted.

**Trap 7 — leaking the client.** No client identifier and no benchmark path in any tracked file — ever.

**Trap 8 — a clobbered edit on a stale read of a file plan 97 also edits.**
- **The four shared files.** Plan 97 (`97-WRAPPER-MODE-FRAMEWORK-MENTION-GUARD-PLAN.md`, DRAFT) proposes edits to `src/commands/implement/main.md`, `src/commands/fix/main.md`, `src/commands/verify/main.md` and `src/commands/implement/references/crash-recovery.md`. All four are in this plan's sub-phase 2d.
- **The shared docs site.** Both plans' Phase 3 create `CHANGELOG.md`'s `## [Unreleased]` section, so the second finds it present.
- **The rule.** **Whichever plan ships second reads those files LIVE and re-derives its own edits, never from a pre-computed diff** (the plans 89/90 coordination precedent). The rule binds the READ, not the edit.
- ⚠ **Recorded 2026-09-18 (build):** this plan's sub-phase 2d landed first (`78c8d17`), while plan 97 was still a DRAFT with nothing built. Under the rule above, plan 97 is therefore the plan that ships second, and it owes the LIVE read of the four shared files.

**Also remember: unclassified ⇒ Class A,** and a Class-A question with no named option ends the turn with nothing written on a second non-pick (D1's second default).

**Also remember: D5 is RESOLVED as no change.** The PHASE-0b `flipped` / `already-approved` / `inserted` tokens and every `cmd_check_status_and_flip` stay untouched.

**Build order, and it is forced rather than preferred:**
1. **Phase 1 (Python) first.** Phase 2 names verbs and flags that must exist: `record-intake-confirmation`, `--delegated-reply`, `--no-verdict-override`.
2. **OQ-8's `claude-code-guide` check** precedes Phase 2.
3. **Phase 3 last**, because it records what the earlier phases actually did.

⚠ *Recorded 2026-09-18 (build): sub-phases 2a, 2d and 2e landed before Phase 1, in `78c8d17`. None of them names a Phase-1 verb or flag — only the research, discover and specify specs do, and those are 2b and 2c — so the forced part of this order held.*

**File anchors:**

- `src/commands/research/main.md` — Phase 0.5 Step 2 and Step 3; the Phase 1 per-dimension protocol; Step 4.1.
- `src/commands/discover/main.md` — the same sites, plus the coverage exit and verdict rule D.
- `src/devforge/lib/_research/_cmds_intake.py` and `_discover/_cmds_intake.py` — the heading.
- `_research/_cli.py` and `_discover/_cli.py` — `record-conflict-resolution` and the `--accept-gaps` help.
- `_discover/_cmds_scope.py` — `override_recorded`.
- `_specify/_cmds_phase2.py` — the mode gate.
- `_specify/_render.py` — the §8 branches and the Step 5.1 truncation.
- `plan_helper.py` / `breakdown_helper.py` `cmd_check_status_and_flip`, `src/devforge/storage-rules.md` Status Tracking, and `src/CLAUDE.md` Hard Gates — **read-only here** (D5 RESOLVED: the implicit flip stays).
- `src/CLAUDE.md` — `### Never`, the *"once the user agrees, run it directly"* agreement rule and the fix-or-file offer.
- `src/commands/grill/main.md` PHASE 7.2; `src/commands/spec-check/main.md` PHASE 5.2; `src/commands/implement/main.md` PHASE 7; `src/commands/finalize/main.md` 3.3.
- `src/commands/fix/main.md` — the closed bounce sentence, **read-only reference**.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation.
2. **Check `## Phase 0 close record` first.** If it still reads *Pending*, nothing is ratified and **no build phase may start**.
3. **Read the live files before editing.** Line digits in this document drift, so **grep the quoted text, never the digits** — `Is this interpretation right?`, `(or any other reply)`, `Requirements (what you asked for)`, `rejects default-applied setter`, `user-chose`, `User explicitly accepted`, `override_recorded`, `auto-injects 'Other'`.
   - ⚠ *Recorded 2026-09-18 (build):* two of these strings are gone from `src/` by design: `Requirements (what you asked for)` (D4c) and `User explicitly accepted` (D8). Zero hits for them is the built state, not a regression. In `_specify/_cmds_phase2.py` the mode-gate message is split across two string literals, so grep `default-applied setter` to reach it there.
4. **Check plan 97's state before sub-phase 2d or Phase 3** (Trap 8).
5. **Route every edit through the house flow:**
   - instruction-author → instruction-reviewer for every markdown edit;
   - python-engineer → python-reviewer for every Python edit;
   - **`claude-code-guide` for every Claude-Code-integration fact** (OQ-8 is owed before Phase 2 — discharged 2026-09-18).
6. **Commit by explicit path, never `git add -A`.** Another session may be mid-build in the same checkout.
7. **After each phase, cross-check.** Grep every identifier, verb, flag, heading and token touched, and fix any dangling reference in the SAME change.
8. **Keep the evidence class attached.** Any summary of this plan repeats it: ONE observed site, a read-only audit, every other site predicted, nothing measured.
