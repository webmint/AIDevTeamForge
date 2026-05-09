# Session summary 2026-05-09 → 2026-05-10

Hand-off to next session. Two goals for next session encoded below: (1) cleanup obsolete plan files; (2) keep this doc + active plans only.

## What shipped this session (commits on `develop-2.0-init`)

Branch is **12 commits ahead** of last checkpoint. Suite green at **1358 passed, 11 skipped, 0 failures**.

| # | SHA | Type | Summary |
|---|---|---|---|
| 1 | `551ab69` | plan | JUDGMENT-LAYER-PLAN — final feature plan committed as plan-of-record |
| 2 | `543a1c2` | plan | Pre-req commit dropped — `_preflight.py:326-410` already shells out to CBM `index_repository`; /init-forge spec change unnecessary |
| 3 | `a6a303f` | feat | Step 0 substrate — `_doc_corpus.py` (5 helper functions: walk / extract terms / validate cite paths / get section span / noise filter) + `_merge_project_skeleton` declared-order insertion fix (HIGH-severity anchor-prefix bug prevented) |
| 4 | `a35be1f` | feat | ~~Track A.1 helper — `set-overview-suggested-research-starts`~~ (rolled back below) |
| 5 | `cd56713` | docs | ~~Track A.2 spec — `Suggested Research Starts` compose step~~ (rolled back below) |
| 6 | `e26c472` | docs | ~~Track A.3 cross-refs — CLAUDE.md / storage-rules~~ (rolled back below) |
| 7 | `432135a` | feat | **Track B.1 helper — `_glossary.py` (440 LOC) + `build-glossary-bundles` + `set-glossary-entries` SUBCMDS** — produces `docs/glossary.md` from CBM-augmented term bundles + LLM definitions; validator enforces 30..150 entries, definition shape, cite-back, related-terms closure |
| 8 | `d673bf6` | docs | **Track B.2 spec — Phase B section in `/generate-docs`** + flipped line 247 contradiction (inline-Purpose disambiguation + project-tier `docs/glossary.md` co-exist truthfully) |
| 9 | `48af692` | docs | **Track B.3 cross-refs — CLAUDE.md / storage-rules / tech-writer.md (corrected stale references)** |
| 10 | `5d89924` | plan | **Step Z — annotated GENERATE-DOCS-PLAN.md Steps 6.2/6.3/6.4/6.5/6.6/6.7/6.8 as REJECTED or SUPERSEDED; declared `/generate-docs` FEATURE-CLOSED** |
| 11 | `b3563d0` | fix | Empirical fixes: `_validate_entries` cite-path bug (was `project_root`, now `project_root / "docs"`) + `_render_glossary` HTML escape (`<` `>` `&` → entities; prevents `BLoC<S>` triggering strikethrough in WebStorm md preview) |
| 12 | `f019968` | revert | **Track A rollback** — 540 LOC removed; YAGNI lesson logged in `feedback_track_a_yagni_rollback`. Coverage upper-bound mathematically too low (5-6 entries on 22-package monorepo); zero unique signal vs Entry Points + concern docs + CBM BM25; speculative consumer (`/research`) doesn't exist |

**Net feature delivered**:
- `_doc_corpus.py` substrate (5 reusable helpers; validate_cite_paths used by Track B)
- `_merge_project_skeleton` declared-order insertion fix (anchor-prefix bug prevention — HIGH-severity)
- `_glossary.py` Track B helper (`docs/glossary.md` rendering with CBM-augmented classification)
- `/generate-docs` Phase B (glossary) compose step in spec
- Cross-file refs propagated to CLAUDE.md template + storage-rules
- `/generate-docs` formally FEATURE-CLOSED (only bug-fix + CBM-API-evolution accepted thereafter)

**Empirical run on testForge20 (2026-05-10)** confirmed:
- Concern + package tiers stamp-gate correctly skip unchanged content
- Project tier rebuild required manual stamp bust (anchor-schema-drift detection deferred — known-bug logged)
- Glossary: 80 candidates → 22 noise-filtered → 58 final entries; 0 [TODO: human-define]; all classified prose-only (CBM `query_graph WHERE n.name=<term>` exact-match misses TS PascalCase qualified names; classification quality depends on a name-normalization tweak — deferred)
- Validator path bug + renderer escape bug surfaced + fixed in `b3563d0`

## What was tested empirically — 2 real diagnosis tickets

