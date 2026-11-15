---
disable-model-invocation: true
user-invocable: false
---
# Plan Checks: What Every Plan Asks Before It Is Written

Referenced by `/plan` (Phase 2, before it writes the plan) and `_independent-gate.md` → "Reviewer Prompt", which pastes these sections verbatim into the plan-gate lenses' prompts: "Precedents" and "Runtime" into the architect lens's, "CI-unrun tests" into the QA lens's. A lens reads only its own checklist section, so a rule here reaches it only through that paste.

## Precedents

Every new plan writes a `## Precedents` section, whatever the spec's format. It sits next to the Reuse Map, not inside it: the Map's rows are symbols, decided reuse, extend or new. A Precedents row is a construct the plan adds that the codebase already does somewhere: in this repository or in another repository of the same system that the project's docs or CLAUDE.md name. That rule is the test, not a list of kinds. When the plan adds no such construct, the section is one line: "None: <what was searched>".

One row per construct:

| Construct | Nearest example (path:symbol) | Decision |
|---|---|---|

- **Construct**: what the plan adds, named by what it does.
- **Nearest example**: found by looking at two or three existing examples of the same kind and taking the closest (the same layer, module or kind of data). What such a search looks for, for example:
  - how the row types of storage code are kept private;
  - how a race on create is handled;
  - how each endpoint module documents its contract;
  - how existing schemas spell column types.
- **Decision**: `follow`, or `depart: <one sentence of why>`. A departure is also a row in "Key Design Decisions".

### How the rows are judged

- A missing section, or a row without its example or decision, is a Warning.
- A departure without its "Key Design Decisions" row is a Warning.
- The reviewer repeats the search for two or three of the plan's constructs; a construct with a precedent and no row, or a nearer example than the one cited, is a Warning.

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

_Filled by piece 6 of release 1.41.0 (tests CI never runs); pasted into the QA lens's prompt._
