# 107 — Surface Path Proof Plan

**Created**: 2026-09-20
**Status**: **Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start.** Every decision (D1–D8) and every open question (OQ-1–OQ-3) carries a recommendation and its strongest counter-argument, and each waits for the maintainer. **Phase 7 is a user-driven consumer e2e HARD GATE that has not run**; when this plan is later closed on its build, "done" will mean BUILT and build-verified and NEVER that Phase 7 passed. ⚠ **Numbered 107 because 100, 101, 102, 104, 105 and 106 are taken in this checkout as of 2026-09-20 and 103 was vacated by a renumbering — the gap at 103 is not a missing plan.** ⚠ **Other sessions work in this same checkout and may take 107 first; a resuming session re-checks the number before trusting it.**

A spec can say a user-facing surface is covered WITHOUT a code change — that the surface inherits the change through some shared path — and that claim is recordable as free text with no evidence behind it. The same spec can carry an acceptance criterion asserting something about what that same surface sends. The two can contradict each other inside one artifact, and nothing in the pipeline refuses the pair. Four things make up the single change proposed here: a typed role key on the §4 row that makes the claim keyable on structure rather than on phrasing (D2), a citation requirement that rides on that key (D3), an advisory §4 ↔ §5 cross-check (D4), and one sentence at `/devforge:verify` pointing the agent at evidence that is definitionally outside the diff (D6's instead-clause). They are one change because they are one gap: the claim is authored without evidence, it is never compared against the criterion it contradicts, and the code that would refute it is in a file the change did not touch. **This plan additionally carries two items that are NOT part of that argument** — D5's `/devforge:research` band anchor, which has its own build phase, and D8's render decision.

---

## Origin & evidence

⚠ **Evidence class, to be repeated in every summary of this plan: ONE observed consumer incident, relayed from a peer session, whose artifacts are NOT re-readable from this repo — plus grep-verified structural facts read against THIS tree on 2026-09-20. The five-link structural chain WAS verified here. The incident behind it was NOT. NOTHING WAS MEASURED.** A clean Phase 7 would show the mechanisms behave on planted fixtures; it would never show that this gap costs anything at any rate.

**The incident, told generically.** This repo is public and the run happened on a frozen external install whose artifacts live outside it, so this plan names no client, no install, no repo, no branch, no ticket id, no identifier and no framework, language or product name from that install. The shape, and only the shape:

A run correctly found every surface of a feature, including a non-obvious one, and cited valid user-visible identity evidence for it — a mode constant plus a translation key. It wrote an acceptance criterion for that surface about the shape of the request that surface issues. Then, in the spec's §4 Affected Areas, it recorded the same surface as **"no code change — the surface inherits the payload change via the same use case."**

**That inheritance claim was false.** The surface constructs its own dependency object WITHOUT the identity hooks that its sibling surface passes in, so a runtime check inside that object evaluates false and the call is dispatched through a DIFFERENT use case — the very one the spec separately pinned as unchanged. **The §4 row and the §5 AC therefore contradicted each other inside one spec.** The contradiction survived `/devforge:research`, `/devforge:specify` and `/devforge:spec-check`.

**Why the existing prover could not see it.** The conflict exists only in conjunction with a reachability fact. Identity evidence establishes that the surface SHOWS the feature; it says nothing about the path by which that surface is populated. Two statements that are each individually satisfiable — "this surface needs no code change" and "this surface sends X" — are contradictory only once the construction site is read, and reading it is not part of any formalization.

**The relay, and what it is worth.** The chain above reached this plan through a peer session's written report plus a verification pass made against this tree the same day. ⚠ **Nothing in a relayed report is a fact until it is re-derived from the tree.** L1–L5 below are this session's own reads, and **three of the relayed claims were CORRECTED or MATERIALLY EXTENDED** in the course of making them — recorded here rather than smoothed away:

- **Correction 1 — L2's grep is not "exactly two authoring hits".** `grep -rn "reached through the changed code\|a different path" src/ --exclude-dir=__pycache__` returns **four** hits, and all four are enumerated here so a resuming session scores the grep against the LIST and never against a remembered number. Two are the band's authoring sites (`src/commands/research/main.md:782` and `:787`); one is an unrelated error string (`src/devforge/lib/_generate_docs/_setters.py:112`); and **the fourth is `src/commands/research/main.md:425`, Phase 2.3b's surface-count frame**, whose prose reads *"other surfaces show the user the same feature, whether through the same shared symbol or through a different path"*. That hit is NOT the band — it is a framing instruction that happens to share the words. ⚠ **A session that greps this phrase to find the band's sites must discard line 425 by reading it, not by counting hits.** L2's conclusion is unaffected: no helper, no schema and no downstream command keys on the band.
- **Correction 2 — the §4 row shape ALREADY varies in key count, and the repo ALREADY tolerates it.** D2's counter-argument as relayed ("every consumer must tolerate a fourth key") is materially weaker than it reads. `src/devforge/lib/_specify/_cmds_handoff.py` carries TWO serializers into the same state bucket: `_affected_area_to_dict` at `:456` returns `{"area", "files", "impact"}` (three keys), and `_discover_affected_area_to_dict` at `:461` returns those three **plus `is_internal_extension_candidate`** (`:472`) — its own docstring calls that a *"discover-only field"*. **So a fourth key on this exact row is not a new shape; it is the shape the discover lane already writes**, and the render reads every field through `.get` with a default — `""` for the two scalars at `src/devforge/lib/_specify/_render.py:251` and `:253`, `[]` for the files join at `:252` — **so an unknown extra key is simply not read.** ⚠ **The consequence for D2 is that the counter-argument stands on the SETTER's required-flag break, not on the row's key count.** ⚠ **The consequence for the row's two written descriptions is that BOTH are ALREADY narrower than the row they describe** — the setter docstring at `src/devforge/lib/_specify/_cmds_phase4_setters.py:276` (`"""Append a §4 Affected Areas row {area, files, impact}."""`) and the subparser help at `src/devforge/lib/_specify/_cli.py:421` (`help="Append §4 row {area, files, impact}."`). **That drift predates this plan and this plan does not own it; Phase 1 touches both strings and must not widen either to "fix" the discover-lane omission as a side effect.** ⚠ **A builder who updates one and not the other leaves the pair inconsistent — they are two sites, not one.**
- **Correction 3 — there is a consumer the relayed list OMITTED, and it reads the rendered markdown rather than the state.** `src/devforge/lib/cbm_sync_helper.py:226`, `_parse_affected_areas(spec_md_path)`, scans `spec.md` from the `## 4.` heading to the next `## N.` heading and harvests backticked path-like tokens via `_AFFECTED_AREAS_FILE_RE` (`:223`), called at `:376`. **It is column-agnostic** — it never parses the table — **so a fourth column does not break it.** ⚠ **But its regex is `` `([^`\n]+\.[a-zA-Z0-9]+)` ``, which requires the backticked token to END in a dot plus alphanumerics. A `path:line` token does not match it; a bare `path.ext` token does.** So a `path_evidence` value rendered as `` `src/a/b.ts:412` `` is not harvested, and the same value rendered without its line number WOULD be. **This is a reading of the regex, not a test result — and what pins it DEPENDS ON D8: on a RATIFIED D8 Phase 1 pins it with an actual test rather than trusting this paragraph, and on a DECLINED D8 nothing renders `path_evidence` at all, so it stays a READING of the regex. Phase 1's `#### Verify` says exactly that on both arms.** ⚠ **And the conditional above is load-bearing only if the render emits backticks at all — it does not.** `src/devforge/lib/_specify/_render.py:252` is `", ".join(a.get("files", []))`, a bare join, and the row template at `:250` is `"| {0} | {1} | {2} |".format(...)` with no backtick anywhere. **So today `cbm_sync_helper._parse_affected_areas` harvests every backticked `path.ext` token an author typed ANYWHERE in the rendered §4 SECTION — the `area` cell and the `impact` cell alike, because the harvest is scoped to the whole section from the `## 4.` heading to the next `## N.` heading and never to one cell — and nothing at all from the Files column, which the template emits bare.** **Whether a rendered `path_evidence` value is harvested AT ALL therefore depends FIRST on whether the render backticks it, which is D8's question and not Correction 3's.** **That too is a read and not a test result, and it splits on D8 the same way: the bare-render half — the Files column yielding no harvest at all — is pinned by Phase 1's baseline test UNCONDITIONALLY, while whether a rendered `path_evidence` is harvested is pinned by an actual test only on a RATIFIED D8. On a DECLINED D8 nothing renders `path_evidence` at all, so that half stays a READING, and Phase 1's `#### Verify` says so rather than leaving it to this paragraph.**

### The verified structural chain (2026-09-20)

Five links. Every anchor below was read against this tree on 2026-09-20. ⚠ **Line digits drift — grep the quoted text, never the digits.**

**L1 — the path claim is authored as free prose inside another string.** `/devforge:research` Phase 2.4e Step 3 records each feature surface with a `--relevance` string whose template ends in a path band: `<reached through the changed code | a different path: …>` — `src/commands/research/main.md:782`. The prose that governs it sits at `:787`: *"In `--relevance`, write `reached through the changed code` when the surface's trace passes through a fix-path helper Phase 2.4c recorded or through the symptom site, and `a different path: ` followed by the request or data path the surface takes when it does not."* **The band is a classification with NO evidence requirement: no hop, no `file:line`, nothing anchors it.** ⚠ **The band is present in BOTH templates.** Line `:782` carries the evidenced-surface form and line `:787` carries the suspected-surface form (*"may show the named feature — no identity evidence found; why it may be the same feature: … — `<reached through the changed code | a different path: …>`"*). **Do not write that the band is suspected-only.**

**L2 — the band has no consumer anywhere in the framework.** Subject to Correction 1's hit count, no helper, no schema, no setter, no verify check and no downstream command keys on either band value. **The band is prose that is written and then read by nobody except a model reading the report as text.**

**L3 — Phase 2.4e's surfaces never reach `/devforge:specify` as typed data.** Four reads, each verified:

- The research handoff's `spec_seeds.affected_areas` is built from fix-path helpers and value-production sites ONLY — `src/devforge/lib/_research/_handoff_build.py:556` calls `_build_affected_areas(...)`, whose signature at `:84` is `_build_affected_areas(fix_path_helpers, value_production_sites)`. **Phase 2.4e's findings are not among its inputs.**
- The typed caller rows that carry surface / scope / justification (plan 69 D5/WI-E) go into the `CallerEnumeration` block — `src/devforge/lib/_research/_handoff_build.py:446` — **not into `spec_seeds`.**
- `/devforge:specify`'s `import-handoff` reads `handoff.spec_seeds` and nothing else: `src/devforge/lib/_specify/_cmds_handoff.py:582`, `seeds = handoff.spec_seeds`, inside `cmd_import_handoff` (`:508`). **`grep -rn "inbound_callers" src/devforge/lib/_specify/` returns ZERO matches.**
- `/devforge:specify` states the consumption in its own words: *"No content parsing of `/devforge:research` output — the file is consumed as plain markdown into Phase 1.5 findings."*

