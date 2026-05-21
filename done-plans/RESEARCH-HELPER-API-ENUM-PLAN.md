# Research command — Helper-API surface enumeration (Phase 2.4c)

## Context for next session

`/research` currently produces unreliable recommendations. Natural experiment on the same `convertQuoteToOrder splitOnSNA=false` bug across `testForge20` and `cse-strata-ws-forge` produced:

- testForge20 pass 1 → Option A (view-layer one-line fix). Wrong.
- testForge20 pass 2 (after user critique "look on BLoC") → Option B-revised (drop redundant param + revive dead `OrderBLoC.toggleSplit`). Correct.
- strata pass 1 → Option A. Wrong.
- strata pass 2 (after same user critique) → Option B-shallow (`splitOnSNA = isExternal || isSplit` at use case). Self-corrected with named introspection but still missed dead `toggleSplit` and the API-as-designed signal.

3 of 4 attempts produced wrong recommendation. Pushback recovered only 1 of 2. The model's introspection theatre (5-mistake mea culpa) did not produce a correct corrected answer — strata pass 2 was still shallow.

Root-cause analysis identified **four distinct gaps** in the current research rubric, all related but not reducible to one:

1. **Forward data-flow trace** — model never asked "what does this flag do downstream / why does it exist?". Both researches treated `splitOnSNA` as opaque payload, missed that the spec rule was an invariant (Q&O parity at server boundary), not a UI preference.
2. **Inbound caller enumeration on every helper on fix path** — model never enumerated callers of `OrderBLoC.fetchOrder` to do a bug-class-vs-instance check.
3. **Sibling-method enumeration on classes owning fix-path helpers** — `OrderBLoC.toggleSplit` is dead (empty inbound) and encoded the API as originally designed; missed entirely by strata, found by testForge20 v2 only because user prompt said "look on BLoC".
4. **Preference-vs-invariant classification of symptom values** — without this classification, model defaults to "minimal change" reflex, which biases toward view-layer fixes.

Current spec at `src/commands/research/main.md` (32K) covers parallel-pattern sweep (2.4) and canonical SOLUTION pattern search (2.4b) but has no helper-API surface enumeration. `trace_path` is listed as available but with `mode` left to model judgment.

This plan inserts **Phase 2.4c** between current 2.4b and 2.5, adds classification to 2.5, and adds a Phase 3 setter constraint that makes invariant + dead-sibling combinations force a helper-signature-touching approach to be enumerated.

The goal is structural — forcing functions via mandatory CBM calls + helper-side cross-checks, not prose heuristics. Heuristics are what got us here.

## Active assumptions

- Single `research_helper.py` (75K) + single `test_research_helper.py` (54K). No `_research_/` subpackage exists.
- `research_helper` is invoked as a Bash executable (shebang script wrapping the Python module). Setter subcommands extend the existing CLI surface; storage is `.devforge/research-state.json` + `.devforge/research-report.json`.
- CBM provides `trace_path` with `mode ∈ {calls, data_flow, cross_service}` and `direction ∈ {inbound, outbound}`. Verified via existing references in spec.
- Spec authoring conventions reviewed via the `claude-code-guide` agent are honored where they apply (Claude Code slash-command structure, frontmatter, MANDATORY directive style). Framework-internal helper conventions are governed by this repo's CLAUDE.md.
- Test-first discipline (per `feedback_test_first_python_helpers`): every new helper function ships with a test written + run in the same turn.

## Out of scope

- `/discover` parallel changes — port only if `/research` regression suite passes.
- Re-architecting the entire research helper into a `_research_` subpackage (would conflict with existing 75K monolith; defer).
- Generalizing Phase 2.4c to all symptom kinds (perf, refactor, dead-code audits) — scope to bug + enhancement modes only.
- Adding a separate `research_helper enumerate-helper-api` aggregator subcommand (Alt 4 in design discussion). Defer to v2 if v1 prose-level forcing function underperforms regression.

