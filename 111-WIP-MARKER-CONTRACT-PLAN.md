# 111 — WIP Marker Contract Plan

**Created**: 2026-09-24
**Status**: **Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start.** Every decision (D1–D5) and every open question (OQ-1–OQ-3) carries a recommendation and its strongest counter-argument, and each waits for the maintainer. ⚠ **Numbered 111 because a glob of `1??-*.md` at the repo root on 2026-09-24 returns 100, 101, 102, 104, 105, 106, 107, 108, 109 and 110 and no 111. The gaps at 76 and 103 are vacated and must not be reused.**

`.devforge/wip.md` is the crash-recovery marker `/devforge:implement` writes before each task. **Three sources state its contract and they disagree with each other**: the orchestrator's instructions in `src/commands/implement/main.md`, the prose in `src/commands/implement/references/crash-recovery.md`, and the Python in `src/devforge/lib/_implement/_wip.py` + `_state.py`. **Only the Python could enforce anything, and the Python has never executed** — its writer, its reader and its state dataclass have had no production caller since the day they were born. **The consequence is live and is not a tidiness complaint: PHASE 0's `resume` arm is not implementable as written**, because the `**Phase**` field it re-enters on is written once and never advanced (F8, D4). **A SECOND and INDEPENDENT defect sits beside it, and the two must not be bundled:** the five phase values the spec enumerates are not the eight the code validates (F6, D3). **That mismatch changes nothing today — the code never runs — and it becomes an immediate runtime failure the moment anyone wires it up** (D1's Arm A, Trap 5). **The unreachable code is the CAUSE; the underspecified `resume` is the effect.**

---

## Origin & evidence

⚠ **Evidence class, to be repeated in every summary of this plan: NO consumer incident, NONE CLAIMED, NOTHING MEASURED, and no benchmark run stands behind any line here.** Every defect below is a property of the files in this tree, established by reading them on 2026-09-24. **No runtime misbehaviour on any install has been observed**, and no phase of this plan may claim one. The four defects are: a factually wrong docstring, a spec sentence asserting a contract nothing enforces, an underspecified field progression, and an armed latent failure that fires only if someone wires the dead code up without reconciling the vocabulary first.

This repo is public. **This plan names no client, no install, no repo, no branch of a client, no ticket id and no session identifier**, and no phase of it may introduce one.

### Verified structure (2026-09-24)

⚠ **Line digits drift — grep the quoted text, never the digits.**

**F1 — Three symbols have no production caller.** An unfiltered grep over `src/` on 2026-09-24 for `write_wip_marker|read_wip_marker|clear_wip_marker|ImplementState` returns their definitions, their own docstrings, and exactly one live import. The three with no caller are **`write_wip_marker`** (`src/devforge/lib/_implement/_wip.py:88`), **`read_wip_marker`** (`_wip.py:130`) and **`ImplementState`** (`src/devforge/lib/_implement/_state.py:73`). Their only exercisers are `tests/lib/_implement/test_wip.py` and `tests/lib/_implement/test_state.py` (both files exist).

**F2 — One symbol IS live, and it is READ-ONLY for this plan.** `clear_wip_marker` (`_wip.py:172`) is imported at `src/devforge/lib/_implement/_cmds_commit.py:157` and called at `:694`, inside the `if not final:` guard at `:691`. The comment at `:684`–`:690` states why it must stay a guard: a FINAL-mode (cold `/devforge:fix`) run wrote no marker, *"so clearing one here would destroy another, possibly still-in-flight, `/devforge:implement` run's crash-recovery state. This branch must stay a `not final` guard, never an unconditional clear."* ⚠ **No phase of this plan touches that guard, that call or that comment.**

**F3 — Born unwired, not rotted.** `git log --oneline -S<symbol> -- src/` returns **exactly one commit for each of the four symbols**: `b66ed8d`, 2026-06-07, *"feat(implement): per-task execution loop command + helper"*. **No caller was ever added and none was ever removed.** ⚠ **This fact was established by the maintainer on 2026-09-24 and is the one item here not re-derivable by a file read — re-derive it with that exact command**, which is cheaper than the read and settles rot-versus-birth on its own.

**F4 — The ORCHESTRATOR is the live writer, reader and remover.** `src/commands/implement/main.md:61` — PHASE 0 reads `.devforge/wip.md`. `:144` — PHASE 2 step 2 writes it, field by field. It is removed by the orchestrator at three sites: `:68` (PHASE 0 `rollback`), `:69` (PHASE 0 `skip`) and `:320` (Stage B `skip`, *"Clear `.devforge/wip.md` (the orchestrator removes the file)"*). ⚠ **`main.md:320` and `_cmds_commit.py:694` are NOT a double clear** — they fire on different events, a skip versus an approved WIP commit. **Reporting them as a defect is a misread.**

**F5 — Even the one Python function that touches the marker calls none of the module's API.** `_cmds_preflight.py:306`–`:325`, `_check_wip_marker`, composes `root / ".devforge" / "wip.md"` itself and tests `.exists()`. It reads no field, so it neither uses `read_wip_marker` nor is constrained by any format. **The path literal is stated there a second time, independently of `_wip.py`.**

**F6 — Three divergent phase vocabularies for one field.**
- `_state.py:13`, the module docstring: *"phase is a string Literal constrained to exactly the seven loop phases."*
- `_state.py:39`–`:48`, `_VALID_PHASES`, a frozenset of **EIGHT**: `preflight`, `agent`, `verify`, `review`, `forcing_functions`, `gate`, `commit`, `complete`. **`__post_init__` at `:124` raises `ValueError` on anything else.**
- ⚠ **A GREEN test already pins that count, which makes the docstring falsifiable by RUNNING the suite rather than only by reading the file.** `tests/lib/_implement/test_state.py` asserts the phase set in **two** places: `test_valid_phases_constant_size` asserts `len(_VALID_PHASES) == 8` under the docstring *"`_VALID_PHASES` has exactly 8 entries (no accidental additions or drops)"*, and a second test enumerates all eight names under the docstring *"Every valid phase string is accepted."* **The repo therefore asserts eight in a passing test while the docstring two screens above it says seven.**
- The spec says **FIVE**: `dispatch` / `verify` / `review` / `forcing_functions` / `gate`, at `main.md:67` (the `resume` arm) and `crash-recovery.md:23` (the `**Phase**` bullet). `main.md:144` writes the field *"set to the phase about to run, starting at `dispatch`"*.
⚠ **`dispatch` does not exist in `_VALID_PHASES` — the code's name for that phase is `agent`.** `preflight`, `commit` and `complete` do not exist in the spec's list. **Only four names are shared.**

**F7 — A spec sentence asserts a contract that nothing enforces.** `crash-recovery.md:7`: *"PHASE 2 writes the file directly and PHASE 0 parses it back; `_implement/_wip.py` states the same field shape in code, and both ends must honour it."* Each clause about the orchestrator is true (F4). **The code end never runs (F1), so no validator constrains the file** — a hand-written marker with a misspelled field, a missing field or an invalid `**Phase**` value is accepted by every reader that exists. **A future session reads that sentence as ground truth and believes the format is code-constrained.**

**F8 — THE LIVE CONSEQUENCE. `**Phase**` is write-once and never advances.** `grep -n 'Phase\*\*' src/commands/implement/` returns **five hits — one write and four reads**: `main.md:144` writes it; `main.md:67`, `main.md:347`, `crash-recovery.md:17` (the fenced field block) and `crash-recovery.md:34` read or restate it. **No instruction at any of those five sites, or anywhere else in the command, tells the orchestrator to rewrite the marker as the loop advances through verify / review / forcing_functions / gate / commit.** ⚠ **`main.md:347` is the sharpest evidence and is easy to miss because the line is long:** the tooling-unavailable `fix-tooling` arm tells the user that on the next run *"`resume` re-enters the recorded task at its `**Phase**:` field — the verify leg (PHASE 5) re-runs from the top once the tooling is fixed"*. **That is only true if the field reads `verify`, and nothing ever sets it to `verify`.** So the field is underspecified: an LLM orchestrator may leave it at `dispatch` forever, `resume` then re-enters at dispatch and re-runs the whole task regardless of where the crash landed, and the five-value enumeration at `main.md:67` and `crash-recovery.md:23` describes a progression the spec never produces. ⚠ **Whether the marker SHOULD advance is D4's question, not an assumption this plan makes.**

**F9 — Plan 91 closed half of this deliberately and disclaimed the other half.** `91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md` is ✅ DONE. Its Phase-1 harvest at `:358` reported that `crash-recovery.md:7` then read *"written by the `_implement/_wip.py` helper module"* while `write_wip_marker` had no production caller. `:363` records the closure — the report was closed **by ruling the PROSE wrong** and rewriting `:7` to its current text — and then, verbatim: *"⚠ **What the fix did NOT do: `write_wip_marker` is STILL production-unreachable** (grep-verified 2026-08-29 …). The report was closed by correcting the claim about who writes the file, not by wiring the helper up. **That unreachability is a live fact this plan neither owns nor fixes.**"* Restated at `:678`. ⚠ **The current `:7` wording is plan 91's deliberate decision, not an oversight. This plan SUPERSEDES it; it does not correct a plan-91 error, and no phase may describe plan 91 as wrong.** ⚠ **The old string *"written by the `_implement/_wip.py` helper module"* NO LONGER EXISTS in this tree** — do not grep for it expecting a hit.

**F10 — Plan 110 records this and is COUPLED to the outcome.** `110-IMPLEMENT-AUTO-APPROVE-PLAN.md` is *"Phase 0 OPEN"*. Its Correction 1 (`:29`), F14 (`:94`–`:96`) and Trap 8 (`:538`) all record the unreachability. Nonetheless its **D7 RECOMMENDS at `:224` adding a new marker field *"at BOTH ends the tree already binds"*** — including `_wip.py`'s docstring, `write_wip_marker` and `_state.py`'s `ImplementState` — justified by quoting `crash-recovery.md:7`'s *"both ends must honour it."* Its Phase 1 Deliverables (`:352`–`:354`) and its `### File anchors` EDIT list (`:561`, `:563`) name `_state.py`, `_wip.py`, `test_state.py` and `test_wip.py`. ⚠ **Two further couplings, both first-order:**
- Plan 110's Phase 1 Verify (`:361`), its `## Non-goals` (`:500`) and its Trap 11 (`:544`) name `_state.py`'s *"seven loop phases"* docstring as one of three pre-existing stale statements it deliberately does NOT repair. **This plan takes ownership of exactly that one line (D3, Phase 1).** The other two stay unowned by both plans.
- **The ordering dependency is a first-class decision here (D5):** if this plan retires the unreachable code, plan 110's D7 scope and file anchors change; if it keeps the code, plan 110 pays to extend a dead mirror. **The fork below should be settled BEFORE plan 110 builds.**

**F11 — The birth plan does NOT own this, and it carries a false-match trap.** `07-EXECUTE-TASK-REDESIGN-PLAN.md` (SHIPPED 2026-06-07) introduced all of it: `:157` lists `ImplementState`'s fields with all eight phase names already in the `Literal`; `:159` lists `_wip.py`'s three-function API; `:380` makes a recovery read helper conditional — *"if needed beyond `_wip.read_wip_marker`"*; and `:169` is a Phase-1 smoke check that imports `write_wip_marker` only to print `Phase 1 substrate ok`. ⚠ **That check verified the symbol EXISTS; it never verified that anything CALLS it.** ⚠ **`PLAN-STATUS-ARCHIVE.md:20`, plan 07's entry, carries a pending item reading *"state-cardinality/departure-flagging e2e (run `/plan`, confirm `States:`/`DEPARTURE:` notes)"*. That is about `src/agents/architect.md:154` and has NOTHING to do with `_VALID_PHASES`' cardinality. A future session grepping `cardinality` will false-match it.**

**F12 — One more mention, not an owner.** `88-COLD-FIX-BUGS-LANE-PLAN.md:1382` lists `clear_wip_marker` inside a grep-string list. **It owns none of this.**

---

## Phase 0 — ratification

Nothing below is ratified. Each item states the decision, its options, a recommendation, and the strongest counter-argument, **recorded honestly rather than answered away**.

### D1 — The fork: WIRE, RETIRE, or DOCUMENT-ONLY

- **Arm A — WIRE.** Add CLI verbs (e.g. `write-wip` / `read-wip`) to `implement_helper` and rewrite PHASE 0 and PHASE 2 to call them instead of hand-writing and hand-parsing the file. ⚠ **Armed trap: `dispatch` is not in `_VALID_PHASES` (F6), so wiring WITHOUT first reconciling the vocabulary (D3) makes `__post_init__` reject the very first task of the very first run.** ⚠ **Tension that must be stated rather than slipped past: plan 110's Trap 8 (`:538`) says a phase that adds a helper verb for this marker *"has misread this"*. Arm A deliberately reverses that judgment; if Arm A is taken, the close record says so and Phase 4 updates plan 110's trap rather than leaving two documents contradicting each other.**
- **Arm B — RETIRE.** Delete `write_wip_marker`, `read_wip_marker`, `ImplementState` and their two test modules; keep `clear_wip_marker` (D2); rewrite `crash-recovery.md:7` so it no longer asserts a code-side contract. **Cost is near zero.** **What is lost, stated plainly:** `write_wip_marker`'s atomic write (`tempfile.mkstemp` + `os.replace`, `_wip.py:62`–`:80`), which the orchestrator's hand-write does not have and never had (OQ-1).
- **Arm C — DOCUMENT-ONLY.** Fix `_state.py:13` (seven → eight), rename `_VALID_PHASES`' member to D3's winning name, and reconcile the spec, leaving the code unreachable but no longer self-contradicting. ⚠ **Scope SETTLED here rather than left implicit: Arm C DOES edit the `_VALID_PHASES` literal.** The rename is one token in code nothing executes, so it carries no runtime risk, and the alternative — repairing the COUNT defect while preserving the NAME defect inside the same dead mirror — would leave Arm C re-creating this plan's own subject. ⚠ **Consequence a builder must plan for: under Arm C a `dispatch` ruling breaks the same tests Arm A would break** (Phase 1's Deliverables). **Cheapest**, but `crash-recovery.md:7` keeps asserting an unenforced contract and plan 110's D7 keeps paying to maintain a dead mirror.

