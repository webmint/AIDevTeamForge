# /verify — Post-Task Verification

Verifies completed tasks against the original specification's acceptance criteria, performs code review, and updates persistent memory.

## Usage
```
/verify [spec-file]
```

## Arguments
- `$ARGUMENTS` — Optional path to a spec file. If empty, use the most recently modified spec in `specs/`.

## Source Repo Auto-Commit (Wrapper Mode)

Skip this section entirely when `SOURCE_ROOT` is `.` (standalone mode).

**Squash** (at Phase 9.5): Propose a commit message and ask user to confirm before committing:
1. Extract ticket ID from source branch name — first match of `[A-Z]{2,}-[0-9]+`
2. Generate description from spec overview (`## 1. Overview`, first 1-2 sentences)
3. Present to user: `Proposed source commit: [AAA-123] - Description. Confirm or edit:`
4. On confirmation: `git -C $SOURCE_ROOT reset --soft [squash-base] && git -C $SOURCE_ROOT commit -m "<confirmed message>"`
5. If WIP commits were already pushed to remote, skip squash and warn user

No `Co-Authored-By`. No AI traces. No conventional commit prefixes.

## PHASE 1: Load Context

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, run type-checking and linting commands inside that directory.

**Source repo tracking** (wrapper mode only, `SOURCE_ROOT != "."`):
- Record the source repo's current branch: `git -C $SOURCE_ROOT branch --show-current`
- Find the source squash base: look for `[WIP]` commits in the source repo (`git -C $SOURCE_ROOT log --oneline --grep="\[WIP\]"`). The squash base is the parent of the oldest `[WIP]` commit. If no `[WIP]` commits exist, there are no source changes to squash.

1. Read the spec file (from `$ARGUMENTS` or most recent feature directory in `specs/`)
2. Read the feature's `plan.md`
3. Read all task files in `specs/NNN-feature/tasks/`
4. Read `constitution.md`
   - **Guard**: If `constitution.md` contains `_Run /constitute to populate_`, stop: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/verify`."
5. Read `.claude/memory/MEMORY.md`

## PHASE 2: Acceptance Criteria Check

### 2.0: Determine Verification Mode

Read `AC_VERIFICATION` from `.claude/project-config.json`.

- If `"off"`, missing, or file doesn't exist → use **code-reading mode** (skip to 2.3-fallback below)
- If `"auto"`, `"browser-only"`, or `"api-only"` → proceed to 2.1

### 2.1: MCP Availability Check

**Only for `auto` and `browser-only` modes:**

Attempt to call `mcp__chrome-devtools__list_pages` as a lightweight probe.

- **If succeeds** → `CHROME_MCP_AVAILABLE = true`
- **If fails** (MCP server not running, connection refused, error):
  - `CHROME_MCP_AVAILABLE = false`
  - If mode is `"browser-only"`: warn — "Chrome DevTools MCP is not available. AC verification is set to browser-only but the debugger is not running. Falling back to code reading. Start the WebStorm JS debugger and re-run `/verify` for browser-based verification."
  - If mode is `"auto"`: note — "Chrome MCP not available. Frontend AC items will be verified by code reading."

### 2.2: Launch ac-verifier Agent

Check if `.claude/agents/ac-verifier.md` exists. If not, fall back to code-reading mode (2.3-fallback).

If it exists, launch the **ac-verifier** agent with:
1. The full acceptance criteria section from the spec
2. `CHROME_MCP_AVAILABLE` status (`true`/`false`)
3. `AC_VERIFICATION_URL` from `.claude/project-config.json`
4. `AC_VERIFICATION_API_BASE` from `.claude/project-config.json`
5. `AC_VERIFICATION` mode (`auto`/`browser-only`/`api-only`)
6. The list of changed files across all tasks (for code-reading fallback on items that cannot be browser/API verified)
7. Instruction: "Verify each AC item. For items you cannot verify via browser/API, fall back to reading the changed files listed below."

### 2.3: Merge Results

Use the agent's structured report to populate the AC verification checklist:

```markdown
## Acceptance Criteria Verification

