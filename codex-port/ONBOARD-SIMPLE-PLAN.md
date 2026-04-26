# Onboard Simple — Implementation Plan (revised)

**Premise**: User produced ~7035 lines of documentation in one reference monorepo and ~370KB in another by *just asking the LLM* to "read everything, document everything." Current /onboard's elaborate prompt under-emits across runtimes, projects (R1 + cross-version 1.28.0 + cross-machine evidence). The redesign hypothesis: a simpler prompt mandating cover-all-code with mirror-folder structure produces the prior-framework's quality without helper apparatus.

**Comparison branch**: `feature/onboard-path-b` (5 commits, paused at Step 1.1) holds the elaborate Path-B-style design with helper-mediated extraction. After this simple approach is implemented and tested, R5 outputs are compared against the current-main baseline and reference outputs to decide which to merge.

**Branch**: `feature/onboard-simple` cut from `feature/codex-support` HEAD `3b2c838` (same starting point as path-b branch).

**Revision history**: this plan was revised on 2026-04-26 after design discussion surfaced wrong assumptions in earlier drafts (WORKSPACE_MODE-based shape selection, count-based heuristic with web-paradigm bias, prescribed patterns in architecture.md). Corrected design below.

---

## Working mode

For every decision and every implementation step:

1. **Think** — what's the real problem, smallest correct answer.
2. **Argue** — surface tradeoffs honestly; if there's a real fork, present both sides.
3. **Find best** — pick best, not easiest to defend.
4. **Align** — check against earlier decisions and design tenets.
5. **Implement** — only what was decided.

Approval gate at every atomic step.

---

## Reference outputs (concrete targets)

| Reference | Source shape | Doc shape used | Total docs |
|---|---|---|---|
| Reference A (npm monorepo) | 23 small library packages + 1 composite frontend app | Mirror folders: per-package doc files + per-concern sub-docs inside the app + `architecture/overview.md` | ~7035 lines |
| Reference B (npm monorepo) | 4 composite packages (frontend app, admin frontend, backend functions, shared common) | **Topical numbered** (deliberately flattened): `01-overview.md` … `13-<topic>.md` + per-app subfolder for the second frontend | ~370KB |

Both share: cover all code, real code blocks lifted from source with file refs, types inline, dependencies enumerated, usage examples from real consumers, "not exported" annotations.

Both diverge: Reference A mirrored folders; Reference B flattened to topical. **This plan adopts the mirror-folder approach as the universal shape** — it's deterministic, language-agnostic, and structurally cleaner for agent navigation. The topical-flatten approach of Reference B is treated as a deliberate stylistic deviation we don't replicate.

---

## Design tenets

1. **Cover all code at agent-navigation depth.** Every meaningful source folder gets a documentation home. Density target derives from "agent can navigate and decide where to make changes from this doc alone, without opening source for first-pass orientation." Source becomes a verification step, not a discovery step.

2. **Mirror folder structure.** Source tree → doc tree. No shape selection. No heuristic. Every package in `packages[]` → `docs/<package-relative-path>/index.md`. Meaningful concern subdirs → sub-docs at the package's doc folder. Trivial sub-folders collapse into parent. Mechanical, deterministic, language-agnostic.

3. **Code blocks lifted from real source.** Every code example in a doc has a `path/to/file.ext:line-range` reference. No invented code. No paraphrasing.

4. **Boundary surface, not implementation.** Document what crosses module/class/component boundaries (exports, public class members, route handlers, props/emits/slots). Skip private helpers, internal utilities, function bodies. Visibility model is the language's (TS `export`, Python `_`-convention/`__all__`, Rust `pub`, Go capitalization, etc.).

5. **No bundled pattern assumptions.** `docs/architecture.md` carries the project's actual architectural patterns, dependency directions, naming conventions, decision rules — observed from the codebase, not prescribed by the spec. A Django project gets Django's patterns; a Rust crate gets Rust's; a procedural Go project gets Go's. The spec mandates structure (architecture.md exists, is substantive) but never preset content.

