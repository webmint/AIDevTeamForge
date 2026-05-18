# RESEARCH-FRAMING-REGRESSION-PLAN-V3

**Status**: Patches 8 + 9 LANDED 2026-05-18 on `develop-2.0-init` (helper + tests + spec; 320 passed via venv-test). Empirical verify-replay on testForge20 splitOnSNA topic pending. Hardened 2026-05-18 against 4 pre-commit refinements: (R1) enum locked at 6 values including `generated`; (R2) literal-token regex expanded to cover Python `True|False|None`, hex `0xff`, BigInt `100n`, scientific `1e-9`, backtick templates `` ` `` (non-interpolated); array/object literals documented out-of-scope; (R3) Patch 9 identifier regex updated for optional chaining `a?.b?.c`; (R4) oldest-introducing-commit anchor edge case (deliberate-then-stale) acknowledged + deferred to /audit. Predecessor V2 plan empirically verified 3/3 on Strata duplicate-options bug 2026-05-18. V3 closes 2 unaddressed gaps surfaced on the 2026-05-18 splitOnSNA bug run, where /research recommended a call-site fix that produced argument duplication (`fetchOrder(false)` → `fetchOrder(isExternalUser.value)` while `isExternalUser.value` was already arg 2 in the same call); user required 3 dialogue turns to escalate to S3 (wrapper default-param), and LLM never opened git blame on the hardcoded `false` to surface its historical intent. Patches 6+7 forced WHERE-evidence + STABILITY-evidence; V3 forces HISTORICAL-evidence + FIX-SHAPE-evidence.
**Branch**: `develop-2.0-init`
**File targets**: `src/commands/research/main.md` + `src/devforge/lib/research_helper.py` + `tests/lib/test_research_helper.py`
**Predecessor plan**: `RESEARCH-FRAMING-REGRESSION-PLAN-V2.md` (Patches 6+7 shipped + empirically verified 3/3 causes on Strata duplicate-options 2026-05-18). V3 stacks on top; do NOT roll Patches 1-7 back.

## Context for next session

V2 closed Gap 6 (symbol-on-screen-but-unfollowed; adapters never traced end-to-end) + Gap 7 (id-stability axis missing from value-semantics classification). Empirical verify on the Strata duplicate-options bug confirmed: V2 identifies the `strataFamilyToItemAdapters.ts:5` Math.random rewriter as a root cause across 3 state surfaces (Finding row, Value Production Sites table, recommended approach Part 1). Score V1 1.5/3 → V2 3/3.

V2 does NOT handle bugs whose root cause is a **hardcoded literal with historical intent**. Empirical artefact: the 2026-05-18 splitOnSNA run on testForge20 (`research/2026-05-18-splitonsna-boolean-incorrect-on.md`, 18.3K).

**The 2026-05-18 splitOnSNA failure mode:**

- Bug: `convertQuoteToOrders` GraphQL mutation sends `splitOnSNA=false` for EXTERNAL + INTERNAL_STAFF identities; should be `true` for those, `false` only for INTERNAL.
- Trace path: `OrderViewer.vue:290 fetchOrder(false)` → `OrderViewer.vue:281 orderBLoC.fetchOrder(..., false, ...)` → `OrderBLoC.fetchOrder` → `FetchOrderUseCase.execute` → `OrderInMemoryRepository.fetchOrder` → Apollo mutation variable `splitOnSNA: isSplit`.
- V2 /research run identified the literal `false` at `OrderViewer.vue:290` as the bug site correctly. Phase 2.4d traced the full handler→write-boundary chain. Phase 2.5 classified `splitOnSNA` as `invariant + stable_across_calls=true` correctly (no Math.random involved).
- Recommended fix: replace `fetchOrder(false)` with `fetchOrder(isExternalUser.value)`.
- **First failure**: `isExternalUser.value` is ALREADY passed as arg 2 to `orderBLoC.fetchOrder` at the same call site one line up (`OrderViewer.vue:281`). The recommended fix would produce `orderBLoC.fetchOrder(quoteId, isExternalUser.value, isExternalUser.value, getQuoteType, isEmeaUser.value)` — same value passed twice in one call. User caught this in iteration 1.
- **Second failure**: LLM never ran `git log -S "false" ...` or `git blame` on the literal. Git archaeology would have shown `false` was inherited from a 2022-02 commit (Roma Frolov) through a 2023-12 refactor (nestor-pineda DEAL-292) that just extracted the inline call into a wrapper — the literal predates the identity-aware split policy by months and was a historical "split feature initial state" assumption, not a deliberate policy choice. User opened blame manually; LLM did not.
- **Third failure**: LLM dismissed the runner-up frame ("centralized data-layer identity→splitOnSNA policy") in 1 turn after canonical-pattern search returned 0 hits. The dismissal logic was "no helper exists project-wide for identity→write-boundary-flag mapping" — but absence of canonical helper ≠ absence of need for one. The runner-up frame was actually closer to the correct architectural fix (wrapper default-param or use-case-level derivation) than the primary frame.

**Iteration outcome:** user pushed back 3 times. Each push corrected one layer of shallowness. Final solution S3 = local-wrapper default `split: boolean = isExternalUser.value` is correct. But the framework should have surfaced S3 in 1 turn, not 3.

**Empirical artefacts (verify these still exist before resuming):**

- 2026-05-18 splitOnSNA run: `/Users/mykolakudlyk/Projects/testForge20/research/2026-05-18-splitonsna-boolean-incorrect-on.md` (18.3K)
- Subject file: `/Users/mykolakudlyk/Projects/testForge20/db-cse-ui-strata/apps/app-web/src/components/order/OrderViewer.vue:290`
- Historical commit for `false` literal: pre-DEAL-292 (Roma Frolov 2022-02-23, line 286 era); DEAL-292 commit `cca351494a` (nestor-pineda 2023-12-12) refactored inline call → wrapper without touching the literal.
- Wrapper-default winning solution recorded in the user-LLM dialogue transcript (in conversation history; not yet persisted).

**Lesson encoded (save as `feedback_literal_archaeology_and_argument_duplication.md` in memory before V3 implementation):** /research must (a) git-blame any hardcoded literal that the recommended fix proposes to replace, and (b) detect when the proposed fix produces argument duplication in a single call (same identifier passed twice) — both signal that the default-source belongs at a different layer (wrapper signature / state initialization / use-case default), not at the call site.

## Diagnosis — two unaddressed gaps

### Gap 8 — Literal-archaeology missing (no commit-history dig before recommending literal replacement)

V2 Phase 2.4d forces end-to-end reads of intermediate functions; V2 Phase 2.5 forces stability classification + production-site recording. Neither forces a `git log` / `git blame` on a hardcoded literal that the recommended fix proposes to replace. The LLM treats the literal as "the bug" without asking "WHY was this literal here? when? deliberate or placeholder?".

Empirical observation 2026-05-18: the `false` literal at `OrderViewer.vue:290` was inherited from a 2022-02 commit through a 2023-12 wrapper refactor. Git archaeology would have shown:
- Originating commit's subject ("Split order ship info" — feature intro, not policy decision).
- The literal predates the identity-aware split-policy requirement that came with STRATA migration.
- Classification: `inherited-refactor` (DEAL-292 preserved the literal verbatim while restructuring around it).

Without archaeology, the LLM's framing is "literal is wrong, replace literal." With archaeology, the LLM's framing becomes "literal was historical placeholder, never adjusted when policy was added; default-source needs to be added at the appropriate layer (wrapper / state-init / use-case), not patched at the call site."

Distinction from earlier gaps:
- Gap 6 (V2): forces reading of intermediate **functions** on the data-flow chain.
- Gap 7 (V2): forces classification of identifier **stability** across calls.
- Gap 8 (V3): forces classification of literal **historical intent** before recommending replacement.

### Gap 9 — Argument-duplication blind spot in recommended-fix shape

When /research recommends replacing a hardcoded literal with a value, no helper-side gate checks whether the resulting call shape would contain the same identifier passed twice. The LLM produces a fix that "works" at the wire level (correct value reaches the right param) but is structurally wrong (the default-source belongs upstream, not duplicated at the call site).

Empirical observation 2026-05-18: recommended fix `orderBLoC.fetchOrder(quoteId, isExternalUser.value, isExternalUser.value, getQuoteType, isEmeaUser.value)`. Argument duplication in a single function call is a red flag for "default belongs elsewhere." Possible elsewhere-locations:
- Wrapper function default parameter (winning S3).
- State-initialization default.
- Use-case / domain method default.
- Upstream caller derivation.

Detection challenge: the LLM expresses the proposed fix in **prose** in the recommended-approach `description` and `rationale` fields. Mechanical detection requires either: (a) parsing those prose fields for `f(a, b, c)` call shapes, OR (b) requiring the LLM to record a separate structured "proposed call shape" string and validating that. Option (b) is more reliable.

Effect: surface-fix wins KISS / minimal-change axis but loses readability / architectural-fit axis. Iteration with user catches it but costs 3 dialogue turns when the framework should catch it in 1.

## Patches

Two patches, in dependency order. Each leaves /research in a buildable, verifiable state. Apply sequentially.

### Patch 8 — Literal-archaeology gate (Gap 8)

**Where**: New helper setter `record-literal-archaeology` + new verify check 17. Spec extension in Phase 2.5 / Phase 3 (recommended-approach drafting).

**Trigger condition**: bug mode + recommended approach modifies a hardcoded literal (defined as: `false`, `true`, integer, float, single-quoted string, double-quoted string, `null`, `undefined` appearing as a positional arg in a function call OR as an assignment RHS in the code at the cited file:line).

**Change**:

1. **New helper setter `record-literal-archaeology`**:
   ```bash
   record-literal-archaeology
     --literal <value>                            (required, non-empty; the literal string as it appears in source — e.g., "false", "0", "''")
     --file-line <path:line>                      (required, valid file:line; where the literal lives)
     --introduced-by <commit-sha>                 (required, 7-40 char hex; commit that introduced the literal)
     --introduced-when <YYYY-MM-DD>               (required, ISO date)
     --commit-subject "<msg subject>"             (required, non-empty)
     --intent <placeholder|migrated|deliberate|forgotten|inherited-refactor|generated>   (required choices — 6-value enum)
   ```

2. **Helper validation**:
   - All required args non-empty.
   - `--literal` is a recognizable literal token (regex covers: JS/TS bools `true|false`, Python bools `True|False`, `null|undefined|None`, decimal `-?\d+(\.\d+)?`, hex `-?0x[0-9a-fA-F]+`, BigInt `-?\d+n`, scientific `-?\d+(\.\d+)?[eE][+-]?\d+`, double-quoted `"[^"]*"`, single-quoted `'[^']*'`, backtick-template `` `[^`]*` `` — no `${}` interpolation supported in template regex; flag interpolated templates as out-of-scope advisory). Out-of-scope (document, do not match): array literals `[]`, object literals `{}`, regex literals `/.../`, function/arrow literals. These rarely surface as the "bug literal" in practice — recommended fix usually targets primitive bools/numbers/strings.
   - `--file-line` parses via `_validate_file_line` (rejects `(none)` sentinel — archaeology requires a real path).
   - `--introduced-by` is hex 7-40 chars.
   - `--introduced-when` parses as ISO date.
   - `--intent` is one of the 6 enum values.