## Implementation steps

Each step ends in a buildable + verifiable state. No step depends on a later step's output for verification.

### Step 1 — Helper state schema additions

**Files**: `src/devforge/lib/research_helper.py`, `tests/lib/test_research_helper.py`

Add the following fields to the in-memory + on-disk `ResearchReport` shape (Phase 0 SymptomMemo is untouched):

- `fix_path_helpers: list[str]` — qualified names of helpers on the fix path (the helpers whose signature carries the symptom value or its source). Deduped on append by `record-fix-path-helper`.
- `value_semantics: list[{value: str, classification: str, evidence: str}]` — per-symptom-value records; `classification` ∈ {`preference`, `invariant`, `unclassified`}; `evidence` is a one-line citation (a `file_path:line` or consumer name). Upsert semantics on `value` key: second call with same `value` overwrites; new `value` appends. `evidence` lives inside each row — there is no separate `value_semantics_evidence` field.
- `dead_siblings: list[{class_qn: str, method_qn: str, verified_via: str}]` — sibling methods with empty inbound traces; `verified_via` ∈ {`trace_path`, `search_code`}. No dedupe: two recordings of the same `(class_qn, method_qn)` from different trace passes are both kept; verify checks tolerate duplicates.
- `inbound_callers: list[{helper_qn: str, caller_qn: str, file_line: str}]` — callers found for every fix-path helper.
- `consumer_chain: list[{value: str, consumer_qn: str, file_line: str, role: str}]` — forward data-flow trace endpoints for each symptom value.

Use fresh-defaults pattern (matching existing `reset-memo` / `reset-report` style) so `reset-report` wipes these to empty lists / `None`.

**Test**: add one fixture-driven test per field demonstrating round-trip (reset → set → read JSON file → assert shape). Run pytest in the same turn.

**Verify**:
- `pytest tests/lib/test_research_helper.py -k "<new test names>"` passes.
- `python -m research_helper reset-report && cat .devforge/research-report.json` shows fresh-default values for new fields.

**Argue**: placing classification + evidence at the report level (not memo) keeps Phase 1 unchanged. Phase 2 produces these. Risk: schema grows; mitigated by keeping all six fields tightly typed + cleared on reset.

### Step 2 — Helper setter subcommands

**Files**: `src/devforge/lib/research_helper.py`, `tests/lib/test_research_helper.py`

Add subcommands:

- `record-fix-path-helper --helper-qn <qn>` — append to `fix_path_helpers`.
- `record-inbound-caller --helper-qn <qn> --caller-qn <qn> --file-line <path:line>` — append to `inbound_callers`.
- `record-dead-sibling --class-qn <qn> --method-qn <qn> --verified-via <trace_path|search_code>` — append to `dead_siblings`. The `--verified-via` field documents which evidence source confirmed the sibling is dead; ignored unless the spec's cross-verify step ran.
- `record-consumer-chain --value <symbol> --consumer-qn <qn> --file-line <path:line> --role <one-line>` — append to `consumer_chain`.
- `set-value-semantics --value <symbol> --classification <preference|invariant|unclassified> --evidence <file:line or consumer name>` — upserts into `value_semantics` keyed on `value`; the `evidence` lives inside the same row. Helper rejects classifications outside the allowed enum; rejects `invariant` (exit code 2) when no `consumer_chain` row exists for the same `value` — call `record-consumer-chain` first.

`--file-line` arguments must validate as `<non-empty path>:<positive integer>` or the literal sentinel `(none)`. Reuse existing validation pattern from `record-finding`.

**Test**: per-subcommand happy path + rejection cases (invalid classification, missing evidence on invariant, malformed `file-line`). Pytest in same turn.

**Verify**:
- All new tests pass.
- Each subcommand emits non-zero exit + meaningful stderr on rejection cases.

