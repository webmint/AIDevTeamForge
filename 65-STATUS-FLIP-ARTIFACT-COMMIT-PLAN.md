# 65 — Status-Flip Artifact Commit Plan

**Status**: Phases 0–4 DONE (working tree) 2026-07-17 on `develop-2.0-init` — Phase 0 ratified by maintainer 2026-07-17 (D1–D4 + scope exclusions all confirmed); Phases 1–3 command edits shipped behind instruction-author → instruction-reviewer + claude-code-guide loops; Phase 4 docs reconcile shipped. Only **Phase 5 (consumer / mintEnvoy e2e) remains, user-driven (HARD GATE)**.
**Branch**: `develop-2.0-init`
**Discovered**: 2026-07-17, in the mintEnvoy consumer install — the git tree was dirty at `/implement` start.

## Problem

Pipeline commands flip an **upstream artifact's** `**Status**:` line when they consume it, but the flipping command does NOT commit that mutation. Each flip re-dirties a file its producing command had already `[WIP]`-committed. So by the time `/implement` starts, the working tree carries a set of uncommitted status-flips.

Three flips are systematic and command-triggered:

| Flipped file | Mutation | Flipping command / site | That command's own commit stages | Flip committed? (post-fix) |
|---|---|---|---|---|
| `specs/<f>/spec.md` | `Status: Draft → Approved` | `/plan` PHASE 0b (`plan_helper check-status-and-flip <path>`) | `plan.md` + `plan-handoff.json` (+ optional docs) — Phase 4 | **Yes** (Phase 1 — `spec.md` added to the Phase-4 path-set) |
| `specs/<f>/plan.md` | `Status: Draft → Approved` | `/breakdown` PHASE 0b (`breakdown_helper check-status-and-flip <path>`) | `tasks/` + `breakdown-handoff.json` (+ manifest) — Phase 5 | **Yes** (Phase 2 — `plan.md` added to the Phase-5 path-set) |
| `specs/<f>/spec.md` | `Status: → Complete` + AC boxes ticked | `/verify` PHASE 6 (`verify_helper flip-spec-status`) | `verification.md` + `verify-state.json` — Cleanup | **Yes, conditional** (Phase 3 — `spec.md` appended to Cleanup path-set iff `flipped:true`) |

### Evidence (mintEnvoy, feature `018-code-editor-extract`)

```
 M specs/018-code-editor-extract/spec.md    # -**Status**: Draft  +**Status**: Approved
 M specs/018-code-editor-extract/plan.md    # -**Status**: Draft  +**Status**: Approved
```

`spec.md` WIP-committed as `Draft` by `/specify` (`dc0330d`), flipped to `Approved` by `/plan` PHASE 0b, never re-committed. `plan.md` likewise flipped by `/breakdown`. The `/implement` `[checkpoint] pre-task 001` commit is empty (marker only) — it does not sweep these. The `/verify` Complete-flip is not yet exercised in this feature but is the same class.

### Mechanism note — `check-status-and-flip` is overloaded

The verb name is shared but does two different things:
- **`/plan`, `/breakdown`**: `check-status-and-flip <positional-path>` mutates the **upstream artifact's** on-disk `**Status**:` line (the dirtying flip this plan fixes).
- **`/verify`, `/grill`, `/review`, `/audit`**: `check-status-and-flip --feature-dir/--workspace-root … --to <phase>` advances the command's OWN run-state JSON phase counter. That state JSON is EPHEMERAL/feature-scoped and is NOT the mutation at issue. `/verify`'s dirtying spec flip is a *separate* verb (`flip-spec-status`).

## Why it matters (and the honest tradeoff)

`/finalize`'s safety-net (`git add specs/<feature>/`, plan 37 D4 + plan 33 lineage) sweeps all of `specs/<feature>/` into the squash, so the **final PR is already clean** regardless of this fix. This is not a data-loss bug.

The value is a **clean tree between pipeline commands**:
- `/implement` (and any manual `git` op) starts from a clean tree instead of a confusing mid-pipeline dirty state.
- Robustness against `git clean -fdx` and accidental entanglement of the stray flips into an unrelated manual commit.
- It closes a real hole in plan 37's stated guarantee ("every pipeline command WIP-commits its own artifacts the moment it writes them") — a command that *mutates* an upstream artifact currently leaves that mutation uncommitted.

Cost is low: the fix reuses the already-shipped `artifact_helper commit-artifacts` verb (no Python), and is a set of instruction-only edits to three `main.md` files plus a doc reconcile.

## Scope

**In scope** — the three command-triggered status-flips above.

