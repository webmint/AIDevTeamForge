---
disable-model-invocation: true
user-invocable: false
---
# Autonomous Mode: Rules for Conductor Runs

Referenced by `/conduct` and by every command that has an interactive point. Interactive delivery is the default: every command waits for the user at its gates and questions. Autonomous delivery is opt-in. In it, `/conduct` runs the spec cycle one subagent per phase, and the runners decide where the commands would ask, within the rules below. The user is consulted only for STOP conditions and for the points the project keeps interactive.

## When It Applies

All of these hold:
1. `.claude/project-config.json` sets `DELIVERY_MODE` to `autonomous` (a missing key means `interactive`).
2. The command runs as a conductor runner: its prompt starts with `Forge conductor mode,` (see `/conduct` → "Reference Prompts").
3. The point is not kept interactive. `DELIVERY_GATES` in the same file is a space-separated list of `<point>=interactive` pairs (for example `"specify=interactive fix=interactive"`; empty or missing = none), or `all`: every point except `context` stays interactive (a subagent cannot compact itself, so `context` keeps its autonomous rule), so `/conduct` still runs one runner per phase and each point comes back to the user as `blocked (user gate <point>)`; `all` also covers points added to the table later. The points are the ids in the "Interactive Points" table.

When rule 1 or 2 fails, the command keeps its interactive form, even when the user runs it by hand in an autonomous project. At a point kept interactive (rule 3), the runner stops there: it writes its run report, returns `status: blocked (user gate <point>)` with the summary it would have shown the user, and the conductor asks the user and resumes the runner with the answer.

## Interactive Points

| Point | Command, place | Autonomous behaviour |
|-------|----------------|----------------------|
| `branch` | `/specify` 0.3, on a branch that is neither the default nor `spec/*` | Option 2: switch to `DEFAULT_BRANCH`, then create the spec branch |
| `default-branch` | `/specify` 0.2, no default branch found | Use `DEFAULT_BRANCH` from `.claude/project-config.json` |
| `audit-gate` | `/specify` 0.4: exit 1 (an audit is due); exit 2 on a remediation request after the retry; spec type unsure | Exit 1 and the remediation exit 2: STOP 8, return `blocked (audit due)`; never "start anyway". Spec type: `structural` only when the request remediates audit themes or names no behaviour change; record the choice |
| `existing-spec` | `/research` Phase 1, an existing spec covers the topic | Return `blocked (existing spec specs/NNN-*)`; the conductor resumes that spec |
| `clarify` | `/specify` Phase 2, `/plan` questions, `/fix` questions | Answer from the sources of truth. When they do not answer, take the recommended option and record it as a decision. A question that falls under STOP 1 or 2 is a STOP |
| `specify` | `/specify` Phase 5 HARD GATE | Self-approval (below) |
| `plan` | `/plan` Phase 3 HARD GATE | Self-approval |
| `breakdown` | `/breakdown` Phase 5 HARD GATE | Self-approval |
| `task-review` | `/execute-task` and `/fix` code review options | Critical: "Address now", then one re-review; still BLOCK = STOP 6. Warning: fix it when cheap, otherwise "Continue" and record it in the task's Completion Notes (the fix report for `/fix`). Suggestion and Info: record only |
| `checkpoint` | `_multi-task-continuation.md` review checkpoint | "Continue" |
| `context` | `_multi-task-continuation.md` context health | Ignore the task count. On a context guard message: finish the current task, run the Batch Gate over the completed tasks (unless the stop message forbids it), and return `status: paused (context)` with `next` naming the remaining tasks; never show the compaction prompt |
| `recovery` | `_recovery.md` 0.3, a crash marker `.claude/wip.md` exists | "Resume" when the marker names the same command, task and feature as this runner's prompt; otherwise return `blocked (crash marker: <its summary>)` without touching it |
| `intent` | `/verify` Phase 3.5, the intent check lists DIRECT surfaces the spec's Request section does not answer yet | STOP 1: write the run report and return `blocked (intent: <n> questions)` with the surfaces as questions; never answer them from the sources of truth or the spec. The answers come back on resume (`/conduct` → "Runner Outcomes") |
| `bugs` | `/verify` 9.3 bug filing | "Yes": file every issue. The runner never fixes product code; the conductor runs one `/fix` per bug |
| `fix-scope` | `/fix` Phase 1, "larger than expected" | STOP 1: return `blocked`; the conductor parks it and proposes a `/specify` |
| `fix` | `/fix` Phase 2 diagnosis HARD GATE | Self-confirm the root cause once the evidence shows it (a reproduction, a failing test or a quoted code path), and record it. Without such evidence: STOP 6 after 3 attempts |
| `commit` | `/finalize` and `/fix` source-repo squash message (wrapper mode) | Use the proposed message |
| `research-save` | `/research` "Save this research to a file?" | Yes: save it and commit nothing; the result block names the path |

