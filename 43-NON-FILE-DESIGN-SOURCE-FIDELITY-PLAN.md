# 43 — NON-FILE DESIGN-SOURCE FIDELITY

**Status:** **✅ COMPLETE 2026-06-26 (Option 4 + Option 1 hybrid) — Steps 1A–1D ALL SHIPPED; consumer e2e DEFERRED by maintainer (not blocking)** on `develop-2.0-init` (commits `493dc81` 1A/1B/1D + `580c264` 1C). See `## Ratified` for the maintainer decision + OQ resolutions and `## Phase 1` for the per-step build breakdown. Shipped: the `design_source` producer (`/specify` Phase 4 capture + `set-design-source` setter + `**Design source**:` render line), the classify/WARN helper (`design_helper check-design-source`), the `/breakdown` PHASE 2.5 WARN wire-in (Step 1C, landed once plan 42 shipped — `f0a9e95`), and docs reconcile; built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops (design + specify suites green; 1003-test cross-suite sweep clean). This file began as a DECISION RECORD capturing a coverage boundary of the design-fidelity apparatus; the decision space + recommendation are retained below for rationale.

## Problem — the apparatus is keyed end-to-end on a local HTML+CSS file

The framework's design-fidelity apparatus (built by plan 40, `40-DESIGN-FIDELITY-FORCING-FUNCTION-PLAN.md` — DONE) and its trigger-hardening (plan 42, `42-DESIGN-MANIFEST-TRIGGER-FORCING-FUNCTION-PLAN.md`) are BOTH keyed end-to-end on a single local artifact: `design/reference.html` (plus optionally `design/styles.css`, the CSS token source). Every gate assumes that HTML+CSS artifact exists on disk:

- `/breakdown` PHASE 2.5 `design_helper resolve-reference` PARSES `design/reference.html` to extract `data-ref` elements + resolved CSS into `specs/[feature]/design-manifest.json`.
- `/implement`'s forcing-functions gate runs `constitute_helper verify-design-tokens`, which checks code literals against the `design/styles.css` token source.
- `/review` section 2.5 (within PHASE 2) dispatches `design-auditor`, which does computed-style / screenshot diffs against the RENDERED `design/reference.html`.

**THE GAP:** a team whose design source is NOT a local HTML file — a **Figma selection**, a **hosted design URL**, a **screenshot/image**, or a design-tool export the team did not convert to `reference.html` — gets ZERO design-fidelity enforcement, and gets it **SILENTLY**. No manifest is produced, every gate skips cleanly, and nobody is warned that a design intent exists with no enforceable reference. This is a real coverage boundary of plan 40's apparatus.

## Framing: this is NEW CAPABILITY, not a plan-42 trigger bug

State this explicitly so a future session does not mis-route the work:

- This is **NOT** a plan-42 trigger bug. Plan 42's gates correctly skip with no false halt and no false warn when `design/reference.html` is absent — they simply cannot ENGAGE a non-file source. There is nothing to fix in plan 42's trigger; the trigger is doing the right thing.
- Extending coverage to non-file sources is a **NEW enforcement backend** (a new capability), not a trigger tweak.
- This stub captures that capability so it is not lost; it does **NOT** supersede plan 40 or plan 42. Plan 40 owns the HTML+CSS apparatus this would extend; plan 42 hardens the HTML-keyed trigger. Plan 43 generalizes the design-source TYPE.

## The two hard problems

The whole stub turns on two problems. Neither is solved here; both are the core of any future build.

### Problem 1 — Declaration: how does the framework mechanically KNOW a non-file design source exists?

When the design source is a file, presence-on-disk IS the signal (`design/reference.html` exists ⇒ engage). A non-file source has no such on-disk signal. The framework must be told.

The signal MUST be a structured `design_source` declaration — a typed field with a shape like `html:<path> | figma:<url> | screenshot:<path> | none` — NOT prose-scraping the spec / discover narrative. **Prose-scraping is explicitly rejected**: fuzzy NLP over free-text "the design is in Figma" is fragile, unfalsifiable, and exactly the kind of prose-only obligation the framework has repeatedly converted to mechanical gates (the `feedback_helper_owns_contract_filesystem_forcing` lesson — only a structured, filesystem/field-walked assertion is a reliable forcing function).

