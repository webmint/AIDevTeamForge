---
name: verify
description: Post-implementation acceptance-criteria verification plus assembled mechanical checks for one feature. Runs after `/devforge:review` and before `/devforge:summarize`. Proves each AC PASS/FAIL/PARTIAL, folds in `/devforge:review`'s findings, and renders the single APPROVED / NEEDS WORK / REJECTED verdict.
argument-hint: "[spec-file]"
---

# /devforge:verify — Acceptance-Criteria Verification + Verdict

`/devforge:verify` is the pipeline step run after `/devforge:review` and before `/devforge:summarize`/`/devforge:finalize`. It owns the ONE job nothing else in the pipeline owns: **the verdict**. `/devforge:review` is findings-only; `/devforge:verify` is where the spec's acceptance criteria are proven, the assembled feature is mechanically checked together (the cross-task version of `/devforge:implement`'s per-task gate) and run against a full-suite regression gate (green→red at the feature's merge-base flags a feature that broke a previously-green test suite the changed-file checks never touch — config-gated by `regression_gate`, default on), `/devforge:review`'s findings are folded in, and a single APPROVED / NEEDS WORK / REJECTED verdict is rendered and acted on. State + render shape are owned by `.devforge/lib/verify_helper`; the orchestrator composes values via verb subcommands and dispatches the `ac-verifier` agent.

**`/devforge:verify` OWNS the verdict — unlike `/devforge:review`, which produces findings only.** `/devforge:verify` does NOT run a finder ensemble or a refutation pass — that is `/devforge:review`'s job. `/devforge:verify` relies on `/devforge:review` for cross-task code-quality / consistency reasoning and adds three things on top: AC conformance, assembled mechanical checks, and the verdict. It does NOT fix code (it reports + decides) and it does NOT re-review.

Usage: `/devforge:verify` (auto-resolve the most-recently-modified feature directory under `specs/`) · `/devforge:verify <feature_dir>` or `/devforge:verify <feature_dir>/spec.md` (an explicit feature dir or a spec file inside it).

## Maintainer note

This file lives at `src/commands/verify/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/devforge:verify` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.devforge/command-refs/verify/<file>.md` at install time.

## Outputs of this command

`<feature_dir>` — here and everywhere else in this document — is the feature directory this run reads from and writes into: one path the orchestrator holds in working memory for the rest of the run. PHASE 0.2 resolves it, from `$ARGUMENTS` when one is given and by auto-resolution when it is empty. Hold it exactly as PHASE 0.2 resolved it — do not re-shape it, do not rebuild it from parts, and do not spell what is inside it. Every path below that sits inside the feature directory is `<feature_dir>` plus a filename, or plus the `tasks/` subdirectory PHASE 6's task cross-check reads — the one child directory this command names — and every `--feature` / `--feature-dir` flag below takes `<feature_dir>` itself. The `bugs/` tree in the third bullet is NOT inside `<feature_dir>`: it is a separate top-level directory with its own numbering, so `<feature_dir>` never composes a `bugs/` path.

The files this command writes under the repo are:

- `<feature_dir>/verification.md` — the rendered verification report (AC table, code-quality block, folded review findings, issues, and the verdict). Produced by the helper's `render-report` verb in PHASE 5. Idempotent: re-running `/devforge:verify` on the same feature OVERWRITES `verification.md` (the helper does an atomic write).
- `<feature_dir>/spec.md` — **mutated only on an APPROVED verdict** (PHASE 6): the spec `**Status**:` line flips to `Complete` and the passed AC checkboxes tick `- [ ]` → `- [x]`. This is the deliberate write-back that `/devforge:summarize` and `/devforge:finalize` gate on. On NEEDS WORK / REJECTED the spec is left unchanged.
- `bugs/NNN-<slug>.md` — **written only on a NEEDS WORK verdict** (PHASE 9), one file per issue the user elects to file, in the `.devforge/storage-rules.md` bug format (`Source: verify`). Sequential `NNN` numbering scanned from the existing `bugs/` directory.
- `<feature_dir>/verify-state.json` — per-feature run state (helper-owned, advanced via `check-status-and-flip --feature-dir <feature>`). Committed alongside `verification.md` in the end-of-run `[WIP]` commit (the `commit-artifacts` `--paths` lists both).

At the end of the run, `/devforge:verify` WIP-commits its OWN report artifacts — `verification.md` and the per-feature `verify-state.json` (always), plus `spec.md` when the PHASE-6 spec-status flip actually happened (an APPROVED verdict with no task-completion blocker) — via `.devforge/lib/artifact_helper commit-artifacts`. The two report paths are unconditional; `spec.md` is added to `--paths` ONLY when PHASE-6 `flip-spec-status` returned `flipped: true`, so the APPROVED-verdict flip lands in this same commit rather than sitting modified-uncommitted. Any `bugs/NNN-*.md` files (PHASE 9) are NOT part of this commit. The commit lands in the INSTALL repo only (never the wrapper-mode source/product repo) and is fail-soft (a git failure warns and `/devforge:verify` continues — the report is already written). The `[WIP]` commit folds into `/devforge:finalize`'s squash, so the final PR is unchanged.

### Intermediate scratch files (orchestrator-written, helper-consumed) — all under `$WORKDIR`

The helper cannot dispatch agents (a subprocess has no Task/MCP tools), so the orchestrator captures each verb's stdout to an intermediate scratch file that the next verb reads (most verbs take a `--<name> <path>` flag, not stdin). All live under `$WORKDIR` (`${TMPDIR:-/tmp}/forge-verify`) and are scratch state for one run — the whole directory is removed by the single PHASE-9 `rm -rf "$WORKDIR"`. Because `$WORKDIR` is outside the work tree, the files need no leading dot and no gitignore handling.

- `$WORKDIR/preflight.json` — the `preflight` stdout (`source_root`, `framework`, `language`, `wrapper_mode`, …). Written in PHASE 0, read by the orchestrator for the `--source-root` / `--framework` values it threads into later verbs.
- `$WORKDIR/scope.json` — the `resolve-feature-scope` stdout (`files`, `files_for_finders`, `file_count`, `scope_block`). Written in PHASE 1, read by the orchestrator to extract the changed-file count + the file list.
- `$WORKDIR/files.json` — the `files_for_finders` ARRAY extracted from `$WORKDIR/scope.json`. Written in PHASE 1, passed to `check-hygiene --files` (which takes a file PATH containing a JSON array). The same array, inlined as a single-line JSON string, is the `verify-touched --files` argument (which takes an inline JSON-array STRING, not a path).
- `$WORKDIR/review.json` — the `read-review-findings` stdout (`missing`, `confirmed`, `contested`, `summary`). Written in PHASE 2, passed to `compute-verdict --review-findings`, `render-report --review-findings`, and `render-inline-summary --review-findings`.
- `$WORKDIR/ac-config.json` — the `read-ac-config` stdout (`ac_verification_mode`, `ac_runtime_url`, `ac_runtime_api_base`, `ac_runtime_cli_command`). Written in PHASE 3, read by the orchestrator to pick the AC-mode branch and to compose the `ac-verifier` brief.
- `$WORKDIR/acs.json` — the `parse-acs` stdout (the structured AC list — `id`, `text`, `checked`, `subsection` per AC). Written in PHASE 3, passed to `merge-ac-results --acs`.
- `$WORKDIR/ac-report.md` — the `ac-verifier` agent's `## AC Verification Report` (its `### Results` table). Written BY THE AGENT via Bash redirection in PHASE 3, consumed by `merge-ac-results --agent-report`.
- `$WORKDIR/ac-results.json` — the `merge-ac-results` stdout (the AC list extended with `status` + `evidence` per AC). Written in PHASE 3, passed to `compute-verdict --ac-results`, `render-report --ac-results`, `render-inline-summary --ac-results`, and `flip-spec-status --ac-results`.
- `$WORKDIR/hygiene.json` — the `check-hygiene` stdout (`scope_creep`, `leftover_artifacts`, `scope_creep_checked`, `files_checked`, `files_unreadable`, `files_skipped`). Written in PHASE 4, passed to `compute-verdict --hygiene` and `render-report --hygiene`.
- `$WORKDIR/regression.json` — the `regression-gate` stdout (`status`, `regression`, `mode`, `baseline_status`, `head_status`, `note`, and — only on `status: "regression"` — `head_output_tail`). Written in PHASE 4, passed to `compute-verdict --regression`. (It is NOT a `render-report` input — the regression result reaches `verification.md` only through the verdict's reasons/blockers that `compute-verdict` folds it into.)
- `$WORKDIR/dead-code.json` — the `check-dead-code-removal` stdout (`status`, `violation`, `rows`, `pass_count`, `violation_count`, `total_count`, `note`, `handoff_read_error`). Written in PHASE 4, passed to `compute-verdict --dead-code`. (Like `regression.json`, it is NOT a `render-report` input — the dead-code result reaches `verification.md` only through the verdict's reasons/blockers that `compute-verdict` folds it into.)
- `$WORKDIR/e2e.json` — the `e2e-gate` stdout (`status`, `note`, and — only on `status: "e2e-failing"` — `output_tail`). Written in PHASE 4, passed to `compute-verdict --e2e`. (Like `regression.json`, it is NOT a `render-report` input — the e2e result reaches `verification.md` only through the verdict's reasons that `compute-verdict` folds it into, and it never becomes a blocker.)
- `$WORKDIR/verdict.json` — the `compute-verdict` stdout (`verdict`, `reasons`, `blockers`). Written in PHASE 5, passed to `render-report --verdict` and `render-inline-summary --verdict`.
- `$WORKDIR/issues.json` — the bug-issue array the orchestrator composes from the verdict blockers + AC failures + folded findings on a NEEDS WORK verdict. **Orchestrator-written via the Write tool** (NOT a helper-verb stdout — no verb produces it), in PHASE 9, passed to `file-bugs --issues`. Skipped entirely on a `none` election (the `file-bugs` call is not made — see PHASE 9 for the shape).

## Reference files

- `references/report-format.md` — the `verification.md` skeleton the helper produces (orientation for PHASE 5; the helper's `render-report` owns the actual render — do not hand-author the report).

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/verify_helper <verb> ...`, with two classes of exception, both enumerated here. Three steps call a DIFFERENT installed helper: `.devforge/lib/artifact_helper find-feature-artifacts` in PHASE 0.2 (feature resolution), `.devforge/lib/implement_helper verify-touched` in PHASE 4 (reused as a report), and `.devforge/lib/artifact_helper commit-artifacts` in the Cleanup block (the end-of-run `[WIP]` commit). The remaining non-`verify_helper` lines call no helper at all — the plain shell the fences show for scratch handling (`WORKDIR` setup, `mkdir` / `rm -rf`, the `cat` that loads a scratch file into a variable) plus PHASE 1's single `python3 -c` extraction. A step added later that is not a `verify_helper` call belongs in one of those two lists. Each verb prints JSON (or a rendered block) to stdout. Most verbs that consume a prior verb's output take a `--<name> <path>` flag (not stdin), so capture stdout to the named `$WORKDIR/*.json` scratch file with `>` and pass that path into the next call — the per-phase fences below show the exact redirects. Re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-verify"` at the top of every Bash block that touches scratch (the variable does not survive across Bash calls — see PHASE 0). On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns file structure, validation, and atomic writes; the orchestrator owns the `ac-verifier` dispatch, the MCP-availability probe, user-facing prose, and phase pacing.

## PHASE 0 — Preflight + feature resolution + scratch

Cheapest guards first; preflight before any feature I/O.

### 0.1 — Preflight gate

```bash
.devforge/lib/verify_helper preflight --workspace-root . > /tmp/verify-preflight-check.json
```

`preflight` checks the 4-command setup chain (`/devforge:init-forge → /devforge:generate-docs → /devforge:configure → /devforge:constitute`) and the populated-constitution guard. It ALWAYS writes its JSON context block to stdout BEFORE any gate check, then exits **2** with a user-facing stderr message when (a) a setup-chain artefact is missing or (b) `constitution.md` is absent or still carries an unpopulated sentinel. On exit 2, copy the helper's stderr VERBATIM as a fenced code block and end the turn — the user runs the named missing command first. On exit 0, the stdout JSON carries `source_root` (the project's Source Root — `.` for a standalone install, the inner project subdir in wrapper mode), `framework` (the Framework / Language string), `language`, and `wrapper_mode`. (`$WORKDIR` is not established until 0.3, so this gate call captures to a fixed `/tmp` path; 0.3 re-runs `preflight` into `$WORKDIR/preflight.json` once the scratch dir exists. `preflight` is read-only and cheap, so running it twice is harmless.) Carry `source_root` and `wrapper_mode` forward: PHASE 1 branches on `wrapper_mode` to decide whether to pass `--source-root` / `--install-root` to `resolve-feature-scope` (standalone omits both; wrapper mode passes both), PHASE 4 passes `source_root` to `check-hygiene --source-root`, and PHASE 5 passes both to `render-report`.

### 0.2 — Resolve the feature directory

Resolve the feature dir from `$ARGUMENTS`:

- When `$ARGUMENTS` names a feature directory, or a file inside one (e.g. `<feature_dir>/spec.md`), use that directory — strip a trailing filename to its parent directory, and re-shape nothing else.
- When `$ARGUMENTS` is empty, auto-resolve the feature directory holding the most recently written artifact (the feature most likely just finished `/devforge:review`). Resolve it here:

```bash
.devforge/lib/artifact_helper find-feature-artifacts --filenames '["*"]' --limit 1
```

`find-feature-artifacts` walks every feature directory the install has and reports the files sitting directly in each one; a file inside a nested subdirectory — `<feature_dir>/tasks/`, the one child directory this command names — is not listed and so does not affect the ordering below. `--filenames '["*"]'` names no particular file on purpose: this resolution selects a feature DIRECTORY, and it selects one whatever artifacts that directory happens to hold. `/devforge:verify` does need `<feature_dir>/spec.md` later — PHASE 3.1 parses its acceptance criteria — but that is a requirement of the RUN, not of the resolution: narrowing `--filenames` to `spec.md` would skip a spec-less feature directory this resolution is meant to consider and silently verify an older one in its place, so do not "tighten" it. `--limit 1` caps the result to a single record, applied AFTER the recency ordering is computed — so the survivor is chosen from every artifact in the install, never from a pre-truncated slice.

Stdout is a JSON object; take `matches_by_recency[0].feature_dir` from it — the first entry of the newest-artifact-first ordering, and under `--limit 1` the only entry. That path IS `<feature_dir>`: carry it forward exactly as reported. An EMPTY `matches_by_recency` means no feature directory holds any artifact: the call exits 0 in that case, because finding nothing is a normal outcome and not a failure, so there is no exit code to test for it — branch on the array being empty. A non-zero exit means the call itself failed (a malformed flag value, or a workspace that could not be resolved), never that no feature exists: copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

When `matches_by_recency` comes back empty, tell the user there is no feature to verify (run `/devforge:specify` → `/devforge:plan` → `/devforge:breakdown` → `/devforge:implement` → `/devforge:review` first) and end the turn. Carry the resolved directory forward as `<feature_dir>`, exactly as resolved — every subsequent `--feature` / `--feature-dir` flag takes it, and the spec file inside it is `<feature_dir>/spec.md` (the `--spec` value PHASE 3 needs).

### 0.3 — Initialize run state + scratch dir

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase0
```

`check-status-and-flip` advances `<feature_dir>/verify-state.json` to the named phase so an interrupted run can report where it stopped. Call it once at the start of each major phase with `--feature-dir <feature> --to <phase>` (`phase0` … `phase9`), and once at the very end of the run with `--to phase9 --status complete`. Keep these lightweight (one call per boundary, no parsing of the output beyond the non-zero-exit check). `--to` accepts any label, so these phase names are a convention, not a helper-enforced enum. The optional `--verdict <APPROVED|NEEDS WORK|REJECTED>` flag records the final verdict into `verify-state.json` and is passed ONLY on the terminal complete-flip (the Cleanup block) — every other phase-boundary call omits it, leaving the recorded verdict unchanged. (Note: the verb keys on `--feature-dir`, NOT `--workspace-root` — its state file is per-feature.)

Then establish + clear the scratch working directory:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"
```

**All intermediate scratch for this run lives in `$WORKDIR` (the fixed literal `${TMPDIR:-/tmp}/forge-verify`), OUTSIDE the repo.** The literal is `forge-verify`, NOT `forge-review` or `forge-audit` — `/devforge:review` and `/devforge:audit` may run concurrently, and a shared workdir would corrupt every run. `$WORKDIR` is outside the work tree, so the scratch files need no leading dot, no gitignore handling, and no per-file `rm` list. The `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"` clears any stale scratch from a prior crashed run.

**CRITICAL — `$WORKDIR` is a FIXED LITERAL you re-derive in every Bash block; it does NOT persist across calls.** The orchestrator runs each Bash tool call in a FRESH shell, so shell variables (including `$WORKDIR`) do NOT carry from one Bash call to the next. So every Bash block that touches scratch MUST begin by re-establishing `WORKDIR="${TMPDIR:-/tmp}/forge-verify"` and then reference `"$WORKDIR/..."`. The literal is identical in every block, so each block reconstructs the same directory.

Now re-capture the preflight context into `$WORKDIR` so later blocks can re-read its `source_root` / `framework` values (the gate already passed in 0.1; this just persists the context to the scratch dir):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper preflight --workspace-root . > "$WORKDIR/preflight.json"
```

## PHASE 1 — Resolve the assembled-feature scope

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase1
```

Compute the assembled-feature diff — the union of every change the feature made, across all the WIP commits `/devforge:implement` accumulated (squashed only by `/devforge:finalize`, which has not run yet). This is the assembled surface the per-task `/devforge:implement` gate never saw together. Read `wrapper_mode` and `source_root` from `$WORKDIR/preflight.json` (PHASE 0) and branch on them:

- **Standalone install** (`source_root` is `"."`): pass `--feature <feature>` ONLY. Omit `--source-root` and `--install-root` — the helper defaults `source_root` to CWD and `install_root` to `source_root`, which is correct here.
- **Wrapper mode** (`source_root` is NOT `"."` per `preflight.json`): pass `--feature <feature> --source-root <source-root> --install-root <install-root>`. `--source-root` is the code repo (the inner project subdir, the `source_root` value); `--install-root` is the forge install root where `.devforge/` lives (the wrapper root — typically the cwd `.`). **Both flags are mandatory in wrapper mode.** If `--install-root` is omitted the helper defaults it to `source_root` — then `abs_source == abs_install`, the wrapper-mode path-prefixing never fires, and `files_for_finders` is silently NOT source-root-prefixed, so the finder paths the later verbs read from the install root point at nonexistent files. Never omit `--install-root` in wrapper mode.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
# Standalone (source_root == "."): --feature only.
# Wrapper mode (source_root != "." per preflight.json): ALSO pass
#   --source-root <source-root> --install-root <install-root>
# so files_for_finders is source-root-prefixed, not silently left unprefixed.
.devforge/lib/verify_helper resolve-feature-scope \
  --feature <feature> \
  [--source-root <source-root> --install-root <install-root>  # wrapper mode only] \
  > "$WORKDIR/scope.json"
```

`resolve-feature-scope` runs `git diff --name-only $(git merge-base <base> HEAD)..HEAD` with `cwd = source-root` and emits JSON to stdout; the `>` redirect captures it to `$WORKDIR/scope.json`. The base ref auto-detects via `origin/HEAD → main → develop → master`; pass `--base <ref>` when auto-detection fails (the exit-2 stderr message says so). In wrapper mode the `--install-root` passed above (the forge install root where `.devforge/` lives) is what makes the emitted file paths install-root-relative — see the per-mode branch above. Stdout JSON carries `files` (sorted source-relative changed paths), `files_for_finders` (the same list, source-root-prefixed in wrapper mode), `file_count`, and `scope_block` (a pre-rendered human-readable scope summary, labelled "Verification Scope"). On a non-zero exit (not a git repo, bad ref, no auto-detectable base), copy the helper's stderr VERBATIM and end the turn.

**Empty-diff stop.** If `file_count` is `0` (HEAD == merge-base — the feature has no changes yet, or it is already squashed/merged), there is nothing to verify: tell the user the feature diff is empty (no changes between the base and HEAD, so no assembled surface to verify), clean up (`rm -rf "$WORKDIR"`), and end the turn gracefully. This is not an error — it is an empty feature.

Extract the `files_for_finders` ARRAY into its own file — `check-hygiene --files` (PHASE 4) takes a file PATH containing a JSON array, and the same array inlined as a single-line string is the `verify-touched --files` argument:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
python3 -c "import json; json.dump(json.load(open('$WORKDIR/scope.json'))['files_for_finders'], open('$WORKDIR/files.json','w'))"
```

Carry `file_count` forward for the user-facing prose.

## PHASE 2 — Read /devforge:review findings

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase2
```

Fold in `/devforge:review`'s findings — `/devforge:review` is findings-only; `/devforge:verify` reads `<feature_dir>/review.md` and incorporates its confirmed + high-stakes `[CONTESTED]` findings into the verdict. `/devforge:verify` does NOT re-derive these findings (no finder ensemble, no refutation pass — that is `/devforge:review`'s job).

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper read-review-findings --feature <feature> > "$WORKDIR/review.json"
```

`read-review-findings` accepts the feature directory (it appends `/review.md`) and parses `<feature_dir>/review.md` into a folded-findings dict: `missing`, `confirmed` (the confirmed-findings list), `contested` (the `[CONTESTED]`-tagged list), and `summary` (severity + partition counts). On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

**Missing-review warning (proceed weakened).** If the stdout JSON has `"missing": true`, warn the user: *no review report was found — run `/devforge:review` first for a complete verdict; proceeding with AC + mechanical checks only.* Do NOT stop — `compute-verdict` handles a missing review report as a non-blocking note (the verdict is computed from AC + mechanical + hygiene, and the missing report is recorded in the verdict reasons). Keep `$WORKDIR/review.json` and pass it forward unchanged.

## PHASE 3 — Acceptance-criteria verification

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase3
```

Prove each AC item PASS / FAIL / PARTIAL. The verification METHOD is selected by `ac_verification_mode`; in every mode the orchestrator dispatches the `ac-verifier` agent, and the agent's `## Verification modes` section owns the per-mode behavior. `/devforge:verify` reports AC failures — it NEVER fixes them; remediation happens separately (via `/devforge:fix` for a NEEDS-WORK finding, or a fresh `/devforge:specify` → `/devforge:plan` → `/devforge:breakdown` cycle for a spec-level change), not in `/devforge:verify`.

### 3.1 — Read the AC config + parse the spec's ACs

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper read-ac-config --root . > "$WORKDIR/ac-config.json"
.devforge/lib/verify_helper parse-acs --spec <feature>/spec.md > "$WORKDIR/acs.json"
```

`read-ac-config` reads the four `ac_*` keys from `.devforge/project-config.json` and emits `ac_verification_mode` (one of `code-only` | `tests` | `runtime-assisted` | `off`, defaulting to `off` when unset), `ac_runtime_url`, `ac_runtime_api_base`, and `ac_runtime_cli_command` (each defaulting to `""` when unset). Read the `ac_verification_mode` value — it is both the AC-mode branch selector below AND the `--ac-mode` flag PHASE 5 threads into `compute-verdict` and `render-report`. `parse-acs` parses the spec's `## Acceptance Criteria` section into a structured AC list (one dict per `- [ ] **AC-N**: …` checkbox, with `id` / `text` / `checked` / `subsection`); an empty list (no ACs in the spec) is valid, not an error.

### 3.2 — Probe Chrome MCP availability (runtime-assisted only)

When `ac_verification_mode` is `runtime-assisted`, probe Chrome DevTools MCP availability BEFORE composing the agent brief: make ONE lightweight `mcp__chrome-devtools__list_pages` call. If it returns a result, set `CHROME_MCP_AVAILABLE` to `true`; if the tool is unavailable or the call errors, set it to `false`. The agent uses `CHROME_MCP_AVAILABLE` to reclassify unobservable `frontend` items to code-reading fallback. For the other three modes (`tests`, `code-only`, `off`), do NOT probe — set `CHROME_MCP_AVAILABLE` to `false` (those modes never use the browser channel).

### 3.3 — Dispatch the ac-verifier agent

Dispatch the `ac-verifier` agent in ALL four modes. Compose its brief from the inputs its `## Input` section names — the AC list, the mode, the three runtime values, the MCP-availability flag, and the changed-files list — and instruct it to write its `### Results` report to `$WORKDIR/ac-report.md`:

- **Acceptance criteria** — the structured AC list from `$WORKDIR/acs.json` (the `id` + `text` of each AC).
- **`ac_verification_mode`** — the value from `$WORKDIR/ac-config.json`.
- **`ac_runtime_url`**, **`ac_runtime_api_base`**, **`ac_runtime_cli_command`** — the three runtime values from `$WORKDIR/ac-config.json` (each may be empty).
- **`CHROME_MCP_AVAILABLE`** — `true`/`false` from the 3.2 probe.
- **Changed files** — the `files` list from `$WORKDIR/scope.json` (the assembled-feature diff; the agent code-reads these for any AC it cannot observe at runtime).

Dispatch with `subagent_type: ac-verifier` (this loads the agent's persona from `.claude/agents/ac-verifier.md` as the subagent's system context — do NOT prepend or re-inline the persona into the brief; the brief carries only the inputs above on top of it). Instruct the agent to write its `## AC Verification Report` (its `### Results` table) to `$WORKDIR/ac-report.md` via Bash shell redirection — the agent carries `Bash`, so it writes the file with a `cat > "$WORKDIR/ac-report.md" << 'EOF' … EOF` heredoc; no Write tool needed. The four modes map to PHASE-3 behavior as:

- **`runtime-assisted`** — the agent verifies each AC against the running app (browser channel via `ac_runtime_url` for `frontend` ACs, API channel via `ac_runtime_api_base` for `backend` ACs, `ac_runtime_cli_command` to launch the runtime), and code-reads any item that cannot be observed (MCP down per `CHROME_MCP_AVAILABLE=false`, or the relevant `ac_runtime_*` value empty).
- **`tests`** — the agent verifies each AC by **code-reading** the changed files (the same per-AC method as `code-only`); it does NOT receive live test outcomes at dispatch time, because it is dispatched here in PHASE 3, before PHASE 4 runs the suite. The assembled test suite is executed **independently** by the orchestrator in PHASE 4 (the `verify-touched` test leg), and a non-`pass` mechanical status is an independent blocker that `compute-verdict` already enforces in PHASE 5 (regardless of the AC table). The fine-grained test-outcome→AC mapping is **deferred** (OQ-1 — resolve at the testForge20 e2e); the agent does NOT map PHASE-4 outcomes.
- **`code-only`** — the agent judges each AC by reading the changed files and records `PASS (code)` / `FAIL (code)` / `PARTIAL (code)`. No runtime probing, no test execution.
- **`off`** — the agent skips behavioral verification but applies a code-reading floor (a per-AC status by reading the changed files) and notes that ACs were verified by code only. The verdict explicitly flags this (and treats AC failures as advisory, not blocking — see PHASE 5).

### 3.4 — Merge the agent's results into the AC list

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper merge-ac-results --acs "$WORKDIR/acs.json" --agent-report "$WORKDIR/ac-report.md" > "$WORKDIR/ac-results.json"
```

`merge-ac-results` reads the structured AC list (`--acs`) and the agent's markdown report (`--agent-report`), extracts the agent's `### Results` table, and emits the AC list extended with `status` (`PASS` / `FAIL` / `PARTIAL` / `MANUAL` / `PASS (code)` / `FAIL (code)` / `PARTIAL (code)`, or `UNVERIFIED` when the agent produced no row for an AC) and `evidence` (the agent's Evidence cell) per AC. On a non-zero exit (missing required flag, or the `--acs` file is not a JSON list), copy the helper's stderr VERBATIM and end the turn.

## PHASE 4 — Assembled mechanical checks + hygiene + regression gate + dead-code removal + e2e run

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase4
```

Run the assembled-feature type-check / lint / build / test together — the cross-task version of `/devforge:implement`'s per-task gate. `/devforge:verify` REUSES the installed `implement_helper verify-touched` binary, treats its result as a REPORT, and does **NOT** loop on `self_repair` — the self-repair loop is `/devforge:implement`'s job; `/devforge:verify` reports failures, never fixes.

### 4.1 — Run the assembled mechanical check (report-only)

Pass the assembled changed-files list as an inline JSON-array STRING (NOT a path — `verify-touched --files` takes the array literally, distinct from `check-hygiene --files`, which takes a file path):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
FILES_JSON="$(cat "$WORKDIR/files.json")"
.devforge/lib/implement_helper verify-touched --files "$FILES_JSON" --root . --iteration 0 > "$WORKDIR/mechanical.json"
```

`verify-touched` resolves the source root from `PROJECT_ROOT` inside `.devforge/project-config.json` (via `--root .`), matches each touched file to its package via `PACKAGE_STACKS` (longest-path-prefix wins), and runs that package's commands in the fixed order static checks (type-check + lint) → build → tests, with `cwd = <source-root>`. **`--iteration 0`** is passed deliberately: it asks for ONE pass. Read the top-level `status` field from `$WORKDIR/mechanical.json` — it is one of `pass`, `self_repair`, `failed`, `isolation_failure`, or `tooling_unavailable`. **Do NOT re-run on `self_repair`** — capture the `status` string verbatim and carry it forward as the `--mechanical-status` value for PHASE 5 (`compute-verdict` treats any status other than `pass` / `""` as a mechanical failure that blocks APPROVED; `self_repair` here means "a check failed and would have been retried under `/devforge:implement`", which for `/devforge:verify` is a reported failure). The verb itself returns exit 0 for `pass` / `self_repair` and exit 2 for `failed` / `isolation_failure` / `tooling_unavailable`; a non-zero exit is still a valid REPORTED status (the JSON `status` is the report), so do NOT end the turn on it — read the `status`, carry it forward, and continue.

### 4.2 — Scope-creep + leftover-artifact hygiene

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper check-hygiene --files "$WORKDIR/files.json" --scope-baseline <scope-baseline> --source-root <source-root> > "$WORKDIR/hygiene.json"
```

`check-hygiene` reads the changed-files list (`--files`, a file PATH containing the JSON array written in PHASE 1) and flags two things across the assembled diff: scope-creep (changed files outside the planned scope) and leftover artifacts (debug prints, bare TODOs, commented-out code). For `--scope-baseline`, pass `<feature>/breakdown-handoff.json` when that file exists (its tasks' `touched_files` union is the planned scope); pass the literal string `none` when it is absent (the helper then skips the scope-creep check and reports only leftover artifacts). Pass the `source_root` from `$WORKDIR/preflight.json` to `--source-root` so the changed files are read from the right tree. Stdout JSON carries `scope_creep`, `leftover_artifacts`, `scope_creep_checked`, `files_checked`, `files_unreadable`, and `files_skipped` (count of non-code prose/data files bypassed by the file-type gate). On a non-zero exit (missing `--files`, or it is not a JSON list), copy the helper's stderr VERBATIM and end the turn.

### 4.3 — Full-suite regression gate

Run the full-suite regression gate — the net for a defect the changed-file mechanical check in 4.1 structurally cannot catch: a feature that breaks an EXISTING, untouched test. 4.1 scopes its type-check / lint / build / test to the assembled feature's changed files; the regression gate runs the WHOLE primary test suite at the feature's merge-base and again at HEAD, and compares.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper regression-gate --feature <feature> --workspace-root . > "$WORKDIR/regression.json"
```

`regression-gate` reads the `regression_gate` config itself (`REGRESSION_GATE` in `.devforge/project-config.json`, default `full`) — pass NO `--mode` in normal operation; the verb resolves the config default. It runs the primary test command (`TEST_COMMANDS[0]`) at the feature's merge-base in an isolated git worktree and again at HEAD, and reports a regression ONLY when the suite was green at the merge-base and is red at HEAD (a suite already red at the merge-base is a pre-existing failure, reported as `baseline-failing`, never the feature's fault, never gated). It is **FAIL-SOFT by design**: it ALWAYS exits 0, even on a git error, a missing merge-base, or an absent test command — an internal problem yields `status: "inconclusive"`, never a crash and never a non-zero exit. So do NOT apply the "non-zero exit → copy stderr → end the turn" recovery here; read the `status` field from `$WORKDIR/regression.json` and branch on it. Stdout JSON carries `status` (one of `off` / `inconclusive` / `clean` / `baseline-failing` / `regression`), `regression` (bool — `true` only when `status` is `regression`), `mode`, `baseline_status`, `head_status`, `note` (a human-readable explanation, always present), and — only when `status` is `regression` — `head_output_tail` (the last lines of the failing HEAD test run).

Branch on `status` (mirroring how 4.1 surfaces the mechanical-check status — only `regression` gates; every other status is informational, never a silent pass but never a false gate):

- **`off`** — the regression gate is disabled (`regression_gate=off`). Note it in the run; do not gate.
- **`inconclusive`** — the gate could not run this time (no auto-detectable merge-base, no configured test command, or a git error). Surface the `note` field to the user so it is visible that the regression net did not run this time; do not gate.
- **`baseline-failing`** — the suite was already red at the merge-base, so a red HEAD is not this feature's fault. Surface the `note`; do not gate.
- **`clean`** — the full suite is green at both the merge-base and HEAD. Note it; do not gate.
- **`regression`** — the feature broke a previously-green suite (green→red). This FEEDS the verdict as a blocker via `compute-verdict --regression` (PHASE 5.1) → NEEDS WORK. Surface the `head_output_tail` to the user so they can see which tests now fail. Do NOT decide the verdict yourself — pass `$WORKDIR/regression.json` to `compute-verdict` and let the helper own the fold.

Carry `$WORKDIR/regression.json` forward to PHASE 5.1 unchanged in every branch (`compute-verdict --regression` handles each status — only `regression:true` adds a blocker; every other status leaves the verdict unaffected).

### 4.4 — Change-induced dead-code removal check

Confirm the plan-declared change-induced dead code was actually removed — the net for the guard-and-leave failure where a dominating change ships but the now-unreachable arm / branch / import it kills is left in place. `/devforge:plan` predicts what a Key Design Decision renders unreachable, `/devforge:breakdown` carries the declared kill-list as a `dead_code_rows` array on `breakdown-handoff.json`, and this check mechanically confirms each declared row's anchor string is GONE from the post-change source tree.

**Honest bound.** This confirms REMOVAL of the DECLARED kill-list only — it does not, and structurally cannot, discover deadness the architect never declared at `/devforge:plan` (that gap is covered only by the advisory backstops (the single-task check in `code-reviewer.md` item 9 and the cross-task pattern in `review/references/emergent-issue-checklist.md`), never by this gate; declared kill-list only — undeclared deadness is not checked). A `violation` means the declared `anchor_token` literal string is still present somewhere in the file — verify it is a genuine leftover, not an incidental match (a comment, a quoted string, an unrelated symbol name) — before treating it as a confirmed defect.

For `--breakdown-handoff`, pass `<feature>/breakdown-handoff.json` when that file exists (its top-level `dead_code_rows` array is the declared kill-list); pass the literal string `none` when it is absent (the helper then reports a vacuous result — nothing declared, nothing to confirm). Pass the `source_root` from `$WORKDIR/preflight.json` to `--source-root` so each row's `file` resolves from the right tree.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
# --breakdown-handoff: pass <feature>/breakdown-handoff.json when it exists,
#   else the literal string "none" (vacuous — nothing declared to confirm).
.devforge/lib/verify_helper check-dead-code-removal --breakdown-handoff <breakdown-handoff-or-none> --source-root <source-root> > "$WORKDIR/dead-code.json"
```

`check-dead-code-removal` reads the declared `dead_code_rows` and confirms each row's `anchor_token` is absent from its post-change file. Stdout JSON carries `status` (one of `vacuous` / `clean` / `violation`), `violation` (bool — `true` only when a declared row's anchor is still present), `rows`, `pass_count`, `violation_count`, `total_count`, `note`, and `handoff_read_error` (bool). It is **non-fatal — it ALWAYS exits 0** (a handoff read/parse failure is reported in the JSON, never a crash and never a non-zero exit), so do NOT apply the "non-zero exit → copy stderr → end the turn" recovery here; read the JSON and branch on it.

**`handoff_read_error: true` — relay the WARN, do not end the turn.** When the stdout JSON has `"handoff_read_error": true`, the declared kill-list could not be read — the `breakdown-handoff.json` existed but was unreadable, malformed, or its `dead_code_rows` was the wrong type. This is DISTINCT from nothing being declared (a `vacuous` result with `handoff_read_error: false`): the check genuinely could not run. The helper writes a stderr line beginning `verify_helper check-dead-code-removal: WARN:`; copy that stderr line VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), so it is visible that the dead-code confirmation could not run, then continue (the check is non-fatal — `violation` stays `false`, so the verdict is unaffected).

Carry `$WORKDIR/dead-code.json` forward to PHASE 5.1 unchanged (`compute-verdict --dead-code` handles it — only `violation:true` adds a blocker; a `vacuous` result — including the read-error case, which stays `status: vacuous` with `handoff_read_error: true` layered on, never a third status value — or a `clean` result leaves the verdict unaffected).

### 4.5 — e2e run

Run the project's configured end-to-end suite once against the assembled feature. 4.1 runs each touched package's commands from `PACKAGE_STACKS` and 4.3 runs the primary test command (`TEST_COMMANDS[0]`); neither of them reads `E2E_COMMAND`, so a suite configured under that key runs here and in no earlier check. This run is **ADVISORY**: no status changes the verdict, and the result reaches `verification.md` only through the verdict's reasons.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper e2e-gate --workspace-root . > "$WORKDIR/e2e.json"
```

`e2e-gate` reads the `E2E_COMMAND` key from `.devforge/project-config.json` itself — pass no command and no `--source-root`; the verb resolves the Source Root from `--workspace-root` the same way `regression-gate` does, and a successfully-read config whose `E2E_COMMAND` is absent or blank means no suite is configured (`off`) — while a `project-config.json` that is missing, unreadable, or not a parseable JSON object is reported `inconclusive` with a `note` naming the cause, never `off`. It runs that command ONCE, at HEAD, in the project's Source Root — never in an isolated worktree, never at the merge-base, and never a second time — under its own timeout. **The suite owns the application lifecycle:** `/devforge:verify` starts no server, waits on nothing beyond the command itself, and tears nothing down; whatever the suite needs brought up (a dev server, a browser, containers) the suite brings up for itself. It is **FAIL-SOFT by design**: it ALWAYS exits 0, even when the configured command cannot be found or executed, the run times out, or the subprocess errors — an internal problem yields `status: "inconclusive"`, never a crash and never a non-zero exit. So do NOT apply the "non-zero exit → copy stderr → end the turn" recovery here; read the `status` field from `$WORKDIR/e2e.json` and branch on it. Stdout JSON carries `status` (one of `off` / `inconclusive` / `e2e-clean` / `e2e-failing`), `note` (a human-readable explanation, always present), and — only when `status` is `e2e-failing` — `output_tail` (the last lines of the failing run's combined output).

Branch on `status` (mirroring how 4.3 surfaces the regression status, with one difference: here NO status gates at all — every branch is informational, never a silent pass, and the result reaches the verdict only as the advisory reasons line `compute-verdict` folds in):

- **`off`** — no `E2E_COMMAND` is configured. Note NOTHING in the run: print no line about the end-to-end suite at all, and do not gate. (This branch DELIBERATELY diverges from 4.3's `off`, which does note itself — do not harmonize the two. A regression gate that is off was switched off by a person and is worth saying; an absent `E2E_COMMAND` is the ordinary state of most projects, and saying so every run is noise.)
- **`inconclusive`** — the gate could not produce a suite result this time (`project-config.json` could not be read or parsed, the command could not be executed, the run timed out, or the gate hit an internal error). Surface the `note` field to the user so it is visible that the end-to-end suite did not report this time; do not gate.
- **`e2e-clean`** — the suite ran and passed. Note it briefly; do not gate.
- **`e2e-failing`** — the suite ran and reported failures. Surface the `note` AND the `output_tail` to the user so they can see what failed; do not gate, and do NOT treat it as a blocker or decide the verdict yourself — pass `$WORKDIR/e2e.json` to `compute-verdict` and let the helper own the fold.

Carry `$WORKDIR/e2e.json` forward to PHASE 5.1 unchanged in every branch (`compute-verdict --e2e` handles each status — a non-`off` status adds one advisory line to the verdict's reasons, `off` adds nothing, and no status changes the verdict).

## PHASE 5 — Verdict + report + inline summary

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase5
```

Compute the deterministic verdict, write `verification.md`, and print the count-first inline summary.

### 5.1 — Compute the verdict

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper compute-verdict --ac-results "$WORKDIR/ac-results.json" --review-findings "$WORKDIR/review.json" --hygiene "$WORKDIR/hygiene.json" --regression "$WORKDIR/regression.json" --dead-code "$WORKDIR/dead-code.json" --e2e "$WORKDIR/e2e.json" --mechanical-status <mechanical-status> --ac-mode <ac-mode> > "$WORKDIR/verdict.json"
```

`compute-verdict` is deterministic: it reads the merged AC results (`--ac-results`), the folded review findings (`--review-findings`), the hygiene result (`--hygiene`), the regression-gate result (`--regression`, the `$WORKDIR/regression.json` from PHASE 4.3), the dead-code removal result (`--dead-code`, the `$WORKDIR/dead-code.json` from PHASE 4.4), the e2e result (`--e2e`, the `$WORKDIR/e2e.json` from PHASE 4.5), the `verify-touched` status string (`--mechanical-status`, the `status` carried from PHASE 4.1), and the AC mode (`--ac-mode`, the `ac_verification_mode` from PHASE 3.1), and emits `verdict` (APPROVED / NEEDS WORK / REJECTED), `reasons` (explanation lines), and `blockers` (structured blocker dicts). **Constitution violations always block APPROVED** (D7): a confirmed `[CONSTITUTION-VIOLATION]` from the review findings forces REJECTED, and a contested one forces at least NEEDS WORK. Under `ac_verification_mode=off`, AC failures are advisory (noted in `reasons`, not blocking); under all other modes a FAIL/PARTIAL AC is a blocker. **A regression (`regression:true` in `--regression`) adds a blocker → NEEDS WORK, and never anything else** — a regression can never force REJECTED (it is an implementation-level break, not a spec-level failure), and every non-`regression` status (`off` / `inconclusive` / `clean` / `baseline-failing`) leaves the verdict unaffected. **A declared-but-unremoved dead-code row (`violation:true` in `--dead-code`) folds in the same way** — it adds a `dead_code_unremoved` blocker → NEEDS WORK, and never REJECTED (a mechanical-check precedent, not a spec-level failure); a `vacuous` (nothing declared, including the read-error case — `handoff_read_error:true` stays layered on a `vacuous` status, never a third status value) or `clean` (all rows confirmed removed) result leaves the verdict unaffected. **The e2e result (`--e2e`) folds differently from both — it NEVER produces a blocker, under any status.** It adds ONE advisory line to `reasons` naming the status and its `note`, and adds nothing at all on `off`; given the same other inputs the verdict is identical whether the e2e status is `off`, `inconclusive`, `e2e-clean` or `e2e-failing`. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

### 5.2 — Render the report

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
DATE="$(date +%Y-%m-%d)"
.devforge/lib/verify_helper render-report --verdict "$WORKDIR/verdict.json" --ac-results "$WORKDIR/ac-results.json" --review-findings "$WORKDIR/review.json" --hygiene "$WORKDIR/hygiene.json" --mechanical-status <mechanical-status> --feature <feature> --date "$DATE" --ac-mode <ac-mode>
```

`render-report` reads the verdict + the AC results + the folded review findings + the hygiene result, renders the full verification markdown (skeleton documented in `references/report-format.md`), and writes it to `<feature_dir>/verification.md` via an atomic write, OVERWRITING any prior `verification.md`. `--feature` and `--date` are REQUIRED (the helper never calls the clock — `--date` is `YYYY-MM-DD`). Stdout is the written path. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

### 5.3 — Print the inline summary

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper render-inline-summary --verdict "$WORKDIR/verdict.json" --ac-results "$WORKDIR/ac-results.json" --review-findings "$WORKDIR/review.json" --mechanical-status <mechanical-status> --feature <feature>
```

`render-inline-summary` prints the count-first `## Verification Complete` block — the verdict, the AC pass/fail/unverified counts, the mechanical result, the folded-finding counts, the key reasons, and the next-step pointer. (It does NOT accept `--hygiene` or `--ac-mode` — those are `render-report`-only; the inline summary draws hygiene + mode context from the verdict's `reasons`/`blockers`, which already factor them in, rather than from the raw hygiene/mode data.) Copy the helper's stdout VERBATIM into your user-facing message as a fenced code block (this follows the count-first audit-format discipline). Read the `verdict` from `$WORKDIR/verdict.json` — it drives PHASE 6, PHASE 8, and PHASE 9.

## PHASE 6 — Spec-status flip (APPROVED only)

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase6
```

**Only on an APPROVED verdict** — flip the spec `**Status**:` to Complete and tick the passed AC boxes. On NEEDS WORK or REJECTED, do NOTHING here (the spec status is left unchanged) and skip straight to PHASE 7.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper flip-spec-status --feature <feature> --ac-results "$WORKDIR/ac-results.json"
```

`flip-spec-status` FIRST cross-checks that every task file under `<feature_dir>/tasks/*.md` (excluding `README.md`) has `**Status**: Complete` or `Skipped`; only when all tasks are satisfied does it flip the spec `**Status**:` line to `Complete` and tick each passed AC's `- [ ]` → `- [x]` (a passed AC is one whose merged `status` is `PASS` or `PASS (code)`). The atomic write mutates `spec.md`. Stdout JSON carries `flipped` (bool), `blocker` (a message string, or `null` on success), `ticked` (the AC ids ticked this call), and `spec_path`. **If `flipped` is `false`**, the spec was NOT changed — report the `blocker` message to the user verbatim (e.g. a task is still `In Progress`) and keep the spec status unchanged; the verdict stays APPROVED in `verification.md` but the lifecycle flip is held until the blocker clears. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

## PHASE 7 — Memory update

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase7
```

**Read what is already recorded before writing.** Alongside the fields 0.1 names, the `preflight` stdout captured at `$WORKDIR/preflight.json` (PHASE 0, so it reflects the file as it stood BEFORE this run) carries `memory_present` (bool) and `memory_excerpt` (the populated `## ` sections of `.devforge/memory.md` — `## Task Outcomes` excluded, every section with no entries under its heading dropped, and any section the line budget could not fit whole cut from its EARLIEST lines, with an inline marker line right after the heading naming how many were omitted). Read `memory_excerpt` before composing the entry, and let it shape what you write: an entry already covering this lesson makes an append a duplicate — sharpen or extend the existing wording instead of restating it — and a lesson this feature hit for the SECOND time is worth recording AS recurring, which is a stronger signal than a fresh-looking note. When `memory_present` is false or `memory_excerpt` is empty — the shipped stub carries no entries under its headings, so it renders as an empty excerpt — there is nothing to reconcile against: proceed exactly as below and say nothing to the user about the empty file. **Honesty bound.** A prior entry is an UNVERIFIED prior-session assertion, not a verified fact — it informs WHAT to write here and nothing else. It never enters the verdict (PHASE 5 already computed that from the inputs `compute-verdict` takes, and this phase never revises it), and it is never restated into the new entry as though this run had confirmed it.

Record the feature-level lesson in `.devforge/memory.md` — what the ASSEMBLED feature taught, and what verification caught that the per-task `/devforge:implement` gate missed. Keep it LIGHT: feature-level only, never a per-task re-log (per-task detail belongs in the task files' `## Completion Notes` and in `.devforge/session-state.md`, not here). Skip silently when there is nothing feature-level worth recording.

**Pick the destination section FIRST — there is no end-of-file append path.** Take the FIRST line of this rubric that matches the lesson; there is no fourth bucket:

- **A defect this verification CAUGHT** — write it under `## What Failed`.
- **A technique or approach that WORKED** — write it under `## What Worked`.
- **A gotcha or near-miss to avoid next time** — write it under `## Known Pitfalls`.

A lesson matching none of the three is not written at all — that is the skip-silently case above, not a licence to put it somewhere else.

**Then place the entry INSIDE the section you picked.** Read `.devforge/memory.md`, locate the chosen `## ` heading, and insert the short dated entry immediately BEFORE the next `## ` heading at the same depth — or before EOF when the chosen section is the file's last one. When the chosen heading is absent from the file, CREATE it at the end of the file — the `## ` title line, then the entry — which is NOT the same as appending a bare entry under whatever section already sits last: a new section carrying an entry is neither excluded nor content-free, so the excerpt keeps it. When `.devforge/memory.md` itself is absent, Write the file fresh, holding just that `## ` heading and the entry. **Placement is load-bearing:** an entry appended blindly at EOF lands inside whatever section happens to be last, which on any install that ran tasks under the retired per-task writer is `## Task Outcomes` — the one section the excerpt above drops outright, so no consumer of that excerpt ever surfaces the lesson again. This write is orchestrator prose — no `verify_helper` verb writes memory — and **the Write tool OVERWRITES the file it is given, so it can never "append"**: Read `.devforge/memory.md`, compose the full new content with the entry inserted at the located position, and Write that whole content back; or make the same insertion with the Edit tool against a unique anchor (the chosen heading line, or the entry the new one follows).

## PHASE 8 — Present + next step

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase8
```

Tell the user where `verification.md` was written and the next step, branched on the verdict:

- **APPROVED** — the spec is Complete (PHASE 6, unless a flip blocker was reported); next is `/devforge:summarize` then `/devforge:finalize`.
- **NEEDS WORK** — offer the user a two-arm fix-or-file choice for the blocking issues (these are ALTERNATIVES, not a pipeline): **(A)** run `/devforge:fix` to remediate the blockers now (a gated remediation loop reusing `/devforge:implement`'s back-half verify + review-panel + commit — re-running `/devforge:verify` afterward re-checks the ACs against the remediated diff), or **(B)** file bugs to defer (PHASE 9 — the batch bug-filing path below). `/devforge:verify` only PROPOSES `/devforge:fix` — it never runs it, and it writes no `bugs/` file itself except via the PHASE-9 `file-bugs` path the user elects; the user types `/devforge:fix` to take arm A, or proceeds into PHASE 9 to take arm B. Do NOT suggest re-running `/devforge:implement` here — `/devforge:implement` drains approved tasks, which does not fix a NEEDS-WORK finding; `/devforge:fix` does.
- **REJECTED** — the feature has a spec-level problem; revise the spec via `/devforge:specify` → `/devforge:plan` → `/devforge:breakdown`, then re-implement.

On APPROVED or REJECTED, skip PHASE 9 and go straight to the cleanup block below.

## PHASE 9 — Issue report + batch bug-filing (NEEDS WORK only)

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase9
```

**Only on a NEEDS WORK verdict.** Present the blocking issues to the user (the verdict `blockers` — which covers AC failures, mechanical check failures, Critical/High/Medium review findings, and any constitution blocker — the same set surfaced in `verification.md`), then offer to file bugs: **all** (file one bug per issue), **select** (the user names which to file), or **none** (skip filing). When the user elects to file some or all, compose the issue array and write it to scratch, then call `file-bugs`:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
DATE="$(date +%Y-%m-%d)"
.devforge/lib/verify_helper file-bugs --issues "$WORKDIR/issues.json" --bugs-dir bugs --feature-spec <feature>/spec.md --date "$DATE"
```

Compose `$WORKDIR/issues.json` as a JSON array of issue dicts and write it with the Write tool (it is orchestrator-composed — no helper verb emits it). Each dict carries `title`, `severity` (the storage-rules vocabulary `Critical` | `Warning` | `Info` — map review/AC severities to it), `description`, `expected`, `actual`, `files` (a list of `{path, detail}`), `evidence`, and `ac_ref` (`AC-N` or `N/A`):

```json
[
  {
    "title": "Order total ignores discount code",
    "severity": "Critical",
    "description": "Applying a valid discount code leaves the cart total unchanged.",
    "expected": "Total reflects the discount after the code is applied.",
    "actual": "Total is unchanged; the discount is parsed but never subtracted.",
    "files": [
      {"path": "src/cart/total.ts", "detail": "applyDiscount() computes but discards the delta"}
    ],
    "evidence": "AC-3 FAIL: expected $90.00, observed $100.00 (see verification.md)",
    "ac_ref": "AC-3"
  }
]
```

Write that array to `$WORKDIR/issues.json`, then make the `file-bugs` call above. `file-bugs` scans the existing `bugs/` directory for the highest `NNN` prefix, assigns sequential numbers from there, and writes one `bugs/NNN-<slug>.md` per issue in the `.devforge/storage-rules.md` format (`Source: verify`). `--date` is REQUIRED (`YYYY-MM-DD`). Stdout is the JSON array of paths written; report them to the user. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn. When the user elects **none**, do NOT compose `issues.json` and SKIP the `file-bugs` call entirely (do not invoke it with an empty path).

## Cleanup

First mark the run complete so an interrupted re-run can distinguish a finished verification from a stopped one, recording the run's verdict into state via `--verdict`. Use `<verdict>` — the literal APPROVED / NEEDS WORK / REJECTED value the orchestrator read from `$WORKDIR/verdict.json` in PHASE 5.3 (the `verdict` field) and has held since; inline the verdict value you already hold — do NOT re-read the scratch file here:

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase9 --status complete --verdict "<verdict>"
```

Then WIP-commit `/devforge:verify`'s own report artifacts so the work is git-safe at this step. Run this UNCONDITIONALLY for every verdict (`verification.md` was written in PHASE 5.2 regardless of verdict). Use the feature directory's own name — the last segment of `<feature_dir>`, called `<feature-dir-name>` below — for the commit label, and pass `<feature_dir>` itself in the `--paths` entries: `commit-artifacts` takes an absolute entry and a repo-relative one alike, so pass it in the form PHASE 0.2 resolved it and re-shape nothing.

```bash
# Base paths (ALWAYS): verification.md + verify-state.json.
# When PHASE-6 flip-spec-status returned flipped:true, ALSO append
#   "<feature_dir>/spec.md" to the --paths array; omit it otherwise.
.devforge/lib/artifact_helper commit-artifacts --paths '["<feature_dir>/verification.md", "<feature_dir>/verify-state.json"]' --label 'verify: <feature-dir-name>'
```

Substitute `<feature_dir>` with the directory PHASE 0.2 resolved and `<feature-dir-name>` with its last segment. The base `--paths` array ALWAYS lists `verification.md` + `verify-state.json`; when PHASE-6 `flip-spec-status` returned `flipped: true`, ALSO append `<feature_dir>/spec.md` to the array so the APPROVED-verdict spec flip is committed here (otherwise it is left modified-uncommitted, dirtying the tree). Append `spec.md` ONLY when the flip happened — on NEEDS WORK / REJECTED, or when a task-completion blocker held the flip (`flipped: false`), `spec.md` is unchanged and MUST be omitted. Any `bugs/NNN-*.md` file from PHASE 9 is NOT part of this commit. `commit-artifacts` stages ONLY the named paths and makes a `[WIP] verify: <feature-dir-name>` commit in the INSTALL repo (never the wrapper-mode source/product repo). It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the report is already written, so note the warning and CONTINUE; do NOT end the turn); "nothing to commit" (paths already staged or absent) exits 0 silently as a benign no-op. The `[WIP]` commit folds into `/devforge:finalize`'s squash, leaving the final PR unchanged.

Finally, clean up the scratch directory in one step — nothing else needs the scratch after the report + summary + (optional) bug-filing + the commit above (the commit reads only paths under `<feature_dir>`, never `$WORKDIR`):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
rm -rf "$WORKDIR"
```

## Important rules

1. **`/devforge:verify` OWNS the verdict** — unlike `/devforge:review` (findings only), `/devforge:verify` renders the single APPROVED / NEEDS WORK / REJECTED verdict via the deterministic `compute-verdict` verb. The verdict is `/devforge:verify`'s defining job.
2. **`/devforge:verify` does NOT fix code** — it reports AC failures, mechanical-check failures, and hygiene flags, and renders a verdict; it never edits source. Remediation happens separately (via `/devforge:fix` for a NEEDS-WORK finding, or a fresh `/devforge:specify` → `/devforge:plan` → `/devforge:breakdown` cycle for a spec-level change), not in `/devforge:verify`. The `verify-touched` reuse is report-only at `--iteration 0` with NO self-repair loop.
3. **`/devforge:verify` does NOT re-review** — it has no finder ensemble and no refutation pass (those are `/devforge:review`'s job, and the `_shared` refutation engine is deliberately NOT reused here). `/devforge:verify` folds in `/devforge:review`'s already-refuted findings via `read-review-findings` and points to the `/devforge:review` report for cross-task code-quality reasoning.
4. **Constitution violations always block APPROVED** (D7) — a confirmed `[CONSTITUTION-VIOLATION]` from the review findings forces REJECTED; a contested one forces at least NEEDS WORK. `compute-verdict` enforces this structurally; never override it.
5. **`/devforge:verify` WRITES BACK to the spec** — on APPROVED (and only after the task cross-check passes), `flip-spec-status` flips `spec.md`'s `**Status**:` to Complete and ticks the passed AC boxes. This is the deliberate departure: `/devforge:verify` is the only review/verify command that mutates its input, because it owns the Complete lifecycle transition `/devforge:summarize` and `/devforge:finalize` gate on. On NEEDS WORK / REJECTED the spec is untouched.
6. **Missing review report is non-fatal** — if `<feature_dir>/review.md` is absent, warn the user (run `/devforge:review` first) and proceed with AC + mechanical + hygiene only; `compute-verdict` records the missing report in the verdict reasons.
7. **Empty feature diff is non-fatal** — `file_count == 0` (HEAD == merge-base) means there is nothing to verify; stop gracefully after cleanup (PHASE 1).
8. **Wrapper-mode aware** — in wrapper mode, `resolve-feature-scope` requires both `--source-root` (the inner code repo) AND `--install-root` (the wrapper root where `.devforge/` lives); `verify-touched --root` and `check-hygiene --source-root` each take `source_root`; `<feature_dir>`, `bugs/`, and `verification.md` always live at the workspace root.
9. **Cleanup is last** — all intermediate scratch lives in `$WORKDIR` (`${TMPDIR:-/tmp}/forge-verify`), outside the repo, and is swept by the single `rm -rf "$WORKDIR"` in the Cleanup block, never mid-run.
10. **Regression gate is NEEDS WORK-only and fail-soft** — the PHASE-4.3 regression gate is the full-suite net for a feature that breaks a previously-green, untouched test (green→red at the merge-base). A `status:regression` result ALWAYS folds to NEEDS WORK via `compute-verdict --regression` and can NEVER force REJECTED (it is implementation-level, not spec-level). Every other status (`off` / `inconclusive` / `clean` / `baseline-failing`) ALWAYS does not gate — those are informational, never a silent pass. The gate is fail-soft: a git or test-runner error is reported as `inconclusive`, never a blocker and never a crash. It is config-gated by `regression_gate` (`REGRESSION_GATE`, default `full`), which the verb reads itself — `/devforge:verify` passes no `--mode`.
11. **Dead-code removal check is NEEDS WORK-only, honest-bounded, and non-fatal** — the PHASE-4.4 `check-dead-code-removal` confirms REMOVAL of the plan-declared change-induced dead-code kill-list (the `dead_code_rows` carried on `breakdown-handoff.json`); it confirms the DECLARED kill-list only and does NOT discover deadness the architect never declared (that gap is the advisory backstops', not this gate's). A `violation:true` result ALWAYS folds to NEEDS WORK via `compute-verdict --dead-code` as a `dead_code_unremoved` blocker and can NEVER force REJECTED (a mechanical-check precedent, not spec-level); `vacuous` (nothing declared) and `clean` (all rows confirmed removed) never gate. The check is non-fatal (it ALWAYS exits 0); a `handoff_read_error:true` result means the declared kill-list could not be read (distinct from nothing declared) — relay the helper's stderr WARN verbatim and continue.
