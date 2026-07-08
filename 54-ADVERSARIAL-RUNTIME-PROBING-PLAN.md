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

- **Python helpers** (a new `src/devforge/lib/_probe/` or similar + JS collectors) — `python-engineer` → `python-reviewer`, test-first (round-trip parsers via the real producer).
- **Command / agent markdown** (any new command `main.md` + `references/`, any new `src/agents/*.md`) — `instruction-author` → `instruction-reviewer` + `claude-code-guide` (ships into `.claude/`).
- If a new agent is added: register in the emitter `_PROMOTED` and run `scripts/verify-agent-reachability.py` (plan 41) so it is not born an orphan.
- Cross-check after every edit (grep affected identifiers/paths/verbs); update `src/CLAUDE.md` catalog + `CHANGELOG.md`.

## Phase 0 — Maintainer design-ratification gate (GATE — no code)

This plan records the DIRECTION, not a ratified design. Phase 0 is a design session that settles OQ-1…OQ-5 and the invariants above, then writes the build phases. NO build before sign-off. Do not start until plan 51's F4/F1/F5/F3 have shipped (their delivered machinery is the reuse baseline).

**Verify (Phase 0):** OQ-1…OQ-5 resolved; the four invariants ratified or amended; the build phases authored; the reuse-vs-fork decisions named against the plan-51/plan-53 machinery that now exists.

## When resuming work

1. Confirm plan 51's F4/F1/F5/F3 shipped (this plan reuses their machinery — especially plan 53's `_design/js` browser substrate + non-gating advisory, and any runtime-provisioning helpers plan 51 added).
2. Re-read this file + plan 51 Finding 2 + plan 23 (`/grill`, the structural sibling) + plan 19 (`/audit` refutation precision, the anti-false-positive discipline).
3. Run Phase 0 (design ratification) — settle the OQs, lock the invariants (especially advisory-never-gates), author the build phases.
4. Build behind the agent loops above. The non-negotiable acceptance bar: a clean feature MUST NOT produce a false NEEDS-WORK (mirror plan 34's clean-feature regression test) — flake control is the make-or-break.

## Provenance

Grounded from plan 51 Finding 2 (two Explore investigators, 2026-07-06: no exploratory/adversarial runtime testing anywhere in the pipeline; every runtime check verifies stated ACs / stated design only). Re-confirmed against post-plan-53 state 2026-07-08 (the VLM advisory is visual, not behavioral; the gap stands). Split to its own plan per maintainer direction 2026-07-08.
