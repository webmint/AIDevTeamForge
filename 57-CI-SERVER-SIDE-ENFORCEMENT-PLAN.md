# 57 — CI Server-Side Gate Enforcement

**Status:** SKELETON — NOT STARTED. Phase 0 (investigation + ratify) is the gate. No code.
**Type:** BUILD plan (CI config + a headless gate runner). The single biggest enterprise gap.
**Branch:** `develop-2.0-init`.
**Created:** 2026-07-10, seeded from an enterprise-readiness gap analysis (this session).

---

## Problem

Every mechanical forcing-function gate the framework ships runs **local, in the dev's own pipeline** — at `/breakdown` PHASE 3.5, `/implement`'s per-task gate, and the **opt-in** `pre-commit-forcing-functions.sh` hook. All three are bypassable:

- `/breakdown`, `/implement` gates only fire if the dev runs the command. Nothing forces them.
- Pre-commit hook is opt-in AND skippable with `git commit --no-verify`.
- Memory (plan 41): *"repo has no CI/Makefile, so the pytest test IS the gate."* That is a framework-dev posture, not an enterprise one.

Enterprise enforcement = **server-side, in the merge pipeline, unbypassable by any individual dev**. A gate a dev can skip is not a gate an org can rely on.

## Why it matters (enterprise)

- Merge-blocking CI is the ONLY place a gate is truly unbypassable (branch protection + required checks).
- "Prove the gate ran on every merge" is a compliance question. Local hooks can't answer it; CI check history can.
- At 50 devs, "did everyone run `/implement`'s gate?" has one honest answer without CI: no.

## Believed current state — VERIFY in Phase 0

- [ ] Confirm which gates are pure-Python / headless-capable (no LLM dispatch, no MCP): `verify-agent-roster`, `verify-contract-chain`, `verify-ac-coverage`, `verify-manifest-present`, `verify-design-tokens`, `verify-magic-enum`, `verify-cross-layer-imports`, `verify-any-leak`, `verify-universal-defaults`, `verify-forcing-function-keys`.
- [ ] Confirm which gates CANNOT run in CI without a model (LLM-dispatch: `/audit`, `/review`, `/grill`, `/verify`'s finder/refutation slices). These are OUT of the CI-mechanical scope — flag explicitly.
- [ ] Confirm the pre-commit hook template path + its opt-in install point (`src/git-hooks/pre-commit-forcing-functions.sh` → `.devforge/templates/git-hooks/`).
- [ ] Confirm no existing CI wiring anywhere in `install.sh` / `update.sh` / consumer scaffold.

## Core design question (the fork)

The mechanical gates are per-feature / per-task, invoked mid-pipeline against pipeline artifacts (`breakdown-handoff.json`, `design-manifest.json`, task files). A CI job runs on a PR/push against a **repo state**, not a live pipeline. Key question: **what does a headless CI gate actually check?**

- **Option A — replay the shipped gates against committed artifacts.** CI runs the same `*_helper verify-*` verbs against the artifacts committed by plan 37's per-step commits. Requires artifacts to be present in the PR (plan 37 ships them). Cheap, reuses existing verbs.
- **Option B — a dedicated `forge ci-gate` aggregator verb** that discovers the feature under review, runs the applicable subset, exits non-zero on any failure with an aggregated report. New surface, but one clean CI entrypoint.
- **Option C — both:** A is the mechanism, B is the packaging.

## Open questions

- OQ-1: CI provider surface — ship a GitHub Actions workflow template only, or provider-agnostic (a `forge ci-gate` script + example workflows for GHA/GitLab/Jenkins)?
- OQ-2: Where does the CI template live + how installed? (`src/files/`? emitted? opt-in in the wizard like the pre-commit hook?)
- OQ-3: Which gates are safe to make merge-BLOCKING vs merge-WARNING at first rollout? (False-halt in CI blocks the release train — see plan 61.)
- OQ-4: How does CI know which feature/spec a PR touches? (Infer from changed `specs/<feature>/` paths? From branch name?)
- OQ-5: Wrapper mode — CI runs in the install repo or the source/product repo? (Gates target `install_root`; the product repo is traceless. Which repo's CI?)
- OQ-6: Does the LLM-dispatch slice get a CI story at all, or is "CI covers mechanical only, humans+pipeline cover judgment" the honest, documented boundary?

## Phase skeleton (draft — refine in Phase 0)

- **Phase 0** — Investigate current gate inventory; classify headless-capable vs model-required; ratify Option A/B/C + OQ-1..6. Maintainer sign-off gate.
- **Phase 1** — The headless aggregator: `forge ci-gate` (or equivalent) that discovers the feature, runs the applicable mechanical verbs, exits non-zero + aggregated report. python-engineer→python-reviewer. Real git-fixture test.
- **Phase 2** — CI template(s): GHA workflow (+ optional GitLab/Jenkins) invoking Phase 1. Install/opt-in path.
- **Phase 3** — Branch-protection + required-check documentation (how the org wires it unbypassable). Doc, not code.
- **Phase 4** — Boundary doc: what CI covers (mechanical) vs what it structurally can't (LLM judgment). Reconcile `src/CLAUDE.md` + `CHANGELOG.md` + this list.
- **Phase 5** — Consumer e2e (user-driven): a real PR that trips a gate in CI and blocks merge.

## Decisions to ratify (Phase 0)

- D1: A/B/C for the CI check mechanism.
- D2: CI provider scope (GHA-only vs agnostic).
- D3: Blocking vs warning per-gate at rollout.
- D4: LLM-slice CI story (covered / documented-out).

## Dependencies + related

- Depends on plan 37 (per-step artifact commits) — CI needs the artifacts present in the PR to replay gates against. Verify 37's commit coverage first.
- Related: plan 61 (false-halt hardening) — CI blocking is only safe once false-positive rate is near-zero + an audited-bypass path exists.
- Related: plan 58 (audit trail) — CI check history IS part of the compliance evidence.

## Context for next session

This is the highest-leverage enterprise gap. The mechanical gates already exist and are tested; this plan is about *relocating enforcement* from the dev's local pipeline to server-side CI, NOT building new gate logic. The hard intellectual work is Phase 0: cleanly separating headless-capable gates from model-required ones, and deciding what a CI job checks against a static repo state vs a live pipeline.

## When resuming work

1. Read this file in full.
2. Run the Phase 0 verify checklist (grep the helper subpackages for `verify-*` verbs; confirm headless-capable set).
3. Bring the OQ answers to the maintainer BEFORE authoring build phases.
4. Do not write CI templates before D1 (mechanism) is ratified.

## Verify

- Phase 0 done = gate inventory classified + Option ratified + OQs answered, maintainer sign-off recorded here.
- Build phases done = a headless `ci-gate` run trips a real gate and exits non-zero in a CI fixture; consumer e2e blocks a real PR merge.
