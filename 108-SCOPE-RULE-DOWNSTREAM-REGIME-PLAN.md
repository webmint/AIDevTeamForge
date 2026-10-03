# 108 — Scope Rule Downstream Regime Plan

**Created**: 2026-09-21
**Status**: **✅ DONE (build) 2026-10-02 — Phases 1–4 BUILT (Phase 2 a verified no-op, no commit); no consumer e2e is proposed (`## Honest bounds`). Build-verified, NOT consumer-validated: "built and build-verified" is the ceiling of every claim here. As of 2026-10-02 the maintainer has not closed the plan.** *(corrected 2026-10-02 — Phase 3: until then this line opened with the Phase 0 close status that follows, kept as written with its R1–R4 markers; its "Build phases MAY start. NOTHING IS BUILT.", its "this plan's build is next" and its "still NOTHING BUILT" were true until Phase 1's commit `b122abe`)* *(added 2026-10-03 — wording amendment: after the build, an explicit maintainer pick changed one phrase of D2's ratified wording — item 17's "with that reason" now reads "with the reason you named", 197 words — `### Phase 0 close record`, **Amended after the build by an explicit maintainer pick — D2's wording, one phrase (2026-10-03)**)* Commits: Phase 0 close `fddbc7d` — the plan's creation commit (2026-09-23), which carries the close dated 2026-09-21; re-check `79d556c` (R1–R4, plan text only); Phase 1 `b122abe`; Phase 3 — the ledger commit, which carries this line. Phases 2 and 4 made no commit: Phase 2 is a verified no-op and Phase 4 a test run. `## Build record — 2026-10-02` records each phase's commit, tests and review, the Phase 2 sweep site by site, the concurrency note and the residuals. ⚠ **The close, the re-check and the build each leave the evidence class unchanged** (`## Origin & evidence`). **Phase 0 CLOSED 2026-09-21 by a blanket maintainer directive — D1–D7 and OQ-2 ratified as recommended, OQ-1 MOOT by D2's outcome. Build phases MAY start. NOTHING IS BUILT.** Every decision and both open questions keep their recommendation and their strongest counter-argument, unshortened; see `### Phase 0 close record`. ⚠ **The maintainer works the open plans in NUMERIC ORDER, and 101, 102, 104, 105, 106 and 107 are all DONE (build) — 101 on 2026-09-23, 102 on 2026-09-24, 104 on 2026-09-25, 105 on 2026-09-27, 106 on 2026-09-28, 107 on 2026-10-01 — so under that order this plan's build is next.** *(corrected 2026-10-02 — R4: this read "101, 102, 104, 105, 106 and 107 are open and lower-numbered, so this plan's build comes after theirs", true on 2026-09-21)* ⚠ **Every `file:line` here was verified on 2026-09-21 and WILL have drifted by then — `## When resuming work` step 3's re-verification is the FIRST action of any build session, not an optional one.** ⚠ **A live-tree re-check against `HEAD` `8e61645` is recorded in `### Re-check against the live tree (2026-10-02)`: four R-items, the drifted digits refreshed, nothing ratified and still NOTHING BUILT — and step 3 still comes first.** *(added 2026-10-02 — R1–R4)* ⚠ **Numbered 108 because 100, 101, 102, 104, 105, 106 and 107 are taken in this checkout as of 2026-09-21 and the gap at 103 was vacated by an earlier renumbering — 103 is not a missing plan.** ⚠ **Other sessions work in this same checkout and may take 108 first; a resuming session re-checks the number before trusting it.**

An always-on rule in the emitted `CLAUDE.md` sets a universal default that one lifecycle stage structurally cannot execute, and the command at that stage says the opposite in its own text. **The fix moves the RULE, not the command** — and it moves it by giving the fact a single owner rather than by adding a second regime, because the rule restating a per-command outcome is what produced the clash in the first place (`### Root cause`).

---

## Origin & evidence

⚠ **Evidence class, to be repeated in every summary of this plan: a contradiction read directly out of two files in THIS tree — NO consumer incident, NO measurement, NO run.** The clash was surfaced by a consumer pipeline run relayed from outside this repo; everything below was re-derived here by grep on 2026-09-21. **This plan names no client, install, repo, branch, ticket or product from that run.** The shape, and only the shape: a run reached the `/devforge:plan` surface arm, read the emitted `CLAUDE.md` rule beside it, and could not satisfy both.

⚠ **Line digits drift — grep the quoted text, never the digits.** Every `file:line` below was read against this tree on 2026-09-21. *(added 2026-10-02 — R4: the digits R4 corrects were re-read on 2026-10-02, and each carries an R4 marker naming the digit it replaced; R4 also lists the digits it re-verified unchanged)*

### The verified anchors (2026-09-21)

**Anchor A — the always-on default.** `src/CLAUDE.md:230`, `## Key Rules` → `### Always` item 17, **Scope follows what the user sees**. Its last three sentences, verbatim:

> Deciding it yourself — handed back or never asked — cover it unless you can name what the user would see differently without it; record any exclusion as yours, with that reason, and tell the user. A surface that only shares code is neither covered nor raised. Ask a present user about a surface you suspect but cannot evidence; deciding yourself, leave it an open question, never silently covered or excluded.

The first of those three is the sentence that matters: **the model deciding alone — handed back or never asked — covers the surface.** *(added 2026-10-02 — Phase 3: this is item 17 as it read before the build; Phase 1's `b122abe` replaced that first sentence in place with D2 (c)'s three sentences, and the other two stand byte-identical — see `## Build record — 2026-10-02`)*

**Anchor B — the command's opposite outcome.** `src/commands/plan/main.md:434` *(corrected 2026-10-02 — R4: was `:413`)*, Phase 1.3 sub-question 6, **the surface arm — the SECOND non-decision arm in that sub-question.** ⚠ **The FIRST non-decision arm in the same sub-question concerns a §6 entry and is NOT in conflict; see the trap.** Verbatim:

> A reply to that escalation that decides nothing — one that hands the decision back to you, or free text that neither covers the surface nor leaves it out — is not a decision: ask once more, and if the second reply again decides nothing, the surface stays uncovered — tell the user that the surface stays uncovered and that covering it needs a revision of the spec, add it to the plan's Risk Assessment as: "<surface> (<what the user sees there>) shows the feature, but the spec does not cover it — left uncovered; the user did not decide it", and list it on the Phase 3 approval summary's `**Unconfirmed exclusions**:` line.

### The three divergences — three, not one

They are stated as three because a fix that closes one leaves the other two standing.

1. **Default.** `cover it` (Anchor A) versus `the surface stays uncovered` (Anchor B).
2. **Attribution.** `record any exclusion as yours` (Anchor A) versus `the user did not decide it` (Anchor B).
3. **Reason.** Item 17 requires a **named user-visible difference** behind any exclusion the model makes; the `/devforge:plan` arm requires **none** — it records the non-decision itself as the reason.

### Why the clash cannot be resolved by reading harder

**Anchor C — the other always-on rule points the other way.** `src/CLAUDE.md:239`, `### Never` item 7, **Never record your choice as the user's**, says:

> At a question that decides what the run does, ask the same question once more, and on a second such reply take the option the command names for that reply; where the command names none, end the turn having written nothing.

**That sentence has two branches, and `/devforge:plan` is in the first: it names an option for that reply, and the option it names is `uncovered`.** ⚠ **The second branch — *"where the command names none"* — governs a command that names no outcome, and D2's reason 3 under the "Why (c)" list is where that case matters; it is stated there once and nowhere else.** **So `Never` 7 points at the command while `Always` 17 points at `cover`. Two rules of equal authority in the same emitted file point in opposite directions** — there is no reading of `CLAUDE.md` that satisfies both, and a reader who "resolves" it by leaning on one has simply picked a side without saying so.

**Anchor D — the constitution does not arbitrate.** `src/constitution.md:238`, `### 6.1 Minimal Changes [universal]`, ends:

> Which user-facing surfaces a change covers is set by what the user sees, never by the code that reaches them: a bug fix changes the bug everywhere the user sees it, a feature changes every surface that shows it, and "as little code as possible" governs how each of those surfaces is changed, never which of them count.

That sentence sets **WHICH surfaces count**, never **what to do on a non-decision**. `### Always` item 2 makes the constitution outrank `CLAUDE.md` (*"Constitution is law"*), and outranking settles nothing here, because §6.1 carries no hand-back default to outrank the conflicting one with.

### The structural reason `/devforge:plan` cannot simply obey item 17

**Anchor E.** Sub-question 6 states the limit in its own text, in the sentence that introduces the surface escalation:

> the spec defines what the feature covers, and this command adds no affected area and no acceptance criterion to `spec.md`

Covering a surface the approved spec does not cover therefore requires a revision of that spec. **"Cover it" is not an action available at that stage.** This is the whole reason the fix moves the rule rather than the command: obeying item 17 at `/devforge:plan` would mean writing into an artifact the command is forbidden to write into.

### The second hole, in the OPPOSITE direction — and the strongest argument for this plan

**Anchor F.** `grep -rln "user-facing surface\|shows the feature" src/commands/breakdown src/commands/implement src/commands/fix src/commands/review src/commands/verify` returns **no hits** (verified 2026-09-21; each of the five directories greps to zero independently). *(corrected 2026-10-02 — R1: true on 2026-09-21; on 2026-10-02 the grep returns ONE file, `src/commands/verify/main.md` — its single hit at `:207` is the **Changed files** bullet of the ac-verifier brief, added by plan 107 after this plan was written — and `breakdown`, `implement`, `fix` and `review` still grep to zero. That hit tells `/devforge:verify` how to read the construction site of a surface an AC already names, never what to do with a surface no AC names, so the conclusion below stands — see R1)* **Those five commands carry no surface rule of their own, so a surface met there is governed by the always-on rule ALONE — and the always-on rule currently says `cover it`.** At `/devforge:implement` that reads as a mandate to build a surface the approved spec does not cover.

⚠ **Label this honestly in every summary: PREDICTED from the text, never observed. Nothing was measured.**

**The shipped record already recognizes the exposure, which is what makes the prediction more than a reading.** `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md:297`, inside its D5, states:

> Item 17's "never asked" arm still governs the commands that decide without asking: research's Step 2b classification, `/devforge:implement`, `/devforge:fix`, `/devforge:review` and `/devforge:verify`.

And `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md:250`, inside its D8, states the same disposition as a deliberate non-edit — *"discovering a new surface there rides the always-on rule alone"* — with a named revisit trigger at `:251`: *"an observed exclusion at one of those stages."* *(corrected 2026-10-02 — R4: was `:248` and `:249`)* ⚠ **That trigger has NOT fired, and this plan is not it firing.** No exclusion was observed at any of those stages. What was found is that **the rule those commands ride contradicts itself**, and it was found at a different command entirely — `/devforge:plan`, which plan 99's D8 list does not name because that command has an arm of its own.

⚠ **Two different lists.** Plans 99 and 100 name **four** commands (`/devforge:implement`, `/devforge:fix`, `/devforge:review`, `/devforge:verify`). Anchor F's grep covers **five**, adding `/devforge:breakdown`, which greps to zero as well and which neither plan's list names. **Do not conflate the lists when re-deriving this.**

### Provenance — both sides landed in the same build

**Anchor G.** `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md`'s `**What landed:**` list records them as items 1 and 5 of one build:

- Item 1 (`:460`): *"**1a — `src/CLAUDE.md` (D1, as amended by D10).** `### Always` item 17, **Scope follows what the user sees**: D10's text, 152 words in six sentences, the longest item in either list. Items 1–16 are byte-identical."* *(corrected 2026-10-02 — R4: was `:458`)*
- Item 5 (`:490`, third bullet at `:495`): *"no decision → ask once more; on a second reply that again decides nothing, the surface stays uncovered, with a Risk Assessment row, an entry on the PHASE 3 line, and the user told."* *(corrected 2026-10-02 — R4: was `:487` and `:492`)*

`100-SCOPE-RULE-FOLLOW-UPS-PLAN.md`'s D10 escalation table re-recorded the arm at `:375` — *"the surface stays uncovered; a Risk row and `**Unconfirmed exclusions**:` (plan 99)"* — and its D5 (`:293`) separately decided **NO edit** to item 17, for an unrelated reason (how "a present user" reads), recording at `:299` that *"`src/CLAUDE.md` stays byte-identical; Phase 3's Verify checks it."*

**Neither plan names the clash.** Plan 99's `## Residuals (found during the build, not fixed)` lists six items and this is not among them; plan 100's decisions run D1–D14 and none of them is this. ⚠ **Both plans are DONE and CLOSED: this plan amends neither of them and edits neither file.**

### The contradiction also shipped inside ONE changelog entry

**Anchor H.** `CHANGELOG.md:24` *(corrected 2026-10-02 — R4: was `:14`)*, the plan-99 entry under `## [2.0.12]`, carries both halves:

> when the model decides it, the surface is covered unless the model can name what the user would see differently without it, and any exclusion is recorded as the model's own

and, later in the same entry:

> no decision after one re-ask → the surface stays uncovered, with a Risk Assessment row, the PHASE 3 line and a word to the user

⚠ **That entry is the historical record of what shipped and is NOT rewritten by this plan.** `PLAN-STATUS-ARCHIVE.md:262` *(corrected 2026-10-02 — R4: was `:256`)*, inside the plan-99 entry under `## Entries`, carries the same cover-default half (*"evidenced → cover unless it names what the user would see differently"*) and is likewise NOT rewritten.

### The derivative that DOES get amended

**Anchor I.** `DEVELOPMENT-STATUS.md:116` *(corrected 2026-10-02 — R4: was `:114`)*, numbered item **20**, repeats the universal default:

> when the model decides it, the surface is covered unless the model can name what the user would see differently

⚠ **Item 20 there, item 17 in the emitted file — do not conflate the two numbers.** It must move in the same change or it becomes the next session's ground truth.

### The emission path

**Anchor J.** `src/manifest.json:27-29` *(corrected 2026-10-02 — R4: was `:26-28`)* maps the source to the target — the three lines of that object, quoted as they read: `"source": "generated:coreLLM"`, `"target": "CLAUDE.md"`, and

> "description": "Sourced from src/CLAUDE.md. Three-way merge against .devforge/template/CLAUDE.md preserves project customizations."

So the contradiction is **live in consumer installs**, and the fix reaches an install only through `update.sh`'s three-way merge.

### Root cause

**The defect is not a wrong word in item 17. It is an always-on rule restating a per-command outcome, with no single owner for the fact.**

Item 17's `cover it` is **a restatement of `/devforge:specify`'s default.** The command carries it at `src/commands/specify/main.md:399` (*"The value is `cover <surface>`, unless you can name what the user would see differently because that surface is left out"*), and item 17 carries a second copy of the same norm. **Two copies agreed for as long as `/devforge:specify` was the only stage that met a surface.** They stopped agreeing the moment a third stage appeared with an arm of its own (Anchor B) — not because either copy was written badly, but because a copy has no way to know the other one has grown a case it does not have.

