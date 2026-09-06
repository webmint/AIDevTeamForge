# 96 — PR Reading Guide Plan

**Created**: 2026-09-06
**Status**: **Phase 0 CLOSED 2026-09-06** (single blanket maintainer directive — every D-item and OQ ratified AS RECOMMENDED, no per-item deliberation supplied; see `## Phase 0 close record`). **Build phases 1–4 in progress this session.** Phase 5 is a DEFERRED user-driven HARD GATE — not run, so nothing here is consumer-validated.

Make `summary.md` a reviewer's READING GUIDE rather than only a recap, and make the PR-ready artifact actually reach the PR.

---

## Origin & evidence

⚠ **Evidence class, and every summary of this plan must repeat it: ONE maintainer-raised concern in conversation (2026-09-06) — AI-PR review fatigue, a general observed phenomenon and NOT a consumer incident with this framework — plus grep-verified structural facts about the tree.** No consumer incident, none claimed, nothing measured. This is a **predicted-gap plan in plan 87's class**. A clean Phase 5 would be evidence the sections render as designed; it would never be evidence the gap cost anything, because nothing here measured reviewer fatigue before or after.

The maintainer's concern: humans get tired reading large AI-generated PRs. A session review of the framework's PR-facing surface found `/devforge:summarize`'s `summary.md` is a good structured RECAP but not a reviewer READING GUIDE, and that the "PR-ready" artifact never actually reaches a PR.

Three findings, each verified against the tree on 2026-09-06. ⚠ Line digits below drift — **grep the quoted text, never the digits**.

### F1 — no attention triage (medium)

`summary.md`'s skeleton renders directory-level file COUNTS only. `src/commands/summarize/references/summary-format.md`'s `### Files changed` block (around lines 46-56 — grep `### Files changed`) is `- \`src/components/\` — N file(s)` repeated per directory plus a totals line. Nothing tells a reviewer where to start, which files carry the decisions, and which are mechanical consequences of them.

The data to compose such a guide already exists in this command's own scratch inputs and simply never reaches the summary:

- `decisions.json` — `decision` / `chosen` / `rationale` / `rejected` per key decision (`read-plan-decisions`).
- `notes.json` — per-task `files_changed` and the task file path (`parse-completion-notes`).
- Task titles, from the task files the command already enumerates.
- The **Two-hats partition** declarations plan 86's F2 put in task files: **behavior-changing / behavior-preserving labels ON the `- In <path>:` entries already written in `## Change Details`** (and, where one file holds both kinds of change, on the named functions under an entry), MIXED tasks only, and **deliberately never a header field** (plan 86 **Facts 17/18** — header fields are helper-emitted and flag-gated in `render_task_file`, so a new one would have been Python, while `## Change Details` is a free-form skeleton section the ORCHESTRATOR fills).

⚠ **Correction recorded 2026-09-06 so it is not re-inherited: there is NO `### Two-hats partition` heading in a task file.** An earlier revision of this plan described the partition as a subsection by that name, and Phase 2 consumed that wrong description once before instruction-reviewer caught it. `### Two-hats partition (mixed behavior-change + restructuring tasks)` is a heading in `src/commands/breakdown/main.md` — the name of the INSTRUCTION section that tells `/devforge:breakdown` how to write the labels — and that lane states in its own text that it *"adds NO flag and NO header line"*. A consumer therefore looks for the labels, never for a heading; a grep for the heading in task files finds nothing and would wrongly conclude no task declares a partition.

### F2 — no honest-bounds section (medium)

Nothing in the summary says what was NOT verified. Two verified sub-facts:

**(a) `has_unverified` is emitted and consumed by nothing.** `summarize_helper parse-completion-notes` already emits `has_unverified` per task — `src/devforge/lib/_summarize/_inputs.py`, the `parse_completion_notes` docstring (around line 268) and the regex `_UNVERIFIED_BOX_RE` (around lines 251-253) matching `^- \[ \].*_\(unverified`, i.e. plan 89 D4's annotated unverified Done-When boxes.

⚠ **Correction to the drafting brief, recorded so it is not re-inherited:** the brief stated a grep proves `has_unverified` appears NOWHERE in `src/commands/summarize/main.md`. **That is false.** It appears TWICE in `main.md` — in the `$WORKDIR/notes.json` scratch-file key enumeration (around line 36) and in the PHASE-2.2 field enumeration (around line 162). What is TRUE, and what the finding rests on, is narrower and still sufficient: both mentions merely enumerate the helper's output shape, **no composition step names the field** (PHASE 2.2's consumption sentence says *"The orchestrator reads `files_changed` + `notes` per task for the Changes + Deviations sections"*), and the field appears **nowhere in `summary-format.md`**. So the field is on the wire and reaches no rendered section — **exactly plan 89's "already on the wire, never named by the spec" pattern**, which is the precedent this finding cites.

