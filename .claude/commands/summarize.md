# /summarize — Feature Summary Generator

Generates a concise, PR-ready summary of a completed feature. Reads spec, plan, tasks, and git history. Saves to `specs/[feature]/summary.md`. Run after `/verify` approves, before `/finalize`.

## Usage
```
/summarize [spec-file]
```

## Arguments
- `$ARGUMENTS` — Optional path to a spec file. If empty, use the most recently modified spec in `specs/` with status "Complete".

## PHASE 1: Load Context

1. Read the spec file (from `$ARGUMENTS` or most recent completed feature directory in `specs/`)
   - **Guard**: If the spec's status is not "Complete", stop: "⛔ Spec is not marked Complete. Run `/verify` first."
   - **Finalization check**: Check if WIP/checkpoint commits exist (`git log --oneline --grep="\[WIP\]\|\[checkpoint\]"`). If none exist and a clean `feat(*)` commit is present, warn: "⚠️ Feature appears already finalized (no WIP commits, clean feature commit found). Summary will be based on current state, not task-by-task history. For best results, run `/summarize` before `/finalize`."
2. Read the feature's `plan.md`
3. Read all task files in `specs/NNN-feature/tasks/` — extract:
   - Task titles and 1-line descriptions
   - Completion Notes (files changed, deviations, observations)
4. Read the task index `specs/NNN-feature/tasks/README.md`

## PHASE 2: Gather Change Data

1. Read `.claude/project-config.json` for `DEFAULT_BRANCH` and `SOURCE_ROOT`. If `DEFAULT_BRANCH` is missing, fall back to `main` silently.
2. Identify the feature branch: read the current branch name or detect the `spec/NNN-*` branch associated with this feature
3. Run `git diff --stat [DEFAULT_BRANCH]...HEAD` to get file change statistics
4. Run `git log --oneline [DEFAULT_BRANCH]...HEAD` to get commit history for this feature
5. **Wrapper mode** (if `SOURCE_ROOT` is not `.`): Also gather source repo changes:
   - `git -C $SOURCE_ROOT diff --stat` to get source code change statistics
   - `git -C $SOURCE_ROOT log --oneline -20` to get recent source commits
   - Include both wrapper (specs, docs) and source (code) changes in the summary
6. Collect all files changed across all tasks from task completion notes and deduplicate

## PHASE 3: Generate Summary

Produce the following structured summary. Each section should be concise — target 1-5 lines per section, not a wall of text.

```markdown
## Feature Summary: [NNN — feature name]

### What was built
[2-3 sentence high-level description synthesized from the spec overview and plan summary. Focus on what the user gets, not implementation details.]

### Changes
[Bullet list — one line per task, describing what it accomplished:]
- Task 1: [title] — [1-line what it did]
- Task 2: [title] — [1-line what it did]
...

### Files changed
[Group by directory/area, showing counts:]
- `src/components/` — N files modified
- `src/utils/` — N files added, M modified
- `tests/` — N files added
[Total: X files changed, Y insertions, Z deletions]

### Key decisions
[2-4 most important design decisions from plan.md's key decisions table. One line each:]
- [Decision area]: [what was decided and why]
...

### Deviations from plan
[Only include this section if any task noted deviations in its Completion Notes. Otherwise omit entirely.]
- Task [N]: [what deviated and why]
...

### Acceptance criteria
[Compact checklist — all should be PASS since verify approved:]
- [x] AC-1: [short description]
- [x] AC-2: [short description]
...
```

## PHASE 4: Save Summary

1. Write the summary to `specs/[feature]/summary.md`
2. Commit the summary file (follow the **Commit Convention** section in CLAUDE.md for attribution rules):
   ```
   git add specs/[feature]/summary.md && git commit -m "[WIP] Feature summary: NNN-feature-name"
   ```

## PHASE 5: Present

Display the full summary to the user, then:

```
Summary saved to specs/[feature]/summary.md
Copy-ready for PR description.

Next: Run `/finalize` to squash WIP commits and generate feature-level documentation.
```

## IMPORTANT RULES

1. **Concise over comprehensive** — this is a summary, not a report. Each section targets 1-5 lines. If a section would be empty (e.g., no deviations), omit it entirely
2. **User-facing language** — describe what was built in terms of behavior and outcomes, not implementation mechanics. "Added email validation to signup" not "Created validateEmail function in utils/validation.ts"
3. **Deduplicate** — if multiple tasks touched the same directory or area, group them in Files Changed rather than listing each file
4. **No speculation** — only include information that's present in the spec, plan, task files, or git history. Don't infer or guess
5. **Idempotent** — running `/summarize` again overwrites `summary.md` with a fresh summary