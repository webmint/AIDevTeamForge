# /devforge:fix triage + scope-estimate

This file is read by the orchestrator at PHASE 1 of `/devforge:fix`. It is **decision guidance**, not a template the helper renders and not a brief injected into an agent — the orchestrator reads it to classify each working-list item and to decide whether to bounce. Apply it before calling `fix_helper resolve-scope`.

**It applies UNCHANGED to both lanes.** Whether the working-list item came from a feature's `review.md` / `verification.md`, from a conversational in-window defect, or from a `bugs/NNN-<slug>.md` file on the cold lane, the classification below is the same table with the same discriminator. **What differs is only WHERE a bounced item is sent** — see `## Where a bounce goes` at the end.

## What /devforge:fix may remediate vs what it may not

`/devforge:fix` exists to remediate a **defect** — code that is wrong against its own intent — with `/devforge:implement`'s gates, without re-running spec → plan → breakdown. It does NOT exist to change WHAT the feature does. The triage decision for every working-list item is binary:

| Class | Stays in `/devforge:fix` | Examples |
|---|---|---|
| **Defect repair** | yes | A logic bug; a missing/incorrect case in existing behavior; a contract violation (a function does not do what its callers/spec assume); a security hole in code that already exists; a leftover artifact (debug print, dead branch); a name/comment that lies about what the code does; a regression a cross-task interaction introduced. The fix makes EXISTING behavior correct. |
| **Feature / architecture change** | no — bounce (see `## Where a bounce goes`) | The fix would ADD behavior not in the spec; change a data model / schema; introduce or remove a dependency; restructure a layer or module boundary; change a public API contract; alter an architectural decision. The change grows or reshapes the feature, it does not correct it. |

The discriminator is **correctness vs. scope**: a defect repair restores the feature to what it was already supposed to do; a feature/architecture change moves the goalposts. If remediating the finding requires deciding something the spec never decided (a new behavior, a new contract, a new structure), it is out of scope for `/devforge:fix`.

## The scope bounce — when to stop

STOP when ANY working-list item is a feature/architecture change rather than a defect repair. Surface the bounce to the user naming:

- WHICH item triggered the bounce (its `title`).
- WHY it is a scope change, not a defect repair (which row of the table above it falls under — e.g. "this adds a new validation rule the spec never specified" or "this changes the data model").
- The right home for it, which depends on the lane — see `## Where a bounce goes` below. Either way the reason is the same: the change needs a spec decision + plan + atomic breakdown, not a gated in-place fix.

Do NOT partially remediate around a bounced item. `/devforge:fix` either remediates a working list of pure defect repairs, or it bounces.

### Mixed working lists

When the working list MIXES defect repairs with a scope change, surface the scope change as the bounce and let the USER decide:

- **Drop the scope change and re-run** — the user removes the scope-change finding from consideration and re-runs `/devforge:fix`; `/devforge:fix` then remediates the defect-only remainder.
- **Take the whole set through `/devforge:specify`** — when the defects are entangled with the scope change (fixing the defect only makes sense alongside the new behavior), the whole set goes through the full chain.

`/devforge:fix` does not silently drop the scope item and proceed — the user owns that call.

## Scope-estimate sizing (informational)

After classifying every item as a defect repair, the touched-file set is whatever the findings cite — `fix_helper resolve-scope` computes the narrow union of `files_cited` across the working list (NOT the assembled-feature diff; that breadth is `/devforge:verify`'s job). Two sizing checks worth a glance before dispatching:

- **Empty scope** — if the findings cite no files, `/devforge:fix` has no file target to verify against. The PHASE-1 empty-scope guard stops the run and points the user back to the report to add the missing location. A defect with no file citation is not yet remediable by a gated fix.
- **Wide scope** — if a single "defect" touches many files across several layers, re-examine the classification: a fix that ripples broadly is often a feature/architecture change wearing a defect's clothes (it is reshaping, not correcting). When in doubt, treat breadth as a signal to re-check the defect-vs-change call above, and bounce if it is really a change.

**Breadth is a SIGNAL, never a rule.** There is no file-count threshold anywhere in this command: a one-file edit that changes a public contract is a scope change, and a mechanical null-check repair across eight call sites is a defect repair. The defect-vs-change call is the discriminator; the file count is only a hint that it is worth making that call again carefully.

## Where a bounce goes

Same classification, two destinations — and the difference is mechanical, not stylistic.

| Lane | The bounce recommends | Seed | The item's record |
|---|---|---|---|
| **FEATURE** (a feature dir was resolved) | `/devforge:specify` → `/devforge:spec-check` → `/devforge:plan` → `/devforge:grill` → `/devforge:breakdown` | On the matching `re-enter specify` pick ONLY, `specs/[feature]/fix-seed.json` | The seed carries the diagnosis into the re-run |
| **COLD** (a `bugs/NNN-<slug>.md` argument) | `/devforge:research "<the bug's description>"`, then the full chain | **NONE — ever** | **Nothing persists it. Your message to the user IS the record** |

**Why the cold lane names `/devforge:research` and not `/devforge:specify`:** `/devforge:specify` blocks until a pending research or discover handoff exists in a feature directory. A cold bug has no feature directory and no handoff, so recommending `/devforge:specify` would name a command that refuses to run. `/devforge:research` is what allocates the feature directory `/devforge:specify` then resolves.

**Why the cold lane writes no seed:** a re-entry seed is written INTO a feature directory and is found there by the consuming command. A cold run has no feature directory, so there is nowhere to put one and no consumer that would look. This makes the naming duty above load-bearing on the cold lane in a way it is not on the feature lane — state the item and the reason explicitly in your message, because nothing else will.

**Leave the bug file `Open` on a cold bounce.** Do not flip it, do not mark it `In Progress`, do not annotate it. The bug is not being worked, and a status the framework cannot keep true is worse than one it never set.

## A captured bug is not a confirmed bug

This applies to the cold lane only, and it comes BEFORE triage rather than during it — but it is the most common way a cold run should end early, so it belongs here.

`/devforge:report-bug` is pure capture: it reads no source code and confirms nothing. A `bugs/` file therefore records **what somebody believed at the time they filed it**, which is not the same as what the code does now. Before classifying a cold item at all, PHASE 0.4b requires that the defect be found in live code and the offending lines quoted. Three ways a captured bug fails that check, all ordinary:

- **Already fixed** — unrelated work repaired it since it was filed.
- **Described inaccurately** — the real defect is elsewhere, or the symptom has a different cause.
- **Intended behavior** — what looked wrong is what the code is supposed to do.

In every one of those cases the run STOPS without remediating, the bug file is left `Open` and untouched, and `/devforge:research` is the recommended next step. **Do not "triage around" an unconfirmed bug** — classification of a defect nobody has located is classification of a guess.