`/review` has no interactive point; its runner lists every Critical finding of `review.md` under `blockers:` (status `done`), and the conductor runs one `/fix` per Critical. `/refactor`, `/audit`, `/constitute`, `/onboard` and `/setup-wizard` are not conductor phases; they stay interactive.

## Self-Approval at a HARD GATE

A HARD GATE self-approves only after its independent gate (`_independent-gate.md`):
- The gate must run. When its checklist says `**Gate**: off` (or the file is missing), the point is interactive: stop as at a point kept interactive. A breakdown-gate that `_independent-gate.md` skips for a structural spec is not off: the runner checks itself that every copy the plan lists and every Reuse Map row lands in a task, records that in its run report, and self-approves.
- The gate's loop ends with no open Critical. In autonomous mode a Critical the author `rejected` stays open unless the same reviewer's re-check accepts the rejection. A Critical still open after the loop is STOP 6 (the conductor parks the spec).
- Then set the artifact's `**Status**: Approved`, add `Self-approved (autonomous mode, <date>): <checks performed>; gate <gate> C<n> W<n> S<n> I<n>, open Critical: none` under the header, and continue.

An artifact that the user never saw is approved on evidence, not on trust: the gate is what makes self-approval acceptable.

## Sources of Truth

When sources conflict, earlier entries win:
1. the user's instructions;
2. `constitution.md`;
3. the planning sources (`.claude/quality-profile.json` → `planningSources`, when set; otherwise `ROADMAP_FILE` and `docs/`);
4. `docs/architecture.md`;
5. the existing code and docs.

## Decisions

- Record every autonomous decision where it is made: the spec's Decisions or Open Questions closure, the plan's architecture decisions, the fix report.
- When the binding sets `decisionRecords`, also add one row to the unit's own fragment file (`<fragments>/<unit id>.md`: the spec directory name, `fix-<slug>`, `chore-<slug>`); a unit writes only its own fragment. Look up earlier decisions with `python3 scripts/forge/check-decision-records.py --list --grep '<regex>'`.
- A decision never contradicts a constitution rule. A change to one is STOP 2.

## STOP Conditions

