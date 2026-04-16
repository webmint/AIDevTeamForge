# /review — Expert Code Review

Launches specialist review agents (security, performance, test assessment) on completed feature code. Produces a structured review report for `/verify` to incorporate into its verdict.

## Usage
```
/review [spec-file]
```

## Arguments
- `$ARGUMENTS` — Optional path to a spec file. If empty, use the most recently modified spec in `specs/`.

## PHASE 1: Load Context

**Source Root**: Read `CLAUDE.md` and note the Source Root (default: `.`). When reading task completion notes, changed files are listed relative to the repository root. In wrapper mode (`SOURCE_ROOT != "."`), source files live under the Source Root path — inform agents of this so they read files from the correct location.

1. Read the spec file (from `$ARGUMENTS` or most recent feature directory in `specs/`)
2. Read the feature's `plan.md` (for architecture decisions — needed by performance-analyst)
3. Read all task files in `specs/NNN-feature/tasks/` — extract:
   - Task titles and completion status
   - Completion Notes (files changed, deviations)
4. Read `constitution.md`
   - **Guard**: If `constitution.md` contains `_Run /constitute to populate_`, stop: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/review`."
5. Read `.claude/memory/MEMORY.md` (for known pitfalls, security patterns, and performance anti-patterns from prior work)
6. Collect the list of all changed files across all tasks (from task completion notes) and deduplicate

**Completeness warning**: Read `specs/[feature]/tasks/README.md`. If any task has Status other than `Complete`:
```
⚠️ Not all tasks are Complete. Review findings may change after remaining tasks are executed.
Proceeding with review of current state.
```

## PHASE 2: Security Review

If `.claude/agents/security-reviewer.md` exists, launch the **security-reviewer** agent on all files changed across the feature's tasks.

Read `.claude/agents/security-reviewer.md` and include its **full content** as the opening section of the agent prompt.

Provide the agent with:
1. The list of all changed files (from all task completion notes)
2. The feature spec (for context on what was built)
3. The constitution's security-related rules (if any)
4. Relevant entries from MEMORY.md (known security pitfalls, past incidents)

Instruct the agent: "If any finding involves a constitution rule violation, mark it Critical regardless of other severity factors."

Collect the agent's findings with severity levels (Critical, High, Medium, Info).

If the agent doesn't exist, skip this phase and note in the report: _Skipped — no security-reviewer agent configured._

## PHASE 3: Performance Review

If `.claude/agents/performance-analyst.md` exists, launch the **performance-analyst** agent on all files changed across the feature's tasks.

Provide the agent with:
1. The list of all changed files
2. The feature spec (especially any performance-related acceptance criteria)
3. The plan's architecture decisions (from `plan.md`, for context on expected data flow)
4. Relevant entries from MEMORY.md (known performance anti-patterns)

Collect the agent's findings with impact levels (High, Medium, Low).

If the agent doesn't exist, skip this phase silently.

## PHASE 4: Test Assessment

If `.claude/agents/qa-engineer.md` exists, launch the **qa-engineer** agent.

Provide the agent with:
1. The list of all changed files (from all task completion notes)
2. The spec's acceptance criteria (for AC-to-test traceability)
3. The feature's test files (if any were created or modified across tasks)

The agent assesses: test coverage gaps for changed code, untested AC items, missing edge case tests. It does NOT write tests — report only.

If the agent doesn't exist, skip this phase silently.

## PHASE 5: Write Review Report

Save the structured review report to `specs/[feature]/review.md`:

```markdown
# Review Report: [NNN-feature-name]

**Date**: [date]
**Spec**: [spec file path]
**Changed files**: [count]

## Security Review

- Critical: [N] | High: [N] | Medium: [N] | Info: [N]

[For each finding:]
- **[Severity]** — [file path]: [description]
  Recommendation: [suggested fix]

## Performance Review

[Include if performance-analyst ran, otherwise:]
_Skipped — no performance-analyst agent configured._

- High: [N] | Medium: [N] | Low: [N]

[For each finding:]
- **[High/Medium/Low]** — [file path]: [description]
  Recommendation: [suggested optimization]

## Test Assessment

[Include if qa-engineer ran, otherwise:]
_Skipped — no qa-engineer agent configured._

- AC items with test coverage: [N] of [M]
- Coverage gaps: [list uncovered areas]
- Verdict: ADEQUATE / GAPS FOUND

[For each gap:]
- [AC-N]: [description of missing coverage]
```

Commit the review report:
```
git add specs/[feature]/review.md && git diff --cached --quiet || git commit -m "[WIP] Review report: [feature-name]"
```

## PHASE 6: Present Summary

Display a concise summary of findings:

```
## Review Complete

**Security**: [N] Critical, [N] High, [N] Medium, [N] Info
**Performance**: [summary or "skipped"]
**Test Coverage**: [verdict or "skipped"]

Full report: specs/[feature]/review.md

Next: Run `/verify` to validate acceptance criteria and render verdict.
```

## IMPORTANT RULES

1. **Review does not render a verdict** — it produces findings with severity levels. The verdict is `/verify`'s job, which incorporates these findings
2. **Review does not fix code** — it identifies issues, not patches
3. **Idempotent** — running `/review` again overwrites `review.md` with fresh findings
4. **All agents run in parallel when possible** — launch security, performance, and test assessment agents concurrently to minimize execution time
5. **Constitution violations are always Critical** — never downgrade a constitution-related security finding
