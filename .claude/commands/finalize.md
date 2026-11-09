# /finalize — Feature Finalization

Generates feature documentation and squashes all WIP commits into a single clean commit. This is the last step before creating a PR.

## Usage
```
/finalize [spec-file]
```

## Arguments
- `$ARGUMENTS` — Optional path to a spec file or its feature directory in `specs/`. If empty, use the most recently modified spec in `specs/` with status "Complete".

## Source Repo Auto-Commit (Wrapper Mode)

Skip this section entirely when `SOURCE_ROOT` is `.` (standalone mode).

**Squash** (at Phase 3): Propose a commit message and ask user to confirm before committing:
1. Extract ticket ID from source branch name — first match of `[A-Z]{2,}-[0-9]+`
2. Generate description from spec overview (`## 1. Overview`, first 1-2 sentences)
3. Present to user: `Proposed source commit: [AAA-123] - Description. Confirm or edit:`
   **Autonomous mode** (`_autonomous-mode.md`, point `commit`): use the proposed message.
4. On confirmation: `git -C $SOURCE_ROOT reset --soft [squash-base] && git -C $SOURCE_ROOT commit -m "<confirmed message>"`
5. If WIP commits were already pushed to remote, skip squash and warn user

No `Co-Authored-By`. No AI traces. No conventional commit prefixes.

## PHASE 1: Gate Check

1. Read the spec file (from `$ARGUMENTS` or most recent completed feature directory in `specs/`)
   - **Guard**: If the spec's status is not "Complete", stop: "⛔ Spec is not marked Complete. Run `/verify` first."
2. Read the feature's `plan.md` (architecture context for tech-writer)
3. Read all task files in `specs/NNN-feature/tasks/` — extract Completion Notes (files changed) to build the changed files list for tech-writer
   - **Task cross-check**: Verify all task files (excluding README.md) have `Status: Complete`. If any task is not Complete, stop: "⛔ Not all tasks are complete. Task [N] is [status]. Run `/execute-task` to complete it first."
   - **Evidence check**: when `.claude/quality-profile.json` sets `integrationRef`, run `python3 scripts/forge/check-task-evidence.py`: a Complete task without filled Completion Notes or a task commit stops finalize with the script's lines. When the binding sets `decisionRecords` (the project keeps one decision file per unit of work), also run `python3 scripts/forge/check-decision-records.py` and stop on its problems.
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
   **Exception**: when `.claude/quality-profile.json` sets `auditGate`, stop instead: "⛔ No summary.md found. The audit gate counts finished features by their `summary.md` (`auditGate.mergedSpecMarker`). Run `/summarize` first."

## PHASE 1.5: Escape Analysis

Records where each defect of this feature came from and which gate should have stopped it, and teaches that gate's checklist. Skip this phase when `.claude/checklists/` does not exist.

1. **Collect** every defect found during this feature:
   - gate findings that required a fix (`specs/NNN-*/gates/*.md`, Dispositions `fixed`);
   - code-review Critical findings in the task Completion Notes;
   - `review.md` findings that required a fix;
   - bug files in `bugs/` whose `**Feature**:` points at this spec (the `/verify` triage);
   - any defect the user reported in this session.
2. **Record** each one in `specs/NNN-*/escapes.md`:

   ```markdown
   # Escapes: [feature-name]

   | Id | Introduced | Detected | Should have been caught by | Escaped | Description |
   |----|------------|----------|----------------------------|---------|-------------|
   | E1 | spec / plan / breakdown / code / test / config | [gate or phase that found it: spec-gate, plan-gate, breakdown-gate, task-review, review, verify, user] | [earliest gate whose lens covers it] | yes / no | [one line: the wrong behaviour, not the code] |

   quality: caught: spec-gate n / plan-gate n / breakdown-gate n / task-review n / review n / verify n / user n; escaped past gate: n
   ```

   - The earliest gate: a spec gap → spec-gate; a design gap → plan-gate (name the lens); a coverage, order or contract gap in the tasks → breakdown-gate; a wrong implementation of a correct plan → task-review; a missing or weak test → test-lens.
   - Escaped: `yes` when the defect was detected after that gate.
   - The `quality:` line counts each record once, at the gate or phase that detected it. With no defects, write the table header, `No defects recorded.` and the line with zeros.
3. **Learning step**: for every record with Escaped `yes`, append ONE generic, reusable check to that gate's checklist (`.claude/checklists/<gate>.md`; the test-lens record goes to `test-lens.md`):
   - worded as a check, not as the specific bug;
   - with the next free id and the origin `escape NNN/E<n>`;
   - deduplicated: when an existing item already covers the failure mode, add the origin to that item instead.
4. Commit by path:
   ```
   git add specs/[NNN-feature]/escapes.md .claude/checklists/ && git commit -m "[WIP] Escape analysis: [feature-name]"
   ```

## PHASE 1.6: Structural Hand-off

Skip when `.claude/quality-profile.json` does not set `ratchets` and `specs/[NNN-feature]/review.md` has no "Structural Check" section.