**Where the declaration lives is an open question** (see OQ-1): spec frontmatter, `.devforge/project-config.json`, or the design-manifest seed are the candidates.

### Problem 2 — Enforcement backend: fidelity without a local HTML+CSS artifact

Plan 40's two mechanical halves are the static **provenance** gate (`verify-design-tokens` — code literals vs `design/styles.css` tokens) and the runtime **conformance** gate (`design-auditor` — computed-style / screenshot diff vs the rendered HTML). Neither survives the loss of the local HTML+CSS artifact unchanged:

- **The static token-provenance gate is IMPOSSIBLE without a CSS token source.** `verify-design-tokens` checks code literals against the tokens declared in `design/styles.css`. A Figma node, a hosted URL's rendered DOM, or a screenshot supplies no `styles.css` and no token provenance. So non-file sources can at best get the **runtime-conformance half**, never the static-provenance half — and even that half is degraded (no token binding to anchor it).
- **Figma backend** — a Figma-API node diff. Requires an API token + network + a Figma file/node ref. Heavy, external dependency, auth.
- **Hosted URL backend** — render the URL via Chrome DevTools MCP (already used by `design-auditor`) + screenshot / computed-style diff. But no token/CSS provenance, so only the runtime-conformance half is possible.
- **Screenshot/image backend** — pure visual diff, no DOM, no tokens — the weakest signal; arguably only a human-review prompt, not a mechanical gate.

## Decision space

The options below are distinct candidate answers. They are not all mutually exclusive — Option 4's declare-and-warn is a natural precursor to any backend, and Option 1 could co-exist with a narrow backend. No winner is picked unilaterally; the maintainer ratifies one (or a hybrid) at Phase 0.

### Option 1 — "convert-to-reference" lane (likely the lean, NOT finalized)

The framework helps or requires the team to export their Figma / URL / screenshot to a `design/reference.html` (+ optionally `styles.css`, the CSS token source) so the EXISTING plan-40 apparatus applies unchanged.

**Pros.**
- Lowest engineering cost — zero new enforcement backend; the whole plan-40 + plan-42 apparatus applies as-is once the file exists.
- Keeps ONE enforcement mechanism and one source of truth (the same invariant plan 28's "one producer" and plan 40's single apparatus already chose).
- Both halves (static provenance + runtime conformance) are recovered, because the converted artifact carries real CSS tokens.

**Cons.**
- Pushes the conversion burden onto the team (a manual or semi-assisted export step before `/breakdown`).
- Does not enforce that the converted `reference.html` faithfully matches the upstream Figma/URL — conversion fidelity is the team's responsibility, unchecked by the framework.

### Option 2 — native Figma-API backend

A new resolver that diffs against Figma nodes directly (extend `design_helper` / `design-auditor` with a Figma-API path).

**Pros.**
- Zero team conversion burden — the Figma file IS the reference.
- Could recover a provenance-like signal from Figma's own token/variable system (closer to the static half than the URL or screenshot backends).

**Cons.**
- Highest cost — external API client, auth (token storage / secret handling), network dependency, Figma file/node ref plumbing.
- Couples the framework to a specific commercial design tool's API surface and its evolution.

### Option 3 — URL-render backend

Reuse the Chrome-MCP runtime path `design-auditor` already uses, pointed at a hosted design URL instead of a local rendered `reference.html`.

**Pros.**
- Reuses an existing mechanism (Chrome DevTools MCP) — smaller new surface than the Figma backend.
- No team conversion burden for teams who already host their design.

**Cons.**
- Runtime-conformance half ONLY — no static token provenance (no `styles.css` to check code literals against), so `verify-design-tokens` cannot engage at all.
- Network/hosting dependency; the URL must be reachable at `/review` time.

### Option 4 — declare-and-warn only (no new backend)

Add only the `design_source` declaration (Problem 1) + a tripwire that WARNS "design source declared but not enforceable — no `design/reference.html`," giving teams visibility without building any enforcement backend.

**Pros.**
- Cheapest closure of the SILENT part of the gap — the team is no longer unaware that an enforceable reference is missing.
- A natural minimal bridge from plan 42's WARN-tripwire pattern (the `reference.html`-present-but-manifest-absent loud WARN) — same shape, new trigger condition.
- Could ship as a precursor BEFORE any backend (Option 1/2/3 build on top of the declaration it adds).

