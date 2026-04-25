# Onboard Simple — Implementation Plan

**Premise**: User produced ~7035 lines of cse-strata-workspace docs and ~370KB of ap-workspace docs by *just asking the LLM* to "read everything, document everything." Current /onboard's elaborate prompt (sample-based scanning at 1000+, capability clustering, length targets) under-emits across runtimes, projects, and versions (R1 evidence, cross-version, cross-machine).

**Hypothesis**: A simpler /onboard — direct prompt mandating cover-all-code with a per-package template — will produce output closer to the prior-framework quality without the Path-B-style helper apparatus.

**Comparison branch**: `feature/onboard-path-b` (5 commits) holds the elaborate Path-B-style design. After this simple approach is implemented and tested, we compare R3 outputs against R1 baseline and (if implemented) Path-B's R2 to decide which to merge.

**Branch**: `feature/onboard-simple` cut from `feature/codex-support` HEAD `3b2c838` (same starting point as path-b branch).

---

## Working mode (lifted from path-b)

1. **Think** — what's the real problem, smallest correct answer.
2. **Argue** — surface tradeoffs honestly; if there's a real fork, present both sides.
3. **Find best** — pick best, not easiest to defend.
4. **Align** — check against earlier decisions and design tenets.
5. **Implement** — only what was decided.

Approval gate at every atomic step.

---

## Reference outputs (concrete targets)

| Project | Shape | Files |
|---|---|---|
| `~/Projects/doosan/cse-strata-workspace/documentation/` | Per-package monorepo: `packages/<pkg>/index.md`, `app-web/{overview,composables,plugins,routing,features}/`, `architecture/overview.md` | 23 packages, 7 app features, 4 app-internal layers, 1 architecture |
| `webmint/ap-workspace` (GitHub) `documentation/` | Topical numbered: `01-overview.md` through `13-database-hosting-comparison.md` + `admin-app/` subfolder for the second app | 13 numbered topics + admin-app subfolder |

Both share: cover-all-code, code blocks lifted from real source, types defined, dependencies enumerated, usage examples shown, "not exported" annotations called out.

Both diverge: decomposition shape (filesystem-aligned per-package vs concern-aligned numbered topical).

---

## Design tenets

1. **Cover all code.** Every source folder/package gets a documentation home. No skipping at scale, no sample-based silence.
2. **Decomposition adapts per project.** Monorepo with packages → per-package shape (cse-strata pattern). Single-app or non-package layout → topical numbered shape (ap-workspace pattern). Wizard's `WORKSPACE_MODE` is the signal.
3. **Code blocks lifted from real source.** No invented examples. Real signatures, real types, real usage. Annotations call out unexported / internal.
4. **Boundary surface, not implementation.** Same as path-b. Document what crosses module boundaries, not internals.
5. **User-corrigible.** Baseline + Overwrite/Merge/Abort across all outputs. Re-runs preserve user fixes.
6. **No helper apparatus.** No `scripts/lib/structure_report.py`. No per-symbol extraction validation. No capability-evidence helper. Simpler is the point of this branch.

---

## Resolved design decisions

### S1 — Spec hosting *(resolved 2026-04-26)*

**Choice**: **Inline everything in `src/commands/onboard/main.md`.** No `references/tech-writer-onboarding.md` external file. Kills F1 (file-resolution divergence) by avoiding the cross-runtime path-resolution mechanism entirely.

### S2 — Decomposition selection *(resolved 2026-04-26)*

**Choice**: **Pick from wizard's `WORKSPACE_MODE`.**
- `WORKSPACE_MODE = monorepo` → per-package shape: `docs/packages/<pkg>/index.md` for each `packages/*` (or workspace-root equivalent).
- `WORKSPACE_MODE = single` → topical numbered shape: `docs/01-overview.md` through `docs/NN-<topic>.md`.
- Apps within a monorepo (e.g. `apps/app-web/`) get their own subfolder mirroring cse-strata's `app-web/` pattern: `docs/apps/<app>/{overview,composables,plugins,routing,features}/...`.

### S3 — Per-document template *(resolved 2026-04-26)*

**Per-package doc** (monorepo packages):
1. `# <pkg-name>`
2. `## Overview` — 1 paragraph, what this package provides.
3. `## Directory Structure` — annotated tree; mark non-exported subdirs explicitly.
4. `## Main Exports` — grouped by concern; each export with signature + code block from real source.
5. `## Types` — principal types this package exposes, full type definitions.
6. `## Dependencies` — package.json dependencies (other packages it consumes).
7. `## Usage Example` — lifted from a real consumer.

