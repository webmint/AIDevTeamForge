# Storage Rules — Specs, Plans, Tasks, and Docs

These rules define how all development artifacts are organized. All commands MUST follow them.

## Directory Structure

```
bugs/
  NNN-short-description.md           # Bug reports (/report-bug or /verify triage)

research/
  YYYY-MM-DD-[topic-slug].md          # Research reports (/research) — exploratory, pre-spec

audits/
  YYYY-MM-DD-audit.md                  # Adversarial codebase audits (/audit) — periodic, dated, not auto-committed
  .gitignore                           # Auto-created on first /audit run (excludes .tmp-* files)

specs/
  NNN-feature-name/                # One numbered directory per feature
    spec.md                        # Feature specification (/specify)
    plan.md                        # Technical implementation plan (/plan)
    research.md                    # Research findings (/plan) — optional
    data-model.md                  # Entity definitions (/plan) — optional
    contracts.md                   # API contracts (/plan) — optional
    tasks/                         # Task breakdown (/breakdown)
      001-short-task-title.md      # Individual task files
      002-short-task-title.md
      003-short-task-title.md

docs/
  overview.md                      # Project overview and getting started
  architecture.md                  # Architecture patterns, layers, data flow
  features/                        # Feature-specific docs (one file per feature area)
    [feature-name].md
  api/                             # API docs (one file per resource/domain)
    [resource-name].md
  guides/                          # How-to guides
    [topic].md
```

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

## Task File Format

Each task file (`specs/NNN-feature/tasks/NNN-title.md`) contains:

```markdown
# Task NNN: [Title]

**Feature**: [feature directory name]
**Agent**: [assigned agent name]
**Status**: Pending | In Progress | Complete
**Depends on**: [task numbers] or None
**Blocks**: [task numbers] or None
**Spec criteria**: AC-[numbers]
**Review checkpoint**: Yes/No
**Context docs**: [doc file paths] or None

## Files

| File | Action | Description |
|------|--------|-------------|
| [path] | Create/Modify | [what changes] |

## Description

[Detailed description of what to do]

## Change Details

- In `path/to/file.ts`:
  - [specific change]
- In `path/to/other.ts`:
  - [specific change]

## Contracts

### Expects (checked before execution)
- [precondition: what must be true in the codebase before this task runs]

### Produces (checked after execution)
- [postcondition: what must be true in the codebase after this task completes]

## Done When

- [ ] [Testable condition specific to this task]
- [ ] [Another task-specific condition]
- [ ] No debug artifacts (console.log, debugger, etc.) in changed files
- [ ] Type checker passes on changed files (see Type Check Command in CLAUDE.md)
- [ ] Linter passes on changed files (see Lint Command in CLAUDE.md)
- [ ] No new secrets or credentials in code

## Completion Notes

[Filled in by /execute-task after completion]
**Completed**: [date/time]
**Files changed**: [actual files]
**Contract**: Expects [X/Y verified] | Produces [X/Y verified]
**Notes**: [deviations or observations]
```

## File Lifecycle

```
/research     → displays report in console, optionally saves to research/YYYY-MM-DD-[topic-slug].md
/specify      → creates specs/NNN-name/spec.md
/plan         → creates specs/NNN-name/plan.md (+ research.md, data-model.md, contracts.md if needed)
/breakdown    → creates specs/NNN-name/tasks/001-xxx.md, 002-xxx.md, ...
/execute-task → updates individual task file status + completion notes
/review       → creates specs/NNN-name/review.md (security, performance, test findings)
/verify       → updates specs/NNN-name/spec.md status to Complete; Phase 9 triage may create bugs/NNN-xxx.md
/summarize    → creates specs/NNN-name/summary.md (PR-ready feature summary)
/finalize     → squashes WIP commits, generates feature docs in docs/
/report-bug   → creates bugs/NNN-description.md
/fix          → updates bugs/NNN-description.md status to Fixed (when given a bug file)
/audit        → creates audits/YYYY-MM-DD-audit.md (dated, not overwritten; standalone, not in workflow chain)
```

## Status Tracking

### Spec Status (in spec.md header)
- `Draft` — initial creation, not yet approved
- `Approved` — user approved, ready for /plan
- `In Progress` — tasks are being executed
- `Complete` — all acceptance criteria verified

### Plan Status (in plan.md header)
- `Draft` — initial creation
- `Approved` — user approved, ready for /breakdown

### Task Status (in each task file header)
- `Pending` — not yet started
- `In Progress` — currently being executed
- `Complete` — done and verified

## Cross-Referencing

- Every plan.md MUST reference its spec
- Every task file MUST reference which acceptance criteria (AC-N) it addresses
- Task dependencies reference other task numbers within the same feature
- The /verify command reads the spec and all task files to cross-check

## Documentation Rules

### File Naming
- Lowercase kebab-case: `cart-management.md`, `order-api.md`
- Group by topic, not by date or ticket number
- One file per logical feature area — don't create a new file per task

### When Docs Are Updated
- After every `/execute-task` — the tech-writer agent runs automatically
- The agent reads ONLY the completed task, spec, and changed files
- It updates existing docs or creates new ones in the appropriate subfolder
- Not every task produces doc changes — internal refactoring, bug fixes, and test-only changes are skipped

### Doc File Structure
```markdown
# [Topic Name]

## Overview
[1-2 sentences: what this is and why it exists]

## How It Works
[Explanation with code examples from actual implementation]

## Usage
[How to use it — code examples]

## Configuration
[If applicable]

## Related
- [Links to related docs]
```

### Rules
- Every code example must come from the actual implementation — no pseudocode
- Update existing docs instead of creating new files when possible
- `docs/architecture.md` is updated when architectural patterns change
- `docs/features/` files are updated when feature behavior changes
- `docs/api/` files are updated when API contracts change

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
- `In Progress` — currently being fixed via `/fix`
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
| [path/to/file.ts] | [area or function — not line numbers, they shift after other fixes] |

## Evidence

[How this was discovered — error message, verification report excerpt, user observation]

## Related Issues

[Other bugs filed in the same batch, if any. Omit if standalone.]
- bugs/NNN-xxx.md — [short title]

## Fix Notes

[Filled in by /fix after resolution — root cause, what was changed, commit reference]
```

**Field notes:**
- `Feature` and `AC` are populated by `/verify`. `/report-bug` sets them to N/A.
- `Expected Behavior` and `Actual Behavior` are populated by `/verify` (from spec + verification evidence). `/report-bug` may omit them if unknown.
- `Related Issues` is populated when multiple bugs are filed in the same batch. Helps `/fix` know what else is being addressed.
- `File(s)` should use area/function references, not line numbers — line numbers shift after other fixes are applied.

### How Bug Files Are Created
- `/verify` Phase 9 — user requests batch bug filing for verification issues
- `/report-bug` — standalone manual bug reporting

### How Bug Files Are Resolved
- `/fix bugs/NNN-xxx.md` — reads the bug file, fixes the issue, updates status to Fixed
- Manual: user can edit the status directly if fixing outside the workflow

## Cleanup Rules

- Do NOT delete feature directories after completion — they serve as documentation
- Do NOT modify completed specs unless explicitly asked
- Task files are permanent records of what was done and why