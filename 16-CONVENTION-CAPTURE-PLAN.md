# 16 — Convention Capture (styling + state-management) + /constitute Routing

**Status**: Phases 0–5 DONE 2026-06-14 on `develop-2.0-init`. Phases 0–4 committed `bbde1c8`; Phase 5 testForge20 e2e PASSED — Styling + State Management captured in `docs/architecture.md` § Conventions, state-management routed to constitution §4 (classified into always/never/prefer by phrasing), styling correctly absent from the constitution. Both design decisions RESOLVED (see Decisions). Hard precondition SATISFIED — plan 15 (`15-AGENT-STANDARDIZATION-PLAN.md`) SHIPPED `720253f` (2026-06-07); its consumer-side work (agents swept of the dangling `§Conventions` anchor, the concept-name citation rule recorded at `src/agents-AUTHORING.md:147`) is the foundation this plan's producer-side capture completes.
**Branch**: `develop-2.0-init`

## Driver

Plan 15 fixed the CONSUMER side of the convention story: the agents now know to ground state-management decisions in "the constitution's Patterns & Anti-Patterns material" and styling decisions in existing components, and the dangling `§Conventions` anchor is gone (`grep §Conventions src/agents/` = 0, verified this session).

But the PRODUCER side is still blind. `/generate-docs` — the only command in the chain that reads the codebase (CBM + filesystem) — captures NO styling conventions and captures state-management conventions only incidentally (if a human hand-documents them in the architecture Patterns section). The producer's `## Conventions` section in `docs/architecture.md` has exactly four hardcoded buckets — `naming`, `file_organization`, `import_style`, `error_handling` (the `section_order` tuple at `src/devforge/lib/_generate_docs/_doc_setters/_renderers.py:280-285`). So the agents are told to ground in captured conventions that were never captured.

This plan closes that producer gap. It teaches `/generate-docs` Phase 4.3 to extract two new conventions buckets — `styling` and `state_management` — and teaches `/constitute` Phase 2 where each newly-captured bucket routes into the constitution (or to nowhere). It builds NOTHING on the agent side; it feeds the conventions the plan-15 agents already reference.

## Grounded pipeline facts (verified this session)

PRODUCER — `/generate-docs` Phase 4.3 (project-architecture tier) composes a `## Conventions` section in `docs/architecture.md` via the helper verb `set-architecture-conventions`. Today that section carries exactly four buckets:

- Render order + headings: `src/devforge/lib/_generate_docs/_doc_setters/_renderers.py:280-285` (`_render_conventions_subsections`, a `section_order` tuple of `(key, Heading)` pairs). Buckets whose bullet list is empty are omitted from output (`_renderers.py:289-290`).
- Accepted keys: `src/devforge/lib/_generate_docs/_doc_setters/_cmds_project.py:407` (`cmd_set_architecture_conventions`, a `for key in (...)` tuple).
- `--conventions` arg help text: `src/devforge/lib/_generate_docs/_doc_setters/_cmds_project.py:642-643` (`_build_set_architecture_conventions`, a JSON-object example listing the four keys).
- Spec instruction: `src/commands/generate-docs/main.md:434` (the Phase 4.3 table row naming the 4-bucket schema) and `:453-454` (the literal `set-architecture-conventions` example call).
- Existing tests: `tests/lib/test_doc_setters_project.py:1469` (`CmdSetArchitectureConventionsTests`).

CONSUMER — `/constitute` does NOT read code. Its Phase 0 hard-gates on `docs/overview.md` + `docs/architecture.md` + `docs/glossary.md` existing. Phase 1 `read-docs` parses `architecture.md` via `configure_helper._parse_architecture_md` (`src/devforge/lib/_configure/_md_parsers.py:219`), which lifts the WHOLE `## Conventions` section as a single raw-text string into `DOCS_JSON.architecture.conventions` (`_md_parsers.py:230`). Phase 2 composes that raw text into the constitution: Section 3 (Code Quality Standards) draws from `DOCS_JSON.architecture.conventions` (`src/commands/constitute/main.md:103`).

