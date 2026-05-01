---
description: Generate per-package documentation via the python-skeleton primitive. Read source, fill slots, run validate, render final docs.
---

# /generate-docs — per-package documentation via skeleton-fill

`/generate-docs` produces per-package documentation under `docs/<package-path>/index.md` for the project. The mechanism is the **skeleton-fill primitive**: `.devforge/lib/generate_docs_helper render-package-skeleton` writes a markdown skeleton with `[TODO]` slots, the orchestrator (or a tech-writer subagent in canonical mode) fills slots by reading source and invoking setters, `validate-package` checks structure and citation fidelity, and `render-package-doc` renames `.skeleton` → `.md` once validation passes. The helper owns markdown structure, section ordering, and citation format — the LLM contributes only values.

This command will replace `/onboard` once empirical iteration locks the output shape.

---

## ⚠️ ITERATION MODE — APP-WEB ONLY (TEMPORARY)

**This override is in effect until removed.** Multi-package iteration is paused; this run validates output shape on a single unit before broader rollout.

**A/B comparison run**: Phase 3 in this version is configured for orchestrator-direct slot-fill (no tech-writer subagent dispatch). Option A used a tech-writer subagent — that produced coverage degradation + contract breaks (direct JSON edits bypassing the helper API). This run tests whether orchestrator-direct produces comparable or better output without those failure modes.

For this run, `/generate-docs` operates in single-package verification mode:

| Phase | Behavior |
|---|---|
| Phase 0 — Pre-flight | Run normally |
| Phase 1 — Discover the assigned package | **Override** — package is hardcoded to `db-cse-ui-strata/apps/app-web`. Skip the multi-package iteration loop that the full flow would run. |
| Phase 2 — Register package + extract scripts | Run normally for the single package |
| Phase 3 — Render skeleton, fill slots inline (orchestrator-direct), then fan out concern-tier subagents | Run **once** for `db-cse-ui-strata/apps/app-web` only; orchestrator fills the package doc inline (A/B option B), then dispatches one `concern-slot-filler` subagent per substantive subfolder under `src/`. The run produces 1 package doc plus N concern docs (not a single-doc output). |
| Phase 4 — Verify the produced doc | Run normally |
| Phase 5 — Report | Run normally; explicitly note iteration scope |

Pre-existing `docs/` content under any path other than `docs/db-cse-ui-strata/apps/app-web/` is left untouched in this mode.

**Removing this override:** when the output shape is locked (per the iteration plan that drives this command), delete this entire `## ⚠️ ITERATION MODE` section. The full multi-package flow resumes via the corresponding spec edit that lifts iteration scope at that time.

---

## Phase 0 — Pre-flight

