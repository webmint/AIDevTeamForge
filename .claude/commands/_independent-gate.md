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
| spec-gate | `general-purpose` | `specs/NNN-*/spec.md`; `CLAUDE.md`; `constitution.md` if present; `docs/architecture.md` and the `docs/features/*.md` the spec touches; the `/research` report the spec cites, if any; the source files the spec's Affected Areas name; `specs/NNN-*/gates/reviewer-inputs.txt` and `specs/NNN-*/gates/spec.citations.txt` ("Spec-gate checks" step 1) |
| plan-gate | three lenses in parallel, in one message: `architect` (Architect lens), `security-reviewer` (Security lens), `qa-engineer` (QA lens) | `plan.md`; `research.md`, `data-model.md`, `contracts.md` if present; `spec.md`; `CLAUDE.md`; `constitution.md` if present; `docs/architecture.md`; the source files the plan's File Impact names |
| breakdown-gate | `general-purpose` | `tasks/README.md` and every task file; `plan.md`; `contracts.md` and `data-model.md` if present; `spec.md`; `CLAUDE.md`; `.claude/commands/_agent-assignment.md` |

- **Model**: run `general-purpose` reviewers on a different model from this session where possible (the Agent tool's `model`: `sonnet` when this session runs Opus, `opus` when it runs Sonnet). The diversity is the point. Specialist agents keep the model of their own definition, except the plan-gate Architect lens, whichever agent runs it: launch it with the Agent tool's `model` set to `MODEL_ARCHITECT_LENS` from `.claude/project-config.json` (missing = the `MODEL_DO` value). The Security and QA lenses keep their own. The breakdown-gate reviewer is the one exception to the different-model rule: it runs on `sonnet`, also when this session runs Sonnet.
- **Missing agent**: a plan-gate lens whose agent is not in `.claude/agents/` runs as `general-purpose` with the same lens.

## Reviewer Prompt

Fill `<…>`; add only the gate's inputs (spec-gate: also the lines of "Spec-gate checks" step 2):

```
Independent gate reviewer. Gate: <gate>[, lens <architect|security|qa>]. Feature: specs/<NNN-*>.
You did not write the artifact under review. Read the primary sources first, then work adversarially through .claude/checklists/<gate>.md[, the "<Lens> lens" section only]. Report any other defect as "new".
Inputs: <the gate's inputs>. Change no file except your report.
For each finding give: severity (Critical / Warning / Suggestion), checklist id or "new", location, and evidence quoted from the artifact and from the source. Report findings only: an item that passes gets no line.
Write the full report to specs/<NNN-*>/gates/<gate>[-<lens>].md. Return only one line `<gate>: C<n> W<n> S<n>`, then one line per Critical and Warning: `<severity> <id> <location> — <one-line defect>`.
With `Re-check only: <ids>`: read only the report's findings for those ids and their Dispositions, the artifact sections those findings locate and the sources they cite. Append your result under `## Re-check` in the existing report; never rewrite it. Return one line per id: `<id>: closed | still open | rejection accepted | rejection not accepted — <reason>`.
With `Correct citations only: <ids>` (spec-gate) and a citations file: edit only those findings' or re-check entries' citations in the existing report; never rewrite it. Return one line per id: `<id>: corrected | cannot quote — <reason>`.
```

## Loop

Plan-gate: before any fix, merge the findings of different lenses that name the same defect at the same location into one finding, with the highest of their severities and all their ids. It gets one disposition, recorded in each of those lens reports.

Spec-gate: every review, re-check and fix round also runs "Spec-gate checks" steps 3–7.

1. **Critical**: fix the artifact, then record each disposition under `## Dispositions` at the end of the gate report (`<id>: fixed — <what changed>` or `<id>: rejected — <reason>`). Then a **fresh** reviewer of the lens (or gate) that raised them re-checks only those Criticals and the step 2 rejections, with the same prompt plus `Re-check only: <ids>` (a resumed reviewer idle past the 5-minute cache rebuilds its whole context). One loop: a Critical still open after it goes to the HARD GATE as open. A rejection not accepted counts as still open; one accepted, as closed.
2. **Warning**: fix it in the same pass when the fix is cheap; otherwise record it as `deferred — <reason>`. A breakdown-gate finding that a task omits or contradicts an AC's literal wording or a contract behaviour is never deferred: it is fixed; a rejection is re-checked by a fresh reviewer as in step 1, and one it does not accept stays open and goes to the HARD GATE as in step 5.
3. **Suggestion**: record only.
4. A finding you believe is wrong is `rejected` with the reason; the user sees it at the gate. Never drop a finding silently.
5. A fix may not turn an AC into an untested exception (moved to manual, to Out of Scope, or to an accepted exception without a test) to close a finding. A finding that only such a fix would close stays open and goes to the HARD GATE as an open Critical, whatever its severity: it keeps its own severity in `C<n> W<n> S<n>`, and its id is listed under `open Critical`.

## Spec-gate checks

Spec-gate only; the other gates skip it. Each script writes its file under `specs/<NNN-*>/gates/` and prints it. Exit 0 is clean, 1 is findings; on exit 2 (usage or I/O error) note its message in the HARD GATE summary and go on without that check.

1. **Before the reviewer**: run `python3 scripts/forge/spec_lint.py lint specs/<NNN-*>` and fix its blocking findings as in step 4 (record those dispositions once the report exists). Then run `python3 scripts/forge/spec_paths.py specs/<NNN-*>`, which writes `gates/reviewer-inputs.txt` (files to verify, the author's notes on validation and normalisation, a security focus), and `python3 scripts/forge/verify_citations.py spec specs/<NNN-*>/spec.md`, which writes `gates/spec.citations.txt` (not blocking by itself). Pass both files as inputs.
2. **Reviewer prompt**: add these lines.
   ```
   Except with `Re-check only` or `Correct citations only`: read specs/<NNN-*>/gates/reviewer-inputs.txt first: check the spec against every file under `## Files to verify`, and apply its `## Security focus`. Each failure in specs/<NNN-*>/gates/spec.citations.txt is a candidate finding: confirm or dismiss it against the code.
   On validation, normalisation and path-building code, read the whole function and its callees, not a line window.
   Write each finding, Suggestions included, as a heading `### <id> <title>` (ids C-1, W-1, S-1, …) under `## Critical`, `## Warning` or `## Suggestion`. Under `## Re-check`, one `### <id>: <result>` heading per id.
   Every finding carries at least one quoted citation, from the code or from the spec: a code span holding path:N or path:N-M (path from the project root), then on the same line an optional separator (— – - :) and the verbatim quote as a code span (a longer backtick run if it holds backticks) or in double quotes ("…" or “…”; a quote holding " takes a code span). Example: `src/utils/dates.js:144` — `const trimmed = value.trim();`
   The quote must appear in lines N..M, whitespace aside; one cited as path:N may run on past line N; " … " (spaces on both sides) separates fragments that appear in that order. A quote has at least 8 non-space characters (3 per " … " fragment); a range spans at most 300 lines; a citation never points outside the project. Citations under `## Re-check` are checked too.
   A finding whose subject is authorisation, access scope, path or key construction, or personal data is at least Warning, with [security-floor] in its heading.
   ```
3. **After each review or re-check round**: run `python3 scripts/forge/verify_citations.py report specs/<NNN-*>/gates/spec-gate.md` (it writes `gates/spec-gate.citations.txt`). Failures in findings or under `## Re-check` go back once to the same reviewer with `Correct citations only: <ids>` and that file's path: resume it with `SendMessage` when you have that tool, otherwise launch a fresh spec-gate reviewer with the same prompt plus those lines. Run the script again. A finding that still fails gets the disposition `<id>: unverified — <reason>` and is not acted on (no fix, no re-check, not sent back again). A `## Re-check` entry that still fails makes only that re-check result unverified: the finding is not marked `unverified`, and a Critical counts as still open (Loop step 1). An `unverified` finding is not an open Critical, but step 9 lists its id, and an unverified Critical is named in the HARD GATE summary (autonomous mode: also under the run report's `## For the register`). Then run `python3 scripts/forge/spec_lint.py hash specs/<NNN-*> --record` (sets the report's `**Spec hash**:`, drops `**Unreviewed changes**:`). In later runs, failures of ids already `unverified`, and of re-check results already unverified, are ignored, and failures on `## Dispositions` lines are yours to fix (step 5); only failures in findings or under `## Re-check` go back to a reviewer.
4. **After every fix round**: run `python3 scripts/forge/spec_lint.py lint specs/<NNN-*>` (it writes `gates/spec-lint.txt`), fix the blocking findings (`B` codes) and run it again; the rest goes to the HARD GATE. A lint finding's id is `<code>-<spec line>` (`B3-9`); record each lint fix as `- B3-9: fixed — <what changed> [spec-lint]`. Then run `verify_citations.py report` again: it checks the new dispositions.
5. **Security floor**: a `[security-floor]` finding may be `recorded`, `deferred` or `rejected` only with a disposition that opens and quotes the cited code (step 2's citation form); the script checks it. When it fails, fix the finding, or it goes to the HARD GATE as open.
6. **Unreviewed changes**: `python3 scripts/forge/spec_lint.py hash specs/<NNN-*> --unreviewed "<ids>"` replaces the `**Unreviewed changes**:` line. Run it after a re-check round's `--record`, with the preceding fix round's fixes the re-check did not cover (Warning fixes, lint fixes), and after a fix round no review round follows, with the ids already on the line plus every fix since the last `--record` (`"W-2 B3-9"`).
7. **Disposition lines**: one line each, `- <id>: <disposition> — <text> [<mechanism>]`, ending with the mechanism that produced or blocked it: `[reviewer]` (a review-round finding), `[re-check]` (a disposition after a re-check), `[spec-lint]` (a lint finding), `[verify-citations]` (an `unverified` finding, or a security-floor disposition the script failed).
8. **Traces**: `gates/reviewer-inputs.txt`, `gates/spec.citations.txt`, `gates/spec-gate.citations.txt`, `gates/spec-lint.txt`, `gates/spec-hash.txt`, and the report's `**Spec hash**:` and `**Unreviewed changes**:` lines. A conductor-mode runner commits them with the `gates/` reports.
9. **At the HARD GATE**: run `python3 scripts/forge/spec_lint.py hash specs/<NNN-*> --check` and append to the spec-gate `**Gate**:` line `; spec hash: <unchanged | unchanged, unreviewed: <ids> | changed after review, unreviewed: <ids>>; lint: B<n> A<n> (gates/spec-lint.txt); unverified: <ids | none>`; name an unverified Critical in the summary (step 3).

## At the HARD GATE

Add this line to the summary presented to the user:

`**Gate**: <gate> — C<n> W<n> S<n>; fixed <n>; open Critical: <ids, or none>; report: specs/<NNN-*>/gates/<gate>[-<lens>].md` (plan-gate: one line per lens). An id under `open Critical` may be a finding that Loop step 2 or 5 sends to the HARD GATE as open, or that "Spec-gate checks" step 5 sends there. Spec-gate: run that section's step 9 first.

- An open Critical is the user's decision: fix it now, accept it (record `accepted by user — <reason>` in the report's Dispositions), or stop.
- When the user's change requests at the HARD GATE change the artifact's substance (a new or changed AC, design decision, contract or task), run the gate again on the changed parts, reporting Warning and above only, before asking for approval again.

## Rules

- The reviewer never edits the artifact; only the authoring command does.
- The gate reports are inputs of `/finalize`'s escape analysis: every gate finding that required a fix is an escape record there.
- Keep this session's context small: read the reviewer's returned lines, and open its report only to apply or dispute a finding.