KEY CONSEQUENCE: because the parser lifts the conventions section as one raw-text blob, any bucket the producer adds to its `## Conventions` section automatically flows into `/constitute`'s raw conventions text — with NO consumer helper change. Routing each new bucket to the right constitution home is therefore a Phase-2 INSTRUCTION change in `constitute/main.md`, not a helper change. But this cuts both ways: because Section 3 composes from the whole conventions blob (`constitute/main.md:103`), the two new buckets flow into Section 3 BY DEFAULT — so the Phase-2 routing table must actively REDIRECT `state_management` to §4 and EXCLUDE `styling` from the constitution, not merely append rows.

CONSTITUTION STRUCTURE (verified `src/constitution.md`): §3 Code Quality Standards; §4 Patterns & Anti-Patterns, whose project-specific buckets are §4.1.1 ALWAYS [project-specific] (`:143`), §4.2.1 NEVER [project-specific] (`:169`), §4.3.1 PREFER [project-specific] (`:181`). `/constitute` Phase 2 emits those three via `add-pattern-rule --bucket {always,never,prefer} --scope project-specific` (`src/commands/constitute/main.md:112,114,116`). Plan 15 verified two facts about today's `/constitute`: it captures NO styling rules even in a real UI project (`15-AGENT-STANDARDIZATION-PLAN.md:100`), and state/pattern rules already land in the §4 Patterns & Anti-Patterns material (`15:99` — testForge20's BLoC rules live there). Routing the NEW `state_management` conventions bucket into §4 is THIS plan's decision (D3), consistent with that plan-15 observation.

## Scope and non-scope

This plan edits, on the PRODUCER side:

- the conventions schema in the `/generate-docs` helper (`_renderers.py` `section_order`, `_cmds_project.py:407` key tuple, `_cmds_project.py:642-643` help text) + its tests (`tests/lib/test_doc_setters_project.py` `CmdSetArchitectureConventionsTests`);
- the `/generate-docs` Phase 4.3 spec (`src/commands/generate-docs/main.md:434` table row + `:453-454` example call + the Phase 4.3 composition guidance);

on the CONSUMER side:

- the `/constitute` Phase 2 composition guidance (`src/commands/constitute/main.md` Section 3 + Section 4 — adds the D3 routing table; NO `/constitute` helper change — see Driver KEY CONSEQUENCE);

and the docs:

- the repo-root `CLAUDE.md` active-plans list (add the plan-16 entry), `CHANGELOG.md`, and `DEVELOPMENT-STATUS.md` if it tracks command capabilities.

It does NOT change:

- any `src/agents/*.md` file — plan 15 owns the agent roster + their convention-grounding rules; this plan only feeds the conventions they already reference;
- the `/constitute` `read-docs` parser or any `_configure` helper — the raw-text lift already carries new buckets through (see Driver KEY CONSEQUENCE);
- the build contract — `scripts/generate-agents.py` / `emit_claude` / the meta-block are irrelevant here (the conventions schema is a runtime-helper change, NOT a build-contract change);
- the constitution's structure — no new §-sections, no styling section.

## Locked decisions

### D1 — Capture lives in `/generate-docs` Phase 4.3, NOT `/constitute`

The two new buckets are captured in `/generate-docs`, not `/constitute`. Rationale: `/generate-docs` is the only command in the chain that reads the codebase (CBM + filesystem); `/constitute` reads only prior commands' doc outputs (its Phase 0 gates on the docs existing; its Phase 1 parses `architecture.md`). Putting capture in `/constitute` would force it to re-invoke code analysis, breaking the 4-command-chain separation.

### D2 — Styling captured in docs, EXCLUDED from the constitution

Styling is captured in the docs `## Conventions` section (as a new `styling` bucket) but is NEVER lifted into the constitution. Mechanism: an explicit routing entry in the `/constitute` Phase 2 table (D3) marks `styling` as documented-only. Rationale: plan 15 ruled styling authority is existing components + the design reference, NOT the constitution; this plan honors that — styling is documented knowledge, never constitution law. This is the user-chosen "in Conventions + routing guard" option, preferred over a structurally-separate docs section because the `state_management` routing instruction is needed anyway, so adding "styling → not lifted" to the same table is near-zero extra work and minimal blast radius.