**Cons.**
- Closes only the silent half — declares the gap but enforces nothing. A team that declares `figma:<url>` still gets no fidelity gate.
- A standing WARN with no remedy backend can become noise teams learn to ignore.

## Recommendation

**Lean: Option 1 (convert-to-reference) as the standing answer, very likely fronted by Option 4 (declare-and-warn) as a precursor — NOT finalized; the maintainer ratifies.**

**Why (preliminary, argued, not binding).**
- **Option 1 keeps one enforcement mechanism.** The framework has repeatedly chosen single-source-of-truth over a second parallel producer (plan 28 rejected a standalone doc producer; plan 40 built one apparatus). A convert-to-reference lane reuses the entire plan-40 + plan-42 apparatus unchanged and recovers BOTH fidelity halves, where Option 2/3 recover at most the runtime half at high cost.
- **Option 4 cheaply closes the SILENT part now.** The most acute symptom is silence — a design intent with zero enforcement and zero warning. Option 4's declare-and-warn removes the silence for the cost of a typed field + a tripwire, and it is the prerequisite declaration any backend needs anyway.
- **Decline Option 2/3 as default.** Both build a second enforcement backend that recovers only the runtime-conformance half (the static provenance gate is impossible without a CSS token source — see Problem 2), at network/auth cost. A half-covered, costly gate is a poor trade against Option 1's full-coverage reuse — unless the maintainer judges the team conversion burden of Option 1 unacceptable, in which case Option 3 (URL) is the cheaper backend than Option 2 (Figma).

This recommendation is preliminary. The maintainer ratifies the option (or a hybrid) at Phase 0.

## Ratified

**Ratified 2026-06-25 (maintainer):** **Option 4 + Option 1 hybrid.** Build the declare-and-warn precursor (a typed `design_source` field + a loud non-blocking WARN when a non-file design source is declared but no enforceable `design/reference.html` exists), with convert-to-reference as the standing answer (team exports their Figma / URL / screenshot to `design/reference.html` so the existing plan-40 apparatus applies unchanged). **No new enforcement backend** (Option 2 Figma / Option 3 URL declined).

- **OQ-1 (declaration home) RESOLVED → spec.md frontmatter (per-feature).** `design_source` lives in each feature's `specs/NNN-<slug>/spec.md` frontmatter, written by `/specify` (Phase 4 render), read at `/breakdown`. Per-feature granularity matches the per-feature value shape (`figma:<specific-frame-url>`) and is read at exactly the time the WARN needs it. The generated spec frontmatter is bold key-value lines (NOT YAML) emitted by `render_spec` (`src/devforge/lib/_specify/_render.py:128-133`); the field is a new `**Design source**:` line.
- **OQ-2 (backend choice) RESOLVED → no backend** (Option 1 convert-to-reference is the standing answer; the team conversion burden is accepted).
- **OQ-3 (half-coverage worth) MOOT** — no half-coverage backend is built; Option 4's declare-and-warn closes the silent half and Option 1 recovers full coverage via conversion.
- **OQ-4 (Chrome-MCP-absent) MOOT for now** — no rendering backend is built; a converted `reference.html` inherits plan-40's existing floor-and-declare stance unchanged.
- **Verb home → `_design/` (`design_helper`), NOT `breakdown_helper.py`.** The `breakdown_helper.py` file is plan-42's active edit zone (the `verify-manifest-present` PHASE 3.5 gate). The new `design_source` classify/WARN verb is homed in `_design/_source.py` + registered in `_design/_cli.py` — collision-free and design-cohesive. Only the `/breakdown` PHASE 2.5 detect-step edit (Step 1C) touched plan-42's region; it was gated on plan 42 shipping and landed afterward.

## Relationships to other plans

- **Plan 40 (`40-DESIGN-FIDELITY-FORCING-FUNCTION-PLAN.md`, DONE)** — owns the HTML+CSS apparatus this plan would extend (`design_helper`, `verify-design-tokens`, `design-auditor`, constitution §3.8). Do NOT modify it; plan 43 adds a new source-type backend AROUND it, not new logic inside it.
- **Plan 42 (`42-DESIGN-MANIFEST-TRIGGER-FORCING-FUNCTION-PLAN.md`)** — hardens the HTML-keyed TRIGGER (asserts the manifest exists for a `reference.html`-present feature). Plan 43 generalizes the design-source TYPE. **Plan 42 must ship first** — plan 43 builds on a hardened trigger (a generalized source type only makes sense once the file-source trigger is mechanically guaranteed). Plan 42's non-goals point at this capability as out-of-its-scope; this stub is where that capability is captured.
- **Option 4's declare-and-warn is the natural minimal bridge from plan 42's WARN-tripwire pattern** — same loud-WARN shape, new trigger condition (`design_source` declared but no enforceable `design/reference.html`).

