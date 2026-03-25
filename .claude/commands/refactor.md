# /refactor — Focused Code Refactoring Workflow

Lightweight workflow for restructuring code without changing behavior. Uses the project's agents, enforces all constitution rules, and requires approval before applying changes.

## Usage
```
/refactor path/to/file.ts
/refactor path/to/file.ts "extract validation logic into utility"
/refactor path/to/file.ts:42-87
/refactor path/to/file.ts:42-87 "simplify conditional chain"
/refactor
```

## Arguments
- `$ARGUMENTS` — File path (required), optional line range (`:start-end`), and optional goal in quotes. Supports both manual input and IDE-injected context (JetBrains plugin passes active file/selection). If empty, ask the user to specify a file.

## When to Use /refactor vs /specify

Use `/refactor` when:
- The change is behavior-preserving (restructuring, renaming, extracting, simplifying)
- The scope is small and localized (1-5 files affected)
- No new features or behavior changes are needed

Use `/specify` instead when:
- The refactoring requires behavior changes or new features
- Multiple components need coordinated architectural changes
- More than 5 files are affected
- The restructuring requires design decisions or trade-offs

If during analysis (Phase 2) the refactoring turns out to be larger than expected, STOP and recommend the user run `/specify` instead. Do not attempt large refactors through `/refactor`.

## PHASE 0: Recovery Check

Before anything else, check if a previous refactoring was interrupted.

### 0.1: Check for WIP Marker

Read `.claude/wip.md`. If it does NOT exist, skip to PHASE 1.

If it DOES exist, a previous execution was interrupted. Read the WIP marker to determine:
- What was being refactored
- Which phase it was in when interrupted
- What files were being modified

### 0.2: Assess State

Run these checks:
1. `git status` — are there uncommitted changes?
2. `git log --oneline -5` — are there `[WIP]` commits?
3. Read the WIP marker for context

### 0.3: Present Recovery Options

Report findings to the user and offer exactly these options:

```
Interrupted refactoring detected: [description]
Interrupted during: Phase [N] — [phase name]

Git state:
- Uncommitted changes: [yes/no] ([list files])
- WIP commits found: [yes/no] ([count])

Options:
1. **Resume** — Re-run verification on current state and continue from the interrupted phase.
2. **Rollback and retry** — Reset to the last clean checkpoint, then re-execute the refactoring from scratch.
3. **Rollback and abandon** — Reset to pre-WIP state. You handle it manually.
4. **Keep changes, clear marker** — Keep current git state as-is, delete WIP marker only.
```

Wait for user to choose. Execute their choice using the same recovery logic as `/execute-task` Phase 0.3.

## PHASE 1: Load Context

### 1.1: Read Project Rules

1. Read `constitution.md`
2. Read `.claude/memory/MEMORY.md`
3. Read `CLAUDE.md` — note the Source Root (if not `.`, this is a wrapper project)

### 1.2: Parse Arguments

Parse `$ARGUMENTS` to extract:

1. **If empty** — ask the user to specify a file path and optionally what they want to refactor
2. **First token** = file path. If it contains `:` followed by a digit pattern (e.g., `src/foo.ts:42-87`), split into file path and line range
3. **Remaining tokens** = optional goal string (strip surrounding quotes if present)
4. **If IDE-injected context** includes selected code, use it to narrow the refactoring scope to that selection

If the file does not exist, stop with an error.

### 1.3: Read Target Code

1. Read the target file in full (needed for context regardless of line range)
2. If a line range is specified, note those lines as the primary refactoring scope
3. If selected code was injected by the IDE, locate it in the file and use it as the scope

### 1.4: Identify Related Files

1. Use Grep to find files that import from or are imported by the target file
2. Read the most closely related files (up to 5) — you need to know what utilities, types, and patterns already exist before proposing extractions
3. Check `.claude/memory/MEMORY.md` for known pitfalls in this area

### 1.5: Scope Check

Estimate how many files the refactoring will touch:
- **How many files will need changes?** (imports, shared types, etc.)
- **Does this require architectural decisions?**

If the refactoring would affect more than 5 files or requires architectural changes:
```
This refactoring appears larger than expected:
- Estimated files affected: [N]
- Reason: [why it's complex]

Recommend running `/specify "[refactoring description]"` instead for proper planning.
Proceed with /refactor anyway? (not recommended)
```

Wait for user decision. If they say proceed, continue. If not, stop.

## PHASE 2: Analyze

Perform a structured analysis of the code against refactoring categories. This is the core of `/refactor`.

### 2.1: Detect Code Characteristics