**Wall-clock telemetry (mandatory for cost visibility):** record the wall-clock time at the entry of each phase (Phase 0 entry, Phase 1 entry, ..., Phase 5 entry) into a session-local variable. At Phase 5's report, compute deltas and emit them as the phase-timing table (see Phase 5). The recording is in-session memory only — no persistence required, no helper invocation. The orchestrator's own clock (whatever Claude Code's environment exposes) is sufficient.

Verify, in order:

1. `.devforge/init.yaml` exists. If absent, tell the user to run `/init-forge` first and stop.
2. `.devforge/lib/generate_docs_helper` exists and is executable. If missing, the install is incomplete — tell the user to re-run `install.sh` and stop.
3. The target package path `db-cse-ui-strata/apps/app-web/` exists relative to the install root. If absent, tell the user the path is missing and ask whether they want to abort or supply a different path; do not proceed silently.
4. Inspect `.devforge/.generate-docs-state.json`. If absent, proceed (clean run). If present, run `.devforge/lib/generate_docs_helper status` to see which packages are registered, then branch:
   - **Target package already registered** (`db-cse-ui-strata/apps/app-web` appears in status output): the prior run's state will block `add-package` re-registration in Phase 2 (the helper rejects duplicate `add-package` by design — see `_setters.py` `cmd_add_package`). Ask the user via AskUserQuestion (single-line prompt: `Prior run state for app-web exists. Reset and start fresh, resume by filling missing slots only, or abort?`) with options **Reset** (default — invoke `.devforge/lib/generate_docs_helper reset`, then proceed to Phase 1 normally), **Resume** (skip `add-package` only; for each scalar `set-package-*` setter — language / framework / build-tool — check current state via `status` first and re-run the setter ONLY if the field is currently `null`/unset; ALWAYS run `extract-package-scripts` and the `add-package-script` loop because script registration is append-only and the helper rejects duplicate `script-name` entries with exit 2, so duplicates are silently skipped while missing scripts are added; after the conditional re-run, proceed to Phase 2's verification gate at step 7 before proceeding to Phase 3), **Abort** (stop and let the user reconcile manually). Default to **Reset** because iteration mode treats each run as a fresh attempt unless the user opts to resume.
   - **Only a different package registered** (target not in status output): no action needed — `add-package` for `db-cse-ui-strata/apps/app-web` will succeed; existing legacy package state remains untouched.

   Note: this reset-first prompt is specific to iteration mode (single-package, repeated runs on the same package are expected). When the `## ⚠️ ITERATION MODE` section is removed, the multi-package flow handles per-package state differently and this check will be revisited.

## Phase 1 — Discover the assigned package

The hardcoded package for this iteration is `db-cse-ui-strata/apps/app-web`. Read the package manifest at `db-cse-ui-strata/apps/app-web/package.json` to confirm ecosystem signals. From the manifest, identify:

- `primary_language` — TypeScript (when `package.json` lists `typescript` in `devDependencies` or the project includes a `tsconfig.json`)
- `framework` — Vue 3 (when `package.json` lists a `vue` dependency at version `3.x`)
- `build_tool` — Vite (when `package.json` lists `vite` in `devDependencies`)

If any of those signals is absent or ambiguous from the manifest, ask the user for the value rather than guessing.

## Phase 2 — Register package + extract scripts

Invoke the helper in this order. Each call's exit code 0 is required before proceeding to the next.

1. `.devforge/lib/generate_docs_helper add-package --path db-cse-ui-strata/apps/app-web --name app-web`
2. `.devforge/lib/generate_docs_helper set-package-language --path db-cse-ui-strata/apps/app-web --value typescript`
3. `.devforge/lib/generate_docs_helper set-package-framework --path db-cse-ui-strata/apps/app-web --value "Vue 3"`
4. `.devforge/lib/generate_docs_helper set-package-build-tool --path db-cse-ui-strata/apps/app-web --value vite`
5. `.devforge/lib/generate_docs_helper extract-package-scripts --path db-cse-ui-strata/apps/app-web` — capture stdout (a JSON object mapping script names to commands).
6. For each `(name, command)` pair in the JSON output of step 5: `.devforge/lib/generate_docs_helper add-package-script --path db-cse-ui-strata/apps/app-web --script-name <name> --command <command>`

If `extract-package-scripts` returns an empty JSON object (no scripts in `package.json`), step 6 is a no-op.