**RECOMMEND B or C over A.** **Arm A buys atomicity nobody asked for at the price of rewriting two phases of the command**, and it is the only arm that can introduce a new runtime failure. **B and C differ only in whether the dead mirror is removed or repaired in place**; B is preferred between them because C leaves `crash-recovery.md:7` unfixable without saying something false.

**Counter-argument, recorded and NOT answered away:** **Arm B deletes the only code that states the marker's format as data.** After B, the format lives in prose in two files, and the next person who wants a validator writes it from scratch. **That is a real cost and the recommendation accepts it rather than dissolving it** — because a validator nothing calls has never prevented anything.

⚠ **The final call is the user's at this phase, and it is taken with F10's coupling visible.**

### D2 — If Arm B: the deletion boundary

**`clear_wip_marker` and its tests STAY.** The `if not final:` guard at `_cmds_commit.py:684`–`:694` is **untouched** — comment, guard and call (F2).

**RECOMMEND D2 as stated.** It is a boundary, not a trade-off: `clear_wip_marker` is live, the other three are not.

### D3 — One source of truth for the phase vocabulary, and where it lives

Whichever arm D1 picks, **exactly one place states the phase list and every other site cites it.** The decision must settle two things: **`dispatch` versus `agent`**, and **whether `preflight`, `commit` and `complete` belong in the recovery enumeration at all** — they are loop stages at which a crash leaves nothing to resume into the middle of.

