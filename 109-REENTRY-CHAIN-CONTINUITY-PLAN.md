# 109 — Re-entry Chain Continuity Plan

**Created**: 2026-09-21
**Status**: **Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start.** Every decision (D1–D5) and every open question (OQ-1–OQ-6) carries a recommendation and its strongest counter-argument, and each waits for the maintainer. **Phase 6 is a user-driven consumer e2e HARD GATE that has not run**; when this plan is later closed on its build, "done" will mean BUILT and build-verified and NEVER that Phase 6 passed. ⚠ **Numbered 109 because 101, 102, 104, 105, 106, 107 and 108 are taken in this checkout as of 2026-09-21 and 103 was vacated by a renumbering — the gap at 103 is not a missing plan.**

The backward re-entry chain `/devforge:grill → /devforge:research → /devforge:specify` takes exactly one step back and stops. `/devforge:grill` writes a research-targeted re-entry seed; `/devforge:research` consumes it in attach mode and corrects the investigation in place; and then `/devforge:specify`'s mandatory pending gate refuses the feature directory forever, because `spec.md` exists there and no seed in it targets the spec stage. The corrected research sits beside a `spec.md` that contradicts it, and no supported route updates that spec. **The proposal is one new pending arm keyed on a self-clearing marker the intake re-run writes, plus the stderr wording repair the same gate needs anyway.** Nothing is being built. This plan exists to be argued and ratified first.

---

## Origin & evidence

⚠ **Evidence class, to be repeated in every summary of this plan: ONE observed consumer incident, reported by a peer session against a frozen benchmark install running 2.0.12-era code, whose artifacts are NOT in this repo and were NOT inspected here. Every structural fact below was independently re-derived by READING this tree on 2026-09-21. NOTHING WAS MEASURED, and no fixture reproduction of the dead-end exists yet — building one is Phase 1's first job.** A clean Phase 6 would show the new arm behaves on planted fixtures; it would never show how often the dead-end is reached or what it costs.

This repo is public. **This plan names no client, no install, no repo, no branch, no ticket id and no session identifier**, and no phase of it may introduce one.

### The dead-end, derived from the tree

Each link is F-cited below. Nothing in this chain is a relayed claim; each step was re-read on 2026-09-21.

1. **`/devforge:grill` reaches a RE-ENTER-UPSTREAM disposition targeting research** and, on the matching user pick, writes `<feature_dir>/grill-seed.json` with `target_stage: "research"` (F5). `"research"` is a valid value (F4).
2. **`/devforge:research` Phase 0.6 consumes that seed in ATTACH MODE** — it reuses the seed's reported `feature_dir`, skips branch creation, and Phase 4 overwrites `research-report.md`, `research-handoff.json` and (when present) `emission-matrix.md` in place (F6). It does not touch the seed, by explicit instruction (F6). `/devforge:discover` carries the mirrored block for the `discovery` lane (F7).
3. **`/devforge:specify` Phase 0.4's `find-handoffs --require` gate then blocks forever.** `spec.md` exists in that dir, so arm (a) fails; the only seed there still says `target_stage: "research"`, so arm (b) fails (F1, F2). Exit 2, and the gate is documented as mandatory with no override and **no cold-spec escape hatch** (F8).
4. **Re-running `/devforge:research` changes nothing.** Attach mode rewrites the same handoff in the same directory, where `spec.md` still exists and the seed is still research-targeted (F6). The predicate's inputs are unchanged, so the gate's answer is unchanged.

**Consequence.** The return chain moves one stage upstream and stops. The live `spec.md` contradicts the corrected research, and every exit left to the user is unsupported: hand-deleting `spec.md` to re-open arm (a); running `/devforge:spec-check` and hoping for a REVISE-SPEC verdict, which would write a spec-targeted seed; or re-running `/devforge:grill` and hoping this time the disposition points at the spec stage. **None of those is a documented route, and two of them are gambles on a verdict the user does not control.**

**Why this is unowned.** `68-INTAKE-OWNS-FEATURE-DIR-PLAN.md`'s amendment **D10** (`### D10 — Re-entry seeds keep the gate passable (amendment, ratified in-session 2026-08-06)`) introduced arm (b) precisely to make `/devforge:grill → /devforge:specify` re-entry reachable, and it reasoned only about a seed whose `target_stage` is `"spec"` — its own wording is *"a sibling `*-seed.json` carries `target_stage: \"spec\"`"*. **A chain with an INTERMEDIATE stage was never considered.** Separately, `106-INTAKE-PROVENANCE-CONTINUITY-PLAN.md`'s finding **F6** names the very same two-arm predicate, but for a different scenario — a mid-run `reset-state` after `spec.md` was written — and that plan is Phase 0 OPEN and lists `_cmds_handoff.py` under its read-only anchors. **It does not own this defect and will not collide with it** (F15).

### Correction to the original report

**Correction 1 — the `find-handoffs --require` stderr does NOT blame a missing handoff.** The reporter claimed it did. Its BODY names both arms explicitly (F9). **Only the HEADLINE line reads as if the handoff were absent.** This is a cosmetic wording defect that makes the block harder to diagnose; **it is NOT a cause of the block, and no phase of this plan may describe it as one.** It is bundled as D5 because the same gate is being edited anyway, not because it contributes to the dead-end.

### Verified structure (2026-09-21)

Every fact below was read against this tree on 2026-09-21. ⚠ **Line digits drift — grep the quoted text, never the digits.**

**F1 — The pending predicate has exactly two arms, and the loop applies it in four steps.** `src/devforge/lib/_specify/_cmds_handoff.py`, `cmd_find_handoffs` (`def cmd_find_handoffs` at `:1078`). Its docstring states the predicate: an intake handoff is present **AND EITHER** *"(a) spec.md is absent"* **OR** *"(b) spec.md IS present but a sibling \*-seed.json file has target_stage == \"spec\""*. The loop that applies it (`:1149`–`:1157`) reads `for feature_dir in iter_feature_dirs(specs_root):`, then `if (feature_dir / "spec.md").exists():` (`:1151`), then `reentry = _has_spec_reentry_seed(feature_dir)` (`:1154`), then a TWO-line guard — `if not reentry:` (`:1155`) with an indented `continue` on its own line (`:1156`). **A dir whose `spec.md` exists and whose seeds target another stage is `continue`d before either handoff file is even looked at.**

**F2 — `_has_spec_reentry_seed` matches one literal and nothing else.** `def _has_spec_reentry_seed(feature_dir: Path) -> bool:` (`:964`), docstring *"True iff feature_dir contains a \*-seed.json whose target_stage is \"spec\""*. It globs `*-seed.json` in that ONE directory and returns True only for `raw.get("target_stage") == "spec"`. Its docstring already records the deliberate tolerances: it matches on that field only, does not reconstruct a `ReEntrySeed`, and treats a corrupt/unreadable/non-dict seed as *"not a match"* rather than raising. **A research-targeted seed is, to this function, indistinguishable from no seed at all.**

**F3 — The output format is a five-field line plus an OPTIONAL sixth, and the sixth is contractually an extension.** Same docstring: `<mtime ISO> | <handoff_path> | kind=<research|discover> | <mode_or_verdict> | <summary>[ | re-entry]`, with the note *"This is a deliberate backward-compatible extension, not a reformat of the existing 5 fields"* and *"a caller that splits on \" | \" and reads only the first 5 fields … sees byte-identical output to before D10"*. The emitting code appends `" | re-entry"` only when `h.get("reentry")`. **Load-bearing for OQ-5: whatever arm (c) emits, the first five fields stay byte-identical.**

**F4 — `"research"` and `"discovery"` are valid seed targets.** `src/devforge/lib/_shared/seed_schema.py`: `SEED_TARGET_STAGES = ("spec", "discovery", "research", "plan")`, enforced by `_require_in_enum(self.target_stage, SEED_TARGET_STAGES, "ReEntrySeed.target_stage")`. **The seed in the dead-end is well-formed and correct. Nothing is broken about it.**

**F5 — `/devforge:grill` writes ONE seed, at ONE fixed filename.** `src/commands/grill/main.md`, the *"Seed-write + commit block (7.2's matching re-entry arms only)"*: `grill_helper write-seed --feature <feature_dir> --target-stage <stage> …`, described as *"builds a `ReEntrySeed` … and writes `<feature_dir>/grill-seed.json` via an atomic write"*. `<stage>` is *"`plan` for a matching Revise plan, or the PHASE-5 nearest upstream stage (`spec` | `discovery` | `research`) for RE-ENTER-UPSTREAM"*. **One filename, one seed per feature dir — load-bearing for D2's third rejected alternative.**

**F6 — `/devforge:research` attach mode reuses the dir, and the block is forbidden from touching the seed.** `src/commands/research/main.md`, `### Phase 0.6 — Re-entry from /devforge:grill (conditional — skip if no seed)`. Its `**Attach mode (binds Phase 4).**` paragraph: *"on save, Phase 4 reuses it instead of allocating a new one, skips branch creation, and overwrites the artifacts in place."* The prohibition, verbatim: *"This block only READS the seed's directive. It does NOT delete the seed or change its `cycle_count` — seed lifecycle (deleting or incrementing `cycle_count` after consumption) is handled by the next `/devforge:grill` run, which reads `carried_findings` to stay monotonic. That is a v1 simplification; do not add seed-deletion logic here."* ⚠ **The enumerated examples are deletion and `cycle_count`; the governing sentence is the flat "This block only READS the seed's directive."**