### D3 — `/constitute` Phase 2 REDIRECTS the conventions buckets

Because `/constitute` Section 3 today composes from the WHOLE `DOCS_JSON.architecture.conventions` raw text (`constitute/main.md:103`), the two new buckets would leak into Section 3 unless Phase 2 redirects them. Phase 2 gains an explicit routing table that REDIRECTS each bucket to its constitution home (or to none):

- `naming` / `file_organization` / `import_style` / `error_handling` → Section 3 Code Quality Standards (unchanged — these are the buckets `:103` already intends);
- `state_management` → Section 4 Patterns & Anti-Patterns project-specific buckets (§4.1.1 / §4.2.1 / §4.3.1, emitted via `add-pattern-rule --scope project-specific` at `:112,114,116`) — NOT Section 3;
- `styling` → documented in `docs/architecture.md` only, lifted into NEITHER Section 3 NOR Section 4 (D2).

The orchestrator separates the buckets by their rendered `**Heading**` sub-section labels (`**Styling**`, `**State Management**`, etc.) in the raw conventions text — an instruction-level routing, NO helper change. Rationale: routes each captured bucket to the constitution home plan 15's agents already expect (state-management → Patterns & Anti-Patterns material; styling → existing components, never the constitution).

### D4 — No new mechanical detection

The two new buckets are orchestrator-composed in Phase 4.3 via CBM + the already-detected tech stack, exactly like the existing four buckets (none of which has a dedicated mechanical detector either — they are composed from concern docs + filesystem patterns per `generate-docs/main.md:434`). Rationale: consistency over invention — match the established bucket-composition pattern rather than introducing a new styling/state detector.

### D5 — Focused scope (items 1+2 build; items 3+4 verify-only)

Plan 15's `## Companion / future work` chartered four items for plan 16: (1) styling capture, (2) state-management capture, (3) constitution section-number/name drift reconciliation, (4) "Conventions"-vocabulary defragmentation. Items 3+4 are ALREADY substantially delivered by plan 15 (verified this session: `grep §Conventions src/agents/` = 0; `grep framework-idiomatic src/agents/` = 0; the concept-name-not-§-number rule recorded at `src/agents-AUTHORING.md:147`; the constitution's own section numbering is self-consistent). This plan therefore BUILDS only items 1+2 (capture) + the D3 routing, and VERIFIES items 3+4 in the Phase 4 DoD sweep rather than re-building them.

### D6 — Render order / back-compat (append after the existing four)

The two new buckets are APPENDED after the existing four in the `section_order` tuple (`styling`, then `state_management`), with headings "Styling" and "State Management". Because empty buckets are omitted from render output (`_renderers.py:289-290`), an existing 4-bucket caller (no styling/state values) renders byte-identical to before — a regression-free extension. A 6-bucket caller renders all six in `section_order` order.

## Open questions

None. Both design decisions are RESOLVED (D1–D6). Phase 5 is the standard user-driven testForge20 e2e gate, not an open decision.

## Execution discipline (applies to every phase)

- Every Python helper change goes through the `python-engineer` → `python-reviewer` loop, with a test written + actually run in the SAME turn (repo test-immediately-after-write rule).
- Every command/spec markdown edit (`src/commands/generate-docs/main.md`, `src/commands/constitute/main.md`, the repo-root `CLAUDE.md`) goes through `instruction-author` → `instruction-reviewer` (route-spec-edits-through-agent-flow).
- Cross-check after every change: re-grep the bucket-name signature repo-wide (the four producer sites — `_renderers.py`, `_cmds_project.py:407`, `_cmds_project.py:642-643`, `generate-docs/main.md:434`) so no enumeration of the bucket set drifts out of sync.
- Re-grep all `file:line` anchors before editing — line numbers drift.
- Each phase leaves the system buildable and tests green.
- This plan lives at repo root and is committed alongside the work it drives.

## Phase 0 — Precondition re-confirm + grounding (no edits)

Re-confirm the (already-satisfied) hard precondition and the verified grounding facts before any edit begins. Plan 15 SHIPPED `720253f` (2026-06-07); this phase re-confirms that shipped state, it is NOT a wait-gate.

