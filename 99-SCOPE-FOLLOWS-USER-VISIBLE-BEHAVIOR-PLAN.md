# 99 — Scope Follows User-Visible Behavior Plan

**Created**: 2026-09-19
**Status**: **✅ DONE (build) 2026-09-19 — Phase 0 CLOSED, the D10 post-close amendment ratified, and Phases 1–2 BUILT.** Phase 0 was closed by a single blanket maintainer directive: every item ratified AS RECOMMENDED, no per-item deliberation supplied (see `## Phase 0 close record`). D10 was ratified after the close by an explicit maintainer pick, not a delegation. Commits: `b8e5d1f` draft / `5923e04` Phase 0 close / `cf6dc1c` D10 / `6a786b3` Phase 1. The Phase 2 docs commit follows this sweep, and no SHA is recorded for it here. **Phase 3 consumer e2e is DEFERRED — a user-driven HARD GATE, NOT run and NOT waived.** Everything here is **build-verified, NOT consumer-validated**, and "done" never means Phase 3 passed. ⚠ Evidence class: ONE observed instance; every other site is predicted; nothing was measured.

Minimality limits HOW a change is built (mechanism, code, abstractions), never WHAT counts as done. Scope follows what the user sees. When the feature the user named is visible on more than one user-facing surface, every such surface is either covered or named to the user as an open question, with the user-visible reason. A different code path, request, use case or builder is never by itself a reason to leave a surface out. When the user hands that question back, the model decides under the same rule and records the decision as its own, with the reason, through the channel plan 98's rule requires for a model-supplied answer.

---

## Expansion note — 2026-09-19

The first draft of this file (the "frame", 134 lines, same day) had the right principle and a thin, partly wrong design. The orchestrator then read the live spec markdown AND the Python helpers, and this rewrite carries every correction below into the facts and decisions that follow. The frame's six facts are replaced by F1–F12, its five decisions grow to D1–D9 plus OQ-1–OQ-5, and the frame's D4 (the plan-side §6 escalation) is now D5.

1. **The enumeration gap — the biggest miss.** The frame's research edit was one sentence in Step 2b, but Step 2b only classifies inbound callers of the changed helpers, and Phase 2.3b's surface-count frame is bound to the call graph the same way (F1, F2). A surface that reaches the same feature through a different request path is never enumerated, so no Step 2b sentence can reach it. A user-facing surface sweep is needed (D3(b)). ⚠ In the observed instance the model found that surface itself, so this gap is PREDICTED; the observed failure sat at the decision.
2. **The research carrier was wrong.** The frame said research has no open-question setter and chose `set-recommended-approach --rationale`. `record-gap` exists, renders under the report's `## Open Uncertainties`, and specify reads that report; `--rationale` reaches specify only as an 80-char picker summary and is gated twice (F3). D3(d) uses `record-gap`.
3. **Specify already has the decision seat and the model-answer channel.** `scope_boundaries` is decision-point category 1, and plan 98 built the delegated path (F4). The frame re-invented both with a §8 entry plus a §6 suffix. What is actually missing is narrower: a sentence that makes each uncovered surface a decision point, a rule for the value the model supplies, and a §6 marker (D4). The frame's "§8 plus a §9 row" clause is not a drafting addition either — specify Step 4.4 already routes a product question that way (F6).
4. **A suffix is cut off where `/devforge:plan` reads §6** — `_render_sec6` keeps the first 80 characters (F7). The marker must be a prefix.
5. **§6 already renders its own " — " suffix** for a cited finding (F5). A second em-dash suffix would read ambiguously — a second reason for a prefix.
6. **The constitution outranks the always-on rule.** `### Always` item 2 makes `constitution.md` law, and §6.1 opens with the strongest text for the exclusion reading (F8, F9). The frame's "no constitution edit" tripwire becomes an explicit decision (D2).
7. **Agent-local text competes too** — architect Rule 9 and devils-advocate Rule 6 (D6, D7).
8. **Vocabulary.** The frame said "place". The codebase's word is "surface" (research Step 2b's `--surface`, the rubric's `affected_area`, Phase 2.3b's surface-count frame), and "user-facing surface" already appears in research Step 2b. Emitted text says "user-facing surface" and defines it once. A behavioral precedent on one surface axis already ships: `qa-reviewer.md` step 6 checks *"that behavior changed on both iOS and Android … is exercised by tests on both platforms, not one"*, and `qa-engineer.md`'s *"**Platform parity**"* bullet asks for parity tests.
9. **The delegated decision was unconstrained.** The frame let the model decide "a covering AC, or a §6 entry carrying the suffix" — which lets it exclude again for the incident's reason. The principle binds the model's answer too (D1, D4(b)).
10. **"Own words" was undefined.** Defined in D3(c) and D4. A `scope` rubric pick of `"one place"` names no surface and excludes nothing research later finds.
11. **Over-inclusion needed its own clause, not only an e2e anchor** (D1, D3(c)).
12. **Specify's "Only ask questions you CANNOT answer by reading the codebase…"** could be read as licence to decide scope from code; the site now says scope is a product question (D4(a)).

---

## Origin & evidence

⚠ **Evidence class, to be repeated in every summary of this plan: ONE observed instance. Every other site is predicted, and nothing was measured.**

- The incident is the same benchmark incident plan 98 records: one consumer install on release 2.0.11, with the evidence held outside this repo. This repo is public, so this plan names no client, no component and no path.
- In an aborted attempt, the model ruled out of scope a second surface that shows the user the same feature, because that surface reaches the data through a different request path. The model itself noted that the surface shows the same feature.
- **What the instance shows, and what it does not.** The model found the second surface on its own, so the observed failure is the DECISION — an exclusion resting on a code-path reason. The discovery-side gap (F1, F2, D3) is predicted: in a run where the model does not notice such a surface, no research step would surface it.
- The benchmark operator stated the principle through a peer session on 2026-09-18, adding that the model should make the recorded decision easy to review.
- Plan 98 fixed the attribution half: a delegated reply is never the user's pick. This plan is the scope half.
- Plan 98 left one interaction this plan must fix. On a reply that decides nothing, its `/devforge:plan` sub-question-6 escalation arm lets "the spec's §6 Out of Scope exclusion" stand. So an exclusion the model itself wrote into §6 at `/devforge:specify` gets entrenched by a delegated reply at `/devforge:plan` (D5).
- On 2026-09-19 the benchmark operator's peer session recommended fixing that §6 entrenchment before plan 98's release, as a side effect of plan 98 rather than a new principle. D5's ship-alone option exists for that reason.
- On 2026-09-19 the benchmark operator's peer session proposed the two parts of D10: identity needs user-visible evidence, and the model's default depends on that evidence.

### Verified structure (2026-09-19)

Each fact was verified against the tree on 2026-09-19 — spec markdown and Python helpers — by the orchestrator, and its quotes were spot-checked by the drafting author the same day. ⚠ Line digits drift — **grep the quoted text, never the digits.**

**F1 — Step 2b sees callers, not surfaces.** `src/commands/research/main.md` *"Step 2b — Trace each caller to its surface and classify scope."* classifies `inbound_callers` rows only — the callers of fix-path helpers that Phase 2.4c Step 2 records with a depth-1 `trace_path(<helper_qn>, mode=calls, direction=inbound)`. Its own bound: *"This gate forces the classification + justification to EXIST for every caller; it cannot force the in/out call to be CORRECT."* `research_helper classify-caller-scope` (`_research/_cmds_dataflow.py` `cmd_classify_caller_scope`) validates only that the `(helper_qn, caller_qn)` pair was recorded, that `--surface` and `--justification` are non-empty, and that `--scope` is `in` or `out`. Nothing constrains what an `out` justification rests on.

**F2 — No research step enumerates the surfaces that show the named feature.** Phase 2.3b's *"Surface-count frame"* reads *"the named surface is NOT the only entry point — other surfaces reach the same shared symbol,"* with *"falsifier = the inbound `trace_path` of that shared symbol"*, and defers the question: it *"is still mechanically probed downstream by Phase 2.4c's caller enumeration + Step 2b's per-caller surface trace."* Phase 2.4 sweeps the SAME file (mandatory in bug mode on an inline expression); Phase 2.4b searches for the canonical FIX pattern; Phase 2.4c Step 4's data-flow trace is skipped when *"`desired.value` is expressed purely in user-facing terms with no identifiable code-symbols"*. Every one of them starts from code the change touches, so a surface that shows the feature through a different request path is never enumerated. Phase 2.4d (click-handler-to-write-boundary trace) already exists, so the next free letter is 2.4e.

**F3 — Research's open-question carrier is `record-gap`, not `--rationale`.**
- `research_helper record-gap --dimension <d> --description "<…>"` (`_research/_cmds_phase0.py` `cmd_record_gap`) appends `{dimension, description}` to `memo.gaps` and sets that dimension to `Partial` only when it is not already `Clear`. `--dimension` is restricted to the rubric dimensions (`_research/_cli.py`: `choices=list(RUBRIC_DIMENSIONS)`), and `affected_area` is one of them (*"Which UI / module / feature surface"*).
- `memo.gaps` renders in `research-report.md` as `## Open Uncertainties`, one line per gap: `- [NEEDS CLARIFICATION: <dimension> — <description>]` (`_research/_render.py`).
- A post-Phase-1 call has precedent: the hypothesis-suppression gate's recovery reads *"move the mechanism into an open question via `record-gap`"*. `_research/_cmds_render_verify.py` contains no `gaps` token, so research `verify` reads no gap.
- `/devforge:specify` §1.5 reads `<feature_dir>/research-report.md`: *"the file is consumed as plain markdown into Phase 1.5 findings"*. ⚠ Bound: that read is instructed, not gated — it is not among Phase 1 finalize's four mandatory base reads (`constitution.md`, `.devforge/memory.md`, `CLAUDE.md`, `docs/architecture.md`).
- `research-handoff.json` does NOT carry `memo.gaps`: research's `_build_open_questions` reads only `report.open_uncertainties` (`_research/_handoff_build.py`), and nothing writes that field (`_research/_state.py` initializes it to `[]`). Discover diverges — `_discover/_handoff_build.py` `_build_open_questions(memo, report)`: *"Build OpenQuestion list from report.open_uncertainties + memo.gaps"*, with gaps marked `blocking=True`. `specify_helper import-handoff` seeds `state["open_questions"]` from `spec_seeds.open_questions` (`_specify/_cmds_handoff.py`), which render in spec §8.
- `set-recommended-approach --rationale` becomes `plan_seeds.recommended_approach_summary` (`_research/_handoff_build.py`). `/devforge:specify` shows it only as the `find-handoffs` picker summary, cut to 80 chars (`_specify/_cmds_handoff.py`: `if len(summary) > 80: summary = summary[:77] + "..."`); `/devforge:plan` renders it in its upstream plan-seeds block (`plan_helper.py`, `rec_summary`). It is gated twice: check 11 (*"`--rationale` MUST cite at least one of: a `consumer_chain` row's `consumer_qn`, an invariant row's `evidence` string, OR a `dead_siblings` row's `method_qn`"*, when `value_semantics` carries an invariant row) and `verify-hypothesis-suppression`, which *"token-overlaps each unverified hypothesis's `--cause` text against `recommended_approach.rationale`"* and exits 2 on a shared token — so surface names written into the rationale can trip it.

