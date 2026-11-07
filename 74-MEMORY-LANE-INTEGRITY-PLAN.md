# 74 — Memory Lane Integrity

**Status:** **✅ DONE (build) 2026-08-13 — all build phases shipped.** Phase 0 RATIFIED (every decision D1–D8 and every open question OQ-1–OQ-6 carries a recorded outcome inline — see `### Phase 0 ratification record (2026-08-13)` under Phase 0; the disposition table ratified **exactly as drafted, 13 `READS` / 7 `N/A`, no row overridden**). Phases 1–6 + OQ-5 shipped on `develop-2.0-init` in seven commits: `e3b63cb` Phase 1 (resolver), `fde6cfc` Phase 2 (dead-path sweep), `ebb8f1f` Phase 3 (falsifiable gate), `95cb64b` Phase 4 (intake lane), `a45e162` OQ-5 (install-clobber guard), `9a91998` Phase 5 (disposition + maintainer gate), `ac2a1e0` Phase 6 (docs). Full suite 10727 passed, 0 failures; `scripts/verify-memory-lane.py` and `scripts/verify-agent-reachability.py` both PASS and are independent.

**Phase 7 (consumer e2e) is DEFERRED by the maintainer 2026-08-13 — the maintainer intends to run it later. It is NOT waived and NOT executed.** Read that precisely: the mechanism is **build-verified, not consumer-validated**. Every phase closed behind its review loop and the gate proves coverage, but nothing here has been exercised against a real consumer install, and a decision to defer a check is not evidence the check would pass. The recipe stands under `## Phase 7` as the validation procedure. The single highest-value item in it is the motivating incident itself: re-run that ticket through `/devforge:research` and confirm the memory entries reach evidence-gathering **before scoping is committed** — that is a known-answer regression anchor, since the correct outcome is already known from the second run of the original A/B.

**This plan DOCUMENT stays untracked deliberately** (like `73-` and `75-`): it names consumer installs and a client repo path, and this repo is PUBLIC. The commit state is therefore SPLIT — code committed, plan doc untracked — the same disposition plan 73 carries. **[UPDATED 2026-11-07 — maintainer directive: plans 73, 74 and 75 were committed after their client identifiers (install paths, the backend repo name, ticket IDs, consumer commit SHAs, component, file and symbol names) were replaced by placeholders such as `<v1-install>`, `<v2-install>`, `<backend-repo>`, `TICKET-B`, `<sha-B>`, `ChildRow.vue` and `isVariantItems`. The untracked disposition stated here is superseded; the placeholders are not the consumer codebase's real names.]**

**Four follow-ups were deliberately NOT taken; each is a separate decision, none is a leftover step of this plan.** (1) `.devforge/project-config.json` has the IDENTICAL `install.sh` bulk-`cp -R` clobber exposure that OQ-5 fixed for memory, with a LARGER blast radius — it ships as an all-null stub, `/devforge:configure` populates it with `PACKAGE_STACKS` / `WORKSPACE_MODE` / every build-lint-test command, and `install.sh` contains zero references to it, so a re-install silently resets it and breaks scope-aware verify plus every `PACKAGE_STACKS`-dependent command until someone re-runs `/devforge:configure`. (2) Running the test suite writes `src/devforge/.generate-docs-trace.log` into the framework source tree, which `install.sh`'s stray-user-state guard then aborts on — so test-then-install currently fails for anyone; the guard is right to fire, the tests should not create the file it fires on. (3) Six of the seven preflights compute `memory_state` via `read_memory_context` and drop it, emitting only `present`/`excerpt`, so those six specs judge stub-vs-populated by inspecting an excerpt where a mechanical value already exists. (4) `src/agents/architect.md` Rule 8 has the architect read memory independently, so memory now reaches it by two routes (its own unbounded read + the orchestrator's bounded excerpt) — not a defect, a reconciliation decision.
**Type:** BUILD plan (one shared helper module + a dead-path sweep + a mechanical gate) with a substantial DECISION component (the per-command memory disposition).
**Branch:** `develop-2.0-init`.
**Created:** 2026-08-12, seeded from a `/devforge:research` run in a consumer install that re-derived context the persistent memory file already held.

---

## Problem — memory is write-mostly, and four commands read a path that does not exist

`.devforge/memory.md` is the framework's persistent cross-session lessons file. It is written by two commands (`/implement`, `/verify`) and committed by a third (`/finalize`) — and its CONTENT is routed to an executor in exactly **two** places in all of `src/commands/**`: `implement/references/agent-brief.md:12` and `fix/main.md:157`. Four commands cite a dead memory path (`.claude/memory/MEMORY.md` or a bare `MEMORY.md`), as do three helper modules and one manifest entry; that path exists in no consumer install. Seven helper preflights build a `memory_excerpt` field that **no command spec ever consumes**. Nine of the twenty emitted commands never mention memory at all.

The failure has four distinct mechanisms, and a fix that addresses only the first leaves the other three live:

1. **Dead path.** `/specify`, `/audit`, `/plan`, `/breakdown` cite `.claude/memory/MEMORY.md` (or a bare `MEMORY.md`) in prose; `_specify/_schema.py`, `_review/_preflight.py`, `_audit/_preflight.py` cite it in code. Nothing errors — the read simply returns nothing, forever.
2. **Certified read of a nonexistent file.** `/specify`'s Phase 1 → Phase 1.5 gate requires four mandatory base reads, one of which is the dead path, and the recording verb validates only that a *string* was passed. Every `/specify` run in history has recorded having read a file that has never existed, and the mandatory gate went green on that record. **A forcing function that certifies a read of a nonexistent file is worse than no forcing function** — it manufactures false confidence in exactly the dimension it was built to protect.
3. **Orphaned payload.** Seven preflights emit `memory_present` / `memory_excerpt` — five reading the live path, two reading the dead one. `grep -rn "memory_excerpt\|memory_present" src/commands/` returns **zero hits**. The data is produced correctly and dropped on the floor — plan 41's type-3 orphan (a value that is computed, rendered into a JSON contract, and gates/informs nothing), applied to data rather than to findings.
4. **Truncation to the structurally-empty prefix.** The one command with a consumed read (`/implement`) reads a **5-line digest**; the preflight excerpts are 40 lines. The shipped stub's four section headings and their HTML comments occupy the top of the file, and the pipeline's own writer appends at EOF — so for any file whose additions came only from the pipeline, the 5-line digest is provably the stub preamble and nothing else.

**The always-on channel already says the right thing and was not enough.** `src/CLAUDE.md:205` (Key Rule 4, "**Memory is persistent** — check `.devforge/memory.md` for lessons from past sessions") and `src/constitution.md:238` (§6.3 Read-First Principle **[universal]**, item 4: "Check memory for past lessons about this area") both name the obligation, both are in always-on consumer context, and neither prevented the motivating incident. Adding a third always-on rule is a **Non-goal** (see below) — the instruction is not missing; the enumerated phases that do the work never execute it.

## Motivating incident

A `/devforge:research` run in the consumer install `<v2-install>` (`specs/<feature>/research-report.md`) investigated `catalogId`-related dead code while `.devforge/memory.md` held, unread, two directly-applicable entries: that the backend repo is locally readable at `<backend-repo>`, and the standing lesson "read the backend mapper BEFORE scoping — half the ticket may already be done or belong to the other repo."

A second run of the same ticket in a different install (`<v1-install>/research/<v1-report>.md`) used that backend evidence and found roughly **4× the removable surface**.

`/research` is the command with the strictest evidence-grounding machinery in the framework (plans 67 + 69: mode-independent caller enumeration, declared caller totals, per-caller scope classification) — and it has **zero** memory references. The strongest intake lane is the one with no memory read at all.

## Verified state (2026-08-12)

Everything below was verified against the live repo and two consumer installs this session. Re-verify only if `src/` changed since. **Do not re-derive these; they are the plan's factual base.**

### Consumer ground truth

- **[VERIFIED]** In both `<v1-install>` and `<v2-install>`: `.devforge/memory.md` EXISTS (49KB / 151 lines in forge20). `.claude/memory/` does NOT exist. A repo-root `MEMORY.md` does NOT exist.

### Dead-path sites (`.claude/memory/MEMORY.md` or a bare `MEMORY.md`)

Command prose:

- `src/commands/specify/main.md` — **five** `.claude/memory/MEMORY.md` occurrences at `:178` (the §1.2 heading), `:183` (the literal `record-input-read --path ".claude/memory/MEMORY.md"` call), `:243` (the four-mandatory-base-reads gate sentence), `:470` (the `greenfield_feature` mandatory-read slot list), `:497` (the cross-reference instruction) — plus a bare `MEMORY.md` at `:931`.
- `src/commands/audit/main.md` — `.claude/memory/MEMORY.md` at `:146` (the `preflight-context` description); bare `MEMORY.md` at `:33` and `:282`.
- `src/commands/plan/main.md:611` — bare `MEMORY.md` ("**Memory check** — consult MEMORY.md for lessons about similar technical decisions").
- `src/commands/breakdown/main.md:104` — bare `MEMORY.md` ("`MEMORY.md` — past lessons about similar decompositions").

Helper code:

