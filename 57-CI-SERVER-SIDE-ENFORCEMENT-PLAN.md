# 57 — CI Server-Side Gate Enforcement

**Status:** SKELETON — NOT STARTED. Phase 0 (investigation + ratify) is the gate. No code.
**Type:** BUILD plan (CI config + a headless gate runner). The single biggest enforcement gap — enterprise-critical, but ALSO the one seam that makes Forge's "the framework catches shit" net trustworthy for a solo project.
**Amended:** 2026-07-15 — folded in three findings from a trust/quality analysis session (solo-trust driver; wrapper-mode limit resolving OQ-5; the two-gate-family scoping problem that corrects the "free relocation" premise). New/changed content dated inline.
**Branch:** `develop-2.0-init`.
**Created:** 2026-07-10, seeded from an enterprise-readiness gap analysis (this session).

---

## Problem

Every mechanical forcing-function gate the framework ships runs **local, in the dev's own pipeline** — at `/breakdown` PHASE 3.5, `/implement`'s per-task gate, and the **opt-in** `pre-commit-forcing-functions.sh` hook. All three are bypassable:

- `/breakdown`, `/implement` gates only fire if the dev runs the command. Nothing forces them.
- Pre-commit hook is opt-in AND skippable with `git commit --no-verify`.
- Memory (plan 41): *"repo has no CI/Makefile, so the pytest test IS the gate."* That is a framework-dev posture, not an enterprise one.

Enterprise enforcement = **server-side, in the merge pipeline, unbypassable by any individual dev**. A gate a dev can skip is not a gate an org can rely on.

## Why it matters

**Solo-trust — the primary driver (added 2026-07-15).** This is NOT only an enterprise feature. Every local gate runs inside the dev's own loop, and a gate inside the agent's tool loop is bypassable — empirically, not theoretically: the private kiro-harness gate research found agents route around mid-loop gates, and `anthropics/claude-code#40117` shows Claude Code bypassing `--no-verify` across 6 commits despite deny rules. So even at **1 dev**, "vibe code because the framework catches shit" is only true-*by-construction* once the catch is unbypassable — i.e. server-side. Local + in-loop = mostly-reliable; server-side = the seam closed. The kiro-harness gate-redesign reached the identical conclusion independently: the one hard gate must be out-of-band CI + branch protection (`e6-e8-gate-redesign` memory). This reframes 57 from "enterprise nice-to-have" to "the plan that makes the net trustworthy at any team size."

**Enterprise.**
- Merge-blocking CI is the ONLY place a gate is truly unbypassable (branch protection + required checks).
- "Prove the gate ran on every merge" is a compliance question. Local hooks can't answer it; CI check history can.
- At 50 devs, "did everyone run `/implement`'s gate?" has one honest answer without CI: no.

## Believed current state — VERIFY in Phase 0

