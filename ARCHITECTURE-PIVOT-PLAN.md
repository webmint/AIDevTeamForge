# Architecture Pivot — 4-command sequence

**Status**: approved 2026-04-30. Not yet started. Empirical validation complete.

User-approved pivot from current `/setup-wizard` + `/onboard` + `/constitute` trio to a four-command sequence: `/init` → `/generate-docs` → `/configure` → `/constitute`. Detection moves from Phase 1 light-scan (in current setup-wizard) to onboard's deep scan (renamed `/generate-docs`).

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

- Branch: `develop-2.0-setup-wizard`
- Q1–Q10 of questions.md written under OLD architecture (single `/setup-wizard` flow)
- Helpers: `detect_report` (23+ setters + summary), `wizard_render` (10 setters)
- Phase 1 detection (detect.md §4.1–§4.6) implemented and recently patched
- Last work commit: `5e180f8` (detect: weaken §4.4 to manifest-dep-sufficient)

The Q1–Q10 question logic transfers to `/configure` mostly unchanged. Phase 1's structural steps (workspace_mode, project_root, default_branch, project_state, packages_detected) transfer to `/init`. Phase 1's library/architecture/error-handling/runtime-url detection (§4.4–§4.6) is replaced by onboard-driven detection in `/configure`.

## The 4-command sequence

### `/init` — minimal structural bootstrap

Captures 5 fields. Bash-style fast. LLM only orchestrates.

- `workspace_mode` (user choice via AskUserQuestion: standalone vs wrapper)
- `project_root` (user choice in wrapper mode; `.` in standalone)
- `default_branch` (git query)
- `project_state` (filesystem check: empty vs brownfield, per current detect.md Step 2)
- `packages_detected` (manifest path + filename walk; no content reads)

Side effect: installs framework files (`.devforge/`, `.claude/`, CLAUDE.md template, agent templates with `{{...}}` placeholders intact).

Implemented as: `src/commands/init/main.md` + `src/commands/init/references/*.md` + extends `install.sh`.

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

### Step 1: Schema-anchor `/generate-docs` outputs

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

**Verify**: re-run `/generate-docs` against testForge20. The 97 generated docs are structurally consistent (every package doc has Overview / Public API / Internal Structure / Dependencies / Scripts sections in same order); citation format conforms to `<file>:<line-range>` regex; required fields present everywhere; helper rejects malformed inputs (test by passing bad citation, bad enum value).

**Cost estimate**: 2-3 sessions for the helper buildout + tests + spec refactor. Largest single step in the pivot.

**Integration with downstream steps**: `/configure` (Step 4) reads docs that are now structurally parseable — it can extract per-package scripts directly from the `Scripts:` section without ecosystem-default fallbacks. Closes the experiment's biggest gap (per-package script commands not in onboard's free-form docs).

### Step 2: Decide and implement config-file capture for `runtime_url_value`

Two options:
- (A) `/generate-docs` captures key config files (`vite.config.ts`, `next.config.js`, `webpack.config.js`, etc.) into per-app docs as quoted blocks
- (B) `/configure` reads config files directly as a small focused step

Pick one. (B) is simpler (no template change to onboard); (A) is more uniform (single source for everything).

**Verify**: for testForge20, `/configure` produces `runtime_url_value: https://okta.local.dev.dice-tools.com:8080` (matching the actual `vite.config.ts` `server.host` + `server.port` combination), not the framework-default `http://localhost:5173`.

### Step 3: Write `/init` spec

Create `src/commands/init/main.md` + references. Carries over from current `detect.md` Steps 1–3 + the manifest-discovery part of Step 4.1 (just paths + filenames, no content). Adds framework-file installation logic (formerly install.sh territory).

**Verify**: running `/init` on a fresh project produces the 5 structural fields in detection_report.yaml + installs `.devforge/`, `.claude/`, CLAUDE.md template, agent templates. No yaml fields beyond the 5 are populated. No questions beyond workspace_mode + project_root.

### Step 4: Write `/configure` spec

