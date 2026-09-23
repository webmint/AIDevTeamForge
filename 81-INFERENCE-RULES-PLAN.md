# 81 — Inference Rules: turning correct facts into correct conclusions

**Status:** **✅ DONE (build) 2026-08-18 — Phases 0–6 complete; Phase 7 consumer e2e DEFERRED 2026-08-18 — maintainer intends to run it (NOT waived; build-verified, NOT consumer-validated). The frozen-prompt re-run stays the HARD GATE, model pinned `claude-fable-5`.** Builds, one commit per phase: F4 `9e4757a`, F1 `9a3300b`, F2 `af16cb3`, F3 `59b5152`, F5 `92eadfb` (OQ-3 seam = ac-verifier Rule 14; see the OQ-3 record), F6 `fe7329b`, docs `b1a1484`. The tripwire held in every phase's diff; full suite green post-build (10812 passed, 0 moved). Phase 0 record follows. All ten items (a)–(j) confirmed by the maintainer as recommended, no overrides: D1–D6 as written (D3 with its no-baseline bound, D5 with the FALSE BINARY finding remaining open, D6 with the model pinned to `claude-fable-5`), OQ-1 = no mechanical detector for v1, OQ-2 = role key as mitigation with residual recorded, OQ-3 = seam decided at Phase 5, and item (j) F6 ratified explicitly with its second-incident provenance and paraphrase residual. Anchors re-verified against the working tree 2026-08-18 before ratification (plans 79/80 landed since the 2026-08-17 verification; only plan 79 touched target files, memory-excerpt lines only, no anchor moved). Every decision carries its counter-argument.
**Type:** DESIGN + BUILD plan. Instruction-only (D1). Its acceptance test is a single user-driven re-run of a frozen prompt (Phase 7), which is a HARD GATE and not a measurement design — see D6's honest bound.
**Branch:** `develop-2.0-init`
**Created:** 2026-08-17.
**Amended:** 2026-08-18 — **F6 added pre-ratification** (a sixth fix, from a SECOND observed incident). The amendment added **no new D-number and no new OQ-number**; F6 is ratified at Phase 0 as item **(j)**.

## ABSOLUTE CONSTRAINT ON THIS FILE

**The originating evidence is a benchmark against a private client codebase, and this repository is PUBLIC. This file is mechanism-only.** It contains no ticket ID, feature slug, commit SHA, branch name, company or product name, component name, function name, parameter name, file path or enum value from that codebase, and none may be added — not in an example, not in a table, not in a grep pattern. Where the failure must be described, it is described in invented neutral terms: **a shared query-filter builder**, **two UI entry points (a tab and a modal)**, **the hidden surface**, **AC-2** as an anonymous label for the run's second acceptance criterion.

Any identifier introduced into this file, into any `src/` file, into a commit message or into a test fixture during this plan's execution is a hard error, not a style nit. **If a sentence only works with a real identifier, rewrite the sentence.**

**Evidence provenance.** The originating record is `81-EVIDENCE-V2-BENCHMARK-RUN.md` (present at repo root, verified 2026-08-17). **It carries private-client identifiers, it must never be committed, and it must never be quoted or excerpted into this file or any other tracked file** — the same disposition as the untracked plans 73/74/75 and `77-EVIDENCE-DISCOVERY-TO-LOCK-INVERSION.md`, routed to plan 78's delete-at-v2-go-live decision rather than to a scrub. It is cited here by filename only. It shares this plan's `81-` filename prefix but is EVIDENCE, not a second plan file; an `81-*` glob returns exactly these two — this plan and the evidence file (verified 2026-08-17). An unrelated plan briefly carried the same number; it has been renumbered to `83-DOWNSTREAM-REENTRY-SEED-PLAN.md`, so that collision no longer exists and must not be re-added from a stale index line. **F6's second incident (2026-08-18) has NO evidence file at all** — it is a conversational maintainer report whose only record in this repository is F6's own origin paragraph, written in the same mechanism-only terms. Do not sharpen it with an identifier, and do not go looking for a third `81-`-prefixed file.

---

## The failure — one causal chain, seven steps

A frozen brownfield ticket (remove a small set of filters from one search surface) was run 20 times across 6 spec-driven-development frameworks. **This framework's v2 produced the best run in the set**, and it is the run this plan is built on:

- its `/devforge:research` emission matrix — plan 77's shipped artifact — named the coupled call site that 16 of the 20 runs never named;
- its Coupling decision point surfaced the hidden second UI surface **by name, unprompted**;
- its spec wrote the only acceptance criterion in the benchmark requiring **both** entry points to change;
- its architect's rejected-alternative forcing step derived the decisive argument-level fact correctly.

**And it failed the handling probe.** The hidden surface — a modal reaching the same shared query-filter builder as the tab named in the ticket — kept the removed filters, because the implementation added a discriminator parameter instead of changing the predicate inside the shared builder.

The chain, genericized:

1. **`/devforge:research` labelled the coupled caller's surface with the name of a lane it RESEMBLED.** That label was false. It is the only wrong input in the entire run.
2. **`/devforge:specify` wrote a preservation AC (AC-2)** protecting that mislabelled lane's behavior — an AC over a state the code cannot reach, because no reachable construction site produces it.
3. **`/devforge:spec-check` returned CONSISTENT 12/12 — correctly.** An unfalsifiable AC cannot conflict with anything; Z3 was sat on both quorum passes. The prover did its job.
4. **The Rule 5 impossibility analysis was correct** — the bracketed Rule 5 note at `src/commands/plan/main.md:443` and its architect-side twin, Rule 9's Rejected-alternative checkability forcing step. (**"Rule 5" is `plan/main.md`'s label, never the architect's** — `src/agents/architect.md`'s own Rule 5 is "Synthesize, don't rubber-stamp", `:149`. Do not write "architect Rule 5".) It derived that the two supposed lanes can present a byte-identical argument tuple to the shared builder.
5. **The inference from that fact was wrong.** The architect concluded "identical tuple, opposite outputs required ⇒ intrinsic derivation impossible" and chose a discriminator parameter. **The correct inference from an identical REACHABLE tuple plus opposite required outputs is that the two "lanes" are ONE lane and the two ACs conflict** — a product question to escalate, not an implementation gap to bridge.
6. **The plan's narrowing answer marked the coupled caller out of scope, citing the phantom AC-2.**
7. **The plan discharged the both-surfaces AC as "holds by construction — no file in that layer changed."** File-layer reasoning discharging a behavioral (emitted-request) claim.

**One mislabel at intake survived a formal consistency proof and a correct argument-level analysis and emerged as the operative design constraint.**

### What this rules out, before any fix is proposed

The benchmark's own null results bound the solution space, and they are the reason this plan proposes no new verification layer:

- artifact volume varied **24×** with no effect on the probe;
- test volume varied **14×** with no effect;
- review depth ranged from none to mutation-tested, with no effect.

**Every verification layer validates against the spec's model of the code, and more of it hardens whichever model it is given.** In this run, four independent mechanisms — the matrix, the coupling decision point, the SMT prover, the architect's forcing step — each executed correctly and each hardened a model built on one false label. **So the fix must be INFERENCE RULES over facts already computed, never new verification layers.** That sentence is this plan's spine; a phase that adds a checking stage has left the plan.

### The bar this plan inherits

Plan 77's criterion governs every rule below and is meant to be quoted:

> **The visibility bar: does the rule produce an artifact that is visibly wrong when the analysis wasn't done?**

The six fixes clear it on CONTENT grounds, not on presence grounds: a surface label with no construction site named beside it, an identical-reachable-tuple rejection recording neither a distinctness showing nor an escalation, an impossibility rejection stating an expression where a value set belongs, a preservation AC with no cited construction site, a behavioral AC discharged by a file-level observation, and an upstream re-entry attribution naming no introducing artifact each read wrong on their face, with no design principle needed to see it.

---

## The six fixes

Each is an inference rule attached to a forcing step that **already exists and already fires**. None adds a stage, a verb, a check number, or an artifact.

### F4 — Derived surface labels (root cause) — `/devforge:research`

**The rule.** The surface label on a caller classification must be **DERIVED from that caller's construction sites** — who builds it, with which dependencies — and never taken from the name of a lane, tab, route or mode it resembles. A label the classifier cannot tie to a construction site is not a label; it is a guess, and it must be recorded as one.

**Targets, verified 2026-08-17:**
- `src/commands/research/main.md:505`–`:532` — Step 2b, the plan-69 WI-E `classify-caller-scope` upward-trace block. The machinery is already there: the inbound trace (`:512`), the 8-hop bound to the first user-facing entry point (`:515`), the `--surface` / `--scope` / `--justification` setter (`:520`–`:526`), and the rule that a found entry point MUST be cited by name in the justification (`:528`). **What is missing is the standard for the VALUE**: `--surface` accepts any non-empty string, and nothing says where the string must come from.
- `src/commands/research/main.md:1146`–`:1170` — the emission-matrix composition text, whose **step 1** reads each caller's recorded `surface` as context for its Note (`:1148`).

**Why it is the root.** Steps 2–7 of the chain each behaved correctly given their inputs. Only step 1 produced a false input. Fixing F1–F3 without F4 catches this failure three times downstream; fixing F4 prevents it.

**Relationship to plan 77's finding A4 — sibling gaps on one call site, and A4 did NOT name this one.** A4 (`77-POST-CHANGE-OUTPUT-MATRIX-PLAN.md`, `### A4`, verified 2026-08-17) names the research-time `scope: out` classification with an unconstrained free-text **justification** as an upstream lock point, and records that constraining that string MECHANICALLY is outside its own instruction-only scope. **A4 never mentions `--surface`, and its scenario is not this run's failure mode:** the coupled caller here was classified `scope: in` — surfaced by name, never excluded — so no exclusion justification was the lock. **A4 and F4 constrain two DIFFERENT fields of the same `classify-caller-scope` call**: A4 the justification attached to an exclusion, F4 the derivation of the `--surface` label, which is set unconditionally whether the caller is in scope or out. That makes them siblings on one call site — **and it makes F4 a gap plan 77 did not name**, so do not build it as the completion of A4.

