# 62 — SMT Requirements-Consistency Gate (spec-check)

**Status:** DRAFT SEED / NOT STARTED / no code. Awaiting **Phase 0 brainstorm + maintainer ratification** before any build phase is authored.
**Branch:** `develop-2.0-init`
**Origin:** Surfaced 2026-07-15 during a Forge-vs-AWS-Kiro capability-gap research session (quality/stability axis). The research found this is the **one capability where Kiro's architecture is genuinely ahead of Forge**, and that it fits Forge's own stated philosophy ("every gate is mechanical not prose") better than it fits Kiro's. The maintainer asked to pursue it in a fresh chat — this file is the handoff.

---

## READ FIRST (fresh session): what this is and what to do

You are picking this up cold. Do **not** start coding. The first action is a **brainstorm** (`superpowers:brainstorming`) to settle the open questions below, then a proper plan via the repo's plan convention, then build behind the standard review loops. This document is the seed, not the plan.

**Do NOT trust any code/path claim in this file without verifying it against the repo** — it was written from the maintainer's CLAUDE.md context, not from a fresh read of the source. Verify before you build (per the framework's own sentence-level-hallucination discipline).

---

## The opportunity (why this is worth building)

Forge already enforces "every gate is mechanical, not prose" — but **only at the code tier**. Its forcing-function detectors (`magic-enum`, `cross-layer-imports`, `any-leak`, `design-token-provenance`) all inspect *code* at implement/commit time. Nothing in Forge mechanically checks whether the **requirements themselves are logically consistent** before code is written. `/specify` produces acceptance criteria; `/grill` attacks the *design* with an LLM adversary — but neither runs a deterministic proof over the requirement logic.

Kiro (AWS) ships exactly this and it is its strongest, most-cited quality mechanism. This plan closes that gap for Forge — as the **first requirement-tier forcing function**.

### What the mechanism actually is (neurosymbolic — verified from the Kiro research)

Two parts, one soft and fallible, one hard and deterministic:

1. **Auto-formalization (soft, LLM):** translate each acceptance criterion from English into formal logic over SMT theories. E.g. "response must be < 100ms" → `resp_ms < 100`; "only admins can delete" → `can_delete ⇒ is_admin`.
2. **Logical analysis (hard, SMT solver):** feed the conjunction of all formalized constraints to the solver, which *deterministically* proves:
   - **Contradiction** — the constraint set is UNSAT (two+ ACs can't all hold). The solver returns the minimal unsatisfiable core (the exact conflicting subset).
   - **Vacuity** — an AC whose precondition can never be satisfied (dead requirement).
   - **Gap / underspecification** — input regions no AC constrains (the solver finds a model in an uncovered zone). *(Hardest of the three; likely a later phase, not v1.)*

**Critical honesty point (Kiro's own docs admit this):** the solver is sound only over *the subset the LLM managed to formalize*. It proves consistency of the formalized logic, **not** the whole natural-language spec, and **not** semantic correctness (whether the requirement is what the user meant). It is neurosymbolic, not end-to-end deterministic. Any framing as "mathematically proves the spec is correct" is an overstatement — do not repeat it.

---

## The tool

**Z3** (`z3-solver` on PyPI, MIT license, Microsoft Research). Same solver family AWS's Automated Reasoning is built on (Zelkova / IAM Access Analyzer sit on Z3-class solvers). Runs local, no service, no network — fits Forge's self-hosted, stdlib-leaning helper substrate. The solver integration is the *small* part (~a few hundred lines: build sorts/vars, assert constraints, `check()`, extract `unsat_core()`).

**Open dependency question (OQ-7 below):** Z3 is a non-stdlib pip dependency shipped into consumer installs. Forge helpers have leaned stdlib-only. Whether to vendor it, require `pip install`, or gate the feature on its presence is an unresolved decision — do not assume.

---

## Where it fits Forge (proposed, NOT settled)

Candidate home: a new **requirements-tier forcing-function** rule, invoked at either `/specify` (right after ACs are authored) or `/grill` (the existing adversarial pre-`/breakdown` stage). This is OQ-1 and must be settled in the brainstorm.

Shape follows the existing forcing-function pattern (helper owns structure, LLM composes values):
- helper parses the spec's acceptance criteria
- helper dispatches an LLM step to formalize each AC into a **typed constraint intermediate representation** (helper owns the IR schema; LLM fills values)
- helper feeds the IR to Z3 (deterministic)
- helper reports the UNSAT core + a plain-English rendering of the proven conflict
- gate behavior (hard-halt vs advisory) = OQ-2

Precedent to mirror for the mechanical-gate + `main.md` halt shape: plans **40 / 42 / 38** (forcing-function verbs that exit non-zero and halt the command on stderr). Precedent for the helper subpackage layout: `src/devforge/lib/_constitute/_forcing_functions/` (per-rule detector dirs) and the `constitute_helper verify-*` verbs.

---

## The hard part (design this carefully or it becomes noise)

**Formalization fidelity, and its collision with Forge's precision discipline.** A wrong LLM translation either invents a contradiction that isn't real (false positive) or misses a real one (false negative). Forge spent real effort (plan **19** — default-dismiss adversarial refutation) making the framework *not* cry wolf. An SMT gate that fires on a mistranslation is exactly the wolf plan 19 was built to kill.

Therefore this gate **cannot be silent/auto** like `magic-enum`. The design must **surface the formalized logic for a human check** — show the person "here is how I read your acceptance criteria as logic, and here is the conflict I proved" — so a false contradiction is caught at the formalization step, not trusted blindly. That human-check loop is the real design work, not the Z3 call. How it works = OQ-3.

Consider whether the formalization step should itself be verified adversarially (a second LLM checks the first's translation) before Z3 runs — this would reuse Forge's existing `_shared/` refutation-engine philosophy at the requirements tier. Possibly over-engineered for v1; flag for the brainstorm.

---

## Honest scope

| Catches well | Cannot touch |
|---|---|
| Numeric / threshold conflicts (`<100ms` ∧ `>200ms`) | Whether the requirement is what the user *meant* (semantic correctness) |
| Permission / role logic (`is_admin` ∧ `¬is_admin`) | Vague prose ACs ("feels responsive", "intuitive") |
| State-machine / ordering constraints | Anything the LLM chose not to / couldn't formalize |
| Transitive inconsistency (A→B, B→C, C→¬A) | Gaps (v1) — coverage-of-input-space is a stretch goal, not v1 |

Strong for specs with numeric, state, or permission logic. Weak for prose-heavy product specs. Set expectations accordingly in any user-facing copy — under-promise.

---

## Open questions to resolve in the Phase-0 brainstorm

- **OQ-1 (home):** `/specify` vs `/grill` vs a standalone opt-in verb. Which stage owns the gate? (`/grill` is already opt-in + adversarial + pre-`/breakdown`; `/specify` is where ACs are born and is mandatory.)
- **OQ-2 (hard vs advisory):** does a proven contradiction HALT the pipeline (like plan 40/42 gates) or surface as an advisory finding the user can override? Kiro's own behavior here is unknown (it was the top unresolved open question in the research — sources establish the mechanism, not whether it enforces).
- **OQ-3 (human-check loop):** how is the formalization surfaced for correction? Inline in the command? A written artifact the user edits? What happens when the user says "your translation is wrong"?
- **OQ-4 (constraint IR):** what does the typed intermediate representation look like? Sorts (Int/Real/Bool/Enum), constraint relations, variable identity across ACs. This is the core schema design.
- **OQ-5 (AC input format):** what does `/specify` actually emit for ACs today (EARS? Gherkin? freeform bullets?) and how parseable is it? **Read the real `/specify` output before designing the parser.**
- **OQ-6 (scope for v1):** contradiction-only for v1, defer vacuity + gaps? (Recommended: yes — contradiction is the highest-value, lowest-false-positive-risk check.)
- **OQ-7 (Z3 dependency):** vendor / require-pip / presence-gate the non-stdlib `z3-solver` dependency into consumer installs. Ties into `install.sh` / `update.sh` surgical-copy sets.
- **OQ-8 (variable identity):** the LLM must map "the user" in AC-1 and "an admin" in AC-3 to consistent solver variables, or the contradiction check is meaningless. How is entity co-reference resolved across ACs? This is a deep formalization-fidelity sub-problem.

---

## First concrete actions for the fresh session

1. Invoke `superpowers:brainstorming` — do not skip to a plan.
2. **Read the real code before deciding anything:**
   - `src/commands/specify/main.md` + `src/devforge/lib/_specify/` — what ACs look like coming out of `/specify`, and the handoff schema.
   - `src/commands/grill/main.md` + `src/devforge/lib/_grill/` — the existing opt-in adversarial stage (candidate home).
   - `src/devforge/lib/_constitute/_forcing_functions/` + `_setters.py` + `_schema.py` (`FORCING_FUNCTION_RULES`) — the forcing-function substrate this would extend, and how a new rule is registered.
   - Plans **40 / 42 / 38** — the mechanical-gate → exit-non-zero → `main.md`-halts-on-stderr shape to mirror.
   - Plan **19** — the precision/false-positive discipline this must not violate.
3. Settle OQ-1..OQ-8 with the maintainer (this framework ratifies decisions at a Phase-0 gate before build phases are authored — see plans 32/33 for the DRAFT-then-ratify precedent).
4. Only then author the numbered plan with per-step `## Verify` criteria and build behind the standard loops: `python-engineer → python-reviewer` for helpers (test-first — every function gets a test run in the same turn), `instruction-author → instruction-reviewer` + `claude-code-guide` for any `main.md`/spec edit that ships into `.claude/`.

---

## Non-goals

- Not trying to verify *semantic* correctness or "is this the right feature" — logic consistency only.
- Not trying to match Kiro feature-for-feature (no PBT/fuzz layer in this plan — that is a separate, code-tier idea if ever pursued).
- Not a full formal-methods system — bounded, opt-in, contradiction-first.

---

## Provenance / supporting material from the origin session

- The comparison this came from (published artifact): `https://claude.ai/code/artifact/0aaaca15-bdc8-4a5a-b9f8-6ca2819708e5` — "AIDevTeamForge vs AWS Kiro — Quality & Stability Dossier."
- Verified sources on Kiro's spec-check mechanism (survived 3-vote adversarial verification in the research):
  - `https://kiro.dev/blog/deep-spec-analysis/` (Kiro's own description of Refinement → Auto-Formalization → Logical Analysis)
  - `https://kiro.dev/docs/specs/analyze-requirements`
  - `https://www.geekwire.com/2026/aws-targets-ai-slop-with-new-spec-check-in-kiro-coding-tool-amid-scrutiny-of-agent-reliability/`
  - `https://theoutpost.ai/news-story/aws-kiro-tackles-ai-agent-reliability-with-math-based-bug-detection-before-code-is-written-26215/`
  - `https://kiro.dev/docs/specs/correctness/` (Kiro's PBT layer — out of scope here, but context)
- AWS internal data point cited across sources: ~60% of first-draft requirements across 35 projects / 1,400+ acceptance criteria needed refinement after their spec-check — evidence that requirement-logic defects are common and worth gating.
- Key caveat carried from the research: **no head-to-head output-quality benchmark between Forge and Kiro exists.** This plan is motivated by an architectural gap, not a measured deficiency.