- Re-confirm plan 15's consumer-side state is intact: no `§Conventions` anchor in any agent; the concept-name citation rule present at `src/agents-AUTHORING.md:147`.
- Re-confirm the producer-side anchors still hold (line numbers drift — re-grep before editing): the 4-bucket `section_order` tuple in `_renderers.py`; the 4-key tuple at `_cmds_project.py:407`; the 4-key help text at `_cmds_project.py:642-643`; the Phase 4.3 table row at `generate-docs/main.md:434` + example at `:453-454`.
- Re-confirm the consumer-side facts: `_parse_architecture_md` lifts `## Conventions` as raw text (`_md_parsers.py:230`); `constitute/main.md:103` composes Section 3 from `DOCS_JSON.architecture.conventions`; §4 project-specific buckets emit via `add-pattern-rule --scope project-specific` (`constitute/main.md:112,114,116`).
- Zero edits in this phase.

### Verify

```bash
# Plan-15 consumer-side state intact:
grep -rn "§Conventions" src/agents/                       # expect: 0
grep -n "concept-name" src/agents-AUTHORING.md            # expect: present (the F3 rule)
# Producer-side: the 4-bucket schema present at all four sites:
grep -n "naming\|file_organization\|import_style\|error_handling" src/devforge/lib/_generate_docs/_doc_setters/_renderers.py     # expect: the section_order tuple
grep -n "naming\|file_organization\|import_style\|error_handling" src/devforge/lib/_generate_docs/_doc_setters/_cmds_project.py  # expect: the key tuple + the help text
grep -n "set-architecture-conventions" src/commands/generate-docs/main.md   # expect: the table row + example call
# Consumer-side: raw-text lift + Section 3 composition:
grep -n 'conventions = _extract_section' src/devforge/lib/_configure/_md_parsers.py   # expect: lifts the whole Conventions section
grep -n "architecture.conventions" src/commands/constitute/main.md          # expect: Section 3 composition (line ~103)
# Plan-15 SHIPPED:
git log --oneline develop-2.0-init | grep 720253f         # expect: present
```

DoD: precondition re-confirmed satisfied (plan 15 SHIPPED `720253f`; consumer-side `§Conventions` swept; concept-name rule recorded); the producer-side 4-bucket anchors + the consumer-side raw-text-lift / Section-3-composition facts re-confirmed; zero edits in this phase.

## Phase 1 — Producer: extend the conventions schema (Python helper)

Add the two new buckets to the `/generate-docs` conventions schema so Phase 4.3 can populate them. Routed through `python-engineer` → `python-reviewer` (the repo helper loop — every python edit gets a test written + run the same turn).

- Append two entries to the `section_order` tuple in `src/devforge/lib/_generate_docs/_doc_setters/_renderers.py` (`_render_conventions_subsections`): `("styling", "Styling")` and `("state_management", "State Management")`, AFTER the existing four (D6). Update the function docstring's enumeration of sub-sections to match.
- Append `"styling"` and `"state_management"` to the key tuple at `src/devforge/lib/_generate_docs/_doc_setters/_cmds_project.py:407` (the `for key in (...)` in `cmd_set_architecture_conventions`).
- Extend the `--conventions` help text at `src/devforge/lib/_generate_docs/_doc_setters/_cmds_project.py:642-643` (`_build_set_architecture_conventions`) so the JSON-object example lists all six keys.
- Tests in `tests/lib/test_doc_setters_project.py` `CmdSetArchitectureConventionsTests` (`:1469`): (a) the two new buckets render with their "Styling" / "State Management" headings; (b) empty new buckets are omitted from output (D6 omission rule); (c) BACK-COMPAT — a 4-bucket input (no styling/state) renders byte-identical to the pre-change output; (d) a full 6-bucket input renders all six in `section_order` order.
- Helper edits via `python-engineer` → `python-reviewer`, with the tests written + run in the same turn.

### Verify