Stop, report, and wait for the user:
1. A product decision the sources do not answer and that is costly to reverse (scope, money or legal semantics, data loss). DIRECT surfaces the Request section does not answer yet are STOP 1: only the user answers them (point `intent`).
2. An irreconcilable conflict between sources of truth, or a needed change to a constitution rule.
3. Credentials, accounts, paid or external services: a push other than the routine one under "Pull Requests", any force push, merging a pull request or any merge into a remote branch, a deploy, a change to repository, CI or cloud settings or secrets. A local fast-forward of the default branch to its remote (`git merge --ff-only`) is routine.
4. A system-level install (a package manager, a runtime, a global tool), or an environment problem the agent cannot fix. Project-local installs justified in `plan.md` are routine.
5. A destructive or irreversible operation outside the spec branch (rewriting the default branch's history, deleting user files).
6. The same blocker after 3 attempts (failing tests, flaky infrastructure, a review BLOCK after repair, a gate Critical after its loop).
7. The context guard's stop message in the conductor session.
8. The audit gate is closed (an audit is due, or its blocking themes are unfixed): an audit and its triage need the user.

STOP 1, 3, 4 and 6 confined to one spec park that spec; the others stop the run (`/conduct` → "Park and Continue"). Every STOP report gives what is blocked, the options with a recommendation, and the exact resume command.

## What Every Runner Follows

- **Run the skill**: a phase runner invokes the Forge command its prompt names (Skill tool) and runs it to completion, applying this file at its interactive points. It launches the command's specialist agents itself.
- **Wait for nested agents**: return only after the completion notification of every agent you launched, and after every background shell command you started has ended or been stopped. Never hand back while one runs: ending your turn without a hand-back is how you wait, and the notification wakes you; never sleep-poll. A busy nested agent is never a reason to return `blocked`: wait for its completion notification. In autonomous mode `.claude/hooks/forge/nested-wait-guard.py` refuses a hand-back while work you launched is pending.
- **No sleep polling**: never wait with sleep loops, background `sleep` timers or `until` polls; the completion notification arrives on its own. A wait on an external condition is one foreground command with a bounded timeout. Stop every background shell you started before you return.
- **Check output stays out of context**: run every check (type check, lint, tests, build) through `scripts/forge/gate.sh <name> -- <command>`; read the log only with a targeted search, to diagnose a failure.
- **Review effort follows severity**, as in the `task-review` row. A repair of the same failed item relaunches the specialist one `effort` level above its definition (`medium` → `high` → `xhigh`; never `max`).
- **Instruction and config files**: a finding whose fix would reword `CLAUDE.md`, `.claude/agents/*.md`, `.claude/commands/*.md` or `.claude/project-config.json` beyond an acceptance criterion is recorded for the user, not fixed.
- **Session state**: a runner skips the commands' steps that write or reset `.claude/session-state.md` (reading it is fine): parallel runners would overwrite each other's snapshot. The conductor's ledger is the resume source.
- **Commits**: where you stage yourself, stage by explicit path, never `git add -A` or `.`: another runner may be writing in the same tree. Commit your run report before you return (with the phase's own commit, or alone as `[WIP] Docs: <feature> — <phase> run report`), so the tree is clean. A research runner commits nothing: its report stays untracked until the `/specify` runner commits it on the spec branch.
- **Write refused**: when the harness refuses a runner's Write of `summary.md` (or another report), return its full content with `status: blocked (write refused: <path>)`; the conductor saves it verbatim, commits it, and resumes the runner.
- **Open items**: a finding the unit does not fix (deferred Warning, recorded-only finding, follow-up) goes under `## For the register` in the run report, one line each with its severity. The conductor decides where it goes (an issue, the next spec, the user).

**Run report**: `specs/NNN-*/runs/<phase>[-task-NNN | -W<n>].md` (a research runner: the research report itself). It covers what was done, the gate details, the review findings with their dispositions, the self-approval notes, and one line `binding: <keys of .claude/quality-profile.json the phase read; "(unset)" after a key that fell back> | none`.

**Result block** — the runner's entire final message, at most 10 lines:
```
phase: <phase>[ task NNN | wave W<n>]
spec: <specs/NNN-slug>
status: done | paused (<reason>) | blocked (<reason>) | failed
artifacts: <paths created or changed; the last commit's short sha>
gates: <name=exit (counts)>, …
decisions logged: <n> in <file> | none
blockers: <one line each, with its STOP number or finding id> | none
duration: <h:mm>
nested: all completed (<n>) | none | pending <ids> (a STOP only)
next: <exact next command>
```
- `duration` is the runner's own wall time (`date -u` at its start and before it returns).
- `nested` says how many agents it launched and that all of them completed and no background command of its own still runs. A block without it is unverified: the conductor runs the pre-wave check before it starts anything in that tree. Only a STOP returns while nested work is pending: `status: blocked`, the STOP number on `blockers:` and `nested: pending <every pending id>`; every other return (`done`, `paused`, `blocked (user gate …)`, `blocked (write refused …)`) waits for the notifications first.
- The independent gates run inside the authoring command (`_independent-gate.md`); their reviewers return the gate's own lines, and the authoring runner puts each `**Gate**:` line in its run report and `<gate> C<n> W<n> S<n> I<n>` in `gates:`.

## Pull Requests

`MERGE_MODE` in `.claude/project-config.json` (missing = `local`):
- `local`: the closing runner ends after `/finalize`; the user merges the spec branch.
- `pr`: after `/finalize`, the closing runner pushes the spec branch by name, without force (`git push -u <PUSH_REMOTE> <branch>`, remote default `origin`), and opens a pull request into `DEFAULT_BRANCH` (`gh pr create --base <DEFAULT_BRANCH> --head <branch> --title "<the squashed commit's subject>" --body-file specs/NNN-*/summary.md`). The PR URL goes into `artifacts:`.
- Only the user merges. An open pull request is never force-pushed and gets no new commit.
- **Update** (a rebase because the default branch moved, or a fix after red CI), run by a PR update runner after any `/fix` runner landed its commits on the spec branch:
  1. `git fetch <PUSH_REMOTE>`; `git switch -c <branch>-r<n>` (the next free `n`); `git rebase -q <PUSH_REMOTE>/<DEFAULT_BRANCH>` when it moved (a conflict that is not mechanical: `blocked`).
  2. Squash to one commit with the original message: `git reset --soft $(git merge-base HEAD <PUSH_REMOTE>/<DEFAULT_BRANCH>)`, then `git commit -q -C <the old pull request's squashed commit>`.
  3. Re-run the checks `/verify` ran (through `gate.sh`); a failure is `blocked`.
  4. `git push -u <PUSH_REMOTE> <branch>-r<n>`; `gh pr create` as above with `--head <branch>-r<n>`; `gh pr close <old> --comment "Superseded by #<new>"`.
- Branch names start with a prefix of `PUSH_BRANCH_PREFIXES` (space-separated; default `spec/ fix/ refactor/ chore/`).
- The push guard (`.claude/hooks/forge/push-guard.py`, active in autonomous mode) denies other pushes, force pushes, tags, remote deletions, `gh pr merge`, `gh api` writes, settings and secret writes, and workflow dispatches. It stops accidental actions, not a determined one, and it lets a command through when the guard itself fails: the rules above bind whether or not it fires. A denial is final: no alias, other shell, interpreter, script or config edit around it; report the blocked action instead.