6. **User-corrigible.** Baseline + Overwrite/Merge/Abort across all `docs/` outputs. Re-runs preserve user fixes.

7. **No helper apparatus.** No `scripts/lib/structure_report.py`. No per-symbol extraction validation. No capability-evidence helper. No signal aggregation. Simpler is the point of this branch.

8. **Cross-runtime parity by determinism, not by validation.** Mirror-folder mapping is mechanical; the same source produces the same doc structure on Claude and Codex. F1 closed by inlining tech-writer instructions in `main.md` (no external references). F2 closed by adaptive subagent dispatch without full-history fork.

---

## Resolved design decisions

### S1 — Spec hosting *(resolved 2026-04-26)*

**Choice**: **Inline everything into `src/commands/onboard/main.md`.** Delete `references/tech-writer-onboarding.md`. Kills F1 (file-resolution divergence) by removing the cross-runtime path-resolution mechanism entirely.

### S2 — Doc structure *(resolved 2026-04-26, revised)*

**Choice**: **Mirror folder structure.** No shape A/B/C selection. No heuristic.

#### Unifying rule

The mirror rule does not assume `src/` or `packages/` folder names — those are web/Cargo-ecosystem conventions, not universal. Go has no `src/`. Java buries source under `src/main/java/<groupId>/<pkg>/`. Cargo workspaces may put crates at root (`./my-cli/`) or in any folder. Rules below use the wizard's detected paths verbatim and let the LLM identify ecosystem-conventional source roots.