Create `src/commands/configure/main.md` + references. Combines:
- Doc-reading logic (read all per-package docs, extract evidence per detect.md field)
- Yaml-population logic (invoke detect_report setters with doc-cited evidence)
- Q1–Q12 transferred from current `src/commands/setup-wizard/references/questions.md`
- Template substitution (replaces `{{...}}` placeholders with final values)

**Verify**: running `/configure` on a project where `/init` + `/generate-docs` have completed produces a fully-populated detection_report.yaml + project-config.json + substituted CLAUDE.md and agent files. All Q1–Q12 user choices are captured. Templates have no remaining `{{...}}` markers.

### Step 5: Migrate Q1–Q12 INTENT (not implementation) from current questions.md to /configure

The Q1-Q12 work on `develop-2.0-setup-wizard` branch transfers in INTENT (which fields exist, what their value spaces are, what the user is being asked) but COLLAPSES in implementation:

- Q1 (project name), Q2 (project description), Q3 (project type), Q4 (architecture), Q5 (error handling), Q6 (runtime URL), Q7 (API layer), Q8 (testing framework) — all these collapse into the bulk-confirmation prompt. Per-question two-branch precondition logic is gone; replaced by docs-driven detection + bulk review.
- Q9 (workflow_enforcement), Q10 (AI attribution), Q11 (agent tiers — not yet written), Q12 (AC verification — not yet written) — stay as sequential prompts (user-only fields).

**Verify**: /configure on testForge20 produces correct yaml + project-config.json with one bulk confirmation interaction + 4 sequential user-only prompts. The Q5 testForge20 case (purify-ts + Either monad) appears in the bulk prompt with correct values, no override needed if docs-driven detection produced them correctly.

### Step 6: Update install.sh to orchestrate the chain

`install.sh` chains `/init` → `/generate-docs` → `/configure` → `/constitute` for first-time installs. Each step can be re-run independently.

**Verify**: fresh-project install runs through all four commands cleanly, producing a fully-configured project. Re-running individual commands (e.g., `/generate-docs` after a code refactor) updates only their outputs.

### Step 7: Decommission old detect.md / setup-wizard

Once `/init` + `/configure` cover the same ground:
- Delete `src/commands/setup-wizard/` (or rename to `setup-wizard-OLD` until migration is complete)
- detect.md content disperses: structural parts (Steps 1–3) → /init's references; library/architecture/error-handling/runtime-url detection (§4.4–§4.6) → /configure's references (with docs-source instead of grep-source)
- questions.md fully migrates to /configure's references

**Verify**: no references to `/setup-wizard` remain in active code paths. Existing test data (testForge20, cse-strata-ws-forge) still produces correct outputs through the new sequence.

## Open decisions

- **Config-file capture**: in `/generate-docs` template (uniform) or `/configure` direct read (simpler)? Decide at step 2.
- **Helper renames**: should `wizard_render` get renamed to match new architecture? E.g., `configure_render`? Cosmetic but worth aligning. Decide during step 4.
- **Backward compatibility**: existing projects running old `/setup-wizard` need migration path or are forced to re-init? Lean: forced re-init since this is a refactor; document in CHANGELOG.
- **Q11–Q12 status**: Q11 (Agent Tier Models) and Q12 (AC Verification Mode) are not yet written under old architecture. Write them under new `/configure` spec directly, not as catch-up under old `/setup-wizard`.

## When resuming work

1. Read this plan in full
2. Read the experiment evidence at the experiment commit (TBD — this plan being saved is the marker)
3. Read `project_4command_architecture_pivot.md` from `~/.claude/projects/.../memory/`
4. Confirm test data still available: `ls /Users/mykolakudlyk/Projects/testForge20/.devforge/` and `ls /Users/mykolakudlyk/Projects/doosan/cse-strata-ws-forge/docs/`
5. Pick step 1 (extend `/generate-docs` template with Scripts subsection) or step 3 (write `/init` spec) — both are valid entry points; step 1 unblocks step 2's option A; step 3 unblocks step 4
6. Use the iterative apply-verify loop established this session: instruction-author writes, instruction-reviewer + claude-code-guide verify in parallel, loop until clean
7. Commit each step independently; don't bundle

Test data validation: every step should be verifiable against testForge20 (the wrapper + monorepo edge case). If a step works for testForge20, it works for the easy single-package case by construction.
