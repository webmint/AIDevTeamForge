# Section shapes — per-section authoring guidance

`/devforge:constitute` Phase 2 composes section content from Phase 1 JSON outputs. The structural shape (section numbers, bucket assignment, rule-tag enum, table column/row consistency) is locked by `constitute_helper`; only the rule TEXT, table CELLS, code-example CONTENT, and section DESCRIPTION are LLM-composed. The universal parts — sub-sections 3.5-3.8 and 6.1-6.4, and Section 4's three universal buckets — are not composed at all: Phase 1's `constitute_helper seed-universal` writes them verbatim from the canonical constitution, with their numbers, headings, tags and rule identities. This file documents per-section authoring expectations: opening prose template, tag distribution rules, sub-section count expectations, table shape examples, and code-example selection criteria.

## Cross-section numbering convention

Sub-section numbers are bucket-prefixed and non-overlapping:

- Section 2 (Architecture Rules) → sub-sections numbered `2.1`, `2.2`, `2.3`, ...
- Section 3 (Code Quality Standards) → fixed numbers `3.1`-`3.8`: 0-4 composed, numbered consecutively from `3.1` and never beyond `3.4`; `3.5`-`3.8` seeded by `seed-universal`
- Section 4 (Patterns & Anti-Patterns) → no numbered sub-sections; six fixed buckets — the three universal ones seeded by `seed-universal`, the three project-specific ones composed via `add-pattern-rule`
- Section 5 (Domain Rules) → sub-sections numbered `5.1`, `5.2`, `5.3`
- Section 6 (Workflow Rules) → fixed numbers `6.1`-`6.6`: `6.1`-`6.4` seeded by `seed-universal`; 0-2 composed, numbered `6.5` then `6.6`
- Section 7 (Scaffolding Guide) → no numbered sub-sections; single `set-scaffolding-guide` call

The helper's `_find_section` does first-match across the four section_array buckets keyed by the `--number` argument, so non-overlapping numbering is required: do NOT use `2.1` for both an architecture sub-section and a workflow sub-section.

## Tag distribution

**Two distinct enums — DO NOT confuse:**

- **`section_tag`** (used by `add-section --tag`): `{universal, project-specific, greenfield-only}`. Optional. Describes the section's audience scope — universal sections apply to every project; project-specific sections describe THIS project's customisations; greenfield-only is reserved for Section 7. **Does NOT include `extracted` or `enforced`.** A section extracted from this codebase carries `--tag project-specific` (because it describes THIS project), NOT `--tag extracted`. `seed-universal` writes `universal` on the seeded sub-sections 3.5-3.8 and 6.1-6.4; Phase 2 never passes `--tag universal` to `add-section`.
- **`rule_tag`** (used by `add-rule --tag` + `add-pattern-rule --tag`): `{extracted, enforced, universal, project-specific}`. REQUIRED. Describes the rule's provenance / authority. The 4-value enum below is the rule_tag rubric. A rule record may also carry `name`, its identity: `seed-universal` writes it on every canonical rule and the universal-section drift check matches rules by it; `add-rule` / `add-pattern-rule` accept `--name`, but Phase 2 never passes it.

Common LLM confusion: passing a rule_tag value to `add-section --tag`. The helper rejects with `section_tag: invalid value 'extracted'` — re-emit with `project-specific` (the section_tag analog of the rule_tag `extracted`).

The `rule.tag` enum is `{extracted, enforced, universal, project-specific}`. Decision rubric:

- **`extracted`** — rule is directly cited from the project's documentation (`docs/architecture.md`, `docs/glossary.md`, etc.). Use this when the rule reads as a paraphrase of source documentation. Default for most Section 2 + Section 5 rules.
- **`enforced`** — rule is mechanically enforced by tooling (tsconfig `strict`, ESLint config, pre-commit hooks, CI checks). Use this when the rule would fail a build / lint / type-check if violated. Default for most Section 3 type-safety + lint rules.
- **`universal`** — rule applies to every project regardless of stack or domain. `seed-universal` writes it on every canonical rule of sub-sections 3.5-3.8 and 6.1-6.4 and of Section 4's three universal buckets. Phase 2 never assigns it — every rule Phase 2 composes carries one of the other three tags.
- **`project-specific`** — rule applies only to this project (e.g., a custom naming convention, a project-unique enforcement). Default for Section 4 project-specific-scope rules and project overrides in Sections 3, 5, 6.