| AC | Description | Task(s) | Category | Status | Evidence |
|----|-------------|---------|----------|--------|----------|
| AC-1 | [description] | Task [N] | frontend | PASS | [snapshot/screenshot/explanation] |
| AC-2 | [description] | Task [N] | backend | FAIL | [expected vs actual] |
| AC-3 | [description] | Task [N] | manual | MANUAL | [reason cannot automate] |
...
```

For MANUAL and SKIPPED items, append a note explaining why automated verification was not possible.

### 2.3-fallback: Code-Reading Mode

If AC verification is off, the agent doesn't exist, or MCP probe failed in browser-only mode — use the original code-reading approach:

For EACH acceptance criterion (AC-N) in the spec:
1. **Identify the task(s)** that addressed this criterion
2. **Read the changed files** and verify the criterion is actually satisfied
3. **Mark status**: PASS / FAIL / PARTIAL

Generate the same checklist table (without the Category column).

### 2.4: Handle Failures

If ANY criterion is FAIL or PARTIAL:
- Identify what's missing
- Suggest which task needs to be re-executed or a new task to address the gap
- Do NOT attempt to fix it in this command — that's what `/execute-task` is for

## PHASE 3: Code Review (code-reviewer agent)

Launch the **code-reviewer** agent on ALL files changed across all tasks in the breakdown.

Provide the agent with:
1. The list of all changed files (from all task completion notes)
2. The feature spec (acceptance criteria and scope boundaries)
3. The constitution
4. Relevant entries from `.claude/memory/MEMORY.md`

The agent will check: constitution compliance, architecture & patterns, type safety, security basics, code quality, and memory pitfalls.

**Additionally**, run these automated checks and append results to the agent's findings:
- **Type checker**: Run the Type Check Command from CLAUDE.md and report result
- **Linter**: Run the Lint Command from CLAUDE.md on all changed files and report result
- **Build** (if Build Command is specified in CLAUDE.md): Run the build command and report result. For wrapper mode projects, run inside the Source Root directory. Skip if no Build Command is configured
- **Scope creep**: Compare changed files against the spec's scope boundaries — flag files outside scope
- **Documentation**: Check if any task introduced new public APIs or behavior changes that lack docs in `docs/` or inline JSDoc. Flag as Warning. For each documentation gap found, record the specific file path and public API name — this is needed for direct remediation in Phase 10

The code-reviewer's verdict (APPROVE / REQUEST CHANGES / BLOCK) feeds into the final verification report.

## PHASE 4: Security Review (if security-reviewer agent exists)

If `.claude/agents/security-reviewer.md` exists, launch the **security-reviewer** agent on all files changed across the feature's tasks.

Provide the agent with:
1. The list of all changed files (from all task completion notes)
2. The feature spec (for context on what was built)
3. The constitution's security-related rules (if any)

Append the agent's findings to the verification report under a **Security Review** section. Any Critical or High findings become Critical issues in the report.

If the agent doesn't exist (wasn't generated by the wizard), skip this phase silently.

## PHASE 5: Performance Review (if performance-analyst agent exists)

If `.claude/agents/performance-analyst.md` exists, launch the **performance-analyst** agent on all files changed across the feature's tasks.

Provide the agent with:
1. The list of all changed files
2. The feature spec (especially any performance-related acceptance criteria)
3. The plan's architecture decisions (for context on expected data flow)

Append the agent's findings to the verification report under a **Performance Review** section. Any High-impact bottlenecks that violate spec criteria become Critical issues.

If the agent doesn't exist, skip this phase silently.

## PHASE 6: Generate Verification Report

```markdown
## Verification Report

**Feature**: [NNN-feature-name]
**Spec**: [spec file path]
**Tasks**: [task directory path]
**Date**: [date/time]

### Acceptance Criteria
| AC | Status |
|----|--------|
| AC-1 | PASS/FAIL |
| AC-2 | PASS/FAIL |
...

