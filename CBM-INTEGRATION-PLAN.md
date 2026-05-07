# CBM Integration Plan — Plan E (codebase-memory-mcp + sourcemap bridge)

**Status (2026-05-07)**: Approved, not started. Successor architecture to Part D for /generate-docs concern-fill scaling.
**Branch**: continues on `develop-2.0-init`.
**Predecessors**:
- `VALIDATOR-LOOP-PLAN.md` (Part A, frozen).
- `VALIDATOR-LOOP-B-PLAN.md` (Part B, retired; Part D revert documented inline).
- Active /generate-docs flow = Part D (commit `ddda751`): single-dispatch-per-concern with orchestrator-direct per-export composition. Verified on testForge20 helpers concern: 16 min wall-clock, output quality good, public_surface 8/61 (curated subset, not complete).

## Why Plan E

Empirical signal from Part D testForge20 helpers run:
- 16 min wall-clock for ONE concern (61 files, 8 public_surface entries). Bulk of time = orchestrator-direct per-export description composition (LLM call per export despite "single dispatch" framing for tree).
- Linear projection across all 8 substantive concerns of app-web: ~130-220 min (~2-4 hr) per full pass. Subscription-window borderline.
- Public surface coverage gap: 8 of 61 files contained exports but only 8 entries surfaced — LLM-curated subset, not mechanical completeness. Consumers don't see full API surface.
- Per-export LLM calls = same architectural shape as Part B per-md. Solving one quota burn vector creates another.

Plan E corrects the architecture: **ONE LLM dispatch per concern, period**. Anything requiring LLM judgment for that concern goes IN that single dispatch. Mechanical fields come from codebase-memory-mcp graph queries. Sourcemap resolution applied for Vue cite-back.

