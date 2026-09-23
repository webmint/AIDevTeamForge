# 102 — Specify In-Place Revision Plan

**Created**: 2026-09-20
**Status**: **Phase 0 OPEN — nothing is ratified, no close record exists, and no build phase may start.** Every decision (D1–D4) and every open question (OQ-1–OQ-5) below carries a recommendation and its strongest counter-argument, and each waits for the maintainer. **Phase 5 is a user-driven consumer e2e HARD GATE that has not run**; when this plan is later closed on its build, "done" will mean BUILT and build-verified and NEVER that Phase 5 passed. ⚠ **Numbered 102 — drafted as 102, briefly renumbered to 103 while the Hypothesis-Suppression Precision Plan held 102, and returned to 102 the same day once that plan moved to 103.**

Four fixes in `/devforge:specify`. One blocking gate rejects correct spec text by construction and is demoted to an advisory warning the command surfaces at its approval gate. One missing capability — no verb edits an acceptance criterion already recorded — is added as a single in-place `revise-ac`. One cluster of sentences in the shipped instruction is false against today's code, including the one on the command's primary human gate, and is repaired. One latent id-numbering defect in `add-ac` is closed before the new verb makes it reachable. The four are one change because they are one loop: the gate fires, the command documents a recovery, and the recovery is to throw the spec state away.

---

## Origin & evidence

⚠ **Evidence class, to be repeated in every summary of this plan: ONE observed consumer incident, plus grep-verified structural facts found while checking the report. D3's false-sentence cluster and D4 are PREDICTED gaps found by READING during that verification — not observed, and nothing was measured.**

**The incident.** On a benchmark install running 2.0.12-era code; evidence held outside this repo. This repo is public, so this plan names no client, no install, no repo, no branch and no identifier. `specify_helper verify-numerical-consistency` exited 2 on the wording of one acceptance criterion (AC-8). Because the helper has no verb that edits an already-recorded AC, the agent followed the command's own documented recovery — reset the whole spec state and replay it from scratch — and began writing a script to reconstruct that state. **The cost:** the run's turn count and wall-clock grew for reasons unrelated to the task, which also skews the benchmark's effort metric. ⚠ **This plan does not fix that metric.** It removes the framework-induced cost from future runs; the run that paid it is spent.

**The predicted half.** D3's false-sentence cluster and the id-numbering defect (D4) were found by reading `_specify/` and `src/commands/specify/main.md` while verifying the report. No run hit them, none is claimed, and a clean Phase 5 would show the new behavior works on planted fixtures — never that either gap ever cost anything.

### Verified structure (2026-09-20)

Every fact below was checked against the tree on 2026-09-20. ⚠ **Line digits drift — grep the quoted text, never the digits.**

**F1 — The predicate.** `src/devforge/lib/_specify/_schema.py:277` defines `NUMERIC_DIGIT_NOUN_RE = re.compile(r"\b(\d+)\s+([a-zA-Z]+)\b")`, beside `NUMERIC_HEADING_RE` (`^\s*#+\s`) and `NUMERIC_TABLE_SEP_RE`. `_specify/_cmds_phase4_verify.py:122` `cmd_verify_numerical_consistency` — docstring *"Variance rule #6: digit-prefixed nouns consistent across spec."* — renders the WHOLE spec, skips heading lines and table separator rows, and for every match does `num, noun = m.group(1), m.group(2).lower()` then `groups.setdefault(noun, {}).setdefault(num, []).append(lineno)`. Any noun whose value map has `len(value_map) >= 2` is an inconsistency, and the verb returns 2. **The grouping key is the bare lowercased noun and nothing else.**

**F2 — What that makes impossible.** The predicate cannot distinguish "the same quantity restated inconsistently" from "the same unit measuring two different things", because both produce one noun with two values. Three pairs of ordinary spec text collide by construction:

- `The API shall respond within 200 ms.` + `The report shall render within 500 ms.` → noun `ms`, values `200` and `500`.
- `The importer shall accept 3 files per batch.` + `The exporter shall write 7 files per run.` → noun `files`, values `3` and `7`.
- `The queue shall hold 50 items.` + `The page shall show 10 items.` → noun `items`, values `50` and `10`.

Each statement is a valid `ubiquitous` EARS criterion under F6's regex, each pair is legitimate, and each pair exits 2. The orchestrator records reproducing this class on the live helper on 2026-09-20; **the derivation above is what this plan's author verified, by reading F1's code — not by running it.** ⚠ The statements are written with lowercase `shall` deliberately: `EARS_REGEX` requires it, so an uppercase `SHALL` never reaches state at all (F6).

**F3 — One invocation, one test assertion.** The verb is invoked in exactly one place in the emitted instruction: `src/commands/specify/main.md:825`, in Step 4.9's four-verb block, with its describing bullet at `:831`. A repo-wide case-insensitive grep for `NUMERIC_DIGIT_NOUN_RE|verify-numerical-consistency|numerical_consistency` returns eight files: `_specify/_schema.py`, `_specify/_cmds_phase4_verify.py`, `_specify/_cli.py`, `src/commands/specify/main.md`, `tests/lib/test_specify_helper.py`, `DEVELOPMENT-STATUS.md`, and two files under `done-plans/` (history). **No sibling check exists in any other helper.** In the tests, `TestPhase4VerifyNumericalConsistency` (`tests/lib/test_specify_helper.py:3638`) holds three methods: `test_passes_on_consistent_render` asserts 0, `test_ignores_section_heading_numbers` asserts 0, and `test_fails_on_inconsistent_render` asserts `returncode == 2` (`:3671`) and then `assertIn("packages", r.stderr)` (`:3672`). The two fixture round-trips that also call the verb — `test_state_satisfies_phase_gates` at `:5412` and `:5448` — assert 0. **The whole blast radius of a demotion is the single `assertEqual(r.returncode, 2)` at `:3671`.**

**F4 — No revision verb exists anywhere.** `grep -rnE "def cmd_(remove|delete|drop|update|edit|amend|replace|revise)_" src/devforge/lib/` returns exactly one hit — `_implement/_cmds_session.py:247` `cmd_update_session_state` — and it is not in `_specify/`. `_specify/_cli.py` registers no removal, update, edit or revision subcommand.

**F5 — Six append-only list sections, seven overwriting scalars.** In `_specify/_cmds_phase4_setters.py` each of `cmd_record_affected_area` (`:275`), `cmd_record_out_of_scope` (`:307`), `cmd_record_constraint` (`:340`), `cmd_record_open_question` (`:411`), `cmd_record_risk` (`:431`) and `cmd_add_ac` (`:475`) ends in a `state[<section>].append({...})` and touches no existing entry. The scalar setters overwrite in place: `_set_string_field` (`:248`) does `state[field_name] = content`, serving `set-overview` / `set-current-state` / `set-desired-behavior`, and `set-design-source`, `set-spec-number`, `set-date` and `set-status` each assign their own field. ⚠ Separate mechanism, not a counter-example: `import-handoff` (`_cmds_handoff.py`) REPLACES `constraints`, `affected_areas`, `risks` and `open_questions` wholesale at Phase 0.4 — that is a pre-seed, not a per-entry edit, and it happens before any setter runs.

**F6 — `add-ac` validates EARS at write time, and appends unconditionally.** `cmd_add_ac` validates `--subsection` against `AC_SUBSECTION_ENUM`, `--ears-variant` against `EARS_VARIANT_ENUM`, and then `if not EARS_REGEX[ears_variant].match(statement): return _die(..., code=2)` (`_cmds_phase4_setters.py:525`). `_schema.py:110` defines `EARS_VARIANT_ENUM` as exactly the five keys of `EARS_REGEX` at `:113`, so the lookup cannot miss. Inside the transaction it does `ac_id = (args.ac_id or "").strip() or _next_ac_id(state)` and appends — **there is no duplicate scan anywhere in `_specify/`** — then `_flip_findings(state, finding_ids, "AC", ac_id)` and prints `ac_id`.

