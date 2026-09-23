# 106 — Intake Provenance Continuity Plan

**Created**: 2026-09-20
**Status**: **Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start.** Every decision (D1–D3) and every open question (OQ-1–OQ-5) carries a recommendation and its strongest counter-argument, and each waits for the maintainer. **Phase 5 is a user-driven consumer e2e HARD GATE that has not run**; when this plan is later closed on its build, "done" will mean BUILT and build-verified and NEVER that Phase 5 passed. ⚠ **Numbered 106 because 101, 102, 104 and 105 were taken by other sessions in this checkout on 2026-09-20 and 103 was vacated by a renumbering — the gap at 103 is not a missing plan.**

A spec seeded by an investigation can lose that link without anyone being told. Three things are proposed. One documented route back after a mid-run state reset, so a replaying orchestrator re-binds the feature directory through the verb that carries the provenance rather than the verb that drops it (D1). One read-only reporter at `/devforge:plan`, so a run that plans cold beside an unconsumed intake handoff says so instead of printing a bare cold line (D2). And one separation of the two producers of `--seeded-by-upstream`, so the emitted artifact cannot claim a research pre-seed its own provenance block denies (D3). The three are one change because they are one loss: the binding is dropped at the moment of recovery, the artifact then lies about it, and the next command plans without it in silence.

---

## Origin & evidence

⚠ **Evidence class, to be repeated in every summary of this plan: ONE observed consumer incident (the same run the Specify In-Place Revision Plan stands on), plus grep-verified structural facts read on 2026-09-20. Every gap this plan names beyond the incident's third link — D3's mechanism included — is PREDICTED, found by READING and never observed. NOTHING WAS MEASURED.** A clean Phase 5 would show the mechanisms behave on planted fixtures; it would never show that any of these gaps cost anything.

**The incident.** On a benchmark install running 2.0.12-era code; artifacts held outside this repo. This repo is public, so this plan names no client, no install, no repo, no branch, no ticket id and no identifier. It was traced by a peer session from that run's transcript and **re-verified against THIS tree on 2026-09-20 by the orchestrator.** The chain has three links:

1. **`/devforge:specify` ran a full `import-handoff` from a research intake handoff.** The upstream binding existed.
2. **`specify_helper verify-numerical-consistency` exited 2 on one acceptance criterion's wording.** No verb edits an already-recorded AC, so the agent followed the command's own documented recovery — reset the whole spec state and replay. ⚠ **That link is owned by the Specify In-Place Revision Plan and is NOT this plan's subject.**
3. **On the replay the agent re-bound the feature directory with `record-handoff-path`** — the Phase 0.4 `cold`-arm writer — instead of re-running `import-handoff`. The emitted `handoff.json` therefore carried `provenance.upstream_handoff_path: null` while the intake handoff sat in the same directory, and `/devforge:plan` planned "cold", silently dropping the whole upstream HOW seed. Alongside it, `classification.spec_type_rationale` in that same artifact read `pre-seeded from research handoff at <path>` — **the artifact contradicted itself.**

**The relay, and what it is worth.** The chain above reached this plan through a peer session's written report. ⚠ **Nothing in a relayed report is a fact until it is re-derived from the tree.** F1–F12 below are the orchestrator's own reads, and **two of that report's claims were CORRECTED** in the course of making them:

- **Correction 1 — `record-handoff-path`'s null provenance is NOT a bug.** The report called it one. It is deliberate, it is argued in `cmd_record_handoff_path`'s own docstring, and **this plan LEAVES IT ALONE** (F3, and the matching trap). A plan that "fixed" it would silently reintroduce, one command downstream, the exact content pre-seed the `cold` arm exists to withhold.
- **Correction 2 — a way to restore the binding after a reset DOES exist.** The report said none did. `import-handoff` is re-runnable by explicit path and carries no re-import block (F5). **What is missing is any instruction telling a replaying orchestrator to use it** — which is D1, and D1 only.

### Verified structure (2026-09-20)

Every fact below was read against the tree on 2026-09-20. ⚠ **Line digits drift — grep the quoted text, never the digits.**

**F1 — `record-handoff-path` writes exactly one field.** `src/devforge/lib/_specify/_cmds_handoff.py`, `cmd_record_handoff_path`: inside `_state_transaction` it sets `state["source"]["handoff_path"] = handoff_path_rel` and nothing else; `state["source"]["handoff_kind"]` deliberately stays at its default `None`. It prints `recorded: <root-relative path>` to stdout and returns 0.

**F2 — Provenance is keyed on `handoff_kind`, not on `handoff_path`.** `cmd_finalize_handoff` (same module) builds `Provenance` from the kind: the in-code comment states *"handoff_kind, not handoff_path, is the provenance signal"*, and the path expression reads `source.get("handoff_path") or None if upstream_handoff_kind is not None else None`. `tests/lib/_specify/test_finalize_handoff.py::TestNoUpstreamProvenance::test_handoff_path_set_without_kind_produces_no_upstream_provenance` pins it: a state with `source.handoff_path` set and `handoff_kind` None emits `upstream_handoff_path=None` / `upstream_handoff_kind=None` / `upstream_completed_at=None` and exits 0.

**F3 — The null is deliberate and argued in code.** `cmd_record_handoff_path`'s docstring: *"`cold` means 'do not pre-seed the spec from the handoff's CONTENT' … it does not mean the directory is unknown"*, and *"/devforge:plan's PHASE 0a.5 reads a non-null provenance pair to decide whether to surface the ORIGINAL handoff's plan_seeds as 'the authoritative starting point for planning' — were this verb to also set handoff_kind, a cold /devforge:specify run would silently reintroduce that exact content pre-seed one command downstream, instead of never."* ⚠ **The quoted phrase `the authoritative starting point for planning` is the DOCSTRING's own paraphrase of `/devforge:plan`, and grepping it in `src/commands/plan/main.md` returns ZERO hits — that is the expected result, not evidence of drift.** PHASE 0a.5's own wording is *"the authoritative starting point for Phase 0 (Research Evaluation …), Phase 1 (Technical Design), and Phase 1.3 (Architecture Decisions …)"*. **Do not "reconcile" the two: no phase of this plan edits `src/devforge/lib/_specify/_cmds_handoff.py` — `## Non-goals` keeps that docstring's argument standing — and PHASE 0a.5's non-cold path is untouched by Phase 3.** The emitted spec says the same to the model: `src/commands/specify/main.md` Phase 0.4's `cold` arm states *"the `handoff.json` this run emits still reports no upstream handoff at all in its provenance block, exactly as it would on a run with none."*

