# 100 — Scope Rule Follow-Ups Plan

**Created**: 2026-09-19
**Status**: **Phase 0 CLOSED 2026-09-20** — every decision (D1–D14) and every open question (OQ-1–OQ-5) ratified as recommended by a single blanket maintainer directive, with no per-item deliberation supplied. Detailed plan written 2026-09-19; item 2's scope was picked by the maintainer 2026-09-19 via AskUserQuestion: (c). **Build pending** — Phases 1–4 not started. **Phase 5 consumer e2e is DEFERRED and user-driven.**

⚠ **Evidence class, to be repeated in every summary of this plan: NO incident. Items 1 and 3–6 are gaps found by reading during plan 99's build — predicted, nothing observed. Item 2 is a maintainer directive. Nothing was measured.**

Plan 99 found six residuals during its build and left them unfixed; this plan takes them up. Item 1 gives `/devforge:plan`'s acceptance-criteria-conflict escalation an orchestrator route with a named arm for a reply that decides nothing, and maps every architect escalation to its route. Item 2 makes the three commands that ask clarifying questions — `/devforge:specify`, `/devforge:plan` and `/devforge:breakdown` — ask them whether or not Claude Code's auto mode is on, by removing every auto-mode branch in them. Item 3 closes the `/devforge:plan` PHASE 2.5 step 4 seam through which a surface's files could enter the plan unescalated. Item 4 lists every decision point deferred to an open question in specify's Step 5.1 approval summary. Item 5 makes a question round one `AskUserQuestion` call and bundles independent questions always. Item 6 makes research check 12b's message name every phase whose findings satisfy it.

---

## Expansion note — 2026-09-19

The first version of this file (the "frame", same day) recorded what, why and where, and left the design to this rewrite. What changed:

1. **Item 2's scope is answered: (c)** (F7). The frame's first question was put to the maintainer through `AskUserQuestion`. D1–D6 design (c).
2. **The frame's three owed `claude-code-guide` checks are discharged** (F8). The drafting author re-fetched four vendor pages the same day and added two facts the frame did not have: auto mode is the built-in starting permission mode on Pro, Max and Team plans, and `AskUserQuestion` is on the vendor's list of actions no mode auto-approves.
3. **Auto mode's Python footprint is wider than the frame's two gates** (F11): a verb, two constants, a facade re-export, a state key and a dashboard key — plus test fixtures that seed defaults through auto mode (F12).
4. **specify's auto-path prose has more sites than the frame named** (F9), among them the stop rule, Step 4.5's marker rule and two deferral-path sentences.
5. **breakdown's escalations are enumerated** (F5), with their restatements kept apart from the three sites.
6. The frame's items keep their numbers; `## Item → decision map` traces each one.

---

## Origin & evidence

- **Source.** `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md` `## Residuals (found during the build, not fixed)`, items 1–6. Item N here is plan 99's residual N. ⚠ One widening in scope, not in numbering: item 1's scope was widened while drafting past residual 1's two literal sites (the Rule 5 note and architect Rule 9's rejected-alternative step) to `/devforge:breakdown`'s human escalations generally, beside the full map of the architect's escalations at `/devforge:plan` (F5, D10). Plan 99 is DONE (build): Phase 0 close `5923e04`, D10 `cf6dc1c`, Phase 1 `6a786b3`, Phase 2 `6838c1c`. Its Phase 3 consumer e2e is deferred and not run.
- **Directive.** Given 2026-09-19 in Ukrainian. English paraphrase: fix items 1, 3, 4, 5 and 6; for item 2, *"clarifying questions are needed even in auto mode"*.
- ⚠ **The orchestrator's reading, not the maintainer's words.** The maintainer wrote "3" twice and no "4". The orchestrator read the second "3" as item 4 and told the maintainer so. The item list rests on that reading.
- **Item 2's scope** was picked by the maintainer on 2026-09-19 (F7): (c), every clarifying question in the three commands.
- **Context for item 2.** Plan 99's D10 records that the benchmark operator's blind protocol answers every content question with a delegation. Asking in auto mode routes such runs through plan 98's delegated path, which records the delegation, instead of through defaults applied without a question. This says why the directive matters. It is not evidence that anything failed.

### Verified structure (2026-09-19)

Every fact below was checked against the tree on 2026-09-19; vendor facts carry their URL. ⚠ Line digits drift — **grep the quoted text, never the digits.**

#### Item 1 — the AC-conflict escalation and every architect escalation

**F1 — The Rule 5 note.** `src/commands/plan/main.md`, the `[Rule 5: …]` bracket under the plan template's `### Key Design Decisions`. An identical reachable tuple with opposite required outputs *"is an acceptance-criteria conflict, not an implementation gap to bridge: surface it to the user as a product question naming both criteria and the shared tuple — the architect escalates it per its Rule 6 (termination), triggered by its Rule 9 rejected-alternative checkability step — rather than recording a discriminator parameter that forces the tuples apart"*. No sentence says what happens on a reply that decides nothing, what is recorded, or what the Key Design Decision records while the conflict stands.

**F2 — Six escalation sites in `src/agents/architect.md`** (grep `escalat`):
- Rule 6: *"You decide, or you escalate to the user on spec-level ambiguity"*.
- `### Termination rule — you always decide`: *"(in which case, stop and escalate to the user)"*.
- `### How to consult` step 1: *"escalate per the Out-of-scope-respect step in Rule 9"*.
- Rule 9, three sentences:
  - the Out-of-scope-respect step: *"naming the §6 entry and why you believe it cannot stay excluded"*;
  - its opposite direction: *"**escalate it to the user** per Rule 6, naming the surface and what the user sees there"*;
  - the `**Rejected-alternative checkability forcing step:**`: *"**escalate to the user** per Rule 6 (the termination rule), naming the two ACs and the identical tuple"*.

**F3 — The routes `plan/main.md` has today.**
- **Sub-question 6** carries a named non-decision arm in both directions.
  - The §6 direction (plan 98): after a second non-deciding reply, *"the spec's §6 Out of Scope exclusion stands — record no override of it"*.
  - The uncovered-surface direction (plan 99): three arms, each writing a Risk Assessment row. The non-decision row ends *"left uncovered; the user did not decide it"*.
  - Both non-decision outcomes are listed on PHASE 3's `**Unconfirmed exclusions**:` line. Sub-question 6 states that the command *"adds no affected area and no acceptance criterion to `spec.md`"*.
- **PHASE 2.5 step 6** re-enters Phase 1.3 for an OOS-reaching decision (*"or escalate the §6 concern to the user per its Rule 6 (termination)"*). Steps 7 and 8 re-enter Phase 1.3 the same way.
- **PHASE 2.5 step 3:** *"If you cannot determine the implementation path, add it to the plan's Risk Assessment as: "AC-[N] has no clear implementation path — requires clarification during breakdown"."* Its first arm reads *"Revise the plan to add the missing coverage."*
- **PHASE 3's interactive bullet is the only generic route:** *"if the plan surfaces decision points the spec didn't resolve (…), pause and ask the user via `AskUserQuestion` (or fallback to numbered markdown list) before writing"*. A hand-back takes *"your recommended default, mark it `[default applied]`, and list it under "Decision Points Resolved""*. Nothing routes the architect's generic Rule 6 escalation, or the AC conflict, specifically.
- **PHASE 3's approval summary has eight conditional lines**, each with its own omit rule: `**Defaults applied**:`, `**Unconfirmed exclusions**:`, `**Departures from convention**:`, `**Pure-builder targets**:`, `**Dead code declared**:`, `**Follow-on cleanups**:`, `**Emission matrix**:`, `**E2E scenarios**:`.

**F4 — The two readings `src/CLAUDE.md` `### Never` item 7 allows for the AC conflict.** The text picks neither.
- **(a) A content question.** The conflict counts as one of PHASE 3's *"decision points the spec didn't resolve"*, whose channel is `[default applied]`. On a hand-back the model then picks which acceptance criterion wins — a product decision the Rule 5 note sends to the user, taken by the model, and looking resolved. **This is the dangerous reading.**
- **(b) A run decision.** Item 7: *"A question the command does not classify decides what the run does."* The question is asked once more; on a second such reply, *"end the turn having written nothing"*.

**F5 — `/devforge:breakdown`'s human escalations** (`src/commands/breakdown/main.md`; grep `the human`). Three sites, none with a named arm for a reply that decides nothing:
- PHASE 2 sub-question 4: *"if the missing piece is a decision `/devforge:plan` should have made rather than a wording gap, escalate to the human."*
- The Agent Assignment paragraph: *"If splitting is genuinely impossible, escalate to the human."*
- *"If the owning stack's implementer is not generated for this project (not all projects generate all agents), split or escalate to the human — never fall back to `architect`"*.

Three restatements add no route: PHASE 2 relay-loop step 1 (*"surfaces as a human-escalation rather than a draft-task revision — route it per sub-question 4"*), the `qa-engineer` paragraph (*"the split-or-escalate rule applies as for any other missing implementer"*), and IMPORTANT RULES item 3 (*"per the Agent Assignment table's split-or-escalate rule"*). ⚠ All three escalations arise after PHASE 0b, which may already have flipped `plan.md`'s `**Status**:` to Approved on disk.

**F6 — The architect cannot ask the user.**
- Phase 1.3: *"Orchestrator-mediated consultation relay (the architect emits requests; it does NOT invoke anyone)"*.
- Vendor: `AskUserQuestion` is removed from every subagent *"even when listed in the `tools` field"* (https://code.claude.com/docs/en/sub-agents.md). The Agent SDK page states *"`AskUserQuestion` is not currently available in subagents spawned via the Agent tool"* (https://code.claude.com/docs/en/agent-sdk/user-input.md).
- How the user is reached instead is this framework's own relay — the orchestrator surfaces the escalation. That part is not a vendor statement.

#### Item 2 — auto mode

**F7 — The maintainer's scope pick.** Put on 2026-09-19 through `AskUserQuestion`, with three options: (a) escalations only; (b) product and scope questions; (c) every clarifying question in `/devforge:specify`, `/devforge:plan` and `/devforge:breakdown`. The option marked (Recommended) was (c). **The answer was (c).** It is an explicit pick, not a delegation (plan 98's D1 distinction).

