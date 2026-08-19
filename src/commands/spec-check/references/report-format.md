# Spec-Check report layout

This is the skeleton the `spec_check_helper render-report` verb produces and
writes to `specs/[feature]/spec-check.md`. It is **orientation only** — the
helper owns the actual render (`src/devforge/lib/_spec_check/_report.py`); this
file documents the shape so the orchestrator knows what the report contains. Do
not hand-author the report; call `render-report`.

## Two layers — check the SOFT layer, not the HARD one

The report deliberately separates two layers, because the softness in this
neurosymbolic check lives in the TRANSLATION, not the proof:

1. **SOFT (LLM) — "how your ACs were read as logic."** The variable glosses plus
   an original-text ↔ logic-reading juxtaposition. This is what the human is
   asked to CHECK — the proof below is only as good as this reading.
2. **HARD (Z3) — "given that reading, these ACs are provably incompatible."** The
   deterministic solver's contradiction, present only on a proven `unsat`.

The reader's job is to confirm layer 1, not to re-derive layer 2. `Dismiss` at the
human gate is the escape hatch when layer 1 is wrong.

## Sections (in render order)

- **Header** — `# Spec-Check: <feature>`, then `**Feature**` and `**Date**` (the
  helper computes the date itself), then `**Spec hash**: <sha256-hex>` when the
  `render-report` call supplied a `--spec-file`: the content hash of the
  `spec.md` this check ran over, so a later consumer can re-hash that file and
  detect drift between when the report was produced and when it is consumed. No
  `--spec-file`, no hash line.
- **Scope blockquote (D11)** — the verbatim "consistency prover, not a
  mind-reader" boundary. Rendered near the top of every report.
- **`## Recommendation`** — the recommended disposition (CONSISTENT / REVISE-SPEC
  / DISMISS) plus its reason. On REVISE-SPEC it names the conflicting `ac_id`s; on
  CONSISTENT with nothing formalizable it states "No formalizable logic found —
  nothing was proven"; an `unknown` solver result adds a caveat line. When the
  run supplied a `--stability-file` (D13), this section also carries the
  formalization-stability line — "contradiction core reproduced in j/k passes" for
  a stable verdict, or a prominent "Formalization unstable" caveat for an unstable
  one (the instability is surfaced here, never folded into the disposition).
- **`## UNRESOLVED SUBJECTS`** — rendered ONLY when the run supplied an
  `--ir-files-file` and the cross-pass merge over those passes reports at least
  one variable whose subject no pass resolved; otherwise the section is absent
  entirely. One entry per such variable — its name, its gloss, and the `ac_id`s
  whose coverage rows named it — then one line per pass that failed it: what
  that pass searched, or, when the pass claimed a resolution whose citation did
  not check out, that citation error. A variable resolved in ANY pass is
  excluded. This is a FORMALIZATION FAILURE, not a solver result — those ACs
  carry no constraint at all, so Z3 never reasoned about them and a CONSISTENT
  verdict elsewhere in this report says nothing about them. Placed right after
  the recommendation it qualifies: this is exactly the case a CONSISTENT verdict
  can otherwise hide.
- **`## How your ACs were read as logic`** (D4 SOFT layer) — the variable glosses,
  then each formalized AC's original text beside its logic reading. This is the
  human's check against a mistranslation.
- **`## Contradiction`** (D4 HARD layer) — rendered ONLY on a proven `unsat`. Names
  exactly the `unsat_core` ACs and the constraints that produced them, and states
  it is a deterministic proof over the formalization shown above, not a judgment
  about whether that formalization is what you meant.
- **`## Coverage`** (D6 honesty ledger) — the headline
  `**Checked N of M acceptance criteria** (K unformalizable).`, which gains a
  third term — `(K unformalizable; J unresolved subjects).` — only when J > 0
  (singular `subject` when J is 1; the K term renders unconditionally, "0
  unformalizable" included). Then a per-AC line marking each `formalized` /
  `skipped_prose` / `skipped_unsupported` (with the skip reason) /
  `unresolved_subject` (with the named subject variable:
  `- AC-2: unresolved_subject (subject: <variable>)`).
  An `unresolved_subject` AC counts in neither N nor K — it is the ledger's
  fourth term: the AC was never formalized, because nothing resolved what its
  subject IS, so the solver never saw it; the failure detail lives in the
  UNRESOLVED SUBJECTS section above. Makes "the solver only proves over the
  formalized subset" structural, not a footnote.

When the IR carries at least one `implication` constraint, a short reachability
note (conditional ACs are checked assuming their trigger can fire — the solver
does not independently verify reachability) is rendered after the reading section.

## The re-entry seed (REVISE-SPEC only)

The seed is NOT part of `spec-check.md`; it is a sibling JSON artifact
(`specs/[feature]/spec-check-seed.json`) written by `write-seed` in the command's
PHASE 6 — ONLY when the user's human-gate pick is `Revise spec` AND the
recommendation was REVISE-SPEC. It carries `source="spec-check"`,
`target_stage="spec"`, `prior_conclusion` (the conflicting ACs as authored),
`invalidating_evidence` (the proven contradiction — the unsat-core `ac_id`s plus
the logic reading), `must_satisfy` (the conflict the revised spec must resolve),
`cycle_count`, `carried_findings`, and `provenance` (a pointer to this
`spec-check.md`). The schema is owned by
`src/devforge/lib/_shared/seed_schema.py` (`ReEntrySeed`); the helper validates and
atomically writes it — do not hand-author the seed. `/devforge:specify` consumes it on
re-entry (a `Consistent` / `Dismiss` / cross-pick verdict writes no seed).
