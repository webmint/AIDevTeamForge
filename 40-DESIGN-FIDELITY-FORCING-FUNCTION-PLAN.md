# 40 — Design-Fidelity Forcing Function (make visual drift structurally gate-blocking)

**Status:** Phases 0–8 SHIPPED 2026-06-24 (built + per-phase review-clean via python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops); only **Phase 9 (testForge20 e2e) remains, user-driven (HARD GATE).** On `develop-2.0-init`. All six OQs ratified 2026-06-24 (see `## Open questions`). Extends the proven `_constitute/_forcing_functions/` family (`_design_tokens/` + `verify-design-tokens`) + the `/implement` per-task verify-gate + the new `_design/` disposition-manifest helper (`/breakdown` PHASE 2.5) + a NEW runtime-conformance dispatch into `/review` PHASE 2.5 (`design-auditor`, which before this plan was dispatched by NO command). Contract = persisted universal constitution section **§3.8 Design Fidelity** (the principle moved from a draft §4.4 to §3.8 so `/constitute`'s render-from-state does not wipe it; `_UNIVERSAL_SECTIONS`-tracked). No new pipeline command (`_PROMOTED` unchanged). Activation = `/constitute` Section 3.5 offers the `design_token_provenance` rule for UI projects.

## The diagnosis — drift is contract-licensed, not a rogue agent

A consumer project (an Electron app) built a UI shell that drifted from its `design/reference.html` — wrong border tokens, missing/wrong hover and `:focus-visible` states, ad-hoc spacing. The developer's own post-mortem traced the drift to the framework's CONTRACT, not to a misbehaving agent. Every step that should have caught the drift was licensed to let it through:

- **The spec licensed it.** "Look/behavior only, never reproduce `reference.html` markup, pixel-exact was never the target — semantic equivalence was." That sentence is the loophole: "semantic equivalence" was treated as a defense for wrong borders, wrong spacing, and missing hover/focus states.
- **Visual fidelity was deferred to a stage that DOES NOT RUN.** The developer's defense — "fidelity reconciles later at `/review` → design-auditor" — was itself FALSE. No command dispatches `design-auditor`: `/review` dispatches a FIXED 5-finder ensemble (`code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst` — `review/main.md:3`, `:141`) that does NOT include it; `/verify` dispatches `ac-verifier` only (`verify/main.md:179`), which checks AC pass/fail, not visual fidelity vs `reference.html`; `/summarize` and `/finalize` never dispatch it. `design-auditor` exists as an agent but is an ORPHAN — at diagnosis time it appeared in source at exactly three non-dispatch spots: two agent-availability enumeration lists (`breakdown/main.md:189`, `plan/main.md:326`) and one Agent-Assignment table row (originally `breakdown/main.md:251` — "Accessibility, design system compliance, UI audit | design-auditor"). That table row ASSIGNED `design-auditor` to UI-audit concerns and so manufactured the developer's false expectation of a `/review` fidelity pass that no command honors. (That mis-routing row was DE-ASSIGNED standalone 2026-06-24 — D8 site #1; the remaining two sites resolve via the Phase-6 `/review` wire-in.) Visual fidelity is auto-checked at ZERO points today, so DONE already meant drift-shipped.
- **Nothing checked visual VALUES at write time.** Hardcoded hex and `var(--token, <literal-fallback>)` literals passed `/implement` because no gate inspected component styles when they were written.
- **Legitimate scope was conflated with defects.** Empty mount slots, static placeholders, and inert accent areas were not distinguished from real defects, so any fidelity check drowns in noise and gets dismissed.

The drift is the predictable consequence of the contract, so a one-off fix to the current shell fixes nothing structural. **The goal of this plan is a framework mechanism that makes this CLASS of visual drift structurally gate-blocking for ANY future frontend task** — given that the framework cannot reliably "see pixels."

## The confirmed contract (maintainer-approved — settled)

Convert the unverifiable question "does it look right?" into two verifiable questions: (a) the PROVENANCE of every visual value, and (b) the RUNTIME CONFORMANCE of every in-scope element to the reference — both scoped to a DECLARED disposition. Two maintainer qualifications are NON-NEGOTIABLE.

### Qualification 1 — TWO ORTHOGONAL CHECKS, never merged into one

The provenance check and the runtime-conformance check cover two DIFFERENT defect classes, and neither can cover the other's hole:

- A runtime computed/visual compare reads RESOLVED values with no provenance. A hardcoded `#e8e6e3` and a `var(--border)` that resolves to `#e8e6e3` are INDISTINGUISHABLE at runtime — so the runtime check CANNOT catch token-bypass.
- A static grep catches token-bypass but reads only the source text — so it CANNOT catch "right token, wrong spacing": correct token bindings that still produce the wrong rendered box model.

Two defect classes, two gates, neither redundant with the other. **A future session MUST NOT delete the static provenance grep as "already covered by the runtime check," nor drop the runtime check as "the grep already enforces tokens."** This orthogonality is the load-bearing reason there are two gates and not one.

- **Provenance gate (static, write-time, in `/implement`):** in component styles — no hardcoded hex / `rgb()` / `hsl()` / named colors; no `var(--x, <literal>)` fallbacks; an UNDEFINED token must FAIL LOUDLY (escalate, never silently render a fallback — a CSS fallback is the silent-guess failure in CSS form); token-binding required on MATCH elements; every interactive element declares both `:hover` and `:focus-visible`. Greppable, no rendering.
- **Runtime conformance gate (in `/review`):** MECHANISM-AGNOSTIC. The contract requires "a runtime visual/computed conformance check," NOT a specific API. The mechanism is SELECTED at Phase 0 (see OQ-1); it is never hardcoded in this plan.

### Qualification 2 — Step 0 must PROVE the render substrate before any contract rewrite

Do not assume a renderer. Phase 0 records the substrate findings (gathered this session, below) and proves rendering `reference.html` (via `file://`) and the running implementation, reading resolved values, is BUILDABLE before any contract text is rewritten.

### The markup-freedom vs visual-fidelity distinction (the crux)

Rebuilding markup with clean semantic classes stays CORRECT and ALLOWED. What changes: the COMPUTED/VISUAL values and box model of every IN-SCOPE element must match the reference 1:1 (color, border, radius, spacing, typography, hover, focus-visible). "Semantic equivalence" is no longer a defense for wrong borders / spacing / hover. Markup freedom is untouched; VALUE fidelity is now enforced.

## The disposition manifest — the unifying mechanism

The difference between a defensible diff and a defect is whether it was DECLARED. This plan turns the developer's after-the-fact verbal taxonomy into a REQUIRED PRE-CODE intake artifact: a per-element disposition manifest classifying every element of `reference.html` for the feature.

| Disposition | Meaning | What is enforced |
|---|---|---|
| **MATCH** | In scope | Runtime values equal the reference 1:1 — color, border, radius, spacing, typography, `:hover`, `:focus-visible`. |
| **DEFER-EMPTY** | Slot CONTENT out of scope | The CONTAINER's box model (border, padding, dimensions) still must match 1:1. (The distinction the spec never made — catches "sidebar container has the wrong border" while allowing "sidebar tree unpopulated.") |
| **STATIC-PLACEHOLDER** | Content fixed/hardcoded | Styling still must match 1:1. |
| **DEVIATE** | Explicit recorded decision | Skipped by the runtime gate; the recorded reason is the audit trail. |

### Escalate at intake — never guess

- **Unclassified element → intake HALTS and escalates to the user BEFORE any code is written.**
- When resolving the reference's declared values, anything UNRESOLVABLE (a class with no definition on disk, a token with no source file) goes on a GAP-LIST; a non-empty gap-list HALTS intake and escalates. The user supplies the missing artifact or makes an explicit recorded decision.

This is the "escalate ASAP / never guess" requirement, fired at INTAKE — before writing — not at verify after shipping. A defect that is structurally impossible to write is worth more than a defect caught after the user has seen it.

### Element correspondence — `data-ref` anchors

To make 1:1 matching DETERMINISTic, the recommendation is to require impl elements that correspond to reference elements to carry a `data-ref="<reference-element-id>"` anchor; the manifest is keyed on these anchors. Fuzzy DOM matching is the fallback and is exactly where 1:1 silently degrades. Anchors-required vs fuzzy-fallback is a Phase-0 / Phase-1 decision (OQ-5).

## Substrate findings (gathered this session — verified against the cited files)

- **The render substrate EXISTS.** `src/agents/ac-verifier.md` (line 4 `tools:`) already carries `mcp__chrome-devtools__evaluate_script` plus `navigate_page`, and the agent already uses `evaluate_script` to run JS in the page (`## Verification modes`, `runtime-assisted`). Rendering `reference.html` (via `file://`) and the running impl, then reading resolved per-element values, is BUILDABLE — not assumed.
- **The nominal visual-fidelity agent is BOTH orphaned AND under-equipped.** `src/agents/design-auditor.md` is the agent whose charter is visual fidelity, but no command dispatches it (see the diagnosis — `/review` runs a fixed 5-finder ensemble without it, `/verify` runs `ac-verifier` only). And even if dispatched, it is under-equipped: it does NOT have `evaluate_script` — its `tools:` (line 4) are `Read, Grep, Glob, Bash, navigate_page, take_screenshot, take_snapshot, resize_page` only, and its method (`## Approach` step 1) is screenshot + eyeball comparison ("Take a browser screenshot … Compare spacing, colors, typography … document pixel-level differences that matter"). That is the unreliable human-eyeball failure relocated into an agent. So Phase 6 must do TWO things — WIRE a runtime-conformance dispatch into `/review` (a NEW dispatch, not "extend an already-running agent") AND give whatever agent runs it the `evaluate_script`-class capability.
- **The runtime gate is CONDITIONAL on Chrome MCP.** A structured `CHROME_MCP_AVAILABLE` + `mcp__chrome-devtools__list_pages` probe exists in `ac-verifier.md` (line 37); `design-auditor.md` Rule 1 uses prose judgment ONLY ("Use the Chrome DevTools MCP … when a running app is available; fall back to reading the source when it is not") — there is NO structured probe and NO `CHROME_MCP_AVAILABLE` symbol in `design-auditor.md` yet. Phase 6 (OQ-2/OQ-3) must REPLACE Rule 1's prose-judgment fallback with the structured probe (not supplement it — see Phase 6) so the agent has ONE gate, not two contradictory ones. When Chrome MCP is absent the plan MUST degrade HONESTLY: run the static provenance floor only, and DECLARE in the report that runtime spacing/proportion fidelity was NOT machine-covered that run. Never silently assume the renderer.
- **The agent-level license is `design-auditor.md` Rule 5:** "Styling and design conventions are NOT governed by the constitution — its authority is the existing components plus the design reference." The contract flip is a NARROW carve-out, NOT an overturn: WHEN a design reference exists, in-scope elements match it 1:1; WHEN no reference exists, the existing "ground in existing components" stance is unchanged.

## Framework conventions this plan respects

- **The static provenance detector extends the proven forcing-functions family — a deliberate "extend the proven architecture" choice.** The family lives at `src/devforge/lib/_constitute/_forcing_functions/` with per-rule subpackages (`_magic_enum/` = `_cmd.py` + `_scanner.py` + `_inventory.py`; `_cross_layer/` = `_cmd.py` + `_scanner.py` + `_graph.py`; `_any_leak/` = `_cmd.py` + `_scanner.py`), a shared `_setters.py` + `_shared.py`, the rule registry in `_schema.py` (`FORCING_FUNCTION_RULES` frozenset), the `verify-*` verbs registered in `_constitute/_cli.py`, verbs shipped via `.devforge/lib/constitute_helper`, and an opt-in pre-commit hook template at `src/git-hooks/pre-commit-forcing-functions.sh`. The new detector follows the same architectural pattern: a new `_design_tokens/` subpackage + a `constitute_helper verify-design-tokens`-style verb + an opt-in pre-commit hook template (a forward reference — built in Phases 4–5).
- **The disposition-manifest helper is a new `_design/` subpackage** under `src/devforge/lib/` with a launcher `src/devforge/lib/design_helper{,.py}` (mirrors the `audit_helper` / `review_helper` / `summarize_helper` shim pattern). Verbs: `resolve-reference` (→ element list + resolvable values + gap-list), `init-manifest` / `validate-manifest` (unclassified → fail), and an optional spacing-scale extraction from `design/styles.css` when present.
- **Spacing scale.** `tokens.json` may carry NO spacing scale (design hardcoded px), itself a root cause — components have nothing to bind to. The plan extracts a spacing scale from `design/styles.css` when present (feeds the provenance gate's token-binding check); when CSS is absent the runtime gate still works off the reference's own resolved values and the spacing PROVENANCE check relaxes accordingly. Maintainer caveat: full CSS/tokens will NOT always be present, but full HTML is assumed present.
- **Wiring points are existing commands — NO new pipeline command.** Provenance gate → `/implement` per-task verify-gate (PHASE 5 / forcing-functions gate). Runtime gate → `/review` — but `/review` today dispatches a FIXED 5-finder ensemble (`code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst`, `review/main.md:3`) and NO `design-auditor`; `/verify` dispatches `ac-verifier` only (`verify/main.md:179`); `design-auditor` is dispatched by no command. So Phase 6 must ADD a NEW dispatch — wiring `design-auditor` into `/review`'s ensemble (OQ-2 = EXTEND), NOT extending an already-running agent. Manifest intake → `/breakdown` (OQ-4). Do not invent a new command.
- **Execution uses dedicated agents + review loops — maintainer directive.** Every python helper function is test-first via **python-engineer → python-reviewer**. Every `.claude/`-shipping markdown edit (constitution, agent files, command `main.md`, references) routes through **instruction-author → instruction-reviewer + the claude-code-guide agent**. Each phase below names its loop.

## Settled decisions

- **D1 — The drift is contract-licensed, not a rogue agent** (the diagnosis). The fix is structural, not a patch to the current shell.
- **D2 — Two orthogonal gates, neither redundant.** Provenance (static, write-time) + runtime conformance. The orthogonality statement is load-bearing and must survive in the contract text.
- **D3 — A disposition manifest is a REQUIRED pre-code intake artifact** with the 4-way taxonomy (MATCH / DEFER-EMPTY / STATIC-PLACEHOLDER / DEVIATE).
- **D4 — Unclassified element OR unresolvable value HALTS intake and escalates BEFORE writing.** Escalate ASAP / never guess, fired at intake.
- **D5 — The forcing function moves to WRITE-TIME** so DONE cannot mean drift-shipped.
- **D6 — Narrow constitution carve-out (reference-present ⇒ 1:1), NOT an overturn** of the styling-not-governed-by-constitution stance. When no reference exists, the existing stance is unchanged.
- **D7 — The runtime gate is mechanism-agnostic;** the mechanism is selected at Phase 0 (OQ-1). No phase hardcodes `getComputedStyle`.
- **D8 — `design-auditor` has THREE orphan sites; each has a distinct resolution owner. WIRE-IN branch SELECTED (OQ-2 = EXTEND, 2026-06-24).** The maintainer's orphan research found three distinct sites where `design-auditor` is referenced for a behavior no command performs (it is dispatched by no command today). Wiring it into `/review` (Phase 6) resolves two of them by making the promised behavior TRUE; it does NOT resolve the third, because that one is a wrong-KIND assignment, not a missing dispatch.
  - **#1 — `breakdown/main.md` Agent-Assignment row** (`| Accessibility, design system compliance, UI audit | design-auditor |`, the table at `main.md:238`; the row was at `:251` as verified 2026-06-24 — note the maintainer brief cited `:250`, off by one). This assigns a READ-ONLY agent (`design-auditor` tools = `Read, Grep, Glob, Bash` + Chrome MCP, NO `Edit`/`Write`) as a per-task IMPLEMENTER — an active mis-routing. **DE-ASSIGNED standalone 2026-06-24** (the read-only agent removed from the implementer table, routed to the owning stack engineer per the `:245`/`:246` perf/security convention). NOT made correct by wiring — a `/review`-stage reviewer is never a per-task implementer. Edit CONFIRMED 2026-06-24 (`breakdown/main.md:251`) — Phase 8 VERIFIES it landed, does not re-do.
  - **#2 — `design-auditor.md:3` charter description** ("Use proactively after UI work lands, before a feature is verified") — an orphaned step (the agent runs at no such point). RESOLVED BY Phase 6 wire-in: once `design-auditor` is dispatched at `/review`, the charter becomes TRUE. Do NOT edit it away — Phase 6 makes it true.
  - **#3 — `design-auditor.md:68` Boundaries** ("Own: visual fidelity, accessibility (WCAG), responsive behavior, and design-system compliance — documented as findings") — an orphaned output (findings are never produced or consumed). RESOLVED BY Phase 6 wire-in: once the agent runs at `/review` and `/review` consumes its findings on the same path as the 5 finders, the boundary becomes TRUE. Do NOT edit it away — Phase 6 makes it true.
  - Net: #1 is fixed STANDALONE (an edit, because it was a wrong-kind assignment); #2 and #3 are made TRUE BY WIRING (no edit — Phase 6 supplies the missing dispatch). Files touched: `breakdown/main.md` (#1, done); `src/agents/design-auditor.md` + `review/main.md` (#2/#3, via Phase 6).

## Open questions (the Phase-0 ratification gate)

- **OQ-1 — Runtime-conformance MECHANISM.** Candidates:
  - **computed-style diff** — render reference + impl, read resolved per-element values (via Chrome DevTools MCP `evaluate_script`, the substrate `ac-verifier.md` already proves), diff numerically. Deterministic, machine-comparable, blind to layout glitches.
  - **screenshot / pixel diff** — `take_screenshot` + an image-diff producing a STRUCTURED/NUMERIC result. Noisy on font-rendering / antialiasing / dynamic content / empty slots — high false-positive risk against DEFER-EMPTY.
  - **hybrid** — computed-style for tokenizable axes (color/border/radius/spacing/typography) + screenshot-diff scoped only to declared MATCH regions.
  - **RECOMMENDED:** hybrid, leaning computed-style for tokenizable axes. NOT hardcoded — Phase 0 selects and RECORDS the choice.
  - **RESOLVED 2026-06-24 = HYBRID** (recommendation taken): computed-style diff for the tokenizable axes (color/border/radius/spacing) + screenshot-diff scoped ONLY to declared MATCH regions for layout. Rationale: screenshot noise is contained to in-scope MATCH areas, so DEFER-EMPTY slots cannot false-positive.
- **OQ-2 — design-auditor wire-in vs new agent.** Either re-equip `design-auditor.md` (add `evaluate_script` + a structured availability probe + rewrite its `## Approach`) AND add it to `/review`'s dispatch, OR introduce a dedicated computed-conformance agent AND add ITS dispatch. Either way the dispatch is NET-NEW — `design-auditor` is dispatched by no command today. **RECOMMENDED:** wire-in `design-auditor` (its charter is already visual fidelity, so reusing it avoids an 18th-agent split) — but ratify, since both its screenshot-eyeball method AND its missing dispatch must be fixed, which is a larger change than a tools-line edit.
  - **RESOLVED 2026-06-24 = EXTEND `design-auditor`** (recommendation taken): add the OQ-1 mechanism's Chrome-MCP tool(s) + a structured Chrome-MCP availability probe (the agent has NEITHER today) to the existing `design-auditor`, and wire it into `/review` as the net-new dispatch. This SELECTS D8's wire-in branch (the strike branch is moot) — but note: wiring it as a `/review`-stage agent does NOT make a per-task implementer-assignment row correct, which is why D8 site #1 (the `breakdown/main.md` Agent-Assignment row, originally `:251`) was fixed SEPARATELY as a standalone de-assignment, not by wiring (see D8).
- **OQ-3 — Chrome-MCP-absent degradation.** **RECOMMENDED:** provenance-floor-only + DECLARE-not-covered in the report. Confirm.
  - **RESOLVED 2026-06-24** (recommendation taken): provenance-floor-only + DECLARE in the report that runtime spacing/proportion fidelity was NOT machine-covered that run. Never silently skip, never hard-block the pipeline.
- **OQ-4 — Manifest placement command.** Candidates: produced at `/breakdown` (natural — it already does atomicity + agent assignment + the architect consult), at `/plan`, or as a pre-dispatch `/implement` intake step. Enforced at `/implement` (provenance) + `/review` (runtime) regardless. **RECOMMENDED:** produced at `/breakdown`, enforced at `/implement` + `/review`.
  - **RESOLVED 2026-06-24** (recommendation taken): the manifest is produced at `/breakdown`; enforced downstream at `/implement` (provenance gate) + `/review` (runtime gate).
- **OQ-5 — `data-ref` anchors required vs fuzzy DOM matching.** **RECOMMENDED:** `data-ref` anchors required (deterministic; fuzzy matching is where 1:1 silently degrades).
  - **RESOLVED 2026-06-24** (recommendation taken): REQUIRE `data-ref` anchors; the manifest is keyed on them; fuzzy DOM matching is rejected.
- **OQ-6 — spacing-scale extraction when `design/styles.css` is absent.** Define the relaxation precisely: which provenance sub-checks relax (the spacing token-binding check) and which stay hard (color/border literals; undefined-token-fails-loud).
  - **RESOLVED 2026-06-24** (recommendation taken): when `design/styles.css` is PRESENT, extract a spacing scale from it and REQUIRE spacing token-binding; when ABSENT, the runtime gate still works off the reference's own resolved values and the spacing PROVENANCE check RELAXES (there is no token to bind to). The color/border literal checks + undefined-token-fails-loud stay HARD regardless.

## Phases

### Phase 0 — Substrate proof + ratification (GATE — maintainer sign-off, NO build) — RATIFIED 2026-06-24

No code. The substrate findings (above) are recorded as proven against `src/agents/ac-verifier.md`, `src/agents/design-auditor.md`, `src/devforge/lib/_constitute/_forcing_functions/`, `src/git-hooks/pre-commit-forcing-functions.sh`. All six OQs were resolved with the maintainer to the plan's recommendations (see the `RESOLVED 2026-06-24` lines under `## Open questions`): (a) runtime mechanism = HYBRID (OQ-1); (b) `design-auditor` EXTEND, not a dedicated agent (OQ-2 → D8 wire-in branch); (c) Chrome-MCP-absent = provenance-floor-only + declare (OQ-3); (d) manifest produced at `/breakdown` (OQ-4); (e) `data-ref` anchors required (OQ-5); (f) spacing provenance relaxes when CSS absent (OQ-6).

**Verify:** SATISFIED — the substrate findings re-read clean against the four cited files; OQ-1–OQ-6 each carry a recorded `RESOLVED 2026-06-24` resolution (mechanism named, not deferred); the manifest-placement command (`/breakdown`) + the two enforcement points (`/implement` provenance, `/review` runtime) are named; maintainer sign-off recorded in this plan's status line.

### Phase 1 — The contract (constitution + the orthogonality principle)

Built via **instruction-author → instruction-reviewer + claude-code-guide** (ships into `.claude/`).

- Add the two-gate principle to the constitution's Patterns & Anti-Patterns material, WITH the explicit orthogonality statement (D2 — neither gate is redundant; a future session must not delete one as covered by the other) and the NARROW reference-present ⇒ 1:1 carve-out (D6).
- Revise `src/agents/design-auditor.md` Rule 5 to reflect the carve-out: WHEN a design reference exists, in-scope elements match it 1:1 (color/border/radius/spacing/typography/hover/focus-visible); WHEN no reference exists, the existing "existing components are the source of truth" stance is UNCHANGED. State the narrowness explicitly so the edit does not read as overturning the whole stance.

**Verify:** instruction-reviewer clean; claude-code-guide confirms the constitution + agent-file edits match authoring conventions; the orthogonality statement is present verbatim in the contract text; the carve-out is scoped to reference-present and explicitly does NOT touch the no-reference stance; cross-ref sweep confirms no other site contradicts the revised Rule 5.

### Phase 2 — Disposition manifest schema + helper (`_design/`)

Built via **python-engineer → python-reviewer** (test-first; real `reference.html` + `design/styles.css` fixtures, round-tripped via the real producer where one exists).

- New `src/devforge/lib/_design/` subpackage: a manifest schema (per element: disposition ∈ {MATCH, DEFER-EMPTY, STATIC-PLACEHOLDER, DEVIATE} + the `data-ref` key + a `DEVIATE` reason field) + verbs:
  - `resolve-reference` → element list + resolvable declared values + a gap-list of unresolvable classes/tokens.
  - `init-manifest` / `validate-manifest` → unclassified element → FAIL (D4); non-empty gap-list → FAIL (D4).
  - optional spacing-scale extraction from `design/styles.css` when present (OQ-6 relaxation when absent).
- New launcher `src/devforge/lib/design_helper{,.py}`.

**Verify:** unit tests — fully-classified manifest with empty gap-list → exit 0; one unclassified element → exit non-zero naming the element; non-empty gap-list → exit non-zero naming the unresolvable class/token; `resolve-reference` on a fixture `reference.html` returns the expected element list + values; spacing-scale extraction returns the scale when `styles.css` is present and relaxes per OQ-6 when absent; tests use real fixtures, not hand-authored value strings.

### Phase 3 — Intake escalation gate

Built via **instruction-author → instruction-reviewer + claude-code-guide** (ships into `.claude/`).

- Wire the unclassified-halts-intake / gap-list-escalates rule (D4) into `/breakdown` (the manifest-placement command, OQ-4): run `validate-manifest`, copy its block VERBATIM on failure, HALT and escalate to the user BEFORE any code is written. The user supplies the missing artifact or records an explicit decision (a `DEVIATE` entry, or supplies the missing token source).

**Verify:** instruction-reviewer clean; claude-code-guide confirms the gate wording + halt semantics match Claude Code command conventions; the gate fires at intake (pre-code), not at verify; cross-ref sweep confirms the verb name appears in the chosen command's helper-call list and nowhere stale.

### Phase 4 — Provenance gate (static forcing function)

Built via **python-engineer → python-reviewer** (test-first).

- New `src/devforge/lib/_constitute/_forcing_functions/_design_tokens/` detector (`_cmd.py` + `_scanner.py` at minimum — mirroring `_any_leak/`; additional files like `_inventory.py` / `_graph.py` are rule-specific, and the design-tokens rule may need one for manifest-keyed check dispatch) + a `constitute_helper verify-design-tokens`-style verb. Registration, in order: (1) add the new rule key to `_constitute/_schema.py::FORCING_FUNCTION_RULES` (frozenset) FIRST — `_setters.py` asserts `set(RULE_TO_VERB) == FORCING_FUNCTION_RULES` at import, so omitting this raises an `AssertionError` at startup; (2) add the `RULE_TO_VERB` mapping in `_setters.py`; (3) import `cmd_verify_design_tokens` from `_design_tokens/_cmd.py` and register the subparser in `_constitute/_cli.py` (following the `verify-magic-enum` pattern there) — NOT `_cmds_forcing_functions.py`, which handles only `set-forcing-functions` / `list-forcing-functions`. Checks, over component styles: no hardcoded hex / `rgb()` / `hsl()` / named colors; no `var(--x, <literal>)` fallbacks; undefined token → FAIL LOUDLY; token-binding required on MATCH elements (keyed off the manifest); every interactive element declares `:hover` + `:focus-visible`. Spacing-scale extraction (from Phase 2) feeds the token-binding check.

**Verify:** unit tests — clean tokenized styles → exit 0; a hardcoded hex → exit non-zero naming `file:line`; a `var(--x, #fff)` fallback → exit non-zero; an undefined token → fail-loud (escalate), not silent-fallback; a MATCH element missing a token binding → fail; an interactive element missing `:focus-visible` → fail; spacing provenance relaxes per OQ-6 when CSS is absent; the new subpackage matches the existing `_forcing_functions/` shape (regression net = the existing forcing-functions tests stay green).

### Phase 5 — Wire provenance gate into `/implement` + opt-in pre-commit hook template

Built via **instruction-author → instruction-reviewer + claude-code-guide** (`main.md`) + **python-engineer → python-reviewer** (hook script).

- Wire the `verify-design-tokens` verb into the `/implement` per-task verify-gate (PHASE 5 / forcing-functions gate) so the provenance check runs at WRITE TIME (D5) — a violation blocks the per-task gate.
- Add an opt-in pre-commit hook template alongside `src/git-hooks/pre-commit-forcing-functions.sh` (or extend it) so the provenance floor can run pre-commit, consistent with the existing opt-in hook pattern.

**Verify:** instruction-reviewer + claude-code-guide clean on `implement/main.md`; python-reviewer clean on the hook script; the provenance gate runs at the per-task gate (write time), and a hardcoded-hex component blocks before commit; the opt-in hook template installs via the existing hook-install path; cross-ref sweep on the verb name across `implement/main.md` + the hook + docs.

### Phase 6 — Runtime conformance gate (NEW `/review` dispatch — `design-auditor` wired in)

Built via **instruction-author → instruction-reviewer + claude-code-guide** (ships into `.claude/`).

This phase ADDS a dispatch that does not exist today: `/review` currently dispatches a fixed 5-finder ensemble with NO `design-auditor`, and `design-auditor` is dispatched by no command (see the diagnosis). Phase 6 is the first time a runtime-conformance check is actually invoked. Per the OQ-2 resolution (EXTEND, 2026-06-24), the conformance agent is the existing `design-auditor`, re-equipped and wired into `/review` — NOT a new agent. This wire-in is what RESOLVES orphan sites #2 (`design-auditor.md:3` charter) and #3 (`design-auditor.md:68` Boundaries) per D8 — by making the agent actually run at `/review` and `/review` consume its findings, NOT by editing those lines away.

- Implement the OQ-1 HYBRID mechanism: computed-style diff for the tokenizable axes (color/border/radius/spacing) + screenshot-diff scoped ONLY to declared MATCH regions for layout. Apply the manifest-scoped comparison (1:1 on MATCH; box-model-only on DEFER-EMPTY; styling-1:1 on STATIC-PLACEHOLDER; SKIP DEVIATE) and the OQ-3 Chrome-MCP-absent degradation (provenance-floor-only + DECLARE-not-covered, never silent-skip, never hard-block).
- Re-equip `design-auditor.md`: add the mechanism's Chrome-MCP tool(s) (incl. `evaluate_script` for the computed-style read) to its `tools:`, and rewrite `## Approach` step 1 from screenshot-eyeball to the hybrid mechanism. REPLACE Rule 1's prose-judgment fallback (`design-auditor.md:75` — "Use the Chrome DevTools MCP … when a running app is available; fall back to reading the source when it is not") with the structured `list_pages`/`CHROME_MCP_AVAILABLE` probe — NOT supplement it. The structured `CHROME_MCP_AVAILABLE` check becomes the GATE; reading the source is the DECLARED degradation path (OQ-3 provenance-floor-only + declare), not an inline judgment call. Leaving the old prose rule in place alongside the probe would give the agent TWO contradictory fallback mechanisms — the prose rule must go.
- WIRE `design-auditor` into `/review` as the NEW dispatch (`review/main.md`) — inject it into the ensemble or add a dedicated fidelity sub-step. This is net-new wiring; today `/review` dispatches it nowhere.
- Add `design-auditor` to the `breakdown/main.md` read-only-reviewer note (the sentence at `main.md:258` that currently reads "`performance-analyst` and `security-reviewer` are READ-ONLY reviewers — they run during `/review` (and `/audit`) …") so the now-running review-stage reviewer joins that list once it actually runs at `/review`. This is deferred to Phase 6 (NOT done in the standalone #1 de-assignment) precisely because the dispatch does not exist until this phase — adding it earlier would be a forward-reference into a shipped command.

**Verify:** instruction-reviewer + claude-code-guide clean; `/review` actually dispatches `design-auditor` (a NEW dispatch — confirm it appears in `review/main.md` where today it does not); the runtime gate compares per the manifest disposition (MATCH 1:1 / DEFER-EMPTY box-model-only / DEVIATE skipped); when Chrome MCP is absent the report DECLARES runtime fidelity was not machine-covered (no silent assume-renderer); `design-auditor.md`'s `tools:` carries the hybrid mechanism's MCP tool(s) + a structured availability probe and `## Approach` no longer relies on eyeball comparison; Rule 1 no longer contains the old prose-judgment fallback — the structured probe is the gate; the `breakdown/main.md:258` reviewer note now lists `design-auditor` as a review-stage reviewer; orphan sites #2 and #3 read TRUE against the live `/review` dispatch (charter step + boundary output both now happen); the agent file remains structurally conformant to `src/agents-AUTHORING.md`.

### Phase 7 — Producer alignment (frontend/mobile-engineer briefs)

Built via **instruction-author → instruction-reviewer + claude-code-guide** (ships into `.claude/`).

- Brief `src/agents/frontend-engineer.md` + `src/agents/mobile-engineer.md`: bind to tokens (never hardcode color/spacing literals), declare `:hover` + `:focus-visible` on interactive elements, carry `data-ref` anchors on elements that correspond to reference elements (per OQ-5), and NEVER silently fill a gap — escalate an unresolvable value rather than guess a fallback.

**Verify:** instruction-reviewer clean; both engineer briefs state the token-binding + state-declaration + `data-ref` + escalate-don't-guess requirements; the briefs do not contradict the design-auditor carve-out (Phase 1) or the provenance gate (Phase 4); the edits keep both files structurally conformant to `src/agents-AUTHORING.md`.

### Phase 8 — Emitter + docs reconcile + cross-ref sweep

Built via **python-engineer → python-reviewer** (any emitter / install change) + direct edits (docs).

- No new pipeline command, so NO `scripts/emitters/claude.py` `_PROMOTED` change is expected — VERIFY this (the new `_design/` helper + `design_helper` launcher install via the full-install `cp -R` of `src/devforge/lib/`, and the `_design_tokens/` detector ships inside the existing `constitute_helper` package).
- Reconcile repo-root `CLAUDE.md` (this plan-list entry as phases land; the "Where to find what" table — a forcing-functions row + a `_design/` helper row), `CHANGELOG.md`, and `src/CLAUDE.md` (the design-fidelity contract + the manifest intake, wherever the consumer overlay needs awareness).
- Reconcile the three `design-auditor` orphan sites (D8) — all three resolved by the end of Phase 6, NOT pending here. Phase 8 VERIFIES, it does not re-do: (a) **#1** — confirm the per-task Agent-Assignment row de-assignment landed (done STANDALONE 2026-06-24 — `design-auditor` removed from the implementer table, routed to the owning stack engineer); (b) **#2/#3** — confirm Phase 6 wired `design-auditor` into `/review` so the `design-auditor.md:3` charter step + `:68` boundary output are now TRUE, and confirm Phase 6 added `design-auditor` to the `breakdown/main.md:258` read-only-reviewer note; (c) confirm the `breakdown/main.md` + `plan/main.md` availability-list mentions read coherently against the live dispatch. Any residual `.claude/`-shipping edit here routes through **instruction-author → instruction-reviewer + claude-code-guide**.
- Cross-ref sweep: grep `verify-design-tokens`, `design_helper`, `_design_tokens`, `data-ref`, `design-auditor`, and the manifest verb names across `src/` to confirm no dangling reference, no site still asserting the old screenshot-eyeball method as the fidelity mechanism, and that all three `design-auditor` orphan sites are no longer orphaned (the agent is dispatched at `/review`, not assigned as a per-task implementer, and not referenced for any other behavior no command performs). Confirm the new-rule registration is complete: `_constitute/_cli.py` imports `cmd_verify_design_tokens` and registers the subparser; `_constitute/_schema.py::FORCING_FUNCTION_RULES` includes the new rule key; `_setters.py::RULE_TO_VERB` includes the mapping and the import-time assertion passes.

**Verify:** `_PROMOTED` confirmed unchanged (no new command); the install ride installs `design_helper` (executable) + the `_design_tokens/` detector with zero `{{` leaks; CLAUDE.md / CHANGELOG / `src/CLAUDE.md` reconciled; all three `design-auditor` orphan sites are resolved (#1 de-assigned standalone — confirmed in the file; #2/#3 made true by the Phase-6 `/review` wire-in; the `breakdown/main.md:258` reviewer note now lists `design-auditor`); the cross-ref sweep finds no dangling reference, no stale "eyeball comparison" fidelity claim, and no mention implying a `design-auditor` behavior that no command performs.

### Phase 9 — testForge20 e2e (user-driven, HARD GATE)

Build a frontend feature with a `reference.html` and confirm, end-to-end:

- an UNCLASSIFIED reference element HALTS intake (the manifest gate at `/breakdown`, OQ-4) before any code is written;
- a hardcoded hex in a component BLOCKS at the `/implement` per-task gate (provenance gate, write time);
- the runtime conformance gate at `/review` CATCHES a wrong-spacing MATCH element;
- a declared DEFER-EMPTY container PASSES content-empty but FAILS on a wrong border (box-model still enforced);
- with Chrome MCP absent, the run degrades to the provenance floor and the report DECLARES runtime fidelity was not machine-covered.

**Verify:** each of the five scenarios above behaves as stated on a real install; the manifest halt fires pre-code; the provenance block fires at write time; the runtime gate distinguishes MATCH (full 1:1) from DEFER-EMPTY (box-model only); the degradation path is honest (declared-not-covered, not silent-pass).

## Context for next session

- Phase 0 ratified 2026-06-24; all six OQs resolved to the plan's recommendations (OQ-1 hybrid mechanism; OQ-2 EXTEND `design-auditor`; OQ-3 provenance-floor-only + declare; OQ-4 manifest produced at `/breakdown`; OQ-5 `data-ref` required; OQ-6 spacing relaxes when CSS absent). Next executable phase is Phase 1 (the contract — constitution two-gate principle + `design-auditor.md` Rule 5 carve-out).
- The bug surfaced in a consumer install (an Electron app), not in this repo. This plan is the FORGE root-cause fix — a structural mechanism for the CLASS of visual drift, NOT a fix for the consumer's current shell.
- The two gates are ORTHOGONAL by construction (D2) — provenance is static/write-time (`/implement`), runtime conformance is rendered (`/review`). Do not collapse them; a hardcoded `#e8e6e3` and a `var(--border)` resolving to the same value are indistinguishable at runtime, and a correct token can still produce wrong spacing.
- The substrate is PROVEN, not assumed: `ac-verifier.md` already carries `evaluate_script` AND a structured `list_pages`/`CHROME_MCP_AVAILABLE` probe (line 37); `design-auditor.md` has NEITHER (its method is screenshot-eyeball, and its Rule 1 Chrome-MCP fallback is prose judgment only — no structured probe). The runtime gate is conditional on Chrome MCP — Phase 6 must REPLACE that prose-judgment Rule 1 with the structured probe (one gate, not two) and degrade honestly when absent.
- The constitution carve-out is NARROW (reference-present ⇒ 1:1). It does NOT overturn `design-auditor.md` Rule 5's no-reference stance.
- The static detector EXTENDS the proven `_forcing_functions/` family (`_design_tokens/` mirroring `_magic_enum/` / `_cross_layer/` / `_any_leak/`) — a deliberate architecture-reuse choice, not a new pattern.
- No new pipeline command — `/implement`, `/review`, and the manifest intake command (`/breakdown`, OQ-4) are extended.
- `design-auditor` had THREE orphan sites (maintainer research), tracked in D8. Today the agent is dispatched by NO command (`/review` runs a fixed 5-finder ensemble without it, `/verify` runs `ac-verifier` only), so the developer's "fidelity reconciles at `/review` → design-auditor" defense was FALSE. **#1** the `breakdown/main.md` per-task Agent-Assignment row (was `:251`; the maintainer brief said `:250`, off by one) mis-routed a READ-ONLY agent as an implementer — FIXED STANDALONE 2026-06-24 (de-assigned to the owning stack engineer; an edit, because wiring never makes a reviewer a per-task implementer). **#2** the `:3` charter step and **#3** the `:68` boundary output are made TRUE BY Phase 6's `/review` wire-in (NOT edited away). OQ-2 resolved to the WIRE-IN branch; Phase 6's `/review` dispatch is NET-NEW (not "extend an already-running agent") and also adds `design-auditor` to the `breakdown/main.md:258` reviewer note once it actually runs at `/review`.
- OQ-1 resolved to the HYBRID mechanism (computed-style diff for tokenizable axes + screenshot-diff scoped to MATCH regions); `getComputedStyle` is the computed-style reading approach, ONE half of the hybrid, never the sole mechanism.

## When resuming work

Read this plan in full, then re-read `src/agents/ac-verifier.md` (line 4 `tools:` + `## Verification modes`), `src/agents/design-auditor.md` (line 4 `tools:` + `## Approach` step 1 + Rule 5), and the `src/devforge/lib/_constitute/_forcing_functions/` layout (`_magic_enum/` as the per-rule reference shape) before touching code. Phase 0 is RATIFIED (2026-06-24) — all six OQs resolved to the plan's recommendations — so the next executable phase is Phase 1 (the contract). Start at the lowest un-shipped phase; each phase names its review loop (python-engineer → python-reviewer for helpers; instruction-author → instruction-reviewer + claude-code-guide for `.claude`-shipping markdown).
