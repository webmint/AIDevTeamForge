# 129 — Grill Gate to Signal Recommendation Plan

**Created**: 2026-10-03
**Status**: **Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start. Nothing is built and nothing is measured.** ⚠ **Evidence class, repeated in every summary of this plan: ONE research diagnosis file (`RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md`), committed 2026-11-07 (untracked before), its numbers measured by a sibling session from local transcripts and NOT re-verified here; the live tree VERIFIED by grep and read on 2026-10-03; NOTHING built and NOTHING measured by this plan.** ⚠ **It REVERSES IN PART the ratified, built `85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md` on a VALUE claim** — not plan 85 D7's "the gate is slow" carve-out (this plan's `### The load-bearing argument` and Trap 1). ⚠ **Not committed before the maintainer decides the research file's own commit status (OQ-5).** ⚠ Numbered 129: a glob of `12[0-9]-*.md` on 2026-10-03 returns 120–128; other sessions work here, so re-check. ⚠ **Every `file:line` was read on 2026-10-03 — grep the quoted text, never the digits.**
**Branch:** `develop-2.0-init`

`/devforge:breakdown` refuses to decompose a plan until `/devforge:grill` has run for it (F1), at about an hour per run. Asked for conditions under which grill is RECOMMENDED instead, this plan proposes removing the gate and making the existing stakes hint (F5) grill's only driver, with a per-breakdown record that lets the install's own data later say whether grill pays.

---

## Evidence constraint

`81-EVIDENCE-V2-BENCHMARK-RUN.md` and `77-EVIDENCE-DISCOVERY-TO-LOCK-INVERSION.md` are **UNTRACKED private-client records. Neither may be committed, and neither may be quoted, excerpted, cited or paraphrased by content into this file or any other tracked file** — plan 85's own rule (`:17`).

This plan cites ONE file instead — `RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md`, "the research file" — as `124-PIPELINE-COST-REDUCTION-PLAN.md` does (`:8`); both were untracked until 2026-11-07. Its Disposition line (`:3`–`:6`) says it "names no client, no install path, no ticket, no component, and no symbol from any consumer codebase"; its populations are pseudonyms. **Two of its sentences characterize the benchmark report; whether a tracked file may carry them is OQ-5. This plan is NOT committed before the maintainer decides the research file's own commit status.** **[OQ-5 DECIDED 2026-11-07 by the maintainer: commit — the research file, plan 124 and this plan are committed together, so a tracked file may carry those two sentences.]**

No phase may introduce a client name, install path, ticket id, or any content of the two evidence files. Reaching for a benchmark number the research file does not state signals an unargued decision, not a licence to open an evidence file (plan 85 `:26`–`:28`).

---

## Origin & evidence

The evidence class in the `**Status**:` line binds every number below.

### The maintainer's statements, 2026-10-03

