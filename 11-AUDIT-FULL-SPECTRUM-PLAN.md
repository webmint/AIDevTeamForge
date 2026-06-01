# 11 — AUDIT FULL-SPECTRUM PLAN

**Status:** Steps 1–9 SHIPPED 2026-06-01 on `develop-2.0-init` (working-tree, not committed). **Step 10 (testForge20 e2e) = HARD GATE, user-driven — pending.** 664 `tests/lib/_audit/` pass; emit verified (`audit command: yes (folder, 5 references)`, 0 `{{` leaks). Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer loops; all reviewer findings fixed (notably a grounded-false Phase 3.1 claim that `preflight-context` exposes constitution text — corrected to "orchestrator reads `constitution.md` directly").

Builds on `10-AUDIT-COMMAND-PORT-PLAN.md` (Phases 0–7 shipped, working-tree). This plan enriches the **already-shipped** `/audit` command so a single default run gives the *full picture* — no lens flag, no mode to remember — on whatever scope it is pointed at (file / directory / project).

## Context for next session

`/audit` today hunts **one dimension: mislogic** (contradictions, lying code, control-flow). A real testForge20 run proved the gap: on the *same* 29-file Vue/TS order directory,

- **audit-2** (shipped command) found Critical 3 / High 24 / Medium 24 — strong on mislogic + layering, but caught language/framework best-practice violations at only **~20% recall** (`as any` 3 vs 16, untyped props 1 vs 7, reactivity 5 vs 23).
- **audit-3** (a hand-injected "system-design + best-practices" brief, deliberately run by the user because they knew the code quality was low) found Critical 2 / High 28 / Medium 34, with **94% of design/best-practice findings surviving the verbatim-quote validation gate** — proving these findings are groundable to the same standard as mislogic.

The user's directive: **one `/audit` run must surface, on any scope** — (1) errors/mislogic [already caught], (2) system-design problems [partial], (3) language/framework best-practice violations [~20% recall — biggest gap], (4) constitution-principle violations [already auto-Critical], (5) duplications [partial]. "Design" = **system/software design (architecture, layering, SOLID, coupling, god components), NOT visual.** Visual/UI design stays out of scope (the existing `design-auditor` agent — Figma/WCAG/responsive — is a different, unrelated tool).

The recall gap is **not** a missing agent — it is that the **checklist does not name those hunts**, so agents improvise and catch ~1 in 5. The fix is to name them, the same way mislogic is named.

## The backbone: declared-category, per "commands don't own shape"

The framework principle — *the helper owns shape; the LLM/command is invited to fill values into an owned vocabulary* (e.g. `severity` is a closed `SEVERITY_ENUM` the agent fills and the schema validates) — is **violated today** by `_report.py:_bucket_finding`, which *infers* a finding's category from **who produced it**:

```
1. "[CONSTITUTION-VIOLATION]" tag  -> Constitution
2. agent == "security-reviewer"    -> Security
3. agent == "architect"            -> Cross-Module
4. everything else                 -> Mislogic            # the renderer guesses the taxonomy
```

This heuristic **breaks** the moment all four agents start producing best-practice and duplication findings — you cannot infer "this is a duplication finding" from "architect emitted it." So the category must become a **producer-declared, helper-owned-vocabulary field**, exactly like `severity`:

| Layer | Owns | Change |
|---|---|---|
| `findings_schema.py` | the closed vocabulary | add `CATEGORY_ENUM` + a validated `category` field (the SSOT) |
| `_OUTPUT_CONTRACT` (`_scope.py`) | the agent's fill-in form | add a required `Category:` field — agent **selects** from the vocabulary, never invents |
| `_consume.py` | parse + validate | parse `Category:`, validate against `CATEGORY_ENUM`, default to `mislogic` on missing/invalid |
| `_report.py:_bucket_finding` | bucketing | **retire the agent-name heuristic** → bucket by the *declared* `category`; keep `[CONSTITUTION-VIOLATION]` tag as the only cross-cutting override |

