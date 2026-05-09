# Next-session work dump

State at hand-off (2026-05-09): **Track 4 (project-tier shape expansion) SHIPPED + CLOSED.** No further work on Track 4 per user direction. testForge20 validated empirically (6-min wall-clock, 11-section overview + 8-section architecture). Next priority: **Track 1 (F.11 hooks)** as the enforcement leg of Plan F COMPLETE.

## Reading order at session start

1. `CLAUDE.md` (auto-loaded).
2. This file — start at **Track 1 (F.11 hooks)**. Track 3 (/research redesign) deferred per 2026-05-08 direction.
3. Track-specific plan (linked under each track).

## State summary

| Track | Status | Last commit |
|---|---|---|
| Plan F pipeline (concern + package + project tiers) | **SHIPPED** | bcd5f1c |
| Track 4 Phase 1 — project-overview mechanical | **SHIPPED 2026-05-09** | 9577705 |
| Track 4 Phase 2 — project-overview mixed mech/LLM | **SHIPPED 2026-05-09** | 36076a2 |
| Track 4 Phase 3 — project-architecture LLM-judgment + cite-back | **SHIPPED 2026-05-09** | 70b547e |
| Track 4 — CLOSED. Follow-ups (snippet-fidelity, targeted retry) NOT pursued per user direction 2026-05-09 | **CLOSED** | — |
| Track 1 — F.11 hooks (CBM-first enforcement) | OPEN — **NEXT** | — |
| Track 2 — codegraph reference scrub | OPEN | — |
| Track 3 — /research command redesign | DEFERRED | — |

Suite at hand-off: **1284 passed + 11 skipped** on `develop-2.0-init`.

## Track 4 — what shipped (so next session knows what's there)

`docs/overview.md` rendered with 11 sections (cse-strata bar parity):
Purpose · Tech Stack · Project Structure · Entry Points · Key Commands · Module Map · Cross-Module Dependencies · Application Routes · Navigation Guards · Test Files · Packages

`docs/architecture.md` rendered with 8 sections:
Architecture Overview · Module / Package Structure · Patterns · Conventions · Layers · Cross-Cuts (subsection-style with cite-backed snippets) · Dependency Direction Rules · Dependency Overview (mermaid)

`project-input` extended outputs (mechanical + candidate fields):
- Phase 1: tech_stack_candidates, key_commands, test_file_paths, cross_module_deps_tree, project_structure_tree
- Phase 2: entry_point_candidates, router_route_files, nav_guard_files, package_classification_hints
- Phase 3: dep_graph_mermaid

`_resolve_effective_project_root` reads init.yaml's `project_root` field for wrapper-mode projects (testForge20-style) so mechanical extraction operates on the inner monorepo, not the wrapper.

`_gather_workspace_deps` aggregates deps across npm-workspaces packages so monorepo root package.jsons (orchestration-only) don't mask app-layer Vue/TS/Pinia/Apollo detection.

12 new setters total (5 Phase 1 + 5 Phase 2 + 7 Phase 3, two of which share placeholder slots with Phase 0 — `set-doc-cross-cuts` for bullet-list shape vs `set-architecture-cross-cuts-detailed` for subsection shape).

## 2h 19m stall — investigation completed (informational only)

A testForge20 run of project-tier (2 docs) took 138min on 2026-05-09. Investigation found the cause was Claude Code session-side, NOT helper:
- 47min mid-tier gap = extended-thinking latency on long accumulated context
- 76min after validate-doc fail = stuck `<assistant>` empty block; user manually prodded "why did u stopped" to resume

Subsequent fresh-session run did 2 docs in 6min — Phase 3 cost shape is fine. Helper code innocent. Stall is a Claude Code / long-context artifact, not a /generate-docs design flaw.

**Mitigation: split tier work across separate Claude Code sessions when long context accumulates** (e.g. clear/restart between concern → package → project). Targeted-retry + snippet-fidelity were considered as remediation paths but **NOT pursued — user closed Track 4 2026-05-09**.

