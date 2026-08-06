# 64 — Spec-Check (+ Grill) Latest-Spec Resolution Fix

**Status**: ✅ DONE 2026-08-06 — Phases 1–3 SHIPPED, committed `4099006` (spec-check inline `ls -t` resolver + grill `_scope.py` mtime sort + prose/docstrings/help reconciled + CHANGELOG + stale plan-23 ref fixed; instruction-author→instruction-reviewer + python-engineer→python-reviewer loops, 1 low finding each, both fixed; 342 `_grill` tests green, full suite 10052 ran / 0 failures / 2 pre-existing env-only pytest-import collection errors). **Phase 4 (consumer e2e) DEFERRED by maintainer 2026-08-06 — not blocking; run opportunistically** (recipe stands in Phase 4 below). Phase 0 signed off 2026-07-17 (D1 mtime confirmed; `/grill` IN scope).
**Branch**: `develop-2.0-init`.
**Discovered**: 2026-07-16, live — ran `/specify` on `018-code-editor-extract`, then `/spec-check` resolved `001-ui-primitives` (the lowest-numbered spec) instead of the just-authored 018.

## Problem

`/spec-check` (opt-in, between `/specify` and `/plan`) auto-resolves the **lowest-numbered** `specs/NNN-*` with a `spec.md` when given no argument. So immediately after `/specify` writes feature 018, `/spec-check` targets feature 001 — never the spec the user just authored. The command's whole job is to prove the *just-written* spec's ACs are self-consistent before `/plan`, so lowest-number resolution defeats the pipeline position.

**Root cause** — `src/commands/spec-check/main.md`:
- `:75` — `for d in specs/[0-9]*/; do [ -f "${d}spec.md" ] && { echo "${d%/}"; break; }; done` iterates ascending and `break`s on the first hit → always lowest `NNN`.
- `:24` + `:72` — prose both say "lowest-numbered".

**The correct convention already exists downstream.** Every other post-`/specify` command resolves by **most-recently-modified**, keyed on the artifact it consumes:

| Command | No-arg resolution | Keyed on | Where |
|---|---|---|---|
| `/plan` | highest mtime | `spec.md` | `plan_helper.py:324` `max(valid, key=os.path.getmtime)` |
| `/review` | most-recently-modified | feature dir | `review/main.md:14` |
| `/verify` | most-recently-modified | feature dir | `verify/main.md:14` |
| `/summarize` | most-recently-modified | feature dir | `summarize/main.md:55` |
| **`/spec-check`** | **lowest-numbered** ❌ | `spec.md` | `spec-check/main.md:75` |
| **`/grill`** | **lowest-numbered** ❌ | `plan.md` | `grill/main.md:76` + `_grill/_scope.py:142-143` |

`/spec-check` and `/grill` are the only two outliers. This plan brings both onto the shared convention.

## Decisions

- **D1 — mtime, not highest-number.** Resolve by the mtime of the artifact the command consumes (`spec.md` for `/spec-check`, `plan.md` for `/grill`), matching `/plan`/`/review`/`/verify`/`/summarize`. Rationale: the user cited `/plan` explicitly ("must select latest spec, as plan"), and `/plan` uses `spec.md` mtime. Consistency across the pipeline beats highest-number's marginally-greater predictability. **Named tradeoff (carried, not hidden):** if the user edits an OLDER spec last, mtime picks that older feature — but that is *exactly* `/plan`'s behavior, so the two stay consistent (a user who ran `/spec-check` then `/plan` gets the same feature both times).
- **D2 — key on the consumed artifact's mtime, not the directory's mtime.** `/spec-check` keys on `spec.md` mtime (like `/plan`); `/grill` keys on `plan.md` mtime. This is stricter than `/review`/`/verify`/`/summarize`'s "directory mtime" prose, and it is the right choice here because both commands hard-gate on that specific artifact's presence anyway — keying on the same file the gate checks avoids a stale sibling file (e.g. a re-touched `handoff.json`) skewing the pick.
- **D3 — `/spec-check` stays instruction-only; `/grill` needs a helper change.** `/spec-check` resolves inline in `main.md` (its `resolve-scope` verb does not auto-detect), so its fix is pure prose + bash. `/grill`'s `resolve-scope` DOES auto-detect inside the helper (`_grill/_scope.py::resolve_target_feature`), so its fix touches Python + a test. Different shapes → separate phases (Phase 1 vs Phase 2), and Phase 2 is independently droppable if the maintainer wants `/spec-check`-only.
- **D4 — no new shared resolver.** Two call sites of a 1-line idiom do not justify extracting a shared helper; a premature abstraction here would couple two commands that legitimately key on different artifacts. Each site inlines the mtime pick. (Revisit only if a 3rd outlier appears.)
- **D5 — `ls -t` for the bash site, not `stat`.** `ls -t specs/[0-9]*/spec.md | head -1` is portable across BSD/macOS + GNU; `stat`'s mtime flag differs (`-f %m` vs `-c %Y`). The pre-existing `for d in specs/[0-9]*/` glob already carries the same zsh-`nomatch` exposure on an empty `specs/`, so the replacement introduces **no new** shell-compat risk (verified: empty `specs/` → `$newest` empty → prints nothing → the existing "no feature → run /specify" fallback prose fires).