**Result**: [ALL PASS / X of Y PASS]

### Code Quality
- Type checker: PASS/FAIL
- Linter: PASS/FAIL
- Build: PASS/FAIL/SKIP
- Constitution compliance: PASS/FAIL [details if fail]
- No scope creep: PASS/FAIL [details if fail]
- No leftover artifacts: PASS/FAIL [details if fail]

### Security Review
[Include if security-reviewer ran, otherwise omit section]
- Critical: N | High: N | Medium: N | Info: N
- [findings list]

### Performance Review
[Include if performance-analyst ran, otherwise omit section]
- [bottlenecks and recommendations]

### Issues Found
[List any issues, categorized by severity]

#### Critical (must fix before merge)
- [issue description, file, suggested fix]

#### Warning (should fix, not blocking)
- [issue description, file, suggested fix]

#### Info (nice to have)
- [observation]

### Overall Verdict
[APPROVED / NEEDS WORK / REJECTED]

[If NEEDS WORK: specific tasks that need re-execution or new tasks needed]
[If APPROVED: ready for commit/PR]
```

## PHASE 7: Update Spec Status

If all acceptance criteria pass and code quality checks pass:
1. **Task completion cross-check**: Before marking spec Complete, verify all task files in `specs/NNN-feature/tasks/` (excluding README.md) have `Status: Complete`. If any task is not Complete, keep spec as "In Progress" and report: "Spec cannot be marked Complete — Task [N] is still [status]."
2. Update the spec file status to "Complete"
   - In the spec's **Acceptance Criteria** section, change `- [ ]` to `- [x]` for every AC that passed verification
3. Update the task index README.md with a completion summary

If issues found:
1. Keep spec status as "In Progress"
2. Add issues to the relevant task files
3. Suggest next steps

## PHASE 8: Memory Update

Update `.claude/memory/MEMORY.md` with lessons learned from this feature:

- **What went well**: Patterns that worked, good decisions in the spec
- **What went wrong**: Issues discovered during verification, things that should have been caught earlier
- **New patterns**: Any new code patterns introduced that should be followed in future work
- **Pitfalls**: Gotchas discovered that should be avoided in similar work

Use the format: `- **[AREA]**: [observation] _(Task N / Feature NNN)_`. Add entries under the matching section in MEMORY.md (Known Pitfalls, What Worked, What Failed, External API Quirks, etc.).

Keep memory entries concise (1-2 lines each). Link to specific files if relevant.

## PHASE 9: Present Results

Show the user the verification report and recommend next action:

- If APPROVED: "All acceptance criteria are met and code quality checks pass." Then run Phase 9.5 (if applicable), then invoke `/summarize`.
- If NEEDS WORK: "Found [N] issues. Recommend re-running `/execute-task [X]` for [reason]. Details in the verification report above."
- If REJECTED: "Critical issues found that require revisiting the spec. [Describe the fundamental problem]."

## PHASE 9.5: Source Repo Squash (wrapper mode only)

Skip if `SOURCE_ROOT` is `.`, verdict is not APPROVED, or no `[WIP]` commits exist in source repo.

Run the **Squash** procedure from the Source Repo Auto-Commit section above. Generate the description from the spec's `## 1. Overview` section (first 1-2 sentences).

Then invoke `/summarize`:
```
✅ Verification passed — automatically running /summarize
```

## PHASE 10: Issue Triage (if NEEDS WORK)

If the verdict is NEEDS WORK and the report contains Critical or Warning issues, offer the user a triage for each issue. If the verdict is APPROVED or REJECTED, skip this phase entirely.

### 10.1: Number and Present Issues

List each Critical and Warning issue from the verification report with a sequential number:

```
Issues to triage:

1. [Critical] [file path] — [issue description]
2. [Warning] [file path] — [issue description]
3. [Warning] [file path] — [issue description]
...
```

Info-level issues are shown for awareness but not included in triage (they are observations, not actionable bugs).

