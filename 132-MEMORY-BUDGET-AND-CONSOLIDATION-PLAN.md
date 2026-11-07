# 132 — Memory Budget And Consolidation Plan

**Created**: 2026-10-05
**Status**: **Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start. Nothing is built and nothing is measured.** Every decision (D1–D15) and every open question (OQ-1–OQ-9) carries a recommendation, every decision carries its strongest counter-argument, and each waits for the maintainer. ⚠ **Evidence class, repeated in every summary of this plan: TWO consumer installations on the 1.x command layout (wrapper mode, one operator, one method), measured there by a sibling session with shell tools and NOT re-measurable from this repo; ONE 2.0 data point — one feature in one small install, the maintainer's 2.0 end-to-end test install, read on 2026-10-05 by the session that commissioned this plan; the 2.0 tree VERIFIED here by grep and read on 2026-10-05; NOTHING built and NOTHING measured by this plan.** ⚠ **Sequencing.** Plans execute in NUMERIC ORDER (D15). Plans 128 and 131 (both Phase 0 OPEN) build BEFORE 132 and edit the same prose — `src/commands/verify/main.md` PHASE 7 and `src/devforge/memory.md` (131 D14), `FINDINGS.md` (128 D9 (b)) — so every anchor below drifts by build time. ⚠ **Numbered 132 because a glob of `13[0-9]-*.md` at the repo root on 2026-10-05 returns 130 and 131 only. Other sessions work in this checkout and may take 132 first; a resuming session re-checks the number before trusting it.** ⚠ **Every `file:line` here was read on 2026-10-05 and will drift — grep the quoted text, never the digits.**
**Branch:** `develop-2.0-init`

On 2026-10-05 a sibling session, writing on the maintainer's behalf, handed over a memory-hygiene METHOD and what it did to two consumer installations' memory files. **The centerpiece of this plan is a user-invoked command that carries that method end to end — measure → audit → target structure → execute with a ledger and a verbatim archive → mechanical gates → regrowth guard (D2–D6).** It is supported by a deterministic census in the shared memory module, which is the command's own measurement step (D7), and by a cheap regrowth guard in `/devforge:verify` that points at the command (D8, D9). The framing is D1: on 2.0 the lever is a FILE budget, because the read side is bounded only for helper-verb reads and only by lines. Plan 79's excerpt stands untouched.

---

## Origin & evidence

⚠ **Evidence class, stated first and repeated in every summary of this plan: TWO consumer installations on the 1.x command layout (wrapper mode, one operator, one method), measured there by a sibling session with shell tools and NOT re-measurable from this repo; ONE 2.0 data point — one feature in one small install — read on 2026-10-05 by the session that commissioned this plan; the 2.0 tree VERIFIED here by grep and read on 2026-10-05; NOTHING built and NOTHING measured by this plan.**

**Maintainer directive, 2026-10-05 (recorded here in English):** *"the main thing is that the memory-hygiene method is understood and that the repo has a command for it."* It orders this plan: the command (D2–D6) is the main deliverable, the census (D7) is the command's measurement step, the `/devforge:verify` check (D8, D9) is a regrowth guard that names the command, and OQ-6 keeps the command in one plan and does not cut it.

The handoff covers two consumer installations, called **installation A** and **installation B** here and nothing else. Both run the 1.x command layout in wrapper mode, both are operated by the same person, and both were consolidated with the same method — A on 2026-10-04, B on 2026-10-05. Every number below was measured there with `/usr/bin/grep`, `/usr/bin/wc` and `awk` over the one memory file; these are **the handoff's figures**, quoted as given. Some do not reconcile: A's 198 tagged plus 143 untagged make 341, not its 354 entries, and 198 is also its count of entries over 600 chars; "140 of 315 entries" stands against 354; and A's ≈ 65 K tokens per load × ≈ 13 loads per feature is ≈ 845 K, against the handoff's ≈ 750 K per feature. They come from different greps and snapshots, and this plan does not reconcile them. **No decision below depends on the per-feature multiplier** — the budget is a file size, and the token figures are context only.

| Before consolidation | Installation A | Installation B |
|---|---|---|
| File size | 259 KB | 71 KB — doubled in 17 days (35 → 71 KB) |
| Entries | 354 | 124 |
| `## ` headers | 16 (its 1.x template had 10) | not reported |
| Entries over 600 chars / longest | 198 / 4,087 | 62 / 1,676 |
| Untagged / undated entries | 143 / 188 | 124 untagged (0 tagged) / not reported |
| Tokens per load (bytes / 4) | ≈ 65 K | ≈ 18 K |
| Loads per feature | ≈ 13 per 10-task feature | ≈ 24 per 18-task feature |
| Memory tokens per feature | ≈ 750 K | ≈ 430 K |

A also gained ≈ 12 KB per feature verification; 140 of 315 entries narrated one campaign; corrections sat beside the claims they overturned; and Known Pitfalls was 74 % of the file. **The audit** found 14 live contradictions in A and 18 in B — store against store and store against repo, several of them corrections of corrections. **Ledger outcomes:** A keep 24 / compress 12 / merge 256 / archive 56 / delete 6 (354 rows); B keep 20 / compress 19 / merge 83 / archive 1 / delete 1 (124 rows).

| Gate, before → after | Installation A | Installation B |
|---|---|---|
| Bytes | 259,406 → 36,676 | 71,247 → 32,224 |
| Tagged entries | 198 → 72 | 0 → 65 |
| `## ` headers | 16 → 11 | not reported |
| Entries over 600 chars / longest | 198 / 4,087 → 0 / 596 | 62 / 1,676 → 0 / 597 |
| `SUPERSEDED` / `Correction` lines | 2 / 11 → 0 / 0 | not reported |
| Duplicate pastes | 5 → 0 | not reported |
| Tokens per load (bytes / 4) | ≈ 64,850 → ≈ 9,170 | ≈ 17,800 → ≈ 8,060 |

In both: the archive was `cmp`-identical to the old file, ledger rows equalled the old entry count, no command file changed, and the inner repo was untouched. B later sat at 38.4 KB after an import — ≈ 2 KB from its 40 KB budget. **Both installations REJECTED a stricter target** ("entries over 300 chars ≤ 10"); the budget they kept is ≤ 40 KB and ≤ 80 tagged lesson entries, an entry target of ≈ 350 chars and a hard ceiling of 600.

**Tooling.** In one installation a shell hook returned false zeros for `grep -c`, `wc -l` and `head -1`; A measured a one-line offset from a hook-routed grep. A grep gate such as "`grep -c SUPERSEDED` → 0" is defeated when the ledger or the archive quotes the word and the grep is not scoped to the one file. Both facts are the design reason D2 gives every count to the helper. The handoff's 1.x point about compaction advice that says "preserve every memory entry" is N/A on 2.0 (F6).

