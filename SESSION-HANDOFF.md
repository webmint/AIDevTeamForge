# Session handoff — 2026-05-02

This file exists so a fresh Claude Code session can pick up where this session left off without losing context. User explicitly requested handoff after committing iter 10 + wall-clock removal + plan updates.

## Current branch + state

- **Branch**: `develop-2.0-init`
- **Working tree**: clean (all work committed; only `__pycache__/` untracked)
- **Test count**: 760 passing (was 763; -3 wall-clock breaker tests removed this session)
- **Recent commits** (this session, oldest → newest):
  - `6b0fc93` — Phase 3.3.2 refactor (extract-snippet + drop concern-slot-filler subagent + drop tech-writer + python-engineer to sonnet)
  - `9da0050` — concern-tier tree file granularity + index-based enumeration (iter 5)
  - `63e264a` — per-phase cwd-anchor soft fix (iter 6)
  - `ab1f03c` — full-recursion concern tree + ecosystem-decoupled instructions (iter 7+8)
  - `71693dc` — circuit-breaker: drop wall-clock check; fix invocation-budget
  - `1717c52` — reverse tree skip-rule default — every entry described (iter 10)
  - `fd754ee` — plan: Steps 3.3.4 through 3.3.7

## Empirical validation status

`/generate-docs` ran against testForge20 (`db-cse-ui-strata/apps/app-web`) twice this session:

**Run 1** (post-Phase-3.3.2 + iter 5):
- Wall-clock: 31.8 min total (Phase 3: 29.7 min)
- Concerns: 7/7 ok, 0 failed
- 2 extract-snippet retries (LLM line-estimation off-by-one), auto-recovered
- Components tree: depth-1 only — top-level subfolders + immediate cross-cutting infrastructure files; 17 feature folders (`quote/`, `catalog/`, etc.) stayed folder-level. Empirical motivation for iter 7 (full recursion).

**Run 2** (post-iter-7+8):
- Wall-clock: 28.8 min total (Phase 3: 25.7 min)
- Concerns: 7/7 ok, 0 failed
- 0 extract-snippet retries
- Components tree: full recursion (581 entries) BUT most leaf files had NO description. Skip-rule mass-applied. Empirical motivation for iter 10.

**Run 4** (manual user re-render of `components/index.md` after iter 10 spec change):
- 597 inline `#` descriptions across 582-row tree, 0 bare
- Wall-clock circuit-breaker tripped during the re-render (iter 10 + wall-clock removal both committed AFTER this run; user bypassed via `DEVFORGE_DISABLE_CIRCUIT_BREAKER=1`)
- LLM's honest description-quality breakdown: 5% verified (file read), 25% hand-mapped (name + folder context), 70% regex camelCase split (filename echo)

## Critical architectural finding from Run 4

Tree-as-documentation is a CATEGORY ERROR. Tree's job is location + locator hints; 70% of dense-tree descriptions on a descriptively-named codebase are filename rephrasing, providing no info beyond the filename itself. /research's semantic load lives in:

1. Concern overview prose (LLM-generated structural summary)
2. Public Surface section (verified per-export descriptions, helper-validated citations)
3. Phase 3.4 glossary (Sphinx `objects.inv`-style symbol/term reverse index — pending)
4. /research's targeted code reads on demand

Tree per-entry descriptions are HINTS. Step 3.3.5 captures this as a spec-level contract.

## What's next

### Pending steps from the plan (in order of likely execution)

1. **Step 3.3.4** — open `--kind` enum + soft-recommended list. Empirical: testForge20 Run 3 hit `add-package-export --kind script` (rejected). Closed enum is web-coupled. Two-part change: helper drops validation + adds normalization (lowercase, hyphenate spaces); spec adds recommended-kinds list with ecosystem-rotational examples (trait, decorator, composable, hook, etc.).

2. **Step 3.3.5** — spec-level honesty about tree descriptions as hints. One-paragraph addition to `main.md` step 10 declaring: "tree per-entry descriptions are locator hints; verified semantic content lives in concern overview + Public Surface + Phase 3.4 glossary."

