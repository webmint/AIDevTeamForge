# Storage Rules — Specs, Plans, Tasks, and Docs

These rules define how all development artifacts are organized. All commands MUST follow them.

## Directory Structure

```
bugs/
  NNN-short-description.md           # Bug reports (report-bug or verify triage)

audits/
  YYYY-MM-DD-audit.md                  # Adversarial codebase audits (audit) — periodic, dated, not auto-committed
  .gitignore                           # Auto-created on first audit run (excludes .tmp-* files)

specs/
  NNN-feature-name/                # One numbered directory per feature (allocated by research or discover)
    research-report.md             # Research report (research) — bug/enhancement lane
    research-handoff.json          # research→specify structured handoff (research)
    probe-script.<ext>             # Tier-1.5 runtime probe (research) — optional
    discovery-report.md            # Discovery report (discover) — greenfield lane
    discover-handoff.json          # discover→specify structured handoff (discover)
    spec.md                        # Feature specification (specify)
    plan.md                        # Technical implementation plan (plan)
    research.md                    # Research findings (plan) — optional, NOT research-report.md
    data-model.md                  # Entity definitions (plan) — optional
    contracts.md                   # API contracts (plan) — optional
    handoff.json                   # specify→plan structured handoff (specify)
    plan-handoff.json              # plan→breakdown structured handoff (plan)
    breakdown-handoff.json         # breakdown→implement structured handoff (breakdown)
    tasks/                         # Task breakdown (breakdown)
      001-short-task-title.md      # Individual task files
      002-short-task-title.md
      003-short-task-title.md

docs/
  overview.md                      # Project overview + package map (project tier)
  architecture.md                  # Cross-package architecture + layering rationale (project tier)
  glossary.md                      # CBM-augmented project glossary (project tier; Phase B)
  <package>/                       # One subdir per package detected by /devforge:init-forge
    overview.md                    # Package role + concern enumeration
    architecture.md                # Package layers + patterns
    <concern>/                     # One subdir per src/ subfolder concern
      index.md                     # Concern: Purpose + Structure (annotated tree) + Hazards
```

**Intake owns the feature directory.** `/devforge:research` and `/devforge:discover` allocate
`specs/NNN-feature-name/` — and the matching `spec/NNN-feature-name` branch —
at the end of a run, once the user confirms the save and the feature name, and
write their report + handoff inside it. `/devforge:specify` then RESOLVES that existing
directory and writes `spec.md` beside those artifacts; it allocates no number
of its own. A run the user declines to save leaves nothing under `specs/`.
Top-level `research/` and `discover/` directories are legacy — installs that
ran intake before this layout keep theirs as inert history, and nothing new is
written there.

**The `discovery-` / `discover-` stem asymmetry is deliberate.** `/devforge:discover`
writes its report as `discovery-report.md` and its handoff as
`discover-handoff.json`. Both literals are load-bearing — `specify_helper
find-handoffs` globs `specs/*/discover-handoff.json`, and the handoff records
the sibling report in its `report_path` field — so renaming either file to make
the two stems match breaks discovery. Do not normalize them.

NOTE: legacy layout (`docs/features/`, `docs/api/`, `docs/guides/`) is dropped.
Structural information (exports, types, deps, public-surface, call chains) is
NOT pre-rendered into docs/ — query the codebase-memory-mcp graph live via
`search_graph`, `trace_path`, `get_code_snippet`, `search_code`,
`query_graph`. Md files carry the narrative + judgment layer; CBM carries
the structural-query layer.