```bash
# section_order carries 6 entries (styling + state_management appended last):
grep -n 'styling\|state_management' src/devforge/lib/_generate_docs/_doc_setters/_renderers.py   # expect: appended after error_handling
# key tuple carries 6 keys:
grep -n 'styling\|state_management' src/devforge/lib/_generate_docs/_doc_setters/_cmds_project.py  # expect: in the key tuple + help text
# tests green incl. the 4 new cases:
python -m pytest tests/lib/test_doc_setters_project.py -k CmdSetArchitectureConventions   # expect: green
```

DoD: `section_order` carries six `(key, heading)` pairs with the two new buckets appended last; the `cmd_set_architecture_conventions` key tuple + the `--conventions` help text both enumerate all six; the four new tests (render-with-headings / empty-omitted / 4-bucket-byte-identical / 6-bucket-full) are written + run + green; helper edits through the python-engineer → python-reviewer loop.

## Phase 2 — Producer: update `/generate-docs` Phase 4.3 spec

Teach the Phase 4.3 orchestrator to compose the two new buckets from the codebase. Depends on Phase 1 (the helper must accept the keys first). Routed through `instruction-author` → `instruction-reviewer`.

- Update the table row at `src/commands/generate-docs/main.md:434` — the schema becomes the 6-bucket `{naming, file_organization, import_style, error_handling, styling, state_management}`.
- Update the example call at `:453-454` — the `--conventions` JSON example lists all six buckets.
- Extend the Phase 4.3 composition guidance so the orchestrator composes the styling + state-management bullets from the codebase (CBM + the already-detected stack), applying the SAME judgment discipline the existing four buckets follow (document only observed conventions; ground in real code; mark inference) — keep the phrasing consistent with how the existing four buckets are described (`:434` "LLM extracts from concern docs + filesystem patterns").
- All via `instruction-author` → `instruction-reviewer`.

### Verify

```bash
# Phase 4.3 table row + example name all 6 buckets:
grep -n "state_management\|styling" src/commands/generate-docs/main.md   # expect: in the :434 table row + the :453-454 example
# Composition guidance present (orchestrator composes the two new buckets from the codebase):
grep -niE "styling|state.management" src/commands/generate-docs/main.md  # expect: Phase 4.3 guidance for both
```

DoD: the Phase 4.3 table row + example call both enumerate the 6-bucket schema; the composition guidance directs the orchestrator to compose styling + state-management bullets from the codebase (CBM + detected stack) under the existing judgment discipline; phrasing consistent with the existing four buckets; all via the author → reviewer loop.

## Phase 3 — Consumer: `/constitute` Phase 2 routing table

REDIRECT each captured bucket to its constitution home in `/constitute` Phase 2 (D3). The two new buckets flow into Section 3 BY DEFAULT (Section 3 composes from the whole conventions blob at `:103` — see Driver KEY CONSEQUENCE), so Phase 2 must actively narrow Section 3 and redirect `state_management`, not merely append rows. NO `/constitute` helper change — the raw-text lift already carries the new buckets through; the redirect is instruction-only. Routed through `instruction-author` → `instruction-reviewer`.

The Phase 3 edits to `src/commands/constitute/main.md` must touch all three points:

- NARROW the Section 3 conventions intake at `:103` so it draws from ONLY the four legacy buckets (`naming` / `file_organization` / `import_style` / `error_handling`) of `DOCS_JSON.architecture.conventions`, explicitly EXCLUDING `styling` and `state_management`. The orchestrator separates buckets by their rendered `**Heading**` sub-section labels in the raw conventions text (D3).
- ADD `state_management` (the `state_management` sub-section of `DOCS_JSON.architecture.conventions`) as a source for the Section 4 project-specific buckets, reconciling the existing per-bucket source attributions at `:112` (always → patterns), `:114` (never → anti-patterns), `:116` (prefer → conventions) so a state-management rule can be classified into always / never / prefer as appropriate — the existing patterns / anti-patterns sources are KEPT, state_management conventions are ADDED alongside.
- RECORD `styling` as documented-only — lifted into NEITHER Section 3 NOR Section 4 — cross-referencing plan 15's styling stance (styling authority = existing components + the design reference, never the constitution) so a future session reading the routing table sees WHY styling is excluded.
- All via `instruction-author` → `instruction-reviewer`.