- [ ] Confirm which gates are pure-Python / headless-capable (no LLM dispatch, no MCP): `verify-agent-roster`, `verify-contract-chain`, `verify-ac-coverage`, `verify-manifest-present`, `verify-design-tokens`, `verify-magic-enum`, `verify-cross-layer-imports`, `verify-any-leak`, `verify-universal-defaults`, `verify-forcing-function-keys`.
- [ ] Confirm which gates CANNOT run in CI without a model (LLM-dispatch: `/audit`, `/review`, `/grill`, `/verify`'s finder/refutation slices). These are OUT of the CI-mechanical scope — flag explicitly.
- [ ] Confirm the pre-commit hook template path + its opt-in install point (`src/git-hooks/pre-commit-forcing-functions.sh` → `.devforge/templates/git-hooks/`).
- [ ] Confirm no existing CI wiring anywhere in `install.sh` / `update.sh` / consumer scaffold.
- [ ] Confirm whether the Family-2 constitution detectors (`verify-magic-enum` etc.) can scope to a PR DIFF vs only whole-file / whole-path — brownfield adoption depends on it (see "The two gate families").
- [ ] Confirm which gates fail-CLOSED on absent artifact (`verify-manifest-present` known; audit the rest) and design a non-framework-change skip mode for them.

## Core design question (the fork)

The mechanical gates are per-feature / per-task, invoked mid-pipeline against pipeline artifacts (`breakdown-handoff.json`, `design-manifest.json`, task files). A CI job runs on a PR/push against a **repo state**, not a live pipeline. Key question: **what does a headless CI gate actually check?**

- **Option A — replay the shipped gates against committed artifacts.** CI runs the same `*_helper verify-*` verbs against the artifacts committed by plan 37's per-step commits. Requires artifacts to be present in the PR (plan 37 ships them). Cheap, reuses existing verbs.
- **Option B — a dedicated `forge ci-gate` aggregator verb** that discovers the feature under review, runs the applicable subset, exits non-zero on any failure with an aggregated report. New surface, but one clean CI entrypoint.
- **Option C — both:** A is the mechanism, B is the packaging.

## The two gate families — and why this is NOT free relocation (added 2026-07-15)

The plan's premise "relocate the existing gates, no new gate logic" is too optimistic. CI runs against a **static repo snapshot on a machine the dev doesn't control** — a fundamentally different context from the local pipeline, where live artifacts and current-feature scope are always present. Two failure modes surface, split by gate family:

**Family 1 — artifact-structure gates** (`verify-contract-chain`, `verify-ac-coverage`, `verify-agent-roster`, `verify-manifest-present`). Meaningful ONLY for a framework-produced feature. A change made WITHOUT the pipeline (hotfix, dependency bump, docs edit) has no `breakdown-handoff.json` / `design-manifest.json`.
- Required CI behavior: **absent artifact ⇒ skip = PASS** (benign no-op), never fail-closed.
- BUT some deliberately fail-CLOSED today — `verify-manifest-present` fails when `design/reference.html` is present but the manifest is absent (correct for a fresh `/breakdown`; WRONG for an arbitrary PR that touches a template). So CI needs a mode where these self-skip on non-framework changes. **That is new behavior, not relocation.**

**Family 2 — constitution code gates** (`magic-enum`, `any-leak`, `cross-layer`, `design-token`). Repo-wide code-quality rules — their POINT is "no violation anywhere, regardless of author." Firing on a non-framework change is **CORRECT, not a false halt** — that IS the code floor. But two constraints:
- Must **scope to the PR diff**, not whole files / whole repo. Otherwise touching one legacy file with pre-existing violations fails on code the PR never wrote — brownfield adoption dies on turn-on. Whether the detectors can diff-scope today is UNKNOWN — Phase 0 must verify.
- Must be near-zero false-positive before blocking (the plan 61 dependency).

**Net:** CI cannot be "run all gates on every PR." It must **detect what the PR is, run only the applicable gates, scope Family 2 to the diff, and skip Family 1 cleanly when its artifact is absent.** That scoping/skip layer is the real Phase-1 work — the "just relocating" framing is hereby corrected.

## Wrapper-mode limit — resolves OQ-5 (added 2026-07-15)

Server-side enforcement requires **owning the repo's branch protection**. In wrapper mode Forge does not own the product/source repo — and by the plan 25 D5 traceless design it deliberately leaves ZERO footprint there. Consequences:
- The product code (what Family-2 gates must read) lives in the source/product repo; the artifacts + gate binaries live in the install repo (plan 37 commits them to `install_root` only). **No single-repo CI job sees both.**
- Blocking an install-repo PR does not block the product merge — the company ships product code through ITS pipeline, which Forge doesn't control.
- Planting a required `forge-gate` check in the product repo would break traceless (you cannot be both invisible AND an enforced gate in the same repo). The traceless *feature* is exactly what forbids the enforced-gate.

**Resolved shape:**
- **Standalone mode → full enforcement.** Forge lives in the product repo; a required check on its PRs is unbypassable. This is where 57 fully delivers.
- **Wrapper mode → advisory + opt-in-degraded.** Best available: (a) install-repo CI runs the mechanical gates ADVISORY (a signal, not in the product merge's enforcement path); OR (b) the COMPANY explicitly adopts a workflow into their product repo — their call, breaks traceless, and cleanly covers only the artifact-INDEPENDENT Family-2 gates (`magic-enum`/`any-leak`/`cross-layer`), since the artifact-dependent gates need the install repo's files. Document this boundary honestly; do NOT claim wrapper mode gets unbypassable enforcement.

## Open questions

- OQ-1: CI provider surface — ship a GitHub Actions workflow template only, or provider-agnostic (a `forge ci-gate` script + example workflows for GHA/GitLab/Jenkins)?
- OQ-2: Where does the CI template live + how installed? (`src/files/`? emitted? opt-in in the wizard like the pre-commit hook?)
- OQ-3: Which gates are safe to make merge-BLOCKING vs merge-WARNING at first rollout? (False-halt in CI blocks the release train — see plan 61.)
- OQ-4: How does CI know which feature/spec a PR touches, AND how does each gate scope? (Infer feature from changed `specs/<feature>/` paths? From branch name?) — now coupled to the two-gate-family split: Family-1 skip-on-absent-artifact + Family-2 diff-scope. See "The two gate families" section.
- OQ-5: Wrapper mode CI repo — **RESOLVED 2026-07-15**: standalone = full enforcement; wrapper = advisory + opt-in-degraded. See "Wrapper-mode limit" section.
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
- D5: The scoping/skip layer — Family-1 skip-on-absent-artifact + Family-2 diff-scope. Confirm it's new build, not config, and own the estimate (added 2026-07-15).
- D6: Wrapper-mode story — advisory-only in install repo vs company-opt-in workflow in product repo (or both, documented boundary). Resolved shape in "Wrapper-mode limit"; ratify the build target (added 2026-07-15).

## Dependencies + related

- Depends on plan 37 (per-step artifact commits) — CI needs the artifacts present in the PR to replay gates against. Verify 37's commit coverage first.
- Related: plan 61 (false-halt hardening) — CI blocking is only safe once false-positive rate is near-zero + an audited-bypass path exists.
- Related: plan 58 (audit trail) — CI check history IS part of the compliance evidence.

## Context for next session

This is the highest-leverage enforcement gap — enterprise-critical AND the seam that makes "the framework catches shit" trustworthy at 1 dev (see Why it matters). The mechanical gates already exist and are tested, but this plan is **NOT pure relocation**: CI needs a scoping/skip layer (Family-1 skip-on-absent-artifact, Family-2 diff-scope — see "The two gate families") that may be new build. And the enforcement guarantee is **standalone-only**: wrapper mode caps out at advisory/degraded (see "Wrapper-mode limit"). The hard Phase-0 work: separating headless-capable gates from model-required ones, confirming diff-scope capability, and accepting the wrapper limit.

## When resuming work

1. Read this file in full.
2. Run the Phase 0 verify checklist (grep the helper subpackages for `verify-*` verbs; confirm headless-capable set).
3. Bring the OQ answers to the maintainer BEFORE authoring build phases.
4. Do not write CI templates before D1 (mechanism) is ratified.

## Verify

- Phase 0 done = gate inventory classified + Option ratified + OQs answered, maintainer sign-off recorded here.
- Build phases done = a headless `ci-gate` run trips a real gate and exits non-zero in a CI fixture; consumer e2e blocks a real PR merge.