| Ticket | Diagnosis path | Pipeline contribution | Net verdict |
|---|---|---|---|
| **Alert content not sorted in Quote & Order** (testForge20) | docs+CBM only first → CBM identified `AlertResolverChoices.vue:203` `.sort((a,b) => choicesOrderStatus[a.status] - choicesOrderStatus[b.status])` — sorts by status field not display name; status-collision causes apparent randomness | CBM 95%, concern docs 5%, SRS 0%, glossary 0% | docs+CBM sufficient; SRS+glossary contributed nothing |
| **`[Vue warn]: injection "notificationsBLoC" not found`** | docs+CBM identified provide-vs-inject mismatch (App.vue:62 component-level provide; vendor `@doosanica/db-widgets-ui` injects from Pinia store factory context) | CBM 70%, concern docs 25%, SRS 0%, glossary 0% — **but** main-branch `/research` flow produced a structurally better report (4 hypothesis emitter categories enumerated, diagnose-first via `app.config.warnHandler` recommended); this session's flow stopped at first plausible theory | Main-branch `/research` won — process scaffolding (Approaches A/B/C section in /research spec) forced fix-breadth that this session's free-form output missed. Cause-side hypothesis-enumeration NOT in /research either; came from model judgment |

**Lesson logged** in `REDESIGN-RESEARCH-PLAN.md` Findings §2: hypothesis-enumeration + diagnose-first discipline as new mandatory output schema for /research redesign.

## Current state of /generate-docs

**FEATURE-CLOSED** as of `5d89924`. Bug fixes + CBM-API-evolution adjustments only.

Active surfaces:
- Phase 0 — pre-flight gate (devforge dir + CBM binary check)
- Phase 1 — preflight (vue-extract + index_repository + concern stamp diff)
- Phase 2 — concern tier (concern docs with Purpose paragraph + structure tree)
- Phase 3 — package tier (overview + architecture per package, 8-section validator)
- Phase 4 — project tier (overview.md + architecture.md, 11-section overview, 8-section architecture)
- **Phase B — glossary (`docs/glossary.md` via build-glossary-bundles + set-glossary-entries)**
- Phase 5 — verify (defensive validate-doc on rendered files)
- Phase 6 — report (counts + glossary line item)

Helper code lives at `src/devforge/lib/_generate_docs/` and is invoked via `.devforge/lib/generate_docs_helper <subcmd>`.

## Deferred / known bugs (not blocking)

1. **Stamp gate doesn't detect owned-anchor schema drift** — when `_PROJECT_OVERVIEW_OWNED_ANCHORS` gains a new entry, existing project's `source_stamp` may still match → phase skipped → new anchor never lands. Workaround: bust source_stamp manually or delete `docs/overview.md`. Real fix: detect anchor-schema drift in stamp comparison.
2. **CBM watcher async-miss on freshly-written files** — `docs/glossary.md` did not appear via watcher; required explicit `index_repository mode=full` to surface as File + Section nodes. Pre-existing CBM behavior; flag if it bites.
3. **Glossary classification name-normalization** — `query_graph WHERE n.name='<term>'` exact-match misses TS PascalCase qualified names; testForge20 run produced 58 entries all prose-only (zero code-anchored / fuzzy-anchored). Classification works in code but doesn't fire on real CBM data without name normalization (try short-name + qualified-suffix lookups in `_classify_term`).

## Memory updates this session

- `feedback_command_spec_single_responsibility.md` (NEW) — command spec steps run + verify only; no downstream speculation
- `project_judgment_layer_empirical_validated.md` (NEW) — testForge20 empirical run details, deferred bugs
- `feedback_track_a_yagni_rollback.md` (NEW) — coverage-check + unique-signal-check + real-consumer-check before authoring curated-content surfaces
- `project_judgment_layer_plan.md` (UPDATED) — Track A rolled back; Track B + Step 0 retained; /generate-docs FEATURE-CLOSED

## CLEANUP CHECKLIST FOR NEXT SESSION

Files at repo root with status. Next session should review + delete obsolete plan files. Don't delete CLAUDE.md / README.md / CHANGELOG.md / DEVELOPMENT-STATUS.md / this file.

