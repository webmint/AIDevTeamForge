# Architecture Pivot — 4-command sequence

**Status**: Step 1 complete. Step 2 next. Branch `develop-2.0-init` at commit `bd544ff`.

User-approved pivot from current `/setup-wizard` + `/onboard` + `/constitute` trio to a four-command sequence: `/init-forge` → `/generate-docs` → `/configure` → `/constitute`. Detection moves from Phase 1 light-scan (in current setup-wizard) to onboard's deep scan (renamed `/generate-docs`).

## Step 1 outcomes (2026-04-30 session)

**Three commits on `develop-2.0-init`:**

- `a55d923` — Original `/init` spec + purpose-built `init_helper.py` (5-field scoped helper, NOT a reuse of `detect_report`) + 81 tests
- `052cf2a` — Renamed `/init` → `/init-forge` to avoid collision with Claude Code's built-in `/init` skill (which generates CLAUDE.md). Project-level command would shadow built-in but creates UX confusion
- `bd544ff` — Added `summary` subcommand to `init_helper` + Step 5 in spec (verbatim-echo report); dropped `model: sonnet` override; removed `/setup-wizard` from emitter `_PROMOTED` (no longer ships into target projects). Tests: 336/336 passing

**Departures from original Step 1 plan:**

- **Single-file spec, no `references/`** — original plan said `src/commands/init-forge/main.md` + `references/*.md`; ~110 lines fits comfortably in main.md
- **Purpose-built `init_helper`, not `detect_report` reuse** — `detect_report` has 30+ fields' worth of setters scoped to setup-wizard; `init_helper` exposes exactly the 8 subcommands `/init-forge` needs (reset, set-workspace-mode, set-project-root, set-project-state, set-default-branch, add-package, find-nested-git, summary). `detect_report.py` is now docstring-marked deprecated (see top of file) but still ships during transition
- **Yaml file is `.devforge/init.yaml`, NOT `detection_report.yaml`** — narrower contract; 5 fields only. Co-exists with legacy `detection_report.yaml` during transition
- **No approval gate after Step 4** — 5 deterministic fields don't warrant friction; user verifies via Step 5's verbatim summary instead
- **install.sh chain NOT extended** — only the final-message string updated (`Next — run /init-forge`). Full chain rewrite stays in Step 6
- **`/setup-wizard` partially decommissioned** — emitter no longer ships `setup-wizard.md` into target projects (Step 7 partial); source `src/commands/setup-wizard/` + helpers `wizard_render.py`, `detect_report.py` retained for reference

**Verified end-to-end against testForge20:**

- `/init-forge` populates `.devforge/init.yaml` with all 5 fields:
  - `workspace_mode: wrapper`, `project_root: db-cse-ui-strata`, `project_state: brownfield`, `default_branch: dev`
  - `packages_detected: 26 records` — exact match to `find -name package.json` count
- `init_helper summary` renders the report with manifest-column alignment

**Open follow-ups (not blocking Step 2):**

- testForge20 has stale `setup-wizard.md` from prior install (manual `rm` cleanup)
- `update.sh` has 3 user-facing warnings referencing `/setup-wizard` (lines 168, 355, 377) — point at a command no longer shipped; cleanup belongs to Step 4 or later
- `install.sh` line 5 header comment still references `/setup-wizard` (philosophy doc, not behavioral); cleanup with Step 6 chain rewrite

## Context for next session

### Why pivot

Current `/setup-wizard` mashes three architecturally-distinct jobs: framework bootstrap, light-scan detection, user-question + template substitution. The light-scan detection has a structural flaw — 5-file grep cap per library category — that's unfixable by patching. On a 27-package monorepo (testForge20), the grep misses library usage 27/5 = 5.4× more than it sees, producing non-deterministic results: `purify-ts` detected on one run, `N/A` on another. We patched detect.md §4.4 to manifest-dep-sufficient (better recall) but architecture and error_handling_pattern fields remain sampling-fragile.

Onboard already does a deep scan that produces 97 per-package docs for testForge20. Its depth captures what Phase 1 misses. Pivot moves detection there.

### Empirical validation (2026-04-30)

A fresh session populated `.devforge/detection_report.yaml` for testForge20's `db-cse-ui-strata` project using **only onboard's docs** (`/Users/mykolakudlyk/Projects/doosan/cse-strata-ws-forge/docs/db-cse-ui-strata/`), with hard constraint of no source-code reads.

**Result: 18 of 22 fields populated with doc-cited evidence, 0 source-code cheats, 3 caveat-fields, 1 honest null.**