**Per-app subfolder** (within monorepo apps):
- `<app>/overview/introduction.md` + `<app>/overview/tech-stack.md`
- `<app>/composables/composables.md` (if Vue/React)
- `<app>/plugins/plugins.md` (if framework supports)
- `<app>/routing/routes.md`
- `<app>/features/<feature>.md` per app-internal user-facing concern

**Per-topic doc** (single-app projects):
- Numbered (`01-overview.md`, `02-getting-started.md`, ...) covering: project overview, getting-started, project-structure, data-schema, frontend-guide, state-management, backend-services, dev-guidelines, services-doc, workflows, routing-navigation, additional-architecture-topics. Adapted per project; not all required.

### S4 — Subagent dispatch *(resolved 2026-04-26)*

**Choice**: **Adaptive per project size.**
- < 50 files: orchestrator writes everything itself.
- 50–500 files: subagent per package or per topic.
- 500+ files: subagent per package (parallel batches), or sequential per-topic for topical layout.

Subagent prompt embedded inline (S1). Subagent invocation does NOT use full-history fork (avoids F2). Subagent receives: package/topic identifier + scope path + structured template + write target.

### S5 — Verification *(resolved 2026-04-26)*

**Choice**: **Coverage check first, then hygiene.**

After tech-writer completes:
1. **Coverage check**: every `packages/*` directory (monorepo) or every detected major source area (single-app) has a corresponding doc file. Listing-diff.
2. **Term hygiene**: locked terminology used precisely (Q6-style glossary, simpler — just "package", "module", "feature" with locked meanings).
3. **Sigil hygiene**: no `/onboard` or `$onboard` strings in `docs/*` (lift from current).
4. **Code-block hygiene**: every code block in docs has a `path/to/file.ext:line` reference where it was lifted from. Spot-check 5 random blocks; fail if any are invented.

Coverage failure fails verify; user prompted to re-run. No silent under-emit.

### S6 — Baseline + O/M/A *(resolved 2026-04-26)*

**Choice**: **Same as path-b Q7 — baseline tracked across all `docs/` outputs.** User-corrigible LLM output is mandatory; re-runs preserve user fixes.

`.devforge/baseline/docs/<...same-relative-path...>` per output file. `populate.md` (wizard) drops baselines for known paths; onboard takes ownership of dropping baselines for paths it adds (per-package, per-topic).

### S7 — Memory enrichment *(resolved 2026-04-26)*

**Choice**: **Lift from current onboard.** §3.2 + tech-writer §A.4 already work; same MEMORY_ADDITIONS structure (module boundaries / dependency warnings / complexity / inconsistencies). Just enforce coverage in the prompt: "report observations from every package, not a curated subset."

### S8 — Cross-runtime parity testing *(resolved 2026-04-26)*

**Choice**: **R3 measurement** against `~/Projects/testParity/` (Claude) and `~/Projects/testParity-codex/` (Codex). Same protocol as R1 baseline. Compare:
- Coverage (file count per directory; both runtimes)
- Volume (total lines)
- Density (lines per source file)
- Structural shape (decomposition matches WORKSPACE_MODE)
- Capability of each runtime to satisfy the simpler prompt

Latency and divergence reported alongside R1 baseline and (if available) path-b's R2.

---

## Atomic step plan

### Phase 0 — Pre-work *(steps already done outside the plan)*

- [x] **0.1** — Branch `feature/onboard-simple` cut from `feature/codex-support` HEAD `3b2c838`.
- [x] **0.2** — This plan doc captured.

### Phase 1 — Spec rewrite

#### Step 1.1 — Inline tech-writer-onboarding.md content into main.md
- **Entry**: Phase 0 done.
- **Action**: read current `src/commands/onboard/references/tech-writer-onboarding.md`. Lift forward valuable parts (smart extraction table, return-format scaffold, sigil neutrality, quality checks, memory enrichment shape). Inline them into `src/commands/onboard/main.md`. Delete the references file.
- **Self-verify**: no remaining file references in main.md to `references/tech-writer-onboarding.md`; the references file is removed; `main.md` self-contained.
- **Approval gate**: review.

#### Step 1.2 — Rewrite Phase 1 (project-knowledge gathering) for simpler shape
- **Entry**: 1.1 approved.
- **Action**: keep §1.0 baseline check (S6) + §1.1 brief gathering (lift). Replace §1.2 module map with a "decomposition selection" step driven by `WORKSPACE_MODE` (S2). Replace §1.3 scan strategy with a coverage-mandate strategy (S4). Drop sample-based-at-1000+ tier; replace with "subagent per package, parallel-or-sequential per project size."
- **Self-verify**: `WORKSPACE_MODE` referenced; no "sample-based" silence; coverage mandate explicit.
- **Approval gate**: review.

