# Plan F — Multi-tier docs/ + CBM as structural-query layer

**Status (2026-05-07)**: Approved. Supersedes Plan E. E.1 (sourcemap consumer) + E.1.b (nearest mode) + topology lock + iteration scaffold are committed foundations; F reshapes E.2–E.6 and adds F.0 + F.7–F.10. F.0 (preflight) added 2026-05-07 to reframe freshness from "invariant-to-maintain" to "operation-to-run" — collapsed three risk classes (reindex-discipline, stale cite-back, wasted dispatch) to non-issues.

**Branch**: continues on `develop-2.0-init`.

**Predecessors**:
- `VALIDATOR-LOOP-PLAN.md` (Part A, frozen)
- `VALIDATOR-LOOP-B-PLAN.md` (Part B retired; Part D revert documented inline)
- Plan E (this same file at commit `3223c90` and earlier — pre-pivot scope; superseded)

---

## Why Plan F

Plan E premise was "pre-compute 7-section markdown per concern so future LLM workflows skip codebase exploration." That premise dissolved when codebase-memory-mcp landed:

- CBM's structural queries (`search_graph`, `trace_path`, `get_code_snippet`, `agentic_context`, `search_code`) deliver in 1–10ms what Plan E proposed pre-rendering for $5–15/concern of LLM cost.
- 5 of E's 7 sections (exports, types, dependencies, usage_example, public-surface descriptions) are derivable live from CBM with strictly fresher data than any pre-rendered md.
- 1 of E's 7 sections (overview / Purpose) is NOT in any graph — pure LLM judgment over source. Stays md.
- 1 of E's 7 sections (annotated tree / Structure) is mechanical structure + LLM 1-line annotations per leaf. Keep as md.
- Hazards moved out of concern docs entirely (2026-05-07 V4 finding) — `/audit` command is the right home for adversarial gotcha discovery; pre-rendering hazards into every concern doc bloats output for LLM consumers (research/specify/plan) who care about orientation, not gotchas. Quality-review territory ≠ orientation territory.
- New tiers Plan E didn't address: package overview/architecture, project overview/architecture. These are also pure LLM judgment over the codebase, regenerated rarely. Add as md. (Glossary tier dropped 2026-05-07 — V4 confirmed concern Purpose paragraphs surface domain terms in context; a separate glossary file is redundant. Cross-concern terms can land in the package overview's Purpose paragraph or via CBM `search_code` live.)

Result: docs/ becomes the **orientation + narrative** layer (Purpose + Structure per concern; package + project tiers); CBM becomes the **structural-query** layer; `/audit` becomes the **hazard-discovery** layer.

LLM-first density: docs/ files are LLM context source first, dev-greppable second. Format is structured-prompt-fragment, not wiki page.

---

## Inherited from Plan E (committed foundations — no rework)

| Component | Commit | Location |
|---|---|---|
| Sourcemap V3 consumer + nearest mode | `b08fdfd`, `3223c90` | `src/devforge/lib/_generate_docs/_sourcemap.py` |
| Sourcemap test suite (31 cases) | `b08fdfd`, `3223c90` | `tests/lib/test_sourcemap.py` + `tests/fixtures/sourcemap/` |
| vue-extract default `.devforge/vue-tmp/` | `8126443` | `src/devforge/lib/vue-extract` |
| codebase-memory-mcp in installed `.mcp.json` | `8126443` | `src/mcp.json` |
| README codebase-memory-mcp section | `8126443` | `README.md` |
| Iteration `/generate-docs` (vue-extract + index_repository) | `8126443`, `3223c90` | `src/commands/generate-docs/main.md` |
| Topology lock (single-index walk; wrapper + non-wrapper symmetry) | `8126443` | this file (rewritten) |

These ship as-is into Plan F. Sourcemap module is consumed by F.2 (concern-input helper, `nearest=True` for Vue cite-back).

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ /generate-docs (rewritten under F.4 — multi-tier loop)           │
└─────────────────────────────────┬────────────────────────────────┘
                                  │
                                  ▼
         F.0 preflight ── vue-extract → cli index_repository → stamp diff
                          (idempotent;  (idempotent)         (ms; per concern)
                           5-15s)                             returns
                                                              concerns[].status
                                  │
                  ┌───────────────┼────────────────┐
                  ▼               ▼                ▼
         F.4 project tier  F.4 package tier   F.4 concern tier
         (1 dispatch ×    (3 dispatches ×    (1 dispatch ×
          2 docs;          M packages;        N concerns;
          gated by         gated by           gated by
          project-stamp)   pkg-stamp)         source_stamp)
              │                │                  │
              ▼                ▼                  ▼
         doc-composer agent (F.3) — same agent, tier-specific prompts
              │
              ▼
         orchestrator parses output, calls setters (F.4 primitives)
              │
              ▼
         helper renders md (helper owns structure; LLM owns values)
              │
              ▼
         validate-doc gate (F.5) — frontmatter + cite-backs + density
              │
              ▼
         render-doc (F.4) — `.skeleton` → `.md` once validation passes
