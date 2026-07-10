# 55 — Standalone Bug-Fix Lane

**Status**: DEFERRED (analysis captured, NOT started — no code) — 2026-07-10 on `develop-2.0-init`
**Author basis**: competitive-landscape review (Spec Kit / BMAD / Kiro / Task Master / Agent OS / Cline-Roo / AIDLC) → scope-adaptive-depth discussion → narrowed to the bug-fix middle band.

## Why this exists

A DEFERRED record so the analysis is not re-derived next time a standalone bug makes the full pipeline feel like a sledgehammer. **Nothing is committed to build.** The revival trigger + open decisions are below.

## The gap (confirmed against code, not guessed)

For a **standalone, already-filed bug** (e.g. reported post-ship, unrelated to an open feature window) there is **no lightweight lane**. The only entry is the full spec-driven pipeline (`/research`|`/discover` → `/specify` → `/plan` → `/breakdown` → `/implement` → …), which is disproportionate for a small known defect.

`/fix` looks like the answer but is **hard-locked to the in-pipeline window**:
- `src/devforge/lib/_fix/_window.py` — `in_fix_window()` requires post-`/implement` / pre-`/summarize` state (all task files terminal, no `summary.md`, spec not `Complete`).
- `src/devforge/lib/_fix/_findings.py` — input is `review.md` / `verification.md` NEEDS-WORK issues, i.e. pipeline-window artifacts, **not** a standalone bug file.
- Plan `26` D2: "everywhere else file-only — **never a cold/free-text fixer**." D4: `/fix` writes NO `bugs/` files; the `Open → In Progress → Fixed` lifecycle stays MANUAL.

So `report-bug` **files** a standalone bug (`bugs/NNN-*.md`, `Source: manual`, `Feature: N/A`) but **nothing resolves it** — the bug lifecycle has a producer and a status field and no resolver command.

## The input contract already exists (and is near-perfect)

- `report-bug` is a promoted command writing `bugs/NNN-*.md` — standalone/manual bugs are already first-class (`Source: verify | manual`, `Feature: N/A for standalone bugs`). See `27-REPORT-BUG-COMMAND-PLAN.md`.
- The bug format (`src/devforge/storage-rules.md` §Bug File Format) carries a **`File(s)` table** (area/function refs) and a **`Fix Notes`** slot ("root cause, what changed, commit ref — filled in AFTER resolution").

Two facts that shape any future design:
1. **Filed bugs are OBSERVED, not DIAGNOSED** — `Fix Notes` (root cause) is filled *after* resolution, so at fix-time the cause is unknown. The diagnosis step must be a **real investigation**, not a rubber-stamp. This structurally prevents the lane degenerating into symptom-patching.
2. **The `File(s)` table is a STARTING scope, not authoritative** — human/verify-authored, area-level. Diagnosis must be free to *expand* the file set to the true cause (root cause ≠ symptom location). That expansion is what a blast-radius tripwire measures.

## Candidate shape (IF built)