⚠ **The scope of that second sub-question, stated here rather than left to a reader's inference: it reaches the PROSE recovery enumeration ONLY — `main.md:67` and `crash-recovery.md:23` — and NEVER `_VALID_PHASES`.** **The two are different lists answering different questions, not two copies of one.** `_VALID_PHASES` constrains `ImplementState.phase`, which records where the loop IS: `_state.py:4` says the object is *"created at preflight time and threaded through the per-task loop phases"*, so `preflight`, `commit` and `complete` are states the loop genuinely occupies, and dropping them would make `__post_init__` reject a legitimate state. The recovery enumeration answers the strictly narrower question of which values are a valid **resume target**. **So D3's one-home rule applies PER LIST, and `_VALID_PHASES`' size of EIGHT is pinned by the loop's structure, not by this decision — it is not D3's to change under any ruling** (F6).

**RECOMMEND**: under Arm B or C the single home is `crash-recovery.md`'s `**Phase**` bullet and `main.md:67`/`:144`/`:347` cite it; under Arm A the single home for the winning NAME is `_VALID_PHASES` and every prose site spells it that way. **On the name itself, RECOMMEND `agent` over `dispatch`** — it is the value the code validates today, so under Arm A it is the only choice that needs no code change at all, under B the choice is free, and under C it costs the one-token literal rename that arm now owns (D1's Arm C). **Picking the same name in all three arms keeps this outcome independent of D1.**

**Counter-argument, recorded:** **`dispatch` is the word the user-facing prose has used since 2026-06-07**, and `agent` names a noun where the other four values name verbs. **A vocabulary chosen for the code's convenience reads worse in the one place a human meets it.**

### D4 — Does `**Phase**` advance during the loop?