1. **Documentation unit** = each entry in `.devforge/detection_report.yaml` `packages[]`. The wizard already detects manifest files across ecosystems — `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `pom.xml`, `*.csproj`, `Gemfile`, `composer.json`. Each entry has a `path` field with the actual filesystem location. **Use the path verbatim.**

   If `packages[]` is empty or has just one entry pointing to the workspace/source root, the project itself is the single unit (single-app case).

2. **Unit's doc location** = `docs/<entry.path>/index.md`, mirroring whatever path the wizard found. Examples:
   - npm package at `packages/pkg-foo/` → `docs/packages/pkg-foo/index.md`
   - Rust crate at root (`my-cli/`) → `docs/my-cli/index.md`
   - Rust crate in custom folder (`workspace/crates/my-lib/`) → `docs/workspace/crates/my-lib/index.md`
   - Go module at root (path = `.`) → `docs/index.md`
   - Java module at `services/billing/` → `docs/services/billing/index.md`
   - Single-app project (`packages[]` = [{path: "."}]) → `docs/index.md`

3. **Inside each unit**: find the unit's **source root** by ecosystem convention (the LLM observes per language):
   - JS/TS/PHP-PSR4: `src/`
   - Rust: `src/`
   - Ruby: `lib/`
   - Java/Kotlin: `src/main/java/<groupId>/<pkg>/` (collapse boilerplate path segments — see rule 5)
   - Python: `src/<pkg>/` or `<pkg>/`
   - Go: unit root (no source-folder convention; subfolders like `cmd/`, `pkg/`, `internal/` are direct concerns)
   - C#/.NET: project folder directly

   Once found, mirror the source root's substantive subfolders as sub-docs at `docs/<unit-path>/<concern>.md` (or `<concern>/index.md` + further sub-docs when the concern has its own substantial sub-tree).

4. **Trivial subfolders** (1-2 files, single-purpose utilities) fold into the parent doc. LLM judges per-folder.

5. **Boilerplate path segments collapse.** Java's `src/main/java/com/example/` is uninformative path nesting; mirror starts at the meaningful level (the package namespace `com/example/<pkg>/`'s contents, not the boilerplate prefix). Same for Maven's `target/`, Gradle's `build/`, etc.

6. **Stop at file granularity.** Files never get individual docs; they're enumerated within their folder's doc.

7. **`docs/architecture.md`** always exists at the workspace root of `docs/`. Optional `docs/cross-cutting/<topic>.md` only when the LLM observes a pattern that genuinely spans units without a folder home.

#### Worked examples (covering the spectrum)

**Single web-framework frontend** (e.g. Vue/React/Angular/Svelte/Solid; `packages[]` = [{path: "."}], source in `src/`):
```
docs/
├── index.md                      ← project overview (the unit's main doc)
├── components.md                 (or components/ subfolder if substantive sub-tree)
├── composables.md
├── stores.md
├── views.md
├── router.md
├── helpers.md                    (or folded into index.md if trivial)
└── architecture.md               ← observed patterns, conventions, decision rules
```

**Reference-A-style npm monorepo** (many small libraries + one composite frontend; `packages[]` paths under `packages/` and `apps/`):
```
docs/
├── packages/pkg-foo/index.md          ← per-detected-manifest path verbatim
├── packages/pkg-bar/index.md
... N more
├── apps/<frontend-app>/
│   ├── index.md
│   ├── components/.../...
│   ├── composables.md                 (or hooks.md / similar per framework)
│   ├── stores.md
│   └── routing.md
└── architecture.md
```

**Reference-B-style monorepo if mirrored instead of flattened** (few composite packages; paths under `packages/`):
```
docs/
├── packages/<frontend-app>/{index.md, components.md, stores.md, ...}
├── packages/<admin-frontend>/{...}
├── packages/<backend-functions>/{index.md, <handler-group>.md, services.md, daos.md, ...}
├── packages/<shared-common>/index.md
└── architecture.md
```

**Rust workspace, members at root** (Cargo.toml: `members = ["my-cli", "my-lib"]`):
```
docs/
├── my-cli/index.md               ← whatever path Cargo lists, verbatim
├── my-lib/index.md
└── architecture.md
```

**Rust workspace, custom folder layout** (Cargo.toml: `members = ["workspace/crates/*"]`):
```
docs/
├── workspace/crates/my-cli/index.md
├── workspace/crates/my-lib/index.md
└── architecture.md
```

**Go module** (single manifest at root, source in `cmd/`/`pkg/`/`internal/`):
```
docs/
├── index.md                      ← module overview
├── cmd/<binary>.md               (per binary)
├── pkg/<pkg>.md                  (per public package)
├── internal/<pkg>.md             (per internal package)
└── architecture.md
```

**Java multi-module Maven project** (`packages[]` = entries per module pom.xml):
```
docs/
├── services/billing/index.md     ← mirror starts at meaningful level (src/main/java/com/example/... boilerplate collapsed)
├── services/auth/index.md
└── architecture.md
```

**Python monorepo** (`packages[]` paths from each pyproject.toml location):
```
docs/
├── libs/auth/index.md
├── apps/api/{index.md, handlers.md, services.md, ...}
└── architecture.md
```

**Python single-package project** (`packages[]` = [{path: "."}]):
```
docs/
├── index.md                      ← project overview
├── <top-level-subdir>.md         (per substantive subdir of src/<pkg>/ or <pkg>/)
└── architecture.md
```

#### Why this works

- **Deterministic**: same source tree → same doc tree. Cross-runtime, cross-developer, cross-run parity guaranteed by construction.
- **Path-from-source = path-to-docs**: an agent at `packages/pkg-foo/src/<concern>/` knows the doc lives under `docs/packages/pkg-foo/`. No mental translation.
- **Language-agnostic**: every ecosystem has folders. Rust crates, Go modules, Python packages, Java modules, npm packages, Ruby gems — all map naturally.
- **Coverage check is trivial**: `listdiff(meaningful-source-folders, doc-folders)` = 0.
- **Handles single-source projects**: the unit-IS-the-project rule means a single-frontend project (any web framework) with just `src/` gets clean docs at `docs/` root level, no awkward `docs/<root-package>/...` nesting.

### S3 — Per-doc template *(resolved 2026-04-26)*

Every package-level `index.md` (and each meaningful concern sub-doc) carries enough content for an agent to navigate without opening source. Required sections:

1. **`# <package or concern name>`**
2. **`## Overview`** — 1 paragraph: what this provides, who consumes it.
3. **`## Directory Structure`** — annotated tree of source layout. Mark non-exported subdirs explicitly (e.g. `revisionHistory/ — internal, not exported`).
4. **`## Main Exports` (or `Public Surface`, `Public API`, etc.)** — every exported symbol grouped by concern. For each: signature + a code block lifted from real source with a `path/file.ext:line-range` reference comment.
5. **`## Types` (or `Data Shapes`)** — principal types this exposes, full inline definitions. Not "see types.ts" — the actual type definitions inline.
6. **`## Dependencies`** — workspace-internal and external dependencies (from package.json, Cargo.toml, pyproject.toml, etc.). **Workspace-internal entries hyperlink to their docs** (e.g., `[pkg-bar](../pkg-bar/index.md)`); each entry has 1 line about what's used from that dep. External dependencies named with version, no link. This section is the **forward-direction** primary cross-link mechanism (S9).
7. **`## Usage Example`** — lifted from a real consumer file in the codebase. End-to-end pattern showing how the package/module is consumed.

Length adapts to package complexity:
- Tiny utility package: 50–80 lines.
- Mid-size library: 150–300 lines.
- Composite (multi-concern): main `index.md` is the directory + overview + cross-references to sub-docs; sub-docs carry the per-concern depth.

`docs/architecture.md` template:

1. **Architecture overview** — what the project IS at the architectural level. Observed from code, not prescribed.
2. **Module/package structure** — the workspace layout, how packages relate.
3. **Patterns** — every architectural pattern observed in the codebase. **A project may legitimately have multiple coexisting patterns** (e.g., MVC in backend services + Clean Architecture in frontend; legacy procedural code being phased out alongside modern layered code in new modules; different paradigms in different microservices). When multiple patterns coexist, document each with explicit "where it applies" scope:
   ```
   ## Patterns

   ### <Pattern A> (applies in: <package-paths or module-paths>)
   <observed description, conventions, decision rules>

   ### <Pattern B> (applies in: <other paths>)
   <observed description>
   ```
   The spec mandates honesty about diversity — do NOT force-fit the project into a single pattern when more than one exists.
4. **Conventions** — naming, file organization, import style, error handling — all observed. If conventions vary across patterns, scope each accordingly.
5. **Cross-cutting concerns** — auth flow, data flow, state management, error propagation — all observed.
6. **Dependency direction rules** — observed (where inward/outward dependencies go); per-pattern when patterns diverge on this.

**Per-package overrides**: a package's `index.md` MAY contain a "Pattern" section when that package follows a distinct pattern worth calling out at the package level (cross-reference `docs/architecture.md` for the workspace context).

**Optional split**: when one or more patterns are substantial enough to warrant their own deep document, split into `docs/architecture/<pattern>.md` per pattern; `docs/architecture.md` becomes the index pointing at each. Same trigger as "substantive subfolder gets its own sub-doc."

No prescribed list of patterns to look for. The spec says "document the project's architectural patterns at substantive depth, honestly reflecting any diversity"; the LLM observes what's there.

### S4 — Subagent dispatch *(resolved 2026-04-26)*

**Choice**: **Adaptive per project size, no full-history fork.**

| Source files | Strategy |
|---|---|
| < 50 | Direct: orchestrator writes everything itself, no subagents. |
| 50–500 | One subagent per package. Sequential or small parallel batches respecting runtime concurrency limits. |
| 500+ | One subagent per package, parallel batches. |

Subagent prompt is self-contained: package identifier + scope path + per-doc template (S3) + write target + project brief from §1.1. Subagent does NOT inherit orchestrator's conversation history. Closes F2 (Codex's "role-specialized agents can't inherit that way").

