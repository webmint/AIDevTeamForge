# /configure — implementation plan

**Status**: design locked 2026-05-10. Ship pending. Branch `develop-2.0-init`. Predecessor work: `/init-forge` (Step 1, DONE) + `/generate-docs` (Step 2, FEATURE-CLOSED). This is Step 4 of `ARCHITECTURE-PIVOT-PLAN.md`.

`/configure` is the third command in the 4-command sequence (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). It consumes `.devforge/init.yaml`, `.devforge/index.json`, `docs/overview.md`, `docs/architecture.md`, and a focused subset of repo config files; populates `.devforge/configure.yaml`; renders `.devforge/project-config.json`; and substitutes `{{...}}` placeholders in `CLAUDE.md` + `.claude/agents/*.md` to materialize the project's runtime configuration.

## Context for next session

### What changed since the original pivot plan was written

The 2026-04-30 pivot plan described `/configure` as "consume legacy onboard docs + use `detect_report` setters + populate `detection_report.yaml` + write `project-config.json` via `wizard_render`". That description is stale. Three architectural shifts since then:

1. `/generate-docs` is schema-anchored (Plan F shipped + judgment-layer Track B shipped + FEATURE-CLOSED 2026-05-10). Its docs/ output is structurally parseable: `docs/overview.md` has a fixed-shape Tech Stack table + Project Structure tree + Key Commands table; `docs/architecture.md` has Architecture Overview + Patterns + Conventions; `docs/glossary.md` has CBM-classified terms. /configure no longer "reads free-form onboard docs" — it parses a known shape.
2. `detect_report.py` + `wizard_render.py` are deprecated. ARCHITECTURE-PIVOT-PLAN Step 7 deletes both. Building /configure on them = double work + reinforces what we're removing. /configure gets its own helper from the start: `configure_helper.py`, mirroring the helper-owns-shape pattern established by `init_helper.py` + the `_generate_docs/` helper layout.
3. The single-yaml convention won. `/init-forge` writes `.devforge/init.yaml`; the legacy split between `detection_report.yaml` (deep-scan output) + `project-config.json` (wizard answers) is gone. /configure writes one yaml: `.devforge/configure.yaml`. `project-config.json` becomes a render artifact regenerated from the yaml on every run, parallel to how `docs/structure.md` is a render artifact of `index.json`.

### Empirical pass (2026-05-10)

Before drafting this plan, the docs/ output, manifest extraction surface, and template placeholder list were inventoried against testForge20 (the wrapper-mode + 26-package-monorepo test bed):

- `docs/overview.md` exposes 11 sections: Purpose, Tech Stack (Layer | Technology table), Project Structure (annotated tree), Entry Points, Key Commands (Command | Description table), Module Map (Infrastructure / Core / Domain bucket tables), Cross-Module Dependencies (text tree), Application Routes, Navigation Guards, Test Files, Packages.
- `docs/architecture.md` exposes 8 sections: Architecture Overview, Module/Package Structure, Patterns (with code samples), Conventions, Layers, Cross-Cuts, Dependency Direction Rules, Dependency Overview.
- `docs/glossary.md` is alphabetical term entries with code anchors.
- `.devforge/index.json` carries per-package `manifest_scripts` (npm scripts block) + `manifest_dependencies` + `files[]` (capped at 500). Sufficient to derive `BUILD_COMMANDS` / `TYPE_CHECK_COMMANDS` / `LINT_COMMANDS` per package without re-parsing manifests.
- `.devforge/project-config.json` (legacy shape) has 36 keys. 5 are filled by /init-forge already; 22 are detection-derivable from docs + manifest + config files; 5 are user-only preferences (Q9-Q12).

The detection-derivable set is bigger than the original plan assumed — Plan F's tech-stack table + architecture overview together cover what the old onboard free-form docs left to ecosystem-defaults. The Q5 testForge20 benchmark case (`error_handling_pattern: Either monad`) now resolves directly off the architecture.md Patterns section, not off a 5-file grep.

### Test bed

- `/Users/mykolakudlyk/Projects/testForge20/` — wrapper mode, `project_root = db-cse-ui-strata`, 26 packages, fully populated `.devforge/{init.yaml,index.json}` + `docs/{overview,architecture,glossary,structure}.md` + per-package + per-concern docs.
- `.devforge/project-config.json` exists with all 36 keys NULL — confirms /configure is the missing piece.