(F8.) Two coherent outcomes, and this plan does not assume either:
- **(i) It advances.** The spec gains an explicit instruction to rewrite the marker at each phase boundary, and `resume`'s five-value enumeration becomes true. **Cost: a marker rewrite per phase, at up to five points in a loop that currently writes it once.**
- **(ii) It is write-once.** The field is declared write-once, and `main.md:67` and `crash-recovery.md:23` stop enumerating five values. **`resume` then means re-run the task from the top**, and `main.md:347`'s *"the verify leg (PHASE 5) re-runs from the top"* sentence must be repaired, because under (ii) the whole task re-runs, not only the verify leg.

**RECOMMEND (ii), write-once.** **It is what the spec already produces**, so it makes the documents true without changing runtime behaviour, and re-running a task from its checkpoint is the safe re-entry: the working tree after a crash is unverified, and re-entering at `gate` would present a diff nothing re-checked.

**Counter-argument, recorded and NOT answered away:** **(ii) throws away real work.** A crash during the review panel discards a completed agent run and a completed verify leg, and the user pays for both again. **That is exactly the cost the `**Phase**` field was invented to avoid**, and (ii) is an admission that the field never delivered it.

⚠ **Do not read a recommendation as a ruling. The user rules here.**

### D5 — Ordering against plan 110

**RECOMMEND that D1 be ratified before any build phase of plan 110 runs.** What changes in plan 110 under each arm:
- **Arm A** — plan 110's D7 recommendation becomes cheap and correct, its Trap 8 becomes false and needs rewriting, and its Phase 1 gains a helper-verb dependency it does not currently have.
- **Arm B** — plan 110's D7 alternative (a) (*"instruction-only"*, `:231`) becomes the only available arm, and its Phase 1, its Phase 1 Verify and four of its EDIT anchors cease to exist.
- **Arm C** — plan 110 is unchanged except that `_state.py:13` is no longer one of its three named un-repaired stale statements (F10).

**Counter-argument, recorded:** **plan 110 sits behind six unratified plans and will not build soon** (its own F19), so the ordering may resolve itself. **The recommendation stands anyway**, because the cost of stating the dependency is one sentence and the cost of missing it is plan 110 building a mirror this plan then deletes.

### OQ-1 — Under Arm B, is the lost atomic write replaced?

**RECOMMEND recording the loss and replacing nothing.** The orchestrator's hand-write has never been atomic, no torn marker has been observed, and a torn marker is survivable: `read_wip_marker`'s own contract already returns `{}` for a present-but-unparseable file, and the live reader is an LLM that can see a truncated file.
**Counter, recorded:** **"nobody has seen it" is not "it cannot happen"**, and a torn marker at exactly the wrong moment is a crash-recovery artifact that fails at the one job it has.

### OQ-2 — Under Arm B or C, does `_check_wip_marker` grow a format assertion?

It currently tests `.exists()` and reads no field (F5). **A cheap middle path exists**: have it parse the marker and report an invalid `**Phase**` value, restoring some code-side enforcement without Arm A's two-phase rewrite.
**RECOMMEND NO.** Its job is the sole-detector invariant (`crash-recovery.md:28`), it runs at per-task entry where a marker should be ABSENT, and a format check there fires only in the state the function already treats as an invariant violation.
**Counter, recorded:** **it is the only Python that runs anywhere near this file**, so declining it means Arm B leaves zero code-side enforcement by choice rather than by accident. **The close record should say that out loud.**

### OQ-3 — Where the ledger entries land

**Posed, not decided here.** The `CHANGELOG.md` entry goes under whichever unreleased section is in flight, **re-verified LIVE at build time**, never as an edit into a released version block. `PLAN-STATUS-ARCHIVE.md` gains this plan's `## Index` line and its `## Entries` record — **both shapes or neither**, per that file's own `## Index` preamble.
⚠ **Under Arm B the CHANGELOG entry describes a deletion of code no consumer ever executed. It must say that, and it must not be worded as a fix to observed behaviour.**

### Phase 0 close record

**PENDING — nothing is ratified.**

#### Verify

- The record names **each** of D1, D2, D3, D4, D5, OQ-1, OQ-2 and OQ-3 with an explicit outcome (ratified / amended / declined), **checked BY NAME, never against a range**.
- **D1's outcome names ONE arm — A, B or C.** A close that ratifies "the fork" without naming an arm has not closed D1, because Phase 2's entire content is the arm.
- **D3's outcome states the winning literal (`dispatch` or `agent`) and names the single file that owns the list.** Phase 1 may not invent either.
- **D4's outcome states advance-or-write-once explicitly**, and states what happens to `main.md:347`'s *"the verify leg (PHASE 5) re-runs from the top"* sentence under it.
- **The record quotes plan 91's disclaimer (F9) and plan 110's D7 (F10)**, so the decision is visibly taken with the coupling in view.
- **Every counter-argument above is still present, unshortened** — including D1's lost-validator concession, D3's readability objection, D4's discarded-work cost and OQ-2's zero-enforcement admission.
- ⚠ **Ratification changes no evidence class: NO consumer incident, none claimed, nothing measured.**

---

## Phases

Phase 0 is the section above; **nothing below starts before its close record exists.**

**Build order, and its one forced dependency: Phase 1 precedes Phase 2 under every arm.** Under Arm A that ordering is load-bearing rather than tidy — wiring the helper before the vocabulary is reconciled makes `__post_init__` reject the first task (D1, Trap 5). Phase 3 follows Phase 2. Phase 4 runs last.

### Phase 1 — Reconcile the phase vocabulary

**Route: instruction-author → instruction-reviewer for the markdown; python-engineer → python-reviewer for any `.py` edit, with a test per function written AND run in the same turn.** Commit by explicit path.

#### Deliverables

