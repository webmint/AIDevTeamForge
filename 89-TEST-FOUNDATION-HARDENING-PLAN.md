# 89 — Test-foundation hardening: the test OBLIGATION made as standing as the test RUN

**Status:** NOT STARTED — awaiting Phase-0 ratification (D1–D6 + OQ-1–OQ-5 unanswered). Nothing below is decided; every decision carries a recommendation and at least one recorded alternative.
**Branch:** `develop-2.0-init`
**Created:** 2026-08-26.

This plan document contains no private-client identifiers and is intended to be
**committed normally**, unlike the deliberately-untracked plans 73/74/75.

## Evidence constraint

**There is no consumer incident behind this plan, no failing run, and no measurement.**
This is a **predicted-gap** plan, in the same class as plan 87 (whose `## Origin` likewise
records an argued exposure rather than an observed leak). Its entire evidentiary base is
(a) the live files enumerated in `## Verified mechanics`, read on 2026-08-26, and (b) one
maintainer review question dated the same day. **Say so wherever this plan is summarized** —
an entry that reads as if a consumer shipped untested code has over-claimed the origin.

The two UNTRACKED private-client evidence files at repo root
(`81-EVIDENCE-V2-BENCHMARK-RUN.md`, `77-EVIDENCE-DISCOVERY-TO-LOCK-INVERSION.md`) are neither
read nor cited here, and no phase may import from them.

---

## Origin — a review question, and what the sweep it triggered actually found

On 2026-08-26 the maintainer asked whether the framework actually covers the code it
generates with tests. The sweep that followed found a clean split, and the split is the whole
plan:

**Test RUNNING is solid, at three independent layers.** `/devforge:implement` PHASE 5 runs each
touched package's `test_command` as part of scope-aware verification, with a helper-owned
3-iteration self-repair loop (fact 9). `/devforge:verify` PHASE 4 runs the assembled suite as a
mechanical gate and, separately, runs a baseline-diff regression gate that compares merge-base
against HEAD (fact 12). `/devforge:review`'s panel includes `qa-reviewer`, which maps every
acceptance criterion to its tests and calls an unmapped AC a gap (fact 8). **Nothing in this
plan touches any of that**, and a future session must not read this plan as a claim that
test execution was broken.

**Test OBLIGATION is soft, at every layer that could carry it.** The duty to *have* a test —
as opposed to running whatever tests exist — is stated only in agent prose and nowhere in a
standing, always-present artifact:

- **The constitution never states a test obligation.** §3.4 Testing Requirements is a bare
  placeholder — one `- **Framework**: {{TESTING}}` bullet, a multi-stack rendering note, and
  `_Run /devforge:constitute to populate details_` (fact 1). The `[universal]` sections that
  DO carry standing rules — §3.5 Universal Code Quality, §3.6 Design Principles, §3.7 Check
  Before You Build, §3.8 Design Fidelity — say nothing about tests (fact 2).
- **The task-file skeleton has no test condition.** Every task's `## Done When` carries four
  helper-owned standing lines — no debug artifacts, type checker passes, linter passes, no new
  secrets — and no test analog (fact 3).
- **The emitted `CLAUDE.md` Key Rules have no test analog.** Item 8 is **Lint everything**;
  there is no test counterpart among the fifteen `### Always` items (fact 5).
- **A package with no configured test command runs no tests, silently.** `verify-touched`
  drops a `null`/`"N/A"` `test_command` with no signal, by design (facts 9, 10), and
  `/devforge:configure` is explicitly instructed NOT to guess one (fact 11). The two decisions
  are individually correct and jointly produce a path where a task completes with every
  Done-When box ticked and zero tests executed.

**The asymmetry is the finding.** Linting is obligated in three places at once — a Key Rule, a
standing Done-When line, and a per-task mechanical run. Testing has the mechanical run and
nothing else. This plan closes the two-of-three gap and makes the silent no-test path visible.
It does **not** add a gate.

### What was checked and deliberately left alone

Three testing-adjacent surfaces were examined during the sweep and ruled OUT of scope, each for
a stated reason. They are listed here rather than in `## Non-goals` alone, so a future session
finds the reasoning at the point where it would otherwise re-open them:

1. **AC→test-outcome mapping.** `/devforge:specify` already captures an optional `test_anchor`
   per AC, and `/devforge:verify`'s `tests` mode explicitly defers consuming it (fact 13).
   That deferral is **chartered to the testForge20 e2e** by its own text. This plan does not
   collect it.
2. **The regression-net declaration.** Plan 86's F3 shipped it with two honest bounds in the
   emitted text — nothing checks it, and its trigger rests on a belief rather than a
   measurement (fact 14). **Strengthening it waits on plan 86's Phase-7 observation data**,
   which has not been produced.
3. **`qa-engineer`-only-on-a-flagged-gap.** Inline tests are the per-engineer default and a
   separate `qa-engineer` task is created only on a flagged coverage gap or a declared
   property-test target (fact 15). That is deliberate design from the plan 09 / 15 lineage,
   not a hole.

---

## What is actually being added

Five things. **Phase 0 ratifies each independently — with one named exception, stated here
rather than discovered mid-build: D4's recommended arm CONSUMES D2's output and is not
buildable without it.** Every other pair is independent.

1. **One universal constitution rule** (Phase 2) — a titled bold block of test defaults
   appended inside a section that the drift detector actually tracks (D1). **Instruction-only.**
2. **A fifth standing Done-When line** (Phase 1) — emitted by `breakdown_helper
   render-task-file` beside the existing four (D2). **This is the only Python the plan
   builds**, and it is one list literal plus its tests.
3. **A no-test-run honesty arm** (Phase 3) — when `verify-touched` returns `pass` having run
   ZERO test commands, `/devforge:implement`'s approve path leaves D2's box unticked and
   annotated instead of falsely green (D4). **Instruction-only, and it reuses machinery that
   already exists.**
4. **A sixteenth emitted Key Rule** (Phase 4) — a pure append to `src/CLAUDE.md`'s `### Always`
   list (D3). **Advisory by construction** — see D3's bound.
5. **One documentation repair** (Phase 5) — the `REGRESSION_GATE` config key is read by
   `/devforge:verify` and set by a `configure_helper` verb, but `/devforge:configure`'s spec
   never mentions it (D6). **Instruction-only.**

**⚠ Three honest bounds that must survive into every emitted sentence and every summary:**

- **Nothing here is a gate.** Plan 75's tripwire holds in both halves: **zero new `verify-*`
  PHASE-3.5 gate numbers, zero new hard-fail validators, zero new check numbers.** D2 adds a
  checkbox; D4 decides whether that checkbox is ticked. Neither blocks anything, and
  `mark-complete` runs on the approve path after the human gate has already passed.
- **A Key Rule is not enforcement, by the vendor's own statement.** Claude Code's memory docs
  say CLAUDE.md content is *"context, not enforced configuration"* and that to block an action
  regardless of what Claude decides you use a hook instead (fact 16). **D3 buys presence, not
  compliance**, and the plan claims nothing more.
- **The obligation added is to WRITE tests; the coverage of those tests is not measured
  anywhere and this plan does not measure it** (D5). A future reader must not cite this plan
  as evidence that generated code is covered.

---

## Verified mechanics (2026-08-26)

Every row was confirmed by opening the named file or by the named fetch. **The quoted token is
the anchor; the digit is a dated hint** — this repo has documented anchor rot, so grep the
string, never the `:NNN`.

