# RESEARCH — 2026-10-07 — `/devforge:discover` (v2) against v1 `/research`: scope mapping, size, what each addition buys

**Status**: evidence file, companion to `RESEARCH-2026-10-07-RESEARCH-AUDIT.md`. Comparison only — not a finding-by-finding audit; the observations in Part 4 are what a full read surfaced and are recorded so the discover audit, when it runs, starts from them. Nothing in `src/` was modified.

**Inputs read in full**: `src/commands/discover/main.md` at HEAD `44d9e1c` (826 lines, 88,345 bytes, zero `references/`); v1 `.claude/commands/research.md` from `main` (`9eeff96`, 232 lines, 9,566 bytes); v1 `fix.md` and `report-bug.md` headings; `src/devforge/lib/_discover/_cli.py` verb table (41 verbs); `RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md` (`:98` is the only discover row — a static call-site count; **no discover run was ever profiled**).

---

## Part 1 — Scope mapping: which v2 command v1 `/research` actually became

v1 `/research` ("Quick Feasibility & Fit Research") took a vague NEW idea — its three usage examples are *"what about WebSockets for real-time updates?"*, *"caching strategy for API responses"*, *"should we add dark mode?"* — and answered *does it fit, what exists, what are the options, proceed to `/specify`?* It never mentions bugs. v1 bug diagnosis lived in `fix.md` PHASE 2 *"Diagnose"* (choose strategy → document root cause → present diagnosis) and intake in `report-bug.md`.

v2 split that one command by the shape of the input:

| v1 piece | Went to | Evidence |
|---|---|---|
| New-capability idea → fit / exists / options / verdict | `/devforge:discover` (greenfield) | discover's deliverable is design options + build-vs-buy + fit verdict — v1's report, sharpened |
| Verdict vocabulary `Feasible / Feasible with Caveats / Not Recommended` | `/devforge:research` enhancement mode | `research/main.md:1200`, verbatim |
| Signal-based external research (Context7 / WebSearch) | `/devforge:discover` Step 2.1 | research has none (research audit finding 9) |
| Bug diagnosis (from v1 `fix.md`, not from v1 `research.md`) | `/devforge:research` bug mode | symptom memo, hypotheses, falsifiers |

So the honest pairing is **discover ← v1 research** and **research ← v1 fix's diagnose phase**. The all-commands table of 2026-10-07 paired by name and reported research at ×22; by job, v1 research's successor grew ×9 (9.6 → 88 KB) and v2 research has no single v1 predecessor to compare bytes against.

What does NOT carry over either way: v1 research was optional (*"Skip it when you already know what you want to build"*); both v2 successors are the pipeline's intake and `/specify` reads their handoff. That is a role change, not a size change, and it is why every v2 addition below exists.

---

## Part 2 — Static comparison, like for like