- The single phase list, at the home D3 fixed, in the vocabulary D3 fixed. ⚠ **Under Arm C this is TWO edits in ONE change, not one:** the prose home per D3, **and `_VALID_PHASES`' member renamed to the same winning name**, because D1's Arm C owns that edit. **They land together or the arm has not been executed** — a prose-only Arm C ships the very vocabulary mismatch the arm exists to remove, and **the green suite would not catch it**, because the existing assertions keep passing against the unrenamed literal (this phase's Verify, and Phase 2's Arm C Verify, both check for it). ⚠ **Under Arm A the code literal IS the home, so it is one edit. Under Arm B `_VALID_PHASES` goes with the file at Phase 2 and there is nothing to rename.**
- `_state.py:13`'s *"exactly the seven loop phases"* — corrected, or deleted with the file under Arm B. ⚠ **This line is one of the three pre-existing stale statements plan 110 explicitly declines to repair (F10). This plan owns it now, and Phase 4 records the transfer.**
- ⚠ **ONLY if D3 ruled `dispatch` the winning name, and then under Arm A or Arm C** — under Arm B the affected modules are deleted or reduced by Phase 2 regardless of D3, so the question is moot there: the test sites that hardcode the LOSING name, updated in the SAME change as the literal. ⚠ **Find the affected MODULES by grepping the `ImplementState` import across `tests/lib/_implement/` — today exactly `test_state.py` and `test_wip.py` — then find the phase-value sites inside those modules. Enumerate at build time; carry no count from this document.** ⚠ **Do NOT grep `"agent"` across that directory: most hits there are the agent-NAME field (`agent_name=`, `"agent": "backend-engineer"`, `r["agent"]`) and are NOT phase values** — one such hit sits two lines from a real one inside the same test. **Known failures: in `test_state.py`, the eight-name literal list and the `dataclasses.replace(state, phase=…)` call with its assertion, which re-runs `__post_init__` and raises once the losing name leaves `_VALID_PHASES`; in `test_wip.py`, `test_full_cycle`'s state construction and its `Phase` round-trip assertion.** ⚠ **One site assigns the name inside the frozen-assignment test; CLASSIFY it at build time rather than assuming** — a frozen dataclass may raise on `__setattr__` before validation runs, in which case that site needs no change. ⚠ **`test_valid_phases_constant_size` is NOT one of these: a rename SWAPS one member for another and the count stays 8** (D3). **Editing that assertion would put a real bug into the suite under cover of an expected update.** ⚠ **Under D3's RECOMMEND (`agent`) nothing in either file changes and this phase touches neither.**
- `main.md:67`, `main.md:144`, `main.md:347` and `crash-recovery.md:23` — each cites the single home, and each carries D4's ruling on whether the field advances.
- ⚠ **`crash-recovery.md:17`'s fenced field block keeps `**Phase**: <phase>` unchanged** — it states the field's presence, not its vocabulary.

#### Verify

- `grep -rn "dispatch" src/commands/implement/` returns **no hit that is a marker VALUE** once D3's literal has landed. Hits that are prose about dispatching the agent are classified as prose, **one at a time**, and stay byte-unchanged. ⚠ **`main.md:148`'s heading `Dispatch the implementing agent` is capitalised and does not match a case-sensitive grep for the marker value** — a sweep run case-insensitively must classify it, never edit it.
- **Under Arm A or C:** `grep -n "seven loop phases" src/devforge/lib/_implement/_state.py` **returns nothing**, checked at this phase's close. ⚠ **Under Arm B this criterion does NOT apply at this phase's close** — the docstring goes with the symbols Phase 2 deletes. **Phase 2's Verify is the one that proves it gone, and it is named there by this bullet.** ⚠ **Arm B is not permission to leave the line unproven: it is proven one phase later, by name, and F10 commits this plan to owning it.**
- **The phase list appears in exactly one place as an enumeration**, verified by grepping the winning literal across `src/` and confirming every other hit is a citation rather than a second list. ⚠ **ONE carve-out, and it is an application of the rule rather than an exception to it:** `_VALID_PHASES` and the prose recovery enumeration are two DIFFERENT lists answering different questions (D3), so under Arm A **and under a completed Arm C** the winning literal appears in BOTH — the prose home and the code list — **with neither citing the other, and that is the CORRECT state, not a second copy of one list.** **Check by classifying every hit as prose-enumeration, code-list or citation; a hit that is none of those three is the failure this criterion exists to catch.**
- **`git diff` shows no change to `src/devforge/lib/_implement/_cmds_commit.py`.**
- Under any `.py` edit: the targeted module's tests, then the full `tests/lib` suite, are green, and python-reviewer returns SHIP-READY or every finding is fixed.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — Execute the arm D1 picked

**Route: per arm. Arm A and Arm B touch Python (python-engineer → python-reviewer); Arm C is instruction-only.** Commit by explicit path.

#### Deliverables