#### Step 1.3 — Rewrite Phase 2 (tech-writer prompt template)
- **Entry**: 1.2 approved.
- **Action**: rewrite prompt template:
  - Mandate "cover all code"
  - Reference per-doc template (S3) inline
  - Code blocks lifted from real source (with `path/file.ext:line` reference required)
  - For monorepo: per-package + per-app structure
  - For single-app: topical numbered structure
  - Subagent dispatch instructions for large projects
  - "Annotate non-exported subdirs explicitly"
- **Self-verify**: every section of S3 templates is reflected; no length caps that force brevity.
- **Approval gate**: review prompt.

#### Step 1.4 — Rewrite Phase 3 (verification)
- **Entry**: 1.3 approved.
- **Action**: §3.1 verification gets coverage check (S5.1) as the FIRST gate. Term + sigil + code-block hygiene as subsequent checks. §3.2 memory append per S7.
- **Self-verify**: coverage check fires before any other; coverage failure blocks proceed.
- **Approval gate**: review.

#### Step 1.5 — Rewrite Phase 4 (summary) + IMPORTANT RULES
- **Entry**: 1.4 approved.
- **Action**: summary template adapts to whichever decomposition was used. IMPORTANT RULES updated to reflect S1–S7 (no per-symbol helper, coverage-first).
- **Self-verify**: summary handles both monorepo and single-app shapes.
- **Approval gate**: review.

#### Step 1.6 — Documentation Requirements + Glossary
- **Entry**: 1.5 approved.
- **Action**: rewrite Documentation Requirements per S3. Add Glossary with locked terminology: package, module, feature, app — each with precise meaning.
- **Self-verify**: every doc shape from S3 has a section in Documentation Requirements.
- **Approval gate**: review.

### Phase 2 — Regenerate + R3 measurement

#### Step 2.1 — Regenerate installed files
- **Entry**: Phase 1 complete + approved.
- **Action**: run `scripts/generate.sh` (or whatever generator exists) to produce installed `src/commands/onboard/main.md` artifacts.
- **Self-verify**: installed copy matches src.
- **Approval gate**: ready for R3.

#### Step 2.2 — R3 reinstall + run on testParity (Claude)
- **Entry**: 2.1 approved.
- **Action**: user wipes `~/Projects/testParity/`, fresh-installs from this branch, runs `/onboard`. Captures full transcript + `docs/` tree + `.devforge/memory.md` additions.
- **Self-verify**: `docs/` populated; coverage check passed; structure matches `WORKSPACE_MODE`.
- **Approval gate**: review output.

#### Step 2.3 — R3 reinstall + run on testParity-codex (Codex)
- **Entry**: 2.2 approved.
- **Action**: same on Codex side.
- **Self-verify**: same expectations; F1 and F2 closures evident.
- **Approval gate**: review output.

#### Step 2.4 — R3 comparison
- **Entry**: 2.3 approved.
- **Action**: compare R3 outputs to:
  - R1 baseline (Claude 1450 lines, Codex ~700 lines)
  - cse-strata reference (~7035 lines, prior framework)
  - path-b's R2 if it has been run by the time we get here
- **Self-verify**: comparison table covers all known runs.
- **Approval gate**: numbers reviewed.

#### Step 2.5 — Append R3 section to parity-findings.md
- **Entry**: 2.4 approved.
- **Action**: write R3 section in `codex-port/phase-R/parity-findings.md` covering F1–F6 closures and quality vs reference outputs.
- **Self-verify**: section present; F-finding statuses recorded.
- **Approval gate**: review.

### Phase 3 — Decision

#### Step 3.1 — Compare simple vs path-b vs current
- **Entry**: Phase 2 complete.
- **Action**: produce side-by-side comparison: `feature/codex-support` (current main onboard, R1), `feature/onboard-simple` (this branch, R3), `feature/onboard-path-b` (path-b branch, R2 if run). Quality, complexity, maintenance burden, cross-runtime parity, code surface added.
- **Self-verify**: comparison covers all branches.
- **Approval gate**: ship/kill/merge decision next.

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
| Phase 1 | 6 |
| Phase 2 | 5 |
| Phase 3 | 2 |

**Total: 15 atomic steps** vs path-b's 49. Same parity-test discipline; much smaller spec/code surface.

## Pickup instructions for fresh session

1. Confirm branch `feature/onboard-simple` is checked out.
2. Read this plan + path-b's plan (`codex-port/ONBOARD-IMPLEMENTATION.md` on `feature/onboard-path-b`).
3. Identify next step by `git log` + step-ID search in commits.
4. Approval gate at every step.