### Verify

```bash
# The routing table names all 3 destinations:
grep -niE "state_management|styling" src/commands/constitute/main.md   # expect: the routing table (state_management → §4; styling → docs-only)
# Section 3 intake NARROWED — its conventions reference is bucket-scoped, not the whole blob:
grep -niE "naming.*file_organization.*import_style.*error_handling|four legacy buckets|EXCLUD" src/commands/constitute/main.md  # expect: the :103 intake scoped to the four legacy buckets, styling + state_management excluded
# Section 4 project-specific bucket emit-path still referenced (state_management home):
grep -n "scope project-specific" src/commands/constitute/main.md      # expect: still present (the §4.x.1 emit calls)
# No styling lift into the constitution (the routing must mark it docs-only):
grep -niE "styling.*not lifted|styling.*docs.*only|never lifted|NEITHER" src/commands/constitute/main.md  # expect: the D2 exclusion documented
```

DoD: `/constitute` Phase 2 REDIRECTS the three bucket groups across all three touch-points — §3 intake NARROWED at `:103` to the four legacy buckets (styling + state_management excluded); `state_management` ADDED as a Section 4 project-specific source at `:112,114,116` (existing patterns / anti-patterns sources KEPT); `styling` recorded documented-only (lifted into NEITHER §3 NOR §4) with its exclusion rationale cross-referencing plan 15's styling stance; NO `/constitute` helper change; all via the author → reviewer loop.

## Phase 4 — Docs reconciliation + items-3+4 verification sweep

Reconcile the docs to the extended capture and run the D5 verification sweep for items 3+4.

- Add the plan-16 entry to the repo-root `CLAUDE.md` active-plans list (numbered = execution order), and reconcile the `/generate-docs` / `/constitute` rows in the "Where to find what" table IF the bucket set is named there (re-grep first; only edit if the 4-bucket list is enumerated there).
- Add a `CHANGELOG.md` entry (conventions schema 4 → 6 buckets; `/constitute` routing table).
- Update `DEVELOPMENT-STATUS.md` ONLY if it tracks per-command capabilities at the bucket level (re-grep first; do not invent a section).
- Run the D5 verification sweep for items 3+4 (verify-only, NOT re-build) and record the results inline in the commit / plan-update:
  - `grep -rn "§Conventions" src/agents/` = 0 (item 4 — vocabulary defragmentation: no dangling `§Conventions` anchor);
  - `grep -rn "framework-idiomatic" src/agents/` = 0 (item 4 — no stale convention vocabulary);
  - the concept-name-not-§-number rule present at `src/agents-AUTHORING.md:147` (item 3 — constitution citation-by-name convention recorded);
  - the constitution's own §-numbering is self-consistent (item 3 — no section-number drift to reconcile).
- Via `instruction-author` → `instruction-reviewer`.

### Verify

```bash
# Plan-16 in the active-plans list:
grep -n "16-CONVENTION-CAPTURE-PLAN" CLAUDE.md      # expect: present in the active-plans list
# CHANGELOG entry:
grep -niE "conventions.*bucket|styling.*state" CHANGELOG.md   # expect: the new entry
# D5 items-3+4 sweep (verify-only — these must already be clean from plan 15):
grep -rn "§Conventions" src/agents/                 # expect: 0
grep -rn "framework-idiomatic" src/agents/          # expect: 0
grep -n "concept-name" src/agents-AUTHORING.md      # expect: present
# Bucket-name signature in sync across all producer sites (no enumeration drift):
grep -rln "state_management" src/devforge/lib/_generate_docs/ src/commands/generate-docs/main.md   # expect: all updated key-form sites (helper + /generate-docs spec)
grep -n "State Management" src/commands/constitute/main.md   # expect: present — constitute renders the bucket as the heading form `**State Management**` / hyphenated "state-management", NOT the underscore key
```