### 10.2: Per-Issue Triage

If there are **5 or fewer** issues, ask the user for each one individually:

```
Issue #N: [severity] [short description]
  1. Fix now — invoke /fix with this issue
  2. Fix docs now — invoke tech-writer agent directly (for documentation-only issues)
  3. Report for later — save to bugs/ for future fixing
  4. Skip — ignore this issue
```

If there are **more than 5** issues, first offer a batch option:

```
[N] issues found. How would you like to triage?
  1. Triage individually — decide per-issue
  2. Report all for later — save all to bugs/
  3. Pick specific issues to fix now — provide issue numbers, report the rest
```

Wait for user response before proceeding.

### 10.3: Execute Triage Decisions

**Determine next bug number**: Scan `bugs/` for existing `.md` files, find the highest NNN prefix, and assign numbers sequentially from there. Do this ONCE before creating any files (do not re-scan between each file creation).

**"Report for later" items**: For each, create a bug file in `bugs/`:
1. Write `bugs/NNN-short-description.md` using the standard bug file format
2. Set **Status** to "Open", **Source** to "verify", **Severity** from the verification report
3. Copy the relevant evidence from the verification report into the **Evidence** section
4. Populate **File(s)** from the issue's file path

**"Fix now" items**: For each, also create a bug file first (so there's a tracking record):
1. Write the bug file with **Status** set to "In Progress"
2. Invoke `/fix bugs/NNN-short-description.md` for the **first** "fix now" item only
3. If there are additional "fix now" items beyond the first, inform the user:
   "Starting with issue #N. After this fix completes, address remaining issues by running `/fix bugs/NNN-xxx.md` for each, or re-run `/verify` to re-assess."

**"Fix docs now" items** (documentation gaps only): For each, invoke the tech-writer agent directly — do NOT route through `/fix`:
1. Read `.claude/agents/tech-writer.md` and include its **full content** as the opening section of the agent prompt. If the file does not exist, proceed with the inline prompt alone.
2. Launch the **tech-writer** agent with:
   - Part 1 (if agent file exists): The full content of `.claude/agents/tech-writer.md`
   - Part 2: The list of files and public APIs flagged as lacking documentation, the feature spec for context, and instruction: "These public APIs were flagged during verification as lacking documentation. Add inline docs (JSDoc/docstrings) to each, and create or update the relevant `docs/` file."
3. After the tech-writer completes, verify the flagged APIs now have inline docs
4. Commit the doc changes (follow the **Commit Convention** section in CLAUDE.md for attribution rules):
   ```
   git add docs/ [source files with doc changes] && git commit -m "docs: add missing documentation flagged by /verify"
   ```
5. Process the next "Fix docs now" item (unlike "Fix now", multiple doc fixes can run sequentially since they are lightweight)

**"Skip" items**: No action taken.

### 10.4: Summary

Present a summary of triage decisions:

```
Triage complete:
- Fix now: [count] (starting with: bugs/NNN-xxx.md)
- Fix docs now: [count] (completed)
- Reported for later: [count]
  - bugs/NNN-xxx.md
  - bugs/NNN-xxx.md
- Skipped: [count]
```

If "fix now" items exist, proceed to invoke `/fix` for the first one. If only "fix docs now" items exist (no "fix now"), report documentation fixes complete.

## IMPORTANT RULES

1. **Verify against spec, not assumptions** — the spec is the contract. If the code does something useful but the spec didn't ask for it, that's scope creep
2. **Be specific about failures** — "AC-2 fails because `orderState.soldToParty` is null when ShippingTypeEnum is SoldTo, but it should return the party data" not "AC-2 fails"
3. **Don't fix during verification** — Phases 1-9 are read-only. Phase 10 may invoke `/fix` based on user triage decisions, but verification itself does not apply fixes
4. **Memory updates are mandatory** — even if everything passed, record what you learned
5. **Constitution violations are always critical** — never downgrade a constitution violation to "warning"