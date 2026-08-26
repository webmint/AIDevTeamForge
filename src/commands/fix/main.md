---
name: fix
description: Proposal-only gated remediation of already-written findings, in one of two lanes. The FEATURE lane is OFFERED (never auto-invoked) when `/devforge:review` surfaces findings, when `/devforge:verify` returns NEEDS WORK, or conversationally when the user raises a defect the model code-confirms in-window. The COLD lane runs on an explicit `bugs/NNN-<slug>.md` argument and remediates one already-filed bug with no feature involved. Either lane intakes the finding, triages + scopes it, then delegates to `/devforge:implement`'s back-half engine (scope-aware verify + self-repair → four-reviewer panel → forcing-functions gate → two-stage hard gate → commit). Never invents a defect, never accepts a free-text bug description; the only `bugs/` write is flipping the ONE consumed bug file to Fixed at the end of a cold run.
argument-hint: "[spec-file/feature-dir | bugs/NNN-slug.md]"
disable-model-invocation: true
allowed-tools:
  - Bash(.devforge/lib/fix_helper preflight *)
  - Bash(.devforge/lib/fix_helper in-fix-window *)
  - Bash(.devforge/lib/fix_helper read-findings *)
  - Bash(.devforge/lib/fix_helper resolve-scope *)
  - Bash(.devforge/lib/fix_helper write-seed *)
  - Bash(.devforge/lib/fix_helper close-bug *)
  - Bash(.devforge/lib/artifact_helper commit-artifacts *)
  - Bash(.devforge/lib/implement_helper verify-touched *)
  - Bash(.devforge/lib/implement_helper merge-review-panel *)
  - Bash(.devforge/lib/implement_helper run-forcing-functions-gate *)
  - Bash(.devforge/lib/implement_helper wip-commit *)
  - Bash(git diff *)
  - Bash(git -C * diff *)
---

# /devforge:fix — Gated Remediation of Written Findings

`/devforge:fix` is a thin, gated **remediation** command. It is OFFERED (PROPOSED), never auto-invoked (this command sets `disable-model-invocation: true` in its own frontmatter, so the model cannot invoke it). When invoked it intakes an already-written, already-located finding, triages + scopes it, then points `/devforge:implement`'s already-shipped back-half engine at that finding instead of at a fresh task.

**Two lanes, and which one runs is decided mechanically by the argument — never by judgment.**

- **The FEATURE lane** — the "remediate now" arm of a two-arm fix-or-file offer, run in exactly three in-window situations: `/devforge:review` surfaces findings, `/devforge:verify` returns NEEDS WORK, or the user raises a defect the model code-confirms while the active feature is post-`/devforge:implement`/pre-`/devforge:summarize`. Entered when `$ARGUMENTS` is empty or names a feature directory or a spec file. Ends in a `[WIP]` commit that `/devforge:finalize` squashes.
- **The COLD lane** — entered when, and only when, `$ARGUMENTS` names a file under `bugs/` (e.g. `bugs/007-null-cart-total.md`). It remediates ONE already-filed bug with no feature involved: no feature directory, no fix window, no `[WIP]`. It ends in one clean `fix(<scope>): <title>` commit and flips that one bug file to `Fixed`.

**The lanes share PHASES 1–7 entirely.** Only PHASE 0's intake differs, plus the commit call at PHASE 6 and the bug-file flip that follows it. Everything the back half does — verify + self-repair, the four-reviewer panel, the forcing-functions gate, the two-stage human hard gate — is IDENTICAL in both lanes. The cold lane drops the gates that have no meaning without a feature; it drops no gate that is about the CODE.

**`/devforge:fix` reuses `/devforge:implement`'s back half — it does NOT re-implement it.** PHASES 3–6 below CALL the installed `implement_helper` verbs (`verify-touched`, `merge-review-panel`, `run-forcing-functions-gate`, `wip-commit`) exactly as `/devforge:implement` PHASES 5–7 wire them. Those verbs are single-source-of-truth binaries; this spec orchestrates them, it copies none of their machinery (no `PACKAGE_STACKS` logic, no self-repair-cap logic, no panel-merge logic lives here). State + render shape are owned by `.devforge/lib/fix_helper` and `.devforge/lib/implement_helper`; the orchestrator composes values via verb subcommands and dispatches the implementing agent + the four review-panel agents.

**`/devforge:fix` never invents a defect.** It consumes findings that were WRITTEN somewhere before this run started: pipeline-produced findings (`specs/[feature]/review.md`, `specs/[feature]/verification.md` NEEDS-WORK issues), a single user-raised + code-confirmed in-window defect, or one `bugs/NNN-<slug>.md` file handed to it by path. It does NOT accept a free-text "describe a bug" input — there is no argument form and no prompt that turns a typed description into a working-list item, and a bug the user merely describes in conversation goes to `/devforge:report-bug` first so that a written record exists to consume.

**A bug FILE is a written finding; it is NOT a confirmed one.** `/devforge:report-bug` captures without reading any source, so a `bugs/` file records what someone believed, not what the code does. The cold lane therefore CONFIRMS the bug against live code before remediating anything, and stops when it cannot (PHASE 0.4).

**One `bugs/` write exists, and only in the cold lane.** After a cold run's hard gate approves and the commit lands, the ONE bug file passed as the argument is flipped to `Fixed`. `/devforge:fix` creates no `bugs/` file, touches no other `bugs/` file, and writes no `bugs/` file at all in the feature lane — run `/devforge:report-bug` to file a bug, which is both the "defer" arm of the offer and the way a cold bug becomes remediable in the first place.

Usage: `/devforge:fix` (auto-resolve the most-recently-modified `specs/NNN-*` feature) · `/devforge:fix specs/001-auth` or `/devforge:fix specs/001-auth/spec.md` (an explicit feature dir or a spec file inside it) · `/devforge:fix bugs/007-null-cart-total.md` (the cold lane — one already-filed bug, no feature).

## Maintainer note

This file lives at `src/commands/fix/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/devforge:fix` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.devforge/command-refs/fix/<file>.md` at install time.

## Outputs of this command

`/devforge:fix` writes NO report file of its own. Its durable outputs differ by lane, and **a run either bounces at PHASE 1 or runs through to PHASE 6 — never both.**

**Feature lane** — at most ONE of:

- A `[WIP] fix: <title>` commit (standalone) or `[TICKET-ID] - <title>` commit (wrapper mode, ticket derived from the source branch), written by `implement_helper wip-commit` in task-less mode (PHASE 6) carrying the remediation diff. This is the same output `/devforge:implement` produces per approved task. WIP commits accumulate and are squashed by `/devforge:finalize`.
- `specs/[feature]/fix-seed.json` — a backward re-entry seed (`source="fix"`, `target_stage="spec"`), written by `fix_helper write-seed` in PHASE 1 and WIP-committed alongside via `artifact_helper commit-artifacts`. It is written ONLY on the scope-change bounce's matching pick (PHASE 1's `re-enter specify` arm); every other pick, and every run that reaches PHASE 2, writes no seed. `/devforge:specify` detects and consumes it on its next run.

**Cold lane** — on a completed run, BOTH of:

- A clean `fix(<scope>): <title>` commit (standalone) or `[TICKET-ID] - <title>` commit (wrapper mode) carrying the remediation diff, written by `implement_helper wip-commit --final` (PHASE 6). **No `[WIP]` prefix in standalone**, because no `/devforge:finalize` run will ever squash a cold-lane commit — there is no feature to finalize.
- The consumed `bugs/NNN-<slug>.md` flipped to `**Status**: Fixed` with its `**Fixed**:` date and `## Fix Notes` filled, written by `fix_helper close-bug` (PHASE 6). In standalone this rides the same commit; in wrapper mode it gets its own install-repo commit. **On a cold bounce at PHASE 1 the run writes NEITHER** — no commit, no seed, and the bug file stays `Open`.

`/devforge:fix` does NOT write `specs/[feature]/*.md`, does NOT mutate the spec or the task files, and does NOT CREATE any `bugs/` file. Its only `bugs/` write is the cold lane's single flip above, on the one file it was handed. The feature's `review.md` / `verification.md` (its inputs) are read-only here. Re-verifying the remediated diff is `/devforge:verify`'s job (PHASE 7 points there — feature lane only; a cold run has no acceptance criteria to re-prove).