A rule may legitimately fit more than one tag (an extracted rule that is also enforced by tooling). Pick the tag that best signals intent — `enforced` wins over `extracted` when tooling is the source of authority.

## Section 1 — Project Identity

**Shape**: 4 scalars (no rules, no tables, no code examples).

**Opening prose**: none — Section 1 renders as a 4-row bold-key list, not as a sub-section bucket. The helper concatenates the four scalars into the rendered output directly.

**Composition tips**:
- `domain` — one sentence. Compose from `GLOSSARY_JSON` key entity terms (3-5 most-used by `used_in` count). Keep the language concrete (e.g., "Industrial equipment quoting and dealer management" beats "Business domain platform").
- `stack` — one sentence, comma-separated. Order: language(s) → primary framework → secondary frameworks → architecture style → build tooling. Cap around 12 items.

## Section 2 — Architecture Rules

**Shape**: 2-4 sub-sections, each with rules + optional table + optional code examples.

**Sub-section count expectation**: 3 typical (Layer Boundaries, File Organization, Dependency Rules). Add 1-2 more only when the project has additional load-bearing architectural patterns (e.g., a cross-cutting eventing layer worth its own sub-section).

**Sub-section opening prose**: 1-2 sentences naming the architectural pattern, the layers/modules involved, and the import/dependency direction. Example: "The codebase follows Clean Architecture + BLoC. Each domain package is organized into feature sub-modules with three layers — `data/`, `domain/`, `presentation/` — plus a composition-root factory."

**Table shapes**:
- **Layer Boundaries** (most common Section 2 table) — 4 columns: `Layer | Path | Contains | Imports from`. One row per layer.
- **Module Structure** — typically a fenced tree code block (NOT a markdown table) showing `src/` hierarchy. Emit via `add-code-example --label EXAMPLE --language text --code "..."`.

**Code-example selection criteria**:
- Prefer **CORRECT/WRONG pairs** for architecture rules. Each pair is two `add-code-example` calls — one with `--label CORRECT`, one with `--label WRONG` — sharing the same `--language`.
- Each example is 4-15 lines. Truncate larger examples; the goal is to illustrate the rule, not to ship complete files.
- Use `--annotation` to label the rule the example illustrates (e.g., `--annotation "domain entity with immutable mutation"`).

**Tag distribution typical for Section 2**: predominantly `extracted` (rules cited from `architecture.md`); occasional `enforced` (e.g., `@` alias resolves to `./src` — enforced by tsconfig + ESLint).

## Section 3 — Code Quality Standards

**Shape**: fixed numbering. The four universal sub-sections — 3.5 Universal Code Quality, 3.6 Design Principles, 3.7 Check Before You Build, 3.8 Design Fidelity — are seeded by `seed-universal`, numbers and headings included; Phase 2 composes nothing for them. Phase 2 composes only the project-specific sub-sections, numbered consecutively 3.1, 3.2, … and never beyond 3.4, each with rules + optional table + optional code examples.

**Sub-section count expectation**: 0-4 composed sub-sections, one per quality dimension the project has content for. Headings are the project's dimensions: the typical ones are Type Safety, Error Handling, Naming Conventions, Testing Requirements — use them when they fit, otherwise name the project's own dimension (e.g., "Import Style"). A project with more than four dimensions merges related ones until four or fewer remain.

**Sub-section opening prose**: 1-2 sentences naming the quality dimension. Each composed sub-section carries an optional `--tag`: `project-specific` (e.g., "Type Safety [project-specific]"). Phase 2 never passes `--tag universal`.

**Table shapes**:
- **Naming Conventions** — 3 columns: `What | Convention | Example`. One row per naming convention (entity class, repository, use case, etc.).
- Other sub-sections rarely need tables — bullet rules + code examples cover most ground.

**Code-example selection criteria**:
- Prefer **EXAMPLE** label for Section 3 (illustrative single-block snippets).
- CORRECT/WRONG pairs work well for Type Safety + Error Handling sub-sections (e.g., showing `any` type as WRONG and `unknown` + type guard as CORRECT).

**Tag distribution typical for Section 3**: the composed 3.1-3.4 carry a mix of `enforced` (tsconfig strict, ESLint strictness rules), `extracted` (project naming conventions documented in architecture.md), and `project-specific` (conventions implicit in the codebase but not explicitly documented). The seeded 3.5-3.8 rules carry `universal`; Phase 2 tags no rule `universal`.