7. **Phase 2 verification gate (hard requirement; blocks Phase 3 entry).** This gate runs after every Phase 2 invocation regardless of whether Phase 0 routed via Reset or Resume. Invoke `.devforge/lib/generate_docs_helper status` and confirm the state for the target package shows:
   - `language` is a non-null string
   - `framework` is set (a non-null string for typical web/app packages; explicitly empty via `set-package-framework --value ""` only when the package legitimately has no framework — must be a deliberate choice, not a silent skip)
   - `build_tool` is set (same rule as `framework`: deliberate empty via `--value ""` is allowed; silent `null` is not)
   - `scripts` count is > 0 (0 is acceptable only when the manifest has no scripts block AND the ecosystem provides no defaults — `extract-package-scripts` emits ecosystem defaults for Rust / Go / Java / Maven / etc., so 0 should be rare)

   If ANY required field is missing or the script count is unexpectedly 0, do NOT proceed to Phase 3. Re-run the corresponding setter:
   - `language` missing → `.devforge/lib/generate_docs_helper set-package-language --path db-cse-ui-strata/apps/app-web --value <detected>`
   - `framework` missing → `.devforge/lib/generate_docs_helper set-package-framework --path db-cse-ui-strata/apps/app-web --value <detected from manifest>` (or `--value ""` only if the package legitimately has no framework)
   - `build_tool` missing → `.devforge/lib/generate_docs_helper set-package-build-tool --path db-cse-ui-strata/apps/app-web --value <detected from manifest>` (same rule)
   - `scripts` empty → re-run `extract-package-scripts --path db-cse-ui-strata/apps/app-web` and loop `add-package-script` per entry

   After re-running, invoke `status` again and verify all fields populated. Cap retries at 3; if the gate still fails after 3 attempts, surface the failure to the user (which field, which setter, what error) and ABORT before Phase 3 starts.

   This gate exists because LLM Phase 2 dropout (skipping setters silently) was empirically observed in a prior iteration run — `framework=null`, `build_tool=null`, `scripts={}` despite the spec instructing the setters. `validate-package` does not catch this because those fields are schema-optional. The verification gate is the explicit "did Phase 2 actually do its job" check.

## Phase 3 — Render skeleton, fill slots inline (orchestrator-direct)

**Note (option B — A/B comparison run)**: This phase is currently configured for orchestrator-direct slot-fill (no tech-writer subagent). The tech-writer SKELETON-FILL MODE contract still exists in `.claude/agents/tech-writer.md` and can be dispatched in a future run by replacing this phase with the dispatch step. For empirical comparison purposes, run this phase inline first; if quality matches/exceeds tech-writer-mediated runs, this becomes the canonical Phase 3.

1. Invoke `.devforge/lib/generate_docs_helper render-package-skeleton --path db-cse-ui-strata/apps/app-web` — produces `docs/db-cse-ui-strata/apps/app-web/index.md.skeleton` with `[TODO]` slots for the fields not yet set.

2. Read the resulting skeleton to confirm it was written and to see the structure of `[TODO]` slots that need filling.

3. **Read source files** under `db-cse-ui-strata/apps/app-web/src/` to identify:
   - Public exports (functions, classes, types, constants, configs, components, plugins) that cross module boundaries — every `export` statement in `src/` is a candidate. Limit to genuine public boundary surface (not private helpers).
   - External dependencies (npm packages from `package.json` `dependencies`) and workspace-internal dependencies (`pkg-cse-*` packages — these are workspace-internal because they live in the same monorepo).
   - Hazards / mislogic observations: naming inconsistencies, performance pitfalls, type-safety gaps (e.g., `@ts-ignore`, `any` casts), v1/v2 coexistence patterns, internal duplication, cross-feature inconsistencies, complexity hotspots. Use the closed `HazardCategory` enum: `naming|performance|type-safety|duplication|inconsistency|v1-v2-coexistence|complexity`.
   - Usage example: a real consumer pattern — typically the package's `main.ts` or `App.vue` showing how the package is bootstrapped/consumed.
   - Consumer pattern: a representative downstream call site — typically a composable that uses the package's API.