**(b) verify's advisory material never reaches summarize.** `read_verification` (`_inputs.py`, around lines 111-199 — grep `def read_verification`) returns ONLY `ac_list` (id / status / evidence), `verdict` and `path`. So everything `/devforge:verify` records ADVISORILY in `verification.md` is invisible here:

- the e2e advisory line `compute-verdict --e2e` folds into `reasons` — `"E2E run ({status}, advisory — does not block the verdict): {note}"` (`src/devforge/lib/_verify/_verdict.py`, around lines 520-524; grep `E2E run (`), appended when the status is truthy and not `off`;
- the two `_(advisory — does not block the verdict)_` blocks in `## Code Quality` for scope creep and leftover artifacts (`src/devforge/lib/_verify/_report.py`, around lines 182 and 195 — grep `advisory — does not block the verdict`).

Plan 90's own recorded cost — *"a ratifier who takes (i) will see APPROVED printed beside a red suite"* — is precisely the honest bound a PR reviewer needs to see. Today the summary cannot show it.

⚠ **Second correction to the drafting brief, and it is load-bearing for D2.** The brief described the reasons list as *"the `**Key reasons**:` list rendered capped at 4 in `_verify/_report.py:442-445`"*. Verified: that capped block is inside **`render_inline_summary`** (grep `def render_inline_summary`) — the `## Verification Complete` **console block**, which is never written to a file and is therefore unreachable to `/devforge:summarize`. The list that DOES land in `verification.md` is rendered by `render_report` under `## Verdict`, is headed **`**Reasons**:`** (not `**Key reasons**:`), and is **UNCAPPED** — the loop is `for reason in reasons` with no slice (grep `out.append("**Reasons**:")`). D2(b) below targets that heading. **A build that greps for `**Key reasons**:` in `verification.md` finds nothing and would conclude the feature is unbuildable.**

### F3 — "PR-ready" never reaches the PR (medium)

`/devforge:summarize` PHASE 5 tells the user the summary is *"copy-ready for a PR description"*. `/devforge:finalize` PHASE 4 ends with *"Feature is ready for PR."* and its rule 9 reads, verbatim:

> 9. **Terminal** — `/devforge:finalize` is the last pipeline step. Its "next step" is "create a PR"; there is no downstream command pointer.

No command composes a PR body. ⚠ **Third correction to the drafting brief:** the brief asserted *"nothing in the emitted instruction set invokes `gh pr`"*. **False as stated** — a `gh pr` grep over `src/` returns hits in `src/commands/pr-review/main.md` (its `Bash(gh pr *)` permission line and its `gh pr view --json` + `gh pr diff` intake) and in `src/devforge/lib/_pr_review/`, and `pr-review` **is** a member of `_PROMOTED` in `scripts/emitters/claude.py`, so it ships. The accurate claim, which is what F3 rests on: **`gh pr create` appears nowhere in `src/`**, and every `gh pr` hit belongs to `/devforge:pr-review`, which CONSUMES an already-existing PR. **No command in the framework creates or composes one.**

`/devforge:finalize`'s only touch on `summary.md` is a presence check plus a soft-warn (`main.md` PHASE 0.3 — grep `Missing-summary soft-warn`) and the `**Summary**: [included in squash | not found …]` line in the PHASE-4 results block (shape documented in `references/results-and-docs.md`). So the human creates the PR by hand, and the reading guide sits in `specs/<feature_dir>/summary.md` where a GitHub reviewer may never look.

---

## Decisions to ratify

Nothing below is ratified. Each item states a recommendation, its reasoning, and the counter-argument against it.

### D1 — F1 composition route

**Fork.** (a) **Instruction-only** — `/devforge:summarize` PHASE 3 gains a composition input: the orchestrator reads the behavior-changing / behavior-preserving labels on `## Change Details` entries (the Two-hats partition — labels on the existing `- In <path>:` entries, no heading) and task titles directly from the task files it already enumerates for `parse-completion-notes` (the `--task-file` list is already at hand in PHASE 2.2). (b) **Python** — widen `parse-completion-notes` with a `two_hats` field.

**RECOMMEND (a).** The two-hats block is deliberately free-form prose (plan 86 Facts 17/18 — never a header field, because header fields are helper-emitted and flag-gated while `## Change Details` is orchestrator-filled), so a prose-composing orchestrator is its natural consumer. There is direct precedent: plan 90 D2 had `/devforge:breakdown` read the E2E table from `plan.md` directly, *"as the dead-code table already is"*.