**F7 — `/devforge:discover` carries the mirror, word for word on the prohibition.** `src/commands/discover/main.md`'s Phase 0.6 equivalent matches `target_stage == "discovery"`, carries an `**Attach mode — the feature directory already exists.**` paragraph stating that *"Phase 4's save flow SKIPS allocation and SKIPS branch creation, and overwrites the discovery report + handoff in place"*, and carries the identical *"This block only READS the seed's directive…"* paragraph. **The defect is identical on both intake lanes, and every phase of this plan treats them as one surface.**

**F8 — The Phase 0.4 gate is documented as unbypassable.** `src/commands/specify/main.md`, `### Phase 0.4 — Pending-feature-dir resolution`: *"**This gate is mandatory, with no override.**"*, *"the precondition is unbypassable — there is NO cold-spec escape hatch, even for a feature the user researched externally"*, and on exit 2 *"Do NOT proceed to Phase 1 and do NOT offer a cold-start alternative — there is no override."* **This is correct and this plan does not weaken it: a third arm still requires an intake handoff AND a machine-written marker; it adds no user-supplied bypass.**

**F9 — The stderr body names both arms; only the headline misleads.** `cmd_find_handoffs`'s `--require` branch writes, in order: `"BLOCKED: /devforge:specify requires a pending research or discover handoff.\n"`, then *"No feature dir under specs/ carries an intake handoff … that is pending -- either its spec.md does not yet exist, or (re-entry) a sibling \*-seed.json targets this stage (target_stage == \"spec\")."*, then the two recovery commands. **The body is accurate today. The headline says "requires a pending … handoff" in a way that reads as "you have no handoff", which is false in exactly the case this plan is about** (Correction 1, and D5).

**F10 — The spec-hash self-clearing shape is ALREADY the house pattern, in this same pipeline.** `src/devforge/lib/plan_helper.py`, the `verify-spec-check --spec <spec-path>` docstring: *"Freshness = content hash: re-hashes the current spec.md (sha256 of its raw bytes) and compares against the sibling report's \"**Spec hash**:\" header line"*, with exit-2 arm (d) *"the report's recorded hash does not match the current spec.md (the spec changed after the check ran)"*. It also records its own lineage: *"Modeled on specify_helper's `find-handoffs --require` gate"*. **D3 is consistency with an established in-repo pattern applied to the same two verbs, not an invention.**

**F11 — Three separate globs would pick up any new file named `*-seed.json`.** (i) `_has_spec_reentry_seed`'s own `feature_dir.glob("*-seed.json")` (F2). (ii) `src/commands/specify/main.md` Phase 0.5: *"glob `<feature_dir>/*-seed.json` — the feature dir resolved in Phase 0.4, and ONLY that dir"*. (iii) `src/commands/plan/main.md`: `.devforge/lib/artifact_helper find-feature-artifacts --filenames '["*-seed.json"]'` — **project-wide, not dir-scoped.** ⚠ **Load-bearing for OQ-1: the marker's filename MUST NOT end in `-seed.json`.**

**F12 — `_shared/` is the ratified home for a capability two intake helpers both need, and `artifact_helper` is deliberately seed-blind.** `68-INTAKE-OWNS-FEATURE-DIR-PLAN.md` **OQ-1** resolved the same shape for the allocation substrate: *"**Recommend the shared module**: relocate `_next_spec_number` into `src/devforge/lib/_shared/` and expose thin verbs from `research_helper` / `discover_helper` / `specify_helper` over the one implementation"*, because *"A cross-helper shell-out would make one command's helper a runtime dependency of another's, which nothing in the framework does today."* The standing examples exist on disk: `src/devforge/lib/_shared/feature_scope.py`, `_shared/seed_schema.py`, `_shared/feature_alloc.py`. **Against that, `artifact_helper`'s seed-blindness is a property its own callers rely on in writing:** `src/commands/research/main.md` says of `find-feature-artifacts` that *"the verb above matches filenames across feature directories without ever opening a seed or knowing what one means"*, and concludes *"so it stays valid even if `/devforge:grill` is ever removed."* **Load-bearing for D4's explicit rejection.**

**F13 — Step 4.6's commit already has the conditional-paths shape the marker would join.** `src/commands/research/main.md`, `### Step 4.6 — Write the handoff, then commit`: `research_helper finalize-handoff --feature-dir "<feature_dir>"`, then *"`--paths` carries the report and the handoff, plus `<feature_dir>/probe-script.<ext>` when Step 4.5 copied one and `<feature_dir>/emission-matrix.md` when Step 4.5b wrote one; the two extras are independent — either, both, or neither may be present."* The fenced block carries per-element comments naming each conditional. **Load-bearing for OQ-3: a third conditional element is an existing pattern in that exact list, not a new one.**

**F14 — The hygiene token list is ratified and closed by its own rule.** `src/devforge/lib/_verify/_hygiene.py`'s module docstring: *"The check is a ratified TOKEN list, never a stem match"* and *"Every token below is fixed; regexes may be refined for correctness but no token may be added or removed without a fresh ratification."* The filename/path token list it enumerates ends with `` `fix-seed` `` and `` `grill-seed` ``, and the corresponding regexes exist in the module's pattern list as `r"(?<![\w-])fix-seed(?![\w-])"` and `r"(?<![\w-])grill-seed(?![\w-])"`. **Load-bearing for OQ-2: adding the marker's token is a RATIFICATION question for the maintainer, never a build decision a phase may take on its own.**