**The 2.0 data point** (read-only, 2026-10-05, by the session that commissioned this plan). The maintainer's 2.0 end-to-end test install's `.devforge/memory.md` holds 3,605 bytes, 20 lines and 5 bullets, last modified 2026-06-18 — before plan 79 built (79's Status line: Phases 1–5 built 2026-08-18). One `/devforge:verify` run wrote 3 entries of 797, 493 and 1,705 characters — 2 of 3 over 600 — tagged `**[verify / <feature>, <date>]**`; the other 2 bullets sit under `## Task Outcomes`, the retired per-task writer's section. n = 1 feature. Because that run predates plan 79's build, the PHASE 7 prose it ran under is not today's text, and whether it already said "short dated entry" and "Keep it LIGHT" (`src/commands/verify/main.md:380`, `:390` today) is not checked here. What the data point shows is only that a 2.0 prose writer produced over-ceiling entries on its first run.

This repo is public. **Public-repo rule: this plan names no client, company, workspace, package, ticket, spec number, feature name or filesystem path outside this repo**, in this file and in every phase, commit, record and ledger line it drives. The consumer installations are "installation A" and "installation B"; the 2.0 install is "the maintainer's 2.0 end-to-end test install"; the sender is "a sibling session".

---

## Overlap with plans 128, 131, 124, 74 and 79 — what is NOT re-decided here

- **Plan 128** (`128-AC-VERIFICATION-COMMAND-GATE-PLAN.md`, Phase 0 OPEN on 2026-10-05). Its D9 (`:148`–`:154`): **(a)** declines a new memory-template SECTION; **(b)** records "no size budget and no consolidation step" as a new `FINDINGS.md` entry with no plan and no owner, on the counter-argument *"the excerpt bounds what a session READS, not what the file becomes"* (`:154`). Its F7 table row reads *"Bounded memory read cost | BOUNDED"* (`:60`); its non-goals are *"No memory template or PHASE 7 rubric change"* and *"No memory size-budget or consolidation build"* (`:385`–`:386`) and *"No `src/CLAUDE.md` edit"* (`:388`); its honest bound is *"2.0 has no memory consolidation step"* (`:411`). Its cost bound is F10 (`:70`): *"Any lane this plan adds must be mechanical, add no `AskUserQuestion` stop, and add at most one helper call per command."* 128 builds before 132; 132 edits nothing in it and offers its ratifier two clauses (D13).
- **Plan 131** (`131-CONSUMER-LESSONS-TRIAGE-PLAN.md`, Phase 0 OPEN, untracked on 2026-10-05). Its D14 (`:329`–`:336`) puts the entry SHAPE `- **[TAG]** YYYY-MM-DD — <at most two lines> — <pointer: specs/<feature>/…>` and two rules — a changed fact is deleted and re-inserted, re-dated, at the END of its section, because the excerpt keeps a section's LAST lines; never cite another entry by position — into the PHASE 7 rubric and the template comments, with *"No size cap, no entry cap, no consolidation (128 D9 (b))"* (`:331`). Its F15 says *"The read side is bounded"* (`:75`); its R3 row routes consolidation to 128 (`:101`); its non-goal is *"No memory size cap or consolidation step"* (`:693`). 131 builds before 132 and edits the same PHASE 7 prose and template comments. 132 consumes D14 **as ratified** (D5, D9) and offers one clause (D13).
- **Plan 124** (`124-PIPELINE-COST-REDUCTION-PLAN.md`, a stub): fewer stops and fewer calls in the regular pipeline. 132 adds NO `AskUserQuestion` stop to the regular pipeline; its one stop is inside the user-invoked command (D2). It adds zero helper calls to `/devforge:verify` on the census path (D8) and one conditional call on the entry-check path — two after a violation (D9, Bound 1).
- **Plans 74 and 79** (both DONE). The read lane (74) and the section-aware excerpt (79) stand: 132 does not change `_render_excerpt`, the 120-line budget, the `## Task Outcomes` denylist or the newest-last cut, and does not re-open 79 OQ-1 (D1's counter-argument records that option).

---

## Verified structure (2026-10-05)

⚠ **Line digits drift — grep the quoted text, never the digits.** Every `file:line` below was read against this tree on 2026-10-05.

**F1 — The excerpt is LINE-bounded, not byte-bounded.** `src/devforge/lib/_shared/memory.py:327` `DEFAULT_EXCERPT_LINES = 120`; `:339` `EXCLUDED_MEMORY_SECTIONS = ("## Task Outcomes",)`; `_render_excerpt` at `:350`; its step 6 (`:393`–`:395`) *"Within a section, a truncation keeps the LAST `alloc` content lines -- both memory.md writers append, so the newest lines are the trailing ones"*. A line is a physical line, so a 1,705-char bullet is one line. Step 4 counts interior blank lines toward the budget (`:384`–`:386`); step 5 gives each retained section `min(len, budget // k)` and then ONE pass in file order hands the leftover to still-truncated sections (`:387`–`:392`, code `:451`–`:463`). Plan 79 predicted the gap at its OQ-1 counter-argument (`79-MEMORY-WINDOW-AND-RECEIPT-PLAN.md:406`–`:410`): *"a line budget bounds nothing on a file whose entries are long paragraphs, which is what `/devforge:verify`'s prose writer produces"*. 79 is DONE (`:3`) and is not re-opened here.

**F2 — Prose readers read the WHOLE file.** Emitted `src/CLAUDE.md:179` *"**Pre-flight check** (before each task): read `constitution.md` and `.devforge/memory.md`"*; `:217` *"check `.devforge/memory.md` for lessons from past sessions"*. `src/commands/implement/references/agent-brief.md:12` *"Read `.devforge/memory.md`, SELECT the entries that bear on the area this task touches"* — deliberately KEPT by plan 79 D7 (`79-…:371`–`:391`). `src/commands/specify/main.md:195` *"If the file exists, read it."* (under `### 1.2`, `:193`). `src/commands/verify/main.md:390` *"Read `.devforge/memory.md`, locate the chosen `## ` heading"*. All 20 files under `src/agents/` carry the phrase *"check `.devforge/memory.md` for prior lessons"* — the line `src/agents-AUTHORING.md` prescribes (`:79`, `:151`, `:179`); `src/agents/code-reviewer.md:32` adds a second read (*"cross-reference `.devforge/memory.md` for known pitfalls"*). Plan 74's Status records that the architect reads memory by two routes (`74-MEMORY-LANE-INTEGRITY-PLAN.md:9`, follow-up 4). **Whether a dispatched agent actually opens the file is UNMEASURED.**

**F3 — Helper-verb reads ARE bounded, line-wise, through one accessor.** `scripts/lib/memory_lane.py:104` `DISPOSITIONS` lists 13 `READS` and 8 `N/A` commands. `read_memory_context` (`memory.py:499`) is called from 12 helper modules outside `memory.py`; its docstring promises *"Returns a dict with exactly these keys"* (`:510`), and `tests/lib/_shared/test_memory.py` pins that dict exactly (`TestReadMemoryContext.test_absent`, `:559`–`:569`). Example consumer: `src/devforge/lib/_verify/_preflight.py:184`–`:187` (`read_memory_context` → `memory_present`, `memory_excerpt`).

**F4 — One command writes lessons: `/devforge:verify` PHASE 7.** `src/commands/verify/main.md:372` `## PHASE 7 — Memory update`; `:378` *"an entry already covering this lesson makes an append a duplicate — sharpen or extend the existing wording instead of restating it"*; `:380` *"Keep it LIGHT: feature-level only"*; `:382` *"there is no fourth bucket"*; the three buckets at `:384`–`:386`; `:390` *"insert the short dated entry immediately BEFORE the next `## ` heading"* and *"This write is orchestrator prose — no `verify_helper` verb writes memory"*. There is no size, entry-count, length, tag or pointer rule. `verification.md` is rendered at PHASE 5 by `render-report` (`### 5.2`, `:338`–`:346`), BEFORE PHASE 7; PHASE 8 (`:392`) is the user-facing present step. **verify's end-of-run commit does not include `memory.md`** — its `--paths` are `verification.md` and `verify-state.json`, plus `spec.md` on a flip (`:455`–`:459`) — so the PHASE 7 delta stays uncommitted until `/devforge:finalize`'s safety-net commit (F6).

**F5 — A second writer: an agent.** `src/agents/runtime-debugger.md:66` *"…and write concise notes on error patterns and fixes back to `.devforge/memory.md`"* — unshaped and outside the PHASE 7 rubric. `src/commands/breakdown/main.md:306` assigns runtime-debugger to *"Bug investigation with runtime symptoms"* tasks, which `/devforge:implement` dispatches. Plan 131 F15 (`131-…:75`) *"The only command that WRITES a lesson into it is `/devforge:verify` PHASE 7"* is true of commands; this agent is the gap. Emitted `src/CLAUDE.md:314` makes the same claim to every session: *"`.devforge/memory.md` is not a history home either: it carries feature-level LESSONS, written by `/devforge:verify` into its named `## ` sections"* — true of the verify writer, silent on this agent. `src/agents/tech-writer.md:310` disclaims *"`.devforge/memory.md` updates"*. Task-level detail reaches a task file through `mark-complete --notes` (`src/commands/implement/main.md:282`); PHASE 7 names Completion Notes only as where per-task detail belongs (`verify/main.md:380`) and does not read them.

**F6 — Nothing consolidates, prunes or budgets.** `/devforge:finalize` puts known pitfalls from `.devforge/memory.md` into the tech-writer brief (`src/commands/finalize/main.md:138`) and commits the file in its safety-net commit (`:166`–`:169`: `commit-artifacts --paths '["<feature_dir>/", ".devforge/memory.md", ".devforge/spec-stamps.jsonl"]'`). `commit-artifacts` stages named paths only (`src/devforge/lib/_artifact/_cli.py:37` *"NEVER `git add -A` / `git add .`"*) and always writes the message `[WIP] <label>` (`:268`). A case-insensitive grep for `compact` over `src/` finds hook matchers, the session-state prose and unrelated wording — no advice to preserve memory entries — so the handoff's 1.x compaction point is N/A on 2.0.

**F7 — The template.** `src/devforge/memory.md:1`–`:13`: the title `# Project Memory` and four sections (`## Architecture Decisions`, `## Known Pitfalls`, `## What Worked`, `## What Failed`), each with one HTML comment; no entry-format rule. Architecture Decisions has no writer in the PHASE 7 rubric (observation only). `tests/lib/_shared/test_memory.py:89` reads the real template as `_REAL_STUB_PATH`, and `test_stub_against_real_shipped_stub_fixture` (`:571`–`:584`) pins it as `stub` with an empty excerpt. `install.sh:277` and `:296` call it *"the 13-line stub"*.

**F8 — `memory.md` is project-owned.** `src/manifest.json:39` lists `.devforge/memory.md` under `projectOwned`; `install.sh:309` `_PRESERVE="memory.md project-config.json"`; `src/devforge/storage-rules.md:124` *"`manifest.json`'s `projectOwned` DOCUMENTS, it does not ENFORCE"*. `update.sh` has no `memory.md` hit. **A template-comment change reaches FRESH installs only; an existing install's file never receives it.**

**F9 — One comment-tracking scan, by rule.** `_scan_lines` (`memory.py:206`) is the module's comment-aware state machine, and its docstring (`:217`–`:219`) says *"the comment-tracking logic must not be duplicated a second time anywhere else in this module"*. `_render_excerpt` drops text before the first `## ` heading as PREAMBLE (`:365`–`:367`). `MEMORY_RELATIVE_PATH = ".devforge/memory.md"` (`:147`) is a forward-slash literal at least one consumer compares for exact equality (`:135`–`:146`), and the path is install-root relative even in wrapper mode (`:131`–`:132`).

**F10 — Gates and pins a new command touches.** `scripts/emitters/claude.py:57` `_PROMOTED` (21 names); the emit lands at `.claude/commands/devforge/` (`:69`). `disable-model-invocation: true` sits at `:4` of `configure`, `constitute`, `init-forge` and `generate-docs`'s `main.md`, and in no other `src/commands/*/main.md`. `memory_lane.py`: `DISPOSITIONS` (`:104`; Rule 1a — every `_PROMOTED` command needs a row); `MEMORY_TOKENS = ("memory_excerpt", "memory_state")` (`:255`); the read-primitive regex `read_memory_context|read_memory_excerpt|probe_memory_state|memory_present` (`:268`–`:271`); Rule 2 — a `READS` command's helper calls a primitive AND its `main.md` / `references/*.md` name a token (`:496`–`:500`); Rule 3 — an `N/A` command carries neither token anywhere (`:501`–`:506`); the helper is found at `_<cmd_u>/**/*.py` plus `<cmd_u>_helper.py` (`:301`–`:320`). Pins: `tests/lib/test_memory_lane.py:218` `len(_mod.DISPOSITIONS) == 21` and `:548`–`:550` `test_live_repo_matches_the_21_known_names`; `src/devforge/lib/_profile/_segment.py:71` `HELPER_STEMS` with `tests/lib/_profile/test_segment.py:122`–`:123` (`len(KNOWN_COMMANDS) == 21`); `tests/lib/_verify/test_preflight.py:728` `len(_SUBCOMMAND_REGISTRY) == 16` (128 moves it to 17). Launcher shape: `src/devforge/lib/report_bug_helper` beside `report_bug_helper.py` and the package `_report_bug/`. The agent-reachability gate (`scripts/lib/agent_reachability.py`) applies only to a command that dispatches an agent.

**F11 — The human-typed-only set is enumerated in prose.** `src/CLAUDE.md:47` *"Four are **human-typed only**"* … *"Every other forge command is model-invocable"*; `:78` *"Four commands — the setup chain … — are human-typed only, so their entries below carry a full description: this section is the only place the model sees what they do."*; `:71` opens the Standalone list. `README.md:57` *"Seventeen of the twenty-one are model-invocable … Four are human-typed only"*. Repo `CLAUDE.md:34` names the four. `src/devforge/storage-rules.md:123` *"Each of the 21 emitted commands carries exactly one declared memory disposition (13 `READS` / 8 `N/A`)"*; `memory_lane.py:69`–`:79` carries the 21, 17/4 and 13/8 counts.

**F12 — Storage classes.** `src/devforge/storage-rules.md:106` `| memory.md | VERSIONED | …`; the class table (`:104`–`:120`) already carries subdirectory rows (`profile/`, `lib/`, `command-refs/`). `src/files/devforge.gitignore:1`–`:21` lists EPHEMERAL and CODE paths only, so a new VERSIONED `.devforge/` subdirectory needs a storage-rules row and NO gitignore line. `.devforge/wip.md` is EPHEMERAL (`storage-rules.md:112`; `devforge.gitignore:3`) — `/devforge:implement`'s per-task crash-recovery marker (`implement/main.md:39`). `src/CLAUDE.md:302` states md files are auto-indexed by codebase-memory-mcp.

**F13 — FINDINGS.** `FINDINGS.md` holds entries `## 1.` through `## 12.`; none is about memory size or consolidation (128 D9 (b) would add one at 128's Phase 4). `FINDINGS.md:5`: a finding drafted into a plan has its entry replaced with a pointer — and finding 4's precedent, on the same line, amends in place.

**F14 — The approval stop's tool.** `AskUserQuestion` appears in 18 files under `src/commands/` on 2026-10-05; plan 124 quotes the tool's limit *"each `AskUserQuestion` call supports 1-4 questions with 2-4 options each"* (`124-…:24`, citing `https://code.claude.com/docs/en/agent-sdk/user-input`). D2's one stop has three options.

---

## Phase 0 — ratification

Nothing below is ratified. Each item states the question, its proposal, a recommendation, what it costs, and the strongest counter-argument, **recorded honestly rather than answered away**. A weakness that is not the strongest counter-argument is recorded as a **Bound, recorded:** line. Costs are weighed against 128 F10's bound (`128-…:70`). The command is named `consolidate-memory` throughout as OQ-1's recommendation; a different OQ-1 outcome renames it everywhere.

### D1 — The lever is a FILE budget, not a read budget (F1, F2, F3)

**Proposal:** 132 bounds the FILE — bytes, entries, entry length — and changes no reader. On 2.0 only helper-verb reads are bounded, and only by lines (F1, F3); five prose read paths and all 20 agent files read the whole file (F2). A file budget bounds the excerpt and every whole-file read at once, with no change to plan 79's excerpt. **When the file's content lines — entries plus the interior blank lines step 4 counts — total ≤ 120, the excerpt drops nothing:** step 5's leftover, `120 − Σ alloc`, is at least every section's remaining room whenever `Σ len ≤ 120`, so its one pass grants each section its full length (F1). Eighty single-line entries with no blank separators meet that; eighty separated by blank lines (159 content lines) do not — hence D6's one-physical-line rule and D5's `excerpt_fits` gate.
**RECOMMEND.** **Cost:** none by itself; D2–D9 carry the cost.
**Counter-argument, recorded:** **re-opening 79 OQ-1 — a byte-budgeted excerpt — would bound every helper-verb read without any consolidation step.** It leaves the whole-file readers unbounded and re-decides a DONE plan.

### D2 — The consolidation command: the method, end to end (the core deliverable)

**Proposal:** a new emitted command, `/devforge:consolidate-memory`, human-typed only (`disable-model-invocation: true`, OQ-9). It is never part of the regular pipeline, and no other command invokes it. Its `main.md` carries the method in this order, one command phase per step:
1. **Measure** — PHASE 0, the helper's `preflight` (D3). PHASE 1, `baseline`: the census-before (D7), a byte-identical archive, and a ledger skeleton with one row per OLD entry — `id`, `start_line`, `end_line`, `section`, `bytes`, `tag`, `date`, `provenance` (the short SHA and author date `git blame` attributes to the entry's first line, from ONE `git blame --porcelain` over the file at the start HEAD, never one call per entry), `ACTION`, `TARGET`, `note`, and the entry's first 100 chars. Everything is written to the scratch workdir `${TMPDIR:-/tmp}/forge-consolidate-memory/`; nothing under the install root changes before approval. Under `--census` (OQ-1), the command runs the helper's `census` verb, prints the result and stops — no write; it refuses only on D3's UTF-8 and absent-file reasons.
2. **Audit** — PHASE 2, the orchestrator: contradictions checked against the repo TODAY (memory against `constitution.md`, against `CLAUDE.md` and against the code), duplicates, misfiled entries and stale entries. It fills `ACTION` ∈ {`keep`, `compress`, `merge`, `archive`, `delete`} and `note` on every row, and writes the contradictions table to `contradictions.md`.
3. **Target structure** — PHASE 3, ONE `AskUserQuestion` stop: `approve` / `revise named rows` / `cancel`, shown beside the ledger's per-ACTION counts, the contradictions table and D6's target structure. `revise named rows` returns to PHASE 2 for exactly the rows the user names, re-runs PHASE 2's fills for those rows only, and re-presents the same stop; it repeats until `approve` or `cancel`, and because each iteration is the user's choice it carries no count bound. `cancel` removes the workdir and changes nothing.
4. **Execute, with a ledger and a verbatim archive** — PHASE 4: the orchestrator rewrites `.devforge/memory.md` under D6's brief (`references/rewrite-brief.md`). PHASE 5: the helper's `index-new` assigns each NEW entry a code — section prefix plus ordinal, `AD` / `KP` / `WW` / `WF` + n — into `new-entries-index.tsv`; codes live in the index, NEVER in `memory.md`. The orchestrator then fills `TARGET` on the ledger from that index.
5. **Gates** — PHASE 6: the helper's `verify` runs D5's gates; the command refuses to close until it exits 0. On a failure the orchestrator corrects the ledger, the index or the rewrite and re-runs it.
6. **Regrowth guard** — PHASE 7: the workdir moves into D4's directory and the result is committed (OQ-4). The consolidated file's header comment states the budget and the shape (D6), and the closing message names `/devforge:verify`'s regrowth line (D8) and the `--census` lane.

**Every count is taken by the helper, in Python, over `.devforge/memory.md` alone — never by shell `grep` / `wc` / `head` — so a shell hook that rewrites output (false zeros, measured in one installation) cannot corrupt the census or the gates.** That is the design reason for a helper, not a convenience; it also keeps a gate from counting a word the ledger or the archive quotes (D5). The command dispatches no agent: the orchestrator audits and rewrites, as both installations' sessions did, and tech-writer disclaims memory updates (F5); the agent-reachability gate is not engaged (F10).
**Alternative considered:** draft-then-install — the orchestrator writes the rewrite to `<workdir>/memory.new.md`, `verify` gates the DRAFT, and on exit 0 the helper atomically replaces `.devforge/memory.md` with it. The live file is then never in a half state, and the helper owns the write — at the cost of one more verb. Under the proposal, an abandoned run leaves a modified `memory.md` that `git checkout -- .devforge/memory.md` restores, because D3 refuses to start on an uncommitted file.
**RECOMMEND as proposed.** **Cost:** the largest item — a `main.md`, two references (`rewrite-brief.md` = D6; `ledger-contract.md` = D4 + D5), a helper package with five verbs (`census`, `preflight`, `baseline`, `index-new`, `verify`) and its tests, a `_PROMOTED` entry, a `memory_lane.py` row (OQ-8), the `src/CLAUDE.md` listing (OQ-9), and the count pins F10 names.
**Counter-argument, recorded:** **a helper verb plus a `FINDINGS.md` note would mechanize the gates without a new emitted surface** — 21 commands instead of 22, no `src/CLAUDE.md` sentence rewritten (F11) — and the method itself is prose an operator can follow by hand, as both installations did.

### D3 — Preconditions: mechanical, each refusing with a named reason

**Proposal:** `preflight` makes ONE read of the file — `read_memory_context(workspace_root, census=True)`, D7's opt-in keyword — and takes both `memory_state` and the census from it, emitting both. It exits 2 with a one-line stderr reason on the first of the checks below. **The helper is the single authority for every reason string:** `main.md` PHASE 0 restates none of them and tells the orchestrator to copy the helper's stderr line VERBATIM into its next user-facing message, the repo's usual pattern. Each reason this plan quotes is emitted as exactly the bytes shown — backticks included, the em dash as written — followed by a single newline; the reasons it does not quote (not tracked, branch, `wip.md`) are worded in the helper at build, which stays their single authority, and Phase 2's tests pin them. The checks:
- the file is not valid UTF-8 — the text-mode read raises `UnicodeDecodeError`, which is not an `OSError` and which `_read_lines` does not catch today (`memory.py:273`–`:283`; existing callers are not changed). `preflight` catches it and writes exactly: *"`.devforge/memory.md` is not valid UTF-8 — re-encode the file as UTF-8, then re-run `/devforge:consolidate-memory`."* The string is lane-neutral: on the consolidation lane the re-encoded file is then uncommitted, and the next run's uncommitted-file reason tells the user to commit it;
- `memory_state` is not `populated` — nothing to consolidate (OQ-8). `absent` writes exactly *"`.devforge/memory.md` does not exist — there is nothing to consolidate."*; `stub` writes exactly *"`.devforge/memory.md` holds no entries yet — there is nothing to consolidate."*;
- `.devforge/memory.md` is not tracked at HEAD (`git cat-file -e HEAD:.devforge/memory.md` fails);
- `git status --porcelain -- .devforge/memory.md` is non-empty — an uncommitted change. Between `/devforge:verify` and `/devforge:finalize` this refuses BY DESIGN, because PHASE 7's entry stays uncommitted until the safety-net commit (F4, F6). `preflight` writes exactly ONE fixed string to stderr, naming both remedies: *"`.devforge/memory.md` has uncommitted changes — run `/devforge:finalize` for the feature that wrote them, or commit the file, then re-run `/devforge:consolidate-memory`."* The helper composes the path in every quoted reason from `MEMORY_RELATIVE_PATH` (D7), so the emitted bytes equal the strings shown;
- `git log --branches --not HEAD -- .devforge/memory.md` is non-empty — a LOCAL branch carries a memory commit HEAD cannot reach (remote branches: OQ-5);
- `.devforge/wip.md` exists — a task is mid-run or was interrupted (F12).

**The `census` verb** (D2's `--census` lane) checks only two of these: it exits 2 on a non-UTF-8 file with the UTF-8 string above, and on an absent file with the `absent` string above; on a stub it prints the census (0 entries, verdict `within`) and exits 0, as it does on a populated file. It runs no git check and writes nothing.

`preflight` also records `git status --porcelain` of the install root and, in wrapper mode, `git -C <source-root> status --porcelain`, as the baselines D5's last two gates compare against. A feature mid-pipeline on the current branch is NOT a blocker beyond these checks: its verification appends to the consolidated file.
**Bound, recorded:** a local branch already merged by squash or rebase still carries memory commits HEAD cannot reach, so the branch check refuses until that branch is deleted; the refusal names the branch.
**RECOMMEND.** **Cost:** one verb and its tests in temp git repositories, one failing case per precondition.
**Counter-argument, recorded:** **a teammate's unpushed branch is invisible to every local check** — stated as an honest bound, not solved.

### D4 — Artifacts: a tracked consolidation record

**Proposal:** PHASE 7 moves six files into `.devforge/memory-consolidations/<YYYY-MM-DD>-<short-sha>/`, `<short-sha>` being the start HEAD: `archive-<sha>.md`, `ledger.tsv`, `new-entries-index.tsv`, `contradictions.md`, `census-before.json`, `census-after.json`. D3's status snapshots stay in the workdir and are removed with it. The class is VERSIONED: one `storage-rules.md` row, no gitignore line (F12). The archive duplicates git history on purpose — the ledger cites its line numbers, and it survives a squash or a history rewrite of the commit it came from (OQ-3 offers git-only). None of these files feeds any read path: every reader keys on `.devforge/memory.md` alone (F9).
**Bound, recorded:** `src/CLAUDE.md:302` states md files are auto-indexed by codebase-memory-mcp; whether that indexing reaches a tracked `.devforge/` subdirectory is not checked here. If it does, superseded lessons in the archive become searchable beside the live file.
**RECOMMEND.** **Cost:** the move in `main.md`, the storage-rules row, a growing tracked directory (one per consolidation).
**Counter-argument, recorded:** **every consolidation adds a tracked copy of the old file — 259 KB in installation A's case — to a directory that only grows**, when `git show <sha>:.devforge/memory.md` already recovers it.

### D5 — Gates: every count scoped to `.devforge/memory.md` alone

**Proposal:** `verify` exits 0 only when every gate passes, and its JSON names each failing gate with the offending entries. Every count runs over `.devforge/memory.md` alone, so the ledger and the archive can neither satisfy nor defeat a gate.
- **Budget and shape:** the file's on-disk `bytes` (D7) ≤ budget; entries ≤ budget; 0 entries over the ceiling; `excerpt_fits` true (D1, D7); the template's four `## ` headings present and none duplicated — unknown headings LISTED, not failed, since consumers may add sections and 79 D3 includes unknown headings by default; `## Task Outcomes` absent (its rows are `archive`); 0 entries without 131 D14's stamp; 0 HARD correction markers; 0 positional references; 0 byte-identical duplicate entries.
- **Coverage:** the archive is byte-identical to `git show <start-HEAD>:.devforge/memory.md`; the ledger's row count equals the entry count the SAME parser re-derives from the archive; every row has exactly one valid `ACTION`; every `delete` and `merge` row names its superseding entry code or rule in `TARGET` / `note` — nothing is deleted on judgement alone; every `TARGET` code exists in the index; every new entry is the `TARGET` of at least one row or carries a "genuinely new" reason in the index's `note` column.
- **Containment:** no path except `.devforge/memory.md` differs from D3's install-root snapshot (the workdir is outside the tree until PHASE 7); in wrapper mode the inner repo's status equals D3's snapshot.
- **Readable:** a `UnicodeDecodeError` reading the rewritten file is a failing gate, named in the JSON with D3's UTF-8 string — never a traceback; the gates that read the rewritten file are then not evaluated.

On exit 0, `verify` writes `<workdir>/census-after.json` — D7's census of the consolidated file, the sixth artifact D4 lists; on any failing gate it writes no such file.
**Bounds, recorded.** **(1)** The positional-reference and correction-marker gates are heuristics (D7): a false positive forces a rewording, accepted. **(2)** The stamp gate keys on 131 D14 AS RATIFIED; if D14 is declined or amended, this gate is re-derived at 132's Phase 0 close or cut.
**RECOMMEND.** **Cost:** the `verify` verb and one failing-case test per gate.
**Counter-argument, recorded:** **gates prove shape and bookkeeping, not that the merged entries say what the old ones meant** — a faithful-looking ledger can still lose a lesson in a `compress` row; the archive and the user's PHASE 3 review are the only guard.

### D6 — Target structure: the rewrite brief

**Proposal:** `references/rewrite-brief.md` states the target the PHASE 4 rewrite meets: the template's four sections; one fact, one home — a lesson restating a `constitution.md` or `CLAUDE.md` rule is deleted with a pointer note in the ledger; 131 D14's entry shape; **each entry ONE physical line (a `- ` bullet ≤ 600 chars) with no blank line between entries in a section**, so D1's lossless excerpt holds; a changed fact is rewritten, never overridden by a later paragraph; no positional references; and a header HTML comment after `# Project Memory` stating the budget and the shape. The header comment is how EXISTING installs receive the rule (F8): it is an HTML comment, which `_scan_lines` never scores as content, in the preamble, which the excerpt drops (F9) — so the shipped stub still probes `stub`. **DECLINE the handoff's `## Read first` block on 2.0:** it is a fifth section, which 128 D9 (a) declines in kind, and once the budget holds the excerpt is lossless (D1).
**RECOMMEND.** **Cost:** one reference file.
**Counter-argument, recorded:** **in installation A the generic lessons were buried among 219 pitfalls, and on 2.0 the newest-last cut drops a section's OLDEST lines first — foundational lessons are exactly the old ones whenever the budget is breached.**

### D7 — The census: the command's measurement step, in the single owner (F1, F9)

**Proposal:** `_shared/memory.py`, which owns the path, the probe and the reads (repo `CLAUDE.md` router), gains an entry parser, a pure `memory_census(lines, file_bytes)` and named constants — bytes 40,000; entries 80; entry ceiling 600 characters; `near` at ≥ 90 % of either budget; `over` above either. **An ENTRY** starts at a column-0 `- ` line, or at a populated non-bullet line after a blank line or a heading; it continues over following non-blank lines that are neither a `#` heading nor a new column-0 `- ` bullet. HTML-comment content (the `_scan_lines` semantics, F9) and the preamble before the first `## ` are not entries; every populated line belongs to exactly one entry. The parser reuses the ONE comment state machine — Phase 1 factors it into a per-line classifier `_scan_lines` also uses, with `_scan_lines`' behaviour unchanged (F9's rule). **Bytes, two kinds.** The file-level `bytes` — the figure the budget gate and the headroom use — is the ON-DISK size, matching the handoff's `wc -c` figures. The census path keeps `_read_lines`' existing text-mode read unchanged — the same `open(path, "r", encoding="utf-8")` and `readlines()` (`memory.py:273`–`:283`; text mode translates `\r\n` and a lone `\r` to `\n`) — and takes the on-disk size from `os.fstat(fh.fileno()).st_size` on that SAME open handle. A private helper (proposed name `_read_lines_and_size(path)`) returns `(lines, size)`, or `None` on the `OSError` `_read_lines` maps to `None`: one open, one read, and lines identical to `_read_lines`' by construction. `size` is passed to `memory_census` as `file_bytes`; the file-level figure is never re-derived from the lines, which would undercount a CRLF file. A span's `bytes` is the UTF-8 length of its entry text with line terminators normalised to `\n`, its `chars` the character count of that text; per-section `bytes` sum the spans. **Census fields:** bytes (on-disk), lines, entries, per-section entries and bytes, headings against the template's four (missing / unknown / duplicate), entries over the ceiling (in characters), longest, untagged, undated, positional-reference count, correction-marker counts, byte-identical duplicate entries, duplicates by normalized first 80 characters, `excerpt_fits` (`_render_excerpt` at `DEFAULT_EXCERPT_LINES` emits no truncation marker — calling it, not re-implementing it), headroom (bytes, entries), the verdict `within | near | over`, and `tokens ≈ bytes / 4` labelled as an estimate. **Correction markers** split into a HARD set (`SUPERSEDED`, `Correction:` / `Correction (`, `Update (`, `Resolved by`) and a COUNT-ONLY set (`no longer` — common English). **Positional references** are phrases such as "the entry above/below", "see above/below", "#N entry", or an ordinal plus entry/pitfall plus above/below; the exact regexes are chosen at build with tests, and the check is heuristic and says so. **The entry parser is a PUBLIC, pure function** of `memory.py` (proposed name `parse_memory_entries(lines)`) returning one span per entry — `start_line`, `end_line`, `section`, `bytes`, `chars`, `tag`, `date` and the first line's text; `memory_census` is built on it. **A public accessor** (proposed name `read_memory_entries(workspace_root)`) reads through `_read_lines_and_size` and returns `None` when the file is absent, otherwise a dict `{"bytes": int, "text": str, "entries": [span, ...]}` — the on-disk size, the joined text-mode lines and the spans — in `read_memory_context`'s dict style. **The consolidation helper reads `.devforge/memory.md` content only through a `memory.py` accessor — never by its own `open()` on that path — and names the path in git commands and messages only through `MEMORY_RELATIVE_PATH`** (F9); it opens its own ledger, index and archive directly. `read_memory_context` gains an OPT-IN keyword, `census=True`, that ALWAYS adds a `census` key: `None` when the file is absent; the census dict when it is `stub` or `populated` (a stub → 0 entries, verdict `within`). Under `census=True` its single read is `_read_lines_and_size`, so `present`, `memory_state` and `excerpt` equal the default call's with no new decode path. The default return keeps its three keys (F3's exact-dict test). A non-UTF-8 file raises `UnicodeDecodeError` from the text-mode read, as `_read_lines` does today.
**RECOMMEND.** **Cost:** one module extension and its tests.
**Counter-argument, recorded:** **a census without a remedy is noise** — which is why it ships only with the command (OQ-6) and why `/devforge:verify`'s line names the command (D8).

### D8 — `/devforge:verify` regrowth guard: one PHASE 8 line, zero extra calls (F3, F4)

**Proposal:** verify's `preflight` JSON carries `memory_census`, derived from the SAME single read through D7's opt-in keyword — `read_memory_context`'s single-read contract holds, and no helper call is added. PHASE 8 adds ONE line when the census verdict is `near` or `over` — a `None` census (no file) prints nothing — naming bytes and entries against the budget and `/devforge:consolidate-memory` for the user to type. When PHASE 7 wrote an entry, the line reads D9's post-write census; otherwise it reads the preflight census. **If D9 is declined, the line always reads the preflight census** — the file as it stood before PHASE 7's append, so a write that crosses the budget surfaces at the next run. **NO change to `verification.md`** — memory health is project state, not this feature's report, and 131 D7 / OQ-8 are already reshaping that render. **NO new "must merge when near" rule** — `:378`'s merge rule stands.
**RECOMMEND.** **Cost:** one preflight field, one PHASE 8 sentence, the PHASE 0 field list.
**Counter-argument, recorded:** **the handoff's headroom rule — at B's 2 KB headroom the next append must merge instead of add — stretches the time between consolidations.** Recorded, not adopted: "an existing entry covers it" is a judgement call, and the zero-escape-hatch rule forbids building one into a gate.

### D9 — Post-write entry check: the hard form of 131 D14 (F4)

**Proposal:** a new verb, `verify_helper check-memory-entry --entry-file <path> --section "<## heading>"`, run in PHASE 7 ONLY when an entry was written; the skip-silently case makes 0 calls. The orchestrator writes the entry text to `$WORKDIR/memory-entry.md` (a new scratch file in the `:32` list). The verb confirms: the entry text occurs exactly once in `memory.md`; it sits inside the chosen section, which also catches the `## Task Outcomes` misplacement `:390` warns about; its length ≤ the ceiling; 131 D14's stamp is present; it has no positional reference. JSON `{ok, violations[], census}` — the census is post-write, for D8 — with exit 0 on any completed check and non-zero only when the check could not run. On violations the orchestrator rewrites ITS OWN entry once and re-runs; a second failure is reported in the PHASE 8 line. The verdict is never touched (PHASE 7 never revises it, `:378`).
**Bounds, recorded.** **(1)** Clean path: one added call; violation path: two — 128 F10's "at most one helper call per command" is exceeded by one there. **(2)** The stamp clause keys on 131 D14 AS RATIFIED; if D14 is declined or amended, it is re-derived at 132's Phase 0 close or cut, and the rest of D9 stands. **(3)** The evidence is the 2.0 data point (797 / 1,705-char entries), whose PHASE 7 prose predates today's text (`## Origin & evidence`).
**RECOMMEND.** **Cost:** one verb, its tests, the registry pin (F10), PHASE 7 prose.
**Counter-argument, recorded:** **the next run's census catches the same defects one feature later, at zero extra calls.**

### D10 — Where the regrowth rule lives

**Proposal:** in PHASE 7 (D8, D9 and 131 D14's prose), the template's header comment (fresh installs) and the consolidated file's header comment (existing installs, D6). **Not in `src/CLAUDE.md`:** an always-on line costs every session, readers do not need the budget, and 128's *"No `src/CLAUDE.md` edit"* (`:388`) points the same way. The command LISTING that OQ-9 forces into `src/CLAUDE.md` (F11) and the one-clause writer correction at `:314` (F5) are truth maintenance of existing statements, not a budget rule — the distinction 131 D13 draws for the same non-goal.
**RECOMMEND.** **Cost:** none beyond D6, D8 and D9.
**Counter-argument, recorded:** **the handoff states the rule in three places including CLAUDE.md, and the runtime-debugger writer (F5) never reads PHASE 7.**

### D11 — runtime-debugger's write clause: retarget it (F5)

**Proposal:** `runtime-debugger.md:66` drops *"and write concise notes on error patterns and fixes back to `.devforge/memory.md`"* for a clause that reports error patterns and fixes in the agent's output instead. The only task-level record `/devforge:implement` writes is `mark-complete --notes` (F5), and nothing guarantees the patterns reach it. One writer, one shape check.
**RECOMMEND.** **Cost:** one agent sentence.
**Counter-argument, recorded:** **PHASE 7 does not read Completion Notes today (F5), so a runtime pattern reaches memory only if verification surfaces it again.** The alternative keeps the write and gives it 131 D14's shape plus the three-bucket rule.

### D12 — Whole-file readers stay; record them in `FINDINGS.md` (F2)

**Proposal:** the five prose read paths and the agent read lines are unchanged in 132. A new `FINDINGS.md` entry (no plan, no owner) records that per task, the orchestrator pre-flight, the agent-brief read and each dispatched agent's read line can each read the whole file, and that the multiplier is unmeasured.
**RECOMMEND.** **Cost:** one ledger entry.
**Counter-argument, recorded:** **routing agents through the excerpt would cut reads more than any budget** — but it changes 20 agent files and plan 79 D7's ratified KEEP, which this plan must not re-decide.

### D13 — Coordination record with 128 and 131

**Proposal:** 132 edits neither plan; it OFFERS their ratifiers clauses. **(a)** 128 F7 / D9 (b) and 131 F15: "the read side is bounded" → "the helper-verb reads are line-bounded; whole-file reads are not (132 F2, F3)". **(b)** 128 D9 (b)'s `FINDINGS.md` entry may name plan 132 as its owner. **(c)** 131 D14's *"at most two lines"* may read "one physical line" (D6) — or 132's D6 treats D14's two lines as display lines. If 128 D9 (b)'s entry exists when 132 builds, Phase 6 replaces it with a pointer to this plan or amends it in place (F13), per this decision's outcome.
**RECOMMEND.** **Cost:** ledger text.
**Counter-argument, recorded:** **offering clauses to two open plans couples three Phase 0 closes**; a ratifier who declines leaves 132's F-list citing their wording as the thing it corrects.

### D14 — Per-user auto-memory: OUT

**Proposal:** Claude Code's own per-user memory directory is not git-tracked and is neither shipped nor read by the framework. The handoff's auto-memory budget stays consumer-side.
**RECOMMEND.** **Cost:** none.
**Counter-argument, recorded:** **the handoff budgets the operator's per-user memory too (its auto-memory section)**, so a project-only budget leaves that part of the handoff's method unbuilt.

### D15 — Queue position

**Proposal:** 132 builds after every lower-numbered plan that is not done — on 2026-10-05 that includes 128 and 131 (Phase 0 OPEN) and stub 124 — in numeric order, no jump.
**RECOMMEND no jump.** **Cost:** consumer memory files keep growing until the queue reaches 132.
**Counter-argument, recorded:** **growth is shipped and compounding (B doubled in 17 days), and plan 125's D5 is the precedent for a ratified jump.** Under the 2026-10-05 directive the jumpable unit is Phases 1–3 — the census, the helper and the command, which carry the method; a census-only slice would ship a measure with no remedy (OQ-6). The maintainer decides.

### OQ-1 — The command's name, and a measure-only lane

**RECOMMEND `consolidate-memory`** — `/devforge:consolidate-memory`, helper `consolidate_memory_helper`, package `_consolidate_memory/` (the mapping `memory_lane.py` expects, F10), verb-noun like `report-bug`. **Alternatives:** `memory` — rejected-leaning, because it may be confused with Claude Code's own built-in `/memory` command; that is a CLAIM to verify through the claude-code-guide agent at build, not a verified fact here — and `tidy-memory`. **Also RECOMMEND a `--census` flag** that prints the census and stops (D2 step 1).

### OQ-2 — Budget values

The handoff's 40,000 bytes / 80 entries / 600-char ceiling were chosen by one operator in two 1.x installs; 2.0's possible per-task read multiplier (F2, D12) could argue lower. **RECOMMEND the handoff's values, as named constants (D7), revisitable.**

### OQ-3 — The archive: in the tree or git-only

**RECOMMEND in the tree** (D4). **Alternative:** git-only — the ledger cites `git show <sha>:.devforge/memory.md` line numbers, and a squash or rewrite of that commit breaks the citation.

### OQ-4 — Does the command commit?

**RECOMMEND commit**, via the existing `artifact_helper commit-artifacts --paths …` with `.devforge/memory.md` and the consolidation directory — it never runs `git add -A` (F6). **Bound, recorded:** its message is always `[WIP] <label>` (F6), so on a feature branch the consolidation commit folds into that feature's `/devforge:finalize` squash, and on a trunk branch it stays a `[WIP]` commit. **Alternative:** leave the result uncommitted and print the exact `git commit -- <paths>` line for the user.

### OQ-5 — D3's branch check: local only, or also remotes?

**RECOMMEND local branches only** (`--branches`). **Alternative:** add `--remotes`, which sees pushed teammate branches but also refuses on any remote-tracking branch whose memory commits HEAD cannot reach — including branches already merged by squash, whose original commits HEAD never contains.

### OQ-6 — One plan or two

**RECOMMEND one plan; the command is the core and is not cut** — the 2026-10-05 directive. **Counter-argument, recorded and NOT adopted (citing the directive):** ship the census and the verify line first (D7–D9), collect 2.0 growth data, then decide whether the command is needed — 2.0 evidence today is n = 1 feature.

### OQ-7 — Ledger format

**RECOMMEND TSV** — reviewable in a git diff; the helper is its only parser and replaces tabs and newlines in the 100-char field. **Alternative:** JSON.

### OQ-8 — The command's memory-lane disposition

Rule 2 or Rule 3 binds the command the moment it joins `_PROMOTED` (F10). **RECOMMEND `READS`:** the command does read memory, and `preflight` calls `read_memory_context(` (D3's one read) and emits `memory_state`, which `main.md` names at D3's first precondition — the read-performed and read-named halves Rule 2 checks. **Alternative:** `N/A`, with no `memory_state` / `memory_excerpt` token anywhere in its helper package or surfaces (Rule 3); it misdescribes the one command whose job is the whole file. Either way the counts F11 lists move (13/8 → 14/8 under `READS`; 21 → 22).

### OQ-9 — Human-typed only, or model-invocable?

**RECOMMEND human-typed only** (`disable-model-invocation: true`, D2): the command rewrites a project-owned file under one approval, and the model should name it, never start it. **Cost, verified in the tree (F11):** `src/CLAUDE.md:47` and `:78` say "Four", and `:78` says that section is the only place the model sees what a human-typed command does — so both sentences change and the command gets a Command Details entry; `README.md:57`, repo `CLAUDE.md:34`, `storage-rules.md:123` and `memory_lane.py:69`–`:79` restate the split. **Alternative:** model-invocable — `:47` and `:78` keep "Four", but the command still needs a Standalone entry, and the model may propose a whole-file rewrite on its own.

### Phase 0 close record

**OPEN — nothing ratified.** No decision and no open question above has an outcome, and **no build phase may start.** ⚠ **Nothing is built and nothing is measured.**

When the record closes, it is written in the shape of plan 125's close record (`125-VERIFY-FILE-BUGS-IMPORT-PLAN.md`, `### Phase 0 close record`): the occasion; the directive, with any non-English directive given in English translation; the pick-or-delegation classification per `98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md`'s D1 distinction; and an outcomes table.

#### Verify

- The record names **each** of D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13, D14, D15, OQ-1, OQ-2, OQ-3, OQ-4, OQ-5, OQ-6, OQ-7, OQ-8 and OQ-9 **by name, never against a range**, each with an explicit outcome (ratified / amended / declined).
- **D2's outcome names the write form:** direct rewrite (the proposal) or draft-then-install (the alternative).
- **D5's and D9's outcomes state the stamp clause against 131 D14's recorded outcome** — kept, re-derived or cut.
- **D9's outcome states its consequence for D8:** ratified — the PHASE 8 line reads D9's post-write census when an entry was written; declined — the line always reads the preflight census.
- **D11's outcome states its consequence for Phase 3's `src/CLAUDE.md:314` clause:** retarget — `/devforge:verify` as the writer, `/devforge:consolidate-memory` as the only rewriter; declined — the same, plus runtime-debugger as a second writer.
- **D13's outcome names, for 128 D9 (b)'s entry, pointer or amend-in-place.**
- **D15's outcome states jump or no jump**, and on a jump names the phases.
- **OQ-1's outcome names the command**; every `consolidate-memory` / `consolidate_memory` occurrence in this plan is rewritten to it before any build.
- **OQ-8's outcome names `READS` or `N/A`; OQ-9's names human-typed only or model-invocable.**
- **Each outcome states whether it is an explicit maintainer pick or a delegation.**
- **Every counter-argument, Bound line and Alternative above is still present, unshortened.** Phase 0's lead-in *"Nothing below is ratified."* stays as written, with a dated parenthetical beside it naming the close.

---

## Phases

Phase 0 is the section above; **nothing below starts before its close record exists.** **Build order: Phase 1 → 2 → 3 → 4 → 5 → 6.** Phases 1–3 build the command and its measurement engine — the core deliverable; Phase 4 adds the regrowth guard, which names the command and so lands after it exists; Phase 5 edits the template and the second writer; Phase 6 records everything. Every phase builds only what its decisions' ratified outcomes name. D1, D10, D14 and D15 build nothing themselves; D10's rule is carried by Phase 3 (the rewrite brief's header comment for existing installs, D6), Phase 4 (D8, D9) and Phase 5 (the template's header comment for fresh installs, D6).

**House rules for every phase.**
- Python edits route **python-engineer → python-reviewer**, and markdown edits route **instruction-author → instruction-reviewer**; each loop runs until its review is clean.
- Every helper function gets its own test, written AND run in the same turn; tests round-trip through the real producers (D7's parser on the real template, the helper's verbs chained over temp git repositories), never hand-authored imitations of their output.
- Exact test output is read via `rtk proxy` plus a file redirect, never from the display (Trap 4).
- Commits name their paths (`git commit -m … -- <paths>`), never `git add -A`; briefed agents never run `git add`, `git rm` or `git stash`. Subjects take the `<type>(plan-132): Phase N — …` form (the HEAD subject on 2026-10-05 read `docs(plan-111): Phase 4 — …`). After each commit, `git show --stat` lists only that phase's files and this plan.

### Phase 1 — `_shared/memory.py`: the census (D7, OQ-2)

**Route: python-engineer → python-reviewer.**

#### Deliverables

- **`src/devforge/lib/_shared/memory.py`** — the per-line comment classifier factored out of `_scan_lines` (one state machine, F9); the public entry parser and its spans; the public entries accessor `read_memory_entries(workspace_root)` returning `None` or `{"bytes": int, "text": str, "entries": [span, ...]}`; the private `_read_lines_and_size(path)` (text-mode read plus `os.fstat` size on the same handle); `memory_census(lines, file_bytes)`; the named budget constants; the opt-in `census=True` keyword on `read_memory_context`, its docstring naming the opt-in key and its `None` / dict shapes (D7).
- **`tests/lib/_shared/test_memory.py`** — new cases: the real template → 0 entries, `within`; a multi-line HTML comment; `## Task Outcomes` entries counted; an over-ceiling entry; byte-identical and first-80-char duplicates; positional references; HARD versus COUNT-ONLY markers; missing, unknown and duplicate headings; a CRLF file, asserting that the census and `read_memory_entries`' `bytes` equal `os.path.getsize` of the file, that `_read_lines_and_size`' lines equal `_read_lines` on the same file, and that each span's `bytes` is the `\n`-normalised figure; preamble text; multi-line entries; `excerpt_fits` true at 120 content lines and false at 121; each span field on a fixture with known lines; `read_memory_entries` returning `None` on an absent file and a dict with exactly the keys `bytes`, `text` and `entries` on a present one; `read_memory_context(..., census=True)` returning the same `present`, `memory_state` and `excerpt` as the default call on the same CRLF file; and `read_memory_context(..., census=True)` on an absent file (`census` is `None`), on the real template (`census` is a dict with 0 entries and verdict `within`) and on a populated file (`census` is a dict whose `entries` matches the fixture).
- **This plan** — `#### Phase 1 record` below.

#### Verify

- Every populated line belongs to exactly one entry (a test asserts the entries' line spans cover the populated lines exactly once).
- **`_render_excerpt` is untouched:** `git diff` shows no change inside its body; every pre-existing `TestRenderExcerpt`, `TestScanLines` and `TestProbeMemoryState` case is unchanged and green.
- `TestReadMemoryContext.test_absent`'s exact-dict assertion is unchanged and green — the census key appears only when requested.
- `python3 -m pytest tests/lib/_shared -q` is green, then `python3 -m pytest tests/lib -q`; `tests/lib/test_memory_lane.py` is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 1 record

**NOT STARTED.**

### Phase 2 — The consolidation helper (D2–D5, OQ-3, OQ-5, OQ-7, OQ-8)

**Route: python-engineer → python-reviewer.**

#### Deliverables

- **`src/devforge/lib/_consolidate_memory/`** (`__init__.py`, `_cli.py` and whatever modules the build splits out) and the launcher pair **`src/devforge/lib/consolidate_memory_helper`** + **`consolidate_memory_helper.py`**, mirroring `report_bug_helper` (F10). Verbs: `census`, `preflight`, `baseline`, `index-new`, `verify`; every count imports D7's parser and census, and every read of the memory file goes through a `memory.py` accessor (D7). `verify` writes `<workdir>/census-after.json` on exit 0 (D5).
- **`tests/lib/_consolidate_memory/`** — a round trip on a temp git repository through the real verbs (`preflight` → `baseline` → a filled ledger → a rewrite → `index-new` → `verify` exit 0); one failing-case test per D3 precondition — the non-UTF-8 one included — and per D5 gate, the readable gate included (non-UTF-8 bytes in the rewritten file make `verify` report that gate with D3's UTF-8 string, exit non-zero, and raise no traceback); `census` tests: exit 2 plus the exact string on a non-UTF-8 file and on an absent file, exit 0 with 0 entries and verdict `within` on a stub; a ledger field holding a tab and a newline round-trips sanitized (OQ-7).
- **This plan** — `#### Phase 2 record` below.

#### Verify

- The helper's only subprocess calls are `git`; no count is taken by a shell tool (D2): a grep of the package for `subprocess` finds only `git` argument lists.
- `baseline`'s archive is byte-identical to `git show HEAD:.devforge/memory.md`, and `provenance` comes from one `git blame --porcelain` call (a test counts the calls).
- `preflight` reads the file exactly once, through `read_memory_context(` with `census=True` (D3), and emits `memory_state` and the census from that one read; a grep of the package finds no `probe_memory_state(`, `read_memory_excerpt(` or `memory_present(` call. Under OQ-8 = `N/A`, neither `memory_state` nor `memory_excerpt` appears anywhere in the package or the command's surfaces (Rule 3), and this item is rewritten to that outcome before the build.
- **`census-after.json`:** after `verify` exit 0, `<workdir>/census-after.json` parses and its `entries` equals the number of DATA rows in `new-entries-index.tsv` (the header row excluded); a failing `verify` on a fresh workdir leaves no `census-after.json`.
- **Exact reason strings:** a test makes `.devforge/memory.md` dirty in a temp git repository, runs `preflight`, and asserts exit 2 and a stderr equal to D3's uncommitted-file string plus a single newline, byte for byte — backticks and em dash included; further tests assert the same of D3's UTF-8 string (through `preflight` and through `census`), of its `absent` string (through `preflight` and through `census`) and of its `stub` string (through `preflight`); the unquoted reasons (not tracked, branch, `wip.md`) are pinned by their own tests to the wording the build fixes.
- **No path literal:** `git grep -n --untracked '\.devforge/memory\.md' -- src/devforge/lib/_consolidate_memory/ src/devforge/lib/consolidate_memory_helper.py src/devforge/lib/consolidate_memory_helper` prints nothing — zero hits, docstrings and comments included, so they name the file through `MEMORY_RELATIVE_PATH` or as "the memory file" (D7). `--untracked` makes the grep see the new files before they are committed. No grep for `open(` is required: the helper opens its ledger, index and archive.
- `python3 -m pytest tests/lib/_consolidate_memory -q` is green, then `python3 -m pytest tests/lib -q`.
- python-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 2 record

**NOT STARTED.**

### Phase 3 — The command (D2, D4, D6, OQ-1, OQ-4, OQ-8, OQ-9)

**Route: instruction-author → instruction-reviewer for the command files, `src/CLAUDE.md` and `storage-rules.md`; python-engineer → python-reviewer for `claude.py`, `memory_lane.py`, `_segment.py` and the tests.**

#### Deliverables

- **`src/commands/consolidate-memory/main.md`** — frontmatter, then the method in D2's order (measure → audit → target structure → execute with ledger + verbatim archive → gates → regrowth guard), including D2's counting sentence verbatim; **`references/rewrite-brief.md`** (D6); **`references/ledger-contract.md`** (D4, D5).
- **Frontmatter verified through the claude-code-guide agent BY PAGE and SECTION with a verbatim quote** (repo rule): `disable-model-invocation`, `argument-hint`, `allowed-tools`; and OQ-1's `/memory` claim if that name is in play.
- **`scripts/emitters/claude.py`** — `_PROMOTED` gains the name. **`scripts/lib/memory_lane.py`** — a `DISPOSITIONS` row per OQ-8 and the docstring counts (`:69`–`:79`). **`tests/lib/test_memory_lane.py`** — `:218` and `:548`–`:550` move to 22. **`src/devforge/lib/_profile/_segment.py`** — `HELPER_STEMS` gains the stem; **`tests/lib/_profile/test_segment.py:122`–`:123`** move to 22.
- **`src/CLAUDE.md`** — per OQ-9: `:47`, `:78` and a Command Details entry, plus a Standalone entry at `:71`; and `:314` (F5), a one-clause edit: `memory.md` is written by `/devforge:verify` and rewritten only by `/devforge:consolidate-memory`, under one approval. The runtime-debugger half of that sentence's truth depends on D11's outcome: under D11 retarget it holds once Phase 5 lands; if D11 is declined, the clause names runtime-debugger as a second writer. **`src/devforge/storage-rules.md`** — the D4 row and `:123`'s counts.
- **This plan** — `#### Phase 3 record` below.

#### Verify

- An emit to a scratch target (`python3 scripts/emitters/claude.py --src src --target <scratch>`) writes `.claude/commands/devforge/consolidate-memory.md` and the references under `.devforge/command-refs/consolidate-memory/`.
- `main.md` names the six method steps in D2's order, and D2's counting sentence greps back verbatim.
- `main.md`'s PHASE 3 carries D2 step 3's `revise named rows` rule: a grep of `main.md` finds each of its three clauses — `named rows`, `re-present` (as in "re-presents the same stop") and ``until `approve` or `cancel` ``.
- `main.md`'s PHASE 0 restates no `preflight` reason string and tells the orchestrator to copy the helper's stderr line VERBATIM (D3); a grep of `main.md` for `has uncommitted changes` finds nothing.
- `src/CLAUDE.md:314`'s sentence carries the form D11's outcome names: retarget — `/devforge:verify` as the writer and `/devforge:consolidate-memory` as the only rewriter; declined — the same, plus runtime-debugger as a second writer.
- `tests/lib/test_memory_lane.py` and `scripts/verify-memory-lane.py` pass with the new row; `tests/lib/_profile/test_segment.py` passes at 22.
- **Count sweep:** a grep for every phrasing variant of the command count and split (`21`, `twenty-one`, `Seventeen`, `Four are`, `Four commands`, `13/8`, `13 READS`, `17/4`) across `src/`, `scripts/`, `tests/`, `README.md` and `CLAUDE.md` finds no stale live statement; Phase 6 owns `README.md` and `CLAUDE.md`.
- The claude-code-guide citation (page, section, verbatim quote) is recorded in the Phase 3 record.
- Both reviewers return SHIP-READY, or every finding is fixed.

#### Phase 3 record

**NOT STARTED.**

### Phase 4 — `/devforge:verify` regrowth guard (D8, D9)

**Route: python-engineer → python-reviewer for `_verify/_preflight.py`, `_verify/_cli.py` and the tests; instruction-author → instruction-reviewer for `src/commands/verify/main.md`.**

#### Deliverables

- **`src/devforge/lib/_verify/_preflight.py`** — `memory_census` from the single read (D7's opt-in keyword).
- **`src/devforge/lib/_verify/_cli.py`** — `check-memory-entry`, registered in `_SUBCOMMAND_REGISTRY`; tests, including the registry pin and `test_registry_verb_names` in `tests/lib/_verify/test_preflight.py`.
- **`src/commands/verify/main.md`** — the `memory_census` field in PHASE 7's preflight-field sentence and the `$WORKDIR/preflight.json` bullet; `$WORKDIR/memory-entry.md` in the `$WORKDIR` list; the PHASE 7 call and its rewrite-once rule; the PHASE 8 line.
- **This plan** — `#### Phase 4 record` below.

#### Verify

- The registry pin moves by exactly one from whatever 128 left it at (16 on 2026-10-05; 17 after 128).
- PHASE 7 names `check-memory-entry` exactly once, and PHASE 8's line names `/devforge:consolidate-memory`.
- **No report change:** `git diff` shows no change to `src/devforge/lib/_verify/_report.py` or `verify/references/report-format.md`.
- `check-memory-entry` tests cover: a clean entry; an entry under `## Task Outcomes`; one over the ceiling; a missing stamp; a positional reference; an entry present twice; exit 0 on each completed check.
- `python3 -m pytest tests/lib/_verify -q` is green, then `python3 -m pytest tests/lib -q`; `tests/lib/test_memory_lane.py` is green.
- Both reviewers return SHIP-READY, or every finding is fixed.

#### Phase 4 record

**NOT STARTED.**

### Phase 5 — Template, second writer, installer comments (D6, D10, D11)

**Route: instruction-author → instruction-reviewer for `src/devforge/memory.md`, `src/agents/runtime-debugger.md` and the `install.sh` comments.** The `install.sh` edit is prose in a shell comment with no behaviour change, and no house agent owns shell, so it takes the markdown route — a routing choice this plan makes, not a house rule.

#### Deliverables

- **`src/devforge/memory.md`** — the header comment (budget and shape) ON TOP of whatever 131 D14 landed.
- **`src/agents/runtime-debugger.md`** — D11's clause at `:66`.
- **`install.sh`** — the two comments drop their line count: `:277` *"the 13-line stub"* and `:296` *"the 13-line lessons stub"*. No new count is written, because 131 D14 and this phase both change the template's length and a count would go stale; no behaviour change.
- **This plan** — `#### Phase 5 record` below.

#### Verify

- `test_stub_against_real_shipped_stub_fixture` stays green: the template still probes `stub` with an empty excerpt, and D7's census reports 0 entries, `within`.
- `git grep -n "13-line" install.sh` prints nothing.
- `git grep -n "memory.md" src/agents/runtime-debugger.md` shows the read line and no write clause.
- Both reviewers return SHIP-READY, or every finding is fixed.

#### Phase 5 record

**NOT STARTED.**

### Phase 6 — Ledgers (D12, D13)

**Route: instruction-author → instruction-reviewer.** ⚠ **Ledger edits WAIT until any other session's uncommitted edits to the same files are committed** (Trap 3).

#### Deliverables

- **Repo `CLAUDE.md`** — `:34`'s human-typed list (per OQ-9), a router row for the command, and the persistent-memory row naming the census.
- **`README.md`** — `:57`'s counts and the command lists (on 2026-10-05, `report-ticket` is listed at `:53`, `:89` and `:101`; re-grep).
- **`CHANGELOG.md`** — lines under `## [Unreleased]` only, stating the evidence class and claiming nothing measured. **`DEVELOPMENT-STATUS.md`** and **`PLAN-STATUS-ARCHIVE.md`** — this plan's lines.
- **`FINDINGS.md`** — D12's new entry, numbered after the last present at build time; 128 D9 (b)'s entry, if present, handled per D13's outcome.
- **This plan** — its Status line and `#### Phase 6 record` below.

#### Verify

- The count sweep from Phase 3 run again over `README.md` and `CLAUDE.md` finds no stale statement; released `CHANGELOG.md` blocks and finished plans are untouched (`git diff` shows no line outside `## [Unreleased]`).
- `grep -n "^## " FINDINGS.md` shows D12's entry last.
- The identifier grep over the staged diff — run by whoever holds the installations' identifiers — gets no hit.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 6 record

**NOT STARTED.**

### Consumer e2e — user-driven, NOT run by default

⚠ **The user-driven consumer-install exercise is the repo's deferred final gate; nothing in Phases 1–6 waits on it.** It runs only on the user's direction, and never on a frozen benchmark install.

#### Verify

- `/devforge:consolidate-memory --census` on a consumer install whose memory file exists and is UTF-8 prints a census, exits 0 and writes nothing (`git status` unchanged).
- A full consolidation on a COPY of a consumer install reaches `verify` exit 0; the archive is byte-identical to the start HEAD's file; the ledger's row count equals the old entry count.
- One `/devforge:verify` on a `near` install prints D8's line.
- The outcome is recorded below with no installation identifier.

#### Consumer e2e record

**NOT RUN.**

---

## Non-goals

- **No change to the excerpt** — `_render_excerpt`, the 120-line budget, the denylist and the newest-last cut stay (plan 79; D1's counter-argument).
- **No `## Read first` section and no fifth template section** (D6; 128 D9 (a)).
- **No budget or entry-shape rule in `src/CLAUDE.md`** (D10). The command listing OQ-9 forces and the `:314` writer clause are truth maintenance, not rules.
- **No change to the agents' memory read lines** (D12); runtime-debugger's WRITE clause is the one agent edit (D11).
- **No consolidation inside any regular-pipeline command, and no new stop in the regular pipeline** (D2, D8).
- **No per-user auto-memory handling** (D14).
- **No back-fill of existing installs' memory files by `install.sh` or `update.sh`** — the consolidated file's header comment is the delivery path (F8, D6).
- **No change to `verification.md`** (D8).
- **No backport to `main` or the 1.x line; no release cut; no consumer delivery** — the consumer e2e is user-driven.
- **No re-verification of the handoff's numbers** — they are the handoff's figures (the evidence class).

---

## Context for next session

⚠ **Evidence class: TWO consumer installations on the 1.x command layout (wrapper mode, one operator, one method), measured there by a sibling session with shell tools and NOT re-measurable from this repo; ONE 2.0 data point — one feature in one small install; the 2.0 tree VERIFIED here by grep and read on 2026-10-05; NOTHING built and NOTHING measured by this plan.** ⚠ All line digits drift — **grep the quoted text, never the digits.**

**The one sentence that governs everything here:** **on 2.0 only the helper-verb reads are bounded, and only by lines, so this plan bounds the FILE — through a user-invoked command that carries the memory-hygiene method end to end, a census that measures it, and a verify line that sends the user back to the command when the file regrows.**

### Honest bounds

- **Two 1.x installations, one operator, one method; the 2.0 evidence is one feature in one small install**, and its PHASE 7 prose predates today's text. The handoff's figures do not all reconcile (`## Origin & evidence`); no decision depends on its per-feature token multiplier.
- **If D9 is declined, D8's line lags one run** — it reads the file as it stood before PHASE 7's append (D8).
- **The 2.0 read cost is not measured**, and whether dispatched agents follow their read line is not measured (F2, D12).
- **A non-UTF-8 memory file still raises `UnicodeDecodeError` in every existing helper read** (`_read_lines` catches only `OSError`), `/devforge:verify`'s `census=True` preflight read (D8) included; only the consolidation helper refuses it cleanly (D3, D5), and no existing caller changes.
- **The budget counts on-disk bytes, entry spans count `\n`-normalised bytes** (D7): on a CRLF file a span's `bytes` is smaller than its on-disk size by one byte per line it covers, so span and section figures are never compared with the file figure.
- **The budget values are one operator's choice** (OQ-2).
- **The positional-reference and correction-marker checks are heuristics** (D5 Bound 1, D7).
- **A teammate's unpushed branch is invisible to D3**, and a local branch already merged by squash blocks D3 until it is deleted (D3's Bound).
- **The gates prove shape and bookkeeping, not meaning** (D5's counter-argument); the archive and the PHASE 3 review are the guard.
- **Template comments reach fresh installs only** (F8); existing installs get the rule only through a consolidation's header comment.
- **The stamp clauses depend on 131 D14's outcome** (D5 Bound 2, D9 Bound 2), and D9's violation path exceeds 128 F10's one-call bound by one (D9 Bound 1).
- **132 builds after 128 and 131**, which edit `verify/main.md` PHASE 7 and the template first — every anchor above will have drifted.

### Traps

**Trap 1 — line digits.** 128 and 131 build first and edit `src/commands/verify/main.md` PHASE 7 and `src/devforge/memory.md`. Find text by heading or quote, never by a remembered line.

**Trap 2 — installation identifiers.** This file is tracked in a public repo. "Installation A", "installation B", "the maintainer's 2.0 end-to-end test install" and "a sibling session" — every time, in every commit, record and ledger line.

**Trap 3 — concurrent sessions.** Another session may build in this checkout. Commit by explicit path (`git commit -- <paths>`), brief agents not to `git add` / `git rm` / `git stash`, and hold Phase 6's ledger edits until other sessions' uncommitted edits to those files are committed.

**Trap 4 — shell output is lossy.** Hooks rewrite output (false zeros, truncation). Use `/usr/bin/grep`, `/usr/bin/wc`, `awk` and `git grep -n` (plain grep also hits `.pyc` files that survive a deleted `.py`), take line numbers from `awk` or `/usr/bin/grep -n`, and read full test output via `rtk proxy` plus a file redirect. The same failure is why D2 puts every count in the helper.

**Trap 5 — the exact-dict test.** `TestReadMemoryContext.test_absent` pins `read_memory_context`'s return exactly (F3). The census key is opt-in; a default-on key breaks that test and changes the return every other caller receives.

**Trap 6 — one comment scanner.** `memory.py`'s docstring forbids a second comment-tracking implementation (F9). Factor the state machine; do not copy it.

**Trap 7 — memory-lane Rules 2 and 3.** The disposition OQ-8 picks decides which tokens may appear in the new helper and command files (F10); `memory_census` is not a gate token, but `memory_state` is.

**Trap 8 — count pins.** `test_memory_lane.py` (`:218`, `:548`–`:550`), `test_segment.py` (`:122`–`:123`) and verify's registry pin (`test_preflight.py:728`, after 128) each move once; grep each phrasing variant of a count — the same number is written differently per file — and never edit a released `CHANGELOG.md` block or a finished plan's counts.

**Trap 9 — `[WIP]` commits fold.** `commit-artifacts` always writes `[WIP] <label>` (F6); a consolidation committed on a feature branch is squashed into that feature's commit (OQ-4's Bound).

**Trap 10 — the lossless condition counts blank lines.** `excerpt_fits` is computed by calling `_render_excerpt`, never by `entries ≤ 120` (D1, D7).

**Trap 11 — the verify→finalize window.** PHASE 7's entry is uncommitted until `/devforge:finalize` (F4); D3's uncommitted-file refusal there is intended, not a bug.

**Trap 12 — the frozen benchmark install.** Never run, edit or describe it beyond "a frozen benchmark install".

### File anchors

**EDIT targets — a phase of this plan writes each of these:**

- **Phase 1:** `src/devforge/lib/_shared/memory.py` (`:206` `_scan_lines`, `:217`–`:219`, `:327`, `:499`–`:536` `read_memory_context`); `tests/lib/_shared/test_memory.py` (`:89`, `:558`–`:569`).
- **Phase 2:** `src/devforge/lib/_consolidate_memory/` (new); `src/devforge/lib/consolidate_memory_helper` + `.py` (new); `tests/lib/_consolidate_memory/` (new).
- **Phase 3:** `src/commands/consolidate-memory/` (new); `scripts/emitters/claude.py:57`; `scripts/lib/memory_lane.py` (`:69`–`:79`, `:104`); `tests/lib/test_memory_lane.py` (`:218`, `:548`–`:550`); `src/devforge/lib/_profile/_segment.py:71`; `tests/lib/_profile/test_segment.py:122`–`:123`; `src/CLAUDE.md` (`:47`, `:71`, `:78`, `:314`); `src/devforge/storage-rules.md` (`:104`–`:120`, `:123`).
- **Phase 4:** `src/devforge/lib/_verify/_preflight.py:184`–`:187`; `src/devforge/lib/_verify/_cli.py` (`:1144` `_SUBCOMMAND_REGISTRY`, `:1279`); `tests/lib/_verify/test_preflight.py:728`; `src/commands/verify/main.md` (`:32`–`:49`, `:378`, `:390`, `:392`–`:406`).
- **Phase 5:** `src/devforge/memory.md:1`–`:13`; `src/agents/runtime-debugger.md:66`; `install.sh` (`:277`, `:296`).
- **Phase 6:** `CLAUDE.md:34`; `README.md` (`:53`, `:57`, `:89`, `:101`); `CHANGELOG.md` (`## [Unreleased]`, `:8`); `DEVELOPMENT-STATUS.md`; `PLAN-STATUS-ARCHIVE.md`; `FINDINGS.md`.
- **This plan** — every phase's record and, at Phase 6, the Status line.

**READ-ONLY anchors — no phase of this plan writes any of these:**

- `128-AC-VERIFICATION-COMMAND-GATE-PLAN.md` (`:60`, `:70`, `:148`–`:154`, `:385`–`:388`, `:411`); `131-CONSUMER-LESSONS-TRIAGE-PLAN.md` (`:75`, `:101`, `:329`–`:336`, `:693`) — D13 offers clauses only.
- `79-MEMORY-WINDOW-AND-RECEIPT-PLAN.md` (`:3`, `:371`–`:391`, `:399`–`:410`); `74-MEMORY-LANE-INTEGRITY-PLAN.md:9`; `124-PIPELINE-COST-REDUCTION-PLAN.md` (`:4`, `:24`); `125-VERIFY-FILE-BUGS-IMPORT-PLAN.md` (D5 `:81`, close record `:105`); `98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md` (D1).
- `src/devforge/lib/_shared/memory.py` `_render_excerpt` (`:350`–`:476`) — called by the census, never edited.
- `src/CLAUDE.md` (`:179`, `:217`, `:302`); `src/commands/implement/references/agent-brief.md:12`; `src/commands/specify/main.md:193`–`:195`; `src/agents-AUTHORING.md` (`:79`, `:151`, `:179`); `src/agents/code-reviewer.md:32`; `src/agents/tech-writer.md:310`; `src/commands/breakdown/main.md:306`; `src/commands/implement/main.md` (`:39`, `:282`).
- `src/commands/finalize/main.md` (`:138`, `:166`–`:174`); `src/devforge/lib/_artifact/_cli.py` (`:37`, `:268`).
- `src/manifest.json:39`; `install.sh:309`; `src/devforge/storage-rules.md` (`:106`, `:112`, `:124`); `src/files/devforge.gitignore`; `FINDINGS.md` (`:5`, `## 12.`).
- `scripts/lib/memory_lane.py` (`:255`, `:268`–`:271`, `:301`–`:320`, `:496`–`:506`); `scripts/lib/agent_reachability.py`; `src/commands/configure/main.md:4`; `src/devforge/lib/report_bug_helper` + `report_bug_helper.py`.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation.
2. **Check `### Phase 0 close record` FIRST.** While it reads OPEN, nothing is ratified and no build phase may start.
3. **Read 128's and 131's current Status lines and their D9 / D14 outcomes before closing Phase 0** — D5, D9 and D13 depend on them.
4. **Check the queue position before any build.** Lower-numbered open plans build first unless D15's outcome ratifies a jump.
5. **Re-verify F1–F14 by grepping the quoted text, never the digits.** F1's `DEFAULT_EXCERPT_LINES`, F4's PHASE 7 with no size rule, F5's runtime-debugger write clause and F10's `_PROMOTED` without the command are the checks that each gap is still open.
6. **Route every edit through the house flow** — python-engineer → python-reviewer, instruction-author → instruction-reviewer, each looping until clean — and **commit by explicit path, never `git add -A`.**
7. **Keep the evidence class and the public-repo rule attached** to every summary of this plan.
