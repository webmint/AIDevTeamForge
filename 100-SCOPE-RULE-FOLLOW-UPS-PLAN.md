# 100 — Scope Rule Follow-Ups Plan

**Created**: 2026-09-19
**Status**: DRAFT (frame) — the detailed plan is owed by a new session; nothing ratified, nothing built.

Plan 99 found six residuals during its build and deliberately left them unfixed. This plan takes them up. The maintainer's 2026-09-19 directive sets the direction for five of them. Item 1 gives the AC-conflict escalation at `/devforge:plan` an orchestrator-side arm for a reply that decides nothing. Item 3 closes a PHASE 2.5 seam that lets an uncovered surface's files into the plan as ordinary additions. Item 4 makes a model's no-evidence deferral visible at spec approval. Item 5 makes surface questions always bundled. Item 6 makes research check 12b's message name the Phase 2.4 family it counts, 2.4e included. Item 2 is a directive rather than a fix: clarifying questions are asked even in auto mode. Its scope is the first question the detailed plan puts to the maintainer. This file is a frame. It records what, why and where, and what is still open. The design, the D-items and the phases are owed by the detailed plan.

---

## Origin & evidence

⚠ **Evidence class, to be repeated in every summary of this plan: NO incident. Items 1 and 3–6 are gaps found by reading during a build — predicted, nothing observed, nothing measured. Item 2 is a maintainer directive.**

- **Source.** `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md` `## Residuals (found during the build, not fixed)`, items 1–6, found during its build on 2026-09-19. Plan 99 is DONE (build); its Phase 0 close, D10, Phase 1 and Phase 2 commits are `5923e04` / `cf6dc1c` / `6a786b3` / `6838c1c`. Its Phase 3 consumer e2e is deferred and not run. Item N here is plan 99's residual N.
- **Directive.** The maintainer gave it on 2026-09-19 in Ukrainian. English paraphrase: fix items 1, 3, 4, 5 and 6; for item 2, *"clarifying questions are needed even in auto mode"*.
- ⚠ **The orchestrator's reading, not the maintainer's words.** The maintainer wrote "3" twice and did not write "4". The orchestrator read the second "3" as item 4 and told the maintainer so. The item list above rests on that reading.
- **Context for item 2.** Plan 99's D10 records that the benchmark operator's blind protocol answers every content question with a delegation. So asking in auto mode would route those runs through plan 98's delegated path, which records the delegation, instead of through auto defaults applied without a question. This says why the directive matters. It is not evidence that anything failed.

Every quoted site below was checked against the tree on 2026-09-19. ⚠ Line digits drift — **grep the quoted text, never the digits.**

---

## Items

### Item 1 — A non-decision arm for the sibling AC-conflict escalation (FIX)

**Sites.**
- `src/commands/plan/main.md`, the `[Rule 5: …]` note in the plan template's `### Key Design Decisions`. An identical reachable tuple with opposite required outputs *"is an acceptance-criteria conflict, not an implementation gap to bridge: surface it to the user as a product question naming both criteria and the shared tuple — the architect escalates it per its Rule 6 (termination), triggered by its Rule 9 rejected-alternative checkability step"*.
- `src/agents/architect.md` Rule 9, `**Rejected-alternative checkability forcing step:**`: *"**escalate to the user** per Rule 6 (the termination rule), naming the two ACs and the identical tuple"* — listed as the escalation's source, not as a place the arm is written.

**Gap.** Neither site says what happens on a reply that decides nothing. Two readings of the rules fit that reply, and the text does not pick between them:
- **Reading (a): a content question.** The AC-conflict question counts as one of `plan/main.md` PHASE 3's *"decision points the spec didn't resolve"*. PHASE 3 names a channel for a model-supplied answer, so `src/CLAUDE.md` `### Never` item 7 treats the question as one that asks for content. On a hand-back — and on a reply that names no option, which item 7's first sentence treats the same way — the model picks which AC wins, marks it `[default applied]` and lists it under "Decision Points Resolved". That is a product decision the Rule 5 note sends to the user (*"surface it to the user as a product question"*), taken by the model.
- **Reading (b): a run decision.** The command does not classify the question, and item 7 reads *"A question the command does not classify decides what the run does."* The question is asked once more. On a second such reply, with no option named for it, item 7's *"end the turn having written nothing"* applies, and the `/devforge:plan` run stops at that question.
- The gap is therefore an ambiguity between two rules. Reading (a) is the more dangerous one, because it produces a model-made product decision that looks resolved.