**F15 — Concurrency, and the neighbouring open plans.** Other sessions are building in this checkout. As of 2026-09-21 the repo root carries the whole 101–108 neighbourhood, and the two states in it are NOT the same state. **Untracked and in flight — `git status` shows each as `??`:** `101-NON-WEB-STACK-READINESS-PLAN.md`, `102-SPECIFY-IN-PLACE-REVISION-PLAN.md`, `104-UNIVERSAL-SECTIONS-INTEGRITY-PLAN.md`, `105-HYPOTHESIS-SUPPRESSION-PRECISION-PLAN.md`, `106-INTAKE-PROVENANCE-CONTINUITY-PLAN.md` and `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`. **Present but NOT in flight:** `107-SURFACE-PATH-PROOF-PLAN.md` is on disk and appears in NO `git status` line at all — tracked and unmodified, **not uncommitted work.** (103 is absent by the renumbering this plan's `**Status**:` line records; untracked plan files outside the 101–108 band also sit at the root and are not enumerated here.) Separately, `CHANGELOG.md`, `VERSION`, `README.md`, `DEVELOPMENT-STATUS.md`, `FINDINGS.md`, `src/CLAUDE.md`, `src/manifest.json` and `src/commands/summarize/main.md` were modified and uncommitted by other work when this plan was drafted — **re-derive both lists from `git status` rather than trusting them here.** Before touching any shared file: re-read `git status`, read the live file, commit by explicit path, never `git add -A`, and **never touch another session's plan file.**

**F16 — The "only READS the seed's directive" prohibition has FOUR sites in THREE wordings, and only ONE pair of them is word for word.** Verified 2026-09-21 by an unfiltered `grep -rn "This block only READS" src/`, which returns four hits and no others:
- `src/commands/research/main.md` **Phase 0.6** (`:201`) and `src/commands/discover/main.md` **Phase 0.6** (`:190`) — **byte-identical to each other**, both naming *"the next `/devforge:grill` run, which reads `carried_findings` to stay monotonic"* as the lifecycle owner (F6, F7).
- `src/commands/specify/main.md` **Phase 0.5** (`:156`) — its OWN wording: *"It does not delete the seed or mutate its `cycle_count` — that lifecycle management, whatever form it takes, is the emitting command's responsibility, not this consumer's."* ⚠ **Phase 0.5 is a section Phase 4 EDITS**, so this is the copy most at risk of being reflowed or clipped by this plan's own work.
- `src/commands/plan/main.md` **PHASE 0a.7** (`:127`) — its own wording again, with the lifecycle clause folded into parentheses. ⚠ **READ-ONLY — no phase of this plan edits `plan/main.md`**; it is named here so the four-file grep is not misread as putting it in scope.

⚠ **Load-bearing for Phase 4's Verify, and the reason that Verify is worded the way it is:** each occurrence is compared PER FILE against that file's own text. **Cross-file byte-identity holds for the research/discover pair ONLY** — an assertion that four identical strings exist is FALSE and would fail against a tree that is perfectly correct.

---

## Coordination with the neighbouring open plans

⚠ **Sibling plans are referenced by TITLE throughout this plan, because plan numbers in this checkout have already moved** — `106-INTAKE-PROVENANCE-CONTINUITY-PLAN.md` records that the Specify In-Place Revision Plan was briefly 103 and that the Hypothesis-Suppression Precision Plan moved 102 → 103 → 105. **If a filename given here does not resolve, find the plan by its title — `grep -l "Intake Provenance Continuity Plan" *.md`, `grep -l "Specify In-Place Revision Plan" *.md` — never by assuming a number.**

**Both neighbours are Phase 0 OPEN, and both edit `src/commands/specify/main.md`.** Verified 2026-09-21 from each plan's own `**Status**:` line and its own scope statements.

- **The Specify In-Place Revision Plan** — its Status line reads *"Phase 0 OPEN — nothing is ratified, no close record exists, and no build phase may start."* It states *"This plan edits `src/devforge/lib/_specify/` and `src/commands/specify/main.md`"*, and its own file-anchor list names **Step 4.4, Step 4.9, Step 4.11, Step 5.1, Step 5.2, Step 5.3, and IMPORTANT RULES items 8 and 11** — the verify/AC verbs and its false-sentence cluster. **It names Phase 0.4 nowhere as an edit target** (its two Phase-0.4 mentions are a read-only fact about `import-handoff`'s pre-seed and a trap warning against misreading it), and **it names `cmd_find_handoffs` and `find-handoffs` nowhere at all.**
- **The Intake Provenance Continuity Plan** — its scope in `src/commands/specify/main.md` is *"Phase 0.4 (D1's re-bind route) and Phase 3 Step 1 (D3's call site)"*, with a placement fork that may instead lodge its block near Phase 0.3's `reset-state` call; it also edits `src/commands/plan/main.md` PHASE 0a.5. **It touches the ARMS' surrounding prose at most, never the pending PREDICATE**, and its own `### File anchors` section lists `src/devforge/lib/_specify/_cmds_handoff.py` under *"**Read-only here** — **no phase of this plan writes any of these**"*, naming `cmd_find_handoffs` explicitly. **Its non-goals say so a second time: *"No change to `find-handoffs`'s pending predicate — F6 is a fact this plan routes AROUND, not one it changes."*** ⚠ **Vocabulary collision, named here so it cannot be misread later:** that plan says *"three arms"* in its **F4** (*"Phase 0.4 has three arms"*) and in its **D1** placement fork (*"Inside Phase 0.4, after the three arms"*), and in both places it means Phase 0.4's `AskUserQuestion` options `yes-most-recent` / `pick-other` / `cold` — **not** this plan's pending-predicate arms (a) / (b) / (c). **Once this plan lands its arm (c), Phase 0.4 carries BOTH a three-way picker AND a three-arm predicate**, so whoever implements that plan's placement fork afterwards must read *"after the three arms"* as a position after the picker's arms and NEVER as a position relative to arm (c). **This plan renames nothing there and edits no line of that file** — the disambiguation is this sentence and nothing else.

### Shared surfaces, and the rule that binds

- **`src/commands/specify/main.md` — all three plans edit this file, in DIFFERENT regions.** This plan's region is **Phase 0.4's pending-predicate prose (arms and the gate's arm-counting sentences) and one sentence in Phase 0.5**. ⚠ **If the Intake Provenance Continuity Plan lands its re-bind block inside Phase 0.4, the two edits sit in the same phase and must be reconciled by whoever ships second — they are not in conflict, but they are adjacent.**
- **`src/devforge/lib/_specify/_cmds_handoff.py` — this plan is the ONLY one of the three that writes it.** Both neighbours read it; neither edits it. ⚠ **If either neighbour's scope later expands to this module, this line stops being true — re-derive it from their live text, not from here.**
- **`src/commands/research/main.md` and `src/commands/discover/main.md`** — neither neighbour names either file in its scope as of 2026-09-21. **This plan writes both.**
- **`src/commands/plan/main.md` — a neighbour edits it; this plan only GREPS it.** The Intake Provenance Continuity Plan names PHASE 0a.5 in its scope; this plan's Phase 4 Verify reads that file's PHASE 0a.7 "only READS the seed's directive" line (F16) and **no phase of this plan edits the file at all.** ⚠ **A `plan/main.md` diff produced by that neighbour does not violate this plan's Verify** — the Verify is scoped to the lines THIS phase's own diff touches, which is none of them.
- **`CHANGELOG.md`, `CLAUDE.md`'s router table, `src/devforge/storage-rules.md`, `PLAN-STATUS-ARCHIVE.md`** — ledger surfaces this plan's docs phase writes. ⚠ **`PLAN-STATUS-ARCHIVE.md` is the most shared of the four** — every session that changes any plan's status amends it — **so it is re-read LIVE and amended by NAMED LINE only**, per Phase 5. ⚠ **The Intake Provenance Continuity Plan records that `CHANGELOG.md` had no `## [Unreleased]` section on 2026-09-20 and that the Specify In-Place Revision Plan's OQ-4 creates one.** Re-derive the live state; do not trust either statement at build time.
- **The rule that binds, in one sentence: whoever lands first, the next re-reads LIVE.** Every shared surface is read at build time and every edit is re-derived from what is actually there — never from a pre-computed diff, never from a sibling plan's site list. **The rule binds the READ, not the edit.**
- ⚠ **A neighbouring plan's `git diff --stat` Verify line is not a rule this plan violates.** The Specify In-Place Revision Plan's Phase 3 Verify reads *"`git diff --stat src/commands/` lists `specify/main.md` and nothing else"*; this plan's instruction phase lists three command files. **Neither builder may read the other's committed work as a defect.**
- ⚠ **Finished plans and `PLAN-STATUS-ARCHIVE.md` are historical records and are NOT rewritten by this plan** — with **two bounded exceptions, both named in Phase 5, both ADDITIVE, and both about the same plan**: a back-reference ADDED under `68-INTAKE-OWNS-FEATURE-DIR-PLAN.md`'s D10, and the matching amendment to the TWO lines `PLAN-STATUS-ARCHIVE.md` devotes to that same plan — its `## Index` line and its `## Entries` record, which restate D10's two-arm predicate independently of the plan document and are therefore not reached by editing the plan document alone. **Neither exception rewrites D10's ratified wording, and no other plan's record in that file is touched** — see Phase 5's Verify for why a phrase-keyed sweep of that file is forbidden.

---

## Phase 0 — ratification

Nothing below is ratified. Each item states the decision, its options where they exist, a recommendation, and the strongest counter-argument, **recorded honestly rather than answered away**. **Every helper verb name, flag, filename and output token this section proposes is PROPOSED and UNRATIFIED**; no phase may quote one until Phase 0's close record fixes it. Proposed emitted wording is **substance, not final text**: the builder may reword, but every element named must survive. **No emitted sentence may name plan vocabulary** ("D3", "plan 109", "Phase 0"); real headings such as `Phase 0.4` are fine.

### D1 — Name the defect class: there is no record of downstream staleness

**The framing, recommended.** The gap is that **an upstream stage re-ran over a feature whose downstream artifacts already exist, and nothing records that those artifacts are now stale.** The seed routed correctly, the intake re-ran correctly, and the artifacts it produced are correct. What is missing is any durable statement that `spec.md` is now behind the handoff sitting beside it.

**Counter-argument, recorded and not answered away.** The narrower framing — *"the seed points at the wrong stage"* — yields a one-line fix, and a broader framing risks scope creep into `plan.md` and breakdown staleness that nobody asked for. **That risk is real and this plan bounds it explicitly in `## Non-goals`: the downstream chain past `spec.md` is verified to recover on its own and is out of scope.**

**Rebuttal.** D2's three rejected alternatives are exactly the narrow fixes, and **each fails for a reason that only the broader framing exposes** — one lies to a downstream consumer about what a field means, one opens the gate before the demanded re-run has happened, and one binds `/devforge:specify` to a directive written before the evidence existed. A framing that cannot see those three failures is not a cheaper framing; it is a framing that ships one of them.

**RECOMMEND D1 as stated.**

### D2 — The fix: a THIRD pending arm in `find-handoffs`, keyed on an intake-rerun marker

**The proposal.** `cmd_find_handoffs`'s predicate gains arm **(c)**: an intake handoff is present, `spec.md` exists, and a sibling marker file records that an intake stage re-ran over this feature AFTER that `spec.md` was written. Arms (a) and (b) are untouched. The marker's clearing rule is D3; its producer is D4; its filename is OQ-1.

**RECOMMEND D2.** The three alternatives below were considered and are rejected, each for a reason that is structural rather than aesthetic.

**Rejected alternative 1 — retarget the seed to `"spec"` after `/devforge:research` consumes it.** This was the reporter's own proposal. **REJECT on two independent grounds.**
- **(i) Semantics.** `src/commands/specify/main.md` Phase 0.5 documents the seed field as *"`prior_conclusion` — what the previous spec concluded; it was invalidated, so do NOT re-derive it."* A seed authored by `/devforge:grill` for the research stage carries a RESEARCH conclusion in that field (`src/commands/research/main.md`: *"`prior_conclusion` — what the previous research investigation concluded"*). **Retargeting it would put a research conclusion where the spec consumer is told to read a spec conclusion — the directive would lie to its consumer.**
- **(ii) Lifecycle.** It is the CONSUMER mutating the PRODUCER's record, which both intake specs forbid in terms: *"This block only READS the seed's directive"* (F6, F7). ⚠ **Those sentences enumerate deletion and `cycle_count`; the flat "only READS" is the governing clause, and a retarget breaks it.**

**Rejected alternative 2 — broaden arm (b) to admit `target_stage in {"spec", "research", "discovery"}`, excluding `"plan"` as downstream of spec.** **REJECT — and concede plainly that this option is genuinely cheap and that its stage-ordering logic is sound.** It is a few characters in `_has_spec_reentry_seed`, it needs no new file, no new producer and no new helper verb, and the exclusion of `"plan"` is correct reasoning about the pipeline's direction. **It fails on timing, not on logic:** the seed is written by `/devforge:grill` **BEFORE** the demanded research re-run happens (F5). Broadening arm (b) therefore opens the `/devforge:specify` gate the instant the grill verdict lands — **so a user could skip `/devforge:research` entirely and re-spec straight off the STALE handoff, which is the opposite of what the grill asked for.**

**Rejected alternative 3 — have `/devforge:grill` write a second, spec-targeted seed at the same time.** **REJECT.** It binds `/devforge:specify` to a directive authored before the research re-run had a chance to confirm or refute the prior conclusion — the new spec would be directed by a guess about what the corrected research would say. **There is also a mechanical snag worth recording:** `grill_helper write-seed` writes to the single fixed filename `<feature_dir>/grill-seed.json` (F5), so both seeds would want the same name.

**Counter-argument to D2 itself, recorded and NOT answered:** D2 is the most expensive of the four options — a new artifact, a new producer on two helpers, a new predicate arm, and a new output token. **The three cheaper options are cheaper because each one is wrong in a way that only shows up one command later.** That is an argument for D2, not a denial of its cost; the cost is real and the maintainer is the one who decides whether the chain is worth it.

### D3 — The marker is SELF-CLEARING by spec-hash comparison, and is never deleted

**The mechanism.** The marker records the `sha256` of `spec.md` **as it stood at the moment of the attach-mode intake re-run**. Arm (c) admits the dir **while the recorded hash still EQUALS the current `sha256(spec.md)`** — that is, while the spec has not been re-rendered since. Once `/devforge:specify` re-renders `spec.md`, the two diverge and the dir stops being pending on its own.

**Consequences, stated plainly because each one removes work:**
- **`/devforge:specify` needs NO clearing step.** Nothing is added to its flow.
- **No command deletes another command's artifact.** The marker's producer is the only writer; nobody is a deleter.
- **No already-committed file has to be un-committed.** The marker stays on disk and in git; it simply stops matching.

**PRECEDENT, cited.** `plan_helper`'s `verify-spec-check` gate is exactly this shape, on exactly these two files: *"re-hashes the current spec.md (sha256 of its raw bytes) and compares against the sibling report's \"**Spec hash**:\" header line"*, with the mismatch arm reading *"the spec changed after the check ran"* (F10). **This is consistency with an established in-repo pattern, not an invention.**

**Counter-argument, recorded honestly and NOT answered away:** **a hand edit to `spec.md` — even a whitespace change — moves the hash and silently closes arm (c) although no re-spec happened.** The user is then back in the dead-end with no signal. ⚠ **The same limitation already lives in the `/devforge:plan` gate this is modelled on** (a hand-edited spec fails `verify-spec-check` for the same reason), so this plan accepts a known, precedented weakness rather than inventing a stronger mechanism. **Say so; do not hide it.**

**A second bound, recorded for symmetry:** the hash comparison is byte equality, so **a `/devforge:specify` re-render that produces a byte-identical `spec.md` leaves arm (c) OPEN.** The dir stays pending and the gate offers it again. That outcome is benign — a re-runnable gate rather than a stuck one — but it means "self-clearing" is true of a changed spec, not of every re-spec. **Neither bound is a reason to reject D3; both are reasons not to describe it as airtight.**

### D4 — Producer placement: a `_shared/` module with thin verbs on both intake helpers

**The proposal.** The marker writer lives in `src/devforge/lib/_shared/` — one implementation — with **thin verbs exposed by `research_helper` and `discover_helper`** over it. The READ side is consumed by `src/devforge/lib/_specify/_cmds_handoff.py`.

**PRECEDENT, cited.** `68-INTAKE-OWNS-FEATURE-DIR-PLAN.md` **OQ-1** resolved exactly this shape for the allocation substrate, with the reason stated as *"A cross-helper shell-out would make one command's helper a runtime dependency of another's, which nothing in the framework does today."* The standing examples are on disk: `_shared/feature_scope.py`, `_shared/seed_schema.py`, `_shared/feature_alloc.py` (F12).

**EXPLICITLY REJECTED — putting it in `artifact_helper`.** `src/commands/research/main.md` praises that helper, in writing, for matching filenames *"without ever opening a seed or knowing what one means"*, and concludes that this is why the block *"stays valid even if `/devforge:grill` is ever removed"* (F12). **Teaching `artifact_helper` what a seed or a spec hash means would destroy the property its own spec relies on.** The marker's semantics belong in `_shared/`; `artifact_helper` keeps committing files it does not understand.

**The write site, and its two conditions.** The marker is written **ONLY in attach mode** and **ONLY when `spec.md` exists at that moment.** The site is `src/commands/research/main.md`'s `### Step 4.6 — Write the handoff, then commit` and its `src/commands/discover/main.md` counterpart — beside `finalize-handoff`, before the `commit-artifacts` call (F13). OQ-4 governs the no-`spec.md` case.

**Counter-argument, recorded:** a `_shared/` module plus two thin verbs is more surface than one verb on one helper, and only two callers will ever exist. **The rebuttal is that the second caller is the whole point** — F7 establishes that the discover lane has the identical defect, and a one-helper fix would repair one lane and leave the other dead-ended, which is how the framework accumulates asymmetries.

### D5 — Repair the `find-handoffs --require` stderr headline

**Bundled, small, and independently correct.** The BODY already names the arms (F9); the HEADLINE — `"BLOCKED: /devforge:specify requires a pending research or discover handoff."` — reads as if the handoff were absent, which is false in exactly the case this plan is about. **Two changes:** the headline stops implying absence and names PENDINGNESS as the failing condition; and the body names arm (c) once arm (c) exists.

⚠ **Bounded by Correction 1: the headline is a diagnosis cost, never a cause of the block.** No phase, ledger line or CHANGELOG entry may describe the wording as contributing to the dead-end.

**Counter-argument, recorded:** bundling a cosmetic wording fix into a structural change widens the diff and makes the change harder to review in isolation. **Accepted; the justification is that Phase 2 is already rewriting that exact string to name arm (c), so the alternative is editing one string twice.** If D2 is declined, **D5 is independently shippable and should be re-posed on its own.**

### OQ-1 — The marker's filename

**Hard constraint first: it MUST NOT end in `-seed.json`.** Three globs would otherwise pick it up (F11) — `_has_spec_reentry_seed`'s own dir glob, `/devforge:specify` Phase 0.5's same-dir glob, and `/devforge:plan`'s **project-wide** `find-feature-artifacts --filenames '["*-seed.json"]'`.
**RECOMMEND `intake-rerun.json`** — PROPOSED and unratified. ⚠ **Verified 2026-09-21: `grep -rn "intake-rerun" .` returns zero hits, so the name collides with nothing today.**
**When resolving, verify the non-match explicitly** rather than assuming it: the chosen name must not match `*-seed.json` under any of the three globs above.
**Alternatives:** any name outside that glob. ⚠ **Cheap to settle at ratification, expensive to change after three command files quote it.**

### OQ-2 — Does the new filename join the ratified hygiene token list?

`src/devforge/lib/_verify/_hygiene.py`'s docstring states the list is *"a ratified TOKEN list"* and that *"no token may be added or removed without a fresh ratification"*; `fix-seed` and `grill-seed` are already tokens (F14).
**RECOMMEND yes — add it, for consistency with the two seed tokens that already sit there.** ⚠ **This is a RATIFICATION question for the maintainer, not a build decision.** It needs its own explicit ratification line in the close record; **a phase may not add the token on the strength of this recommendation alone.**
**Alternative:** leave it out, accepting that a wrapper-mode source repo could carry the marker's filename without the hygiene check firing.

### OQ-3 — Does the marker travel in Step 4.6's `commit-artifacts --paths` list?

**RECOMMEND yes** — alongside `research-report.md` and `research-handoff.json`, **as a conditional element exactly like `probe-script.<ext>` and `emission-matrix.md` already are** (F13). The existing block already carries per-element comments naming each conditional, so a third joins a pattern rather than starting one.
**Alternative:** leave it uncommitted, which would make the marker's survival depend on the next command that happens to stage the directory.

### OQ-4 — What does the producer do when `spec.md` does NOT exist at attach time?

**RECOMMEND: write no marker at all.** Arm (a) already admits that dir (F1), so the gate is open without one, and a marker with no hash to compare would be inert at best.
**Alternative:** write a marker with a null/absent hash, which would need arm (c) to define what a hashless marker means — a second admission rule for a case arm (a) already covers.

### OQ-5 — Does arm (c) reuse the ` | re-entry` token or get its own?

**Hard constraint first:** whichever way this resolves, **the first five output fields stay byte-identical** — `cmd_find_handoffs`'s own contract calls the sixth field *"a deliberate backward-compatible extension, not a reformat of the existing 5 fields"* (F3).
**RECOMMEND a DISTINCT token**, so `/devforge:specify` Phase 0.4 can tell the two admissions apart: a **seed-admitted** dir means Phase 0.5 will find a directive, while a **marker-admitted** dir means Phase 0.5 correctly no-ops and the direction comes from the freshly re-run intake handoff instead. ⚠ **This plan proposes no literal spelling for that token** — fix it in the same ratification line as OQ-1's filename so the two cannot drift apart.
**Alternative:** reuse ` | re-entry`, which is cheaper in the helper and costs a discrimination the instruction then has to make some other way.

### OQ-6 — CHANGELOG landing, and back-porting into already-shipped installs

**Posed, not decided here** — this mirrors the pair the Intake Provenance Continuity Plan poses as its own OQ-3 and OQ-4.
- **CHANGELOG landing:** the entry goes in an `## [Unreleased]` section, **re-verified LIVE at build time**, never as an edit into a released version block. ⚠ **Whether that section exists is a live question: the neighbouring plans record that it did not exist on 2026-09-20 and that another plan's own open question creates it. Read `CHANGELOG.md` at build time; do not trust any of the three plans on this.**
- **Back-porting:** **RECOMMEND an explicit NON-GOAL**, per the standing house rule — consumers arrive via `install.sh` / `update.sh`. An install that has already dead-ended keeps the dead-end until it updates. ⚠ **The frozen benchmark install is never touched.**

### Phase 0 close record

**PENDING — nothing is ratified.** When it closes, this record must name **each** of D1, D2, D3, D4, D5 and OQ-1 through OQ-6 with its outcome (ratified / amended / declined), state whether per-item deliberation was supplied, state whether the close was an explicit pick or a delegation, and say which files the outcomes put in scope. **Every counter-argument stays where it is written — a ratified decision with its counter-argument deleted cannot be re-opened honestly.** ⚠ **Ratification changes no evidence class: ONE observed consumer incident, every structural fact re-derived by reading, nothing measured, no fixture reproduction yet.**

#### Verify

- The record names **each** of D1–D5 and OQ-1–OQ-6 with an explicit outcome. **No item is silently omitted**, and each is checked **by NAME, never against a range** — a range reads as complete while a hand-written enumeration beside it drops a member, and an item with no Verify line cannot fail.
- **OQ-1 and OQ-5 are closed in the SAME line or in two lines that reference each other** — the filename and the output token must not drift apart.
- **OQ-2's outcome is an explicit hygiene-token RATIFICATION or an explicit decline.** A close record that resolves the filename without ruling on the token has not closed OQ-2, and Phase 1 may not add the token on its own.
- **D5's outcome states whether it survives a declined D2** — if D2 is declined, D5 is re-posed standalone or it is declined too; it is never left implicit.
- It states whether per-item deliberation was supplied, and whether the close was an explicit pick or a delegation.
- **Every counter-argument above is still present, unshortened** — including D2's concession that rejected alternative 2 is cheap and sound, and D3's two accepted bounds.
- The record says what the outcomes put in scope: **D2 decides whether Phases 1–4 exist at all**; **D3 decides the marker's contents and therefore Phase 1's module**; **D4 decides Phase 3's two verbs**; **D5 decides whether Phase 2 edits the stderr**; **OQ-1 fixes the filename Phase 4 is allowed to quote**; **OQ-2 decides whether Phase 1 touches `_hygiene.py` at all**; **OQ-3 decides Phase 4's Step 4.6 edit**; **OQ-5 fixes the token Phase 2 emits**; **OQ-6 decides where Phase 5's CHANGELOG entry lands.**

---

## Phases

Phase 0 is the `## Phase 0 — ratification` section above; **nothing below starts before its close record exists.**

**Build order, and its forced dependencies.** **Phase 1 is first** — it owns the marker module and the fixture reproduction everything else is checked against. **Phases 2 and 3 both depend on Phase 1** and are independent of each other. **Phase 4 depends on Phases 2 and 3**, because it describes what they shipped and quotes the names they created. **Phase 5 runs last**, because it records what the earlier phases did. **Phase 6 is the maintainer's.**

⚠ **This plan is not shippable as Phase 2 alone.** Arm (c) with no producer admits nothing and changes no behavior — it would ship a predicate that can never fire.

### Phase 1 — The `_shared/` marker module, and the fixture reproduction

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** Commit by explicit path (F15).

#### Deliverables

- **The fixture reproduction, FIRST and before any new code.** A test that builds a feature dir by hand — an intake handoff, a `spec.md`, and a `*-seed.json` whose `target_stage` is `"research"` — and asserts that `find-handoffs --require` **exits 2 today**. ⚠ **This test is what turns a reported incident into something this repo can prove.** It is written against the CURRENT predicate and it must be green before anything else is written.
- `src/devforge/lib/_shared/<module>.py` — the marker writer and the marker reader over one implementation: compose the record (the recorded `sha256` of `spec.md` per D3), write it atomically to the filename OQ-1 ratified, and answer the read-side question "does this dir carry a marker whose recorded hash still equals `sha256(spec.md)`?"
- `tests/lib/_shared/` — tests covering: **marker written and read back; marker present with a MATCHING hash; marker present with a DIVERGED hash; marker absent; marker corrupt / unreadable / not a dict; `spec.md` absent at read time; and a byte-identical re-render leaving the hash matching** (D3's second bound).
- **`src/devforge/lib/_verify/_hygiene.py` — ONLY if OQ-2 ratified the token.** ⚠ **If OQ-2 declined or was left open, this file is not touched and the phase records that as an explicit verified no-op with the grep that shows it.**

#### Verify

- **The fixture-reproduction test is green against the UNCHANGED predicate**, and its assertion is `exit 2` — the dead-end is proven in-repo before it is fixed. ⚠ **After Phase 2 lands, that test's expectation flips by design; the phase that flips it says so in its own commit, and a later reader must not read the flip as a regression.**
- The marker reader is **read-only** — it writes no file and returns a boolean-equivalent result in every one of the seven cases above, including the three malformed ones.
- The marker reader **never raises** on a corrupt, unreadable or non-dict marker; it answers "no match", matching `_has_spec_reentry_seed`'s documented tolerance (F2).
- `git diff --stat` for this phase lists the new `_shared/` module, its test file, the reproduction test, **and `_hygiene.py` only if OQ-2 ratified it.**
- The targeted suite, then the full `tests/lib` suite, is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — `find-handoffs` arm (c), the D5 stderr repair, and their tests

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** **Needs Phase 1** — it consumes the marker reader. Commit by explicit path (F15).

#### Deliverables

- `src/devforge/lib/_specify/_cmds_handoff.py` — **arm (c) in `cmd_find_handoffs`'s predicate**, admitting a dir whose `spec.md` exists when the marker's recorded hash still matches, via Phase 1's reader; plus the **sixth-field token OQ-5 ratified** for a dir admitted only via arm (c); plus **the docstring's own predicate and Output-format paragraphs updated to describe three arms.**
- `src/devforge/lib/_specify/_cmds_handoff.py` — **the D5 stderr repair**: the headline stops implying the handoff is absent and names pendingness, and the body names arm (c). ⚠ **Only if D5 ratified; otherwise the body still needs arm (c) named, and the headline is left byte-identical and recorded as a verified no-op.**
- `tests/lib/_specify/test_find_handoffs_require.py` — ⚠ **that file exists today; add to it rather than creating a second module.** Tests covering: **arm (c) admits a marker-matched dir; arm (c) does NOT admit a diverged-hash dir; arm (c) does NOT admit a dir with no intake handoff; arms (a) and (b) behave exactly as before; and the `--require` stderr text.**

#### Verify

- **Arms (a) and (b) are unchanged** — every pre-existing test in `tests/lib/_specify/test_find_handoffs_require.py` is green **UNEDITED**, with the single exception of the Phase-1 reproduction test whose expectation this phase deliberately flips.
- **The first five output fields are byte-identical** on an arm-(a) hit, an arm-(b) hit and an arm-(c) hit — asserted by splitting on `" | "` and comparing the first five positions, **never by comparing whole lines.**
- **An arm-(c)-only hit carries the OQ-5 token and an arm-(b)-only hit carries ` | re-entry`**, and the two are distinguishable by more than whitespace.
- **A dir with no intake handoff is admitted by no arm**, marker or not — arm (c) is a THIRD disjunct inside the existing conjunction, never a replacement for it (F1, F8).
- **The `--require` stderr names all three arms**, and its headline contains no phrasing that implies the handoff is absent.
- `git diff` on `src/devforge/lib/_specify/` shows `cmd_find_handoffs`, its docstring and the stderr block **and nothing else** — **no edit to `_has_spec_reentry_seed`, no edit to `cmd_import_handoff`, no edit to `cmd_record_handoff_path`, no edit to `cmd_finalize_handoff`.**
- The full `tests/lib` suite is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 3 — The producer verbs on `research_helper` and `discover_helper`

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** **Needs Phase 1** — both verbs are thin wrappers over its module. Commit by explicit path (F15).

#### Deliverables

- `src/devforge/lib/research_helper.py` — a thin verb over Phase 1's writer, at the name Phase 0 ratified, plus its subparser registration.
- `src/devforge/lib/discover_helper.py` — the mirror verb, **over the SAME implementation** (D4). ⚠ **No second implementation and no cross-helper shell-out** (F12).
- Tests for both verbs covering: **`spec.md` present → marker written with the correct hash; `spec.md` absent → no marker written and exit 0 (OQ-4); the verb run twice → idempotent, same recorded hash; and a feature dir that does not exist → a clean non-zero exit with a usable stderr.**

#### Verify

- **Exactly ONE implementation exists** — `grep` for the writer's function name shows one `def`, in `_shared/`, and each helper's verb calls it.
- **Neither helper imports the other**, and neither shells out to the other — `grep` each helper for the other's name returns nothing new.
- **The OQ-4 case writes no file** and exits 0; the directory is byte-unchanged afterwards.
- **Running the verb twice produces a byte-identical marker** (same recorded hash, no duplicate file).
- The full `tests/lib` suite is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 4 — Instructions

**Route: instruction-author → instruction-reviewer, plus `claude-code-guide` for any Claude-Code-integration fact.** Instruction-only: **no `.py` file changes in this phase.** **Needs Phases 2 and 3** — it quotes the verb names, the filename and the output token they created. Commit by explicit path (F15).

#### Deliverables

- **`src/commands/research/main.md`** — Phase 0.6's attach-mode paragraph gains the marker's existence; **Step 4.6 gains the producer call and, per OQ-3, the conditional `--paths` element** in the shape `probe-script.<ext>` and `emission-matrix.md` already use (F13).
- **`src/commands/discover/main.md`** — the same two edits against its own Phase 0.6 attach-mode paragraph and its own Step 4.6 counterpart. ⚠ **Both lanes or neither** — a phase that wires only research ships a framework with one dead-ended lane (F7).
- **`src/commands/specify/main.md` — Phase 0.4 gains arm (c)**, in the shape of the existing arm (a) / arm (b) bullets. ⚠ **The arm-COUNTING sentences in that phase are part of the same edit** — the live text says *"either arm holds"*, *"its stderr names both arms"*, *"A pending feature dir — arm (a) or arm (b) above"* and *"both pending arms"*. **All of them become three-arm statements. A change that adds the bullet and leaves those four sentences saying "both" ships a self-contradicting instruction.**
- **`src/commands/specify/main.md` — Phase 0.5 gains ONE sentence**: a marker-admitted dir carries no seed directive, this block correctly no-ops there, and the direction for the revision comes from the freshly re-run intake handoff instead.
- ⚠ **Phase 4 must NOT weaken ANY of the FOUR "only READS the seed" sentences** — `research/main.md` Phase 0.6, `discover/main.md` Phase 0.6, `specify/main.md` **Phase 0.5** and `plan/main.md` PHASE 0a.7 (F6, F7, F16). **The marker is a NEW sibling artifact, not a mutation of the seed**, so all four prohibitions stay literally true — **and they must stay on the page, unshortened.** ⚠ **`specify/main.md`'s copy sits in Phase 0.5 — the same section the bullet immediately above edits** — so it is the one this phase can clip by accident while adding its own sentence. **`plan/main.md` is edited by no phase of this plan**; its copy is named here only so the four-file check below is not misread as putting that file in scope.

#### Verify

- `grep -n "This block only READS" src/commands/research/main.md src/commands/discover/main.md src/commands/specify/main.md src/commands/plan/main.md` returns **four** hits, **one per file** (F16), and **this phase's `git diff` changes none of those four lines.** ⚠ **Byte-identity is asserted PER FILE, each hit against that file's OWN text before this phase ran — never across files.** Only the research/discover pair is word for word; `specify/main.md`'s and `plan/main.md`'s copies are separately worded, so **a Verify that expects four identical strings fails against a perfectly correct tree** and must not be written that way. ⚠ **`specify/main.md` is the at-risk hit** — this phase edits Phase 0.5, the section its copy lives in — **and `plan/main.md` is grepped here as a READ-ONLY anchor only**, consistent with the `git diff --stat src/commands/` line below, which lists three files and not four. **A diff that touched any of the four has violated this phase's own constraint.**
- `grep -n "both arms\|either arm\|arm (a) or arm (b)\|both pending arms" src/commands/specify/main.md` returns **nothing** — every arm-counting sentence was converted.
- **All three command files name the ratified filename**, and **no emitted sentence names a verb, flag, filename or token that Phases 1–3 did not create.**
- **No emitted sentence names plan vocabulary** ("arm (c)" as a phrase is fine only if the file already numbers its arms that way — it does; "D2", "plan 109" and "Phase 0" are not).
- **`grep -n "no override\|NO cold-spec escape hatch" src/commands/specify/main.md` still returns the gate's own sentences** (F8) — arm (c) is an additional machine-written admission, **never a user-supplied bypass**, and the gate's unbypassable framing survives verbatim.
- `git diff --stat src/commands/` lists **`research/main.md`, `discover/main.md` and `specify/main.md` and nothing else.** ⚠ See `## Coordination with the neighbouring open plans` — a sibling plan's narrower diff-stat Verify is not violated by this line.
- The live-spec tests are green: `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py`, `tests/scripts/test_claude_emitter.py`.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 5 — Docs sweep

**Route: instruction-author → instruction-reviewer. Docs only.** ⚠ **Apply the coordination rule before touching any shared file** (F15, and `## Coordination with the neighbouring open plans`): other sessions are building in this checkout and several ledger files are already modified by other work. **Re-read `git status`, read each file LIVE, re-derive every edit from what is there, and commit by explicit path — never `git add -A`.**

#### Deliverables

- **`CHANGELOG.md`** — one entry, placed per OQ-6's answer, with **the evidence class FIRST and the honest bounds LAST.** ⚠ **Never an edit into a released version block.**
- **`CLAUDE.md`'s router table** — the pipeline-handoff rows. ⚠ **Verified 2026-09-21: the discover → specify row ends `specify_helper find-handoffs = one glob with the two-arm pending predicate.` That sentence becomes false the moment Phase 2 lands and is part of THIS change, not the next audit's.** Re-read the table live; the research → specify row is an edit-or-verified-no-op with the grep that shows it.
- **`src/devforge/storage-rules.md`** — the marker's git disposition. **It is FEATURE-SCOPED**: it lives at `specs/<feature>/`, which that file's own FEATURE-SCOPED class defines as *"the persistent per-feature records, committed per-step … everything under `specs/<feature>/`"*.
- **`68-INTAKE-OWNS-FEATURE-DIR-PLAN.md` — a back-reference under D10**, noting that D10's predicate has since gained a third arm and naming where it is specified. ⚠ **ADD a back-reference; do NOT rewrite D10's own text.** That plan is a finished record and its ratified wording stands as history.
- **`PLAN-STATUS-ARCHIVE.md` — the SAME back-reference, in BOTH of that file's shapes for that same plan.** ⚠ **That file restates D10's predicate INDEPENDENTLY of the plan document, so editing the plan document does not reach it.** Verified 2026-09-21, both shapes: its `## Index` line for `68-INTAKE-OWNS-FEATURE-DIR-PLAN.md` carries the clause *"D10 two-arm pending predicate"*, and its `## Entries` record for the same plan carries *"**D10** `find-handoffs`' pending predicate has TWO arms — (a) `spec.md` absent, or (b) `spec.md` present AND a sibling `*-seed.json` with `target_stage == \"spec\"` …"*. ⚠ **BOTH shapes or neither** — that file's own `## Index` preamble states *"When a plan's status changes, amend BOTH its line here and its entry below."* ⚠ **ADDITIVE only:** plan 68's ratified D10 text is neither rewritten nor contradicted; the amendment records that the predicate has since gained a third arm and names the live authority for it — `cmd_find_handoffs`'s own docstring and `src/commands/specify/main.md` Phase 0.4.
- **`DEVELOPMENT-STATUS.md`** and **`README.md`** — an edit or a recorded verified no-op each, with the grep that shows it.

#### Verify

- Every site above is recorded as an **edit or an explicit verified no-op**, with the grep that shows it.
- **`grep -rn "two-arm pending predicate" CLAUDE.md` returns nothing**, and the router row describes three arms.
- **`grep -rn "two-arm\|both arms" src/ CLAUDE.md` surfaces no surviving statement about `find-handoffs`' predicate.** ⚠ **Hits that belong to other mechanisms are expected and are left alone** — `src/CLAUDE.md`'s two-arm fix-or-file offer is one of them, verified 2026-09-21. ⚠ **This sweep stops at `src/` and `CLAUDE.md` and is NOT widened to the repo root** — `PLAN-STATUS-ARCHIVE.md` is covered by the two bullets below and by nothing else.
- **D10's own paragraph in `68-INTAKE-OWNS-FEATURE-DIR-PLAN.md` is byte-unchanged**, and the back-reference is additive text that does not reflow it.
- **`grep -n "68-INTAKE-OWNS-FEATURE-DIR-PLAN" PLAN-STATUS-ARCHIVE.md` returns exactly TWO lines** — that plan's `## Index` line and its `## Entries` record — **and neither of them any longer claims the predicate has two arms.** `git diff PLAN-STATUS-ARCHIVE.md` shows those two lines amended and **no other line of that file changed.**
- ⚠ **TRAP — the naive sweep of that file is FORBIDDEN, and "returns nothing" is not achievable there.** `grep -n "two-arm\|TWO arms" PLAN-STATUS-ARCHIVE.md` returned SEVEN matches on 2026-09-21. Two are this plan's business (`:58` *"two-arm pending predicate"*, `:189` *"TWO arms"*, both in plan 68's own shapes). **The other five sit on four lines and belong to plans this predicate has nothing to do with:** `:145` *"two-arm fix-or-file OFFER"* (the `26-REINTRODUCE-FIX-PLAN.md` record), `:225` TWICE — *"two-arm resolution"* and *"two-arm fork ADOPTED"* (the `82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md` record), `:237` *"two-arm \"Conversational fix-or-file offer\" grows to THREE arms"* (the `88-COLD-FIX-BUGS-LANE-PLAN.md` record) and `:243` *"two-arm variable-depth walk"* (the `91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md` record). **`two-arm` — and, at `:237`, even "THREE arms" — is ordinary vocabulary in that ledger for unrelated mechanisms.** A sweep keyed on the bare phrase rewrites finished records that were never about `find-handoffs`. **The only two lines this plan may touch in that file are the two the previous bullet's grep returns**; the digits above drift, so re-derive them from the quoted text.
- **No line belonging to any neighbouring plan is altered or reflowed by this sweep** — `git diff` on the shared files shows only this plan's own additions.
- **The CHANGELOG entry's evidence-class statement PRECEDES its honest-bounds statement**, read from the entry's own text and **never inferred from its section placement.**
- **No ledger sentence claims any phase is consumer-validated. "Built and build-verified" is the ceiling in every line.**
- **No tracked file names a client, an install, a repo, a branch, a ticket id or any benchmark identifier.**

### Phase 6 — Consumer e2e — user-driven HARD GATE, DEFERRED by default, NOT run

⚠ **Deferred by default, per the house pattern, and explicitly NOT WAIVED.** Everything Phases 1–5 ship is **build-verified at best and NEVER consumer-validated** until this phase runs, and **"done" never means Phase 6 passed.**

- **Fixture:** a testForge20 feature. ⚠ **The frozen benchmark install is never touched.**

The anchors are known-answer cases, **scored explicitly and in their pairs**:

1. **The full chain, research lane** — `/devforge:grill` → RE-ENTER-UPSTREAM targeting research → `/devforge:research` in attach mode → `/devforge:specify`. **The gate OPENS**, the chosen line carries the arm-(c) token, and Phase 0.5 no-ops. **PAIRED WITH 2.**
2. **The same feature immediately after `/devforge:specify` re-rendered a CHANGED `spec.md`** → the dir is **no longer pending**, arm (c) has closed itself, and no clearing step ran anywhere. ⚠ **Anchors 1 and 2 are scored as a PAIR: an arm that never opens passes neither, and an arm that never closes passes only the first.**
3. **The full chain, discovery lane** — the same run against `/devforge:discover`. ⚠ **Scored separately and explicitly. A pass on anchor 1 is not a pass here** (F7).
4. **A grill seed targeting research with NO intake re-run yet** → the gate still **BLOCKS**, because the marker does not exist. ⚠ **This is rejected-alternative-2's failure mode, pinned as an anchor.**
5. **A dir with a marker but NO intake handoff** → admitted by no arm.
6. **The `--require` stderr, read as a user would read it** → the headline does not imply the handoff is absent, and the body names all three arms.

#### Verify

- **Every anchor is scored explicitly — stated, not summarized — with anchors 1 and 2 scored together and anchor 3 scored on its own.**
- **If an anchor fails, record the negative with the artifacts and NAME THE MECHANISM before proposing anything:** a closed gate on anchor 1 is **the producer or arm (c)**; a still-open gate on anchor 2 is **D3's hash comparison**; a failure on anchor 3 alone is **the discover-lane producer**; an open gate on anchor 4 is **arm (c)'s predicate admitting too much**; an admitted dir on anchor 5 is **the conjunction being broken into a disjunction.** ⚠ **They have different fixes.**
- ⚠ **A clean run shows the chain completes on planted fixtures, never that the dead-end was common or that closing it bought anything measurable.**

---

## Non-goals

Each is argued, not merely listed.

- **No staleness propagation to `plan.md` or to the task breakdown.** ⚠ **Verified, not assumed.** Once `/devforge:specify` re-renders `spec.md`, its Step 5.4 `finalize-handoff` re-emits `<feature_dir>/handoff.json`, and `/devforge:plan` resolves that sibling through `plan_helper read-specify-handoff`, whose docstring states *"The sibling is spec_path.parent / \"handoff.json\""*. Independently, `/devforge:plan`'s own freshness gate `verify-spec-check` blocks on a `spec.md` whose hash no longer matches the recorded `**Spec hash**:` line in `spec-check.md` (F10), which routes the user through `/devforge:spec-check` as designed. **The chain moves forward on its own once the `/devforge:specify` gate opens. Adding staleness propagation here would duplicate a gate that already works.**
- **No mtime-based predicate.** An arm of the form *"the intake handoff is newer than `spec.md`"* was considered and is **REJECTED**: mtimes do not survive clone, checkout or a fresh install, so the gate would be non-deterministic across exactly the machines a consumer install spans. **The hash is content-addressed and survives all three.**
- **No seed deletion, no seed mutation, no `cycle_count` change.** The v1 simplification stands, in both intake specs, verbatim (F6, F7). **This plan adds a sibling artifact; it does not become the seed's second owner.**
- **No change to arms (a) or (b), and no change to `_has_spec_reentry_seed`.** D10's ratified predicate keeps both arms exactly as it defined them; arm (c) is additive.
- **No user-supplied override on the Phase 0.4 gate.** F8's unbypassable framing is correct and survives. **Arm (c) is machine-written evidence that an upstream stage re-ran, not a human assertion that the gate should open.**
- **No back-port into shipped installs** (OQ-6). They arrive via `install.sh` / `update.sh`.
- **Nothing is done to any installed consumer.** A frozen benchmark install exists; **this plan neither updates nor edits it and sends it no message**, and every verification here happens on a fixture inside this repo.
- **No new `verify-*` gate number and no new hard-fail validator script.** Arm (c) lives inside an existing gate; the producer verbs write a file and exit 0.
- **No `disable-model-invocation` change**, no constitution edit, no `src/CLAUDE.md` edit.
- **Anything specific to the benchmark**, and any client, install, repo, branch, ticket id or benchmark path in this repo.

---

## Context for next session

⚠ **Evidence class, repeated: ONE observed consumer incident, reported by a peer session against a frozen benchmark install whose artifacts are NOT in this repo and were NOT inspected here; every structural fact re-derived by READING this tree on 2026-09-21. NOTHING WAS MEASURED, and no fixture reproduction exists until Phase 1 writes one.** ⚠ All line digits drift — **grep the quoted text, never the digits.**

**The one sentence that governs everything here:** **when an upstream stage re-runs over a feature whose downstream artifacts already exist, something must record that those artifacts are stale — and the record must clear itself when they stop being stale.**

### Honest bounds

- **The marker is a hash comparison, so a hand edit to `spec.md` closes arm (c) with no re-spec having happened.** The same limitation lives in the `/devforge:plan` gate this is modelled on (F10). **Precedented, accepted, and not hidden.**
- **A byte-identical re-render leaves arm (c) open.** "Self-clearing" is true of a CHANGED spec, not of every re-spec. The result is a re-runnable gate, not a stuck one — but it is not airtight.
- **Arm (c) opens the gate; it does not force an import.** A `cold` pick on a marker-admitted dir re-specs without the corrected intake content, and nothing prevents that. **The user keeps the call, which is consistent with Phase 0.4's existing design and is also a way to waste the re-run.**
- **Nothing here measures** how often a grill verdict targets an intermediate stage, how often users hit the dead-end, or what the unsupported workarounds cost. **No rate was computed before this plan and none will be after it.**
- **The reporter's account was relayed, not inspected.** Every structural claim was re-derived; **the incident itself was not.**
- **The stderr headline is a diagnosis cost only** (Correction 1). Repairing it makes the block legible; it does not make the block go away.

### Traps

**Trap 1 — retargeting the consumed seed to `"spec"`.** It puts a research conclusion in the field `/devforge:specify` Phase 0.5 documents as *"what the previous spec concluded"*, and it is the consumer mutating the producer's record against *"This block only READS the seed's directive"* (D2, rejected alternative 1).

**Trap 2 — broadening arm (b)'s `target_stage` set.** Cheap, sound-looking, and **wrong on timing**: the seed exists before the demanded re-run, so the gate would open while the re-run is still outstanding (D2, rejected alternative 2).

**Trap 3 — a second grill seed.** Two files want the name `grill-seed.json` (F5), and the directive would be authored before the evidence existed (D2, rejected alternative 3).

**Trap 4 — naming the marker `*-seed.json`.** Three globs would claim it, one of them project-wide from `/devforge:plan` (F11, OQ-1).

**Trap 5 — teaching `artifact_helper` what the marker means.** Its own callers' specs praise it for *"never opening a seed or knowing what one means"* and rely on that for removability (F12, D4).

**Trap 6 — adding a clearing step to `/devforge:specify`.** D3 exists precisely so no command deletes another command's artifact. A clearing step would also have to decide what to do when the re-spec is abandoned halfway.

**Trap 7 — adding the hygiene token without ratification.** `_hygiene.py`'s own docstring forbids it: *"no token may be added or removed without a fresh ratification"* (F14, OQ-2).

**Trap 8 — weakening any of the FOUR "only READS" sentences while editing the re-entry blocks.** They live in `research/main.md` **Phase 0.6**, `discover/main.md` **Phase 0.6**, `specify/main.md` **Phase 0.5** and `plan/main.md` **PHASE 0a.7** (F16). ⚠ **specify's copy is in Phase 0.5, NOT Phase 0.6 — that file's Phase 0.6 is the unrelated model advisory — and Phase 0.5 is a section Phase 4 edits**, which makes it the one this plan can clip by accident. The marker is a new sibling artifact, so all four sentences stay literally true; Phase 4's Verify pins all four byte-unchanged, **per file against its own text** (F6, F7, F16).

**Trap 9 — adding the arm (c) bullet and leaving the arm-counting sentences saying "both".** Four sentences in `src/commands/specify/main.md` and one router row in `CLAUDE.md` count the arms and are CONVERTED; **all five are part of the same change** (Phase 4, Phase 5). ⚠ **Two further arm-counting restatements live in `PLAN-STATUS-ARCHIVE.md`'s two lines for plan 68** — those are Phase 5's, and they are **amended ADDITIVELY, never converted**, because they are a finished plan's ratified record. **Five converted, two amended — do not treat the seven alike.**

**Trap 10 — shipping the research lane only.** `/devforge:discover` has the identical defect in identical words (F7). One lane fixed is an asymmetry, not a fix.

**Trap 11 — reading the Phase-1 reproduction test's flipped expectation as a regression.** It asserts `exit 2` against the CURRENT predicate by design, and Phase 2 deliberately flips it.

**Trap 12 — describing the stderr headline as a cause of the block.** It is not (Correction 1). No phase, ledger line or CHANGELOG entry may say otherwise.

**Trap 13 — touching another session's plan file, or sweeping a shared ledger.** On 2026-09-21 SIX neighbouring plan files were untracked and in flight, a seventh (`107-SURFACE-PATH-PROOF-PLAN.md`) was tracked and unmodified — **present is not the same as in flight** — and eight tracked files were modified by other work (F15). ⚠ **`PLAN-STATUS-ARCHIVE.md` is the sharpest case of the ledger half:** Phase 5 amends exactly two of its lines and no others, and a sweep keyed on the phrase `two-arm` there would rewrite finished records of unrelated plans — **Phase 5's Verify holds the line numbers and the reason.** Re-read `git status`, read each file live, commit by explicit path.

**Trap 14 — quoting a `file:line` from this plan as current.** Every anchor here was true on 2026-09-21 and drifts on the next edit to those files.

### File anchors

**EDIT targets — a phase of this plan writes each of these:**

- **`src/devforge/lib/_shared/`** — the new marker module (Phase 1).
- **`src/devforge/lib/_specify/_cmds_handoff.py`** — `cmd_find_handoffs` only: its predicate, its docstring's predicate and Output-format paragraphs, and its `--require` stderr block (Phase 2).
- **`src/devforge/lib/research_helper.py`** and **`src/devforge/lib/discover_helper.py`** — one thin verb and its subparser each (Phase 3).
- **`src/devforge/lib/_verify/_hygiene.py`** — **ONLY if OQ-2 ratified the token** (Phase 1).
- **`src/commands/research/main.md`** — Phase 0.6's attach-mode paragraph; Step 4.6 (Phase 4).
- **`src/commands/discover/main.md`** — its Phase 0.6 attach-mode paragraph; its Step 4.6 counterpart (Phase 4).
- **`src/commands/specify/main.md`** — Phase 0.4's arm bullets and its four arm-counting sentences; one sentence in Phase 0.5 (Phase 4).
- **`tests/lib/_specify/test_find_handoffs_require.py`** (exists), **`tests/lib/_shared/`**, and the helper test modules (Phases 1–3).
- **`CHANGELOG.md`**, **`CLAUDE.md`** (router table only), **`src/devforge/storage-rules.md`**, **`68-INTAKE-OWNS-FEATURE-DIR-PLAN.md`** (additive back-reference under D10 only), **`PLAN-STATUS-ARCHIVE.md`** (that same plan's TWO lines only — its `## Index` line and its `## Entries` record, both amended ADDITIVELY; no other record in that file), **`DEVELOPMENT-STATUS.md`**, **`README.md`** (Phase 5).

**READ-ONLY anchors — no phase of this plan writes any of these, and an anchor listed here is a file to READ, never an edit target:**

- `src/devforge/lib/_specify/_cmds_handoff.py`'s OTHER functions — `_has_spec_reentry_seed`, `cmd_import_handoff`, `cmd_record_handoff_path`, `cmd_finalize_handoff`.
- `src/devforge/lib/_shared/seed_schema.py` — `SEED_TARGET_STAGES`, `ReEntrySeed`.
- `src/devforge/lib/plan_helper.py` — `verify-spec-check` (D3's precedent), `read-specify-handoff` (the non-goal's evidence).
- `src/commands/grill/main.md` — PHASE 5's seed inputs and PHASE 7's seed-write block.
- `src/commands/plan/main.md` — its project-wide `*-seed.json` glob (F11), **and its own separately-worded copy of the "only READS the seed's directive" prohibition at PHASE 0a.7 (F16)**. ⚠ **Phase 4's Verify greps this file; no phase edits it.**
- `src/devforge/lib/_shared/feature_scope.py`, `feature_alloc.py` — D4's standing examples.
- `68-INTAKE-OWNS-FEATURE-DIR-PLAN.md` — D10 and OQ-1, read for their ratified reasoning; **only the additive back-reference is written.**
- The neighbouring open plans named in `## Coordination with the neighbouring open plans`.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation. Then read `## Coordination with the neighbouring open plans` together with each neighbour's own `## Non-goals` and scope statements; three plans edit one command file. ⚠ **Find every sibling plan by its TITLE if a filename has moved** — `grep -l "Intake Provenance Continuity Plan" *.md`, `grep -l "Specify In-Place Revision Plan" *.md` — **never by assuming a number.**
2. **Check `### Phase 0 close record` first** — it sits at the end of `## Phase 0 — ratification`. While it reads *PENDING*, nothing is ratified, **no build phase may start**, and **no verb name, flag, filename or output token from this plan may be quoted in any file.**
3. **Re-verify F1–F16 against the live tree. Grep the QUOTED TEXT, never the digits:** `_has_spec_reentry_seed`, `target_stage`, `This block only READS`, `BLOCKED: /devforge:specify requires`, `| re-entry`, `Spec hash`, `grill-seed`, `attach mode`. ⚠ **After a build phase some of these strings have changed by design — a differing result is then the built state, not a regression, and the phase that changed it says so in its own commit.**
4. **Build order:** **Phase 1 first** (it owns the marker module and the fixture reproduction); **Phases 2 and 3 both need Phase 1** and are independent of each other; **Phase 4 needs Phases 2 and 3**; **Phase 5 runs last.** ⚠ **Never ship Phase 2 alone** — arm (c) with no producer can never fire.
5. **Route every edit through the house flow:**
   - python-engineer → python-reviewer for every Python edit, with a test per function, written and run in the same turn;
   - instruction-author → instruction-reviewer for every markdown edit;
   - `claude-code-guide` for every new Claude-Code-integration fact.
6. **Commit by explicit path, never `git add -A`.** Re-read `git status` first, and read every shared file live (F15). **Never touch another session's plan file.**
7. **After each phase, cross-check.** Grep every verb, flag, filename, arm label and phase name touched — `find-handoffs`, `_has_spec_reentry_seed`, `cmd_find_handoffs`, the ratified marker filename, the ratified producer verbs, the ratified sixth-field token, `Phase 0.4`, `Phase 0.5`, `Step 4.6`, and the arm-counting phrases `both arms` / `either arm` / `two-arm` — and fix any dangling reference **in the SAME change.** ⚠ **The `two-arm` sweep stops at `src/` and `CLAUDE.md`.** In `PLAN-STATUS-ARCHIVE.md` that phrase is ordinary vocabulary for unrelated plans, and only the two lines Phase 5 names may be amended there — **Phase 5's Verify holds the evidence and the forbidden grep.**
8. **Run Phase 5, then leave Phase 6 to the maintainer.** "Done" means BUILT and build-verified; it never means Phase 6 passed.
9. **Keep the evidence class attached.** Any summary of this plan repeats it: **ONE observed consumer incident, relayed and never inspected here; every structural fact re-derived by reading this tree on 2026-09-21; nothing measured.**