- **Under Arm A** — the `implement_helper` verbs, their subparser registration, their tests, and the PHASE 0 / PHASE 2 rewrites that call them. ⚠ **Phase 1 must already have landed** (D1's armed trap).
- **Under Arm B, and the two modules are treated differently ON PURPOSE** — `write_wip_marker` and `read_wip_marker` deleted with `_wip.py`'s module docstring reduced to the one surviving function, **the FILE surviving because `clear_wip_marker` is live in it** (F2); **`ImplementState` deleted and `src/devforge/lib/_implement/_state.py` deleted AS A FILE**, because nothing in it survives the class — ⚠ **`_VALID_PHASES` and `_require_nonempty` are referenced only from `__post_init__` and from that file's own docstrings, so a gutted `_state.py` would be an orphan with no caller and no purpose, which is the exact drift class this plan exists to remove.** Then `tests/lib/_implement/test_state.py` deleted, its subject being gone, and `tests/lib/_implement/test_wip.py` reduced to `clear_wip_marker`'s coverage.
- **Under Arm C** — nothing BEYOND what Phase 1 already delivered. ⚠ **The `_VALID_PHASES` rename D1's Arm C owns is PHASE 1's first Deliverable, not this phase's:** Phase 1 reconciles the vocabulary, Phase 2 executes the arm, and a rename is vocabulary reconciliation rather than arm execution — **which is also why the build-order invariant puts the vocabulary before anything wired to it.** **The phase is recorded as a deliberate no-op ON THE SYMBOLS, with the grep that shows `write_wip_marker`, `read_wip_marker` and `ImplementState` still present, not silently skipped.**

#### Verify

- **`clear_wip_marker` still resolves from `_cmds_commit.py`** — asserted by importing it in a test, not by reading the import line.
- **`git diff` shows no change to `_cmds_commit.py`'s `if not final:` guard, its call, or the comment above them** (F2, D2).
- Under Arm B: `grep -rn "write_wip_marker\|read_wip_marker\|ImplementState" src/ tests/` **returns nothing**; **`grep -rn "seven loop phases" src/devforge/lib/_implement/` returns nothing** — ⚠ **this is the criterion Phase 1's Verify deferred under this arm, it is DIRECTORY-scoped so it holds whether `_state.py` survived the deletion or went with it, and Phase 4 records the ownership transfer it discharges** (F10); and the full `tests/lib` suite is green.
- Under Arm A: a marker is written and read back through the real verbs, and `**Phase**`'s first written value is accepted by `__post_init__` — **the specific failure D1's armed trap names.**
- Under Arm C: the recorded no-op names the three symbols and states that they remain unreachable by design. ⚠ **It ALSO confirms Phase 1's `_VALID_PHASES` rename already landed** — `grep -n` the winning literal in `src/devforge/lib/_implement/_state.py` returns it — **so an Arm C that reached this phase with the prose renamed and the code literal untouched is caught HERE rather than shipping.** ⚠ **A green suite is NOT evidence on this point: the existing assertions hardcode the CURRENT name, so they pass precisely when the rename was skipped** (Phase 1's Deliverables).
- python-reviewer returns SHIP-READY on any `.py` edit, or every finding is fixed.

### Phase 3 — Bring `crash-recovery.md:7` into line

**Route: instruction-author → instruction-reviewer.** Instruction-only. Commit by explicit path.

#### Deliverables

- **`crash-recovery.md:7`** — rewritten so every clause is true after Phase 2. Under Arm B or C it no longer asserts that `_implement/_wip.py` states the same shape in code; under Arm A it states the helper as the writer and the orchestrator as its caller.
- ⚠ **The commit message and this plan's own record state that this edit SUPERSEDES plan 91's closure rather than correcting a plan-91 error.** Plan 91 ruled the prose wrong on the evidence it had and disclaimed the reachability question explicitly (F9). **The wording changes because this plan changed the code end, not because plan 91 got it wrong.**
- ⚠ **`91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md` IS NOT EDITED.** It is a finished plan and its record is frozen.

#### Verify

- `grep -n "both ends must honour it" src/commands/implement/references/crash-recovery.md` agrees with the arm: **nothing under Arm B or C; the sentence present and true under Arm A.**
- **Every clause of the new `:7` is checkable against the tree**, checked one clause at a time rather than as a sentence.
- **`git diff` on `91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md` is empty.**
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 4 — Cross-reference sweep

**Route: instruction-author → instruction-reviewer. Docs and plan ledgers only.** ⚠ **Other sessions build in this checkout. Re-read `git status`, read each file LIVE, stage by hunk, check `git diff --cached --stat`, and commit by explicit path — never `git add -A`.**

#### Deliverables

- **`110-IMPLEMENT-AUTO-APPROVE-PLAN.md`** — its Correction 1 (`:29`), F14 (`:94`–`:96`), D7 (`:224`, and alternative (a) at `:231`), Trap 8 (`:538`), Phase 1 Deliverables (`:352`–`:354`), Phase 1 Verify (`:361`), `## Non-goals` (`:500`), Trap 11 (`:544`) and `### File anchors` (`:561`, `:563`). ⚠ **Each is an edit or a recorded verified no-op, per D5's ratified outcome.** ⚠ **Plan 110 is another session's open plan — if it is mid-build, this sweep waits rather than racing it.**
- **`PLAN-STATUS-ARCHIVE.md`** — this plan's own `## Index` line and `## Entries` record. ⚠ **No other plan's record in that file is touched**, including plan 07's.
- **`src/CLAUDE.md`'s `### Crash Recovery` section and `### Always` item 14** — an edit or a recorded verified no-op. ⚠ **`src/CLAUDE.md` is contended by other open plans; stage by hunk.**
- **`src/devforge/storage-rules.md`** — an edit or a recorded verified no-op for `wip.md`'s field set.
- **`CHANGELOG.md`** — one entry, per OQ-3. ⚠ **Never an edit into a released version block.**

#### Verify

- **Every site above is recorded as an edit or an explicit verified no-op, with the grep that shows it.**
- **The `state-cardinality` false-match trap is recorded in this plan's own traps and `PLAN-STATUS-ARCHIVE.md:20` is BYTE-UNCHANGED** — `git diff` proves it (F11).
- **`grep -rn "write_wip_marker\|read_wip_marker\|ImplementState\|both ends must honour it" *.md src/` leaves no sentence claiming a state the tree no longer has**, with one exception stated explicitly: **hits in `CHANGELOG.md` and in FINISHED plan files are frozen historical records of what was true on their own dates and are left alone.**
- **The transfer of `_state.py:13` from plan 110's un-repaired list to this plan is recorded in both directions** — named in plan 110's edit, and named here (F10).
- **No line belonging to any neighbouring plan is altered or reflowed** — checked with `git diff --cached --stat` after staging, never on the unstaged view.
- **No ledger sentence claims any consumer-side failure was observed.**

---

## Non-goals

Each is argued, not merely listed.

