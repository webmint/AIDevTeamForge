# 128 — AC Verification-Command Gate Plan

**Created**: 2026-10-03
**Status**: **Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start. Nothing is built and nothing is measured.** Every decision (D1–D10) and every open question (OQ-1–OQ-7) carries a recommendation and its strongest counter-argument or alternative, and each waits for the maintainer. ⚠ **The evidence class, to be repeated in every summary of this plan:** ONE consumer installation, observed and measured by a sibling session, its measurements reported here and NOT re-verified; the 2.0 gap VERIFIED in this tree by grep and by reading the parser on 2026-10-03; NOTHING measured here, no run scored, nothing built. ⚠ **Sequencing.** Plans execute in NUMERIC ORDER, and on 2026-10-03 plans 110–127 sit ahead of this one (F11), so this plan's build waits behind them unless the maintainer directs otherwise (D10). ⚠ **Numbered 128 because a glob of `12[0-9]-*.md` at the repo root on 2026-10-03 returns 120–127 and no 128. Other sessions work in this checkout and may take 128 first; a resuming session re-checks the number before trusting it.** ⚠ **Every `file:line` here was read on 2026-10-03 and will drift — grep the quoted text, never the digits.**

`/devforge:specify` makes every §5.1 (tooling / artifact presence and absence) and §5.7 (hygiene) acceptance criterion carry an executable `--verification-command`, and its helper refuses one without it (F1). **Nothing in the pipeline runs that command.** The spec renders it as a `> Verification:` hint line (F2), the shared AC parser skips that line by design (F3), and `/devforge:verify` hands the ac-verifier agent each AC's id and text only, so in `tests` and `code-only` modes a hygiene criterion is judged by reading the diff (F4). **This plan runs the command twice** — at spec time, where a hygiene command must FAIL, proving the gate can fail (D3), and at verify time, where it must pass, its result an independent blocker (D4) — **and writes both results, with the source tree hash, where the next run can read them** (D3's `> Baseline:` line, D5's report section). It adds no plan-side or breakdown-side lane (D6), no harness directory convention (D7), and never runs a measured command inside `/devforge:implement`'s self-repair loop (D8).

---

## Origin & evidence

⚠ **Evidence class, stated first and repeated in every summary of this plan: ONE consumer installation, observed and measured by a sibling session, its measurements reported here and NOT re-verified; the 2.0 gap VERIFIED in this tree by grep and by reading the parser on 2026-10-03; NOTHING measured here, no run scored, nothing built.**

On 2026-10-03 a sibling session sent two cross-session handoffs. The first analysed a "measurement-first" practice that emerged in one consumer installation (wrapper mode, running the 1.x command layout): before executing tasks, the model there writes self-check scripts, captures baselines, predicts per-task numbers and runs falsification passes. The sibling session traced the practice NOT to any Forge command but to that installation's project-memory file, which had accumulated a method lesson each time a fake gate burned a run. The five lessons that bear on this plan, stated generically:

- **(a)** A grep-based gate must be measured at baseline BEFORE it becomes a done-condition. One gate was written as "returns 0" when the real baseline was 1.
- **(b)** A grep acceptance criterion that passed at its owning task went false at verification, because a LATER task added a test file whose doc comment quoted the old pattern.
- **(c)** Measurement evidence written to a shared temp directory could not be regenerated from the workspace.
- **(d)** The source tree hash belongs in the verification report, so a re-run can prove nothing changed.
- **(e)** A new gate needs a negative control, or it is a tautology.

The sibling session proposed transferring the METHOD to Forge `main` at 1.28.0, as a signal-gated partial plus six one-line edits. **The maintainer redirected on 2026-10-03: *"for a start, into version 2"*.** This plan evaluates the proposal against THIS tree — the 2.0 line — and records what to build. The second handoff concerned the same installation's memory file growing without a size budget on the 1.x line; D9 records what that observation means for 2.0.

**Lesson → decision.** (a) and (e) → D3: the spec-time baseline is the measurement (a) asks for, and its hygiene refusal is the negative control (e) asks for. (b) → D2's path-scoping rule, and D4's verify-time run, which measures after the LAST task rather than at the owning one. (c) → D3 and D5, which keep both measured values in committed files, and D7, which declines a temp-directory convention. (d) → D5.

This repo is public. **This plan names no client, no company, no project or workspace name, no package name, no ticket id, no spec number from that installation and no path outside this repo**, and no phase of it may introduce one. The installation is "one consumer installation (wrapper mode, running the 1.x command layout)"; the session that sent the analysis is "a sibling session".

### The 1.x line — why 2.0 first (re-verified 2026-10-03)

The session that planned this file re-verified these facts on 2026-10-03. `main` is `9eeff96` (2026-04-14) at template version 1.28.0, with no release on `main` since 1.28.0; the 2.0 line shipped 2.0.0 on 2026-06-23 and 2.0.12 on 2026-09-20; `develop-2.0-init` is 953 commits ahead of `main`. On `main`, `update.sh` treats `.claude/commands/specify.md` as templateOwned and overwrites it, so a 1.x backport would clobber that installation's local edits — one reason the maintainer's "2.0 first" holds. That installation's local `specify.md` has carried a "verify numerical claims" rule and a `grep -r <removed-api-name> returns 0 matches` acceptance-criterion suggestion since 2026-04-29; both shapes are on 2.0 today (F7), and the second is the command-then-prose shape F2 finds in this tree's own fixture.

### Verified structure (2026-10-03)

⚠ **Line digits drift — grep the quoted text, never the digits.** Every `file:line` below was read against this tree on 2026-10-03.

**F1 — `/devforge:specify` REQUIRES an executable check on two AC subsections.** `src/commands/specify/main.md:660` is `### Step 4.4 — §5 Acceptance Criteria (7 categorized subsections, EARS notation)`. Its subsection list maps `tooling_artifact_presence` → **5.1 Tooling / artifact presence and absence** *(Ubiquitous only; `--verification-command` required)* at `:696` and `hygiene` → **5.7 Hygiene** *(Ubiquitous only; `--verification-command` required)* at `:702`; the **Subsection-EARS constraints** paragraph (`:680`) closes *"The helper rejects an AC that violates these constraints."* The helper does: `src/devforge/lib/_specify/_cmds_phase4_setters.py:506` `def cmd_add_ac` dies with exit 2 *"requires non-empty --verification-command (Variance rule #10)"* for a subsection in `AC_UBIQUITOUS_ONLY_SUBSECTIONS` (`src/devforge/lib/_specify/_schema.py:105`), and appends the AC record at `:601` with keys `ac_id`, `subsection`, `ears_variant`, `statement`, `verification_command`, `test_anchor`, `n_a_reason`. `src/devforge/lib/_specify/_cmds_phase4_revise.py:140`–`:161` carries the same rule for `revise-ac`. The transport schema `src/devforge/lib/_specify/handoff_schema.py`, `class AcceptanceCriterion` (around `:143`–`:170`), has `verification_command: str` as a required string.

**F2 — The command renders as a hint line, and the shipped fixture stores prose, not a command.** `src/devforge/lib/_specify/_render.py:71`–`:76` renders `  > Verification: <verification_command>` on the line after an AC's `- [ ] **AC-N**: …` checkbox when the command is non-empty. The fixture `tests/lib/fixtures/specify-sample-migration.md` carries **TWO** such lines: `:32`, under AC-1 (§5.1), reads `  > Verification: grep -rE 'lerna' . returns no matches`, and `:57`, under AC-7 (§5.7 Hygiene), reads `  > Verification: find . -name 'yarn-lock' returns no matches`. Each is a command followed by English prose, run from `.` — the whole tree, including the spec directory that itself contains the word — so neither is executable as written and neither is scoped. ⚠ **`:57`'s pattern would not match a file named `yarn.lock`, the lockfile name the same fixture's `## 2. Current State` uses (`:13`), so even as a command it would pass at any baseline — lesson (e)'s tautology, in the shipped fixture.** The sibling `tests/lib/fixtures/specify-sample-migration-state.json` holds the state the fixture renders from: the same two strings as `verification_command` at `:305` and `:359`, and `""` for the other five ACs. The fixture is read by nine test files — `tests/lib/test_specify_helper.py`, `tests/lib/_spec_check/test_cli.py`, `tests/lib/_spec_check/test_consume.py`, `tests/lib/_summarize/test_preflight.py`, `tests/lib/_shared/test_spec_acs.py`, `tests/lib/_finalize/test_preflight.py`, `tests/lib/_verify/test_ac.py`, `tests/lib/_verify/test_report.py`, `tests/lib/_verify/test_specstatus.py` — and by `src/devforge/lib/_verify/_specstatus.py`; `src/commands/specify/main.md` names it (around `:717`) as the migration AC shape.

