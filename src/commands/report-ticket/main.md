---
name: report-ticket
description: Capture a work item for later — PURE CAPTURE, agent-free, NO diagnosis. Writes one structured record under `tickets/` from a free-text idea or pasted tracker-ticket text. Does NOT plan, implement, or advance a ticket file's lifecycle — `/devforge:research` investigates.
argument-hint: '"<work item, or pasted tracker-ticket text>" [--type enhancement|task|imported] [--ticket <ID>]'
allowed-tools:
  - Read
  - Bash(.devforge/lib/report_ticket_helper preflight *)
  - Bash(.devforge/lib/report_ticket_helper write-ticket *)
  - Write
---

# /devforge:report-ticket — Capture a Work Item for Later

`/devforge:report-ticket` is a **pure-capture** command: it records a non-bug work item — a feature idea, an enhancement, a task noticed in passing — as one structured `tickets/NNN-<slug>.md` file so the team can track it and pick it up later. It is also where the text of an external tracker ticket lands when someone has it in hand and no time to start the pipeline: paste it, and the original wording is kept verbatim in a file instead of living only in a chat message. It does ONE thing: capture.

**`/devforge:report-ticket` does NOT plan, implement, or advance anything.** It dispatches no agent, runs no investigation, reads no source code, and never edits an existing ticket file. Turning a captured item into work is `/devforge:research`'s job (investigate it against the codebase), then `/devforge:specify` → `/devforge:plan` → `/devforge:breakdown` → `/devforge:implement`. In each ticket file the `Open → In Progress → Done` lifecycle is maintained MANUALLY by whoever works the item — **no command in this framework flips, fills, or deletes a ticket file**, so a ticket file that is never updated by hand stays `Open` forever, and that is the intended design rather than a fault to remedy. File structure, sequential numbering, slug derivation, validation, and the atomic write are owned by `.devforge/lib/report_ticket_helper`; the orchestrator composes the values (body, type, source, ticket ID, title, date) and dispatches the two verbs.

**A ticket file is not a bug report and the two never share a drawer.** A defect goes to `/devforge:report-bug`, which writes under `bugs/` and whose files `/devforge:fix` can remediate directly. A ticket file is never an input to `/devforge:fix`.

Usage: `/devforge:report-ticket "add CSV export to the reports page"` · `/devforge:report-ticket "split the settings screen into tabs" --type task` · `/devforge:report-ticket "<pasted tracker-ticket text>" --type imported --ticket PROJ-123`.

## Maintainer note

This file lives at `src/commands/report-ticket/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/devforge:report-ticket` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project.

## Two senses of "ticket" — say which one every time

This command sits where the framework's two uses of the word meet, so it never says a bare "ticket":

- **ticket ID** — the identifier a tracker assigns, shape `LETTERS-NUMBER` (e.g. `PROJ-123`). It is what `/devforge:research` asks for when it allocates a feature directory, and it is what this command records in the `**Ticket**:` field.
- **ticket file** — `tickets/NNN-<slug>.md`, the local capture document this command writes. It has its own number, which is local to `tickets/` and unrelated to any tracker.

A ticket file may carry a ticket ID or none. Full conventions live in `.devforge/storage-rules.md`.

## Outputs of this command

The only file this command writes is one ticket capture under `tickets/`:

- `tickets/NNN-<slug>.md` — one structured record in the `.devforge/storage-rules.md` ticket-file format: an `# Ticket NNN: <title>` heading, then `**Status**: Open`, `**Type**`, `**Source**`, `**Ticket**`, `**Reported**`, then the body verbatim. The `NNN` prefix and the `<slug>` are assigned by `report_ticket_helper write-ticket` (it scans `tickets/` for the highest existing number and increments); the orchestrator does NOT choose the number, the slug, or the path. Numbering is local to `tickets/` — a populated `bugs/` never shifts it, so `tickets/001-*.md` and `bugs/001-*.md` can both exist and every reference names the directory.