## Goal

Ship `/configure` as the third command in the 4-command sequence. Verify on testForge20: re-running `/configure` after `/init-forge` + `/generate-docs` produces a fully-populated `.devforge/configure.yaml` (28 fields filled) + a fully-substituted `CLAUDE.md` (no `{{...}}` markers remain) + a fully-substituted set of agent files in `.claude/agents/`. Q11 + Q12 captured cleanly. End-to-end runs in under 5 minutes wall-clock with one bulk-confirmation prompt + four sequential prompts.

## Architecture

### State + render

```
.devforge/
  configure.yaml           # canonical state — single source of truth
  project-config.json      # render artifact — regenerated each run
CLAUDE.md                  # substituted in-place
.claude/agents/*.md        # substituted in-place
```

`configure.yaml` is the source of truth. Every setter does atomic read-modify-write. `project-config.json` is regenerated from `configure.yaml` on each `render-config` call — never edited directly. Template files (`CLAUDE.md`, `.claude/agents/*.md`) are substituted in-place by `substitute-templates` using `configure.yaml` as the substitution map.

### Helper boundary

`configure_helper.py` mirrors `init_helper.py`'s pattern: stdlib-only, atomic writes via `tempfile.mkstemp` + `os.replace`, locked field order in `FIELD_SCHEMA`, enum constraints in `ENUM_FIELDS`, defaults to `None` / `[]`. Helper owns:

- Field schema (locked order, enum constraints, default values)
- Yaml emission shape (deterministic — diff-stable across re-runs)
- Doc-extraction logic (Plan F section parsers)
- Manifest-extraction logic (read from `index.json`, not from disk)
- Config-file basename match (against `index.json` file list — no fresh scan)
- Render-config rules (configure.yaml → project-config.json)
- Template substitution rules (placeholder-find regex, atomic per-file write, list of templates)
- Validation (per-field shape, cross-field invariants where they exist)

LLM owns:
- Field values (composed from helper-pre-extracted inputs)
- Bulk-confirmation prompt rendering (orchestrator-direct, plain prose echo)
- Sequential AskUserQuestion calls for Q9-Q12

### Phase shape

```
Phase 0 — Pre-flight gate
  test -f .devforge/init.yaml          (else ABORT: run /init-forge first)
  test -f .devforge/index.json         (else ABORT: run /init-forge build-index)
  test -f docs/overview.md             (else ABORT: run /generate-docs first)
  test -f docs/architecture.md         (else ABORT: run /generate-docs first)

Phase 1 — Reset + pull inputs
  configure_helper reset
  configure_helper read-init           # echoes init.yaml fields as JSON
  configure_helper read-docs           # parses Plan F sections; emits structured JSON
  configure_helper read-manifests      # reads index.json; emits per-package script tables
  configure_helper read-configs        # basename-matches config files in index.json file list; reads matched

Phase 2 — Compose detection-derived values (orchestrator-direct, NO subagent)
  LLM synthesizes 22 fields from Phase 1 JSON outputs:
    Identity: PROJECT_NAME, PROJECT_TYPE, PROJECT_DESCRIPTION
    Stack:    PRIMARY_LANGUAGE, LANGUAGES, FRAMEWORKS, ARCHITECTURES,
              ERROR_HANDLINGS, API_LAYERS, TESTINGS, BUILD_TOOLS
    Per-pkg:  BUILD_COMMANDS, TYPE_CHECK_COMMANDS, LINT_COMMANDS, PACKAGE_STACKS
    Render:   PROJECT_STRUCTURE (verbatim from docs), DEV_COMMANDS (verbatim),
              ARCHITECTURE_DETAILS (verbatim)
    Runtime:  AC_RUNTIME_URL, AC_RUNTIME_API_BASE, AC_RUNTIME_CLI_COMMAND

Phase 3 — Bulk-confirmation prompt (plain prose, NOT AskUserQuestion)
  Orchestrator echoes all 23 detection-derived fields in a fenced block.
  User: 'yes' (apply all) OR 'cancel' OR line-per-override.
  Each accepted/overridden value applied via configure_helper set-<field>.

Phase 4 — Sequential user-only prompts (AskUserQuestion)
  Q9  set-workflow-enforcement      (Strict | Moderate | Light)
  Q10 set-ai-attribution            (Yes | No)
  Q11 set-claude-tier-think         (Opus | Sonnet | Haiku | Other)
  Q11 set-claude-tier-do            (Opus | Sonnet | Haiku | Other)
  Q11 set-claude-tier-verify        (Opus | Sonnet | Haiku | Other)
  Q12 set-ac-verification-mode      (code-only | tests | runtime-assisted | off)
  Q12.x conditional (if mode == runtime-assisted):
       set-ac-runtime-url           (pre-filled from Phase 2 detection)
       set-ac-runtime-api-base
       set-ac-runtime-cli-command

Phase 5 — Render + substitute
  configure_helper render-config         # writes .devforge/project-config.json
  configure_helper substitute-templates  # walks CLAUDE.md + .claude/agents/*.md;
                                         # replaces {{KEY}} from configure.yaml

Phase 6 — Verify + report
  configure_helper verify       # cross-checks all 28 fields populated,
                                # no remaining {{KEY}} in templates,
                                # project-config.json round-trips
  configure_helper summary      # verbatim-echo report (mirrors init_helper)
```