**F7 — `_next_ac_id` counts instead of scanning.** `_cmds_phase4_setters.py:470`: `n = 1 + len(state["acceptance_criteria"]); return "AC-{0}".format(n)`.

**F8 — `--ac-id` is optional and no emitted instruction passes it.** `_specify/_cli.py:455` is `sp.add_argument("--ac-id", default="", dest="ac_id")`; a repo-wide `grep -rn -- "--ac-id" src/` returns that one line and nothing else, and `src/commands/specify/main.md:679` documents the `add-ac` call without it. **So the numbering defect is LATENT today.** One test passes the flag: `tests/lib/test_specify_helper.py:3392` `test_accepts_explicit_ac_id` passes `--ac-id AC-X` and asserts stdout `AC-X`, so **an id that is not `AC-<digits>` is accepted today**; `:3374` `test_auto_assigns_ac_ids` pins `["AC-1", "AC-2", "AC-3"]`.

**F9 — Only two list sections carry an identity the user can cite.** In state, `acceptance_criteria` entries carry `ac_id` and `open_questions` entries carry `question_id`. `constraints`, `risks`, `out_of_scope` and `affected_areas` entries carry **no id field at all**: `record-out-of-scope`, `record-constraint` and `record-risk` each COMPUTE a positional label (`"OOS-{len+1}"`, `"Constraint-{len+1}"`, `"Risk-{len+1}"`) to hand to `_flip_findings`, and none of the three persists it on the entry. **This is the decisive fact for D2's scope fork.**

**F10 — Revision keeps landed findings valid; deletion would strand them silently.** `_flip_findings` (`_cmds_phase4_setters.py:59`) sets `landed_in` and `landed_ref` on each named finding, and `add-ac` passes the AC's own `ac_id` as `landed_ref`. `cmd_verify_coverage` (`_cmds_phase4_verify.py:31`) checks only that `landed_in != "unlanded"` — **it never checks that `landed_ref` resolves to a live entry.** So a delete verb would leave findings marked landed against an AC that no longer exists and `verify-coverage` would still pass. This is why this plan proposes revision and never deletion.

**F11 — `verify-ac-shape` cannot fire through the normal flow.** `import-handoff` seeds `spec_type`, `constraints`, `affected_areas`, `risks`, `open_questions` and `design_anchor` — **not `acceptance_criteria`** (`_cmds_handoff.py`, the pre-seed block); it only READS that list as a warning guard (`:642`, `:821`) and EXPORTS it into the plan handoff (`:1308`). So every AC in state got there through `add-ac`, which already applied the same `EARS_REGEX` (F6). `cmd_verify_ac_shape` (`_cmds_phase4_verify.py:87`) re-applies that regex and also reports an unknown variant, which F6's enum equality rules out. The suite says so in its own test name: the only test that makes the verb exit 2 is `TestPhase4VerifyAcShape.test_fails_when_state_corrupted` (`tests/lib/test_specify_helper.py:3603`), **which hand-edits `specify-state.json` to insert the bad entry.** `verify-ac-shape` is a pure backstop. **Load-bearing for D3.**

**F12 — The render, and what a duplicate id does to it.** `_specify/_render.py:58` `_render_section_acs` filters `state["acceptance_criteria"]` by `subsection`, preserves list order, and emits `- [ ] **{ac_id}**: {statement}`. So two entries sharing `ac_id` render as two `**AC-8**` bullets, and an in-place revision that keeps both the entry's position and its `ac_id` changes neither the order nor the printed label.

**F13 — The recovery, and what it costs.** `cmd_reset_state` (`_cmds_phase01.py:42`) atomically writes `default_state()` over `.devforge/specify-state.json`. `src/commands/specify/main.md:96` states the model: *"Fresh-every-run: any prior state is overwritten. `/devforge:specify` does not resume mid-flight prior runs — every invocation starts clean."* A reset therefore discards the Phase 1 input reads, the Phase 1.5 findings, the Phase 2 decision points and all nine rendered sections — everything the run has built.

**F14 — The Step 4.9 block already contains two non-blocking precedents, and they are handled DIFFERENTLY at Phase 5.** Step 4.9 spans `src/commands/specify/main.md:819`–`:843`.
- `check-constitution-compliance` (`:834`–`:837`): *"Warnings appear on stderr but exit code is 0 unless the helper itself fails. Surface any warning text to the user as plain prose so they decide whether to amend the spec or proceed with the conflict noted … Re-run this command at Phase 5 entry so changes between Phase 4 and approval re-surface relevant warnings."* That re-run is Step 5.2 (`:936`), whose prose closes *"Surface any warning text to the user as plain prose alongside the approval prompt."*
- `verify-scope-coherence` (`:840`–`:843`): *"Warnings appear on stderr but exit code is 0 unless the helper itself fails — a warning is NOT a verify failure, so do not treat it as one. Surface any warning text to the user as plain prose."* ⚠ **It is NOT re-run at Step 5.2**, and it names no approval placement. IMPORTANT RULES item 11 (`:1019`) carries its stance in rule form.
- **So the two siblings share one sentence — *"Surface any warning text to the user as plain prose"* — and differ on whether the check is re-run at the approval gate.** D1's second half must pick, and it cannot claim to match both.
- **Count, for Phase 3's Verify:** `grep -n "Surface any warning text" src/commands/specify/main.md` returns **three** lines today — `:837`, `:843` and `:939`.

**F15 — The approval summary shows counts, not AC text.** `_approval_summary` (`_specify/_render.py:359`) renders *"**Acceptance criteria**: {acc} testable criteria across {sc} AC categories"* — a count. Out-of-scope items render in full; ACs never do. **So a number inside an AC statement is NOT in the approval block.** The user meets it in `spec.md`, written at Step 4.11, or in prose the model surfaces.

---

## Coordination with the Hypothesis-Suppression Precision Plan

⚠ **The sibling is referenced by TITLE throughout this section, because its number has already moved more than once: the Hypothesis-Suppression Precision Plan (`105-HYPOTHESIS-SUPPRESSION-PRECISION-PLAN.md` as of 2026-09-20; it was `103-` when this section was first written, and no `103-` file exists).** A bare number rots; the title does not.

It was drafted the same day, in this same working tree, by a parallel session. It audits `research_helper verify-hypothesis-suppression` — a blocking gate that over-fires — and its **D6 DECLINES demotion to an advisory WARN**, citing the same precedents this plan's D1 invokes to RECOMMEND demotion (plan 34's hygiene demotion to ADVISORY, plan 87 D1's advisory WARN). **Two plans in one repo therefore take opposite stances on one question class: what to do with a blocking heuristic gate that over-fires.** A future session will read both. Either the distinction below holds, or the stances conflict — and this section says which.

### Test 1 — is the predicate repairable?

**The Hypothesis-Suppression Precision Plan declines demotion because it first repairs the predicate.** Its D3 adds a specificity floor (*"ONE token of 8 or more characters"*), its D2 fixes the evidence source set so the overlap is evidence-grounded, its D4 validates the addressed-hypotheses labels so the gate's own exemption cannot be silently lost, and its D5 removes the lexical exit so rewording stops being the cheapest way past an exit 2. Its D6 says so outright: *"D1, D2 and D3 remove most of that pressure and D5 gives the remainder a named exit, so the reason to demote is largely spent before the question is put."*

**That route does not exist here.** The hypothesis gate's false positives come from **weak tokens** — a package-path segment weighing the same as a 21-character API identifier — and a length floor filters exactly that. This gate's false positives come from **two correct statements**: in `within 200 ms` and `within 500 ms` both numbers are right, and no token-level filter separates them, **because what differs is the thing being measured, not the vocabulary** (F1, F2).

