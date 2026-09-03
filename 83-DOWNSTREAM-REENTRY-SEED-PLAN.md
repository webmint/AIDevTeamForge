# 83 — Downstream Re-entry Seed Plan

**Status: DONE (build) 2026-08-20 — Phases 1–5 shipped (Phase 0 ratification `c453929`; Phases 1+4 `0734697`; Phase 2 `70db52b`; Phase 3 `2ca7b34`; Phase 5 = the docs reconcile this line is part of). Phase 6 consumer e2e is PENDING — a user-driven HARD GATE that has NOT run, so this ships build-verified, NOT consumer-validated. Phase 0 RATIFIED 2026-08-20 — D1–D6 and OQ-1–OQ-6 are all resolved, with MOST recommendations adopted as-is; two entries diverge and are called out so the difference is not read as a rubber stamp: OQ-3 carries one ratified BOUND beyond its recommendation, and OQ-4's third sub-case carries a FRESH disposition because no recommendation existed there (its own text says so, and D4 forces the answer) — read both entries rather than the summary. Each disposition is recorded inline under its own D or OQ, opening with the literal `*Resolved:*` marker.**

Branch: `develop-2.0-init`.

This plan document contains no private-client identifiers and is intended to be
**committed normally**, unlike the deliberately-untracked plans 73/74/75.

---

## Problem

The backward re-entry machinery is built and shipped, and **every producer of it
runs before `/devforge:breakdown`.** `/devforge:grill` and `/devforge:spec-check`
are the only two commands that can emit a `ReEntrySeed`, and both sit in the
design tier. Nothing downstream of `/devforge:plan` can emit one.

So when implementation reveals that the PLAN was wrong — not the code — the
framework diagnoses it correctly and then throws the diagnosis away.
`/devforge:fix` triages the item against a written classification table,
concludes it is a scope change rather than a defect repair, names which item and
why, recommends a fresh `/devforge:specify` → `/devforge:plan` →
`/devforge:breakdown` cycle, and ends the turn. The re-run then re-derives from
scratch what `/devforge:fix` just established, because nothing carried it.

Plan 75's OQ-2 recorded this gap as "structurally inexpressible" and deferred it
to a sibling plan that was never written. **This plan is that sibling.**

### Verified mechanics

Every row was confirmed by opening the named file (2026-08-17). Rows 1, 3, 7, 8
and 10 are the ones the plan's cost argument rests on; re-check those before
building.

| # | Fact | Evidence |
|---|------|----------|
| 1 | `SEED_SOURCES = ("grill", "spec-check")` and `SEED_TARGET_STAGES = ("spec", "discovery", "research", "plan")`. Validation is `_require_in_enum` + `_require_nonempty`, so adding a member is additive **at the schema level** | `src/devforge/lib/_shared/seed_schema.py:52`, `:54`, `:62-71`, `:73-81` |
| 2 | `ReEntrySeed` is a frozen dataclass whose own docstring describes this plan's case verbatim — *"emitted when a defect is proven rooted upstream"*. Required non-empty: `seed_version`, `source`, `feature`, `prior_conclusion`, `invalidating_evidence`, `must_satisfy`, `provenance`; `cycle_count` strict int ≥ 1; `carried_findings` list of str, may be empty | `seed_schema.py:89-121` (fields), `:123-165` (`__post_init__`), `:91` (the docstring line) |
| 3 | **…but the test suite pins both enums by exact value.** `assertEqual(SEED_SOURCES, ("grill", "spec-check"))` and `assertEqual(len(SEED_TARGET_STAGES), 4)`. Adding a member to either turns those red | `tests/lib/_shared/test_seed_schema.py:62`, `:80-81` |
| 4 | **Producer pattern** — each producing helper owns a `write-seed` verb that builds a `ReEntrySeed` and writes it atomically, returning a JSON ack. `/devforge:grill` passes `--target-stage` (all four values, exit 2 on any other); `/devforge:spec-check` fixes `source` and `target_stage` internally | `src/commands/grill/main.md:369-372`; `src/commands/spec-check/main.md:244-247`; `src/devforge/lib/_spec_check/_seed.py:1-37` (*"Mirrors `_grill/_report.py`'s build_seed + write_seed exactly"*, imports `_shared.seed_schema` at `:37`) |
| 5 | **Seeds are verdict-gated at a human gate.** The seed is written only when the user's pick MATCHES the recommended disposition; a cross-pick, Proceed, Kill or Dismiss writes nothing | `grill/main.md:29`, `:357-364`; `spec-check/main.md:35`, `:239` |
| 6 | **Consumer pattern** — glob, match on `target_stage`, parse the flat JSON **inline and helper-free** (deliberately, *"so this block remains valid even if `/devforge:grill` is later removed"*), no-op silently when nothing matches. Neither consumer deletes the seed or touches `cycle_count` | `src/commands/plan/main.md:98-112` (esp. `:100`, `:110`, `:112`); `src/commands/specify/main.md:135-154` (esp. `:137`, `:152`, `:154`) |
| 7 | **The `spec` route is source-agnostic in code.** `/devforge:specify` Phase 0.5 globs `specs/<resolved-dir>/*-seed.json` and matches `target_stage == "spec"` only — it never filters on `source`. The mandatory Phase-0.4 pending gate's arm (b) is implemented the same way: `_has_spec_reentry_seed` globs `*-seed.json` and reads only the top-level `target_stage` key, deliberately not reconstructing the schema | `specify/main.md:104-107` (the gate's two arms), `:137`, `:154`; `src/devforge/lib/_specify/_cmds_handoff.py:920-944` — glob at `:937`, predicate at `:942` |
| 8 | **The `plan` route is NOT source-agnostic.** `/devforge:plan` PHASE 0a.7 globs a hardcoded `specs/*/grill-seed.json`. It is also project-wide, where the `/devforge:specify` consumer explicitly warns against globbing project-wide and scopes to the resolved dir | `plan/main.md:100`, `:112`; contrast `specify/main.md:137` |
| 9 | `/devforge:fix` PHASE 1 is the D7 bounce: it reads `references/triage.md` in full, classifies each working-list item, and on a scope change STOPS — naming the item and why, recommending a fresh `/devforge:specify` cycle — and ends the turn without partially remediating. It emits no seed. Rule 4 restates it | `src/commands/fix/main.md:125-131`, `:267`; classification table `src/commands/fix/references/triage.md:9-14`; the naming duty `:18-24`; mixed lists `:26-33` |
| 10 | **`/devforge:breakdown` has NO `ReEntrySeed` consumer.** All five "seed" occurrences name plan-handoff decomposition seeds, an unrelated concept | `src/commands/breakdown/main.md:59`, `:68`, `:101`, `:139`, `:520` |
| 11 | `_fix/_cli.py` carries a `_SUBCOMMAND_REGISTRY` of four verbs plus a documented three-step extension point for adding one | `src/devforge/lib/_fix/_cli.py:179-185` (the extension comment), `:186-222` (the registry) |
| 12 | `/devforge:fix` is one of the seven human-typed-only commands (`disable-model-invocation: true`); `/devforge:specify` is model-invocable | `src/commands/fix/main.md:5`; `src/CLAUDE.md` Workflow section (the seven-name list) |