- **Re-opening plan 91's closed report.** Its ruling stands on the evidence it had. **This plan supersedes the wording and must not describe plan 91 as wrong** (F9, Phase 3).
- **Touching `clear_wip_marker`'s one live call site or its `if not final:` guard.** The comment above it states a cross-command hazard this plan has no standing to re-litigate (F2, D2).
- **Claiming any observed consumer-side failure.** Nothing has been observed. **A summary that upgrades "unreachable code" to "a bug users hit" has falsified this plan's evidence class.**
- **Any change to `/devforge:implement`'s approval gates, caps, or the review panel.** None is reached by any decision here.
- **The `.claude/commands/` → `.claude/skills/` migration question.** Out of scope, no owner, framework-wide, and the `/devforge:<name>` namespace question under it is unverified. **No phase may act on it.**
- **Repairing the two remaining pre-existing stale statements plan 110 named** — `DEVELOPMENT-STATUS.md:133`'s `## Source Repo Checkpoint` sentence, and `_cmds_preflight.py`'s *"Phase 9"* naming at `:12`, `:310` and `:323`. ⚠ **`_cmds_preflight.py:310` and `:323` sit in a function this plan reads (F5), and `:323` is inside a user-facing stderr string, which makes it the most tempting drive-by.** **They are named so they are not edited by accident, not so they are fixed here.** ⚠ **`_state.py:13` is the exception — this plan DOES own it** (F10, D3).
- **Nothing is done to any installed consumer.** A frozen benchmark install exists; **this plan neither updates nor edits it and sends it no message.**

---

## Context for next session

⚠ **Evidence class, repeated: NO consumer incident, none claimed, NOTHING MEASURED. A code read of this tree on 2026-09-24 plus one `git log -S` check.** ⚠ All line digits drift — **grep the quoted text, never the digits.**

**The one sentence that governs everything here:** **the WIP marker has three divergent contracts, the only one with executable force has never executed, and the live consequence is that PHASE 0's `resume` arm is not implementable as written.**

### Honest bounds

- **Nothing is measured.** No consumer has reported a bad recovery, and this plan would not know if one had.
- **The `**Phase**` defect is a reasoning defect, not an observed one.** It says an LLM orchestrator *may* leave the field at `dispatch`. **Nobody has checked what real orchestrators actually write there**, and this plan does not claim to know.
- **D4 (ii) is the cheap answer and it discards work.** Making the documents true by lowering what they promise is a legitimate move and it is not free.
- **Arm B removes the only machine-readable statement of the marker's format.** After it, the format lives in prose. **That is accepted, not dissolved.**
- **Plans execute in numeric order, and every lower-numbered plan still open sits ahead of this one.** ⚠ **Do not carry a COUNT of them from this document** — plan 110's F19 counted them on 2026-09-23 and the set moves. **Re-derive it from each file's own `**Status**:` line.** **This plan will not be built soon, and every `file:line` here will have drifted first.**

### Traps

**Trap 1 — reading this as dead-code cleanup.** It is a contract-divergence plan. **The unreachable code is the CAUSE; PHASE 0's underspecified `resume` is the live effect** (F8). A close record that ratifies a deletion and leaves D3 and D4 open has fixed nothing.

**Trap 2 — grepping for plan 91's old string.** *"written by the `_implement/_wip.py` helper module"* NO LONGER EXISTS in the tree (F9). A session that greps it and gets nothing will conclude the finding is stale. **It is not; grep `both ends must honour it` instead.**

**Trap 3 — describing plan 91 as wrong.** It ruled deliberately and disclaimed the rest in writing (F9). **This plan supersedes; it does not correct.**

**Trap 4 — touching `clear_wip_marker`'s guard.** `_cmds_commit.py:684`–`:694`. **It must stay a `not final` guard** (F2, D2, `## Non-goals`).

**Trap 5 — wiring Arm A before Phase 1 lands.** `dispatch` is not in `_VALID_PHASES`, so `__post_init__` rejects the first task of the first run (F6, D1). **The failure is immediate and total, which is the only reason it is survivable.**

**Trap 6 — the `state-cardinality` false match.** `PLAN-STATUS-ARCHIVE.md:20` carries that phrase in plan 07's entry, and it is about `src/agents/architect.md:154`'s `States:` / `DEPARTURE:` notes. **It has nothing to do with `_VALID_PHASES`' cardinality** (F11).

**Trap 7 — counting two `**Phase**` hits in `main.md`.** There are **three** — `:67`, `:144` and `:347` — and `:347` is the easiest to miss because the line is long and the phrase sits mid-sentence. **It is also the strongest single piece of evidence for F8**, because it promises a re-entry at `verify` that nothing can produce.

**Trap 8 — reading plan 110's Trap 8 as binding here.** It says a phase adding a helper verb for this marker *"has misread this"* (`110-…:538`). **It was written for plan 110's own scope. Arm A would deliberately reverse it, and D1 requires that reversal to be stated rather than slipped past.**

**Trap 9 — reporting `main.md:320` and `_cmds_commit.py:694` as a double clear.** They fire on different events — a Stage B skip versus an approved WIP commit (F4). **It is not a defect.**

**Trap 10 — quoting a `file:line` from this plan as current.** Every anchor here was true on 2026-09-24, and several neighbouring plans are unbuilt and will move these digits.

### File anchors

**EDIT targets — a phase of this plan writes each of these:**

