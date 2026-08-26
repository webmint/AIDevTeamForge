---
name: report-bug
description: Capture a bug report for later — PURE CAPTURE, agent-free, NO diagnosis. Writes one structured record under `bugs/` from a free-text description. Does NOT diagnose, fix, or close bugs — `/devforge:research` investigates, `/devforge:specify` fixes.
argument-hint: '"<bug description>" [--file <path>] [--severity Critical|Warning|Info]'
allowed-tools:
  - Read
  - Bash(.devforge/lib/report_bug_helper preflight *)
  - Bash(.devforge/lib/report_bug_helper write-bug *)
---

# /devforge:report-bug — Capture a Bug for Later

`/devforge:report-bug` is a **pure-capture** command: it records a developer-noticed bug as one structured `bugs/NNN-<slug>.md` file so the team can track it and address it later. It is the "file it for later" path for any bug — including a cold bug a developer notices independently of the spec pipeline. It does ONE thing: capture.

**`/devforge:report-bug` does NOT diagnose, fix, or close bugs.** It dispatches no agent, runs no investigation, reads no source code to confirm the defect, and never touches the `bugs/` lifecycle beyond writing a fresh `Open` file. Diagnosis is `/devforge:research`'s job; turning the bug into a fix is `/devforge:specify` → `/devforge:plan` → `/devforge:breakdown` → `/devforge:implement`'s job; the gated remediation loop — in-window on a feature, or cold on one already-filed bug — is `/devforge:fix`'s job. In each bug file the `Open → In Progress → Fixed` lifecycle is maintained MANUALLY by whoever works the bug, with ONE exception: a `/devforge:fix` cold run given that bug file by path flips it to `Fixed` itself once the remediation passes its gates. Either way `/devforge:report-bug` only ever writes the initial `Open` record. File structure, sequential numbering, and the atomic write are owned by `.devforge/lib/report_bug_helper`; the orchestrator composes the values (description, file, severity, date) and dispatches the two verbs.

Usage: `/devforge:report-bug "cart total shows NaN when all items are removed"` · `/devforge:report-bug "login fails silently on bad password" --file src/auth/login.ts` · `/devforge:report-bug "date renders in UTC, should be local" --file src/util/date.ts --severity Critical`.

## Maintainer note

This file lives at `src/commands/report-bug/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/devforge:report-bug` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project.

## Outputs of this command

The only file this command writes is one bug report under `bugs/`:

- `bugs/NNN-<slug>.md` — one structured bug record in the `.devforge/storage-rules.md` format (`**Status**: Open`, `**Source**: manual`, `**Severity**: <severity>`, the description, the optional file, and `**Reported**: <date>`). The `NNN` prefix and the `<slug>` are assigned by `report_bug_helper write-bug` (it scans `bugs/` for the highest existing number and increments); the orchestrator does NOT choose the number or the slug.

`/devforge:report-bug` writes NOTHING else: it does not mutate any spec, plan, task file, or other `bugs/` file, and it makes no git commit (the bug file is left in the working tree for the user to commit). One run writes exactly one bug file.

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/report_bug_helper <verb> ...`. `preflight` prints JSON to stdout (the `bugs_dir` the write targets); `write-bug` prints a JSON array of the written path(s) to stdout. On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns the bugs-directory resolution, file structure, sequential numbering, validation, and atomic write; the orchestrator owns the argument parsing, the user-facing prose, and supplying the current date.

`/devforge:report-bug` keeps NO scratch state and NO run-state file of its own — it is a two-call flow (`preflight` → `write-bug`), so no scratch working directory and no phase-boundary state-flip call appear below.

## PHASE 1 — Parse `$ARGUMENTS`

Extract three things from `$ARGUMENTS`:

1. **Description** (REQUIRED) — the free-text bug description, the text outside the `--file` and `--severity` flags (strip surrounding quotes if present). This is the bug in the developer's own words. **If the description is empty** (the command was invoked with no text, or only flags), do NOT call the helper: ask the user to describe the bug in one or two sentences, then end the turn and wait for their reply.
2. **`--file <path>`** (OPTIONAL) — the suspected file. If `--file` is supplied, verify the path exists (with the Read tool, or by inspecting the working tree). If it does NOT exist, WARN the user inline that the path was not found but CONTINUE — a bug report is still useful without a confirmed file path, and the helper records the path as given. (The helper independently re-checks existence and emits its own warn-but-continue notice; this PHASE-1 check just lets you flag a likely typo before the write.)
3. **`--severity <level>`** (OPTIONAL) — one of `Critical`, `Warning`, `Info`. **Default `Warning`** when the flag is absent. Use `Critical` only when the user explicitly says so or the bug clearly prevents core functionality. If the user supplies a value outside the three (e.g. `High`, `Medium`), tell them the valid severities are `Critical | Warning | Info` and ask which they meant rather than guessing — the helper rejects an out-of-vocabulary `--severity` with exit 2.

## PHASE 2 — Preflight (resolve the bugs directory)

Resolve the target `bugs/` directory — wrapper-mode aware — before writing:

```bash
.devforge/lib/report_bug_helper preflight --workspace-root .
```

`preflight` resolves the workspace (fail-soft to standalone on any config error) and ALWAYS prints JSON `{bugs_dir, root, is_wrapper}` to stdout, exit 0 — it has no gate and never blocks. `bugs_dir` is the absolute path the bug file is written under: `<install_root>/bugs` in BOTH modes — in wrapper mode the bugs live at the install root (the wrapper), NOT inside the inner project sub-directory. Carry `bugs_dir` forward into PHASE 3's `--bugs-dir` argument. (The directory itself is created by `write-bug` on first write, not by `preflight`.)

## PHASE 3 — Write the bug file

Write the bug with `write-bug`, passing the `bugs_dir` from PHASE 2, the current date (which YOU, the orchestrator, supply in `YYYY-MM-DD` form — the helper never calls the clock), and the PHASE-1 values:

```bash
.devforge/lib/report_bug_helper write-bug \
  --bugs-dir "<bugs_dir from PHASE 2>" \
  --date "<TODAY in YYYY-MM-DD>" \
  --description "<the bug description from PHASE 1>"