### Intermediate scratch files (orchestrator-written, helper-consumed) — all under `$WORKDIR`

The helper cannot dispatch agents (a subprocess has no Task/MCP tools), so the orchestrator captures each verb's stdout to an intermediate scratch file that the next verb reads. All live under `$WORKDIR` (`${TMPDIR:-/tmp}/forge-fix`) and are scratch state for one run — the whole directory is removed by the single Cleanup `rm -rf "$WORKDIR"`. Because `$WORKDIR` is outside the work tree, the files need no leading dot and no gitignore handling.

- `$WORKDIR/preflight.json` — the `preflight` stdout (`source_root`, `framework`, `language`, `wrapper_mode`, `setup_chain_ok`, …). Written in PHASE 0, read by the orchestrator for the `source_root` / `wrapper_mode` values it threads forward.
- `$WORKDIR/findings.json` — the `read-findings` stdout (`items`, `sources`). Written in PHASE 0 **on the FEATURE lane only**; a cold run never calls `read-findings` and this file never exists there. Read by the orchestrator to triage (PHASE 1) and passed to `resolve-scope --items` (PHASE 1).
- `$WORKDIR/items.json` — the working list as a bare JSON ARRAY, passed to `resolve-scope --items` (which takes a file PATH containing it). On the FEATURE lane it is the `items` array extracted from `$WORKDIR/findings.json`, plus any conversational item the orchestrator appends, written in PHASE 1. On the COLD lane it is written directly in PHASE 0.4 as a one-element array the orchestrator composes itself — there is no `findings.json` to extract from. **Either way this is the file PHASE 1 triages and `resolve-scope` consumes**, so everything downstream is lane-independent.
- `$WORKDIR/scope.json` — the `resolve-scope` stdout (`files`, `file_count`, `empty`). Written in PHASE 1, read by the orchestrator to build the inline `verify-touched --files` JSON-array string.
- `$WORKDIR/mechanical.json` — the `verify-touched` stdout (`status`, `iteration`, `failed_command`, `output`, …). Written + re-written across the PHASE 3 self-repair loop.

The PHASE 4 review panel writes its per-reviewer scratch to `${TMPDIR:-/tmp}/forge-implement-review/` — the SAME path `/devforge:implement` PHASE 6 uses (not under `$WORKDIR/forge-fix`). That directory is the bridge to `merge-review-panel`; the Cleanup block removes it alongside `$WORKDIR`.

## Reference files

