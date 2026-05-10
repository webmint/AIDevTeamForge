---
name: configure
description: Populate config + substitute templates from /init-forge state + /generate-docs output
disable-model-invocation: true
---

# /configure — Project Configuration

`/configure` is the third command in the 4-command sequence (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). It consumes the structural fields persisted by `/init-forge` and the docs corpus produced by `/generate-docs`, fills 27 configuration fields via `.devforge/lib/configure_helper` setters, renders the consolidated config, and substitutes `{{KEY}}` placeholders in the framework's templates.

## Outputs of this phase

- `.devforge/configure.yaml` — canonical state (27 fields). Owned + shaped by the helper; mutated only via setter subcommands.
- `.devforge/project-config.json` — render artifact rebuilt from `configure.yaml` + `.devforge/init.yaml` + `.claude/agents/` listing on every run (35 keys: 27 from configure.yaml + 5 from init.yaml + 3 derived).
- `CLAUDE.md` — substituted in place; no `{{KEY}}` markers remain.
- `.claude/agents/*.md` — every file substituted in place; no `{{KEY}}` markers remain.

## Phase 0 — Pre-flight gate

Verify each predecessor artifact exists; abort the run on the first miss.

```bash
test -f .devforge/init.yaml
test -f .devforge/index.json
test -f docs/overview.md
test -f docs/architecture.md
```

- If `.devforge/init.yaml` is missing → ABORT: "missing .devforge/init.yaml — run `/init-forge` first."
- If `.devforge/index.json` is missing → ABORT: "missing .devforge/index.json — run `/init-forge` first (Step 6 builds the index)."
- If `docs/overview.md` is missing → ABORT: "missing docs/overview.md — run `/generate-docs` first."
- If `docs/architecture.md` is missing → ABORT: "missing docs/architecture.md — run `/generate-docs` first."

## Phase 1 — Reset + pull inputs

Reset helper state, then invoke each `read-*` subcommand in order. Every read subcommand emits JSON to stdout; capture each output into a named variable so Phase 2 has all four inputs in memory before composing.

```bash
.devforge/lib/configure_helper reset
```

`reset` writes a fresh defaults yaml at `.devforge/configure.yaml` (every schema field reset to its null/empty default). Idempotent on re-runs.

```bash
.devforge/lib/configure_helper read-init
```

Stdout JSON carries every field in `.devforge/init.yaml`: `project_root`, `workspace_mode`, `project_state`, `default_branch`, `packages_detected[]`. Capture as `INIT_JSON`.

```bash
.devforge/lib/configure_helper read-docs
```

Stdout JSON has two top-level keys: `overview` and `architecture`. Field types vary by section — most are pre-parsed dicts/lists, a few are raw section text strings:

- `overview.purpose` — raw paragraph text (string)
- `overview.tech_stack` — list of `{layer, technology}` row dicts
- `overview.project_structure` — raw section text (string, includes the fenced text-tree)
- `overview.entry_points` — list of `{entry_point, path, purpose}` row dicts
- `overview.key_commands` — list of `{command, description}` row dicts
- `overview.module_map` — nested dict keyed by `infrastructure` / `core` / `domain`, each value a list of row dicts
- `overview.cross_module_dependencies` — raw section text (string)
- `overview.application_routes` — list of `{route, component, description}` row dicts
- `overview.navigation_guards` — list of bullet strings
- `overview.test_files` — list of bullet strings
- `overview.packages` — list of bullet strings
- `architecture.architecture_overview` — raw section text (string)
- `architecture.module_structure` — raw section text (string)
- `architecture.patterns` — list of pattern record dicts (`{name, applies_in, rule, snippet_lang, snippet}`)
- `architecture.conventions` — raw section text (string)
- `architecture.layers` — list of bullet strings
- `architecture.cross_cuts` — list of bullet strings
- `architecture.dependency_direction_rules` — list of bullet strings
- `architecture.dependency_overview` — raw section text (string)

Capture as `DOCS_JSON`. The exact per-field shape is owned by the helper's `_parse_overview_md` + `_parse_architecture_md` functions.

```bash
.devforge/lib/configure_helper read-manifests
```

