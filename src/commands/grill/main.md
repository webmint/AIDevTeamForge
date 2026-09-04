---
name: grill
description: Adversarial design grill of the finished plan, run between `/devforge:plan` and `/devforge:breakdown` — two devils-advocate passes, unioned and cross-examined by non-author refuters, written to `<feature_dir>/grill.md` with a PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL recommendation the user owns. `/devforge:breakdown` requires that it RAN, never that its disposition binds; a run nothing survived ends without a question.
argument-hint: "[plan-file-or-feature]"
---

# /devforge:grill — Adversarial Design Grill

`/devforge:grill` is a standalone, required pipeline stage positioned BETWEEN `/devforge:plan` and `/devforge:breakdown`. It is the design-level mirror of `/devforge:review`: `/devforge:plan` builds the design, and `/devforge:grill` attacks the FINISHED design (`plan.md` and the `spec.md` it implements) before `/devforge:breakdown` spends effort decomposing it and `/devforge:implement` writes the code — while killing a fatally-flawed design is still cheap. It dispatches the `devils-advocate` adversary in ADVERSARIAL DESIGN-GRILL MODE TWICE — two independent passes over an identical brief, whose validated findings are UNIONED into one working list — validates every attack against the actual artifacts to discard ungrounded ones, cross-examines the survivors of that union with a SINGLE refutation pass (default-dismiss unless the defect is demonstrable from quoted evidence), writes a findings report to `<feature_dir>/grill.md`, and recommends a 4-way disposition. Read-only on source — it never modifies source, never modifies the plan or spec; it WIP-commits only its OWN artifacts (the report + seed + state) in an install-repo-only, fail-soft `[WIP]` commit that folds into `/devforge:finalize`'s squash. State + render shape are owned by `.devforge/lib/grill_helper`; the orchestrator composes values via verb subcommands.

The genuine gap it fills: `/devforge:plan` *compares* 2–3 alternatives and the architect picks a winner, but nobody ever attacks the winner — comparison is optimization, not refutation. By charter the architect is an OPTIMIZER / decision authority ("decide HOW", "own the final architectural call"), not an adversary chartered to attack the design it chose. So the chosen design is never adversarially attacked anywhere in the pipeline. `/devforge:grill` is the only place it is.

**`/devforge:grill` produces FINDINGS PLUS a recommended DISPOSITION — but the disposition is a RECOMMENDATION, not a binding verdict.** The human owns the final call at the existing `/devforge:breakdown` approval gate. Unlike `/devforge:review` (pure findings-only, because `/devforge:verify` owns its verdict downstream), `/devforge:grill` carries a light disposition because there is no downstream design-`/devforge:verify` to own it. The four dispositions are PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL.

**A CLEAN run does NOT interrupt the human.** When no finding survived cross-examination — nothing confirmed, nothing contested, nothing left unresolved — PHASE 7 presents the result and ends the turn without asking a question. The human gate fires only when at least one finding survived, so the question the user is asked always has something concrete behind it. A clean run still renders `grill.md`, still records its state, and still WIP-commits both.

**Mandatory to RUN, never binding in its VERDICT.** `/devforge:breakdown` refuses to decompose a plan until `/devforge:grill` has run for it, so every feature pays exactly one grill. That entry gate reads the PRESENCE of `<feature_dir>/grill.md` plus the adversary status recorded in its sibling `grill-state.json`, and NOTHING else — not the disposition (a KILL report satisfies it exactly as a PROCEED one does) and not freshness (a report written against a since-edited `plan.md` still passes, so acting on a finding never costs another full adversarial run). `/devforge:grill` itself still runs ONLY on the user's say-so — typed, or agreed to when a blocked `/devforge:breakdown` offers it — and no command starts it on its own initiative. `/devforge:plan` still emits its NON-BLOCKING advisory hint when the finished plan looks high-stakes (wide file impact / new data model / new dependency / security-relevant / risk-laden with 4+ risks); that hint is unchanged — it neither runs `/devforge:grill` nor gates anything, and it now nudges about WHEN to grill, not WHETHER to.

**What being mandatory did NOT change.** The USER still owns every non-clean verdict at the PHASE-7 human gate. All FOUR dispositions survive, KILL included. The cross-pick and re-entry arms are untouched. `/devforge:grill` still never modifies `plan.md` or `spec.md`. What became mandatory is that the grill RAN — never that its disposition binds anything.

Usage: `/devforge:grill` (auto-resolve the feature under `specs/` whose `plan.md` was modified most recently) · `/devforge:grill <feature_dir>` or `/devforge:grill <feature_dir>/plan.md` (an explicit feature dir or a `plan.md` path inside it).

## Maintainer note

