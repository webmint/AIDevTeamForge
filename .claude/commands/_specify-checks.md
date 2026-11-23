---
disable-model-invocation: true
user-invocable: false
---
# Specify Checks: What Every Spec Asks Before It Is Saved

Referenced by `/specify` Phase 2 and Phase 4: "Decision Points" runs in Phase 2, and again for the points found later, through Phase 4, before the spec is saved. No section is pasted into a gate prompt.

## Decision Points

A decision point is a choice that changes an acceptance criterion, an Out of Scope line or a Decision.

**What, not how.** A choice that only changes how the feature is built is the plan's and is not asked here: the categories of `_plan-checks.md` → "Open Decisions" (placement, timing, the mechanics of failure handling, sharing, the storage model, contracts, dependencies, test seams). Where a topic is shared, the split is:
- **Failure**: `/specify` owns the outcome bound the user observes (for example "the user gets the result, or it is given up and logged, within N minutes") and whether the user gets a duplicate or a missed result; try counts and the interval between attempts are the plan's (`_plan-checks.md` → "Open Decisions": Failure, and "a value within what the spec allows").
- **Settings**: `/specify` owns whether a setting the user configures exists, whether it is required, and what an unset one does. The default of a technical value (a timeout, the interval between attempts, a batch size) is the plan's. A schedule the user observes (how often a job runs) is a criterion's value.
- **Errors**: `/specify` owns the status or exit code the user observes; `/plan` owns the shape of the error body.
- **Compatibility**: `/specify` owns whether a break of an existing consumer is acceptable; `/plan` owns versioning.
- **Stored records**: `/specify` owns whether existing records are included; `/plan` owns the migration and the storage model.

No choice is asked by both commands.

**Settled, not asked.** A choice that one of these decides. The first three decide it only by naming the case, not by implying it or allowing two readings:
- the whole request record (`_intent-check.md` → "The Request Record", items 1–6): the request and every answer recorded so far;
- `constitution.md` and `CLAUDE.md`;
- a fresh `/research` report (Phase 1 step 5): its Request block, its `**This part**:` field and `## Split` answer, and its Constitution Constraints; its `**Depends on**` field settles the constraints it names. Its "Reuse / extend / replace" column, its Approaches and its `**Recommended approach**` line settle nothing: they give the recommended option;
- an existing convention, only for a new instance of itself (the form of a new message, error, exit status or output format), when it applies with one outcome.

A choice settled by `constitution.md`, `CLAUDE.md`, the report or an existing convention gets no `DEC` line of its own; answers and stated or picked numbers are recorded as "Answers" and "One number, not a range" say. Facts about what exists (the code, Prior art, the report's Codebase Findings) are read, not asked: they state what exists today and never decide an outcome, except an existing convention as above.

**Revision.** When the feature directory already has a `spec.md` (Phase 4, "An existing spec keeps its format"; not a change request at this run's HARD GATE), the scan covers only what the change touches; the rest of the spec stands.

**Open, asked.** Scan each category. A point is scanned once, under the first category under which it is a decision point. A clause of a category that the request's behaviour does not reach is skipped, not asked. A choice that no source settles, with two or more valid outcomes, is asked, even when the run has a default it would pick: the default becomes the recommended option, not the answer.
1. **Scope**: which related areas, consumers or commands are included, or only the named one.
2. **Existing behaviour**: an existing behaviour the feature reaches on a path it adds or changes, whose outcome there the request contradicts, changes or leaves open, with two or more valid outcomes (for example a default of code the feature calls). Code and Prior art show what exists, not what should be; the Prior art row's Decision column follows the answer. A conflicting case is a case on the path the feature adds or changes whose outcome would differ from what the behaviour does today, or whose outcome the request leaves open. On a path the feature adds, every case of an existing behaviour it reaches is open unless a source names it (reusing code does not settle it). On a path the feature changes, a case is not left open when each existing behaviour keeps its own outcome on it; an outcome changed only by what the request names keeps the rest as today. A behaviour reused unchanged, with no conflicting case, is not a decision point here; categories 3–8 still apply to its cases.
3. **Inputs and defaults**: each input, option or setting the user gives or configures: whether it exists, required or defaulted, and which default; what a missing, invalid or unset one does. Technical values with no user-facing meaning are the plan's.
4. **What is counted and shown**: what each figure or field means; which records it includes and which it leaves out, and the records at the edge of that rule.
5. **Empty and failing**: what the user sees for an empty result, and when an outside system fails or hangs: whether a message appears and what it must convey, the status or exit code the user observes, and the bound within which the user gets the result or a final failure; how often it runs, when the user observes it.
6. **Order, repeats and restarts**: the sort key, and its rule for letter case, ties and missing values; whether the user gets a duplicate or a missed result when an action repeats, is retried or stops midway; what the user sees after a restart.
7. **Output**: format, units, labels and presentation (a UI state, a message, a file format, column headers). Their exact wording follows an existing output of the same kind, else the run drafts it into the acceptance criterion, not a Decision (the shape of an error body is the plan's). The names of new commands, options, settings and fields follow existing patterns, else are drafted into the criterion; they are not asked.
8. **Compatibility**: whether a break of an existing consumer, response or stored record is acceptable.

**Stop by coverage.** Rounds continue until every decision point found has a user answer, a source that settles it, an Out of Scope line, or an Open Question. An Out of Scope line closes a point only when the request or an answer gives it. An Out of Scope line naming something the request does not ask for (a feature, channel or flow beyond it) is not a decision point; only an area under category 1 that the request's words could reach is. An Open Question stays only when the user chooses so. A request with no open decision point asks nothing and goes to Phase 3.

**Points found later**, in Phase 3 or while drafting the criteria, are asked the same way before the spec is saved, never picked (a number left open within an answer's or the request's words is picked as "One number, not a range" says). Each is recorded as a Phase 2 question (source `/specify Phase 2`).

**One number, not a range.** A value a criterion states (an outcome bound or a limit the user observes) is one number, never a range left to the plan. When an answer or the request leaves a number open within its own words, the run picks one value inside those words and records it as a Decision whose why names the source ("within the answer on retries (Q-3)", or "within the request"); it is not asked again, and Phase 5 shows it. A try count or an interval between attempts that the request or an answer states goes into the spec as a Decision whose why names its source the same way, not into a criterion; `/plan` reads it there. A vague count ("a few tries") is picked within its words and recorded the same way. Only a count no one stated, with no count words at all, stays out of the spec.

**The scan** goes to the conversation, before the first round, or before Phase 3 when nothing is open: the open points, and the settled points that change a criterion, each with its source. It is not written into the spec (`_writing.md` → "Specs": the spec holds only what each section names) and not into the request record (it is not a request).

**Asking.** `AskUserQuestion`, in rounds of up to 4 questions: the recommended option first, each option with one sentence of what it changes. Questions follow category order; a question whose options depend on another answer waits for it. There is no cap on rounds; the sources are the filter.

**Answers.** Each is reflected in the spec as `_intent-check.md` → "The Request Record" says.

**Autonomous mode** (`_autonomous-mode.md`, point `clarify`): each open point is answered as that point says, from the sources of truth as `_autonomous-mode.md` → "Sources of Truth" lists them, the code included. A point that falls under STOP 1 or 2 is a STOP. A point that takes the recommended option has a Decision whose why is `recommended, not settled (autonomous)`. These answers are decisions, never request-record entries.