`[CONSTITUTION-VIOLATION]` stays a **tag, not a category** — a finding is *both* (e.g.) `system_design` *and* a constitution violation; the always-Critical-separate-section rule is orthogonal to what kind of problem it is.

## Decisions (baked in — flip any during review)

1. **No lens flag.** One default run covers all dimensions. (User directive, 2026-06-01.)
2. **Declared category is the backbone** (above). Renderer never infers category from agent.
3. **Dimension vocabulary** (`CATEGORY_ENUM`): `mislogic`, `system_design`, `best_practice`, `duplication`, `security`, `blind_spot`. `cross_module` bucket is **renamed/broadened to `system_design`** (it already *was* the architecture bucket). `best_practice` is **one** bucket (lang/framework idioms + type-safety suppression + untyped boundaries) — sub-typing lives in the per-finding `Pattern:` field, to avoid taxonomy sprawl. *(OQ-A: confirm the six-value set.)*
4. **Lean 1 — four agents, no swap.** Keep `code-reviewer, architect, qa-engineer, security-reviewer`. Do NOT swap in `performance-analyst` (audit-3 did, losing security coverage). Perf-*idiom* smells (inline `reduce` in template) fold into the `best_practice` checklist; runtime perf profiling stays out of scope. Add `performance-analyst` as an additive 5th agent only if a later run shows perf recall is still low. *Change what's hunted, not who hunts.*
5. **Lean 2 — judgment findings are never `Certain`.** Best-practice findings that are opinions ("this watcher should be a computed") must be marked `Likely`/`Speculative`. Grounding stops fabrication, not wrong judgment; the Confidence tier keeps the report triage-able. Enforced as a rule in the new checklist text.
6. **Lean 3 — visual design stays out of scope.** `_report.py` "UI/design consistency (out of scope)" caveat is kept. This plan is *system* design only.
7. **Sibling checklist file, no rename.** Add `references/best-practices-checklist.md` alongside `mislogic-checklist.md`; inject BOTH into every agent brief (always-on). `mislogic-checklist.md` is unchanged (referenced by path in `main.md:49`, `_scope.py`, tests — no rename churn).
8. **Type-safety suppression lives under `best_practice`**, in the new checklist — NOT as a separate edit to `mislogic-checklist.md` (supersedes the earlier single-category idea; cleaner now that category is declared).

## Steps (each leaves the suite green and the build runnable)

Per CLAUDE.md: `.py` changes go through python-engineer → python-reviewer; `.md` content (Step 5, Step 9 spec edits) through instruction-author → instruction-reviewer (+ `claude-code-guide` if any Claude Code authoring convention is touched — none expected, these are reference-prompt + helper files).

### Step 1 — Own the vocabulary (`findings_schema.py`) — foundation, no behavior change
- Add `CATEGORY_ENUM = ("mislogic", "system_design", "best_practice", "duplication", "security", "blind_spot")` beside `SEVERITY_ENUM`.
- Add `category: str` to `Finding` (frozen dataclass) **with a default** of `"mislogic"` placed **last** (after `source_pass`, which currently is last — dataclass default-ordering rule), validated via `_require_in_enum(self.category, CATEGORY_ENUM, ...)`.
- **Verify:** `test_findings_schema.py` extended — valid category accepted, invalid rejected, default applies, existing construction sites still pass (default keeps them valid).

### Step 2 — Renderer buckets by declared category (`_report.py`) — backward-compatible
- Add buckets `_BUCKET_SYSTEM_DESIGN`, `_BUCKET_BEST_PRACTICE`, `_BUCKET_DUPLICATION`; rename `_BUCKET_CROSSMODULE` → `_BUCKET_SYSTEM_DESIGN` ("### System Design"). Headers + `_BUCKET_ORDER` updated.
- Rewrite `_bucket_finding`: (1) `[CONSTITUTION-VIOLATION]` tag → constitution; (2) else `finding.get("category")` mapped to its bucket; (3) missing/unknown → `mislogic`. **Delete the `agent == architect` / `agent == security-reviewer` inference.** (Security findings now bucket because the agent declares `category: security` — more honest: a code-reviewer that finds security drift is categorized correctly.)
- Reconcile "Not Audited" caveats (lines 362-367): keep "UI/design consistency (out of scope)"; soften "Performance (out of scope — use /review)" → "Runtime performance profiling (out of scope — use /review); static performance-idiom smells are in scope."
- **Verify:** `test_report.py` — a finding with each category lands in its section; constitution tag still overrides; category-less finding still defaults to mislogic (proves backward-compat before agents declare anything).