The retry budget per setter is 3 (matches /generate-docs convention). On 4th setter failure, surface to user + abort the run. On bulk-prompt parse failure, re-prompt with a clarification.

## Field-source map

Twenty-seven fields populated by /configure. Five more (`PROJECT_ROOT`, `WORKSPACE_MODE`, `PROJECT_STATE`, `DEFAULT_BRANCH`, `PACKAGES_DETECTED`) are read-through from `init.yaml`.

| Field | Source | Phase | Bulk vs Sequential |
|---|---|---|---|
| `PROJECT_NAME` | `index.json` root manifest `name` | 1+2 | Bulk |
| `PROJECT_TYPE` | LLM 13-cat taxonomy from `FRAMEWORKS` + `LANGUAGES` | 2 | Bulk |
| `PROJECT_DESCRIPTION` | `docs/overview.md` `## Purpose` paragraph | 1+2 | Bulk |
| `PRIMARY_LANGUAGE` | `docs/overview.md` Tech Stack `Language` row | 1+2 | Bulk |
| `LANGUAGES` | LLM per-package summary from manifests | 2 | Bulk |
| `FRAMEWORKS` | `docs/overview.md` Tech Stack `Framework` row | 1+2 | Bulk |
| `ARCHITECTURES` | LLM extract from `docs/architecture.md` `## Architecture Overview` | 2 | Bulk |
| `ERROR_HANDLINGS` | LLM extract from `docs/architecture.md` `## Patterns` + `## Conventions` | 2 | Bulk |
| `API_LAYERS` | `docs/overview.md` Tech Stack `API Layer` row | 1+2 | Bulk |
| `TESTINGS` | `docs/overview.md` Tech Stack `Testing` row | 1+2 | Bulk |
| `BUILD_TOOLS` | `docs/overview.md` Tech Stack `Build Tool` row + per-pkg manifest | 1+2 | Bulk |
| `BUILD_COMMANDS` | per-pkg `index.json` manifest `scripts.build` (+ ecosystem fallback) | 1+2 | Bulk |
| `TYPE_CHECK_COMMANDS` | per-pkg `index.json` manifest `scripts.typecheck` / `tsc` | 1+2 | Bulk |
| `LINT_COMMANDS` | per-pkg `index.json` manifest `scripts.lint` | 1+2 | Bulk |
| `PACKAGE_STACKS` | composite per-package record (lang + framework + build commands) | 2 | Bulk |
| `PROJECT_STRUCTURE` | `docs/overview.md` `## Project Structure` text-tree (verbatim) | 1 | Bulk (verbatim — confirm-only) |
| `DEV_COMMANDS` | `docs/overview.md` `## Key Commands` table (verbatim) | 1 | Bulk (verbatim) |
| `ARCHITECTURE_DETAILS` | `docs/architecture.md` `## Architecture Overview` paragraph (verbatim) | 1 | Bulk (verbatim) |
| `WRAPPER_MODE_SECTION` | preset block from `WORKSPACE_MODE` | derived | none |
| `COMMIT_ATTRIBUTION` | preset block from `AI_ATTRIBUTION` | derived | none |
| `AGENT_LIST` | render of `.claude/agents/*.md` filenames | derived | none |
| `AC_RUNTIME_URL` | LLM extract from matched config files | 1+2 | Bulk |
| `AC_RUNTIME_API_BASE` | LLM extract from matched config files / env | 1+2 | Bulk |
| `AC_RUNTIME_CLI_COMMAND` | LLM extract from manifest `scripts.dev` / `scripts.start` | 1+2 | Bulk |
| `WORKFLOW_ENFORCEMENT` | Q9 user choice | 4 | Sequential |
| `AI_ATTRIBUTION` | Q10 user choice | 4 | Sequential |
| `CLAUDE_TIER_THINK` | Q11.1 user choice | 4 | Sequential |
| `CLAUDE_TIER_DO` | Q11.2 user choice | 4 | Sequential |
| `CLAUDE_TIER_VERIFY` | Q11.3 user choice | 4 | Sequential |
| `AC_VERIFICATION_MODE` | Q12 user choice | 4 | Sequential |