```

CBM provides the structural-query layer. Commands consult it directly via MCP tools — no batch-pre-rendering of structural fields.

---

## CBM topology + indexing layout (locked)

(Locked under Plan E `8126443`; carried verbatim into F.)

Single CBM index covers source + Vue mirror in one walk. Two facts:

1. **CBM `index_repository` takes ONE `repo_path`.** No multi-root flag (verified against codebase-memory-mcp 0.6.1 README + CLI probe).
2. **CBM walks dotfile-prefixed dirs.** Verified empirically (`.devforge/template/CLAUDE.md` appears in current testForge20 index).

Mirror layout: `vue-extract` emits `.vue.ts` + `.vue.ts.map` to `<index-root>/.devforge/vue-tmp/<rel-source-path>/`.

| Mode | Index root | Source tree | Mirror dir |
|---|---|---|---|
| Wrapper (testForge20-style) | `<wrapper>/` | `<wrapper>/<project>/...` | `<wrapper>/.devforge/vue-tmp/<project>/...` |
| Non-wrapper | `<project>/` | `<project>/...` | `<project>/.devforge/vue-tmp/...` |

CBM cite-paths come in two flavors: original TS/JS (passes through verbatim) or mirror `.devforge/vue-tmp/.../<f>.vue.ts` (helper applies sourcemap with `nearest=True` to rewrite back to original `.vue` path).

Mirror is regenerable. Add `.devforge/vue-tmp/` to gitignore template (wizard STEP 0 owns it).

---

## docs/ canonical layout

```
docs/
  overview.md                       (F.8 project tier)
  architecture.md                   (F.8 project tier)
  <package>/
    overview.md                     (F.7 package tier)
    architecture.md                 (F.7 package tier)
    <concern>/
      index.md                      (F.2/F.3 concern tier)
constitution.md                     (existing; root; unchanged)
```

Killed: `docs/api/`, `docs/features/`, `docs/guides/` (legacy CLAUDE.md template suggestions; replaced by CBM live queries or only-when-actually-needed manual writing).

---

## LLM-first density format

Universal rules (encoded in F.3 doc-composer prompt + F.5 validate-doc):

- **Frontmatter mandatory** — every doc opens with YAML-subset front-matter. Required keys per tier:
  - Concern: `concern`, `package`, `files`, `source_stamp`, `last_indexed`
  - Package overview/architecture: `package`, `last_indexed`, `source_stamp`
  - Project overview/architecture: `last_indexed` only
  Helper writes the frontmatter; LLM never edits it.
- **Section anchors fixed** — `## Purpose`, `## Structure`, `## Layers`, `## Patterns`, `## Concerns`, `## Files`, `## Packages`, `## Cross-Cuts`. Orchestrator parses by anchor. Hazards moved to `/audit` (separate command); concern docs do NOT carry hazard content. Glossary dropped — Purpose paragraphs surface terms in context. `## Files` (added 2026-05-08 after V5 smoke) surfaces loose files at `<pkg>/src/` root that don't belong to any concern subfolder (e.g. `index.ts` barrels, `env.d.ts` ambient declarations).
- **No preamble paragraphs** — section content starts on the first line after the anchor. Banned phrases (case-insensitive): "this document", "in this section", "we will", "various", "several", "many", "some", "other".
- **Tree formatting** — `## Structure` content is plain text directly under the heading. No code fence. Helper provides the tree verbatim from F.2 output; LLM appends `— <annotation ≤60 chars>` to each LEAF on the same line.
- **Density caps** (calibrated 2026-05-07 on testForge20 helpers + V4 finding):
  - Per-section caps only — no whole-doc budget. Tree section grows with file count; that is intentional.
  - Per-bullet length: ≤200 chars (Layers/Patterns/Concerns/Packages/Cross-Cuts); Structure annotations: ≤60 chars
- **Cite-back format** (Layers/Patterns/Concerns/Packages/Cross-Cuts only — concern docs have no cites): `<project-relative-path>:<line>` or `<project-relative-path>:<start>-<end>`. Helper validates each cite resolves to an existing line in an existing file. For Vue cite-back, helper applies sourcemap (E.1.b nearest mode) before validating.
- **No prose tables for structural data** — exports, types, deps, callees lists are NEVER in docs/. Those queries hit CBM live.

Example concern doc (target shape):

```markdown
---
concern: order
package: db-cse-ui-strata/apps/app-web
files: 47
source_stamp: 9f3c2a1
last_indexed: 2026-05-07
---

# order

## Purpose
Order line-item editor + submit/cancel flow for app-web. Cross-cuts identity (BLoC), pricing (helpers), and division-specific terms.

## Structure
src/components/order/
├── OrderFooter.vue          — submit/cancel + T&C; EMEA branch
├── OrderLines.vue           — line-item list editor
├── orderLine/
│   ├── OrderLine.vue        — single line render
│   └── OrderLinePrice.vue   — price formatter per division
└── helpers/
    └── data.ts              — modal config provider
```

Example package architecture.md:

```markdown
---
package: db-cse-ui-strata/apps/app-web
last_indexed: 2026-05-07
---

# architecture

## Layers
- presentation — Vue components in `src/components/`
- composition — composables in `src/composables/`; thin glue
- business — BLoCs in pkg-cse-core/src/<concern>/presentation/
- data — repositories in pkg-cse-core/src/<concern>/data/

## Patterns
- BLoC over Pinia for cross-package state — pkg-cse-core/src/*/presentation/*BLoC.ts
- ref() for primitives, reactive() for nested objects — convention; verify on edit
- @vue/compiler-sfc Source Map V3 emitted to .devforge/vue-tmp/ — used by /research cite-back
```

---

## Components

### F.0 — Preflight (entry-point freshness operation)

Locked 2026-05-07. Reframes freshness from "invariant-to-maintain" (commands assume `.devforge/vue-tmp/` and the CBM graph are current; staleness causes silent cite-back drift) to "operation-to-run" (every entry point that consults docs/ or CBM invokes preflight first; cheap operations always run, expensive operations gate on stamp diff).

**F.0.a — `generate_docs_helper preflight`** (new subcommand, ~80 lines + tests).

Behavior:
1. Run `vue-extract` (idempotent: regenerates `.devforge/vue-tmp/` mirror; no-op when source `.vue` files unchanged).
2. Run `codebase-memory-mcp cli index_repository '{"repo_path":"<index-root-abs>"}'` (idempotent: incremental reindex via watcher artifact).
3. For each `<package>/src/<concern>/` subfolder, compute its source_stamp (reuses `_build_spans_and_stamp` from F.2). Read existing `docs/<package>/<concern>/index.md` frontmatter (if present) and diff its `source_stamp` against the freshly-computed value.
4. Emit JSON to stdout:
   ```json
   {
     "vue_extract": {"compiled": N, "failed": 0, "duration_ms": ...},
     "index_repository": {"nodes": N, "edges": M, "duration_ms": ...},
     "concerns": [
       {"package": "P", "concern": "C", "source_stamp": "...",
        "prior_stamp": "...", "status": "unchanged|changed|new"},
       ...
     ]
   }
   ```
5. Exit 0 on success; non-zero with stderr diagnostic if vue-extract or CBM fails.

CLI:
```
generate_docs_helper preflight [--devforge-dir D] [--skip-vue-extract] [--skip-index]
```

The skip flags are escape valves only; default behavior runs both. Cache: a `<devforge-dir>/.preflight-stamp` file records the wall-time of the last successful preflight; consumer commands MAY skip preflight when stamp is fresher than 60s (per-command policy, not enforced here).

**F.0.b — Stamp-gate rule in F.4**.

`/generate-docs` Phase 3 (concern tier loop) reads preflight's `concerns[]` list. For each concern with `status=unchanged`, SKIP the doc-composer dispatch + setter chain entirely. Only concerns marked `changed` or `new` get a dispatch.

