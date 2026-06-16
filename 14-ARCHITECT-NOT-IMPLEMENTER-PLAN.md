# 14-ARCHITECT-NOT-IMPLEMENTER-PLAN

**Status**: IN PROGRESS — Steps 1–4 SHIPPED (working tree, not committed) 2026-06-07; Step 5 (user-driven e2e) + two deferrals pending. Drafted 2026-06-06.
**Branch**: `develop-2.0-init`
**Driver**: The `/breakdown` Agent Assignment table assigns the `architect` agent as a task's *implementer* (the `Agent:` field `/implement` dispatches to write code), which directly contradicts the architect's charter ("Never write implementation code… refuse and route to a specialist", `src/agents/architect.md` Rule 1, line 145). The architect is a **director** — invoked by `/plan` and `/breakdown` to SUPPLY DECISIONS, never to code (Rule 2, line 146). The table is the defect; the charter is the authority it must conform to. This plan documents the fix; it edits the table to honor the charter, not the other way round.

## The defect (verified against source 2026-06-06)

The architect charter (CORRECT — do **NOT** change):
- `src/agents/architect.md` line 145 (Rule 1): "Never write implementation code. If the task requires editing source, you have failed your role — refuse and route to a specialist."
- `src/agents/architect.md` line 146 (Rule 2): "You are invoked by /plan and /breakdown to supply decisions — you do not run any command."
- `src/agents/architect.md` line 26: "Write implementation code — ever. Not repositories, not use cases, not services, not types, not components, not tests, not migrations." (verbatim list — note: explicitly bans writing **types**, which is exactly what the table's rows 238/252 route to the architect).
- `src/agents/architect.md` line 31: "If asked to implement: refuse and route." (paraphrase of the charter's response shape; the literal line reads *"If asked to implement**: refuse and route."*).

The offending table (`src/commands/breakdown/main.md`, `### Agent Assignment table`, lines 232–257 — line numbers confirmed 2026-06-06):
- Row 238: "Domain models, interfaces, contracts, type definitions, architectural decisions → architect"
- Row 239: "State management with orchestration logic (BLoC, Redux reducers with business rules, Pinia stores with computed logic) → architect"
- Row 252: "Shared utilities, type definitions, cross-cutting concerns → architect"
- Row 253: "Unclear or mixed → architect (safe default)"
- Line 255: "If the assigned agent does not exist in `.claude/agents/`… fall back to `architect`."

The table contradicts the **same file's own line 205**: "Agent assignment is orchestrator-direct… The architect only VALIDATES the agent assigned to design-decision tasks… it does not re-derive the whole assignment." Line 205 already restricts the architect's `/breakdown` role to *validation* — yet rows 238/239/252/253 + the line-255 fallback make it the *assignee*. The legitimate architect role at `/breakdown` is validation, never being the coding agent.

## Settled design decisions (confirmed with user 2026-06-06 — do NOT re-open)

### Decision 1 — NO generalist implementer agent

The framework will NOT add a catch-all "implementer" agent. A generalist is useless for most real cases and can never cover 100% of development. The framework ships layer-specific implementers (backend-engineer, frontend-engineer, mobile-engineer, db-engineer, api-designer, devops-engineer, migration-engineer, …) and every coding task routes to the implementer that owns the touched file's layer/package.

### Decision 2 — Architect SHAPES; the layer implementer CODES

The architect decides the solution *shape* at `/plan` (recorded in the plan's Key Design Decisions — type signatures stated as decisions, approach, patterns). The layer's implementer writes the *code* at `/implement`. Plans carry shape, NOT real implementation code. Therefore "architectural decisions" is **not an `/implement` task at all** — it happens at `/plan` and must not appear in the breakdown coder table.

### Decision 3 — The architect charter is the authority; it does NOT change

`src/agents/architect.md` is correct as written. This plan changes ONLY the breakdown table to conform to the charter. A future session must NOT "fix" the charter to permit implementation — that would be fixing the wrong file.

## Empirical grounding (motivation, not a dependency)

Discovered while verifying `/implement` on the testForge20 project, feature `001-on-the-configuration-page`:
- Task 001 (widen `getConfigurationItems` outcome — defines a type + edits the BLoC) was assigned `Agent: architect` — the bug. The architect then wrote and committed the code, violating its charter.
- Task 002 (branch `ConfigurationMenu.vue` on the outcome) was correctly assigned `frontend-engineer`.
- Both tasks are presentation/UI work in an all-UI project: Task 001 hit table rows 238/239, Task 002 hit the UI row (241). The feature's `plan.md` contained ZERO code (shape only: a discriminated-union *type signature* stated as decision D1) — confirming the plan and the architect's shaping role are innocent. The defect is isolated to the breakdown table's coder assignment.

---

## Step 1 — Fix the breakdown Agent Assignment table

**Owner**: instruction-author → instruction-reviewer.

**File**: `src/commands/breakdown/main.md` (`### Agent Assignment table`, rows 238/239/252).

**Guiding principle**: layers aren't agents; stacks are agents. A stack's engineer owns ALL of that stack's layers (domain/types/state AND UI). The architect is not a layer — it shapes at `/plan`, then disappears from the coder table.

- Route type/interface/model/contract/BLoC/cross-cutting work to **the implementer that owns the touched file's layer/package**, not `architect`. Fold these into the existing layer rows — e.g. a UI type or a Pinia/BLoC store → `frontend-engineer`; a server-side type or contract → `backend-engineer`; shared/cross-cutting utilities → the layer that owns the file (split if it spans layers — see Step 2).
- **Drop "architectural decisions"** from the coder table entirely — it is a `/plan` activity (Decision 2), not an `/implement` task.
- **Delete row 243** ("Both core + UI (tightly coupled change) → architect first, then frontend-engineer") outright. Three reasons: (1) "core" is a **testForge20 leak** — it is that project's `pkg-cse-core` package name and is defined NOWHERE else in the generic table (there is no "core" row); a table shipped to all projects must not reference a project-specific layer. (2) The cross-layer/cross-stack *shape* is already decided at `/plan` (Decision 2), so "architect first" at breakdown time is redundant. (3) In a single-stack project (React/Vue/Flutter) the domain/types/state layer and the UI layer are BOTH that stack's engineer's job — "core + UI" is one implementer working across its own layers, not a two-agent handoff. Route any core+UI work to the owning stack's implementer (a frontend stack's domain/types/state/UI all → `frontend-engineer`). A genuine multi-stack coupled change (e.g. BE API + FE consumer) is handled by Step 2's split-or-escalate rule + dependency ordering — split into per-layer tasks joined by a dependency edge — never by "architect first."
- After Steps 1–2 the architect appears NOWHERE in the Agent Assignment table as a coder or co-coder — only in its line-205 validation role. Row 243 is the same leak-class as rows 238/239/252 (all carve a "logic-y" layer — types/domain/BLoC/core/shared — to the architect when it belongs to the owning stack's implementer); deleting 243 + rerouting 238/239/252 together remove the architect from the coder table entirely.

**Status (2026-06-07)**: DONE. The Agent Assignment table was fixed in BOTH `src/commands/breakdown/main.md` AND the inline source `src/_pending/commands/_agent-assignment.md`: deleted the four architect-as-coder rows (domain/types/contracts; state/BLoC; "core + UI"; shared/cross-cutting); broadened the backend/frontend/mobile rows so each owns its full stack (domain/types/interfaces/contracts/state + UI); added the "assign by owning package/stack — layers aren't agents, stacks are" framing line. Also fixed a dangling intra-file ref at `breakdown/main.md` IMPORTANT RULE 3 (it had cited the now-deleted "architect first, then frontend-engineer" sequencing).

### Verify
```bash
# No Agent Assignment table row names `architect` as a coder or co-coder (row 243 is deleted).
grep -nE "\| architect" src/commands/breakdown/main.md
# Expect: no matches over the Agent Assignment table rows.
# Architect now appears ONLY in its line-205 validation prose — nowhere else.
grep -n "only VALIDATES" src/commands/breakdown/main.md
# Expect: the line-205 validation-role line, and no coder/co-coder table row.
```

---

## Step 2 — Fix the unclear/mixed row + the missing-agent fallback

**Owner**: instruction-author → instruction-reviewer.

**File**: `src/commands/breakdown/main.md` (row 253 + line 255).

- Replace row 253 ("Unclear or mixed → architect (safe default)") with the **split-or-escalate** rule: split the task until each piece maps to one layer's implementer; if genuinely impossible, escalate to the human. Never assign `architect` to write code. A mixed/unclear task is a decomposition smell — exactly what the architect's mandatory Phase 2 `/breakdown` validation (atomicity / ordering / contract-chain, lines 199–205) should catch before any task file is written.
- Replace the line-255 fallback ("If the assigned agent does not exist… fall back to `architect`") with the same split-or-escalate rule (the fallback must never name `architect` as a coder). Preserve the existing surrounding guidance about `performance-analyst`/`security-reviewer` running during `/review`.

**Status (2026-06-07)**: DONE. The "Unclear or mixed" row + the missing-agent fallback were replaced with split-or-escalate (never architect) in BOTH `src/commands/breakdown/main.md` and the inline source `src/_pending/commands/_agent-assignment.md`.

### Verify
```bash
# "architect" no longer appears as a default / fallback / safe-default coding assignee.
grep -niE "fall back to .?architect|architect \(safe default\)|safe default" src/commands/breakdown/main.md
# Expect: no matches.
```

---

## Step 3 — Cross-reference pass

**Owner**: orchestrator (grep) → instruction-author for any doc edits surfaced.

Confirm the fix leaves no dangling reference or contradicting text:

- `src/agents/architect.md` line 205 reference + the breakdown validation-role wording (line 205 of `breakdown/main.md`) stay consistent with Steps 1–2 — the architect's `/breakdown` role is validation only.
- **Handoff schema check (already verified 2026-06-06)**: `src/devforge/lib/_breakdown/handoff_schema.py` `TaskRow.agent` is validated **non-empty only** (line 121) — there is **NO agent-name enum** to update. The schema does not (and need not) forbid `architect`; the constraint lives in the LLM-facing table (Steps 1–2) and the optional `/implement` guard (Step 4). Record this so a future session does not hunt for a schema enum that doesn't exist.
- Docs that describe the assignment table: `src/CLAUDE.md` (`/breakdown` catalog entry, the `## Available Agents` line "Agent selection is automatic in `/implement` based on the task's assigned agent"), `09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md` (OQ-3 / Decision 3 / the alignment table referencing `_agent-assignment`), and the inline source `src/_pending/commands/_agent-assignment.md` (the table's origin — check whether it carries the same architect-as-coder rows and needs the same fix to avoid re-introducing the defect on a future re-inline).

**Status (2026-06-07)**: DONE. Cross-ref pass completed:
- Fixed `/implement` (`src/commands/implement/main.md` + `src/commands/implement/references/agent-brief.md`): fallback changed from "fall back to architect" to escalate/never-architect; the "safe default for any layer" claim deleted; the architect-charter citation corrected from the forge-source path `src/agents/architect.md` to the runtime path `.claude/agents/architect.md` (the command runs in the target project).
- Fixed `src/CLAUDE.md:114` (dropped `architect` from the `/refactor` auto-selected-agent list).
- Fixed `src/_pending/commands/refactor.md` fallback (escalate/never-architect, standalone-appropriate — no "re-run /breakdown").
- Added to `_agent-assignment.md` the perf/security scoping sentence + `VALIDATES` caps for consistency with `breakdown/main.md`.
- **Handoff schema needs NO change** — `_breakdown/handoff_schema.py` `TaskRow.agent` has no enum (validated non-empty only), as anticipated.
- Verified: no positive architect-as-coder / fallback claim remains anywhere in `src/` EXCEPT the deferred `fix.md:167` (see Deferrals). (`_audit/_preflight.py:275` lists architect as an audit *reviewer* — legitimate, not a coder.)

### Verify
```bash
# Every "architect implements / architect as assignee" claim is gone across docs + the inline source.
grep -rniE "architect.*(implement|write|code|assign)" \
  src/commands/breakdown/main.md \
  src/_pending/commands/_agent-assignment.md \
  src/CLAUDE.md \
  09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md
# Review each hit: none may claim the architect writes code / is a coding assignee
# (validation-role and "shapes-not-codes" wording is fine).
```

---

## Step 4 — (DEPENDENT, defense-in-depth) `/implement` guard

**Owner**: instruction-author → instruction-reviewer (spec) and/or python-engineer → python-reviewer (if the guard is a helper check).

**DEPENDENCY**: `/implement` (a.k.a. `/execute-task`) is **still being built** — see `07-EXECUTE-TASK-REDESIGN-PLAN.md` and `13-IMPLEMENT-WRAPPER-MODE-PLAN.md`. The source may live under `src/_pending/commands/execute-task.md` or `src/commands/implement/main.md` depending on promotion state at execution time. **Do NOT assert a concrete guard file path until you have read the actual `/implement` spec and confirmed it exists.** This step is best folded into / coordinated with plan 07 rather than executed against an assumed-live `/implement` spec.

- Add a guard so `/implement` refuses/halts if a task's `Agent:` is `architect` (belt-and-suspenders behind the table fix — catches any stale breakdown produced before Steps 1–2, or a hand-authored task file). The refusal should mirror the architect's own response shape (`src/agents/architect.md` line 31): the architect does not implement; re-route to the owning layer's implementer or re-run `/breakdown`.

**Status (2026-06-07)**: DONE, and **PLAN PREMISE CORRECTED**. This step was originally framed as DEPENDENT because "`/implement` is still being built." That premise was WRONG: `/implement` is already live and promoted at `src/commands/implement/main.md`. The architect guard ("if the resolved task's `agent` is `architect`, HALT — re-run `/breakdown` or add the owning-stack implementer; never dispatch architect to implement") was added to `implement/main.md:134` + `references/agent-brief.md:23`. NOTE the concurrent `/implement`→`/execute-task` rename (plans 07/13): the guard lives in the currently-live `/implement` spec; if 07 rebuilds `/execute-task`, carry the guard + the never-architect fallback forward. (The `**DEPENDENCY**` line above is retained as the original framing record; it is superseded by this status note.)

### Verify
```bash
# Only meaningful once /implement exists. Confirm the guard is present in the live spec/helper.
ls src/commands/implement/main.md src/_pending/commands/execute-task.md 2>/dev/null
# Then grep the file that exists for the architect-as-agent refusal guard.
```

---

## Step 5 — Verify end-to-end (user-driven)

**Owner**: user-driven manual e2e (matches the testForge20 e2e gates in 09/13).

Re-run `/breakdown` on a representative feature and confirm the fix holds:

- Use the testForge20 `001-on-the-configuration-page` feature (the empirical case) or a synthetic feature with a type-definition + BLoC/store task.
- Confirm the Task-001-equivalent (type + store change in an all-UI feature) now routes to the **layer implementer** (`frontend-engineer`), NOT `architect`.
- Confirm **NO** task in the generated breakdown is assigned `architect` as its coding agent, and the architect appears only in the Phase 2 Specialist Consultation provenance (validation role).

### Stop criteria
- The breakdown emits zero `Agent: architect` coding assignments.
- A type/BLoC/cross-cutting task routes to its layer implementer.
- The architect appears only as the Phase 2 decomposition validator in the tasks index Specialist Consultation table.

**Status (2026-06-07)**: NOT DONE — user-driven. Unchanged: re-run `/breakdown` on a representative feature, confirm zero `Agent: architect` coding assignments.

---

## Out of scope
- Changing the architect charter (`src/agents/architect.md`) — it is the authority; Decision 3.
- Adding a generalist implementer agent — Decision 1.
- Re-architecting the agent roster or the Phase 2 mandatory-architect-consultation mechanism (09 Decision 3) — untouched.
- Building the `/implement` guard against a non-existent spec — original framing gated Step 4 on 07/13 producing a live `/implement`. **SUPERSEDED 2026-06-07**: `/implement` was already live (`src/commands/implement/main.md`); the guard SHIPPED there (see Step 4 status).

## Deferrals / follow-ups

- **`/fix` cleanup (deferred) — RESOLVED 2026-06-15 → dropped, executed by plan 21.** The drop-vs-fix decision settled DROP; `21-DROP-FIX-REFACTOR-PLAN.md` removed both `/fix` and `/refactor` and ran this deferral's removal checklist (deleted `fix.md` + the `src/CLAUDE.md` catalog entry + the `_agent-assignment.md` line-3 mention + the manifest entries + `/implement`'s escalate-to refs). The original deferral text is preserved below for history. — *Original (now superseded):* `src/_pending/commands/fix.md:167` still carries the positive "fall back to `architect`" fallback. Left intentionally — the user is weighing **dropping `/fix` entirely** (its main value, a root-cause-before-edit gate, may not justify the command; it's unbuilt / `_pending`). The drop-vs-fix decision + cleanup is a separate future pass. If `/fix` is dropped: delete `fix.md` + its `src/CLAUDE.md` catalog entry + `/fix` mentions in `_agent-assignment.md` line 3 / the manifest / `/implement`'s escalate-to refs. If kept: apply the same never-architect fallback fix.
- **Inline-source duplication (deferred, pre-existing)**: the Agent Assignment table (and its perf/security sentence) is duplicated between `breakdown/main.md` (inlined copy) and `_agent-assignment.md` (shared source per 09 OQ-3). They are kept in sync manually; a future "inline-source reconciliation" should decide a single source of truth. Out of scope for this plan.

## Context for next session
- Steps 1–4 are SHIPPED in the working tree (uncommitted, 2026-06-07): the breakdown table fix + split-or-escalate fallback in BOTH `src/commands/breakdown/main.md` and the inline source `src/_pending/commands/_agent-assignment.md`; the cross-ref pass (`/implement`, `src/CLAUDE.md:114`, `refactor.md`); and the live-`/implement` architect guard (`implement/main.md:134` + `references/agent-brief.md:23`). Nothing committed.
- Only **Step 5** (user-driven testForge20 e2e) + the **inline-source single-source-of-truth reconciliation** deferral remain. (The `/fix` drop-vs-fix deferral is **RESOLVED 2026-06-15 → dropped, executed by plan 21** — `fix.md` is deleted; see Deferrals.)
- Step 4's original "still being built" premise was WRONG and is corrected: `/implement` is already live at `src/commands/implement/main.md`; the guard lives there. If 07 rebuilds `/execute-task`, carry the guard + never-architect fallback forward.
- The architect charter is CORRECT and was NOT changed. The breakdown table conforms to it — not the reverse. Do not edit `src/agents/architect.md`.
- `_breakdown/handoff_schema.py` needs NO change: `TaskRow.agent` has no enum (validated non-empty only) — the no-architect-as-coder rule is an LLM-facing table constraint, backstopped by the shipped `/implement` guard.
- The inline source for the table is `src/_pending/commands/_agent-assignment.md` (09 OQ-3 inlined it into `breakdown/main.md`); it was fixed in lockstep. The two copies are kept in sync manually — see the inline-source-duplication deferral.

## When resuming work
Steps 1–4 are SHIPPED (working tree, uncommitted, 2026-06-07). Only Step 5 + the two Deferrals remain.
1. Confirm the three settled decisions still hold (no generalist; architect-shapes/implementer-codes; charter unchanged) — do NOT re-litigate them. The charter was NOT touched (correct as written).
2. Run **Step 5** (user-driven testForge20 e2e): re-run `/breakdown` on a representative feature (the `001-on-the-configuration-page` empirical case or a synthetic type+BLoC/store feature); confirm zero `Agent: architect` coding assignments and that the type/store task routes to `frontend-engineer`. Not DONE until that holds.
3. ~~Decide the **`/fix` deferral**~~ — **RESOLVED 2026-06-15 → dropped, executed by plan 21** (`21-DROP-FIX-REFACTOR-PLAN.md` removed `/fix` + `/refactor` and ran this deferral's removal checklist; `fix.md` is deleted). See Deferrals. No action remains.
4. Optionally tackle the **inline-source-duplication deferral** (single source of truth for the Agent Assignment table across `breakdown/main.md` + `_agent-assignment.md`) — pre-existing, out of this plan's scope.
5. Commit the working-tree changes (Steps 1–4) when ready — match repo commit style (terse, scope prefix).

## Related plans
- `09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md` — built `/breakdown` + the Agent Assignment table this plan fixes (09 Decision 3 set the mandatory-architect-validation role; this plan corrects the table that contradicted it).
- `07-EXECUTE-TASK-REDESIGN-PLAN.md` / `13-IMPLEMENT-WRAPPER-MODE-PLAN.md` — own `/implement` (a.k.a. `/execute-task`), the consumer of the `Agent:` field. Step 4's guard already SHIPPED in the live `src/commands/implement/main.md`; if 07 rebuilds `/execute-task`, carry the guard + never-architect fallback forward (see Step 4 status).
