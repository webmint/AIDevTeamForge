# CONSTITUTION-STRENGTHENING-PLAN

**Status**: Patches applied. Iterative review loop CLEAN (2 iters: 5 findings → 0). Propagation guidance documented below.
**Date**: 2026-05-16
**Branch**: `develop-2.0-init`
**File**: `src/constitution.md` (271 lines, forge framework template)

## Context for next session

`src/constitution.md` is the **forge framework template** that propagates to every consumer project via `/constitute`. Generic SOLID principles in the prior version (`"depend on abstractions, not concrete implementations"`) failed to bind LLM behavior — a parity-test deep-dive against spec 008 (cse-strata MIG-2642 "prevent-duplicate-config-options") found that 4 `/plan` runs + 1 `/research` run + 1 wrapper-plan all missed the cross-layer wrapper pattern despite citing constitution rules. Real shipped solution (commits 74adb5b17 + df231933a in `db-cse-ui-strata`) added the wrapper pattern at code-review time; constitution + spec + research all permitted the violating import.

Root fix: codify the binding concrete patterns at the framework-template level. The 6 patches below replace generic-principle text with 3-step procedural anchors LLMs can transcribe into spec §7 + plan File Impact + research Constitution Constraints.

### Origin: parity-test gap analysis

Detailed gap analysis lives in `PLAN-COMMAND-REDESIGN-PLAN.md` Step 6 + adjacent conversation logs. Key citation: spec 008 §4 + §7 prescribed `import { CoreQuoteLine } from 'pkg-cse-core'` directly into a Vue file — violating Clean Arch dependency-inversion. Constitution's pre-patch generic DI rule didn't surface the violation. Real ship corrected via module-scope `export const isSingleInstance = (line) => CoreQuoteLine.isSingleInstance(line)` wrapper pattern.

## Patches applied (6 total — already on disk)

All in `src/constitution.md`. Verbatim location + intent:

### 1. §3.6 SOLID Open/Closed (line 100)

**Before**: Generic *"extend behavior through composition or new implementations, not by modifying existing working code."*
**After**: 3-step concrete pattern — new-implementation / tweak-everyone-wants / strategy-parameter. Cross-refs Minimal Changes (§6.1).

### 2. §3.6 SOLID Liskov Substitution (line 104)

**Before**: Generic *"subtypes must be usable wherever their parent type is expected without breaking behavior."*
**After**: 3-step rule — contravariant parameters / covariant returns / no new exception variants. Cross-refs Composition (§4.3).

### 3. §3.6 SOLID Interface Segregation (line 110)

**Before**: Generic *"don't force consumers to depend on methods they don't use."*
**After**: 3-step "split along consumer use-cases" pattern + ≤5 method ceiling for non-facade interfaces.

### 4. §3.6 SOLID Dependency Inversion (line 116) — LOAD-BEARING

**Before**: Generic *"depend on abstractions (interfaces, types), not concrete implementations. High-level modules should not import from low-level modules directly."*
**After**: 3-step concrete pattern:
1. Implement the behavior on the inner layer's entity / class.
2. Export a module-scope named function from the same module that delegates to the entity method, taking DTO-typed inputs (not class-instance inputs).
3. The outer layer imports the named function, NEVER the inner-layer entity class.

Framework-agnostic. Applies across all cross-layer boundaries (presentation → domain, view → business-logic, API → use-case).

This is the patch that directly addresses the MIG-2642 gap.

### 5. §3.7 Check Before You Build (line 133)

**Before**: *"Search for it using Grep and Glob before creating a new one."*
**After**: CBM-first canonical tools (`search_graph`, `search_code`, `get_code_snippet`, `trace_path`) with Grep/Glob as fallback for non-code text. References F.11 hook at `.claude/hooks/cbm-code-discovery-gate`.

### 6. §4.3 PREFER Composition over inheritance (line 196)

**Before**: Generic *"Build behavior by combining small pieces, not by extending base classes. Deep inheritance hierarchies are fragile."*
**After**: 3-step concrete pattern — name the role / define interface / inject via constructor parameter. Deep hierarchies >2 levels flagged.