Two repairs were considered and each fails:

- **Widen the grouping key to include the preceding word(s).** It fails on that exact pair: both statements carry `within` immediately before the number, so the widened key is identical and the collision survives. A wider window is also a number nothing in this repo measures — D1's rejected option (b).
- **Restrict comparison to a single rendered section.** It destroys the true positive the repo's own fixture encodes: `tests/lib/test_specify_helper.py` `TestPhase4VerifyNumericalConsistency.test_fails_on_inconsistent_render` sets `3 packages` through `set-overview` (§1) and `5 packages` through `set-current-state` (§2) — **the inconsistency it pins is cross-section** (F3).

### Test 2 — does a human gate downstream re-check the same concern?

**`/devforge:research` has no terminal approval gate over the report's content.** Verified 2026-09-20: `grep -niE "approve|approval" src/commands/research/main.md` returns **nothing**. Its Phase 4 asks whether to SAVE the report, not whether the reasoning is sound. So an invariant that gate stops defending is defended by nothing after it.

**`/devforge:specify` is the opposite.** Phase 5 Step 5.3 (`main.md:943`) is a mandatory `AskUserQuestion` — `"Approve this spec?"` with `approve` / `request-changes` / `cancel` — and Step 5.1 echoes the spec's content back before it. **Two heuristics in this command's own Step 4.9 already rely on that backstop by name** (F14), and IMPORTANT RULES item 11 states it as a rule: *"the hard human gate is the Phase 5 approval echo-back, and this check is a warning backstop behind it."*

**That is why demotion is safe here and is not safe there.**

### The retained counter, not softened

**If either test is wrong, this plan is the one that is wrong, not the sibling.** ⚠ **Neither plan measures its gate's false-positive rate, and neither will after building.** The Hypothesis-Suppression Precision Plan says so in its own D6 counter-argument (*"the false-positive rate is unknown before these fixes and will still be unknown after them"*), and this plan says so in D1. **Both are betting on reasoning.**

### One disagreement with the sibling's reasoning — about the maxim's fit, not about its conclusion

The Hypothesis-Suppression Precision Plan's D6 cites plan 90's *"a gate that silently disarms itself is worse than no gate."* **That maxim described `regression-gate` reading its own failure as `baseline-failing` and SILENTLY ceasing to gate.** A demotion to WARN is not silent: it prints its report on every run in which it fires. ⚠ **This is a dispute about the maxim's fit, NOT a claim that the sibling's D6 is wrong** — its conclusion may well be right for its gate, and Test 1 above is the reason this plan believes it is.

**What follows is this plan's own reading, offered as a reading and never as a report of what that plan says.** Its D6's actual words are *"A WARN printed inside a run that is already producing the report is precisely the shape plan 90 named"* — and on this plan's reading what makes that worrying is not silence but audience: a warning printed while the artifact is already being produced reaches nobody positioned to act on it. ⚠ **The sibling does not state that as a concern separate from the maxim** — verified by reading its D6 live on 2026-09-20 — **this plan separates it.** This plan then answers it with **D1's half 2**: the warning is surfaced to the user at the approval gate, where the command already routes two other advisory checks. **The sibling has no equivalent surface to answer it with, because its command has no approval gate** (Test 2). That asymmetry, not the maxim, is what separates the two decisions.

### Shared surfaces, and the rule that binds

**Both plans edit the same three ledger surfaces at their docs phase:** `PLAN-STATUS-ARCHIVE.md`'s `## Index` line, that same file's `## Entries` entry, and `CHANGELOG.md` — **three surfaces in two files, two of them inside one file**, so a stale read of `PLAN-STATUS-ARCHIVE.md` can clobber both halves of the sibling's status at once. **The house rule: whichever plan ships SECOND reads those three surfaces LIVE and re-derives its own edits, never a pre-computed diff — the rule binds the READ, not the edit.** The Hypothesis-Suppression Precision Plan's Phase 5 also names `DEVELOPMENT-STATUS.md` and `README.md`; this plan's Phase 4 names both too, so they are shared as well.

⚠ **Both plans are being drafted against a MOVING ledger:** `PLAN-STATUS-ARCHIVE.md` was restructured by other work on 2026-09-20 — it gained the `## Index` section that the repo `CLAUDE.md` used to carry — and `CHANGELOG.md` and `VERSION` are modified and uncommitted in this tree. Phase 4 therefore re-reads `git status`, reads each ledger LIVE, commits **by explicit path**, and must not sweep those files wholesale.

### Source-file scope, verified

- **The Hypothesis-Suppression Precision Plan edits** `src/devforge/lib/_research/` (`_cmds_render_verify.py`, `_cmds_approach.py`, `_cmds_phase1.py`, `_cli.py`, `_render.py`) and `src/commands/research/main.md`. Its Phase 4 states *"`src/commands/discover/main.md` is not touched"* with a `git diff --stat` Verify line.
- **This plan edits** `src/devforge/lib/_specify/` and `src/commands/specify/main.md`.
- **The two EDIT sets do not intersect** — verified by reading that plan's Phase 1–5 deliverables and its file anchors on 2026-09-20.
- ⚠ **One asymmetric touch, recorded so nobody reads it as a conflict:** the sibling's file anchors list `src/devforge/lib/_specify/_cmds_phase4_verify.py` as **read-only** (its F7 records that file as the second consumer of `_shared/text_overlap.py`), and **this plan WRITES that file** — a different function, `cmd_verify_numerical_consistency`, which imports no shared tokenizer. Its D1 keeps its filters out of `_shared/text_overlap.py` precisely so that consumer is untouched, and nothing in this plan's Phase 1 changes what F7 records. A session working that plan and re-reading this file after this plan's Phase 1 sees a changed function it does not depend on.

---

## Phase 0 — ratification

Nothing below is ratified. Each item states the decision, its options where they exist, a recommendation, and the strongest counter-argument, **recorded honestly rather than answered away**. Proposed emitted wording and proposed stderr text are **substance, not final text**: the builder may reword, but every element named must survive. **No emitted sentence may name plan vocabulary** ("D1", "plan 102", "Phase 0"); real headings such as `Step 4.9` are fine.

### D1 — Demote `verify-numerical-consistency` to a non-blocking WARNING, and SURFACE it

**The decision has two halves, and it is not ratifiable in one.**

**Half 1 — the exit code.** `cmd_verify_numerical_consistency` writes its report and returns **0**. The per-noun detail lines stay byte-identical; the header line gains explicit WARNING framing so a reader can tell an advisory report from a failure. The predicate, the heading and table-separator skips, and the `Variance rule #6` anchor are unchanged.

**Half 2 — the surface.** The emitted instruction surfaces the warning text to the user **as plain prose alongside the Phase 5 approval prompt**, in the shape this command already uses for its two other advisory checks (F14): the Step 4.9 bullet carries the siblings' shared sentence *"Surface any warning text to the user as plain prose"*, and the warning reaches the approval gate.

- ⚠ **The two siblings diverge on the carrier, so "match both" is impossible** (F14). This decision picks one:
  - **(i) Re-run the verb at Step 5.2**, beside `check-constitution-compliance`, whose own Step 4.9 text already instructs exactly that (*"Re-run this command at Phase 5 entry so changes between Phase 4 and approval re-surface relevant warnings"*) and whose Step 5.2 prose already ends *"alongside the approval prompt"*. **RECOMMEND** — a re-run cannot go stale, and the sentence it needs already exists one step away.
  - **(ii) Carry the Phase 4 warning forward** and restate it at the approval prompt, the `verify-scope-coherence` shape.
  - **Counter to (i), recorded:** Step 5.2 is titled *"Constitution recheck (re-run)"*, so (i) either widens that step past its heading or adds a sibling step — a bigger edit than (ii), and one more helper call on every run.

