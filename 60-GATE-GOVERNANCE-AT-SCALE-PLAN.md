# 60 — Gate Governance at Org Scale

**Status:** SKELETON — NOT STARTED. Phase 0 (investigation + ratify) is the gate. No code (likely).
**Type:** MOSTLY DECISION / PROCESS / DOC plan — least code-shaped of the five. May end as a governance doc + a few maintainer tools.
**Branch:** `develop-2.0-init`.
**Created:** 2026-07-10, seeded from an enterprise-readiness gap analysis (this session).

---

## Problem

The framework's entire authoring + maintenance process assumes **one sophisticated maintainer** (the repo owner) who:

- Runs python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops by hand.
- Ratifies the constitution + forcing-function config per project.
- Decides which gates exist, builds the detectors, maintains the drift-checkers.

At enterprise scale that single-maintainer model breaks:

- Who owns the constitution for 50 devs across 8 teams? Who ratifies changes to it?
- Who maintains the mechanical detectors + their drift-checkers (the meta-maintenance the framework already accumulates — `constitution-drift-check.sh`, `verify-forcing-function-keys`, `verify-universal-defaults`)?
- How does a new team onboard the framework without the founder's tacit knowledge?
- How are gate changes reviewed/approved so one team can't silently weaken a gate everyone relies on?

Gap = the framework has a **maintenance + governance model of exactly one person**, and enterprise needs a **platform-team + governance model**.

## Why it matters (enterprise)

- A control everyone depends on but no one owns rots. Enterprise governance exists precisely to assign that ownership.
- "Who can change a gate, and who approves it" is an audit question (ties to plan 58).
- Onboarding cost per team determines whether the framework spreads or dies in one repo.

## Believed current state — VERIFY in Phase 0

- [ ] Confirm the constitution ownership model: `/constitute` produces per-project `constitution.md` + `constitute.json`; who's assumed to run/ratify it? (Currently: the installing dev.)
- [ ] Confirm the forcing-function config surface: `constitute_helper set-forcing-functions` / `list-forcing-functions`, `_schema.py::FORCING_FUNCTION_RULES` — who decides which rules are on?
- [ ] Confirm the drift-maintenance already-shipped: `update.sh` + `install.sh` source `constitution-drift-check.sh` (`verify-universal-defaults` + `verify-forcing-function-keys`), WARN-only.
- [ ] Confirm plan 41's maintainer-side reachability gate (`scripts/verify-agent-reachability.py`) is the pattern for "maintainer tools" vs "consumer tools."
- [ ] Confirm there is NO existing multi-maintainer / RBAC / approval concept anywhere.

## Core question (mostly not-code)

Enterprise governance is a **people-and-process** problem the framework can *support* but not *solve*. The real question: **what does the framework need to PROVIDE so an org's platform team can govern it?**

Candidate needs (to prioritize in Phase 0):

- **A constitution ownership/change-review model** — how the org edits + approves the shared constitution (a doc/convention, maybe a `CODEOWNERS`-style pattern over `constitution.md`).
- **A gate catalog + lifecycle doc** — every mechanical gate, what it checks, who owns it, how to add/retire one. So knowledge isn't tacit-in-the-founder's-head.
- **An onboarding runbook** — how a new team adopts the framework without the founder present.
- **Maintainer-tool consolidation** — the drift-checkers + reachability gate + review loops packaged so a platform team can run them, not just the founder.
- **Separation of "framework maintainer" vs "consumer team"** roles — the framework already half-has this (maintainer-side `scripts/` gates vs consumer-side `.devforge/` helpers). Make it explicit.

## Open questions

- OQ-1: Is this ONE plan or does it fork? (Constitution governance / gate-catalog / onboarding runbook are somewhat independent.)
- OQ-2: Does the framework provide RBAC-ish mechanism, or just conventions + docs? (Strong lean: docs + `CODEOWNERS`-style conventions, NOT a bespoke permission system — that's the host's job, e.g. GitHub branch protection.)
- OQ-3: What's the minimum onboarding artifact — a runbook doc? a `forge doctor` command that checks an install is governed correctly?
- OQ-4: How does gate-change review work — normal PR review over `src/` + the reachability/drift gates as required checks (ties to plan 57 CI)?
- OQ-5: Is a "gate catalog" auto-generated from `FORCING_FUNCTION_RULES` + the reachability data, or hand-maintained? (Auto-gen resists drift.)

## Phase skeleton (draft — refine in Phase 0)

- **Phase 0** — Scope decision: which of the candidate needs are in, is it one plan or a fork, code-vs-doc split. Maintainer sign-off. **This plan may legitimately conclude "mostly a governance doc + one auto-generated gate catalog."**
- **Phase 1 (likely doc)** — Constitution governance model: ownership, change-review, `CODEOWNERS`-style convention.
- **Phase 2 (maybe code)** — Auto-generated gate catalog from `FORCING_FUNCTION_RULES` + reachability data (resists drift, single source of truth).
- **Phase 3 (doc)** — Onboarding runbook: new-team adoption without the founder.
- **Phase 4 (maybe code)** — `forge doctor`-style install-health check (is this consumer's forge install governed/current). Overlaps plan 57/44 drift-checks — dedup.
- **Phase 5 (doc)** — Maintainer-vs-consumer role separation made explicit in docs.

## Decisions to ratify (Phase 0)

- D1: One plan vs fork.
- D2: Conventions+docs vs bespoke mechanism (strong lean: former).
- D3: Auto-generated vs hand-maintained gate catalog.
- D4: Minimum onboarding artifact.

## Dependencies + related

- Related: plan 57 (CI) — gate-change review as required checks is the enforcement arm of governance.
- Related: plan 58 (audit trail) — "who changed which gate when" is governance evidence.
- Related: plan 44 (constitution drift wiring), plan 41 (reachability gate) — existing maintainer-side tooling this plan organizes.

## Context for next session

**This is the least code-shaped of the five — don't force it into a build.** The honest likely outcome is a governance doc + an auto-generated gate catalog + an onboarding runbook, with a small `forge doctor`-style health check if warranted. The trap is inventing an RBAC/permission mechanism the framework shouldn't own (the host's branch protection + PR review already does that — see D2). The framework's job is to make its gates *catalogable, ownable, and onboardable*, not to reimplement GitHub's access control. Keep scope tight; this can sprawl endlessly.

## When resuming work

1. Read this file in full.
2. First task: decide D1 (one plan vs fork) + D2 (conventions vs mechanism) — these set whether there's any build at all.
3. Resist scope creep into permissions/RBAC. Lean docs + auto-generated catalog.

## Verify

- Phase 0 done = scope + code/doc split ratified; D1/D2 decided; maintainer sign-off.
- Plan done = a platform team could adopt, govern, and extend the framework's gates from the shipped docs/catalog WITHOUT the founder's tacit knowledge.
