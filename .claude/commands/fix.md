# /fix — Small Bug Fix Workflow

Lightweight workflow for diagnosing and fixing small bugs. Uses the project's agents and enforces all constitution rules without the overhead of the full spec→plan→breakdown pipeline.

## Usage
```
/fix "description of the bug"
/fix "description" --file path/to/suspected/file.ts
/fix bugs/NNN-short-description.md
```

## Arguments
- `$ARGUMENTS` — Either a path to a bug file in `bugs/` (e.g., `bugs/003-null-check.md`), or a description of the bug with an optional `--file` flag. If empty, ask the user to describe the bug.

## When to Use /fix vs /specify

Use `/fix` when:
- The bug is small and localized (1-5 files affected)
- The root cause is likely a single mistake (wrong value, missing check, typo, null reference)
- No architectural changes are needed

Use `/specify` instead when:
- The "bug" is actually a missing feature or behavior change
- Multiple components need coordinated changes
- The fix requires architectural decisions or trade-offs
- You're unsure of the scope

If during diagnosis (Phase 2) the bug turns out to be larger than expected, STOP and recommend the user run `/specify` instead. Do not attempt large fixes through `/fix`.

## PHASE 0: Recovery Check

Before anything else, check if a previous fix was interrupted.

### 0.1: Check for WIP Marker

Read `.claude/wip.md`. If it does NOT exist, skip to PHASE 1.

If it DOES exist, a previous execution was interrupted. Read the WIP marker to determine:
- What was being fixed
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
Interrupted fix detected: [bug description]
Interrupted during: Phase [N] — [phase name]

Git state:
- Uncommitted changes: [yes/no] ([list files])
- WIP commits found: [yes/no] ([count])