**The prevention is single ownership: the rule owns the invariant and the definition; the command owns the outcome.** `## Honest bounds` already records that nothing mechanical will ever catch a violation of item 17, and the same is true of a semantic contradiction between a rule and a command arm — **no check can be written for it.** De-duplication IS the prevention here, and it is the only one available.

⚠ **This is what disqualifies D2's candidates (a) and (b), and it disqualifies them on principle rather than on taste.** Both restate `/devforge:plan`'s OUTCOME inside item 17 — *"leave it uncovered, record that no one decided it, say a spec revision is needed"*. Adopting either would leave item 17 restating **`/devforge:specify`'s default AND `/devforge:plan`'s outcome**: three copies of one norm and **two** independent drift seams where there is one today. **A fix that adds a copy is a fix that schedules its own recurrence.** ⚠ **A future session must not read (a) and (b) as merely "less preferred wording" — they are rejected for reproducing the cause.**

### Re-check against the live tree (2026-10-02)

Every anchor in this plan was re-read against `HEAD` `8e61645` on 2026-10-02, after plans 101, 102, 104, 105, 106 and 107 — all DONE (build) — and the 2.0.12 release commit `e2a3862` had landed. **Each R-item below is recorded here AND at every site it touches, and every such site carries a dated `R<n>` marker** — `*(corrected 2026-10-02 — R<n>)*` where an existing sentence was wrong, `*(added 2026-10-02 — R<n>)*` where the text is new — so a reader who enters at any one site can find the item that changed it. **Where a sentence was wrong, its correction says what it was corrected FROM rather than overwriting it silently, and no counter-argument, trap, tripwire or honest bound is deleted or shortened by a correction.** **Ratified text is never rewritten:** the close record's quoted sentences, D2's quoted (c) text and the cells of the close record's outcomes table keep their 2026-09-21 words, and an `added` marker beside them says what changed. ⚠ **The re-check ratifies nothing, re-opens no decision, changes no outcome, builds nothing and changes no evidence class: a contradiction read out of this tree, no consumer incident recorded here, nothing measured, no run.** `### Phase 0 close record` stands as written. ⚠ **The digits inside each R-item were read on 2026-10-02 and drift like every other digit in this plan — grep the quoted text, never the digits.**

**R1 — Anchor F's grep is no longer zero: one hit, at `/devforge:verify`, about a surface an AC already names — so Anchor F's conclusion stands.** *(added 2026-10-02 — R1)* Anchor F's `grep -rln "user-facing surface\|shows the feature" src/commands/breakdown src/commands/implement src/commands/fix src/commands/review src/commands/verify` now returns ONE file, and `grep -rn` with the same pattern and directories returns exactly ONE hit: `src/commands/verify/main.md:207`, the **Changed files** bullet of the ac-verifier brief, which says the agent *"also reads, in every mode, the construction site of any user-facing surface an AC names, including code outside this `files` list"*. `breakdown`, `implement`, `fix` and `review` still grep to zero. The hit comes from `107-SURFACE-PATH-PROOF-PLAN.md`'s Phase 5, commit `2f6173d` (2026-10-01), which also added to `src/agents/ac-verifier.md:31` — `## Input` item 7, **Changed files** — *"When an AC names a user-facing surface, also read that surface's construction site — the code that builds, mounts, or registers what it depends on — in every mode, including code outside this list"*, and, at `:63` and `:71`, a `PARTIAL`-never-`PASS` verdict for a passing observation that the construction site of a surface the AC names contradicts. **Both sites concern a surface an AC already NAMES, and tell `/devforge:verify` how to READ it. Neither gives `/devforge:verify` a rule for a surface no AC names that it meets.** So Anchor F's conclusion — the five commands carry no surface rule of their own for a surface no AC names, and the always-on rule governs such a surface there ALONE — **stands**; only the literal *"no hits"* / *"each of the five directories greps to zero"* claim is corrected. ⚠ **The zero-hit claim was true when this plan was written; this IS drift — plan 107's Phase 5 landed on 2026-10-01, after this plan was written.** Corrected at: Anchor F's paragraph. Added at: D2's **Why (c)** reason 3, beside the sentence ending *"which is what Anchor F's grep shows"* — the hit asks nothing, so that sentence holds; Phase 2's `#### Deliverables` site list, which gains both sites as a re-read against the amended rule, a verified no-op expected; `### File anchors`, which lists them; and `## When resuming work` step 3, which says what the grep returns today.

**R2 — plan 104's run settled the cost D7's practical half leans on: it did not hold when this plan was written, and it holds from plan 104 on. D7's outcome stands, and D7 is NOT reopened.** *(added 2026-10-02 — R2)* D7's **The cost avoided** paragraph quoted plan 99's record that a §6.1 edit made both checks report §6.1 drift for installs constituted earlier — *"the third such finding, after plans 86 and 89"* — concluded that touching §6.1 again produces a fourth, and told a builder who leans on that cost to re-check what those two checks do today before quoting it. **This is that re-check.** `104-UNIVERSAL-SECTIONS-INTEGRITY-PLAN.md` (DONE (build) 2026-09-25), Phase 6, commit `087497c` (2026-09-25), established BY A RUN that one state built through the real CLI to match the canonical constitution exactly drew exit 2 and 32 findings, all MISSING, from the comparator as it stood before plan 104's fix, and exit 0 with zero findings from the fixed comparator. Plan 104's verdict on this plan's D7 sits at `104-UNIVERSAL-SECTIONS-INTEGRITY-PLAN.md:747`, under the bold lead-in **`108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`'s D7 — recorded, never amended.**, and reads, verbatim:

> Its premise was that a §6.1 edit costs *"a fourth drift finding for installs constituted earlier"*. Before plan 104 that cost was zero, because every constituted install already saw every universal rule reported MISSING. After plan 104 the cost is real for installs constituted after it — a genuine per-rule finding — and an install constituted before it sees a single `PRE_IDENTITY` line. **So the premise did not hold at the time; it holds from here on.**

`PRE_IDENTITY` is the finding kind `cmd_verify_universal_defaults` documents in its docstring (`src/devforge/lib/_constitute/_cmds_quality.py:150`, the kind at `:173`): when the consumer state has not one named rule, per-rule comparison is skipped and exactly one finding, `{"kind": "PRE_IDENTITY", "section": "*", ...}`, is reported. **The consequence for this plan.** D7's OUTCOME is unchanged — NO §6.1 edit — and the cost argument behind it now HOLDS: from plan 104 on, a §6.1 edit produces a genuine per-rule finding for installs constituted after plan 104, and an install constituted before it sees the single `PRE_IDENTITY` line either way. **What is corrected is the counting frame** — *"the third such finding"* and *"a fourth"*: the earlier findings, for plans 86, 89 and 99, were indistinguishable from a comparator artifact, and plan 104 records it as NOT established whether any particular install also had real drift. Plan 104 recorded this plan's D7 without amending it, and this re-check does not amend it either. Plan 99's cited line moved from `:460` to `:462` (R4), and plan 99 now carries plan 104's dated, additive amendment directly under that bullet (`99-…:463`). Corrected at: D7's **The cost avoided** paragraph; and `## Tripwires`' `src/constitution.md` bullet, whose STOP stands. Added at: the D7 row of the close record's outcomes table — a ratified cell, so its words stand and a marker follows them. `grep -n "fourth"` over this file, run before this section was written, found four hits: the three drift-cost sites R2 marks, and D2's *"34 is the fourth sentence"*, which counts sentences — none in `## Honest bounds`, `## Non-goals` or `### Traps`.

**R3 — Trap 1 is NOT in force: `src/CLAUDE.md` is clean, and its hunks were already committed when this plan was. The explicit-path discipline stays.** *(added 2026-10-02 — R3)* `git status --short` is clean on 2026-10-02 for `src/CLAUDE.md`, `CHANGELOG.md`, `DEVELOPMENT-STATUS.md` and `PLAN-STATUS-ARCHIVE.md`. The `### Format` commit-subject hunks Trap 1 describes — `[checkpoint] pre-task NNN` among them — are in the committed file; they landed in commit `e2a3862` (`chore(release): 2.0.12 — version bump, ledger sweep, two spec corrections`, 2026-09-23 12:09:31 +0300), 20 seconds BEFORE this plan's own commit `fddbc7d` (2026-09-23 12:09:51 +0300). **So Trap 1 was already stale when this plan was committed; its text was verified on 2026-09-21, two days earlier.** ⚠ **What stays in force:** other sessions still work in this checkout — several untracked plan files sit at the repo root — and `110-IMPLEMENT-AUTO-APPROVE-PLAN.md` (Phase 0 OPEN as read 2026-10-02) plans a later edit of `src/CLAUDE.md` in a different region (`110-…:145`). **So re-reading `git status` before staging, committing by explicit path and checking `git diff --cached --stat` after staging all stay mandatory, in every phase.** Trap 1's two routes — wait, or stage only the item-17 hunk through a patch — stay in the text as the procedure for exactly one state: `git status` showing `src/CLAUDE.md` dirty at build time. ⚠ **That is a condition on WHICH staging procedure applies, never an exit from the discipline: the `git status` read is unconditional.** Corrected at: Trap 1's heading; Phase 1's lead line; Phase 1's `#### Verify` staged-diff bullet; Phase 3's lead line; `## Tripwires`' last bullet; and `## When resuming work` step 6. Added at: the note opening Trap 1's body; Option LIFECYCLE-REGIME's closing ⚠ sentence and D2's **COUNTER to (c)**, each of which names a file another session is editing — both counters stand unshortened.

**R4 — line digits refreshed, and the sequencing and state sentences brought current.** *(added 2026-10-02 — R4)* Every quoted TEXT below was re-found; only the digits had moved. Each digit is corrected in place, and each corrected site carries one dated R4 marker naming the digits it replaced — **except inside the close record's outcomes table, whose cells are ratified text: there the 2026-09-21 digit stands and an `added` R4 marker beside it names the current one.**

| File | Anchor, and where this plan cites it | Was | Now |
|---|---|---|---|
| `src/commands/plan/main.md` | Phase 1.3 sub-question 6 — Anchor B; D2's **Why (c)** reason 1; D4 | `:413` | `:434` |
| same | the `**Unconfirmed exclusions**:` line's body — Phase 2's named check; `### File anchors` | `:640` | `:661` |
| `src/commands/specify/main.md` | the **Covering a user-facing surface takes two entries.** paragraph — D2's **Why (c)** reason 2; the D5 outcome row (ratified: `added` marker); Phase 2's D5 Verify; Trap 7; `### File anchors` | `:652` | `:658` |
| `CHANGELOG.md` | the plan-99 entry under `## [2.0.12]` — Anchor H; Option MOVE-THE-COMMAND | `:14` | `:24` |
| `PLAN-STATUS-ARCHIVE.md` | the plan-99 entry under `## Entries` — Anchor H; D6; the D6 outcome row (ratified: `added` marker) | `:256` | `:262` |
| `DEVELOPMENT-STATUS.md` | numbered item 20 — Anchor I | `:114` | `:116` |
| `src/manifest.json` | the `generated:coreLLM` object — Anchor J | `:26-28` | `:27-29` |
| `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md` | D8's disposition and its revisit trigger — Anchor F's record paragraph | `:248`, `:249` | `:250`, `:251` |
| same | item 17's word count and per-sentence breakdown — D2's **Length, counted rather than estimated**, twice; Phase 1's sentence-count Verify | `:322` | `:324` |
| same | `**What landed:**` item 1 — Anchor G | `:458` | `:460` |
| same | the §6.1 *"Designed consumer drift"* bullet — D7's **The cost avoided** | `:460` | `:462` |
| same | the Phase 3 step `3b` record — D2's **Why (c)** reason 3 | `:476` | `:479` |
| same | `**What landed:**` item 5, and its third bullet — Anchor G | `:487`, `:492` | `:490`, `:495` |

**Why they moved.** Plans 106 and 101 edited `src/commands/plan/main.md` above sub-question 6 after this plan was written — plan 106's `find-intake-handoff` notice in PHASE 0a.5 (`:73`–`:90`), plan 101's `game-engineer` entry in the specialist list (`:411`) — and both digits this plan cites there moved by 21. Plan 107's Phase 2 (`d1d1370`, 2026-10-01) moved `src/commands/specify/main.md`: it added two flag lines to Step 4.3's `record-affected-area` fence and two paragraphs above the covering paragraph — one opening *"Every row this step records with `record-affected-area` declares `--change-kind`"*, one with the bold lead-in **The standard Step 4.4 sets for §5.2 Behavior preservation binds every §4 row that claims `no-code-change`.** — and one sentence inside the covering paragraph: *"That holds whatever `--change-kind` the row is recorded with, and a `no-code-change` row is recorded only with the citation required above."* The excerpt D2's **Why (c)** reason 2 quotes, with its ellipsis, still reads true, and the definition is unchanged: a §4 row AND a §5 AC naming the surface. `CHANGELOG.md` now opens with `## [Unreleased]` at `:8` and its `### Changed` at `:10`, carrying six entries — plans 101, 102, 104, 105, 106 and 107 — above `## [2.0.12]` at `:18`: the ten lines the plan-99 entry moved. That `### Changed` is the in-flight section Phase 3 would target today, and Phase 3 still reads the top of the file live at build time. *(added 2026-10-02 — Phase 3: read live at build time, the entry went under `## [Unreleased]` → `### Fixed` instead — a correction of shipped rule text, in the subsection plan 125 opened on 2026-10-02, after this re-check; see `## Build record — 2026-10-02`)* `PLAN-STATUS-ARCHIVE.md`'s `## Index` gained six lines — plans 101, 102, 104, 105, 106 and 107 (`:92`–`:97`) — above the plan-99 entry. `src/manifest.json`'s mapping moved by one line, below plan 104's `templateOwned` entry for `src/constitution.md` (`:14`). Plan 104's Phase 6 (`087497c`) added dated, additive amendments to plan 99 — a paragraph after its F9 (`99-…:70`) and one line under the §6.1 bullet (`:463`) — which moved plan 99's digits by two above `:463` and by three below it; plan 99's quoted texts are otherwise unchanged. `DEVELOPMENT-STATUS.md`'s item 20 moved by two lines, its quoted text unchanged.