**Why half 2 is part of the decision and not a Phase 3 detail.** Without surfacing, **a demoted gate becomes a warning nobody reads, and the demotion trades a false-positive block for a silent miss.** Half 2 is what makes the human backstop real rather than assumed — the backstop IMPORTANT RULES item 11 already names for `verify-scope-coherence`. **Consequence, stated so no phase treats it as cosmetic: Phase 3's instruction edits are LOAD-BEARING for D1.** Shipping Phase 1 without Phase 3 leaves the gate silent, which is strictly worse than today.

**Options for half 1:**

- **(a) Demote to WARN (exit 0). RECOMMEND.**
- **(b) Narrow the grouping key** to a wider noun-phrase window, so `200 ms` and `500 ms` no longer collide.
- **(c) Delete the verb.**
- **(d) Keep it blocking** and rely on D2 to make the recovery cheap.

**The argument for (a).** Two in-repo precedents sit in the SAME Step 4.9 block as the verb being demoted: `check-constitution-compliance` and `verify-scope-coherence` are both heuristics that warn, exit 0, and name the Phase 5 approval echo-back as the real backstop, with IMPORTANT RULES item 11 carrying that stance in rule form (F14). Plan 34 set the wider precedent when it demoted the hygiene scans to ADVISORY so they never block a verdict. And the case here is stronger than noise: **the predicate is unsound, not merely imprecise.** Grouping on the bare noun cannot separate the two cases by construction (F1, F2), so no amount of care by the author avoids the false positive.

**Against (b).** Any widened window is still a heuristic — and it fails on the exact pair that motivated the plan, since `within 200 ms` and `within 500 ms` share the preceding word (`## Coordination with the Hypothesis-Suppression Precision Plan`, Test 1). Nothing in this repo measures which window works, and **this plan has no measurement.** Picking a window would be choosing a number on no evidence.

**Against (c).** The real signal exists: the same quantity restated with a different value is a genuine defect, and the fixture test `test_fails_on_inconsistent_render` is a real instance of it (F3). A warning keeps that signal at zero cost to a correct spec; deletion throws it away.

**Against (d) — the sharpest counter, and it is the reason (a) is recommended rather than (d).** A blocking gate on an unsound predicate does not merely cost turns; it forces the model to reword CORRECT content until the regex is satisfied. That is word-picking: the spec gets worse so the check can pass. Making the recovery cheap (D2) reduces the PRICE of that wrong behavior instead of stopping it, and would leave a gate that still rewards rewording a true statement into a vaguer one. ⚠ **This plan records no prior maintainer statement about this failure mode; the argument stands on the mechanism, not on precedent.**

**Accepted costs, named rather than argued away.**
- A genuine inconsistency no longer blocks. Nothing mechanical stops a spec carrying two contradictory numbers from being approved.
- The approval block renders AC counts, not AC text (F15), so the user does not meet the number there. **The carrier is half 2's prose, which is model judgment and is checked by nothing** — the same bound the two sibling checks already carry.

**RECOMMEND (a) + half 2, with carrier (i).**

### D2 — Add ONE in-place revision verb, `revise-ac`

**The shape.**

```
specify_helper revise-ac --ac-id <existing id>
    [--statement "<EARS-formatted statement>"]
    [--ears-variant <ubiquitous|event_driven|state_driven|optional|unwanted>]
    [--verification-command "<executable check>"]
    [--test-anchor "<path::test_name>"]
```

- It replaces only the fields passed, on the entry ALREADY IN `state["acceptance_criteria"]`, **keeping that entry's list position and its `ac_id`** — so render order and the printed `AC-8` label are unchanged (F12) and every landed finding reference stays valid (F10).
- An `--ac-id` matching no entry exits 2.
- No field flag passed exits 2.
- It re-validates against `EARS_REGEX` exactly as `add-ac` does, including the `AC_UBIQUITOUS_ONLY_SUBSECTIONS` rule when the resulting variant or verification command is affected (F6).
- **It never deletes and never reorders.**

**The scope fork:**

- **(a) `revise-ac` only**, plus one honest sentence in the emitted text naming which section can be revised in place and which still require a reset. **RECOMMEND.**
- **(b) A revision verb for all six list sections.**
- **(c) A generic `revise-entry --section --index`.**

**The decisive argument for (a).** (b) is not a symmetric six-fold repeat of the same work. Four of the six sections — `constraints`, `risks`, `out_of_scope`, `affected_areas` — carry **no id field in state at all** (F9), so (b) must first invent an identity scheme for them, decide how it survives the wholesale `import-handoff` pre-seed, and answer what an id means for an entry the user has never seen labelled. (c) avoids that by addressing entries by list index — which the user cannot cite, which no rendered artifact shows, and which shifts under any later append. `acceptance_criteria` is the one section with a stable identity the user already cites by name at the approval gate, and it is the section the incident hit.

**Counter-argument, recorded and NOT answered:** the cost is identical for a risk row or an out-of-scope item. A user who says "change the third risk's mitigation" at `request-changes` still pays the full reset-and-replay (F13), and (a) narrows the dodge surface without closing it. Nothing here makes that case cheaper, and this plan does not claim it does.

**Named strengthening arm, NOT built.** The first `request-changes` reply that names a constraint, risk, out-of-scope or affected-area entry opens (b) — and **that plan owes the identity scheme first**, before any verb.

**A build constraint the ratifier should see, recorded rather than smoothed.** The recommended module placement is beside `cmd_add_ac` in `_specify/_cmds_phase4_setters.py`, because the new verb shares that module's validators, its `_state_transaction` pattern and its pre-validate-before-transaction rule. ⚠ **That file is 695 lines today**, and `.claude/agents/python-engineer.md:85` sets *"> 400 lines | Plan a split. > 600 lines without a split = automatic finding (HIGH) in code review."* — so the file is already past the automatic-HIGH threshold and this verb grows it. The alternative is a new sibling module for the revision verb. **Phase 2 picks one and records the reason; neither option is pre-chosen here**, and either way the split of the existing file is a pre-existing condition this plan does not undertake.

**RECOMMEND (a).**

### D3 — Repair the false sentences in the shipped instruction

**Mandatory regardless of how D1 and D2 ratify**, because these sentences are false against TODAY's code — not merely stale relative to the proposal. All of them are one change, under the repo's cross-check rule. **Six claims at five lines in `src/commands/specify/main.md`:**

1. **`:830`, the `verify-ac-shape` bullet — *"re-add with the same `ac_id` is rejected"*.** FALSE today: `add-ac` appends a duplicate silently, and a duplicate `AC-8` renders as two `**AC-8**` bullets (F6, F8, F12). Under D4 this sentence becomes true for the first time.
2. **`:830`, the same bullet's fallback — *"reset state and re-walk Step 4.4 to avoid stale entries"*.** TRUE today, and it is the recovery the benchmark agent correctly followed. **It is the cost this plan attacks, not a model error.** Under D2 it is replaced by the `revise-ac` route; if D2 is declined it stays, and the bullet must then say plainly what the reset costs (F13).
3. **`:831`, the `verify-numerical-consistency` bullet — *"resolve by editing the source values via setters and re-rendering"*.** Impossible whenever the offending number sits in any of the six append-only sections (F5); true only for the seven scalar fields. **Under D1 this bullet is also where half 2's surfacing sentence lands** (F14) — without it the demoted warning reaches nobody.
4. **`:939`, Step 5.2 — state *"may have changed … (e.g., a Phase 4 verifier loop revised an AC)"*.** Names a capability that does not exist today (F4). It becomes true only if D2 ships; if D2 is declined the example must be replaced with one that is real.
5. **`:946`, Step 5.3's `request-changes` arm — *"The state file persists across the loop; setters mutate in place."*** FALSE for all six list sections (F5). **This is the most consequential of the six: it sits on the command's primary human gate.** Under it, a user asking to change AC-8's wording at the approval gate leads the model to re-run `add-ac`, producing a SECOND AC-8 in the rendered spec (F12). **It must be fixed even if D1 and D2 are both declined** — in that case it must state plainly that list-shaped sections do NOT mutate in place, and name the reset as the recovery.
6. **`:1016`, IMPORTANT RULES item 8 — *"Inconsistent numbers in the same spec are a hard error — `verify-numerical-consistency` blocks the render until reconciled."*** Becomes false the moment D1 ships. ⚠ **It is already imprecise today:** `cmd_render` (`_cmds_phase4_verify.py:370`) consults no verifier, so nothing in the helper prevents `render` from being called — the block is procedural, from Step 4.9's *"run in order"* placement ahead of Step 4.11. The repaired sentence states the advisory status and keeps the verify-by-enumeration duty, which is independent of the gate.

