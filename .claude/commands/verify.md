# /verify — Post-Task Verification

Verifies completed tasks against the original specification's acceptance criteria, performs integration checks, and renders a verdict. Incorporates findings from `/review` if available.

## Usage
```
/verify [spec-file]
```

## Arguments
- `$ARGUMENTS` — Optional path to a spec file. If empty, use the most recently modified spec in `specs/`.

## PHASE 1: Load Context

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, run type-checking and linting commands inside that directory.

1. Read the spec file (from `$ARGUMENTS` or most recent feature directory in `specs/`)
2. Read the feature's `plan.md`
3. Read all task files in `specs/NNN-feature/tasks/`
4. Read `constitution.md`
   - **Guard**: If `constitution.md` contains `_Run /constitute to populate_`, stop: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/verify`."
5. Read `.claude/memory/MEMORY.md`

## PHASE 2: Read Review Report

Check if `specs/[feature]/review.md` exists.

- **If found**: read the review report and extract:
  1. **Security findings**: any finding with severity Critical or High → add as a Critical issue in Phase 5's "Issues Found" section. Medium/Info findings → add as Warning/Info respectively.
  2. **Performance findings**: include in the report's "Review Findings" section. High-impact bottlenecks that violate spec criteria → add as Warning issues.
  3. **Test assessment**: include verdict (ADEQUATE/GAPS FOUND) in the report. If GAPS FOUND, add coverage gaps as Warning issues.
- **If not found**: warn and proceed:
  ```
  ⚠️ No review report found. Run `/review` first for a complete verdict.
  Proceeding with AC and integration checks only.
  ```

## PHASE 3: Acceptance Criteria Check

### 3.0: Determine Verification Mode

Read `AC_VERIFICATION` from `.claude/project-config.json`.

- If `"off"`, missing, or file doesn't exist → use **code-reading mode** (skip to 3.3-fallback below)
- If `"auto"`, `"browser-only"`, or `"api-only"` → proceed to 3.1

### 3.1: MCP Availability Check

**Only for `auto` and `browser-only` modes:**

Attempt to call `mcp__chrome-devtools__list_pages` as a lightweight probe.

- **If succeeds** → `CHROME_MCP_AVAILABLE = true`
- **If fails** (MCP server not running, connection refused, error):
  - `CHROME_MCP_AVAILABLE = false`
  - If mode is `"browser-only"`: warn — "Chrome DevTools MCP is not available. AC verification is set to browser-only but the debugger is not running. Falling back to code reading. Start the WebStorm JS debugger and re-run `/verify` for browser-based verification."
  - If mode is `"auto"`: note — "Chrome MCP not available. Frontend AC items will be verified by code reading."

### 3.2: Launch ac-verifier Agent

Check if `.claude/agents/ac-verifier.md` exists. If not, fall back to code-reading mode (3.3-fallback).

If it exists, launch the **ac-verifier** agent with:
1. The full acceptance criteria section from the spec
2. `CHROME_MCP_AVAILABLE` status (`true`/`false`)
3. `AC_VERIFICATION_URL` from `.claude/project-config.json`
4. `AC_VERIFICATION_API_BASE` from `.claude/project-config.json`
5. `AC_VERIFICATION` mode (`auto`/`browser-only`/`api-only`)
6. The list of changed files across all tasks (for code-reading fallback on items that cannot be browser/API verified)
7. Instruction: "Verify each AC item. For items you cannot verify via browser/API, fall back to reading the changed files listed below."

### 3.3: Merge Results

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

### 3.3-fallback: Code-Reading Mode

If AC verification is off, the agent doesn't exist, or MCP probe failed in browser-only mode — use the original code-reading approach:

For EACH acceptance criterion (AC-N) in the spec:
1. **Identify the task(s)** that addressed this criterion
2. **Read the changed files** and verify the criterion is actually satisfied
3. **Mark status**: PASS / FAIL / PARTIAL

Generate the same checklist table (without the Category column).

### 3.4: Handle Failures

If ANY criterion is FAIL or PARTIAL:
- Identify what's missing
- Suggest which task needs to be re-executed or a new task to address the gap
- Do NOT attempt to fix it in this command — that's what `/execute-task` is for

## PHASE 4: Integration Check

Individual code quality was reviewed per-task during `/execute-task` Phase 3.3. This phase checks what only the epic-level view can see: cross-task integration and overall consistency.

### 4.1: Cross-Task Consistency

Read the key integration points between components built by different tasks:
- Shared types/interfaces: are they used consistently across all consumers?
- Import chains: do the pieces connect correctly?
- API contracts: do callers and providers agree on signatures and behavior?
- State flow: does data move correctly between layers built by different tasks?

Flag any inconsistencies as Critical issues.

### 4.2: Automated Checks

Run these on ALL changed files across all tasks:
- **Type checker**: Run the Type Check Command from CLAUDE.md and report result
- **Linter**: Run the Lint Command from CLAUDE.md on all changed files and report result
- **Build** (if Build Command is specified in CLAUDE.md): Run the build command and report result. For wrapper mode projects, run inside the Source Root directory. Skip if no Build Command is configured
- **Scope creep**: Compare changed files against the spec's scope boundaries — flag files outside scope
- **Leftover artifacts**: Check for debug logs, bare TODOs, commented-out code across all changed files

## PHASE 5: Generate Verification Report

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

### Review Findings
[Include if review.md was found, otherwise: "No review report available — run `/review` for security, performance, and test coverage analysis."]

**Security**: Critical: [N] | High: [N] | Medium: [N] | Info: [N]
**Performance**: High: [N] | Medium: [N] | Low: [N] [or "not reviewed" / "skipped"]
**Test Coverage**: [ADEQUATE / GAPS FOUND / "not reviewed" / "skipped"]

[List Critical/High findings that affect the verdict]

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
[If APPROVED: ready for summarize and finalize]
```