**Precedent.** Sub-question 6 in `plan/main.md` Phase 1.3 has a non-decision arm in both directions:
- **The §6 direction** (plan 98, plus plan 99's D5 line). After a second non-deciding reply, *"the spec's §6 Out of Scope exclusion stands — record no override of it"*. The architect re-scopes to sub-question 5's minimal change, and the §6 entry is listed on PHASE 3's `**Unconfirmed exclusions**:` line.
- **The uncovered-surface direction** (plan 99). The surface stays uncovered, and the user is told that covering it needs a spec revision. A Risk Assessment row ends *"left uncovered; the user did not decide it"*, and the surface is listed on the same PHASE 3 line.
- Neither arm records its outcome as the user's pick. Only the surface arm writes a Risk Assessment row.

**Direction.** The named non-decision arm lands on the orchestrator side, in `plan/main.md`: re-ask once, then take a named outcome that writes a visible record and is never recorded as the user's decision. It goes at the Rule 5 note, plus a routing sentence in Phase 1.3 if the detailed plan finds the orchestrator needs one — the way sub-question 6 carries its arms, neither of which is in `architect.md`. The Rule 9 sentence quoted under Sites stays as it is and gains no arm, because the architect never receives the user's reply: Phase 1.3 states that the architect *"emits requests; it does NOT invoke anyone"*, and the orchestrator is the one that surfaces the escalation and receives the reply.

**Enumeration owed.** The detailed plan lists every architect escalation to the user and confirms that each has an orchestrator route that carries a named non-decision arm. On 2026-09-19 a grep for `escalat` found these sites:
- **In `architect.md`, six sites:**
  - Rule 6: *"You decide, or you escalate to the user on spec-level ambiguity"*.
  - `### Termination rule — you always decide`: *"(in which case, stop and escalate to the user)"*.
  - `### How to consult` step 1: *"escalate per the Out-of-scope-respect step in Rule 9"*.
  - Rule 9's three escalation sentences — the Out-of-scope-respect step (*"naming the §6 entry and why you believe it cannot stay excluded"*), its opposite direction (*"**escalate it to the user** per Rule 6, naming the surface and what the user sees there"*), and the rejected-alternative checkability step quoted above.
- **In `plan/main.md`:** sub-question 6, the Rule 5 note, PHASE 2.5 step 6 (*"or escalate the §6 concern to the user per its Rule 6 (termination)"*), and the PHASE 3 `**Unconfirmed exclusions**:` line, which records escalations rather than raising one.

- Open: which rule governs the AC-conflict question, stated explicitly. RECOMMEND: exclude it from PHASE 3's `[default applied]` arm, because a product question the spec leaves in conflict is never a model default. In auto mode, PHASE 3's auto-mode bullet raises the same question — *"Apply model's recommended defaults to any decision the spec left as `[default applied]` or that the plan surfaces fresh"* — and item 2's scope answer settles that half.
- Open: where an unresolved AC conflict is recorded. The candidates are a Risk Assessment row, plus either the existing `**Unconfirmed exclusions**:` line or a new PHASE 3 line. That line today covers only sub-question 6's escalations, so reusing it widens its definition.
- Open: what the Key Design Decision records while the conflict stands. The Rule 5 note already rules out *"recording a discriminator parameter that forces the tuples apart"*.
- Open: whether the enumeration also covers `/devforge:breakdown`. The architect's `description` names that command, and `breakdown/main.md` has its own human escalations. Among them are PHASE 2 sub-question 4's plan-level implementability gap, and two triggers in the Agent Assignment section: *"If splitting is genuinely impossible, escalate to the human."* and *"If the owning stack's implementer is not generated for this project (not all projects generate all agents), split or escalate to the human — never fall back to `architect`"*. This list is illustrative, not complete; the new session re-greps `escalat` in `breakdown/main.md` for the full inventory.

### Item 2 — Clarifying questions are asked even in auto mode (DIRECTIVE)

**Scope.** Plan 99's residual 2 covers sub-question 6 only. The directive is wider, and the maintainer's paraphrased words above are its whole direction. Nothing in this item is designed before the scope answer.

**Auto-mode branches today.** On 2026-09-19, a grep for `auto mode` / `auto-mode` / `mode=auto` / `DEVFORGE_AUTO_MODE` over `src/commands/` hit only three files, and the Python side of auto mode lives only in specify's helper:
- `plan/main.md` PHASE 3: *"**If auto mode is active** (…): do not pause for clarifying questions during plan creation. Apply model's recommended defaults …"*.
- `breakdown/main.md` PHASE 4: *"**If auto mode is active** (…): do not pause for clarifying questions during decomposition."*
- `specify/main.md` Phase 2:
  - `### Mode detection`: `detect-mode` persists `auto` on any of three C-strict signals — `DEVFORGE_AUTO_MODE=1`, `--auto`, or `"auto mode is active"` / `"auto mode still active"` in the reminder text.
  - The per-decision-point protocol's **Auto path** records `set-dp-default-applied` without asking.

**The two detection rules differ.** Plan and breakdown detect auto mode *"via `<system-reminder>` about auto mode, or explicit user instruction to operate autonomously"*. Specify counts no user prose: *"User natural-language prose is not a signal."*

**Python gates.** Both gates are in `src/devforge/lib/_specify/_cmds_phase2.py`, and both exit 2 in auto mode:
- `set-dp-answer`: *"set-dp-answer: mode=auto rejects user-answer setter (use set-dp-default-applied)"*.
- `set-dp-default-applied --delegated-reply`: *"--delegated-reply is for mode=interactive only"*.

⚠ Both messages are split across source lines in the Python, so grep a fragment such as `rejects user-answer setter`. `specify/main.md`'s per-decision-point protocol quotes each one whole, on a single line.

Any scope under which specify asks in auto mode must change these gates. That work goes python-engineer → python-reviewer, with a test for every function, run in the same turn.

**Scope options — the FIRST question put to the maintainer, not picked here:**
- **(a) Escalations only.** Sub-question 6 in both directions, plus the AC conflict (item 1).
  - Blast radius: `plan/main.md` — PHASE 3's auto-mode bullet plus the plan-side sites item 1 enumerates. Zero Python. The specify and breakdown auto paths are unchanged.
- **(b) Product and scope questions.** Everything in (a), plus specify's `scope_boundaries` decision points.
  - Blast radius: (a), plus specify Phase 2's auto path for that category, the two Python gates, and the auto-path half of plan 99's D4(b) and D10 P2.
- **(c) Every clarifying question in specify, plan and breakdown** — the literal reading of the directive.
  - Blast radius: (b), plus every other specify decision-point category, breakdown PHASE 4's auto-mode bullet, `detect-mode`'s role, and plan 98's `**Defaults applied**:` lines, whose auto-mode entries come from the branches this option removes.
  - No ask-free branch would remain in those three commands. The detailed plan must state what, if anything, auto mode still changes there.

**Interactions the detailed plan resolves:**
- Plan 99's D10 P2 (the model's evidence-dependent default) and D4(b) (the value the model supplies, and its binding of the deferral path). Both are written for the auto path and the delegated path alike.
- `src/CLAUDE.md` `### Never` item 7. A delegated reply to a question asked in auto mode takes the delegated path, which specify's `--delegated-reply` gate rejects today.
- Plan 98's `**Defaults applied**:` lines at specify Step 5.1 and plan PHASE 3.
- `src/CLAUDE.md` `### Always` item 17, always-on in every consumer session. It splits asking from deciding: *"Deciding it yourself — handed back or never asked — cover it unless you can name what the user would see differently without it"*, and *"Ask a present user about a surface you suspect but cannot evidence; deciding yourself, leave it an open question"*. Any scope that asks about surfaces in auto mode changes when "never asked" occurs and what "a present user" means, so item 17's text is in the blast radius.
- Plan 99's Trap 7 (`## Context for next session`). It reads "raised with the user" — plan 99's term for item 17's *"raised with them"* arm — in auto mode as *"listed at the approval summary — Step 5.1's `**Defaults applied**:` and §6 in full — not a question"*. Any scope that asks about surfaces in auto mode overturns that reading where it asks — at specify, the command Trap 7 names, under (b) and (c). Plan 99 is amended only by a dated note, per this plan's Non-goals.

