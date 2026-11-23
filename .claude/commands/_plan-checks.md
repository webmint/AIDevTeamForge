---
disable-model-invocation: true
user-invocable: false
---
# Plan Checks: What Every Plan Asks Before It Is Written

Referenced by `/plan` ("The /research Report" in Phase 0, "Open Decisions" in 1.7, the other sections in Phase 2) and `_independent-gate.md` → "Reviewer Prompt", which pastes two sections verbatim into the plan-gate lenses' prompts: "Runtime" into the architect lens's, "CI-unrun tests" into the QA lens's. A lens reads only its own checklist section, so a rule here reaches it only through that paste; the first two sections are not pasted.

## The /research Report

Read in Phase 0, before Step 1.

1. **Which report**: the feature directory's `research-report.md`; otherwise the `research/YYYY-MM-DD-<slug>.md` report the request record names (the source of a `### Request` entry in `history.md`, or an older spec's Request section). None: Phase 0 runs without one.
2. **Fresh or stale**: `git fetch origin`, then `git diff --name-only <Investigated at> <ref> -- <Scoped paths>`, `<ref>` being the binding's `integrationRef`, else `origin/[DEFAULT_BRANCH]` (as `/specify` Phase 1 step 5). A failed fetch is noted in the HARD GATE summary, and the diff runs against the ref as it is. Any output, or no `**Investigated at**:` line: the report is stale. It is read for leads only; it settles nothing and is not cited.
3. **A fresh report**:
   - Step 1 starts from its Codebase Findings and Reuse or Extend rows. Where they and the spec's "Prior art" disagree, Prior art wins (1.5 step 0).
   - A signal it answers (its Approaches, External Research and `**Recommended approach**` line) is not researched again: the Key Design Decisions row cites the report and quotes the finding it uses, in a line or two.
   - A version, API or limit it states is checked again (Context7 first), because the report may predate a release; a difference goes into `research.md`.
   - `research.md` holds only the signals the report does not answer and those differences. With none, there is no `research.md`, and Supporting Documents lists the report.

## Open Decisions

Run in 1.7, after 1.6 and before Phase 2. A design choice that two runs of `/plan` could take two ways is the user's.

**Settled, not asked.** A choice that one of these decides; when it has a Key Design Decisions row, the row names the source as its why:
- the spec: its criteria, Out of Scope and Decisions;
- `constitution.md` and `CLAUDE.md`;
- a fresh `/research` report (above);
- an existing pattern in the code (IMPORTANT RULES 3);
- `plan.md` itself: 1.5 (the owner by Information Expert, the layer directions, no abstraction without a confirmed axis, the extraction threshold, a seam task before a third copy) and 1.6, whose deferral keeps its own question;
- on a re-run, the earlier `specs/[feature-name]/plan.md`'s rows whose why names the user's answer, while its `**Spec hash**:` line equals what `python3 scripts/forge/spec_lint.py hash specs/[feature-name]` prints now (no flag: it prints and writes nothing). They are carried into the new plan unchanged. A different hash, or no such line, asks them again.

`research.md` settles no choice between valid options: its comparison gives the recommended one.

**Open, asked.** Scan each category. A choice in it that no source settles, with two or more valid options, is asked:
1. **Placement**: which module or layer holds new behaviour, when two existing ones could.
2. **Timing**: in the request, after the response, or in a background or scheduled job.
3. **Failure**: how a failed attempt is retried and counted; what a crash mid-way, a repeat or a second instance does.
4. **Sharing**: a shared helper or local code, where the extraction threshold does not decide.
5. **Data**: the storage model (a field on an existing record, or a new collection or table) and what happens to existing records.
6. **Contracts**: a choice that changes compatibility or errors: a breaking change or a new version, the error contract of a new endpoint or message. Names and types of fields follow existing patterns and are not asked.
7. **Dependencies**: a new library or code of the project's own, where the constitution does not decide.
8. **Tests**: the seam through which tests replace an outside service, a clock or a store.

**Asking.** `AskUserQuestion`, in rounds of up to 4 questions: the recommended option first, each option with one sentence of what it changes. A question whose options depend on another answer waits for it. There is no cap; the sources are the filter.