*Counter-argument, recorded:* a construction-site trace is real work at a stage that already traces a lot, and a caller with many construction sites makes the rule expensive. The defence is that the trace is bounded by the same 8-hop walk Step 2b already performs, in the same direction, and that the expensive case — many construction sites producing different dependency sets — is exactly the case where a single resembling name is most likely to be wrong.

### F1 — The identical-tuple rule — `/devforge:plan` + architect

**The rule.** When argument analysis shows two call sites can present the **same reachable tuple** to a shared function, **the default conclusion is that they are the same lane.** An identical reachable tuple plus opposite required outputs is **an AC CONFLICT to escalate as a product question**, never an implementation gap to bridge. Adding a parameter to force identical tuples apart is permitted only **after** the two sites are shown genuinely distinct — and **"an AC says one of them must not change" is NOT that showing**, because that is what the conflict is about.

**Targets, verified 2026-08-17:**
- `src/commands/plan/main.md:443` — the bracketed Rule 5 note under the Key Design Decisions table: an alternative rejected as IMPOSSIBLE "must name the arguments the function in question actually receives and show the impossibility claim against them."
- `src/agents/architect.md:153` — Rule 9's **Rejected-alternative checkability forcing step**, the architect-side twin of that note. **Its own worked example is the failing shape**: it illustrates a rejection reading "the shared formatter can't tell the two callers apart — it receives only `items` and `locale`, and neither carries the caller's mode." That is the run's fact, correctly derived. **The rule produces the fact and then says nothing about what follows from it** — which is precisely the gap F1 fills.

**Relationship to the standing FALSE BINARY finding (repo-root `FINDINGS.md`, finding 1) — read this before proposing a constitution edit.** F1 is the mechanical trigger that finding has lacked: an identical reachable tuple is the condition under which the enumeration-independent form (derive the restricting condition inside the shared function from arguments it already receives) is the only form that can work. **This plan nevertheless makes NO edit to `src/constitution.md` (D5).** The run is direct evidence that a constitution edit would not have helped: Rule 5 DID consider the intrinsic form first and rejected it — on the phantom AC's authority, not on a rule preference. **The phantom, not the preference, was decisive.**