3. **Step 3.3.6** — BLOCKING validation gate. Test on a cryptic-named codebase before iteration-mode unlock. Candidates: legacy enterprise Java with abbreviated module names, generated-code-heavy Rust, single-letter modules from older C++ projects. Pass criterion: tree + concern overview + glossary cover /research's access patterns. Fail → unlock Step 3.3.7.

4. **Step 3.3.7** — per-file docs (B), DEFERRED INDEFINITELY. Conditional on Step 3.3.6 fail. If cryptic-codebase test shows architecture is insufficient, this introduces a sub-concern / section tier. Architectural sketch in plan.

### Live testForge20 state (user paused mid-run)

- Run 3 was paused after concern 1 (components) re-render. State JSON in testForge20 has partial Run 3 data — package-tier complete, components concern complete (with 597 descriptions), other concerns in various states. User chose to halt for token budget.
- A fresh `/generate-docs` run on testForge20 will hit Phase 0's reset/resume prompt. State is preserved.

## Critical context for fresh session

### Architecture decisions locked this session

1. **(A) dense-tree shape with concern-overview prose carrying semantic load** — empirically validated on testForge20 (Vue/TS, descriptive names). Step 3.3.6 will validate on a cryptic-named codebase before final lock.

2. **Tree descriptions are HINTS, not docs** — captured in Step 3.3.5 brief; LLM's empirical 5%/25%/70% breakdown is the load-bearing evidence.

3. **(B) per-file docs DEFERRED INDEFINITELY** — only revisits if Step 3.3.6 fails on cryptic-named codebase.

4. **Circuit breaker: 2 of 3 breakers** — wall-clock removed (was buggy + project-coupled); doom-loop + invocation-budget remain. `DEVFORGE_DISABLE_CIRCUIT_BREAKER=1` still bypasses everything.

### Active rules (per project CLAUDE.md + memory)

- All work goes through agents (no orchestrator-direct writes; per Execution discipline section of `GENERATE-DOCS-PLAN.md`)
- Audit format: count first, one finding at a time, fix/defer/skip/discuss prompt
- Iterative apply-verify loop (writer → reviewer → loop until clean)
- Sentence-level non-hallucination check on spec docs
- Cross-check after every change
- Pre-empt future-session hallucination — what would a fresh session falsely believe?
- Default-argue: engage critically with every non-trivial request
- Zero escape hatch: no carve-outs in discipline rules

### Ecosystem coupling status

The iteration-mode banner (`## ⚠️ ITERATION MODE — APP-WEB ONLY (TEMPORARY)`) at lines 25-44 of `main.md` is INTENTIONALLY coupled to `db-cse-ui-strata/apps/app-web` — it's the empirical-iteration's structural override. Removing the banner unlocks multi-package mode (BLOCKED on Step 3.3.6 validation gate). Everything OUTSIDE the banner was decoupled in iter 8 (multi-ecosystem examples, generic file extensions, ecosystem-rotational lists).

### Test isolation gap (deferred)

Subprocess invocations without `DEVFORGE_DIR` leak trace to repo dir. Workaround: `rm -f src/devforge/.generate-docs-trace.log && python3 -m unittest ...`. Proper fix: ensure all test subprocess invocations set `DEVFORGE_DIR` explicitly. Not addressed this session.

## How to bootstrap a fresh session

1. Read `CLAUDE.md` (project root) — canonical project instructions
2. Read this file (`SESSION-HANDOFF.md`) — current-session decisions
3. Read `GENERATE-DOCS-PLAN.md` Steps 3.3.4 through 3.3.7 — pending work briefs
4. Auto-memory at `~/.claude/projects/-Users-mykolakudlyk-Projects-ai-dev-team-forge/memory/MEMORY.md` is loaded automatically
5. `git log --oneline -10` to see recent commits
6. Optionally: `rm -f src/devforge/.generate-docs-trace.log && python3 -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3` to verify the 760-test baseline holds

## Files NOT to delete

- `SESSION-HANDOFF.md` (this file) — read by next session, then can be overwritten
- `GENERATE-DOCS-PLAN.md` — load-bearing, plan is mid-execution
- `GENERATE-DOCS-EXECUTION-LOG.md` — historical record of phase outcomes
- `testForge20/.devforge/.generate-docs-state.json` — paused-run state for testForge20