**Argue**: granular setters match existing helper style (`set-X`, `record-X`). Resist temptation to add an aggregated `enumerate-helper-api` setter — that's Alt 4. The Phase 3 cross-check is the constraint, not the setter shape.

### Step 3 — Helper verify cross-checks

**Files**: `src/devforge/lib/research_helper.py`, `tests/lib/test_research_helper.py`

Extend `research_helper verify` with these additional cross-checks (added after existing checks, ordered to short-circuit cheapest first):

1. If `memo.mode == "bug"`, then `fix_path_helpers` must be non-empty.
2. If `fix_path_helpers` is non-empty, then for every helper QN in the list, `inbound_callers` must contain at least one row referencing it (the "at least the symptom-site caller" row).
3. If any `value_semantics` row has `classification == "invariant"` AND `dead_siblings` is non-empty, then `approaches` must contain at least one approach whose `name`, `description`, `pros`, or `cons` mentions modifying the helper's signature OR reusing one of the dead-sibling `method_qn` values. Helper checks via case-insensitive substring on the literal tokens `"signature"`, `"drop param"`, plus every recorded dead-sibling `method_qn`.
4. If any `value_semantics` row has `classification == "invariant"`, then `recommended_approach.rationale` must reference either a `consumer_chain.consumer_qn`, a `value_semantics.evidence` string from an invariant row, or a dead-sibling `method_qn`. Helper checks via case-insensitive substring; if the candidate token list is empty (no evidence anywhere), the check degrades gracefully and emits no violation.

Each new check emits a distinct line on stderr identifying the violation + the setter to call to fix it.

**Test**: one happy-path + one failure-path per new check. Pytest in same turn.

**Verify**:
- All new tests pass.
- Manual smoke: hand-author a state JSON that violates each check; confirm `verify` rejects with the correct stderr line.

**Argue**: substring matching for QN references is imperfect (a generic word could match accidentally), but stronger constraint (AST-level cite parsing) is overkill for v1. Acceptable false-positive rate: low, because QNs are usually multi-segment dotted paths unlikely to collide with prose tokens.

### Step 4 — Spec update: Phase 2.4c insertion

**File**: `src/commands/research/main.md`

Insert new `### Phase 2.4c — Helper-API surface enumeration (MANDATORY for bug mode; OPTIONAL for enhancement)` between current Phase 2.4b and Phase 2.5.

Content covers (write in spec style matching surrounding sections):

- **Definition of "fix-path helper"**: any helper whose signature carries the symptom value or any value the symptom value derives from. Stopping rule: trace at most 2 layers above the symptom site through helpers in the same package; do not cross package boundaries.
- **For each fix-path helper, run three CBM calls in this order**:
  1. `trace_path(<helper_qn>, mode=calls, direction=inbound)` — list every caller. Record each via `record-inbound-caller`.
  2. `search_graph(label="Method", qn_pattern="<containing_class>\\.")` followed by `trace_path mode=calls direction=inbound` on each sibling. Apparent dead siblings (empty inbound) must be cross-verified via `search_code(pattern="<method-name>(")` to rule out dynamic dispatch. Record confirmed dead siblings via `record-dead-sibling`.
  3. For every symptom value, `trace_path(<value-source>, mode=data_flow, direction=outbound)`. Record consumer-chain endpoint via `record-consumer-chain`.
- **Recording**: every helper found goes through `record-fix-path-helper` first. The CBM `file_path:line` grounding rule from Phase 2.3 applies.
- **MANDATORY**: skipping is forbidden in bug mode. Helper `verify` rejects empty `fix_path_helpers` on bug mode.

**Verify**:
- `grep -n "Phase 2.4c" src/commands/research/main.md` finds the new section.
- Section numbering downstream of 2.4c is unaffected (2.5, 2.6 retain numbers).
- Cross-grep: no other spec file references "Phase 2.4c"; if a downstream spec mentions Phase 2 sections by number, update those references too.