## Verification status (already-confirmed)

- File line count: 271 (was 240).
- `grep -c "Concrete pattern:"` in §3.6 SOLID block: 4 (Open/Closed, LSP, ISP, DI). Composition block at §4.3 also carries "Concrete pattern:" — 5 total.
- `grep -c "search_graph"`: 1 (§3.7).
- `grep -c "module-scope named function"`: 1 (DI block).
- `grep -cE "abstraction surface|wrapper export"`: 2 (DI block context).
- All 6 patches verified inline via `Read` immediately after `Edit`.

## Outstanding work

**Iterative review loop** — DONE 2026-05-16. Ran in fresh session.

### Iteration 1 — 5 findings, all fixed inline

1. **High** — §3.7 line 148: hook claim ("block raw Read/Grep/Glob on code-discovery calls") overstated the hook's behavior (one-shot per session, not sustained). Fixed: "block the first raw `Read` / `Grep` / `Glob` call per session with a reminder to use CBM (subsequent calls in the same session pass through)".
2. **Medium** — §3.6 LSP line 109: cross-ref cited `§4.3 Composition over inheritance` but actual heading is `§4.3 PREFER [universal]` with composition as an inner bullet. Fixed: `§4.3 PREFER — "Composition over inheritance" bullet`.
3. **Medium** — §3.6 DI lines 116-121: pattern wording ("module-scope named function", "DTO-typed inputs") was JS/TS-specific despite the closing "regardless of framework or language" claim. Fixed: language-neutral wording with per-language instantiations parenthesized (named function export in JS/TS, module-level function or Protocol in Python, interface in Java/C#/Go, trait in Rust); "DTO-typed inputs" → "value-object / data-typed inputs"; closing sentence reframed to "the exposure mechanism varies by language, the rule does not".
4. **Low** — §3.7 lines 137-138: search-prompt bullets used framework-specific vocabulary ("composable", "hook", "shared component", "UI pattern") in a universal template. Fixed: bullet 2 → "A helper or reusable module that covers your use case"; bullet 3 → "A shared abstraction or building block that handles this pattern".
5. **Nit** — §3.7 line 146: `trace_path` `mode` enum was truncated to `mode=calls` only; canonical form elsewhere shows `calls|data_flow|cross_service`. Fixed: appended `|data_flow|cross_service`.

### Iteration 2 — 0 findings

Verified by `instruction-reviewer` on the patched file. Dimensions cleared: logical flow, cross-reference consistency, sentence-level hallucination, DI step-2 binding strength, framework-name leak. Loop terminates.

## Propagation path (recommendation)

### How `constitution.md` reaches consumer projects today

- `install.sh:117-124` copies `src/constitution.md` → `<target>/constitution.md` ONCE, only when no existing file is present (brownfield safety).
- `manifest.json` lists `constitution.md` under `userOwned.patterns` (line ~at "Files generated/customized per-project — NEVER overwrite"). So `update.sh` does NOT overwrite or three-way-merge it on update. The `update.sh:818` comment claiming "constitution.md / agents — those still three-way merge upstream" is stale/aspirational — there is no merge entry for `constitution.md` in `manifest.json.mergeFiles`.
- For projects that have already run `/constitute`, the rendered `constitution.md` comes from `constitute_helper render` walking `.devforge/constitute.json` — NOT directly from `src/constitution.md`. The universal-section rules in the state JSON were transcribed BY THE LLM at /constitute time, drawing on `src/constitution.md` as the implicit universal-defaults source.
- Conclusion: `src/constitution.md` edits do not auto-propagate. There is no template-pull mechanism for the rendered consumer artifact.

### Propagation options

**A. Re-run `/constitute` on each consumer project.** LLM re-transcribes universal defaults from the now-patched `src/constitution.md` into the state JSON; helper renders fresh `constitution.md`. Pros: uses the canonical command, exercises the full chain. Cons: re-elicits configuration via the wizard; project-specific section content (§3.1 Type Safety, §4.1.1 project-specific ALWAYS-DO, §5 Domain Rules, etc.) gets regenerated and may diverge from the prior run. Not a pure universal-only sync.

**B. Surgical state edits via helper setters.** Call `constitute_helper update-rule` / `set-section-body` on each consumer's `.devforge/constitute.json` to replace the universal-rule text for §3.6 (Open/Closed, LSP, ISP, DI), §3.7 (Check Before You Build), §4.3 (Composition over inheritance), then `render`. Pros: surgical, preserves project-specific. Cons: requires mapping each patch to specific setter calls + rule keys; no batch sync tool exists.

**C. Manual constitution.md edits in consumer projects (then accept drift from `.devforge/constitute.json`).** Edit the rendered `constitution.md` by hand to mirror the 6 patches. Pros: fastest. Cons: next `/constitute` re-render OVERWRITES from state JSON (which still has old universal text) — drift inevitable. NOT recommended.

### Recommendation

**Option A on next normal `/constitute` re-run, Option C-skip in the interim.**

- Don't proactively re-`/constitute` consumer projects (testForge20, cse-strata-ws-forge wrapper). The wizard re-elicitation is high-friction and the universal text is currently *advisory* — old generic SOLID text in their constitution.md still works, it just doesn't bind LLMs as tightly as the new pattern.
- Next time any consumer project runs `/constitute` (e.g., as part of a re-bootstrap, schema migration, or wrapper-mode setup change), the new universal text propagates automatically.
- If a consumer urgently needs the strengthened DI rule TODAY (e.g., to fix the MIG-2642-style cross-layer wrapper gap that triggered this plan), apply Option B surgically — open a follow-up plan for that specific consumer with the per-rule setter calls.
- **Do not document Option C** as a supported path — manual constitution.md edits drift from `.devforge/constitute.json` and get clobbered on next render.

### Future work (not blocking this plan)

A `forge-internal:resync-universal-constitution-rules` helper subcommand that reads the current `src/constitution.md` universal blocks + updates `.devforge/constitute.json` universal-rule bodies in place (no wizard re-run) would close the gap properly. Out of scope here; flag if a consumer project hits the DI gap before next normal /constitute.

## Brief for instruction-reviewer (use verbatim in fresh session)

```
Review /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/constitution.md (271 lines, forge framework template) after 6 strengthening patches.

CONTEXT
=======

Forge framework's CONSTITUTION TEMPLATE. Propagates to consumer projects via /constitute. Patches strengthen generic SOLID principles + Composition rule + Search-Before-Build rule with binding concrete patterns the prior generic versions lacked.

The 6 patches applied (already on disk):

1. §3.6 SOLID Open/Closed (line 100) — added 3-step concrete pattern (new implementation / tweak / strategy parameter).
2. §3.6 SOLID Liskov Substitution (line 104) — added contravariance / covariance / exception-declaration rules.
3. §3.6 SOLID Interface Segregation (line 110) — added 3-step "split along consumer use-cases" pattern + ≤5 method ceiling.
4. §3.6 SOLID Dependency Inversion (line 116) — added 3-step concrete pattern (implement on entity → export module-scope named function → outer layer imports the named function NEVER the entity class). Framework-agnostic.
5. §3.7 Check Before You Build (line 133) — replaced Grep/Glob with CBM-first canonical tools (search_graph, search_code, get_code_snippet, trace_path). Fallback to Grep/Glob for non-code text only. References F.11 hook at .claude/hooks/cbm-code-discovery-gate.
6. §4.3 PREFER Composition over inheritance (line 196) — added 3-step concrete pattern (name the role / define interface / inject via constructor parameter).

WHAT TO REVIEW
==============

1. Logical flow across the 6 patches: do they read coherently top-to-bottom? Does §3.6 SOLID still flow as a unit? Does §4.3 Composition-over-Inheritance correctly cross-reference §3.6 LSP?

2. Cross-references:
   - §3.6 LSP closing line cites "§4.3 Composition over inheritance" — verify section reference.
   - §3.6 Open/Closed step 2 cites "Minimal Changes, §6.1" — verify section reference.
   - §3.7 references .claude/hooks/cbm-code-discovery-gate — verify against src/CLAUDE.md "CBM-first Protocol Enforcement" section and src/hooks/ directory contents.

3. Sentence-level hallucination check (feedback_sentence_level_hallucination_check_specs): every sentence must be mechanically true / verifiable now / explicit forward reference. Particular concerns:
   - DI rule's claim about hooks blocking raw Read/Grep/Glob — verifiable against src/hooks/cbm-code-discovery-gate + src/settings.template.json.
   - All "3-step concrete pattern" numbered procedures — each step should be a real pattern, not invention.

4. Framework-agnostic check: constitution must NOT name specific frameworks (Vue, React, Angular, etc.). Walk every patched passage; flag any framework name. Abstract layer terms (presentation, domain, view, business-logic, API, use-case) are acceptable.

5. Concrete-pattern binding strength: each numbered step should be specific enough that an LLM transcribing it into a plan or spec produces a non-ambiguous instruction. Flag any step that's still generic.

6. Anything else the prior audit missed (1st pass on these patches).

OUTPUT FORMAT
=============

Per feedback_audit_format:
- Count first.
- One finding at a time. Each: Severity / Location (file:line) / Issue / Why it matters / Fix.
- End each with "fix / defer / skip / discuss?".

If zero findings, state so explicitly. The loop terminates.

Read-only.
```

## Resume-in-fresh-session prompt

Paste this into a new Claude Code session in `~/Projects/ai-dev-team-forge`:

```
Resume CONSTITUTION-STRENGTHENING-PLAN.md at repo root. Read the plan top-to-bottom. Six patches are already applied to src/constitution.md (verified inline). Outstanding work: run iterative review loop via instruction-reviewer agent using the verbatim brief in `## Brief for instruction-reviewer`. Apply findings per audit format; re-loop until 0 findings or only paranoid items. Then update this plan with loop results + recommend the propagation path (re-`/constitute` on consumer projects vs manual constitution sync).
```

## When resuming work

1. Read this plan top-to-bottom.
2. Verify the 6 patches are still in `src/constitution.md`:
   ```bash
   grep -c "Concrete pattern:" /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/constitution.md
   ```
   Expect 5 (Open/Closed, LSP, ISP, DI, Composition).
3. Verify CBM tools in §3.7:
   ```bash
   grep -c "search_graph\|search_code\|get_code_snippet\|trace_path" /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/constitution.md
   ```
   Expect ≥4 (one per tool name; may be higher if tools cited multiple times).
4. Dispatch `instruction-reviewer` with the verbatim brief above.
5. Iterate apply-review until clean.
6. After clean: document propagation path. Consumer projects (testForge20, cse-strata-ws-forge wrapper) have their own constitution.md files that DIFFER from the template (filled-in by their `/constitute` run). Re-running `/constitute` may or may not regenerate the universal sections — needs verification. Manual sync of universal sections (§3.5, §3.6, §3.7, §4.1, §4.2, §4.3, §6.1, §6.2, §6.3, §6.4) is the safe propagation path.

## Out of scope (this plan)

- **Project-specific section population** (§2 Architecture Rules, §3.1 Type Safety, §4.1.1 / §4.2.1 / §4.3.1 project-specific anti-patterns, §5 Domain Rules, §6.5 Deprecation, §6.6 Project-Specific Workflow) — those get filled by each consumer's `/constitute` run, not the template patches.
- **`/specify` strengthening** to actually surface the new DI rule in spec §7 — separate work, documented in `PLAN-COMMAND-REDESIGN-PLAN.md` future-work notes.
- **`/plan` strengthening** — should be downstream-redundant once `/specify` carries the rule forward into spec §7.
- **Existing consumer sync** (testForge20, cse-strata-ws-forge wrapper) — documented as "When resuming work" step 6.

## Related plans

- `PLAN-COMMAND-REDESIGN-PLAN.md` — `/plan` command redesign; Step 6 parity test surfaced the original DI gap that drove this plan.