**Answers.**
- Each is a Key Design Decisions row whose why names the user's answer: a `DEC` row in a `**Format**: 2` plan (`_writing.md` → "Plans"), a row without an id in an older one. It is not a request-record entry.
- One that changes `data-model.md` or `contracts.md` updates them; one that changes File Impact re-runs 1.5 step 5 and 1.6 for the changed files.
- One that contradicts or adds to an acceptance criterion, an Out of Scope line or a spec decision is not a plan decision; any choice the criteria allow is. Say so and stop before Phase 2; `/plan` runs again after `/specify` revises the spec; that run rewrites the files this one saved.
- **They hold.** A plan-gate fix or a HARD GATE change that would overturn one goes back to the user, never into the fix loop.

**Autonomous mode** (`_autonomous-mode.md`, point `clarify`): each open choice is answered as that point says; one that is a costly product decision or needs a constitution change stops the run (STOP 1 or 2). A choice that takes the recommended option has the why `recommended, not settled (autonomous)`.

## Runtime

Every new plan writes a `## Runtime` section, whatever the spec's format. It applies when the feature adds or changes a write, background or scheduled work, or an entry point (a server handler, a job, a scheduled task, a queue consumer). Otherwise the section is one line: "No runtime paths."

What the section holds follows what the feature does, not the project type:
- **Server-side work** (a handler, a job, a queue consumer, background or scheduled work): both tables below, under `### Write paths` and `### Time budget`.
- **A client feature that calls a write**: one line per write call, with two answers: can the user trigger it twice, and what the user sees when it fails or hangs. No time-budget table: the limit belongs to the server.
- **A client feature with no writes**: "No runtime paths."

### Write paths

One row per write path (a route, a job, a scheduled run, a queue consumer):

| Write path | Runs it twice | Second attempt after the first took effect | Redelivery | Who learns of a failure |
|---|---|---|---|---|

- **Runs it twice**: every layer that can, found by search: the project's retry wrapper, SDK retries, gateway or scheduler retries, a job's retry setting, the user acting twice; searched in code and in infrastructure and workflow config.
- **Second attempt after the first took effect**: what the repeat sees and returns when the first already committed or sent, including when the caller saw it fail on a deadline while it ran on.
- **Redelivery**: what delivers a failed delivery again, and whether that path still has something to send once the change is stored, and accepts this data. A send made only when the data changes is lost when that one send fails.
- **Who learns of a failure** without polling: an alert, a metric, a stored pending state a job retries, or "accepted blind spot" with who accepted it. Work no user watches never answers "the response says so".

### Time budget

One row per entry point the feature adds or changes, reads included:

| Entry point | Platform limit (where set) | Worst case | Scale |
|---|---|---|---|

- **Platform limit**: the gateway deadline or its default, the function or service timeout, the scheduler's attempt deadline, a workflow step's timeout; with the file or setting that sets it.
- **Worst case**: the sequential remote calls times their latency, plus the retry budget.
- **Scale**: the figure the worst case is computed at. It is measured where the project allows (the base, a fixture, a recorded count), with the command. Without access it is an estimate with its assumption written down.

### How the rows are judged

- A worst case at or above half the limit is a Warning; one over the limit is Critical.
- A row whose scale is an estimate is a Warning until a figure exists. It is never a stop.
- A missing table, row or column for a path this section covers is a Warning. The reviewer repeats the "Runs it twice" search; a layer the plan missed is a Warning.

## CI-unrun tests

The QA lens checks the test the plan names as each criterion's proof against the project's CI configuration: the workflow, pipeline and job files of the repository the tests live in (under the Source Root in wrapper mode), followed through the commands they call to the test runner's include and exclude patterns.

- A test that is a criterion's only proof and that no CI job runs is a Warning. The finding names the criterion, the test, and the CI file and command that leave it out.
- A standing project decision that CI runs only some suites (a constitution rule, or a recorded decision) does not lift this Warning; the finding cites the decision.
- A repository with no CI configuration is one Note that says so, not a Warning per test.