## Agents & review loops (per CLAUDE.md)

- **Phase 1 (`/spec-check`, instruction-only):** `instruction-author` writes the `main.md` edits → `instruction-reviewer` reviews (intra-file logical flow + cross-ref + sentence-level hallucination). Loop until clean. `claude-code-guide` is **NOT** invoked — the change is a bash resolver + prose with no Claude Code authoring-convention surface (no frontmatter, command-mechanics, or `.claude/` structural change); invoking it would be a no-op verification. (Rule basis: claude-code-guide is mandatory only for Claude-Code-*integration* conventions.)
- **Phase 2 (`/grill`, helper + prose):** `python-engineer` changes `_grill/_scope.py` + writes/updates the test (test-first, run in the same turn) → `python-reviewer` reviews. Loop until clean. In parallel, `instruction-author` → `instruction-reviewer` on the `grill/main.md` prose. Same claude-code-guide carve-out reasoning as Phase 1.
- Orchestrator carries the cross-file precedent into every brief explicitly (instruction-* agents are intra-file only): "the target convention is `/plan`'s `spec.md`-mtime `max(...)` pick at `plan_helper.py:324`; match it, keyed on `plan.md` for grill."

---

## Phase 0 — Ratify (maintainer sign-off gate) ✅ DONE 2026-07-17

D1 (mtime over highest-number) confirmed. `/grill` IS in scope — Phase 2 builds. Build phases execute on next explicit "build" instruction.

---

## Phase 1 — `/spec-check` resolver → newest `spec.md` mtime

**Files**: `src/commands/spec-check/main.md` only.

**1a. Replace the resolver bash** (`:74-76`). From:
```bash
for d in specs/[0-9]*/; do [ -f "${d}spec.md" ] && { echo "${d%/}"; break; }; done
```
To:
```bash
newest=$(ls -t specs/[0-9]*/spec.md 2>/dev/null | head -1); [ -n "$newest" ] && dirname "$newest"
```

**1b. Reword the prose.**
- `:72` — "select the lowest-numbered `specs/NNN-*` directory that contains a `spec.md`" → "select the `specs/NNN-*` directory whose `spec.md` was modified most recently — the feature most likely just finished `/specify` (matching how `/plan` and `/verify` auto-resolve)". Keep the existing parenthetical about `resolve-scope` not auto-detecting.
- `:24` — "auto-resolve the lowest-numbered feature under `specs/` that has a `spec.md`" → "auto-resolve the most-recently-modified feature under `specs/` that has a `spec.md`".

**1c.** Confirm the two-values-forward contract (`:78` — `<feature-dir>` full path + `<feature>` slug) still holds. `dirname "$newest"` returns `specs/NNN-slug` (the same shape `${d%/}` returned) → `basename` still yields the slug. No downstream change.

### Verify (Phase 1)
- `grep -rn "lowest-numbered\|lowest numbered" src/commands/spec-check/` → **0 matches**.
- The new bash, run against a fixture where a lower-numbered spec is touched AFTER a higher-numbered one, prints the **most-recently-touched** feature dir (proven in scratch 2026-07-16: `018-c` touched, then `005-b` → resolver returns `specs/005-b`).
- Empty `specs/` → resolver prints nothing (fallback prose at `:78` handles it).
- `instruction-reviewer` returns clean (no dangling ref, `:24`/`:72`/`:78` mutually consistent, no sentence made false by the edit).

---

## Phase 2 — `/grill` resolver → newest `plan.md` mtime *(droppable per D3)*

**Files**: `src/devforge/lib/_grill/_scope.py` + its test + `src/commands/grill/main.md`.