Result projection:
- testForge20 full-app pass: ~8-15 min total (down from 130-220 min)
- Per-concern wall-clock: ~30-180s
- Quota burn: minimal (~80-240K tokens per full app run)
- Public surface coverage: mechanical complete (every export imported by code outside the concern's subfolder)

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│ /generate-docs Phase 3 step 10 (per-concern slot-fill)   │
└─────────────────────────────┬────────────────────────────┘
                              │
       ┌──────────────────────┼──────────────────────┐
       │                      │                      │
       ▼                      ▼                      ▼
  E.2 query-concern    E.3 concern-composer    E.4 orchestrator
  forge helper         Task subagent           parses output, calls
                                               N setters mechanically
  - calls CBM MCP      - input: batch JSON
    tools (search_     - output: 7 sections   E.4 per setter:
    graph, query_      (overview, tree,         set-concern-overview,
    graph, get_code_   exports, types, deps,    set-concern-tree,
    snippet)           hazards, usage_example)  add-concern-export
  - applies E.1                                 (xN; no LLM per call),
    sourcemap                                   add-concern-type,
    resolution to                               add-concern-dep,
    .vue.ts cites                               etc.
  - returns batch
    JSON
```

## Components

### E.1 — Python sourcemap V3 consumer

Location: `src/devforge/lib/_generate_docs/_sourcemap.py` (new module).

API:
```python
class SourceMap:
    version: int
    sources: List[str]
    sources_content: Optional[List[str]]
    mappings: str  # raw VLQ string

def parse_sourcemap(text: str) -> SourceMap
def apply_mapping(sm: SourceMap, gen_line: int, gen_col: int = 0) -> Tuple[str, int, int]
    # Returns (original_file_path, original_line, original_col)
    # Raises MappingNotFoundError if no mapping covers (gen_line, gen_col)
```

Implementation: stdlib only. `json` parses the .map JSON. Custom VLQ decoder (~60 lines: base64 → 5-bit groups → signed integers). `mappings` field decoded into per-line segment lists; binary-search finds nearest mapping for query position.

Test scope (`tests/lib/test_sourcemap.py`):
- Round-trip via real vue-to-ts output: parse the .map vue-to-ts emits, apply to known generated-positions, verify original-positions match (e.g., header offset = 7, .vue.ts:8 first import → .vue:2)
- VLQ decode: known values (e.g., `AAAA` → [0,0,0,0])
- Reject malformed: missing version, malformed mappings, sources length mismatch
- Boundary: line beyond mappings → MappingNotFoundError
- Multi-source map (sources length > 1) — defer to v0+1; v0 supports single-source only (vue-to-ts always emits single-source)

#### Verify E.1
- `tests/lib/test_sourcemap.py` — ≥10 cases all green
- Manual: parse a real `.vue.ts.map` from testForge20's `.vue-tmp/`, apply to a known node from codebase-memory-mcp's graph, verify cite resolves to original `.vue` line

---

### E.2 — Forge helper `query-concern`

Location: `src/devforge/lib/_generate_docs/_cbm_query.py` (new module).

CLI signature:
```
generate_docs_helper query-concern --package P --concern C [--vue-extract-dir D]
```

Behavior:
1. Resolve concern's source subfolder: `<package>/src/<concern>/`.
2. Spawn codebase-memory-mcp via stdio (JSON-RPC) OR shell out to its CLI mode (verify which path is supported by the binary).
3. Issue queries:
   - `search_graph(file_pattern='<subfolder>.*')` for file enumeration
   - `query_graph(cypher)` for cross-concern import discovery (exports in subfolder imported from outside)
   - `get_code_snippet(qualified_name)` per cross-concern export for verbatim snippet + cite range
   - `query_graph(cypher)` for types defined in subfolder
   - `query_graph(cypher)` for dependencies imported BY subfolder (npm/cargo/etc.)
4. For each cite returned by graph that points at a `.vue.ts` file:
   - Locate the corresponding `.vue.ts.map` in `--vue-extract-dir` (or `<concern>/.vue-tmp/` auto-detect)
   - Apply E.1 sourcemap resolution → original `.vue` path + line
   - Replace cite-file/cite-start/cite-end in returned data with original-`.vue` values
5. Output to stdout: batch JSON containing all mechanical fields ready for concern-composer dispatch.

JSON shape:
```json
{
  "concern": "helpers",
  "subfolder": "apps/app-web/src/helpers/",
  "subfolder_files": ["apps/app-web/src/helpers/calculatePrice.ts", ...],
  "public_surface_candidates": [
    {
      "name": "checkUserWebRoles",
      "kind": "function",
      "signature": "(userRoles?: UserRoles[]) => boolean",
      "cite_file": "apps/app-web/src/helpers/checkUserWebRoles.ts",
      "cite_start": 4,
      "cite_end": 13,
      "code_snippet": "export default function checkUserWebRoles...",
      "imported_by": ["apps/app-web/src/components/auth/RoleGuard.vue", ...]
    },
    ...
  ],
  "types_in_concern": [...],
  "dependencies_imported": [...],
  "sibling_concern_overviews": {...}
}
```

Exit codes:
- 0: success
- 2: validation failure (package/concern not registered, MCP server unreachable)
- 5: graph data error (concern not indexed, malformed sourcemap)

Test scope (`tests/lib/test_cbm_query.py`):
- Mocked codebase-memory-mcp responses: confirm batch JSON shape
- Sourcemap resolution applied to .vue.ts cites
- Graceful degrade if MCP unreachable (exit 2 with diagnostic, not crash)
- Vue cite resolution: `.vue.ts:15` → `.vue:3` (header offset accounted)

#### Verify E.2
- New test file ≥8 cases
- End-to-end smoke against testForge20 (post-vue-extract): query helpers concern → verify batch JSON contains 30+ exports (vs Part D's curated 8) with original `.vue` paths where applicable

---

### E.3 — New agent `concern-composer`

Location: `src/agents/concern-composer.md` (new file).

Frontmatter:
```yaml
name: concern-composer
description: "Single-dispatch concern documentation composer for /generate-docs Phase 3. Receives batch JSON from query-concern helper (CBM graph data + sourcemap-resolved cites), emits all 7 concern doc sections (overview, tree, exports, types, deps, hazards, usage_example) in one assistant message. Orchestrator parses sections into N setter calls. Replaces orchestrator-direct per-export LLM composition. Cost: 1 dispatch per concern."
model_tier: think
tools: Read, mcp__codebase-memory-mcp__search_graph, mcp__codebase-memory-mcp__query_graph, mcp__codebase-memory-mcp__get_code_snippet, mcp__codebase-memory-mcp__trace_path, mcp__codebase-memory-mcp__get_architecture, mcp__codebase-memory-mcp__search_code
```

Note: model_tier=think (Sonnet) — composing 7 sections with cross-references requires fuller judgment than scan-tier. Empirically tune downward to scan if Sonnet output proves over-spec.

Tool allowlist explanation:
- CBM tools: primary research surface (no Read/Grep/Glob fallback that hooks would block anyway)
- Read: ALLOWED but only for verification reads after CBM call (120s window per cbm-code-discovery-gate hook). Subagent should not need it but kept as escape valve.
- NO Bash (no helper invocation from subagent; orchestrator parses output and calls setters)

Output contract: 7-section structured Markdown emitted as final assistant message. Sections delimited by `## OVERVIEW`, `## TREE`, `## EXPORTS`, `## TYPES`, `## DEPENDENCIES`, `## HAZARDS`, `## USAGE_EXAMPLE`. Orchestrator parses each section.

Annotation discipline rules: same banned phrases / specificity / vs-siblings / negative-space rules from tree-annotator (Part D), now applied to ALL sections in batch.

#### Verify E.3
- Spec authored via instruction-author + claude-code-guide (per `feedback_dual_agent_verify_command_statements`)
- Sample dispatch on testForge20 helpers: input = E.2 batch JSON, output = 7 sections; orchestrator parses cleanly

---

### E.4 — /generate-docs Phase 3 step 10 spec rewrite

Replace Part D "Tree composition (single dispatch per concern)" block with Plan E flow:

```markdown
**Concern composition (Plan E — single batched dispatch per concern).** For each concern:

1. Invoke `query-concern --package P --concern C` helper. Captures graph-derived
   mechanical fields + sourcemap-resolved cites in batch JSON.
2. Dispatch `concern-composer` Task subagent with batch JSON as input. Subagent
   emits 7-section Markdown response.
3. Parse subagent output into 7 sections.
4. Invoke setters mechanically (no LLM per setter):
   - set-concern-overview --text "<OVERVIEW section>"
   - set-concern-tree --text "<TREE section>"
   - For each line in EXPORTS section: add-concern-export --name X --description Y
     --code-snippet Z --cite-file F --cite-start S --cite-end E
   - For each line in TYPES section: add-concern-type ...
   - For each line in DEPENDENCIES section: add-concern-dep ...
   - For each line in HAZARDS section: add-concern-hazard ...
   - set-concern-usage-example with USAGE_EXAMPLE section content
5. Invoke validate-concern. On failure: capture stderr verbatim, re-dispatch
   concern-composer with stderr as previous_attempt_feedback. Cap at 3 attempts.
6. Invoke render-concern-doc.
```

Cost gate (subscription-aware framing per `feedback_avoid_command_model_override` informed memory):
- Pre-dispatch: print expected dispatches per concern (1 think-tier + retries) + token estimate (~10-30K input + ~5-10K output per concern)
- Single AskUserQuestion: `Proceed with concern composition for <C>? (yes/no)`

Removed from Part D spec:
- Orchestrator-direct per-export source-reading + composition (replaced by graph queries + batch dispatch)
- Per-tree-entry annotation discipline prose (rolled into concern-composer's annotation-rules section)

#### Verify E.4
- Spec change reviewed by instruction-author + instruction-reviewer
- claude-code-guide verifies agent dispatch + MCP tool conventions

---

### E.5 — Hook installation reference

User-installed hooks at `~/.claude/hooks/` per the sgaabdu4/claude-code-tips pattern:
- `cbm-code-discovery-gate` (PreToolUse, matches Read/Grep/Glob)
- `cbm-mcp-marker` (PostToolUse, matches Bash + MCP)
- `cbm-session-reminder` (SessionStart, resume/clear/compact)
- `bash-ban-raw-tools` (PreToolUse, matches Bash)

These hooks ENFORCE the CBM-first protocol. Without them, Claude can fall back to Read/Grep on source files; with them, it must use CBM unless escape hatch invoked.

For AIDevTeamForge users running /generate-docs:
- Optional: framework's `install.sh` ships hook reference scripts to target's `.claude/hooks/` (presence-guarded; user opts in via wizard prompt)
- Mandatory: framework's `CLAUDE.md` template documents the hook pattern with a "Strongly recommended for /generate-docs" note

Default for v0: don't auto-install hooks. Document in CLAUDE.md template + concern-composer agent's body. Hook adoption is user choice.

#### Verify E.5
- CLAUDE.md template documents hook pattern + linkbacks to sgaabdu4 source
- concern-composer agent body has explicit "use CBM tools, not Read/Grep" directive (defensive when hooks not installed)

---

### E.6 — Empirical verification on testForge20

After E.1–E.5 ship:

1. Reset testForge20 state (full).
2. update.sh syncs E.1–E.4 helpers + spec + agent.
3. Re-index testForge20 with codebase-memory-mcp (post vue-to-ts pass; verify Function nodes from .vue.ts are queryable).
4. Run /generate-docs with TEST SCOPE OVERRIDE = helpers concern. Capture metrics:
   - Dispatch count: 1 (concern-composer) + 0-2 retries
   - Wall-clock for helpers concern: target <2 min (vs 16 min Part D)
   - Public surface coverage: target ≥30 entries (vs 8 Part D)
   - Token cost: target <50K total
5. Read rendered helpers/index.md. Compare quality vs Part D baseline (commit `ddda751`).
6. If pass: remove TEST SCOPE OVERRIDE; run full app-web. Target: ~10-15 min total wall-clock for all 8 concerns.

#### Verify E.6
- Helpers run: 1-3 dispatches; wall-clock <2 min; coverage ≥30 surface entries; quality ≥ Part D baseline
- Full app-web run: ~10-15 min total; ≤8 dispatches + retries; all concern docs rendered; package doc rendered (no skeleton remains)

---

## Disposition of prior work

| Artifact | Disposition under Plan E |
|---|---|
| Part D `tree-annotator` agent | Deprecated in active flow; replaced by `concern-composer`. KEEP file for reference / future revival path. |
| Part D Phase 3 step 10 "Tree composition" block | Replaced by E.4 flow |
| Part D TEST SCOPE OVERRIDE | KEEP as test-mode primitive; same mechanism applies under Plan E |
| Part B per-md helpers + tests | KEEP dormant. Plan F could re-enable per-md as opt-in for richer file-level docs once concern composer batch shape is proven. Per-md fill becomes ONE additional dispatch per concern (composer emits per-md content + setter calls in same batch). |
| `_md_frontmatter.py` | KEEP — generic util |
| Vue source map fix + walk-down resolver in `vue-to-ts.mjs` | KEEP — required for E.2 sourcemap resolution |
| `vue-extract` launcher | KEEP — primary user invocation for vue-to-ts pre-pass |
| `_check_file_docs_complete` rule | KEEP dormant. Revivable if/when Plan F (per-md revival) lands. |

## Risks + open questions

1. **MCP server invocation from forge helper.** codebase-memory-mcp speaks MCP stdio JSON-RPC. Forge helper is Python. Either (a) spawn MCP server subprocess + speak protocol from Python (~200 lines client), (b) shell out to a CLI mode if the binary supports it, (c) orchestrator (Claude Code) does MCP queries, passes results to forge helper as JSON. Option (c) cleanest — orchestrator already has MCP access via Claude Code's harness; helper just receives JSON, applies sourcemap resolution, returns enriched JSON. Defer (a) implementation to v0+1. Test: verify CLI mode availability of codebase-memory-mcp binary.

2. **Sourcemap multi-source maps.** vue-to-ts emits single-source maps. If toolchain ever emits multi-source (e.g., post-bundling), E.1 must support sources length > 1. v0 rejects multi-source with explicit error. Defer to v0+1.

3. **Cite-file paths after sourcemap resolution.** Map's `sources[0]` is path RELATIVE to .map dir. E.2 must canonicalize to project-root-relative for downstream cite-validate. Verify via end-to-end smoke.

4. **Subagent context budget.** concern-composer ingests batch JSON (potentially 30-50K input tokens for components concern). Sonnet's 200K context fine, but cost per dispatch grows. Monitor in E.6 empirical.

5. **Retry feedback shape.** validate-concern can fail on MULTIPLE rules (e.g., banned phrase in 3 export descriptions + 1 cite mismatch). concern-composer must accept multi-error feedback, not just single-error. E.4 spec wording must mandate verbatim full-stderr injection.

6. **Vue files with NO `<script>` block.** vue-to-ts emits a stub `.vue.ts` with `export default {}`. codebase-memory-mcp indexes the stub. Graph returns no Functions for these. concern-composer should still emit tree entry + filename-inferred description; not crash on empty graph data.

7. **Hook installation rollout.** Framework auto-install may surprise users who already have other hooks at `~/.claude/hooks/`. Manual opt-in (CLAUDE.md doc only) is safer for v0. Revisit in v0+1 with `--with-hooks` install.sh flag.

8. **Glossary tier (Plan F?) under codebase-memory-mcp.** Mechanical term/symbol extraction free via graph; LLM single-dispatch fills definitions. Same architectural shape as concern-composer. Plan F's single-dispatch per project covers it. Out of Plan E scope.

## When resuming work

1. Read `CLAUDE.md` (project root, auto-loaded).
2. Read `VALIDATOR-LOOP-PLAN.md` (Part A history, frozen).
3. Read `VALIDATOR-LOOP-B-PLAN.md` (Part B retired + Part D revert note).
4. Read this file (Plan E, active).
5. Read `SESSION-HANDOFF.md` if it exists (most recent snapshot).
6. Determine current step:
   - E.1 not started → start with sourcemap consumer
   - E.2 in progress → continue forge helper
   - etc.
7. Files NOT to delete (Part D + Plan E both reference):
   - `src/agents/tree-annotator.md` (Part D agent; reference for concern-composer)
   - `src/devforge/lib/_generate_docs/_md_frontmatter.py` (generic util)
   - `src/devforge/lib/_generate_docs/_setters_concern_files.py` (per-md helpers, dormant)
   - `src/devforge/lib/_generate_docs/_validators_file_doc.py` (per-md validators, dormant)
   - `src/devforge/lib/vue-to-ts.mjs` + `vue-extract` launcher
8. Run full test suite at every step; baseline 907 OK + 3 skipped (post-Part-D revert).
9. clear `src/devforge/.generate-docs-trace.log` before each test run (circuit-breaker invocation budget).

## Memory bookmarks (for fresh-session resume)

After Plan E approved, add a memory entry:
- `project_cbm_integration_plan_e.md` — pointer to this plan + status

After E.1 lands, update memory:
- `project_cbm_integration_plan_e.md` — status updated to "E.1 done; E.2 next"

Same pattern for each subsequent step. Memory provides cross-session continuity beyond the plan file.

## References

- `VALIDATOR-LOOP-PLAN.md` — Part A history (annotations-in-state, retired)
- `VALIDATOR-LOOP-B-PLAN.md` — Part B history + Part D revert note
- `tools/vue-to-ts.mjs` source map fix (commit `fc5fad8`) + walk-down resolver (commit `b5e2a3a`)
- `vue-extract` launcher (commit `f2c4631`)
- Part D revert (commit `ddda751`)
- TEST SCOPE OVERRIDE for testForge20 (commit `d49be3a`)
- sgaabdu4/claude-code-tips: hook pattern reference for CBM enforcement
- codebase-memory-mcp: https://github.com/DeusData/codebase-memory-mcp
- Memory rules: `feedback_helper_owns_shape_principle.md`, `feedback_zero_escape_hatch_policy.md`, `feedback_iterative_review_loop_preferred.md`, `feedback_test_first_python_helpers.md`, `feedback_dual_agent_verify_command_statements.md`, `feedback_avoid_subagents_for_sequential_identical_workflows.md` (Plan E REVERSES this for batch dispatch — single subagent per concern is the correct primitive when input is large + structured)