**So the band travels to `/devforge:specify` as prose for a model to read, and as nothing else.**

**L4 — the spec-side claim has no role key and no evidence requirement.** `record-affected-area --impact` is an unvalidated free-text scalar: `src/devforge/lib/_specify/_cli.py:428` is `sp.add_argument("--impact", required=True)` — **no `choices`, no validator beyond non-empty.** The setter appends the row at `src/devforge/lib/_specify/_cmds_phase4_setters.py:297`, under the docstring at `:276`. The authoring site is `src/commands/specify/main.md:644`, governed by two rules in the same file: **Covering a user-facing surface takes two entries** at `:652`, and **Every covered surface needs its own AC** at `:662`. **So "No code change — surface inherits via the same use case" is a PATH CLAIM recorded with zero evidence, and the row carries no structural marker saying a path claim was made at all.**

⚠ **The enum shape has precedent in this same file.** `record-risk`'s `--impact` at `src/devforge/lib/_specify/_cli.py:564` is declared `required=True, choices=list(IMPACT_ENUM)`, beside `--likelihood` at `:561` with `choices=list(LIKELIHOOD_ENUM)`. **Two different flags named `--impact` already live in this CLI module and mean different things** — one enum-valued on `record-risk`, one free-text on `record-affected-area`. Any new flag added here is named against that collision, not into it.

**L5 — nothing compares §4 against §5.** `cmd_verify_scope_coherence` (`src/devforge/lib/_specify/_cmds_phase4_verify.py:242`) pools §5 AC statements and §4 affected-area impacts into ONE target list and compares each target against **§6 Out-of-Scope entries** — the affected-area arm is at `:282`. **The §4 ↔ §5 pair — the pair that contradicted — is compared by nothing: the two halves are siblings in the same target list, never checked against each other.** The verb is also deliberately NON-BLOCKING; its own docstring states the posture is *"intentionally NON-BLOCKING: warnings are written to stderr but the command always exits 0"* because *"this is a heuristic check that WILL produce false positives"*.

### The downstream consequence

**This is the sharpest formulation in the plan and the reason the gap does not close itself one command later.** `/devforge:verify`'s code-reading fallback reads the CHANGED FILES: `src/commands/verify/main.md:207` — *"**Changed files** — the `files` list from `$WORKDIR/scope.json` (the assembled-feature diff; the agent code-reads these for any AC it cannot observe at runtime)."*

**The construction site that falsifies an inheritance claim sits in an UNCHANGED file by definition — if it had changed, there would have been a code change.** So **the evidence that refutes the claim is definitionally outside the diff, and no `ac_verification_mode` points the agent at it.** ⚠ **This, not the absence of a browser, is why reading the diff cannot close such an AC.** A session that reaches for a runtime channel here has misread the failure.

### The precedent that decides the shape

Two facts from this repo, both verified on 2026-09-20, and together they decide what a fix here is allowed to look like.

**(a) `/devforge:specify` already carries a rule of exactly this shape for a different claim class.** Step 4.4, the paragraph beginning **"The same standard binds every AC entering §5.2 Behavior preservation"**, requires every AC entering §5.2 to show its subject state REACHABLE by citing the construction site that produces it, traced through the codebase-memory-mcp chain, *"never asserted"*. Its trigger is explicit: *"The trigger is the subsection an AC is added under, not how its statement is worded — framing a claim as preserved lane behavior rather than as a still-present value is no exit from it."* Where no construction site can be cited, the criterion is not a preservation criterion but a product question and routes to §8 Open Questions (Step 4.7) with its Phase 1.5 finding in §9 Risks (Step 4.8). ⚠ **Cited by section name deliberately: that paragraph is long, it is being edited by other sessions in this checkout, and its digits drift. Find it by its opening words.**

**(b) `FINDINGS.md` finding 4 records WHY that rule took the form it did.** Plan 77's R3 shipped a correct prose directive into `src/commands/specify/main.md` naming the trap by name — *"and the AC was written anyway"* — and the same `FINDINGS.md` sentence says why: *"almost certainly because it was framed as lane-behavior preservation rather than value presence and so never matched the directive's lexical trigger."* ⚠ **Two fragments because a bold marker closes between them at the source — each half greps to `FINDINGS.md`, the span across them does not.** Plan 81's F3 closed that by re-keying the trigger on the AC's declared ROLE — the `add-ac --subsection behavior_preservation` key — *"rather than on its phrasing, which narrows the dodge surface without closing it."* The same entry records the residual honestly: the role key narrows the dodge surface without closing it, and an author can still file under another subsection.

**The consequence for this plan, stated as a design rule: any fix here that triggers on the PHRASE "no code change" repeats plan 77 R3's failure.** The trigger must be a structural key the author cannot phrase around. **§4 rows have no such key today — so creating one is the spine of this plan, not an optional extra.**

**And the visibility bar, from `FINDINGS.md` finding 5, carried here because it disqualifies the obvious weak fix.** That entry's load-bearing half asks: *"does the rule produce an artifact that is visibly wrong when the analysis wasn't done?"* — and records that a required field filled with a plausible sentence *"does not read wrong on its face, which is the same defect for which that plan records 'enumerate the consumers' and a completeness count as REJECTED candidates."* ⚠ **Any field this plan adds is shaped so a weak answer is VISIBLE: an enum plus a `file:line`, never free prose.** A `--path-evidence` that accepts a sentence fails this bar and must not ship.

---

## Item → decision map

Every link above either has an owner in this plan or is explicitly routed around. **A link with no owner is named as such rather than left to look covered.**

| Item | What it is | Owner |
|---|---|---|
| **L1** — the band is free prose inside `--relevance`, in both templates | `/devforge:research` Phase 2.4e Step 3 | **D5** — anchored in place, not typed |
| **L2** — the band has no consumer | no helper, schema or command keys on it | **No owner here.** D5 defers typing to a separate plan; `## Non-goals` records it |
| **L3** — Phase 2.4e surfaces do not reach `/devforge:specify` as typed data | `spec_seeds` is built from other inputs | **No owner here.** This plan routes AROUND the lossy hop; it does not widen `spec_seeds` |
| **L4** — the §4 row has no role key and no evidence requirement | `record-affected-area --impact` is free text | **D2** (the key) + **D3** (the citation) |
| **L5** — nothing compares §4 against §5 | `verify-scope-coherence` compares both against §6 | **D4** — a new advisory verb |
| **The downstream consequence** — refuting evidence is outside the diff | `/devforge:verify`'s changed-files fallback | **D6's instead-clause** — one sentence, no new channel |
| **Which command owns the rule** | authored at specify, known at research | **D1** |
| **Whether `/devforge:plan` gets it too** | §4 is not read there by name | **D7** — recommended NO |
| **Whether the rendered §4 table carries the new keys** | state DOES reach `/devforge:plan`, but the handoff re-read whitelists each row to `("area", "files", "impact")` and drops the two new keys there, so the §4 render is the only channel that carries them to a reviewer | **D8** — recommended YES (render both) |

---

## Decisions to ratify

Nothing below is ratified. Each item states the decision, a recommendation, and **the strongest counter-argument, recorded honestly rather than answered away.** Proposed emitted wording is **substance, not final text**: the builder may reword, but every element named must survive. **No emitted sentence may name plan vocabulary** ("D1", "plan 107", "Phase 0"); real headings such as `Step 4.3` are fine.

### D1 — Which command owns the fix

**The decision.** `/devforge:specify` or `/devforge:research`.

**RECOMMEND `/devforge:specify`.** The false claim was authored there, in a §4 row, and contradicted an AC authored there, in §5. **Both halves of the contradiction live in one artifact produced by one command, so one command can be made to refuse the pair.** D4 is only possible at all on that side, because only there do both halves sit in one state file.

**COUNTER, at full strength.** The run that actually KNOWS the path is `/devforge:research` — it walked the callers and read the construction sites, and it is where the band is authored (L1). `/devforge:specify` sits downstream of a lossy prose-only hop (L3), so putting the citation duty there makes specify re-pay a trace research already paid, and on a thinner context. **An author at specify who cannot cheaply re-derive the construction site will write a plausible one, which is exactly the visibility-bar failure finding 5 warns about.**

**The rebuttal to the counter, stated rather than hidden.** `/devforge:specify` Step 4.4 already performs exactly this kind of codebase-memory-mcp-traced construction-site read for every §5.2 AC. **The capability is present in that command today and the precedent is established** — this plan applies a shipped standard to a second claim class rather than inventing a new duty. ⚠ **The counter is not thereby dissolved: specify pays the trace twice across the two rules, and nothing measures what that costs.**

### D2 — Add a typed `--change-kind` enum to `record-affected-area`

**The decision.** Add `--change-kind` with values `code-change` | `no-code-change` to `record-affected-area`. ⚠ **Those two values are what D2 PROPOSES, and D2's outcome ALONE does not settle the enum's ARITY: a ratified D3 (a) carrying a THIRD enum value widens D2's declared `code-change` | `no-code-change` pair, and Phase 0's `#### Verify` is where that arm is picked.** The third value originates in **D3**, not here — D3's resolution (a) FORBIDS its uncitable row from `no-code-change`, so that row *"carries `code-change` (or a third enum value)"*. ⚠ **A reader entering at D2 has therefore not seen the whole of this decision until D3's two resolution arms are read with it.**

**Why it is the spine.** It is the role key that (i) makes the D3 citation rule keyable on STRUCTURE rather than on phrasing — the precedent's whole lesson — and (ii) makes D4's cross-check precise instead of lexical.

**RECOMMEND: required on the SETTER for new calls; an absent key on an already-written state row reads as unclassified (empty string), never fabricated — and that reading holds on ANY row lacking the key, seeded as well as legacy, because the paragraph below establishes this population as PERMANENT rather than a backlog that drains.** That is the same absent-key-defaults-to-`""` pattern the repo already uses for `InboundCaller.surface` under plan 69 D5/WI-E — `src/devforge/lib/_research/_handoff_build.py:407-412`: *"A row recorded but never classified has no surface/scope/justification keys in report state at all -- absent-key defaults to `""` here, matching InboundCaller's own `""` defaults (not fabricated; simply the unclassified-legacy-row state)."*

**The unclassified state is a PERMANENT population, not a legacy one.** As FIRST WRITTEN, the RECOMMEND above framed the absent key as an *already-written* state row and nothing more, borrowing a precedent that names it the *"unclassified-legacy-row state"*. **On this row that framing WAS wrong**, and the RECOMMEND above now carries the correction inline rather than deferring it to this paragraph. **The history is recorded rather than smoothed away, so a reader meeting the corrected RECOMMEND first still learns what it was corrected FROM** — and the evidence for the correction is this paragraph's, not the RECOMMEND's. `import-handoff` writes §4 rows on BOTH seeded lanes and NEITHER passes through the setter: `src/devforge/lib/_specify/_cmds_handoff.py:588` builds the research lane's rows — `affected_areas = [_affected_area_to_dict(a) for a in affected_areas_src]` — and `:773` builds the discover lane's through `_discover_affected_area_to_dict`. **So every row seeded by `import-handoff` arrives unclassified, today and after this plan ships, because neither lane ever calls `record-affected-area`.** The consequence, named rather than left implicit: **D3's citation duty never binds a seeded row, and D4's check never examines one — both mechanisms cover the SETTER-AUTHORED population ONLY.** ⚠ **Nothing in this plan requires an author to classify a seeded row afterwards, and no verb reports how many of a spec's rows are unclassified.**

