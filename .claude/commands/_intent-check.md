---
disable-model-invocation: true
user-invocable: false
---
# Intent Check: The Change Against the User's Request

Referenced by `/specify` (the request record), `/verify` (Phase 3.5 and its scope-creep check) and `_autonomous-mode.md` (point `intent`). Every other review grades the change against its spec, so a spec that narrows the request (a path the change also had to cover, moved to Out of Scope or pinned to the old behaviour by an AC) passes them all. The user's request is therefore kept verbatim, and `/verify` has a fresh auditor that sees only that request, the code diff and the code, never the spec, report the surfaces the request describes that the change leaves as before.

## The Request Record

Where it is kept follows the spec's format, never mixed:
- **A `**Format**: 2` spec** (that header line; a new spec takes the format of the template in `/specify`): `specs/<KEY|NNN>-*/history.md`; `/specify` creates it in Phase 4. The request is read from exactly two places: the `**Request (verbatim)**` block of the feature's own `specs/<KEY|NNN>-*/research-report.md`, which item 2 then leaves there (not copied), and `history.md`, which holds every other item, a `research/YYYY-MM-DD-<slug>.md` report's block or Topic line included.
- **An older spec**: its own `## Request (verbatim)` section, as below.

"The request record" means that place. It holds, each as a quoted or fenced block:
1. `$ARGUMENTS` exactly as `/specify` received it. When it was empty, the description the user gave in reply.
2. When `/specify` starts from a `/research` report (the user names it, or `$ARGUMENTS` is its path): the report's `**Request (verbatim)**` block (the run of `>` lines after the field), copied whole, labels included. A report from before this block existed: its `**Topic**:` line, labelled `research Topic line, not verbatim`. Arguments beyond the path are recorded separately, labelled `/specify arguments`; a bare path is not recorded as item 1.
3. When the request names another file: the part of it that states the request, verbatim.
4. Each Phase 2 clarification question as asked and the user's answer as given, as Q/A pairs.
5. At the `/specify` HARD GATE, a change request that adds or excludes scope: the user's words, dated.
6. The intent check's questions and the user's answers, Include and Exclude alike, dated ("Handling the Result").

Rules:
- Never paraphrased or summarised. In an older spec, a dated entry reads `Q (<source>, YYYY-MM-DD): <question as asked>` and `A: <answer as given>`, or `User (HARD GATE, YYYY-MM-DD): <words>`. `<source>` is `Phase 2` for clarification questions and `intent check` for the intent check's.
- After the spec is approved, entries are only appended (items 5 and 6); nothing is edited or removed.
- **`history.md` entries** (Format 2), each dated and sourced:
  - The request (items 1–3): `### Request (<source>, YYYY-MM-DD)` over its block; `<source>` is `/specify arguments` (or the reply when they were empty), `conductor Inputs`, the path of the report or file it comes from, or `research Topic line, not verbatim`.
  - A question with its answer (items 4–6): `### Q-N <question as asked> (<source>, YYYY-MM-DD)`, then `A: <answer as given>`. `<source>` is `/specify Phase 2`, `/specify HARD GATE`, `/verify intent` or `size check`. A HARD GATE change request's question is the gate's own.
  - **Numbers**: the command that asks takes the highest `Q-N` in the spec and `history.md`, plus one. An Open Question of the spec (`- **Q-N** …`) keeps its number: once answered, the answer goes under `### Q-N` and the spec drops the open line.
  - **The spec records what was decided**: each answer from Phase 2 or a HARD GATE, change requests included, is reflected in the spec as a `DEC` line, an Out of Scope line or an AC, so the spec hash changes and the gate reviews it; `history.md` keeps the words.
- **A split**: the request is never rewritten. The user's split answer (source `size check`) is an Exclude answer for the parts it leaves to other features, for every reader of the request record.
- **Autonomous mode**: the request record holds the research report's `**Request (verbatim)**` block when the Inputs name a report that has one (the runner's `/specify` arguments, the same topic, are then not recorded again), otherwise the roadmap row or the description from the conductor's Inputs, verbatim; not the previous result block or other Inputs. An answer the runner takes from the sources of truth is a decision, recorded under Decisions (Format 2: a `DEC` line), never a request-record entry.

## Running the Check

