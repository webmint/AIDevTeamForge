# Validator-Loop Plan — annotator quality gate (markdown bridge + graph native)

**Status**: Draft, not started. Two parts:
- **Part A** — markdown bridge: validator loop dropped into current `/generate-docs` Phase 3 on `develop-2.0-init`. Empirical test target: testForge20.
- **Part B** — graph native: validator loop addendum to `CODEGRAPH-INTEGRATION-PLAN.md` Phase B (helper API + schema).

**Origin**: Obsidian note `20 Projects/AIDevTeamForge/rewritePlans/LLM-augmented knowledge graph - architecture and generalization controls.md`. Note diagnoses 6-cause generalization failure mode; per-node dispatch alone covers 4/6 (~70%); validator loop covers remaining 30% (archetype substitution + missing back-pressure).

**Why validator loop now**: Run 4 against testForge20 produced 597 tree descriptions; LLM honest breakdown 5% verified / 25% hand-mapped / **70% regex camelCase filename echo**. Step 3.3.5 retreats by spec-declaring "tree descriptions = hints, not docs." Validator loop is the alternative — keep semantic load, gate it mechanically.

**Promotion criterion**: Part A on testForge20 components/ concern (50-entry sample) produces ≥80% `extracted` confidence + 0 banned-phrase hits + 0 identical-text duplicates → validator loop is the right tool. Then Part B becomes the native implementation in graph stack.

**Failure handling**: if Part A on testForge20 still produces archetype paragraphs after 3 retry rounds, the failure is in prompt design (not loop design). Iterate prompt. If that still fails, retreat to Step 3.3.5 hint-only contract.

---

## Context for next session

Validator loop = the actual quality gate per Obsidian note. Annotator proposes, validator enforces. Most engineering effort goes into validator. Weak validator → thousands of generic annotations efficiently. Strong validator → thousands of specific annotations at higher cost. **Cost is the right thing to spend on; quality is not.**

Six generalization causes (Obsidian note):
1. Context dilution
2. Output budget pressure (most-generic words win)
3. **Archetype substitution** (pretrained reflex — survives any dispatch)
4. Repetition fatigue (file 30 = same shape 29×)
5. No grounding contract
6. **No back-pressure** (no forced cite — survives unless schema mandates)

1/2/4/5 die under per-node isolation. **3 + 6 require prompt + validator design.**

Annotator prompt must enforce:
- Evidence-first ordering (read source → cite line range → label)
- Mandatory `_evidence: file:start-end` per claim
- Banned-phrase reject list: `handles`, `manages`, `processes`, `validates`, `various`, `etc`, `responsible for`
- Specificity test: "if label could apply to >5 other functions in any codebase, refine"
- vs-siblings framing (agent receives sibling names, must differentiate)
- Confidence calibration: `extracted` / `inferred` / `ambiguous`
- Negative-space test: "what lost if this node deleted?"

Validator loop:
1. Annotator proposes typed annotation
2. Mechanical validator: schema + cite resolves + banned-phrase + specificity + confidence distribution + vs-siblings differentiation
3. Pass → commit
4. Fail → feedback → retry ≤3
5. Exhaust → tag `ambiguous` + escalate to stricter model (Sonnet) for one final round; never silently accept untagged

Post-batch verification queries:
- Topics covering >N% of nodes → too generic
- Identical text across disjoint code → over-generalization
- Annotations with no resolvable cite → reject
- Confidence skew toward `inferred`/`ambiguous` → bad batch
- Pairs of nodes with identical labels but disjoint callers → not differentiating

Failures gate promotion of annotation set into queryable surface (`/research`, `/fix`).

Cost tier (per note):
- Haiku annotator @ ~$0.005/call → $25-100 / full pass on 5k-20k nodes
- Sonnet only on validator failure escalation
- Opus reserved
- Parallel dispatch (~200 concurrent), temperature=0, content-hash cache (skip re-annotate if source range unchanged)

---

## Pre-A.2 split (executed 2026-05-06)