**Owed `claude-code-guide` checks (house rule):**
- Whether `AskUserQuestion` is available and answered while Claude Code's auto mode is on. The only record is an observation: the orchestrator called it during auto mode in its 2026-09-19 session and got an answer. That is not a vendor statement. The three approval gates already ask via `AskUserQuestion` in auto mode — `plan/main.md` PHASE 3's auto-mode bullet ends *"The user reviews defaults at the approval gate below."*, `breakdown/main.md` PHASE 4's ends *"The user reviews the breakdown at the approval gate below."*, and specify's `### Step 5.3 — Approval prompt` has no auto-mode branch — so the spec text already assumes asking works in auto mode. That is an assumption, not evidence: the check covers those three gates as well as the questions this item adds.
- What Claude Code's own auto mode is, as distinct from the framework's two detection rules above.

- Open: the scope pick — (a), (b) or (c).
- Open: whether the pick needs a constitution edit. `src/constitution.md` does not mention auto mode today (grep 2026-09-19). Any edit is flagged as its own decision.

### Item 3 — The PHASE 2.5 step 4 seam (FIX)

**Site.** `plan/main.md` PHASE 2.5 step 4: *"Check the reverse: does the plan's File Impact list files NOT in the spec's Affected Areas? If yes, note them as additions discovered during planning (add to the plan's File Impact table with a note)."*

