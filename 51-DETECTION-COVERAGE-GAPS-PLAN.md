# 51 — Detection Coverage Gaps

**Status: BUILD COMPLETE 2026-07-08 (working tree) — F4 ✅ · F5 ✅ · F3 ✅ · F1 ✅ shipped; F2 → plan 54; F6 skipped. Consumer/testForge20 e2e is the remaining user-driven gate.** Re-analysed against plan 53; un-parked 2026-07-08.

### Build log (2026-07-08)
- **F4 (a11y dispatch) ✅** — new `design-auditor` Accessibility-scoped mode + `/review` PHASE 2.5b conditional dispatch (recall-biased `resolve-ui-scope` verb over `PROJECT_NATURES`) + `render-report --a11y-section` + report-format/`src/CLAUDE.md`/CHANGELOG. 360 `_review` tests green; instruction-reviewer + claude-code-guide clean; a case-sensitivity bug caught + fixed inline. a11y 🔴→🟢.
- **F5 (concurrency lens) ✅** — `code-reviewer.md` new Approach step 5 (static, anti-false-positive absolute, grounded). **`architect.md` deliberately EXCLUDED** (its Rule 9 already governs design-level concurrency by respecting §6 out-of-scope; a hunting lens would contradict it — do NOT "fix" this omission). Verified directly.
- **F3 (perf honesty) ✅** — `performance-analyst.md` reworded to two modes: static perf-smell (in-pipeline default, un-measured `Likely`/`Speculative`) vs runtime profiling (when app/profiler available); Rule 1 relaxed, anti-guessing preserved; no new tools claimed. The runtime-WIRE option (fix a) is DEFERRED (bigger; could fold into plan 54). Verified directly.
- **F1 (regression gate) ✅** — the largest build. New config `regression_gate` (off/full, default `full`, back-filled into existing configs) + `verify_helper regression-gate` (`_verify/_regression.py`: baseline-diff green→red — primary test command at the feature merge-base in an isolated `git worktree` with symlinked deps vs HEAD; pre-existing-red never gates; fail-soft, try/finally worktree cleanup) + `compute-verdict --regression` fold (regression → NEEDS WORK, never REJECTED) + `/verify` PHASE 4.3 + 5.1 wiring + report-format + `src/CLAUDE.md`/CHANGELOG. Reuses `_shared/feature_scope.py` merge-base helpers + `_implement/_workspace.py` wrapper source-root. 544 `_verify` + 549 `_configure` tests green (real git-fixture regression/pre-existing/cleanup tests); full repo 9,425 green. `_regression.py` + the PHASE-4.3/5.1 wiring self-verified directly by the orchestrator. Design: baseline-diff + default-on (maintainer-ratified — the baseline-diff de-risks default-on). MVP = primary `TEST_COMMANDS[0]`; per-package aggregation is a `# TODO(refinement)`.
- **Reviewer-agent note:** `instruction-reviewer` / `python-reviewer` dispatches repeatedly stalled on cross-file grep steps in this environment; F5/F3/F1 + the helper case-fix were review-verified directly by the orchestrator (edits landed before the stall). F4's reviews completed normally.
- **Follow-on candidates (not built here):** F3(a) runtime-wire perf-analyst (could fold into plan 54); F1 per-package test-aggregation refinement; the type-2 step-level reachability gate (open decision 3, prompted by F4's a11y orphan); persisting F1's failing-test tail into `verification.md` (currently in-run only). None blocking.

On `develop-2.0-init`.

**Un-park note (2026-07-08):** the original park reason was *"a separate issue found in `design-auditor`; resolve it before Finding 4."* That issue was the design-fidelity rework — **plan 53 (`53-DESIGN-ANCHOR-FIRST-CLASS-PLAN.md`) shipped (phases 1–8; e2e deferred)** and is that resolution. This plan was re-analysed against the post-plan-53 state (see `## Re-analysis 2026-07-08`). Net effect: Findings 1/2/3/5/6 unchanged as gaps (F2/F3 fixes became more tractable — plan 53 built reusable precedents); **Finding 4 got WORSE and reshaped** — accessibility/responsive/native (design-auditor steps 8–10) are dispatched by NO command. **Attribution (corrected 2026-07-08):** this is NOT a plan-53 regression. The `/review` design-auditor dispatch was fidelity-purposed from its creation (plan 40 Phase 6, `40-…-PLAN.md:169`: *"add a dedicated fidelity sub-step"*); the a11y/responsive/native half never had a pipeline caller. Plan 40 declared the design-auditor charter orphan-resolved by wiring only the fidelity half; plan 53 merely FORMALIZED the exclusion (added the explicit "SKIP steps 8–10" scoped mode). Net: a **long-standing gap**, present since design-auditor was first wired.

This is a **findings-capture record**, not yet a build plan. It preserves a coverage audit of the framework's quality-detection apparatus so a future session can resume triage + build without re-deriving. No code written.

## Context for next session

Origin question (maintainer, 2026-07-06): *"Does the review/verify apparatus catch most issues, or are there gaps?"* — sparked by observing that `/review` on the mintEnvoy consumer install really does catch issues, but wondering if coverage is enough.

Method: mapped the whole detection surface against a defect taxonomy via two grounded investigators (Explore agents reading the actual specs/helpers). Every finding carries `file:line` grounding — not vibes.

### One-line coverage verdict

**The framework is strong on `in-scope + stated + static` defects, and blind on `out-of-scope + unstated + dynamic` defects.** Everything the pipeline catches is within the current feature's diff, named in the ACs/design-ref, or found by code-reading. What escapes: out-of-scope regressions, unstated runtime failure modes, and dynamic non-functional behavior — exactly the class where "a human can miss something" bites, because no automated gate covers it either.

### Detection surface (what exists)

- `/implement` per-task panel — code-reviewer + qa-reviewer + security-reviewer + performance-analyst, over the per-task diff
- `/review` feature-level — 5 finders (code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst) + conditional design-auditor (fidelity-only) + refutation, over the assembled feature diff, emergent cross-task
- `/verify` — ac-verifier (runtime/code by mode) + assembled mechanical checks + folds `/review` findings → the verdict
- `/grill` — design-time, devils-advocate attacks `plan.md` before build
- `/audit` — standalone full-spectrum + refutation (NOT in the pipeline chain)
- forcing functions — magic-enum / cross-layer / any-leak / design-tokens (mechanical, consumer-side)

### Coverage matrix (defect class → status, post-plan-53)

| Defect class | Status | Owner |
|---|---|---|
| Logic bugs (mislogic, control-flow) | 🟢 strong | code-reviewer + /audit mislogic |
| Security (injection/auth/secrets/deps) | 🟢 static | security-reviewer |
| Test coverage gaps | 🟢 | qa-reviewer (static assessment) |
| AC not met | 🟢 | ac-verifier (runtime when `runtime-assisted`) |
| Cross-task arch drift | 🟢 | /review architect |
| Design/visual fidelity | 🟢 | design-auditor (fidelity engine) + design-tokens — plan 53 |
| Constitution adherence | 🟢 | forcing functions + /audit |
| **Regression in existing (out-of-scope) features** | 🔴 GAP | none — Finding 1 |
| **Exploratory/adversarial runtime (unstated failure modes)** | 🔴 GAP | none — Finding 2 |
| **Runtime perf / load / memory (in-pipeline)** | 🟡 partial | Finding 3 (charter-vs-execution) |
| **Accessibility (any feature)** | 🔴 GAP (was 🟡) | none — Finding 4 (orphaned by plan 53's scoping) |
| **Concurrency / race conditions** | 🔴 GAP | none — Finding 5 |
| Security at runtime (DAST/fuzz) | 🟢 by-design boundary | Finding 6 (skip) |

## Re-analysis 2026-07-08 (post plan 53)

Plan 53 (`53-DESIGN-ANCHOR-FIRST-CLASS-PLAN.md`, phases 1–8 shipped, e2e deferred) reshaped the entire design-fidelity apparatus: design intent is now a first-class `design_anchor` captured at intake; `design-auditor` was rewritten to an intent-reader × built-reader × comparator engine (steps 0–7) + a new **fidelity-only scoped dispatch mode**; `/review` PHASE 2.5 dispatches it in that scoped mode.

Impact on the six findings:

- **F1 (regression gate) — UNCHANGED.** Plan 53 touched nothing in the test/mechanical-check scope. `/verify` PHASE 4 still runs `verify-touched` scoped to changed files. Still HIGH, still valid. Re-confirm `file:line` on build (verify PHASE 4 was not a plan-53 edit site).
- **F2 (exploratory/adversarial runtime) — UNCHANGED as a gap; fix more tractable.** Plan 53's VLM advisory is holistic *visual* judgment, not adversarial *behavior* probing, and still keys off stated design intent — it does not close F2. But plan 53 shipped two reusable precedents: (a) an in-pipeline browser-driving runtime substrate (`.devforge/lib/_design/js/*.js` collectors run via Chrome DevTools MCP `evaluate_script`), and (b) the **non-gating advisory layer** pattern (design-auditor step 7 / `## Advisory (non-gating)`) — a model for an adversarial prober that surfaces "worth a human glance" findings without gating (mirrors the flake-risk mitigation F2 needs).
- **F3 (perf static-in-pipeline) — UNCHANGED as a gap; fix cheaper.** Plan 53 did not touch performance-analyst. But it PROVES a read-only reviewer (design-auditor) can drive a headless browser + the real running app in-pipeline. So F3's fix option (a) — provision a runtime profiler for performance-analyst — drops from "heavy" to "moderate: copy design-auditor's Chrome-MCP dispatch + `evaluate_script` collector pattern." Honesty option (b) unchanged.
- **F4 (accessibility) — CHANGED: WORSE + reshaped; attribution corrected.** Not a plan-53 regression — a long-standing gap (the `/review` design-auditor dispatch was fidelity-purposed from plan 40; plan 53 formalized the a11y exclusion). See the rewritten Finding 4 below. Truth-in-advertising dimension: `design-auditor.md:3` advertises "accessibility (WCAG), responsive behavior" and the agent appears in the consumer `{{AGENT_LIST}}`, so consumers believe a11y is covered — it is not.
- **F5 (concurrency) — UNCHANGED.** Plan 53 irrelevant.
- **F6 (security static-only) — UNCHANGED.** Plan 53 irrelevant; still SKIP.

## Findings

Presented in the mandated audit format (`CLAUDE.md` §Audit format). Severities (post-re-analysis): **3 HIGH** (F1, F2, F4 ↑), 2 MEDIUM (F3, F5), 1 LOW (F6).

### Finding 1 — Regression blind spot: no full-suite gate anywhere
- **Severity:** HIGH
- **Location:** `src/commands/verify/main.md:209-221` (PHASE 4), `src/commands/implement/main.md:157-171` (PHASE 5), `src/devforge/lib/_implement/_cmds_verify.py:258-307` (`_collect_commands`)
- **Issue:** Every mechanical/test gate scopes tests to **changed files only**. `/implement` runs per-task touched-file tests; `/verify` runs assembled-feature changed-file tests. `verify-touched` derives commands strictly from the touched-files list (longest-path-prefix → package `test_command`). No command runs the full project suite.
- **Why it matters:** A feature that breaks an existing, untouched feature's behavior sails through. The regression surfaces only if a pre-existing test happens to live inside the changed-file scope — otherwise invisible until CI (if any) or production. Zero automated net for the "my change broke something unrelated" class. Confirmed end-to-end by investigator.
- **Fix:** Add a full-suite regression gate at `/verify` PHASE 4 (feature boundary is the right altitude — not per-task, too expensive). Run the primary-stack `TEST_COMMANDS` unscoped once, report-only, fold failures into the verdict. Gate behind a config flag (`regression_gate: full | scoped | off`) so slow/expensive suites can opt to scoped-only. Cross-ref: `verify/main.md` + a new `_verify` verb or a `verify-touched --full` flag + `verify/references/report-format.md`.
- **Triage rec:** BUILD. **Post-53: unchanged.**

### Finding 2 — No exploratory/adversarial runtime testing
- **Severity:** HIGH
- **Location:** whole pipeline — `src/agents/ac-verifier.md` (stated-AC only), `src/commands/review/main.md:141` (code-reading finders), `src/commands/verify/main.md:189-221`
- **Issue:** Every runtime check verifies pre-stated ACs or pre-stated design conformance. Nothing probes the running app for *unstated* failure modes — abuse input, weird sequences, boundary inputs the ACs never named. (Plan 53's VLM advisory added holistic *visual* judgment, not behavioral probing — the gap stands.)
- **Why it matters:** The "human can miss something" class — and the framework misses it too. The human is the sole exploratory tester with zero automated backstop. The highest-value bugs (the ones nobody thought to spec) live here.
- **Fix:** New opt-in step or agent — an adversarial runtime prober dispatched at `/verify` when `runtime-assisted` + app up. Feeds off the ACs but attacks *around* them. **Reuse plan 53's precedents:** the `_design/js/*` + Chrome-MCP `evaluate_script` substrate for driving the app, and the non-gating `## Advisory (non-gating)` pattern so a flaky probe surfaces "worth a human glance" notes without gating the verdict (the framework already fought false-positives in plans 19/34 — a cry-wolf prober is the anti-goal). Biggest single build; probably its own plan. Absorbs any runtime-security appetite from Finding 6.
- **Triage rec:** BUILD — but DEFERRED to its own plan. **Now owned by `54-ADVERSARIAL-RUNTIME-PROBING-PLAN.md`** (split out 2026-07-08: highest weaken-risk of plan 51's findings, largest build, needs the F4/F1/F5/F3 deliveries as reuse precedent). Do NOT build F2 under plan 51. **Post-53: unchanged gap, now more tractable; see plan 54.**

### Finding 3 — Perf verified static-in-pipeline despite runtime charter
- **Severity:** MEDIUM
- **Location:** `src/agents/performance-analyst.md` Approach (lines ~24-31, "measure first / profile the running app") vs `src/commands/review/main.md` dispatch (finders code-read the diff; no step starts the app or provisions a profiler)
- **Issue:** The agent is chartered to profile the *running* app, but no pipeline step provisions a running app + profiler for it, and (to confirm) it lacks Chrome-MCP tools. In `/review`/`/implement` it de-facto reads the diff for perf smells only.
- **Why it matters:** Charter-vs-execution gap. Runtime perf regressions (N+1 that only shows at scale, bundle bloat, memory) aren't measured in-pipeline — the "measure first" instruction is unfired. Also a type-2 orphan risk (declared-but-unexecuted step) per plan 41's taxonomy.
- **Fix:** Either (a) wire performance-analyst to a runtime provisioning step — **now moderate cost: copy design-auditor's proven Chrome-MCP dispatch + `evaluate_script` collector pattern (plan 53)** — or (b) honestly retitle it a static perf-smell reviewer in-pipeline and note runtime profiling is standalone-only. **Verify the `tools:` line first** — if it has no browser channel, (b) is the honest floor.
- **Triage rec:** DISCUSS — cheap fix is honesty (b); real fix (a) is now moderate, not heavy. **Post-53: gap unchanged, fix (a) cheaper.**

### Finding 4 — Accessibility / responsive / native audits are dispatched by NO command
- **Severity:** HIGH (was MEDIUM in plan 51 v1 — raised by plan 53's re-analysis)
- **Location:** `src/agents/design-auditor.md:27` (fidelity-only scoped mode skips steps 8–10), `:37-39` (steps 8 Accessibility / 9 Responsive / 10 Native), `src/commands/review/main.md:199` (the ONLY pipeline dispatch — scopes to fidelity-only, instructs the agent to SKIP steps 8–10 "entirely")
- **Issue:** Accessibility (WCAG), responsive-breakpoint, and native-mobile audits live in `design-auditor` steps 8–10. The ONLY command that dispatches `design-auditor` in the pipeline is `/review` PHASE 2.5, and it scopes the dispatch to **fidelity-only mode** — instructing the agent to SKIP steps 8–10 "entirely" (`review/main.md:199`). No command dispatches `design-auditor` in a mode that runs steps 8–10. Net: **steps 8–10 run for zero features in the pipeline** — the a11y/responsive/native capability is orphaned. This is long-standing: plan 40 wired the dispatch as a fidelity sub-step (`40-…-PLAN.md:169`); plan 53 added the explicit "SKIP steps 8–10" scoped mode but did not change the (already-zero) a11y coverage.
- **Why it matters:** a11y is a legal/UX floor (ADA / EN 301 549 / WCAG). It runs for no pipeline feature — AND `design-auditor.md:3` advertises it (the agent is in the consumer `{{AGENT_LIST}}`), so it is **advertised but not delivered**. This is a concrete **type-2 orphan** (a declared step with no caller) — the class plan 41 deliberately left unmechanized: plan 41's `verify-agent-reachability` gate passes `design-auditor` as "reachable" (it IS dispatched), blind to steps 8–10 being dead because the only dispatch is scoped past them.
- **Root cause:** fidelity and a11y were COUPLED under one dispatch gated on a design reference — but they are orthogonal. Fidelity is intent-relative (drift *from a reference* → needs `design/reference.html` + binding). a11y is absolute (WCAG needs no reference → needs only a frontend UI + a running app).
- **Fix (orthogonal split):** keep PHASE 2.5 as the fidelity gate (design-ref-gated, as-is). Add a SEPARATE a11y/responsive/native dispatch sub-step at `/review` for any **frontend** feature (detect via touched-file stacks / `PACKAGE_STACKS`, reference or NOT) — dispatch `design-auditor` in a new "a11y-scoped" mode (steps 8–10), with the SAME Chrome-MCP-present-or-NOT-COVERED honesty model as fidelity (a11y checks are runtime DOM reads — contrast/keyboard/ARIA/focus — so they need the app up + Chrome MCP; app down → NOT-COVERED, honest). Cross-ref: `review/main.md` (new sub-step) + `design-auditor.md` scoped-mode text (add the a11y-scoped variant beside the fidelity-only one) + `review/references/report-format.md` (restore the Accessibility section). **Plus** — this is the poster child for growing plan 41's reachability gate a step-level (type-2) check so a future scoping change can't silently orphan a capability again (open decision 3).
- **Triage rec:** BUILD (severity raised — now zero coverage, not partial). **Post-53: no longer blocked (park reason resolved); reshaped from "decouple from design-ref" to "re-home the orphaned a11y dispatch."**

### Finding 5 — No concurrency / race-condition detection
- **Severity:** MEDIUM (project-dependent — HIGH for concurrent backends, ~nil for static sites)
- **Location:** absent — not in `security-reviewer.md`, `performance-analyst.md`, `architect.md`, or any runtime step
- **Issue:** No gate, static or runtime, hunts races / thread-safety / lock-ordering.
- **Why it matters:** Hardest bug class, worst to debug in prod. Static review rarely catches; no runtime stress exists.
- **Fix:** Add a concurrency lens to code-reviewer/architect checklists (static, cheap, partial). Full runtime stress is out of scope/YAGNI for most consumers.
- **Triage rec:** BUILD the static lens only; skip runtime stress. **Post-53: unchanged.**

### Finding 6 — Security is static-only
- **Severity:** LOW
- **Location:** `src/agents/security-reviewer.md:25-39` — 8 static checklists, no runtime probing
- **Issue:** No DAST/fuzzing/live auth-bypass probing.
- **Why it matters:** Static catches most; runtime IDOR/authz-at-runtime not probed.
- **Fix:** Likely none — reasonable scope boundary. Any runtime-security appetite folds into Finding 2's adversarial prober.
- **Triage rec:** SKIP. **Post-53: unchanged.**

## Open decisions (unresolved — carry into the build session)

1. **Scope** — which findings to build UNDER THIS PLAN: F4, F1, F5-static (+ F3 honesty). F2 is SPLIT OUT to `54-ADVERSARIAL-RUNTIME-PROBING-PLAN.md` (deferred — highest weaken-risk). SKIP F6 (folds into plan 54). Build order (per the strengthen-not-weaken triage, maintainer-directed 2026-07-08): F4 → F1 → F5 → F3(b honesty).
2. **Structure** — one umbrella plan (Phase 0 ratify + a build-phase-group per accepted finding) vs separate numbered plans per finding. Repo convention favors single-topic plans; the findings share a coherent theme (detection coverage). Recommendation: umbrella for F1/F4/F5; F2 (adversarial prober — largest, new agent) split to its own plan given its size and flake-risk profile. **F4 is now a quick, high-value re-home** (re-point a dispatch scope), a strong first build.
3. **New (from re-analysis)** — should plan 41's `verify-agent-reachability` gate grow a **step-level / type-2** check? F4 is proof that a reachable agent can carry a fully-orphaned capability. Out of scope for the findings themselves; note it as a candidate follow-on when F4 is built.

## Agent-loop mechanics (per CLAUDE.md — for the build session)

Every build phase routes through the mandated iterative apply-verify loops:

- **Python helpers** (`src/devforge/lib/_verify/`, `_implement/`, any new subpackage) — `python-engineer` → `python-reviewer`, looping until review-clean. Test-first: every function gets a test written + run in the same turn (round-trip via the real producer for parsers).
- **Command / agent / reference markdown** (`src/commands/*/main.md`, `references/*.md`, `src/agents/*.md`) — `instruction-author` → `instruction-reviewer`, looping until clean, PLUS `claude-code-guide` for anything shipping into `.claude/` or describing Claude Code integration.
- **Cross-cutting**: after each edit, grep for affected identifiers/paths/section-numbers/config-keys/helper-verb-names and fix dangling refs in the same change. Update the emitter `_PROMOTED` + verify install end-to-end if a new command/agent is added. Bump nothing (version bump is maintainer-driven, deferred).

Per-finding loop shape (build session):
- **F1** — `_verify` verb (or `verify-touched --full` flag) via python loop → `verify/main.md` PHASE 4 edit + `report-format.md` via instruction loop.
- **F2** — new `src/agents/<adversarial-prober>.md` + `/verify` dispatch step via instruction loop + claude-code-guide; register in emitter `_PROMOTED`; run the agent-reachability gate (`scripts/verify-agent-reachability.py`) so the new agent isn't an orphan. Reuse plan 53's `_design/js` + Chrome-MCP substrate + the non-gating advisory pattern.
- **F4** — NEW a11y-scoped `/review` dispatch sub-step (orthogonal to the fidelity PHASE 2.5, frontend-gated not reference-gated) + a new a11y-scoped mode in `design-auditor.md` (beside the fidelity-only one) + `review/references/report-format.md` (restore the Accessibility section) via instruction loop + claude-code-guide. **No longer blocked** — plan 53 resolved the park reason. Cheapest high-value build (mostly a dispatch + scoped-mode wiring; the a11y steps 8–10 already exist in the agent).
- **F5** — checklist additions to `code-reviewer.md` + `architect.md` via instruction loop.

## When resuming work

1. Read this file in full, then skim plan 53 (`53-DESIGN-ANCHOR-FIRST-CLASS-PLAN.md`) for the current design-auditor / `/review` PHASE 2.5 dispatch model — F4's fix depends on it.
2. Re-confirm each finding's grounding still holds (the `file:line` refs may have drifted — re-grep before building; plan 53 moved design-auditor + `/review` PHASE 2.5 text, so F4's line refs are the freshest but re-verify).
3. Get the maintainer's scope selection (open decision 1) + structure choice (open decision 2) + the type-2-gate question (open decision 3).
4. For accepted findings, build behind the agent loops above.
5. Each finding's DoD includes a testForge20 / consumer e2e (the repo's standard manual gate).

## Verify (per finding, when built)

- **F1** — a feature whose change breaks an out-of-scope existing test now surfaces at `/verify` NEEDS WORK (was: silently APPROVED). Config flag toggles full/scoped/off.
- **F2** — the prober surfaces at least one unstated-AC failure mode on a seeded buggy feature; false-positive rate acceptable (no cry-wolf on a clean feature — mirror plan 34's clean-feature regression test).
- **F3** — either perf-analyst runs a real profiler in-pipeline (a), OR its spec + the docs honestly state static-in-pipeline / runtime-standalone (b) with no dangling "measure first" claim.
- **F4** — a frontend feature (with OR without a `design/reference.html`) now gets an accessibility audit at `/review`; the report carries an Accessibility section again.
- **F5** — a seeded race (e.g. unguarded shared mutable state) is flagged by code-reviewer or architect.

## Provenance

Grounding from two Explore investigators (2026-07-06): one mapped test/regression gate scope (confirmed no full-suite gate — traced `verify-touched` `_collect_commands` scoping), one mapped runtime/non-functional coverage (confirmed no exploratory runtime, no concurrency check; perf chartered-runtime; a11y present but design-ref-conditional). Re-analysis (2026-07-08) read the post-plan-53 live state directly: `design-auditor.md` (fidelity-only scoped mode + steps 8–10), `review/main.md:182-201` (PHASE 2.5 fidelity-only dispatch, only pipeline dispatch site of design-auditor), and confirmed no unscoped design-auditor dispatch exists across `src/commands/`. Refs current as of 2026-07-08.