`/devforge:report-ticket` writes NOTHING else: it does not mutate any spec, plan, task file, bug file, or other ticket file, and it makes no git commit (the ticket file is left in the working tree for the user to commit). One run writes exactly one ticket file.

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/report_ticket_helper <verb> ...`. `preflight` prints JSON to stdout (the `tickets_dir` the write targets); `write-ticket` prints a JSON array holding the written path to stdout. On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns the tickets-directory resolution, file structure, sequential numbering, slug derivation, validation, and atomic write; the orchestrator owns the argument parsing, the user-facing prose, and supplying the current date.

`/devforge:report-ticket` keeps NO run-state file of its own — it is a two-call flow (`preflight` → `write-ticket`), so no phase-boundary state-flip call appears below. It does use one scratch file, for the body only (PHASE 3.1), and removes it when the write succeeds.

## PHASE 1 — Parse `$ARGUMENTS`

Extract five things from `$ARGUMENTS`:

1. **Body** (REQUIRED) — the work item in the user's own words, or the pasted tracker-ticket text: everything outside the `--type`, `--ticket`, `--title` and `--source` flags (strip surrounding quotes if present). Keep it VERBATIM — do not paraphrase it, do not summarize it, do not re-wrap its lines, and do not "clean up" a pasted tracker body. **If the body is empty** (the command was invoked with no text, or only flags), do NOT call the helper: ask the user to describe the work item in a sentence or two, or to paste the tracker-ticket text, then end the turn and wait for their reply. (The helper independently rejects an empty body with exit 2 and writes nothing; this PHASE-1 check just avoids a pointless call.)
2. **`--type <value>`** (REQUIRED by the helper — compose it when the user did not) — one of `enhancement`, `task`, `imported`. Choose by what the input IS, not by how large it is: `imported` when the body is pasted tracker-ticket text; `enhancement` when the item adds or changes what the system does; `task` when it is chore or maintenance work that changes no observable behavior. When the user supplies a value outside the three, tell them the valid types are `enhancement | task | imported` and ask which they meant rather than guessing — the helper rejects an out-of-vocabulary `--type` with exit 2. **Nothing checks that the value is right**: the type is a label for a human reading the drawer later, and no phase of any command validates it against the body.
3. **`--source <value>`** (OPTIONAL, default `manual`) — `paste` when the body is pasted tracker-ticket text, `manual` when the user described the item themselves. In practice `--type imported` and `--source paste` travel together, because both describe the same input; a hand-written item is `manual`. The two valid values are `manual | paste`, and the helper rejects anything else with exit 2.
4. **`--ticket <ID>`** (OPTIONAL) — the tracker ticket ID this item is tracked under, e.g. `PROJ-123`. Pass it exactly as the user typed it: do NOT upper-case it, do NOT add or strip a prefix, and do NOT repair a near-miss such as `proj 123`. The helper validates the shape (`LETTERS-NUMBER`) and rejects what it cannot accept with exit 2, so repairing a value here would bake into the file an ID the user never typed. When no ID is given, omit the flag entirely — the helper records `(none)`.
5. **`--title "<short title>"`** (OPTIONAL) — a tidy 1–5-word heading. When omitted, the helper uses the first non-empty line of the body, which is usually what you want for a pasted tracker body whose first line is its summary.

## PHASE 2 — Preflight (resolve the tickets directory)

Resolve the target `tickets/` directory — wrapper-mode aware — before writing:

```bash
.devforge/lib/report_ticket_helper preflight --workspace-root .
```

`preflight` resolves the workspace (fail-soft to standalone on any config error) and ALWAYS prints JSON `{tickets_dir, root, is_wrapper}` to stdout, exit 0 — it has no gate and never blocks. `tickets_dir` is the absolute path the ticket file is written under: `<install_root>/tickets` in BOTH modes — in wrapper mode the ticket files live at the install root (the wrapper), NOT inside the inner project sub-directory. Carry `tickets_dir` forward into PHASE 3's `--tickets-dir` argument. (The directory itself is created by `write-ticket` on first write, not by `preflight`.)

## PHASE 3 — Write the ticket file

### PHASE 3.1 — Stage the body in a scratch file

**The body never crosses a shell argument boundary.** Write it to a scratch file with the Write tool, then pass that path:

```
${TMPDIR:-/tmp}/forge-report-ticket/body.md
```

Use the Write tool for this — not a shell command, and not a heredoc. It is pre-approved in this command's `allowed-tools`, so staging the body costs no extra confirmation. **The reason is concrete: inside a double-quoted shell argument, backticks and `$(...)` are command substitution, and a pasted tracker-ticket body routinely contains both.** An inline body would therefore arrive mangled, or worse, execute a fragment of somebody's ticket text. There is no inline body argument on the helper at all — `--body-file` is the only route in, so this staging step is not a precaution you may skip.

Write the body bytes EXACTLY as PHASE 1 captured them: no added heading, no added quoting, no trailing commentary, no re-wrapping.

### PHASE 3.2 — Write the ticket file

Write the ticket file with `write-ticket`, passing the `tickets_dir` from PHASE 2, the scratch path from PHASE 3.1, the current date (which YOU, the orchestrator, supply in `YYYY-MM-DD` form — the helper never calls the clock), and the PHASE-1 values:

```bash
.devforge/lib/report_ticket_helper write-ticket \
  --tickets-dir "<tickets_dir from PHASE 2>" \
  --date "<TODAY in YYYY-MM-DD>" \
  --body-file "${TMPDIR:-/tmp}/forge-report-ticket/body.md" \
  --type "<enhancement | task | imported from PHASE 1>"
