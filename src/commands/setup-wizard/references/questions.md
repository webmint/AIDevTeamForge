# Phase 2 — Questions

This reference covers the interactive Q&A phase of the setup-wizard flow, loaded by the wizard orchestrator when Phase 2 executes. Walk the user through Q0 → Q11 in order; later questions depend on earlier answers. Phase 1 detection outputs live in `.devforge/detection_report.yaml` (composed by `scripts/lib/detect_report` at the end of Phase 1) — read fields from that file when presenting findings. The Phase 2 preflight section below covers this explicitly.

## Outputs to retain in conversational memory

Each question stores its answer under a specific key (detailed in the question body). Top-level keys produced by this phase:

- `PROJECT_NAME` (Q0)
- `PROJECT_DESCRIPTION` (Q1)
- `PROJECT_TYPE` (Q2)
- `LANGUAGES`, `FRAMEWORKS`, `PRIMARY_LANGUAGE` (Q3 — confirms/overrides Phase 1 detection)
- `ARCHITECTURES` (Q4 — array parallel to `LANGUAGES` / `FRAMEWORKS`; each element is the pattern for that stack or `"TBD"` if deferred)
- `ERROR_HANDLINGS` (Q5 — array parallel to `LANGUAGES` / `FRAMEWORKS`; each element is the convention for that stack or `"TBD"` if deferred)
- `API_LAYERS` (Q6 — array parallel to `LANGUAGES` / `FRAMEWORKS`; each element is the API style for that stack, `"N/A"` if that stack has no API layer, or `"TBD"` if deferred)
- `TESTINGS` (Q7 — array parallel to `LANGUAGES` / `FRAMEWORKS`; each element is the testing framework for that stack, `"N/A"` if no testing, or `"TBD"` if deferred)
- `WORKFLOW_ENFORCEMENT` (Q8)
- `AI_ATTRIBUTION` (Q9)
- `CLAUDE_TIER_THINK`, `CLAUDE_TIER_DO`, `CLAUDE_TIER_VERIFY` (Q10a)
- `CODEX_TIER_THINK`, `CODEX_TIER_DO`, `CODEX_TIER_VERIFY`, optional `CODEX_TIER_*_MODEL` overrides (Q10b)
- `AC_VERIFICATION_MODE` (Q11)
- `AC_RUNTIME_URL` / `AC_RUNTIME_API_BASE` / `AC_RUNTIME_CLI_COMMAND` (Q11 conditional, depending on mode + project type)

All collected answers are written to `.devforge/project-config.json` during Phase 3; `.devforge/project-config.json` is the canonical answers record read by every downstream command and by `update.sh`.

---

## How to run this phase

Present what you detected in Phase 1 in a clear summary (or, if `PROJECT_STATE` is empty, skip the summary and go straight to questions). Walk the user through each question in order (Q0 → Q11; later questions depend on earlier answers). Every question is labeled with exactly one of three markers:

- **REQUIRED** — must be answered. Offer **confirm / override**. Defer is not allowed; downstream commands depend on the value.
- **OPTIONAL** — user may answer or explicitly defer. Offer **confirm / override / defer**. "Defer" marks the field as `TBD` and downstream commands will ask when the field becomes relevant (e.g., when `/specify` needs an architecture decision for a specific feature). A small number of OPTIONAL questions are free-text only (e.g. "anything else I should know?") — those are noted explicitly and allow an empty response.
- **CONDITIONAL** — may not apply to this project. If it doesn't apply, skip it and record the natural default (this is the one case where a silent default is permitted; the marker acknowledges it). If it does apply, treat as REQUIRED (confirm / override — no silent guess).

For every question that applies, do NOT silently default. Do NOT infer answers. The user's confirmed answers are the canonical input across all runtimes — that's what keeps outputs consistent between Claude, Codex, and any future runtime.