**COUNTER.** `--impact` is already required and free-text; **adding a second required flag to the same setter is a breaking CLI change**, and every consumer of the row must tolerate a fourth key. The consumers, enumerated rather than counted:

- `src/devforge/lib/_specify/_render.py` — the §4 table at `:244-247` (`| Area | Files | Impact |`) and the impact read at `:253`; the file-count aggregation at `:407`; the area count at `:409`; the second aggregation at `:511` and its loop at `:514`.
- `src/devforge/lib/_specify/_cmds_handoff.py` — the two serializers at `:456` and `:461`, the import assignments at `:653` and `:832`, and the specify→plan handoff re-read at `:1321-1326`.
- `src/devforge/lib/_specify/_cmds_phase4_setters.py:297` — the append itself, under the docstring at `:276`.
- `src/devforge/lib/_specify/_cmds_phase4_verify.py:282` — the affected-area arm of `verify-scope-coherence`.
- `src/devforge/lib/_specify/_cmds_phase3.py:208` — the affected-area count in the phase-3 summary.
- `src/devforge/lib/_specify/_state.py:71` — the default empty bucket.
- `src/devforge/lib/cbm_sync_helper.py:226` — **the rendered-markdown parser** (Correction 3), plus the research and discover seed producers that build the same dataclass (`src/devforge/lib/_research/_handoff_build.py:84`, `src/devforge/lib/_discover/_handoff_build.py:102`).

**Two mitigating facts, both verified.** First, **the spec-side blast radius is ONE block**: `grep -rn "record-affected-area" src/commands/` returns exactly one authoring call site, `src/commands/specify/main.md:644`. Second, **the row already carries a fourth key on the discover lane** (Correction 2), so a fourth key is not a new shape and the render already reads through `.get`. ⚠ **What survives the mitigation is the required-flag break itself, and that is the real cost.**

### D3 — The citation requirement for a `no-code-change` row

**The decision.** What a `no-code-change` row must prove.

**SHAPE.** A `no-code-change` row must cite, in a new `--path-evidence` flag, the `file:line` of the **construction site through which that surface is reached** — the code that builds, mounts or registers the surface's dependencies — traced through the codebase-memory-mcp chain, **never asserted**. Where no such site can be cited, **the row may NOT claim `no-code-change`**: the surface takes the route §5.2 already defines for an uncitable subject — §8 Open Questions (Step 4.7), with its Phase 1.5 finding in §9 Risks (Step 4.8).

⚠ **UNRESOLVED — the §8 route the SHAPE names has NO mechanism at Step 4.3, and Phase 0 must settle it.** Three facts, each verified against this tree:

- **The §8 deferral mechanism is a decision-point verb at `/devforge:specify`'s PHASE 2, not at `/devforge:specify`'s Phase 4.** `set-dp-deferral --deferral-kind open_question` sits inside that command's Phase 2 per-decision-point protocol — the flag at `src/commands/specify/main.md:409`, the whole call written out at `:400`, and the `open_question` arm governed at `:418`, where the deferral *"renders the decision point in §8 Open Questions (Step 4.7)"*. ⚠ **`:400` specifies it for a surface with NO identity evidence.**
- **D3's uncitable row is a DIFFERENT case.** Its surface HAS identity evidence, and a Phase 2 decision point already resolved it to `cover <surface>` (`src/commands/specify/main.md:399`). By the time Step 4.3 runs that decision point is closed, and no setter re-opens it.
- **The shipped rule makes the row NECESSARY.** *"Covering a user-facing surface takes two entries"* (`src/commands/specify/main.md:652`) requires an affected-area row for a covered surface. ⚠ **What `:417` adds is an ANALOGY, labelled as one rather than read as shipped text about §4 rows.** That line governs `--deferral-kind OOS` inside `/devforge:specify`'s Phase 2 decision-point protocol and says nothing about dropping a §4 row: *"The deferral writes no §6 entry and renders in neither §6 nor §8, so a deferral you made would be an exclusion no reader of the spec sees."* **The SHAPE is what transfers — a covered surface silently uncovered, visible to no reader of the spec — and the transfer is this plan's, not the file's.**

⚠ **The asymmetry with the §5.2 precedent this rule claims to mirror.** There the uncitable object is an AC, which is simply never added, and §5.2 can be marked N/A. **Here the object is a ROW for a surface the user already chose to cover — it cannot be "not added" without silently UNCOVERING that surface.**

**Two candidate resolutions, named without one being picked for the maintainer.** Either **(a)** the row is still recorded but is FORBIDDEN from the `no-code-change` value, so it carries `code-change` (or a third enum value) and the uncitable path claim goes to §8 as an open question ALONGSIDE the row; or **(b)** a new Step 4.3 verb records the deferral at `/devforge:specify`'s Phase 4 — **new mechanism this plan currently declares out of scope.** ⚠ **D3 as written ratifies a route whose mechanism does not exist. The gap surfaced because THIS plan's Phase 2 `#### Verify` line — "The three paragraphs are mutually consistent" — was the only thing carrying it; Phase 0's `#### Verify` now demands the pick between (a) and (b) BY NAME, so that Phase 2 line is the downstream consistency check and no longer stands in for the Phase 0 decision.**

**RECOMMEND: adopt, worded as a near-verbatim sibling of the shipped §5.2 paragraph so the two read as one rule applied to two claim classes.** The §8/§9 route is named identically in both, so a reader meets one escape hatch, not two.

**COUNTER, at full strength.** **This is still prose plus a flag.** An author can write a plausible `file:line` that is the wrong site, and nothing distinguishes a traced citation from a guessed one. That is the same honesty bound Phase 2.4e's identity evidence already carries — `src/commands/research/main.md:741`: *"The evidence is yours to cite and nothing checks it: citing it makes the call inspectable, not mechanical."* ⚠ **The claim this plan may make is that the citation makes the claim INSPECTABLE. It may NOT claim the citation makes it correct.** The shipped §5.2 paragraph ends on the same note and supplies the wording to reuse: *"A citation is necessary; it is never proof of exhaustiveness."*

**A divergence from the sibling this rule claims to mirror, recorded rather than smoothed over.** §5.2's citation is **prose inside an EXISTING field** — that paragraph says *"One line carries the citation, inside either the AC's `--statement` or the Phase 1.5 finding it cites with `--finding-ref`."* **D3 proposes a DEDICATED flag instead.** The two are not the same mechanism, and calling D3 "the same rule" without this note would be false. **The argument for diverging:** finding 5's visibility bar is only met when a weak answer is visible, and a `file:line` in its own flag is inspectable at a glance while a sentence buried in `--impact` is not; a dedicated flag is also what makes the absent-key-reads-as-unclassified pattern available. **The argument against:** it makes §4's rule mechanically unlike §5.2's, so the two drift independently from the day they ship, and a future session reading the §5.2 paragraph will not find the §4 rule by analogy. ⚠ **This fork is part of D3 and is ratified or declined with it.**

### D4 — A §4 ↔ §5 cross-check

**The decision.** A new `specify_helper` verb that, for every affected-area row with `change_kind == "no-code-change"`, finds §5 ACs whose `statement` names that row's `area`, and reports each pair. ⚠ **`statement` and `area` are the live state keys, verified at `src/devforge/lib/_specify/_cmds_phase4_verify.py:279` and `:286`.**

**The match predicate, stated rather than assumed.** The word *"names"* is inherited from two SHIPPED prose rules that an AGENT evaluates, never code: `src/commands/specify/main.md:652` — *"at least one acceptance criterion whose statement names it"* — and `:662` — *"at least one AC here whose `--statement` names that surface"*. **Mechanizing that word is a divergence from both, and it is stated here rather than assumed away.** **RECOMMEND a case-insensitive, whitespace-normalized SUBSTRING test of the row's `area` inside the AC `statement`.** The reason is OQ-3's whole argument: it keeps this precise enum-keyed trigger away from the deliberately fuzzy token heuristic, and reusing `tokenize_for_overlap` (`src/devforge/lib/_shared/text_overlap.py:58`, imported by `verify-scope-coherence`) would entangle exactly the two things OQ-3 separates. **COUNTER, recorded honestly: a substring test misses every AC that names the surface in OTHER WORDS, which is the majority of EARS statements** — so the check is a false-NEGATIVE machine before it is ever a false-positive one.

**The population this check can reach.** ⚠ **What excludes the seeded rows is the ENUM, not the shape of their `area` values.** Two of the three seeded shapes ARE path-shaped — `src/devforge/lib/_research/_handoff_build.py:119` builds `AffectedArea(area=pkg, ...)` from a package path, and `src/devforge/lib/_discover/_handoff_build.py:138` builds `area_name = "internal:" + path_part` from an internal prior-art entry, passed at `:145` as `area=area_name`. **The third is not.** `src/devforge/lib/_discover/_handoff_build.py:114` reads `name = (tp.get("name") or "").strip()` off an integration touchpoint and `:124` passes it through as `area=name` — **a human-written touchpoint name, which an EARS statement CAN contain.** So an argument from `area` shape excludes two of the three and leaves the third matchable. **What excludes all three is D2's permanent-unclassified fact: a seeded row carries no `change_kind` at all, so this check's `change_kind == "no-code-change"` filter never reaches it whatever its `area` looks like.** **D4's reachable population is therefore SETTER-AUTHORED surface rows ONLY.** That matches the incident and is **not thereby a defect** — ⚠ **but it bounds what a clean Phase 7 can show.**

**RECOMMEND: ADVISORY — warnings to stderr, always exit 0** — matching `verify-scope-coherence`'s ratified posture (L5).

**The reasoning, including the position reversal, stated honestly.** A blocking check is tempting here, and more defensible than it would be for the existing verb: **this trigger keys on a declared enum plus the row's own `area` string, which is far narrower than a bag-of-tokens heuristic.** That is a real argument and it was the first position. **It is reversed for one reason: an AC that names a surface is NOT always a contradiction with `no-code-change`.** An AC can name the surface precisely in order to assert that it stays unchanged, which is consistent with the row. **Whether the AC asserts a CHANGE on that surface is not mechanically decidable**, so a blocking check would refuse correct specs.

**COUNTER to the advisory recommendation, at full strength, and it is the strongest objection to this whole plan.** `FINDINGS.md` finding 4 records that routing this class to an advisory home *"buys detection for the specs that opt in and nothing at all for the specs whose author was confident, which are the ones that produce this AC."* **An author confident enough to write a false inheritance claim is exactly the author who will read past a warning.** ⚠ **If that objection is accepted, D4 is worth approximately nothing and the plan reduces to D2 + D3 + D6 — a role key, a citation, and a read target. The maintainer decides whether that is enough.**

