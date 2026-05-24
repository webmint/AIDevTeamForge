# Structural Integration Check (DIR) — Implementation Plan

**Status:** IMPLEMENTED 2026-05-24 on `develop-2.0-init` — all 3 spec edits landed in `src/agents/code-reviewer.md` (§7 Structural Integration at end of checklist; Output Format `Structural Integration` subsection; Rule 1 new-file overlap-search clause). §7 placed at end of checklist (monotonic 1→7), not after §2 as originally drafted — resolved a numbering conflict. **Smoke tests (DoD) PENDING — manual:** (1) changeset with duplicate module → expect `DUPLICATE`; (2) new handler beside same-shape handlers → expect `INTEGRATED` (no false positive).

## Background

**Source:** SLUMP / ProjectGuard paper. Structural integration degrades on both Claude Code and Codex even when semantic faithfulness holds. On Codex, DIR (Dependency Integration Ratio) improves on 15 of 19 papers after ProjectGuard, with 76% mean relative improvement. This is a separate problem from semantic drift, not a side-effect.

## Gap in current pipeline

Nobody in the current AIDevTeamForge pipeline explicitly checks whether new code integrates with previously written code:

- **Architect** — does not catch it; bottom-up repo knowledge is absent at plan stage.
- **code-reviewer** — checks "does it work + does it match the spec".
- **qa-engineer** — checks behavior.

"Did the agent rewrite something that already existed?" is an orphan check.

## Proposal

Cheapest viable version: extend the existing `code-reviewer` agent with one extra pass. No new agent, no new command, no module map.

For each **newly created** file/module in the changeset:
1. Search the repo for existing modules with similar responsibility or interface shape (Glob for likely names; Grep for similar signatures; check sibling directories).
2. Classify the new code as `INTEGRATED | INTENTIONAL_PARALLEL | DUPLICATE`.
3. `DUPLICATE` → Critical. `INTENTIONAL_PARALLEL` without spec justification → Warning.

One targeted search pass per new file, not a full repo audit. Files that only edit existing modules are skipped.

## Concrete edits

### 1. `src/agents/code-reviewer.md` — add Section 7 after Architecture & Patterns

Insert after line 34 (end of Section 2):

```markdown
### 7. Structural Integration

For each **newly created** file/module in this changeset:
1. Search the repo for existing modules with similar responsibility or interface shape
   (Glob by likely names; Grep for similar function/class signatures; check sibling directories).
2. If a similar module exists, classify the new code as one of:
   - **Intentional parallel** — explicit design reason (e.g., versioned API, A/B variant). Must be justified in spec/plan.
   - **Duplicate / parallel rewrite** — same responsibility implemented again, ignoring existing code.
3. Output: list each new file with verdict `INTEGRATED | INTENTIONAL_PARALLEL | DUPLICATE`.
   `DUPLICATE` is **Critical** — it means the agent rewrote what existed.
   `INTENTIONAL_PARALLEL` without spec justification is **Warning**.

Limit: one targeted search pass, not a full repo audit. Skip files that only edit existing modules.
```

### 2. `src/agents/code-reviewer.md` — extend Output Format

In the Output Format block (lines 54–74), add a subsection before `### Verdict`:

```markdown
### Structural Integration
- [new-file]: INTEGRATED | INTENTIONAL_PARALLEL (reason: ...) | DUPLICATE (existing: [path])
```

### 3. `src/agents/code-reviewer.md` — extend Rule 1

Line 78, after "Read ALL changed files before giving any feedback", append:

> For newly created files, also search for pre-existing modules with overlapping responsibility — a single targeted pass.

## What is intentionally NOT in scope

- **No new `integration-checker` agent.** Would split context and re-read the same changed files. Code-reviewer already reads them.
- **No new phase in `/review`.** The orchestrator currently does not invoke `code-reviewer` at all (Phases 2–4 run security / performance / qa). Whether to wire `code-reviewer` into `/review` is a separate decision; this plan does not depend on it.
- **No `repo-map.md` or module-map artifact.** The paper's compatibility-aware brief uses one, but for a single per-turn check, Glob+Grep is cheaper and avoids a maintenance artifact that decays.
- **No five-level rubric (0–4).** Verdict stays in the existing `Critical / Warning / Info` shape.

## Cost and risks

**Cost:** one extra Glob+Grep cycle per new file. For a typical 1–3 new-file PR, negligible. For a feature with 20+ new files, the agent should limit the check to domain-level modules, not pure helpers/types — already implied by "responsibility or interface shape", not "similar name".

**False positives:** a new handler in a directory of five existing handlers is a pattern, not a duplicate. The wording "similar responsibility or interface shape" loads judgment onto the reviewer; this is accepted, not engineered around.

**Knowing new vs edited files:** the agent needs to distinguish creation from modification.
- When invoked via `/review`, the changed-file list is already assembled in Phase 1 (`review.md:25`); pass creation flags through.
- When invoked manually, the reviewer takes the list from `git status` / `git diff --name-status` (creation marker `A`).

## Definition of done

- `code-reviewer.md` Section 7 added.
- Output Format extended with `Structural Integration` subsection.
- Rule 1 extended.
- Manual smoke test: invoke code-reviewer on a changeset with one obviously new module that mirrors an existing one. Verify it flags `DUPLICATE`.
- Manual smoke test: invoke on a changeset with a new handler beside existing handlers of the same shape. Verify it does NOT flag `DUPLICATE` (this is `INTEGRATED` — same pattern, different responsibility).

## Future work (deferred, not part of this plan)

- Wire `code-reviewer` into `/review` pipeline as a phase.
- Spec-failure vs agent-failure audit when tasks fail (separate proposal — RCR idea from the same paper).
- Semantic code search before "X is not implemented" claims (separate proposal).