**State sentences brought current, each marked R4.** The Status line, which now names all six lower-numbered plans DONE (build) and this plan's build as next, and which points at this section — that pointer marked R1–R4, because it covers every R-item. *(added 2026-10-02 — Phase 3: the Status line has since gained its DONE (build) opening; the text this sentence describes follows that opening as written, and the opening's Phase 3 marker records that its "this plan's build is next" held until Phase 1's commit `b122abe`. This R4 sentence is kept as the record of what R4 did)* The close record's `**Build sequencing — 2026-09-21.**` block: its second bullet (the same fact); its third, whose forecast held — its text stands, and an `added` marker beside it says the anchors did drift, as the table above records; and its fourth, whose obligation is discharged — plan 107's D7 now sits at `107-SURFACE-PATH-PROOF-PLAN.md:256`, and plan 107 closed it on 2026-10-01 as *"Ratified as recommended — arm: NO"* (`107-…:346`), the row that records this plan's D1 re-check as *"not triggered"*, so D1 stands. The `## Phases` lead (the same fact as the Status line). `### Ledger indexing`, whose *"named in no ledger file"* was true on 2026-09-21: on 2026-10-02 each of plans 101, 102, 104, 105, 106 and 107 is indexed in `PLAN-STATUS-ARCHIVE.md`'s `## Index` (`:92`–`:97`) and `## Entries` (`:266`–`:276`), added at its close — that section's rule at work, and the rule stands. And `## Context for next session`'s *"Phase 0 is the gate and nothing below it may start."*, a drafting-time sentence the close left standing, which contradicted the CLOSED status — ⚠ **an internal inconsistency found during the re-check, NOT tree drift.** **Also added under R4:** the digit note under `## Origin & evidence` and Trap 6, which now say the R4 digits were re-read on 2026-10-02; `## When resuming work` step 3, which names R4's table as the digit register; and the D5 and D6 rows of the outcomes table, as above.

**Re-verified UNCHANGED on the same read:** `src/CLAUDE.md:230` — item 17, byte-identical to every quote of it in this plan, still 152 words by plan 99's counting rule, per sentence 23 / 40 / 20 / 34 / 11 / 24 *(added 2026-10-03 — wording amendment: true at `HEAD` `8e61645`, before Phase 1 (`b122abe`) took item 17 to 195 words and the explicit pick to 197)* — and `:239` (`### Never` item 7); (c) still counts 77 words (26 / 39 / 12), so 152 → 195 holds *(added 2026-10-03 — wording amendment: true at `HEAD` `8e61645`; after the explicit pick, item 17 is 197 words, (c) 79 words, 26 / 39 / 14)*; `src/constitution.md:238` (§6.1); `src/commands/specify/main.md:399`; every `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md` digit this plan cites — `:293`, `:297`, `:299`, `:301`, `:352`, `:375` and `:657`; Phase 1's two `#### Verify` counts — `cover it unless you can name` 1 hit in `src/`, `unless you can name what the user would see differently` 2; Phase 3's two inventories — `what the user would see differently` still returns 10 hits in 7 files outside this plan file (`CHANGELOG.md` 1, `DEVELOPMENT-STATUS.md` 1, `PLAN-STATUS-ARCHIVE.md` 1, `99-…` 4, `100-…` 1, `src/CLAUDE.md` 1, `src/commands/specify/main.md` 1), and `the surface stays uncovered` its 4 pre-existing hits; no command or agent other than `/devforge:specify` calls `record-affected-area`, `add-ac` or `revise-ac` (a grep over `src/commands` and `src/agents`), so (c)'s first sentence still holds; the four Phase 4 test files exist; and the number 108 is still unique at the repo root. ⚠ **The plan's own rule still holds and R4 does not retire it: grep the quoted text, never the digits. These digits are current at `HEAD` `8e61645` and will drift again on the next edit to those files.**

---

## The fix

**Give the fact a single owner: the rule owns the invariant and the definition; the command owns the outcome.** Item 17 states what covering IS and therefore which stage can do it, and says nothing about what any stage does when it cannot. `/devforge:plan` keeps its outcome — the re-ask, the Risk Assessment row, the `**Unconfirmed exclusions**:` entry — in its own file, and `/devforge:specify` keeps its default in its own file. **Neither command is edited.** The rule's `Deciding it yourself …` sentence is replaced by a sentence that derives the limit from the definition of covering instead of restating anyone's outcome. **This is Option SINGLE-OWNER below; its wording is D2 candidate (c), and D2 is where those exact words are ratified.**

**FOUR options were weighed. All three rejected ones are recorded with their reasons, so that a future session does not rediscover any of them as a fresh idea:**

⚠ **A departure from house form, flagged rather than left to be noticed:** this plan labels its options by NAME where plans 99 and 100 labelled theirs by letter, because capital letters are already spoken for here by Anchor A–J and a second capital-letter series in the same document is a collision.

- **Option MOVE-THE-COMMAND** — move `/devforge:plan` to the rule: make the second non-decision take the cover branch as the model's own choice. **Rejected** because "cover" at `/devforge:plan` is not plan-local (Anchor E); because the outcome would stop being an exclusion — the `**Unconfirmed exclusions**:` line lists *"a §6 exclusion left standing, or a surface left uncovered"* (`CHANGELOG.md:24` *(corrected 2026-10-02 — R4: was `:14`)*), and a covered surface is neither, so this option leaves the outcome with no home on the approval summary, and plan 100's D8 already declined to widen that line, recording at `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md:352` that *"That line's definition covers sub-question 6's non-decisions only"*; and because it effectively bounces the pipeline back to `/devforge:specify` on a user's silence. ⚠ **Recorded as rejected-but-coherent: this is the option that keeps rule 17 strongest, and a maintainer who values that above pipeline flow should pick it deliberately rather than let D1 pass by default.**
- **Option ESCAPE-CLAUSE** — move the rule to the command: add "where a command names the outcome, it stands". **Rejected under this repo's zero-escape-hatch policy** (`CLAUDE.md`, `## Meta-discipline`), which names "if X except Y" and any equivalent slip-path as the thing to close before adopting a rule. That clause is a textbook escape hatch: every future command could name an outcome and exit the rule.
- **Option LIFECYCLE-REGIME** — make rule 17 lifecycle-aware: keep the `cover it` default where covering is available and **append one sentence** naming a second regime — after a spec is approved, covering a surface it does not cover takes a revision of that spec, so a downstream command raises the surface and, on a reply that decides nothing, leaves it uncovered, records that no one decided it, and says covering it takes a spec revision. **This was the first option briefed for this plan, and it is rejected in favour of Option SINGLE-OWNER** for the reason `### Root cause` gives: it makes item 17 restate `/devforge:plan`'s outcome on top of the `/devforge:specify` default it already restates — three copies, two seams. ⚠ **Option LIFECYCLE-REGIME's wordings are D2's candidates (a) and (b); ratifying either of those ratifies this option, and the two records point at each other.** ⚠ **Recorded as rejected-but-coherent as well: it is a pure append and therefore the smallest possible blast radius on a file another session is editing, which is the one thing it has over Option SINGLE-OWNER.** *(added 2026-10-02 — R3: "a file another session is editing" is the 2026-09-21 reading — on 2026-10-02 `src/CLAUDE.md` carries no other session's hunks, and `110-IMPLEMENT-AUTO-APPROVE-PLAN.md` plans a later edit of it in a different region; this counter is recorded as made and is not re-argued)*
- **Option SINGLE-OWNER — RECOMMENDED.** The shape described above: item 17 states what covering IS and which stage can therefore do it, and restates no command's outcome. ⚠ **Its wording is D2 candidate (c), and only (c)** — the other two candidates belong to Option LIFECYCLE-REGIME. **The argument for it is made in D2, not here.**

---

## Decisions to ratify

