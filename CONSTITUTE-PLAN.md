# /constitute — implementation plan

**Status**: IN PROGRESS 2026-05-10. Plan locked (this file). No code shipped. Branch `develop-2.0-init` clean apart from auto-generated `__pycache__` files. This is Step 8 of `ARCHITECTURE-PIVOT-PLAN.md` — the final pivot scope. Predecessor work: `/init-forge` (Step 1, DONE) + `/generate-docs` (Step 2, FEATURE-CLOSED) + `/configure` (Step 4, FEATURE-CLOSED 2026-05-10).

`/constitute` is the fourth and last command in the 4-command sequence (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). It consumes `.devforge/init.yaml`, `.devforge/configure.yaml`, `docs/overview.md`, `docs/architecture.md`, and `docs/glossary.md`; populates `.devforge/constitute.json`; renders `constitution.md` at the install root with 7 schema-anchored sections + closed rule-tag enum.

## Context for next session

### What changed since the original pivot plan was written

The 2026-04-30 pivot plan said `/constitute` was "unchanged" — the existing `src/commands/constitute/main.md` (40K of pre-pivot prose) would carry through. That description is stale. Three architectural shifts since then:

1. **Helper-owns-shape extends to /constitute.** Approved 2026-04-30 (memory `project_schema_anchored_constitute.md`). `constitute_helper.py` owns `constitution.md` structure; LLM provides values via setters. Manual concatenation render (no template engine). Same pattern as `/configure` + `/generate-docs`.
2. **The 5 empirical bugs surfaced during /configure must be preempted.** Phase 3 stop-discipline directive, JSON-array setter form, case-insensitive enum validator, install.sh stray-state-file guard, wrapper-mode path resolution — all bake in from day one (see `project_schema_anchored_constitute.md` § "Patterns inherited from /configure").
3. **Existing /constitute spec is a full-rewrite scope, not a touch-up.** Current `src/commands/constitute/main.md` is 40K + 8.7K test-scenarios.md, written under the legacy `/setup-wizard` + `/onboard` + `/constitute` trio. References `.devforge/project-config.json` (legacy single-source key set), the `/setup-wizard` chain, `.devforge/wip/constitute-prewrite.md` crash-recovery, free-form prose synthesis. None of this survives Step 5 — the helper-owns-shape spec is a clean replacement.

### Empirical reference (cse-strata-ws-forge constitution.md, 451 lines)

Sample structure validated against `cse-strata-ws-forge/constitution.md` during the 2026-04-30 schema-design session:

- **Section 1 — Project Identity**: 4 fields (name, type, domain, stack)
- **Section 2 — Architecture Rules**: 3 sub-sections (2.1 Layer Boundaries with table + code examples, 2.2 File Organization with bullet rules + tree code block, 2.3 Dependency Rules with bullet rules)
- **Section 3 — Code Quality Standards**: 7 sub-sections (3.1 Type Safety through 3.7 Check Before You Build), each tagged `[universal]` or `[project-specific]`
- **Section 4 — Patterns & Anti-Patterns**: 6 sub-sections (3 buckets ALWAYS / NEVER / PREFER × 2 scopes universal / project-specific)
- **Section 5 — Domain Rules**: 3 sub-sections (5.1 Key Entities, 5.2 Business Rules, 5.3 External Contracts)
- **Section 6 — Workflow Rules**: 6 sub-sections (6.1 Minimal Changes through 6.6 Project-Specific Workflow)
- **Section 7 — Scaffolding Guide [greenfield-only]**: present only when mode == greenfield

Each rule has a tag from the closed enum: `[extracted]` / `[enforced]` / `[universal]` / `[project-specific]`. Sub-sections may carry an opening paragraph + bullet rules + tables (Layer Boundaries shape) + code examples (CORRECT vs WRONG TS/JS pairs).

### Test bed

