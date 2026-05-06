# Session handoff — 2026-05-06

Snapshot for fresh-session restart after `/clear`. Built validator-loop Part A (Steps A.1–A.4) + Fix A/B/C/D + render-fix; ran empirical testForge20 run; pivoted to per-file `.md` architecture (Part B) based on empirical signal + codegraph state-of-world update.

## Branch state

- **Branch**: `develop-2.0-init`
- **Working tree**: many uncommitted changes (Part A + fixes + Part B plan); user has NOT committed yet
- **Test count**: 885 passing (was 760 at session start; +125 this session)
- **Last committed SHA at session start**: `8ffb22c` (codegraph-integration parallel-track plan)

## What landed this session (uncommitted)

### Part A — annotations-in-state validator loop (Steps A.1–A.4 + fixes)

| Step | Outcome |
|---|---|
| A.1 | `add-annotation` setter + `_check_concern_annotations` validator + `tests/lib/test_add_annotation.py` (24 tests, 760→784) |
| A.2 | `validate-annotation` mechanical validator with 6 exit codes (schema/banned/cite/specificity/binary) + `_banned_phrases.py` + `tests/lib/test_validate_annotation.py` (21 tests, 784→805) |
| `_validators.py` split | 1193-line monolith → 5 files: `_validators_shared.py`, `_validators_package.py`, `_validators_concern.py`, `_validators_decomposition.py`, `_validators.py` (77-line shim, 0 defs) |
| A.3 | Per-tree-entry retry loop in `src/commands/generate-docs/main.md` Phase 3 step 10 + new `src/agents/tree-annotator.md` (model_tier: scan = Haiku) + `scan` tier added to `install_defaults.py` |
| A.4 | `verify-annotations` post-batch aggregator with 4 hard gates (banned-phrase=0 / ambiguous-rate≤10% / cross-concern-duplicate≤5% / vacuous-pass) + `tests/lib/test_verify_annotations.py` (22 tests, 805→827; +Fix D split tests landed at 885 total) |

### Render bug fix (mid-session, user-reported)

`_render_concern_*` and `_render_package_*` for optional sections leaked LLM-targeted TODO into final docs. Added `mode="skeleton"` vs `mode="final"` parameter to render functions; `_FINAL_NONE = "_(none)_"` placeholder for empty optional sections in final mode. Skeleton render unchanged. 20 new tests.

### Fix series after empirical testForge20 run #1

| Fix | What | Module |
|---|---|---|
| **A** | `verify-annotations` adds `vacuous_pass` gate — concern with non-empty `directory_tree` AND zero annotations → exit 2 | `_validators_annotation.py` |
| **B** | `set-concern-tree --text` validates entry count vs `index.json` (threshold 80%, small-concern guard ≤5, graceful degradation on missing index) | `_setters_concern.py` (jumped to 828 lines — past 600 threshold; pending-split documented in plan + module docstring) |
| **C** | `_load_index_files` progressive-suffix path match (state's `db-cse-ui-strata/apps/app-web` vs index's `apps/app-web`) | `_setters_concern.py` |
| **D** | `validate-concern` adds `annotations-missing` rule — bypass-proof escalation of vacuous_pass to mandatory gate | `_validators_concern.py` |

## Empirical testForge20 runs (2 attempts)

**Run 1** (post-Part-A, pre-Fix): 7 concerns processed, 36 min wall-clock. **Three-layer bypass observed**:
1. Annotation retry loop entirely skipped — orchestrator cited "100+ subagent dispatches across seven concerns"
2. `verify-annotations` never invoked (vacuous_pass gate live but only fires when called)
3. Components tree depth-1 only (23 of 597 expected entries — 4% coverage); `set-concern-tree` accepted because no entry-count check existed

**Run 2** (post-Fix-A/B/C/D not synced; user ran with 597-entry tree from a Python skeleton script): 7 concerns ok, 27 min wall-clock. Annotation loop STILL skipped (verify-annotations never invoked). Coverage check skipped (Fix C not synced; path mismatch silently degraded). Confirmed: helper-owns-contract requires the helper to be on a code path orchestrator MUST traverse → Fix D wired vacuous_pass into validate-concern.