### Step 3 — Parse + validate `Category:` (`_consume.py`)
- Add `_RE_CATEGORY` (`^Category:\s*(.+)$`), parse into the finding dict, validate against `CATEGORY_ENUM` (import from `findings_schema`), default `mislogic` on missing/invalid. Add `'Category:'` to the `_extract_section` known-headings list so it terminates the prior field.
- **Verify:** `test_consume.py` — declared category parsed; bogus category → mislogic; absent category → mislogic; the new heading doesn't bleed into adjacent fields.

### Step 4 — Output contract gains `Category:` (`_OUTPUT_CONTRACT` in `_scope.py`)
- Add a `Category: mislogic | system_design | best_practice | duplication | security | blind_spot` line to the per-finding fixed format, with a one-line gloss of each. Add a hard rule: *"Every finding MUST declare exactly one Category from the list."*
- **Verify:** `test_scope.py` — `_OUTPUT_CONTRACT` contains the Category field + each enum value (keeps contract/enum in lockstep).

### Step 5 — Author `references/best-practices-checklist.md` (instruction-author → instruction-reviewer)
Sections, each with generic framing + stack-tagged *examples* (polyglot-safe; agents already receive framework/language via `preflight-context`):
- **System design** (`system_design`): layering / dependency-direction violations, SOLID-at-scale, god component / low cohesion, business-or-data logic in presentation, prop-drilling-through-pass-through (objective cases only).
- **Language/framework best practices** (`best_practice`): type-safety suppression (`as any` / double-cast / `# type: ignore` / unchecked Go assertion / cast over a nullable), untyped boundaries (prop/param/return typed `any`/`Object` when a concrete type exists), framework reactivity/lifecycle misuse (stale snapshot of a reactive source, watcher-that-should-be-computed, side-effect-in-computed, composable-outside-setup, resource/timer without cleanup), perf-idiom smells (heavy computation in a render/template path).
- **Duplication & divergence** (`duplication`): copy-pasted logic blocks, **diverged** variant copies (the worst case — a fix must land in N places and one has already drifted), repeated domain logic that belongs in a shared layer.
- **Per-constitution-principle adherence**: instruct the agent to read the supplied constitution excerpts and hunt each named principle; constitution violations carry the `[CONSTITUTION-VIOLATION]` tag (→ always Critical, constitution section).
- **Judgment rule (Decision 5):** any finding that is an opinion rather than a demonstrable defect MUST be `Likely`/`Speculative`, never `Certain`.
- Reuse the existing "EXAMPLES, not a find-list; if the codebase has none, report none" framing verbatim from `mislogic-checklist.md` so a Python/Go project reports none of the Vue/TS examples.
- **Verify:** instruction-reviewer pass (logical flow, no hallucinated cross-refs, sentence-level grounding); file reads cleanly; every `Category` it tells agents to emit is in `CATEGORY_ENUM`.

### Step 6 — Inject the checklist + tune focus blocks (`_scope.py:render_agent_brief` + `_FOCUS_BLOCKS`)
- `render_agent_brief`: read `best-practices-checklist.md` from `references_dir` and add it to the `parts` assembly (after `mislogic` checklist, before the per-agent focus). Same OSError→ValueError handling as the existing two reads. Update the docstring assembly-order list.
- `_FOCUS_BLOCKS`: extend each agent's focus so dimensions are owned without overlap — architect → `system_design` + `duplication`; code-reviewer → `mislogic` + `best_practice`; qa-engineer → `blind_spot` (unchanged); security-reviewer → `security` (unchanged). Each focus block reminds the agent to set `Category:` accordingly.
- **Verify:** `test_scope.py` — brief now contains both checklists + the focus; missing best-practices file raises the ValueError; assembly order asserted.