`_validators.py` 1193-line monolith was split per its own docstring plan into 5 files: `_validators_shared.py` (123 lines), `_validators_package.py` (511 lines), `_validators_concern.py` (441 lines), `_validators_decomposition.py` (147 lines), and `_validators.py` (77-line re-export shim, zero function defs). All 784 tests pass post-split. Step A.2's new validation rules land in `_validators_concern.py` (annotations are concern-scoped).

## Pending split — `_setters_concern.py` (flagged 2026-05-06)

After Fix B (`set-concern-tree` coverage gate), `_setters_concern.py` grew to 828 lines, 38% past the 600-line threshold. Planned next split: extract coverage helpers (`_load_index_files`, `_path_contains_trivial_dir`, `_build_expected_entry_set`, `_count_rendered_tree_entries`, `_check_tree_entry_coverage`) into `_setters_concern_coverage.py`. **The NEXT addition to `_setters_concern.py` must execute that split first.**

---

## Part A — Markdown bridge (current `/generate-docs`)

Goal: drop validator loop into Phase 3 concern slot-fill on `develop-2.0-init` without changing storage backend (markdown). Target: tree-description annotation specifically (the 70%-filename-echo failure point).

### Step A.1 — Annotation schema + helper API

Helper-owns-shape principle: helper validates structure, LLM composes values.

Add to `src/devforge/lib/generate_docs_helper.py`:
- `add-annotation --concern C --target-path P --label "..." --confidence (extracted|inferred|ambiguous) --cite-file F --cite-start S --cite-end E`
- Schema validation: label non-empty, confidence in enum, cite triple complete
- State write: append to `state["concerns"][C]["annotations"][P]`

Annotation record shape:
```json
{
  "label": "...",
  "confidence": "extracted|inferred|ambiguous",
  "evidence": {"file": "F", "start": S, "end": E},
  "model_version": "claude-haiku-4-5-20251001",
  "content_hash": "sha256(file_content[start:end])"
}
```

#### Verify A.1
- New helper function passes own unit test (round-trip add → read → fields preserved)
- `validate-concern` includes annotation schema check (via `_check_concern_annotations` in `_validators.py`)
- Test file: `tests/lib/test_add_annotation.py` — happy path + invalid confidence + missing cite

### Step A.2 — Mechanical validator

Add to `src/devforge/lib/generate_docs_helper.py`:
- `validate-annotation --concern C --target-path P` returns exit code:
  - 0 = pass
  - 2 = banned-phrase hit (stderr: which phrase)
  - 3 = cite unresolvable (stderr: file/range mismatch)
  - 4 = specificity fail (stderr: identical-label sibling found)
  - 5 = schema invalid
  - 6 = cite-file is binary (NUL byte in first 8KB)