Nothing below is ratified. **(Drafting-time text, kept as drafted — Phase 0 CLOSED 2026-09-21; D1–D7 and OQ-2 ratified as recommended, OQ-1 moot by D2's outcome; see `### Phase 0 close record`.)** Each item states the decision, a recommendation, and **the strongest counter-argument, recorded honestly rather than answered away.** Proposed emitted wording is **the object of ratification**, not a description of it — D2 carries full text for exactly that reason. **No emitted sentence may name plan vocabulary** ("D1", "plan 108", "Phase 0"); the plan-99 build recorded *"no plan vocabulary entered `src/`"* as an invariant and this plan keeps it.

### D1 — Which side moves

**The decision.** The rule, or the command.

**RECOMMEND the rule** — `src/CLAUDE.md` `### Always` item 17. **`/devforge:plan` is not edited at all**, in this plan or by it. ⚠ **D1 decides only WHICH SIDE moves; whether the edit is an append or a replacement of one sentence is D2's, and the two candidate shapes differ on exactly that.**

**Why.** Anchor E: the command's outcome is forced by what the command may write. A rule whose default an entire lifecycle stage cannot execute is the broken half.

**COUNTER, at full strength.** **This weakens the rule exactly downstream, where silent dropping is most likely.** Upstream there is a human at a question and a spec still being written; downstream there is a model with a task list. A reader who takes away only the half that says you cannot cover it there may read it as licence to drop surfaces at `/devforge:breakdown` or `/devforge:implement`. ⚠ **The consequence for the wording is binding, on every candidate: it must keep "raise it" MANDATORY and must never authorise an exclusion.** A draft that reads as "downstream, leave it out" has failed D1 even if D1 is ratified.

### D2 — The exact wording: three candidates, in two different shapes

**The decision.** Which words go into item 17. All three candidates are given in full so ratification is on words, not on a description of words.

⚠ **The candidates are not three wordings of one edit — they are two different EDITS.** **(a) and (b) are an INSERTION**, added after item 17's `Deciding it yourself …` sentence and leaving it standing. **(c) REPLACES that sentence in place** and adds nothing anywhere else. Phase 1's deliverable and its Verify differ accordingly, and Phase 1 as written below is (c)'s shape.

#### (c) — RECOMMENDED

**What it replaces**, quoted from `src/CLAUDE.md:230`:

> Deciding it yourself — handed back or never asked — cover it unless you can name what the user would see differently without it; record any exclusion as yours, with that reason, and tell the user.

**The replacement, three sentences:** *(added 2026-10-03 — wording amendment: the quote below keeps the ratified words; in item 17 its third sentence's "with that reason" now reads "with the reason you named", by an explicit maintainer pick — see `### Phase 0 close record`, **Amended after the build by an explicit maintainer pick — D2's wording, one phrase (2026-10-03)**)*

> Covering a surface takes an affected area and an acceptance criterion in the spec that name it, so only the command writing that spec covers one. Deciding it yourself — handed back or never asked — cover it there, unless you can name what the user would see differently without it; anywhere else you cannot cover it, so raise it and leave it neither covered nor excluded. Record any exclusion as yours, with that reason, and tell the user.

**Why (c):**

1. **It restates no command's outcome.** No Risk Assessment row, no approval-summary line, no "spec revision" phrasing — all of those stay owned by `src/commands/plan/main.md:434` *(corrected 2026-10-02 — R4: was `:413`)*. **Nothing in item 17 can drift against that arm, because item 17 no longer says anything about it.**
2. **It is derived, not declared.** *"Only the command writing that spec covers one"* follows from the definition of covering that `/devforge:specify` already carries at `src/commands/specify/main.md:658` *(corrected 2026-10-02 — R4: was `:652`)*: *"**Covering a user-facing surface takes two entries.** A surface that shows the feature the user named is covered … only when this step records an affected-area row naming that surface AND Step 4.4 adds at least one acceptance criterion whose statement names it."* **The rule states a definition the tree already holds, rather than a second opinion about an outcome.**
3. **It closes Anchor F by definition rather than by enumeration.** `/devforge:implement` cannot cover a surface because covering takes a §4 row and a §5 AC it does not write — **not because a lifecycle clause says so.** Any future command is covered without touching item 17, which is the property (a) and (b) lack.
   - ⚠ **A check on that generalization, read from the record rather than measured.** `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md:297` names **`/devforge:research`'s Step 2b classification** as a sixth site governed by item 17's `never asked` arm, and `/devforge:research` writes no `spec.md` either — so under (c) it too "cannot cover it". **That matches what the command already does:** `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md:479` *(corrected 2026-10-02 — R4: was `:476`)* records that its *"**Phase 3 step `3b`** records each uncovered surface through `record-gap --dimension affected_area`"*, which is a surface left neither covered nor excluded. **Under the current `cover it` text, item 17 tells `/devforge:research` to do something that command cannot do; under (c) it does not.** ⚠ **This is a reading of two plan records and one command's documented step, NOT a run and NOT a measurement — and `/devforge:research` is NOT edited by this plan.**
   - ⚠ **A second contradiction site, this one between the two always-on rules themselves — recorded at a stated width, and it must not be read wider.** Anchor C's sentence has a second branch: *"where the command names none, end the turn having written nothing."* **For a command that names no outcome, `Never` 7 says write nothing and item 17 says `cover it` — write something.** Candidate (c) agrees with `Never` 7, because *"anywhere else you cannot cover it, so raise it"* writes no artifact; **(a) and (b) leave that contradiction standing**, since neither touches the case where no outcome is named. ⚠ **The width.** `Never` 7 governs **a reply that picks nothing** — a hand-back, or free text naming none of the options offered. **Item 17's `never asked` arm is a DIFFERENT case**, and `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md:297` assigns the Anchor-F commands to that arm, not to this one, **so this second site does NOT cover the never-asked case and must not be written as though it does.** It is reachable only where a downstream command ASKS about a surface and the reply decides nothing — and **no downstream command carries a rule that asks**, which is what Anchor F's grep shows. *(added 2026-10-02 — R1: the grep now returns one hit, at `/devforge:verify` — an instruction to read the construction site of a surface an AC names, which asks nothing — so this sentence holds)* ⚠ **What this is NOT is `Never` 7 being silent downstream.** That rule closes with *"A question the command does not classify decides what the run does"*, so **an unclassified question falls into the run-deciding branch by the rule's own words**: a command that classifies no surface question does not thereby escape `Never` 7, and **where such a question IS asked, the branch applies and the contradiction with item 17's `cover it` fires.** ⚠ **Whether it is ever reached in practice is NOT established here: the contradiction is between two always-on rules as written, and nothing in this plan observes it firing.** **It is recorded because it is what stops a future session dismissing Anchor F with *"`Never` 7 already covers downstream"* — it does not, and where it does apply it contradicts item 17 rather than rescuing it.**
4. **It resolves COUNTER 2 outright.** There is no "two defaults inside one item" to reconcile: the single `Deciding it yourself` sentence states both cases in one breath, and no meta-sentence is needed to say which displaces which.
5. **It keeps every D1 obligation.** *"raise it"* stays mandatory; *"leave it neither covered nor excluded"* authorises no exclusion; the attribution clause survives verbatim as its own third sentence. *(added 2026-10-03 — wording amendment: verbatim in the ratified text; since the explicit pick, that sentence's "with that reason" reads "with the reason you named", while "Record any exclusion as yours" and "tell the user" are unchanged, so this reason still holds)*

**COUNTER to (c), at full strength.** **(c) edits a sentence that plans 99 and 100 both left standing** — plan 100's D5 deliberately (`:293`, `:299`) — **so it is a heavier touch than an append, and a builder who mis-splices it damages a rule that is currently correct upstream.** Phase 1's sentence-by-sentence Verify is what contains that risk, and **a maintainer who prefers the smaller blast radius of a pure append should pick (a) deliberately**, on a file another session is editing concurrently (Trap 1). *(added 2026-10-02 — R3: "another session is editing concurrently" is the 2026-09-21 reading — on 2026-10-02 `src/CLAUDE.md` carries no other session's hunks and Trap 1 is not in force, while `110-IMPLEMENT-AUTO-APPROVE-PLAN.md` plans a later edit of the file in a different region; this counter is recorded as made and is not re-argued)* ⚠ **Also recorded: (c) still leaves `cover it` stated in two places — item 17 and `src/commands/specify/main.md:399`. It takes the seam count from two to ONE, not to zero.** See the Tripwires item on why zero is refused.

#### (a) — NOT recommended. 46 words, inserted

> After a spec is approved, covering a surface it does not cover takes a revision of that spec: raise the surface, and on a reply that decides nothing leave it uncovered, record that no one decided it, and say that covering it takes a spec revision.

#### (b) — NOT recommended. 60 words, inserted

The same as (a), with the "the default above does not apply downstream" clause spelled out and the attribution stated as its own clause.

> The default above does not apply once a spec is approved: after that, covering a surface the spec does not cover takes a revision of it, so raise the surface, and on a reply that decides nothing leave it uncovered and say that covering it takes a spec revision. Record that no one decided it, never as your own exclusion.

**COUNTER to (a) and (b) — the root-cause objection, and it is why they are not recommended.** Both **restate `/devforge:plan`'s outcome inside item 17**. Item 17 already restates `/devforge:specify`'s default, so either candidate leaves **three copies of one norm and two independent drift seams** where there is one today, and `### Root cause` records that a rule restating a per-command outcome is what produced this clash in the first place. ⚠ **They are rejected for reproducing the cause, not for reading worse.** ⚠ **(a) and (b) ARE Option LIFECYCLE-REGIME's wordings in `## The fix`; ratifying either ratifies that option, and (c) is Option SINGLE-OWNER's only wording.**

**COUNTER 1 to (a) and (b) — length.** Item 17 is already the longest item in either list by a wide margin, and an insertion makes it longer than a replacement does. An always-on rule that no one finishes reading is not always-on in practice. ⚠ **Recorded and NOT argued away: the maintainer weighs it.**

**COUNTER 2 to (a) — two defaults inside one item.** (a) adds a second regime without saying that it displaces the first, so item 17 would then contain *"cover it unless you can name what the user would see differently without it"* and *"leave it uncovered"* with nothing between them but a lifecycle clause the reader must apply correctly. **(b) says outright that the default above does not apply**, at the cost of spending words describing its own other sentences. **(c) has neither problem** (reason 4 above).

#### Length, counted rather than estimated

Item 17 is **152 words** today — `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md:324` *(corrected 2026-10-02 — R4: was `:322`)* records both the count and the counting rule (*"bold title counted, hyphenated words as one, item number excluded"*), and `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md:301` repeats it as *"already the longest item in either list, at 152 words."* No candidate contains a hyphenated word, so the same rule gives:

| Candidate | Shape | Words added | Item 17 after |
|---|---|---|---|
| **(c)** | replaces a 34-word sentence with 77 words | **+43** | **195** *(added 2026-10-03 — wording amendment: 79 words, +45, 197 after the explicit pick — still the shortest of the three)* |
| (a) | inserts 46 words | +46 | 198 |
| (b) | inserts 60 words | +60 | 212 |

⚠ **The 34 is not this plan's own arithmetic: `99-…:324` *(corrected 2026-10-02 — R4: was `:322`)* gives item 17's per-sentence breakdown as *"23 / 40 / 20 / 34 / 11 / 24"*, and 34 is the fourth sentence — the one (c) replaces.** **So (c) is the shortest of the three despite being the largest edit**, which is a consequence of replacing rather than appending and not an argument for it.

### D3 — Command-agnostic, or `/devforge:plan`-named

**The decision.** Whether the new sentence names `/devforge:plan`.

**RECOMMEND command-agnostic**, and **all three D2 candidates are written that way.**

**Why.** Anchor F: five commands ride the always-on rule alone. **Naming only `/devforge:plan` would leave `/devforge:implement` still reading `cover it`**, which is the hole this plan exists to close in both directions.

⚠ **Under (c) this stops being a choice about phrasing.** (c) names no command and no stage at all — it names the definition of covering — so **the command-agnostic property falls out of the shape** rather than being selected. Under (a) or (b) it remains a live phrasing decision, because both need a clause that picks out which stage they apply to.

**COUNTER.** A command-agnostic sentence is **vaguer at the one site where a concrete route exists.** At `/devforge:plan` there is a Risk Assessment row, an `**Unconfirmed exclusions**:` line and a re-ask, all named in the command's own text; a general sentence makes the reader map the rule onto that specific machinery, and a reader who maps it wrong has an inconsistency the plan claims to have removed.

**The answer to that counter, under (c), is the single-owner principle itself:** the concrete route is **not vague — it is owned by `/devforge:plan`**, stated once, in that command's file, where a model running that command reads it. **The reader is not asked to derive the route from the rule; the rule does not have one.** ⚠ **That answer is available to (c) only. Under (a) or (b) the counter stands unanswered, because those candidates do carry a route and it is a paraphrase of the command's.**

### D4 — Where the downstream record lands for a command with no artifact slot

**The decision.** Whether the rule requires an artifact.

**RECOMMEND: the rule requires RAISING the surface and requires NO artifact.** Raising it is how the user learns of it, and under (c) that is the whole obligation — *"raise it and leave it neither covered nor excluded"*. ⚠ **(c)'s third sentence, *"Record any exclusion as yours, with that reason, and tell the user"*, does NOT attach to this case: the outcome is not an exclusion.** *(added 2026-10-03 — wording amendment: that sentence now reads "with the reason you named", by an explicit maintainer pick; it still does not attach to this case)* **Only `/devforge:plan` has a slot** — the Risk Assessment row plus the `**Unconfirmed exclusions**:` line, both named at `src/commands/plan/main.md:434` *(corrected 2026-10-02 — R4: was `:413`)*. Adding routes to `/devforge:breakdown`, `/devforge:implement`, `/devforge:fix`, `/devforge:review` and `/devforge:verify` — **Anchor F's five, none of which has a slot** — is a **NON-GOAL** of this plan and is listed as one.

**COUNTER, at full strength.** **"Tell the user" with no artifact is the weakest possible record.** It leaves nothing for a later session to read, nothing for `/devforge:verify` to reconcile, and nothing that survives the conversation. A surface raised and left uncovered at `/devforge:implement` is, after the turn ends, indistinguishable from one never noticed. ⚠ **Name this as a known residual in the close record, never as coverage.**

### D5 — `/devforge:specify` edit, or not

**The decision.** Whether the authoring-stage default is restated at its command.

**RECOMMEND NO edit.** `src/commands/specify/main.md:399` already implements the authoring-stage default in the same terms the rule uses, inside numbered step 2 (**Resolve the decision point**) of the decision-point block. A mirrored sentence would be a second site to drift.

**COUNTER.** **A reader of `specify` alone never learns the downstream regime.** The answer is that an always-on `CLAUDE.md` rule is exactly what that reader also loads — but ⚠ that answer is only as good as the rule's reach, and Anchor J says the rule reaches an existing install only through `update.sh`.

### D6 — Docs sweep scope

**The decision.** Which records move and which stay.

**RECOMMEND:**
- **Amend** `DEVELOPMENT-STATUS.md` item 20 (Anchor I) in the same change.
- **Add a NEW `CHANGELOG.md` entry** under whatever section is in flight at build time — read the top of the file live; no version is hardcoded anywhere in this plan.
- **Leave byte-intact:** the plan-99 `CHANGELOG.md` entry (Anchor H), the plan-99 `PLAN-STATUS-ARCHIVE.md` entry (`:262` *(corrected 2026-10-02 — R4: was `:256`)*), and plan files 98, 99 and 100.

**COUNTER.** **Leaving Anchor H unrewritten means the shipped changelog keeps carrying both halves of the contradiction**, and a future session reading `## [2.0.12]` meets the same clash with no note beside it. **Accept it: rewriting shipped history is worse.** A released version block is never edited — the new entry is where the correction is recorded.

### D7 — Whether `src/constitution.md` §6.1 gets a sentence too

**The decision.** Whether the constitution moves with the rule.

**RECOMMEND NO.** Anchor D: §6.1 carries no hand-back default, so **there is nothing there to contradict.** A sentence added there would be new rule text, not a correction.

**The cost avoided, stated because it is the practical half of the recommendation.** §6.1 is a `[universal]` section. `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md:462` *(corrected 2026-10-02 — R4: was `:460`)* records what happened the last time it was touched: *"`constitute_helper verify-universal-defaults` and the WARN-only update-time drift check report §6.1 drift for installs constituted earlier — the third such finding, after plans 86 and 89."* **On that record, touching it again produces a fourth.** ⚠ **That is plan 99's account of the 2026-09-19 build, not a behavior re-verified here; a builder who wants to lean on this cost re-checks what those two checks do today before quoting it.** *(corrected 2026-10-02 — R2: this paragraph's counting frame — "the third such finding" and "touching it again produces a fourth" — predates plan 104's run, which showed the earlier findings indistinguishable from a comparator artifact; the cost holds from plan 104 on, and D7's outcome is unchanged — see R2)*

**COUNTER.** **The constitution outranks `CLAUDE.md`** (`### Always` item 2), and `CLAUDE.md` is three-way merged into a project the user may edit (Anchor J). **A rule that lives only in `CLAUDE.md` can be overridden by a project's own edits to it**, where a constitution sentence could not be — so declining D7 leaves the amended regime on the weaker of the two carriers.

### OQ-1 — What the new sentence keys on — **MOOT if D2 ratifies (c), OPEN otherwise**

**The question exists only for (a) and (b)**, because only they need a phrase to select which regime applies. Two candidate triggers, and they are not the same:

- **"after a spec is approved"** — a lifecycle fact.
- **"where covering the surface takes a spec revision"** — a capability fact.

They agree at `/devforge:plan` and may diverge for any run that meets a surface with no approved spec in hand.

**The record, applying ONLY if (a) or (b) is ratified. RECOMMEND the lifecycle phrase**, which is what both of those candidates use: it is checkable by the model without reasoning about its own write permissions, and it reads as a regime rather than as a self-assessment. **Alternative:** the capability phrase states the actual reason and therefore travels correctly to any future command, at the cost of asking the model to judge what it may write — a judgment it gets wrong exactly when it is already confused about scope. ⚠ **D3's command-agnostic recommendation makes that trigger phrase load-bearing under (a)/(b): it is the ONLY thing selecting which regime applies.**

**Under (c) there is no trigger phrase at all.** (c) keys on **the definition of covering plus which command is running** — a fact the model reads off its own invocation, not a judgment about its write permissions and not a lifecycle clause it must apply correctly. ⚠ **That is why OQ-1 is recorded as moot rather than deleted: the question is real, it is answered by the SHAPE of (c) rather than by a decision, and it comes back the moment (a) or (b) is picked instead.**

### OQ-2 — Whether the rule names the re-ask

`/devforge:plan`'s arm re-asks **once** before landing on `uncovered`, and `### Never` item 7 supplies that single re-ask as an always-on rule (Anchor C). **No D2 candidate names the re-ask** — (c)'s replacement is as silent about it as (a) and (b) are — so all three read, in isolation, like a one-strike rule.

**RECOMMEND relying on `Never` 7** and adding no re-ask clause: it is already always-on, it is already in the same emitted file, and restating it in item 17 creates two sites that must agree about how many times to ask. ⚠ **Under (c) this is not an independent judgment call but a direct consequence of the single-owner principle: the rule does not restate what another always-on site already owns.** **Alternative:** name it ("ask once more, then …") so the sentence is correct read alone — at the cost of the duplication, and of words D2's COUNTER 1 already objects to. ⚠ **This applies to ALL THREE candidates equally; it is not a reason to prefer one over another.**

### Phase 0 close record

**CLOSED 2026-09-21.** **D1–D7 and OQ-2 are ratified as recommended. OQ-1 is MOOT by D2's outcome and is NOT ratified.** Nothing was amended, nothing was declined, no item is left open, and **build phases may start.** ⚠ **Nothing is built.** *(corrected 2026-10-02 — Phase 3: true on 2026-09-21 and until Phase 1's commit `b122abe`; Phases 1–4 have run since — see `## Build record — 2026-10-02`)*

Every statement in this record is dated 2026-09-21 unless it names another date.

**What this record was required to contain, and does:** each of D1–D7, OQ-1 and OQ-2 named with its outcome; whether per-item deliberation was supplied; whether the close was an explicit pick or a delegation; which files the outcomes put in scope; D2's chosen candidate with its text in full and its edit shape; whether the single-ownership principle was endorsed or only the sentence; D4's residual named explicitly; and D1's answer on whether `/devforge:plan` is edited.

**How it closed — 2026-09-21.**

- A **single blanket maintainer directive**, given in the maintainer's own words, in Ukrainian. English paraphrase: *"as for the verdicts — OK, fix all the problems."*
- **No per-item deliberation was supplied, and this record says so.** The precedent is the close records of plans 91, 92, 94, 95, 96, 97, 98, 99 and 100, which state the same.
- **It is a PICK, not a delegation** (plan 98's D1 distinction): it states an outcome rather than handing the decision back. ⚠ **But it names no option per item.** The outcomes below are **this plan's own recommendations, taken under a blanket approval — not nine separate maintainer choices**, and no sentence here may be read as the maintainer having weighed any individual counter-argument.
- **Every decision keeps its counter-argument.** Nothing under `## Decisions to ratify` is deleted, shortened or answered away by this close, because **a ratified decision with its counter-argument deleted cannot be re-opened honestly.** That section's drafting-time lead-in keeps its original opening sentence, *"Nothing below is ratified."*, with a dated parenthetical beside it naming this close — the pre-close text is preserved as the record of the pre-close state.
- ⚠ **Ratification changes no evidence class: a contradiction read out of this tree, nothing measured, no run.** A blanket approval of a reading is still a reading.

#### Outcomes — 2026-09-21

| Item | Outcome (2026-09-21) | What it settles |
|---|---|---|
| **D1** | Ratified as recommended | **The rule moves, not the command.** `src/CLAUDE.md` `### Always` item 17 is the only rule text edited, and **`/devforge:plan` is NOT edited — not in this plan and not by it.** Option MOVE-THE-COMMAND stays rejected. |
| **D2** | Ratified as recommended | **Candidate (c)** — Option SINGLE-OWNER's only wording, quoted in full beneath this table. **The shape is a REPLACEMENT IN PLACE** of item 17's `Deciding it yourself …` sentence, **NOT an append**; candidates (a) and (b), which are Option LIFECYCLE-REGIME's wordings, are declined with it. **The count: item 17 goes 152 → 195 words.** *(added 2026-10-03 — wording amendment: 197 since the explicit pick that changed "with that reason" to "with the reason you named"; this ratified cell keeps its 2026-09-21 count — see **Amended after the build by an explicit maintainer pick — D2's wording, one phrase (2026-10-03)**, below)* |
| **D3** | Ratified as recommended | **Command-agnostic wording.** ⚠ Under (c) this is not a separate wording choice — (c) names no command and no stage at all, so the command-agnostic property **falls out of the shape** rather than being selected. |
| **D4** | Ratified as recommended | **The downstream obligation is RAISE IT**, and **no artifact route is added** to Anchor F's five (`/devforge:breakdown`, `/devforge:implement`, `/devforge:fix`, `/devforge:review`, `/devforge:verify`). ⚠ **The residual, named as the close record demanded: outside `/devforge:plan` NOTHING records the surface beyond the raise itself** — no Risk row, no summary line, nothing a later session can read. **This is the plan's weakest joint and it is ratified WITH its weakness, not despite it.** |
| **D5** | Ratified as recommended | **`src/commands/specify/main.md` is NOT edited.** It already carries the authoring-stage default (`:399`) and the definition (c) derives from (`:652`); both stay byte-identical. *(added 2026-10-02 — R4: `:652` is now `:658`, its text unchanged; this ratified cell keeps its 2026-09-21 digit)* |
| **D6** | Ratified as recommended | **`DEVELOPMENT-STATUS.md` item 20 is amended to match**, and a **NEW `CHANGELOG.md` entry** goes under whichever section is in flight at build time, read live. **Plan 99's `CHANGELOG.md` entry, `PLAN-STATUS-ARCHIVE.md:256` and plan files 98, 99 and 100 stay BYTE-INTACT.** *(added 2026-10-02 — R4: `:256` is now `:262`, the entry unchanged; this ratified cell keeps its 2026-09-21 digit)* |
| **D7** | Ratified as recommended | **`src/constitution.md` §6.1 is NOT edited**, so no fourth `verify-universal-defaults` / update-time drift finding is created for installs constituted earlier. *(added 2026-10-02 — R2: the outcome is unchanged; the earlier findings this "fourth" counts were indistinguishable from a comparator artifact, and the cost holds from plan 104 on — see R2)* |
| **OQ-1** | **MOOT by D2's outcome — NOT ratified** | ⚠ **The one row that is not a blanket "as recommended".** OQ-1's recommendation was the **lifecycle phrase**, which is a trigger only candidates (a) and (b) need. **D2 ratified (c), which keys on neither trigger**, so the question is REMOVED rather than answered. **Its recommendation and its counter-argument stay in the document as history and are NOT ratified by this close.** They return live only if D2 is ever re-opened onto (a) or (b). |
| **OQ-2** | Ratified as recommended | **Rely on `### Never` item 7 for the re-ask.** Item 17 gains **no re-ask clause**, so the two always-on sites never have to agree about how many times to ask. |

**D2's ratified text, in full — the three sentences that replace item 17's `Deciding it yourself …` sentence:** *(added 2026-10-03 — wording amendment: the quote keeps the ratified words; in item 17 the third sentence's "with that reason" now reads "with the reason you named" — **Amended after the build by an explicit maintainer pick — D2's wording, one phrase (2026-10-03)**, below)*

> Covering a surface takes an affected area and an acceptance criterion in the spec that name it, so only the command writing that spec covers one. Deciding it yourself — handed back or never asked — cover it there, unless you can name what the user would see differently without it; anywhere else you cannot cover it, so raise it and leave it neither covered nor excluded. Record any exclusion as yours, with that reason, and tell the user.

**The single-ownership principle — 2026-09-21.**

**The principle is ratified by ratifying Option SINGLE-OWNER**, which is the principle's name in this plan: the rule owns the invariant and the definition, the command owns the outcome. ⚠ **No separate statement about the principle was given by the maintainer, and this record says so.** A blanket directive is not upgraded here into a considered endorsement of a principle — what was approved is the plan's recommendations, and Option SINGLE-OWNER is one of them.

**Amended after the build by an explicit maintainer pick — D2's wording, one phrase (2026-10-03).** *(added 2026-10-03 — wording amendment)* ⚠ **The MAINTAINER's explicit pick, made AFTER the build — never a delegation, and never part of the 2026-09-21 blanket close.**

- **What surfaced.** Phase 1's review recorded a ratified-text observation, kept as `## Build record — 2026-10-02` residual (b): in (c)'s third sentence, *"Record any exclusion as yours, with that reason, and tell the user."*, the nearest antecedent of *"that reason"* is the clause *"anywhere else you cannot cover it"*, while the reason meant is the named user-visible difference — *"unless you can name what the user would see differently without it"*. The build left the words as ratified.
- **The options offered — three.** Replace *"with that reason"* by *"with the reason you named"*; replace it by *"with the reason you gave for it"*, the wording residual (b) records; or move the attribution into the second sentence, which takes item 17 from eight sentences to seven.
- **The pick — EXPLICIT.** **The maintainer picked *"with the reason you named"*** — its *"named"* echoes the second sentence's *"unless you can name"*. It is a PICK of one named option, not a delegation (plan 98's D1 distinction), and unlike the 2026-09-21 close it names the option. The other two options are declined.
- **The amended sentence**, (c)'s third sentence as it now reads in `src/CLAUDE.md` `### Always` item 17:

  > Record any exclusion as yours, with the reason you named, and tell the user.

