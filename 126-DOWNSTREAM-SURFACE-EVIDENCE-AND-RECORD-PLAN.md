# 126 — Downstream Surface Evidence and Record Plan

**Created**: 2026-10-03
**Status**: **Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start. Nothing is built and nothing is measured.** The maintainer PICKED this plan's SHAPE on 2026-10-03 — one plan, Phase A (a measurement) first, then Phase B (a shared record) — and confirmed that no external install is touched (`### The maintainer directive — 2026-10-03`). ⚠ **That pick is a pick of the plan's SHAPE only: it ratifies no decision below.** Every decision (D1–D7) and every open question (OQ-1–OQ-10) carries a recommendation and its strongest counter-argument, and each waits for the maintainer. ⚠ **The evidence class, to be repeated in every summary of this plan:** the residual this plan closes is a DESIGN READING; plan 108's Anchor F was PREDICTED from text and never observed; NOTHING has been measured yet. ⚠ **Sequencing.** The maintainer works the open plans in NUMERIC ORDER. On 2026-10-03, plans 109, 110 and 111 read *"Phase 0 OPEN"* and plans 112–124 read *"Stub"* in their Status lines, so under that order this plan's build sits behind them unless the maintainer directs otherwise — the precedent for such a direction is plan 125, *"built ahead of plan 108 by ratified D5"* (`PLAN-STATUS-ARCHIVE.md:99`). ⚠ **Numbered 126 because 125 is the highest plan number at the repo root on 2026-10-03 and no other `126-*` file existed when this was drafted. Other sessions work in this checkout and may take 126 first; a resuming session re-checks the number before trusting it.** ⚠ **Every `file:line` here was read on 2026-10-03 and will drift — grep the quoted text, never the digits.** Plan 108's digits drifted DURING this draft: another session amended that file the same day, so its line numbers here are the ones read last.

Plan 108 left one weakness ratified on purpose: outside `/devforge:plan`, a surface a downstream command raises and leaves uncovered survives only as long as the turn does. It also left an evidence gap: the downstream hole it closed was predicted from text, and nothing was ever measured. **This plan answers both, in the order the maintainer picked: Phase A measures how a model reads `src/CLAUDE.md` item 17 before and after plan 108 when a downstream task meets an uncovered surface; Phase B gives a surface raised downstream ONE feature-scoped record, with one owner of its format and one reader at `/devforge:verify`.** ⚠ **Phase B persists what a model raises; it detects nothing.** A model that never raises the surface leaves the record empty, and Phase A's measurement is what puts a number on how often that happened in a synthetic setting.

---

## Origin & evidence

⚠ **Evidence class, stated first and repeated in every summary of this plan: the residual this plan closes is a DESIGN READING of plan 108's ratified text — NO consumer incident is recorded here, NO measurement exists, NO run was scored. Plan 108's Anchor F was PREDICTED from text and never observed. Phase A would produce the first measurement in that evidence class, and its ceiling is a synthetic fixture — never a consumer run.** This plan names no specific client, install, repo, branch, ticket or product.

⚠ **Line digits drift — grep the quoted text, never the digits.** Every `file:line` below was read against this tree on 2026-10-03.

### What plan 108 left — its ratified D4 residual

`108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md` is DONE (build) 2026-10-02 (its Status line, `108-…:4`; its `## Index` line, `PLAN-STATUS-ARCHIVE.md:98`). Its Phase 1 commit `b122abe` replaced one sentence of `src/CLAUDE.md` `### Always` item 17, **Scope follows what the user sees**, and its Phase 3 docs commit is `82171a9`. Item 17's three sentences that carry the downstream regime read, at `src/CLAUDE.md:230` on 2026-10-03:

> Covering a surface takes an affected area and an acceptance criterion in the spec that name it, so only the command writing that spec covers one. Deciding it yourself — handed back or never asked — cover it there, unless you can name what the user would see differently without it; anywhere else you cannot cover it, so raise it and leave it neither covered nor excluded. Record any exclusion as yours, with the reason you named, and tell the user.

⚠ **The phrase *"with the reason you named"* is NOT plan 108's ratified 2026-09-21 text.** Plan 108's build shipped *"with that reason"*; the maintainer picked the replacement explicitly on 2026-10-03, after the build, and plan 108 records that pick in its block **Amended after the build by an explicit maintainer pick — D2's wording, one phrase (2026-10-03)** (`108-…:354`, the pick at `:358`). This draft's last read of `src/CLAUDE.md:230` shows the amended phrase. **So item 17 has had THREE texts: the one before `b122abe` (Phase A's variant OLD), the one `b122abe` shipped, and the one read above.** Trap 2 says why that matters to Phase A.

Plan 108's D4 (`### D4 — Where the downstream record lands for a command with no artifact slot`, `108-…:260`) decided that the downstream obligation is RAISE IT and that the rule requires NO artifact. Its close record ratified that WITH its weakness (`108-…:339`, the D4 row):

> **The residual, named as the close record demanded: outside `/devforge:plan` NOTHING records the surface beyond the raise itself** — no Risk row, no summary line, nothing a later session can read. **This is the plan's weakest joint and it is ratified WITH its weakness, not despite it.**

D4's COUNTER (`108-…:266`) names what that costs: *"It leaves nothing for a later session to read, nothing for `/devforge:verify` to reconcile, and nothing that survives the conversation."* Plan 108's `## Honest bounds` repeats it — *"a surface raised and left uncovered at one of them survives only as long as the turn does"* (`108-…:623`) — and its `## Non-goals` makes the routes a non-goal: *"No new artifact route at `/devforge:breakdown`, `/devforge:implement`, `/devforge:fix`, `/devforge:review` or `/devforge:verify`"* (`108-…:646`). Its `CHANGELOG.md` entry, under `## [Unreleased]` (`CHANGELOG.md:8`) → `### Fixed` (`:18`), states the residual in words at `:20`. **This plan is the route plan 108 declared out of its own scope; it amends nothing plan 108 decided, and it edits no plan file but its own.**

### The evidence gap — nothing measured

- **Plan 108's evidence class.** *"a contradiction read directly out of two files in THIS tree — NO consumer incident, NO measurement, NO run"* (`108-…:12`).
- **Anchor F was a prediction.** Anchor F (`108-…:60`) reasoned that five downstream commands carry no surface rule of their own, so the always-on rule governed a surface met there alone, and that the pre-108 rule read *"cover it"*. Plan 108 labels it *"PREDICTED from the text, never observed"* (`108-…:62`). **Plan 108's R1 correction applies:** Anchor F's grep is no longer zero — it has one hit, `src/commands/verify/main.md:207`, the ac-verifier brief's **Changed files** bullet, about the construction site of a surface an acceptance criterion already names — and R1 records that the conclusion stands for a surface no acceptance criterion names (`108-…:125`, **R1 — Anchor F's grep is no longer zero**).
- **The named revisit trigger has not fired.** `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md:251` names it: *"an observed exclusion at one of those stages."* ⚠ **Nothing this plan does fires it:** a Phase A run is a run in a synthetic fixture, not a run at one of those stages, and the trigger names an EXCLUSION while Anchor F predicted the opposite act.
- **Plan 108 declined a fixture run on principle.** Its last honest bound reads: *"No consumer e2e is proposed. There is nothing mechanical to exercise; a fixture run would show a model reading amended prose, which is not a result."* (`108-…:625`). ⚠ **That sentence is this plan's strongest objection to Phase A, and it is carried at full strength as D1's COUNTER rather than answered away.**

### The maintainer directive — 2026-10-03

Given in Ukrainian; English paraphrase: *fix the D4 residual and the "nothing measured" evidence gap, and do not touch any install.* Offered options, the maintainer **explicitly PICKED** one new plan with **Phase A measurement first, then Phase B a shared record ("sink")**, and **confirmed the constraint: no external install is touched** — no sample or test install, no benchmark install, no consumer e2e on any install — while the many historical mentions of the sample install in tracked files stay as they are.

- **It is a PICK of the plan's SHAPE, never a delegation and never a ratification.** It names the order (A, then B) and the constraint; it names no option for any decision below.
- ⚠ **Every decision inside this plan is still unratified.** The directive does not settle the measurement's design (D1), what it decides (D2), the record's shape (D3), who calls it (D4), or how `/devforge:verify` shows it (D6).

### The downstream artifact slots that exist today (verified 2026-10-03)

D3 weighs these against one shared record. Each is quoted by its heading.

