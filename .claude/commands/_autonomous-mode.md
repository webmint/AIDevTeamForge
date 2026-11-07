# Autonomous Mode: Rules for Conductor Runs

Referenced by `/conduct` and by every command that has an interactive point. Interactive delivery is the default: every command waits for the user at its gates and questions. Autonomous delivery is opt-in. In it, `/conduct` runs the spec cycle one subagent per phase, and the runners decide where the commands would ask, within the rules below. The user is consulted only for STOP conditions and for the gates the project keeps interactive.

## When It Applies

All of these hold:
1. `.claude/project-config.json` sets `DELIVERY_MODE` to `autonomous` (a missing key means `interactive`).
2. The command runs as a conductor runner: its prompt starts with `Forge conductor mode,` (see `/conduct` → "Reference prompts").
3. The point is not kept interactive. `DELIVERY_GATES` in the same file is a space-separated list of `<point>=interactive` pairs (for example `"specify=interactive fix=interactive"`; empty or missing = none). The points are the ids in the "Interactive Points" table.

When rule 1 or 2 fails, the command keeps its interactive form, even when the user runs it by hand in an autonomous project. At a point kept interactive (rule 3), the runner stops there: it writes its run report, returns `status: blocked (user gate <point>)` with the summary it would have shown the user, and the conductor asks the user and resumes the runner with the answer.

## Interactive Points

| Point | Command, place | Autonomous behaviour |
|-------|----------------|----------------------|
| `branch` | `/specify` 0.3, on a branch that is neither the default nor `spec/*` | Option 2: switch to `DEFAULT_BRANCH`, then create the spec branch |
| `audit-gate` | `/specify` 0.4, exit 1 (an audit is due) | STOP 8: return `blocked (audit due)`; never "start anyway" |
| `clarify` | `/specify` Phase 2, `/plan` questions, `/fix` questions | Answer from the sources of truth. When they do not answer, take the recommended option and record it as a decision. A question that falls under STOP 1 or 2 is a STOP |
| `specify` | `/specify` Phase 5 HARD GATE | Self-approval (below) |
| `plan` | `/plan` Phase 3 HARD GATE | Self-approval |
| `breakdown` | `/breakdown` Phase 5 HARD GATE | Self-approval |
| `task-review` | `/execute-task` code review options, `/fix` and `/refactor` code review options | Critical: "Address now", then one re-review; still BLOCK = STOP 6. Warning: fix it when cheap, otherwise "Continue" and record it in the task's Completion Notes. Suggestion and Info: record only |
| `checkpoint` | `_multi-task-continuation.md` review checkpoint | "Continue". The context pause does not apply to a runner: a wave runner runs one wave and returns |
| `bugs` | `/verify` 9.3 bug filing | "Yes": file every issue. The runner never fixes product code; the conductor runs one `/fix` per bug |
| `fix-scope` | `/fix` Phase 1, "larger than expected" | STOP 1: return `blocked`; the conductor parks it and proposes a `/specify` |
| `fix` | `/fix` Phase 2 diagnosis HARD GATE | Self-confirm the root cause once the evidence shows it (a reproduction, a failing test or a quoted code path), and record it. Without such evidence: STOP 6 after 3 attempts |
| `commit` | `/finalize` squash message | Use the proposed Conventional Commit message |
| `research-save` | `/research` "Save this research to a file?" | Yes: save it, commit nothing; the result block names the path |

`/refactor`, `/audit`, `/constitute`, `/onboard` and `/setup-wizard` are not conductor phases; they stay interactive.

## Self-Approval at a HARD GATE

