# 58 — Compliance-Grade Audit Trail

**Status:** SKELETON — NOT STARTED. Phase 0 (investigation + ratify) is the gate. No code.
**Type:** BUILD plan (structured evidence emission + export), with a strong decision component up front.
**Branch:** `develop-2.0-init`.
**Created:** 2026-07-10, seeded from an enterprise-readiness gap analysis (this session).

---

## Problem

The framework produces process artifacts — `specs/<feature>/review.md`, `verification.md`, `summary.md`, `audits/YYYY-MM-DD-audit.md`, `grill.md`, plus per-step WIP commits (plan 37). These are **human-readable markdown in a feature directory**. That is good process hygiene, but it is NOT compliance evidence:

- No structured, queryable "who approved / when / which gate passed / what verdict" record.
- No immutable / tamper-evident guarantee (markdown is freely editable, squashed away by `/finalize`).
- Nothing exportable for SOC2 / ISO 27001 / regulated-industry audit.

Gap = between **"artifact exists in the repo"** and **"exportable, attributable, tamper-evident evidence a gate ran and a verdict was rendered."**

## Why it matters (enterprise)

- Regulated orgs must *prove* a control executed on every change. "Trust me, `/verify` ran" fails an audit.
- Auditors want a record independent of the mutable working tree — the `/finalize` squash erases the WIP history where much of the evidence lived.
- Attribution (which human owned the verdict, per plan 17/22 human-verdict gates) must be captured, not just implied.

## Believed current state — VERIFY in Phase 0

- [ ] Confirm `/verify` writes `verification.md` with the verdict (APPROVED / NEEDS WORK / REJECTED) but NO structured attribution/timestamp record. (Note: `Date.now()`-class timestamps are unavailable in some helper contexts — check how the pipeline stamps time today.)
- [ ] Confirm `/finalize`'s squash collapses the per-step WIP commits (plan 25/37) — i.e. the granular evidence trail is intentionally erased from git history.
- [ ] Confirm what plan 37 / plan 49 persist vs treat as ephemeral (`spec-stamps.jsonl` is VERSIONED — is it evidence-grade?).
- [ ] Confirm human-verdict capture points: `/implement` PHASE 7 gate, `/verify` verdict, `/grill` PHASE 7, `/breakdown` approval gate.

## Core design question (the fork)

Where does compliance evidence live, and what shape?

- **Option A — an append-only evidence log** (`.devforge/audit-log.jsonl` or similar), one structured record per gate-run/verdict, written by each command at its verdict/gate point. Cheap, in-repo, but "in-repo + mutable" weakens the tamper-evidence claim.
- **Option B — evidence rides git, tamper-evidence via commit signing / notes.** Records committed (not squashed away), optionally signed. Leans on git's content-addressing for integrity.
- **Option C — emit to an external sink** (webhook / SIEM / artifact store). Strongest for enterprise, but adds an external dependency + network surface the framework has avoided.
- **Option D — a structured `evidence export` verb** that assembles a report from whatever exists (artifacts + git history + logs) on demand, rather than a live log. Lowest intrusion; weakest immutability.

## Open questions

- OQ-1: What standard(s) to target? SOC2 CC-series controls? ISO 27001 Annex A? Generic "attributable + timestamped + tamper-evident"? Scope the ambition.
- OQ-2: Timestamp source — helpers can't call `Date.now()` in some contexts. Where does trusted time come from (git commit time? CI clock? orchestrator-injected)?
- OQ-3: Attribution — the framework's verdicts are human-owned but the human is a Claude Code operator. What identity is captured (git user? config? OS user)? Is that audit-grade?
- OQ-4: Does the squash (plan 25/37) need a carve-out so evidence survives finalization? (Plan 49 already made a narrow squash carve-out for VERSIONED state — precedent exists.)
- OQ-5: In-repo (A/B) vs external sink (C) — which does the target enterprise actually accept? This is a customer-discovery question, not a code question.

## Phase skeleton (draft — refine in Phase 0)

- **Phase 0** — Customer-discovery + standard-scoping. What evidence does the target buyer's auditor actually demand? Ratify Option A/B/C/D + OQ-1..5. Maintainer + (ideally) a real enterprise stakeholder sign-off. **Do not build before this.**
- **Phase 1** — Evidence schema: the record shape (event, gate, verdict, feature, actor, time-source, artifact refs). python-engineer→python-reviewer.
- **Phase 2** — Emission: wire each verdict/gate point to write a record. Shared verb, reused across commands (mirror `commit-artifacts` shared-verb pattern).
- **Phase 3** — Survival: squash carve-out / commit strategy so evidence isn't erased at `/finalize`.
- **Phase 4** — Export: a `forge evidence export` verb producing an auditor-consumable report.
- **Phase 5** — Docs + boundary: what the framework attests to vs what it cannot (it can't prove the *code* is correct, only that the *controls ran*). Reconcile docs.
- **Phase 6** — Consumer e2e (user-driven): run a feature end-to-end, export the trail, sanity-check against a mock audit checklist.

## Decisions to ratify (Phase 0)

- D1: Evidence home + shape (A/B/C/D).
- D2: Target standard / ambition scope.
- D3: Time + identity source (the credibility crux).
- D4: Squash carve-out yes/no.

## Dependencies + related

- Related: plan 57 (CI) — CI check history is itself part of the evidence; the two stories reinforce.
- Related: plan 25 / 37 / 49 — squash + artifact-commit behavior determines what evidence survives.
- Precedent: plan 49 D3 (narrow squash carve-out for VERSIONED runtime state).

## Context for next session

The trap here is building an elegant evidence log nobody's auditor accepts. **Phase 0 is customer-discovery, not engineering.** The single most credibility-determining decision is D3 (trusted time + attributable identity) — an evidence trail an operator can freely backdate/forge is worthless. Solve that or the whole plan is theater. If a real enterprise stakeholder isn't reachable, scope down to "attributable + timestamped + append-only" and be honest it's evidence-*grade-ish*, not certified.

## When resuming work

1. Read this file in full + skim plan 25 (finalize squash) + plan 37 (per-step commits) + plan 49 (state disposition).
2. Answer OQ-1/OQ-5 from the actual target buyer if possible — do not invent a standard.
3. Nail D3 (time+identity) before any schema work — it's the load-bearing decision.

## Verify

- Phase 0 done = target standard scoped + Option ratified + D3 credibly answered, sign-off recorded.
- Build done = a full feature run emits a structured, timestamped, attributed evidence trail that survives `/finalize` and exports to an auditor-readable report.
