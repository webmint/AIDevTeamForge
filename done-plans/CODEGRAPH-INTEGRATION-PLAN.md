# CodeGraph Integration Plan — Parallel Track

**Status**: Plan only, not started. Parallel-track exploration.
**Branch**: TBD (not started). Primary work continues on `develop-2.0-init`.
**Relationship to primary**: This is a SECONDARY exploration track that does NOT block or modify primary `/generate-docs` work. It explores a graph-backed alternative architecture.

---

## Why this is a parallel track

**Primary track** (continues uninterrupted): current `/generate-docs` (LLM-based markdown), Steps 3.3.4 through 3.3.7 from `GENERATE-DOCS-PLAN.md`, methodology iteration on testForge20, multi-ecosystem validation gate.

**Parallel track** (this plan): fork `codegraph-rust`, add Vue support via Vue compiler integration, connect to SurrealDB, parse a demo project, evaluate whether the graph-backed approach produces better methodology results than markdown-backed.

**Promotion criterion**: parallel track promotes to primary IF (a) Vue support stable + (b) integration empirically pays off vs markdown-backed approach + (c) methodology produces measurably better results. Until then, primary continues.

**Failure handling**: if parallel track fails (Vue grammar too unstable, integration cost too high, methodology doesn't improve), primary continues unaffected. No sunk-cost commitment.

---

## Strategic context — discoveries from 2026-05-02/03 session

This plan emerged from a multi-hour design discussion. Key reframes captured:

### Discovery 1: Methodology is the deliverable, not artifacts

The framework's actual goal is **a methodology that produces better results** when working on real software. `/generate-docs`, the helper, the constitution, plan files — all are SCAFFOLDING for the methodology. Means, not ends.

Architectural decisions should be evaluated by **does this make the methodology produce better results on real work**, not by architectural purity or universality claims.

### Discovery 2: Graph DB > markdown for storage (with caveats)

For mechanical / structural data: graph DB wins on cost (~5-100× cheaper queries) and quality (deterministic AST extraction vs LLM 70% echo).

For semantic narrative (concern overview, hazards): roughly comparable; graph node fields can hold rich-text prose. Both formats work.

The earlier "markdown wins for narrative" position was overstated — graph node fields can store full paragraphs of prose. The trade-off is operational, not content-shaped.

### Discovery 3: SurrealDB beats SQLite + Neo4j

**SurrealDB** (32k stars, mature, multi-model, embedded mode supported) is the architectural sweet spot:
- File-based simplicity (like SQLite)
- Graph-native queries (like Neo4j)
- Vector / HNSW built in
- Embedded mode = no server overhead
- SurrealQL (SQL-like, LLM-friendly)
- Single Rust binary

**Surrealist** (1.3k stars) is the official GUI — graph visualization + query editor + schema designer. Useful for methodology debugging.

### Discovery 4: codegraph-rust — fork, don't adopt

**`Jakedismo/codegraph-rust`** (193 stars) is more mature than the TS version. Pure Rust. SurrealDB-backed. Hybrid search (vector + lexical + graph). MCP tools designed for Claude Code.

**But**: doesn't support Vue (.vue files), Svelte, JSX/TSX as distinct file types. Only 11 languages: cpp, csharp, go, java, javascript, php, python, ruby, rust, swift (no dedicated typescript file).

**Decision**: fork at a stable commit. Pin and maintain. Don't track upstream blindly. Selective merges from upstream.

### Discovery 5: Vue support via compiler, not grammar

**Don't write a tree-sitter-vue grammar**. Existing options are immature (`ikatyang/tree-sitter-vue` unmaintained, `xiaoxin-sky/tree-sitter-vue3` is WIP — 4 stars, no releases).

**Use Vue's official compiler**: `@vue/compiler-sfc` transforms SFCs to plain JavaScript with source maps. Authoritative parsing. Free Vue version updates. Same pattern works for Svelte (`svelte/compiler`), Astro (`@astrojs/compiler`), MDX, etc.

Implementation paths:
- **Path 1 (recommended)**: Node.js subprocess — Rust spawns `node` running `@vue/compiler-sfc`, gets compiled JS + source map, parses JS with tree-sitter-typescript, source-map-translates offsets back to original .vue file
- **Path 2**: WASM build of Vue compiler embedded in Rust binary
- **Path 3**: Rust port (less mature)

Trade-off: Node.js subprocess vs WASM. Subprocess is simplest; WASM avoids external Node dependency. Decision deferred until implementation.

### Discovery 6: Methodology splits cleanly into two layers

**Mechanical layer** (codegraph-rust + SurrealDB):
- File index, symbols, calls, imports, inheritance
- Tree-sitter for 11 supported languages
- Vue compiler integration for .vue files
- Stored in SurrealDB graph nodes/edges
- Vector embeddings for semantic search
- MCP query tools

**Semantic layer** (our methodology, LLM-driven, writes to same graph):
- Concern overview prose
- Hazards (LLM judgment)
- Usage examples + verbatim citations
- Consumer patterns
- Architecture narrative (Phase 4+ work)
- ADRs / memory archaeology (Phase 5+ work)
- Concern decomposition heuristic (concerns = substantive subfolders under src/)

Helper API stays Python; writes to SurrealDB instead of markdown setters. Spec discipline (verbatim citations, iterative review, audit format, memory rules) applies to both layers.

### Discovery 7: ~80% of `/generate-docs` reuses

Most methodology transfers. Only the storage backend changes. Detailed in §"What transfers" below.

---

## The integration architecture

```
┌──────────────────────────────────────────────────────────┐
│  Claude Code slash commands                              │
│  /generate-docs   /research   /constitute   /verify ...  │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  Helper API (Python)                                     │
│  - add-package, add-concern, add-hazard, etc.            │
│  - set-concern-overview, set-concern-tree (graph fields) │
│  - extract-snippet (verbatim citation validator)         │
│  - validate-package, validate-concern                    │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  SurrealDB (embedded, file-based)                        │
│  Schema:                                                 │
│  - Package, Concern, File, Symbol, Hazard nodes          │
│  - Contains, Imports, Calls, Inherits, HasHazard edges   │
│  - Rich-text fields for narrative content                │
│  - HNSW vector index for semantic search                 │
└─────────────────────────┬────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌────────────────────┐               ┌─────────────────────┐
│  codegraph-rust    │               │  LLM (via /generate │
│  (forked + Vue)    │               │  -docs Phase 3-5)   │
│                    │               │                     │
│  - tree-sitter     │               │  - Concern overview │
│  - 11 langs + Vue  │               │  - Hazards          │
│    compiler subp   │               │  - Usage examples   │
│  - Mechanical:     │               │  - Consumer pattern │
│    Files, Symbols, │               │  - Architecture     │
│    Imports, Calls  │               │    narrative        │
│  - HNSW vectors    │               │  - ADRs (Phase 5+)  │
│  - File watchers   │               │                     │
└────────────────────┘               └─────────────────────┘
        ↑                                   ↑
        │                                   │
        ▼                                   ▼
┌──────────────────────────────────────────────────────────┐
│  /research consumer                                      │
│  - MCP queries (predefined tools wrap SurrealQL)         │
│  - research_search, research_concern, research_callers,  │
│    research_impact, research_hazards, etc.               │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  Optional tooling                                        │
│  - render-docs CLI: SurrealDB → markdown export for      │
│    human reading / PR review                             │
│  - Surrealist: visual graph inspection (debug methodology│
│    issues; ad-hoc server-mode SurrealDB instance)        │
└──────────────────────────────────────────────────────────┘
```

---

## What transfers from current `/generate-docs`

### Strong reuse (~80% of methodology value)

| Component | Why it transfers |
|---|---|
| `detect_report.py` logic (Phase 1) | LLM-based language/framework detection. codegraph-rust parses but doesn't identify "this is Vue + Pinia + vue-router." |
| Spec discipline patterns | Verbatim citations, iterative writer-reviewer loop, audit format, helper-validates-shape. Methodology, not artifact. |
| Concern decomposition heuristic | "Substantive subfolder under src/" — methodology layer above raw file list. |
| Semantic content generation | LLM-generated overview/hazards/usage examples. codegraph-rust doesn't do this. |
| Constitution + memory rules | Methodology, orthogonal to storage. |
| Iteration-mode banner pattern | Empirical validation mechanism. Independent of backend. |
| `/research` consumer protocol | Backend changes; protocol persists. |
| Phase 0 pre-flight checks | Adapts to graph backend. |
| Phase 5 report format | Format-agnostic. |
| Verbatim citation discipline | Helper validates `--code-snippet` against `--cite-file` line range. Critical methodology piece. |
| Workflow orchestration (`/research → /specify → /plan → /breakdown → /execute-task`) | Each command targets the appropriate backend. |

### Partial reuse

| Component | Adaptation |
|---|---|
| `index_helper.py` | **Replace**. codegraph-rust builds richer index automatically. |
| `generate_docs_helper` setter API surface | **Adapt**. Setter NAMES + validation rules transfer; setters write to SurrealDB instead of markdown. |
| `_trace.py` | **Replace** with codegraph-rust's existing tracing OR adapt. |
| `_circuit.py` (doom-loop, invocation-budget) | **Adapt** — same patterns to graph-write operations. |
| Decomposition gate | **Adapt** — same heuristic, different validation target. |

### Replace entirely

| Component | Why replaced |
|---|---|
| Markdown rendering (skeleton render, render-package-doc) | Graph storage replaces. `render-docs` export tool is the human-side derivation. |
| State file (`.generate-docs-state.json`) | SurrealDB IS the state. |
| Tree-section setter logic (set-package-tree, set-concern-tree) | codegraph-rust populates file/symbol nodes. Tree section becomes derived from graph. |
| Per-entry filename echo (the 70% problem) | Disappears — codegraph-rust gives accurate symbol names + paths from AST. |

---

## What's MISSING from codegraph-rust + SurrealDB stack

### Critical missing pieces (must add)

| Missing | What we add |
|---|---|
| Semantic content generation (concern overview, hazards, usage examples, consumer patterns) | Helper API for LLM to write rich-text fields on graph nodes |
| Concern abstraction | Concern nodes, ConcernContains edges (Concern→File). Layer above raw file index. |
| Hazard tracking | Hazard nodes with category enum, description, citation. |
| Verbatim citation validation | Custom validator checks `--code-snippet` against `--cite-file` line range. |
| Markdown export tooling (`render-docs`) | Graph → markdown rendering for human/PR consumption. |
| Spec / command integration | `/generate-docs`, `/research`, `/constitute`, `/verify` slash commands. |
| Iteration-mode scoping | Single-package empirical mode vs multi-package full mode. |
| Schema extensions | Concern overview, hazard categorization, usage example, consumer pattern, dependency-with-purpose nodes. |

### Non-critical but valuable

| Missing | What we add |
|---|---|
| Memory archaeology + ADRs (Phase 5+) | Historical context extraction. |
| Constitution-aware validation | Project rules inform pattern detection. |
| Architecture narrative (Phase 4 work) | Cross-concern architectural decisions. |
| Multi-package iteration logic | Sequential per-package processing with shared state. |

### What codegraph-rust gives us free that we don't currently have

| Gain | Enables |
|---|---|
| Symbol-level reverse index (mechanical, accurate) | "Where is symbol X?" → instant graph query |
| Call graph | "What calls Y?" → graph traversal |
| Multi-hop queries | "Impact of changing Z?" → graph traversal |
| Vector + lexical hybrid search | Semantic search alongside structural |
| File watchers / auto-sync | Incremental updates |
| MCP tool surface | Pre-built tools for /research |
| Tier-aware indexing | Speed/depth trade-offs |

---

## Implementation plan — phases

### Phase A — Fork + Vue support (~3-4 weeks)

**A.1**: Fork `Jakedismo/codegraph-rust` at a stable commit. Pin to specific SHA. Document fork commit.

**A.2**: Vue compiler integration:
- Add Node.js subprocess driver to fork (or WASM build of `@vue/compiler-sfc`)
- Create `crates/codegraph-parser/src/languages/vue.rs` mirroring `javascript.rs` pattern
- Compile .vue → JS via Vue compiler + source map
- Parse compiled JS with existing tree-sitter-typescript / tree-sitter-javascript
- Translate source-map-derived offsets back to original .vue file positions
- Handle: `<script>`, `<script setup>`, `lang="ts"` vs `lang="js"`, multiple script blocks
- Tests against testForge20's `db-cse-ui-strata/apps/app-web/components/`

**A.3**: Verify Vue support empirically — run codegraph-rust against testForge20 with Vue support, compare graph extraction to current LLM extraction quality.

**Pass criterion**: Vue file extraction produces complete, accurate symbol nodes with correct citations to original .vue line ranges.

**Failure criterion**: grammar/compiler integration unstable enough that >20% of Vue files fail extraction. Falls back to "use codegraph-rust for non-Vue + LLM for Vue" hybrid.

### Phase B — SurrealDB schema + helper API (~3-4 weeks)

**B.1**: Schema extension on top of codegraph-rust's existing schema:
- `Concern` nodes (above File)
- `Hazard` nodes (with category enum)
- `UsageExample` and `ConsumerPattern` nodes (with verbatim citation)
- `DependencyWithPurpose` (extend dependency to include LLM-generated purpose annotation)
- Rich-text fields on Concern: `overview`, `architectural_role`
- Rich-text fields on Symbol: `description`, `role`
- Edges: `ConcernContains` (Concern→File), `HasHazard` (Concern→Hazard), `HasUsageExample`, `HasConsumerPattern`

**B.2**: Helper API (Python, mirrors current pattern but writes to SurrealDB):
- `graph_helper add-package --path P --name N`
- `graph_helper add-concern --package P --name N`
- `graph_helper set-concern-overview --concern C --text "..."`
- `graph_helper set-concern-tree --concern C --text "..."` (or auto-derive from graph)
- `graph_helper add-symbol --concern C --kind K --signature S --description D --code-snippet ... --cite-file F --cite-start S --cite-end E`
- `graph_helper add-hazard --concern C --category K --description D [--cite-file F --cite-start S --cite-end E]`
- `graph_helper validate-package`, `graph_helper validate-concern`
- `graph_helper extract-snippet --file F --start S --end E` (verbatim citation validator)

**B.3**: Validation discipline preserved:
- Verbatim citation: `--code-snippet` must match `extract-snippet --file F --start S --end E` (whitespace-normalized)
- Decomposition gate: every substantive subfolder must have a registered Concern
- Helper-owns-shape: setters validate field types, required-vs-optional

### Phase C — `/generate-docs` spec adaptation (~2-3 weeks)

**C.1**: Rewrite `/generate-docs` Phase 3 to target graph backend:
- Phase 3 step 1: load `.devforge/devforge.db` schema info
- Phase 3 setters: invoke `graph_helper` instead of markdown setters
- Concern decomposition: same heuristic; populates Concern nodes
- Concern slot-fill: same per-concern iteration; writes to Concern node fields

**C.2**: Methodology preservation:
- All current spec discipline (verbatim citations, helper-validates-shape, iterative writer-reviewer)
- Sentence-level hallucination check applies to graph-field content
- Memory rules apply unchanged

**C.3**: Iteration mode:
- Banner stays — empirical validation on single package before multi-package unlock
- Single-package mode: graph populated for one package; other packages untouched

### Phase D — `render-docs` markdown export (~1-2 weeks)

**D.1**: CLI tool `render-docs` that reads SurrealDB and emits markdown:
- One file per package: `docs/<package>/index.md`
- One file per concern: `docs/<package>/<concern>/index.md`
- Same structure as current /generate-docs output (Overview, Directory Structure, Tech Stack, Public Surface, Hazards, Usage Example, Consumer Pattern)
- Templates per node type

**D.2**: Triggers:
- Manual: `render-docs --package P` regenerates markdown for one package
- Auto: post-`/finalize` for the active feature's docs
- Optional: post-`/generate-docs` for the whole project

### Phase E — MCP server for `/research` (~1-2 weeks)

**E.1**: Build Python MCP server that wraps SurrealDB queries:
- `research_search <query>` — full-text + vector hybrid search
- `research_concern <name>` — concern node + outgoing edges
- `research_symbols --concern C` — symbols in a concern
- `research_callers --symbol S` — what calls this symbol (via Calls edges)
- `research_impact --symbol S` — transitive callers
- `research_dependencies --package P` — dependency graph
- `research_hazards --concern C` — hazards for a concern

**E.2**: Layer on top of codegraph-rust's existing MCP tools (`agentic_context`, `agentic_impact`, etc.) — extend or replace with `/research`-specific tool surface.

**E.3**: `/research` slash command consumes these MCP tools.

### Phase F — Empirical validation (~2-3 weeks)

**F.1**: Run new stack against testForge20:
- `/generate-docs` populates SurrealDB
- `render-docs` exports markdown for comparison with current docs
- Run on `db-cse-ui-strata/apps/app-web` with Vue support

**F.2**: Compare:
- Mechanical accuracy: codegraph-rust symbol extraction vs current LLM tree descriptions
- Wall-clock: graph populate time vs current /generate-docs time
- Token usage: build-time + projected /research read-time
- /research query examples (run query patterns; compare to current markdown grep approach)

**F.3**: Decision point:
- **If new stack produces better methodology results**: promote parallel track to primary. Markdown approach retired.
- **If new stack equivalent**: keep parallel as optional. Methodology iteration continues on either.
- **If new stack worse**: roll back. Document what didn't work. Primary continues unaffected.

### Total scope

| Phase | Weeks |
|---|---|
| A — Fork + Vue support | 3-4 |
| B — Schema + helper API | 3-4 |
| C — Spec adaptation | 2-3 |
| D — Markdown export | 1-2 |
| E — MCP server | 1-2 |
| F — Empirical validation | 2-3 |
| **Total** | **12-18 weeks** |

---

## Open decision points

1. **Helper API language**: Python (matches framework) vs Rust (extends codegraph-rust). **Recommendation: Python** — keeps spec discipline + LLM integration simple; Python helpers exec codegraph-rust as subprocess for graph writes.

2. **MCP server placement**: extend codegraph-rust's existing MCP tools OR build separate Python MCP server. **Recommendation: separate** — codegraph-rust's tools are Rust; our /research-specific tools live in Python alongside helpers.

3. **State file management**: single SurrealDB instance per project at `<install_root>/.devforge/devforge.db`. Replaces current state file.

4. **Migration story**: existing testForge20 markdown docs → import to SurrealDB OR regen from scratch. **Recommendation: regen** — methodology iteration anyway.

5. **Vue compiler integration**: Node subprocess vs WASM. **Recommendation: subprocess first** (Path 1); migrate to WASM (Path 2) if Node.js dependency proves unacceptable in deployment.

6. **Iteration mode banner removal**: stays as Step 3.3.6 validation gate from primary plan — but now the test target is "graph backend produces equivalent results AND mechanical layer is verifiably better."

7. **Upstream contribution**: contribute Vue compiler support back to codegraph-rust upstream OR keep as private fork. **Recommendation: contribute upstream once stable** — benefits mainline maintenance.

---

## Success criteria

The parallel track succeeds if all of:

1. **Vue support stable** — testForge20's `db-cse-ui-strata/apps/app-web` extracts cleanly via the new pipeline (every .vue file produces correct graph nodes with correct citations).

2. **Mechanical layer accuracy** — symbol extraction is verifiably more accurate than current LLM-based tree descriptions (zero filename echo on supported languages).

3. **Methodology preserved** — current discipline (verbatim citations, iterative writer-reviewer, audit format, memory rules) applies unchanged. Spec still works the same way for the LLM.

4. **/research read-cost reduction** — token cost per /research query meaningfully lower than markdown grep (target: 5-10× reduction).

5. **Wall-clock build time** — comparable or better than current /generate-docs (target: ≤30 min on testForge20).

6. **Newcomer test (per Step 3.3.6 methodology)** — fresh user reads `render-docs` output, answers 5-question test (what does this codebase do, major pieces, where to find X, gotchas, deps), scores ≥4 of 5.

If any of 1-3 fails: parallel track returns to drawing board. If 4-6 fail: parallel track optional, primary continues.

---

## Failure modes + handling

### Vue compiler integration too unstable
**Symptom**: Vue compiler subprocess crashes / source maps wrong / >20% Vue files fail extraction.
**Handling**: Fallback to LLM extraction for Vue files only. codegraph-rust handles non-Vue. Hybrid mechanical + LLM by file type.

### codegraph-rust upstream breaks fork compatibility
**Symptom**: upstream changes API; merging upstream becomes painful.
**Handling**: pin to current fork commit; defer upstream merges; revisit only when there's a clear benefit. Treat as effectively a hard fork.

### Schema extensions don't fit codegraph-rust's design
**Symptom**: adding Concern/Hazard nodes conflicts with codegraph-rust's schema assumptions.
**Handling**: separate SurrealDB tables; relations to codegraph-rust's tables via foreign-key-style links. Two co-located schemas in one DB.

### SurrealDB embedded performance issues
**Symptom**: SurrealDB embedded slower than expected on large projects.
**Handling**: switch to SurrealDB server mode locally (same DB, different deployment). Documented fallback.

### Methodology doesn't improve with graph backend
**Symptom**: empirical comparison shows no meaningful improvement in /research output quality vs markdown.
**Handling**: roll back. Document why. Primary continues. Track lessons in memory.

---

## Coordination with primary track

This plan does NOT modify:
- `GENERATE-DOCS-PLAN.md` Steps 3.3.4-3.3.7 (open --kind enum, tree-as-hints contract, multi-ecosystem validation gate, per-file docs deferred)
- Iteration-mode banner removal blocking on Step 3.3.6
- Current `/generate-docs` Phase 3 architecture
- Current spec discipline + memory rules
- Current `develop-2.0-init` branch progress

This plan ADDS a separate exploration:
- New branch (TBD, e.g., `feature/codegraph-integration`)
- Independent commits
- Independent timeline
- Promotion to primary only after empirical validation passes

If parallel track succeeds AND primary track has shipped Steps 3.3.4-3.3.7: promote graph backend as the canonical storage; current markdown approach retires.

If parallel track fails: discard branch. Primary unaffected.

If primary track ships first AND graph backend stalls: graph backend remains optional / future work; primary stays canonical.

---

## How to bootstrap this track (fresh session)

1. Read `CLAUDE.md` (project root) — canonical project instructions.
2. Read `SESSION-HANDOFF.md` — primary-track session state (still active).
3. Read this file (`CODEGRAPH-INTEGRATION-PLAN.md`) — parallel-track plan.
4. Auto-memory loaded automatically.
5. `git log --oneline -10` to see recent commits.
6. **Decision point**: which track to work on?
   - **Primary track**: Steps 3.3.4-3.3.7 from `GENERATE-DOCS-PLAN.md` — methodology iteration, multi-ecosystem validation, etc.
   - **Parallel track**: this plan — fork codegraph-rust, add Vue, integrate SurrealDB, validate empirically.
7. If parallel: create branch `feature/codegraph-integration`. Start Phase A (fork + Vue support).

---

## References

### Repos / tools
- [codegraph-rust](https://github.com/Jakedismo/codegraph-rust) — Rust codegraph fork to base parallel track on
- [SurrealDB](https://github.com/surrealdb/surrealdb) — multi-model embedded DB
- [Surrealist](https://github.com/surrealdb/surrealist) — official GUI for visualization / debugging
- [tree-sitter-vue3](https://github.com/xiaoxin-sky/tree-sitter-vue3) — WIP Vue grammar (NOT for adoption; reference only)
- [Vue compiler-sfc](https://www.npmjs.com/package/@vue/compiler-sfc) — official Vue SFC compiler

### Methodology references in this repo
- `GENERATE-DOCS-PLAN.md` — primary plan; Steps 3.3.4-3.3.7 outline upcoming work
- `SESSION-HANDOFF.md` — primary-track session state
- `CLAUDE.md` — project conventions + spec discipline rules
- Memory at `~/.claude/projects/-Users-mykolakudlyk-Projects-ai-dev-team-forge/memory/MEMORY.md` — pinned learnings

### Related architectural memory rules
- `feedback_helper_owns_shape_principle.md` — helper validates structure; LLM provides values
- `feedback_survey_prior_art_before_inventing_formats.md` — adopt or document divergence
- `feedback_no_underspecification_when_delegating.md` — agent briefs must be self-contained
- `feedback_zero_escape_hatch_policy.md` — discipline rules without carve-outs
- `project_schema_anchored_generate_docs.md` — pre-graph schema-anchored design intent

---

## Captured decisions and rationale (from session 2026-05-02/03)

### Why fork over adopt codegraph-rust
- Beta concern: 193 stars, active dev, but small community → upstream stability risk
- Vue gap: 14 supported langs but no Vue, Svelte, JSX/TSX, Kotlin, Dart
- Forking pins to known-good commit; we maintain Vue extension; selective upstream merges

### Why Vue compiler over tree-sitter-vue grammar
- tree-sitter-vue grammars are immature (1-3 month grammar engineering otherwise)
- Vue's official compiler is authoritative — handles all edge cases (script setup, lang attributes, multiple script blocks)
- Generalizes to Svelte, Astro, MDX (any framework with a JS-output compiler)
- Maintenance: bump dep version vs maintain grammar forever

### Why SurrealDB over Neo4j or SQLite
- Neo4j: server-based; ops cost; Cypher is excellent but framework's drop-in install is harder
- SQLite: file-based but not graph-native; multi-hop queries require recursive CTEs
- SurrealDB: embedded mode, graph-native, multi-model (graph + relational + vector + document), single Rust binary, mature (32k stars)

### Why hybrid mechanical + semantic layers
- Mechanical (tree-sitter / Vue compiler) handles what's mechanically derivable from AST — 100% accurate
- Semantic (LLM) handles what's NOT mechanically derivable — overview, hazards, usage examples
- Empirical evidence (Run 4): LLM-as-mechanical at scale produces 70% filename echo. Don't ask LLM to do mechanical work.
- Concentrate LLM effort on semantic; outsource mechanical to deterministic extractors.

### Why parallel-track instead of pivot
- Primary methodology validated on Vue/TS via current /generate-docs
- Pivoting wholesale = high risk; methodology may regress on Vue
- Parallel = low risk; primary unaffected; explore + validate before promoting
- Promotion criterion: empirical evidence that graph backend produces better methodology results

### Why methodology > artifacts
- Goal: methodology that produces better results on real software development
- /generate-docs, helpers, plans, constitutions = scaffolding
- Architectural decisions evaluate by "does this produce better results?" not "is this universal / clean / pure?"

---

## Final note

This plan is exploratory. Treat it as a hypothesis: the graph-backed approach will produce better methodology results on real work than the markdown-backed approach. Validation gates (Phases A.3, F.1-F.3) test the hypothesis empirically. If validated, promote. If not, discard. Either way, primary methodology continues unaffected.

**The plan is open to revision.** New discoveries during implementation may invalidate decisions captured here. Keep this document live; update as the track progresses.
