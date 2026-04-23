# {{cli.sigil}}constitute — Establish project rules from scan + preferences

You are populating the project's `constitution.md` body sections with enforceable rules. The constitution is the authoritative source of HOW code must be written in this project; every downstream command (`{{cli.sigil}}plan`, `{{cli.sigil}}execute-task`, `{{cli.sigil}}review`, `{{cli.sigil}}fix`, etc.) reads it before acting.

`{{cli.sigil}}constitute` is the **establishment phase** — it takes what already exists (setup-wizard's answers, onboard's discovery findings, the constitution scaffold) plus a small number of questions the user alone can answer, and synthesizes per-language ALWAYS / NEVER / PREFER rules, layer boundaries, naming conventions, and domain rules into the constitution's `[project-specific]` sections.

This command does NOT scan the codebase — onboard already did that for brownfield projects. This command does NOT re-ask questions the wizard already captured (architecture pattern, error handling, API layer, testing framework). It reads those as inputs and produces rules that reflect them.

## Prerequisites

1. `{{cli.sigil}}setup-wizard` must have been run — `.devforge/project-config.json` exists with Q-answers populated.
2. `constitution.md` must exist at the project root (placed by install, header populated by wizard §5.7).
3. For brownfield projects: `{{cli.sigil}}onboard` should have run first — `docs/overview.md`, `docs/architecture.md`, and `.devforge/memory.md` contain scan findings. If onboard was skipped on a brownfield project, proceed anyway — the scan-derived sections fall back to user interview + convention-based rules with `[convention]` tagging (see Phase 4).
4. The constitution must not already be populated — check `constitution.md`: if any `[project-specific]` section still contains a sentinel string starting with `_Run constitute to populate` (bare form or any of the variants described in Phase 5 Step 1), proceed in Fresh-fill mode. If NO `[project-specific]` section contains such a sentinel (all already populated), ask the user whether to re-constitute (Full-rewrite mode) or abort.

If any prerequisite is missing, inform the user and suggest running the missing command first.

## PHASE 1: Read Context

Load inputs from existing artifacts. Do NOT walk the codebase.

1. **`.devforge/project-config.json`** — wizard answers. Retain in working memory:
   - `LANGUAGES` / `FRAMEWORKS` / `PRIMARY_LANGUAGE`
   - `ARCHITECTURES[]` (per-stack; may contain `"TBD"`)
   - `ERROR_HANDLINGS[]` (per-stack)
   - `API_LAYERS[]` (per-stack; may be `"N/A"`)
   - `TESTINGS[]` (per-stack; may be `"N/A"`)
   - `WORKFLOW_ENFORCEMENT` (strict / moderate / light)
   - `PROJECT_STATE` — `brownfield` / `greenfield` / `empty`
   - `WORKSPACE_MODE`, `SOURCE_ROOT`
   - `PACKAGES_DETECTED` / `PACKAGE_STACKS` for multi-package projects