`WRAPPER_MODE_SECTION`, `COMMIT_ATTRIBUTION`, `AGENT_LIST` are derived during `render-config` from already-populated fields — they don't have setters and don't appear in the bulk prompt.

## Config-file basename match

`read-configs` walks `index.json.packages[*].files[]` and matches basenames against a fixed pattern set:

```
vite.config.ts | vite.config.js | vite.config.mjs
next.config.ts | next.config.js | next.config.mjs
nuxt.config.ts | nuxt.config.js
webpack.config.ts | webpack.config.js
vitest.config.ts | vitest.config.js
jest.config.ts | jest.config.js
.env | .env.local | .env.development
```

Matched files are read in full and the contents emitted in the JSON output keyed by basename. The LLM extracts `AC_RUNTIME_URL` (vite: `server.host` + `server.port`; next: `server.port`; webpack: `devServer.host` + `devServer.port`), `AC_RUNTIME_API_BASE` (env: `VITE_API_URL` / `NEXT_PUBLIC_API_URL` / `REACT_APP_API_URL`), and `AC_RUNTIME_CLI_COMMAND` (manifest: `scripts.dev` / `scripts.start`). No fresh filesystem scan.

## Schema — `configure.yaml`

Schema is locked field order. The yaml emitter walks `FIELD_SCHEMA` so field order is part of the diff-stability contract.

```python
FIELD_SCHEMA = (
    # Identity
    ("project_name",          "scalar"),
    ("project_description",   "scalar"),
    ("project_type",          "scalar"),

    # Stack
    ("primary_language",      "scalar"),
    ("languages",             "string_array"),
    ("frameworks",            "string_array"),
    ("architectures",         "string_array"),
    ("error_handlings",       "string_array"),
    ("api_layers",            "string_array"),
    ("testings",              "string_array"),
    ("build_tools",           "string_array"),

    # Per-package (derived from manifests)
    ("build_commands",        "string_array"),
    ("type_check_commands",   "string_array"),
    ("lint_commands",         "string_array"),
    ("package_stacks",        "package_stack_array"),

    # Verbatim from docs/
    ("project_structure",     "scalar"),
    ("dev_commands",          "scalar"),
    ("architecture_details",  "scalar"),

    # User-only preferences
    ("workflow_enforcement",  "scalar"),
    ("ai_attribution",        "scalar"),
    ("claude_tier_think",     "scalar"),
    ("claude_tier_do",        "scalar"),
    ("claude_tier_verify",    "scalar"),

    # AC verification
    ("ac_verification_mode",  "scalar"),
    ("ac_runtime_url",        "scalar"),
    ("ac_runtime_api_base",   "scalar"),
    ("ac_runtime_cli_command","scalar"),
)

ENUM_FIELDS = {
    "workflow_enforcement":  {"Strict", "Moderate", "Light"},
    "ai_attribution":        {"Yes", "No"},
    "claude_tier_think":     {"Opus", "Sonnet", "Haiku", "Other"},
    "claude_tier_do":        {"Opus", "Sonnet", "Haiku", "Other"},
    "claude_tier_verify":    {"Opus", "Sonnet", "Haiku", "Other"},
    "ac_verification_mode":  {"code-only", "tests", "runtime-assisted", "off"},
}
```

