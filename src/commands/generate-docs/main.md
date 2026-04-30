---
description: Generate per-package documentation via the python-skeleton primitive. Read source, fill slots, run validate, render final docs.
---

# /generate-docs — per-package documentation via skeleton-fill

`/generate-docs` produces per-package documentation under `docs/<package-path>/index.md` for the project. The mechanism is the **skeleton-fill primitive**: `.devforge/lib/generate_docs_helper render-package-skeleton` writes a markdown skeleton with `[TODO]` slots, the `tech-writer` subagent fills slots by reading source and invoking setters, `validate-package` checks structure and citation fidelity, and `render-package-doc` renames `.skeleton` → `.md` once validation passes. The helper owns markdown structure, section ordering, and citation format — the LLM contributes only values.

This command will replace `/onboard` once empirical iteration locks the output shape.

---

## ⚠️ ITERATION MODE — APP-WEB ONLY (TEMPORARY)

**This override is in effect until removed.** Multi-package iteration is paused; this run validates output shape on a single unit before broader rollout.

For this run, `/generate-docs` operates in single-package verification mode:

| Phase | Behavior |
|---|---|
| Phase 0 — Pre-flight | Run normally |
| Phase 1 — Discover the assigned package | **Override** — package is hardcoded to `db-cse-ui-strata/apps/app-web`. Skip the multi-package iteration loop that the full flow would run. |
| Phase 2 — Register package + extract scripts | Run normally for the single package |
| Phase 3 — Render skeleton, dispatch tech-writer to fill | Run **once** for `db-cse-ui-strata/apps/app-web` only |
| Phase 4 — Verify the produced doc | Run normally |
| Phase 5 — Report | Run normally; explicitly note iteration scope |

Pre-existing `docs/` content under any path other than `docs/db-cse-ui-strata/apps/app-web/` is left untouched in this mode.

**Removing this override:** when the output shape is locked (per the iteration plan that drives this command), delete this entire `## ⚠️ ITERATION MODE` section. The full multi-package flow resumes via the corresponding spec edit that lifts iteration scope at that time.

---

## Phase 0 — Pre-flight

Verify, in order:

1. `.devforge/init.yaml` exists. If absent, tell the user to run `/init-forge` first and stop.
2. `.devforge/lib/generate_docs_helper` exists and is executable. If missing, the install is incomplete — tell the user to re-run `install.sh` and stop.
3. The target package path `db-cse-ui-strata/apps/app-web/` exists relative to the install root. If absent, tell the user the path is missing and ask whether they want to abort or supply a different path; do not proceed silently.
4. Inspect `.devforge/.generate-docs-state.json`. If absent, proceed (clean run). If present, run `.devforge/lib/generate_docs_helper status` to see which packages are registered, then branch:
   - **Target package already registered** (`db-cse-ui-strata/apps/app-web` appears in status output): the prior run's state will block `add-package` re-registration in Phase 2 (the helper rejects duplicate `add-package` by design — see `_setters.py` `cmd_add_package`). Ask the user via AskUserQuestion (single-line prompt: `Prior run state for app-web exists. Reset and start fresh, resume by filling missing slots only, or abort?`) with options **Reset** (default — invoke `.devforge/lib/generate_docs_helper reset`, then proceed to Phase 1 normally), **Resume** (skip Phase 2's `add-package` and any scalar `set-*` already populated; dispatch tech-writer in Phase 3 with a brief noting the package is registered and only `[TODO]` slots remain), **Abort** (stop and let the user reconcile manually). Default to **Reset** because iteration mode treats each run as a fresh attempt unless the user opts to resume.
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

## Phase 3 — Render skeleton, dispatch tech-writer to fill

1. `.devforge/lib/generate_docs_helper render-package-skeleton --path db-cse-ui-strata/apps/app-web` — writes `docs/db-cse-ui-strata/apps/app-web/index.md.skeleton` with `[TODO]` slot markers.
2. Read the resulting `docs/db-cse-ui-strata/apps/app-web/index.md.skeleton` to confirm it was written.
3. Dispatch the `tech-writer` subagent via the Task tool with `subagent_type=tech-writer`. The brief delivers the parameters the agent needs; the SKELETON-FILL MODE contract lives in `src/agents/tech-writer.md` and is part of the agent's system prompt — do not duplicate it in the brief. The brief includes:

   - **Mode**: SKELETON-FILL
   - **Package path**: `db-cse-ui-strata/apps/app-web`
   - **Package name**: `app-web`
   - **Skeleton path**: `docs/db-cse-ui-strata/apps/app-web/index.md.skeleton`
   - **Helper path**: `.devforge/lib/generate_docs_helper`
   - **Source root**: `db-cse-ui-strata/apps/app-web/src/` (Vue/TS convention)
   - **Iteration scope reminder**: only this one package; do NOT touch sibling packages

4. Wait for the `tech-writer` subagent to return. The subagent reads source, invokes setters (`set-package-overview`, `set-package-tree`, `add-package-export`, `add-package-dep`, `add-package-hazard`, `set-package-usage-example`, `set-package-consumer-pattern`), runs `validate-package`, and on validation pass runs `render-package-doc`. The agent's return value is a structured report (see Phase 5 fields below).

## Phase 4 — Verify the produced doc

After `tech-writer` returns:

1. Confirm `docs/db-cse-ui-strata/apps/app-web/index.md` exists (no `.skeleton` suffix). If it doesn't exist, validation must have failed inside the subagent — ask the user how to proceed (re-dispatch with stricter brief, or abort).
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

Tell the user: "This is single-package iteration; multi-package flow is paused under the `## ⚠️ ITERATION MODE` section of `/generate-docs`. Re-run after the iteration plan unlocks multi-package scope."