**F4 — Specify already owns the scope decision and the model-answer channel.** `src/commands/specify/main.md` Phase 2 lists category 1 *"**scope_boundaries** — does this affect related area X, related area Y, or only specific area Z?"* and orders rounds *"**scope > breaking changes > data flow > tooling > UX > edge cases**"*. Plan 98 built the delegated path: in interactive mode `set-dp-default-applied --dp-id … --default-applied "<your choice>" --delegated-reply "<the user's reply, verbatim>"`; §8 renders `[default applied]` plus `_(you delegated this choice: "…")_`, and Step 5.1's `**Defaults applied**:` block lists it (`_specify/_render.py`). Auto mode uses `set-dp-default-applied` without the flag. `set-dp-deferral --deferral-kind <OOS|open_question>` handles an explicit punt. Question rounds: *"Up to 5 questions per round."*; *"Only ask questions you CANNOT answer by reading the codebase or Phase 1.5 findings."*; the bundling rule puts ≥4 related questions that are not conditionally dependent into one `AskUserQuestion` call.

**F5 — Specify §6 as recorded and rendered.** `specify_helper record-out-of-scope --content "<NOT-included item>" [--finding-ref …]` (`_specify/_cmds_phase4_setters.py` `cmd_record_out_of_scope`) validates `--content` only as non-empty. The render is `"- NOT included: {0}{1}"`, where `{1}` is `" — <finding_ref>"` when a finding is cited (`_specify/_render.py`). Since plan 98, Step 5.1's approval summary lists every §6 item's content in full, joined with `"; "`. `verify-scope-coherence` (`_specify/_cmds_phase4_verify.py`) is a NON-BLOCKING token-overlap warning between §6 and §5 ACs / §4 impacts. Its tokenizer (`_shared/text_overlap.py` `tokenize_for_overlap`) keeps tokens of ≥4 characters, and its stopwords include `scope`, `shall` and `system` but NOT `excluded` or `model` — so a `[excluded by the model]` prefix can add non-blocking warnings wherever an AC or an affected-area impact says "model" (a recorded bound, D4(d)).

**F6 — §8 is not a landing bucket, and a precedent already routes product questions around that.** `verify-coverage` accepts exactly four buckets — *"every finding landed in AC/Constraint/OOS/Risk"* (`_specify/_cmds_phase4_verify.py`). Specify Step 4.4's emission-matrix paragraph already routes a product question to §8 and its finding to §9: *"surface it to the user as plain prose and record it under §8 Open Questions (Step 4.7), landing its Phase 1.5 finding in §9 Risks (Step 4.8), since §8 is not one of the four buckets `verify-coverage` accepts"*. The §5.2 behavior-preservation paragraph takes the same route.