- `/Users/mykolakudlyk/Projects/testForge20/` — wrapper mode, `project_root = db-cse-ui-strata`, 26 packages, fully populated `.devforge/{init.yaml, configure.yaml, index.json}` + `docs/{overview, architecture, glossary, structure}.md` + per-package + per-concern docs. Fresh `/constitute` invocation on this bed has every required input present.
- `/Users/mykolakudlyk/Projects/doosan/cse-strata-ws-forge/constitution.md` — the empirical reference shape (451 lines). Step 6 success criterion: regenerated constitution.md is structurally equivalent (7 sections, sub-section count matches within ±1, rule-tag distribution similar).

## Goal

Ship `/constitute` as the fourth command in the 4-command sequence. Verify on testForge20: re-running `/constitute` after `/init-forge` + `/generate-docs` + `/configure` produces a fully-populated `.devforge/constitute.json` + a rendered `constitution.md` at the install root with all 7 sections present (mode-conditional Section 7 included when greenfield), closed rule-tag enum honored, code examples syntactically valid, citation paths existent. End-to-end runs in under 8 minutes wall-clock with one bulk-confirmation prompt per major section + at most two sequential prompts (Q-mode confirm + conditional Q-domain greenfield-only).

## Architecture

### State + render

```
.devforge/
  constitute.json          # canonical state — single source of truth (JSON, not YAML — see Open Decisions)
  constitute.json.lock     # fcntl LOCK_EX sidecar
constitution.md            # render artifact at install root — regenerated each `render` call
```

`constitute.json` is the source of truth. Every setter does atomic read-modify-write through `_state_transaction(devforge_dir)` with `fcntl.LOCK_EX` on the sidecar. `constitution.md` is regenerated from `constitute.json` on each `render` call — never edited directly between renders.

**Wrapper-mode placement.** `constitution.md` lives at `<install_root>/constitution.md`, NOT inside `project_root`. Per the wrapper-mode artifact convention all framework outputs stay at install root (parallels `docs/`).

### Helper boundary

`constitute_helper.py` mirrors `configure_helper.py`'s pattern: stdlib-only, atomic writes via `tempfile.mkstemp` + `os.replace`, `_state_transaction` context manager around `fcntl.LOCK_EX`, locked field schema, enum constraints, defaults to `None` / `[]`. Single-file helper (~3.5k lines target — `configure_helper.py` is the size template). Helper owns:

- Field schema (locked order, enum constraints, default values)
- State emission shape (deterministic — diff-stable across re-runs)
- Doc-extraction logic (read overview.md / architecture.md / glossary.md sections)
- Configure-yaml extraction logic (read project_natures, language, frameworks, etc.)
- Manual markdown concatenation render (per-section, per-rule, per-table, per-code-example)
- Validation (per-field shape, cross-field invariants, 4-dim quality framework)

LLM owns:
- Rule text composition (per-section, from helper-pre-extracted inputs + ecosystem knowledge)
- Section descriptions (opening paragraph per sub-section)
- Code-example selection + annotation (CORRECT / WRONG / EXAMPLE pairs)
- Bulk-confirmation prompt rendering (orchestrator-direct, plain prose echo)
- Sequential AskUserQuestion calls for Q-mode (+ conditional Q-domain)

### Phase shape