### S5 — Verification *(resolved 2026-04-26)*

**Choice**: **Coverage-first, structural-completeness check — not just file presence.**

After tech-writer completes:

1. **Coverage check** (load-bearing):
   - For every entry in `packages[]`, confirm `docs/<package-path>/index.md` exists.
   - For every meaningful subfolder of every package, confirm a corresponding doc exists OR the parent's `index.md` covers it.
   - Listing-diff produces miss list. Any miss → coverage failure.

2. **Structural-completeness check** (not just "file exists"): each `index.md` has the S3 required sections — Overview present and substantive, Main Exports section with code blocks, Types section, Dependencies, Usage Example. A doc missing types-inline OR missing real code blocks fails verification even if the file exists.

3. **Code-block sourcing**: spot-check 5 random code blocks across `docs/`. Each must have a `path/file.ext:line-range` reference comment. Any unsourced block = failure.

4. **Cross-link existence**: spot-check 5 random Markdown links in `docs/*.md` resolve to existing files. Per S8, all cross-link targets must exist; broken links = failure.

5. **Term hygiene**: locked terminology (Glossary in main.md) used precisely.

6. **Sigil hygiene**: no `/<command>` or `$<command>` strings in `docs/*` (lift from current onboard).

Coverage or structural failure blocks proceed; user prompted **Re-run** / **Accept gap** / **Abort**. Hygiene failures are softer — present findings + ask Proceed / Re-run / Abort.