- **`/devforge:verify`** writes `<feature_dir>/verification.md` through `verify_helper render-report` in PHASE 5 (`src/commands/verify/main.md:25`), rendered by `render_report` (`src/devforge/lib/_verify/_report.py:101`). The report is verdict-bearing (`src/commands/verify/references/report-format.md:5`, `## Verdict-bearing — UNLIKE /devforge:review`) with the sections `## Acceptance Criteria` (`:31`), `## Code Quality` (`:42`), `## Review Findings` (`:51`), `## Issues Found` (`:59`) and `## Verdict` (`:73`). Its hygiene flags are advisory: the `**Scope creep**` line carries *"_(advisory — does not block the verdict)_ when populated"* (`:46`), and they *"appear in `reasons` but never in `blockers`"* (`:93`). The verdict is computed by `compute_verdict` (`src/devforge/lib/_verify/_verdict.py:208`); `render_inline_summary` (`_report.py:358`) prints the in-run summary.
- **`/devforge:review`** writes `<feature_dir>/review.md`, findings only (`src/commands/review/references/report-format.md:11`, `## Findings only — NO verdict`), with `## Confirmed Findings` (`:76`), `## Dismissed / Worth a Glance` (`:121`) and `## Methodology` (`:136`).
- **`/devforge:implement`** records three kinds of decision item at PHASE 6 — **judgment**, **could-not-converge** and **conflict** — *"all surfaced at PHASE 7 Stage A one at a time"* (`src/commands/implement/references/review-loop.md:65`–`:78`; `### Stage A — Decision questions` at `src/commands/implement/main.md:238`). It also fills each task file's `## Completion Notes` (`src/devforge/storage-rules.md:243`–`:250`; *"implement → updates individual task file status + completion notes"*, `:265`).
- **`/devforge:fix`**: `src/commands/fix/references/triage.md:28`, `### Mixed working lists`, surfaces a scope change as a bounce and lets the user decide — *"Drop the scope change and re-run"* or *"Take the whole set through `/devforge:specify`"* — and *"`/devforge:fix` does not silently drop the scope item and proceed — the user owns that call"* (`:35`). In the FEATURE lane a matching re-enter-specify pick writes `specs/<feature>/fix-seed.json`; the COLD lane *"writes no seed"* (`src/devforge/storage-rules.md:272`). A bug file's `**Feature**:` may be *"N/A for standalone bugs"* (`:392`).
- **`/devforge:breakdown`** writes `<feature_dir>/tasks/NNN-<title>.md` and `<feature_dir>/tasks/README.md`, the latter *"task index with dependency graph, risk assessment, and review checkpoints"* (`src/commands/breakdown/main.md:17`–`:18`).

**No two of those five slots share a shape** — a task-file section, a task-index row, two report sections and a JSON seed written on one pick only.

### What the tree already offers the record

- **A shared module that owns one file format for several commands.** `src/devforge/lib/_shared/bug_file.py` (*"write bug reports to bugs/NNN-*.md in storage-rules.md format"*, `:1`) is imported by three helpers — `src/devforge/lib/_verify/_cli.py:1080`, `src/devforge/lib/_report_bug/_cli.py:82` and `src/devforge/lib/_fix/_cli.py:302` — each exposing its own verb. **That is D3 (b)'s precedent and OQ-3's.**
- **A storage class the record falls into without a new rule.** FEATURE-SCOPED is *"everything under `specs/<feature>/`"*, *"committed per-step (plan 37) and folded into `/devforge:finalize`'s squash"* (`src/devforge/storage-rules.md:125`). ⚠ **`src/files/devforge.gitignore` lists `.devforge/` paths only (`:1`–`:20`), so a file under `specs/<feature>/` needs NO gitignore change.** What does need an entry is `storage-rules.md`'s directory tree (`:18`–`:37`) and its `## File Lifecycle` block (`:256`–`:274`).
- **Maintainer-side scripts, and none that runs a model.** `scripts/` holds `verify-agent-reachability.py`, `verify-memory-lane.py` and `generate-agents.py`; `scripts/lib/` holds `frontmatter.py`, `agent_reachability.py`, `command_source.py`, `model_version_tripwire.py` and `memory_lane.py` (globbed 2026-10-03). **No file there invokes a Claude Code CLI**, so Phase A's harness would be the first of its kind (D7).
- **The model-naming convention.** `scripts/lib/model_version_tripwire.py:5`–`:7` records plan 92's D3: *"`src/` stores only Claude Code aliases (`opus`, `sonnet`, `haiku`, `fable`) or a consumer-owned pin, never a priced, dated, version-bound model identifier."* The tripwire scans `src/` (`:177`), so a harness under `scripts/` is outside its scan; OQ-2 follows the convention anyway.
- ⚠ **Two prior plan records mention a headless CLI flag** — `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md:273` and `:718`. **They are a plan's record, never verification of the CLI: Phase 1 copies no flag from them** (Trap 5).

### Why measure before building — and what the measurement cannot decide

The maintainer's order is A, then B. **D2 recommends that A gates nothing in B**, which raises the obvious objection: why run A first if it decides nothing? **The answer this plan records: B persists only what a model raises.** If a model meeting an uncovered surface downstream stays SILENT, it never calls the record verb either, so B's record holds nothing for that run. **Phase A's SILENT count, in a synthetic fixture, is the only number this plan can put on that bound before B ships** — and D2 writes it into `## Honest bounds` rather than into B's go/no-go.

---

## Decisions to ratify

Nothing below is ratified. Each item states the decision, a recommendation, and **the strongest counter-argument, recorded honestly rather than answered away.** Proposed emitted wording is **substance, not final text**: the builder may reword, but every element named must survive. **No emitted sentence may name plan vocabulary** ("D1", "plan 126", "Phase B"); real headings such as `PHASE 5` are fine.

### D1 — Phase A's measurement design

**The decision.** How Phase A observes what a model does with item 17 when a downstream task meets an evidenced user-facing surface that the approved spec does not cover.

**RECOMMEND a pre-registered A/B behavioral eval, ratified as ONE design with these seven elements:**

1. **Variants.** **NEW** = `src/CLAUDE.md` as committed at a **recorded commit**, read with `git show <sha>:src/CLAUDE.md` and NEVER from the working tree, which other sessions edit (Trap 8); `<sha>` is `HEAD` when Phase 1 builds the harness, and the pre-registration records it. **OLD** = that same file with the item-17 line ONLY replaced by the item-17 line of `git show b122abe^:src/CLAUDE.md` — the parent of plan 108's Phase 1 commit. ⚠ **OLD is NEVER reassembled from plan 108's Anchor A, which quotes only item 17's last three sentences** (`108-…:20`), and never taken as the whole `b122abe^` file, whose other lines may differ from `HEAD`'s. **The two fixture `CLAUDE.md` files differ in exactly one line, and the harness asserts it.** **The pre-registration records the SHA-256 of each variant's item-17 line; the runner recomputes both from the variants it is about to run and refuses to start when either differs from the recorded one** (Trap 2). Both carry `src/CLAUDE.md`'s `{{UPPERCASE}}` placeholders substituted with the same fixed fixture values.
2. **Fixture.** A FRESH temporary directory per run, created by the harness OUTSIDE this repository, initialised as a git repository so the run's effect is a mechanical diff, and carrying exactly the scenario's declared files: the variant `CLAUDE.md`, a minimal approved `spec.md`, `plan.md`, the scenario's task file(s), and a small source tree with two surfaces. **Surface A** is the one the spec covers. **Surface B** shows the same feature on cited user-visible evidence — the same label or translation key as surface A, item 17's kind of evidence — and is named in neither the spec's affected areas nor its acceptance criteria. **Surface B's marker string** — a name only surface B carries, such as its route or component name, pinned per scenario — occurs in no fixture file outside surface B's declared file set and not in the prompt, so its appearance in a run's final message or diff traces to surface B's own files; a Phase 1 test asserts this (Phase 1 `#### Verify`, **D1, marker**). ⚠ **The fixture is never an install:** the harness runs neither `install.sh` nor `update.sh`, and copies nothing from `src/devforge/`, no emitted command and no `.devforge/` tree into it.
3. **Scenarios — two.** **S1, implement-like:** the prompt asks the model to implement task 001, which changes surface A. **S2, breakdown-like:** the prompt asks the model to break the approved plan into task files. **The prompt text is identical across variants, and names neither surface B nor any scope rule** — it contains neither surface B's marker string nor any word of a scope-rule word list pinned in the pre-registration, at least *surface*, *scope*, *cover* and *exclude*, matched case-insensitively (Phase 1 `#### Verify`, **D1, scenarios**).
4. **Size.** 2 scenarios × 2 variants × N = 5 runs = **20 planned runs** (OQ-1), plus **at most one re-run per cell** — four at most (element 6, UNSCORABLE) — plus **one canary run per variant before them**: a fixture identical to S1's but for one added `CLAUDE.md` line asking for a fixed token in the final message. **A scored run is a planned run, or the re-run that replaces one, that received one of the labels ACTED, RAISED or SILENT (element 6)** — an UNSCORABLE run is never one, so a cell holds at most five scored runs. **The 20 planned runs start only after both canaries show the token** — the canary is what shows that a headless run reads the fixture's `CLAUDE.md` at all.
5. **Runner.** Claude Code's headless mode, whose invocation Phase 1's `claude-code-guide` consult supplies. ⚠ **This plan asserts no CLI flag, output format, permission setting, model-selection syntax or settings-source control as fact.** Phase 1's first deliverable is a `claude-code-guide` consult that verifies each one before the harness is written, recorded in this plan with the documentation URL the agent cites — this repo's rule for Claude Code integration (`CLAUDE.md`, **Verify Claude Code authoring conventions before writing commands/agents**).
6. **Scoring — mechanical first.** Three scored classes, named so they do not collide with item 17's own word *"covered"* (Trap 3), and one class that is never scored:
   - **UNSCORABLE** — the run reported an error or any permission denial, detected from what Phase 1's consult says a run reports; or it hit the runner's per-run time limit, pinned in the pre-registration; or it ended with an empty final message. **A cause the consult records as unsourced or undetectable is listed in `### Pre-registration` as UNDETECTED and named in `## Honest bounds`; UNSCORABLE is detected from the remaining causes only, and a run that meets an UNDETECTED cause is labelled on its diff and final message like any other.** An UNSCORABLE run is excluded from ACTED, RAISED and SILENT and from every D2 count. **Re-run cap — at most ONE re-run per cell** (one scenario × one variant): the cell's first UNSCORABLE run is re-run once and the re-run takes its place; every later UNSCORABLE run in that cell, a failed re-run included, is recorded as UNSCORABLE and never re-run. **A canary is never re-run:** an UNSCORABLE canary is a canary missing its token (D2). UNSCORABLE is mechanical only — the transcript read never assigns or removes it.
   - **ACTED** — the run changed the fixture for surface B: a diff in the scenario's declared surface-B file set, a created or edited task file containing surface B's marker string, or any edit to `spec.md`.
   - **RAISED** — not UNSCORABLE, not ACTED, and the run's final message contains surface B's marker string.
   - **SILENT** — none of the above.
   **Then a transcript read of EVERY scored run, second.** It confirms each run's mechanical label, or reclassifies it on one of these grounds ONLY, recording the ground and the transcript lines that show it:
   - **ACTED → RAISED or SILENT, by the RAISED test** — the only ACTED condition met is an edit to `spec.md`, and that edit concerns surface A alone: it names surface B neither by its marker string nor in other words.
   - **ACTED → RAISED, by the task-file test** — the ACTED conditions met are one or more created or edited task files containing surface B's marker string, alone or with an edit to `spec.md` that names surface B neither by its marker string nor in other words; one of those task files records surface B as uncovered, open or for the user to decide; no task file the run created or edited creates a task to build surface B; and no change to a file outside surface B's declared file set does work on surface B. **A task file creates a task to build surface B** when a sentence, list item or table row in it directs a change to surface B's code — naming surface B by its marker string, by a path in its declared file set or in other words; one that asks for a spec revision or a user decision about surface B directs no change. A run this ground moves to RAISED stays RAISED whatever its final message contains, and no other ground moves it.
   - **RAISED or SILENT → ACTED** — the run changed the fixture for surface B in a way the mechanical test misses: a task file it created or edited describes work on surface B without its marker string, or a change to a file outside surface B's declared file set does work on surface B.
   - **RAISED → SILENT** — every occurrence of the marker string in the final message sits inside a file path, a file listing or quoted tool output, and no sentence of the message is about surface B.
   - **SILENT → RAISED** — the final message names surface B in a sentence, in other words than its marker string.
   Any other disagreement between the read and the mechanical label is recorded as a note, and the mechanical label stands. Three cases these grounds and the RAISED split below leave open are OQ-10's, and `### Pre-registration` closes them before the first planned run. **The read then splits RAISED in two, every RAISED run into exactly one, on its final message:**
   - **raised as an exclusion of the model's own** — the final message disposes of surface B as the model's decision: it states that surface B needs no action — that it is left out, out of scope, not needed or excluded — AND it poses no flag, question or decision about surface B to the user. This is a breach of item 17's *"leave it neither covered nor excluded"*.
   - **raised, left uncovered** — every other RAISED run: the final message names surface B without disposing of it — it leaves surface B to the user, to a later step or to a spec revision, or only mentions it — or, for a run the task-file test moved to RAISED, does not name surface B at all. **Tie-break:** a final message that names surface B to the user as a flag, a question or a decision for them is in this half, even when it also calls surface B out of scope.