- **The count, by plan 99's rule.** The sentence goes from 12 words to 14, so item 17 goes from 195 to 197 words and stays at eight sentences — per sentence 23 / 40 / 20 / 26 / 39 / 14 / 11 / 24. (c) goes from 77 words to 79, +45 over the 34-word sentence it replaced, so against D2's **Length, counted rather than estimated** table it is still the shortest of the three — 197 against (a)'s 198 and (b)'s 212.
- **What it reopens: D2's WORDING — that one phrase, and nothing else.**
- **What it does NOT change.** **D2's shape stands** — candidate (c), a REPLACEMENT IN PLACE, Option SINGLE-OWNER's only wording — and D2 is not re-opened onto (a) or (b), so OQ-1 stays MOOT. **Every other outcome in the table above stands as ratified.** Item 17's other seven sentences are byte-identical, no other line of `src/CLAUDE.md` changes, and no command, agent or constitution file is edited. D4's reading stands: the amended third sentence still does not attach to a surface raised where it cannot be covered, because that outcome is not an exclusion.
- **Where it is carried.** Every site in this file that the amendment touches carries a dated `wording amendment` marker — grep that phrase to find them all. **The ratified text is not rewritten:** D2's quoted (c) in `#### (c) — RECOMMENDED` and **D2's ratified text, in full** above keep their 2026-09-21 words, each with a marker beside it, as `### Re-check against the live tree (2026-10-02)` kept ratified text; residual (b) keeps its text and gains a marker. Outside this file: `src/CLAUDE.md` item 17; this plan's `CHANGELOG.md` entry under `## [Unreleased]` → `### Fixed`; and this plan's `## Index` line and `## Entries` entry in `PLAN-STATUS-ARCHIVE.md`. `DEVELOPMENT-STATUS.md` item 20 quotes neither the phrase nor a count, so it is unchanged. Plan files 98, 99 and 100 stay byte-intact — plan 99 quotes the pre-build sentence, *"with that reason"* included, as the record of what shipped.
- ⚠ **Evidence class unchanged.** The observation is a reading of the ratified text; nothing was measured, and the pick is a choice of wording, never evidence that the old phrase misled a model on any run.

**What the outcomes put in scope — 2026-09-21.**

Each ratified item is checked here **by NAME, never against a range**, and the phase that carries it is named. ⚠ **This accounting exists because `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md:657` records a HIGH finding of exactly the opposite: an item ratified by a blanket close, covered in that plan's item map only as part of a RANGE, dropped from every hand-enumerated per-phase list, and shipped NOWHERE while two ledgers claimed it had.**

- **Phase 1 — `src/CLAUDE.md` item 17.** Carries **D1** (the rule is the side that moves), **D2** (the ratified text and its replace-in-place shape), **D3** (the sentence names no command), **D4**'s obligation half (*"raise it"*, and no artifact) and **OQ-2** (no re-ask clause).
- **Phase 2 — cross-check sweep.** Carries **D5** and **D7** as verified no-ops — `src/commands/specify/main.md` and `src/constitution.md` byte-unchanged — and **D1** as the check that `src/commands/plan/main.md` is byte-unchanged.
- **Phase 3 — docs sweep.** Carries **D6**'s two targets (`DEVELOPMENT-STATUS.md` item 20; a new `CHANGELOG.md` entry) and **D4**'s residual half, which the changelog entry's honest-bounds section must state.
- **Phase 4 — live-spec tests.** Carries **no D-item**, and that is stated rather than left to be inferred: it pins that nothing else in the tree moved.
- **OQ-1 is carried by NO phase, and that is its correct disposition, not an omission** — a moot question has nothing to build. It is recorded here so a later reader does not go looking for the phase that lost it.

**Build sequencing — 2026-09-21.**

- **Phase 0 is CLOSED and build phases MAY start.** The sequencing below is **the maintainer's**, not a gate this plan imposes. *(added 2026-10-02 — Phase 3: they have run — Phases 1–4, 2026-10-02; see `## Build record — 2026-10-02`)*
- The maintainer stated today that the open plans are worked **in numeric order**. **101, 102, 104, 105, 106 and 107 are open and lower-numbered, so this plan's build comes after them.** *(corrected 2026-10-02 — R4: true on 2026-09-21; on 2026-10-02 all six are DONE (build) — 101 on 2026-09-23, 102 on 2026-09-24, 104 on 2026-09-25, 105 on 2026-09-27, 106 on 2026-09-28, 107 on 2026-10-01 — so under that order this plan's build is next)* *(corrected 2026-10-02 — Phase 3: "this plan's build is next" held until Phase 1's commit `b122abe`; the build ran on 2026-10-02 — see `## Build record — 2026-10-02`)*
- ⚠ **The consequence, stated as a warning and not an aside: every `file:line` in this plan was verified on 2026-09-21, and the lower-numbered plans edit `src/commands/specify/main.md`, `src/commands/research/main.md` and `src/commands/verify/main.md` among others. By the time this plan builds, its anchors WILL have drifted.** `## When resuming work` step 3's re-verification is **the FIRST action of any build session**, not an optional one. *(added 2026-10-02 — R4: confirmed — the anchors did drift; R4's table records each digit that moved, its **Why they moved.** paragraph describes each move, and step 3's re-verification still comes first)*
- ⚠ **One cross-plan interaction to re-check, verified today.** `107-SURFACE-PATH-PROOF-PLAN.md` carries a D7 titled *"Whether `/devforge:plan` gets a rule too"* whose recommendation is **NO**. **As recommended it does not collide with this plan's D1** — both leave `/devforge:plan` unedited. **But if plan 107 closes that D7 the other way, a build session here must re-check D1 before touching anything.** ⚠ **That plan is OPEN and is being edited in this checkout: its D7 moved from line 168 to line 187 between two reads on 2026-09-21. Find it by its title, never by its digits.** *(corrected 2026-10-02 — R4: plan 107 is DONE (build), no longer OPEN; its D7 now sits at `107-SURFACE-PATH-PROOF-PLAN.md:256`, and plan 107 closed it on 2026-10-01 as "Ratified as recommended — arm: NO" (`107-…:346`), the row that records this plan's D1 re-check as "not triggered". The re-check this bullet asks for is discharged: D1 stands. Still find that D7 by its title)*

**What this record does NOT close — 2026-09-21.**