```
Phase 0 — Pre-flight gate
  test -f .devforge/init.yaml          (else ABORT: run /init-forge first)
  test -f .devforge/configure.yaml     (else ABORT: run /configure first)
  test -f docs/overview.md             (else ABORT: run /generate-docs first)
  test -f docs/architecture.md         (else ABORT: run /generate-docs first)
  test -f docs/glossary.md             (else ABORT: run /generate-docs first)

Phase 1 — Reset + pull inputs
  constitute_helper reset
  constitute_helper read-init          # echoes init.yaml fields as JSON
  constitute_helper read-configure     # echoes configure.yaml fields as JSON
  constitute_helper read-docs          # extracts overview.md + architecture.md sections
  constitute_helper read-glossary      # extracts glossary terms + cite-back paths

Phase 2 — Compose section content (orchestrator-direct, NO subagent)
  LLM synthesizes per-section content from Phase 1 JSON outputs:
    Section 1 (Project Identity): scalar fields composed from configure.yaml
    Section 2 (Architecture Rules): rules + tables + code examples from architecture.md
    Section 3 (Code Quality Standards): rules from architecture.md Patterns/Conventions
    Section 4 (Patterns & Anti-Patterns): 6 buckets from architecture.md + ecosystem defaults
    Section 5 (Domain Rules): rules from glossary.md key terms
    Section 6 (Workflow Rules): rules from configure.yaml workflow_enforcement + universal defaults
    Section 7 (Scaffolding Guide): only when mode == greenfield
  Each section staged in memory; NOT yet persisted.

Phase 3 — Bulk-confirmation prompt (plain prose, NOT AskUserQuestion)
  Per-section: orchestrator echoes proposed rules + tables + code examples in a fenced block.
  User: 'yes' (apply this section) OR 'cancel' OR line-per-override.
  Each accepted/overridden rule applied via constitute_helper add-rule / add-table / add-code-example.
  STOP discipline: end assistant turn after each section's echo; do NOT advance to next section in same turn.

Phase 4 — Sequential user-only prompts (AskUserQuestion)
  Q-mode  set-mode  (existing-codebase | greenfield)
          (default: existing-codebase if init.yaml.project_state == brownfield;
           greenfield if project_state == empty; ask only when ambiguous)
  Q-domain (conditional, greenfield only when glossary key-entity terms < 3):
          What 3-5 key business entities does this project manage? (free text)
          Stored as scalar verbatim; LLM splits to per-entity rules in Section 5.

Phase 5 — Render
  constitute_helper render          # walks schema, manual-concatenates constitution.md
                                    # atomic write at <install_root>/constitution.md

Phase 6 — Verify + report
  constitute_helper verify          # required-section presence (1, 2, 3, 4, 5, 6,
                                    # mode-conditional 7); closed-enum rule tags;
                                    # round-trip identity (state → render → re-parse)
  constitute_helper validate        # 4-dim quality framework (slot-fill / citation /
                                    # code-example syntax / rule-tag validity);
                                    # composite ≥ 0.95 = pass
  constitute_helper summary         # verbatim-echo report (mirrors init/configure summary)
```

The retry budget per setter is 3 (matches /generate-docs + /configure convention). On 4th setter failure, surface to user + abort the run. On bulk-prompt parse failure per section, re-prompt with a clarification.

## Schema — `constitute.json`

```python
@dataclass
class ConstitutionDoc:
    project_name: str
    generated_date: str           # YYYY-MM-DD
    last_updated: str             # YYYY-MM-DD
    mode: Literal["existing-codebase", "greenfield"]
    project_identity: ProjectIdentity
    architecture_rules: list[Section]
    code_quality_standards: list[Section]
    patterns_and_antipatterns: PatternsSection
    domain_rules: list[Section]
    workflow_rules: list[Section]
    scaffolding_guide: ScaffoldingGuide | None  # mode == greenfield only

@dataclass
class ProjectIdentity:
    name: str
    type: str           # from configure.yaml.project_type
    domain: str         # 1-line domain description
    stack: str          # comma-separated stack summary

@dataclass
class Section:
    number: str         # "2.1", "3.5", etc.
    title: str
    tag: Literal["universal", "project-specific", "greenfield-only"] | None
    description: str | None
    rules: list[Rule]
    tables: list[Table]
    code_examples: list[CodeExample]

@dataclass
class Rule:
    tag: Literal["extracted", "enforced", "universal", "project-specific"]
    text: str

@dataclass
class Table:
    columns: list[str]
    rows: list[list[str]]

@dataclass
class CodeExample:
    label: Literal["CORRECT", "WRONG", "EXAMPLE"]
    language: str
    code: str
    annotation: str | None

@dataclass
class PatternsSection:
    always_universal: list[Rule]
    always_project_specific: list[Rule]
    never_universal: list[Rule]
    never_project_specific: list[Rule]
    prefer_universal: list[Rule]
    prefer_project_specific: list[Rule]

@dataclass
class ScaffoldingGuide:
    starter_directories: list[str]
    sample_files: list[FileTemplate]    # FileTemplate: path + language + content
```

