# 33 — FINALIZE STAGES SPEC ARTIFACTS PLAN

**Status:** SUPERSEDED by 37-PER-STEP-ARTIFACT-COMMIT-PLAN.md — finalize-only (33 D1) + inline-git (33 D6) replaced by per-step artifact commits via a shared verb; 33's whole-dir/install-repo-only safety-net survives as 37 D4 (the /finalize safety-net). Do NOT execute plan 33.

Fixes a confirmed framework gap: the spec-driven pipeline NEVER git-commits a feature's planning artifacts (`spec.md`, `plan.md`, `research.md`, the `*-handoff.json` files, `review.md`, `verification.md`, the `*-state.json` files). They accumulate untracked in the working tree for the whole feature lifecycle, so the PR that ships after `/finalize` contains code with no spec/plan/review, and a `git clean -fdx` would silently delete them. This plan extends `/finalize` (the single point that already assembles the clean feature commit and already stages `docs/` right before the squash) to ALSO stage the feature's `specs/<feature>/` directory before the squash, so the planning artifacts fold into the same clean commit the code lands in. Scope is `/finalize` ONLY — NOT a new command, NOT a change to `/implement`.

## Context for next session

The investigation is DONE; the following are VERIFIED facts (read against the live tree this session — re-verify any line number before citing it in a `#### Verify` block, line numbers drift). A fresh session needs no re-investigation.

### Who stages what across the pipeline (all verified by reading the helpers today)