- **Nothing is built.** Phases 1–4 have not started. *(corrected 2026-10-02 — Phase 3: true on 2026-09-21 and until Phase 1's commit `b122abe`; on 2026-10-02 Phases 1–4 have run — Phase 1 BUILT, Phase 2 a verified no-op, Phase 3 the ledger commit, Phase 4 a test run — see `## Build record — 2026-10-02`)*
- **No evidence class changed.** This plan still rests on a contradiction read out of this tree — **no consumer incident is recorded here, nothing was measured, no run was scored** — and Anchor F's opposite-direction hole is still PREDICTED and never observed.
- **No mechanical check was created and none is possible.** `## Honest bounds` stands unaltered: nothing will ever catch a violation of item 17, and (c) takes the drift seam count from two to one, never to zero.
- **No per-item deliberation happened**, so every counter-argument in this plan is live for re-opening on its own merits.

---

## Build record — 2026-10-02

**Phases 1–4 have run: Phase 1 is BUILT, Phase 2 is a verified no-op, Phase 3 is the ledger commit, and Phase 4 is a test run.** *(added 2026-10-02 — Phase 3)* Phases 2 and 4 changed no file and made no commit. No consumer e2e is proposed (`## Honest bounds`), so none waits. ⚠ **Build-verified, never consumer-validated — "built and build-verified" is the ceiling of every claim in this record.** This record was written without a shell: the commits, the diff shape, the word and sentence counts and the test result below are the orchestrator's, verified on 2026-10-02, and every `src/` line digit in it was re-read by grep while it was written; `git log` carries the commit timestamps.

⚠ **The build changes no evidence class:** a contradiction read out of this tree; no consumer incident recorded here; nothing measured; no run. Every check below shows that item 17 now reads as ratified and that nothing else in the tree moved — never that the clash cost anything on a real run, and never how a model reading the amended rule behaves. Anchor F's opposite-direction hole stays PREDICTED and never observed.

| Phase | Commit | Tests | Review |
|---|---|---|---|
| Phase 0 close | `fddbc7d` — the plan's creation commit (2026-09-23), which carries the close dated 2026-09-21 | — (the close record only) | not recorded here |
| Re-check (R1–R4) | `79d556c` | — (plan text only) | not recorded here |
| Phase 1 | `b122abe` | — (instruction-only; Phase 4 runs over it) | instruction-author → instruction-reviewer: SHIP-READY, no finding beyond the two ratified-text observations recorded as residuals (b) and (c) below |
| Phase 2 | none — a verified no-op | — (instruction-only) | instruction-reviewer read eight sites against the amended rule: 0 findings |
| Phase 3 | the ledger commit | — (docs only) | routed instruction-author → instruction-reviewer |
| Phase 4 | none — a test run | the four live-spec test files: 354 passed, 2 skipped | — (no route: this phase runs tests) |

**Commit order:** `fddbc7d` (the plan, with its close) → `79d556c` (the re-check) → `b122abe` (Phase 1) → the Phase 3 ledger commit. The table lists the close before the re-check because its commit came first.

**Phase 1 — `src/CLAUDE.md` item 17 — `b122abe`.**
- Item 17's fourth sentence — the `Deciding it yourself …` sentence — is replaced in place by D2 (c)'s three sentences. The commit changes one line, `src/CLAUDE.md:230`: 1 insertion, 1 deletion. Item 17 is that whole line, so `### Always` items 1–16 and `### Never` items 1–7 are byte-identical, and nothing was inserted anywhere else.
- The new text equals the close record's quoted three sentences character for character, and the five surviving sentences are byte-identical. *(added 2026-10-03 — wording amendment: true of `b122abe`; since the explicit pick, the third new sentence reads "with the reason you named" where the quote reads "with that reason" — see `### Phase 0 close record`)*
- **Counted by plan 99's rule:** 152 → 195 words and 6 → 8 sentences, per sentence 23 / 40 / 20 / 26 / 39 / 12 / 11 / 24. Figures 1–3 and the last two are the surviving sentences; 26 / 39 / 12 is the replacement — the 77 words D2's **Length, counted rather than estimated** table and R4's re-verification counted. *(added 2026-10-03 — wording amendment: true of `b122abe`; after the explicit pick, 197 words, still 8 sentences, per sentence 23 / 40 / 20 / 26 / 39 / 14 / 11 / 24 — the replacement 26 / 39 / 14, 79 words)*
- **Greps over `src/`:** `cover it unless you can name` 1 → 0 hits, by design; `unless you can name what the user would see differently` 2 → 2 — `src/CLAUDE.md` and `src/commands/specify/main.md`; the new words occur in `src/CLAUDE.md` alone; the new words carry no `/devforge:`; no plan vocabulary entered `src/`.
- **Per-item Verify — D1, D2, D3, D4 and OQ-2 each pass.**

**Phase 2 — Cross-check sweep — run 2026-10-02, a verified no-op: no edit, no commit.** instruction-reviewer read every site below against the amended rule: 0 findings, and `## Tripwires`' Phase 2 STOP did not trip. Each row records the line read and its verdict.

| Site | Read at | Verdict |
|---|---|---|
| (1) `src/commands/plan/main.md` sub-question 6, and the `**Unconfirmed exclusions**:` line | `:434`; `:661` | No-op. The §6-entry arm keeps an exclusion the spec already carries — item 17's *"excluded in the user's own words"*. The surface arm — *"the surface stays uncovered … the user did not decide it"* — is the raise, made as the escalation; the command owns the outcome, and the arm never says "excluded". `:661` is the named check below. |
| (2) `src/commands/specify/main.md` — numbered step 2's surface value, the no-evidence case, numbered step 3 (**Deferral path**), and the **Covering a user-facing surface takes two entries.** paragraph | `:397`–`:399`; `:400`; `:404`; `:658` | No-op. *"The value is `cover <surface>`, unless you can name …"* is item 17's *"cover it there"*; the no-evidence case is an open question; the **Deferral path** is a deferral the user states; `:658` is the definition the new first sentence derives from. |
| (3) `src/agents/architect.md` Rule 9, the **Out-of-scope-respect forcing step** | `:154` | No-op: it escalates the surface and does not cover it. |
| (4) `src/agents/devils-advocate.md` Rule 6 | `:79` | No-op: it flags `[excluded by the model]`. |
| (5) `src/commands/grill/references/design-attack-checklist.md` — the `[excluded by the model]` entry | `:79`–`:82` | No-op: a §6 entry so marked that leaves out a surface showing the feature is a signal to flag, not a deliberate exclusion. |
| (6) `src/constitution.md` §6.1 | `:238` | No-op: it sets which surfaces count, never what to do on a non-decision (Anchor D). |
| (7) `src/commands/verify/main.md` — the **Changed files** bullet of the ac-verifier brief | `:207` | No-op: a surface an AC names. |
| (8) `src/agents/ac-verifier.md` — `## Input` item 7, **Changed files**, and the two `PARTIAL`-never-`PASS` sites | `:31`; `:63`, `:71` | No-op: a surface an AC names. |

**The named check — the pre-declared verdict held.** The `**Unconfirmed exclusions**:` line's title is a loose name over a correct body — *"(the exclusion standing, the surface uncovered)"* — so it is no finding, and renaming the line stays out of this plan's scope.

**Two further checks, both clean.** No other sentence in `src/CLAUDE.md` says a model deciding alone covers a surface. `grep -rn "cover it" src/` shows no other site restating a conflicting cover default; `/devforge:research`'s *"cover it or leave it out"* is a question to the user.

**D1, D5 and D7 — byte-unchanged.** `git diff --stat 79d556c HEAD` is empty on `src/commands/plan/main.md`, `src/commands/specify/main.md` and `src/constitution.md`, and the working tree is clean on all three.

**Phase 3 — Docs sweep — the ledger commit.** Docs only. In this plan file: the Status line, this record, the per-phase pointer lines, a dated line atop `## When resuming work`, and dated Phase 3 markers on the sentences the build made stale. In the ledgers: `DEVELOPMENT-STATUS.md` item 20, amended to match the amended rule (D6, target 1); a new `fix(scope):` entry in `CHANGELOG.md` under `## [Unreleased]` → `### Fixed` — the subsection plan 125 opened on 2026-10-02, chosen because the change corrects shipped rule text — with the evidence class first, the honest bounds last and D4's residual in words (D6, target 2, and D4's residual half); and `PLAN-STATUS-ARCHIVE.md`'s `## Index` line and `## Entries` entry for this plan (`### Ledger indexing`). Routed instruction-author → instruction-reviewer; the ledger commit carries the SHA.

**Phase 4 — Live-spec tests — run 2026-10-02, no commit.** `tests/lib/test_constitute_helper.py`, `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py` and `tests/scripts/test_claude_emitter.py`, run over the tree with Phase 1 applied: **354 passed, 2 skipped.** Both skips are in `tests/lib/test_constitute_helper.py` — the `skipUnless` guards at `:695` and `:938`, which skip when the external sample install those two tests copy docs from, at a hard-coded absolute path outside this repo, is absent from this machine. *(added 2026-10-03 — the two guarded tests were converted in `fe8cd40`: they now produce their docs with `generate_docs_helper` and run; the file has 0 skips)* No Python changed, and nothing is red. **This is the passing count Phase 4's `#### Verify` asks this plan to record when the build closes.**