ENUM_FIELDS:

```python
ENUM_FIELDS = {
    "mode":            {"existing-codebase", "greenfield"},
    "rule_tag":        {"extracted", "enforced", "universal", "project-specific"},
    "section_tag":     {"universal", "project-specific", "greenfield-only"},
    "code_label":      {"CORRECT", "WRONG", "EXAMPLE"},
}
```

`_validate_enum` is case-insensitive (returns canonical form). `_validate_string_array` accepts BOTH JSON-array and comma-separated forms (rule text + code examples frequently contain internal commas — TS generic syntax `Either<DataError, T>` requires JSON-array).

## Helper subcommand registry

```
reset
read-init
read-configure
read-docs
read-glossary

set-project-identity --name <n> --type <t> --domain <d> --stack <s>
set-mode --value <existing-codebase|greenfield>
set-dates --generated <YYYY-MM-DD> --updated <YYYY-MM-DD>

add-section --bucket <architecture|code-quality|domain|workflow> --number <n> --title <t> [--tag <universal|project-specific|greenfield-only>] [--description "..."]
add-rule --section <number> --tag <extracted|enforced|universal|project-specific> --text "..."
add-table --section <number> --columns "<c1,c2,...>" --rows-json "<JSON-array of arrays>"
add-code-example --section <number> --label <CORRECT|WRONG|EXAMPLE> --language <l> --code "..." [--annotation "..."]

add-pattern-rule --bucket <always|never|prefer> --scope <universal|project-specific> --tag <extracted|enforced|universal|project-specific> --text "..."

set-scaffolding-guide --starter-dirs "<JSON-array>" --sample-files-json "<JSON-array>"

render
verify
validate
summary
```

Approximately 14 subcommands. Smaller surface than `/configure`'s ~32 — constitute has fewer top-level fields but each setter is more complex (record-append into nested structure).

## Render approach (manual concatenation)

`render` walks the schema and concatenates `constitution.md` per section:

```
# Project Constitution — <project_name>

Generated: <generated_date>
Last updated: <last_updated>
Mode: <mode-pretty>

> Sections marked `[universal]` are pre-populated with rules that apply to ALL projects.
> Sections marked `[project-specific]` are populated by `/constitute` based on your codebase or interview answers.

---

## 1. Project Identity

**Name**: <project_identity.name>
**Type**: <project_identity.type>
**Domain**: <project_identity.domain>
**Stack**: <project_identity.stack>

---

## 2. Architecture Rules (NON-NEGOTIABLE)

These rules MUST be followed in every code change. Violating these rules requires explicit user approval.

<for each section in architecture_rules:>
### <section.number> <section.title>
[ <section.description> ]
[ <render_table(table) for table in section.tables> ]
- [<rule.tag>] <rule.text>          (one bullet per rule)
[ <render_code_example(ex) for ex in section.code_examples> ]

---

## 3. Code Quality Standards
<same shape as Section 2 with [tag] suffix on title>

## 4. Patterns & Anti-Patterns
### Always Do (Universal)
- [<rule.tag>] <rule.text>
### Always Do (Project-Specific)
- [<rule.tag>] <rule.text>
### Never Do (Universal)
### Never Do (Project-Specific)
### Prefer (Universal)
### Prefer (Project-Specific)

## 5. Domain Rules
## 6. Workflow Rules

[ if mode == greenfield: ]
## 7. Scaffolding Guide [greenfield-only]
<starter_directories>
<sample_files rendered as fenced code blocks per file>
```

Tables render as standard GitHub-flavored markdown:

```
| <col1> | <col2> | ... |
|--------|--------|-----|
| <row1col1> | <row1col2> | ... |
```

Code examples render as labelled fenced blocks:

```
**<label>** — <annotation>
```<language>
<code>
```
```

No template engine; helper owns the concatenation directly. Mirrors `/generate-docs`'s `_doc_setters.py` skeleton-fill render approach.

## 4-dim quality framework (`validate`)