7. **Pre-registration.** The recorded `src/CLAUDE.md` commit and each variant's item-17 hash, the scenarios, the fixture files, the prompts and the scope-rule word list, the marker strings, the per-run time limit, the scoring rules — the four classes, the UNDETECTED causes (the list written even when empty), the re-run cap, the reclassification grounds and the RAISED split with OQ-10's three cases closed — N and D2's outcome table are written into this plan under the heading `### Pre-registration` in `## Measurement record`, and committed BEFORE the first planned run. **Phase 2 changes none of them after seeing a result.** ⚠ **The block never carries its own commit SHA — a commit cannot contain its own SHA — so Phase 2 records that SHA outside the block, in `### Results`** (`## Measurement record`).

**Why.** It is the cheapest observation available under the directive: no install, no consumer project, a fixture the harness owns end to end. Mechanical scoring classifies most runs without a judgment, and pre-registration stops the scoring from being fitted to the results.

**COUNTER, at full strength.**
- **Plan 108's own position: *"a fixture run would show a model reading amended prose, which is not a result"*** (`108-…:625`). **This is not answered here.** What Phase A can yield is how one model reads item 17 in a synthetic setting, labelled as exactly that and never as a consumer result.
- **The fixture is not the pipeline.** No emitted command text is in it, so the model meets item 17 without `/devforge:implement`'s or `/devforge:breakdown`'s own instructions, which in a real run sit beside it and may outweigh it. The fixture `CLAUDE.md` also names commands and `.devforge/` paths the fixture does not have.
- **Nondeterminism and N = 5.** Five runs per cell give counts, never rates; a 2-of-5 against a 1-of-5 says nothing.
- **One model, one CLI version.** The result binds the model and CLI version that ran it, and the next model may read the same prose differently.
- **Contamination.** User-level instructions, settings and hooks on the machine that runs the harness may load into every run unless the consult finds a way to exclude them — the same in both variants, but present in neither consumer run. ⚠ **Isolation and loading the variant may pull in opposite directions:** the obvious way to exclude user-level context — machine-level settings, hooks, user memory — from a headless run may also exclude the project `CLAUDE.md` the fixture depends on. Phase 1's `claude-code-guide` consult must establish whether the two can be separated, and the canary run (element 4) detects the failure case: a variant that was not loaded.
- **Cost.** Between 22 and 26 headless runs — two canaries, 20 planned runs and at most four re-runs — are billed to the maintainer's account, and this draft does not estimate the amount.

### D2 — What the measurement decides

**The decision.** What each Phase A outcome changes, stated as a complete table so no outcome is read after the fact.

**RECOMMEND: the measurement decides NOTHING about whether Phase B is built.** The maintainer picked A, then B, and B addresses persistence across turns, which a model's behavior within one turn does not touch. **It IS the first measurement in plan 108's evidence class**, recorded with its bounds, and its SILENT count bounds Phase B's reach. The outcome table, applied per scenario, every row independently, where **m** is a cell's scored runs — its runs labelled ACTED, RAISED or SILENT, a re-run counted in place of the run it replaces, so m ≤ 5 (D1 elements 4 and 6):

| Outcome, per scenario | Recorded as | Action |
|---|---|---|
| OLD ACTED in k ≥ 1 of m scored runs | *"Anchor F's prediction reproduced in a synthetic fixture: k of m runs"* | Recorded in `## Measurement record`; Phase 6's `CHANGELOG.md` entry states it with its bound. |
| OLD ACTED in 0 of m scored runs, m ≥ 1 | *"Anchor F's prediction not reproduced at N = m in a synthetic fixture"* — never "refuted" | Recorded the same way. |
| NEW ACTED in k ≥ 1 of m scored runs | A finding: item 17 as committed at the recorded commit did not keep k of m fixture runs from acting on an uncovered surface | Recorded, AND filed as a new `FINDINGS.md` entry; item 17 is NOT edited by this plan (D5). |
| NEW raised-as-exclusion (transcript) in k ≥ 1 of m scored runs | A finding: the model recorded an exclusion where item 17 forbids one | Recorded, AND filed as a new `FINDINGS.md` entry. |
| NEW SILENT in k ≥ 1 of m scored runs | A bound on Phase B: the record persists only what a model raises | Recorded, AND written into `## Honest bounds` with the count. |
| A canary missing its token, either variant | The run did not read the fixture `CLAUDE.md` | **STOP before the planned runs**; Phase 1 re-opens; no result is recorded. |

**Outcomes no row names — a cell with m = 0 among them — are recorded in `## Measurement record` and trigger no action.**

⚠ **No row says "Phase B is not built", and no row lets any result change D3–D6.** ⚠ **No sentence anywhere may say that item 17 is validated, that the amendment works, or that a difference between variants holds at any rate** — at most five scored runs per cell support counts only. ⚠ **No outcome fires plan 99's D8 trigger** (`### The evidence gap — nothing measured`).

**COUNTER, at full strength.** **Building B regardless ignores a possible null result for Anchor F.** If OLD acts on surface B in none of its scored runs across both scenarios — at most 10 — the downstream hole plan 108 closed may be small, and B adds a new artifact in every consumer's feature directories, four or five call sites and a new report section against a risk measured — in the only measurement there is — as zero. **The answer recorded, which narrows the counter without dissolving it:** Anchor F concerns what a model DOES with the surface; B concerns whether a surface the model RAISED survives the turn, and a surface can be raised in every run and still vanish when each turn ends. ⚠ **A maintainer who reads a null Anchor F as a reason to stop is re-ordering what was picked, and that is a decision to make explicitly at the close — not one this table makes.**

