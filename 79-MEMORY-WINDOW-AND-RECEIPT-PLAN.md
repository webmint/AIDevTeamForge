# 79 — Memory Window And Receipt Plan

**Status: IN PROGRESS — Phase 0 CLOSED 2026-08-17. D1–D7 and OQ-1–OQ-5 all maintainer-ratified 2026-08-17; dispositions recorded inline below. Phases 1–4.5 BUILT 2026-08-18 — Phase 4.5 ran its YES arm, per OQ-3's ratified `yes`. Phase 5 (`/devforge:implement` digest → context) in progress. Phase 6 (consumer e2e) PENDING — user-driven.**

Branch: `develop-2.0-init`.

This plan document contains no private-client identifiers and is intended to be
**committed normally**, unlike the deliberately-untracked plans 73/74/75.

---

## Problem

`.devforge/memory.md` has two writers and twelve readers. **Every writer writes
to the bottom of the file. Every reader reads the top.** Past roughly 25
accumulated lines the readable window freezes permanently on the shipped stub's
headings plus the oldest task-completion receipts, and no lesson written after
that point is ever visible to any consumer again.

### Verified mechanics

Every row below was confirmed by opening the named file. A future session should
re-check rows 1–5 before building — the plan's whole argument rests on them
composing.

*Line-number caveat:* Phases 3, 4 and 4.5 all edit `src/commands/verify/main.md`,
so row 4's line number shifts once any of them lands. Every row's quoted text is
the durable anchor; the numbers are correct as of the pre-build state.

| # | Fact | Evidence |
|---|------|----------|
| 1 | The shipped stub is 13 lines with four sections — `## Architecture Decisions`, `## Known Pitfalls`, `## What Worked`, `## What Failed` — and **no `## Task Outcomes`** | `src/devforge/memory.md` (whole file) |
| 2 | `_append_under_section`: section **not found ⇒ appended at EOF** (with a blank separator when the file is non-empty); found ⇒ inserted before the next `## ` at the same depth, **or before EOF if the section is last** | `src/devforge/lib/_implement/_cmds_session.py:124-137` (docstring), implementation `:139-164`, pure core `_insert_line_under_section` `:167` |
| 3 | `/devforge:implement` writes one receipt per approved task into `## Task Outcomes` — which, by #1 + #2, is created at EOF and is therefore always the last section, so every receipt lands at EOF | `_cmds_session.py:493-503` (the write block, guarded by `if last_task_number and last_task_title:`), entry built at `:303-318` |
| 4 | `/devforge:verify` PHASE 7 writes feature-level lessons as orchestrator prose: *"use the Write tool to append a short dated entry … append, do not overwrite"* — no helper verb, no section targeting, so also EOF | `src/commands/verify/main.md:334` |
| 5 | The bounded excerpt returns `lines[:40]` — the **first** 40 raw lines, terminators preserved | `src/devforge/lib/_shared/memory.py:310` (`DEFAULT_EXCERPT_LINES = 40`), `read_memory_excerpt` `:314-324` |
| 6 | Eleven consumers reach that excerpt through one function, `read_memory_context` `:348-380` | 11 call sites, listed under *Blast radius* below |
| 7 | The twelfth consumer, `/devforge:implement`, uses `read_memory_digest` — the first **5** non-blank lines | `_implement/_cmds_preflight.py:421`, `_shared/memory.py:311` (`DEFAULT_DIGEST_LINES = 5`), `read_memory_digest` `:327-340` |
| 8 | `probe_memory_state` reports **`populated`** truthfully for a file containing only receipts — `_is_populated_line` skips blanks, headings and whole-line HTML comments, and a receipt bullet is none of those | `_shared/memory.py:166-186`, `:279-297` |
| 9 | All eleven `read_memory_context` consumers read `["present"]` and `["excerpt"]`; five additionally read `[MEMORY_STATE_KEY]`; **none reads any other key** | the eleven call sites, each opened — see *The consumer contract* below |
| 10 | The existing test suite PINS the current positional semantics **in assertions**, not merely in prose: `TestReadMemoryExcerpt` pins `DEFAULT_EXCERPT_LINES == 40` outright (`:448-449`), the `readlines()` reference shape (`:475-487`), and an exact newline count at `n=40` (`:463-473`); and two `assertEqual(combined["excerpt"], read_memory_excerpt(root))` calls pin context-equals-excerpt (`:636` in a fixture loop, `:643` in the absent case) | `tests/lib/_shared/test_memory.py:443-493` (the excerpt class), `:636`, `:643`; the module docstring at `:20-28` describes them but is not the pin |

### The arithmetic

The stub occupies 13 lines. `_append_under_section` adds a blank separator plus
the `## Task Outcomes` heading. That leaves roughly **25 lines of readable
headroom**, which `/devforge:implement` consumes at **one line per approved
task**, with content carrying no lesson at all:

```
- **[Task 001 / 001-widget-catalog]**: Define types — completed. _(Task 001)_
```

So the receipt writer evicts the lesson writer. On any project past its first
couple of features, all eleven excerpt consumers receive the stub preamble plus
the oldest receipts, and `/devforge:verify`'s feature-level lessons — the only
lesson-shaped content the pipeline produces — sit permanently below the window,
moving further from it with every task.

### The clincher

`src/commands/implement/references/agent-brief.md:12` **already documents this
exact failure for the 5-line digest**:

> the shipped stub's own first 5 non-blank lines are its headings and HTML
> comments — so on any memory file whose entries were APPENDED below that
> preamble (which is how both writers add them …), the digest is that preamble
> and carries no lesson at all

and routes `/devforge:implement`'s agent brief around it with a direct file
read. **The identical arithmetic at n=40 was never generalized.** It takes ~25
more lines to bite, which is why it survived.

### The second-order effect D2 and D3 do not close on their own

Facts #2, #3 and #4 compose into a consequence that changes how D3, OQ-3 and
OQ-4 must be decided, and it is not visible from any one of them:

