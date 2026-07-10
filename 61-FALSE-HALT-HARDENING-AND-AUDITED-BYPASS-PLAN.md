# 61 — False-Halt Hardening + Audited Bypass

**Status:** SKELETON — NOT STARTED. Phase 0 (investigation + ratify) is the gate. No code.
**Type:** BUILD plan (gate precision + a bypass-with-evidence mechanism). The prerequisite for making any gate merge-BLOCKING (plan 57).
**Branch:** `develop-2.0-init`.
**Created:** 2026-07-10, seeded from an enterprise-readiness gap analysis (this session).

---

## Problem

Mechanical gates trade false-negatives for false-positives: a hard gate that HALTs on a legit-but-unpredicted variation blocks correct work. Two real incidents already root-caused in consumer installs:

- **Plan 34** — `/verify` false-positive NEEDS WORK on a CLEAN feature (hygiene regexes ran over prose/spec files; scope-creep flagged pipeline-written artifacts). Fixed reactively.
- **Plan 38** — `backend-engineer` assigned to an Electron main-process file (no backend stack) → `/breakdown` roster gate would halt on a legit desktop-app structure.

These were caught because the founder root-caused them. At enterprise scale:

- A false-halt in **local** flow = one annoyed dev.
- A false-halt in **merge-blocking CI** (plan 57) = a blocked release train + multiple angry teams + eroded trust in the gate.

Gap = the gates are tuned for a sophisticated operator who can diagnose + patch a false-halt. Enterprise needs (a) **near-zero false-positive rate before rollout** and (b) **an escape-with-audit path** — never a silent `--no-verify`, but not a hard wall either.

## Why it matters (enterprise)

- Every false-halt erodes operator trust; enough of them and teams route around the gate entirely (worse than no gate).
- A hard gate with NO escape path is operationally unacceptable at scale — legit edge cases WILL occur.
- But a silent bypass (`git commit --no-verify`) destroys the enforcement guarantee. The only enterprise-acceptable middle: **bypass that is loud, attributed, and logged** — an override that itself becomes audit evidence (ties to plan 58).

## Believed current state — VERIFY in Phase 0

- [ ] Confirm the false-positive incidents + their fixes: plan 34 (hygiene file-gate denylist; hygiene → advisory in `_verdict.py`), plan 38 (roster gate + Electron table row), plan 40/42 (design gates + carve-outs).
- [ ] Confirm the mandatory plan-34 regression test exists (clean feature + only hygiene flags → APPROVED) — the model for "false-positive regression net."
- [ ] Confirm current bypass surfaces: pre-commit hook is skippable (`--no-verify`); `/breakdown` PHASE 3.5 preamble had a "record in Risk Assessment" bypass that plan 38 CARVED OUT for the roster gate (HARD, no bypass). So the framework has BOTH bypassable and no-bypass gates today — inconsistent policy.
- [ ] Confirm there is NO audited-override mechanism (a logged, attributed, reason-carrying bypass).

## Two workstreams (may fork)

### A — False-positive hardening (precision)

Reduce the rate BEFORE any gate goes merge-blocking.

- A false-positive **regression corpus**: collect the known false-halt cases (plan 34/38/40/42) into a standing test suite each gate must pass. (Precedent: `REGRESSION-ANCHORS.md` from plan 45 pins fixed meta-bugs to guarding tests.)
- A **polyglot/edge-case audit** of each gate: where does its denylist/allowlist/enum assume a stack it might not see? (Plan 34's polyglot denylist stance; plan 38's non-server-host row.)
- A **severity review**: which gates should be HARD-halt vs ADVISORY-warn? (Plan 34 demoted hygiene to advisory — is that the right default for more gates?)

### B — Audited bypass (escape-with-evidence)

For the legit edge a gate can't predict.