- `references/triage.md` — how to triage a working-list item (defect-repair vs feature/architecture change) and the PHASE-1 bounce criteria for BOTH lanes. Read it in full at PHASE 1.

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/fix_helper <verb> ...` (the front half) or `.devforge/lib/implement_helper <verb> ...` (the reused back half). Each verb prints JSON (or a rendered block) to stdout. Verbs that consume a prior verb's output take a `--<name> <path>` flag (not stdin), so capture stdout to the named `$WORKDIR/*.json` scratch file with `>` and pass that path into the next call — the per-phase fences below show the exact redirects. Re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-fix"` at the top of every Bash block that touches scratch (the variable does not survive across Bash calls — see PHASE 0). On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns file structure, validation, and atomic writes; the orchestrator owns the agent dispatch, user-facing prose, and phase pacing.

`/devforge:fix` keeps NO per-feature run state of its own (there is no `check-status-and-flip` verb — `/devforge:fix` has no multi-phase back-half state; the back-half loops are owned by `implement_helper`). So unlike `/devforge:review` and `/devforge:verify`, no phase-boundary state-flip call appears below.

## PHASE 0 — Preflight + lane selection + findings intake

Cheapest guards first; preflight before any feature I/O.

**Lane selection — decide it here, once, and carry it through the run.** Inspect `$ARGUMENTS` after 0.1's preflight passes:

- `$ARGUMENTS` names a path under `bugs/` (a `bugs/NNN-<slug>.md` file) → **the COLD lane**. Skip 0.2 and 0.3's window gate entirely (0.3's scratch-dir block still runs), then take 0.4's cold arm.
- `$ARGUMENTS` does NOT name a path under `bugs/` — it is empty, names a `specs/NNN-*` directory or a file inside one, or is anything else at all → **the FEATURE lane**. Run 0.2, 0.3 and 0.4's feature arm as written. **0.2 is what resolves the argument**, and it is also where an argument that names nothing resolvable is caught and reported.

**These two bullets are a true partition — every possible `$ARGUMENTS` value lands in exactly one of them.** The FEATURE lane is the complement of the cold test, not a second pattern match, so there is no third state and nothing for you to adjudicate: a malformed feature path, a typo'd `bug/007-x.md` (singular, not under `bugs/`), or a bare word is a FEATURE-lane run whose argument 0.2 then fails to resolve — it is NOT a cold run and NOT an error to diagnose here.

The test is the argument's PATH, not its content and not a judgment about how big the bug looks. There is no flag, no severity threshold and no auto-detection: a run is cold because the user pointed it at a file under `bugs/`.

**Three sub-phases do not run on the cold lane — 0.2, 0.3's window gate, and 0.4's `read-findings` call — and the reason is the same for all three: each one needs a feature directory that a cold run does not have.** `fix_helper`'s `in-fix-window` and `read-findings` verbs both REQUIRE a `--feature` argument, so on a cold run there is nothing to pass them; `in-fix-window` in particular would report `no_tasks_dir` and gate the run out by construction. **Do NOT call them anyway and disregard the answer** — a check whose result the instructions tell you to ignore is not a check.

**Why skipping the window gate is correct rather than a loophole.** That gate exists to stop an in-place fix landing inside a SEALED feature unit — one whose WIP commits have already been squashed into a finished feature commit. A cold run is not fixing inside a feature unit at all: it has no feature, writes no `[WIP]` commit, and lands a standalone `fix(<scope>):` commit that belongs to no feature's history. The rule's subject does not exist on this lane. **Everything the gate protects that is about the CODE — verify + self-repair, the four-reviewer panel, the forcing-functions gate, the human hard gate — still runs, unchanged (PHASES 3–6).**

⚠ **One protection is genuinely lost, and it is stated rather than argued away:** the window gate also refuses to run while `/devforge:implement` is mid-flight (its `not_all_tasks_complete` reason). A cold run has no such interlock. `wip-commit --final` does NOT clear `.devforge/wip.md`, so a concurrent `/devforge:implement`'s crash-recovery marker survives a cold run intact — but the two will be editing the same working tree. If the user has an `/devforge:implement` run in progress, say so and suggest finishing it first.

### 0.1 — Preflight gate

```bash
.devforge/lib/fix_helper preflight --workspace-root . > /tmp/fix-preflight-check.json
```

`preflight` checks the 4-command setup chain (`/devforge:init-forge → /devforge:generate-docs → /devforge:configure → /devforge:constitute`) and the populated-constitution guard. It ALWAYS writes its JSON context block to stdout BEFORE any gate check, then exits **2** with a user-facing stderr message when (a) a setup-chain artefact is missing or (b) `constitution.md` is absent or still carries an unpopulated sentinel. On exit 2, copy the helper's stderr VERBATIM as a fenced code block and end the turn — the user runs the named missing command first. On exit 0, the stdout JSON carries `source_root` (the project's Source Root — `.` for a standalone install, the inner project subdir in wrapper mode), `framework`, `language`, and `wrapper_mode`. (`$WORKDIR` is not established until 0.3, so this gate call captures to a fixed `/tmp` path; 0.3 re-runs `preflight` into `$WORKDIR/preflight.json` once the scratch dir exists. `preflight` is read-only and cheap, so running it twice is harmless.) Carry `source_root` and `wrapper_mode` forward: PHASE 2 briefs the implementing agent under the source root, and PHASE 3 passes `source_root` context to the implementing agent during self-repair.

### 0.2 — Resolve the feature directory *(FEATURE lane only — skipped on the cold lane)*

Resolve the feature dir from `$ARGUMENTS`:

- When `$ARGUMENTS` names a feature directory (`specs/NNN-<slug>`) or a file inside one (e.g. `specs/001-auth/spec.md`), use that feature directory (strip a trailing filename to the `specs/NNN-<slug>` dir).
- When `$ARGUMENTS` is empty, auto-resolve the most-recently-modified `specs/NNN-*` directory (the feature most likely just finished `/devforge:review` or `/devforge:verify`).

If no `specs/NNN-*` directory exists, tell the user there is no feature to remediate (run `/devforge:specify` → `/devforge:spec-check` → `/devforge:plan` → `/devforge:grill` → `/devforge:breakdown` → `/devforge:implement` → `/devforge:review` first) and end the turn. Carry the resolved feature dir forward as `<feature>` — every subsequent `--feature` flag takes it, with ONE exception: PHASE 1's `write-seed` call takes the `NNN-<slug>` basename (`<feature-id>`, derived from `<feature>`) via `--feature`, and takes `<feature>` itself via its separate `--feature-dir` flag.

### 0.3 — Window gate *(FEATURE lane only)* + scratch dir *(BOTH lanes)*

**The window gate below is FEATURE-lane only; the scratch-dir block after it runs on BOTH lanes.** On a cold run, skip straight to "Then establish + clear the scratch working directory".

In the feature lane `/devforge:fix` only remediates a feature whose WIP commits are still open — post-`/devforge:implement`, pre-`/devforge:summarize`. Confirm the window before any further work:

```bash
.devforge/lib/fix_helper in-fix-window --feature <feature>
```

`in-fix-window` emits JSON `{in_window, reason}` and uses its EXIT CODE as the gate: **exit 0** = in-window (proceed), **exit 1** = out-of-window. On exit 1 (`reason` is `summary_present` or `spec_complete` → the feature is SEALED; `no_tasks_dir` / `no_task_files` → not yet implemented; `not_all_tasks_complete` → `/devforge:implement` is still mid-flight), STOP: do NOT remediate this feature in place. Report the `reason` to the user so they know which out-of-window state applies, then name the route that fits it:

- **SEALED** (`summary_present` / `spec_complete`) — the feature's artifacts are a finished record and must not be reopened in place. Two routes, and which one fits depends on the fix, not on its size: for a **defect repair**, run `/devforge:report-bug` to file it, then `/devforge:fix bugs/NNN-<slug>.md` to remediate it under the same gates on the cold lane (a fresh standalone commit on top of sealed code — the seal covers the feature's artifacts, not its source files); for a **behavior or architecture change**, start a fresh `/devforge:research` → `/devforge:specify` → … → `/devforge:implement` cycle.
- **`not_all_tasks_complete`** — `/devforge:implement` has not drained the feature. Finish `/devforge:implement` first; do not reach for the cold lane to route around this.
- **`no_tasks_dir` / `no_task_files`** — the feature is not implemented yet, so there is no code to remediate.

Then end the turn. On exit 2 (a `--feature` argument error), copy the helper's stderr VERBATIM as a fenced code block and end the turn.

Then establish + clear the scratch working directory:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"
```

**All intermediate scratch for this run lives in `$WORKDIR` (the fixed literal `${TMPDIR:-/tmp}/forge-fix`), OUTSIDE the repo.** The literal is `forge-fix`, NOT `forge-verify` / `forge-review` / `forge-audit` — those commands may run concurrently, and a shared workdir would corrupt every run. `$WORKDIR` is outside the work tree, so the scratch files need no leading dot, no gitignore handling, and no per-file `rm` list. The `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"` clears any stale scratch from a prior crashed run.

**CRITICAL — `$WORKDIR` is a FIXED LITERAL you re-derive in every Bash block; it does NOT persist across calls.** The orchestrator runs each Bash tool call in a FRESH shell, so shell variables (including `$WORKDIR`) do NOT carry from one Bash call to the next. So every Bash block that touches scratch MUST begin by re-establishing `WORKDIR="${TMPDIR:-/tmp}/forge-fix"` and then reference `"$WORKDIR/..."`. The literal is identical in every block, so each block reconstructs the same directory.

Now re-capture the preflight context into `$WORKDIR` so later blocks can re-read its `source_root` / `wrapper_mode` values (the gate already passed in 0.1; this just persists the context to the scratch dir):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
.devforge/lib/fix_helper preflight --workspace-root . > "$WORKDIR/preflight.json"
```

### 0.4 — Intake the finding

Two arms. **Take the one your lane selected at the top of PHASE 0** — the feature arm calls `read-findings`, the cold arm never does.

#### 0.4a — Feature-lane intake *(FEATURE lane only)*

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
.devforge/lib/fix_helper read-findings --feature <feature> > "$WORKDIR/findings.json"
```

`read-findings` parses `specs/[feature]/review.md` confirmed/contested findings AND the `specs/[feature]/verification.md` NEEDS-WORK issues into ONE working list. (Pass `--source review` or `--source verify` to restrict to one file; the default `both` unions them.) Stdout JSON carries `items` (the working list — each item a `{title, severity, files_cited, evidence, source}` dict) and `sources` (`review` / `verify` found-flags, the `verify_verdict` string, and `review_missing` / `verify_missing`). `read-findings` returns exit 0 even when both files are absent (`items` is `[]`); a non-zero exit is a `--feature` argument error — copy the helper's stderr VERBATIM and end the turn.

**Case-3 conversational defect.** When the `/devforge:fix` invocation followed a user-raised defect that you ALREADY code-confirmed before proposing `/devforge:fix` (not a `/devforge:review`/`/devforge:verify` finding on disk), that confirmed defect IS the working-list item. Carry it as a single item of the same shape — `{title, severity, files_cited, evidence, source: "conversation"}` — with `files_cited` set to the file(s) you read to confirm it and `evidence` set to the verbatim code you quoted. You will append it to the working list in PHASE 1. Do NOT fabricate this item: it exists only when the user pointed out the defect AND you confirmed it from the actual code in this conversation.

**Empty-list STOP.** If `$WORKDIR/findings.json` `items` is `[]` AND no case-3 confirmed defect was supplied, there is nothing to remediate on this lane: tell the user there are no pipeline findings to fix — run `/devforge:review` or `/devforge:verify` first to surface findings. **For a bug noticed independently of this feature**, the route is `/devforge:report-bug` to file it and then `/devforge:fix bugs/NNN-<slug>.md` to remediate it on the cold lane under the same gates. `/devforge:fix` never invents a defect and never accepts a free-text bug description — the bug has to be written down before it can be consumed. Clean up (`rm -rf "$WORKDIR"`) and end the turn. This is not an error — it is an empty working list.

#### 0.4b — Cold-lane intake *(COLD lane only)*

The cold lane reads the bug file, CONFIRMS it against live code, and composes the working list itself. **No helper call reads the bug file** — `read-findings` is feature-bound and is not used here.

**Step 1 — read the bug file.** Read the `bugs/NNN-<slug>.md` path from `$ARGUMENTS` with the Read tool. If it does not exist, tell the user the path was not found (offer `/devforge:report-bug` to file the bug first), clean up and end the turn. Take from it: the title (the `# Bug NNN: <title>` heading), `**Status**`, `**Severity**`, the `## Description` and `## Evidence` bodies, and the `## File(s)` table's paths.

**Step 2 — refuse an already-closed bug.** If `**Status**` is not `Open` or `In Progress`, STOP: tell the user that bug is already recorded as `Fixed` (or carries an unrecognized status) and that re-remediating it needs a fresh `/devforge:report-bug` record. Clean up and end the turn. This is a courtesy check that saves a wasted run — `close-bug` enforces the same rule at PHASE 6 and would reject the flip anyway.

**Step 3 — CONFIRM the bug against live code. This step is mandatory and is not a formality.** The bug file is a CAPTURE: `/devforge:report-bug` wrote it without reading any source, so nothing in it has been checked against the code. Read the cited file(s) — and, when the `## File(s)` table is empty or reads `(unknown)`, search the codebase for the behavior the description names — and establish that the defect is really present in the code as it stands NOW. Quote the offending code verbatim; that quote becomes the working-list item's evidence. A bug filed weeks ago may already have been fixed by unrelated work, may have been described inaccurately, or may describe intended behavior.

**Step 4 — the unconfirmable-bug STOP.** If you cannot locate the defect in live code, **STOP — do not remediate.** Tell the user the bug could not be confirmed against the current code, name exactly which files you read and what you searched for, and suggest `/devforge:research "<the bug's description>"` to investigate it properly. Leave the bug file **untouched and `Open`**. Clean up (`rm -rf "$WORKDIR"`) and end the turn. **Remediating an unlocated defect means editing code on the strength of a prose description, which is exactly the free-text intake this command refuses** — there is no degraded "best effort" arm here.

**Step 5 — compose the working list.** Write a ONE-element JSON array straight to `$WORKDIR/items.json` with the Write tool — same item shape the feature lane uses, so everything downstream is lane-independent:

```json
[
  {
    "title": "<the bug file's title>",
    "severity": "<the bug file's **Severity** value>",
    "files_cited": ["<the file(s) you confirmed the defect in, in step 3>"],
    "evidence": "<the offending code you quoted in step 3>",
    "source": "bug-file"
  }
]
```

`files_cited` is what STEP 3 CONFIRMED, not what the bug file claimed — a bug filed with no `--file`, or naming a path the defect has since moved out of, still yields a correct scope because confirmation supplies it. The `source` value is the literal `bug-file`, distinct from the feature lane's `review` / `verify` / `conversation` values, so the item's origin stays readable downstream.

Carry the bug-file path forward as `<bug-file>` — PHASE 6 passes it to `close-bug`.

**No empty-list STOP applies on this lane:** a cold run either composed exactly one item in step 5 or already stopped at step 1, 2 or 4.

## PHASE 1 — Triage + scope-estimate (the scope bounce)

Read `references/triage.md` in full now — it carries the defect-repair-vs-change classification and the bounce criteria for both lanes.

**Triage the working list. Where that list came from depends on the lane, and NOTHING else in this phase does:**

- **FEATURE lane** — the `items` from `$WORKDIR/findings.json`, plus the case-3 item if one was supplied.
- **COLD lane** — the single item already written to `$WORKDIR/items.json` at 0.4b. There is no `findings.json` on this lane; do not read one.

For each item, classify it per `references/triage.md`: a **defect repair** (the code is wrong against its own intent — a logic bug, a missing case, a contract violation, a security hole) stays in `/devforge:fix`; a **feature/architecture change** (the fix would add behavior, change a data model, introduce a dependency, or restructure a layer — i.e. it changes WHAT the system does, not just whether it does it correctly) does NOT belong in `/devforge:fix`. **The classification is IDENTICAL on both lanes** — same table, same discriminator. What differs is only where a bounced item is sent.

**The scope-escalation bounce — FEATURE lane.** If ANY working-list item would require a feature/architecture change rather than a defect repair, STOP and recommend `/devforge:specify`: tell the user the item is not a defect repair but a scope change — naming WHICH item and WHY, per `references/triage.md` — so it belongs in a fresh `/devforge:specify` → `/devforge:spec-check` → `/devforge:plan` → `/devforge:grill` → `/devforge:breakdown` cycle, not in a gated in-place fix. `/devforge:fix` remediates known defects with `/devforge:implement`'s gates; it does not grow the feature. Do NOT partially remediate.

**The scope-escalation bounce — COLD lane. It names a DIFFERENT command, and the difference is mechanical rather than stylistic.** If the bug triages as a feature/architecture change, STOP and recommend **`/devforge:research`** — naming WHICH aspect of the bug makes it a change rather than a repair, per `references/triage.md`. The chain starts at `/devforge:research` and not at `/devforge:specify` because **`/devforge:specify` blocks until a pending research or discover handoff exists in a feature directory**, and a cold bug has neither; recommending `/devforge:specify` here would name a command that refuses to run. Tell the user the bug needs the full chain from `/devforge:research "<the bug's description>"`, which allocates the feature directory `/devforge:specify` then resolves.

On this bounce:

- **Write NO re-entry seed.** A `fix-seed.json` is written into a feature directory, and a cold run has none — there is nowhere for it to live and no consumer that would find it. The naming duty above is therefore the WHOLE record: state the item and the reason in your message to the user, because nothing persists it.
- **Leave the bug file `Open` and otherwise byte-unchanged.** Do NOT flip it, do not annotate it, do not mark it `In Progress` — the bug is not being worked, and a status the framework cannot keep true is worse than one it does not set.
- Ask no question — the cold lane's bounce has one route, so there is nothing to choose. Clean up (`rm -rf "$WORKDIR"`) and end the turn.

`/devforge:spec-check` sits inside that recommended cycle because `/devforge:plan` blocks until a `spec-check.md` exists beside the resolved spec whose recorded spec hash still matches `spec.md`, and re-entering at `/devforge:specify` rewrites `spec.md` — which stales any prior report by construction. `/devforge:grill` sits there for the same reason one stage later: `/devforge:breakdown` blocks until a `grill.md` exists beside the resolved plan whose adversary run completed. Both are human-typed only, so name them for the user rather than running them.

**The rest of this bounce section is FEATURE-lane only** — the question, the seed and its commit. A cold bounce already ended the turn above.

The naming duty above is NOT discharged by the seed below — the seed RECORDS that duty's output, it does not replace it. Having named the item(s) and the reason, ask ONE `AskUserQuestion` to capture who owns the scope change:

- Question: `"<named item> is a scope change, not a defect repair — how do you want to handle it?"` — single-line text; the explanation lives in the option `description` fields.
- Options: `["re-enter specify", "drop and re-run", "stop"]`. Option 1 is the matching arm — the one this bounce already recommends — and is marked `(recommended)`. (Exactly three authored options: `AskUserQuestion` auto-injects an "Other" row, so never author one.)

End the turn. The user's reply opens the next turn.

- **`re-enter specify`** → the matching arm, and the ONLY arm that writes a seed. Follow "Seed write + commit" below.
- **`drop and re-run`** → `references/triage.md`'s first mixed-list path. Write NO seed. Tell the user to drop the named scope-change item(s) from consideration and re-run `/devforge:fix`, which then remediates the defect-only remainder. End the turn.
- **`stop`** → write NO seed and record nothing. End the turn.

An "Other" answer, and any reply that does not select `re-enter specify`, writes NO seed. This verdict-gating is why the seed is not written at the bounce itself: `/devforge:specify` treats a seed as a binding directive for its run, so an unratified one becomes an orphan a later run silently obeys.

**Seed write + commit (the `re-enter specify` arm only).** Compose the seed inputs from material the bounce has already produced — the mapping is fixed, so two runs on the same bounce compose the same seed:

- `--feature` — the feature id: the `NNN-<slug>` basename of the `<feature>` dir resolved in 0.2.
- `--feature-dir` — the resolved `<feature>` dir itself.
- `--prior-conclusion` — the bounced item's conclusion/claim as written in the working list.
- `--invalidating-evidence` — when the item came from a written finding (`specs/[feature]/review.md` or `specs/[feature]/verification.md`), QUOTE that finding's own `evidence` string, plus the one-line triage classification reason. The bare classification judgment alone is permitted ONLY for a case-3 conversational defect, which has no written finding to quote.
- `--must-satisfy` — what the fresh `/devforge:specify` cycle must resolve: the scope change, named.
- `--provenance` — the report file the item came from (`specs/[feature]/review.md` or `specs/[feature]/verification.md`); for a case-3 conversational defect, the literal string `conversational (in-window user report; no report file)`.
- `--cycle-count` — before composing, check whether `<feature>/fix-seed.json` ALREADY exists (a prior bounce on this same feature). If it does, read that file's `cycle_count` and pass it plus one; otherwise omit the flag (default `1`). There is no cap logic on this path.
- `--carried-findings` — a JSON array string; omit it for a single-item bounce.

**Multi-item bounce.** When SEVERAL working-list items EACH independently triage as a scope change, write ONE seed, never one per item — `fix-seed.json` is a fixed filename, so a second write would overwrite the first. The three flat strings (`--prior-conclusion`, `--invalidating-evidence`, `--must-satisfy`) SYNTHESIZE across the items, and each item's own per-item reasoning goes into `--carried-findings` as one array element per item. The AskUserQuestion's single-line question names ALL triggering items in that case, not just one. (This is a different case from the mixed working list `references/triage.md` covers — that one is a single scope change sitting among defect repairs.)

```bash
.devforge/lib/fix_helper write-seed --feature <feature-id> --feature-dir <feature> --prior-conclusion "<the bounced item's conclusion as written>" --invalidating-evidence "<the finding's quoted evidence + the one-line classification reason>" --must-satisfy "<the scope change the /devforge:specify cycle must resolve>" --provenance "<feature>/review.md"
```

`write-seed` builds a `ReEntrySeed` (`source="fix"`, `target_stage="spec"`, both fixed INTERNALLY — there is no `--target-stage` flag, because the bounce has exactly one backward direction) and writes `<feature>/fix-seed.json` via an atomic write, OVERWRITING any prior `fix-seed.json`. `--feature`, `--feature-dir`, `--prior-conclusion`, `--invalidating-evidence`, `--must-satisfy`, and `--provenance` are all REQUIRED and non-empty (a missing or empty value exits **2**); `--cycle-count` (an int ≥ 1) and `--carried-findings` (a JSON array string) default to `1` and `[]` and may be omitted. Stdout is a JSON ack `{"seed_path"}`. On a non-zero exit, copy the helper's stderr VERBATIM as a fenced code block and end the turn — no seed was written.

Then WIP-commit the seed so it is git-safe:

```bash
.devforge/lib/artifact_helper commit-artifacts --paths '["<feature>/fix-seed.json"]' --label 'fix-seed: <feature-id>'
```

Substitute `<feature>` with the resolved feature dir (e.g. `specs/001-auth`) and `<feature-id>` with its basename (e.g. `001-auth`). `commit-artifacts` stages ONLY the named path and makes a `[WIP] fix-seed: <feature-id>` commit in the INSTALL repo (never the wrapper-mode source/product repo). The label is `fix-seed:`, NOT `fix:` — `implement_helper wip-commit` already owns `[WIP] fix: <title>` for the remediation diff (PHASE 6), and the two must stay distinguishable in the log. `commit-artifacts` is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the seed is already written, so note the warning and CONTINUE to the closing message below; do NOT end the turn on it); "nothing to commit" exits 0 silently as a benign no-op. The `[WIP]` commit folds into `/devforge:finalize`'s squash, leaving the final PR unchanged.

Then end the turn, telling the user: that `<feature>/fix-seed.json` was written (the ack's `seed_path`); that the recommended next cycle is `/devforge:specify` → `/devforge:spec-check` → `/devforge:plan` → `/devforge:grill` → `/devforge:breakdown`; and that `/devforge:specify` will detect and consume the seed on its next run, so the re-run is directed at the named scope change instead of re-deriving the spec. `/devforge:fix` never runs `/devforge:specify` itself — name the command and let the user start the cycle.

**No bounce — every item is a defect repair.** When NO working-list item triaged as a feature/architecture change, the bounce above does not fire at all: no question is asked and no seed is written. Resolve the narrow touched-file set instead. **`resolve-scope` reads `$WORKDIR/items.json` on BOTH lanes** — only how that file got there differs:

- **COLD lane** — `$WORKDIR/items.json` was already written at 0.4b. **Skip the extraction line below entirely** (there is no `findings.json` to read; running it would fail) and call `resolve-scope` directly.
- **FEATURE lane** — extract the `items` array to its own file first, appending the case-3 item if one was supplied:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
# FEATURE lane only — extract the working list. When a case-3 item was supplied,
# append it here (write the combined array yourself with the Write tool instead
# of this line). On the COLD lane items.json already exists; skip this line.
python3 -c "import json; json.dump(json.load(open('$WORKDIR/findings.json'))['items'], open('$WORKDIR/items.json','w'))"
```

Then, on BOTH lanes, map the working list to the file set:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
.devforge/lib/fix_helper resolve-scope --items "$WORKDIR/items.json" > "$WORKDIR/scope.json"
```

`resolve-scope` takes the working list as a file PATH (`--items`; pass `-` to read stdin) and emits JSON `{files, file_count, empty}` — `files` is the deduplicated, sorted union of every path cited across the working-list items (the NARROW finding-targeted set, NOT the assembled-feature diff — that is `/devforge:verify`'s scope). On a non-zero exit (unreadable `--items`, invalid JSON, or a non-list), copy the helper's stderr VERBATIM and end the turn.

**Empty-scope guard.** If `scope.json` `empty` is `true` (the findings cited no files), the remediation has no file target to verify against. Tell the user the findings name no files to fix (so `/devforge:fix` cannot scope a verify gate) and that the finding(s) need a file citation — point them back to the `/devforge:review` / `/devforge:verify` report to add the missing location, or hand-fix. Clean up and end the turn. (**On the cold lane this guard should be unreachable**: 0.4b step 5 fills `files_cited` from the files confirmation actually READ, and a run that could not locate the defect already stopped at step 4. If it fires anyway, the cold item was composed without its confirmed files — go back and fix that rather than proceeding.)

Carry the `files` array forward — it is the inline JSON-array STRING the `verify-touched --files` argument takes in PHASE 3.

## PHASE 2 — Dispatch the implementing agent at the finding

Pick the implementing agent per the file-layer → agent mapping (the same mapping `/devforge:breakdown` uses — a file's package/layer determines its owning stack's implementer). **Architect guard:** the architect is a director and cannot write implementation code (per `.claude/agents/architect.md` Rule 1; its charter is to refuse-and-route coding work back to the owning stack's implementer). NEVER dispatch `architect` to remediate. If the finding spans multiple layers, split the remediation across the owning implementers (one agent per layer's files) rather than handing the whole thing to the architect; if no owning implementer agent is installed for a finding's layer, HALT and escalate to the human (re-run `install.sh`, which regenerates every agent and also overwrites `.claude/settings.json`, or hand-copy the missing agent file into `.claude/agents/`, or hand-fix) — never fall back to `architect`.

Brief the chosen agent with COMPLETE context — it sees only what you brief it with. The brief MUST carry:

- **The finding(s)** it is remediating — the `title`, `severity`, and `evidence` of each working-list item assigned to this agent.
- **The cited files** — the `files_cited` for those items (source-rooted: `<source_root>/<path>` in wrapper mode, repo-relative in standalone), as the scope constraint.
- **The constitution rules** (`constitution.md`) and the known pitfalls — the entries from `memory_excerpt` that bear on the cited files. Alongside the fields 0.1 names, the `preflight` stdout re-captured at `$WORKDIR/preflight.json` carries `memory_present` (bool) and `memory_excerpt` (the populated `## ` sections of `.devforge/memory.md`, the project's persistent cross-session lessons file, with `## Task Outcomes` excluded and every section that has no entries under its heading dropped); read the excerpt from that file and select from it, so the remediation does not re-introduce a defect a past session already recorded — a fix that trips a known pitfall is a second finding, not a fix. A memory entry is an UNVERIFIED prior-session assertion, not a specification: it CONSTRAINS the remediation, it never redefines it — the finding is what the agent is fixing, and the scope rule below still binds. When `memory_present` is false or `memory_excerpt` is empty — the shipped stub carries no entries under its headings, so it renders as an empty excerpt — pass the constitution rules alone and say nothing to the user about memory; a project with no recorded lessons is the ordinary state of a fresh install, not a fault to remedy.
- **An explicit scope rule:** "Remediate ONLY the cited defect(s) — make the minimal change that fixes the finding; do not modify unrelated code, do not add features, do not refactor beyond the fix." A remediation that grows the change beyond the finding is itself a finding the PHASE 4 panel will flag.

The agent edits SOURCE files and writes its edits into the working tree; nothing is committed yet. In wrapper mode, state explicitly that the agent must NOT write forge artifacts (`.claude/`, `specs/`, `CLAUDE.md`, `constitution.md`, `bugs/`, …) into the source tree — those live at the install root, and PHASE 3's wrapper-isolation check fails the run if any appear inside the source root. In standalone mode the single repo legitimately contains those artifacts, so the isolation rule is moot.

## PHASE 3 — Scope-aware verify + self-repair

Run scope-aware verification over the remediated files, looping self-repair EXACTLY as `/devforge:implement` PHASE 5. `/devforge:fix` is a write-path command, so it REPAIRS (unlike `/devforge:verify`, which calls `verify-touched` report-only). Pass the `files` array from PHASE 1's `scope.json` as an inline JSON-array STRING and start the iteration counter at 0:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
FILES_JSON="$(python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/scope.json'))['files']))")"
.devforge/lib/implement_helper verify-touched --files "$FILES_JSON" --root . --iteration 0 > "$WORKDIR/mechanical.json"
```

`verify-touched` (the helper, not this spec) matches each file to its package via `PACKAGE_STACKS`, runs that package's static checks (type-check + lint) → build → tests with `cwd = <source_root>`, and owns the self-repair cap (3) — the orchestrator cannot extend it. It emits JSON with a top-level `status` field. Handle EACH status exactly as `/devforge:implement` PHASE 5 does:

- **`{"status": "pass", ...}`** (exit 0) → verification passed. Proceed to PHASE 4.
- **`{"status": "self_repair", ...}`** (exit 0) → a command failed and the cap is not yet reached. The object carries `iteration` (`N`), `failed_command`, and `output`. Relaunch the **same implementing agent** from PHASE 2 with the `failed_command` and `output` so it can fix the failure, then re-call `verify-touched` with `--iteration` set to `N + 1`. Repeat this autonomous self-repair leg — no human between iterations.
- **`{"status": "failed", ...}`** (exit 2) → the self-repair cap was reached; the remediation is blocked. Copy the helper's stdout VERBATIM into a fenced code block, then STOP and tell the user the fix could not be made to pass verification within the self-repair cap — they can repair manually with more direction and re-run `/devforge:fix`, or take the finding through the full chain. Clean up and end the turn (nothing has been committed).
- **`{"status": "isolation_failure", "artifacts": [...]}`** (exit 2, wrapper mode only) → the agent polluted the source tree with forge artifacts (the `artifacts` array lists the offending paths). Copy the helper's stdout VERBATIM, then instruct the implementing agent to REMOVE the misplaced artifacts from the source tree and re-run this PHASE-3 verify from `--iteration 0`. (Standalone never emits this status.)
- **`{"status": "tooling_unavailable", "failed_command": "...", "output": "..."}`** (exit 2) → a configured type-check, lint, or test command could not be executed (a missing binary or misconfigured command). This is a tooling/config problem, not a code error, and it is not self-repairable. Copy the helper's stdout VERBATIM, then STOP and tell the user to correct the configured command (owned by `/devforge:configure`) or install the missing tool, then re-run `/devforge:fix`. Clean up and end the turn. (`/devforge:fix` has no `scope-and-approve` path — unlike `/devforge:implement`, it does not own a per-task hard gate that can scope-and-approve unverified boxes; a fix that cannot be mechanically verified does not land.)

Exit 1 (missing/malformed `project-config.json`) — copy the helper's stderr VERBATIM into a fenced code block, then end the turn.

## PHASE 4 — Four-reviewer panel

After verify passes, run the bounded autonomous review-panel loop EXACTLY as `/devforge:implement` PHASE 6 — a panel of FOUR read-only reviewers (`code-reviewer`, `qa-reviewer`, `security-reviewer`, `performance-analyst`) ⇄ the implementing agent, ≤3 rounds (the helper-owned counter), NO human between rounds. The loop converges to a panel-clean verdict (every reviewer clean). All four reviewers are read-only and tools-locked (`Read, Grep, Glob, Bash`; no `Edit`/`Write`/`Agent`), so a parallel fan-out is safe and the only writer is the implementing agent during a repair leg.

Start the loop iteration counter at 0 and run:

1. **Fan out the four reviewers in parallel.** In ONE turn, dispatch `code-reviewer`, `qa-reviewer`, `security-reviewer`, and `performance-analyst` via the Task tool — four Task calls in the same turn, each with `subagent_type: <agent>` (which loads that reviewer's persona from `.claude/agents/<agent>.md`; do NOT re-inline the persona). Give EACH the same inputs: the remediated `files` (PHASE 1's scope), the constitution, and the finding(s) being remediated. The four results return UNORDERED, so key each returned markdown to the agent you dispatched it to. Each reviewer returns a markdown verdict carrying a `### Verdict:` line in its own vocabulary (`code-reviewer`: `APPROVE` / `REQUEST CHANGES` / `BLOCK`; `qa-reviewer`: `ADEQUATE` / `GAPS FOUND`; `security-reviewer`: `PASS` / `FAIL`; `performance-analyst`: `MEETS TARGETS` / `BOTTLENECKS FOUND`).
2. **Write each reviewer's returned markdown to a run-scoped scratch file** — write each with the Write tool to `${TMPDIR:-/tmp}/forge-implement-review/<agent>.md` (one file per reviewer, named for the agent). This is the SAME scratch path `/devforge:implement` PHASE 6 uses — reuse it unchanged. A bash subprocess cannot read a subagent's return value, so these files are the bridge to the merge helper.
3. **Merge the four verdicts** via the helper, passing the current iteration `N` and one `--reviewer <agent>:<path>` per reviewer (the path written in step 2):

   ```bash
   .devforge/lib/implement_helper merge-review-panel --iteration N --reviewer code-reviewer:<path> --reviewer qa-reviewer:<path> --reviewer security-reviewer:<path> --reviewer performance-analyst:<path>
   ```

   The helper parses each reviewer's `### Verdict:` line against that reviewer's vocabulary and emits JSON `{clean, escalate, iteration, per_reviewer}` (exit 0). `clean` is `true` IFF EVERY reviewer returned its own clean token (`code-reviewer` `APPROVE`, `qa-reviewer` `ADEQUATE`, `security-reviewer` `PASS`, `performance-analyst` `MEETS TARGETS`); one dirty reviewer keeps the loop going. `escalate` is `true` when `N >= 3` (the helper-owned cap). Exit 2 means one reviewer's verdict line was missing, was the unfilled template, or carried a token outside that reviewer's vocabulary — copy the helper's stderr VERBATIM (it names WHICH reviewer failed), then re-invoke ONLY that named reviewer for a properly-formed verdict, rewrite its scratch file, and re-run `merge-review-panel`.
4. Branch on the JSON:
   - **`clean: true`** → exit the panel loop. Carry any reviewer warnings into PHASE 6 Stage B. Proceed to the forcing-functions gate (PHASE 5).
   - **`clean: false` and `escalate: false`** → the autonomous repair leg (no human). Synthesize ALL findings across the four reviewers into ONE implementing-agent repair brief, relaunch the **implementing agent** ONCE with the synthesized findings, then re-run PHASE 3 (verify) over the same scope and **re-fan-out the FULL panel** (all four reviewers) at iteration `N + 1`. Full-panel re-review each round closes the cross-file-regression hole a repair could open.
   - **`clean: false` and `escalate: true`** → the cap was reached without converging. The remediation is blocked: STOP and tell the user the review panel could not be brought clean within the cap, surfacing the unresolved reviewer objection(s). They can repair manually with more direction and re-run `/devforge:fix`, or take the finding through the full chain. Clean up and end the turn (nothing has been committed).

## PHASE 5 — Forcing-functions gate

After the panel exits clean, run the constitution forcing-functions gate via the helper, exactly as `/devforge:implement` PHASE 6 tail:

```bash
.devforge/lib/implement_helper run-forcing-functions-gate
```

The helper reads the `forcing_functions` block from `.devforge/constitute.json` and invokes `constitute_helper verify-<rule>` for each enabled rule (`verify-magic-enum`, `verify-cross-layer-imports`, `verify-any-leak`). It emits JSON `{gate, rules_run, rules_failed, reports, aggregate_exit}` on stdout.

- **exit 0** → no enabled rule failed (or no rules are enabled). Proceed to PHASE 6.
- **exit 2** → one or more rules failed; the remediation is gate-blocked. Copy the helper's stdout JSON VERBATIM into a fenced code block (the stdout report carries the per-rule findings, NOT stderr). Then either send the implementing agent back to fix the flagged rule break and re-run PHASE 3 → PHASE 4 → PHASE 5, or STOP if it cannot be brought clean (nothing has been committed; clean up and end the turn).
- **exit 1** → config I/O or parse error (malformed `.devforge/constitute.json`, or an enabled rule with no known verb). Copy the helper's stderr VERBATIM into a fenced code block, then end the turn.

## PHASE 6 — Two-stage hard gate + commit

This is the human gate, run EXACTLY as `/devforge:implement` PHASE 7 — **no content has been committed at this point** (the remediation sits in the working tree). Stage A surfaces any judgment-level calls the panel recorded one at a time (skipped when none), then Stage B always presents the diff for the final code read. The `approve` gate is reachable ONLY from a fully-clean panel (PHASE 4 `clean: true`) AND a passing forcing-functions gate (PHASE 5 exit 0) — there is no path that commits an open finding.

### Stage A — Decision questions (run ONLY if PHASE 4 recorded ≥1 judgment-level call)

For EACH recorded judgment item, ask ONE `AskUserQuestion` — sequentially, never batched; the question is a single line, the explanation lives in the option `description` fields. Option 1 is ALWAYS the agent's resolution, marked `(recommended)`. Choosing an alternative or `let me specify` is treated as a repair: relaunch the implementing agent with the chosen direction, re-run PHASE 3 (verify) → PHASE 4 (panel) → PHASE 5 (forcing-functions), and restart Stage A. `stop` keeps the working tree and ends the turn. Most remediations record zero judgment items → Stage A is skipped.

### Stage B — Final code read (ALWAYS)

Present the ready diff and the verification results. Show `git diff --stat` and the `git diff` (for a large diff, bound it: show `--stat` in full plus the diff for the highest-impact files, and tell the user the full diff is available on request). Summarize the PHASE 3 verify result, the PHASE 4 panel verdict (the four reviewers' clean verdicts plus any carried warnings), and the PHASE 5 forcing-functions result.

Then ask via `AskUserQuestion`:

- Question: `"Approve fix for <feature> — <short finding summary>?"` — single-line text.
- Options: `["approve", "repair", "stop"]`. (No `skip` — `/devforge:fix` remediates a chosen finding set; there is no "advance to the next task" to skip to. To abandon the remediation, use `stop`.)

End the turn. The user's reply opens the next turn.

- **`approve`** → commit the approved remediation (the remediated `files` from PHASE 1's scope, staged precisely — never `git add -A`). **The call differs by lane; take your lane's block.**

  **FEATURE lane — the `[WIP]` commit:**

  ```bash
  WORKDIR="${TMPDIR:-/tmp}/forge-fix"
  .devforge/lib/implement_helper wip-commit --files "$(python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/scope.json'))['files']))")" --title "<short finding summary>"
  ```

  This is `wip-commit`'s **task-less mode** — `/devforge:fix` passes ONLY `--files` and `--title`, omitting `--task-file`/`--index`/`--number` (which are optional; when absent, the verb stages only the touched files and writes a fix-shaped message). The commit lands as a `[WIP] fix: <title>` commit in standalone mode, or a `[TICKET-ID] - <title>` commit on the source branch in wrapper mode. It never uses `git add -A` — in standalone mode it stages ONLY the touched `--files` in the single repo (no task file, no index); in wrapper mode it stages ONLY the source `touched_files` to the source repo on its branch (deriving the `[TICKET-ID]` from the source branch and SUPPRESSING attribution). It composes the message per the wrapper/non-wrapper convention (reading `WORKSPACE_MODE` + `COMMIT_ATTRIBUTION` from `.devforge/project-config.json`), commits, captures the new source HEAD SHA, and clears `.devforge/wip.md` (exit 0 → `{"committed": true, head_sha, message}`). Exit 1 (missing/malformed config, non-JSON or non-array `--files`, missing `--title`, or config/I/O error); exit 2 (git staging/commit failure — including an empty `--files '[]'`, which stages nothing and fails the commit) — copy the helper's stderr VERBATIM into a fenced code block and resolve before re-running. (`/devforge:implement` PHASE 7 still passes all of `--task-file`/`--index`/`--number` and is unaffected by this mode — its behavior is unchanged.)

  **COLD lane — the final commit plus the bug-file flip.** A cold run ends in ONE clean `fix(<scope>): <title>` commit rather than a `[WIP]` one, because **no `/devforge:finalize` run will ever squash it** — there is no feature to finalize, so a `[WIP]` prefix would promise a squash that never comes. Compose two values first:

  - `<scope>` — the Conventional-Commits scope: the area the fix touches, derived from the remediated files (e.g. `cart`, `auth`, `api`). Keep it one short lowercase token.
  - `<title>` — a short imperative description of the fix. `<scope>` and `<title>` together become the commit subject `fix(<scope>): <title>`.

  **The ORDER of the two calls differs by workspace mode, and the difference is forced by which repo the code commit lands in. Do not average the two.**

  **Cold lane, STANDALONE** — the bug file and the code live in the same repo, so the flip rides the SAME commit. Call `close-bug` FIRST, then commit both together:

  ```bash
  .devforge/lib/fix_helper close-bug --bug-file <bug-file> --date "$(date +%Y-%m-%d)" --fix-notes "root cause; what changed; commit subject: fix(<scope>): <title>"
  ```

  ```bash
  WORKDIR="${TMPDIR:-/tmp}/forge-fix"
  .devforge/lib/implement_helper wip-commit --files "$(python3 -c "import json,sys; f=json.load(open('$WORKDIR/scope.json'))['files']; f.append('<bug-file>'); print(json.dumps(f))")" --title "<title>" --final --scope "<scope>"
  ```

  **The fix notes carry the commit SUBJECT LINE, never a SHA, in this mode** — the bug file is inside the commit that mints the SHA, so a SHA cannot be written into it beforehand. The subject line is the durable, checkable reference.

  ⚠ **If `wip-commit --final` fails here, the bug file is ALREADY flipped to `Fixed` on disk but uncommitted.** That is not a clean rollback point: do NOT discard the working tree, do NOT re-run `close-bug` (it will exit 2 — the file is no longer `Open` and its fix notes are no longer the placeholder). Copy the helper's stderr VERBATIM, resolve the commit failure, and re-run ONLY the `wip-commit --final` call. The remediation, the flip and the staging list are all still intact in the tree.

  **Cold lane, WRAPPER** — the code commit lands in the SOURCE repo while `bugs/` lives at the install root, which is a different repo. Staging the bug path into the source-repo commit would fail, and would write a forge artifact into the product repo. So commit the code FIRST, then flip, then commit the flip separately:

  ```bash
  WORKDIR="${TMPDIR:-/tmp}/forge-fix"
  .devforge/lib/implement_helper wip-commit --files "$(python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/scope.json'))['files']))")" --title "<title>" --final --scope "<scope>"
  ```

  ```bash
  .devforge/lib/fix_helper close-bug --bug-file <bug-file> --date "$(date +%Y-%m-%d)" --fix-notes "root cause; what changed; source commit: <head_sha from the wip-commit ack>"
  ```

  ```bash
  .devforge/lib/artifact_helper commit-artifacts --paths '["<bug-file>"]' --label 'bug closed: <bug-file basename>'
  ```

  **In wrapper mode the fix notes DO carry the returned SHA** — the code commit already landed, so `wip-commit`'s `head_sha` is available to write down. The flip's own commit lands in the INSTALL repo under `commit-artifacts`' `[WIP] ` label prefix; that prefix is accepted here (it is bookkeeping in the install repo, and adding a second commit composer for it would duplicate machinery this spec deliberately does not own). `commit-artifacts` is FAIL-SOFT: a staging or commit failure warns on stderr and exits 1 — the flip is already written to disk, so note the warning and CONTINUE to PHASE 7 rather than ending the turn.

  **`--final` contract (both modes).** `--scope` is REQUIRED with `--final` and REJECTED without it; `--final` may not be combined with `--task-file`/`--index`/`--number`. Any of those exits **1** with a stderr message naming the problem. Standalone subject: `fix(<scope>): <title>`. Wrapper subject: `[TICKET-ID] - <title>`, ticket derived from the source branch exactly as in the other modes — **including the fallback of using the full branch name when the branch carries no `PROJ-123`-style token**, so a cold fix on `develop` reads `[develop] - <title>`. That is expected, not a defect. Staging stays `--files`-only per-path, never `git add -A`. **`--final` does NOT clear `.devforge/wip.md`** — a cold run wrote no marker, and clearing one it did not write would destroy another command's crash-recovery state. Exit 2 is a git staging/commit failure (including an empty `--files '[]'`); copy stderr VERBATIM and resolve before re-running.

  **`close-bug` contract.** `--bug-file`, `--date` and `--fix-notes` are ALL required and non-empty. YOU supply the date in `YYYY-MM-DD` form — the helper never calls the clock. It mutates exactly three fields of that one file — `**Status**: Open | In Progress` → `Fixed`, the empty `**Fixed**:` line → `--date`, and the `## Fix Notes` placeholder body → `--fix-notes` — and preserves every other byte. Stdout on success is `{"closed": true, "bug_file": "<path>"}`. It exits **2**, **writing nothing**, when: an argument is missing or empty; the file does not exist; the file's `**Status**` is not `Open` or `In Progress`; the file has no `**Status**:` or `**Fixed**:` line; or **the `## Fix Notes` body is no longer the placeholder** — meaning someone already wrote real notes there, which are never silently overwritten. On any exit 2, copy the helper's stderr VERBATIM into a fenced code block. **In standalone, an exit 2 means the flip did not happen — do NOT proceed to the commit with a stale bug file; resolve it first.** In wrapper, the code commit has already landed, so report the failure and tell the user the bug file needs a manual close.

  Proceed to PHASE 7.
- **`repair`** → ask the user via free-text follow-up for the repair direction, relaunch the implementing agent with those notes, then re-run PHASE 3 (verify) → PHASE 4 (panel) → PHASE 5 (forcing-functions) → return to this hard gate.
- **`stop`** → keep the working tree as-is; tell the user the remediation stopped with work uncommitted; clean up `$WORKDIR` and end the turn.

## PHASE 7 — Present + next step

What landed, and what comes next, differ by lane.

**FEATURE lane** — the fix landed as a `[WIP]` commit (the remediation diff). Tell the user:

- The remediation is committed as a `[WIP]` commit (it will be squashed into the clean feature commit by `/devforge:finalize`).
- The next step is **`/devforge:verify`** — re-running `/devforge:verify` on this feature re-proves the acceptance criteria against the REMEDIATED diff and re-renders the verdict (the remediation may flip a NEEDS WORK to APPROVED). When the original findings came from `/devforge:review`, re-running `/devforge:review` then `/devforge:verify` re-checks the assembled feature.

**COLD lane** — the fix landed as a finished commit and the bug is closed. Tell the user:

- The remediation is committed as `fix(<scope>): <title>` (standalone) or `[TICKET-ID] - <title>` on the source branch (wrapper). **It is a final commit — nothing will squash it**, so it is ready to push or PR as it stands.
- `<bug-file>` is now `**Status**: Fixed`, dated, with the fix notes written. In wrapper mode, name its separate install-repo commit too.
- **There is no `/devforge:verify` step** — a cold run has no feature and no acceptance criteria to re-prove. The gates it passed (scope-aware verify + self-repair, the four-reviewer panel, the forcing-functions gate, your own Stage-B read) were the whole verification, and they already ran.

Then clean up the scratch directories in one step — both `$WORKDIR` and the review-panel scratch dir (the same one `/devforge:implement` PHASE 6 uses):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
rm -rf "$WORKDIR" "${TMPDIR:-/tmp}/forge-implement-review"
```

## Important rules

1. **Proposal-only, never auto-invoked** — `/devforge:fix` is OFFERED (PROPOSED) as the "remediate now" arm of a two-arm fix-or-file offer; the user types `/devforge:fix`. The model never runs it autonomously (`disable-model-invocation: true`).
2. **Consumes WRITTEN findings, never invents them** — `/devforge:fix` remediates findings that already exist on disk or in the transcript before the run starts: pipeline-surfaced findings (`review.md` / `verification.md` NEEDS-WORK issues), a single user-raised + code-confirmed in-window defect, or ONE `bugs/NNN-<slug>.md` file handed to it by path. It does NOT accept a free-text bug description — there is no argument form that turns typed prose into a working-list item. On the feature lane an empty working list with no case-3 defect STOPS the run; on the cold lane a bug that cannot be CONFIRMED against live code STOPS the run (0.4b step 4).
3. **Two lanes, chosen by the argument** — the FEATURE lane runs in-window only, on a feature whose WIP commits are still open (post-`/devforge:implement`, pre-`/devforge:summarize`, gated by `in-fix-window`), and never fixes a sealed feature in place. The COLD lane runs when `$ARGUMENTS` names a `bugs/` file, has no feature and no window gate, and is the route for a bug that sits outside any feature's window. **The lane is decided by the argument's path, never by judgment**, and the cold lane is not a way to route around an in-window feature's gate — a defect in an open feature belongs on the feature lane.
4. **Defect repairs only — the scope bounce** — a working-list item that needs a feature/architecture change (not a correctness repair) bounces; `/devforge:fix` never grows scope. The bounce names the item and the reason on both lanes. On the FEATURE lane it recommends `/devforge:specify` and the USER picks the route (PHASE 1's three-option question); only the `re-enter specify` pick writes the `fix-seed.json` re-entry seed. On the COLD lane it recommends **`/devforge:research`** (because `/devforge:specify` blocks without a handoff), asks nothing, writes NO seed, and leaves the bug `Open`.
5. **The back half is CALLED, not COPIED** — PHASES 3–6 call `implement_helper verify-touched` / `merge-review-panel` / `run-forcing-functions-gate` / `wip-commit`, and PHASE 6's cold arm calls `fix_helper close-bug`; this spec copies none of their machinery (no `PACKAGE_STACKS`, self-repair-cap, panel-merge or bug-file-format logic). They are single-source-of-truth binaries; a caller cannot drift from them. **Both lanes run the SAME back half** — the cold lane skips no code gate.
6. **The architect never codes** — never dispatch `architect` to remediate; route layer-mixed work to the owning stack's implementers, or escalate to the human when an owning implementer is missing (per `.claude/agents/architect.md` Rule 1).
7. **Writes a commit, or on a feature bounce a re-entry seed — and CREATES no `bugs/` file, ever** — `/devforge:fix` writes NO report and mutates NO spec/task/`review.md`/`verification.md`. It never creates a `bugs/` file and never touches a `bugs/` file it was not handed; `/devforge:report-bug` is the only creator and the separate "defer" arm. Durable outputs by lane: on the FEATURE lane, at most ONE of the remediation `[WIP]` commit (PHASE 6) or `specs/[feature]/fix-seed.json` on the PHASE-1 bounce's matching `re-enter specify` pick — itself WIP-committed via `artifact_helper commit-artifacts` (install-repo-only, fail-soft), both squashed by `/devforge:finalize`. On the COLD lane, a completed run produces BOTH a final `fix(<scope>):` commit (never squashed — nothing finalizes it) and the single `Fixed` flip of the ONE bug file it consumed; a cold bounce produces NEITHER and leaves that bug `Open`.
8. **Nothing commits before `approve`** — the remediation + all self-repair / panel-repair edits sit in the working tree until the Stage B gate approves them, **and no `bugs/` file is flipped before then either**. A blocked verify cap, an unconverged panel, or a failed forcing-functions gate ends the turn with nothing committed and the bug file untouched.
9. **Relay machine reports VERBATIM** — where a helper emits a user-facing finding report on stdout (blocked verify, forcing-functions exit 2), copy its stdout VERBATIM into a fenced code block; for helper failures, copy the stderr VERBATIM. Do not summarize or paraphrase.
10. **Cleanup is last** — all intermediate scratch lives in `$WORKDIR` (`${TMPDIR:-/tmp}/forge-fix`) plus the reused `${TMPDIR:-/tmp}/forge-implement-review/` panel dir, both outside the repo, swept by the single PHASE-7 (or `stop`-path) `rm -rf`.
```
