# /research redesign plan

Active branch: `develop-2.0-init` (or successor — confirm at session start).
Status: planning. No code edits yet.

## Why redesign

`/research` exists at `src/_pending/commands/research.md` (pre-promotion). Its current spec was authored under the old setup-wizard architecture + before Plan F docs/ + CBM landed. Per session 2026-05-08 empirical test, the current discovery flow has a precision gap: graph-only searches miss inline framework expressions (Vue `<script setup>`, React hooks, Svelte reactive blocks). Redesign target: a discovery flow that lands precise root cause for typical UI/logic bugs without forcing source reads as the next step after graph queries.

The redesign should integrate with the 4-command setup chain (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`) — once /constitute populates `constitution.md`, /research can consult it.

## Findings to encode (locked discoveries to bake into the redesign)

### 1. CBM discovery chain — `search_graph` THEN `search_code` fallback

**Rule**: When CBM `search_graph` returns 0 hits for an expected behavior (sort logic, filter, validation, etc.), do NOT declare "absent" yet. Chain: `search_graph` (named fns/classes) → if 0 hits → `search_code` (text/regex over indexed files) → only declare absent if BOTH return nothing.

**Why**: Empirical 2026-05-08 testForge20 alert-sort research. CBM `search_graph` for `.*sort.*` patterns returned 0 hits across the alert resolver pipeline. The orchestrator declared "alphabetical sort missing entirely." Wrong — sort EXISTED inline at `AlertResolverChoices.vue:203` as a `.sort()` call inside a Vue `watch` body. CBM's tree-sitter graph indexes only callable named symbols (top-level functions, methods, classes); inline expressions, computed refs, watch bodies, and ad-hoc `.sort()`/`.filter()`/`.map()` calls are invisible to graph queries. `search_code` (text/regex) would have found `.sort(` immediately and surfaced the right line.

The same gap applies to React hooks, Vue computed/watch, Svelte reactive blocks, any framework where logic lives in reactive bodies rather than named functions. Tree-sitter graph indexers don't promote inline calls to graph nodes.

**How to encode in /research spec**:
- Discovery protocol step 1: CBM `agentic_context "<topic>"` (synthesized bundle, when LLM mode enabled).
- Step 2: CBM `search_graph` for named symbols (high-signal first).
- Step 3: **MANDATORY** if step 2 returns 0 hits for an expected behavior — chain to `search_code` with the literal token (`.sort(`, `.filter(`, `.localeCompare(`, etc.) over the suspected package's files.
- Step 4: only after both return nothing, declare "truly absent" + escalate to source `Read`.
- Confidence calibration: 0 hits at search_graph alone = "no NAMED implementation"; 0 hits at search_code = "truly absent". Spec must NOT conflate these.
- Inline-call-site bugs (sort/filter/comparison expressions buried in framework reactive blocks) are common in Vue/React UI code. Default to search_code as the second step, not source `Read`.

Memory cross-ref: `feedback_cbm_discovery_chain_search_graph_then_code.md`.

### 2. Hypothesis-enumeration + diagnose-first discipline

**Rule**: When a symptom has multiple plausible causes (provide/inject mismatches, async-timing races, vendor microfrontend bundles, framework lifecycle gaps, etc.), enumerate the FULL hypothesis set BEFORE proposing fixes. For each plausible cause that can't be falsified from static analysis alone, mandate a runtime-verification step (e.g., `app.config.warnHandler` capture, console-log probe, breakpoint dump) before committing to a fix path.

**Why**: Empirical 2026-05-10 comparison on testForge20 `[Vue warn]: injection "notificationsBLoC" not found` ticket. The docs+CBM-driven investigation reached the same root-cause GENRE as the main-branch `/research` flow (provide/inject mismatch on vendor inject sites) but stopped at the FIRST plausible theory ("Pinia store factory context breaks inject"). The main-branch flow enumerated 4 candidate causes (vendor suffixed-key mismatch, teleport-to-non-Vue-tree, plugin install-time setup, vendor module-load side-effect) and recommended a `app.config.warnHandler` capture to identify the actual emitter component before patching. The four-hypothesis breadth mattered because the suffixed-key vendor pattern (`notificationsBLoC-${id}` in `chunk-BZDCDJU3.js:47094`) would have made a host-side `app.provide('notificationsBLoC', ...)` fix a partial fix only — not visible from a single-hypothesis path.

The single-hypothesis failure mode is hard to detect during the investigation itself — the first plausible theory feels sufficient. Discipline must enforce enumeration as a step, not leave it to judgment.

**How to encode in /research spec**:
- Discovery protocol after the search-chain (§1): MANDATORY hypothesis-enumeration step. Output shape: bullet list of N≥2 candidate causes for the symptom, each with a one-line "what would falsify this" probe.
- For each hypothesis whose falsification probe needs runtime data (cannot be answered from static analysis): MANDATORY runtime-verification recommendation in the report. Examples: `app.config.warnHandler` capture for Vue warnings, network-tab probe for HTTP-shaped issues, breakpoint dump for timing/lifecycle issues.
- Output schema gains a `hypotheses` field (array of `{cause, falsifier}`) and a `verify_step` field (the recommended runtime probe). Helper enforces non-empty hypotheses array (≥2 entries) for symptom-driven research; freezes if LLM provides only 1.
- The fix recommendation MUST cite which hypothesis it addresses + which others it would NOT cover. Forces explicit acknowledgement of remaining uncertainty.

**Anti-pattern this prevents**: confident "root cause = X, fix = Y" output when only X was enumerated and Y is partial because non-enumerated causes also contribute. Hypothesis-enumeration surfaces the gaps before they become regressions.

**Cross-CBM-discovery interaction**: this rule layers on top of §1. CBM search-chain finds candidate code surfaces; hypothesis-enumeration explains WHY each surface might be the root cause. Two-rule combo: §1 finds WHERE, §2 explains WHY (and which other WHYs are still in play).

## Constraints (apply when authoring redesign)

- Zero-escape-hatch policy: no "OR / if / except / unless / use-judgment" clauses in the discovery protocol. Each step has a single mandated action.
- Helper-owns-shape: research output schema (if any) owned by a Python helper, not by LLM prose.
- LLM-first density: spec body is LLM instructions, not human-onboarding wiki. No forward refs to future phases that don't exist yet.
- Dual-agent verification: any /research spec edit goes through instruction-author + claude-code-guide before commit (per `feedback_dual_agent_verify_command_statements`).
- No CSE / dev-version refs in shipped spec; production-ready prose only.

## Open questions

1. Does /research save artefacts (e.g., `research/YYYY-MM-DD-topic.md`)? Current spec does. Redesign keeps or drops?
2. Should /research consult `constitution.md` proactively (when populated)? Current spec reads it. Redesign should make this conditional + non-blocking when constitution unpopulated.
3. Should /research delegate to a research subagent or stay orchestrator-direct? Per `feedback_avoid_subagents_for_sequential_identical_workflows`: orchestrator-direct unless three benefits (parallelism / tool isolation / context-budget) earn the dispatch.
4. Cost-gate prose: should /research surface estimated CBM call count + token cost before kicking off, parallel to /generate-docs Phase 1 cost gate?
5. Output shape: free-form report vs structured (Goal / Surface / Suspect lines / Confidence / Next-step recommendation)?

## Work order (TBD when starting)

To draft when redesign begins:

- Step 1: read current `src/_pending/commands/research.md` end-to-end + map sections.
- Step 2: list all CBM tools available (per session deferred-tool list) + decide which are mandatory vs optional in discovery.
- Step 3: draft new spec body with the locked discovery chain + constraint set above.
- Step 4: dual-agent verify (instruction-author + claude-code-guide).
- Step 5: ship to `src/commands/research/main.md` (promote out of `_pending/`); update `scripts/emitters/claude.py` `_PROMOTED` list.
- Step 6: empirical test on testForge20 with a real ticket (e.g., the alert-sort ticket from the 2026-05-08 session — see Findings §1).

## Verify criteria (per step, fill in during redesign)

- TBD.

## When resuming work

1. Read this file in full.
2. Read `feedback_cbm_discovery_chain_search_graph_then_code.md` (memory).
3. Check current state of `src/_pending/commands/research.md` + emitter `_PROMOTED` list.
4. Run preflight on testForge20 to confirm CBM index still live: `cd /Users/mykolakudlyk/Projects/testForge20 && ./.devforge/lib/generate_docs_helper preflight --skip-vue-extract --skip-index | jq '.concern_counts'`.
5. Pick up at the open question that's still blocking, or drop into Work order Step 1.
