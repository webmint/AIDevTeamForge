# Independent Gate: Fresh-Context Review Before a HARD GATE

Referenced by `/specify` (spec-gate), `/plan` (plan-gate) and `/breakdown` (breakdown-gate), right before their HARD GATE. An artifact that the next command consumes is reviewed by someone other than its author: a fresh agent that reads the primary sources and works adversarially to a checklist. The user still approves at the HARD GATE; the gate gives them an independent finding list to approve against.

## When It Runs

- The gate runs when `.claude/checklists/<gate>.md` exists and its `**Gate**:` line does not say `off`.
- Otherwise skip it and write `Gate <gate>: off` in the HARD GATE summary. The checklists are project-owned: a project switches a gate off on that line (deleting the file does not work: `update.sh` restores missing checklists).
- A structural spec (`**Type**: structural` in its header; see `/specify` → "Spec type") runs the spec-gate as usual, the plan-gate with the architect lens only (plus the security lens when it touches access control, privileged code, permissions or authentication), and no breakdown-gate: write `Gate breakdown-gate: skipped (structural spec)` in the HARD GATE summary.

## Reviewers

| Gate | Reviewer | Inputs (pass the paths; the reviewer reads them) |
|------|----------|--------------------------------------------------|
| spec-gate | `general-purpose` | `specs/NNN-*/spec.md`; `CLAUDE.md`; `constitution.md` if present; `docs/architecture.md` and the `docs/features/*.md` the spec touches; the `/research` report the spec cites, if any |
| plan-gate | three lenses in parallel, in one message: `architect` (Architect lens), `security-reviewer` (Security lens), `qa-engineer` (QA lens) | `plan.md`; `research.md`, `data-model.md`, `contracts.md` if present; `spec.md`; `CLAUDE.md`; `constitution.md` if present |
| breakdown-gate | `general-purpose` | `tasks/README.md` and every task file; `plan.md`; `contracts.md` if present; `spec.md`; `.claude/commands/_agent-assignment.md` |

- **Model**: run `general-purpose` reviewers on a different model from this session where possible (the Agent tool's `model`: `sonnet` when this session runs Opus, `opus` when it runs Sonnet). The diversity is the point. Specialist agents keep the model of their own definition.
- **Missing agent**: a plan-gate lens whose agent is not in `.claude/agents/` runs as `general-purpose` with the same lens.

## Reviewer Prompt

Fill `<…>`; add only the gate's inputs:

```
Independent gate reviewer. Gate: <gate>[, lens <architect|security|qa>]. Feature: specs/<NNN-*>.
You did not write the artifact under review. Read the primary sources first, then work adversarially through .claude/checklists/<gate>.md[, the "<Lens> lens" section only]. Report any other defect as "new".
Inputs: <the gate's inputs>. Change no file except your report.
For each finding give: severity (Critical / Warning / Suggestion / Info), checklist id or "new", location, and evidence quoted from the artifact and from the source.
Write the full report to specs/<NNN-*>/gates/<gate>[-<lens>].md. Return only one line `<gate>: C<n> W<n> S<n> I<n>`, then one line per Critical and Warning: `<severity> <id> <location> — <one-line defect>`.
```

## Loop

1. **Critical**: fix the artifact, then record each disposition under `## Dispositions` at the end of the gate report (`<id>: fixed — <what changed>` or `<id>: rejected — <reason>`). Then resume the **same** reviewer with `SendMessage` to re-check only those Criticals; if the resume fails, a fresh reviewer with the same prompt plus "Re-check only: <ids>" takes over. One loop: a Critical still open after it goes to the HARD GATE as open.
2. **Warning**: fix it in the same pass when the fix is cheap; otherwise record it as `deferred — <reason>`.
3. **Suggestion / Info**: record only.
4. A finding you believe is wrong is `rejected` with the reason; the user sees it at the gate. Never drop a finding silently.

## At the HARD GATE

Add this line to the summary presented to the user:

`**Gate**: <gate> — C<n> W<n> S<n> I<n>; fixed <n>; open Critical: <ids, or none>; report: specs/<NNN-*>/gates/<gate>.md`

- An open Critical is the user's decision: fix it now, accept it (record `accepted by user — <reason>` in the report's Dispositions), or stop.
- When the user's change requests at the HARD GATE change the artifact's substance (a new or changed AC, design decision, contract or task), run the gate again on the changed parts before asking for approval again.

## Rules

- The reviewer never edits the artifact; only the authoring command does.
- The gate reports are inputs of `/finalize`'s escape analysis: every gate finding that required a fix is an escape record there.
- Keep this session's context small: read the reviewer's returned lines, and open its report only to apply or dispute a finding.