- **`/implement` standalone WIP commit stages, per-path:** source code (the task's `touched_files`) + the current task file + `tasks/README.md` index. It explicitly NEVER uses `git add -A` — this is a deliberate safety rule (`src/devforge/lib/_implement/_cmds_commit.py:39,97`). So `/implement` commits the TASK FILES under `specs/NNN/tasks/` but NOT the `spec.md`/`plan.md` they derive from.
- **`/finalize` PHASE 2 stages ONLY `docs/`** — `git add docs/ && git commit -m "[WIP] Feature docs: <NNN-slug>"` (`src/commands/finalize/main.md:143`), and only when the tech-writer wrote docs (it is a CONDITIONAL commit — the "Docs written" branch of PHASE 2).
- **`/finalize` PHASE 3 squash is `git reset --soft <base>` + `git commit`** (`src/devforge/lib/_finalize/_squash.py:521` `_git_reset_soft` → `:536` `_git_commit_simple`). `git reset --soft` only re-commits what was ALREADY committed between `<base>..HEAD` — it never picks up untracked files. So nothing untracked enters the squash unless an explicit `git add` staged + committed it into the WIP range first (exactly what the `docs/` `[WIP]` commit does for `docs/`).
- **`/specify`, `/plan`, `/breakdown`, `/research`, `/discover`, `/review`, `/verify` contain ZERO `git add`** — verified by grep (0 matches for `git add` across their helper subpackages `src/devforge/lib/{_specify,_plan,_breakdown,_research,_discover,_review,_verify}/`).

### Therefore NEVER committed by any command

`spec.md`, `plan.md`, `research.md`, the discover report, all `*-handoff.json` (research/plan/breakdown/specify), `review.md`, `verification.md`, the `*-state.json` files, and the `.devforge/` runtime state (`memory.md`, `session-state.md`, `cbm-last-indexed-sha`). The PR that ships after `/finalize` therefore contains code with NO spec/plan/review tracked alongside it, and a `git clean -fdx` would silently delete every one of those untracked artifacts.

### Why it is a GAP, not a deliberate design (the key tell)

`/implement` commits the TASK FILES (`specs/NNN/tasks/*.md` + README) but NOT the `spec.md`/`plan.md` they derive from — task files in, parent contract out. That inconsistency is not deliberate. And the framework's own creed is "Specs are contracts" (consumer `src/CLAUDE.md` Key Rule 5: *"Specs are contracts — once approved, implementation must satisfy every acceptance criterion"*), yet the contract never reaches git. No command or prompt ever tells the user to commit `specs/` either. The fix closes the inconsistency: the parent contract lands in git alongside the code and the task files.

### The fix shape (one sentence)

Add an UNCONDITIONAL `git add specs/<feature>/` + `[WIP]` commit to `/finalize` PHASE 2 (before the PHASE-3 squash), wrapper-mode targeting the INSTALL repo only, so the feature's planning artifacts fold into the single clean commit exactly the way the existing conditional `docs/` `[WIP]` commit folds in.

## Decisions (drafted — RATIFY in Phase 0 before any edit)

These touch plan-25 settled design (`/finalize`'s PHASE-2 commit set + PHASE-3 squash fold), so Phase 0 gates on user sign-off.

### D1 — Fix location: extend `/finalize`, NOT a new command, NOT a change to `/implement`

**Recommendation: extend `/finalize`.** `/finalize` is the single point that already assembles the clean feature commit and already stages `docs/` right before the squash (PHASE 2 — `main.md:140-144`); it is the natural and only coherent home for staging the rest of the feature's artifacts into the same commit. **Trade-off considered:** adding the stage to `/implement` (which already commits the task files) was rejected — `/implement` runs PER TASK, so it would re-stage the whole `specs/<feature>/` dir on every task, and it deliberately NEVER `git add`s the parent `spec.md`/`plan.md` (its per-path safety rule, `_cmds_commit.py:39,97`); reversing that for `/implement` would touch a hot per-task path for a once-per-feature concern. A standalone command was rejected for the same reason `/finalize` exists at all — the terminal PR-prep belongs in one place. **Reasoning:** consistency-over-invention — `/finalize` already owns the clean-commit assembly + the `docs/` stage; the spec-artifacts stage is the same pattern one step wider.

### D2 — Staging scope: the WHOLE `specs/<feature>/` directory, not a curated subset

**Recommendation: stage the whole `specs/<feature>/` directory** (spec, plan, research, all `*-handoff.json`, review, verification, the `*-state.json` files, and `tasks/`). **Trade-off considered:** a curated subset (e.g. exclude the `*-state.json`/`*-handoff.json` intermediates) was rejected as added cherry-pick logic for no benefit — KISS, atomic, no per-file filter to maintain. Everything under `specs/<feature>/` is already feature-scoped; the `*-state.json`/`*-handoff.json` complete the reproducible record and are cheap (small JSON). **Reasoning:** `git add specs/<feature>/` is one path, no glob logic; the task files + README were already committed by `/implement`, so re-`git add`-ing the directory is a harmless no-op for unchanged files (git stages only the delta). See OQ1 for the curated-subset alternative left open for ratification.

**What "the whole directory" includes (full enumeration — staging is path-level, so every file present is committed):** beyond the always-present `spec.md`, the optional `/plan` supplementals `data-model.md` + `contracts.md` (present only when `/plan` wrote them), the optional `/grill` outputs `grill.md` + `grill-seed.json` (present only when `/grill` ran — both currently untracked per `src/commands/grill/main.md:28-29`), the `*-state.json` run-state files, and `summary.md` (already tracked — see D-note below). **`grill-seed.json` is a backward re-entry seed** consumed by upstream `/research`/`/discover`/`/specify`; once the feature reaches `/finalize` the seed has served its purpose, so committing it is a permanent record of a transient. **It is included deliberately, not excluded** — carving it (or any single file) out would reintroduce the exact cherry-pick/filter logic D2 rejects and breach the zero-escape-hatch rule; the whole-directory stage is the consistent call. **`summary.md` is NOT newly staged by this step** — `/summarize` already `[WIP]`-committed it (plan 24) and it already folds into the squash (plan 25 `main.md:82`); the re-`git add` is a no-op for it, exactly like the already-committed task files.

### D3 — Runtime state is EXCLUDED (a deliberate boundary, not an oversight)

**Recommendation: do NOT auto-stage `.devforge/memory.md` / `.devforge/session-state.md` / `.devforge/cbm-last-indexed-sha` into the feature commit.** **Trade-off considered:** committing runtime state alongside the feature would make the install fully reproducible from git, but it was rejected — these are GLOBAL machine state, not feature-scoped; riding them on every feature commit creates cross-feature churn and merge noise (two features finalized in sequence would each rewrite `memory.md` in their commit). **Reasoning:** the stage targets `specs/<feature>/` precisely because that path is feature-scoped; `.devforge/` is install-scoped. Leaving runtime state to the user (or a separate concern) keeps the feature commit clean. State this as a deliberate boundary so a future session does not "fix" it by adding `.devforge/` to the stage. See OQ2.

### D4 — Wrapper-mode safety: the `specs/` stage targets the INSTALL repo ONLY, never the source repo

**Recommendation: in wrapper mode, the `git add specs/<feature>/` + commit runs in the INSTALL/wrapper repo only.** **The constraint:** in wrapper mode `specs/` lives in the INSTALL/wrapper root (verified — consumer `src/CLAUDE.md` Artifact Storage: *"Wrapper mode: All artifacts (`specs/`, `docs/`, `constitution.md`) live in the wrapper root, NOT inside `{{PROJECT_ROOT}}`"*), and the SOURCE (product) repo squash stays traceless `[TICKET-ID]` with NO AI traces — this is plan 25's D5, a USER-CONFIRMED invariant. Staging `specs/` into the source repo would both put forge artifacts into the product repo (wrong root) AND violate the traceless guarantee. **Reasoning:** the PHASE-0 `preflight` already exposes `source_root` + `wrapper_mode`, and PHASE 2 already branches on them for the existing flow — the `specs/` stage reuses that same branch, it does NOT re-detect. The existing `docs/` `[WIP]` commit (`main.md:143`) already runs in the install repo without a `git -C <source_root>` — the `specs/` stage follows the identical placement. **DO NOT violate plan 25 D5.**

### D5 — Timing: an UNCONDITIONAL `[WIP]` commit before the squash

**Recommendation: stage `specs/<feature>/` in an UNCONDITIONAL `[WIP]` commit before the PHASE-3 squash.** **The contrast with the existing `docs/` commit:** the `docs/` `[WIP]` commit is CONDITIONAL (it runs only when the tech-writer wrote docs — `main.md:140`). The `specs/` commit is UNCONDITIONAL — every feature that reaches `/finalize` has a `specs/<feature>/` directory (the spec at minimum; the gate already requires the spec exists and is `Complete`). **The mechanism:** it folds into the squash the same way the `docs/` commit does (plan 25 D8 pattern — docs `[WIP]`-committed BEFORE the squash so they fold in). **Why an explicit `git add` is required (not derivable):** the staged artifacts are NOT in `gather-change-data`'s `files` list — that list is the COMMITTED `merge-base..HEAD` diff (verified — `_changes.py` calls `_shared.feature_scope.resolve_feature_scope`, which diffs committed history), and an untracked `spec.md` never appears in a committed diff. So this MUST be an explicit `git add specs/<feature>/` — the squash's `git reset --soft` will not pick it up otherwise (the same reason `docs/` needs its own `git add`). **Reasoning:** unconditional + before-the-squash + explicit-`git add` is the only shape that lands the artifacts in the clean commit.

### D6 — Inline orchestrator step, NOT a helper verb (the one genuinely debatable call)

**Recommendation: an INLINE orchestrator `git add specs/<feature>/` + `git commit` step in `main.md` PHASE 2**, for parity with the existing inline `git add docs/` docs-commit. **The fact:** PHASE 2 already does its git ops inline (the `docs/` commit is a raw `git add docs/ && git commit -m ...` Bash block at `main.md:142-144`), NOT via a `finalize_helper` verb. **The alternative considered:** a `finalize_helper stage-feature-artifacts` verb that encapsulates the wrapper-mode install-repo path resolution (so the path logic lives in tested Python, not prose). **Why inline is preferred:** (a) the `docs/` precedent is inline, so an inline `specs/` step is consistency-over-invention; (b) the wrapper-mode branch data (`wrapper_mode`, the fact that the install repo is the cwd `.`) is ALREADY in the orchestrator's hand from PHASE 0, and the existing inline `docs/` commit already runs in the install repo with no `git -C` — so there is no nontrivial path resolution for a verb to encapsulate (the install repo IS the cwd in both standalone and wrapper mode for this stage). **Flag this as the one genuinely debatable call** — if the user prefers tested-Python path logic, OQ3 routes it to a helper verb and the Phase-2 work becomes a python-engineer→python-reviewer task instead of an instruction-author task. **Reasoning:** the inline step is a 2-line Bash block identical in shape to the existing `docs/` commit; a verb would be more machinery than the concern warrants.

## Open Questions (OQ-N — argued, recommended, ratify in Phase 0)

- **OQ1 — whole `specs/<feature>/` dir vs excluding the `*-state.json` intermediates?** Lean: whole dir (D2 — KISS, atomic, the intermediates are cheap and complete the reproducible record). The counter: a reviewer might argue the `*-state.json` run-state files are scratch and do not belong in the PR. Recommendation: whole dir per D2; the state files are small and feature-scoped, and excluding them adds filter logic for marginal cleanliness. Resolve in Phase 0.
- **OQ2 — should runtime state EVER be committed, by a different mechanism?** Lean: out-of-scope for this plan (D3 — `.devforge/` is install-scoped, not feature-scoped). Note it explicitly so a future session does not fold it into this fix. If a "commit my install config" concern arises, it is a separate plan with a separate mechanism (likely a one-time `/configure`-adjacent commit, not a per-feature ride). Resolve as out-of-scope in Phase 0; record the note.
- **OQ3 — inline git step vs new helper verb?** Mirror of D6. Lean: inline (the `docs/` precedent + the wrapper branch data already in hand + no nontrivial path resolution to encapsulate). The counter: tested-Python path logic is more robust than prose. Recommendation: inline; flag it as the one genuinely debatable call. If the user prefers a verb, Phase 2 becomes a python-engineer→python-reviewer task. Resolve in Phase 0.
- **OQ4 — back-fill is a NON-GOAL.** This plan fixes FORWARD only. Artifacts already orphaned in existing installs (e.g. a project mid-pipeline today with an untracked `spec.md`) must be committed manually — this plan adds NO migration / back-fill step, and a future session must NOT build one under this plan. **State this explicitly as a non-goal.** Reasoning: a back-fill would need to scan every existing `specs/*/` for untracked artifacts and decide which feature commit each belongs to — a separate, speculative concern with no current consumer; forward-fix is the whole scope. Ratify the non-goal in Phase 0.

## Out of scope (do NOT plan here)

- **A new command or a `/implement` change** — the fix is `/finalize`-only (D1).
- **Staging the source (product) repo's `specs/`** — `specs/` lives in the install/wrapper root; the source repo squash stays traceless `[TICKET-ID]` (plan 25 D5; D4 is the guard).
- **Committing `.devforge/` runtime state** (`memory.md`, `session-state.md`, `cbm-last-indexed-sha`) — install-scoped, not feature-scoped (D3 / OQ2).
- **A back-fill / migration for already-orphaned artifacts in existing installs** — forward-fix only; manual back-fill (OQ4).
- **`git add -A` anywhere** — stage the explicit `specs/<feature>/` path only (matches `/implement`'s existing safety rule, `_cmds_commit.py:39,97`).

## Phases (build order)

Each phase: objective, files touched, an execution agent-loop note, a `#### Verify` fenced bash block, and a `DoD:` line. Per repo discipline (`CLAUDE.md`): every command/spec/reference/`CLAUDE.md`/plan markdown edit goes through **instruction-author → instruction-reviewer**; any `.py` helper change (only if OQ3 picks a verb) goes through **python-engineer → python-reviewer** with a test written + actually run in the SAME turn (round-trip REAL git fixtures, not hand-faked); any Claude-Code-integration concern (the slash-command spec body, command frontmatter, the emitter/install behavior) is verified via the **claude-code-guide** agent BEFORE writing. Each phase leaves the system buildable and tests green.

**Zero-escape-hatch:** no rule in any phase below contains an OR / if / except / unless / use-judgment carve-out. The `specs/<feature>/` stage is UNCONDITIONAL (D5); the wrapper guard is a single branch on the already-resolved `wrapper_mode` (D4); the path staged is always the explicit `specs/<feature>/` (never `git add -A`).

### Phase 0 — Decisions ratified (gate on user sign-off)

**Objective:** confirm D1–D6 + resolve OQ1–OQ4 with the user before any edit, because this touches plan-25 settled design (`/finalize`'s PHASE-2 commit set + PHASE-3 squash fold).

- **Files touched:** none (decision gate).
- **Execution:** present D1–D6 + OQ1–OQ4 to the user; record the ratified decisions in this plan (flip any the user redirects). Confirm specifically: (a) D1 fix-in-`/finalize` (not `/implement`); (b) D2/OQ1 whole-dir scope; (c) D3/OQ2 runtime-state-excluded boundary; (d) D6/OQ3 inline-vs-verb (the genuinely debatable call); (e) OQ4 back-fill non-goal.

#### Verify

```bash
grep -n "RATIFIED\|USER-CONFIRMED" 33-FINALIZE-STAGES-SPEC-ARTIFACTS-PLAN.md   # expect: D1-D6 + OQ1-OQ4 marked ratified after sign-off
```

DoD: D1–D6 ratified (or flipped) + OQ1–OQ4 resolved with the user; the inline-vs-verb call (D6/OQ3) is settled so Phase 2 knows whether it is an instruction-author task (inline) or a python-engineer task (verb); the back-fill non-goal (OQ4) is explicitly recorded; user sign-off obtained.

### Phase 1 — `/finalize` spec edit: stage `specs/<feature>/` before the squash

**Objective:** add the UNCONDITIONAL `specs/<feature>/` staging step to `src/commands/finalize/main.md` PHASE 2 (an unconditional `[WIP] Feature spec artifacts: <NNN-slug>` commit, wrapper-mode install-repo-only per D4, before the PHASE-3 squash so it folds in per D5), and reconcile the surrounding `main.md` prose so a fresh reader sees the new commit consistently.

- **Files touched:** `src/commands/finalize/main.md` ONLY (this phase). The edits:
  1. **PHASE 2** — add an UNCONDITIONAL spec-artifacts stage step. After the existing `docs/` commit handling (`main.md:140-149`), add a step that ALWAYS runs (every feature has a `specs/<feature>/`): `git add specs/<feature>/ && git commit -m "[WIP] Feature spec artifacts: <NNN-slug>"`, staging the WHOLE feature directory (D2) — the explicit path, NEVER `git add -A`. In wrapper mode this runs in the INSTALL repo (the cwd), NOT the source repo (D4) — identical placement to the existing inline `docs/` commit (which uses no `git -C`). Note inline that the artifacts are NOT in `gather-change-data`'s `files` list (committed-diff only — D5), so the explicit `git add` is required for them to fold into the squash. If OQ3 picked a verb instead of inline, this becomes a `finalize_helper stage-feature-artifacts` call (Phase 2-helper); the inline form is the D6 recommendation.
  2. **The PHASE-2 "Outputs of this command" list** (`main.md:22-28`) — add a bullet for the spec-artifacts `[WIP]` commit (parallel to the existing docs `[WIP]` bullet at `:28`): the feature's `specs/<feature>/` artifacts are `[WIP]`-committed in PHASE 2 and fold into the squash, leaving no separate commit in the final history (D5).
  3. **The "Outputs" intro** — confirm the section's framing still reads correctly with the new commit (the squash now also collapses the spec-artifacts `[WIP]` commit). Edit only if the existing prose asserts the squash collapses only `docs/`+code (re-read `:24-30` at edit time; do not cite the line blind).
  4. **PHASE 4 results block** (`main.md:215-230`) — note that the feature's `specs/` artifacts are included in the squash (parallel to the existing `**Docs**:` / `**Summary**:` lines). Add a results line or extend the existing prose so the user sees the spec artifacts landed in the clean commit — right-size at edit (a `**Spec artifacts**: included in squash` line mirrors the existing block shape).
  5. **Important rules** (`main.md:243-253`) — confirm rule 2 ("Squash is the LAST operation … the tech-writer docs are written and `[WIP]`-committed in PHASE 2, BEFORE the PHASE-3 squash, so they fold into the single clean commit") still reads correctly; extend it (or add a sibling rule) so the spec-artifacts `[WIP]` commit is named alongside the docs commit as a thing that folds into the squash. Keep the existing rules' wording; do not collapse.
- **CONSTRAINT (state inside the phase):** this edit ships into `.claude/` (it is the `/finalize` slash-command spec body emitted into target projects), so per the repo's discipline the actual `main.md` edit MUST go through the **instruction-author → instruction-reviewer** loop AND be verified via the **claude-code-guide** agent BEFORE it lands (confirm the slash-command spec-body conventions + that an unconditional inline `git add`/`git commit` Bash step inside a PHASE block matches the live `/finalize` `docs/`-commit convention). Confidence is not verification — claude-code-guide is a real tool call, not a claimed doc check.
- **Execution:** instruction-author → instruction-reviewer for the `main.md` edit; claude-code-guide consulted FIRST for the slash-command spec-body + inline-git-step convention. (If OQ3 picked a verb, the `_finalize/_squash.py` or a new `_finalize/_artifacts.py` verb goes through python-engineer → python-reviewer with a REAL git fixture test written + run in the same turn — assert `git add specs/<feature>/` stages the untracked `spec.md` + `plan.md` and the resulting `[WIP]` commit contains them; the standalone + wrapper arms both tested.)

#### Verify

```bash
grep -n "git add specs/" src/commands/finalize/main.md   # expect: the explicit specs/<feature>/ stage (NOT git add -A)
grep -n "git add -A" src/commands/finalize/main.md        # expect: NO match (never git add -A)
grep -n "WIP\] Feature spec artifacts\|spec artifacts\|specs/<feature>/" src/commands/finalize/main.md   # expect: the unconditional [WIP] spec-artifacts commit + outputs/rules mentions
grep -n "git -C" src/commands/finalize/main.md            # read: the specs/ stage does NOT use git -C <source_root> (install-repo-only, D4)
grep -n "Spec artifacts\|spec artifacts" src/commands/finalize/main.md   # expect: PHASE-4 results-block mention
```

DoD: `src/commands/finalize/main.md` PHASE 2 stages the whole `specs/<feature>/` directory in an UNCONDITIONAL `[WIP] Feature spec artifacts: <NNN-slug>` commit (explicit path, never `git add -A`, install-repo-only in wrapper mode per D4) BEFORE the PHASE-3 squash so it folds in (D5); the "Outputs" list + PHASE-4 results block + Important rules name the new commit consistently; the edit went through instruction-author → instruction-reviewer + claude-code-guide.

### Phase 2 — verification of the spec edit (no new helper code unless OQ3 picks a verb)

**Objective:** confirm the Phase-1 edit is internally consistent and emits cleanly. Under the D6 inline recommendation there is NO new helper code — the verification is the install ride + the e2e (Phase 3). If OQ3 instead picked a helper verb, the test-first python discipline applies here.

- **Files touched (inline path, D6):** none beyond Phase 1 — this phase is the install-ride + intra-file consistency check below.
- **Files touched (verb path, OQ3 alternative):** `src/devforge/lib/_finalize/_squash.py` (or a new `_finalize/_artifacts.py`) + `_cli.py` wiring + `tests/lib/_finalize/`, with the verb tested against a REAL git fixture (untracked `spec.md`/`plan.md` staged + committed, both standalone + wrapper arms) written + run in the same turn.
- **Execution:** for the inline path, instruction-reviewer's intra-file consistency pass over the edited `main.md` is the verification (the cross-ref sweep in Phase 4 catches cross-file drift); for the verb path, python-engineer → python-reviewer.

#### Verify

```bash
# Inline path (D6): the emitted command still substitutes cleanly + the helper is unchanged.
python -m pytest tests/scripts/   # expect: green (the emit still works)
# Verb path (OQ3 alternative) only:
python -m pytest tests/lib/_finalize/   # expect: green (the stage-feature-artifacts verb tested against a real git fixture)
```

DoD: under the inline path, the emitter test suite is green and the edited `main.md` passes the instruction-reviewer intra-file consistency pass; under the verb path, the new verb is registered + tested against a REAL git fixture (untracked artifacts staged + committed, both arms) + python-reviewer loop applied.

### Phase 3 — install ride + e2e Verify

**Objective:** the repo's standard manual e2e gate — confirm `/finalize` now lands the feature's `specs/` artifacts in the squashed commit, in BOTH standalone and wrapper mode, without touching the source-repo traceless guarantee.

- **Install ride (can be checked now):** `install.sh <tmp-target>` reports `finalize command: yes (folder, N references)`, 0 `{{` placeholder leaks in the emitted command, and an executable `finalize_helper`. (Same install-ride shape plans 22/24/25 used.)
- **Standalone e2e:** run `/finalize` on a test feature that finished `/implement` → `/review` → `/verify` (APPROVED) → `/summarize`. **Success looks like:** the squashed commit's `git show --stat <head>` contains `specs/<feature>/spec.md`, `specs/<feature>/plan.md`, `specs/<feature>/review.md`, and `specs/<feature>/verification.md` (the planning artifacts are now IN the clean feature commit alongside the code + the task files); the spec-artifacts `[WIP]` commit left NO separate commit in the final history (it folded into the squash — D5); a re-run idempotently no-ops ("Nothing to finalize"); NO verdict is rendered, NO finder ensemble runs (the existing `/finalize` invariants hold).
- **Wrapper e2e:** run `/finalize` on a wrapper-mode feature. **Success looks like:** `specs/<feature>/spec.md` (and the rest of the directory) lands in the INSTALL repo's squashed commit (D4), and the SOURCE (product) repo's squashed commit stays traceless — `[TICKET-ID] - Description`, NO `Co-Authored-By`, NO AI traces, and NO `specs/` path in its `git show --stat` (plan 25 D5 holds; D4 is the guard).
- Mark DONE only after user sign-off.

#### Verify

```bash
# (User-driven — run against a target install with the new /finalize source emitted.)
# Standalone, after /finalize:
#   git show --stat <head> | grep -E "specs/.*/(spec|plan|review|verification)\.md"   # expect: all four present in the clean commit
#   git log --oneline <base>..<head> | grep -c "\[WIP\]"   # expect: 0 (the [WIP] spec-artifacts commit folded into the squash)
# Wrapper, after /finalize:
#   (install repo)  git show --stat <head> | grep "specs/"            # expect: specs/<feature>/ present
#   (source repo)   git show --stat <head> | grep "specs/"            # expect: NO match (specs/ never enters the product repo)
#   (source repo)   git show <head> | grep -i "Co-Authored-By"        # expect: NO match (traceless, plan 25 D5)
# Install ride:
#   install.sh <tmp> reports: finalize command: yes (folder, N references); 0 '{{' leaks; executable finalize_helper.
```

DoD: standalone e2e confirms `spec.md`/`plan.md`/`review.md`/`verification.md` land in the squashed feature commit with no leftover `[WIP]` commits; wrapper e2e confirms `specs/` lands in the INSTALL repo commit ONLY and the SOURCE repo commit stays traceless (`[TICKET-ID]`, no `Co-Authored-By`, no `specs/`); install ride green; user sign-off obtained.

### Phase 4 — docs propagation + cross-ref sweep

**Objective:** propagate the change to the awareness surfaces + sweep for any reference the edit made stale.

- **`CHANGELOG.md`** — add an entry: `/finalize` now stages the feature's `specs/<feature>/` planning artifacts (spec, plan, research, handoffs, review, verification, task files) into the clean feature commit, closing the gap where the shipped PR contained code with no tracked spec/plan/review.
- **Consumer overlay `src/CLAUDE.md`** — update the `/finalize` one-liner (the Workflow-section bullet, currently *"Surgical `docs/` updates via tech-writer + squash WIP commits into a clean feature commit"* — re-read at edit time, it is around `:56`) and the `#### /finalize [spec-file]` Command-Details body (currently *"Dispatches tech-writer for surgical `docs/` updates … then squashes all WIP commits into a single clean feature commit. Gate-checked: spec must be Complete …"* — around `:96-97`) to add that `/finalize` ALSO commits the feature's `specs/` artifacts into the squash. Keep the existing load-bearing gate sentence verbatim (per the plan-08 rationale: every forge command sets `disable-model-invocation: true`, so its always-on `src/CLAUDE.md` catalog entry is the only model-facing awareness source — do NOT delete the gate/context sentence). Right-size: a clause added to the existing WHAT sentence, not a new paragraph.
- **Repo-root `CLAUDE.md` plan list** — add a `33-FINALIZE-STAGES-SPEC-ARTIFACTS-PLAN.md` entry to the active-plans list (status, branch, the one-paragraph what/why, the D1–D6 + OQ1–OQ4 summary, the phase list).
- **Cross-ref sweep** — grep for any other surface that describes what `/finalize` commits or what the shipped PR contains, and reconcile only where a mention asserts the OLD "squash collapses only docs + code" framing. Verify the `src/commands/finalize/references/results-and-docs.md` results-block shape still matches the Phase-1 PHASE-4 edit (if Phase 1 added a `**Spec artifacts**:` results line, the reference's documented shape must match — re-read both).
- **Execution:** instruction-author → instruction-reviewer for every markdown edit; claude-code-guide consulted for the `src/CLAUDE.md` consumer-overlay edit if the catalog-awareness framing is touched (the one-liner is model-facing awareness). The `CHANGELOG.md` + repo-root `CLAUDE.md` edits are repo-internal docs (no claude-code-guide needed — they do not ship into `.claude/`).

#### Verify

```bash
grep -n "specs/\|spec artifacts\|planning artifacts" src/CLAUDE.md   # read: the /finalize one-liner + Command-Details body now mention the specs/ commit
grep -n "33-FINALIZE-STAGES-SPEC-ARTIFACTS" CLAUDE.md                 # expect: the new plan-list entry
grep -n "specs/\|spec artifacts" CHANGELOG.md                        # expect: the changelog entry
grep -rn "squash.*docs\|docs.*squash" src/commands/finalize/references/results-and-docs.md   # read: results-block shape matches the Phase-1 PHASE-4 edit
grep -rn "/finalize" src/CLAUDE.md src/commands/ | grep -v "finalize_helper\|_finalize/"   # read: no mention asserts the stale "only docs + code in the commit" framing
```

DoD: `CHANGELOG.md` + `src/CLAUDE.md` (`/finalize` one-liner + Command-Details body, gate sentence kept verbatim) + repo-root `CLAUDE.md` plan-list entry all reflect that `/finalize` commits the feature's `specs/` artifacts into the squash; the `references/results-and-docs.md` results-block shape matches the Phase-1 edit; the cross-ref sweep is clean (no dangling "only docs + code" claim); all edits went through instruction-author → instruction-reviewer (+ claude-code-guide for the consumer-overlay awareness edit).

## When resuming work

1. **Re-read this plan in full** + the live files it grounds against: `src/commands/finalize/main.md` (the command being edited — read PHASE 2 `:124-149`, the "Outputs" list `:22-30`, PHASE 4 `:215-241`, and the Important rules `:243-253` from scratch; line numbers above are pre-edit and drift), `src/devforge/lib/_finalize/_squash.py` (the squash core — confirm `_git_reset_soft`/`_git_commit_simple` `:521,536` still use `git reset --soft`, which is why an explicit `git add` is required to fold artifacts in), `src/devforge/lib/_finalize/_changes.py` (confirm `gather-change-data` diffs COMMITTED history via `_shared.feature_scope`, so untracked `spec.md` is never in its `files` list — the D5 reason for the explicit stage), `src/devforge/lib/_implement/_cmds_commit.py:39,97` (the `/implement` per-path `git add` safety rule the explicit-path stage matches), and `src/CLAUDE.md` (the `/finalize` one-liner + Command-Details body + the "Specs are contracts" Key Rule 5 + the wrapper-mode Artifact Storage note that grounds D4). Spot-verify any line number you put in a `#### Verify` block by reading the file first.
2. **Phase 0 is the gate** — D1–D6 + OQ1–OQ4 must be ratified with the user before any edit (this touches plan-25 settled design). The genuinely debatable call is D6/OQ3 (inline vs helper verb); the rest are recommendations with the trade-off argued.
3. **Execute Phases 1→4 in order** (each green before the next). Phase 1 edits `main.md` (through instruction-author → instruction-reviewer + claude-code-guide — it ships into `.claude/`); Phase 2 verifies (no new helper code under the D6 inline recommendation — the verification is the install ride + e2e; the verb path applies only if OQ3 flips to a verb); Phase 3 is the user-driven install-ride + e2e HARD GATE; Phase 4 propagates docs + sweeps cross-refs.
4. **Discipline:** every markdown edit through instruction-author → instruction-reviewer; the `main.md` edit (ships into `.claude/`) AND the `src/CLAUDE.md` awareness-framing edit verified via claude-code-guide BEFORE landing; any helper verb (only under OQ3) through python-engineer → python-reviewer with a REAL git fixture test written + run in the same turn. Never `git add -A` — the explicit `specs/<feature>/` path only. Never stage `specs/` into the source repo in wrapper mode (plan 25 D5; D4 is the guard). This plan file is a repo-root plan and does NOT ship into `.claude/`, so writing it needs no claude-code-guide; `main.md` (Phase 1) DOES ship and DOES.
5. Commit alongside the work in repo commit style (lowercase, terse, scope prefix — e.g. `feat(finalize): stage feature specs/ artifacts into the squash`, `docs(claude): note /finalize commits specs/ artifacts`).

## Related plans

- `25-FINALIZE-COMMAND-REDESIGN-PLAN.md` — the plan that built the live `/finalize` command this plan extends; the source of the PHASE-2 `docs/` `[WIP]`-commit pattern (D5/D6 model), the PHASE-3 `git reset --soft` squash (the reason an explicit `git add` is required), and the wrapper-mode source-repo traceless invariant (its D5 — this plan's D4 is the guard that does not violate it). DO NOT violate plan 25 D5.
- `24-SUMMARIZE-COMMAND-REDESIGN-PLAN.md` — the upstream producer of `specs/[feature]/summary.md`; the structural template `/finalize` itself followed. NOTE: `summary.md` is ALREADY committed — `/summarize` makes a `[WIP]` commit (plan 24) that already folds into the `/finalize` squash (plan 25 `main.md:82`). It is therefore NOT in this plan's never-committed set and this plan's `git add specs/<feature>/` does NOT newly stage it (the re-`git add` is a harmless no-op for an already-tracked file).
- `07-EXECUTE-TASK-REDESIGN-PLAN.md` / `17-IMPLEMENT-PER-TASK-PANEL-PLAN.md` — the `/implement` command whose per-path WIP-commit safety rule (`_cmds_commit.py:39,97` — never `git add -A`) the explicit `specs/<feature>/` stage matches, and which already commits the task files (the inconsistency this plan closes: task files in, parent contract out).
