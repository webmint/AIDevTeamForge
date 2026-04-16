# /finalize — Feature Finalization

Generates feature documentation and squashes all WIP commits into a single clean commit. This is the last step before creating a PR.

## Usage
```
/finalize [spec-file]
```

## Arguments
- `$ARGUMENTS` — Optional path to a spec file. If empty, use the most recently modified spec in `specs/` with status "Complete".

## Source Repo Auto-Commit (Wrapper Mode)

Skip this section entirely when `SOURCE_ROOT` is `.` (standalone mode).

**Squash** (at Phase 3): Propose a commit message and ask user to confirm before committing:
1. Extract ticket ID from source branch name — first match of `[A-Z]{2,}-[0-9]+`
2. Generate description from spec overview (`## 1. Overview`, first 1-2 sentences)
3. Present to user: `Proposed source commit: [AAA-123] - Description. Confirm or edit:`
4. On confirmation: `git -C $SOURCE_ROOT reset --soft [squash-base] && git -C $SOURCE_ROOT commit -m "<confirmed message>"`
5. If WIP commits were already pushed to remote, skip squash and warn user

No `Co-Authored-By`. No AI traces. No conventional commit prefixes.

## PHASE 1: Gate Check

1. Read the spec file (from `$ARGUMENTS` or most recent completed feature directory in `specs/`)
   - **Guard**: If the spec's status is not "Complete", stop: "⛔ Spec is not marked Complete. Run `/verify` first."
2. Read the feature's `plan.md` (architecture context for tech-writer)
3. Read all task files in `specs/NNN-feature/tasks/` — extract Completion Notes (files changed) to build the changed files list for tech-writer
   - **Task cross-check**: Verify all task files (excluding README.md) have `Status: Complete`. If any task is not Complete, stop: "⛔ Not all tasks are complete. Task [N] is [status]. Run `/execute-task` to complete it first."
4. Read `.claude/project-config.json` for `DEFAULT_BRANCH` and `SOURCE_ROOT`. If `DEFAULT_BRANCH` is missing, fall back to `main`.

**Source Root**: If `SOURCE_ROOT` from project-config.json is not `.`, this is a wrapper project — run squash-related commands inside that directory.

**Source repo tracking** (wrapper mode only, `SOURCE_ROOT != "."`):
- Record the source repo's current branch: `git -C $SOURCE_ROOT branch --show-current`
- Find the source squash base: look for `[WIP]` commits in the source repo (`git -C $SOURCE_ROOT log --oneline --grep="\[WIP\]"`). The squash base is the parent of the oldest `[WIP]` commit. If no `[WIP]` commits exist, there are no source changes to squash.

3. Check for WIP/checkpoint commits:
   ```
   git log --oneline --grep="\[WIP\]\|\[checkpoint\]" [DEFAULT_BRANCH]..HEAD
   ```
   If no WIP or checkpoint commits found: "Nothing to finalize — no WIP commits found. Feature may have already been finalized."

4. **Summary warning**: Check if `specs/[feature]/summary.md` exists.
   If missing:
   ```
   ⚠️ No summary.md found. Run `/summarize` first for a complete feature record.
   Proceeding without summary.
   ```

## PHASE 2: Feature Documentation

Launch the **tech-writer** agent to generate or update feature-level documentation in `docs/`.

Read `.claude/agents/tech-writer.md` and include its **full content** as the opening section of the agent prompt. If the file does not exist, proceed with the inline prompt alone.

Provide the agent with:
1. The feature spec (what was built and why)
2. The feature's `plan.md` (architecture decisions and data flow)
3. All changed files across all tasks (from task completion notes gathered in Phase 1)
4. Existing `docs/` content (output of Glob on `docs/`)
5. Instruction: "Write or update feature-level documentation for `docs/`. Inline code docs already exist in the source files — focus on how the feature works as a whole, architecture decisions, and usage examples. Use the document-when/skip-when criteria from your workflow."

If the tech-writer determines no feature-level docs are needed (internal refactoring, no public-facing changes), accept the justification and skip.

If the tech-writer agent fails (error, timeout, context limit):
```
⚠️ Tech-writer failed: [error]. Feature docs may be incomplete.
Proceeding with squash — you may need to manually write/update docs after PR creation.
```

If documentation was created or updated, commit:
```
git add docs/ && git commit -m "[WIP] Feature docs: [feature-name]"
```

## PHASE 3: Feature Squash

Squash all `[WIP]` and `[checkpoint]` commits from this feature into a single clean commit.

1. Use `DEFAULT_BRANCH` from Phase 1 (already loaded from project-config.json).
2. Find the squash base:
   - **If on a feature branch** (not on DEFAULT_BRANCH): `git merge-base HEAD [DEFAULT_BRANCH]` — this is the commit where the feature branch diverged. No commit message parsing needed.
   - **If on DEFAULT_BRANCH** (no feature branch): fall back to finding the oldest `[checkpoint]` commit via `git log --oneline --grep="\[checkpoint\]" | tail -1`, then use its parent as the squash base.
3. Verify WIP commits haven't been pushed to the remote:
   ```
   git log --oneline origin/$(git branch --show-current)..HEAD 2>/dev/null
   ```
4. If commits are local only — safe to squash:
   ```
   git reset --soft [squash-base]
   git commit -m "feat([feature-name]): [spec title — 1-2 sentences from spec overview]"
   ```
   Follow the **Commit Convention** section in CLAUDE.md (format and attribution rules).
5. If commits were already pushed — skip squash, warn user:
   ```
   ⚠️ WIP commits have already been pushed to remote. Squash skipped to avoid
   rewriting shared history. Consider using an interactive rebase before creating a PR.
   ```

**Source repo squash** (wrapper mode only, `SOURCE_ROOT != "."`): Also run the Source Repo Squash procedure from the Source Repo Auto-Commit section above.

## PHASE 4: Present Results

```
## Feature Finalized

**Commit**: [short hash] [commit message]
**Files**: [N] files changed, [insertions] insertions, [deletions] deletions
**Docs**: [updated / skipped — reason]
**Summary**: [included in squash / not found]

Feature is ready for PR.
```

## IMPORTANT RULES

1. **Finalize does not verify code** — it assumes `/verify` has already approved. The gate check (spec Complete) enforces this
2. **Squash is the last operation** — docs are generated and committed as `[WIP]` before squash so they're included in the clean commit
3. **Idempotent safety** — if no WIP commits exist, finalize no-ops gracefully instead of failing
4. **No auto-invoke** — finalize does not automatically run any other command. The user decides what's next
5. **Wrapper mode squash** — both the wrapper repo and the source repo are squashed. Source repo follows the ticket-ID format from the branch name