```

Append `--source paste` when PHASE 1 classified the body as pasted tracker-ticket text (omit it to take the `manual` default), `--ticket "<ID>"` when the user gave one, and `--title "<short title>"` when the user gave one. Passing `-` instead of a path to `--body-file` reads the body from stdin; the scratch-file form above is the one to use, because it leaves the exact bytes on disk for inspection if the write fails. That diagnostic copy is short-lived: the scratch path is fixed, so the next `/devforge:report-ticket` run overwrites it — a failed capture the user wants to keep should be re-run or copied out before the next invocation.

`write-ticket` validates the arguments, reads the body, builds one ticket record, and writes it via the shared writer (`**Status**: Open`, sequential `NNN-` numbering scanned from `tickets/`). It prints a JSON array holding the written path to stdout, exit 0 on success. Handle a non-zero exit:

- **exit 2** — an argument error, and **nothing was written**: a missing `--tickets-dir` / `--date` / `--body-file` / `--type`, a `--type` outside `enhancement | task | imported`, a `--source` outside `manual | paste`, a `--ticket` whose shape the helper rejected, or a body file whose content is empty. Copy the helper's stderr VERBATIM into a fenced code block, correct the offending argument, and re-run. For a rejected `--ticket`, show the user what the helper said and ask for the ID again rather than repairing it yourself.
- **exit 1** — an I/O error (the helper could not read the scratch file, could not create `tickets/`, or could not write the ticket file). Copy the helper's stderr VERBATIM into a fenced code block and end the turn.

Read the written path from the stdout JSON array (the single element) for PHASE 4, then remove the scratch file. Removal happens on success ONLY — a failed run deliberately leaves the staged body in place so it can be inspected, subject to the overwrite window noted above.

## PHASE 4 — Confirm + next step

Tell the user the work item was captured. Print the written path, the type, and the ticket ID:

```
Ticket file written: <written path from PHASE 3>

  Type:      <type>
  Ticket ID: <ID, or "(none)" when no --ticket was given>
```

Then give the forward pointer (and nothing more — `/devforge:report-ticket` does not act on the item):

> To pick this up later, run `/devforge:research tickets/NNN-<slug>.md` — it reads the ticket file as the starting point for its investigation and still asks its own questions from there.

`/devforge:report-ticket` stops here. It does not investigate the item, does not plan it, and does not advance its lifecycle — the developer picks it up later via `/devforge:research`. The `Open → In Progress → Done` transitions in the ticket file are never this command's to make, and rule 7 records that they are nobody's but a human's.

## Important rules

1. **Pure capture, no diagnosis** — `/devforge:report-ticket` only records a work item. It may be model-invoked (when the user mentions an item in conversation and agrees to file it) as well as typed by the user; what never changes is WHAT it does, not who invokes it. It dispatches no agent, reads no source code, and runs no investigation.
2. **One work item per ticket file** — if the user describes several distinct items, run `/devforge:report-ticket` once per item so each gets its own `tickets/NNN-<slug>.md` file. Do not pack several items into one record.
3. **Keep the body verbatim** — the body is recorded as the user gave it. Do not paraphrase, summarize, re-wrap, translate, or tidy a pasted tracker-ticket body; its original wording is the reason this command exists rather than a chat message being enough.
4. **Sequential numbering and the slug are the helper's job** — `write-ticket` scans `tickets/` for the highest existing `NNN` and increments, and derives the slug from the resolved title. Never hardcode, guess, or compose the number, the slug, or the ticket file's path yourself (the PHASE-3.1 scratch path is a different thing — it is a temporary staging file, never the artifact). The sequence is local to `tickets/` and is never shared with `bugs/`.
5. **Supply the date yourself** — `write-ticket` requires `--date YYYY-MM-DD` and never calls the clock; the orchestrator passes the current date.
6. **The body never crosses a shell argument** — stage it in the PHASE-3.1 scratch file and pass `--body-file`. The helper has no inline body argument, so there is nothing to fall back to and nothing to decide.
7. **Write-once — never flips, fills, or deletes a ticket file** — `/devforge:report-ticket` only ever writes a fresh `Open` record, and this command never edits an existing ticket file. The `Open → In Progress → Done` lifecycle is maintained manually by whoever works the item, and **no command in this framework advances it** — there is no automatic closer for a ticket file the way there is for a bug file. A ticket file left `Open` after its work shipped is a stale record a human updates, and nothing detects it.
8. **A ticket ID is a discipline, not a verification** — nothing checks that the ID exists. This framework has no tracker integration, and the only test applied to the value is its shape (`LETTERS-NUMBER`), so `PROJ-0000` satisfies the rule exactly as a real ticket ID does. Recording one is a discipline a project may require of itself; it is never evidence that the tracker agrees.
9. **Say "ticket ID" or "ticket file", never a bare "ticket"** — the two mean different things (see the section above), and a message that says only "ticket" will be read the wrong way by half its readers. This applies to every user-facing message this command prints.
10. **Never call `/devforge:fix` from here** — a ticket file is not a defect record and is never an input to `/devforge:fix`, whose cold lane takes a `bugs/NNN-<slug>.md` path. A captured work item is addressed through the normal pipeline, starting at `/devforge:research`. If what the user described turns out to be a defect rather than a change, file it with `/devforge:report-bug` instead — that is the command whose output `/devforge:fix` can act on.
