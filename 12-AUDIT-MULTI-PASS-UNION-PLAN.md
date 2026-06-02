# 12 — AUDIT MULTI-PASS UNION PLAN

**Status:** Steps 1–7 SHIPPED 2026-06-01 (working tree, NOT committed) on `develop-2.0-init`. Built via python-engineer→python-reviewer (`.py`) + instruction-author→instruction-reviewer (`main.md`/docs) loops. New module `_audit/_merge.py` (unified tolerant merger, 53 tests) + `--passes` flag (`_preflight`/`_cli`) + `merge-passes` verb (`_cli`) + `pass_count` schema/report/rank wiring + `render-report --passes-run` + main.md K-loop + docs propagation. ~840 `_audit` tests pass; full repo suite clean except pre-existing unrelated breakage (3 `doc_setters` collection errors + a 41-test `handoff_schema` cross-file test-isolation collision — both reproduce without any multi-pass involvement). **Step 8 (testForge20 e2e) PASSED 2026-06-02** — a clean fully-in-spec 2-pass run on the 29-file order dir: scope auto-resolved (29), both passes ran + pools survived, `Passes run: 2 | Multi-pass-confirmed: 45`, realistic severity (3 Critical), scratch in `$WORKDIR`, swept. **Post-validation fixes shipped (working tree):** (1) `_scope` nested-repo detection — `git ls-files -- <dir>` returns 0 for a nested independent git repo, so when empty it walks ancestors for a `.git` and runs `git -C <nested> ls-files`, prefixed (the first `--recurse-submodules` attempt was a non-fix: the dir is a nested repo, NOT a registered submodule); (2) **`_merge` no longer bumps severity** on cross-agent overlap — the `±3` location merge over-fired vs exact-match consensus (30 Critical → 3); the `[CROSS-AGENT]`/`[MULTI-PASS:k]` tags carry the signal; (3) all scratch relocated from `audits/.*` to a fixed `${TMPDIR:-/tmp}/forge-audit` workdir (an external reaper deletes dotfiles under `audits/` mid-run; the workdir is outside the repo) + `render-agent-brief --tmp-path` flag + single `rm -rf` cleanup; (4) **mode-conditional `--passes` default — SUPERSEDES Decision 1 below**: broad/hotspot default 2, narrow default 1, explicit `--passes N` (clamped `[1,3]`) overrides. (Decision 1's "opt-in, default 1, cannot be the default" no longer holds for broad/hotspot.) Plus the `_report` cross-agent Summary count now derives from `[CROSS-AGENT]` tags (was 0 in multi-pass). ~901 `_audit` tests pass. A pre-existing HIGH doc bug was also fixed: `main.md` wrongly called `resolve-scope`'s output key `scope_files`; the real key is `files` (verified `_scope.py:260`).

Builds on `11-AUDIT-FULL-SPECTRUM-PLAN.md` (SHIPPED, committed `6024169`). Adds an opt-in `--passes N` mode that runs the audit pipeline K times and unions the validated findings, pushing single-run observed-union coverage (~60%) toward ~80% (2 passes) / ~92% (3 passes).

## Context for next session

A single `/audit` run is a **stochastic sample** of the defect space, not a deterministic scan. Empirically, on testForge20's 29-file Vue/TS order directory (6 real runs, audit-2..audit-6), the union of all runs is **84 distinct defect clusters** (±4-line tolerant). Per-run and union coverage:

| | Clusters covered |
|---|---|
| Best single run (audit-6, post-depth-levers) | 51/84 (**60%**) |
| 2-run union (audit-6 ∪ audit-3) | 67/84 (**79%**) |
| 3-run union (audit-2 ∪ audit-3 ∪ audit-6) | 78/84 (**92%**) |
| All 5 runs | 84/84 (100% — denominator *is* this union; tautological) |

**These percentages are coverage of the OBSERVED-UNION** (the 84 clusters = the union of the 6 runs themselves), not absolute recall against the unknown true defect set. The true defect count is ≥84, so absolute recall is unmeasured and strictly ≤ these figures; the numbers establish only the *relative* gain from additional passes — which is what motivates this plan. The cited unions are also **cross-configuration** (audit-3 used a hand-authored system-design/best-practices brief; audit-6 was post-depth-levers), so the observed cross-run independence is partly a brief/config-variation artifact. That makes 79%/92% an **optimistic ceiling** for identical-brief production passes, not a calibrated prediction — the plan provides no same-brief 2-run union to ground the identical-brief case (see OQ-B).

The misses are **largely independent across runs** (audit-6 missed `OrderHeader.vue:369`, which runs 2/3/4/5 all caught; audit-6 found 11 defects no other run did). Independent ~p-recall samples union as `1−(1−p)^k`: p≈0.6, k=2 → ~84%, k=3 → ~94% — matching the observed 79%/92%. The curve is steep at k=1→2 and flattens past k=3, so **2–3 passes is the sweet spot**.

**Why union is safe (no garbage accumulation):** every finding already passes the per-pass grounding gate (`validate-findings` re-reads source, discards ungrounded). Unioning accumulates only *validated* findings — it widens true-positive recall without dragging in false positives. The plan-11 exact-quote-or-drop lever already cut per-pass discards 12→5, so each pass's pool is high-signal.

**Bonus signal:** a defect found in ≥2 passes is corroborated — the same logic as today's cross-agent consensus. Multi-pass-confirmed findings can carry a confidence/consensus tag.

## The backbone: reuse the pipeline, generalize the merge

The single-run pipeline is: dispatch 4 agents → `.tmp-<agent>.md` → `consume-tmp` → `validate-findings` → `compute-consensus` (merges across the 4 agents by exact `(file, line, normalized-pattern)`) → `map-recurring-issues` → `force-rank-top10` → `render-report`.

Multi-pass is the **same pipeline with the merge generalized from "across 4 agents in one run" to "across 4×K agent outputs over K passes":**

1. Loop the **dispatch + consume + validate** phase K times, accumulating each pass's validated `passed` findings into one pool (so the pool holds 4K agent outputs instead of 4).
2. A **single tolerant merge** (`_merge`) collapses the whole pool by location (`(file, line ± TOL)`) and **subsumes `compute-consensus` — one merge stage, not two.** It computes BOTH corroboration axes from each cluster's members: `agent_count` (distinct agents → `[CROSS-AGENT]` when ≥2, the signal `compute-consensus` provides today) and `pass_count` (distinct passes → `[MULTI-PASS:k]` when ≥2). Running `compute-consensus` *after* a location merge would be dead work — the merge has already collapsed each location cluster to one representative, so the exact-match consensus stage would see only singletons and do nothing. So in the multi-pass path `compute-consensus` is **dropped**; the unified `_merge` replaces it.
3. **`map-recurring-issues` → `force-rank-top10` → `render-report` run ONCE** over the merged pool — unchanged.

So the work is: an **orchestration K-loop** (main.md) + a **new algorithmic merge module** (`_audit/_merge.py` — unifies cross-agent + cross-pass corroboration and replaces `compute-consensus` in the multi-pass path) + a **`--passes` flag** + a **cost guard**. `compute-consensus` (module + verb) stays for the single-pass (`--passes 1`) path, which is untouched. Most of the helper layer is reused as-is.

## Decisions (baked in — flip any during review)

1. **Opt-in `--passes N`, default 1.** Multi-pass is K× the cost (K× agent dispatches); it cannot be the default. Single pass stays default for quick checks; the user opts into depth for periodic "second opinion" audits where completeness justifies 2–3× cost. Composes with scope modes (`--full --passes 3`, `--top 25 --passes 2`, etc.).
2. **Hard cap at 3 passes.** `--passes` is clamped to [1, 3]. Diminishing returns past 3 (~92%→~96% for a 33% cost bump) don't justify uncapped spend; a `--passes 10` request is clamped to 3 with a logged note.
3. **Algorithmic merge only (constitution-compliant).** Cross-pass merge is a deterministic rule — `(file, line ± TOL)` proximity, NOT LLM "are these the same" judgment (the constitution forbids fuzzy semantic merging; `compute-consensus` is already exact-match-only for this reason). The ±-line tolerance is the only new fuzziness, and it is mechanical — location-proximity is a deterministic, auditable *proxy* for defect-identity (the inherently semantic "same defect?" question answered by a fixed rule rather than LLM judgment), not a claim that defect-identity is non-semantic. The constitution axis here is determinism-vs-LLM-judgment; OQ-A / Decision 4 govern the proxy's error modes (under-/over-merge).
4. **Merge key = `(file, line ± TOL)` with `TOL=3`.** Same file, lines within 3 → same defect → keep the best-grounded/highest-severity/highest-confidence representative. *(OQ-A: TOL value + whether to also gate on category to avoid merging two distinct co-located defects.)*
5. **Pass-corroboration as a consensus signal.** A merged finding seen in ≥2 passes gets a `[MULTI-PASS:k]` tag and a confidence floor of `Likely` (a defect three independent passes flagged is not `Speculative`). Reuses the existing tag + severity-bump machinery shape.
6. **Each pass runs at the full scope-aware cap** (plan-11 `min(60, max(30, files*2))`) — passes are independent full samples; the merge dedups. Do NOT split the cap across passes (that would shrink each sample and defeat the independence that makes union work).
7. **Cost guard before dispatch.** When `passes × file_count` exceeds a threshold (mirror the existing `scope_oversize` AskUserQuestion at `--scope-limit`), prompt before spending. Show the estimated agent-dispatch count (`passes × agents_present × partitions`).
8. **The merge unifies cross-agent + cross-pass corroboration; `compute-consensus` is dropped from the multi-pass path (NOT run after the merge).** A location merge collapses each cluster to one representative, so a subsequent exact-match `compute-consensus` would see only singletons and be a no-op. Instead `_merge` computes `agent_count` and `pass_count` from each cluster's members in one pass and emits `[CROSS-AGENT]` (agent_count≥2) and `[MULTI-PASS:k]` (pass_count≥2) itself, reusing `_consensus._bump_severity` for the severity bump. `compute-consensus` (module + verb) stays for the single-pass path. **`--passes 1` bypasses `_merge` entirely and takes the existing single-pass pipeline (… → `compute-consensus` → …) — so single-pass is byte-identical to today; all new behavior is confined to `--passes ≥ 2`.**

## Steps (each leaves the suite green)

Per CLAUDE.md: `.py` via python-engineer→python-reviewer; `main.md` via instruction-author→instruction-reviewer.

### Step 1 — `_audit/_merge.py` — the unified tolerant merger (foundation)
- New module: `merge_passes(pools)` takes a list of per-pass validated-finding lists, returns one merged list. Group by file; within a file, cluster findings whose lines are within `TOL` (default 3); collapse each cluster to one representative (highest severity, then highest confidence, then most-grounded/longest evidence — deterministic tiebreak). Each input finding carries its `agent` (already present) and a `pass` index (added by the K-loop) so the cluster can compute, BEFORE discarding members: `agent_count` = distinct agents → `[CROSS-AGENT]` tag + one-level severity bump when ≥2 (reusing `_consensus._bump_severity` — import, don't duplicate); `pass_count` = distinct passes → `[MULTI-PASS:k]` tag when ≥2. This is the cross-agent consensus `compute-consensus` used to compute, now folded into the one location-keyed stage.
- Pure function, dict-flow, stdlib only, Python 3.8+. No I/O, no LLM.
- **Verify:** `tests/lib/_audit/test_merge.py` — two passes with the same defect at `:244`/`:245` collapse to one (pass_count=2); two genuinely distinct defects >TOL apart stay separate; a defect in only one pass keeps pass_count=1; **a single pool where 2 different agents flag the same location → `agent_count=2`, `[CROSS-AGENT]` tag + severity bump, matching today's `compute-consensus` result** (proves the unification is faithful); deterministic representative selection; empty/single-pass inputs behave correctly; `TOL` boundary (==TOL merges, ==TOL+1 does not).

### Step 2 — `findings_schema` + tag plumbing for pass-corroboration
- Add `pass_count` (and confirm `agent_count`) to the finding contract surfaced to the report (optional, default 1) and the `[MULTI-PASS:k]` / `[CROSS-AGENT]` tag conventions. Add a `pass` index field carried on per-pass findings (set by the K-loop, consumed by `_merge`). Confidence floor (`Likely` when pass_count≥2) applied in the merger (Step 1).
- **Verify:** schema/tag tests; `_report` renders the `[MULTI-PASS:k]` tag in the finding's Tags line (it already renders Tags + `[CROSS-AGENT]`); Summary gains a "passes run / multi-pass-confirmed count" line.

### Step 3 — `--passes` flag + clamp (`_cli.py` / `resolve-mode`)
- Add `--passes N` (int, default 1, clamped to [1,3] with a stderr note when clamped). Thread it into the mode result the orchestrator reads.
- **Verify:** `test_cli.py` parse tests (default 1; `--passes 2` → 2; `--passes 10` → 3 + note); `resolve-mode` carries it.

### Step 4 — `force-rank` / `map-recurring` compatibility check (consensus already folded into `_merge`)
- The unified `_merge` (Step 1) has already done cross-agent + cross-pass corroboration, so `compute-consensus` is NOT called in the multi-pass path. Confirm the merged pool (with `pass_count` + `agent_count` + `[MULTI-PASS]`/`[CROSS-AGENT]` tags) flows through `map-recurring-issues` and `force-rank-top10` (the plan-11 location-dedup already handles same-location top-N) without change. Add the multi-pass tag/pass_count into `force-rank`'s score (a corroborated finding ranks higher) — small, optional (OQ-C).
- **Verify:** integration test — a merged pool ranks multi-pass-confirmed findings above single-pass ones of equal base score; **`--passes 1` bypasses `_merge` and is byte-identical to today's single-pass output (the existing `compute-consensus` path is untouched)**.

### Step 5 — orchestrator K-loop (`main.md`)
- For `--passes ≥ 2`: rewrite Phase 3–4.1 as a K-pass loop — for pass in 1..N, dispatch agents to `audits/.tmp-<agent>-p<pass>.md`, consume+validate each into `audits/.validated-p<pass>.json`, stamping every finding with its `pass` index; accumulate. After the loop, call `_merge` (new verb `merge-passes --pools <glob>`) → `audits/.merged.json`, then resume the Phase 4.2+ chain (recurring → rank → report) on the merged file. `compute-consensus` is **skipped** in this path — `_merge` already did cross-agent + cross-pass corroboration.
- For `--passes 1` (narrow default — see status note): take the existing single-pass Phase 3–4 path verbatim (… → `compute-consensus` → …); `_merge` is not invoked. This keeps single-pass byte-identical to today.
- Add the Step-7 cost-guard AskUserQuestion (Decision 7) before the loop.
- Scratch-file lifecycle: per-pass temp files swept by `cleanup-tmps` (the `.tmp-*.md` glob already covers `.tmp-<agent>-p<pass>.md`); add `.validated-p*.json` + `.merged.json` to the Phase-6 `rm`.
- **Verify:** instruction-reviewer pass; grounding — every new sentence matches the helper verbs (esp. the new `merge-passes` verb name + its flags); the `--passes 1` path is described as identical to today.

### Step 6 — `merge-passes` verb wiring (`_cli.py`)
- Expose `audit_helper merge-passes --pools <path-or-glob> > audits/.merged.json` calling `_merge.merge_passes`. Reads the per-pass validated JSON arrays, writes the merged bare array.
- **Verify:** `test_cli.py` + a round-trip test (two pass files → merged file with collapsed dupes).

### Step 7 — docs + report surfacing
- `references/report-format.md`: document the `[MULTI-PASS:k]` tag + the Summary "passes / corroborated" line. `main.md` top + `src/CLAUDE.md` `/audit` description: note the `--passes` mode. CHANGELOG + repo `CLAUDE.md` row.
- **Verify:** instruction-reviewer; grep no stale "single-pass only" framing.

### Step 8 — testForge20 e2e (USER-DRIVEN — DoD gate)
- Run `/audit <order-dir> --passes 2` and `--passes 3`; confirm coverage rises toward the predicted 79%/92% band vs the committed single-pass baseline (audit-6, 60%), `[MULTI-PASS:k]` tags appear, discards stay low, the cost guard fires appropriately, and `--passes 1` is byte-identical to a normal run.
- **Merge-fidelity check (F3).** The recorded 84-cluster baseline is itself a ±4-line-tolerant clustering, so the merger (TOL=3) is validated *against* it, not assumed equal to it. After the K-loop, diff the merger's automated clusters against the baseline and report, alongside coverage %: (a) under-merge count (one baseline defect split across >1 automated cluster), (b) over-merge count (>1 baseline defect collapsed into one), and (c) the cluster→baseline mapping used to compute coverage. A non-trivial over/under-merge count gates OQ-A's category-gating decision. Coverage % is reported *with* these counts, never instead of them — a right-looking coverage number can hide a wrong merge.
- **Brief-diversity A/B (F2).** Run the `--passes 2` calibration both ways — identical briefs vs. per-pass varied framing/seed — and compare union coverage. If identical-brief union undershoots the predicted band while varied-brief hits it, resolve OQ-B → per-pass diversity. Undershooting is *not* grounds to abandon the feature (union remains monotonically positive); it only selects the diversity strategy.

## Open questions

- **OQ-A — merge tolerance.** `TOL=3` lines (±). Too tight → same defect cited 3 lines apart stays split (under-merge, double-counts). Too loose → two distinct co-located defects collapse (over-merge, loses one). Should the key ALSO require matching `category` (or pattern-family) to reduce over-merge? Lean: `(file, line±3)` alone first; add category-gating only if e2e shows over-merge. The ±4 used in plan-11's analysis worked empirically; 3 is slightly tighter. The over/under-merge counts from Step 8's merge-fidelity check are the resolution input for the category-gating decision — "if e2e shows over-merge" means a non-trivial over-merge count in that diff, not an ad-hoc judgment.
- **OQ-B — pass diversity.** Run each pass with identical briefs (rely on inherent LLM nondeterminism) vs. deliberately varied framing/seed per pass to maximize independence? **Lean: diversity-first.** The historical cross-run independence is confounded by brief/config variation (audit-3 hand-brief, audit-6 post-depth-levers), so it cannot support the inference that *identical*-brief passes will be independent enough — identical briefs may correlate and undershoot the band. Make per-pass framing/seed diversity the primary hypothesis Step 8's A/B tests; fall back to identical only if the A/B shows no union loss.
- **OQ-C — corroboration in ranking.** Should `pass_count` bump `force-rank` score (Step 4), and by how much, vs. just tagging? A corroborated finding is more certainly real but not necessarily more *severe*. Lean: small score nudge + tag, severity unchanged.
- **OQ-D — partial-pass failure.** If pass 2 of 3 errors mid-dispatch, union passes 1+3 and note the degraded pass, or fail? Lean: degrade gracefully — union whatever passes completed, note "ran K of N passes" in the Summary.

## When resuming work

1. Read this plan + `11-AUDIT-FULL-SPECTRUM-PLAN.md` (the shipped substrate, commit `6024169`) + the archived testForge20 reports `audits/2026-06-01-audit-{2..6}.md` (the empirical union evidence + e2e baseline).
2. Resolve OQ-A/B/C/D with the user if still open.
3. Execute Steps 1→7 in order (each green before the next); the merger (Step 1) is the foundation, and `--passes 1` must stay byte-identical to today (it bypasses `_merge` and runs the existing single-pass path, `compute-consensus` included) so single-pass behavior never regresses. Step 8 is the user-driven DoD gate.
4. The whole feature is gated on `--passes ≥ 2`; `--passes 1` (narrow default) bypasses `_merge` entirely and runs the committed single-pass `/audit` path verbatim — so the change is bisectable and low-risk to trunk.