1. **Skip**: when an older spec has no `## Request (verbatim)` section (a spec written before 1.36.0), skip the check and write one line in the report: `Intent check: skipped — no verbatim request recorded.` A `**Format**: 2` spec is always checked.
2. **Answers first**: answers to earlier intent questions that have not been recorded yet (given in this session, or carried in the runner's Inputs on an autonomous resume) are appended to the request record, verbatim and dated, before the auditor runs, so it sees them.
3. **Diff**: the feature's code changes from `<base>`, the same base `/review` uses: `git merge-base HEAD <ref>`, with `<ref>` the binding's `integrationRef` (else `origin/[DEFAULT_BRANCH]`, from `.claude/project-config.json`). In wrapper mode, run it in the Source Root repository. The diff is written inside the git directory, never committed:
   ```bash
   X=(':(exclude)specs' ':(exclude).claude' ':(exclude)docs' ':(exclude)research' ':(exclude)bugs' ':(exclude)CLAUDE.md' ':(exclude)constitution.md')
   D="$(git rev-parse --git-path forge)"; mkdir -p "$D"; D="$(cd "$D" && pwd)"
   git status --porcelain --untracked-files=all -- . "${X[@]}" | grep '^??'
   git diff <base> -- . "${X[@]}" > "$D/intent-check.diff"
   ```
   - Untracked files listed by the status line are not in the diff: say so in the report and to the user. Never `git add` them.
   - When the diff file is empty, stop the check: record the Warning `Intent check could not run: empty diff` in "Issues Found" (not blocking; an autonomous runner also lists it under `## For the register` in its run report) and write that line in the report.
   - `<DIFF_PATH>` is `$D/intent-check.diff` (absolute).
4. **Auditor**: launch one fresh `general-purpose` agent, on a different model from this session where possible (as `_independent-gate.md` → "Model"), with the prompt below and nothing else: not the spec, the plan, the tasks or the review. A subagent runs in this session's directory (the Agent tool has no working-directory parameter). After the prompt block, append:
   - always: `Do not read specs/, .claude/, bugs/, research/ or docs/.`
   - in wrapper mode: `The repository after the change is <absolute Source Root path, from CLAUDE.md's Source Root>; read its code there.`
5. **Prompt**: substitute `<REQUEST>` with the full request record, appended answers included (Format 2: the report's block, then `history.md`), and `<DIFF_PATH>` with the absolute diff path:

```
You are an intent-alignment auditor. You have no other context about how this change was produced. Here is the verbatim request this work started from:

<request>
<REQUEST>
</request>

The change under review is the unified diff at `<DIFF_PATH>`. Read that file. The current directory is the repository after the change; read its code as needed to find every place the changed code is reached from.

Your task is strictly descriptive: do not prescribe additional work. Work the request assigns to another ticket, issue, phase or follow-up is not this change's: list it under UNCOVERED-BROADER, never UNCOVERED-DIRECT. Report: (1) the defensible readings of the request, enumerated; (2) which reading this diff implements; (3) where the readings and the diff diverge: which surfaces (the outermost user-facing entry points) the request's expectations could live at, versus which surfaces the diff's changes and its tests exercise.

Review by inspection only. Do not modify files, run builds or tests. End with exactly these lines, one surface per line after each heading, or the word none:
UNCOVERED-DIRECT:
<surfaces the request's own words describe (the feature it names, as its user sees it) that the diff leaves behaving as before>
UNCOVERED-BROADER:
<surfaces only a reading wider than the feature the request names reaches, that the diff leaves behaving as before>
```

## Handling the Result

- **UNCOVERED-DIRECT**: each surface the request record does not answer yet is a question to the user, one at a time:
  ```
  Intent check: the request describes [surface], which this change leaves behaving as before.
  Request: "[the request's words or recorded answer it rests on]"
    1. Include — this change must cover it
    2. Exclude — this change leaves it as it is
  ```
  Append the question and the user's answer to the request record, verbatim and dated, either way.
  - **Include**: record the Critical issue `Intent: <surface> not covered`; the verdict is NEEDS WORK, and the issue goes through `/verify` Phase 9 like any other. When covering it is more than a small fix (new behaviour, new ACs), the next step is a spec revision with `/specify`, not `/fix`.
  - **Exclude**: the item is closed.
  - A surface the request record already answers is not asked again: an Include answer makes it the Critical issue, an Exclude answer closes it. Match a surface to an answer by the entry point it names (screen, route, command, use case), not by its wording; when unsure, it is a new surface. The report quotes the matching record entry for each surface treated as answered.
- **Scope rule**: only the user's answer closes a DIRECT item. The spec's Out of Scope, the plan, a task or a test that keeps the old behaviour is never a reason to close or downgrade it; when only those exclude it, that is the finding.
- **UNCOVERED-BROADER**: each surface goes to the report as Info; no question.
- **Autonomous mode** (`_autonomous-mode.md`, point `intent`): unanswered DIRECT surfaces are STOP 1. Write the run report and return `blocked (intent: <n> questions)` with each surface as a question; never answer them from the sources of truth or the spec. On resume, a fresh `/verify` runner receives the user's answers in its Inputs and applies step 2 of "Running the Check".

**Report**: the verification report's "Intent Check" subsection holds:
```markdown
### Intent Check
- **Readings**: [the auditor's enumerated readings, one line each]
- **Implemented**: [the reading this diff implements]
- **DIRECT**: [surface] — included (Critical issue) | excluded by the user ([date]) [| answered earlier: "<quoted record entry>"] — one line each, or none
- **BROADER** (Info): [surface] — one line each, or none
- **Not in the diff**: [untracked files from step 3] | none
```
When the check was skipped or could not run, the subsection holds only that line from "Running the Check".