⚠ **Only the CONFIDENT-AUTHOR half of that quote transfers, and the plan as written OVERSTATES the objection.** Finding 4's own **AMENDED 2026-08-19** entry retires the premise the opt-in half rests on: it records that *"the opt-in premise the quoted clause rested on is gone"* and says why in the same sentence — *"plan 62's D14 was amended in place the same day — `/devforge:spec-check` is run-mandatory"*. ⚠ **Two fragments because a bold marker closes between them at the source — each half greps to `FINDINGS.md`, the span across them does not.** **D4's verb would run unconditionally inside Step 4.9, beside `verify-scope-coherence`, so the "specs that opt in" half does not apply to it.** What survives is the OTHER half — *"the specs whose author was confident"* — and what makes that half bite on D4 is the ADVISORY posture, a word this plan takes from finding 4's EARLIER clause *"But `/spec-check` is opt-in and ADVISORY by ratified D14"* and NOT from the AMENDED entry. ⚠ **The AMENDED entry's *"the verdict never binds"* sentence is about a DIFFERENT MECHANISM and answers nothing here.** It says `/devforge:spec-check`'s report VERDICT does not bind `/devforge:plan`'s gate; **D4's verb would render no verdict and would gate nothing** — under the posture recommended above it writes warnings to stderr and always exits 0. **So a session that follows that citation looking for the objection's answer finds a mechanism D4 does not have**, and what is left of the objection is about advisory OUTPUT alone: the warning is written, and the confident author reads past it. ⚠ **The correction makes D4 slightly MORE defensible, not less, and it is recorded because the maintainer is deciding D4's worth on the paragraph above.**

### D5 — The `/devforge:research` side: type the band, or anchor it in place?

**The decision.** Whether v1 types the band or anchors it.

**RECOMMEND for v1: anchor it in place.** ONE added requirement at `src/commands/research/main.md:787`: **the band value must name the hop it rests on** — `reached through the changed code: <file:line>` (the fix-path helper or symptom site the trace passes through) or `a different path: <file:line>` (the construction site or dispatch point that takes it elsewhere). **No new setter, no new verify check, no handoff field in v1.** The template at `:782` is updated to match — **that is a line inside the Step 3 bash fence, not a paragraph** — and so is the suspected-surface form, which does NOT sit beside the template: it lives in `:787`'s prose paragraph, the same paragraph as the governing sentence quoted in L1.

**COUNTER.** **L2 proved an unconsumed prose band is mechanically worthless, and anchoring a worthless band produces a better-looking worthless band** — which is itself a finding-5 failure mode, since a `file:line` in a field nobody reads is exactly an artifact that does not read wrong on its face.

**The honest answer, stated rather than dodged.** The band is worthless MECHANICALLY, but **it is the text `/devforge:specify` actually reads at §1.5**, where the report is consumed as plain markdown (L3). **Anchoring costs one sentence and improves the only channel that exists.** ⚠ **Typing the band properly — a new setter, a new research verify check, a handoff schema field, a render change and a specify-side consumer — is a SEPARATE and LARGER plan and must not ride along on this one.** For that future plan's benefit only: **the next free research check number is 21**, since the highest in use is check 20 (`src/devforge/lib/_research/_cmds_render_verify.py:837` and `:851`). ⚠ **That number is recorded as a fact about today's tree, not as a reservation — another plan may take 21 first.**

### D6 — The runtime/browser evidence rung

**The decision.** Whether `/devforge:research` gains a runtime or browser evidence channel.

**RECOMMEND: REJECT for this plan.** Three reasons, each verified:

- **The runtime band already exists and is owned downstream.** `/devforge:verify` has `ac_verification_mode: runtime-assisted`, probes Chrome DevTools MCP availability with one `mcp__chrome-devtools__list_pages` call (`src/commands/verify/main.md:197`), and reads a configured runtime URL from the `ac_runtime_url` config key (`src/devforge/lib/_configure/_schema.py:64`). **A second browser channel at `/devforge:research` would duplicate that config surface.**
- **It demands what the phase cannot supply.** A running environment, credentials and a specific signed-in identity, at the phase least able to supply them.
- **It is not what the incident needed.** A static trace from the surface through its construction site **breaks at the FIRST hop.**

**INSTEAD, adopt one narrow sentence at `/devforge:verify`:** an AC that names a user-facing surface directs the agent to read that surface's construction site **even though it is not in the changed-files list** — at the bullet `src/commands/verify/main.md:207`.

**COUNTER.** **A static chain proves wiring, not behavior.** Dynamic dispatch, feature flags and runtime configuration can still route a correctly-wired surface elsewhere, and only an observed request settles it. `/devforge:specify` Step 4.4 already concedes exactly this bound for §5.2 — *"reachability by static trace is bounded by dynamic dispatch, so a cited construction site shows the state IS reachable but never shows the citation exhausted every path."* ⚠ **This plan inherits that bound verbatim and must STATE it. It may not claim the static rung closes the class.**

### D7 — Whether `/devforge:plan` gets a rule too

**The decision.** Whether the rule gets a third home.

**RECOMMEND: NO.** `grep -rn "affected_area" src/commands/` returns **15 occurrences in exactly one file, `src/commands/research/main.md`, and ZERO in `src/commands/plan/main.md` or `src/commands/breakdown/main.md`** — neither command reads §4 by that name. ⚠ **And the 15 hits are NOT §4 rows: `affected_area` in `/devforge:research` is the memo dimension holding the user's own answer. Do not conflate the two when re-deriving this grep.** The claim is authored at `/devforge:specify` and checked at `/devforge:verify`; **a third home for the same rule multiplies the places it can drift out of sync.**

**COUNTER.** `/devforge:plan` is where the architect consult happens and **where a false inheritance claim would first become expensive.** Declining to touch it leaves the longest window between the false claim and its detection — the claim is written at specify and caught, if at all, at verify, with plan, grill, breakdown and every implement task in between.

### D8 — Whether the rendered §4 table carries the new keys

**The decision.** Whether `src/devforge/lib/_specify/_render.py`'s §4 table carries the row's `change_kind` and `path_evidence` values, or the two stay in `.devforge` state only. ⚠ **Named as STATE KEYS, not as the flags that write them: `_render.py` reads row dicts, never argv.** ⚠ **Every site below branches on this decision and none of them can be built or checked until it closes:** Phase 1's `_render.py` deliverable (*"if and only if D8 ratifies rendering them"*); Phase 1's `cbm_sync_helper` clause (*"if and only if the §4 render changes"*); Phase 1's `#### Verify` bullet **"A test pins the bare-render baseline UNCONDITIONALLY"**, whose Correction 3 regex assertions are ADDED on a ratified D8 and WITHHELD on a declined one; Phase 1's `#### Verify` bullet keyed on `git diff --stat src/devforge/lib/`, whose allowed diff set loses `src/devforge/lib/_specify/_render.py` and `src/devforge/lib/cbm_sync_helper.py` on a declined D8; the Tripwire **"If Phase 1 needs to change the `AffectedArea` dataclass shape in more than the consumers D2 enumerates"**, which carries that same declined-D8 MINUS clause (`src/devforge/lib/_specify/_render.py` and `src/devforge/lib/cbm_sync_helper.py` alike); and the Tripwire that fires *"If the §4 render EMITS either of the two shapes D8 contemplates"*. ⚠ **No count is given, because a count is what went stale here when this list was last extended. A site added to this plan is added to this list BY NAME.**

**RECOMMEND: render both.** The reason is D3's own justification. Finding 5's visibility bar asks whether the rule produces an artifact that is **visibly wrong when the analysis wasn't done**, and **the render is the only channel that can carry these two values to a reviewer.** ⚠ **Not because the state file goes unread downstream — it IS read.** `src/devforge/lib/_specify/_cmds_handoff.py:1321-1326` builds the specify→plan handoff's affected-area rows from `state.get("affected_areas")`, so state does reach `/devforge:plan` — **but that same re-read WHITELISTS each row to `("area", "files", "impact")` (`:1324`), so `change_kind` and `path_evidence` are dropped silently at that hop whatever D8 decides.** **The drop is consistent with D7's NO and needs no code change**, and it is what leaves `spec.md` as the only artifact in which a reviewer, `/devforge:plan` or `/devforge:verify` can see the two values at all. **A citation that never renders is invisible at exactly the review moment it exists for.**

**A fact the render decision must carry, verified today.** The §4 render emits **NO backticks** — `src/devforge/lib/_specify/_render.py:252` is `", ".join(a.get("files", []))`, bare. **So today `cbm_sync_helper._parse_affected_areas` harvests every backticked `path.ext` token an author typed ANYWHERE in the rendered §4 SECTION — the `area` cell and the `impact` cell alike, because the harvest is scoped to the whole section from the `## 4.` heading to the next `## N.` heading and never to one cell — and nothing at all from the Files column, which the template emits bare.** ⚠ **Whether a rendered `path_evidence` reaches the CBM drift set therefore depends FIRST on whether Phase 1 backticks it, which is part of THIS decision and not of Correction 3.**

**COUNTER.** The table is three columns and its rows already carry long file lists; **two more columns make it unreadable in a terminal.** And the alternative — folding both values into the existing Impact cell — **re-merges the structural key back into free text, which is the shape D2 exists to escape.**

**D8 DECIDES THREE things, not one, and the two below close WITH it.** The paragraphs above decide render-or-not alone. The SHAPE of the render, and whether the rendered `path_evidence` is BACKTICKED, are settled by the same ratification, because Phase 1 can build neither arm without them. ⚠ **Phase 0's `#### Verify` demands both BY NAME — a render-only outcome closes neither, and each sub-question below names what such an outcome leaves behind.**

**The SHAPE — RECOMMEND: two added columns, never the fold into the Impact cell.** The argument is already written above and is cited rather than restated: D8's own **COUNTER.** paragraph records that folding both values into the existing Impact cell *"re-merges the structural key back into free text, which is the shape D2 exists to escape"* — and D2 is this plan's spine, so the fold guts what the rest of it rests on. ⚠ **The counter to THIS recommendation is the OTHER half of that same paragraph** — *"two more columns make it unreadable in a terminal"* — **so both arms are argued in one place and are weighed there rather than re-argued here.** ⚠ **Both shapes stay live until this closes:** `## Tripwires` polices the fold as a shape that can actually ship, and Phase 1's deliverable — *"the §4 table carries the two new values"* — is satisfied by EITHER of them, **so a builder who finds no pick can take the arm D8's own COUNTER rejects, by default and without noticing.**

**The BACKTICKING — RECOMMEND: the rendered `path_evidence` is BACKTICKED.** Two reasons. **First, the ratified-D8 arm of Phase 1's `#### Verify` bullet "A test pins the bare-render baseline UNCONDITIONALLY" is written over REAL RENDER OUTPUT** — its added assertions are *"asserted over output `_render.py` itself produced and never over a hand-authored fixture"*, and they say a backticked `path:line` token is NOT harvested while a backticked `path.ext` token IS. **A BARE render is what the template does today** — `src/devforge/lib/_specify/_render.py:250`, no backtick anywhere — **so under a bare render `_render.py` emits no backticked token at all, that assertion has no real output to run against, and the only thing left that could satisfy it is the hand-authored fixture the same bullet forbids.** **Second, this plan writes its own `file:line` citations in backticks throughout**, so a bare cell is the one place a reviewer of the rendered table meets that convention broken.