## Open questions (enumerated, NOT resolved)

- **OQ-1 — where the `design_source` declaration lives.** Spec frontmatter vs `.devforge/project-config.json` vs the design-manifest seed. The choice interacts with which command first reads the field (spec frontmatter is read at `/specify`/`/breakdown`; project-config is global; a manifest seed is feature-scoped). Resolve before any build.
- **OQ-2 — which backend(s) to build, if any.** Option 2 (Figma) and/or Option 3 (URL) vs Option 1 (convert-to-reference) as the standing answer with no new backend. Turns on whether the team conversion burden of Option 1 is acceptable.
- **OQ-3 — half-coverage worth.** Since static token provenance is impossible without a CSS token source (Problem 2), non-file backends get at best the runtime-conformance half. Is a half-covered gate worth the engineering complexity, or is Option 4 (declare-and-warn) the more honest closure until a full-coverage path exists?
- **OQ-4 — Chrome-MCP-absent degradation.** For any backend that renders (Option 3 URL; a converted Option 1 reference also renders), what happens when Chrome DevTools MCP is unavailable? Mirror plan 40's floor-and-declare stance (provenance-floor-only + DECLARE-not-covered) rather than silently passing.

## Phase 0 — Maintainer ratification (decision gate)

No code. Present this decision record to the maintainer. The maintainer ratifies exactly one of Option 1 / Option 2 / Option 3 / Option 4 (or directs a hybrid — e.g. Option 4 precursor + Option 1 standing answer), and confirms: (a) the NEW-CAPABILITY framing (this is not a plan-42 trigger fix), (b) that plan 42 ships first, (c) OQ-1 declaration home, (d) OQ-2 backend choice. Until ratification, no build phases are authored.

### Verify

- Maintainer has ratified a single option or a named hybrid (record the choice + any amendments inline under a new `## Ratified` heading when it happens).
- Plan 42 has shipped (it is the trigger this plan builds on).
- OQ-1 (declaration home) is decided if any option beyond pure documentation is ratified.

## Phase 1 — Build the ratified capability (Option 4 + Option 1 hybrid)

Authored 2026-06-25 after Phase-0 ratification. Build runs behind the standard agent loops (python-engineer → python-reviewer for any helper change; instruction-author → instruction-reviewer + claude-code-guide for any `main.md` / `src/CLAUDE.md` change that ships into `.claude/`). Sequenced so the collision-free producer + helper (1A, 1B) land independently of plan 42; only the `/breakdown` detect-step wire-in (1C) waits on plan 42.

### Step 1A — `design_source` schema + parser + classify/WARN verb (collision-free) — ✅ SHIPPED

Built via **python-engineer → python-reviewer** (test-first; round-trip via the real producer). Shipped: `_specify/_schema.py` enum (`DESIGN_SOURCE_SCHEME_ENUM` + `DESIGN_SOURCE_DEFAULT`), `_design/_source.py` (`parse_design_source` + `cmd_check_design_source`), `_design/_cli.py` verb registration. Reviewer caught + fixed: target-not-stripped false WARN, html-WARN hardcoded-filename, stale `--help` verb list, and a producer/consumer `none:` divergence (parser now rejects `none:<...>` to match the setter). 124 `_design` tests pass.

- `src/devforge/lib/_specify/_schema.py`: add `DESIGN_SOURCE_SCHEME_ENUM = ("html", "figma", "screenshot", "none")` + `DESIGN_SOURCE_DEFAULT = "none"` beside the existing `SPEC_TYPE_ENUM` (`:38`).
- `src/devforge/lib/_design/_source.py` (new): `parse_design_source(value) -> DesignSource` (fields: `scheme`, `target`, `raw`, `valid`) parsing the `scheme:target` / `none` shape; `cmd_check_design_source(args)` reads the `**Design source**:` line from a spec.md (reusing a frontmatter regex), checks `design/reference.html` presence at the workspace root, and emits a loud WARN block to **stderr + exit 0** (non-blocking, house style per `_specify/_cmds_phase4_verify.py:303-323`) when a non-file source (`figma`/`screenshot`, or `html:<path>` whose path is not an existing `design/reference.html`) is declared but no `design/reference.html` exists. `none` / absent / enforceable-html → exit 0, no output.
- `src/devforge/lib/_design/_cli.py`: register `check-design-source --spec <path> --workspace-root <path>` (registry tuple `:39` + elif arg-block + handler import).

