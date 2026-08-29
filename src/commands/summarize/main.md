---
name: summarize
description: PR-ready summary of a completed feature — what was built (in user terms), change stats, key decisions, deviations, and AC status. Runs after `/devforge:verify` approves and before `/devforge:finalize`. Pure synthesis — agent-free, renders no verdict, mutates none of its inputs.
argument-hint: "[spec-file]"
---

# /devforge:summarize — PR-Ready Feature Summary

`/devforge:summarize` is the pipeline step run after `/devforge:verify` approves and before `/devforge:finalize`. It owns the ONE job nothing else in the pipeline owns: **the PR-ready human-facing feature narrative**. `/devforge:verify` owns the verdict; `/devforge:review` owns findings; `/devforge:summarize` owns the synthesized story of what was built — in user terms — once the feature record is complete. Its output (`<feature_dir>/summary.md`) is copy-ready for a PR description. State + render shape are owned by `.devforge/lib/summarize_helper`; the orchestrator composes values via verb subcommands and writes the summary prose itself.

**`/devforge:summarize` is pure SYNTHESIS — agent-free, no verdict, read-only on its inputs.** It runs NO finder ensemble, NO refutation pass, and dispatches NO agent. It does NOT verify (that is `/devforge:verify`), does NOT find issues (that is `/devforge:review`), and does NOT squash commits or generate docs (that is `/devforge:finalize`). It REFERENCES the verdict `/devforge:verify` already computed (read from `verification.md`) but never renders one of its own. It writes ONLY `<feature_dir>/summary.md` and touches none of its inputs (spec, plan, task files, `verification.md`, git history).

Usage: `/devforge:summarize` (auto-resolve the most-recently-modified feature directory under `specs/`) · `/devforge:summarize <feature_dir>` or `/devforge:summarize <feature_dir>/spec.md` (an explicit feature dir or a spec file inside it).

## Maintainer note

This file lives at `src/commands/summarize/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/devforge:summarize` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.devforge/command-refs/summarize/<file>.md` at install time.

## Outputs of this command

`<feature_dir>` — here and everywhere else in this document — is the feature directory this run reads from and writes into: one path the orchestrator holds in working memory for the rest of the run. PHASE 0.1 resolves it — from `$ARGUMENTS` when one is given, by auto-resolution when it is empty. Hold it exactly as PHASE 0.1 resolved it — do not re-shape it, do not rebuild it from parts, and do not spell what is inside it. The one artifact path below is `<feature_dir>` plus a filename, and so is every input this command reads beside the spec (or, for the task files, `<feature_dir>/tasks/` plus a filename).

The only file this command writes under the repo is:

- `<feature_dir>/summary.md` — the rendered feature summary (What was built / Changes / Files changed / Key decisions / Deviations / Acceptance criteria). Composed INLINE by the orchestrator in PHASE 3 and written with the Write tool in PHASE 4. Idempotent: re-running `/devforge:summarize` on the same feature OVERWRITES `summary.md`.

`/devforge:summarize` makes ONE `[WIP]` commit (PHASE 4) that adds `summary.md`; it mutates no other tracked file. The WIP commit is squashed later by `/devforge:finalize`.

### Intermediate scratch files (orchestrator-written, helper-consumed) — all under `$WORKDIR`

The helper cannot dispatch agents and the orchestrator owns the prose synthesis, so each phase captures a verb's stdout JSON to an intermediate scratch file under `$WORKDIR` that a later phase reads. All live under `$WORKDIR` (`${TMPDIR:-/tmp}/forge-summarize`) and are scratch state for one run — the whole directory is removed by the single Cleanup-block `rm -rf "$WORKDIR"`. Because `$WORKDIR` is outside the work tree, the files need no leading dot and no gitignore handling.

- `$WORKDIR/preflight.json` — the `preflight` stdout (`source_root`, `wrapper_mode`, `framework`, `language`, `spec_status`, `spec_complete`, …). Written in PHASE 0, read by the orchestrator for the `source_root` + `wrapper_mode` values it branches on when threading `--source-root` / `--install-root` into `gather-change-data` (PHASE 1).
- `$WORKDIR/changes.json` — the `gather-change-data` stdout (`files`, `file_count`, `scope_block`, `by_directory`, `insertions`, `deletions`, `stat_summary`, `source_changes`). Written in PHASE 1, read by the orchestrator for the Files-changed section.
- `$WORKDIR/verification.json` — the `read-verification` stdout (`ac_list`, `verdict`). Written in PHASE 2, read by the orchestrator for the Acceptance-criteria section (the AUTHORITATIVE AC status) and the referenced verdict.
- `$WORKDIR/notes.json` — the `parse-completion-notes` stdout (a JSON array, one dict per task: `completed_at`, `files_changed`, `expects_met`, `produces_met`, `notes`, `has_unverified`, `has_notes`, `task_file`). Written in PHASE 2, read by the orchestrator for the Changes + Deviations sections.
- `$WORKDIR/decisions.json` — the `read-plan-decisions` stdout (`decisions`, `heading`, `shape`). Written in PHASE 2, read by the orchestrator for the Key-decisions section.

## Reference files

- `references/summary-format.md` — the `summary.md` skeleton the orchestrator composes (orientation for PHASE 3; documents the six sections, the omit-Deviations-if-none rule, and that AC status comes from `verification.md`. The synthesis is inline prose — there is no `write-summary` helper verb).

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/summarize_helper <verb> ...`. Each verb prints JSON to stdout; capture it to the named `$WORKDIR/*.json` scratch file with `>` and read that file in the phase that needs it — the per-phase fences below show the exact redirects. Re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-summarize"` at the top of every Bash block that touches scratch (the variable does not survive across Bash calls — see PHASE 0). On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns the preflight/gate, structured-input gathering, and parsing; the orchestrator owns the prose synthesis, the `summary.md` write, the `[WIP]` commit, and phase pacing. **No agent is dispatched and no verdict is rendered anywhere in this flow.**