### Step 7 — Emitter / install ride
- Confirm the build copies **all** `src/commands/audit/references/*.md` (so the new file is emitted to `.claude/commands/audit/references/`) and that `render-agent-brief`'s default `--references-dir` resolves it at runtime. If the emitter enumerates references explicitly rather than globbing, add the new file.
- **Verify:** local install into a scratch target → `best-practices-checklist.md` present in `.claude/commands/audit/references/`; 0 `{{` leaks; `/audit` reference list reports the new file.

### Step 8 — `main.md` + reference-doc reconciliation (instruction-author → instruction-reviewer)
- `main.md`: add `references/best-practices-checklist.md` to the reference list (§ line 49 area); update Phase 3 text ("Read `mislogic-checklist.md`" → both checklists); note the `Category:` field in the Phase 3/4 description; update the top-of-file `/audit` summary + "Important rules" if needed.
- `references/report-format.md`: add the new severity-section sub-buckets (System Design / Best Practice / Duplication) to the documented skeleton.
- `references/adversarial-preamble.md`: add one line that every finding declares a `Category` (it is shared across agents).
- **Verify:** instruction-reviewer pass; grep shows no doc still claims "mislogic only" / the old 4-bucket taxonomy.

### Step 9 — Docs propagation
- `CHANGELOG.md`: full-spectrum `/audit` entry (declared-category backbone + new dimensions).
- `src/CLAUDE.md`: update the `/audit` command description (it currently says "hunt for mislogic, cross-file contradictions, and lying code") to name the five dimensions + "system design, not visual."
- Repo-root `CLAUDE.md`: update the `/audit` row in "Where to find what" + the `10-...PLAN` cross-reference to point at this plan for the full-spectrum work.
- **Verify:** grep for stale "mislogic"-only descriptions of `/audit` across docs; none remain.

### Step 10 — testForge20 e2e (USER-DRIVEN — DoD gate)
- Re-install the forge into testForge20; run **default** `/audit db-cse-ui-strata/apps/app-web/src/components/order/` (the same 29-file dir as audit-2/audit-3).
- **Pass criteria:** one default run surfaces the system-design + best-practice + duplication dimensions at recall comparable to audit-3 (not audit-2's ~20%), each finding carries a correct `Category`, the report shows the new sections, and 94%-class grounding survival holds. Compare finding counts to the archived audit-2 (baseline) and audit-3 (hand-brief) as the before/after.

## Open questions for the user

- **OQ-A — vocabulary set.** Confirm `CATEGORY_ENUM = (mislogic, system_design, best_practice, duplication, security, blind_spot)`. Alternative: split `best_practice` into `lang_framework` + `type_safety`. Lean: keep one `best_practice` bucket (sub-type via `Pattern:`), avoid sprawl.
- **OQ-B — rename `cross_module` → `system_design`.** This changes an existing report section heading (anyone reading old reports sees a different label). Lean: rename — it already *is* the architecture bucket and "System Design" matches the user's vocabulary. Confirm.
- **OQ-C — `qa-engineer` blind-spot category.** `blind_spot` (untested branches) is qa-only and arguably a sub-kind of risk rather than a defect dimension. Keep it as its own category, or fold its findings under whichever defect they expose? Lean: keep as its own category (it is how the report already separates "Logic Blind Spots").

## When resuming work

1. Read this plan in full + `10-AUDIT-COMMAND-PORT-PLAN.md` (the shipped substrate).
2. Re-read the actual testForge20 reports at `/Users/mykolakudlyk/Projects/private/testForge20/audits/2026-06-01-audit-{2,3}.md` — they are the before/after evidence base and the e2e comparison target.
3. Resolve OQ-A/B/C with the user if still open.
4. Execute Steps 1→9 in order (each green before the next); Step 10 is the user-driven DoD gate.
5. The backbone (Steps 1-4) is behavior-preserving until Step 6 makes agents declare categories — so the suite stays green throughout and the change is bisectable.
