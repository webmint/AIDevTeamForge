# 37 — PER-STEP ARTIFACT COMMIT PLAN

**Status:** NOT STARTED — decisions drafted, awaiting Phase-0 sign-off. On `develop-2.0-init`. **SUPERSEDES `33-FINALIZE-STAGES-SPEC-ARTIFACTS-PLAN.md`** (its D1 finalize-only + D6 inline-git calls — see "Supersedes plan 33" below).

The spec-driven pipeline currently NEVER git-commits most of a feature's planning artifacts the moment they are produced — `spec.md`, `plan.md`, the `*-handoff.json` files, `grill.md`/`grill-seed.json`, `review.md`, `verification.md`, the `*-state.json` run-state files, and the repo-root `research/`/`discover/` reports + handoffs all accumulate UNTRACKED in the working tree until `/finalize`. A user hit this in a real consumer install (mintEnvoy 2026-06-23): interrupting the pipeline mid-stream or running `git clean -fdx` silently loses all of that work. This plan makes each command WIP-commit its OWN artifacts (markdown AND `.json` handoffs AND state files) the moment it produces them, so work is git-safe at every step — not just at the terminal command. Every per-step `[WIP]` commit folds into `/finalize`'s existing `git reset --soft` squash, so the FINAL PR is byte-identical to today; the only thing that changes is WHEN work becomes git-safe (throughout the pipeline, not just at the end). Scope is a single new shared, tested helper verb plus one per-step call site in each of the eight commands that today commit nothing, plus a retained `/finalize` safety-net.

## Supersedes plan 33

`33-FINALIZE-STAGES-SPEC-ARTIFACTS-PLAN.md` chose a **finalize-only** fix (D1) implemented as an **inline git step, not a helper verb** (D6): a single unconditional `git add specs/<feature>/` + `[WIP]` commit added to `/finalize` PHASE 2 before the squash. That approach left every artifact UNTRACKED for the whole feature lifecycle — the exact gap the user now wants closed mid-pipeline. This plan REVERSES both of those calls:

- **33 D1 (finalize-only) → 37 D1 + the per-step commit map:** every command commits its own artifacts the moment it writes them, not just `/finalize`.
- **33 D6 (inline git, not a verb) → 37 D1 (a shared, tested helper verb):** 33 chose inline because it was ONE call site; with ~8 NEW call sites (plus the retained `/finalize` safety-net), DRY mandates a single shared verb (a per-spec inline copy would be 9 hand-copied git blocks that drift).

33's ONE surviving idea — an UNCONDITIONAL `/finalize` safety-net `git add specs/<feature>/` + `[WIP]` commit before the squash, install-repo-only in wrapper mode — is CARRIED FORWARD into this plan as D4 / Phase 10 (a belt-and-suspenders catch for any artifact a fail-soft per-step commit skipped). 33's D2 (whole-directory scope), D3 (runtime state excluded), D4 (wrapper install-repo-only), and D5 (unconditional, before the squash) are all preserved as the shape of that safety-net.

Phase 11 marks plan 33 SUPERSEDED in its own file + the repo-root `CLAUDE.md` plan list, and adds a 37 entry.

## Context for next session

The investigation is DONE; the following are VERIFIED facts (read against the live tree this session — re-verify any line number before citing it in a `#### Verify` block; line numbers drift). A fresh session needs no re-investigation.

### Who commits what across the pipeline today (verified this session by reading the helpers + plan 33's verified investigation)

