---
name: review-helper
description: Review-and-fix pipeline for a Python helper file
argument-hint: <path-to-python-file>
disable-model-invocation: true
---

# /review-helper — Python Helper Review-and-Fix Pipeline

Run a five-step audit-fix-test-reaudit pass against one Python helper file in this framework. The orchestrator owns the flow; subagents own the work. The user triages findings between agent dispatches.

## Invocation

```
/review-helper <path-to-python-file>
```

The first positional argument is the helper path. Inside this command, that path is `$0`.

## Inputs

- **Target file** — `$0`, an absolute or repo-relative path to one `.py` helper file (e.g. `src/devforge/lib/detect_report.py`).
- **Reviewer agent** — `python-reviewer` (definition at `.claude/agents/python-reviewer.md`).
- **Engineer agent** — `python-engineer` (definition at `.claude/agents/python-engineer.md`).
- **Test target directory** — `tests/lib/`. Test file naming: `tests/lib/test_<helper-stem>.py` (e.g. `detect_report.py` → `tests/lib/test_detect_report.py`).

## Pre-flight validation

Before dispatching any agent, validate the target:

1. Resolve `$0` to an absolute path. If the path does not exist on disk, print `ERROR: target file not found: <path>` and exit. Do not proceed.
2. If the resolved path does not end in `.py`, print `ERROR: target must be a .py file (got: <path>)` and exit.
3. If the resolved path is a directory, print `ERROR: target must be a single file, not a directory (got: <path>)` and exit.

Validation failure terminates the command. The reviewer agent is not dispatched.

---

## Step 1 — First review

Dispatch the `python-reviewer` agent via the `Agent` tool with `subagent_type: "python-reviewer"`. The brief MUST contain:

- **Target file** — the resolved absolute path from pre-flight.
- **Mode** — first-pass review (no prior fixes to validate; review the file as-is).
- **Scope** — review the entire file. Cover all functions in the file, not a curated subset.
- **Output contract** — count-first findings list per the project audit format (severity / location / issue / why-it-matters / fix). The orchestrator will iterate the list one finding at a time with the user.
- **What NOT to do** — do not modify the file (the agent's tool grant is Read+Bash+Grep, but state it explicitly so the agent does not request escalation).

Capture the agent's full findings list in conversational memory. The orchestrator owns this list across the rest of the pipeline; do not ask the agent to re-emit it later.

If the agent returns zero findings, skip Step 2 entirely and proceed to Step 3 with a tests-only brief (the helper still needs test coverage — every function in a helper script gets a test per the project discipline rule, and the `tests/lib/` directory is initially empty).

---

## Step 2 — Per-finding triage

For each finding in the order the reviewer returned it, present the finding to the user and ask for a disposition. Use the `AskUserQuestion` tool with exactly four options:

- **Fix** — apply the suggested fix in Step 3.
- **Defer** — note for later; do not apply now.
- **Skip** — not a real issue; discard.
- **Discuss** — pause the loop and engage in free-form discussion.

When the user picks **Discuss**, do not advance to the next finding. Engage in conversation until the user converges on `Fix`, `Defer`, or `Skip` for the current finding. Once converged, record the disposition and continue iteration with the next finding.

When the user picks **Fix**, append the finding (full text — severity, location, issue, fix) to an in-memory `approved_fixes` list.

When the user picks **Defer** or **Skip**, do not add the finding to `approved_fixes`. Deferred findings are not persisted by this command; the user is responsible for tracking them.

Do not batch findings into one `AskUserQuestion` call. One finding per turn, one question per turn, per the project's AskUserQuestion contract.

After all findings have been triaged, count the entries in `approved_fixes`. If the count is zero, skip Step 3's fix portion and dispatch the engineer with a tests-only brief (the file is unchanged; tests still need to be written).

---

## Step 3 — Fix and test pass

Dispatch the `python-engineer` agent via the `Agent` tool with `subagent_type: "python-engineer"`. The brief MUST contain:

- **Target file** — the resolved absolute path.
- **Approved fixes** — the full `approved_fixes` list, finding-by-finding, including each finding's location and the reviewer's suggested fix. State explicitly that ONLY these fixes are in scope; do not apply unrelated changes the agent may notice while reading the file.
- **Test mandate** — write a test for every function in the target file. Tests live at `tests/lib/test_<helper-stem>.py`. Use the Python stdlib `unittest` framework. No third-party test dependencies.
- **Real-fixture testing** — for any function that parses output produced by another tool (e.g. helper subcommands that read state files written by `compose` verbs), tests MUST round-trip via the real producer rather than hand-author the input. The agent's own discipline already states this; restate it so the brief is self-contained.
- **Test directory creation** — `tests/lib/` may not exist yet. The agent creates it if needed, including any necessary `__init__.py` files for the chosen test layout.
- **Run the tests** — the agent MUST execute the tests in the same turn and include the actual test output in its return. "Tests written" without "tests passed" is not acceptance.
- **Cross-check** — after applying fixes, grep for callers of any modified function. If a fix changes a function's signature, behavior contract, or return type, callers must be updated in the same turn.
- **Output contract** — return the diff applied to the target file, the new/modified test file content, the test execution output, and any callers updated.

If the engineer agent reports failure (a fix did not apply cleanly, tests did not pass, or a caller cannot be updated), present the failure to the user via `AskUserQuestion` with three options:

- **Retry** — re-dispatch the engineer with the same brief plus the failure context.
- **Skip-fix** — drop the failing fix from `approved_fixes` and re-dispatch with the reduced set.
- **Abort** — terminate the command without proceeding to Step 4. Report what was applied and what was not.

Loop the failure-handler until the engineer succeeds or the user picks **Abort**.

---

## Step 4 — Second review

Dispatch the `python-reviewer` agent again via the `Agent` tool with `subagent_type: "python-reviewer"`. The brief MUST contain:

- **Target file** — the resolved absolute path (now containing applied fixes).
- **Test file** — the new or modified test file at `tests/lib/test_<helper-stem>.py`.
- **Mode** — second-pass review. Focus on (a) bugs introduced by the applied fixes, (b) test quality (real-fixture usage, branch coverage, weak/circular assertions), and (c) any cross-reference fallout from signature or behavior changes.
- **Approved-fix context** — the list of fixes that were applied in Step 3, so the reviewer can verify each one landed correctly.
- **Output contract** — same count-first findings format as Step 1.

Capture the second-pass findings list in conversational memory.

---

## Step 5 — Present second-pass findings

Iterate the second-pass findings the same way as Step 2 (one at a time, `AskUserQuestion` with `Fix / Defer / Skip / Discuss`). Build a new `approved_fixes` list from the second pass.

After triage, branch on the second-pass result:

- **Zero approved fixes** — print a summary covering: number of fixes applied in Step 3, number of tests written, test pass count, number of second-pass findings (broken down by severity), and any deferred items the user noted. The command exits.
- **One or more approved fixes AND no high-severity findings among them** — same summary, plus an explicit note that medium/low items remain unaddressed and the user can re-invoke the command to address them. The command exits.
- **One or more approved fixes including at least one high-severity finding** — offer a follow-up loop. Use `AskUserQuestion` with two options:
  - **Loop** — re-enter Step 3 with the new `approved_fixes` list, then Step 4, then Step 5 again.
  - **Exit** — print the summary as above and terminate without looping.

The follow-up loop has a maximum of two iterations beyond the initial pass. After the third Step 4 review, do not offer **Loop** again — print the summary including all unresolved high-severity items and exit. This bound prevents infinite cycles when fixes keep introducing new issues.

---

## Reporting

The final summary printed at exit covers:

- Target file path.
- Step 1 findings count by severity.
- Approved fixes applied (count + brief location list).
- Tests written (file path + count of test methods + pass/fail).
- Step 4 findings count by severity, plus any subsequent loops.
- Deferred or skipped items the user noted (location only — full content was already shown during triage).
- Exit reason: clean, user-aborted, or loop-bound reached.

## Constraints

- The orchestrator does not write fix code, does not write test code, and does not modify the target file directly. All file mutations go through the `python-engineer` dispatch in Step 3 (and Step 3 of any follow-up loop).
- The orchestrator does not perform the review itself. All findings come from `python-reviewer` dispatches in Step 1 and Step 4.
- `AskUserQuestion` invocations live only in the orchestrator's flow, never inside agent briefs. The triage tool is unavailable to subagents; presenting findings to the user is the orchestrator's responsibility.
- Approved fixes pass to the engineer as an explicit list. The engineer does not receive the full reviewer findings with an "apply only the approved ones" instruction; the orchestrator filters first, then briefs.
- The command does not commit, push, or stage any changes. Git state at exit reflects whatever the engineer wrote; the user owns the commit decision.