**F4 — Phase 0.4 has three arms and is written as a once-per-invocation flow.** `src/commands/specify/main.md`, `### Phase 0.4 — Pending-feature-dir resolution`, asks `AskUserQuestion` with options `["yes-most-recent", "pick-other", "cold"]`; the two importing arms call `import-handoff --handoff-path <path>` and the `cold` arm calls `record-handoff-path --handoff-path <path>`. **Nothing in the file describes a MID-RUN return to this phase.** Phase 0.3's block states the state model: *"Fresh-every-run: any prior state is overwritten. `/devforge:specify` does not resume mid-flight prior runs — every invocation starts clean."* — that sentence is about INVOCATIONS. **A mid-run `reset-state` produces a state the instruction never describes.**

**F5 — `import-handoff` is re-runnable, by explicit path, and does not consult pendingness.** `cmd_import_handoff` resolves `--handoff-path` (absolutising a relative one against cwd), and exits 2 only when the argument is missing, the file is absent, unreadable, invalid JSON, fails schema validation, or carries an unknown `handoff_kind`. Its ONLY re-import guard is a WARNING: when `source.handoff_path` is already set AND the state carries `overview` / `desired_behavior` / `acceptance_criteria`, it writes `import-handoff: warning: state has user-composed content (overview / desired_behavior / acceptance_criteria); pre-seeded blocks overwritten but user content preserved` to stderr and **still exits 0.** It never reads `find-handoffs` output. **So after a `reset-state` the warning cannot even fire — the state is empty — and the re-import is clean.**

**F6 — `find-handoffs` is NOT always available as the re-derivation route.** `cmd_find_handoffs`'s docstring: a feature dir is PENDING when an intake handoff is present AND EITHER *"(a) spec.md is absent"* OR *"(b) spec.md IS present but a sibling \*-seed.json file has target_stage == \"spec\""*. **So a mid-run reset AFTER `spec.md` has been written (Step 4.11) leaves the dir invisible to `find-handoffs` unless a spec-targeted seed exists** — which is exactly why D1's route must be the explicit-path one (F5), not a re-run of the Phase 0.4 picker.

**F7 — `reset-state` is total.** `cmd_reset_state` (`src/devforge/lib/_specify/_cmds_phase01.py`) does `_atomic_write_json(default_state(), _state_path(args.devforge_dir))`. The `source` bucket goes back to all-None, so **after a reset the handoff path is no longer IN state** — the orchestrator must hold it in working memory or re-derive it.

**F8 — `/devforge:plan` PHASE 0a.5 has two cold branches and neither looks at the spec's own directory.** `src/commands/plan/main.md`, `## PHASE 0a.5: Upstream handoff discovery`: stdout `no-handoff` → *"No upstream handoff; planning cold from the spec."*; a 4-line block whose `upstream_handoff_path` line reads `none` → *"Spec has no upstream research/discover handoff; planning cold."* The phase states *"This phase is informational … There is no user gate here; do not invoke `AskUserQuestion`."* **Neither branch checks whether `research-handoff.json` or `discover-handoff.json` sits beside the spec.**

**F9 — The block's shape is pinned in five places, and the count is phrased differently in each.** `plan_helper.cmd_read_specify_handoff` prints exactly four lines (`spec-handoff:`, `spec_seeds: present`, `upstream_handoff_path:`, `upstream_handoff_kind:`) and resolves the sibling as `spec_path.parent / "handoff.json"`. The literal `4-line` appears in `src/devforge/lib/plan_helper.py` **twice** — the module docstring's usage block (*"Success (sibling valid): print a 4-line block —"*) and the subparser help (*"Prints a 4-line block on success, 'no-handoff' when none exists, "*) — and in `src/commands/plan/main.md` **twice** (*"A 4-line block (lines `spec-handoff:`, `spec_seeds:`, `upstream_handoff_path:`, `upstream_handoff_kind:`)"* and *"passing the `spec-handoff:` value from the 4-line block as the argument"*); `tests/lib/test_plan_helper.py` asserts `assertEqual(len(lines), 4, "Expected 4-line block, got: …")`. **That enumeration is D2's rejected-option blast radius and must be given as a list, never as a bare number.**
- ⚠ **The test site is TWO assertions, not one.** Beside the message-carrying assertion above, `test_real_specify_handoff_no_upstream_reports_none` carries a bare `assertEqual(len(lines), 4)` with no message, followed by `assertIn("upstream_handoff_path: none", lines[2])`. **A builder who greps the message string finds one and misses the other.** Grep `len(lines), 4` as well.

**F10 — `classify-spec-type` takes `--seeded-by-upstream` on trust.** `cmd_classify_spec_type` (`src/devforge/lib/_specify/_cmds_phase3.py`) validates `--spec-type` against `SPEC_TYPE_ENUM` and `--rationale` as a scalar **before** opening `_state_transaction`, then inside the transaction assigns `state["spec_type"]`, `state["spec_type_rationale"]` and `state["spec_type_seeded_by_upstream"] = bool(args.seeded_by_upstream)` — and **consults `state["source"]` for nothing.** The rationale is a free `--rationale` string.
- ⚠ **Recorded, owned by no phase here:** the flag's CLI help in `src/devforge/lib/_specify/_cli.py` reads *"Phase 1 adapter pre-seeded from /devforge:discover (path-based)."* — it names only F11's producer 2, while producer 1 passes the same flag. **If D3 ships, producer 1 stops passing this flag and the help becomes accurate without being edited; if D3 is declined, the help stays narrower than the flag's actual use and nothing in this plan corrects it.**

**F11 — THE FLAG HAS TWO LEGITIMATE PRODUCERS, AND THE SECOND ONE FIRES ON THE COLD PATH.** A grep for `--seeded-by-upstream` over `src/commands/specify/main.md` returns **exactly two lines**, and they are the two producer sites in Phase 3 Step 1 (the second names the flag twice — once to add it on `accept`, once to omit it on `override`):
  - **Producer 1, the handoff-seeded precondition:** fires only when *"state has `spec_type_seeded_by_upstream == true` AND `spec_type` is set AND `source.handoff_kind == \"research\"`"*, and its `accept` arm passes a HAND-WRITTEN rationale literal `"pre-seeded from research handoff at <handoff_path>"`.
  - **Producer 2, the origin-based discover pre-seed:** fires when any Phase 1 input has `source_origin == "discover"`, and the file states explicitly *"This pre-seed is driven by the Phase 1 reads, not by the import: a `cold` pick in Phase 0.4 skips the handoff-content import but still reads the reports in §1.5/§1.6, so a `discovery-report.md` pre-seeds `greenfield_feature` on the cold path too."*
  - ⚠ **Consequence, and it is load-bearing for D3:** any gate of the form *"reject `--seeded-by-upstream` when `source.handoff_kind` is None"* would BREAK producer 2, which is documented, correct and cold-path-legitimate. **D3 must therefore separate the two producers structurally instead of gating the shared flag.**