`package_stack_array` shape: `[{"path": str, "language": str, "framework": str|null, "build_tool": str|null, "build_command": str|null, "type_check_command": str|null, "lint_command": str|null}]`. The shape mirrors `init.yaml.packages_detected[]` extended with stack metadata.

## Helper subcommand registry

```
reset
read-init
read-docs
read-manifests
read-configs

set-project-name <value>
set-project-description <value>
set-project-type <value>
set-primary-language <value>
set-languages <comma-sep-list>
set-frameworks <comma-sep-list>
set-architectures <comma-sep-list>
set-error-handlings <comma-sep-list>
set-api-layers <comma-sep-list>
set-testings <comma-sep-list>
set-build-tools <comma-sep-list>
set-build-commands <comma-sep-list>
set-type-check-commands <comma-sep-list>
set-lint-commands <comma-sep-list>
add-package-stack --path <p> --language <l> [--framework <f>] ...
set-project-structure --text <verbatim>
set-dev-commands --text <verbatim>
set-architecture-details --text <verbatim>
set-workflow-enforcement <Strict|Moderate|Light>
set-ai-attribution <Yes|No>
set-claude-tier-think <model>
set-claude-tier-do <model>
set-claude-tier-verify <model>
set-ac-verification-mode <mode>
set-ac-runtime-url <url>
set-ac-runtime-api-base <url>
set-ac-runtime-cli-command <command>

render-config
substitute-templates
verify
summary
```

Approximately 30 subcommands. Mirrors init_helper's pattern (8 subcmds for 5 fields + scan + summary); /configure has more fields so more setters.

## Template substitution

`substitute-templates` walks a fixed template list and replaces `{{KEY}}` markers atomically per file:

```
Templates substituted:
  CLAUDE.md
  .claude/agents/*.md      (every file in the directory; pattern match)
```

Substitution rules:
- `{{KEY}}` is replaced by `configure.yaml.<key>` (uppercase → lowercase mapping).
- Array fields render as comma-separated lists when substituted into scalar markers; renders as bullet lists when the marker is on its own line surrounded by whitespace.
- Missing fields raise an error (no silent default; the substitution is a contract).
- Each file write is atomic (`tempfile.mkstemp` + `os.replace`).
- The substitution map pre-computes derived fields (`WRAPPER_MODE_SECTION`, `COMMIT_ATTRIBUTION`, `AGENT_LIST`) before walking templates.

`PACKAGE_STACKS_SECTION` is rendered as a markdown table from `package_stacks[]`. `WRAPPER_MODE_SECTION` is rendered from a preset string template parameterized by `WORKSPACE_MODE` + `PROJECT_ROOT`.

## Step-by-step work order

Each step ends with verifiable evidence. Steps are independently committable.

### Step 0 — Scaffolding + emitter wiring

Create:
- `src/commands/configure/main.md` (stub: H1 + "TODO: implement")
- `src/commands/configure/references/q11-tiers.md` (stub)
- `src/commands/configure/references/q12-ac.md` (stub)
- `src/devforge/lib/configure_helper.py` (stub: argparse + reset only)
- `src/devforge/lib/configure_helper` (POSIX launcher; copy-paste from init_helper)
- `tests/lib/test_configure_helper.py` (stub with 1 test for reset)

Update `scripts/emitters/claude.py` `_PROMOTED` tuple to include `configure`.

**Verify**: `bash install.sh` against tmpdir → `<tmpdir>/.claude/commands/configure.md` exists; `<tmpdir>/.devforge/lib/configure_helper` exists + executable; `python3 -m unittest tests.lib.test_configure_helper` passes (1 test).

### Step 1 — Helper schema + reset + read-* subcmds

Implement:
- `FIELD_SCHEMA` + `ENUM_FIELDS` + defaults
- `reset` subcmd (atomic write of fresh defaults)
- `read-init` subcmd (read `.devforge/init.yaml`, emit JSON to stdout)
- `read-docs` subcmd (parse Plan F sections from `docs/overview.md` + `docs/architecture.md`; emit structured JSON)
- `read-manifests` subcmd (walk `.devforge/index.json` packages, extract scripts; emit JSON)
- `read-configs` subcmd (basename-match config files in `index.json` file list; emit JSON keyed by basename)
- Tests for each: round-trip via real producers (init_helper writes init.yaml → read-init parses; generate_docs renders docs → read-docs parses).