### S6 — Baseline + O/M/A *(resolved 2026-04-26)*

**Choice**: lifted unchanged from path-b Q7 — baseline tracked across all `docs/` outputs.

Mechanics:
- `.devforge/baseline/docs/<...same-relative-path...>` for every generated doc file.
- Pre-scan check (§1.0) loops over all docs files, detects modifications via baseline diff, presents single combined Overwrite/Merge/Abort prompt.
- Onboard owns dropping baselines for paths it adds (per-package, per-concern).

### S7 — Memory enrichment *(resolved 2026-04-26)*

**Choice**: lift current onboard's MEMORY_ADDITIONS structure (module boundaries / dependency warnings / complexity / inconsistencies). Mandate: **report observations from every package, not a curated subset**.

### S8 — Cross-linking between docs *(resolved 2026-04-26)*

**Choice**: explicit cross-link rules to keep navigation reliable without per-doc reverse-link maintenance burden.

#### Where cross-links live

1. **Per-package `Dependencies` section** (forward direction, "what THIS uses"). Workspace-internal entries hyperlink to their package docs (e.g., `[pkg-bar](../pkg-bar/index.md)`). External deps named + version, no link. This is the **primary cross-link mechanism** between packages.

2. **Inline cross-references in prose** — within any doc, when a type/function/concept defined in another package or sub-doc is mentioned, link to the source doc inline. Examples:
   - "consumes `Order` from [`pkg-orders`](../pkg-orders/index.md)"
   - "uses `useAuthStore` defined in [`stores.md`](./stores.md)"
   - Reference cross-doc symbols by `[<symbol>](<path>#<anchor>)` when an anchor exists.

3. **`docs/architecture.md` dependency overview** — a high-level "who depends on whom" across all workspace packages. Mermaid graph OR plain bullet list. Bird's-eye view complementing per-package Dependencies sections.

4. **`docs/cross-cutting/<topic>.md`** — for concerns spanning packages without a folder home (already mentioned in S2 rule 7). Each cross-cutting topic explicitly links into every package it touches.

#### What does NOT exist

- **No "Used by" / "Consumers" section per package**: reverse-direction tracking is expensive to maintain (changes every time a new consumer is added). The architecture-level dependency overview provides the inverse view; agents needing "who uses X?" read architecture.md or grep for imports.

#### Cross-link path conventions