2. **`constitution.md`** — determine operation mode based on the user's answer to Prereq #4:
   - **Fresh-fill mode** (at least one `[project-specific]` section still carries a sentinel starting with `_Run constitute to populate` — bare form or any variant): your targets are the sentinel-marked sections. Leave already-populated sections untouched.
   - **Full-rewrite mode** (user chose "re-constitute" in Prereq #4 when all sections were already populated): your targets are every `[project-specific]` body section — regenerate content regardless of current state.
   
   In either mode, hold the current file body in memory so you can restore it on abort (Phase 6).

3. **`docs/architecture.md`** — if onboard ran, this contains module map, dependency rules, conventions, and cross-cutting concerns. Read these as observed patterns to cite when synthesizing rules.

4. **`docs/features/*.md`** and **`docs/api/*.md`** — if present (onboard ran), these describe module responsibilities, public surfaces, key types, invariants. Use them to inform per-module rules and Section 5 domain rules.

5. **`.devforge/memory.md`** — check `## Architecture Decisions` and `## Known Pitfalls` for onboard findings (module boundaries, dependency warnings, complexity hotspots, inconsistencies).

6. **Lint / type-check / test configs at project root** — if any exist (`.eslintrc*`, `tsconfig.json`, `pyproject.toml` linting sections, `rustfmt.toml`, `.golangci.yml`, `Cargo.toml` clippy sections, etc.), note which rules are ENFORCED by tooling. Rules derived from these get the `[enforced]` tag in Phase 4.

## PHASE 2: Resolve Deferred Wizard Answers

If any of `ARCHITECTURES[]`, `ERROR_HANDLINGS[]`, `API_LAYERS[]`, `TESTINGS[]` contain `"TBD"` (user deferred during wizard), resolve them now — you can't synthesize project-specific rules for a stack whose architecture / error-handling / etc. is unknown.

For each `"TBD"` entry, ask the user inline using your runtime's natural question mechanism:

> For stack [i+1] ([LANGUAGES[i]] / [FRAMEWORKS[i]]), the wizard deferred the `[concern name]` question. Please answer now so I can generate rules for this stack. Free-form answer — name a specific pattern or convention (e.g., "hexagonal architecture", "thiserror + `?` operator", "REST with problem+json"), or answer "still defer" to omit rules for this stack × concern combination.

Store the user's answer verbatim; update the in-memory copy of `project-config.json` (write-back happens in Phase 5). If the answer is "still defer" or empty, record as `TBD` and proceed — that stack × concern will produce no rules in Phase 4, and constitution's corresponding bullet will read `_Deferred — rerun {{cli.sigil}}constitute after deciding_`.

## PHASE 3: Interview

Two to three questions scoped to what wizard + onboard didn't capture. Use your runtime's natural question mechanism.

### Q-strict: Strictness Level (always asked)

> How strict should the project's coding rules be?
>
> - **Maximum** — zero tolerance. No escape-hatch types (`any`, `unsafe`, `dynamic`), all public APIs fully typed, tests required for every non-trivial function, no `TODO` without a tracked issue, no `@ts-ignore` / `// nolint` without comment explaining why.
> - **High** — occasional escape hatch with explicit justification in a comment, tests for business logic, strict lint config enforced.
> - **Moderate** — pragmatic. Strict where it matters (domain logic, public APIs), relaxed where it doesn't (scripts, tests, prototypes).

Store as `STRICTNESS`. This modulates how aggressive the ALWAYS / NEVER / PREFER rules are in Phase 4.

### Q-naming (conditional, per category): Naming Conventions

For each of four naming categories (types, functions / methods, files, constants), decide independently:

- **If onboard observed a clear pattern for THIS category** (memory or `docs/architecture.md` explicitly names it — e.g., "all types PascalCase, observed in `src/domain/` and `src/features/`"): use the observed convention with `[extracted]` tag. Skip the question for this category.
- **Otherwise** (greenfield, onboard skipped, or onboard findings are silent / inconsistent for this category): ask the user:

> For [category: types / functions / files / constants] in [LANGUAGES], should I use:
>
> - **Language / framework defaults** — I'll apply the idiomatic convention (e.g., PascalCase types, camelCase functions, kebab-case or snake_case files per language, SCREAMING_SNAKE constants)
> - **Custom** — specify your preference

Collect answers per category; store as `NAMING_CONVENTIONS` with keys `types`, `functions`, `files`, `constants`. Skip categories that onboard already resolved.

### Q-domain (conditional): Key Domain Entities

**Skip this question if domain entities are already available from any source:**

- Brownfield WITH onboard: extracted from `docs/features/*.md` Key Types sections and `docs/architecture.md` Key Domain Types.
- Anywhere else: if `.devforge/memory.md` contains a domain-related entry (e.g., under Architecture Decisions).

**Ask this question when domain entities are NOT available from any source:**

- Greenfield / empty (no code to scan).
- Brownfield without onboard (onboard was skipped — Prereq #3's fallback path).

> I have no extracted domain context available. What are the 3–5 key business entities this project manages? (free text, e.g., "User, Order, Invoice, Subscription")
>
> Answer `skip` if the domain isn't clear yet — Section 5 (Domain Rules) will remain minimal with a note to populate during `{{cli.sigil}}specify` runs.

Store as `DOMAIN_ENTITIES` (may be empty).

## PHASE 4: Synthesize Rules

For each `[project-specific]` sentinel section in `constitution.md`, produce rules using the inputs from Phase 1 + answers from Phase 2/3. Tag every rule by its source.

### Rule source tags (every rule MUST have exactly one)

- `[extracted]` — observed in actual code (from onboard findings in `docs/` or `.devforge/memory.md`). **Cite evidence** — file path, module name, or specific observation. A rule claiming `[extracted]` without citation is a fabrication.
- `[convention]` — chosen standard from user answers, framework defaults, or idiomatic practice for the ecosystem.
- `[enforced]` — backed by project tooling (linter, type-checker, CI config, pre-commit hook). **Name the tool + config file** (e.g., `tsconfig.json strict: true`, `.eslintrc.js no-explicit-any`).
- `[recommended]` — suggested best-practice, not project-enforced. Used sparingly for rules the user can override per case.

**Tag precedence when a rule qualifies for multiple:**

A rule is `[enforced]` only if the **specific** rule is enforced by tooling — not if some related rule is. Example: user picks Maximum strictness, generating "no `any`". `tsconfig.json` has `strict: true` but not `noExplicitAny` (that's an eslint-level rule), and the eslint config has no `@typescript-eslint/no-explicit-any`. Tooling enforces general strictness but NOT this specific rule. Tag as `[convention]`, not `[enforced]`.

Precedence — pick the most accurate tag for each rule:

1. `[enforced]` — **only** when the specific rule is backed by tooling (name the config line).
2. `[extracted]` — when observed in code, even if not tool-enforced.
3. `[convention]` — when derived from strictness level, user answers, or framework idioms without tool backing.
4. `[recommended]` — reserved for genuine suggestions the user should consider but where stricter tagging would overstate the commitment.

### Per-section synthesis

**§2.1 Layer Boundaries** — derive from `ARCHITECTURES[i]` per stack. Each named pattern (hexagonal / ports-and-adapters, clean, layered, MVC, feature-sliced, etc.) has a canonical layer shape. Name the layers the project's architecture implies; state allowed import directions. For brownfield, cite `docs/architecture.md`'s module map.

**§2.2 File Organization** — from architecture pattern + observed folder structure (brownfield) or framework defaults (greenfield). State where new files of each type go (services, repositories, domain entities, components, views, etc., per the language/framework).

**§2.3 Dependency Rules** — from architecture's layer constraints + any circular-dep or tight-coupling warnings onboard flagged in `.devforge/memory.md`. Specify which modules/layers can import from which; which crossings are forbidden.

**§3.1 Type Safety** — modulate by `STRICTNESS` × primary language:
- Maximum TS: "No `any`; use `unknown` and narrow. No `@ts-ignore`. All exports typed."
- Maximum Python: "Type hints on all public functions; `mypy --strict` on domain modules; no `Any` without justification."
- Maximum Rust: "No `unsafe` blocks without a `// SAFETY:` comment; no `.unwrap()` in non-test code — use `?` or explicit handling."
- Moderate variant of each: relaxed where it doesn't matter.
- Include per-language rules in multi-stack projects (one bullet group per stack under a language sub-header).

**§3.2 Error Handling** — wizard filled the top-line (`{{ERROR_HANDLING}}`). Add body details: how errors are created / propagated / surfaced per stack. For brownfield: cite observed patterns from `docs/architecture.md` "Error Handling" subsection if onboard populated it.

**§3.3 Naming Conventions** — from Q-naming answer + `LANGUAGES`. Concrete rules per language in multi-stack projects.

**§3.4 Testing Requirements** — wizard filled the top-line (`{{TESTING}}`). Add body details: what must be tested (modulated by STRICTNESS), where tests live, naming conventions for test files, setup/teardown patterns if observed.

**§4.1.1 ALWAYS Do** — 5–10 concrete DO rules. Draw from framework idioms × strictness × onboard observations. Every rule tagged.

**§4.2.1 NEVER Do** — 5–10 concrete DON'T rules. Same tagging approach.

**§4.3.1 PREFER** — 3–7 preference rules (softer than ALWAYS/NEVER; can be overridden with justification).

**§5 Domain Rules** — brownfield: extract from `docs/features/*.md` Key Types and Invariants. Greenfield: use `DOMAIN_ENTITIES` from Q-domain if provided; otherwise render a minimal stub: `_Will be populated during {{cli.sigil}}specify runs as features get built — no domain context available at constitute time._`

**§6.5 Deprecation Handling** — brownfield: check `docs/` or memory for existing deprecation patterns. If none observed, use language conventions (TS: JSDoc `@deprecated` + removal version; Python: `warnings.warn(DeprecationWarning)`; Rust: `#[deprecated(since=..., note=...)]`; etc.). Tag `[convention]` when unobserved.

**§6.6 Project-Specific Workflow** — derive from `WORKFLOW_ENFORCEMENT` + any CI/CD patterns onboard observed. Keep short — don't duplicate the command flow documented in the runtime primer (`{{cli.primer}}`); add only project-specific workflow deviations here.

**§7 Scaffolding Guide (greenfield only)** — propose a directory structure based on `ARCHITECTURES[0]` + `FRAMEWORKS[0]`. Include:
- Proposed initial directory tree
- First-files-to-create list — order matters and **depends on the architecture pattern** chosen (`ARCHITECTURES[0]`). Common orderings:
  - **Clean / hexagonal / layered**: domain / types → data layer → business logic → UI or entry points
  - **MVC**: models → controllers → views
  - **Feature-sliced** (frontend): shared / entities → features → widgets → pages
  - **Event-driven**: event schemas → handlers → emitters / consumers
  - **Actor model**: actors + messages → supervisors → entry points
  - **Microservices**: service boundaries + API contracts → per-service internals
  - **Flat / simple / unopinionated**: entry point first, then feature-by-feature as needed
  
  For an architecture not listed above, propose an order that respects the pattern's own dependency direction (things depended-on first, things depending last) and name the pattern you're applying. Do NOT default to the clean-architecture order for an arbitrary pattern.
- Pattern reference (one concrete example per chosen pattern)
- "When to re-constitute" note: run `{{cli.sigil}}constitute` again when the project reaches 20+ source files to replace convention-based rules with extracted ones from the then-existing codebase.

For brownfield, **omit §7 entirely** — the project is already scaffolded.

### Multi-stack handling

For `len(LANGUAGES) > 1`: produce per-stack rule blocks within each section where rules diverge (type safety, naming, layer boundaries — these vary per language). Cross-stack rules (workflow enforcement, deprecation strategy at the project level) go once without stack labels.

## PHASE 5: Populate `constitution.md`

Write the synthesized rules into constitution.md's body sections. Branch on the operation mode captured in Phase 1 Step 2:

1. **Fresh-fill mode**: replace each `_Run constitute to populate_` sentinel (and its variants like `_Run constitute to populate with language-specific type rules_`, `_Run constitute to populate details_`) with the synthesized content for that section. Sections without sentinels remain untouched.
2. **Full-rewrite mode**: overwrite every `[project-specific]` body section's content with the newly synthesized rules, regardless of its previous state. Preserve section headings, subsection numbers, and `[project-specific]` section tags — only the body content changes.
3. In both modes, preserve section headings, subsection numbers, and `[project-specific]` section tags.
4. Do NOT touch `[universal]` sections (§3.5, §3.6, §3.7, §4.1, §4.2, §4.3, §6.1, §6.2, §6.3, §6.4). They're installed verbatim and apply to every project.
5. Do NOT rewrite the header (§1 Project Identity) — wizard owns that.
6. Every rule must carry its source tag (`[extracted]` / `[convention]` / `[enforced]` / `[recommended]`).
7. Update the `Last updated:` line near the top of the file to today's ISO-8601 date.

If any Phase 2 TBD resolutions happened, write the updated `project-config.json` too (preserve all other fields; only update the ones you resolved).

## PHASE 6: User Review Gate

**Do not consider the command complete until the user explicitly approves.** Show the result and wait.

Present a summary:

```
## Constitution Draft

Populated [N] sections with [M] rules total:
- §2.1 Layer Boundaries: [count] rules ([breakdown by tag, e.g., "3 extracted · 2 convention"])
- §2.2 File Organization: [count] rules
- §2.3 Dependency Rules: [count] rules
- §3.1 Type Safety: [count] rules
- §3.2 Error Handling details: [count] rules
- §3.3 Naming Conventions: [count] rules
- §3.4 Testing Requirements details: [count] rules
- §4.1.1 ALWAYS: [count] rules
- §4.2.1 NEVER: [count] rules
- §4.3.1 PREFER: [count] rules
- §5 Domain Rules: [count] rules (or "minimal — will grow during /specify")
- §6.5 Deprecation: [count] rules
- §6.6 Workflow: [count] rules
- §7 Scaffolding (greenfield only): included / omitted

Rule sources:
- [extracted]: [count] (from onboard scan)
- [convention]: [count] (from user answers + framework idioms)
- [enforced]: [count] (backed by project tooling)
- [recommended]: [count] (best-practice suggestions)
```

Then ask the user:

> Review the constitution at `constitution.md`. How should I proceed?
>
> - **Accept** — constitution is ready; finalize
> - **Revise section X** — name a section AND describe what should change (e.g., "§4.2.1 NEVER — add a rule about avoiding callbacks, prefer async/await" or "§3.1 Type Safety — too strict, reduce to High-level rules"). I'll regenerate that section incorporating your feedback.
> - **Abort** — discard the draft; constitution reverts to its pre-`{{cli.sigil}}constitute` state (sentinels restored)

Wait for the user's choice. On **Accept** → Phase 7. On **Revise** → capture the user's feedback as additional synthesis input; re-enter Phase 4 for the named section only, incorporating the feedback on top of Phase 1–3 inputs; then re-present. If the user revises the same section repeatedly, feedback accumulates — don't lose earlier feedback on the next revise round. On **Abort** → restore the body content you held in memory at Phase 1 step 2; report "aborted — no changes written" and exit.

## PHASE 7: Summary

Present to the user:

```
## Constitution Established

### Sections populated
[Brief one-line summary per populated section]

### Rule inventory
- [extracted]: [N]   (observed from scan)
- [convention]: [N]  (user answers + framework idioms)
- [enforced]: [N]    (backed by tooling — cite which)
- [recommended]: [N] (best-practice suggestions)

### Files updated
- `constitution.md` — [project-specific] sections filled; [universal] sections untouched
- `.devforge/project-config.json` — [only if Phase 2 resolved TBDs — list which ones]

### Next Steps
1. Review `constitution.md` and adjust any rules as needed
2. Start working with `{{cli.sigil}}specify "your first feature"`

All downstream commands now consult these rules when making decisions.
```

## IMPORTANT RULES

1. **Read, don't scan** — this command consumes wizard + onboard output; it does NOT walk the codebase itself. If brownfield data is missing, ask the user rather than re-scanning.
2. **Never modify `[universal]` sections** — those are installed verbatim. Your write scope is `[project-specific]` body sections only. In Fresh-fill mode that means sections carrying `_Run constitute to populate_` sentinels; in Full-rewrite mode that means every `[project-specific]` body section regardless of sentinel state. Either way, `[universal]` sections are off-limits.
3. **Never rewrite Section 1 Project Identity** — name, type, framework, language, workspace mode, source root are owned by setup-wizard. Only the `Last updated:` line at the very top of the file gets modified (to today's date, per Phase 5 Step 7).
4. **Every rule carries a source tag** — `[extracted]` / `[convention]` / `[enforced]` / `[recommended]`. No untagged rules.
5. **Cite evidence for `[extracted]` rules** — file path, module name, or specific observation from onboard findings. A rule claiming `[extracted]` without citation is a fabrication; downgrade to `[convention]` if the observation is thin.
6. **Name the tool for `[enforced]` rules** — which lint config, which type-checker option, which CI check. A rule tagged `[enforced]` without a named enforcement mechanism is ambiguous.
7. **Strictness modulates rule strength** — Maximum produces more NEVER rules and tighter type-safety; Moderate leans toward PREFER with room for judgement.
8. **Multi-stack projects get per-stack blocks** — type safety, naming, layer boundaries vary per language. Render per-stack within each section (one sub-block per stack under a language sub-header).
9. **User review is blocking** — do NOT consider the command complete until the user explicitly approves the draft. The review gate is a contract, not a suggestion.
10. **Abort must be non-destructive** — hold the original constitution body content in memory before Phase 5 writes. On abort, restore it fully; no partial state.