A HARD GATE self-approves only after its independent gate (`_independent-gate.md`):
- The gate must run. When its checklist says `**Gate**: off` (or the file is missing), the point is interactive: stop as at a point kept interactive.
- The gate's loop ends with no open Critical. A Critical still open after the loop is STOP 6 (the conductor parks the spec).
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
1. A product decision the sources do not answer and that is costly to reverse (scope, money or legal semantics, data loss).
2. An irreconcilable conflict between sources of truth, or a needed change to a constitution rule.
3. Credentials, accounts, paid or external services: a push other than the routine one under "Pull requests", any force push, any merge, a deploy, a change to repository, CI or cloud settings or secrets.
4. A system-level install (a package manager, a runtime, a global tool), or an environment problem the agent cannot fix. Project-local installs justified in `plan.md` are routine.
5. A destructive or irreversible operation outside the spec branch (rewriting the default branch's history, deleting user files).
6. The same blocker after 3 attempts (failing tests, flaky infrastructure, a review BLOCK after repair, a gate Critical after its loop).
7. The context guard's stop message in the conductor session.
8. The audit gate is closed (an audit is due, or its blocking themes are unfixed): an audit and its triage need the user.

STOP 1, 3, 4 and 6 confined to one spec park that spec; the others stop the run (`/conduct` → "Park and Continue"). Every STOP report gives what is blocked, the options with a recommendation, and the exact resume command.

## What Every Runner Follows

- **Run the skill**: a phase runner invokes the Forge command its prompt names (Skill tool) and runs it to completion, applying this file at its interactive points. It launches the command's specialist agents itself.
- **Wait for nested agents**: return only after the completion notification of every agent you launched, and after every background shell command you started has ended or been stopped. Never end the turn while one runs.
- **No sleep polling**: never wait with sleep loops, background `sleep` timers or `until` polls; the completion notification arrives on its own. A wait on an external condition is one foreground command with a bounded timeout. Stop every background shell you started before you return.
- **Check output stays out of context**: run every check (type check, lint, tests, build) through `scripts/forge/gate.sh <name> -- <command>`; read the log only with a targeted search, to diagnose a failure.
- **Review effort follows severity**, as in the `task-review` row. A repair of the same failed item relaunches the specialist one `effort` level above its definition (`medium` → `high` → `xhigh`; never `max`).
- **Instruction and config files**: a finding whose fix would reword `CLAUDE.md`, `.claude/agents/*.md`, `.claude/commands/*.md` or `.claude/project-config.json` beyond an acceptance criterion is recorded for the user, not fixed.
- **Session state**: only the conductor writes `.claude/session-state.md`. A runner skips the commands' session-state steps (reading it is fine): parallel runners would overwrite each other's snapshot.
- **Commits**: stage by explicit path, never `git add -A` or `.`: another runner may be writing in the same tree.
- **Summary write refused**: when the harness refuses a runner's Write of `summary.md` (or another report), return its full content with `status: blocked (write refused: <path>)`; the conductor saves it verbatim, commits it, and resumes the runner.
- **Open items**: a finding the unit does not fix (deferred Warning, recorded-only finding, follow-up) goes under `## For the register` in the run report, one line each with its severity. The conductor decides where it goes (an issue, the next spec, the user).

**Run report**: `specs/NNN-*/runs/<phase>[-task-NNN].md` (a research runner: the research report itself). It covers what was done, the gate details, the review findings with their dispositions, the self-approval notes, and one line `binding: <keys of .claude/quality-profile.json the phase read; "(unset)" after a key that fell back> | none`. It is committed with the phase.

**Result block** — the runner's entire final message, at most 10 lines:
```
phase: <phase>[ task NNN | wave W<n>]
spec: <specs/NNN-slug>
status: done | blocked (<reason>) | failed
artifacts: <paths created or changed; the last commit's short sha>
gates: <name=exit (counts)>, …
decisions logged: <n> in <file> | none
blockers: <one line each, with its STOP number> | none
duration: <h:mm>
nested: all completed (<n>) | none
next: <exact next command>
```
- `duration` is the runner's own wall time (`date -u` at its start and before it returns).
- `nested` says how many agents it launched and that all of them completed and no background command of its own still runs. A block without it is unverified: the conductor runs the pre-wave check before it starts anything in that tree.
- The independent gates run inside the authoring command (`_independent-gate.md`); their reviewers return the gate's own lines, and the authoring runner puts each `**Gate**:` line in its run report and `<gate> C<n> W<n> S<n> I<n>` in `gates:`.

## Pull Requests

`MERGE_MODE` in `.claude/project-config.json` (missing = `local`):
- `local`: the closing runner ends after `/finalize`; the user merges the spec branch.
- `pr`: after `/finalize`, the closing runner pushes the spec branch by name, without force (`git push -u <PUSH_REMOTE> <branch>`, remote default `origin`), and opens a pull request into `DEFAULT_BRANCH` (`gh pr create --base <DEFAULT_BRANCH> --head <branch> --title "<the squashed commit's subject>" --body-file specs/NNN-*/summary.md`). The PR URL goes into `artifacts:`.
- Only the user merges. An open pull request is never force-pushed and gets no new commit: a change (a rebase because the default branch moved, a fix after red CI) is made locally, squashed, pushed as `<branch>-r<n>`, opened as a new pull request, and the old one is closed with `gh pr close <old> --comment "Superseded by #<new>"`.
- Branch names start with a prefix of `PUSH_BRANCH_PREFIXES` (space-separated; default `spec/ fix/ refactor/ chore/`).
- The push guard (`.claude/hooks/forge/push-guard.py`, active in autonomous mode) denies every other push, force pushes, tags, remote deletions, merges and settings writes. A denial is final: no alias, other shell, interpreter, script or config edit around it; report the blocked action instead.