Onboard's depth wins decisively on:
- `error_handling_pattern`: `Either monad` (correct) vs Phase 1's `try/catch` (wrong, due to 5-file grep on apps/ only)
- `architecture_shape`: `clean-feature-modular-monorepo` (correct enum match) vs Phase 1's `feature-modular-monorepo` (missed Clean dimension)
- `error_handling_library`: deterministic `purify-ts` vs Phase 1's coin-flip
- `state_management`: same value (Pinia) but with richer evidence (BLoC pattern documented)

Three caveats that need addressing:
1. Per-package script commands (`build_commands`, `type_check_commands`, `lint_commands`) — onboard docs don't echo `package.json scripts` block; fresh session used ecosystem defaults
2. `runtime_url_value` — onboard doesn't document config files; framework-default got `http://localhost:5173` when actual is `https://okta.local.dev.dice-tools.com:8080` per `vite.config.ts`
3. `validation_library` — set to null; would surface in deeper component docs not sampled

### Test data references

- testForge20 (target): `/Users/mykolakudlyk/Projects/testForge20/`
- Onboard output (source-of-truth docs): `/Users/mykolakudlyk/Projects/doosan/cse-strata-ws-forge/docs/db-cse-ui-strata/`
- Current detection_report.yaml (Phase 1 output for comparison): `/Users/mykolakudlyk/Projects/testForge20/.devforge/detection_report.yaml`

### Current branch state