3. **State storage**: append to `report["literal_archaeology"]` array (initialized empty in `default_report_state()`). Row shape: `{literal, file_line, introduced_by, introduced_when, commit_subject, intent}`. Distinct on `(literal, file_line)` — re-recording same `(literal, file_line)` is no-op.

4. **New verify check 17** (gated on bug mode + recommended-approach text containing literal-replacement pattern):
   - Helper computes whether `recommended_approach.description` OR `recommended_approach.rationale` contains a literal-replacement pattern: regex matching `replace <X> with <Y>`, `change <X> to <Y>`, `<X> -> <Y>` where `<X>` is a recognizable literal token.
   - If pattern matched AND no `literal_archaeology` row exists whose `--literal` value matches the detected `<X>` from the prose AND whose `--file-line` matches a `recommended_approach.cites` entry OR a finding's `file_line` → reject:
     ```
     "check 17: recommended approach proposes replacing literal {X!r} at {file_line} but no
     literal_archaeology record exists for it. Run git log -S {X!r} <file> + git blame -L on
     the line; classify intent (placeholder / migrated / deliberate / forgotten /
     inherited-refactor); then call record-literal-archaeology before set-recommended-approach"
     ```

5. **Spec extension in `src/commands/research/main.md`** — new Phase 2.5b section between Phase 2.5 (hypothesis enumeration) and Phase 2.6 (wire findings into helper). Section mandates:
   - When recommended approach's fix involves replacing a hardcoded literal in source: run `git log -S "<literal>" -- <file>` for ALL commits touching the literal; pick the introducing commit (oldest one whose diff added the literal).
   - Run `git show --stat <introducing-commit>` to see the commit subject + scope.
   - Run `git blame -L <start>,<end> <file>` around the literal to confirm the author + date.
   - Classify intent: `placeholder` (literal was a TODO / FIXME / temporary value) / `migrated` (literal carried over from a legacy system, e.g., Q&O → STRATA) / `deliberate` (literal was a considered policy choice with rationale in commit msg) / `forgotten` (literal added during a feature intro but never updated when policy was added later) / `inherited-refactor` (literal was preserved verbatim by a later refactor without re-evaluation).
   - Call `record-literal-archaeology` with the classification.
   - If `intent in {placeholder, forgotten, inherited-refactor}`: the fix layer is the LITERAL-INTRODUCTION layer's caller chain — escalate the default-source one layer up from the literal site (typical: literal at call-site → default at wrapper signature; literal at state init → default at state-init factory function).
   - If `intent == migrated`: investigate the legacy system's behavior for the SAME literal — likely the legacy version had a different default OR an upstream policy that the migration dropped.
   - If `intent == deliberate`: the fix may be the literal-replacement (LLM's instinct was right) — but archaeology record + commit-msg cite REQUIRED to justify overriding a deliberate choice.

**Verify**: re-dispatch /research on the testForge20 splitOnSNA topic. Phase 2.5b runs git archaeology on `false` at `OrderViewer.vue:290`. Discovers DEAL-292 commit (`cca351494a`) inherited the literal from a 2022-02 Roma Frolov commit. Classifies intent as `inherited-refactor`. Spec recovery rule fires: escalate default-source one layer up → wrapper function default parameter (S3) emerges as recommended approach in turn 1, not turn 3.

**Argue**: archaeology adds 3-5 git commands per /research run on bug mode. Cost: ~2-5K tokens per archaeology dig (one `git log -S`, one `git show --stat`, one `git blame -L`). Bounded; far cheaper than the 3 dialogue turns the splitOnSNA case cost. Counter-risk: archaeology may surface tangential history (literal touched by many commits over years) — mitigate by requiring ONLY the introducing commit (oldest), not the full history.

Counter-risk: when the literal lives in a generated file / vendored code, archaeology returns non-actionable history (auto-generated commit). Mitigate: when literal is in a generated file (path matches `**/generated/**` or `**/node_modules/**` or has a `// AUTO-GENERATED` marker in the file header), record archaeology with `--intent generated` (6th enum value, locked); skip the fix-layer-escalation rule (fix layer for generated literals is the generator template, not the consumer).

Counter-risk: multiple refactors over years. Patch 8 anchors on the OLDEST introducing commit (first commit whose diff added the literal). Subsequent refactor history dropped. Edge case missed: literal was deliberate-in-2020, became wrong-after-2023 when a downstream policy was added. Acceptable simplification — `--intent deliberate` rows still trigger commit-msg cite requirement which catches some staleness; full multi-commit timeline is /audit scope, not /research.

### Patch 9 — Argument-duplication shape-check (Gap 9)

**Where**: New required field on `set-recommended-approach` setter + new verify check 18. Spec extension in Phase 3 (approach drafting).

**Change**:

1. **New arg on `set-recommended-approach` subparser**:
   ```bash
   --proposed-call-shape "<exact call as it would appear post-fix>"
   ```
   REQUIRED when: bug mode AND `--single-layer-justification` is set (single-layer recommendation — the case where the fix is most likely to produce argument duplication) OR `recommended_approach.description` matches the literal-replacement regex from Patch 8 (the case where the fix replaces a literal with an existing arg).

2. **Helper validation**:
   - `--proposed-call-shape` is a non-empty string that LOOKS like a function call: regex `^[A-Za-z_][\w.]*\([^)]*\)$` (function name + parenthesized arg list). Multi-line call shapes accepted via collapsed-whitespace pre-processing.
   - Helper parses the arg list (split on top-level commas) + checks for argument duplication: any identifier (regex `[A-Za-z_][\w]*(?:\??\.[A-Za-z_][\w]*)*` — supports optional chaining `a?.b?.c` which is common in modern JS/TS) appearing more than once in the parsed arg list.
   - If duplication detected → reject:
     ```
     "set-recommended-approach: --proposed-call-shape {shape!r} contains argument duplication
     ({duplicated_identifier!r} appears N times in the arg list). Same value passed multiple
     times in one call indicates the default-source belongs at a different layer (wrapper
     signature / state initialization / use-case default). Reconsider the fix layer and
     re-draft."
     ```

3. **New verify check 18** (gated on bug mode + recommended approach has `--proposed-call-shape`):
   - Mirror the duplication check at verify time. Catches direct state-mutation that bypasses the setter gate. Re-uses the same parsing logic.

4. **Spec extension in `src/commands/research/main.md` Phase 3** — before `set-recommended-approach`, the LLM MUST simulate the post-fix call shape literally (substituting the proposed value into the existing call site). If the simulated shape contains argument duplication, the LLM MUST escalate the default-source one layer up before drafting the approach.

**Verify**: re-dispatch /research on the splitOnSNA topic. LLM drafts initial approach "replace fetchOrder(false) with fetchOrder(isExternalUser.value)". Helper-side: when `set-recommended-approach` runs with `--proposed-call-shape "orderBLoC.fetchOrder(Number(quoteId), isExternalUser.value, isExternalUser.value, getQuoteType.value as QuoteType, isEmeaUser.value)"`, helper rejects with check 18. LLM re-drafts to wrapper-default S3: `--proposed-call-shape "fetchOrder()"` (no duplication). Approach committed in turn 1.

**Argue**: detection regex is fragile — multi-line calls, nested calls, spread operators, template literals can defeat naive parsing. Mitigate: pre-process the proposed-call-shape string (collapse whitespace, strip line continuations), document supported call shapes, treat parser failures as warnings (helper emits stderr advisory) rather than rejections. Fail-soft: if helper can't parse the shape, skip the duplication check + log advisory; do NOT block on parsing failure.

Counter-risk: legitimate same-arg-twice exists (e.g., `Math.max(x, x)` is meaningless but valid; `range(0, 0)`). Mitigate: spec language clarifies the rule applies to RECOMMENDED-APPROACH call shapes where the duplicated identifier is the value that REPLACED a literal — not arbitrary same-arg patterns. The duplication rule fires specifically when the fix introduces duplication that didn't exist pre-fix.

Counter-risk: Patch 9 needs Patch 8's literal-replacement-pattern detection to gate when it fires (avoid forcing `--proposed-call-shape` on every bug-mode recommendation). Order matters: ship Patch 8 first; Patch 9 depends on Patch 8's regex.

## Out of scope (this plan)

- **Rolling back Patches 1-7** — they're necessary-not-sufficient for V3's failure mode. V3 stacks on top.
- **State-initialization audit** — the `orderInitialState.isSplit: false` defect (identity-blind state default at `OrderState.ts:50`) is a real bug surfaced during the splitOnSNA dig but lives in a separate file and is independent of the call-site bug. V3 patches don't audit state-init files automatically. Add to /audit scope, not /research.
- **Dead-code sweep** — the orphaned `OrderBLoC.toggleSplit` at `OrderBLoC.ts:84-85` (unused since DEAL-292 wired the toggle through local `splitOrder` handler) is real cruft. Out of /research scope; belongs to /audit.
- **Backend defense-in-depth probe** — V2's H_B hypothesis (server-side coercion / enforcement of identity→split policy) was dismissed too quickly by the 2026-05-18 run. Real fix: verify backend behavior with a runtime probe before declaring /research closed. V3 does NOT add a backend-probe gate; the `verify_step` block already exists for runtime probes, and adding a gate that REQUIRES backend probing for every bug-mode run is too heavyweight.
- **Patches against /specify, /plan downstream** — V3 closes gaps at /research; if the literal-archaeology / argument-duplication regression class re-appears downstream, separate plans.
- **Re-running empirical verify on testForge20 AFTER V3** — that's the verification step. Required to confirm V3 actually closes the gaps before declaring victory. The verify topic is the SAME splitOnSNA topic (re-run + diff against `research/2026-05-18-splitonsna-boolean-incorrect-on.md`).

## Cross-references

- `RESEARCH-FRAMING-REGRESSION-PLAN-V2.md` (predecessor — Patches 6+7 shipped, status reflects 3/3 empirical verification on Strata duplicate-options bug)
- `RESEARCH-FRAMING-REGRESSION-PLAN.md` (V1 — Patches 1-5 shipped, status reflects empirical failure that motivated V2)
- `feedback_literal_archaeology_and_argument_duplication.md` (NEW memory entry — save before V3 implementation; encodes the meta-instinct user surfaced 2026-05-18)
- `feedback_helper_owns_contract_filesystem_forcing` (spec prose can't enforce loop bounds; only mandatory gates that walk filesystem are reliable forcing functions — V3 patches use helper setter gates not prose)
- `feedback_test_first_python_helpers` (every new helper function + every new check has a test in same turn)
- `feedback_dual_agent_verify_command_statements` (spec edits go through instruction-author + instruction-reviewer)
- `feedback_iterative_review_loop_preferred` (apply-verify loop; engineer → reviewer → loop until clean)
- `feedback_cross_check_after_every_change` (grep for affected identifiers / paths / check numbers after each patch)
- `feedback_basic_path_plus_user_fallback` (when archaeology fails — e.g., file not in git, shallow clone, generated file — fall back to user prompt asking for intent classification)

## Resume-in-fresh-session prompt

Paste the following into a fresh Claude Code session at `~/Projects/ai-dev-team-forge` (run `/clear` first if continuing in the same shell):

```
Resume RESEARCH-FRAMING-REGRESSION-PLAN-V3.md at repo root. Read the plan top-to-bottom — Context, Diagnosis (Gaps 8 + 9), Patches 8 + 9, Out of scope, Cross-references, When-resuming-work. Read the predecessor plan RESEARCH-FRAMING-REGRESSION-PLAN-V2.md's Status field for V2's empirical-verification context.

Pre-flight: save the meta-instinct lesson to memory as feedback_literal_archaeology_and_argument_duplication.md BEFORE implementing V3 patches. Lesson encodes the user's chain-of-thought ("hardcoded literal must have reason — dig commit history" + "fix that duplicates an existing arg = wrong layer") so future sessions inherit the instinct without re-deriving.

Implementation order: Patch 8 (literal archaeology gate, with --intent classification + check 17) → Patch 9 (argument-duplication shape check + check 18; depends on Patch 8's literal-replacement regex). Each implementation patch in its own commit on develop-2.0-init.

Per-patch flow (same as V2):
  (a) Draft helper setter changes + verify checks via python-engineer agent with test-first discipline (per feedback_test_first_python_helpers; tests via /Users/mykolakudlyk/Projects/ai-dev-team-forge/.venv-test/bin/pytest tests/lib/test_research_helper.py).
  (b) Run python-reviewer on the helper additions (per feedback_dual_agent_verify_command_statements).
  (c) Apply reviewer findings; re-loop until clean.
  (d) Draft Phase-N spec edits in src/commands/research/main.md directly (orchestrator-owned; instruction-reviewer dispatched on output).
  (e) Run instruction-reviewer on the spec edits.
  (f) Apply reviewer findings; re-loop until clean.
  (g) Cross-check: grep for affected identifiers / paths / check numbers across the file.
  (h) Update RESEARCH-FRAMING-REGRESSION-PLAN-V3.md Status field.
  (i) Commit (stage only the patched files — research_helper.py + research/main.md + test_research_helper.py + this plan).

After Patch 9 lands: run update.sh --force on testForge20 to propagate, then re-dispatch /research on the splitOnSNA topic (same topic as 2026-05-18 run). Diff against testForge20/research/2026-05-18-splitonsna-boolean-incorrect-on.md. CRITICAL — the empirical-verify acceptance criterion this time is "did the new run propose the wrapper-default S3 solution in turn 1 without requiring 3 dialogue rounds?". If yes, V3 closes the gaps. If no, V3's structural gates were also insufficient — surface a new gap and draft V4.

DO NOT roll back Patches 1-7. They're structural improvements that stand on their own. V3 stacks on top.

DO NOT skip the empirical-verify-replay step. The lesson from V1+V2 is that structural gates pass tests but can still miss the original failure mode. V3 must replay the testForge20 splitOnSNA topic + check the turn-1-S3 acceptance criterion explicitly before declaring victory.
```

## When resuming work

1. Read this plan top-to-bottom + the V2 plan's Status field.

2. Verify empirical artefacts still exist (paths may have changed since 2026-05-18):
   ```bash
   ls -la /Users/mykolakudlyk/Projects/testForge20/research/2026-05-18-splitonsna-boolean-incorrect-on.md \
          /Users/mykolakudlyk/Projects/testForge20/db-cse-ui-strata/apps/app-web/src/components/order/OrderViewer.vue
   ```

3. Verify Patches 1-7 still landed (drift possible):
   ```bash
   git -C /Users/mykolakudlyk/Projects/ai-dev-team-forge log --oneline develop-2.0-init -15 | grep -E "Patch [1-7]"
   ```
   Expected: 7 commits — 832aa4e (Patch 1), b8e6098 (Patch 2), c8a9ca3 (Patch 3), 5eaa704 (Patch 4), 4a6a519 (Patch 5), 7a82a87 (Patch 6), 73ef728 (Patch 7).

4. Verify research_helper.py + research/main.md are at expected post-V2 shape:
   ```bash
   grep -nE "cmd_record_data_flow_chain|cmd_record_value_production_site|check 15|check 16|stable-across-calls" /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/devforge/lib/research_helper.py | head -8
   grep -nE "Phase 2.4d|Phase 2.5.*stability|record-value-production-site|check 16" /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/commands/research/main.md | head -8
   ```

5. Confirm test baseline:
   ```bash
   /Users/mykolakudlyk/Projects/ai-dev-team-forge/.venv-test/bin/pytest tests/lib/test_research_helper.py 2>&1 | tail -3
   ```
   Expected: 267 passed.

6. Save the meta-instinct lesson to memory (`feedback_literal_archaeology_and_argument_duplication.md`) BEFORE writing any V3 code. Reasons recorded earlier; ensures the instinct survives if V3 implementation is interrupted.

7. Apply Patch 8 (literal-archaeology gate), then Patch 9 (argument-duplication shape check). Each = one commit. Do not bundle.

   **Cost-surface note**: Patch 8 archaeology adds 3-5 git commands per bug-mode /research run = ~2-5K tokens per dig. Patch 9 adds 1 helper-side regex check per `set-recommended-approach` call = negligible token cost. Total added cost: ~3-5K tokens per /research run.

8. After Patch 9 lands + tests green:
   a. Run `~/Projects/ai-dev-team-forge/update.sh --force /Users/mykolakudlyk/Projects/testForge20`.
   b. Open a fresh Claude Code session in `/Users/mykolakudlyk/Projects/testForge20`.
   c. Run `/research "<splitOnSNA topic phrasing>"` (same topic as 2026-05-18 run).
   d. Diff output against `research/2026-05-18-splitonsna-boolean-incorrect-on.md`. Check specifically: does the new run propose the wrapper-default S3 solution as Approach 1 without requiring user iteration? AND does it record a `literal_archaeology` entry for the `false` at `OrderViewer.vue:290` with intent=`inherited-refactor`? Both must be true.

9. Update this plan's Status: **V3 applied + empirically verified (turn-1-S3 acceptance)** OR **V3 applied + empirical verify still failing — draft V4 against the new gap**.

## Notes for engineer / reviewer

- Helper changes are test-first per `feedback_test_first_python_helpers`. Every new setter + every new verify check has a test in `tests/lib/test_research_helper.py` written + run in the same turn. Tests via `/Users/mykolakudlyk/Projects/ai-dev-team-forge/.venv-test/bin/pytest tests/lib/test_research_helper.py` (system python3 lacks pytest; use venv binary).

- Helper-owns-shape pattern per `feedback_helper_owns_shape_principle`: `literal_archaeology` is a list of `{literal, file_line, introduced_by, introduced_when, commit_subject, intent}` dicts. `recommended_approach.proposed_call_shape` is a string field.

- Spec edits via direct orchestrator edit; instruction-reviewer dispatched for verification per `feedback_dual_agent_verify_command_statements`. Scope = intra-file only per `feedback_intra_file_only_consistency_check`.

- Cross-check after every patch: grep for affected identifiers / paths / section numbers / check numbers per `feedback_cross_check_after_every_change`. Specifically watch for verify-checks paragraph at the END of Phase 3 in main.md — needs check 17 + check 18 added when those patches land. Also update module docstring subcommand summary (line ~33) — count goes 45 → 46 (record-literal-archaeology); Phase 2.5b group added.

- Patch 8's literal-replacement regex must match the prose patterns the LLM actually uses in recommended-approach text. Test cases: `"replace fetchOrder(false) with fetchOrder(isExternalUser.value)"`, `"change false to isExternalUser.value at line 290"`, `"false -> isExternalUser.value"`, `"swap the literal false for the identity-derived bool"`. Regex should match all 4 forms; over-matching (false positives) is acceptable — better to require archaeology on a few non-literal fixes than miss the actual literal-replacement cases.

- Patch 9's call-shape parser is fragile by design. Accept the parsing failure mode: on parse failure, emit stderr advisory + skip the duplication check + return success. Do NOT block /research on a parser corner case. The check is BEST-EFFORT structural guidance, not a hard correctness gate.

- The `--intent` enum has 6 values (LOCKED 2026-05-18): `placeholder | migrated | deliberate | forgotten | inherited-refactor | generated`. The `generated` value applies to files in `**/generated/**`, `**/node_modules/**`, or files with `// AUTO-GENERATED` marker in header; archaeology record is still required (forward-compatibility + audit trail) but the fix-layer-escalation rule skips (fix layer for generated literals is the generator template, not the consumer).

- Patch 8 archaeology can be partial when running on a shallow git clone (no full history). Fall-through: on `git log -S` returning 0 commits OR `git blame` returning "(uncommitted)", treat as `--intent forgotten` + add advisory note in stderr. Don't fail — the gate is informational on shallow-clone environments.

- The `proposed_call_shape` field is a NEW key on `recommended_approach`. Adding it to the dict is forward-compatible (existing render code that doesn't know about the field will skip it). Update `_render_report_md` to surface `proposed_call_shape` under the recommended-approach section when present.

- Reviewer findings application loop is the same as V2: python-engineer → python-reviewer → apply findings → re-loop until clean → instruction-reviewer → apply findings → re-loop until clean.
