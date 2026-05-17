# RESEARCH-FRAMING-REGRESSION-PLAN-V2

**Status**: Draft 2026-05-17, hardened 2026-05-18 against 6 pre-commit concerns (C1 token cost / C2 write-boundary token list / C3 handler-detection fragility / C4 cyclic dep / C5 multi-production-site / C6 trace_path data_flow accuracy). Addresses 2 unaddressed gaps (Gap 6 + Gap 7) surfaced after RESEARCH-FRAMING-REGRESSION-PLAN Patches 1-5 shipped + scored 1.5 of 3 on empirical verify (BELOW pre-patch 04-30 baseline of 2 of 3). Not yet implemented.
**Branch**: `develop-2.0-init`
**File targets**: `src/commands/research/main.md` + `src/devforge/lib/research_helper.py` + `tests/lib/test_research_helper.py`
**Predecessor plan**: `RESEARCH-FRAMING-REGRESSION-PLAN.md` (Patches 1-5 shipped, status field reflects empirical failure). DO NOT roll Patches 1-5 back — they're necessary-not-sufficient.

## Context for next session

Patches 1-5 in the predecessor plan were structural gates (framing competition / layer-boundary stopping rule / scope evidence / single-layer recommendation / fix-path anchor). They forced the LLM to produce structurally-cleaner state. They did NOT close the actual observed failure mode on the testForge20 duplicate-options topic, because the actual failure mode wasn't about framing or layer-stack — it was about NOT READING THE ADAPTER FILE.

**Empirical artefacts (verify these still exist before resuming):**

- Old caught run (the model run we WANT to match): `/Users/mykolakudlyk/Projects/testForge20/tmp/2026-05-16-restriction-on-adding-the.md` (22.4K)
- Older still-caught run (different baseline, also got 2 of 3): `/Users/mykolakudlyk/Projects/testForge20/research/2026-04-30-...md`
- Fresh post-Patch-1-5 run (scored 1.5/3): `/Users/mykolakudlyk/Projects/testForge20/research/2026-05-17-restriction-on-adding-the.md`
- Actual fix in `~/Projects/doosan/cse-strata-ws-forge/db-cse-ui-strata` on branch `bugfix/MIG-2642`, commits `74adb5b17` + `df231933a` (added partNo fallback param)
- Smoking-gun adapter file: `apps/app-web/src/helpers/strataFamilyToItemAdapters.ts:5` — `const uniqueId = Math.floor(10000 + Math.random() * 90000);`
- Symbol reference site (visible-on-screen-but-unfollowed): `apps/app-web/src/components/configuration/components/configurationMenu/components/MenuItemInfo.vue:193`

**Lesson encoded** (saved as `project_research_patches_1_5_empirical_failed.md` in memory): regression plans must replay-the-failure, not just constrain output shape. Patches 1-5 were designed against the 05-16 fresh-run's *symptoms* (wrong framing); they didn't test against the 04-30 caught-run's *success criteria* (catching the adapter). V2 closes that loop.

## Diagnosis — two unaddressed gaps

### Gap 6 — Symbol-on-screen-but-unfollowed (adapters / transformers / mappers never read end-to-end)

Phase 2.3 / 2.4 / 2.4b / 2.4c surface CBM hits + helper-API surfaces. The LLM treats any function with a name suggesting shape-conversion (`adapter`, `mapper`, `transformer`, `normalizer`, `converter`, `serializer`) as identity-preserving on the values it passes through — because the name advertises shape conversion, not value mutation.

Empirical observation 2026-05-17: `strataFamilycharacteristicOptionAdapter` was visible at `MenuItemInfo.vue:193` (the symptom-area file), indexed by CBM as a code node, named in CBM search results — and never opened end-to-end. The function rewrites `bqItemId` / `id` / `baseInfo.id` to `Math.floor(10000 + Math.random() * 90000)` on every call. Any id-based comparator downstream of this adapter fails for Strata items by design. The 04-30 run caught it; the 05-16 + 05-17 runs missed it.

Effect: the LLM stops at the comparator (the SYMPTOM site) and never traces FORWARD to the production site of the value being compared. Identifier kind questions (`id` vs `bqItemId` vs `partNo`) get asked; identifier ORIGIN questions (where is this value assigned? does the assignment preserve it across calls?) don't.

