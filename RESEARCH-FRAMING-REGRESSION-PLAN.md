# RESEARCH-FRAMING-REGRESSION-PLAN

**Status**: Patches 1 + 2 applied + tests green (160/160 in `tests/lib/test_research_helper.py`); Patches 3/4 pending. F2 closed by Patch 2 (layer-boundary stopping rule + check 8b cross-layer gate + `record-fix-path-helper --file-line`).
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

## Diagnosis — four structural gaps in /research that allowed the regression

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

## Patches

Four patches, in dependency order. Each leaves /research in a buildable, verifiable state. Apply sequentially.

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
Resume RESEARCH-FRAMING-REGRESSION-PLAN.md at repo root. Read the plan top-to-bottom — context, diagnosis, 4 patches (an earlier 5th patch on prior-art input was rejected — see boxed note under `## Patches`). Implementation order: Patch 1 → Patch 2 → Patch 3 → Patch 4, each in its own commit on develop-2.0-init. Per-patch flow: (a) draft helper setter changes + verify checks via python-engineer agent with test-first discipline; (b) draft Phase-N spec edits via instruction-author; (c) review via python-reviewer + instruction-reviewer; (d) re-loop until clean; (e) commit. Verify per patch against the verify criteria in the plan. After all 4 patches: re-dispatch /research on testForge20 against the duplicate-options topic, diff against `testForge20/tmp/2026-05-16-restriction-on-adding-the.md` (the old run that caught it), confirm fresh run now reaches structural diagnosis.
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
5. After Patch 4 lands, run the empirical verify: fresh testForge20 /research on the duplicate-options topic. Diff against `testForge20/tmp/2026-05-16-restriction-on-adding-the.md` to confirm framing parity.
6. Update this plan's Status: **Patches applied + empirically verified** OR list which patches landed and which deferred.

## Notes for engineer / reviewer

- Helper changes are test-first. Every new setter + every new verify check has a test in `tests/lib/test_research_helper.py` written + run in the same turn (per `feedback_test_first_python_helpers`).
- Spec edits go through `instruction-author` + `instruction-reviewer` per `feedback_dual_agent_verify_command_statements`.
- Cross-check after every patch: grep for any other spec / command / helper that references the changed Phase numbers, setter names, or verify check numbers (per `feedback_cross_check_after_every_change`). The `claude-code-guide` agent verifies external Claude-Code authoring conventions for any /research spec changes that touch slash-command surface (frontmatter, AskUserQuestion shape, etc.) per `feedback_claude_code_authoring_best_practices`.