**Verify:** unit tests — `parse_design_source` over every scheme + malformed input; WARN matrix (figma + no reference.html → WARN on stderr exit 0; screenshot + no reference.html → WARN; `html:design/reference.html` + file present → silent exit 0; `none` → silent exit 0; absent field → silent exit 0). No hand-authored spec.md — render fixtures via the real `specify_helper render` once 1B lands; until then, parse-level tests use the documented `**Design source**:` line shape.

### Step 1B — `/specify` produces the `design_source` field (collision-free) — ✅ SHIPPED

Built via **python-engineer → python-reviewer** (render + setter) and **instruction-author → instruction-reviewer + claude-code-guide** (`specify/main.md`). Shipped: `_render.py` `**Design source**:` line (always-render, default `none`), `default_state()` key, `set-design-source` setter (`_cmds_phase4_setters.py` + `_cli.py` + `specify_helper.py` re-exports), updated `specify-sample-*` fixtures, and `specify/main.md` Step 4.10 (single-line AskUserQuestion, 4 schemes, default None, next-turn prose for Figma/Screenshot targets) with render renumbered to Step 4.11 + the Phase-5 `request-changes` re-entry shorthand updated. An authoring note records that the next-turn target capture is intentional (must not collapse into an "Other" option — would overflow AskUserQuestion's 2–4 limit). 21 new specify tests + fixture round-trips green.

- `src/devforge/lib/_specify/_render.py`: add `out.append("**Design source**: {0}".format(design_source))` in the frontmatter block (`:128-133`), sourced from `state.get("design_source", DESIGN_SOURCE_DEFAULT)`. One edit covers `cmd_render`, `cmd_verify_rendered`, and the `:124` re-render (all share `render_spec`).
- Add a `set-design-source --value <v>` setter (validates against `DESIGN_SOURCE_SCHEME_ENUM`) writing `state["design_source"]`.
- `src/commands/specify/main.md` Phase 4: add ONE single-line `AskUserQuestion` (4 options — the complete scheme set, NO "hosted URL": `[None, Local design/reference.html, Figma, Screenshot/image]`, default None) before the render step; for Figma/Screenshot capture the free-text target (URL/path) in a next-turn prose follow-up; compose `scheme:target` (or `none`) and call `set-design-source`. Default-none keeps non-UI features friction-free.

**Verify:** render test — a state with `design_source=figma:<url>` round-trips to a `**Design source**: figma:<url>` line and `cmd_verify_rendered` stays green; a state with no `design_source` renders `none` (back-compat — existing specify render tests stay green); setter rejects an out-of-enum scheme. `instruction-reviewer` clean on `specify/main.md`; `claude-code-guide` confirms the AskUserQuestion shape.

### Step 1C — `/breakdown` PHASE 2.5 WARN wire-in — ✅ SHIPPED (after plan 42)

Built via **instruction-author → instruction-reviewer + claude-code-guide** (ships into `.claude/`) once plan 42's `/breakdown` PHASE 2.5/3.5 edits committed (`f0a9e95`/`8ec2a36`). Edits the same detect-step region (`src/commands/breakdown/main.md` PHASE 2.5 detect step).

- In the PHASE 2.5 detect step's reference-ABSENT branch: run `design_helper check-design-source --spec specs/NNN-<feature>/spec.md --workspace-root .`; if the verb produces a WARN, copy that output VERBATIM into the user-facing message before proceeding to Phase 3; if it produces no output, emit the plain skip line as before. This replaces the silent skip for the declared-non-file-source case; a genuine `none`/non-UI feature still skips silently (the verb emits nothing). Reviewer-caught: the absent-branch silent-case parenthetical was corrected (no false "already resolves to an enforceable reference"), and the branch discriminator reframed from a brittle stderr-emptiness test to verb-produced-output (robust to Bash-tool stream handling; the WARN still writes stderr, matching the file's `## ... VERBATIM` idiom). NON-BLOCKING — never halts Phase 3.