**One site outside that file, found while cross-checking, and owned by Phase 4 rather than Phase 3.** `DEVELOPMENT-STATUS.md:16` lists the Phase 4 verifiers as *"… `verify-ac-shape` (per-variant regex), `verify-numerical-consistency`, non-blocking `check-constitution-compliance`"* — the qualifier attaches to the last item only, so after D1 the line reads as though the demoted verb still blocks. The two `done-plans/` hits are history and are NOT rewritten.

**RECOMMEND D3 as stated.**

**Counter-argument, recorded:** claims 1, 4 and 6 are repairs whose final text depends on how D1 and D2 ratify, so D3 cannot be built first. Sequencing it after Phases 1 and 2 means the false sentences stay shipped for two more phases — knowingly, and that is the ordering this plan accepts.

### D4 — Reject a duplicate `ac_id` in `add-ac`, and make `_next_ac_id` scan instead of count

**The decision, in two halves that ship together.**
- `add-ac` exits 2 when the resolved `ac_id` already exists in `state["acceptance_criteria"]`, leaving state unchanged. The check runs on a read-only load BEFORE the write transaction opens, matching the pre-validate rule the module already states for `--finding-ref` (*"This guarantees no partial write is structurally possible"*, F5/F6).
- `_next_ac_id` returns one above the highest existing `AC-<n>` suffix instead of `1 + len(...)` (F7).

**Why the halves ship together, and the plan must say so.** With duplicate rejection alone, `1 + len(...)` still hands out an id that an earlier explicit `--ac-id` already consumed — turning today's silent duplicate into a hard exit 2 in the middle of a run, at a call the model wrote correctly. Scanning removes that.

**Severity is a NIT and this plan says so.** No emitted instruction passes `--ac-id` (F8), so the defect is **latent** today — it cannot be reached through the documented flow. It becomes reachable the moment D2 ships, because `revise-ac`'s existence makes explicit-id handling a normal thing for the model to reason about.

**Two shape constraints from the existing tests, recorded so the builder does not break them.**
- `test_accepts_explicit_ac_id` passes `--ac-id AC-X` and asserts stdout `AC-X` (F8), so **a non-`AC-<digits>` id is accepted today.** The scan must SKIP an id it cannot parse, never crash on it and never reject it.
- Consequence, stated rather than discovered later: on a state whose only entry is `AC-X`, the count rule yields `AC-2` and the scan rule yields `AC-1`. Neither collides, but the value differs, and Phase 2 records that divergence as intended rather than as a regression. `test_auto_assigns_ac_ids` (`["AC-1","AC-2","AC-3"]`) is unaffected either way.

**For the tripwire record:** D4 adds a write-time rejection INSIDE an existing setter — the same class as the EARS validation `add-ac` already performs. It adds **no `verify-*` gate number and no new hard-fail validator script.**

**RECOMMEND D4 as stated.**

**Counter-argument, recorded:** it is a fix for a path nothing reaches, shipped on the strength of a prediction that D2 will make it reachable. If D2 is declined, D4 closes a defect that remains latent — cheap, but unevidenced, and this plan has no observation of it.

### OQ-1 — Does `revise-ac` accept `--subsection`?

**RECOMMEND no, in v1.** A subsection change is a re-classification, not a wording fix: `verify-ac-subsection-coverage` (`_cmds_phase4_verify.py:57`) computes its `populated` set from each entry's `subsection`, so moving one AC can empty the subsection it left and silently satisfy the one it joined. `add-ac`'s `AC_UBIQUITOUS_ONLY_SUBSECTIONS` rule also binds subsection to variant and to `--verification-command` together (F6), so the flag would have to re-run that pair check. **Name the bound in the emitted text:** a subsection change is not a revision, and it still requires the reset path.
**Alternative:** accept `--subsection` and re-run the full `add-ac` validation set on the revised entry.

### OQ-2 — Does `revise-ac` touch finding refs?

**RECOMMEND no.** The entry keeps its existing `landed_ref` because it keeps its `ac_id` (F10, F12), and `set-finding-landed` (`_cmds_phase4_setters.py:649`) already owns direct finding flips — its own docstring names *"correcting a typo in landed_ref"* as its purpose. Adding `--finding-ref` to `revise-ac` would create a second owner for one field.
**Alternative:** accept a repeatable `--finding-ref` that lands additional findings on the revised AC, leaving existing ones untouched.

### OQ-3 — Does anything revert an `--mark-na` subsection marker?

**RECOMMEND out of scope, and name it.** `add-ac --mark-na` writes `state["ac_subsection_na"][subsection] = reason` (F6/`:491`), which overwrites in place, so a marker's TEXT can already be corrected — but **no verb removes the key**, so a subsection marked N/A cannot be un-marked without a reset. That is a real gap of the same family, it is not what the incident hit, and closing it needs a delete-shaped operation this plan's non-goals forbid.
**Alternative:** a `--clear` form on `add-ac --mark-na` that removes the key.

### OQ-4 — Where does the CHANGELOG entry land?

**Verified facts (2026-09-20):** `VERSION` reads `2.0.12`; `CHANGELOG.md`'s newest section is `## [2.0.12] - 2026-09-20` with `### Changed`, `### Removed` and `### Fixed`; **no `## [Unreleased]` section exists** (a `grep -n Unreleased CHANGELOG.md` returns nothing); and both `VERSION` and `CHANGELOG.md` are modified in the working tree — a release is being cut right now.
**RECOMMEND a new `## [Unreleased]` section above `## [2.0.12]`, and NEVER an edit into the released 2.0.12 block.** An entry added inside a version section that is being cut changes what that version claims to contain, after its number was set. ⚠ The Hypothesis-Suppression Precision Plan's Phase 5 says *"one entry under `## [Unreleased]` — re-verify the section and its subheadings live before writing"*, so **whichever plan ships second finds that section already created** and adds to it rather than creating it.
**Alternative:** hold the entry until the next version section is opened.

### OQ-5 — Back-porting into installs already shipped

**RECOMMEND an explicit NON-GOAL,** per the standing house rule: consumers arrive via `install.sh` / `update.sh`. An install that has already run `/devforge:specify` keeps the blocking verb and the false sentences until it updates.
**Alternative:** none proposed. ⚠ The frozen benchmark install is never touched.

### Phase 0 close record