DoD: the repo-root `CLAUDE.md` active-plans list carries the plan-16 entry (and the "Where to find what" rows reconciled IF they enumerate the bucket set); a `CHANGELOG.md` entry added; `DEVELOPMENT-STATUS.md` updated only if it tracks bucket-level capability; the D5 items-3+4 sweep recorded clean (all four greps return their expected result — verify-only, no re-build); the bucket-name signature is in sync across every producer site (no enumeration drift); all via the author → reviewer loop.

## Phase 5 — testForge20 e2e (USER-DRIVEN HARD GATE)

Run the producer → consumer chain on testForge20 (a real UI project) and confirm capture + routing end to end. This phase is user-driven (requires a live testForge20 install of the post-Phase-4 source); it is the repo's standard manual e2e gate, NOT a code change.

- Run `/generate-docs` on testForge20; confirm `docs/architecture.md` `## Conventions` now carries a "Styling" subsection and a "State Management" subsection grounded in the project's real code.
- Run `/constitute`; confirm state-management lands in the constitution §4 (Patterns & Anti-Patterns project-specific buckets) and styling does NOT appear anywhere in the constitution (D2).

### Verify

```bash
# (User-driven — run against a testForge20 install with the new source emitted.)
# After /generate-docs on testForge20:
#   grep -n "## Conventions" -A40 docs/architecture.md   # expect: Styling + State Management subsections, grounded in real code
# After /constitute on testForge20:
#   grep -niE "state|store|reducer" constitution.md       # expect: state-management rules present in §4 Patterns & Anti-Patterns
#   grep -niE "styling|css|tailwind|stylesheet|theme" constitution.md  # expect: 0 (styling NOT lifted, per D2)
```

DoD: e2e confirms `docs/architecture.md` `## Conventions` carries Styling + State Management subsections after `/generate-docs`; the constitution carries state-management rules in §4 and ZERO styling rules after `/constitute` (D2); user-driven sign-off.

## Out of scope (do NOT plan here)

- **Items 3+4 as BUILD work** — constitution section-number/name drift reconciliation and "Conventions"-vocabulary defragmentation are plan-15-delivered (D5); this plan VERIFIES them in the Phase 4 sweep, it does not re-build them.
- **Any build-side change to the generator** — `scripts/generate-agents.py` is irrelevant here; the `/generate-docs` conventions-schema extension is a runtime-helper change, NOT a build-contract change.
- **New mechanical convention detectors** — the two new buckets are orchestrator-composed exactly like the existing four (D4); no styling/state detector is introduced.
- **Adding styling to the constitution** (D2) or any constitution STRUCTURAL change — no new §-sections, no styling section; styling stays documented-only.
- **Touching agent files** — plan 15 owns the agent roster + their convention-grounding rules; this plan only feeds the conventions they already reference. Confirm zero `src/agents/*.md` edits across all phases.

## Context for next session

