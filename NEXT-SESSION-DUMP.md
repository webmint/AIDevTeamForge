# Next-session work dump

State at hand-off: Plan F + 3a COMPLETE end-to-end, validated on testForge20 full-scale (148 docs / 0 failures). This file lists the deferred work picked up in a fresh session.

## Reading order at session start

1. `CLAUDE.md` (auto-loaded).
2. This file — pick a track below.
3. Track-specific plan (linked under each track).

## Track 1 — F.11 hooks (CBM-first enforcement)

**Source spec**: `CBM-INTEGRATION-PLAN.md` §F.11 (lines ~539-564). 4 hooks defined (placeholder only — scripts not authored, install.sh not wired):

| Hook | Event | Purpose |
|---|---|---|
| `cbm-code-discovery-gate` | PreToolUse on Read/Grep/Glob | Advisory: "consider `search_graph` / `agentic_context` / `search_code` before text search". Exit 0 (non-blocking) |
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

## Track 3 — /research command redesign (separate plan)

See `REDESIGN-RESEARCH-PLAN.md`. Locked finding §1 = CBM discovery chain (`search_graph` → 0 hits → fall through to `search_code`). Tracks 1 + 2 should fold their relevant changes into the /research redesign rather than landing standalone.

## Recommended session order

1. Track 2 (codegraph scrub) — small, mechanical, lands in 30-60 min. Frees Track 1 + 3 from inheriting stale refs.
2. Track 3 (/research redesign) — biggest design work; benefits from clean slate post-Track 2.
3. Track 1 (F.11 hooks) — depends on Track 3's discovery protocol being final, since hooks reference it.

Or invert if F.11 is the priority.

## When resuming

```bash
cd /Users/mykolakudlyk/Projects/ai-dev-team-forge
git status
git log --oneline -5
grep -rn "agentic_context\|agentic_impact\|agentic_quality\|agentic_architecture" src/ scripts/ install.sh update.sh | grep -v __pycache__ | wc -l   # baseline ref count
```

Memory bookmarks (auto-loaded):
- `project_cbm_integration_plan_e.md` — Plan F status (now COMPLETE)
- `project_codegraph_state_2026_05_06.md` — codegraph LLM-disabled
- `feedback_cbm_discovery_chain_search_graph_then_code.md` — locked discovery chain
- `project_post_codex_command_revision.md` — per-command revision pass context