⚠ **The honest counter, and it is the whole of the case against BACKTICKING: on the value shape D3 requires, backticking changes NOTHING mechanically.** D3's citation is a `file:line`, and a backticked `path:line` token is NOT harvested either — Correction 3's verified reading of `_AFFECTED_AREAS_FILE_RE`. **D8's "A fact the render decision must carry, verified today." paragraph says the CBM drift set depends FIRST on backticking, and FIRST is the exact limit of that claim**: the regex's second condition — the token must END in a dot plus alphanumerics — is one a `file:line` never meets, backticks or no backticks. ⚠ **So this sub-question decides whether Phase 1's test is satisfiable and what a reviewer reads, and NEVER what reaches the CBM drift set. A close record that ratifies backticking as a drift-set change has ratified something this plan does not claim.**

**The scope consequence.** D8 decides whether Phase 1 touches `_render.py` at all, and whether Phase 1's `cbm_sync_helper` clause fires.

### OQ-1 — Does `--change-kind` belong on EVERY §4 row, or only on rows naming a user-facing surface?

**RECOMMEND every row.** It is simpler and has no carve-out, which is what the zero-escape-hatch policy in `CLAUDE.md` favours — that policy names "if X except Y" and "unless trivial" as slip-paths to close before adopting a rule.
**Alternative:** surface-only rows are cheaper to author but require a judgment about what counts as a surface, **which is a carve-out by another name.**

### OQ-2 — Should `--path-evidence` accept a `(none)` sentinel?

`/devforge:research` Phase 2.4b uses an explicit sentinel for an explicitly-absent result, so the precedent exists in the framework.
**RECOMMEND the latter — no sentinel, whichever SHAPE D3 ends up carrying: under either of D3's two candidate resolutions an uncitable row is FORBIDDEN from claiming `no-code-change`, and the claim routes to §8/§9 instead.** A sentinel would re-open the escape hatch D3 exists to close, and finding 5's bar is failed by any field that can be satisfied without the analysis. ⚠ **OQ-2 decides the sentinel question ONLY. It does NOT pick between D3's resolution (a) and (b) — that pick closes with D3, and a close record reading OQ-2's outcome as settling it has closed neither.**
**Alternative:** the sentinel, whose argument is that forbidding the claim may strand a row with nowhere to go. ⚠ **The §8/§9 route is that somewhere; whether it is sufficient is the actual question.**

### OQ-3 — Does the D4 advisory check belong in the existing `verify-scope-coherence` verb or in a new one?

**RECOMMEND a new verb.** It keeps the ratified non-blocking posture of the old one untouched and keeps the two triggers independently revisable — the old trigger is a deliberately fuzzy token heuristic, the new one an enum-keyed exact match.
**Alternative:** folding it in reuses the wiring — `_load_state`, the stderr shape, the always-exit-0 contract — **but entangles a precise enum-keyed trigger with a deliberately fuzzy token heuristic, so a future session tuning one silently tunes the other's blast radius.**
⚠ **OQ-3 decides the verb's HOME ONLY. It does NOT pick D4's match predicate.** A folded verb keeps its OWN enum-keyed trigger — that is exactly what the Alternative's entanglement argument PRESUPPOSES, since there is nothing to entangle unless the two triggers stay distinct — **so nothing in OQ-3 contemplates the new check adopting `tokenize_for_overlap`.** The predicate pick closes with D4, and **a close record reading OQ-3's outcome as settling the predicate has closed neither.**

### Phase 0 close record

**PENDING — nothing is ratified.** When it closes, this record must name **each** of D1 through D8 and OQ-1 through OQ-3 with its outcome (ratified / amended / declined), state whether per-item deliberation was supplied, state whether the close was an explicit pick or a delegation, and say which files the outcomes put in scope. **Every counter-argument stays where it is written — a ratified decision with its counter-argument deleted cannot be re-opened honestly.** ⚠ **Ratification changes no evidence class: one relayed incident, a structural chain verified by reading, nothing measured.**

---

## Phases

**Phase 0 is the `## Decisions to ratify` section above; nothing below starts before its `### Phase 0 close record` reads anything other than PENDING.**

**Build order, and its forced dependencies.** Phase 2 needs Phase 1, because it quotes the flags Phase 1 creates. Phase 3 needs Phase 1, because its trigger reads the key Phase 1 stores. Phases 4 and 5 are independent of Phases 1–3 and of each other. Phase 6 runs last because it records what the earlier phases did. ⚠ **Phase 1 alone ships a key nothing requires and nothing reads; this plan is not shippable as Phase 1 alone.**

### Phase 0 — Ratification gate

D1–D8 and OQ-1–OQ-3 go to the maintainer. **NO build phase may start before a close record exists.**

#### Verify

- The `### Phase 0 close record` section names **each** of D1–D8 and OQ-1–OQ-3 with an explicit disposition. **No item is silently omitted**, and each is checked **by NAME, never against a range** — an item with no Verify line cannot fail.
- **D3's outcome names BOTH the citation rule and the dedicated-flag-versus-prose fork.** A record that ratifies "the citation rule" without naming the fork has not closed D3. **And it names a THIRD thing: an explicit pick between D3's two candidate resolutions for the uncitable row — (a) the row is still recorded but FORBIDDEN from the `no-code-change` value, or (b) a new Step 4.3 verb records the deferral at `/devforge:specify`'s Phase 4.** Ratifying the citation rule while leaving that route open ships a rule whose escape hatch has no mechanism.
- **D4's outcome names the posture (advisory / blocking / declined) explicitly**, because declining D4 changes what Phase 3 is. **And it names the MATCH PREDICATE too** — Phase 3's `#### Verify` pins the verb to *"the one D4's outcome ratified"*, so a posture-only outcome leaves that check unsatisfiable and the builder picks the predicate by default.
- It states whether per-item deliberation was supplied, and whether the close was an explicit pick or a delegation.
- **Every counter-argument above is still present, unshortened.**
- The record says what the outcomes put in scope: **D2 decides whether Phase 1 exists**, **D3 decides Phase 2's content — and its resolution-arm pick decides part of Phase 1 too: a ratified (b) puts a new setter, its tests and its Step 4.3 documentation in scope and OVERRIDES Phase 1's `No new subparser` line; a ratified (a) that KEEPS the two-value enum leaves Phase 1 exactly as written; and a ratified (a) carrying a THIRD enum value ALSO OVERRIDES D2's declared `code-change` | `no-code-change` pair and Phase 1's `choices` over the two values**, **D4 and OQ-3 together decide whether Phase 3 exists and where the check lives**, **D5 decides whether Phase 4 exists**, **D6 decides whether Phase 5 exists**, **D7 decides that no phase touches `/devforge:plan` or `/devforge:breakdown`**, and **D8 decides whether Phase 1 touches `_render.py` at all, and whether Phase 1's `cbm_sync_helper` clause fires. And D8's outcome names TWO things BEYOND render-or-not: the SHAPE it ratifies — two added columns, or the fold into the Impact cell D8's own COUNTER rejects — and whether the rendered `path_evidence` is BACKTICKED.** A render-only outcome closes neither: it leaves Phase 1's ratified-D8 test bullet — whose assertions are made over output `_render.py` itself produced, never over a fixture — unsatisfiable under a bare render, and it leaves the fold, which `## Tripwires` polices as a shape that can actually ship, for the builder to take by default.

### Phase 1 — Helper: the role key and the citation flag

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn**, per the repo's test-immediately-after-write rule. Commit by explicit path.

#### Deliverables

- `src/devforge/lib/_specify/_cli.py` — `--change-kind` on the existing `record-affected-area` subparser with `choices` over the two values, and `--path-evidence`. **No new subparser.** ⚠ **That line holds under a ratified D3 (a). A ratified D3 (b) OVERRIDES it**: (b)'s Step 4.3 deferral verb is a SECOND subparser in this same module, with its own setter and its own tests, and **Phase 0's `#### Verify` is where that arm is picked — a builder who finds no pick has no mandate to choose one here.** ⚠ **The `choices` over the two values holds under a ratified D3 (a) that KEEPS the two-value enum. A ratified D3 (a) carrying a THIRD enum value OVERRIDES that clause, and D2's declared `code-change` | `no-code-change` pair with it**: `choices` then carries three values, and **Phase 0's `#### Verify` is where THAT arm is picked too — a builder who finds no pick has no mandate to invent a third value here.** ⚠ **`No new subparser.` survives the third-value arm untouched — a third enum value adds no subparser** — and D3's SHAPE and D4's filter both key on the `no-code-change` value alone, so neither trigger moves on that arm. ⚠ **Named against the `--impact` collision recorded in L4, not into it.**
- `src/devforge/lib/_specify/_cmds_phase4_setters.py` — the row carries the new keys.
- **BOTH row descriptions updated in the same unit** — the setter docstring at `_cmds_phase4_setters.py:276` and the subparser help at `_cli.py:421`. ⚠ **Neither is widened to describe the discover-lane key (Correction 2) — that drift is not this plan's — and neither is left behind by the other.**
- `src/devforge/lib/_specify/_render.py` — the §4 table carries the two new values **if and only if D8 ratifies rendering them**. ⚠ **A declined D8 leaves this file untouched by this phase**: the render already reads every affected-area field through `.get` with a default — `""` for the two scalars at `:251` and `:253`, `[]` for the files join at `:252` (Correction 2) — **so an unknown extra key is simply not read** and it tolerates the new keys with no edit, and **the `cbm_sync_helper` clause in the bullet below then cannot fire**, because nothing else in this phase changes the render. ⚠ **A ratifying D8 also settles whether the rendered `path_evidence` is backticked** — D8's **A fact the render decision must carry, verified today.** paragraph — and that, not Correction 3's regex reading alone, is what decides whether the parser has any work to do.
- Every consumer D2 enumerates **that READS a §4 row** — out of specify state, or out of the rendered `spec.md` — updated to tolerate the new keys, **including `src/devforge/lib/cbm_sync_helper.py`'s rendered-markdown parser** if and only if the §4 render changes. ⚠ **The two seed PRODUCERS D2's last bullet names — `src/devforge/lib/_research/_handoff_build.py` and `src/devforge/lib/_discover/_handoff_build.py` — are READ-ONLY here, and `## File anchors` lists both under its `Read-only here` bullet.** **They build an `AffectedArea` carrying no `change_kind` and no `path_evidence`, so "tolerate the new keys" is VACUOUS for them and neither needs an edit.** ⚠ **An edit that gives either one of the two keys falsifies D2's permanent-unclassified fact** — the fact `## Honest bounds`'s **The mechanisms reach the SETTER-AUTHORED population only** and Trap 11 both rest on — **and it widens the seeded `affected_areas` shape, which `## Non-goals`'s No widening of `spec_seeds` forbids.** **Both are excluded from this phase's allowed diff set by the `#### Verify` bullet below.**
- Tests, in the same unit as the code.