**Counter-argument to record:** helper-owned parsing is the house norm for mechanical steps, and reading prose in the orchestrator is weaker than a parser with tests. **Answer:** this is COMPOSITION INPUT, not a mechanical gate predicate — no downstream consumer parses the result, no gate reads it, and a mis-read degrades one advisory prose section rather than failing a check. The norm binds mechanical steps; this is not one.

⚠ **If (b) is ratified, this plan does not yet build it.** No phase below widens `parse-completion-notes` — Phase 1 exists only for D2(b) and touches only `read_verification`. **Ratifying D1(b) therefore REQUIRES a plan amendment adding a second conditional Python phase (mirroring Phase 1's D2(b) pattern: helper-side parse, tests in `tests/lib/_summarize/test_inputs.py`, python-engineer → python-reviewer) BEFORE Phase 2 may proceed**, because Phase 2's composition step would otherwise name a field nothing emits. The gap is stated here rather than left silent so a ratifier picking (b) knows the cost they are accepting.

### D2 — F2 scope

**Fork.** (a) **Zero-Python v1** — no new signal is parsed; the Not-verified section composes from what the command already receives today, which for this section is `has_unverified`. (b) **Widen `read_verification`** with three MECHANICALLY PARSED fields — `e2e_status` and the two advisory-block presence booleans — as a bounded parser addition with tests, so the section can name a red or inconclusive e2e run and the presence of advisory findings.

(What either fork RENDERS is D3's to decide, not this fork's — D3 owns the checklist-exclusion rule and is the single owner of what reaches the page.)

**RECOMMEND (b).** The loudest honest bound — an `e2e-failing` status printed beside an APPROVED verdict, which is plan 90's own recorded cost — is exactly what (a) cannot show. The widening is one bounded parser addition in a file that already parses `verification.md` for two other things, it is covered by tests, and it feeds one summary line.

⚠ **The parse must yield a STATUS TOKEN, never the raw reasons list.** Per F2's correction, the bullets live under `**Reasons**:` in the `## Verdict` section, rendered UNCAPPED by `render_report` — but exposing that list to the orchestrator would force it to mine free text for the e2e token and to judge which unrelated reason lines to suppress. That is inference, and it contradicts D3's verbatim-quotation rule at the exact seat D3 governs. So the helper regexes the known shape `/devforge:verify` emits (`"E2E run ({status}, advisory — does not block the verdict): {note}"` — `_verify/_verdict.py`) and returns the status token alone; **the raw `reasons` list is deliberately NOT part of the returned shape.** Nothing composes from it, and exposing it would invite exactly the judgment-mining this plan forbids.

**Counter-argument to record:** minimal-scope instinct says ship (a), record (b) as the strengthening arm with an observed trigger, and keep this plan zero-Python. **The recommendation is still (b)** because the section's whole point is honesty, and shipping a Not-verified section blind to the loudest advisory signal in the pipeline undercuts that point at birth. A ratifier who prefers (a) should expect a summary that says "everything verified" over a red e2e suite.

**If (a) is ratified, Phase 1 is SKIPPED.** The plan is zero-Python end to end only when **D1(a) AND D2(a)** are both ratified — D1(b) carries its own Python cost and its own required amendment (see D1). That branch is restated at Phase 1.

### D3 — the two new sections' shape and placement

**`### Review guide`** — 3-5 lines: where to start, which files carry which decision, and which changes are mechanical consequences of those decisions. Composed from `decisions.json`'s `rationale`, the two-hats declarations, and task titles + `files_changed`. **Model judgment grounded ONLY in those named present inputs.** Placed directly AFTER `### What was built` and BEFORE `### Changes` — triage before detail.

**`### Not verified`** — unverified Done-When boxes by task (`has_unverified`). Non-passed ACs are **already annotated in the AC checklist**, so this section names only what the checklist does not. Under D2(b) it also names the **`e2e_status`** field by name — rendered when its value is neither `e2e-clean` nor `off` — and the two advisory-presence booleans. Each is a **VERBATIM** report of a field `/devforge:verify` already recorded and the helper already parsed; **the orchestrator extracts nothing from prose here.** Placed directly AFTER `### Acceptance criteria`.

**Both sections follow the house omit-empty rule** — omitted ENTIRELY when they would be empty, the same rule `### Deviations from plan` already carries (`summary-format.md`: *"**Omit empty sections** — the Deviations section is omitted entirely when no task deviated."*). A clean feature's summary therefore looks exactly as it does today.

**Neither section renders a verdict or findings.** Plan 24's D1 (agent-free, verdict-free, findings-free) is untouched, and this must be said explicitly in the emitted text: everything the Not-verified section shows is a **verbatim quotation of a status `/devforge:verify` or `/devforge:implement` already recorded**, never a judgment `/devforge:summarize` makes.

**Counter-argument to record:** two more sections is two more things to read, in a plan whose origin is reading fatigue. **Answer:** the Review guide is the shortest section in the document and sits first, so it is read INSTEAD of the detail below it, not in addition; and the Not-verified section renders only when there is something a reviewer would otherwise have to discover by hand. A ratifier who rejects this should reject the Review guide and the Not-verified section together — they trade against the same budget.

### D4 — F3 shape

**Fork.** (i) **Print-only** — `/devforge:finalize` PHASE 4, when the summary is present AND the squash succeeded, appends one concrete ready-to-run line to the results block, e.g. `gh pr create --title "<message_used>" --body-file <feature_dir>/summary.md`. The user runs it; finalize stays terminal and executes nothing new. (ii) **Offer-and-run** — finalize offers and runs `gh pr create` on the user's agreement (plan 93's one-agreement-per-command shape).