**F3 — The shared parser SKIPS the hint line, on purpose.** `src/devforge/lib/_shared/spec_acs.py:26` reads *"Non-AC lines (narrative, tables, "> Verification:" hints) are skipped."* `:27`–`:31` gives the reason: the parser captures *"only the first (checkbox) line as ``text`` because that line is the EARS sentence. This matches the AC-verifier agent's contract — it reads the sentence, not the hint."* `_AC_LINE_RE` (`:72`) matches only the checkbox line; `def parse_acs` is at `:82`. `src/devforge/lib/_verify/_cli.py:256` `def cmd_parse_acs` emits that list as JSON, and `src/commands/verify/main.md:185` (`### 3.1`) documents its keys as `id` / `text` / `checked` / `subsection`. `src/devforge/lib/_verify/_ac.py:64` re-exports `parse_acs` from `_shared.spec_acs`, and `src/devforge/lib/_spec_check/_consume.py:88` imports it too; the docstring's relocation note (`:36`–`:42`) records that the parser moved to `_shared/` so both commands consume one copy.

**F4 — Nothing downstream consumes the command.** On 2026-10-03 a grep for `verification[-_]command` over `src/devforge/lib/_verify/`, `src/devforge/lib/_breakdown/`, `src/devforge/lib/_implement/`, `src/agents/ac-verifier.md`, `src/commands/verify/main.md`, `src/commands/breakdown/main.md` and `src/commands/implement/main.md` returned ZERO hits. `src/commands/verify/main.md:199` (`### 3.3 — Dispatch the ac-verifier agent`) hands the agent the AC list as `id` + `text` and classifies each AC by its prose (`frontend` / `backend` / `manual` / code-fallback); in `tests` and `code-only` modes (`:208`–`:213`) every AC, hygiene included, is verified by CODE-READING. **So a §5.7 hygiene criterion is judged by reading the diff, and its own check is never run.**

**F5 — The verdict and the report are deterministic helper outputs with a fixed input set.** `src/devforge/lib/_verify/_verdict.py:208` is `def compute_verdict(ac_results, mechanical_status, review_findings, hygiene, ac_verification_mode, regression, dead_code, e2e)`; its docstring lists the blocker types `constitution_confirmed`, `constitution_contested`, `ac_failure`, `mechanical_failed`, `critical_high_finding`, `medium_finding`, `regression`, `dead_code_unremoved`. In `src/devforge/lib/_verify/_cli.py`, `def cmd_compute_verdict` is at `:657` and `def cmd_render_report` at `:808`; verbs are registered in a `_SUBCOMMAND_REGISTRY` table (entries near `:1194` `check-dead-code-removal`, `:1204` `compute-verdict`, `:1212` `render-report`, `:1241` `regression-gate`), dispatched by `elif verb == …` branches (near `:1474`, `:1502`, `:1586`, `:1748`), and wired by `_register_subcommands` (`:1279`). `tests/lib/_verify/test_preflight.py` pins that registry exactly: `:728` asserts `len(_SUBCOMMAND_REGISTRY) == 16`, and `test_registry_verb_names` (`:730`–`:757`) asserts the full set of 16 names. `src/devforge/lib/_verify/_report.py:101` is `def render_report`, `:358` `def render_inline_summary`. `src/commands/verify/main.md:329` (`### 5.1`) lists the `compute-verdict` flags `--ac-results --review-findings --hygiene --regression --dead-code --e2e --mechanical-status --ac-mode`; `:338` (`### 5.2`) lists the `render-report` flags; `:32` opens the list of orchestrator-written scratch files under `$WORKDIR`. `src/commands/verify/references/report-format.md:11` says `render-report` assembles the report *"from four helper outputs"*, and `:33` is the `| AC | Status | Evidence |` table. **The report carries no tree hash**: a grep for `tree`, `rev-parse` and `hash` over `report-format.md` returned nothing but the table header words.

**F6 — The tree already holds the two mechanisms this plan composes.**
- **(i) A merge-base baseline.** `src/devforge/lib/_verify/_regression.py:335` `def run_regression_gate` is fail-soft — it always exits 0, with statuses `off` / `inconclusive` / `clean` / `baseline-failing` / `regression` — and runs the primary test command at the merge-base in a temp git worktree and again at HEAD (`src/commands/verify/main.md:259`, `### 4.3`).
- **(ii) An absence check.** `src/devforge/lib/_verify/_cli.py:506` `def cmd_check_dead_code_removal` confirms each plan-declared anchor token is ABSENT from its file (`src/commands/verify/main.md:280`, `### 4.4`). Its honest bound tells the reader to *"verify it is a genuine leftover, not an incidental match (a comment, a quoted string, an unrelated symbol name)"* — exactly lesson (b)'s failure class.
- Both feed `compute-verdict` as a blocker only on a violation.
- **The source-root convention.** `resolve_workspace` lives at `src/devforge/lib/_implement/_workspace.py:130` and is imported cross-package by its absolute name, `from _implement._workspace import resolve_workspace`. Outside `_implement` it is imported **function-local** at `src/devforge/lib/_verify/_regression.py:381`, `src/devforge/lib/_verify/_e2e.py:284`, `src/devforge/lib/_report_bug/_cli.py:56` and `src/devforge/lib/_report_ticket/_cli.py:66`, and **at module level** at `src/devforge/lib/_artifact/_cli.py:89` and `src/devforge/lib/_artifact/_cmds_find_artifacts.py:268`. The function-local form, the one `_verify`'s two sites use, is the form a `_specify` setter copies (Trap 5).

**F7 — What 2.0 already has of the sibling session's proposal.**

| Proposal component | State on 2.0 | Where |
|---|---|---|
| "Verify numerical claims" rule | PRESENT | `src/commands/specify/main.md:1030` (IMPORTANT RULE 8) + the `verify-numerical-consistency` verb at Step 4.9 (`:825`) |
| Seven AC categories, §5.1–§5.7 | PRESENT | F1 |
| Signal-gated phases | PRESENT, but routes only to external research | `src/commands/plan/main.md:234` (`### Step 2: Signal Scan`) routes ONLY to Step 3 Deep Research (Context7 / WebSearch, `research.md`), with "No signals found → proceed to Phase 1" |
| A lane: sub-question → plan subsection → seed → breakdown gate → verify check | PRESENT | architect sub-questions 8 (pure builders), 9 (change-induced dead code), 12 (e2e scenarios) at `src/commands/plan/main.md:397` onward → conditional plan subsections → `src/devforge/lib/_plan/handoff_schema.py:318` `class BreakdownSeeds` (`pure_builder_targets`, `dead_code_rows`) → `src/commands/breakdown/main.md:536` `## PHASE 3.5: Integrity gates` (`verify-property-coverage`, `verify-dead-code-coverage`, HARD gates) → `/devforge:verify` 4.4 |
| Bounded memory read cost | BOUNDED | `src/devforge/lib/_shared/memory.py:327` `DEFAULT_EXCERPT_LINES = 120`, section-aware, `## Task Outcomes` excluded at `:339` |
| Memory template and write rubric | Four sections; a three-bucket rubric | `src/devforge/memory.md` (Architecture Decisions, Known Pitfalls, What Worked, What Failed); `src/commands/verify/main.md:372` `## PHASE 7 — Memory update`, *"there is no fourth bucket"* |
| Anchor-token absence grep | PRESENT | F6 (ii) |
| Merge-base baseline in a worktree | PRESENT | F6 (i) |
| **An AC's own check, run at spec time or at verify time; a tree hash in the report** | **ABSENT** | F3, F4, F5 — the gap this plan closes |

**F8 — `/devforge:implement` self-repairs on command output.** `src/commands/implement/main.md:172` is `## PHASE 5: Scope-aware verify + autonomous self-repair`: `implement_helper verify-touched` runs the package's type-check / lint / build / test commands, and on `self_repair` the orchestrator relaunches the implementing agent with `failed_command` + `output`, capped at 3, with *"no human between iterations"*. **A measured count inside that loop would hand an agent the goal "make this number equal N", which it can reach by editing the measurement rather than the code.**

**F9 — Storage facts.** `src/devforge/storage-rules.md:125`: everything under `specs/<feature>/` is FEATURE-SCOPED, committed per step and folded into `/devforge:finalize`'s squash — so any harness directory a feature writes is already committed under the existing rule. The task header fields `**Property targets**:` and `**Dead code removal**:` (`:203`–`:204`) are the two existing lane fields. `src/commands/breakdown/main.md:450`–`:465` (`### Regression-net declaration`) is a prose-line lane that states *"NOTHING CHECKS the declaration"*. `/devforge:verify`'s scratch is `${TMPDIR:-/tmp}/forge-verify`, swept at Cleanup (`src/commands/verify/main.md:445`, `## Cleanup`); its durable record is `<feature_dir>/verification.md`, written by `render-report`.