- **`src/devforge/lib/_implement/_state.py`** — the `"seven loop phases"` docstring `:13`; `_VALID_PHASES` `:39`–`:48`; `ImplementState` `:73` (Phases 1–2, per D1 and D3).
- **`src/devforge/lib/_implement/_wip.py`** — the module docstring, `write_wip_marker` `:88`, `read_wip_marker` `:130` (Phase 2, per D1). ⚠ **`clear_wip_marker` `:172` is NOT edited.** ⚠ **`_atomic_write` `:62`–`:80` is `write_wip_marker`'s only caller, so Arm B removes it with the writer — and that removal IS the atomicity loss OQ-1 poses.**
- **`src/commands/implement/main.md`** — the `resume` arm `:67`; PHASE 2 step 2 `:144`; the `fix-tooling` arm `:347` (Phase 1, per D3 and D4).
- **`src/commands/implement/references/crash-recovery.md`** — the two-ends sentence `:7` (Phase 3); the `**Phase**` bullet `:23` and the `resume` bullet `:34` (Phase 1).
- **`tests/lib/_implement/test_wip.py`**, **`tests/lib/_implement/test_state.py`** — both exist (Phase 2, per D1). ⚠ **BOTH are ALSO PHASE 1 anchors if D3 rules `dispatch` the winning name, under Arm A or Arm C** — moot under Arm B, where Phase 2 removes them anyway — and the two attributions are true in different arms. ⚠ **Find them by grepping the `ImplementState` import across `tests/lib/_implement/`, today exactly these two, and NEVER by grepping `"agent"`, which in that directory is mostly the agent-NAME field.** Known failures: `test_state.py`'s eight-name literal list and its `dataclasses.replace` call with the assertion; `test_wip.py`'s `test_full_cycle` construction and its `Phase` round-trip assertion. **One site, the frozen-assignment test, needs classifying rather than assuming.** **Updating the failing sites is that ruling's expected consequence, not a regression.** ⚠ **`test_valid_phases_constant_size` is NOT affected by ANY D3 ruling:** the naming sub-question is a one-for-one swap that preserves the count, and the enumeration sub-question is prose-scoped and cannot reach `_VALID_PHASES` (D3). ⚠ **Under D3's RECOMMEND (`agent`) Phase 1 does not touch this file.**
- **`110-IMPLEMENT-AUTO-APPROVE-PLAN.md`**, **`PLAN-STATUS-ARCHIVE.md`** (this plan's two lines only), **`src/CLAUDE.md`**, **`src/devforge/storage-rules.md`**, **`CHANGELOG.md`** (Phase 4).

**READ-ONLY anchors — no phase of this plan writes any of these, and an anchor listed here is a file to READ, never an edit target:**

- `src/devforge/lib/_implement/_cmds_commit.py:157` and `:684`–`:694` — `clear_wip_marker`'s import, its `if not final:` guard and the comment that explains it (F2).
- `src/devforge/lib/_implement/_cmds_preflight.py:306`–`:325` — `_check_wip_marker`, which composes the path itself and tests `.exists()` only. ⚠ **Its *"Phase 9"* naming at `:310` and `:323` is NOT repaired here, and `:12` is module-level, outside this range** (F5, `## Non-goals`).
- `src/commands/implement/main.md:61`, `:68`, `:69`, `:320` — the orchestrator's read and its three removal sites (F4).
- `91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md:358`, `:363`, `:678` — plan 91's harvest, its closure and its disclaimer (F9). **A finished plan; its record is frozen.**
- `07-EXECUTE-TASK-REDESIGN-PLAN.md:157`, `:159`, `:169`, `:380` — the birth plan's field list, API list, smoke check and conditional read helper (F11). **SHIPPED; frozen.**
- `88-COLD-FIX-BUGS-LANE-PLAN.md:1382` — one grep-string mention, not an owner (F12).
- `PLAN-STATUS-ARCHIVE.md:20` — plan 07's entry and its `state-cardinality` false match; `src/agents/architect.md:154` is what that item is actually about (F11, Trap 6).

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation. Then read `110-IMPLEMENT-AUTO-APPROVE-PLAN.md`'s D7, Trap 8 and `### File anchors`, because D5 is an ordering decision against that plan. ⚠ **Find any sibling plan by its TITLE if a filename has moved** — never by assuming a number.
2. **Check `### Phase 0 close record` first.** While it reads *PENDING*, nothing is ratified, **no build phase may start**, and **no phase vocabulary, arm or file list from this plan may be quoted in any file.**
3. **Re-verify F1–F12 against the live tree. Grep the QUOTED TEXT, never the digits:** `write_wip_marker`, `read_wip_marker`, `clear_wip_marker`, `ImplementState`, `_VALID_PHASES`, `seven loop phases`, `both ends must honour it`, `starting at \`dispatch\``, `the verify leg (PHASE 5) re-runs from the top`, `never an unconditional clear`, `the orchestrator removes the file`, `Phase 1 substrate ok`, `state-cardinality`, `Phase 9`. ⚠ **F3 is re-derived with `git log --oneline -S<symbol> -- src/`, not with a file read.** ⚠ **Do NOT grep `written by the \`_implement/_wip.py\` helper module` — that string is gone and its absence is expected** (F9, Trap 2). ⚠ **After a build phase some of these strings have changed by design — a differing result is then the built state, not drift, and the phase that changed it says so in its own commit.**
4. **Build order: Phase 1 → Phase 2 → Phase 3 → Phase 4.** ⚠ **Phase 1 before Phase 2 is load-bearing under Arm A, not tidy** (Trap 5).
5. **Route every edit through the house flow:** python-engineer → python-reviewer for every Python edit, with a test per function written and run in the same turn; instruction-author → instruction-reviewer for every markdown edit.
6. **Commit by explicit path, never `git add -A`.** Re-read `git status` first, read every shared file live, stage by hunk on `src/CLAUDE.md` and on `110-IMPLEMENT-AUTO-APPROVE-PLAN.md`, and check `git diff --cached --stat` rather than the unstaged view. ⚠ **Plan 110 is another session's open plan — if it is mid-build, Phase 4 waits.**
7. **After each phase, cross-check.** Grep every symbol, phase name and field name touched — the ratified phase literal, `**Phase**`, `wip.md`, `write_wip_marker`, `read_wip_marker`, `ImplementState`, `clear_wip_marker` — and fix any dangling reference **in the SAME change.** ⚠ **The sweep stops at `src/`, `tests/` and the OPEN plan files. In `CHANGELOG.md` and in FINISHED plan files those strings are frozen historical records, and editing them falsifies the record.**
8. **Keep the evidence class attached.** Any summary of this plan repeats it: **NO consumer incident, none claimed, nothing measured — a code read of this tree on 2026-09-24 plus one `git log -S` check.**