- **`/implement` ALREADY commits, per task, per-path** (`src/devforge/lib/_implement/_cmds_commit.py`): source code (`touched_files`) + — **in STANDALONE mode only** — the current task file + `tasks/README.md` (the `index`). It explicitly NEVER uses `git add -A` (a deliberate per-path safety rule — `_cmds_commit.py:39,96-97`). **The standalone-vs-wrapper split matters for Phase 7:** in STANDALONE mode `_cmds_commit.py:527-534` stages `touched + [task_file, index]` together; in WRAPPER mode `_cmds_commit.py:515-526` stages ONLY the source `touched_files` in the SOURCE repo — the task file and `tasks/README.md` are WRAPPER artifacts (they live in the install/wrapper root) and are left UNCOMMITTED by `/implement`'s wrapper path (`mark-complete` writes them to disk but they are never staged). It does NOT commit the parent `spec.md`/`plan.md`, and **this plan does NOT change that** — under per-step commits each command owns ONLY its own artifact; `/specify` commits `spec.md`, `/plan` commits `plan.md`, `/implement` keeps committing code (+ task files in standalone mode). `/implement` is UNCHANGED by this plan.
- **`/summarize` ALREADY `[WIP]`-commits `summary.md`** (plan 24 — it makes a `[WIP]` commit that `/finalize` squashes). UNCHANGED by this plan.
- **All of `/research`, `/discover`, `/specify`, `/plan`, `/grill`, `/breakdown`, `/review`, `/verify` contain ZERO `git add` today** — verified by grep across their helper subpackages in plan 33 (0 matches for `git add` across `src/devforge/lib/{_specify,_plan,_breakdown,_research,_discover,_review,_verify}/`; `/grill`'s `_grill/` likewise has none). These EIGHT commands are the NEW commit sites this plan adds (Phases 2–9).

### Why the per-step `[WIP]` commits are SAFE (produce an identical PR)

`/finalize` PHASE 3 squash is `git reset --soft <base>` + `git commit` (`src/devforge/lib/_finalize/_squash.py` — `_git_reset_soft` near `:521`). `git reset --soft` re-commits the entire COMMITTED `merge-base..HEAD` range as one commit — so every per-step `[WIP]` commit on the branch between the squash base and HEAD folds in automatically. The final history is one clean `feat(<feature>): <title>` commit, byte-identical to today's PR. The ONLY difference is that work is now git-safe at each step (recoverable after an interrupt or a `git clean`), instead of accumulating untracked until the terminal command. (Caveat for `research/`/`discover/` pre-feature commits: see D3 — they commit before a `specs/NNN` exists; if they land on the same branch after the eventual squash base they fold in; if a feature branch starts later they are a harmless separate WIP commit upstream.)

### The existing `wip-commit` verb is the safety-discipline template

`implement_helper wip-commit` (`_cmds_commit.py`) is the model the NEW verb mirrors for git discipline: it stages explicit paths only (`git add -- <path>`, NEVER `git add -A` — `_git_stage_path`, `:240-272`), uses `git -C <repo_root>` so it never changes the process cwd, bounds every git call with a 30 s subprocess timeout (`_GIT_TIMEOUT`), and resolves the install-vs-source split via `resolve_workspace` (`src/devforge/lib/_implement/_workspace.py` → `Workspace{install_root, source_root, is_wrapper}`, fail-soft to standalone). The NEW verb differs in three ways: (a) it targets `workspace.install_root` ALWAYS (never the source repo — D2), (b) it uses a plain `[WIP] <label>` message (no ticket-id, no attribution suppression logic — install-repo artifact commits are NOT the traceless product commits), and (c) a git failure is FAIL-SOFT (warn on stderr, return a non-fatal signal — it must NEVER block the calling command). The existing `wip-commit` targets the SOURCE repo for code in wrapper mode and is UNCHANGED by this plan.

### Wrapper-mode artifact root (D2 grounding)

In wrapper mode `specs/`, `research/`, `discover/`, `docs/`, and `constitution.md` all live in the INSTALL/wrapper root, NOT inside the nested product repo (verified — consumer `src/CLAUDE.md` Artifact Storage: *"Wrapper mode: All artifacts (`specs/`, `docs/`, `constitution.md`) live in the wrapper root, NOT inside `{{PROJECT_ROOT}}`"*). `resolve_workspace(install_root)` exposes `workspace.install_root` (the wrapper root) and `workspace.source_root` (the nested product repo). The NEW verb commits to `install_root` always; the SOURCE repo gets code commits only and stays traceless (`[TICKET-ID]`, no AI traces — plan 25 D5, a USER-CONFIRMED invariant). The existing `implement_helper wip-commit` already targets `source_root` for code in wrapper mode and is untouched.

### Install wiring for a standalone launcher (OQ1 grounding)

The full install copies EVERYTHING under `src/devforge/lib/` to `.devforge/lib/` via a single `cp -R "$TEMPLATE_DIR/src/devforge/." "$TARGET_DIR/.devforge/"` (`install.sh:197`; preserving the executable bit on launchers), so a standalone `artifact_helper{,.py}` launcher rides along automatically in a FULL install with NO `_PROMOTED` / command-dir association needed (`_PROMOTED` governs only which COMMANDS the emitter promotes — `scripts/emitters/claude.py:51` — not which lib launchers ship). The surgical `--only <cmd>` mode (`install.sh:96-161`), by contrast, is keyed to a command name (`_${cmd_u}/` + `${cmd_u}_helper`), so a shared `artifact_helper` not tied to a command name would NOT be delivered by `--only <cmd>` unless homed under `_shared/` (which `--only` always copies, `install.sh:135-141`). This is the concrete tradeoff OQ1 weighs (single launcher = trivial full-install ride, but surgical-delivery needs a thought; verb-in-`_shared` = surgical-delivered free but needs per-helper `_cli` registration). Resolve in Phase 1.

## Decisions (RATIFIED recommendations — confirm in Phase 0)

These are the user's accepted recommendations. They still get a Phase-0 sign-off gate because the mechanism touches plan-25 settled `/finalize` design (the safety-net rides in `/finalize` PHASE 2) and supersedes plan-33 settled calls.

### D1 — MECHANISM: a SHARED, TESTED helper verb, NOT inline git per spec

A single new verb (working name `commit-artifacts`) that:

- Takes `--paths <json-array>` (the explicit artifact paths to stage) + `--label <str>` (the WIP message label) + `--root <path>` (the install root, defaults to cwd). **`--paths` items may be FILE OR DIRECTORY paths** — each is passed to `git -C <install_root> add -- <path>` unchanged (git handles both: a directory path stages all tracked-modified + untracked files under it, identical to `git add <dir>`). This is what lets the D4 safety-net pass a single `specs/<feature>/` directory. An absent or empty path is a benign no-op (the path-absent skip in the fail-soft bullet below), not a failure.
- Resolves the workspace via `resolve_workspace(--root)` (the SAME `src/devforge/lib/_implement/_workspace.py` resolver `wip-commit` uses).
- Stages ONLY the explicitly named paths (`git add -- <path>` per path, NEVER `git add -A`) in the INSTALL repo (`workspace.install_root`).
- Commits with message `[WIP] <label>`.
- Is FAIL-SOFT: a git failure (staging or commit) warns on stderr and returns a non-fatal signal — it must NEVER block the command that called it, because committing an artifact is a SAFETY NET, not the command's job (the command already did its real work: it wrote the artifact). A "nothing to commit" (no staged delta) is also a benign no-op, not a failure.

**Why a verb, not inline git (REVERSES plan 33 D6):** 33 chose inline because it was ONE call site. This plan has ~8 NEW call sites plus the `/finalize` safety-net — DRY mandates a single shared, tested verb so the git discipline (explicit paths, `git -C`, timeout, fail-soft, install-root targeting) lives in tested Python once, not hand-copied across 9 spec files where it would drift.

**OQ1 (verb home) is OPEN, not decided here.** Lean recommendation: a single new launcher `artifact_helper{,.py}` under `src/devforge/lib/` mirroring the existing `audit_helper`/`review_helper`/`summarize_helper` launcher-shim pattern (a 2-dozen-line shim that puts the lib dir on `sys.path` and dispatches to a `_artifact/_cli.py` `main()`), exposing the one verb, installed the same way the other `*_helper` launchers ship (the full-install `cp -R`). The alternative is adding the verb to `_shared/` and registering it in each consuming command helper's `_cli`. Phase 1 RESOLVES this; do NOT pick it unilaterally.

### D2 — WRAPPER SPLIT: the artifact verb commits to the INSTALL repo ONLY, never the source/product repo

In wrapper mode `specs/`, `research/`, `discover/`, `docs/`, `constitution.md` live in the INSTALL/wrapper root (verified — see Context "Wrapper-mode artifact root"). The artifact verb targets `workspace.install_root` ALWAYS. The SOURCE (product) repo gets code commits only and must stay traceless (`[TICKET-ID]`, no AI traces — plan 25 D5, USER-CONFIRMED). The existing `implement_helper wip-commit` already targets the SOURCE repo for code in wrapper mode and is UNCHANGED. **State the contrast explicitly so a future session never points the artifact verb at `source_root`.** Pointing it at the source repo would both put forge artifacts into the product repo (wrong root) AND violate the traceless guarantee.

### D3 — research/discover INCLUDED

`/research` and `/discover` produce reports + handoffs that live OUTSIDE `specs/` (repo-root `research/YYYY-MM-DD-slug.md` + sibling `handoff.json`; `discover/YYYY-MM-DD-slug.md` + sibling `.handoff.json`) and run BEFORE a feature dir exists. Their artifacts are committed per-step too — the user's pain covers them. They commit to the INSTALL repo via the same verb. **Nuance:** these are pre-feature (no `specs/NNN` yet) but on the same branch, so they still fold into the eventual `/finalize` squash if they land after the squash merge-base; if a feature branch starts later, a pre-feature research/discover commit is a harmless separate WIP commit on the upstream branch. Do NOT over-engineer — a fail-soft per-step commit is the whole ask; this plan does NOT try to retroactively associate a research report with the feature it eventually seeds.

### D4 — /finalize SAFETY-NET RETAINED

Keep an UNCONDITIONAL `git add specs/<feature>/` + `[WIP]` commit in `/finalize` PHASE 2 before the squash (carried from plan 33 D2/D5), as a belt-and-suspenders catch for any artifact a fail-soft per-step commit skipped. **Zero-escape-hatch:** it ALWAYS runs (every feature reaching `/finalize` has a `specs/<feature>/`), install-repo-only in wrapper mode (plan 33 D4 — never `git -C <source_root>`), explicit path never `git add -A`. This is redundant with the per-step commits for the happy path but catches stragglers (a per-step commit that failed fail-soft, or an artifact written by a path the per-step map missed) — **that redundancy is deliberate, not an oversight; state so in the spec.** It reuses the new verb where it can (one call with `--paths '["specs/<feature>/"]'` + a `[WIP] finalize: artifact safety-net` label), so the wrapper install-repo-only guard is the verb's, not re-implemented inline (this is the one place the verb is called with a DIRECTORY path rather than a file list — the verb stages whatever git resolves under it, identical to `git add specs/<feature>/`).

## Open Questions (OQ-N — argued, recommended, ratify in Phase 0)

- **OQ1 — verb home: single new `artifact_helper` launcher vs verb-in-`_shared`-registered-per-helper.** Lean: single new `artifact_helper{,.py}` launcher (mirrors the existing `*_helper` shim pattern, one self-contained launcher, rides the full-install `cp -R` with no `_PROMOTED`/command association). The counter: a standalone launcher is NOT keyed to any command, so the surgical `--only <cmd>` install path (`install.sh:96-161`) would not deliver it for a single-command patch unless special-cased; a `_shared/` verb is surgical-delivered free (`--only` always copies `_shared/`) but needs registration in each consuming command's `_cli`. Recommendation: single launcher; address surgical-delivery by either (a) noting that artifact-commit changes ride a full install/update, or (b) teaching `--only` to also ship `artifact_helper` — decided in Phase 1 alongside the home. RESOLVE in Phase 1.
- **OQ2 — research/discover pre-feature commits: include (D3) vs defer.** Lean: include — the user's pain explicitly covers the repo-root `research/`/`discover/` reports + handoffs; they fold into the squash when on the same branch after the base, and a harmless separate upstream WIP commit otherwise. The counter: a pre-feature commit on a not-yet-branched trunk is a commit the user did not ask `/finalize` to squash. Recommendation: include (D3); the commit is fail-soft and the worst case is a recoverable extra commit, never lost work. RESOLVE in Phase 0.
- **OQ3 — verb label/message scheme: per-command `[WIP] <label>` vs a single generic `[WIP] forge artifacts`.** Lean: per-command label (e.g. `[WIP] spec: 003-foo`, `[WIP] plan: 003-foo`, `[WIP] review: 003-foo`) — readable WIP history before the squash erases it, so an interrupt-and-inspect shows which step's artifacts landed. The counter: the labels are erased by the squash anyway, so a generic label is simpler. Recommendation: per-command label — the readability is free and the squash makes the choice invisible in the final PR. RESOLVE in Phase 0.
- **OQ4 — does the `/finalize` D4 safety-net become pure-redundant once every step commits, and should it be dropped?** Lean: KEEP. Per-step commits are fail-soft (a git error warns + continues), so a step CAN skip its commit silently; the safety-net catches that straggler. Dropping it would reintroduce the "code ships with no spec tracked" failure on the fail-soft path — a zero-escape-hatch violation. Recommendation: KEEP and record the redundancy as deliberate (D4). RESOLVE in Phase 0.

## Out of scope (do NOT plan here)

- **Changing `/implement` or `/summarize`** — both already commit their own artifacts (code + task files; `summary.md`). Per-step commits are ADDED only to the eight commands that commit nothing today (D-context). `/implement`'s per-path `git add` safety rule is the template the new verb mirrors, not a thing this plan edits.
- **Committing artifacts into the source (product) repo in wrapper mode** — `specs/`/`research/`/`discover/` live in the install/wrapper root; the source repo stays traceless `[TICKET-ID]` (plan 25 D5; D2 is the guard).
- **Committing `.devforge/` runtime state** (`memory.md`, `session-state.md`, `cbm-last-indexed-sha`) — install-scoped, not feature-scoped; excluded exactly as in plan 33 D3. The per-step verb stages only the command's named artifact paths, never `.devforge/` state.
- **A back-fill / migration for already-orphaned artifacts in existing installs** — forward-fix only; a project mid-pipeline today with untracked artifacts must commit them manually. This plan adds NO migration step and a future session must NOT build one under it.
- **`git add -A` anywhere** — the verb stages explicit named paths only (matches `/implement`'s existing safety rule, `_cmds_commit.py:39,96-97`).
- **Making the per-step commit BLOCKING** — it is fail-soft by design (D1). Fail-soft means it never blocks the command; it does NOT mean the commit is optional/skippable by judgment. The verb is CALLED unconditionally at each site (zero-escape-hatch); only the git op inside it tolerates failure.

## The per-step commit map (the spine — one build phase per NEW commit site)

Each command WIP-commits its OWN outputs (md + json + state). Re-verify each command's actual artifact paths + the correct insertion point by READING the live `main.md` at build time — do NOT trust this table's paths blind; filenames and line numbers drift. The insertion point in each spec is near the END of the command's flow, AFTER the artifact is written + approved.

**Per-command run-state files are INCLUDED** (decided — no escape-hatch judgment call). The three per-feature commands that own a `<feature_dir>/<cmd>-state.json` run-state file — `/grill` (`grill-state.json`, `_grill/_state.py:31`), `/review` (`review-state.json`, `_review/_state.py:29`), `/verify` (`verify-state.json`, `_verify/_state.py:29`) — INCLUDE that state file in their own `--paths` (rows 6/8/9 above) so the per-step commit truly captures everything the command wrote under `specs/<feature>/`. This is the explicit, concrete replacement for the earlier vague "any verify state json" wording. The remaining commit-site commands have no `<cmd>-state.json`: `/research`/`/discover`/`/specify`/`/plan` carry no per-feature state file (their state, where any, is upstream-handoff JSON already in `--paths`), and `/breakdown` has no `*-state.json` at all (verified — `_breakdown/` has no `_state.py` state file), so nothing is added for them. The `*-state.json` files live in `specs/<feature>/` (NOT `.devforge/`), so committing them does NOT violate the `.devforge/` runtime-state exclusion (Out-of-scope / plan-33 D3 — those are `memory.md`/`session-state.md`/`cbm-last-indexed-sha`, all `.devforge/`-scoped and globally-shared, never feature-scoped).

| Phase | Command | Artifacts to commit (re-verify at build time) | Source spec file | Lean label |
|---|---|---|---|---|
| 2 | `/research` | `research/<date>-slug.md` + its `handoff.json` | `src/commands/research/main.md` | `[WIP] research: <slug>` |
| 3 | `/discover` | `discover/<date>-slug.md` + its `.handoff.json` | `src/commands/discover/main.md` | `[WIP] discover: <slug>` |
| 4 | `/specify` | `specs/NNN/spec.md` + `specs/NNN/handoff.json` | `src/commands/specify/main.md` | `[WIP] spec: NNN-slug` |
| 5 | `/plan` | `specs/NNN/plan.md` + `plan-handoff.json` (+ optional `data-model.md`, `contracts.md`) | `src/commands/plan/main.md` | `[WIP] plan: NNN-slug` |
| 6 | `/grill` | `specs/NNN/grill.md` + optional `grill-seed.json` + `specs/NNN/grill-state.json` | `src/commands/grill/main.md` | `[WIP] grill: NNN-slug` |
| 7 | `/breakdown` | `specs/NNN/tasks/*` + `tasks/README.md` + `breakdown-handoff.json` | `src/commands/breakdown/main.md` | `[WIP] breakdown: NNN-slug` |
| 8 | `/review` | `specs/NNN/review.md` + `specs/NNN/review-state.json` | `src/commands/review/main.md` | `[WIP] review: NNN-slug` |
| 9 | `/verify` | `specs/NNN/verification.md` + `specs/NNN/verify-state.json` | `src/commands/verify/main.md` | `[WIP] verify: NNN-slug` |

Each phase adds ONE step to its `main.md`: after the artifact is written + approved, call the new verb with the command's artifact paths (`--paths`) + the per-command label (`--label`). The orchestrator composes the JSON paths array (helper-owns-shape: the verb owns staging/commit shape; the orchestrator composes the path values from the run's known output filenames). Optional artifacts (`data-model.md`, `contracts.md`, `grill-seed.json`) are included in `--paths` only when the run wrote them — the orchestrator already knows which it wrote; the verb's "nothing to commit / path absent" no-op (D1) makes a path that was not written a benign skip if the orchestrator includes it anyway.

**Phase 7 (`/breakdown`) is NOT redundant in WRAPPER mode.** In standalone mode `/implement` already tracks the task files + `tasks/README.md` (it stages `touched + [task_file, index]`, `_cmds_commit.py:527-534`), so Phase 7's commit of `specs/NNN/tasks/*` + `tasks/README.md` mostly re-stages already-tracked files there (a harmless no-op for unchanged files; it still newly tracks `breakdown-handoff.json`). In WRAPPER mode, however, `/implement` stages ONLY source `touched_files` in the SOURCE repo (`_cmds_commit.py:515-526`) and leaves the task files + `tasks/README.md` UNCOMMITTED in the install/wrapper root — so **Phase 7 is the FIRST per-step commit that tracks the task files + `tasks/README.md` in the install repo**; before it, they are untracked. State this in Phase 7's DoD so a future session does not mistake Phase 7's commit for redundant.

## Phases (build order)

Each phase: objective, files touched, an execution agent-loop note, a `#### Verify` fenced bash block, and a `DoD:` line. Per repo discipline (`CLAUDE.md`): every command/spec `main.md` edit goes through **instruction-author → instruction-reviewer** AND is verified via the **claude-code-guide** agent BEFORE it lands (these files ship into a target project's `.claude/` — slash-command spec bodies). The NEW helper verb goes through **python-engineer → python-reviewer** with a REAL git-fixture test written + actually run in the SAME turn. This plan FILE is a repo-root plan and does NOT ship into `.claude/`, so writing it needs no claude-code-guide; every `main.md` edit it schedules DOES.

**Zero-escape-hatch:** no rule in any phase below contains an OR / if / except / unless / use-judgment carve-out. The per-step commit call is UNCONDITIONAL at each site; "fail-soft" governs only the git op INSIDE the verb (warn + continue), never whether the call is made. The wrapper guard is the verb's single `resolve_workspace` branch (install-root targeting — D2), never re-detected per spec. The path staged is always the explicit named `--paths` list (never `git add -A`).

### Phase 0 — Decisions ratified (gate on user sign-off)

**Objective:** confirm D1–D4 + resolve OQ1–OQ4 with the user before any edit, because the mechanism rides `/finalize` PHASE 2 (plan-25 settled design) and supersedes plan-33 settled D1/D6.

- **Files touched:** none (decision gate).
- **Execution:** present D1–D4 + OQ1–OQ4 + the supersede-33 call to the user; record the ratified decisions in this plan (flip any the user redirects). Confirm specifically: (a) D1 shared verb (not inline) + supersede 33 D6; (b) D1 + the per-step map (supersede 33 D1 finalize-only); (c) D2 install-repo-only wrapper split; (d) D3/OQ2 research/discover included; (e) D4/OQ4 `/finalize` safety-net retained as deliberate redundancy; (f) OQ1 verb home deferred to Phase 1; (g) OQ3 per-command label.

#### Verify

```bash
grep -n "RATIFIED\|USER-CONFIRMED" /Users/mykolakudlyk/Projects/ai-dev-team-forge/37-PER-STEP-ARTIFACT-COMMIT-PLAN.md   # expect: D1-D4 + OQ1-OQ4 marked ratified after sign-off
```

DoD: D1–D4 ratified (or flipped) + OQ1–OQ4 resolved with the user; the supersede-33 call is confirmed; OQ1 (verb home) is explicitly deferred to Phase 1; OQ4 (keep the safety-net) is settled with the redundancy recorded as deliberate; user sign-off obtained.

### Phase 1 — Build the shared `commit-artifacts` verb + launcher/install wiring

**Objective:** build the single new verb (D1) plus its home (OQ1) so all downstream phases have a stable `<launcher> commit-artifacts --paths <json> --label <str> --root <path>` interface to call.

- **Files touched (under the OQ1 lean — single launcher):** new `src/devforge/lib/_artifact/_cli.py` (+ any `_artifact/` modules the verb needs) + new launcher shim `src/devforge/lib/artifact_helper` + `src/devforge/lib/artifact_helper.py` (mirror the `summarize_helper.py` shim — put the lib dir on `sys.path`, dispatch to `_artifact._cli.main`) + `tests/lib/_artifact/`. If OQ1 instead picks `_shared/`: add the verb to `src/devforge/lib/_shared/` + register it in each consuming command helper's `_cli` (more wiring — Phase 1 resolves which).
- **The verb contract (mirror `wip-commit`'s git discipline, `_cmds_commit.py`):** parse `--paths` (JSON array) + `--label` + `--root`; `resolve_workspace(--root)` → `Workspace`; stage each path with `git -C <install_root> add -- <path>` (NEVER `git add -A`); `git -C <install_root> commit -m "[WIP] <label>"`; FAIL-SOFT — a staging or commit git failure warns on stderr and returns a non-fatal signal (the calling command must not be blocked); a no-staged-delta "nothing to commit" is a benign no-op; bound every git call with a subprocess timeout (mirror `_GIT_TIMEOUT = 30`). Target `workspace.install_root` ALWAYS — never `source_root` (D2).
- **TEST FIRST, in the same turn (REAL git fixture — round-trip, not hand-faked):** in a tmp git repo, assert the verb (1) stages the explicitly named untracked paths in the install repo and makes a `[WIP] <label>` commit containing EXACTLY those paths; (2) NEVER runs `git add -A` (an unrelated dirty file in the tree is NOT committed); (3) is FAIL-SOFT on a git error (e.g. a non-repo `--root`) — non-zero-but-non-fatal signal, no exception that would crash a caller; (4) the WRAPPER arm (a tmp install repo with a nested source repo + a `project-config.json` `PROJECT_ROOT` pointing at it) commits to `install_root`, NOT `source_root` (assert the source repo HEAD is unchanged); (5) **the D4 DIRECTORY-PATH arm** — called with a directory path (`specs/<feature>/`) stages all untracked files under it (equivalent to `git add specs/<feature>/`, still never `git add -A` — assert an unrelated dirty file OUTSIDE that directory is NOT committed) and an absent/empty path is a benign no-op (no exception). All arms (standalone, wrapper, directory-path) tested, written + run in the SAME turn.
- **Resolve OQ1 here:** pick the verb home + (if single launcher) decide whether the surgical `--only` path needs to also ship `artifact_helper` or whether artifact-commit changes ride a full install/update. Record the resolution in this plan.
- **Execution:** python-engineer → python-reviewer with the REAL git-fixture tests above written + run in the same turn.

#### Verify

```bash
cd /Users/mykolakudlyk/Projects/ai-dev-team-forge
python -m pytest tests/lib/_artifact/   # expect: green (verb tested vs a real git fixture — standalone + wrapper arms, never git add -A, fail-soft)
grep -rn "git add -A" src/devforge/lib/_artifact/   # expect: NO match (explicit paths only)
grep -rn "source_root" src/devforge/lib/_artifact/   # read: the verb targets install_root, never commits to source_root (D2)
ls -l src/devforge/lib/artifact_helper   # expect: present + executable (under the single-launcher OQ1 resolution)
```

DoD: the `commit-artifacts` verb exists at the OQ1-resolved home, stages explicit paths only (never `git add -A`), targets `install_root` always (D2), is fail-soft (a git failure never crashes a caller), and is tested against a REAL git fixture (standalone + wrapper arms, both written + run in the same turn) with python-reviewer applied; OQ1 (home + install wiring) is resolved + recorded.

### Phases 2–9 — add the per-step artifact-commit call to each NEW commit site

**Objective:** edit ONE `src/commands/<cmd>/main.md` per phase to add the per-step artifact-commit call from the per-step commit map. Each phase is INDIVIDUALLY verifiable; group them under this heading for readability, but each command's edit is its own instruction-author → instruction-reviewer + claude-code-guide unit and its own DoD.

Pipeline order: **Phase 2 `/research` · Phase 3 `/discover` · Phase 4 `/specify` · Phase 5 `/plan` · Phase 6 `/grill` · Phase 7 `/breakdown` · Phase 8 `/review` · Phase 9 `/verify`.**

For EACH phase:

- **Files touched:** ONLY that command's `src/commands/<cmd>/main.md` (per the table). No helper code (the verb shipped in Phase 1).
- **The edit:** at build time, READ the live `main.md` in full, locate where the command's artifact is written + approved (near the END of the flow), and add a step that calls the Phase-1 verb with that command's artifact paths (`--paths` — composed by the orchestrator from the run's known output filenames) + the per-command label (`--label`, from the map's "Lean label" column, OQ3-resolved). Re-verify the command's ACTUAL artifact filenames against the live spec — do NOT trust the map's paths blind. Optional artifacts (`data-model.md`/`contracts.md` for `/plan`; `grill-seed.json` for `/grill`) go in `--paths` only when the run wrote them; the verb's path-absent no-op (D1) makes an included-but-unwritten path a benign skip.
- **RECONCILE THE OUTPUTS SECTION (required, not optional — modeled on Phase 10's Outputs edit):** each command's `main.md` carries an "Outputs of this command" section (or equivalent) describing what it writes, and several state "Not committed, not staged" verbatim (e.g. `src/commands/grill/main.md:28` for `grill.md`). After this edit that claim is STALE/CONTRADICTORY. As part of the SAME `main.md` change, edit that section so it states the command now `[WIP]`-commits its OWN artifacts via the verb (install-repo-only, fail-soft) — and remove or rewrite every "Not committed, not staged" / "not auto-committed" claim about an artifact the verb now stages. Re-read the live Outputs section at build time (the exact filenames + the "not committed" wording drift) and reconcile every contradicting sentence. This is a required edit alongside the verb-call step, not an afterthought.
- **CONSTRAINT (state inside each phase):** the helper invocation is `[WIP]`-committing the command's OWN artifacts into the INSTALL repo (D2) and is FAIL-SOFT (D1) — a commit failure warns and the command continues (the artifact is already written; the commit is a safety net). The call is UNCONDITIONAL (zero-escape-hatch — no "skip if trivial"). Use the installed runtime path for the launcher (`.devforge/lib/artifact_helper`, or the `_shared` form if OQ1 picked that), matching how each spec already invokes its own helper.
- **DISCIPLINE (state inside each phase):** this edit ships into `.claude/` (the `/<cmd>` slash-command spec body emitted into target projects), so the `main.md` edit MUST go through **instruction-author → instruction-reviewer** AND be verified via the **claude-code-guide** agent BEFORE it lands (confirm the slash-command spec-body convention for an inline helper-call step matches the live command's existing helper-invocation pattern). Confidence is not verification — claude-code-guide is a real tool call.
- **Execution:** instruction-author → instruction-reviewer for the `main.md` edit; claude-code-guide consulted FIRST.

#### Verify (run per command — substitute `<cmd>` and the expected paths/label)

```bash
cd /Users/mykolakudlyk/Projects/ai-dev-team-forge
# The per-step artifact-commit call is present, with the command's artifact paths + label:
grep -n "commit-artifacts" src/commands/<cmd>/main.md          # expect: the verb call near the end of the flow
grep -n "artifact_helper\|_shared" src/commands/<cmd>/main.md  # expect: the installed launcher path (OQ1-resolved form)
grep -n "git add -A" src/commands/<cmd>/main.md                # expect: NO match (the verb owns staging; explicit paths only)
grep -n "WIP\]" src/commands/<cmd>/main.md                     # read: the per-command [WIP] <label> is the message
```

DoD (per command): `src/commands/<cmd>/main.md` calls the Phase-1 verb with the command's actual artifact paths + the per-command label, near the end of the flow after the artifact is written + approved; the call is unconditional + fail-soft + install-repo-only (via the verb); the command's "Outputs of this command" section is reconciled to state it now `[WIP]`-commits its own artifacts (every stale "Not committed, not staged" claim removed/rewritten); the edit went through instruction-author → instruction-reviewer + claude-code-guide; the command's real artifact filenames were re-verified against the live spec (not trusted from the map). (Phase 7 `/breakdown` additionally: the DoD states Phase 7 is the FIRST per-step commit tracking the task files + `tasks/README.md` in the install repo in WRAPPER mode — `/implement`'s wrapper path skips them, `_cmds_commit.py:515-526` — so the commit is NOT redundant there.)

### Phase 10 — `/finalize` safety-net (D4)

**Objective:** add the UNCONDITIONAL `git add specs/<feature>/` + `[WIP]` commit to `/finalize` PHASE 2 before the squash (carried from plan 33 D2/D5), as the belt-and-suspenders catch for any artifact a fail-soft per-step commit skipped, and reconcile the surrounding `main.md` prose.

- **Files touched:** `src/commands/finalize/main.md` (+ `src/commands/finalize/references/results-and-docs.md` if the results-block shape changes).
- **The edit:** in PHASE 2 (after the existing `docs/` commit handling), add an UNCONDITIONAL step that calls the Phase-1 verb with `--paths '["specs/<feature>/"]'` + a `[WIP] finalize: artifact safety-net` label (OQ3 form). Every feature reaching `/finalize` has a `specs/<feature>/`; the call always runs (zero-escape-hatch). It is install-repo-only in wrapper mode (the verb's D2 guard — NOT re-implemented inline, NOT `git -C <source_root>`), explicit path never `git add -A`. **State inline that this is DELIBERATELY redundant with the per-step commits** (D4 / OQ4) — it catches a straggler a fail-soft per-step commit skipped; it is not an oversight. Reconcile the "Outputs of this command" list + the Important rules so the safety-net commit is named alongside the docs `[WIP]` commit as a thing that folds into the squash. (This is the ONE place the verb takes a DIRECTORY path; the verb stages whatever git resolves under it — identical to `git add specs/<feature>/` — and a re-`git add` of already-committed per-step artifacts is a harmless no-op for unchanged files.)
- **DISCIPLINE:** ships into `.claude/` → instruction-author → instruction-reviewer + claude-code-guide BEFORE landing.
- **Execution:** instruction-author → instruction-reviewer; claude-code-guide consulted FIRST for the inline helper-call-step convention inside a PHASE block.

#### Verify

```bash
cd /Users/mykolakudlyk/Projects/ai-dev-team-forge
grep -n "commit-artifacts" src/commands/finalize/main.md    # expect: the verb invocation is present in PHASE 2 (the safety-net call), before the squash
grep -n "specs/.*feature" src/commands/finalize/main.md     # expect: the safety-net call passes the specs/<feature>/ directory path
grep -n "git add -A" src/commands/finalize/main.md          # expect: NO match
grep -n "redundant\|safety-net\|belt-and-suspenders" src/commands/finalize/main.md   # expect: the deliberate-redundancy note (D4/OQ4)
# NOTE: the D2 install-repo-only guarantee is enforced by the verb's resolve_workspace (built + tested in Phase 1),
# NOT by a git -C string in this spec — finalize/main.md already contains a git -C <source_root> for the PHASE-3
# squash, so a "git -C" grep here is ambiguous and is deliberately NOT used as the D2 check.
```

DoD: `/finalize` PHASE 2 makes an UNCONDITIONAL artifact safety-net commit (via the Phase-1 verb, explicit `specs/<feature>/` path, install-repo-only in wrapper mode, never `git add -A`) BEFORE the squash so it folds in; the Outputs list + Important rules name it; the deliberate-redundancy-with-per-step-commits note (D4/OQ4) is stated inline; the edit went through instruction-author → instruction-reviewer + claude-code-guide.

### Phase 11 — Supersede plan 33

**Objective:** mark plan 33 superseded everywhere it is referenced, so a fresh session does not execute the finalize-only/inline approach this plan replaced.

- **Files touched:** `33-FINALIZE-STAGES-SPEC-ARTIFACTS-PLAN.md` (its top `**Status:**` line) + repo-root `CLAUDE.md` (the active-plans list).
- **The edits:** (1) change plan 33's `**Status:**` line to `**Status:** SUPERSEDED by 37-PER-STEP-ARTIFACT-COMMIT-PLAN.md — finalize-only (33 D1) + inline-git (33 D6) replaced by per-step commits via a shared verb; 33's whole-dir/install-repo-only safety-net survives as 37 D4. Do NOT execute plan 33.` (2) in repo-root `CLAUDE.md`, update the plan-33 list entry to reflect SUPERSEDED status (one clause, keep the existing description so the rationale is still readable) AND add a new `37-PER-STEP-ARTIFACT-COMMIT-PLAN.md` entry (status, branch, the one-paragraph what/why, D1–D4 + OQ1–OQ4 summary, the supersede-33 note, the phase list).
- **DISCIPLINE:** both are repo-internal docs (do NOT ship into `.claude/`) → instruction-author → instruction-reviewer; NO claude-code-guide needed.
- **Execution:** instruction-author → instruction-reviewer.

#### Verify

```bash
cd /Users/mykolakudlyk/Projects/ai-dev-team-forge
grep -n "SUPERSEDED by 37" 33-FINALIZE-STAGES-SPEC-ARTIFACTS-PLAN.md   # expect: the status line flipped
grep -n "37-PER-STEP-ARTIFACT-COMMIT" CLAUDE.md                        # expect: the new plan-list entry
grep -in "superseded by 37" CLAUDE.md                                  # expect: the plan-33 entry marked superseded (case-insensitive — matches "SUPERSEDED"/"Superseded"/"superseded")
```

DoD: plan 33's `**Status:**` line reads SUPERSEDED by 37; the repo-root `CLAUDE.md` plan list marks 33 superseded AND carries a new 37 entry; edits went through instruction-author → instruction-reviewer.

### Phase 12 — install ride + e2e (user-driven HARD GATE)

**Objective:** the repo's standard manual e2e gate — confirm each command now WIP-commits its own artifacts mid-pipeline, and that they all still fold into ONE clean commit at `/finalize`, in BOTH standalone and wrapper mode, without touching the source-repo traceless guarantee.

- **Install ride (can be checked now):** a full `install.sh <tmp-target>` lands an executable `.devforge/lib/artifact_helper` (the OQ1-resolved launcher) and re-emits each edited command with 0 `{{` placeholder leaks. (Same install-ride shape plans 22/24/25 used.)
- **Standalone e2e:** run the pipeline (`/research` OR `/discover` → `/specify` → `/plan` → optional `/grill` → `/breakdown` → `/implement` → `/review` → `/verify` → `/summarize` → `/finalize`). **Success BEFORE `/finalize`:** after each step, `git log --oneline` shows that step's own `[WIP] <label>` commit and the step's artifacts are TRACKED (a `git status` shows them committed, not untracked) — verify mid-pipeline (e.g. after `/specify`, `spec.md` + `handoff.json` are in a `[WIP] spec: …` commit). **Success AFTER `/finalize`:** all the per-step `[WIP]` commits fold into ONE clean feature commit — `git log --oneline <base>..HEAD` shows ZERO `[WIP]` commits, and `git show --stat <head>` contains `spec.md`/`plan.md`/`review.md`/`verification.md`/the handoffs alongside the code + task files.
- **Wrapper e2e:** run the pipeline in a wrapper-mode install. **Success:** the artifacts are committed in the INSTALL repo only (the install repo's `git log` shows the per-step `[WIP]` commits + the final squash contains `specs/`); the SOURCE (product) repo stays code-only + traceless — `git show --stat <head>` in the source repo shows NO `specs/`/`research/`/`discover/` path, and `git show <head>` shows NO `Co-Authored-By` (plan 25 D5 holds; D2 is the guard).
- Mark DONE only after user sign-off.

#### Verify

```bash
# (User-driven — run against a target install with the new verb + edited commands emitted.)
# Mid-pipeline (e.g. after /specify):
#   git log --oneline | grep "\[WIP\] spec:"                         # expect: the per-step spec commit exists
#   git status --porcelain specs/                                    # expect: spec.md + handoff.json NOT untracked (they were committed)
# After /finalize, standalone:
#   git log --oneline <base>..HEAD | grep -c "\[WIP\]"               # expect: 0 (all per-step WIP commits folded into the squash)
#   git show --stat HEAD | grep -E "specs/.*/(spec|plan|review|verification)\.md"   # expect: all present in the clean commit
# After /finalize, wrapper:
#   (install repo)  git show --stat HEAD | grep "specs/"             # expect: present
#   (source repo)   git show --stat HEAD | grep -E "specs/|research/|discover/"   # expect: NO match
#   (source repo)   git show HEAD | grep -i "Co-Authored-By"         # expect: NO match (traceless, plan 25 D5)
# Install ride:
#   install.sh <tmp> lands an executable .devforge/lib/artifact_helper; 0 '{{' leaks in each edited command.
```

DoD: standalone e2e confirms each step WIP-commits its own artifacts mid-pipeline (tracked, not untracked) AND they all fold into one clean commit with zero leftover `[WIP]` commits after `/finalize`; wrapper e2e confirms artifacts land in the INSTALL repo ONLY and the SOURCE repo stays code-only + traceless (no `specs/`/`research/`/`discover/`, no `Co-Authored-By`); install ride green; user sign-off obtained.

### Phase 13 — docs propagation + cross-ref sweep

**Objective:** propagate the change to the awareness surfaces + sweep for any reference the edit made stale.

- **`CHANGELOG.md`** — add an entry: each pipeline command now WIP-commits its own planning artifacts (spec/plan/handoffs/grill/review/verification/research/discover) the moment it produces them via the shared `artifact_helper commit-artifacts` verb, so work is git-safe at every step (recoverable after an interrupt or `git clean`); the commits fold into `/finalize`'s squash, so the final PR is unchanged. `/finalize` retains an unconditional `specs/<feature>/` safety-net commit.
- **Consumer overlay `src/CLAUDE.md`** — update the per-command one-liners (Command Details + Workflow bullets) for the eight edited commands to note that each WIP-commits its own artifacts, ONLY where a one-liner already describes what the command writes. Keep the existing load-bearing gate/awareness sentences VERBATIM (per the plan-08 rationale: every forge command sets `disable-model-invocation: true`, so its always-on `src/CLAUDE.md` catalog entry is the only model-facing awareness source — do NOT delete or reshape the catalog sentences). Right-size: a clause added to the existing WHAT sentence, not a new paragraph. claude-code-guide consulted if the catalog-awareness framing is touched (the one-liners are model-facing awareness).
- **Repo-root `CLAUDE.md`** — already updated in Phase 11 (the 37 entry + the 33-superseded mark); confirm the "Where to find what" table has a row or note for the new `artifact_helper` if the table enumerates helpers (re-read at edit time; add only if the table's convention covers per-command launchers).
- **Cross-ref sweep** — grep for any surface that asserts the OLD "artifacts are never committed until `/finalize`" framing (notably plan 33's own prose, now superseded, and any `src/CLAUDE.md`/`storage-rules.md` claim that planning artifacts ride the `/finalize` squash exclusively) and reconcile only where a mention contradicts per-step commits.
- **Execution:** instruction-author → instruction-reviewer for every markdown edit; claude-code-guide for the `src/CLAUDE.md` consumer-overlay edits if the catalog-awareness framing is touched. `CHANGELOG.md` + repo-root `CLAUDE.md` are repo-internal (no claude-code-guide — they do not ship into `.claude/`).

#### Verify

```bash
cd /Users/mykolakudlyk/Projects/ai-dev-team-forge
grep -n "WIP-commit\|commit-artifacts\|artifact" CHANGELOG.md                # expect: the changelog entry
grep -rn "commits its own\|WIP-commit\|artifact" src/CLAUDE.md               # read: the per-command one-liners note per-step commits; gate sentences kept verbatim
grep -rn "never committed\|until /finalize\|only at /finalize" src/CLAUDE.md src/devforge/storage-rules.md   # read: no surface still asserts the stale "never committed until finalize" framing
grep -n "artifact_helper" CLAUDE.md                                          # read: the "Where to find what" table notes the new launcher if its convention covers it
```

DoD: `CHANGELOG.md` + the eight `src/CLAUDE.md` command one-liners (gate sentences kept verbatim) reflect per-step artifact commits; the repo-root `CLAUDE.md` 37 entry + the helper-location note are consistent; the cross-ref sweep is clean (no surface asserts the stale "artifacts never committed until `/finalize`" framing); all edits went through instruction-author → instruction-reviewer (+ claude-code-guide for the consumer-overlay awareness edits).

## When resuming work

1. **Re-read this plan in full** + the live files it grounds against: `src/devforge/lib/_implement/_cmds_commit.py` (the `wip-commit` git-discipline template the new verb mirrors — explicit `git add -- <path>`, `git -C`, `_GIT_TIMEOUT`, `resolve_workspace`; confirm `git add -A` is still never used at `:39,96-97`), `src/devforge/lib/_implement/_workspace.py` (`resolve_workspace` → `Workspace{install_root, source_root, is_wrapper}`, fail-soft to standalone — the D2 install-root targeting source), `src/devforge/lib/summarize_helper.py` (the launcher-shim pattern the OQ1-lean `artifact_helper` mirrors), `src/devforge/lib/_finalize/_squash.py` (the `git reset --soft <base>` squash near `:521` — WHY per-step WIP commits fold in and produce an identical PR), `src/commands/finalize/main.md` (the PHASE-2 commit set + Outputs list the D4 safety-net rides), each of the eight `src/commands/<cmd>/main.md` files in the per-step map (READ each in full at build time — the artifact filenames + the correct insertion point drift; do NOT trust the map blind), and `install.sh` (the full-install `cp -R "$TEMPLATE_DIR/src/devforge/." "$TARGET_DIR/.devforge/"` at `install.sh:197` that ships launchers + the surgical `--only` path `install.sh:96-161` that keys to a command name and always copies `_shared/` at `install.sh:135-141` — the OQ1 install-wiring source).
2. **Phase 0 is the gate** — D1–D4 + OQ1–OQ4 + the supersede-33 call must be ratified with the user before any edit (the mechanism rides `/finalize` PHASE 2, plan-25 settled, and supersedes plan-33 settled D1/D6).
3. **Execute Phases 1→13 in order** (each green before the next). Phase 1 builds + tests the verb (python-engineer → python-reviewer, REAL git fixture, standalone + wrapper arms, same turn) and resolves OQ1. Phases 2–9 each edit one command `main.md` (instruction-author → instruction-reviewer + claude-code-guide — they ship into `.claude/`). Phase 10 adds the `/finalize` safety-net. Phase 11 supersedes plan 33. Phase 12 is the user-driven install-ride + e2e HARD GATE (standalone + wrapper). Phase 13 propagates docs + sweeps cross-refs.
4. **Discipline:** every `main.md` / `src/CLAUDE.md` edit through instruction-author → instruction-reviewer; every `main.md` edit (ships into `.claude/`) AND any `src/CLAUDE.md` awareness-framing edit verified via claude-code-guide BEFORE landing; the new verb through python-engineer → python-reviewer with a REAL git-fixture test written + run in the same turn (standalone + wrapper arms). Never `git add -A` — the verb stages explicit named paths only. Never point the artifact verb at `source_root` in wrapper mode (plan 25 D5; D2 is the guard). The per-step call is unconditional (zero-escape-hatch); fail-soft means the git op never blocks the command, not that the call is optional. This plan file is a repo-root plan and does NOT ship into `.claude/`, so writing it needs no claude-code-guide; the `main.md` edits (Phases 2–10) DO ship and DO require it. Today is 2026-06-23.
5. Commit alongside the work in repo commit style (lowercase, terse, scope prefix — e.g. `feat(artifact): shared commit-artifacts verb for per-step WIP commits`, `feat(specify): WIP-commit spec.md + handoff per step`, `docs(claude): note per-step artifact commits`).

## Related plans

- `33-FINALIZE-STAGES-SPEC-ARTIFACTS-PLAN.md` — **SUPERSEDED by this plan** (Phase 11). 33 chose a finalize-only (D1) inline-git (D6) `git add specs/<feature>/` before the squash; this plan replaces that with per-step commits via a shared verb and carries 33's whole-dir/install-repo-only safety-net forward as D4. Read 33 for the original investigation (who commits what, the `git reset --soft` fold mechanic) — it is the source this plan's Context section condenses.
- `25-FINALIZE-COMMAND-REDESIGN-PLAN.md` — built the live `/finalize` command whose PHASE-3 `git reset --soft` squash (the reason per-step WIP commits fold in) + PHASE-2 commit set (where the D4 safety-net rides) this plan depends on, and whose D5 source-repo traceless invariant this plan's D2 guards. DO NOT violate plan 25 D5.
- `07-EXECUTE-TASK-REDESIGN-PLAN.md` / `17-IMPLEMENT-PER-TASK-PANEL-PLAN.md` — built the `/implement` command whose `wip-commit` verb (`_cmds_commit.py` — never `git add -A`, `resolve_workspace`, `git -C`, `_GIT_TIMEOUT`) is the git-discipline template the new `commit-artifacts` verb mirrors, and which already commits code + task files per task (UNCHANGED by this plan).
- `24-SUMMARIZE-COMMAND-REDESIGN-PLAN.md` — built `/summarize`, which already `[WIP]`-commits `summary.md` (so `summarize` is NOT in this plan's per-step map; its artifact is already committed and already folds into the `/finalize` squash).
