# RESEARCH-FRAMING-REGRESSION-PLAN

**Status**: **9 patches applied + EMPIRICAL VERIFY PASSED 2026-05-18**. After 5-17 fail-verify (1.5/3 causes, below 04-30 baseline of 2/3), Patches 6-9 landed (Patch 6 = Phase 2.4d data-flow chain trace / adapter-follow forcing function; Patch 7 = Phase 2.5 id-stability hypothesis axis; Patch 8 = literal-archaeology gate; Patch 9 = argument-duplication shape check). Plus refactor: `research_helper.py` split into `src/devforge/lib/_research/` package per `REFACTOR-MONOLITHIC-HELPERS-PLAN.md` Phase D (commit `6c8545c`); shim at `research_helper.py` forwards to `_research/`.

5-18 verify run (`testForge20/research/2026-05-18-restriction-on-adding-the.md`, 24.9K) caught **3.5/3 real-ship causes** vs commits `74adb5b17` + `df231933a`: (a) shallow `Array#find` + recursive-walk recommendation ✅; (b) Strata adapter `Math.random()` rewrite at `strataFamilyToItemAdapters.ts:5` ✅ (Patch 6/7/8 paid off); (c) `partNo` fallback for stable id ✅; (d) extra defense-in-depth domain guard at `AddActiveQuoteLineUseCase` ⚠️ overshoot (real ship didn't add but architecturally correct). Beats old 5-16 caught-it baseline which had (a)+(missing classifier) but missed Strata randomization entirely.

**Coupling note (2026-05-20)**: `CONSTITUTION-STRENGTHENING-PLAN.md` work rolled back in `src/constitution.md` (0 matches for `Concrete pattern:` / `module-scope named function` / `module-boundary abstraction`; §3.6 DI reverted to generic; §3.7 reverted to Grep/Glob). /research now carries pattern-correctness alone — downstream PATTERN backstop gone, but 5-18 verify shows /research handles it without the backstop.
**Date**: 2026-05-16
**Branch**: `develop-2.0-init`
**File**: `src/commands/research/main.md` (~554 lines) + `src/devforge/lib/research_helper.py` setters + verify checks
**Trigger**: parity-test regression on identical bug, identical day, same forge version, same /research command. Old run (`testForge20/tmp/2026-05-16-restriction-on-adding-the.md`, 22.4K, 11:07) converged on correct structural diagnosis (shallow walk + parentConfigId routing + Strata id remap → domain-layer fix). Fresh run (`testForge20/research/2026-05-16-restriction-on-adding-same.md`, 14.7K, 20:14) converged on a different (incorrect) root cause (id-field comparator mismatch → Vue-only fix).

`/research` is the **first user-facing command** of the per-feature chain (`/research` → `/specify` → `/plan` → `/breakdown` → `/execute-task`). Framing locked in at /research propagates through every downstream command. A research run with wrong root cause produces a spec with wrong AC, a plan with wrong file impact, and an implementation that masks the real bug. **No silent skips, no soft mandates, no LLM judgement calls at framing decision points.**

## Context for next session

Compare both research runs side-by-side. Both ran on the same machine, same day, same `/research` command, same target codebase (`testForge20` workspace, db-cse-ui-strata package).

| Dimension | Old run (caught) | Fresh run (missed) |
|---|---|---|
| File | `testForge20/tmp/2026-05-16-restriction-on-adding-the.md` | `testForge20/research/2026-05-16-restriction-on-adding-same.md` |
| Size | 22.4K | 14.7K |
| Timestamp | May 16 11:07 | May 16 20:14 |
| Symptom > Scope | `feature-wide` | `one place` |
| Root cause | shallow `Array#find` at depth 1 + missing structural classifier + parentConfigId routing + Strata id remap | id-field comparator mismatch (`subLine.item?.id` vs `props.item?.bqItemId`) |
| Recommended approach | "Domain helper + classifier in pkg-cse-core" — cross-layer | "Fix comparator + gate with isAttachment" — Vue-only |
| Canonical-pattern hits (Phase 2.4b) | `QuoteLine.ts:97` (isAttachment static), `UpdateMachineTotalPriceUseCase.ts:15` (getAllSubLines recursive idiom) — domain-layer | `UpdateActiveQuoteLineCharge.ts:35`, `ActiveQuoteBLoC.ts:499` — activeQuote-package, bqItemId-comparator |
| Prior research / spec citation | specs/008-prevent-duplicate-config-options/spec.md cited as approved-but-unimplemented | NOT cited |
| Hypotheses enumerated | 3 (shallow detection, Strata id remap, missing structural classifier) | 2 (id mismatch, attachment over-apply) |
| Maps real ship at commit 74adb5b17 | YES (statics on CoreQuoteLine + module-scope exports + Vue rewires to named functions) | NO (proposes comparator swap; real ship kept `line.item?.id === candidateBqItemId` as match key) |

Real-ship evidence (commit `74adb5b17` in `db-cse-ui-strata`): keeps `subLine.item?.id === candidateBqItemId` comparator unchanged inside the recursive walker; adds `CoreQuoteLine.isSingleInstance` + `CoreQuoteLine.findMatchingConfigurationLine` statics; adds module-scope named function exports (`export const isSingleInstance = …`); rewires `MenuSection.vue:117` to `import { findMatchingConfigurationLine, isSingleInstance }` (NOT `import { CoreQuoteLine }`). Confirms old research was right + fresh research wrong-rooted.

## Diagnosis — nine structural gaps in /research that allowed the regression

### Gap 1 — Phase 2.3 framing lock-in propagates with no adversarial challenge

Phase 2.3 (CBM discovery chain) picks initial search literals from the symptom phrasing. LLM converges on a frame ("comparator typo" vs "shallow walk + missing classifier") in Phase 2.3 and inherits that frame through 2.4 / 2.4b / 2.4c / 2.5 / 3. Phase 2.5 hypothesis enumeration is ≥2 hypotheses *within* the chosen frame — never across competing frames.

Effect: hypothesis enumeration is hypothesis-level competition, not framing-level competition. LLM picks frame F in Phase 2.3, enumerates ≥2 hypotheses (H1, H2) both consistent with F, declares H1 confirmed. The runner-up frame F' never surfaces.

### Gap 2 — Phase 2.4c same-package stopping rule traps cross-layer bugs in the wrong layer

Phase 2.4c definition (main.md:274): *"trace AT MOST 2 layers above the symptom site through helpers in the SAME package; do not cross package boundaries"*. Designed to prevent infinite trace into framework/vendor packages. Side effect: when the symptom lives in `app-web` (Vue) and the root cause lives in `pkg-cse-core` (domain), Phase 2.4c stays in `app-web`. fix_path_helpers list passes `verify` check 8 with same-package entries; no signal to surface domain-layer helpers.

Effect: cross-layer architecture violations (the EXACT failure class the strengthened constitution §3.6 DI rule targets) are invisible to /research. /research → /specify → /plan inherits the wrong-layer framing.

### Gap 3 — Phase 1 scope narrowing without justification

Phase 1 dimension `Scope` accepts `one place` / `feature-wide` / `cross-feature` (or similar). Helper does not require evidence-of-locality when LLM picks `one place`. A premature `one place` selection prunes Phase 2 exploration depth before Phase 2 runs.

Effect: LLM that frames the bug narrow in Phase 1 stays narrow in Phase 2. Old run picked `feature-wide` → broader CBM exploration. Fresh run picked `one place` → exploration constrained.

### Gap 4 — Phase 3 approach gate doesn't flag single-layer recommendations

Phase 3 `recommended_approach` accepts any approach text. If the recommendation changes only the presentation layer (or only the domain layer), no gate fires to ask: *"is the symptom REALLY single-layer, or did Phase 2.4c stop short of the cross-layer helper?"* Recommended approach inherits the framing from Phase 2.3 unchallenged.

Effect: even if Phase 2.4c surfaced a same-package helper, Phase 3 has no forcing function to question whether the recommendation should cross layers.

### Gap 5 — Fix-path helper target not anchored to Phase 2.3 evidence

Phase 2.4c `record-fix-path-helper --helper-qn` accepts any string. Post-Patch-2 `--file-line` anchors it to a CBM result row, but LLM still picks the row. No structural relationship enforced between Phase 2.4c fix-path helpers and Phase 2.3 findings — LLM can record findings at `MenuSection.vue:206` then invent a fix-path helper at `quoteBloc.addLine:42` that was never surfaced by CBM discovery.

Effect: 2-layer trace from a wrong starting point lands 2 layers from wrong. Constitution strengthening (`CONSTITUTION-STRENGTHENING-PLAN.md` §3.6 DI) catches **wrong PATTERN** of cross-layer fix (entity-class import in outer layer) but is **silent on wrong TARGET**. /specify, /plan, /execute-task can author a constitution-compliant wrapper-export pattern targeting the wrong code region → bug ships unfixed + new wrapper-export shipped uselessly.

Distinction from Gap 2: Gap 2 controls how far Phase 2.4c traces (stopping rule). Gap 5 controls where Phase 2.4c starts (anchor rule). Different gates.

### Gap 6 — Symbol-on-screen-but-unfollowed (adapter-hidden mutation)

Phase 2.3 CBM discovery surfaces a click-handler file (e.g., `MenuItemInfo.vue`) and the write-boundary call (e.g., `quoteBloc.addLine`), but the chain in between — adapters / transformers / mappers (`strataFamilycharacteristicOptionAdapter`, etc.) — are visible as call-site symbols but never opened. LLM can read the handler + write-boundary endpoints AND STILL miss a `Math.random()` / `Date.now()` / `uuid()` id-rewrite hiding in the adapter body two hops away.

Effect: empirical 5-17 verify failure. Real bug = `Math.floor(10000 + Math.random() * 90000)` at `strataFamilyToItemAdapters.ts:5` rewriting `bqItemId / id / baseInfo.id` per call. Adapter file was indexed by CBM, referenced by symbol at `MenuItemInfo.vue:193`, never read end-to-end. /research scored 1.5/3 on duplicate-options topic — below 04-30 baseline.

### Gap 7 — Hypothesis enumeration biased toward identifier KIND, not STABILITY

Phase 2.5 ≥2 hypothesis rule competes hypotheses within a single semantic axis. For identifier bugs, the axis defaults to KIND (id-A vs id-B field name) — same-axis competition. The STABILITY axis (stable id vs randomized-per-call) never surfaces unless the LLM independently considers it.

Effect: paired with Gap 6 — 5-17 verify's hypotheses all probed comparator-typo / id-field-mismatch (KIND axis). Production-site randomization (STABILITY axis) ungathered. Required Gap 6's adapter-follow AND Gap 7's STABILITY-axis hypothesis to converge on the real Math.random root cause.

### Gap 8 — Literal-replacement prose without git-blame archaeology

Phase 3 `recommended_approach` can propose "replace literal X with Y" without classifying whether X is a placeholder / migrated-from-legacy / deliberate-business-value / forgotten-TODO / inherited-refactor / generated-by-tool. Each intent demands a different fix scope. "Replace `Math.random()` with stable id" reads identical to "replace `MAX_RETRIES=3` with `5`" but the former is a bug, the latter a config decision. Without classification, fix lands at wrong layer.

Effect: orthogonal failure class to Gaps 1-7 — surfaced during V3 plan iteration before 5-18 verify. Closing it pre-emptively (Patch 8) gave 5-18 verify the literal-archaeology table that anchored the Math.random recommendation to "placeholder" intent.

### Gap 9 — Proposed call-shape passing same identifier twice

Phase 3 `recommended_approach` can propose a fix at a call site that passes the same identifier as multiple arguments (e.g., `addLine(id, ..., id, ...)`). Argument-duplication is a signal the fix layer is wrong — duplication means the call-site is patching around an upstream defect that should be fixed at the wrapper signature / state initialization / use-case default.

Effect: orthogonal failure class — surfaced during V3 iteration. Patch 9 forces literalized call-shape commit + duplication detection, signaling fix-layer escalation.

## Patches

Nine patches, in dependency order. All applied + empirically verified (5-18 pass: 3.5/3 causes vs real-ship commits `74adb5b17` + `df231933a`). Each leaves /research in a buildable, verifiable state.

> **Rejected patch — prior-art input source (recorded for posterity).** An earlier draft proposed a Phase 1.5 step that walked `research/*.md` + `specs/*/spec.md` for topic-slug match + recorded them via `record-prior-art`. **Rejected** because (a) /research is `Fresh-every-run` by contract (main.md:66) — prior-art read contradicts that invariant; (b) prior LLM outputs propagate stale framing — old run's cited `specs/008` itself missed the wrapper-export step that the real ship corrected at code review, so transcribing it would propagate the same half-correct framing; (c) pollution scales with project age — N stale entries per fresh run anchor LLM toward older constitution + older code state; (d) /research's contract is independent investigation from CBM + docs + constitution, NOT consensus with prior LLM outputs. Patches 1 + 2 (renumbered below) make the framing-luck delta irrelevant without LLM-to-LLM transcription.

### Patch 1 — Phase 2.3 framing-challenge gate (Gap 1)

**Where**: New phase `Phase 2.3b — Framing challenge` between Phase 2.3 (CBM discovery) and Phase 2.4 (parallel-pattern sweep).

**Change**: After Phase 2.3 records initial CBM hits, LLM MUST enumerate the ALTERNATIVE root-cause framing. Setter:

```bash
.devforge/lib/research_helper record-runner-up-framing \
    --frame "<one-sentence alternative root cause>" \
    --falsifier "<concrete evidence that would confirm THIS framing over the primary>" \
    --confidence-vs-primary "lower|comparable|higher"
```

MANDATORY single call per /research run. The LLM must commit to the runner-up frame BEFORE Phase 2.4 / 2.4b / 2.4c searches start, so subsequent searches probe BOTH frames. Phase 2.4 / 2.4b / 2.4c setters get a new optional `--framing primary|runner-up` arg; findings recorded against either framing are accepted, but verify (new check) rejects a report where runner-up framing has 0 finding rows (LLM must explicitly disprove the runner-up via at least one finding, even if the finding is a negative result).

**Verify**: re-dispatch fresh research on the duplicate-options topic. Primary frame in Phase 2.3 may still be "id-field mismatch". Runner-up frame in Phase 2.3b should be "shallow walk + parentConfigId routing". Phase 2.4 / 2.4b / 2.4c findings show probes against BOTH frames. Phase 3 recommended approach addresses BOTH explicitly — either dismisses runner-up with falsifier-verified evidence OR adopts it.

**Argue**: a framing challenge gate cannot guarantee the LLM picks the *right* runner-up. The protection is structural: forcing enumeration of a second frame breaks the cognitive lock-in pattern where the LLM commits to the first plausible frame in Phase 2.3 and stops considering alternatives. The runner-up may itself be wrong — but having two competing frames forces Phase 2.4 / 2.4b / 2.4c to gather evidence that discriminates, which is the only structural mechanism /research has to surface a mis-framing before Phase 3.

### Patch 2 — Phase 2.4c cross-layer helper surface (Gap 2)

**Where**: Phase 2.4c definition (main.md:270-348); `record-fix-path-helper` setter; helper verify check 8.

**Change**: Drop the same-package stopping rule. Replace with **layer-boundary stopping rule** — Phase 2.4c traces fix-path helpers UP through the layer stack until reaching a *layer boundary* (presentation-layer file → composable/store → domain helper → entity static; presentation → application → domain; outer → inner per Clean Architecture). The 2-layer-max constant stays, but the "SAME package" restriction goes.

Stopping rule rewrite: *"Trace AT MOST 2 layer boundaries above the symptom site, following the dependency-inversion direction (outer-to-inner). Stop at framework/vendor packages (do not trace into framework internals, vendored SDKs, or shared utility libs). Cross application/domain boundaries within the project workspace."*

Helper verify check 8 strengthens: rejects a `fix_path_helpers` list where ALL entries are in the same package as the symptom site AND the symptom site is in a presentation-layer package (component file, view, controller). Domain-layer symptoms remain same-package OK (no cross-layer required for a domain-internal bug). Detection of presentation-layer is by path heuristic, configurable per project — defaults match common conventions (`apps/app-web/`, `src/components/`, `src/views/`, component-file extensions like `.vue` / `.tsx`).

**Verify**: re-dispatch on duplicate-options topic. Phase 2.4c traces from `MenuSection.vue:207` → through `quoteBloc.addLine` → into `pkg-cse-core`. fix_path_helpers list includes at least one `pkg-cse-core` entry. Old-run pattern (`CoreQuoteLine.isAttachment`, `getAllSubLines`) surfaces.

**Argue**: layer-boundary detection is heuristic + path-pattern-based — fragile across project conventions. Mitigation: detection ruleset lives in `.devforge/configure.yaml` under a new `presentation_layer_paths` key (defaults to common Vue/React/Angular patterns; user can override per project). When detection fails (no path matches), the same-package rule remains as fallback. Trades structural rigour for project-portability — acceptable because the worst case is "rule didn't fire" not "rule fired wrong".

### Patch 3 — Phase 1 scope evidence requirement (Gap 3)

**Where**: Phase 1 `set-dimension --field scope` setter; helper verify.

**Change**: When LLM passes `--value "one place"` to `set-dimension --field scope`, the setter REQUIRES an additional `--evidence` flag with a `file:line` citation proving the bug is localized (typically the single symptom site). Without `--evidence`, setter exits non-zero with stderr explaining the rule. `--value "feature-wide"` / `--value "cross-feature"` do not require evidence (broad framings are safer defaults; narrowing is the risky direction).

**Verify**: re-dispatch on duplicate-options topic. LLM attempts `set-dimension --field scope --value "one place"` without `--evidence` → helper rejects, LLM either (a) provides evidence-of-locality (which forces the LLM to verify locality vs broad scope before committing) or (b) picks a broader scope. Either outcome correct.

**Argue**: requiring evidence for narrowing creates one extra setter call per run on the common-case "one place" framing. Cost is real (LLM has to think + cite). Benefit: prevents the silent narrow-framing failure mode that gates exploration depth before Phase 2 runs. Worth the friction at the entrypoint of the workflow chain.

### Patch 4 — Phase 3 cross-layer recommendation gate (Gap 4)

**Where**: Phase 3 `set-recommended-approach` setter; helper verify (new check).

**Change**: When `recommended_approach` text touches only one layer (heuristic: setter parses the approach text + cross-references `fix_path_helpers` entries; if all touched files map to the same layer per the Patch 2 path heuristic, single-layer flag set), helper requires a new `--single-layer-justification` flag explicitly stating: *"single-layer fix is correct because <evidence>"*. The justification text MUST cite at least one `consumer_chain` row OR `value_semantics` row that proves the symptom is layer-local.

**Verify**: re-dispatch on duplicate-options topic with primary framing = id-field mismatch (Vue-only). LLM attempts to commit Vue-only recommendation. Helper demands `--single-layer-justification`. LLM must produce evidence the symptom is layer-local — given the Phase 2.4c cross-layer trace (Patch 2) surfaces at least one `pkg-cse-core` helper as fix-path candidate, the layer-local claim has no row to cite → LLM either escalates to multi-layer recommendation OR commits to a justification that the reviewer can audit.

**Argue**: this is the strongest gate but also the most prose-heavy. Risk: LLM produces a vacuous justification (e.g., "single-layer fix is correct because the bug is in the Vue file"). Mitigation: justification text MUST cite a recorded row (helper enforces non-empty `--cites` arg referencing a row id). Without a recorded row to cite, justification fails. This raises the bar from "LLM agreed it's single-layer" to "LLM had to produce a row in its own evidence trail that supports single-layer".

### Patch 5 — Fix-path helper anchor gate (Gap 5)

**Where**: `record-fix-path-helper` setter + new verify check on the helper.

**Change**: When `record-fix-path-helper --helper-qn ... --file-line <path:line>` is called, the setter enforces that `<path:line>` collides with at least one already-recorded `record-finding --file-line` row. Collision = identical `path:line` string OR same `path` with line numbers within ±5 (lenient to absorb minor line drift between CBM hit + helper trace). If no Phase 2.3 finding anchors the fix-path helper, setter exits 2 with stderr citing the missing anchor.

Ordering enforcement: helper inspects findings recorded BEFORE the fix-path-helper call (via row timestamp or array-index gate). Findings added AFTER the fix-path call do NOT unlock the collision check retroactively. Adversarial-generator path closed.

New verify check (sequential — wherever it lands in the numbered list): each `fix_path_helpers` entry must carry a non-null `--file-line` AND that file-line must anchor to a finding recorded earlier. Reject the report otherwise.

**Verify**: dispatch /research on duplicate-options topic.
- Negative path: LLM records findings at `MenuSection.vue:206` and `QuoteLine.ts:97`, then attempts `record-fix-path-helper --helper-qn quoteBloc.addLine --file-line src/quote/quoteBloc.ts:42`. Setter rejects — `quoteBloc.ts:42` is not in any prior finding.
- Positive path: LLM records finding at `QuoteLine.ts:97` (isAttachment canonical static), then `record-fix-path-helper --helper-qn CoreQuoteLine.isAttachment --file-line src/quote/domain/entities/QuoteLine.ts:97`. Setter accepts.
- Adversarial path: LLM tries `record-finding` AFTER `record-fix-path-helper` at the same wrong file-line. Setter still rejects because the finding wasn't earlier in the state.

**Argue**: anchor rule is strict — could reject legitimate fix-paths that surface only via `trace_path mode=calls direction=inbound` (Phase 2.4c Step 2) without a prior CBM finding at that location. Mitigation: legitimate trace_path inbound walks SHOULD surface fix-path candidates that the LLM then records as a finding BEFORE record-fix-path-helper. This forces Phase 2.4c Step 2's inbound-caller enumeration to flow back into Phase 2.3 findings, tightening the evidence chain. If LLM legitimately finds a fix-path with no prior finding, the workflow is: (a) record the trace_path result as a finding, (b) THEN record-fix-path-helper. Two setter calls instead of one — small friction, big anchor guarantee. The ±5 line lenience absorbs CBM-vs-trace minor offsets.

Independent of Patches 1-4 — Patch 5 closes the target-selection blind spot constitution can't see. Constitution strengthens **wrapper-export pattern** for cross-layer fixes; Patch 5 strengthens **which code region** the fix targets. Both layers needed.

### Patch 6 — Phase 2.4d data-flow chain trace (Gap 6)

**Where**: New phase `Phase 2.4d` between `Phase 2.4c` and `Phase 2.5`. Helper additions in `_research/_state.py` (`data_flow_chain` field) + new `record-data-flow-chain` setter + verify check 15. Commit `7a82a87`.

**Change**: Five-step procedural sequence: (1) identify click handler; (2) identify write-boundary call; (3) `trace_path mode=calls` from handler to write-boundary; (4) read each first-party intermediate adapter/transformer/mapper end-to-end (filter by file-path heuristics + shape-conversion name heuristics); (5) persist via `record-data-flow-chain --handler-qn ... --write-boundary-qn ... --intermediate-qns <JSON>`. Setter validates every intermediate substring-matches an existing Finding's relevance OR surface — forces `record-finding` per intermediate BEFORE chain-record call. Verify check 15: bug mode + presentation-layer primary symptom → `data_flow_chain` must be non-null.

**Verify**: 5-18 testForge20 run surfaced `Data-flow intermediate: strataFamilycharacteristicOptionAdapter` finding row + `data_flow_chain` populated with both `itemWithQuotePrice` + `strataFamilycharacteristicOptionAdapter` intermediates. Adapter file opened, Math.random rewrite detected.

### Patch 7 — Phase 2.5 id-stability hypothesis axis (Gap 7)

**Where**: Phase 2.5 setter `set-value-semantics` extended with `--stable-across-calls true|false|unknown`. New `record-value-production-site` setter + `value_production_sites` field on report. Verify check 16. Commit `73ef728`.

**Change**: `--stable-across-calls` 4 evaluation-ordered gates — required when classification = invariant; `unknown` rejected on presentation-layer; `consumer_chain` row required to commit `false`; `false` requires at least one prior `record-value-production-site` row. New setter records `{value, file_line, is_stable}` with dedupe on `(value, file_line)` — multi-site support (same value at different lines append). Verify check 16: bug mode + any value_semantics row with `stable_across_calls=false` → at least one hypothesis cause must cite a `value_production_sites.file_line` (word-boundary regex `(?!\d)` prevents `:5` matching `:50`). Render adds Stability column + Value Production Sites section.

**Verify**: 5-18 run rendered `Value Semantics` table with `bqItemId | invariant | … | false` + `Value Production Sites` table with `bqItemId | strataFamilyToItemAdapters.ts:5 | false`. Hypothesis H2 cites `Math.floor(10000 + Math.random() * 90000)` per call as identity-stability violation — STABILITY axis competition, not KIND.

### Patch 8 — Literal-archaeology gate (Gap 8)

**Where**: New Phase 2.5b between Phase 2.5 and Phase 2.6. `record-literal-archaeology` setter with 6-value `--intent` enum (`placeholder | migrated | deliberate | forgotten | inherited-refactor | generated`). Verify check 17 + render section. Commit `ef3cff2`.

**Change**: `record-literal-archaeology` requires 6 args (literal, file_line, intent, git log -S evidence, git blame author/date, git show context). Verify check 17: bug-mode + recommended approach rationale (or linked approach description) contains literal-replacement prose (`"replace X with Y"` / `"X -> Y"`) → at least one `literal_archaeology` row for X at a finding's file_line. Spec adds `git log -S <literal>` + `git show` + `git blame` steps + per-intent recovery rules + shallow-clone fallback.

**Verify**: 5-18 run classified `Math.random(...)` literal as `placeholder` intent + cited git blame surface. Recommended approach "replace with partNo fallback" anchored to placeholder classification rather than treated as deliberate business value.

### Patch 9 — Argument-duplication shape check (Gap 9)

**Where**: `set-recommended-approach` gains `--proposed-call-shape` arg. Helper additions: `CALL_SHAPE_RE` / `IDENT_CHAIN_RE` + `_split_top_level_args` + `_detect_arg_duplication` (paren/bracket/brace-depth aware). Verify check 18 mirrors duplication check. Render surfaces shape as fenced code block. Commit `fcc860b`.

**Change**: `--proposed-call-shape` REQUIRED in bug mode when `--single-layer-justification` is set OR when rationale (or linked approach description) contains literal-replacement prose (reuses Patch 8 `_detect_literal_replacement`). Setter rejects when the literalized call passes the same identifier (bare / dotted / optional-chained) more than once; fail-soft on parser failure (stores shape verbatim + advisory stderr). Verify check 18 mirrors at verify time. Rationale: argument duplication signals fix layer belongs upstream (wrapper signature / state initialization / use-case default) rather than at the call site.

**Verify**: 5-18 run committed proposed call-shape for `quoteBloc.addLine(item, options.lineConfigId)` — no duplication, no rejection. Gate didn't fire (correctly) on this topic but cross-validated against 28 new tests.

## Out of scope (this plan)

- **Re-run testForge20 /research on the duplicate-options topic AFTER patches** — that's the empirical verification step, runs once patches land.
- **Backport patches to consumer projects already running /research** — emit changes propagate via `update.sh` re-emit of promoted commands; no separate backport plan needed.
- **Phase 0 / Phase 4 changes** — preflight gate + save flow are correctness-orthogonal to the framing-regression class.
- **/specify, /plan downstream-redundant gates** — patches here close the gap at the workflow entrypoint; downstream commands inherit the corrected framing. If the regression class re-appears at /specify or /plan, separate plans.
- **Adversarial LLM-generator instinct guard** (re: `project_adversarial_generator_instinct` + `project_bulk_repair_script_instinct`) — orthogonal failure class; not in scope.
- **Prior-art input source** — explicitly rejected (see boxed note under `## Patches`). /research stays Fresh-every-run; framing convergence comes from Patches 1 + 2, not from reading past LLM outputs.

## Cross-references

- Strengthened constitution §3.6 DI rule (this session's other plan, `CONSTITUTION-STRENGTHENING-PLAN.md`) targets the same failure class downstream (in spec / plan / code). This plan targets it upstream (in research). Pair complementary.
- `feedback_cbm_discovery_chain_search_graph_then_code` — falls through to `search_code` when `search_graph` returns 0 hits. Related to Gap 1 but orthogonal — that feedback addresses CBM tool-choice for a single query; this plan addresses framing-level competition across multiple queries.
- `feedback_basic_path_plus_user_fallback` — default-skip edge-case findings unless basic path actively misleads. Important calibration: patches above raise structural gates at the entry of the workflow; they should NOT propagate down as edge-case findings in /specify, /plan, /breakdown.

## Resume-in-fresh-session prompt

Paste the following into a fresh Claude Code session at `~/Projects/ai-dev-team-forge`:

```
Resume RESEARCH-FRAMING-REGRESSION-PLAN.md at repo root. Read the plan top-to-bottom — context, diagnosis (Gaps 1-5), 5 patches (an earlier prior-art-input draft was rejected — see boxed note under `## Patches`; Patch 5 is fix-path anchor gate, added 2026-05-17 to close target-selection blind spot constitution can't see). Implementation order: Patch 1 → Patch 2 → Patch 3 → Patch 4 → Patch 5, each in its own commit on develop-2.0-init. Per-patch flow: (a) draft helper setter changes + verify checks via python-engineer agent with test-first discipline; (b) draft Phase-N spec edits via instruction-author; (c) review via python-reviewer + instruction-reviewer; (d) re-loop until clean; (e) commit. Verify per patch against the verify criteria in the plan. After all 5 patches: re-dispatch /research on testForge20 against the duplicate-options topic, diff against `testForge20/tmp/2026-05-16-restriction-on-adding-the.md` (the old run that caught it), confirm fresh run now reaches structural diagnosis.
```

## When resuming work

1. Read this plan top-to-bottom.
2. Verify both research artefacts still exist at the cited paths:
   ```bash
   ls -la /Users/mykolakudlyk/Projects/testForge20/tmp/2026-05-16-restriction-on-adding-the.md \
          /Users/mykolakudlyk/Projects/testForge20/research/2026-05-16-restriction-on-adding-same.md
   ```
3. Verify `/research` command spec + helper are at the cited line ranges (drift possible if other work landed):
   ```bash
   grep -n "Phase 2.4c — Helper-API surface enumeration" /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/commands/research/main.md
   grep -n "Phase 2.5 — Hypothesis enumeration" /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/commands/research/main.md
   wc -l /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/commands/research/main.md
   ```
4. Apply patches in order. Each patch = one commit. Do not bundle.
5. ~~After Patch 5 lands, run the empirical verify~~ — DONE 2026-05-18 (after Patches 6-9 added). Fresh testForge20 /research at `testForge20/research/2026-05-18-restriction-on-adding-the.md` (24.9K) caught 3.5/3 real-ship causes vs commits `74adb5b17` + `df231933a`. Framing parity + target parity + adapter-trace + STABILITY-axis hypothesis all passed.
6. Update this plan's Status: **Patches applied + empirically verified** OR list which patches landed and which deferred.

## Notes for engineer / reviewer

- Helper changes are test-first. Every new setter + every new verify check has a test in `tests/lib/test_research_helper.py` written + run in the same turn (per `feedback_test_first_python_helpers`).
- Spec edits go through `instruction-author` + `instruction-reviewer` per `feedback_dual_agent_verify_command_statements`.
- Cross-check after every patch: grep for any other spec / command / helper that references the changed Phase numbers, setter names, or verify check numbers (per `feedback_cross_check_after_every_change`). The `claude-code-guide` agent verifies external Claude-Code authoring conventions for any /research spec changes that touch slash-command surface (frontmatter, AskUserQuestion shape, etc.) per `feedback_claude_code_authoring_best_practices`.