**Verify:** `instruction-reviewer` clean; `claude-code-guide` confirms the WARN placement + verbatim-copy idiom; the WARN fires only on the `non-file-source-declared ∧ reference.html-absent` intersection (not on every non-UI feature); cross-ref sweep that the verb name matches the registered verb.

### Step 1D — Docs reconcile — ✅ SHIPPED

- Repo-root `CLAUDE.md` "Where to find what" design-fidelity row: name the new `design_helper check-design-source` verb + the `design_source` spec-frontmatter field.
- `src/CLAUDE.md` `/specify` entry: note the per-feature `design_source` declaration.
- `CHANGELOG.md`.
- This plan's entry in repo-root `CLAUDE.md` plan list + this file's Status (mark phases shipped).

**Verify:** `grep` the new verb name appears in the docs + nowhere stale; `pre-empt-future-hallucination` pass — a fresh session reading `/specify` sees the `design_source` field, and reading the design-fidelity row sees the non-file-source declare-and-warn capability.

### Verify (Phase 1 overall)

- 1A + 1B land + all helper tests green, independent of plan 42.
- 1C lands only after plan 42's PHASE 2.5/3.5 edits are committed (no merge collision).
- The convert-to-reference (Option 1) lane is the WARN's named remedy — the WARN points the team at exporting to `design/reference.html`.

## Context for next session

This is a captured gap awaiting ratification, NOT an active build. The design-fidelity apparatus plan 40 shipped (and plan 42 hardens) is keyed end-to-end on a local `design/reference.html` (plus optionally `design/styles.css`, the CSS token source): `/breakdown` PHASE 2.5 `design_helper resolve-reference` parses the HTML, `/implement`'s `constitute_helper verify-design-tokens` checks the CSS tokens, `/review` section 2.5 (within PHASE 2) `design-auditor` diffs against the rendered HTML. A team whose design source is a Figma selection / hosted URL / screenshot gets ZERO fidelity enforcement, SILENTLY. This is NOT a plan-42 trigger bug (those gates correctly skip with no false halt/warn when the file is absent — they cannot ENGAGE a non-file source); it is a NEW enforcement-backend capability. Two hard problems frame any build: (1) **Declaration** — a structured `design_source` field (`html:<path> | figma:<url> | screenshot:<path> | none`), NOT prose-scraping; (2) **Enforcement backend** — the static token-provenance gate is IMPOSSIBLE without a CSS token source, so non-file sources get at best the runtime-conformance half. The lean is Option 1 (convert-to-reference, reusing the plan-40 apparatus unchanged) likely fronted by Option 4 (declare-and-warn precursor), declining the costly half-coverage backends (Option 2 Figma / Option 3 URL) as default — but the maintainer ratifies. Plan 42 ships first.

## When resuming work

This is a recorded decision, not an active build. Before authoring any edit instruction:

1. Confirm plan 42 has shipped — plan 43 builds on the hardened HTML-keyed trigger. Read `42-DESIGN-MANIFEST-TRIGGER-FORCING-FUNCTION-PLAN.md` directly; it may not yet be in CLAUDE.md's active-plans list. Its Phase 0 is already ratified — the build phases (1–6) must be complete before plan 43 proceeds (do not re-present plan 42 for ratification).
2. Re-confirm the apparatus references against the live tree — `design_helper resolve-reference` at `/breakdown` PHASE 2.5, `constitute_helper verify-design-tokens` at `/implement`'s forcing-functions gate, `design-auditor` at `/review` section 2.5 (within PHASE 2), and the `design/reference.html` (+ optional `design/styles.css`) artifacts. Do not invent line numbers; verify against `40-DESIGN-FIDELITY-FORCING-FUNCTION-PLAN.md` and the live commands before trusting any cited location.
3. Get the maintainer to ratify an option (Phase 0). Record the ratification inline.
4. Resolve OQ-1 (declaration home) before treating any enforcement option as buildable; resolve OQ-2 (backend choice) before building a Figma/URL backend.
5. Then promote Phase 1 to a real per-step build breakdown with `## Verify` per step, behind the standard agent loops.