**On any install where `/devforge:implement` has completed at least one task,
`/devforge:verify`'s feature-level lessons are textually inside
`## Task Outcomes`.** `## Task Outcomes` is created at EOF and is therefore the
file's last section (#2 + #3); `/devforge:verify` appends at EOF and names no
section (#4); so its dated entry lands after the last receipt, which is inside
that section.

Three consequences:

1. **A D3 exclusion of `## Task Outcomes` — by denylist (Option A) or by
   omission from an allowlist (Option B) — would drop the very lessons this plan
   exists to surface** on every install that ran tasks before the fix. D2 stops
   new receipts; it does not move the lessons already filed under that heading.
2. **On a fresh install after D2, the same mechanic mis-buckets rather than
   excludes.** With no receipt writer, `## Task Outcomes` is never created, so
   the file's last section is `## What Failed` (fact #1) and an EOF append lands
   inside it. The lesson is then INCLUDED — the plan works — but rendered under
   a heading that can contradict it, and D1's whole reason for preserving
   headings is that the reader learns which bucket a lesson came from. A
   correctly-surfaced lesson filed under the wrong bucket is a smaller defect
   than an invisible one, and it is still a defect this plan created the
   conditions for.
3. **OQ-3 is therefore not cosmetic.** Giving `/devforge:verify` section
   discipline is what decouples its lessons from the excluded heading going
   forward AND what stops consequence 2; OQ-4 (back-fill) is what would address
   the ones already filed under `## Task Outcomes`. The two questions are one
   decision surface, not two independent ones.

*Residual, stated honestly:* fact #4 records that `/devforge:verify`'s
instruction says "append" without naming a position. EOF is the reading this
plan assumes and is what "append, do not overwrite" means. An orchestrator that
inserted elsewhere would not produce this layout. Phase 6's e2e is where the
assumption is checked against a real install; the plan does not treat it as
proven before then.

### Why plan 74's gate did not catch it

Plan 74 fixed the *plumbing* (dead path, unfalsifiable gate, seven orphaned
payloads, a live install-clobber data-loss bug) and its checker states its own
non-coverage explicitly at `scripts/lib/memory_lane.py:39-65`: it verifies that
a read happens and that a surface names the field, **not** that the consumption
is substantive or that the content is useful. A window returning the stub
preamble satisfies every rule the gate enforces. This plan is the content half
of the same defect and does not reopen any plan-74 decision. (Fact #8's
probe/excerpt divergence is the mechanism; D6 owns it.)

---

## Blast radius

### The eleven `read_memory_context` call sites

All inherit the fix from one function, which is precisely the payoff of plan
74's consolidation into `_shared/memory.py`:

```
src/devforge/lib/_discover/_cmds_core.py:127
src/devforge/lib/_research/_cmds_basic.py:141
src/devforge/lib/_review/_preflight.py:174
src/devforge/lib/_fix/_preflight.py:179
src/devforge/lib/_grill/_preflight.py:193
src/devforge/lib/_verify/_preflight.py:182
src/devforge/lib/_finalize/_preflight.py:346
src/devforge/lib/_audit/_preflight.py:389
src/devforge/lib/_pr_review/_cli.py:567
src/devforge/lib/plan_helper.py:2347
src/devforge/lib/breakdown_helper.py:3549
```

### The consumer contract

Each of the eleven was opened. They take exactly two shapes, and **no call site
reads a key other than `"present"`, `"excerpt"`, and `MEMORY_STATE_KEY`.** This
is the contract Phase 1 must hold.

**Shape A — dedicated read-memory verb, emits all three keys as JSON (5 sites):**
`_research/_cmds_basic.py:141-146`, `_discover/_cmds_core.py:127-132`,
`_pr_review/_cli.py:567-573`, `plan_helper.py:2347-2353`,
`breakdown_helper.py:3549-3555`. Each maps `mem_ctx["present"]` →
`memory_present`, `mem_ctx["excerpt"]` → `memory_excerpt`,
`mem_ctx[MEMORY_STATE_KEY]` → `memory_state`.

**Shape B — preflight fold; reads `present` + `excerpt` only, never touches
`MEMORY_STATE_KEY` (6 sites):** `_review/_preflight.py:174-176`,
`_fix/_preflight.py:179-181`, `_grill/_preflight.py:193-195`,
`_verify/_preflight.py:182-184`, `_finalize/_preflight.py:346-348`,
`_audit/_preflight.py:389-391`. Each assigns into a larger result dict with
`result["memory_present"] = mem_ctx["present"]` and
`result["memory_excerpt"] = mem_ctx["excerpt"]`.

5 + 6 = 11.

**One `read_memory_digest` call site:** `_implement/_cmds_preflight.py:421`,
which passes a local `DIGEST_LINES` rather than the module default, and emits
the value under the JSON key `memory_digest` (`_cmds_preflight.py:26-27`,
`:424-432`).

**The other three read primitives, enumerated (2026-08-17):**

- `read_memory_excerpt` — **zero** direct production callers outside
  `_shared/memory.py`; the only callers are in `tests/`. All eleven excerpt
  consumers really do route through `read_memory_context`, so Phase 1's rewrite
  of `read_memory_excerpt` has test-only blast radius.
- `probe_memory_state` — exactly **one** production caller,
  `src/devforge/lib/_specify/_cmds_phase01.py:145`, which is plan 74's
  falsifiable `/devforge:specify` gate. **D6 exists to protect that call site**;
  it is the concrete thing "the probe is not touched" is protecting.
- `memory_present` — **zero** direct production callers outside `_shared`.

Phase 1 Step 1.0 re-runs this sweep rather than trusting it, because the counts
are a point-in-time fact about a tree that keeps moving — but the plan is built
on the answers above, not on an unknown.

### The stale-claim surface

`grep -rn "first 40" src/` returns **32 hits, of which 30 are memory-related**
(measured 2026-08-17). Every one of the 30 becomes false the moment Phase 1's
semantics change. They span **three classes**, and a sweep scoped to command
specs reaches only the first:

| Class | Count | Where |
|---|---|---|
| Command specs | 16 | eleven files under `src/commands/` — `research` ×2, `discover` ×2, `plan` ×2, `breakdown` ×2, `pr-review` ×2, and one each in `grill`, `verify`, `audit`, `review`, `fix`, `finalize` |
| Helper docstrings | 13 | `plan_helper.py` ×2, `breakdown_helper.py` ×2, `_pr_review/_cli.py` ×2, and one each in `_verify/_preflight.py`, `_review/_preflight.py`, `_research/_cmds_basic.py`, `_grill/_preflight.py`, `_fix/_preflight.py`, `_finalize/_preflight.py`, `_discover/_cmds_core.py` |
| **argparse `help=` text** | 1 | `plan_helper.py:2504` — **user-facing terminal output**, reached by no docs sweep and no command-spec sweep |

16 + 13 + 1 = 30. The `src/devforge/lib/` share is **14** across ten files
(`plan_helper.py` carries three of them: two docstrings plus the argparse
string). Note `_audit/_preflight.py` is a `read_memory_context` consumer but
carries no "first 40" claim — consumer list and stale-claim list are not the
same set.

The third class is the one worth naming separately: a `--help` string is read by
a human at a terminal, not by a model reading a spec, so it survives every
review that scopes itself to `.md` files. It is the reason **Phase 3's sweep is
over `src/`, not `src/commands/`, and not `src/**/*.md`.**

**Two hits are FALSE POSITIVES. Do not "fix" them:**

```
src/devforge/lib/_constitute/_forcing_functions/_design_tokens/_scanner.py:617   # first 40 chars of selector
src/devforge/lib/_pr_review/_dispatch.py:36                                     first 40K + marker + last 40K   (the diff cap)
```

Neither concerns `.devforge/memory.md`. They are why Phase 3's Verify criterion
targets **two** surviving hits rather than zero.

**A stale claim the grep will NOT find.** `/devforge:verify` PHASE 7 says:
*"When `memory_present` is false, or the excerpt holds only the shipped stub's
headings with no entries under them, there is nothing to reconcile against."*
After Phase 1 the excerpt can never hold the stub's headings — a stub returns
`""`. That clause is dead, and no "first 40" grep matches it. Phase 3 owns it by
quoted text.

### Untouched

`probe_memory_state` and `MEMORY_RELATIVE_PATH` semantics (D6), so
`/devforge:specify`'s falsifiable Phase-1 gate (plan 74) is unaffected. The
gate does an exact string comparison against `MEMORY_RELATIVE_PATH`, which is
why that literal is pinned as a forward-slash constant
(`_shared/memory.py:118-130`) and why this plan does not go near it.

---

## Decisions

### D1 — Section-aware read, replacing the positional slice *(maintainer-ratified 2026-08-17)*

`read_memory_context` returns section-selected text rather than `lines[:40]`:
parse `## ` sections, drop excluded ones, drop empty ones, preserve headings so
the reader knows which bucket a lesson came from.

*Counter-argument, recorded:* a tail slice (`lines[-40:]`) is a one-line change
that all eleven consumers inherit with no parsing code. It was rejected because
it hands the reader a mid-section fragment with no heading context and receipts
would still fill most of it — it moves the window without fixing what is in it.

### D2 — `/devforge:implement` stops writing per-task receipts *(maintainer-ratified 2026-08-17)*

Delete the memory-write block at `_cmds_session.py:493-503`. Receipts are
session-state material and `.devforge/session-state.md` already tracks the last
three tasks.

*This contradicts `src/CLAUDE.md:296`*, which designates `.devforge/memory.md`
as the history home ("**Not a history log** — history lives in task completion
notes (`specs/`) and `.devforge/memory.md`"). That sentence is reconciled in
Phase 4. The maintainer ratified the contradiction knowingly; a future session
must not "restore" the receipt writer on the strength of the old sentence.

*Retained, deliberately:* `/devforge:implement`'s **read** stays
(`_cmds_preflight.py:421`). Removing the write does not affect plan 74's gate,
which classifies commands by what they read — verified: the gate's
read-detection regex at `scripts/lib/memory_lane.py:258-261` matches only
`read_memory_context`, `read_memory_excerpt`, `read_memory_digest`,
`probe_memory_state` and `memory_present` followed by `(`. `MEMORY_RELATIVE_PATH`
is not in that set, so deleting its import from `_cmds_session.py:83` is
gate-neutral, and `implement`'s satisfying read lives in a different module of
the same package.

### D3 — Exclusion is a named denylist, not a heuristic *(ratified 2026-08-17 — Option A)*

*Disposition:* Option A — module-level denylist constant excluding
`## Task Outcomes`, unknown sections included by default; ratified because a
denylist's failure mode is visible noise while an allowlist's is the silent loss
this plan exists to fix.

**Option A (recommended) — module-level denylist constant.** It names the
excluded sections (`## Task Outcomes` at minimum). An unknown section is
**included** by default, so a future writer's content is never silently dropped.
The failure mode of a denylist here is noise; the failure mode of an allowlist
is invisible loss, which is the defect this plan exists to fix.

**Option B — allowlist of the four stub sections.** Output is bounded and
predictable; anything a future writer invents is dropped without a trace.

*Counter-argument to the recommendation:* a denylist cannot exclude a section
nobody anticipated, so a future writer that starts appending high-volume
low-value content re-creates this bug and needs a constant edit to fix. That is
a one-line change made after a visible symptom, versus a silent loss that
produces no symptom at all — which is why the recommendation stands.

**Decide this together with OQ-3 and OQ-4.** Per *The second-order effect* above,
excluding `## Task Outcomes` also excludes `/devforge:verify`'s lessons on every
install that ran tasks before the fix. Option A closes the forward case and
leaves the historical case to OQ-4; neither option closes both alone.

### D4 — Truncation is declared, never silent *(ratified 2026-08-17 — Option A)*

*Disposition:* ratified as written — truncation always carries an explicit
marker.

When the budget drops content, the returned text carries an explicit marker
naming what was dropped. A reader must always be able to tell **"nothing
recorded"** from **"recorded, not shown"** — the same three-state discipline
plan 75 built into its history sweep (`absent` / swept-and-empty / populated)
and plan 53 into its NOT-COVERED verdict.

**Sub-question — where the marker lives.**

*Resolved:* Option A — the marker lives inside the `excerpt` string at the point
of the drop, because that is the only placement that reaches all eleven
consumers with zero call-site changes.

**Option A (recommended) — inside the `excerpt` string, at the point of the
drop.** The consumer that must know about the truncation is the model reading
the excerpt, and text inside the excerpt reaches it with zero call-site changes.

**Option B — an additive dict key** (e.g. `"truncated"`). Machine-readable and
type-clean, but it reaches no reader until all eleven consumers are taught to
surface it — which is exactly the orphaned-payload defect plan 74's gate exists
to catch (`scripts/lib/memory_lane.py:9-12`). Adding the key without wiring
eleven surfaces produces a field nobody reads.

*Counter-argument to Option A:* a marker embedded in prose is unparseable by any
future mechanical check, so a gate that wanted to assert "truncation was
declared" would have to string-match. Option A accepts that; the plan builds no
such gate.

### D5 — Recency wins within a section *(ratified 2026-08-17)*

*Disposition:* ratified as written — newest entries win within a section,
uniformly across buckets; D4's marker makes any resulting drop visible.

When a section exceeds budget, keep the newest entries. Both writers append, so
newest is last. A lesson recorded yesterday outranks one from feature 001.

*Counter-argument, recorded:* `## Architecture Decisions` is the one bucket
where the oldest entry is plausibly the most load-bearing — a foundational
decision does not decay. Recency-within-section applies one rule to all buckets
and will drop such an entry once that section is over budget. The alternative
(per-section ordering policy) adds a second constant and a second thing to get
wrong; the recommendation accepts the uniform rule, and D4's marker is what
makes the drop visible rather than silent.

### D6 — `probe_memory_state` is not touched *(confirmed 2026-08-17)*

*Disposition:* confirmed — the probe and `/devforge:specify`'s gate stay exactly
as plan 74 shipped them, and the post-Phase-1 probe/read divergence is accepted
as correct.

Its three states, and `/devforge:specify`'s gate built on them, stay exactly as
plan 74 shipped them. This plan changes what a *read* returns, never what a
*probe* reports.

*Note for the ratifier:* after Phase 1 the probe and the read can legitimately
disagree — a receipts-only file probes `populated` (fact #8) while its excerpt is
empty (every section is either excluded or content-free). That divergence is
correct and intended: the probe answers "does this file carry any content", the
read answers "does this file carry any content a consumer should act on". D6
confirms that the divergence is accepted rather than treated as a defect to
reconcile.

### D7 — `/devforge:implement` migrates from digest to context *(ratified 2026-08-17 — migrate, keep the selection paragraph)*

*Disposition:* yes — `/devforge:implement` moves to `read_memory_context`;
`agent-brief.md`'s direct-file-read workaround paragraph is KEPT because its
stated reason is selection (the orchestrator picks entries bearing on this
task's `touched_files`), and only the now-false digest-emptiness sentence inside
it is removed.

Once the excerpt carries real lessons, `/devforge:implement` should consume it
like the other eleven. Per the ratified Disposition, `agent-brief.md:12`'s
direct-file-read workaround paragraph is KEPT for its selection rationale; only
the now-false digest-emptiness sentence inside it is removed, alongside deleting
the `read_memory_digest` call site itself (OQ-2).

*Counter-argument, recorded:* the workaround is not purely a digest artifact.
Its stated reason is SELECTION — the orchestrator holds the task contract and
picks the entries bearing on this task's `touched_files`, which a bounded read
cannot do. A section-aware excerpt fixes the emptiness but not the selection, so
deleting the paragraph outright trades a working mechanism for a cheaper one.
The ratifier decides whether the excerpt is good enough to replace selection or
whether only the digest sentence inside that paragraph is removed.

**Separable:** this is Phase 5 and can be cut without affecting Phases 1–4.

---

## Open questions

- **OQ-1 — Budget unit and size.** *Resolved:* a LINE budget of 120 lines total
  (3× the old positional window), chosen because the receipts that motivated a
  tight bound are gone under D2 and D4's marker covers overflow. Lines, bytes,
  or entries? The current 40-line figure was a positional bound; a section-aware
  read wants an entry or byte budget. *Recommendation:* a line budget large
  enough to carry several features' lessons (the receipts that motivated a tight
  bound are gone under D2), with D4's marker covering overflow.
  *Counter-argument:* a line budget bounds nothing on a file whose entries are
  long paragraphs, which is what `/devforge:verify`'s prose writer produces; a
  byte budget bounds the actual context cost but produces a mid-word cut that
  D5's newest-first selection then has to reason about. Whichever unit is
  picked, Phase 1's over-budget test is written against it.

  **Sub-question — how the budget is allocated across sections.** *Resolved:*
  Option B — an equal per-section share of the 120-line budget across retained
  sections, with unused share redistributed in file order to over-budget
  sections in a single pass, so no section starves another and D4's marker fires
  per section. D5 fixes the ordering *within* a section and says nothing about
  which section gives way first. Phase 1 cannot be built without the answer.
  - *Option A — one global budget, consumed in file order.* Simplest. Its
    failure mode is starvation: `## Architecture Decisions` is first in the stub
    (fact #1), so a large one consumes the whole budget and `## What Failed`
    renders empty while holding content — which reads to the consumer exactly
    like a section with nothing in it.
  - *Option B (recommended) — a per-section share, with unused share
    redistributed.* No section starves another, and D4's marker fires per
    section so the reader sees which bucket was cut. Costs one more rule.
  - *Counter-argument to B:* the output then depends on how many sections
    exist, so adding a section silently shrinks every other section's share — a
    change with no visible cause. Option A's starvation is at least positional
    and explainable from the file's own order.

- **OQ-2 — Does `read_memory_digest` survive Phase 5?** *Resolved:* delete
  `read_memory_digest` once Phase 5's migration lands, removing its name from
  `scripts/lib/memory_lane.py`'s `_MEMORY_READ_CALL_RE` alternation in the same
  commit as the function. If D7 lands and `/devforge:implement` moves to
  `read_memory_context`, the digest has no caller. *Recommendation:* delete it
  rather than leave an uncalled bounded read as a trap for the next reader.
  *Counter-argument:* it is exported public surface named in
  `_shared/memory.py:26`'s docstring, and deleting it means editing that
  docstring, the digest tests, and — the touchpoint that matters — the plan-74
  gate. Retaining it costs nothing at runtime. Note the two are not symmetric:
  an uncalled function is discoverable by any future reader, whereas the defect
  this plan fixes was invisible.

  **The gate touchpoint, stated explicitly because it is easy to miss.**
  `scripts/lib/memory_lane.py:259-260` hardcodes a regex alternation over all
  five memory function names, and that regex is what drives `_helper_performs_read`
  — the rule certifying that a READS command actually reads. Deleting
  `read_memory_digest` without editing the regex leaves **the gate that certifies
  this entire lane carrying a dead function name**. It would not fail; it would
  simply match one thing that can no longer exist. That is the same class of
  silent staleness plan 74 was built to remove, reintroduced into plan 74's own
  checker. Phase 5's scope lists it as an edit target, not just a grep.

- **OQ-3 — Does `/devforge:verify` gain section discipline?** *Resolved:* YES —
  `/devforge:verify` gains section discipline; Phase 4.5 runs its YES arm (the
  three-bucket rubric with absent-heading creation). It writes prose at EOF with
  no section (fact #4), so its lessons land in whatever section happens to be
  last. Per *The second-order effect* that is `## Task Outcomes` on every install
  that ran tasks before the fix (where a D3 denylist excludes them), and
  `## What Failed` on a fresh install after D2 (where they are included under a
  heading that can contradict them). Writing them *into* `## Known Pitfalls` /
  `## What Worked` / `## What Failed` by intent would make the buckets real and
  fix both. *Recommendation:* yes, and it is load-bearing rather than cosmetic —
  it is what makes D3's Option A safe going forward and the only thing that
  addresses the fresh-install mis-bucketing D2 creates.

  **The cost of a `no`, on legacy installs, stated because it is not obvious.**
  On an install that ran tasks before this plan, `## Task Outcomes` exists and
  stays last forever — D2 stops writing to it and OQ-4 declines to migrate it, so
  nothing removes it. Under a `no`, every future `/devforge:verify` lesson on
  that install therefore lands inside it and is excluded, exactly like the
  historical ones. So `no` means **no `/devforge:verify` lesson is ever visible on
  a legacy install, before or after this plan ships**, unless OQ-4's manual
  remedy is applied by hand. Fresh installs are unaffected (they have no
  `## Task Outcomes`, so the lesson lands in `## What Failed` — mis-bucketed but
  visible). This is a consequence to weigh, not an argument that settles the
  question. *Scope note:* the write
  is orchestrator prose, so this is a `main.md` instruction change, not a helper
  change; a helper verb would be a larger decision (a second writer sharing
  `_append_under_section`'s shape) and is not proposed here. **This question has
  an implementing phase: Phase 4.5, which is written with both arms.** A `yes`
  selects its build arm; a `no` selects its record-the-limitation arm. Neither
  answer leaves the question orphaned.

- **OQ-4 — Back-fill.** *Resolved:* NON-GOAL as recommended — no back-fill
  migration; the manual remedy (operator moves entries out of
  `## Task Outcomes`) stays documented here as the middle option. Existing
  consumer installs carry files whose readable window is already ossified, and
  whose `/devforge:verify` lessons already sit under `## Task Outcomes`.
  *Recommendation:* NON-GOAL. The fix is forward-looking; a receipt-stripping
  migration is a separate decision with its own data-loss surface.
  *Counter-argument the ratifier must weigh:* under D3 Option A the historical
  lessons stay excluded forever on those installs, so "forward-looking" means
  the plan's benefit does not reach the installs that motivated it until their
  operators hand-edit the file. A manual remedy (tell the operator to move
  entries out of `## Task Outcomes`) is not a migration and carries no data-loss
  surface; that is the middle option.

- **OQ-5 — Do `--last-task-number` / `--last-task-title` survive Phase 2?**
  *Resolved:* Option A — remove `--last-task-number` / `--last-task-title` and
  the `main.md:282` arguments in the same commit, per the sequencing constraint.
  *(New — surfaced while verifying Phase 2's edit surface.)* Both flags exist
  solely to feed the memory entry: they are parsed at
  `_cmds_session.py:436-437`, used only at `:494-496`, and their `--help` text
  at `:352` and `:358` says "(for memory.md entry)". After D2 they feed nothing.
  `src/commands/implement/main.md:282` passes both on every approved task.
  - *Option A (recommended) — remove the flags and the `main.md:282` argument.*
    No inert CLI surface is left behind, consistent with OQ-2's reasoning about
    the uncalled digest.
  - *Option B — retain them as accepted-and-ignored.* Decouples the Python edit
    from the `main.md` edit.
  - **This is a hard sequencing constraint, not a preference.** Under Option A
    the helper change and the `main.md:282` edit MUST land in the same commit:
    a helper that drops the flags while `main.md` still passes them makes
    argparse exit non-zero on "unrecognized arguments", breaking
    `/devforge:implement` at PHASE 7 step 4 on every approved task. Under
    Option B they can land separately, at the cost of shipping two inert flags.

---

## Phases

### Phase 0 — Ratification *(gate)*

Maintainer confirms D3–D7 and resolves OQ-1–OQ-5, **plus the two sub-questions**
that Phase 1 cannot be built without:

- D4's sub-question — where the truncation marker lives (in the `excerpt`
  string, or as an additive dict key).
- OQ-1's sub-question — how the budget is allocated across sections.

D1 and D2 are already ratified. No `src/` edit before this closes.

Read *The second-order effect* before deciding D3, OQ-3 and OQ-4. They are one
decision surface; ratifying D3 in isolation produces a fix that excludes the
lessons it was built to surface.

**OQ-3's answer selects which arm of Phase 4.5 runs** — a `yes` builds the
section-targeting change, a `no` records the mis-bucketing as an accepted
limitation. There is no answer under which Phase 4.5 is skipped.

Record the disposition inline in this file, under each D and OQ, in the form
plan 74 used: the chosen option plus one sentence of reason.

**Verify:** `grep -n "^### D[3-7] " 79-MEMORY-WINDOW-AND-RECEIPT-PLAN.md`
returns five lines, and each one ends in a recorded disposition instead of the
`(OPEN)` marker it carries today. Every OQ-1–OQ-5 bullet opens with a
`*Resolved:*` sentence naming the chosen option, and the D4 and OQ-1
sub-questions each carry one too. The status line at the top of this file names
the ratification date.

---

### Phase 1 — Section-aware read in the single owner file

Rewrite the bounded-read half of `src/devforge/lib/_shared/memory.py` per
D1/D3/D4/D5. Stdlib only, Python 3.8+ (the module's existing constraint,
`_shared/memory.py:100`). Route through **python-engineer → python-reviewer**.

#### Step 1.0 — Re-check the caller enumeration

The sweep was already run (see *The other three read primitives, enumerated* under
*Blast radius*): `read_memory_excerpt` has zero production callers outside
`_shared/memory.py`, `memory_present` has zero, and `probe_memory_state` has
exactly one — `_specify/_cmds_phase01.py:145`, plan 74's gate, which D6 protects.

Re-run the sweep anyway before editing, because those counts describe a tree that
keeps moving. Any caller found that is not in that list is added to the consumer
contract and treated as a Phase-1 obligation.

**What the answers buy Phase 1:** rewriting `read_memory_excerpt` has
**test-only** production blast radius. That is what makes Step 1.5's
change-both-together requirement cheap rather than risky.

#### Step 1.1 — The return contract (unchanged, load-bearing)

`read_memory_context(workspace_root, ...)` keeps its name and keeps returning a
dict whose keys are exactly:

| Key | Type | Change |
|---|---|---|
| `"present"` | `bool` | **unchanged** — same value, same semantics |
| `MEMORY_STATE_KEY` (the literal `"memory_state"`) | `str`, one of `MEMORY_STATE_ENUM` | **unchanged** — D6 |
| `"excerpt"` | `str` | **content changes; name and type do not** |

Absent/unreadable returns
`{"present": False, MEMORY_STATE_KEY: MEMORY_STATE_ABSENT, "excerpt": ""}` —
byte-identical to today (`_shared/memory.py:365-373`).

No key is renamed, removed, or retyped. Any key D4 Option B would add is
additive. **Because all eleven consumers read only these three keys (fact #9),
holding this contract means Phase 1 requires ZERO call-site edits** — the fix
propagates through the one function, which is the payoff plan 74's consolidation
bought.

The keyword parameter currently named `excerpt_lines` is a line count. If OQ-1
picks a different unit, the parameter is renamed to match the unit and every
caller that passes it positionally or by name is updated in the same commit;
Step 1.0's sweep is what finds them. No caller in the eleven passes it today.

#### Step 1.2 — Behavior per probe state

- **`absent`** — `"excerpt"` is `""`. Unchanged from today.
- **`stub`** — `"excerpt"` is `""`. **This is a deliberate behavior change.**
  Today a stub returns the 13 shipped stub lines. Under D1 every section is
  content-free, so every section is dropped and nothing remains. Four empty
  headings are not content.
- **`populated`** — `"excerpt"` is the rendered section-selected text, per
  Step 1.3. A file whose only populated lines sit in excluded sections renders
  `""` while still probing `populated` — the accepted divergence D6 records.

#### Step 1.3 — The section model

- A **section** begins at a line whose stripped form starts with `## ` and runs
  to the next such line or EOF. This is level-2 only, matching
  `_append_under_section`'s same-depth rule (`_cmds_session.py:124-137`); a
  `### ` line is section CONTENT, not a boundary.
- Text before the first `## ` is **preamble**. The preamble is dropped: it is
  the installer-shipped `# Project Memory` title, identical in every install,
  and carries no lesson.
- A section is **empty** when it contains no line for which
  `_is_populated_line` returns `True`. Reuse that existing predicate
  (`_shared/memory.py:166-186`); do not author a second content predicate. The
  module already states this constraint for its scan at `:200-202` — *"the
  comment-tracking logic must not be duplicated a second time anywhere else in
  this module"* — and a second predicate would be the same defect one level up.
  Empty sections are dropped, heading included.
- **Excluded** sections (D3) are dropped BEFORE the empty check, so an excluded
  section never reaches the budget and never contributes a marker.
- **Fenced code blocks are not tracked.** `_shared/memory.py:63-70` already
  records this as an accepted scope boundary for the content scan, and Phase 1
  inherits that stance rather than diverging. Note that
  `_insert_line_under_section` (`_cmds_session.py:167-177`) DOES track fences —
  that asymmetry is deliberate and about to become moot, since D2 deletes the
  writer. Record the inheritance in the module docstring so a future reader does
  not read it as an oversight.

#### Step 1.4 — Rendering

- Retained sections render in **file order**, not budget order, so a reader
  scanning buckets sees them in the stub's declared order.
- Each retained section renders its `## ` heading line verbatim, then its
  content lines.
- Exactly one blank line separates rendered sections. Output is deterministic
  and pinnable.
- A non-empty result ends with exactly one `\n`. An empty result is `""`, not
  `"\n"`.
- Budget allocation across sections follows whatever OQ-1's sub-question
  ratified. D5 fixes the ordering WITHIN a section; it does not say which
  section loses entries first, and Phase 1 cannot be built without that answer.
- The D4 marker's placement is whatever Phase 0 ratified under D4's
  sub-question. Under Option A the marker is a line inside the rendered text at
  the point of the drop, naming the section and what was dropped.

#### Step 1.5 — `read_memory_excerpt` moves with it

`read_memory_context["excerpt"]` and `read_memory_excerpt()` return the same
string for the same file. That equivalence is pinned by two live assertions —
`assertEqual(combined["excerpt"], read_memory_excerpt(root))` at
`tests/lib/_shared/test_memory.py:636` (inside a multi-fixture `subTest` loop)
and `:643` (the absent case) — so the two functions change together. Changing
one alone fails the existing suite. Both are rewritten in this phase, and per
Step 1.0 the production blast radius of the `read_memory_excerpt` half is zero.

Four existing expectations are retired or re-pinned, never deleted silently.
Each retirement records its reason in the test's docstring:

| Pin | Location | Disposition |
|---|---|---|
| `DEFAULT_EXCERPT_LINES == 40` asserted outright | `test_memory.py:448-449` | Re-pinned to whatever OQ-1 ratified as the budget constant, or deleted if OQ-1 replaces the constant with a different name |
| `readlines()` reference-shape equality at `n=2` | `:475-487` | **Retired** — the positional reference behavior is exactly what D1 removes; replaced by an assertion against section-aware output |
| Exact newline count at `n=40` | `:463-473` | **Retired** — same reason |
| `combined["excerpt"] == read_memory_excerpt(root)` | `:636`, `:643` | **Kept**, re-pinned against the new shared output. This is the assertion that makes the two functions one contract; deleting it would let them silently diverge |

#### Step 1.6 — In-file documentation

The module docstring's *"Bounded reads — byte-identical to existing callers"*
section (`_shared/memory.py:72-86`) asserts the positional shape and its
`default N=40`. It becomes false in this phase and is rewritten in the same
commit. The public-surface list at `:25-32` is updated for whatever the new
signature is.

#### Tests

Repo discipline: every function gets a test that actually runs, with input
shapes matching production. The existing suite's own convention
(`tests/lib/_shared/test_memory.py:3-6`) is **real-fixture discipline** — the
`stub` state is proven against the ACTUAL shipped stub at `src/devforge/memory.md`
read from disk, not a hand-authored approximation. Phase 1's new tests follow it.

Mandatory cases:

1. **Stub-only** — the real `src/devforge/memory.md` read from disk, copied to a
   temp install root. Asserts `excerpt == ""` and `memory_state == "stub"`.
   Four empty headings are not content.
2. **Receipts-only** — the stub plus a `## Task Outcomes` section holding N
   receipt lines. Asserts whatever Phase 0 ratified for an excluded section
   (under D3's recommended Option A: `excerpt == ""`), and
   `memory_state == "populated"` regardless (fact #8 — the divergence D6
   accepts). **Production-shape requirement:** the fixture bytes are produced by
   round-tripping through the real writer — call `_build_memory_entry` +
   `_append_under_section` (`_cmds_session.py:303`, `:124`) against a temp copy
   of the real stub — and the resulting bytes are then pinned as a literal in
   the test file. Pinning the literal is what lets this test survive Phase 2's
   deletion of that writer. A hand-typed approximation of the receipt format
   does not satisfy this case.
3. **Receipts plus a later lesson** — the case-2 file with a
   `/devforge:verify`-shaped dated prose entry appended at EOF, reproducing fact
   #4. Asserts the lesson is present in the excerpt and no receipt line is.
   **This test is the plan's whole thesis in one assertion.** Note it interacts
   with *The second-order effect*: under D3 Option A alone the appended prose
   lands inside `## Task Outcomes` and is excluded, so this fixture must place
   the lesson under a non-excluded heading, and a SECOND fixture placing it at
   bare EOF must assert whatever Phase 0 ratified for that case. Both fixtures
   ship; neither is optional.
4. **Over-budget** — input exceeding whatever OQ-1 ratified, allocated across
   sections per OQ-1's sub-question. Asserts the D4 marker is present in
   whatever placement D4's sub-question ratified, and that the surviving entries
   are the ones D5 ratified (under D5's recommendation: the newest).
5. **Unknown section** — a `## Something Nobody Anticipated` heading with one
   populated line. Asserts whatever Phase 0 ratified for an unnamed section
   (under D3's recommended Option A: included, by the default-include rule;
   under Option B: dropped). This case is the one that DISTINGUISHES D3's two
   options, so it is written after ratification, not before.
6. **Absent** — asserts the exact dict from Step 1.1, unchanged.
7. **Agreement** — `read_memory_context(root)["excerpt"] == read_memory_excerpt(root)`
   across every fixture above.
8. **`probe_memory_state` unchanged** — the same three states for the same three
   fixtures as before the change (D6).

**Verify:**

- `python -m pytest tests/lib/_shared/test_memory.py` passes, with all eight
  case groups present.
- `python -m pytest tests/lib/` passes. This is the falsifiable form of the
  zero-call-site-edit claim: the eleven consumers were not touched, so any
  failure outside `tests/lib/_shared/` means the return contract in Step 1.1
  was not held.
- Case 3's first fixture demonstrates a lesson surviving where a receipt does
  not. A run in which case 3 passes trivially (because the fixture has no
  receipts) does not satisfy this phase.

---

### Phase 2 — Stop the receipt writer

Delete the memory write. Route through **python-engineer → python-reviewer**
for the helper edit AND **instruction-author → instruction-reviewer +
claude-code-guide** for the `src/commands/implement/main.md` edit — that file
ships into `.claude/commands/devforge/implement.md`, so the instruction loop is
mandatory. **This phase is not Python-only.**

#### Step 2.1 — The code deletions

Delete `_cmds_session.py:493-503` (the write block) and `_build_memory_entry`
(`:303-318`).

#### Step 2.2 — Check, do not assume (four named checks)

Each check names the action for each outcome. There is no judgment call.

| # | Check | If it has no other caller | If it has another caller |
|---|---|---|---|
| 1 | `_append_under_section` (`_cmds_session.py:124`) | Delete it and its tests | Leave it; record the surviving caller in the commit message |
| 2 | `_insert_line_under_section` (`:167`) — the pure core, separated per its own docstring so it can be unit-tested without touching the filesystem | Delete it and its tests | Leave it; record the surviving caller |
| 3 | `_build_memory_entry` (`:303`) | Delete it and its tests | Leave it; record the surviving caller |
| 4 | The `from _shared.memory import MEMORY_RELATIVE_PATH` import (`:83`) — used only at `:495` | Delete the import line | Leave it |

Run all four checks with a repo-wide grep for the identifier, including
`tests/`. Check 4 is gate-neutral either way: `scripts/lib/memory_lane.py:258-261`
matches only the five read primitives, and `implement`'s satisfying read is
`read_memory_digest` in `_cmds_preflight.py:421`, a different module of the same
package.

#### Step 2.3 — The CLI flags (per OQ-5)

Under OQ-5 Option A, remove `--last-task-number` and `--last-task-title`
(`_cmds_session.py:348-359`), their locals (`:436-437`), and the arguments in
`src/commands/implement/main.md:282` — **in the same commit**, per OQ-5's
sequencing constraint. Under Option B, retain the flags and rewrite their
`--help` text (`:352`, `:358`) to state that they are accepted and unused.

#### Step 2.4 — The in-file claims that become false

All of these are edited in this phase, not deferred:

```
src/devforge/lib/_implement/_cmds_session.py:3-4     module docstring: "append one line to .devforge/memory.md"
src/devforge/lib/_implement/_cmds_session.py:27-33   algorithm step 5 (the memory insert)
src/devforge/lib/_implement/_cmds_session.py:61-70   design notes: entry-per-task, section behavior, entry format
src/devforge/lib/_implement/_cmds_session.py:352     --last-task-number help: "(for memory.md entry)"
src/devforge/lib/_implement/_cmds_session.py:358     --last-task-title help: "(for memory.md entry)"
src/devforge/lib/_implement/_cmds_session.py:400     cmd_update_session_state docstring: "append a line to memory.md"
src/commands/implement/main.md:38                    "Refreshed .devforge/session-state.md + an appended .devforge/memory.md line per approved task."
src/commands/implement/main.md:279                   step heading "4. Update session-state + memory:"
src/commands/implement/main.md:285                   "and appends one outcome line to .devforge/memory.md"
```

The `main.md:38` site is the one most easily missed: it sits in the command's
own opening summary rather than in PHASE 7's body, so a session that navigates
to the write block and works outward never reaches it. Anchor on the quoted text
above, not on the line number — the three `main.md` edits shift each other.

`src/commands/implement/references/agent-brief.md:12` also names
`/devforge:implement` as one of two writers ("which is how both writers add
them: `/devforge:implement` PHASE 7 appends its per-task outcome line,
`/devforge:verify` PHASE 7 appends its feature-level entry"). That clause
becomes false here. Under D7 the whole paragraph is revisited in Phase 5; the
clause is corrected in THIS phase regardless, because Phase 5 is separable and
may be cut. Leaving a false sentence conditional on a separable later phase is
the failure mode this repo's cross-check rule exists to prevent.

**Verify:**

- `python -m pytest tests/lib/_implement/` passes.
- Run `update-session-state` against a temp install root holding a copy of the
  real `src/devforge/memory.md`; `.devforge/memory.md` is **byte-unchanged**
  before and after (`cmp` exits 0).
- The same run's `.devforge/session-state.md` is byte-identical to the
  pre-change output for the same arguments. Capture the pre-change output before
  editing.
- `grep -rn "memory" src/devforge/lib/_implement/_cmds_session.py` returns only
  lines that are true after the change.
- `python scripts/verify-memory-lane.py` exits 0.
- **Under OQ-5 Option A** (flags removed): `.devforge/lib/implement_helper
  update-session-state --last-task-number 001 ...` exits non-zero with
  "unrecognized arguments", and `grep -n "last-task-number"
  src/commands/implement/main.md` returns nothing.
- **Under OQ-5 Option B** (flags retained, inert) — BOTH bullets, because a flag
  that still parses proves nothing about the help string beside it:
  - The same command exits **0**, and the run leaves `.devforge/memory.md`
    byte-unchanged (the flags are accepted and do nothing).
  - `grep -n "for memory.md entry" src/devforge/lib/_implement/_cmds_session.py`
    returns zero lines — the two help strings were rewritten to say the flags are
    accepted and unused, not left asserting a write that no longer happens.

---

### Phase 3 — Reconcile the stale read-semantics claims

Every sentence asserting the positional window becomes true again. The `.md`
surfaces route through **instruction-author → instruction-reviewer +
claude-code-guide**; the `.py` sites in scope item 2 — docstrings and the
argparse `help=` string alike — route through **python-engineer →
python-reviewer**.

Scope:

1. The **16** "first 40" occurrences across the eleven `src/commands/` files.
2. The **14** occurrences under `src/devforge/lib/` — helper docstrings across
   ten files plus the argparse `help=` string at `plan_helper.py:2504`. These are
   `.py` files and are edited under **python-engineer → python-reviewer**. The
   argparse string is user-facing terminal output; it is in scope for the same
   reason the docstrings are, and it is the one a `.md`-scoped sweep misses.
3. `/devforge:verify` PHASE 7's dead clause — *"or the excerpt holds only the
   shipped stub's headings with no entries under them"* — which no "first 40"
   grep matches. After Phase 1 a stub excerpt is `""`, so the clause is
   rewritten to the empty-excerpt condition. Locate it by the quoted text: this
   phase and Phase 4 both edit that file, so either one's line numbers shift the
   other's.

**Out of scope, and named so nobody edits them:** the two false-positive "first
40" hits in `_design_tokens/_scanner.py` and `_pr_review/_dispatch.py` (see *The
stale-claim surface*). Neither concerns `.devforge/memory.md`.

Each edited sentence describes the section-aware semantics: which sections are
included, that empty and excluded sections are dropped, and that truncation is
declared (D4). **Describe the selection rule; do not restate the budget number
in prose.** Replacing `40` with the new budget figure reproduces this plan's own
defect — a hardcoded number in sixteen files that the next budget change
falsifies in all sixteen at once.

**Verify:**

- `grep -rn "first 40" src/` returns **exactly two lines**, and both are the
  named false positives (`_design_tokens/_scanner.py`, `_pr_review/_dispatch.py`).
  Zero lines means a false positive was edited by mistake; more than two means a
  memory-related occurrence was missed.
- `grep -rn "shipped stub's headings" src/commands/` returns zero lines.
- For each of the eleven command files touched, the replacement sentence names
  the section-aware behavior. Spot-check by reading three of them end to end;
  a diff that only deletes the number without describing the new rule does not
  satisfy this phase.
- `grep -rn "first 40" src/devforge/lib/plan_helper.py` returns **zero** lines.
  This file carried three of the fourteen and no false positive, and one of its
  three is the argparse `help=` string — so it is the single best indicator that
  all three classes were swept rather than only the docstrings.
- `python scripts/verify-memory-lane.py` exits 0 — Rule 2b requires each READS
  command's surfaces to still NAME one of `memory_excerpt` / `memory_digest` /
  `memory_state` (`scripts/lib/memory_lane.py:245`, `:486-490`), and a rewrite
  that drops the token name would fail it.

---

### Phase 4 — Docs reconcile

Route through **instruction-author → instruction-reviewer + claude-code-guide**
for the consumer-facing files.

Named targets:

- `src/CLAUDE.md:296` — the D2 contradiction. `.devforge/memory.md` is no longer
  where per-task history lives.
- `src/CLAUDE.md:169` (*"Pre-flight check (before each task): read
  `constitution.md` and `.devforge/memory.md`"*), `:205` (Always rule 4) and
  `:309` (the References link) — **verified still true after D2**, because
  `/devforge:implement` retains its read. Confirm, do not edit.
- `/devforge:verify` PHASE 7 — the clause *"per-task lessons are already written
  by `/devforge:implement`"*. False after Phase 2. Locate it by the quoted text;
  Phase 3 and Phase 4.5 edit the same file, so its line number shifts.
- `src/devforge/storage-rules.md:105` — the memory READ-lane paragraph, which
  describes "the bounded excerpt/digest reads". Reconcile with Phase 1's
  semantics, and with OQ-2's disposition if the digest is deleted.
- `src/devforge/storage-rules.md:213` — *"implement → updates individual task
  file status + completion notes"*. **Verified: this line makes no memory claim
  and needs no edit.** Recorded so a future session does not re-open it.
- `CHANGELOG.md` — an entry under `## [Unreleased]`.
- This repo's root `CLAUDE.md` plan index — a plan-79 entry.

**Verify:**

- `grep -rn "memory" src/CLAUDE.md` returns only lines true after the change.
- No surviving text in `src/` claims `/devforge:implement` writes memory. Check
  with `grep -rniE "implement.{0,80}(append|write).{0,40}memory\.md" src/` and
  read every hit.
- The root `CLAUDE.md` plan index carries a 79 entry naming the ratified D3–D7
  and OQ-1–OQ-5 dispositions.

---

### Phase 4.5 — `/devforge:verify` section targeting *(conditional on OQ-3; both arms below)*

This phase exists because OQ-3 would otherwise be an **orphaned decision** — a
ratified answer with no consuming surface. No other phase changes WHERE that
write lands: Phase 3 and Phase 4 both edit prose inside the same PHASE 7 block,
but only its *describing* clauses (the stub-headings condition and the
per-task-lessons aside), never the append-at-EOF instruction itself. So without
this phase a `yes` on OQ-3 would change no file and `/devforge:verify` would keep
appending blindly at EOF forever. That is the defect class this plan exists to
close, and it is not permitted to appear inside the plan itself.

Numbered 4.5 rather than renumbering Phases 5–6, because sub-phase numbering is
already established in this repo's plans (plan 01 shipped `Phase 5a` / `5b`) and
renumbering would invalidate every cross-reference in this document. It sits
after Phase 4 because both touch `/devforge:verify` PHASE 7's prose; under the
yes-arm they may be authored in a single instruction-loop pass.

**Exactly one arm runs. Which one is determined by OQ-3's ratified answer.**

#### Arm YES — build the section targeting

Rewrite `/devforge:verify` PHASE 7's write instruction so the lesson is placed
under a named section instead of appended at EOF. Route through
**instruction-author → instruction-reviewer + claude-code-guide** — it ships into
`.claude/commands/devforge/verify.md`.

The rewritten instruction requires all of:

- The orchestrator selects exactly one of three buckets by this rubric. There is
  no EOF-append path, no fourth bucket, and no judgment left undefined:
  - a defect verification CAUGHT → `## What Failed`
  - a technique or approach that WORKED → `## What Worked`
  - a gotcha or near-miss to avoid next time → `## Known Pitfalls`

  When a lesson satisfies more than one line, the FIRST matching line in that
  order wins. A lesson matching none is not written (the existing "skip silently
  when there is nothing feature-level worth recording" path already covers it).
- The write reads the file, locates the chosen heading, and inserts before the
  next `## ` heading at the same depth, or before EOF when the chosen section is
  last — the same placement rule `_append_under_section` documents at
  `_cmds_session.py:124-137`. This is orchestrator prose reproducing that rule,
  **not** a call into that helper: Phase 2 may have deleted it, and the Non-goals
  forbid a helper verb for this writer.
- When the chosen heading is absent from the file, the instruction creates it
  rather than falling back to EOF.

Then update Phase 1's case-3 second fixture (the bare-EOF lesson): its docstring
records that under this arm no NEW lesson lands at bare EOF, so the fixture now
covers the historical case only. The fixture itself is kept — legacy installs
still hold such files.

**Verify (arm YES):**

- `grep -n "append, do not overwrite" src/commands/verify/main.md` returns zero
  lines — that is the exact phrase carrying today's EOF-append instruction.
- The rewritten PHASE 7 names all three candidate buckets.
- The rewritten PHASE 7 states the absent-heading behavior.
- `python scripts/verify-memory-lane.py` exits 0 — `verify` is a READS command
  and its surface must still NAME a memory field (`scripts/lib/memory_lane.py:245`).
- Phase 1's case-3 second fixture still exists, and its docstring now says it
  covers the historical bare-EOF case only (the edit directed above).

#### Arm NO — record the limitation

Make no `src/commands/verify/main.md` write-instruction change. Add to
*Non-goals*, beside OQ-4, an explicit statement carrying **both** halves of the
accepted limitation, with OQ-3's ratification date:

- On an install with no `## Task Outcomes` (one that never ran tasks under the
  old writer), lessons land in `## What Failed` — visible but **mis-bucketed**.
- On an install that DID run tasks, `## Task Outcomes` persists and stays last,
  so lessons land there and are excluded — **no `/devforge:verify` lesson is ever
  visible on such an install**, before or after this plan, absent OQ-4's manual
  remedy. This is the sharper half and the one a reader will not derive
  unaided; see OQ-3's legacy-install note.

**Verify (arm NO):**

- *Non-goals* carries the statement, naming both landing sections, the
  permanently-invisible legacy case, and the ratification date.
- `git diff --stat src/commands/verify/main.md` shows no change from this phase
  (Phases 3 and 4 change it; this arm does not).
- The statement says the mis-bucketing is accepted, not that it is absent. A
  future session must be able to tell a decided limitation from an unnoticed one.

---

### Phase 5 — `/devforge:implement` digest → context *(separable, D7)*

Migrate `_cmds_preflight.py:421` from `read_memory_digest` to
`read_memory_context`, resolve OQ-2, and revisit
`agent-brief.md:12`'s workaround paragraph per D7's ratified scope. Route
through **python-engineer → python-reviewer** for the helper and
**instruction-author → instruction-reviewer + claude-code-guide** for the two
command surfaces.

Coupled surfaces. The first two name the preflight JSON key and move together
with the migration; the third is D7's own subject:

- `_cmds_preflight.py:26-27` (the emitted-JSON docstring) and `:424-432` (the
  result dict) — the key `memory_digest` changes if the migration renames it.
- `src/commands/implement/main.md:103` — lists `memory_digest` in the preflight
  JSON contract the orchestrator reads. A key rename that skips this line leaves
  the orchestrator reading a field the helper no longer emits.
- `src/commands/implement/references/agent-brief.md:12` — the workaround
  paragraph, revisited per D7's ratified scope. Phase 2 already corrected this
  line's separate "both writers" clause; do not re-introduce it.
- **`scripts/lib/memory_lane.py:259-260`** — the five-name alternation inside the
  `_MEMORY_READ_CALL_RE` compile at `:258-261`, which drives
  `_helper_performs_read`. **In scope only when OQ-2 resolves to deleting
  `read_memory_digest`**, in which case the name is removed from the alternation
  in the same commit as the function. This is the maintainer-side gate that
  certifies the whole memory lane; leaving a deleted name in it makes the gate
  itself carry stale text. Note the deletion cannot be detected by running the
  gate — it still exits 0 — so this line is an edit target, not something a
  green run would surface.

**Verify:**

- `python scripts/verify-memory-lane.py` exits 0. Rule 2b is conjunctive: after
  the migration, `/devforge:implement`'s surfaces (`main.md` +
  `references/*.md`) must still NAME one of the three tokens
  (`scripts/lib/memory_lane.py:245`, `:489-490`). If the migration renames the
  key to `memory_excerpt` and the `agent-brief.md:12` paragraph is deleted,
  confirm `grep -rn "memory_excerpt\|memory_digest\|memory_state"
  src/commands/implement/` still returns at least one hit — a green gate here is
  not automatic. *(D7's ratified disposition KEEPS that paragraph, so the
  paragraph-deleted half of this condition is a dead branch. Run the grep after
  the key rename regardless: Phase 5 edits BOTH surfaces that carry a token
  today — `main.md:103`'s key and `agent-brief.md:12`'s digest sentence — so a
  hit is still not automatic.)*
- `python -m pytest tests/lib/_implement/` passes.
- **Under OQ-2 "delete":** `grep -rn "read_memory_digest" src/ tests/ scripts/`
  returns zero lines, including `_shared/memory.py:26`'s public-surface list and
  `scripts/lib/memory_lane.py:258-261`'s regex.
- **Under OQ-2 "keep":** that same grep still returns hits (at minimum
  `_shared/memory.py`'s definition, `scripts/lib/memory_lane.py`'s regex, and the
  digest tests), AND `grep -rn "read_memory_digest" src/devforge/lib/_implement/`
  returns **zero** — the function survives, but this phase's whole point is that
  `/devforge:implement` no longer calls it. A surviving `_implement/` hit means
  the migration did not land.

---

### Phase 6 — Consumer e2e *(user-driven)*

Known-answer anchor: a consumer install past its first feature, where a
`/devforge:verify` lesson is currently below the window. The correct outcome is
known in advance — a lesson is on disk and provably not in any brief today —
which is what makes this a regression anchor rather than an exploratory run.
**Which** lesson serves as the probe is decided at step 3, not step 1; on the
most likely install the historical one cannot serve.

Procedure:

1. In the consumer install, confirm the starting state: `.devforge/memory.md`
   carries a `/devforge:verify` lesson below line 40, and
   `.devforge/lib/plan_helper read-memory` does not return it. (`read-memory` is
   the Shape-A verb name, recorded at `src/devforge/lib/_shared/memory.py:157`
   as belonging to `/plan`, `/breakdown` and `/pr-review`.)
2. Confirm *The second-order effect*'s assumption on real data: check whether
   that lesson sits textually inside `## Task Outcomes`. Record the answer in
   this plan — it is the one part of the argument that rests on an inference
   about orchestrator behavior rather than on code.
3. Deliver the change, then pick the probe lesson by step 2's answer. **The two
   branches are not equivalent and the wrong one produces a false negative:**

   - **OUTSIDE branch** — step 2 found the lesson outside `## Task Outcomes`.
     Re-run the same verb; that lesson is returned.
   - **INSIDE branch** — step 2 found it inside `## Task Outcomes`. **That lesson
     cannot demonstrate the fix and must not be used as the probe.** D3 excludes
     that section and OQ-4 declines to migrate its contents, so its continued
     absence is the ratified design working, not a defect. Instead: run
     `/devforge:verify` on a feature in that install AFTER delivery so a NEW
     feature-level lesson is written, and probe THAT. This is the mandatory
     action for this branch — do not relocate the historical entry as a
     substitute, since that is OQ-4's manual remedy and a separate decision.
     - Under Phase 4.5's **YES** arm the new lesson goes to a named bucket and
       is returned.
     - Under Phase 4.5's **NO** arm it lands in `## Task Outcomes` again (that
       section persists on legacy installs and stays last — see OQ-3's
       legacy-install note), so **no `/devforge:verify` lesson is returnable on
       this install at all**. The anchor then uses a hand-authored entry placed
       under a non-excluded heading, and the run records that verify-written
       lessons remain invisible here as a ratified consequence of OQ-3=no plus
       OQ-4's Non-goal.

4. Run a downstream command and confirm the probe lesson reaches a dispatched
   brief.

**A failure at step 3 under the INSIDE branch is NOT evidence that Phases 1–5
are broken.** It is the expected behavior of the ratified OQ-4 Non-goal, and on
the NO arm also of OQ-3. Diagnose in that order before touching any helper.

**Verify:**

- The probe lesson selected by step 3's branch appears in a dispatched brief,
  quoted.
- Step 2's answer is recorded in this file whichever way it comes out, along
  with which branch step 3 took.
- Record the result in `REGRESSION-ANCHORS.md` — the arithmetic that hid this
  bug at n=40 after it was already documented at n=5 is exactly the recurrence
  an anchor exists to pin. The anchor names the guarding test (Phase 1 case 3)
  alongside the observed behavior, and names the branch, so a later re-run
  compares like with like.

---

## Ordering and separability

| Phases | Relationship |
|---|---|
| 1 + 3 | **LOCKED TOGETHER.** The moment Phase 1 lands, all 30 stale-claim occurrences (16 command specs + 14 under `src/devforge/lib/`, incl. the argparse string) plus `/devforge:verify` PHASE 7's stub-headings clause are false. They ship in the same commit or the same PR — there is no intermediate state in which the shipped instructions describe the shipped behavior. Note this pairing is necessary but NOT sufficient: see *The minimum shippable unit* below. |
| 2 + its `main.md` edits | **LOCKED TOGETHER** under OQ-5 Option A (argparse breaks otherwise — see OQ-5). Separable under Option B. |
| 1 vs 2 | Independent in code — different files, no shared symbol. Phase 1's case-2 test fixture is generated by round-tripping through Phase 2's writer, so **Phase 1's tests are authored while that writer still exists**; the generated bytes are pinned as a literal so the test survives Phase 2. Running Phase 2 first is permitted and costs that convenience. |
| 4 | Follows Phase 2. Its targets are the sentences Phase 2 falsifies. |
| 4.5 | Follows Phase 4 (both touch `/devforge:verify` PHASE 7). Runs under either arm; only the arm changes. Its YES arm is the only thing that stops the post-D2 mis-bucketing. |
| 5 | Separable (D7). Cutting it leaves Phases 1–4.5 whole. |
| 6 | Requires 1 + 2 + 3 landed in a consumer install. |

### The minimum shippable unit is 1 + 2 + 3, not 1 + 3

**Phase 1 + Phase 3 alone does NOT fix the reported defect.** An earlier draft of
this section claimed it did; the claim is false and the trace is short enough to
re-run:

Without D2, `/devforge:implement` keeps writing receipts into `## Task Outcomes`,
so by fact #2 that section stays last forever. `/devforge:verify` appends blindly
at EOF (fact #4), so its lessons keep landing inside it. D3 then drops that
section — Option A by naming it, Option B by omitting it from the allowlist, so
the conclusion does not depend on which option is ratified. The lessons stay
invisible: **the mechanism merely changes from budget-eviction to
section-exclusion, and gets worse**, because a visibly-full window is at least
noticeable while a silent exclusion is not.

What 1 + 3 actually buys: the four original stub sections become readable past
line 40. Since no pipeline command writes to those four, that benefits
hand-authored entries only. It does not restore visibility for
`/devforge:verify`'s lessons, which the *Problem* section identifies as the only
lesson-shaped content the pipeline produces.

So: **1 + 2 + 3 is the minimum unit** — matching what the Phase-6 row above
already required. **4** keeps the docs true. **4.5** decides the bucketing
question either way. **5** is an improvement on top; **6** is the proof.

---

## Non-goals

- Any change to `probe_memory_state` or `/devforge:specify`'s Phase-1 gate (D6).
- Back-filling existing consumer memory files (OQ-4).
- A second memory writer, or a helper verb for `/devforge:verify`'s write. OQ-3
  proposes an instruction change to where that writer aims; giving it a helper
  verb is a larger decision and is not on the table here. Phase 4.5's YES arm
  respects this — it has the orchestrator reproduce the placement rule in prose,
  not call `_append_under_section`, which Phase 2 may have deleted.
- A retrospective/follow-through mechanism. That is the *other* half of the
  finding this plan came from — BMAD's `bmad-retrospective` carries a
  per-item follow-through record checking whether the previous cycle's action
  items actually landed, which we have no analogue for. It is deliberately
  **not** in scope: building follow-through on top of an unreadable window would
  produce entries no consumer can see. Revisit only after Phase 6 passes.

---

## Context for next session

The finding arrived from a review of BMAD-METHOD's agent set (2026-08-17). The
agent-roster comparison was a dead end — BMAD v6 ships five persona shells whose
bodies are activation ritual, against our nineteen dispatch targets — but their
`bmad-retrospective` skill exposed that our memory lane produces lessons nobody
can read.

Two claims made early in that review were **wrong** and are corrected here so
they are not re-derived: (a) `/devforge:implement` is *not* the only writer —
`/devforge:verify` PHASE 7 writes feature-level lessons as orchestrator prose;
and (b) "no stage ever writes a lesson" is false. The defect is not that lessons
are unwritten. It is that they are unreadable.

Seven things were established while developing this plan and should not be
re-derived:

1. **The consumer contract is narrow** — all eleven `read_memory_context`
   consumers read exactly three keys, in two code shapes. Holding those three
   key names and types means zero call-site edits.
2. **The other three read primitives were enumerated** — `read_memory_excerpt`
   and `memory_present` have zero production callers outside `_shared`;
   `probe_memory_state` has exactly one, plan 74's `/devforge:specify` gate at
   `_specify/_cmds_phase01.py:145`. So D6 is protecting one concrete call site,
   and rewriting `read_memory_excerpt` is test-only in production terms.
3. **The existing test suite pins the current semantics in ASSERTIONS**, not in
   the module docstring: `DEFAULT_EXCERPT_LINES == 40` at
   `tests/lib/_shared/test_memory.py:448-449`, the `readlines()` reference shape
   at `:475-487`, an exact newline count at `:463-473`, and — the pin that
   couples the two functions — `assertEqual(combined["excerpt"],
   read_memory_excerpt(root))` at `:636` and `:643`. An earlier revision of this
   plan cited the docstring lines instead; the docstring is description, the
   assertions are the constraint.
4. **The stale-claim surface is 30 memory-related hits across three classes**,
   not sixteen in one: 16 command specs + 14 under `src/devforge/lib/`, the
   latter including an argparse `help=` string at `plan_helper.py:2504` that no
   `.md`-scoped sweep reaches. Two further hits are false positives and are
   named in *The stale-claim surface* so nobody edits them.
5. **Phase 2 is not Python-only** — it edits `src/commands/implement/main.md`,
   which ships into `.claude/`, so it needs the instruction loop as well as the
   python loop. The original draft named no review loop for that phase at all.
6. **The minimum shippable unit is 1 + 2 + 3, not 1 + 3** — an earlier revision
   claimed 1 + 3. Argument in *The minimum shippable unit*.
7. **`/devforge:verify`'s lessons are probably already inside `## Task Outcomes`**
   on any install that ran tasks — the coupling behind D3/OQ-3/OQ-4, and the
   plan's one inference-based claim. Argument in *The second-order effect*;
   checked at Phase 6 step 2.

One structural fix was applied to the plan itself: **OQ-3 had no implementing
phase.** It was described as load-bearing with a recommendation of "yes", yet no
phase edited `/devforge:verify`'s write instruction — so a ratified `yes` would
have changed no file. That is the orphaned-decision defect this plan exists to
close, appearing inside the plan. Phase 4.5 now consumes the answer under both
arms. When adding any further open question here, check it has a consuming
phase before considering it written.

Two things were checked and found NOT to be problems, recorded so nobody
re-opens them:

- Deleting `_cmds_session.py:83`'s `MEMORY_RELATIVE_PATH` import is neutral for
  plan 74's gate (its regex matches only the five read primitives).
- `src/devforge/storage-rules.md:213` and `src/CLAUDE.md:169` / `:205` / `:309`
  survive D2 unedited.

## When resuming work

Read the *Verified mechanics* table first — every row is a `file:line` you can
check in under a minute, and the plan's whole argument rests on rows 1–5
composing. If any row no longer holds, stop and re-derive before building.

Then read *The second-order effect* before touching Phase 0. Ratifying D3
without it produces a fix that excludes the lessons it was built to surface.

Two corrections have already been applied to this plan and must not be undone by
a session that reads only part of it:

- **The minimum shippable unit is 1 + 2 + 3.** If you find yourself concluding
  that Phase 1 + Phase 3 is enough, re-read *The minimum shippable unit* — that
  conclusion was drawn once already and is false.
- **Phase 4.5 runs under either OQ-3 answer.** It is not an optional phase
  gated on a `yes`; a `no` selects its record-the-limitation arm. Skipping it
  entirely re-orphans the decision.