**Out of scope** (documented, deliberate):
- `.devforge/spec-stamps.jsonl` append — a VERSIONED runtime-state file whose commit is deliberately deferred to `/finalize`'s PHASE-2 safety net by **plan 49 D3**. Do not commit it per-step here; that would fight plan 49.
- The `research/<date>-<slug>/handoff.json` `outcome.spec_path` back-fill observed dirty in mintEnvoy. `append-outcome` (the verb that writes it) is called by **no** command `main.md` — so this mutation is not systematically pipeline-triggered (it was a manual/one-off write in that install). It is also outside `/finalize`'s `specs/<feature>/` safety net, so if it ever becomes command-triggered it is a genuine separate leak. Flag as OQ-2; do not fix here.

## Decisions (recommendations — ratify in Phase 0)

### D1 — Mechanism: extend each command's existing end-of-run commit path-set (RECOMMENDED) vs commit-at-flip-site

**Recommend Option A**: each flipping command adds the artifact it flipped to its **existing** end-of-run `commit-artifacts --paths` array. Zero new commit calls; mirrors the plan-37 per-step-commit pattern exactly; the flipped file folds into the same `[WIP]` commit the command already makes.

Rejected **Option B** (a dedicated `commit-artifacts` call immediately after the flip at PHASE 0b): its only advantage is robustness if the command aborts between the flip and the end-of-run commit. But (a) the flip verbs are idempotent — a re-run returns `already-approved` and the end-of-run commit still stages the (already-flipped) file, so an aborted run self-heals on re-run; and (b) the squash erases all WIP history, so the extra commit is invisible in the final PR — no benefit to justify the extra call site. A is fewer edits and fewer commits for identical end-state.

### D2 — Include `/verify`'s Complete-flip, conditionally

**Recommend YES.** Same defect class. `/verify`'s end-of-run `commit-artifacts` (Cleanup) runs *after* the PHASE-6 flip, so extending its path-set works. It must be **conditional**: add `spec.md` to `--paths` ONLY when PHASE-6 `flip-spec-status` returned `flipped: true` (i.e. APPROVED verdict AND no task-completion blocker). On NEEDS WORK / REJECTED / blocked, `spec.md` is unchanged → do not add it (adding an unchanged path is a benign no-op anyway, but the conditional keeps the instruction honest). This also **resolves a live doc contradiction**: `src/CLAUDE.md`'s `/verify` one-liner already claims it "WIP-commits … the flipped spec" — currently false (`verify/main.md:376` excludes it); this fix makes the claim true.

### D3 — Reuse `commit-artifacts`, no Python change

**Recommend YES.** `commit-artifacts --paths <json-array>` already stages arbitrary named paths (`git add -- <path>`), is install-repo-only, and is fail-soft. It needs nothing new. This plan is instruction-edits + docs only — no `python-engineer`/`python-reviewer` phase.

### D4 — Worth doing given `/finalize` cleans the final PR

**Recommend YES** — the cost is minimal (reuse verb, three small instruction edits) and it buys a clean mid-pipeline tree, which is the property the bug report actually asks for.

## Open questions

- **OQ-1** — For `/verify`, is expressing the conditional `spec.md` path-set entry in `main.md` prose clean enough, or does it read as branchy? (The `/plan` optional-docs composition at `plan/main.md:527-529` is precedent for runtime `--paths` composition; the `/verify` conditional is one boolean on top of that.) Resolve during Phase 3 authoring.
- **OQ-2** — The `research/…/handoff.json` back-fill leak (out of scope above). Does it warrant its own investigation into whether any command *should* call `append-outcome`, and if so wiring its commit? Defer; open a separate plan only if it is observed command-triggered.

## Phases

### Phase 0 — Maintainer ratification (GATE) — ✅ DONE 2026-07-17

Ratified by the maintainer 2026-07-17 ("all good"): D1 (extend end-of-run path-set), D2 (include `/verify` conditionally), D3 (reuse verb, no Python), D4 (worth doing) + the scope exclusions (spec-stamps → plan 49 D3; research-handoff back-fill → OQ-2, not command-triggered).

Original gate text: sign off on D1–D4 + the scope exclusions (spec-stamps, research-handoff back-fill). No edits before this gate clears. Nothing downstream is authored until D1's mechanism and D2's `/verify` inclusion are confirmed.

**Verify**: maintainer explicitly ratifies D1–D4.

### Phase 1 — `/plan` commits the approved-spec flip — ✅ DONE 2026-07-17

Edit `src/commands/plan/main.md`: extend the Phase-4 WIP-commit block (`plan/main.md:527-535`) so `--paths` includes `specs/<NNN>-<feature>/spec.md` (the file PHASE 0b flipped to `Approved`). Add one sentence stating the spec is committed here because PHASE 0b mutated it and that mutation must be git-safe alongside the plan artifacts. The call stays UNCONDITIONAL and FAIL-SOFT as it already is (an unchanged/`already-approved` spec is a benign "nothing to commit" no-op).

Route through `instruction-author` → `instruction-reviewer` + `claude-code-guide` (ships into `.claude/`).

