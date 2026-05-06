# Validator-Loop Plan — Part B (per-file `.md` docs)

**Status**: Draft, not started. Successor architecture to Part A's annotations-in-state model.
**Branch**: continues on `develop-2.0-init`.
**Predecessor**: `VALIDATOR-LOOP-PLAN.md` (Part A, Steps A.1–A.5). Empirical run on testForge20 surfaced three-layer bypass: orchestrator skipped annotation loop + verify-annotations + coverage gate. Fix D (validate-concern enforcement) closed the verify-annotations bypass post-run. Architectural follow-up: filesystem becomes the forcing function.

## Why Part B

Part A architecture: tree text + annotations dict in `.devforge/.generate-docs-state.json`. Render emits ONE concern `index.md` per concern. Annotations were "additive metadata" — orchestrator could skip the loop, validate-concern still passed (until Fix D), and per-tree-entry quality stayed unenforced.

Part B architecture: filesystem mirrors source tree. One `.md` per source file at `docs/<package>/<concern>/<rel-path>/<file>.md`. validate-concern walks the docs tree, fails if any expected `.md` is missing or empty. Orchestrator MUST fill each `.md` (or fail visibly) — no spec-prose bypass possible.

**Locked decisions (2026-05-06):**
1. **Replace, not coexist** — `state["packages"][P]["concerns"][C]["annotations"]` dict is removed in Step B.5. Per-file `.md` is the single source of truth.
2. **File-level granularity** — one `.md` per non-trivial source file (skip-rule exemptions per existing trivial-leaf + canonical-aggregator lists).
3. **Incremental fill content** — Step B starts with label + evidence cite + confidence per `.md` (port annotation record shape). Richer content (per-file overview, local hazards, public-surface) = future iteration.
4. **Skeleton tool = helper command** — `render-file-skeletons` stays in /generate-docs scope; not an `init-forge` extension.
5. **Existing Part A helpers KEPT as building blocks** — `add-annotation` / `validate-annotation` / `verify-annotations` / `tree-annotator.md` adapt to per-md flow rather than retire.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│ /generate-docs Phase 3 step 10 (per-concern slot-fill)   │
└─────────────────────────────┬────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  B.1 render-file-     B.3 per-md fill      B.5 validate-
  skeletons             dispatch             concern gate
  (empty .md per       (tree-annotator      (file-docs-
  source file under    Task subagent per    incomplete rule;
  subfolder)           md, writes content)  walks docs tree,
                                            asserts each
                       B.4 validate-        expected .md
                       file-doc per-md      present + non-
                       (refactored from     empty + validated)
                       validate-annotation)
