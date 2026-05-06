---
description: Generate per-package documentation via the python-skeleton primitive. Read source, fill slots, run validate, render final docs.
---

# /generate-docs — per-package documentation via skeleton-fill

`/generate-docs` produces per-package documentation under `docs/<package-path>/index.md` for the project. The mechanism is the **skeleton-fill primitive**: `.devforge/lib/generate_docs_helper render-package-skeleton` writes a markdown skeleton with `[TODO]` slots, the orchestrator fills slots by reading source and invoking setters, `validate-package` checks structure and citation fidelity, and `render-package-doc` renames `.skeleton` → `.md` once validation passes. The helper owns markdown structure, section ordering, and citation format — the LLM contributes only values.

This command will replace `/onboard` once empirical iteration locks the output shape.

---

## Phase entry contract

At the start of every phase (Phase 0–5), the orchestrator MUST verify that the install root is still the current working directory. The check:

- Bash: `test -x .devforge/lib/generate_docs_helper`
- If exit 0 → cwd is the install root; proceed.
- If non-zero → cwd has shifted from the install root mid-run. ABORT with: "cwd shifted from install root; re-run /generate-docs from the directory containing .devforge/." Do NOT attempt to recover by changing cwd or by switching to absolute paths — the orchestrator's downstream Bash invocations all use bare-relative `.devforge/...` paths and recovery is fragile. A clean re-run from the right cwd is the only sanctioned path.

Why this exists: bare-relative `.devforge/...` paths assume cwd == install root. If anything between phases changes cwd (a Bash `cd` from the orchestrator, a tool that resolves paths differently, etc.), every subsequent helper call exits 127. Without this check, the failure cascades through 3-5 retries before the orchestrator diagnoses; with this check, the failure is detected within one Bash call per phase.

---

## ⚠️ ITERATION MODE — APP-WEB ONLY (TEMPORARY)

**This override is in effect until removed.** Multi-package iteration is paused; this run validates output shape on a single unit before broader rollout.

For this run, `/generate-docs` operates in single-package verification mode:

| Phase | Behavior |
|---|---|
| Phase 0 — Pre-flight | Run normally |
| Phase 1 — Discover the assigned package | **Override** — package is hardcoded to `db-cse-ui-strata/apps/app-web`. Skip the multi-package iteration loop that the full flow would run. |
| Phase 2 — Register package + extract scripts | Run normally for the single package |
| Phase 3 — Render skeleton, fill slots inline (orchestrator-direct), then iterate per-concern slot-fill inline | Run **once** for `db-cse-ui-strata/apps/app-web` only; orchestrator fills the package doc inline, then iterates per-concern slot-fill inline (sequential, orchestrator-direct) for each substantive subfolder under `src/`. The run produces 1 package doc plus N concern docs (not a single-doc output). |
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

Run the **Phase entry contract** check (see top of spec). Abort if it fails.

The hardcoded package for this iteration is `db-cse-ui-strata/apps/app-web`. Read the package manifest at `db-cse-ui-strata/apps/app-web/package.json` to confirm ecosystem signals. From the manifest, identify:

- `primary_language` — TypeScript (when `package.json` lists `typescript` in `devDependencies` or the project includes a `tsconfig.json`)
- `framework` — Vue 3 (when `package.json` lists a `vue` dependency at version `3.x`)
- `build_tool` — Vite (when `package.json` lists `vite` in `devDependencies`)

If any of those signals is absent or ambiguous from the manifest, ask the user for the value rather than guessing.

## Phase 2 — Register package + extract scripts

Run the **Phase entry contract** check (see top of spec). Abort if it fails.

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

Run the **Phase entry contract** check (see top of spec). Abort if it fails.

1. **Load the project index into working memory.** Use the Read tool to read `.devforge/index.json` once at phase start; parse the file content as JSON and hold the parsed structure in working memory for the duration of Phase 3. Subsequent steps consult this in-memory structure for per-package file listings, manifest scripts, and manifest deps instead of re-globbing the filesystem. Assumption: Phase 3 completes within a single slash-command conversation before auto-compaction triggers. If Phase 3 spans multiple turns or the session approaches context capacity, re-read `.devforge/index.json` at the start of each subsequent step.

   Then invoke `.devforge/lib/generate_docs_helper render-package-skeleton --path db-cse-ui-strata/apps/app-web` — produces `docs/db-cse-ui-strata/apps/app-web/index.md.skeleton` with `[TODO]` slots for the fields not yet set.