Mirrors `/generate-docs`'s `validate_doc` + `/configure`'s `verify` patterns, extended to 4 quality dimensions:

1. **Slot-fill rate** — required sections present (1, 2, 3, 4, 5, 6; mode-conditional 7); each top-level section has ≥1 sub-section. Each sub-section has ≥1 rule OR ≥1 table OR ≥1 code-example. Pass = ≥0.95 of required slots filled.
2. **Citation validity** — rules citing files/packages point to existing artifacts (cross-check `docs/<package>/...` for internal links, `package.json` paths in `init.yaml.packages_detected[]`). Pass = ≥0.95 of cited paths resolve.
3. **Code-example syntax** — code blocks parse as declared language. `python` → `ast.parse`; `json` → `json.loads`; `ts` / `js` / `tsx` → balanced-brace + non-empty heuristic absent a parser; other languages → non-empty heuristic only. Pass = ≥0.95 of examples parse clean.
4. **Rule-tag validity** — every rule has a tag from the closed enum (`extracted` / `enforced` / `universal` / `project-specific`). Pass = 1.0 (mechanical, not LLM-judgment — failure is a helper bug).

Composite ≥0.95 = `validate` exits 0 (pass). Below = exit 2 with stderr enumerating per-dimension scores + failed items.

## Step-by-step work order

Each step ends with verifiable evidence. Steps are independently committable.

### Step 0 — Scaffolding + emitter wiring

Create:
- `src/commands/constitute/main.md` (stub: H1 + "TODO: implement under helper-owns-shape pattern")
- Move existing `src/commands/constitute/main.md` to `src/commands/constitute/main.md.legacy` (preserved for cross-reference during Step 5 rewrite, deleted at Step 8)
- Move existing `src/commands/constitute/test-scenarios.md` to `.legacy` similarly
- `src/devforge/lib/constitute_helper.py` (stub: argparse + reset only)
- `src/devforge/lib/constitute_helper` (POSIX launcher; copy-paste from configure_helper)
- `tests/lib/test_constitute_helper.py` (stub with 1 test for reset)

Verify `scripts/emitters/claude.py` `_PROMOTED` tuple already includes `constitute` (it predates the pivot). If absent, add it.

**Verify**: `bash install.sh` against tmpdir → `<tmpdir>/.claude/commands/constitute.md` exists with stub content; `<tmpdir>/.devforge/lib/constitute_helper` exists + executable; `python3 -m unittest tests.lib.test_constitute_helper` passes (1 test). Test baseline 1661 OK + new test = 1662 OK.

### Step 1 — Helper schema + reset + read-* subcmds

