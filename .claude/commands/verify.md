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

## PHASE 3: Integration Check

Individual code quality was reviewed per-task during `/execute-task` Phase 3.3. This phase checks what only the epic-level view can see: cross-task integration and overall consistency.

### 3.1: Cross-Task Consistency

Read the key integration points between components built by different tasks:
- Shared types/interfaces: are they used consistently across all consumers?
- Import chains: do the pieces connect correctly?
- API contracts: do callers and providers agree on signatures and behavior?
- State flow: does data move correctly between layers built by different tasks?

Flag any inconsistencies as Critical issues.

### 3.2: Automated Checks

Run these on ALL changed files across all tasks:
- **Type checker**: Run the Type Check Command from CLAUDE.md and report result
- **Linter**: Run the Lint Command from CLAUDE.md on all changed files and report result
- **Build** (if Build Command is specified in CLAUDE.md): Run the build command and report result. For wrapper mode projects, run inside the Source Root directory. Skip if no Build Command is configured
- **Scope creep**: Compare changed files against the spec's scope boundaries — flag files outside scope
- **Leftover artifacts**: Check for debug logs, bare TODOs, commented-out code across all changed files

### 3.3: Feature Documentation

Launch the **tech-writer** agent to generate or update feature-level documentation in `docs/`.

Read `.claude/agents/tech-writer.md` and include its **full content** as the opening section of the agent prompt. If the file does not exist, proceed with the inline prompt alone.

Provide the agent with:
1. The feature spec (what was built and why)
2. All changed files across all tasks (from task completion notes)
3. Existing `docs/` content (output of Glob on `docs/`)
4. Instruction: "Write or update feature-level documentation for `docs/`. Inline code docs already exist in the source files — focus on how the feature works as a whole, architecture decisions, and usage examples. Use the document-when/skip-when criteria from your workflow."

If the tech-writer determines no feature-level docs are needed (internal refactoring, no public-facing changes), accept the justification and skip.

If documentation was created or updated, commit:
```
git add docs/ && git commit -m "[WIP] Feature docs: [feature-name]"
```

Integration check results feed into the verification report (Phase 6).

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
- Cross-task consistency: PASS/FAIL [details if fail]
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

- If APPROVED: "All acceptance criteria are met and integration checks pass." Then run Phase 9.5, then invoke `/summarize`.
- If NEEDS WORK: "Found [N] issues. Details in the verification report above." Then proceed to Phase 10.
- If REJECTED: "Critical issues found that require revisiting the spec. [Describe the fundamental problem]. To address: revise the spec with `/specify`, then re-run `/plan` and `/breakdown`. The current task breakdown should not be re-executed as-is."

## PHASE 9.5: Feature Squash

Skip if verdict is not APPROVED or no `[WIP]` commits exist.

Squash all `[WIP]` and `[checkpoint]` commits from this feature into a single clean commit.

1. Read `DEFAULT_BRANCH` from `.claude/project-config.json`. If missing, fall back to `main`.
2. Find the squash base:
   - **If on a feature branch** (not on DEFAULT_BRANCH): `git merge-base HEAD [DEFAULT_BRANCH]` — this is the commit where the feature branch diverged. No commit message parsing needed.
   - **If on DEFAULT_BRANCH** (no feature branch): fall back to finding the oldest `[checkpoint]` commit via `git log --oneline --grep="\[checkpoint\]" | tail -1`, then use its parent as the squash base.
3. Verify WIP commits haven't been pushed to the remote:
   ```
   git log --oneline origin/$(git branch --show-current)..HEAD 2>/dev/null
   ```
4. If commits are local only → safe to squash:
   ```
   git reset --soft [squash-base]
   git commit -m "feat([feature-name]): [spec title — 1-2 sentences from spec overview]"
   ```
   Follow the **Commit Convention** section in CLAUDE.md (format and attribution rules).
5. If commits were already pushed → skip squash, warn user

**Source repo squash** (wrapper mode only, `SOURCE_ROOT != "."`): Also run the Source Repo Squash procedure from the Source Repo Auto-Commit section above.

Then invoke `/summarize`:
```
✅ Verification passed — automatically running /summarize
```

## PHASE 10: Issue Report (if NEEDS WORK)

If the verdict is NEEDS WORK and the report contains Critical or Warning issues, present them to the user with actionable guidance. If the verdict is APPROVED or REJECTED, skip this phase entirely.

### 10.1: Present Issues

List each Critical and Warning issue from the verification report with a sequential number. For each issue, indicate the type and suggested action:

```
## Issues Found

### Code Issues
1. [Critical] [file path] — [issue description]
   → Run `/fix "[description]"` to address
2. [Warning] [file path] — [issue description]
   → Run `/fix "[description]"` to address

### Documentation Gaps
3. [Warning] [file path] — [public API lacking docs]
   → Run `/refresh-docs` to address documentation gaps

### Info (no action needed)
- [observation]
```

### 10.2: Failure-Count Guidance

Based on the number of Critical + Warning issues, add context-aware guidance:

**1-3 issues:**
```
[N] issues found. You can run `/fix` for each in the current session.
```

**4-6 issues:**
```
[N] issues found. Run `/fix` for each, but consider `/compact` after every 2-3 fixes to manage context.
```

**7+ issues:**
```
[N] issues found. This many failures may indicate deeper issues with the implementation.
Consider re-running `/execute-task` for the affected tasks rather than fixing individually.
```

### 10.3: Offer Batch Bug Filing

After presenting issues and guidance, offer to create bug files:

```
Create bug files for all [N] issues? Each file will contain the AC reference,
expected/actual behavior, and affected files — enough context for a fresh
`/fix` session.
  1. Yes — create bug files for all issues
  2. Select — create bug files for specific issues (provide numbers)
  3. No — I'll handle these manually
```

Wait for user response.

### 10.4: Create Bug Files (if requested)

**Determine next bug number**: Scan `bugs/` for existing `.md` files, find the highest NNN prefix, and assign numbers sequentially from there. Do this ONCE before creating any files.

For each issue being filed, create a bug file in `bugs/` following the format in `.claude/templates/storage-rules.md`:
1. Write `bugs/NNN-short-description.md`
2. Populate all fields:
   - **Status**: Open
   - **Source**: verify
   - **Severity**: from the verification report
   - **Feature**: path to the feature's spec.md
   - **AC**: the acceptance criterion that failed (e.g., AC-2), or N/A
   - **Expected Behavior**: what the AC says should happen (from the spec)
   - **Actual Behavior**: what verification observed (from the report evidence)
   - **File(s)**: affected files with area/function references (not line numbers)
   - **Evidence**: verification method and specific output
   - **Related Issues**: list of other bug files created in this batch

Present the created files:

```
Bug files created:
- bugs/NNN-xxx.md — [short title]
- bugs/NNN-yyy.md — [short title]
- bugs/NNN-zzz.md — [short title]

To fix: run `/fix bugs/NNN-xxx.md` for each issue.
After fixes, run `/verify` to confirm.
```

## IMPORTANT RULES

1. **Verify against spec, not assumptions** — the spec is the contract. If the code does something useful but the spec didn't ask for it, that's scope creep
2. **Be specific about failures** — "AC-2 fails because `orderState.soldToParty` is null when ShippingTypeEnum is SoldTo, but it should return the party data" not "AC-2 fails"
3. **Verification does not fix code** — /verify does not modify source code or invoke /fix. It verifies, documents (feature-level docs via tech-writer in Phase 3.3), and reports findings. The user decides next steps
4. **Memory updates are mandatory** — even if everything passed, record what you learned
5. **Constitution violations are always critical** — never downgrade a constitution violation to "warning"