| # | Fact | Evidence |
|---|------|----------|
| 1 | **Constitution §3.4 is a bare placeholder.** Its entire body is `- **Framework**: {{TESTING}}`, a multi-stack rendering note, and `_Run /devforge:constitute to populate details_`. It is tagged `[project-specific]` | `src/constitution.md:55`–`:60` |
| 2 | **`_UNIVERSAL_SECTIONS` is a CLOSED literal tuple of ELEVEN §-strings** — `"§3.5", "§3.6", "§3.7", "§3.8", "§4.1", "§4.2", "§4.3", "§6.1", "§6.2", "§6.3", "§6.4"`. **`§3.4` is NOT among them**, and a new numbered subsection would require editing this tuple, which is Python | `src/devforge/lib/_constitute/_schema.py:296`–`:300` |
| 2a | **Consequence, and it inverts the obvious host choice:** `cmd_verify_universal_defaults` builds its canonical side from `_parse_universal_blocks`, which iterates `_UNIVERSAL_SECTIONS` only. **A block added inside §3.4 produces NO drift finding, ever** — the detector never looks there. A `3.4`/`Testing Requirements` grep across `src/devforge/lib/_constitute/` returns **zero** hits | `_cmds_quality.py:134`–`:171`; `_universal.py:71`; repo grep 2026-08-26 |
| 2b | **§3.5 parses as ONE rule whose body is the whole section**: the `else` branch returns `[{"tag_or_label": heading, "body": body_text}]` for every section that is not §3.6 or §4.1–4.3. So appending a block to §3.5 changes that single rule's body — which the detector compares — with **no parser change** | `src/devforge/lib/_constitute/_universal.py:79`–`:86` |
| 2c | **§3.6 splits per `**Name:**` standalone bold header** (regex `^\*\*([^*]+):\*\*\s*$`), which is why plan 86's `**Two-hats …**` block became a rule for free. §3.5's blocks are INLINE (`**No dead code.** Delete …`), so §3.5 does not split | `_universal.py:91`–`:133`; `src/constitution.md:64`–`:98` |
| 2d | ⚠ **`/devforge:constitute` REGENERATES `constitution.md` wholesale** from `.devforge/constitute.json` — `cmd_render` *"Concatenates and writes `<install_root>/constitution.md` atomically"*, and Section 3 renders from `state["code_quality_standards"]`. Its Phase-2 instruction says to draw on *"universal defaults applicable to every project"* but never says to copy the template's universal sections verbatim. **`verify-universal-defaults` is the only thing that NOTICES a divergence, and it is WARN-only at update time** | `_cmds_render.py:23`–`:27`; `_render.py:244`; `constitute/main.md:103`; `scripts/constitution-drift-check.sh:5`, `:54` |
| 3 | **The four standing Done-When lines are HELPER-OWNED PYTHON**, not instruction prose: `_DONE_WHEN_FIXED_LINES` is a module-level list, commented *"The four helper-owned Done-When lines (verbatim from storage-rules.md)"*, emitted by `cmd_render_task_file` | `src/devforge/lib/breakdown_helper.py:979`–`:985`, `:1083`–`:1089` |
| 3a | The same four lines are documented in the task-file skeleton | `src/devforge/storage-rules.md:186`–`:189` |
| 3b | **Two prose restatements name the set and would go stale**: *"the helper-emitted skeleton already carries the standing tsc/lint/no-secrets/no-debug conditions"* and *"every task's Done When carries tsc + lint conditions (the helper-emitted skeleton already does)"* | `src/commands/breakdown/main.md:356`, `:645` |
| 3c | **One test asserts the four verbatim and is NAMED for the count** — `test_four_fixed_done_when_lines_verbatim`. It uses `assertIn` per line, so a fifth line does not fail it; **the NAME becomes wrong, not the assertion** | `tests/lib/test_breakdown_helper.py:1756`–`:1767` |
| 3d | Two further test files embed the literal `- [ ] No debug artifacts left in changed files\n` inside hand-authored task-file fixtures (inputs, not `render-task-file` outputs) | `tests/lib/_implement/test_cmds_resolve.py:177`; `tests/lib/_implement/test_handoff_reader.py:186` |
| 4 | **`mark-complete` ticks every Done-When box by default**; `--unverified-box <substring>` (repeatable) forces the matching box UNticked and appends `_UNVERIFIED_ANNOTATION` *"so they are visibly honest instead of falsely green"*. The annotation literal is `" _(unverified — see Completion Notes)_"`, and the transform is idempotent across repair re-runs | `src/devforge/lib/_implement/_cmds_complete.py:68`–`:74`, `:129`, `:217`–`:224` |
| 4a | **`/devforge:implement`'s approve path ALREADY scans for a test condition it cannot currently find.** Its `--unverified-box` instruction says any Done-When line *"mentioning type-check / type errors / tsc / lint / linting / test / tests / spec / unit test / pytest / jest / vitest (case-insensitive) is a verification condition"*, and under `scope-and-approve` *"the type-check, lint, AND test Done-When conditions are all conservatively left unverified"*. **The consumer plumbing for D2's line exists before D2 ships it** | `src/commands/implement/main.md:254` |
| 5 | **The emitted `### Always` list is exactly FIFTEEN items**; item 8 is *"**Lint everything** — linting must pass on all changed files before task completion"*; item 15 is plan 87's *"**English in files**"*. **No test analog exists** | `src/CLAUDE.md:203`–`:217` |
| 6 | **`qa-engineer` is pointed at an empty page.** Its Rule 6 reads *"Read `constitution.md` before deciding (incl. its testing requirements)"* — and the constitution's testing requirements are fact 1's placeholder | `src/agents/qa-engineer.md:78`; `src/constitution.md:55`–`:60` |
| 7 | **No coverage threshold exists anywhere.** `qa-engineer` says *"Run the coverage tool and identify uncovered code paths"* and *"Prioritize what to cover: business logic > error handling > edge cases > rendering"* — a priority order with **no number** | `src/agents/qa-engineer.md:44`–`:46` |
| 8 | **The framework's actual coverage lever is AC→test mapping, not a percentage**: `qa-reviewer` Rule 2 is *"Map every acceptance criterion to its tests before judging coverage; an unmapped AC is a gap, not an omission to overlook"* | `src/agents/qa-reviewer.md:62` |
| 9 | `verify-touched` runs *"static checks (type-check + lint) first, then the build once, then tests last"* and states *"a project with no test command configured runs no tests (backward-compatible)"*. The self-repair cap (3) is helper-owned | `src/commands/implement/main.md:163` |
| 9a | **The drop is silent in the code**: `_collect_verify_commands` registers a test command only `if test_cmd and test_cmd != _NA and test_cmd not in test_set` — a `null` or `"N/A"` value falls through with no signal, no warning, no field | `src/devforge/lib/_implement/_cmds_verify.py:311`–`:314` |
| 9b | ⚠ **The fact is ALREADY on the wire and nobody reads it.** The `pass` payload carries `"test_commands_run": test_cmds` — so an EMPTY list on a `pass` means no test command executed. **`implement/main.md` never mentions the key.** It is absent from the `self_repair` / `failed` / `tooling_unavailable` payloads, but those are not approve paths | `_cmds_verify.py:613`–`:624`; `implement/main.md:163`–`:169` |
| 10 | **The `null` originates as a deliberate configure-time refusal**: *"`test_command` — … `null` when the package has no test script — do NOT invent an ecosystem-default guess"* | `src/commands/configure/main.md:134` |
| 11 | **`/devforge:configure` never mentions `REGRESSION_GATE`.** Phase 3 confirms *"all 23 detection-derived values"* (22 setter rows + the bulk `package_stacks` call); Phase 4 asks *"six fields [that] cannot be derived from filesystem scan"* (workflow enforcement, AI attribution, three tiers, AC mode). `regression_gate` is in **neither** | `src/commands/configure/main.md:148`–`:150`, `:199`, `:208`–`:233`, `:272`–`:299` |
| 11a | **Yet it is a first-class config field with a setter and a default**: `("regression_gate", "scalar")` in the schema, enum `{"off", "full"}`, default `"full"`, verb `set-regression-gate`, emitted key `REGRESSION_GATE` in `project-config.json`, and it appears in the `configure_helper` summary's **AC verification** group | `_configure/_schema.py:69`, `:84`, `:92`; `_configure/_cli.py:306`–`:310`; `_configure/_render.py:67`–`:68`; `_configure/_summary.py:52`–`:61` |
| 11b | **`/devforge:verify` reads it and documents it**: *"`regression-gate` reads the `regression_gate` config itself (`REGRESSION_GATE` in `.devforge/project-config.json`, default `full`)"*, and the verb is FAIL-SOFT — *"It ALWAYS exits 0"* | `src/commands/verify/main.md:242` |
| 12 | The regression gate reports `regression` only when the suite was green at the merge-base and red at HEAD; `inconclusive` covers *"no auto-detectable merge-base, no configured test command, or a git error"* and never gates | `src/commands/verify/main.md:242`–`:249` |
| 13 | **AC→test mapping is inert BY CHARTER, twice.** `/devforge:specify`: *"Downstream `/devforge:verify` will consume the anchor once fine-grained tests-mode test→AC mapping lands (currently deferred …)"*. `/devforge:verify` tests-mode: *"The fine-grained test-outcome→AC mapping is **deferred** (OQ-1 — resolve at the testForge20 e2e); the agent does NOT map PHASE-4 outcomes"* | `src/commands/specify/main.md:668`; `src/commands/verify/main.md:191` |
| 14 | **Plan 86's regression-net declaration ships its own two bounds**: *"NOTHING CHECKS the declaration: there is no Phase 3.5 gate for it, no `verify-*` verb, and no helper flag"* and *"the TRIGGER RESTS ON A BELIEF, not on a measurement"* | `src/commands/breakdown/main.md:417` |
| 15 | **Inline tests are the per-engineer default**: *"Inline tests stay the per-engineer default … Create a SEPARATE task assigned to `qa-engineer` … ONLY when decomposition or the Phase-2 architect consult flags a coverage gap or a test-heavy acceptance criterion"*, closing *"`qa-engineer` WRITES tests, while `/devforge:implement`'s per-task scope-aware verify step RUNS them"* | `src/commands/breakdown/main.md:283` |
| 16 | **Claude Code memory semantics, fetched 2026-08-26** from `https://code.claude.com/docs/en/memory` (`https://docs.claude.com/en/docs/claude-code/memory` 301-redirects there). Verbatim: *"CLAUDE.md files are loaded into the context window at the start of every session, consuming tokens alongside your conversation."* · *"**Size**: target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence."* · *"Claude treats them as context, not enforced configuration. To block an action regardless of what Claude decides, use a PreToolUse hook instead."* · *"**Consistency**: if two rules contradict each other, Claude may pick one arbitrarily."* **Cited so a future author re-verifies rather than trusting this file** | fetch 2026-08-26 |
| 17 | `CHANGELOG.md` carries a `## [Unreleased]` section whose first subsection is `### Added` | `CHANGELOG.md:8`, `:10` |