**(AMENDED 2026-08-20 — line-anchor drift from plans 81/82; every fact's SUBSTANCE
re-verified and holding.)** Four rows moved and none changed meaning. **Fact 4:**
`spec-check/main.md`'s `write-seed` block is now `:278-281` (was `:244-247`) — plan 82's
edits shifted that file; the same row's `grill/main.md:369-372` anchor is unmoved.
**Fact 5:** `spec-check/main.md`'s verdict-gating is now PHASE 6 at `:269-273` (was
`:239`), and that phase gained a clean-arm no-pick branch (plan 82) which also writes no
seed — fact 5's point holding on a new arm, not a change to it; `grill/main.md`'s gate
arms now sit around `:359-361` (were `:357-364`). **Facts 6 and 8:** `plan/main.md`'s
PHASE 0a.7 block moved `:98-112` → `:100-114` — heading `:100`, the hardcoded
`grill-seed.json` glob at `:102` and `:114` — and its no-op line now hands off to plan
82's new PHASE 0a.8 spec-check preflight rather than straight to the plan work.
**The two sites that name these as EDIT TARGETS — Phase 4's `plan`-route scope bullet
and the `plan` row of the route table below — were CORRECTED IN PLACE to `:102` + `:114`
on 2026-08-20.** The fact-6 and fact-8 rows above keep their as-recorded `:100`, `:112`
anchors, per this file's amend-don't-rewrite convention for *Verified mechanics* rows;
this paragraph is those rows' correction.
**Fact 10:** the five-hit count is now EIGHT (`:59`, `:68`, `:72`, `:101`,
`:139`, `:267`, `:373`, `:520`) — every hit is still a plan-handoff decomposition seed or
an unrelated concept (`:267` database seed data, `:373` a pinned test seed), so the row's
point, that `/devforge:breakdown` has no `ReEntrySeed` consumer, is unchanged. Re-grep
every anchor before use, per this file's own standing rule.

**(AMENDED 2026-09-03 — plan 93.)** Fact 12 is false as of 2026-09-03:
`/devforge:fix` is model-invocable and the human-typed set is the four setup
commands. Fact 12 was cited by D3's counter-argument ("present by construction",
below); that clause weakens to "present by agreement" — the user agreed to the
offer that started the run — and D3's three-arm `AskUserQuestion` is unchanged,
because it never relied on the keystroke, only on the user being in the session.

### What the gap costs

Fact 9 already produces every string the seed needs. `triage.md:18-24` requires
the bounce to name WHICH item and WHY it is a scope change — that is
`prior_conclusion` and `invalidating_evidence` in prose form. The recommended
cycle is `must_satisfy`. The feature is already resolved (`fix/main.md:116`).
**The material exists at the moment of the bounce and is discarded when the turn
ends.** The change is to persist it in the record the pipeline already knows how
to read.

---

## Blast radius

### Zero-cost, one-line, and new-block — the three target routes

This table is the plan's central cost argument. It follows from facts 7, 8 and 10.

| Target stage | Consumer today | Cost to route a NEW source there |
|---|---|---|
| `spec` | `/devforge:specify` Phase 0.5, globbing `*-seed.json`, matching `target_stage` only (fact 7) | **No code change.** The Phase-0.4 pending gate admits it and Phase 0.5 consumes it as-is. Prose only — the sentences that enumerate `source` by name |
| `plan` | `/devforge:plan` PHASE 0a.7, globbing hardcoded `grill-seed.json` (fact 8) | **One glob widened** in `plan/main.md:102` + `:114`, plus prose. No helper change |
| `breakdown` | **none** (fact 10) | A whole new consumer block, plus whatever gate arm makes it reachable — the analogue of the `find-handoffs` arm (b) that exists for `spec` |

### The two test pins that turn red

Fact 3. Both are exact-value assertions, not membership checks, so a Phase-1
build that changes only `seed_schema.py` fails its own suite with no other
mistake made. They are edit targets, not surprises.

### In-file claims that become false when `SEED_SOURCES` grows

```
src/devforge/lib/_shared/seed_schema.py:5-6    module docstring: "(e.g. /grill -> ... , /spec-check -> spec)"
src/devforge/lib/_shared/seed_schema.py:26     "source must be one of SEED_SOURCES ("grill", "spec-check")"
src/devforge/lib/_shared/seed_schema.py:95-96  ReEntrySeed docstring: the same claim
src/commands/specify/main.md:107               gate arm (b): "a /devforge:grill RE-ENTER-UPSTREAM or /devforge:spec-check REVISE-SPEC verdict is asking for this spec to be REVISED"
src/commands/specify/main.md:135               section heading: "Re-entry from /devforge:grill or /devforge:spec-check"
src/commands/specify/main.md:137               "read the seed's source field to know which check fired: /devforge:grill ... or /devforge:spec-check"
src/commands/specify/main.md:139               "which command emitted this seed (grill or spec-check)"
src/commands/specify/main.md:146               "naming the seed's source command (/devforge:grill or /devforge:spec-check)"
src/commands/specify/main.md:154               "both /devforge:grill and /devforge:spec-check are opt-in, and no seed is ever produced unless..."
src/devforge/lib/_specify/_cmds_handoff.py:37-38   "a sibling *-seed.json file (grill-seed.json / spec-check-seed.json)"
```

**(AMENDED 2026-08-19 — one quoted anchor in that list was rewritten and is no longer
greppable as quoted.)** `82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md`'s Phase 6
rewrote the `specify/main.md:154` sentence, because `/devforge:spec-check` is no longer
opt-in (it is user-typed, and `/devforge:plan` blocks until a fresh report exists — the
verdict still never binds). That sentence now reads *"…`/devforge:grill` is opt-in, and
`/devforge:spec-check`, though the user must run it before `/devforge:plan` will proceed,
writes no seed on most runs; no seed is ever produced unless…"*. **The row's POINT is
unchanged** — it is still a `source`-enumerating sentence that a third seed source would
falsify, and it is still an edit target for this plan. The other ten rows are unaffected;
re-grep every anchor before use, per this file's own standing rule.

`_cmds_handoff.py:920-944`'s docstring names the two seed filenames
illustratively; the code globs `*-seed.json` (fact 7), so the code needs no
change and the docstring does.

**This list is NOT certified exhaustive.** It was compiled by opening the files
named in *Verified mechanics*, not by a repo-wide sweep — the drafting session's
`grep` tooling was unavailable. Two rows (`:107`, `:146`) were added by a review
pass after the first draft missed both. Treat a hit not named above as an
omission in this list, not as a new defect.