**RECOMMEND (i).** Creating a PR is an outward-facing PUBLISH action; `gh` availability, authentication and remote state all vary, and none of them is checked at this seat. Rule 9's terminal stance survives untouched: printing the concrete command **is not a downstream-command pointer** — it IS the "create a PR" next step made concrete, which `main.md` PHASE 4 already calls the next step in prose (verbatim: `The "ready for PR" line above IS the next step (create the PR).`).

**Counter-argument to record:** a printed line the user must copy is one more manual step, and plan 93 already established the offer-and-run shape for commands the model may invoke. **Answer:** plan 93's shape governs invoking FORGE commands; `gh pr create` publishes to a third party. Record (ii) as the **named strengthening arm** with the trigger *"the maintainer observes the printed line going unused"*.

**A tool-surface asymmetry the ratifier should weigh, stated as an observation and not as a semantics claim.** Verified in the tree: `src/commands/pr-review/main.md`'s frontmatter declares an `allowed-tools` list whose first entry is `Bash(gh pr *)`; `src/commands/finalize/main.md`'s frontmatter declares **no `allowed-tools` key at all** (only `name`, `description`, `argument-hint`). Whether arm (ii) would therefore need a frontmatter change to `/devforge:finalize` is a **Claude-Code-integration question this plan does not answer** — under the house rule in `CLAUDE.md` ("Verify Claude Code authoring conventions before writing commands/agents"), **a ratifier who takes (ii) owes a `claude-code-guide` agent check BEFORE Phase 3 begins**, and that check is a Phase-3 precondition on that arm only. **Arm (i) executes nothing and so never raises the question** — a further, non-decisive point in its favour.

**Consistency edits this fork owes, to be re-derived live at Phase 3 (digits and wording drift):**

1. `finalize/main.md` PHASE 4's results block gains the line, and the surrounding TERMINAL sentence is checked for tension with it.
2. `finalize/main.md` rule 9's wording is checked live — its clause is *"there is no downstream command pointer"*, and `gh pr create` is not a forge command, so the reading holds; the plan requires that this be **stated**, not assumed.
3. `finalize/references/results-and-docs.md`'s documented block shape is updated to match, **and** its `## What this block is NOT` third bullet — which today reads ``- **No next-pipeline-command pointer.** `/devforge:finalize` is terminal — its "next step" is "create a PR", already named in the block. Do not point at a downstream command.`` (grep `No next-pipeline-command pointer`) — is amended to say the `gh pr create` line is that same next step made concrete and is not a downstream-command pointer. ⚠ **Without edit 3 a future session reads the new line as violating the bullet directly above it.**

### OQ-1 — does rule 4's source enumeration need widening?

`/devforge:summarize` `main.md` rule 4 (**No speculation**) enumerates the allowed sources: *"include only information present in the spec, plan, task `## Completion Notes`, `verification.md`, or git data"*. F1 draws on **two** task-file sources that enumeration does not name: `## Change Details` (the two-hats home, read under D1(a)) and the **task TITLE header**.

⚠ **The task-title gap is PRE-EXISTING, not introduced here.** Today's shipped `### Changes` section already composes one line per task from task titles (`main.md` PHASE 3 item 2; the skeleton's `- [Task title] — [1-line what it did]`) while rule 4 names no task source but `## Completion Notes`. So rule 4 is already narrower than the command's own behavior, and this plan neither created that nor is required to fix it.

