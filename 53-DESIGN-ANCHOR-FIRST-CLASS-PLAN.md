# 53 — Design intent as a first-class pipeline input (the `design_anchor`)

**Status:** ✅ **BUILD DONE — Phases 1–8 SHIPPED 2026-07** on `develop-2.0-init` (working tree, uncommitted). **Phase 9 (mintEnvoy/testForge20 e2e) DEFERRED by maintainer — "will test later"; NOT blocking** (matches the repo's standard user-driven-e2e disposition). All 8 build phases were built + reviewed clean behind python-engineer→python-reviewer + instruction-author→instruction-reviewer+claude-code-guide loops; full suite green (~9300 unittest, only the 2 pre-existing environmental `pytest`-import collection errors in `_audit`/`_shared`). An **install-ride smoke PASSED** — the installed `.devforge/lib/` design-fidelity helper chain (`design_helper validate-binding`/`compare`/`extract-spacing-scale`/`check-design-source`, the `set-design-anchor`/`set-scope-design-anchor` setters incl. the cross-package `_design._source` import, both `_design/js/*.js` collectors `node --check` clean) runs correctly as `cp -R`'d consumer artifacts. **Runtime-unproven only where a live browser is required** (the JS collectors' real `evaluate_script` behavior against a running app + Chrome DevTools MCP) — that is exactly what Phase 9 covers. **This plan SUPERSEDES plan 52** (`52-DESIGN-FIDELITY-WEB-PROBE-PLAN.md`): it absorbs plan 52's still-valid parts (the honesty invariants, the deterministic-probe discipline, the always-on geometry floor, the seed-dependency limitation note) and discards the machinery plan 52 built only to compensate for a missing input (the `data-ref` manifest assumptions, route-inference framing, and — reversed here via D12 — plan 52 D11's "no automated check reads the reference"). Branch: `develop-2.0-init`. **Original design ratified 2026-07-06** (all forks decided in the maintainer design session). **Deferred/flagged (non-blocking):** the `update.sh --only` `_implement`/`_artifact` always-copy gap (pre-existing, broader than plan 53); the figma fast-follow SIBLING plan (open `kind`, unwritten); a `/review` anti-relitigation dedup nit.

## Problem — the pipeline has no first-class capture of design intent

Font drift was the symptom that exposed the gap: nothing in the pipeline carries "here is what this should look like" from intake to verification, so every downstream step re-guesses it. There are two gaps, **in priority order**:

1. **Specification (capture intent at input) — FIRST.** Today the maintainer expresses design intent manually in research prose ("build what's in this HTML file, class `.fooBar`"). That anchor is never captured as a structured, first-class pipeline input, so every downstream step re-derives it from prose or re-infers it from the built code. Plan 43 added a flat `**Design source**:` spec-frontmatter line (`html` / `figma` / `screenshot` / `none`) parsed by `parse_design_source()` in `src/devforge/lib/_design/_source.py`, but that field names only the SOURCE FILE — never WHICH elements of it carry the intent — and no stage beyond a non-blocking WARN consumes it.

2. **Verification (catch drift after build) — falls out of #1.** Because intent is never captured at input, plan 40's `design-auditor` had to INVENT a `data-ref` disposition manifest at `/breakdown` and INFER a render route at `/review` — half of that machinery existed only to reconstruct the input that was never recorded. If the anchor is captured at input, verification READS it and compares, instead of inventing a manifest or inferring a route.

The fix is a **`design_anchor`** — design intent as a first-class pipeline object that lives from research → discovery → specify → plan → breakdown → implement → review → verify and is consumed by the `design-auditor` (`src/agents/design-auditor.md`). Declared once at intake, every later stage reads the SAME object — not re-declared, not re-inferred.

## The mechanism

### Two INDEPENDENT axes (the central anti-over-fit)

Design fidelity has two axes that do NOT correlate, and they are ASYMMETRIC in SOURCE — one is declared, one is detected (D17):

- **Source of intent (the anchor) — HOW intent is expressed. DECLARED.** `kind: html` / `figma` / … — an EXPLICIT tagged field ON THE ANCHOR (you declare your design source). Platform-agnostic: any UI on any stack can be built visually identical to an HTML intent, so intent is platform-agnostic.
- **Platform of the built UI — WHAT the implementation renders on. DETECTED, not declared.** `web` / DOM (read via `getComputedStyle`) / later others. This is a fact of the feature's stack, read from the feature's package **stack metadata** (`PACKAGE_STACKS` / `/configure` / constitution — reusing existing stack metadata, NOT a new detector), NEVER a hand-declared field. You do not declare your build platform; it is a property of your stack. Only the READING of the rendered result is platform-specific.

These do not correlate: a Figma-selection intent can drive a web build; an HTML intent can drive a native build. The auditor engine is therefore an **intent-reader × built-reader** matrix (the intent side keyed on the declared `anchor.kind`, the built side keyed on the detected stack platform — see D17). Today exactly one cell is real:

| intent ↓ \ built → | `web` (DOM) | non-web |
|---|---|---|
| `html` | **IMPLEMENTED** (this plan) | NOT-COVERED |
| `figma` | NOT-COVERED (open schema slot) | NOT-COVERED |
| any other `kind` | NOT-COVERED | NOT-COVERED |

Schema-open, implementation-narrow: the schema anticipates every cell; this plan implements the `html`-intent × `web`-built cell and NOT-COVERS the rest generically.

### The anchor — a tagged (open-discriminator) variant

The `design_anchor` is a `kind`-tagged variant:

- `kind: "html"` → `{ file, selectors }` — export-based. Figma export, Claude Code, Claude Design, and chat-generated designs all export to HTML; HTML is the export common denominator. An export is a static snapshot → can go stale → needs a staleness guard (see the staleness decision). **IMPLEMENTED in this plan.**
- `kind: "figma"` → a live Figma MCP node / `currentSelection` — a live connection, staleness-free (always the current node, no snapshot to rot). **NOT implemented here** — an OPEN schema slot, NOT-COVERED until its reader is built. Rationale: the figma intent-reader must normalize real Figma node data into the comparator's value/geometry bag, and that shape cannot be defined correctly until read against a live MCP node — it drops into the ready slot as a fast-follow sibling plan, mirroring plan 52 D13's "second real consumer" discipline.
- **Open discriminator, NOT an enum.** The framework implements exactly `kind: "html"`; any other `kind` string is SHAPE-valid but resolves to NOT-COVERED at probe time, never a schema error that blocks the pipeline. Enumerate NO speculative kinds.

**Reuse (grounded):** `parse_design_source()` in `src/devforge/lib/_design/_source.py` already parses `html:<path>` / `figma:<url>` / `screenshot:<path>` / `none` into a `DesignSource(scheme, target, raw, valid)` namedtuple (`_KNOWN_SCHEMES = {html, figma, screenshot, none}`, `:48`). The anchor's `kind` + `file` ARE that `scheme` + `target`; the anchor only ADDS `selectors` (the intent elements, e.g. `.fooBar`). So the anchor is the structured UPGRADE of plan 43's existing flat `**Design source**:` field, not a parallel declaration.

### Anchor vs binding — the two-part split

The intent and the built-side wiring are two objects, authored at two times:

- **The anchor = INTENT: `{ kind, file, selectors }`.** Authored ONCE at intake, immutable after capture. It names WHAT the design intent is and WHICH source elements matter. It does NOT name built-side selectors — those don't exist at intake.
- **The binding = built-side wiring: `{ route, pairs: [{ anchor_selector, built_testid }], … }`.** Written LATER at `/breakdown`, references the anchor. Completes "where the feature renders + which built element corresponds to which intent element." The binding is the successor of plan 40's `design-manifest.json`.

"Declared once" holds for INTENT; the binding is a downstream COMPLETION, not a re-declaration.

### Propagation — park once, read in place (NOT carried through every handoff)

- **Capture:** at `/research` OR `/discover` via a NEW rubric dimension (design reference? kind? file? which selectors?). The captured anchor is written into the research/discover handoff as a new field in `SpecSeeds`.
- **One carry hop:** research/discover handoff → `/specify`. This hop is real because the intake report lives in `research/` / `discover/` (a different directory than the feature dir), and `/specify` is what CREATES `specs/[feature]/`. `/specify` records the anchor into the feature dir. If intake skipped capture, `/specify` is the BACKSTOP capture point — the gate that guarantees the anchor is persisted before `/plan`.
- **Persistence home of record:** `specs/[feature]/design-anchor.json` (structured, immutable after `/specify` writes it) PLUS plan 43's `**Design source**:` frontmatter line as the human-readable summary.
- **Read in place after that — NO further carry.** The anchor is NOT re-serialized into `plan-handoff.json` / `breakdown-handoff.json`. It is an immutable raw fact; re-carrying it through N handoffs = N desync points, violating single-source-of-truth. Every stage already reads the feature dir freely; the anchor is a sibling file they open.

**Consumers of the anchor:**

| Stage | Relationship to the anchor |
|---|---|
| plan | light passive read — shape the UI approach to match intent (wired by Phase 6) |
| breakdown | reads anchor, WRITES the binding (built-side `route` + selector pairs) as a sibling — the design-manifest successor |
| implement | the UI agent (`frontend-engineer` / `mobile-engineer`) reads anchor + binding, builds to intent |
| review | `design-auditor` reads anchor + binding + built app → compares source-vs-build (the fidelity gate) |
| verify | indirect — folds review's findings into the verdict (already does) |

### Correspondence — the binding is floor + opt-in pairs

- **Region floor (zero pairs, always present):** one container pair — anchor container ↔ built container. Compare the container's own box geometry + all INHERITED computed properties (font-family, color, line-height — children inherit unless they override). This is NOT vacuous: it catches the inherited-default class across every child for free (the most-omitted, most-dangerous class — the root-font drift lives here) plus container geometry/overflow. It only misses per-child OVERRIDDEN properties.
- **Pairwise (opt-in N pairs on top):** `{ anchor_selector ↔ built_testid }` per element whose per-element values matter — catches overridden-property drift. N is small in practice (design intent is usually a handful of elements).
- **Rejected middle path — structural auto-walk** (`nth-child` + tag parallel walk): this is plan 40 OQ-5's "fuzzy DOM matching," rejected then and rejected here — one extra wrapper div misaligns the walk → false correspondences. Human-declared pairs or nothing.
- **Selector asymmetry:** the anchor-side selector may be BRITTLE (a class) — the reference is a static file that never changes, so fragility is harmless. The built-side MUST be a stable testid — it points at living, refactored code. So: anchor selector = whatever matches the reference; built selector = a testid the engineer adds (normal practice).

### The auditor engine — intent-reader × built-reader × comparator

- **Intent reader** (keyed on `anchor.kind`): produces a normalized value+geometry bag for "what it should look like." `html` → render the anchor file in a headless browser + `getComputedStyle` / geometry on the anchor `selectors` (faithfully resolves the cascade — better than parsing CSS text). `figma` → NOT-COVERED (open slot). This SUBSUMES plan 52's "value source": `styles.css` was a stand-in intent reader that existed only because no anchor was captured — now it is an internal detail of the `html` reader (rendering the file loads its CSS), not a separate presence-gated layer.
- **Built reader / probe** (keyed on the built platform detected from stack metadata, D17): `web` → `getComputedStyle` + geometry on the built `route` + testid. Non-web → NOT-COVERED.
- **Comparator:** normalized-bag vs normalized-bag — `kind`- and platform-agnostic once both sides normalize.

### Two tiers of check — only one needs the anchor

- **Always-on sanity floor (anchor-FREE):** unintended horizontal overflow (`scrollWidth > clientWidth` AND computed `overflow-x ∈ {visible, hidden}`; exempt `auto` / `scroll`), clipping (child rect ⊄ parent rect AND parent `overflow ∈ {hidden, clip, auto}` AND child `position ∈ {static, relative}`; exempt `absolute` / `fixed`), and font-not-loaded. Self-evident defects — no reference needed. Runs even for features with NO anchor. Harvested verbatim-in-spirit from plan 52 Pass 1.
- **Anchor-gated fidelity (needs the anchor):** value fidelity (color / spacing / radius / typography / font-family — built computed vs anchor intent values) AND geometry fidelity (box dimensions / positions of corresponding elements, anchor-rendered vs built).

**Font-loaded is the ONE genuine special case:** a correctly-DECLARED-but-UNLOADED font renders a fallback while its declaration still matches, so a value-compare passes vacuously — it needs a LOAD check (`document.fonts.check('<size> <family>')` on the first QUOTED / custom family; SKIP generic / system keywords, which always resolve). Reference-free → lives in the always-on floor. Font-family value is otherwise just one more value in the bag — NOT special.

### Visual verification — three layers, split hard across the deterministic/advisory line

- **(b) computed-property + geometry-number diff → the deterministic CORE, GATES.** Precise, no tolerance-flake, machine-comparable. Catches everything expressible as a number: color, spacing, radius, font-family, and box geometry. Honest limit: cannot see holistic "looks wrong" (visual hierarchy, an in-bounds-but-swamped element, gestalt). This is the floor and it gates.
- **(a) raw pixel-diff as a gate → REJECTED.** Better than plan 52's retired app-level diff (isolated component, not full-app-mismatched-data) BUT the data-mismatch does not vanish — anchor shows mock content, build shows live data → text-length differences shift layout → pixels differ → needs a tolerance → flaky gate (the exact failure mode plan 52 retired screenshot-diff to escape). The layout signal is taken as GEOMETRY-NUMBER diff instead (deterministic). Screenshots are captured as EVIDENCE (feed the human + the VLM), never pixel-diffed as a gate.
- **(c) VLM pass → ADVISORY layer, NEVER gates.** A multimodal model over anchor-screenshot + built-screenshot catches the holistic "looks wrong" numbers miss. Feasible cheaply today (the `design-auditor` is already a dispatched, multimodal agent; two screenshots + one reasoning pass). Non-deterministic → sits OUTSIDE the honesty-guarantee core, emits "worth a human glance" notes, NEVER PASS / FAIL, clearly labeled advisory. A VLM that cries wolf gets ignored; one too quiet gives false comfort — so its output never gates the verdict and never gives false comfort.

Net: core = computed + geometry-number (gates); advisory = VLM (never gates); pixel-diff-as-gate = rejected.

## Honesty invariants — reframed around a PRESENT anchor

Non-vacuousness is STRUCTURAL (the always-on floor), not procedural — a check is emitted only when something real was actually compared; PASS never means "nothing was checked." The NOT-COVERED set (each loud, never a silent PASS, never a spurious FAIL), reframed from plan 52 around a first-class anchor:

1. **Chrome MCP absent** → NOT-COVERED (carried from plan 40 OQ-3 / plan 52 #1).
2. **`route` absent in the binding** → NOT-COVERED (never infer the screen — a misinferred route runs the deterministic probe on the wrong surface and returns clean: a correctly-checked, wrong-place false-green).
3. **Built `region_selector` / testid absent in the binding** → NOT-COVERED.
4. **Region not found / not mounted** → NOT-COVERED (loud, not clean, not a defect — absence ≠ overflow; isolate-first builds mount a component via its owner later).
5. **Anchor absent or malformed (no captured intent)** → the anchor-gated FIDELITY layer is NOT-COVERED, but the always-on SANITY FLOOR STILL runs.
6. **PASS is emittable ONLY when a probe actually executed against a FOUND region.**
7. **Platform mismatch** — the feature's built platform (DETECTED from stack metadata, D17) is non-web, OR the anchor's intent `kind` is unimplemented (e.g. `figma`) → NOT-COVERED, **evaluated FIRST (the outermost preflight)**, never PASS, never crash. (The built platform is read from the feature's stack metadata, NOT from any binding field — the binding schema is flat `{ route, pairs }`, see D17.)

The DEFECT findings (overflow / clip / font-not-loaded / value-mismatch / geometry-mismatch) are real failures against a found region, NOT NOT-COVERED conditions — only #1–#7 gate the coverage verdict.

**Known limitation carried verbatim from plan 52:** geometry reflects the RENDERED state — an empty / seed-less app can hide a data-dependent geometry defect (false-negative). The report must note that a green geometry on sparse data means "didn't overflow on THIS data," not "layout safe," and recommend a representative seed for data-dependent layouts.

## HARVEST vs LEAVE-BEHIND

**HARVEST from plan 52** (still valid; absorbed):
- The honesty invariants (NOT-COVERED vs PASS vs FAIL; non-vacuousness by construction).
- The deterministic-probe discipline (the machine computes / compares, the LLM orchestrates / reports, never eyeballs geometry).
- The always-on geometry sanity floor (overflow / clip / font-not-loaded).
- The seed-dependency limitation note.

**LEAVE BEHIND** (discard — these existed only to compensate for the missing input):
- The `data-ref` manifest assumptions.
- Route-INFERENCE (the route now comes from the binding; still never inferred).
- Platform-name enumeration.
- The assumption that intent must be RE-DECLARED at review (with a first-class anchor, review READS the anchor).
- Plan 52's "value source proxy" as a standalone presence-gated layer (subsumed into the `html` intent reader — rendering the anchor file loads its CSS).
- Plan 52 D11's "no automated check reads the reference" narrowing — **REVERSED** (see D12): the anchor's human-provided selector lets the intent reader read the actual design source directly again. This reversal is the key improvement over plan 52.

## Settled decisions (all ratified this session)

- **D1 — Design intent is a first-class pipeline input (the `design_anchor`).** A structured object captured once at intake and read by every downstream stage, replacing per-stage re-derivation from prose / re-inference from built code. Capture-first, verify-follows: gap #2 (verification) falls out of gap #1 (capture) — half of plan 52's machinery existed only to reconstruct the uncaptured input.
- **D2 — Two INDEPENDENT axes: source of intent (the DECLARED anchor `kind`) × platform of the built UI (DETECTED from stack metadata, D17).** They do not correlate, and they are ASYMMETRIC in source — intent is a declared tagged field on the anchor, platform is a detected fact of the feature's stack (never a shared field, never a declared platform field — see D17). The auditor engine is an intent-reader × built-reader matrix; today exactly one cell (`html` × `web`) is implemented, the rest NOT-COVERED generically. Schema-open, implementation-narrow.
- **D3 — The anchor is a tagged, OPEN-discriminator variant.** `kind: "html"` → `{ file, selectors }` is implemented; any other `kind` string is SHAPE-valid but NOT-COVERED at probe time, never a pipeline-blocking schema error. Enumerate no speculative kinds.
- **D4 — Anchor vs binding, a two-part split.** The anchor = INTENT `{ kind, file, selectors }`, authored once, immutable after capture. The binding = built-side wiring `{ route, pairs: [{ anchor_selector, built_testid }] }`, written later at `/breakdown`, referencing the anchor. "Declared once" holds for INTENT; the binding is a downstream completion, not a re-declaration. The binding is plan 40's `design-manifest.json` successor.
- **D5 — Park once, read in place.** Capture at `/research` / `/discover` (new rubric dimension → `SpecSeeds` field); ONE carry hop research/discover-handoff → `/specify`; `/specify` writes the anchor into the feature dir and is the backstop capture point. After that, every stage reads the sibling `design-anchor.json` directly — the anchor is NOT re-serialized into `plan-handoff.json` / `breakdown-handoff.json` (re-carrying an immutable fact through N handoffs = N desync points; single-source-of-truth forbids it).
- **D6 — Persistence home of record: `specs/[feature]/design-anchor.json`** (structured, immutable after `/specify` writes it) PLUS plan 43's `**Design source**:` frontmatter line as the human-readable summary. `/specify` is the gate that guarantees the anchor is persisted before `/plan`.
- **D7 — Correspondence = region floor + opt-in pairs; structural auto-walk rejected; selector asymmetry.** The floor is one always-present container pair (container box geometry + inherited computed properties — catches the inherited-default class across every child, incl. root-font drift). Opt-in N pairwise `{ anchor_selector ↔ built_testid }` bindings catch overridden-property drift. Structural `nth-child` + tag auto-walk is rejected (plan 40 OQ-5's fuzzy matching — one wrapper div misaligns the walk). The anchor-side selector may be brittle (static reference); the built-side MUST be a stable testid (living code).
- **D8 — The auditor engine is intent-reader × built-reader × comparator.** The intent reader (keyed on the declared `anchor.kind`) and the built reader (keyed on the built platform detected from stack metadata, D17) each normalize their side into a value + geometry bag; the comparator diffs bag-vs-bag, `kind`- and platform-agnostic. The `html` intent reader renders the anchor file in a headless browser and reads `getComputedStyle` / geometry — subsuming plan 52's separate `styles.css` value source.
- **D9 — Two tiers of check; only one needs the anchor.** An always-on sanity floor (anchor-FREE: overflow / clip / font-not-loaded — runs even with no anchor) + an anchor-gated fidelity layer (value + geometry fidelity against the captured intent). Non-vacuousness is structural (the floor always runs), not procedural.
- **D10 — Font-loaded is the ONE genuine special case.** A declared-but-unloaded font renders a fallback while its declaration still matches, so a value-compare passes vacuously; a `document.fonts.check()` LOAD check (first quoted / custom family; skip generics) lives in the anchor-free floor. Font-family VALUE is otherwise one more value in the bag — not special.
- **D11 — Visual verification splits hard across the deterministic/advisory line.** (b) computed-property + geometry-NUMBER diff is the deterministic core and GATES; (a) raw pixel-diff-as-a-gate is REJECTED (mock-vs-live-data noise → tolerance → flake — the layout signal is taken as geometry-number diff instead; screenshots are evidence only); (c) a VLM pass over the two screenshots is ADVISORY, emits "worth a human glance" notes, and NEVER gates.
- **D12 — REVERSAL of plan 52 D11: the intent reader reads the actual design source directly again.** Plan 52 narrowed value-fidelity to trust a declared value source (`styles.css` / `contract.md`) as a proxy because no anchor named the reference elements; the captured anchor's human-provided `selectors` restore direct reading of the design source (render the `html` file, read computed style on the named selectors). This is the key improvement over plan 52 and is recorded as an explicit reversal so a future session does not reinstate the D11 narrowing. `src/constitution.md` §3.8 is reworded to state it (Phase 8).
- **D13 — Staleness, recorded honestly.** For `kind: html`, the guard can ONLY detect an intra-repo edit (the anchor file changed since `/specify` captured it — a content-hash re-confirm signal); it CANNOT detect export-vs-live drift (the framework has no Figma source behind an HTML export). So html staleness = a re-confirm signal, NOT a freshness guarantee; where undetectable it is an honest NOT-COVERED, never oversold as "guarded." For `kind: figma`, a live MCP read is staleness-free by construction (relevant only when the figma reader is built — a property of the fast-follow).
- **D14 — The anchor is the structured upgrade of plan 43's flat `**Design source**:` field.** The anchor's `kind` + `file` REUSE `parse_design_source()`'s `scheme` + `target`; the anchor only ADDS `selectors` and the `design-anchor.json` persistence. The frontmatter line stays as the human summary; plan 43's declare-and-warn is absorbed, not duplicated.
- **D15 — The figma intent reader is a fast-follow SIBLING plan (open `kind`, no other platform named).** The `figma` slot is schema-open and NOT-COVERED here; its reader normalizes live Figma node data into the comparator's bag, a shape definable only against a live MCP node — a new reader against the same engine, mirroring plan 52 D13's "second real consumer" discipline. Name no concrete platform beyond `figma`.
- **D16 — This plan SUPERSEDES plan 52.** Plan 52 (NOT STARTED) is absorbed (HARVEST list) and retired (LEAVE-BEHIND list); Phase 8 adds a supersede back-pointer and moves plan 52 toward done-plans framing.
- **D17 — Platform is DETECTED from stack metadata, not declared; intent `kind` is DECLARED on the anchor.** The two axes (D2) are ASYMMETRIC in SOURCE. The **intent axis** (`anchor.kind` = `html` / `figma` / …) is an EXPLICIT tagged field ON THE ANCHOR — you declare your design source. The **platform axis** (`web` / non-web) is a DETECTED discriminator read from the feature's package **stack metadata** (`PACKAGE_STACKS` / `/configure` / constitution), per-feature/package — NOT a declared field, and NOT a new detector: it reuses the SAME existing stack metadata the rest of the framework already reads (exactly the reuse-not-invent stance plan 52's honesty invariant #7 took). You do not declare your build platform; it is a fact of your stack. Consequently the binding schema stays FLAT — `{ route, pairs }` (D4/D7) — with NO `kind` / `target` / `platform` field; the built platform is never a binding value. **Rejected alternative:** adding a declared `platform` field to the binding (or an anchor `target.kind`) — rejected because it would make someone hand-declare a fact the stack already encodes (redundant, drift-prone: a hand-declared platform can disagree with the actual stack). The outermost preflight (honesty #7) evaluates this DETECTED platform FIRST; Phase 6's `design-auditor` rewrite resolves it from stack metadata, not from a binding field. Referenced by D2, honesty invariant #7, and Phase 6.

## Open questions (carried to build)

- **OQ-A — JS-probe test toolchain (carried from plan 52 OQ-A).** The framework repo has no JS test infra today. Phase 4's deterministic probe needs an automated DOM-level test so "deterministic, not LLM-judgment" is verified, not asserted. Options: (a) a jsdom / node unit test (adds a node dev-dependency to a Python framework); (b) a headless-browser smoke (closer to the real `evaluate_script` environment, heavier). The geometry math is jsdom-unit-testable; the `document.fonts.check()` font-load check is inherently a REAL-render check (jsdom has no font loading, so a jsdom "pass" there is meaningless), pushing the font portion toward (b). Decide at Phase 4 start. Both the intent reader (render the anchor file) and the built reader need a real-render arm, which strengthens the case for (b) over plan 52's geometry-only framing.
- **OQ-B — The VLM advisory's exact home and labeling in `design-auditor.md`.** Whether the advisory VLM notes live in a dedicated `## Advisory (non-gating)` report subsection or an inline `[ADVISORY]`-tagged block, and the exact wording that makes "this NEVER gates the verdict" unmissable to a reader. Resolve at Phase 6 with `instruction-reviewer` + `claude-code-guide`.
- **OQ-C — Anchor-`file` staleness signal home (D13).** Whether the html content-hash re-confirm signal is computed by `/specify` at capture and stored in `design-anchor.json`, or recomputed by the `design-auditor` at read time. Resolve at Phase 2 (the persistence phase) — it decides whether the anchor schema carries a `source_hash` field.

## Phase 0 — Maintainer build sign-off (GATE — no code)

The mechanism + all decisions above were ratified in the 2026-07-06 design session. Phase 0 is the checkpoint before build: confirm the phase breakdown, the build loops, the retire-list, and the supersede-of-52. NO build until signed off.

**Verify:** maintainer confirms phases 1–9, the build loops, the retire-list, and that plan 52 is superseded (not run in parallel); no scope drift from the ratified design.

## Phase 1 — Anchor schema + capture at `/research` and `/discover`

Built via **python-engineer → python-reviewer** (test-first; parser round-trips via the real producer where one exists) for the helpers, **+ instruction-author → instruction-reviewer + claude-code-guide** for the `/research` + `/discover` `main.md` rubric edits (they ship into `.claude/`).

- Define a new `design_anchor` dataclass `{ kind: str, file: str, selectors: list[str] }` (a nested record; `kind` an OPEN discriminator per D3 — any string SHAPE-valid). Add it as a typed `design_anchor` field to the `SpecSeeds` of ALL THREE handoff schemas: research (`src/devforge/lib/_research/handoff_schema.py`), discover (`src/devforge/lib/_discover/handoff_schema.py`, `HANDOFF_KIND="discover"`), and specify (`src/devforge/lib/_specify/handoff_schema.py`, `SpecSeeds` at `:278` — verified today to carry exactly 8 fields and NO design field, so the field is net-new). Append it last / default-empty so an old handoff without it deserializes to an empty anchor (back-compat, the honest pair: old-JSON → default + current-producer-stable, no impossible byte-identity claim).
- Reuse `parse_design_source()` (`_design/_source.py`) to derive `kind` + `file` from the `scheme:target` shape; the anchor ADDS the `selectors` list.
- Add ONE new rubric dimension (design reference: kind? file? which selectors?) + its setter to `/research` (the 6-dimension rubric at `src/commands/research/main.md:144-154`, setters listed `:182-187`, invoked as `.devforge/lib/research_helper set-<dim> --value … --state <state>`) AND to `/discover` (the 8-dimension rubric at `src/commands/discover/main.md:162-174`, `discover_helper set-scope-<dim>`), following the exact existing setter pattern.

**Verify:** unit tests — the `design_anchor` dataclass validates `{kind, file, selectors}` (empty default deserializes clean; a non-`html` kind string is shape-valid); an old handoff JSON without the field deserializes to an empty anchor; a round-trip through the real handoff producer preserves a captured anchor. `instruction-reviewer` + `claude-code-guide` clean on the `/research` + `/discover` rubric edits; the new dimension + setter follow the existing pattern; the setter name appears in the `main.md` setter list and nowhere stale.

## Phase 2 — Carry + persist: `/specify` records the anchor into the feature dir

Built via **python-engineer → python-reviewer** (the carry helper) **+ instruction-author → instruction-reviewer + claude-code-guide** (`src/commands/specify/main.md`).

- Carry `design_anchor` across the ONE hop: `cmd_import_handoff` (`src/devforge/lib/_specify/_cmds_handoff.py:372-429`) today pre-seeds a SPECIFIC field list (constraints / affected_areas / risks / open_questions), so carrying `design_anchor` needs an EXPLICIT new line here — it is NOT automatic. `/specify` Phase 0.4 (`src/commands/specify/main.md:96-118`) is where the handoff is imported; `find-handoffs` is at `_cmds_handoff.py:707-857`.
- `/specify` writes `specs/[feature]/design-anchor.json` (structured, immutable after this write — D6) and keeps the `**Design source**:` frontmatter summary (plan 43's field, `render_spec` emits it at `src/devforge/lib/_specify/_render.py:134`, `DESIGN_SOURCE_DEFAULT="none"`; setter `cmd_set_design_source` at `src/devforge/lib/_specify/_cmds_phase4_setters.py:560-583`, validator `_validate_design_source` `:512-557`).
- **Backstop capture:** if intake skipped capture (empty `design_anchor` in the handoff) but the user declares a design source at `/specify` (via the existing `set-design-source`), `/specify` composes the anchor from that declaration — the gate that guarantees the anchor is persisted before `/plan`.
- Resolve OQ-C here: decide whether `design-anchor.json` carries a `source_hash` field for the D13 html re-confirm signal.

**Verify:** unit tests — `cmd_import_handoff` carries a captured `design_anchor` into the specify state (round-tripped through the real research/discover producer, not hand-authored JSON); an intake with no anchor + a `/specify` design-source declaration yields a composed anchor (backstop); `design-anchor.json` is written with the `{kind, file, selectors}` shape and the frontmatter summary stays in lockstep. `instruction-reviewer` + `claude-code-guide` clean on `specify/main.md`; cross-ref sweep of the new anchor path.

## Phase 3 — Reframe `_design/` schema → anchor + binding

Built via **python-engineer → python-reviewer** (test-first).

- RETIRE the `data-ref` / disposition schema in `src/devforge/lib/_design/_schema.py`: `ElementRecord` (slots `data_ref` / `disposition` / `deviate_reason`), the `DISPOSITION_*` constants + `VALID_DISPOSITIONS`, and the `ManifestContainer`'s element/gap-list shape. RETIRE the `data-ref` HTML-anchor extraction in `_reference.py`: the `_DataRefCollector` (HTMLParser subclass), `resolve_reference()`, and the `resolve-reference` CLI verb.
- **KEEP the shared CSS-parse utilities** — `_CSS_DECL_RE` (`_reference.py:139`), `_extract_rule_blocks` (`:153-206`), `_parse_css_rules` (`:209-250`) — because `_manifest.py::extract_spacing_scale` (`:238-257`, kept) and `_constitute/_forcing_functions/_design_tokens/_cmd.py` (Checks 1–4's token-source path) import them. Do NOT delete `_reference.py` wholesale; relocate the utils to a new `_css_parse.py` only if cleaner. KEEP `extract_spacing_scale` and `parse_design_source`.
- Define the NEW binding schema `{ route: str, pairs: [{ anchor_selector: str, built_testid: str }] }` (D4/D7 — the container floor is one always-present pair; opt-in pairs on top). Reframe `init-manifest` / `validate-manifest` to the binding, exposed as Phase 3's `validate-binding` verb (naming: reuse or rename the existing verbs — decide in the loop): route required, ≥1 container pair required, empty binding → exit non-zero (the intake escalation, honesty #3).

**Verify:** unit tests — a binding with a `route` + ≥1 container pair → exit 0; a binding missing `route` → exit non-zero naming the field; a binding with zero pairs → exit non-zero; the old `data-ref` fixtures no longer parse (their code paths are gone). `extract_spacing_scale` still imports and its existing tests stay green (the retained CSS utils are not collateral-damaged); `_design_tokens/_cmd.py` still imports; no `data-ref` / `ElementRecord` / `disposition` symbol remains in `_design/`.

**Ordering note — HARD CO-REQUISITE with Phase 7's `/breakdown` caller edit (plan-42 failure class).** `/breakdown`'s `main.md` LITERALLY calls `.devforge/lib/design_helper resolve-reference` / `init-manifest` / `validate-manifest` at `src/commands/breakdown/main.md:278,290,298,301,319` (verified live). This phase RETIRES the `resolve-reference` verb + the `ElementRecord` / `data-ref` schema those calls depend on. So Phase 3's verb/schema retirement and Phase 7's retirement of those `/breakdown` `main.md` call sites MUST land in the SAME build increment; in practice, pull Phase 7's `/breakdown` caller edit forward to accompany Phase 3 if the phases are otherwise built separately. They CANNOT be split across increments: retiring the verb while a live `main.md` caller still invokes it makes a real `/breakdown` on a `design/reference.html` feature call a DELETED verb — a hard CLI failure, not a graceful NOT-COVERED. (Distinct from the Phase 6/7 consumer-before-producer ordering, which IS split-safe because a missing binding degrades to NOT-COVERED.)

## Phase 4 — The deterministic probe: html intent-reader + web built-reader + comparator

Built via **python-engineer → python-reviewer** (the Python validator is test-first) **+ an automated DOM-level probe test** (the probe's own logic is tested, per OQ-A — NOT deferred to the e2e phase).

- Ship the **html intent-reader** as a JS `evaluate_script` asset under `_design/`: render the anchor `file` in a headless browser, read `getComputedStyle` + geometry on the anchor `selectors`, return a normalized value + geometry bag.
- Ship the **web built-reader** as an `evaluate_script` asset: navigate the `route`, read `getComputedStyle` + geometry on the built testid, return the same-shape bag. `region_found: false` when the selector matches nothing (honesty #4).
- Ship the **comparator + structured-output validator** (Python, in `_design/`): diff intent-bag vs built-bag, map differences to design-fidelity findings via the `src/devforge/lib/_shared/` finding substrate, map `region_found: false` → NOT-COVERED (distinct from "found, zero differences" = a real clean check). The finding shape is **platform-agnostic by construction** (it aligns with the `_shared/` finding substrate), so any future built-side reader emits the same shape. (Note: a hypothetical future NON-WEB BUILT/platform reader is NOT addressed by any current decision — it is distinct from D15, which governs the figma INTENT reader on the other axis; do not mis-cite D15 for platform-reader work.)
- Carry OQ-A here: decide the JS-test toolchain (jsdom vs headless-browser). Both readers RENDER (the intent reader renders the anchor file; the built reader renders the app), and the font-load check needs a real-render arm.

**Verify:** unit tests on the comparator — `region_found:false` → NOT-COVERED (not PASS, not FAIL); `region_found:true` + zero differences → PASS; value / geometry differences → mapped `_shared/` findings; malformed probe output → loud error, not silent pass. **AND a minimal automated DOM-level test exercises the readers' real logic against synthetic fixtures** so the "deterministic, not LLM-judgment" guarantee is verified, not asserted. The JS-test toolchain decision is recorded here (OQ-A); the font-load check's real verification is a headless-browser arm, not a jsdom unit test (jsdom cannot load fonts). Full in-app browser execution stays at Phase 9.

## Phase 5 — The check set: always-on floor + anchor-gated fidelity

Built via **python-engineer → python-reviewer** (test-first).

- Build the **always-on sanity floor** (anchor-FREE, D9/D10): unintended horizontal overflow (`scrollWidth > clientWidth` AND `overflow-x ∈ {visible, hidden}`; exempt `auto` / `scroll`), clipping (child rect ⊄ parent rect AND parent `overflow ∈ {hidden, clip, auto}` AND child `position ∈ {static, relative}`; exempt `absolute` / `fixed`), and font-not-loaded (`document.fonts.check()` on the first quoted / custom family; skip generics). Runs even for a feature with NO anchor.
- Build the **anchor-gated fidelity** checks (D9): value fidelity (color / spacing / radius / typography / font-family — built computed vs anchor intent) + geometry-number fidelity (box dimensions / positions, anchor-rendered vs built).
- Map every check's output → the `_shared/` finding shape (single source of finding structure, reused from Phase 4's comparator).

**Verify:** unit tests — an overflowing div (`overflow-x:visible`) flags; a legitimate `overflow-x:auto` scroll container does NOT flag; an `absolute`-positioned escapee out of a clipping parent does NOT flag; a `static` child clipped by an `overflow:hidden` parent flags; a declared-but-unloaded quoted family flags `font-not-loaded` while a value-compare passes vacuously (proving the D10 special case); a value / geometry mismatch against a captured anchor flags; a feature with NO anchor still runs the floor and can PASS or flag on the floor alone (proving D9's structural non-vacuousness).

## Phase 6 — Rewire `design-auditor` + `/review` + `/plan` anchor read

Built via **instruction-author → instruction-reviewer + claude-code-guide** (ships into `.claude/`).

- Rewrite `design-auditor.md` `## Approach` (`:23-40`) to the intent-reader × built-reader × comparator engine: **(0) platform preflight (honesty #7, OUTERMOST — before Chrome MCP): resolve the feature's built platform from its stack metadata (`PACKAGE_STACKS` / `/configure` / constitution — the existing mechanism, D17, NOT a binding field and NOT a new detector); if that platform is non-web, or the anchor's intent `kind` is unimplemented (e.g. `figma`), report NOT-COVERED + STOP;** (1) read the anchor (`specs/[feature]/design-anchor.json`) + the binding; (2) honesty preflight (Chrome MCP present? route present? region found? anchor present-and-valid?) — each miss → its NOT-COVERED per #1–#6; (3) run the always-on sanity floor (overflow / clip / font-not-loaded); (4) run the anchor-gated value + geometry fidelity when the anchor is present, else declare that layer NOT-COVERED while the floor still ran (#5); (5) emit the verdict under the 7 honesty invariants + the seed-dependency limitation note.
- Add the **VLM advisory layer** clearly labeled non-gating (resolve OQ-B here): a multimodal pass over the anchor-screenshot + built-screenshot emitting "worth a human glance" notes, in a report section that makes "this NEVER gates the verdict" unmissable.
- Reword **Rule 5** (`design-auditor.md:91`, "every in-scope element must match the reference 1:1") from the retired per-element disposition framing to the anchor + binding framing: floor + opt-in pairwise comparison, no per-element MATCH / DEFER-EMPTY / STATIC-PLACEHOLDER / DEVIATE disposition. A binding lacking a `route` (or absent) resolves to NOT-COVERED, not a clean skip.
- RETIRE the screenshot-DIFF + `data-ref` MATCH/disposition mechanism from `## Approach` step 1's "hybrid" framing (`:27-35`). Keep the structured `CHROME_MCP_AVAILABLE` probe (Rule 1) as honesty invariant #1. Screenshots stay ONLY as VLM / human evidence, never as a pixel-diff gate.
- **Producer alignment:** `src/agents/frontend-engineer.md` + `src/agents/mobile-engineer.md` instruct per-element `data-ref` anchoring for the retired model. REPLACE both with: carry the binding's built testid on the containing REGION (not per-element). `mobile-engineer.md` paraphrases without the literal `data-ref`, so edit it BY NAME (a keyword sweep cannot find it).
- `/review` PHASE 2.5 already dispatches `design-auditor`; update the dispatch to reference the anchor + binding (no new dispatch site). Update plan 42's tripwire condition text (`reference.html`-present ∧ manifest-absent) to the anchor + binding equivalent.
- **`/plan` light passive read (wires the consumers-table `plan` row — no orphaned declaration):** `/plan`'s `main.md` gains a light passive read — when `specs/[feature]/design-anchor.json` is present, `/plan` notes the captured design intent (`kind` + which `selectors` matter) so it shapes the UI approach to match that intent. Passive and read-only: `/plan` does NOT write the binding (that is `/breakdown`, D4), does NOT re-serialize the anchor into `plan-handoff.json` (D5 park-once, read-in-place), and no-ops silently when the sibling anchor is absent. **Placed in Phase 6** (not Phase 8): this is an active `main.md` consumer wiring through the same instruction-author → instruction-reviewer + claude-code-guide loop as the `design-auditor` / `/review` edits here — grouping it with the other consumer wiring — and its only dependency (the anchor persisted at `specs/[feature]/design-anchor.json`) is satisfied by Phase 2, so it does not force a later phase; Phase 8 is a docs-reconcile phase and a behavioral consumer edit does not belong there.

**Verify:** `instruction-reviewer` + `claude-code-guide` clean; `design-auditor.md` no longer references `data-ref`, screenshot-diff, `eyeball`, per-element `1:1` disposition, or MATCH/DEFER-EMPTY/STATIC-PLACEHOLDER/DEVIATE; the 7 honesty invariants (incl. #7 outermost, resolving the built platform from stack metadata per D17 — not from a binding field) + the VLM advisory-non-gating labeling + the seed-limitation note are present; `frontend-engineer.md` + `mobile-engineer.md` no longer instruct per-element anchoring (`grep data-ref src/agents/` = 0 AND `mobile-engineer.md`'s paraphrase gone by direct read); `/plan` `main.md` references the sibling `specs/[feature]/design-anchor.json` as a light passive read (present ⇒ noted, absent ⇒ silent no-op), `instruction-reviewer` + `claude-code-guide` clean (it ships into `.claude/`); all three agents stay conformant to `src/agents-AUTHORING.md`; cross-ref sweep of `design-auditor` / binding verb names clean. **Ordering note:** this phase's `design-auditor` consumes the binding that `/breakdown` only starts PRODUCING in Phase 7 — the consumer lands before the producer. This is acceptable because a missing binding degrades gracefully to NOT-COVERED (honesty #2/#3), never a broken state; a maintainer preferring producer-before-consumer may swap Phases 6 and 7.

## Phase 7 — Static gate reconcile + `/breakdown` produces the binding

Built via **python-engineer → python-reviewer** (`_design_tokens` + `verify-manifest-present`) **+ instruction-author → instruction-reviewer + claude-code-guide** (`/breakdown` `main.md`).

- RETIRE Check 5 (MATCH token-binding) in `src/devforge/lib/_constitute/_forcing_functions/_design_tokens/` — the only manifest-dependent check (it was a `data-ref` proxy) — and its `specs/*/design-manifest.json` glob. KEEP Checks 1–4 (no hardcoded hex / rgb / hsl / named colors; no `var(--x,<literal>)` fallbacks; undefined-token-fails-loud; `:hover` + `:focus-visible`) — manifest-independent, untouched. Orphan-cleanup: remove any `spacing_scale_available` computation left dead once Check 5 is gone, UNLESS a retained reader still uses it.
- `/breakdown` PHASE 2.5: produce the BINDING (`route` + ≥1 container pair), not a `data-ref` disposition manifest. This RETIRES the live `design_helper resolve-reference` / `init-manifest` / `validate-manifest` call sites at `src/commands/breakdown/main.md:278,290,298,301,319` and repoints them at the Phase 3 `validate-binding` verb. **This `/breakdown` `main.md` caller edit is a HARD CO-REQUISITE with Phase 3's verb/schema retirement — see Phase 3's Ordering note: the two MUST land in the same build increment; in practice, pull this caller edit forward to accompany Phase 3 if the phases are otherwise built separately, because retiring the verb while these call sites still invoke it breaks `/breakdown`.** The reference-present detect (plan 42 D4, `test -f design/reference.html`) stays; on reference-present, an empty / invalid binding HARD-halts intake and escalates to the user (honesty #3) BEFORE any code is written.
- Retarget `breakdown_helper verify-manifest-present` (plan 42): reference-present ⇒ a valid BINDING present (route + ≥1 container pair), replacing the old present-and-non-empty-`data-ref` assertion. Keep it as the PHASE 3.5 integrity gate + the `finalize-handoff` chokepoint (its plan-42 shape: shared predicate, two call sites, HARD-halt no bypass).

**Verify:** unit tests — Checks 1–4 fire exactly as before (hardcoded hex → non-zero; `var(--x,#fff)` → non-zero; undefined token → fail-loud; missing `:focus-visible` → fail); no manifest glob remains in `_design_tokens`; reference-present + valid binding → `verify-manifest-present` exit 0; reference-present + empty binding → HARD halt naming the gap; reference-absent → skip (unchanged); the gate fires at PHASE 3.5 and folds into `finalize-handoff`. `instruction-reviewer` + `claude-code-guide` clean on `/breakdown` `main.md`; cross-ref sweep of the verb name.

## Phase 8 — Docs reconcile + supersede plan 52

Built via **instruction-author → instruction-reviewer + claude-code-guide** (`src/constitution.md` — it ships as a consumer template, same authoring bar as agent files) **+ python-engineer → python-reviewer** (any emitter / install / test change) **+ direct edits** (repo-internal docs).

- Rewrite `src/constitution.md` §3.8 Design Fidelity: currently asserts "match the reference 1:1" per-element — reword to the anchor-driven two-tier mechanism (always-on floor + anchor-gated fidelity), stating that value-fidelity now reads the ACTUAL anchor source via the intent reader — i.e. the D12 REVERSAL of plan 52 D11 (the automated check reads the reference again). Edit by name (a keyword sweep does not catch §3.8).
- Supersede plan 52: add a `Status: SUPERSEDED BY 53` back-pointer in `52-DESIGN-FIDELITY-WEB-PROBE-PLAN.md` and move it toward done-plans framing (do not run 52 in parallel). Add a supersede-of-52 note in this plan's repo-root `CLAUDE.md` plan-list entry.
- Retarget plan 42 notes (`verify-manifest-present` now asserts a valid BINDING, not a `data-ref` manifest) and absorb plan 43 (its flat `**Design source**:` field is now the anchor's human summary — D14).
- Reconcile the repo-root `CLAUDE.md` "Where to find what" design-fidelity row + this plan-list entry, `CHANGELOG.md`, and `src/CLAUDE.md` (the `/specify`, `/breakdown`, `/review` catalog entries + the design-fidelity awareness). Name the **figma fast-follow SIBLING plan** (D15) in the "Where to find what" row: a figma intent reader is a NEW reader against the same engine + open `kind`, named now so a future session builds it against the shared comparator rather than forking; name no concrete platform beyond `figma`.
- Cross-ref sweep across `src/`: `data-ref`, `resolve-reference`, screenshot-as-a-fidelity-mechanism, `in-scope element`, `match_refs`, per-element disposition — confirm no dangling reference and no site still asserting the retired mechanism as the fidelity path. The sweep is a backstop, NOT the primary retire mechanism — the grep-invisible sites (`mobile-engineer.md`'s paraphrase in Phase 6, `constitution.md` §3.8 here) are edited by name.

**Verify:** docs read coherently against the shipped behaviour; `src/constitution.md` §3.8 no longer asserts reference-1:1 and names the two-tier mechanism + the D12 reversal (`instruction-reviewer` + `claude-code-guide` clean); the plan 52 supersede back-pointer + the plan 42/43 retarget/absorb notes land; the figma sibling plan is named (open `kind`); cross-ref sweep clean; `test_generate_agents` + the full suite green.

## Phase 9 — Consumer / testForge20 / mintEnvoy e2e (user-driven HARD GATE)

The live reproduction is mintEnvoy (a real HTML export + real observed drift). Confirm end-to-end:

- The anchor is captured at intake (`/research` or `/discover` new rubric dimension), carried across the one hop, and persisted to `specs/[feature]/design-anchor.json` by `/specify` (with the backstop path exercised on an intake that skipped capture).
- The binding is produced at `/breakdown` (route + container floor pair); `verify-manifest-present` HARD-halts a reference-present feature with an empty binding.
- The `design-auditor` reads anchor + binding + the built app and compares source-vs-build: real findings, a clean-on-found-region PASS, or a loud NOT-COVERED — never a vacuous PASS.
- NOT-COVERED fires on each honesty condition exercised (Chrome MCP absent, route absent, region not mounted, anchor absent, platform mismatch).
- The VLM advisory appears clearly labeled non-gating.
- The always-on floor runs on a feature with NO anchor (geometry-only), proving the structural non-vacuousness (D9).

**Verify:** all e2e checks pass; no vacuous PASS reproducible; NOT-COVERED fires on each honesty-invariant condition; the VLM advisory is present and clearly non-gating; the previously font-drifted mintEnvoy feature now surfaces the drift (font-family value mismatch or font-not-loaded) instead of a green gate.

## Context for next session

- Design fully ratified 2026-07-06 (this session). The load-bearing idea: **design intent is a first-class pipeline input (the `design_anchor`)**, captured ONCE at intake and read in place by every downstream stage — capture-first (gap #1), verify-follows (gap #2 falls out of #1). This SUPERSEDES plan 52, which built machinery to reconstruct the input that was never captured.
- Two INDEPENDENT axes (D2), ASYMMETRIC in source (D17): the DECLARED anchor `kind` (source of intent — `html` implemented, `figma` open) × the built platform DETECTED from stack metadata (built UI — `web` implemented; never a declared field). They do not correlate; the engine is intent-reader × built-reader × comparator, with exactly one real cell today (`html` × `web`).
- Anchor vs binding (D4): the anchor is immutable INTENT `{kind, file, selectors}` (persisted `specs/[feature]/design-anchor.json` by `/specify`); the binding is built-side wiring `{route, pairs}` written at `/breakdown` (the `design-manifest.json` successor). The anchor is NOT re-serialized through handoffs (D5 park-once, read-in-place).
- Two check tiers (D9): an anchor-FREE always-on sanity floor (overflow / clip / font-not-loaded — D10) + an anchor-gated fidelity layer (value + geometry). Non-vacuousness is STRUCTURAL (the floor always runs), guarded by the 7 honesty invariants (#7 platform-mismatch is the outermost preflight).
- Visual split (D11): computed + geometry-NUMBER diff GATES; pixel-diff-as-gate is REJECTED (mock-vs-live noise); the VLM pass is ADVISORY and NEVER gates.
- The key improvement over plan 52 is D12: the intent reader reads the actual design source directly again (reversing plan 52 D11) because the anchor's human-provided `selectors` name the reference elements.
- Grounded reuse: `parse_design_source()` (`_design/_source.py`) supplies `kind` + `file`; the specify `SpecSeeds` (`_specify/handoff_schema.py:278`) has 8 fields today and gains `design_anchor`; `_design/_schema.py`'s `ElementRecord` / disposition / `ManifestContainer` are retired, the CSS-parse utils + `extract_spacing_scale` kept.

## When resuming work

1. Confirm Phase 0 sign-off (or get it). Do NOT build before sign-off, and do NOT run plan 52 — this supersedes it.
2. Re-read this plan in full — it encodes multi-turn design context (the two axes, the anchor/binding split, park-once propagation, the two check tiers, the visual split, the 7 honesty invariants, the retire-list) not in the conversation.
3. Build phases 1→8 in order; each names its loop (python-engineer→python-reviewer for helpers / probe / validator, test-first; instruction-author→instruction-reviewer+claude-code-guide for `/research` / `/discover` / `/specify` / `design-auditor.md` / `/plan` `main.md` / `/breakdown` `main.md` and `src/constitution.md`). Note the Phase 6/7 consumer-before-producer ordering (graceful-degrade to NOT-COVERED; swappable). **HARD CO-REQUISITE (NOT swappable, NOT split-safe):** Phase 3's `resolve-reference` verb/schema retirement and Phase 7's retirement of the `/breakdown` `main.md` call sites (`breakdown/main.md:278,290,298,301,319`) MUST land in the SAME build increment — retiring the verb while the live caller still invokes it breaks `/breakdown` (a deleted-verb CLI failure). If you split phases across increments, pull Phase 7's `/breakdown` caller edit forward to accompany Phase 3.
4. Phase 9 (e2e) is the user-driven HARD GATE — mintEnvoy is the live reproduction.
5. The figma intent reader (D15) is a future SIBLING plan against the same engine + open `kind` — do NOT fork the comparator; write a new intent reader, and name no concrete platform beyond figma.