Checks:
1. **Schema**: required fields present, confidence in enum
2. **Cite resolves**: `extract-snippet --file F --start S --end E` succeeds (reuses existing helper)
3. **Banned phrase**: regex match on label against fixed list. List in `src/devforge/lib/_banned_phrases.py` (separate module → easy to extend per ecosystem later, but starts with note's verbatim list)
4. **Specificity**: query state for siblings (same parent path); reject if any sibling has identical label
5. **Vs-siblings differentiation**: NOT mechanically enforceable — LLM-generated; validator can only reject identical labels (specificity #4 covers)
6. **Cite-file is text**: reject if the first 8 KB of `cite-file` contains a NUL byte (binary file detection — the set-time gate in `add-annotation` accepts binary files with replacement-character hashing; this check is where binary citations are rejected)

Banned phrases v0:
```python
BANNED_PHRASES = [
    "handles", "manages", "processes", "validates",
    "various", "etc", "responsible for",
]
```

#### Verify A.2
- Banned phrase grep test (each phrase triggers exit 2)
- Cite-mismatch test (deliberately wrong line range → exit 3)
- Sibling-collision test (two annotations under same parent with identical label → exit 4)
- Pass case (clean annotation → exit 0)
- Binary cite-file test (NUL byte in first 8KB → exit 6)

### Step A.3 — Retry loop in `/generate-docs` spec

Modify `src/commands/generate-docs/main.md` Phase 3.3 concern slot-fill.

Insert per-annotation loop (replaces current single-shot tree-entry generation):

```
For each tree entry:
  attempt = 0
  while attempt < 3:
    LLM generates annotation (label + cite + confidence)
    helper.add-annotation --concern C --target-path P --label L --confidence K --cite-file F --cite-start S --cite-end E
    helper.validate-annotation --concern C --target-path P
    if exit 0: break
    else: feedback to LLM with stderr reason; attempt += 1
  if attempt == 3:
    re-attempt with stricter model (escalation) ONE TIME
    if still fail: tag confidence=ambiguous, commit, continue
```

Spec discipline: validator feedback verbatim into LLM next prompt (no paraphrase). LLM cannot retry blind.

#### Verify A.3
- Spec sentence-level hallucination check: every sentence in modified Phase 3.3 satisfies (a) mechanically true / (b) verifiable now / (c) explicit forward ref
- instruction-author + claude-code-guide dual-verify (per memory rule `feedback_dual_agent_verify_command_statements`)
- Cross-check: any spec section referencing tree-description format updated to point at annotation schema

### Step A.4 — Post-batch verification queries

Add to `src/devforge/lib/generate_docs_helper.py`:
- `verify-annotations --concern C` returns aggregate report:
  - Banned-phrase count (should be 0 — validator should have caught all)
  - Identical-label-sibling count
  - Confidence distribution: % extracted / % inferred / % ambiguous
  - Cross-concern identical-label pairs (same label, disjoint parent paths)
  - Missing-cite count
- Exit 0 if all gates pass; exit 2 with summary otherwise

Gates (config in helper):
- Banned phrase: 0 tolerated
- `ambiguous` rate: ≤10% (else bad batch)
- Cross-concern identical labels: ≤5% (else over-generalization)
- Vacuous pass: concern with non-empty `directory_tree` AND zero registered annotations → fail (added 2026-05-06 after empirical run on testForge20 showed orchestrator skipping the annotation loop entirely; helper-owns-the-contract: spec prose can't enforce loop bounds)

`/generate-docs` spec calls `verify-annotations` after each concern completes. Fail → halt with message; user decides re-run vs proceed.

#### Verify A.4
- Verification helper passes own unit test (synthetic state with known violations → correct counts)
- Spec calls helper at correct phase boundary
- Exit-on-fail wired into circuit-breaker pattern (counts toward invocation budget)

### Step A.5 — Empirical floor on testForge20

Per Obsidian note: 1 node type, 1 small package, 50 entries, full pipeline, read 10 random outputs.

Target: testForge20 `db-cse-ui-strata/apps/app-web` components/ concern. Sample 50 of 597 entries (uniform random with seed=42 for reproducibility).

Procedure:
1. Reset state for components concern only (preserve other concerns from paused Run 3)
2. Run /generate-docs Phase 3 components concern with validator loop ON
3. Record per-entry: attempts before pass, final confidence tag, banned-phrase hits, cite resolves
4. Read 10 random annotations as user
5. Pass criteria:
   - 0 banned phrases in committed output
   - ≥80% `extracted` confidence
   - ≤10% `ambiguous`
   - 10 reads = "human engineer wrote this" verdict on ≥8 of 10
6. Fail criteria:
   - Any banned phrase in committed output (validator broke)
   - >20% `ambiguous` (annotator too weak even for Haiku — escalate Sonnet default OR strengthen prompt)
   - <6 of 10 reads pass user judgment (prompt design needs work)

#### Verify A.5
- Aggregate report committed alongside testForge20 state
- Pass → unlock Part B as canonical implementation
- Fail → iterate prompt (NOT loop); document failure mode; if 3 prompt iterations don't fix → retreat to Step 3.3.5 hint-only

---

## Part B — Graph native (`CODEGRAPH-INTEGRATION-PLAN.md` Phase B addendum)

Goal: validator loop natively in SurrealDB stack. Phase B already plans helper API; this expands it with annotation schema + validator queries.

### Step B.1 — SurrealDB annotation schema

Extend Phase B.1 schema with Annotation node:

```surrealql
DEFINE TABLE Annotation SCHEMAFULL;
DEFINE FIELD label ON Annotation TYPE string ASSERT $value != NONE;
DEFINE FIELD target ON Annotation TYPE record<File | Symbol | Concern>;
DEFINE FIELD confidence ON Annotation TYPE string
  ASSERT $value IN ['extracted', 'inferred', 'ambiguous'];
DEFINE FIELD evidence_file ON Annotation TYPE string;
DEFINE FIELD evidence_start ON Annotation TYPE int;
DEFINE FIELD evidence_end ON Annotation TYPE int;
DEFINE FIELD model_version ON Annotation TYPE string;
DEFINE FIELD content_hash ON Annotation TYPE string;
DEFINE FIELD created_at ON Annotation TYPE datetime DEFAULT time::now();

DEFINE INDEX label_text ON Annotation FIELDS label SEARCH ANALYZER ascii;
DEFINE INDEX target_idx ON Annotation FIELDS target;
DEFINE INDEX confidence_idx ON Annotation FIELDS confidence;
```

Edges: `Annotation → AnnotatesNode → (File|Symbol|Concern)` already covered by `target` record link.

### Step B.2 — Validator as SurrealQL queries

Validator becomes named stored procedures (functions in SurrealQL):

**Banned-phrase regex**:
```surrealql
DEFINE FUNCTION fn::has_banned_phrase($label: string) {
    RETURN $label ~ "(handles|manages|processes|validates|various|etc|responsible for)";
};
```

**Identical-label specificity check** (siblings = same parent concern):
```surrealql
DEFINE FUNCTION fn::label_collides_with_sibling($annotation: record<Annotation>) {
    LET $parent = (SELECT ->ConcernContains<-Concern AS p FROM $annotation.target)[0].p;
    LET $siblings = (SELECT id FROM Annotation WHERE
        target IN (SELECT ->ConcernContains->File FROM $parent)
        AND label = $annotation.label
        AND id != $annotation.id);
    RETURN array::len($siblings) > 0;
};
```

**Cite resolution**: helper-side check (read file content, slice [start:end], sha256, compare to `content_hash`).

**Aggregate verification queries**:
```surrealql
-- topics covering >N% of nodes
SELECT label, count() AS n FROM Annotation GROUP BY label
  ORDER BY n DESC LIMIT 20;

-- identical text across disjoint call graphs
SELECT a.label, count() AS n FROM Annotation AS a
  GROUP BY a.label HAVING count() > 5;

-- confidence distribution
SELECT confidence, count() AS n FROM Annotation GROUP BY confidence;

-- missing cite (content_hash mismatch)
-- run helper-side; can't recompute file hashes inside SurrealQL
```

#### Verify B.2
- Each function definition passes SurrealDB syntax check
- Round-trip test: insert known-bad annotation → validator query returns true positive
- Round-trip test: insert known-good annotation → validator query returns true negative

### Step B.3 — Python helper orchestration

`graph_helper.py` (Phase B.2 expansion):
- `propose-annotation --target T --label L --confidence K --cite-file F --cite-start S --cite-end E --model M`
  - Computes `content_hash = sha256(file[S:E])`
  - INSERT Annotation
  - Returns annotation id
- `validate-annotation --id I` runs all four checks (banned-phrase fn, sibling fn, cite hash, schema). Returns exit 0 / 2-5 same as Part A.
- `verify-batch --concern C` runs aggregate queries; returns same pass/fail report shape as Part A.

Retry orchestration in slash-command spec layer (same as Part A.3 — fresh per-call agent dispatch, validator feedback verbatim, escalate to Sonnet at attempt 3).

Content-hash cache: before propose, check `SELECT FROM Annotation WHERE content_hash = $hash AND target = $target`; if hit AND `model_version` matches current, return cached. Skip annotator call.

#### Verify B.3
- Helper test: cache hit on identical content_hash skips LLM call (mock annotator, assert not called)
- Helper test: model-version bump invalidates cache
- Helper test: retry-loop wiring matches spec (4th attempt = Sonnet escalation)

### Step B.4 — Verification queries as named procedures

Promotion gate: `verify-batch --concern C` must return clean before annotation set is exposed to `/research` MCP queries. Build flag: `Annotation.queryable: bool` (false until batch verifies).

`/research` MCP tools filter `WHERE queryable = true`. Failed-batch annotations remain in graph for debugging but invisible to user-facing queries.

#### Verify B.4
- MCP query filter test: failed-batch annotations don't surface
- Promotion test: passing batch flips `queryable = true`

### Step B.5 — Empirical floor on testForge20 (graph)

Same protocol as A.5 but graph backend:
- testForge20 components concern, 50 sampled entries
- Annotator: Haiku, parallel 50-way dispatch, temperature=0
- Validator: SurrealQL stored functions
- Read 10 random annotations
- Same pass/fail criteria as A.5

Comparison metrics A vs B:
- Wall-clock build time
- Token cost
- `extracted` confidence rate
- 10-read user judgment

Decision: if graph (B) ≥ markdown (A) on all four → graph promoted to canonical (per CODEGRAPH-INTEGRATION-PLAN.md promotion criterion).

#### Verify B.5
- Aggregate comparison report committed
- A vs B side-by-side on the same 10 sampled entries

---

## Cross-cutting

### Banned-phrase list (single source)

`src/devforge/lib/_banned_phrases.py` — used by both Part A markdown helper AND Part B graph helper. Avoid drift.

### Confidence semantics (locked)

| Tag | Meaning |
|---|---|
| `extracted` | Literally in code: identifier name, type signature, exported symbol, comment text. Cite line range contains the literal label words. |
| `inferred` | Derived from naming or structure: filename + folder context + import patterns. Cite line range supports inference but doesn't contain literal words. |
| `ambiguous` | Annotator + validator unsure after retry exhaustion. Tagged for filtering, never silently dropped. |

### Sibling definition (locked)

For tree-entry annotations: siblings = entries under same parent path in concern tree.
For symbol annotations (graph): siblings = symbols in same File OR functions calling same parent.

### Empirical-floor halt rule (note's protocol)

After Step A.5 OR B.5: read 10 random outputs. If ANY banned phrase appears in committed output, validator broke — halt scaling, fix validator, re-run. Do NOT scale to 597 entries until 50-entry sample passes clean.

### Coordination with primary-track Step 3.3.5

Step 3.3.5 ("tree descriptions = hints, not docs") in `GENERATE-DOCS-PLAN.md` is the *fallback* if validator loop fails. If Part A.5 passes, Step 3.3.5 retreats further: tree descriptions stay semantic, contract-declared as validated annotations, not hints.

If Part A.5 fails after prompt iteration: Step 3.3.5 stays as written.

---

## When resuming work

1. Read `CLAUDE.md`, `SESSION-HANDOFF.md`, `GENERATE-DOCS-PLAN.md` Steps 3.3.4-3.3.7.
2. Read this file (`VALIDATOR-LOOP-PLAN.md`).
3. Read Obsidian note `20 Projects/AIDevTeamForge/rewritePlans/LLM-augmented knowledge graph - architecture and generalization controls.md` for full diagnosis.
4. Determine current step:
   - Part A not started → Step A.1 (annotation schema + helper API).
   - Part A.5 in progress → check `testForge20/.devforge/.generate-docs-state.json` for components-concern annotations.
   - Part A complete → Part B starts after codegraph-rust fork stable (parallel-track Phase A done).

## Files NOT to delete

- `VALIDATOR-LOOP-PLAN.md` — this file
- `src/devforge/lib/_banned_phrases.py` — single source for banned list (when created)
- `tests/lib/test_add_annotation.py`, `tests/lib/test_validate_annotation.py`, `tests/lib/test_verify_annotations.py` — empirical-floor test harness
- `testForge20/.devforge/.generate-docs-state.json` — preserved across runs

## References

- Obsidian: `20 Projects/AIDevTeamForge/rewritePlans/LLM-augmented knowledge graph - architecture and generalization controls.md`
- `GENERATE-DOCS-PLAN.md` — primary track plan
- `CODEGRAPH-INTEGRATION-PLAN.md` — parallel track plan (Phase B is where Part B integrates)
- `SESSION-HANDOFF.md` — session 2026-05-02 state
- Memory rules: `feedback_helper_owns_shape_principle.md`, `feedback_test_first_python_helpers.md`, `feedback_dual_agent_verify_command_statements.md`, `feedback_iterative_review_loop_preferred.md`, `feedback_zero_escape_hatch_policy.md`