**RECOMMEND yes, and widen to name BOTH** — task `## Change Details` AND the task title header — in the same edit as D1(a). Otherwise **rule 4 forbids the very read D1(a) instructs**, and the command ships a self-contradiction; naming only `## Change Details` would leave the Review guide's title-derived half in the same contradiction the Changes section sits in today. Closing the pre-existing half costs one clause in the same sentence, so it is folded in rather than deferred. The same enumeration appears in PHASE 3's closing paragraph (*"Do not speculate — include only what is present in…"*) and must be widened with it; grep the quoted phrase to find both sites rather than trusting a count.

### OQ-2 — does PHASE 5's closing message change too?

**RECOMMEND no.** Minimal scope: the PR moment belongs to `/devforge:finalize`, and PHASE 5's *"copy-ready for a PR description"* sentence stays true — more true, in fact, once the summary carries a reading guide. **Counter-argument:** a reader at PHASE 5 learns nothing about the `gh pr create` line that finalize will print. **Answer:** they learn it from finalize, one command later, which is where the action is.

### OQ-3 — the Review guide's honesty bound

The file-to-decision mapping is **MODEL JUDGMENT over named inputs, and nothing checks it**. No gate reads it, no validator parses it, and a wrong mapping produces a misleading guide with no error anywhere.

**RECOMMEND recording this as an accepted bound, stated in the emitted text** — the claim is **orientation, not enforcement**. This mirrors plan 86 F3's honesty pattern (*"NOTHING CHECKS the declaration"* — the claim there is that its absence is visible, not that anything enforces it). The emitted sentence must not use the words *accurate*, *correct* or *reliable* about the mapping.

---

## Phase 0 close record

**CLOSED 2026-09-06** by a **single blanket maintainer directive** («го»). **Every D-item and OQ is ratified AS RECOMMENDED.**

⚠ **No per-item deliberation was supplied, and this record says so** rather than implying the arguments were weighed one by one (plans 91 / 92 / 94 / 95 precedent). Each item's recommendation, reasoning and counter-argument stand as drafted above; the close adopted the recommendation set wholesale. A future session must not cite this close as evidence that any individual counter-argument was answered — it was accepted along with the rest.

### Per-item outcomes

| Item | Ratified arm | Consequence for the build |
|---|---|---|
| **D1** | **(a)** instruction-only | The orchestrator reads the behavior-changing / behavior-preserving labels on `## Change Details` entries + task titles from the task files it already enumerates. **No amendment phase is owed** — the conditional Python phase D1(b) would have required is NOT triggered. |
| **D2** | **(b)** widen `read_verification` | **Phase 1 RUNS.** It delivers `e2e_status` + the two advisory booleans, and **NO `reasons` key**. |
| **D3** | as drafted | Both placements (`### Review guide` after `### What was built`; `### Not verified` after `### Acceptance criteria`), the omit-empty rule on both, and the verbatim-only Not-verified rule. |
| **D4** | **(i)** print-only | `/devforge:finalize` PHASE 4 prints the `gh pr create` line; nothing executes `gh`. Arm (ii) stays the **named strengthening arm** with its recorded trigger (*"the maintainer observes the printed line going unused"*). **The `claude-code-guide` precondition attached to (ii) is therefore NOT owed** for this build. |
| **OQ-1** | **yes**, widened to BOTH | Rule 4's enumeration names task `## Change Details` AND the task title header, at **both** enumeration sites (rule 4 and PHASE 3's closing no-speculation sentence). |
| **OQ-2** | **no** | `/devforge:summarize` PHASE 5's closing message is unchanged. |
| **OQ-3** | accepted bound | The orientation-not-enforcement bound is stated in the emitted text; the words *accurate* / *correct* / *reliable* appear nowhere in it. |

### Build-binding field names

The three fields D2(b) adds to `read_verification`'s result dict are **named here so Phase 1's Python and Phase 2's instruction edits cannot drift apart**. These spellings are binding on both phases:

| Field | Type | Source in `verification.md` |
|---|---|---|
| `e2e_status` | `str` or `None` | The status token regexed out of the `E2E run ({status}, advisory — does not block the verdict): {note}` bullet under `**Reasons**:` in `## Verdict`. `None` when no such bullet is present. |
| `has_scope_creep_advisory` | `bool` | Presence of the `## Code Quality` scope-creep block carrying `_(advisory — does not block the verdict)_`. |
| `has_leftover_artifacts_advisory` | `bool` | Presence of the `## Code Quality` leftover-artifacts block carrying `_(advisory — does not block the verdict)_`. |

⚠ **`reasons` is NOT a field.** Its absence is a ratified constraint, not an oversight — Phase 1's Verify asserts the key is absent. Do not add it "for completeness"; nothing composes from it, and exposing it would push judgment-mining into the orchestrator against D3.

---

## Phases

### Phase 0 — Ratification