---

## Decisions — ALL OPEN, awaiting Phase-0 ratification

Each carries the rule, the alternatives, the reasoning, and the strongest counter-argument.
**The counter-arguments are load-bearing: a decision ratified with its counter-argument deleted
cannot be re-opened honestly later.**

### D1 — A universal test-obligation block in the constitution — inside §3.5, NOT §3.4 *(OPEN)*

**RECOMMENDED RULE.** Append one titled bold block to the END of `src/constitution.md`
§3.5 Universal Code Quality, in the shape that section's seven existing rules already use
(`**Title.** prose`). Proposed text, for Phase 0 to ratify or amend as written:

> **Tests are part of the change.** A change to observable behavior is complete only when a
> test asserts that behavior and the project's configured test command passes on the changed
> files. New behavior gets a test that asserts it; a repaired defect gets a test that fails
> without the repair. Tests assert observable behavior, not implementation shape — a test that
> restates the code it calls proves nothing. When a test and the code disagree, fix the test or
> fix the code; never weaken an assertion to make a test pass.

**Every clause is zero-escape-hatch** — no OR, no unless, no judgment call — and every clause
already has a consistent statement elsewhere in the framework, so this block introduces no new
policy, only a standing one: the last sentence is `qa-engineer` Rule 5 promoted from agent prose
to law, and the third is its *"Test behavior, not implementation details"* approach line.

**Why §3.5 and not §3.4, and it is mechanical rather than aesthetic.** §3.4 looks like the
natural home and is the wrong one:

- **§3.4 is invisible to the drift detector.** `_UNIVERSAL_SECTIONS` is a closed eleven-entry
  tuple that does not contain `§3.4` (fact 2), and `verify-universal-defaults` builds its
  canonical side by iterating exactly that tuple (fact 2a). **A rule placed in §3.4 gets no
  drift detection at all** — the one integrity mechanism the constitution has would never look
  at it.
- **§3.5 needs no parser change.** Every section outside §3.6 and §4.1–4.3 parses as ONE rule
  whose body is the whole section (fact 2b), so appending a block changes that rule's body and
  the existing comparison picks it up. **Plan 86 shipped the same move into §3.6 and recorded
  the identical consequence.**
- **A NEW numbered subsection (§3.9) is out of bounds** for the same reason plan 86's D2 gave:
  the tuple is a Python literal, and this plan's only Python phase is D2's list.

**Expected and DESIGNED consumer drift, recorded so nobody files it as a regression:** canonical
§3.5 gains a rule, so `constitute_helper verify-universal-defaults` will report a §3.5 body
mismatch against any install whose `.devforge/constitute.json` predates this build, and the
WARN-only update-time drift check will fire (fact 2d). **Back-porting into shipped installs is
an explicit NON-GOAL** — they arrive via `install.sh` / `update.sh`. ⚠ **If this ships in the
same release as plan 86, consumers see TWO drift findings (§3.5 and §3.6), not one.**

**Alternatives considered:**

- *(a) The block inside §3.4, above the placeholder.* REJECTED on fact 2a — zero drift
  detection. Its one genuine advantage is adjacency: `qa-engineer` Rule 6 sends the agent to
  *"its testing requirements"* (fact 6), which is §3.4. **That advantage is real and is not
  answered by this decision** — it is OQ-3's subject.
- *(b) A new numbered §3.9 Testing.* REJECTED — Python (fact 2), out of bounds.
- *(c) No constitution edit; rely on D3's Key Rule alone.* Recorded as the honest minimum. It is
  NOT recommended because the constitution is the artifact `/devforge:implement`'s per-task
  pre-flight reads, `qa-engineer` Rule 6 names by hand, and every agent is told is law — a test
  obligation that lives only in `CLAUDE.md` is absent from exactly the read path that already
  goes looking for it.

*Counter-argument, recorded, and it is the strongest one:* §3.5's heading is **Universal Code
Quality**, and a reader looking for testing rules will look at §3.4, find the placeholder, and
conclude the framework has none — **which is the exact failure this plan exists to fix, relocated
rather than removed.** *Accepted as a real cost*, and OQ-3 is where it is answered or accepted.
The reply is that a rule which survives is worth more than a rule which is well-filed and
undetected, and that fact 2d's regeneration seam makes detection the scarcer property.

*Second counter-argument, recorded:* fact 2d means a universal rule's survival into a consumer's
rendered constitution rests on the model composing it during `/devforge:constitute`, since that
command regenerates the file wholesale from state. **This plan does not close that seam and must
not claim to** — see `## Context for next session`, discovery 1.

### D2 — A fifth standing Done-When line *(OPEN — the plan's only Python)*

**RECOMMENDED RULE.** Add one entry to `_DONE_WHEN_FIXED_LINES` (fact 3), mirroring the
type-check and lint lines' exact wording so the five read as one family:

> `Tests pass on changed files (see Development Commands section)`

**The line is UNCONDITIONAL, and that is deliberate.** The drafting brief proposed *"the
package's configured test command passes (skip only when the package has no test command
configured)"*. **That phrasing is an escape hatch** — a `skip only when` clause inside a rule
is exactly the shape this repo's meta-rule forbids by name, and a reader who cannot see the
config from the task file cannot evaluate it. **The null-`test_command` case is handled by D4
instead**, which leaves the box UNTICKED and annotated rather than skipped — a strictly more
honest artifact, since a skipped condition leaves no trace and an annotated one does.

**Why the exact wording matters and is not a style choice.** `/devforge:implement`'s
`--unverified-box` instruction identifies verification conditions by scanning for lines
*"mentioning type-check / … / test / tests / …"* (fact 4a). `Tests pass on changed files`
contains `Tests`, so the existing scan already matches it, and the substring is unique within
the skeleton. **D2 requires NO change to that scan list** — Phase 3 verifies the no-op rather
than editing it.

**The full blast radius, verified — EIGHT sites: FIVE that D2 edits (1–5) and THREE verified
no-ops (6–8) that are RECORDED rather than changed.** A recorded no-op is a deliverable of this
decision, not an absence of one — "checked, nothing to change" is the finding that stops the
next session re-checking.

1. `src/devforge/lib/breakdown_helper.py:979`–`:985` — the list literal **and its comment**,
   which says *"The four helper-owned Done-When lines"* (fact 3).
2. `src/devforge/storage-rules.md:186`–`:189` — the documented skeleton the comment calls
   canonical (fact 3a).
3. `src/commands/breakdown/main.md:356` — *"the standing tsc/lint/no-secrets/no-debug
   conditions"* (fact 3b).
4. `src/commands/breakdown/main.md:645` — *"every task's Done When carries tsc + lint
   conditions"* (fact 3b).
5. `tests/lib/test_breakdown_helper.py:1756` — `test_four_fixed_done_when_lines_verbatim`. ⚠
   **Its assertions still PASS with a fifth line; only its NAME is falsified** (fact 3c), so a
   green suite is not evidence this site was handled.
6. `src/commands/implement/main.md:254` — **verified NO-OP FOR D2** (fact 4a): the scan-list
   sentence already matches `test`/`tests`, so adding the Done-When line requires no change to
   it. Record the no-op; **D2 does not edit this file.** ⚠ **Do not read this as "the file is
   untouched" — the SAME paragraph is rewritten at Phase 3 under D4**, whose build constraint
   corrects the categorical *"On a clean `pass`, pass NO `--unverified-box` arguments:"*
   sentence. **Two sentences, two decisions, opposite treatment**: the scan list is D2's no-op,
   the closing sentence is D4's edit.
7. `tests/lib/_implement/test_cmds_resolve.py:177` — fixture INPUT, not a `render-task-file`
   expectation (fact 3d). **Verified no-op**; record it.
8. `tests/lib/_implement/test_handoff_reader.py:186` — same (fact 3d). **Verified no-op**;
   record it.

*Counter-argument, recorded:* a ticked checkbox is not a passing test. `mark-complete` ticks
every box by default (fact 4), so on a package with no test command the new box would read
`- [x] Tests pass on changed files` over a run in which nothing ran. **This objection is
correct, and it is the entire reason D4 exists.** A ratifier who accepts D2 and declines D4 is
shipping a box that can lie — and should say so explicitly rather than discover it at Phase 6.

