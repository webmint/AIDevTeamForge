# 54 — Adversarial Runtime Probing (the exploratory-testing gap)

**Status: NOT STARTED — deferred from `51-DETECTION-COVERAGE-GAPS-PLAN.md` Finding 2. Design-direction record + open questions; awaiting (a) the plan-51 F4/F1/F5/F3 deliveries as precedent AND (b) a Phase 0 design-ratification gate before any build. No code.**

On `develop-2.0-init`. Split out of plan 51 per maintainer direction (2026-07-08): F2 is the largest of plan 51's findings, carries the highest *weaken-risk* (flake / false-positives), and needs its own careful design — building it in the same loop as the safe additive findings would risk weakening the framework, contradicting the "strengthen not weaken" directive that governs plan 51's build. This plan is the handoff: it will be picked up and EXTENDED (design ratified, then built) once plan 51's F4/F1/F5/F3 ship, because those deliveries establish reusable precedent (see `## Reuse precedents`).

## Problem — the pipeline never tests for the unstated

Grounded from plan 51 Finding 2 (investigator-confirmed 2026-07-06, re-confirmed against post-plan-53 state 2026-07-08):

Every runtime check in the pipeline verifies **pre-stated** expectations:
- `ac-verifier` (`src/agents/ac-verifier.md`) — verifies each STATED acceptance criterion (`runtime-assisted` mode probes the running app, but only against the ACs).
- `/review` finders (`src/commands/review/main.md:141`) — code-read the assembled diff.
- `design-auditor` — checks conformance to a STATED design reference (plan 53) + (once plan 51 F4 lands) accessibility against WCAG.
- `/verify` mechanical checks (`src/commands/verify/main.md:189-221`) — type-check / lint / build / test against PRE-STATED standards.

**Nothing probes the running app for UNSTATED failure modes** — abuse input, malformed sequences, boundary values, hostile ordering, states the ACs never named. Plan 53's VLM advisory added holistic *visual* judgment, not behavioral probing — it does not close this.

Why it matters: this is the "a human can miss something" class from the origin conversation — and the framework misses it too. The human is the SOLE exploratory tester, with zero automated backstop. The highest-value bugs (the ones nobody thought to spec) live exactly here. For any non-trivial app this is a real coverage hole, not a theoretical one.

## Why deferred + why its own plan

- **Highest weaken-risk of plan 51's findings.** An adversarial prober is non-deterministic and flake-prone. A prober that cries wolf (false NEEDS-WORK on a clean feature) gets ignored, then trusted-off — strictly worse than no prober. The framework already fought exactly this trust-erosion in plans 19 (audit false-positive precision) and 34 (verify hygiene false-positive). Rushing this weakens; it must be designed against flake from the start.
- **Largest build.** A new agent (or a substantial extension) + a dispatch site + a scratch/report chain + an opt-in gate — comparable in size to `/grill` (plan 23) or the `/audit` refutation work.
- **Needs the plan-51 precedents.** Its safe design reuses machinery plan 51's F4 (and plan 53) establish — see below. Building it before those land would fork that machinery.

## Design direction (NOT yet ratified — Phase 0 decides)

The load-bearing constraints, stated up front so a future session designs within them:

1. **Opt-in, never auto-invoked.** Like `/grill` (plan 23) and `/audit`, this is user-triggered — every forge command sets `disable-model-invocation: true`. It is NOT a mandatory pipeline gate.
2. **Advisory — NEVER gates the verdict.** This is the central anti-weaken invariant. A non-deterministic prober must emit "worth a human look" findings, NOT PASS/FAIL that blocks. Model it on plan 53's `## Advisory (non-gating)` layer (design-auditor step 7): clearly labeled, outside any deterministic gate, never folded into `/verify`'s APPROVED/NEEDS-WORK/REJECTED. A finding it surfaces routes a human to look — or routes to `/fix` / `/report-bug` by the human's choice — it does not itself fail the feature.
3. **Grounded / reproducible findings only.** A surfaced finding must carry a concrete reproduction (the exact input/sequence + the observed wrong behavior), not a vague "this might break." Reuse the `src/devforge/lib/_shared/` finding substrate + validation, and consider routing findings through the `_shared/` refutation engine (default-dismiss unless the defect is demonstrated) — the same precision discipline plan 19 gave `/audit`.
4. **Bounded, seeded, and honest about coverage.** Exploratory probing is unbounded by nature; the design must bound it (time / attempt budget / scoped surface) and DECLARE what it did and did not cover — never imply exhaustiveness. Needs a running app + seed data (same provisioning as `ac-verifier runtime-assisted` / `design-auditor`); app down / Chrome MCP absent → NOT-COVERED, honest (the plan-53 honesty-invariant model).