**F10 — Cost direction.** `124-PIPELINE-COST-REDUCTION-PLAN.md` (a stub) records a measured pre-implement chain cost of 2.3–3.7 h plus 30–60 min of human answers, and that helpers cost turns, not bytes. **Any lane this plan adds must be mechanical, add no `AskUserQuestion` stop, and add at most one helper call per command.** Against that bound: D3 adds no helper call (it runs inside the existing `add-ac` / `revise-ac` calls) and no stop; D4 adds one call, `check-ac-commands`, to `/devforge:verify`; D5 adds flags to two existing calls.

**F11 — Queue.** Open root plans on 2026-10-03: 110 and 111 (Phase 0 OPEN), 112–124 (stubs), 125 DONE (build), 126 and 127 (Phase 0 OPEN). 128 is the next number. Plans execute in numeric order; plan 125 built ahead of the queue ONLY by its ratified D5.

---

## Phase 0 — ratification

Nothing below is ratified. Each item states the question, its options or proposal, a recommendation, what it costs, and the strongest counter-argument, **recorded honestly rather than answered away**. Where a proposal has a weakness that is not its strongest counter-argument, it is recorded as a **Bound, recorded:** line.

### D1 — The shared parser carries the command (F3)

**Proposal:** `_shared/spec_acs.parse_acs` adds two keys to every AC dict — `verification_command` (a string; `""` when no `> Verification:` line follows the checkbox) and `baseline` (a dict, or `null` when no `> Baseline:` line follows; the line's shape is D3's) — by capturing the indented `>` hint lines that immediately follow an AC checkbox line, before the next checkbox or heading. The existing keys `id` / `text` / `checked` / `subsection` are unchanged; **`text` stays the checkbox line alone**, so the ac-verifier contract the docstring states (`:27`–`:31`, *"it reads the sentence, not the hint"*) still holds. The docstring's `:26` sentence is amended to say the two hints are captured into the two new keys.
**Alternative considered:** a second parser inside `_verify` only. Declined: two parsers of one format drift apart, and the relocation note (`:36`–`:42`) records that the parser moved to `_shared/` precisely so commands share one copy.
**RECOMMEND the shared parser** — the single owner; `_verify/_ac.py:64` and `_spec_check/_consume.py:88` both import it. **Cost:** one function extension and its tests.
**Counter-argument, recorded:** **`/devforge:spec-check` consumes the same list**, and a new key is harmless only if its consumer ignores unknown keys. Phase 2's Verify must prove that with `/devforge:spec-check`'s own tests, not assume it.

### D2 — The command's shape rule (F2)

**Proposal:** a `--verification-command` value is a shell command, run with cwd = the source root, whose exit 0 means the criterion HOLDS, with no prose after it. A hygiene (absence) command is anchored on the BROKEN form the change removes and scoped to a path — e.g. `! grep -rqE '<broken-form>' <path>`, never `.`; when test files are excluded, the AC's `--statement` says so. The two fixture lines F2 names are rewritten to that shape, and their `-state.json` sibling is updated, keeping AC ids and counts. **Enforcement:** prose in Step 4.4, plus a new IMPORTANT RULE in `src/commands/specify/main.md` — rule 13, after rule 12 (`:1034`), the last rule of `## IMPORTANT RULES` (`:1021`) on 2026-10-03 — and, mechanically, D3: a command that cannot execute is refused.
**Alternative considered:** keep the value free text and let the ac-verifier agent interpret it. Declined: not mechanical.
**Bound, recorded — the negated form masks a failure to run.** In a POSIX shell, `!` inverts every non-zero status to 0. A `! grep …` whose `grep` is not found (exit 127), or whose path does not exist (`grep` exits 2), therefore reports exit 0 — a PASS. For a hygiene AC, D3's spec-time run still catches both, because the masked failure exits 0 at baseline and D3 refuses a hygiene baseline of 0. **At verify time it does not:** a path that is gone or a tool that is missing reads as PASS, and D4 cannot see exit 127 behind a `!`. The alternative absence form `grep -rqE '<broken-form>' <path>; [ $? -eq 1 ]` keeps "no match" (1) apart from "error" (2), at the cost that a change which deletes the scoped path reads as FAIL. **The close record names the form the rule text uses.**
**RECOMMEND the shape rule as proposed**, with the absence form named at the close. **Cost:** prose in one command file, and two fixture lines with their state.
**Counter-argument, recorded:** **a shell command in a spec runs with the user's privileges at specify time AND at verify time.** This plan cannot make it read-only or sandbox it; the honest bound is that it carries the same trust as `verify-touched`'s configured commands.

### D3 — Spec-time baseline on `add-ac`, which doubles as the negative control (lessons a, e)

**Proposal:** for an AC under `tooling_artifact_presence` or `hygiene`, `add-ac` RUNS the command once — cwd = the source root, resolved through the function-local cross-package import F6 names; timeout per OQ-2 — and stores three fields on the AC: `baseline_exit` (int), `baseline_output_head` (the first 200 characters of combined output) and `baseline_sha` (the short HEAD sha of the source repo). Field names and edge values per OQ-4.
- **`hygiene`:** the baseline exit MUST be non-zero — the broken form must be present NOW. Otherwise `add-ac` exits 2 with *"tautological hygiene gate: the command already passes at baseline — anchor it on the form this change removes"*.
- **`tooling_artifact_presence`:** record only. When the baseline already passes, stderr carries the WARNING *"already true at baseline — this AC pins current state"*, and the exit is 0 (OQ-3).
- **Not executable:** exit 127 / "command not found" → `add-ac` exits 2 with *"verification command is not executable (exit 127): <command>"*. **Timeout** (OQ-2) → `add-ac` exits 2 with *"verification command exceeded the <N> s timeout: <command>"*, `<N>` being OQ-2's ratified value.
- **`revise-ac --verification-command`** re-runs the baseline under the same rules.
- **Render:** `  > Baseline: exit <n> @ <sha> — <output head>`, on the line under `> Verification:` (`_render.py:71`–`:76`). The line renders ONLY when the AC carries a baseline, so a state written before this plan re-renders byte-identically.
- **Transport:** `handoff_schema.AcceptanceCriterion` gains the three fields as OPTIONAL, with defaults, so a pre-128 handoff still deserializes.

**Options for the hygiene rule:** **(a)** refuse (exit 2), as above; **(b)** warn only, and store the baseline.
**Alternative placement considered and declined:** a measurement-only task 001 at `/devforge:breakdown` — the sibling session's shape. It costs a task, an agent dispatch and a review panel, and it leaves the AC's number fictional until that task runs.
**Bounds, recorded.** **(1)** D3 cannot tell a command that fails because the broken form is present from one that fails because it is malformed: a malformed command (anything non-zero other than 127) passes the hygiene baseline. It then fails at verify (D4) — loudly, not silently. **(2)** D3 does not catch the opposite error, lesson (b)'s: a command that fails at baseline because of a match the change will NOT remove. The stored `baseline_output_head` shows the author what matched; D4 fails it at verify. **(3)** A `revise-ac` that runs after the change has landed — whichever command drives it — re-runs the hygiene baseline against a tree that no longer holds the broken form, and is refused.
**RECOMMEND (a).** A hygiene criterion that already passes at baseline is precisely the tautology lesson (e) names. With D4 built, option (b) would let it PASS at verify and enter the report as a MEASURED pass for a fictional reason — a stronger-looking claim than a code-read one. **Cost:** one subprocess call in two setters, three fields, one render line, schema defaults and their tests; no new helper call (F10).
**Counter-argument, recorded:** **a slow command stalls `/devforge:specify`** (OQ-2), and option (a) refuses a legitimate "must never appear" guard written under §5.7. Such a guard belongs under §5.5 Hooks / gates or §5.2 Behavior preservation, and the rule text must say so, or authors will fight the refusal.

### D4 — The `/devforge:verify` gate (F4, F5, F6)