Stdout JSON has one top-level key `packages[]`. Each entry is `{path, manifest, scripts, dependencies, dev_dependencies, build_tool_hint}`, sourced from `.devforge/index.json` (no fresh disk scan). `build_tool_hint` is `vite` / `webpack` / `rollup` / `next` / `tsc` / `null`, derived from dep names. Capture as `MANIFESTS_JSON`.

```bash
.devforge/lib/configure_helper read-configs
```

Stdout JSON enumerates config files matched against the helper's fixed basename set (`vite.config.{ts,js,mjs}`, `next.config.{ts,js,mjs}`, `nuxt.config.{ts,js}`, `webpack.config.{ts,js}`, `vitest.config.{ts,js}`, `jest.config.{ts,js}`, `.env`, `.env.local`, `.env.development`). Each match carries its file content (capped at 10 KB; `truncated: true` when the cap is hit). Capture as `CONFIGS_JSON`.

If any read subcommand exits non-zero, surface its stderr verbatim and ABORT — Phase 2 cannot compose without all four inputs.

## Phase 2 — Compose detection-derived values

Orchestrator-direct compose (NO Task-tool dispatch to any subagent — same convention as `/generate-docs` Phase 2). The orchestrator (this thread) reads the four Phase 1 JSON outputs inline and synthesizes 22 detection-derived values in memory. Values are NOT yet persisted; Phase 3's bulk confirmation decides what gets written. Composition rules per field:

**Identity**

- `PROJECT_NAME` — root manifest `name` from `MANIFESTS_JSON.packages[]` (the entry whose `path` equals `.` or, for wrapper mode, the entry matching `INIT_JSON.project_root`). Fall back to the basename of `INIT_JSON.project_root` when no root manifest exists.
- `PROJECT_DESCRIPTION` — the Purpose paragraph from `DOCS_JSON.overview` (`docs/overview.md` `## Purpose` section). One concise sentence; trim whitespace.
- `PROJECT_TYPE` — single-label classification from the legacy 13-category taxonomy (web app / web service / CLI tool / library/SDK / desktop app / mobile app / data pipeline / ML model / browser extension / game / framework / static site / monorepo platform). Pick the label that best matches the composed `FRAMEWORKS` + `LANGUAGES` signal.

**Stack**

- `PRIMARY_LANGUAGE` — Tech Stack `Language` row from `DOCS_JSON.overview` (the dominant language across the workspace).
- `LANGUAGES` — comma-separated list across all detected packages, derived per-package from `MANIFESTS_JSON.packages[].manifest` (e.g., `package.json` → JavaScript/TypeScript inferred from `.ts` files in the package, `pyproject.toml` → Python).
- `FRAMEWORKS` — Tech Stack `Framework` row from `DOCS_JSON.overview`, comma-separated.
- `ARCHITECTURES` — comma-separated; extract from `DOCS_JSON.architecture.architecture_overview` (e.g., "Clean Architecture", "Turborepo monorepo").
- `ERROR_HANDLINGS` — comma-separated; extract from `DOCS_JSON.architecture.patterns` + `DOCS_JSON.architecture.conventions` (e.g., "Either monad", "thrown exceptions with global handler").
- `API_LAYERS` — Tech Stack `API Layer` row from `DOCS_JSON.overview`, comma-separated.
- `TESTINGS` — Tech Stack `Testing` row from `DOCS_JSON.overview`, comma-separated.
- `BUILD_TOOLS` — Tech Stack `Build Tool` row from `DOCS_JSON.overview` plus per-package `build_tool_hint` from `MANIFESTS_JSON`, deduplicated, comma-separated.

**Per-package**

- `BUILD_COMMANDS` — comma-separated list aligned per-package; each entry is the package's `scripts.build` from `MANIFESTS_JSON.packages[]`. When a package lacks a `build` script, emit the ecosystem default (`npm run build` for `package.json`, `cargo build` for `Cargo.toml`, etc.).
- `TYPE_CHECK_COMMANDS` — comma-separated; per-package `scripts.typecheck` or `scripts.tsc` from `MANIFESTS_JSON`. When absent, emit `tsc --noEmit` for TypeScript packages, `mypy .` for Python packages, or `N/A` when no type checker applies.
- `LINT_COMMANDS` — comma-separated; per-package `scripts.lint`. When absent, emit `N/A`.
- `PACKAGE_STACKS` — composite per-package record list. Each record is `{path, language, framework, build_tool, build_command, type_check_command, lint_command}`, composed from the same `MANIFESTS_JSON.packages[]` entry plus the framework signal from `DOCS_JSON.overview` Tech Stack. Path values are project-relative (matching `INIT_JSON.packages_detected[].path`).