## Reuse precedents (why it waits for plan 51 + rides plan 53)

- **In-pipeline browser-driving substrate (plan 53).** `.devforge/lib/_design/js/*.js` collectors run via Chrome DevTools MCP `evaluate_script`, driven by a read-only reviewer agent — proof the framework can drive the real running app in-pipeline. The prober's interaction layer copies this pattern rather than inventing one.
- **Non-gating advisory layer (plan 53).** design-auditor step 7 / `## Advisory (non-gating)` is the exact "surface-without-gating" shape invariant 2 needs.
- **Runtime provisioning (`ac-verifier`).** The `ac_runtime_url` / `ac_runtime_api_base` / `ac_runtime_cli_command` config + the Chrome-MCP channel already stand up + drive the app — reuse, do not re-solve.
- **Refutation / precision engine (`_shared/`, plans 19/20/23).** `route_refutation` / `apply_verdicts` / validation — the default-dismiss-unless-demonstrated discipline that keeps a noisy finder honest. Candidate for invariant 3.
- **Opt-in standalone-command shape (`/grill`, plan 23).** The closest structural sibling: opt-in, dedicated adversary agent, `_shared/` reuse, findings-only output, user owns the verdict. `/grill` is the design-time adversary; this is the runtime adversary.

## Open design questions (Phase 0 must settle before build)