**Gap.** Take a file that serves a user-facing surface showing the feature — a surface the spec neither covers nor excludes. Step 4 lets that file into File Impact with a note, and sub-question 6's uncovered-surface escalation never runs.

**Direction.** Such a file is not an addition discovered during planning. It routes to sub-question 6's opposite-direction escalation. Every other addition keeps today's note.

- Open: how step 4 recognizes a surface-serving file. `plan/main.md` has no identity-evidence definition — under `src/`, the term appears only in `research/main.md` and `specify/main.md` (grep 2026-09-19). The definition's substance is also in `src/CLAUDE.md` `### Always` item 17: *"A surface shows the feature the user named only on cited user-visible evidence — the same title, label or translation key, route, or tab or mode; shared or different code, requests or data are never evidence or a reason to exclude."* Both actors at `/devforge:plan` load it: the orchestrator session, and the `architect` subagent. Plan 97's OQ-1 records, from a `claude-code-guide` check, that a custom subagent loads every `CLAUDE.md` level the main conversation loads unless its definition sets `omitClaudeMd`, and a grep for `omitClaudeMd` over `src/` and `scripts/` returns zero hits (grep 2026-09-19). The detailed plan picks one of four:
  - step 4 restates the definition;
  - step 4 points to it;
  - step 4 relies on sub-question 6's own wording;
  - step 4 relies on item 17 and restates nothing.
- Open: whether the route re-enters Phase 1.3, which is the shape PHASE 2.5 steps 6–8 already use.

### Item 4 — Model deferrals visible at spec approval (FIX)

**Site.** `src/devforge/lib/_specify/_render.py` `_approval_summary`, which is what `render-summary` prints at specify Step 5.1.
- It lists the `default_applied` decision points (`**Defaults applied**:`) and every §6 item in full.
- It lists no `deferred_open_question` decision point and no Risk.
- Step 5.4's handoff block (`_plan_handoff_block`) renders only on the approve branch. It counts both kinds and names neither.

**Gap.** Step 2 of specify's per-decision-point protocol has the model defer a surface with no identity evidence: `set-dp-deferral --deferral-kind open_question --reason "deferred by the model — why it may be the same feature: <reason>"`. A surface deferred that way is invisible at spec approval. Plan 99's D10 recorded this as the cost of declining the peer's `[unresolved by the model]` form. The deferral is the model's route *"on the auto path and the delegated path alike"*, so this item does not depend on item 2's scope.