4. **Fill the slots via setter invocations**. Citation discipline is mandatory — every code-snippet setter requires `--cite-file` + `--cite-start` + `--cite-end` and the snippet MUST be lifted VERBATIM from the cited source line range (whitespace-normalized comparison runs at validate-time):
   - `set-package-overview` — 1-2 paragraph package overview (NEVER guess abbreviations; consult `README.md` at project root + at the package path for any acronym/initialism encountered before expanding it; if no authoritative definition found, use the abbreviation verbatim or mark with `[TODO: <abbreviation> — definition not found]`)
   - `set-package-tree` — ascii directory tree of `src/` (no other directories). The tree MUST include an inline `# <description>` comment after each substantive folder (folders, not files); the description is 3–7 words capturing what the folder contains and/or its architectural role. Trivial leaf folders (assets, generated output, fixtures) stay uncommented. Right-align the `#` column for readability — pad with spaces between the longest tree-glyph + folder name and the `#` marker so descriptions line up visually. Example format:

     ```
     src/
     ├── foo/          # domain entry points and routing
     ├── bar/          # shared composables and helpers
     │   └── assets/
     └── baz/          # cross-cutting type definitions
     ```
   - For each export: `add-package-export --name <n> --kind <k> --signature "..." --description "..." --language <l> --code-snippet "..." --cite-file <f> --cite-start <s> --cite-end <e>`
   - For each dependency: `add-package-dep --name <n> --kind internal|external --version <v> --purpose "..." [--consumer-location <loc>...]`
   - For each hazard: `add-package-hazard --category <c> --description "..." [--cite-file <f> --cite-start <s> --cite-end <e>]`
   - `set-package-usage-example --language <l> --code-snippet "..." --cite-file <f> --cite-start <s> --cite-end <e>`
   - `set-package-consumer-pattern --language <l> --code-snippet "..." --cite-file <f> --cite-start <s> --cite-end <e>`

5. **DO NOT make direct edits to `.devforge/.generate-docs-state.json`**. The helper API is the only sanctioned mutation path. If you hit a wall (e.g., `add-package-export` rejects a duplicate name when you need to update an existing entry, or the internal-dep validator rejects a workspace-internal dep that can't resolve in single-package iteration), DO NOT bypass the helper. Surface the wall to the user with a clear error message and ABORT before `validate-package` + `render-package-doc`. The walls are signals of helper-API gaps that need fixing — bypassing them produces factual errors in the doc (this empirically happened in option A's run: 19 workspace-internal deps were misclassified as external).

6. **Source-reading discipline**: read public-API-relevant files first (`src/composables/`, `src/helpers/`, `src/router/index.ts`, `src/main.ts`, `src/App.vue`, `src/types/`); only descend into implementation if a public symbol's signature is unclear. The package has ~900 source files; a thorough reading is impractical and unnecessary. Focus on boundary surface.

7. **Run `validate-package`**: `.devforge/lib/generate_docs_helper validate-package --path db-cse-ui-strata/apps/app-web`. On failure, read the structured error list (each error has `rule` / `field` / `message` / optional `diff`). Two error categories with different handling:
   - **Package-tier registration errors** (every `rule` value EXCEPT `decomposition`): fix by re-invoking the corresponding setter (re-registration overwrites for `set-*` setters; for `add-*` setters that reject duplicates, you must `reset` and re-fill OR surface the issue to the user). Cap retries at 3.
   - **Decomposition errors** (`rule: decomposition`): NOT setter-fixable. Each error names ONE substantive subfolder under `db-cse-ui-strata/apps/app-web/src/` with no registered concern. Capture this error list — it's the worklist for step 8's concern fan-out.

   Proceed to step 8 ONLY when the only outstanding errors are `rule: decomposition`, OR when validate-package exits 0. If non-decomposition errors persist after 3 retries, ABORT before step 8.

8. **Build the concern worklist** from step 7's `decomposition` errors. Each entry is the triple `(package_path, concern_name, subfolder)`:
   - `package_path` is `db-cse-ui-strata/apps/app-web` (iteration-mode hardcoded)
   - `concern_name` is the substantive subfolder's basename (e.g., `components`, `composables`, `helpers`)
   - `subfolder` is the relative path under `<package_path>/` reported in the decomposition error (e.g., `src/components`)

   If step 7 reported zero decomposition errors, skip steps 10–11 (no concerns to fan out) and proceed to step 12.