## Section 4 — Patterns & Anti-Patterns

**Shape**: 6 fixed buckets, one per `--bucket` × `--scope` combination. The three universal buckets are seeded by `seed-universal` from canonical 4.1 ALWAYS Do, 4.2 NEVER Do and 4.3 PREFER; Phase 2 composes nothing for them. Phase 2 composes only the three project-specific buckets, via `add-pattern-rule --scope project-specific`. No sub-section numbering, no tables, no code examples.

**Bucket × scope matrix**:

| Bucket | Universal scope (seeded) | Project-specific scope (composed) |
|--------|--------------------------|-----------------------------------|
| `always` | Canonical 4.1 ALWAYS Do | Always-do rules unique to this project |
| `never` | Canonical 4.2 NEVER Do | Never-do rules unique to this project |
| `prefer` | Canonical 4.3 PREFER | Project-specific preferences |

**Per-bucket count expectation**: 3-8 rules per project-specific bucket. Heavily-curated codebases (with strong coding conventions) push them toward 8; new projects with thin conventions push them toward 3. The universal buckets hold the seeded canonical rules, so no count expectation applies to them.

**Tag distribution typical for Section 4**: project-specific-scope rules → `tag = extracted` (when the rule is documented in architecture.md) or `tag = project-specific` (when implicit in the codebase but not explicitly documented). The seeded universal-bucket rules carry `tag = universal`; Phase 2 tags no rule `universal`.

**Source for the project-specific buckets**: draw from two sources — (1) `DOCS_JSON.architecture.patterns` (the architecture.md Patterns section) and (2) the `**State Management**` bucket of `DOCS_JSON.architecture.conventions`. Classify each state-management convention into `always` / `never` / `prefer` by how the rule is phrased: a mandate → `always`; a prohibition → `never`; a preference → `prefer`. See `main.md` § "Section 4" for the full conventions-bucket routing table (which `DOCS_JSON.architecture.conventions` bucket lands where).

**Composition tip**: keep each rule one sentence. Multi-clause rules belong in Section 2 or Section 3 with code examples. The Section 4 buckets are quick-reference checklists, not deep-dive content.

## Section 5 — Domain Rules

**Shape**: 1-3 sub-sections (Key Entities, Business Rules, External Contracts), each with rules + optional table + optional code examples.

**Sub-section count expectation**:
- 1 sub-section (5.1 Key Entities only) — minimum viable Section 5; greenfield projects with thin domain knowledge.
- 2 sub-sections (5.1 + 5.2) — typical for most projects.
- 3 sub-sections (5.1 + 5.2 + 5.3 External Contracts) — for projects with external API integrations or third-party service contracts.

**Sub-section opening prose**:
- 5.1 Key Entities: name the 3-5 most-used entities (e.g., "Order, Quote, Customer, Catalog, Dealer").
- 5.2 Business Rules: name the rule category (e.g., "Order lifecycle invariants", "Quote validation rules").
- 5.3 External Contracts: name the integration surface (e.g., "Apollo GraphQL contracts with the backend service layer").

**Composition source**:
- Pull entity terms from `GLOSSARY_JSON` records where `used_in` paths point to `entities/`, `domain/`, `models/`, `core/`.
- Pull business rules from glossary records whose `definition` paragraphs include verbs like "must", "cannot", "is required to".
- Pull external contracts from glossary records whose `used_in` paths include `services/`, `integrations/`, `external/`, `api/`.

**Tag distribution typical for Section 5**: predominantly `extracted` (rules pulled from glossary); occasional `project-specific` (rules added via Phase 4 Q-domain greenfield prompt).

## Section 6 — Workflow Rules

**Shape**: fixed numbering. The four universal sub-sections — 6.1 Minimal Changes, 6.2 Semantic Understanding, 6.3 Read-First Principle, 6.4 Documentation — are seeded by `seed-universal`, numbers and headings included; Phase 2 composes nothing for them. Phase 2 composes only the project-specific sub-sections, numbered consecutively 6.5, then 6.6, each with rules. Tables and code examples are rare in Section 6.

**Sub-section count expectation**: 0-2 composed sub-sections, one per workflow concern the project has content for. Typical headings: Deprecation Handling, Project-Specific Workflow. A single composed sub-section takes 6.5, whatever its heading.