**Verdict**: Part A architecture has structural bypass risk even with all gates. Filesystem forcing function (Part B) is the next architectural layer.

## Codegraph state-of-world update (user-pasted from another session)

- SurrealDB up at `ws://localhost:3004` ns=ouroboros db=codegraph
- `app-web-js/apps/app-web` claims 5345 nodes, 6697 edges, 388 files
- **CRITICAL BROKEN STATE**: `nodes` table EMPTY (0 rows), `edges` table 4891 dangling (point at non-existent node IDs), `chunks` EMPTY. `file_metadata` 390 OK.
- Root cause: codegraph binary missing `ai-enhanced` feature; embedding pipeline failure drops node persistence silently
- Re-install path: `bash /Users/mykolakudlyk/Projects/private/codegraph-rust-smap/install-codegraph-full-features.sh`
- Vue cite-back risk: `tools/vue-to-ts` produces `.vue.ts` outputs; if no source maps, citations point at generated file not original `.vue` — breaks verbatim citation contract
- Schema gap vs `generate_docs_schema.py`: codegraph has nodes/edges/chunks/file_metadata; PackageDoc / ConcernDoc / Hazard / Architecture types NOT present, need Phase B.1 schema extension per CODEGRAPH-INTEGRATION-PLAN

**Decision**: codegraph is NOT ready for wholesale replacement. Promoted to MECHANICAL AUGMENT role (when fixed). Per-file md (Part B) becomes source-of-truth structure that codegraph augments later.

## Active plan: Part B (per-file `.md` docs)

`VALIDATOR-LOOP-B-PLAN.md` written this session. 6 steps:

- **B.1** — `render-file-skeletons` helper: empty `.md` per non-trivial source file at `docs/<package>/<concern>/<rel-path>/<file>.md`
- **B.2** — `validate-concern` rule `file-docs-incomplete`: walks expected `.md` set, fails if missing/empty
- **B.3** — Per-md fill: `tree-annotator` adapted to write `.md` directly (not return JSON); `validate-file-doc` per-md validator (refactored from `validate-annotation`)
- **B.4** — `verify-file-docs` post-batch aggregator (refactored from `verify-annotations`)
- **B.5** — Deprecate annotations-in-state; remove `state[...]["annotations"]` dict; CLI subcommands removed (helpers stay as internal building blocks)
- **B.6** — Empirical floor on testForge20 (replaces deferred A.5)

5 design decisions locked (user approved 2026-05-06):
1. REPLACE annotations-in-state, not coexist
2. File-level granularity (not directory)
3. Incremental fill content (label + cite + confidence v0; richer iteration future)
4. Helper command `render-file-skeletons` (not `init-forge` extension)
5. Keep Part A helpers as building blocks, adapt to per-md flow

## State of testForge20

- Path: `/Users/mykolakudlyk/Projects/testForge20` (sibling to `ai-dev-team-forge`, NOT inside)
- State JSON: 7 concerns processed in Run 2; tree text populated; annotations dict empty (loop was skipped)
- index.json key: `apps/app-web` (NOT `db-cse-ui-strata/apps/app-web` — Fix C handles this mismatch)
- Final docs at `docs/db-cse-ui-strata/apps/app-web/<concern>/index.md` (Run 2 output, all 7 concerns ok)
- Render bug fix synced + applied — final docs no longer show LLM-targeted TODO prose for empty optional sections

## How to resume Part B

1. Read `CLAUDE.md`, `VALIDATOR-LOOP-PLAN.md` (Part A history), `VALIDATOR-LOOP-B-PLAN.md` (Part B plan), this file.
2. `git status` — many uncommitted changes; user may want to commit per-file before B starts. Suggest grouping: A.1/A.2/A.3/A.4 + split + render-fix + Fix-A/B/C/D as one commit; Part B plan as another.
3. `git log --oneline -5` (committed): last is `8ffb22c`. After commit, that pointer moves.
4. `python3 -m unittest discover -s tests -p "test_*.py"` — should be 885 OK.
5. **Decision before starting B**: commit current uncommitted changes first? User implied "preserve" so they want history before clearing session.
6. **Step B.1 first**: dispatch python-engineer to build `render-file-skeletons`.