**F12 — Concurrency.** Other sessions are building in this checkout. Four plan files — `101-NON-WEB-STACK-READINESS-PLAN.md`, `102-SPECIFY-IN-PLACE-REVISION-PLAN.md`, `104-UNIVERSAL-SECTIONS-INTEGRITY-PLAN.md` and `105-HYPOTHESIS-SUPPRESSION-PRECISION-PLAN.md` — were created by other sessions on 2026-09-20, and `CHANGELOG.md`, `VERSION`, `README.md`, `DEVELOPMENT-STATUS.md`, `src/CLAUDE.md`, `src/manifest.json` and `src/commands/summarize/main.md` were modified and uncommitted by other work when this plan was drafted — **re-derive that list from `git status` rather than trusting it here.** `PLAN-STATUS-ARCHIVE.md` **carries neither an `## Index` line nor an `## Entries` entry for plans 101–105** (a grep for all four filenames and for their three titles returns nothing), **so this plan's docs phase will find that `## Index` section without any of its neighbours in it.** ⚠ **The repo `CLAUDE.md` was rewritten twice the same day by another session** — commits `e859bfe` and `fc11d2f` — and now carries no plan index, no archive pointer and no `done-plans/` mention; see `## Coordination with the Specify In-Place Revision Plan` for the greps. Before touching any ledger: re-read `git status`, read the ledger LIVE, commit by explicit path, never `git add -A`, and **never touch another session's plan file.**

---

## Coordination with the Specify In-Place Revision Plan

⚠ **The sibling is referenced by TITLE throughout this plan, because plan numbers in this checkout have already moved: the Specify In-Place Revision Plan (`102-SPECIFY-IN-PLACE-REVISION-PLAN.md` as of 2026-09-20) was briefly 103, and the Hypothesis-Suppression Precision Plan moved 102 → 103 → 105.** If a filename given here does not resolve, find the plan by its title — `grep -l "Specify In-Place Revision Plan" *.md` — never by assuming a number.

**One incident, two halves.** That plan removes a REASON to reset mid-run: an in-place `revise-ac`, plus the demotion of the blocking numeric check. This plan makes the replay LOSSLESS and the loss VISIBLE. **Neither subsumes the other.**

**Why this plan is not dissolved by that one — argued from that plan's own text, quoted.** Its `## Context for next session` → Honest bounds says *"D2 covers one section of six. A user who names a constraint, risk, out-of-scope item or affected area at `request-changes` still pays the full reset"*, and its `## Non-goals` says *"No change to the fresh-every-run state model or to `reset-state`. A `/devforge:specify` run still starts clean … this plan only removes a reason to reset mid-run."* **So a mid-run reset stays reachable for five of six sections even after that plan ships in full.** Independently, `/devforge:specify` is fresh-every-run (F4), so an interrupted run re-invoked from scratch enters Phase 0.4 again with no memory of the first pass. **And the `/devforge:plan`-side silent loss (D2) is reachable with no reset at all:** a user who deliberately picks `cold` in Phase 0.4 gets the same silent cold plan.

**This plan RESPECTS that plan's non-goal.** D1 is instruction-only and changes neither `reset-state` nor the fresh-every-run model. **The rejected alternative, recorded:** a `reset-state` that preserves the `source` bucket was considered and is **REJECTED twice over** — it contradicts the neighbouring plan's stated non-goal, AND it is independently wrong, because Phase 0.3's reset runs BEFORE Phase 0.4 resolves anything (F4), so preserving `source` there would carry a PREVIOUS run's binding into a new run and would defeat `import-handoff`'s own re-import warning guard (F5), which reads `source.handoff_path` to detect a re-import.

### Shared surfaces, verified 2026-09-20

- **`src/commands/specify/main.md` — both plans edit this file, in DIFFERENT sections.** That plan: Step 4.9's two bullets, Step 5.2, Step 5.3's `request-changes` arm, IMPORTANT RULES item 8. This plan: Phase 0.4 (D1's re-bind route) and Phase 3 Step 1 (D3's call site).
  - ⚠ **That plan's Phase 3 Verify line reads `git diff --stat src/commands/` lists `specify/main.md` and nothing else** — and **this plan's instruction phase also lists `plan/main.md`. Whichever ships second must not read the other's diff as a violation of its own Verify.** Stated plainly so neither builder treats the other's committed work as a defect.
- **`src/devforge/lib/_specify/_cli.py`** — that plan registers a `revise-ac` subparser; this plan adds a flag to the existing `classify-spec-type` subparser. **Different subparsers, same file.**
- **`src/commands/plan/main.md` — also shared, with the Non-Web Stack Readiness Plan** (`101-NON-WEB-STACK-READINESS-PLAN.md` as of 2026-09-20; `grep -l "Non-Web Stack Readiness Plan" *.md` if it has moved), whose D5 edits *"the relay availability line"* in that file. **This plan edits PHASE 0a.5. Different regions.**
- **The ledgers a docs phase writes** — `PLAN-STATUS-ARCHIVE.md` (**both** its `## Index` line and its `## Entries` entry) and `CHANGELOG.md` — **plus `DEVELOPMENT-STATUS.md` and `README.md` as edit-or-verified-no-op sites.** **The house rule: whichever plan ships SECOND reads those surfaces LIVE and re-derives its own edits, never a pre-computed diff — the rule binds the READ, not the edit.** That plan's OQ-4 creates a `## [Unreleased]` CHANGELOG section above the released `2.0.12` block; whichever ships second **finds it already created and ADDS to it.** ⚠ **The released `## [2.0.12]` block is never edited.**
- ⚠ **The repo `CLAUDE.md` is NOT on that list, and the neighbouring plans' Phase 4 wording predates the change. Verified live on 2026-09-20.** `PLAN-STATUS-ARCHIVE.md` carries BOTH shapes — `## Index` (one line per plan) above `## Entries` (the full record, and the authority) — and **the bookkeeping obligation is carried twice inside that one file, in two DIFFERENT wordings** — the opening paragraph's *"the obligation is now to amend BOTH this file's `## Index` line and its `## Entries` entry when a plan's status changes"*, and the `## Index` preamble's *"When a plan's status changes, amend BOTH its line here and its entry below."* ⚠ **Two wordings of one obligation, not one sentence repeated:** the second string exists exactly once in the file, and it is the one Phase 4's Verify pins byte-unchanged. **The obligation is carried NOWHERE in `CLAUDE.md`.** Two commits landed on `develop-2.0-init` the same day — `e859bfe` (*"docs(ledger): CLAUDE.md carries development instructions, not history"*) and `fc11d2f` (*"docs(ledger): CLAUDE.md names the plan archive nowhere"*) — after which `grep -c "PLAN-STATUS-ARCHIVE" CLAUDE.md` and `grep -c "done-plans" CLAUDE.md` each return **0**, and the file's former plan-records section is now `## Read before making changes`, keeping exactly two things: read the relevant plan in full before changing anything, and `FINDINGS.md` for open unowned problems. **By maintainer ruling `CLAUDE.md` is the framework's development instructions, not its history, and a bounded pointer was judged to be a pointer all the same.** ⚠ **All four neighbouring plans — the Non-Web Stack Readiness Plan, the Specify In-Place Revision Plan, `104-UNIVERSAL-SECTIONS-INTEGRITY-PLAN.md` and the Hypothesis-Suppression Precision Plan (filenames as of 2026-09-20) — still carry the superseded "one index line in `CLAUDE.md`" wording in their own Phase 4, and are being corrected separately by another session. Do not restore that site from a sibling's text.** Phase 4 re-derives its own placement from the ledgers as they read at build time; it does not copy a sibling plan's site list.

