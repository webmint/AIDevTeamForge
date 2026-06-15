# Forge 2.0 — Architecture of `/init-forge`, `/generate-docs`, `/configure`, `/constitute`

Contributor / future-me reference. Architecture-only: helper layout, schemas, data flow, state shape, hook integration. Command UX (steps, prompts, retry budgets) lives in the authoritative specs:

- `src/commands/init-forge/main.md` — `/init-forge` step contract
- `src/commands/generate-docs/main.md` — `/generate-docs` phase contract
- `src/commands/configure/main.md` — `/configure` phase contract
- `src/commands/constitute/main.md` — `/constitute` phase contract

This file does not duplicate those. It explains what sits **behind** the commands: the Python helpers, the on-disk artifacts, the inter-helper data flow, and the runtime hooks that police LLM behavior. When the spec and this file disagree about user-facing behavior, the spec wins; when they disagree about helper internals, this file wins.

Version: develop-2.0-init branch, post-2026-05-11. All four pivot commands shipped (`/init-forge` + `/generate-docs` + `/configure` + `/constitute`); ARCHITECTURE-PIVOT-PLAN.md retired.

---

## 1. Conceptual model

The three shipped commands sit at the head of the 4-command pivot (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). They share five design principles:

1. **Helper-owns-shape, LLM-owns-values.** Every artifact (`init.yaml`, `index.json`, `docs/<...>/index.md`, `docs/glossary.md`, `configure.yaml`, `project-config.json`, substituted `CLAUDE.md` + `.claude/agents/*.md`) is rendered by a Python helper. The orchestrator (the LLM thread executing the slash command) never writes structural content directly via the `Write` tool to those paths. It composes values, passes them to setters, and the helper produces the canonical bytes. This includes template substitution (`/configure substitute-templates`) and agent pruning (`/configure prune-agents`) — neither is done via the `Edit` tool against `.claude/agents/*.md`. This is the only way to make idempotent re-runs and downstream parsers reliable.
2. **State IS the on-disk file.** Each setter does a read-modify-write cycle with `tempfile.mkstemp` + `os.replace` for atomicity. There is no in-memory "current state" object held across invocations; the file is the source of truth. For `/generate-docs`'s skeleton-fill flow, the skeleton file (`*.md.skeleton`) IS the state — no sidecar JSON. `/configure`'s `_state.py`-style transaction (`_state_transaction` context manager around `fcntl.LOCK_EX` on `configure.yaml.lock`) serializes concurrent setters; the primary path `set-package-stacks` replaces the whole record list in one atomic write, while the historical/recovery path `add-package-stack` array-appends one record per call and two parallel appends could lose entries without the lock (lock pattern lifted from `_generate_docs/_state.py`'s prior fix).
3. **Mechanical first, LLM second.** Anything that can be derived without judgment (file walks, manifest parsing, dep extraction, source-stamp hashing, ASCII tree rendering, build-tool / framework detection) is helper work. The LLM is invoked only for prose synthesis (`Purpose` paragraphs, leaf annotations, glossary definitions, cross-cut rationale, classification calls like PROJECT_TYPE). The helper layer pre-extracts mechanical fields via `*-input` / `read-*` subcommands so the LLM never reads raw source if a helper can extract first. `/configure` extends this with `_derive_build_tool_hint` + `_derive_framework_hint` (per-package, dependency-name match against locked tables).
4. **Bottom-up tier walk.** `/generate-docs` always proceeds concern → package → project, so each upper tier has rendered child docs to synthesize from. The pipeline gates on per-tier `source_stamp`: if upstream input hashes are unchanged, the tier skips dispatch. Stamps are SHA-256 prefixes (16 chars) over canonicalized input.
5. **Atomic taxonomy + helper-side enforcement.** `/configure` uses atomic project-nature labels (`web` / `backend` / `mobile` / etc.) — no synthetic meta-labels like "fullstack". A monorepo with both web and backend packages declares `project_natures: ["web", "backend"]`; the agent-pruning gate matches via set intersection (`agent.applies_to ∩ project.natures`), keeping agents that fit either nature. Project rules (state-management / styling conventions) live in `constitution.md` (per `/constitute` pipeline), NOT in template-substitution placeholders — keeps the substitution layer free of concerns it can't own.

---

## 2. `/init-forge` — bootstrap

`/init-forge` captures five structural fields about the target project, persists them, then materializes a structural index for downstream consumers. No classification, no inference, no language detection at this stage.

### 2.1 Helpers

Two Python helpers, both stdlib-only, both POSIX-launcher-wrapped at `src/devforge/lib/<name>` (shell shim) calling `<name>.py`.

#### `init_helper.py`

Owns `.devforge/init.yaml`. The launcher invokes `python3 init_helper.py <subcmd>`.

Subcommand surface:

| Subcommand | Mutation |
|---|---|
| `reset` | Write fresh defaults yaml (every field null/`[]`) |
| `set-workspace-mode <standalone\|wrapper>` | Set scalar field |
| `set-project-root <path>` | Set scalar field (`.` for standalone) |
| `set-project-state <empty\|brownfield>` | Set scalar field |
| `set-default-branch <name>` | Set scalar field |
| `find-nested-git` | Depth-1 scan for `<dir>/.git/`; returns candidate list (read-only) |
| `add-package --path <p> --manifest <m>` | Append package record |
| `summary` | Render human-readable report to stdout |

Schema (locked field order, used by the YAML emitter):

```python
FIELD_SCHEMA = (
    ("workspace_mode", "scalar"),        # standalone | wrapper
    ("project_root", "scalar"),          # "." or relative folder name
    ("project_state", "scalar"),         # empty | brownfield
    ("default_branch", "scalar"),        # main, master, etc.
    ("packages_detected", "package_record_array"),
)
ENUM_FIELDS = {
    "workspace_mode": {"standalone", "wrapper"},
    "project_state":  {"empty", "brownfield"},
}
```

Each scalar defaults to `None`; the array defaults to `[]`. Loud-fail downstream when a required field is `None` is the design — no "sensible default" overrides. `reset` writes a defaults file; it never deletes. `NESTED_GIT_SKIP` (hidden directories + standard build/dependency dirs) is a fixed set used by `find-nested-git`.

#### `index_helper.py`

Owns `.devforge/index.json` + `<install_root>/docs/structure.md`. Single subcommand:

| Subcommand | Mutation |
|---|---|
| `build-index` | Walk packages from `init.yaml`; write both artifacts atomically |

For each package in `init.yaml.packages_detected`:
- Walk source tree (capped at 500 files; `files_truncated: true` flag set on overflow).
- Skip dirs: `_FILE_WALK_SKIP_DIRS` (`node_modules`, `dist`, `build`, `target`, `out`, `.git`, `__pycache__`, `.venv`, `venv`, `.idea`, `.vscode`, `.next`, `.nuxt`, `.turbo`, `bin`, `obj`) plus any dot-prefixed directory.
- Read manifest by filename match against `_MANIFEST_REGISTRY`. Extract scripts + dependencies. Malformed manifest → `manifest_parse_skipped: true`, stderr warning, continue (not a hard failure).

Both writes are atomic. Re-running is idempotent: byte-identical output across re-runs on stable input (modulo `generated_at` timestamp).

**Wrapper-mode quirk.** `structure.md` lives at `<install_root>/docs/structure.md` (alongside `.devforge/`), NOT inside `project_root`. In wrapper mode the install root and source root differ; per the wrapper-mode artifact convention all framework outputs stay at install root.

**Per-language source extraction is an explicit non-goal.** No exports, no type extraction, no import graph. The cost of building per-language extractors that stay correct across the long tail of edge cases is not worth what the LLM already provides. CBM (codebase-memory-mcp) is the structural query layer for code; `index.json` is structural metadata only.

### 2.2 Outputs

```
.devforge/
  init.yaml          # 5 scalar fields + packages_detected[]
  index.json         # per-package structural data (file lists, scripts, deps)
docs/
  structure.md       # human-readable workspace map (rendered from index.json)
```

`init.yaml` field order is fixed (FIELD_SCHEMA walks the list); diff stability is part of the contract. `index.json` is versioned (`INDEX_VERSION = 1`). `structure.md` is render-only — never the source of truth.

### 2.3 Step → helper mapping

The spec's six numbered steps map onto helper subcommands:

| Spec step | Helper invocation(s) |
|---|---|
| Preflight | `init_helper reset` |
| 1. Workspace mode | `find-nested-git` (read-only scan) → `set-workspace-mode` + `set-project-root` |
| 2. Project state | (LLM ls + classify) → `set-project-state` |
| 3. Default branch | (LLM git probes) → `set-default-branch` |
| 4. Discover packages | (LLM walk + manifest match) → `add-package` (per package) |
| 5. Render summary | `summary` (helper renders, LLM relays verbatim) |
| 6. Build index | `index_helper build-index` |

Steps 1-5 mutate `init.yaml`. Step 6 produces the structural artifacts that `/generate-docs` consumes.

---

## 3. `/generate-docs` — bottom-up doc materialization

`/generate-docs` produces the project's `docs/` knowledge base. Bottom-up across three tiers (concern → package → project), gated by per-tier `source_stamp`. Orchestrator-direct compose; no Task-tool dispatch to subagents for content.

### 3.1 Helper architecture

A single user-facing entry point — `src/devforge/lib/generate_docs_helper` (shell shim) → `generate_docs_helper.py` (thin re-export shim) → `_generate_docs/` package. The package was split out of a 1144-line monolith; the shim exists so legacy `import generate_docs_helper` and stable POSIX-launcher paths keep working.

Submodule layout:

| Module | Role |
|---|---|
| `_cli.py` | Controller. Argparse + dispatch via `_SUBCOMMANDS` registry (~53 subcmds across all tiers + legacy setters). One handler per subcmd. |
| `_state.py` | Atomic JSON state I/O for legacy setters. POSIX flock around read-modify-write to prevent concurrent-setter loss. Provides `_die`/`_info` stderr printers shared across submodules. |
| `_trace.py` | Per-invocation trace log at `.devforge/.generate-docs-trace.log`. Every subcmd appends one line: `<timestamp> subcommand=<name> exit=<code>`. |
| `_circuit.py` | Helper-side circuit breaker. Reads trace log; refuses to proceed on doom-loop (3 consecutive identical exit-2s) or invocation-budget exceeded (default 500). Hooks into `_cli.main()` AFTER argparse, BEFORE handler dispatch. Reset boundary is the most-recent `subcommand=reset` entry. |
| `_preflight.py` | F.0 — orchestration of vue-extract + CBM `index_repository` + per-concern source-stamp diff. Emits JSON the orchestrator gates Phase 2 on. Writes `.devforge/.preflight-stamp` (wall-time of last successful run). |
| `_concern_input.py` | F.2 — concern-tier batch JSON. Walks `<pkg>/src/<concern>/` filesystem-direct (NOT via `index.json`, which caps at 500 files and may truncate large concerns). Emits ASCII tree + `comment_rich_span` per file. Switches to split-batch shape when concern crosses threshold AND has ≥2 immediate child dirs. |
| `_package_input.py` | F.7 — package-tier batch JSON. Reads each rendered concern doc's frontmatter + Purpose paragraph; collects package-root files (README, CHANGELOG, package.json). Emits `concern_seeds[]` + `package_root_files[]` + `source_stamp`. |
| `_project_input.py` | F.8 — project-tier batch JSON. Reads each rendered package overview's frontmatter + Purpose paragraph; collects project-root files. Adds Phase 1 mechanical fields (`tech_stack_candidates[]`, `key_commands[]`, `test_file_paths[]`, `cross_module_deps_tree`, `project_structure_tree`) and Phase 2 candidate fields (`entry_point_candidates[]`, `router_route_files[]`, `nav_guard_files[]`, `package_classification_hints`). Wrapper-mode aware. |
| `_doc_setters.py` | F.4 — multi-tier skeleton-fill primitives. `init-doc` writes `*.md.skeleton` for the requested tier; per-section setters edit in-place; `render-doc` atomic-renames to `*.md`. The skeleton file IS the state. |
| `_doc_corpus.py` | Shared corpus-extraction substrate. `walk_doc_corpus`, `extract_term_occurrences`, `validate_cite_paths`, `get_section_body_span`, `noise_filter`. Used by `_glossary` and `_validate_doc`. |
| `_glossary.py` | Phase B — glossary helper. `build-glossary-bundles` (CBM-augmented term ranking, emits JSON) + `set-glossary-entries` (consumes LLM-composed entries, validates, renders `docs/glossary.md`). |
| `_md_frontmatter.py` | Stdlib YAML-subset parser/writer for `*.md` frontmatter. Locked schema rules: `---` open on line 1; close within 100 lines; duplicate keys rejected; quoted strings unescape `\"`/`\\`; ints unquoted; newlines in values rejected at render time. |
| `_validate_doc.py` | F.5 — multi-tier validate-doc. Walks rendered doc; checks frontmatter required keys, section anchors, no banned phrases, bullet-cap, structure annotations cap. Exit 0 = pass; exit 2 = violation (stderr enumerates errors → orchestrator captures as compose feedback). |
| `_validators.py` | Re-export shim for the validator surface (post-2026-05-07 cleanup). New code patches `_validators_concern` / `_validators_package` directly. |
| `_validators_concern.py` / `_validators_package.py` / `_validators_shared.py` / `_validators_decomposition.py` / `_validators_file_doc.py` | Tier-specific validators. Concern + package validators are render-coupled (share `render_*_skeleton` references). File-doc validator handles per-source-file `.md` (Validator-Loop Part B). |
| `_setters.py` / `_setters_concern.py` | Legacy package/concern state-mutation setters (the spec's "FORBIDDEN under /generate-docs" list). Kept for tests + backwards-compatible imports; not invoked from the helper-chain spec. |
| `_setters_concern_files.py` | Per-source-file `.md` skeleton + `write-file-doc` / `validate-file-doc` (Validator-Loop Part B). Filesystem-forcing-function for per-leaf doc coverage. |
| `_render.py` | PackageDoc render (legacy tier). `render-package-skeleton` / `render-package-doc`. Render-package-doc gated by `_validators_package.validate_package`. |
| `_manifest.py` | `extract-package-scripts` — parse `package.json`'s `scripts` block. |
| `_snippet.py` | `extract-snippet` — read `<file>:<start>-<end>` line range from disk. Used by orchestrator when composing CBM cite-back blocks. |
| `_sourcemap.py` | Vue cite-back through-sourcemap support (deferred; not yet wired into validate-doc). |
| `_status.py` | `status` — read-only state inspection for the legacy state file. |
| `_banned_phrases.py` | Shared banned-phrase list (`this document`, `in this section`, `various`, `several`, `many`, `some`, `other`). Validators reject prose containing any. |

### 3.2 Subcommand registry

`_cli.py` exposes every subcommand via the `_SUBCOMMANDS` tuple. The tuple is the closed-against-modification dispatch table; adding a new subcommand means adding a parser-factory + handler in the appropriate sibling module and one line in this tuple. The dispatch path stays OCP-clean.

The currently active subcommands fall into six groups:

1. **State plumbing** — `reset`, `status`, `extract-package-scripts`, `extract-snippet`.
2. **Legacy package/concern setters** (`_setters` / `_setters_concern`; spec's FORBIDDEN list) — `add-package`, `set-package-*`, `add-package-*`, `add-concern`, `set-concern-*`, `add-concern-*`, `render-package-skeleton`, `render-package-doc`, `validate-package`, `render-concern-skeleton`, `render-concern-doc`, `validate-concern`. Kept for compatibility; current pipeline does not invoke them.
3. **Per-file-doc** (`_setters_concern_files` / `_validators_file_doc`) — `render-file-skeletons`, `write-file-doc`, `validate-file-doc`, `verify-file-docs`. Validator-Loop Part B.
4. **Tier inputs** — `concern-input`, `package-input`, `project-input`, `preflight`.
5. **Skeleton-fill primitives** (`_doc_setters`) — `init-doc`, `set-doc-purpose`, `set-doc-structure`, `set-doc-concerns`, `set-doc-files`, `set-doc-layers`, `set-doc-patterns`, `set-doc-packages`, `set-doc-cross-cuts`, `set-doc-subconcerns`, `render-doc`, `validate-doc`.
6. **Project-tier setters** (Track 4 Phase 1-3) — `set-overview-tech-stack`, `set-overview-key-commands`, `set-overview-test-files`, `set-overview-cross-module-deps`, `set-overview-project-structure-tree`, `set-overview-entry-points`, `set-overview-application-routes`, `set-overview-navigation-guards`, `set-overview-module-map`, `set-overview-project-structure-annotations`, `set-architecture-overview-narrative`, `set-architecture-module-structure`, `set-architecture-patterns`, `set-architecture-conventions`, `set-architecture-cross-cuts-detailed`, `set-architecture-dependency-direction-rules`, `set-architecture-dependency-overview-mermaid`.
7. **Glossary** — `build-glossary-bundles`, `set-glossary-entries`.

The mandatory chain for concern-tier authoring is:

```
init-doc → set-doc-purpose → set-doc-structure → render-doc → validate-doc
```

Group 2 (legacy setters) emit a different shape and are out of scope under `/generate-docs`. Group 4-7 own the current pipeline.

### 3.3 Phase flow

```
Phase 0 — Pre-flight gate         (test -f index.json; require codebase-memory-mcp on PATH)
Phase 1 — preflight subcmd        (vue-extract + CBM index_repository + per-concern stamps)
Phase 2 — concern tier loop       (changed/new only; single-batch or split-batch path)
Phase 3 — package tier loop       (overview + architecture per package)
Phase 4 — project tier loop       (overview + architecture; project-input mechanical fields)
Phase B — glossary                (build-glossary-bundles → orchestrator compose → set-glossary-entries)
Phase 5 — verify                  (re-run validate-doc per rendered doc; defensive)
Phase 6 — report                  (counts + failures)
```

The retry budget is 3 per doc (Phase 2.5, 3.2, 3.3, 4.2, 4.3, B.4); on the 4th failure the orchestrator surfaces the failure and continues with the next unit. Children are not regenerated by parent retries.

### 3.4 Stamp gate

Every tier carries a `source_stamp` field — a SHA-256 prefix (16 chars) over canonicalized input. The orchestrator skips dispatch when the prior rendered doc's frontmatter `source_stamp` matches the new computed stamp from the corresponding `*-input` helper.

- **Concern tier**: `_preflight.py` computes per-concern stamps over the source files in the concern's subfolder; emits `concerns[*].status` ∈ `{unchanged, changed, new, empty}`. Phase 2 dispatches only `changed | new`.
- **Package tier**: orchestrator inline-computes per-package stamps from `package-input` output and compares to prior overview/architecture frontmatter. Skip iff every concern was `unchanged` AND prior overview + architecture stamps match.
- **Project tier**: same pattern with `project-input`'s `source_stamp`.
- **Glossary**: regenerated unconditionally when Phase B runs (cheap relative to dispatch cost).

The stamp is a presence-only mechanism — it tells you "input bytes changed" but not "what changed". Validators run regardless; the stamp gate only saves dispatch cost.

### 3.5 Split-batch path

When a concern's file count crosses the split threshold AND it has ≥2 immediate child directories, `concern-input` emits `split: true` and:

- `parent_meta.tree_text` (full ASCII tree)
- `parent_meta.subconcern_names[]` (immediate child dirs)
- `parent_meta.loose_files[]` (files at concern root not in any child)
- `sub_concerns[]` — one self-sufficient batch per child, each shaped like a single-batch entry

The orchestrator iterates `sub_concerns[]` directly (NOT `subconcern_names`) — children with empty file lists after trivial-leaf filtering are dropped, so `sub_concerns[]` may be shorter. Each child renders to `docs/<pkg>/<concern>/<sub_name>/index.md` via Steps 2.2-2.5. After all children pass, a parent-aggregator pass renders `docs/<pkg>/<concern>/index.md` with `## Purpose` + `## Sub-concerns` (no `## Structure`) using `init-doc --split` + `set-doc-subconcerns`.

`validate-doc --tier concern --split` enforces parent-shape: Purpose + Sub-concerns required, Structure forbidden, each Sub-concerns bullet matches `- <name> — <summary> ([→](<doc_path>))`, each `doc_path` resolves to a rendered child.

### 3.6 Orchestrator-direct compose

Phase 2's `set-doc-purpose` + `set-doc-structure` compose step is **orchestrator-direct** — the main `/generate-docs` thread reads the `concern-input` JSON inline and emits Purpose + per-leaf annotations itself. NO Task-tool dispatch to a compose subagent.

Why: subagent dispatch costs 30-90K tokens per concern (full system prompt + redundant source reads inside the subagent). Orchestrator-direct is 3-10× cheaper because session context is already loaded; the concern's batch JSON inlines (~3-5K tokens) and structured output emits (~2-4K tokens). The forbidden-actions list in the spec (Write tool, custom Python emitting markdown, legacy concern setters) closes the escape hatches.

### 3.7 Legacy schema (`generate_docs_schema.py`)

A separate `src/devforge/lib/generate_docs_schema.py` defines a dataclass schema (`PackageDoc`, `ConcernDoc`, `ArchitectureDoc`, `Export`, `Dependency`, `Hazard`, `Pattern`, `Layer`, `DepEdge`, `Decision`, `MemoryFinding`, `SourceCite`, `CodeBlock`) with closed-enum tuples (`EXPORT_KINDS`, `DEPENDENCY_KINDS`, `HAZARD_CATEGORIES`, `ANNOTATION_CONFIDENCE_VALUES`). It's pure records — no serialization, no rendering, no I/O. Per-record validation runs in `__post_init__` (non-empty strings, enum membership, line-range invariants).

This schema feeds the **legacy** package/concern setters in Group 2 (rendered by `_render.py`). The current Plan F pipeline (Group 4-7) does not round-trip through these dataclasses — its state is the `*.md.skeleton` file. The schema stays for backwards-compat tests + because some validators in `_validators_package` still construct records during validation.

### 3.8 State + outputs

```
.devforge/
  init.yaml                          # /init-forge — bootstrap state
  index.json                         # /init-forge — structural index
  .preflight-stamp                   # last-successful preflight wall-time
  .generate-docs-state.json          # legacy setter state (file-locked)
  .generate-docs-trace.log           # circuit-breaker signal source
  cbm-usage.log                      # CBM-adoption telemetry (hook output)
  vue-tmp/                           # vue-extract scratch (idempotent regen)
docs/
  structure.md                       # /init-forge — workspace map
  overview.md                        # project-tier overview
  architecture.md                    # project-tier architecture
  glossary.md                        # Phase B — CBM-classified terms
  <package>/
    overview.md                      # package-tier overview
    architecture.md                  # package-tier architecture
    <concern>/
      index.md                       # concern-tier (Purpose + Structure)
      <sub_concern>/
        index.md                     # split-batch child
```

The `*.md.skeleton` files are transient — `init-doc` writes them, setters edit them, `render-doc` atomic-renames to `*.md`. A skeleton present after `/generate-docs` exits indicates an incomplete tier (one of the setters or render-doc failed).

---

## 4. `/configure` — populate config + substitute templates + prune agents

`/configure` consumes the artifacts emitted by `/init-forge` + `/generate-docs`, fills 29 configuration fields, renders `.devforge/project-config.json` (37-key substitution map), prunes non-applicable agent files based on the project's natures, and substitutes `{{KEY}}` placeholders across `CLAUDE.md` + the surviving `.claude/agents/*.md` files. Single helper module + single command spec.

### 4.1 Helper architecture

One file: `src/devforge/lib/configure_helper.py` (no submodule split — fits in a single module). Single shell launcher at `src/devforge/lib/configure_helper`. Stdlib only, Python 3.8+.

Subcommand surface (~32 subcommands grouped by role):

| Group | Subcommands | Role |
|---|---|---|
| State plumbing | `reset` | Write fresh defaults yaml |
| Read-* inputs | `read-init` / `read-docs` / `read-manifests` / `read-configs` | Capture Phase 1 inputs as JSON |
| Identity setters (3) | `set-project-name` / `set-project-description` / `set-project-type` | Scalar fields |
| Stack setters (8) | `set-primary-language` / `set-languages` / `set-frameworks` / `set-architectures` / `set-project-natures` / `set-error-handlings` / `set-api-layers` / `set-testings` | Scalar + string-array |
| Per-pkg arrays (5) | `set-build-tools` / `set-build-commands` / `set-type-check-commands` / `set-lint-commands` / `set-test-commands` | string-array |
| Per-pkg record | `set-package-stacks` (primary) / `add-package-stack` (recovery) | `set-package-stacks` replaces the record list from bulk stdin (8-subfield); `add-package-stack` record-append retained for recovery |
| Verbatim docs (3) | `set-project-structure --text` / `set-dev-commands --text` / `set-architecture-details --text` | Multi-line scalar |
| User prefs (5) | `set-workflow-enforcement` / `set-ai-attribution` / `set-claude-tier-think` / `-do` / `-verify` | Scalar (Q11 tiers are non-enum to allow custom model aliases) |
| AC verification (4) | `set-ac-verification-mode` / `set-ac-runtime-url` / `set-ac-runtime-api-base` / `set-ac-runtime-cli-command` | Scalar |
| Render | `render-config` | Atomic JSON write of project-config.json (37 keys) |
| Prune | `prune-agents [--apply]` | Walk agents/, delete mismatches (or dry-run JSON) |
| Substitute | `substitute-templates` | `{{KEY}}` replacement across CLAUDE.md + agents |
| Verify | `verify` | Required-field + round-trip identity check |
| Summary | `summary` | Verbatim-echo report (mirrors `init_helper summary`) |

Schema: `FIELD_SCHEMA` carries 29 fields (locked order; emit walks list for diff stability). Three field kinds: `scalar`, `string_array`, `package_stack_array` (the only record kind; 8 fixed subfields). `ENUM_FIELDS` carries 3 entries (`workflow_enforcement` / `ai_attribution` / `ac_verification_mode`); `claude_tier_*` deliberately NOT in ENUM_FIELDS — accepts free-text scalars so users can name custom Claude routes via the Q11 `Other` branch.

Validation helpers (private):
- `_validate_scalar` — non-empty after strip
- `_validate_enum` — case-insensitive match → returns canonical (lowercase `strict` → `Strict`)
- `_validate_string_array` — accepts JSON-array form `["a", "b,c"]` (decoded via `json.loads` when input strips to start with `[` and end with `]`) OR comma-separated form `"a, b"` (legacy default; backward compatible)
- `_validate_path_value` — non-empty, no newlines
- `_validate_verbatim` — non-empty, no inner stripping (preserves multi-line content for verbatim doc fields)

Setters route through `_state_transaction(devforge_dir)` — context manager that acquires `fcntl.LOCK_EX` on `<configure.yaml>.lock`, loads state, yields to mutation, dumps state, releases lock. Single read-modify-write codepath; no setter calls `_load`/`_dump` directly. `_HAVE_FCNTL` flag exists for non-POSIX import-time graceful fallback but no-op locking on Windows is NOT a supported configuration (Forge is POSIX-only per CLAUDE.md).

### 4.2 Phase shape

```
Phase 0 — Pre-flight gate         (test -f init.yaml, index.json, docs/overview.md, docs/architecture.md)
Phase 1 — Reset + pull inputs     (reset → read-init → read-docs → read-manifests → read-configs;
                                   each captures JSON to a named variable: INIT_JSON / DOCS_JSON /
                                   MANIFESTS_JSON / CONFIGS_JSON)
Phase 2 — Compose detection-derived values (orchestrator-direct, NO subagent — 23 fields composed
                                   in memory from the 4 Phase-1 JSON outputs; NOT yet persisted)
Phase 3 — Bulk-confirmation prompt (plain prose echo, NOT AskUserQuestion; explicit stop-discipline
                                   directive ends assistant turn after echo; user replies
                                   yes / cancel / line-per-override; JSON-array form documented
                                   for values with internal commas)
Phase 4 — Sequential user-only prompts (Q9 workflow_enforcement + Q10 ai_attribution +
                                   Q11.1/.2/.3 claude tier triple + Q12 ac_verification_mode +
                                   conditional Q12.1/.2/.3 runtime triple when mode == runtime-assisted)
Phase 5.1 — render-config         (configure.yaml + init.yaml → project-config.json atomic write)
Phase 5.2 — prune-agents          (dry-run → bulk-confirm with keep/drop list →
                                   prune-agents --apply on yes; os.unlink per dropped file)
Phase 5.3 — substitute-templates  (regex-based {{KEY}} replacement across CLAUDE.md +
                                   .claude/agents/*.md; per-file atomic write)
Phase 6 — Verify + summary        (verify cross-checks 29-field configure.yaml + 37-key
                                   project-config.json + round-trip identity; summary echoes
                                   field-by-field report verbatim)
```

Retry budgets: 3 per setter on validation failure; 3 per bulk-prompt parse failure; on 4th surface-failure-and-continue. Stop discipline: Phase 3 + Phase 5.2 echoes MUST end assistant turn (plain prose has no harness wait-for-user affordance; explicit "do not advance" directive in spec).

### 4.3 Field-source map (29 configure.yaml + 5 init.yaml + 3 derived = 37 project-config.json keys)

Detection-derived (23 fields composed in Phase 2):
- Identity (3): PROJECT_NAME / PROJECT_DESCRIPTION / PROJECT_TYPE
- Stack (9): PRIMARY_LANGUAGE / LANGUAGES / FRAMEWORKS / ARCHITECTURES / **PROJECT_NATURES** / ERROR_HANDLINGS / API_LAYERS / TESTINGS / BUILD_TOOLS
- Per-package (5): BUILD_COMMANDS / TYPE_CHECK_COMMANDS / LINT_COMMANDS / TEST_COMMANDS / PACKAGE_STACKS
- Verbatim docs (3): PROJECT_STRUCTURE / DEV_COMMANDS / ARCHITECTURE_DETAILS
- AC runtime (3): AC_RUNTIME_URL / AC_RUNTIME_API_BASE / AC_RUNTIME_CLI_COMMAND

User-only (6 fields via Phase 4 sequential prompts): WORKFLOW_ENFORCEMENT / AI_ATTRIBUTION / CLAUDE_TIER_THINK / CLAUDE_TIER_DO / CLAUDE_TIER_VERIFY / AC_VERIFICATION_MODE. (AC runtime triple is conditional follow-up to Q12 only when mode == runtime-assisted.)

From `init.yaml` (5 keys, read-through): WORKSPACE_MODE / PROJECT_ROOT / PROJECT_STATE / DEFAULT_BRANCH / PACKAGES_DETECTED.

Derived at render time (3): WRAPPER_MODE_SECTION (preset block; populated only when workspace_mode=wrapper) / COMMIT_ATTRIBUTION (preset block; populated only when ai_attribution=Yes) / AGENT_LIST (alphabetical bullet list of `.claude/agents/*.md` basenames at render time).

PACKAGE_STACKS record's `framework` field is derived from `_derive_framework_hint` per package (locked table of 24 framework→canonical-name mappings; meta-frameworks like Next.js / Nuxt / Remix / SvelteKit / Expo listed before underlying React / Vue / Svelte so meta wins; returns null when no recognized framework dep is present — prevents mis-attributing project-level top framework to every workspace package).

### 4.4 Agent pruning system

Source agent files at `src/agents/*.md` carry `applies_to: [...]` frontmatter — atomic project-nature values matching the same vocabulary as `project_natures`. The "all" sentinel marks universal-fit agents (architect / code-reviewer / qa-engineer / etc.). Specific atomic values (`web` / `backend` / `mobile`) restrict to those natures.

`scripts/generate-agents.py` propagates `applies_to` through to the installed Claude-Code-native frontmatter (`---` delimited). `_parse_agent_frontmatter` accepts BOTH source ```yaml fence form AND installed `---` form; without the dual-form parser, `prune-agents` would fail on every installed agent (frontmatter format mismatch was an empirical bug surfaced + fixed during testForge20 run).

`_decide_agent` rules:
- `applies_to` missing/unparseable → KEEP (conservative default; emits stderr warning so the user sees there's a frontmatter issue)
- `"all" in applies_to` → KEEP (universal-fit)
- `applies_to ∩ project_natures` non-empty → KEEP
- otherwise → DROP

`prune-agents [--apply]`: dry-run emits `{kept, dropped, decisions}` JSON to stdout (no file mutation); `--apply` deletes files in `dropped[]` via `os.unlink`. Phase 5.2's bulk-confirm pattern: dry-run first → echo decisions → wait for user yes/cancel/override → on yes invoke `--apply`. Override lines (`keep <name>` / `drop <name>`) processed by orchestrator since helper has no per-agent flag.

### 4.5 Template substitution

25 unique placeholders inventoried across `src/CLAUDE.md` + `src/agents/*.md` (no `{{STATE_MANAGEMENT}}` / `{{STYLING}}` — those rules live in `constitution.md` per the constitution-pipeline routing decision). Substitution map covers 4 categories:

| Category | Count | Source |
|---|---|---|
| (A) Direct project-config.json keys | 12 | Verbatim from the 37-key map |
| (B) Singular aliases of plural arrays | 10 | `{{FRAMEWORK}}` → comma-join `FRAMEWORKS`, etc. (10 fields: FRAMEWORK / LANGUAGE / BUILD_TOOL / BUILD_COMMAND / TYPE_CHECK_COMMAND / LINT_COMMAND / ERROR_HANDLING / API_LAYER / TESTING / ARCHITECTURE) |
| (C) Composed | 2 | `{{PACKAGE_STACKS_SECTION}}` markdown table (4 cols: Package \| Language \| Framework \| Build Tool); `{{PROJECT_PATHS}}` comma-join `path` from `packages_detected[]` |
| (D) Identity passthrough | 1 | `{{UPPERCASE}}` substitutes to literal `{{UPPERCASE}}` (preserves prose explanation of placeholder syntax in CLAUDE.md's "Placeholder Convention" section) |

Engine: `_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")`. Per-file atomic write via `_write_file_atomic` (mkstemp + fsync + os.replace + unlink-on-exception). Unknown placeholder → exit 2 + stderr enumerates per-file; original file NOT modified (atomic-per-file fail-safe).

Known limitation (cosmetic): substitute engine matches all `{{[A-Z_]+}}` markers including those used as DOCS examples in CLAUDE.md prose ("Any `{{UPPERCASE}}` marker (e.g., `{{PROJECT_NAME}}`)..."). The `{{PROJECT_NAME}}` example gets substituted to the actual project name on install, making the prose example slightly less didactic. Future fix: escape mechanism or fenced-code-block exclusion in the engine.

### 4.6 Wrapper-mode awareness

`read-configs` walks `index.json.packages[].files[]` for matched config-file basenames (vite.config.* / next.config.* / vitest.config.* / .env / etc.). When `init.yaml.workspace_mode == wrapper` AND `project_root != "."`, helper prepends `project_root` to abs-path construction so `<install_root>/<project_root>/<file>` resolves correctly. Without the prefix, all 88 matched files would `OSError`-skip silently and `read-configs` would emit empty `matched_files[]` (empirical bug fixed during testForge20 run).

`render-config`'s WRAPPER_MODE_SECTION + AGENT_LIST derivation also reads init.yaml. Substitute-templates does NOT use init.yaml directly — it reads project-config.json which already carries the resolved values.

### 4.7 State + outputs

```
.devforge/
  configure.yaml            # canonical 29-field state — single source of truth
  configure.yaml.lock       # fcntl LOCK_EX sidecar
  project-config.json       # 37-key render artifact (regenerated each run)
.claude/agents/             # pruned by Phase 5.2 (16 → 12 in testForge20 web case);
                            # surviving agents substituted in place by Phase 5.3
CLAUDE.md                   # substituted in place
```

`configure.yaml` is the authoritative state. `project-config.json` is regenerated each `render-config` call (not edited directly — never modified between renders). Template files are mutated in place by `substitute-templates`.

### 4.8 Locked design decisions

- **Atomic project-nature taxonomy (no "fullstack" meta-label).** A fullstack monorepo declares `project_natures: ["web", "backend"]` as a SET. Pruner uses set intersection. Cleaner than synthetic meta-values + matches monorepo reality.
- **state_management + styling routed through constitution.md.** Project conventions (rules) live in constitution; CLAUDE.md / agent template substitution doesn't carry them. Frontend-engineer + mobile-engineer agents reference `constitution.md §Conventions` instead of embedding `{{STATE_MANAGEMENT}}` / `{{STYLING}}` placeholders. Drops 2 placeholders from substitution map; tightens layering between `/configure` and `/constitute`.
- **claude_tier_* fields are non-enum scalars.** ENUM_FIELDS deliberately excludes them so users may name custom Claude routes (Bedrock, self-hosted, future model aliases) via Q11 `Other` branch. Recommended defaults: think=Opus, do=Sonnet, verify=Haiku.
- **Phase 3 plain-prose echo with explicit stop-discipline directive.** AskUserQuestion is single-line only (memory `feedback_askuserquestion_single_line_only.md`); multi-line bulk content can't fit. Plain prose has no harness-level wait-for-user affordance, so the LLM must self-impose the stop. Spec includes a "STOP and wait" directive at top of Phase 3 + Phase 5.2.
- **Helper-side framework derivation.** `_derive_framework_hint` reads manifest deps + emits canonical name from a locked priority table. NOT LLM judgment — mechanical fact extraction. Same pattern as `_derive_build_tool_hint`. Prevents Phase 2 LLM from inheriting the project-level top framework into every workspace package's record.
- **install.sh stray-state-file guard.** Empirical bug: stray `init.yaml` in `src/devforge/` (artifact from running helpers at repo root with DEVFORGE_DIR unset) got copied over the target's real init.yaml, silently wiping wrapper-mode + packages_detected. Fix: install.sh now exits 1 with a named-stray error if any user-state file (`init.yaml` / `configure.yaml` / etc.) is present in `src/devforge/` at install time. Forces cleanup at framework dev time, not user install time. `.gitignore` complements with framework-side prevention.

### 4.9 Step 6 follow-ups (post-empirical, all shipped)

The empirical /configure run on testForge20 (wrapper + 26-pkg monorepo) surfaced 5 bugs all fixed before feature-close:

1. Phase 3 stop discipline directive (LLM kept advancing past plain-prose echo without waiting)
2. JSON-array setter form (TypeScript generic syntax `Either<DataError, T>` with internal commas broke comma-split → setter now accepts JSON-array form for values with literal commas)
3. Case-insensitive enum validator (LLM passed `strict` instead of `Strict` → validator normalizes to canonical exact-case member)
4. Dash-delimited frontmatter parser (installed agents use Claude Code native `---` form, not source ```yaml fence → parser tolerates both)
5. Per-package framework_hint helper-side enforcement (LLM mis-attributed project-level top framework to every workspace package → `_derive_framework_hint` mechanical extraction; LLM uses helper output as authoritative)

Plus install.sh stray-state-file guard (Step 6 surfaced the bug; fix shipped under same banner).

---

## 5. `/constitute` — synthesize constitution.md

`/constitute` consumes the artifacts emitted by `/init-forge` + `/generate-docs` + `/configure` and synthesizes `constitution.md` at the install root. Schema-anchored: helper owns the 7-section markdown structure; LLM provides values via setters; manual concatenation render. Mirrors the helper-owns-shape pattern from `/configure` + `/generate-docs`.

### 5.1 Helper architecture

One file: `src/devforge/lib/constitute_helper.py` (~2710 lines, no submodule split). Single shell launcher at `src/devforge/lib/constitute_helper`. Stdlib only, Python 3.8+.

15 subcommands grouped by role:

| Group | Subcommands | Role |
|---|---|---|
| State plumbing | `reset` | Write fresh defaults JSON |
| Read-* inputs | `read-init` / `read-configure` / `read-docs` / `read-glossary` | Capture Phase 1 inputs as JSON |
| Identity setters | `set-project-name` / `set-mode` / `set-dates` / `set-project-identity` | Top-level scalars + identity record |
| Section builders | `add-section` / `add-rule` / `add-table` / `add-code-example` | Build Sections 2/3/5/6 sub-sections + content |
| Pattern builder | `add-pattern-rule` | Build Section 4's 6 buckets |
| Scaffolding | `set-scaffolding-guide` | Section 7 (greenfield only) |
| Render | `render` | Atomic write `<install_root>/constitution.md` |
| Verify | `verify` | Required-section + closed-enum + round-trip identity |
| Validate | `validate` | 4-dim quality framework (composite ≥0.95) |
| Summary | `summary` | Verbatim-echo report (mirrors init/configure summary) |

Schema: `FIELD_SCHEMA` carries 11 top-level keys (locked order; emit walks list for diff stability). Top-level kinds: scalar / date_scalar / enum_scalar / nullable_record / section_array / patterns_section. State format is **JSON** (not YAML) — constitute data is 2-3 levels deep (Section → rules + tables + code_examples per bucket per scope) and JSON's native nesting fits cleaner than extending the configure-style YAML emitter.

`ENUM_FIELDS`: 4 closed enums — `mode` (existing-codebase | greenfield), `rule_tag` (extracted | enforced | universal | project-specific), `section_tag` (universal | project-specific | greenfield-only), `code_label` (CORRECT | WRONG | EXAMPLE).

5 validation helpers mirror `configure_helper`: `_validate_scalar` / `_validate_enum` (case-insensitive → canonical) / `_validate_string_array` (JSON-array form for internal-comma values OR comma-sep) / `_validate_path_value` / `_validate_verbatim`. Setters route through `_state_transaction(devforge_dir)` — `fcntl.LOCK_EX` on `constitute.json.lock` sidecar; mirrors configure plumbing line-for-line.

`_find_section` first-match across 4 section_array buckets. Cross-bucket section number duplicates are a caller bug (Phase 5 spec convention numbers each bucket non-overlappingly: 2.x = architecture, 3.x = code-quality, 5.x = domain, 6.x = workflow).

### 5.2 Phase shape

```
Phase 0 — Pre-flight gate (5 file checks: init.yaml + configure.yaml + docs/{overview,architecture,glossary}.md)
Phase 1 — reset + 4 read-* into INIT_JSON / CONFIGURE_JSON / DOCS_JSON / GLOSSARY_JSON
Phase 2 — Compose section content (orchestrator-direct, NO subagent dispatch).
          Section 1 from configure.yaml + glossary; Sections 2/3 from
          architecture.patterns + conventions + universal defaults; Section 4
          6-bucket patterns; Section 5 from glossary entity terms; Section 6
          from workflow_enforcement + universal defaults; Section 7 conditional
          on greenfield + scaffolding_guide.
Phase 3 — Per-section bulk-confirmation (plain prose echo, NOT AskUserQuestion;
          STOP discipline directive at top — non-negotiable per /configure
          empirical bug; Section 4 has its own echo template — bucket-based,
          no sub-section numbers; JSON-array setter form documented for
          internal-comma values).
Phase 4 — Sequential AskUserQuestion (Q-mode auto-resolved from project_state
          when unambiguous, runtime-resolved as Phase 1.5; conditional
          Q-domain greenfield-only when glossary < 3 records).
Phase 5 — render constitution.md atomically at install_root.
Phase 6 — verify + validate + summary. Sub-0.95 validate composite prompts
          user ship/cancel/fix decision (novel pattern — /configure verify is
          binary, /constitute validate is graded; different ergonomics warranted).
```

Retry budget: 3 per setter on validation failure; 4th surface + abort.

### 5.3 4-dim validate framework

| Dim | Weight | Pass threshold | Check |
|---|---|---|---|
| `slot_fill` | 0.30 | 0.95 | Required sections + identity subfields populated. 9 slots (existing-codebase) or 10 slots (greenfield + Section 7). |
| `citation` | 0.25 | 0.95 | Path-like tokens in rule text + table cells + code annotations resolve under `<install_root>/`. Package-name lookup via init.yaml.packages_detected[]. URL filter strips http(s):// remnants. |
| `code_syntax` | 0.25 | 0.95 | python → `ast.parse`; json → `json.loads`; ts/tsx/js/jsx → balanced-brace ±1 tolerance + non-empty; other → non-empty heuristic. Zero examples → N/A (1.0). |
| `rule_tag` | 0.20 | **1.0** | Every rule.tag ∈ `ENUM_FIELDS["rule_tag"]`. Mechanical — invalid tag = helper bug. |

Composite ≥ 0.95 = exit 0; below = exit 2. stdout = JSON `{composite, dimensions, failed_items}`. stderr = per-dim scores + failed items. Per-dim `pass` field uses `_DIM_PASS_THRESHOLDS` (rule_tag = 1.0; others = 0.95) — the JSON output reflects per-dim semantics, not just the composite threshold.

### 5.4 Render

Manual concatenation per section. No template engine. Mirrors `_doc_setters.py` skeleton-fill pattern from `/generate-docs`. Tables render as GFM (`| col | col |` with separator row). Code examples as labelled fenced blocks (`**LABEL** — annotation` then ```` ```lang ```` block). Empty buckets render the H2 heading + `_(no rules defined)_` marker (no dropped sections). Section 7 renders only when `mode == greenfield` AND `scaffolding_guide` is non-null. `mode-pretty` mapping: `existing-codebase` → `Existing Codebase`; `greenfield` → `Greenfield`.

Required-field check pre-render: `project_name` + `generated_date` + `last_updated` + `mode` + `project_identity` (4 subfields). Missing → exit 2 with stderr enumerating fields. State unreadable → exit 1.

### 5.5 State + outputs

```
.devforge/
  constitute.json           # canonical 11-key state
  constitute.json.lock      # fcntl LOCK_EX sidecar
constitution.md             # render artifact at install root
```

Wrapper-mode placement: `constitution.md` lives at `<install_root>/constitution.md` regardless of wrapper/standalone mode (parallels `docs/`); never inside `project_root`.

### 5.6 Locked design decisions

- **State = JSON, not YAML.** Deviates from the single-yaml convention used by /init-forge + /configure. Justified by data depth: rules + tables + code_examples per Section per bucket per scope is 2-3 levels deep; JSON's native nesting fits cleaner than extending the configure YAML emitter.
- **Cross-bucket section numbering convention.** `_find_section` is first-match across 4 buckets. Phase 5 spec convention assigns non-overlapping number ranges per bucket (2.x = architecture, 3.x = code-quality, 5.x = domain, 6.x = workflow) so the LLM never produces a cross-bucket duplicate. Helper-side enforcement deferred — caller bug to avoid.
- **Sub-0.95 validate composite prompts user ship/cancel/fix.** Novel pattern — /configure verify is binary (yes/no); /constitute validate is graded. The user-confirmation prompt on borderline composite is the right ergonomic for graded quality. /configure-style abort would waste work on fixable issues.
- **Section 4 has no numbered sub-sections.** Six fixed buckets (always/never/prefer × universal/project-specific) addressed via `add-pattern-rule --bucket × --scope`. Section 4's Phase 3 echo template is separate from Sections 2/3/5/6 because override syntax differs (bucket:scope, not number:index).
- **Empirical bug preempts (5 items).** All shipped from day one per CONFIGURE-PLAN lessons: Phase 3 stop-discipline directive; JSON-array setter form for internal-comma values; case-insensitive enum returning canonical; install.sh stray-state-file guard for `constitute.json` + `.lock`; wrapper-mode path resolution (constitution.md at install_root).

### 5.7 Step 5 follow-ups (post-empirical)

The testForge20 helper smoke test surfaced one cosmetic finding (no functional bugs):

1. **Render produces table → bullet-list with no blank line between** (markdown style preference). Standard markdown allows the rendering but reads less cleanly. Fix path: `_render_section_body` inserts a blank line between block elements. Cosmetic; deferred.

---

## 6. CBM-first protocol enforcement

Four hooks ship at `src/hooks/` and are wired into `.claude/settings.json` by `install.sh`. They steer code exploration toward `codebase-memory-mcp` (`search_graph`, `trace_path`, `get_code_snippet`, `search_code`, `query_graph`) instead of raw `Read`/`Grep`/`Glob` or `grep`/`find`/`cat` over source files.

| Hook | Event | Matcher | Behavior |
|---|---|---|---|
| `cbm-code-discovery-gate` | `PreToolUse` | `Read\|Grep\|Glob` | First match per session: exit 2 + stderr reminder; gate file (`/tmp/cbm-code-discovery-gate-$PPID`) prevents re-trigger. Subsequent matches pass. |
| `bash-ban-raw-tools` | `PreToolUse` | `Bash` | First call per session whose `command` contains `grep`/`find`/`cat` over a source-extension file: exit 2. Other Bash calls pass. |
| `cbm-mcp-marker` | `PostToolUse` | `Bash\|mcp__codebase-memory-mcp__.*` | Append `<UTC> <tool>` to `.devforge/cbm-usage.log`. Always exit 0 — never blocks. |
| `cbm-session-reminder` | `SessionStart` | `startup\|resume\|clear\|compact` | Stdout injected as session context; re-states the protocol after compaction/resume/clear. |

These hooks shipped in Track 1 F.11 (commits `65b0a24` / `e0ca9bb` / `cdddf76`). They are install-time wired by `install.sh` updating `.claude/settings.json`; the hook scripts themselves remain on disk but inert if their entries are removed from settings. Re-running `install.sh` overwrites settings and restores hooks.

The hook scripts reference codebase-memory-mcp tools exclusively. They do NOT reference codegraph's `agentic_*` tools — those require LLM-enabled mode that is not configured in default forge installs.

---

## 7. Known limitations + drift hazards

Live as-of 2026-05-10. Most are deferred bugs surfaced during empirical validation on `testForge20`. /configure-specific bugs surfaced during the empirical run were all fixed before feature-close (see §4.9).

**`/generate-docs` (deferred):**

1. **Stamp gate anchor-schema drift.** When the helper's section anchor schema changes (e.g., adding a new project-overview section), prior rendered docs' frontmatter still says "stamp matches" but their on-disk shape no longer matches the new validator. The stamp gate skips dispatch, validate-doc passes (because old shape was valid for the old schema), and the doc never re-renders against the new shape. Workaround: force re-render via `init-doc` on the affected target. Fix pending.
2. **CBM watcher async-miss.** `_preflight.py` invokes `index_repository` synchronously, but CBM's filesystem watcher runs async — large repos can return from `index_repository` before the watcher has absorbed every recent write, causing `search_graph` queries in Phase B (glossary) to miss nodes that were just rendered. Workaround: re-run Phase B. Fix pending.
3. **Glossary classification name-normalization.** `_glossary.py` keys terms by exact-case match on the docs corpus → CBM lookup. Terms that vary in case (`useStore` in code vs. `UseStore` in prose) classify as prose-only despite a code anchor existing. Workaround: case-fold during classification. Fix pending.
4. **`index_helper` 500-file cap.** Per-package file listings cap at 500; concerns past the cap fall into `files_truncated: true`. This is why `_concern_input.py` walks the filesystem directly rather than reading `index.json` for the file list — `index.json` is structurally complete (manifest, deps, scripts) but file-list-incomplete on large packages.
5. **Vue cite-back through-sourcemap not validated.** `_validate_doc.py` checks cite-path existence + line-range only. Vue components compile through a sourcemap; validating that a `<file>.vue:line` cite resolves to the right line in the original `.vue` (not the compiled output) is deferred. `_sourcemap.py` exists but is not yet wired into validation.
6. **Per-concern dispatch cost.** ~$0.20 Haiku + ~10s wall-clock per concern. Spec surfaces the breakdown via the cost gate before Phase 2 starts; for runs over $5 / 5 min, recommend confirming with the user. Stamp-gate skips are free.

**`/configure` (cosmetic, non-blocking):**

7. **PACKAGE_STACKS framework column reads stray manifest deps.** `_derive_framework_hint` honestly reports what's in `dependencies` / `dev_dependencies`. If a package's `package.json` has a stray dep (e.g., `pkg-cse-common` with `react: ^18.2.0` in the testForge20 codebase, despite the package being pure-TS BLoC base), helper attributes that framework. Fix path: codebase-side `package.json` cleanup (not helper logic). LLM Phase 2 can also override at bulk-confirm time, but the spec's parser only handles top-level field overrides, not record-array subfield overrides — `package_stacks.<pkg>.framework: null` syntax is NOT supported. Future spec extension could add dot-path override parsing.
8. **Substitute engine matches DOCS-example placeholders.** CLAUDE.md's "Placeholder Convention" section uses `{{PROJECT_NAME}}` as a literal example for readers; substitute engine substitutes it to the real project name. Reads slightly less didactic post-substitution. Fix path: escape mechanism (`\{\{PROJECT_NAME\}\}`) or fenced-code-block exclusion in the engine. Cosmetic; no functional impact.
9. **Phase 2 LLM compose drift across re-runs.** Re-running /configure on the same project yields slightly different field compositions — not a bug, but Phase 2's LLM-judgment fields aren't deterministic. Bulk-confirm covers it (user can override). For exact reproducibility, supply explicit overrides via Phase 3 reply.

---

## 8. Reading order for new contributors

1. **Specs first** — `src/commands/init-forge/main.md`, then `src/commands/generate-docs/main.md`, then `src/commands/configure/main.md`, then `src/commands/constitute/main.md`. They are the authoritative user-facing contract.
2. **This file** — for the helper-layer mental model.
3. **`init_helper.py` + `index_helper.py` module docstrings** — `/init-forge`'s entire helper surface is two files.
4. **`_generate_docs/_cli.py`'s `_SUBCOMMANDS` registry** — the catalog of every `/generate-docs` helper subcommand.
5. **`_doc_setters.py`** — the skeleton-fill primitive everyone uses.
6. **`_preflight.py`** + **`_concern_input.py`** + **`_glossary.py`** — the three input/output modules that drive the `/generate-docs` pipeline.
7. **`configure_helper.py` module docstring + `build_parser`** — `/configure`'s helper surface is one file with ~32 subcommands. Read FIELD_SCHEMA + ENUM_FIELDS first, then `_state_transaction`, then the read-* / setters / render-config / prune-agents / substitute-templates handlers.
8. **`constitute_helper.py` module docstring + `build_parser`** — `/constitute`'s helper surface is one file with 15 subcommands. Read FIELD_SCHEMA + ENUM_FIELDS first, then `_state_transaction`, then the read-* / setters / render / verify / validate handlers. State format is JSON (not YAML — see §5.1).
9. **`scripts/generate-agents.py`'s `emit_claude` + `_render_one`** — agent emitter; understands how `applies_to` propagates from `src/agents/*.md` source frontmatter (```yaml fence) to installed `.claude/agents/*.md` (--- delimited).
10. **Plans at repo root (all DONE; retained for historical reference)** — `ARCHITECTURE-PIVOT-PLAN.md` for the 4-command sequencing context (all 8 Steps DONE 2026-05-11); `CONFIGURE-PLAN.md` and `CONSTITUTE-PLAN.md` for per-command work-order detail. None active; future work tracked in new plans.

When the helper layout in this file disagrees with what's in `src/devforge/lib/_generate_docs/`, the code wins. Update this file as part of the same change that moves the boundary.