```

The filesystem IS the contract. Orchestrator can't skip a loop the helper traverses on validate.

## Coordination with parallel codegraph track

Per the 2026-05-06 codegraph state-of-the-world update (nodes empty + edges dangling + Vue cite-back unverified + Phase B.1 schema gap), codegraph parallel track is NOT ready to replace markdown storage. Per-file `.md` becomes the canonical doc structure; codegraph (when fixed + Phase B.1 lands) AUGMENTS by feeding mechanical fields (tree section, exports, import deps) INTO per-file md. Verbatim citation contract preserved (filesystem-based extract-snippet). Promotion of codegraph from augment to replacement remains gated on CODEGRAPH-INTEGRATION-PLAN §"Success criteria".

---

## Step B.1 — `render-file-skeletons` helper

Goal: helper command walks the concern's source subfolder via `index.json`, produces an empty `.md` at the corresponding `docs/.../` path for each non-trivial source file. Skip-rule exemptions apply (canonical aggregators stay as bare entries with empty md; trivial-leaf folders excluded entirely).

**CLI**:
```
generate_docs_helper render-file-skeletons --package P --concern C
```

**Behavior**:
1. Load index.json via `_load_index_files(devforge_dir, P)` (progressive-suffix match per Fix C).
2. Filter files by `subfolder_prefix = "src/{concern}/"`.
3. Apply trivial-leaf exclusion (`_path_contains_trivial_dir`).
4. For each remaining file, compute target path: `docs/<P>/<C>/<rel-path-after-subfolder>/<filename>.md`. Create parent dirs. Write empty `.md` if absent.
5. Idempotent: re-running on existing skeletons is a no-op (don't overwrite filled mds).
6. Stdout: count of skeletons created + count of pre-existing.
7. Exit 0 on success; exit 2 on package/concern not registered or index.json missing.

**Test scope**:
- Happy path: 10 source files → 10 empty `.md` files at expected paths.
- Trivial-leaf exclusion: source file under `node_modules/` → no `.md` created.
- Idempotency: second invocation preserves existing filled mds + creates only new skeletons.
- Path mismatch: package not in index.json → exit 2 with clear message.
- Concern subfolder empty: zero source files → zero skeletons + warn.

#### Verify B.1
- `tests/lib/test_render_file_skeletons.py` — all paths above
- Helper test passes own unit test
- Cross-check: `_load_index_files` reuse confirmed (no duplicate logic)

---

## Step B.2 — `validate-concern` enforces `file-docs-incomplete`

Goal: extend `validate_concern` with a new rule that walks the expected `.md` set + fails if any are missing or empty. Mandatory gate — orchestrator can't skip validate-concern before render-concern-doc.

**New rule**: `file-docs-incomplete`
- Compute expected set: same logic as B.1's enumeration (index.json + subfolder filter + skip rules).
- For each expected path: assert (a) `.md` exists on disk, (b) file size > N bytes (configurable threshold, default 50 bytes — empty/whitespace-only fails).
- Aggregate missing + empty into single error rule with stderr summary listing first 5 offenders + total count.
- Exit 2 from `cmd_validate_concern` if rule fires (existing exit logic).

**Replaces**: `_check_concern_annotations_completeness` from Fix D (annotations-missing rule). New rule fires on a strictly more meaningful condition (filesystem evidence vs state dict).

**Tests**:
- All expected mds present + non-empty → rule passes.
- One md missing → rule fails, error names path.
- One md empty (whitespace only) → rule fails.
- Concern with empty subfolder → rule passes vacuously (no expected mds).
- Legacy concern without skeletons run → rule fails with "no skeletons rendered" guidance.

#### Verify B.2
- Existing 885 tests still pass (after `_check_concern_annotations_completeness` retirement)
- New 5 tests in `tests/lib/test_validate_concern_file_docs.py`

---

## Step B.3 — per-md fill dispatch + validation

Goal: spec change in `src/commands/generate-docs/main.md` Phase 3 step 10 — replace the per-tree-entry annotation loop with per-md fill loop. Adapt existing `tree-annotator.md` to write `.md` content instead of returning JSON.

**Per-md fill flow**:
1. After `render-file-skeletons` produces skeletons, orchestrator iterates the empty `.md` files.
2. For each empty `.md`: dispatch `tree-annotator` Task subagent. Input: `target_source_path`, `target_md_path`, `concern`, `siblings` (peer mds in same parent dir), `previous_attempt_feedback` on retry.
3. Subagent reads source, composes per-file md content (label, evidence cite, confidence — incremental shape), writes to `target_md_path` directly (Write tool).
4. Orchestrator invokes `validate-file-doc --md-path <path>` (refactored from `validate-annotation`).
5. On exit 0 → next md. On non-zero → capture stderr verbatim, retry up to 3 times. Sonnet escalation once. `confidence: ambiguous` fallback for irrecoverable.
6. After all mds in concern processed → orchestrator invokes `validate-concern` (B.2 rule fires if any md still missing/empty).

**`validate-file-doc` CLI** (refactored from `validate-annotation`):
```
generate_docs_helper validate-file-doc --md-path <path>
```
Same 6 exit codes as Step A.2: schema (5), banned (2), cite (3), specificity-vs-siblings (4), binary cite-file (6), 0 pass.
Reads `.md` content, parses front-matter or structured sections (locked schema TBD in B.3 implementation), runs same checks.

**Per-md schema (locked v0)**: structured Markdown with fenced YAML front-matter:
```markdown
---
label: "<3-7 word description>"
confidence: extracted | inferred | ambiguous
evidence_file: "<relative path>"
evidence_start: <int>
evidence_end: <int>
content_hash: "<sha256 hex>"
model_version: "<haiku | sonnet | opus>"
---

# <filename>