*Second counter-argument, recorded:* this is a fifth always-present line in every task file of
every feature forever, for a duty the constitution (D1) and the Key Rules (D3) will also state.
**Accepted as redundancy, and it is the point** — linting is stated in three places and testing
in one, and the asymmetry is the finding. The task file is the only one of the three the
implementing agent must tick.

### D3 — A sixteenth emitted Key Rule, pure append *(OPEN)*

**RECOMMENDED RULE.** Append one item to `src/CLAUDE.md`'s `### Always` list (fact 5), keeping
items 1–15 byte-identical:

> `16. **Test behavior changes** — every change to observable behavior ships with a test that
> asserts it; the configured test command must pass on changed files before task completion`

**Precedent is exact.** Plan 87's D4 appended item 15 *"English in files"* by pure append with
nothing renumbered. This is the same move, one item later, and it pairs with item 8 *"Lint
everything"* by design — the two read as the same obligation for the two check families.

**One line, and the size discipline is external, not a preference.** Claude Code's own memory
docs state CLAUDE.md is loaded into context at the start of every session, consuming tokens, and
*"target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce
adherence"* (fact 16). **Plan 08's always-on trim discipline binds this section for a documented
reason**, so the item is one line and Phase 4's verify criteria pin the line count.

**⚠ Honest bound, stated in the vendor's words rather than argued:** *"Claude treats them as
context, not enforced configuration. To block an action regardless of what Claude decides, use a
PreToolUse hook instead"* (fact 16). **Item 16 buys presence in every session, not compliance in
any of them.** This plan builds no hook and claims no enforcement.

**Alternatives considered:**

- *(a) Extend item 8 to read "Lint and test everything."* REJECTED — it silently rewrites a
  shipped rule's meaning, breaks plan 87's pure-append precedent, and buries a new obligation
  inside an old item where a diff reader will miss it.
- *(b) No Key Rule; D1 and D2 suffice.* Recorded. The constitution is read at pre-flight and the
  task file at dispatch, but neither is in context during the conversational turns where a user
  asks for a change directly. **Item 16 is the only one of the three that is always resident.**

*Counter-argument, recorded:* the `### Always` list has grown by two items in the last two plans
(15, now 16) with no eviction rule, and plan 84's OQ-3 recorded *"no addition without eviction"*
as a **candidate convention only, nothing built**. **This plan adds without evicting and does not
pretend otherwise.** A future session that finds the list past useful length has a real
plan to write, and fact 16's 200-line target is the objective trigger for it.

### D4 — The silent no-test path, surfaced through machinery that already exists *(OPEN — three arms; DEPENDS ON D2)*

**RECOMMENDED RULE — arm (b), instruction-only.** In `/devforge:implement`'s PHASE-7 approve
path, extend the existing `--unverified-box` determination with one mechanical clause:

> When PHASE 5's `verify-touched` returned `{"status": "pass", …}` and its `test_commands_run`
> array is EMPTY, pass the Tests Done-When condition as `--unverified-box`.

**The trigger is a JSON field, not a judgment.** `test_commands_run` is already on the `pass`
payload (fact 9b); an empty array means no test command executed, for the mechanical reason that
`_collect_verify_commands` registered none (fact 9a). There is no threshold, no heuristic and no
"if it seems like" clause.

**Why this is cheaper AND stronger than a stderr warning.** The result is a durable artifact:
the task file keeps `- [ ] Tests pass on changed files _(unverified — see Completion Notes)_`
(fact 4), which a human, `/devforge:review`, and `/devforge:verify` can all still read weeks
later. A stderr line scrolls past once. **And it costs zero Python** — the annotation, the
idempotent re-tick on a repair re-run, and the substring match all exist today.

**Coverage is complete across approve paths, and this was checked rather than assumed.** A task
reaches `mark-complete` either after a `pass` (the new clause) or via the
`tooling_unavailable` → `scope-and-approve` route, where the existing instruction already marks
the type-check, lint AND test conditions unverified (fact 4a). `self_repair` and `failed` are
not approve paths.

**⚠ Dependency, stated loudly because it breaks this plan's independence rule:** arm (b) marks a
box that only exists if **D2 ships**. **If D2 is declined, arm (b) is not buildable** and D4
falls to arm (a) or arm (c). Phase 0 must ratify D2 before, or together with, D4 — never D4
alone.

**Alternatives considered:**