`docs/glossary.md` is the project-tier consolidated glossary produced by
Phase B of `/devforge:generate-docs` — 30-150 entries classified by CBM presence
(code-anchored: exact name match in graph; fuzzy-anchored: BM25 hit; prose-
only: no graph match) with 1-2 sentence definitions and cite-back paths.
Validator-enforced shape (term unique case-insensitive, definition ≤280 chars
single paragraph, cite_md_paths ≥1 each on disk, code/fuzzy-anchored
snippet must resolve via CBM, prose-only ≥2 cite_md_paths, related_terms
must reference other entries, aliases_to_avoid optional list of banned
synonyms guarded against self-reference / in-list dup / cross-entry
collision with another entry's canonical term, count 30..150). Concern-tier Purpose paragraphs
still carry inline term disambiguation; this file is the project-tier
consolidation, not a replacement.

## `.devforge/` Runtime State Disposition

`.devforge/` holds four storage classes: three runtime-state classes over its top-level files (VERSIONED / EPHEMERAL / FEATURE-SCOPED, plan 49), each with exactly one git disposition, plus a CODE class over its install-reproducible helper-code subdirectories (plan 56, extended by plan 63's relocated command-reference files). Getting the class right is what keeps a consumer install's tree CLEAN after a full pipeline cycle instead of dirty with runtime churn — and keeps the consumer's codebase-memory-mcp (CBM) graph free of forge-internal code.

| File | Class | Git treatment |
|---|---|---|
| `memory.md` | VERSIONED | Tracked; per-feature delta folds into the `/devforge:finalize` squash |
| `spec-stamps.jsonl` | VERSIONED | Tracked; per-feature delta folds into the `/devforge:finalize` squash |
| `init.yaml`, `configure.yaml`, `constitute.json` | VERSIONED | Tracked; setup identity, changes only on reconfigure |
| `project-config.json`, `index.json` | VERSIONED | Tracked; render/index artifacts, stable across cycles |
| `storage-rules.md` | VERSIONED | Tracked; installed framework file |
| `session-state.md` | EPHEMERAL | gitignored (crash recovery reads it from DISK, not git) |
| `specify-state.json`, `research-state.json`, `discover-scope.json` | EPHEMERAL | gitignored; per-cycle working state |
| `research-report.json`, `discover-report.json` | EPHEMERAL | gitignored; single-slot scratch output |
| `.preflight-stamp`, `cbm-last-indexed-sha` | EPHEMERAL | gitignored; pointers/timestamps |
| `.generate-docs-trace.log`, `cbm-usage.log` | EPHEMERAL | gitignored; logs |
| `*.lock` | EPHEMERAL | gitignored |
| `profile/` (subdir) | EPHEMERAL | gitignored; per-run wall-clock profiler reports (`profile_helper`, plan 70) — diagnostic output the maintainer hands over, never committed |
| `lib/`, `bin/`, `templates/` (subdirs) | CODE | gitignored + untracked; regenerated by `install.sh`/`update.sh` `cp -R` (the node_modules model) |
| `command-refs/` (subdir) | CODE | gitignored + untracked; relocated slash-command reference files, regenerated by the `scripts/emitters/claude.py` emit (plan 63 — moved out of `.claude/commands/` so they stop leaking into the `/` menu as phantom commands) |

- **VERSIONED** — carry history or setup identity; stay tracked. Only `memory.md` + `spec-stamps.jsonl` have a per-feature delta, and that delta rides the `/devforge:finalize` squash (a scoped, deliberate narrowing of the plan 33/37 D3 runtime-state exclusion — see `src/commands/finalize/main.md` PHASE 2).
  - **`memory.md`'s READ lane (plan 74).** `src/devforge/lib/_shared/memory.py` is the SINGLE owner of the `.devforge/memory.md` path literal, of the three-state probe (`absent` / `stub` / `populated`), and of the bounded excerpt/digest reads. **The excerpt is SECTION-AWARE, not a positional slice** (plan 79): the file is parsed into its `## ` sections, the pre-heading title is dropped, a section named on the module's exclusion list (`## Task Outcomes`) is dropped outright, a section carrying no populated content is dropped heading and all, the NEWEST entries in a section are the ones that survive when a section must be cut, and any cut is DECLARED by a marker line under that section's heading — so a reader can always tell "nothing recorded" from "recorded, not shown". The digest is the separate flat first-N-non-blank-lines read that `/devforge:implement` consumes. A `populated` file can therefore render an EMPTY excerpt, when every populated line sits in an excluded section — an accepted probe/read divergence, not a defect. Every consumer imports it; the literal exists in exactly one place, because it previously drifted across 13 helper files — two of which read a legacy location under `.claude/` that is present in NO consumer install, so their reads silently returned nothing. (That dead path is deliberately not spelled out here: the plan-74 gate's fourth rule fails the build on the literal appearing anywhere under `src/`, which is what stops the class being re-authored.) `absent` and `stub` are both CORRECT states, never faults: the installer ships this stub into every install, so the file almost always exists while carrying zero lessons, which is exactly why the probe is three-state rather than a boolean. Each of the 20 emitted commands carries exactly one declared memory disposition (13 `READS` / 7 `N/A`) with a recorded reason, enforced by the maintainer-side gate `scripts/verify-memory-lane.py`. That gate requires BOTH halves for a `READS` command — a read is performed AND a consuming surface names the field — because a preflight that builds an excerpt nobody reads back is the defect it exists to catch. A memory entry is an unverified prior-session assertion, never a finding: it is re-grounded against the code before it can support a conclusion.
  - **`manifest.json`'s `projectOwned` DOCUMENTS, it does not ENFORCE.** The list is read once (`update.sh`) and consumed only to compute a count for a summary line. A file is safe from overwrite because it is absent from `templateOwned` / `templateDerived` / `mergeFiles`, never because it appears here. `memory.md`'s actual protection from the `install.sh` bulk `cp -R` is the preserve-and-restore guard in `install.sh` itself (plan 74 OQ-5), not its `projectOwned` entry.
- **EPHEMERAL** — per-cycle working state, single-slot scratch, pointers, logs, locks. Gitignored via the dedicated `src/files/devforge.gitignore` template (merged into a consumer's `.gitignore` by `install.sh` + `update.sh`); already-tracked ones are untracked by `update.sh`'s one-time `git rm --cached` migration.
- **FEATURE-SCOPED** — the persistent per-feature records, committed per-step (plan 37) and folded into `/devforge:finalize`'s squash: everything under `specs/<feature>/`, from the `/devforge:research` / `/devforge:discover` intake artifacts that open the directory through to `summary.md` (plan 68). Legacy top-level `research/<date>-<slug>/*` + `discover/<date>-<slug>.*` reports exist only in installs whose intake predates that layout; they are never written to again and nothing migrates them.
- **CODE (install-reproducible)** — the forge's own helper code the installer copies into every consumer: `.devforge/lib/` (Python helper subpackages + `*_helper` launchers), `.devforge/bin/`, `.devforge/templates/`, plus `.devforge/command-refs/` (plan 63 — the relocated slash-command reference files, formerly emitted under `.claude/commands/<name>/references/`, moved out because Claude Code recursively colon-namespaces every `.md` it finds under `.claude/commands/`). Gitignored + untracked (the node_modules model) via the same `src/files/devforge.gitignore` template + `scripts/devforge-state-migrate.sh` `git rm --cached` migration as the EPHEMERAL class; regenerated by `install.sh` / `update.sh` `cp -R` (for `lib`/`bin`/`templates`) or the `scripts/emitters/claude.py` emit (for `command-refs`) on every run, so none of it is ever git-tracked. This is what stops the consumer's CBM graph from indexing forge-internal code (plan 56) and from surfacing phantom `/` menu entries (plan 63).
  - **Fresh-clone onboarding.** A clone that does NOT re-run forge install/update lacks these helpers, so forge commands fail on helper invocation until an install/update run restores them — exactly like `npm install` restoring `node_modules`. This is an accepted onboarding step, not a bug; no guard runs at command time — plan 72 added an auto-repair guard to `update.sh` (an install whose `.devforge/lib` holds no executable `*_helper` launcher is repaired on the next update run, regardless of version), but a clone that runs neither installer is still on its own (plan 56 OQ-1, closed on the update path by plan 72).
  - **`.devforge/template/` (SINGULAR) is NOT in the CODE class — it stays fully tracked.** It is `update.sh`'s agent three-way-merge baseline + NEW/REMOVED agent enumeration source, so untracking it would risk blind agent overwrite + skipped pruning on the next `update.sh`. Do NOT untrack it. (Note `templates/` plural IS in the CODE class; `template/` singular is NOT — they differ by one character.)
  - **Rollout.** The untrack migration is carried by a FULL `install.sh` or `update.sh` run (both source `scripts/devforge-state-migrate.sh`); a surgical `install.sh --only <cmd>` patch exits before the migration and does NOT carry it — consistent with plan 49's OQ-3 pull-based rollout (no separate back-fill command). This matches the pre-existing plan-49 migration behavior; it is not a plan-56 regression.

**Scratch ≠ record — do not conflate.** `.devforge/research-report.json` (EPHEMERAL single-slot scratch, gitignored) is a DIFFERENT file from `specs/NNN-slug/research-handoff.json` (FEATURE-SCOPED persistent record, committed). Same for `.devforge/discover-report.json` vs `specs/NNN-slug/discover-handoff.json`. The `.devforge/` copy is overwritten by the next run of that command; the copy inside the feature directory is the durable artifact.

The trap is sharpest for the two files that share a NAME: `specs/NNN-slug/research-report.md` is the durable RECORD `/devforge:research` saves, while `.devforge/research-report.json` is the EPHEMERAL run state its setters mutate during the run. Same words, different class — read the class off the location, never off the name.

## Naming Rules

### Feature Directories
- **Format**: `NNN-feature-name` where NNN is a zero-padded sequential number
- Scan existing `specs/` directories to determine the next number
- Examples: `001-user-auth`, `002-cart-pricing`, `003-order-history`
- Feature name part: lowercase kebab-case, 2-4 words

### Task Files
- **Format**: `NNN-short-task-title.md` where NNN is a zero-padded sequential number within the feature
- Numbers are sequential within the feature: 001, 002, 003...
- Title part: lowercase kebab-case, concise description of the task
- Examples: `001-define-types.md`, `002-create-repository.md`, `003-build-form-component.md`

### How to Determine Next Feature Number
1. List all directories in `specs/`
2. Extract the highest NNN prefix
3. Next feature = highest + 1 (or 001 if empty)

This scan runs at intake: `/devforge:research` and `/devforge:discover` call `allocate-feature-dir` once the user confirms the save. `/devforge:specify` reads the number off the directory it resolved and allocates none.

## Task File Format

Each task file (`specs/NNN-feature/tasks/NNN-title.md`) contains:

```markdown
# Task NNN: [Title]

**Feature**: [feature directory name]
**Agent**: [assigned agent name]
**Status**: Pending | In Progress | Complete | Skipped
**Depends on**: [task numbers] or None
**Blocks**: [task numbers] or None
**Spec criteria**: AC-[numbers]
**Review checkpoint**: Yes/No
**Context docs**: [doc file paths] or None
**Property targets**: [comma-separated pure-builder target names]
**Dead code removal**: [semicolon-separated literal anchor tokens]

## Files

| File | Action | Description |
|------|--------|-------------|
| [path] | Create/Modify | [what changes] |

## Description

[Detailed description of what to do]

## Change Details

- In `path/to/file`:
  - [specific change]
- In `path/to/other`:
  - [specific change]

## Contracts

### Expects (checked before execution)
- [precondition: what must be true in the codebase before this task runs]

### Produces (checked after execution)
- [postcondition: what must be true in the codebase after this task completes]

## Done When

- [ ] [Testable condition specific to this task]
- [ ] [Another task-specific condition]
- [ ] No debug artifacts left in changed files
- [ ] Type checker passes on changed files (see Development Commands section)
- [ ] Linter passes on changed files (see Development Commands section)
- [ ] No new secrets or credentials in code

## Completion Notes

[Filled in by /devforge:implement after completion]
**Completed**: [date/time]
**Files changed**: [actual files]
**Contract**: Expects [X/Y verified] | Produces [X/Y verified]
**Notes**: [deviations or observations]
```

The `**Property targets**:` line is OPTIONAL — `render-task-file` emits it only when passed `--property-targets`, so it appears solely on the dedicated property-test tasks `/devforge:breakdown` creates for `/devforge:plan`-declared pure-builder targets. Its comma-separated target names are exact-match-consumed by `breakdown_helper verify-property-coverage` (the Phase 3.5 property-coverage gate). Ordinary tasks omit the line entirely.

The `**Dead code removal**:` line is likewise OPTIONAL — `render-task-file` emits it only when passed `--dead-code-removal`, so it appears solely on the OWNING task(s) of `/devforge:plan`-declared change-induced dead-code rows. Its value is a SEMICOLON-separated list of literal anchor tokens (semicolon, not comma — anchor tokens are code fragments that commonly contain commas; the schema rejects a semicolon INSIDE a token at creation), split-and-exact-match-consumed by `breakdown_helper verify-dead-code-coverage` (the Phase 3.5 dead-code-coverage gate — every declared row covered by exactly ONE task) and confirmed removed post-change by `verify_helper check-dead-code-removal` at `/devforge:verify`. Ordinary tasks omit the line entirely.

## File Lifecycle

```
research     → displays report in console; on a confirmed save allocates specs/NNN-name/ + the spec/NNN-name branch and writes research-report.md + research-handoff.json there (+ probe-script.<ext> when a tier-1.5 probe ran); a declined save leaves nothing in the repo
discover     → displays report in console; on a confirmed save allocates specs/NNN-name/ + the spec/NNN-name branch and writes discovery-report.md + discover-handoff.json there; a declined save leaves nothing in the repo
specify      → creates specs/NNN-name/spec.md inside the feature directory intake already allocated
spec-check   → creates specs/NNN-name/spec-check.md (SMT AC-consistency report) + specs/NNN-name/spec-check-seed.json ONLY on a MATCHING REVISE-SPEC pick (user picks "Revise spec" AND the recommendation was REVISE-SPEC; a cross-pick / Consistent / Dismiss writes no seed — the plan-39 verdict-gate) (backward re-entry seed → /devforge:specify); opt-in, between /devforge:specify and /devforge:plan
plan         → creates specs/NNN-name/plan.md (+ research.md, data-model.md, contracts.md if needed)
breakdown    → creates specs/NNN-name/tasks/001-xxx.md, 002-xxx.md, ... + specs/NNN-name/breakdown-handoff.json (machine contract for /devforge:implement; task .md files stay human-readable)
implement    → updates individual task file status + completion notes
review       → creates specs/NNN-name/review.md (emergent cross-task findings; findings only, no verdict)
verify       → updates specs/NNN-name/spec.md status to Complete; Phase 9 triage may create bugs/NNN-xxx.md
summarize    → creates specs/NNN-name/summary.md (PR-ready feature summary)
finalize     → squashes WIP commits + surgical docs/ updates via tech-writer
report-bug   → creates bugs/NNN-description.md
fix          → writes a [WIP] commit in the source repo (no spec/bugs/ files written)
audit        → creates audits/YYYY-MM-DD-audit.md (dated, not overwritten; standalone, not in workflow chain)
```

## Status Tracking

### Spec Status (in spec.md header)
- `Draft` — initial creation, not yet approved
- `Approved` — user approved, ready for plan command
- `In Progress` — tasks are being executed
- `Complete` — all acceptance criteria verified

### Plan Status (in plan.md header)
- `Draft` — initial creation
- `Approved` — user approved, ready for breakdown

### Task Status (in each task file header)
- `Pending` — not yet started
- `In Progress` — currently being executed
- `Complete` — done and verified
- `Skipped` — `/devforge:implement` gate skip path: the task was not executed (its working-tree edits were reset). Counts as satisfied for downstream dependency resolution.

## Cross-Referencing

- Every plan.md MUST reference its spec
- Every task file MUST reference which acceptance criteria (AC-N) it addresses
- Task dependencies reference other task numbers within the same feature
- The verify command reads the spec and all task files to cross-check

## Documentation Rules

### Audience
Docs/ are LLM context source first, dev-greppable second. Density and structure are optimized for LLM consumption (compact, parseable, cite-backed); humans grep them as a side benefit.

### File Naming
- Tier files use fixed names: `overview.md`, `architecture.md`
- Concern dirs use the source-subfolder name verbatim (e.g., `docs/<package>/order/index.md` for `<package>/src/order/`)
- Package dirs mirror the package's index.json key (e.g., `docs/module/apps/app/`)

### When Docs Are Generated
- /devforge:generate-docs (Plan F) walks all tiers bottom-up: concerns → packages → project
- Incremental: each doc carries `source_stamp` in frontmatter; helper skips regeneration when the stamp matches the current source-subfolder content hash
- Manual `--full` flag forces regeneration of everything

### Doc Structure (LLM-first density format)

Every doc opens with YAML-subset frontmatter, then fixed section anchors.

**Concern doc** (`docs/<package>/<concern>/index.md`):
```markdown
---
concern: <name>
package: <package-path>
files: <count>
source_stamp: <sha256-prefix>
last_indexed: <YYYY-MM-DD>
---

# <concern>

## Purpose
<1-2 sentences; no preamble>

## Structure

```text
<ASCII tree of files in subfolder; each leaf annotated `  # <≤60 chars>`>
```
```

**Package architecture** (`docs/<package>/architecture.md`): `## Layers` + `## Patterns` sections, each entry cite-backed.

**Package overview** (`docs/<package>/overview.md`): `## Purpose` + `## Concerns` (list with cite-backs to concern dirs).

**Project overview/architecture** (`docs/overview.md`, `docs/architecture.md`): same shape as package tier but at project scope; package list / cross-package layers.

### Density rules (validate-doc enforces)
- Banned phrases: "This document...", "In this section...", "We will...", "various", "several", "many", "some", "other"
- Per-bullet length cap: ≤200 chars (Layers/Patterns/Concerns/Packages/Cross-Cuts); Structure annotations: ≤60 chars
- Concern docs ship `## Purpose` + `## Structure` only (Hazards moved to `/devforge:audit`; Glossary tier dropped — Purpose paragraphs surface terms in context)
- No prose tables for structural data — exports/types/deps/callees lists live in CBM, NOT in md

### CBM auto-indexing
Md files are walked by `codebase-memory-mcp index_repository` automatically. Their content becomes searchable via `search_code`. No separate registration step.

### Rules
- Every cite-back must resolve at validation time (file exists, line range valid)
- Vue cite-backs (`<f>.vue:N`) are validated through the `.vue.ts.map` sourcemap chain
- Concerns are derived from `src/` subfolders enumerated by /devforge:init-forge's index.json
- `docs/api/`, `docs/features/`, `docs/guides/` are NOT generated under Plan F

## Bug Report Rules

### Directory
- Location: `bugs/` at project root (parallel to `specs/` and `docs/`)
- Each bug is a single file: `NNN-short-description.md`

### Naming
- **Format**: `NNN-short-description.md` where NNN is a zero-padded sequential number
- Scan existing `bugs/` files to determine the next number
- Description part: lowercase kebab-case, 2-4 words
- Examples: `001-null-cart-total.md`, `002-missing-auth-check.md`, `003-broken-date-format.md`

### Status Lifecycle
- `Open` — reported, not yet being fixed
- `In Progress` — currently being fixed
- `Fixed` — fix applied and verified

### Bug File Format

```markdown
# Bug NNN: [Short Title]

**Status**: Open | In Progress | Fixed
**Severity**: Critical | Warning | Info
**Source**: verify | manual
**Feature**: [spec path, e.g. specs/001-feature/spec.md — or N/A for standalone bugs]
**AC**: [AC-N — or N/A if not tied to an acceptance criterion]
**Reported**: [YYYY-MM-DD]
**Fixed**: [YYYY-MM-DD or empty]

## Description

[What is wrong — 1-3 sentences. Use behavioral description, not line numbers.]

## Expected Behavior

[What should happen — from the spec's acceptance criterion. Omit for manual bugs where this isn't known.]

## Actual Behavior

[What actually happens — from verification evidence or user observation. Omit for manual bugs where this isn't known.]

## File(s)

| File | Detail |
|------|--------|
| [path/to/file] | [area or function — not line numbers, they shift after other fixes] |

## Evidence

[How this was discovered — error message, verification report excerpt, user observation]

## Related Issues

[Other bugs filed in the same batch, if any. Omit if standalone.]
- bugs/NNN-xxx.md — [short title]

## Fix Notes

[Filled in after resolution — root cause, what was changed, commit reference]
```

**Field notes:**
- `Feature` and `AC` are populated by verify. report-bug sets them to N/A.
- `Expected Behavior` and `Actual Behavior` are populated by verify (from spec + verification evidence). report-bug may omit them if unknown.
- `Related Issues` is populated when multiple bugs are filed in the same batch. Helps whoever resolves the batch know what else is being addressed.
- `File(s)` should use area/function references, not line numbers — line numbers shift after other fixes are applied.

### How Bug Files Are Created
- verify Phase 9 — user requests batch bug filing for verification issues
- report-bug — standalone manual bug reporting

### How Bug Files Are Resolved
- Manual: the user edits `**Status**: Fixed` after resolving the issue (the `Open → In Progress → Fixed` lifecycle is not driven by any command)
- Re-running `/devforge:verify` re-proves the ACs against the remediated diff

## Cleanup Rules

- Do NOT delete feature directories after completion — they serve as documentation
- Do NOT modify completed specs unless explicitly asked
- Task files are permanent records of what was done and why