1. > "I'm thinking — maybe make the grill skill optional? It's too long and it also requires two [passes]..."

   *(maintainer's words, translated from Ukrainian by the drafting session; "[passes]" completes the trailing word)*
2. > "I always use Strict. Time is in fact the problem. Grill's value for me right now is frankly a bit doubtful, because v1 lives fine without it."

   *(maintainer's words, translated from Ukrainian by the drafting session)*
3. > "Draft it. But let's do it this way: can we conditionally define metrics by which grill would be RECOMMENDED?"

   *(maintainer's words, translated from Ukrainian by the drafting session)*

Statement 1 names two costs: wall-clock, and plan 85 D2's two passes (D6). **Statement 2 removes the policy knob:** plan 124's item 5 — the research file's L3 — keys the gate on `workflow_enforcement`, `Strict` = required (`124-…:25`), so a maintainer who always answers `Strict` keeps today's gate. **This plan supersedes L3; it does not build it.** Statement 3 is this plan's shape: a deterministic RECOMMENDATION — never a mandate, never a silent skip.

### What the research file measured

Its F-labels are written RF4, RF5, RF10 here, apart from this plan's F1–F10.

| Fact | Where | Value |
|---|---|---|
| Grill per run, benchmark install | RF5 (`:116`–`:122`) | ≈ 65 min (31 LLM + 34 agent); spec-check ≈ 26 min; the pair "about 1.5 h per feature, roughly a quarter of the v2 chain" |
| Benchmark credit (OQ-5) | RF5 | "Neither appears in the benchmark report's 'what v2 got right' list" |
| Grill table row | `:88` | 31 / 70 / 17 (LLM min / turns / helper calls) + 34 min agent; idle "grill 6 h" in one run (RF4, `:113`) |
| One real-work feature (client install D, v2 `2.0.12`) | RF10 (`:193`–`:226`) | both grill runs `RE-ENTER-UPSTREAM` → `spec`; `cycle_count: 2`; "the third pass went on to breakdown instead of a third grill"; the passes ending in grill cost 112 and 159 min main + 92 and 168 min agent; grill alone 52 + 58 and 75 + 101 min (`:209`); pre-implement ≈ 6.2 h main + ≈ 5 h agents vs a v1 median of ≈ 50 min; "Whether the two re-entries improved the plan is not measured; their cost is." |
| Verdict | §3 (`:250`–`:259`) | "Cost is certain and structural." · "Benefit is unproven on outcome. One v2 run, model not pinned, probe failed; the best v1 run passed." (OQ-5) · the improvement is concentrated elsewhere — "Not the setter round-trips, not the mandatory grill/spec-check, …" |
| What would settle it | §5 (`:276`–`:283`) | the plan-81 re-run with the model pinned, three or more runs, plus "an ablation … with grill and spec-check off" |

### The load-bearing argument — a VALUE claim, not "the gate is slow"

Plan 85 was ratified (D3, D4 on 2026-08-24; D1, D2, D5–D8 on 2026-08-25) with *"no incident behind this plan, no failing run, and no measured cost"* (`:40`–`:41`) and *"Nothing here rests on benchmark data"* (`:25`). Its D7 pre-named this reversal's obvious argument and routed it (`:957`–`:961`): *"the answer is profiling-driven optimization (plan 70's Phase 3, which opens from numbers only) — **NEVER gate dilution.** 'The gate is slow' is precisely the argument that manufactures a carve-out when no other route is named"*. D7's honest content: *"the number does not exist yet and Phase 5 must produce it"* (`:964`–`:965`); Phase 5 never ran.

**That routing is a COST argument that ASSUMES the gate's value.** Optimization makes a worthwhile step cheaper; it cannot say whether the step is worthwhile, and D7 could not ask — its plan forbade itself the data. **This plan reverses on a VALUE claim D7 did not have:** the cost is measured and structural (RF5, RF10, §3); the benefit is unproven, the best v1 run passed with no grill (v1 has no grill — RF5), and grill is not credited (§3, RF5); the policy owner doubts its value (statement 2). **Optimization cannot answer a value question, so D7's route does not bind.** D7's counter-argument named the alternative (`:1019`–`:1021`): *"decline D3+D5 until plan 70's Phase 2 produces a per-command number for grill, keeping only Phase 1."* **D7's ratification (`:940`–`:944`) DECLINED that alternative because plan 70's Phase 2 had no defined end; this plan re-opens that DECLINE on the ground that a measured number now exists (RF5, RF10).**

**Not claimed:** that grill is worthless. Claimed: a MANDATORY gate is unjustified at the measured price while its benefit is unmeasured; D5 builds the record that can settle it.

### The strongest case for keeping the gate, recorded in full

1. **Install D's two RE-ENTER verdicts.** On the one real-work feature both grill runs recommended `RE-ENTER-UPSTREAM` to `spec` (RF10), and a seed is written only when the user picks the matching re-entry (`src/commands/grill/main.md`, PHASE 7.2). **If those verdicts were right, grill caught twice what `/devforge:spec-check` and `/devforge:plan` missed.** That is unmeasured in both directions — RF10's own sentence.
2. **Detection dominance.** Plan 85 D2's defence (`:358`–`:359`): *"a mandatory single pass strictly dominates an optional zero passes on detection"*. Under this plan an unflagged plan gets zero passes unless the user asks for one.
3. **Recall where the signals are silent.** The five signals (F5) read plan SHAPE: a file count, a risk count, a dependency line, a sibling file, keywords. A wrong invariant in a four-file plan fires none of them. The gate attacked every plan; this plan's recommendation reaches only the flagged ones, and the flagged set was designed to be a minority.
4. **A human-centric principle stated the same day.** On 2026-10-03 the maintainer declined `110-IMPLEMENT-AUTO-APPROVE-PLAN.md` because the per-task gate is human-centric by design and its cost *"is latency, not quality, accepted by decision"* (`DEVELOPMENT-STATUS.md` `## Key Design Decisions` item 23, `:119`). A future session may read this plan as inconsistent with that decision. **It is not, and the distinction is stated here:** item 23 keeps a HUMAN read of every task's diff, whose value is the principle itself; grill is an LLM stage whose value is an empirical claim that its owner now doubts. Grill's own human gate — PHASE 7, where the user owns every non-clean verdict — is untouched (D1).
5. **Selection bias in the replacement.** The D5 record is observational: users grill the plans they worry about, so "recommended and run" against "recommended and skipped" is confounded. It can show association, never cause; the research file's §5 ablation stays the causal test.

**This case is not answered away.** Ratification is the maintainer weighing it against the measured price.

---

## What plan 85 built, verified against the live tree (2026-10-03)

**F1 — The gate.** `src/commands/breakdown/main.md:80` `## PHASE 0a.6: Grill gate (MANDATORY)`; `:87` runs `breakdown_helper verify-grill-ran --plan <resolved-path>`; exit 2 copies BLOCKED stderr and ends the turn (`:93`); `:95` offers `/devforge:grill`; `:97` reads presence and recorded adversary status only; `:99` seats it before PHASE 0b's Draft → Approved flip; `:101` says `0a.6` is local. **`:71` and `:72` end *"proceed to Phase 0a.6"*; `:71` also runs `plan_helper finalize-handoff` in PHASE 0a.5 when no `plan-handoff.json` exists and `plan.md` declares Pure-Builder Targets.**

**F2 — The verb.** `src/devforge/lib/breakdown_helper.py`: section comment `:2676`–`:2688`, `_render_blocked_grill_ran` `:2691`, `cmd_verify_grill_ran` `:2714` (read-only; passes when `grill.md` exists AND `_grill._state.adversary_ran()`), registration `:4066`–`:4097` (named `--plan`, explained `:4080`–`:4087`). The module docstring's subcommand list (`:3`–`:177`) does not name it. Tests: 21 matching lines in `tests/lib/test_breakdown_helper.py` from `:7749`; one docstring line, `tests/lib/_grill/test_state.py:112`.

**F3 — Grill state.** `src/devforge/lib/_grill/_state.py`: `_ADVERSARY_RAN_STATUSES = ("complete", "clean")` (`:58`); `class GrillState` (`:62`) — `phase`, `feature_dir`, `status`, `out_path`, `scope_files`, `agent_assignments`, `adversary_status` (`:76`), `plan_sha256` (`:85`), **no disposition**; `read_state` (`:106`) → `None` on absent/corrupt/non-object; `adversary_ran` (`:174`); `compute_plan_sha256` (`:204`), *"RECORDED ONLY"*. `src/commands/grill/main.md:337`–`:341` hashes `plan.md`'s raw bytes at grill's PHASE 6; nothing reads the hash.

**F4 — The disposition lives only in `grill.md`.** `src/devforge/lib/_grill/_report.py:384`–`:397` renders `## Disposition` / `**Verdict**: <DISPOSITION>` (plus ` (target: …)` on re-entry). `src/commands/breakdown/main.md:642` reads it for PHASE 4's `**Grill**:` line (`:628`), says *"nothing records that pick"*, and says the line *"is always present — Phase 0a.6 lets a run reach this point only when a grill report exists"* — **FALSE under this plan.**

**F5 — The stakes hint.** `src/devforge/lib/_plan/_stakes.py`: signals *"must fire on a MINORITY of plans"*; thresholds 8 and 4 (`:61`–`:62`); `compute_signals` (`:196`) returns `fires`, `file_count`, `risk_count`, `large_blast_radius`, `many_risks`, `new_dependency`, `new_data_model`, `security_relevant` (only I/O: a `data-model.md` existence check); `render_hint` (`:276`, copy `:299`–`:302`) says *"/devforge:grill is required before /devforge:breakdown"*. `plan_helper.py` `cmd_stakes_hint` (`:2431`) always exits 0; help says `/devforge:grill` (`:2889`) but `/grill` at `:119`–`:130`, `:2432`. `src/commands/plan/main.md:718` calls it a *"consider running"* hint; `:723` says breakdown *"refuses to decompose a plan until a grill has run for it"* — **FALSE under this plan.** `tests/lib/test_plan_stakes_hint.py`: 56 tests; `:727` pins `"required"`. ⚠ **It predates plan 85:** plan 50's P3, 2026-07-05 (`50-…:8`, `:68`), an opt-in-era nudge; plan 85's Status lists `4c08908` as *"the stakes hint"*. **Its minority tuning rests on one fixture and synthetic handoffs (plan 50 `:93`–`:95`); no real firing rate exists.**

**F6 — The breakdown handoff.** `src/devforge/lib/_breakdown/handoff_schema.py`: `SCHEMA_VERSION = "1.0"` (`:50`), locked in `__post_init__` (`:329`); `class Provenance` (`:164`); `class Breakdown` (`:296`), whose `dead_code_rows` was *"Appended LAST with a default"* (`:311`, field `:324`) **with no version bump.** Producer `cmd_finalize_handoff_breakdown` (`breakdown_helper.py:3205`; docstring list `:138`–`:171`) builds at `:3614`, writes at `:3631`, overwrites every run (`:3261`). Readers, none reading an unknown key: (i) `_implement/_handoff_reader.py` `read_breakdown_handoff` (`:86`), from named keys (`:214`–`:223`); (ii) `check-hygiene`, raw `tasks[].touched_files` (`_verify/_cli.py:470`); (iii) `check-dead-code-removal`, raw `dead_code_rows` (`:566`).

**F7 — PHASE 0b changes `plan.md`'s bytes.** `cmd_check_status_and_flip` (`breakdown_helper.py:519`) rewrites `Draft` → `Approved` or inserts a Status line; plans are written `**Status**: Draft` (`src/commands/plan/main.md:461`). **After the flip, or on a second breakdown run, a raw-hash comparison against grill's hash (F3) says "stale" with no content change.**

**F8 — Stops.** Breakdown's unconditional questions are `"Process this plan?"` (`:48`–`:51`) and `"Approve this breakdown?"` (`:644`–`:647`); the others are conditional (`:117`, `:119`, `:173`, `:325`, `:380`). `pick-other` proceeds without re-asking (`:56`); free text is not a pick (`:59`). Precedent: `## PHASE 0b.5: Model advisory (printed, never gating)` (`:123`), *"it asks no question, it gates nothing"*.

**F9 — Research handoff.** `src/devforge/lib/_research/handoff_schema.py` contains no "emission" — the matrix is the optional `emission-matrix.md`. It carries `plan_seeds.caller_enumeration` (`class CallerEnumeration` `:989`; `InboundCaller(helper_qn, caller_qn, file_line, …)` `:944`; `PlanSeeds` `:1066`; `Handoff.plan_seeds` `:1491`). `_discover/handoff_schema.py` has none.

**F10 — Invocation.** Plan 93's D1 (*"13/7 → 16/4"*) removed `disable-model-invocation` from grill (`src/commands/grill/main.md:1`–`:5`). `src/CLAUDE.md:47`: *"propose it, and once the user agrees, run it directly"*; plan 93 D2: *"One agreement per command; no bundling"*.

---

## Coordination with neighbouring plans

| Plan | State, 2026-10-03 | Relation |
|---|---|---|
| 85 | DONE (build); Phase 5 deferred | Reversed in part (D1); dated notes only. |
| 124 (untracked stub) | queued after 106–123 | Item 5 (L3) superseded; item 8's L10 (`:28`) untouched — RE-ENTER now arises only on an opted-in grill; item 7's ablation stands. |
| 93 · 82 · 50 · 110 | complete · DONE (build) · shipped · DECLINED | F10 · Non-goals · F5 · strongest case item 4. |
| 109 | Phase 0 CLOSED, unbuilt | Its `:329` quotes `breakdown/main.md:27`; an OQ-2 edit makes that history. |
| 126 | Phase 0 OPEN | May edit `breakdown/main.md` (`:501`); second to land re-reads live. |
| 111, 127, 128 | Phase 0 OPEN | No planned edit to this plan's `src/` regions (grep of plans 109–128); ledgers are shared and re-read live. |

**Queue:** numeric order. 109 ratified; 111, 126–128 Phase 0 OPEN; 112–124 stubs; 110 declined; 125 DONE. **129's position is the maintainer's call, recorded at Phase 0's close.**

---

## Phase 0 — ratification

Nothing below is ratified. Each of D1–D7 and OQ-1–OQ-5 gives the proposal, recommendation, strongest counter-argument — **recorded, not answered away** — and alternatives, and awaits the maintainer. Every verb, field and line of copy is UNRATIFIED until the close record fixes it. **No emitted sentence names plan vocabulary** ("D3", "plan 85", "Phase 0").

### D1 — Scope of the reversal within plan 85 *(OPEN — awaits the maintainer)*

| Plan 85 item | Here | Touches |
|---|---|---|
| D1 STRICT CLEAN | **KEEP** | nothing — it governs only *"whether PHASE 7's HUMAN GATE fires"* (`:212`–`:213`) |
| D2 2-pass quorum | **KEEP** (D6) | nothing |
| D3 gate seat + predicate | **REVERSE** | the seat, the predicate, *"ONE mandatory grill run per feature"* (`:373`) |
| D4 hash recorded, never enforced | **KEEP** (OQ-3) | nothing |
| D5 auto-accept of a clean run | **KEEP** | nothing |
| D6 Rule-1 amendment (amended by plan 93) | **REVERSE the "required" posture; KEEP the NARROWS list** | the *"what becomes mandatory is that the grill RAN"* clause; the list (user owns every non-clean verdict, four dispositions incl. KILL, cross-pick and re-entry arms, grill never edits `plan.md`/`spec.md`) stays |
| D7 cost line | **SUPERSEDED** | its routing (`### The load-bearing argument`) |
| D8 two mandatory stages | **ONE remains** (spec-check) | "Combined per-feature cost" (`:1036`–`:1038`) |
| OQ-1 name it, never run it | moot at breakdown | — |
| OQ-2 e2e anchors | anchors 1, 2, anchor 4's visibility half, the auto-accept rate and wall-clock survive; anchor 3 and anchor 4's gate half void | plan 85's Phase 5 |

**Not revived:** D7 kept a reduced *"mandatory profile"* and *"skipping refutation on mandatory runs"* REJECTED (`:967`–`:971`); this plan revives neither — every grill run is the full ratified shape.
**Why D5 stays:** plan 85's separability note (`:80`–`:81`) — *"(3) without (2) is a nicety"* — records auto-accept without a gate as coherent; a grill the user chose should still end silently when nothing survived.
**RECOMMEND as tabled.**
**Counter-argument:** **D5's stated purpose was keeping the gate from *"pure friction"* (`:77`–`:78`);** without the gate it survives only as "a nicety".
**Alternatives:** reverse D5 too (every grill asks) — a stop on runs the user chose, against statement 2; reverse D2 too — D6.

### D2 — The signal set *(OPEN — awaits the maintainer)*

**Proposal:** keep the five signals and both thresholds (F5). Retuning without data is preference; 56 tests pin today's behavior; D5's record can calibrate later.

| Candidate | Why not now |
|---|---|
| `layer_map` / `doc_impact` breadth (`BreakdownSeeds`, `src/devforge/lib/_plan/handoff_schema.py:318`, `:332`–`:340`) | no threshold basis |
| `specialist_consultation`, `dead_code_rows`, `pure_builder_targets` non-empty | may fire on most plans; unmeasured |
| Coupling, emission-matrix form | **not mechanically readable** (F9) — future candidate |
| Coupling, caller-enumeration form (a fix-path helper with ≥ 2 `inbound_callers`) | readable, but never fires on the discover lane, adds a third upstream file at two call sites, and may fire on most bug-mode research plans — against the minority rule |

Coupling was the evidence-linked candidate because §3 credits the emission matrix and Coupling decision point with v2's analysis advantage.
**RECOMMEND no new signal in v1;** the caller-enumeration form is the first future candidate. **Option (b), not recommended:** D5's record carries the raw maximum inbound-caller count, firing on nothing, for later fitting.
**Counter-argument:** **as the ONLY driver, minority-tuned thresholds may be too quiet** — plan 50 tuned them for this same opt-in regime, but from one fixture, never a measured rate (F5).
**Alternatives:** lower thresholds now (preference); every candidate (noise that trains users to ignore the line); option (b) (a field nothing reads yet).

### D3 — Where the recommendation surfaces *(OPEN — awaits the maintainer)*

**(a)** the end of `/devforge:plan` — exists (F5); copy flips (OQ-1). **(b)** `/devforge:breakdown`'s entry — one line when the signals fire and no grill completed; no new question:

| | Placement | Consequence |
|---|---|---|
| **(b1)** | PHASE 0a.6 keeps its number, in PHASE 0b.5's shape (F8) | `:71` / `:72` stay valid; the line prints after the first routine stop, before the Approved flip, and the next stop is PHASE 4 after decomposition (F8) — acting on it costs an interrupt or a cancelled decomposition |
| **(b2)** | PHASE 0a, after `render-pick-summary` (`:45`), before `"Process this plan?"` (`:48`), naming `cancel` as the route to grill first; printed again for the chosen plan on `pick-other` (`:56`) | no new question or option; PHASE 0a.6 deleted, `:71` / `:72` → "Phase 0b", `:101` goes |
| **(b3)** | inside `render-pick-summary`'s output | declined: couples the preview renderer to `_plan._stakes` and `_grill` |

**RECOMMEND (a) + (b2).** **Why (b) at all:** under the research file's L9 (`:241`–`:244`, a fresh session per command) the `/devforge:plan` hint is out of context; in RF10's single session it is in context but far back. Breakdown's entry is the decision point either way.
**Counter-argument:** **(b) repeats `/devforge:plan`'s line and costs a helper call per run.** Against (b2): **(i)** `pick-other` does not re-ask, so there the line has no stop after it; **(ii)** free text "grill first" at `"Process this plan?"` is not a pick (`:59`), so the copy must name `cancel`; **(iii)** the line runs before PHASE 0a.5, which creates a missing `plan-handoff.json` for a plan declaring Pure-Builder Targets (F1) — the advisory is then silent (`recommended: null`) while D5's record, computed at PHASE 5, may read `true`. (b1), seated after 0a.5, avoids (iii) at the cost of the no-stop problem.
**Alternatives:** (b1), (b3), (a) alone.

### D4 — The helper shape *(OPEN — awaits the maintainer)*

**Proposal:** DELETE `verify-grill-ran` (F2); add `breakdown_helper grill-advisory --plan <path>` — read-only, exit 0 on every path once argparse accepts the call (the `stakes-hint` contract). Stdout JSON:

| Key | Value |
|---|---|
| `recommended` | `compute_signals(...)["fires"]` over the sibling `plan-handoff.json`; **`null` when it is absent, unreadable or lacks `breakdown_seeds` — including a handoff-less plan before PHASE 0a.5 (D3 (iii))** |
| `signals` | the fired names, in `render_hint`'s reason order |
| `ran` | `grill.md` exists AND `adversary_ran(read_state(...))` (F2's two conditions) |
| `adversary_status` | raw state value; `""` when unreadable |
| `disposition` | the RECOMMENDED disposition from `**Verdict**:` (F4) **only when `ran` is true; `null` otherwise** — a run whose adversary did not complete has no grill verdict. Never the user's pick. |
| `stale` | only if OQ-3's outcome is its alternative (b) |
| `line` | helper-composed copy (OQ-1); `""` unless `recommended` is `true` and `ran` is `false` |

The command echoes `line` verbatim when non-empty (the `render_hint` precedent). The `**Verdict**:` parser lives in `_grill` beside its renderer; `breakdown_helper.py` already imports `_plan` and `_grill` function-local (`:751`–`:752`, `:2820`).
**Recompute, never persist:** no `_plan/handoff_schema.py` change, `_stakes.py` stays the one source, and **a persisted block would freeze plan-time thresholds past a later calibration.** Cost: two call sites compute the same thing.
**Delete, never keep:** the name encodes gate semantics; the frozen benchmark install is never updated, so no compatibility arm is owed.
**RECOMMEND as proposed.**
**Counter-argument:** **deleting a verb breaks anything scripted against it** — on 2026-10-03 its only live caller is `breakdown/main.md:87` plus its tests; plan files, `PLAN-STATUS-ARCHIVE.md`, the research file and a released CHANGELOG block name it as history.
**Alternatives:** a persisted `stakes` block in `plan-handoff.json` (declined above); line-only stdout (D5 and the tests need the underlying values).

### D5 — The measurement record in `breakdown-handoff.json` *(OPEN — awaits the maintainer)*

**Proposal:** `Breakdown` gains ONE nested record, appended LAST with a default as `dead_code_rows` was (F6): `grill_advisory` = `recommended` (`bool`/`null`), `signals`, `ran`, `adversary_status`, `disposition` (**non-null only when `ran` is true**, per D4). `finalize-handoff` computes it through `grill-advisory`'s function — **no new flag, nothing orchestrator-composed** — from the files present at PHASE 5, so it can differ from the PHASE 0a advisory (D3 (iii)).
**Schema version stays `"1.0"`:** `__post_init__` rejects any other value and the `_implement` reader passes the file's own, so a bump rejects every handoff on disk (F6).
**Reader tolerance (F6):** reader (i) does not name the field, keeps the default, and MUST NOT raise; (ii) and (iii) ignore it. **Staleness is not recorded** (F7).
**What it answers:** how often grill is recommended, and how often a recommended grill ran; joined by hand (no reader is built here) with `review.md`, `verification.md` and the re-entry seeds, association with downstream outcomes. **It cannot prove value** (selection bias, small n); it sits BESIDE §5's ablation, never instead.
**RECOMMEND as proposed.**
**Counter-argument:** **a record nothing reads is schema surface for a question that may never be asked**, and each run overwrites it (F6).
**Alternatives:** a separate `grill-advisory.json` (new artifact, `storage-rules.md` row, commit path); `grill-state.json` (exists only when grill ran).

### D6 — Plan 85 D2's two-pass quorum stays *(OPEN — awaits the maintainer)*

Plan 85's `## Non-goals` (`:1694`–`:1696`): *"do not let a later 'the gate missed something' observation convert into a quorum without re-arguing D2."* Written before D2 ratified a quorum, its principle binds both ways; **this is that re-argument.**
**For one pass:** D2 made CLEAN *"HARD to reach"* against the endorsement objection (`:298`–`:301`), an objection sized for a gate on every feature; statement 1 names the second pass as cost, which D2 says *"doubles the adversary half"* (`:320`–`:321`).
**For two:** an opt-in grill now runs mostly where signals fire — where recall matters most; changing it sweeps `_grill/_merge.merge_two_passes` (`src/devforge/lib/_grill/_merge.py:41`), grill PHASE 2/3 (`src/commands/grill/main.md:152`, `:190`) and tests; no single-pass baseline exists (`:322`–`:323`).
**RECOMMEND two passes.** The single-pass lever is named, unpulled; revival trigger: the D5 record plus a measured single-pass baseline.
**Counter-argument:** **statement 1 asked for exactly this cut, and this plan declines it.**

### D7 — Zero-escape-hatch compliance; no question at breakdown *(OPEN — awaits the maintainer)*

**Not D7's feared carve-out:** no run decides anything — the helper computes, the model prints a line it did not compose, and whether grill runs is the user's standing choice. The model's rule has no OR: print the helper's line when non-empty; never block; never ask.
**No `AskUserQuestion` offer:** "grill first?" on every flagged plan is a per-run skip prompt answered under time pressure, and a new stop. D3 (b2) reuses `cancel`.
**Invocation (F10, unchanged):** a user who picks `cancel` and asks for grill has given `src/CLAUDE.md:47`'s explicit yes; the model runs that one command, then proposes `/devforge:breakdown` separately. Free text at the question is not a pick (F8), hence the copy names `cancel`.
**RECOMMEND as stated.**
**Counter-argument:** **a recommendation the user can always decline is, from the pipeline's side, optional** — the policy governs the MODEL's rules, and this plan moves the decision to the user on purpose.

### OQ-1 — The advisory copy

Under-promise: *recommended because <reasons>; not run* — never unsafe, risky or wrong. **RECOMMEND** one reason vocabulary — `render_hint`'s phrases ("touches N files · new data model · security-relevant · introduces a dependency · N risks recorded") extracted into one `_stakes.py` function — and:
- **`/devforge:plan`:** `**High-stakes plan**: <reasons>.` / `/devforge:grill is recommended before /devforge:breakdown -- run it now while the plan is still fresh in context.` / `/devforge:grill <plan-path>`.
- **Breakdown advisory:** `Grill recommended for this plan (<reasons>); no completed grill run is recorded. To grill first, answer cancel and run /devforge:grill <plan-path>.`
- **PHASE 4 `**Grill**:` line:**

| `grill.md` | `ran` | `recommended` | Line |
|---|---|---|---|
| absent | false | `false` / `null` | `not run` |
| absent | false | `true` | `not run — recommended: <reasons>` |
| present | true | any | today's line (disposition; clean / not clean; seed present / absent) |
| present | false | any | `did not complete (adversary_status: <value>)`, `— recommended: <reasons>` when `true`; **no disposition** |

**Alternative:** keep the shipped heading `**High-stakes plan detected**`.

### OQ-2 — The workflow chains

The `plan → grill → breakdown` position appears in `src/CLAUDE.md:44`, `README.md:50`, `src/commands/breakdown/main.md:27`, `src/commands/plan/main.md:27`, `src/commands/implement/main.md:45`, `src/commands/fix/main.md:131` and `src/commands/fix/references/triage.md:54` (the FEATURE lane's bounce). **Options:** (a) mark it `/devforge:grill (recommended by signal)`; (b) drop it from the arrows, say it in prose.
**RECOMMEND (a)**, with no legend — plan 85 D6 RETIRED the bracket legend (`:699`–`:702`).
⚠ **Weak precedent:** `/devforge:research (optional)` in the breakdown, plan and implement chains contradicts `src/CLAUDE.md`'s *"required precondition"*, those chains omit discover, and two omit spec-check. Reported for routing, not repaired.
**Counter-argument:** **any step in an arrow chain reads as one every feature takes;** (b) is more honest and loses the position.

### OQ-3 — The stale-plan arm (`plan_sha256` mismatch) in v1?

**RECOMMEND NO** (F7). **Alternatives:** (a) hash with the `**Status**:` line normalized — diverges from the raw-bytes predicate plan 85 D4 ratified as *"IDENTICAL to plan 82's"* (`:526`), reopening both; (b) compare only while `plan.md` reads `Draft`, `null` otherwise — sound, one more branch, `null` on every re-run; the field then joins D4's JSON, never D5's record.

### OQ-4 — CHANGELOG landing and dated notes

**RECOMMEND** a `### Changed` line under `## [Unreleased]` (`CHANGELOG.md:8`; `### Changed` `:10`, `### Fixed` `:18`) plus a new `### Removed` for the verb, on `## [2.0.12]`'s precedent (`:31`). Only the `### Removed` line names `verify-grill-ran`; the `### Changed` line describes the behavior without naming the verb, so Phase 4's count check stays at 2. Plan 85's entry (`:65`, released `## [2.0.10]` at `:49`) is never edited; finished plans get ADDED dated notes (Phase 4).

### OQ-5 — Carrying the two research-file characterizations into a tracked file

The research file characterizes the benchmark report twice, and this plan carries both: RF5's *"Neither appears in the benchmark report's 'what v2 got right' list"* and §3's *"the best v1 run passed"* (the measured-facts table and the load-bearing argument). Its citing precedent, plan 124, is untracked too.
**Options:** **(a)** keep both — no client identifier, and the research file is the maintainer's own derived diagnosis naming no client; **(b)** drop both, resting the value claim on the RF5 / RF10 cost figures and statement 2.
**RECOMMEND (a)**, with the rule in the `**Status**:` line and `## Evidence constraint`: this plan is not committed before the maintainer decides the research file's own commit status. **[DECIDED 2026-11-07: the maintainer chose to commit the research file, plan 124 and this plan; OQ-5 is closed.]**
**Counter-argument:** **both sentences are, at one remove, content of the report the evidence constraint protects;** (b) leaves "costly and doubted" without "and not credited".

### Phase 0 close record

**OPEN — nothing ratified; no build phase may start.** ⚠ **Nothing is built and nothing is measured.** It closes in plan 125's shape (`125-VERIFY-FILE-BUGS-IMPORT-PLAN.md`, `### Phase 0 close record`): occasion; directive (non-English in English translation); pick-or-delegation per `98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md` D1; outcomes table.

#### Verify

- **Each** of D1, D2, D3, D4, D5, D6, D7, OQ-1, OQ-2, OQ-3, OQ-4 and OQ-5 has an explicit outcome (ratified / amended / declined), **checked BY NAME, never against a range.**
- D2 states whether option (b) was taken; D3 names (b1), (b2) or (b3); OQ-3 states no, (a) or (b); OQ-5 states (a) or (b) and the research file's commit status.
- **Phase 2's edit list is rewritten to the ratified D3 placement only, so Phase 2 carries no "under (b1) / under (b2)" fork.**
- OQ-4's outcome states how many CHANGELOG lines name `verify-grill-ran` after Phase 4 (2 as recommended); Phase 4's Verify uses that number.
- The record states 129's queue position, and whether each outcome is an explicit pick or a delegation.
- Every counter-argument and alternative above survives unshortened; `### The strongest case for keeping the gate` is unedited.

---

## Phases

**Nothing below starts before the close record exists. Build order 1 → 2 → 3 → 4; Phase 3 depends on Phase 1 only.**

⚠ **Departure from the commissioning brief, argued:** the brief put the verb deletion and copy flip in Phase 1 and `src/CLAUDE.md` in Phase 4. Here Phase 1 is ADDITIVE and Phase 2 is the whole switch — deletion, copy flip, every `src/` text — in ONE commit, so no commit ships a spec naming a deleted verb, a "recommended" hint beside a live gate, or emitted `CLAUDE.md` contradicting an emitted command. Plan 85 `:1456`'s rule: *"Either dispatch both before committing either"* (`:1477`).

### House rules for every phase

- Python: **python-engineer → python-reviewer**; markdown: **instruction-author → instruction-reviewer**; each loops until SHIP-READY.
- Every helper function gets its own test, written AND run the same turn; fixtures round-trip through real producers (`plan_helper finalize-handoff`, `grill_helper check-status-and-flip --adversary-status …`, the `_grill/_report` renderer).
- Targeted tests, then `python3 -m pytest tests/lib -q` green; output read via `rtk proxy` plus a file redirect.
- Commit by explicit path (never `git add -A`) as `<type>(plan-129): Phase N — …`; `git show --stat` lists only that phase's files and this plan; the identifier grep over the staged diff finds no client hit.

### Phase 1 — Additive helpers (D4, OQ-1's reason function)

#### Deliverables
- `src/devforge/lib/_grill/` — the `**Verdict**:` parser (F4), round-trip tested for all four dispositions and the re-entry form.
- `src/devforge/lib/_plan/_stakes.py` — OQ-1's reason function, extracted with no output change.
- `src/devforge/lib/breakdown_helper.py` — a function shared with Phase 3; `grill-advisory`; its module-docstring entry (`:3`–`:177`).
- `tests/lib/test_breakdown_helper.py` — no handoff → `recommended: null`, empty `line`; firing, no grill → `true`, signals, non-empty `line`; firing + `complete` and + `clean` → `ran: true`, a disposition, empty `line`; firing + `failed` → `ran: false`, `disposition: null`, non-empty `line`; `grill.md` without state → `ran: false`, `disposition: null`; exit 0 everywhere.

#### Verify
- **RED first:** the first `grill-advisory` test fails because the verb is missing, for no other reason; recorded with its command.
- `render_hint`'s output is byte-identical — the 56 tests pass unedited.
- `python3 -m pytest tests/lib/test_breakdown_helper.py tests/lib/test_plan_stakes_hint.py tests/lib/_grill -q` green; then the house rules.

#### Phase 1 record

**NOT STARTED.**

### Phase 2 — The switch (D3, D4, D7, OQ-1, OQ-2) — one commit

**Both loops. The grill frontmatter `description` is a Claude Code authoring surface: invoke the `claude-code-guide` agent by page and section heading and record a verbatim quote (house rule).**

#### Deliverables
- **Delete** F2's code ranges and test block; re-point `tests/lib/_grill/test_state.py:112` at `grill-advisory`. The module docstring names no `verify-grill-ran` (F2).
- **Flip the hint** (F5): `render_hint` per OQ-1; `test_plan_stakes_hint.py:727` renamed and inverted (asserts "recommended", no "required", keeps its "verdict" / "disposition" absences); `plan_helper.py` `:119`–`:130` and `:2432` aligned, `/grill` namespaced.
- **`src/commands/breakdown/main.md`** — the ratified D3 placement; F1's phase rewritten or deleted with `:71` / `:72`; F4's `**Grill**:` line per OQ-1's table; `:27` per OQ-2.
- **`src/commands/plan/main.md`** — F5's `:718` and `:723`; `:27` per OQ-2.
- **`src/commands/grill/main.md`** — `:3` (`description`), `:9`, `:17`, `:19` (its NARROWS list stays), `:75`, `:458` (Important rule 1).
- **`src/commands/spec-check/main.md:9`** — the clause making a grill run a precondition of `/devforge:breakdown` and the predicate comparison after it.
- **`src/commands/fix/main.md:251`** ("`/devforge:breakdown` blocks until a `grill.md` exists"); OQ-2's chains at `fix/main.md:131`, `:241`, `:295`, `fix/references/triage.md:54`, `implement/main.md:45`.
- **`src/CLAUDE.md`** — `:44`, `:47` ("the two required adversarial checks"), `:60`, `:98`–`:99`, `:162` (Hard Gates entry — DELETED).

#### Verify

```bash
grep -rn "verify-grill-ran\|verify_grill_ran" src/ tests/                    # → nothing
grep -rnE "Grill gate|Mandatory to RUN|refuses to decompose" src/             # → nothing
grep -rniE "required before .?/devforge:breakdown|requires that it ran|reach this point only" src/   # → nothing
grep -rn "when a blocked" src/   # → one hit: spec-check/main.md (:67), about /devforge:plan — true
```

- The third grep owns `src/CLAUDE.md:60`, `:99`, `grill/main.md:3`, `breakdown/main.md:642`; `README.md`, `DEVELOPMENT-STATUS.md` and the repo-root `CLAUDE.md` belong to Phase 4.
- `grep -rn "grill" src/commands src/CLAUDE.md src/agents` — every hit read; its disposition (edited / true as written) recorded.
- `grep -n "0a\.6" src/commands/breakdown/main.md` matches the ratified placement: nothing under (b2); the heading, `:71`, `:72`, `:101` under (b1).
- No command or reference file added — `scripts/emitters/claude.py`'s `_PROMOTED` unedited.
- `python3 -m pytest tests/lib/test_memory_lane.py tests/lib/test_agent_reachability.py -q` green (`devils-advocate` stays reachable via grill); the claude-code-guide quote recorded; the house rules.

#### Phase 2 record

**NOT STARTED.**

### Phase 3 — The record (D5)

#### Deliverables
- `src/devforge/lib/_breakdown/handoff_schema.py` — the nested record, appended last with a default; `SCHEMA_VERSION` untouched.
- `breakdown_helper.py` — `cmd_finalize_handoff_breakdown` (`:3205`) computes it via Phase 1's function; its docstring entry (`:138`–`:171`) names it; `src/commands/breakdown/main.md:665` names it.
- Tests: `tests/lib/test_breakdown_helper.py` (recommended-not-run, recommended-run, not-recommended, failed adversary → `disposition: null`); `tests/lib/_implement/test_handoff_reader.py`, `tests/lib/_verify/test_hygiene.py`, `tests/lib/_verify/test_dead_code.py` each read a handoff carrying the record.

#### Verify
- A pre-Phase-3 handoff, without the record, still reads through `read_breakdown_handoff`.
- `grep -n "SCHEMA_VERSION = " src/devforge/lib/_breakdown/handoff_schema.py` → `"1.0"`; the house rules.

#### Phase 3 record

**NOT STARTED.**

### Phase 4 — Docs and ledgers (OQ-4)

⚠ **Ledger edits wait until other sessions' uncommitted edits to the same files are committed.**

#### Deliverables
- `README.md` `:50` (OQ-2), `:59`, `:77`; `DEVELOPMENT-STATUS.md:42`; repo-root `CLAUDE.md:46` (the `/grill` row).
- `PLAN-STATUS-ARCHIVE.md` — ADDED dated notes: plan 23 (`:33`, `:147`), plan 85 (`:76`, `:239`), the Appendix `/grill` cell (`:311`); this plan's Index line and Entries record. `:233` (plan 82's entry) is history — left.
- `CHANGELOG.md` — OQ-4's lines.
- Dated notes: plan 85's Status line ("REVERSED in part by plan 129 — see its D1") and Phase 5 (void anchors, D1); `124-…:25` (L3 superseded).
- Left as history: plan 93 (8 `verify-grill-ran` lines), `124-…:12`, the research file, `PLAN-STATUS-ARCHIVE.md:249`, `:252`, `:254` (plans 90, 92, 94 cite plan 85's D7 wall-clock run — still runnable).

#### Verify

```bash
grep -niE "required before .?/(devforge:)?breakdown|requires that it ran" README.md DEVELOPMENT-STATUS.md CLAUDE.md   # → nothing
grep -c "verify-grill-ran" CHANGELOG.md   # → 2 with OQ-4 as recommended: Phase 4's own `### Removed` line under `## [Unreleased]`, and plan 85's entry under `## [2.0.10]` (`:65` on 2026-10-03). The Phase 0 close record fixes the expected count from OQ-4's outcome; any other count fails.
grep -rln "verify-grill-ran" . --exclude-dir=.git --exclude-dir=__pycache__   # → only plan files (this one included), PLAN-STATUS-ARCHIVE.md, CHANGELOG.md, the research file — never src/ or tests/ (Phase 2's grep already proved those empty)
```

- `git diff CHANGELOG.md` shows hunks only under `## [Unreleased]` (above `CHANGELOG.md:22`, the `## [2.0.12]` heading on 2026-10-03), so every released block including `## [2.0.10]` is byte-identical; the house rules.

#### Phase 4 record

**NOT STARTED.**

### Phase 5 — Consumer e2e — user-driven HARD GATE, DEFERRED by default, NOT run

⚠ **Deferred by default and NOT WAIVED.** Phases 1–4 are build-verified at best, never consumer-validated until this runs; **"done" never means Phase 5 passed.** ⚠ **The frozen benchmark install is never touched.**

1. **A plan firing no signal** reaches breakdown with no grill → no advisory line, no added stop; record `recommended: false`, `ran: false`.
2. **A plan firing a signal** reaches breakdown with no grill → exactly one advisory line naming the signals, no new question; record `recommended: true`, `ran: false`.

#### Verify
- Both anchors scored explicitly. A failure is recorded with its artifacts and mechanism: a line on anchor 1 is `compute_signals` over-firing or `line` composed when it should be empty; no line on anchor 2 is the placement; a wrong record is Phase 3.

#### Phase 5 record

**NOT RUN.**

---

## Non-goals

- **The spec-check gate** (plan 82; the research file's L3 keeps it, `:406`).
- **Deleting `/devforge:grill`, `_grill/`, `devils-advocate` or any grill reference file.**
- **Grill's finder / refuter internals**, or reviving D7's rejected reduced profile or refutation skip (D1).
- **Plan 124's L10** — cross-reference only. **L3's policy knob** — superseded.
- **Thresholds or signals tuned without D5's record** (D2); **a reader for the record** (D5).
- **Repairing the stale chains** (OQ-2); **touching the frozen benchmark install.**

---

## Context for next session

⚠ **Evidence class: ONE research diagnosis file (`RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md`), committed 2026-11-07 (untracked before), its numbers measured by a sibling session from local transcripts and NOT re-verified here; the live tree VERIFIED by grep and read on 2026-10-03; NOTHING built and NOTHING measured by this plan.**

**The one sentence that governs everything here:** **grill stops being mandatory because its cost is measured and its benefit is not; the stakes hint becomes its only driver, `/devforge:breakdown` prints one line instead of blocking, and every breakdown records whether grill was recommended and run, so the question can be answered from data.**

### Honest bounds
- Cost numbers: one benchmark install and one real-work feature, measured by another session.
- Signals read plan shape, not correctness (strongest case, item 3); their minority rate was never measured (F5).
- The record is observational and confounded (D5).
- D3 (b2)'s weak spots — `pick-other` and the handoff-less plan — D3's counter.
- Whether install D's RE-ENTER verdicts were right is unknown (RF10).

### Traps
**Trap 1 — reading this as plan 85 D7's "the gate is slow" carve-out.** It is a value claim D7's cost routing cannot answer (this plan's `### The load-bearing argument`); re-adding a gate "because 129 was about speed" misreads it.
**Trap 2 — assuming the stakes hint is new** — plan 50 shipped it; plan 85 flipped its copy (F5).
**Trap 3 — deleting D5 auto-accept with the gate** — D1.
**Trap 4 — persisting signals into `plan-handoff.json`** — D4.
**Trap 5 — an `AskUserQuestion` offer at breakdown** — D7.
**Trap 6 — computing staleness after PHASE 0b** — F7, OQ-3.
**Trap 7 — bumping `SCHEMA_VERSION`** — D5.
**Trap 8 — splitting Phase 2 across commits** — `## Phases`.
**Trap 9 — reading `disposition` as the user's pick, or recording it for an incomplete run** — D4.
**Trap 10 — reading this as contradicting the plan-110 decision** — strongest case, item 4.

### File anchors

Each phase lists its EDIT targets. **READ-ONLY (F-item sources):** `src/devforge/lib/_grill/_state.py` (`:58`, `:62`, `:106`, `:174`, `:204`); `_grill/_merge.py:41`; `_implement/_handoff_reader.py` (`:86`, `:214`–`:223`); `_verify/_cli.py` (`:470`, `:566`); `_research/handoff_schema.py` (`:944`, `:989`, `:1066`, `:1491`); `_plan/handoff_schema.py:318`; `src/commands/breakdown/main.md` (`:48`, `:56`, `:59`, `:123`, `:644`); `src/commands/grill/main.md:337`–`:341`; `src/commands/spec-check/main.md:67`; `CHANGELOG.md:65`; `PLAN-STATUS-ARCHIVE.md:233`; plans 50 and 93; `DEVELOPMENT-STATUS.md:119`; the research file.

---

## When resuming work

1. **Read this plan in full**, then plan 85's D3, D5, D7 and `## Non-goals`.
2. **Check `### Phase 0 close record` first.** While OPEN, nothing is ratified and no build phase starts.
3. **OQ-5 is decided (2026-11-07): the maintainer committed the research file, plan 124 and this plan.** Every other D and OQ still awaits Phase 0.
4. **Check the queue position** the close record names; plans run in numeric order.
5. **Re-verify F1–F10 by the quoted text.** `grep -rn "verify-grill-ran" src/` still hitting means the gate is live and this plan unbuilt.
6. **Use the house loops**, commit by explicit path, build Phase 2 as ONE commit (Trap 8), and keep the evidence class attached to every summary.
