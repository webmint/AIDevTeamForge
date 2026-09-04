# 15 — Agent Standardization Plan

**Status**: SHIPPED 2026-06-07 on `develop-2.0-init` — Phases 0–5 complete. Phase 0 authoring doc `src/agents-AUTHORING.md` (`348561b`); Phase 1 six pure read-only reviewers tools-locked + unified severity, qa-reviewer split out, performance-analyst demoted (`fcc4947`); Phase 2 eight builders + runtime-debugger actor standardized (`ea2995d`); Phase 3 architect + tech-writer light-conformed without flattening (`76df502`); Phase 4 consumer rewire — qa-engineer-reviewer→qa-reviewer + performance-analyst/security-reviewer implementer rows rerouted across commands + the `_audit` helper + tests (`3fe4644`); Phase 5 structural verification PASSED (17 agents emit, exactly 6 tools-locked, all cross-ref sweeps 0, full suite green). D-ReviewerSplit RESOLVED toward a SPLIT (roster 16 → 17). **Remaining: user-driven full install-ride / testForge20 e2e** (repo's standard manual-e2e gate — not a code change).
**Branch**: `develop-2.0-init`
**Driver**: The 16 agent source files in `src/agents/` were each LLM-authored ad-hoc and never standardized. Their bodies diverge: no two identity lines phrased alike ("expert" / "senior" / "elite autonomous" / "director"); the same concept carries different section names ("Review Checklist" vs "X Principles" vs "Testing Philosophy" vs "Mandatory Debugging Loop" vs "Phase 1–5"); five incompatible severity/verdict vocabularies; inconsistent constitution + memory handling; `{{PROJECT_PATHS}}` present in 14 but missing from `ac-verifier` and `runtime-debugger`; no tool restrictions anywhere; and a handful of discrete bugs (a stray body line, an unexecutable cross-agent instruction, stale plan references). `architect.md` and (partly) `tech-writer.md` received later hand-maintenance and are far more rigorous — `architect.md` is effectively the reference implementation for the boundaries/consultation discipline the other 15 lack. This plan rewrites every agent body to a single canonical skeleton, anchored to that reference, splits the nominal-reviewer roster along a clean read-only-vs-acting line (one new agent `qa-reviewer`; `performance-analyst` demoted to a pure analyst), rewires every consumer command + Python helper that referenced the old roles, and does all of this without touching the build contract.

## Scope and non-scope

This plan standardizes the **markdown body** of each `src/agents/*.md` source file (and trims/normalizes the `description` inside its meta block), ADDS one new agent source (`qa-reviewer`), and rewires the commands + Python helpers that invoked the old `qa-engineer`-reviewer / `performance-analyst`-implementer roles. It does NOT change:

- `scripts/generate-agents.py`, the `emit_claude` emitter, the meta-block contract (fenced ```yaml block: `name`/`description`/`model_tier` required, optional `tools`/`applies_to`), or `applies_to` semantics.

The roster grows from 16 → **17** with the new `qa-reviewer`. The 17 agents (canonical names): `architect`, `backend-engineer`, `frontend-engineer`, `db-engineer`, `api-designer`, `devops-engineer`, `migration-engineer`, `mobile-engineer`, `tech-writer`, `code-reviewer`, `security-reviewer`, `qa-engineer`, `qa-reviewer`, `ac-verifier`, `design-auditor`, `performance-analyst`, `runtime-debugger`.

Consumer rewire IS in scope (it is the load-bearing consequence of the split): every command markdown + Python helper that named `qa-engineer` in a reviewer/assessor role is repointed to `qa-reviewer`, and every assignment of `performance-analyst` as an optimization-implementer is rerouted to the owning engineer. See the new rewire phase. The build contract itself stays fixed.

## The build contract (fixed — do NOT propose changing it)

`scripts/generate-agents.py` reads each `src/agents/*.md` source as a fenced ```yaml meta block followed by a free-form markdown body, and `emit_claude` (`generate-agents.py:168`) translates it into a Claude-native `.claude/agents/<name>.md`:

- Meta fields: `name` (required), `description` (required), `model_tier` (required ∈ {think, do, verify, scan}), optional `tools`, optional `applies_to`.
- Emitted frontmatter: `name`, `description`, optional `tools:` line (emitted verbatim when non-empty after `.strip()`; absent otherwise — `generate-agents.py:185`), `model:` (derived from `model_tier` via boot-safe defaults opus/sonnet/sonnet/haiku — `_claude_tier_model`), optional `applies_to:` line.
- The body passes through unchanged as the agent's system prompt.

The meta-block contract is already consistent across all 16 existing sources and is NOT what this plan changes; the new `qa-reviewer` source is authored TO this same contract. This plan standardizes the BODY, normalizes the `description` text, and adds one conforming new source.

> **Dated note — 2026-09-03, `92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md` D1/D6.** The contract above gained **one optional meta field, `model_pin`** (an alias, regex `^[a-z][a-z-]*$` — no digit, so a version string cannot enter through it), and the **emitted** frontmatter changed in one way: `model_tier` is now emitted as its own `model_tier:` line **in addition to** the static `model:` default it has always produced. The emitted order is `name`, `description`, optional `tools`, `model`, `model_tier`, optional `applies_to`. A source declaring `model_pin` emits `model: <pin>` and **no** `model_tier:` line. The `model_tier:` line exists so `configure_helper apply-agent-models` can rewrite `model:` / `effort:` per tier from `.devforge/project-config.json` on a consumer install, where the meta-block sources are not shipped. **The field names above and their required/optional status are unchanged, and nothing in this plan's reasoning is edited** — this note records that the contract it calls fixed was consciously EXTENDED, and by which plan.

> **Dated note — 2026-09-04, `94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md` D2/D3. `model_pin` is GONE — removed the day after it was added.** On a maintainer directive that the framework ship no model of its own, the pin (a framework-chosen model for one agent) was replaced by a **fourth tier**: `model_tier` values are now **`think | do | verify | security`** (`scan` retired, zero members), `security-reviewer` carries `model_tier: security`, and its model comes from a new configuration question rather than from this repo. The emitter **ignores** a `model_pin` declaration with one stderr warning, and **no shipped source declares it.** The static per-tier `model:` default is gone too: **every agent now emits the constant `model: inherit`**, and the consumer's own answers are written over it by `configure_helper apply-models` (renamed from `apply-agent-models`, which survives as an alias for one release), now covering **`.claude/agents/*.md` and eight `.claude/commands/devforge/*.md`**. **The required/optional status of every remaining field is unchanged, and nothing in this plan's reasoning is edited.**

## Research-grounded facts (verified this session — treat as settled)

- **Claude Code subagent tool grants**: `tools:` is comma-separated (e.g. `Read, Grep, Glob, Bash`); omitting `tools:` inherits ALL tools; restricting reviewers to a read-only subset is officially recommended; MCP tool names may be listed; including `Agent` permits subagent-spawning while OMITTING `Agent` blocks it. Subagents CANNOT spawn other subagents (authoritative). `model` aliases (`sonnet`/`opus`/`haiku`) and `inherit` are valid. There is NO official mandatory body structure — official examples use role line → numbered workflow → checklist → optional output format, ~20–40 body lines, "design focused subagents." (Re-confirm current syntax via the `claude-code-guide` agent at each agent-rewrite phase per repo spec-edit discipline.)
- **Cross-framework survey** (BMAD-METHOD, wshobson/agents, VoltAgent, 0xfurai, CrewAI): the convergent agent-body shape is identity → focus/expertise → principles/approach → numbered procedure → output contract → handoffs/boundaries → rules. The boundaries / "what-I-defer-to-whom" section is the highest-leverage section for a large roster and the strong frameworks all carry it. No surveyed framework uses per-agent tool grants to separate read-only reviewers from acting builders, and none defines a formal severity enum — so this plan's tools-lock + unified severity are genuine differentiators, not table stakes.
- **Canonical severity scale already ships here**: `src/devforge/lib/_audit/findings_schema.py:49` → `SEVERITY_ENUM = ("Critical", "High", "Medium", "Info")` (verified). The reviewers' severity vocab anchors to it. `security-reviewer` already matches; nobody else does (`code-reviewer` uses Critical/Warning/Info, `performance-analyst` uses high/med/low impact, `design-auditor` PASS/FAIL, `qa-engineer` ADEQUATE/GAPS).
- **F1 description-trim blast-radius** (verified this session): `{{AGENT_LIST}}` in `src/CLAUDE.md` is derived from agent FILENAMES only (`_configure/_render.py:169-188`), NOT descriptions; `tests/scripts/test_generate_agents.py` asserts frontmatter STRUCTURE (keys + tools handling), not `Examples:` content; `_configure/_md_parsers.py` parses only `applies_to`. So trimming each `description` is contained to the agent source files and breaks nothing downstream — provided `description` stays non-empty (this also means the new `qa-reviewer` source auto-appears in `{{AGENT_LIST}}` once it exists, no consumer wiring needed). `tools:` rendering is already supported AND tested (`tests/scripts/test_generate_agents.py`). Phase 0 re-confirms both findings before any rewrite.

## Locked decisions

### D-Skeleton — the canonical body skeleton

Every agent body conforms to this ordered skeleton. Section NAMES are fixed; depth varies by role-family.

1. **Identity** — `You are a {role}. {one-line mandate}.` One line. No "elite" / "senior" / "relentless" / "director-of" inflation. (`architect`'s "a director, not an implementer" framing is substantive and is retained as its mandate — the ban is on empty seniority adjectives, not on a substantive role descriptor.)
2. **`## Core Expertise`** — focus/expertise bullets; `**Field**: {{PLACEHOLDER}}` pairs where stack-specific.
3. **`## Project Paths`** — `{{PROJECT_PATHS}}`, in ALL 17 agents, no exceptions (D2).
4. **`## Approach`** — the working procedure as a numbered list. ONE consistent section name replacing the divergent "Principles" / "Workflow" / "Phases" / "Testing Philosophy" / "Mandatory Debugging Loop" names.
5. **`## Output`** — deliverable contract. The pure read-only reviewers carry the unified severity (D1); builders (incl. the now-pure-builder `qa-engineer`) may omit `## Output` if they produce only code/tests.
6. **`## Boundaries & Handoffs`** — NEW in every agent: own X · defer Y to {named agent} · consult specialists via the orchestrator (subagents can't spawn). Back-ported in lighter form from `architect`'s `## Boundaries & Handoffs` + `## Consulting Specialists` discipline.
7. **`## Rules`** — numbered; closes with the constitution + memory + minimal-scope + grounding conventions (F2 + the fleet-wide grounding rule).

`architect` and `tech-writer` keep additional substantive sections beyond this skeleton (see D-Families); they conform section NAMES and Rules style, they are not flattened to the minimal skeleton.

### D-Families — four role-families (exact membership)

The split (D-ReviewerSplit, RESOLVED) reshapes the families into four, totalling **17**:

- **Pure read-only reviewers — tools-locked (6)**: `code-reviewer`, `security-reviewer`, `ac-verifier`, `design-auditor`, `performance-analyst` (demoted), `qa-reviewer` (new). Meta gets a `tools:` read-only allowlist (`Read, Grep, Glob, Bash` + any read-only MCP the agent genuinely needs; NO `Edit`/`Write`; NO `Agent` → blocks spawning). `## Output` MANDATORY with the unified severity Critical/High/Medium/Info + one verdict vocab; read-only stance stated explicitly.
- **Builders (8)**: `api-designer`, `backend-engineer`, `db-engineer`, `devops-engineer`, `frontend-engineer`, `migration-engineer`, `mobile-engineer`, `qa-engineer` (now a pure test-writer builder). Full tools (read + write — meta omits `tools:` so they inherit all). `## Output` optional. `## Boundaries & Handoffs` names the reviewer/sibling to hand off to.
- **Actor (1)**: `runtime-debugger`. A pure fix-loop actor — it never reviews. Inherits all tools (meta omits `tools:`); builder-style `## Boundaries & Handoffs` (it acts, no reviewer verdict block).
- **Specials (2)**: `architect`, `tech-writer`. Richer multi-section substance preserved; conform section NAMES, Rules style, constitution/memory phrasing, and confirm a `## Boundaries & Handoffs` section. `architect` is the reference, not a flatten target. `tech-writer` has 3 operating modes — they are preserved, not collapsed.

### D-ReviewerSplit — read-only-vs-acting within the nominal-reviewer set (RESOLVED toward a SPLIT)

Three nominal reviewers actually MODIFY code today: `qa-engineer` writes tests, `performance-analyst` applies fixes, and `runtime-debugger` runs a fix loop. They are NOT symmetric, so a single rule does not fit all three. Resolution (settled, not awaiting confirmation):

1. **`qa-engineer` → SPLIT into two agents.** Writing tests (builder; assigned by `/breakdown` + `/plan`) and assessing tests (read-only reviewer; used by `/review`, `/audit`, `/fix`, `/refactor`) are both first-class, and the consumers already hand-clamp the conflict (`src/_pending/commands/review.md:74` literally says "It does NOT write tests — report only"). The split makes that hand-clamp structural:
   - `qa-engineer` → becomes a PURE BUILDER (writes tests). Strip its assessment/reviewer half. Stays in the Builders family; inherits all tools (no `tools:` lock).
   - **NEW agent `qa-reviewer`** (new source file `src/agents/qa-reviewer.md`) → the read-only test ASSESSOR. Gets `qa-engineer`'s old assessment half (coverage gaps, untested AC items, missing edge-case tests, assertion quality). Pure read-only reviewer: `tools:` lock (`Read, Grep, Glob, Bash`; no `Edit`/`Write`; no `Agent`), mandatory `## Output` with the unified severity (D1), conforms to D-Skeleton. Meta block: `applies_to: ["all"]`, `model_tier: verify`. Its `description` follows F1 (concise purpose + delegation signal, no dialogue `Examples:`).
2. **`performance-analyst` → DEMOTE to a pure read-only analyst.** It currently both profiles AND applies optimizations ("Changes Made" / "After Metrics"). Strip the acting half: it becomes read-only — profiles, identifies bottlenecks, reports findings with the unified severity (D1) — and does NOT apply fixes. The owning engineer (`backend-engineer` / `frontend-engineer` / etc.) or `/refactor` applies the optimization the analyst recommends. This mirrors `14-ARCHITECT-NOT-IMPLEMENTER-PLAN.md` (analysts recommend, engineers implement). It joins the pure read-only reviewers: `tools:` lock, mandatory `## Output` with unified severity. RETIER `model_tier` `do` → `verify` to match its read-only-reviewer peers (this resolves the `performance-analyst` half of D-Bugs-e — see D-Bugs-e).
3. **`runtime-debugger` → UNCHANGED actor.** It never reviews (absent from `/review` and `/audit`; appears only in `/breakdown`, `/fix`, `/_agent-assignment`). It is a pure fix-loop actor and stays in the Actor family (inherits all tools, builder-style boundaries). No split.

Rationale for the split (over the earlier "keep `qa-engineer`/`performance-analyst` as acting reviewers" option): a single agent that both writes/applies AND is invoked as a read-only assessor forces consumers to hand-clamp ("does NOT write tests — report only"), and a `tools:` lock can't be both present (for the assessor invocation) and absent (for the writer invocation) on one source. Splitting `qa-engineer` and demoting `performance-analyst` lets each agent carry an honest, enforceable tool grant. The cost — one new source, a larger roster, and a consumer-rewire phase — is paid once here. The roster change is therefore IN scope for this plan (see Scope and the rewire phase), not deferred.

### D1 — Unified severity

`Critical / High / Medium / Info` for every agent that emits findings, anchored verbatim to `findings_schema.py:49`. Replaces the five current vocabularies (`code-reviewer` Critical/Warning/Info, `performance-analyst` high/med/low impact, `design-auditor` PASS/FAIL, `qa-engineer` ADEQUATE/GAPS; `security-reviewer` already conforms). The two split/demoted agents inherit the unified severity in their new read-only form: `qa-reviewer` (carrying `qa-engineer`'s old ADEQUATE/GAPS assessment) and the demoted `performance-analyst` (replacing high/med/low impact). The now-pure-builder `qa-engineer` produces tests, not findings, so it carries no severity vocab. A single verdict vocab accompanies the severity in each pure-reviewer's `## Output`.

### D2 — `{{PROJECT_PATHS}}` in all 17

Add the `## Project Paths` / `{{PROJECT_PATHS}}` block to `ac-verifier` and `runtime-debugger` (the two existing agents that lack it); author the new `qa-reviewer` with the block from the start; confirm the placeholder is present and correctly placed in the other 14.

### D5 — `tools:` read-only allowlist on the pure-reviewer subset

Apply a `tools:` read-only allowlist (`Read, Grep, Glob, Bash` + needed read-only MCP; no `Edit`/`Write`; no `Agent`) to the **6** pure read-only reviewers (per D-ReviewerSplit): `code-reviewer`, `security-reviewer`, `ac-verifier`, `design-auditor`, `performance-analyst` (demoted), `qa-reviewer` (new) — using the emitter's existing-and-tested `tools` support. The 8 Builders (incl. the now-pure-builder `qa-engineer`) and the Actor (`runtime-debugger`) omit `tools:` (inherit all).

### D-Boundaries — `## Boundaries & Handoffs` in every agent

NEW section in all 17 (the 16 existing + the new `qa-reviewer`), back-ported from `architect`'s boundaries + consulting discipline in lighter form: own X · defer Y to {named agent} · specialist consultation flows through the orchestrator because subagents cannot spawn other subagents.

### F1 — Trim each `description`

Trim each agent's `description` from the embedded `Examples:` user/assistant dialogue blocks down to the official concise form: a one-to-two-sentence purpose plus a delegation signal ("Use when…" / "Use proactively" / "Use immediately after…"). Dialogue `Examples:` are not a Claude Code convention, and dispatch in this framework is orchestrator-mediated (not model-auto-invocation), so the dialogue examples carry no functional weight. Contained per the F1 blast-radius finding; `description` MUST stay non-empty.

### F2 — Constitution + memory handling as prose

Standardize constitution + memory handling as a fixed Rules-section prose convention — e.g. "Read `constitution.md` before deciding; check `.devforge/memory.md` for prior lessons." Do NOT introduce a new frontmatter field; the meta-block contract is fixed.

### F3 — Repoint the broken `§Conventions` anchor (= option B), by concept-name

The `§Conventions` anchor is dangling in `frontend-engineer` (lines 14, 15, 57) and `mobile-engineer` (lines 15, 59) ONLY. `design-auditor` has no `§Conventions` anchor — its line 89 (`5. Check constitution for design/styling rules`) is a separate vague constitution reference that gets the same concept-name treatment (see the design-auditor item below). Repoint:

- **State-management** → the constitution's **Patterns & Anti-Patterns** material, referenced BY CONCEPT-NAME, never by `§`-number. (Verified: `/constitute` files state/pattern rules under that material — testForge20's BLoC rules live there.)
- **Styling** → existing components + framework idiom, NOT the constitution. (Verified: `/constitute` captures NO styling rules even in a real UI project, so the constitution is the wrong authority for styling.)
- **design-auditor (line 89)** → repoint the vague "Check constitution for design/styling rules" to reference the constitution by concept-name AND state that styling's real authority is existing components + the design reference (Figma / design spec), not the constitution. This is design-auditor's F3 item — NOT a `§Conventions` repoint (there is no anchor to repoint there).

Throughout every agent, reference the constitution by section NAME/CONCEPT, never a brittle `§`-number — numbers drift across constitution versions (template §3.6 "Design Principles" vs testForge20 populated §3.6 "Function Length & Simplicity").

### D-Grounding — fleet-wide grounding rule

Add this as a standard Rule in every agent's `## Rules` (generalizing the styling concern): **"When the constitution is silent on a convention, ground in real code (CBM / existing files) before acting; apply the dominant observed pattern and flag any inconsistency in your output; never invent a convention from 'framework idiom' alone."** This closes the hallucination/drift vector that the current weak "follow framework-idiomatic conventions" fallback opens. (`grep "framework idiom"` must return 0 after Phase 4.)

### D-Bugs — five discrete bug fixes folded in

| # | Location | Defect | Fix |
|---|---|---|---|
| a | `api-designer.md:7` | A stray `b` line sits after the yaml fence and renders into the agent body | Delete the stray line (Phase 2). |
| b | `api-designer.md:84` | "Validate with the backend-engineer agent before implementation" — unexecutable (subagents can't spawn) | Replace with `## Boundaries & Handoffs` "consult via the orchestrator" wording; the no-`Agent`-tool rule is reviewer-side, but the unexecutable instruction is removed here (Phase 2). |
| c | `tech-writer.md` (refs ~lines 3, 32, 270, 325) | Stale references to `GENERATE-DOCS-PLAN.md` (now under `done-plans/`) + an `/onboard`-deprecation framing | Re-verify current state and de-stale (Phase 3). |
| d | `ac-verifier.md`, `runtime-debugger.md` | Missing `{{PROJECT_PATHS}}` | Add the `## Project Paths` block (D2; Phases 1/2 respectively — see note). |
| e | model_tier audit | `design-auditor` = `do` and `performance-analyst` = `do` sit below their peer reviewers (`code-reviewer`/`ac-verifier` = `verify`, `security-reviewer` = `think`) | `performance-analyst` RESOLVED: `do` → `verify` (demoted to a pure read-only reviewer by D-ReviewerSplit, so it matches its read-only-reviewer peers; applied in Phase 1). `design-auditor` model_tier audit is UNCHANGED from the current plan — still a flag-and-justify item: Phase 1 justifies its FINAL tier against the peer reviewers, changed only with stated reasoning, not by inertia. The now-pure-builder `qa-engineer`'s tier (currently `verify`) is reconsidered against the Builders (which are `do`) in Phase 2 — flag the FINAL `qa-engineer` tier with reasoning; the new `qa-reviewer` is authored at `verify` in Phase 1. |

(Line numbers for c are stated as approximate in the brief and MUST be re-verified at Phase 3 before editing; line numbers for a, b are confirmed against the file this session.)

## Execution discipline (applies to every phase)

- Every agent-file rewrite goes through `instruction-author` → `instruction-reviewer` (this repo's spec-edit discipline; route-spec-edits-through-agent-flow).
- For any Claude-Code-integration concern in a rewrite (frontmatter, `tools:` syntax, model aliases), verify current conventions via the `claude-code-guide` agent before writing — confidence is not verification.
- Each phase leaves the system buildable/verifiable: every rewritten source still parses through `generate-agents.py` and `description` stays non-empty.
- This plan lives at repo root and is committed alongside the work it drives.

## Phase 0 — Authoring-convention doc + blast-radius re-confirm (no agent rewrites)

Write the canonical-shape authoring convention as a standing doc so future agents are not authored ad-hoc. **Decision — location**: create `src/agents-AUTHORING.md` — a SIBLING of the `src/agents/` directory, deliberately NOT inside it. Rationale: `generate-agents.py:260` globs `args.src.glob("*.md")` (default `--src src/agents`) and parses EVERY matched `*.md` as an agent meta-block source (confirmed against the file this session). A doc placed AT `src/agents/AGENTS.md` would be globbed, parsed as a (malformed) agent, and either error the build or emit a junk `.claude/agents/AGENTS.md` — and adding a generator-side exclusion is a build-side change this plan forbids. Placing the doc one level UP (`src/agents-AUTHORING.md`) keeps it co-discoverable with the sources (same `src/` neighborhood, sorts adjacent to `agents/` in a listing) while staying outside the `src/agents/*.md` glob, so it is provably build-inert with no generator change. It also keeps the always-on `src/CLAUDE.md` budget untouched (per `08-CLAUDE-MD-COMMAND-TRIM-PLAN.md` discipline). `agents-AUTHORING.md` records: the D-Skeleton section order + fixed names, the **four** role-families and their membership (6 pure read-only reviewers / 8 builders / 1 actor / 2 specials — the post-split 17-agent roster), the read-only-vs-acting split principle from D-ReviewerSplit (a single source carries one honest tool grant; assessors are split out, implementers demoted), the unified severity (D1, anchored to `findings_schema.py:49`), the `tools:` read-only-allowlist convention for the 6 pure reviewers (D5/D-ReviewerSplit), the F1 description form, the F2 constitution/memory prose convention, the D-Grounding rule, and the "reference the constitution by concept-name, never `§`-number" rule (F3).

Then re-confirm the two blast-radius findings hold before any rewrite begins:

- F1: trimming `description` is contained (filename-derived `{{AGENT_LIST}}`; structure-only generate-agents tests; `applies_to`-only md parsing).
- D5: the emitter's `tools:` support is live and tested.

### Verify

```bash
# The authoring doc exists OUTSIDE the generator's glob:
ls src/agents-AUTHORING.md            # expect: present
ls src/agents/AGENTS.md 2>/dev/null   # expect: absent (must NOT live inside src/agents/)
# The generator globs src/agents/*.md — confirm the doc is not in that set:
ls src/agents/*.md | wc -l            # expect: 16 (the EXISTING agents; qa-reviewer is added in Phase 1, not here)
# Emit into a temp target and confirm the emitted .claude/agents/ set is exactly the 16 existing agents
# (no extra file emitted from the authoring doc; qa-reviewer does not exist yet at Phase 0).
# F1 re-confirm — {{AGENT_LIST}} is filename-derived, not description-derived:
grep -n "AGENT_LIST" src/devforge/lib/_configure/_render.py
# D5 re-confirm — tools rendering is supported + tested:
grep -n "tools" tests/scripts/test_generate_agents.py
```

DoD: `src/agents-AUTHORING.md` written and reviewed (`instruction-author` → `instruction-reviewer`) recording the post-split 17-agent roster + four families; it lives OUTSIDE `src/agents/` so the `src/agents/*.md` generator glob still matches exactly the 16 existing agents (qa-reviewer is created in Phase 1); both blast-radius findings re-confirmed; zero agent rewrites in this phase.

## Phase 1 — Pure read-only reviewers batch (6, incl. new qa-reviewer + demoted performance-analyst)

Author/rewrite the 6 pure read-only reviewers — the tools-locked family per D-ReviewerSplit (RESOLVED; no kickoff confirmation needed). Per agent, via `instruction-author` → `instruction-reviewer`:

- **Existing-stance read-only (4)** — `code-reviewer`, `security-reviewer`, `ac-verifier`, `design-auditor`: add the `tools:` read-only allowlist (`Read, Grep, Glob, Bash` + needed read-only MCP; no `Edit`/`Write`; no `Agent`), conform to D-Skeleton, state the read-only stance, mandatory `## Output` with unified severity (D1) + one verdict vocab, add `## Boundaries & Handoffs`. `ac-verifier` also gets `{{PROJECT_PATHS}}` (D2/D-Bugs-d). `design-auditor` also gets the F3 styling-reference repoint at line 89: repoint the vague "Check constitution for design/styling rules" to the concept-name form + state styling's real authority is existing components + the design reference (Figma / design spec), not the constitution (NOT a `§Conventions` anchor — there is none in this file).
- **`performance-analyst` — DEMOTED to a pure read-only analyst** (D-ReviewerSplit #2): strip the acting half ("Changes Made" / "After Metrics"); it profiles, identifies bottlenecks, and reports findings with the unified severity (D1) but does NOT apply fixes. Add the `tools:` read-only allowlist (same as the 4 above), conform to D-Skeleton, state the read-only stance, mandatory `## Output` with unified severity + one verdict vocab, `## Boundaries & Handoffs` that defers the actual optimization to the owning engineer (`backend-engineer` / `frontend-engineer` / etc.) or `/refactor`. RETIER `model_tier` `do` → `verify` to match the read-only-reviewer peers (D-Bugs-e).
- **`qa-reviewer` — NEW source `src/agents/qa-reviewer.md`** (D-ReviewerSplit #1): the read-only test ASSESSOR. Author it fresh from `qa-engineer`'s old assessment half (coverage gaps, untested AC items, missing edge-case tests, assertion quality). Meta block: `name: qa-reviewer`, `applies_to: ["all"]`, `model_tier: verify`, `tools:` read-only allowlist (`Read, Grep, Glob, Bash`; no `Edit`/`Write`; no `Agent`), and a `description` per F1 (concise purpose + delegation signal — e.g. "Use to assess test coverage and quality after tests are written"; no dialogue `Examples:`). Body conforms to D-Skeleton with `{{PROJECT_PATHS}}` (D2), mandatory `## Output` with unified severity (D1) + one verdict vocab, read-only stance stated, `## Boundaries & Handoffs` that defers test-WRITING to `qa-engineer`.
- Every agent in this phase gets F2 (constitution/memory prose), the D-Grounding rule, and the F3 concept-name constitution-reference convention.
- **model_tier audit (D-Bugs-e)**: `performance-analyst` `do` → `verify` (resolved, above). For `design-auditor` (`do`), justify the FINAL tier in the rewrite against the peer reviewers (`verify`/`think`); change only with stated reasoning, do not change by inertia.

Note: `qa-engineer` is NOT touched here — it is rewritten as a pure builder in Phase 2, where its assessment half (now owned by `qa-reviewer`) is removed.

### Verify

```bash
# Read-only tools lock present on all 6 pure reviewers (incl. the new qa-reviewer + demoted perf):
grep -l "tools:" src/agents/{code-reviewer,security-reviewer,ac-verifier,design-auditor,performance-analyst,qa-reviewer}.md  # expect: all 6
# No Edit/Write/Agent granted to any pure reviewer:
grep -nE "tools:.*(Edit|Write|Agent)" src/agents/{code-reviewer,security-reviewer,ac-verifier,design-auditor,performance-analyst,qa-reviewer}.md  # expect: 0
# The new source exists and parses (non-empty description, verify model_tier):
ls src/agents/qa-reviewer.md                                            # expect: present
grep -nE "model_tier:\s*verify" src/agents/qa-reviewer.md              # expect: 1
# performance-analyst retiered do -> verify:
grep -nE "model_tier:\s*verify" src/agents/performance-analyst.md     # expect: 1
# Unified severity present, old vocabularies gone, in the 6 pure reviewers:
grep -rnE "Critical|High|Medium|Info" src/agents/{code-reviewer,security-reviewer,ac-verifier,design-auditor,performance-analyst,qa-reviewer}.md
grep -rnE "Warning|high/medium/low" src/agents/{code-reviewer,security-reviewer,ac-verifier,design-auditor,performance-analyst,qa-reviewer}.md  # expect: 0 (dead severity vocab; verdicts like PASS/FAIL, ADEQUATE/GAPS are legitimate and not swept)
# performance-analyst acting half stripped:
grep -niE "Changes Made|After Metrics" src/agents/performance-analyst.md  # expect: 0
# ac-verifier + qa-reviewer carry Project Paths:
grep -l "{{PROJECT_PATHS}}" src/agents/{ac-verifier,qa-reviewer}.md   # expect: both
# design-auditor styling reference repointed (vague constitution line gone):
grep -n "Check constitution for design/styling rules" src/agents/design-auditor.md  # expect: 0 (vague reference repointed)
```

DoD: all 6 pure reviewers authored/rewritten through the author→reviewer loop (incl. the new `qa-reviewer` source and the demoted `performance-analyst`); each parses; `description` non-empty; severity unified; `tools:` lock on all 6; `performance-analyst` retiered `do` → `verify` and its acting half stripped; `qa-reviewer` carries the test-assessment half + `applies_to: ["all"]` + `model_tier: verify`.

## Phase 2 — Builders batch (8, incl. pure-builder qa-engineer) + runtime-debugger

Rewrite the 8 Builders (`api-designer`, `backend-engineer`, `db-engineer`, `devops-engineer`, `frontend-engineer`, `migration-engineer`, `mobile-engineer`, `qa-engineer`) plus `runtime-debugger` (the Actor, builder-style tool grants). Per agent, via `instruction-author` → `instruction-reviewer`:

- Conform to D-Skeleton; `## Output` optional for code-only builders; add `## Boundaries & Handoffs` naming the reviewer/sibling to hand off to; omit `tools:` (inherit all).
- Apply F2, the D-Grounding rule, and the F3 concept-name constitution-reference convention.
- **`qa-engineer` — now a PURE BUILDER (test writer)** (D-ReviewerSplit #1): STRIP its assessment/reviewer half (coverage gaps / untested-AC / assertion-quality assessment) — that half is now owned by the new `qa-reviewer` (authored in Phase 1). `qa-engineer` keeps only the test-WRITING role; it produces tests, not findings, so it carries NO severity vocab and `## Output` is optional (code-only builder). `## Boundaries & Handoffs` defers test ASSESSMENT to `qa-reviewer`. Reconsider `qa-engineer`'s `model_tier` (currently `verify`) against the Builders (which are `do`) and flag the FINAL tier with reasoning (D-Bugs-e) rather than leaving it by inertia; omit `tools:` (inherit all).
- `runtime-debugger`: add `{{PROJECT_PATHS}}` (D2/D-Bugs-d); builder-style boundaries (it acts, no reviewer verdict block); omit `tools:` (inherit all).
- F3 `§Conventions` repoint: `frontend-engineer` (lines 14, 15, 57), `mobile-engineer` (lines 15, 59) — state-management → constitution Patterns & Anti-Patterns by concept-name; styling → existing components + framework idiom.
- **api-designer bug fixes**: delete the stray `b` line (`api-designer.md:7`, D-Bugs-a); remove the unexecutable "Validate with the backend-engineer agent before implementation" (`api-designer.md:84`, D-Bugs-b) and replace with `## Boundaries & Handoffs` "consult via the orchestrator" wording.

### Verify

```bash
# Project Paths now in all 9 touched here (the 8 builders + runtime-debugger):
grep -L "{{PROJECT_PATHS}}" src/agents/{api-designer,backend-engineer,db-engineer,devops-engineer,frontend-engineer,migration-engineer,mobile-engineer,qa-engineer,runtime-debugger}.md  # expect: none listed
# No tools: lock on any builder/actor (they inherit all):
grep -l "tools:" src/agents/{api-designer,backend-engineer,db-engineer,devops-engineer,frontend-engineer,migration-engineer,mobile-engineer,qa-engineer,runtime-debugger}.md  # expect: none
# qa-engineer assessment vocab stripped (now owned by qa-reviewer):
grep -niE "ADEQUATE / GAPS FOUND|Verdict:.*GAPS" src/agents/qa-engineer.md  # expect: 0 (assessment-verdict form gone; test-writing 'coverage gaps' language is legitimate)
# api-designer stray-line + unexecutable-instruction gone:
sed -n '6,9p' src/agents/api-designer.md   # confirm no bare 'b' line after the fence
grep -n "Validate with the backend-engineer agent" src/agents/api-designer.md  # expect: 0
# §Conventions repointed in the FE/mobile builders:
grep -n "§Conventions" src/agents/frontend-engineer.md src/agents/mobile-engineer.md  # expect: 0
# Boundaries section present in every builder + runtime-debugger:
grep -l "## Boundaries & Handoffs" src/agents/{api-designer,backend-engineer,db-engineer,devops-engineer,frontend-engineer,migration-engineer,mobile-engineer,qa-engineer,runtime-debugger}.md  # expect: all 9
```

DoD: all 9 rewritten through the loop; each parses; `description` non-empty; `qa-engineer` is a pure test-writer (assessment half removed, no severity vocab, final tier flagged with reasoning); no `tools:` lock on any builder/actor; no `§Conventions` / `framework-idiomatic` weak fallback / stray `b` / unexecutable cross-agent call remains in the touched files.

## Phase 3 — Specials (architect, tech-writer)

Light conform only — `architect` is the reference and is NOT a flatten target; `tech-writer`'s 3 operating modes are preserved. Via `instruction-author` → `instruction-reviewer`:

- **architect**: conform section NAMES to D-Skeleton where they diverge, conform Rules style and constitution/memory phrasing (F2), confirm a `## Boundaries & Handoffs` section exists (its `## Boundaries & Handoffs` already carries this discipline — reconcile the name to the fleet convention or document why it keeps the richer name), confirm the F3 concept-name constitution-reference rule and the D-Grounding rule are present. No substance is removed.
- **tech-writer**: conform section names + Rules style; PRESERVE the 3 operating modes (do not collapse); de-stale the `GENERATE-DOCS-PLAN.md` references (now under `done-plans/`) and the `/onboard`-deprecation framing (D-Bugs-c) after RE-VERIFYING current state — the ~line numbers in the brief are approximate and must be re-grepped before editing; apply F2, F3, D-Grounding.

### Verify

```bash
# Stale plan reference gone from tech-writer:
grep -n "GENERATE-DOCS-PLAN.md" src/agents/tech-writer.md   # expect: 0 (or only an accurate done-plans/ path if one is genuinely still needed — re-verify)
# Boundaries section reconciled in architect (named per fleet convention or justified):
grep -nE "## (Boundaries & Handoffs|Role & Boundaries)" src/agents/architect.md
# tech-writer still carries its 3 modes (count preserved):
grep -niE "mode" src/agents/tech-writer.md   # confirm the 3 operating modes survive the rewrite
```

DoD: both rewritten through the loop; `architect` substance intact and section names reconciled; `tech-writer` 3 modes intact and stale refs removed; both parse; `description`s non-empty.

## Phase 4 — Consumer/command + helper rewire

The split (qa-engineer → qa-engineer + qa-reviewer; performance-analyst demoted) renames roles that DOWNSTREAM consumers reference. This phase rewires every consumer that named `qa-engineer` in a reviewer/assessor role or `performance-analyst` as an optimization-implementer, so no consumer invokes a non-existent role after the split. It runs AFTER the agent-body phases (1–3) have created `qa-reviewer` and demoted `performance-analyst`, and BEFORE the regenerate/sweep phase.

**The classification rule (applied per site — read the file, classify the role, then edit):**

- A **reviewer/assessor** invocation of `qa-engineer` → repoint to `qa-reviewer`.
- A **test-writing** assignment of `qa-engineer` → STAYS `qa-engineer`.
- An **optimization-implementer** assignment of `performance-analyst` → reroute to the owning engineer (`backend-engineer` / `frontend-engineer` / etc., per the file's layer-to-agent mapping).
- A **reviewer** invocation of `performance-analyst` → STAYS `performance-analyst` (it is now read-only, so the invocation is already correct).

The plan names the rule + the candidate sites verified this session; the execution reads each file to classify the role before editing. Two sub-tracks run inside this phase.

**Ordering constraint (hard):** sub-track A (command markdown) and sub-track B (Python helpers) must land TOGETHER with the agent split (Phases 1–2) so the pipeline is never in a broken intermediate state — a consumer must not reference `qa-reviewer` before the source exists, and the audit panel must not name a `qa-engineer` reviewer after the split makes it a pure builder. Treat Phases 1, 2, and 4 as a single landable unit (commit together or in immediate succession on the same branch tip); Phase 3 (Specials) is independent and may land separately.

### Sub-track A — Command markdown (via `instruction-author` → `instruction-reviewer`)

Apply the markdown spec-edit loop (route-spec-edits-through-agent-flow). Candidate sites verified this session:

- **`qa-engineer` reviewer-role → `qa-reviewer`** (classify first, then repoint):
  - `src/_pending/commands/review.md` — the command's own test-assessment phase (its line 74 already says "does NOT write tests — report only"; the structural split makes that hand-clamp redundant).
  - `src/commands/audit/main.md` + `src/commands/audit/references/report-format.md` + `src/_pending/commands/audit.md` — the adversarial review panel.
  - `src/_pending/commands/fix.md` — test assessment.
  - `src/_pending/commands/refactor.md` — test assessment.
  - `src/CLAUDE.md` — three reviewer-role mentions (`/fix` Phase 6 "Test assessment (qa-engineer agent)" line 105; `/refactor` Phase 6 "Test assessment (qa-engineer agent…)" line 117; `/audit` description "Launches code-reviewer, architect, qa-engineer, and security-reviewer in adversarial mode" line 126) — all three repoint to `qa-reviewer`. These are role-name swaps within existing lines, budget-neutral re: the `08-CLAUDE-MD-COMMAND-TRIM-PLAN.md` always-on budget (no length change).
- **`qa-engineer` test-writing role → KEEP `qa-engineer`** (no edit beyond confirming the role reads as test-writing, not assessment):
  - `src/commands/breakdown/main.md`, `src/commands/plan/main.md`.
- **`performance-analyst` implementer-role → reroute to owning engineer**:
  - `src/commands/breakdown/main.md`, `src/commands/plan/main.md`, `src/_pending/commands/_agent-assignment.md`.
  - `performance-analyst` reviewer-role in `src/_pending/commands/review.md` STAYS (already read-only there).

#### Verify

```bash
# qa-engineer reviewer-role sites repointed to qa-reviewer (read each match to confirm role first):
grep -rn "qa-engineer" src/commands/audit/main.md src/commands/audit/references/report-format.md src/_pending/commands/{review,audit,fix,refactor}.md  # expect: only test-WRITING mentions remain (none in audit/review/fix/refactor assessment role)
grep -rn "qa-reviewer" src/commands/audit/main.md src/commands/audit/references/report-format.md src/_pending/commands/{review,audit,fix,refactor}.md  # expect: present where assessment was repointed
# src/CLAUDE.md reviewer-role mentions (fix/refactor/audit) repointed to qa-reviewer:
grep -n "qa-engineer" src/CLAUDE.md   # expect: 0
grep -n "qa-reviewer" src/CLAUDE.md   # expect: 3 (the /fix + /refactor + /audit reviewer-role mentions)
# Test-writing assignments still name qa-engineer:
grep -n "qa-engineer" src/commands/breakdown/main.md src/commands/plan/main.md  # expect: present (test-writing role kept)
# performance-analyst no longer assigned as an implementer in breakdown/plan/_agent-assignment:
grep -rn "performance-analyst" src/commands/breakdown/main.md src/commands/plan/main.md src/_pending/commands/_agent-assignment.md  # expect: 0 implementer assignments (rerouted to owning engineer)
```

DoD: every `qa-engineer` reviewer/assessor invocation in the listed command files (incl. the three `src/CLAUDE.md` `/fix` + `/refactor` + `/audit` mentions) repointed to `qa-reviewer`; every `qa-engineer` test-writing assignment confirmed-kept; every `performance-analyst` implementer assignment rerouted to the owning engineer; the read-only `performance-analyst` reviewer invocation in `review.md` left intact; all edits through the `instruction-author` → `instruction-reviewer` loop.

### Sub-track B — Python helpers (via `python-engineer` → `python-reviewer`, the helper loop — NOT the markdown loop)

The audit helper hard-codes the adversarial REVIEWER panel as a Python constant. Verified this session:

- `src/devforge/lib/_audit/_preflight.py:21` — `_AUDIT_AGENTS = ["architect", "code-reviewer", "qa-engineer", "security-reviewer"]` is the audit's adversarial reviewer panel; change `qa-engineer` → `qa-reviewer`. The docstring at `_preflight.py:275` ("The four agents are: architect, code-reviewer, qa-engineer, security-reviewer") names `qa-engineer` — update it to `qa-reviewer` in the same edit (the "four agents" count is unchanged).
- **`_FOCUS_BLOCKS` rename is a HARD-coupled requirement, atomic with `_AUDIT_AGENTS`.** `src/devforge/lib/_audit/_scope.py` keys `_FOCUS_BLOCKS` on agent NAMES (`_scope.py:45` = `"qa-engineer"`), and `render_agent_brief` raises `ValueError` (`_scope.py:569`, the `if agent not in _FOCUS_BLOCKS:` guard) when its `agent` arg is not a `_FOCUS_BLOCKS` key. So `_AUDIT_AGENTS` (in `_preflight.py`) and the `_FOCUS_BLOCKS` key (in `_scope.py`) MUST be renamed `qa-engineer` → `qa-reviewer` TOGETHER (atomically): if the panel names `qa-reviewer` but `_FOCUS_BLOCKS` still keys `qa-engineer`, `render_agent_brief("qa-reviewer", …)` raises `ValueError` and `/audit` breaks at runtime.
- Update the `tests/lib/_audit/` tests that assert on `_AUDIT_AGENTS` (any test expecting `qa-engineer` in the panel) to expect `qa-reviewer`.
- Remaining Python mentions to update in this same sub-track (read first; `code-reviewer` references are UNCHANGED): `src/devforge/lib/_audit/_cli.py:1342` (help text), `src/devforge/lib/_audit/_report.py:412-415` (comments describing qa-engineer findings → qa-reviewer), `src/devforge/lib/audit_helper.py:4` (docstring agent ensemble). Verify whether `qa-engineer`/`performance-analyst` appear in a reviewer role in each before editing; leave non-reviewer references untouched.
- The `_implement` review-loop modules (`src/devforge/lib/_implement/{_cli.py,_state.py,_cmds_review_loop.py}`) stay as already written — audit them for any qa/perf reviewer-role / audit-for-qa/perf-references mention and update consistently (read first; leave non-reviewer references untouched).

#### Verify

```bash
# Audit panel now names qa-reviewer, not qa-engineer:
grep -n "qa-reviewer" src/devforge/lib/_audit/_preflight.py   # expect: in _AUDIT_AGENTS + the docstring
grep -n "qa-engineer" src/devforge/lib/_audit/_preflight.py   # expect: 0
# No stray qa-engineer reviewer-role / performance-analyst implementer-role in the audit + implement helpers:
grep -rn "qa-engineer" src/devforge/lib/_audit src/devforge/lib/_implement   # expect: 0 reviewer-role mentions (read each to confirm)
# Audit helper tests pass with the renamed panel:
python -m pytest tests/lib/_audit/
```

DoD: `_AUDIT_AGENTS` contains `qa-reviewer` not `qa-engineer` (panel count still 4); the `_preflight.py:275` docstring updated; every `tests/lib/_audit/` test asserting on the panel updated and the full `tests/lib/_audit/` suite passes; the sibling `_audit` + `_implement` modules carry no `qa-engineer`-reviewer / `performance-analyst`-implementer reference; `code-reviewer` references untouched; all edits through the `python-engineer` → `python-reviewer` loop.

## Phase 5 — Regenerate, test, install-ride, cross-ref sweep

Regenerate the emitted agents and prove the fleet (now **17**) is consistent, the rewire is complete, and the build is green.

- Run `scripts/generate-agents.py --src src/agents --target <dir>` (both args are required) to regenerate `<dir>/.claude/agents/` from the **17** rewritten/new sources (the new `qa-reviewer` included). Use a scratch `<dir>` for verification (see the `### Verify` block).
- Run `tests/scripts/test_generate_agents.py` (frontmatter structure + tools handling) — must pass. Run `tests/lib/_audit/` too (the rewire changed `_AUDIT_AGENTS`) — must pass.
- Install-ride verify: **17** emitted `.claude/agents/*.md`; no `{{` leaks in emitted agents; `tools:` lines emit for exactly the **6** pure reviewers; every `description` non-empty.
- Cross-ref sweep across `src/agents/`: `grep §Conventions` → 0; `grep "framework-idiomatic"` → 0 (the weak fallback is fully replaced by D-Grounding; the D-Grounding rule's quoted 'framework idiom' is legitimate and not swept); severity vocab consistent across the 6 pure reviewers (only Critical/High/Medium/Info; no Warning/ADEQUATE/GAPS/PASS-FAIL/high-med-low survives — note `qa-engineer` is no longer a reviewer, so its `ADEQUATE/GAPS` must be gone there too).
- Rewire-completeness sweep: no command or helper still invokes `qa-engineer` in a reviewer/assessor role, and no command/helper still assigns `performance-analyst` as an implementer.

### Verify

```bash
# Regenerate into a scratch target dir (the emitter writes to <target>/.claude/agents/;
# both --src and --target are required — a bare invocation errors and emits nothing):
rm -rf /tmp/forge-phase5-verify && mkdir -p /tmp/forge-phase5-verify
python scripts/generate-agents.py --src src/agents --target /tmp/forge-phase5-verify
python -m pytest tests/scripts/test_generate_agents.py
python -m pytest tests/lib/_audit/   # the rewire changed _AUDIT_AGENTS
# Exactly 17 emitted agents (the 16 existing + new qa-reviewer):
ls /tmp/forge-phase5-verify/.claude/agents/*.md | wc -l   # expect: 17
# No placeholder leaks in emitted agents:
grep -rn "{{" /tmp/forge-phase5-verify/.claude/agents/   # expect: 0
# tools: line emitted for exactly the 6 pure reviewers:
grep -l "^tools:" /tmp/forge-phase5-verify/.claude/agents/*.md   # expect: code-reviewer, security-reviewer, ac-verifier, design-auditor, performance-analyst, qa-reviewer
# Every emitted agent has a non-empty description:
grep -rnE "^description: *(\"\"|'')? *$" /tmp/forge-phase5-verify/.claude/agents/   # expect: 0
# Fleet-wide cross-ref sweep over the 17 sources:
grep -rn "§Conventions" src/agents/        # expect: 0
grep -rn "framework-idiomatic" src/agents/     # expect: 0 (old weak fallback phrasing; the D-Grounding rule's quoted 'framework idiom' is legitimate and not swept)
grep -rnE "Warning|high/medium/low" src/agents/{code-reviewer,security-reviewer,ac-verifier,design-auditor,performance-analyst,qa-reviewer,qa-engineer}.md  # expect: 0 (dead severity vocab; verdicts like PASS/FAIL, ADEQUATE/GAPS are legitimate and not swept)
# Rewire complete — no qa-engineer reviewer-role and no performance-analyst implementer-role downstream
# (read each remaining qa-engineer match to confirm it is a test-WRITING assignment, not assessment):
grep -rn "qa-engineer" src/commands src/_pending  # expect: only test-writing assignments (breakdown/plan) remain
grep -n "qa-reviewer" src/devforge/lib/_audit/_preflight.py   # expect: present in _AUDIT_AGENTS (panel renamed)
grep -n "qa-engineer" src/devforge/lib/_audit/_preflight.py   # expect: 0
# src/CLAUDE.md reviewer-role mentions repointed:
grep -n "qa-engineer" src/CLAUDE.md                                   # expect: 0
# _scope.py _FOCUS_BLOCKS key renamed (both directions — atomic with the panel):
grep -n "qa-engineer" src/devforge/lib/_audit/_scope.py              # expect: 0
grep -n "qa-reviewer" src/devforge/lib/_audit/_scope.py              # expect: 1 (the _FOCUS_BLOCKS entry)
# other audit helper mentions repointed:
grep -rn "qa-engineer" src/devforge/lib/_audit/_cli.py src/devforge/lib/_audit/_report.py src/devforge/lib/audit_helper.py  # expect: 0
```

DoD: generator runs clean; `test_generate_agents.py` AND `tests/lib/_audit/` pass; exactly 17 emitted agents; zero `{{` leaks; `tools:` on exactly the 6 pure reviewers; every `description` non-empty; the cross-ref sweeps return their expected counts; the rewire-completeness sweep confirms no `qa-engineer` reviewer-role and no `performance-analyst` implementer-role survives in any command or helper — explicitly including `src/CLAUDE.md` (0 `qa-engineer`) and the named `_audit/` helper files (`_scope.py` `_FOCUS_BLOCKS` key, `_cli.py`, `_report.py`, `audit_helper.py` all 0 `qa-engineer`).

## Out of scope (do NOT plan here)

- **Convention-capture work** — teaching `/constitute` or `/generate-docs` to extract styling/state-management rules, reconciling constitution section-number/name drift, and resolving the "Conventions"-vocabulary fragmentation — is DEFERRED to a separate companion plan (`16-CONVENTION-CAPTURE-PLAN.md`), owned by other sessions. See `## Companion / future work`.
- **Build-side changes** — `scripts/generate-agents.py`, the `emit_claude` emitter, the meta-block contract (`name`/`description`/`model_tier`/`tools`/`applies_to` field set), and `applies_to` semantics are untouched. Agent SOURCE files only (one new source `qa-reviewer.md` IS added, but it conforms to the fixed meta-block contract — it does not change the contract or the generator).
- **`architect` charter substance** — `architect.md` is the reference; section NAMES and phrasing are conformed, its boundaries/consultation substance is NOT removed (it aligns with `14-ARCHITECT-NOT-IMPLEMENTER-PLAN.md`, which holds the charter as authority).

## Companion / future work

- `16-CONVENTION-CAPTURE-PLAN.md` — styling/state-management CAPTURE (teaching `/constitute` / `/generate-docs` to extract these), constitution section-name/number drift reconciliation, and "Conventions"-vocabulary defragmentation. Owned by other sessions; this plan only repoints the dangling `§Conventions` anchor (F3) and adds the D-Grounding fallback, it does not build capture.

## Context for next session

- This plan rewrites the BODY (and trims the `description`) of all 16 existing `src/agents/*.md` sources to the D-Skeleton, ADDS one new source (`qa-reviewer`, roster 16 → **17**), and rewires the commands + Python helpers that named the old roles; it does NOT touch the build contract (`generate-agents.py` / `emit_claude` / meta block / `applies_to`).
- **D-ReviewerSplit is RESOLVED toward a SPLIT** (no longer an open decision; no kickoff confirmation required). The three nominal code-modifying reviewers are NOT symmetric: `qa-engineer` SPLITS into a pure-builder test-writer (`qa-engineer`) + a NEW read-only assessor (`qa-reviewer`); `performance-analyst` is DEMOTED to a pure read-only analyst (retiered `do` → `verify`); `runtime-debugger` is an UNCHANGED actor. Four families now: 6 pure read-only reviewers (tools-locked) / 8 builders / 1 actor / 2 specials.
- `architect.md` is the REFERENCE for the boundaries + consulting discipline (its `## Boundaries & Handoffs` + `## Consulting Specialists` are back-ported in lighter form across the fleet). Do NOT flatten `architect` or `tech-writer` — Specials keep richer substance; `tech-writer` keeps its 3 operating modes.
- The new rewire phase (Phase 4) spans BOTH agent-flow loops: sub-track A (command markdown) via `instruction-author` → `instruction-reviewer`, sub-track B (Python helpers, incl. `_audit/_preflight.py` `_AUDIT_AGENTS`) via `python-engineer` → `python-reviewer`. Phases 1, 2, and 4 must land together (a consumer must not reference `qa-reviewer` before the source exists, and the audit panel must not name a `qa-engineer` reviewer after the split).
- Verified-settled facts: `SEVERITY_ENUM = ("Critical","High","Medium","Info")` at `findings_schema.py:49`; `tools:` emitter support live + tested (`tests/scripts/test_generate_agents.py`); `{{AGENT_LIST}}` is filename-derived (`_configure/_render.py:169-188`), so F1 description-trim is contained AND the new `qa-reviewer` will auto-appear in `{{AGENT_LIST}}` once its source exists; `api-designer.md:7` stray `b` + `:84` unexecutable cross-agent call confirmed against the file this session; `_AUDIT_AGENTS = ["architect","code-reviewer","qa-engineer","security-reviewer"]` at `_audit/_preflight.py:21` (+ docstring naming the four at `:275`) confirmed this session.
- The five D-Bugs are folded into the phase that touches each file: a/b → Phase 2 (api-designer); c → Phase 3 (tech-writer, RE-VERIFY ~line numbers first); d → Phase 1 (ac-verifier) + Phase 2 (runtime-debugger); e (model_tier audit) → Phase 1 (`performance-analyst` `do`→`verify` resolved; `design-auditor` flagged) + Phase 2 (`qa-engineer` builder tier reconsidered).
- The `tech-writer` stale-ref line numbers (~3, 32, 270, 325) and the api-designer `:84` line are stated in the brief; re-grep before editing — line numbers drift as the body is rewritten.

## When resuming work

1. Re-read this plan in full + `src/agents/architect.md` (the reference) + the canonical body skeleton (D-Skeleton). If Phase 0 has run, read `src/agents-AUTHORING.md` (the authoring doc — it lives OUTSIDE `src/agents/` so the generator glob ignores it).
2. D-ReviewerSplit is RESOLVED (split: new `qa-reviewer`, demoted `performance-analyst`, unchanged `runtime-debugger`) — no kickoff confirmation needed. Proceed straight into the batches.
3. Check `git log --oneline` on `develop-2.0-init` for the last landed phase. Phases 0 and 3 are independent batches; **Phases 1, 2, and 4 are a single landable unit** (the split + its consumer rewire must land together so no consumer references a role that does not yet exist or no longer plays that role).
4. Run phases in order (0 → 1 → 2 → 3 → 4 → 5). Every agent-file rewrite AND every command-markdown rewire (Phase 4 sub-track A) goes through `instruction-author` → `instruction-reviewer`; the Phase 4 sub-track B Python-helper edits go through `python-engineer` → `python-reviewer` (the helper loop). Verify Claude-Code-integration syntax (frontmatter, `tools:`, model aliases) via the `claude-code-guide` agent before writing agent files.
5. After all rewrites + the rewire, run Phase 5 (regenerate → 17 emitted agents + `test_generate_agents.py` + `tests/lib/_audit/` + install-ride + cross-ref + rewire-completeness sweeps) before declaring DONE.
6. Commit alongside the work in repo commit style (lowercase, terse, scope prefix — e.g. `feat(agents): split qa reviewer + standardize bodies + tools-lock`).

## Related plans

- `14-ARCHITECT-NOT-IMPLEMENTER-PLAN.md` — holds `architect.md` as the authoritative charter (it is correct, not edited there); this plan conforms `architect`'s section NAMES/phrasing only and preserves its boundaries/consultation substance. Keep the two consistent: neither removes the "architect shapes, never codes" discipline. **The `performance-analyst` demotion (D-ReviewerSplit #2) applies the SAME principle as 14** — analysts/reviewers recommend, engineers implement; the analyst reports the optimization and the owning engineer (or `/refactor`) applies it, exactly as 14 reroutes the architect out of the implementer seat.
- `08-CLAUDE-MD-COMMAND-TRIM-PLAN.md` — the always-on `src/CLAUDE.md` budget discipline that motivates putting the authoring doc in `src/agents-AUTHORING.md` rather than the overlay CLAUDE.md.
- `16-CONVENTION-CAPTURE-PLAN.md` — companion (future, other sessions): styling/state-management capture + constitution drift reconciliation; this plan defers all capture work to it.