`/fix <bug-id>` (or a sibling command — see Option 2) →
1. Read `bugs/NNN-*.md`. `File(s)` = starting surface; `Description`/`Evidence` = the requirement (the filed bug is the scope contract — this is what plan 26's free-text fear did NOT have).
2. **Diagnose (mandatory)** — code-read root cause; escalate to `runtime-debugger` when the cause isn't in the read. Expand the file set to the cause.
3. **Blast-radius tripwire (CBM)** — measure callers / cross-layer on the expanded set. Balloons past bounds, OR touches new surface (= it's a feature in bug clothing) → **bounce to `/specify`**, refuse the lane. Fails toward rigor.
4. **Existing back-half, unchanged** — `verify-touched` + self-repair → four-reviewer panel → forcing-functions gate → `[WIP]` commit (wrapper-aware, already there). The cheap mechanical floor never goes dark.
5. Write `Fix Notes` + flip `Open → Fixed` (subject to Decision D-writeback below).

### The load-bearing design principle behind this

The pipeline splits into **cheap mechanical gates** (forcing-functions, roster/handoff-schema validation, design-token detector — ~zero tokens; the quality FLOOR) vs **expensive LLM deliberation** (research rubric, `/grill`, four-reviewer panel, multi-pass `/audit`, refutation ensembles — real tokens; the CEILING). A light lane sacrifices quality **only if it strips a gate that would have caught a real defect** — and gates are cheap, so there is no reason to strip them. **Keep the floor, lower the ceiling.** Diagnosis is FLOOR (load-bearing for bug-fixing), not ceiling — the lane may skip spec/plan ceremony but NOT diagnosis.

**Coupling caveat (why "just enter mid-pipeline" is wrong):** forge's gates are coupled to their producing stages (design-anchor captured at `/research`+`/specify`; ACs at `/specify`). Skipping a stage silently takes its gate dark. Any real light lane must fire the floor gates standalone, decoupled from their parent stage — that is the non-trivial part.

## Why DEFERRED (two independent reasons)

1. **It reverses settled plan-26 decisions, on weak grounds.** When plan 26 reversed plan 21 D1, it argued plan 21's *premise was false*. Here nothing about D2/D4 is *wrong* — the `report-bug` substrate existed when plan 26 was written; plan 26 *could* have built cold-start and chose not to. So this is **use-case discovery ("bugs feel frequent"), not error discovery** — a change of mind, not a corrected mistake. Forge's anti-drift culture rightly resists that.
2. **No evidence the band is frequent.** "Some bugs," not "every day." Forge's own YAGNI lesson (Track A rollback — build for real consumers, not speculative ones) applies. The middle band (too small for full pipeline, too risky for by-hand) is asserted, not measured.

## Three ways to proceed IF revived (ranked by reversal cost)

- **Option 1 — Minimize the reversal.** Keep D4 fully (`/fix` writes no `bugs/` files; the human flips `Open→Fixed` by hand, matching the existing file-by-hand workflow). Only cold-start entry is new → shrinks the change to one bent decision (D2's "outside the window, file-only"). **Lowest churn.**
- **Option 2 — Sibling command, zero reversal.** A dedicated standalone-bug resolver over the same `_fix` back-half engine, leaving `/fix` untouched (D2/D4 both about `/fix`, both intact). **Smell:** `/review` vs `/verify` earned separation because *outputs* differ (findings vs verdict); here the output is identical (a fix commit), only the *input* differs — thinner grounds, and fix-command proliferation is a flagged smell. Avoids reversal by spending ceremony.
- **Option 3 — Build nothing (current state).** Recommended until the band proves itself.

## Revival trigger (instrument the pain first)

Do NOT build on assertion. Over the next **3–4 bugs** that make the full pipeline feel disproportionate, record:
- how many files the fix actually touched,
- did it hit a gated surface (auth / migration / design / public API),
- would a single reviewer have caught what four would.

If that band is **frequent AND consistently low-blast-radius** → real case; have the reversal debate with evidence, pick Option 1 or 2. If it's 2–3 annoying bugs → it was friction to route around by hand, not a plan. Delete this file if the trigger never fires.

## Open decisions (settle only if revived)

- **D-writeback** — flip `Open→Fixed` + fill `Fix Notes` automatically (reverses plan 26 D4) vs manual flip (Option 1, preserves D4). Leaning manual — matches how bugs are already filed by hand.
- **D-batch** — `/fix <id>` single-bug vs drain-all-`Open`. Leaning single — batch = scope-balloon + mixed-surface in one commit.
- **D-diagnosis-agent** — inline code-read by default, escalate to `runtime-debugger` only when the cause isn't in the read (avoid paying an agent dispatch on every trivial fix).
- **D-command-surface** — overload `/fix` (Option 1) vs sibling command (Option 2).

## Cross-references

- `26-REINTRODUCE-FIX-PLAN.md` — built `/fix` as in-window-only; D2 (no cold/free-text fixer) + D4 (no `bugs/` writeback) are the decisions this plan would revisit.
- `27-REPORT-BUG-COMMAND-PLAN.md` — the `report-bug` producer + `bugs/NNN-*.md` format this lane would consume.
- `21-DROP-FIX-REFACTOR-PLAN.md` — original `/fix` drop; carries the fix-command-proliferation-is-a-smell context relevant to Option 2.
- `src/devforge/storage-rules.md` §Bug File Format + §Bug lifecycle — the input contract.