- *(a) A stderr WARN from `cmd_verify_touched`* — plan 87 D1's shape (`commit-artifacts:
  warning: …`, exit code and stdout JSON byte-unchanged). RECORDED as the **named strengthening
  arm**, not as the first cut. It is mechanical rather than model-mediated, which is genuinely
  stronger, but it is Python for a predicted gap with no incident, and it produces no durable
  record. **Strengthening trigger, stated so it is checkable: the first observed run in which a
  package with no configured test command completed a task with the Tests box ticked.** Until
  one is observed, arm (b) has demonstrated only that it can be followed.
- *(c) Build nothing; the `null` is documented behavior.* Recorded, and it is defensible — fact
  10 shows the `null` is a deliberate refusal to guess, and fact 9's *"backward-compatible"* is
  a design statement, not an oversight. It is NOT recommended because the documented thing is
  that no tests RUN; nothing documents that the task file then claims they passed.

*Counter-argument, recorded:* arm (b) is orchestrator prose, so nothing enforces that the
orchestrator read the field — the same class of guarantee plan 86's F3 accepted with *"NOTHING
CHECKS the declaration."* **Accepted.** The reply is that the trigger is a mechanical field
rather than a belief (which is where F3's second bound bit), and that arm (a) remains available
on an observed miss.

### D5 — No numeric coverage threshold *(OPEN)*

**RECOMMENDED RULE.** This plan adds **no** coverage percentage, at any layer — not in the
constitution block (D1), not in the Done-When line (D2), not in `qa-engineer`, not as a gate.
`qa-engineer`'s priority order (fact 7) and `qa-reviewer`'s AC→test mapping (fact 8) remain the
framework's coverage lever, unchanged.

**Why**, and two of the three reasons are already this repo's stance:

- **A percentage is gameable in the direction that looks like compliance.** Tests that execute
  lines without asserting behavior raise it — the exact failure D1's third sentence and
  `qa-reviewer`'s *"weak assertions, tests that bind to implementation"* focus both name.
- **A threshold punishes honest deletion.** Removing a well-covered module lowers the number
  while improving the codebase, and plan 71's dead-code lane makes deletion a MANDATORY
  obligation on some changes. **A gate that fires on discharging another gate's duty is a
  contradiction, and fact 16 warns that contradictory rules get resolved arbitrarily.**
- **Precedent: plan 27's D3 and plan 88's D7 both refused a size metric** for routing, on the
  ground that the number measures a proxy. The same argument applies to coverage.

*Counter-argument, recorded, and it is not fully answered:* without any number, "coverage" is
unfalsifiable — `qa-reviewer` reports gaps in prose, no artifact records how much of a feature
is exercised, and nothing in this framework can answer "is this codebase tested?" with evidence.
**Accepted as the standing bound.** A future plan that wants an answer should build a
**reported, non-gating** coverage number first (a measurement with no verdict attached) and
argue a threshold only from the distribution that measurement produces — never the reverse.
**Nothing in this plan makes that easier, and it should not be cited as a step toward it.**

### D6 — Document `REGRESSION_GATE` in `/devforge:configure` *(OPEN — two arms)*

**RECOMMENDED RULE — arm (b), documentation only.** `/devforge:configure`'s spec gains a short
note stating that `regression_gate` exists, defaults to `"full"`, is set by
`configure_helper set-regression-gate <off|full>`, and is emitted as `REGRESSION_GATE` in
`.devforge/project-config.json` where `/devforge:verify` reads it (facts 11a, 11b). **No new
prompt, no new detected value, no change to the "23 values" or "six fields" counts** (fact 11).

**Why the gap is real and worth one paragraph:** the key is a live user preference with an enum,
a default, a setter, a `project-config.json` slot and a documented consumer — and the one
command that owns configuration never names it, so the model running `/devforge:configure` never
surfaces it and the user never learns it exists. **This is the cheapest finding in the plan and
the only one that repairs a documentation defect rather than adding an obligation.**

**Alternatives considered:**

- *(a) A seventh Phase-4 `AskUserQuestion`* (`full` recommended / `off`). NOT recommended: it
  adds a prompt to a one-time setup chain for a setting whose default is correct for nearly
  every project, and it forces edits to Phase 4's *"six fields"* framing plus the counts in
  fact 11. **⚠ If Phase 0 picks (a) anyway, the two-option question is legal** — the
  AskUserQuestion contract allows 2–4 options and injects "Other" itself, so no explicit
  Other option may be authored.
- *(c) Leave it undocumented.* REJECTED — an undocumented live config key is precisely the
  future-session hallucination seed this repo's discipline names.

*Counter-argument, recorded:* a note in a command spec is read by the model, not by the user, so
arm (b) makes the key discoverable to the orchestrator and still invisible to the human who
would want to turn the gate off. **Accepted.** The partial answer is that `/devforge:verify`
already surfaces the gate's status per run with a `note` field on every non-gating status
(fact 12), so a user who sees it run has a name to search for — and arm (a) is the recorded
escalation if that proves insufficient.

---

## Open questions (OQ-N) — ALL OPEN

### OQ-1 — Exact wording of D2's Done-When line

**RECOMMENDATION:** `Tests pass on changed files (see Development Commands section)` — mirroring
the type-check and lint lines verbatim in structure, so the five lines read as one family and
the `(see Development Commands section)` pointer stays consistent.

**Two mechanical constraints Phase 0 must not break**, whatever wording it picks: the line MUST
contain a token from fact 4a's scan list (`test`/`tests` — case-insensitive), and it MUST be a
substring unique within the rendered skeleton, because `--unverified-box` matching is *"plain
case-sensitive substring containment"* (fact 4). A wording that matches two boxes marks both.

### OQ-2 — Does D1's block name a testing PRACTICE or only an OBLIGATION?

**RECOMMENDATION: obligation only, as drafted.** The block states when a change is complete and
what a test must assert. It names **no framework, no file layout, no directory convention and no
number** — those are §3.4's `[project-specific]` territory (fact 1) and `/devforge:constitute`'s
job. **A universal section that names a testing framework would be false on the next project**,
and `{{TESTING}}` already exists for exactly that.

### OQ-3 — Does anything repair §3.4's emptiness, or is D1's relocation accepted as-is?

This is D1's counter-argument turned into a question, and it needs an explicit answer rather
than silence. Three candidates:

- **(i) Accept it.** §3.4 keeps its placeholder; the universal rule lives in §3.5. **RECOMMENDED**
  — it is the only candidate that adds nothing, and `/devforge:constitute` legitimately owns
  §3.4's content on every project.
- **(ii) Add a one-line pointer in §3.4** to §3.5. ⚠ **Verify before choosing:** fact 2d means a
  pointer in §3.4 is wiped the moment `/devforge:constitute` re-renders, and §3.4 is untracked
  (fact 2a), so nothing would notice. **A line that vanishes on the first run of the command it
  refers to is worse than no line.**
- **(iii) Repoint `qa-engineer` Rule 6** (fact 6) from *"its testing requirements"* to the
  constitution generally. **NOT recommended:** the rule is already correct on a populated
  install — §3.4 is where `/devforge:constitute` puts project testing rules — and the agent
  reads the whole constitution regardless. Editing it would trade a correct sentence for a
  vaguer one. ⚠ **`qa-engineer.md` is also a plan-90 shared surface**, so a change here would
  fall under the coordination rule below.

### OQ-4 — Does anything need to change in `/devforge:verify` or `/devforge:review`?

**RECOMMENDATION: no, and the reasoning is worth recording so it is not re-derived.**
`/devforge:verify` already runs the assembled suite as a mechanical blocker and the regression
gate independently (facts 9, 12), and `qa-reviewer` already reports coverage gaps at
`/devforge:review` (fact 8). D2's box is a per-task authoring condition, not a verdict input,
and **nothing in this plan feeds `compute-verdict` a new field.** ⚠ The corollary matters: an
unticked, annotated Tests box does **not** produce a NEEDS WORK on its own. It is visible, not
blocking, and no phase may describe it otherwise.

### OQ-5 — Do the two verified no-op test fixtures get touched?

**RECOMMENDATION: no.** `tests/lib/_implement/test_cmds_resolve.py:177` and
`test_handoff_reader.py:186` embed the four-line block as hand-authored task-file INPUT, not as
an expected `render-task-file` output (fact 3d), so a fifth emitted line does not affect them.
**Record the no-op in Phase 1's verify block** — "checked, nothing to change" is a finding, and
recording it stops the next session re-checking. The site that DOES need attention is fact 3c's
count-named test, whose assertions pass while its name lies.

---

## Phases

### Phase 0 — Ratification *(doc-only)*

**Objective:** ratify or amend D1–D6 and answer OQ-1–OQ-5, recording each answer in this file
with its reasoning. **Nothing else may start.**

Three items need an explicit pick rather than a nod:

- **D1's host section.** §3.5 versus §3.4 is decided by fact 2a, not by taste — a ratifier
  choosing §3.4 is choosing a rule with no drift detection and should say so.
- **D4's arm, AND its dependency on D2.** Ratifying D4(b) while declining D2 produces an
  unbuildable phase. Ratifying D2 while declining D4 ships a checkbox that can read `[x]` over a
  run in which no test executed — **stated in D2's counter-argument, and a ratifier must accept
  it explicitly rather than by omission.**
- **D6's arm.** (a) adds a setup prompt and forces the count edits in fact 11; (b) does not.

**Verify:**

- `grep -n "^### D[1-6] " 89-TEST-FOUNDATION-HARDENING-PLAN.md` returns six lines and **every one
  carries a ratification marker with a date** — no `*(OPEN)*` remains anywhere in the file.
- `grep -n "^### OQ-[1-5] " 89-TEST-FOUNDATION-HARDENING-PLAN.md` returns five lines, each with a
  recorded answer.
- **Every decision still carries its counter-argument.**
- The status line at the top names the ratification date and which phases are cleared.
- **The D2 ↔ D4 dependency is resolved in writing**, not left implicit.

---

### Phase 1 — The fifth standing Done-When line *(the ONLY Python phase)*

**Route: python-engineer → python-reviewer, test-first.** No `.claude/`-shipping file changes
here, so no claude-code-guide pass is owed by this phase.

**Deliverable.** One entry appended to `_DONE_WHEN_FIXED_LINES` (fact 3), its comment corrected
from *"The four helper-owned Done-When lines"*, `storage-rules.md`'s skeleton updated to match
(fact 3a — the comment names it as canonical, so they move together), and fact 3c's test renamed
and extended to five lines.

**⚠ Three build constraints, each a fact rather than a fork:**

1. **The line is emitted UNCONDITIONALLY** — no flag, no `if`, unlike the optional
   `**Property targets**:` and `**Dead code removal**:` lines. It joins the fixed four.
2. **The wording must satisfy OQ-1's two mechanical constraints** — a `test`/`tests` token and
   substring-uniqueness within the skeleton.
3. **Ordering:** append after `No new secrets or credentials in code` OR insert after the linter
   line. **Phase 0 does not decide this; Phase 1 does, and states which and why** — the
   type-check/lint/test grouping argues for insertion, byte-stability of existing output argues
   for append. Whichever is chosen, `storage-rules.md` matches it exactly.

**Tests — written and RUN in the same turn as the code**, per repo discipline, and round-tripped
through the real producer: a test invokes `render-task-file` and asserts all FIVE lines verbatim,
plus a sibling asserting the rendered skeleton still parses under
`_cmds_complete.py`'s `## Done When` section regex (fact 4) with the new line ticked by default
and left annotated when passed as `--unverified-box`.

**Verify:**

- python-reviewer clean; `tests/lib/test_breakdown_helper.py` and `tests/lib/_implement/` green.
- **fact 3c's test is renamed** — `grep -n "four_fixed_done_when" tests/` returns nothing. A
  green suite alone does not prove this site was handled; the assertions pass either way.
- **A test proves `--unverified-box` on the new line leaves it unticked and annotated exactly
  once**, and a sibling proves a second `mark-complete` re-run does not double-append (fact 4's
  idempotence).
- **`storage-rules.md`'s skeleton and `_DONE_WHEN_FIXED_LINES` are byte-consistent** — diff them
  line by line; the code comment asserts they are.
- **OQ-5's two fixture files are confirmed untouched** and the no-op is recorded in the commit
  message.
- `git status` shows zero files modified under `src/commands/`, `src/agents/` or
  `src/constitution.md` — this phase is Python + `storage-rules.md` only.

---

### Phase 2 — The constitution block

**Route: instruction-author → instruction-reviewer.** `constitution.md` does not ship into
`.claude/`, so no claude-code-guide pass is owed.

Scope, one file: `src/constitution.md` §3.5, one appended titled bold block per D1.

**⚠ Two placement constraints:**

1. **Append at the END of §3.5's rule prose but BEFORE the two `*Backed by*` lines** — those
   name `verify-magic-enum` and `verify-any-leak` and read as the section's closers. Confirm
   against the live file; §3.5's tail is `*Backed by* … verify-any-leak …` today.
2. **Use §3.5's INLINE bold shape** (`**Title.** prose`), not §3.6's standalone `**Title:**`
   header shape — fact 2c shows the two sections are parsed by different code paths, and §3.5's
   whole body is one rule either way.