```

Append `--file "<path>"` when PHASE 1 captured one, and `--severity "<level>"` when the user supplied one (omit it to take the `Warning` default). You may also pass `--title "<short title>"` for a tidy 1–5-word heading; when omitted the helper uses the description as the title.

`write-bug` validates the arguments, builds one bug record, and writes it via the shared writer (`**Source**: manual`, `**Status**: Open`, sequential `NNN-` numbering scanned from `bugs/`). It prints a JSON array of the written path(s) to stdout, exit 0 on success. Handle a non-zero exit:

- **exit 2** — an argument error (missing `--bugs-dir` / `--date` / `--description`, or a `--severity` outside `Critical | Warning | Info`). Copy the helper's stderr VERBATIM into a fenced code block, correct the offending argument, and re-run. (A missing description should already have been caught in PHASE 1; reaching exit 2 for it means the description was dropped between phases — re-derive it from `$ARGUMENTS`.)
- **exit 1** — an I/O error writing the bug file (the helper could not create `bugs/` or write the file). Copy the helper's stderr VERBATIM into a fenced code block and end the turn.

Read the written path from the stdout JSON array (the single element) for PHASE 4.

## PHASE 4 — Confirm + next step

Tell the user the bug was captured. Print the written path, the severity, and the file:

```
Bug reported: <written path from PHASE 3>

  Severity: <severity>
  File(s):  <file path, or "(unknown)" when no --file was given>
```

Then give the forward pointer (and nothing more — `/devforge:report-bug` does not act on the bug):

> To investigate this bug, run `/devforge:research "<description>"`; to address it directly as a feature, run `/devforge:specify "<description>"`.

`/devforge:report-bug` stops here. It does not diagnose the bug, does not fix it, and does not advance its lifecycle — the developer picks up the bug later via `/devforge:research` (investigate) or `/devforge:specify` (turn it into a feature). The `Open → In Progress → Fixed` transitions in the bug file are never this command's to make; rule 7 records who does make them.

## Important rules

1. **Pure capture, no diagnosis** — `/devforge:report-bug` only records a bug. It may be model-invoked (when the user asks to log a bug in conversation) as well as typed by the user; what never changes is WHAT it does, not who invokes it. It dispatches no agent, reads no source to confirm the defect, and runs no investigation.
2. **One bug per file** — if the user describes multiple distinct bugs, run `/devforge:report-bug` once per bug so each gets its own `bugs/NNN-<slug>.md` file. Do not pack several bugs into one record.
3. **Don't diagnose** — this command records the bug as reported; it does not read source to confirm or root-cause it. Diagnosis happens in `/devforge:research`, a full fix in `/devforge:specify` → `/devforge:plan` → `/devforge:breakdown` → `/devforge:implement`.
4. **Sequential numbering is the helper's job** — `write-bug` scans `bugs/` for the highest existing `NNN` and increments. Never hardcode, guess, or compose the number or the slug yourself.
5. **Severity defaults to Warning** — pass `--severity Critical` only when the user says so or the bug clearly breaks core functionality; the three valid values are `Critical | Warning | Info`.
6. **Supply the date yourself** — `write-bug` requires `--date YYYY-MM-DD` and never calls the clock; the orchestrator passes the current date.
7. **Never closes or advances a bug** — `/devforge:report-bug` only ever writes a fresh `Open` record; this command never edits an existing bug file. The `Open → In Progress → Fixed` lifecycle is maintained manually by whoever works the bug, with one exception that is NOT this command's doing: a `/devforge:fix` cold run given a bug file by path closes that one file itself once its remediation passes the gates.
8. **Never call `/devforge:fix` from here** — `/devforge:report-bug` is the file-it-for-later path, the deliberate counterpart to `/devforge:fix`'s remediate-now path. It does not propose, invoke, or chain into `/devforge:fix`; a bug captured here is addressed later through the normal pipeline.