**Sub-section opening prose**: 1 sentence stating the composed sub-section's intent.

**Tag distribution typical for Section 6**:
- 6.1-6.4 → seeded by `seed-universal` with `universal` on the sub-section and on every rule. Phase 2 tags nothing there, because it composes nothing there.
- The composed 6.5 / 6.6 → `--tag project-specific`; per-rule tags `extracted` (when documented), `enforced` (the CBM-first protocol rule below), or `project-specific` (when implicit).

**Composition source**: extract project-specific workflow rules from `CONFIGURE_JSON.workflow_enforcement` value. The four universal sub-sections 6.1-6.4 need no derivation from JSON inputs — `seed-universal` writes them from the canonical constitution.

**CBM-first protocol rule (Section 6 project workflow sub-section)**: when `.claude/settings.json` exists with the AIDevTeamForge CBM hooks (`cbm-code-discovery-gate`, `bash-ban-raw-tools`, `cbm-mcp-marker`, `cbm-session-reminder`), Phase 2 MUST add an `[enforced]` rule to the Section 6 project-specific sub-section for project workflow — typically headed Project-Specific Workflow, at 6.6, or at 6.5 when it is the only composed one — composing that sub-section when it is absent: structural code queries route through `codebase-memory-mcp` tools (`search_graph` / `trace_path` / `get_code_snippet` / `search_code` / `query_graph`) — NOT raw `Read` / `Grep` / `Glob` over source files. The hooks block raw discovery at `PreToolUse` on the first match per session. Optional companion `[project-specific]` rule, in the same sub-section: `docs/` is LLM-context-source first, dev-greppable second; concern prose lives in `docs/<pkg>/<concern>/index.md`; structural metadata stays in CBM (queried live), never embedded in `docs/`. Phase 2 detects CBM-hook presence via `test -f .claude/settings.json` + grep for the hook script names; absence → skip both rules.

## Section 7 — Scaffolding Guide (greenfield only)

**Shape**: single `set-scaffolding-guide` call with two arguments.

**`--starter-dirs`** — JSON array of directory names. Compose from `CONFIGURE_JSON.frameworks` + `CONFIGURE_JSON.architectures`:
- Generic project → `["src", "tests", "docs"]`
- Monorepo → `["apps", "packages", "tools", "docs"]`
- Frontend SPA → `["src/components", "src/pages", "src/lib", "src/styles", "tests"]`
- Backend service → `["src/routes", "src/services", "src/models", "src/middleware", "tests"]`

**`--sample-files-json`** — JSON array of `{path, language, content}` records. Aim for 3-6 files: one manifest (`package.json` / `pyproject.toml` / `Cargo.toml`), one type-config (`tsconfig.json` / etc. when applicable), one entry-point file (`src/index.ts` / `src/main.py`), one README, one CI config (optional).

Each file's `content` is the full literal file content as a string (no placeholder substitution; the user edits after `/devforge:constitute` ships).

**Tag distribution**: Section 7 carries no rule tags; it is a structural sub-doc, not a rule list.

## Common authoring mistakes

- **Using a markdown table when a fenced code block fits better.** Module-structure trees, sample directory layouts, and ASCII flow diagrams render better as `add-code-example --label EXAMPLE --language text` than as `add-table`. Reserve tables for genuine tabular data with consistent columns.
- **Tagging a composed rule `universal`.** `universal` belongs to the canonical rules `seed-universal` writes; Phase 2 never assigns it. A composed rule that reads as stack-agnostic is either already in the seeded canon — omit it — or a rule of this project, tagged `extracted`, `enforced` or `project-specific` per the rubric above. A rule that mentions `foo-types` is always one of those three.
- **Sub-section count creep.** Sticking to the count expectations above keeps `constitution.md` in the 250-450 line range typical of a healthy reference shape. Sections 3 and 6 compose only at their project-specific numbers (consecutive from 3.1 up to 3.4; 6.5 then 6.6): a project with more than four quality dimensions merges related ones into four or fewer sub-sections — never composing at 3.5 or above (3.5-3.8 are seeded), never adding a 3.9.
- **Overlapping numbers across buckets.** `2.1` is in the architecture bucket; `5.1` is in the domain bucket. Re-using `2.1` for a domain sub-section breaks the helper's `_find_section` first-match resolution.
