# Step A.5 — Empirical Floor Launch Protocol

**Purpose**: Run `/generate-docs` against testForge20 components/ concern with the validator loop ON. Measure pass/fail per `VALIDATOR-LOOP-PLAN.md` Step A.5 criteria.

**Status**: Steps A.1–A.4 landed on `develop-2.0-init`. 823 tests pass. Validator loop ready.

**Why this run is the gate**: Run 4 (2026-05-01, pre-validator-loop) produced 597 tree descriptions with LLM honest breakdown 5% verified / 25% hand-mapped / **70% regex camelCase filename echo**. A.5 tests whether the validator loop fixes the failure mode. Pass → loop is the right tool; promotion path opens. Fail → iterate prompt OR retreat to Step 3.3.5 hint-only.

---

## Pre-flight checklist

### 1. Branch state

- Current branch: `develop-2.0-init`
- Recent commits up to and including Step A.4 fix-pass present
- 823 tests pass: `python3 -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3`

### 2. testForge20 location + state

- Path: `/Users/mykolakudlyk/Projects/testForge20`
- State: `.devforge/.generate-docs-state.json` (118.8K — Run 3 paused state preserved)
- Index: `.devforge/index.json` (240K)
- Components concern: `db-cse-ui-strata/apps/app-web/src/components/` (597 entries from Run 3)

### 3. DevForge sync

testForge20's `.devforge/lib/` and `.claude/` need the Step A.1–A.4 changes synced. Two options:

- **Option (a) — fresh install**: from testForge20 root, run the framework's install/update script that copies `src/devforge/lib/*.py`, `src/agents/tree-annotator.md`, `src/commands/generate-docs/main.md`, and helper modules into testForge20.
- **Option (b) — manual symlink**: if testForge20 already symlinks DevForge's `src/devforge/lib/` directly, the Step A.1–A.4 changes are live without sync. Verify by running `testForge20/.devforge/lib/generate_docs_helper add-annotation --help` and confirming the subcommand exists.

The sync mechanism is your choice; the gate is: `add-annotation`, `validate-annotation`, `verify-annotations` must be invokable from testForge20's helper, AND `tree-annotator.md` must be present at `testForge20/.claude/agents/tree-annotator.md`.

### 4. Reset components concern only (preserve other concerns from Run 3)

The new validator loop adds annotations alongside the existing `set-concern-tree` text. Run 3's components concern has `directory_tree` populated with the 597-entry text but ZERO annotations (annotations didn't exist in Run 3). Two paths:

- **Path (a) — keep existing tree text**: skip `set-concern-tree` in the new run; only run the per-tree-entry annotation loop on the 597 entries. Faster; reuses existing tree text.
- **Path (b) — fresh components**: reset just the components concern's annotations dict (preserve overview, tree, exports, deps, hazards, usage_example) and run the annotation loop. Same outcome as (a) since the loop reads entries from `index.json`, not from the tree text.

Recommend (a) — minimal touch, no state mutation needed pre-run.

---

## Run protocol

### A. Open a fresh Claude Code session in testForge20

```
cd /Users/mykolakudlyk/Projects/testForge20
claude
```

A fresh session ensures the orchestrator picks up the synced agent + helper changes. The orchestrator's default model is whatever your Claude Code config sets (likely Opus 4.7 or Sonnet 4.6); this is fine — the `tree-annotator` subagent dispatch overrides to Haiku per its `model_tier: scan` frontmatter.

### B. Invoke /generate-docs

```
/generate-docs
```

Phase 0 will detect Run 3's paused state. Choose **Resume** (preserves Run 3's tree text + concern records; the new annotation loop runs alongside as Step A.3 wired).

Phase 3 will iterate concerns. Components concern is the target. The new per-tree-entry annotation loop dispatches `tree-annotator` per entry, runs `add-annotation` + `validate-annotation`, retries verbatim feedback, escalates Sonnet, falls back to `ambiguous`.

After components completes, the spec invokes `verify-annotations --package db-cse-ui-strata/apps/app-web --concern components`. Three exit codes:

- **Exit 0** — all gates pass. Continue to remaining concerns OR halt manually if you only need components data.
- **Exit 2** — gate fail. JSON report shown verbatim. Decide: re-run loop, edit thresholds, accept failure.
- **Exit 5** — state error. Concern aborted; record in outcome `errors`.

### C. Cost + wall-clock budget

- 597 entries × up-to-3 Haiku attempts each ≈ 1800 Task calls in worst case
- Haiku @ ~$0.005/call → ~$5–10 cost ceiling
- Wall-clock estimate: 25–45 min depending on retry rate + parallelism
- Budget: set a hard cap of $20 + 60 min wall-clock; abort if exceeded

### D. Capture metrics during the run

