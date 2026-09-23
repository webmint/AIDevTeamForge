# 77-EVIDENCE — v1 benchmark handoff: the discovery-to-lock inversion

**⚠ UNTRACKED — DO NOT COMMIT.** This file contains private-client identifiers (file paths, field names, symbol names) and this repository is PUBLIC. It follows the same disposition as the untracked plan documents 73/74/75: kept untracked, deleted at the official v2 go-live per the ratified disposition recorded in `78-TEST-IDENTIFIER-SCRUB-PLAN.md`. Never quote its identifiers into any tracked file — `77-POST-CHANGE-OUTPUT-MATRIX-PLAN.md`'s privacy constraint treats any such identifier as a hard error.

**Provenance:** delivered by the maintainer in-conversation on 2026-08-13 as design input for v2 (the amendment recorded in `77-POST-CHANGE-OUTPUT-MATRIX-PLAN.md`'s 2026-08-13 amendment section). Preserved verbatim below; nothing edited.

---

DevForge v2 — design input: the discovery-to-lock inversion

Provenance: measured on DevForge v1 (forge main branch; template sets 1.28.0 and 1.27.0) across 6 runs of a frozen brownfield benchmark. This is not a report on v2. It is the specific v1 behavior v2 should be built to not reproduce.

The finding

v1 has a real, repeatable discovery advantage over every other SDD framework measured — and it converts that advantage into a worse outcome than not looking.

Benchmark: a frozen ticket says "remove filters X, Y, Z from search surface S." A second, unnamed surface reaches the same filter builder and is equally affected. A frozen probe asserts the second surface stops emitting Y and Z.

┌─────────────────────────────┬─────────────────────────────────┬──────────┐
│          framework          │ named the second surface's file │ fixed it │
├─────────────────────────────┼─────────────────────────────────┼──────────┤
│ cursor ×3, kiro ×3, bmad ×1 │ 0 / 7                           │ 0        │
├─────────────────────────────┼─────────────────────────────────┼──────────┤
│ speckit ×3                  │ 1 / 3 (one passing mention)     │ 0        │
├─────────────────────────────┼─────────────────────────────────┼──────────┤
│ DevForge v1 ×6              │ 6 / 6                           │ 0        │
└─────────────────────────────┴─────────────────────────────────┴──────────┘

v1 found it every time. In 5 of 6 runs it then produced, in ascending order of harm:

1. an "Explicitly NOT modified" list containing that exact file
2. a §7 hard constraint forbidding the one discriminator that would have covered it
3. an acceptance criterion asserting the removed fields are still present on that path
4. a review whose top-priority action item was: "add a use-case-level spec asserting the captured input still contains primaryShipToCity / primaryShipToState."

An unseen coupling is a bug someone finds later. A coupling that has been examined, named, constrained by a written rule, and covered by a passing regression test is a bug that the audit trail has made permanent. Every downstream reader now has documentary evidence that the behavior is intended.

The frameworks that never looked left the defect discoverable. v1 left it defended.

The mechanism — one sentence, at research time

The single run that passed differs from the other five by a framing, not by depth. All six ran the same blast-radius analysis and found the same caller.

Five failing runs, on finding a second caller of a shared function:

▎ "High — do not edit the function body; add a caller-side opt-out."
▎ "Explicitly NOT modified: accounts/domain/cases/SearchOrganizationsV2UseCase.ts."

The one passing run, same finding:

▎ "Fallback path … reaches the same two builders … with tabType = CUSTOMER. Both paths need the change for consistent behavior."

It went further and pre-empted the obvious objection — the path is "defensive only in practice" — and kept it in scope anyway, "so both paths stay consistent."

That run then chose a guard keyed on the tab type itself rather than a new opt-out parameter, and changed the second surface's behavior without editing the second surface's file at all.

So: v1's blast-radius analysis is sound and its output is correct. The defect is that the analysis has exactly one exit — protect — and no path to include. "Shared code" resolves to "risk" and never to "consistency."

What to change in v2

Not prose. Artifact shape. Each of these is a v1 template feature that currently only points one way:

1. Blast radius → emission matrix. Replace the risk-worded caller table with one whose required column is what this caller emits after my change. A row still emitting a field the ticket removes is a finding requiring resolution, not a row to be marked "unchanged." Produce it at /research, before any AC exists.

2. "Explicitly NOT modified" must be derived, not asserted. A file may enter that list only with a reason of the form "emits ⟨fields⟩; the ticket targets ⟨other fields⟩." If the emitted set intersects the removed set, the entry is invalid and must be escalated as a product question.

3. Regression pins need contradiction detection. An AC of the form "path P still contains field F" where F is a field the same spec removes elsewhere is a conflict flag, not a pin. v2 must refuse to write it on inferred intent ("we didn't intend to touch this file") and require product intent, quoted.

4. Hard constraints (§7) must record their cost. Any rule that eliminates a candidate discriminator must state what that candidate would have achieved. v1 wrote "must not rely on userType === undefined" twice, independently, without ever recording that this was the only discriminator covering both surfaces.

5. Review needs one question that can invalidate an AC. v1's review is excellent — five-line evidence chains, mutation-tested assertions, recorded reviewer disagreement, a written correction to its own spec's risk table — and it is structurally incapable of catching this, because it grades against the spec's ACs. It can ask did we do what we said; it cannot ask was the invariant right. Add exactly one review step that reads the emission matrix, not the ACs.

What will not work

Do not fix this with added guidance text. Measured null result: 16 runs across 6 frameworks whose guidance differs enormously — bare IDE, spec-kit, BMAD, DevForge v1 — produced identical guard designs. 15 of 16 added an opt-out parameter to the shared function. Artifact volume ranged 24× (106 → 2523 lines) with zero effect on the probe. Test volume ranged 14× with zero effect. Investigation depth inverted the relationship. The only axis that predicted the outcome was guard shape, at 17/17.

Guidance that does not change the shape of a required artifact does not change the outcome.

Acceptance test for v2

Re-run the frozen prompt. v2 passes if the second surface stops emitting the removed fields without the prompt ever naming that surface — and, importantly, without the second surface's file appearing in the diff. The passing v1 run never edited it. Correct coverage here looks like a predicate change in one shared function, not a call-site sweep.

Secondary check, cheaper to run and nearly as diagnostic: grep v2's own artifacts for the string "still contains" applied to a field the ticket removes. In v1 that phrase is the signature of the failure.

---

## Known internal tension (recorded at intake, unresolved)

The table above scores DevForge v1 "fixed it: 0" across 6 runs, while the mechanism section describes ONE of the 6 as passing (the run that guarded on the tab type and satisfied the probe without editing the second surface's file). `77-POST-CHANGE-OUTPUT-MATRIX-PLAN.md`'s own Problem table separately lists "a reference run using the same commands: pass/pass" beside "v1.28: 2 runs, 2/2 discovery, 0/2 handling" — the likely reconciliation is that the table's "fixed it" column excludes (or mis-counts) the passing/reference run, but this was NOT confirmed by the maintainer when asked on 2026-08-13. Treat the per-run counts as approximate; treat the mechanism finding (protect-only exit; guard shape decides the probe) as the load-bearing content.