#### Verify

- New tests pass; **the existing specify test suite passes unchanged.**
- **A state file written before this phase still loads, and its rows read as unclassified — an empty string, never a fabricated `code-change`.**
- **`grep -rn "{area, files, impact}" src/` returns BOTH updated sites or neither** — the two strings are worded differently (`"Append a §4 Affected Areas row …"` versus `"Append §4 row …"`), so a grep for either wording alone under-reports. ⚠ **Grep the shared `{area, files, impact}` token, never one of the two sentences.**
- **A test pins the bare-render baseline UNCONDITIONALLY**: a §4 row whose Files cell is the bare `", ".join(a.get("files", []))` the template emits today — no backtick anywhere in that cell — yields NO harvest from the Files column at all by `_parse_affected_areas`. ⚠ **That assertion holds on BOTH D8 outcomes**, because neither shape D8 contemplates — two added columns, or the fold into the Impact cell its COUNTER names and rejects — touches the Files cell. **On a ratified D8 the SAME test unit adds Correction 3's regex reading**, asserted over output `_render.py` itself produced and never over a hand-authored fixture: a rendered `path_evidence` carried as a backticked `path:line` token is NOT harvested, and a backticked `path.ext` token IS. ⚠ **Both assertions are asserted by a test, never by re-reading the regex.** ⚠ **The baseline is what makes the second assertion meaningful.** Without it a passing `path:line`-is-not-harvested test can pass for the wrong reason, because nothing in §4 is backticked today, so the token the assertion looked for was never rendered as a backticked token in the first place. ⚠ **On a DECLINED D8 nothing renders `path_evidence` at all, so ONLY the baseline applies and Correction 3 stays a READING of the regex** — recorded as a reading and never as a tested fact, and never propped up by a hand-authored fixture, which `CLAUDE.md`'s test rule sends back to a round-trip through the real producer.
- `git diff --stat src/devforge/lib/` lists only the modules the allowed diff set contains, **and that set is stated as an OUTCOME, never as a role**: **the modules D2 enumerates MINUS `src/devforge/lib/_research/_handoff_build.py` and `src/devforge/lib/_discover/_handoff_build.py`, PLUS `src/devforge/lib/_specify/_cli.py`; and on a declined D8 that whole set MINUS `src/devforge/lib/_specify/_render.py` and `src/devforge/lib/cbm_sync_helper.py`**. **`src/devforge/lib/_specify/_cli.py` is this phase's FIRST deliverable**; the two `_handoff_build.py` modules are READ-ONLY here and the Deliverables bullet above says why they need no edit; and a declined D8 needs no render edit at all — the render already tolerates the new keys — **and with the render untouched the `cbm_sync_helper` clause the Deliverables bullet above makes conditional CANNOT FIRE, so that parser needs no edit on that arm either.** **So any `_render.py` or `cbm_sync_helper.py` line in `git diff --stat` trips the check on that arm, and any `_handoff_build.py` line trips it on BOTH arms.** ⚠ **`_cli.py`'s absence from D2's enumeration is NOT an oversight in D2 and is never "fixed" by adding it there: D2 enumerates the ROW's CONSUMERS, and `_cli.py` is where the FLAGS are declared** — a producer D2 had no reason to list. ⚠ **This phase's test modules land under `tests/lib/`, OUTSIDE the path this command measures**, so they never appear in its output and their absence from it is never read as "no tests were written" — the `New tests pass` bullet above is what covers them. ⚠ **Stated by outcome because `_render.py` is ALREADY a member of D2's enumeration, so a "plus `_render.py`" clause adds nothing to the set, and `git diff --stat` reports PATHS, never producer-versus-consumer roles** — under a declined D8, role wording lets a stray `_render.py` edit pass the very branch this bullet exists to police. ⚠ **A module outside the allowed set means the blast radius was mis-measured; see `## Tripwires`.**
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — `/devforge:specify` Step 4.3 directive

**Route: instruction-author → instruction-reviewer.** Instruction-only: **no `.py` changes.** **Needs Phase 1** — it quotes the flags Phase 1 created.

#### Deliverables

- `src/commands/specify/main.md` Step 4.3 — **the `record-affected-area` bash block carries every flag Phase 1 made required**, in the same form Phase 1 created them, so the documented call and the setter's signature describe ONE invocation. ⚠ **This block is the ONLY authoring call site in the repo** — `grep -rn "record-affected-area" src/commands/` returns exactly one hit (`src/commands/specify/main.md:644`) — **so a required flag missing here is missing everywhere.** ⚠ **A prose rule that is not reflected in the copied bash block ships a Step 4.3 whose FIRST command fails**, on argparse's missing-required-argument error (exit 2), before it records anything. ⚠ **The digits drift; find the block by grepping `record-affected-area`.**
- `src/commands/specify/main.md` Step 4.3 — the D3 citation rule, **worded as a sibling of the shipped §5.2 paragraph**, plus the §8 Open Questions / §9 Risks route for the uncitable PATH CLAIM **in the form D3's ratified resolution defines it** (under **(a)** the row is still recorded and only the claim routes; under **(b)** a new Step 4.3 verb records the deferral), plus the honesty bound that the citation makes the claim inspectable and never correct.
- A cross-reference sweep over the two governing paragraphs — **Covering a user-facing surface takes two entries** (`src/commands/specify/main.md:652`) and **Every covered surface needs its own AC** (`:662`) — **so the three read as one rule.** ⚠ **Both digits drift; find those paragraphs by their bold lead-ins.**

#### Verify

- `grep` shows no dangling reference to any flag or verb name the built phases did not create.
- **Every flag Phase 1 made required appears in the Step 4.3 bash block** — checked by grepping each flag name in `src/commands/specify/main.md`. ⚠ **The bullet above checks the OPPOSITE direction: a name the block uses that no phase created. Both are needed — one catches a phantom flag, the other a missing one, and neither catches the other's case.**
- **The new paragraph names the same §8 Open Questions (Step 4.7) / §9 Risks (Step 4.8) route the §5.2 paragraph names**, in the same words, so a reader meets one route and not two.
- **The three paragraphs are mutually consistent**: the two-entries rule, the own-AC rule and the citation rule do not contradict each other about when a surface counts as covered.
- **No emitted sentence names plan vocabulary**, and no emitted sentence claims the citation proves the claim correct.
- The live-spec tests are green: `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py`, `tests/scripts/test_claude_emitter.py`.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 3 — The D4 advisory cross-check

**Route: python-engineer → python-reviewer for the verb; instruction-author → instruction-reviewer for the call site.** **Needs Phase 1.** Commit by explicit path.

#### Deliverables

- The verb, at the home OQ-3 ratified, plus its subparser and its tests.
- `src/commands/specify/main.md` Phase 4 — the call, **beside the existing `verify-scope-coherence` call**, with the same non-blocking framing the existing warning carries.
- A cross-reference sweep over the two OTHER sites in the SAME file that describe this advisory surface, **so the new verb is described wherever the existing one is, with the same non-blocking framing**: the §6 exhaustiveness paragraph (`src/commands/specify/main.md:727`, *"is surfaced by `verify-scope-coherence` at Phase 4 Step 4.9 as a non-blocking warning for the author to reconcile"*) and `## IMPORTANT RULES` item 11 (`:1019`, *"**§5↔§6 coherence is a non-blocking warning**"*). ⚠ **Every digit here drifts; find the sites by grepping `verify-scope-coherence` — and that grep over this one file returns FOUR hits, not two.** **Each hit is ruled on by READING it, never by counting** — the discipline Correction 1 and Trap 4 already set for this plan's other multi-hit grep: **`:840`** is the existing Phase 4 CALL the deliverable above places the new call beside; **`:727`** and **`:1019`** are the two description sites this sweep covers; and **`:725`** is the exclusion-marker paragraph, which mentions this advisory surface only as a DISPOSITION instruction for one false-positive class — *"A `verify-scope-coherence` warning (Step 4.9) whose overlap tokens are only the marker's own words … is a false positive of that heuristic: note it and proceed"* — **and that false positive is one the new §4↔§5 verb cannot produce, because it never reads a §6 entry, so `:725` is read and left untouched.** ⚠ **`CLAUDE.md`'s cross-check-after-every-change rule makes this part of the SAME change, not a follow-up** — a new advisory verb left out of the two places the existing one is described is an advisory surface the spec under-reports to its own author. ⚠ **Neither existing `verify-scope-coherence` sentence is reworded: the new verb gets its OWN sentence beside them**, because those two describe a §5↔§6 check and this one is a §4↔§5 check.

#### Verify

- **The verb warns on a planted contradicting pair in a fixture and stays silent on a planted consistent pair; it exits 0 in both cases.**
- **A planted consistent pair means an AC that names the surface in order to assert it stays unchanged** — the case D4's reversal turns on. ⚠ **If that fixture warns, the trigger is wrong; see `## Tripwires`.**
- The verb reads `change_kind` from state and **never matches on the phrase "no code change".**
- **The predicate the verb implements is the one D4's outcome ratified, named explicitly in the test** — the test asserts that predicate by name and by behaviour, not merely that some fixture pair warns. ⚠ **Under D4's RECOMMENDED substring predicate it is NOT `tokenize_for_overlap`** (`src/devforge/lib/_shared/text_overlap.py:58`, imported by `_cmds_phase4_verify.py:28`): **reusing that helper entangles this enum-keyed trigger with the deliberately fuzzy heuristic OQ-3 exists to keep separate**, and a future session tuning one would silently tune the other. ⚠ **If D4's outcome ratifies a TOKEN-OVERLAP predicate instead — the arm D4's own RECOMMEND rejects, reusing `tokenize_for_overlap` — that outcome OVERRIDES OQ-3's separation argument, and this bullet is REWRITTEN to the ratified predicate rather than satisfied by default.**
- **A false-NEGATIVE fixture is recorded as a KNOWN MISS, not as a pass**: an AC that asserts a change on the surface in words the ratified predicate cannot match produces no warning, and the test records that silence as a known miss rather than as correct behaviour. ⚠ **The fixture is DEFINED BY the ratified predicate, so it is written after Phase 0's pick and never before it** — under D4's RECOMMENDED substring predicate those are words that do NOT contain the row's `area` string, which is D4's own recorded counter; under a ratified TOKEN-OVERLAP predicate they are words that share no overlap token with it. ⚠ **A check that is silent because it matched nothing reads identically to a check that is silent because the spec is clean, and only a recorded known-miss tells the two apart.**
- `verify-scope-coherence`'s own output is byte-unchanged.
- The full `tests/lib` suite is green; python-reviewer and instruction-reviewer each return SHIP-READY, or every finding is fixed.

### Phase 4 — `/devforge:research` Phase 2.4e band anchor

**Route: instruction-author → instruction-reviewer.** Instruction-only. Independent of Phases 1–3.