## Track 1 — F.11 hooks (CBM-first enforcement) — NEXT

**Source spec**: `CBM-INTEGRATION-PLAN.md` §F.11 (lines ~539-564). 4 hooks defined (placeholder only — scripts not authored, install.sh not wired):

| Hook | Event | Purpose |
|---|---|---|
| `cbm-code-discovery-gate` | PreToolUse on Read/Grep/Glob | Advisory: "consider `search_graph` / `search_code` before text search". Exit 0 (non-blocking) |
| `cbm-mcp-marker` | PostToolUse on Bash + MCP tools | Telemetry: marks each CBM tool invocation in transcript so adoption is measurable |
| `cbm-session-reminder` | SessionStart (resume / clear / compact) | Re-injects CBM-first protocol when prior context window dropped |
| `bash-ban-raw-tools` | PreToolUse on Bash | Soft-rejects raw `grep`/`find`/`cat` patterns over source files; suggests CBM equivalent |

**Pattern reference**: sgaabdu4/claude-code-tips at https://github.com/sgaabdu4/claude-code-tips/tree/main/hooks.

**F.11.a — Hook scripts** ship in `src/devforge/hooks/`. Each is stand-alone shell/python consuming Claude Code hook JSON contract on stdin.

**F.11.b — install.sh / wizard integration**:
- Wizard prompts: `Install CBM-first enforcement hooks to .claude/hooks/? (recommended for /research /specify /plan workflows) [yes/no]`.
- On `yes`: copy hook scripts to `<target>/.claude/hooks/` (presence-guarded; never overwrite existing same-named hooks) + add entries to `<target>/.claude/settings.json` under appropriate event arrays.

**F.11.c — CLAUDE.md template documentation**:
- Section "CBM-first protocol enforcement" describes each hook's role + how to disable individually + linkback to sgaabdu4 reference.

**Verify F.11**:
- 4 hook scripts authored + manually invoked against sample tool-call JSON to confirm exit codes + stderr messages
- install.sh adds hooks (presence-guarded) on wizard `yes`; doesn't overwrite custom hooks; doesn't error when `~/.claude/hooks/` lacks settings.json keys
- Empirical: in testForge20, run /research with hooks active; confirm `cbm-code-discovery-gate` fires when Claude tries Read/Grep/Glob on source files; confirm `bash-ban-raw-tools` fires on naive grep
- Documentation: CLAUDE.md template has the section; instruction-author + claude-code-guide sign off on hook contract conventions

**Considerations before authoring**:
- `agentic_context` is a codegraph MCP tool requiring LLM-enabled mode (currently disabled per memory `project_codegraph_state_2026_05_06`). The advisory in `cbm-code-discovery-gate` should reference CBM-only tools (`search_graph`, `search_code`, `trace_path`, `get_code_snippet`) — not codegraph. Cross-link with Track 2.
- Hook authoring needs Claude Code hook contract verification via `claude-code-guide` agent (per `feedback_claude_code_authoring_best_practices`).
- Install path: `~/.claude/hooks/` (user-level) vs `<project>/.claude/hooks/` (project-level). Plan assumes project-level. Confirm.

## Track 2 — codegraph reference scrub

**Why**: codegraph MCP tools (`agentic_context`, `agentic_impact`, `agentic_quality`, `agentic_architecture`) are LLM-disabled in current setup (per `project_codegraph_state_2026_05_06`). Framework spec/docs reference them as if available. User confirmed 2026-05-08: codegraph not used; remove references.

**Files with stale refs** (at session start, may evolve):

```
src/_pending/commands/audit.md
src/_pending/commands/breakdown.md
src/_pending/commands/fix.md
src/_pending/commands/plan.md
src/_pending/commands/refactor.md
src/_pending/commands/research.md
src/_pending/commands/specify.md
src/devforge/storage-rules.md
src/devforge/lib/_generate_docs/_validators_concern.py
src/devforge/lib/vue-to-ts.mjs
```