Distinction from Gap 5: Gap 5 anchors fix-path helpers to findings (helper can't invent a target). Gap 6 anchors findings themselves to the data-flow chain between user-action and write-boundary (findings can't skip intermediate transformers).

### Gap 7 — Id-stability hypothesis axis missing from Phase 2.5

Phase 2.5 hypothesis enumeration biases toward identifier KIND (`id` vs `bqItemId` vs `partNo`) because the helper's value-semantics classifier maps onto kind-of-value (preference / invariant / unclassified). It does NOT have a stability axis — the LLM cannot record "this identifier is `invariant` BUT its value is randomized at production". Any id-comparator hypothesis framed in terms of identifier kind misses a production-site rewriter because the rewriter doesn't change the kind, just the stability.

Empirical observation 2026-05-17: the runner-up frame the 05-17 run committed to was "id vs bqItemId mismatch" (kind axis). The actual cause was "id is randomized per-call by adapter" (stability axis). Both runs that missed the bug stayed on the kind axis.

Effect: invariant classification = TRUE but stable-across-calls = FALSE is a valid state in the real world, and the helper has no shape to record it. Phase 2.5 generates hypotheses against the (wrong) implicit assumption that an invariant value is stable across the operation chain.

## Patches

Two patches, in dependency order. Each leaves /research in a buildable, verifiable state. Apply sequentially.

### Patch 6 — Phase 2.4d data-flow chain trace (Gap 6)

**Where**: New phase `Phase 2.4d — Click-handler-to-write-boundary trace` between Phase 2.4c (helper-API surface) and Phase 2.5 (hypothesis enumeration). New helper setters + new verify check 15.

**Change**:

1. **Phase 2.4d spec section** mandates the following sequence for bug-mode reports where the symptom is in a presentation-layer file:
   - Identify the user-action handler: the function on the presentation-layer file that fires on the user's repro action (click handler, form submit, input change). Source: `repro_or_current` dimension prose + `affected_area` file path. Run `search_code` for event-binding tokens (`@click=`, `onClick=`, `addEventListener`, `v-on:`, `onPress`, `onPanResponderMove`, `hx-on::`, `dispatchEvent`, `useClickHandler`, `useEventListener`) in the symptom file to locate. **Heuristic-fragility fallback** (concern C3 per `feedback_basic_path_plus_user_fallback`): if no handler token is found via the search_code sweep (dynamic event binding with variable event type, composable-wrapped binding, framework-specific syntax not in the token list, programmatic dispatch), the LLM MUST ask the user one direct prompt: *"I couldn't auto-detect the click/event handler that triggers the bug from the symptom file. Which function or method handles the user action that reproduces the bug? (give a function name or `file:line`)"* — wait for the user answer, then proceed. Do NOT guess. Do NOT skip Phase 2.4d on heuristic miss — the user-fallback is the gate-recovery path.
   - Identify the write-boundary call: the function the handler eventually calls that PERSISTS the operation. **Default write-boundary token list** (concern C2 — list deliberately broad to cover REST + Redux + repository + WebSocket + GraphQL + IndexedDB + Server-Sent Events + message-bus + Apollo cache + Pinia / state-management actions): `addLine|dispatch|commit|mutate|mutation|repo.save|*.put|*.post|*.create|*.update|*.emit|*.send|*.publish|cache.writeQuery|cache.writeFragment|store.put|tx.add|tx.put|.dispatchEvent|eventBus.emit|bus.publish`. **Project-portable override** via `.devforge/configure.yaml` key `write_boundary_tokens: [...]` — projects with non-conventional write-boundary verbs (e.g., `tellSaga`, `enqueueWork`, `requestSync`) override the default list. When override is set, the helper uses the override INSTEAD of the default (not in addition); the LLM consults `.devforge/configure.yaml` before running the `search_code` token sweep. Source: `search_code` for write-boundary tokens in the symptom file (use the effective token list — override if set, default otherwise).
   - Run `trace_path` from the handler QN to the write-boundary QN with `mode=data_flow direction=outbound`. Record the full path of intermediate function QNs. **CBM mode-accuracy fallback** (concern C6): per `project_cbm_empirical_state_2026_05_09`, CBM has Section-level indexing granularity + the empirical depth of `mode=data_flow` analysis is unverified. If `trace_path mode=data_flow direction=outbound` returns an EMPTY intermediates list (CBM doesn't model the data-flow edges through this code) OR returns a list that obviously misses framework-bridging hops (e.g., handler → write-boundary directly with no intermediates, when the file source clearly shows a transformer in between), **fall back to `mode=calls direction=outbound`** for the same handler→write-boundary pair. Record the call-graph path AND explicitly note in the `data_flow_chain` record (via new field `trace_mode: "data_flow" | "calls"`) which mode was used; downstream LLM steps must read each intermediate body via `get_code_snippet` to confirm the value of interest actually passes through (call-graph reachability ≠ data-flow reachability). The shape-conversion-name filter (concern C1) still applies. Pre-flight verification BEFORE shipping Patch 6: add a test to `tests/lib/test_research_helper.py` that dispatches a real `trace_path mode=data_flow` against a known-shape fixture (e.g., a 3-function chain in the test fixtures dir) + asserts intermediates appear. If empty → switch the spec default to `mode=calls` + remove the fallback (just always use calls).
   - For EACH intermediate function on the path (NOT including the handler + write-boundary themselves), call `get_code_snippet` to READ THE BODY end-to-end. **Two filters apply** (cumulative — both must pass for a function to require end-to-end read):
     - **First-party filter** (already specified in Argue below): skip functions whose source file is in framework / vendor / SDK packages; read only first-party project workspace files.
     - **Shape-conversion-name filter** (token-cost mitigation per concern C1): preferentially read functions whose name matches a shape-conversion pattern — case-insensitive substring match against `adapter|mapper|transformer|normalizer|converter|serializer|deserializer|encoder|decoder|wrapper|builder|formatter|parser`. These names advertise shape-conversion but commonly hide value-mutation (random-id assignment, type coercion, field rename). Pure-passthrough functions (handlers / dispatchers / forwarders whose names do NOT match the pattern) MAY be skipped at LLM discretion if the file body is large. The shape-conversion-name filter is a HINT, not a hard gate: when in doubt, read.
     - Look for value-mutation patterns: `Math.random`, `crypto.random`, `Date.now`, `uuid()`, manual id reassignment (`item.id = ...`, `obj[...] = ...`), structuredClone/destructuring that loses fields, type-coercion that drops precision.
   - Record EACH intermediate function as a `Finding` row via `record-finding --surface "data-flow intermediate: <function role>" --file-line "<path:line>" --relevance "<one-line role note>"`. This integrates with the Patch 5 anchor gate (Phase 2.4c's fix-path-helpers automatically anchor to these new findings without separate enforcement).
   - Persist the chain via new setter: `record-data-flow-chain --handler-qn ... --write-boundary-qn ... --intermediate-qns '["A","B","C"]'`.

2. **New helper setters**:
   - `record-data-flow-chain --handler-qn <qn> --write-boundary-qn <qn> --intermediate-qns '[<qn>, ...]' --trace-mode <data_flow|calls>` — persists the chain. Required when bug-mode + presentation-layer symptom. `--trace-mode` records WHICH `trace_path` mode produced the intermediates list (concern C6) — downstream verify/render branches show whether the chain was data-flow-confirmed or call-graph-only.
   - Helper validates: handler_qn + write-boundary_qn non-empty; intermediate_qns is JSON array (may be empty if direct call); each intermediate QN must have a corresponding Finding row (forces the `record-finding` pre-call per spec); `--trace-mode` is one of the two enum values.

3. **New verify check 15** (gated on bug mode + presentation-layer symptom): `data_flow_chain` must be set; every `intermediate_qns[i]` must have a Finding row whose `file_line` matches the function's definition file (use `_has_anchor_finding` from Patch 5 with ±5 line tolerance against `get_code_snippet`-derived file_line).

4. **Helper data structure** (added to `default_report_state()`):
   ```python
   "data_flow_chain": None,  # {handler_qn, write_boundary_qn, intermediate_qns}
   ```

**Verify**: re-dispatch /research on testForge20 duplicate-options topic. Phase 2.4d traces from `MenuItemInfo.handleButtonClick` (click handler) → `strataFamilycharacteristicOptionAdapter` (intermediate transformer — MUST be recorded as Finding) → `quoteBloc.addLine` (write boundary). The intermediate-recording step forces the LLM to read `strataFamilyToItemAdapters.ts` end-to-end + spot the `Math.random()` id assignment. Hypothesis enumeration in Phase 2.5 then has the random-id signal in evidence.

**Argue**: trace_path may return long chains for complex UIs (10+ intermediate functions for a click that goes through Vue event bus → Pinia store → composable → BLoC → BLoC handler → repository); reading each end-to-end could cost 5K-10K tokens per intermediate × N intermediates. Mitigation: limit intermediate-read to functions whose source file is in the SAME project workspace (skip framework / vendor / SDK packages — same heuristic as Patch 2's layer-boundary stopping rule but applied to file ownership). Skip framework files (Vue runtime, Pinia store internals, BLoC infrastructure); read only first-party transformers + adapters. This filter still catches the Strata-adapter pattern (it's first-party in `apps/app-web/src/helpers/`).

Counter-risk: trace_path may MISS adapters that the LLM passes a value to inline without calling a named function (`addLine({...adapter(item), extraField: foo})`). Mitigation: when the write-boundary call argument list contains a function call expression (not just identifier passthrough), the call expression's callee MUST also be added to intermediate_qns. Forces inline-call detection.

### Patch 7 — Phase 2.5 id-stability hypothesis axis (Gap 7)

**Where**: `set-value-semantics` setter — new required field when classification=invariant. Phase 2.5 spec extension.

**Change**:

1. **`set-value-semantics --stable-across-calls true|false|unknown`** — new arg. REQUIRED when `--classification invariant`. Optional otherwise.

2. **Helper validation**:
   - When `--classification invariant` + `--stable-across-calls unknown`: rejection **gated on symptom layer** (concern C4 — cyclic dependency mitigation): rejection fires ONLY when the primary symptom is presentation-layer (per `_is_presentation_layer` from Patch 2), because that's the case where Phase 2.4d data-flow chain ran and surfaced an investigatable production site. For domain-layer symptoms (where Phase 2.4d doesn't fire), `--stable-across-calls unknown` is ACCEPTED — the LLM has no auto-trace path to investigate the production site and the user-fallback is the recovery. Helper stderr on presentation-layer rejection: `set-value-semantics: --stable-across-calls cannot be 'unknown' when --classification is 'invariant' AND symptom is presentation-layer; investigate the production site (where the value is assigned) via Phase 2.4d data-flow chain (already recorded) before classifying`.
   - When `--classification invariant` + `--stable-across-calls false`: helper REQUIRES a new setter `record-value-production-site` call before/after `set-value-semantics` recording the file:line where the value is assigned/computed. This is the rewriter site (`Math.random`, `Date.now`, etc.).

3. **New setter `record-value-production-site --value <symbol> --file-line <path:line> --is-stable <true|false>`** — captures where the value is produced. **Append-only with distinct file_line dedupe** (concern C5 — multi-production-site support): a single `--value` may have MULTIPLE production-site rows recorded (e.g., 3 adapters each rewriting the same id field with the caller picking dynamically). Each `record-value-production-site` call appends a new row IFF its `--file-line` is distinct from all prior rows for the same `--value`; same `--file-line` is a no-op dedupe. Helper validates non-empty `--value` + valid `--file-line` (rejects `(none)` sentinel — production site must be a real path). `--is-stable false` on ANY of the rows flags the production-site cluster as a candidate root cause; render aggregates by `--value` showing all N production sites. Stored as `value_production_sites: [{value, file_line, is_stable}, ...]` on report state.

4. **Phase 2.5 spec extension**: when any `value_semantics` row has `stable_across_calls=false`, Phase 2.5 hypothesis enumeration MUST include at least one hypothesis citing the production-site rewriter as the root cause. Helper enforces via new check 16 (bug mode + any invariant-unstable row → at least one hypothesis text contains the production-site file:line).

5. **Render**: extend the Value Semantics section in the rendered report to show `stability` column alongside classification.

**Verify**: re-dispatch /research on testForge20 duplicate-options topic.
- Negative path: LLM attempts `set-value-semantics --value bqItemId --classification invariant` without `--stable-across-calls`. Helper rejects (arg required).
- Negative path: LLM passes `--stable-across-calls unknown`. Helper rejects (must investigate production site first; cite Phase 2.4d).
- Positive path: LLM reads Phase 2.4d's intermediate-trace of `strataFamilycharacteristicOptionAdapter`, sees `Math.random` assignment, calls `record-value-production-site --value bqItemId --file-line src/helpers/strataFamilyToItemAdapters.ts:5 --is-stable false`, then `set-value-semantics --value bqItemId --classification invariant --stable-across-calls false`. Check 16 passes because Phase 2.5 hypothesis enumeration now includes "production-site rewriter at strataFamilyToItemAdapters.ts:5" as a candidate.

**Argue**: `stable-across-calls=unknown` rejection adds friction for legitimately-unknown cases where the LLM hasn't yet investigated the production site. That's the point — Patch 7 forces the investigation BEFORE the invariant classification is committed. The Phase 2.4d data-flow chain (Patch 6) provides the structural path to investigate; Patch 7 enforces the investigation happens. Without Patch 6, Patch 7's `unknown` rejection has no clear recovery path; with Patch 6, the recovery is mechanical (read the intermediate chain → spot rewriters → record production site → re-classify).

Edge case: when no production-site exists in the report state (because Phase 2.4d's intermediate chain showed all functions are identity-preserving), the LLM should classify `--stable-across-calls true`. The check 16 hypothesis-citation requirement only fires when at least one `stable_across_calls=false` row exists.

## Out of scope (this plan)

- **Rolling back Patches 1-5** — they're structural improvements that stand on their own. V2 stacks on top.
- **Replay-the-failure infrastructure** — the lesson "regression plans must replay the original failure" is recorded in memory (`project_research_patches_1_5_empirical_failed.md`) but is workflow discipline, not a code patch.
- **Auto-detection of "user-action handler"** — heuristic-only via spec prose + `search_code` for event-binding tokens. If the heuristic fails, the LLM falls back to user-input fallback (asks the user).
- **Auto-detection of "write-boundary call"** — same heuristic strategy. Mitigation for misses = explicit user fallback.
- **Patches against /specify, /plan downstream** — V2 closes gaps at /research; if the regression class re-appears downstream, separate plans.
- **Re-running empirical verify on testForge20 AFTER V2** — that's the verification step, runs once V2 patches land. Required to confirm V2 actually closes the gaps before declaring victory.

## Cross-references

- `RESEARCH-FRAMING-REGRESSION-PLAN.md` (predecessor — Patches 1-5 shipped, status field reflects empirical failure)
- `project_research_patches_1_5_empirical_failed.md` (memory — failure mode + lesson)
- `feedback_helper_owns_contract_filesystem_forcing` (spec prose can't enforce loop bounds; only mandatory gates that walk filesystem are reliable forcing functions — V2 patches use helper setter gates not prose)
- `feedback_cbm_discovery_chain_search_graph_then_code` (CBM-first discovery; V2 Phase 2.4d builds on this)
- `feedback_test_first_python_helpers` (every new helper function + every new check has a test in same turn)
- `feedback_dual_agent_verify_command_statements` (spec edits go through instruction-author + instruction-reviewer)
- `feedback_iterative_review_loop_preferred` (apply-verify loop; engineer → reviewer → loop until clean)
- Constitution `§3.6 DI` (cross-layer fix pattern — V2's Patch 6 + 7 don't change §3.6's scope)

## Resume-in-fresh-session prompt

Paste the following into a fresh Claude Code session at `~/Projects/ai-dev-team-forge` (run `/clear` first if continuing in the same shell):

```
Resume RESEARCH-FRAMING-REGRESSION-PLAN-V2.md at repo root. Read the plan top-to-bottom — Context, Diagnosis (Gaps 6 + 7), Patches 6 + 7, Out of scope, Cross-references, When-resuming-work. Read the predecessor plan RESEARCH-FRAMING-REGRESSION-PLAN.md's Status field for the empirical-failure context that motivated V2.

Implementation order: PRE-FLIGHT (CBM trace_path mode=data_flow accuracy check — concern C6) → Patch 6 (Phase 2.4d data-flow chain trace) → Patch 7 (Phase 2.5 id-stability axis). Each implementation patch in its own commit on develop-2.0-init.

Pre-flight: write a focused test that dispatches mcp__codebase-memory-mcp__trace_path with mode=data_flow direction=outbound against a known 3-function chain in the existing test fixtures (or set one up if none exists). Confirm intermediates appear. If empty → switch Patch 6 spec from "mode=data_flow with fallback to mode=calls" to "always mode=calls" + simplify the helper (no --trace-mode arg needed). Document the empirical finding in the plan Status field before continuing to Patch 6.

Per-patch flow:
  (a) Draft helper setter changes + verify checks via python-engineer agent with test-first discipline (per feedback_test_first_python_helpers — every new function gets a test written + run in the same turn; tests via /Users/mykolakudlyk/Projects/ai-dev-team-forge/.venv-test/bin/pytest tests/lib/test_research_helper.py).
  (b) Run python-reviewer on the helper additions (per feedback_dual_agent_verify_command_statements).
  (c) Apply reviewer findings; re-loop until clean.
  (d) Draft Phase-N spec edits in src/commands/research/main.md directly (orchestrator-owned; instruction-reviewer dispatched on output).
  (e) Run instruction-reviewer on the spec edits (per feedback_dual_agent_verify_command_statements + feedback_intra_file_only_consistency_check).
  (f) Apply reviewer findings; re-loop until clean.
  (g) Cross-check: grep for affected identifiers / paths / check numbers across the file (per feedback_cross_check_after_every_change).
  (h) Update RESEARCH-FRAMING-REGRESSION-PLAN-V2.md Status field.
  (i) Commit (stage only the patched files — research_helper.py + research/main.md + test_research_helper.py + fixtures + this plan).

After Patch 7 lands: run update.sh --force on testForge20 to propagate, then re-dispatch /research on the duplicate-options topic. Diff against testForge20/tmp/2026-05-16-restriction-on-adding-the.md. CRITICAL — the empirical-verify acceptance criterion this time is NOT "framing parity" but "did the new run identify the strataFamilyToItemAdapters.ts:5 random-id assignment as a root cause?". If yes, V2 closes the gaps. If no, V2's structural gates were also insufficient — surface a new gap and draft V3.

DO NOT roll back Patches 1-5. They're structural improvements that stand on their own. V2 stacks on top.

DO NOT skip the empirical-verify-replay step. The lesson from V1 is that structural gates pass tests but can still miss the original failure mode. V2 must replay the testForge20 duplicate-options topic + check the adapter-detection acceptance criterion explicitly before declaring victory.
```

## When resuming work

1. Read this plan top-to-bottom + the predecessor plan's Status field.

2. Verify empirical artefacts still exist (paths may have changed since 2026-05-17):
   ```bash
   ls -la /Users/mykolakudlyk/Projects/testForge20/tmp/2026-05-16-restriction-on-adding-the.md \
          /Users/mykolakudlyk/Projects/testForge20/research/2026-05-17-restriction-on-adding-the.md \
          ~/Projects/doosan/cse-strata-ws-forge/db-cse-ui-strata/apps/app-web/src/helpers/strataFamilyToItemAdapters.ts
   ```

3. Verify Patches 1-5 still landed (drift possible):
   ```bash
   git -C /Users/mykolakudlyk/Projects/ai-dev-team-forge log --oneline develop-2.0-init -10 | grep -E "Patch [1-5]"
   ```
   Expected: 5 commits — 832aa4e (Patch 1), b8e6098 (Patch 2), c8a9ca3 (Patch 3), 5eaa704 (Patch 4), 4a6a519 (Patch 5).

4. Verify research_helper.py + research/main.md are at expected shape:
   ```bash
   grep -nE "_compute_check_8b_would_fire|_has_anchor_finding|_make_scope_setter|helper_rejection_log" /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/devforge/lib/research_helper.py | head -5
   grep -nE "Phase 2.3b|Phase 2.4c|Anchor gate|single-layer-justification" /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/commands/research/main.md | head -5
   ```

5. Confirm test baseline:
   ```bash
   /Users/mykolakudlyk/Projects/ai-dev-team-forge/.venv-test/bin/pytest tests/lib/test_research_helper.py 2>&1 | tail -3
   ```
   Expected: 231 passed.

6. Run pre-flight CBM `trace_path mode=data_flow` accuracy check (concern C6). Update plan Status field with the empirical finding (data_flow works → keep dual-mode; data_flow returns empty → switch to mode=calls always + simplify the helper). Then apply Patch 6, then Patch 7. Each = one commit. Do not bundle.

   **Cost-surface note** (concern C1): before kicking off the testForge20 empirical verify in step 7, surface estimated added token cost to the user. Strata case has ~5-8 first-party intermediates; ~5K tokens/end-to-end read × 8 = ~40K added tokens per /research run on a Strata-shaped bug. Cost may be lower or higher on other projects depending on first-party transformer count. Per `feedback_per_concern_cost_ceiling`.

7. After Patch 7 lands + tests green:
   a. Run `~/Projects/ai-dev-team-forge/update.sh --force /Users/mykolakudlyk/Projects/testForge20`.
   b. Open a fresh Claude Code session in `/Users/mykolakudlyk/Projects/testForge20`.
   c. Run `/research "<duplicate-options topic phrasing>"` (the same topic from 2026-05-16/17 runs).
   d. Diff output against `tmp/2026-05-16-restriction-on-adding-the.md` for framing parity AND check specifically: does the new run identify `strataFamilyToItemAdapters.ts:5` `Math.random` assignment as a root cause? Both must be true.

8. Update this plan's Status: **V2 applied + empirically verified (3/3 causes)** OR **V2 applied + empirical verify still failing — draft V3 against the new gap**.

## Notes for engineer / reviewer

- Helper changes are test-first per `feedback_test_first_python_helpers`. Every new setter + every new verify check has a test in `tests/lib/test_research_helper.py` written + run in the same turn. Tests via `/Users/mykolakudlyk/Projects/ai-dev-team-forge/.venv-test/bin/pytest tests/lib/test_research_helper.py` (system python3 lacks pytest; use venv binary).

- Helper-owns-shape pattern per `feedback_helper_owns_shape_principle`: `data_flow_chain` is `{handler_qn, write_boundary_qn, intermediate_qns}` dict (helper owns structure; LLM passes args).

- Spec edits via instruction-author or direct orchestrator edit; instruction-reviewer dispatched for verification per `feedback_dual_agent_verify_command_statements`. Scope = intra-file only per `feedback_intra_file_only_consistency_check`; orchestrator carries cross-file precedents.

- Cross-check after every patch: grep for affected identifiers / paths / section numbers / check numbers per `feedback_cross_check_after_every_change`. Specifically watch for verify-checks paragraph at the END of Phase 3 in main.md — needs check 15 + check 16 added when those patches land.

- Patches 1-5 changed the schema enough that round-trip fixtures (`tests/lib/fixtures/research-sample-*.md`) needed regeneration. V2 may also change fixture output — regenerate via the one-liner in the predecessor plan's commit messages.

- The `_PRESENTATION_EXTENSIONS` / `_PRESENTATION_PATH_FRAGMENTS` constants from Patch 2 are the source of truth for "is this a presentation-layer symptom?". V2's Phase 2.4d gating should reuse `_is_presentation_layer` (no duplicate heuristics).

- Patch 6 introduces a new `intermediate_qns` array; the Patch 5 anchor gate already enforces fix_path_helpers→findings collision. V2 should make `intermediate_qns` enforcement work the same way (each intermediate QN gets a Finding row; verify check enforces it). Reuse `_has_anchor_finding` for collision detection.

- Patch 7's `record-value-production-site` setter should follow the helper-rejection-log pattern from Patch 5 if you need anti-adversarial sticky-reject (probably not needed — production-site is a one-shot record, not a retry-loop).