Every D-item and OQ above. **No build until Phase 0 is closed.** House norm: the maintainer may close it with a blanket directive; the close record **must state whether per-item deliberation was supplied** (plans 91 / 92 / 94 / 95 precedent). Record the D2 branch explicitly — it decides whether Phase 1 runs at all.

#### Verify

- A `## Phase 0 close record` section exists in this file naming, per item, the ratified arm and whether deliberation was supplied.
- The record states which D2 arm was taken and therefore whether Phase 1 runs or is skipped.

### Phase 1 — Python (ONLY if D2(b) is ratified)

⚠ **If D2(a) is ratified instead, Phase 1 is SKIPPED and the Phase-1 close record says so explicitly.** The plan is zero-Python end to end only when **D1(a) AND D2(a)** are both ratified; **D1(b) requires its own conditional Python phase, added by amendment before Phase 2 (see D1).**

Widen `read_verification` in `src/devforge/lib/_summarize/_inputs.py` so its result dict also carries these three **mechanically parsed** fields:

- `e2e_status` — `str` or `None`. Parsed by regex over the known shape `/devforge:verify` emits into the `**Reasons**:` bullets under `## Verdict`: `"E2E run ({status}, advisory — does not block the verdict): {note}"` (`_verify/_verdict.py` — grep `E2E run (`). `None` when no such bullet is present.
- Two advisory-presence booleans for the `## Code Quality` blocks carrying `_(advisory — does not block the verdict)_` — one for scope creep, one for leftover artifacts.