---

## Phase 0 — ratification

Nothing below is ratified. Each item states the decision, its options where they exist, a recommendation, and the strongest counter-argument, **recorded honestly rather than answered away**. Proposed emitted wording is **substance, not final text**: the builder may reword, but every element named must survive. **No emitted sentence may name plan vocabulary** ("D1", "plan 106", "Phase 0"); real headings such as `Phase 0.4` are fine.

### D1 — A documented mid-run RE-BIND route in `/devforge:specify` (instruction-only)

**The gap.** The emitted instruction describes no return path after a mid-run `reset-state` (F4, F7). The orchestrator improvises, and **the nearest-looking arm is `cold` + `record-handoff-path`, which is exactly the wrong one** — it re-binds the DIRECTORY and drops the PROVENANCE (F1, F2, F3).

**The proposal.** A short block in `src/commands/specify/main.md` that names a mid-run `reset-state` as its trigger and routes the re-bind to `import-handoff --handoff-path <feature_dir>/research-handoff.json` (or `discover-handoff.json`) **by explicit path** — never `record-handoff-path`, and never a re-run of Phase 0.4's `AskUserQuestion` picker. It must state, as substance:

- the explicit-path route works whether or not `spec.md` already exists, because the verb never consults `find-handoffs` (F5) — and `find-handoffs` would NOT list the directory once `spec.md` exists unless a spec-targeted seed sits beside it (F6);
- `import-handoff`'s user-composed-content warning cannot fire on a post-reset state, because the reset emptied the three fields it guards (F5, F7);
- what taking `cold` instead costs: the emitted `handoff.json` reports no upstream handoff, and `/devforge:plan` plans cold — **and that is `cold` behaving correctly (F3), not a defect to route around**;
- the block does NOT authorise a mid-run reset and does not change the fresh-every-run model; **it describes what to do when one has already happened.**

**Placement fork:**

- **(a) Inside Phase 0.4, after the three arms. RECOMMEND** — that is where the re-bind vocabulary already lives, and a reader looking for "how do I bind a feature dir" is already there.
- **(b) A standalone block near Phase 0.3's `reset-state` call**, where the trigger is named.
- **(c) IMPORTANT RULES, as a one-line rule.**
- **Counter to (a), recorded:** Phase 0.4 is a gate a reader expects to run ONCE, so a mid-run route lodged inside it widens that phase's meaning.

**Counter-argument, recorded and NOT answered:** this is instruction-only, so it is **model judgment with no mechanical backstop** — the same class of bound the neighbouring plan records for its own surfacing sentence. An orchestrator that does not re-read the phase after a reset gets no help from it. **D2 is the backstop that makes the failure loud one command downstream, and D1 without D2 leaves the loss silent.** The two are complementary and catch different failures: **D1 catches the loss at the moment of the re-bind, inside the run that caused it; D2 catches it one command later, after `spec.md` and `handoff.json` are already written.**

**RECOMMEND D1 with placement (a).**

### D2 — `/devforge:plan` names a sibling intake handoff instead of saying "planning cold"

**The gap.** Both cold branches of PHASE 0a.5 print a cold-planning line **without ever looking in the spec's own directory**, where `/devforge:research` / `/devforge:discover` put their handoff at intake (F8). The HOW seed is dropped with no notice.

**The proposal — Python decides, the instruction prints.** A new read-only `plan_helper` verb, recommended name `find-intake-handoff <spec-path>`, that looks for `research-handoff.json` and `discover-handoff.json` beside the spec — the same `spec_path.parent` resolution `read-specify-handoff` already uses (F9) — and prints a deterministic one-line result: `none`, or the kind plus the path. **It always exits 0; it is a reporter, not a gate.** PHASE 0a.5 calls it on **BOTH** cold branches — the `no-handoff` branch and the `upstream_handoff_path: none` branch — and, on a hit, surfaces a notice that names the file found and the recovery (re-run `/devforge:specify` and take an importing arm in Phase 0.4) instead of the bare cold line.

**Shape fork:**

- **(a) A separate verb. RECOMMEND.** It leaves `read-specify-handoff`'s 4-line block byte-identical, so the sites F9 enumerates are untouched, and it covers the `no-handoff` branch uniformly — a spec with no sibling `handoff.json` at all still gets the notice. **Its cost is one extra helper call, and only on the cold branches.**
- **(b) A fifth line on `read-specify-handoff`'s block. Rejected.** Its blast radius is the sites F9 enumerates — the module docstring's usage block, the subparser help, two sentences in `src/commands/plan/main.md`, and the `assertEqual(len(lines), 4, …)` assertion **plus the bare `assertEqual(len(lines), 4)` beside it** — and it still leaves the `no-handoff` branch needing a second shape.
- **(c) Auto-render the upstream seed when the sibling is found. Rejected on the mechanism, not on taste:** it would reintroduce exactly the content pre-seed the `cold` arm deliberately withheld, which is the thing `cmd_record_handoff_path`'s docstring argues against by name (F3).

**Gate fork, and it is separate from the shape.** The notice is **INFORMATIONAL — no `AskUserQuestion`** — because PHASE 0a.5 states in its own prose that it has no user gate (F8). **Named strengthening arm, NOT built:** a user gate offering to import the seed after all; **its trigger is the first run in which a user reports that the notice fired and they wanted the seed.** The counter, recorded honestly: **the user is the only party who can tell a deliberate `cold` from a lost binding**, so a notice puts the discrimination on the person best placed to make it — and also on a person who may not be reading.