- Relative paths preferred when within the same workspace: `../pkg-bar/index.md`, `./stores.md`, `../cross-cutting/auth-flow.md`.
- Absolute-from-docs-root acceptable when relative would be confusing: `[stores](docs/apps/<frontend>/stores.md)`.
- All cross-link targets must exist (verified in S5's hygiene check; **add**: cross-link existence check spot-samples 5 random links per run).

### S9 — Cross-runtime parity testing (R5) *(resolved 2026-04-26)*

**Choice**: same protocol as baseline measurement of current main. Run new /onboard on `~/Projects/testParity/` (Claude) and `~/Projects/testParity-codex/` (Codex). Compare:

- Coverage (every package has a doc on both runtimes)
- Volume (lines per package; ratio of doc lines per source file)
- Structural shape (mirror-folder applied identically on both)
- Density target met (Reference A's ~3.2 lines per source file is the reference)
- F1 / F2 closure evidence

Append R5 section to `codex-port/phase-R/parity-findings.md` with F1–F6 closure status.

---

## Open work TODOs (deferred)

- [ ] **`/update-docs` command (or equivalent)** — for greenfield growth + incremental updates as code evolves. Both reference projects had this command in their `.claude/commands/`; current Forge does not. Same DOCS_SHAPE inherited; same coverage mandate. Out of scope for this branch.
- [ ] **Greenfield doc lifecycle** — when a project starts empty, `/onboard` skips. Docs accumulate per-task via downstream commands. Needs design separately. Out of scope here.
- [ ] **Downstream command wiring** — same as path-b's deferred TODO. `plan`, `specify`, `execute-task`, `breakdown`, `verify` live in `src/_pending/commands/` and aren't built. When they're built, they must consume `docs/<package>/...` per the locked terminology and reading patterns.

---

## Atomic step plan

Steps are atomic. Each has entry / action / self-verify / approval-gate. Approval gate at every step.

### Phase 0 — Pre-work *(done)*

- [x] **0.1** — Branch `feature/onboard-simple` cut from `feature/codex-support` HEAD `3b2c838`.
- [x] **0.2** — Original simple plan committed (bb8f9c2). Revised plan (this file) supersedes it.

### Phase 1 — Spec rewrite

#### Step 1.1 — Audit current onboard files for lift-forward parts
- **Entry**: 0.2 done.
- **Action**: read current `src/commands/onboard/main.md` (311 lines) and `src/commands/onboard/references/tech-writer-onboarding.md` (200 lines). Produce written inventory: which sections lift forward verbatim (smart extraction table, sigil neutrality, memory enrichment scaffold), which get rewritten (Phase 1 setup, Phase 2 prompt template, Phase 3 verification, Documentation Requirements, IMPORTANT RULES), which get added new (Glossary, mirror-folder shape rules, depth requirements, structural-completeness check).
- **Self-verify**: inventory covers every section of both files; lift-forward entries cite line ranges.
- **Approval gate**: review inventory.

#### Step 1.2 — Write new `src/commands/onboard/main.md` (full rewrite, self-contained)
- **Entry**: 1.1 approved.
- **Action**: write new main.md from scratch incorporating S1–S8. Inline tech-writer instructions (Section A). Mirror-folder shape per S2. Per-doc template per S3 with depth requirement. Subagent dispatch per S4 (no full-history fork). Verification per S5 (coverage + structural-completeness + sourcing). Baseline + O/M/A per S6. Memory enrichment per S7. Glossary with locked terminology. IMPORTANT RULES.
- **Self-verify**: file is self-contained (no `references/...` paths); every Section A piece from current tech-writer-onboarding.md that's worth keeping is inlined; mirror-folder rules are explicit; depth requirement is clear; verification section requires structural completeness.
- **Approval gate**: review draft before deletion of references file.

#### Step 1.3 — Delete `src/commands/onboard/references/tech-writer-onboarding.md` and the empty references folder
- **Entry**: 1.2 approved.
- **Action**: `git rm src/commands/onboard/references/tech-writer-onboarding.md` and remove the empty directory.
- **Self-verify**: `find src/commands/onboard -type f` shows only `main.md`; `grep -r "references/" src/commands/onboard/` produces no matches.
- **Approval gate**: confirm clean.

#### Step 1.4 — Regenerate installed files via `scripts/generate.sh` (or per-runtime emitters)
- **Entry**: 1.3 approved.
- **Action**: run the generator that produces installed `.claude/commands/onboard/...` and `.agents/skills/onboard/...` artifacts from `src/`.
- **Self-verify**: installed copies match src; Codex installation no longer has a `references/` subfolder; Claude installation likewise.
- **Approval gate**: ready for R5.

### Phase 2 — R5 measurement

#### Step 2.1 — Reinstall testParity (Claude side)
- **Entry**: Phase 1 complete + approved.
- **Action**: I provide exact wipe + fresh-install commands for the user to run on `~/Projects/testParity/` from this branch.
- **Self-verify**: `tech-writer-onboarding.md` no longer present in target; new `main.md` shape installed; `.devforge/` exists.
- **Approval gate**: confirm install before /onboard run.

#### Step 2.2 — Run /onboard on Claude side (user executes)
- **Entry**: 2.1 approved.
- **Action**: user runs `/onboard` in Claude Code in `~/Projects/testParity/`. Captures full transcript + `docs/` tree + `wc -l docs/**/*.md` + `.devforge/memory.md` additions.
- **Self-verify**: docs/ populated; mirror-folder shape evident; coverage check passed; F1 not triggered (no file-resolution issue).
- **Approval gate**: review output.

#### Step 2.3 — Reinstall + run on testParity-codex (Codex side)
- **Entry**: 2.2 approved.
- **Action**: same protocol on `~/Projects/testParity-codex/` with `$onboard` in Codex CLI.
- **Self-verify**: same expectations; F1 + F2 closures evident.
- **Approval gate**: review output.

#### Step 2.4 — Structural diff R5 outputs
- **Entry**: 2.3 approved.
- **Action**: compare:
  - Both R5 outputs to each other (Claude vs Codex, expect near-identical mirror-folder structure)
  - R5 vs baseline (current main, current-main onboard baseline: Claude 1450 lines, Codex ~700 lines — expect substantial increase)
  - R5 vs Reference A baseline (~7035 lines — expect roughly comparable density per source file)
  - R5 vs path-b R6 if path-b implementation has been continued and tested (probably not yet — leave blank)
- **Self-verify**: comparison table covers all known runs.
- **Approval gate**: numbers reviewed.

#### Step 2.5 — Append R5 section to `codex-port/phase-R/parity-findings.md`
- **Entry**: 2.4 approved.
- **Action**: write R5 section using R4 (Path B) as the template. Score F1–F6 closures + new findings.
- **Self-verify**: section present; each F-finding has explicit closure status.
- **Approval gate**: review.

### Phase 3 — Decision

#### Step 3.1 — Compare simple vs path-b vs current
- **Entry**: Phase 2 complete.
- **Action**: produce side-by-side comparison: `feature/codex-support` (current main onboard, R1), `feature/onboard-simple` (this branch, R5), `feature/onboard-path-b` (path-b branch, R6 if run by then). Quality, complexity, maintenance burden, cross-runtime parity, code surface added, alignment with reference outputs.
- **Self-verify**: comparison covers all branches.
- **Approval gate**: ready for ship/kill decision.

#### Step 3.2 — Decision gate
- **Entry**: 3.1 reviewed.
- **Action**: user picks: merge simple, merge path-b, merge a hybrid, or neither.
- **Self-verify**: decision recorded in `codex-port/PLAN.md`.
- **Approval gate**: explicit user decision.

---

## Step-count summary

| Phase | Steps |
|---|---|
| Phase 0 | 2 (done) |
| Phase 1 | 4 |
| Phase 2 | 5 |
| Phase 3 | 2 |

**Total: 13 atomic steps** (vs path-b's 49). Same parity-test discipline; smaller spec/code surface.

## Pickup instructions for fresh session

1. Confirm branch `feature/onboard-simple` is checked out.
2. Read this plan in full.
3. Cross-read `feature/onboard-path-b`'s `codex-port/ONBOARD-IMPLEMENTATION.md` for the comparison branch's design.
4. Identify next step by `git log` + step-ID search.
5. Approval gate at every step.