- `src/devforge/lib/_specify/_schema.py:230` — `PHASE1_MANDATORY_READS` tuple entry (the gate's own literal).
- `src/devforge/lib/_specify/_schema.py:291-292` — the `MANDATORY_READS_BY_TYPE["greenfield_feature"]` slot, whose second element is a human-facing LABEL (`"MEMORY.md prior-feature lessons"`), not just a path.
- `src/devforge/lib/_specify/_schema.py:309` — `_RENDER_SECTION_ORDER`, a **render-group KEY**, not a path that is read. See D3.
- `src/devforge/lib/_review/_preflight.py:76` (docstring), `:171` (comment), `:172` (`os.path.join(workspace_root, ".claude", "memory", "MEMORY.md")`); the excerpt is `mem_lines[:40]` at `:177`.
- `src/devforge/lib/_audit/_preflight.py:8` (module docstring), `:309` (function docstring), `:381` (comment), `:382` (the `os.path.join`).
- `src/devforge/lib/_audit/_scope.py:548` and `src/devforge/lib/_audit/_cli.py:1699` — prose-only mentions of "MEMORY.md excerpts" in `--extra-context-file` help text.
- `src/manifest.json:38` — `".claude/memory/**"` in `projectOwned.patterns`. See the manifest finding below.

### Correct-path sites

- `src/devforge/lib/_verify/_preflight.py:183`, `_summarize/_preflight.py:197`, `_finalize/_preflight.py:347`, `_fix/_preflight.py:180`, `_grill/_preflight.py:194` — each `os.path.join(workspace_root, ".devforge", "memory.md")`, each emitting `memory_present` + a 40-line `memory_excerpt`.
- `src/devforge/lib/_implement/_cmds_preflight.py:420-421` — the live path, read as a digest.
- `src/devforge/lib/_implement/_cmds_session.py:491-499` — the write path (append under `## Task Outcomes`).
- `src/commands/finalize/main.md:153,156` — the plan-49 D3 safety-net commit path list (a COMMIT, not a read).
- `src/commands/fix/main.md:157` — prose instructing that the brief carry "the `.devforge/memory.md` pitfalls".
- `src/commands/implement/references/agent-brief.md:12` — the ONLY place in `src/commands/**` that instructs an executor to use memory CONTENT.
- `src/CLAUDE.md:169`, `:205`, `:308` — all three cite the live path correctly.
- `src/devforge/storage-rules.md:89` — the plan-49 disposition row (`memory.md` | VERSIONED | folds into the `/devforge:finalize` squash).

### The four mechanisms, each with its anchor

- **[VERIFIED — the certified nonexistent read]** `_specify/_cmds_phase01.py:111-133` (`cmd_record_input_read`) calls `_validate_scalar(args.path, ...)` at `:117` and records the string; there is no existence check. `cmd_phase1_finalize` (`:136-154`) compares the recorded path STRINGS against `PHASE1_MANDATORY_READS` and returns 2 only on a missing string. So `record-input-read --path ".claude/memory/MEMORY.md"` (`specify/main.md:183`) satisfies the gate unconditionally.
- **[VERIFIED — the orphaned payload]** `grep -rln "memory_excerpt" src/devforge/lib/` → **seven** files (`_verify`, `_summarize`, `_finalize`, `_fix`, `_grill` at the live path; `_review`, `_audit` at the dead one). `grep -rn "memory_excerpt\|memory_present" src/commands/` → **zero hits**. `memory_digest` appears exactly twice in `src/commands/**`: `implement/main.md:103` (inside the preflight JSON field list, with no instruction to use it) and `implement/references/agent-brief.md:12` ("the preflight `memory_digest` is a starting point; the agent **may** read the full file" — permissive, not directed).
- **[VERIFIED — the truncation]** `_implement/_cmds_preflight.py:102` sets `DIGEST_LINES = 5`; `:421` builds `memory_digest` from the first 5 **non-blank** lines (`:56`). The shipped stub `src/devforge/memory.md:1-13` opens with `# Project Memory`, `## Architecture Decisions` + its HTML comment, `## Known Pitfalls` + its HTML comment — exactly five non-blank lines. `_implement`'s writer appends under `## Task Outcomes`, and `_append_under_section` (`_cmds_session.py:122-136`) appends a missing section **at EOF** (verified: the missing-section case is handled, not a bug). Therefore, for any memory file whose additions came only from the pipeline's own writers, the 5-line digest is byte-identical to the stub preamble and carries zero lessons.
- **[VERIFIED — the dead path is a known, never-swept class]** Plan 22 finding F fixed exactly this bug in `/verify`. The framework then annotated it in two more files rather than sweeping it: `_fix/_preflight.py:7` ("does NOT read .claude/memory/MEMORY.md") and `:179` ("DO NOT change to .claude/memory/MEMORY.md (plan-22 finding F)"), and `_grill/_preflight.py:191-193`, which states outright that "`_review/_preflight.py` carries a bug where it checks `.claude/memory/MEMORY.md`". **Two hand-written "do not change this" comments are the cheapest available proof that a duplicated literal cannot be held correct by convention.**

### The `src/manifest.json:38` finding (the brief's explicit verify item — RESOLVED, not left open)

`projectOwned.patterns` is read once, at `update.sh:418`, and consumed once, at `update.sh:670-673`, where it is expanded against the target tree solely to compute a count for the summary line `SKIP  <N> project-owned file(s)`. `grep -rn "PROJECT_OWNED\|projectOwned" *.sh` returns four hits, all in `update.sh`, all in that path. **`projectOwned` protects nothing** — a file is safe from overwrite because it is absent from `templateOwned` / `templateDerived` / `mergeFiles`, not because it is listed here.

Consequences: (a) `".claude/memory/**"` at `:38` is a dead documentation entry whose only runtime effect is a cosmetic count; (b) the LIVE `.devforge/memory.md` has **no** `projectOwned` entry, so the manifest currently documents protection for a path that does not exist and documents nothing for the path that does.

### Adjacent finding — `install.sh` overwrites memory (verified, NOT a read-path bug)

`install.sh:271` runs `cp -R "$TEMPLATE_DIR/src/devforge/." "$TARGET_DIR/.devforge/"`, which copies the shipped 13-line stub `src/devforge/memory.md` over the target's `.devforge/memory.md`. The stray-user-state guard at `install.sh:260` lists `init.yaml`, `configure.yaml`, `configure.yaml.lock`, `constitute.json`, `constitute.json.lock`, `.preflight-stamp`, `.generate-docs-trace.log` — **not** `memory.md`, because `memory.md` genuinely IS a framework-shipped template (the initial stub), unlike those files. `update.sh` does not copy it (`memory.md` is absent from `manifest.json` `templateOwned`). So a re-run of `install.sh` against a populated install erases accumulated memory. Recorded as **OQ-5**; a plan named "memory lane integrity" that leaves this live would be misnamed.

### Two stale claims discovered in passing

- `src/devforge/memory.md:4` — the stub's Architecture Decisions section is annotated `<!-- Populated during constitute ... -->`. `grep -in memory src/commands/constitute/main.md` returns three hits (`:37`, `:84`, `:200`), **all** meaning working memory ("hold all four inputs in memory before composing"). `/constitute` writes nothing to `.devforge/memory.md`. This is plan 41's type-2 shape: a declared step with no executor.
- `src/CLAUDE.md:295` — "history lives in task completion notes (`specs/`) and `MEMORY.md`". A bare stale `MEMORY.md` in the consumer overlay, three lines from the correct citation at `:308`.

### Re-verification 2026-08-13 (post-plan-73)

Plan 73 (`73-LITERAL-ARCHAEOLOGY-EVIDENCE-ARM-PLAN.md`) SHIPPED its `src/` work after this plan was drafted, which is exactly the "re-verify only if `src/` changed since" trigger the section header names. The re-verification was performed on 2026-08-13. Four results:

- **(a) The factual base HOLDS — re-confirmed exact against live `src/`.** Every dead-path anchor above, the seven-preflight orphan count, `grep -rn "memory_excerpt\|memory_present" src/commands/` → **zero hits**, `grep -rl "\.claude/memory" tests/` → **10 files** (the same 10 enumerated in OQ-4), `DIGEST_LINES = 5` (`_implement/_cmds_preflight.py:102`, consumed at `:421`), the shipped stub's five non-blank preamble lines, and `_shared/` already being present in BOTH installer always-copy sets (`install.sh:150`, `update.sh:156`) all re-checked and unchanged. **Nothing in the four-mechanism analysis, the disposition table, or any decision rests on a claim that moved.**
- **(b) ONE line-number drift, content identical.** `src/commands/plan/main.md:611` is now **`:614`** (+3) — plan 73's Phase 5 appended architect sub-question 10 to that file, shifting everything below it. The line itself is byte-unchanged ("`6. **Memory check** — consult MEMORY.md for lessons about similar technical decisions.`"). **Three sites in this plan carried the stale `:611` anchor and meant `:614`:** the dead-path list above, disposition-table row 9, and Phase 2b's task list. **[CORRECTED 2026-08-13 — the two LIVE-INSTRUCTION sites now cite `:614` in place: disposition row 9 (`was :611 pre-plan-73`) and Phase 2b's edit target. The dead-path list entry at `:45` deliberately KEEPS `:611`, because this Verified-state section is dated-and-frozen history — it records what was true on 2026-08-12 — and this bullet is its correction. So exactly ONE `:611` anchor remains in this file as a live-looking citation, and it is that dated one.]** Every OTHER line anchor in this Verified-state section re-confirmed exact — this is the only one that moved.
- **(c) OQ-5's alternative route is CLOSED by verification, not open.** OQ-5 recorded that "whether `install.sh` honours `copyIfMissing` at all was NOT verified this session and must be checked before that route is chosen." It has now been checked: `copyIfMissing` is read ONLY by `update.sh` (`:419` reads the patterns, `:531` filters them to missing files, `:1001` executes the copy); `grep -n copyIfMissing install.sh` returns **ZERO hits**. **`install.sh` does not honour `copyIfMissing`, so the manifest route cannot fix the install clobber at all** — it is not merely the un-preferred option, it is unavailable. The inline `install.sh` guard is the only viable route, and a future session must not re-propose the manifest alternative.
- **(d) A NEW post-73 boundary this plan did not anticipate — do not cross it.** Plan 73's D7 shipped `EvidenceLanes` on the research handoff (`src/devforge/lib/_research/handoff_schema.py:1332`): a **fixed four-bool** self-declaration (`static_graph` / `text_search` / `runtime_probe` / `history`, validated at `:1382`) carried on `Handoff.evidence_lanes` (`:1428`) with a declaration-EXISTS guard at `finalize-handoff`. This plan's **Phase 4 adds a memory read to `/research`, which is a FIFTH evidence source outside that vocabulary.** The constraint, stated explicitly so it is not rediscovered at build time: **Phase 4 adds the memory read WITHOUT adding, renaming, or otherwise touching the `EvidenceLanes` enum.** Two independent reasons, either alone sufficient: (i) this plan's own Non-goals forbid any change to plan 73; (ii) `75-INVESTIGATION-SEARCH-HARNESS-PLAN.md`'s D6 explicitly claims the lane-vocabulary extension as ITS work. A future session must not "helpfully" add a memory lane here — that is plan 75's decision to make, not this plan's. **[BOOKKEEPING 2026-08-14 — plan 75's two touchpoints with this plan, both now settled.** (1) **Its D6 lane-vocabulary extension is DEFERRED**, ratified at plan 75's Phase 0 on 2026-08-14 — so `EvidenceLanes` is byte-unchanged by BOTH plans and no memory lane is pending from either. Reason (ii) above stands exactly as written: the extension is still plan 75's to make, it is simply not made. (2) **Plan 75's one constraint ON this plan is DISCHARGED** — that the memory read land at **INTAKE**, because a memory entry can name an evidence SOURCE and not merely a hazard, so a read placed later cannot change what the run searches. This plan's shipped text satisfies it verbatim: `src/commands/research/main.md:51` ("too late to change what this run searches") and `:55` ("candidate evidence source"). **The bound on that discharge:** this plan's Phase 7 consumer e2e is deferred, so the lane is **build-verified, not consumer-validated** — the constraint is met in the shipped text, which is not the same as observed in a run.]**

## Per-command memory disposition (the plan's organizing artifact)

Modelled on plan 49's three-class `.devforge/` table (D1 there). Every one of the 20 emitted commands (`scripts/emitters/claude.py:57` `_PROMOTED`) gets **exactly one** disposition — `READS` or `N/A` — **with a recorded reason**, so an exclusion is an audited decision rather than a silent gap. Phase 0 ratified this table **as drafted** on 2026-08-13 (13 `READS` / 7 `N/A`, no row overridden); Phase 5 makes it mechanically enforced.

`Today` values: **DEAD** = cites the nonexistent path · **ORPHAN** = a helper reads the live path but no spec consumes the field · **DIGEST** = read and consumed, but truncated · **WRITE** = writes or commits memory without reading it · **NONE** = no reference anywhere.

| # | Command | Today (verified) | Proposed | Reason |
|---|---|---|---|---|
| 1 | `/init-forge` | NONE | **N/A** | First command of the setup chain; runs before any feature work, so memory holds only the shipped stub. Nothing to read. |
| 2 | `/generate-docs` | NONE | **N/A** | Pure code-reader producing `docs/` from the indexed tree; its inputs are the codebase and the CBM graph, not project lessons. *Counter-argument recorded — see D5.* |
| 3 | `/configure` | NONE | **N/A** | Fills `.devforge/project-config.json` from `/init-forge` state + `/generate-docs` output. Mechanical substitution; no judgment memory could inform. |
| 4 | `/constitute` | NONE (and `src/devforge/memory.md:4` falsely claims it populates memory) | **N/A** | Derives rules from the codebase + interview. *Counter-argument recorded — see D5; this is the strongest N/A objection in the table.* |
| 5 | `/research` | NONE | **READS** | **The motivating incident.** Bug/enhancement intake against existing code — the exact place a recorded pitfall changes what gets scoped. WI-4. |
| 6 | `/discover` | NONE | **READS** | Greenfield intake; prior-feature lessons constrain what is proposed. WI-4. |
| 7 | `/specify` | DEAD (5 prose sites + the certified gate) | **READS** | Already declares memory a MANDATORY base read; the declaration must become true. WI-2 + WI-3. |
| 8 | `/spec-check` | NONE | **N/A** | Solves over the spec's own ACs for internal contradiction (plan 62). Project lessons do not bear on whether two ACs contradict each other; adding them would blur the plan-62 D9/D11/D13 honesty bound. |
| 9 | `/plan` | DEAD (bare `MEMORY.md` at `:614`; was `:611` pre-plan-73) | **READS** | Explicitly asks for "lessons about similar technical decisions" — the instruction exists and points nowhere. |
| 10 | `/breakdown` | DEAD (bare `MEMORY.md` at `:104`) | **READS** | Same: "past lessons about similar decompositions", pointing nowhere. |
| 11 | `/implement` | DIGEST (5 lines) + agent-brief full-read affordance | **READS** | Already the best-wired consumer; the change is D7's contract tightening plus the resolver, not a new read. |
| 12 | `/pr-review` | NONE | **READS** | Personal-overlay review; forge-overlay-aware AI-slop / blast-radius / scope-drift checks are judgment calls. *Borderline — see D5's counter-argument on foreign repos.* |
| 13 | `/audit` | DEAD (`main.md:146` + `_audit/_preflight.py:382`) | **READS** | Already reads memory for "pitfalls, past incidents, lessons" — at the wrong path. Its recurring-issue scan is precisely a memory-shaped concern. |
| 14 | `/review` | DEAD (helper only; `main.md` silent) | **READS** | Emergent cross-task review is judgment-heavy; the preflight already builds the excerpt at the wrong path and no phase consumes it. |
| 15 | `/verify` | ORPHAN (correct read, unconsumed) + **WRITE** (PHASE 7, `verify/main.md:332`) | **READS** | Owns the verdict; it already WRITES feature-level lessons, so reading prior ones closes the loop. Consuming the excerpt its own preflight already emits is a prose change, not a new read. |
| 16 | `/grill` | ORPHAN (correct read, unconsumed) | **READS** | The adversary's job is to attack a design; a recorded past failure in the same area is the highest-value ammunition available. |
| 17 | `/summarize` | ORPHAN (correct read, unconsumed) | **N/A** | Plan 24 D1/D3/D4: pure synthesis, agent-free, read-only, consuming only artifacts other commands produced. Global lessons are not a feature artifact. *If ratified N/A, the unconsumed excerpt must be dropped — OQ-6.* |
| 18 | `/finalize` | WRITE/COMMIT only (`main.md:153,156`) + ORPHAN preflight excerpt | **READS** | **Not classified in the brief; this is a plan-side call.** `/finalize` dispatches `tech-writer` to update live `docs/<package>/<concern>/index.md` **Hazards** sections (plan 25 D1) — and memory's `## Known Pitfalls` is literally hazard material. Reading makes its already-present preflight excerpt live rather than orphaned. *Borderline — see D5.* |
| 19 | `/fix` | Correct (prose at `fix/main.md:157` + `_fix/_preflight.py:180`) | **READS** | Already correct; only the path literal moves to the resolver. |
| 20 | `/report-bug` | NONE | **N/A** | Pure capture (plan 26 D4 framing): writes one `bugs/NNN-*.md` and stops; dispatches no agent, renders no judgment. |

**Totals: 13 `READS`, 7 `N/A`.** *Pre-empting a false inference:* the model-invocable / human-typed split is also 13/7 (plan 63), but the two sets are **different** — `/summarize` and `/report-bug` are model-invocable yet `N/A` here, while `/grill` and `/fix` are human-typed yet `READS`. The coincidence is arithmetic, not structural; a future session must not derive one split from the other.

## Work items

- **WI-1 — one shared memory-path resolver.** A single module owning the `.devforge/memory.md` literal and the read. Every consumer imports it; the literal exists in exactly ONE place. This is the anti-rot half: without it, WI-2 fixes today's drift and the next relocation silently re-breaks it — exactly as plan 22's single-file fix did.
- **WI-2 — sweep the dead paths onto the resolver.** `/specify`, `/audit`, `/plan`, `/breakdown` prose + `_specify/_schema.py`, `_review/_preflight.py`, `_audit/_preflight.py` + the `src/manifest.json:38` entry.
- **WI-3 — make absence detectable.** The gate must be able to fail. A recorded read must imply an actual read.
- **WI-4 — wire the intake lane.** `/research` + `/discover` gain an explicit early-phase memory read that carries forward entries touching the affected area as candidate evidence sources and constraints. This is the WI that addresses the motivating incident.
- **WI-5 — per-command declared disposition + a maintainer-side gate.** The table above, plus a checker that FAILS when any emitted command has neither a memory read nor a declared `N/A` reason.

## Decisions (each carrying its counter-argument)

- **D1 — One shared resolver owns the path literal and the read (WI-1).** Recommended home: `src/devforge/lib/_shared/memory.py`, matching the existing flat `_shared/` precedents (`feature_scope.py`, plan 22 Phase 0; `spec_acs.py`, plan 62; `seed_schema.py`, plan 62). It exposes the path constant, a presence/state probe, and a bounded read. Every consumer — the seven preflights, `_implement`'s digest builder, `_specify`'s gate, the two writers — imports it. **Counter-argument:** a module is indirection over a one-line `os.path.join`, and the sweep alone would fix every site that is wrong today. **Rebuttal:** the drift exists precisely BECAUSE the literal is duplicated across 13 helper files (`grep -rl "memory\.md\|MEMORY\.md" src/devforge/lib/`) and 9 command-spec files (same grep over `src/commands/`), and plan 22 fixed exactly one of them; two files now carry hand-written "do not change this path" comments (`_fix/_preflight.py:179`, `_grill/_preflight.py:191-193`), which is direct evidence that convention has already failed to hold the invariant. A resolver makes the next relocation a one-line change instead of a thirteen-site sweep with two survivors.
  **Installer note (verified, no action needed):** `_shared/` is already in both surgical `--only` always-copy sets — `install.sh:150` and `update.sh:156` each `cp -R src/devforge/lib/_shared`. The resolver rides existing wiring; no installer change.
  **The resolver's concrete SYMBOL names are deliberately not fixed here — with ONE exception, ratified after this paragraph was drafted: the exported field name (see the note below).** Phase 5c Rules **2 AND 3** both key on the same three token categories — Rule 2 asserting their PRESENCE on a consuming surface, Rule 3 their ABSENCE from an `N/A` command. Two PREDATE this plan as literals in the repo — `memory_excerpt` (the seven preflights, helper-side only; **zero** command surfaces today, which is exactly what Phase 5a adds) and `memory_digest` (`implement/main.md:103` + `agent-brief.md:12`). The third — "the resolver's exported field name" — is **`memory_state`**, ratified 2026-08-13 and exported by the Phase-1 resolver `src/devforge/lib/_shared/memory.py` as `MEMORY_STATE_KEY` (see the note below; a Phase-4 preflight verb per OQ-1 could add a FURTHER field name on the same terms). It must be threaded into the Phase 5c checker constant **and wired into BOTH rules** — a session that adds it to Rule 2's presence check but not Rule 3's absence check leaves an `N/A` command able to acquire a read the gate cannot see. This matters most for the prose-only commands `/plan`, `/breakdown`, `/pr-review`, which expose no JSON field of their own (OQ-1's inventory) — their consuming surface names whatever token the resolver exports. **The exact API surface is the helper's to own (helper-owns-shape); the plan fixes the resolver's responsibilities, not its symbol names.** A Phase-5 session must not read this plan as a full API spec and stall looking for a definition that was never meant to live here.
  **[RATIFIED 2026-08-13 — the deferral above is CLOSED for the third literal only.]** The resolver's exported field name is **`memory_state`**, so the Phase 5c token set is now fully known: `{memory_excerpt, memory_digest, memory_state}`. Both Phase 5c Rule 2 and Phase 5c Rule 3 delegate the third literal's identity to this decision, so both inherit that name and **`memory_state` must be threaded into BOTH**. The "does not exist yet" phrasing this note originally superseded was **CORRECTED IN PLACE on 2026-08-13** in the paragraph immediately above, and both Phase 5c rules now carry the name inline beside a drafting-history note — **no "not-yet-existing" phrasing about this literal survives as a LIVE CLAIM anywhere in this file**. The quoted strings in this sentence are the correction RECORD, not a live claim — do not re-correct them; a session finding such a phrasing OUTSIDE a correction record has found something this pass missed. Everything else in this paragraph stands: the resolver's remaining API surface (the state enum's member names, the probe's and the bounded read's signatures) is still the helper's to own and is still not fixed here.

- **D2 — Sweep the dead paths onto the live one; do NOT re-home memory to `.claude/memory/`.** **Counter-argument:** creating `.claude/memory/MEMORY.md` (as a copy or symlink) would make all four commands and three helpers correct with zero spec edits. **Rejected:** two memory files is a fork with no merge story; consumer installs already hold 49KB at the live path and nothing at the dead one; `src/CLAUDE.md` (3 sites), `storage-rules.md:89`, plan 49's VERSIONED classification, and the `/finalize` squash-fold (`finalize/main.md:153-165`) are all built on `.devforge/memory.md`. The live path wins on every axis.

- **D3 — `_specify/_schema.py`'s three sites are three DIFFERENT kinds of citation and must not be swept uniformly.** `:230` is the gate's path literal (swap it). `:291-292` is a slot-table entry whose second element is a human-facing LABEL — the label text needs rewording, not just the path. `:309` is a **render-group KEY** in `_RENDER_SECTION_ORDER`, consumed by `_cmds_phase01._group_for_path` (`:277-302`) and paired with `_topic.source_origin_for_path` (`_topic.py:70-101`) — the two classifiers are documented as deliberately kept in lockstep (`_topic.py:24-25`: "Shared by `source_origin_for_path` below and `_cmds_phase01._group_for_path` so the two classifiers cannot drift apart"). Changing the key without changing the classifier makes a memory finding render under the wrong heading — the exact failure mode plan 68 Phase 4 documented for research/discover reports (`_cmds_phase01.py:280-288`). **Counter-argument:** it is one string in three places; a global replace is faster. **Rejected:** a global replace on `:309` silently breaks Phase-1 findings rendering with no error, and the existing in-code comments prove the maintainers already know this pairing is fragile.

- **D4 — Absence is legitimate; the gate distinguishes "declared absent" from "claimed read" (WI-3).** A missing or empty memory file on a fresh install is CORRECT (nothing has been learned yet) and must never hard-block the pipeline. The wrong shape is a blanket existence requirement. The right shape: the resolver returns a structured state, and the gate accepts *absent-and-declared* while rejecting *absent-and-claimed-read*. **The counter-argument is decisive and reshapes the design:** an existence check alone would be **near-vacuous**, because `install.sh:271` ships the stub into every install — so `.devforge/memory.md` almost always EXISTS while being structurally empty, and an existence gate would pass on a stub exactly the way today's string gate passes on a nonexistent path. **Recommended:** a three-state probe — `absent` / `stub` / `populated` — where `populated` means at least one line that is non-blank, not a heading, and not an HTML comment. This mirrors the framework's own established shape for "the file is there but nobody filled it in": the constitution populate-guard sentinel check (`_specify/_cmds_phase01.py:82-86`, `CONSTITUTION_POPULATE_GUARDS`). The exact predicate is the helper's to own (helper-owns-shape); the plan fixes the three states, not the parsing.

- **D5 — Coverage is by DECISION, not by uniform reads (WI-5).** Every emitted command is `READS` or `N/A` **with a recorded reason**; the gate enforces that each is one or the other. **The maintainer's directive is "all commands should work with memory," and the honest reading of that directive is "no command is silently uncovered" — not "all 20 issue a read."** Two independent reasons a blanket all-20 is wrong: (a) plan 08's finding that always-on context has a real, measured cost (3383 → 2806 words, −17.1%) means every added read is a token bill charged to a phase that may not need it; (b) a command that reads memory and does nothing with it is a **type-3 orphan** — which is not hypothetical here, it is the verified current state of seven preflights. **Counter-arguments to the specific `N/A` calls, recorded rather than dismissed:**
  - **`/constitute` (strongest objection).** It re-runs on mature projects when memory IS populated, and the shipped stub literally claims constitute populates it (`src/devforge/memory.md:4`). If ratified `N/A`, the stale stub comment must be corrected in Phase 6 or the plan ships a self-contradiction.
  - **`/generate-docs`.** Also re-runs on mature projects; a recorded architectural pitfall is plausible `docs/` Hazards material. The counter-counter is that `/finalize` (classified `READS`) is the command that owns Hazards updates via `tech-writer`, so the concern has a home.
  - **`/summarize`.** Its narrative could plausibly benefit from lessons; and its preflight ALREADY reads memory correctly, so `N/A` is not free — it converts a working read into declared dead weight (OQ-6).
  - **`/pr-review` (borderline the other way).** Classified `READS`, but it reviews foreign repos where the local project's lessons may not bear. The counter-counter: the overlay is deliberately personal, and the recurring-issue dimension is the same one `/audit` reads memory for.
  - **`/finalize` (a plan-side call, not in the brief's sets).** Classified `READS` on the Hazards argument. If the maintainer prefers `N/A`, OQ-6's drop-the-orphan-field consequence applies to it as well as to `/summarize`.

- **D6 — The gate is MAINTAINER-side, modelled on plan 41 WI-3.** A standalone checker under `scripts/` (recommended: `scripts/lib/memory_lane.py` exposing a `find_gaps(repo_root)`-shaped function + `scripts/verify-memory-lane.py` CLI + `tests/lib/test_memory_lane.py` running against live `src/`). Per plan 41's ratified OQ-1 and its recorded fact that the repo has no CI and no Makefile, **the pytest test against live `src/` IS the permanent gate**. The declared dispositions live as a constant in the checker module (a `{command: (disposition, reason)}` mapping), mirroring the shape of the agent lists plan 41's checker already parses — so adding a command to `_PROMOTED` without a disposition entry fails the gate, exactly as the existing emitter `_PROMOTED` cross-check convention intends. **Counter-argument:** a second standalone checker duplicates plumbing already present in `scripts/lib/agent_reachability.py` — why not extend it? **Rejected:** different subject (commands vs agents), different roster source (`_PROMOTED` vs `src/agents/*.md`), and plan 41 D7 already established the complement-not-fold precedent for a gate with a different subject. Extending `find_orphans` to also answer "does this command read memory" would overload a function whose name and tests are about agent reachability.

- **D7 — `/implement`'s 5-line digest is a presence signal, not a memory read.** Verified: the digest is provably the stub preamble for any pipeline-written file (see Verified state). The `READS` contract for `/implement` is satisfied by the agent-brief carry at `references/agent-brief.md:12`, which must be tightened from permissive ("the agent **may** read the full file") to directed (the orchestrator carries the entries relevant to the task's touched area into the brief). **Counter-argument:** a full-file read costs context on every task, and memory is unbounded — 151 lines today, more tomorrow. **Resolution:** the contract is "the entries relevant to the touched area", never "the whole file"; and memory growth/compaction management is an explicit Non-goal, so this plan must not smuggle a curation mechanism in through the digest. **Phase home: Phase 5a's first bullet names `src/commands/implement/references/agent-brief.md:12` as the edit target** — this decision is not self-executing, and it is the only phase step that closes mechanism #4.

- **D8 — `src/manifest.json:38` is corrected in the sweep, with its cosmetic nature recorded.** Replace `".claude/memory/**"` with the live `.devforge/memory.md`. **Counter-argument:** the entry is verified cosmetic (it only feeds a count at `update.sh:670-673`), so editing it is pure churn. **Rebuttal:** a dead path sitting in a manifest is precisely the "sentence that used to be true and now misleads" seed the repo's discipline rules name; a future session reading `projectOwned` will reasonably believe memory is overwrite-protected. The edit costs one line and the plan records — in Phase 2's Verify and in `storage-rules.md` — that `projectOwned` **documents** rather than **enforces**.

## Open Questions (drafted as Phase-0 ratification items — **ALL SIX RESOLVED 2026-08-13**; the recommendations below are the reasoning, the outcomes are in `### Phase 0 ratification record (2026-08-13)`)

- **OQ-1 — Does the memory read live in `main.md` prose, or in the command's `_preflight.py`?** The pipeline is inconsistent today: `/verify` and `/fix` do it in preflight; `/specify` does it via prose plus a `record-input-read` gate. **Verified inventory:** nine subpackages have a dedicated `_preflight.py` (`_generate_docs`, `_audit`, `_finalize`, `_fix`, `_grill`, `_review`, `_spec_check`, `_summarize`, `_verify`); `_implement` has `_cmds_preflight.py`; `_research`, `_discover`, `_specify`, `_report_bug` expose preflight verbs from other modules; `_plan`, `_breakdown`, `_pr_review` expose none. **Recommendation: BOTH, with a division of labour — preflight PRODUCES, prose CONSUMES, and the prose must name the field.** Preflight-only is exactly today's orphan (seven preflights emit `memory_excerpt`; zero specs consume it), and prose-only is skippable — the mechanical read is what makes the obligation testable, and the named consumption is what makes it non-inert. Where no preflight verb exists (`/plan`, `/breakdown`, `/pr-review`), the PRODUCE half is prose-form against the resolver until a preflight exists — the gate is indifferent to which form performs the read, but **never** indifferent to whether a consuming surface names the field. **This recommendation is encoded mechanically as Phase 5c Rule 2, which is CONJUNCTIVE for exactly this reason**; leaving it as authoring guidance is what allowed seven preflights to become orphans.
- **OQ-2 — Does `/specify` keep memory as a MANDATORY base read once absence is detectable, or demote it to read-if-present?** **Recommendation: keep it MANDATORY, with the mandate redefined.** Under D4, "mandatory" means *the resolver was consulted and its three-state result recorded* — not *the file had content*. That keeps the four-read gate intact (no weakening of a shipped forcing function) while making a green gate mean something for the first time. Demoting to read-if-present would repeat the original sin in a new form: an obligation nobody can fail. Ratify jointly with D4, since the answer is a direct consequence of the three-state probe.
- **OQ-3 — Does the resolver own memory WRITES, or reads only?** **Verified writers (there are exactly two, with different mechanisms):** `/implement` via `_implement/_cmds_session.py:491-499` (helper-side atomic append under `## Task Outcomes`, `_append_under_section`), and `/verify` PHASE 7 via `verify/main.md:332` (orchestrator prose using the Write tool — no helper verb). `/finalize` COMMITS memory (`finalize/main.md:153,156`) but does not write it. **Recommendation: the resolver owns the PATH for everyone and the READ for readers; writes keep their current mechanisms in v1.** Unifying a helper-side atomic append with an orchestrator Write-tool append is a genuinely separate concern (it would mean giving `/verify` a write verb, which is a `/verify` design change), and this plan's subject is the read lane. The narrow constraint that must hold: both writers import the path constant, so the literal count stays exactly one.
- **OQ-4 — Should the checker also assert that no `src/` file references `.claude/memory` at all?** **Recommendation: YES — a second, cheap rule alongside the classification rule.** The classification rule alone would pass a command that reads memory at the WRONG path (which is precisely `/audit`'s and `/review`'s current state — they *do* read, they just read nothing). A repo-wide "no `.claude/memory` literal in `src/`" assertion is the permanent anti-regression sweep that stops this class from being re-authored. **Scope it to `src/` only**: `done-plans/` and the numbered plan files at repo root cite the literal as history, and `tests/` carries it in TWO distinct classes — a repo-wide rule would fail on its own regression net.
  **The `tests/` blast radius is 10 files** (`grep -rl "\.claude/memory" tests/`, verified 2026-08-12) — an order of magnitude larger than a four-file characterization suggests, and the two classes have OPPOSITE obligations:
  - **Class A — anti-regression assertions that STAY byte-unchanged.** The literal IS the point: they assert the stale path is NOT read. `tests/lib/_verify/test_preflight.py:465-475`, `tests/lib/_summarize/test_preflight.py:503-512`, `tests/lib/_fix/test_fix_helper.py:425`, `tests/lib/_grill/test_preflight.py:433-435`, `tests/lib/_finalize/test_preflight.py:26` (docstring). These are the reason the rule must be `src/`-scoped.
  - **Class B — current-behavior fixtures Phase 2a MUST REWRITE.** These encode the dead path as the CURRENT expected PASSING behavior of code the sweep changes, so they need content edits, not unchanged passes: `tests/lib/_audit/test_preflight.py:485-495` (asserts `memory_present` is True after writing the dead path at `:489` — Phase 2a makes it False); `tests/lib/_review/test_preflight.py:45-71` (`_make_full_install`, the shared suite-wide fixture helper, writing the dead path at `:70-71` under a docstring at `:53` that claims "All paths are exactly what the real commands produce (no invented names)") plus `:384`; `tests/lib/test_specify_helper.py` (12 hits, incl. the e2e at `:4152-4160` recording the dead path as one of the four `phase1-finalize` mandatory reads); `tests/lib/fixtures/specify-sample-migration-state.json:24,91` and `tests/lib/fixtures/specify-sample-greenfield-state.json:24,96,204` (the literal baked into recorded state).
  The rewrite obligation is written into Phase 2a's task list and its Verify block; a build session that reads only OQ-4 and stops at "tests deliberately keep the literal" would leave class B asserting the dead path forever.
- **OQ-5 (new, from the adjacent finding) — does the `install.sh:271` memory clobber belong in this plan?** **Recommendation: yes, fixed here as a one-line guard**, because a plan named "memory lane integrity" that permits a re-install to erase memory is misnamed. Smallest blast radius: exclude `memory.md` from the bulk `cp -R` and copy it only when absent, guarded inline in `install.sh` next to the existing stray-user-state loop (`:260-268`). **Counter-argument:** it is an installer change, not a read-path change, and it enlarges an already-broad plan. **Alternative considered and NOT recommended:** route it through `manifest.json` `copyIfMissing` — that list is currently EMPTY (`src/manifest.json:78-80`) and is read at `update.sh:419`; **whether `install.sh` honours `copyIfMissing` at all was NOT verified this session and must be checked before that route is chosen.** Recorded as an explicit open item rather than assumed. **[CHECKED 2026-08-13 — that open item is now CLOSED, and the answer kills the alternative: `install.sh` does not honour `copyIfMissing` at all (`grep -n copyIfMissing install.sh` → zero hits; the key is read only by `update.sh` at `:419`, `:531`, `:1001`). The manifest route cannot fix the install clobber. See re-verification (c) under Verified state; ratified OQ-5 outcome = IN SCOPE via the inline guard.]**
- **OQ-6 (new) — for a command classified `N/A` whose preflight ALREADY reads memory, drop the field or reclassify?** Applies to `/summarize` (and to `/finalize` if the maintainer overrides its `READS` classification). **Recommendation: drop the field.** An emitted-but-unconsumed field is the exact type-3 orphan this plan exists to eliminate; leaving it in place while declaring the command `N/A` ships a contradiction between the table and the code. **Counter-argument:** dropping `memory_present` / `memory_excerpt` is a change to a JSON contract with existing tests (`tests/lib/_summarize/test_preflight.py`), so it costs a test update for zero behavioural gain. If the maintainer prefers zero churn, the honest alternative is to reclassify `/summarize` as `READS` and give its synthesis prose a named consumption — **not** to leave an `N/A` command reading memory.

## Non-goals (explicit)

- **Changing what memory CONTAINS, or how it is authored, curated, compacted, or pruned.** This plan is about the READ lane and the path. Growth management is out (see D7).
- **Any change to plan 73 (`73-LITERAL-ARCHAEOLOGY-EVIDENCE-ARM-PLAN.md`).** Related-but-separate: 73 hardens how a run grounds claims in code literals; 74 hardens whether a run reads what previous runs already learned. Different mechanism, different lane. Cite it, do not touch it. (A concurrent session owns that file — do not read-modify-write it.)
- **Migrating or backfilling memory content in existing consumer installs.** No consumer's `.devforge/memory.md` is rewritten, reformatted, or seeded by this plan. (The OQ-5 `install.sh` guard PROTECTS existing content; it does not modify it.)
- **Adding a new always-on `CLAUDE.md` rule.** The rule already exists — twice, in two independent always-on channels: `src/CLAUDE.md:205` (Key Rule 4) and `src/constitution.md:238` (§6.3 Read-First Principle, item 4). Neither prevented the motivating incident. A third statement of the same obligation would add always-on token cost (plan 08) for zero mechanical change. **The gap is enumerated-phase execution, not always-on awareness.**
- **Unifying the two memory WRITE mechanisms** (helper-side atomic append vs orchestrator Write tool) — see OQ-3.
- **Any new agent.** The 19-agent roster (plan 62 grew it 18 → 19) is untouched; no memory-reading agent is introduced. Memory reads happen in preflights and orchestrator prose.

## Phase 0 — Maintainer ratification (decision gate, no code)

Present this plan. The maintainer confirms, or overrides with a recorded reason:

(a) the per-command disposition table — specifically the seven `N/A` calls, and the four borderline rows flagged in D5 (`/constitute`, `/generate-docs`, `/summarize`, `/pr-review`) plus `/finalize`, which the plan classified on its own initiative;
(b) D1 (shared resolver) and D2 (sweep, don't re-home);
(c) D4's three-state probe (`absent` / `stub` / `populated`) and the joint OQ-2 answer (mandatory-means-consulted);
(d) D6's gate home + the disposition-as-checker-constant shape;
(e) D7's `/implement` contract tightening and D8's manifest correction;
(f) OQ-1 (preflight produces / prose consumes), OQ-4 (the `src/`-scoped anti-regression rule), OQ-5 (install clobber in or out — and if in, which route), OQ-6 (drop the orphan field or reclassify).

Until ratification, no build phase is authored.

### Phase 0 ratification record (2026-08-13)

**Ratified by the maintainer 2026-08-13 — this gate is CLEARED and build is authorized.** Every decision and every open question below carries its outcome. Where an outcome reads "as recommended", it adopts the recommendation as written in the corresponding decision/OQ above — the reasoning there is unchanged and is not restated here.

**Decisions:**

- **D1 — CONFIRMED.** One shared resolver at `src/devforge/lib/_shared/memory.py` owns the path literal and the read. **The deferred third literal is now FIXED: the resolver's exported field name is `memory_state`.** The Phase 5c token set is therefore exactly `{memory_excerpt, memory_digest, memory_state}`, and **`memory_state` must be wired into BOTH Rule 2 (presence) and Rule 3 (absence)** — per D1's own warning that threading it into only one reopens the OQ-6 hole (an `N/A` command able to acquire a read the gate cannot see).
- **D2 — CONFIRMED.** Sweep the dead paths onto `.devforge/memory.md`; do NOT re-home memory to `.claude/memory/`.
- **D3 — CONFIRMED.** The three `_specify/_schema.py` sites are three different kinds of citation and are not swept uniformly; `:309` is a render-group KEY, swept ATOMICALLY with `_cmds_phase01._group_for_path` and `_topic.source_origin_for_path`.
- **D4 — CONFIRMED.** Three-state probe: `absent` / `stub` / `populated`.
- **D5 — CONFIRMED.** Coverage is by DECISION, not by uniform reads. **The disposition table is ratified EXACTLY AS DRAFTED: 13 `READS` / 7 `N/A`.** All five borderline rows named in Phase 0 item (a) — the **four flagged in D5** (`/constitute`, `/generate-docs`, `/summarize`, `/pr-review`) plus **`/finalize`, which the plan classified on its own initiative** (disposition row 18: "Not classified in the brief; this is a plan-side call") — stand as the table proposes. **No row was overridden.**
- **D6 — CONFIRMED.** The gate is maintainer-side under `scripts/`, the declared dispositions live as a checker constant, and the live-`src/` pytest IS the permanent gate.
- **D7 — CONFIRMED.** `/implement`'s 5-line digest is a presence signal, not a memory read; the `references/agent-brief.md` carry is tightened from permissive ("may") to directed.
- **D8 — CONFIRMED.** `src/manifest.json` is corrected in the sweep, with its cosmetic (documents-not-enforces) nature recorded.

**Open questions:**

- **OQ-1 — RESOLVED as recommended.** Preflight PRODUCES, prose CONSUMES, and the prose must NAME the field; encoded mechanically as the CONJUNCTIVE Phase 5c Rule 2, not left as authoring guidance.
- **OQ-2 — RESOLVED as recommended.** `/specify` keeps memory as a MANDATORY base read, with "mandatory" redefined as *the resolver was consulted and its three-state result recorded* — not *the file had content*.
- **OQ-3 — RESOLVED as recommended.** The resolver owns the PATH for everyone and the READ for readers; the two writers keep their current mechanisms in v1 and import the path constant, so the literal count stays exactly one.
- **OQ-4 — RESOLVED as recommended.** A `src/`-scoped "no `.claude/memory` literal" rule; `tests/` and the repo-root plan files deliberately retain it.
- **OQ-5 — RESOLVED IN SCOPE, via the inline `install.sh` guard.** The manifest `copyIfMissing` alternative is **not merely un-preferred but VERIFIED UNAVAILABLE** — `install.sh` does not honour `copyIfMissing` at all (see re-verification (c) under Verified state). Recorded here so no future session re-proposes that route.
- **OQ-6 — RESOLVED: DROP the field.** `/summarize` stays `N/A` and its preflight's `memory_present` / `memory_excerpt` are REMOVED, with the accompanying test update. **It was NOT reclassified.** (Build-ordering note: `/summarize`'s OQ-4 class-A anti-regression assertion at `tests/lib/_summarize/test_preflight.py:503-512` is unchanged at Phase 2 as that phase's Verify states, and is re-touched at Phase 5b when the fields go — the two are sequential, not contradictory.)

**Build sequencing (ratified with the above):** Phases 1–6 execute autonomously with **a commit per phase**; **Phase 7 (consumer e2e) remains the user-driven HARD GATE** and is not self-serviced.

### Verify

- Every decision D1–D8 carries a recorded confirm-or-override, and every OQ-1–OQ-6 carries a recorded resolution, inline in this file.
- The disposition table's 20 rows each carry a ratified disposition; the total is stated (13/7 as proposed, or the ratified split).
- No phase below has started before this gate clears.

---

## Phase 1 — The shared memory resolver (WI-1)

Loop: **python-engineer → python-reviewer**, test-first (every function gets a test written and run in the same turn, per repo discipline).

Build `src/devforge/lib/_shared/memory.py` owning: the `.devforge/memory.md` path constant, the three-state probe from D4, and a bounded read. The module is the ONLY place the path literal appears after Phase 2. Follow the existing flat `_shared/` layout (`feature_scope.py`, `spec_acs.py`, `seed_schema.py`) — no subpackage.

Nothing else changes in this phase: existing callers keep their own literals until Phase 2 re-points them, so Phase 1 is additive and independently landable.

Helper-owns-shape applies: the module owns the state enum, the populated-predicate, and the excerpt bounding; callers compose values and never re-implement the predicate.

**Installer:** no change required — `_shared/` is already in both surgical always-copy sets (`install.sh:150`, `update.sh:156`).

### Verify

- `src/devforge/lib/_shared/memory.py` exists; unit tests cover all three states (absent file; the shipped 13-line stub verbatim from `src/devforge/memory.md`; a populated file) and the bounded read.
- The stub fixture is the REAL shipped stub, not a hand-authored approximation — the `stub` state must be proven against the file the installer actually copies.
- No existing caller changed in this phase; the full test suite is green.
- `grep -rn "devforge.*memory\.md\|memory\.md" src/devforge/lib/_shared/memory.py` shows the literal; no other new site was added.

---

## Phase 2 — Dead-path sweep onto the resolver (WI-2)

Two sub-steps with different loops; land them in one phase because the D3 pairing must not be split.

**2a — helper code.** Loop: **python-engineer → python-reviewer**, test-first.
- `_specify/_schema.py:230` (gate literal), `:291-292` (slot path **and** its human label), `:309` (**render-group key — swept ATOMICALLY with `_cmds_phase01._group_for_path` at `:277-302` and `_topic.source_origin_for_path` at `_topic.py:70-101`**, per D3).
- `_review/_preflight.py:76,171,172` and `_audit/_preflight.py:8,309,381,382` → the resolver. Both then read the live path; their `memory_excerpt` becomes real data (consumed in Phase 5's disposition wiring / their commands' prose).
- `_verify`, `_summarize`, `_finalize`, `_fix`, `_grill` preflights and `_implement/_cmds_preflight.py` → re-pointed at the resolver constant (they are already CORRECT; this removes the duplicate literals that made the bug possible, and lets the "DO NOT change this path" comments at `_fix/_preflight.py:179` and `_grill/_preflight.py:191-193` be replaced by an import).
- The two writers (`_implement/_cmds_session.py:491-499`; and `/verify`'s orchestrator write has no helper) import the constant per OQ-3.
- `_audit/_scope.py:548` and `_audit/_cli.py:1699` — prose-only help text naming "MEMORY.md"; reword to the live filename.
- **Rewrite the current-behavior test fixtures (OQ-4 class B) IN THE SAME TURN as the code they cover.** These are NOT dormant historical assertions — they encode the DEAD path as the CURRENT expected passing behavior of code this sub-step rewrites, so they need content edits (swap the fixture path, flip the assertion), not "unchanged passes": `tests/lib/_audit/test_preflight.py:485-495` (`test_memory_present_and_excerpt` writes `.claude/memory/MEMORY.md` at `:489` and asserts `memory_present` is True at `:491` — after this sub-step that assertion is FALSE); `tests/lib/_review/test_preflight.py:45-71` (`_make_full_install`, the shared fixture helper the whole suite builds on, writes the dead path at `:70-71` — and its docstring at `:53` claims "All paths are exactly what the real commands produce (no invented names)", which is itself false today) plus the per-test write at `:384`; `tests/lib/test_specify_helper.py` (12 hits, including the e2e at `:4152-4160` that records `.claude/memory/MEMORY.md` as one of the four `phase1-finalize` mandatory reads); and the recorded-state fixtures `tests/lib/fixtures/specify-sample-migration-state.json:24,91` + `tests/lib/fixtures/specify-sample-greenfield-state.json:24,96,204`, which have the literal baked into saved state. Enumerate the full set before editing (`grep -rl "\.claude/memory" tests/` → **10 files**, verified 2026-08-12) and classify each as OQ-4 class A (stays) or class B (rewrite) — a file left unclassified is a silent green-suite hole.

**2b — command prose.** Loop: **instruction-author → instruction-reviewer + claude-code-guide** (these files ship into `.claude/`).
- `specify/main.md:178,183,243,470,497` + the bare `MEMORY.md` at `:931`.
- `audit/main.md:33,146,282`.
- `plan/main.md:614` (was `:611` pre-plan-73 — see re-verification (b) under Verified state); `breakdown/main.md:104`.

**2c — manifest.** Loop: none of its own — a JSON data edit with no Claude-Code-authoring surface and no Python logic, reviewed inline as part of 2a's python-engineer → python-reviewer pairing (it is one line, adjacent, and mechanical). `src/manifest.json:38` per D8, with the "documents, does not enforce" fact recorded (the full statement lands in `storage-rules.md` at Phase 6).

### Verify

- `grep -rn "\.claude/memory" src/` returns **zero** hits.
- `grep -rn "MEMORY\.md" src/` returns zero hits, or only hits that are deliberately historical and named in this Verify block.
- `/specify` Phase-1 findings render identically for non-memory sources before and after the `_RENDER_SECTION_ORDER` change (the D3 atomicity proof) — round-trip the render through the real producer, not a hand-authored state fixture.
- **The full set of `tests/` files carrying the stale literal was ENUMERATED and each classified** — `grep -rl "\.claude/memory" tests/` → 10 files; every one is recorded as OQ-4 class A (anti-regression, stays byte-unchanged) or class B (current-behavior fixture, rewritten in 2a). "Suite green" alone does NOT satisfy this criterion: a class-B file left un-rewritten either fails loudly or, worse, passes while asserting the dead path is still read.
- Class A tests still pass **unchanged** (`tests/lib/_verify/test_preflight.py:465-475`, `tests/lib/_summarize/test_preflight.py:503-512`, `tests/lib/_fix/test_fix_helper.py:425`, `tests/lib/_grill/test_preflight.py:433-435`, `tests/lib/_finalize/test_preflight.py:26`) — they assert the stale path is NOT read, which stays true.
- Class B tests were REWRITTEN and pass on the live path — in particular `tests/lib/_audit/test_preflight.py`'s `test_memory_present_and_excerpt` now writes `.devforge/memory.md`, and `tests/lib/_review/test_preflight.py`'s `_make_full_install` docstring claim ("All paths are exactly what the real commands produce") is TRUE for the first time.
- The full `_specify`, `_review`, `_audit` suites are green.
- Exactly ONE occurrence of the path literal remains in `src/devforge/lib/`, in `_shared/memory.py`.
- `src/manifest.json` names the live path; no other manifest entry was touched.

---

## Phase 3 — Absence detection (WI-3)

Loop: **python-engineer → python-reviewer** for the helper; **instruction-author → instruction-reviewer + claude-code-guide** for the `specify/main.md` prose that describes the gate.

Make `/specify`'s mandatory memory read impossible to satisfy without consulting the resolver:
- The memory slot's `record-input-read` is fed from the resolver's probe result, so a recorded read carries the observed state (`absent` / `stub` / `populated`) rather than a bare string.
- `cmd_phase1_finalize` (`_cmds_phase01.py:136-154`) accepts `absent` and `stub` when they were **declared by the probe**, and rejects a memory record that claims a read the probe never performed.
- The three other mandatory base reads (`constitution.md`, `CLAUDE.md`, `docs/architecture.md`) are **untouched** — this phase changes exactly one slot's provenance, not the gate's arity.
- `specify/main.md:243`'s gate sentence is reconciled to describe what a green gate now means, and `:183`'s call is re-pointed.

**Scope guard:** this phase does not add an existence requirement anywhere else in the pipeline. A missing memory file must never block `/research`, `/plan`, `/implement`, or any other command — the three-state probe is informational everywhere except this one gate slot.

### Verify

- A `/specify` run against a target with NO memory file: gate passes, the record shows `absent`, and stderr/report says so — the pipeline is not blocked.
- A run against the shipped stub: gate passes, state `stub`.
- A run against a populated file: gate passes, state `populated`.
- A synthetic run that records the memory slot WITHOUT the probe having run: gate REJECTS with exit 2 and an enumerating stderr message. **This is the test that proves the forcing function can now fail** — before this phase, no input made it fail.
- The other three mandatory reads behave byte-identically (regression).
- Tests round-trip through the real `record-input-read` → `phase1-finalize` producer/consumer pair, not hand-authored state JSON.

---

## Phase 4 — Wire the intake lane (WI-4)

Loop: **instruction-author → instruction-reviewer + claude-code-guide** (`research/main.md` and `discover/main.md` ship into `.claude/`); **python-engineer → python-reviewer** if the read is homed in a preflight verb per OQ-1.

Add an explicit early-phase memory read to `/research` and `/discover` that:
- reads via the resolver;
- carries forward the entries touching the affected area as **candidate evidence sources and constraints** — not as findings (a memory entry is a prior session's assertion, not verified evidence for THIS run);
- states the honesty bound explicitly, matching the register plan 67/69 established for carried research data: a carried memory entry is an **unverified prior-session assertion** and must be re-grounded before it becomes a finding, exactly as plan 67's carried caller list is "a seed, not a terminal answer" and plan 69's zero-caller justification is "an UNVERIFIED research-time assertion";
- no-ops cleanly on `absent` / `stub` (the fresh-install case), consistent with Phase 3's scope guard.

The motivating incident is the acceptance case: an entry naming a locally-readable sibling repo and a standing "read the backend mapper before scoping" lesson must reach the run's evidence-gathering, not sit unread.

### Verify

- `/research` on a target whose memory names a relevant prior lesson surfaces that lesson in the run before scoping is committed.
- `/discover` likewise.
- Both commands no-op cleanly with `absent` and `stub` memory — no blocked run, no spurious warning.
- The carried entries are framed as candidate/unverified, never as established findings; instruction-reviewer confirms the framing does not license treating a memory entry as grounded evidence.
- `/research`'s existing gates (plans 67 + 69 — the mode-independent check 8, the declared caller total check 9, the per-caller classification check 19) are byte-unchanged; the memory read adds an input, it does not touch a gate.
- **Plan 73's `EvidenceLanes` is byte-unchanged.** `src/devforge/lib/_research/handoff_schema.py`'s four-bool enum (`static_graph` / `text_search` / `runtime_probe` / `history`, `:1332`) gains no memory lane, no rename, and no field — memory is a FIFTH evidence source this plan deliberately leaves outside that vocabulary. See re-verification (d) under Verified state for the two independent reasons (this plan's Non-goals; plan 75's D6 claims the lane-vocabulary extension).

---

## Phase 5 — Per-command disposition + maintainer-side gate (WI-5, the backbone)

Loop: **python-engineer → python-reviewer** for the checker + tests; **instruction-author → instruction-reviewer + claude-code-guide** for each `main.md` **and each `references/*.md`** that gains a named memory consumption (both ship into `.claude/` and `.devforge/command-refs/` respectively).

**5a — wire the `READS` set.** Each command classified `READS` gets a memory read in the OQ-1 form (preflight produces / prose consumes, with the prose NAMING the consumed field). For the commands whose preflight already emits `memory_excerpt` (seven today; all of them live-path after Phase 2), this is a prose change only — the read exists, the consumption does not.

- **`/implement` — D7's contract tightening, the named edit target.** `src/commands/implement/references/agent-brief.md:12` currently reads "the preflight `memory_digest` is a starting point; the agent **may** read the full file". Replace the permissive "may" with a DIRECTED instruction: the orchestrator carries the entries relevant to the task's **touched area** into the brief (per D7 — "the entries relevant to the touched area", never "the whole file"). **This bullet is the only place in any phase that closes mechanism #4 (digest truncation).** D7 settles it, disposition row 11 repeats it, and Phase 0 item (e) ratifies it — but until this edit lands, `/implement`'s entire memory input is the 5-line digest that is provably the stub preamble, and every other Verify block in this plan would still pass.

**5b — resolve the `N/A` set.** Each `N/A` command carries its recorded reason in the checker constant. Per OQ-6, any `N/A` command whose preflight still reads memory has that read removed (or is reclassified) — no command may be declared `N/A` while its helper reads memory.

**5c — the gate.** `scripts/lib/memory_lane.py` + `scripts/verify-memory-lane.py` + `tests/lib/test_memory_lane.py`, per D6. Rules:
1. Every name in `scripts/emitters/claude.py:57` `_PROMOTED` has a declared disposition with a non-empty reason. FAIL otherwise (this is what makes a newly-added command fail the gate until it is classified).
2. Every `READS` command satisfies **BOTH** halves of OQ-1's produce/consume split: (a) a memory read is PERFORMED — a helper preflight or a resolver call; **and** (b) a consuming surface — the command's `main.md` or a file under its `references/` — explicitly NAMES the field it reads (a text check for the literal field token: `memory_excerpt`, `memory_digest`, or the resolver's exported field name — **`memory_state`**, fixed by the ratified D1 on 2026-08-13; this rule was drafted while that third name was still deferred). FAIL if either half is missing. **A command whose ONLY memory touchpoint is a helper preflight FAILS.**
   **Rule 2 is deliberately CONJUNCTIVE, and this is load-bearing.** A disjunctive presence check ("`main.md` prose OR `references/` OR helper preflight") would PASS mechanism #3 — preflight-builds-it, nobody-consumes-it — which is the exact state WI-5 exists to eliminate and the verified current state of seven preflights. OQ-1's "preflight PRODUCES, prose CONSUMES, and the prose must NAME the field" is encoded HERE as a gate rule, not left as authoring guidance a future edit can quietly drop.
3. Every `N/A` command has NO memory read. FAIL otherwise (the anti-orphan rule). **Detection uses the SAME token set as Rule 2** (`memory_excerpt`, `memory_digest`, `memory_state` — see D1), scanned across the command's surfaces and its helper package. Rule 3 therefore inherits both of Rule 2's bounds. **Bound one — presence, not substance:** it proves the absence of KNOWN tokens, not the absence of reads; a read surfaced under a token outside that set is invisible to it. **Bound two — the third literal:** it depends on the same third literal Rule 2 does — **`memory_state`**, fixed by the ratified D1 on 2026-08-13, drafted here while that name was still deferred — and that literal must be wired into Rule 3 as well as Rule 2. A session that threads it into the presence check and not the absence check reopens exactly the hole OQ-6 exists to close — an `N/A` command (today: `/summarize`) silently keeping or re-acquiring an orphan read.
4. **Per OQ-4:** no file under `src/` contains the `.claude/memory` literal. FAIL otherwise. Scoped to `src/` — `tests/` and the repo-root plan files deliberately retain it (see OQ-4 for the two `tests/` classes).

Per plan 41 D5/D8's honesty precedent, the checker's own output must state what it does NOT cover. It DOES verify that a read is performed AND that a consuming surface names the field (Rule 2 — consumption-vs-orphan is the literal defect, not a quality question). It does NOT verify that the consumption is SUBSTANTIVE (that naming the field actually changes what the command does), that the right entries were selected, or that the memory content is accurate — nor, per Rule 3, that an `N/A` command is truly read-free, since Rule 3 proves only that no KNOWN token appears. A green gate is not a claim about memory quality.

### Verify

- python-reviewer clean; the checker runs green against live `src/` after 5a + 5b.
- Synthetic tests: a `_PROMOTED` command with no disposition → FAIL naming the command; a `READS` command with no read performed at all → FAIL; an `N/A` command whose helper reads memory → FAIL; a planted `.claude/memory` literal under `src/` → FAIL.
- **The mechanism-#3 regression test (mandatory):** a `READS` command whose ONLY memory touchpoint is a helper preflight — the read is performed, no `main.md` or `references/` file names the field — → **FAIL**. This is precisely the case a disjunctive presence rule would wrongly pass, and precisely the live state of seven preflights today; without this test, Rule 2 could be silently loosened back to a disjunction and the suite would stay green.
- **D7 / mechanism-#4 — closed by THIS criterion, not by Rule 2.** `src/commands/implement/references/agent-brief.md:12` no longer gates the full-file read on "may" — the memory carry is DIRECTED (the orchestrator carries the touched-area-relevant entries). The falsifiable check is `grep -n "may read the full file" src/commands/implement/references/agent-brief.md` returning zero hits. **Rule 2 does NOT force this edit and must not be relied on to:** `src/commands/implement/main.md:103` ALREADY contains the literal `memory_digest` today — inside the preflight's JSON field-list documentation, with no instruction to use it — so Rule 2(b)'s text match is trivially satisfiable for `/implement` whether or not the `agent-brief.md` edit ever lands. That is the presence-vs-substance limitation the checker declares in 5c's non-coverage paragraph: Rule 2 proves a field is NAMED, never that naming it changed anything. Mechanism #4 is closed by the grep above and by nothing else in the gate.
- The checker's output names its non-coverage explicitly (consumption IS checked; substantive-use, entry-selection, and content accuracy are NOT).
- `tests/lib/test_memory_lane.py` runs against live `src/` — it IS the permanent gate, since the repo has no CI and no Makefile (plan 41's recorded fact, re-confirmed).
- Plan 41's `scripts/verify-agent-reachability.py` still passes (the two gates are independent; neither imports the other).

---

## Phase 6 — Docs reconcile + cross-ref sweep

Direct doc edits; **instruction-author → instruction-reviewer + claude-code-guide** for `src/CLAUDE.md` (it ships into consumers as `CLAUDE.md`).

- **Repo-root `CLAUDE.md`** — add the active-plan entry for 74 and a "Where to find what" row for the resolver + the memory-lane gate (alongside the existing plan-41 agent-reachability row).
- **`CHANGELOG.md`** — the resolver, the dead-path sweep, the detectable gate, the intake wire-in, the disposition + gate.
- **`src/CLAUDE.md`** — fix the stale bare `MEMORY.md` at `:295` (Session Continuity, "history lives in task completion notes (`specs/`) and `MEMORY.md`"). Leave `:169`, `:205`, `:308` alone — verified correct. **Do NOT add a new always-on rule** (Non-goal).
- **`src/devforge/storage-rules.md`** — plan 49 owns the `.devforge/` disposition table, and memory's row is at `:89`. Extend it with the READ lane: which commands read memory, that the resolver owns the path, and (per D8) that `manifest.json`'s `projectOwned` **documents** rather than **enforces** protection.
- **`src/devforge/memory.md:4`** — correct the stale "Populated during constitute" comment (verified false — `/constitute` writes nothing to memory). Ratified `/constitute` = `N/A` (D5, `### Phase 0 ratification record (2026-08-13)`; disposition row 4, no row overridden), so this correction is **unconditionally mandatory**; leaving it ships a self-contradiction.
- **Cross-ref sweep** — grep for `memory`, `MEMORY.md`, `memory_excerpt`, `memory_present`, `memory_digest` across `src/`, `scripts/`, and repo-root docs; reconcile anything the new model contradicts.

### Verify

- Cross-ref sweep clean: no doc cites `.claude/memory/MEMORY.md` or a bare `MEMORY.md` as a live path; no doc claims `/constitute` populates memory; no doc claims `projectOwned` protects a file.
- Repo-root `CLAUDE.md` plan entry + "Where to find what" row, and `CHANGELOG.md`, carry the change.
- **Pre-empt-future-hallucination pass:** a fresh session reading the docs would not believe (a) memory lives at `.claude/memory/`, (b) `/specify`'s green four-read gate implies memory was read, (c) `memory_excerpt` is consumed by any command it is not, (d) the 13/7 memory split is the same set as the 13/7 model-invocable split, or (e) `/constitute` populates memory.

---

## Phase 7 — Consumer e2e (user-driven, HARD GATE)

Run against a consumer install with a POPULATED `.devforge/memory.md` (`<v2-install>` has 151 lines) plus a scratch install with no memory file:

- Re-run the motivating ticket through `/devforge:research` and confirm the backend-repo entry and the "read the backend mapper before scoping" lesson reach the run's evidence-gathering before scoping is committed.
- `/devforge:specify` → confirm the gate records a real `populated` state and that stderr/report no longer certifies a read of a nonexistent file.
- `/devforge:plan`, `/devforge:breakdown`, `/devforge:review`, `/devforge:verify`, `/devforge:audit` → confirm each `READS` command surfaces memory content it previously could not see.
- On the empty scratch install → confirm every command runs clean with `absent` memory: no block, no spurious warning (Phase 3's scope guard).
- Per OQ-5 (**ratified IN scope 2026-08-13 — this bullet is not optional**): re-run `install.sh` against the populated install and confirm `.devforge/memory.md` is NOT overwritten.

### Verify

- The motivating incident does not reproduce: the same ticket, run again, has the memory entries in hand at scoping time.
- No command regressed on a memory-less install.
- The `/specify` gate's green state is now backed by an actual read.
- `install.sh` re-run preserves accumulated memory (OQ-5 was ratified IN scope, so this criterion applies).

---

## Dependencies + related

- **Plan 22 (`22-VERIFY-COMMAND-REDESIGN-PLAN.md`)** — finding F is the original single-file fix of this exact bug, and the reason the class is *known* rather than *newly discovered*. Its scope note ("the `/review`-side fix is a separate concern for the orchestrator to route") is the routing that never happened; plan 74 is that routing, generalized.
- **Plan 41 (`41-AGENT-EXECUTOR-REACHABILITY-PLAN.md`)** — the model for WI-5's enforcement half (maintainer-side checker + live-`src/` pytest as the gate, since the repo has no CI). Its type-3 "orphaned finding" class is the exact shape of the unconsumed `memory_excerpt`. D6 follows its D7 complement-not-fold precedent.
- **Plan 49 (`49-DEVFORGE-RUNTIME-STATE-DISPOSITION-PLAN.md`)** — the model for the per-command disposition table, and the owner of memory's git disposition (`storage-rules.md:89`, VERSIONED, delta folds into the `/finalize` squash). Plan 74 adds a READ lane on top; it does not touch the storage class.
- **Plan 08 (`08-CLAUDE-MD-COMMAND-TRIM-PLAN.md`)** — the always-on-context cost finding that makes a blanket "all 20 commands read memory" not automatically correct (D5).
- **Plan 67 / plan 69** — the register for carrying an upstream, unverified assertion into a downstream stage without treating it as grounded evidence (Phase 4's honesty bound copies their framing).
- **Plan 73 (`73-LITERAL-ARCHAEOLOGY-EVIDENCE-ARM-PLAN.md`)** — SIBLING, related but separate mechanism (grounding claims in code literals vs reading prior sessions' lessons). Explicit Non-goal to touch it; a concurrent session owns that file.
- **Plan 26 (`26-REINTRODUCE-FIX-PLAN.md`)** and **plan 24** — the source of `/fix`'s and `/summarize`'s correct-path preflights, and of the "pure synthesis, read-only" framing behind `/summarize`'s proposed `N/A`.

## Context for next session

The trap here is fixing only the visible half. "Four commands point at a dead path" is the symptom that greps cleanly; it is one of **four** mechanisms, and the other three survive a pure path sweep: the `/specify` gate that certifies a read of a nonexistent file (`_cmds_phase01.py:117` validates a string, nothing more), the seven preflights that emit a `memory_excerpt` **zero** command specs consume, and the 5-line digest that is provably the stub preamble for any pipeline-written memory file. A sweep alone leaves a pipeline that reads the right path and still learns nothing.

The second trap is over-fixing in the other direction: "all commands should work with memory" does not mean "all 20 issue a read." A command that reads memory and does nothing with it is the orphan this plan exists to kill — seven of them exist right now. Coverage is by **recorded decision** (`READS` or `N/A` + reason), enforced mechanically, which is why WI-5 is the backbone and WI-2 is merely the visible part.

The third trap is a blanket existence check for WI-3. It would be near-vacuous, because `install.sh:271` ships the stub into every install — `.devforge/memory.md` almost always EXISTS while being structurally empty. The three-state probe (`absent` / `stub` / `populated`) is the design, and it deliberately mirrors the constitution populate-guard the framework already uses for "the file is there but nobody filled it in."

Do not propose a new always-on `CLAUDE.md` rule. Two already exist, in two independent always-on channels (`src/CLAUDE.md:205`, `src/constitution.md:238`), and neither prevented the incident. The gap is in the enumerated phases, not in awareness.

## When resuming work

1. **Read this file in full.** The Verified-state section replaces re-derivation — every anchor in it was checked against live `src/` and two consumer installs on 2026-08-12, and re-checked against live `src/` on 2026-08-13 after plan 73 shipped. Read `### Re-verification 2026-08-13 (post-plan-73)` before trusting any line number in this plan: it records the ONE anchor that moved (`plan/main.md:611` → `:614`), confirms the rest exact, closes OQ-5's un-verified alternative, and names a post-73 boundary Phase 4 must not cross. Re-verify only what changed since.
2. **Phase 0 RATIFIED 2026-08-13 — this gate has CLEARED. Do not stall waiting for it.** The items that were live maintainer decisions at drafting time — the seven `N/A` calls (especially `/constitute`), the five borderline rows (the four flagged in D5: `/constitute`, `/generate-docs`, `/summarize`, `/pr-review`; plus `/finalize`, the plan's own-initiative call), OQ-5 (install clobber, in or out), and OQ-6 (drop the orphan field or reclassify) — are all settled, and every D1–D8 / OQ-1–OQ-6 outcome is recorded inline in `### Phase 0 ratification record (2026-08-13)`. The disposition table stands **exactly as drafted: 13 `READS` / 7 `N/A`, no row overridden.** **Read the ratification record for what was DECIDED; the recommendation text above it is the reasoning, not the outcome.** Do not reopen a settled item without the maintainer.
3. **Re-confirm the live anchors before editing** — line numbers drift, and one already has. Re-check `_specify/_schema.py:230,291-292,309`, `_specify/_cmds_phase01.py:117,136-154,277-302`, `_topic.py:70-101`, `_review/_preflight.py:171-177`, `_audit/_preflight.py:381-388`, `src/commands/implement/references/agent-brief.md:12`, `src/manifest.json:38`, `scripts/emitters/claude.py:57`, and **`src/commands/plan/main.md:614` (drifted +3 from `:611`; the two live-instruction sites — disposition row 9 and Phase 2b's task list — were corrected to `:614` on 2026-08-13, and the dated Verified-state list at `:45` deliberately retains `:611` as frozen history — see the 2026-08-13 re-verification)** before authoring Phase 2 or Phase 5.
4. **Phase 2's D3 pairing is atomic.** `_schema.py:309` is a render-group KEY, not a path — sweep it together with `_cmds_phase01._group_for_path` and `_topic.source_origin_for_path`, or Phase-1 findings silently render under the wrong heading with no error.
5. **Phase 3 changes exactly one gate slot's provenance.** Do not add an existence requirement anywhere else; a memory-less install must run the whole pipeline unblocked.
6. **Phase 5c's Rule 2 is CONJUNCTIVE — do not loosen it to a disjunction.** "A read is performed AND a consuming surface names the field" is the whole point; "prose OR references OR preflight" would pass mechanism #3, the exact defect WI-5 exists to kill. The mechanism-#3 regression test in Phase 5's Verify is what keeps it honest. The checker still states its own non-coverage (consumption IS checked; substantive-use, entry-selection, and content accuracy are NOT), per plan 41's D5/D8 honesty precedent.
7. **Phase 5a's `agent-brief.md:12` bullet is the ONLY phase step that closes mechanism #4.** D7 settles it and Phase 0(e) ratifies it, but the edit lives in exactly one place — if that bullet is dropped, every other Verify block in this plan still passes while `/implement`'s only memory input stays the 5-line stub-preamble digest.
8. Route every `src/commands/*/main.md`, `references/`, agent, and `src/CLAUDE.md` edit through **instruction-author → instruction-reviewer + claude-code-guide** (they ship into `.claude/`); every `src/devforge/lib/` and `scripts/` change through **python-engineer → python-reviewer**, test-first. This PLAN file lives at repo root, does not ship into `.claude/`, and needs no Claude Code authoring loop itself.