**Direction.** Add a conditional Step 5.1 bullet listing those deferrals, omitted when there are none, as `**Defaults applied**:` is.
- This is Python plus tests.
- The Step 5.1 docs, which today say *"four bullets, plus a `**Defaults applied**:` bullet"*, change with it.
- When the bullet is built, every record of D10's cost — that Step 5.1 does not list §8 deferrals — changes in the same commit, with one rule per file type:
  - `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md`: a dated note at each of three sites, per this plan's Non-goals — D10's recorded cost (*"a §8 deferral is not listed in specify's Step 5.1 summary"*, ~:299), `## Residuals` item 4 (*"A model's no-evidence deferral is not visible at spec approval."*, ~:601), and Trap 7's D10 amendment (*"which Step 5.1 does not list — the cost D10 records"*, ~:640).
  - Repo `CLAUDE.md`'s plan-99 index line (*"specify's Step 5.1 does NOT list §8 deferrals"*, ~:92) and `PLAN-STATUS-ARCHIVE.md`'s plan-99 entry (~:166 — *"lists defaults and §6 but not §8 deferrals"*, *"summary lists neither §8 deferrals nor Risks"* and *"Specify's Step 5.1 does not list §8 deferrals."*): amended in the same commit, because ledger lines state current state.
  - `CHANGELOG.md`: a new entry for this plan's change under `## [Unreleased]`. Plan 99's `feat(scope)` entry (*"but NOT §8 deferrals"*, ~:13) is not rewritten.
  - This inventory is as of 2026-09-19, and more sites may appear. Before building, re-grep `Step 5.1`, `§8 deferral` and `visible at spec approval`; a new site takes its file type's rule.

- Open: which deferrals the bullet lists — model deferrals only (the reason starts `deferred by the model`), or every `deferred_open_question` decision point. The second set also holds user punts and the follow-up-cap transition, whose reason is `exceeded follow-up cap`.
- Open: the first choice makes a free-text reason prefix load-bearing. The detailed plan either accepts that or names another carrier.

### Item 5 — Surface questions always bundled (FIX)

**Site.** Specify's per-decision-point protocol, interactive path: *"**Bundling**: when ≥4 related questions exist AND they are NOT conditionally dependent on each other, bundle them into a single `AskUserQuestion` call"*. `### Question rounds` adds *"Decision points about separate surfaces are related, and none is conditionally dependent on another, so they qualify for the bundling rule"*.

**Gap.** Plan 99's OQ-4 ratified *"one decision point per uncovered surface, bundled per call"*. Below the ≥4 threshold the bundling rule does not apply, so two or three surface decision points can each be asked in a separate call. Above the threshold the rule cannot be met either. On two observations — plan 98's OQ-8 docs page and the tool schema loaded in the orchestrator's 2026-09-19 session, both recorded in the first Open bullet below, neither the owed `claude-code-guide` check — one call holds at most 4 questions. So 5 qualifying questions do not fit *"a single `AskUserQuestion` call"*, and neither does a full round under `### Question rounds`' *"Up to 5 questions per round."*: a 5-question round takes two submissions.

**Direction.** `scope_boundaries` decision points about user-facing surfaces are always bundled, in as few `AskUserQuestion` calls as the tool allows.

- Open: the per-call question limit, a Claude Code fact owed a `claude-code-guide` check. Plan 98's OQ-8 check found an Agent SDK docs page stating *"1-4 questions with 2-4 options each"*. A second observation agrees: the `AskUserQuestion` schema loaded in the orchestrator's 2026-09-19 session caps `questions` at 4 items (`maxItems: 4`), with 2–4 options per question. Neither is a vendor statement from that check.
- Open: how specify's round and bundling rules fit the per-call limit. RECOMMEND:
  - A round is one `AskUserQuestion` call, holding as many questions as one call accepts — 4 today, pending the owed check. The numbered-markdown fallback holds the same count per round. *"Up to 5 questions per round."* is replaced to match. The wording names the call's capacity rather than a literal 4, because a literal goes stale if the vendor limit changes.
  - Total questions stay uncapped: rounds continue until every decision point is covered, as `### Question rounds` already says (*"whether all decision points have been covered, not on subjective sufficiency"*). The per-DP cap of 3 follow-ups stays.
  - The ≥4 threshold is dropped: independent questions are always bundled, up to one call's capacity, and conditionally dependent ones still are not. The priority order (*"scope > breaking changes > …"*) decides which questions go first.
  - This is wider than item 5, whose residual and Direction name surface decision points only: it changes specify's general round and bundling rules, so the detailed plan ratifies it at Phase 0 rather than taking it silently.
  - The maintainer's input (English paraphrase, given 2026-09-19), separate from the RECOMMEND above: more questions are acceptable, and a reasonable per-round limit is wanted. The RECOMMEND is the proposed answer to that.

### Item 6 — Research check 12b's message (FIX)

