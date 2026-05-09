# JUDGMENT-LAYER-PLAN — final md-tier enhancements to `/generate-docs`

## Status

**This is the final feature enhancement plan for `/generate-docs`.** After both tracks below ship + cross-file refs land, `/generate-docs` is closed for further feature work. Only bug-fixes, validator tightenings, and CBM-API-evolution adjustments accepted thereafter. Future LLM-judgment retrieval surfaces (e.g., topic-index, reverse-index, pattern-catalog) are explicitly rejected per the docs+CBM split argument below — closing the door now prevents future sessions from re-litigating.

Two judgment-layer artifacts ship together via this plan:

| Track | Output | CBM dep | Lifecycle slot |
|---|---|---|---|
| **A** — Suggested Research Starts | section IN `docs/overview.md` (between Entry Points + Key Commands) | none | inside project-overview phase |
| **B** — Glossary | new file `docs/glossary.md` | yes — `query_graph`, `search_graph`, `get_code_snippet` | new Phase B at end of `/generate-docs` |

Both are pure md-tier judgment (definition phrasing, question scoping, cross-references). Neither duplicates CBM structural verbs.

## Why (shared)

Three retrieval gaps in current `/generate-docs` output that LLM consumers (today's sessions, future `/research` / `/specify` / `/plan` / `/breakdown`) hit:

1. **Cold-start orientation** — a fresh session reading `docs/` lacks scenario seeds. `## Entry Points` lists files; doesn't list "what scenarios to trace." Track A fills this.
2. **Term disambiguation** — PascalCase / camelCase identifiers appear in concern doc `## Purpose` paragraphs (`InMemoryRepository`, `CoreFamily`, `provideFamilyBLoC`) without a one-stop lookup. Track B fills this.
3. **Drift detection** — terms in narrative docs whose code symbols were renamed/removed are invisible today. Track B's combined-pipeline classification surfaces them as `code-stale`.

## Why not topic-index / reverse-index / pattern-catalog (Track B Steps 6.4 / 6.2 / 6.6 from GENERATE-DOCS-PLAN.md)

Rejected. Those artifacts answer **structural queries** ("which docs reference file X?", "what's the canonical implementation of pattern Y?", "fuzzy intent → file map") that CBM already answers live via `search_graph`, `get_architecture`, `query_graph`. Precomputing them into `docs/` violates the Plan F principle codified in `src/CLAUDE.md:270`: "structural queries live in CBM, not docs/."

This plan's two artifacts pass that test:
- **Suggested Research Starts** = LLM-curated scenario questions (judgment, not structure)
- **Glossary** = term definitions in prose with code anchors (judgment about meaning, not structural query)

The "do NOT reference codegraph's `agentic_*` tools" prohibition (`src/CLAUDE.md:182`) is the same principle — defer structural queries to live tooling.

## Context for next session

- **Track 4 (project-tier shape) shipped + CLOSED** (3dc425c). This plan is scope-distinct: adds NEW artifacts, not richer content within existing sections.
- **Plan F + memory `project_cbm_integration_plan_e`** lock the docs+CBM split. Both tracks respect it.
- **CBM empirical state on testForge20** (verified 2026-05-09):
  - 15,413 nodes; 26,709 edges; 2,946 File nodes; 709 Section nodes
  - Md files indexed end-to-end (concern docs, overviews, architectures, structure, READMEs, framework docs)
  - Section nodes derived from md headings, **heading-line only** (`start_line == end_line`); body spans computed by helper via filesystem read between consecutive Section start_lines
  - `f.docstring` property exists in schema for Function / Method / Class / Interface / Type but is **empty across both indexed projects** (Python forge AND TS testForge20). Track B cannot query CBM for docstrings; must read source via `get_code_snippet(qualified_name)` when definitions need code-anchor context.
  - BM25 `search_graph(query="...")` works for fuzzy term lookup
  - Cypher subset: MATCH / WHERE / RETURN / COUNT / DISTINCT / ORDER BY / LIMIT (no WITH / COLLECT / OPTIONAL MATCH / IS NOT NULL)
- **Lifecycle**: CBM auto-sync watcher absorbs `/generate-docs` writes — manual reindex on testForge20 post-Track-4-run was a no-op (`changed=0 unchanged=2947`). Explicit `index_repository` between Phase A and Phase B is OPTIONAL belt-and-suspenders, not required.
- **/init-forge index trigger** (memory `project_4command_architecture_pivot`): /init-forge does NOT currently trigger `index_repository`. Track B pre-req is to add the trigger (small separate commit before B.1) OR have helper detect missing index and shell out to CBM CLI as fallback. Default: pre-req commit.

## Shared engineering substrate (Step 0)

Step 0 ships TWO additions in one commit:

### (a) New module `src/devforge/lib/_generate_docs/_doc_corpus.py` (~120 LOC)

| Function | Purpose |
|---|---|
| `walk_doc_corpus(docs_root)` | enumerate `docs/**/*.md`; return list of `(rel_path, frontmatter, body)` |
| `extract_term_occurrences(corpus)` | regex `[A-Z][a-zA-Z0-9]+` (PascalCase) + `[a-z]+[A-Z][a-zA-Z0-9]*` (camelCase) + `[A-Z]+(_[A-Z]+)+` (ALL_CAPS_SNAKE); skip fenced code blocks, frontmatter, table headers; return `{term: [(rel_path, line, ±2-sentence-context)]}` |
| `validate_cite_paths(paths, project_root)` | per path → `os.path.exists()`; return `(ok, missing[])`; both tracks reuse for cite-back validation |
| `get_section_body_span(file_path, section_start_line)` | helper for future tracks needing section body — computes (start, next_section_start - 1) by sorting Section nodes per file |
| `noise_filter(terms, override_path=None)` | strip framework names from baseline list (Vue, Pinia, GraphQL, Promise, …); merge with optional `.devforge/glossary-noise.txt` |

Both tracks import from this module. Track A uses `extract_term_occurrences` + `validate_cite_paths`; Track B uses all four. ~80 LOC reuse vs separate plans.

### (b) Enhance `_merge_project_skeleton` for declared-order insertion of missing anchors

**Problem**: existing merge logic (`src/devforge/lib/_generate_docs/_doc_setters.py:242`) appends missing owned anchors at END of body, not at their declared position in the `_PROJECT_OVERVIEW_OWNED_ANCHORS` tuple. When Track A adds `Suggested Research Starts` between `Entry Points` and `Key Commands` in the tuple, re-runs on already-doc'd projects (e.g., testForge20) would land the section at the END of overview.md (after `Packages`), not in declared position.

**Fix** (~30 LOC): inside `_merge_project_skeleton`, when an owned anchor is missing from existing body, scan the declared tuple AFTER the missing anchor for the FIRST anchor that DOES exist in the body; insert the missing anchor (with placeholder) immediately before that one. If no later anchor exists in the body (anchor is last in declared order or all later anchors are also missing), fall through to current append-at-end behavior.

**Cold-start path unchanged**: `_build_project_overview_skeleton` already emits all anchors in declared order in the fresh skeleton; cold start has no merge phase.

### Tests

`tests/lib/test_doc_corpus.py` (~15 cases) — extraction edge cases, fenced-code skip, frontmatter skip, noise filter, cite-path validation, section span computation.

Extend `tests/lib/test_doc_setters_project_merge.py` (~5 new cases) — declared-order insertion: (1) missing-middle anchor inserted before next-existing, (2) missing-last anchor falls through to append, (3) all-missing series inserted contiguously before next-existing, (4) cold-start unchanged, (5) multi-anchor missing-then-existing-then-missing pattern.

Ship as one commit `feat(generate-docs): _doc_corpus substrate + declared-order merge for judgment-layer tracks`.

## Lifecycle (shared)

```
T0 install:
  /init-forge → index_repository ONCE (pre-req commit ahead of Track B)
  auto_index=true → CBM watcher running thereafter

Tn /generate-docs run:
  Phase 1-N (existing): per-concern → per-package → project-overview → project-architecture
  
  Track A fires INSIDE project-overview phase, after Module Map step,
  before Key Commands step. Pure md-judgment, no CBM read.
  Watcher absorbs the overview.md write.

  Phase A→B barrier: OPTIONAL `index_repository` (helper shells out to
  CBM CLI; ~1-5s on testForge20-scale; deterministic). Default: skip,
  trust watcher. Add `--reindex-before-glossary` flag for paranoid runs.

  Phase B (new — Track B):
    helper builds glossary bundles via query_graph + search_graph
    LLM defines terms (orchestrator-direct slot-fill)
    helper validates + renders docs/glossary.md
    watcher absorbs glossary.md write
    docs/glossary.md becomes File + Section nodes on next CBM index pass

Refresh on code change:
  rerun /generate-docs
  source_stamp incremental skip for narrative docs (already implemented per Track 4)
  Track A re-runs always (cheap — 1 LLM call)
  Track B re-runs always (full rebuild v1; term-cache deferred to v2)
```

## Track A — Suggested Research Starts

### Output shape

Section inserted into `docs/overview.md` between `## Entry Points` and `## Key Commands`:

```markdown
## Suggested Research Starts

| Question | Scope hint | Start here |
|---|---|---|
| How does a quote line propagate cart → finalize → DOCX export? | active-quote BLoC + quoteFinalize + quotePrint | `router/routes/quote.ts`, `router/routes/quoteFinalize.ts`, `router/routes/quotePrint.ts` |
| Where does Okta auth state reach route guards? | Okta plugin → multiguard chain | `plugins/okta.ts`, `router/index.ts` |
```

Empty list → section omitted (no empty header).

### State + validation

**Skeleton file IS the state** per `_doc_setters.py:22-31` architecture. No separate JSON file. Setter consumes JSON list on stdin (matching existing setter precedent at `cmd_set_overview_entry_points`, `_doc_setters.py:1349+`), validates inline, replaces `<!-- TODO: suggested-research-starts -->` placeholder in `overview.md.skeleton` with rendered markdown table.

Validator (helper-enforced, exit 2 on failure):
- count: `3 ≤ N ≤ 6`
- `question` non-empty, ends `?`, ≤140 chars
- `scope_hint` non-empty, ≤140 chars, no newlines
- `cite_paths` ≥2 entries, each `os.path.exists()` true (uses `_doc_corpus.validate_cite_paths`)
- no duplicate questions (case-insensitive)
- exit 1 on I/O failure (file write / placeholder substitution failure)

### Phased steps

| Phase | Scope | Files touched |
|---|---|---|
| **A.1** helper | Add `("Suggested Research Starts", _SUGGESTED_RESEARCH_STARTS_PLACEHOLDER)` to `_doc_setters.py:~225` placeholder ordering; append section header to skeleton template at `_doc_setters.py:~315`; new `cmd_set_overview_suggested_research_starts` near the existing entry-points setter (~`_doc_setters.py:1349`); register in `_cli.py` SUBCMDS table (~`_cli.py:498`). | `_doc_setters.py`, `_cli.py`, `tests/lib/test_doc_setters_project.py` (~13 new test cases) |
| **A.2** spec | Add new step to project-overview phase in `src/commands/generate-docs/main.md` after Module Map step; orchestrator-direct LLM-judgment dispatch (Phase 3 Option B precedent). Cross-check: helper subcommand list in spec/references gets `set-overview-suggested-research-starts`. | `src/commands/generate-docs/main.md` |
| **A.3** empirical + cross-refs | Run `/generate-docs` on testForge20; verify 3–6 entries with cite_paths resolving; cross-file note in `src/CLAUDE.md` Artifact Storage + `src/devforge/storage-rules.md` mentioning the new section. | testForge20 docs + `src/CLAUDE.md` + `src/devforge/storage-rules.md` |

### Cost (Track A)

- LLM: 1 step ~500 output tokens. Negligible vs current overview cost.
- Engineering: ~150 LOC + ~120 LOC tests + ~30 LOC spec.

## Track B — Glossary

### Output shape

`docs/glossary.md` at docs/ root:

```markdown
---
generated_by: /generate-docs (Phase B — glossary)
last_indexed: 2026-05-09
total_terms: 78
---

# Project Glossary

Terms surfaced in `docs/` and cross-referenced against the CBM-indexed code graph. Code-anchored entries link to a canonical definition; prose-only entries have no code symbol but appear in narrative.

## BLoC

A presentation-layer state container exposing reactive state and command methods to Vue components via the `useBLoCState` bridge.

- **Defined**: `pkg-cse-core/src/lib/BLoC.ts:14`
- **Used in**: `docs/db-cse-ui-strata/packages/pkg-cse-core/lib/index.md`, `docs/db-cse-ui-strata/architecture.md`
- **Related**: BLoCState, provideBLoC, useBLoCState

## domain layer

Architectural layer holding entities, use cases, and repository interfaces; depends on no other layer.

- **Used in**: `docs/db-cse-ui-strata/architecture.md`, `docs/db-cse-ui-strata/packages/pkg-cse-core/architecture.md` (and 47 others)
```

### Term classification (helper-enforced)

| Class | Has CBM symbol node? | Min cite-back |
|---|---|---|
| code-anchored | yes — exact name match (Function/Method/Class/Type/Interface/Enum) | 1 md path + 1 qn:line |
| fuzzy-anchored | no exact name; ≥1 BM25 hit on `search_graph(query=term)` w/ rank ≥ -25 | 1 md path + 1 qn:line, marked `(fuzzy)` |
| prose-only | no CBM symbol match | ≥2 md paths |

### State + validation

Track B writes a **standalone file** `docs/glossary.md`, not a section in an existing skeleton. Two-step setter API matches Track 4 precedent for setters that need helper-LLM-helper round-trip:

1. `build-glossary-bundles` — helper produces ranked term bundles as JSON on stdout (one record per top-N candidate term with `term, class, doc_context, code_anchor, related_set, cite_md_paths`)
2. `set-glossary-entries` — helper consumes JSON list on stdin (`{term, definition, related_terms}` per entry), merges with bundles (which already carry cite paths), validates, renders directly to `docs/glossary.md` (no `.skeleton` file — output is final).

Intermediate state during a single run: ephemeral in-memory dict inside the helper process. No JSON state file persisted between runs (full rebuild every run per v1).

Validator (helper-enforced, exit 2 on failure):
- term unique (case-insensitive)
- definition non-empty, ≤280 chars, single paragraph
- ≥1 cite_md_path; all `os.path.exists()` true (uses `_doc_corpus.validate_cite_paths`)
- code-anchored / fuzzy-anchored: `cite_qn` resolves via `get_code_snippet`
- prose-only: ≥2 cite_md_paths
- related_terms: each appears as a `term` elsewhere (no dangling refs)
- count: `30 ≤ N ≤ 150`
- exit 1 on I/O failure (CBM unreachable, glossary.md write failure)

### Combined pipeline (the step that uses CBM)

```
helper Step 1 (extract D-terms):
  walk docs/**/*.md via _doc_corpus.walk_doc_corpus
  extract_term_occurrences → {term: [(md_path, line, context), ...]}
  noise_filter

helper Step 2 (cross-ref against CBM):
  per term → query_graph: MATCH (n) WHERE n.name = "<term>"
                          RETURN n.qualified_name, labels(n), n.file_path,
                                 n.start_line, n.signature, n.is_exported
  classify code-anchored / fuzzy-anchored / prose-only
  fall through to search_graph(query=term) BM25 if 0 exact

helper Step 3 (rank):
  doc_freq  = len(occurrences)
  code_freq = MATCH (n)<-[:CALLS|USAGE|DEFINES]-() WHERE n.name="<term>" RETURN count(*)
  combined  = w1·log(doc_freq) + w2·log(code_freq) + w3·is_exported_bonus
  pick top-N=80

helper Step 4 (bundle per term):
  doc_context  = ±2 sentences per occurrence
  code_anchor  = first 5 lines via get_code_snippet(qn)
  related_set  = SEMANTICALLY_RELATED edges from CBM

helper Step 5 (LLM defines):
  per term → 1-2 sentence definition seeded by doc_context
  if doc_context <2 sentences total → mark [TODO: human-define]

helper Step 6 (validate + render):
  apply rules; alphabetical sort; write docs/glossary.md
```

### Phased steps

| Phase | Scope | Files touched |
|---|---|---|
| **B.1** helper | New module `src/devforge/lib/_generate_docs/_glossary.py` (~400 LOC) with sub-functions per the pipeline above; two SUBCMDS — `build-glossary-bundles` (helper produces JSON for LLM) and `set-glossary-entries` (helper consumes LLM output + renders). | `_glossary.py`, `_cli.py`, `tests/lib/test_glossary.py` (~30 cases) |
| **B.2** spec | Add Phase B section to `src/commands/generate-docs/main.md` at the end (after project-architecture). Spec instructs orchestrator to invoke helper, draft definitions seeded by doc_context, NOT invent definitions for thin contexts. **Mandatory edit at line 247**: flip the existing sentence `"Domain glossary lives inline in each Purpose paragraph; no separate glossary file."` to `"Domain glossary lives inline in each Purpose paragraph for in-context disambiguation; project-tier consolidated glossary lives at docs/glossary.md produced by Phase B."` Reviewer (instruction-reviewer) must confirm both tier-statements are now consistent. | `src/commands/generate-docs/main.md` |
| **B.3** empirical + cross-refs | Run `/generate-docs` on testForge20; verify 30–150 entries; spot-check 5 definitions against cite_md_paths; verify CBM consumes glossary via `search_graph(query="<term>")` returning the new Section. Cross-file note in `src/CLAUDE.md` + `src/devforge/storage-rules.md`. | testForge20 + `src/CLAUDE.md` + `src/devforge/storage-rules.md` |

### Cost (Track B)

- CBM: ~80 query_graph + ~20 search_graph fallbacks + ~80 get_code_snippet ≈ 1.5s total.
- LLM: ~80 define-prompts × ~150 tokens ≈ 12K input + 6K output. Haiku ~$0.10; Sonnet ~$0.30.
- Engineering: ~400 LOC helper + ~250 LOC tests + ~30 LOC spec.

## Cross-track synergy (post both shipped)

| Synergy | Mechanism | When |
|---|---|---|
| Track B consumes Track A's section as additional `doc_freq` signal | Track B's `walk_doc_corpus` picks up overview.md including the freshly-written `## Suggested Research Starts` section; terms in `scope_hint` and question text contribute to `doc_freq` | automatic once both shipped — no extra code |
| Track A questions cross-link to glossary terms | future render: terms in question text auto-rendered as markdown links to `glossary.md#term-anchor` | v2 — out of scope for this plan; flagged for future bug-fix-only commit |

## Sequencing recommendation

```
Pre-req:  Add `index_repository` trigger to /init-forge spec      (1 commit)
Step 0:   Ship _doc_corpus.py + _merge_project_skeleton enhancement (1 commit)
Step A1:  Track A helper                                           (1 commit)
Step A2:  Track A spec                                             (1 commit)
Step A3:  Track A empirical + cross-refs                           (1 commit)
Step B1:  Track B helper                                           (1 commit)
Step B2:  Track B spec                                             (1 commit)
Step B3:  Track B empirical + cross-refs                           (1 commit)
Step Z:   GENERATE-DOCS-PLAN.md annotation pass — mark
          Steps 6.3 + 6.4 superseded by this plan; declare
          /generate-docs feature-closed                            (1 commit)
```

9 commits total. ~2 sessions. Each commit independent + reversible.

## Open decisions

1. **Section title for Track A**: `## Suggested Research Starts` (default) vs `## Where to Start Investigating` vs `## Recommended Traces`. Lock at A.2 entry.
2. **Track A count bounds**: 3–6 (default) vs 4–5 (tighter). Lock at A.1 entry.
3. **Track A cite_paths convention**: file paths only (default) vs file:line ranges. Default keeps cite-back simple. Lock at A.1 entry.
4. **Track B top-N default**: 80 (testForge20-scale heuristic). Lock at B.1 entry.
5. **Track B noise-filter list location**: hardcoded baseline + optional `.devforge/glossary-noise.txt` user override. Lock at B.1 entry.
6. **Track B term-cache for refresh (v2 feature)**: ship in v1 or defer? Default: defer. v1 = full rebuild every run.
7. **Track B fuzzy-match threshold**: BM25 rank ≥ -25 (default). Lock at B.1 entry.
8. **/init-forge index trigger placement**: pre-req commit (default) vs helper-side fallback that shells out to CBM CLI on missing project. Default: pre-req keeps helper free of CLI shell-out.
9. **Cross-track v2 synergies (auto-link, glossary-consumes-research-starts)**: defer to bug-fix-only commits post feature-closure of `/generate-docs`. Not in this plan's scope.

## When resuming work

1. Read this plan in full + cited memory (`project_track4_phase1_2_3_shipped`, `project_cbm_integration_plan_e`, `feedback_cbm_search_graph_pattern_keys`, `feedback_cbm_discovery_chain_search_graph_then_code`, `feedback_helper_owns_shape_principle`).
2. Confirm branch: `develop-2.0-init` or successor. Verify test baseline ≥1297 OK.
3. Verify CBM is indexed for testForge20 + ai-dev-team-forge: `mcp__codebase-memory-mcp__list_projects`. If missing, `index_repository` first.
4. Lock Open Decisions before starting respective steps (A.1 / B.1 entries).
5. Pre-req + Step 0 first. Then A1→A2→A3 OR B1→B2→B3 in any order — they don't interleave; pick one track to completion before starting the other (avoid spec merge conflicts in `src/commands/generate-docs/main.md`).
6. Step Z LAST — declares `/generate-docs` feature-closed. After Step Z, no further enhancement plans for `/generate-docs` are accepted; only bug fixes + CBM-API-evolution adjustments.
7. After each commit, update memory if design diverges (e.g., CBM behavior changes invalidate term classification).
8. **Don't expand scope** into Track B remaining scripts (topic-index / reverse-index / pattern-catalog / accuracy-validation / constitution-anchors / freshness-footers). Those remain rejected per the docs+CBM-split argument in this plan's "Why not" section.

## Integration with existing plans + memory

- **GENERATE-DOCS-PLAN.md** Step 6.3 (Glossary) + Step 6.4 (Topic index "consider on entry") — superseded by this plan. Step Z annotates them. Other Track B steps (6.2 / 6.5 / 6.6 / 6.7 / 6.8) are NOT shipped and will not be — explicitly rejected per docs+CBM split.
- **ARCHITECTURE-PIVOT-PLAN.md** Step 1 (`/init-forge`) — gains `index_repository` trigger as pre-req commit. Doesn't change Step 2 (`/generate-docs`) scope. Steps 3-8 unaffected.
- **CBM-INTEGRATION-PLAN.md F.11** — already shipped this session (commits `65b0a24` / `e0ca9bb` / `cdddf76`). Track B's CBM queries align with F.11 hook enforcement; symbiotic.
- **CODEX-REMOVAL-PLAN.md** — orthogonal. Independent merge.
- **REDESIGN-RESEARCH-PLAN.md** — DEFERRED per dump 2026-05-08. Track A's output (Suggested Research Starts) feeds the future `/research` redesign whenever that unblocks; not a pre-req for either.
- **VALIDATOR-LOOP-B-PLAN.md** — orthogonal (validator-loop is concern-doc level; this plan is project-tier).
- **Memory `project_track4_phase1_2_3_shipped`** — Track 4 closed. This plan is scope-distinct; does not violate closure.
- **Memory `project_cbm_integration_plan_e`** — direct application of docs+CBM split.
- **Memory `project_codegraph_state_2026_05_06`** — codegraph LLM-mode broken; this plan does NOT use codegraph (only CBM). Confirmed alignment.
- **Memory `project_schema_anchored_generate_docs`** — helper-owns-shape pattern reused. No new schema dataclass needed; project-tier uses dict-shaped state per Track 4 precedent.
- **Memory `feedback_helper_owns_shape_principle`** — both tracks' helpers own structure; LLM provides values via setter API. Standard pattern.
- **Memory `feedback_cbm_search_graph_pattern_keys`** + **`feedback_cbm_discovery_chain_search_graph_then_code`** — Track B respects both: exact name match first via `query_graph`, fall through to `search_graph(query=...)` BM25 on miss.