2. Read the resulting skeleton to confirm it was written and to see the structure of `[TODO]` slots that need filling.

3. **Read source files** under `db-cse-ui-strata/apps/app-web/src/` to identify:
   - Public exports (functions, classes, types, constants, configs, components, plugins) that cross module boundaries — every `export` statement in `src/` is a candidate. Limit to genuine public boundary surface (not private helpers).
   - External dependencies (from the package manifest's dependency list — `dependencies` in `package.json`, `[dependencies]` in `Cargo.toml`, `dependencies` under `[project]` in `pyproject.toml` (PEP 621) or `[tool.poetry.dependencies]` (Poetry), `require` in `composer.json`, etc.) and workspace-internal dependencies (`pkg-cse-*` packages — these are workspace-internal because they live in the same monorepo).
   - Hazards / mislogic observations: naming inconsistencies, performance pitfalls, type-safety gaps (e.g., `@ts-ignore`, `any` casts), v1/v2 coexistence patterns, internal duplication, cross-feature inconsistencies, complexity hotspots. Use the closed `HazardCategory` enum: `naming|performance|type-safety|duplication|inconsistency|v1-v2-coexistence|complexity`.
   - Usage example: a real consumer pattern — typically the package's main entry point or root component (e.g., `main.ts`, `App.vue`, `lib.rs`, `__main__.py`, `main.go` — depending on ecosystem) showing how the package is bootstrapped/consumed.
   - Consumer pattern: a representative downstream call site — typically a composable that uses the package's API.

4. **Fill the slots via setter invocations**. Citation discipline is mandatory — every code-snippet setter requires `--cite-file` + `--cite-start` + `--cite-end` and the snippet MUST be lifted VERBATIM from the cited source line range (whitespace-normalized comparison runs at validate-time).

   **Mechanical snippet extraction precedence.** Every invocation of a code-snippet-bearing setter — `add-package-export`, `set-package-usage-example`, `set-package-consumer-pattern` (this step), and `add-concern-export`, `add-concern-type`, `set-concern-usage-example` (the per-concern slot-fill in step 10) — MUST be preceded by a Bash invocation of `.devforge/lib/generate_docs_helper extract-snippet --file <F> --start <S> --end <E>` whose stdout is captured and passed as the `--code-snippet` argument. Pass code-snippet output via double-quoted command substitution: `--code-snippet "$(...)"`. This preserves literal `$`, backticks, and newlines in source code. Do NOT use bare `$(...)` or heredoc.

   **`extract-snippet` failure fallback.** If `extract-snippet` exits non-zero, the orchestrator regenerates the index by invoking `init-forge build-index` and retries once. A second failure aborts the current concern with a logged reason; orchestrator continues to the next concern. (At the package tier in this step, "current concern" reads as "current setter invocation" — a second failure aborts the slot-fill and surfaces the error to the user before `validate-package`.)

   Setters to invoke:

   - `set-package-overview` — 1-2 paragraph package overview (NEVER guess abbreviations; consult `README.md` at project root + at the package path for any acronym/initialism encountered before expanding it; if no authoritative definition found, use the abbreviation verbatim or mark with `[TODO: <abbreviation> — definition not found]`)
   - `set-package-tree` — ascii directory tree of `src/` (no other directories). The tree MUST include an inline `# <description>` comment after each substantive folder (folders, not files); the description is 3–7 words capturing what the folder contains and/or its architectural role. Trivial leaf folders (assets, generated output, fixtures) stay uncommented. Right-align the `#` column for readability — pad with spaces between the longest tree-glyph + folder name and the `#` marker so descriptions line up visually. Example format:

     ```
     src/
     ├── foo/          # domain entry points and routing
     ├── bar/          # shared composables and helpers
     │   └── assets/
     └── baz/          # cross-cutting type definitions
     ```
   - For each export: first `.devforge/lib/generate_docs_helper extract-snippet --file <f> --start <s> --end <e>` via Bash, then `add-package-export --name <n> --kind <k> --signature "..." --description "..." --language <l> --code-snippet "$(.devforge/lib/generate_docs_helper extract-snippet --file <f> --start <s> --end <e>)" --cite-file <f> --cite-start <s> --cite-end <e>`
   - For each dependency: `add-package-dep --name <n> --kind internal|external --version <v> --purpose "..." [--consumer-location <loc>...]`
   - For each hazard: `add-package-hazard --category <c> --description "..." [--cite-file <f> --cite-start <s> --cite-end <e>]`
   - `set-package-usage-example --language <l> --code-snippet "$(.devforge/lib/generate_docs_helper extract-snippet --file <f> --start <s> --end <e>)" --cite-file <f> --cite-start <s> --cite-end <e>`
   - `set-package-consumer-pattern --language <l> --code-snippet "$(.devforge/lib/generate_docs_helper extract-snippet --file <f> --start <s> --end <e>)" --cite-file <f> --cite-start <s> --cite-end <e>`

5. **DO NOT make direct edits to `.devforge/.generate-docs-state.json`**. The helper API is the only sanctioned mutation path. If you hit a wall (e.g., `add-package-export` rejects a duplicate name when you need to update an existing entry, or the internal-dep validator rejects a workspace-internal dep that can't resolve in single-package iteration), DO NOT bypass the helper. Surface the wall to the user with a clear error message and ABORT before `validate-package` + `render-package-doc`. The walls are signals of helper-API gaps that need fixing — bypassing them produces factual errors in the doc (this empirically happened in a prior run: 19 workspace-internal deps were misclassified as external).

6. **Source-reading discipline**: read public-API-relevant files first; only descend into implementation if a public symbol's signature is unclear. The package has ~900 source files; a thorough reading is impractical and unnecessary. Focus on boundary surface.

7. **Run `validate-package`**: `.devforge/lib/generate_docs_helper validate-package --path db-cse-ui-strata/apps/app-web`. On failure, read the structured error list (each error has `rule` / `field` / `message` / optional `diff`). Two error categories with different handling:
   - **Package-tier registration errors** (every `rule` value EXCEPT `decomposition`): fix by re-invoking the corresponding setter (re-registration overwrites for `set-*` setters; for `add-*` setters that reject duplicates, you must `reset` and re-fill OR surface the issue to the user). Cap retries at 3.
   - **Decomposition errors** (`rule: decomposition`): NOT setter-fixable. Each error names ONE substantive subfolder under `db-cse-ui-strata/apps/app-web/src/` with no registered concern. Capture this error list — it's the worklist that step 8 builds and step 10 iterates over inline.

   Proceed to step 8 ONLY when the only outstanding errors are `rule: decomposition`, OR when validate-package exits 0. If non-decomposition errors persist after 3 retries, ABORT before step 8.

8. **Build the concern worklist** from step 7's `decomposition` errors. Each entry is the triple `(package_path, concern_name, subfolder)`:
   - `package_path` is `db-cse-ui-strata/apps/app-web` (iteration-mode hardcoded)
   - `concern_name` is the substantive subfolder's basename (e.g., `components`, `composables`, `helpers`)
   - `subfolder` is the relative path under `<package_path>/` reported in the decomposition error (e.g., `src/components`)

9. **Pause for user review before per-concern slot-fill (mandatory checkpoint).** If the concern worklist from step 8 is empty (zero decomposition errors), skip this checkpoint and proceed directly to step 12. Before iterating per-concern slot-fill, summarize Phase 2 + 3-so-far outcome and ask the user to confirm. Specifically:
   - Run `.devforge/lib/generate_docs_helper status` and capture output.
   - Print a summary block to the user: package-tier counts (exports / dependencies / hazards / citations validated / scripts), the concern worklist (the N triples from step 8 — concern names + subfolder paths), and an estimate of the work ("N concerns will be slot-filled sequentially inline").
   - Then prompt via AskUserQuestion (single-line prompt: `Phase 2 complete and N concerns ready to slot-fill. Proceed?`) with options **Continue** (proceed to step 10 — sequential inline iteration), **Inspect** (read `docs/db-cse-ui-strata/apps/app-web/index.md.skeleton` and copy its contents VERBATIM into the next user-facing message as a fenced code block — do not summarize or paraphrase — then re-prompt with the same Continue/Inspect/Abort options; Inspect is non-destructive and may be invoked any number of times), **Abort** (stop the command and state to the user: "Aborted before per-concern slot-fill. State is preserved; re-run /generate-docs to resume.").

   **Why this gate exists:** empirical evidence from a `/generate-docs` run on testForge20 (2026-05-01) showed Phase 3's slot-fill loop running 50+ unattended helper invocations between user touchpoints. State-loss happened during parallel concern dispatch (the prior architecture) and was only discovered post-run. A checkpoint here lets the user verify package-tier looks correct before triggering N concern slot-fills that operate on the same state file. Per Claude Code auto-mode discipline, destructive operation classes (operations that mutate shared state extensively) need a human gate.

10. **Iterate per-concern slot-fill SEQUENTIALLY in the orchestrator's own context — one concern per loop iteration, complete its slot-fill before starting the next.** Do NOT dispatch subagents and do NOT use parallel iteration. For each `(package_path, concern_name, subfolder)` triple from the step 8 worklist, execute the per-concern slot-fill workflow inline (register concern, render concern skeleton, read source under `subfolder`, invoke concern-tier setters with `extract-snippet` precedence per step 4's directive, run `validate-concern` with capped retries, render concern doc).

    Per memory `feedback_avoid_subagents_for_sequential_identical_workflows.md`: empirical evidence (testForge20 runs, 2026-04 to 2026-05) showed transcription degradation across subagent boundaries caused citation-mismatch retries; inline iteration preserves context fidelity.

    **Why sequential, not parallel:** empirical evidence from a `/generate-docs` run on testForge20 (2026-05-01) showed parallel concern processing produced state-loss — the Phase 5 report documented 3 of 7 concerns reduced to empty shells in state despite their docs being rendered to disk earlier in the run (when slot data WAS populated). Either the helper's `_state_transaction()` lock failed under high concurrency or empty values were written via setters. Until `tests/lib/test_state_concurrency_stress.py` empirically verifies parallel safety, sequential is mandatory. Trade-off: sequential iteration costs more wall-clock for the iteration-mode single-package run; this is acceptable given the iteration's scope (1 package × ~7 concerns).

    **Resume-mode propagation is mandatory, not a hint.** If Phase 0 routed via Resume, every per-concern iteration MUST honor the slot-skip contract: before each setter, check current state via `.devforge/lib/generate_docs_helper status` and skip the setter if its corresponding field is already populated. For `add-*` setters that reject duplicates, re-running in resume mode is safe but redundant. Mixing modes across concerns in one run is forbidden — all-fresh or all-resume per run.

    **Concern-tier setter-specific instructions:**

    - `set-concern-tree` — ASCII tree of `<subfolder>/` rooted at the subfolder (NOT at the package's `src/`). The tree MUST include EVERY entry at EVERY depth under the subfolder — folders AND files, recursively to leaf files. There is NO depth limit. A folder shown without its file children is INCOMPLETE; recurse until the tree's leaves are individual files (or genuinely-trivial leaf folders per the trivial-leaves rule below). Trivial leaf folders (build/cache/vendor folders that mechanically contain only generated, cached, or vendored content — e.g., `assets`, `dist`, `target`, `bin`, `obj`, `node_modules`, `__pycache__`, `.venv`, `vendor`, generated output, fixtures, locales) stay uncommented **and are exempt from file-child expansion** — the full-recursion mandate does not apply to them. Right-align the `#` column for readability — pad with spaces between the longest tree-glyph + entry-name and the `#` marker so descriptions line up visually.

      **Description-rule (default = describe every entry).** Every entry — folder or file — gets a 3–7 word inline `# <description>` comment by default. The description is inferred from the filename + the entry's location in the tree + surrounding naming patterns. Filename inference is the EXPECTED source of tree descriptions; reading the file's source is reserved for the public-API surface (the `add-concern-export` setter), NOT for tree descriptions. A suggestively-named file like `OrderHeader.vue`, `formatters.ts`, `parser.rs`, or `validators.go` gets a filename-inferred description (e.g., `OrderHeader.vue` → `# table header for order summary view`).

      **Skip-rule (narrow — canonical aggregators only).** Skip the description ONLY for canonical aggregator files whose names are purely structural and convey nothing semantic about content: `mod.rs`, `lib.rs`, `__init__.py`, `index.ts`, `index.js`, `doc.go`, and direct ecosystem equivalents. All other entries — including loosely "self-evident" filenames — get a description.

      **Tree descriptions are free-text, NOT subject to the verbatim-citation discipline.** The verbatim-citation rule governs `--code-snippet` arguments (e.g., `add-concern-export`, `add-concern-type`, `set-concern-usage-example`), where the helper mechanically validates whitespace-normalized snippet equality against the cited `--cite-file` `--cite-start` `--cite-end` range. That validator does NOT run on tree text — `set-concern-tree --text` is character-class validated only, with no citation comparison. Filename-inferred descriptions are the design intent for tree prose, not hallucination; hallucination applies to the verbatim-citation surface, where the helper catches it mechanically.

      **Source-enumeration scope.** Read the subfolder's entries from the in-memory `.devforge/index.json` loaded at Phase 3 step 1 — this is mechanical, not source-reading. Source-reading remains scoped per the "Limit source-reading to public-API-relevant files first" discipline rule below: spot-read a file only when its filename is ambiguous about what it does. The tree fills naming-inferred descriptions for the bulk; source-reading is reserved for the public-API surface (the `add-concern-export` setter), not for tree descriptions.

      **Why file-level.** The concern doc's tree is the file-level index for /research retrieval. A future query "where is `<filename>`?" or "what's in `<subfolder>/<file>`?" must resolve via this tree. Folder-only granularity loses that recall. Source-reading cost is bounded because the tree's per-file descriptions are filename-inferred or skipped, not source-derived.

      Example format (ecosystem-agnostic):

      ```
      <subfolder>/
      ├── core/                            # core domain logic
      │   ├── mod.rs
      │   ├── parser.rs                    # input parsing
      │   └── errors.rs                    # domain error types
      ├── feature/                         # example feature folder
      │   ├── components/                  # feature ui components
      │   │   ├── FeatureView.tsx          # feature root component
      │   │   └── FeatureItem.tsx          # single feature row
      │   ├── handlers/                    # feature event handlers
      │   │   └── feature_handler.py       # request handler entry
      │   └── helpers/                     # feature-local utilities
      │       └── feature_utils.go         # feature helper functions
      └── shared/                          # cross-feature shared code
          ├── BulletList.tsx               # generic bullet-list component
          └── helpers/                     # shared utility helpers
              └── formatters.ts            # date / currency formatters
      ```

      Note in the example: depth-3 recursion under `feature/` (folder → components/handlers/helpers → individual `.tsx` / `.py` / `.go` leaves) is fully expanded; every entry has a 3–7 word filename-inferred description except `mod.rs`, which is a canonical aggregator and qualifies for the narrow skip-rule. Folder-level `# <description>` follows the same filename-inference rule. A `locales/` folder at this level would stay uncommented and unexpanded — the full-recursion mandate exempts trivial leaves. The mix of `.rs`, `.tsx`, `.py`, `.go`, and `.ts` file extensions is illustrative — the same rules apply regardless of source-language ecosystem.

    **Per-tree-entry annotation validator loop (runs after `set-concern-tree`, before `validate-concern`).** For each non-trivial tree entry (folder OR file) listed in the concern's tree text — except canonical aggregators (`mod.rs`, `lib.rs`, `__init__.py`, `index.ts`, `index.js`, `doc.go`, per the `set-concern-tree` skip-rule above) and trivial-leaf folders (`assets`, `dist`, `target`, `bin`, `obj`, `node_modules`, `__pycache__`, `.venv`, `vendor`, generated output, fixtures, locales, per the `set-concern-tree` trivial-leaves rule above) — run the annotation loop:

        1. **Build the entry list** from the in-memory `.devforge/index.json` (loaded at Phase 3 step 1) filtered to the subfolder. Apply the canonical-aggregator and trivial-leaf exclusions inline; the resulting list is the per-entry worklist for this loop.
        2. **Build sibling context** for each entry: enumerate the OTHER entries under the same immediate parent path, paired with their already-recorded annotation values when an annotation has been added in this loop's prior iterations, or with the LLM-composed tree description from `set-concern-tree`'s `--text` when no annotation exists yet.
        3. **Dispatch the `tree-annotator` Task subagent** with the input context `(target_path, concern, subfolder, siblings, previous_attempt_feedback)`. On the first attempt for an entry, `previous_attempt_feedback` is absent. The subagent returns a JSON block with fields `label`, `confidence`, `evidence_file`, `evidence_start`, `evidence_end`. The `confidence` value is one of `extracted | inferred` (the third enum value `ambiguous` is locked per `generate_docs_schema.py:ANNOTATION_CONFIDENCE_VALUES` but is reserved for the orchestrator's escalation tag in step 8 — annotator never returns it).
        4. **Invoke `add-annotation`**: `.devforge/lib/generate_docs_helper add-annotation --package <package_path> --concern <concern_name> --target-path <entry> --label "<label>" --confidence <confidence> --cite-file <evidence_file> --cite-start <evidence_start> --cite-end <evidence_end> --model-version <model_version>`. The helper computes `content_hash` from the cite-file slice; the orchestrator does not pass it. `<model_version>` is the literal Task-tool `model` override used for the dispatch — `haiku` on the default attempts (the agent's `model_tier: scan` resolves to Haiku per `install_defaults.py`), `sonnet` on the step 7 escalation. The validator stores the string verbatim; no format constraint beyond non-empty single-line.
        5. **Invoke `validate-annotation`**: `.devforge/lib/generate_docs_helper validate-annotation --package <package_path> --concern <concern_name> --target-path <entry>`. Exit 0 → annotation accepted; move to the next entry. Exit 2 / 3 / 4 / 5 / 6 → capture stderr and proceed to step 6.
        6. **On non-zero exit, retry with feedback.** Copy the captured stderr VERBATIM into your next `tree-annotator` dispatch's `previous_attempt_feedback` field as a fenced code block — do not summarize or paraphrase. The validator's exit message names the exact rejection reason (which banned phrase from `src/devforge/lib/_banned_phrases.py`, which cite mismatch or binary-file reject, which sibling collision, or which schema field is invalid); paraphrasing loses the load-bearing detail the annotator needs to refine. Re-invoke `add-annotation` (overwrites the prior attempt for the same `target-path`) and re-invoke `validate-annotation`. Cap at 3 attempts total per entry (initial dispatch + 2 retries).
        7. **After 3 failed attempts, escalate to Sonnet.** Dispatch `tree-annotator` ONE final time using the Task tool's `model: "sonnet"` override, passing the most recent stderr as `previous_attempt_feedback`. Re-run `add-annotation` and `validate-annotation`. Single attempt only — no further retries at the Sonnet tier.
        8. **If escalation also fails, fall back to `ambiguous`.** Re-invoke `add-annotation` with the LAST proposed `label` / `cite-file` / `cite-start` / `cite-end` values BUT `--confidence ambiguous`. Then invoke `validate-annotation` once more. If the validator still fails (e.g., the rejection reason is a banned phrase in the label rather than confidence), record the entry in the concern's outcome `errors` array as `{"target_path": "<entry>", "reason": "<final stderr>"}` and proceed to the next entry. Do NOT block the whole concern on a single entry's annotation failure.

        **Verbatim stderr discipline (mandatory).** Step 6 says "copy VERBATIM... do not summarize or paraphrase" because the validator's stderr is the only signal the annotator has about why its prior attempt was rejected. Pass the captured stderr to the next dispatch as a fenced code block: `previous_attempt_feedback:` followed by a triple-backtick fence containing the literal stderr text. Paraphrased feedback loses the exact banned-phrase token, the exact cite-line numbers, or the exact sibling label that collided — all of which are load-bearing for the annotator's next attempt.

        **Why this loop is additive, not replacement.** `set-concern-tree` continues to set the tree text in one invocation as today; the annotations recorded by this loop are an additive per-entry record stored separately in state. Step A.5 of `VALIDATOR-LOOP-PLAN.md` (the empirical comparison phase) will determine whether validated annotations should derive the tree text in a future spec revision; for now, both coexist. See `VALIDATOR-LOOP-PLAN.md` for the loop's empirical motivation (per-node dispatch + mechanical validation eliminates batch-induced generalization causes that produced filename-echo on a descriptively-named codebase in a prior run).

        **Post-batch quality gate.** After the per-entry loop completes for the concern, invoke `.devforge/lib/generate_docs_helper verify-annotations --package <package_path> --concern <concern_name>`. Three exit codes:
        - Exit 0 — all gates pass (banned-phrase = 0, ambiguous rate ≤ 10%, cross-concern duplicate rate ≤ 5%). Proceed to `validate-concern`.
        - Exit 2 — at least one gate failed. Capture the JSON report from stdout and the failing-gate lines from stderr; copy both VERBATIM into the user-facing message as a fenced code block (do not summarize or paraphrase). Halt the concern with the report shown; the user decides whether to re-run the per-entry loop, edit thresholds, or accept the failure. Do NOT silently skip.
        - Exit 5 — state error (concern not registered, schema-corrupt confidence). Capture stderr verbatim, record `{"reason": "<stderr>"}` in the concern's outcome `errors` array, and abort the concern. Per the per-concern abort discipline, proceed to the next concern.

    **Per-concern discipline (inline safeguards):**

    - **Never guess abbreviations or acronyms.** When you encounter an abbreviation or initialism in source identifiers, file names, or existing prose, verify its expansion against authoritative project sources BEFORE using or expanding it in any setter value. Search order, stopping at the first hit: (1) `README.md` at project root and at `<package_path>`, (2) the package manifest `description` field (`package.json`, `Cargo.toml`, `pyproject.toml`, `composer.json`, `*.csproj`, etc.), (3) top-level `docs/` content, (4) `.devforge/project-config.json` `PROJECT_DESCRIPTION` field if present, (5) JSDoc / docstrings near the first definition. If no authoritative definition is found, use the abbreviation verbatim without expansion or mark with `[TODO: <abbreviation> — definition not found in README, manifest, or top-level docs; human to define]`. Inventing an expansion is hallucination — same principle as the verbatim citation rule.
    - **Reinforces step 5 at the concern tier — never make direct edits to `.devforge/.generate-docs-state.json`.** If you hit a wall (e.g., `add-concern-export` rejects a duplicate name, the cite range cannot resolve against the source file, or a citation fails whitespace-normalized comparison after re-extraction), abort the current concern with the wall captured in its outcome record's `errors` array and proceed to the next concern. Do NOT bypass.
    - **Cite verbatim from source via `extract-snippet`.** Every `--code-snippet` value must come from the `extract-snippet` helper's stdout for the cited `--cite-file` `--cite-start` `--cite-end` range. The helper validates this mechanically; failures surface as validation errors rather than silently shipping bad citations.
    - **Limit source-reading to public-API-relevant files first.** The package may have hundreds of source files; thorough reading is impractical and unnecessary. Read the subfolder's module-entry file(s) and any file that defines a public symbol crossing the boundary. Descend into deeper implementation only when a signature or behavior is unclear from the entry-level read.
    - **Never invoke `set-concern-overview`, `set-concern-tree`, or `set-concern-usage-example` with empty or whitespace-only values.** `--text` (overview, tree) and `--code-snippet` (usage-example) MUST contain real content. The helper accepts empty strings legally with last-writer-wins semantics, so an empty-value setter silently wipes a populated slot. If you cannot find content to fill the slot (no readable source, no representative call site, etc.), abort the current concern with the wall captured in its outcome record — never blank the slot to "retry" or "clear" it.
    - **On `add-concern` rejection in `fresh` mode, abort the current concern.** If `add-concern` returns exit 2 with `concern already registered` and the iteration is in `fresh` mode (where the resume-mode `status` check above skips the call only in `resume` mode), the worklist or mode propagation is inconsistent; capture `errors: ["concern already registered; mode mismatch with run-level mode"]` in the outcome record and proceed to the next concern. Do NOT invoke `reset`, `add-package`, or any other setter to "clear and retry" — `reset` wipes state for ALL packages and concerns, destroying every other concern's work in the same run.
    - **On any wall, abort the current concern and proceed to the next — never improvise destructive recovery.** When this per-concern iteration reaches a state it does not know how to handle (helper API rejection, `validate-concern` failing 3 retries, citation that cannot be lifted verbatim from the cited range, missing source file, ambiguous concern boundary), the only legitimate action is to capture the wall in the outcome record's `errors` array and proceed to the next concern. Improvised recovery — invoking `reset`, `add-package`, package-tier setters, or any operation outside this iteration's concern-tier allowlist — is forbidden.

    **This per-concern iteration does NOT:**

    - **Modify source files.** Read-only access to source. All file writes happen through the helper into `docs/`.
    - **Invoke `.devforge/lib/generate_docs_helper reset`.** `reset` is a global destructive operation that wipes the state file for all packages and all concerns; it is reserved for Phase 0's routing decision (Reset / Resume / Abort prompt to the user). The per-concern iteration's scope is one concern and it has no authority to reset state — invoking `reset` destroys every other concern's work in the same run.
    - **Invoke package-tier or architecture-tier setters.** Per-concern scope is concern-tier only: `add-concern`, `render-concern-skeleton`, `set-concern-overview`, `set-concern-tree`, `add-concern-export`, `add-concern-type`, `add-concern-dep`, `add-concern-hazard`, `set-concern-usage-example`, `validate-concern`, `render-concern-doc`, plus the read-only `status` subcommand (used in resume mode to inspect current concern state before each conditional setter) and `extract-snippet` (used for verbatim snippet extraction). Package-tier setters are out of scope and MUST NEVER be invoked from per-concern iteration: `add-package`, `set-package-overview`, `set-package-tree`, `set-package-language`, `set-package-framework`, `set-package-build-tool`, `add-package-script`, `add-package-export`, `add-package-dep`, `add-package-hazard`, `set-package-usage-example`, `set-package-consumer-pattern`. Architecture-tier setters are likewise out of scope.

11. **Collect the per-concern outcome.** For each concern processed in step 10, capture an outcome record `{"concern": "<name>", "status": "ok|failed", "exports": <n>, "deps": <n>, "hazards": <n>, "errors": [...]}` based on whether `validate-concern` exited 0 (status `ok`) or failed after capped retries (status `failed` with the structured error list). Aggregate the records into a per-concern table for the Phase 5 report. If any concern is `failed`, surface the error list to the user before proceeding to step 12 — do NOT silently ignore concern failures.

12. **Re-run `validate-package`**: `.devforge/lib/generate_docs_helper validate-package --path db-cse-ui-strata/apps/app-web`. With every substantive subfolder now registered as a concern, the decomposition gate should emit zero errors and validate-package should exit 0. If decomposition errors remain, step 10's iteration missed entries (a per-concern iteration failed and produced no concern state, or the step 8 worklist was incomplete) — surface to the user and ABORT before step 13.

13. **Invoke `render-package-doc`**: `.devforge/lib/generate_docs_helper render-package-doc --path db-cse-ui-strata/apps/app-web` (renames `.skeleton` → `.md`). The helper internally re-runs validation; with step 12's clean exit, this succeeds and writes `docs/db-cse-ui-strata/apps/app-web/index.md`. Each concern's doc was already rendered inline by step 10's per-concern slot-fill iteration (the workflow's final step renders the concern doc). The package doc is the LAST thing rendered, after all concerns are in place — this ordering is required because `render-package-doc` rejects any outstanding decomposition errors.

14. **Out of scope** (do NOT invoke):
   - Architecture-tier subcommands (reserved for future phases of /generate-docs)
   - Memory archaeology subcommands (reserved for future phases of /generate-docs)
   - Multi-package iteration (the package loop is paused under the `## ⚠️ ITERATION MODE` section)
   - Modifying source files (read-only access to source)
   - Re-running `validate-package` between steps 7 and 12 (step 7 captures the worklist; step 12 confirms decomposition is clean — intermediate validates produce noise without progressing the flow)

## Phase 4 — Verify the produced doc

Run the **Phase entry contract** check (see top of spec). Abort if it fails.

After Phase 3 completes:

1. Confirm `docs/db-cse-ui-strata/apps/app-web/index.md` exists (no `.skeleton` suffix). If it doesn't exist, validation must have failed during slot-fill — ask the user how to proceed (retry slot-fill, or abort).
2. Run `.devforge/lib/generate_docs_helper status` — exit 0, output should show one package registered with overview / tree / exports / deps populated.
3. Read `docs/db-cse-ui-strata/apps/app-web/index.md`. Copy its contents VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase).
4. Ask the user to evaluate the produced doc against the iteration plan's empirical baseline targets.

## Phase 5 — Report

Run the **Phase entry contract** check (see top of spec). Abort if it fails.

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
  | Phase 3 — Slot-fill + per-concern iteration | <Δ to phase 4 entry> |
  | Phase 4 — Verify the produced doc | <Δ to phase 5 entry> |
  | **Total wall-clock** | <total> |

  This phase-timing table makes per-phase cost visible to the user post-run, addressing the "no per-step cost telemetry" gap surfaced by the audit. Helper-side per-invocation tracing lives separately in `.devforge/.generate-docs-trace.log`; not required for this phase-timing table — the orchestrator's wall-clock summary is sufficient on its own.

Tell the user: "This is single-package iteration; multi-package flow is paused under the `## ⚠️ ITERATION MODE` section of `/generate-docs`. Re-run after the iteration plan unlocks multi-package scope."