9. **Pause for user review before concern fan-out (mandatory checkpoint).** Before dispatching any `concern-slot-filler` subagent, summarize Phase 2 + 3-so-far outcome and ask the user to confirm fan-out. Specifically:
   - Run `.devforge/lib/generate_docs_helper status` and capture output.
   - Print a summary block to the user: package-tier counts (exports / dependencies / hazards / citations validated / scripts), the concern worklist (the N triples from step 8 — concern names + subfolder paths), and an estimate of the work ("N concern subagents will be dispatched sequentially").
   - Then prompt via AskUserQuestion (single-line prompt: `Phase 2 complete and N concerns ready to dispatch. Proceed?`) with options **Continue** (proceed to step 10 — sequential dispatch), **Inspect** (read `docs/db-cse-ui-strata/apps/app-web/index.md.skeleton` and copy its contents VERBATIM into the next user-facing message as a fenced code block — do not summarize or paraphrase — then re-prompt with the same Continue/Inspect/Abort options; Inspect is non-destructive and may be invoked any number of times), **Abort** (stop the command and state to the user: "Aborted before concern fan-out. State is preserved; re-run /generate-docs to resume.").

   **Why this gate exists:** empirical evidence from a `/generate-docs` run on testForge20 (2026-05-01) showed Phase 3's slot-fill loop running 50+ unattended helper invocations between user touchpoints. State-loss happened during fan-out and was only discovered post-run. A checkpoint here lets the user verify package-tier looks correct before triggering N concern dispatches that operate on the same state file. Per Claude Code auto-mode discipline, destructive operation classes (operations that mutate shared state extensively) need a human gate.

10. **Dispatch `concern-slot-filler` subagents SEQUENTIALLY — one Agent call per assistant message, wait for the subagent's return, then dispatch the next.** Do NOT use Claude Code's parallel-tool-call mechanism for concern dispatch. Each call uses `subagent_type: concern-slot-filler` with an inline prompt that supplies the four required inputs the agent expects (see `.claude/agents/concern-slot-filler.md`):
   - `package_path: db-cse-ui-strata/apps/app-web`
   - `concern_name: <basename>`
   - `subfolder: <relative path under package_path>`
   - `mode: fresh` if Phase 0 routed via Reset (or no prior state existed), `mode: resume` if Phase 0 routed via Resume

   **Why sequential, not parallel:** empirical evidence from a `/generate-docs` run on testForge20 (2026-05-01) showed parallel concern dispatch produced state-loss — the Phase 5 report documented 3 of 7 concerns reduced to empty shells in state despite their docs being rendered to disk earlier in the run (when slot data WAS populated). Either the helper's `_state_transaction()` lock failed under high concurrency or a subagent wrote empty values via setters. Until `tests/lib/test_state_concurrency_stress.py` empirically verifies parallel safety, sequential is mandatory. Trade-off: sequential dispatch costs more wall-clock for the iteration-mode single-package run; this is acceptable given the iteration's scope (1 package × ~7 concerns).

   **Resume-mode propagation is mandatory, not a hint.** If Phase 0 routed via Resume, every dispatched `concern-slot-filler` call MUST receive `mode: resume` so the subagent honors the slot-skip contract for any concern state already persisted. Mixing modes across concerns in one fan-out is forbidden — all-fresh or all-resume per run.

11. **Collect the per-concern reports.** Each subagent returns a single JSON line `{"concern": "<name>", "status": "ok|failed", "exports": <n>, "deps": <n>, "hazards": <n>, "errors": [...]}` plus a 2-3 sentence prose summary. Aggregate the JSON lines into a per-concern table for the Phase 5 report. If any concern reports `status: failed`, surface the error list to the user before proceeding to step 12 — do NOT silently ignore concern failures.

12. **Re-run `validate-package`**: `.devforge/lib/generate_docs_helper validate-package --path db-cse-ui-strata/apps/app-web`. With every substantive subfolder now registered as a concern, the decomposition gate should emit zero errors and validate-package should exit 0. If decomposition errors remain, the fan-out missed entries (subagents failed and produced no concern state, or the worklist was incomplete) — surface to the user and ABORT before step 13.