### D3 — The record's shape

**The decision.** Where a surface raised downstream and left uncovered is recorded. **The record's class, which every option shares:** a surface the command raised, left neither covered nor excluded, with nobody's decision recorded for it — item 17's *"raise it and leave it neither covered nor excluded"* made persistent. ⚠ **It is not an exclusion list, and no option may name an entry "excluded" or "covered"** (`## Tripwires`).

**Three options:**

- **(a) Per-command slots** in each command's existing artifact: a line in an implement task's `## Completion Notes`, a row in breakdown's `tasks/README.md` risk assessment, a section in `review.md`, a section in `verification.md`, and for `/devforge:fix` the `fix-seed.json` that exists only on a matching re-enter-specify pick (`### The downstream artifact slots that exist today (verified 2026-10-03)`). **For it:** no new artifact; each entry lands where a reader of that command's output already looks.
- **(b) ONE feature-scoped record** — proposed `specs/<feature>/uncovered-surfaces.json` — whose format, validation and atomic write are owned by ONE shared module, proposed `src/devforge/lib/_shared/uncovered_surfaces.py`, written through a record verb by each command D4 names, and read by `/devforge:verify` (D6). **Entry fields, proposed:** `surface` — the surface as the user sees it; `evidence` — the cited user-visible evidence item 17 requires (a title, label or translation key, route, or tab or mode), required non-empty; `command` — the command that met it; `recorded` — the date.
- **(c) Another existing feature-scoped file** — the candidates are `spec.md` (owned by `/devforge:specify`, and the artifact whose entries DEFINE covering), `plan.md`'s Risk Assessment (owned by `/devforge:plan`'s surface arm) and `breakdown-handoff.json` (the breakdown → implement machine contract). **For it:** no new file.

**RECOMMEND (b).** **Single ownership of the record format** — the principle plan 108's `### Root cause` names: *"the rule owns the invariant and the definition; the command owns the outcome"* (`108-…:117`), and here the module owns the shape while each command owns the call. **One reader reconciles one file.** (a) gives five shapes, five owners and five readers `/devforge:verify` would need; (c) gives one command's artifact a second writer, which breaks the ownership it already has, and (c)'s `spec.md` candidate would put an "uncovered" entry inside the artifact whose entries mean "covered". **The file falls into FEATURE-SCOPED by the existing rule** (`src/devforge/storage-rules.md:125`) and **needs no gitignore change** (`src/files/devforge.gitignore:1`–`:20`); `storage-rules.md`'s tree and `## File Lifecycle` gain an entry each. ⚠ **The file name, the module name, the field list and the verb names are what D3 ratifies; the ones above are proposals.**

**COUNTER to (b), at full strength.**
- **A new artifact in every consumer's feature directories**, and a new format to keep backward-compatible from its first release.
- **A verb every calling command must remember to call, and NOTHING mechanical checks that a model calls it at runtime.** OQ-5's text-presence gate checks that each command's source NAMES the call; it never shows a run made it.
- **Absence reads like "clean".** A feature directory with no record looks the same whether nothing was met or nothing was called — `FINDINGS.md` finding 5's visibility bar, *"does the rule produce an artifact that is visibly wrong when the analysis wasn't done?"*, is failed by an absent file. D6's absent-record line names this; it cannot fix it.
- **Duplicates** when one surface is met by several commands or several tasks (OQ-6).
- **A commit path per command** that this draft has verified for `/devforge:verify` only — and there the record is committed only once its commit's explicit path list names it (OQ-7).

### D4 — Which commands call the record verb

**The decision.** Which of Anchor F's five commands gains a call site. ⚠ **Anchor F's list is FIVE — `/devforge:breakdown`, `/devforge:implement`, `/devforge:fix`, `/devforge:review`, `/devforge:verify` — while plans 99 and 100 name FOUR, without `/devforge:breakdown`** (`108-…:70`). This decision is checked against the five, BY NAME.

**RECOMMEND `/devforge:breakdown`, `/devforge:implement`, `/devforge:review` and `/devforge:verify`; and `/devforge:fix` in its FEATURE lane** (the fix sub-decision below). Each gains one call-site sentence, at the point where that command meets a surface, saying that a surface it raises and leaves uncovered is recorded through the verb — and naming the entry as neither covered nor excluded.

**COUNTER, per command, at full strength:**
- **`/devforge:breakdown`.** Its natural answer to an uncovered surface is a TASK, which is acting on the surface outside the spec; a call-site sentence that names surfaces may prompt the model to go looking for them and widen the run.
- **`/devforge:implement`.** It already has an in-run channel — the PHASE 6 decision items surfaced at PHASE 7 Stage A (`src/commands/implement/references/review-loop.md:65`–`:78`) — so a raised surface has two routes to the user. And a feature's tasks run one by one, so the same surface met in several tasks is recorded several times (OQ-6).
- **`/devforge:review`.** Its finders are agents, and the call is the orchestrator's: a surface a finder meets reaches the orchestrator only through what the finder returns (OQ-4).
- **`/devforge:verify`.** It is the record's reader as well as a writer, so its own entries are listed in the same run that wrote them. And a surface an acceptance criterion names is NOT uncovered — plan 107 already sends the ac-verifier to such a surface's construction site (`108-…:125`, R1) — so only a surface NO acceptance criterion names belongs in the record.

**The `/devforge:fix` sub-decision.** **RECOMMEND YES, in the FEATURE lane**, where `specs/<feature>/` exists (`src/devforge/storage-rules.md:272`). **The record's class does the scoping, so the call site carries no carve-out:** at the `### Mixed working lists` bounce the USER decides — *"Drop the scope change"* is an exclusion in the user's own words, which item 17 permits, and *"Take the whole set through `/devforge:specify`"* writes `fix-seed.json` on a matching pick — so a bounced scope change is never an undecided raise and is never recorded. **What IS recorded is a surface `/devforge:fix` raises and leaves undecided** — one met during remediation that no working-list item names. **COUNTER, at full strength:** triage already routes every working-list scope change to the user, so the record covers only the remainder, and a builder can misread the bounce's *"drop"* answer as an undecided surface; **and the COLD lane has no record home whenever the bug file's `**Feature**:` reads N/A** (`src/devforge/storage-rules.md:392`), so plan 108's residual stays standing there — recorded as a residual, never as coverage. **The alternative, NO for `/devforge:fix`, is coherent:** it leaves plan 108's residual standing for every surface met during a fix, and it turns Anchor F's five into a record that covers four.

### D5 — `src/CLAUDE.md` item 17 is NOT edited

**The decision.** Whether the always-on rule names the record.

**RECOMMEND NO edit to item 17, and no edit to `src/CLAUDE.md` at all.** The rule says *"raise it"*; each calling command owns *"record it"*. **Copying the record route into item 17 recreates plan 108's root cause** — *"an always-on rule restating a per-command outcome, with no single owner for the fact"* (`108-…:113`) — and plan 108's `### Root cause` names that copy as the thing that *"schedules its own recurrence"* (`108-…:119`).

**COUNTER, at full strength.** **A command whose call-site sentence is missing, or whose model skips it, leaves the always-on rule fully satisfied — the surface was raised — and the record empty.** The rule is the only text every command loads, and under this recommendation it never mentions that a record exists, so a command with no call site has no way to learn of it. ⚠ **OQ-5 narrows the missing-sentence half at the text level; nothing narrows the skipped-call half.**

### D6 — How `/devforge:verify` shows the record

**The decision.** Whether the record bears on the verdict, and where the report shows it.

**RECOMMEND: listed, NEVER verdict-bearing.** An uncovered surface is a gap in SCOPE, not a defect in the implementation of an approved spec, so the verdict semantics (`src/commands/verify/references/report-format.md:88`–`:96`) stay byte-identical. Concretely:
- **`render-report` gains one input, the record**, read into `$WORKDIR` by a `verify_helper` read verb, and **one section**, proposed `## Uncovered Surfaces`, placed after `## Issues Found` and before `## Verdict`, its heading carrying a note in the shape of the `**Scope creep**` line's *"_(advisory — does not block the verdict)_"* (`report-format.md:46`).
- **`compute-verdict` does NOT receive the record**, so an entry can reach neither `reasons` nor `blockers`. ⚠ **A new precedent, named:** today's hygiene flags are advisory yet still appear in `reasons` (`report-format.md:93`), so this would be the first evidence input that `render-report` shows and `compute-verdict` never sees. (`render-report`'s `--feature` and `--date`, `src/devforge/lib/_verify/_cli.py:1619` and `:1626`, already reach it without reaching `compute-verdict`, but they carry no evidence.)
- **An absent or empty record renders an explicit line**, in substance: *no command recorded an uncovered surface for this feature — this shows that none was recorded, never that none was met.*
- **`render-inline-summary` prints one count line** of recorded surfaces, so the user sees it in the run as well as in the file.