**Verify**: `python3 -m unittest tests.lib.test_configure_helper` passes ~30 tests; running `configure_helper read-docs` against testForge20's `docs/overview.md` + `docs/architecture.md` produces JSON containing every Plan F section.

### Step 2 — Setters + atomic state

Implement every setter in the registry above. Each setter is a per-field shape-validate + atomic read-modify-write. Mirror `init_helper`'s setter shape (argparse, validation, `_load`, `_dump`).

Add `_load` / `_dump` helpers. Use the same `tempfile.mkstemp` + `os.replace` pattern.

Tests: per-setter validate-then-load test (assert yaml shape after each call). Round-trip test (set every field; reload; compare). Cross-process safety test (concurrent setters via subprocess; assert no lost writes — `init_helper` doesn't have this since fields are independent, but `add-package-stack` is array-append so it does need it).

**Verify**: ~80 setter tests pass. testForge20 round-trip: set every field; reload; compare; identical.

### Step 3 — render-config + verify + summary

Implement:
- `render-config` — read configure.yaml, derive `WRAPPER_MODE_SECTION` / `COMMIT_ATTRIBUTION` / `AGENT_LIST`, write `.devforge/project-config.json`. Atomic.
- `verify` — read configure.yaml, assert every required field non-null. Read project-config.json, assert round-trip identity. Emit pass/fail report. Exit 0 = pass, 2 = violation.
- `summary` — verbatim-echo report (mirrors `init_helper summary`). Field-by-field listing in locked order.

Tests: render-config produces valid JSON; verify catches missing fields; summary output stable across re-runs.

**Verify**: ~20 tests pass. testForge20 hand-populated fixture renders project-config.json with all 36 keys non-null.

### Step 4 — substitute-templates

Implement:
- Template list constant (`CLAUDE.md` + glob `.claude/agents/*.md`)
- Placeholder regex (`\{\{([A-Z_]+)\}\}`)
- Substitution map builder (configure.yaml + derived fields)
- Per-file atomic write
- Validation: after substitution, no `{{KEY}}` remains; raise on unmatched key

Tests: substitute against testForge20's `CLAUDE.md` template; assert zero remaining markers; assert specific substitutions land (e.g., `{{PROJECT_NAME}}` → `db-cse-ui-strata`); assert array → comma-list works; assert missing field raises.

**Verify**: ~20 tests pass. testForge20 end-to-end: `configure_helper substitute-templates` against a hand-populated configure.yaml produces a fully-substituted CLAUDE.md (visual diff inspection + grep for `{{`).

### Step 5 — Spec authoring (`src/commands/configure/main.md`)

Write the authoritative command spec following the Phase shape above. Mirrors `src/commands/init-forge/main.md`'s shape:
- Frontmatter (`name: configure`, `description: Populate config + substitute templates`, `disable-model-invocation: true`)
- H1 + Outputs section
- Phase 0 pre-flight gate
- Phase 1 read-* invocations
- Phase 2 LLM compose (orchestrator-direct, no subagent — mirrors /generate-docs convention)
- Phase 3 bulk-confirmation prompt format (literal echo template + parsing rules)
- Phase 4 sequential prompts (one section per Q with AskUserQuestion calls verbatim)
- Phase 5 render + substitute
- Phase 6 verify + report

Reference docs:
- `references/q11-tiers.md` — Q11.1/Q11.2/Q11.3 prompt details + recommended defaults rationale
- `references/q12-ac.md` — Q12 mode taxonomy + conditional Q12.x runtime details

Run `instruction-author` to write the spec; verify via `instruction-reviewer` + `claude-code-guide` per the iterative-review-loop convention.

**Verify**: spec passes both reviewers; sentence-level hallucination check passes (every sentence verifiable now or marked as forward-ref).

### Step 6 — End-to-end empirical run

Run `/configure` against testForge20 (with `/init-forge` + `/generate-docs` already complete). Confirm:
- All 28 fields land in `.devforge/configure.yaml`
- `.devforge/project-config.json` has all 36 keys non-null
- `CLAUDE.md` has zero remaining `{{...}}` markers
- `.claude/agents/*.md` have zero remaining `{{...}}` markers
- Bulk prompt fits one screen + parses 'yes' / overrides correctly
- Q11 (3 prompts) + Q12 (1-4 prompts conditional) flow cleanly
- `configure_helper verify` exits 0
- Total wall-clock < 5 min

If any field detection misfires on testForge20's wrapper-mode + 26-package monorepo, fix in the same commit.

**Verify**: full run logged + committed under `testParity-configure-run1` worktree branch (mirrors prior parity-run convention).

### Step 7 — install.sh chain integration

Update `install.sh` to chain the 4 commands. Update header comment. Update `update.sh` warnings (currently still reference `/setup-wizard` per ARCHITECTURE-PIVOT-PLAN §Step 1 follow-ups).

**Verify**: fresh install on a tmpdir runs `/init-forge` → `/generate-docs` → `/configure` → `/constitute` cleanly. Re-running individual commands updates only their outputs.

### Step 8 — Cross-reference updates + status flip

Update `ARCHITECTURE-PIVOT-PLAN.md` §Step 4 → DONE; cross-reference this plan. Update `CLAUDE.md` "Active work" section to remove CONFIGURE-PLAN.md (or mark as completed). Update `DEVELOPMENT-STATUS.md` if it tracks per-command state.

**Verify**: no stale "Step 4 next" references remain in any plan / status doc.

## Open decisions

- **Q11 default-model triple.** Recommended defaults: Think=Opus, Do=Sonnet, Verify=Haiku. Confirm during Step 5 spec authoring; depends on whether the framework should opinion-set or stay neutral.
- **Q12 `runtime-assisted` follow-up depth.** Three follow-ups (URL + API base + CLI command) cover the full ac-verifier integration surface; if one is unused (e.g., backend project has no runtime URL), the helper should accept `N/A` sentinel verbatim. Confirm during Step 5.
- **`PROJECT_TYPE` 13-cat taxonomy.** Inherited from legacy questions.md Q3. Verify the taxonomy is still complete given current project shapes (CLI tool, library/SDK, etc. cover most; check during Step 5 against current ecosystem).
- **`ARCHITECTURES` array vs scalar.** Old yaml had scalar `architecture_shape`; new yaml has `architectures: string_array` to support multi-architecture monorepos (testForge20 is "Clean Architecture" + "Turborepo monorepo"). Confirm during Step 5 — single-architecture projects still work with a 1-element array.
- **AGENT_LIST format.** The old template substitutes `{{AGENT_LIST}}` with a markdown bullet list; new render derived from `.claude/agents/*.md` filenames at substitute-time. Confirm format during Step 4 — bulleted list with one-line role descriptions vs. just filenames.

## When resuming work

**Status as of last save**: design locked 2026-05-10 (this plan). No code shipped. Branch `develop-2.0-init` clean apart from auto-generated `__pycache__` files.

1. Read this plan in full.
2. Read `ARCHITECTURE-PIVOT-PLAN.md` for the broader 4-command sequencing context.
3. Read `docs/v2/ARCHITECTURE.md` for the helper-layer mental model — `configure_helper.py` follows the same `init_helper.py` pattern.
4. Confirm test bed availability: `ls /Users/mykolakudlyk/Projects/testForge20/.devforge/` (init.yaml + index.json present) and `ls /Users/mykolakudlyk/Projects/testForge20/docs/` (overview.md + architecture.md + glossary.md present).
5. Confirm test baseline: `python3 -m unittest discover tests/lib -q` reports all tests OK on `develop-2.0-init`.
6. Execute Steps 0-8 in order. Each step is independently committable.
7. Use the iterative apply-verify loop:
   - Python: `python-engineer` writes function + tests in same turn → `python-reviewer` audits → loop until clean.
   - Spec: `instruction-author` writes → `instruction-reviewer` + `claude-code-guide` audit in parallel → loop until clean.
8. Bulk-confirmation prompt design (Phase 3) must be plain prose echo, NOT AskUserQuestion (per `feedback_askuserquestion_single_line_only.md` memory).
9. Helper-owns-shape extends to template substitution — LLM never edits CLAUDE.md / agent files via the Edit tool inside `/configure` (per `feedback_helper_owns_shape_principle.md` memory).
10. Commit each step independently; don't bundle.

Test data validation: every step verifiable against testForge20 (wrapper + 26-package monorepo edge case). If a step works for testForge20, it works for the easy single-package case by construction.