| | v1 `research.md` | v2 `discover/main.md` |
|---|---|---|
| Prose at invocation | 9.6 KB / 232 lines ≈ 2.4 k tokens | 88 KB / 826 lines ≈ 22 k tokens, zero `references/` |
| Helper | none | 41 CLI verbs, 40 named in spec, 54 call sites, 5,750 lines Python |
| Stops, static, clean run with `$ARGUMENTS` | 1 (save) + conditional overlap question | 13: echo-back 1 + references 1 + design-reference 1 + 8 dimensions + coverage 1 + save 1 (`AskUserQuestion` × 11 sites, free-text prompts × 10) |
| External research | conditional on 5 signals; skipped when none | unconditional Stream A (WebSearch → Context7 → WebFetch), gap-narrowed by Step 2.0 |
| Codebase check | Grep / Glob / Read ≤ 10 files | CBM chain: Step 2.0 `search_graph` + `search_code` per verb; Step 2.2 docs via graph + 4-step chain |
| Report | fixed template, LLM-composed in the console | helper-rendered from state; 7 `verify` invariants A–G |
| Artifacts | `research/<date>-<slug>.md`, on request | feature dir + branch + `discovery-report.md` + `discover-handoff.json` + `[WIP]` commit; conditional `intake-rerun.json` |
| Runtime | 14 min / 98 turns / 4 stops (v1 research median, 92 runs) | **never profiled** — the diagnosis has no discover run |
| Verbs with no spec caller | — | `append-outcome` (CLI only; same orphan class as research's) |

The stop count is the headline: v1 asked nothing before producing a usable feasibility report; discover asks 12 questions before investigating — one more dimension-pair than research (8 vs 6), so the rubric cost is higher here than in the command the research audit measured.

---

## Part 3 — Section-by-section: what v1 did → what discover does → what the change buys

| v1 `/research` | v2 `/discover` | Buys | Costs |
|---|---|---|---|
| PHASE 1 Load context: constitution, memory, CLAUDE.md, architecture, scan `specs/` for overlap → ask whether to proceed | 0.1 `preflight` + memory excerpt; pre-rubric docs scan via CBM (`:268-280`); **overlap check dropped** (`:735` *"this command does no topic matching"*) | setup-chain gate; memory carried into scoping | 1 CBM `get_architecture` + `search_graph` in place of 2 reads; a lost v1 behaviour (duplicate feature dirs, user told to delete) |
| — | 0.4 suspected-fit classification + 0.5 intake echo-back (`:92-167`) | the user sees the framework's reading before cost is spent (plan 18 Step 5) | 1 stop, 2–3 helper calls |
| — (v1 asked no scoping questions) | Phase 1: references prompt, design-reference prompt, 8-dimension rubric one turn each, conflicts, drift, coverage decision (`:203-375`) | a typed `ScopingMemo` the handoff carries; per-dimension user commitment | **11 stops**, ≈ 20 helper calls; the same contradiction research carries — `:116` *"ONE echo-back confirmation and ZERO interrogation"* vs `:207` *"ask each dimension question separately and wait for the user's answer in its own turn"* |
| PHASE 2: 3–7 keywords → Grep/Glob/Read → existing infrastructure, patterns in use, reusable abstractions, dependencies | Step 2.0 verb extraction → `search_graph` + `search_code` per verb → `record-prior-art --source internal:` + `record-integration-touchpoint` per hit → gate message to the user (`:381-430`) | **internal-first before web**, and invariant G: a Build recommendation must cite the internal path or say what it does not cover — v1 could recommend building what already existed | per-hit setter pairs; CBM (OQ-2) |
| PHASE 2 Step 3 constitution check | setter 7 `set-constitution-constraints` (`:603`) | same | one call per rule |
| PHASE 3 signal-based external research, skipped when no signal | Step 2.1 Stream A, unconditional, gap-narrowed, `record-prior-art` per result (`:432-452`) | current-version docs via Context7; gap narrowing avoids re-surveying what Step 2.0 found | always runs, even for an internal-only feature; per-result setter |
| — | Step 2.2 fit-check: docs via graph, CBM chain, `record-integration-touchpoint`, `record-fit-assessment --user-expected / --reality`, `set-overall-fit`, `set-effort-estimate`, `set-fit-rationale` (`:454-510`) | **belief vs reality** as a first-class finding — v1 had no equivalent | ≈ 3 calls per touchpoint + 3 aggregates |
| PHASE 4 report: summary, codebase findings, constraints, Option A/B with pros/cons/complexity, external, complexity, recommendation | Phase 3 setters: summary, design options as data-model / API / state-machine shapes (not library lists — a real sharpening), recommended option, **build-vs-buy**, **absence probe** via `git log -S` / `--diff-filter=D` when Build + 0 internal hits, **derisk plan**, constitution, verdict, recommendation, next-step; `verify` A–G; `render` (`:512-672`) | three decisions v1 left implicit (build-vs-buy, derisk, absence) made explicit and checked | ≈ 12 setter calls + verify loop ≤ 3 |
| PHASE 5 ask to save → `research/<date>-<slug>.md` → next steps | Phase 4: save + ticket in one call, `allocate-feature-dir`, branch, re-render, write, `finalize-handoff`, `commit-artifacts`, exit-3 recovery, attach mode (`:674-826`, 24 KB) | pipeline artefacts `/specify` consumes | 6 calls; 24 KB of prose, mostly rare arms |
| — | 0.6 grill re-entry, attach mode, `intake-rerun.json` (`:169-201`) | the backward seed loop | ≈ 6 KB of prose, read on every run, taken on almost none |

**What discover does better than v1, honestly** (the do-not-cut candidates): Step 2.0 internal-first + invariant G; the fit-check's belief-vs-reality split; build-vs-buy as a decision with a reasoning field; design options as shapes rather than libraries; the derisk plan; the absence probe (incident-driven, plan 73 D6). None of these is a stop.

**What v1 had that discover lost**: the `specs/` overlap check before starting (`:735`); the *skip external research when no signal* rule (Stream A is unconditional); v1's *"Not recommended → lead with the alternative"* — discover's `Reconsider` has no alternative slot (`set-recommendation --action` could carry one; nothing mandates it).

---

## Part 4 — Observations from the full read (seeds for the discover audit, not findings yet)

1. **Same rubric contradiction as research, worse by two dimensions.** `:116` (proportionality: one confirmation, zero interrogation) vs `:207-209` (eight separate turns, never skip, never fabricate a mode). Research audit finding 3 and OQ-1 apply with 8 dimensions instead of 6; the batched-table fix is the same and should be decided once for both commands.
2. **Discover knows the price of a reset and research does not.** `:731` refuses to send the user back to re-invoke on a slug error because *"Phase 0.3 resets the memo and report unconditionally … the eight rubric answers and the whole Phase 2 investigation would be thrown away over a name the user can fix in one turn"* — yet `:510` and `:658` still name *re-run from scratch* as the 4th-failure exit. The sentence at `:731` is the argument research audit finding 1 makes; discover already contains it.
3. **Same CBM posture, same false enforcement claim.** `:275` and `:460` route docs through the graph; `:467` says raw reads *"will be blocked by runtime hooks on the first matched call per session"* — closer to the truth than research's `:412` (it names "first call"), but still used as the reason to forbid `Read` on markdown. OQ-2 applies; discover's Step 2.0 is one of the three graph-shaped mechanisms a "no" would re-spec.
4. **Finalize-only guard, same class as research finding 7.** `:595`: `finalize-handoff` rejects an absence-founded report with no probe *"where the report is already on disk and only the handoff fails"*. One invariant (H) in `verify` closes it.
5. **Sibling inconsistency.** Turn cap 3 follow-ups per dimension (`:224`) vs research's 2 (`research/main.md:233`) for the same mechanism; discover has no cost-gate stop (good — research finding 6 is the one to remove, not the one to copy).
6. **Size shape.** 88 KB with zero references: 0.6 re-entry ≈ 6 KB, Phase 4 24 KB with attach / exit-3 arms, the memory-excerpt semantics paragraph (`:45-54`) duplicated verbatim from research — a Conventions block and `.devforge/command-refs/discover/` would take it to ≈ 50 KB. Boilerplate: *"copy … VERBATIM"* × 14, *"end the turn"* × 21, *"hands the choice back"* × 7, `MANDATORY` × 6 (research: 33 / 16 / 12 / 27 — discover is already the leaner sibling).
7. **Never measured.** No discover run exists in the diagnosis. Every number above is static. The measurement plan (124 item 7) must include one discover run before any of this is cut.

---

## Part 5 — Verdict in one paragraph

By job, `/discover` is v1 `/research` grown ×9 in bytes and ×13 in stops, and the growth is not uniform in value: the investigation layer (Step 2.0, fit-check, build-vs-buy, absence probe, invariant G) is a genuine improvement over v1 and costs calls, not stops; the intake layer (echo-back + 8-dimension rubric + two supplementary prompts + coverage decision) is where the stops are, and it carries the same proportionality contradiction the research audit recorded. The decisions this comparison feeds — OQ-1 (which rubric questions must be asked) and OQ-2 (CBM) — are the same two the research audit left open, and they should be taken once for both intake commands rather than twice.