#### Deliverables

- `src/commands/research/main.md:787` — the added requirement that each band value names the hop it rests on.
- `src/commands/research/main.md:782` — **the EVIDENCED-surface template, which is a line inside the Step 3 bash fence and not a paragraph**, updated to match; **and the SUSPECTED-surface form updated with it, which does NOT sit beside that line: it lives in `:787`'s prose paragraph**, the same paragraph as the governing sentence quoted in L1 and as the added requirement in the bullet above. ⚠ **The band lives in BOTH templates (L1); updating one is half the change.**

#### Verify

- **The two lines agree** — the template's band shape and the prose requirement describe the same string.
- **Both templates carry the anchored band**, evidenced and suspected alike.
- **No other file references the old band shape** — L2's grep is the check, run with Correction 1's discipline: `src/commands/research/main.md:425` is Phase 2.3b prose and is **not** a band site; it is left untouched.
- **No new setter, no new verify check and no handoff field were added** — that is D5's explicit v1 boundary.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 5 — `/devforge:verify` read-target sentence

**Route: instruction-author → instruction-reviewer.** Instruction-only. Independent of Phases 1–4.

#### Deliverables

- `src/commands/verify/main.md` — one sentence at the changed-files bullet (`:207`): an AC that names a user-facing surface directs the agent to read that surface's construction site even though it is not in `scope.json`'s `files` list.

#### Verify

- **The sentence names the construction site as a read target OUTSIDE `scope.json`'s `files` list**, explicitly, so it cannot be read as a restatement of the existing bullet.
- **It contradicts no `ac_verification_mode` branch** — it adds a read target in every mode rather than changing what any mode does, and it does not imply a browser.
- **No new config key, no new probe, no second runtime channel** — D6's rejection is honored by the diff, not only by the prose.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 6 — Docs sweep

**Route: instruction-author → instruction-reviewer. Docs only.** ⚠ **Other sessions are building in this checkout and several ledger files are already modified by other work. Re-read `git status`, read each ledger LIVE, re-derive every edit from what is there, and commit by explicit path — never `git add -A`, and never a wholesale sweep. Never touch another session's plan file.**

#### Deliverables

- `CHANGELOG.md` — one entry, **with the evidence class FIRST and the honest bounds LAST**, placed into whatever unreleased section exists at build time. ⚠ **A released version block is never edited.**
- `DEVELOPMENT-STATUS.md` — an edit or a recorded verified no-op, with the grep that shows it.
- `CLAUDE.md` — **a router row ONLY if one is warranted**, decided by reading the router table live. ⚠ **`CLAUDE.md` carries development instructions, not history; it carries no plan index. A row is warranted only if this plan creates a new topic the router does not already point at.**
- Whatever plan ledger exists at build time, **re-derived from the ledger itself rather than copied from a sibling plan's site list.**

#### Verify

- Every site above is recorded as an **edit or an explicit verified no-op**, with the grep that shows it.
- **`grep` for each new flag name and each new verb name returns only intended sites.**
- **No ledger line belonging to any neighbouring plan is altered or reflowed** — `git diff` on shared files shows only this plan's own additions.
- **No ledger sentence claims any phase is consumer-validated. "Built and build-verified" is the ceiling in every line.**
- **No tracked file names a client, an install, a repo, a branch, a ticket id or any benchmark identifier.**

### Phase 7 — Consumer e2e — user-driven HARD GATE, DEFERRED by default, NOT run

⚠ **Deferred by default, per the house pattern, and explicitly NOT WAIVED. Everything Phases 1–6 ship is build-verified at best and NEVER consumer-validated until this phase runs, and "done" never means Phase 7 passed.**

- **Fixture:** a testForge20 feature. ⚠ **The frozen benchmark install is never touched.**

The anchors are known-answer cases, **scored explicitly and in their pairs**:

1. **A §4 row claiming `no-code-change` with a cited construction site** → the row records, the spec renders, and the D4 check is silent when no AC asserts a change on that surface.
2. **The same row with an AC that DOES assert a change on that surface** → the D4 check warns and **exits 0. PAIRED WITH 1: a change that makes the check warn on both passes neither.**
3. **A `no-code-change` row with no citable construction site** → **scored against D3's ratified resolution, never against one arm of it**: under **(a)** the row still enters §4 but never carrying the `no-code-change` value, and the uncitable path claim takes the §8/§9 route beside it; under **(b)** the new Step 4.3 verb records the deferral and no such row enters §4 at all.
4. **A `/devforge:verify` run whose AC names a surface whose construction site is outside the diff** → the agent reads that site and says so in its report.

#### Verify

- **Every anchor is scored explicitly — stated, not summarized — with anchors 1 and 2 scored together.**
- **If an anchor fails, record the negative with the artifacts and NAME THE MECHANISM before proposing anything:** a silent check on anchor 2 is **D4's predicate**; a warning on anchor 1 is **D4's trigger**; on anchor 3 the mechanism is read against D3's ratified resolution before it is named — under **(b)** an uncited row entering §4 at all is **D3's instruction half**, while under **(a)** that same row is the CORRECT outcome and **D3's instruction half** is named only by a row carrying the `no-code-change` value or by a missing §8/§9 route beside it; an unread construction site on anchor 4 is **D6's instead-clause**. ⚠ **They have different fixes.**
- ⚠ **A clean run shows the mechanisms behave on planted fixtures, never that the gap cost anything on any real run.**

---

## Honest bounds

⚠ **These are the plan's ceiling. Any summary that drops one overstates the plan.**

- **The incident is relayed, not re-readable from this repo.** The five-link structural chain WAS verified against this tree on 2026-09-20; **the incident behind it was not, and NOTHING WAS MEASURED.** No rate, no frequency, no cost.
- **D3's citation makes a claim INSPECTABLE, never CORRECT.** A wrong `file:line` reads exactly like a right one. The bound is `src/commands/research/main.md:741`'s, inherited verbatim.
- **Static reachability is bounded by dynamic dispatch** — inherited verbatim from the §5.2 bound. **A cited construction site shows the surface IS reached that way; it never shows the citation exhausted every path.**
- **D4 is advisory, so a confident author can read past it** — and `FINDINGS.md` finding 4 says that is *precisely* the author who produces this defect. ⚠ **Only the CONFIDENT-AUTHOR half of finding 4's quoted objection transfers, and D4 carries the correction: the opt-in half was retired by finding 4's own AMENDED 2026-08-19 entry, and D4's verb would run unconditionally inside Step 4.9 regardless — so the surviving objection is about advisory OUTPUT, never about whether the check runs. The word ADVISORY is this plan's own, taken from finding 4's EARLIER clause *"But `/spec-check` is opt-in and ADVISORY by ratified D14"* and NOT from that objection — it names the posture that makes the confident-author half bite on D4.** **This is the plan's weakest joint and it is not argued away.**
- **The role key narrows the dodge surface without closing it.** An author can classify a row `code-change` and write the inheritance claim into `--impact` anyway, where no citation is required and nothing keys on it. **Said plainly: D2 makes the honest path structural; it does not make the dishonest path impossible.**
- **The mechanisms reach the SETTER-AUTHORED population only.** Every §4 row seeded by `import-handoff` on the research and discover lanes arrives unclassified and stays unclassified, because neither lane ever calls `record-affected-area`. **So D3's citation duty never binds a seeded row, D4's check never examines one, and nothing in this plan counts how many rows are in that state.** ⚠ **The coverage claim this plan may make is "rows an author wrote at Step 4.3", NEVER "rows in §4".**
- **D4's reach is bounded by its PREDICATE before it is bounded by its POSTURE.** Even inside the setter-authored population, the check finds only the ACs the ratified predicate can match — **under D4's RECOMMENDED substring predicate** those are the ACs whose `statement` literally contains the row's `area` string; **under a ratified TOKEN-OVERLAP predicate** — the arm **D4's own RECOMMEND rejects**, reusing `tokenize_for_overlap` — those are the ACs whose `statement` shares an overlap token with it. **On either arm, an AC that asserts a change on that surface in words the ratified predicate cannot match is invisible to it.** **That bound sits UPSTREAM of the advisory-posture bound recorded above** — a reader who drops it hears "advisory" and assumes the check saw the pair and merely declined to block. ⚠ **A clean Phase 7 shows the predicate works on fixtures BUILT TO SATISFY it; it never shows it works on ACs written naturally.**
- **No mechanical detector is proposed for band correctness at `/devforge:research`. D5 is prose**, and L2 already proved the band is mechanically unconsumed.
- **This plan adds no gate.** D4's verb always exits 0; D2's enum rejects an invalid value but not a wrong one. **Nothing here blocks anything.**

---

## Tripwires

- **If Phase 1 needs to change the `AffectedArea` dataclass shape in more than the consumers D2 enumerates, STOP and re-scope** — the blast radius was mis-measured, and D2's counter-argument was stronger than its recommendation. ⚠ **The dataclass shape is not the only way to trip this, and keying on it alone leaves an escape.** Phase 1's `#### Verify` is keyed on the DIFF SET, **stated as an OUTCOME and never as a role**: any module outside the set that Verify allows — **the modules D2 enumerates MINUS `src/devforge/lib/_research/_handoff_build.py` and `src/devforge/lib/_discover/_handoff_build.py`, PLUS `src/devforge/lib/_specify/_cli.py`; and on a declined D8 that whole set MINUS `src/devforge/lib/_specify/_render.py` and `src/devforge/lib/cbm_sync_helper.py`** — appearing in `git diff --stat src/devforge/lib/` trips this tripwire the same way, **whether or not the dataclass shape changed.** ⚠ **`_render.py` is ALREADY a member of D2's enumeration, so a "plus `_render.py` when D8 ratified rendering" clause would add nothing to the set and would let a stray `_render.py` edit pass on the declined-D8 arm this tripwire exists to police.** ⚠ **The two `_handoff_build.py` modules are ALSO members of D2's enumeration — D2's last bullet names both — so the MINUS on them is LOAD-BEARING and is never dropped as redundant: they are seed PRODUCERS that emit no `change_kind`, `## File anchors` lists both under its `Read-only here` bullet, and an edit to either falsifies D2's permanent-unclassified fact.**
- **If the D4 check's fixture work shows the ratified predicate's match produces false positives on ordinary specs, the trigger is WRONG, not the threshold. STOP and return to Phase 0.** Tuning a threshold on a trigger that is matching the wrong thing produces a check that is quiet for the wrong reason.
- **If the D4 check is SILENT across every fixture INCLUDING the planted contradicting pair, STOP** — the predicate matched nothing, so the check is decorative rather than advisory. ⚠ **A check silent for lack of a match reads identically to a check silent on a clean spec**, which is why silence is never scored as a pass here. **The named suspect is the population fact D4 records:** a seeded row carries no `change_kind` at all, so D4's `change_kind == "no-code-change"` filter never reaches it — which is why a fixture whose row came from `import-handoff` rather than from `record-affected-area` can never match.
- **If a session finds itself grepping for the phrase "no code change", the plan has reverted to plan 77 R3's failed shape. STOP.** The trigger is the enum, always.
- **If the §4 render EMITS either of the two shapes D8 contemplates — a new column, or the fold of `change_kind` and `path_evidence` into the existing Impact cell that D8's COUNTER names and rejects — and `cbm_sync_helper._parse_affected_areas` was not re-tested in the same unit, STOP** — Correction 3 is a reading of a regex, and a reading is not a test. ⚠ **Keying this on a new COLUMN alone is a slip-path, not a trigger: under the fold the render CHANGES and gains NO column, so a column-keyed tripwire never fires — yet the folded `path_evidence` lands in the Impact cell, which the harvest DOES read, because the scan runs from the `## 4.` heading to the next `## N.` heading and is never scoped to one cell.**
- **If any phase reaches for a browser, a runtime URL or a second `ac_runtime_*` key, STOP** — that is D6's rejected arm arriving under another name.