**Argue**: 2-layer trace cap is conservative — covers OrderViewer → OrderBLoC → FetchOrderUseCase chain but stops before infrastructure layers. Adjustable later if regression suite shows misses.

### Step 5 — Spec update: Phase 2.5 classification

**File**: `src/commands/research/main.md`

Extend current Phase 2.5 ("Hypothesis enumeration") with a leading classification step:

- Before enumerating hypotheses, classify every symptom value cited in the memo's `desired` dimension as `preference` (per-user-action, per-toggle, per-request-context) or `invariant` (per-identity, per-business-rule, payload-shape contract).
- Evidence must come from a consumer-chain entry recorded in Phase 2.4c. If no consumer chain was recorded for a value, classification is `unclassified` and bug-mode verify fails.
- Call `set-value-semantics` for each classified value.

**Verify**:
- `grep -n "set-value-semantics" src/commands/research/main.md` returns at least one hit.
- Phase 2.5 still says "≥2 hypotheses" (classification is additive, not a replacement).

**Argue**: classification before hypothesis enumeration ensures hypotheses are framed against the right semantics. If the value is invariant, "view layer doesn't seed correct default" is a wrong-framing hypothesis — should be "no chokepoint enforces invariant".

### Step 6 — Spec update: Phase 3 constraint

**File**: `src/commands/research/main.md`

In Phase 3 setters:

- Add to `set-approach` MANDATORY guidance: when `value_semantics == "invariant"` AND `dead_siblings` is non-empty, at least one approach in the enumerated list must touch the helper signature or revive a dead sibling. Cite the dead-sibling QN explicitly in the approach `description` or `pros`.
- Add to `set-recommended-approach` MANDATORY: when `value_semantics == "invariant"`, the `--rationale` must cite either a consumer-chain entry (by `consumer_qn` or value evidence string) or a dead-sibling QN.

The helper verify additions from Step 3 enforce both at gate time.

**Verify**:
- `grep -n "value_semantics" src/commands/research/main.md` returns hits in Phase 2.5 + Phase 3.
- Manual read: the spec text matches the helper cross-check behavior (no drift between prose + helper enforcement).

**Argue**: this is where lock-in-by-enumeration is broken. The constraint forces the approach list to include a helper-signature option whenever the evidence demands it.

### Step 7 — Spec sentence-level hallucination check + cross-reference grep

**Files**: `src/commands/research/main.md`, anything that references research-command phase numbers or `research_helper` setter names.

Walk the spec sentence by sentence (per `feedback_sentence_level_hallucination_check_specs`). Every claim about a helper subcommand must match the actual subcommand name added in Step 2. Every claim about a state field must match the schema in Step 1.

Cross-ref grep targets:

- New setter names (`record-fix-path-helper`, `record-inbound-caller`, `record-dead-sibling`, `record-consumer-chain`, `set-value-semantics`) — verify no typo'd cites in spec, and grep elsewhere in repo to confirm no other doc mentions them with a different spelling.
- New state fields (`fix_path_helpers`, `value_semantics`, `dead_siblings`, `inbound_callers`, `consumer_chain`) — same. Note: `evidence` is a key inside each `value_semantics` row, not a separate top-level field.
- Phase 2.4c references in any downstream doc.

**Verify**:
- `grep -rn "record-fix-path-helper\|record-inbound-caller\|record-dead-sibling\|record-consumer-chain\|set-value-semantics" src/` returns only the expected hits (helper source, spec, possibly tests).
- No dangling reference to a renamed or moved section.

**Argue**: mandatory per CLAUDE.md cross-check rule. Skipping leaves dangling references that are tomorrow's audit findings.

### Step 8 — Regression test on testForge20 + cse-strata-ws-forge

**Files**: none modified; pure observational pass.