**Proposal:** a new verb, `verify_helper check-ac-commands --acs <acs.json> --source-root <source-root> [--timeout N]` (name per OQ-1), in a new module `src/devforge/lib/_verify/_ac_commands.py`. For every AC whose `verification_command` is non-empty (scope per OQ-7), it runs the command with cwd = the source root, records `exit` and `output_head`, and derives `result`: `pass` (exit 0), `fail` (non-zero), `inconclusive` (timeout, or exit 127). It also records `head_sha` and `tree_sha` (`git rev-parse HEAD^{tree}` at the source root).
- **Fail-soft, like `regression-gate`:** it ALWAYS exits 0. Stdout is JSON `{status: vacuous|clean|violation|inconclusive, rows: [...], pass_count, fail_count, inconclusive_count, head_sha, tree_sha, note}` → `$WORKDIR/ac-commands.json`. Status precedence, proposed here: `vacuous` when no AC carries a command; otherwise `violation` when any row is `fail`; otherwise `inconclusive` when any row is `inconclusive`; otherwise `clean`.
- **Verdict:** `compute-verdict --ac-commands <path>` adds one blocker of a new type, `ac_command_failed`, ONLY on `status: violation`; `inconclusive` yields a reason line only. Its treatment under `ac_verification_mode=off` is OQ-6.
- **Independence:** the agent's own AC status is NOT overridden. The command result is an independent blocker, because the agent is dispatched in PHASE 3, before PHASE 4 runs.
- **Spec text:** `src/commands/verify/main.md` gains `### 4.6 — Acceptance-criteria command check` after `### 4.5 — e2e run` (`:301`) and before `## PHASE 5` (`:321`), modelled on 4.3's branch-on-status prose. The `## PHASE 4` heading (`:225`), which names each 4.x step, gains the new one; `### 5.1` (`:329`) and `### 5.2` (`:338`) gain the flag; the scratch-file list (`:32`) gains `ac-commands.json`; `### 3.1` (`:185`) lists the two keys D1 adds; and `## Important rules` (`:471`, items 1–11 on 2026-10-03) gains item 12 — the gate's statuses and what each does to the verdict, in the shape of items 10 and 11, with D8's tripwire sentence.

**RECOMMEND as proposed.** **Cost:** one module, one verb, one verdict parameter, prose.
**Counter-argument, recorded:** **the gate proves an exit code, not that the command measures the right thing.** D2's shape rule is prose, and D3's hygiene refusal is the only mechanical tooth behind it.

### D5 — The report records the tree and the measured rows (lesson d)

**Proposal:** `render-report --ac-commands <path>` renders `**Source tree**: <tree_sha> @ <head_sha>` in the report's header block, and a new `## Measured Acceptance Criteria` section — the table `| AC | Command | Baseline (exit @ sha) | Verify (exit) | Result |` — placed after `## Acceptance Criteria`. When the status is `vacuous` the section reads *"_No acceptance criterion carries a verification command._"* `render_inline_summary` (`_report.py:358`) adds one count line. `references/report-format.md` documents the new input — its `## Inputs that shape the report` list (`:9`), whose lead-in *"from four helper outputs"* (`:11`) becomes five — and the new section, with a semantics paragraph shaped like its `## Regression gate` one (`:98`).
**⚠ Precedent this sets in `report-format.md`.** The regression gate's heading there reads *"(folds into the verdict — no dedicated rendered section)"* (`:98`), and the 4.2 hygiene result renders as lines of the Code Quality block (`:16`). D5 gives a PHASE 4 result a section of its own. The justification: the baseline and verify values ARE the record lesson (d) asks for, and a verdict reason line cannot hold a table.
**Bound, recorded:** `HEAD^{tree}` names the COMMITTED tree. An uncommitted edit present when the commands run is not in it, and this plan does not check for one.
**RECOMMEND as proposed.** **Cost:** small.
**Counter-argument, recorded:** **the baseline sha is the spec-time HEAD, and the verify sha is now.** After a rebase neither equals the merge-base, and this plan does NOT re-measure at the merge-base — the regression-gate worktree (F6 i) is not reused. That is an honest bound, and a possible later lane.

### D6 — No plan-side or breakdown-side lane (F7, F10)

**Proposal — decline:** no Signal Scan row (that table routes to external research), no architect sub-question 13, no `BreakdownSeeds` field, no breakdown gate, no task header field, no measurement-only task. The signal is MECHANICAL — an AC carries a command — so no LLM-judged signal is needed, and F10's cost direction weighs against every added step.
**RECOMMEND decline.** **Cost:** none.
**Counter-argument, recorded:** **with no "Baseline & Measurement" plan subsection, a plan may promise a number that no AC carries**; that gap is visible only to a human reading the plan.

### D7 — No harness / baseline / verify directory conventions, no scratch-overlay dry-run (F9, F10)

**Proposal — decline.** The baseline value lives on the AC (D3) and the re-run in `verification.md` (D5), never in a temp directory (lesson c); `/devforge:verify`'s own scratch is swept at Cleanup (F9). Harness scripts a project writes are already FEATURE-SCOPED under `specs/<feature>/` and committed under the existing rule (F9), so they need no new one.
**RECOMMEND decline.** **Cost:** none.
**Counter-argument, recorded:** **the installation's largest wins came from measuring the final code shape BEFORE planning** — as the sibling session reports it, every number predicted and zero self-repair across a six-task feature. D3 and D4 do not deliver that; it stays a project practice.

### D8 — Measured commands never enter `/devforge:implement` (F8)

**Proposal:** `verify-touched` and its self-repair loop do not run AC commands. The check runs at `/devforge:verify` only, where Important rule 2 (`src/commands/verify/main.md:474`) forbids fixing code; a failed command becomes NEEDS WORK and a `/devforge:fix` cycle. A tripwire sentence says so in `## Important rules` item 12 of `src/commands/verify/main.md` and in this plan's Trap 9.
**RECOMMEND as proposed.** **Cost:** one sentence of spec text.
**Counter-argument, recorded:** **a per-task failure now costs a `/devforge:fix` cycle instead of one self-repair iteration.**

### D9 — Memory: no template section, no rubric change; record the 2.0 consolidation gap

- **(a) Decline** the sibling session's "Gates & measurement" memory-template section. The 2.0 excerpt is budgeted and section-aware (F7), the PHASE 7 rubric has three buckets, and method lessons belong under What Worked / Known Pitfalls. Once the method is in the framework, those entries are prunable in the installation.
- **(b) Record** the second handoff's observation — the memory file has no size budget and no consolidation step — because it holds for 2.0's WRITE side too: `/devforge:finalize` only READS `.devforge/memory.md` (its preflight carries the same bounded excerpt, `src/devforge/lib/_finalize/_preflight.py:246`–`:250`, into the tech-writer brief (`src/commands/finalize/main.md:138`)) and COMMITS it in its unconditional safety-net commit (`src/commands/finalize/main.md:166`–`:169`); nothing writes it back consolidated, prunes it or budgets it, so only the READ side is bounded. It becomes a new numbered `FINDINGS.md` entry in Phase 4, on plan 125's D4 precedent (an entry with *"no plan file, no owner"*), not a build item here.

**RECOMMEND (a) decline and (b) record.** **Cost:** one `FINDINGS.md` entry.
**Counter-argument, recorded:** **the excerpt bounds what a session READS, not what the file becomes**; a growing file still shapes the 120 lines that survive.

### D10 — Queue position (F11)

128 builds after 110–127, in numeric order.
**RECOMMEND no jump.** **Cost:** the gap stays open until the queue reaches 128.
**Counter-argument, recorded:** **the gap is shipped and silent** — no AC's own command has ever been run by the pipeline (F4), so every hygiene AC written since the seven categories landed was judged without its check — and plan 125 is a precedent for a ratified jump. **The maintainer decides.**

### OQ-1 — The verb's name

`check-ac-commands` matches `check-hygiene` and `check-dead-code-removal`.
**RECOMMEND `check-ac-commands`.** **Alternative:** `measure-acs`.

### OQ-2 — The per-command timeout

**RECOMMEND a fixed 120 s**, as the D4 verb's `--timeout` default and as `add-ac`'s limit. On timeout `add-ac` exits 2 with D3's timeout message and the D4 verb records `inconclusive`. **Alternative:** a configurable timeout — a new config key, which nothing else in this plan needs.

### OQ-3 — `tooling_artifact_presence` already passing at baseline

**RECOMMEND warn-and-record**, as D3 states: a §5.1 presence criterion whose artifact already exists legitimately pins current state. **Alternative:** refuse, like hygiene.

### OQ-4 — Field names, the render line, and two edge values

Field names `baseline_exit`, `baseline_output_head`, `baseline_sha`; render line `  > Baseline: exit <n> @ <sha> — <head>`. The maintainer may rename either. Two edge values D3 leaves open, with recommendations:
- **The output head can hold newlines and the separator ` — `.** **RECOMMEND** that the stored head collapse each whitespace run to one space, so the render stays one line, and that D1's parser split on the FIRST ` — ` only.
- **A source root with no HEAD** (not a git repository, or no commit yet) has no sha. **RECOMMEND** `baseline_sha` `""`, rendered as `@ (no HEAD)`. **Alternative:** refuse `add-ac` when the source root has no HEAD.

### OQ-5 — Which `CHANGELOG.md` sub-heading the entry goes under