- Branch: `develop-2.0-init` (renamed from `develop-2.0-setup-wizard` mid-session)
- Q1–Q10 of questions.md written under OLD architecture (single `/setup-wizard` flow) — still in `src/commands/setup-wizard/references/questions.md`; transfers to `/configure` in Step 4
- Helpers shipped to target:
  - `init_helper` (8 subcommands; `/init-forge`'s persistence layer; tests in `tests/lib/test_init_helper.py`)
  - `detect_report` (deprecated; legacy `/setup-wizard` Phase 1 helper; kept until Step 7)
  - `wizard_render` (legacy `/setup-wizard` Phase 3 helper; kept until Step 4)
  - `onboard_helper` (stub; gets buildout in Step 2)
- Last work commit: `bd544ff` (Step 1 final)
- Test count: 336 passing

The Q1–Q10 question logic transfers to `/configure` mostly unchanged. Phase 1's structural steps (workspace_mode, project_root, default_branch, project_state, packages_detected) now live in `/init-forge` (Step 1 done). Phase 1's library/architecture/error-handling/runtime-url detection (§4.4–§4.6 of legacy detect.md) is replaced by docs-driven detection in `/configure`.

## The 4-command sequence

### `/init-forge` — minimal structural bootstrap ✓ DONE (Step 1)

Captures 5 fields. Bash-style fast. LLM only orchestrates.

- `workspace_mode` (user choice via AskUserQuestion: standalone vs wrapper)
- `project_root` (user choice in wrapper mode; `.` in standalone)
- `default_branch` (git query)
- `project_state` (filesystem check: empty vs brownfield)
- `packages_detected` (manifest path + filename walk; no content reads)

Side effect: install.sh copies framework files (`.devforge/`, `.claude/`, CLAUDE.md template, agent templates with `{{...}}` placeholders intact). `/init-forge` itself does NOT install — install.sh runs first, then user invokes `/init-forge` in Claude Code.

**Implemented as** (Step 1 ship state):
- `src/commands/init-forge/main.md` — single-file spec (no references/), 5 numbered steps + Preflight + Render Summary
- `src/devforge/lib/init_helper.py` + launcher + 92 tests in `tests/lib/test_init_helper.py`
- Yaml output: `.devforge/init.yaml`
- Emitter (`scripts/emitters/claude.py`) ships `init-forge.md` into `<target>/.claude/commands/`

### `/generate-docs` — deep codebase scan

Renames current `/onboard`. Same logic. Reads everything; no sampling caps. Produces `docs/<package>/...`.

**Extension during pivot**: per-package doc template gains a "Scripts" subsection capturing `package.json scripts` block verbatim. Closes one of the three caveats.

**Open decision**: should `/generate-docs` also document config files (`vite.config.ts`, `next.config.js`, `webpack.config.js`, etc.) so `/configure` can extract `runtime_url_value` from doc evidence? Alternative: `/configure` reads config files directly as a small focused step. Decide during step 2 (see Work Order below).

Implemented as: rename `src/commands/onboard/` → `src/commands/generate-docs/`. Update doc template in `main.md`. Extend `onboard_helper.py` if Scripts capture needs helper support.

### `/configure` — consume docs, populate config, ask user

Replaces current `/setup-wizard`'s Phase 2 + Phase 3 work. **Uses bulk-confirmation shortcut** instead of 12+ sequential AskUserQuestion calls — see "Bulk-confirmation shortcut" section below.

Phases:
1. Read `docs/` directory exhaustively (all per-package docs, not just top-tier — closes the validation_library gap)
2. Populate `.devforge/detection_report.yaml` via `detect_report` setters using doc evidence
3. (Possibly) read config files directly for `runtime_url_value` if not in docs — decision pending
4. Render bulk-confirmation prompt covering ~15 detection-derived fields (project_name, project_type, project_description, primary_language, architecture, frameworks, library categories, runtime URL, etc.). User replies `'yes'` to confirm all OR lists overrides line-by-line (e.g., `'architecture: hexagonal'`)
5. Sequential prompts for 4 user-only fields (workflow_enforcement, ai_attribution, agent_tiers, ac_verification_mode)
6. Substitute templates with final values into CLAUDE.md and agent files (replaces `{{LANGUAGE}}`, `{{FRAMEWORK}}`, `{{ARCHITECTURE}}`, etc.)

Implemented as: `src/commands/configure/main.md` + `src/commands/configure/references/*.md`. Reuses `detect_report` setters for yaml writes and `wizard_render` setters for project-config.json writes.

#### Bulk-confirmation shortcut

For all fields where /generate-docs's deep scan provides a value (or the LLM can derive one via ecosystem knowledge applied to docs), present them all in one review prompt instead of asking confirm/override per field.

Detection-derived fields (in bulk):
- Project: name, type, description, primary_language
- Architecture: workspace_mode, project_root, architecture_shape
- Stack: frameworks per package, auth_layer, state_management, styling, routing, validation_library, error_handling_library, error_handling_pattern, runtime_url

User-only fields (sequential, after bulk confirmation):
- workflow_enforcement (Strict/Moderate/Light — pure preference)
- ai_attribution (Yes/No — pure preference)
- agent_tiers (Think/Do/Verify model picks — pure preference)
- ac_verification_mode (code-only/tests/runtime-assisted/off — pure preference)

Bulk prompt format:

```
Here's what /generate-docs found:

Project:
- name: <value>
- type: <value>
- description: <value>
- primary_language: <value>

Architecture:
- workspace_mode: <value>
- project_root: <value>
- architecture: <value>

Stack:
- frameworks: <per-package summary>
- auth_layer: <value>
- state_management: <value>
- ... (all other detection-derived fields)

Reply 'yes' to confirm all, or list overrides one per line (e.g., 'architecture: hexagonal').
```

User reply parsing:
- `"yes"` (case-insensitive, exact) → all values confirmed; apply via setters
- Otherwise → parse line-by-line for `<field>: <value>`; apply only those fields via setters; remaining fields confirmed as-is

This reduces Q1-Q12's 12+ sequential AskUserQuestion calls to 1 bulk prompt + 4 user-only prompts. ~5-10K token savings per run plus better UX (user reviews all detection at once, like a code review).

### `/constitute` — unchanged

Synthesizes constitution.md from populated config + docs. No changes from current spec.

## Work order

Each step listed with verify criteria.

### Step 2: Schema-anchor `/generate-docs` outputs

Approved 2026-04-30: `/generate-docs` becomes schema-anchored. `onboard_helper.py` owns markdown structure; LLM provides values via setters (extends the helper-owns-shape pattern from `detect_report` + `wizard_render` to the doc-generation tier). Closes the previously-scoped "Scripts subsection" gap as a side-effect.

**Three schemas to implement:**

- `ProjectIndexDoc` (Tier 1, `docs/<project>/index.md`) — name + workspace_mode + path + overview + directory_tree + main_exports + cross_package_deps_summary
- `ArchitectureDoc` (Tier 1, `docs/<project>/architecture.md`) — architecture_shape + patterns + layers + cross_package_dep_graph + key_decisions
- `PackageDoc` (Tier 2/3, per-package + feature docs) — name + path + overview + primary_language + framework + build_tool + **scripts dict (closes pivot's Scripts gap)** + dependencies + public_api + internal_structure + consumer_pattern + cross_refs

Full schema details + helper API sketch live in memory `project_schema_anchored_generate_docs.md`.

**Sub-steps:**

- 1a. Validate schemas against more sample docs from `cse-strata-ws-forge/docs/db-cse-ui-strata/` (read 5–10 representative per-package + feature docs; confirm schema fields cover actual onboard output shape; refine if gaps surface)
- 1b. Implement `onboard_helper.py` setters (one per field, mirror `detect_report.py` patterns: argparse, validation, atomic JSON state writes, idempotent reset)
- 1c. Implement markdown render templates (one per doc type — `_render_project_index`, `_render_architecture`, `_render_package_doc`); add `render-all` subcommand that reads state and writes all `.md` files
- 1d. Update `/generate-docs` spec (formerly `onboard/main.md`) to instruct LLM via the new helper API instead of free-form markdown writes; existing main.md becomes ~60% smaller (LLM provides values, doesn't compose markdown)
- 1e. Tests covering each setter + each render template + the `render-all` end-to-end pipeline (target ~80-120 tests, parallel to `detect_report`'s 126)
- 1f. Implement `onboard_helper validate` subcommand — mechanical quality measurement across four dimensions: slot-fill rate, citation validity rate, code-snippet fidelity rate (snippets match source at cited line ranges, verbatim whitespace-normalized), dependency accuracy rate. Composite score with 0.95 default pass threshold. CI-runnable. Report identifies failed snippets requiring re-generation (strongest hallucination check — code can't be fabricated if validated against source). Tests parallel detect_report patterns plus snippet-vs-source comparison logic.

**Verify**: re-run `/generate-docs` against testForge20. The 97 generated docs are structurally consistent (every package doc has Overview / Directory Structure / Main Exports / Types / Dependencies / Usage Example sections in same order); citation format conforms to `<file>:<line-range>` regex; required fields present everywhere; helper rejects malformed inputs (test by passing bad citation, bad enum value); `onboard_helper validate` produces composite quality ≥0.95 with no failed snippets.

**Cost estimate**: 2-3 sessions for the helper buildout + tests + spec refactor. Largest single step in the pivot.

**Integration with downstream steps**: `/configure` (Step 4) reads docs that are now structurally parseable — it can extract per-package scripts directly from the `Scripts:` section without ecosystem-default fallbacks. Closes the experiment's biggest gap (per-package script commands not in onboard's free-form docs).

### Step 3: Decide and implement config-file capture for `runtime_url_value`

Two options:
- (A) `/generate-docs` captures key config files (`vite.config.ts`, `next.config.js`, `webpack.config.js`, etc.) into per-app docs as quoted blocks
- (B) `/configure` reads config files directly as a small focused step

Pick one. (B) is simpler (no template change to onboard); (A) is more uniform (single source for everything).

**Verify**: for testForge20, `/configure` produces `runtime_url_value: https://okta.local.dev.dice-tools.com:8080` (matching the actual `vite.config.ts` `server.host` + `server.port` combination), not the framework-default `http://localhost:5173`.

### Step 1: Write `/init-forge` spec ✓ DONE

Commits: `a55d923`, `052cf2a`, `bd544ff` on `develop-2.0-init`. See "Step 1 outcomes" section near top of this plan for details.

**Verify** (passed): running `/init-forge` on testForge20 produces all 5 fields in `.devforge/init.yaml` (workspace_mode=wrapper, project_root=db-cse-ui-strata, project_state=brownfield, default_branch=dev, packages_detected=26 records). Render Summary step displays the values verbatim before `/generate-docs` handoff.

### Step 4: Write `/configure` spec ✓ DONE 2026-05-10

Full feature delivered end-to-end on testForge20 (wrapper + 26-pkg monorepo). See `CONFIGURE-PLAN.md` for the full work order; final delivery state matches that plan plus several Step 6 follow-ups (JSON-array setter form, case-insensitive enum, dash-delimited frontmatter parser, framework_hint helper-side enforcement, install.sh stray-state-file guard). Step 7 (install.sh chain orchestration) shipped 2026-05-10. Step 8 (this status flip) closes the feature.

**Detailed plan: `CONFIGURE-PLAN.md`** (design locked 2026-05-10; empirical pass against testForge20 + locked decisions on helper foundation, state shape, and bulk-confirmation flow). The original "consume legacy onboard docs + reuse `detect_report` / `wizard_render`" framing below is superseded by the plan file — read CONFIGURE-PLAN.md before starting Step 4.

Original framing (kept as historical context):
- Doc-reading logic (read all per-package docs, extract evidence per detect.md field)
- Yaml-population logic (invoke detect_report setters with doc-cited evidence)
- Q1–Q12 transferred from current `src/commands/setup-wizard/references/questions.md`
- Template substitution (replaces `{{...}}` placeholders with final values)

Updated framing (per CONFIGURE-PLAN.md):
- New `configure_helper.py` (mirrors `init_helper.py` pattern); `detect_report` + `wizard_render` are deprecated and not reused.
- Single source-of-truth state file: `.devforge/configure.yaml`; `project-config.json` becomes a render artifact.
- Inputs: `init.yaml` + `index.json` + `docs/{overview,architecture}.md` + config files (basename-matched against `index.json` file list, no fresh scan).
- Helper-owns-shape extends to template substitution (`substitute-templates` subcmd; LLM does not edit CLAUDE.md / agents directly).
- Bulk-confirmation for ~23 detection-derived fields + 4-6 sequential AskUserQuestion calls for user-only preferences (Q9-Q12 inc. NEW Q11 + Q12).

**Verify**: running `/configure` on a project where `/init-forge` + `/generate-docs` have completed produces a fully-populated `.devforge/configure.yaml` (28 fields) + a regenerated `project-config.json` + substituted `CLAUDE.md` and agent files. All Q9-Q12 user choices captured. Templates have no remaining `{{...}}` markers.

### Step 5: Migrate Q1–Q12 INTENT (not implementation) from current questions.md to /configure

The Q1-Q12 work on `develop-2.0-setup-wizard` branch transfers in INTENT (which fields exist, what their value spaces are, what the user is being asked) but COLLAPSES in implementation:

- Q1 (project name), Q2 (project description), Q3 (project type), Q4 (architecture), Q5 (error handling), Q6 (runtime URL), Q7 (API layer), Q8 (testing framework) — all these collapse into the bulk-confirmation prompt. Per-question two-branch precondition logic is gone; replaced by docs-driven detection + bulk review.
- Q9 (workflow_enforcement), Q10 (AI attribution), Q11 (agent tiers — not yet written), Q12 (AC verification — not yet written) — stay as sequential prompts (user-only fields).

**Verify**: /configure on testForge20 produces correct yaml + project-config.json with one bulk confirmation interaction + 4 sequential user-only prompts. The Q5 testForge20 case (purify-ts + Either monad) appears in the bulk prompt with correct values, no override needed if docs-driven detection produced them correctly.

### Step 6: Update install.sh to orchestrate the chain ✓ DONE 2026-05-10

install.sh's header comment + final-message string updated to reference the 4-command sequence (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). update.sh's three /setup-wizard warnings (lines 168, 355, 377) redirected to /configure. install.sh also gained a stray-user-state-file guard (rejects accidental `init.yaml` / `configure.yaml` left in `src/devforge/` from helper runs at repo root). The actual chain auto-execution is NOT shipped — slash commands run inside Claude Code, not from a shell script; install.sh just lays files + tells the user the order.

`install.sh` chains `/init-forge` → `/generate-docs` → `/configure` → `/constitute` for first-time installs. Each step can be re-run independently.

**Step-1 partial progress** (already shipped): install.sh's final-message string was updated from `Next — run /setup-wizard` to `Next — open the project and run /init-forge in Claude Code`. The actual chain auto-execution is still pending. install.sh's header comment block (lines 1-9) still references `/setup-wizard` philosophy — clean up here.

**Verify**: fresh-project install runs through all four commands cleanly, producing a fully-configured project. Re-running individual commands (e.g., `/generate-docs` after a code refactor) updates only their outputs.

### Step 7: Decommission old detect.md / setup-wizard

Once `/init-forge` + `/configure` cover the same ground:
- Delete `src/commands/setup-wizard/` (or rename to `setup-wizard-OLD` until migration is complete)
- Delete `src/devforge/lib/wizard_render.py` + launcher
- Delete `src/devforge/lib/detect_report.py` + launcher (currently docstring-marked deprecated; full delete here)
- Update 3 user-facing warnings in `update.sh` (lines 168, 355, 377) currently pointing at `/setup-wizard` — likely redirect to `/configure`
- Update `install.sh` header comment block (lines 1-9) currently describing `/setup-wizard` philosophy
- detect.md is no longer load-bearing once Step 1 (done) + Step 4 ship — its content has dispersed

**Step-1 partial progress** (already shipped): emitter `scripts/emitters/claude.py` removed `setup-wizard` from `_PROMOTED`, so new installs no longer ship `setup-wizard.md` into `<target>/.claude/commands/`. Source files + helpers retained here; full delete waits for `/configure` to land.

**Verify**: no references to `/setup-wizard` remain in active code paths. Existing test data (testForge20, cse-strata-ws-forge) still produces correct outputs through the new sequence.

### Step 8: Schema-anchor /constitute

Apply the same helper-owns-shape pattern to `/constitute`'s `constitution.md` output. Schema validated against cse-strata-ws-forge constitution.md (451 lines). 7 top-level sections, closed rule-tag enum (`extracted`/`enforced`/`universal`/`project-specific`), structured tables + code examples.

Sub-steps:
- 8a. Implement `constitute_helper.py` setters (parallels `onboard_helper.py` pattern from Step 1)
- 8b. Implement render function (manual concatenation per the same approach as generate-docs)
- 8c. Implement `validate` subcommand (same 4-dimension quality framework: slot-fill, citation validity, code-example syntax check, rule-tag validity)
- 8d. Update `/constitute` spec to instruct LLM via the helper API instead of free-form markdown
- 8e. Tests parallel `constitute_helper`'s shape (target ~50-80 tests)

**Verify**: re-running `/constitute` against testForge20 produces a constitution.md structurally identical to current cse-strata-ws-forge/constitution.md (or improved); `constitute_helper validate` reports composite quality ≥0.95; rule tags all from the closed enum; tables and code examples correctly rendered.

**Cost estimate**: 1-2 sessions on top of the rest of the pivot. The helper is smaller than `onboard_helper` but the schema includes patterns/anti-patterns (6 buckets) and tables, so render logic is non-trivial.

Schema details + helper API in memory `project_schema_anchored_constitute.md`.

## Open decisions

- **Config-file capture**: in `/generate-docs` template (uniform) or `/configure` direct read (simpler)? Decide at step 2.
- **Helper renames**: should `wizard_render` get renamed to match new architecture? E.g., `configure_render`? Cosmetic but worth aligning. Decide during step 4.
- **Backward compatibility**: existing projects running old `/setup-wizard` need migration path or are forced to re-init? Lean: forced re-init since this is a refactor; document in CHANGELOG.
- **Q11–Q12 status**: Q11 (Agent Tier Models) and Q12 (AC Verification Mode) are not yet written under old architecture. Write them under new `/configure` spec directly, not as catch-up under old `/setup-wizard`.

## When resuming work

**Status as of last save**: Step 1 done (commits `a55d923`, `052cf2a`, `bd544ff` on `develop-2.0-init`). Tests 336/336 passing. Working tree clean. Step 2 next.

1. Read this plan in full — pay attention to the "Step 1 outcomes" section near the top for what's already shipped + how it differs from the original plan
2. Read `project_schema_anchored_generate_docs.md` from `~/.claude/projects/.../memory/` for Step 2's schema details
3. Confirm test data still available: `ls /Users/mykolakudlyk/Projects/testForge20/.devforge/` (should contain `init.yaml` + legacy `detection_report.yaml`) and `ls /Users/mykolakudlyk/Projects/doosan/cse-strata-ws-forge/docs/`
4. Confirm helper baseline: `python3 -m unittest discover tests/lib -q` should report 336/336 OK
5. Execute remaining steps in order: **Step 2 (schema-anchor `/generate-docs`)** → Step 3 (config-file capture decision) → Step 4 (write `/configure` spec) → Step 5 (migrate Q1–Q12) → Step 6 (install.sh chain) → Step 7 (decommission old setup-wizard) → Step 8 (schema-anchor /constitute). Each step independently testable; no need to bundle.
6. Use the iterative apply-verify loop established this session:
   - For Python: `python-engineer` writes function + tests in same turn → `python-reviewer` audits → loop until clean
   - For specs: `instruction-author` writes → `instruction-reviewer` + `claude-code-guide` audit in parallel → loop until clean
7. **When adding a new command**: ALSO add to `scripts/emitters/claude.py` `_PROMOTED` tuple AND verify end-to-end install (run `install.sh` against tmpdir, check `<target>/.claude/commands/` has the new file). Step-1 lesson: missed this initially.
8. Commit each step independently; don't bundle
9. Step-2 parallel concern: `onboard_helper.py` is currently a stub (~50 lines). Step 2 buildout target is ~80-120 tests parallel to `init_helper`'s 92.

Test data validation: every step should be verifiable against testForge20 (the wrapper + monorepo edge case). If a step works for testForge20, it works for the easy single-package case by construction.
