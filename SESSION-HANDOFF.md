# Session handoff — 2026-05-01

This file exists so a fresh Claude Code session can pick up where this session left off without losing context. Created at the user's explicit request after a long iteration on `/generate-docs` Phase 3.3 Step 1.

## Current branch + state

- **Branch**: `develop-2.0-init`
- **Working tree**: clean (all work committed)
- **Last commit**: `index_helper: drop language field — YAGNI per user critique`
- **Test count**: 763 passing (`python3 -m unittest discover -s tests -p "test_*.py"`)

## What was done in this session

**Phase 3.1** (committed earlier): 11 concern-tier helper subcommands + decomposition gate + 66 new tests (foundation done before this session's main work).

**Phase 3.2** (committed earlier): concern-slot-filler subagent + spec dispatching it. This session removed the assumption it was a good design.

**This session's work — audit-driven harness + Step 1 of Phase 3.3**:

1. **Audit-driven minimum viable harness** (3 commits):
   - **Capability-limiting**: tools allowlist propagation in `scripts/generate-agents.py` so subagent source files can declare `tools: Read, Bash, Glob, Grep` and the runtime enforces. Concern-slot-filler updated to use it.
   - **Approval gate**: Phase 2→3 mid-flight checkpoint added to `/generate-docs/main.md` (Continue / Inspect / Abort prompt before fan-out).
   - **Audit trail**: `_trace.py` per-invocation JSONL log at `.devforge/.generate-docs-trace.log` (subcommand, args summary, duration, exit code). Phase 5 timing table in spec.
   - **Circuit breaker**: `_circuit.py` 3 breakers (doom-loop / invocation budget / wall-clock) with bypass env var. Empirically validated — tripped at 60min on testForge20 run.

2. **Phase 3.3 Step 1** (3 commits):
   - `extract-snippet --file F --start S --end E` subcommand on `generate_docs_helper`. Returns verbatim bytes from line range. Closes citation-mismatch error class.
   - `index_helper.py` + POSIX launcher with `build-index` subcommand. Produces `.devforge/index.json` (machine-readable) + `<install_root>/docs/structure.md` (human-readable). Language-agnostic.
   - Wired into `/init-forge` as Step 6.
   - Bug fix: structure.md was landing under project_root in wrapper mode (wrong); now correctly lands at install_root. Regression test pinned.
   - YAGNI cleanup: dropped `language` field from index.json schema (was always "unknown" because init-forge doesn't capture per-package language; LLM detects it during Phase 1 anyway).

3. **Lessons memorized** (2 new memory files):
   - `feedback_avoid_subagents_for_sequential_identical_workflows.md` — subagents for sequential identical-workflow work are overhead; orchestrator-direct beats dispatched subagent on transcription quality. Empirical evidence: tech-writer A/B + concern-slot-filler iteration both hit subagent transcription degradation.
   - `feedback_survey_prior_art_before_inventing_formats.md` — before dispatching for new file formats / schemas / storage shapes, survey prior art (Sphinx objects.inv, ctags, Lunr, SCIP, etc.) and adopt or document divergence. Triggered by `index.json` being invented from scratch when objects.inv encodes essentially the same shape.

## What's next — Phase 3.3 Step 2

**The brief is in `GENERATE-DOCS-PLAN.md` under Step 3.3.2** (search for "Step 3.3.2").

TL;DR: refactor `/generate-docs/main.md` Phase 3 to:
1. Read `.devforge/index.json` once at Phase 3 start (Read tool, in memory)
2. Use `extract-snippet` for every code-snippet arg → eliminates citation-mismatch retries
3. **Drop concern-slot-filler subagent** — orchestrator-direct everywhere (sequential inline iteration over concerns)
4. **Delete `src/agents/concern-slot-filler.md`**
5. Keep `scripts/generate-agents.py`'s tools-allowlist propagation (defense-in-depth for future agents)

Dispatch agents: `instruction-author` + `instruction-reviewer` + `claude-code-guide` (no python-engineer — pure spec edit).

Expected impact (vs latest broken testForge20 run):
- Wall-clock: ~30-50 min (vs ~100min)
- Tokens: ~70-90k (vs ~150k)
- Failed concerns: 0 (citation walls closed)

## Critical context for fresh session

### Recent testForge20 evidence (saved at testForge20/tmp/)

- `.generate-docs-state-r1.json` — first run, parallel dispatch, state-loss incident
- `.generate-docs-state-r2.json` — second run, sequential dispatch, citation-mismatch wall on components + composables
- `.generate-docs-trace-r2.log` — second run trace log (262 invocations over 106 min — 99.99% LLM time, 0.6s helper time)

These are diagnostic data; don't delete.

### Open testForge20 docs state

- `docs/db-cse-ui-strata/apps/app-web/index.md.skeleton` exists (1.6KB, package-tier never finalized)
- `docs/db-cse-ui-strata/apps/app-web/components/index.md.skeleton` (688B — broken concern)
- `docs/db-cse-ui-strata/apps/app-web/composables/index.md.skeleton` (689B — broken concern)
- `.devforge/index.json` (240KB, fresh from this session's helper sync)
- `docs/structure.md` (correct path post-fix)

### Critical decisions to NOT re-derive

1. **Drop subagents for sequential identical-workflow work** — memory rule. When the user proposes adding a subagent, ask which of three concrete benefits (parallelism / tool isolation / context-budget) it buys. Push back if none.

2. **Survey prior art before inventing formats** — memory rule. For Phase 3.4+, the survey table is in the plan's "Execution discipline" section. Cite chosen reference in the brief.

3. **Mechanical extraction is justified by LLM-side savings** — empirical: helper CPU was 0.6s of 100min on testForge20. Helper performance optimization has near-zero impact; LLM token reduction is everything.

4. **Helper-side language detection is a Principle 5 trap** — same as per-language source extraction. Don't add it. LLM detects per-package language during Phase 1's manifest scan.

5. **Wrapper-mode artifacts at install_root, not project_root** — per CLAUDE.md. structure.md path bug already fixed + regression-tested.

6. **Test isolation gap** (deferred): subprocess invocations without `DEVFORGE_DIR` leak trace to repo dir. Workaround: `rm src/devforge/.generate-docs-* && python3 -m unittest ...`. Proper fix: ensure all test subprocess invocations set DEVFORGE_DIR explicitly.

### Active rules (per-project CLAUDE.md + memory)

- All work goes through agents (no direct orchestrator writes; per Execution discipline section of GENERATE-DOCS-PLAN.md)
- Audit format: count first, one finding at a time, fix/defer/skip/discuss prompt
- Iterative apply-verify loop (writer → reviewer → loop until clean)
- Sentence-level non-hallucination check on spec docs
- Cross-check after every change
- Pre-empt future-session hallucination — what would a fresh session falsely believe?

## How to bootstrap a fresh session

1. Read `CLAUDE.md` (project root) — the canonical project instructions
2. Read `GENERATE-DOCS-PLAN.md` — the active plan; Step 3.3.2 is the next dispatch
3. Read this file (`SESSION-HANDOFF.md`) — current-session decisions
4. Auto-memory at `~/.claude/projects/-Users-mykolakudlyk-Projects-ai-dev-team-forge/memory/MEMORY.md` is loaded automatically — both new feedback rules referenced above are pinned there
5. Start with: `git log --oneline -10` to see recent commits
6. Optionally: `python3 -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -5` to verify the 763-test baseline holds

## Files NOT to delete

- `SESSION-HANDOFF.md` (this file) — read by next session, then can be overwritten as new sessions accumulate
- `GENERATE-DOCS-PLAN.md` — load-bearing, plan is mid-execution
- `GENERATE-DOCS-EXECUTION-LOG.md` — historical record of phase-by-phase outcomes
- `testForge20/tmp/.generate-docs-*` — diagnostic evidence for Phase 3.3 design decisions
- `src/agents/concern-slot-filler.md` — slated for deletion in Step 3.3.2 but not yet