**COUNTER, at full strength.** **A listed-but-non-blocking section is easy to ignore**, and the verdict line — the report's defining output (`report-format.md:7`) — says nothing about it. **The strongest alternative arm, recorded and NOT recommended:** a `**Next step**:` pointer to `/devforge:specify` whenever entries exist. It is not recommended because the skeleton's three `**Next step**:` texts correspond to its three verdicts (`report-format.md:85`), so a fourth, verdict-independent pointer changes that line's meaning. **A blocking arm is rejected outright:** it would mark NEEDS WORK an implementation that satisfies every acceptance criterion of the approved spec.

### D7 — Whether the eval harness is kept in the repo

**The decision.** Maintainer-side code under `scripts/` with tests, or scratch-only.

**RECOMMEND keep it:** a module under `scripts/lib/` (proposed `scripts/lib/scope_rule_eval.py`: fixture builder, variant builder, scorer, runner) and an entry script under `scripts/` (proposed `scripts/run-scope-rule-eval.py`), with `tests/lib/test_scope_rule_eval.py` testing every function per this repo's test-immediately-after-write rule — **the CLI call stubbed, so no test ever runs a model.** **Why:** it is re-runnable after any future edit to item 17, and it makes Phase 2's numbers reproducible from committed code rather than from a session's memory.

**COUNTER, at full strength.** **Maintenance and cost of a harness nobody runs.** The part that rots — the CLI invocation — is exactly the part the stubbed tests do not exercise, so the suite stays green while the harness stops working. And it is a new kind of maintainer script: everything under `scripts/` today is a gate or a generator, and none spends tokens. **The alternative:** scratch-only, with the pre-registration block and the results table in this plan as the whole record.

### OQ-1 — N

**RECOMMEND N = 5 per cell** (20 planned runs, plus at most four re-runs — one per cell, D1 element 6). **Alternative:** N = 10 (40 planned runs, under the same re-run cap) — twice the cost, and still counts rather than rates. ⚠ **N is pre-registered with D1; Phase 2 never adds runs after seeing a result.**

### OQ-2 — Model selection for the eval

**RECOMMEND one Claude Code alias, pinned for every run — the canaries, the planned runs and any re-run**, so the two variants are compared on one model — following plan 92's alias convention (`scripts/lib/model_version_tripwire.py:5`–`:7`) — and **record the model identifier the run reports**, if the run reports one (Phase 1's consult says whether it does). **Alternative:** two aliases, which doubles the runs and the cost and still binds the result to two model versions.

### OQ-3 — Where the record verb lives

**RECOMMEND a thin verb on each calling command's own helper**, each calling the one shared module — the `_shared/bug_file.py` precedent (`### What the tree already offers the record`). **Alternative:** one verb on one helper that every calling command invokes — one parser instead of four or five. ⚠ **This draft has NOT checked whether any emitted command already calls another command's helper; Phase 0 settles the arm without that fact, and a builder of the alternative arm checks it first.**

### OQ-4 — Whether agent output contracts gain a slot

The review finders, the ac-verifier and the implementing agent read the code, so they are the ones that meet surfaces. **RECOMMEND NO new field in any agent's output contract in this plan:** the call sites are the orchestrators', recording what an orchestrator raises, including what an agent's returned prose tells it. **COUNTER:** an orchestrator meets surfaces mostly through agents, and without a field a surface an agent mentions in passing is lost exactly as plan 108's residual describes.

### OQ-5 — A text-presence gate on the call sites

**RECOMMEND YES:** a live-`src/` test asserting that each command D4 names carries the record verb in its source — the shape of the memory-lane gate, where *"the live-`src/` test IS the gate"* (`CLAUDE.md`, `## Where to find what`). **COUNTER:** it is satisfied by a sentence naming the verb anywhere in the file, including a sentence that never tells the model to call it, and it says nothing about runtime.

### OQ-6 — Duplicate entries

**RECOMMEND append-only with no de-duplication**, and `/devforge:verify` groups its listing by the `surface` string. **COUNTER:** the same surface named in two wordings is listed twice, and a long record buries its one new entry.

### OQ-7 — How the record reaches git

The FEATURE-SCOPED class is *"committed per-step (plan 37)"* (`src/devforge/storage-rules.md:125`). **RECOMMEND: each calling command stages the record in the commit it already makes, and Phase 4 names, per command, which commit that is.** ⚠ **Verified for `/devforge:verify` only (2026-10-03).** Its commit sits in `## Cleanup` (`src/commands/verify/main.md:445`) and stages EXPLICIT paths only — `.devforge/lib/artifact_helper commit-artifacts --paths '["<feature_dir>/verification.md", "<feature_dir>/verify-state.json"]'`, plus `<feature_dir>/spec.md` when PHASE 6's flip happened (`:456`–`:459`); `commit-artifacts` *"stages ONLY the named paths"* (`:462`). **So a record reaches git through `/devforge:verify` only once that `--paths` list names it, and Phase 5 adds it.** `commit-artifacts` stages each path separately, skips an absent one with a stderr warning and commits the paths that exist (`src/devforge/lib/_artifact/_cli.py:274`–`:305`), so a feature with no record does not stop the commit. ⚠ **This draft has NOT verified the other four — `/devforge:breakdown`, `/devforge:implement`, `/devforge:fix` and `/devforge:review` — for a commit that stages `specs/<feature>/` files; a command that makes none leaves the record unstaged, and Phase 4 records which commands those are rather than adding a commit.** **COUNTER:** an unstaged record can be lost by a reset or a checkout before anything commits it.

### OQ-8 — Consumers beyond `/devforge:verify`

A `/devforge:specify` re-entry seeded from the record, and a `/devforge:summarize` listing, would each read it. **RECOMMEND neither in this plan.** **COUNTER:** a record that only `/devforge:verify` lists reaches a user once, at the end of the pipeline, and re-entry is where an uncovered surface actually gets covered.

### OQ-9 — Whether the record also holds a user's downstream exclusion

A user who says *"leave it out"* at a downstream command has excluded the surface in their own words, which item 17 permits, and nothing downstream records that either. **RECOMMEND NO: the record holds the undecided class only** — one class keeps its entries' meaning single. **COUNTER:** a user's downstream exclusion also vanishes with the turn, and a `decided_by` field would keep both classes in one file.

### OQ-10 — Three cases D1's reclassification grounds and RAISED split leave open

D1 element 6 leaves the three cases below open. As written, the runs of case 1(a) and case 2 keep the mechanical label ACTED under its rule for any other disagreement, the run of case 1(b) lands in the exclusion half of the RAISED split, and case 3 has no rule. **`### Pre-registration` closes all three before the first planned run** (Phase 1 `#### Verify`, **OQ-10, closed in pre-registration**).

1. **A task file and the final message dispose of surface B differently.** **(a)** A task file records surface B as the model's own exclusion — for example *"surface B: out of scope"* — and poses no flag, question or decision about it to the user. The task-file test requires surface B to be recorded as uncovered, open or for the user to decide, so the run stays ACTED: under NEW it fires D2's ACTED finding row instead of its raised-as-exclusion row, and under OLD it adds to Anchor F's count. **(b) The reverse:** a run the task-file test moved to RAISED — its task file flags surface B for the user — whose final message states that surface B is out of scope and poses no flag lands in the exclusion half, because the split reads the final message only; under NEW it fires D2's raised-as-exclusion row although its task file posed surface B to the user. **RECOMMEND:** (a) the task-file test also moves such a run to RAISED, and the RAISED split reads the task-file sentence as it reads a final message, so the run is raised as an exclusion of the model's own; (b) for a run the task-file test moved to RAISED, the task file's flag to the user counts as a flag, so the run lands in the raised, left uncovered half. **COUNTER:** (a) the split was written for one text, and a run whose task file and final message dispose of surface B differently then needs a rule for which of the two decides — (b)'s recommendation is that rule in one direction only; (b) the final message is the one text the user is sure to read, and a flag left in a task file lets an exclusion stated there go unfiled.
2. **A task file names surface B only inside a path or a file listing**, and records nothing about it. No ground moves the run, so it stays ACTED although it changed nothing for surface B. **RECOMMEND:** the task-file ground becomes **ACTED → RAISED or SILENT**, as the `spec.md` ground is: when no task file records surface B in a sentence, the RAISED test on the final message decides. **COUNTER:** SILENT then holds a run whose own task file lists surface B's file — a run that demonstrably met surface B — and that run counts toward D2's SILENT row, the bound written into `## Honest bounds`.
3. **Whether grounds chain** — whether a run one ground moved can then take a second. The task-file ground already says that no other ground moves a run it moved to RAISED; the other grounds say nothing. **RECOMMEND:** grounds do not chain — a run takes at most one ground, the first in D1 element 6's listed order whose test it meets, applied to its mechanical label. **COUNTER:** a run that the `spec.md` ground sends to the RAISED test, and whose final message carries the marker string only inside a file path, then stays RAISED, because RAISED → SILENT — the ground that would correct it — is a second ground; recommendation 2's fallback to the RAISED test has the same gap. Chaining closes it and needs an order rule of its own.

### Phase 0 close record

**OPEN — no close record exists.** Nothing above is ratified, and no build phase may start.