13. **Invoke `render-package-doc`**: `.devforge/lib/generate_docs_helper render-package-doc --path db-cse-ui-strata/apps/app-web` (renames `.skeleton` → `.md`). The helper internally re-runs validation; with step 12's clean exit, this succeeds and writes `docs/db-cse-ui-strata/apps/app-web/index.md`. Each concern's doc was already rendered by its dispatched `concern-slot-filler` subagent (the agent's final step). The package doc is the LAST thing rendered, after all concerns are in place — this ordering is required because `render-package-doc` rejects any outstanding decomposition errors.

14. **Out of scope** (do NOT invoke):
   - Architecture-tier subcommands (not part of Phase 3.2)
   - Memory archaeology subcommands (not part of Phase 3.2)
   - Multi-package iteration (the package loop is paused under the `## ⚠️ ITERATION MODE` section)
   - Modifying source files (read-only access to source)
   - Re-running `validate-package` between steps 7 and 12 (step 7 captures the worklist; step 12 confirms decomposition is clean — intermediate validates produce noise without progressing the flow)

## Phase 4 — Verify the produced doc

After Phase 3 completes:

1. Confirm `docs/db-cse-ui-strata/apps/app-web/index.md` exists (no `.skeleton` suffix). If it doesn't exist, validation must have failed during slot-fill — ask the user how to proceed (retry slot-fill, or abort).
2. Run `.devforge/lib/generate_docs_helper status` — exit 0, output should show one package registered with overview / tree / exports / deps populated.
3. Read `docs/db-cse-ui-strata/apps/app-web/index.md`. Copy its contents VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase).
4. Ask the user to evaluate the produced doc against the iteration plan's empirical baseline targets.

## Phase 5 — Report

After the user has the doc in front of them, print a summary:

- **Package**: `app-web` at `db-cse-ui-strata/apps/app-web`
- **Exports**: <count from state file>
- **Dependencies**: workspace-internal=<count>, external=<count>
- **Hazards**: <count>
- **Citations**: <count> (verified against source: <verified-count>, from `validate-package`'s structured output)
- **Final doc**: `docs/db-cse-ui-strata/apps/app-web/index.md`
- **Concerns processed**: <count> (from step 11's per-concern aggregation)
- **Per-concern summary** (from step 11's collected JSON lines):

  | Concern | Status | Exports | Deps | Hazards |
  |---------|--------|---------|------|---------|
  | <name>  | ok / failed | <n> | <n> | <n> |
  | …       | …      | …       | …    | …       |

  Concern docs are at `docs/db-cse-ui-strata/apps/app-web/<concern_name>/index.md`. If any row is `failed`, the corresponding concern doc is missing — surface those rows distinctly so the user can decide whether to retry the failed concerns.
- **Phase timing** (wall-clock per phase):

  | Phase | Duration |
  |---|---|
  | Phase 0 — Pre-flight | <Δ from phase 0 entry to phase 1 entry> |
  | Phase 1 — Discover the assigned package | <Δ to phase 2 entry> |
  | Phase 2 — Register package + extract scripts | <Δ to phase 3 entry> |
  | Phase 3 — Slot-fill + concern fan-out | <Δ to phase 4 entry> |
  | Phase 4 — Verify the produced doc | <Δ to phase 5 entry> |
  | **Total wall-clock** | <total> |

  This phase-timing table makes per-phase cost visible to the user post-run, addressing the "no per-step cost telemetry" gap surfaced by the audit. Helper-side per-invocation tracing lives separately in `.devforge/.generate-docs-trace.log` once implemented; not required for this phase-timing table — the orchestrator's wall-clock summary is sufficient on its own.

Tell the user: "This is single-package iteration; multi-package flow is paused under the `## ⚠️ ITERATION MODE` section of `/generate-docs`. Re-run after the iteration plan unlocks multi-package scope."
