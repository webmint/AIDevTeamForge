# Enterprise-Readiness Roadmap (Plans 57–61)

**Purpose:** work-order index for the 5 enterprise-gap plans. Plan numbers are creation-order IDs (repo norm); **this file owns the execution order.** When resuming, follow the sequence here, not the numeric order.

**Created:** 2026-07-10. Branch: `develop-2.0-init`.

---

## The gap (one line)

The framework's mechanical-gate + adversarial-verify split is the right foundation for enterprise-quality software, but enforcement lives in the dev's **local** pipeline, evidence is **human-readable markdown** not compliance-grade, gate severity is **inconsistent + bypassable**, LLM verdicts are **not characterized for reproducibility**, and the whole thing assumes a **single maintainer**. These 5 plans close that.

---

## Work order (follow this, not the numbers)

```
  ┌─────────────────────────────────────────────────────────┐
  │ 1. Plan 59  LLM-VERDICT-REPRODUCIBILITY   (mostly doc)   │  ← start: fast, framing
  └─────────────────────────────────────────────────────────┘
                         │ sets honest vocabulary
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ 2. Plan 61  FALSE-HALT-HARDENING + AUDITED-BYPASS (build)│  ← precision + escape
  └─────────────────────────────────────────────────────────┘
                         │ HARD PREREQUISITE
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ 3. Plan 57  CI-SERVER-SIDE-ENFORCEMENT    (build)        │  ← relocate gates → CI
  └─────────────────────────────────────────────────────────┘
                         │ produces check history
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ 4. Plan 58  COMPLIANCE-AUDIT-TRAIL        (build+discovery)│ ← evidence export
  └─────────────────────────────────────────────────────────┘
                         │ everything above needs owning
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ 5. Plan 60  GATE-GOVERNANCE-AT-SCALE      (mostly doc)   │  ← who owns/changes gates
  └─────────────────────────────────────────────────────────┘
```

---

## Sequence + why each is placed here

| Order | Plan | File | Type | Why this position |
|-------|------|------|------|-------------------|
| **1** | 59 | `59-LLM-VERDICT-REPRODUCIBILITY-PLAN.md` | Mostly doc | Smallest. Likely confirms `compute-verdict` is already a pure function → the reproducibility story mostly already exists. Fast win; sets the honest "bound, don't fake determinism" vocabulary the later plans lean on. |
| **2** | 61 | `61-FALSE-HALT-HARDENING-AND-AUDITED-BYPASS-PLAN.md` | Build | Precision + escape-with-audit. Builds on real incidents already root-caused (plans 34, 38). **Hard prerequisite for 57** — never make a gate merge-blocking before its false-positive rate is bounded and a loud, attributed override exists. |
| **3** | 57 | `57-CI-SERVER-SIDE-ENFORCEMENT-PLAN.md` | Build | The core relocation: gates local → server-side merge-blocking CI. Safe ONLY after 61. The single biggest enterprise gap. |
| **4** | 58 | `58-COMPLIANCE-AUDIT-TRAIL-PLAN.md` | Build + customer-discovery | Consumes 57's CI check history + 61's override records as evidence. Phase 0 is customer-discovery, not engineering — scope to what a real auditor accepts. |
| **5** | 60 | `60-GATE-GOVERNANCE-AT-SCALE-PLAN.md` | Mostly doc/process | Organizes ownership of everything the other four produce. Least code; resist inventing RBAC (host branch-protection owns that). Last because it governs the finished set. |

---

## Dependency edges (explicit)

- **61 → 57** — hard prerequisite. Merge-blocking without hardened precision + audited escape = blocked release trains.
- **57 → 58** — CI check history is part of the compliance evidence.
- **61 → 58** — override records ARE evidence.
- **60 ties to 57/58/61** — the HARD/ADVISORY/OVERRIDABLE gate taxonomy is a governance decision; "who changed which gate when" is governance evidence.
- **59 independent** — no hard dep; do first because it's cheap and sets honest framing.

---

## Independence note (can parallelize)

- **59** can run anytime — no dep. Front-loaded only for the fast win + vocabulary.
- **60** can start its doc/scoping (Phase 0) in parallel with 57/58 build, since it's mostly process. Just finish it last (it governs the finished set).
- **61 and 57 are strictly ordered** — do not invert.
- **58**'s Phase 0 (customer-discovery) can start anytime — it's people-research, not code — but its build waits on 57.

---

## How to use this file

Each plan is worked in a **separate cleared session**. When you start one:

1. Open THIS file → confirm the plan's position + its inbound dependencies are satisfied.
2. Open the plan file → run its `## When resuming work` block.
3. On completion, update the plan's status header AND the row here (mark done).

Do NOT reorder by plan number. The number is a stable ID; this table is the truth.