| File | Status | Action |
|---|---|---|
| `ARCHITECTURE-PIVOT-PLAN.md` | active (Steps 2-8 still pending) | KEEP |
| `CBM-INTEGRATION-PLAN.md` | F.11 shipped earlier this session (commits 65b0a24/e0ca9bb/cdddf76) | DELETE — superseded by shipped state + `project_track1_f11_hooks_shipped.md` memory |
| `CHANGELOG.md` | git-history aggregate | KEEP |
| `claude-r3-interview.md` | interview transcript, historical | DELETE — preserve in Obsidian if user wants the artifact |
| `CLAUDE.md` | repo conventions | KEEP |
| `CODEGRAPH-INTEGRATION-PLAN.md` | codegraph deferred per memory `project_codegraph_state_2026_05_06` (LLM-mode broken, abandoned) | DELETE — fully superseded |
| `CODEX-REMOVAL-PLAN.md` | active on `feature/codex-remove` branch | KEEP (or DELETE if codex-removal merged + branch closed) |
| `DEVELOPMENT-STATUS.md` | aggregate framework status | KEEP |
| `GENERATE-DOCS-EXECUTION-LOG.md` | per-session execution log, historical | DELETE — preserve in Obsidian if needed; git history covers commits |
| `GENERATE-DOCS-PLAN.md` | feature-closed per Step Z (5d89924) | KEEP for historical record (annotated SUPERSEDED/REJECTED inline) OR DELETE if user wants clean tree — RECOMMEND DELETE since /generate-docs is closed and the annotated steps are pure historical context |
| `JUDGMENT-LAYER-PLAN.md` | feature-closed; Track A rolled back; Track B shipped | DELETE — fully shipped + closed; memory `project_judgment_layer_plan.md` carries the summary |
| `NEXT-SESSION-DUMP.md` | prior session hand-off | DELETE — superseded by THIS file |
| `PENDING-CHANGES.md` | prior pending state | DELETE — current state in this file |
| `QUALITY-AUDIT.md` | old audit | DELETE — preserve in Obsidian if needed |
| `README.md` | public-facing | KEEP |
| `REDESIGN-RESEARCH-PLAN.md` | active; Findings §1 + §2 locked; work order TBD | KEEP |
| `run3-observations.md` | old run observations | DELETE |
| `SESSION-HANDOFF.md` | prior handoff | DELETE — superseded by THIS file |
| `SESSION-SUMMARY-2026-05-10.md` | THIS file | KEEP (until next session writes its own summary, then delete or rename to dated archive) |
| `structural-integration-check-plan.md` | historical | DELETE |
| `VALIDATOR-LOOP-A5-LAUNCH.md` | old launch doc | DELETE |
| `VALIDATOR-LOOP-B-PLAN.md` | per memory `project_validator_loop_part_b`, status was Part B planned (validator-loop pivot from annotations to per-file md docs); check current status before delete | REVIEW — if shipped or abandoned, delete; if active, keep |
| `VALIDATOR-LOOP-PLAN.md` | superseded by Part B | DELETE |

Estimated cleanup: **~12 files deleted** (~150KB freed), ~8 retained.

## ACTIVE PLAN-OF-RECORD AFTER CLEANUP

After cleanup, remaining plans at root:
- `ARCHITECTURE-PIVOT-PLAN.md` — pivot Steps 2-8 (Steps 1+ partially done)
- `CODEX-REMOVAL-PLAN.md` — if branch still open
- `REDESIGN-RESEARCH-PLAN.md` — /research command redesign with locked Findings §1 (CBM discovery chain) + §2 (hypothesis-enumeration + diagnose-first)
- `VALIDATOR-LOOP-B-PLAN.md` — IF still active

Plus:
- `CLAUDE.md` — conventions
- `README.md` — public
- `DEVELOPMENT-STATUS.md` — framework status
- `CHANGELOG.md` — history

## Recommended next session priorities

1. **Cleanup** per checklist above (single bulk commit `chore: cleanup superseded plan files`)
2. **/research redesign** — highest-leverage next move per this session's empirical finding that diagnosis-quality bottleneck is process-scaffolding, not docs/. Findings §1 + §2 are locked; need spec body + dispatch. See `REDESIGN-RESEARCH-PLAN.md` Work order steps 1-6.
3. **(Optional) Glossary classification name-normalization** — small `_glossary.py` patch in `_classify_term` to try short-name + qualified-name lookup variants. Unblocks code-anchored / fuzzy-anchored classification on real CBM data.
4. **(Optional) Stamp gate anchor-schema drift detector** — small fix to project-tier rebuild trigger when owned-anchors change. Workaround acceptable for now.

## How to resume

1. Read this file in full.
2. Read `CLAUDE.md` for repo conventions (especially audit format + working process).
3. Read auto-loaded memory index (focus: `project_judgment_layer_plan.md`, `project_judgment_layer_empirical_validated.md`, `feedback_track_a_yagni_rollback.md`).
4. Check branch state: `git status && git log --oneline -15`.
5. Run cleanup commit per checklist.
6. Pick next priority + start.

Branch: `develop-2.0-init`. Suite: 1358 passed, 11 skipped.