- **OQ-1 — Where does it live?** A standalone opt-in command (e.g. `/probe`, the runtime sibling of `/grill`) vs a new opt-in sub-step inside `/verify` vs an extension of `ac-verifier`. Leaning standalone (mirrors `/grill`) — but decide against the pipeline-position question (post-`/implement`, pre-`/summarize`, like `/fix`'s window).
- **OQ-2 — New agent vs extend.** A dedicated `adversarial-tester` / `runtime-adversary` agent (mirrors `/grill`'s `devils-advocate`) vs extending `ac-verifier`. A new agent keeps the stated-AC verifier clean and unconflated; but it adds to the roster (run `scripts/verify-agent-reachability.py`, plan 41). Leaning new agent.
- **OQ-3 — Flake control mechanism.** How the design guarantees a clean feature does not produce false NEEDS-WORK: advisory-only (invariant 2) is the primary defense; is a refutation/repro-confirm pass (invariant 3) also required before a finding surfaces? Define the concrete bound (attempt budget, per-finding repro requirement).
- **OQ-4 — Input generation strategy.** How probe inputs are derived — from the ACs (attack *around* each stated criterion), from the data model / API contracts, from fuzzing the boundaries, or LLM-reasoned abuse cases. Scope this; unbounded fuzzing is out.
- **OQ-5 — Absorbs F6 (runtime security).** Plan 51 Finding 6 (security static-only) folded its runtime appetite here — runtime IDOR / authz-bypass / injection-at-runtime probing is a natural sub-case of adversarial runtime testing. Decide whether this plan covers runtime-security probing or leaves it to a future security-specific sibling.

## Agent-loop mechanics (per CLAUDE.md — for the build session)

- **Python helpers** (a new `src/devforge/lib/_probe/` or similar; the first build uses NO bespoke JS collector — see §6/§9 — a thin `_probe/js/error_state_reader.js` is deferred) — `python-engineer` → `python-reviewer`, test-first (round-trip parsers via the real producer).
- **Command / agent markdown** (any new command `main.md` + `references/`, any new `src/agents/*.md`) — `instruction-author` → `instruction-reviewer` + `claude-code-guide` (ships into `.claude/`).
- If a new agent is added: place it in `src/agents/` (auto-discovered by `scripts/generate-agents.py`, no `_PROMOTED` step) and run `scripts/verify-agent-reachability.py` (plan 41) so it is not born an orphan.
- Cross-check after every edit (grep affected identifiers/paths/verbs); update `src/CLAUDE.md` catalog + `CHANGELOG.md`.

## Phase 0 — Maintainer design-ratification gate (GATE — no code)

This plan records the DIRECTION, not a ratified design. Phase 0 is a design session that settles OQ-1…OQ-5 and the invariants above, then writes the build phases. NO build before sign-off. Do not start until plan 51's F4/F1/F5/F3 have shipped (their delivered machinery is the reuse baseline).

**Verify (Phase 0):** OQ-1…OQ-5 resolved; the four invariants ratified or amended; the build phases authored; the reuse-vs-fork decisions named against the plan-51/plan-53 machinery that now exists.

## Phase 0 — DESIGN PROPOSAL (DRAFT — awaiting maintainer ratification)

Everything below is a PROPOSAL that fills in the gate above. Nothing here is ratified or final — each decision is marked PROPOSED / RECOMMENDED / leaning, and the build phases are gated on maintainer sign-off. Per this plan's own rule: **NO build before sign-off.**

### 1. Dependency confirmation + caveat

This plan is blocked until plan 51's F4/F1/F5/F3 ship — they establish the reuse baseline. As of 2026-07-08 all four are marked ✅ SHIPPED in the working tree on `develop-2.0-init`. **Caveat the maintainer must weigh before sign-off:** those four are UNCOMMITTED working-tree changes, and F1/F3/F5 were orchestrator-self-reviewed (the normal `python-reviewer` / `instruction-reviewer` loop stalled) — only F4 went through the normal review loop — and plan 51's consumer/testForge20 e2e is still open. So the reuse baseline EXISTS but is not yet hardened/committed. This proposal's build phases assume those four land clean (committed + review-hardened); if plan 51 regresses under review, the reuse decisions in §5 must be re-checked before build.

### 2. Proposed-ratified invariants

The four `## Design direction` constraints, carried forward as PROPOSED-RATIFIED (sharpened where noted; no new constraints invented):

1. **Opt-in, never auto-invoked.** User-triggered only; every forge command sets `disable-model-invocation: true`. NOT a mandatory pipeline gate.
2. **Advisory — NEVER gates the verdict.** The central anti-weaken invariant. The prober emits "worth a human look" findings, NEVER PASS/FAIL. A surfaced finding routes a human to look — or, by the human's choice, to `/fix` or `/report-bug` — it never itself fails the feature. Modeled on plan 53's `## Advisory (non-gating)` layer (`design-auditor` step 7): clearly labeled, structurally outside any deterministic gate, never folded into `/verify`'s APPROVED / NEEDS-WORK / REJECTED. **Sharpening (PROPOSED):** the non-gating property is STRUCTURAL, not just conventional — the report embeds via a dedicated section flag entirely OUTSIDE the refutation partition (§5), so no `/probe` finding can reach a verdict-bearing bucket even by mislabel.
3. **Grounded / reproducible findings only.** Each finding carries a concrete reproduction (exact input/sequence + observed wrong behavior), never a vague "this might break." Reuse the `src/devforge/lib/_shared/` finding substrate + validation + refutation (default-dismiss unless the defect is demonstrated).
4. **Bounded, seeded, honest about coverage.** A time/attempt budget on a scoped surface; the prober DECLARES what it did and did not cover and never implies exhaustiveness. Needs a running app + seed data (same provisioning as `ac-verifier runtime-assisted` / `design-auditor`); app down / Chrome MCP absent → NOT-COVERED, honest (the plan-53 honesty-invariant model).

### 3. Resolved open questions (each: DECISION (RECOMMENDED) + rationale)

- **OQ-1 — Where does it live? RECOMMEND a standalone opt-in command `/probe`, the runtime sibling of `/grill`.** Pipeline position: post-`/implement`, pre-`/summarize` (the same window `/fix` operates in — code exists and the app can be stood up). Rationale: `/grill` is the design-time adversary between `/plan` and `/breakdown`; `/probe` is the runtime adversary after code exists. Standalone keeps it opt-in and unconflated. **Rejected alternatives:** a sub-step inside `/verify` (would entangle a non-deterministic prober with the deterministic verdict — violates invariant 2's structural separation); extending `ac-verifier` (conflates stated-AC verification with unstated-abuse probing).
- **OQ-2 — New agent vs extend? RECOMMEND a NEW agent `runtime-adversary`** (the runtime twin of `/grill`'s `devils-advocate`). Read-only-plus-browser `tools:` allowlist modeled on `ac-verifier` + `design-auditor` — the Chrome DevTools MCP interaction set (`list_pages` / `navigate_page` / `click` / `fill` / `fill_form` / `press_key` / `hover` / `wait_for` / `evaluate_script` / `take_snapshot` / `take_screenshot` / `list_console_messages` / `list_network_requests` / `resize_page`) plus `Read` / `Grep` / `Glob` / `Bash`. The `resize_page` tool (carried by `design-auditor`) is what makes the list genuinely the union of both models rather than the `ac-verifier` set alone — it enables viewport-abuse probing (mobile-width layout breaks, touch-target violations under reflow, overflow/clip bugs on viewport change). Rationale: keeps the stated-AC verifier clean and unconflated. **Name (maintainer-settled 2026-07-08):** `runtime-adversary` is the locked agent name — the `adversarial-tester` alternative is declined. **Constraint (mechanical):** the new agent is auto-discovered by `scripts/generate-agents.py` when placed in `src/agents/` — NO `_PROMOTED` registration is needed for agents; `_PROMOTED` is a command-only registry. Run `scripts/verify-agent-reachability.py` (plan 41) after authoring to confirm the agent is not an orphan.
- **OQ-3 — Flake control (the make-or-break)? RECOMMEND a layered defense:** (a) advisory-only (invariant 2) is the primary structural defense; (b) a MANDATORY per-finding repro-confirm pass — a surfaced finding must reproduce on a second independent probe run before it is reported, else it is dismissed; this repro-confirm pass is **mandatory and NOT configurable** (unlike the caps below, it cannot be tuned off); (c) route findings through the `_shared/` refutation engine (default-dismiss-unless-demonstrated). **Concrete bound (maintainer-directed proposed defaults 2026-07-08, to validate/tune at Phase 8 e2e — not a blocker):** a per-surface attempt cap of **20** distinct probe attempts per probe surface (a route / endpoint); a per-surface wall-clock cap of **180 seconds**; and a total-run wall-clock cap of **900 seconds** across all surfaces. A scope stops when EITHER its attempt cap or its time cap is reached (whichever comes first) — this is an operational budget, not a discipline rule, so the either/or bound is correct here (not an escape hatch). The three caps are config-overridable via a `probe` config block that mirrors the `design_token_provenance` config-block pattern — a small `{enabled, ...caps}` shape whose PROPOSED keys are `probe_max_attempts_per_surface`, `probe_surface_time_budget_seconds`, and `probe_total_time_budget_seconds` (to be built; named PROPOSED — no such config block exists yet). **Non-negotiable acceptance bar:** a clean feature MUST NOT produce a false NEEDS-WORK — mirror plan 34's clean-feature regression test (§8).
- **OQ-4 — Input generation strategy? RECOMMEND bounded + seeded input derivation:** attack *around* each stated AC (boundary/abuse of each criterion), derive from the data-model / API contracts, and add LLM-reasoned abuse cases. **Blind/unbounded fuzzing is explicitly OUT of scope.**
- **OQ-5 — Absorbs F6 (runtime security)? RECOMMEND folding runtime-security probing (IDOR / authz-bypass / injection-at-runtime) in as ONE category the prober covers, DECLARED non-exhaustive.** Deep/dedicated security probing is left to a future security-specific sibling plan. Rationale: prevents the first build ballooning and keeps the security appetite honest.

### 4. Adjacent decisions (not in the original OQ list — surfaced this session)

- **ADJ-1 — F3 runtime-perf scope. PROPOSE `/probe` stays BEHAVIORAL-only for the first build.** Plan 51's F3 deferred its runtime-WIRE option (fix a), noted as "could fold into plan 54." Runtime perf probing shares the browser channel + advisory shape with behavioral probing. Runtime-perf is explicitly DEFERRED to a later phase or a sibling plan — named here so it is neither silently absorbed nor silently dropped.
- **ADJ-2 — Invariant-2 tension, stated out loud. PROPOSE a standing note.** If the prober NEVER gates, it catches bugs only insofar as a human reads its advisory output. This is a deliberate trust-over-strength choice — the framework already fought false-positive trust-erosion in plans 19 (audit precision) and 34 (verify hygiene). The OQ-3 numeric-budget problem and plans 19/34's false-positive trust-erosion history are the reason this invariant exists. **Standing rule (PROPOSED):** nobody may ever strengthen `/probe` into a verdict gate. Any future desire to do so requires a new plan — the advisory-only design is a structural invariant, not a configuration choice.

### 5. Reuse-vs-fork decisions

Against the machinery verified to exist this session (REUSE = consume unchanged / pass an override arg; no fork):

| Concern | Decision | What it reuses |
|---|---|---|
| Browser-driving substrate | REUSE the Chrome DevTools MCP channel directly — first build: NO bespoke collector (§6) | plan 53 proved the framework can drive the real running app in-pipeline via Chrome DevTools MCP `evaluate_script` (its `src/devforge/lib/_design/js/built_reader.js` collector). `/probe` instead DRIVES the app through the native MCP interaction + observation tools (§6) — no measurement collector in the first build. A DEFERRED `_probe/js/error_state_reader.js` (§6, to be built) would follow plan 53's thin-JS-collector + Python-predicate split (all decision logic in Python, JS only measures). Repo has NO JS test infra and jsdom has no layout engine → any such collector is unit-tested only at e2e; predicates are Python against synthetic fixtures. |
| Non-gating advisory shape | REUSE the embed-outside-the-partition pattern | plan 53's `design-auditor.md` step 7 `## Advisory (non-gating)` + `src/commands/review/main.md` `render-report --design-section` (section embedded ENTIRELY outside the refutation partition — not parsed, not counted in any bucket/headline). `/probe`'s report embeds via its own `--section` flag, fail-soft (unreadable/empty ⇒ omitted + stderr warning, never a non-zero exit). |
| Runtime provisioning | REUSE — do not re-solve | `ac-verifier`'s config keys `ac_runtime_url` / `ac_runtime_api_base` / `ac_runtime_cli_command` and the `runtime-assisted` channel (Chrome-MCP probe first; browser channel for frontend, API channel for backend, CLI command to launch/drive the runtime). |
| Refutation / precision engine | REUSE via `priority=` override (zero fork) | `src/devforge/lib/_shared/` — `route_refutation(findings, present_finders, priority=None)` + `apply_verdicts` (`_verify.py`), `validate_findings` (`_validate.py`), `parse_agent_tmp` / `ParsedFinding` (`_consume.py`). Same zero-fork pattern `/grill` and `/review` use. Default refuter priority is `[code-reviewer, architect, qa-reviewer, security-reviewer]`. |
| Standalone opt-in skeleton | MIRROR `/grill` | `src/commands/grill/main.md` (`disable-model-invocation: true`, 8 PHASES, `$WORKDIR = ${TMPDIR:-/tmp}/forge-grill` scratch chain swept by one `rm -rf`), helper subpackage `src/devforge/lib/_grill/` (`seed_schema` / `_state` / `_preflight` / `_scope` / `_brief` / `_report` / `_cli`), launcher `grill_helper`, single-adversary Task dispatch, findings-only output to `specs/[feature]/grill.md`, WIP-commit via `artifact_helper commit-artifacts`. |

### 6. Proposed command / agent surface (artifacts to be BUILT — none exist yet)

- **Command:** `src/commands/probe/main.md` + `src/commands/probe/references/*.md` (candidate references: an adversarial / abuse-attack checklist, a refutation preamble reused/adapted from `_shared`, a report-format) — to be built (Phase 5).
- **Helper subpackage:** `src/devforge/lib/_probe/` (modules mirroring `_grill/`: `_preflight`, `_scope`, `_brief`, `_report`, `_state`, `_cli`) + launcher `src/devforge/lib/probe_helper{,.py}` — to be built (Phases 1–2, 4). **No bespoke `_probe/js` collector in the first build (settled 2026-07-08):** plan 53's `_design/js` collectors MEASURE static computed-style + geometry bags for fidelity diffing, whereas behavioral probing DRIVES the running app (via the Chrome DevTools MCP interaction tools `navigate_page` / `click` / `fill` / `fill_form` / `press_key` / `hover` / `wait_for` / `evaluate_script`) and OBSERVES outcomes (via `list_console_messages` / `list_network_requests`) — all native Chrome DevTools MCP tools already in `runtime-adversary`'s allowlist (§3 OQ-2). A measurement collector adds nothing the interaction + observation tools do not already provide, so the first build reuses the MCP channel directly. A thin `_probe/js/error_state_reader.js` (a standardized post-action error-state snapshot — visible-error-text scrape / unhandled-rejection detection / broken-layout-after-action check) is DEFERRED — named-not-dropped — for a later phase, added only if it earns its place (mirroring plan 53's thin-JS pattern if so; to be built, does not exist yet).
- **Agent:** `src/agents/runtime-adversary.md` — to be built (Phase 3).
- **Output:** `specs/[feature]/probe.md` (findings-only, advisory, confidence-gated; NO verdict) + a per-feature `probe-state.json` — produced by the built command (Phase 5).

### 7. Proposed build phases (gated on Phase 0 sign-off — do NOT start before it)

Each phase leaves the system buildable + verifiable and names its agent loop. All new-verb names below are PROPOSED (final names settle during the python-engineer loop).

- **Phase 1 — `_probe/` helper skeleton (preflight / scope / state).** Build `src/devforge/lib/_probe/` `_preflight` (setup-chain + feature resolution + source-root/wrapper-mode + running-app / Chrome-MCP presence → NOT-COVERED when absent), `_scope` (resolve the assembled-feature surface to probe), `_state` (per-feature `probe-state.json` status), `_cli` registry, and the `probe_helper{,.py}` launcher. Loop: `python-engineer` → `python-reviewer`, test-first (round-trip any parser via its real producer). **Verify:** helper verbs run standalone; preflight returns NOT-COVERED cleanly with app down / Chrome MCP absent; state round-trips.
- **Phase 2 — Input-generation + brief-rendering layer.** Build `_brief` — derive bounded/seeded probe inputs (attack around each stated AC; derive from data-model / API contracts; LLM-reasoned abuse cases per OQ-4) and render the `runtime-adversary` brief. Loop: `python-engineer` → `python-reviewer`, test-first. **Verify:** brief renders from a synthetic AC + data-model fixture; no unbounded-fuzz path exists.
- **Phase 3 — `runtime-adversary` agent + reachability.** Author `src/agents/runtime-adversary.md` (OQ-2 `tools:` allowlist); place it in `src/agents/` — auto-emitted by `scripts/generate-agents.py`, no registration step — and run `scripts/verify-agent-reachability.py` (plan 41). Loop: `instruction-author` → `instruction-reviewer` + `claude-code-guide`. **Verify:** `scripts/verify-agent-reachability.py` is green (agent reachable, not an orphan); the agent emits on install.
- **Phase 4 — Refutation + repro-confirm wiring (reuse `_shared/`).** Wire `_probe` findings through `route_refutation` / `apply_verdicts` / `validate_findings` from `_shared/` (pass a `priority=` override; no fork) and implement the MANDATORY per-finding repro-confirm pass (OQ-3b: a finding must reproduce on a second independent probe run or be dismissed). Loop: `python-engineer` → `python-reviewer`, test-first. **Verify:** an un-reproduced finding is dismissed; a twice-reproduced finding survives; refutation partition is exercised against synthetic findings.
- **Phase 5 — `/probe` command + references + report.** Author `src/commands/probe/main.md` (mirror `/grill`'s opt-in skeleton, `disable-model-invocation: true`, scratch chain, single `runtime-adversary` Task dispatch, post-`/implement`/pre-`/summarize` position) + `references/*.md` + `_report` (write `specs/[feature]/probe.md`, findings-only advisory, NO verdict; embed via `--section` fail-soft, outside the refutation partition per invariant 2). Add `probe` to the `_PROMOTED` tuple in `scripts/emitters/claude.py` (commands DO need `_PROMOTED` registration — the emitter does not auto-discover commands). Loop: `instruction-author` → `instruction-reviewer` + `claude-code-guide`; `_report` via `python-engineer` → `python-reviewer`. **Verify:** `probe` present in `_PROMOTED` and `/probe` emits on install; a dry run writes a well-formed `probe.md` with no verdict line.
- **Phase 6 — Clean-feature anti-flake regression test (the acceptance bar).** Its own explicit phase. Build a regression test asserting a clean feature produces NO false finding / NO NEEDS-WORK (mirror plan 34's clean-feature regression test). Loop: `python-engineer` → `python-reviewer`. **Verify:** the clean-feature test passes and is wired into the suite as the standing anti-flake gate.
- **Phase 7 — Docs reconcile.** Update `src/CLAUDE.md` command catalog (`/probe` entry + workflow position) + `CHANGELOG.md`; cross-check every touched identifier/path/verb. Loop: `instruction-author` → `instruction-reviewer`. **Verify:** catalog entry present; cross-ref sweep clean.
- **Phase 8 — testForge20 e2e (user-driven).** Run `/probe` on a real feature in a consumer install; confirm advisory-only output, honest NOT-COVERED when the app is down, and no false NEEDS-WORK. **Verify:** user-driven HARD GATE — real-app run produces grounded reproducible findings (or a clean NOT-COVERED) and never gates a verdict.

### 8. Acceptance bar (non-negotiable)

A clean feature MUST NOT produce a false NEEDS-WORK. Flake control is make-or-break: a prober that cries wolf gets trusted-off and is strictly worse than no prober (plans 19/34 history). Phase 6's clean-feature regression test is the mechanical guardian of this bar; the invariant-2 advisory-only structure is its structural backstop.

### 9. Still-open items

**Cleared 2026-07-08 — the three items that stood here are resolved.** For the record they were:

- **OQ-3 numeric budget** → resolved-with-values. Maintainer-directed proposed defaults now live in §3 OQ-3 (per-surface attempt cap 20, per-surface time cap 180 s, total-run time cap 900 s; the three caps config-overridable via a `probe` config block; the per-finding repro-confirm pass mandatory and NOT configurable), subject to tuning at Phase 8 e2e — not a blocker.
- **Bespoke `_probe/js` collector vs reuse** → resolved. The first build uses NO bespoke collector — it drives the app through the native Chrome DevTools MCP interaction + observation tools; a thin `_probe/js/error_state_reader.js` is deferred (named-not-dropped). See §6 (and the §5 browser-driving row).
- **`runtime-adversary` naming** → resolved. Locked to `runtime-adversary` (see §3 OQ-2).

No sub-item decisions remain open. **This does NOT authorize the build:** the broader Phase 0 design proposal (§1–§8) is still DRAFT and awaits maintainer ratification of the invariants, OQ resolutions, and build phases as a whole. Per this plan's own rule, **NO build before final sign-off.**

## When resuming work

1. Confirm plan 51's F4/F1/F5/F3 shipped (this plan reuses their machinery — especially plan 53's `_design/js` browser substrate + non-gating advisory, and any runtime-provisioning helpers plan 51 added).
2. Re-read this file + plan 51 Finding 2 + plan 23 (`/grill`, the structural sibling) + plan 19 (`/audit` refutation precision, the anti-false-positive discipline).
3. Run Phase 0 (design ratification) — settle the OQs, lock the invariants (especially advisory-never-gates), author the build phases.
4. Build behind the agent loops above. The non-negotiable acceptance bar: a clean feature MUST NOT produce a false NEEDS-WORK (mirror plan 34's clean-feature regression test) — flake control is the make-or-break.

## Provenance

Grounded from plan 51 Finding 2 (two Explore investigators, 2026-07-06: no exploratory/adversarial runtime testing anywhere in the pipeline; every runtime check verifies stated ACs / stated design only). Re-confirmed against post-plan-53 state 2026-07-08 (the VLM advisory is visual, not behavioral; the gap stands). Split to its own plan per maintainer direction 2026-07-08.