*(Amended 2026-09-19 by plan 99, `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md` — F1 is unchanged, and so are its two sites, the Rule 5 note and Rule 9's Rejected-alternative checkability forcing step; it stays code-side, reasoning about call sites that present arguments to one shared function. Plan 99 added its user-side counterpart — a surface shows the feature only on cited user-visible identity evidence, and shared code is never that evidence (`/devforge:research` Phase 2.4e) — which also reaches a surface on a different request path, one that never calls the shared function and that F1 therefore cannot see.)*

*Counter-argument, recorded:* "the default conclusion is that they are the same lane" is a default, and a default is a preference — which is the instrument plan 77's evidence says loses against one confident sentence. The defence is that F1 is not stated as a preference between designs but as a **named consequence with a named escalation route**: the artifact must either show the two sites are distinct, or carry the escalation. An artifact that shows neither reads wrong on its face.

### F2 — Value sets, not expressions — `/devforge:research` matrix + `/devforge:plan`

**The rule.** Every artifact that reasons about a call site — an emission-matrix row, a Rule 5 impossibility rejection, a caller trace — must record each argument's **REACHABLE VALUE SET** before that row or rejection is usable as evidence. "Varies", a bare parameter name, or an expression standing in for the values it can take is an incomplete answer.

**⚠ CORRECTION — this fix does NOT close an accounting hole, and a build session must not write as though it does.** Verified against the shipped text 2026-08-17:

- `src/commands/research/main.md:1158` — **composition step 5** (the numbered steps at `:1146`–`:1160`, distinct from the `**The rules this matrix must satisfy**` bullets at `:1162`–`:1170`; `:1170` says in terms that **there is no rule 5** — do not label this text as one) already handles `varies` conservatively: an undeterminable cell **must** state in the Note which values were considered and what blocked the trace, and **the verdict is recorded `affected`**. "The conservative reading is the recorded one: an undeterminable set is never `unaffected`."
- `src/commands/plan/main.md:370` — sub-question 11 already forces every `affected` row to be accounted for, and states explicitly that a `varies` cell **is** an `affected` row "and is accounted for like any other." An unaccounted `affected` row "is not recordable."
- `src/commands/plan/main.md:539` — PHASE 2.5 step 8 is the read-side backstop for that accounting.

**The run's row WAS flagged and WAS accounted for.** It was accounted for with a sentence licensed by the phantom AC. **So there is no accounting hole to close.** What F2 removes is the AMBIGUITY that made a wrong accounting sentence look plausible: when the cell names an expression, the reader cannot see that the accounting sentence contradicts the values that expression actually takes.

**Two consequences for the build, stated so they are not lost:**

1. **Do NOT ban the word `varies`.** Composition step 5 at `:1158` permits it deliberately, for genuinely dispatch-blocked sites, and the ban would convert a fail-safe into a forced guess. **And do not re-add the considered-values requirement to that step — it is already there.** F2's delta at the research site is narrower: the **`Emits today` and intersection cells of a NON-`varies` row** must read as value sets, so that a cell naming an expression is recognised as an assertion rather than a trace (matrix rule 2 at `:1165` already demands "traced, never asserted" — F2 supplies the standard for what counts).
2. **The plan-side delta is where the fix actually bites.** `plan/main.md:443` and the architect's Rejected-alternative step require naming the arguments the function receives and showing the claim against them. **Neither requires stating each named argument's reachable VALUE SET** — so a rejection may name an argument and reason about it as an expression, which is exactly what "identical tuple" was derived from and what nothing forced into values.

*Counter-argument, recorded:* enumerating a reachable value set is unbounded for a parameter of open type, and an unfillable requirement gets waived or filled reflexively — plan 77's OQ-2 names that as the visibility bar failing in a new way. The mitigation is the one already shipped at `:1158`: an unenumerable set is declared as such, with what was considered and what blocked it, and the conservative verdict is recorded. F2 extends that shape; it does not invent a stricter one.

### F3 — Preservation-AC admission — `/devforge:specify`

**The rule.** Before an acceptance criterion enters as **behavior preservation**, its subject state must be shown **REACHABLE** — a cited construction site, traced and not asserted. **An AC that cannot be violated is not a guard; it is a constraint that shapes the implementation while protecting nothing.**

**This work item takes OWNERSHIP of the file-less preservation-AC finding recorded in repo-root `FINDINGS.md` as finding 4 (D4).**

**⚠ CORRECTION — the shipped directive did not stop this AC, and the build must be designed against that fact.** Verified 2026-08-17: `src/commands/specify/main.md:619` already carries plan 77's R3 directive in full — an AC asserting that a value this change removes is still present or still emitted "may NOT be written from inferred intent; it requires product intent, quoted", and the text names the trap by name ("We did not intend to touch that file" is inferred intent and is not sufficient). **AC-2 was written anyway.** The most probable reason is that it was framed as **lane-behavior preservation** rather than **value presence**, so it never matched the directive's lexical trigger.

**F3 therefore does two things:**

**(a) Widen the trigger from phrasing to ROLE.** Verified 2026-08-17: `specify_helper add-ac --subsection` already carries a `behavior_preservation` value (`src/commands/specify/main.md:637`), mapping to the fixed heading **§5.2 Behavior preservation** (`:648`). **That subsection key is a role declaration the author makes explicitly**, so the requirement can be keyed on it rather than on how the statement happens to be worded. This is the recommended resolution of OQ-2 and it is the strongest available answer, **with its bound stated: an author can still file a preservation-shaped AC under `behavior_change` or another subsection.** The role key narrows the dodge surface; it does not close it.

**(b) Add the reachability citation.** An AC entering §5.2 asserts a state must be preserved; the artifact must show that state is reachable, by citing the construction site that produces it. **Where no construction site can be cited, the AC is not a preservation criterion** — it is the product question F1 escalates, and it belongs in §8 Open Questions with a §9 Risks finding, the route `:619` already prescribes for the matrix's non-empty-intersection case.

**Two bounds, both mandatory in the emitted text:**
- **Plan 62's D9 parallel.** `/devforge:spec-check` catches a permission clash only when a permitting case is **asserted reachable**. F3 is the same principle one stage earlier and in prose: an unreachable subject state makes the criterion unfalsifiable, and an unfalsifiable criterion is what the prover correctly passed.
- **Reachability by static trace is bounded by dynamic dispatch.** F3 catches the AC-2 class — a state with no reachable construction site — and not every phantom.

**`/devforge:spec-check` stays opt-in and ADVISORY per its ratified D14, and this plan proposes no change to it.** Its entry in `PLAN-STATUS-ARCHIVE.md` explicitly warns a future session not to strengthen it; F3 does not, and a build session must not read F3's subject matter as licence to.

*(Reconciled 2026-08-19 — true when written, and this plan's scope claim still stands. `82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md` ratified its D6 on 2026-08-19 and amended plan 62's D14 in place: `/devforge:spec-check` is now RUN-mandatory — `/devforge:plan` blocks until a fresh `spec-check.md` exists for the resolved spec — while **the verdict never binds** and the command is still typed by the user. So the sentence above describes the stance as of this plan's build, not the current one; what is unchanged is that **THIS plan changed nothing about that command**. The two are defence in depth on the same failure class, with the split stated in that plan's D8 and in `FINDINGS.md` finding 4: **F3 = admission at authoring; plan 82 = refusal at formalization.**)*

*Counter-argument, recorded:* requiring a citation for every §5.2 AC taxes the common, correct case — most preservation ACs are about states everyone knows are reachable, and the citation is then ceremony. The defence is that the ceremony is one traced line, and that the case where the state's reachability is obvious is exactly the case where the line is cheapest to write. The case where it is expensive is the case worth stopping.

### F5 — Behavioral ACs cannot be discharged by file-layer reasoning — `/devforge:plan` + `/devforge:verify`

**The rule.** **"Holds by construction — no files in layer X changed" is an invalid discharge of an AC about emitted output.** An AC asserting what a path emits is satisfied only by evidence about that path's emitted output. The absence of a diff in a file set is evidence about files; it is not evidence about behavior, and for a shared-code change it is evidence of precisely nothing, since the whole hazard is behavior changing where files did not.

**⚠ CORRECTION — the brief's plan-side target does not exist. Verified 2026-08-17:** `src/commands/plan/main.md` contains **no test-boundary and no verification-strategy section**. The plan template (`:384`–`:514`) runs Specialist Consultation → Summary → Technical Context → Constitution Compliance → Implementation Approach (Layer Map, Key Design Decisions, Established-Convention Departures, Pure-Builder Targets, Change-Induced Dead Code, Follow-On Cleanups, File Impact, Documentation Impact) → Risk Assessment → Dependencies → Supporting Documents. A grep for `test` in that file returns three hits, all about the property-test lane (`:367`, `:461`, `:559`). **Do not go looking for the section; it is not there.**

**The actual plan-side seam is PHASE 2.5 steps 1–3** (`src/commands/plan/main.md:528`–`:534`), the plan-spec cross-reference check. Step 2 instructs the orchestrator to verify each AC by checking "the plan's 'Layer Map' and 'File Impact' for files/components related to this AC" — **AC coverage established through a file list.** For a behavioral AC over a shared code path that is the invalid discharge, written into the step that is supposed to catch the gap. F5 lands there: a behavioral AC is covered when the plan names the behavior-changing decision that satisfies it, and an AC that no decision's behavior change reaches is uncovered **even when every file it mentions appears in File Impact**.

**The verify-side seam is OQ-3 and is decided at build after reading the live files.** Two candidates, both verified present 2026-08-17:
- `src/agents/ac-verifier.md` — Rules run 1–13 (`:125`–`:137`), so an F5 rule appends as **Rule 14** under the repo's append-never-renumber convention. Rule 9 (`:133`) already makes evidence mandatory for every `PASS`/`FAIL`/`PARTIAL`; F5 would say what does not count as evidence for a behavioral AC.
- `src/commands/verify/main.md:180` — PHASE 3.3, where the orchestrator composes the `ac-verifier` brief.

Recommendation: **the agent rule**, because the agent renders the verdict and the brief is composed per run. Decide at build, having read both.

*Counter-argument, recorded:* "evidence about the emitted output" is expensive at `/devforge:plan`, where nothing has been emitted yet, and the plan-side half of F5 risks demanding runtime evidence at a design stage. The defence is that the plan-side demand is narrower — name the behavior-changing decision, not observe the behavior — and that the observation half belongs to the verify side, which is where the run's discharge should have been caught a second time.

### F6 — Attribution traces to introduction, not restatement — `/devforge:grill`

**RATIFIED 2026-08-18 as Phase-0 item (j)** — explicitly, since F6 carries no D-number: the rule as stated, its second-incident origin (a maintainer-reported consumer run of 2026-08-18, conversational, no artifact in this repository), and its recorded residual that paraphrased transcription can still mis-attribute. Its place in the priority order is confirmed under item (b)/D2.

**The rule.** When PHASE 5's Q2 reaches RE-ENTER-UPSTREAM, the NEAREST introducing stage is established by tracing the invalidated conclusion back to the artifact that **INTRODUCED** it, and the feature's `research-handoff.json` and `discover-handoff.json` (where present) are **MANDATORY trace inputs** — not `spec.md` + the dossier alone. **The decision standard: where the invalidated conclusion's substance — a surface label, a caller row, a requirement's content — appears in an upstream handoff, the introducing stage is that upstream artifact's stage; `spec` is the introducing stage only when the conclusion has no upstream source.** Where the text was WRITTEN is not where the error was INTRODUCED.

It clears plan 77's visibility bar on the same CONTENT grounds as F1–F5: the disposition rationale must NAME the introducing artifact and the matching content, so **an RE-ENTER-UPSTREAM attribution naming no introducing artifact reads as a guess on its face.**

**Origin — a SECOND observed incident, whose provenance is weaker than the benchmark's, and it must be stated that way.** Maintainer-reported 2026-08-18: on a consumer install of the current version, `/devforge:research` delivered a defective matrix/handoff conclusion, `/devforge:grill` **CAUGHT** the defect downstream, and the RE-ENTER-UPSTREAM attribution settled on `spec` — the stage that **TRANSCRIBED** the conclusion — so the seed targeted `spec`. **This is a conversational report, not an artifact in this repository:** that run's `grill.md` disposition lives in the consumer install, and **this paragraph is the record.** Do not cite it as benchmark evidence, do not merge it into the seven-step chain above, and do not go looking for a file. Its failure SIGNATURE is the chain's: the disambiguating fact — the handoff row — was on disk, and the inference stopped one artifact short of it.

**Targets, verified 2026-08-18:**
- `src/commands/grill/main.md:280` — PHASE 5's Q2 YES arm, and **the ONLY statement of the attribution rule in the command.** It already carries the correct clause: findings are "attributed to the NEAREST introducing stage", the trace is "trace via `spec.md` + the dossier", one of its own examples is "a bad requirement already in the research handoff → `research`", and it closes "nearest-stage-first, NOT a blanket rewind to research". **What is missing is the trace INPUT set and the transcription standard that make that research-handoff example actually fire** — nothing today requires the handoff to be opened. The build widens that one sentence: **one statement of the rule, not two.**
- Every other "nearest" occurrence is a **stage-token enumeration** and is **UNCHANGED by F6**: `src/commands/grill/main.md:287` (the `target_stage` composition bullet), `:324` (`--re-entry-target`), `:361` and `:364` (the PHASE 7 arms), and `src/commands/grill/references/report-format.md:182` (the report's stage cell). Each lists `spec` \| `discovery` \| `research`; **none states how the stage is chosen.**

**F6 is NOT a rewind-to-research default.** The `:280` sentence's closing clause survives the widening in substance: nearest-stage-first still governs, and a conclusion with no upstream source still attributes to `spec`. F6 changes what the trace must READ, not which direction it prefers.

**Why mis-attribution is severe rather than cosmetic — verified 2026-08-18.** A spec-targeted seed for a research-introduced defect **guarantees re-derivation.** The `/devforge:specify` re-entry run resolves the same feature directory and re-imports the same `research-handoff.json` — `src/commands/specify/main.md:104` is the pending-feature-dir glob over `specs/*/research-handoff.json` and `specs/*/discover-handoff.json`, `:125` is the `yes-most-recent` → `import-handoff` arm — and Phase 0.5 states in terms that the revision is "authored from the seed plus this run's Phase 1–3 inputs", the imported handoff among them. **Nothing in the seed consumer invalidates or regenerates the handoff.** So the mis-routed correction re-ingests the defective input: the stage that owns the error is never re-run, and the stage that merely transcribed it is asked to fix it from the same source.

**The downstream route already EXISTS and F6 does not build it.** `src/commands/research/main.md:137`–`:153` is Phase 0.6, "Re-entry from `/devforge:grill`": it globs `specs/*/grill-seed.json`, matches `target_stage == "research"`, treats the seed as a **binding directive**, and has Phase 4 save in attach mode (overwriting that feature's artifacts in place). **F6 makes an already-shipped route REACHABLE by correct attribution.** A phase that adds anything to that route has left this fix.

**Relationship to F4 — detection-time complement, not overlap.** F4 prevents the false surface label at intake; F6 ensures that when `/devforge:grill` catches a false label's CONSEQUENCE downstream, the correction routes to the stage that owns it. **F6 is remediation ROUTING, not defect prevention** — which is why D2 orders it last.

**Relationship to plan 83 (`83-DOWNSTREAM-REENTRY-SEED-PLAN.md`) — no collision, and a future session must not read the two plans as conflicting.** Plan 83's non-goal *"Any change to `/devforge:grill` or `/devforge:spec-check` behavior"* is **plan 83's own scope statement about itself** — it stays true of plan 83 and it does not bind this plan. F6's grill edit belongs to plan 81, and `src/commands/grill/main.md` is **not in plan 83's file set** (`src/devforge/lib/_fix/`, `src/commands/fix/main.md`, `src/commands/specify/main.md` prose, and one glob in `src/commands/plan/main.md`). Two of those files ARE this plan's — F3 edits `specify/main.md`, F1/F2/F5 edit `plan/main.md` — so whichever plan lands second re-reads those two **as landed** — the same discipline this plan's second tripwire imposes between its own Phases 2 and 3. **The grill edit collides with nothing.** Both plans are NOT STARTED.

*Counter-argument, recorded — two, and the second is not answered.* (i) Reading two handoff JSONs is extra work on the classify step. The defence is that it is bounded — two flat JSON files already sitting in the feature directory, at a step that already traces via `spec.md` + the dossier — and that it is paid **only on the RE-ENTER-UPSTREAM branch**, the rare arm. (ii) A transcription may be paraphrased rather than copied, so content-matching is a judgment call, and a lexical miss still mis-attributes. **That is accepted and recorded as a residual rather than argued away**, in OQ-2's shape one command over: **F6 narrows the miss surface — today the handoffs need not be opened at all — and does not close it.** Do not report it as closed.

---

## Decisions (Phase 0 ratification recorded 2026-08-18 — each item below carries its confirm inline)

- **D1 — instruction-only scope.** **RATIFIED 2026-08-18 as written, both tripwire halves.** Zero Python, zero schema fields, zero helper verbs, zero new check numbers **AND zero new unnumbered hard-fail validators.** Both criteria are plan 75's tripwire, and the second is load-bearing: plan 73 shipped two hard-fail gates carrying no check number at all, so a grep for `Check N` would pass an imitation that violates the tripwire in substance. All six fixes are inference rules attached to forcing steps that already fire. *Counter:* an instruction-only fix is skippable by construction, and four of this plan's six sites already carry an instruction that fired correctly — so "another sentence" is a weak instrument. **F6's site sharpens that counter rather than answering it:** its instruction fired, produced an attribution, and the attribution was wrong. The defence is the failure's own shape: nothing here failed to run. The facts were computed and the conclusions drawn from them were wrong, and a conclusion is not the kind of thing a mechanical gate adjudicates.
- **D2 — priority order F4 → F1 → F2 → F3 → F5 → F6.** **RATIFIED 2026-08-18 as written — the order and the defence-in-depth (not chain) reading, F6's last place included.** F4 is the root; F1, F2 and F3 each catch F4's failure downstream **independently**, so the set is defence in depth rather than a chain. F5 is next-to-last because it catches the discharge, which is the least load-bearing link of the design — by the time it fires the design is already wrong. **F6 is last because it is remediation ROUTING rather than defect prevention:** it fires only when a defect has already escaped every fix above it AND the opt-in, human-typed `/devforge:grill` was run — the narrowest trigger in the set, and the only one downstream of the design itself. *Counter:* shipping F4 alone would be the cheapest test of the root-cause claim, and the other five are then unmeasured additions. The defence is D6's acceptance test, which cannot attribute across six fixes either way, and the fact that F1–F3 are independently justified by the chain rather than by F4's failure — with F6 independently justified by a second observed incident rather than by the chain at all.
- **D3 — plan-77 disposition: KEEP AND AMEND, and this plan is the amendment.** **RATIFIED 2026-08-18 TOGETHER WITH the honest bound below — an "after" with no "before"; the discovery vindication is consistent-with, not a demonstration.** The external benchmark effectively supplied plan 77's waived measurement, and its reading is split: **the matrix is VINDICATED on discovery** (it named the coupled call site 16 of 20 runs missed) and **the probe FAILED on handling.** Under plan 77's retired D6 a non-flipping probe was the delete branch; the evidence supports keep-and-amend instead, because the discovery value is now measured and the failure is localized to named inference steps rather than to the artifact. **Recording this supersedes nothing in plan 77's file — that plan's entry stays as-is**, and Phase 6 adds a short cross-reference amendment to its `PLAN-STATUS-ARCHIVE.md` entry (with the `CLAUDE.md` one-liner kept in sync), drafted at that phase and not now.
  **⚠ Honest bound, and it corrects a natural reading of the sentence above.** What ran is plan 77's Phase-3 ARM — a matrix-present run — with **no Phase-1 baseline**, because no blind v2-without-matrix run on this ticket exists. So this is an "after" with no "before". Under plan 77's own OQ-6 bound, one run cannot separate "the rule worked" from "this sample landed differently"; here it additionally cannot separate matrix-attributable discovery from v2's other post-v1.28 gains. **The discovery vindication is consistent with the matrix working and is not a demonstration that it did.** Do not restate it as one.
- **D4 — F3 takes ownership of the file-less preservation-AC finding.** **RATIFIED 2026-08-18 as written, with the residual recorded: the class moves from unowned-and-prose to owned-and-prose.** The two AC failure shapes are siblings handled by one admission rule: **pins-a-removed-value** (a conflict flag wearing a regression pin's clothes, the finding's original subject) and **unreachable-subject-state** (an unfalsifiable guard, this run's AC-2). Both are answered by requiring the subject state's reachability before the AC is admitted as preservation. *Counter:* the finding's own text names `/devforge:spec-check` as the natural mechanical home and observes that a prose directive is skippable; F3 is prose, so the finding's central complaint survives its own resolution. That is accepted and recorded rather than argued away — **F3 moves the class from unowned-and-prose to owned-and-prose**, and OQ-1 is where a mechanical successor would be decided.
- **D5 — no `src/constitution.md` edit.** **RATIFIED 2026-08-18 as written — and the FALSE BINARY finding REMAINS OPEN; nothing in this ratification settles it.** The FALSE BINARY finding stays **open and untouched**, and this plan does not settle, close, moot or weaken it. **F1, IF ratified and IF validated at Phase 7, becomes a candidate route for it — and that entry's "no designated route" statement stands until then.** *Counter, which is real:* §3.6's Narrowing rule is cited at three enforcement sites (`src/commands/plan/main.md` sub-question 7 and its echoes, `src/agents/architect.md` Rule 9, and the constitution itself at `:121`–`:125`, all verified 2026-08-17), so "no change" is not costless — the rule keeps steering toward the caller-scoped opt-in the benchmark's guard-shape axis rejects. The defence is the run: the intrinsic form WAS considered and was rejected on the phantom AC's authority, so removing the preference would not have changed the outcome while adding an unmeasured constitution edit to an unmeasured plan.
- **D6 — acceptance test: re-run the frozen benchmark prompt (Phase 7).** **RATIFIED 2026-08-18 as written: model pinned to `claude-fable-5`; the two greps are manual observations, never gates; F6's separate anchor recorded as a third manual observation.** **Pass** = the hidden surface stops emitting the removed values **WITHOUT the prompt naming it** and **WITHOUT that surface's component file appearing in the diff** — a predicate change inside the shared builder, not a call-site sweep. **The model must be PINNED for the re-run.** This run was on `claude-fable-5`; all v1 benchmark runs were on `claude-opus-5`. That is a live confound and pinning it is the control. **Two cheap secondary checks, recorded as MANUAL e2e observations and explicitly NOT mechanical gates:** grep the run's artifacts for a `varies` matrix value cell lacking an enumerated value set, and for a preservation AC lacking a cited construction site. **F6 is not exercised by this re-run unless the operator invokes `/devforge:grill`** — it is opt-in and human-typed-only, so its own known-answer anchor is separate and is recorded at Phase 7 as a third manual observation, not as a gate. *Counter:* one run cannot attribute across six fixes, and a pass is consistent with any subset of them working. Accepted — Phase 7 is a HARD GATE on the outcome, not an attribution instrument, and the plan says so rather than implying otherwise.

---

## Open questions (Phase 0 — resolutions recorded 2026-08-18)

- **OQ-1 — does F3's reachability citation ever warrant a mechanical detector?** **RESOLVED 2026-08-18: NO for v1 — prose-first, per the recommendation, with the counter (the skipping population writes this AC) recorded and accepted; a mechanical successor is a separate plan with its own measurement.** *Recommendation: **no for v1** — prose-first, on plan 66's Narrowing reasoning* (that rule shipped as prose with its mechanical detector deliberately deferred until an empirical miss-rate justified it). **Counter, stated fairly:** the preservation-AC finding's own argument is that a prose directive is skippable and that the specs producing this AC are the ones whose authors were confident — which is the population least likely to read the directive. Deciding "no" accepts a known-skippable fix for a known-skipping population. **This is the maintainer's call**, and revisiting it is cheap: the mechanical form is a separate plan with its own measurement, not a phase here.
- **OQ-2 — can a prose trigger ever be made non-dodgeable?** **RESOLVED 2026-08-18: the role key (F3(a)) is adopted as MITIGATION with the residual recorded — the author picks the subsection, so the dodge surface narrows and does not close; never report it as a solution.** *Honest answer: **no.*** A rephrasing can always slip a lexical trigger, and the run is the demonstration — plan 77's R3 directive was present, correct, and dodged by framing. **The mitigation is F3(a): key the requirement on the AC's ROLE (the `behavior_preservation` subsection the author declares) rather than on its phrasing.** That is strictly better than a lexical key and still not closed, since the author picks the subsection. Record the residual; do not report the role key as a solution.
- **OQ-3 — where exactly does F5's verify-side seam land?** **RESOLVED 2026-08-18: decided at Phase 5 after reading both live files in full, `ac-verifier.md` Rule 14 the leading candidate; a seam outside those two files fails the phase and returns to Phase 0.** **SEAM DECIDED at Phase 5 build (2026-08-18, commit `92eadfb`): the agent rule — `src/agents/ac-verifier.md` Rule 14, appended after Rule 13 — plus the plan-side landing in `src/commands/plan/main.md` PHASE 2.5 step 2 (third bullet) with a matching one-clause carve-out at PHASE 1.5's `[PLAN COVERAGE:]` marker line in the same file (an intra-file contradiction the review surfaced; same file, so the file set is unchanged). No file outside the named set was touched.** Plan-side only, or also `ac-verifier` guidance? *Recommendation: decide at build (Phase 5) after reading both live files*, with `src/agents/ac-verifier.md` Rule 14 as the leading candidate over a line in `src/commands/verify/main.md:180`'s brief composition. **Counter:** deferring a scope decision into a build phase is how scope grows mid-phase, which is the accumulation pattern this repo has documented. Mitigation: the Phase-5 Verify criterion names the file set as landed, and a seam outside those two files returns to Phase 0.

---

## Non-goals (explicit)

- **Any new verification layer, stage, agent, gate, check number or unnumbered validator.** This is D1 and it is the plan's thesis, not a scope preference.
- **Any change to `src/constitution.md`** (D5).
- **Any change to `/devforge:spec-check`.** It behaved correctly in the run — an unfalsifiable AC cannot conflict with anything — and its advisory stance is ratified (plan 62 D14). *(Reconciled 2026-08-19: this non-goal was HONOURED — no phase of this plan touched that command. A SEPARATE plan later did: `82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md` ratified its D6 and amended D14 in place, so `/devforge:spec-check` is now run-mandatory before `/devforge:plan` with its verdict still non-binding. The bullet stands as this plan's scope statement; it is not a claim about that command's present stance.)*
- **Any change to plan 71's shipped dead-code chain** — sub-question 9, `### Change-Induced Dead Code`, `DeadCodeRow`, `verify-dead-code-coverage`, `check-dead-code-removal`, the `**Dead code removal**:` task field. This plan neither feeds nor touches it.
- **Any change to plan 77's emission-matrix accounting machinery** — `src/commands/plan/main.md:370` sub-question 11 and `:539` PHASE 2.5 step 8. F2 sharpens what a cell must contain; it changes no accounting rule.
- **Any change to `/devforge:grill`'s gating, seed schema, disposition set or verdict ownership, and any change to `/devforge:research` Phase 0.6.** F6 widens ONE sentence inside PHASE 5's existing Q2 arm. `/devforge:grill` stays opt-in and human-typed-only, the 4-way disposition set stays as it is, the USER still owns the verdict at the `/devforge:breakdown` gate, and the consuming route stays exactly as shipped — F6 makes it reachable, it does not touch it.
- **Improving discovery.** Discovery worked in this run. Every phase here is downstream of it.
- **Re-running or migrating the benchmark's source material.** It is the evidence record.
- **Settling the FALSE BINARY finding** (D5).

---

## The named risk to this plan

**Six fixes across six files under one acceptance test is more surface than plan 77 carried, and plan 77's named risk was phase accumulation.** The six, so the count is checkable rather than asserted: `src/commands/research/main.md`, `src/commands/plan/main.md`, `src/agents/architect.md`, `src/commands/specify/main.md`, F5's verify-side seam file (the count holds under either OQ-3 candidate — both are files no other fix touches), and `src/commands/grill/main.md`. This plan is written inside that pattern and says so — and F6 was added on 2026-08-18, after the first draft, which is the accumulation pattern happening to this plan rather than inside it.

The concrete form the drift will take here: **a build phase will want to convert an inference rule into a check.** F3's reachability citation is one `grep` away from looking mechanizable; F1's identical-tuple condition is one helper verb away from looking gateable. Each is defensible in isolation and each contradicts the finding this plan rests on — that every mechanism in the run executed correctly and the conclusions were still wrong.

**Tripwire, stated as a Verify criterion in every build phase rather than as a note, because a note would not survive the pull:**

> **No new mechanical check, helper verb, schema field, exit code, check number or unnumbered hard-fail validator appears in any phase's diff.** A build session that finds itself needing one stops and returns to Phase 0 — that is a different plan with a different measurement. **Both halves are checked**, per plan 75: a `Check N` grep is not sufficient, because a validator can hard-fail without carrying a number.

A second tripwire, specific to this plan's shape: **F1's and F2's edits land in the same two files** (`src/commands/plan/main.md:443` and `src/agents/architect.md:153` Rule 9). Phase 3 edits sentences Phase 2 just wrote. **Phase 3 re-reads the file as landed and widens Phase 2's text; it does not re-draft from this plan's description of it.** A Phase 3 that produces a second, parallel statement of the same rule has accumulated rather than widened.

---

## Build discipline

- **Every file this plan edits ships into a consumer's `.claude/`.** `src/commands/*/main.md` → `.claude/commands/devforge/<name>.md`; `src/agents/*.md` → `.claude/agents/<name>.md`. **Every edit in Phases 1–5b routes through instruction-author → instruction-reviewer AND a claude-code-guide check.** No exception for size — a one-sentence rule ships the same way a section does.
- **Plan vocabulary NEVER ships into a consumer's `.claude/`.** "Inference rule", "the visibility bar", "the causal chain", D-numbers, F-numbers and this plan's phase numbers are maintainer vocabulary. Emitted text may reference only each command's own phases, sub-question numbers, rule numbers, and the constitution's own rule names.
- **The privacy constraint at the top binds every phase, not just drafting.**
- **Append, never renumber.** `src/commands/plan/main.md` carries sub-questions 1–11 (`:360`–`:370`, verified 2026-08-17) and PHASE 2.5 steps 1–8 (`:528`–`:539`); `src/agents/ac-verifier.md` carries Rules 1–13 (`:125`–`:137`). Anything added lands after the last existing number, and every cross-reference to a number elsewhere in `src/` is reconciled against the file as landed.
- **Re-verify every anchor at use time.** The table below was correct on 2026-08-17 against an uncommitted working tree. This repo has documented anchor rot — **grep the quoted string, never the `:NNN`.**
- Every load-bearing claim added during execution carries a `file:line` anchor **or** is marked an open item. Do not invent verb names, check numbers, counts or line numbers.

---

## Verified anchors (2026-08-17; the four F6 rows 2026-08-18)

Every anchor below was read at the position stated. **The quoted token is the anchor; the digit is a dated hint.**

| Anchor | What is there |
|---|---|
| `src/commands/research/main.md:505` | `**Step 2b — Trace each caller to its surface and classify scope.**` — block runs `:505`–`:532` |
| `src/commands/research/main.md:515` | 8-hop bound to "the first user-facing entry point"; `"none"` sentinel rules |
| `src/commands/research/main.md:520`–`:526` | the `classify-caller-scope` setter call: `--surface`, `--scope`, `--justification` |
| `src/commands/research/main.md:528` | "the `--justification` MUST cite it by name" when an entry point was found |
| `src/commands/research/main.md:530` | the honesty bound: forces the classification to EXIST, cannot force it to be CORRECT |
| `src/commands/research/main.md:1123` | `### Emission matrix (CONDITIONAL — …)` — the plan-77 production step |
| `src/commands/research/main.md:1146`–`:1160` | the six numbered **composition steps** (1–6) |
| `src/commands/research/main.md:1158` | **composition step 5**: `varies` → Note states which values were considered + what blocked the trace; **verdict recorded `affected`** |
| `src/commands/research/main.md:1162`–`:1170` | `**The rules this matrix must satisfy**` — Rules **1, 2, 3, 4, 6**; `:1170` states "There is no rule 5 in this step" (rule 5 is `/devforge:plan`'s consumption rule). **Steps and Rules are two different lists with overlapping numbers — never conflate them.** **⚠ `:1170`'s onward cross-reference does not land where it says.** It claims rule 5 governs how `/devforge:plan` CONSUMES the matrix and "is stated there"; verified 2026-08-17, `grep -n "Rule 5" src/commands/plan/main.md` returns **exactly one** hit — `:443`, the impossibility-rejection note — whose subject is what the Alternatives Rejected column may contain, **not** matrix consumption. The consumption content EXISTS but carries **no rule label**: sub-question 11 (`:370`) and PHASE 2.5 step 8 (`:539`). **Pre-existing plan-77 residual, NOT introduced by this plan and NOT this plan's to fix** — a build session must neither graft matrix-consumption language onto `:443` nor hunt for a labelled rule that is not there. |
| `src/commands/research/main.md:1165` | **Rule 2**: "the evidence cells are traced, never asserted" |
| `src/commands/plan/main.md:350` | the architect brief file list carries `specs/<feature>/emission-matrix.md` |
| `src/commands/plan/main.md:366` | sub-question 7 — the Narrowing / caller-scoped-vs-layer-wide question |
| `src/commands/plan/main.md:370` | sub-question 11 — matrix currency + **accounting**; a `varies` cell "is an `affected` row … accounted for like any other" |
| `src/commands/plan/main.md:443` | **Rule 5** — an impossibility rejection "must name the arguments the function in question actually receives and show the impossibility claim against them" |
| `src/commands/plan/main.md:528`–`:534` | PHASE 2.5 steps 1–3 — AC coverage checked against "Layer Map" and "File Impact" (**F5's real plan-side seam**) |
| `src/commands/plan/main.md:539` | PHASE 2.5 step 8 — the emission-matrix accounting backstop |
| `src/commands/plan/main.md` (whole file) | **NO test-boundary and NO verification-strategy section exists** — grep for `test` returns `:367`, `:461`, `:559`, all property-test lane |
| `src/agents/architect.md:153` | Rule 9 — six forcing steps incl. **Rejected-alternative checkability**, whose worked example is the run's own derived fact |
| `src/commands/specify/main.md:619` | plan 77's R3 directive, in full, naming the "we did not intend to touch that file" trap |
| `src/commands/specify/main.md:637`, `:648` | `add-ac --subsection` carries `behavior_preservation` → **§5.2 Behavior preservation** (F3's role key) |
| `src/commands/specify/main.md:244`–`:254` | §1.8 — the conditional `emission-matrix.md` read, with the `Verdict` vocabulary restated |
| `src/agents/ac-verifier.md:125`–`:137` | Rules 1–13; Rule 9 (`:133`) evidence-is-mandatory; Rule 13 (`:137`) the plan-34 negative-grep rule |
| `src/commands/verify/main.md:180` | PHASE 3.3 — the `ac-verifier` brief composition site |
| `src/constitution.md:121`–`:125` | the Narrowing block — caller-scoped opt-in `:122`, fallback `:123`, layer-wide naming `:124`, tie-breaker `:125` (**untouched by this plan, D5**) |
| `src/commands/grill/main.md:280` | **(verified 2026-08-18)** PHASE 5's Q2 YES arm — "attributed to the NEAREST introducing stage", "trace via `spec.md` + the dossier", the example "a bad requirement already in the research handoff → `research`", and the closing "nearest-stage-first, NOT a blanket rewind to research". **The ONLY statement of the attribution rule, and F6's single edit site.** |
| `src/commands/grill/main.md:287`, `:324`, `:361`, `:364`; `src/commands/grill/references/report-format.md:182` | **(verified 2026-08-18)** every other "nearest" occurrence in the command — `target_stage` composition, `--re-entry-target`, the two PHASE 7 arms, and the report's stage cell. All are **stage-token enumerations** (`spec` \| `discovery` \| `research`); none states how the stage is chosen. **F6 leaves them unchanged.** |
| `src/commands/research/main.md:137`–`:153` | **(verified 2026-08-18)** Phase 0.6 "Re-entry from `/devforge:grill`" — globs `specs/*/grill-seed.json`, matches `target_stage == "research"`, treats the seed as a binding directive, saves in attach mode. **The route F6 makes reachable; F6 builds nothing here.** |
| `src/commands/specify/main.md:104`, `:125`, `:148` | **(verified 2026-08-18)** the pending-feature-dir glob over `specs/*/research-handoff.json` + `specs/*/discover-handoff.json` (`:104`), the `yes-most-recent` → `import-handoff` arm (`:125`), and Phase 0.5's "authored from the seed plus this run's Phase 1–3 inputs" (`:148`). **Why a mis-attributed `spec` seed re-ingests the defective upstream input.** |

---

## Phase 0 — Maintainer ratification (decision gate, no code)

**COMPLETE 2026-08-18.** All ten items (a)–(j) confirmed by the maintainer as recommended, no overrides. The per-item records live inline: D1–D6 in the Decisions section, OQ-1–OQ-3 in the Open-questions section, item (j) at the top of F6's own section. No `src/` file was edited before this ratification.

Present this plan. The maintainer confirms, or overrides with a recorded reason:

(a) **D1** — instruction-only scope, both tripwire halves;
(b) **D2** — the F4 → F1 → F2 → F3 → F5 → F6 order, and defence-in-depth rather than a chain;
(c) **D3** — keep-and-amend for plan 77, **together with its honest bound** (an "after" with no "before"; the discovery vindication is consistent-with, not a demonstration);
(d) **D4** — F3 owns the file-less preservation-AC finding, and the residual that it moves the class from unowned-prose to owned-prose;
(e) **D5** — no constitution edit; the FALSE BINARY finding stays open and untouched, with F1 as a candidate route only after Phase 7;
(f) **D6** — the acceptance test, the diff-shaped pass criterion, **the pinned model**, and the two greps as manual observations rather than gates;
(g) **OQ-1** — no mechanical detector for F3 in v1 (recommended), against the counter that the skipping population is the one that writes this AC;
(h) **OQ-2** — the role key as mitigation, with the residual recorded and not reported as a solution;
(i) **OQ-3** — F5's verify-side seam decided at Phase 5 after reading both files, with a seam outside those two files returning here;
(j) **F6** — attribution traces to introduction rather than restatement, **its second-incident origin** (a maintainer-reported consumer run of 2026-08-18, conversational, with no artifact in this repository) and its recorded residual that paraphrased transcription can still mis-attribute. **F6 carries no D-number of its own, which is why it needs this item**; its place in the priority order is item (b)'s to confirm, stated there in full and deliberately not restated here.

Until ratification, no build phase is authored and no `src/` file is edited.

### Verify

- Every decision D1–D6 and every open question OQ-1–OQ-3 carries a recorded confirm-or-override, inline in this file.
- **Item (j) carries its own recorded confirm-or-override.** The 2026-08-18 amendment deliberately added no D-number and no OQ-number, so a ratification recorded only against D1–D6 and OQ-1–OQ-3 would leave F6 unratified while looking complete.
- **The D3 pick is recorded together with its bound** — a bare "keep and amend" without the no-baseline caveat records a stronger claim than the evidence carries.
- **The D5 pick is recorded together with the statement that the FALSE BINARY finding remains open**, so no later session reads ratification here as having settled it.
- No `src/` file has been edited.

---

## Phase 1 — F4: derived surface labels (instruction-author → instruction-reviewer + claude-code-guide)

**File:** `src/commands/research/main.md`.

Add the derivation standard to Step 2b (`:505`–`:532`), beside the existing entry-point-citation rule at `:528` rather than replacing it: the `--surface` value is derived from the caller's construction sites — who builds it and with which dependencies — and a label taken from a resembling lane, tab, route or mode name is not derived. Where construction sites cannot be established within the block's existing 8-hop bound, the label says so and the justification records what was traced, in the shape `:515` already uses for the `"none"` case.

Reconcile the matrix composition text (the steps at `:1146`–`:1160` and the rules at `:1162`–`:1170`) where it reads a caller's recorded `surface` as context (`:1148`), so the two sites state the same standard for the same value.

### Verify

- Instruction-reviewer clean; claude-code-guide clean; **no plan vocabulary in the emitted text.**
- **The tripwire holds, both halves**: no new check number and no new unnumbered hard-fail validator in the diff; `git diff --name-only` returns exactly `src/commands/research/main.md`.
- The existing `--surface` / `--scope` / `--justification` setter signature is **unchanged** — this phase adds no argument and no verb.
- The entry-point-citation rule at `:528` and the honesty bound at `:530` are **still present and unweakened**; the derivation standard sits beside them.
- Cross-check sweep: `grep -rn "classify-caller-scope\|surface" src/` reconciles — the research-side standard and the `/devforge:plan` sub-question 7 caller-rendering text (`:372`) do not contradict each other.

---

## Phase 2 — F1: the identical-tuple rule (instruction-author → instruction-reviewer + claude-code-guide)

**Files:** `src/commands/plan/main.md` (Rule 5, `:443`) and `src/agents/architect.md` (Rule 9's Rejected-alternative checkability forcing step, `:153`).

State the inference at both sites, in each site's own vocabulary: an identical **reachable** tuple presented by two call sites defaults to one lane; identical reachable tuple + opposite required outputs = an AC conflict escalated as a product question (the architect's Rule 6 termination route already exists for spec-level ambiguity); a discriminator parameter is admissible only after the sites are shown genuinely distinct, and an AC asserting one must not change is not that showing.

**Do not add a column, a table, or a subsection.** Rule 5's own closing sentence — "This constrains what the existing Alternatives Rejected column may contain; it adds no column and no table" — is the shape to preserve.

### Verify

- Instruction-reviewer clean; claude-code-guide clean; no plan vocabulary in the emitted text.
- Tripwire holds, both halves; `git diff --name-only` returns exactly the two files named above.
- **No new column, table or subsection** appears in the plan template; Rule 5 stays a bracketed note under the Key Design Decisions table.
- The architect's worked example at `:153` still reads as an example of a **checkable rejection** — the phase adds what follows from the fact, and does not turn the example into a rejected-design illustration.
- The escalation route named in the emitted text is the one that exists (`architect.md` Rule 6 termination / escalate-to-user), verified by grep, not asserted.

---

## Phase 3 — F2: value sets, not expressions (instruction-author → instruction-reviewer + claude-code-guide)

**Files:** `src/commands/research/main.md` (**Rule 2**, `:1165`) and the two Phase-2 sites as landed.

**Read all three sites as they stand after Phases 1–2 before drafting** — this phase widens Phase 2's sentences; it does not restate them.

Research side: the standard for what makes an evidence cell traced rather than asserted — a cell reads as the reachable value set, and a cell naming an expression, a parameter, or a name standing for its values is an assertion. **`varies` is untouched**: composition step 5 at `:1158` already requires the considered-values statement and already records the conservative verdict, and this phase must not duplicate, restate or tighten it.

Plan side: a Rule 5 impossibility rejection states each named argument's reachable value set, not an expression that stands for it — which is what makes "the two callers present the same tuple" a checkable claim rather than a plausible one.

### Verify

- Instruction-reviewer clean; claude-code-guide clean; no plan vocabulary.
- Tripwire holds, both halves; `git diff --name-only` returns exactly the three files.
- **`varies` is still permitted** at `src/commands/research/main.md:1158`, its considered-values requirement appears **once** in the file, and the `affected` default verdict is unchanged. A diff that bans `varies`, or that states its Note requirement a second time, fails this phase.
- **The accounting machinery is byte-unchanged**: `grep -rn "affected" src/commands/plan/main.md` shows sub-question 11 (`:370`) and PHASE 2.5 step 8 (`:539`) making the same claims as before the change.
- The plan-side value-set requirement reads as a widening of the sentence Phase 2 landed — one statement of the rule, not two.

---

## Phase 4 — F3: preservation-AC admission (instruction-author → instruction-reviewer + claude-code-guide)

**File:** `src/commands/specify/main.md`.

Widen the trigger at `:619` from value-presence phrasing to the **role** an AC enters under, keyed on the `behavior_preservation` subsection (`:637`, `:648`), and add the reachability-citation requirement: an AC entering §5.2 cites the construction site producing the state it preserves. Where none can be cited, route the AC to §8 Open Questions with its §9 Risks finding — the route `:619` already prescribes for the matrix's non-empty-intersection case, reused rather than re-invented.

State both bounds in the emitted text: the plan-62 D9 parallel (a permitting case counts only when asserted reachable) and the dynamic-dispatch bound on static reachability. **Add nothing about `/devforge:spec-check`** beyond what is already there.

### Verify

- Instruction-reviewer clean; claude-code-guide clean; no plan vocabulary.
- Tripwire holds, both halves; `git diff --name-only` returns exactly `src/commands/specify/main.md`.
- **The `add-ac` interface is unchanged** — no new argument, no new subsection key, no new enum value. `grep -n "subsection" src/commands/specify/main.md` returns the same seven keys.
- The R3 directive at `:619` is **widened, not replaced** — the quoted-product-intent requirement and the named inferred-intent trap both survive verbatim in substance.
- The emitted text states the dynamic-dispatch bound, so a reader cannot take a cited construction site as proof of exhaustive reachability.
- **No text proposing, implying or preparing a strengthening of `/devforge:spec-check` appears in the diff.**

---

## Phase 5 — F5: behavioral ACs and file-layer discharge (instruction-author → instruction-reviewer + claude-code-guide)

**Files:** `src/commands/plan/main.md` (PHASE 2.5 steps 1–3, `:528`–`:534`) and the verify-side seam OQ-3 selects.

**Read `src/agents/ac-verifier.md` and `src/commands/verify/main.md` in full before deciding the seam.** Recommendation on file: `ac-verifier.md` Rule 14, appended after Rule 13 (`:137`).

Plan side: an AC about emitted output is covered when the plan names the behavior-changing decision that satisfies it; matching its files against Layer Map / File Impact does not cover it, and an unchanged file set is not evidence about behavior.

Verify side: the same rule as a verdict standard — a `PASS` on a behavioral AC rests on evidence about the emitted output at the asserted path, and the absence of a diff in some file set is not that evidence.

### Verify

- Instruction-reviewer clean; claude-code-guide clean; no plan vocabulary.
- Tripwire holds, both halves; `git diff --name-only` returns exactly the files named in the seam decision recorded at this phase — **a file outside that set fails the phase and returns to Phase 0** (OQ-3).
- PHASE 2.5's step numbering is **appended, not renumbered**: steps 1–8 keep their numbers and every cross-reference to a step number elsewhere in `src/` still resolves.
- If the `ac-verifier` seam is taken, the new rule is **Rule 14** and Rules 1–13 keep their numbers and text.
- The emitted text does not forbid file-level evidence generally — it forbids it as a **discharge of a behavioral claim**. A diff that reads as "file evidence is invalid" fails this phase.

---

## Phase 5b — F6: attribution traces to introduction (instruction-author → instruction-reviewer + claude-code-guide)

**File:** `src/commands/grill/main.md`.

**Why a letter and not a number.** Phases 6 and 7 are cited **by number outside this file** — the repo-root `CLAUDE.md` ledger line for this plan names "Phase 7 = user-driven HARD GATE" — so this phase takes a letter suffix rather than renumbering them. This is the same append-never-renumber discipline the Build-discipline section applies to `src/` numbering, applied to this file's own phases.

Widen the ONE sentence that states the attribution rule — PHASE 5's Q2 YES arm, the sentence carrying "attributed to the NEAREST introducing stage" — so that it states two things it does not state today: (1) the feature's `research-handoff.json` and `discover-handoff.json` (where present) are **MANDATORY trace inputs** alongside `spec.md` + the dossier, and (2) the transcription standard — where the invalidated conclusion's substance appears in an upstream handoff, the introducing stage is that upstream artifact's stage, and `spec` is the introducing stage only when the conclusion has no upstream source. **Grep the quoted string to find it; do not navigate by `:280`.**

In the same sentence's terms, add the rationale duty: an RE-ENTER-UPSTREAM rationale **NAMES the introducing artifact and the matching content.** That is what makes a guessed attribution visible on the artifact's face.

**Add nothing to `/devforge:research` Phase 0.6.** The consuming route already exists (see F6's section) and is not this phase's to touch — F6 makes it reachable, it does not build it.

### Verify

- Instruction-reviewer clean; claude-code-guide clean; **no plan vocabulary in the emitted text.**
- **The tripwire holds, both halves**: no new check number and no new unnumbered hard-fail validator in the diff; `git diff --name-only` returns exactly `src/commands/grill/main.md`.
- **The Q1/Q2 decision-tree structure is unchanged** — Q1 is untouched, Q2 keeps its YES/NO arms, no third question appears, and the 4-way disposition set (PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL) is unchanged.
- **"nearest-stage-first, NOT a blanket rewind to research" survives** — a diff that reads as a research default fails this phase.
- **The stage-token enumerations are byte-unchanged**: the `target_stage` composition bullet, the `--re-entry-target` bullet and both PHASE 7 arms carry the same text, and `src/commands/grill/references/report-format.md` appears in **no** diff for this phase.
- **ONE statement of the rule, not two** — the widening lands inside the existing sentence. A second, parallel statement elsewhere in the file is the accumulation this plan's second tripwire names.
- No helper verb, no `write-seed` argument and no seed field is added; `target_stage`'s four accepted values are unchanged.

---

## Phase 6 — Docs reconcile

- `PLAN-STATUS-ARCHIVE.md` (full entry) + repo-root `CLAUDE.md` (one-liner, kept in sync): this plan's status entry moves from NOT STARTED to the shipped wording, stating which phases landed and that Phase 7 is the outstanding gate.
- **Both ledger surfaces already carry F6's CONTENT** — the 2026-08-18 amendment added it to the `CLAUDE.md` one-liner and appended a dated addendum to the `PLAN-STATUS-ARCHIVE.md` entry, both in NOT-STARTED wording. **This phase updates their STATUS, not their content**: do not re-describe F6 from scratch, and do not remove the addendum — amend it, in the same amend-never-rewrite shape the plan-77 bullet below prescribes.
- `PLAN-STATUS-ARCHIVE.md` (full entry) + repo-root `CLAUDE.md` (one-liner, kept in sync): **the plan-77 entry gains a short cross-reference amendment** recording D3's keep-and-amend disposition and its no-baseline bound. **Drafted at this phase, not before**, and written as an amendment — plan 77's entry is not rewritten and no sentence in it is withdrawn.
- `FINDINGS.md` finding 4: **the file-less preservation-AC finding entry is amended, not replaced**, to record F3's ownership. Its "NOTE ON THIS ENTRY'S SHAPE" paragraph is not touched — the fifth file-less finding back-references it — and no finding is renumbered.
- `FINDINGS.md` finding 1 (the §3.6 Narrowing FALSE BINARY entry; the file-less findings were relocated out of repo-root `CLAUDE.md` into `FINDINGS.md` on 2026-08-17): its 2026-08-17 amendment already records F1 as a CANDIDATE route conditional on Phase-0 ratification AND Phase-7 validation. **Update it to whichever outcome landed** — route LIVE (both conditions met, and the entry's "without any designated route" statement is superseded) or route DEAD (either condition failed, and that statement stands unchanged) — **amending, never replacing**, and leaving the finding open either way: a live route is a route to a decision, not the decision. If Phase 7 has not run, the amendment says exactly that rather than implying the route is settled.
- `CHANGELOG.md`.
- `src/CLAUDE.md` **only if** a command's user-visible contract changed. If all six fixes are internal reasoning standards with no change to what a user is asked or shown, that file is untouched and **the no-op is recorded as deliberate**. F6 is the case worth checking rather than assuming: that file's `/devforge:grill` catalog entry describes the seed and its routing, so read it before recording the no-op.
- Cross-ref sweep across `src/` and `tests/` for every rule number, sub-question number, step number and subsection key the six build phases touched.

### Verify

- Sweep returns zero dangling references; full test suite green (**no test should have moved under D1 — a moved test is itself a finding**).
- The plan-77 amendment says **keep-and-amend with a bounded reading**, and does not restate the discovery result as a demonstration.
- The preservation-AC finding entry still carries its shape note, its ordinal, and its original text; the amendment is additive and dated.
- No plan vocabulary leaked into any file under `src/`.

---

## Phase 7 — Frozen-prompt re-run (user-driven, HARD GATE)

Re-run the frozen benchmark prompt against the framework with Phases 1–5b landed. **Pin the model** — this run was `claude-fable-5` and the v1 benchmark arm was `claude-opus-5`; an unpinned re-run measures the fixes and the model change together.

**Pass criterion (D6):** the hidden surface stops emitting the removed values, **without the prompt naming it**, and **without that surface's component file appearing in the diff** — a predicate change inside the shared builder, not a call-site sweep.

**Two manual observations, recorded whichever way the run lands, and NOT gates:** grep the run's artifacts for a `varies` matrix value cell with no enumerated value set, and for a preservation AC with no cited construction site.

**Read the plan's own machinery as part of the result**, since it is the subject: whether the surface labels carry construction evidence, whether any Rule 5 rejection states value sets, whether a §5.2 AC carries a construction-site citation, and whether any AC is discharged by a file-level observation.

**F6 is exercised by this re-run only if the operator invokes `/devforge:grill`.** It is opt-in and human-typed-only, so a frozen-prompt re-run that never invokes it leaves F6 **unobserved** — which is not a failure of F6 and must not be scored as one. **F6's own known-answer anchor is separate: a `/devforge:grill` re-run over the second incident's defective artifacts, expecting RE-ENTER-UPSTREAM attributed to `research`, a seed written with `target_stage="research"`, and `/devforge:research` Phase 0.6 consuming it.** Record that as a **MANUAL observation**, alongside D6's two greps and on the same footing — **not a gate.** The artifacts it needs live in a consumer install, not in this repository.

### Verify

- The pass criterion is scored **explicitly**, stating whether the hidden surface's file appears in the diff — not summarized.
- The pinned model is recorded with the result.
- Both manual observations are recorded, labelled as observations.
- **F6's status is recorded explicitly as observed or unobserved**, with whether `/devforge:grill` was invoked. Silence here reads later as a pass.
- **The attribution bound is recorded with whichever result lands:** one run across six fixes attributes nothing to any single one, and a pass is consistent with any subset of them working. Write the result in those terms.
- **If it fails**, record the negative here with the artifacts, and identify which link of the seven-step chain broke this time before proposing anything further. **A failed run is not a licence to add a gate** — that is the move D1 exists to refuse.

---

## Dependencies + related

- **Plan 77** (`77-POST-CHANGE-OUTPUT-MATRIX-PLAN.md`) — the direct predecessor. Its emission matrix produced the discovery this run converted into a wrong design, its R3 directive is the one F3 widens, and its finding **A4** is F4's SIBLING on the same `classify-caller-scope` call — a different field of it (A4 the free-text justification on an exclusion, F4 the surface label), **not a predecessor that already named F4's gap.** **D3 keeps and amends it; nothing in its file is edited by this plan.**
- **Plan 71** (`71-POST-CHANGE-CONSEQUENCE-PLAN.md`) — sub-question 9 and the dead-code chain. **Untouched; explicit non-goal.**
- **Plan 69** (`69-CALLER-ENUM-RESIDUAL-HARDENING-PLAN.md`) — WI-E built the Step 2b classification F4 constrains, and supplies the honesty stance F4 borrows: force the classification to exist, state openly that correctness cannot be forced.
- **Plan 67** (`67-CALLER-ENUMERATION-GATE-MODE-DECOUPLE-PLAN.md`) — made caller enumeration mode-independent, which is why the enumeration behind F4's labels ran at all on an enhancement-classified ticket.
- **Plan 62** (`62-SMT-REQUIREMENTS-CONSISTENCY-PLAN.md`) — `/devforge:spec-check`, which behaved correctly here. Its **D9** (a permitting case counts only when asserted reachable) is F3's direct parallel, and its **D14** (opt-in, advisory, never a gate) is the boundary this plan does not cross. *(Reconciled 2026-08-19: D14 was later amended in place by plan 82's ratified D6 — run-mandatory, verdict never binding. This plan still does not cross it; the parenthetical above describes D14 as of 2026-08-18.)*
- **Plan 66** (`66-PROPERTY-BASED-TESTING-AND-NARROWING-RULE-PLAN.md`) — the Narrowing rule D5 declines to edit, and the prose-first precedent OQ-1 leans on.
- **Plan 75** (`75-INVESTIGATION-SEARCH-HARNESS-PLAN.md`) — the unnumbered-validator tripwire D1 adopts in both halves, and the sibling stance: 75 argues the framework loses on curiosity rather than rigor. **This plan argues it can lose on inference while both curiosity and rigor hold** — the run investigated well, gated well, and concluded wrongly.
- **Plan 23** (`23-ADVERSARIAL-GRILLING-PLAN.md`) — built `/devforge:grill`, its 4-way disposition, and the verdict-gated `ReEntrySeed` machinery **F6 rides**. F6 changes no verb, no seed field and no disposition — only how the RE-ENTER-UPSTREAM stage is chosen.
- **Plan 36** (`36-GRILL-UNIVERSAL-REENTRY-PLAN.md`) — added `/devforge:plan` as the FOURTH `ReEntrySeed` consumer (`target_stage="plan"` for REVISE-PLAN), completing universal consumption across the four upstream commands. Context for the consumer set only: **F6 touches no consumer**, and the `research` consumer it depends on predates it (plan 23).
- **Plan 83** (`83-DOWNSTREAM-REENTRY-SEED-PLAN.md`) — **no collision with F6**; see F6's own paragraph. Its non-goal about `/devforge:grill` is its own scope statement about itself, its file set does not include `src/commands/grill/main.md`, and it DOES overlap this plan's `specify/main.md` and `plan/main.md` sites — so whichever plan lands second re-reads those two as landed. Both are NOT STARTED.
- **Plan 41** (`41-AGENT-EXECUTOR-REACHABILITY-PLAN.md`) — the orphan classes this plan avoids creating: every rule below is attached to a forcing step that already fires.
- **The FALSE BINARY finding** in repo-root `FINDINGS.md` (finding 1) — related by subject, **untouched by decision (D5)**.
- **The file-less preservation-AC finding** in repo-root `FINDINGS.md` (finding 4) — **owned by F3 (D4)**, pending ratification.
- `81-EVIDENCE-V2-BENCHMARK-RUN.md` — the run record. **Untracked, carries private-client identifiers, cited by filename only, never quoted into a tracked file.**

---

## Context for next session

**The one sentence that governs everything here:** the best run in a 20-run, 6-framework benchmark computed every fact correctly and drew the wrong conclusion from one of them — so **the gap is inference, not verification**, and every fix below is a rule about what follows from a fact the pipeline already has.

**The first trap is adding a checking stage.** Four independent mechanisms fired correctly in this run and each hardened a model built on one false label. Volume of checking is measured at zero effect (24× artifacts, 14× tests, review depth from none to mutation-tested). A phase that adds a stage has left the plan, and the tripwire is written into every phase's Verify for that reason.

**The second trap is reading F2 and F3 as closing holes.** Neither does, and the plan says so in bold at both places. **F2 does not close an accounting hole** — `src/commands/plan/main.md:370` already forces every `affected` row to be accounted for, the run's row WAS accounted for, and the accounting sentence was wrong. F2 removes the ambiguity that made it look plausible. **F3 does not add a missing directive** — `src/commands/specify/main.md:619` already carries one, and the AC dodged it by framing. F3 re-keys it on role. A build session that writes either as a gap-closure has mis-stated what shipped.

**The third trap is treating the benchmark as a measurement of plan 77.** It is one run of the matrix-present arm with no blind baseline. It is consistent with the matrix working. It does not demonstrate it, and D3 records the difference deliberately.

**The fourth trap is the constitution.** F1 is the mechanical trigger the FALSE BINARY finding has lacked, and that makes editing §3.6 feel like the natural next step. **D5 refuses**, and the reason is in the run: the intrinsic form WAS considered and WAS rejected — on a phantom AC's authority, not on the rule's preference. Removing the preference changes nothing about that rejection. The finding stays open and stays untouched.

**The fifth trap is building F6's downstream route.** F6 came from a **SECOND observed incident** (maintainer-reported 2026-08-18, a consumer run, no artifact in this repo — F6's origin paragraph is the record), and it is a **single-sentence widening at one site**: the PHASE 5 Q2 sentence in `src/commands/grill/main.md` carrying "attributed to the NEAREST introducing stage". **The route a `research` attribution lands in already exists** — `/devforge:research` Phase 0.6 globs the seed, matches `target_stage == "research"` and treats it as binding. **Do not build it, do not extend it, and do not add a second statement of the attribution rule anywhere in the grill command.** F6's whole content is which artifacts the trace must read.

**One pre-existing residual was found while drafting this plan and is recorded here because nothing else records it — it is NOT this plan's to fix.** `src/commands/research/main.md:1170` says rule 5 governs how `/devforge:plan` consumes the matrix and "is stated there". It is not stated there under that label: `grep -n "Rule 5" src/commands/plan/main.md` returns one hit, `:443`, whose subject is impossibility rejections in the Alternatives Rejected column, while the consumption content sits UNLABELLED at sub-question 11 (`:370`) and PHASE 2.5 step 8 (`:539`). It shipped with plan 77's Phase 2, it is **unowned**, and repairing it would edit the matrix accounting machinery this plan's non-goals exclude — so it is routed to a future surgical cleanup. **A Phase 2 or Phase 3 session must not close it by attaching matrix-consumption language to `:443`, and must not search for a labelled rule that does not exist.**

**The working tree is uncommitted throughout**, and several plans this file cites are working-tree state, so any "shipped" claim about them means reviewed-but-uncommitted rather than released. Re-check each from the code rather than from a Status line.

---

## When resuming work

1. Read this file in full, then the **six fixes** section again — the two corrections marked ⚠ are the parts most likely to be lost, and both change what the fix IS rather than how it is built. **F6 was appended on 2026-08-18 and carries no ⚠ block**; what is easy to lose there is that its origin is a SECOND incident with weaker provenance than the benchmark's.
2. Read **plan 77** (whose artifact this plan amends, whose R3 directive F3 widens, and whose A4 finding is F4's sibling on the same call site but on a different field — read F4's own paragraph before treating A4 as a predecessor), then **plan 69** (whose Step 2b machinery F4 constrains).
3. **Re-verify every anchor in the Verified-anchors table against the working tree.** Grep the quoted strings — `Step 2b — Trace each caller`, `varies`, `traced, never asserted`, `must name the arguments the function in question actually receives`, `Rejected-alternative checkability`, `behavior_preservation`, `Layer Map`, `attributed to the NEAREST introducing stage` — never the `:NNN`.
4. **Re-confirm the numbering before drafting.** `src/commands/plan/main.md` carried sub-questions 1–11 and PHASE 2.5 steps 1–8 on 2026-08-17; `src/agents/ac-verifier.md` carried Rules 1–13. If another in-flight plan appended first, this plan's additions land after, and any phase text naming a number is re-checked against the file as landed.
5. **Do not look for a test-boundary or verification-strategy section in `src/commands/plan/main.md`.** It does not exist; F5's plan-side seam is PHASE 2.5 steps 1–3. This is recorded because the brief that produced this plan named a section that is not there.
6. Start at **Phase 0.** D3, D5 and OQ-3 each shape a phase below; leaving any of them to executor discretion re-opens it mid-build. **Confirm item (j) explicitly** — F6 carries no D-number, so a ratification recorded only against D1–D6 and OQ-1–OQ-3 leaves Phase 5b unauthorized while looking complete.
7. Re-read the privacy constraint at the top before writing a single sentence into this file or into any `src/` file. **It binds execution, not just drafting.**