Implement:
- `FIELD_SCHEMA` + `ENUM_FIELDS` + defaults
- State emission via `json.dumps(indent=2, sort_keys=False)` (key order locked by FIELD_SCHEMA walk; mirrors configure's diff-stability contract)
- `reset` subcmd (atomic write of fresh defaults JSON)
- `read-init` subcmd (read `.devforge/init.yaml`, emit JSON to stdout)
- `read-configure` subcmd (read `.devforge/configure.yaml`, emit JSON to stdout)
- `read-docs` subcmd (parse `docs/overview.md` Tech Stack + `docs/architecture.md` Patterns + Conventions sections; emit structured JSON)
- `read-glossary` subcmd (parse `docs/glossary.md` term entries; emit JSON keyed by term)
- Tests for each: round-trip via real producers (init_helper writes init.yaml → read-init parses; configure_helper writes configure.yaml → read-configure parses; generate_docs renders docs → read-docs + read-glossary parse).

**Verify**: `python3 -m unittest tests.lib.test_constitute_helper` passes ~30 tests; running `constitute_helper read-docs` against testForge20's `docs/architecture.md` produces JSON containing every Patterns + Conventions section.

### Step 2 — Setters + atomic state

Implement every setter in the registry. Each setter is per-field shape-validate + atomic read-modify-write through `_state_transaction(devforge_dir)`. Mirror `configure_helper`'s setter shape.

Validation helpers (5 patterns from configure):
- `_validate_scalar` — non-empty after strip
- `_validate_enum` — case-insensitive → returns canonical (lowercase `extracted` → `extracted` since enum lowercase; mixed-case `Extracted` → `extracted`)
- `_validate_string_array` — accepts JSON-array form `["a", "b,c"]` AND comma-separated form `"a, b"`
- `_validate_path_value` — non-empty, no newlines
- `_validate_verbatim` — non-empty, preserve internal whitespace (rule text + code examples frequently multi-line)

`add-section` / `add-rule` / `add-table` / `add-code-example` / `add-pattern-rule` are array-append into the locked schema; concurrency-safe via `_state_transaction`.

`add-table --rows-json` decodes `json.loads` and re-validates as `list[list[str]]`.

`set-scaffolding-guide --sample-files-json` decodes as `list[{"path": str, "language": str, "content": str}]`.

Tests: per-setter validate-then-load test (assert state shape after each call). Round-trip test (set every field type; reload; compare). Cross-process safety test (concurrent `add-rule` via subprocess; assert no lost array-append).

**Verify**: ~80 setter tests pass. testForge20 round-trip: stage every section type; reload; compare; identical.

### Step 3 — render + verify + summary

Implement:
- `render` — read constitute.json, walk schema, concatenate constitution.md per the manual-concatenation template above. Atomic write at `<install_root>/constitution.md`.
- `verify` — read constitute.json, assert required sections (1-6, mode-conditional 7) present, all rule tags ∈ closed enum, round-trip identity (parse rendered constitution.md → reconstruct state → compare). Exit 0 = pass, 2 = violation.
- `summary` — verbatim-echo report (mirrors `init_helper summary` + `configure_helper summary`). Section-by-section listing in locked order with rule + table + code-example counts.

Tests: render produces stable output (byte-identical across re-runs on stable input modulo `last_updated`); verify catches missing sections; summary output stable.

**Verify**: ~30 tests pass. testForge20 hand-populated fixture renders constitution.md with all 6 + (greenfield-only) 7 sections, ~250-450 lines depending on rule density, no remaining placeholder markers.

### Step 4 — `validate` (4-dim quality)

Implement `validate` subcmd per the 4-dim framework above. CI-runnable: exit 0 = composite ≥0.95 pass; exit 2 = failure with per-dimension stderr report.

For citation validity: walk every rule text + table cell + code annotation; extract paths matching `<word>/<word>(.<ext>)?` patterns; cross-check against `init.yaml.packages_detected[].path` + `docs/<package>/` directory existence.

For code-example syntax: switch on `code_example.language`; dispatch to per-language parser; fail closed (unknown language counts as pass-through with warning).

For rule-tag validity: regex `^\[(extracted|enforced|universal|project-specific)\]\s+` on every emitted rule line; failure = helper bug.

Tests: ~25 tests covering each dimension, including known-bad fixtures (missing section / unresolved cite path / unparseable code / invalid tag) that should produce per-dimension failure.

**Verify**: `validate` against testForge20 hand-populated fixture exits 0 with composite ≥0.95.

### Step 5 — Spec authoring (`src/commands/constitute/main.md`)

Rewrite from scratch under helper-owns-shape Phase 0-6 contract. Replace the legacy 40K spec entirely (preserved at `.legacy` from Step 0; deleted at Step 8). Mirror `src/commands/configure/main.md`'s shape:

- Frontmatter (`name: constitute`, `description: Synthesize constitution.md from /configure + /generate-docs outputs`, `disable-model-invocation: true`)
- H1 + Outputs section
- Phase 0 pre-flight gate (5 file-existence checks)
- Phase 1 read-* invocations (capture INIT_JSON / CONFIGURE_JSON / DOCS_JSON / GLOSSARY_JSON variables)
- Phase 2 LLM compose (orchestrator-direct, no subagent — mirrors /generate-docs convention)
- Phase 3 per-section bulk-confirmation prompt format (literal echo template + parsing rules + STOP discipline directive at top of each section)
- Phase 4 sequential prompts (Q-mode + conditional Q-domain only — strictness + naming absorbed into Phase 2)
- Phase 5 render
- Phase 6 verify + validate + summary

Reference docs (one each, parallel to `/configure`'s `q11-tiers.md` + `q12-ac.md`):
- `references/section-shapes.md` — per-section opening prose template + tag-distribution guidance + code-example selection criteria
- `references/empirical-bugs.md` — the 5 preempt-from-day-one items (stop discipline / JSON-array / case-insensitive enum / install guard / wrapper-mode) restated for spec readers

Run `instruction-author` to write the spec; verify via `instruction-reviewer` + `claude-code-guide` per the iterative-review-loop convention.

**Verify**: spec passes both reviewers; sentence-level hallucination check passes (every sentence verifiable now or marked as forward-ref); cross-file consistency check passes (no stale `/setup-wizard` references; no references to `.devforge/wip/constitute-prewrite.md` or other legacy artifacts).

### Step 6 — End-to-end empirical run

Run `/constitute` against testForge20 (with `/init-forge` + `/generate-docs` + `/configure` already complete). Confirm:
- `.devforge/constitute.json` populated (every required field non-null per FIELD_SCHEMA)
- `constitution.md` rendered at install root with all 6 sections (mode = existing-codebase, so Section 7 absent)
- Section count matches reference shape (~7 sub-sections across architecture + code-quality + domain + workflow; ~6 buckets in patterns)
- Rule count > 30 (cse-strata reference has 80+; lower bound check)
- `constitute_helper verify` exits 0
- `constitute_helper validate` reports composite ≥0.95
- Bulk prompts per section fit one screen + parse 'yes' / overrides correctly
- Q-mode prompt resolves cleanly (testForge20 is brownfield → default existing-codebase)
- Total wall-clock < 8 min

If any field detection misfires on testForge20's wrapper-mode + 26-package monorepo, fix in the same commit. Commit under `testParity-constitute-run1` worktree branch (mirrors prior parity-run convention).

**Verify**: full run logged + committed; constitution.md visually compared against `cse-strata-ws-forge/constitution.md` reference shape.

### Step 7 — install.sh chain integration

Forward-compat already shipped 2026-05-10:
- install.sh stray-state-file guard already covers `constitute.json` + `constitute.json.lock` (was scoped to `constitute.yaml` + `.lock` per single-yaml memory; **revisit during Step 0 if state format flipped to JSON** — see Open Decisions)
- `.gitignore` complements with `constitute.json` + `constitute.json.lock` entries

Verify both are still in place after Step 0 commit. Update install.sh final-message string if it doesn't already mention `/constitute` as the 4th step (already shipped 2026-05-10 per session-summary).

**Verify**: `git grep -n constitute.yaml install.sh .gitignore` shows the guard entries (renamed to `.json` if format flipped); fresh install on a tmpdir runs `/init-forge` → `/generate-docs` → `/configure` → `/constitute` cleanly; re-running `/constitute` updates only its outputs.

### Step 8 — Cross-reference updates + status flip

- `ARCHITECTURE-PIVOT-PLAN.md` §Step 8 → DONE; cross-reference this plan
- `CLAUDE.md` "Active work" section → strike through CONSTITUTE-PLAN.md (mirror CONFIGURE-PLAN.md treatment)
- `docs/v2/ARCHITECTURE.md` → add §5 `/constitute` section (helper architecture, phase shape, schema, render approach, validate framework, locked design decisions); renumber CBM hooks (currently §5) to §6 + later sections to match
- Memory `project_4command_architecture_pivot.md` → mark all 4 commands DONE
- Delete `src/commands/constitute/main.md.legacy` + `test-scenarios.md.legacy` (preserved through Step 5 for cross-reference; no longer needed)
- Write `SESSION-SUMMARY-NEXT.md` replacing `SESSION-SUMMARY-2026-05-10.md`; mark all 4 pivot commands shipped + retire pivot plan

**Verify**: no stale "Step 8 next" references remain in any plan / status doc; pivot plan retired; `git grep -n constitute.md.legacy` returns empty.

## Open decisions — RESOLVED 2026-05-10

- **State file format**: RESOLVED → JSON (`.devforge/constitute.json`). Native nesting fits Section→rules+tables+code_examples shape. Smaller emitter. Precedented by `/generate-docs` (`.generate-docs-state.json`). Deviates from the prior "single-yaml convention won" memory; the memory pre-dated nested-data design. install.sh + `.gitignore` stray-state guards renamed from `constitute.yaml` to `constitute.json` in Step 0.

- **Existing /constitute spec rewrite scope**: RESOLVED → full rewrite under helper-owns-shape. Legacy 40K main.md + 8.7K test-scenarios.md preserved as `.legacy` through Step 5 for cross-reference; deleted at Step 8. Discards Phase 1 deferred-wizard handling, SCHEMA_VERSION negotiation, Q-strict / Q-naming / Q-domain free-form interview, wip/crash-recovery, abort restoration. None fits helper-owns-shape.

- **Phase 4 user-only scope**: RESOLVED → Q-mode + conditional Q-domain only. Strictness covered by `/configure`'s `workflow_enforcement`. Naming + per-stack absorbed into Phase 2 LLM compose. Domain entities pre-populated from glossary; ask only when greenfield AND glossary key-entity terms < 3.

- **ScaffoldingGuide (Section 7)**: RESOLVED → ship schema + setter + render-conditional in v1. testForge20 brownfield won't exercise it; greenfield validation deferred to post-Step-6 manual check on fresh-init scratch project. Doesn't block feature-close.

- **Q-naming category-by-category**: DEFERRED to v2. Helper-owns-shape v1 collapses into Phase 2 LLM compose. Add per-category Phase 4 Qs in follow-up if empirical run surfaces naming-rule gaps.

## When resuming work

**Status as of last save**: plan locked 2026-05-10 (this file). No code shipped. Branch `develop-2.0-init` clean apart from auto-generated `__pycache__` files. Tests baseline 1661 OK + 3 skipped.

1. Read this plan in full.
2. Read `ARCHITECTURE-PIVOT-PLAN.md` for the broader 4-command sequencing context.
3. Read `CONFIGURE-PLAN.md` as the structural template (this plan mirrors its shape).
4. Read memory `project_schema_anchored_constitute.md` for schema design + patterns inherited from /configure.
5. Read `docs/v2/ARCHITECTURE.md` §4 (`/configure`) for the helper-layer mental model — `constitute_helper.py` follows the same `configure_helper.py` pattern.
6. Confirm test bed availability: `ls /Users/mykolakudlyk/Projects/testForge20/.devforge/` (init.yaml + configure.yaml + index.json present) and `ls /Users/mykolakudlyk/Projects/testForge20/docs/` (overview.md + architecture.md + glossary.md present).
7. Confirm test baseline: `python3 -m unittest discover tests/lib -q` reports all tests OK on `develop-2.0-init`.
8. Resolve the four Open Decisions above before Step 0 (state format, spec rewrite scope, Phase 4 scope, ScaffoldingGuide v1).
9. Execute Steps 0-8 in order. Each step is independently committable.
10. Use the iterative apply-verify loop:
    - Python: `python-engineer` writes function + tests in same turn → `python-reviewer` audits → loop until clean.
    - Spec: `instruction-author` writes → `instruction-reviewer` + `claude-code-guide` audit in parallel → loop until clean.
11. Bulk-confirmation prompt design (Phase 3) must be plain prose echo with explicit STOP discipline directive (per `feedback_askuserquestion_single_line_only.md` + Phase 3 stop-discipline empirical bug from /configure).
12. Helper-owns-shape extends to render — LLM never edits constitution.md via the Edit tool inside `/constitute` (per `feedback_helper_owns_shape_principle.md` memory).
13. Commit each step independently; don't bundle.

Test data validation: every step verifiable against testForge20 (wrapper + 26-package monorepo brownfield). Greenfield path (Section 7 ScaffoldingGuide) deferred to post-Step-6 manual validation against a fresh-init scratch project.