Determine what the code is:
- **File layer**: frontend component, backend service, shared utility, type definitions, etc.
- **Pattern type**: component, composable/hook, store, repository, controller, middleware, utility, etc.
- **Metrics**: function count, longest function line count, nesting depth, import count

### 2.2: Scan for Refactoring Opportunities

Check the code against these categories, ordered by priority. If the user provided a goal, prioritize that category and focus the analysis there:

1. **Long Functions** (>40 lines per constitution rule 3.5) — identify extraction candidates with clear responsibilities
2. **Deep Nesting** (>3 levels) — identify early-return conversions and guard clauses
3. **SOLID Violations** — single responsibility violations (functions/components doing multiple things), tight coupling, concrete dependencies where abstractions should be used
4. **DRY Violations** (3+ occurrences per constitution rule 3.6) — duplicated logic that should be extracted into a shared utility or function
5. **Type Safety Issues** — `any` types without justification, missing null checks, unsafe type assertions
6. **Naming Inconsistencies** — identifiers that don't match codebase conventions found in related files
7. **Dead Code** — unused functions, variables, imports, commented-out blocks
8. **Pattern Violations** — code that doesn't follow the patterns established elsewhere in the codebase (compare with similar files read in Phase 1.4)
9. **Complexity** — complex conditionals that could be simplified, unnecessary abstractions that add indirection without value

For each opportunity found, note: the category, affected lines, what's wrong, what the improvement looks like, and which constitution rule or principle it addresses.

### 2.3: Select Agent

Based on the file location and code characteristics from 2.1, select the execution agent:

- If the file is a **UI component, view, or deals with styling/state management/routing** → **frontend-engineer**
- If the file is in the **core/domain/backend layer** (service, repository, use case, controller, middleware) → **architect**
- If the file is a **backend endpoint or route handler** → **backend-engineer**
- If the file is a **shared utility or type definition** → **architect**
- If unclear → **architect** (safest default for structural changes)

Cross-reference with `CLAUDE.md` project structure and `{{PROJECT_PATHS}}` in agent templates to confirm the selection.

### 2.4: Present Refactoring Proposal

**HARD GATE** — Present the proposal to the user. No code changes until approved.

```
## Refactoring Proposal

**File**: [path]
**Scope**: [whole file / lines X-Y]
**Agent**: [selected agent name]
**Goal**: [user's goal if provided, or "General code quality improvement"]

### Opportunities Found

#### 1. [Category]: [Short description]
**Priority**: High / Medium / Low
**Lines**: [start-end]
**Current**: [brief description or short code snippet showing the issue]
**Proposed**: [what the refactored version would look like — description or snippet]
**Rationale**: [which constitution rule or principle this addresses]

#### 2. [Category]: [Short description]
...

### Files That Will Change
- [file path]: [what changes]
- [file path]: [what changes]

### Risk Assessment
- **Behavioral changes**: None (this is a pure refactoring)
- **Test impact**: [will existing tests need updating? why?]
- **Import changes**: [will other files' imports break?]

Approve this proposal to proceed? You can also:
- **Approve all** — apply everything
- **Approve specific items** — e.g., "approve 1 and 3"
- **Modify** — request changes to the proposal
- **Cancel** — exit with no changes
```

Wait for user response. Record which items were approved. If the user cancels, exit cleanly with no changes (no WIP marker has been created yet).

**Bugs noticed during analysis**: If actual bugs are discovered (not structural issues), note them separately as "Bugs noticed (out of scope — use `/fix` for these)" and do NOT include them in the refactoring plan.

## PHASE 3: Pre-Flight Check

Before writing ANY code, verify:

1. **Constitution populated**: If `constitution.md` contains `_Run /constitute to populate_`, stop immediately and inform the user: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/refactor`."
2. **Constitution compliance**: Does the planned refactoring comply with all NON-NEGOTIABLE rules?
3. **Behavior preservation**: Verify that approved changes are genuinely behavior-preserving. If any change would alter observable behavior, flag it and remove from scope
4. **Memory check**: Does MEMORY.md have any warnings about similar changes or this area of code?
5. **File state check**: Are the target files in a clean state? (`git status`)
6. **Scope constraint**: The refactoring must touch ONLY the files identified in the proposal. If more files need changing, re-assess scope (Phase 1.5)

If ANY pre-flight check fails, stop and inform the user with specifics.

### 3.1: Create WIP Marker and Clean Checkpoint

1. Create a git checkpoint BEFORE any changes:
   ```
   git commit -m "[checkpoint] Pre-refactor: [short description]" --allow-empty
   ```

2. Write `.claude/wip.md`:
   ```markdown
   # Work In Progress

   ## Refactoring
   Target: [file path]
   Goal: [description]
   Type: refactoring

   ## Started
   Phase: 4 (Apply Refactoring)

   ## Files Being Modified
   - [list from proposal]

   ## Rollback Point
   Commit: [hash from the checkpoint commit above]
   ```

## PHASE 4: Apply Refactoring

### 4.1: Launch Agent

Launch the selected agent (from Phase 2.3) with the approved refactoring plan.

Agent prompt must include:

```
You are executing an approved refactoring plan.