**Counter-argument, recorded:** on a deliberately-chosen `cold` the notice fires every time and says nothing the user does not already know. **That is noise on the correct path, paid so the incorrect path stops being silent.** ⚠ **Nothing here measures how often each path is taken.**

**RECOMMEND D2 with shape (a) and the informational gate.**

### D3 — Separate the two `--seeded-by-upstream` producers so the handoff rationale cannot be fabricated

⚠ **Severity: NIT, and this plan says so. It is independently declinable — D1 and D2 do not depend on it.**

**The gap.** The emitted artifact contradicted itself: `classification.spec_type_rationale` named an upstream research handoff while `provenance` reported none. `cmd_classify_spec_type` assigns the rationale and the flag from argv and consults `state["source"]` for nothing (F10), and the rationale that names the handoff is a hand-written literal in the emitted instruction (F11, producer 1).

⚠ **The evidence split, stated precisely so no summary overstates it:** the contradictory artifact is part of the observed incident's third link. **What is PREDICTED is the mechanism's reach** — that `cmd_classify_spec_type` would accept an ungrounded `--seeded-by-upstream` on any OTHER run is a reading of the code (F10), never an observation, and nothing measures how often it happens.

**The proposal.** Give producer 1 its own argument — recommended `--from-handoff` — on the existing `classify-spec-type` verb. With it, **the helper COMPOSES the rationale itself** from `state["source"]["handoff_path"]` and sets `spec_type_seeded_by_upstream`, and **exits 2 leaving state unchanged when `state["source"]["handoff_kind"]` is None.** Producer 2 keeps `--seeded-by-upstream` plus its own rationale citing the discovery report, **byte-unchanged** (F11). The pre-validate-before-transaction rule the function already follows applies — its enum and scalar checks run on a read-only load before `_state_transaction` opens (F10) — **so no partial write is structurally possible.**

**Why not the obvious gate.** Rejecting `--seeded-by-upstream` whenever `source.handoff_kind` is None **breaks producer 2**, which is documented and legitimately cold-path (F11).

**Why not sniff the rationale string for the word "handoff".** That is an unsound lexical predicate **of exactly the class the Specify In-Place Revision Plan is demoting elsewhere in this same command.** Do not add one while a sibling plan removes one.

**For the tripwire record:** D3 adds a write-time rejection INSIDE an existing setter — the same class as the EARS validation `add-ac` already performs. It adds **no `verify-*` gate number and no new hard-fail validator script.** D2's new verb always exits 0 and gates nothing.

**Counter-argument, recorded:** **the contradictory rationale was the SYMPTOM; the provenance loss was the damage**, and D1 + D2 address that. D3 buys one thing only — an artifact that either tells the truth or fails loudly at the moment the mistake is made, which matters to a downstream reader who has nothing but the artifact. **One new flag is the price.** If it is declined, the hand-written rationale literal stays and nothing checks it.

**RECOMMEND D3 as stated.**

### OQ-1 — Does D1's route apply to a between-runs reset too?

**RECOMMEND no, and name the bound:** Phase 0.3's `reset-state` is the documented one and Phase 0.4 follows it on every invocation (F4). **D1's block covers a reset that happens AFTER Phase 0.4 has already resolved a directory.**
**Alternative:** one block covering both, which would restate Phase 0.4 for the ordinary case.

### OQ-2 — Does D2's notice fire on a re-entry feature dir (one carrying a spec-targeted `*-seed.json`)?

**RECOMMEND yes, unconditionally** — the verb reports what is on disk and makes no judgement about why.
**Alternative:** suppress it there, which would need the verb to parse seeds and would give it a second job.

### OQ-3 — Where does the CHANGELOG entry land?

**RECOMMEND the `## [Unreleased]` section, re-verified live at build time, never an edit into the released `2.0.12` block.** ⚠ **Verified 2026-09-20: no `## [Unreleased]` section exists today** — `CHANGELOG.md`'s top section is `## [2.0.12] - 2026-09-20`, and the file is modified and uncommitted in this tree. ⚠ **The Specify In-Place Revision Plan's OQ-4 creates that section; whichever plan ships second finds it already there and ADDS to it.**
**Alternative:** hold the entry until the next version section opens.

### OQ-4 — Back-porting into installs already shipped

**RECOMMEND an explicit NON-GOAL,** per the standing house rule: consumers arrive via `install.sh` / `update.sh`. An install that has already run `/devforge:specify` keeps the undocumented re-bind and the silent cold plan until it updates. ⚠ **The frozen benchmark install is never touched.**
**Alternative:** none proposed.

### OQ-5 — The new verb's name

`find-intake-handoff` is proposed against the existing `specify_helper find-handoffs`; **alternatives are `check-intake-handoff` or folding it under an existing verb.** ⚠ **Cheap to settle at ratification, expensive to change after the instruction quotes it.**

### Phase 0 close record