**Verify:**

- Instruction-reviewer clean.
- **The block contains no OR / unless / when-reasonable clause** — read every sentence against
  the zero-escape-hatch check and state the result.
- **The block names no framework, no percentage and no file layout** (OQ-2) —
  `grep -n "%" src/constitution.md` returns no new line, and no test-runner name appears.
- **`{{TESTING}}` in §3.4 is untouched** and §3.4 is byte-identical unless OQ-3 picked (ii).
- **Section numbering is unchanged** — `grep -n "^### 3\." src/constitution.md` returns the same
  eight headings as before. Capture the pre-change output first.
- **No new entry is needed in `_UNIVERSAL_SECTIONS`** — confirm §3.5 is already in the tuple
  (fact 2) and that this phase touched no Python.
- **The expected drift is recorded, not fixed**: a note in the commit message that
  `verify-universal-defaults` will now report a §3.5 mismatch on pre-build installs by design.

---

### Phase 3 — `/devforge:implement`'s no-test honesty arm + the `/devforge:breakdown` prose sweep

**Route: instruction-author → instruction-reviewer + claude-code-guide.** Both files ship into
`.claude/commands/devforge/`.

Scope, two files:

- **`src/commands/implement/main.md` — PHASE 5 and the PHASE-7 approve path.** Document the
  `pass` payload's `test_commands_run` key (fact 9b — it exists and the spec never names it),
  and add D4's single clause to the `--unverified-box` determination at fact 4a's site.
  **⚠ Two neighbouring sentences in that same paragraph get OPPOSITE treatment, so name them
  separately:** the **scan-list sentence** (*"any checkbox line mentioning type-check / … / test
  / tests / …"*) is a verified NO-OP — it already matches D2's wording — so **do not edit it**
  and record the no-op in the phase report; the **closing sentence** of the same paragraph IS
  rewritten, per the build constraint below.
- **`src/commands/breakdown/main.md` — the two prose restatements** (fact 3b): `:356`'s
  *"tsc/lint/no-secrets/no-debug"* enumeration and `:645`'s *"tsc + lint conditions"*. Both name
  the standing set and both go stale on Phase 1.

**⚠ Build constraint — one existing sentence CONTRADICTS D4 and must itself be rewritten, not
just appended to.** The same fact-4a paragraph closes with the categorical sentence
*"On a clean `pass`, pass NO `--unverified-box` arguments:"* (verified verbatim at
`implement/main.md:254`, 2026-08-26). **D4's clause says the exact opposite for one case** — a
clean `pass` whose `test_commands_run` is empty passes exactly one. Adding D4's clause while
leaving that sentence standing puts two contradictory instructions in one paragraph, and fact
16 is explicit that *"if two rules contradict each other, Claude may pick one arbitrarily."*
**So the sentence is REWRITTEN to carry the carve-out inline** — one clause naming the Tests
condition and the empty `test_commands_run` array, so a reader of that sentence alone gets the
whole rule. Its neighbouring `scope-and-approve` sentence stays byte-unchanged.

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean, with the fetched URLs recorded.
- **`grep -n "tsc/lint/no-secrets/no-debug\|tsc + lint" src/commands/breakdown/main.md` returns
  no stale enumeration.** Capture the pre-change output first.
- **The D4 clause names `test_commands_run` and `pass` explicitly** — a clause that says "when
  no tests ran" without naming the field it reads has reintroduced a judgment call.
- **The contradicting sentence is gone in its unqualified form** —
  `grep -n "pass NO \`--unverified-box\` arguments" src/commands/implement/main.md` returns
  either nothing or only an occurrence that carries the Tests carve-out in the same sentence.
  **Capture the pre-change output first** (today it returns exactly one unqualified hit). A run
  that adds D4's clause and leaves this grep unchanged has shipped the contradiction.
- **The clause is scoped to the `pass` path only** — `self_repair` / `failed` /
  `tooling_unavailable` arms are byte-unchanged, and the `scope-and-approve` arm's existing
  three-condition sentence (fact 4a) is untouched.
- **No new helper verb, flag or exit code appears** — `grep -n "implement_helper" src/commands/implement/main.md`
  returns the same verb set as before. Capture the pre-change output first.
- **No plan vocabulary in emitted text** — "D4", "OQ-1" and this plan's number are maintainer
  vocabulary. Emitted text names only commands, files, fields and behaviors.

---

### Phase 4 — The sixteenth Key Rule

**Route: instruction-author → instruction-reviewer + claude-code-guide** (`src/CLAUDE.md` ships
as the consumer's root `CLAUDE.md`).

Scope, one file: `src/CLAUDE.md`'s `### Always` list — **one appended item, nothing renumbered**
(fact 5, plan 87's precedent).

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean, with the fetched URLs recorded.
- **Items 1–15 are byte-identical** — diff the section and confirm the only change is one added
  line. **Plan 87's item 15 in particular is byte-unchanged**; this is an append, not an edit of
  its neighbour.
- **The new item is ONE line** and the `### Always` section's line count grew by exactly one
  (fact 16's size discipline, plan 08's trim rule).
- **The item does not contradict item 8** — the two are read together and cover different check
  families (fact 16: contradictory rules get resolved arbitrarily).
- **`grep -n "%" src/CLAUDE.md`** returns no new coverage number (D5).
- **No `{{` placeholder leaks**: the new line introduces none.

---

### Phase 5 — `REGRESSION_GATE` documentation + docs sweep + dated reconciliation notes

**Route: instruction-author → instruction-reviewer** for every `src/` and plan-document edit;
**+ claude-code-guide** for `src/commands/configure/main.md`, which ships.

Open the phase with `grep -rn "REGRESSION_GATE\|regression_gate" src/ scripts/ *.md` and
reconcile every hit. **This sweep list is NOT certified exhaustive** — treat a hit not named
below as an omission in this plan, not as a new defect.

Scope:

- **`src/commands/configure/main.md`** — D6's note. Under arm (b) it changes **no count**: the
  *"all 23 detection-derived values"* and *"six fields"* statements (fact 11) stay byte-exact,
  because `regression_gate` is neither detected nor prompted. **Under arm (a) both counts move
  and the setter table gains a row** — Phase 0 said which.
- **Repo-root `CLAUDE.md`** — the plan-89 one-liner appended to the active-plans index, matching
  the neighbouring entries' density. **Read the file live for the append point**; the index grows
  and a pre-computed position rots.
- **`PLAN-STATUS-ARCHIVE.md`** — the mirrored full entry, per this repo's index/archive split.
- **`CHANGELOG.md`** — an entry under the existing `## [Unreleased]` → `### Added` (fact 17).
  **Read the file live** rather than creating a heading on the strength of this note.
- **`86-FOWLER-REFACTORING-GAPS-PLAN.md`** — a dated note **only if** its F3 text or its
  `## Non-goals` would be read as covering this plan's ground. **Read it and record the result
  either way** — "checked, no claim to amend" is a finding.
- **`87-ARTIFACT-LANGUAGE-GUARD-PLAN.md`** — **check only, and record the no-op as deliberate.**
  Its D1 advisory-WARN precedent is CITED by D4's arm (a) and nothing in it changes.

**Commits: one per phase, no AI-attribution trailer** (this repo's commits carry none — match
the trailer-free convention), lowercase terse subject with a scope prefix matching
`git log --oneline`.

**Verify:**

- The sweep returns zero dangling references; the `tests/` suite is green.
- **`grep -rn "REGRESSION_GATE" src/commands/` returns hits in BOTH `verify/main.md` and
  `configure/main.md`** — today it returns only the former (fact 11).
- **The `CHANGELOG.md` entry states the honest bounds**: no incident behind the plan, no gate
  added, no coverage measured. **An entry claiming the framework now enforces test coverage has
  over-claimed by two layers.**
- **The repo-root one-liner names the D2 ↔ D4 dependency and the "no gate" tripwire.**
- `scripts/verify-agent-reachability.py` and `scripts/verify-memory-lane.py` pass (nothing here
  touches either, so a failure means something unintended moved).
- **The plan-88 index bullet is byte-unchanged** — this is an append, not an edit of its
  neighbour.

---

### Phase 6 — Consumer e2e *(user-driven HARD GATE)*

**Everything above is build-verified, NOT consumer-validated.** No phase above may claim any
part of this has been observed in a consumer install.

**Known-answer anchors**, so this is a regression anchor rather than an exploratory run:

1. **The configured-test-command path.** Run `/devforge:breakdown` then `/devforge:implement` on
   a feature in a package whose `test_command` is non-null. **MUST** produce: a task file whose
   `## Done When` carries D2's Tests line; a PHASE-5 `pass` whose `test_commands_run` is
   non-empty; and after approve, that box **ticked with no annotation**.
2. **The null-test-command path.** Same, in a package whose `test_command` is `null`. **MUST**
   produce: the same Done-When line; a PHASE-5 `pass` whose `test_commands_run` is **empty**;
   and after approve, that box **UNTICKED and carrying `_(unverified — see Completion Notes)_`**.
3. **The drift signal.** Run `constitute_helper forge-internal:verify-universal-defaults`
   against an install whose `.devforge/constitute.json` predates this build. **MUST** report a
   §3.5 finding and exit 2 — **this is the designed outcome, not a defect** (D1).
4. **The Key Rule shipped and is loaded.** Two parts, both scored. **(a) On disk, checkable with
   no tool-behavior claim at all:** the consumer install's emitted root `CLAUDE.md` contains
   item 16 in its `### Always` list, with items 1–15 unchanged — a plain read of the installed
   file after `install.sh` / `update.sh`. **(b) Loaded into the session:** open the consumer
   project in a FRESH Claude Code session and confirm that root `CLAUDE.md` is among the project
   memory files the session loaded, using whichever in-session memory-listing surface the
   then-current Claude Code provides (`/memory` lists memory-file locations and opens them).
   ⚠ **Part (b) rests on a Claude Code tool-behavior claim and is therefore NOT verified by this
   plan — invoke `claude-code-guide` to confirm the current listing surface and its output BEFORE
   Phase 6 runs**, per this repo's agent-only verification rule. **Part (a) does not depend on
   that check and is scored independently**, so a Phase 6 blocked on (b) still returns a verdict
   on whether the rule shipped.

**Verify:**

- All four anchors are scored **explicitly** — stated, not summarized.
- **Anchors 1 and 2 are scored as a PAIR.** An implementation that annotates every task passes 2
  and fails 1; one that annotates none passes 1 and fails 2. **Neither is meaningful alone.**
- **Anchor 2 records the exact task-file line as a STRING**, not as "looked right" — the
  annotation is a literal with an em-dash and leading space (fact 4).
- **Anchor 3 records the helper's exact finding kind** (`MISSING` versus a body mismatch), so a
  future session knows which arm of the detector fired.
- **Anchor 4's two parts are scored SEPARATELY**, and part (a) is scored even if the
  `claude-code-guide` check for part (b) has not been run. **Recording (a) as "passed" while
  silently skipping (b) is a failure of this criterion** — an unrun part is reported as unrun.
- **If it fails**, record the negative here with the artifacts and identify which mechanism
  produced it before proposing anything: a missing Done-When line is a D2 finding, a wrongly
  ticked box is a D4 finding, a silent drift check is a D1 finding (and specifically means the
  block landed in an untracked section), an absent Key Rule is a D3 finding. **They have
  different fixes.**
- **A clean run is NOT evidence that generated code is better tested.** It is evidence that the
  obligation is present and that the no-test case is visible. **This plan measures no coverage
  and Phase 6 cannot produce that measurement** (D5).

---

## Cross-plan coordination — plan 90

As of 2026-08-26, `90-E2E-TEST-LANE-PLAN.md` exists at repo root — drafted concurrently with
this plan on the same day and likewise **NOT STARTED**. **Execution order is 89 before 90.**
**TWO surfaces this plan edits unconditionally, and a THIRD that is conditional and probably
never joins them:**

- **`src/CLAUDE.md`** — this plan appends one item to the `### Always` list at its Phase 4.
  **Shared, unconditionally.**
- **`src/devforge/storage-rules.md`** — this plan edits the task-file `## Done When` skeleton at
  its Phase 1. **Shared, unconditionally.**
- **`src/agents/qa-engineer.md`** — **CONDITIONAL, and the expected outcome is that this plan
  never touches it.** Only OQ-3's arm **(iii)** (repointing `qa-engineer` Rule 6 away from *"its
  testing requirements"*) would edit that file, and **(iii) is NOT recommended** — arm **(i),
  accept and add nothing, is the recommendation.** This file joins the shared set **only if
  Phase 0 ratifies (iii)**, so a reader must check OQ-3's RESOLVED answer before treating it as
  contested.

**Standing coordination rule, matching the plans 82/85 and 83/85 precedent: whichever of plans
89 and 90 ships SECOND reads the LIVE text of every shared surface and re-derives ITS OWN edits —
if any — from what it finds, never from a pre-computed diff.** The rule binds the READ, not the
edit: it does not predict that the second plan changes any particular surface, and **nothing here
may be read as a claim about what plan 90 will write.** Concretely, if 89 ships first, plan 90
reads the `### Always` list live and counts it rather than trusting a number — and as drafted on
2026-08-26 **plan 90 proposes NO new `### Always` item at all**, so the live read exists to keep
its `### Verification` edit correctly placed, not to append after this plan's item. It likewise
reads the Done-When skeleton live and counts the standing lines rather than assuming four. **A
pre-computed delta applied blind is how the counts in this repo rot**, and both plans' own status
entries record earlier instances of it.

---

## Non-goals

- **Any mechanical check, `verify-*` gate, or hard-fail validator.** Plan 75's tripwire holds in
  both halves: **zero new PHASE-3.5 gate numbers, zero new check numbers, zero new validators.**
  D2 adds a checkbox and D4 decides whether it is ticked; neither blocks anything.
- **A coverage threshold, at any layer.** D5 — declined with its counter-argument recorded. A
  future plan wanting one must build a reported, non-gating measurement first.
- **AC→test-outcome mapping.** Chartered to the testForge20 e2e by `/devforge:verify`'s own text
  (fact 13). **This plan does not collect that deferral**, and a session that finds
  `--test-anchor` inert after this build has found the chartered state, not a regression.
- **Strengthening plan 86's regression-net declaration.** Its two bounds are shipped and its
  strengthening evidence is plan 86's Phase 7, which has not run (fact 14).
- **Changing who writes tests.** Inline-tests-by-default with a flagged-gap `qa-engineer` task
  (fact 15) is deliberate plan 09 / 15 design and is untouched.
- **Any change to `/devforge:verify`'s verdict inputs.** OQ-4 — `compute-verdict` receives no new
  field, and an unticked Tests box is visible, never blocking.
- **Any change to `verify-touched`'s behavior.** D4's recommended arm reads an existing key on an
  existing payload. **`_cmds_verify.py` is not edited** — arm (a), if ever ratified, is the only
  route that would touch it.
- **A new numbered constitution subsection.** D1 — `_UNIVERSAL_SECTIONS` is a closed literal
  tuple (fact 2), and this plan's only Python is D2's list.
- **Back-porting D1's rule into shipped consumer installs.** Explicit non-goal, matching plan
  86's stance: consumers receive it via `install.sh` / `update.sh`, and the interim drift report
  is the designed signal.
- **Guessing an ecosystem-default test command.** Fact 10's refusal stands. D4 makes the absence
  VISIBLE; it never fills it in.
- **Any change to plan 63's 13/7 model-invocable counts.** No command's frontmatter, invocation
  route or description is touched, so this plan contributes no delta and Phase 5's sweep should
  not go hunting a count to update.

---

## Dependencies + related

- **`86-FOWLER-REFACTORING-GAPS-PLAN.md`** — the constitution-editing precedent D1 follows
  exactly (titled bold block inside a tracked section, `_UNIVERSAL_SECTIONS` read as a
  CONSTRAINT never a surface to modify, drift-on-old-installs recorded as designed). Its F3
  regression-net lane is a **non-goal boundary**, not a dependency. ⚠ **If both ship in one
  release, consumers see two drift findings.**
- **`87-ARTIFACT-LANGUAGE-GUARD-PLAN.md`** — two precedents, both cited and neither touched: D4's
  **pure-append `### Always` item** (its D4 shipped item 15 with nothing renumbered) and D4's
  **advisory-WARN with a named strengthening trigger** (its D1). **Cited for the stances only.**
- **`75-INVESTIGATION-SEARCH-HARNESS-PLAN.md`** — the no-new-check-number / no-new-validator
  tripwire. **Both halves hold.**
- **`08-CLAUDE-MD-COMMAND-TRIM-PLAN.md`** — the always-on trim discipline binding Phase 4's
  one-line limit, now with an external number behind it (fact 16's 200-line target).
- **`66-PROPERTY-BASED-TESTING-AND-NARROWING-RULE-PLAN.md`** — the property-test lane and its
  PHASE-3.5 `verify-property-coverage` gate. **Untouched.** Recorded because it is the framework's
  one existing test-side gate, and a future session must not read D2's line as a second one.
- **`34-VERIFY-HYGIENE-FALSE-POSITIVE-PLAN.md` and plan 44** — the ADVISORY / WARN-only family
  D4's stance joins. **Cited for the stance; neither is touched.**
- **`51-DETECTION-COVERAGE-GAPS-PLAN.md`** — the origin of `/devforge:verify`'s regression gate
  (`_verdict.py:420` credits *"plan 51 Finding 1"*). **D6 documents its config key and changes
  none of its behavior**; `regression-gate` stays FAIL-SOFT and always exit-0 (fact 11b).
- **`90-E2E-TEST-LANE-PLAN.md`** — sibling, drafted concurrently the same day, **shipping second
  by execution order**. As of 2026-08-26 it **exists at repo root and is likewise NOT STARTED**.
  See `## Cross-plan coordination — plan 90` for the live-read rule that binds whichever of the
  two ships second.

---

## Context for next session

**The one sentence that governs everything here:** the framework RUNS tests well and never says
they must EXIST, so this plan states the obligation in the three standing places that already
carry the lint obligation — the constitution, the task skeleton, the Key Rules — and makes the
one path where zero tests run visibly honest instead of falsely green. **No gate is added.**

**Trap 1 — putting the constitution block in §3.4.** It is the obvious home and it is
undetected: `_UNIVERSAL_SECTIONS` is a closed tuple without `§3.4`, and the drift detector
iterates exactly that tuple (facts 2, 2a). **A rule there has no integrity mechanism at all.**
§3.5 is in the tuple and parses as one whole-body rule (fact 2b), so it needs no parser change.

**Trap 2 — thinking the standing Done-When lines are prose.** They are **Python** — a module-level
list in `breakdown_helper.py` (fact 3). The drafting brief for this plan framed D4 as the plan's
only Python candidate; **the live code says the opposite**, and D2 is the Python while D4's
recommended arm is instruction-only. Anyone who inherits the brief's framing will build the wrong
phase.

**Trap 3 — reading a ticked box as a passed test.** `mark-complete` ticks every Done-When box by
default (fact 4). **D2 without D4 ships a box that can read `[x]` over a run in which no test
command executed**, which is worse than the current state — today there is no box making the
claim. This is why D4 depends on D2 and why Phase 0 must resolve them together.

**Trap 4 — building a stderr WARN because it feels more mechanical.** Arm (a) is Python for a
predicted gap with no incident, and it produces an ephemeral line. **Arm (b) costs zero Python
and produces a durable annotated artifact** (fact 4), reading a field that is already on the
`pass` payload (fact 9b). Arm (a) is the named strengthening arm with a stated trigger, not the
first cut.

**Trap 5 — "harmonizing" the two mechanically-different Done-When wordings.** `Tests pass on
changed files` must contain a token from `/devforge:implement`'s scan list and must be
substring-unique in the skeleton (facts 4, 4a). A prettier wording that breaks either constraint
breaks D4 silently — the box simply never matches and is ticked as usual.

**Trap 6 — treating a green test suite as proof Phase 1 landed.** Fact 3c's test uses `assertIn`
per line and passes unchanged with a fifth line added; only its NAME becomes false. **Grep the
name, do not trust the suite.**

**Trap 7 — claiming any of this measures coverage.** It does not. D5 declines every number, and
the counter-argument that "coverage" is therefore unfalsifiable is **accepted, not answered**.

**The working tree is uncommitted throughout**, and several plans this file cites are
working-tree state, so any "shipped" claim about them means reviewed-but-uncommitted rather than
released. Re-check each from the code rather than from a Status line.

**Discovered while drafting, NOT owned by this plan and not fixed here:**

1. **`/devforge:constitute` regenerates `constitution.md` wholesale from `constitute.json`**
   (fact 2d), and its Phase-2 instruction says to draw on *"universal defaults applicable to
   every project"* without saying to carry the template's universal sections verbatim. So EVERY
   universal rule's survival into a consumer's rendered constitution — not just D1's — rests on
   the model composing it, with `verify-universal-defaults` as a WARN-only after-the-fact
   noticer. **This is a pre-existing seam this plan neither creates nor closes**, and it bounds
   how much D1 can be claimed to guarantee. A plan that wants universal sections seeded
   mechanically has a real subject here.
2. **`/devforge:constitute`'s Phase-2 example numbering does not match the shipped template.**
   `constitute/main.md:103` illustrates *"3.5 Documentation, 3.6 Function Length, 3.7 Check
   Before You Build"* while `src/constitution.md` ships §3.5 Universal Code Quality, §3.6 Design
   Principles, §3.7 Check Before You Build, §3.8 Design Fidelity — and §3.5 is separately used by
   that same file for the Forcing-Functions **config block** (`constitute/main.md:235`, which
   says so explicitly). **Recorded as an observation about existing text, not a defect this plan
   repairs**, but a session editing §3.5 should know the number is overloaded in the neighbouring
   command spec.
3. **`ac_verification_mode` and `regression_gate` are asymmetric in `/devforge:configure`.** The
   AC mode is prompted (Phase 4's Q12) while the regression gate is not prompted anywhere,
   despite the two sitting in the same **AC verification** group in `configure_helper`'s summary
   (fact 11a). **D6 documents the key; it does not resolve the asymmetry**, and arm (a) is the
   recorded route if a ratifier wants it resolved.

---

## When resuming work

1. **Read this file in full, then `## Verified mechanics` again** — **thirty rows** (seventeen
   numbered, 1–17, plus thirteen lettered: 2a, 2b, 2c, 2d, 3a, 3b, 3c, 3d, 4a, 9a, 9b, 11a,
   11b), each checkable in under a minute. **Count the live table rather than trusting this
   number if you add or remove one.** **If rows 2, 2a, 2b, 3, 4, 4a, 9b or 11 no longer hold,
   stop and re-derive**: they are D1's whole basis, D2's blast radius, D4's mechanism and D6's
   gap.
2. **Read `src/devforge/lib/breakdown_helper.py`'s `cmd_render_task_file` in full before touching
   it** — the optional `--property-targets` / `--dead-code-removal` lines, their byte-identity
   guarantees and the fixed-lines comment all constrain Phase 1.
3. **Read `src/devforge/lib/_implement/_cmds_complete.py` before writing Phase 1's tests** — the
   default-tick behavior, the `_UNVERIFIED_ANNOTATION` literal (leading space, literal em-dash)
   and the idempotence rules are what D4 rests on.
4. **Read `src/constitution.md` §3.5 in full before appending** — its seven rules' INLINE bold
   shape and its two closing `*Backed by*` lines fix where the new block goes (fact 2c).
5. **Re-verify every anchor before use. Grep the quoted string, never the `:NNN`** —
   `_DONE_WHEN_FIXED_LINES`, `_UNIVERSAL_SECTIONS`, `_UNVERIFIED_ANNOTATION`,
   `test_commands_run`, `four_fixed_done_when`, `tsc/lint/no-secrets/no-debug`,
   `pass NO \`--unverified-box\` arguments`, `do NOT invent an ecosystem-default guess`,
   `REGRESSION_GATE`, `Lint everything`, `## [Unreleased]`.
6. **Invoke `claude-code-guide` to re-verify Claude Code memory semantics before writing or
   amending `src/CLAUDE.md`** — this repo's rule is agent-invocation, not a doc read, and the
   same route is what Phase 6's anchor 4(b) owes. Fact 16's source URL
   (`https://code.claude.com/docs/en/memory`; the `docs.claude.com` path 301-redirects there) is
   recorded so the agent's answer can be checked, **not as an alternative to invoking it.**
   The load-bearing facts are that CLAUDE.md loads into context **every session** and that it is
   **context, not enforced configuration** (fact 16). **If a future version makes it enforceable,
   D3's honest bound changes and must be re-derived, not extended.**
7. **Route every edit through the house loops:** **python-engineer → python-reviewer, test-first**
   for Phase 1; **instruction-author → instruction-reviewer** for Phase 2 and Phase 5's
   plan-document edits; **instruction-author → instruction-reviewer + claude-code-guide** for
   Phases 3 and 4 and for Phase 5's `configure/main.md` edit (all ship into a consumer's
   `.claude/` or project root). **Phase 1 dispatches no instruction-author and Phases 2–5
   dispatch no python-engineer** — a phase that finds itself needing the other has crossed its
   own boundary and must stop.
8. **Do not let Phase 3's momentum turn D4 into a gate.** The clause marks a box unverified; it
   does not block the approve path, does not change an exit code, and does not reach
   `compute-verdict` (OQ-4). **A version of D4 that halts the run has left this plan**, and
   Phase 3's verify criteria exist to catch it.
9. **Check plan 90's ship status before touching any shared surface** (`src/CLAUDE.md`'s
   `### Always` list, `storage-rules.md`'s Done-When skeleton, and — only if OQ-3 ratified
   (iii) — `qa-engineer.md`). If plan 90 shipped first, **read those surfaces live and count
   what is actually there** before writing Phase 1's or Phase 4's edit. ⚠ **Do not assume the
   counts moved**: as drafted on 2026-08-26 plan 90 adds no `### Always` item and may add
   nothing to `storage-rules.md` at all, so the live read may well find the same fifteen items
   and four standing lines this plan was written against. **The rule is to look, not to expect a
   delta.**