**Verify**: `plan/main.md` Phase-4 `--paths` lists `spec.md`; a sentence explains why; no dangling ref to a removed line; `instruction-reviewer` clean.

### Phase 2 — `/breakdown` commits the approved-plan flip — ✅ DONE 2026-07-17

Edit `src/commands/breakdown/main.md`: extend the Phase-5 WIP-commit block (`breakdown/main.md:499`) so `--paths` includes `specs/NNN-<feature>/plan.md` (flipped to `Approved` by PHASE 0b). Add the parallel explanatory sentence. Call stays unconditional + fail-soft.

Route through `instruction-author` → `instruction-reviewer` + `claude-code-guide`.

**Verify**: `breakdown/main.md` Phase-5 `--paths` lists `plan.md`; sentence present; `instruction-reviewer` clean.

### Phase 3 — `/verify` conditionally commits the Complete flip + reconcile the exclusion notes — ✅ DONE 2026-07-17

Edit `src/commands/verify/main.md`:
1. Cleanup WIP-commit block (`verify/main.md:372-376`): compose `--paths` to include `specs/<feature>/spec.md` **only when** PHASE-6 `flip-spec-status` returned `flipped: true`. Mirror the runtime-array-composition style used in `/plan`'s optional-docs block.
2. Rewrite the `verify/main.md:376` exclusion sentence ("NOT `spec.md` …") to describe the new conditional inclusion. (The `bugs/NNN-*.md` exclusion stays — bug files are a separate, deliberately-uncommitted artifact.)
3. Update `verify/main.md:29` (the Output-Artifacts summary) to match.

Then reconcile the consumer-overlay doc: `src/CLAUDE.md`'s `/verify` one-liner already says "WIP-commits the verification report (and the flipped spec)". Confirm it now reads truthfully post-fix; tighten only if the conditional ("on APPROVED") needs stating.

Route through `instruction-author` → `instruction-reviewer` + `claude-code-guide`.

**Verify**: `verify/main.md` Cleanup commits `spec.md` iff `flipped==true`; the old exclusion note is gone/updated at both `:29` and `:376`; `src/CLAUDE.md` `/verify` one-liner is consistent; `instruction-reviewer` clean.

### Phase 4 — Docs reconcile + cross-ref sweep — ✅ DONE 2026-07-17

- `CHANGELOG.md` — note the per-step status-flip commit.
- Root `CLAUDE.md` active-plans list — add the plan-65 entry.
- `src/CLAUDE.md` `/plan` + `/breakdown` one-liners — decide (per sentence-level-hallucination discipline) whether "WIP-commits the plan + handoff" needs "+ the approved-spec/plan status flip" for accuracy, or whether the existing wording is non-false and stays. Apply the minimal accurate change.
- Cross-ref grep: `commit-artifacts`, `flip-spec-status`, `check-status-and-flip`, and the three flipped-artifact paths, to confirm no other doc still asserts the flips are uncommitted.

**Verify**: grep sweep shows no doc claiming the flips are left uncommitted; CHANGELOG + both CLAUDE.md files consistent.

### Phase 5 — Consumer / testForge20 e2e (USER-DRIVEN, HARD GATE)

On a fresh consumer install: run `/specify` → `/plan` → `/breakdown`, and after each command run `git status --short` and confirm no `specs/<feature>/{spec,plan}.md` sits modified-uncommitted. Then run a feature through `/verify` to APPROVED and confirm `spec.md`'s Complete-flip is committed (not dirty). Confirm the final `/finalize` PR is byte-unchanged (the flip commits fold into the squash).

**Verify**: after `/plan`, `/breakdown`, and an APPROVED `/verify`, the flipped artifact is committed (clean `git status`); `/finalize` squash output unchanged from baseline.

## Context for next session

- The fix is **instruction-only** — reuse `artifact_helper commit-artifacts`; no helper/Python change (D3). Do not add a Python phase.
- Mechanism is D1 Option A: **extend the existing end-of-run `commit-artifacts` path-set**, not a new commit at the flip site.
- `/verify`'s inclusion is **conditional** on `flip-spec-status → flipped:true` (D2).
- Out of scope by decision: `spec-stamps.jsonl` (plan 49 D3 owns it) and the `research/…/handoff.json` back-fill (not command-triggered — OQ-2).
- The `check-status-and-flip` verb is overloaded — only the `/plan` + `/breakdown` positional-path form is a dirtying flip; the `--to <phase>` form is harmless run-state.
- Every `main.md` edit ships into `.claude/` → route through `instruction-author` → `instruction-reviewer` + `claude-code-guide`.

## When resuming work

1. Confirm Phase 0 ratification landed (check for a maintainer sign-off note here or in the conversation).
2. Execute Phases 1→2→3 in order, each behind the instruction-author/reviewer/claude-code-guide loop.
3. Phase 4 docs reconcile + cross-ref sweep.
4. Hand Phase 5 e2e to the user.