---

## Non-goals

- **No browser or runtime channel at `/devforge:research`** (D6). The runtime band exists and is owned by `/devforge:verify`.
- **No typed handoff field and no new research verify check for the band** (D5 defers both to a separate, larger plan). ⚠ **Check number 21 is recorded as today's next-free, never reserved.**
- **No widening of `spec_seeds`** — L3 is a fact this plan routes AROUND, not one it changes. Phase 2.4e findings still do not reach `/devforge:specify` as typed data.
- **No change to `/devforge:spec-check`'s ratified advisory stance.**
- **No change to `/devforge:plan` or `/devforge:breakdown`** (D7).
- **No change to `verify-scope-coherence`'s predicate, output or non-blocking posture.**
- **No new `verify-*` gate that can fail a build** — D4's verb always exits 0.
- **No fix for the pre-existing discover-lane drift in the two `{area, files, impact}` row descriptions** (Correction 2) — the setter docstring and the subparser help. Phase 1 brings both in step with the keys IT adds and stops there. **Named here so the omission is not mistaken for damage this plan did.**
- **No back-port into shipped installs.** They arrive via `install.sh` / `update.sh`.
- **No touch of any external install, and no client, install, repo, branch, ticket id or benchmark identifier in any tracked file.**

---

## Context for next session

⚠ **Evidence class, repeated: ONE observed consumer incident, RELAYED from a peer session on 2026-09-20, artifacts NOT re-readable from this repo — plus structural facts grep-verified against THIS tree the same day. The chain was verified here; the incident was not. NOTHING WAS MEASURED.** ⚠ **All line digits drift — grep the quoted text, never the digits.**

**The one sentence that governs everything here: a spec must not be able to claim a surface is covered without a code change, and separately assert what that surface sends, with nothing comparing the two and nothing asking how the surface is reached.**

**Provenance of this plan, stated so it is not mistaken for first-hand observation.** It originated from a peer-session relay on 2026-09-20 plus a verification pass against this tree made the same day. The anchors in `## Origin & evidence` were exact when written. ⚠ **They must be re-verified before being acted on: other sessions are editing `src/commands/specify/main.md` and `src/commands/research/main.md` in this same checkout.** ⚠ **Phase 0 is the gate and nothing below it may start.**

### Traps

**Trap 1 — triggering on the phrase.** Any rule keyed on the words "no code change" repeats plan 77 R3's documented failure: the directive was present, correct and shipped, **and the bad AC was written anyway** because it did not match the lexical trigger. **The key is the enum.**

**Trap 2 — claiming the citation proves the claim.** D3 buys inspectability. `src/commands/research/main.md:741` and the §5.2 paragraph's closing sentence both say why, and both wordings are available to reuse.

**Trap 3 — reading the missing browser as the cause.** The refuting evidence is in an UNCHANGED file. A runtime channel does not put it in the diff, and `/devforge:verify`'s changed-files bullet (`src/commands/verify/main.md:207`) is the site that matters.

**Trap 4 — counting the band grep's hits.** Four hits, enumerated in Correction 1 — two band authoring sites (`src/commands/research/main.md:782` and `:787`), one unrelated error string (`src/devforge/lib/_generate_docs/_setters.py:112`) and one Phase 2.3b framing line (`:425`). **Score the grep against that list, never against a remembered number.** `src/commands/research/main.md:425` is Phase 2.3b prose sharing the words. **Discard it by reading it.**

**Trap 5 — treating the fourth row key as unprecedented.** The discover lane already writes a fourth key (Correction 2). **D2's real cost is the required-flag break on the setter, not the key count.**

**Trap 6 — assuming the §4 consumers are all state readers.** `cbm_sync_helper._parse_affected_areas` reads the RENDERED `spec.md` (Correction 3). A render change reaches it; a state change does not.

**Trap 7 — mirroring §5.2 without noting the divergence.** §5.2's citation is prose in an existing field; D3 proposes a dedicated flag. **They are not the same mechanism, and D3's fork is ratified or declined with D3.**

**Trap 8 — conflating the two `affected_area` meanings.** In `/devforge:research` it is the memo dimension carrying the user's own answer (15 hits, one file); in `/devforge:specify` it is the §4 row. **D7's grep is only sound once they are told apart.**

**Trap 9 — quoting a `file:line` from this plan as current.** Every anchor here was true on 2026-09-20 and drifts on the next edit to those files.

**Trap 10 — reading the structural chain as evidence of frequency.** The chain says the gap EXISTS. **One relayed run says it fired once. Nothing says how often.**

**Trap 11 — reading "unclassified" as a legacy state.** It is PERMANENT: `import-handoff` writes unclassified §4 rows on both seeded lanes forever, so an absent `change_kind` says nothing about WHEN the row was written. **A session that treats the unclassified set as a shrinking migration backlog will plan a cleanup that has no end state.**

**Trap 12 — assuming the §4 render backticks anything.** It does not — the row template emits `", ".join(a.get("files", []))` bare. **Any reasoning about what `cbm_sync_helper` harvests from §4 starts there**, and D8 is what decides whether that changes.

**Trap 13 — assuming the new keys reach `/devforge:plan` through the handoff.** They do not. `src/devforge/lib/_specify/_cmds_handoff.py:1321-1326` rebuilds each §4 row for the specify→plan handoff from the whitelist `("area", "files", "impact")` alone, so `change_kind` and `path_evidence` are DROPPED silently at that hop **whatever D8 decides**. ⚠ **The drop is consistent with D7's NO and is not a bug: no phase of this plan adds the two keys to that whitelist.** ⚠ **D2 enumerates this re-read among the row's consumers, but "tolerate the new keys" is what the whitelist ALREADY does by dropping them, so the work is VACUOUS and Phase 1 edits nothing AT THE RE-READ.** ⚠ **That says nothing about the rest of the module: D2's `_cmds_handoff.py` bullet names four OTHER sites, so the module stays inside Phase 1's allowed diff set and is never subtracted from it on the strength of this trap.** **The §4 render is therefore the only channel that can carry the two values to a reviewer**, which is why D8 decides whether they are visible at all.

### File anchors

- **`src/commands/specify/main.md`** — Step 4.3's `record-affected-area` block and its two governing paragraphs; Step 4.4's §5.2 Behavior preservation paragraph (the precedent, read-only here); Phase 4's `verify-scope-coherence` call.
- **`src/commands/research/main.md`** — Phase 2.3b's surface-count frame (read-only; Correction 1); Phase 2.4e's Identity evidence paragraph, its Step 3 template and the prose that governs the band.
- **`src/commands/verify/main.md`** — the Chrome MCP probe section and the changed-files bullet in the `ac-verifier` brief.
- **`src/devforge/lib/_specify/_cli.py`** — the `record-affected-area` subparser, and `record-risk`'s enum-valued `--impact` as the naming precedent.
- **`src/devforge/lib/_specify/_cmds_phase4_setters.py`** — `cmd_record_affected_area` and its docstring.
- **`src/devforge/lib/_specify/_cmds_phase4_verify.py`** — `cmd_verify_scope_coherence` and its affected-area arm.
- **`src/devforge/lib/_specify/_render.py`** — the §4 table and the four affected-area reads.
- **`src/devforge/lib/_specify/_cmds_handoff.py`** — the two affected-area serializers, `cmd_import_handoff`'s `spec_seeds` read, and the specify→plan handoff re-read.
- **`src/devforge/lib/cbm_sync_helper.py`** — `_parse_affected_areas` and `_AFFECTED_AREAS_FILE_RE`.
- **Read-only here:** `src/devforge/lib/_research/_handoff_build.py`, `src/devforge/lib/_discover/_handoff_build.py`, `src/devforge/lib/_research/_cmds_render_verify.py`, `src/devforge/lib/_configure/_schema.py`, `FINDINGS.md` findings 4 and 5.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation.
2. **Check `### Phase 0 close record` first** — it sits at the end of `## Decisions to ratify`. While it reads *PENDING*, nothing is ratified and **no build phase may start.**
3. **Re-verify L1–L5 and the three Corrections against the live tree.** Grep the quoted text, never the digits: `reached through the changed code`, `a different path`, `The evidence is yours to cite`, `record-affected-area`, `--impact`, `{area, files, impact}` (**this token, never either of the two sentences that carry it**), `Covering a user-facing surface takes two entries`, `Every covered surface needs its own AC`, `The same standard binds every AC entering §5.2`, `seeds = handoff.spec_seeds`, `inbound_callers`, `_build_affected_areas`, `cmd_verify_scope_coherence`, `_parse_affected_areas`, `Changed files`, `ac_runtime_url`, `is_internal_extension_candidate`. ⚠ **After a build phase some of these strings have changed by design; a changed hit is then the built state, not a regression.**
4. **Re-check the plan number.** 100, 101, 102, 104, 105 and 106 were taken in this checkout on 2026-09-20 and 103 was vacated by a renumbering. **Another session may have taken 107 since.** ⚠ **Find a sibling plan by its TITLE, never by assuming a number.**
5. **Build order:** Phase 2 and Phase 3 each need Phase 1; Phases 4 and 5 are independent; Phase 6 runs last. ⚠ **Never stop after Phase 1** — a role key nothing requires and nothing reads is worse than no key, because it looks like coverage.
6. **Route every edit through the house flow:**
   - python-engineer → python-reviewer for every Python edit, with a test per function, run in the same turn;
   - instruction-author → instruction-reviewer for every markdown edit;
   - `claude-code-guide` for every new Claude-Code-integration fact.
7. **Commit by explicit path, never `git add -A`.** Re-read `git status` first, and read every shared ledger live. **Never touch another session's plan file.**
8. **After each phase, cross-check.** Grep every verb, flag and phase name touched — `record-affected-area`, `--change-kind`, `--path-evidence`, `verify-scope-coherence`, the new cross-check verb, `Step 4.3`, `Step 4.4`, `Phase 2.4e` — and fix any dangling reference **in the SAME change.**
9. **Run Phase 6, then leave Phase 7 to the maintainer.**
10. **Keep the evidence class attached.** Any summary of this plan repeats it: **ONE relayed consumer incident; a structural chain verified by reading this tree; nothing measured.**