Record (eyeball or paste from terminal output):

- Total entries iterated
- Total `tree-annotator` dispatches (= attempts including retries)
- Distribution of attempts per entry (1, 2, 3, escalated)
- Number of entries where `validate-annotation` exited 0 on first try
- Number of entries where Sonnet escalation fired
- Number of entries tagged `confidence=ambiguous` after fallback
- `verify-annotations` final report (JSON) — full content

---

## Measurement protocol

### 10-read user judgment

After the run:

1. Pick 10 random `target_path` values from `state["packages"][".../app-web"]["concerns"]["components"]["annotations"]`. Use `python3 -c 'import json,random; r=random.Random(42); ann=json.load(open(".devforge/.generate-docs-state.json"))["packages"]["db-cse-ui-strata/apps/app-web"]["concerns"]["components"]["annotations"]; print("\n".join(r.sample(list(ann.keys()), 10)))'` for reproducibility.

2. For each of the 10:
   - Read the annotation record (`label`, `confidence`, cite range)
   - Read the cite-file at the cite range
   - Read the `target_path` itself if the cite is in a different file
   - Judge: does the label read like a human engineer wrote it? Specific, evidence-backed, vs-siblings differentiated, not archetype filler?

3. Score each as **PASS** or **FAIL** (binary). Optional one-line note per entry.

### Computed metrics from `verify-annotations` JSON

- `confidence_distribution.extracted / total_annotations` → extracted rate
- `confidence_distribution.inferred / total_annotations` → inferred rate
- `confidence_distribution.ambiguous / total_annotations` → ambiguous rate (= `ambiguous_rate` field)
- `banned_phrase_count` — should be 0
- `cross_concern_duplicate_rate` — gate threshold 5%
- `sibling_collision_count` — diagnostic
- `missing_cite_count` — diagnostic

---

## Pass / fail criteria

### PASS (validator loop is the right tool — promotion path opens)

All four conditions must hold:

1. `banned_phrase_count == 0` in committed annotations
2. `extracted` rate ≥ 80%
3. `ambiguous` rate ≤ 10%
4. 10-read user judgment: ≥8 of 10 PASS

### CONDITIONAL PASS (iterate prompt, re-run)

- Banned phrases = 0
- Extracted rate ≥ 60% but < 80%
- Ambiguous rate 10-20%
- 10-read judgment 6-7 of 10 PASS

→ Iterate `tree-annotator.md` rules (most likely #4 specificity, #5 vs-siblings, or #7 negative-space) and re-run on a fresh sample of 10.

### FAIL (validator loop did not fix the failure mode)

Any of:

- `banned_phrase_count > 0` in committed output (validator broke OR annotator gamed the regex)
- `ambiguous` rate > 20%
- 10-read judgment < 6 of 10 PASS

→ Two paths:

- (a) Iterate `tree-annotator.md` prompt up to 3 times. If still failing, retreat to `GENERATE-DOCS-PLAN.md` Step 3.3.5 hint-only contract for tree descriptions.
- (b) Architectural retreat — Step 3.3.7 (per-file docs) or codegraph parallel track promotion.

---

## After the run — record results

Update `VALIDATOR-LOOP-PLAN.md` with a new section `## Step A.5 results (executed YYYY-MM-DD)`:

- Total annotations committed
- Aggregate metrics (extracted / inferred / ambiguous rates, banned count, cross-concern rate)
- 10-read judgment: PASS/FAIL count + brief notes
- Verdict: PASS / CONDITIONAL PASS / FAIL
- Next action per verdict

If **PASS**: open promotion to make validator loop default for `/generate-docs`. Step 3.3.5 retreat from the primary plan can be archived (validator-loop replaces it).

If **CONDITIONAL PASS**: prompt-iteration scope captured in plan; re-run is a new mini-step.

If **FAIL**: which retreat path was taken + rationale.

---

## When resuming (if interrupted mid-run)

testForge20's state JSON is preserved across runs. Re-invoke `/generate-docs` → Phase 0 detects in-progress + offers Resume. The annotation loop's per-entry idempotence (overwrite semantics on `add-annotation`) means re-running is safe — entries already validated stay; in-progress entries re-trigger.

Per-concern abort discipline still applies: if components fails irrecoverably, capture the wall in `errors` and move to the next concern (or halt at user discretion).

---

## Files NOT to delete during the run

- `testForge20/.devforge/.generate-docs-state.json` — primary state; do NOT manually edit
- `testForge20/docs/db-cse-ui-strata/apps/app-web/index.md.skeleton` — render artifact; preserved across resumes
- This file (`VALIDATOR-LOOP-A5-LAUNCH.md`)
- `VALIDATOR-LOOP-PLAN.md` — load-bearing for resumption