**Sweep on bare literals. Never on a compound "X or Y" phrase.** The first draft
proposed `grep -rn 'grill or spec-check' src/`. That pattern matches **nothing**
— in both `:107` and `:146` a closing backtick and other words sit between
`grill` and `or` (`` `/devforge:grill` or `/devforge:spec-check` ``,
`` `/devforge:grill` RE-ENTER-UPSTREAM or `/devforge:spec-check` ``). A phrase
pattern is fragile against exactly the markdown these files are written in, and
it is what hid those two rows. An alternation of bare tokens
(`"grill\|spec-check"`) is fine; a phrase spanning a formatting boundary is not.
The sweep is therefore per-file and bare, over the four files named above:

```
grep -n "grill" src/commands/specify/main.md
grep -n "grill" src/commands/plan/main.md
grep -n "grill\|spec-check" src/devforge/lib/_shared/seed_schema.py
grep -n "grill\|spec-check" src/devforge/lib/_specify/_cmds_handoff.py
```

Every hit is read by hand. The review pass counted 7 hits in
`specify/main.md` on 2026-08-17; that figure is a sanity check, not a pass
criterion, and it changes the moment Phase 4 edits the file.

**(2026-08-20 — coordination with plan 85.)**
`85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md` (NOT STARTED) intends to rewrite the
grill-opt-in prose, and `specify/main.md:154` — the row this plan's Phase 4 also
rewrites — is one of the sentences that prose sweep covers, since it is where
`/devforge:grill` is called opt-in. **Coordination rule, the same shape plans 82 and 85
already carry between themselves: whichever of plans 83 and 85 ships SECOND reads the
LIVE sentence and re-derives its rewrite from what it finds — never applies a rewrite
pre-computed against the sentence as quoted above.** The 2026-08-19 amendment is the
standing proof that a pre-computed form goes stale on exactly this row.

### `/devforge:fix`'s own surfaces, if it becomes a producer

```
src/commands/fix/main.md:6-16    allowed-tools list — a write-seed entry (and a commit-artifacts entry) belong here
src/commands/fix/main.md:35      "Its only durable output is the same one /devforge:implement produces per approved task"
src/commands/fix/main.md:125-131 PHASE 1, the bounce itself
src/commands/fix/main.md:270     Rule 7: "Writes only a [WIP] commit ... Its only durable output is the remediation [WIP] commit"
src/CLAUDE.md                    the /devforge:fix Command-Details entry: "bounces to /devforge:specify instead"
```

**`:35` and `:270` are the sharp ones.** A seed file is a second durable output.
Those two sentences become false the moment the first seed is written, and
`/devforge:fix` sets `disable-model-invocation: true` (fact 12), so its
`description` frontmatter is not in model context and the `src/CLAUDE.md` catalog
entry is the model's only awareness source for what the bounce does.

### Untouched

`/devforge:grill` and `/devforge:spec-check` behavior. They are the pattern being
mirrored. Neither producer's verb, gating, seed filename, or consumer contract
changes. The `_shared/` engine is extended by enum membership only.

---

## Decisions

Nothing below is ratified. Each carries a recommendation and the argument
against it.

### D1 — Which command is the source *(RESOLVED 2026-08-20)*

*Resolved:* **Option A** — one new source token `"fix"`, `/devforge:fix` the sole
producer, because it is the only downstream command already performing the
classification the seed carries (fact 9), and the diagnosis-moment-vs-discovery-moment
gap named in the counter-argument below is ACCEPTED for this build rather than answered.

**Option A (recommended) — one new source token `"fix"`, `/devforge:fix` the
sole producer.** It is the only downstream command that already performs the
classification the seed carries (fact 9): a written binary table, a required
naming of which item and why, and a recommended re-entry target. A producer
without that step has nothing grounded to put in `invalidating_evidence`, which
is a required non-empty field (fact 2).

**Option B — `"fix"` and `"implement"`, two tokens, two producers.**

**Option C — one generic token such as `"downstream"`.**

*Counter-argument to the recommendation:* the moment a plan is discovered wrong
is usually DURING `/devforge:implement`, not at `/devforge:fix`.
`/devforge:fix` only ever sees findings `/devforge:review` or `/devforge:verify`
already wrote to disk, plus a single in-window conversational defect
(`fix/main.md:119`, `:121`). A mid-implement realization has no route to
`/devforge:fix` at all until the feature's tasks drain. Option A therefore
covers the diagnosis moment and misses the discovery moment; the ratifier
decides whether that is acceptable for v1.

*Against Option C specifically:* `source` values are per-command today, and
`specify/main.md:139` instructs the consumer to state **which command's** verdict
it is re-entering from. A generic token makes that instruction unanswerable.

### D2 — Does `breakdown` become a fifth target stage? *(RESOLVED 2026-08-20)*

*Resolved:* **Option A** — no `breakdown` target stage in this build; only the two routes
with live consumers ship (`spec`, zero consumer code; `plan`, one widened glob), and the
`breakdown` route — a new consumer block, its reachability gate, AND the three-way triage
discriminator the dependency paragraph below prices — is deferred until an observed
incident justifies that cost. **The `plan`-route glob widening is deliberate consumer
future-proofing** — it also removes fact 8's recorded hardcoded-filename divergence —
**but this build's sole producer emits `target_stage="spec"` only**, since fact 9's
PHASE-1 bounce is a flat binary that always recommends `/devforge:specify`, so the `plan`
route ships UN-EXERCISED and Phase 6, which drives the `spec` route, does not validate
it.

**Option A (recommended for v1) — no.** Ship only target stages that already
have a live consumer. Per the route table above, `spec` costs zero consumer code
and `plan` costs one widened glob; `breakdown` costs a new block plus a
reachability gate.

**Option B — yes, add `breakdown` and write the consumer block.**

*Counter-argument to the recommendation, and it is strong:* the cheapest
correction in the whole pipeline is exactly the one being deferred. When the plan
is right and only the decomposition is wrong — a task boundary in the wrong
place, a contract-chain link missing, an agent assignment wrong — routing to
`spec` re-derives everything upstream of the actual error, which is the waste
this plan exists to remove. Deferring `breakdown` means the framework still
over-corrects for a common case. Weigh the build cost against shipping a
gradation whose cheapest rung is missing.

**Dependency — Option B is NOT consumer-side-only. Read this before ratifying
it.** Choosing Option B also requires a three-way discriminator that does not
exist today. `/devforge:fix`'s PHASE-1 triage is a flat binary — a defect repair
stays, and everything else gets one undifferentiated `/devforge:specify`
recommendation (`fix/main.md:129-131`) — and `references/triage.md:9-14` carries
no rule separating a decomposition-only defect from a design defect. **That
logic is unscoped in Phases 2–4 as written:** Phase 4 states the `breakdown`
route's cost as a new consumer block plus a reachability gate, which is its
consumer-side cost only. Under Option B the discriminator must be added to
**Phase 3's** scope (`references/triage.md` + `fix/main.md` PHASE 1). Shipping
Option B without it makes `"breakdown"` a schema-valid enum member that no
producer path can ever select — the orphaned-target-stage defect this plan
exists to fix, reproduced one level down. Do not design the discriminator here;
this note states the cost, not the mechanism.