**F7 — `/devforge:plan`'s view of §6.** `plan_helper render-findings-from-spec` renders each §6 item through `_truncate(text, max_len=80)` (`plan_helper.py` `_render_sec6`: `"- §6 item {0}: {1} [must not contradict]"`), which keeps the FIRST 80 characters: text appended to the end of a §6 item is cut off in the PHASE 1.5 enumeration the orchestrator works from, and a prefix survives. Architect sub-question 6 ends *"the spec's §6 Out of Scope exclusion stands — record no override of it, and have the architect re-scope that decision to the in-scope baseline (sub-question 5's minimal change)."*; plan 98 added the re-ask before it. PHASE 3's approval summary is LLM-authored, with seven conditional lines — `**Defaults applied**:`, `**Departures from convention**:` and five more — each carrying its own omit-the-entire-line rule. *Amended 2026-09-19 (build): sub-question 6 no longer ENDS with plan 98's arm. The arm is byte-intact, but sentences the build added now follow it: the pointer to PHASE 3's `**Unconfirmed exclusions**:` line, and the opposite-direction escalation with its route (build-time decisions 1 and 6). PHASE 3 now has EIGHT conditional lines, with `**Unconfirmed exclusions**:` directly after `**Defaults applied**:`.*

**F8 — The emitted always-on rules.** `src/CLAUDE.md` `### Always` has 16 items. Item 2: *"**Constitution is law** — `constitution.md` rules override everything except user instructions"*. Item 3: *"**Minimal changes** — every change should impact as little code as possible"*. `### Never` item 5 is *"**Never modify outside scope**"*, item 6 *"**Never guess**"*, and item 7 is plan 98's rule: a content answer goes *"through the channel the command names for a model-supplied answer"*, and *"A question the command does not classify decides what the run does."* The multi-sentence precedents are `### Always` item 15 (two sentences) and `### Never` item 7 (four); item 16 is one sentence joined by a semicolon.

**F9 — §6.1 is universal and carries the exclusion reading's strongest text.** `src/constitution.md` `### 6.1 Minimal Changes [universal]` is one paragraph. It opens *"Every code change MUST impact as little code as possible."*, continues *"A bug fix changes the bug. A feature adds the feature. Nothing more."*, and ends with plan 86's F5 sentence, which begins *"A preparatory restructuring the feature's `plan.md` records"*. `§6.1` is in `_UNIVERSAL_SECTIONS` (`_constitute/_schema.py`: `"§6.1", "§6.2", "§6.3", "§6.4"`), so changing its canonical text makes `constitute_helper verify-universal-defaults` report drift for installs constituted earlier and fires the WARN-only update-time drift check — the designed consequence plans 86 and 89 accepted; back-porting is a non-goal. `tests/lib/test_constitute_helper.py` uses §6.1's first sentence only as a fixture `--text`; no test pins the paragraph to the file.

**F10 — Plan 81's F1 and the emission matrix work from the code side.** Plan 81's F1 lives in architect Rule 9 as the *"Rejected-alternative checkability forcing step"*, which fires when two call sites can present *"an identical REACHABLE argument tuple"* to a shared function. A surface on a different request path presents no tuple to that function, so F1 cannot fire for it. The emission matrix lists call sites of the changed code only. Plan 81's Phase-7 anchor is itself about a "hidden surface" the prompt does not name — the same problem class, attacked from the code side; this plan attacks it from the user side.

**F11 — Discover has no existing surface to miss.** `/devforge:discover` scopes a feature that does not exist yet through `users` (*"Who consumes the feature (role, surface)"*), `integration_points` and `non_goals`; no existing surface already shows the feature.

**F12 — Concurrency in this checkout: plan 97 as dated history, plus a standing rule.** `97-WRAPPER-MODE-FRAMEWORK-MENTION-GUARD-PLAN.md` was built in this checkout while this plan was being drafted.
- **Snapshot, kept as history (2026-09-19).** Plan 97's status line read Phase 1 DONE, Phase 2 DONE, Phase 3 IN PROGRESS.
  - Its Phase 1 (`df536ad`, Python under `_configure/`, `_implement/` and `_verify/`) was committed.
  - Its Phase 2 (`b609b21`) was committed: `src/agents/code-reviewer.md`, `src/commands/configure/main.md`, `fix/main.md`, `implement/main.md`, `implement/references/agent-brief.md`, `implement/references/crash-recovery.md`, `verify/main.md`, `verify/references/report-format.md` and `_verify/_cli.py`.
  - Its Phase 3 docs sweep sat uncommitted in `CHANGELOG.md`, the repo `CLAUDE.md`, `DEVELOPMENT-STATUS.md`, `PLAN-STATUS-ARCHIVE.md`, and plans 13 and 25.
- **Later the same day (2026-09-19): plan 97 CLOSED.** It closed by maintainer directive at `0a3d978`, after its Phase 3 docs commit `cc604fa`.
  - Its ledger edits are committed.
  - Its Phase 4 consumer e2e is deferred to post-release.
  - `git status` then showed no modified tracked files.
- **What does not depend on the snapshot.** None of plan 97's `src/` files is one this plan edits. The ledgers are the surface a concurrent plan shares with this one: `CHANGELOG.md`'s `## [Unreleased]`, the repo `CLAUDE.md`, `DEVELOPMENT-STATUS.md` and `PLAN-STATUS-ARCHIVE.md`.
- **Rule.** Another session may be building in this checkout at any time. Before touching any ledger, re-read `git status` and read the ledger live. Commit by explicit path, never `git add -A`.

---

## Decisions to ratify

Nothing below was ratified when drafted (ratified 2026-09-19 — see `## Phase 0 close record`). Each item states the decision, its options where they exist, a recommendation, and the strongest counter-argument, recorded honestly rather than answered away. D1 and D2 carry proposed emitted text. D3–D7 carry the substance of each emitted sentence: that is **proposed text, not final** — the builder may reword it, but every element listed must survive. No emitted sentence may name plan vocabulary ("D3", "plan 99", "Phase 0"); real headings such as `Phase 2.4e` are fine.

### D1 — The always-on rule

**Placement.** Append item **17** to `src/CLAUDE.md` `### Always` — a pure append, with items 1–16 byte-identical. `### Always`, not `### Never`, because the rule is positive; plans 87 and 89 set the append precedent in this list. Item 3 (*"Minimal changes"*) stays as it is: it governs mechanism, and item 17's first sentence says so.

**Proposed text** (amended by D10, 2026-09-19):

> 17. **Scope follows what the user sees** — minimality limits the mechanism, never which user-facing surfaces (anywhere the user sees or triggers a feature) count. A surface shows the feature the user named only on cited user-visible evidence — the same title, label or translation key, route, or tab or mode; shared or different code, requests or data are never evidence or a reason to exclude. Each evidenced surface is covered, excluded in the user's own words, or raised with them, naming what they see there. Deciding it yourself — handed back or never asked — cover it unless you can name what the user would see differently without it; record any exclusion as yours, with that reason, and tell the user. A surface that only shares code is neither covered nor raised. Ask a present user about a surface you suspect but cannot evidence; deciding yourself, leave it an open question, never silently covered or excluded.

- **Superseded 2026-09-19 by D10** — the ratified 115-word text, kept for history: ~~17. **Scope follows what the user sees** — minimality limits the mechanism, never which user-facing surfaces (anywhere the user sees or triggers a feature) count. Each surface showing the feature the user named is covered, excluded in the user's own words, or raised with them, naming what they see there; no code path, request, use case or builder excludes one. A surface that only shares code is neither covered nor raised. When unsure whether a surface shows that feature, ask. Deciding yourself — handed back or never asked — cover it unless you can name what the user would see differently without it; record a surface you leave out as your exclusion, with that reason, and tell the user.~~

*Amended by D10, 2026-09-19: the sentence map and length note below describe the superseded 115-word text. D10 carries the new text's map and count.*

**What each sentence carries** (so a reword cannot drop one):

1. The split between mechanism and scope, which disarms item 3's "as little code as possible" as an exclusion reason, plus the one plain-words definition of "user-facing surface".
2. The three user-facing arms for a surface showing the named feature — covered, excluded in the user's own words, or raised with the user naming what they see there — and the code-path ban.
3. The over-inclusion clause: a surface that shares code but shows a different feature is neither covered nor raised.
4. The ask-when-unsure default, as one sentence: never decide silently whether a surface shows the feature the user named.
5. **The fourth path — the model's own decision**, reached when the user hands the question back or the command decides without asking.
   - The default is to cover.
   - An exclusion needs a user-visible reason.
   - A surface the model leaves out is recorded as the model's own exclusion, with that reason — the §6 marker D4(d) defines — and told to the user.
   - Attribution follows `### Never` item 7.

**Length and pattern note.**
- **Count:** 115 words in five sentences, counting the bold title, hyphenated words as one, and the item number excluded.
- **Against the targets:** over the ~75-word target set at drafting, and over the ~105-word ceiling set at review by ten words. It is the longest `### Always` item and the first five-sentence item in either list.
- **A correction:** the previous revision's note said five sentences, but that text had six — *"Unsure whether a surface shows that feature? Ask."* was two. This text has five because the ask default is now one sentence.
- **Where the growth came from** (all 2026-09-19, after review): the own-words arm, the unambiguous over-inclusion and ask sentences, and the explicit model-exclusion path in sentence 5. Each sentence carries at least one required element above, and every cut tried dropped one. `### Never` item 7 (four sentences) is the nearest precedent; `### Always` item 15 (two sentences) is the nearest in this list. "Minimality limits the mechanism, never which … count" follows the frame's own wording ("minimality limits the mechanism, never which places count").

**RECOMMEND D1 as stated.**

**Counter-argument, recorded:** "the same feature" is a judgment, and nothing mechanical checks it. The rule also raises the question count, against a proportionality principle the pipeline states outright — research's intake gate says *"It is NOT a 20-question inquisition."*

### D2 — Constitution §6.1: append ONE sentence

**New relative to the frame**, which listed "no constitution edit" as a tripwire. `### Always` item 2 makes `constitution.md` outrank every `CLAUDE.md` rule, and §6.1's opening sentence is the strongest text available to the exclusion reading ("covering the second surface impacts more code"); its *"A feature adds the feature. Nothing more."* is the second foothold (F9). An item 17 that narrows §6.1 from inside `CLAUDE.md` loses to it wherever the model weighs the two.

**Options:**

- **(a) Append one sentence** to the end of §6.1's paragraph, after plan 86's F5 sentence. The heading, the `[universal]` tag and every existing byte stay unchanged, and no subsection is added. **RECOMMEND** — plan 86's F5 is the exact precedent: one appended §6.1 sentence, added to remove a contradiction with a lane it introduced. Proposed text:

  > Which user-facing surfaces a change covers is set by what the user sees, never by the code that reaches them: a bug fix changes the bug everywhere the user sees it, a feature changes every surface that shows it, and "as little code as possible" governs how each of those surfaces is changed, never which of them count.

- **(b) No edit.** Accept that the always-on rule loses to §6.1 wherever the model weighs them, and record that precedence risk as a known bound.

**Counter-argument to (a), recorded:** this is a third universal-defaults drift finding for existing consumers, after plans 86 and 89 (F9). A constitution edit also has a bigger blast radius than the evidence supports — ONE observed instance. **If (a) is declined, D1 still ships**, and the precedence risk is recorded as a known bound.

**A second, verified side effect of (a), recorded 2026-09-19.**
- **The mechanism.** `/devforge:specify`'s `check-constitution-compliance` (`_specify/_cmds_phase4_verify.py` `cmd_check_constitution_compliance`) collects every `constitution.md` line matching `CONSTITUTION_RULE_RE` (`MUST` / `SHALL`) as one rule. §6.1 is a single line, and it already matches on its opening *"MUST"*, so the appended sentence joins that rule.
- **The overlap.** That rule's keywords — tokens of ≥4 letters outside `CONSTITUTION_STOPWORDS` — are token-overlapped against every AC, constraint and §6 entry. The sentence brings keywords the line does not carry today, such as "user", "sees", "surfaces" and "shows".
- **The consequence.** On installs whose `constitution.md` carries the new sentence, consumer specs get more NON-BLOCKING warnings from that check; it exits 0 always.

### D3 — Research: four edits and one bound

- **(a) Widen Phase 2.3b's surface-count frame.** The frame statement changes from "other surfaces reach the same shared symbol" to: other surfaces show the same FEATURE, whether they reach the same shared symbol or a different path. Its falsifier names both the inbound `trace_path` of that symbol AND Phase 2.4e's sweep. Its downstream sentence (*"is still mechanically probed downstream by Phase 2.4c's caller enumeration + Step 2b's per-caller surface trace"*) names 2.4e too; otherwise it goes false. ⚠ Keep "mechanically" attached to 2.4c and Step 2b only, which checks 8, 9 and 19 gate. Phase 2.4e is a search step with no check, so calling it "mechanically probed" would be the next false sentence.
- **(b) New `### Phase 2.4e — Feature-surface sweep (MANDATORY — mode-independent)`**, placed after Phase 2.4d and before Phase 2.5. The letter suffix keeps every existing phase number and its citations (plan 81 F6's precedent). Substance:
  - **Starting point:** the feature the user named — the `symptom`, `desired` and `affected_area` answers, plus the verbatim prompt.
  - **Probe 1, the words the user sees:** a label, heading or message, or its translation key — `search_code` project-wide.
  - **Probe 2, the data the feature shows:** the entity field or payload value — its readers, through `search_graph` / `trace_path(mode=data_flow)`.
  - **Probe 3:** the view, route and component names in the `affected_area` answer.
  - **Trace each hit** up to its user-facing entry point under Step 2b's rules: the 8-hop bound, and a surface label derived from construction sites, never from resemblance.
  - **Record each distinct surface** at Phase 2.6: `record-finding --surface "<surface>" --relevance "shows the named feature — <reached through the changed code | a different path: …>"`, with the usual `--file-line` grounding and `--rests-on-literal` answer. *(Amended by D10, 2026-09-19: the `--relevance` value also cites the surface's user-visible identity evidence.)*
  - **The honesty bound, stated in the emitted text:** this is a SEARCH step, not a gate. Completeness is model judgment, and there is no check number and no validator. (The plan-side reason, which stays out of the emitted text: plan 75's D1 spine and tripwire.)
- **(c) Step 2b's `out` justification rule.**
  - An `out` justification names what the user sees differently. Examples: "shows a different feature: <what the user sees there>", "the user excluded it: '<their words>'", "no user-facing surface reaches it".
  - A caller whose surface shows the feature the user named is `in` unless the user excluded that surface in their own words. *(Amended by D10, 2026-09-19: an `in` justification that rests on the surface showing the feature cites its user-visible identity evidence.)*
  - A code path, request, use case or builder is never the justification.
  - **"Own words" is defined at this site.** The user excluded a surface only when the user's own words — the prompt, a rubric answer, a decision-point answer, or a correction — name that surface or a class that plainly contains it, or when the user explicitly picked an offered option that named it.
  - **A `scope` pick of `"one place"` names no surface.** `set-scope` requires `--evidence` that *"proves the symptom is localized to that single site"*. That is a claim about where the symptom sits, answered before research surfaced any other surface, so it excludes nothing research later finds. This clause lands here at Step 2b, beside the definition it sharpens; 2.4e was the alternative placement considered.
- **(d) New Phase 3 step `3b` — Uncovered feature surfaces.** A letter-suffixed setter step directly after step 3 (Recommended approach), because it depends on the approach. Setters 4–8 keep their numbers, and check 13's *"(see Phase 3 step 3)"* citation stays true.
  - **What it records:** each surface from 2.4e, and each `in` caller's surface, that the recommended approach leaves unchanged and that the user did not exclude in their own words.
  - **How:** `record-gap --dimension affected_area --description "<surface> also shows <feature> (<what the user sees there>); the recommended approach leaves it unchanged — cover it or leave it out?"`. It renders under the report's `## Open Uncertainties`, which specify reads (F3). *(Amended by D10, 2026-09-19: the description also cites the surface's user-visible identity evidence, or states that there is none.)*
  - **Not in `--rationale`** — F3 gives three reasons.
- **Bound:** research records; it does not decide scope. Specify is the decision seat (D4).

**RECOMMEND (a) + (b) + (c) + (d).**

**Counter-argument, recorded:** over-inclusion pressure and cost. Phase 2.4e adds codebase-graph calls to an already heavy command, on every run.

### D4 — Specify: the decision seat

- **(a) Phase 2 `scope_boundaries`.** Take each user-facing surface that the Phase 1.5 findings name as showing the feature the user named, the research report's `## Open Uncertainties` included. When the user has not settled its inclusion in their own words, it is its own `scope_boundaries` decision point, with the two valid implementations `cover <surface>` / `leave <surface> out`. *(Amended by D10, 2026-09-19: the decision point's `--description` cites the surface's user-visible identity evidence, or states that there is none.)*
  - At the *"Only ask questions you CANNOT answer by reading the codebase or Phase 1.5 findings."* line: whether such a surface is in scope is a product question, never answerable from the codebase.
  - Several such decision points bundle into one `AskUserQuestion` call under the existing bundling rule.
  - The "own words" definition from D3(c) is restated here, because commands load independently (plan 98's OQ-7 precedent).
- **(b) The value the model supplies — on the auto path and on the delegated path alike.** The value is `cover <surface>`, unless the model can name what the user would see differently because the surface is left out. A code path, request, use case or builder is never that reason. It is recorded through the existing channels — auto: `set-dp-default-applied`; delegated: `set-dp-default-applied --delegated-reply` — so Step 5.1's `**Defaults applied**:` block already lists it. **No new channel.** *(Note added 2026-09-20 — plan 100's D1, and it governs this bullet's sub-bullets too: `/devforge:specify` no longer branches on Claude Code's auto mode, every decision point is asked, and `set-dp-default-applied` requires `--delegated-reply` on every call — so the one surviving channel is the delegated one and "the auto path" names a route the command no longer has.)*
  - **The value rule binds the deferral path too** (added 2026-09-19, after review). This applies to a `scope_boundaries` decision point about a surface showing the named feature.
    - `set-dp-deferral --deferral-kind OOS` is taken only when the user's own words punt it to §6.
    - The model's answer, on the auto path or the delegated path, goes through `set-dp-default-applied` under the value rule above.
    - This narrows specify's deferral-path text, *"When the user (or auto-mode rationale) explicitly punts the decision to §6 Out of Scope or §8 Open Questions"*: its *"(or auto-mode rationale) explicitly punts"* arm no longer reaches such a decision point.
  - *Amended by D10, 2026-09-19:*
    - The value rule above now applies only to a surface with cited identity evidence.
    - With no evidence, the model's route in BOTH modes — interactive-delegated included — is `set-dp-deferral --deferral-kind open_question`, neither covered nor excluded.
    - `--deferral-kind OOS` stays user-only.
  - **Why the narrowing is needed.** `deferred_OOS` renders in neither §6 nor §8. `_specify/_render.py` renders `deferred_open_question` in §8 and has no branch for `deferred_OOS`, which appears only as a count in the `/devforge:plan` handoff block. A deferral by the model would therefore be an exclusion no reader of the spec sees.
- **(c) "Cover" means both** a §4 affected-area row naming the surface AND at least one §5 AC whose statement names it. An AC naming only the first surface lets `/devforge:verify` pass while the second is untouched.
- **(d) The §6 marker, at Step 4.5.** Every §6 entry the user did not state in their own words takes the form `[excluded by the model] <item> (user sees: <what the user sees because of it, or "no difference">)`.
  - **A prefix, not a suffix:** `/devforge:plan` keeps the first 80 characters of a §6 item (F7), and §6 already renders its own ` — <finding_ref>` suffix (F5).
  - **The reason sits in parentheses, not after an em dash** (separator changed 2026-09-19, after review). A parenthesized `(user sees: …)` cannot collide with that ` — <finding_ref>` suffix, so a cited entry renders unambiguously as `- NOT included: [excluded by the model] <item> (user sees: …) — <finding_ref>`. The em-dash form is recorded as the alternative under OQ-1.
  - **The bracketed form follows house convention:** `[default applied]`, `[exceeded cap]` and `[no DP in category X]` in specify §8, and `[NEEDS CLARIFICATION: …]` in the research report. *Amended 2026-09-19 (build): `[exceeded cap]` is not a render — no code emits it. A decision point that reaches the follow-up cap renders in §8 as `[deferred to open question]`, with the reason `exceeded follow-up cap` (`DP_TURN_CAP_REASON` in `_specify/_schema.py`). The orchestrator carried the false literal over from specify's own text, which the build corrected (build-time decision 5). The house-convention argument still holds on the forms that do render, `[deferred to open question]` among them.*
  - **Option (i), broad — every model-authored §6 entry. RECOMMEND.** The incident's exclusion was framed in code terms ("a different request path"). A marker scoped to "exclusions of a surface" lets a code-framed exclusion escape classification. The broad rule forces the model to write the user-visible consequence of every exclusion it makes, which turns the incident's reason into a visibly false statement.
  - **Option (ii), narrow — only §6 entries that exclude a surface showing the feature.** Less noise, but it relies on the same judgment the rule is trying to discipline.
  - **Counter-argument to (i), recorded:** noise.
    - In auto mode every §6 entry carries the marker, and Step 5.1 gets longer. *(Note added 2026-09-20 — plan 100's D1: specify has no auto branch left, so the marker rule fires on every run the user did not state the exclusion in their own words. The noise cost stands; what changed is that no mode triggers it.)*
    - `verify-scope-coherence` can add non-blocking warnings on the prefix's tokens `excluded` and `model` (F5).
    - The fixed `(user sees:` text adds two more non-stopword tokens, `user` and `sees`. "user" is common in EARS acceptance criteria, so every marked §6 entry can overlap with every AC or affected-area impact that mentions the user.
- **(e) Unresolved — an explicit user punt** (`set-dp-deferral --deferral-kind open_question`). The surface goes to §8, and its Phase 1.5 finding lands in §9 through `record-risk --finding-ref` — the Step 4.4 precedent (F6). *(Amended by D10, 2026-09-19: the same route is also the model's own route for a suspected surface with no identity evidence.)*
- **(f) Named strengthening arm, NOT built.** A helper flag (`record-out-of-scope --origin user|model --reason …`) that renders the marker mechanically. Built only if Phase 3 observes the prefix skipped.

**RECOMMEND (a) + (b) + (c) + (d)(i) + (e); (f) recorded, not built.**

### D5 — Plan: an exclusion kept by a non-decision stays visible

- **Sub-question 6 gains one clause, for EVERY escalation that ended without a decision** — whether or not its §6 entry carries `[excluded by the model]`. The existing non-decision arm is unchanged: the exclusion stands, no override is written, and the architect re-scopes to the minimal baseline (plan 98's arm). The exclusion is also added to a new conditional PHASE 3 summary line. *(Changed 2026-09-19: the first revision fired only on marked entries.)*
- **The line**, proposed text, placed directly after `**Defaults applied**:` because both list what the user did not decide:
  `**Unconfirmed exclusions**: [include this line ONLY if ≥1 sub-question-6 escalation ended without a decision: list each §6 entry it concerned by its leading bracketed marker, when the entry has one, and its item text only — nothing that follows the item — and say the user did not decide it here; omit the entire line when none]`
- **Never quote the entry's `(user sees: …)` clause.** The line names an entry by its prefix, when present, and its item text, and stops there. Its emitted instruction does this without naming the clause or the marker literal, so `plan/main.md` carries neither `(user sees:` nor `[excluded by the model]`. That keeps Phase 1d's invariant: `grep -rn "(user sees:" src/` returns `specify/main.md` only.
- **`/devforge:plan` never edits `spec.md`.** The line makes the state visible; it lifts nothing. *Amended 2026-09-19 (build): the first sentence is too strong, and it was not carried into `src/`. PHASE 0b's `check-status-and-flip` rewrites the spec's `**Status**:` line, or inserts one. `specify_helper resolve-open-question`, which the command runs when a planning decision settles a §8 question, records a resolution in specify-state, and the spec's render strikes the resolved entry through. What shipped makes the narrower true claim: the command "adds no affected area and no acceptance criterion to `spec.md`" (build-time decision 7). The second sentence stands.*
- **Re-read the live sub-question-6 sentence before editing** — plan 98 re-worded it (F7).
- **Bound:** the line fires only on an escalation that ended without a decision. An exclusion — marked or not — that no Key Design Decision reaches is not re-listed at PHASE 3; the spec's Step 5.1 listed it.
- **Consequence: D5 no longer depends on D4.** Its trigger is an escalation's outcome, not the marker, and its emitted text names no literal, so it can ship alone.
- **When it ships — options (the maintainer's call):**
  - **(a)** with the rest of this plan, after Phase 0;
  - **(b)** alone, as an amendment ahead of the rest of this plan — for example with plan 98's release. The entrenchment it closes is a side effect of plan 98's non-decision arm (Origin & evidence).
    - Option (b) needs its own ratification record for D5 alone: one dated, D5-only entry written in `## Phase 0 close record`. After that entry, D5 alone may build.
    - Every other item still waits for the full Phase 0 close, which later records D5 as "ratified early (<date>)".
  - **RECOMMEND:** D5 ships no later than plan 98's release.

**RECOMMEND D5 as stated.**

**Counter-argument, recorded:** one more summary line, against the review-fatigue concern plan 96 grew from.

### D6 — Architect Rule 9: one symmetric sentence

- **The sentence**, at the `**Out-of-scope-respect forcing step:**`: a user-facing surface that shows the feature the spec names, but that the spec neither covers (§4 / §5) nor excludes (§6), is not dropped as outside the minimal change — escalate it to the user per Rule 6.
- **Proposed placement:** after that step's escalation sentence, before *"This is distinct from the state-cardinality step below"*.
- **Unchanged:** Rule 9's heading, its number and its six forcing steps.
- **Why:** Rule 9's local *"Decide what the task requires, not what might be nice to design. No speculative architecture."* is the text the architect weighs. Today its Out-of-scope-respect step covers only the §6 direction. Plan 86's F5 added a Rule 9 sentence for the same kind of local contradiction.

**RECOMMEND D6 as stated.**

**Counter-argument, recorded:** agent-prompt growth. The always-on rule may already reach the architect — plan 97's OQ-1 resolution records that custom agents load the project `CLAUDE.md`.

### D7 — Grill: devils-advocate Rule 6, one sentence

- **The sentence:** an entry marked `[excluded by the model]` is not an exclusion the spec made deliberately on the user's word. When it leaves out a surface that shows the feature the spec names, surface it as an upstream signal — the channel Rule 6 already names (*"surface it as an upstream signal, do not manufacture an attack out of an exclusion the spec made deliberately"*).
- **A second net at a mandatory stage.** Since plan 85 the grill runs before every `/devforge:breakdown`. It is still LLM judgment, and the verdict never binds.

**RECOMMEND D7 as stated.**

**Counter-argument, recorded:** it widens the attack surface, with possible false positives on legitimate model exclusions — which the refuter stage exists to cut.

### D8 — Discover and downstream: no per-site edit

- **Discover is greenfield:** no existing surface already shows the feature (F11).
- **`/devforge:implement` / `/devforge:fix` / `/devforge:review` / `/devforge:verify`:** discovering a new surface there rides the always-on rule alone. Implement's Stage A `conflict` items are the existing stop point.
- **Recorded as a bound, with a named trigger:** an observed exclusion at one of those stages.

**RECOMMEND D8 as stated.**

### D9 — Tripwires and non-deltas

- **Instruction-only v1.** Zero Python. Two named strengthening arms, both NOT built: D4(f)'s helper flag and OQ-3's handoff wiring.
- **No new mechanism.** Zero gates, zero validators, zero `verify-*` numbers and zero new research check numbers — plan 75's tripwire, both halves.
- **The constitution** changes by ONE appended sentence, and only if D2(a) is ratified.
- **No `disable-model-invocation` change:** 17 model-invocable / 4 human-typed-only, untouched.
- **Implicit approval by invocation untouched** (plan 98's D5).
- **No back-porting;** the frozen benchmark install is never touched.
- **Every emitted edit is general** — nothing names a client, component or UI element.

**RECOMMEND D9 as stated.**

### D10 — Feature identity by user-visible evidence (post-ratification amendment, 2026-09-19)

**Ratified 2026-09-19 by an explicit maintainer pick after the Phase 0 close** — see `## Phase 0 close record`.

**Origin.** The benchmark operator's peer session proposed two parts (Origin & evidence). Both aim at the weakness D1's counter-argument names: "the same feature" is a judgment.
- **The peer's context.** Under a blind protocol the operator answers every content question with a delegation and approves artifacts as they are.
- **The consequence.** Every decision point is then model-answered and nobody reviews Step 5.1, so the over-inclusion risk has no human backstop there.

**P1 — Identity needs evidence.**
- **The rule.** A surface counts as showing "the feature the user named" only when at least one piece of USER-VISIBLE identity evidence is cited and recorded beside it:
  - the same title or heading;
  - the same label, translation key or menu item;
  - the same route;
  - or the same tab or mode constant that controls what the user sees.
- **The symmetric ban.** Shared code — a helper, use case, builder or request — and a shared data source are never identity evidence, just as they are never a reason to exclude.
- **Where the evidence is recorded:**
  - research Phase 2.4e's `record-finding --relevance`;
  - research Phase 3 step 3b's `record-gap` description;
  - research Step 2b's `in` justification, when it rests on the surface showing the feature;
  - specify's `scope_boundaries` decision-point description (`record-decision-point --description`).
- **The full list above goes into the command sites** (research, specify). Item 17 carries a shorter form — title, label or translation key, route, tab or mode — to hold its length.

**P2 — The model's default depends on the evidence** (delegated or auto path):
- **Identity evidence cited** → cover, unless the model names what the user would see differently. That is the marked exclusion (D4(d)), unchanged.
- **No identity evidence, but the model suspects the same feature** → neither covered nor excluded.
  - The model defers it to an open question through the EXISTING `set-dp-deferral --dp-id … --deferral-kind open_question --reason "<deferred by the model — why it may be the same feature: …>"`.
  - It renders in §8 as `[deferred to open question]`, with the reason.
  - Its Phase 1.5 finding lands in §9 through `record-risk --finding-ref` — the Step 4.4 route (F6).
  - No new marker.
- **Interactive mode with a live user, no evidence** → ask, as before.
- *(Note added 2026-09-20 — plan 100's D1 and D2: none of the three commands branches on Claude Code's auto mode any more, so specify asks every `scope_boundaries` decision point and "delegated or auto path" above now names the delegated path alone. The "live user" arm is the ordinary path, and the model supplies a value only on a reply that hands the question back.)*

**Rejected variant, recorded.**
- **The peer's form** put the weak case into §6 and the PHASE 3 line, with a new `[unresolved by the model]` marker.
- **Why declined:** §6 holds exclusions and §8 holds unresolved questions. `/devforge:plan` PHASE 1.5 already forces every §8 line to `[RESOLUTION: <decision>]` or `[RESOLUTION: carry-forward to /devforge:breakdown]`.
- **Its cost, recorded:** a §8 deferral is not listed in specify's Step 5.1 summary — only defaults and §6 are. In the weak case, visibility at approval is therefore lower than under the peer's form. *(Note added 2026-09-20 — plan 100's D12 RETIRES this cost: Step 5.1 now renders a conditional `**Deferred to open questions**:` bullet listing every `deferred_open_question` decision point with its reason, so a model deferral is visible at approval. Risks are still not listed there.)*

**Counter-argument, recorded:** the evidence list can be gamed — a label shared by two different features — and it can miss a real identity with no shared visible marker. The evidence is model-cited and nothing checks it. D10 makes the judgment inspectable, not mechanical.

**Amends.** Each amended site carries a dated pointer; ratified text is not rewritten, except D1's proposed-text block.
- **D1** — item 17 gains the identity clause and the evidence-dependent default. The new text is in D1's block, with the superseded text kept beside it; the map and count are below.
- **D3(b), (c), (d)** — identity evidence is cited at 2.4e's `--relevance`, at Step 2b's `in` justification and in step 3b's gap description.
- **D4(a), (b), (e)** — the decision-point description cites the evidence.
  - (b)'s deferral binding keeps `--deferral-kind OOS` user-only.
  - The `open_question` deferral becomes the model's route for the no-evidence case in BOTH modes, interactive-delegated included. The existing specify text *"When the user (or auto-mode rationale) explicitly punts"* did not cover that case. *(Note added 2026-09-20 — plan 100's D6: that specify sentence no longer carries "(or auto-mode rationale)" — the deferral path is written delegated-only, so "BOTH modes" now reads as the single path the command has.)*
- **Phase 1a/1b/1c** element lists and Verify, and **Phase 3**'s anchors.
- **Unchanged:** D9 holds — zero Python (every verb D10 names already exists), zero gates, zero validators.

**The new item 17 — what each sentence carries:**
1. The mechanism-versus-scope split and the one plain-words definition of "user-facing surface".
2. The identity-evidence definition, and the symmetric ban: shared or different code, requests or data are never evidence and never a reason to exclude.
3. The three user-facing arms for an evidenced surface — covered, excluded in the user's own words, or raised naming what the user sees there.
4. The model's own decision on an evidenced surface (handed back or never asked): cover unless it can name a user-visible difference; any exclusion is recorded as the model's own, with that reason (the §6 marker), and told to the user.
5. The over-inclusion clause: a surface that only shares code is neither covered nor raised.
6. The no-evidence split: ask a present user; deciding yourself, leave it an open question (the §8 deferral), never silently covered or excluded.

**Length note.**
- **Count:** 152 words in six sentences, using D1's rule (bold title counted, hyphenated words as one, item number excluded). By sentence: 23 / 40 / 20 / 34 / 11 / 24.
- **Against the target:** over the ≤ ~135 target set for this amendment by 17 words. It is the longest item in either list and the first six-sentence one.
- **The growth over the 115-word text** is the evidence definition and the no-evidence split.
- **Held near 150 by three compressions:**
  - the emitted evidence list is the short form (see P1);
  - "a code path, request, use case or builder" is folded into "shared or different code, requests or data";
  - "record a surface you leave out as your exclusion" became "record any exclusion as yours".

### OQ-1 — The marker literal and its separator

- **The literal.** `[excluded by the model]` (**RECOMMEND** — bracketed like `[default applied]`, in plan 98's "the model" vocabulary) vs `[model exclusion]` vs `[not the user's exclusion]`. Whatever is chosen appears byte-identical in `specify/main.md` and `devils-advocate.md`; `plan/main.md` names no literal (D5). *Amended 2026-09-19 (build): it also appears byte-identical in the grill's `references/design-attack-checklist.md` — the deliberate additional site of build-time decision 2 — which, like `devils-advocate.md`, keys on the literal prefix alone.*
- **The separator for the user-visible reason.**
  - **RECOMMEND the parenthesized form:** `[excluded by the model] <item> (user sees: <what the user sees because of it, or "no difference">)`. It cannot collide with §6's own ` — <finding_ref>` suffix (F5).
  - **Recorded alternative — the em-dash form:** `[excluded by the model] <item> — <what the user sees because of it, or that the user sees no difference>`. It carries no fixed `user` / `sees` tokens into `verify-scope-coherence` (D4(d)'s counter-argument). On a cited entry, though, it renders two em-dash segments, and a reader cannot tell the reason from the finding reference.
  - **Where it lives.** The separator is stated only in `specify/main.md`. `devils-advocate.md` keys on the literal prefix alone, and `plan/main.md` names neither the literal nor the separator (D5).

### OQ-2 — Where the sweep lives

2.4e as its own sub-phase (**RECOMMEND** — 2.4c is defined as helper-API enumeration, and its gates are checks 8 / 8b / 9 / 19) vs a Step 2c inside 2.4c.

### OQ-3 — Carry research `memo.gaps` into the handoff

Carry `memo.gaps` into `research-handoff.json`'s `spec_seeds.open_questions`, as discover already does (F3); that would land them in spec §8 mechanically. **NOT in v1 (RECOMMEND).** The loss in the incident was at the decision, not the carrier. The wiring would also start carrying Phase-1 accepted-gap entries into every spec — a behavior change beyond this plan. Recorded as a named strengthening arm; **trigger:** an observed run where the report's gap never reached specify's findings.

### OQ-4 — Question budget

One decision point per uncovered surface, bundled per call (**RECOMMEND**) vs one decision point listing all surfaces — fewer questions, but the user cannot cover one surface and exclude another in one pick.

### OQ-5 — Where Phase 3 runs

A testForge20 fixture with a feature visible on two surfaces through different request paths (**RECOMMEND** — the frozen install cannot be used).

---

## Phase 0 close record

**CLOSED 2026-09-19 by a single blanket maintainer directive**, given in Ukrainian; English paraphrase: *"I ratify the whole plan"*.
- **An explicit pick, not a delegation.** The directive answered the orchestrator's offer of two paths: ratify everything now, or ratify D5 alone early through option (b). The maintainer picked the whole-plan path.
- **Every item is ratified AS RECOMMENDED. No per-item deliberation was supplied.** This record does not imply that any counter-argument was answered — each stays recorded at its decision (the plans 91 / 92 / 94–98 precedent).
- **The orchestrator stated this reading of the directive to the maintainer before building.**

- **D1** — RATIFIED as proposed: `src/CLAUDE.md` `### Always` item 17, the 115-word text.
- **D2** — RATIFIED as recommended: (a), one sentence appended to `src/constitution.md` §6.1.
- **D3** — RATIFIED as recommended: (a) + (b) + (c) + (d).
- **D4** — RATIFIED as recommended: (a) + (b) + (c) + (d)(i) + (e). (f) is recorded and NOT built.
- **D5** — RATIFIED as stated, option (a): D5 ships with the rest of this plan.
  - The full close makes option (b) moot, and no D5-only early entry exists.
  - Its recommendation that D5 ship "no later than plan 98's release" is met only if this plan lands before that release. Nothing in this record guarantees that it will.
- **D6** — RATIFIED as recommended.
- **D7** — RATIFIED as recommended.
- **D8** — RATIFIED as recommended.
- **D9** — RATIFIED as recommended.
- **OQ-1** — `[excluded by the model]`, with the `(user sees: …)` separator.
- **OQ-2** — 2.4e as its own sub-phase.
- **OQ-3** — not in v1; recorded as a named strengthening arm.
- **OQ-4** — one decision point per uncovered surface, bundled per call.
- **OQ-5** — a testForge20 fixture.

**Files in scope, per Phase 0's Verify:**
- 1a touches `src/CLAUDE.md` AND `src/constitution.md` (D2(a)).
- 1d touches `src/commands/plan/main.md`, `src/agents/architect.md` and `src/agents/devils-advocate.md` (D5, D6, D7).

**Post-ratification amendment — 2026-09-19.**
- **D10** — RATIFIED 2026-09-19 by an explicit maintainer pick after the close, amending D1, D3 and D4.
  - The pick was made through `AskUserQuestion`: *"both, P2 through §8 (recommended)"*. It is a pick, not a delegation.
  - **Per-item deliberation:** the maintainer chose between four offered options.
  - No file-scope change: D10 edits files 1a, 1b and 1c already touch.

---

## Phases

### Phase 0 — Ratification

Every D-item (D1–D9) and every OQ (OQ-1–OQ-5) gets an outcome in `## Phase 0 close record`: ratified, amended or declined. The record states whether per-item deliberation was supplied. Each counter-argument stays at its decision. **Nothing builds before the close — with one exception, D5's option (b).**
- **The exception.** A dated, D5-only ratification entry in `## Phase 0 close record` lets D5 alone build and ship ahead of the rest.
- **Everything else waits.** Every other item still waits for the full close before its own build starts.
- **The full close** later records D5 as "ratified early (<date>)".

#### Verify

- `## Phase 0 close record` names **each** of D1–D9 and OQ-1–OQ-5 with its outcome. No item is silently omitted.
- **If D5 was ratified early,** the record carries its dated D5-only entry, and the full close lists D5 as "ratified early (<date>)".
- **No build starts before the full close** except D5's.
- The record states whether per-item deliberation was supplied.
- Each decision above still carries its counter-argument. **A ratified decision with its counter-argument deleted cannot be re-opened honestly.**
- The record says which Phase 1 files the outcomes put in scope: D2's outcome decides whether 1a touches `src/constitution.md`, and D6's and D7's outcomes decide 1d's agent edits.

### Phase 1 — Instructions

**Route: instruction-author → instruction-reviewer, in small dispatches, committing by explicit path.** Instruction-only: no `.py` file changes in this phase or any other.

- **1a — `src/CLAUDE.md` (D1) + `src/constitution.md` §6.1 (D2, if ratified).** *(Amended by D10, 2026-09-19: item 17 carries D10's 152-word text. The superseded 115-word text is present in `src/CLAUDE.md` as of this amendment, so 1a replaces item 17 in place.)*
- **1b — `src/commands/research/main.md` (D3).** It covers the 2.3b widening, the new Phase 2.4e, the Step 2b sentence with the own-words definition and the `"one place"` clause, and Phase 3 step 3b. Phase 2.6 records 2.4e's findings, so its two sentences that enumerate where findings come from name 2.4e as well — the house cross-check rule, not a new decision. *Amended by D10, 2026-09-19:* 1b also carries P1's identity-evidence definition (the full list) and its recording at 2.4e's `--relevance`, at Step 2b's `in` justification and in step 3b's gap description.
- **1c — `src/commands/specify/main.md` (D4).** It covers the `scope_boundaries` sentence with the own-words definition, the product-question sentence at the *"Only ask questions you CANNOT answer…"* line, the model-value rule on both the auto and delegated paths, the deferral-path binding (a `scope_boundaries` decision point about a surface showing the named feature takes `set-dp-deferral --deferral-kind OOS` only on the user's own words), the cover-means-§4-and-§5 rule, the §6 marker rule at Step 4.5, and the unresolved route. *Amended by D10, 2026-09-19:* 1c also carries P1's identity-evidence definition (the full list), its recording in the `scope_boundaries` decision-point description, and P2's evidence-dependent default.
  - **Evidence cited:** the value rule.
  - **No evidence** (auto or delegated): `set-dp-deferral --deferral-kind open_question --reason "deferred by the model — …"`, with the finding landed in §9 through `record-risk --finding-ref`.
  - **No evidence, with a live user:** ask.
- **1d — `src/commands/plan/main.md` (D5) + `src/agents/architect.md` (D6) + `src/agents/devils-advocate.md` (D7).** If the maintainer takes D5's option (b), D5's `plan/main.md` edit leaves this sub-phase and ships alone, ahead of the rest.
- **Order:** 1a–1d are independent except that D7's devils-advocate sentence quotes the marker 1c defines — build 1c before that edit. D5 names no marker and D6 quotes none, so neither needs 1c.

#### Verify

- **1a:** `### Always` items 1–16 are byte-identical and item 17 is appended. *(Amended by D10, 2026-09-19: item 17 reads exactly D10's text — no sentence of the superseded 115-word text survives.)* If D2 is ratified, §6.1's existing text is byte-identical with one sentence appended, and its heading still reads `### 6.1 Minimal Changes [universal]`. `tests/lib/test_constitute_helper.py` is green. The live-spec tests are green: `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py`, `tests/scripts/test_claude_emitter.py`.
- **1b:** the `### Phase 2.4e — Feature-surface sweep` heading exists, and its body states the search-step-not-a-gate bound.
  - 2.3b names 2.4e in both the frame and the downstream sentence, and "mechanically" stays attached to 2.4c and Step 2b only.
  - The Step 2b sentence, the own-words definition and the `"one place"` clause are present.
  - The Phase 3 step 3b calls `record-gap --dimension affected_area`.
  - Phase 2.6's finding-source sentences name 2.4e.
  - *(Added by D10, 2026-09-19.)* P1's identity-evidence definition is present with its full list and its symmetric ban (shared code and a shared data source are never evidence). 2.4e's `--relevance`, Step 2b's `in` justification and step 3b's gap description each instruct citing that evidence.
  - `grep -ni "check 2[1-9]"` over `research/main.md` returns nothing, and the hypothesis-suppression gate still says it is *"not one of its 20 checks"*.
- **1c:** every element listed for 1c is present — the deferral-path binding included: the per-decision-point protocol's deferral path states that a `scope_boundaries` decision point about a surface showing the named feature takes `set-dp-deferral --deferral-kind OOS` only on the user's own words — and Step 4.5 states the full marker format `[excluded by the model] <item> (user sees: <what the user sees because of it, or "no difference">)`, or OQ-1's ratified literal and separator.
  - *(Added by D10, 2026-09-19.)* P1's definition and full list are present, and the `scope_boundaries` decision-point description cites the evidence.
  - The no-evidence route is `set-dp-deferral --deferral-kind open_question` in both the auto and the interactive-delegated path, with its finding landed in §9. `--deferral-kind OOS` stays user-only.
  - No new marker appears: `grep -rn "unresolved by the model" src/` returns nothing.
- **1d:** the sub-question-6 text plan 98 shipped is intact except for the added clause.
  - The PHASE 3 `**Unconfirmed exclusions**:` line is conditional, and its instruction omits the entire line when none.
  - Its trigger is any sub-question-6 escalation that ended without a decision, not the marker.
  - Its instruction lists an entry's leading marker, when present, and its item text only.
  - `plan/main.md` contains neither `[excluded by the model]` nor `(user sees:`.
  - Rule 9's heading, number and six forcing steps are unchanged.
  - The marker literal is byte-identical across specify and devils-advocate: `grep -rn "\[excluded by the model\]" src/` returns exactly those two files, plus any deliberate additional site the build record names.
  - Specify's Step 4.5 is the only site that states the `(user sees: …)` separator. Devils-advocate keys on the literal prefix alone, and plan names neither: `grep -rn "(user sees:" src/` returns `specify/main.md` only.
- **Every sub-phase:**
  - No emitted text names plan vocabulary ("D1", "plan 99", "Phase 0"); a real heading such as `Phase 2.4e` is fine.
  - `git diff --stat` shows no `.py` file.
  - instruction-reviewer reports SHIP-READY, or every finding it raised is fixed.

#### Phase 1 build record — 2026-09-19

**Route as specified: instruction-author → instruction-reviewer.** The four sub-phases 1a–1d were dispatched in parallel, plus the D10 deltas, which land in files 1a, 1b and 1c already touch. **Commit `6a786b3`, eight files.** ⚠ This block records a BUILD, not a consumer observation. Nothing below was run on a real install.

**instruction-reviewer outcome: SHIP-READY, with 2 findings (1 medium, 1 low), both fixed.** One of them became build-time decision 6 below. Before the build, the draft of this plan had two instruction-reviewer passes — 4 findings, then 2, all fixed.

**What landed:**

1. **1a — `src/CLAUDE.md` (D1, as amended by D10).** `### Always` item 17, **Scope follows what the user sees**: D10's text, 152 words in six sentences, the longest item in either list. Items 1–16 are byte-identical.
2. **1a — `src/constitution.md` §6.1 (D2(a)).** One sentence is appended after plan 86's F5 sentence: which user-facing surfaces a change covers is set by what the user sees, never by the code that reaches them, and "as little code as possible" governs how each surface is changed, never which of them count. The heading still reads `### 6.1 Minimal Changes [universal]`.
   - ⚠ **Designed consumer drift, not a regression.** `constitute_helper verify-universal-defaults` and the WARN-only update-time drift check report §6.1 drift for installs constituted earlier — the third such finding, after plans 86 and 89. Back-porting is a non-goal.
   - `/devforge:specify`'s `check-constitution-compliance` treats §6.1's single MUST line as one rule, so the new words add NON-BLOCKING warnings (D2's second side effect).
3. **1b — `src/commands/research/main.md` (D3, as amended by D10).**
   - **Phase 2.3b's surface-count frame is widened:** other surfaces show the same FEATURE, through the same shared symbol or a different path. The falsifier names the inbound trace AND the sweep. "Mechanically" stays attached to Phase 2.4c and Step 2b only.
   - **New `### Phase 2.4e — Feature-surface sweep (MANDATORY — mode-independent)`**, carrying:
     - three probes — the words the user sees, the data the feature shows, and the names in the `affected_area` answer;
     - the identity-evidence definition;
     - an over-inclusion boundary (evidenced / suspected / other);
     - findings recorded at Phase 2.6;
     - the honesty bound: a SEARCH step, not a gate. Completeness is judgment, and there is no check and no validator.
   - **Step 2b's `**What a scope justification rests on.**` paragraph:**
     - an `out` justification names what the user sees differently, never a code path, request, use case or builder;
     - the own-words definition;
     - a `"one place"` scope pick excludes nothing research finds later;
     - a suspected caller is `in`, which is not a coverage decision (build-time decision 3).
   - Phase 2.6 and Phase 0.5 Step 2 name 2.4e.
   - **Phase 3 step `3b`** records each uncovered surface through `record-gap --dimension affected_area`, never in `--rationale`. The gap renders under the report's `## Open Uncertainties`, which specify reads.
4. **1c — `src/commands/specify/main.md` (D4, as amended by D10).**
   - **A `scope_boundaries` decision point per user-facing surface.** Its description cites identity evidence, or states that there is none. The scope of such a surface is a product question, always asked in interactive mode.
   - **The value the model supplies, on the auto path or the delegated path:**
     - evidenced → `cover <surface>` through `set-dp-default-applied`, unless the model names a user-visible difference;
     - unevidenced → `set-dp-deferral --deferral-kind open_question --reason "deferred by the model — why it may be the same feature: …"`;
     - `--deferral-kind OOS` is user-only for this class, because a model OOS deferral renders nowhere.
   - **"Cover"** means a §4 affected-area row AND a §5 AC that name the surface.
   - **Step 4.5's marker**, for every §6 entry the user did not state in their own words: `[excluded by the model] <item> (user sees: <what the user sees because of it, or "no difference">)`.
   - Step 4.7 now lists four §8 sources (build-time decision 4).
   - The pre-existing false `[exceeded cap]` literal at the `--increment-turn` sentence is corrected (build-time decision 5).
5. **1d — `src/commands/plan/main.md` (D5, plus build-time decisions 1 and 6).**
   - **Sub-question 6:** plan 98's non-decision arm is byte-intact. An escalation that ends without a decision is listed on a new conditional PHASE 3 line, `**Unconfirmed exclusions**:`, placed after `**Defaults applied**:`. The line names no marker literal and no separator.
   - **The orchestrator route for the architect's new uncovered-surface escalation** — a surface the spec neither covers nor excludes, including one named only in a §8 `[deferred to open question]` entry or in the §9 Risks row that cites its finding. The escalation is surfaced to the user:
     - cover → tell the user that covering it needs a spec revision, and add a Risk Assessment row;
     - leave out → add a Risk Assessment row;
     - no decision → ask once more; on a second reply that again decides nothing, the surface stays uncovered, with a Risk Assessment row, an entry on the PHASE 3 line, and the user told.
6. **1d — `src/agents/architect.md` (D6).** Rule 9's Out-of-scope-respect step gains one sentence for the opposite direction: escalate an uncovered, unexcluded feature surface per Rule 6. Rule 9's heading, number and six forcing steps are unchanged.
7. **1d — `src/agents/devils-advocate.md` Rule 6 (D7), plus `src/commands/grill/references/design-attack-checklist.md` (build-time decision 2).** An entry marked `[excluded by the model]` is not an exclusion the spec made deliberately; when it leaves out a feature surface, it is an upstream signal.

**Invariants and tests, as recorded at the build:**
- No `.py` file changed, and no plan vocabulary entered `src/`.
- The live-spec tests — `tests/lib/test_constitute_helper.py`, `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py` and `tests/scripts/test_claude_emitter.py` — are green: 328 passed and 2 skipped across the four files.

**Verify greps, re-run 2026-09-19 when this record was written:**
- `\[excluded by the model\]` under `src/` hits exactly three files: `specify/main.md`, `devils-advocate.md` and the grill checklist. The checklist is the deliberate additional site Phase 1d's Verify allows this record to name.
- `(user sees:` under `src/` hits `specify/main.md` only, so `plan/main.md` carries neither literal.
- `unresolved by the model` has zero hits under `src/`.
- `### Phase 2.4e — Feature-surface sweep (MANDATORY — mode-independent)` exists in `research/main.md`. A case-insensitive `check 2[1-9]` has zero hits there, and the hypothesis-suppression gate still says it is *"not one of its 20 checks"*.
- Phase 1's order note (build 1c before the devils-advocate sentence) exists to keep the marker literal byte-identical. The first grep above is what shows that it held.

#### Build-time decisions — recorded 2026-09-19

These are the choices the build made where the plan text was silent or said something narrower. Each item names the decision it extends. The orchestrator approved each one; none was put to the maintainer.

1. **The orchestrator route for the architect's uncovered-surface escalation (1d; extends D6 and D5).** D6 gave the architect an escalation with no command-side route. Without one, a reply that decides nothing would meet a command that names no arm for it, and `### Never` item 7 would end the turn. Sub-question 6 in `plan/main.md` now carries the route — cover, leave out, or no decision, each with its Risk Assessment row. The PHASE 3 `**Unconfirmed exclusions**:` line also lists, by name, each such surface that stays uncovered because its escalation ended without a decision — beyond the §6 entries D5's proposed text names.
2. **The grill checklist mirrors devils-advocate Rule 6 (1d; extends D7).** `src/commands/grill/references/design-attack-checklist.md` is injected into the adversary brief by the `render-brief` verb, so it carries the same sentence as Rule 6.
3. **A suspected, unevidenced Step 2b caller is `in` (1b; extends D3(c) and D10's P1).** Its justification states that there is no identity evidence. An `out` would need a user-visible difference the model cannot name. `in` there is not a coverage decision.
4. **Specify Step 4.7's §8 source list grew from two to four (1c; extends D4(e) and D10's P2).** The list was already incomplete, and the model's no-evidence deferral now points into it.
5. **The false `[exceeded cap]` literal corrected in specify (1c; pre-existing; see the dated amendment at D4(d)).** The `--increment-turn` sentence named a marker that no code renders. It now names the real render, `[deferred to open question]` with the reason `exceeded follow-up cap`.
6. **The §8 deferral named as a source of an uncovered surface (1d; extends D6 and D10's P2; an instruction-reviewer finding).** The architect's and plan's uncovered-surface sentences include a surface named only in a §8 `[deferred to open question]` entry or in the §9 Risks row that cites its finding, because that route writes it into none of §4, §5 or §6.
7. **D5's "`/devforge:plan` never edits `spec.md`" was not carried into `src/` (1d; narrows D5).** The emitted text makes the narrower true claim — the command "adds no affected area and no acceptance criterion to `spec.md`". See the dated amendment at D5 for why the original sentence is too strong.

### Phase 2 — Docs

- **`CHANGELOG.md`:** append to the existing `## [Unreleased]`, carrying the evidence class and the honest bounds.
- **The repo `CLAUDE.md`:** the index line moves to the DONE shape.
- **`PLAN-STATUS-ARCHIVE.md`:** add an entry.
- **`DEVELOPMENT-STATUS.md`:** a Key Design Decisions item, or a recorded verified no-op.
- **Dated one-line notes in other plans:**
  - plan 98, at its D2 table row for `/devforge:plan`'s architect §6 Out-of-Scope escalation;
  - plan 81, at F1;
  - plan 86, at F5 — §6.1 and architect Rule 9 each gained a second sentence, if D2 / D6 were ratified;
  - plans 23 and 85 — devils-advocate Rule 6, if D7 was ratified.
- **Every checked site is recorded as an edit or as an explicit verified no-op.**

#### Verify

- `99-SCOPE` greps in the repo `CLAUDE.md` and in `PLAN-STATUS-ARCHIVE.md`.
- Each dated note exists, or the decision that conditioned it is recorded as declined. *Amended 2026-09-19 (build): a note site that does not exist in the target plan is recorded as a VERIFIED NO-OP, with the grep that shows it is absent — plan 23 is the case (see `#### Phase 2 build record`). This matches this phase's closing bullet, which already accepts "an explicit verified no-op".*
- No tracked file names a client, a client component or a benchmark path.

#### Phase 2 build record — 2026-09-19

**Route: instruction-author wrote this sweep in three parallel parts; instruction-reviewer then reviews all of it.** Docs only: no Python and no test. **The Phase 2 docs commit follows this sweep.**

**instruction-reviewer outcome: SHIP-READY, 0 findings** — one pass over all nine files, 2026-09-19, which re-verified every count, SHA, grep claim and no-op against the tree.

**This plan document, edited in this sweep:**
- the `**Status**:` line;
- `#### Phase 1 build record`, `#### Build-time decisions` and this record;
- `## Residuals (found during the build, not fixed)`;
- four dated build amendments: F7, D4(d), D5, and `## When resuming work` step 3;
- a dated note at this phase's Verify, for a note site the target plan does not have;
- dated notes at OQ-1 and at `## Context for next session`'s **Also remember**, naming the grill checklist as the third site that quotes the marker literal.

**The rest of this phase's list — each site an edit or an explicit verified no-op, as this phase's closing bullet requires:**

| Site | Outcome |
|---|---|
| `CHANGELOG.md` | **EDIT** — one entry appended to the existing `## [Unreleased]` → `### Changed`. The evidence class comes first and the honest bounds come last. |
| Repo `CLAUDE.md` — the plan-99 index line | **EDIT** — the line now has the DONE shape. |
| Repo `CLAUDE.md` — the "Where to find what" router | **VERIFIED NO-OP — not edited.** Nothing this build changed falsifies the `/grill` row. The router's stale `_PROMOTED` (20 names) and "16 commands model-invocable" counts date from plan 95. They are plan 98's recorded residual 8, not this plan's. |
| `PLAN-STATUS-ARCHIVE.md` | **EDIT** — the plan-99 entry was added after plan 98's. One wrong claim in it — that `resolve-open-question` re-renders the spec — was corrected in the same sweep: the verb records a resolution in specify-state, and the spec's render strikes the resolved entry through. |
| `DEVELOPMENT-STATUS.md` | **EDIT** — `## Key Design Decisions` item 20 was added. The false `[exceeded cap]` literal on the `specify.md` bullet was corrected to a §8 `[deferred to open question]` entry with the reason `exceeded follow-up cap`. That closes the finding `## Residuals` leaves to this record. |
| `README.md` | **VERIFIED NO-OP — not edited.** A case-insensitive grep for `scope` / `minimal` / `surface` / `out of scope` / `rules` returns four lines (55, 66, 77, 89), and none states anything this build falsified. |
| `98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md` | **EDIT** — a dated note under the D2 table, plus an inline pointer to it in the D2 table's `/devforge:plan` §6 Out-of-Scope row. |
| `81-INFERENCE-RULES-PLAN.md` | **EDIT** — a dated note at F1. ⚠ The file is UNTRACKED, so the note rides no commit. It quotes nothing from the untracked evidence file beside it. |
| `86-FOWLER-REFACTORING-GAPS-PLAN.md` | **EDIT** — a dated note in `### Phase 5 — F5: the preparatory-refactoring lane`: §6.1 and architect Rule 9 each gained a second added sentence. |
| `85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md` | **EDIT** — a dated pointer at the `## Non-goals` bullet that names `references/design-attack-checklist.md`. No site in that plan describes devils-advocate's Out-of-Scope respect, so the note sits where the plan names the file this build changed. |
| `23-ADVERSARIAL-GRILLING-PLAN.md` | **VERIFIED NO-OP — not edited.** No site describes devils-advocate's Out-of-Scope respect, and the plan never names `references/design-attack-checklist.md`. `Out-of-Scope\|Out of Scope\|§6\|out-of-scope\|OOS` returns one line, where `OOS` matches inside *CHOOSES*. `respect\|devils-advocate\.md\|Rule 6` returns six lines; every one matches only on the path `src/agents/devils-advocate.md`, and `respect` and `Rule 6` have zero hits. |

### Phase 3 — Consumer e2e — DEFERRED, user-driven HARD GATE, NOT run

**Everything above is build-verified at best, never consumer-validated, until this phase runs.** Per OQ-5, the fixture is a testForge20 feature visible on two surfaces through different request paths. The anchors are known-answer cases, **scored in PAIRS**: a rule that pulls in everything passes the first half and fails the second.

1. **A named feature visible on two surfaces through different request paths.** Research records the second surface — a 2.4e finding plus an `affected_area` gap — specify asks a `scope_boundaries` decision point, and an explicit user answer is honored. *(Amended by D10, 2026-09-19: the finding cites the second surface's user-visible identity evidence.)* **PAIRED WITH 2.**
2. **A different feature that merely shares code with the change.** It is NOT pulled in and NOT raised as a feature-surface gap. Its Step 2b row is `out`, with a user-visible "shows a different feature" justification.
   - *Amended by D10, 2026-09-19:* the model cites NO user-visible identity evidence for it and does not cover it.
   - **This anchor runs in delegated or auto mode — the blind protocol.** That is where the safeguard has to hold without a human backstop. *(Note added 2026-09-20 — plan 100: specify asks the decision point even with Claude Code's auto mode on, so this anchor is run by DELEGATING the reply; auto mode no longer names a path on which the question is skipped.)*
3. **The user delegates that decision point.** The spec covers the surface (a §4 row plus an AC naming it), or excludes it with `[excluded by the model] <item> (user sees: <user-visible reason>)`. §8 shows `[default applied]` with the delegation, and Step 5.1 lists it. **PAIRED WITH 4.**
4. **The user excludes the surface in their own words.** The §6 entry carries NO marker.
5. **A plan escalation on a §6 exclusion, delegated twice — run once on a marked entry and once on an unmarked one.**
   - The exclusion stands both times, and PHASE 3's `**Unconfirmed exclusions**:` lists both.
   - The marked entry is listed with its prefix; neither shows a `(user sees: …)` clause.
6. **(If D7 is ratified.)** The grill surfaces a marked exclusion of a feature surface as an upstream signal.
7. **(Added by D10, 2026-09-19.) A surface the model suspects shows the feature but cannot evidence**, run in delegated or auto mode. *(Note added 2026-09-20 — plan 100: the decision point is asked in either case, so this anchor is run by delegating the reply.)*
   - Specify records it as a §8 `[deferred to open question]` entry, with a reason that says the model deferred it.
   - It is neither covered (no §4 row or AC names it) nor excluded (no §6 entry names it).
   - Its Phase 1.5 finding lands in §9.

#### Verify

- Every anchor is scored **explicitly** — stated, not summarized — with each pair scored together.
- **If an anchor fails**, record the negative with the artifacts and name the mechanism before proposing any fix. A missed enumeration is a D3 finding; a wrong model answer is D1 / D4(b); an unmarked model exclusion is D4(d); over-inclusion is D1 / D3(c). *(Added by D10, 2026-09-19: a cover or exclusion resting on no cited identity evidence, or an unevidenced surface covered or excluded instead of deferred, is a D10 finding.)* **They have different fixes.**
- **A clean run shows the rules behave on planted fixtures, NEVER that the gap cost anything.** The only observed instance is on a frozen install, and it cannot be re-run.

---

## Residuals (found during the build, not fixed)

Each item below was found during the build and deliberately left unfixed. ⚠ Line digits drift — grep the quoted text. *(Note added 2026-09-20: all six items were taken up by `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md`, which owns them — item N there is residual N here; each item below whose text this falsified carries its own note. That plan is build-verified only; its consumer e2e has not run.)*

1. **Two sibling escalations have no non-decision arm (pre-existing).** The plan template's Rule 5 AC-conflict escalation in `plan/main.md`, and architect Rule 9's rejected-alternative step, have no arm for a reply that decides nothing. Sub-question 6's escalations have one; these siblings do not.
2. **Auto mode is unaddressed at sub-question 6.** Nothing says whether a sub-question-6 escalation pauses in auto mode, and both escalation directions — the §6 one and the uncovered-surface one — inherit that ambiguity. *(Note added 2026-09-20 — plan 100's item 2 dissolves the question rather than answering it in place: no branch of `/devforge:plan` depends on auto mode any longer, so a sub-question-6 escalation is put to the user whichever permission mode is on.)*
3. **`plan/main.md` PHASE 2.5 step 4 is a seam.** It reads *"does the plan's File Impact list files NOT in the spec's Affected Areas? If yes, note them as additions discovered during planning"*. An uncovered surface's files could therefore enter File Impact without the sub-question-6 escalation.
4. **A model's no-evidence deferral is not visible at spec approval.** Specify's Step 5.1 summary lists neither §8 deferrals nor Risks — the cost D10 records for declining the peer's `[unresolved by the model]` variant. *(Note added 2026-09-20 — plan 100's item 4 closes the §8 half: Step 5.1 now carries a conditional `**Deferred to open questions**:` bullet listing every `deferred_open_question` decision point. The Risks half stands — Risks are still not listed there.)*
5. **OQ-4's "bundled per call" rides the existing bundling threshold.** The bundling rule applies at ≥4 qualifying questions; below it, surface decision points may be asked separately.
6. **Research check 12b's stderr.** In `_research/_cmds_render_verify.py`, check 12b's message says Phase 2.4 must probe the runner-up frame. Phase 2.4e rows tagged `--framing runner-up` now also satisfy check 12b. The message is not falsified, and the Python stays untouched.

One further build finding is not listed here because Phase 2's docs sweep corrects it: `DEVELOPMENT-STATUS.md` carries the same false `[exceeded cap]` literal that build-time decision 5 corrected in specify. `#### Phase 2 build record`, still pending when this list was written, is where that edit gets recorded.

---

## Non-goals

- **Mechanical detection of "the same feature".** It stays model judgment — the stated bound.
- **Any Python in v1.** D4(f)'s helper flag and OQ-3's handoff wiring are named strengthening arms, not built.
- **Any gate, validator, `verify-*` number or research check number.**
- **Changing the emission matrix or plan 81's rules** (F10).
- **Widening scope automatically.** The rule forces the decision to be visible, not the change to be bigger.
- **Per-site edits in discover / implement / fix / review / verify** (D8).
- **Back-porting into shipped installs**, and **any touch of the frozen benchmark install.**
- **Anything specific to the benchmark.**

---

## Context for next session

⚠ **Evidence class, repeated: ONE observed instance. Every other site is predicted, and nothing was measured.** In that instance the model found the second surface itself; what failed was the decision. The evidence is held outside this repo and is not quoted here. ⚠ All line digits drift — grep the quoted text.

**The one sentence that governs everything here:** minimality limits how a change is built, never which user-facing surfaces it covers. When unsure, the default is to ask — never silent inclusion and never silent exclusion.

**Trap 1 — citing Step 2b as covering the incident class.** Step 2b classifies callers of the changed helper only, so it cannot see a different-path surface (F1).

**Trap 2 — a suffix marker, or an em-dash reason.** `/devforge:plan` keeps the first 80 characters of a §6 item (F7), so keep the marker a prefix. §6 already renders ` — <finding_ref>` after a cited item (F5), so keep the reason in `(user sees: …)` — the format is `[excluded by the model] <item> (user sees: <what the user sees because of it, or "no difference">)`.

**Trap 3 — `--rationale` as an open-question carrier.** It is an 80-char picker summary at specify, gated by check 11 and by `verify-hypothesis-suppression` (F3).

**Trap 4 — "shares code" read as "same feature".** Over-inclusion is the pair-failure (Phase 3 anchors 1 + 2).

**Trap 5 — a `"one place"` scope pick read as an exclusion.** It excludes nothing research later finds (D3(c)).

**Trap 6 — item 3 and §6.1 read as "which surfaces".** That reading is the reason D2 exists.

**Trap 7 — "raised with the user" in auto mode.** There it means listed at the approval summary — Step 5.1's `**Defaults applied**:` and §6 in full — not a question. *(Amended by D10, 2026-09-19: an unevidenced surface the model defers goes to §8 instead, which Step 5.1 does not list — the cost D10 records.)* *(Note added 2026-09-20 — plan 100: both halves of this trap moved. Specify asks every decision point whichever permission mode is on, so "raised with the user" is a question again rather than a listing; and Step 5.1 now lists every `[deferred to open question]` entry, retiring D10's cost.)*

**Trap 8 — reading a predicted site as observed.** ONE observed instance, every other site predicted, nothing measured; the frozen install cannot be re-run.

**Trap 9 — leaking the client.** No client identifier anywhere. Plan 81's file is untracked and sits beside untracked private-client benchmark evidence, so its dated note quotes nothing from that evidence.

**Trap 10 — a clobbered ledger edit.** Another session may be building in this checkout. F12 records plan 97 doing so while this plan was drafted; it has since closed. Before touching any ledger, re-read `git status`, then read the ledger live. Commit by explicit path.

**Trap 11 — a model-made deferral to §6.** On a `scope_boundaries` decision point about a surface showing the named feature, `set-dp-deferral --deferral-kind OOS` is the USER's route only — their own words punt it to §6. `deferred_OOS` renders in neither §6 nor §8, so a model deferral there is an exclusion no reader of the spec sees. The model's answer goes through `set-dp-default-applied` under D4(b)'s value rule. *(Amended by D10, 2026-09-19: that holds for a surface with cited identity evidence. With no evidence, the model's route is `set-dp-deferral --deferral-kind open_question`, never `OOS`.)*

**Also remember:** the marker literal is defined once, in specify (1c), and quoted byte-identically in devils-advocate (1d, D7) — build 1c before that edit. *Amended 2026-09-19 (build): the grill's `references/design-attack-checklist.md` quotes it byte-identically too — the deliberate additional site of build-time decision 2.* `plan/main.md` names no literal. D5's `**Unconfirmed exclusions**:` line fires on EVERY sub-question-6 escalation that ended without a decision, marked or not, and never quotes a `(user sees: …)` clause.

**File anchors:**

- `src/CLAUDE.md` — `### Always` (item 17 appends after item 16) and `### Never` item 7 (read-only here).
- `src/constitution.md` — `### 6.1 Minimal Changes [universal]` (D2 only).
- `src/commands/research/main.md` — Phase 2.3b's surface-count frame; Phase 2.4c Step 2b; Phase 2.4d (the new 2.4e follows it); Phase 2.6; Phase 3 `### Setters (in order)` step 3.
- `src/commands/specify/main.md` — Phase 2 categories, the per-decision-point protocol and question rounds; Step 4.4 (the §8 + §9 precedent); Step 4.5.
- `src/commands/plan/main.md` — architect sub-question 6; PHASE 3's approval summary.
- `src/agents/architect.md` — Rule 9's `**Out-of-scope-respect forcing step:**`.
- `src/agents/devils-advocate.md` — Rule 6, *"Respect the spec's Out-of-Scope."*
- Read-only references: `_research/_cmds_phase0.py` (`cmd_record_gap`), `_research/_render.py` (`## Open Uncertainties`), `_research/_handoff_build.py`, `_specify/_render.py` (§6 and Step 5.1), `_shared/text_overlap.py`, `plan_helper.py` (`_render_sec6`, `_truncate`), `_constitute/_schema.py` (`_UNIVERSAL_SECTIONS`).

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation.
2. **Check `## Phase 0 close record` first.** If it still reads *Pending*, nothing is ratified and **no build phase may start.** If it holds only a dated D5-only entry, that entry permits D5's build alone; everything else still waits for the full close.
3. **Re-verify F1–F12 against the live tree**, because line positions drift. Grep the quoted text, never the digits — `Step 2b — Trace each caller`, `other surfaces reach the same shared symbol`, `mechanically probed downstream`, `record-gap`, `NEEDS CLARIFICATION`, `scope_boundaries`, `CANNOT answer by reading`, `NOT included:`, `_render_sec6`, `exclusion stands — record no override`, `Minimal Changes [universal]`, `Out-of-scope-respect forcing step`, `Respect the spec's Out-of-Scope`. F12 is dated history, not a live state: plan 97 closed at `0a3d978`, and none of its `src/` files is one this plan edits. What still needs a live check is whether any other session has work in progress in this checkout, so run `git status`.
   - ⚠ *Amended 2026-09-19 (build): two of these grep strings are gone from `research/main.md` by design. Phase 1b's Phase 2.3b widening (D3(a)) replaced `other surfaces reach the same shared symbol` and `mechanically probed downstream`; grep the live strings `other surfaces show the user the same feature` and `probed downstream: mechanically` instead. Zero hits for the old strings is the built state, not a regression. F1–F12 describe the tree BEFORE Phase 1, so F2 quotes the replaced text. The build also changed what F7 describes (see its amendment), F8 (`### Always` now has 17 items) and F9 (§6.1 now ends with the sentence D2(a) appended).*
4. **Before Phase 2 touches any ledger, apply F12's rule** (Trap 10): re-read `git status` — another session may be building in this checkout — and read the ledger live. Never stage a file this plan did not edit.
5. **Route every edit through the house flow:**
   - instruction-author → instruction-reviewer for every markdown edit;
   - `claude-code-guide` for every Claude-Code-integration fact.
6. **Commit by explicit path, never `git add -A`.**
7. **After each sub-phase, cross-check.** Grep every heading, verb, flag, token and phase number touched — `2.4e`, `3b`, `[excluded by the model]`, `Unconfirmed exclusions` — and fix any dangling reference in the SAME change.
8. **Run Phase 2, then leave Phase 3 to the maintainer.**
9. **Keep the evidence class attached.** Any summary of this plan repeats it: ONE observed instance, every other site predicted, nothing measured.