**2a. Helper** (`_scope.py:142-143`). Replace the number-sort pick:
```python
candidates.sort(key=_feature_sort_key)
return os.path.abspath(candidates[0]), None
```
with a newest-`plan.md`-mtime pick:
```python
candidates.sort(
    key=lambda d: os.path.getmtime(os.path.join(d, "plan.md")),
    reverse=True,
)
return os.path.abspath(candidates[0]), None
```
Each `candidate` already guarantees a `plan.md` (filtered at `:133`), so `getmtime` cannot raise on a missing file.

**2b. Dead-code check.** After 2a, grep `_feature_sort_key` across `_grill/`. If auto-detect was its only caller, remove it (and its test); if it is still used elsewhere (e.g. display ordering), leave it. **Do not** leave an orphaned helper — cross-check is part of this change.

**2c. Docstrings.** Update `_scope.py:13-14`, `:85-86`, `:96` — "lowest-numbered … that has a plan.md" → "most-recently-modified … that has a plan.md".

**2d. main.md prose.** `grill/main.md:18` + `:76` — "lowest-numbered" → "most-recently-modified". Preserve `:76`'s note that `resolve-scope` performs the auto-detection (still true — only its ordering changed).

### Verify (Phase 2)
- New/updated test in `tests/lib/_grill/` (test-first, run same turn): a `specs/` fixture where a lower-numbered feature's `plan.md` is written AFTER a higher-numbered one → `resolve_target_feature(None, ...)` returns the **lower-numbered** dir (proves mtime, not number, drives the pick). Plus: explicit-arg path unchanged; no-`plan.md` dirs skipped; empty `specs/` → the existing error string.
- Full `tests/lib/_grill/` suite green (no regression).
- `grep -rn "lowest-numbered\|lowest numbered" src/commands/grill/ src/devforge/lib/_grill/` → **0 matches**.
- `_feature_sort_key` is either still referenced or fully removed (no orphan).
- `python-reviewer` + `instruction-reviewer` both clean.

---

## Phase 3 — Cross-check + docs reconcile

- `grep -rn "lowest-numbered\|lowest numbered" src/` → confirm only intended survivors remain (any OTHER command legitimately using lowest-number is out of scope; enumerate the grep result and confirm each).
- `CHANGELOG.md` — one line under the working entry noting `/spec-check` (and `/grill`, if Phase 2 ran) now auto-resolve the most-recently-modified feature, matching `/plan`.
- This plan file committed alongside the work.
- **Pre-empt future-session hallucination:** after the edits, a fresh session reading `spec-check/main.md`/`grill/main.md` must not find any "lowest-numbered" claim that the code no longer honors. The Phase-1/2 greps above are that guard.

### Verify (Phase 3)
- Repo-wide grep clean of unintended "lowest-numbered".
- Full test suite green.
- CHANGELOG updated.

---

## Phase 4 — Consumer / e2e (user-driven)

Manual: in a consumer install (testForge20 or similar), author two specs so a lower-numbered one is edited last, then run `/spec-check` (and `/grill` after a `/plan`) with no argument → confirm each resolves the most-recently-touched feature, not feature 001.

**This is the standard manual e2e gate — DONE is gated on it.**

---

## Context for next session

- The fix is small and fully scoped above; the resolver mechanics are **already verified in scratch** (`ls -t specs/[0-9]*/spec.md | head -1` picks newest, skips no-`spec.md` dirs, empty→nothing). Do not re-derive.
- `/spec-check` = instruction-only (Phase 1). `/grill` = helper + test + prose (Phase 2, droppable).
- The authoritative convention to match is `/plan`'s `plan_helper.py:324` `max(valid, key=os.path.getmtime)` on `spec.md`.
- **Do not** extract a shared resolver (D4) — two sites, different keyed artifacts.
- Route Phase 1 through instruction-author → instruction-reviewer; Phase 2's helper through python-engineer → python-reviewer AND its prose through instruction-author → instruction-reviewer. No claude-code-guide (no CC authoring-convention surface).

## When resuming work

1. Confirm Phase 0 sign-off (D1 + whether Phase 2 is in scope).
2. Execute Phase 1 via the instruction-* loop; run the Phase-1 Verify greps.
3. If Phase 2 in scope: python-engineer writes the `_scope.py` change + test first (run it), python-reviewer reviews; instruction-* loop on the prose; run Phase-2 Verify.
4. Phase 3 cross-check + CHANGELOG.
5. Hand Phase 4 (e2e) to the user.