**Verbatim from docs/**

- `PROJECT_STRUCTURE` — `DOCS_JSON.overview.project_structure` raw section text, verbatim (already a single string from the helper's section extractor; pass to `set-project-structure --text` unchanged).
- `DEV_COMMANDS` — reconstruct a markdown table from `DOCS_JSON.overview.key_commands[]` (parsed list of `{command, description}` row dicts). Emit a header row `| Command | Description |`, an alignment row `|---------|-------------|`, then one body row per entry with the `command` and `description` cells; pass the resulting table text to `set-dev-commands --text`. Empty list → empty string.
- `ARCHITECTURE_DETAILS` — `DOCS_JSON.architecture.architecture_overview` raw section text, verbatim (single string from the section extractor; pass to `set-architecture-details --text` unchanged).

**AC runtime (best-effort detection)**

- `AC_RUNTIME_URL` — extract from matched configs in `CONFIGS_JSON` (e.g., `vite.config.*` `server.host` + `server.port`; `next.config.*` `server.port`; `webpack.config.*` `devServer.host` + `devServer.port`). Compose `http://<host>:<port>`. Empty string when no config exposes a dev-server binding.
- `AC_RUNTIME_API_BASE` — extract from `.env*` matches in `CONFIGS_JSON` (`VITE_API_URL` / `NEXT_PUBLIC_API_URL` / `REACT_APP_API_URL`). Empty string when none present.
- `AC_RUNTIME_CLI_COMMAND` — manifest `scripts.dev` or `scripts.start` from `MANIFESTS_JSON` (root or workspace-root package). Empty string when neither script exists.

## Phase 3 — Bulk-confirmation prompt

Plain prose echo, NOT AskUserQuestion (multi-line content cannot fit AskUserQuestion's single-line question text constraint). Display all 22 detection-derived values from Phase 2 in a fenced block, grouped by category, then ask the user to confirm or override.

**Stop discipline (mandatory).** After emitting the echo block below, this phase MUST end the assistant turn and wait for the user's reply. Do NOT advance to Phase 4 setters in the same turn. Do NOT call any `set-*` subcommand in the same turn. Do NOT call any tool after the echo — the echo is the final output of the turn. The user replies organically; the next turn begins with their reply, which is parsed per the rules below. Plain-prose prompts have no harness-level "wait for user" affordance, so the LLM-level stop is the only mechanism preventing accidental auto-advance through the bulk confirmation.

Echo template (substitute `<...>` with the Phase 2 composed values):

````
Here's what /init-forge + /generate-docs found and what /configure proposes:

Project:
- name: <PROJECT_NAME>
- description: <PROJECT_DESCRIPTION>
- type: <PROJECT_TYPE>

Stack:
- primary_language: <PRIMARY_LANGUAGE>
- languages: <LANGUAGES>
- frameworks: <FRAMEWORKS>
- architectures: <ARCHITECTURES>
- error_handlings: <ERROR_HANDLINGS>
- api_layers: <API_LAYERS>
- testings: <TESTINGS>
- build_tools: <BUILD_TOOLS>

Per-package commands:
- build_commands: <BUILD_COMMANDS>
- type_check_commands: <TYPE_CHECK_COMMANDS>
- lint_commands: <LINT_COMMANDS>
- package_stacks: <count> packages — <list path entries>

Verbatim from docs/:
- project_structure: (<N> lines from docs/overview.md ## Project Structure)
- dev_commands: (<N> lines from docs/overview.md ## Key Commands)
- architecture_details: (<N> lines from docs/architecture.md ## Architecture Overview)

AC runtime (detected):
- ac_runtime_url: <AC_RUNTIME_URL>
- ac_runtime_api_base: <AC_RUNTIME_API_BASE>
- ac_runtime_cli_command: <AC_RUNTIME_CLI_COMMAND>

Reply 'yes' to confirm all, or list overrides one per line as 'field: value' (e.g., 'project_type: CLI tool').
````

For the three verbatim fields (`project_structure`, `dev_commands`, `architecture_details`), echo the line count instead of inlining the full text — they are large blocks already visible in `docs/overview.md` + `docs/architecture.md`. The user can override by re-typing the field followed by the replacement text on the same line; multi-line overrides for these three fields are rare in practice.

### Parsing the user reply

- Reply equals `yes` (case-insensitive, exact after strip) → apply all 22 Phase 2 values via setters.
- Reply equals `cancel` (case-insensitive, exact after strip) → ABORT cleanly: "Run `/configure` again when you're ready to review the detected values." Leave `configure.yaml` in its post-`reset` defaults state. Do not advance to Phase 4.
- Otherwise → parse line-by-line as `<field>: <value>`. Field names are case-insensitive; tolerate either dashed (`project-name`) or underscore-separated (`project_name`) keys. Apply the user's override for matched lines; apply the Phase 2 composed value for every other field.
- Reply not parsable as any of the above (no `yes`, no `cancel`, no `field: value` lines) → re-prompt: "I couldn't parse your reply. Reply 'yes' to confirm all, 'cancel' to abort, or list overrides one per line in 'field_name: value' format." Allow up to 2 retries (3 total attempts). After the third invalid reply, fall back to applying all Phase 2 values as confirmed and warn the user: "Proceeding with detected values; re-run `/configure` to revise."

### Setter mapping

Apply each accepted/overridden value via the matching setter. Setter argument shape is taken verbatim from the helper's argparse:

| Field | Setter |
|---|---|
| `project_name` | `set-project-name <value>` |
| `project_description` | `set-project-description <value>` |
| `project_type` | `set-project-type <value>` |
| `primary_language` | `set-primary-language <value>` |
| `languages` | `set-languages <comma-sep-list>` |
| `frameworks` | `set-frameworks <comma-sep-list>` |
| `architectures` | `set-architectures <comma-sep-list>` |
| `error_handlings` | `set-error-handlings <comma-sep-list>` |
| `api_layers` | `set-api-layers <comma-sep-list>` |
| `testings` | `set-testings <comma-sep-list>` |
| `build_tools` | `set-build-tools <comma-sep-list>` |
| `build_commands` | `set-build-commands <comma-sep-list>` |
| `type_check_commands` | `set-type-check-commands <comma-sep-list>` |
| `lint_commands` | `set-lint-commands <comma-sep-list>` |
| `project_structure` | `set-project-structure --text <verbatim>` |
| `dev_commands` | `set-dev-commands --text <verbatim>` |
| `architecture_details` | `set-architecture-details --text <verbatim>` |
| `ac_runtime_url` | `set-ac-runtime-url <value>` |
| `ac_runtime_api_base` | `set-ac-runtime-api-base <value>` |
| `ac_runtime_cli_command` | `set-ac-runtime-cli-command <value>` |

For `package_stacks`: invoke `add-package-stack` once per package record from Phase 2's composed list:

```bash
.devforge/lib/configure_helper add-package-stack \
    --path <p> --language <l> \
    [--framework <f>] [--build-tool <b>] \
    [--build-command <bc>] [--type-check-command <tc>] [--lint-command <lc>]
```

`--path` and `--language` are required; the other five flags are optional and only included when the Phase 2 record carries a non-null value for that subfield.

If any setter exits non-zero, capture its stderr, fix the input value, and retry the same setter (cap at 3 retries per field). On the 4th failure, surface the failure to the user and ABORT — `configure.yaml` is left in a partial state and the user must re-run `/configure`.

## Phase 4 — Sequential user-only prompts

These five fields cannot be derived from filesystem scan; each requires a user choice. One AskUserQuestion per question, in order. Persist each answer via its setter before issuing the next question.

### Q9: Workflow Enforcement

Use AskUserQuestion: "How strict should workflow enforcement be?"
- `Strict` (Recommended) — every step requires explicit approval; no shortcuts
- `Moderate` — approval gates at major milestones; smaller decisions auto-proceed
- `Light` — minimal gating; rely on conventions over enforcement

Save via `.devforge/lib/configure_helper set-workflow-enforcement <choice>`.

### Q10: AI Attribution

Use AskUserQuestion: "Add AI attribution footer to commit messages?"
- `Yes` (Recommended) — commits include `Generated with Claude Code` footer
- `No` — commit messages stay clean of attribution

Save via `.devforge/lib/configure_helper set-ai-attribution <choice>`.

### Q11: Claude Tier Models

Three sequential AskUserQuestion calls — Q11.1 (think), Q11.2 (do), Q11.3 (verify). See `references/q11-tiers.md` for the full prompt text, options, and recommended-defaults rationale per tier.

### Q12: AC Verification Mode

Use AskUserQuestion to pick the mode, then conditionally ask the runtime triple. See `references/q12-ac.md` for the full prompt text, the four mode options, and the conditional Q12.1 / Q12.2 / Q12.3 follow-up logic that runs only when the user selects `runtime-assisted`.

## Phase 5 — Render + substitute

Once `configure.yaml` is fully populated (27 fields set), render the consolidated JSON config and substitute the templates.

```bash
.devforge/lib/configure_helper render-config
```

`render-config` reads `.devforge/configure.yaml` + `.devforge/init.yaml`, derives `AGENT_LIST` from `.claude/agents/*.md` filenames, and writes `.devforge/project-config.json` atomically. Exit codes:

- Exit 0 → success.
- Exit 1 → `.devforge/init.yaml` missing or unreadable, OR `.devforge/configure.yaml` unreadable, OR write to `project-config.json` failed. Surface stderr verbatim and ABORT.

```bash
.devforge/lib/configure_helper substitute-templates
```

`substitute-templates` reads `.devforge/project-config.json` + `.devforge/init.yaml`, walks `CLAUDE.md` + every `.claude/agents/*.md` file, and replaces every `{{KEY}}` placeholder atomically per file. Exit codes:

- Exit 0 → every template substituted; no `{{KEY}}` markers remain.
- Exit 1 → `project-config.json` missing or malformed, OR `CLAUDE.md` missing, OR a per-file write failed. Surface stderr verbatim and ABORT. (Note: `.devforge/init.yaml` missing is NOT an exit-1 condition for this subcommand — substitute-templates falls back to empty `packages_detected` when init.yaml is absent. The init.yaml dependency is enforced earlier by Phase 0's pre-flight gate and by `render-config` exit 1.)
- Exit 2 → at least one template contained a placeholder the helper cannot resolve. Stderr enumerates the unknown placeholders per file. Failed files are NOT modified (atomic per-file). Surface stderr verbatim and ABORT — the project state is partial; the user must extend the substitution map (helper-side) before re-running.

## Phase 6 — Verify + report

```bash
.devforge/lib/configure_helper verify
```

`verify` cross-checks `.devforge/configure.yaml` + `.devforge/project-config.json`: every required field populated; AC runtime fields exempt unless `ac_verification_mode == runtime-assisted`; round-trip identity between the two files. Exit 0 = pass; exit 2 = at least one violation (each enumerated on stderr). On exit 2, surface stderr verbatim and ABORT — the user must address the violations before `/constitute`.

Scope note: `verify` does NOT re-scan `CLAUDE.md` or `.claude/agents/*.md` for remaining `{{KEY}}` markers. Template-substitution completeness is enforced by Phase 5's `substitute-templates` exit 0; if Phase 5 succeeded, the templates are clean. If you re-run only `verify` standalone after a partial Phase 5 (e.g., aborted mid-substitution), it will not re-detect template markers — re-run `substitute-templates` to re-establish that guarantee.

```bash
.devforge/lib/configure_helper summary
```

`summary` is read-only; it prints a deterministic field-by-field report to stdout. After the helper runs, copy its stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase).

## Closing

`/configure` is complete. The 27 configuration fields are persisted in `.devforge/configure.yaml`; `.devforge/project-config.json` carries all 35 keys; `CLAUDE.md` and every file under `.claude/agents/` is fully substituted. Tell the user: "Run `/constitute` next."