## PHASE 6: Update Spec Status

If all acceptance criteria pass and code quality checks pass:
1. **Task completion cross-check**: Before marking spec Complete, verify all task files in `specs/NNN-feature/tasks/` (excluding README.md) have `Status: Complete`. If any task is not Complete, keep spec as "In Progress" and report: "Spec cannot be marked Complete — Task [N] is still [status]."
2. Update the spec file status to "Complete"
   - In the spec's **Acceptance Criteria** section, change `- [ ]` to `- [x]` for every AC that passed verification
3. Update the task index README.md with a completion summary

If issues found:
1. Keep spec status as "In Progress"
2. Add issues to the relevant task files
3. Suggest next steps

## PHASE 7: Memory Update

Update `.claude/memory/MEMORY.md` with lessons learned from this feature:

- **What went well**: Patterns that worked, good decisions in the spec
- **What went wrong**: Issues discovered during verification, things that should have been caught earlier
- **New patterns**: Any new code patterns introduced that should be followed in future work
- **Pitfalls**: Gotchas discovered that should be avoided in similar work

Use the format: `- **[AREA]**: [observation] _(Task N / Feature NNN)_`. Add entries under the matching section in MEMORY.md (Known Pitfalls, What Worked, What Failed, External API Quirks, etc.).

Keep memory entries concise (1-2 lines each). Link to specific files if relevant.

## PHASE 8: Present Results

Show the user the verification report and recommend next action:

- If APPROVED: "All acceptance criteria are met and integration checks pass. Next: ensure `/summarize` has been run for the feature summary, then run `/finalize` to squash and generate docs."
- If NEEDS WORK: "Found [N] issues. Details in the verification report above." Then proceed to Phase 9.
- If REJECTED: "Critical issues found that require revisiting the spec. [Describe the fundamental problem]. To address: revise the spec with `/specify`, then re-run `/plan` and `/breakdown`. The current task breakdown should not be re-executed as-is."

## PHASE 9: Issue Report (if NEEDS WORK)

If the verdict is NEEDS WORK and the report contains Critical or Warning issues, present them to the user with actionable guidance. If the verdict is APPROVED or REJECTED, skip this phase entirely.

### 9.1: Present Issues

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

### 9.2: Failure-Count Guidance

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

### 9.3: Offer Batch Bug Filing

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

### 9.4: Create Bug Files (if requested)

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
3. **Verification does not fix code** — /verify does not modify source code or invoke /fix. It verifies, reports findings, and renders a verdict. The user decides next steps. Docs and squashing are handled by `/finalize`
4. **Memory updates are mandatory** — even if everything passed, record what you learned
5. **Constitution violations are always critical** — never downgrade a constitution violation to "warning"
6. **Review findings inform the verdict** — if a review report exists, Critical/High security findings become Critical issues in the verdict. Missing review report does not block verification but weakens the verdict. For production-ready features, always run `/review` before `/verify` to catch security and performance issues