**Site.** In `src/devforge/lib/_research/_cmds_render_verify.py`, a grep for `Phase 2.4 must probe the runner-up frame` returns two sites:
- the verify docstring's check-12 entry;
- check 12b's violation message: *"Phase 2.4 must probe the runner-up frame with at least one finding (record-finding --framing runner-up ...)"*.

A third site says the same thing in the comment above the message (*"so Phase 2.4 probed the runner-up frame"*), and that grep does not match it.

**Gap.** Since plan 99, Phase 2.4e rows carry `--framing runner-up` when the surface-count frame holds the runner-up slot (`research/main.md` Phase 2.4e), and check 12b counts any finding tagged that way. Plan 99's residual 6 records the message as not falsified, so this is a completeness fix, not a correction. The message's "Phase 2.4" already stood for more than Phase 2.4 alone: 2.4b and 2.4c findings satisfied check 12b before plan 99, because `research/main.md`'s `**Downstream impact.**` paragraph named `Phase 2.4 / 2.4b / 2.4c` findings as the ones tagged `--framing runner-up` until plan 99's Phase 1 commit `6a786b3` appended `/ 2.4e`, while Phase 2.4d records only `--framing "primary"`.

**Direction.** The message, the docstring's check-12 entry and the comment above the message name the phases whose findings count the way `research/main.md`'s `**Downstream impact.**` paragraph does: `Phase 2.4 / 2.4b / 2.4c / 2.4e`. They name 2.4e with its siblings rather than alone, because naming only 2.4e would imply that 2.4b and 2.4c findings do not satisfy the check. The maintainer's directive to fix item 6 stands, and this is how it is fixed.

- Open: whether a test pins the new wording. In `tests/lib/test_research_helper.py`, `TestVerifyCheck12`'s check-12b test asserts only the substrings `runner_up_framing` and `runner-up` — its check-12a test also asserts `Phase 2.3b` — and no file under `tests/` contains `probe the runner-up` (grep 2026-09-19).

---

## Tripwires

- **Plan 75's tripwire, both halves:** zero gates, zero validators, zero new `verify-*` numbers, zero new research check numbers. Item 6 rewords check 12b's message and adds no check.
- **Python only where named:** item 4, item 6, and item 2 if its scope reaches specify.
  - Python goes python-engineer → python-reviewer, with a test for every function, run in the same turn.
  - Every markdown edit goes instruction-author → instruction-reviewer.
  - Every Claude Code fact is checked through `claude-code-guide`.
- **No `disable-model-invocation` change:** 17 model-invocable / 4 human-typed-only. On 2026-09-19 the flag sat on `init-forge`, `generate-docs`, `configure` and `constitute`, out of 21 commands.
- **No constitution edit is expected.** If item 2's scope needs one, it is flagged as its own decision.
- **No back-porting into shipped installs.** The frozen benchmark install is never touched.

---

## Non-goals

- **Rewriting plan 99's ratified text.** Items 2 and 4 amend it only through dated notes, per plan 99's own convention.
- **Mechanical detection of a delegation or of "the same feature".** Both stay model judgment, the bounds plans 98 and 99 record.
- **Auto-mode changes outside `/devforge:specify`, `/devforge:plan` and `/devforge:breakdown`**, the only commands with an auto-mode branch today.
- **Anything specific to the benchmark**, and any client, component, ticket or benchmark path in this repo.

---

## When resuming work

1. **Read in full:** this frame, then `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md` (D1–D10, the build-time decisions, the residuals), then `98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md`'s D1 (run decisions vs content answers).
2. **Re-verify every quoted site against the live tree.** Digits drift, so grep the quotes.
3. **Ask the maintainer item 2's scope FIRST.** Nothing in item 2 is designed before that answer.
4. **Write the detailed plan in the house shape**, then run Phase 0 ratification. The house shape is:
   - facts;
   - D-items, each with a RECOMMEND and a counter-argument;
   - OQs;
   - a Phase 0 close record;
   - phases, each with a Verify;
   - consumer e2e anchors in pairs — for example, an auto-mode run that asks vs an auto-mode run that delegates;
   - `## Context for next session`.
5. **Commit by explicit path.** Re-read `git status` first — another session may be building in this checkout.
6. **Keep the evidence class attached.** Any summary of this plan repeats it: NO incident, items 1 and 3–6 predicted, item 2 a directive, nothing measured.