This file lives at `src/commands/grill/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/devforge:grill` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.devforge/command-refs/grill/<file>.md` at install time.

## Outputs of this command

`<feature_dir>` — here and everywhere else in this document — is the feature directory this run reads from and writes into: one path the orchestrator holds in working memory for the rest of the run. PHASE 0.1 takes it from `$ARGUMENTS` when the user named one; otherwise PHASE 1's `resolve-scope` auto-detects it. Either way PHASE 1 then re-binds it to the manifest's `feature_dir`, and that is the form every later flag, artifact path and user-facing message carries. Hold it exactly as the resolution site reported it — do not re-shape it, do not rebuild it from parts, and do not spell what is inside it. Every artifact path below is `<feature_dir>` plus a filename, and so is every sibling this command reads.

The files this command writes under the repo are:

- `<feature_dir>/grill.md` — the rendered design-grill report. Produced by the helper's `render-report` verb in PHASE 6; carries the surviving findings AND the recommended 4-way disposition. Idempotent: re-running `/devforge:grill` on the same feature OVERWRITES `grill.md` (the helper does an atomic write).
- `<feature_dir>/grill-seed.json` — written in PHASE 7 when the user chooses the matching re-entry at the human gate — `Revise plan` on a REVISE-PLAN recommendation (`target_stage=plan`, for `/devforge:plan`), or `Re-enter upstream` on a RE-ENTER-UPSTREAM recommendation (an upstream stage `spec` / `discovery` / `research`, for `/devforge:specify` / `/devforge:discover` / `/devforge:research`). Produced by the helper's `write-seed` verb; the structured BACKWARD handoff the named re-entry command consumes on re-entry so the re-run is directed, not a repeat. Not written on a clean run (no question is asked, so no arm is entered), and not written for Proceed, Kill, or a cross-pick (the user picking a re-entry that does not match the recommendation).

Per-feature run state lives in `<feature_dir>/grill-state.json` (helper-owned, advanced via `check-status-and-flip --feature-dir <feature_dir>`).

At the end of PHASE 6, `/devforge:grill` WIP-commits its own report artifacts — `grill.md` and the per-feature `grill-state.json` — via `.devforge/lib/artifact_helper commit-artifacts`. That commit is unconditional: it runs on every run, clean or not, and both arms of PHASE 7 begin with those two artifacts already written and committed. When the user authorizes a matching re-entry at the PHASE-7 human gate, the `grill-seed.json` written there is WIP-committed in that same matching arm. Each commit lands in the INSTALL repo only (never the wrapper-mode source/product repo) and is fail-soft (a git failure warns and `/devforge:grill` continues — the report is already written). The `[WIP]` commit folds into `/devforge:finalize`'s squash, so the final PR is unchanged.

### Intermediate scratch files (orchestrator-written, helper-consumed) — all under `$WORKDIR`

The helper cannot dispatch agents or call the codebase-memory-mcp (CBM) graph (a subprocess has no Task/MCP tools), so the orchestrator captures each verb's stdout to an intermediate scratch file that the next verb reads (most verbs take a `--<name> <path>` flag, not stdin). All live under `$WORKDIR` (`${TMPDIR:-/tmp}/forge-grill`) and are scratch state for one run — the whole directory is removed at the end (the single end-of-run `rm -rf "$WORKDIR"` at PHASE 7.3, reached on the clean arm and the human-gate arm alike). Because `$WORKDIR` is outside the work tree, the files need no leading dot and no gitignore handling. Several verbs print a DICT (e.g. `consume-tmp`'s `{status, findings}`) but the next verb's `--findings` requires a BARE ARRAY — those steps include a one-line `python3 -c` extraction (shown inline at each phase).

- `$WORKDIR/preflight.json` — the `preflight` stdout (`source_root`, `framework`, `language`, `wrapper_mode`, `feature_gate_ok`, …). Written in PHASE 0, read by the orchestrator for the `--source-root` / `--framework` values it threads into later verbs.
- `$WORKDIR/manifest.json` — the `resolve-scope` stdout (the static `GrillScopeManifest`: `feature_dir`, `feature_id`, `plan_path`, `spec_path`, `handoff_path`, `constitution_path`, `claude_md_path`). Written in PHASE 1, read by `render-brief --manifest`.
- `$WORKDIR/scope-block.txt` — the human-readable scope block the orchestrator extracts from the manifest for the refuter briefs. Written in PHASE 1, passed to every `render-verify-brief --scope-block` (that verb takes a pre-rendered scope-block FILE, not the manifest JSON).
- `$WORKDIR/tmp-devils-advocate-p<pass>.md` — ONE PER PASS (`<pass>` is `1` or `2`): that pass's adversary findings, written by the dispatched `devils-advocate` agent in PHASE 2 (that pass's brief `--tmp-path` names its own path, so the two passes cannot overwrite each other), consumed by `consume-tmp` in PHASE 3. Swept by the end-of-run `rm -rf "$WORKDIR"`.
- `$WORKDIR/parsed-devils-advocate-p<pass>.json` — `consume-tmp` stdout per pass (a DICT: `status` + `findings` array). Written + read in PHASE 3.
- `$WORKDIR/findings-devils-advocate-p<pass>.json` — the bare `findings` array extracted from that pass's `parsed-devils-advocate-p<pass>.json`. Written in PHASE 3, read by `validate-findings --findings`.
- `$WORKDIR/validated-devils-advocate-p<pass>.json` — `validate-findings` stdout per pass (`passed` + `discarded` + `discard_counts`). Written + read in PHASE 3.
- `$WORKDIR/validated-p<pass>.json` — one POOL file per pass: that pass's validated `passed` findings as ONE bare array. Written in PHASE 3, read by `merge-passes --pools` (the two pools are passed positionally, `p1` first).
- `$WORKDIR/merged.json` — `merge-passes` stdout: the BARE merged working array unioning both pass pools. Written in PHASE 3, read by `route-refutation --findings` and `apply-verdicts --findings` in PHASE 4. This is the working list, and it REPLACES the single-pass file a reader may expect — there is no `$WORKDIR/validated.json` in a `/devforge:grill` run.
- `$WORKDIR/refutation-routes.json` — `route-refutation` stdout (a list of `{refuter, findings}` cross-examination groups assigning each finding a non-author refuter). Written in PHASE 4, read by the orchestrator to drive the per-group `render-verify-brief` + refuter-dispatch loop.
- `$WORKDIR/refute-<refuter>.json` — one refuter group's bare-array `findings` subset, extracted by the orchestrator from `refutation-routes.json`. Written + read per refuter in PHASE 4, passed to `render-verify-brief --findings`.
- `$WORKDIR/verdicts-<refuter>.md` — per-refuter raw markdown verdicts, written by each dispatched refuter in PHASE 4 (the `render-verify-brief` `--tmp-path` names this exact path), consumed by `consume-verdicts --verdicts` in the same phase. Swept by the end-of-run `rm -rf "$WORKDIR"`.
- `$WORKDIR/parsed-verdicts-<refuter>.json` — `consume-verdicts` stdout per refuter (a DICT: `status` + a `verdicts` array). Written + read per refuter in PHASE 4; its `.verdicts` array is extracted and concatenated into `verdicts.json`.
- `$WORKDIR/verdicts.json` — every refuter's `parsed-verdicts-<refuter>.json` `verdicts` array concatenated into ONE bare array. Written in PHASE 4, read by `apply-verdicts --verdicts`.
- `$WORKDIR/partition.json` — `apply-verdicts` stdout (a DICT: `confirmed` + `dismissed` + `uncertain` + `contested` buckets, with `contested` already `[CONTESTED]`-tagged). Written in PHASE 4, read by `render-report --partition` in PHASE 6.

## Reference files

Read `references/refutation-preamble.md` in full at PHASE 4 (it is the refuter brief text, injected verbatim by `render-verify-brief`). The two adversary references — `anti-relitigation-preamble.md` and `design-attack-checklist.md` — are read and injected by the `render-brief` verb itself; the orchestrator does NOT read or paraphrase them. `report-format.md` documents the report skeleton the helper produces (orientation only; the helper owns the actual render).

- `references/anti-relitigation-preamble.md` — the design-grill scope-discipline preamble (PHASE 2, the adversary; injected by `render-brief`). Bars relitigation of settled upstream decisions and states the "does fixing it destroy the plan?" upstream-routing test.
- `references/design-attack-checklist.md` — the design-level attack vectors + what to quote as Evidence for each (PHASE 2, the adversary; injected by `render-brief`). The `## Finding N` output contract itself is owned by `render-brief`, not this file.
- `references/refutation-preamble.md` — the REFUTATION / cross-examination preamble + the per-finding verdict output contract (PHASE 4, every refuter). Load-bearing prompt text — `render-verify-brief` injects it verbatim into each refuter brief; do not paraphrase, summarize, or templatize it.
- `references/report-format.md` — the report skeleton `render-report` produces (orientation for PHASE 6; the helper owns the actual render).

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/grill_helper <verb> ...`. Each verb prints JSON (or a rendered block) to stdout. Most verbs that consume a prior verb's output take a `--<name> <path>` flag (not stdin), so capture stdout to the named `$WORKDIR/*.json` scratch file with `>` and pass that path into the next call — the per-phase fences below show the exact redirects. Re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-grill"` at the top of every Bash block that touches scratch (the variable does not survive across Bash calls — see PHASE 0). On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns file structure, validation, and atomic writes; the orchestrator owns the adversary/refuter dispatch, the CBM-graph traversal that the adversary performs (not the helper), the verbatim prompt text, user-facing prose, and phase pacing.

## PHASE 0 — Preflight + feature resolution

Cheapest guards first; preflight before any feature work. `/devforge:grill` runs on the user's say-so — typed, or agreed to when a blocked `/devforge:breakdown` offers it — and no command starts it on its own initiative; this preflight confirms the setup chain completed and the target feature has both a `spec.md` and a `plan.md`.

### 0.1 — Resolve the feature directory

Resolve the feature dir from `$ARGUMENTS`:

- When `$ARGUMENTS` names a feature directory or a `plan.md` inside one, use that feature directory (strip a trailing `plan.md` filename to its parent directory). Take the path the user typed as-is — do not re-shape it and do not check what it is made of.
- When `$ARGUMENTS` is empty, auto-resolve the feature directory whose `plan.md` was modified most recently — the feature most likely just finished `/devforge:plan`. (PHASE 1's `resolve-scope` performs this auto-detection — so when `$ARGUMENTS` is empty you may leave the feature unresolved here and let `resolve-scope --feature` auto-detect it, then carry forward the `feature_dir` it returns.)

Carry the resolved feature dir forward as `<feature_dir>` — every subsequent `--feature` / `--feature-dir` flag takes it. (When the feature was left for `resolve-scope` to auto-detect, set `<feature_dir>` from the manifest's `feature_dir` after PHASE 1.)

### 0.2 — Preflight gate

```bash
.devforge/lib/grill_helper preflight --workspace-root . --feature-dir <feature> > /tmp/grill-preflight-check.json
```

`preflight` checks the 4-command setup chain (`/devforge:init-forge → /devforge:generate-docs → /devforge:configure → /devforge:constitute`), the populated-constitution guard, AND the feature gate (the target `<feature>` has BOTH `spec.md` and `plan.md` — the required preconditions for `/devforge:grill`, which runs between `/devforge:plan` and `/devforge:breakdown`). It ALWAYS writes its JSON context block to stdout BEFORE any gate check, then exits **2** with a user-facing stderr message when (a) a setup-chain artefact is missing, (b) `constitution.md` is absent or still carries an unpopulated sentinel, or (c) the feature is missing `spec.md` or `plan.md`. On exit 2, copy the helper's stderr VERBATIM as a fenced code block and end the turn — the user runs the named missing command first (`/devforge:specify` then `/devforge:plan` for a missing feature artefact). On exit 0, the stdout JSON carries `source_root` (the project's Source Root — `.` for a standalone install, the inner project subdir in wrapper mode), `framework`, `language`, and `wrapper_mode`. (`$WORKDIR` is not established until 0.3, so this gate call captures to a fixed `/tmp` path; 0.3 re-runs `preflight` into `$WORKDIR/preflight.json` once the scratch dir exists. `preflight` is read-only and cheap, so running it twice is harmless.) Carry `source_root` and `framework` forward: PHASE 4 passes `source_root` to `render-verify-brief --source-root`, and PHASE 6 passes both to `render-report`.

When `$ARGUMENTS` was empty and the feature was left for `resolve-scope` to auto-detect, you cannot pass `--feature-dir` here yet; in that case omit `--feature-dir` (the feature gate is skipped for this call), run the setup-chain + constitution gate, and re-run `preflight --feature-dir <feature>` once PHASE 1 has resolved the feature, before dispatching the adversary in PHASE 2.

### 0.3 — Initialize run state + scratch dir

This sub-phase only establishes `$WORKDIR` and re-runs preflight into it — it does NOT advance the phase counter (PHASE 1 below opens with the `check-status-and-flip --to scope` boundary advance). The phase counter is advanced by `check-status-and-flip`, which writes `<feature_dir>/grill-state.json` to the named phase so an interrupted run can report where it stopped: call it ONCE at the start of each major phase with `--feature-dir <feature_dir> --to <phase>` (`scope`, `attack`, `validate`, `refute`, `classify`, `report`), and once at the very end of PHASE 6 with `--to report --status complete`. Keep these lightweight (one call per boundary, no parsing of the output beyond the non-zero-exit check). `--to` accepts any label, so these phase names are a convention, not a helper-enforced enum. (Note: the grill state verb keys on `--feature-dir`, NOT `--workspace-root` — its state file is per-feature, not per-workspace.)

Establish + clear the scratch working directory:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"
```

**All intermediate scratch for this run lives in `$WORKDIR` (the fixed literal `${TMPDIR:-/tmp}/forge-grill`), OUTSIDE the repo.** The literal is `forge-grill`, NOT `forge-audit` or `forge-review` — `/devforge:audit` or `/devforge:review` may run concurrently, and a shared workdir would corrupt both runs. `$WORKDIR` is outside the work tree, so the scratch files need no leading dot, no gitignore handling, and no per-file `rm` list. The `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"` clears any stale scratch from a prior crashed run.

**CRITICAL — `$WORKDIR` is a FIXED LITERAL you re-derive in every Bash block; it does NOT persist across calls.** The orchestrator runs each Bash tool call in a FRESH shell, so shell variables (including `$WORKDIR`) do NOT carry from one Bash call to the next. So every Bash block that touches scratch MUST begin by re-establishing `WORKDIR="${TMPDIR:-/tmp}/forge-grill"` and then reference `"$WORKDIR/..."`. The literal is identical in every block, so each block reconstructs the same directory.

Now re-capture the preflight context into `$WORKDIR` so later blocks can re-read its `source_root` / `framework` values (the gate already passed in 0.2; this just persists the context to the scratch dir):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper preflight --workspace-root . --feature-dir <feature> > "$WORKDIR/preflight.json"
```

### 0.4 — Model advisory (printed, never gating)

This step prints one line and does nothing else: it asks no question, it gates nothing, and the user is free to ignore what it says. Every arm above that carries the run forward reaches it.

`/devforge:grill` does its judgment work in the `think` tier. Read `CLAUDE_TIER_THINK` from `.devforge/project-config.json` for that tier's configured model. When the file is absent, or that key is absent or `null`, print `not configured` — the tier has no configured model, so this command carries no model override and its turn runs on the session's own model, and `.devforge/lib/configure_helper apply-models` writes `inherit` onto that tier's agents (that verb is named here for provenance and is NOT invoked by this step). For the second half of the line, name the model this session runs on as your own environment states it; when your environment states none, write the literal `unknown` rather than guessing one.

Surface one line to the user: `"This command's judgment work belongs to the think tier; configured think model: <value>; this session runs on: <session model, or unknown>."`

What the line recommends is a tier, resolved through this install's own `/devforge:configure` answers, so it tracks the user's choice and names no model version. Then proceed to PHASE 1.

## PHASE 1 — Resolve scope (static manifest)

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to scope
```

Resolve the target `plan.md` and assemble the STATIC path manifest the adversary attacks against. This resolves the target ONLY — it does NOT compute the three-ring codebase blast radius. A Python helper cannot call the CBM graph (the same constraint that makes `/devforge:audit`'s ORCHESTRATOR drive the MCP while its helpers only consume the scratch chain); the three-ring blast-radius traversal therefore belongs to the ATTACK step (PHASE 2), performed by the `devils-advocate` agent which holds the CBM graph tools, NOT to `resolve-scope`.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper resolve-scope --feature <feature> --workspace-root . > "$WORKDIR/manifest.json"
```

`resolve-scope` resolves the feature (an explicit feature directory or `plan.md` path via `--feature`, else auto-detects the feature directory whose `plan.md` was modified most recently) and emits the `GrillScopeManifest` JSON to stdout; the `>` redirect captures it to `$WORKDIR/manifest.json`. Stdout JSON carries `feature_dir`, `feature_id`, `plan_path`, `spec_path` (both required and existence-checked), `handoff_path` (the upstream specify handoff if present, else `null`), `constitution_path`, and `claude_md_path` — the existence-checked paths the adversary will read directly (the helper does NOT read file CONTENTS; the agent reads them). On a non-zero exit (feature not found, missing `plan.md` / `spec.md`), copy the helper's stderr VERBATIM and end the turn. When PHASE 0 left the feature for auto-detection, set `<feature>` from the manifest's `feature_dir` now and re-run the PHASE-0.2 `preflight --feature-dir <feature>` gate before dispatching.

Extract the human-readable scope block into its own file — the refuter briefs (PHASE 4) take a pre-rendered scope-block FILE via `--scope-block`, not the manifest JSON. The scope block is a short plain-text summary of what is under attack (the feature id + the plan/spec paths):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
python3 -c "import json; m=json.load(open('$WORKDIR/manifest.json')); open('$WORKDIR/scope-block.txt','w').write('Feature: {0}\nplan.md: {1}\nspec.md: {2}\n'.format(m['feature_id'], m['plan_path'], m['spec_path']))"
```

Carry the manifest's `feature_dir` forward as `<feature>` (every later `--feature` flag takes it) and note `plan_path` + `spec_path` for the PHASE-6 `--scope-files` count (the static manifest scopes the plan + its referenced specs, so the scope-file count is small — pass `2` unless the manifest later grows a file list).

## PHASE 2 — Attack (dispatch the adversary)

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to attack
```

`/devforge:grill` dispatches a SINGLE adversary AGENT — `devils-advocate` — NOT a multi-finder ensemble, and it dispatches that one agent TWICE: two independent passes over an identical brief, whose validated findings PHASE 3 unions into one working list. Two passes is one agent run twice, not two agents — the ensemble is unchanged, and the recall the second pass buys comes from the agent's own nondeterminism. The architect is NOT in the ensemble: it authored the design, and by charter it is an OPTIMIZER / decision authority that "decides HOW" and owns the final call, not an adversary chartered to attack the design it chose. The adversary reads the artifacts the manifest names AND resolves the three-ring codebase blast radius ITSELF via its CBM graph tools — the command does NOT pre-traverse the codebase.

### 2.1 — Adversary-existence check

The adversary agent is present when `.claude/agents/devils-advocate.md` exists. If it is ABSENT, tell the user how to restore it and end the turn — `/devforge:grill` cannot run without its single finder (there is no graceful-degradation fallback; the adversary IS the command). `update.sh` restores the agent only when it was never installed in this project; a `devils-advocate.md` deleted after it was installed comes back from `install.sh` (which regenerates every agent, and also overwrites `.claude/settings.json`) or from hand-copying the file into `.claude/agents/`. When present, carry `devils-advocate` forward as the single present finder — it is the author passed into PHASE 4's `route-refutation --finders` (alongside the refuters PHASE 4.0 determines) and the lone finder PHASE 6 passes to `render-report --finders`.

### 2.2 — Build the adversary brief

Render the brief ONCE PER PASS — the two calls are identical except for `--tmp-path`:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper render-brief --manifest "$WORKDIR/manifest.json" --references-dir .devforge/command-refs/grill --tmp-path "$WORKDIR/tmp-devils-advocate-p1.md"
.devforge/lib/grill_helper render-brief --manifest "$WORKDIR/manifest.json" --references-dir .devforge/command-refs/grill --tmp-path "$WORKDIR/tmp-devils-advocate-p2.md"
```

**The brief TEXT is IDENTICAL across the two passes** — only `--tmp-path` differs, so each pass writes to its own file. Do NOT reword, re-order, or re-tune the second pass's brief, and do NOT pass different `--ring1-cap` / `--finding-cap` values to the two calls: the second pass exists to re-run the SAME attack with a different generation, and a varied prompt would make the two passes incomparable instead of independent.

`render-brief` reads `$WORKDIR/manifest.json` and the two reference files under `--references-dir` (`.devforge/command-refs/grill` — the installed location): `anti-relitigation-preamble.md` and `design-attack-checklist.md`. `--tmp-path PATH` sets the EXACT path the brief tells the adversary to write its findings to; pass that pass's `"$WORKDIR/tmp-devils-advocate-p<pass>.md"` so the temp lands in `$WORKDIR` (outside the repo). It assembles the brief in this order: the anti-relitigation preamble, the design-level attack checklist, the read-context block (the manifest paths), the three-ring blast-radius traversal instruction (carrying the Ring-1 cap default), the output contract (the `## Finding N` field shape, with the finding cap substituted), and the closing reminder (the Bash-write command + grounding rule). Optional `--ring1-cap N` (default 15) and `--finding-cap N` (default 30) tune the traversal cap and finding budget — leave them unset to use the defaults baked into the helper (and leave them unset for BOTH passes). Pass each pass's rendered brief as that pass's Task tool PROMPT. Do NOT save the brief to an extra file; pass the brief text straight to the Task prompt. Dispatching with `subagent_type: devils-advocate` ALREADY loads the adversary's persona (`.claude/agents/devils-advocate.md`) as the subagent's system context — so do NOT prepend or re-inline the persona file into the brief; the brief carries only the grill-specific instructions on top of it.

**Known pitfalls from prior sessions (prepend, when there are any).** Alongside the fields 0.2 names, the `preflight` stdout re-captured at `$WORKDIR/preflight.json` carries `memory_present` (bool) and `memory_excerpt` (the populated `## ` sections of `.devforge/memory.md`, the project's persistent cross-session lessons file, with `## Task Outcomes` excluded and every section that has no entries under its heading dropped). Read `memory_excerpt` from that file and pick out the entries bearing on the area this plan changes (the plan's File Impact table names it). When there are any, PREPEND them to EACH pass's rendered brief as a short, clearly-labelled block — the SAME block in both, per 2.2's identical-brief rule — before passing each as its Task prompt; prepend, never append, so the closing reminder stays the brief's last instruction. A design that already failed here once is the sharpest ammunition an adversary can be handed, and it is the one thing the adversary cannot derive from `plan.md`, the graph, or the web. **Honesty bound.** A memory entry is an UNVERIFIED prior-session assertion, not evidence, and this is the command where over-trusting one is most costly: `/devforge:grill` recommends a disposition up to KILL. An entry is a hypothesis to ATTACK and ground like any other — never a confirmed defect, never a finding on its own, and never a substitute for reading `plan.md` and the Ring-0/Ring-1 code. The code it describes may have changed since it was written, or the entry may have been wrong then. PHASE 3's `validate-findings` grounding gate and PHASE 4's refutation pass apply to a memory-seeded attack exactly as to any other: an attack whose only support is a memory entry is discarded ungrounded. When `memory_present` is false or `memory_excerpt` is empty — the shipped stub carries no entries under its headings, so it renders as an empty excerpt — prepend nothing and say nothing to the user about memory; a project with no recorded lessons is the ordinary state of a fresh install, not a fault to remedy.

### 2.3 — Dispatch the adversary

Dispatch TWO Task calls with `subagent_type: devils-advocate` — one per pass, each carrying that pass's rendered brief as the prompt — as a BATCH in a SINGLE turn (the same batch shape PHASE 4.2 uses for the refuter groups), and wait for both before PHASE 3. The passes are independent and write to different temp paths, so dispatching them together costs one wait instead of two and cannot corrupt either file. Each dispatched adversary then, on its own:

- **Reads the design artifacts** the manifest names — `plan.md` (the HOW under attack), `spec.md` (the WHAT — TRACE context so a grounded attack can be attributed to the upstream stage that introduced it), the recon dossier (`handoff_path`, if present), and `constitution.md`.
- **Resolves the three-ring codebase blast radius via its CBM graph tools** (the command does NOT pre-traverse): **Ring 0** (read in full) — the existing files the plan's File Impact table declares it will MODIFY, plus their tests; **Ring 1** (read in full, ONE hop, CAPPED at the brief's Ring-1 default) — the direct callers/callees of Ring-0 files via `trace_path`, with a Ring-0 hub EXCEEDING the cap read at its highest-centrality slice and the large fan-out EMITTED as a finding (never silently dropped); **Ring 2** (QUERY only, NOT read into context) — the whole repo via `search_graph` / `search_code` / `get_architecture`, pulling only the specific `get_code_snippet` a hit points to (this is how duplicate-by-new-file and layer/boundary violations get grounded WITHOUT reading the repo). Read NARROW (Ring 0 + one hop), query WIDE (Ring 2).
- **Self-gated web-verification** — fires ONLY when the plan names an external dependency (library / version / API / pattern); a pure-internal-logic plan skips it automatically. The adversary VERIFIES the plan's claim against current docs via `context7` (with `WebFetch` / `WebSearch` only for CVEs/advisories context7 does not cover). VERIFY the claim, do NOT re-DISCOVER alternatives — a "better option exists" hit routes upstream (a `/devforge:discover` re-entry signal), it is not adopted into the plan.

The adversary is read-only and carries `Bash` (not `Write`), so it writes its findings to its OWN pass's `$WORKDIR/tmp-devils-advocate-p<pass>.md` (the `--tmp-path` its brief carried) via Bash shell redirection (the closing reminder in the brief gives the exact `cat > … << 'EOF'` command) in the fixed parseable `## Finding N` format the output contract specifies — and writes `# Status: failed` + a `# Reason:` line on partial failure, or `# Finding count: 0` when it finds nothing. The two passes are judged independently in PHASE 3: one pass failing does not abandon the run. The orchestrator does NOT dispatch CBM or context7 calls on the adversary's behalf — the adversary holds those tools and runs them inside its own Task turn.

## PHASE 3 — Validate (the grounding gate) + union the two passes

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to validate
```

Parse EACH pass's findings, extract its `findings` array, then validate that array against the actual source to discard ungrounded attacks. Run this three-step chain ONCE PER PASS, substituting `<pass>` with `1` and then `2` — every path in it carries that pass's `-p<pass>` suffix, so the two passes never overwrite each other:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper consume-tmp --tmp "$WORKDIR/tmp-devils-advocate-p<pass>.md" --agent devils-advocate > "$WORKDIR/parsed-devils-advocate-p<pass>.json"
# Extract the .findings array from the parsed dict into a bare JSON array:
python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/parsed-devils-advocate-p<pass>.json'))['findings']))" > "$WORKDIR/findings-devils-advocate-p<pass>.json"
.devforge/lib/grill_helper validate-findings --findings "$WORKDIR/findings-devils-advocate-p<pass>.json" --repo-root . > "$WORKDIR/validated-devils-advocate-p<pass>.json"
```

`consume-tmp` reads ONE pass's adversary temp file (`--tmp`) and regex-parses it into a result dict with `status` (`complete` / `clean` / `failed` / `missing`) and a `findings` array. `validate-findings` requires a BARE JSON array of finding dicts (it rejects a dict with exit 2), so extract `.findings` from the parsed dict first — the `python3 -c` line above does that. When ONE pass's `status` is `failed` or `missing`, note the reason for the report and treat THAT pass's findings list as empty — its pool below is `[]` and the union simply carries the other pass's findings. A single failed pass never abandons the run. `validate-findings` runs the anti-hallucination guard — file exists, line in range, evidence non-empty, pattern present, evidence quote grounded — and emits a `passed` array (the findings that survived) plus a `discard_counts` tally. `Finding.file` is polymorphic — it holds `plan.md`, `spec.md`, the constitution path, OR a real source file in the Ring-0/Ring-1 blast radius — and the SAME validator validates them all because all of those resolve under `source_root`. (`--repo-root .` is the repo root for resolving relative paths. Pass `--source-root <rel>` ONLY when the project's Source Root is a SUBDIRECTORY of the repo — e.g. `--source-root src` — so the validator resolves finding paths against it; for a standalone `source_root == "."` install, omit `--source-root`.) A web-only attack (no `source_root` file, Evidence = a re-fetchable citation) carries its grounding in the citation rather than a verbatim source quote — the refutation pass (PHASE 4) judges it on the captured citation.

**Record the STRONGER of the two pass statuses.** Rank the four values `complete` > `clean` > `failed` > `missing` and carry the higher-ranked of the two forward as `<adversary-status>` — PHASE 6 persists it with `check-status-and-flip --adversary-status`. A union that received real findings from EITHER pass did receive adversarial review, so one pass returning `failed` does not erase the other's result: `complete` + `failed` records `complete`, `clean` + `missing` records `clean`, and only two non-running passes record `failed` or `missing`. Decide this value here, where both statuses are in hand; do not re-derive it at PHASE 6.

Extract EACH pass's validated `passed` array into that pass's pool file (once per pass, same `<pass>` substitution as above):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/validated-devils-advocate-p<pass>.json')).get('passed', [])))" > "$WORKDIR/validated-p<pass>.json"
```

Then UNION the two pools into the single working list:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper merge-passes --pools "$WORKDIR/validated-p1.json" "$WORKDIR/validated-p2.json" > "$WORKDIR/merged.json"
```

`merge-passes` takes EXACTLY two pool paths and their ORDER is significant — the first is pass A, the second pass B. It prints the merged BARE array to stdout (captured to `$WORKDIR/merged.json`): all of pass A's findings first, in order, then every pass-B finding whose `(file, line, pattern)` identity pass A did not already carry. On a non-zero exit (a missing, unreadable, or malformed pool file), copy the helper's stderr VERBATIM and end the turn.

**This is a UNION, not a quorum.** A finding that only ONE pass produced MUST survive into the working list — catching an attack line that fired on one generation and not the other is the entire reason the adversary runs twice. Never require a finding to appear in BOTH passes, and never reimplement `/devforge:spec-check`'s majority rule here: a reproduce-across-passes rule would discard exactly the findings the second pass exists to catch. The only thing this merge removes is an exact `(file, line, pattern)` duplicate of a finding pass A already contributed.

`$WORKDIR/merged.json` is the working list the refutation pass (PHASE 4) reads. **If it is an empty array `[]`** (neither pass produced a grounded attack), there is nothing to refute or classify: SKIP PHASE 4 entirely (do not call `route-refutation`), write an empty partition to `$WORKDIR/partition.json` yourself, set the disposition to PROCEED (no surviving attack threatens the design), and proceed to PHASE 6 with an empty refuters list:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
printf '%s' '{"confirmed": [], "dismissed": [], "uncertain": [], "contested": []}' > "$WORKDIR/partition.json"
```

In the PHASE-6 `render-report` call, pass `--refuters ""` (no refuter ran), `--finders-skipped ""` (PHASE 4.0 was skipped along with the rest of PHASE 4, so no refuter was found absent — nothing was consulted because there was nothing to refute; note that refuter INSTALLATION was therefore never CHECKED on this branch, since 4.0 is where that check lives, so the report's "Finders skipped" line renders empty as a record that nothing was checked, NOT as a claim that every refuter is installed), `--disposition PROCEED`, and a `--rationale` stating the adversary found no grounded design defect. The report then renders a clean, no-findings grill with a PROCEED disposition. The empty partition this branch writes is CLEAN by the definition PHASE 6's `render-report` ack returns, so this branch reaches PHASE 7's clean arm through the SAME `"clean": true` value every other run is judged by — read the ack there as usual; do not shortcut PHASE 6 or PHASE 7 from here.

## PHASE 4 — Refute (cross-examination)

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to refute
```

Refutation runs ONCE on the merged working list, AFTER validation and BEFORE classification — **one cross-examination pass over the UNION of both adversary passes, never one refutation per adversary pass.** Refuting each pass separately would triple the run's dispatch cost instead of doubling it, and would produce two partitions nothing reconciles; unioning first is exactly what makes a single refutation sufficient. Its job is to invert the default from "assume a defect" to "assume correct unless proven": each finding is cross-examined by a non-author refuter whose default verdict is NOT-a-defect, and only the survivors flow to the classification + report. The refuters are the architect-EXCLUDED priority `[code-reviewer, qa-reviewer, security-reviewer]` — the architect is NEVER a refuter (it authored the design and must judge neither the attacks on it nor the refutation). Read `references/refutation-preamble.md` in full now — it is the refuter brief text and the verdict output contract, injected verbatim by `render-verify-brief`.

The steps below are a per-refuter dispatch loop, opened by a present-refuter determination.

### 4.0 — Determine the present refuters

`route-refutation` can only SELECT a refuter that is passed to it in `--finders`; the priority list `[code-reviewer, qa-reviewer, security-reviewer]` only RANKS among the agents passed, it does not make any of them present. So before routing, determine which refuters are installed: for EACH agent in the architect-excluded priority order `[code-reviewer, qa-reviewer, security-reviewer]`, test whether `.claude/agents/<name>.md` exists (the same presence test PHASE 2.1 uses for `devils-advocate`). Build two comma-lists from the result — `<present-refuters>` (the installed ones, in priority order) and `<skipped-refuters>` (the absent ones). These three are plan-15 standard core reviewers and are normally all installed, so `<skipped-refuters>` is normally empty. Carry both lists forward: 4.1 passes `<present-refuters>` into `route-refutation --finders`, and PHASE 6 passes `<skipped-refuters>` into `render-report --finders-skipped`.

### 4.1 — Route each finding to a non-author refuter

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper route-refutation --findings "$WORKDIR/merged.json" --finders "devils-advocate,<present-refuters>" > "$WORKDIR/refutation-routes.json"
```

`route-refutation` selects a refuter for each finding from the agents passed in `--finders`, choosing the FIRST in the architect-excluded priority order `[code-reviewer, qa-reviewer, security-reviewer]` that is present in `--finders` AND is not the finding's author. `devils-advocate` is passed because it is the author — the `!= author` rule then excludes it from refuting its own findings; the present refuters (4.0's `<present-refuters>`) must be passed too or none can be selected and the finding falls back to author self-refutation. The architect is never passed and never a refuter. Because `<present-refuters>` is passed in `--finders` alongside `devils-advocate`, the author (`devils-advocate`) is in the pool but never chosen (excluded by the `!= author` rule), and `code-reviewer` — first in the priority list — receives all findings when it is present. Stdout (captured to `$WORKDIR/refutation-routes.json`) is a list of `{refuter, findings}` groups — each group is one refuter and the bare-array subset of findings routed to it. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

### 4.2 — Dispatch each refuter over its routed subset, in batches

For each `{refuter, findings}` group, write that group's `findings` subset to a scratch file (a one-line `python3 -c` extraction from `$WORKDIR/refutation-routes.json`) and render that refuter's brief over its assigned subset:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper render-verify-brief --findings "$WORKDIR/refute-<refuter>.json" --refuter <refuter> --references-dir .devforge/command-refs/grill --scope-block "$WORKDIR/scope-block.txt" --source-root <source-root> --tmp-path "$WORKDIR/verdicts-<refuter>.md"
```

`render-verify-brief` assembles the refuter prompt — the refutation preamble (read verbatim from `references/refutation-preamble.md` under `--references-dir`, the installed location) plus the assigned findings to cross-examine — reading the pre-rendered scope block from `$WORKDIR/scope-block.txt` (PHASE 1). `--tmp-path` sets the EXACT path the brief tells the refuter to write its verdicts to; pass `"$WORKDIR/verdicts-<refuter>.md"`. Substitute `<source-root>` with the `source_root` from `$WORKDIR/preflight.json` (PHASE 0). Pass the rendered brief as the Task tool PROMPT. Dispatching with `subagent_type: <refuter>` ALREADY loads that refuter's persona — so do NOT prepend or re-inline the persona; the refutation preamble in the brief carries only the cross-examination instructions on top of it. The brief instructs the refuter to write its fixed-format `## Verdict N` markdown to `$WORKDIR/verdicts-<refuter>.md` via Bash shell redirection (the refuter is a read-only reviewer carrying `Bash`, so it writes the file via redirection — no Write tool needed). **Dispatch the refuter groups in batches** (multiple Task calls in a single turn, wait for the batch before the next); do not fan out all refuter groups at once. Each refuter judges ONLY its routed findings (a bounded set), not the whole working list. On a non-zero `render-verify-brief` exit, copy the helper's stderr VERBATIM and end the turn.

### 4.3 — Parse each refuter's verdicts, then merge

For each refuter dispatched, parse its verdict file into a verdict array, then concatenate all refuters' parsed arrays into one bare array:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper consume-verdicts --verdicts "$WORKDIR/verdicts-<refuter>.md" --refuter <refuter> > "$WORKDIR/parsed-verdicts-<refuter>.json"
# After every refuter is parsed, extract each .verdicts array and concatenate into ONE bare array:
python3 -c "import json,glob; out=[]; [out.extend(json.load(open(p)).get('verdicts',[])) for p in sorted(glob.glob('$WORKDIR/parsed-verdicts-*.json'))]; print(json.dumps(out))" > "$WORKDIR/verdicts.json"
```

`consume-verdicts` regex-parses one refuter's fixed-format markdown verdict file (the `## Verdict N` blocks the refutation contract specifies) into a DICT carrying `status` (`complete` / `failed` / `missing`) and a `verdicts` array. Pass `--refuter <refuter>` so a verdict missing the `# Refuter:` header is still attributed. The `python3 -c` line extracts each parsed dict's `.verdicts` array and concatenates every refuter's verdicts into `$WORKDIR/verdicts.json` — the merged verdict array `apply-verdicts` consumes. When a refuter's `status` is `failed` or `missing`, its `verdicts` array is empty so it contributes nothing to the merge; `apply-verdicts` handles an unjudged finding per its own contract. On a non-zero `consume-verdicts` exit, copy the helper's stderr VERBATIM and end the turn.

### 4.4 — Apply the verdicts and partition

Partition the FULL working list against the merged verdicts:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper apply-verdicts --findings "$WORKDIR/merged.json" --verdicts "$WORKDIR/verdicts.json" > "$WORKDIR/partition.json"
```

`apply-verdicts` reads the SAME `$WORKDIR/merged.json` working list PHASE 4.1 routed (NOT a refutation-derived subset) and the merged verdicts, keys each verdict to its working-list finding by the `(file, line, pattern, agent)` tuple, and partitions category-aware per the D7 routing. It prints a DICT (captured to `$WORKDIR/partition.json`) with four buckets:

- `confirmed` — survivors the refuter demonstrated as genuine design defects; they earn the report headline.
- `dismissed` — the default verdict on undemonstrable findings (incl. relitigation the refuter knocked down); they go to the report's Dismissed / Worth-a-Glance appendix. (A dismissed `[CONSTITUTION-VIOLATION]` does NOT land here — see `contested`.)
- `uncertain` — a finding the refuter could not resolve that is NOT high-stakes (its category is not `security` AND it carries no `[CONSTITUTION-VIOLATION]` tag); it rides the Dismissed / Worth-a-Glance appendix.
- `contested` — HIGH-stakes findings the refuter could not confirm: a `security` finding or any `[CONSTITUTION-VIOLATION]` finding the refuter returned `uncertain` on, PLUS any `dismiss` verdict on a grounded `[CONSTITUTION-VIOLATION]`. `apply-verdicts` tags each `[CONTESTED]`. These are surfaced IN the report headline, flagged — never buried.

The helper owns the verdict→bucket partition and the category routing; the orchestrator does not re-derive verdicts. On a non-zero `apply-verdicts` exit, copy the helper's stderr VERBATIM and end the turn.

## PHASE 5 — Classify (the "destroys-the-plan?" test)

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to classify
```

This is ORCHESTRATOR REASONING, not a helper verb — there is no `classify` verb. Read the `confirmed` and `contested` buckets from `$WORKDIR/partition.json` (the surviving grounded findings). For a finding heading toward RE-ENTER-UPSTREAM, Q2's YES arm names two additional inputs — the feature's intake handoffs, read where they sit in the feature directory (they are not in the manifest and no scratch file carries them). For EACH surviving grounded finding, apply the two-question decision tree:

- **Q1 — "Does a different HOW (a re-plan against the SAME spec) fix the defect?"**
  - YES → **REVISE-PLAN** (plan-local — fixing it leaves the plan intact; a different HOW satisfies the same WHAT).
  - NO (no HOW survives the fix — this is what "destroys the plan" means) → go to Q2.
- **Q2 — "Would a corrected WHAT or grounding (re-`/devforge:specify` / re-`/devforge:discover` / re-`/devforge:research`) yield a viable design?"**
  - YES → **RE-ENTER-UPSTREAM** — attributed to the NEAREST introducing stage (trace via `spec.md` + the dossier: a bad requirement already in the research handoff → `research`; introduced at discovery → `discovery`; introduced at `/devforge:specify` → `spec`; nearest-stage-first, NOT a blanket rewind to research). The trace does not stop at `spec.md` and the dossier: `<feature_dir>/research-handoff.json` (the `research` stage's own artifact) and `<feature_dir>/discover-handoff.json` (`discovery`'s) are MANDATORY trace inputs where present — opened and read, not optional context. Where a conclusion was WRITTEN is not where it was INTRODUCED: when the invalidated conclusion's SUBSTANCE — a requirement's content, a caller row, a surface label — is already present in one of those handoffs, the introducing stage is that handoff's stage, and `spec` is the introducing stage ONLY when the conclusion has no upstream source. The `rationale` for a RE-ENTER-UPSTREAM NAMES the introducing artifact and the matching content found in it — an attribution naming no introducing artifact is a guess.
  - NO (nothing rescues it — the feature is infeasible, unjustified, or should be bought not built) → **KILL**.

PROCEED is the no-surviving-attack / all-accepted-as-risk case — outside this YES/NO tree (the empty-`merged.json` branch in PHASE 3 already routes there; reach it here too when every survivor is accepted as risk).

Synthesize ONE recommended disposition for the whole run (the most severe survivor's routing wins: KILL > RE-ENTER-UPSTREAM > REVISE-PLAN > PROCEED) plus a `rationale` paragraph naming the surviving findings that drove it. For a **RE-ENTER-UPSTREAM** OR a **REVISE-PLAN** disposition, ALSO compose the re-entry-seed inputs PHASE 7's matching re-entry arm needs for its `write-seed` call (the seed is written only if the user picks the matching re-entry at the human gate):

- `target_stage` — the SEED TOKEN, NOT the slash-command name. For RE-ENTER-UPSTREAM it is the nearest upstream stage `spec` | `discovery` | `research`; for REVISE-PLAN it is `plan`. `write-seed --target-stage` accepts all four (`spec` | `discovery` | `research` | `plan`); it rejects any other value with exit 2.
- `prior_conclusion` — for RE-ENTER-UPSTREAM, what that upstream stage concluded that is now invalidated; for REVISE-PLAN, the flawed plan decision the revision must replace.
- `invalidating_evidence` — the grounded grill finding that invalidates it.
- `must_satisfy` — for RE-ENTER-UPSTREAM, what the re-run must additionally satisfy; for REVISE-PLAN, the fix the revised plan must meet.
- `cycle_count` — the bounded-compounding-loop counter (1 for a first grill, incremented when this run itself re-entered from a prior seed).
- `carried_findings` — prior findings carried forward, monotonic (empty on a first grill; for REVISE-PLAN, the remaining confirmed findings the revision must address).
- `provenance` — a pointer to this `<feature_dir>/grill.md` / the plan path.

Carry the disposition + rationale forward to PHASE 6 (the report), and carry the seed inputs (for RE-ENTER-UPSTREAM or REVISE-PLAN) forward to PHASE 7's matching re-entry arm — that arm writes the seed only if the user's pick matches the recommendation.

## PHASE 6 — Report

Open the phase and record this run's two audit fields in the SAME state write:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
PLAN_SHA256="$(python3 -c "import hashlib,json; p=json.load(open('$WORKDIR/manifest.json'))['plan_path']; print(hashlib.sha256(open(p,'rb').read()).hexdigest())")"
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to report --adversary-status <adversary-status> --plan-sha256 "$PLAN_SHA256"
```

This one call does three things in a single write to `grill-state.json`: it flips the phase to `report`, records `<adversary-status>` (the stronger-of-the-two value PHASE 3 decided — `complete` | `clean` | `failed` | `missing`; the helper rejects any other string with exit 2), and records the sha256 hex digest of the `plan.md` this run actually attacked (`--plan-sha256` takes exactly 64 hex characters, and the helper rejects any other shape with exit 2). The `python3 -c` line computes that digest over `plan_path`'s raw bytes, read from the PHASE-1 manifest — the manifest's paths are absolute, so it resolves regardless of the shell's directory. Both fields land BEFORE this phase's artifact commit below, so the committed `grill-state.json` carries them. Omitting either flag leaves the corresponding stored field UNCHANGED rather than blanking it, which is why the `--status complete` call at the end of this phase does not repeat them.

**The plan hash is RECORDED, never compared.** Nothing re-hashes `plan.md`, nothing reads this value back, and no phase branches on it. It exists so that a human reading `grill-state.json` can tell a report about the CURRENT plan from one about a plan that has since been rewritten. Do not build a freshness check on it, and do not describe it as one. `adversary_status` is likewise a record of what happened — it says whether the adversary actually ran, which is a different question from the session-lifecycle `status` field that the `--status complete` call sets (both fields can hold the string `complete` and mean unrelated things). **The word `clean` collides in the same way and shares no meaning across the two uses:** as an `adversary_status` VALUE it means one pass ran and reported zero raw findings, while the `render-report` ack's `clean` BOOLEAN means the final partition has no confirmed, contested, or uncertain survivor. They routinely disagree — a `complete` pass whose findings are every one of them dismissed yields ack `clean: true` while `adversary_status` is never `"clean"`. PHASE 7 branches on the ACK BOOLEAN and on nothing else.

Capture today's date, then render the report from the partition + the PHASE-5 disposition:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
DATE="$(date +%Y-%m-%d)"
.devforge/lib/grill_helper render-report --partition "$WORKDIR/partition.json" --feature <feature> --date "$DATE" --finders "devils-advocate" --finders-skipped "<skipped-refuters>" --refuters "<refuters-csv>" --source-root <source-root> --framework "<framework>" --scope-files <file-count> --disposition <DISPOSITION> --rationale "<rationale>"
```

`render-report` reads `$WORKDIR/partition.json` (the four buckets from PHASE 4) directly and renders the full grill markdown (skeleton documented in `references/report-format.md`), writing it to `<feature_dir>/grill.md` via an atomic write, OVERWRITING any prior `grill.md` (idempotent). The flags:

- `--partition "$WORKDIR/partition.json"` — the apply-verdicts buckets.
- `--feature <feature>` — the resolved feature dir; `grill.md` is written here.
- `--date "$DATE"` — `YYYY-MM-DD` (required for deterministic output; the helper never calls the clock).
- `--finders "devils-advocate"` — the single finder invoked.
- `--finders-skipped "<skipped-refuters>"` — in `/devforge:grill`, refuters are the only non-adversary agents, so the shared `--finders-skipped` flag (a report-labeling flag inherited from `/devforge:audit` + `/devforge:review`, where the report's "finders" ARE the refuter pool) carries them — the `<skipped-refuters>` comma-list PHASE 4.0 built: the refuter agents (code-reviewer / qa-reviewer / security-reviewer) the 4.0 presence check found ABSENT (no `.claude/agents/<name>.md`); the helper renders them on the report's "Finders skipped (not installed): …" line. This is normally empty — the refuters are plan-15 standard core reviewers normally all installed — so pass `""` when 4.0 found none skipped.
- `--refuters "<refuters-csv>"` — the refuter agents that actually ran: the distinct `refuter` values read from `$WORKDIR/refutation-routes.json`, comma-separated. In the normal grill case this is the same set as `<present-refuters>` (every present refuter is non-author and receives at least one finding when findings exist), but read it from the routes file rather than reusing `<present-refuters>` directly. Pass `""` when no refuter ran (the empty-`merged.json` branch).
- `--source-root <source-root>` — the Source Root from `$WORKDIR/preflight.json`.
- `--framework "<framework>"` — the Framework / Language from `$WORKDIR/preflight.json`.
- `--scope-files <file-count>` — the plan-scope file count (the static manifest scopes the plan + its referenced specs; pass `2` for the plan + spec).
- `--disposition <DISPOSITION>` — the PHASE-5 disposition: `PROCEED` | `REVISE-PLAN` | `RE-ENTER-UPSTREAM` | `KILL` (required, non-empty).
- `--rationale "<rationale>"` — the PHASE-5 rationale (required, non-empty).
- `--re-entry-target <stage>` — pass ONLY when `--disposition RE-ENTER-UPSTREAM`: the nearest stage `spec` | `discovery` | `research`. It MUST be absent for every other disposition (the helper rejects a non-RE-ENTER-UPSTREAM disposition that carries a `--re-entry-target`).

`render-report` validates the disposition (exit 2 on a bad value, or on a `--re-entry-target` that is missing for RE-ENTER-UPSTREAM or present for another disposition). The report leads with CONFIRMED findings (a force-ranked Top Priorities list + a by-file/by-category grouped listing), surfaces high-stakes `[CONTESTED]` findings IN that headline flagged, drops dismissed + low-stakes uncertain findings to a `## Dismissed / Worth a Glance` appendix, and renders the `## Disposition` section. Stdout is a JSON ack `{path, confirmed, contested, dismissed, uncertain, clean}`; the `path` is the written `<feature_dir>/grill.md`. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

**Read the ack's `clean` boolean and carry it forward — it decides whether PHASE 7 consults a human at all.** It is `true` exactly when the `confirmed`, `contested`, AND `uncertain` buckets are all empty; a non-empty `dismissed` bucket does NOT make a run non-clean, because a dismissed finding is precisely one that did not survive refutation and so asks nothing of anybody. The helper computes it from the same partition it just rendered, so take the value as given: do NOT re-derive it in prose from the four bucket counts, and do NOT infer it from the disposition — a PROCEED run whose `uncertain` bucket is non-empty is NOT clean, and its human gate still fires.

**WIP-commit the grill report artifacts.** Now that `grill.md` is written, commit `/devforge:grill`'s own report outputs so the work is git-safe at this step. Run this UNCONDITIONALLY (every `/devforge:grill` run reaches here with a written `grill.md`). `grill-state.json` is always included — it lives in `<feature_dir>` and is part of what this run wrote. The seed (`grill-seed.json`) is NOT committed here — it is not written until the PHASE-7 human gate, and only when the user authorizes a matching re-entry; that arm commits it itself.

Use the feature directory's own name — the last segment of `<feature_dir>`, which PHASE 1's manifest already reports as `feature_id`, called `<feature-dir-name>` below — for the commit label. `commit-artifacts` takes an absolute `--paths` entry and a repo-relative one alike, so pass `<feature_dir>` in the form PHASE 1 resolved it and re-shape nothing:

```bash
.devforge/lib/artifact_helper commit-artifacts --paths '["<feature_dir>/grill.md", "<feature_dir>/grill-state.json"]' --label 'grill: <feature-dir-name>'
```

`commit-artifacts` stages ONLY the named paths and makes a `[WIP] grill: <feature-dir-name>` commit in the INSTALL repo (never the wrapper-mode source/product repo). It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the report is already written, so note the warning and CONTINUE; do NOT end the turn); "nothing to commit" (paths already staged or absent) exits 0 silently as a benign no-op. The `[WIP]` commit folds into `/devforge:finalize`'s squash, leaving the final PR unchanged.

Then mark the run complete so an interrupted re-run can distinguish a finished grill from a stopped one:

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to report --status complete
```

## PHASE 7 — Disposition (a clean run ends here; otherwise the user owns the verdict)

**PHASE 7 is ENTERED on EVERY run.** Which arm it takes is decided by the `clean` boolean in PHASE 6's `render-report` ack — read that value, never re-derive it. Both arms end in the same scratch sweep (7.3), and both begin with `grill.md` + `grill-state.json` already written and already put through PHASE 6's fail-soft artifact commit.

### 7.1 — Clean run (`"clean": true`) — present the result, ask nothing

The adversary ran and nothing it produced survived cross-examination: no confirmed finding, no contested one, none left unresolved. There is nothing for a human to decide here, so **ask NO question**: do NOT open 7.2's human gate, do not fire its question tool, and capture no pick. Instead:

- Tell the user that the adversary ran and that NO finding survived cross-examination, and name the written report `<feature_dir>/grill.md`. Say it in those terms: never call the plan sound, proven, validated, or safe. A clean grill is the ABSENCE of a surviving attack, not evidence that the design is correct — and two passes license no stronger claim than one did. When PHASE 3 recorded `failed` or `missing` for one of the two passes, say THAT in the same breath: a clean result from a run where half the attack never landed is a weaker result, and reporting it bare would overstate it.
- Name `/devforge:breakdown` as the next command.
- Write NO seed. `write-seed` runs only inside a matching re-entry arm in 7.2, and this arm enters none — so no `grill-seed.json` is written and 7.2's seed commit does not run. (A clean partition left PHASE 5 no surviving finding to classify, so the recommendation it synthesized is PROCEED.)
- Then run 7.3's sweep and end the turn.

### 7.2 — Non-clean run (`"clean": false`) — the human gate

At least one finding is confirmed, contested, or unresolved, so the user decides what happens to it. The disposition is a RECOMMENDATION; the human makes the final call. Present the recommended disposition + its rationale (print the report's `## Disposition` block, or summarize it), tell the user `<feature_dir>/grill.md` was written, and capture the user's choice via AskUserQuestion so the next step is explicit:

> The grill recommends a disposition for this plan. What do you want to do?

Options (2–4; AskUserQuestion auto-injects "Other"):

- `Proceed` — accept the findings as they stand and run `/devforge:breakdown`.
- `Revise plan` — re-run `/devforge:plan` or hand-patch `plan.md`, then optionally re-run `/devforge:grill`.
- `Re-enter upstream` — re-run the named upstream command (`/devforge:specify`, `/devforge:discover`, or `/devforge:research`).
- `Kill` — stop; the design is fatally flawed (re-run `/devforge:plan` with a wholly different approach).

(Always offer `Proceed` and `Kill` as the outer brackets, and `Revise plan` as an always-available choice (recommended when the disposition is REVISE-PLAN). Omit `Re-enter upstream` when the disposition is not RE-ENTER-UPSTREAM — it is only meaningful when the PHASE-5 disposition routed to an upstream stage.) Then act on the choice:

- **Proceed** → tell the user the next command is `/devforge:breakdown`. Write no seed.
- **Revise plan** → two cases, by whether this matches the recommendation:
  - **Matching (the recommendation was REVISE-PLAN)** → NOW write the re-entry seed from the PHASE-5 seed inputs, targeting `plan`, then WIP-commit it (see the seed-write + commit block below; pass `--target-stage plan`). Then tell the user to re-run `/devforge:plan`, which will detect and consume the emitted `grill-seed.json` (`target_stage="plan"`) so the revision is directed at the grill's confirmed findings, not a repeat (or hand-patch `plan.md`), then optionally re-`/devforge:grill`.
  - **Cross-pick (the recommendation was NOT REVISE-PLAN)** → write NO seed. Tell the user to re-run `/devforge:plan` manually (an undirected revision — there is no seed to consume) or hand-patch `plan.md`, then optionally re-`/devforge:grill`.
- **Re-enter upstream** → this option is offered only when the recommendation was RE-ENTER-UPSTREAM, so it is matching by construction. NOW write the re-entry seed from the PHASE-5 seed inputs, targeting the PHASE-5 nearest upstream stage (`spec` | `discovery` | `research`), then WIP-commit it (see the seed-write + commit block below; pass `--target-stage <stage>`). Then tell the user to re-run the named upstream command, which will detect and consume `grill-seed.json` so the re-run is directed, not a repeat. **Bounded loop:** after 2 kill→re-propose / re-entry cycles on the same feature (the seed's `cycle_count`), escalate to the user — "this feature may be intractable as framed — decide" — rather than looping again.
- **Kill** → stop; the design is abandoned. The recovery is a wholly new design via re-run `/devforge:plan`. Write no seed.

**Every branch above then continues to 7.3** — `Proceed`, BOTH `Revise plan` cases, `Re-enter upstream`, and `Kill` alike. In the two matching re-entry arms, the seed-write + commit block below runs inline first, as part of that arm's action. NONE of these bullets ends the turn on its own: the arm finishes its action, 7.3 sweeps the scratch, and only then does the turn end. `Kill` stops the DESIGN, not the run.

**Seed-write + commit block (7.2's matching re-entry arms only).** Run this ONLY inside the matching `Revise plan` or `Re-enter upstream` arm above — never for `Proceed`, `Kill`, or a cross-pick, and never on 7.1's clean arm (which enters no arm at all). `<stage>` is the arm's target stage: `plan` for a matching REVISE-PLAN, or the PHASE-5 nearest upstream stage (`spec` | `discovery` | `research`) for RE-ENTER-UPSTREAM. First write the seed:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
# <stage> is per-arm: `plan` for a matching Revise plan, or the upstream stage for Re-enter upstream.
.devforge/lib/grill_helper write-seed --feature <feature_dir> --target-stage <stage> --prior-conclusion "<prior-conclusion>" --invalidating-evidence "<invalidating-evidence>" --must-satisfy "<must-satisfy>" --cycle-count <N> --carried-findings "<carried-csv>" --provenance "<feature_dir>/grill.md"
```

`write-seed` builds a `ReEntrySeed` from the PHASE-5 seed inputs and writes `<feature_dir>/grill-seed.json` via an atomic write. `--target-stage` (`spec` | `discovery` | `research` | `plan`), `--prior-conclusion`, `--invalidating-evidence`, `--must-satisfy`, and `--provenance` are all REQUIRED and non-empty (the schema rejects an empty value with exit 2). `--cycle-count` is an int ≥ 1 (default 1; increment when this run itself re-entered from a prior seed). `--carried-findings` is a comma-separated list of prior finding descriptions carried forward (monotonic compounding; may be empty). Stdout is a JSON ack `{path}`. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

Then WIP-commit the seed so it is git-safe (mirrors the PHASE-6 report commit — install-repo-only, fail-soft):

```bash
.devforge/lib/artifact_helper commit-artifacts --paths '["<feature_dir>/grill-seed.json"]' --label 'grill-seed: <feature-dir-name>'
```

`<feature-dir-name>` is the last segment of `<feature_dir>`, the same value PHASE 6's report commit labelled with (PHASE 1's manifest reports it as `feature_id`). `commit-artifacts` stages ONLY the named path and makes a `[WIP] grill-seed: <feature-dir-name>` commit in the INSTALL repo (never the wrapper-mode source/product repo). It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the seed is already written, so note the warning and CONTINUE; do NOT end the turn); "nothing to commit" exits 0 silently as a benign no-op. The `[WIP]` commit folds into `/devforge:finalize`'s squash, leaving the final PR unchanged.

### 7.3 — Sweep the scratch (BOTH arms)

Reached from 7.1 and from 7.2 alike — `render-report` was the last reader of `$WORKDIR/partition.json`, so on either arm nothing else needs the scratch:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
rm -rf "$WORKDIR"
```

This is the run's ONLY sweep (PHASE 0.3's `rm -rf` clears stale scratch at the START, before its `mkdir -p`). `$WORKDIR` is the FIXED literal `${TMPDIR:-/tmp}/forge-grill`, so scratch left behind here does not pile up visibly — it silently persists until the NEXT `/devforge:grill` run clears it, and one run's leftovers sit beside the next run's files. That is why the clean arm ENTERS PHASE 7 and ends AFTER this sweep, rather than skipping the phase.

## Important rules

1. **Mandatory to RUN, never binding in its VERDICT** — `/devforge:breakdown` refuses to decompose a plan until `/devforge:grill` has run for it, so every feature pays exactly one grill. That entry gate reads the PRESENCE of `<feature_dir>/grill.md` plus the adversary status recorded in `grill-state.json`, and NOTHING else: never the disposition (a KILL report satisfies it exactly as a PROCEED one does) and never freshness (a report written against a since-edited `plan.md` still passes; no re-run is ever forced). `/devforge:grill` runs only on the user's say-so — typed, or agreed to when a blocked `/devforge:breakdown` offers it — and one agreement covers one command: the offer is made, the grill runs on the user's yes, and re-running `/devforge:breakdown` is proposed afterwards as its own step, never chained on that same yes. `/devforge:plan`'s non-blocking advisory hint is unchanged: it may suggest a grill for a high-stakes plan, and it neither runs `/devforge:grill` nor gates anything. **What being mandatory did NOT change:** the USER owns every non-clean verdict at PHASE 7, all four dispositions survive (KILL included), the cross-pick and re-entry arms are untouched, and `/devforge:grill` never modifies `plan.md` or `spec.md`.
2. **The architect is absent** — it authored the design, so it is excluded from BOTH the attacker ensemble (the single finder is `devils-advocate`) AND the refuter priority list (`[code-reviewer, qa-reviewer, security-reviewer]`). The proposer never judges attacks on its own design.
3. **Read narrow, query wide, verify-not-rediscover** — the adversary reads Ring 0 + one-hop Ring 1, QUERIES Ring 2 (reading the whole codebase is `/devforge:audit`, OUT), and its web step VERIFIES the plan's claims (a "better option" hit routes upstream, it is not adopted).
4. **Evidence-first** — every finding must be grounded in a verbatim quote from the real plan / spec / dossier / code / constitution (or a re-fetchable web citation for a web claim); `validate-findings` discards ungrounded ones, and the refutation pass cross-examines each survivor before it reaches the headline.
5. **No relitigation** — the adversary attacks the CHOSEN design's demonstrable defects, not its taste; a "I would have built it differently" objection is dismissed by the refutation pass. A grounded defect inherited from upstream routes RE-ENTER-UPSTREAM, it does not become a plan attack.
6. **Constitution violations are always Critical** — never downgraded, regardless of confidence; a `[CONSTITUTION-VIOLATION]` the refuter dismissed is surfaced `[CONTESTED]` in the headline, never buried.
7. **The disposition is a RECOMMENDATION** — `/devforge:grill` recommends PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL; the human owns the final call at the `/devforge:breakdown` approval gate. The backward re-entry loop is bounded (escalate to the human after the cap). The human is ASKED only on a NON-CLEAN run: when nothing was confirmed, contested, or left unresolved, PHASE 7.1 presents the result and ends without a question — the human still owns the call at the `/devforge:breakdown` gate, now holding the report instead of a prompt.
8. **Read-only on source** — no source modifications, no fixes to the plan or spec. `/devforge:grill` does WIP-commit its OWN artifacts via `artifact_helper commit-artifacts` — `grill.md` + `grill-state.json` at the end of PHASE 6 on EVERY run, and `grill-seed.json` in PHASE 7.2's matching re-entry arm when the user authorizes it — install-repo-only, fail-soft `[WIP]` commits that fold into `/devforge:finalize`'s squash; it never commits source or modifies the plan/spec.
9. **Wrapper-mode aware** — the adversary reads source files from the resolved Source Root (`source_root` from `preflight`); `<feature_dir>` always resolves under the workspace root, never the nested source root.
10. **Cleanup is last** — all intermediate scratch lives in `$WORKDIR` (`${TMPDIR:-/tmp}/forge-grill`), outside the repo, and is swept by the single `rm -rf "$WORKDIR"` at the end of PHASE 7 (7.3), never mid-run. PHASE 7 is entered on BOTH arms, so a clean run reaches that sweep exactly as a gated one does — the clean arm ends the turn AFTER the sweep, never instead of it.
11. **Two passes, ONE union, ONE refutation** — the `devils-advocate` adversary is dispatched TWICE over an identical brief, and the two passes' validated findings are UNIONED (`merge-passes`) into one working list before refutation. A finding produced by only ONE pass survives that union; this is not a quorum and must never become one. Refutation then runs ONCE over the union, never once per pass.
```