⚠ **The raw `reasons` list is deliberately NOT part of the returned shape** (D2's ratified constraint). Returning it would push token-extraction and line-suppression judgment into the orchestrator, contradicting D3's verbatim-quotation rule. The helper does the extraction; the orchestrator receives a token and two booleans and composes from those alone. **Do not add `reasons` "for completeness" — nothing composes from it.**

⚠ The parse targets `**Reasons**:` under `## Verdict`, **not** `**Key reasons**:` (console-only — see F2's correction).

The existing keys (`ac_list`, `verdict`, `path`) are **byte-unchanged in shape** so every current consumer is unaffected. Tests go in `tests/lib/_summarize/test_inputs.py` (the existing file for this module). Route through **python-engineer → python-reviewer** per house flow.

#### Verify

- `read_verification`'s returned dict contains `e2e_status` plus the two advisory booleans, and still contains `ac_list`, `verdict` and `path` with unchanged shapes.
- The returned dict contains **no** `reasons` key — assert its absence, not only the presence of the three new fields.
- `tests/lib/_summarize/test_inputs.py` gains tests covering: a report whose Reasons block carries an `E2E run (…)` bullet (each status value the gate can emit), a report with a Reasons block but no e2e bullet, a report with no Reasons block at all, and a report carrying each advisory block. Every added function has a test that RUNS.
- The full `tests/lib/_summarize/` suite is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — Summarize instruction edits (F1 + F2)

Instruction-only. Route through **instruction-author → instruction-reviewer**.

- `references/summary-format.md` — the skeleton gains `### Review guide` (after `### What was built`) and `### Not verified` (after `### Acceptance criteria`), each with its omit-empty condition stated in the skeleton the way `### Deviations from plan` states its own, plus their composition rules in the `## Composition rules` list. The `## Inputs that shape the summary` list is updated to name what each new section draws on.
- `main.md` PHASE 3 — gains the two composition items in the numbered section list (renumbering the existing items, which are positional), the D1(a) task-file read step (**the behavior-changing / behavior-preserving labels on `## Change Details` entries — there is no heading to search for**), and OQ-1's source widening at BOTH sites (rule 4 and PHASE 3's closing no-speculation sentence), naming **both** task `## Change Details` and the task title header.
- `main.md` PHASE 2.2 — the surrounding prose names `has_unverified` as a CONSUMED field, not only an emitted one.
- Under D2(b): `main.md` PHASE 2.1 and the `$WORKDIR/verification.json` scratch-file bullet name `e2e_status` and the two advisory booleans. **They must not name a `reasons` key** — it is deliberately absent from the returned shape.
- The emitted text states OQ-3's bound (orientation, not enforcement) and D3's verdict-free clause (verbatim quotation, never a judgment this command makes).

#### Verify

- `grep -n 'has_unverified' src/commands/summarize/main.md` returns ≥ 1 hit **inside a composition or consumption sentence**, not only in the two field enumerations that exist today.
- `summary-format.md` contains both new headings, and each is within 3 lines of an omit-when-empty instruction.
- `grep -n 'Change Details' src/commands/summarize/main.md` returns a hit inside rule 4's source enumeration AND inside PHASE 3's closing no-speculation sentence; both of those sentences also name the task title header.
- Under D2(b): `grep -n 'reasons' src/commands/summarize/main.md` returns **no hit PRESENTING `reasons` as an available key** — the orchestrator is never pointed at a raw reasons list. **Negative mentions PASS and are expected**: the spec states in two places that the key does not exist and is not to be added, which is the guard against a future session restoring it, so a criterion demanding zero occurrences would delete its own protection.
- No occurrence of the words `verdict` or `findings` is introduced as something either new section RENDERS; the existing verdict-free / findings-free statements are unchanged.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 3 — Finalize instruction edits (F3)

Instruction-only, under the ratified D4 arm. Route through **instruction-author → instruction-reviewer**. Read all three surfaces LIVE before editing — line digits and wording drift.

- `main.md` PHASE 4 — the results block gains the `gh pr create` line under its two conditions (summary present AND squash succeeded), and the block's existing TERMINAL sentence is reconciled with it.
- `references/results-and-docs.md` — the documented block shape gains the line with its composition rule, and the `## What this block is NOT` third bullet is amended per D4's consistency edit 3.
- `main.md` rule 9 — checked live and, if its wording admits the misreading, amended to say the printed command is the "create a PR" step made concrete and not a downstream-command pointer.

#### Verify

- The `gh pr create` line appears in BOTH `main.md`'s PHASE-4 block and `results-and-docs.md`'s documented shape, with byte-identical flag spelling in the two places.
- Its two conditions (summary present, squash succeeded) are stated at both sites.
- `results-and-docs.md`'s `## What this block is NOT` third bullet explicitly reconciles the new line with the no-downstream-pointer rule.
- `grep -n 'gh pr create' src/` returns hits ONLY in the two finalize files — the line is not duplicated into `/devforge:summarize` (OQ-2 recommends no) or anywhere else.

### Phase 4 — Docs sweep

- `CHANGELOG.md` `## [Unreleased]` — one entry.
- `src/CLAUDE.md` — check the `/devforge:summarize` and `/devforge:finalize` catalog lines for staleness. **Likely no-ops** (the summarize entry describes gating and outputs, not section names; the finalize entry names the squash and the last-step-before-PR framing). ⚠ **House rule: verify live and record each no-op EXPLICITLY in the phase's close note** — an unrecorded no-op is indistinguishable from an unchecked site.
- `CLAUDE.md` index line for plan 96, and the `PLAN-STATUS-ARCHIVE.md` entry, both written at close.

#### Verify

- The `## [Unreleased]` entry names the two new summary sections and the finalize PR line.
- The phase's close note records, per checked file, either the edit made or an explicit "verified no-op".
- `CLAUDE.md` carries a one-line index entry for plan 96 and `PLAN-STATUS-ARCHIVE.md` carries the full entry.

### Phase 5 — Consumer e2e — DEFERRED, user-driven HARD GATE

**NOT run at build time.** Build-verified is not consumer-validated. Three known-answer anchors:

1. **A feature with a mixed task carrying a two-hats declaration and an unverified Done-When box** → `summary.md` renders `### Review guide` and `### Not verified`, and each names exactly those inputs (the declared partition; that task's unverified box).
2. **A clean, fully-verified feature** → BOTH sections are ABSENT, and the summary's section shape is identical to today's skeleton. ⚠ **Fixture requirement, recorded 2026-09-06 during Phase 2**: the Review guide's omit condition keys off `decisions` being empty AND no task carrying a behavior-changing / behavior-preserving label — NOT off verification state — so this fixture's feature must ALSO have no recorded key decisions in `plan.md`. A clean feature that recorded decisions will legitimately render the Review guide, and scoring that as a failure would misread correct behavior. Only the Not-verified section keys off verification state.
3. **`/devforge:finalize` with `summary.md` present and the squash succeeded** → the results block carries the `gh pr create --body-file` line verbatim, with the real feature dir substituted.

⚠ **Anchors 1 and 2 are scored as a PAIR** — a section that always renders passes anchor 1 and fails anchor 2, so anchor 1 alone proves nothing. Under D2(b), anchor 1 additionally records whether a non-`e2e-clean` `e2e_status` reached the Not-verified section.

---

## Non-goals

- **Plan 75's tripwire, BOTH halves:** zero new gates, zero new `verify-*` numbers, zero new unnumbered hard-fail validators. **This holds under every ratification arm** — the Python either arm can add is parsing, **a read, never a check**: Phase 1's `read_verification` widening under D2(b), and the amendment-added phase D1(b) would require. Neither introduces a gate.
- **Plan 24 D1 untouched:** `/devforge:summarize` stays agent-free, verdict-free and findings-free.
- **Plan 63 / 93 counts: NO delta.** No `disable-model-invocation` flag moves; the invocability of `/devforge:summarize` and `/devforge:finalize` is untouched.
- **No auto-created PR.** Under the recommended D4(i), nothing in the framework executes `gh`.
- **No back-porting into shipped installs** — they arrive via `install.sh` / `update.sh`.
- **No change to `/devforge:verify`'s or `/devforge:review`'s ownership** of the verdict and findings, and no change to what `verification.md` CONTAINS — Phase 1 only reads it.
- **Verdicts and statuses are quoted verbatim, never re-derived** — plan 24 D3's pattern extended to the two new sections.
- **No new agent, no new command, no new helper verb.**

---

## Context for next session

The compressed fact base, so a fresh session need not re-derive it. ⚠ **All line digits drift — grep the quoted text.**

**`/devforge:summarize`'s four scratch inputs** (all under `$WORKDIR` = `${TMPDIR:-/tmp}/forge-summarize`), and which helper verb emits each:

| Scratch file | Verb | Keys this plan cares about |
|---|---|---|
| `changes.json` | `gather-change-data` | `by_directory`, `insertions`, `deletions`, `source_changes` |
| `verification.json` | `read-verification` | `ac_list` (id/status/evidence), `verdict`, `path` — **and nothing else today** |
| `notes.json` | `parse-completion-notes` | `files_changed`, `notes`, **`has_unverified`**, `has_notes`, `task_file` |
| `decisions.json` | `read-plan-decisions` | `decision`, `chosen`, `rationale`, `rejected` |

**File anchors:**

- `src/commands/summarize/references/summary-format.md` — the skeleton; `### Files changed` renders counts only; `## Composition rules` carries the omit-empty rule that `### Deviations from plan` already follows.
- `src/commands/summarize/main.md` — PHASE 2.2 (`parse-completion-notes`, the `--task-file` list D1(a) reuses), PHASE 3 (the six numbered sections + the closing no-speculation sentence), rule 4 (the source enumeration OQ-1 widens), PHASE 5 (the "copy-ready" message OQ-2 leaves alone).
- `src/devforge/lib/_summarize/_inputs.py` — `read_verification` (returns `ac_list` / `verdict` / `path`); `parse_completion_notes` + `_UNVERIFIED_BOX_RE` (`^- \[ \].*_\(unverified`).
- `tests/lib/_summarize/test_inputs.py` — where Phase 1's tests go.
- `src/devforge/lib/_verify/_report.py` — **`render_report` builds `verification.md`**: `## Verdict` → `**Reasons**:` bullets, **UNCAPPED**; `## Code Quality` → the two `_(advisory — does not block the verdict)_` blocks. **`render_inline_summary` builds the CONSOLE block** and owns the `**Key reasons**:` list capped at 4 — **console only, never in a file.**
- `src/devforge/lib/_verify/_verdict.py` — the e2e reason string `E2E run ({status}, advisory — does not block the verdict): {note}`, appended when the status is truthy and not `off`.
- `src/commands/finalize/main.md` — PHASE 0.3 (missing-summary soft-warn), PHASE 4 (results block + the TERMINAL sentence), rule 9 (terminal).
- `src/commands/finalize/references/results-and-docs.md` — `## Results block — PHASE 4` (documented shape + composition rules) and `## What this block is NOT` (the third bullet D4 amends).
- `scripts/emitters/claude.py` — `_PROMOTED`; `pr-review` IS a member, so its `gh pr view` / `gh pr diff` calls ship. `gh pr create` appears nowhere in `src/`.

**Three brief-level claims corrected during drafting** — do NOT re-inherit the originals: (1) `has_unverified` DOES appear twice in `summarize/main.md`, as field enumerations only; (2) `gh pr` DOES appear in `src/`, in `/devforge:pr-review`, which reads an existing PR; (3) the `**Key reasons**:` capped-at-4 block is the console summary, and `verification.md`'s list is `**Reasons**:` and uncapped.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes multi-session context not in the conversation.
2. **Read the live files before editing.** Line numbers in this document drift; **grep the quoted text, never the digits**. Every anchor above is cited with a quotable string for that reason.
3. **Check Phase 0's close record first.** If it is absent, nothing is ratified and no build phase may start. If it is present, the D2 arm it records decides whether Phase 1 runs.
4. **Route every edit through the house flow** — instruction-author → instruction-reviewer for markdown, python-engineer → python-reviewer for Phase 1's Python.
5. **After each phase, cross-check**: grep for every identifier, path, section name and heading touched, and fix dangling references in the same change.
6. **Keep the evidence class attached.** Any summary of this plan repeats that it is a predicted-gap plan — one maintainer-raised concern plus grep-verified structure, no consumer incident, nothing measured.