1. **Baselines** (a catch-up: a structural spec lowers its baselines in its last task; any feature may lower one by accident): when the binding sets `ratchets`, run `python3 scripts/forge/ratchet.py check`; for each ratchet it reports `LOWER`, run `python3 scripts/forge/ratchet.py update <name>`. When any baseline changed, commit the baseline file (the binding's `baselineFile`) by path: `git add [baselineFile] && git commit -m "[WIP] Ratchet baselines: [feature-name]"`.
2. **Follow-ups**: from `review.md` → "Structural Check" and "Follow-ups", list the undecided hub edits and third copies as seam-first follow-ups for a later spec, in the Phase 4 output.

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

## PHASE 2.5: Pre-Scaffolding Notes

Greenfield projects only. Search for the token `<!-- default, update after scaffolding -->` in `CLAUDE.md`, `.claude/project-config.json` and `.claude/agents/*.md`. If there are no hits, skip this phase.

For each hit, check whether this feature created what the text describes (the command now exists, the planned path now exists):
- **Created**: replace the default text with the real value (the real command from `package.json` or the build file, the real path) and remove the token. Update `project-config.json` with the same value, so the next `update.sh` substitutes it into the agents and `CLAUDE.md` too.
- **Not created yet**: leave the text and the token.

If anything was replaced, commit the edited files by path:
```
git add CLAUDE.md .claude/project-config.json [edited agent files] && git commit -m "[WIP] Pre-scaffolding notes: [feature-name]"
```
List the remaining hits in the Phase 4 summary under "Pre-scaffolding notes left".

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
   git commit -q -m "feat([feature-name]): [spec title — 1-2 sentences from spec overview]"
   ```
   Follow the **Commit Convention** section in CLAUDE.md (format and attribution rules).
5. If commits were already pushed — skip squash, warn user:
   ```
   ⚠️ WIP commits have already been pushed to remote. Squash skipped to avoid
   rewriting shared history. Consider using an interactive rebase before creating a PR.
   ```

**Source repo squash** (wrapper mode only, `SOURCE_ROOT != "."`): Also run the Source Repo Squash procedure from the Source Repo Auto-Commit section above.

## PHASE 3.5: Close Session State

Skip if `.claude/session-state.md` does not exist.

**Autonomous mode**: a runner skips this phase (`_autonomous-mode.md` → "Session state": parallel runners would overwrite each other's snapshot; the conductor's ledger is the resume source).

After the squash, the snapshot of the feature's last task is stale for every later session (fixes, research, questions) until `/specify` resets it for the next feature. FULLY OVERWRITE `.claude/session-state.md` with this closed-feature template (never append):

```
<!-- This file is a fixed-size sliding window. Always fully overwritten, never appended. Max ~40 lines. -->
# Session State
Last updated after /finalize of [NNN-feature-name] ([YYYY-MM-DD])

## Current Feature
None active. Last finalized: [NNN-feature-name]

## Session Stats
Tasks completed this session: 0
Estimated context load: light (<3 tasks) | moderate (3-5) | heavy (6+)

## Progress
- Finalized: `[short hash]` [commit message] (wrapper mode: wrapper `[short hash]` [message]; source `[short hash]` [message], or "no source changes")
- Pushed: [no (finalize never pushes) / WIP commits were already pushed, squash skipped]; PR: not created
- Next: push the branch(es) and open the PR; then any deploy or runtime check that `summary.md` or `verification.md` lists as pending

## Open Follow-ups
- [up to 5 items that the feature's summary.md / verification.md / review.md mark deferred or open, each with its file pointer; "None" if there are none]

## Active Constraints
- [up to 3 constraints that outlive this feature; omit the section if there are none]
```

Write only facts read in this run (the Phase 3 commit hashes, the follow-ups from the feature's own files). Do not carry over the previous snapshot's decisions, file lists or task counters. Never stage the file (the template's `.gitignore` lists it): Phase 3 has already committed, and this write belongs to no commit. A later `/fix` or `/refactor` keeps the "Open Follow-ups" section while Current Feature is "None active".

## PHASE 4: Present Results

```
## Feature Finalized

**Commit**: [short hash] [commit message]
**Files**: [N] files changed, [insertions] insertions, [deletions] deletions
**Docs**: [updated / skipped — reason]
**Summary**: [included in squash / not found]
**Quality**: [the `quality:` line from escapes.md, or "escape analysis skipped — no checklists"]
**Checklists**: [items added / origins added per checklist, or "no escapes"]
**Ratchets lowered**: [names, or "none"]
**Structural follow-ups**: [undecided hub edits and third copies from review.md, seam first, or "none"]
**Session state**: [closed (no active feature) / skipped (no file) / skipped (autonomous runner)]

Feature is ready for PR.
```

## IMPORTANT RULES

1. **Finalize does not verify code** — it assumes `/verify` has already approved. The gate check (spec Complete) enforces this
2. **Squash is the last operation** — docs are generated and committed as `[WIP]` before squash so they're included in the clean commit
3. **Idempotent safety** — if no WIP commits exist, finalize no-ops gracefully instead of failing
4. **No auto-invoke** — finalize does not automatically run any other command. The user decides what's next
5. **Wrapper mode squash** — both the wrapper repo and the source repo are squashed. Source repo follows the ticket-ID format from the branch name
6. **Session state closes with the feature** — Phase 3.5 overwrites `.claude/session-state.md` after the squash, so no later session reads the finished feature's last task as current work