<optional prose section — left empty in v0; future iteration adds overview / public-surface / hazards>
```

#### Verify B.3
- `tests/lib/test_validate_file_doc.py` — all 6 exit codes covered
- Spec change in main.md verified by instruction-reviewer + claude-code-guide
- Existing `tree-annotator.md` adapted (Read + Write tools allowlist, output contract changes from JSON return to `.md` write)

---

## Step B.4 — `verify-file-docs` post-batch aggregator

Goal: refactor existing `verify-annotations` (Step A.4) to operate over per-md set instead of state's annotations dict. Same 4 gates: banned-phrase / ambiguous-rate / cross-concern duplicate / vacuous-pass (now: tree set but zero non-empty mds).

**CLI**:
```
generate_docs_helper verify-file-docs --package P --concern C
```

**Aggregation**: walks `docs/<P>/<C>/` tree, parses each `.md`'s front-matter, computes same metrics + gate results. JSON report shape mirrors Step A.4's `verify-annotations` (renamed fields where appropriate: `total_md_files` instead of `total_annotations`, etc.).

**Spec wiring**: orchestrator invokes after per-md fill loop completes; same 3-exit handling as A.4 (0 pass, 2 gate fail with halt + verbatim report, 5 state error).

#### Verify B.4
- `tests/lib/test_verify_file_docs.py` — same 17 cases as A.4 plus per-md path-existence checks

---

## Step B.5 — deprecate annotations-in-state

Goal: remove `state["packages"][P]["concerns"][C]["annotations"]` field. Migrate `_check_concern_annotations` (schema validation) to per-md schema check. Drop `add-annotation` / `validate-annotation` / `verify-annotations` CLI subcommands (helpers stay as internal building blocks for B.3/B.4 implementations).

**Removals**:
- `default_concern_record` no longer initializes `"annotations": {}`
- `_check_concern_annotations` deleted (replaced by per-md `_check_file_doc_schema`)
- `_check_concern_annotations_completeness` (Fix D) deleted (replaced by B.2's `file-docs-incomplete`)
- CLI subcommands `add-annotation`, `validate-annotation`, `verify-annotations` removed from `_cli.py` registry. Internal functions kept for B.3/B.4 reuse.

**Migration**: testForge20's existing state JSON has `annotations: {}` per concern (empty). Loading legacy state ignores the dict; B.5's removal of the validator path means no error fires. Re-run regenerates `.md` files; state's `annotations` field becomes vestigial and is dropped on next state write (via `default_concern_record` no longer including it).

#### Verify B.5
- All Part A tests removed/adapted (Steps A.1–A.4 test files migrate to per-md equivalents OR retire)
- Total test count adjusts (target: ~870, drop A.4's 22 + A.5's vacuous tests + A.1/A.2/A.3 superseded; gain B.1–B.4 coverage)
- `validate-concern` legacy test for `annotations-missing` rule replaced by `file-docs-incomplete` test

---

## Step B.6 — empirical floor on testForge20

Goal: re-run `/generate-docs` against testForge20 with Part B architecture. Confirm three-layer bypass closed (skeletons forced, fill enforced, gate fires).

**Procedure**:
1. Reset testForge20 state (full).
2. `update.sh` syncs Part B helpers + spec.
3. Fresh `/generate-docs` run. Phase 3 invokes `render-file-skeletons` per concern → empty mds created on disk → orchestrator iterates fill loop → validator runs per-md → `verify-file-docs` post-batch → `validate-concern` gate.
4. Capture metrics:
   - Total `.md` files created (per concern)
   - Per-md fill attempts (1 / 2 / 3 / Sonnet escalated)
   - Confidence distribution (extracted / inferred / ambiguous)
   - Banned-phrase hits / specificity collisions / hash drifts
   - Wall-clock + cost
5. Read 10 random `.md` files. User-judgment pass criteria same as A.5 plan: ≥80% extracted, ≤10% ambiguous, ≥8/10 reads PASS, 0 banned in committed output.

**Pass / fail criteria** identical to VALIDATOR-LOOP-PLAN.md Step A.5.

**Cost expectation**: testForge20 has ~500 source files across 7 concerns. Skip-rule reduces to ~300-400 expected mds. Per-md = 1-3 Haiku dispatches average → ~$5-15 cost ceiling, ~30-60 min wall-clock.

#### Verify B.6
- Aggregate report committed alongside testForge20 state
- Verdict per A.5 criteria
- If PASS → Part B is canonical; archive Part A as historical
- If FAIL → diagnose (prompt iteration vs architecture)

---

## Disposition of Part A artifacts

| Artifact | B disposition |
|---|---|
| `_setters_annotation.py:cmd_add_annotation` | Internal `_write_md_with_frontmatter()` helper for B.3 |
| `_validators_annotation.py:cmd_validate_annotation` | Refactor → `cmd_validate_file_doc` |
| `_validators_annotation.py:cmd_verify_annotations` | Refactor → `cmd_verify_file_docs` |
| `tree-annotator.md` agent | Adapted: Write tool added; output contract = write `.md` directly |
| `_banned_phrases.py` | KEEP as canonical source |
| `_setters_concern.py:_check_tree_entry_coverage` | KEEP — set-concern-tree still emits tree text alongside per-md docs |
| Annotations dict in state | REMOVED (B.5) |
| `validate-concern` rule `annotations-missing` | REPLACED by `file-docs-incomplete` (B.2) |
| Step A.5 testForge20 launch protocol (`VALIDATOR-LOOP-A5-LAUNCH.md`) | OBSOLETE; B.6 supersedes |

## Risks + open questions

1. **Per-md schema parsing brittleness** — YAML front-matter parsing without a YAML dep (stdlib only). Use simple line-based parser bounded by `---` markers; reject malformed front-matter as schema-invalid (exit 5). Risk: minor variations in author whitespace/quoting break parser. Mitigation: helper writes front-matter (subagent uses Write tool but spec mandates a fixed template); LLM doesn't author front-matter freehand.

2. **Filesystem race conditions** — multiple concurrent `add-md` writes? Not expected in single-orchestrator flow but unlocked if /generate-docs ever parallelizes. Defer to "single concurrent writer" assumption.

3. **`docs/.../` directory pollution** — orphaned mds when source files are renamed/deleted. B.5+ should add `prune-orphan-md-files` helper or mark orphaned mds for deletion. Defer to post-B empirical observation.

4. **Vue file extension** — source is `Login.vue`; doc is `Login.vue.md`. Acceptable filename pattern. Confirm no path-component collisions (e.g., a directory named `Login.vue` somewhere) — index.json check should catch.

5. **Codegraph augment integration** — Step B specifies markdown-only flow. Codegraph mechanical augment (when ready, Phase C of CODEGRAPH-INTEGRATION-PLAN) feeds tree-section + exports-list into per-md content. Codegraph integration is out-of-scope for Step B; stays parallel.

6. **Token cost discipline** — every concern produces N md files where N = filtered source file count. testForge20 ≈ 300-400 mds. Other projects could hit 1000+ for a single concern. /generate-docs spec MUST surface cost estimate to user before kicking off Phase 3 step 10's fill loop. Add to B.3 spec change.

## When resuming work

1. Read `CLAUDE.md`, `VALIDATOR-LOOP-PLAN.md` (Part A history), this file (Part B plan).
2. Determine current step:
   - B.1 not started → start with `render-file-skeletons` helper.
   - B.6 in progress → check `testForge20/docs/` tree for partial mds.
3. Files NOT to delete:
   - `VALIDATOR-LOOP-B-PLAN.md` (this file)
   - `VALIDATOR-LOOP-PLAN.md` (Part A history)
   - `tree-annotator.md` (adapted in B.3, not retired)
   - `_banned_phrases.py` (canonical source)
4. Run full test suite at every step; baseline 885 (post-Fix-D).

## References

- `VALIDATOR-LOOP-PLAN.md` — Part A history (Steps A.1–A.5)
- `GENERATE-DOCS-PLAN.md` — primary plan (Step 3.3.5 hint-only is the retreat path if B.6 fails)
- `CODEGRAPH-INTEGRATION-PLAN.md` — parallel mechanical-augment track
- `src/commands/generate-docs/main.md` — Phase 3 step 10 is the spec change target in B.3
- Memory rules: `feedback_helper_owns_shape_principle.md`, `feedback_zero_escape_hatch_policy.md`, `feedback_iterative_review_loop_preferred.md`, `feedback_test_first_python_helpers.md`