**F8 — Claude Code's auto mode, per the vendor.** From a `claude-code-guide` check the orchestrator ran on 2026-09-19. The drafting author re-fetched each quote marked † the same day.
- **What it is.** A permission mode: a classifier model reviews actions instead of prompting. It is turned on with `--permission-mode auto`, `permissions.defaultMode: "auto"`, or the mode selector (https://code.claude.com/docs/en/permission-modes.md).
- **The nudge.** † *"Auto mode also nudges Claude to keep working without stopping for clarifying questions, though Claude still asks when your prompt or a skill explicitly relies on it."* (same page).
- **How common it is.** † *"On Pro, Max, and Team plans, the built-in starting permission mode is auto mode."* (same page).
- **`AskUserQuestion` in auto mode.** Available, and it blocks until the user answers. † The same page lists *"the built-in `AskUserQuestion` tool"* among the actions *"Claude Code doesn't auto-approve … in any mode"*.
- **When it is unavailable.**
  - `dontAsk` mode denies it — *"In `dontAsk` mode both cases are denied instead, because that mode never prompts."* (https://code.claude.com/docs/en/agent-sdk/permissions.md); † *"`AskUserQuestion`, … are denied even when an allow rule matches"* (https://code.claude.com/docs/en/headless.md).
  - † *"With `--permission-prompts none`, Claude Code removes the tools that need an answer from a person, such as [`AskUserQuestion`], so Claude can't call them."* (headless.md).
- **The per-call limit.** † *"each `AskUserQuestion` call supports 1-4 questions with 2-4 options each"* (https://code.claude.com/docs/en/agent-sdk/user-input.md). That is the Agent SDK page; the Claude Code CLI docs do not state the limit. `multiSelect` exists.
- **Not documented:** whether auto mode injects a system reminder, or its wording.
  - Observation only, not a vendor statement: the orchestrator's 2026-09-19 session context contained the text "While auto mode is active", which contains specify's C-strict substring `auto mode is active`.
  - Observation only: the `AskUserQuestion` tool description loaded in that session says users can always pick "Other" for free text.

**F9 — The auto-mode branches in the three commands' markdown.** A grep for `auto mode` / `auto-mode` / `auto path` / `mode=auto` / `DEVFORGE_AUTO_MODE` / `detect-mode` / `--auto` / `operate autonomously` / `system-reminder` under `src/commands/` hits only these three files (2026-09-19). `src/constitution.md` and `src/CLAUDE.md` do not mention auto mode.
- **`plan/main.md` PHASE 3** — three bullets under *"**Mode-dependent execution path** — auto vs interactive paths:"*:
  - the auto bullet: *"**If auto mode is active** (detect via `<system-reminder>` about auto mode, or explicit user instruction to operate autonomously): do not pause for clarifying questions during plan creation. Apply model's recommended defaults to any decision the spec left as `[default applied]` or that the plan surfaces fresh. Document each in a "Decision Points Resolved" subsection of the plan summary, marked `[default applied]`. The user reviews defaults at the approval gate below."*;
  - the interactive bullet (F3), which closes *"list it under "Decision Points Resolved" exactly as auto mode does"*;
  - *"**When uncertain about mode**: prefer pausing (interactive default)."*
  - Separately, the `**Defaults applied**:` line's bracket reads *"whether applied in auto mode or on a decision point the user handed back to you"*.
- **`breakdown/main.md` PHASE 4** — three bullets under *"**Mode-dependent execution path** (mirrors `/devforge:plan` Phase 3):"*:
  - auto: *"do not pause for clarifying questions during decomposition. Apply the model's recommended defaults to any boundary the plan left open."*;
  - interactive: *"the architect consultation in Phase 2 is the place to resolve them; present the resolved breakdown here."*;
  - the uncertain-mode bullet.
- **`specify/main.md`:**
  - Phase 2 intro: *"either ask clarifying questions (interactive mode) or apply named defaults (auto mode)"*;
  - `### Mode detection` in full, including *"**When uncertain about mode → prefer interactive (the helper's default).**"*;
  - per-decision-point protocol step 2: *"auto path vs interactive path"*, *"Every wrong-mode call is a hard helper gate (exit 2)"*, the three quoted gate messages, *"The orchestrator picks the setter that matches the mode `detect-mode` persisted in state"*, the **Auto path** block, and the **Interactive path** heading's *"(mode=`interactive`)"*;
  - the delegated paragraph's *"exactly as an auto-mode default does"*;
  - *"**The value you supply for a surface.** On the auto path and the delegated path alike"*;
  - *"In interactive mode, a surface with no identity evidence is still asked like any other decision point. These two cases govern only your own answer, when the user hands it back or when no question is asked."*;
  - step 3's *"**Deferral path** (either mode). When the user (or auto-mode rationale) explicitly punts"*, and its two surface bullets — *"on the auto path and the delegated path alike (step 2)"* and *"on the auto path or the delegated path"*;
  - `### Question rounds`: *"so in interactive mode a `scope_boundaries` decision point about such a surface is always asked"*;
  - the stop rule: *"In auto mode, a recorded default (`set-dp-default-applied`) also satisfies (a) for stop-rule purposes"*;
  - Step 4.5's marker rule: *"The rule covers a `leave <surface> out` value you chose in Phase 2, an auto-mode default, and any exclusion you add while writing this section."*;
  - Step 4.7's source 3: *"Decision points resolved by a default, in auto mode or on a delegated reply"*;
  - Step 5.1: *"auto-mode defaults and delegated ones alike"*.

**F10 — The framework has two different detection rules.** plan and breakdown detect auto mode *"via `<system-reminder>` about auto mode, or explicit user instruction to operate autonomously"*. specify counts three C-strict signals only: *"User natural-language prose is not a signal."* So today a user's "just decide" switches plan and breakdown to their no-question branch, and does not switch specify.

**F11 — specify's auto-mode Python** (grep 2026-09-19; the builder re-greps):
- **`_specify/_cli.py`:** the `detect-mode` subparser (`--auto`, `--reminder-text`); `set-dp-answer`'s help (*"Interactive path: …"*); `set-dp-default-applied`'s help (*"Auto path: …"*); and `--delegated-reply`'s help (*"mode=interactive only … rejected in mode=auto."*).
- **`_specify/_cmds_phase01.py`:** `detect_mode()` and `cmd_detect_mode`. The module docstring names *"detect_mode helper"*.
- **`_specify/_schema.py`:** `AUTO_MODE_ENV_VAR = "DEVFORGE_AUTO_MODE"` and `AUTO_MODE_REMINDER_SUBSTRINGS` (`"auto mode is active"`, `"auto mode still active"`).
- **`src/devforge/lib/specify_helper.py`** (the facade): re-exports `AUTO_MODE_ENV_VAR`, `AUTO_MODE_REMINDER_SUBSTRINGS` and `detect_mode`.
- **`_specify/_state.py`:** `default_state()` carries `"mode": None`.
- **`_specify/_cmds_phase3.py`:** `cmd_summary`, the `summary` verb (*"Emit phase-progress + counts dashboard JSON."*), outputs `"mode": state.get("mode")`.
  - ⚠ `rubric-coverage` (`cmd_rubric_coverage` in `_cmds_phase2.py`) emits only the `{category: state}` map and carries no `mode` key.
  - No command spec under `src/` calls `specify_helper summary` (grep 2026-09-19). One test pins its `mode` key (F12).
- **`_specify/_cmds_phase2.py` — three gates, each exit 2:**
  - `set-dp-answer` rejects when `mode == "auto"`;
  - `set-dp-default-applied` rejects when `mode == "interactive"` and `--delegated-reply` is absent;
  - `set-dp-default-applied` rejects `--delegated-reply` when `mode == "auto"`.
  - ⚠ While `mode` is `None` — `detect-mode` never run — neither mode gate fires, so today a default can be recorded with no reply at all.
  - The docstrings of `cmd_set_dp_answer` (*"Interactive path."*) and `cmd_set_dp_default_applied` (*"Auto path."*) describe the modes.
- **`_specify/_render.py`:** `_approval_summary`'s docstring says its defaults list covers *"auto-applied and delegated alike"*. The §8 and Step 5.1 renders append the delegation suffix only when `delegated_reply` is non-empty, so a `default_applied` entry with no reply renders `[default applied]` with no suffix.
- **No outside users.** No user of `--auto`, `DEVFORGE_AUTO_MODE` or specify's `detect-mode` exists outside `_specify/`, the facade, `specify/main.md`, the tests and the docs (repo-wide grep 2026-09-19; `scripts/` has none).
- ⚠ `research_helper` has its OWN `detect-mode` — bug vs enhancement, with `--override`. It is a different verb, and this plan does not touch it.

**F12 — Tests.**
- `tests/lib/test_specify_helper.py` holds 43 occurrences of `DEVFORGE_AUTO_MODE|AUTO_MODE|detect_mode|detect-mode|--auto|--reminder-text|reminder_text` (2026-09-19). They are:
  - a constants test (`test_mode_detection_signals`);
  - `detect_mode()` unit tests and `detect-mode` CLI tests;
  - gate tests for all three mode gates;
  - the `summary` test asserting `data["mode"] == "interactive"`;
  - fixtures that set `DEVFORGE_AUTO_MODE=1` to seed `set-dp-default-applied` without `--delegated-reply` — among them `test_renders_dp_default_applied_in_open_questions`, which pins the no-suffix §8 shape.
- ⚠ The single hits in `tests/lib/_specify/test_find_handoffs_require.py`, `tests/lib/test_plan_helper.py` and `tests/lib/test_research_design_anchor.py` are `research_helper detect-mode --override` — research's verb, unaffected.

**F13 — Docs.**
- `DEVELOPMENT-STATUS.md`'s `specify.md` bullet: *"with C-strict mode detection (`DEVFORGE_AUTO_MODE=1` env / `--auto` flag / `<system-reminder>` substring) — auto path uses `set-dp-default-applied`, interactive uses `set-dp-answer` after AskUserQuestion or markdown fallback"*. The same bullet says *"Phase 5 hard-gate approval via deterministic `render-summary` 4-bullet block"*, stale since plan 98 added the conditional `**Defaults applied**:` bullet.
- `CHANGELOG.md`'s plan-98 and plan-99 entries mention auto mode as history.
- Ratified plans 98 and 99 carry auto-path text at their decisions. D6 lists the sites.

**F14 — The always-on rules this plan reads.**
- `src/CLAUDE.md` `### Always` item 17: *"Deciding it yourself — handed back or never asked — cover it unless you can name what the user would see differently without it"*, and *"Ask a present user about a surface you suspect but cannot evidence; deciding yourself, leave it an open question, never silently covered or excluded."*
- `### Never` item 7, at a run decision: *"ask the same question once more, and on a second such reply take the option the command names for that reply; where the command names none, end the turn having written nothing"*. And: *"A question the command does not classify decides what the run does."*

**F15 — The existing no-tool fallback.**
- specify: *"**Fallback**: when `AskUserQuestion` is not available (older runtime, headless mode, or tool not loaded), use a numbered markdown list with one question per item."*, then *"End the turn after presenting the question(s)."*
- plan PHASE 3's interactive bullet: *"(or fallback to numbered markdown list)"*.
- breakdown names no fallback at its escalations.

**F16 — The specify state loader tolerates unknown keys.** `_specify/_state.py` `_load_state` returns `json.loads(...)` with no key validation, and `_state_transaction` writes the whole dict back. A key no code reads therefore persists, inert, across every transaction.

#### Item 3

**F17 — PHASE 2.5 step 4.**
- The text: *"Check the reverse: does the plan's File Impact list files NOT in the spec's Affected Areas? If yes, note them as additions discovered during planning (add to the plan's File Impact table with a note)."* A file serving a user-facing surface that the spec neither covers nor excludes passes through it, and sub-question 6's uncovered-surface escalation never runs.
- `plan/main.md` carries no identity-evidence definition. Under `src/`, the term appears only in `research/main.md` and `specify/main.md` (grep).
- `src/CLAUDE.md` item 17 carries the definition: *"A surface shows the feature the user named only on cited user-visible evidence — the same title, label or translation key, route, or tab or mode; shared or different code, requests or data are never evidence or a reason to exclude."*
- Both actors at `/devforge:plan` load it. Plan 97's OQ-1 records, from a `claude-code-guide` check, that a custom subagent loads every `CLAUDE.md` level the main conversation loads unless its definition sets `omitClaudeMd`. `omitClaudeMd` has zero hits under `src/` and `scripts/`.
- ⚠ Bound, in plan 87's vendor words: `CLAUDE.md` is *"context, not enforced configuration"*. An install older than plan 99 carries no item 17.

#### Item 4

**F18 — Step 5.1's summary and what it omits.**
- `_specify/_render.py` `_approval_summary` prints four bullets, plus a conditional `- **Defaults applied**:` block between `**Acceptance criteria**:` and `**Out of scope**:`. Its entries read `  - **<DP-id>**: <description> → default: <value>`, with the delegation suffix when present.
- It lists no `deferred_open_question` decision point and no Risk. §8 renders such a decision point as `- **<DP-id>** [deferred to open question]: <description> (<reason>)`. Step 5.4's `_plan_handoff_block` counts both kinds and names neither.
- Three other sites describe the summary's shape: `_cmds_phase5.py`'s `render-summary` docstring (*"4 bullets, plus a conditional"*), `_cli.py`'s `render-summary` help (*"4 bullets, plus a conditional"*), and specify Step 5.1 (*"four bullets, plus a `**Defaults applied**:` bullet between the acceptance-criteria and out-of-scope bullets"*).
- A `deferred_open_question` reason is one of three: the model's `deferred by the model — why it may be the same feature: …` (specify step 2); a user's punt, in free text; or `exceeded follow-up cap` (`DP_TURN_CAP_REASON`, the three-follow-up cap's automatic transition).

#### Item 5

**F19 — Bundling and rounds in specify.**
- The per-decision-point protocol: *"**Bundling**: when ≥4 related questions exist AND they are NOT conditionally dependent on each other, bundle them into a single `AskUserQuestion` call (the tool supports multiple questions per call) so the user submits once."*
- `### Question rounds`: *"Up to 5 questions per round."*; *"After each round, decide if more clarification is needed based on **whether all decision points have been covered, not on subjective sufficiency**."*; and *"Decision points about separate surfaces are related, and none is conditionally dependent on another, so they qualify for the bundling rule in the per-decision-point protocol, which puts qualifying questions in one `AskUserQuestion` call."*
- Plan 99's OQ-4 ratified *"one decision point per uncovered surface, bundled per call"*.
- **The gap.** Below the threshold, two or three surface questions may each take their own call. At five, *"a single `AskUserQuestion` call"* cannot hold them under F8's limit, and neither can a 5-question round.
- The per-decision-point cap of 3 follow-ups is helper-enforced (`DP_TURN_CAP_REASON`).

#### Item 6

**F20 — Check 12b's wording.**
- `src/devforge/lib/_research/_cmds_render_verify.py` has three sites: the verify docstring's check-12 entry (*"(Phase 2.4 must probe the runner-up frame)"*), the comment above the check (*"so Phase 2.4 probed the runner-up frame"*), and the violation message (*"Phase 2.4 must probe the runner-up frame with at least one finding (record-finding --framing runner-up ...)"*).
- `research/main.md`'s `**Downstream impact.**` paragraph names `Phase 2.4 / 2.4b / 2.4c / 2.4e` findings as the ones tagged `--framing runner-up`. Phase 2.4d records only `--framing "primary"`.
- In `tests/lib/test_research_helper.py`, `TestVerifyCheck12`'s 12b test asserts only `runner_up_framing` and `runner-up`. No test contains `probe the runner-up`.
- Plan 99's residual 6 records the message as incomplete, not falsified.

#### The checkout

**F21 — Concurrency.** Another session may be building in this checkout at any time (plan 99's F12 rule). Before touching any ledger, re-read `git status` and read the ledger live. Commit by explicit path, never `git add -A`.

---

## Item → decision map

| Item | Plan 99 residual | Decisions | Phases |
|---|---|---|---|
| 1 — the AC-conflict route and the escalation map | 1 | D7, D8, D9, D10 | 3b, 3c |
| 2 — questions asked in auto mode, scope (c) | 2 | D1–D6; OQ-1, OQ-2, OQ-3, OQ-5 | 1a, 3a, 3b, 3c, 4 |
| 3 — the PHASE 2.5 step 4 seam | 3 | D11 | 3b |
| 4 — deferrals visible at spec approval | 4 | D12 | 1b, 3a, 4 |
| 5 — rounds and bundling | 5 | D13; OQ-4 | 3a |
| 6 — check 12b's message | 6 | D14 | 2 |

---

## Decisions to ratify

Nothing below is ratified. **(Drafting-time text, kept as drafted — Phase 0 CLOSED 2026-09-20, every item ratified as recommended; see `## Phase 0 close record`.)** Each item states the decision, a recommendation, and the strongest counter-argument, recorded rather than answered away. Proposed emitted wording is **substance, not final text**: the builder may reword, but every element named must survive. No emitted sentence may name plan vocabulary ("D3", "plan 100", "Phase 0", "item 2").

### D1 — Item 2: what auto mode still changes in the three commands — NOTHING

No branch of `/devforge:specify`, `/devforge:plan` or `/devforge:breakdown` depends on auto mode — neither on Claude Code's permission mode nor on the framework's own signals (F10).

- **(a) specify, markdown.**
  - Delete `### Mode detection`, including its uncertain-mode line, and the per-decision-point protocol's **Auto path** block.
  - The **Interactive path** heading goes too, *"(mode=`interactive`)"* included: with one path left, the protocol needs no path label, and that block's content becomes step 2's body.
  - Step 2's intro loses *"auto path vs interactive path"*, *"Every wrong-mode call is a hard helper gate (exit 2)"* and *"The orchestrator picks the setter that matches the mode `detect-mode` persisted in state"*, and quotes the ONE remaining gate message from (c) byte-for-byte.
- **(b) specify, Python (F11).** Delete:
  - the `detect-mode` verb, with `--auto` and `--reminder-text`;
  - `detect_mode()` and `cmd_detect_mode`;
  - `AUTO_MODE_ENV_VAR` and `AUTO_MODE_REMINDER_SUBSTRINGS`, and their facade re-exports;
  - `"mode"` in `default_state()`, and the `summary` verb's `"mode"` output key;
  - both mode gates.
  - Dead code goes by constitution §3.5 (*"**No dead code.**"*).
- **(c) `set-dp-default-applied` requires `--delegated-reply` on every call.** This is today's interactive gate, made mode-independent, so every `[default applied]` carries the reply that delegated it.
  - Enforced helper-side, with a named exit-2 message that names `--delegated-reply` and `set-dp-answer` — not through argparse `required=True`, whose generic message the command spec could not quote usefully. The message names no mode: no `mode=` token, no "auto" or "interactive".
  - `set-dp-answer` loses its mode gate and nothing else.
  - ⚠ This also closes a pre-existing hole: while `mode` is `None`, no gate fires today (F11), so a default can be recorded with no reply.
- **(d) plan PHASE 3 and breakdown PHASE 4.** Each block's three mode bullets collapse into ONE mode-independent bullet, and the *"**Mode-dependent execution path**"* lead-in goes with them.
  - **plan:** the interactive bullet survives, without its mode qualifiers: its *"**If auto mode is NOT active** (interactive mode, default):"* lead and its *"Do not silently apply defaults in interactive mode."* both go. It defines "Decision Points Resolved" in place — today it defines it only by reference (*"exactly as auto mode does"*). It carries D2's ask sentence and D9's exclusion. What happens to the spec's own `[default applied]` entries is OQ-2.
  - **breakdown:** the interactive bullet survives (decision points resolve in the Phase 2 architect consultation), without its *"**If auto mode is NOT active** (interactive mode, default):"* lead. It carries D2's ask sentence and points to D10's escalation sentence. The auto bullet's *"Apply the model's recommended defaults to any boundary the plan left open"* has no successor: a boundary the architect cannot resolve is an escalation (D10).

**Why.** (c) is the literal reading of the directive and the maintainer's explicit pick (F7). An auto branch left anywhere in the three commands is an ask-free path the pick removed. Auto mode is the built-in starting mode on Pro, Max and Team plans (F8), so a branch keyed on it is plausibly the common path. That last point is bounded: whether the harness emits the `<system-reminder>` plan and breakdown look for is undocumented, and the one observation of such text (F8) is not a vendor statement.

**Rejected alternative:** keep `detect-mode` and `--auto` accepted but ignored. A flag that silently does nothing is an escape hatch and dead code. A caller passing the removed verb now gets argparse's exit 2 — the intended loud failure.

**RECOMMEND D1 as stated.**

**Counter-argument, recorded:** it removes a documented framework contract (`--auto`, `DEVFORGE_AUTO_MODE`). No user was found in the repo (F11), but an operator script outside the repo is invisible to a grep. An unattended auto-mode run now stops at its first question; that is the directive's cost, and nothing in this plan restores an unattended path. And it sets the three commands against the vendor's documented nudge (F8), which D2 answers with prose only.

### D2 — Item 2: an explicit ask sentence in each of the three commands

Removing the auto branches is NOT enough. Auto mode nudges Claude away from clarifying questions, *"though Claude still asks when your prompt or a skill explicitly relies on it"* (F8). Each command therefore states, once, that it relies on its questions and asks them when Claude Code's auto mode is on.

- **Sites:**
  - specify: the Phase 2 intro, whose *"either ask clarifying questions (interactive mode) or apply named defaults (auto mode)"* becomes the ask sentence, both mode qualifiers gone;
  - plan: PHASE 3's collapsed bullet, naming Phase 1.3's escalations beside PHASE 3's own decision points;
  - breakdown: PHASE 4's collapsed bullet, with D10's escalation sentence carrying the same clause.
  - That is four sites — specify's Phase 2 intro, plan's PHASE 3 bullet, breakdown's PHASE 4 bullet and breakdown's PHASE 2 escalation sentence — and no others. OQ-5 adds no site: if ratified, the approval question is named inside the same sentence.
- **Wording constraint:** it names Claude Code's auto mode as the harness mode it is, and names no framework signal — none remains after D1. It uses the words "auto mode" and none of the other terms Phase 3's mode-vocabulary grep lists, so the four ask sentences are that grep's only allowed survivors.
- **OQ-5** decides whether the sentence also names the approval question.

**RECOMMEND D2 as stated.**

**Counter-argument, recorded:** a sentence is model judgment set against a documented harness nudge. Only specify has a mechanical backstop, and it is partial.
- `set-dp-default-applied` refuses a default with no reply (D1(c)) — but the reply it requires is itself text the model passes, so the requirement forces a quoted reply to exist, not to be real.
- `set-dp-answer` cannot tell a real answer from a fabricated one.
- `set-dp-deferral` takes no reply at all (OQ-3).
- plan and breakdown have no backstop.

### D3 — Item 2: when `AskUserQuestion` is not available

`dontAsk` mode denies the tool, and `claude -p --permission-prompts none` removes it (F8).

- **RECOMMEND the existing fallback** — a numbered markdown list, then end the turn (F15). No new path.
  - specify: its fallback trigger names a call the permission mode denies, beside *"older runtime, headless mode, or tool not loaded"*. One clause, because a denied call does not obviously read as "not available".
  - plan: PHASE 3's bullet already names the fallback; D7's conflict route names it too.
  - breakdown: D10's sentence names it.

**Counter-argument, recorded:** in a `-p` run, the run simply ends with the questions printed. Continuing is on the user, and nothing here tells a calling script that the run stopped for questions.

### D4 — Item 2: a standing instruction in the user's prompt ("don't ask, decide yourself")

Today plan and breakdown treat *"explicit user instruction to operate autonomously"* as an auto signal; specify does not (F10).

- **RECOMMEND:** a standing instruction does not replace a question — ask anyway, in all three commands. A reply that delegates the question then takes the delegated path.
- **Why.** `--delegated-reply` carries *"the user's reply, verbatim"* to the question asked (specify step 2). A prompt-level instruction precedes every question and names none of its options. Recording it as the delegation of a particular decision point would attribute to the user a choice about a question they never saw.
- **Rejected alternative, recorded:** treat the standing instruction as a delegation of every later question.
- ⚠ **This is a ratification choice**, not a consequence of (c). (c) says which commands ask; it does not say how a prompt-level instruction reads.

**Counter-argument, recorded:** friction for a user who said it up front — they now answer every round with "you decide".

### D5 — Item 2: `src/CLAUDE.md` `### Always` item 17 — NO edit

- **RECOMMEND no edit, with this reading recorded here.** "A present user" (F14) means a user a command's question can reach.
  - After D1, the three commands ask every scope decision point, so "never asked" no longer occurs inside them.
  - Item 17's "never asked" arm still governs the commands that decide without asking: research's Step 2b classification, `/devforge:implement`, `/devforge:fix`, `/devforge:review` and `/devforge:verify`.
  - The command-scoped rule is the more specific one.
- `src/CLAUDE.md` stays byte-identical; Phase 3's Verify checks it.

**Counter-argument, recorded:** an always-on sentence whose "present" can be read against the command rule — for example, a user who delegated at intake read as "not present". Rewording it to "the user" would widen asking into `/devforge:research` and `/devforge:discover`, which (c) did not pick. Item 17 is also already the longest item in either list, at 152 words.

### D6 — Item 2: downstream wording that assumes an auto path

Rewritten delegated-only in the same phase as the behavior it describes — Phase 1 for Python, Phase 3 for command markdown.

- **`specify/main.md` (F9):** the delegated paragraph's *"exactly as an auto-mode default does"*; *"On the auto path and the delegated path alike"*; *"In interactive mode, a surface with no identity evidence is still asked … when the user hands it back or when no question is asked"*; step 3's *"(either mode)"* and *"(or auto-mode rationale)"*; step 3's two surface bullets; `### Question rounds`' *"in interactive mode"*; the stop rule; Step 4.5's *"an auto-mode default"*; Step 4.7's source 3; Step 5.1's *"auto-mode defaults and delegated ones alike"*.
- **`plan/main.md`:** the `**Defaults applied**:` bracket's *"whether applied in auto mode or on a decision point the user handed back to you"*.
- **Python (F11):** `_approval_summary`'s *"auto-applied and delegated alike"*; the help texts of `set-dp-answer`, `set-dp-default-applied` and `--delegated-reply`; the two setters' docstrings.
- **Ratified plans 98 and 99 get DATED NOTES only; their text is never rewritten.**
  - **The rule for where a note goes:** wherever the text still steers future work — a decision, a residual, a trap, a non-goal, an unrun e2e anchor. No note where the text records the tree as of a date (a numbered fact) or a completed build (a build record, a built phase's instructions).
  - **Known plan-99 sites:**
    - D4(b), *"on the auto path and on the delegated path alike"*, and its sub-bullets;
    - D4(d)'s counter-argument, *"In auto mode every §6 entry carries the marker"*;
    - D10's P2, *"(delegated or auto path)"*, and its **Amends** list, *"(or auto-mode rationale)"*;
    - Trap 7;
    - `## Residuals` — every item is taken up here, so one note under the section intro;
    - the Phase 3 anchors that run *"in delegated or auto mode"*.
  - **Known plan-98 sites:** D3's table rows for specify (*"auto mode byte-unchanged"*) and plan (*"exactly as auto mode lists it"*); D6 (*"auto and delegated alike"*); `## Non-goals` (*"**Auto-mode semantics.** Unchanged"*).
  - The builder re-greps both files for `auto` and records each hit as a note or as a history site under the rule above.

**RECOMMEND D6 as stated.**

**Counter-argument, recorded:** dated notes pile up, and plans 98 and 99 then read correctly only with their notes. The alternative, rewriting ratified text, is a Non-goal: it would erase what was ratified.

### D7 — Item 1: the AC-conflict route lives in `plan/main.md` Phase 1.3

- **Placement.** A paragraph directly after sub-question 12, before *"**Use the carried caller enumeration (do not re-derive it):**"* — the list where sub-question 6's arms live.
  - The Rule 5 note keeps its prohibitions and replaces its inline routing clause with a pointer to that paragraph.
  - `architect.md` gains NO arm: the architect never receives the user's reply (F6), and Rule 9's sentence (F2) stays byte-identical.
- **The route** (substance):
  1. Surface the escalation via `AskUserQuestion` (or the numbered-list fallback), naming both acceptance criteria and the identical tuple. The options are the two criteria's outcomes: the behavior changes at both sites, or it stays at both. An identical tuple is one caller population, so no third option splits them.
  2. `/devforge:plan` writes no acceptance criterion into `spec.md` (F3), so **every outcome needs a spec revision.**
     - **On an answer:** tell the user that resolving the conflict needs a spec revision, and add a Risk Assessment row: *"<AC-X> and <AC-Y> require opposite outcomes for the identical reachable tuple <tuple> — the user chose <outcome>; resolving it needs a spec revision"*.
     - **On a reply that decides nothing:** ask once more; on a second such reply, add the row *"… — left unresolved; the user did not decide it; resolving it needs a spec revision"*, and tell the user.
  3. **In both cases, NO Key Design Decision picks a side,** and the conflicting behavior change stays undesigned.
  4. **PHASE 2.5 step 3 then finds both criteria without an implementation path — and takes NEITHER of its arms for them.** One new clause in step 3 says so, for any acceptance criterion the Phase 1.3 conflict route has already recorded, and points to that route's combined Risk row instead.
     - The first arm (*"Revise the plan to add the missing coverage."*) would pick a side.
     - The second arm, the generic *"AC-[N] has no clear implementation path — requires clarification during breakdown"* row, would add two more rows for one conflict and name the wrong remedy: the fix is a spec revision, not clarification during breakdown.
     - **Result: exactly ONE Risk Assessment row per conflict** — the combined row from point 2.
- **The mirror** is sub-question 6's uncovered-surface arm (F3), where a "cover" answer also needs a spec revision and the plan does not design the surface.

**RECOMMEND D7 as stated.**

**Counter-argument, recorded:** the user answers and the plan still does not follow the answer — the answer is spent on a Risk row. Both alternatives cost more:
- **(i) Design per the user's pick.** The losing criterion then fails at `/devforge:verify` until the spec is revised, and the plan contradicts the spec it was built from.
- **(ii) Stop the run.** Item 7's no-write arm leaves no visible record, and a re-run meets the same conflict.

### D8 — Item 1: a conditional `**AC conflicts**:` line in PHASE 3's approval summary

- **The line** (substance), placed directly after `**Unconfirmed exclusions**:`: *[include this line ONLY if ≥1 acceptance-criteria conflict was surfaced by Phase 1.3's conflict route: list each by its two criteria and the shared tuple, with the user's chosen outcome or "not decided by the user", and say that each needs a spec revision; omit the entire line when none]*.
- **A new line, not a widening of `**Unconfirmed exclusions**:`.** That line's definition covers sub-question 6's non-decisions only, and answered conflicts must be listed too.

**RECOMMEND D8 as stated.**

**Counter-argument, recorded:** a ninth conditional line (eight today, F3), against the review-fatigue concern plan 96 grew from.

### D9 — Item 1: reading (a) excluded

The collapsed PHASE 3 bullet (D1(d)) states that an acceptance-criteria conflict is NOT one of the *"decision points the spec didn't resolve"*. It takes Phase 1.3's conflict route, and the model never supplies the winning criterion as a `[default applied]` answer — including on a hand-back. This ratifies the frame's item-1 recommendation. Under (c) there is no auto half left to settle.

**RECOMMEND D9 as stated.**

**Counter-argument, recorded:** a user who genuinely wants the model to pick the winner cannot hand it back; they must revise the spec themselves. That is the cost of keeping a product decision the spec contradicts out of the model's hands.

### D10 — Item 1: every escalation and its route

**The architect's escalations at `/devforge:plan`** (F2, F3):

| Escalation (source) | Orchestrator route | Arm for a reply that decides nothing |
|---|---|---|
| Rule 9 Out-of-scope-respect step, §6 direction | sub-question 6, §6 arm | the §6 exclusion stands; listed on `**Unconfirmed exclusions**:` (plans 98 and 99) |
| `### How to consult` step 1 → the Out-of-scope-respect step | the same | the same |
| PHASE 2.5 step 6 → re-enters Phase 1.3 | the same | the same |
| Rule 9 Out-of-scope-respect step, uncovered-surface direction | sub-question 6, surface arm | the surface stays uncovered; a Risk row and `**Unconfirmed exclusions**:` (plan 99) |
| Rule 9 rejected-alternative checkability step — the AC conflict | Phase 1.3's conflict route (D7) | a "left unresolved" Risk row and `**AC conflicts**:` (D7, D8) |
| Rule 6 / the Termination rule — generic "spec-level ambiguity" | PHASE 3's clarifying-question bullet | a content answer: `[default applied]`, listed under Decision Points Resolved and on `**Defaults applied**:` — kept |

⚠ Recorded, not changed: the generic route's bullet sits in PHASE 3 and says *"before writing"*, but PHASE 2 has already written `plan.md` by then, and the escalation it receives arises in Phase 1.3.

**breakdown's three escalations (F5): RECOMMEND one shared sentence** in PHASE 2, directly before its **Halt rule:** paragraph.
- **Substance:** every escalation to the human in PHASE 2 — a plan-level decision sub-question 4 finds missing, a task that cannot be split, an implementer this project does not generate — is asked via `AskUserQuestion` (or the numbered-list fallback), naming what is unresolved. D2's ask clause applies. A reply that decides nothing is asked once more; on a second such reply, end the turn having written no task file, naming what stays unresolved.
- **The three sites and their three restatements stay byte-identical.**
- ⚠ **"Written no task file", not "written nothing".** PHASE 0b may already have flipped `plan.md` to Approved (F5), and that flip stays — implicit approval by invocation, kept by plan 98's D5.
- **Why a sentence at all:** item 7 already implies re-ask-then-no-write for an unclassified question (F14). The sentence names the arm, so no reading is left open.

**RECOMMEND D10 as stated.**

**Counter-argument, recorded:** the breakdown sentence adds nothing mechanical and largely restates item 7.

### D11 — Item 3: PHASE 2.5 step 4 routes a surface-serving file to sub-question 6

- **Recognition — the frame's option 4: rely on item 17 and restate nothing.** Step 4 names "a file that serves a user-facing surface showing the feature the spec names" and leaves the identity test to item 17 (F17), which both actors at `/devforge:plan` load.
- **The route.** Such a file, serving a surface the spec neither covers nor excludes, is not an addition discovered during planning.
  - Re-enter Phase 1.3 and take sub-question 6's opposite-direction escalation for its surface — the shape steps 6–8 use.
  - The file stays out of File Impact unless a Key Design Decision inside the spec's scope needs it, because that route does not design the surface into the plan.
  - Every other addition keeps today's note.

**RECOMMEND D11 as stated.**

**Counter-argument, recorded:** item 17 is *"context, not enforced configuration"*, and an install older than plan 99 lacks it (F17) — there, step 4 has no identity test at all. The frame's options 1 and 2 (restate the definition, or point to it) make step 4 self-contained, at the cost of a duplicate definition that can drift from item 17's.

### D12 — Item 4: a conditional `**Deferred to open questions**:` bullet at Step 5.1

- **The bullet.** Rendered by `_approval_summary` between `**Defaults applied**:` and `**Out of scope**:`, and omitted when there are none: `- **Deferred to open questions**:`, with one entry per `deferred_open_question` decision point — `  - **<DP-id>**: <description> (<reason>)`, mirroring the §8 line (F18).
- **Which set: EVERY `deferred_open_question` decision point**, not model deferrals only. The model-only set would make the free-text prefix `deferred by the model` load-bearing, and the reason text already shows who deferred (F18).
- **Python (Phase 1b):** `_approval_summary` and its docstring, `_cmds_phase5.py`'s `render-summary` docstring, `_cli.py`'s `render-summary` help; tests. **Docs (Phase 3a):** Step 5.1's shape sentence, and the paragraph after its code block.
- **Its retirement duty — the frame's eight-site D10-cost inventory, carried over.** Every record of D10's cost changes in ONE commit, Phase 4's, by file type. The frame asked for the same commit as the bullet; this plan puts it in Phase 4 instead, because Phase 1b is a python-engineer commit and these are markdown edits on the instruction-author route. Between Phase 1b and Phase 4 the records below are knowingly stale.
  - **`99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md`** — a dated note at each of three sites: D10's recorded cost (*"a §8 deferral is not listed in specify's Step 5.1 summary"*), `## Residuals` item 4 (*"A model's no-evidence deferral is not visible at spec approval."*), and Trap 7's D10 amendment (*"which Step 5.1 does not list — the cost D10 records"*).
  - **Ledgers, amended because ledger lines state current state:** the repo `CLAUDE.md`'s plan-99 index line (*"specify's Step 5.1 does NOT list §8 deferrals"*), and `PLAN-STATUS-ARCHIVE.md`'s plan-99 entry (*"lists defaults and §6 but not §8 deferrals"*, *"summary lists neither §8 deferrals nor Risks"*, *"Specify's Step 5.1 does not list §8 deferrals."*).
  - **`CHANGELOG.md`** — a new entry under `## [Unreleased]`. Plan 99's entry (*"but NOT §8 deferrals"*) is history and is not rewritten.
  - ⚠ **Risks stay unlisted at Step 5.1.** An amendment to *"neither §8 deferrals nor Risks"* keeps its Risks half.
  - This inventory is as of 2026-09-19. Before building, re-grep `Step 5.1`, `§8 deferral` and `visible at spec approval`; a new site takes its file type's rule.

**RECOMMEND D12 as stated.**

**Counter-argument, recorded:** a user's own punt is listed back to them, which is noise — and every summary a user approves may grow by one more bullet.

### D13 — Item 5: a round is one call; independent questions are always bundled

- **A round is ONE `AskUserQuestion` call,** holding as many questions as one call accepts — 4 today (F8). *"Up to 5 questions per round."* is replaced to match.
- **The emitted text names the call's capacity, never the literal 4,** because a literal goes stale when the vendor limit changes. The numbered-list fallback's count is OQ-4.
- **No total cap.** Rounds continue until every decision point is covered, as `### Question rounds` already says (F19). The per-decision-point cap of 3 follow-ups stays.
- **The ≥4 threshold is dropped.** Independent questions are always bundled, up to one call's capacity; conditionally dependent ones are not. The priority order (*"scope > breaking changes > data flow > tooling > UX > edge cases"*) decides which go first. `### Question rounds`' surface sentence then reads "in as few calls as the tool allows".
- **Recorded separately:** the maintainer's 2026-09-19 input (English paraphrase) — more questions are acceptable, and a reasonable per-round limit is wanted. This decision is the proposed answer to that input.

**RECOMMEND D13 as stated.**

**Counter-argument, recorded:** it is wider than plan 99's residual 5, which named surface questions only — it changes specify's general round and bundling rules. And one call's capacity is a vendor number documented on the Agent SDK page, not in the CLI docs (F8).

### D14 — Item 6: check 12b names the phase family

- The message, the docstring's check-12 entry and the comment above the check name `Phase 2.4 / 2.4b / 2.4c / 2.4e`, as `research/main.md`'s `**Downstream impact.**` paragraph does (F20). Naming 2.4e alone would imply that 2.4b and 2.4c findings do not count.
- A test assertion pins `2.4e` in check 12b's stderr (house rule: every change is tested).
- Check numbering is unchanged, and no check is added.

**RECOMMEND D14 as stated.**

**Counter-argument, recorded:** a test that pins wording is brittle. Accepted, because nothing else pins this message.

### OQ-1 — The stale `"mode"` key in an in-flight `specify-state.json`

After Phase 1 no code reads `mode`, and the loader keeps an unknown key (F16), so an in-flight state carries it, inert.
- **RECOMMEND leave it.** Stripping it adds a migration branch for a transitional state.
- **Alternative:** drop it in `_load_state`.
- **Recorded either way:** a session that loaded the old `specify/main.md` before an update and calls `detect-mode` after it gets argparse's exit 2 — D1's intended loud failure.

### OQ-2 — A spec's `[default applied]` entries recorded before this change

A spec written in auto mode before this change carries `default_applied` decision points with no delegation: nobody was asked.
- **RECOMMEND:** `/devforge:plan` carries them as the spec's resolved values and does not re-ask them. They are the spec's decisions, already listed at that spec's Step 5.1 (without a delegation suffix, F11), and the plan edits no spec decision.
- **Alternative:** the plan re-asks each one as a PHASE 3 decision point.
- Recorded as a transitional bound either way.

### OQ-3 — The model's `open_question` deferral takes no reply

`set-dp-deferral` has no `--delegated-reply`. A model deferral — specify step 2's no-evidence surface route — therefore needs no user reply mechanically, unlike a default (D1(c)).
- **RECOMMEND not built here.** Recorded as a named strengthening arm: a model-deferral flag on `set-dp-deferral` that requires `--delegated-reply`. **Trigger:** an observed model deferral recorded without a question having been asked. D12's bullet makes every such deferral visible at approval, which is the cheaper net.
- **Alternative:** build it in Phase 1a.

### OQ-4 — The numbered-list fallback's count per round

Without the tool loaded, no schema tells the model one call's capacity (F15), so D13's "as many as one call accepts" cannot be read there.
- **RECOMMEND the fallback states a literal 4** — the one place the literal appears in emitted text. If the vendor limit changes, the fallback's count merely differs from the tool's, since a list is not a tool call.
- **Alternative:** the fallback lists every pending question, in priority order, in one round.

### OQ-5 — Does D2's ask sentence also name the approval question?

- **RECOMMEND yes.** Each command's approval question (`"Approve this spec?"`, `"Approve this plan?"`, `"Approve this breakdown?"`) has no auto branch today, but the same harness nudge (F8) applies to it, and naming it costs a clause.
- **Counter:** it widens the sentence past the directive's "clarifying questions", onto gates that were never auto-branched.

---

## Phase 0 close record

**CLOSED 2026-09-20.** Every decision (D1–D14) and every open question (OQ-1–OQ-5) is **ratified as recommended**. Nothing was amended, nothing was declined, no item is left open, and build phases may start.

Every statement in this record is dated 2026-09-20 unless it names another date.

**How it closed — 2026-09-20.**

- A **single blanket maintainer directive**, given in the maintainer's own words. English paraphrase: *"I ratify everything as recommended."*
- **No per-item deliberation was supplied, and this record says so.** The precedent is plans 91, 92, 94, 95, 96, 97 and 98, whose close records state the same.
- **It is a PICK, not a delegation** (plan 98's D1 distinction): an explicit statement naming the outcome, not a reply that handed the decision back.
- **Item 2's scope was picked separately on 2026-09-19**, through `AskUserQuestion`: option (c), the one the tool labelled `(Recommended)` (F7). That is also a pick, not a delegation. It fixed WHICH commands ask; **this close ratifies D1–D6 themselves.**
- **The three `claude-code-guide` checks the frame owed were run on 2026-09-19 and are discharged**, their results recorded at F8 (`## Expansion note`, item 2). **None is still owed.**
- **Every decision keeps its counter-argument.** Nothing under `## Decisions to ratify` is deleted, shortened or answered away by this close, because **a ratified decision with its counter-argument deleted cannot be re-opened honestly.** That section's drafting-time lead-in **keeps its original opening sentence**, *"Nothing below is ratified."*, with a dated pointer beside it naming this close — the pre-close text is preserved as the record of the pre-close state, the pattern `84-ARCHITECT-CONSULT-ACCUMULATION-PLAN.md` argues under **Reading the pre-close text**. The decisions' own text stays as drafted, counter-arguments and recorded rejected alternatives included.

### Outcomes — 2026-09-20

| Item | Outcome (2026-09-20) | What it settles |
|---|---|---|
| D1 | Ratified as recommended | Auto mode changes NOTHING in the three commands: specify's `### Mode detection`, its **Auto path** / **Interactive path** labels and its auto-mode Python all go, plan's and breakdown's three mode bullets collapse into one, and `set-dp-default-applied` requires `--delegated-reply` on every call. |
| D2 | Ratified as recommended | Four ask sentences and no others — specify's Phase 2 intro, plan's PHASE 3 bullet, breakdown's PHASE 4 bullet, breakdown's PHASE 2 escalation sentence — each naming Claude Code's auto mode and no framework signal. |
| D3 | Ratified as recommended | The existing numbered-list fallback covers a denied or removed `AskUserQuestion`; no new path. |
| D4 | Ratified as recommended | A standing "decide yourself" instruction does not replace a question: ask anyway in all three commands, and a reply that delegates then takes the delegated path. |
| D5 | Ratified as recommended | `src/CLAUDE.md` `### Always` item 17 gets NO edit and stays byte-identical. |
| D6 | Ratified as recommended | Downstream auto-path wording is rewritten delegated-only in the phase that changes the behavior it describes; plans 98 and 99 get dated notes only, never rewritten text. |
| D7 | Ratified as recommended | The AC-conflict route is a paragraph in `plan/main.md` Phase 1.3 after sub-question 12; the Rule 5 note keeps its prohibitions and points to it; `architect.md` gains no arm; exactly ONE Risk Assessment row per conflict, and no Key Design Decision picks a side. |
| D8 | Ratified as recommended | A conditional `**AC conflicts**:` line directly after `**Unconfirmed exclusions**:` in PHASE 3's approval summary — a ninth conditional line, not a widening of that one. |
| D9 | Ratified as recommended | Reading (a) is excluded: an acceptance-criteria conflict is never one of PHASE 3's *"decision points the spec didn't resolve"* and never becomes a `[default applied]` answer, hand-back included. |
| D10 | Ratified as recommended | The architect-escalation map stands as tabled, and breakdown gets ONE shared escalation sentence before PHASE 2's **Halt rule:** paragraph; its three escalation sites and their three restatements stay byte-identical. |
| D11 | Ratified as recommended | PHASE 2.5 step 4 routes a file serving a user-facing surface the spec neither covers nor excludes to sub-question 6 instead of noting it as an addition; recognition rests on `src/CLAUDE.md` item 17 and restates nothing. |
| D12 | Ratified as recommended | A conditional `**Deferred to open questions**:` bullet at Step 5.1 covering EVERY `deferred_open_question` decision point, with its eight-site retirement duty run in Phase 4. |
| D13 | Ratified as recommended | A round is ONE `AskUserQuestion` call; independent questions are always bundled; the ≥4 threshold is dropped and *"Up to 5 questions per round."* is replaced to match; emitted text names the call's capacity, never the literal. |
| D14 | Ratified as recommended | Check 12b's message, the docstring's check-12 entry and the comment above the check all name `Phase 2.4 / 2.4b / 2.4c / 2.4e`; a test pins `2.4e`; no check is added or renumbered. |
| OQ-1 | Ratified as recommended — **leave it** | The stale `"mode"` key in an in-flight `specify-state.json` stays, inert. **`_load_state` gets NO migration branch.** |
| OQ-2 | Ratified as recommended | `/devforge:plan` carries a pre-change spec's `[default applied]` entries as that spec's resolved values and does not re-ask them; recorded as a transitional bound. |
| OQ-3 | Ratified as recommended — **not built** | No reply requirement on `set-dp-deferral`. **Phase 1a does NOT touch `set-dp-deferral`.** The flag stays a named strengthening arm with its recorded trigger, and D12's bullet is the cheaper net. |
| OQ-4 | Ratified as recommended | The numbered-list fallback states a literal **4** — the ONE place that literal may appear in emitted text (Trap 7). |
| OQ-5 | Ratified as recommended — **yes** | D2's ask sentence in each of the three commands **also names that command's approval question**. It adds NO fifth site: the clause sits inside the same sentence. |

**What the outcomes put in scope — 2026-09-20.**

- **Phase 1a — `_specify/` Python.** D1(b)–(c) plus D6's Python sites. **OQ-1's "leave it" means `_load_state` gets no migration branch**, so its Verify bullet resolves to the first arm alone: `grep -rn '"mode"' src/devforge/lib/_specify` returns nothing, with no permitted surviving line. **OQ-3's "not built" means Phase 1a does NOT touch `set-dp-deferral`** — no flag, no reply requirement, no test for one — so `## Non-goals`' conditional clause resolves to the non-goal.
- **Phase 1b.** D12's Python only: `_specify/_render.py` (`_approval_summary` and its docstring), `_cmds_phase5.py`, `_cli.py`, and tests.
- **Phase 2.** D14 only: `src/devforge/lib/_research/_cmds_render_verify.py` and `tests/lib/test_research_helper.py`.
- **Phase 3a — `src/commands/specify/main.md`.** D1(a), D2, D3, D6's specify sites, D12's Step 5.1 docs, D13, OQ-4 and OQ-5.
- **Phase 3b — `src/commands/plan/main.md`.** D1(d), D2, D6's plan site, D7, D9, D11, OQ-5, and **D8's conditional `**AC conflicts**:` summary line**.
- **Phase 3c — `src/commands/breakdown/main.md`.** D1(d), D2, D3, OQ-5, and **D10's shared escalation sentence** before PHASE 2's **Halt rule:** paragraph.
- **Phase 3d.** `src/agents/architect.md` and `src/CLAUDE.md` stay byte-identical (D5, D7) — a verified no-op, with `git diff --stat` empty on both.
- **Phase 4.** D6's dated notes on plans 98 and 99, D12's eight-site retirement duty, and this plan's own ledger lines.

**What this record does NOT close — 2026-09-20.**

- **Nothing is built.** Phases 1–4 have not started, and **Phase 5 stays DEFERRED, user-driven and NOT run** — everything this plan ships is build-verified at best until it does.
- ⚠ **Ratification changes no evidence class:** NO incident. Items 1 and 3–6 are gaps found by reading during plan 99's build; item 2 is a maintainer directive; nothing was measured.

---

## Phases

### Phase 0 — Ratification

Every decision (D1–D14) and every OQ (OQ-1–OQ-5) gets an outcome in `## Phase 0 close record`: ratified, amended or declined.

#### Verify

- The record names **each** of D1–D14 and OQ-1–OQ-5 with its outcome. No item is silently omitted.
- The record states whether per-item deliberation was supplied, and whether the close was an explicit pick or a delegation (plan 98's D1 distinction).
- Each decision still carries its counter-argument. **A ratified decision with its counter-argument deleted cannot be re-opened honestly.**
- The record says which files the outcomes put in scope: D8 and D10 decide 3b's and 3c's summary and escalation edits; OQ-3 decides whether 1a touches `set-dp-deferral`; OQ-5 decides the ask sentence's reach.

### Phase 1 — Python, `_specify/`

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** Commit per sub-phase, by explicit path.

- **1a — item 2** (D1(b)–(c), D6's Python sites, and OQ-1 and OQ-3 as ratified).
  - Files: `_specify/_cli.py`, `_cmds_phase01.py`, `_cmds_phase2.py`, `_cmds_phase3.py`, `_schema.py`, `_state.py`, `_render.py` (docstring only), `src/devforge/lib/specify_helper.py`; `tests/lib/test_specify_helper.py`.
  - Test fixtures that seed a default through `DEVFORGE_AUTO_MODE=1` pass `--delegated-reply` instead.
  - A test that pins the no-suffix render of a `default_applied` entry (F12) seeds a pre-change state by writing its JSON directly. That shape still exists in in-flight states and in old specs.
- **1b — item 4** (D12's Python). Files: `_specify/_render.py` (`_approval_summary` and its docstring), `_cmds_phase5.py`, `_cli.py`; tests.
- **Order: 1a before 1b.** Both edit `_approval_summary`'s docstring and `_cli.py`.

#### Verify

- **Removal greps:**
  - **Source.** `grep -rni "detect_mode\|detect-mode\|auto_mode\|reminder_text\|reminder-text\|--auto\|auto path\|interactive path\|auto mode\|interactive mode\|mode=auto\|mode=interactive\|auto-applied" src/devforge/lib/_specify src/devforge/lib/specify_helper.py` returns nothing. The case-insensitive alternation also sees:
    - the `"detect-mode"` subparser and its `--auto` flag;
    - the help texts of `set-dp-answer`, `set-dp-default-applied` and `--delegated-reply`;
    - the two setters' docstrings and the old gate-message literals;
    - `_approval_summary`'s *"auto-applied and delegated alike"* (F11).
    - ⚠ A bare `auto` is deliberately NOT in the pattern: `_specify/` uses "auto-tag", "auto-discovers", "auto-fires" and similar for unrelated things.
  - **Tests.** `grep -n "AUTO_MODE\|detect_mode\|reminder_text\|reminder-text\|mode=auto\|mode=interactive" tests/lib/test_specify_helper.py` returns nothing. `grep -n "detect-mode" tests/lib/test_specify_helper.py` returns only the test that asserts the verb now exits 2.
  - **State key.** `grep -rn '"mode"' src/devforge/lib/_specify` returns nothing — or, if OQ-1 was ratified as "drop it in `_load_state`", exactly that one line.
  - `src/devforge/lib/_research/` has no diff from 1a (research's `detect-mode` is untouched).
- **Tested (1a):**
  - `specify_helper detect-mode` exits 2.
  - `set-dp-default-applied` without `--delegated-reply` exits 2 with the named message — on a state with no `mode` key, AND on states carrying `"mode": "auto"` and `"mode": "interactive"`. With the flag, it succeeds on all three.
  - `set-dp-answer` succeeds on a state carrying `"mode": "auto"`.
  - A pre-change `default_applied` entry with no `delegated_reply` still renders `[default applied]` with no suffix, in §8 and at Step 5.1.
  - The `summary` verb's output has no `mode` key.
- **Tested (1b):**
  - With ≥1 `deferred_open_question` decision point, the bullet sits between `**Defaults applied**:` and `**Out of scope**:` — or directly after `**Acceptance criteria**:` when no default exists — and lists a model deferral, a user punt and a follow-up-cap transition, each with its reason.
  - With none, the summary is byte-identical to before.
- The targeted suite, then the full `tests/lib` suite, is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — Python, `_research/`

**Route: python-engineer → python-reviewer.** Item 6 (D14): `src/devforge/lib/_research/_cmds_render_verify.py` and `tests/lib/test_research_helper.py`.

#### Verify

- `grep -n "Phase 2.4 / 2.4b / 2.4c / 2.4e" src/devforge/lib/_research/_cmds_render_verify.py` returns three lines: the docstring entry, the comment and the message.
- `TestVerifyCheck12`'s 12b test asserts `2.4e` in stderr and passes; `tests/lib/test_research_helper.py` is green.
- No check is added or renumbered: the docstring's check list keeps its numbers.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 3 — Instructions

**Route: instruction-author → instruction-reviewer, one dispatch per sub-phase, committing by explicit path.** Instruction-only: no `.py` file changes in this phase.

- **3a — `src/commands/specify/main.md`** (D1(a), D2, D3, D6's specify sites, D12's Step 5.1 docs, D13, OQ-4, OQ-5). **Needs Phase 1 first:** it quotes 1a's gate message and names 1b's bullet.
- **3b — `src/commands/plan/main.md`** (D1(d), D2, D6's plan site, D7, D8, D9, D11, OQ-5).
- **3c — `src/commands/breakdown/main.md`** (D1(d), D2, D3, D10, OQ-5).
- **3d — `src/agents/architect.md` and `src/CLAUDE.md`: verified untouched** (D5, D7).

#### Verify

- **Mode vocabulary:** `grep -rni "auto mode\|auto-mode\|auto path\|mode=auto\|DEVFORGE_AUTO_MODE\|detect-mode\|--auto\|operate autonomously\|system-reminder\|mode detection\|mode-dependent\|uncertain about mode\|interactive path\|interactive mode\|either mode\|wrong-mode" src/commands/specify src/commands/plan src/commands/breakdown` hits exactly D2's four ask sentences and nothing else: specify's Phase 2 intro, plan's PHASE 3 bullet, breakdown's PHASE 4 bullet and breakdown's PHASE 2 escalation sentence. Each of the four matches only on "auto mode".
  - The grep is case-insensitive (`-i`), so it sees `**Auto path**`, `### Mode detection`, `**Mode-dependent execution path**` and `**When uncertain about mode**`.
  - `interactive path` catches the `**Interactive path**` heading and *"auto vs interactive paths"*. `interactive mode` catches every *"(interactive mode, default)"* and *"in interactive mode"* D1 and D6 remove.
  - `either mode` (step 3's *"(either mode)"*) and `wrong-mode` (step 2's *"Every wrong-mode call"*) each occur once, on a line that also carries another listed term. They are in the pattern so a partial edit that removes only the other term on the line still shows.
  - ⚠ A bare `the mode` is deliberately NOT in the pattern, because it matches "the model".
  - Against the 2026-09-19 tree, every site F9 lists contains at least one term in this pattern.
- **specify:** step 2 quotes 1a's `set-dp-default-applied` message byte-identically and names no other gate message. The Python message is split across string literals, so join them before comparing.
- **plan:**
  - the conflict-route paragraph sits after sub-question 12, and the Rule 5 note points to it and keeps its prohibitions;
  - step 3 carries D7's clause, which suppresses BOTH of step 3's arms — the revise arm and the *"no clear implementation path"* Risk line — for a criterion the conflict route recorded, and points to that route's combined Risk row;
  - `**AC conflicts**:` sits after `**Unconfirmed exclusions**:`, with an omit rule;
  - the collapsed bullet carries D9's exclusion and defines "Decision Points Resolved" in place;
  - step 4 routes a surface-serving file (D11).
- **breakdown:** one shared escalation sentence sits before PHASE 2's **Halt rule:**, and the three escalation sites and three restatements (F5) are byte-identical.
- `git diff --stat src/agents/architect.md src/CLAUDE.md` is empty.
- No emitted text names plan vocabulary.
- The live-spec tests are green: `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py`, `tests/scripts/test_claude_emitter.py`.
- instruction-reviewer returns SHIP-READY for each sub-phase, or every finding is fixed.

### Phase 4 — Docs sweep

**Route: instruction-author → instruction-reviewer.** Docs only. Apply F21 before touching any ledger.

- **Plans 98 and 99:** dated notes per D6's rule, plus D12's three plan-99 D10-cost notes, plus one note under plan 99's `## Residuals` naming this plan as their owner.
- **`CHANGELOG.md`:** a new entry under `## [Unreleased]` — verified on 2026-09-19 to exist with `### Changed`; re-verify at build. The evidence class comes first and the honest bounds last.
- **`DEVELOPMENT-STATUS.md`:** the `specify.md` bullet's mode-detection clause and its stale *"4-bullet block"* (F13); and a `## Key Design Decisions` item, or a recorded verified no-op.
- **Repo `CLAUDE.md`:** the plan-99 index line's D10-cost clause (D12), and this plan's index line in the DONE shape.
- **`PLAN-STATUS-ARCHIVE.md`:** the plan-99 entry's three D10-cost phrases (D12, keeping the Risks half) and its auto-mode anchor phrases (D6's rule); and a new plan-100 entry.
- **The repo `CLAUDE.md` "Where to find what" router and `README.md`:** each an edit or a verified no-op.

#### Verify

- Every site above is recorded in a Phase 4 build record as an **edit or an explicit verified no-op**, with the grep that shows it.
- `grep -rn "Step 5.1 does not list\|Step 5.1 does NOT list\|not listed in specify's Step 5.1" --include=*.md .` returns only dated-noted sites, history, and this plan's own quotes of them.
- `100-SCOPE` greps in the repo `CLAUDE.md` and in `PLAN-STATUS-ARCHIVE.md`.
- No tracked file names a client, a client component or a benchmark path.

### Phase 5 — Consumer e2e — DEFERRED, user-driven HARD GATE, NOT run

**Everything above is build-verified at best, never consumer-validated, until this phase runs.**
- **Fixture:** a testForge20 feature (plan 99's OQ-5 precedent).
- **"Auto mode on"** means a Claude Code session in auto mode (`--permission-mode auto`, or the mode selector).
- **The frozen benchmark install is never touched.**

The anchors are known-answer cases, **scored in PAIRS**:

1. **Auto mode on → specify asks a `scope_boundaries` question** through `AskUserQuestion` rather than recording a default. **PAIRED WITH 2.**
2. **Auto mode on, and the user delegates that question →** §8 shows `[default applied]` with the delegation quoted, and Step 5.1's `**Defaults applied**:` lists it.
3. **An AC conflict, answered →** exactly ONE Risk row for the conflict, ending *"the user chose <outcome>; resolving it needs a spec revision"*, with no *"no clear implementation path"* row for either criterion; and `**AC conflicts**:` lists it. **PAIRED WITH 4.**
4. **The same conflict, delegated twice →** exactly ONE Risk row, saying the user did not decide it, with no *"no clear implementation path"* row for either criterion; and no Key Design Decision picks a side.
5. **A surface-serving file added at PHASE 2.5 →** routed to sub-question 6's surface escalation, not noted as an addition. **PAIRED WITH 6.**
6. **An ordinary added file →** today's note only.
7. **A model deferral at specify →** Step 5.1's `**Deferred to open questions**:` lists it with its reason. **PAIRED WITH 8.**
8. **No deferral →** the bullet is absent.

#### Verify

- Every anchor is scored **explicitly** — stated, not summarized — with each pair scored together.
- **If an anchor fails,** record the negative with the artifacts and name the mechanism before proposing any fix. A question skipped in auto mode is a D2 finding; a default recorded without a reply is D1(c); a side picked in a conflict, or a step-3 row written for a conflicting criterion, is D7 / D9; an unrouted surface file is D11; a missing or spurious bullet is D12. **They have different fixes.**
- **A clean run shows the rules behave on planted fixtures, never that any gap cost anything** — no incident stands behind this plan.

---

## Honest bounds

- **The ask sentence is model judgment against a documented harness nudge** (F8). Nothing mechanical makes a question be asked.
- **Only specify has a mechanical backstop, and it is partial.** `set-dp-default-applied` refuses a default without a reply — but the reply is text the model passes, so the check forces a quoted reply to exist, not to be real. `set-dp-answer` cannot tell a real user answer from a fabricated one. `set-dp-deferral` takes no reply (OQ-3). plan and breakdown have no backstop.
- **An unattended auto-mode run blocks** at its first question.
- **`dontAsk` and `claude -p --permission-prompts none` fall back to a numbered list that ends the turn;** in `-p`, the run just ends.
- **The architect cannot ask** (F6). Every route in this plan is the orchestrator's.
- **`/devforge:plan` never resolves an AC conflict.** Even an answered one needs a spec revision (D7).
- **Item 3's recognition rests on item 17,** which is *"context, not enforced configuration"* and is absent from installs older than plan 99.
- **Nothing detects a delegation, or "the same feature", mechanically** — the bounds plans 98 and 99 record.

---

## Tripwires

- **Plan 75's tripwire, both halves:** zero gates, zero validators, zero new `verify-*` numbers, zero new research check numbers. `set-dp-default-applied`'s `--delegated-reply` requirement is an EXISTING gate made mode-independent, not a new one. D14 rewords check 12b and adds no check.
- **Python only in Phases 1–2** (items 2, 4 and 6).
  - Python goes python-engineer → python-reviewer, with a test for every function, run in the same turn.
  - Every markdown edit goes instruction-author → instruction-reviewer.
  - Every new Claude Code fact is checked through `claude-code-guide`.
- **No `disable-model-invocation` change:** 17 model-invocable / 4 human-typed-only.
- **No constitution edit.** `src/constitution.md` does not mention auto mode (F9).
- **No back-porting into shipped installs.** The frozen benchmark install is never touched.
- **Plans 98 and 99 are amended only by dated notes** (D6).

---

## Non-goals

- **Rewriting plan 98's or plan 99's ratified text.**
- **Mechanical detection of a delegation or of "the same feature".** Both stay model judgment.
- **Asking in commands outside `/devforge:specify`, `/devforge:plan` and `/devforge:breakdown`.** (c) names three; `/devforge:research` and `/devforge:discover` keep their own question rules.
- **An unattended path** through the three commands.
- **Editing `src/CLAUDE.md` item 17** (D5), **`src/agents/architect.md`** (D7), or **`src/constitution.md`**.
- **Changing implicit approval by invocation** (plan 98's D5).
- **A reply requirement on `set-dp-deferral`**, unless OQ-3 is ratified the other way.
- **Anything specific to the benchmark,** and any client, component, ticket or benchmark path in this repo.

---

## Context for next session

⚠ **Evidence class, repeated: NO incident. Items 1 and 3–6 are gaps found by reading; item 2 is a maintainer directive; nothing was measured.** ⚠ All line digits drift — grep the quoted text.

**The one sentence that governs everything here:** the three commands that ask clarifying questions ask them in every mode, and an answer the user did not give is never recorded as theirs.

**The bounds that travel with it** (`## Honest bounds` has them in full): the ask sentence is model judgment against a documented harness nudge; only specify has a mechanical backstop, and it is partial; `set-dp-answer` cannot tell a real user answer from a fabricated one; an unattended auto-mode run blocks; and `dontAsk` and `-p --permission-prompts none` fall back to a numbered list that ends the turn.

**Trap 1 — deleting research's `detect-mode`.** `research_helper detect-mode` (bug vs enhancement, `--override`) is a different verb. Only specify's goes (F11, F12).

**Trap 2 — hunting the `mode` key in `rubric-coverage`.** It is the `summary` verb's key (F11).

**Trap 3 — reading `set-dp-answer` or `--delegated-reply` as proof of what the user said.** Neither can tell real user text from model text. The only mechanical refusal is `set-dp-default-applied`'s, and it forces a reply to exist, not to be real (D1(c), D2).

**Trap 4 — breaking the pre-change render.** A `default_applied` entry with no `delegated_reply` still exists in in-flight states and old specs. Its no-suffix render must keep working and keep a test (Phase 1a).

**Trap 5 — picking a side in an AC conflict, or recording it three times.** Even on an answer, no Key Design Decision picks a side. NEITHER of PHASE 2.5 step 3's arms applies to the two criteria — not the revise arm, and not its *"no clear implementation path"* Risk line. One conflict yields exactly one Risk row (D7).

**Trap 6 — "end the turn having written nothing" at breakdown.** PHASE 0b may already have flipped `plan.md` to Approved. D10's arm writes no task file and leaves that flip in place (F5).

**Trap 7 — a literal 4 in emitted text.** Only the numbered-list fallback may carry it, and only if OQ-4 is ratified that way.

**Trap 8 — editing item 17 or `architect.md`.** Both stay byte-identical (D5, D7).

**Trap 9 — reading plan 98's or plan 99's auto-path text as current.** After Phase 4 each such site carries a dated note (D6). Before Phase 4 that text is stale by this plan's own design.

**Trap 10 — conflating Claude Code's auto mode with the framework's signals.** Claude Code's is a permission mode (F8). `--auto`, `DEVFORGE_AUTO_MODE` and the `<system-reminder>` sniffing were the framework's, and they are what D1 removes. Claude Code's nudge remains, which is why D2 exists.

**Trap 11 — reading a predicted gap as observed.** No incident stands behind any item.

**Trap 12 — a clobbered ledger edit.** Another session may be building in this checkout (F21). Re-read `git status`, read each ledger live, and commit by explicit path.

**File anchors:**

- `src/commands/specify/main.md` — Phase 2's intro, `### Mode detection`, the per-decision-point protocol (steps 2 and 3), `### Question rounds`, the stop rule, Step 4.5, Step 4.7, Step 5.1.
- `src/commands/plan/main.md` — Phase 1.3's sub-question list (6 and 12) and the paragraph after it; the Rule 5 note; PHASE 2.5 steps 3 and 4; PHASE 3's mode bullets and approval summary.
- `src/commands/breakdown/main.md` — PHASE 2's sub-question 4, the Agent Assignment escalation paragraphs and the **Halt rule:**; PHASE 4's mode bullets.
- `src/devforge/lib/_specify/` — `_cli.py`, `_cmds_phase01.py`, `_cmds_phase2.py`, `_cmds_phase3.py`, `_cmds_phase5.py`, `_render.py`, `_schema.py`, `_state.py`; and the facade `src/devforge/lib/specify_helper.py`.
- `src/devforge/lib/_research/_cmds_render_verify.py` — check 12.
- Read-only here: `src/CLAUDE.md` (item 17, `### Never` item 7), `src/agents/architect.md` (Rule 6, the Termination rule, Rule 9).

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation. Then read plan 99's D4, D5 and D10, and plan 98's D1 and D3.
2. **Check `## Phase 0 close record` first.** If it still reads *Pending*, nothing is ratified and **no build phase may start.**
3. **Re-verify F1–F21 against the live tree.** Grep the quoted text, never the digits: `is an acceptance-criteria conflict`, `escalate to the human`, `Mode-dependent execution path`, `### Mode detection`, `rejects user-answer setter`, `default-applied setter`, `AUTO_MODE_ENV_VAR`, `"mode": state.get("mode")`, `additions discovered during planning`, `**Bundling**`, `Up to 5 questions per round`, `four bullets, plus`, `probe the runner-up frame`. ⚠ After each build phase, some of these strings are gone by design; zero hits for them is then the built state, not a regression.
4. **Build order:** Phase 1 before Phase 3a (3a quotes 1a's message and names 1b's bullet). Phases 2, 3b and 3c are independent of Phase 1. Phase 4 runs last, because it records what the earlier phases did.
5. **Route every edit through the house flow:**
   - python-engineer → python-reviewer for every Python edit, with a test per function, run in the same turn;
   - instruction-author → instruction-reviewer for every markdown edit;
   - `claude-code-guide` for every new Claude-Code-integration fact.
6. **Commit by explicit path, never `git add -A`.** Re-read `git status` first (F21).
7. **After each phase, cross-check.** Grep every verb, flag, heading and token touched — `detect-mode`, `--delegated-reply`, `Deferred to open questions`, `AC conflicts`, `2.4e` — and fix any dangling reference in the SAME change.
8. **Run Phase 4, then leave Phase 5 to the maintainer.**
9. **Keep the evidence class attached.** Any summary of this plan repeats it: NO incident, items 1 and 3–6 predicted, item 2 a directive, nothing measured.