**Concurrency — another session in this checkout, 2026-10-02.** Plan 125 was built here during this build — `ac64387`, `1bbd37a`, `43c0c9b` and `aeaf727`. None of them touched `src/CLAUDE.md`, the file Phase 1 edited, or a file this plan must keep byte-unchanged — `src/commands/plan/main.md`, `src/commands/specify/main.md`, `src/constitution.md` and plan files 98, 99 and 100. `aeaf727`, plan 125's Phase 3 ledger commit, did touch `CHANGELOG.md` and `PLAN-STATUS-ARCHIVE.md`, which this plan's Phase 3 edits. Plan 125's `## [Unreleased]` → `### Fixed` entry moved `CHANGELOG.md`'s plan-99 entry from `:24` (R4's digit) to `:27`, and its archive lines moved `PLAN-STATUS-ARCHIVE.md`'s plan-99 entry past R4's `:262`; Phase 3's own additions above each of those entries — its `### Fixed` entry in `CHANGELOG.md`, its `## Index` line in `PLAN-STATUS-ARCHIVE.md` — move them again. ⚠ **R4's table is NOT re-corrected for this:** it records the digits at `HEAD` `8e61645`, and this paragraph is the one record of the later moves. Grep the quoted text, never the digits (Trap 6).

**Residuals — recorded, never as coverage:**
- **(a) D4's ratified weakness.** Outside `/devforge:plan`, nothing records a surface met downstream beyond the raise itself. D4 was ratified WITH that weakness, not despite it; the build does not touch it, and Phase 3's `CHANGELOG.md` entry names it in words.
- **(b) A ratified-text observation, low — from Phase 1's review.** In (c)'s third sentence, *"with that reason"*: after the new second sentence, the nearest antecedent is *"anywhere else you cannot cover it"*, while the intended antecedent is the named user-visible difference. Bounded, because the rule forbids an exclusion outside the spec-writing command and *"Record any exclusion as yours"* steers the reader to the spec-writing case. **NOT edited: ratification was on these exact words.** The wording fix, only if D2 is ever re-opened: *"with the reason you gave for it"*. *(added 2026-10-03 — wording amendment: RESOLVED — offered three options, the maintainer explicitly picked "with the reason you named", not the wording above; see `### Phase 0 close record`, **Amended after the build by an explicit maintainer pick — D2's wording, one phrase (2026-10-03)**)*
- **(c) A nit — from Phase 1's review.** In *"cover it there"*, *"there"* refers back to the whole of the preceding sentence — *"the command writing that spec"*. Readable; no action.
- **(d) Every `## Honest bounds` item stands unaltered.** The build answers none of them.
- ⚠ **Every counter-argument stands as recorded.** The build measured nothing, so it answered none of them, and the close record's bullet **No per-item deliberation happened** still holds: each is live for re-opening on its own merits.

---

## Phases

**Phase 0 is the `## Decisions to ratify` section above. Its `### Phase 0 close record` reads CLOSED 2026-09-21, so the gate is satisfied and the phases below MAY start.** ⚠ **None of them has started. The maintainer's numeric-order sequencing put this plan's build after plans 101, 102, 104, 105, 106 and 107, and all six are DONE (build) as of 2026-10-01, so this plan's build is next — see the record's `**Build sequencing**` block.** *(corrected 2026-10-02 — R4: this read "None of them has started, and the maintainer's numeric-order sequencing puts this plan's build after plans 101, 102, 104, 105, 106 and 107", true on 2026-09-21)* *(corrected 2026-10-02 — Phase 3: "None of them has started" and "this plan's build is next" were true until Phase 1's commit `b122abe`; on 2026-10-02 Phases 1–4 have run — Phase 2 a verified no-op and Phase 4 a test run, neither with a commit — see `## Build record — 2026-10-02`)*

**Build order.** Phase 2 needs Phase 1, because it reads other files against the amended rule. Phase 3 needs Phase 1, because it copies the ratified wording's substance into `DEVELOPMENT-STATUS.md`. Phase 4 runs last and pins that nothing else moved.

### Phase 0 — Ratification gate

D1–D7, OQ-1 and OQ-2 go to the maintainer. **NO build phase may start before a close record exists.** **(CLOSED 2026-09-21 — the record exists and every Verify bullet below is satisfied by it: D1–D7 and OQ-2 ratified as recommended, OQ-1 moot by D2's outcome. Drafting-time text kept as drafted.)**

#### Verify

- The `### Phase 0 close record` section names **each** of D1–D7, OQ-1 and OQ-2 with an explicit disposition, checked **by NAME, never against a range** — an item with no Verify line cannot fail.
- **D2's record names (a), (b) or (c), carries the chosen text verbatim, says whether the edit is an insertion or a replacement, and says whether the single-ownership principle was endorsed or only the sentence.**
- **D1's record says explicitly that `/devforge:plan` is or is not edited**, because Option MOVE-THE-COMMAND is the coherent opposite and a silent close leaves it ambiguous which was picked.
- **OQ-1's record reads "moot" only where D2 ratified (c)**; under (a) or (b) it carries an answer.
- It states whether per-item deliberation was supplied, and whether the close was an explicit pick or a delegation.
- **Every counter-argument above is still present, unshortened** — including `### Root cause`'s objection to (a) and (b), which is the reason they are not recommended and not a preference.
- The record says what the outcomes put in scope: **D1 and D2 decide whether Phase 1 exists and what it does**, **D5 and D7 decide that no phase touches `src/commands/specify/main.md` or `src/constitution.md`**, and **D6 decides Phase 3's site list.**
- ⚠ **Phase 1 below is written for (c), a replacement. If the close ratifies (a) or (b), Phase 1's deliverable becomes an insertion after the `Deciding it yourself …` sentence and before *"A surface that only shares code is neither covered nor raised."*, and its Verify drops the sentence-splice items and keeps that sentence byte-identical instead.** **(RESOLVED 2026-09-21: the close ratified (c), so Phase 1 builds as written and this fallback does not apply.)**

### Phase 1 — `src/CLAUDE.md` item 17

**BUILT 2026-10-02 (`b122abe`)** — see `## Build record — 2026-10-02`; the text and Verify list below are kept as drafted. *(added 2026-10-02 — Phase 3)*

**Route: instruction-author → instruction-reviewer.** Instruction-only: **no `.py` changes.** ⚠ **Re-read `git status` before staging this phase's commit: Trap 1's routes are the procedure when it shows `src/CLAUDE.md` dirty, and the file is staged normally when it does not — by explicit path, with `git diff --cached --stat` checked after staging, in both cases. See `### Traps`.** *(corrected 2026-10-02 — R3: this read "The dirty-file trap is in force for this phase's commit — see `### Traps`.", true on 2026-09-21; on 2026-10-02 `src/CLAUDE.md` is clean)*

**Written for D2 candidate (c) — a REPLACE-IN-PLACE.** **(Confirmed by the close: D2 ratified (c) on 2026-09-21, so this is the shape that builds and the (a)/(b) fallback below is dead text kept as the record of the pre-close state.)**

**Ratified items this phase carries: D1, D2, D3, D4's obligation half, OQ-2.**

#### Deliverables

- `src/CLAUDE.md` `### Always` item 17 — **the `Deciding it yourself …` sentence is REPLACED by (c)'s three sentences. Nothing is inserted anywhere else, and no other file changes.** (**D1** — the rule is the side that moves; **D2** — the ratified text and its shape.)

#### Verify

**What stays byte-identical, enumerated sentence by sentence.** ⚠ **Every string below was read from `src/CLAUDE.md:230` on 2026-09-21; re-read the line live and diff against the tree, not against this list.**

- **`### Always` items 1–16**, byte-identical.
- **`### Never` items 1–7**, byte-identical.
- **Item 17's bold title and first sentence** — *"**Scope follows what the user sees** — minimality limits the mechanism, never which user-facing surfaces (anywhere the user sees or triggers a feature) count."*
- **Item 17's identity-evidence sentence** — *"A surface shows the feature the user named only on cited user-visible evidence — the same title, label or translation key, route, or tab or mode; shared or different code, requests or data are never evidence or a reason to exclude."*
- **Item 17's disposition sentence** — *"Each evidenced surface is covered, excluded in the user's own words, or raised with them, naming what they see there."*
- **Item 17's shared-code sentence** — *"A surface that only shares code is neither covered nor raised."*
- **Item 17's closing sentence** — *"Ask a present user about a surface you suspect but cannot evidence; deciding yourself, leave it an open question, never silently covered or excluded."*

**What changes, and the false-removal trap it sets.**

- **The replaced sentence's own tail survives as (c)'s third sentence with only its leading capital changed:** `record any exclusion as yours, with that reason, and tell the user` becomes `Record any exclusion as yours, with that reason, and tell the user`. ⚠ **A sweep that greps the lower-case form will report a false removal. Grep case-insensitively, or grep `any exclusion as yours`, which is unchanged.** *(added 2026-10-03 — wording amendment: since the explicit pick, that sentence reads "with the reason you named", so the full string greps to zero in `src/` in either case — by design; `any exclusion as yours` is still unchanged)*
- **`grep -rn "cover it unless you can name" src/` goes from 1 hit to 0, BY DESIGN.** ⚠ **Verified 2026-09-21: that string's single hit in `src/` is `src/CLAUDE.md` — `src/commands/specify/main.md:399` does NOT contain it, because that command's default is worded *"The value is `cover <surface>`, unless you can name …"*. A zero here is the built state, not a deletion of the upstream default.**
- **The string that must NOT change count is `unless you can name what the user would see differently`: `grep -rc` over `src/` returns 2 before and 2 after** — one in `src/CLAUDE.md` (now inside (c)'s second sentence, as `cover it there, unless you can name …`) and one at `src/commands/specify/main.md:399`, which this plan does not edit. ⚠ **Re-verify both counts live before relying on them.**
- **The new words grep in exactly one place in `src/`.**
- **No plan vocabulary entered `src/`** — the new sentences name no D-number, no plan number and no phase.

**Per-item Verify for the ratified items this phase carries** — one line each, because an item with no Verify line cannot fail:

- **D1** — `src/commands/plan/main.md` is byte-unchanged by this phase; `git diff` on that path is empty.
- **D2** — the text in item 17 matches the close record's quoted three sentences **verbatim**, and the edit is a replacement: the `Deciding it yourself …` sentence does not survive alongside the new one. *(added 2026-10-03 — wording amendment: passed at `b122abe`; since the explicit pick, item 17 differs from the quote in one phrase by design — "with the reason you named" for "with that reason")*
- **D3** — the new sentences **name no command and no lifecycle stage**; a grep of the added words for `/devforge:` returns nothing.
- **D4** — the new sentences make **raising mandatory** (*"raise it"*) and require **no artifact**: they name no Risk row, no summary line and no file to write.
- **OQ-2** — the new sentences contain **no re-ask clause**; nothing in them says how many times to ask.
- **Item 17's sentence count goes 6 → 8.** ⚠ **The 6 is not this plan's arithmetic: `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md:324` *(corrected 2026-10-02 — R4: was `:322`)* gives the breakdown as *"23 / 40 / 20 / 34 / 11 / 24"*, six figures, and the five surviving sentences listed above are figures 1, 2, 3, 5 and 6.** (c) replaces figure 4 with three sentences. The diff shows no other structural change inside the item.
- **The staged diff for this phase's commit lists `src/CLAUDE.md` alone, and its hunk set is the item-17 edit alone.** ⚠ **`git diff --stat` on the working tree may list other files — other sessions work in this checkout. Check `git diff --cached --stat` after staging, never the unstaged view.** *(corrected 2026-10-02 — R3: the premise read "`git diff --stat` on the working tree will list other files: `src/CLAUDE.md` is dirty with another session's hunks and several ledgers are modified.", true on 2026-09-21; on 2026-10-02 `src/CLAUDE.md` and the three ledgers are clean, and the check stays because other sessions still work here)*
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — Cross-check sweep

**Run 2026-10-02 — a verified no-op, no edit, no commit** — see `## Build record — 2026-10-02`, which records each site with the line read, the named check's outcome and the D1, D5 and D7 diff check; the text and Verify list below are kept as drafted. *(added 2026-10-02 — Phase 3)*

**Route: instruction-author → instruction-reviewer.** ⚠ **Expected NO-OP. An edit in this phase is a FINDING, not routine** — it means the amended rule contradicts something the sweep was supposed to confirm, and the finding is recorded before it is fixed.

**Ratified items this phase carries: D5 and D7 as verified no-ops, D1 as a byte-unchanged check.**

#### Deliverables

Re-read each site below against the amended rule:

- `src/commands/plan/main.md` sub-question 6 — **both** non-decision arms — and the `**Unconfirmed exclusions**:` line the surface arm feeds.
- `src/commands/specify/main.md` — numbered step 2 (**Resolve the decision point**, the *"The value you supply for a surface"* paragraph) and numbered step 3 (**Deferral path**) of the surface rules.
- `src/agents/architect.md` Rule 9's **Out-of-scope-respect forcing step** — the uncovered-surface direction, which is the escalation `/devforge:plan` routes.
- `src/agents/devils-advocate.md` Rule 6.
- `src/commands/grill/references/design-attack-checklist.md` — the `[excluded by the model]` entry.
- `src/constitution.md` §6.1.
- The **Changed files** bullet of the ac-verifier brief in `src/commands/verify/main.md`, and `src/agents/ac-verifier.md` `## Input` item 7, **Changed files**. *(added 2026-10-02 — R1)* **Expected: a verified no-op** — both tell `/devforge:verify` how to read the construction site of a surface an AC names, while (c)'s *"anywhere else you cannot cover it, so raise it"* governs a surface no AC names. The `#### Verify` bullet **Each site is consistent with the amended rule** covers them, and an edit here trips `## Tripwires`' Phase 2 STOP like any other.

**One named check, with its verdict pre-declared.** ⚠ **The `**Unconfirmed exclusions**:` line's TITLE and (c)'s wording do not use the same word for the same thing, and this is expected.** (c) says a surface met where you cannot cover it is left *"neither covered nor excluded"*, while `/devforge:plan` lists it on a line titled `**Unconfirmed exclusions**:`. **The line's BODY distinguishes the two cases correctly** — `src/commands/plan/main.md:661` *(corrected 2026-10-02 — R4: was `:640`)*:

> say that each stays as the spec left it (the exclusion standing, the surface uncovered) and that the user did not decide it here

**Verdict, declared in advance: the title is a loose name over a correct body, and renaming that line is NOT in this plan's scope.** ⚠ **If the cross-check finds the BODY itself ambiguous — not the title — that is a finding to write into this plan, not something to fix in passing.**

#### Verify

- **Each site is consistent with the amended rule**, recorded as a verified no-op with the sentence that was read, or as an edit.
- **The `**Unconfirmed exclusions**:` check above is recorded with its outcome**, whether that is the pre-declared verdict or a finding about the body.
- **Every inconsistency found is either fixed in THIS phase or written into this plan as a new finding — never left.**

**Per-item Verify for the ratified items this phase carries:**

- **D1** — **`src/commands/plan/main.md` is byte-unchanged.** D1 was ratified as recommended on 2026-09-21, so a diff on that file contradicts the close and stops the phase.
- **D5** — **`src/commands/specify/main.md` is byte-unchanged**, `:399` and `:658` *(corrected 2026-10-02 — R4: was `:652`)* included; `git diff --stat` on that path is empty. Recorded as a **verified no-op**, with the sentence that was read.
- **D7** — **`src/constitution.md` is byte-unchanged**; `git diff --stat` on that path is empty. Recorded as a **verified no-op**.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 3 — Docs sweep

**BUILT 2026-10-02** — see `## Build record — 2026-10-02`; the ledger commit carries the SHA. The text and Verify list below are kept as drafted. *(added 2026-10-02 — Phase 3)*

**Route: instruction-author → instruction-reviewer. Docs only.** ⚠ **Other sessions are building in this checkout, and a ledger file may be modified by other work when this phase runs. Re-read `git status`, read each ledger LIVE, re-derive every edit from what is there, and commit by explicit path — never `git add -A`. Never touch another session's plan file.** *(corrected 2026-10-02 — R3: the first sentence read "Other sessions are building in this checkout and several ledger files are already modified by other work.", true on 2026-09-21; on 2026-10-02 `CHANGELOG.md`, `DEVELOPMENT-STATUS.md` and `PLAN-STATUS-ARCHIVE.md` are clean)*

**Ratified items this phase carries: D6's two targets, and D4's residual half.**

#### Deliverables

- **D6, target 1 —** `DEVELOPMENT-STATUS.md` item 20, amended to match the ratified rule. ⚠ **Under (c) that means item 20 stops describing the cover default as unconditional and carries what covering takes and which command can do it; it does NOT gain `/devforge:plan`'s outcome, for the same single-ownership reason the rule does not.**
- **D6, target 2 —** `CHANGELOG.md`, one new entry, **with the evidence class FIRST and the honest bounds LAST**, placed into whichever section is in flight at build time. ⚠ **Read the top of the file live; a released version block is never edited, and no version number is hardcoded in this plan.**
- **D4's residual, inside that entry's honest-bounds half** — that outside `/devforge:plan` nothing records the surface beyond the raise itself. ⚠ **It is written as a residual the change accepts, never as coverage.**

#### Verify

- **`grep -rn "what the user would see differently"` across the repo returns only sites consistent with the amended rule.** The inventory below was taken on 2026-09-21, **before this plan file existed** — this file now carries the phrase itself in its anchor quotes, and so will the new changelog entry. **10 hits in 7 files at that moment:**
  - `src/CLAUDE.md` ×1 — the amended rule (Phase 1).
  - `src/commands/specify/main.md` ×1 — the authoring-stage default (D5: NOT edited).
  - `DEVELOPMENT-STATUS.md` ×1 — item 20 (this phase).
  - `CHANGELOG.md` ×1, `PLAN-STATUS-ARCHIVE.md` ×1, `99-…` ×4, `100-…` ×1 — **records, all byte-intact.**
  - ⚠ **After the build the count rises by this plan file's own quotations and by the new changelog entry. A raw count is not the check; the per-file disposition is.**
- **`grep -rn "the surface stays uncovered"` returns its 4 pre-existing hits** — `src/commands/plan/main.md`, `CHANGELOG.md`, `99-…`, `100-…` — **unchanged**, plus this plan file and the new entry.
- **Plans 98, 99 and 100, the plan-99 `CHANGELOG.md` entry and the plan-99 `PLAN-STATUS-ARCHIVE.md` entry are byte-intact** — `git diff` on those paths is empty.
- **No ledger sentence claims any phase is consumer-validated.** "Built and build-verified" is the ceiling in every line.
- **No tracked file names a client, install, repo, branch, ticket or product.**

**Per-item Verify for the ratified items this phase carries:**

- **D6** — **both** targets are edited, not one: `DEVELOPMENT-STATUS.md` item 20 **and** a new `CHANGELOG.md` entry. ⚠ **And the byte-intact half is checked too: `git diff` is empty on plan files 98, 99 and 100, and the plan-99 entries in `CHANGELOG.md` and `PLAN-STATUS-ARCHIVE.md` are unchanged.**
- **D4** — the new `CHANGELOG.md` entry **names the no-artifact residual in its honest-bounds half, in words**. An entry that describes the raise without the residual has not carried D4.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 4 — Live-spec tests

**Run 2026-10-02 — 354 passed, 2 skipped, no commit** — see `## Build record — 2026-10-02`, which records the passing count this phase's `#### Verify` asks this plan to record when the build closes, so that bullet is satisfied. The text and Verify list below are kept as drafted. *(added 2026-10-02 — Phase 3)*

**No route: this phase runs tests and records the result.**

**Ratified items this phase carries: NONE, and that is stated rather than inferred.** No D-item and no OQ lands here; the phase exists to pin that nothing else in the tree moved.

#### Deliverables

- A run of `tests/lib/test_constitute_helper.py`, `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py` and `tests/scripts/test_claude_emitter.py`.

#### Verify

- **All four are green, and the passing count is recorded in this plan when the build closes.**
- ⚠ **This plan changes no Python. A red test here means something else in the tree moved** — investigate before attributing it to this change, and do not "fix" it inside this plan's commits.

### Ledger indexing

**Index this plan in `PLAN-STATUS-ARCHIVE.md` ONLY when it closes.** Open plans in this repo are indexed nowhere: verified 2026-09-21, `101-NON-WEB-STACK-READINESS-PLAN.md`, `102-SPECIFY-IN-PLACE-REVISION-PLAN.md`, `104-UNIVERSAL-SECTIONS-INTEGRITY-PLAN.md`, `105-HYPOTHESIS-SUPPRESSION-PRECISION-PLAN.md`, `106-INTAKE-PROVENANCE-CONTINUITY-PLAN.md` and `107-SURFACE-PATH-PROOF-PLAN.md` are named in no ledger file (`PLAN-STATUS-ARCHIVE.md`'s `## Index` and `## Entries` both stop at plan 100), only in `FINDINGS.md` and in each other. *(corrected 2026-10-02 — R4: true on 2026-09-21; on 2026-10-02 each of plans 101, 102, 104, 105, 106 and 107 is indexed in `PLAN-STATUS-ARCHIVE.md`'s `## Index` (`:92`–`:97`) and `## Entries` (`:266`–`:276`), added at its close — this section's rule at work, and the rule stands)* *(added 2026-10-02 — Phase 3: this plan is indexed at its DONE (build), in the Phase 3 ledger commit, as plan 107 was at its own; "closes" here is the build's close, and the maintainer's close of the plan has not happened)*

---

## Honest bounds

⚠ **These are the plan's ceiling. Any summary that drops one overstates the plan.**

- **Zero Python, zero gates, zero validators, zero new `verify-*` verbs. Nothing mechanical will ever catch a violation of rule 17** — before this change or after it. The rule is read by a model and checked by nobody.
- **The clash was read out of the tree; the cost of it was never measured.** No run was scored and no incident is re-readable here. The consumer run that surfaced it is not evidence this repo holds.
- **Anchor F's opposite-direction hole is PREDICTED from the text alone and was never observed.** Plan 99's D8 named the revisit trigger for those commands as *"an observed exclusion at one of those stages"*, and that trigger has not fired.
- **The emitted `CLAUDE.md` reaches an install through `update.sh`'s three-way merge** (Anchor J), so an install that is not updated keeps the contradiction, and **an install that customised item 17 may not take the amendment at all.**
- **Whether a surface "shows the same feature" stays model judgment**, exactly as plan 99 recorded. **This change re-homes a default; it does not touch the decision procedure**, the identity-evidence definition, or anything that decides which surfaces count.
- **This plan makes the downstream record weaker than the upstream one on purpose** (D4): all five commands in Anchor F get a raise and no artifact, so a surface raised and left uncovered at one of them survives only as long as the turn does.
- **De-duplication is the only prevention available, and it is partial.** `### Root cause` names single ownership as the fix; **(c) takes the seam count from two to one, not to zero** (see `## Tripwires`), and nothing stops a future change from copying a command's outcome back into item 17. **The principle is a rule for humans, enforced by nothing.**
- **No consumer e2e is proposed.** There is nothing mechanical to exercise; a fixture run would show a model reading amended prose, which is not a result.

---

## Tripwires

- **If a phase finds itself editing `src/commands/plan/main.md`, STOP.** That is Option MOVE-THE-COMMAND arriving under another name — return to D1 and ratify it explicitly or not at all.
- **If a draft of the new sentence lets a command's own named outcome decide whether the rule applies — "where a command names the outcome", "except where the command says otherwise", or any equivalent — STOP.** That is Option ESCAPE-CLAUSE, and the zero-escape-hatch policy in `CLAUDE.md` refuses it. ⚠ **The test is the clause's effect, not its words: item 17 already contains an "unless" that is a condition on the default, not an exit from the rule.**
- **If the new sentence can be read as authorising an exclusion rather than requiring a raise, STOP and rewrite.** D1's counter-argument names this as the failure mode of the recommended option.
- **If Phase 2 produces an edit anywhere, STOP the sweep and record the finding first.** An expected no-op that edits something means the amended rule has a second consequence nobody predicted, and the rest of the sweep must be re-read against that.
- **If a phase reaches for `src/constitution.md`, STOP** — D7 declined it, and from plan 104 on a `[universal]` edit costs a genuine per-rule drift finding for installs constituted after plan 104. *(corrected 2026-10-02 — R2: this read "a `[universal]` edit costs a fourth drift finding for installs constituted earlier"; plan 104's run showed the earlier findings indistinguishable from a comparator artifact, and an install constituted before plan 104 sees a single `PRE_IDENTITY` line either way)*
- **If a session proposes removing the `cover it` default from item 17 altogether — leaving it only at `src/commands/specify/main.md:399` — STOP. That is refused, and it is refused here so nobody attempts it as a cleanup.** (c) accepts one residual seam: `cover it` stays stated in **two** places, item 17 and `/devforge:specify`, and **they agree today.** Deleting item 17's half would take the seam count to zero, **and it would stop item 17 being an always-on rule about surfaces at all** — the whole point of an always-on rule is that a command which never loads `/devforge:specify`'s text still knows the norm. ⚠ **Two seams is the bug, one seam is the fix, zero seams is a different and worse thing.**
- **If a commit in any phase stages a file this plan does not name, STOP and unstage.** Other sessions work in this checkout, and `src/CLAUDE.md` may carry another session's hunks when a phase commits — re-read `git status` first (Trap 1). *(corrected 2026-10-02 — R3: the second sentence read "`src/CLAUDE.md` is dirty with another session's work.", true on 2026-09-21; the file is clean on 2026-10-02)*

---

## Non-goals

- **No edit to `/devforge:plan`** (D1). Its surface arm, its Risk Assessment row and its `**Unconfirmed exclusions**:` line are untouched.
- **No edit to `/devforge:specify`** (D5). It is the one command already compliant.
- **No edit to `src/constitution.md`** (D7), and no back-port for installs constituted earlier.
- **No new artifact route at `/devforge:breakdown`, `/devforge:implement`, `/devforge:fix`, `/devforge:review` or `/devforge:verify`** — Anchor F's five (D4). The rule requires telling the user and nothing more.
- **No mechanical detector, no `verify-*` verb, no gate and no Python.**
- **No rewrite of shipped history** — the plan-99 `CHANGELOG.md` entry, the plan-99 `PLAN-STATUS-ARCHIVE.md` entry and plan files 98, 99 and 100 stay byte-intact (D6).
- **No change to the identity-evidence definition, the feature-surface sweep, or anything that decides which surfaces count.**
- **No back-port into shipped installs.** They arrive via `install.sh` / `update.sh`.
- **No touch of any external install, and no client, install, repo, branch, ticket or product identifier in any tracked file.**

---

## Context for next session

⚠ **Evidence class, repeated: a contradiction read directly out of two files in THIS tree on 2026-09-21 — NO consumer incident recorded here, NO measurement, NO run.** The clash was surfaced by a relayed consumer run whose artifacts are not readable from this repo and which is named nowhere. ⚠ **All line digits drift — grep the quoted text, never the digits.**

**The one sentence that governs everything here: an always-on rule must not set a default that a lifecycle stage structurally cannot execute, and where it does, the rule moves.**

⚠ **Phase 0 is the gate. It CLOSED on 2026-09-21, so the build phases may start — see `### Phase 0 close record`.** *(corrected 2026-10-02 — R4: this read "Phase 0 is the gate and nothing below it may start.", a drafting-time sentence the close left standing; it contradicted the CLOSED status — an internal inconsistency found during the re-check, not tree drift)* *(added 2026-10-02 — Phase 3: they have run — Phases 1–4, 2026-10-02; see `## Build record — 2026-10-02`)*

### Traps

**Trap 1 — `src/CLAUDE.md` can be dirty in this checkout.** *(corrected 2026-10-02 — R3: this heading read "`src/CLAUDE.md` is dirty in this checkout."; not in force on 2026-10-02 — see R3)* This trap is NOT in force on 2026-10-02: `git status --short src/CLAUDE.md` is clean, and the `### Format` hunks described below landed in commit `e2a3862`, 20 seconds before this plan's own commit `fddbc7d`. The text below is kept as verified on 2026-09-21, and its two routes are the procedure when `git status` shows `src/CLAUDE.md` dirty at build time; a clean file is staged normally, by explicit path, with `git diff --cached --stat` checked after staging. ⚠ **The `git status` read is unconditional — see R3.** *(added 2026-10-02 — R3)* Verified 2026-09-21: the file carries **UNCOMMITTED** hunks from other work — the `### Format` commit-subject correction (the corrected `[WIP] task: <title> (Task NNN)` / `[checkpoint] pre-task NNN` / `[WIP] <label>` subjects and the wrapper variants) and a `### Crash Recovery` line, described in `CHANGELOG.md`'s `### Fixed` entry under `## [2.0.12]`. **Those hunks are NOT this plan's.** ⚠ **`git add src/CLAUDE.md` would sweep another session's work into this plan's commit.** Two acceptable routes, and no third:
  1. **Wait** until those hunks are committed by whoever owns them, then stage the file normally.
  2. **Stage only the item-17 hunk with a patch** — `git diff -U0 -- src/CLAUDE.md > <scratch>/item17.patch`, edit the patch down to the single hunk, then `git apply --cached <scratch>/item17.patch`.
⚠ **`git add -i` and `git add -p` are not available: both require an interactive terminal, and this harness runs shell commands non-interactively.** ⚠ **Re-read `git status` before assuming the file is still dirty — another session may have committed since.**

**Trap 2 — the two item numbers.** The rule is item **17** in `src/CLAUDE.md` `### Always` and item **20** in `DEVELOPMENT-STATUS.md`. **A sweep that greps one number misses the other.** Grep the rule's words, not its number.

**Trap 3 — sub-question 6 has TWO non-decision arms.** The **first** concerns a §6 entry (*"free text that neither keeps nor lifts the exclusion"* → *"the spec's §6 Out of Scope exclusion stands"*) and is **NOT in conflict** with item 17: a standing §6 exclusion is an exclusion the user stated in their own words, which item 17 already permits. **Only the second — the surface arm (Anchor B) — is in conflict.** ⚠ **An edit that touches both breaks a correct arm.**

**Trap 4 — the `Never` item 7 pointer.** `Never` 7 says to take the option the command names (Anchor C). **Anyone "fixing" this clash by leaning on `Never` 7 has picked Option ESCAPE-CLAUSE without noticing** — they have made the command's named outcome win by rule, which is exactly the escape hatch that option was rejected for.

**Trap 5 — rewriting history.** `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md`, `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md`, the plan-99 `CHANGELOG.md` entry and the plan-99 `PLAN-STATUS-ARCHIVE.md` entry carry the old text **by design.** They are the record of what shipped, not a bug list, and a sweep that "corrects" them destroys the only account of how the clash arose. `98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md` is the record of `### Never` item 7 (Anchor C), which this plan does not edit either — **all three plan files stay byte-intact.**

**Trap 6 — line digits drift.** Every `file:line` in this plan was true on 2026-09-21. **Grep the quoted text, never the digits.** *(added 2026-10-02 — R4: the digits R4 corrects were re-read on 2026-10-02, and each carries an R4 marker naming the digit it replaced; they drift like the rest)*

**Trap 7 — assuming `/devforge:specify` needs the same sentence.** It is the one command **already compliant** (`src/commands/specify/main.md:399`), and under (c) it is also the **owner of the definition the rule derives from** (`:658` *(corrected 2026-10-02 — R4: was `:652`)*). **Editing either paragraph is how this fix grows the drift site back.**

**Trap 8 — the two downstream lists.** Plans 99 and 100 name **four** commands riding the rule alone; Anchor F's grep covers **five**, adding `/devforge:breakdown`. **Re-derive the grep rather than copying either list.**

**Trap 9 — reading plan 100's D5 as settling this.** Plan 100 D5 decided **NO edit** to item 17 — for an unrelated reason (how *"a present user"* reads against the command rule), not for this clash, which it never names. **It is not a prior rejection of this plan's D1.**

### File anchors

- **`src/CLAUDE.md`** — `### Always` item 17 (**the only file Phase 1 edits**); `### Always` item 2 (*"Constitution is law"*); `### Never` item 7 (read-only, Anchor C).
- **`src/commands/plan/main.md`** — Phase 1.3 sub-question 6, both non-decision arms; the `**Unconfirmed exclusions**:` line on the Phase 3 approval summary (`:661` *(corrected 2026-10-02 — R4: was `:640`)*, the Phase 2 named check). **Read-only in every phase** (D1).
- **`src/commands/specify/main.md`** — the `**Covering a user-facing surface takes two entries.**` paragraph in Step 4.3 (`:658` *(corrected 2026-10-02 — R4: was `:652`)*, **the definition (c) derives from**); the *"The value you supply for a surface"* paragraph in numbered step 2 (`:399`, the surviving `cover it` default); numbered step 3 (**Deferral path**). **Read-only** (D5).
- **`src/constitution.md`** — `### 6.1 Minimal Changes [universal]`, last sentence. **Read-only** (D7).
- **`src/agents/architect.md`** — Rule 9's **Out-of-scope-respect forcing step**, uncovered-surface direction. Phase 2 sweep, read-only unless a finding.
- **`src/agents/devils-advocate.md`** Rule 6 and **`src/commands/grill/references/design-attack-checklist.md`** — the `[excluded by the model]` entries. Phase 2 sweep, read-only unless a finding.
- **`src/commands/verify/main.md`** — the **Changed files** bullet of the ac-verifier brief, Anchor F's one grep hit; and **`src/agents/ac-verifier.md`** — `## Input` item 7, **Changed files**. Phase 2 sweep, read-only unless a finding. *(added 2026-10-02 — R1)*
- **`src/manifest.json`** — the `generated:coreLLM` → `CLAUDE.md` mapping (Anchor J). Read-only.
- **`DEVELOPMENT-STATUS.md`** — numbered item 20. **Phase 3 edits it.**
- **`CHANGELOG.md`** — the plan-99 entry under `## [2.0.12]` (byte-intact) and the in-flight section (Phase 3 appends).
- **Read-only records:** `PLAN-STATUS-ARCHIVE.md` (`## Entries`, the plan-99 entry), `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md` (D8, D10, `**What landed:**`, `## Residuals`), `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md` (D5, D10).
- **Tests:** `tests/lib/test_constitute_helper.py`, `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py`, `tests/scripts/test_claude_emitter.py`.

---

## When resuming work

**The build is DONE (2026-10-02): Phases 1–4 have run — Phase 1 BUILT (`b122abe`), Phase 2 a verified no-op, Phase 3 the ledger commit, Phase 4 a test run (354 passed, 2 skipped).** *(added 2026-10-02 — Phase 3)* What remains is the maintainer's close of the plan. **A resuming session reads `## Build record — 2026-10-02` first**, then the Status line. Steps 1–9 below are kept as the record of how the build was run.

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation.
2. **Read `### Phase 0 close record` first** — it sits at the end of `## Decisions to ratify` and **reads CLOSED 2026-09-21**: D1–D7 and OQ-2 ratified as recommended, **OQ-1 moot by D2's outcome and NOT ratified**. Build phases may start, and **the record — not the decisions above it — is what says what each phase must do.** *(added 2026-10-02 — Phase 3: the phases have run — see the dated line above step 1)* ⚠ **The close was a single blanket directive with no per-item deliberation, so every counter-argument in this plan is still live on its own merits.**
3. **Re-verify every anchor by grepping the quoted strings**, never the digits: `Scope follows what the user sees`, `Deciding it yourself`, `cover it unless you can name`, `any exclusion as yours`, `the surface stays uncovered`, `Never record your choice as the user's`, `adds no affected area and no acceptance criterion`, `` The value is `cover <surface>` ``, `Covering a user-facing surface takes two entries`, `the exclusion standing, the surface uncovered`, `Which user-facing surfaces a change covers is set by what the user sees`, and Anchor F's `user-facing surface\|shows the feature` across the five command directories. *(added 2026-10-02 — R1: on 2026-10-02 Anchor F's grep returns exactly one hit — the **Changed files** bullet of the ac-verifier brief in `src/commands/verify/main.md`, classified in `### Re-check against the live tree (2026-10-02)`, R1, as reading a surface an AC names. Any OTHER hit is new and is classified the same way before building)* *(added 2026-10-02 — R4: that section's R4 table is the digit register as of `HEAD` `8e61645`; re-verify against it by the quoted text, never the digits)* ⚠ **After Phase 1 the `src/CLAUDE.md` hits have changed BY DESIGN: under (c), `Deciding it yourself` survives, `cover it unless you can name` goes to ZERO in `src/`, and `any exclusion as yours` survives with a capitalised lead-in. A changed hit there is the built state, not a regression — and a zero on the middle string is the expected outcome, not a deletion of the upstream default.**
4. **Re-check the plan number.** 100, 101, 102, 104, 105, 106 and 107 were taken in this checkout on 2026-09-21 and 103 was vacated by an earlier renumbering. **Another session may have taken 108 since.** ⚠ **Find a sibling plan by its TITLE, never by assuming a number.**
5. **Route every markdown edit through instruction-author → instruction-reviewer**, and every Python edit through python-engineer → python-reviewer. ⚠ **This plan expects NO Python; a phase that needs some has left its scope.**
6. **Commit by explicit path, never `git add -A`.** Re-read `git status` first — **Trap 1's routes apply when it shows `src/CLAUDE.md` dirty** — and read every shared ledger live. **Never touch another session's plan file.** *(corrected 2026-10-02 — R3: this read "with **Trap 1 (the dirty `src/CLAUDE.md`) in force.**", true on 2026-09-21; the file is clean on 2026-10-02, and the explicit-path rule and the `git status` read stay unconditional)*
7. **After each phase, cross-check.** Grep the amended wording and every string this plan quotes, and **fix any dangling reference in the SAME change.**
8. **Keep the evidence class attached.** Any summary of this plan repeats it: **a contradiction read out of this tree; no consumer incident recorded here; nothing measured.**
9. **Keep the root-cause finding attached to the fix.** The defect was **an always-on rule restating a per-command outcome**, and the fix is **single ownership** — the rule owns the invariant and the definition, the command owns the outcome. ⚠ **A summary that reports only "item 17 got a better sentence" has dropped the part that prevents the next recurrence**, and `### Phase 0 close record` states how the principle stands: **ratified by ratifying Option SINGLE-OWNER, with NO separate maintainer statement about the principle itself.**