**PENDING — nothing is ratified.** When it closes, this record must name **each** of D1, D2, D3 and OQ-1 through OQ-5 with its outcome (ratified / amended / declined), state whether per-item deliberation was supplied, state whether the close was an explicit pick or a delegation (plan 98's D1 distinction), and say which files the outcomes put in scope. **Every counter-argument stays where it is written — a ratified decision with its counter-argument deleted cannot be re-opened honestly.** ⚠ **Ratification changes no evidence class:** one observed incident, everything beyond its third link predicted, nothing measured.

#### Verify

- The record names **each** of D1–D3 and OQ-1–OQ-5 with an explicit outcome. **No item is silently omitted**, and each is checked against the per-phase scope lists **by NAME, never against a range** — plan 100's Phase-4 tripwire: a range reads as complete while a hand-written enumeration beside it drops a member, and an item with no Verify line cannot fail.
- **D2's outcome names BOTH the shape fork ((a) / (b) / (c)) and the gate fork (informational / user gate).** A record that ratifies "the notice" without naming both has not closed D2.
- It states whether per-item deliberation was supplied, and whether the close was an explicit pick or a delegation.
- **Every counter-argument above is still present, unshortened.**
- The record says what the outcomes put in scope: **D2 decides whether Phase 1 exists**, **D3 decides whether Phase 2 exists and whether Phase 3 re-points producer 1's `accept` arm or records it as a verified no-op**, **D1's placement fork decides where Phase 3's re-bind block lands**, **OQ-5 decides the verb name Phase 3 is allowed to quote**, and **OQ-3 decides where Phase 4's CHANGELOG entry goes.**

---

## Phases

Phase 0 is the `## Phase 0 — ratification` section above; **nothing below starts before its close record exists.**

**Build order, and its one forced dependency: Phase 3 needs Phases 1 and 2, because it describes what they shipped.** Phases 1 and 2 are independent of each other and may land in either order. Phase 4 runs last, because it records what the earlier phases did. ⚠ **D1 without D2 leaves the loss silent, so Phase 3 is LOAD-BEARING and this plan is not shippable as Phase 1 alone.**

### Phase 1 — D2, Python

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** Commit by explicit path (F12).

#### Deliverables

- `src/devforge/lib/plan_helper.py` — the new read-only verb at the name OQ-5 ratified (`find-intake-handoff` as proposed), resolving the spec's siblings through the same `spec_path.parent` expression `cmd_read_specify_handoff` uses (F9), printing one deterministic line, and **always exiting 0.**
- `src/devforge/lib/plan_helper.py` — its subparser, registered beside `read-specify-handoff`'s.
- `tests/lib/test_plan_helper.py` — tests covering: **a research sibling present; a discover sibling present; both present; neither present; a spec path that is not a file; and a spec whose own `handoff.json` is absent entirely.**

#### Verify

- **`read-specify-handoff`'s output is byte-unchanged**, and BOTH of F9's test assertions are green **UNEDITED** — the message-carrying `assertEqual(len(lines), 4, "Expected 4-line block, got: …")` and the bare `assertEqual(len(lines), 4)` beside it.
- **The new verb exits 0 in every one of the six cases above**, including the two that find nothing and the one whose argument is not a file.
- Its stdout is one line in every case, and the `none` form is distinguishable from a hit by more than whitespace.
- `git diff` on `src/devforge/lib/plan_helper.py` shows the new verb, its subparser and nothing else — **no edit to `cmd_read_specify_handoff` and no edit to `render-plan-seeds`.**
- The targeted suite, then the full `tests/lib` suite, is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — D3, Python

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** Commit by explicit path (F12).

#### Deliverables

- `src/devforge/lib/_specify/_cmds_phase3.py` — `--from-handoff` handling in `cmd_classify_spec_type`: **the helper-composed rationale**, built from `state["source"]["handoff_path"]`, and `spec_type_seeded_by_upstream` set; plus the **exit-2-on-None-kind pre-check**, run on a read-only load BEFORE `_state_transaction` opens, in the shape the function's existing validators already use (F10).
- `src/devforge/lib/_specify/_cli.py` — the `--from-handoff` argument on the existing `classify-spec-type` subparser. **No new subparser.**
- `tests/lib/test_specify_helper.py` — a test per branch. ⚠ **Verified 2026-09-20: that file is the ONLY one under `tests/` that names `classify-spec-type` or `classify_spec_type`**, so there is no second test module to keep in step; re-derive that at build time rather than trusting this line.

#### Verify

- **With `source.handoff_kind` set:** the composed rationale names the recorded path and `spec_type_seeded_by_upstream` is true.
- **With `source.handoff_kind` None:** exit 2 and `.devforge/specify-state.json` is **byte-unchanged.**
- **Producer 2's plain `--seeded-by-upstream` call still succeeds on a state whose `source` bucket is all-None.** ⚠ **This is the regression that matters — pin it.** A change that gates the shared flag on `handoff_kind` fails here and nowhere else (F11).
- `--from-handoff` and `--seeded-by-upstream` passed together is given an explicit, tested outcome rather than an accident.
- The full `tests/lib` suite is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 3 — D1 + the instruction halves of D2 and D3

**Route: instruction-author → instruction-reviewer.** Instruction-only: **no `.py` file changes in this phase.** **Needs Phases 1 and 2 first** — it describes what they shipped and quotes the verb name and flag they created. Commit by explicit path (F12).

#### Deliverables

- **`src/commands/specify/main.md` — the re-bind block**, at the placement D1 ratified, carrying every element D1 names as substance.
- **`src/commands/specify/main.md` — Phase 3 Step 1's producer-1 `accept` arm** re-pointed at `--from-handoff` with the hand-written rationale literal removed. ⚠ **If D3 was declined, this arm is left byte-identical and the phase records it as a VERIFIED NO-OP with the grep that shows it** — not as an omission.
- **`src/commands/plan/main.md` — PHASE 0a.5**, calling the new verb on **both** cold branches, with the notice naming the file found and the recovery. **Producer 2's origin-based pre-seed paragraph in `specify/main.md` and the rest of PHASE 0a.5's non-cold path are untouched.**

#### Verify

- `grep -n "record-handoff-path" src/commands/specify/main.md` **still returns the `cold` arm**, and **the re-bind block does NOT route to it.**
- `grep -n "pre-seeded from research handoff at" src/commands/specify/main.md` returns **nothing** — or **exactly the declined-D3 wording**, recorded as such.
- **Both cold branches in `src/commands/plan/main.md` name the new verb**, and the `no-handoff` branch and the `upstream_handoff_path: none` branch each carry the notice. ⚠ **A phase that wires only one branch has not shipped D2** (F8).
- `git diff --stat src/commands/` lists **`specify/main.md` and `plan/main.md` and nothing else.** ⚠ See `## Coordination with the Specify In-Place Revision Plan`: that plan's own Phase 3 Verify names `specify/main.md` alone, and this line is not a violation of it.
- **No emitted sentence names a verb or a flag that Phases 1 and 2 did not create**, and no emitted sentence names plan vocabulary.
- The live-spec tests are green: `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py`, `tests/scripts/test_claude_emitter.py`.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 4 — Docs sweep

**Route: instruction-author → instruction-reviewer. Docs only.** ⚠ **Apply the coordination rule before touching any ledger** (F12, and `## Coordination with the Specify In-Place Revision Plan`): other sessions are building in this checkout and several ledger files are already modified by other work. **Re-read `git status`, read each ledger LIVE, re-derive every edit from what is there, and commit by explicit path — never `git add -A`, and never a wholesale sweep.**

#### Deliverables

- **`PLAN-STATUS-ARCHIVE.md`, BOTH shapes — the ledger's own rule is to amend BOTH.**
  - **One line in its `## Index` section**, in the shape of its neighbours as they read at build time.
  - **The full entry under `## Entries`**, in the archive's house shape, carrying the evidence split, what each decision shipped, the accepted costs, the tripwires, the sibling-plan coordination, and Phase 5's anchors with their pair.
  - ⚠ **Re-derive the placement rather than copying a sibling plan's site list** — that discipline is exactly what catches a moved ledger, and it is why this deliverable no longer names `CLAUDE.md`.
- ⚠ **The repo `CLAUDE.md` is NOT written by this plan's docs phase.** It carries no plan index, no archive pointer and no `done-plans/` mention (`## Coordination with the Specify In-Place Revision Plan` records the two commits and the greps). **The removed site must not be silently reintroduced**, and a neighbouring plan's Phase 4 naming it is not a reason to.
- **`CHANGELOG.md`** — one entry, placed per OQ-3's answer, with **the evidence class FIRST and the honest bounds LAST.**
- **`DEVELOPMENT-STATUS.md`** — an edit or a recorded verified no-op, with the grep that shows it.
- **`README.md`** — an edit or a recorded verified no-op, with the grep that shows it.

#### Verify

- Every site above is recorded as an **edit or an explicit verified no-op**, with the grep that shows it.
- **`grep -n "106-INTAKE" PLAN-STATUS-ARCHIVE.md` returns the `## Index` line AND the `## Entries` anchor** — both, never one.
- **`grep -c "106-INTAKE" CLAUDE.md` returns 0.** ⚠ A non-zero result means the removed site was reintroduced.
- **The archive's bookkeeping sentence is byte-unchanged by this sweep** — *"When a plan's status changes, amend BOTH its line here and its entry below"*, in `PLAN-STATUS-ARCHIVE.md`'s `## Index` preamble. It is the carrier of the rule this phase obeys and **must not be absorbed, reflowed or reworded by an adjacent edit.**
- **No ledger line belonging to any neighbouring plan is altered or reflowed by this sweep** — `git diff` on the shared files shows only this plan's own additions.
- The CHANGELOG entry sits where OQ-3 ratified and nowhere else; **the released `## [2.0.12]` block is byte-unchanged.**
- **The new CHANGELOG entry's evidence-class statement PRECEDES its honest-bounds statement**, read from the entry's own text and **never inferred from its section placement.** ⚠ Placement and content order are two different checks; the bullet above is the first and this one is the second.
- **No ledger sentence claims any phase is consumer-validated. "Built and build-verified" is the ceiling in every line.**
- **No tracked file names a client, an install, a repo, a branch, a ticket id or any benchmark identifier.**

### Phase 5 — Consumer e2e — user-driven HARD GATE, DEFERRED by default, NOT run

⚠ **Deferred by default, per the house pattern, and explicitly NOT WAIVED.** Everything Phases 1–4 ship is **build-verified at best and NEVER consumer-validated** until this phase runs, and **"done" never means Phase 5 passed.**

- **Fixture:** a testForge20 feature. ⚠ **The frozen benchmark install is never touched.**

The anchors are known-answer cases, **scored explicitly and in their pairs**:

1. **A spec whose specify run took an importing arm** → `/devforge:plan` PHASE 0a.5 renders the upstream plan-seeds block, and **the new verb's notice does NOT fire. PAIRED WITH 2.**
2. **The same feature after a mid-run `reset-state` re-bound through `import-handoff` by explicit path** → the emitted `handoff.json` carries a **non-null** `provenance.upstream_handoff_path`, and `/devforge:plan` renders **the same seeds.**
   - ⚠ **Anchors 1 and 2 are scored as a PAIR: a change that makes the notice fire everywhere passes neither.**
3. **A deliberately-chosen `cold` pick with an intake handoff present** → provenance stays **null** (F3 unchanged), `/devforge:plan` prints its cold line **AND** the notice naming the sibling file.
4. **`classify-spec-type --from-handoff` on a state with no recorded `handoff_kind`** → exit 2, `specify-state.json` byte-unchanged; **the same call after an import** → the composed rationale names the recorded path.

#### Verify

- **Every anchor is scored explicitly — stated, not summarized — with anchors 1 and 2 scored together.**
- **If an anchor fails, record the negative with the artifacts and NAME THE MECHANISM before proposing anything:** a missing notice on anchor 3 is **D2's instruction half**; a notice on anchor 1 is **the verb's predicate**; a null provenance on anchor 2 is **D1's route**; a silent success on anchor 4 is **D3**. ⚠ **They have different fixes.**
- ⚠ **A clean run shows the mechanisms behave on planted fixtures, never that any gap beyond the observed incident cost anything.**

---

## Non-goals

- **No change to `record-handoff-path`'s semantics.** `cold` keeps null provenance; the docstring's argument stands (F3).
- **No auto-import of an upstream seed at `/devforge:plan`** — D2's rejected option (c).
- **No change to `reset-state` or to the fresh-every-run state model** — the neighbouring plan's non-goal, respected here, **and independently wrong** for the reason recorded in `## Coordination with the Specify In-Place Revision Plan`.
- **No AC revision verb, no change to `verify-numerical-consistency`, and no edit to Step 4.9 / Step 5.2 / Step 5.3 / IMPORTANT RULES item 8** — all owned by the Specify In-Place Revision Plan.
- **No user gate added to PHASE 0a.5** — the named strengthening arm under D2, with its own trigger.
- **No new `verify-*` gate number and no new hard-fail validator script** — plan 75's tripwire. D2's verb always exits 0; D3's rejection lives inside an existing setter.
- **No change to `find-handoffs`'s pending predicate** — F6 is a fact this plan routes AROUND, not one it changes.
- **No back-port into shipped installs** (OQ-4). They arrive via `install.sh` / `update.sh`.
- **No `disable-model-invocation` change**, no constitution edit, no `src/CLAUDE.md` edit.
- **Anything specific to the benchmark**, and any client, install, repo, branch, ticket id or benchmark path in this repo.

---

## Context for next session

⚠ **Evidence class, repeated: ONE observed consumer incident (a benchmark install; artifacts held outside this repo), plus grep-verified structural facts read on 2026-09-20. Every gap beyond the incident's third link — D3's mechanism included — is PREDICTED, found by reading. NOTHING WAS MEASURED.** ⚠ All line digits drift — **grep the quoted text, never the digits.**

**The one sentence that governs everything here:** **a spec that was seeded by an investigation must not be able to lose that link silently — and where the link was dropped on purpose, the command that plans from it must say so out loud.**

### Honest bounds

- **D1 is instruction-only and nothing mechanical makes the route be taken.** D2 is the backstop, and **it fires one command LATER** — after `spec.md` and `handoff.json` are already written.
- **D2 reports what is on disk.** It cannot tell a deliberate `cold` from a lost binding, and **it fires identically on both.**
- **The notice is prose the model is instructed to surface; nothing checks that it was.**
- **D3 fixes a symptom, not the damage,** and is a **NIT** by this plan's own accounting.
- **Nothing here measures** how often a mid-run reset happens, how often `cold` is chosen deliberately, or what a dropped HOW seed costs a plan. **No rate was computed before this plan and none will be after it.**
- **The incident's own first link stays with the Specify In-Place Revision Plan.** If that plan is declined in full, mid-run resets get MORE frequent, not less, **and nothing here changes that.**

### Traps

**Trap 1 — "fixing" `record-handoff-path` to set `handoff_kind`.** That is the change F3's docstring argues against **by name**, and it would silently reintroduce the content pre-seed one command downstream — the thing the `cold` arm exists to withhold.

**Trap 2 — making D2's notice auto-import the seed.** Rejected option (c), and the same mechanism as trap 1: the seed the `cold` pick declined would arrive anyway, one command later.

**Trap 3 — gating `--seeded-by-upstream` on `source.handoff_kind`.** It breaks producer 2, which is documented and cold-path-legitimate (F11). The separation is structural — a second argument — never a gate on the shared flag.

**Trap 4 — sniffing the rationale string for "handoff".** An unsound lexical predicate, **of the class a sibling plan is removing from this same command.**

**Trap 5 — preserving `source` across `reset-state`.** It contradicts a neighbouring plan's non-goal **AND** breaks `import-handoff`'s re-import warning guard, because Phase 0.3's reset runs BEFORE Phase 0.4 resolves anything, so a previous run's binding would be carried into a new run (F4, F5).

**Trap 6 — re-running Phase 0.4's picker as the re-bind route.** `find-handoffs` will not list the directory once `spec.md` exists unless a spec-targeted seed sits beside it (F6). **The route is the explicit path** (F5).

**Trap 7 — adding a fifth line to `read-specify-handoff` without walking F9's sites.** The module docstring's usage block, the subparser help, two sentences in `src/commands/plan/main.md`, and **two** assertions in `tests/lib/test_plan_helper.py` — one of which carries no message and is invisible to a grep for the message string.

**Trap 8 — reading a neighbouring plan's `git diff --stat src/commands/` Verify line as a rule this plan violates.** The two plans edit different sections of one shared file, and one of them also edits `plan/main.md`.

**Trap 9 — quoting a `file:line` from this plan as current.** Every anchor here was true on 2026-09-20 and drifts on the next edit to those files.

**Trap 10 — reading a predicted gap as observed.** One incident stands behind link 3; **everything else is a reading of the code.**

**Trap 11 — touching another session's plan file, or sweeping a shared ledger.** Four plan files and eight tracked files are already modified by other work in this checkout (F12). Re-read `git status`, read each ledger live, commit by explicit path.

**Trap 12 — writing a `CLAUDE.md` index line because a neighbouring plan's Phase 4 says to.** That wording predates commits `e859bfe` and `fc11d2f`; **the site does not exist** — `grep -c "PLAN-STATUS-ARCHIVE" CLAUDE.md` and `grep -c "done-plans" CLAUDE.md` each return 0. **The index line belongs in `PLAN-STATUS-ARCHIVE.md`'s `## Index`**, beside the full entry under `## Entries` (F12, and `## Coordination with the Specify In-Place Revision Plan`).

### File anchors

- **`src/commands/specify/main.md`** — Phase 0.3's `reset-state` call and its fresh-every-run sentence; Phase 0.4's three arms and the `cold` arm's provenance sentence; Phase 3 Step 1's two `--seeded-by-upstream` producers.
- **`src/commands/plan/main.md`** — PHASE 0a.5's two cold branches and its no-user-gate sentence.
- **`src/devforge/lib/_specify/_cmds_phase3.py`** — `cmd_classify_spec_type`.
- **`src/devforge/lib/_specify/_cli.py`** — the `classify-spec-type` subparser.
- **`src/devforge/lib/plan_helper.py`** — `cmd_read_specify_handoff`, `render-plan-seeds`, the module docstring's usage block.
- **`tests/lib/test_plan_helper.py`** — the `read-specify-handoff` tests and **both** 4-line assertions.
- **Read-only here** — **no phase of this plan writes any of these**, and an anchor listed here is a file to READ, never an edit target: `src/devforge/lib/_specify/_cmds_handoff.py` (`cmd_import_handoff` and its two kind arms, `cmd_record_handoff_path`, `cmd_find_handoffs`, `cmd_finalize_handoff`), `src/devforge/lib/_specify/_cmds_phase01.py` (`cmd_reset_state`), `tests/lib/_specify/test_finalize_handoff.py` (`TestNoUpstreamProvenance`), `src/devforge/lib/_specify/handoff_schema.py`, `src/devforge/lib/_research/handoff_schema.py`, `src/devforge/lib/_discover/handoff_schema.py`, and the two neighbouring plans named in `## Coordination with the Specify In-Place Revision Plan`.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation. Then read the Specify In-Place Revision Plan's `## Non-goals` and its Honest bounds together with this plan's `## Coordination with the Specify In-Place Revision Plan`; they are the two halves of one incident. ⚠ **Find that plan by its TITLE if the filename has moved** — `grep -l "Specify In-Place Revision Plan" *.md` — never by assuming a number.
2. **Check `### Phase 0 close record` first** — it sits at the end of `## Phase 0 — ratification`. While it reads *PENDING*, nothing is ratified and **no build phase may start.**
3. **Re-verify F1–F12 against the live tree.** Grep the quoted text, never the digits: `recorded: `, `handoff_kind`, `test_handoff_path_set_without_kind_produces_no_upstream_provenance`, `still reports no upstream handoff at all`, `yes-most-recent`, `Fresh-every-run`, `import-handoff: warning:`, `PENDING`, `no-handoff`, `planning cold`, `4-line`, `len(lines), 4`, `--seeded-by-upstream`, `pre-seeded from research handoff at`, `source_origin == "discover"`. ⚠ **After a build phase some of these strings are gone by design; zero hits for them is then the built state, not a regression.**
4. **Build order:** Phase 1 and Phase 2 are independent; **Phase 3 needs both**; Phase 4 runs last because it records what the earlier phases did. ⚠ **Never stop after Phase 1** — D1 without D2 leaves the loss silent, and Phase 1 without Phase 3 ships a verb nothing calls.
5. **Route every edit through the house flow:**
   - python-engineer → python-reviewer for every Python edit, with a test per function, run in the same turn;
   - instruction-author → instruction-reviewer for every markdown edit;
   - `claude-code-guide` for every new Claude-Code-integration fact.
6. **Commit by explicit path, never `git add -A`.** Re-read `git status` first, and read every shared ledger live (F12).
7. **After each phase, cross-check.** Grep every verb, flag and phase name touched — `record-handoff-path`, `import-handoff`, `find-handoffs`, `read-specify-handoff`, the new intake-handoff verb, `--seeded-by-upstream`, `--from-handoff`, `Phase 0.4`, `PHASE 0a.5` — and fix any dangling reference **in the SAME change.**
8. **Run Phase 4, then leave Phase 5 to the maintainer.**
9. **Keep the evidence class attached.** Any summary of this plan repeats it: **ONE observed consumer incident behind the third link; everything beyond it predicted, found by reading; nothing measured.**