- A **loud, attributed, reason-carrying override**: not `--no-verify`, but an explicit `forge override --gate X --reason "..."` that HALTS by default, requires a reason, and writes an audit record (plan 58 evidence).
- **Policy on which gates are overridable**: high-stakes gates (constitution violations, security) may be NON-overridable; structural gates (roster, contract) overridable-with-reason. Ratify the split.
- The override record becomes evidence: "gate X was bypassed by <actor> on <feature> for <reason>" — visible in review, not hidden.

## Open questions

- OQ-1: Is this ONE plan (A+B) or two? (A = precision, B = escape mechanism — separable but both prerequisites for merge-blocking CI.)
- OQ-2: Per-gate HARD vs ADVISORY vs OVERRIDABLE taxonomy — what's the classification + who decides per project? (Ties to plan 60 governance + `set-forcing-functions` config.)
- OQ-3: What false-positive rate is "acceptable for merge-blocking"? Need a measured baseline (ties to A's regression corpus).
- OQ-4: Override mechanism home — a new `override` verb? A config? How does CI (plan 57) honor/record it?
- OQ-5: Which gates are NON-overridable on principle (constitution/security)? (Plan 19 D7 already treats grounded constitution violations as never-silently-dismissed — precedent.)

## Phase skeleton (draft — refine in Phase 0)

- **Phase 0** — Ratify: one plan vs A/B fork; the HARD/ADVISORY/OVERRIDABLE taxonomy; non-overridable set. Maintainer sign-off.
- **Phase 1 (A)** — False-positive regression corpus: collect plan 34/38/40/42 cases into a standing suite. Extend `REGRESSION-ANCHORS.md`.
- **Phase 2 (A)** — Per-gate edge-case/polyglot audit + severity re-classification.
- **Phase 3 (B)** — The audited-override mechanism: `override` verb, reason-required, writes evidence, HARD by default.
- **Phase 4 (B)** — Non-overridable policy for high-stakes gates; CI (plan 57) honors + logs overrides.
- **Phase 5** — Docs + boundary; reconcile with plan 57/58/60.
- **Phase 6** — Consumer e2e (user-driven): a legit edge trips a gate, operator overrides-with-reason, evidence recorded, merge proceeds.

## Decisions to ratify (Phase 0)

- D1: One plan vs A/B fork.
- D2: HARD / ADVISORY / OVERRIDABLE taxonomy + per-gate classification.
- D3: Non-overridable high-stakes set.
- D4: Override mechanism shape + its evidence tie-in.

## Dependencies + related

- **Hard prerequisite for plan 57** — no gate goes merge-blocking until its false-positive rate is bounded (A) and an escape-with-audit exists (B).
- Related: plan 58 (audit trail) — override records ARE evidence.
- Related: plan 60 (governance) — the HARD/OVERRIDABLE classification is a governance decision.
- Precedent: plan 34 (hygiene→advisory), plan 38 (roster HARD no-bypass), plan 45 (`REGRESSION-ANCHORS.md`), plan 19 D7 (never-silently-dismiss constitution violations).

## Context for next session

This plan is the **safety rail for plan 57**. The framework already discovered — reactively, in real consumer installs — that hard gates false-halt on legit edges (plan 34, 38). Making gates merge-blocking without first hardening precision AND providing an audited escape would convert those annoyances into blocked release trains. The intellectual core is D2 (the HARD/ADVISORY/OVERRIDABLE taxonomy): today the framework's gate-severity policy is inconsistent (some bypassable, some carved-out no-bypass) and unratified. Fix that inconsistency, build the regression corpus, then the audited override — and only THEN is plan 57's merge-blocking safe.

## When resuming work

1. Read this file + plan 57 (the thing this de-risks) + plan 34 + plan 38 (the incidents).
2. First task: inventory every gate's current severity (HARD/advisory/bypassable) — expose the existing inconsistency.
3. Build the regression corpus (Phase 1) before touching the override mechanism — precision first, escape second.

## Verify

- Phase 0 done = taxonomy ratified + non-overridable set decided + one-vs-fork decided; sign-off recorded.
- Plan done = a standing false-positive regression corpus is green across all gates AND a loud, attributed, evidence-writing override exists for the overridable set — making plan 57's merge-blocking operationally safe.