Options:
1. **Resume** — Re-run verification on current state and continue from the interrupted phase.
2. **Rollback and retry** — Reset to the last clean checkpoint, then re-execute the fix from scratch.
3. **Rollback and abandon** — Reset to pre-WIP state. You handle it manually.
4. **Keep changes, clear marker** — Keep current git state as-is, delete WIP marker only.
```

Wait for user to choose. Execute their choice using the same recovery logic as `/execute-task` Phase 0.3.

## PHASE 1: Load Context

### 1.0: Input Detection

Determine whether `$ARGUMENTS` is a bug file path or a plain description.

**If `$ARGUMENTS` matches a path to an existing file in `bugs/`** (e.g., `bugs/003-null-check.md`):
1. Read the bug file
2. Extract the **Description** section as the bug description
3. Extract the **File(s)** table — use the first file path as the `--file` target (if specified and not "(not specified)")
4. Extract the **Severity** for context
5. Update the bug file's **Status** from "Open" to "In Progress"
6. Note the bug file path for later update in Phase 8
7. Continue with Phase 1.1 using the extracted description and file

**If `$ARGUMENTS` refers to a `bugs/` path that does NOT exist**:
- Warn: "Bug file not found: [path]. Treating input as a bug description."
- Continue with existing behavior

**If `$ARGUMENTS` does NOT match a bug file path**:
- Proceed with existing behavior (parse description and optional `--file` flag)

### 1.1: Read Project Rules

1. Read `constitution.md`
2. Read `.claude/memory/MEMORY.md`
3. Read `CLAUDE.md` — note the Source Root (if not `.`, this is a wrapper project)

### 1.2: Locate Affected Code

Based on the bug description (and `--file` flag if provided):

1. **If `--file` is provided**: Read that file as the starting point
2. **If no file specified**: Use Grep and Glob to search for code related to the bug description — error messages, function names, component names, etc.
3. Read all files that appear related (up to 10 files for initial scan)
4. Check `.claude/memory/MEMORY.md` for known pitfalls in this area

### 1.3: Scope Check

Estimate the scope of the bug:
- **How many files are likely affected?**
- **Does this require architectural changes?**

If the bug affects more than 5 files or requires architectural changes:
```
This bug appears larger than expected:
- Estimated files affected: [N]
- Reason: [why it's complex]

Recommend running `/specify "[bug description]"` instead for proper planning.
Proceed with /fix anyway? (not recommended)
```

Wait for user decision. If they say proceed, continue. If not, stop.

## PHASE 2: Diagnose

Identify the root cause BEFORE writing any code.

### 2.1: Choose Diagnosis Strategy

**If the bug is a runtime error** (console errors, crashes, white screens, API failures, rendering issues):
- Launch the **runtime-debugger** agent with the bug description
- The agent will: take screenshots (if browser available), check console/logs, trace the error to source code, and report the root cause
- Do NOT ask the agent to fix anything yet — diagnosis only
- Agent prompt should include: "Diagnose only. Do NOT apply any fixes. Report: (1) exact error, (2) root cause file and line, (3) why it happens, (4) suggested minimal fix."

**If the bug is a logic error** (wrong behavior, incorrect calculations, missing validation, data issues):
- Trace the code path manually using Read and Grep
- Follow the data flow from input to output
- Identify where the actual behavior diverges from expected behavior
- Check type definitions for mismatches

**If the bug is a build/compilation error** (TypeScript errors, import issues, dependency problems):
- Run the build/type-check command and read the error output
- Trace each error to its source file
- Check for recent changes that may have caused the regression (`git log --oneline -10`)

### 2.2: Document Root Cause

Before proceeding, clearly state:

```
## Diagnosis

**Bug**: [user's description]
**Root cause**: [what's actually wrong and why]
**File(s)**: [affected file paths with line numbers]
**Fix approach**: [what needs to change — 1-3 sentences]
**Risk**: [what could go wrong with this fix]
```

Present this to the user. **HARD GATE**: Wait for user confirmation before applying the fix. The user must agree with the diagnosis.

## PHASE 3: Pre-Flight Check

Before writing ANY code, verify:

1. **Constitution populated**: If `constitution.md` contains `_Run /constitute to populate_`, stop immediately and inform the user: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/fix`."
2. **Constitution compliance**: Does the planned fix violate any NON-NEGOTIABLE rules?
3. **Memory check**: Does MEMORY.md have any warnings about similar changes or this area of code?
4. **File state check**: Are the target files in a clean state? (`git status`)
5. **Scope constraint**: The fix must touch ONLY the files identified in the diagnosis. If more files need changing, re-assess scope (Phase 1.3).

If ANY pre-flight check fails, stop and inform the user with specifics.

### 3.1: Create WIP Marker and Clean Checkpoint

1. Create a git checkpoint BEFORE any changes:
   ```
   git commit -m "[checkpoint] Pre-fix: [short bug description]" --allow-empty
   ```

2. Write `.claude/wip.md`:
   ```markdown
   # Work In Progress

   ## Fix
   Bug: [short description]
   Type: bugfix

   ## Started
   Phase: 4 (Apply Fix)

   ## Files Being Modified
   - [list from diagnosis]

   ## Rollback Point
   Commit: [hash from the checkpoint commit above]
   ```

## PHASE 4: Apply Fix

### 4.1: Execute the Fix

Apply the minimal change that fixes the root cause.

**Rules**:
1. Make the smallest possible change that fixes the bug — nothing more
2. Follow the project's constitution (code quality, patterns, naming)
3. No refactoring of surrounding code
4. No feature additions
5. No "while I'm here" improvements
6. Early returns over deep nesting
7. No magic values — use named constants
8. No debug artifacts (console.log, debugger, etc.)
9. Handle both success and error paths

After applying the fix, commit:
```
git add [files you modified] .claude/wip.md && git commit -m "[WIP] Fix: [short description] — fix applied"
```

Update `.claude/wip.md` — change Phase to `5 (Verify)`.

## PHASE 5: Verify (with Self-Repair)

Run verification on all changed files:

1. **TypeScript compiles**: Run `tsc --noEmit` (or project equivalent from CLAUDE.md)
2. **Linter passes**: Run lint on all changed files
3. **Project builds** (if Build Command is specified in CLAUDE.md): Run the build command. For wrapper mode projects, run inside the Source Root directory. Skip this check if no Build Command is configured.
4. **Bug is actually fixed**: Verify the root cause identified in Phase 2 is addressed by the change
5. **No regressions**: Check that the fix doesn't break the obvious happy path
6. **Wrapper isolation check** (wrapper mode only): Verify no Claude artifacts were created inside the Source Root

**If ALL checks pass** → proceed to Phase 6.

**If any check fails** → enter the self-repair loop (max 3 attempts):

For each repair attempt:
1. Collect all error output (tsc errors, lint errors, build errors)
2. Apply a targeted fix for ONLY those errors
3. Commit:
   ```
   git add [files you modified] .claude/wip.md && git commit -m "[WIP] Fix: [short description] — repair attempt [M]/3"
   ```
4. Re-run ALL verification checks

**If verification passes after any attempt** → proceed to Phase 6.

**If all 3 repair attempts are exhausted** → STOP:
- Report the remaining errors to the user
- Keep the WIP marker and commits for inspection
- Suggest: "Run `/fix` again after manually addressing these errors, or use recovery options"

## PHASE 6: Code Review

Launch the **code-reviewer** agent on ALL changed files.

Provide the agent with:
1. The list of changed files (`git diff --name-only` against the checkpoint commit)
2. The bug description and root cause
3. The constitution
4. Relevant entries from `.claude/memory/MEMORY.md`

The agent will check: constitution compliance, architecture & patterns, type safety, security basics, code quality, and memory pitfalls.

**If the agent returns BLOCK or critical issues** (max 1 additional review cycle):
- Apply the required fixes
- Re-run verification (Phase 5 checks)
- Commit:
  ```
  git add [files you modified] .claude/wip.md && git commit -m "[WIP] Fix: [short description] — review fixes"
  ```
- If still BLOCKED after this additional cycle, STOP and report the remaining issues to the user. Do not attempt further review cycles.

**If the agent returns APPROVE or only warnings/info** → proceed to Phase 7.

## PHASE 7: Test Assessment

Launch the **qa-engineer** agent to assess test impact.

Provide the agent with:
1. The changed files and the nature of the fix
2. The existing test files related to the changed code (find them via Grep/Glob)
3. The bug description

The agent should:
1. **Check if existing tests need updating** — does the fix change behavior that existing tests assert?
2. **Assess if a regression test is warranted** — is this bug likely to recur? Was it caused by a gap in test coverage?
3. **If a test is warranted**: Write a minimal regression test that would catch this bug if it were reintroduced
4. **If no test is needed**: Explicitly state why (e.g., "existing tests already cover this path" or "this was a one-time configuration issue")

**Rules for test decisions:**
- Not every bug fix needs a new test — use judgment
- If a test is written, it must follow existing test patterns in the codebase
- Run the test suite on changed areas to confirm nothing is broken

If tests were added or modified, commit:
```
git add [test files you modified] && git commit -m "[WIP] Fix: [short description] — tests"
```

## PHASE 7.5: Documentation Update (Conditional)

If the fix changed any **public API signatures** (function parameters, return types, exported interfaces) or **user-facing behavior** (different output, new error messages, changed defaults):

1. Launch the **tech-writer** agent with:
   - The bug description and root cause from Phase 2.2
   - The list of changed files
   - The existing `docs/` folder structure (run Glob on `docs/`)
   - Instruction: "A bug fix changed these files. Check if any public API signatures or documented behavior changed. If so, update inline docs (JSDoc/docstrings) and the relevant `docs/` file. If the fix only restores previously-documented behavior, report 'No doc update needed.'"

2. If the tech-writer made changes, commit:
   ```
   git add docs/ [source files with doc changes] && git commit -m "[WIP] Fix: [short description] — doc update"
   ```

If the fix is purely internal (no public API or behavior change), skip this phase — but document the skip decision in Phase 8.3's report as: `**Documentation**: No public API changes — skipped`.

## PHASE 8: Report & Clean Up

### 8.1: Final Commit

Squash all `[WIP]` and `[checkpoint]` commits for this fix into a single clean commit.

First, verify WIP commits haven't been pushed to the remote:
```
git log --oneline origin/$(git branch --show-current)..HEAD 2>/dev/null
```
- If this shows commits (or fails because there's no upstream) → WIP commits are **local only** → safe to squash:
  ```
  git reset --soft [checkpoint-commit-hash]
  git commit -m "fix([area]): [concise description of what was fixed]"
  ```
- If this shows **no commits** (HEAD matches remote) → WIP commits were already pushed → **skip squashing** and keep commits as-is.

Follow the **Commit Convention** section in CLAUDE.md (format and attribution rules).

### 8.1.5: Update Bug File (if applicable)

If this fix was initiated from a bug file (detected in Phase 1.0):
1. Update the bug file's **Status** to "Fixed"
2. Fill in the **Fixed** date with today's date (YYYY-MM-DD)
3. Fill in the **Fix Notes** section with:
   - The root cause from Phase 2.2
   - A 1-2 sentence summary of what was changed
   - The commit reference from Phase 8.1

### 8.2: Delete WIP Marker

Delete `.claude/wip.md`.

### 8.3: Present Report

```
## Bug Fix Complete

**Bug**: [user's description]
**Root cause**: [what was wrong]
**Fix**: [what was changed, 1-2 sentences]

**Changes**:
- [file]: [what changed, 1 line]
- [file]: [what changed, 1 line]

**Verification**:
- TypeScript: PASS
- Linter: PASS
- Build: PASS [or SKIP if no build command configured]
- Code review: [APPROVE / issues addressed]

**Tests**: [Added regression test in [file] / Existing tests sufficient / No test needed — [reason]]

**Documentation**: [Updated docs/api/X.md / No public API changes — skipped]

**Commit**: `fix([area]): [description]`
```

## PHASE 9: Memory Update

If anything noteworthy happened during the fix, update `.claude/memory/MEMORY.md`:

- **Bug pattern**: If this bug represents a pattern that could recur (e.g., "null checks missing on API responses in the cart module"), record it under Known Pitfalls
- **What caused it**: If the root cause reveals a systemic issue (e.g., "type definitions don't enforce required fields"), note it
- **Fix approach**: If the diagnosis or fix involved a non-obvious technique, record it under What Worked

Use the format: `- **[AREA]**: [observation] _(Task N / Feature NNN)_`. Add entries under the matching section in MEMORY.md (Known Pitfalls, What Worked, What Failed, External API Quirks, etc.).

Keep entries concise (1-2 lines each). Only update if there's something genuinely useful for future work — not every bug fix needs a memory entry.

## IMPORTANT RULES

1. **Diagnose before fixing** — never apply a fix without understanding the root cause. Guessing wastes time and can introduce new bugs
2. **Minimal changes only** — fix the bug, nothing else. No refactoring, no improvements, no "while I'm here" changes
3. **Constitution is law** — all fixes must comply with constitution rules. Constitution violations are always critical
4. **Hard gate on diagnosis** — the user must confirm the diagnosis before any code is changed
5. **Self-repair before escalation** — when verification fails, attempt automatic repair (up to 3 times) before stopping
6. **Scope discipline** — if the fix grows beyond 5 files, stop and recommend `/specify`. Small bugs get `/fix`, big bugs get the full pipeline
7. **Crash safety** — always write `wip.md` before making changes and delete it only after the final commit
8. **Verify everything** — even if hooks ran, run explicit verification after the fix
9. **Test intentionally** — not every fix needs a test, but every fix needs a test *decision* with reasoning
10. **Memory is selective** — only record genuinely useful patterns and pitfalls, not routine fixes