## Codegraph track — parallel, deferred

CODEGRAPH-INTEGRATION-PLAN.md unchanged. Phase A.3 empirical validation NOT started. Blockers per user's update:
- (a) codegraph persistence broken; full-features re-install pending
- (b) Vue cite-back unverified (source map check needed in `tools/vue-to-ts` output)
- (c) Phase B.1 schema extension untouched (Concern / Hazard / UsageExample / PackageDoc tables)

Promotion criteria from `CODEGRAPH-INTEGRATION-PLAN.md` §"Success criteria" remain: Vue support stable (a), mechanical accuracy proven (b), methodology preserved, /research read cost ≥3× win measured, build wall-clock ≤30 min, newcomer test ≥4/5.

## Files NOT to delete

- `VALIDATOR-LOOP-PLAN.md` (Part A, frozen)
- `VALIDATOR-LOOP-B-PLAN.md` (Part B, active)
- `VALIDATOR-LOOP-A5-LAUNCH.md` (now obsolete; superseded by B.6 in Part B plan)
- `CODEGRAPH-INTEGRATION-PLAN.md` (parallel track)
- `GENERATE-DOCS-PLAN.md` (primary plan; Steps 3.3.4–3.3.7 still pending under iteration mode)
- `src/agents/tree-annotator.md` (adapted in B.3, not retired)
- `src/devforge/lib/_banned_phrases.py` (canonical banned-phrase source)
- `testForge20/.devforge/.generate-docs-state.json` (Run 2 state preserved; reset before B.6 run)

## Key architectural decisions to remember

1. **Helper-owns-contract is the only enforcement mechanism that survives orchestrator drift.** Spec prose can't enforce loop bounds (claude-code-guide Q3). Even helper gates only fire if invoked. Mandatory gates (validate-concern walking filesystem) close the bypass.

2. **Per-file `.md` is the right structure for /research's primary query shape.** 30-50× token reduction on focused queries. Established prior art (Sphinx, JSDoc, rustdoc, godoc).

3. **Codegraph is augment, not replacement.** Empirical state of codegraph (broken persistence + Vue cite-back gap + schema gap) means main track ships per-file md NOW; codegraph integrates Phase C (post-fix + Phase B.1 schema) feeding mechanical fields into per-file md.

4. **Annotations in state were a stepping stone.** Schema work (Steps A.1–A.4) ports to per-md schema in Part B. Validator loop primitives (banned-phrase, specificity, cite resolution) reused.

5. **Cost ceiling per concern run: $5-15 Haiku, 30-60 min wall-clock.** testForge20 ≈ 300-400 mds across 7 concerns. Other projects could hit 1000+ for one concern; spec must surface cost estimate before orchestrator kicks off fill loop.

## Rules / discipline applied this session (high-touch)

- `feedback_iterative_review_loop_preferred` — writer→reviewer→loop→user-approval after every step
- `feedback_helper_owns_shape_principle` — helper validates structure; LLM provides values
- `feedback_zero_escape_hatch_policy` — no opt-out flags on gates
- `feedback_test_first_python_helpers` — every Python function has test in same turn
- `feedback_dual_agent_verify_command_statements` — instruction-author + claude-code-guide on spec changes
- `feedback_avoid_subagents_for_sequential_identical_workflows` — orchestrator-direct for small mechanical edits, sub-agents for bounded scope
- `feedback_default_argue_engage_critically` — surfaced trade-offs on Part B decisions before draft

## Carry-over to next session

- User has not yet committed any of this session's work. Suggest commit grouping before /clear.
- Part B plan is approved (5 decisions locked). Ready to start Step B.1.
- testForge20 awaits Part B re-run for B.6 empirical floor.
- Codegraph parallel track stays parked; no action needed unless user prioritizes Phase A.3 validation.