## Target
[File path, line range if applicable]

## Approved Refactoring Actions
[Only the actions the user approved — list each with its number, category, and proposed change]

## Context Files
[List of related files the agent should read for context]

## Rules
1. Make ONLY the approved refactoring changes — nothing more
2. This is a BEHAVIOR-PRESERVING refactoring — no functional changes
3. Follow the project's constitution
4. Known pitfalls for this area: [from MEMORY.md]
5. Every file you change must pass TypeScript compilation
6. Every file you change must pass linting
7. Preserve all existing public API signatures unless the refactoring explicitly changes them
8. Update imports in consuming files if you move or rename exports

## Do NOT
- Change behavior or functionality
- Add features
- Fix bugs you notice (note them in your report, don't fix)
- Refactor code outside the approved scope
- Change test assertions (test file restructuring is OK if imports changed)
```

After the agent completes, commit:
```
git add [files you modified] .claude/wip.md && git commit -m "[WIP] Refactor: [short description] — refactoring applied"
```

Update `.claude/wip.md` — change Phase to `5 (Verify)`.

## PHASE 5: Verify (with Self-Repair)

Run verification on all changed files:

1. **TypeScript compiles**: Run `tsc --noEmit` (or project equivalent from CLAUDE.md)
2. **Linter passes**: Run lint on all changed files
3. **Project builds** (if Build Command is specified in CLAUDE.md): Run the build command. For wrapper mode projects, run inside the Source Root directory. Skip this check if no Build Command is configured.
4. **Tests pass**: Run existing tests on the affected code area (if test infrastructure exists)
5. **Behavior preservation**: Verify that function signatures, exported APIs, and test assertions are still valid
6. **Wrapper isolation check** (wrapper mode only): Verify no Claude artifacts were created inside the Source Root

**If ALL checks pass** → proceed to Phase 6.

**If any check fails** → enter the self-repair loop (max 3 attempts):

For each repair attempt:
1. Collect all error output (tsc errors, lint errors, build errors, test failures)
2. Apply a targeted fix for ONLY those errors
3. Commit:
   ```
   git add [files you modified] .claude/wip.md && git commit -m "[WIP] Refactor: [short description] — repair attempt [M]/3"
   ```
4. Re-run ALL verification checks

**If verification passes after any attempt** → proceed to Phase 6.

**If all 3 repair attempts are exhausted** → STOP:
- Report the remaining errors to the user
- Keep the WIP marker and commits for inspection
- Suggest: "Run `/refactor` again after manually addressing these errors, or use recovery options"

## PHASE 6: Code Review

Launch the **code-reviewer** agent on ALL changed files.

Provide the agent with:
1. The list of changed files (`git diff --name-only` against the checkpoint commit)
2. The refactoring description and rationale
3. The constitution
4. Relevant entries from `.claude/memory/MEMORY.md`

The agent will check: constitution compliance, architecture & patterns, type safety, security basics, code quality, and memory pitfalls.

**Additional check for refactoring**: Verify the refactored code actually improves on the original (not a lateral move or regression in readability).

**If the agent returns BLOCK or critical issues**:
- Apply the required fixes
- Re-run verification (Phase 5 checks)
- Commit:
  ```
  git add [files you modified] .claude/wip.md && git commit -m "[WIP] Refactor: [short description] — review fixes"
  ```

**If the agent returns APPROVE or only warnings/info** → proceed to Phase 7.

## PHASE 7: Test Assessment

Launch the **qa-engineer** agent to assess test impact.

Provide the agent with:
1. The changed files and the nature of the refactoring
2. The existing test files related to the changed code (find them via Grep/Glob)
3. The refactoring description

The agent should:
1. **Check if existing tests still pass** — since this is behavior-preserving, they should pass without assertion changes
2. **Check if test imports need updating** — if files were moved or exports renamed, test imports may need adjustment
3. **Assess if the refactoring improves testability** — note if the restructured code is now easier to test
4. **If tests fail**: This indicates the refactoring broke something. Diagnose whether the test failure is due to an import change (fixable) or a behavior change (must rollback that specific change)

**Rules for test decisions:**
- Refactoring should not break tests. If tests fail, something went wrong with the refactoring
- Import/path changes in tests are acceptable fixes
- Test assertion changes are NOT acceptable — that means behavior changed
- Run the test suite on changed areas to confirm

If tests were adjusted (import fixes only), commit:
```
git add [test files you modified] && git commit -m "[WIP] Refactor: [short description] — test import fixes"
```

## PHASE 7.5: Documentation Update (Conditional)

If the refactoring changed any **public API signatures** (renamed exports, moved files that other code imports, changed function signatures) or **restructured architecture** (new modules, changed layer boundaries):

1. Launch the **tech-writer** agent with:
   - The refactoring description and approved actions from Phase 2.4
   - The list of changed files
   - The existing `docs/` folder structure (run Glob on `docs/`)
   - Instruction: "A refactoring changed these files. Check if any public API signatures, import paths, or documented architecture changed. If so, update inline docs (JSDoc/docstrings) and the relevant `docs/` file. If the refactoring was purely internal with no public-facing changes, report 'No doc update needed.'"

2. If the tech-writer made changes, commit:
   ```
   git add docs/ [source files with doc changes] && git commit -m "[WIP] Refactor: [short description] — doc update"
   ```

If the refactoring is purely internal (no public API, import path, or architecture change), skip this phase — but document the skip decision in Phase 8.3's report as: `**Documentation**: Internal refactoring — no public API changes`.

## PHASE 8: Report & Clean Up

### 8.1: Final Commit

Squash all `[WIP]` and `[checkpoint]` commits for this refactoring into a single clean commit.

First, verify WIP commits haven't been pushed to the remote:
```
git log --oneline origin/$(git branch --show-current)..HEAD 2>/dev/null
```
- If this shows commits (or fails because there's no upstream) → WIP commits are **local only** → safe to squash:
  ```
  git reset --soft [checkpoint-commit-hash]
  git commit -m "refactor([area]): [concise description of what was restructured]"
  ```
- If this shows **no commits** (HEAD matches remote) → WIP commits were already pushed → **skip squashing** and keep commits as-is.

Follow the **Commit Convention** section in CLAUDE.md (format and attribution rules).

### 8.2: Delete WIP Marker

Delete `.claude/wip.md`.

### 8.3: Present Report

```
## Refactoring Complete

**Target**: [file path, line range if applicable]
**Goal**: [user's goal or detected opportunities]

**Changes**:
- [file]: [what changed, 1 line]
- [file]: [what changed, 1 line]

**Refactoring actions applied**:
1. [action]: [result]
2. [action]: [result]

**Verification**:
- TypeScript: PASS
- Linter: PASS
- Build: PASS [or SKIP if no build command configured]
- Tests: PASS / [details]
- Code review: [APPROVE / issues addressed]
- Behavior preserved: YES

**Documentation**: [Updated docs/architecture.md / Internal refactoring — no public API changes]

**Commit**: `refactor([area]): [description]`
```

## PHASE 9: Memory Update

If anything noteworthy happened during the refactoring, update `.claude/memory/MEMORY.md`:

- **Refactoring pattern**: If a specific restructuring approach worked well in this area, record it
- **Complex area**: If the code was especially tangled or hard to restructure safely, note it as a caution for future work
- **Gotcha discovered**: If the refactoring revealed a hidden coupling or unexpected dependency, record it

Keep entries concise (1-2 lines each). Only update if there's something genuinely useful for future work — not every refactoring needs a memory entry.

## IMPORTANT RULES

1. **Analyze before refactoring** — never apply changes without a structured analysis and user-approved proposal
2. **Behavior preservation is mandatory** — this is refactoring, not feature development. If the change alters behavior, it belongs in `/fix` or `/specify`
3. **Minimal scope** — refactor the target code, nothing else. No "while I'm here" improvements outside the approved scope
4. **Constitution is law** — the refactored code must comply with all constitution rules. Constitution violations are always critical
5. **Hard gate on proposal** — the user must approve the refactoring plan before any code changes
6. **Partial approval is supported** — the user can approve specific refactoring actions and reject others
7. **Self-repair before escalation** — when verification fails, attempt automatic repair (up to 3 times) before stopping
8. **Scope discipline** — if the refactoring grows beyond 5 files, stop and recommend `/specify`
9. **Crash safety** — always write `wip.md` before making changes and delete it only after the final commit
10. **Verify everything** — even if hooks ran, run explicit verification after the refactoring
11. **Tests should not break** — if tests fail after a pure refactoring, the refactoring introduced a behavior change. Fix or rollback
12. **Memory is selective** — only record genuinely useful patterns and gotchas, not routine refactors