- This plan closes the PRODUCER gap behind plan 15's consumer-side convention story. Plan 15 taught the agents to ground state-management in the constitution's Patterns & Anti-Patterns material and styling in existing components, but `/generate-docs` (the only code-reading command) captured NEITHER. This plan teaches `/generate-docs` Phase 4.3 to capture two new conventions buckets (`styling`, `state_management`) and teaches `/constitute` Phase 2 where each routes.
- **Both design decisions are RESOLVED (D1–D6).** Key ones: D1 capture lives in `/generate-docs`, not `/constitute` (only `/generate-docs` reads code); D2 styling is documented-only, NEVER lifted into the constitution; D3 the Phase-2 routing table REDIRECTS the buckets — NARROW §3 intake at `:103` to the four legacy buckets (`naming`/`file_organization`/`import_style`/`error_handling`); redirect `state_management` → §4 project-specific buckets (NOT §3); `styling` → docs-only (NEITHER §3 NOR §4) — because §3 composes from the whole conventions blob, so the table must redirect, not merely append; D4 no new mechanical detector (orchestrator-composed like the existing four); D5 items 3+4 are plan-15-delivered (verify-only); D6 append the two new buckets after the existing four (empty-omitted ⇒ byte-identical 4-bucket back-compat).
- **Hard precondition: plan 15 SHIPPED `720253f` (2026-06-07) — SATISFIED.** Its consumer-side state (agents swept of `§Conventions`; concept-name rule at `src/agents-AUTHORING.md:147`) is the foundation; Phase 0 re-confirms it (not a wait-gate).
- **The critical mechanism (Driver KEY CONSEQUENCE):** `/constitute`'s `read-docs` parser lifts the whole `## Conventions` section as ONE raw-text string (`_md_parsers.py:230` → `DOCS_JSON.architecture.conventions`). So any bucket the producer adds flows into `/constitute`'s raw conventions text with NO consumer helper change — D3 routing is purely a Phase-2 INSTRUCTION change in `constitute/main.md`. Do NOT propose a `_configure`/`_md_parsers` edit for the routing.
- Verified producer-side anchors (this session — re-grep before editing, they drift): the 4-bucket `section_order` tuple at `src/devforge/lib/_generate_docs/_doc_setters/_renderers.py:280-285` (empty-omitted at `:289-290`); the 4-key tuple at `_cmds_project.py:407`; the 4-key help text at `_cmds_project.py:642-643`; the Phase 4.3 table row at `src/commands/generate-docs/main.md:434` + example at `:453-454`; tests at `tests/lib/test_doc_setters_project.py:1469`.
- Verified consumer-side anchors: `conventions = _extract_section(md_text, "Conventions")` at `_md_parsers.py:230`; Section 3 composes from `DOCS_JSON.architecture.conventions` at `src/commands/constitute/main.md:103`; §4 project-specific buckets emit via `add-pattern-rule --scope project-specific` at `:112,114,116`; the constitution's §4.1.1/§4.2.1/§4.3.1 [project-specific] sub-sections at `src/constitution.md:143,169,181`.
- Phase order: 0 (re-confirm) → 1 (helper schema, python loop) → 2 (`/generate-docs` spec, markdown loop, depends on 1) → 3 (`/constitute` routing, markdown loop) → 4 (docs + items-3+4 sweep) → 5 (user-driven testForge20 e2e).

## When resuming work

1. Re-read this plan in full + `15-AGENT-STANDARDIZATION-PLAN.md` `## Companion / future work` (which chartered this plan) + the producer/consumer anchors above.
2. Re-confirm plan 15 is landed (Phase 0 — SHIPPED `720253f`) and its consumer-side state intact (`grep §Conventions src/agents/` = 0) BEFORE any edit; the precondition is already satisfied, so this is a re-confirm, not a wait-gate.
3. Re-grep every `file:line` anchor before editing — line numbers drift.
4. Run phases in order (0 → 1 → 2 → 3 → 4 → 5). Phase 2 depends on Phase 1 (the helper must accept the new keys before the spec tells the orchestrator to emit them); Phase 5 is the user-driven e2e gate.
5. Route every Python helper change through `python-engineer` → `python-reviewer` with a test written + run the same turn; route every command/spec markdown edit through `instruction-author` → `instruction-reviewer`.
6. Cross-check after every change: re-grep the bucket-name signature across all producer sites (`_renderers.py`, `_cmds_project.py:407`, `_cmds_project.py:642-643`, `generate-docs/main.md:434`) so no enumeration of the bucket set drifts out of sync.
7. Commit alongside the work in repo commit style (lowercase, terse, scope prefix — e.g. `feat(generate-docs): capture styling + state-management conventions`).

## Related plans

- `15-AGENT-STANDARDIZATION-PLAN.md` — chartered this plan (`## Companion / future work`); delivered the CONSUMER side (the agent convention-grounding rules + the concept-name citation convention at `src/agents-AUTHORING.md:147`) that this plan's PRODUCER side completes. Plan 15 swept the dangling `§Conventions` anchor and ruled styling authority is existing components, never the constitution (the basis for D2); this plan feeds the conventions those agents already reference. Items 3+4 it chartered are plan-15-delivered — verify-only here (D5).
- `08-CLAUDE-MD-COMMAND-TRIM-PLAN.md` — the always-on `src/CLAUDE.md` budget discipline. Relevant because this plan adds NO content to the always-on overlay (`src/CLAUDE.md`); the capture detail lives in the on-invocation command bodies (`src/commands/generate-docs/main.md`, `src/commands/constitute/main.md`).