**Triage**:

| File | Likely action |
|---|---|
| `src/_pending/commands/*.md` (7) | Per-command revision pass (memory `project_post_codex_command_revision`) is the natural home — fold scrub there. Don't double-edit. |
| `src/devforge/storage-rules.md` | Active doc, ships to target. Edit now: replace `agentic_context` / `agentic_impact` with CBM equivalents (`search_graph` / `query_graph` / `search_code` / `trace_path` / `get_code_snippet`). |
| `src/devforge/lib/_generate_docs/_validators_concern.py` | Inspect: if reference is import/call → broken at runtime (verify with tests); if comment/docstring → prose edit. |
| `src/devforge/lib/vue-to-ts.mjs` | Likely false positive (`graph` substring not codegraph). Inspect + skip. |

**Replacement map** (CBM tools that cover codegraph use cases):

| codegraph (disabled) | CBM equivalent |
|---|---|
| `agentic_context "<topic>"` (synthesized narrative+structure) | `search_graph(query="<topic>")` (BM25 ranked) + `search_code(pattern)` (text fallback) |
| `agentic_impact("if I change X, what breaks?")` | `trace_path(function_name, mode="callers")` + `search_graph(name_pattern=".*X.*")` |
| `agentic_quality("hotspots")` | `query_graph` Cypher for high-fan-out / cyclomatic-complexity |
| `agentic_architecture("how is X structured?")` | `get_architecture(aspects=[...])` (CBM has this) |

**Verify scrub**:
- `grep -rn "agentic_context\|agentic_impact\|agentic_quality\|agentic_architecture" src/ scripts/` returns 0 hits in active (non-`_pending/`) paths.
- Tests pass.
- testForge20 sync via `update.sh` succeeds; spec emits with no codegraph references.

## Track 3 — /research command redesign (DEFERRED)

See `REDESIGN-RESEARCH-PLAN.md`. Locked finding §1 = CBM discovery chain (`search_graph` → 0 hits → fall through to `search_code`). Tracks 1 + 2 should fold their relevant changes into the /research redesign rather than landing standalone.

## Recommended session order

Plan F COMPLETE requires: pipeline (DONE) + project-tier richness (DONE — Track 4 SHIPPED + CLOSED) + enforcement (Track 1 / F.11). Sequence:

1. **Track 1 (F.11 hooks)** — provides the enforcement leg. Hooks enforce CBM-first protocol for ALL consumer commands.
2. Track 2 (codegraph scrub) — small, mechanical, interleavable.
3. **Track 3 (/research redesign) — DEFERRED** per 2026-05-08 user direction.

Track 4 follow-ups (targeted retry, snippet-fidelity) NOT pursued — user closed Track 4 2026-05-09.

## When resuming

```bash
cd /Users/mykolakudlyk/Projects/ai-dev-team-forge
git status
git log --oneline -8
# Track 4 work landed at: 9577705 (Phase 1) → 36076a2 (Phase 2) → 70b547e (Phase 3); CLOSED.

# Track 1 baseline — confirm hook stubs still placeholder-only:
grep -l "F.11" src/ -r 2>/dev/null

# Track 2 baseline — stale codegraph refs:
grep -rn "agentic_context\|agentic_impact\|agentic_quality\|agentic_architecture" src/ scripts/ install.sh update.sh | grep -v __pycache__ | wc -l
```

Memory bookmarks (auto-loaded):
- `project_track4_phase1_2_3_shipped.md` — Track 4 closed; phase commits + scope summary
- `project_cbm_integration_plan_e.md` — Plan F status
- `project_codegraph_state_2026_05_06.md` — codegraph LLM-disabled
- `feedback_cbm_discovery_chain_search_graph_then_code.md` — locked discovery chain
- `project_post_codex_command_revision.md` — per-command revision pass context