## PHASE 0 — Preflight + feature resolution + the spec-Complete gate + scratch

Cheapest guards first; preflight before any feature I/O.

### 0.1 — Resolve the feature directory

Resolve the feature dir from `$ARGUMENTS`:

- When `$ARGUMENTS` names a feature directory under `specs/` or a file inside one (e.g. that directory's `spec.md`), use that feature directory — strip a trailing filename to the directory itself.
- When `$ARGUMENTS` is empty, auto-resolve the feature directory holding the most recently written artifact (the feature most likely just finished `/devforge:verify`). Resolve it here:

```bash
.devforge/lib/artifact_helper find-feature-artifacts --filenames '["*"]' --limit 1
```

`find-feature-artifacts` walks every feature directory the install has and reports the files sitting directly in each one; a file inside a nested subdirectory — `<feature_dir>/tasks/`, the one child directory this command names — is not listed and so does not affect the ordering below. `--filenames '["*"]'` names no particular file on purpose: this resolution selects a feature DIRECTORY, and it selects one whatever artifacts that directory happens to hold. `/devforge:summarize` does need `<feature_dir>/spec.md` and `<feature_dir>/plan.md` later — 0.2's gate reads the spec's `**Status**:` line, and 2.3 reads the plan's decisions — but those are requirements of the RUN, not of the resolution, and there is no single file to key on: narrowing `--filenames` to either one would skip a feature directory this resolution is meant to consider and silently summarize an older one in its place, where today the run stops instead — at 0.2's gate for a missing spec, at 2.3 for a missing plan. So do not "tighten" it. `--limit 1` caps the result to a single record, applied AFTER the recency ordering is computed — so the survivor is chosen from every artifact in the install, never from a pre-truncated slice.

Stdout is a JSON object; take `matches_by_recency[0].feature_dir` from it — the first entry of the newest-artifact-first ordering, and under `--limit 1` the only entry. That path IS `<feature_dir>`: carry it forward exactly as reported. An EMPTY `matches_by_recency` means no feature directory holds any artifact: the call exits 0 in that case, because finding nothing is a normal outcome and not a failure, so there is no exit code to test for it — branch on the array being empty. A non-zero exit means the call itself failed (a malformed flag value, or a workspace that could not be resolved), never that no feature exists: copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

When `matches_by_recency` comes back empty, tell the user there is no feature to summarize (run `/devforge:specify` → `/devforge:plan` → `/devforge:breakdown` → `/devforge:implement` → `/devforge:review` → `/devforge:verify` first) and end the turn. Carry the resolved directory forward as this run's `<feature_dir>` — hold it exactly as resolved, because every input this command reads and the one file it writes is `<feature_dir>` plus a filename. The spec file inside it is `<feature_dir>/spec.md` (the `--spec` value 0.2 needs).

### 0.2 — Preflight + the spec-Complete gate

```bash
.devforge/lib/summarize_helper preflight --workspace-root . --spec <feature_dir>/spec.md > /tmp/summarize-preflight-check.json
```

`preflight` checks the 4-command setup chain (`/devforge:init-forge → /devforge:generate-docs → /devforge:configure → /devforge:constitute`) AND the spec `**Status**: Complete` gate. It ALWAYS writes its JSON context block to stdout BEFORE any gate check, then exits:

- **2** — a setup-chain artefact is missing. On exit 2, copy the helper's stderr VERBATIM as a fenced code block and end the turn — the user runs the named missing command first.
- **3** — the spec is not `**Status**: Complete` (or the spec is absent). `/devforge:summarize` runs AFTER `/devforge:verify` flips the spec to Complete on an APPROVED verdict, so a non-Complete spec means `/devforge:verify` has not yet approved this feature. On exit 3, copy the helper's stderr VERBATIM as a fenced code block and end the turn (the message names the current spec status and instructs the user to run `/devforge:verify` first).
- **0** — both gates pass. The stdout JSON carries `source_root` (the project's Source Root — `.` for a standalone install, the inner project subdir in wrapper mode), `wrapper_mode`, `framework`, `language`, `spec_status`, and `spec_complete`.

(`$WORKDIR` is not established until 0.3, so this gate call captures to a fixed `/tmp` path; 0.3 re-runs `preflight` into `$WORKDIR/preflight.json` once the scratch dir exists. `preflight` is read-only and cheap, so running it twice is harmless.) Carry `source_root` AND `wrapper_mode` forward: PHASE 1 branches on `wrapper_mode` to decide whether to pass `--source-root` / `--install-root` to `gather-change-data` (standalone passes neither; wrapper mode passes both).

### 0.3 — Establish the scratch dir + persist the context

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-summarize"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"
```

**All intermediate scratch for this run lives in `$WORKDIR` (the fixed literal `${TMPDIR:-/tmp}/forge-summarize`), OUTSIDE the repo.** The literal is `forge-summarize`, NOT `forge-verify`, `forge-review`, or `forge-audit` — those commands may run concurrently, and a shared workdir would corrupt every run. `$WORKDIR` is outside the work tree, so the scratch files need no leading dot, no gitignore handling, and no per-file `rm` list. The `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"` clears any stale scratch from a prior crashed run.

**CRITICAL — `$WORKDIR` is a FIXED LITERAL you re-derive in every Bash block; it does NOT persist across calls.** The orchestrator runs each Bash tool call in a FRESH shell, so shell variables (including `$WORKDIR`) do NOT carry from one Bash call to the next. So every Bash block that touches scratch MUST begin by re-establishing `WORKDIR="${TMPDIR:-/tmp}/forge-summarize"` and then reference `"$WORKDIR/..."`. The literal is identical in every block, so each block reconstructs the same directory.

Now re-capture the preflight context into `$WORKDIR` so later blocks can re-read its `source_root` value (the gates already passed in 0.2; this just persists the context to the scratch dir):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-summarize"
.devforge/lib/summarize_helper preflight --workspace-root . --spec <feature_dir>/spec.md > "$WORKDIR/preflight.json"
```

### 0.4 — Already-finalized warning (commit-state check)

Check whether the feature was already finalized before summarizing. `/devforge:summarize` is meant to run on a feature whose tasks are still recorded as unsquashed `[WIP]` / `[checkpoint]` commits (the per-task history `/devforge:implement` accumulated); `/devforge:finalize` squashes those into a single clean `feat(*)` commit. If `/devforge:finalize` already ran, the task-by-task history is gone and the summary reflects only the current assembled state.

```bash
git log --oneline --grep='\[WIP\]' --grep='\[checkpoint\]'
```

(Pass each prefix as its own `--grep` — git ORs multiple `--grep` patterns. Do NOT combine them with a `\|` alternation: that is a GNU-BRE extension BSD/macOS git does not honor, so it would match a literal `\|`, find nothing, and fire the warning on every run.) This is a branch-GLOBAL heuristic backing a non-blocking warning — it searches ALL branch commits, not just this feature's, so on a branch with several sequential features it is intentionally approximate (feature-scoping the grep would itself be unreliable, since per-task `[WIP]` messages need not carry the feature slug). If this prints no `[WIP]` / `[checkpoint]` commits AND a clean `feat(*)` commit for this feature is present, warn the user (do NOT stop): *the feature appears already finalized — no `[WIP]`/`[checkpoint]` commits remain and a clean feature commit is present, so this summary will reflect the current assembled state, not the task-by-task history. For the richest summary, run `/devforge:summarize` before `/devforge:finalize`.* The Commit Convention in `CLAUDE.md` defines the `[WIP]` / `[checkpoint]` / `feat(scope):` prefixes this check keys on. Then proceed — the summary is still useful from the current state.

## PHASE 1 — Gather change data

Compute the assembled-feature change data — the union of every change the feature made across all the WIP commits `/devforge:implement` accumulated (squashed only by `/devforge:finalize`, which has not run yet). Read `wrapper_mode` and `source_root` from `$WORKDIR/preflight.json` (PHASE 0) and branch on them:

- **Standalone install** (`source_root` is `"."`): pass `--feature-dir <feature_dir>` ONLY. Omit `--source-root` and `--install-root` — the helper defaults both to `"."`, which is correct here.
- **Wrapper mode** (`source_root` is NOT `"."` per `preflight.json`): pass `--feature-dir <feature_dir> --source-root <source-root> --install-root <install-root>`. `--source-root` is the code repo (the inner project subdir, the `source_root` value); `--install-root` is the forge install root where `.devforge/` lives (the wrapper root — typically the cwd `.`). **Both flags are mandatory in wrapper mode.** If `--install-root` is omitted the helper defaults it to `source_root` — then `abs_source == abs_install`, the wrapper-mode guard never fires, and `source_changes` is silently `null`, dropping the source-repo change set from the summary (breaking D5). Never omit `--install-root` in wrapper mode.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-summarize"
# Standalone (source_root == "."): --feature-dir only.
# Wrapper mode (source_root != "." per preflight.json): ALSO pass
#   --source-root <source-root> --install-root <install-root>
# so the source-repo change set (source_changes) is gathered, not silently dropped (D5).
.devforge/lib/summarize_helper gather-change-data \
  --feature-dir <feature_dir> \
  [--source-root <source-root> --install-root <install-root>  # wrapper mode only] \
  > "$WORKDIR/changes.json"
```

`gather-change-data` resolves the assembled-feature diff via the shared scope resolver (the same `_shared.feature_scope` resolver `/devforge:review` and `/devforge:verify` use, with the heading label "Summary Scope"), then supplements it with a `git diff --stat <base>..HEAD` for the +/- line totals the resolver does not provide. The base ref auto-detects via `origin/HEAD → main → develop → master`; pass `--base <ref>` when auto-detection fails (the stderr message says so). In wrapper mode the `--install-root` passed above (the forge install root where `.devforge/` lives) is what makes `source_changes` non-null — see the per-mode branch above. Stdout JSON carries `files` (sorted source-relative changed paths), `files_for_finders` (the same list, source-root-prefixed in wrapper mode), `file_count`, `scope_block`, `by_directory` (files grouped by top-level directory), `insertions`, `deletions`, `stat_summary` (the raw `git diff --stat` summary line), and `source_changes`. On a non-zero exit (not a git repo, bad ref, no auto-detectable base), copy the helper's stderr VERBATIM and end the turn.

**Empty-diff stop.** If `file_count` is `0` (HEAD == merge-base — the feature has no changes yet, or it is already squashed/merged), there is nothing to summarize: tell the user the feature diff is empty (no changes between the base and HEAD), clean up (`rm -rf "$WORKDIR"`), and end the turn gracefully. This is not an error — it is an empty feature.

**Wrapper-mode source changes (D5).** When the install ran in wrapper mode (specs/docs in the wrapper root, code in a separate source repo), `gather-change-data` returns a parallel `source_changes` object (same keys as the top level, scoped to the source repo) instead of `null`. When `source_changes` is non-null, include BOTH change sets in the Files-changed section (PHASE 3) — the wrapper-side changes (specs, docs) and the source-side code changes. When `source_changes` is `null` (standalone install), use only the top-level change data.

## PHASE 2 — Read inputs

Read the three structured inputs the synthesis draws from: the authoritative AC status + the referenced verdict (from `verification.md`), each task's completion notes, and the plan's key decisions.

### 2.1 — Read the verification report (authoritative AC status)

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-summarize"
.devforge/lib/summarize_helper read-verification --path <feature_dir>/verification.md > "$WORKDIR/verification.json"
```

`read-verification` parses `/devforge:verify`'s `<feature_dir>/verification.md` into `ac_list` (one dict per AC with `id`, `status`, `evidence` — the status is the AUTHORITATIVE per-AC result `/devforge:verify` already proved) and `verdict` (`APPROVED` / `NEEDS WORK` / `REJECTED`, or `""` when none was found). **The AC status comes from `verification.md`'s table, NOT re-derived from the spec** (D3) — `/devforge:verify` already proved each AC PASS/FAIL/PARTIAL, and `/devforge:summarize` reports that result verbatim. The `verdict` is REFERENCED in the summary (it is `/devforge:verify`'s verdict — `/devforge:summarize` does not compute it).

**Missing-verification warning (proceed weakened).** `read-verification` exits 2 when `verification.md` cannot be opened (it is absent). On that exit, warn the user: *no verification report was found at `<feature_dir>/verification.md` — run `/devforge:verify` first for the authoritative AC status; proceeding with the summary but the Acceptance-criteria section will be marked unverified.* Do NOT end the turn — write an empty `$WORKDIR/verification.json` (`{"ac_list": [], "verdict": ""}`) with the Write tool, proceed, and in PHASE 3 render the Acceptance-criteria section as "_No verification report found — run `/devforge:verify` to populate AC status._" rather than fabricating statuses. (This mirrors how `/devforge:verify` proceeds weakened on a missing `/devforge:review` report rather than stopping.)

### 2.2 — Parse the task completion notes

Enumerate the feature's task files — every `<feature_dir>/tasks/*.md` except `README.md` — and pass each as a repeated `--task-file`:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-summarize"
.devforge/lib/summarize_helper parse-completion-notes \
  --task-file <feature_dir>/tasks/001-<slug>.md \
  --task-file <feature_dir>/tasks/002-<slug>.md \
  > "$WORKDIR/notes.json"
```

(Substitute the actual task filenames — one `--task-file` per task file, `README.md` excluded.) `parse-completion-notes` parses each task's `## Completion Notes` section (filled by `/devforge:implement`'s `mark-complete`) and emits a JSON ARRAY, one dict per task, with `completed_at`, `files_changed` (list), `expects_met`, `produces_met`, `notes` (the deviation / observation text, `""` when none), `has_unverified` (bool), `has_notes` (bool — `false` when the task has no `## Completion Notes` section yet), and `task_file` (the path). The orchestrator reads `files_changed` + `notes` per task for the Changes + Deviations sections. On a non-zero exit (an unreadable task file), copy the helper's stderr VERBATIM and end the turn.

### 2.3 — Read the plan's key decisions

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-summarize"
.devforge/lib/summarize_helper read-plan-decisions --path <feature_dir>/plan.md > "$WORKDIR/decisions.json"
```

`read-plan-decisions` parses `plan.md`'s key-decisions section (D9 — it reads `plan.md`, NOT `plan-handoff.json`) into `decisions` (a list of dicts with `decision`, `chosen`, `rationale`, `rejected`), plus `heading` and `shape` for diagnostics. It recognizes both the current `### Key Design Decisions` heading and the older `## Architecture Decisions` heading; an empty `decisions` list (no recognized heading) is valid, not an error. On a non-zero exit (the plan file cannot be opened), copy the helper's stderr VERBATIM and end the turn.

## PHASE 3 — Compose the summary prose (orchestrator-inline, agent-free)

Compose the summary INLINE from the scratch inputs — `$WORKDIR/changes.json`, `$WORKDIR/verification.json`, `$WORKDIR/notes.json`, `$WORKDIR/decisions.json`. **This is orchestrator prose-writing — dispatch NO agent and render NO verdict.** The summary is a 1-page section-templated narrative; `references/summary-format.md` documents the skeleton. Compose these six sections (each user-facing, 1-5 lines; describe behavior and outcomes, not implementation mechanics):

1. **What was built** — 2-3 sentences synthesized from the spec overview + the plan, in user terms (what the user gets, not how it was coded).
2. **Changes** — one line per task, drawn from `$WORKDIR/notes.json` (the task's accomplishment, summarized in user terms — group by what changed, not raw file paths).
3. **Files changed** — the directory grouping from `$WORKDIR/changes.json`'s `by_directory`, plus the `git diff --stat` totals (`insertions` / `deletions`, or the `stat_summary` line). When `changes.json`'s `source_changes` is non-null (wrapper mode, PHASE 1), include the source-repo change set too (D5).
4. **Key decisions** — the most important decisions from `$WORKDIR/decisions.json`'s `decisions` (one line each: what was decided and why, from the `decision` / `chosen` / `rationale` fields).
5. **Deviations from plan** — **OMIT THIS SECTION ENTIRELY if no task noted a deviation** (no task in `$WORKDIR/notes.json` has a non-empty `notes`). When present, one line per deviating task.
6. **Acceptance criteria** — a compact checklist, with each AC's status taken VERBATIM from `$WORKDIR/verification.json`'s `ac_list` (NOT re-derived from the spec). When `verification.json` is the empty-fallback from 2.1, render the unverified note instead of a checklist.

Keep it concise: this is a summary, not a report. Deduplicate — group files by area rather than listing each. Do not speculate — include only what is present in the spec, plan, task notes, `verification.md`, or git data.

## PHASE 4 — Write summary.md + WIP commit

Write the composed summary to `<feature_dir>/summary.md` with the Write tool (idempotent overwrite — re-running `/devforge:summarize` replaces any prior `summary.md`; D6). There is NO `write-summary` helper verb — the orchestrator writes the prose directly, because the synthesis is inline (D6).

Then make a single `[WIP]` commit adding `summary.md`, following the Commit Convention in `CLAUDE.md` (the `[WIP] Type: description` shape; `[WIP]` commits are squashed into the final feature commit by `/devforge:finalize`):

```bash
git add <feature_dir>/summary.md && git commit -m "[WIP] Feature summary: <feature-dir-name>"
```

Substitute `<feature-dir-name>` — the last segment of `<feature_dir>` — into the commit message. The staged path is `<feature_dir>` plus the filename: `<feature_dir>` already carries every segment above `summary.md`, so nothing is prepended to it. `/devforge:summarize` stages and commits ONLY `summary.md` — it mutates no other tracked file (D4).

## PHASE 5 — Present + next step

Present the composed summary to the user, then point to the next pipeline step:

```
Summary saved to <feature_dir>/summary.md — copy-ready for a PR description.

Next: run `/devforge:finalize` to write surgical `docs/` updates via tech-writer and squash the WIP commits into a clean feature commit.
```

Then clean up the scratch directory — nothing else needs it after the summary is written:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-summarize"
rm -rf "$WORKDIR"
```

## Important rules

1. **Concise over comprehensive** — this is a summary, not a report. Each section targets 1-5 lines. If a section would be empty (e.g. no deviations), omit it entirely.
2. **User-facing language** — describe what was built in terms of behavior and outcomes, not implementation mechanics. "Added email validation to signup", not "Created `validateEmail` in `utils/validation.ts`".
3. **Deduplicate** — when multiple tasks touched the same directory or area, group them in Files changed rather than listing each file.
4. **No speculation** — include only information present in the spec, plan, task `## Completion Notes`, `verification.md`, or git data. Do not infer or guess.
5. **Idempotent** — re-running `/devforge:summarize` overwrites `summary.md` with a fresh summary (D6).
6. **Renders no verdict** (D1) — the verdict is `/devforge:verify`'s. `/devforge:summarize` REFERENCES the verdict it reads from `verification.md` but never computes or renders one of its own. There is no finder ensemble, no refutation pass, and no agent dispatch.
7. **Read-only on inputs** (D4) — `/devforge:summarize` writes ONLY `<feature_dir>/summary.md` (and the one `[WIP]` commit that adds it). It never mutates the spec, plan, task files, `verification.md`, or git history. This is the deliberate contrast with `/devforge:verify`, which writes back to the spec.
8. **Authoritative AC status** (D3) — the Acceptance-criteria section takes each AC's status VERBATIM from `verification.md`'s table; it is never re-derived from the spec.