**Anti-hallucination rule for findings.** When presenting findings to the user (anywhere you'd fill `[findings]`, `[observed indicators]`, `[pattern indicators]`, `[detected framework]`, etc.), quote ONLY concrete observed facts: exact file paths, exact package names, exact config keys, exact imports or symbols you actually read. Do NOT invent indicators to make the prose flow. If detection surfaced nothing for a category, say so plainly (e.g. "I found no framework dependencies, so I can't infer the stack — could you tell me what you're using?") instead of fabricating plausibles.

**Where answers are stored.** As you walk through the questions below, track the user's answers in your working context. At the end of the wizard, every collected answer is written to `.devforge/project-config.json`. That file is the canonical record — every command under every CLI (Claude, Codex, and later runtimes), plus `update.sh`, reads from it. Use the variable names noted in each question (e.g. `SOURCE_ROOT`, `PROJECT_NAME`, `CLAUDE_TIER_THINK`) as the keys.

## Phase 2 preflight

Before asking Q0, read `.devforge/detection_report.yaml`. That file is the output of Phase 1's `scripts/lib/detect_report compose` call (see `references/detect.md` → "Detection Report — Phase 1 output"). If the file is missing or empty, Phase 1 didn't complete — return to `references/detect.md`, run the Phase 1 detection + composition flow, then start Phase 2.

Q0 through Q11 read Report fields directly from the YAML file for their defaults:
- Q0 (project name) → `detection_report.packages[0].manifest` + `name` field
- Q1 (description) → README content read during Phase 1
- Q3 (languages / frameworks) → `detection_report.languages` + `.frameworks`
- Q4 (architecture) → `detection_report.architecture_shape` + `.architecture_evidence`
- Q5 (error handling) → `detection_report.error_handling`
- Q6 (API layer) → `detection_report.api_client`
- Q7 (testing) → `detection_report.test_runner`
- Q11 runtime URL → `detection_report.runtime_url`

Without the Report file, these reference-based defaults fall back to re-asking or guessing, which pollutes `project-config.json` with values the user didn't actually consent to.

**General rule for Report-referenced questions.** For every question listed above with a Report counterpart, the flow is: read the Report field from `.devforge/detection_report.yaml` → present its value as the default → ask the user to confirm or override. This applies even when the question's own prose describes a fallback detection path — the Report field is the primary source; the fallback runs only when the Report field is `null` or explicitly flagged as a low-confidence default (e.g., `source: framework-default` on `runtime_url`). Never skip the Report and jump straight to fallback detection — that re-opens the runtime-to-runtime drift surface the Report was designed to close.

## Question 0: Project Name (REQUIRED)

**If a manifest file exists at SOURCE_ROOT** (`package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `pubspec.yaml`, `*.csproj`, `mix.exs`, `deno.json`, or equivalent) **and contains a name field:**

> I found the project name `[detected name]` in `[manifest file]`. Confirm or override.

**If no manifest or no name field:**

> What is this project called?

Store as `PROJECT_NAME`.

## Question 1: Project Description (REQUIRED)

**If README.md (or README.rst, README.txt) exists at SOURCE_ROOT and contains a meaningful description (not just a scaffolded heading):**

> I found this in your README:
>
> > [quote the first paragraph or summary section — max ~3 sentences]
>
> Does this describe the project well? Confirm, or give me a better description in 1-3 sentences — what does it do, who is it for?

**If no README or README is empty/boilerplate:**

> Describe this project in 1-3 sentences — what does it do, who is it for?

Store as `PROJECT_DESCRIPTION`. This is placed in the Project Overview section of CLAUDE.md / AGENTS.md and gives every downstream command and agent domain context for design decisions, naming, error messages, and UX choices.

## Question 2: Project Type (REQUIRED)

Present the question to the user. If Phase 1 detection surfaced concrete indicators, quote them explicitly; if nothing was detected (or `PROJECT_STATE` is empty), say so plainly and just ask. Do not invent.

**If concrete indicators were found:**

> Based on what I found — [quote 2–5 specific observed facts: exact dep names, exact file paths, exact config markers] — this looks like a [proposed type]. What type of project is this?
>
> Options:
> - Frontend / web application
> - Backend API / service
> - Full-stack web application
> - Mobile application (native or cross-platform)
> - Desktop application (Electron, Tauri, native)
> - CLI tool / script
> - Library / package / SDK
> - Plugin / extension / add-on
> - Data pipeline / ETL / batch job
> - ML / data science / AI model
> - Game
> - Infrastructure-as-code / config management
> - Documentation / static site
> - Other — user describes their own category (e.g., "firmware", "Figma plugin", "browser extension", "Slack bot")

**If nothing was detected (empty / greenfield / unclear):**

> I couldn't detect enough from the files alone to guess. What type of project is this?
>
> Options: [same list as above]

## Question 3: Languages & Frameworks (REQUIRED)

**If the project is empty (`PROJECT_STATE == "empty"` — Phase 1 detection was skipped):**

> This project is empty — I have no detected languages or frameworks to confirm. What languages and frameworks will you use?
>
> Options:
> - Name a single language + framework (e.g., "TypeScript with Next.js" for a frontend-only project)
> - Name multiple languages + frameworks (e.g., "TypeScript with Next.js + Python with FastAPI" for a planned monorepo), then indicate the primary language for downstream defaults
> - List the languages; skip framework for any you haven't decided yet (use `null` — downstream commands will ask when needed)

Accept free-text. After capture, apply the **Array re-sync on Q3 override** rules below (treat this as the "add a language" case, starting from an empty set) so per-stack arrays `BUILD_TOOLS`, `BUILD_COMMANDS`, `TYPE_CHECK_COMMANDS`, `LINT_COMMANDS` get populated with language defaults for each declared language. This ensures downstream phases have consistent data even though Phase 1 detection produced nothing.

**If a single language dominates:**

> I found [language] with [framework]. Confirm, override, or describe if different.

**If multiple languages are present (monorepo, polyglot, cross-platform):**

> I found multiple languages, ordered by approximate file count aggregated across all detected packages:
> - [language 1] (~[n] files, [m] package(s)) with [framework 1]
> - [language 2] (~[n] files, [m] package(s)) with [framework 2]
> - ...
>
> **Ordering note**: file counts are summed per-language across every detected package (apps, services, shared libraries). Large dependency-like or generated-SDK packages can inflate a language's count without reflecting project priority — if your critical stack looks outranked by a bulkier one, override.
>
> The first in the list is treated as the project's "primary" language for downstream defaults (default agent, default type-check command, etc.). Commands still operate correctly on files in other languages — "primary" only controls what to pick when no file or context is specified.
>
> Options:
> - Confirm this ordering
> - Override — reorder, or specify a different primary

Store as:
- `LANGUAGES` = ordered array of detected language strings (e.g. `["TypeScript", "Python"]`)
- `FRAMEWORKS` = parallel array; each element is the dominant framework for the language at the same index (or `null` if none)
- `PRIMARY_LANGUAGE` = first element of `LANGUAGES` (or the user's explicit pick if they overrode the ordering)

Accept free-text for override — no hardcoded framework list.

**Array re-sync on Q3 override** — whenever the user's Q3 answer changes `LANGUAGES` from what Phase 1 detected, re-align ALL per-stack arrays populated by Phase 1 (`FRAMEWORKS`, `BUILD_TOOLS`, `BUILD_COMMANDS`, `TYPE_CHECK_COMMANDS`, `LINT_COMMANDS`) before continuing to Q4:

- **Reorder** (same languages, different ordering): reindex every parallel array so `<ARRAY>[i]` matches the language at `LANGUAGES[i]` in the new ordering. Preserve each value verbatim — only indices change.
- **Remove a language** (e.g., user says "ignore this one, it's a generated SDK"): drop the element at that index from every parallel array.
- **Add a language** (user declares a language not in Phase 1 detection): append an entry to every parallel array. For the new language's per-stack command/tool entries (`BUILD_TOOLS`, `BUILD_COMMANDS`, `TYPE_CHECK_COMMANDS`, `LINT_COMMANDS`), populate each per the "Per-stack tool detection" section in `references/detect.md` — priority step 2.2 (language's standard ecosystem default, using the guiding examples + your training knowledge). For `FRAMEWORKS`, use `null` unless the user also specified a framework for the new language. Mark the added-language values as greenfield-defaults (no manifest to confirm).

After re-sync, the following invariant MUST hold: `len(LANGUAGES) == len(FRAMEWORKS) == len(BUILD_TOOLS) == len(BUILD_COMMANDS) == len(TYPE_CHECK_COMMANDS) == len(LINT_COMMANDS)`. Q4-Q7 per-stack iteration and Phase 3's `PACKAGE_STACKS` aggregation depend on this invariant. Also update `PRIMARY_LANGUAGE` to the new `LANGUAGES[0]` after any reorder.

## Question 4: Architecture Pattern (OPTIONAL)

Stored as `ARCHITECTURES` — an array parallel to `LANGUAGES` / `FRAMEWORKS`. Each element is the architecture pattern for the stack at that index (e.g., `"hexagonal"`, `"feature-sliced"`) or `"TBD"` if deferred. Branch on `len(LANGUAGES)`.

### Single-stack (`len(LANGUAGES) == 1`)

Ask once, producing `ARCHITECTURES = [answer]` (array of length 1).

**If detection identified a pattern with reasonable confidence (existing project):**

> I see [specific folders/files you observed]. This looks like [detected pattern]. Confirm, override, or defer.
>
> Options:
> - Confirm: [detected pattern]
> - Override — name a different pattern
> - Defer — establish the pattern as the project evolves

**If detection was uncertain or the project has no clear pattern (existing project):**

> I scanned the code but couldn't identify a clear architecture pattern. Which does this project follow?
>
> Options:
> - Name a pattern (e.g., Clean Architecture, MVC, feature-modular, hexagonal, layered, flat)
> - Defer — establish the pattern as the project evolves

**If the project is empty or greenfield:**

> Which architecture pattern do you want to follow?
>
> Options:
> - Name a pattern (Clean Architecture, MVC, feature-modular, hexagonal, etc.)
> - Defer — decide as features get built

### Distinguishing Clean Architecture from hexagonal (important)

Three-layer `data/`/`domain/`/`presentation/` splits can look like either Clean Architecture or hexagonal at first glance. Before presenting the detected pattern as `hexagonal`, check for Clean-specific artifacts:

- **`domain/cases/` or `use-cases/` subfolder** within each feature module — this is the Clean-specific artifact (Uncle Bob's use-case layer). Its presence strongly signals Clean, not hexagonal.
- **Repository pattern with interface-in-domain + implementation-in-data split** — data layer implements interfaces declared in domain. This is Clean's dependency inversion.
- **Strict inward dependency direction** — domain imports from nothing; data imports from domain; presentation imports from domain + data adapters. No framework leakage into domain.

When `domain/cases/` OR `use-cases/` subfolder is present alongside the three-layer split, present the detected pattern as **`Clean Architecture`**, NOT `hexagonal`. If the project is ALSO a feature-modular monorepo (packages/* with each package following this split), use **`Clean Architecture, feature-modular monorepo`** as the detected pattern label.

Hexagonal (ports-and-adapters) has a similar three-layer shape but without the use-case layer — domain services are the unit of interaction, not explicit use-case classes. When in doubt and `cases/` is absent, presenting the option as "hexagonal-style" is acceptable, but when `cases/` is present, do not call it hexagonal.

### Multi-stack (`len(LANGUAGES) > 1`)

First, offer the cross-stack shortcut — many monorepos apply the same architectural convention across stacks (e.g., "everything is hexagonal"):

> You have [N] stacks:
> 1. [LANGUAGES[0]] / [FRAMEWORKS[0]]
> 2. [LANGUAGES[1]] / [FRAMEWORKS[1]]
> ...
>
> Does the same architecture pattern apply across all stacks?
>
> Options:
> - Yes, same pattern for all — I'll ask once
> - No, different per stack — I'll ask per stack
> - Defer all — establish the patterns as the project evolves

**If "Yes, same for all":** no per-stack scan is needed for architecture (Q4 doesn't have a per-Q scan step — detection happens at Phase 1). Ask the empty/greenfield variant from the Single-stack section once (detection hints from Phase 1 are per-stack; mixing them into a single-answer form is misleading). Replicate the answer: `ARCHITECTURES = [answer] * N` where N is the number of stacks.

**If "No, different per stack":** iterate through stacks in order. For each stack `i` from 0 to N-1:

> For stack [i+1]/[N] — [LANGUAGES[i]] / [FRAMEWORKS[i]]:
> [then present the appropriate detected/uncertain/greenfield variant from the Single-stack section above, tailored to this stack's detection state]

**Note on per-stack detection hints:** Phase 1 architecture detection typically produces ONE project-wide hint (e.g., "this looks hexagonal" based on a scan of top-level folders), not one hint per stack. If no stack-specific hint is available for stack `i`, present the **empty/greenfield variant** for that stack rather than inventing a per-stack detected pattern. If Phase 1's project-wide hint seems to fit one stack but not others, mention it in the first iteration only and let the user confirm or override per-stack — do NOT reuse the project-wide hint as "detected" confidence for every stack.

Store each answer as `ARCHITECTURES[i]`. Individual stacks may be deferred independently — a deferred stack contributes `"TBD"` to `ARCHITECTURES[i]` while others carry real values.

**If "Defer all":** `ARCHITECTURES = ["TBD"] * N`. No per-stack iteration.

## Question 5: Error Handling Convention (OPTIONAL)

Error handling is typically project-specific, not just language-specific. Even in languages with a dominant default (Go's `(value, error)` returns, Python's exceptions, Rust's `Result<T, E>`), projects commonly layer library-level conventions on top — `pkg/errors` / `hashicorp/go-multierror` for Go; `returns` / `rustedpy/result` for Python; `anyhow` / `thiserror` / `eyre` for Rust; Either-style libraries or custom error hierarchies for TypeScript; etc.

Stored as `ERROR_HANDLINGS` — an array parallel to `LANGUAGES` / `FRAMEWORKS`. Each element is the error-handling convention for the stack at that index, or `"TBD"` if deferred. Branch on `len(LANGUAGES)`.

### Single-stack (`len(LANGUAGES) == 1`)

Before asking, **retrieve the error-handling observations Phase 1 captured** (from the brownfield source-file scan in `detect.md` STEP 3 — 8-10 file sample with specific file-path + indicator citations). If Phase 1's scan surfaced concrete patterns, quote them here. If Phase 1 didn't surface anything (empty / greenfield project, or brownfield scan found no clear pattern), present the "Empty / greenfield" variant below without fabricating observations. Store the answer as `ERROR_HANDLINGS[0]`. Do NOT re-scan source files here — Phase 1 is the authoritative source. Anti-hallucination rule applies.

**Existing projects:**

> I saw [specific imports or patterns observed in source, e.g. `thiserror` derives on error types in `src/error.rs`, `?` operator throughout]. How does this project handle errors?
>
> Options:
> - Confirm: [your summary of what you saw]
> - Override — name a different convention
> - Defer — establish the pattern as the project evolves

**Empty / greenfield projects:**

> How should this project handle errors?
>
> Options:
> - Name a convention (e.g. "language default", "`thiserror` + `?` for Rust", "`returns` Result in Python", "Either/Result via neverthrow", "HTTP-codes at boundary + typed results internally")
> - Defer — decide during the first spec

### Multi-stack (`len(LANGUAGES) > 1`)

Error handling is heavily language-bound — Python exceptions, TS discriminated unions, Go tuples, Rust `Result<T, E>` are structurally different. Most multi-stack projects have different conventions per stack. Offer the shortcut anyway for cross-cutting conventions (e.g., "everything returns problem+json at the HTTP boundary regardless of language"):

> You have [N] stacks:
> 1. [LANGUAGES[0]] / [FRAMEWORKS[0]]
> 2. [LANGUAGES[1]] / [FRAMEWORKS[1]]
> ...
>
> Does the same error-handling convention apply across all stacks?
>
> Options:
> - Yes, same convention for all — I'll ask once
> - No, different per stack — I'll ask per stack
> - Defer all — establish conventions as the project evolves

**If "Yes, same for all":** skip the per-stack scan — the user is declaring a cross-stack convention, not confirming per-stack observations. Ask the greenfield variant from the Single-stack section once. Replicate: `ERROR_HANDLINGS = [answer] * N`.

**If "No, different per stack":** iterate through stacks in order. For each stack `i` from 0 to N-1:

1. **Use Phase 1's findings** as the primary source (from `detect.md` STEP 3's brownfield source-file scan). Phase 1 typically produces project-wide hints, not per-stack — so in the "different per stack" case, fall back to the empty/greenfield variant when no stack-specific evidence exists. If Phase 1 mentioned specific observations tied to a particular stack's language (e.g., "`thiserror` in `src/error.rs`" from a Rust-only file path), use those for that stack's iteration. **Lightweight supplemental scan** (optional): if you need additional per-stack evidence not covered by Phase 1 — e.g., to confirm a library the user has in only one package — read 1-2 files scoped to that stack's language (respect the 8-10 file cumulative cap from Phase 1; don't re-scan everything). Do NOT re-run Phase 1's full brownfield scan.
2. **Present**:

> For stack [i+1]/[N] — [LANGUAGES[i]] / [FRAMEWORKS[i]]:
> [then present the appropriate existing/greenfield variant from the Single-stack section above, using Phase 1 findings or the lightweight supplemental scan above]

Store each answer as `ERROR_HANDLINGS[i]`. Individual stacks may be deferred independently — a deferred stack contributes `"TBD"` to `ERROR_HANDLINGS[i]` while others carry real values.

**If "Defer all":** `ERROR_HANDLINGS = ["TBD"] * N`. No per-stack scan, no per-stack iteration.

## Question 6: API Layer (OPTIONAL)

Stored as `API_LAYERS` — an array parallel to `LANGUAGES` / `FRAMEWORKS`. Each element is the API style for that stack (e.g., `"REST"`, `"GraphQL"`, `"tRPC"`, `"gRPC"`, `"WebSocket"`), `"N/A"` if that stack has no API layer (pure library, CLI tool, static site), or `"TBD"` if deferred. Branch on `len(LANGUAGES)`.

### Single-stack (`len(LANGUAGES) == 1`)

Ask once, producing `API_LAYERS = [answer]` (array of length 1).

**If detection identified an API style with reasonable confidence (existing project):**

> I see [specific signals observed, e.g. `@trpc/client` imports, FastAPI route decorators in `app/routes/*.py`, apollo-client v3]. This looks like [detected style]. Confirm, override, or defer.
>
> Options:
> - Confirm: [detected style]
> - Override — name a different style (REST, GraphQL, tRPC, gRPC, WebSocket, SOAP, custom, N/A)
> - Defer — establish as the project evolves

**If detection was uncertain or the project has no clear API style (existing project):**

> I scanned the code but couldn't identify a clear API layer. Which does this project use?
>
> Options:
> - Name a style (REST, GraphQL, tRPC, gRPC, WebSocket, SOAP, custom)
> - N/A — this project has no API layer
> - Defer — establish as the project evolves

**If the project is empty or greenfield:**

> Which API layer will this project use?
>
> Options:
> - Name a style (REST, GraphQL, tRPC, gRPC, WebSocket, SOAP, custom)
> - N/A — no API layer (pure library, CLI tool, static site)
> - Defer — decide during the first spec

### Multi-stack (`len(LANGUAGES) > 1`)

API layer is often uniform across stacks (e.g., BE exposes REST, FE consumes REST). But monorepos with multiple BE services or BFF layers may legitimately differ. Offer the shortcut:

> You have [N] stacks:
> 1. [LANGUAGES[0]] / [FRAMEWORKS[0]]
> 2. [LANGUAGES[1]] / [FRAMEWORKS[1]]
> ...
>
> Does the same API layer apply across all stacks?
>
> Options:
> - Yes, same API style for all — I'll ask once
> - No, different per stack — I'll ask per stack (some stacks may have no API layer)
> - Defer all — establish as the project evolves

**If "Yes, same for all":** the user is declaring a cross-stack convention (not confirming per-stack detected API styles), so use the **greenfield variant** from the Single-stack section once. Replicate: `API_LAYERS = [answer] * N`. If the user answers `"N/A"` in the same-for-all case (no stack has an API), record `API_LAYERS = ["N/A"] * N`.

**If "No, different per stack":** iterate through stacks in order. For each stack `i` from 0 to N-1:

> For stack [i+1]/[N] — [LANGUAGES[i]] / [FRAMEWORKS[i]]:
> [then present the appropriate detected/uncertain/greenfield variant from the Single-stack section above]

**Note on per-stack detection hints:** Phase 1 API-layer detection typically produces ONE project-wide hint (e.g., "I see `@trpc/client` imports across the repo"), not one hint per stack. If no stack-specific signal is available for stack `i`, present the **empty/greenfield variant** for that stack rather than inventing a per-stack detected API style. If Phase 1's project-wide hint seems to apply to one stack but not others (e.g., `@trpc/client` only appears in the frontend package), mention it once for the relevant stack and let the user confirm or override per-stack.

Store each answer as `API_LAYERS[i]`. Per-stack `"N/A"` is valid (e.g., a shared-library package may have no API while sibling service packages do).

**If "Defer all":** `API_LAYERS = ["TBD"] * N`. No per-stack iteration.

## Question 7: Testing Framework (OPTIONAL)

Stored as `TESTINGS` — an array parallel to `LANGUAGES` / `FRAMEWORKS`. Each element is the testing framework for the stack at that index (e.g., `"pytest"`, `"vitest"`, `"jest"`, `"go test"`, `"cargo test"`, `"JUnit"`), `"N/A"` if that stack has no testing setup, or `"TBD"` if deferred. Testing frameworks are strongly language-bound (pytest requires Python; vitest requires JavaScript/TypeScript; etc.). Branch on `len(LANGUAGES)`.

### Single-stack (`len(LANGUAGES) == 1`)

Before asking, **retrieve the testing-framework observations Phase 1 captured** (from detect.md STEP 3's manifest and per-stack tool detection — the `TESTINGS` per-stack array reflects what Phase 1 inferred from manifests and dev-dependencies). If Phase 1 surfaced a concrete framework, quote it here (manifest path, dev-dep entry). If Phase 1 didn't surface anything (empty / greenfield project, or no test config visible), present the "Empty / greenfield" variant below. Store the answer as `TESTINGS[0]`. Do NOT re-scan manifests here — Phase 1 is the authoritative source. Anti-hallucination rule applies.

**If detection identified a framework with reasonable confidence (existing project):**

> I see [specific signals observed, e.g. `pytest` in `pyproject.toml [tool.pytest]`, `vitest` in `devDependencies`, `*_test.go` files]. This looks like [detected framework]. Confirm, override, or defer.
>
> Options:
> - Confirm: [detected framework]
> - Override — name a different framework
> - Defer — establish as the project evolves

**If detection was uncertain or the project has no clear test framework (existing project):**

> I scanned the project but couldn't identify a test framework. Which does this project use?
>
> Options:
> - Name a framework (pytest, vitest, jest, go test, cargo test, JUnit, RSpec, etc.)
> - N/A — this project has no tests yet
> - Defer — establish as the project evolves

**If the project is empty or greenfield:**

> Which testing framework will this project use?
>
> Options:
> - Name a framework (pytest, vitest, jest, go test, cargo test, JUnit, RSpec, etc.)
> - N/A — no tests planned yet
> - Defer — decide during the first spec

### Multi-stack (`len(LANGUAGES) > 1`)

Testing is heavily language-bound — different stacks typically have different frameworks (pytest for Python, vitest for TS, etc.). Offer the shortcut for cross-cutting conventions (e.g., monorepo where all stacks share one language ecosystem and use the same framework):

> You have [N] stacks:
> 1. [LANGUAGES[0]] / [FRAMEWORKS[0]]
> 2. [LANGUAGES[1]] / [FRAMEWORKS[1]]
> ...
>
> Does the same testing framework apply across all stacks?
>
> Options:
> - Yes, same framework for all — I'll ask once
> - No, different per stack — I'll ask per stack (some stacks may have no tests)
> - Defer all — establish as the project evolves

**If "Yes, same for all":** skip the per-stack scan — the user is declaring a cross-stack convention. Ask the greenfield variant from the Single-stack section once. Replicate: `TESTINGS = [answer] * N`.

**If "No, different per stack":** iterate through stacks in order. For each stack `i` from 0 to N-1:

1. **Use Phase 1's per-stack findings** as the primary source — `TESTINGS[i]` from detect.md STEP 3's per-stack tool detection should already hold the inferred test framework for that stack (from its manifest + dev-dependencies). If `TESTINGS[i]` is set to a concrete value, use it as the "detected" hint. If `TESTINGS[i] == null` (unresolved), present the greenfield variant for that stack. **Lightweight supplemental scan** (optional): if Phase 1's hint was uncertain and you need to confirm (e.g., by checking for `*_test.*` file presence in that package), read the package's manifest plus 1-2 test files — respect the Phase 1 scan cap. Do NOT re-scan across all packages.
2. **Present**:

> For stack [i+1]/[N] — [LANGUAGES[i]] / [FRAMEWORKS[i]]:
> [then present the appropriate detected/uncertain/greenfield variant from the Single-stack section above, using Phase 1 findings or the lightweight supplemental scan above]

Store each answer as `TESTINGS[i]`. Per-stack `"N/A"` is valid (e.g., a shared-types package may have no tests while sibling service packages do).

**If "Defer all":** `TESTINGS = ["TBD"] * N`. No per-stack scan, no per-stack iteration.

## Question 8: Workflow Enforcement Level (REQUIRED)

This controls how many user-approval gates appear in the workflow and how strict post-edit verification is. The underlying verification mechanism varies per runtime — on some runtimes it's automatic after every edit, on others it's an explicit `/verify` step — but the behaviors below are the same regardless.

> How strict should workflow enforcement be?
>
> Options:
> - **Strict** — user approval required at every phase gate (specify → plan → breakdown → execute → verify). Verification runs after every code-writing step.
> - **Moderate** — user approval at spec and task-breakdown gates only. Verification runs after every code-writing step, but running `/verify` explicitly is optional.
> - **Light** — user approval at the initial spec only. Verification runs, but fewer interactive gates.

Recommend Strict for new users. This field is required because it directly shapes downstream command behavior.

Store as `WORKFLOW_ENFORCEMENT`. This value is consumed by every command that has gates (execute-task, specify, plan, breakdown, verify, fix, refactor) — each command reads it from `.devforge/project-config.json` at runtime to decide whether to show approval gates or skip them.

## Question 9: AI Attribution in Commits (REQUIRED)

> Should commits created by the AI assistant include co-author attribution?
>
> Options:
> - No — commits will have no AI attribution (recommended default)
> - Yes — commits will include the trailer: `Co-Authored-By: Claude <noreply@anthropic.com>`

Store as `AI_ATTRIBUTION` — lowercase string `"no"` (default) or `"yes"` (matching populate.md's branch condition for `{{COMMIT_ATTRIBUTION}}` substitution). Case-sensitive — do NOT store as boolean, capitalized string, or other format. Both the question's producer (here) and the consumer (populate.md Phase 3) must agree on this format.

## Question 10: Agent Model Assignments (per-runtime)

Specialized agents are grouped into three tiers based on the reasoning they require. Ask the sub-question for each runtime actually present in this install (see presence guards below). Use **confirm / override / defer** semantics from the preamble above — don't silently default.

**Presence guards:** check runtime-specific directories before asking each sub-question:

- Ask **Q10a (Claude model tiers)** only if `.claude/agents/` exists (Claude was included in this install)
- Ask **Q10b (Codex model tiers)** only if `.codex/agents/` exists (Codex was included in this install)
- Both dirs exist (default install, no `--runtime` flag): ask both sub-questions sequentially
- Only one dir exists (single-runtime install via `--runtime claude` or `--runtime codex`): ask only that sub-question; leave the absent runtime's `*_TIER_*` keys as `null` in `.devforge/project-config.json`

This mirrors Phase 3's presence-guard discipline for runtime config files — don't ask users to configure runtimes they didn't install.

**Tiers (shared across runtimes):**

| Tier | Agents | Purpose |
|------|--------|---------|
| **Think** | `architect`, `api-designer`, `security-reviewer` | Design decisions, interface contracts, security analysis — deep reasoning |
| **Do** | `backend-engineer`, `frontend-engineer`, `mobile-engineer`, `db-engineer`, `devops-engineer`, `migration-engineer`, `runtime-debugger`, `performance-analyst`, `design-auditor` | Implementation following established patterns — benefits from speed |
| **Verify** | `code-reviewer`, `ac-verifier`, `qa-engineer` | Code review, AC verification, test generation — understands intent, doesn't design from scratch |

The `tech-writer` agent is hardcoded to a lightweight default regardless of tier choices — documentation generation doesn't benefit from heavier reasoning.

- Under Claude: tech-writer uses `sonnet`.
- Under Codex: tech-writer uses `medium` reasoning effort.

**Key naming convention (uniform across runtimes):** tier values are stored under `{{RUNTIME}}_TIER_{{ROLE}}` (e.g. `CLAUDE_TIER_THINK`, `CODEX_TIER_DO`). The VALUE under each key is runtime-specific — a model name for Claude, a reasoning-effort enum for Codex — but the KEY SHAPE is symmetric so consumers (update.sh, agent materializer, future runtimes) can iterate uniformly. Model-override secondary keys use a `_MODEL` suffix: `CODEX_TIER_THINK_MODEL`.

### 10a: Claude model tiers

Claude exposes three named models: `opus` (heaviest reasoning), `sonnet` (balanced), `haiku` (fastest).

> **Think tier:** opus (default) / sonnet / haiku
> **Do tier:** sonnet (default) / opus / haiku
> **Verify tier:** sonnet (default) / opus / haiku

Recommended defaults: opus / sonnet / sonnet. Store in config as:
- `CLAUDE_TIER_THINK` = model name (e.g. `"opus"`)
- `CLAUDE_TIER_DO` = model name
- `CLAUDE_TIER_VERIFY` = model name

### 10b: Codex model tiers

Codex tunes agent behavior via `model_reasoning_effort` rather than named model tiers. Valid values: `minimal | low | medium | high | xhigh` (with `xhigh` requiring a Responses-API-capable model). Model selection is separate and defaults to the Codex CLI's current default (e.g. `gpt-5.4` or the latest coding-optimized model available at install time).

> **Think tier reasoning effort:** high (default) / xhigh / medium
> **Do tier reasoning effort:** medium (default) / low / high
> **Verify tier reasoning effort:** medium (default) / low / high

Recommended defaults: high / medium / medium. Store in config as:
- `CODEX_TIER_THINK` = reasoning-effort enum (e.g. `"high"`)
- `CODEX_TIER_DO` = reasoning-effort enum
- `CODEX_TIER_VERIFY` = reasoning-effort enum

Override the underlying model per tier only if the user explicitly asks — otherwise leave the Codex default. Store optional overrides as:
- `CODEX_TIER_THINK_MODEL` = model name or `null`
- `CODEX_TIER_DO_MODEL` = model name or `null`
- `CODEX_TIER_VERIFY_MODEL` = model name or `null`

## Question 11: Acceptance Criteria Verification (REQUIRED)

When the user runs `/verify` after a task completes, how should acceptance criteria be checked? The user can pick one mode (simplest — what most projects need) or combine multiple (defense in depth — stronger signal, slower per-task verification).

**Trade-off to surface in the prompt**: each additional mode adds per-task verification time. Runtime-assisted especially adds 10–30s per task for dev-server boot + UI drive. Pick "Multiple" only when multiple signals genuinely matter for this project.

> Options:
> - **Code-only** — verify by reading code against the AC spec. No execution. Works for any project type; safe pick if unsure.
> - **Tests** — run the project's test suite; failures indicate AC violations. Good fit when the project has meaningful tests.
> - **Runtime-assisted** — run the built artifact and interact with it. Good fit when the artifact is easily launchable (web app, backend, CLI) and AC is observable at runtime.
> - **Off** — skip AC verification; user handles manually. Only choose this if the user explicitly wants to opt out.
> - **Multiple** — combine two or three modes (defense in depth). Follow-up asks which.

### Storage (always an array)

`AC_VERIFICATION_MODE` is always stored as a JSON array of strings in `.devforge/project-config.json` — single-mode picks store a one-element array for uniform downstream iteration. Examples:

- Single pick: `["code-only"]`, `["tests"]`, `["runtime-assisted"]`, or `["off"]`
- Multiple pick: `["code-only", "tests"]`, `["tests", "runtime-assisted"]`, or `["code-only", "tests", "runtime-assisted"]`

Valid values inside the array: exactly `"code-only"`, `"tests"`, `"runtime-assisted"`, or `"off"`. No other strings. `"off"` can only appear as a single-element array `["off"]` — it is inherently exclusive of the other modes.

**FORBIDDEN — bare string form:**

```json
"AC_VERIFICATION_MODE": "code-only"   // WRONG — bare string breaks downstream `"runtime-assisted" in AC_VERIFICATION_MODE` checks (substring match instead of membership)
```

**REQUIRED — array form even for one element:**

```json
"AC_VERIFICATION_MODE": ["code-only"]  // CORRECT — uniform array shape for all branches
```

When you write `.devforge/project-config.json` in Phase 3 (populate), the value MUST be a JSON array literal. If you find yourself about to write a bare string, stop and wrap it in `[...]`.

### If the user picks "Multiple"

Ask a follow-up multi-select. `Off` is NOT in the follow-up options — `Off` is inherently exclusive; if the user wanted that they'd have picked it on the first screen:

> Which modes? Select two or three (Runtime-assisted follow-ups will fire if Runtime-assisted is among them):
> - Code-only
> - Tests
> - Runtime-assisted

Use the runtime's multi-select mechanism if available, otherwise ask the user to list the modes they want. Store the selected set as the `AC_VERIFICATION_MODE` array.

### If the user picks a single mode (Code-only / Tests / Runtime-assisted / Off)

Store as a one-element array (e.g., `["code-only"]`). Proceed directly to the mode-specific follow-ups.

### Runtime-assisted follow-ups (only if `"runtime-assisted"` is in `AC_VERIFICATION_MODE`)

Run these follow-ups whenever the `AC_VERIFICATION_MODE` array contains `"runtime-assisted"` — whether Runtime-assisted was picked as the sole mode OR as part of a Multiple combination. Skip them entirely otherwise.

Branch by the project type confirmed in Q2 (not what Phase 1 detected — Q2's answer is canonical). Map Q2's answer to exactly one follow-up branch using the table below; every Q2 option has a defined destination so the wizard never silently skips the follow-up.

**Q2 → follow-up branch mapping:**

| Q2 answer | Follow-up branch |
|---|---|
| Frontend / web application | Web frontend |
| Documentation / static site | Web frontend (served by a dev server in practice) |
| Backend API / service | Backend with HTTP API |
| Full-stack web application | Full-stack web application |
| CLI tool / script | CLI tool |
| Mobile application | Mobile / desktop / game / other non-automatable |
| Desktop application | Mobile / desktop / game / other non-automatable |
| Game | Mobile / desktop / game / other non-automatable |
| Library / package / SDK | **No automatable runtime** (see below) |
| Plugin / extension / add-on | **No automatable runtime** (see below) |
| Data pipeline / ETL / batch job | **No automatable runtime** (see below) |
| ML / data science / AI model | **No automatable runtime** (see below) |
| Infrastructure-as-code / config management | **No automatable runtime** (see below) |
| Other (free text) | ask user for a specific category; if still unclear, fall back to **Code-only** |

**No automatable runtime branch**: for project types where `/verify` has no meaningful runtime artifact to exercise (libraries consumed by other code, plugins hosted by a third-party app, batch jobs without a live server, IaC executed by external runners, ML training with no serving endpoint), inform the user:

> Runtime-assisted verification doesn't fit this project type — there's no launchable artifact `/verify` can drive. I recommend **Tests** (if the project has a test suite) or **Code-only** (otherwise).

Then:

- **Remove `"runtime-assisted"` from the `AC_VERIFICATION_MODE` array** (since it can't apply for this project type).
- If the user picked Runtime-assisted alone (array was `["runtime-assisted"]`), ask them to pick Tests or Code-only and store it as `["tests"]` or `["code-only"]`.
- If the user picked Multiple with Runtime-assisted AND other modes (e.g., `["tests", "runtime-assisted"]`), drop Runtime-assisted and keep the remaining modes (→ `["tests"]`). No additional question needed — the user already explicitly selected the other modes.
- Do NOT store any `AC_RUNTIME_*` key in this branch (frontend URL / API base / CLI command are all runtime-assisted-specific).

For projects that legitimately span multiple categories (e.g., a mobile app with its own backend, or a monorepo containing a web frontend + a CLI + shared libs) and Q2 only captured one of them, ask the user which ONE scope `/verify` should primarily target, then use that branch. Additional scopes require manual verification — note this for the user so they know what's covered vs. not.

**Web frontend:**

Pre-detect a suggested dev-server URL from Phase 1 detection, then ask the user to confirm or override.

**Primary source — Detection Report's `runtime_url` field.** Read `detection_report.runtime_url` from the Phase 1 Detection Report. If `value` is populated AND `source` is not `framework-default`, use it verbatim as the suggested URL and skip the fallback logic below:

> I found your dev server URL at `<runtime_url.value>` (from `<runtime_url.source>`). Confirm or override?
>
> Options:
> - Confirm
> - Override — enter a different URL

Store the confirmed URL as `AC_RUNTIME_URL`.

If the Report's `runtime_url.value` is `null` OR its `source` is `framework-default`, fall through to the fallback logic below — the Report didn't find a concrete dev-server config, so we guess from scripts or framework defaults.

**Fallback pre-detection logic** (use only when the Detection Report's `runtime_url` is `null` or flagged `framework-default` — these signals in order; stop at the first match):

1. **Explicit port flag in scripts**: scan the primary `package.json`'s `scripts.dev` / `scripts.start` for `--port <N>` or `PORT=<N>` — if found, use `<N>`.
2. **Framework defaults** (from detected `FRAMEWORKS[0]` or `PACKAGE_STACKS` for the frontend package):
   - Vite / Vitest → `5173`
   - Next.js → `3000`
   - Angular → `4200`
   - webpack-dev-server → `8080`
   - Remix → `3000`
   - Astro → `4321`
   - SvelteKit → `5173`
   - Nuxt → `3000`
   - Expo (web) → `19006`
3. **Fallback** for unlisted/unknown frameworks: `3000`.

Present the detected URL with its signal source, and ask to confirm:

> I think your dev server will serve the frontend at `http://localhost:<detected-port>` (based on [signal: e.g., `"--port 5173"` in `package.json` dev script / Vite default / Next.js default]). Is that correct?
>
> Options:
> - Confirm
> - Override — enter a different URL (e.g., `http://localhost:8080`)

Store the confirmed URL as `AC_RUNTIME_URL`. Flag for Phase 3 (`references/populate.md`): the wizard needs to add the chrome-devtools MCP server to `.mcp.json` and `.codex/config.toml`.

**Backend with HTTP API:**

Pre-detect a suggested API base URL from Phase 1 detection.

**Pre-detection logic**:

1. **Explicit port flag in scripts**: scan backend manifests (`package.json` scripts for Node backends; `pyproject.toml` / `[tool.poetry.scripts]` for Python; entrypoint files for Go/Rust) for port flags (`--port <N>`, `PORT=<N>`, `-p <N>`, uvicorn's `--port <N>`).
2. **Framework defaults** (from detected `FRAMEWORKS[0]` or `PACKAGE_STACKS` for the backend package):
   - Express / NestJS / Fastify / Hono → `3000`
   - FastAPI / uvicorn / Starlette → `8000`
   - Django → `8000`
   - Flask → `5000`
   - Rails → `3000`
   - Spring Boot / Ktor → `8080`
   - Go standard HTTP → `8080`
   - Actix-web / Axum / Rocket → `8080`
3. **Fallback** for unlisted/unknown frameworks: `8000`.

Present and ask:

> I think your API will serve at `http://localhost:<detected-port>` (based on [signal: e.g., `"uvicorn --port 8000"` / FastAPI default / Express default]). Is that correct?
>
> Options:
> - Confirm
> - Override — enter a different base URL

Store the confirmed URL as `AC_RUNTIME_API_BASE`.

**Full-stack web application:**

Full-stack projects need both the frontend dev URL (for UI-level AC checks via Chrome DevTools MCP) and the backend API base (for endpoint-level AC checks). Run both pre-detections above — frontend URL first, then backend API base — asking the user to confirm each:

> 1. I think your frontend dev server will serve at `http://localhost:<detected-frontend-port>` (based on [signal]). Confirm, or enter a different URL.
> 2. I think your backend API will serve at `http://localhost:<detected-backend-port>` (based on [signal]). Confirm, or enter a different base URL.

Store the confirmed frontend URL as `AC_RUNTIME_URL` and the confirmed API base as `AC_RUNTIME_API_BASE`. Flag for Phase 3 (`references/populate.md`): the wizard needs to add the chrome-devtools MCP server (frontend verification uses it). Both values populate `.devforge/project-config.json`.

**CLI tool:**

> What command launches the built tool? (e.g. `./target/release/myapp`, `python -m mypackage`, `node dist/cli.js`, `go run ./cmd/myapp`)

Store as `AC_RUNTIME_CLI_COMMAND`.

**Mobile / desktop / game / other non-automatable:**

> Runtime-assisted verification for this project type is largely manual — `/verify` will describe what to check, but the user will run the checks themselves. Confirm Runtime-assisted mode, or switch to Code-only / Tests.

No follow-up storage needed beyond `AC_VERIFICATION_MODE` in this case.

---

Questions phase complete. Proceed to Phase 3 (`references/populate.md`).