**PENDING — nothing is ratified.** When it closes, this record must name **each** of D1, D2, D3, D4 and OQ-1 through OQ-5 with its outcome (ratified / amended / declined), state whether per-item deliberation was supplied, state whether the close was an explicit pick or a delegation (plan 98's D1 distinction), and say which files the outcomes put in scope. **Every counter-argument stays where it is written — a ratified decision with its counter-argument deleted cannot be re-opened honestly.**

#### Verify

- The record names **each** of D1–D4 and OQ-1–OQ-5 with an explicit outcome. No item is silently omitted.
- **D1's outcome names BOTH halves and, for half 2, the carrier — (i) or (ii).** A record that ratifies "demotion" without naming half 2 has not closed D1.
- It states whether per-item deliberation was supplied, and whether the close was a pick or a delegation.
- Every decision above still carries its counter-argument, unshortened.
- The record says what the outcomes put in scope: whether D2 ships (which decides whether Phase 2 exists and what claims 1, 2 and 4 in D3 become), whether D1 ships (which decides Phase 1 and D3's claims 3 and 6), OQ-1's answer (which decides `revise-ac`'s flag set), and OQ-4's answer (which decides where Phase 4's CHANGELOG entry goes).

---

## Phases

Phase 0 is the `## Phase 0 — ratification` section above; **nothing below starts before its close record exists.** Build order is 1 → 2 → 3 → 4, because Phase 3 repairs sentences whose final text depends on what Phases 1 and 2 shipped. Phases 1 and 2 are independent of each other. ⚠ **Phase 3 is load-bearing for D1, not cosmetic** — Phase 1 without Phase 3 leaves the demoted check silent.

### Phase 1 — D1 half 1, Python

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** Commit by explicit path.

#### Deliverables

- `src/devforge/lib/_specify/_cmds_phase4_verify.py` — `cmd_verify_numerical_consistency` writes its report and returns **0** on inconsistencies. The per-noun detail lines (`"  - {noun}: {values} (lines …)"`) are byte-unchanged. The header line gains explicit WARNING framing and states that the check does not block; the verb name and the `Variance rule #6` anchor survive in it. The docstring says the verb is advisory.
- `NUMERIC_DIGIT_NOUN_RE`, `NUMERIC_HEADING_RE` and `NUMERIC_TABLE_SEP_RE` are **byte-unchanged** — this phase demotes the verb, it does not re-tune the predicate (D1's rejected option (b)).
- `src/devforge/lib/_specify/_cli.py` — the `verify-numerical-consistency` help text, if it asserts a blocking outcome, is corrected; otherwise recorded as a verified no-op.
- `tests/lib/test_specify_helper.py` — `test_fails_on_inconsistent_render` is renamed to name what it now asserts, asserts `returncode == 0`, and keeps `assertIn("packages", r.stderr)`. A new assertion pins the WARNING framing on stderr. A new test asserts that **two legitimately different quantities of one unit** (F2's `ms` pair) produce the warning and exit 0 — the false-positive class, pinned as a standing regression rather than left to prose.

#### Verify

- `grep -n "return 2" src/devforge/lib/_specify/_cmds_phase4_verify.py` shows no `return 2` inside `cmd_verify_numerical_consistency`; the state-load failure path keeps `_die`.
- A state rendering `200 ms` and `500 ms` in two ACs exits **0** and prints the warning naming `ms`.
- A state rendering `3 packages` and `5 packages` exits **0**, prints the warning naming `packages`, and the renamed test asserts exactly that.
- `git diff src/devforge/lib/_specify/_schema.py` is empty.
- `tests/lib/test_specify_helper.py` is green, then the full `tests/lib` suite is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — D2 + D4, Python

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** Commit by explicit path.

#### Deliverables

- **`revise-ac`** — a new `cmd_revise_ac`, placed either beside `cmd_add_ac` in `_specify/_cmds_phase4_setters.py` or in a new sibling module; **the phase records which, and why, against the 695-line fact in D2.** It takes `--ac-id` (required) plus the optional field flags OQ-1 settles, replaces only the fields passed on the entry already in the list, keeps the entry's index and `ac_id`, re-validates against `EARS_REGEX`, exits 2 on an unknown `--ac-id`, exits 2 when no field flag is passed, and touches no finding record (OQ-2). It prints the `ac_id` on success, as `add-ac` does.
- **`_cli.py`** — the `revise-ac` subparser, registered beside `add-ac`.
- **Duplicate rejection in `add-ac` (D4)** — a read-only pre-check before the write transaction; exit 2 naming the colliding `ac_id`.
- **`_next_ac_id` scans (D4)** — highest existing `AC-<n>` suffix plus one, skipping any `ac_id` it cannot parse (F8).
- **Tests** for every new function and every new branch, including the two shape constraints D4 records.

#### Verify

- A revise on the middle of three ACs: the entry keeps its index, keeps its `ac_id`, carries the new statement, and `state["findings"]` is byte-unchanged (its `landed_in` / `landed_ref` untouched).
- `revise-ac --ac-id <unknown>` exits 2 and `specify-state.json` is byte-unchanged.
- `revise-ac --ac-id <known>` with no field flag exits 2 and `specify-state.json` is byte-unchanged.
- `revise-ac` with a statement that fails its variant's `EARS_REGEX` exits 2 and `specify-state.json` is byte-unchanged.
- `add-ac --ac-id AC-1` on a state that already holds `AC-1` exits 2 and `specify-state.json` is byte-unchanged.
- `add-ac --ac-id AC-X` on a fresh state still succeeds and still prints `AC-X`; `test_accepts_explicit_ac_id` is green, unedited.
- `test_auto_assigns_ac_ids` is green, unedited.
- A rendered spec after a revise contains exactly one `**AC-8**` line.
- `grep -rnE "def cmd_(remove|delete|drop)_" src/devforge/lib/_specify` returns nothing — no delete verb was added.
- The full `tests/lib` suite is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 3 — D1 half 2 + D3, instructions only

**Route: instruction-author → instruction-reviewer, one dispatch for the one file, committing by explicit path.** Instruction-only: **no `.py` file changes in this phase.** **Needs Phases 1 and 2 first** — it describes what they shipped.

#### Deliverables

- `src/commands/specify/main.md`, D1's half 2:
  - the `verify-numerical-consistency` bullet carries the siblings' shared sentence — *"Surface any warning text to the user as plain prose"* — and states the advisory status in the siblings' shape (F14);
  - the warning reaches the **Phase 5 approval prompt** through the carrier D1 ratified: **(i)** the verb is re-run at Step 5.2 beside `check-constitution-compliance`, whose Step 5.2 prose already ends *"alongside the approval prompt"*, or **(ii)** the Phase 4 warning is carried forward and restated there.
- `src/commands/specify/main.md`, all six claims in D3:
  - the `verify-ac-shape` bullet's duplicate-id sentence, now true (or, if D4 was declined, stating what actually happens);
  - that bullet's recovery, routed to `revise-ac` (or, if D2 was declined, naming the reset and what it costs);
  - the `verify-numerical-consistency` bullet's recovery — one that is possible for a list-section value;
  - Step 5.2's parenthetical example;
  - **Step 5.3's `request-changes` arm** — which sections mutate in place and which do not, and the `revise-ac` route for an AC (or, if D2 was declined, the plain statement that list-shaped sections do NOT mutate in place, with the reset named);
  - IMPORTANT RULES item 8 — advisory rather than *"a hard error"*, keeping the verify-by-enumeration duty and dropping the *"blocks the render"* claim.
- Nothing else in the file changes. IMPORTANT RULES item 11 stays byte-identical: it is the in-file precedent D1 leans on, not a site to edit.

#### Verify

- **D1 half 2, checked explicitly.** That grep returns **three** lines today (F14: `check-constitution-compliance`'s Step 4.9 bullet, `verify-scope-coherence`'s, and Step 5.2's). After this phase it returns **at least four**, and one of the added hits sits on the `verify-numerical-consistency` bullet; under carrier (i) Step 5.2's own text also names the demoted check. Either way the warning is named at the Phase 5 approval prompt. ⚠ **A Phase 3 that repairs D3's six claims and adds none of those hits has not shipped D1.**
- Each of D3's six claims reads true against the post-Phase-1/2 code, checked sentence by sentence against the verbs as built.
- `grep -n "blocks the render" src/commands/specify/main.md` returns nothing.
- `grep -n "setters mutate in place" src/commands/specify/main.md` returns nothing.
- `grep -n "reset state and re-walk" src/commands/specify/main.md` returns nothing, or exactly the declined-D2 wording.
- `grep -n "revise-ac" src/commands/specify/main.md` returns the Step 4.9 recovery and the Step 5.3 arm.
- `git diff --stat src/commands/` lists `specify/main.md` and nothing else.
- No other file under `src/` contradicts them: `grep -rn "verify-numerical-consistency" src/` returns only the Step 4.9 invocation, its bullet, item 8, any Step 5.2 re-run, and the Python sites.
- The live-spec tests are green: `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py`, `tests/scripts/test_claude_emitter.py`.
- No emitted sentence names plan vocabulary.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 4 — Docs sweep

**Route: instruction-author → instruction-reviewer. Docs only.** ⚠ **Apply the coordination rule before touching any ledger** (`## Coordination with the Hypothesis-Suppression Precision Plan`): another session may be building that plan in this checkout, and `PLAN-STATUS-ARCHIVE.md`, `CHANGELOG.md` and `VERSION` have all moved under this plan while it was drafted. Re-read `git status`, read each ledger LIVE, re-derive every edit from what is there, and **commit by explicit path — never `git add -A`, and never a wholesale sweep of those files.**

#### Deliverables

- **`PLAN-STATUS-ARCHIVE.md`'s `## Index` section** — exactly one index line for this plan, in the shape of its neighbours there (plans 96–101). ⚠ **Nothing goes to the repo `CLAUDE.md`** — no index line, and no pointer to the archive either.
- **`PLAN-STATUS-ARCHIVE.md`'s `## Entries` section** — the full entry, and the authority the index line summarizes: the evidence split, what each of the four items shipped, the accepted costs, the tripwires, the sibling-plan coordination, and Phase 5's anchors with their pair.
- **`CHANGELOG.md`** — one entry, placed per OQ-4's answer, with the evidence class FIRST and the honest bounds LAST.
- **`DEVELOPMENT-STATUS.md:16`** — the `specify.md` bullet's verifier list, where the `non-blocking` qualifier currently attaches only to `check-constitution-compliance` (D3's out-of-file site).
- **`README.md`** — an edit or a recorded verified no-op.

#### Verify

- `grep -n "102-SPECIFY" PLAN-STATUS-ARCHIVE.md` returns both sites — the `## Index` line and the `## Entries` anchor — and the `## Index` hit is **exactly one line**.
- ⚠ `grep -n "102-SPECIFY" CLAUDE.md` returns **nothing**. That file carries no plan status, and a hit there is a line this phase must not have written.
- The CHANGELOG entry sits where OQ-4 ratified and nowhere else; the released `## [2.0.12]` block is byte-unchanged if OQ-4 went that way.
- **No ledger line belonging to the Hypothesis-Suppression Precision Plan is altered or reflowed by this sweep** — `git diff` on the shared ledger files shows only this plan's own additions. ⚠ **`PLAN-STATUS-ARCHIVE.md` carries two of the three shared surfaces**, so that one diff is checked twice: once under `## Index`, once under `## Entries`.
- Every site above is recorded as an **edit or an explicit verified no-op**, with the grep that shows it.
- No tracked file names a client, an install, a repo, a branch or any benchmark identifier.

### Phase 5 — Consumer e2e — user-driven HARD GATE, DEFERRED by default, NOT run

⚠ **Deferred by default, per the house pattern.** Everything Phases 1–4 ship is **build-verified at best and NEVER consumer-validated** until this phase runs, and **"done" never means Phase 5 passed.**

- **Fixture:** a testForge20 feature (plan 99's OQ-5 precedent). **The frozen benchmark install is never touched.**

The anchors are known-answer cases:

1. **A spec carrying two legitimately different quantities of one unit** (F2's `ms` pair, in two ACs about different operations) → `verify-numerical-consistency` prints its warning, exits 0, **the run is not blocked**, and the spec renders. **PAIRED WITH 2.**
2. **A spec carrying one genuinely inconsistent restated number** (the same quantity given two values) → the same warning, also no block, **and the warning text is surfaced to the user as plain prose alongside the Step 5.3 approval prompt.** ⚠ The Step 5.1 summary block renders AC counts, not AC text (F15), so "visible to the user" means the surfaced prose and `spec.md` on disk — **never the summary bullet.**
   - **Anchors 1 and 2 are scored as a PAIR:** a change that silences the warning entirely passes 1 and fails 2.
3. **`request-changes` naming AC-8's wording** → exactly one `revise-ac` call → the rendered spec contains exactly one `AC-8`, carrying the new statement, with its finding references intact, **and no `reset-state` anywhere in the turn.**
4. **`add-ac --ac-id` naming an existing id** → exit 2, with `specify-state.json` byte-unchanged.

#### Verify

- Every anchor is scored **explicitly** — stated, not summarized — with the pair scored together.
- **If an anchor fails,** record the negative with the artifacts and name the mechanism before proposing any fix: a block on anchor 1 is D1 half 1; a warning nobody surfaced on anchor 2 is D1 half 2 / Phase 3's Step 4.9 bullet; a second `AC-8`, or a `reset-state`, on anchor 3 is D2 or D3's Step 5.3 arm; a silent append on anchor 4 is D4. **They have different fixes.**
- **A clean run shows the four fixes behave on planted fixtures, never that any gap beyond the observed incident cost anything.**

---

## Non-goals

- **No delete verb for any section.** Deletion would strand landed findings past a gate that does not check for it (F10).
- **No new `verify-*` gate number and no new hard-fail validator script** — plan 75's tripwire, both halves. ⚠ **D1 REMOVES a blocking gate, so the net movement is negative**, and D4's rejection lives inside an existing setter.
- **No change to the fresh-every-run state model or to `reset-state`.** A `/devforge:specify` run still starts clean (F13); this plan only removes a reason to reset mid-run.
- **No identity scheme for the four id-less list sections** (F9), and no revision verb for them — the named strengthening arm under D2, with its own trigger.
- **No back-port into shipped installs** (OQ-5). They arrive via `install.sh` / `update.sh`.
- **No change to `verify-ac-shape`, `verify-coverage` or `verify-ac-subsection-coverage`** — their predicates, their exit codes and their tests are untouched.
- **No change to any other command's helper.** The four fixes are `_specify/` only, and nothing here touches `_research/`, `_shared/text_overlap.py` or the hypothesis-suppression gate.
- **No re-tuning of `NUMERIC_DIGIT_NOUN_RE`** — D1's rejected option (b).
- **No `disable-model-invocation` change** and no change to which commands the model may invoke.
- **No constitution edit** and no `src/CLAUDE.md` edit.
- **Anything specific to the benchmark**, and any client, install, repo, branch or benchmark path in this repo.

---

## Context for next session

⚠ **Evidence class, repeated: ONE observed consumer incident (a benchmark install; evidence held outside this repo), plus grep-verified structural facts. D3's false-sentence cluster and D4 are PREDICTED — found by reading, never observed — and nothing was measured.** ⚠ All line digits drift — **grep the quoted text, never the digits.**

**The one sentence that governs everything here:** a spec author must be able to fix one acceptance criterion without throwing the spec away, and a check that cannot tell correct text from incorrect text must not be the thing that forces them to.

### Honest bounds

- **D1 removes a block and adds nothing mechanical in its place.** A spec carrying two contradictory numbers can be approved. The only carrier is a warning the model is instructed to surface as prose, which nothing checks — the same bound the two sibling checks in Step 4.9 already carry (F14).
- **The approval summary renders counts, not AC text** (F15). No change here makes a number inside an AC statement visible in that block.
- **D2 covers one section of six.** A user who names a constraint, risk, out-of-scope item or affected area at `request-changes` still pays the full reset (F9, F13).
- **D4 fixes a latent path.** Nothing has reached it; it is fixed because D2 makes it reachable (F8).
- **Nothing here verifies that a revised AC is BETTER** — `revise-ac` re-applies the same EARS regex `add-ac` applies, and that regex is a shape check, not a meaning check.
- **`verify-ac-shape` remains a pure backstop** (F11). This plan does not change that, and does not claim the backstop is reachable.
- **The distinction from the Hypothesis-Suppression Precision Plan is reasoning, not measurement.** Neither plan measures its gate's false-positive rate. If Test 1 or Test 2 is wrong, this plan is the one that is wrong.

### Traps

**Trap 1 — reading the demotion as a predicate fix.** D1 leaves `NUMERIC_DIGIT_NOUN_RE` byte-identical, deliberately. The false positives still fire; they just stop blocking. Anyone who "improves" the regex during Phase 1 has taken D1's rejected option (b) without ratification.

**Trap 2 — shipping Phase 1 without Phase 3.** D1 has two halves. Exit 0 alone converts a false-positive block into a silent miss, which is strictly worse than today. **Phase 3 is load-bearing for D1.**

**Trap 3 — reading this plan and the Hypothesis-Suppression Precision Plan as contradicting each other.** They take opposite stances on one question class, and `## Coordination with the Hypothesis-Suppression Precision Plan` states the two tests that separate them — a repairable predicate, and a downstream human gate. If those tests are wrong, this plan is wrong, not that one.

**Trap 4 — adding a delete verb because revision felt incomplete.** `verify-coverage` checks only `landed_in`, never whether `landed_ref` resolves (F10), so a deletion strands findings past the gate silently. This is a non-goal for a mechanical reason, not a scope preference.

**Trap 5 — treating `import-handoff`'s pre-seed as evidence that list sections are editable.** It REPLACES four lists wholesale at Phase 0.4 (F5). That is not a per-entry edit and it is not reachable from Phase 4 or Phase 5.

**Trap 6 — rejecting a non-numeric `ac_id` during D4's scan.** `--ac-id AC-X` is accepted today and a test pins it (F8). The scan skips what it cannot parse.

**Trap 7 — a duplicate check that writes before it fails.** The module's own rule is that no partial write is structurally possible: pre-validate on a read-only load, then open the transaction (F5, F6).

**Trap 8 — writing Phase 3 before Phases 1 and 2.** Three of D3's six claims have different true forms depending on what shipped.

**Trap 9 — quoting a `file:line` from this plan as current.** Every digit here was true on 2026-09-20 and drifts on the next edit to those files.

**Trap 10 — a clobbered ledger edit.** The Hypothesis-Suppression Precision Plan edits the same three ledger surfaces, **two of which now sit inside `PLAN-STATUS-ARCHIVE.md`** — so one stale read of that file risks both. Ledger-adjacent files are already modified in this tree. Re-read `git status`, read each ledger live, commit by explicit path.

**Trap 11 — reading a predicted gap as observed.** One incident stands behind D1 and the recovery cost. D3's cluster and D4 stand behind nothing but a reading of the code.

### File anchors

- `src/commands/specify/main.md` — Step 4.4 (`add-ac`), Step 4.9 (the four-verb block, the `verify-ac-shape` bullet, the `verify-numerical-consistency` bullet, and the two non-blocking precedents), Step 4.11 (render + save), Step 5.1 (the approval summary paragraph), Step 5.2 (the constitution re-run), Step 5.3 (the approval prompt and `request-changes`), IMPORTANT RULES items 8 and 11.
- `src/devforge/lib/_specify/_cmds_phase4_verify.py` — `cmd_verify_coverage`, `cmd_verify_ac_subsection_coverage`, `cmd_verify_ac_shape`, `cmd_verify_numerical_consistency`, `cmd_render`.
- `src/devforge/lib/_specify/_cmds_phase4_setters.py` — `_flip_findings`, the six append-only setters, `_next_ac_id`, `cmd_add_ac`, `cmd_set_finding_landed`.
- `src/devforge/lib/_specify/_schema.py` — `EARS_VARIANT_ENUM`, `EARS_REGEX`, the three `NUMERIC_*` patterns.
- `src/devforge/lib/_specify/_cli.py` — the `add-ac` subparser (and `--ac-id`), the `verify-numerical-consistency` subparser.
- `src/devforge/lib/_specify/_render.py` — `_render_section_acs`, `_approval_summary`.
- `tests/lib/test_specify_helper.py` — `TestPhase4VerifyNumericalConsistency`, `TestPhase4VerifyAcShape`, `test_auto_assigns_ac_ids`, `test_accepts_explicit_ac_id`, the two `test_state_satisfies_phase_gates` fixtures.
- Read-only here: `src/CLAUDE.md`, `src/constitution.md`, `src/devforge/storage-rules.md`, and the Hypothesis-Suppression Precision Plan (`105-HYPOTHESIS-SUPPRESSION-PRECISION-PLAN.md` as of 2026-09-20).

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation. Then read the Hypothesis-Suppression Precision Plan's D6 (`105-HYPOTHESIS-SUPPRESSION-PRECISION-PLAN.md` as of 2026-09-20) and this plan's `## Coordination with the Hypothesis-Suppression Precision Plan` together; they are the two halves of one question. ⚠ **That plan's filename has already changed more than once** — it was `103-` while this plan was being drafted — so if the path above does not resolve, find it by its TITLE (`grep -l "Hypothesis-Suppression Precision Plan" *.md`), never by assuming a number.
2. **Check `## Phase 0 close record` first.** While it reads *PENDING*, nothing is ratified and **no build phase may start.**
3. **Re-verify F1–F15 against the live tree.** Grep the quoted text, never the digits: `NUMERIC_DIGIT_NOUN_RE`, `Variance rule #6`, `re-add with the same`, `setters mutate in place`, `blocks the render until reconciled`, `a Phase 4 verifier loop revised an AC`, `resolve by editing the source values`, `Surface any warning text`, `_next_ac_id`, `--ac-id`, `test_fails_on_inconsistent_render`, `test_accepts_explicit_ac_id`, `test_fails_when_state_corrupted`. ⚠ After a build phase some of these strings are gone by design; zero hits for them is then the built state, not a regression.
4. **Build order:** Phase 1 and Phase 2 are independent; Phase 3 needs both; Phase 4 runs last because it records what the earlier phases did. **Never stop after Phase 1** (Trap 2).
5. **Route every edit through the house flow:**
   - python-engineer → python-reviewer for every Python edit, with a test per function, run in the same turn;
   - instruction-author → instruction-reviewer for every markdown edit;
   - `claude-code-guide` for every new Claude-Code-integration fact.
6. **Commit by explicit path, never `git add -A`.** Re-read `git status` first, and read the three shared ledger surfaces live (`## Coordination with the Hypothesis-Suppression Precision Plan`).
7. **After each phase, cross-check.** Grep every verb, flag and rule number touched — `verify-numerical-consistency`, `revise-ac`, `--ac-id`, `_next_ac_id`, `IMPORTANT RULES` item 8 — and fix any dangling reference in the SAME change.
8. **Run Phase 4, then leave Phase 5 to the maintainer.**
9. **Keep the evidence class attached.** Any summary of this plan repeats it: ONE observed consumer incident for the gate and the recovery cost; D3's cluster and D4 predicted, found by reading; nothing measured.