*Note for either option:* routing to `plan` inherits fact 8's project-wide glob,
which the `/devforge:specify` consumer explicitly argues against
(`specify/main.md:137`: another feature's stale seed would bind this run). If
`plan` is in scope, decide whether to scope its glob at the same time or record
the divergence.

### D3 — Is the seed verdict-gated at a human gate? *(RESOLVED 2026-08-20)*

*Resolved:* **Option A** — verdict-gated: an `AskUserQuestion` at the PHASE-1 bounce,
with the seed written only on the arm that matches the bounce's own recommendation,
mirroring fact 5 and the orphan-seed lesson plan 39 exists to record.

**Option A (recommended) — yes.** Add an `AskUserQuestion` at the PHASE-1 bounce
and write the seed only on the arm that matches the bounce's own recommendation,
mirroring fact 5.

**Option B — no.** Write the seed unconditionally at the bounce; the user can
decline to re-run `/devforge:specify`.

*Argument for A:* plan 39 exists because an unratified seed becomes an orphan a
later run silently obeys, and the failure mode is identical here —
`specify/main.md:137` instructs the consumer to *"treat it as a binding directive
for this run"*. An unconfirmed seed binds a future run.

*Counter-argument:* PHASE 1 currently ends the turn cleanly (fact 9); adding a
question changes the command's shape, and the user is being asked to ratify a
classification they have no independent basis to judge. `/devforge:fix` is also
human-typed-only (fact 12), so the user is present by construction and the
orphan risk is lower than at `/devforge:grill`, which recommends a disposition
the user can override. An acknowledgement-shaped question may be enough.

*(Amended 2026-09-03 — plan 93: "present by construction" → "present by
agreement"; see the fact-12 amendment above. No mechanism changed.)*

*Sub-question Phase 3 cannot be built without:* the option set. The mixed-list
prose at `triage.md:26-33` already offers two paths (drop the scope item and
re-run on the remainder; take the whole set through `/devforge:specify`), and a
third arm — record nothing and stop — may be needed. AskUserQuestion takes 2–4
options and auto-injects an "Other" row, so an explicit "Other" must not be
authored; the live examples are `src/commands/configure/main.md`'s bulk-confirm
and `src/commands/grill/main.md` PHASE 7.

*Resolved:* **three options, no authored "Other" row** (AskUserQuestion auto-injects
it) — **(1)** write the seed and re-enter via `/devforge:specify`, the matching arm and
the one marked recommended, since it is what the bounce itself already recommends;
**(2)** drop the scope item and re-run `/devforge:fix` on the defect-only remainder,
writing NO seed — `triage.md:26-33`'s first path, carried over verbatim rather than
invented; **(3)** stop and record nothing, writing NO seed. Only option (1) writes.

### D4 — Where the seed file lives and what it is named *(RESOLVED 2026-08-20)*

*Resolved:* **Option A** — `specs/[feature]/fix-seed.json`, matching the
`<source>-seed.json` convention, so `/devforge:specify`'s two glob call-sites (the
Phase-0.4 gate and the Phase-0.5 consumer) see it with no code change;
`/devforge:plan`'s consumer still needs its glob widened per Phase 4, since it globs a
hardcoded filename rather than `*-seed.json` (fact 8). One second-order consequence is
load-bearing and is stated here rather than left to be rediscovered: this fixed
one-file-per-source filename is what mechanically forces OQ-4's third sub-case — the
multi-item bounce — onto its option (i).

**Option A (recommended) — `specs/[feature]/fix-seed.json`**, i.e.
`<source>-seed.json` in the feature dir, matching `grill-seed.json` and
`spec-check-seed.json`.

**Option B — any name outside the `*-seed.json` glob.**

*Argument for A, and it is mechanical rather than aesthetic:* both the
`/devforge:specify` Phase-0.4 gate (`_cmds_handoff.py:937`) and the Phase-0.5
consumer (`specify/main.md:137`) glob `*-seed.json`. A name outside that glob is
invisible to both, so Option B costs two additional changes to buy nothing.

*Counter-argument:* a third `*-seed.json` in one directory makes the consumer's
multi-match rule (`specify/main.md:150` — process ALL, narrate each `source`,
union `carried_findings`) load-bearing for a three-way case it was written for
two. The rule holds as written; the cost is that the enumerating sentences
listed under *Blast radius* need widening now and again for a fourth source.
See OQ-3.

### D5 — Does `/devforge:fix` get its own `write-seed` verb? *(RESOLVED 2026-08-20)*

*Resolved:* **Option A** — a new `src/devforge/lib/_fix/_seed.py` (`build_seed` +
`write_seed`) plus a `write-seed` verb registered through `_fix/_cli.py`'s documented
extension point (fact 11), because helper-owns-shape is what makes
`ReEntrySeed.__post_init__`'s rejection reach the CLI as exit 2 instead of shipping an
invalid directive silently; the thin-caller asymmetry argued below is ACCEPTED as
recorded, not refuted.

**Option A (recommended) — yes.** A new `src/devforge/lib/_fix/_seed.py`
(`build_seed` + `write_seed`) plus a `write-seed` verb appended to
`_fix/_cli.py`'s `_SUBCOMMAND_REGISTRY` via its documented extension point
(fact 11), modelled on `_spec_check/_seed.py`, which is itself a narrowing of
`_grill/_report.py` (fact 4).

**Option B — no verb.** The orchestrator composes the JSON with the Write tool.

*Argument for A:* helper-owns-shape. The seed is a validated record with an
atomic write; an orchestrator-composed file bypasses `ReEntrySeed.__post_init__`
entirely, so an empty required field ships silently instead of exiting 2.

*Counter-argument:* `/devforge:fix`'s stated identity is thin caller, no copied
machinery (`fix/main.md:23`, rule 5 at `:268`) — it calls `implement_helper`
binaries rather than owning them — so a producer module is the first machinery
`_fix/` would own beyond reading. And Option B has one real merit: both
consumers read the seed helper-free **on purpose**, so the block survives the
producer's removal (fact 6); a symmetric helper-free write would make the whole
feature deletable by removing prose. The asymmetry is defensible — a read that
finds nothing is a no-op, whereas a write that produces an invalid record is a
directive a later run obeys — but the ratifier should see the argument rather
than inherit the conclusion.

### D6 — Does scope gradation need its own field? *(RESOLVED 2026-08-20)*

*Resolved:* **Option A** — no `scope_grade` field; `target_stage` carries the gradation
(minor ⇒ no seed, moderate ⇒ the nearest stage that owns the error, major ⇒ `spec`), and
the finer nuance the counter-argument names lives in `must_satisfy` free text.

**Option A (recommended) — no.** `target_stage` carries the gradation:
minor ⇒ no seed (remediate in place), moderate ⇒ the nearest stage that owns the
error, major ⇒ `spec`. This is the only borrowable idea from BMAD-METHOD's
`correct-course` (Minor / Moderate / Major routing), and it maps onto a field
that already exists and is already every consumer's routing key.

**Option B — a new `scope_grade` field on `ReEntrySeed`.**

*Argument for A:* two fields encoding one routing decision create a
contradiction surface — a seed with `scope_grade="minor"` and
`target_stage="spec"` is unresolvable and nothing would reject it. Adding a
required field to a frozen dataclass also means editing both existing producers.

*Counter-argument:* `target_stage` says WHERE to go, not HOW BIG the correction
is, and those differ — a major and a moderate change can both target `spec` while
warranting different treatment. Under Option A that nuance lives in
`must_satisfy` free text. The counter to the counter is that no mechanical check
reads any seed field today; every consumer is prose, so the extra field buys
nothing until a checker exists.

---

## Open questions

- **OQ-1 — Does the bounce still end the turn after writing the seed?**
  *Resolved:* yes — the bounce still ends the turn after writing the seed, stating
  that the seed was written and naming `/devforge:specify` as the next command;
  `/devforge:fix` never runs it unprompted. The recommended re-run cycle the bounce
  names now carries `/devforge:spec-check` between `/devforge:specify` and
  `/devforge:plan` — see Phase 3's scope list for why.
  *Recommendation:* yes — state that the seed was written and name
  `/devforge:specify` as the next command. `/devforge:specify` is model-invocable
  (fact 12), so the model may run it once the user agrees; `/devforge:fix` must
  not run it unprompted. *Counter-argument:* a seed written and then not
  consumed for days is the orphan D3 is trying to prevent, and offering the
  re-run immediately narrows that window.

- **OQ-2 — What `cycle_count` does a `/devforge:fix` seed carry, and does it
  participate in any loop cap?**
  *Resolved:* carry `1` unless this run itself re-entered from a prior seed, and add
  no cap logic — matching both existing producers.
  `/devforge:grill` enforces a bounded-loop
  escalation after two cycles (`grill/main.md:361`), but nothing in the `spec`
  consumer reads `cycle_count` today (fact 6). *Recommendation:* carry `1`
  unless this run itself re-entered from a prior seed, matching both existing
  producers, and add no cap logic. *Counter-argument:* a fix → specify → plan →
  implement → fix loop is exactly the compounding the field was added to bound,
  and this is the producer most likely to create one.

- **OQ-3 — Should the consumer prose stop enumerating `source` by name?**
  *Resolved:* yes, with ONE bound — the enumerating sentences are rewritten to READ
  the `source` field, and exactly one site (the `source`-field bullet at
  `specify/main.md:139`) keeps an illustrative value list (`grill`, `spec-check`,
  `fix`) so the consumer can still name which check fired AND Phase 4's positive
  verify criterion — the D1 token appearing inside the Phase 0.5 block — stays
  satisfiable. A fourth source then edits one line, not six.
  The code is already source-agnostic on the `spec` route (fact 7); only the prose
  enumerates. *Recommendation:* rewrite the enumerations to read the field rather
  than list its values, so a fourth source is a schema change alone.
  *Counter-argument:* naming the two commands is what lets the consumer tell the
  user which check fired without the model inventing a description, and a bare
  "read `source`" instruction loses that specificity.

- **OQ-4 — The field mapping, which Phase 2 cannot be built without.**
  *Resolved:* the three sub-cases below each carry their own disposition; every
  other required field maps from material the bounce is already forced to produce —
  `prior_conclusion` from the named item, `must_satisfy` from the recommended cycle
  (`triage.md:18-24`), and `feature` from the already-resolved feature
  (`fix/main.md:116`).
  Which `/devforge:fix` input fills each required field? Three sub-cases have no
  obvious answer and must be settled explicitly:
  - **`provenance` for a case-3 conversational defect.**
    *Resolved:* the literal string
    `conversational (in-window user report; no report file)` — non-empty and
    truthful, and it invents no file.
    It is required
    non-empty (fact 2), and a user-raised in-window defect has no report file on
    disk (`fix/main.md:121`). Every existing seed points at a written report.
  - **`invalidating_evidence` for a scope-change bounce.**
    *Resolved:* when the bounced item carries a written finding
    (`specs/[feature]/review.md` / `specs/[feature]/verification.md`), the field
    MUST quote that finding's own `evidence` string, plus the one-line
    classification reason; the bare classification judgment is permitted ONLY for
    the conversational case, which has no written evidence to quote. This ANSWERS
    the semantic-weakening objection recorded below rather than accepting it.
    Both existing sources
    carry grounded evidence — a quoted grill finding, an unsat core. The
    `/devforge:fix` bounce's evidence is a JUDGMENT against a classification
    table (`triage.md:9-14`). *This is a real semantic weakening of the field and
    is recorded as such rather than hidden:* the ratifier should decide whether
    that is acceptable or whether the field must quote the finding's own
    `evidence` string instead.
  - **Two or more items each independently triggering the bounce.**
    *Resolved:* option **(i)** — ONE seed whose three flat strings synthesize across
    the items, with each item's own reasoning carried in `carried_findings`. It is
    forced mechanically by D4 rather than preferred: the fixed `fix-seed.json` name
    admits exactly one file per source per directory, so option (ii) cannot exist
    under the ratified naming.
    This is NOT
    `triage.md:26-33`'s mixed case (one scope item among defects); it is several
    working-list items that are each a scope change. `prior_conclusion`,
    `invalidating_evidence` and `must_satisfy` are flat single-value strings
    (`seed_schema.py:112-118`) — only `carried_findings` is a list. Three
    options: **(i)** one seed whose three strings synthesize across items, with
    each item's reasoning also carried in `carried_findings`; **(ii)** one seed
    per item — the consumer's multi-match rule (`specify/main.md:150`) already
    handles it, though no producer writes more than one today; **(iii)** refuse
    to seed a multi-item bounce and fall back to today's prose. *No
    recommendation is offered here:* there is no evidence base to prefer one,
    and the failure mode of guessing is specific — a session meeting this in
    Phase 2 without a ratified answer invents a policy on the spot (silently
    dropping all but one item's reasoning, or concatenating) inside an artifact
    `/devforge:specify` treats as a binding directive (`specify/main.md:137`).

- **OQ-5 — Should `/devforge:review` or `/devforge:verify` also be producers?**
  *Resolved:* no — the recommendation below is adopted unchanged, and the answer is
  written down so a later session does not re-derive it.
  *Recommendation:* no — they surface findings and render a verdict, and neither
  performs a scope classification, so neither can fill `invalidating_evidence`
  with anything the other end can act on. Recorded so it is not re-derived.

- **OQ-6 — Should the producer union a sibling seed's `carried_findings`?**
  *Resolved:* no for this build — the consumer's union already covers the same-run
  matches, which is what a producer-side union would duplicate; the cross-cycle
  compounding the counter-argument names is left unaddressed, and recorded as such.
  *Recommendation:* no for v1 — no existing producer reads a sibling seed, and
  the consumer already unions across matches (`specify/main.md:150`).
  *Counter-argument:* the consumer's union only covers seeds that survive to the
  same run, whereas the field's stated purpose is compounding ACROSS cycles —
  *"monotonic compounding"* (`seed_schema.py:107-108`), carried so upstream
  commands can *"detect and cap re-entry loops"* (`:15-16`).

---

## Phases

### Phase 0 — Ratification *(gate)*

Maintainer resolves D1–D6 and OQ-1–OQ-6, **including D3's option-set
sub-question and all three of OQ-4's sub-cases**, which Phases 2 and 3 cannot be built
without. Record each disposition inline under its D or OQ, opening with the
literal marker `*Resolved:*` followed by the chosen option and one sentence of
reason. The literal is what this phase's Verify greps for, so a disposition
recorded without it does not close the gate.

Re-check facts 1, 3, 7, 8 and 10 before ratifying. They are the cost argument,
and every one is a `file:line` checkable in under a minute.

**Verify:**

- `grep -n "^### D[1-6] " 83-DOWNSTREAM-REENTRY-SEED-PLAN.md` returns six lines
  and none of them ends in `*(OPEN)*`.
- Every OQ-1–OQ-6 bullet opens with a `*Resolved:*` sentence naming the chosen
  option; D3's sub-question and each of OQ-4's **three** sub-cases carry one too.
- If D2 was ratified Option B, its scope note is reflected in Phase 3: the
  triage-discriminator work named in D2's dependency paragraph appears in that
  phase's scope list. Ratifying Option B without that edit is the failure the
  dependency paragraph exists to prevent.
- The status line at the top of this file names the ratification date.

---

### Phase 1 — Extend the shared enum

Add the D1 source token to `SEED_SOURCES` (and, under D2 Option B, the
`breakdown` member to `SEED_TARGET_STAGES`) in
`src/devforge/lib/_shared/seed_schema.py`, update the two exact-value test pins,
and rewrite the in-file claims listed under *Blast radius*. Stdlib only, Python
3.8+, matching the module's existing convention (`seed_schema.py:31-34`: explicit
`typing.List`, no PEP 604/585, no `from __future__ import annotations`). Route
through **python-engineer → python-reviewer**.

Open the phase by running the four-command bare-literal sweep specified under
*Blast radius* and reconciling its output against the in-file-claims list there,
which is explicitly not certified exhaustive. The sweep is written out once, in
that section; do not restate the commands here.

**Verify:**

- `python -m pytest tests/lib/_shared/test_seed_schema.py` passes, and the pins
  at `:62` and `:80-81` were UPDATED rather than deleted — the file still
  asserts an exact tuple and an exact length, so a future silent addition still
  fails. A diff that relaxes either to a membership check does not satisfy this
  phase.
- `python -m pytest tests/lib/` passes. This is the falsifiable form of "the two
  existing producers are unaffected": nothing outside `_shared` was touched, so
  any failure elsewhere means the change was not additive.
- `grep -n '"grill", "spec-check"' src/devforge/lib/_shared/seed_schema.py`
  returns zero lines — the constant and all three docstring restatements moved
  together.

---

### Phase 2 — The producer

Build `src/devforge/lib/_fix/_seed.py` (`build_seed` + `write_seed`) and register
a `write-seed` verb in `_fix/_cli.py` per its extension point (fact 11), per D5
and OQ-4's ratified field mapping. Model on `_spec_check/_seed.py`, including its
recorded stance that verdict-gating lives in the command layer, not the module
(`_spec_check/_seed.py:23-26`). Route through **python-engineer →
python-reviewer**.

Repo discipline: every function gets a test that actually runs, with production
input shapes.

Mandatory cases:

1. **Happy path** — writes a file whose JSON `source` is the D1 token and whose
   `target_stage` is the D2-ratified value.
2. **Empty required field** — an empty `--must-satisfy` exits 2, proving the
   schema rejection reaches the CLI rather than being swallowed.
3. **Atomic write** — a re-run overwrites in place, matching both existing
   producers.
4. **The OQ-4 case-3 shape** — the conversational-defect `provenance` value
   ratified in Phase 0 constructs successfully. If Phase 0 chose a value that
   cannot exist for that case, this test is what surfaces it.
5. **The OQ-4 multi-item bounce** — two items each independently a scope change,
   asserted against the option Phase 0 ratified: under **(i)** one file whose
   `carried_findings` carries both items' reasoning; under **(ii)** two files;
   under **(iii)** no file and a non-zero exit. This case exists to make the
   ratified policy mechanical rather than a per-run improvisation.

**Verify:**

- `.devforge/lib/fix_helper --help` lists `write-seed`, and
  `.devforge/lib/fix_helper write-seed --help` exits 0.
- Case 2 above: the run exits 2 and writes no file.
- `python -m pytest tests/lib/_fix/` passes.

---

### Phase 3 — `/devforge:fix` PHASE 1 emits the seed

Rewrite the D7 bounce so it writes the seed (gated per D3) and WIP-commits it via
`artifact_helper commit-artifacts`, mirroring how both existing producers commit
theirs (`grill/main.md:377-380`, `spec-check/main.md:251-257`). Route through
**instruction-author → instruction-reviewer + claude-code-guide** — this file
ships to `.claude/commands/devforge/fix.md`.

Scope, all in `src/commands/fix/main.md`:

- PHASE 1's bounce (`:125-131`) — the seed write, the D3 gate, the commit.
- The recommended re-run cycle the bounce names (`:131`) — it becomes
  `/devforge:specify` → `/devforge:spec-check` → `/devforge:plan` →
  `/devforge:breakdown`. Plan 82 made a fresh, content-hash-matched `spec-check.md`
  a precondition of `/devforge:plan` (its PHASE 0a.8 gate re-hashes `spec.md` and
  compares against the report's recorded `**Spec hash**:` line), and a fix-seeded
  spec revision rewrites `spec.md` — so it stales the prior report BY CONSTRUCTION
  and the old three-command cycle sends the user into a run that blocks.
  `fix/main.md:131` still carries the pre-82 cycle only because plan 82's Phase-6
  sweep did not reach `fix/main.md`.
- The `allowed-tools` list (`:6-16`) — entries for the new `fix_helper` verb and
  for `artifact_helper commit-artifacts`, mirroring the existing entries' shape.
  `allowed-tools` is the current field name and accepts a YAML list
  (https://code.claude.com/docs/en/slash-commands, *Frontmatter reference*,
  fetched 2026-08-17). claude-code-guide confirms the entry, not pattern-matching.
- `## Outputs of this command` (`:35`) and Rule 7 (`:270`) — both assert the WIP
  commit is the ONLY durable output. False once a seed is written; corrected
  here, not deferred.

The bounce must still name WHICH item and WHY (`triage.md:18-24`) — the seed
records that duty's output, it does not replace it.

**Verify:**

- `grep -n "write-seed" src/commands/fix/main.md` returns at least one line
  inside PHASE 1.
- `grep -n "only durable output" src/commands/fix/main.md` returns **zero**
  lines. It returns two today (`:35` and `:270`); both sentences are rewritten
  in this phase, so a surviving hit means one was missed.
- Under D3 Option A: `grep -n "AskUserQuestion" src/commands/fix/main.md`
  returns a line inside PHASE 1. Capture the pre-change output first — today it
  returns lines only in PHASE 6.
- `grep -n "commit-artifacts" src/commands/fix/main.md` returns a line, and the
  matching `allowed-tools` entry exists.
- `grep -n "spec-check" src/commands/fix/main.md` returns a line inside PHASE 1's
  bounce naming the four-command cycle (`/devforge:specify` →
  `/devforge:spec-check` → `/devforge:plan` → `/devforge:breakdown`). It returns
  **zero** lines today (verified 2026-08-20), so every hit is this phase's work
  and a zero-hit result means the cycle rewrite was missed.

---

### Phase 4 — Consumer reconcile

Widen the consumer surfaces for the ratified route(s). Route through
**instruction-author → instruction-reviewer + claude-code-guide**.

- **`spec` route (under a D2 answer that routes there — the route the current
  bounce already recommends):** the source-enumerating sentences at
  `specify/main.md:135`, `:137`, `:139`, `:154`, and the docstring at
  `_cmds_handoff.py:37-38`. **`:139` is the ONE ratified OQ-3 exception:** it is
  rewritten to READ the `source` field but KEEPS an illustrative (`grill`,
  `spec-check`, `fix`) value list, so it is the one site this phase does not
  fully de-enumerate — see the staleness criterion below. **No code change** —
  fact 7 is what makes this prose only. The `.py` docstring routes through
  **python-engineer → python-reviewer**.
- **`plan` route (under a D2 answer that routes there):** widen the glob at
  `plan/main.md:102` and `:114` from `grill-seed.json` to `*-seed.json`, plus
  the surrounding prose.
- **`breakdown` route (under D2 Option B):** a new consumer block plus its
  reachability gate. This is the largest single unit in the plan; do not fold it
  into another phase.

**Verify:**

- **The staleness criterion (fails on a missed enumeration).** Under a ratified
  `spec` route, run `grep -n "spec-check" src/commands/specify/main.md` and read
  **every** hit. A hit that enumerates the sources — "grill … or … spec-check"
  in any markdown form — FAILS this phase, **with ONE ratified exception
  (OQ-3):** `:139` retains an illustrative (`grill`, `spec-check`, `fix`) list,
  which is what keeps the positive criterion below satisfiable. Of the six
  enumerating sites — `:107`, `:135`, `:137`, `:139`, `:146`, `:154` — the FIVE
  that must be fully de-enumerated are therefore `:107`, `:135`, `:137`, `:146`,
  `:154`. A hit naming `spec-check-seed.json` purely as a filename is not an
  enumeration and passes.
- **The positive criterion.** Under a ratified `spec` route,
  `grep -n "<the D1 source token>" src/commands/specify/main.md` returns at least
  one line inside the Phase 0.5 block. The two criteria are not redundant: this
  one fails a phase that deleted the old enumeration without naming the new
  source; the one above fails a phase that named the new source and left an old
  enumeration standing. The first draft carried only this one.
- Under a ratified `spec` route: run `git diff
  src/devforge/lib/_specify/_cmds_handoff.py` and confirm every `+` and `-` line
  begins with `#` or sits inside a `"""` block. Do **not** use `--stat` here: it
  reports per-file counts, not which lines changed, so it cannot produce this
  observable. A non-comment change means fact 7 was misread.
- Under a ratified `plan` route:
  `grep -n "grill-seed.json" src/commands/plan/main.md` returns zero lines.
- `python -m pytest tests/lib/_specify/` passes.

---

### Phase 5 — Docs reconcile

- `src/CLAUDE.md` — the `/devforge:fix` Command-Details entry ("bounces to
  `/devforge:specify` instead"). This is the model's only awareness surface for
  a `disable-model-invocation: true` command (fact 12), so a stale entry here is
  not cosmetic.
- `CHANGELOG.md` — an entry under `## [Unreleased]`.
- The repo-root `CLAUDE.md` plan index — an 83 entry naming the ratified
  dispositions.

**Verify:**

- `grep -n "devforge:fix" src/CLAUDE.md` returns only lines true after the
  change. Read every hit.
- The root `CLAUDE.md` index carries an 83 entry naming the ratified D1–D6 and
  OQ-1–OQ-6 answers.

---

### Phase 6 — Consumer e2e *(user-driven — the standing manual gate)*

Known-answer anchor. The correct outcome is known in advance: a `/devforge:fix`
run whose working list contains a scope-change item today ends the turn and
leaves nothing behind.

Procedure:

1. In a consumer install, drive a feature to a state where `/devforge:review` or
   `/devforge:verify` surfaces a finding that triages as a feature/architecture
   change per `triage.md:9-14`.
2. Confirm the pre-change behavior: `/devforge:fix` bounces and no
   `specs/<feature>/*-seed.json` is written by it.
3. Deliver the change. Re-run `/devforge:fix`; confirm the seed is written (and,
   under D3 Option A, only on the matching pick).
4. Run the target-stage command. Confirm it announces re-entry mode, names the
   `source` as the D1 token, and addresses `must_satisfy` — rather than
   re-deriving.

**Verify:**

- Step 4's command states the seed's `source` and `feature` up front and names
  how the run addresses `must_satisfy`.
- Under a `spec` route, the `/devforge:specify` Phase-0.4 gate admits the
  feature dir with a trailing ` | re-entry` marker (`specify/main.md:109`) — the
  falsifiable proof that fact 7's source-agnostic arm (b) covers the new source
  with no helper change.
- Record the result in `REGRESSION-ANCHORS.md`, naming the guarding test from
  Phase 2 alongside the observed behavior.

---

## Ordering and separability

| Phases | Relationship |
|---|---|
| 1 → 2 | Phase 2 constructs a `ReEntrySeed` with the new source token, so Phase 1 lands first or Phase 2's tests fail on a schema rejection |
| 2 → 3 | Phase 3 calls the verb Phase 2 registers. Shipping 3 first makes `/devforge:fix` call a verb that does not exist |
| 1 + 4 | **LOCKED TOGETHER.** The moment Phase 1 lands, the source-enumerating sentences under *Blast radius* are false. Same commit or same PR — there is no intermediate state in which the shipped instructions describe the shipped schema |
| 3 + its frontmatter edit | **LOCKED TOGETHER.** A `write-seed` call with no `allowed-tools` entry changes the command's permission behavior mid-run |
| 5 | Follows 3 and 4. Its targets are the sentences those phases falsify |
| 6 | Requires 1–4 landed in a consumer install |

**The minimum shippable unit is 1 + 2 + 3 + 4.** Phases 1–3 make the seed
writable; Phase 4 is what makes it *readable as a `fix` seed* rather than
consumed by a consumer whose prose claims only two sources exist. Under the
`spec` route Phase 4 is prose-only (fact 7), which is precisely why it is easy to
skip and precisely why skipping it ships instructions that contradict the code.

---

## Non-goals

> **⚠ NOTE ADDED 2026-08-26 — `88-COLD-FIX-BUGS-LANE-PLAN.md` did NOT make `/devforge:fix` a fourth seed producer, and that was FORCED rather than chosen.** Plan 88 gave `/devforge:fix` a second, feature-less COLD lane whose scope-change bounce is a real bounce with a real diagnosis — exactly the shape this plan turned into a seed for the feature lane. It writes **no seed**, because this plan's seed model is feature-scoped by construction: `write_seed` builds its path as `os.path.join(feature_dir, "fix-seed.json")` and `--feature-dir` is `required=True`, so a run with no feature directory has nowhere to put a seed and no consumer glob that would find it. Emitting one would have required a feature-less carrier, a new consumer block and a `/devforge:research` consumer that does not exist — three new mechanisms. **Nothing in this plan changed; the producer count is still three** (`/devforge:grill`, `/devforge:spec-check`, `/devforge:fix`'s feature lane). ⚠ **The recorded cost:** a cold bounce's diagnosis is spoken to the user and then lost, which is the same loss this plan fixed for the in-window bounce. A future session that observes cold bounces being re-derived has a real plan to write — a feature-less seed carrier plus a `/devforge:research` consumer — and should argue it from that observation, not from symmetry with this plan.

- **Any change to `/devforge:grill` or `/devforge:spec-check` behavior.** They
  are the pattern being mirrored, not modified — no change to their verbs,
  gating, seed filenames, or consumer contracts.
- **A new slash command.** The whole point is reuse of shipped machinery: an
  enum member, a producer verb, and prose. If a phase starts proposing a command,
  the plan has drifted.
- **Porting BMAD-METHOD's `correct-course` skill.** Its only borrowable idea is
  the Minor/Moderate/Major scope gradation, which D6 maps onto the existing
  `target_stage` field. Nothing else from it is in scope.
- **Anything touching `.devforge/memory.md`.** That is plan 79's subject. The two
  plans share no file, no helper, and no decision — stated explicitly so a future
  session does not merge them.
- **Seed lifecycle management.** Neither existing consumer deletes a consumed
  seed or mutates `cycle_count` (fact 6, `plan/main.md:110`,
  `specify/main.md:152`), and both record that as a deliberate v1 simplification.
  This plan inherits it and adds no deletion logic.
- **A mechanical check over seed contents.** Every consumer is prose today. D6's
  counter-argument depends on that staying true; a checker is a separate
  decision.

---

## Context for next session

The finding arrived from a comparison with BMAD-METHOD's `correct-course` skill
(2026-08-17). The skill itself is not the point and is not being ported — it
surfaced that our backward re-entry machinery has no downstream producer.

**The evidence lives in *Verified mechanics* and the route table; it is not
restated here.** An earlier revision duplicated six fact rows into this section,
which meant two copies to keep in sync — and a Phase-0 ratification that
corrected one and not the other would have produced exactly the stale-claim bug
this plan's discipline exists to prevent. What follows is only the *inferences*
those facts support, which the table does not carry:

1. **The two `spec`/`plan` consumers are asymmetric, and reading one tells you
   nothing about the other.** Facts 7 and 8. `/devforge:specify`'s route is
   source-agnostic in code; `/devforge:plan`'s hardcodes a filename. A session
   that verifies one and generalizes will get the route cost wrong.
2. **"Additive at the schema level" is not "additive to the suite."** Facts 1
   and 3 together. A build that correctly changes only `seed_schema.py` goes red
   with no other mistake made.
3. **In `breakdown/main.md` the word collides but the concept does not.** Fact
   10. Do not read those five hits as a consumer that needs updating.
4. **The change persists material that already exists rather than producing
   new material.** Fact 9 plus *What the gap costs*. `triage.md:18-24` already
   forces the bounce to name which item and why.
5. **Two `fix/main.md` sentences (`:35`, `:270`) go false the first time a seed
   is written**, and they are the plan's easiest omission because neither
   contains the word "seed". Phase 3 owns them.

**One honest weakness, recorded rather than hidden:** the `/devforge:fix` seed's
`invalidating_evidence` is a classification judgment, where both existing
sources carry grounded evidence (a quoted grill finding; an unsat core). OQ-4
owns it. A ratifier who decides the field must quote the finding's own evidence
string instead is answering a real objection, not adding ceremony.

**Discovered while drafting, NOT owned by this plan and not fixed here — and
there are TWO sites, not one.** The repo-root `CLAUDE.md` names a
`_grill/seed_schema` in both its plan-23 entry (`:35`, listing `seed_schema` as
a module of `src/devforge/lib/_grill/`) and its plan-36 entry (`:53`,
"`_grill/seed_schema.py` `SEED_TARGET_STAGES` grew 3 → 4"). That file does not
exist: plan 62 relocated it to `_shared/seed_schema.py`, **which the same file
records at `:75`** — so `CLAUDE.md` contradicts itself about where the schema
lives, which is why finding one site does not mean the class is closed. (Verified
2026-08-17: `src/devforge/lib/_grill/seed_schema.py` is absent;
`_spec_check/_seed.py:37` imports from `_shared.seed_schema`. The three line
numbers come from the review pass; the quoted text is the durable anchor.) Route
it separately; it is not this plan's subject and no phase above touches it.

## When resuming work

Read *Verified mechanics* first — twelve `file:line` rows, each checkable in
under a minute. If rows 1, 3, 7, 8 or 10 no longer hold, stop and re-derive: the
route-cost table, and therefore D2, rests on them.

Then read the route table under *Blast radius* before touching Phase 0, and
D2's **dependency paragraph** with it. Ratifying D2 Option B on the route table
alone is the one way to accidentally sign up for the largest build in the plan:
the table gives its consumer-side cost, and the dependency paragraph gives the
producer-side cost that is unscoped in Phases 2–4 as written.

Two things are easy to get backwards and are stated here so they are not:

- **The `spec` route needs no consumer code, but it does need consumer prose.**
  Phase 4 is not optional under any decision. Prose that says "grill or
  spec-check" while the code accepts a third source is exactly the stale-claim
  class this repo's cross-check rule exists to prevent.
- **`/devforge:grill` and `/devforge:spec-check` are not modified.** If a phase
  finds itself editing either producer's verb or gating, the change has left this
  plan's scope.