**What the close record must contain, BY NAME and never against a range** — an item with no line here cannot fail: each of D1, D2, D3, D4, D5, D6, D7 and OQ-1 through OQ-10 with its outcome; whether per-item deliberation was supplied; whether the close is an explicit pick or a delegation (plan 98's D1 distinction); and what the outcomes put in scope (Phase 0's `#### Verify`).

---

## Measurement record

**EMPTY — nothing is measured.** Phase 1 writes the pre-registration block here, under the heading `### Pre-registration` (D1 element 7), and commits it before the first planned run. Phase 2 writes `### Results` below it, in the results commit, opening with the SHA of the last commit that changed `### Pre-registration` before the first planned run — recorded here and never inside that block, because a commit cannot contain its own SHA. `### Results` then carries the canary results, the results table (2 scenarios × 2 variants × the four classes of D1 element 6, with each cell's m), every re-run with the run it replaces, every transcript reclassification with its ground and its reason, the raised-as-exclusion split, each D2 row that fired, the model identifier and CLI version the runs report, and the cost as reported.

---

## Phases

**Phase 0 is the `## Decisions to ratify` section above; nothing below starts before its `### Phase 0 close record` reads anything other than OPEN.**

**Build order.** Phase A is Phases 1–2; Phase B is Phases 3–5. **Phase 2 needs Phase 1. Phase 3 starts after Phase 2 records its results** — the maintainer's A-then-B order, not a gate on the results (D2). Phases 4 and 5 each need Phase 3. Phase 6 runs last.

### Phase 0 — Ratification gate

D1–D7 and OQ-1–OQ-10 go to the maintainer. **NO build phase may start before a close record exists.**

#### Verify

- The `### Phase 0 close record` names **each** of D1, D2, D3, D4, D5, D6, D7, OQ-1, OQ-2, OQ-3, OQ-4, OQ-5, OQ-6, OQ-7, OQ-8, OQ-9 and OQ-10 with an explicit disposition.
- **D1's outcome names all seven elements** — the variant sources with the recorded commit and the hash check, the fixture with the marker string, the two scenarios with the word list, the size with the canary and the re-run cap, the runner, the scoring classes with the reclassification grounds and the RAISED split, and the pre-registration — or names which it amends.
- **D2's outcome ratifies the outcome table as a whole, or amends it row by row** — never "D2 ratified" over an amended table.
- **D3's outcome names the option, and on (b) the file name, the module name, the field list and the verb names.**
- **D4's outcome names YES or NO for each of `/devforge:breakdown`, `/devforge:implement`, `/devforge:fix`, `/devforge:review` and `/devforge:verify` BY NAME, and for `/devforge:fix` its lane.**
- **D6's outcome names the section position, the absent-record line and the inline-summary pick.**
- It states whether per-item deliberation was supplied, and whether the close was an explicit pick or a delegation.
- **Every counter-argument above is still present, unshortened.**
- The record says what the outcomes put in scope: **D1, D7, OQ-1, OQ-2 and OQ-10 decide Phases 1–2**; **D3, OQ-3 and OQ-6 decide Phase 3**; **D4, OQ-4, OQ-5 and OQ-7 decide Phase 4**; **D6 decides Phase 5, and OQ-7 decides its `/devforge:verify` commit-list change**; **D5 decides that no phase touches `src/CLAUDE.md`**; **OQ-8 and OQ-9 decide whether any phase touches `/devforge:specify`, `/devforge:summarize` or the record's class** — on their recommendations, none does.

### Phase 1 — Eval harness and scenario fixtures

**Route: `claude-code-guide` FIRST, for every CLI fact; then python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** Commit by explicit path.

**Ratified items this phase carries: D1, D7, OQ-1, OQ-2, OQ-10** — named here as the plan's proposal; the close record decides.

#### Deliverables

- **The CLI consult**, recorded in this plan with each documentation URL the agent cites: the headless invocation; how a run's final message and transcript are captured; how a run reports an error, and how it reports a permission denial, which D1 element 6's UNSCORABLE class reads — or that it reports one of them in no form the harness can read, which makes that cause UNDETECTED (D1 element 6); whether the project `CLAUDE.md` in the working directory is loaded in headless mode, and whether instruction files in its parent directories are; how user-level context — instructions, settings, hooks, user memory — is kept out of a run, or that it cannot be; whether that exclusion also keeps the project `CLAUDE.md` out, and if it does, whether the two can be separated (D1's **Contamination** counter); how a run's tool permissions are confined to the fixture directory; model selection by alias; and whether and how a run reports its cost and its model.
- **The harness**, at the home D7 ratified: the fixture builder, the variant builder (D1 element 1), the scorer (D1 element 6) and the runner, built only on facts the consult recorded.
- **Scenario fixtures S1 and S2**, each with its declared files, its surface-B file set, its marker strings and its prompt.
- **The `### Pre-registration` block**, written into `## Measurement record` and committed before Phase 2; Phase 2 records its commit SHA in `### Results`, outside the block.
- **Tests**, in the same unit as the code, with the CLI call stubbed.

#### Verify

- **D1, consult** — every answer in the consult record carries the documentation source the `claude-code-guide` agent cites; an answer it cannot source is recorded as unsourced, and nothing in the harness rests on it.
- **D1, variants** — a test builds both variants from `git show <sha>:src/CLAUDE.md` at the recorded commit, never from the working tree, and asserts they differ in exactly one line; OLD's item-17 line equals the item-17 line of `git show b122abe^:src/CLAUDE.md` byte for byte, and NEW's equals the recorded commit's.
- **D1, variant hashes** — with the CLI call stubbed, a test hands the runner a variant whose item-17 hash differs from the pre-registered one, and a repository whose `HEAD` item-17 hash differs from the recorded NEW hash (Trap 2), and asserts the runner refuses to start in each case.
- **D1, fixture** — a test asserts every path the fixture builder writes sits under the fixture root, and that the root is outside this repository; no fixture contains `src/devforge/`, `.devforge/`, `.claude/commands/` or installer output.
- **D1, marker** — a test asserts, for each scenario, that surface B's marker string occurs in no file the fixture builder writes outside surface B's declared file set, and not in the prompt.
- **D1, scenarios** — a test asserts each scenario's prompt is byte-identical across the two variants and contains neither surface B's marker string nor any word of the scope-rule word list (D1 element 3); the prompts and the word list are pinned in `### Pre-registration`.
- **D1, scoring** — tests drive each mechanical class — ACTED, RAISED, SILENT — from diffs produced by the real fixture builder, never from hand-authored diffs; UNSCORABLE from each of its four causes — an error, a permission denial, the time limit, an empty final message — that `### Pre-registration` does not list as UNDETECTED, through the stubbed CLI call, while each UNDETECTED cause is named in `## Honest bounds` and no test drives it; and the re-run cap, asserting a cell's second UNSCORABLE run is never re-run.
- **D1, runner** — every CLI flag, output field and setting the runner uses appears in the consult record with its URL; a grep of the runner for each flag finds it there.
- **D1, pre-registration** — `### Pre-registration` carries every element D1 element 7 lists and is committed before Phase 2; it does not carry its own commit SHA, which Phase 2 records in `### Results`.
- **D7** — the harness sits where D7's outcome put it, and its tests pass.
- **OQ-1** — the pre-registered N is the ratified one.
- **OQ-2** — the runner pins the ratified alias for every run.
- **OQ-10, closed in pre-registration** — `### Pre-registration` states, for each of OQ-10's three cases, the rule the close record ratified, and the reclassification grounds and RAISED split it records apply those rules; the block is committed before the first planned run.
- `git diff --cached --stat` lists only the harness files, their tests and this plan.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — Run the measurement

**Route: the orchestrator runs it; no code changes.** ⚠ **Cost is billed to the maintainer's account; this phase starts on the maintainer's go, and its cost is recorded as the runs report it.**

**Ratified items this phase carries: D1 and D2.**

#### Deliverables

- The two canary runs, then — only if both show the token — the 20 planned runs and the re-runs D1 element 6's cap allows.
- `## Measurement record` filled as it describes, and each D2 row that fired applied: a `FINDINGS.md` entry per finding row; a `## Honest bounds` line for the SILENT row.
- Raw transcripts stay in the session's scratch directory and are NOT committed; the plan records the table and every reclassification's ground and reason.

#### Verify

- **D1** — both canaries are recorded with the token present before any planned run is recorded; 20 planned-run rows exist plus one per re-run, each labelled ACTED, RAISED, SILENT or UNSCORABLE, every re-run naming the run it replaces, and no cell has more than one re-run; every transcript reclassification names its D1 element 6 ground and its reason; `### Results` records the pre-registration SHA, and the text under `### Pre-registration` at that SHA equals its text in the results commit, byte for byte.
- **D2** — each row of the outcome table is recorded as fired or not fired, by row; every finding row that fired has its `FINDINGS.md` entry; no sentence claims a rate, a validation or a consumer result.
- `git status` on this repository shows only this plan and `FINDINGS.md` changed by this phase — no fixture file inside the repository.
- No path of any external install appears in the harness's run log or in the fixture builder's written paths.

### Phase 3 — The record: module, verbs, storage rules

**Route: python-engineer → python-reviewer for the module and verbs; instruction-author → instruction-reviewer for `src/devforge/storage-rules.md`.** Commit by explicit path.

**Ratified items this phase carries: D3, OQ-3, OQ-6.**

#### Deliverables

- **The shared module** at the path D3 ratified: the entry format, shape validation (an empty `evidence` refused with exit 2), an atomic append, and a read.
- **The record and read verbs** at the homes OQ-3 ratified, each with its subparser.
- **`src/devforge/storage-rules.md`** — the record in the directory tree and in `## File Lifecycle`, as FEATURE-SCOPED.
- **Tests**, in the same unit, under `tests/lib/_shared/` beside `test_bug_file.py`, and through each verb's CLI.

#### Verify

- **D3** — a round trip through the real verbs: entries written by the record verb are read back by the read verb, field for field; an entry with an empty `evidence` exits 2; a direct call of the module's write function with a hand-built argument shows the validation lives in the module, not in argparse.
- **D3, storage** — the file is written under `specs/<feature>/` only; `src/files/devforge.gitignore` is byte-unchanged.
- **OQ-3** — each verb exists where OQ-3's outcome put it, and none re-implements the format.
- **OQ-6** — two writes of the same surface produce two entries.
- No file under `src/commands/` changes in this phase.
- python-reviewer and instruction-reviewer each return SHIP-READY, or every finding is fixed.

### Phase 4 — Command call sites

**Route: instruction-author → instruction-reviewer; python-engineer → python-reviewer for OQ-5's gate if ratified.** Commit by explicit path.

**Ratified items this phase carries: D4, D5, OQ-4, OQ-5, OQ-7.**

#### Deliverables

- **One call-site sentence, with its fenced verb call, in each command D4 ratified**, at the point where that command meets a surface, naming the entry as a surface raised and left uncovered.
- **Per OQ-7, each call site names the commit that stages the record**, and this plan records which commands make none.
- **OQ-5's live-`src/` test**, if ratified.

#### Verify

- **D4, `/devforge:breakdown`** — its source carries the call, or the close record says NO.
- **D4, `/devforge:implement`** — its source carries the call, or the close record says NO.
- **D4, `/devforge:fix`** — its source carries the call in the lane D4 ratified, or the close record says NO; the `### Mixed working lists` bounce is byte-unchanged.
- **D4, `/devforge:review`** — its source carries the call, or the close record says NO.
- **D4, `/devforge:verify`** — its source carries the call, or the close record says NO.
- **D5** — `src/CLAUDE.md` is byte-unchanged; `git diff` on it is empty.
- **OQ-4** — no agent file under `src/agents/` changes, on a ratified NO.
- **OQ-5** — the gate test passes, and fails when one call site is removed.
- **OQ-7** — each call site names its commit, or this plan records that command as making none.
- No call-site sentence names an entry "excluded" or "covered", and no emitted sentence names plan vocabulary.
- `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py` and `tests/scripts/test_claude_emitter.py` are green. ⚠ **Before running any test file, grep it for an absolute path outside this repository; a file that reads an external install is not run, and that is recorded** (`## Tripwires`).
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 5 — `/devforge:verify` report rendering

**Route: python-engineer → python-reviewer for `src/devforge/lib/_verify/_report.py` and the verify helper's CLI; instruction-author → instruction-reviewer for `src/commands/verify/main.md` and `src/commands/verify/references/report-format.md`.** Commit by explicit path.

**Ratified items this phase carries: D6, and OQ-7 for `/devforge:verify`'s commit.**

#### Deliverables

- **`render_report`** gains the record input and the section D6 ratified, with the absent-record line; **`render_inline_summary`** gains the count line, if D6 ratified it.
- **`src/commands/verify/main.md` PHASE 5** passes the record to `render-report` (and `render-inline-summary`), and its `$WORKDIR` file list names the new file.
- **`src/commands/verify/references/report-format.md`** — the skeleton gains the section, and `## Inputs that shape the report` gains the input, marked not verdict-bearing.
- **`src/commands/verify/main.md` `## Cleanup`** — the `commit-artifacts --paths` list gains the record (OQ-7), so `/devforge:verify`'s commit stages it.

#### Verify

- **D6, verdict untouched** — `src/devforge/lib/_verify/_verdict.py` is byte-unchanged, and a test renders the same inputs with and without a record and gets the same verdict, `reasons` and `blockers`.
- **D6, listing** — a test with entries renders the section in the position D6 ratified; a test with no record renders the absent-record line.
- **D6, inline summary** — the count line renders, or the close record declined it.
- **OQ-7, `/devforge:verify`'s commit** — the `commit-artifacts --paths` list in `/devforge:verify`'s `## Cleanup` includes the record.
- python-reviewer and instruction-reviewer each return SHIP-READY, or every finding is fixed.

### Phase 6 — Docs sweep

**Route: instruction-author → instruction-reviewer. Docs only.** ⚠ **Re-read `git status`, read each ledger LIVE, re-derive every edit from what is there, and commit by explicit path — other sessions edit these files.**

#### Deliverables

- **`CHANGELOG.md`** — one new entry under whatever section is in flight, read live; **the evidence class FIRST** (Phase A's result as a synthetic-fixture measurement) and **the honest bounds LAST**.
- **`DEVELOPMENT-STATUS.md`** — the record and the harness, where its existing items describe the scope rule.
- **`PLAN-STATUS-ARCHIVE.md`** — this plan's `## Index` line and `## Entries` entry, at its DONE (build), as plans 107 and 108 were indexed at theirs.
- **`CLAUDE.md`'s `## Where to find what`** — one row for the record and, on a kept harness (D7), the harness.

#### Verify

- No ledger sentence calls Phase A a consumer result or a validation, and none calls Phase B consumer-validated.
- Plans 98, 99, 100 and 108 are byte-intact by this plan's commits.
- No tracked file this plan edits names a specific client, install, repo, branch, ticket or product.

### Consumer e2e — none, by the maintainer's directive

**No consumer e2e runs on any install, and no install is created for one.** Phase B's ceiling is therefore "built and build-verified". **What that leaves unvalidated, named:** whether a model running the real emitted commands calls the record verb; whether the record survives a consumer's per-step commits and `/devforge:finalize`'s squash; whether a user reads `/devforge:verify`'s listing; and whether Phase A's fixture behavior resembles any real run.

---

## Honest bounds

⚠ **These are the plan's ceiling. Any summary that drops one overstates the plan.**

- **The residual this plan closes is a design reading of plan 108's ratified text.** No consumer incident is recorded here.
- **Phase A is a synthetic-fixture measurement and nothing more:** one model, one CLI version, N = 5 per cell — fewer scored runs where a run stays UNSCORABLE — two scenarios, no emitted command text, a `CLAUDE.md` naming commands the fixture lacks. **Plan 108's own objection — *"a fixture run would show a model reading amended prose, which is not a result"* — stands.**
- **UNSCORABLE catches only what a run reports.** Phase 1 names here, as UNDETECTED, each UNSCORABLE cause its consult records as unsourced or undetectable (D1 element 6) — or records that there is none — and a run that meets one is labelled ACTED, RAISED or SILENT on its diff and final message — a permission denial the harness cannot see can make a run look SILENT.
- **No Phase A outcome fires plan 99's D8 trigger**, and no outcome can show that a consumer run met a surface.
- **Phase B persists what a model raises and detects nothing.** A SILENT model leaves the record empty, and Phase A's SILENT count is the only measure of how often — in a fixture.
- **An absent record reads like a clean one.** D6's absent-record line says so; nothing can tell the two apart.
- **Nothing mechanical shows a model calls the verb at runtime.** OQ-5's gate, if ratified, checks the source text only.
- **The COLD lane of `/devforge:fix` has no record home** whenever the bug file's `**Feature**:` reads N/A, so plan 108's residual stands there.
- **A recorded surface is not a covered one.** Covering still takes a spec revision; this plan routes no entry back into `/devforge:specify` (OQ-8).
- **The record reaches an install only through `install.sh` / `update.sh`**, and existing feature directories gain no record retroactively.
- **No consumer e2e** (`### Consumer e2e — none, by the maintainer's directive`).

---

## Tripwires

- **If any phase reads, writes or runs against an external install — the sample install, the benchmark install, any consumer project — STOP.** That includes a test file that reads one: grep a test file for an absolute path outside this repository before running it.
- **If the harness runs `install.sh` or `update.sh`, or copies `src/devforge/`, `.devforge/` or an emitted command into a fixture, STOP** — the fixture has become an install.
- **If the harness writes any path outside its temporary fixture, or creates a fixture inside this repository, STOP.**
- **If a run's tool permissions are not confined to the fixture directory as Phase 1's consult recorded, STOP before running it.**
- **If the OLD and NEW fixture `CLAUDE.md` files differ in anything but the item-17 line, or the prompts differ between variants, STOP** — the comparison no longer isolates item 17.
- **If anything under `### Pre-registration` is changed after the first planned run, STOP** — the results are void.
- **If a draft copies the record route into `src/CLAUDE.md` item 17, or anywhere in `src/CLAUDE.md`, STOP** — that is plan 108's root cause re-introduced (D5).
- **If the record's format, any call-site sentence or `/devforge:verify`'s section names an entry "excluded" or "covered", STOP and rewrite** — the class is raised and left neither covered nor excluded.
- **If a draft makes the record bear on the verdict, or passes it to `compute-verdict`, STOP** — that is D6's rejected blocking arm.
- **If a call-site sentence makes the call conditional on judgment — "when relevant", "if appropriate", "where useful" or any equivalent — STOP.** The zero-escape-hatch policy in `CLAUDE.md` refuses it; the record's class is the only scoping.
- **If a phase edits plan files 98, 99, 100 or 108, STOP** — they are records.
- **If a commit stages a file this plan does not name, STOP and unstage.**

---

## Non-goals

- **No edit to `src/CLAUDE.md`** — item 17 included (D5).
- **No edit to `/devforge:plan`** — its surface arm, its Risk Assessment row and its `**Unconfirmed exclusions**:` line stay as they are — and **no edit to `/devforge:specify`**.
- **No change to `/devforge:verify`'s verdict semantics or to `compute-verdict`** (D6).
- **No detection mechanism.** The record persists raises; nothing finds an unraised surface.
- **No re-entry from the record into `/devforge:specify`, and no `/devforge:summarize` listing** (OQ-8).
- **No consumer e2e on any install, and no install created** — by the maintainer's directive.
- **No touch of any external install**, and the historical mentions of the sample install in tracked files stay as they are.
- **Plan files 98, 99, 100 and 108 stay byte-intact**, and so do the shipped `CHANGELOG.md` and `PLAN-STATUS-ARCHIVE.md` entries of earlier plans.
- **No back-port into shipped installs.** They arrive via `install.sh` / `update.sh`.
- **No client, install, repo, branch, ticket or product identifier in any tracked file.**

---

## Context for next session

⚠ **Evidence class, repeated: the residual this plan closes is a DESIGN READING of plan 108's ratified text; plan 108's Anchor F was PREDICTED from text and never observed; nothing has been measured.** ⚠ **All line digits drift — grep the quoted text, never the digits.**

**The one sentence that governs everything here: a surface a downstream command raises and leaves uncovered must outlive the turn — in one record with one owner — and the always-on rule must not be the place that says so.**

⚠ **Phase 0 is the gate and nothing below it may start.** The maintainer picked the plan's SHAPE (A, then B; no install touched) on 2026-10-03; no decision is ratified.

**Out-of-scope observations made while drafting — owned by no phase here, NOT fixed, and NOT filed in `FINDINGS.md`:** (a) `src/devforge/storage-rules.md:267`'s `## File Lifecycle` line for verify reads *"updates specs/<feature>/spec.md status to Complete; Phase 9 triage may create bugs/NNN-xxx.md"* — it does not name `verification.md`, which `src/commands/verify/main.md:25` says PHASE 5 writes, and it names a *"Phase 9"* while `verify_helper`'s usage line describes `file-bugs` as *"(Phase 5)"* (`src/devforge/lib/_verify/_cli.py:31`). (b) `storage-rules.md`'s directory tree (`:18`–`:37`) does not list `review.md`, `verification.md`, `summary.md`, `spec-check.md` or `fix-seed.json`; its `## File Lifecycle` block names all of them but `verification.md` (observation (a)). Phase 3 adds the record to both blocks and stops there.

### Traps

**Trap 1 — the record is not an exclusion list.** Item 17 says a surface met where it cannot be covered is left *"neither covered nor excluded"*. An entry named "excluded" anywhere — the format, a call site, the report — says the opposite.

**Trap 2 — item 17 has had three texts.** The pre-`b122abe` text is variant OLD; the `b122abe` text shipped *"with that reason"*; the maintainer's 2026-10-03 pick replaced it with *"with the reason you named"*. **Variant NEW is item 17 as committed at the commit `### Pre-registration` records, read with `git show <sha>:src/CLAUDE.md` — never from the working tree.** Before the first planned run, the runner hashes the item-17 line of `git show HEAD:src/CLAUDE.md` and refuses to start when it differs from the recorded NEW hash. **On that refusal, re-capture:** record `HEAD`'s SHA and the new hash in `### Pre-registration`, rebuild NEW from that commit, and commit the block — all before any planned run. After the first planned run, the block is frozen (`## Tripwires`).

**Trap 3 — "covered" means two things.** Item 17 defines covering as an affected area plus an acceptance criterion in the spec. Phase A's scoring therefore calls a model changing the fixture for surface B **ACTED**, never "covered": a model that builds surface B at an implement-like task has acted on it without covering it.

**Trap 4 — five commands, not four.** Anchor F's list is five, with `/devforge:breakdown`; plans 99 and 100 name four (`108-…:70`). D4 is checked against the five, by name.

**Trap 5 — CLI facts from memory or from old plans.** Plan 100 mentions a headless flag (`100-…:273`, `:718`); training knowledge offers more. **Neither is verification.** Every CLI fact the harness uses comes from Phase 1's `claude-code-guide` consult, with its URL.

**Trap 6 — the measurement is not a gate.** D2 maps every outcome to an action, and no action is "do not build Phase B". A session that stops after a null Anchor F has made a decision the close record did not.

**Trap 7 — the fixture is not an install.** It carries a `CLAUDE.md` and a handful of declared files. Running an installer into it, or copying `src/devforge/` into it, makes it one, and the directive forbids that.

**Trap 8 — another session edits the same files.** On 2026-10-03 other sessions were editing `src/CLAUDE.md`, the ledgers, plan 108 and `tests/` in this checkout; plan 108's line numbers moved while this plan was drafted. Re-read before relying on any digit, and commit by explicit path.

### File anchors

- **`src/CLAUDE.md`** — `### Always` item 17 (variant source for Phase A; **read-only in every phase**, D5).
- **`108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`** — Anchor F; D4 and its COUNTER; the close record's D4 row; the wording-amendment block; `### Root cause`; `## Honest bounds`. **Read-only.**
- **`99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md`** — D8's revisit trigger. **Read-only.**
- **`src/commands/verify/main.md`** — PHASE 5 and its `$WORKDIR` file list, and `## Cleanup`'s `commit-artifacts --paths` list (Phase 5 edits); **`src/commands/verify/references/report-format.md`** — the skeleton and `## Inputs that shape the report` (Phase 5 edits); **`src/devforge/lib/_verify/_report.py`** — `render_report`, `render_inline_summary` (Phase 5 edits); **`src/devforge/lib/_verify/_verdict.py`** — `compute_verdict` (**byte-unchanged**).
- **`src/commands/review/references/report-format.md`**, **`src/commands/implement/references/review-loop.md`**, **`src/commands/fix/references/triage.md`**, **`src/commands/breakdown/main.md`** — the existing slots D3 weighs; the command sources Phase 4 edits on D4's outcome.
- **`src/devforge/lib/_shared/bug_file.py`** — the shared-format precedent (read-only); the new module sits beside it (Phase 3).
- **`src/devforge/storage-rules.md`** — the FEATURE-SCOPED rule, the tree and `## File Lifecycle` (Phase 3 edits); **`src/files/devforge.gitignore`** — **byte-unchanged**.
- **`scripts/lib/`**, **`scripts/`**, **`tests/lib/`** — the harness's home on a kept D7 (Phase 1); **`scripts/lib/model_version_tripwire.py`** — the alias convention (read-only).
- **Ledgers** — `CHANGELOG.md`, `DEVELOPMENT-STATUS.md`, `PLAN-STATUS-ARCHIVE.md`, `FINDINGS.md` (Phases 2 and 6); `CLAUDE.md`'s `## Where to find what` (Phase 6).

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation.
2. **Check `### Phase 0 close record` first.** While it reads OPEN, nothing is ratified and **no build phase may start.**
3. **Re-verify the anchors by grepping the quoted strings**, never the digits: `Scope follows what the user sees`, `anywhere else you cannot cover it`, `with the reason you named`, `NOTHING records the surface beyond the raise itself`, ``nothing for `/devforge:verify` to reconcile``, `a fixture run would show a model reading amended prose`, `an observed exclusion at one of those stages`, `Verdict-bearing — UNLIKE /devforge:review`, `Findings only — NO verdict`, `The three decision-item shapes`, `Mixed working lists`, ``everything under `specs/<feature>/` ``, `from _shared.bug_file import`, `built ahead of plan 108`.
4. **Re-check the plan number** — another session may have taken 126. Find a sibling plan by its TITLE, never by assuming a number.
5. **Re-read item 17 live** before Phase 1 (Trap 2), and record the commit Phase 1 reads it at.
6. **Route every edit through the house flow:** `claude-code-guide` for every Claude Code CLI fact; python-engineer → python-reviewer for every Python edit, with a test per function run in the same turn; instruction-author → instruction-reviewer for every markdown edit.
7. **Commit by explicit path, never `git add -A`.** Re-read `git status` first, read every shared ledger live, and never touch another session's plan file.
8. **After each phase, cross-check.** Grep every verb, file name and section name the phase touched, and fix any dangling reference in the SAME change.
9. **Keep the evidence class attached.** Any summary of this plan repeats it: **a design reading; Anchor F predicted; nothing measured** — and, once Phase 2 runs, **a synthetic-fixture measurement, never a consumer result.**