Phase 4 (package tier) and Phase 5 (project tier) gates similarly: package overview/architecture/glossary regenerate when ANY concern in the package changed OR when `package_stamp` (sha over package's concern stamps + package-root file hashes) differs from prior; project regenerates when ANY package changed OR project-root files differ.

#### Cost profile

| Operation | Cost | Frequency |
|---|---|---|
| vue-extract (idempotent) | 5-15s | every preflight |
| index_repository (incremental) | 5-30s | every preflight |
| stamp diff | ms | every concern in /generate-docs |
| doc-composer dispatch | $0.10-0.20 + 10s | only changed concerns |

Worst case (every concern changed): full /generate-docs ~$10-25, ~15min. Best case (one concern changed): one dispatch / ~10s / ~$0.20.

#### What dies (fragility classes collapsed by F.0)
- "Did I remember to reindex?" — gone (preflight forces it)
- Stale-map cite-back on Vue files — gone (vue-extract idempotent + always-fresh)
- Stale-graph cite-back from old indexes — gone (index_repository always-fresh)
- Wasted LLM spend on unchanged concerns — gone (stamp gate)

#### Test scope (`tests/lib/test_preflight.py`)
- Happy path: testForge20-style synthetic project; preflight emits valid JSON with all three sections (vue_extract, index_repository, concerns)
- Stamp diff: change one file under `<pkg>/src/<concern>/`, run preflight twice; first run marks concern `new` (no prior doc), second run marks it `unchanged`; touching the file flips back to `changed`
- Skip flags: `--skip-vue-extract` omits vue_extract section; `--skip-index` omits index_repository section
- Failure: CBM binary missing → exit 2 with install-instruction stderr; vue-extract failure → exit 1 with launcher's stderr verbatim
- Frontmatter parse: doc with malformed frontmatter is treated as `prior_stamp=null` → status `new` (graceful degrade, not crash)

#### Verify F.0
- ≥ 6 tests green
- End-to-end smoke on testForge20: preflight runs, second run reports all concerns `unchanged`, touching one file marks one concern `changed`
- Wall-clock budget on testForge20: ≤ 30s for the mechanical phases (vue-extract + index_repository + stamp-diff for ~64 concerns)

---

### F.1 — Sourcemap consumer (DONE under E.1 + E.1.b)

Carried as-is. Used by F.2 to translate `.vue.ts:line` cite-backs to `.vue:line` for inclusion in concern docs.

### F.2 — Concern-input helper

Location: `src/devforge/lib/_generate_docs/_concern_input.py` (new module).

CLI:
```
generate_docs_helper concern-input --package P --concern C [--vue-extract-dir D]
```

Behavior:
1. Resolve concern's source subfolder: `<project_root>/<package>/src/<concern>/`.
2. Walk filesystem under the subfolder recursively (NOT via `.devforge/index.json` — that file caps at 500 entries per package and loses concerns on real monorepos; testForge20 app-web hits the cap and the `helpers/` subfolder falls past it). Apply `_path_contains_trivial_dir` skip rule (node_modules / dist / build / etc.) during the walk.
3. Build mechanical ASCII tree of the surviving project-relative paths. Subfolder header is the first line; directories grouped above leaves at each level.
4. For each file, extract a "comment-rich span" — top 30 lines plus any line containing a hazard marker (TODO / FIXME / HACK / WARNING / XXX) with 2-line context above + below. Overlapping windows merge; non-adjacent windows separated by `...`. Cap per-file at 6KB, total batch at 60KB (excess files emit a `<batch cap reached>` placeholder).
5. Output to stdout: batch JSON. Caller pipes to F.3 doc-composer dispatch.

JSON shape:
```json
{
  "concern": "order",
  "package": "db-cse-ui-strata/apps/app-web",
  "subfolder": "src/components/order/",
  "tree_text": "src/components/order/\n├── OrderFooter.vue\n├── OrderLines.vue\n...",
  "files": [
    {
      "path": "src/components/order/OrderFooter.vue",
      "comment_rich_span": "<...top + comment-dense regions...>"
    },
    ...
  ],
  "source_stamp": "9f3c2a1"
}
```

`source_stamp` = SHA-256 over sorted-file-content hashes of the subfolder; used by F.4 for incremental skip.

NO public-surface query, NO types query, NO deps query, NO IMPORTS/CALLS query. Those derivable from CBM live; not pre-computed.

Test scope (`tests/lib/test_concern_input.py`):
- Index.json with 5 files in subfolder → tree_text contains all 5 with correct indentation
- Comment-rich span: file with top doc-block returns top span + doc block; file with TODOs returns spans containing TODOs
- Source stamp: byte-identical inputs → identical stamp; one file changed → different stamp
- Vue file: span is read from the `.vue` source verbatim, NOT the mirror. Mirror's `.vue.ts` strips template content unless `--include-template` was passed to vue-extract; template-side hazards (v-for misuse, reactivity gotchas) are only visible in the source. The CBM mirror is for graph queries (CALLS edges); helpers read source for span extraction.
- Concern not in index.json → exit 2

#### Verify F.2
- 8+ tests green
- End-to-end smoke: `concern-input --package db-cse-ui-strata/apps/app-web --concern order` returns valid batch JSON ≤ 60KB

### F.3 — doc-composer agent

Location: `src/agents/doc-composer.md` (new file).

Frontmatter:
```yaml
name: doc-composer
description: "Multi-tier doc composer for /generate-docs Plan F. Receives batch JSON from concern-input / package-input / project-input helpers. Emits 1-2 LLM-first dense sections per dispatch (Purpose/Structure for concern; Layers/Patterns for architecture; Purpose/Concerns for overviews). Strict density format. Orchestrator parses sections into setter calls."
model_tier: scan
tools: Read
```

`model_tier: scan` (Haiku) — density caps are LLM-first; scan tier produces tighter output than think tier in this format.

Tool allowlist: `Read` only. Composer doesn't need CBM tools — concern-input helper already extracted what it needs. NO Bash (no helper invocation from subagent; orchestrator parses output and calls setters).

Output contract: structured Markdown with anchors. Sections:
- Concern tier: `## Purpose`, `## Structure` (NO Hazards — moved to /audit)
- Package overview: `## Purpose`, `## Concerns`, `## Files`
- Package architecture: `## Layers`, `## Patterns`
- Project overview: `## Purpose`, `## Packages`
- Project architecture: `## Layers`, `## Cross-Cuts`
- (Glossary tier dropped 2026-05-07 — Purpose paragraphs surface terms in context.)

Density discipline (encoded in agent body):
- Banned phrases list ("This document...", "In this section...", "We will...", "various", "several", "many", "some", "other")
- Per-bullet length cap (≤200 chars; annotation ≤60)
- Concern Structure section: ASCII tree only, with per-leaf 1-line annotation; helper provides the tree pre-computed, LLM fills annotations only

#### Verify F.3
- Agent file authored via instruction-author + claude-code-guide (per `feedback_dual_agent_verify_command_statements`)
- Sample dispatches on testForge20 (helpers concern, order concern, app-web package architecture): orchestrator parses cleanly, density caps met
- Test scope override (single concern): from F.4 spec carry-over

### F.4 — /generate-docs spec rewrite (multi-tier loop)

Replace iteration scaffold (`src/commands/generate-docs/main.md` at commit `3223c90`) with multi-tier flow:

```markdown
## Phase 0 — Pre-flight gate
  Hard-check `command -v codebase-memory-mcp`. If missing, ABORT with
  install instructions. Hard-check `.devforge/index.json` exists (run
  /init-forge first).
## Phase 1 — Preflight (delegates to F.0)
  Invoke `generate_docs_helper preflight`. Capture concerns[] list with
  per-concern status (unchanged | changed | new). vue-extract +
  index_repository run unconditionally inside preflight; idempotent.
## Phase 2 — Concern tier loop (bottom of doc hierarchy; runs first because higher tiers read concern frontmatter)
  For each package P × concern C from preflight's concerns[]:
    If status == "unchanged" → SKIP (F.0.b stamp gate)
    Else (status in {"changed", "new"}):
          render docs/<P>/<C>/index.md.skeleton
          Dispatch doc-composer with concern-input batch JSON
          Parse 2 sections (Purpose, Structure-as-flat-annotations) → setters
          Validate + render
## Phase 3 — Package tier loop (reads concern frontmatter for Concerns list)
  For each package P:
    If all P's concern docs were SKIPPED above AND P-stamp unchanged → SKIP
    Else: render docs/<P>/{overview,architecture}.md.skeleton
          Dispatch doc-composer with package-input helper output
          Parse 3 docs of sections → call setters
          Validate + render
## Phase 4 — Project tier (reads package frontmatter for Packages list)
  If all packages were SKIPPED above AND project-stamp unchanged → SKIP
  Else: render skeletons: docs/overview.md.skeleton + docs/architecture.md.skeleton
        Dispatch doc-composer with project-input helper output
        Parse 2 docs of sections → call setters
        Validate + render
## Phase 5 — Verify
  Walk docs/, ensure every doc has valid frontmatter + cite-backs resolve
## Phase 6 — Report
  Print: N concerns dispatched of M total; M-N skipped via stamp gate.
  Print: cumulative LLM token estimate + cost.
  Print: vue-extract + index_repository wall-clock from preflight.
```

(Phases renumbered: legacy Phase 0/1/2 collapsed into the new Phase 1
preflight delegation; F.0.b stamp gate now drives the SKIP branches in
Phase 2/3/4 instead of inline stamp comparisons.)

Cost gate (subscription-aware):
- Pre-Phase-3: print expected dispatches + token estimate (~10K input + ~5K output per dispatch; ~$0.10–0.20 per concern).
- Single AskUserQuestion: `Proceed with full /generate-docs run? [yes/no/concerns-only/skip-incremental]`

Setter primitives (helper-owned, NEW for F.4):
- `set-doc-purpose --tier T --target X --text "..."` 
- `set-doc-structure --tier concern --target X --tree "..." --annotations '{path: "1-line", ...}'`
- `add-doc-hazard --tier concern --target X --text "..." --cite "file:line"`
- `set-doc-layers --tier T --target X --layers '[{name, role, cite}]'`
- `set-doc-patterns --tier T --target X --patterns '[{name, rule, cite}]'`
- `set-overview-concerns --target X --concerns '[{name, role, cite}]'`
- `set-overview-packages --target X --packages '[{name, role, cite}]'`

Validators (helper-owned, NEW for F.4):
- `validate-doc --tier T --target X` checks: frontmatter present, all cite-backs resolve, density caps met, banned phrases absent
- `render-doc --tier T --target X` writes `.skeleton` → `.md` once validation passes

#### Verify F.4
- Spec change reviewed by instruction-author + instruction-reviewer
- claude-code-guide verifies agent dispatch + tier-loop conventions

### F.5 — validate-doc + cite-back resolution

Helper enforces:
- Frontmatter YAML-subset parses; required keys present per tier
- Each cite-back `file:line` or `file:start-end` resolves: file exists, line range within file's line count
- For Vue cite-backs (`<f>.vue:N` form): if `<f>.vue.ts.map` exists at `.devforge/vue-tmp/<rel>.vue.ts.map`, verify the cite resolves through E.1.b sourcemap (i.e., the original `.vue:N` corresponds to a valid `.vue.ts` mapped position when run forward). This catches LLM-fabricated lines.
- Density: no banned phrases (regex list); per-bullet ≤ 120 chars; hazard requires cite
- Section anchors present per tier

Test scope (`tests/lib/test_validate_doc.py`):
- Concern doc with valid frontmatter + 3 sections + valid cites → passes
- Hazard without cite → fails with clear error
- Banned phrase ("This document...") → fails
- Cite-back to nonexistent line → fails
- Vue cite-back with broken sourcemap chain → fails
- Frontmatter missing required key → fails

#### Verify F.5
- 8+ test cases green
- Live run on a hand-authored doc validates without false-positives/negatives

### F.6 — Empirical verification on testForge20

After F.1–F.5 ship:

1. Reset testForge20 state (full).
2. update.sh syncs F.2–F.5 helpers + spec + agent.
3. Re-index testForge20 (post vue-extract; verify .vue.ts in graph).
4. Run /generate-docs full. Capture metrics:
   - Dispatch count: 1 (project overview) + 1 (project arch) + 8×3 (package tier) + ~64 (concerns) ≈ 90
   - Wall-clock: target 10–20 min
   - Token cost: target $10–25 Haiku
   - Validation pass rate: target ≥ 95% on first dispatch; ≤ 2 retries per failed doc
5. Read 3 sampled docs: 1 concern (order/), 1 package (app-web/architecture.md), 1 project (overview.md). Compare quality vs raw `agentic_context` output for the same scope.
6. Incremental run: touch one file in helpers concern; re-run; verify only helpers concern doc regenerates (others skip via source_stamp match).

#### Verify F.6
- Full run: 80–95 dispatches; wall-clock ≤ 20 min; cost ≤ $25; validation pass rate ≥ 95%
- Incremental run: touched-concern doc regenerates, untouched concerns skip
- LLM-first density: hand-eyeball that docs read as concise prompt fragments, not human-onboarding wikis

### F.7 — Package-tier docs

Three docs per package:
- `docs/<package>/overview.md` — package role + concern enumeration
- `docs/<package>/architecture.md` — layers + patterns

Each generated by ONE doc-composer dispatch with package-input helper output. Helper input: package's index.json file list + per-concern overview seeds (read from already-generated concern docs at this phase) + selected README/comment-dense files at package root.

Concern-tier docs MUST exist before package tier dispatches (overview's "Concerns" list reads from concern doc frontmatter). Phase ordering locked bottom-up: concerns → packages → project (matches F.4 phases 3 → 4 → 5).

#### Verify F.7
- Package tier helper test: 4+ cases (input shape, overview seed read from concern frontmatter, architecture pattern extraction signal, missing concern seeds → graceful warning)
- Live: app-web package generates all 3 docs cleanly

### F.8 — Project-tier docs (DONE)

Two docs at project root:
- `docs/overview.md` — project purpose + package map (sections: `## Purpose`, `## Packages`)
- `docs/architecture.md` — cross-package architecture + cross-cuts (sections: `## Layers`, `## Cross-Cuts`)

Generated orchestrator-direct via the existing `init-doc` → setters → `render-doc` chain (NO subagent dispatch — F.8 mirrors F.4/F.7 design). Helper input: `project-input` batch JSON with `package_seeds[]` (frontmatter + Purpose text from each rendered package overview) + `project_root_files[]` (top-level README/CHANGELOG/package.json comment-rich spans) + `source_stamp`.

Components shipped:
- F.8a: `project-input` helper (`_project_input.py`, 12 tests)
- F.8b: project-tier setters
  - init-doc accepts `tier in (project-overview, project-architecture)` with skeleton templates
  - set-doc-purpose extends to `project-overview`
  - set-doc-layers extends to `project-architecture`
  - new `set-doc-packages` (project-overview)
  - new `set-doc-cross-cuts` (project-architecture)
  - 14 tests in `test_doc_setters_project.py`
- F.8c: validate-doc extends with `_PROJECT_OVERVIEW_REQUIRED_SECTIONS` + `_PROJECT_ARCHITECTURE_REQUIRED_SECTIONS`; project tier doc paths resolve to `docs/<filename>` (no per-target subdir)
- F.8d: Phase 4 wiring in `src/commands/generate-docs/main.md`

Project tier docs live at `docs/<filename>` (NO `<target>` subdir). `--target` arg used as the H1 label only.

#### Verify F.8
- 12 helper tests + 14 setter tests + 4 validator tests green
- Live: testForge20 V6 smoke (run /generate-docs after package tier completes for >=1 package; project tier dispatches against the rendered package overviews)

### F.9 — Per-command read-tier specs

Update consumer commands so they encode (a) preflight invocation as the first step and (b) the layered read order for narrative + structural lookups:

| Command | Step 1 (always) | Step 2+ (read tier) |
|---|---|---|
| `/research` | preflight | concern md → architecture.md → CBM (`agentic_context` + `search_graph` + `search_code` for fuzzy term lookup) → source (Read) |
| `/specify` | preflight | concern md → architecture.md → constitution.md → CBM (verify constraints) → user clarifications |
| `/plan` | preflight | architecture.md → CBM (`trace_path`, `agentic_impact`) → constitution.md |
| `/breakdown` | preflight | plan.md (input) + concern md per affected concern → CBM for any unresolved structural question |
| `/execute-task` | preflight | task.md (input) + CBM (function-level `get_code_snippet`) → source |
| `/fix` | preflight | CBM (locate fault) → source → docs (verify hazard awareness for that concern) |
| `/refactor` | preflight | CBM (find usages) → source → concern md (avoid touching documented hazards) |
| `/audit` | preflight | CBM (`agentic_quality`) + walk docs/ for stale frontmatter (preflight already surfaces this list as `concerns[].status="changed"`) |

Each command spec gets one short paragraph: "Before authoring/executing, invoke `generate_docs_helper preflight` (skipped if `.devforge/.preflight-stamp` is fresher than 60s). Then consult [tier list]. Use CBM tools for any structural lookup; consult docs/ for narrative orientation."

The 60-second freshness shortcut prevents preflight thrashing when several commands chain in the same session (e.g., `/research` → `/specify` → `/plan` within minutes).

#### Verify F.9
- 8 command specs updated
- instruction-author + instruction-reviewer pass on each
- claude-code-guide verifies CBM tool name conventions per command
- Each updated command spec mentions `preflight` as Step 1 and references the 60s stamp shortcut

### F.10 — Template directory rules

Update `src/CLAUDE.md` template + storage-rules:
- Drop `docs/api/`, `docs/features/`, `docs/guides/` from documented layout
- Add canonical layout (per "docs/ canonical layout" section above)
- Document the LLM-first density format expectation
- Document that md files are CBM-indexed automatically (no separate registration)

#### Verify F.10
- Template diff reviewed by instruction-author
- One end-to-end install on a fresh project confirms layout matches template

### F.11 — CBM-first enforcement hooks (sgaabdu4-style)

F.9 documents the soft read-tier order in command specs ("consult preflight → docs → CBM → source"). F.11 makes it ENFORCEABLE at the Claude-Code tool-call level via four hooks at `~/.claude/hooks/` (or, for project-scoped enforcement, `<project>/.claude/hooks/`). Pattern adopted from `sgaabdu4/claude-code-tips` (https://github.com/sgaabdu4/claude-code-tips/tree/main/hooks).

| Hook | Event | Purpose |
|---|---|---|
| `cbm-code-discovery-gate` | PreToolUse on Read/Grep/Glob | Advisory message: "consider `search_graph` / `agentic_context` / `search_code` before text search". Exit code 0 (non-blocking) |
| `cbm-mcp-marker` | PostToolUse on Bash + MCP tools | Telemetry: marks each CBM tool invocation in the transcript so adoption is measurable |
| `cbm-session-reminder` | SessionStart (resume / clear / compact) | Re-injects CBM-first protocol when the prior context window is dropped |
| `bash-ban-raw-tools` | PreToolUse on Bash | Soft-rejects raw `grep`/`find`/`cat` patterns over source files; suggests CBM equivalent |

**F.11.a — Hook reference scripts** ship in `src/devforge/hooks/` (or similar). Each hook is a stand-alone shell/python script that consumes the Claude Code hook JSON contract on stdin and emits the appropriate response.

**F.11.b — install.sh / wizard integration**:
- Wizard prompts: `Install CBM-first enforcement hooks to .claude/hooks/? (recommended for /research /specify /plan workflows) [yes/no]`.
- On `yes`: copy hook scripts to `<target>/.claude/hooks/` (presence-guarded; never overwrite existing same-named hooks) and add their entries to `<target>/.claude/settings.json` under the appropriate event arrays.
- On `no`: skip; user can re-run wizard or manually copy later.

**F.11.c — CLAUDE.md template documentation**:
- Section "CBM-first protocol enforcement" describes each hook's role + how to disable individually + linkback to sgaabdu4 reference.

#### Verify F.11
- 4 hook scripts authored + manually invoked against sample tool-call JSON to confirm exit codes + stderr messages
- install.sh adds the hooks (presence-guarded) on wizard `yes`; doesn't overwrite custom hooks; doesn't error when `~/.claude/hooks/` lacks settings.json keys
- Empirical: in testForge20, run /research with hooks active; confirm `cbm-code-discovery-gate` fires when Claude tries Read/Grep/Glob on source files; confirm `bash-ban-raw-tools` fires on naive grep
- Documentation: CLAUDE.md template has the section; instruction-author + claude-code-guide sign off on hook contract conventions

---

## Disposition of prior work

| Artifact | Disposition under Plan F |
|---|---|
| `src/devforge/lib/_generate_docs/_sourcemap.py` + tests | KEEP — F.2 consumes via `nearest=True` |
| `src/devforge/lib/vue-extract` | KEEP — pre-pass for CBM index |
| `src/devforge/lib/vue-to-ts.mjs` | KEEP — invoked by vue-extract |
| `src/mcp.json` | KEEP — codebase-memory-mcp registered |
| `src/commands/generate-docs/main.md` (iteration scaffold) | REWRITE under F.4 |
| `src/agents/tree-annotator.md` (Part D) | DEPRECATE active flow; KEEP file as historical reference |
| Plan B per-md helpers (`render-file-skeletons`, `write-file-doc`, etc.) | KEEP DORMANT — Plan F doesn't revive but they remain available primitives |
| Part D `_validators_concern.py` rule chain | REPLACE with F.5 `validate-doc` (multi-tier) |
| Part D `_setters_concern.py` setters | REWRITE under F.4 setter primitives list |
| Part A `_check_file_docs_complete` | KEEP DORMANT |
| `_md_frontmatter.py` | KEEP — F.5 uses for parse + write |

---

## Risks + open questions

### Collapsed by F.0 preflight (no longer risks)

- ~~**"Did I remember to reindex?"**~~ — F.0 forces vue-extract + index_repository on every entry-point invocation. Stale-mirror and stale-graph cite-back drift become impossible.
- ~~**Wasted LLM spend on unchanged concerns**~~ — F.0.b stamp gate skips dispatch for `unchanged` concerns.
- ~~**CBM unavailability mid-run**~~ — Preflight hard-checks `command -v codebase-memory-mcp` and aborts with install instructions before any other phase runs. Same check applies to all F.9 consumer commands via the preflight invocation.

### Open

1. **Source stamp granularity**. F.2's `source_stamp` SHA over subfolder content lets F.0/F.4 skip unchanged concerns. Risk: noise edits (whitespace, comment-only changes) trigger needless regeneration. v0 = strict byte hash; v0+1 = AST-aware hash. Defer.

2. **Cite-back for cross-cuts on regenerated source**. If a Layers/Patterns/Cross-Cuts cite-back's source line drifts (refactor inserts a line above), the cite goes stale. F.5 detects via line-content hash; F.0 incremental regen rebuilds the affected doc when its stamp shifts. Acceptable. (Concern docs have no cite-backs, so this risk only applies to package + project tiers.)

5. **Order-of-tiers with frontmatter dependencies**. Package overview reads concern docs' frontmatter; project overview reads package docs' frontmatter. Bottom-up order locked: concerns → packages → project. F.4 enforces.

6. **Density-cap regressions**. doc-composer might drift to verbose prose in long sessions. F.5 validate-doc rejects banned phrases + length cap violations; orchestrator re-dispatches with the failure message. Cap at 3 retries; on 4th, surface to user.

7. **Vue cite-back through sourcemap**. Hazards in Vue concerns must cite `.vue:line`. Composer reads `.vue.ts:line` from helper input + applies E.1.b nearest mode. Helper validates the resolution end-to-end.

8. **Path canonicalization** (residual one-time hardening, not freshness). Map's `sources[0]` is path RELATIVE to .map dir; helper must canonicalize to project-root-relative for downstream cite-validate. Verify via end-to-end smoke under F.5.

9. **Multi-source map reject**. v0 hard-rejects multi-source maps. vue-to-ts emits single-source only; if toolchain ever emits multi-source (post-bundling, etc.), revisit. No incidence yet.

10. **Template-only `.vue` fallback**. Vue files with no `<script>` block emit a stub `.vue.ts` containing `export default {}`. CBM indexes the stub; graph returns no Functions. concern-composer must still emit tree entry + filename-inferred annotation; helper must not crash on empty span. Already specified.

11. **Preflight thrashing**. Multiple consumer commands chained in one session (e.g. `/research` → `/specify` → `/plan`) would each re-run vue-extract + index_repository (~15-30s each). Mitigation: F.9's `.preflight-stamp` 60s freshness check; preflight skips its mechanical phases when the stamp is fresh. Stamp gate inside preflight still runs (cheap; ms).

---

## When resuming work

1. Read `CLAUDE.md` (project root, auto-loaded).
2. Read `VALIDATOR-LOOP-PLAN.md` (Part A history, frozen).
3. Read `VALIDATOR-LOOP-B-PLAN.md` (Part B retired + Part D revert note).
4. Read this file (Plan F, active).
5. Determine current step:
   - F.0 not started → build preflight subcommand + tests
   - F.4 in progress → continue setter primitives + Phase wiring
   - F.5 in progress → continue validate-doc helper
   - etc.
6. Files NOT to delete (Plan F + earlier artifacts):
   - `src/agents/tree-annotator.md` (Part D historical)
   - `src/devforge/lib/_generate_docs/_md_frontmatter.py` (generic util)
   - `src/devforge/lib/_generate_docs/_setters_concern_files.py` (per-md helpers, dormant)
   - `src/devforge/lib/_generate_docs/_validators_file_doc.py` (per-md validators, dormant)
   - `src/devforge/lib/_generate_docs/_sourcemap.py` (E.1; F.1 consumes)
   - `src/devforge/lib/vue-to-ts.mjs` + `vue-extract` launcher
7. Run full test suite at every step; baseline 938 OK + 3 skipped (post-E.1.b).
8. Clear `src/devforge/.generate-docs-trace.log` before each test run (circuit-breaker invocation budget).

---

## Memory bookmarks (for fresh-session resume)

- `project_cbm_integration_plan_e.md` — pointer to this file (renamed contents to F semantics; bookmark name retained for stability)
- After F.2 lands → update bookmark with "F.2 done; F.3 next"
- Same pattern per step

---

## References

- `VALIDATOR-LOOP-PLAN.md` — Part A history (annotations-in-state, retired)
- `VALIDATOR-LOOP-B-PLAN.md` — Part B history + Part D revert note
- Plan E (this file at commit `3223c90` and earlier) — pre-pivot scope; superseded
- E.1 sourcemap module: commit `b08fdfd` (initial) + `3223c90` (nearest mode)
- vue-to-ts source map fix: commit `fc5fad8`
- vue-to-ts walk-down resolver: commit `b5e2a3a`
- vue-extract launcher rename: commit `f2c4631`
- Iteration scaffold + topology lock: commit `8126443`
- codebase-memory-mcp: https://github.com/DeusData/codebase-memory-mcp
- Memory rules: `feedback_helper_owns_shape_principle`, `feedback_zero_escape_hatch_policy`, `feedback_test_first_python_helpers`, `feedback_sentence_level_hallucination_check_specs`, `feedback_dual_agent_verify_command_statements`, `feedback_helper_owns_contract_filesystem_forcing`, `feedback_cbm_search_graph_pattern_keys`
