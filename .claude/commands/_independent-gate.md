---
disable-model-invocation: true
user-invocable: false
---
# Independent Gate: Fresh-Context Review Before a HARD GATE

Referenced by `/specify` (spec-gate), `/plan` (plan-gate) and `/breakdown` (breakdown-gate), right before their HARD GATE. An artifact that the next command consumes is reviewed by someone other than its author: a fresh agent that reads the primary sources and works adversarially to a checklist. The user still approves at the HARD GATE; the gate gives them an independent finding list to approve against.

## When It Runs

- The gate runs when `.claude/checklists/<gate>.md` exists and its `**Gate**:` line does not say `off`.
- Otherwise skip it and write `Gate <gate>: off` in the HARD GATE summary. The checklists are project-owned: a project switches a gate off on that line (deleting the file does not work: `update.sh` restores missing checklists).
- A structural spec (`**Type**: structural` in its header; see `/specify` → "Spec type") runs the spec-gate as usual, the plan-gate with the architect lens only (plus the security lens when it touches access control, privileged code, permissions or authentication), and no breakdown-gate: write `Gate breakdown-gate: skipped (structural spec)` in the HARD GATE summary.
- **Conductor mode** (a `/conduct` phase runner; the prompt's `Phase:` field decides). The breakdown-gate stays inside `/breakdown`. For the spec-gate and the plan-gate:
  - A runner whose Phase is `specify` or `plan` reads the gate's `**Gate**:` line at the gate step. When the gate is off (or its checklist is missing), it runs the command on to its HARD GATE, which is then interactive (`_autonomous-mode.md` → "Self-Approval at a HARD GATE"): it returns `status: blocked (user gate <specify|plan>)` with the HARD GATE summary, which includes `Gate <gate>: off`. Otherwise it does not run the gate. It commits the artifact and its run report, and returns `status: done`, `gates: none (<gate> pending)`, `next: <gate> specs/NNN-*`. The run report adds `## Sources read` (each file read, with the sections or line ranges that mattered) and `## HARD GATE notes` (every note the command puts in the HARD GATE summary, such as the audit-gate notes, plus the decisions-log path).
  - A runner whose Phase is `spec-gate` or `plan-gate` runs this file's gate and Loop on the current artifact, opening only the sources a fix needs. It then follows the authoring command from its gate step to its end. It builds the HARD GATE summary from the artifact and the `## HARD GATE notes`, self-approves (`_autonomous-mode.md`), and runs any later step. Then it commits the artifact's approval changes, the `gates/` reports and its own run report, by explicit path (`_autonomous-mode.md` → "Commits").
  - A fresh gate runner after a park or a failed run runs the gate again on the current artifact; its reports supersede the earlier ones.

## Reviewers

| Gate | Reviewer | Inputs (pass the paths; the reviewer reads them) |
|------|----------|--------------------------------------------------|
| spec-gate | `general-purpose` | `specs/NNN-*/spec.md`; `CLAUDE.md`; `constitution.md` if present; `docs/architecture.md` and the `docs/features/*.md` the spec touches; the `/research` report the spec cites, if any; the source files the spec's Affected Areas name |
| plan-gate | three lenses in parallel, in one message: `architect` (Architect lens), `security-reviewer` (Security lens), `qa-engineer` (QA lens) | `plan.md`; `research.md`, `data-model.md`, `contracts.md` if present; `spec.md`; `CLAUDE.md`; `constitution.md` if present; `docs/architecture.md`; the source files the plan's File Impact names |
| breakdown-gate | `general-purpose` | `tasks/README.md` and every task file; `plan.md`; `contracts.md` and `data-model.md` if present; `spec.md`; `CLAUDE.md`; `.claude/commands/_agent-assignment.md` |

- **Model**: run `general-purpose` reviewers on a different model from this session where possible (the Agent tool's `model`: `sonnet` when this session runs Opus, `opus` when it runs Sonnet). The diversity is the point. Specialist agents keep the model of their own definition, except the plan-gate Architect lens, whichever agent runs it: launch it with the Agent tool's `model` set to `MODEL_ARCHITECT_LENS` from `.claude/project-config.json` (missing = the `MODEL_DO` value). The Security and QA lenses keep their own. The breakdown-gate reviewer is the one exception to the different-model rule: it runs on `sonnet`, also when this session runs Sonnet.
- **Missing agent**: a plan-gate lens whose agent is not in `.claude/agents/` runs as `general-purpose` with the same lens.

## Reviewer Prompt

Fill `<…>`; add only the gate's inputs:

```
Independent gate reviewer. Gate: <gate>[, lens <architect|security|qa>]. Feature: specs/<NNN-*>.
You did not write the artifact under review. Read the primary sources first, then work adversarially through .claude/checklists/<gate>.md[, the "<Lens> lens" section only]. Report any other defect as "new".
Inputs: <the gate's inputs>. Change no file except your report.
For each finding give: severity (Critical / Warning / Suggestion), checklist id or "new", location, and evidence quoted from the artifact and from the source. Report findings only: an item that passes gets no line.
Write the full report to specs/<NNN-*>/gates/<gate>[-<lens>].md. Return only one line `<gate>: C<n> W<n> S<n>`, then one line per Critical and Warning: `<severity> <id> <location> — <one-line defect>`.
With `Re-check only: <ids>`: read only the report's findings for those ids and their Dispositions, the artifact sections those findings locate and the sources they cite. Append your result under `## Re-check` in the existing report; never rewrite it. Return one line per id: `<id>: closed | still open | rejection accepted | rejection not accepted — <reason>`.
```

## Loop

Plan-gate: before any fix, merge the findings of different lenses that name the same defect at the same location into one finding, with the highest of their severities and all their ids. It gets one disposition, recorded in each of those lens reports.

1. **Critical**: fix the artifact, then record each disposition under `## Dispositions` at the end of the gate report (`<id>: fixed — <what changed>` or `<id>: rejected — <reason>`). Then a **fresh** reviewer of the lens (or gate) that raised them re-checks only those Criticals and the step 2 rejections, with the same prompt plus `Re-check only: <ids>` (a resumed reviewer idle past the 5-minute cache rebuilds its whole context). One loop: a Critical still open after it goes to the HARD GATE as open. A rejection not accepted counts as still open; one accepted, as closed.
2. **Warning**: fix it in the same pass when the fix is cheap; otherwise record it as `deferred — <reason>`. A breakdown-gate finding that a task omits or contradicts an AC's literal wording or a contract behaviour is never deferred: it is fixed; a rejection is re-checked by a fresh reviewer as in step 1, and one it does not accept stays open and goes to the HARD GATE as in step 5.
3. **Suggestion**: record only.
4. A finding you believe is wrong is `rejected` with the reason; the user sees it at the gate. Never drop a finding silently.
5. A fix may not turn an AC into an untested exception (moved to manual, to Out of Scope, or to an accepted exception without a test) to close a finding. A finding that only such a fix would close stays open and goes to the HARD GATE as an open Critical, whatever its severity: it keeps its own severity in `C<n> W<n> S<n>`, and its id is listed under `open Critical`.

## At the HARD GATE

Add this line to the summary presented to the user:

`**Gate**: <gate> — C<n> W<n> S<n>; fixed <n>; open Critical: <ids, or none>; report: specs/<NNN-*>/gates/<gate>[-<lens>].md` (plan-gate: one line per lens). An id under `open Critical` may be a finding that Loop step 2 or 5 sends to the HARD GATE as open.

- An open Critical is the user's decision: fix it now, accept it (record `accepted by user — <reason>` in the report's Dispositions), or stop.
- When the user's change requests at the HARD GATE change the artifact's substance (a new or changed AC, design decision, contract or task), run the gate again on the changed parts, reporting Warning and above only, before asking for approval again.

## Rules

- The reviewer never edits the artifact; only the authoring command does.
- The gate reports are inputs of `/finalize`'s escape analysis: every gate finding that required a fix is an escape record there.
- Keep this session's context small: read the reviewer's returned lines, and open its report only to apply or dispute a finding.