`## [Unreleased]` (`CHANGELOG.md:8`) carries `### Changed` (`:10`) and `### Fixed` (`:18`) on 2026-10-03. This is a feature.
**RECOMMEND `### Changed`**, as a `feat(specify,verify): …` line. **Alternative:** `### Fixed`, reading the silent gap as a defect (D10's counter-argument).
⚠ **Re-verify LIVE at build time, and never edit a released version block.**

### OQ-6 — `ac_command_failed` under `ac_verification_mode=off`

Under `off`, *"AC failures are advisory (they appear in `reasons` but do not block)"* (`src/commands/verify/references/report-format.md:94`). D4 does not say whether a measured failure follows that rule.
**RECOMMEND that it does:** under `off`, a `violation` adds a reason line and no blocker — the user chose advisory ACs, and the measured command is an AC's own check. **Alternative:** block in every mode, so a check the user switched to advisory still blocks when it is measured.

### OQ-7 — Specs written before Phase 1: does D4 run a command with no `> Baseline:` line?

A spec written before Phase 1 carries `> Verification:` values in whatever shape its author used — the shipped fixture teaches command-then-prose (F2) — and no `> Baseline:` line. Under D4 as written, the first `/devforge:verify` after an update runs those values; a prose tail makes the command fail, and an in-flight feature turns NEEDS WORK for a reason unrelated to its code.
**RECOMMEND** that D4 runs only ACs that carry a baseline: the `> Baseline:` line is the proof the command executed at spec time. A command-bearing AC without one becomes a row with result `unbaselined`, counted in an `unbaselined_count`, never a blocker and never `inconclusive`; D5's table shows it. Status precedence is unchanged: `vacuous` means no AC carries a command AFTER the `unbaselined` rows are counted, so an all-unbaselined spec reports `clean` with `unbaselined_count` > 0 and D5 renders its table with those rows. D4's JSON gains `unbaselined_count` when this recommendation is ratified. **Alternative:** run every non-empty command, as D4 states, and accept that pre-128 specs with prose values turn NEEDS WORK on their first verify after the update.

### Phase 0 close record

**OPEN — nothing ratified.** No decision and no open question above has an outcome, and **no build phase may start.** ⚠ **Nothing is built and nothing is measured.**

When the record closes, it is written in the shape of plan 125's close record (`125-VERIFY-FILE-BUGS-IMPORT-PLAN.md`, `### Phase 0 close record`): the occasion; the directive, with any non-English directive given in English translation; the pick-or-delegation classification per `98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md`'s D1 distinction; and an outcomes table.

#### Verify

- The record names **each** of D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, OQ-1, OQ-2, OQ-3, OQ-4, OQ-5, OQ-6 and OQ-7 with an explicit outcome (ratified / amended / declined), **checked BY NAME, never against a range**.
- **D2's outcome names the absence form** the rule text uses: `! grep …`, or `…; [ $? -eq 1 ]`.
- **D3's outcome states the hygiene option explicitly: (a) refuse or (b) warn**, and names the three exit-2 message texts (tautology, not-executable, timeout) as ratified or amended.
- **D9's outcome states (a) and (b) separately.**
- **D10's outcome states jump or no jump explicitly**, and on a jump names the plans 128 builds ahead of.
- **OQ-5's outcome names the sub-heading. OQ-7's outcome states whether D4 runs unbaselined commands.**
- **Each outcome states whether it is an explicit maintainer pick or a delegation.**
- **Every counter-argument, every Bound line and every Alternative above is still present, unshortened.** Phase 0's lead-in *"Nothing below is ratified."* stays as written, with a dated parenthetical beside it naming the close.

---

## Phases

Phase 0 is the section above; **nothing below starts before its close record exists.** **Build order: Phase 1 → Phase 2 → Phase 3 → Phase 4** — the producer, then the parser, then the consumer, then the ledgers. Phase 2 follows Phase 1 because its tests round-trip through Phase 1's producer. Phase 3 follows Phase 2 because the D4 verb reads the keys Phase 2 adds. Phase 4 records what Phases 1–3 built.

Every phase commits by explicit path — **never `git add -A`** — because another session builds in this checkout. Commit subjects take the `<type>(plan-128): Phase N — …` form, matching the `docs(plan-108): Phase 3 — …` style `git log --oneline -5` shows on 2026-10-03.

**House rules for every phase.**
- Python edits route **python-engineer → python-reviewer**, and markdown edits route **instruction-author → instruction-reviewer**; each loop runs until its review is clean.
- Every helper function gets its own test, written AND run in the same turn.
- Parser tests round-trip through the REAL producer — `specify_helper add-ac` → render → `parse_acs` — never through hand-authored fixtures alone.
- A test that runs a verification command runs it in a temp git repository the test builds, with a file it controls — never against this repo's tree, whose content changes under the test.
- Exact test output is read via `rtk proxy` plus a file redirect, never from the display (Trap 10).
- After each phase, `git show --stat` lists only that phase's files and this plan.

### Phase 1 — Producer: the shape rule and the spec-time baseline (D2, D3, OQ-2, OQ-3, OQ-4)

**Route: python-engineer → python-reviewer for the Python, test and fixture files; instruction-author → instruction-reviewer for `src/commands/specify/main.md`; each loop runs until its review is clean.**

#### Deliverables

- **`tests/lib/_specify/test_ac_baseline.py`** — new, written FIRST: D3's hygiene refuse path, run RED against the unchanged setter (Trap 7), then the accept path, the not-executable path, the timeout path and the §5.1 warning path.
- **`src/devforge/lib/_specify/_cmds_phase4_setters.py`** — `cmd_add_ac` (`:506`) runs the baseline for `tooling_artifact_presence` and `hygiene` under D3's ratified rules, with OQ-2's timeout, and appends the three fields with the AC record (`:601`). The source root comes from `resolve_workspace`, imported function-local in the form F6 names (Trap 5).
- **`src/devforge/lib/_specify/_cmds_phase4_revise.py`** — `revise-ac` (`:140`–`:161`) re-runs the baseline when `--verification-command` is given, under the same rules.
- **`src/devforge/lib/_specify/handoff_schema.py`** — `AcceptanceCriterion` (around `:143`–`:170`) gains the three fields as optional, with defaults.
- **`src/devforge/lib/_specify/_render.py`** — the `> Baseline:` line under `> Verification:` (`:71`–`:76`), in OQ-4's ratified shape, rendered only when the AC carries a baseline.
- **`src/commands/specify/main.md`** — in Step 4.4 (`:660`): D2's shape paragraph with the absence form D2's outcome names; the baseline semantics; each exit-2 message verbatim; the note, from D3's counter-argument, that a "must never appear" guard belongs under §5.5 or §5.2, not §5.7; and the sentence, from D2's counter-argument, that the command runs with the user's privileges at specify time and at verify time (Trap 6). In `## IMPORTANT RULES`: rule 13, after rule 12 (`:1034`).
- **The fixture pair.** `tests/lib/fixtures/specify-sample-migration.md` `:32` (AC-1) and `:57` (AC-7) are rewritten to D2's shape, each followed by its `> Baseline:` line; `tests/lib/fixtures/specify-sample-migration-state.json` `:305` and `:359` are updated to match and gain the three fields. AC ids, the AC count and every other line stay unchanged (Trap 4). AC-7 is a hygiene AC, so its recorded baseline exit is non-zero.
- **Existing callers of `add-ac`.** On 2026-10-03 `--verification-command` appears 15 times under `tests/` — 14 in `tests/lib/test_specify_helper.py`, 1 in `tests/lib/_specify/test_landing.py`. Under D3 each such call on a §5.1 or §5.7 AC now RUNS its command; a call whose command cannot execute, or whose hygiene command passes at baseline, now exits 2. Each such call is updated in this phase to a command that behaves as the test intends, never deleted.
- **Tests:** `tests/lib/test_specify_helper.py` (add-ac, revise-ac), `tests/lib/_specify/test_handoff_schema.py` (a pre-128 handoff still deserializes), `tests/lib/_specify/test_ac_baseline.py`.
- **This plan** — `#### Phase 1 record` below.

#### Verify

- **RED first.** The new refuse-path test asserts exit 2 and D3's tautology message; against the unchanged setter it fails because `add-ac` exits 0 and stores the AC. **A red caused by an argparse error, a fixture error or a typo does not count** (Trap 7). The RED is recorded with the command that produced it.
- **Hygiene, accept:** `add-ac --subsection hygiene` with a command that FAILS in the test's temp repo → exit 0, and the three fields are stored with the AC.
- **Hygiene, refuse:** the same with a command that PASSES → exit 2 with D3's quoted message, and no AC is stored.
- **Not executable:** a command that exits 127 → exit 2 with D3's not-executable message, and no AC is stored.
- **Timeout:** a command that outlasts the timeout (the test lowers it) → exit 2 with D3's timeout message, and no AC is stored.
- **§5.1:** `--subsection tooling_artifact_presence` with a passing command → exit 0, the stderr WARNING, and the three fields stored.
- **`revise-ac --verification-command`** re-runs the baseline under the same rules, and its refuse path stores nothing.
- **Render:** the `> Baseline:` line sits directly under `> Verification:`; a state with no baseline fields renders byte-identically to its pre-Phase-1 render.
- **Transport:** a pre-128 handoff, with no baseline fields, deserializes.
- **The nine fixture-reading test files** (F2) are green.
- **Targeted first:** `python3 -m pytest tests/lib/_specify tests/lib/test_specify_helper.py -q` is green. **Then the full suite:** `python3 -m pytest tests/lib -q` is green.
- **Grep:** `grep -rn 'Baseline:' src/` returns the render site and the spec text only (it returned nothing on 2026-10-03).
- `git show --stat` lists only this phase's files.
- python-reviewer and instruction-reviewer each return SHIP-READY, or every finding is fixed.

#### Phase 1 record

**NOT STARTED.**

### Phase 2 — Parser (D1)

**Route: python-engineer → python-reviewer, looping until the review is clean.**

#### Deliverables

- **`src/devforge/lib/_shared/spec_acs.py`** — `parse_acs` (`:82`) captures the hint lines after each checkbox line (`_AC_LINE_RE`, `:72`) into D1's two keys, parsing the `> Baseline:` line in OQ-4's ratified shape; `text` is unchanged. The docstring's `:26` sentence and the `:27`–`:31` paragraph are amended to say what is now captured, and that `text` stays the EARS sentence the ac-verifier agent reads.
- **`tests/lib/_shared/test_spec_acs.py`** — the new keys, round-tripped through Phase 1's real producer (`add-ac` → render → `parse_acs`), plus a spec with no hint lines.
- **This plan** — `#### Phase 2 record` below.

⚠ **Between this phase's commit and Phase 3's, `src/commands/verify/main.md` `### 3.1` (`:185`) under-lists `parse-acs`'s keys.** Phase 3 closes that gap; a session that stops between the two phases leaves it open and must say so in `#### Phase 2 record`.

#### Verify

- **`verify_helper parse-acs`** on the rewritten fixture emits `verification_command` and `baseline` for AC-1 and AC-7, and `""` / `null` for AC-2 through AC-6.
- **`text` is unchanged:** for every AC of that fixture, `text` is byte-identical to its value before this phase.
- **Consumers ignore the new keys:** `tests/lib/_verify/test_ac.py`, `tests/lib/_spec_check/test_consume.py` and `tests/lib/_fix/test_fix_helper.py` are green **with no edit to any file under `src/devforge/lib/_spec_check/` or `src/devforge/lib/_fix/`** — `git show --stat` proves the second half.
- **Targeted first:** `python3 -m pytest tests/lib/_shared tests/lib/_verify tests/lib/_spec_check tests/lib/_fix/test_fix_helper.py -q` is green. **Then the full suite:** `python3 -m pytest tests/lib -q` is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 2 record

**NOT STARTED.**

### Phase 3 — Consumer: the gate, the verdict, the report (D4, D5, D8, OQ-1, OQ-6, OQ-7)

**Route: python-engineer → python-reviewer for the Python and test files; instruction-author → instruction-reviewer for `src/commands/verify/main.md` and `src/commands/verify/references/report-format.md`; each loop runs until its review is clean.**

#### Deliverables

- **`src/devforge/lib/_verify/_ac_commands.py`** — new: D4's runner, fail-soft, with D4's status precedence, OQ-2's timeout default and OQ-7's ratified scope.
- **`src/devforge/lib/_verify/_cli.py`** — a `_SUBCOMMAND_REGISTRY` entry for the verb OQ-1 names (neighbours near `:1194`–`:1241`); its `elif verb == …` dispatch branch (neighbours near `:1474`–`:1748`); and `--ac-commands` on `cmd_compute_verdict` (`:657`) and `cmd_render_report` (`:808`).
- **`src/devforge/lib/_verify/_verdict.py`** — `compute_verdict` (`:208`) gains an `ac_commands` parameter with a default, so every existing caller is unchanged; the `ac_command_failed` blocker on `violation`; OQ-6's mode rule; and the new type in its docstring's blocker list.
- **`src/devforge/lib/_verify/_report.py`** — `render_report` (`:101`) renders D5's `**Source tree**:` line and `## Measured Acceptance Criteria` section; `render_inline_summary` (`:358`) adds D5's count line.
- **`tests/lib/_verify/test_preflight.py`** — the registry pins move with the new verb: `:728`'s count 16 → 17, `test_registry_verb_names`' expected set (`:734`–`:755`) gains the verb with a plan-128 comment in its neighbours' style, and its docstring's *"all 16 verb names"* (`:731`) → 17 (Trap 12).
- **`src/commands/verify/main.md`:**
  - `### 4.6 — Acceptance-criteria command check`, between `### 4.5 — e2e run` (`:301`) and `## PHASE 5` (`:321`), modelled on 4.3's branch-on-status prose, with the privileges sentence Phase 1 adds to Step 4.4 (Trap 6);
  - the `## PHASE 4` heading (`:225`) names the new step;
  - `### 3.1` (`:185`) lists D1's two keys;
  - `### 5.1` (`:329`) and `### 5.2` (`:338`) gain `--ac-commands`;
  - the scratch-file list (`:32`) gains `ac-commands.json`;
  - `## Important rules` gains item 12 — the gate's statuses and what each does to the verdict, in item 10's shape, plus D8's tripwire sentence: the check runs at `/devforge:verify` only, never inside `verify-touched` or `/devforge:implement`'s self-repair loop.
- **`src/commands/verify/references/report-format.md`** — the inputs list (`:9`) gains the new input, and its lead-in *"from four helper outputs"* (`:11`) → five; the skeleton gains the `**Source tree**:` line and the new section after `## Acceptance Criteria` (`:31`); a "Measured acceptance criteria" semantics paragraph is added, shaped like the `## Regression gate` one (`:98`).
- **Tests:** new `tests/lib/_verify/test_ac_commands.py`; `tests/lib/_verify/test_verdict.py`; `tests/lib/_verify/test_report.py`.
- **No emitter change:** no new command and no new reference file.
- **This plan** — `#### Phase 3 record` below.

#### Verify

- **RED first** for the blocker: the new `compute-verdict` test asserting one `ac_command_failed` blocker on `violation` fails against the unchanged verdict code for that reason, and no other.
- **Fail-soft:** tests prove that a timeout and an exit 127 each yield `inconclusive` with exit 0, and that the verb exits 0 on every path.
- **Verdict:** `violation` → `compute-verdict` adds exactly one `ac_command_failed` blocker and the verdict is NEEDS WORK; `clean`, `vacuous` and `inconclusive` leave the verdict unchanged; under `ac_verification_mode=off`, the behaviour OQ-6's outcome names.
- **OQ-7:** a test proves the ratified behaviour for a command-bearing AC with no baseline.
- **Report:** the rendered report carries `**Source tree**:` and the table; a `vacuous` status renders D5's sentence.
- **Grep:** (`<verb>` is the name OQ-1's outcome ratifies) `grep -rn '<verb>' src/` returns hits only under `src/devforge/lib/_verify/`, in `src/commands/verify/main.md` and in `src/commands/verify/references/report-format.md`.
- **Grep (D8):** `grep -rn 'ac-commands\|ac_commands' src/devforge/lib/_implement/ src/commands/implement/` returns nothing.
- **Targeted first:** `python3 -m pytest tests/lib/_verify -q` is green. **Then the full suite:** `python3 -m pytest tests/lib -q` is green.
- `git show --stat` lists only this phase's files.
- python-reviewer and instruction-reviewer each return SHIP-READY, or every finding is fixed.

#### Phase 3 record

**NOT STARTED.**

### Phase 4 — Ledgers (D9 b, and the record of D10)

**Route: instruction-author → instruction-reviewer, looping until the review is clean.** Docs and ledgers only. ⚠ **Ledger edits WAIT until any other session's uncommitted edits to the same files are committed** (Trap 3).

#### Deliverables

- **`CHANGELOG.md`** — one `- feat(specify,verify): …` line under `## [Unreleased]`, under the sub-heading OQ-5's outcome names. It states the evidence class and claims nothing measured.
- **`DEVELOPMENT-STATUS.md`** — the `specify.md` and `verify.md` bullets under `### Commands`.
- **`PLAN-STATUS-ARCHIVE.md`** — three edits, in one change:
  - **(1)** this plan's `## Index` line (`## Index` at `:7`; plan 125's line is the last one at `:99` on 2026-10-03) and **(2)** its `## Entries` record (`## Entries` at `:105`), **both shapes or neither**. Both state the evidence class, and both record D10's outcome — whether 128 built in numeric order or by a ratified jump;
  - **(3)** the paragraph that summarizes `FINDINGS.md` (`:101`), whose count plan 125's Phase 3 set to "Eight", gains one in its count and a clause naming D9 (b)'s entry — otherwise it under-counts the file it summarizes.
- **The repo-root `CLAUDE.md`** — the "Where to find what" table gains a row, "Measured-AC gate (consumer-side)", naming the `_specify` `add-ac` baseline, `src/devforge/lib/_shared/spec_acs.py`, `src/devforge/lib/_verify/_ac_commands.py` and the verb OQ-1's outcome names.
- **`FINDINGS.md`** — D9 (b)'s entry, numbered after the last entry present at build time (entries run `## 1.` to `## 8.` on 2026-10-03), in entry 8's shape. Its closing note names its ordinal among the file-less findings and its position after the 2026-08-17 relocation, continuing entry 8's note; while entry 8 is still last, that is the NINTH file-less finding and the fourth recorded after the relocation. ⚠ **The ordinal notes inside the existing entries stay unedited**, per that file's preamble.
- **`src/devforge/storage-rules.md:267`** (the `verify →` lifecycle line) — re-read, and amended only when it enumerates `verification.md`'s sections.
- **This plan** — its Status line and `#### Phase 4 record` below.

#### Verify

- `grep -n "feat(specify,verify)" CHANGELOG.md` shows the new line under `## [Unreleased]`, under OQ-5's sub-heading, above `## [2.0.12]`.
- `grep -n "^## " FINDINGS.md` shows the new entry last; `git diff FINDINGS.md` is additions only.
- In `PLAN-STATUS-ARCHIVE.md`, `grep -n` finds each of the three edits: the `## Index` line above `## Entries`, the `## Entries` record below it, and the FINDINGS paragraph's new count and clause.
- `grep -n "Measured-AC gate" CLAUDE.md` finds the new row.
- The identifier grep over the staged diff — run by whoever holds the installation's identifiers — gets no hit.
- `git show --stat` lists only this phase's files.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 4 record

**NOT STARTED.**

### Consumer e2e — user-driven, NOT run by default

⚠ **The user-driven consumer-install exercise is the repo's deferred final gate; nothing in Phases 1–4 waits on it.** It runs only on the user's direction, never on the frozen benchmark install.

#### Verify

- In an install carrying Phases 1–3, a `/devforge:specify` run whose hygiene AC command passes at baseline is refused with D3's message, and one whose command fails at baseline is accepted, with a `> Baseline:` line in `spec.md`.
- That feature's `/devforge:verify` report carries the `**Source tree**:` line and `## Measured Acceptance Criteria`, with one row per command-bearing AC.
- The outcome is recorded below with no client identifier.

#### Consumer e2e record

**NOT RUN.**

---

## Non-goals

- **No `/devforge:plan` or `/devforge:breakdown` change.** The signal is mechanical — an AC carries a command — so no Signal Scan row, architect sub-question, `BreakdownSeeds` field, breakdown gate or task header field is needed (D6).
- **No harness / baseline / verify directory conventions, no scratch-overlay dry-run, no measurement-only task.** The baseline lives on the AC and the re-run in `verification.md`; harness scripts are already FEATURE-SCOPED (D7, F9).
- **No `/devforge:implement` or `verify-touched` change.** A measured count inside the self-repair loop invites editing the measurement instead of the code (D8, F8).
- **No `src/agents/ac-verifier.md` change.** The agent keeps classifying ACs by their prose, and `parse_acs`' `text` stays the EARS sentence it reads (D1); the command result is an independent blocker beside the agent's status (D4).
- **No `/devforge:spec-check` change.** It ignores the new keys, and Phase 2's Verify proves that with its own tests, not by assumption (D1).
- **No memory template or PHASE 7 rubric change.** Method lessons fit What Worked / Known Pitfalls, and the rubric has three buckets (D9 a).
- **No memory size-budget or consolidation build.** D9 (b) records the gap in `FINDINGS.md`; no plan owns it.
- **No backport to `main` or the 1.x line.** The maintainer redirected to 2.0 first, and `main`'s `update.sh` would overwrite the installation's local `specify.md` (`### The 1.x line — why 2.0 first`).
- **No `src/CLAUDE.md` edit** — the emitted consumer CLAUDE.md. Per `FINDINGS.md` entry 3 (*Post-plan-63 catalog trim — `/plan`'s constitution-backed obligations have no always-on presence*, dated 2026-08-12; heading at `FINDINGS.md:21`), per-obligation mechanics live in command bodies, not in always-on text.
- **No sandbox for verification commands.** They run with the user's privileges at specify and at verify time; this plan documents that and adds no sandbox (D2's counter-argument, Trap 6).
- **No re-measurement at the merge-base.** The regression-gate worktree is not reused (D5's counter-argument).
- **No sweep of the other fixtures' `verification_command` values.** D2 governs values `add-ac` accepts from Phase 1 on; a stored value is rendered and parsed as it is (Trap 13).
- **No release cut.** The CHANGELOG line lands under `## [Unreleased]`.
- **No consumer delivery.** The consumer e2e is user-driven and runs only on the user's direction.

---

## Context for next session

⚠ **Evidence class: ONE consumer installation, observed and measured by a sibling session, its measurements reported here and NOT re-verified; the 2.0 gap VERIFIED in this tree by grep and by reading the parser on 2026-10-03; NOTHING measured here, no run scored, nothing built.** ⚠ All line digits drift — **grep the quoted text, never the digits.**

**The one sentence that governs everything here:** **`/devforge:specify` already makes every presence and hygiene acceptance criterion carry an executable check; nothing in the pipeline runs it; this plan runs it twice — once at spec time to prove the gate can fail, once at verify time to prove it now passes — and writes both results where the next run can read them.**

### Honest bounds

- **One installation, reported by a sibling session; nothing re-measured here.** The lessons in `## Origin & evidence` are that session's account, and how many other installs wrote a fake gate is unknown.
- **The gate proves an exit code, not that the command measures the right thing** (D4). D2's shape rule is prose; D3's hygiene refusal is the one mechanical tooth behind it.
- **D3 cannot tell a malformed command from a present broken form** — both fail at baseline. The malformed one surfaces at verify, as a failure (D3's Bounds).
- **The negated absence form masks a failure to run at verify time** — a missing tool or a missing path reads as PASS behind a `!` (D2's Bound; the close record names the form).
- **Spec-time HEAD versus verify-time HEAD, with no merge-base re-measure** (D5's counter-argument), and `HEAD^{tree}` does not cover uncommitted edits (D5's Bound).
- **The installation's pre-plan measurement wins are not delivered** (D7's counter-argument).
- **2.0 has no memory consolidation step**; D9 (b) records it in `FINDINGS.md`, and nothing builds it.
- **Whether `/devforge:fix`'s feature lane reads an `ac_command_failed` blocker by its type is not examined here.** D8 says a failed command becomes NEEDS WORK and a `/devforge:fix` cycle; what that cycle reads is not part of this plan.
- **128 builds after 110–127** (D10's recommendation), by which time every anchor above will have drifted — re-anchor by the quoted text.

### Traps

**Trap 1 — line digits.** Every anchor here was read on 2026-10-03, and plans 110–127 build first. Re-anchor by searching the quoted text before every edit.

**Trap 2 — client identifiers.** This file is tracked in a public repo. Describe the installation as "one consumer installation (wrapper mode, running the 1.x command layout)" and the sender as "a sibling session", every time, in every phase's commit, record and ledger line.

**Trap 3 — `git add -A` and concurrent sessions.** Plans 110, 111, 126 and 127 are open, and other sessions build in this checkout. Commit by explicit path, check `git show --stat` after every commit, and hold Phase 4's ledger edits until other sessions' uncommitted edits to those files are committed.

**Trap 4 — the shared fixture.** `tests/lib/fixtures/specify-sample-migration.md` is read by nine test files and by `src/devforge/lib/_verify/_specstatus.py` (F2). Change only AC-1's and AC-7's `> Verification:` text, add their `> Baseline:` lines, keep every AC id and the AC count, and update the `-state.json` sibling to match. ⚠ **The fixture carries TWO command lines, `:32` and `:57`; a session that rewrites only AC-1 leaves a prose command under the hygiene AC.**

**Trap 5 — `resolve_workspace`'s import form.** It is imported cross-package, function-local, at four sites outside `_implement`, and at module level only in `_artifact` (F6). Copy the function-local form into the `_specify` setter; do not relocate `resolve_workspace`, and do not take the `_artifact` module-level imports as the precedent.

**Trap 6 — privileges.** A verification command runs with the user's privileges at specify AND at verify time. Document it in `/devforge:specify`'s Step 4.4 (Phase 1) and `/devforge:verify`'s `### 4.6` (Phase 3); never add a sandbox in this plan.

**Trap 7 — a RED for the wrong reason.** Phase 1's red for D3's refuse path is the tautology assertion failing because `add-ac` exited 0. A failing argparse call, a fixture error or a typo is not that red.

**Trap 8 — `/devforge:spec-check` consumes `parse_acs`.** It imports the same parser (`_spec_check/_consume.py:88`). Prove it ignores the new keys with its own tests in Phase 2, and edit nothing under `_spec_check/`.

**Trap 9 — moving the check into `/devforge:implement`.** A future session must not move the D4 verb (named at OQ-1's close), or any run of an AC's command, into `verify-touched` or the self-repair loop (D8, F8). `## Important rules` item 12 of `src/commands/verify/main.md` carries the tripwire sentence once Phase 3 lands.

**Trap 10 — `rtk` display output is lossy.** In this environment a display can drop or truncate lines. Read exact test output via `rtk proxy` plus a file redirect, then read the file.

**Trap 11 — `## [Unreleased]` sub-headings.** They carried `### Changed` and `### Fixed` on 2026-10-03. Re-verify them LIVE at build time; never edit a released block.

**Trap 12 — the verb registry is pinned by count and by name.** `tests/lib/_verify/test_preflight.py:728` asserts 16 registry entries, and `test_registry_verb_names` (`:730`–`:757`) asserts the exact set. Adding the verb without moving both pins fails the suite for a reason that is not a bug.

**Trap 13 — other fixtures carry `verification_command`.** On 2026-10-03 `tests/lib/fixtures/specify-sample-greenfield-state.json` and `tests/lib/fixtures/specs/008-sample-feature/spec-state.json` also carry the key. D2 does not rewrite them (`## Non-goals`). They carry no baseline fields, so under D3's render rule a spec rendered from them carries no `> Baseline:` line; if OQ-7 ratifies its recommendation, D4 never runs a command from them.

**Trap 14 — a measured PASS behind a `!`.** If D2's outcome keeps the `! grep …` form, a PASS row in the measured table does not prove the command ran: a missing tool or path inverts to exit 0 (D2's Bound). Read the row's output head before relying on it.

### File anchors

**EDIT targets — a phase of this plan writes each of these:**

- **`src/devforge/lib/_specify/_cmds_phase4_setters.py`** — `cmd_add_ac` (`:506`), the AC record (`:601`) (Phase 1).
- **`src/devforge/lib/_specify/_cmds_phase4_revise.py`** — `revise-ac` (`:140`–`:161`) (Phase 1).
- **`src/devforge/lib/_specify/handoff_schema.py`** — `AcceptanceCriterion` (around `:143`–`:170`) (Phase 1).
- **`src/devforge/lib/_specify/_render.py`** — `:71`–`:76` (Phase 1).
- **`src/commands/specify/main.md`** — Step 4.4 (`:660`), `## IMPORTANT RULES` (`:1021`; rule 13 after `:1034`) (Phase 1).
- **`tests/lib/fixtures/specify-sample-migration.md`** (`:32`, `:57`) and **`tests/lib/fixtures/specify-sample-migration-state.json`** (`:305`, `:359`) (Phase 1).
- **`tests/lib/test_specify_helper.py`**, **`tests/lib/_specify/test_landing.py`**, **`tests/lib/_specify/test_handoff_schema.py`**, and **`tests/lib/_specify/test_ac_baseline.py`** — new (Phase 1).
- **`src/devforge/lib/_shared/spec_acs.py`** — docstring (`:26`–`:31`), `_AC_LINE_RE` (`:72`), `parse_acs` (`:82`); **`tests/lib/_shared/test_spec_acs.py`** (Phase 2).
- **`src/devforge/lib/_verify/_ac_commands.py`** — new (Phase 3).
- **`src/devforge/lib/_verify/_cli.py`** — the registry (near `:1194`–`:1241`), the dispatch (near `:1474`–`:1748`), `cmd_compute_verdict` (`:657`), `cmd_render_report` (`:808`) (Phase 3).
- **`src/devforge/lib/_verify/_verdict.py`** — `compute_verdict` (`:208`) (Phase 3).
- **`src/devforge/lib/_verify/_report.py`** — `render_report` (`:101`), `render_inline_summary` (`:358`) (Phase 3).
- **`tests/lib/_verify/test_preflight.py`** (`:728`, `:730`–`:757`), **`tests/lib/_verify/test_verdict.py`**, **`tests/lib/_verify/test_report.py`**, and **`tests/lib/_verify/test_ac_commands.py`** — new (Phase 3).
- **`src/commands/verify/main.md`** — `:32`, `:185`, `:225`, `### 4.6` between `:301` and `:321`, `:329`, `:338`, `## Important rules` (`:471`) (Phase 3).
- **`src/commands/verify/references/report-format.md`** — `:9`–`:11`, the skeleton (`:31`), the semantics paragraphs (`:98`) (Phase 3).
- **`CHANGELOG.md`**, **`DEVELOPMENT-STATUS.md`**, **`PLAN-STATUS-ARCHIVE.md`** (`:7`, `:99`, `:101`, `:105`), the repo-root **`CLAUDE.md`**, **`FINDINGS.md`**, and **`src/devforge/storage-rules.md:267`** when it enumerates `verification.md`'s sections (Phase 4).
- **This plan** — every phase's record and, at Phase 4, the Status line.

**READ-ONLY anchors — no phase of this plan writes any of these:**

- `src/devforge/lib/_specify/_schema.py:105` — `AC_UBIQUITOUS_ONLY_SUBSECTIONS` (F1).
- `src/devforge/lib/_verify/_ac.py:64`, `src/devforge/lib/_spec_check/_consume.py:88`, `src/devforge/lib/_verify/_specstatus.py` — the parser's consumers and the fixture's non-test reader (F2, F3).
- `src/agents/ac-verifier.md` — the agent's contract stays as it is (`## Non-goals`).
- Inside EDIT targets, the parts no phase edits: `src/commands/specify/main.md:1030` (rule 8) and `:825` (Step 4.9); `src/commands/verify/main.md:199` and `:208`–`:213` (3.3), `:259` (4.3), `:280` (4.4), `:372` (PHASE 7), `:445` (Cleanup), `:474` (Important rule 2).
- `src/commands/plan/main.md:234` (Signal Scan) and `:397` onward (architect sub-questions); `src/devforge/lib/_plan/handoff_schema.py:318` (`BreakdownSeeds`) (F7, D6).
- `src/commands/breakdown/main.md:450`–`:465` (Regression-net declaration) and `:536` (PHASE 3.5) (F7, F9).
- `src/commands/implement/main.md:172` — PHASE 5 and its self-repair loop (F8, D8).
- `src/devforge/lib/_implement/_workspace.py:130` — `resolve_workspace`; its function-local import sites `src/devforge/lib/_verify/_regression.py:381` and `src/devforge/lib/_verify/_e2e.py:284` (F6, Trap 5).
- `src/devforge/lib/_verify/_regression.py:335` — `run_regression_gate`, the fail-soft precedent (F6, D4).
- `src/devforge/lib/_shared/memory.py:327` and `:339`; `src/devforge/memory.md` (F7, D9).
- `src/commands/finalize/main.md:138` and `:166`–`:169`; `src/devforge/lib/_finalize/_preflight.py:246`–`:250` — `/devforge:finalize` reads and commits `.devforge/memory.md`, never rewrites it (D9 b).
- `src/devforge/storage-rules.md:125` and `:203`–`:204` (F9).
- `124-PIPELINE-COST-REDUCTION-PLAN.md` — the cost direction (F10).
- `125-VERIFY-FILE-BUGS-IMPORT-PLAN.md` — its D4 (`FINDINGS.md` entry) and D5 (queue jump) precedents and its close-record shape; `98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md` — its D1 pick-or-delegation distinction.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation.
2. **Check `### Phase 0 close record` FIRST.** While it reads OPEN, nothing is ratified and no build phase may start.
3. **Check the queue position before any build.** Plans 110–127 sit ahead of 128 (F11); a build starts only when they are done or D10's outcome ratifies a jump.
4. **See what landed:** `git log --oneline -- src/devforge/lib/_shared/spec_acs.py src/devforge/lib/_specify src/devforge/lib/_verify`.
5. **Re-verify F1–F11 by grepping the quoted text, never the digits.** F4's zero-hit grep is the check that the gap is still open; a hit there means some other change has started consuming the command.
6. **Route every edit through the house flow:** python-engineer → python-reviewer for every Python edit; instruction-author → instruction-reviewer for every markdown edit; each loop runs until its review is clean. **Commit by explicit path, never `git add -A`.**
7. **Keep the evidence class** (stated at the top of `## Origin & evidence` and of `## Context for next session`) **and the no-client-identifier rule** (`## Origin & evidence`, Trap 2) **attached** to every summary of this plan.