Re-run `/research` with the identical first-pass prompt (the verbatim original symptom description for the splitOnSNA bug) on both testForge20 and cse-strata-ws-forge installs. No user nudge. Compare pass-1 recommendation to the user-pushback-corrected B-revised target.

Document the comparison in a new `research/2026-MM-DD-rubric-regression.md` under each project root (capturing the pass-1 output verbatim + a diff against the target).

**Verify**:
- Pass criterion: pass-1 recommended approach matches B-revised (drop `isSplit` param from `OrderBLoC.fetchOrder`, revive `toggleSplit`) without user nudge.
- Acceptable variant: pass-1 lists B-revised as one approach + recommends it as primary even if naming differs.
- Failure: pass-1 still recommends Option A (view-only fix) or B-shallow (one-line OR-invariant).

**Argue**: this is the only honest test that the rubric change actually fixed the behavior. Skipping = shipping unvalidated.

### Step 9 — Decision gate: ship or escalate

**Files**: none modified.

Branch on Step 8 outcome:

- **Both pass-1 outputs hit B-revised**: ship. Commit the spec + helper changes on `develop-2.0-init`. Update `MEMORY.md` (auto-memory) with a project memory documenting the rubric gain.
- **One passes, one fails**: investigate the failing case. Likely the failure is in the trace cap (Step 4 stopping rule) or in the classification evidence rule (Step 5). Patch + re-run Step 8 only.
- **Both fail**: prose-level forcing function is insufficient. Escalate to Alt 4 — build a `research_helper enumerate-helper-api` subcommand that walks the CBM graph directly and returns structured `fix_path_helpers` + `dead_siblings` + `consumer_chain` as a single call. Replace Phase 2.4c's three-call sequence with one helper invocation. New plan needed.

**Verify**:
- Decision is documented in a new git commit message + a closing note in this plan file.

**Argue**: explicit gate prevents the "we built it, it half-works, let's ship anyway" failure mode.

## When resuming work

1. Read this plan in full.
2. Read the current state of `src/commands/research/main.md` and `src/devforge/lib/research_helper.py` — they may have moved on.
3. Check `git log --oneline develop-2.0-init` for any commit titled `feat(research): phase 2.4c …` or similar to see if any steps already shipped.
4. Verify the natural-experiment data is still relevant: the strata + testForge20 research files at `research/2026-05-15-*.md` in each project should still exist and match what this plan describes. If they've been overwritten, the regression test in Step 8 needs new baseline.
5. Pick up at the lowest-numbered incomplete step. Steps 1-3 (helper) can ship as one commit, then steps 4-7 (spec) as a second commit, then steps 8-9 (validate) as the third.
6. Cap each spec edit with the `instruction-reviewer` agent pass per `feedback_iterative_review_loop_preferred`.

## Risks and accepted trade-offs

- **Spec length grows by ~80-120 lines.** Accepted; the failure mode it eliminates is high-impact (wrong recommendation propagated to `/specify` → wrong fix shipped).
- **Floor cost of `/research` grows by 3-15 CBM calls per fix-path helper.** Accepted; cost gate at Phase 2.1 already discloses cost to user.
- **Dead-sibling detection has false positives on dynamic dispatch.** Mitigated by mandatory `search_code` cross-verify (Step 4 spec text).
- **Substring matching for QN cites in Phase 3 verify can false-positive.** Accepted; alternative (AST-level cite parsing) is overkill for v1.
- **No automated regression harness.** Step 8 is manual run on two real projects. Future work: capture the natural-experiment prompts as a fixture and run pass-1 nightly.

## Cross-cutting work NOT in this plan

- Porting Phase 2.4c equivalent to `/discover` — defer to a separate plan if `/research` ships and works.
- Building the `enumerate-helper-api` aggregator helper subcommand (Alt 4) — only if Step 9 escalates.
- Refactoring `research_helper.py` (75K monolith) into a `_research_` subpackage — out of scope; existing monolith works.
