# THREE-LAYER-SEPARATION-PLAN

**Status**: Draft — pending user approval
**Date**: 2026-05-17
**Branch**: `develop-2.0-init`
**Owner**: orchestrator (Claude) + user
**Origin**: Kapil Viren Ahuja, *"Spec-Driven Development Isn't Broken. It will collapse."* (Medium, 2026-05-03) — read in chat 2026-05-17. Article's three-layer schematic (Intent / Spec / Implementation) + Four Crafts (Intent / Spec / Context / Prompt) + 5-level Substrate Stack mapped against forge `develop-2.0-init` state. Five gaps surfaced.

## Context for next session

Article argues spec-driven dev collapses because one document ("the spec") jams three separable layers into one: **Intent** (user-authored — goals, constraints, success/failure conditions, scale), **Spec** (evaluable contract — pass/fail tests), **Implementation** (system-authored — architecture choice from empirical memory). Forge sits at Substrate Stack Level 2.5 — has CBM (Codebase Memory MCP) substrate, helper-owns-shape pattern, constitution-as-constraints, research-helper intent gates — but `/specify` still emits a single 9-section doc that mixes layers.

This plan addresses five gaps surfaced by the article-vs-forge analysis. Gaps are ranked by severity + sequencing. Gap A is load-bearing (every spec uses §7); Gap B depends on A; Gap C unlocks the article's main value claim (empirical-memory-driven architecture); Gap D is theoretical for forge's scope; Gap E becomes critical at multi-month timescales.

### Article principles applied here

- **Three-layer separation**: Intent → Spec → Implementation. No layer pre-locks the next.
- **Spec = eval-shaped contract**: every claim convertible to pass/fail test.
- **Implementation belongs to the system**, sourced from empirical memory (knowledge base of prior decisions + their outcomes), not authored into spec by user.
- **Plays are scaffolding, not destination**: precompiled workflows bridge maturity gap until model can resolve intent directly. Forge's 4-command sequence IS a play.

### Forge state baseline (verified 2026-05-17)

| Article concept | Forge equivalent | State |
|---|---|---|
| Intent Crafting | constitution patches + research-helper framing/scope gates | Partial — no `intent.md` artefact; constraints scattered across constitution + spec §7 |
| Spec Crafting | `/specify` §5 AC (EARS notation) | Strong — eval-shaped per IEEE 29148-2018 |
| Context Crafting | CBM (search_graph / search_code / trace_path / get_code_snippet) + F.11 hooks | Strong on code; weak on decision-history |
| Prompt Crafting | `/init-forge → /generate-docs → /configure → /constitute → /specify → /plan → /execute-task` | Strong — full play sequence |
| Empirical memory | CBM graph + docs/ | Indexes code structure, NOT prior /plan decision-rows |
| Drift detection | `.devforge/lib/cbm_sync_helper` | Stamps repo HEAD, NOT per-spec spec.md → code |

### Sequencing rationale

1. **Gap A first** — §7 split is the entry point for layer separation; downstream commands inherit. Blocks B if not done.
2. **Gap B second** — fold A into PLAN-COMMAND-REDESIGN-PLAN before that lands. Avoids carrying §7 collapse into `/plan` v2 port.
3. **Gap C third** — Adds CBM-consult phase to `/plan`. Requires (B) so the new phase can sit inside the redesigned `/plan`.
4. **Gap E fourth** — per-spec drift stamp. Independent of A–C; can land any time but most useful AFTER A–C since drifted spec without separated layers is doubly opaque.
5. **Gap D deferred** — intent-kind axis (consumer vs engineering). Recommendation = SKIP. See section.

### Cross-references

- `PLAN-COMMAND-REDESIGN-PLAN.md` — Gap B + Gap C land inside this. Either merge them into that plan or carry them as a supplement.
- `CONSTITUTION-STRENGTHENING-PLAN.md` — already-applied 6 patches went the right direction (concrete-binding patterns > generic principles). No change needed; this plan extends the trajectory.
- `RESEARCH-HELPER-API-ENUM-PLAN.md` — research-helper Patches 1–4 (framing / scope / layer-boundary / single-layer recommendation) ARE intent-crafting discipline gates. Already shipped. No change needed.
- Memory: `feedback_helper_owns_shape_principle`, `feedback_sentence_level_hallucination_check_specs`, `feedback_cross_check_after_every_change`, `feedback_track_a_yagni_rollback` — all govern this plan's execution.

---

## Gap A — `/specify` §7 conflates intent-constraints with architecture pre-locks

### Evidence

`src/commands/specify/main.md:557-570` — Step 4.6 §7 Technical Constraints invocation:

```
.devforge/lib/specify_helper record-constraint \
    --kind <follow|not_break|use> \
    --content "<constraint text>"
```

Render labels: `follow` → "Must follow"; `not_break` → "Must not break"; `use` → "Must use". Constraint sources cited: *"constitution.md, architecture patterns, or external systems."*

The `use` kind permits — structurally — content like:

- `record-constraint --kind use --content "microservice architecture"` (architecture pre-lock)
- `record-constraint --kind use --content "Redis for session cache"` (implementation pre-lock)
- `record-constraint --kind use --content "Vercel for deployment"` (the exact Ahuja Vercel→GCP scenario)

Helper accepts all three. No structural gate distinguishes:

- (a) **constitution-anchored constraint** (transcribing a §3.x rule LLM must honor) — legitimate intent-layer rule.
- (b) **NFR constraint** (scale, latency, compliance — informs architecture) — legitimate intent-layer constraint.
- (c) **architecture pre-lock** (user said "use Redis") — illegitimate per article; belongs to `/plan` not `/specify`.

`src/commands/specify/main.md:476` correctly states: *"The spec describes WHAT, not HOW; solutions come in `/plan`."* — but only for §3 Desired Behavior. §7 is silent on the WHAT/HOW boundary.

### Severity

**HIGH**. Every spec uses §7. Every architecture pre-lock leaked into §7 propagates downstream into `/plan` Phase 1.5 enumeration (Gap B) and through to `/execute-task`. Article's load-bearing failure mode (Vercel→GCP spec rewrite) lands here verbatim.

### Article principle violated

> "Implementation — the architectural layer — belongs to the system. Not to the user. Not to the spec document. This is the line the industry keeps crossing."

### Counter-argument considered

The `use` kind is dual-use. Most current invocations (verified mental scan of cse-strata 008 spec, parity-test target) populate it with constitution-anchored content: "Must use the wrapper pattern per constitution §3.6". That's intent-layer rule transcription, not architecture pre-lock. So `use` isn't structurally broken — it's structurally permissive.

**Rebuttal**: structural permissiveness IS the failure mode at framework-template scale. Per memory `feedback_zero_escape_hatch_policy` — "no discipline rule may contain an escape hatch." A `use` field that ALLOWS architecture pre-locks but DISCOURAGES them in prose is the textbook escape hatch. Spec text drifts; LLMs interpret permissively; today's well-disciplined "Must use wrapper pattern per §3.6" becomes tomorrow's "Must use microservice."

### Proposed fix

Split `record-constraint` `--kind` taxonomy:

| New kind | Render label | Permitted content | Helper gate |
|---|---|---|---|
| `nfr` | "Must satisfy NFR" | scale / latency / availability / compliance / security-class | reject empty `--quantifier` (numeric or named threshold) |
| `constitution_anchor` | "Must follow constitution §X.Y" | constitution-section citation + verbatim quoted rule | reject unless `--constitution-ref` matches a real §-heading in `constitution.md` (helper greps target's constitution at write time) |
| `external_system` | "Must integrate with <system>" | external dependency name + protocol (e.g. "must speak SAML 2.0 to corporate IdP") | reject without `--protocol` or `--contract-doc-ref` |
| ~~`use`~~ | REMOVED | — | hard-reject; LLM error message: *"`use` removed — use `nfr` for scale/latency, `constitution_anchor` for code-pattern rules, `external_system` for integrations, or move architecture choices to `/plan`."* |
| `follow` | "Must follow" | retained for process rules (e.g. "Must follow conventional-commits") | unchanged |
| `not_break` | "Must not break" | retained for behavior-preservation | unchanged |

### Plan steps

#### Step A.1 — Helper API change

`src/devforge/lib/specify_helper`:

A.1.1 Replace single `--kind=use` enum slot with three new enums: `nfr`, `constitution_anchor`, `external_system`. Retain `follow` and `not_break`.

A.1.2 Add per-kind validators:

- `nfr`: require `--quantifier` (string). **Reject vague quantifiers** — helper enforces a regex + blocklist gate (closes Risk 2 from 2026-05-17 audit):

  ```python
  NUMERIC_THRESHOLD = re.compile(
      r'\d+\s*(ms|s|sec|min|hr|users?|req/s|rps|qps|tps|GB|MB|KB|TB|%|\$|connections?|rows?|records?)\b',
      re.IGNORECASE,
  )
  VAGUE_BLOCKLIST = {
      "high", "low", "fast", "slow", "scalable", "good", "acceptable",
      "reasonable", "robust", "performant", "efficient", "secure", "reliable",
  }

  def validate_quantifier(q: str) -> tuple[bool, str]:
      qstripped = q.strip()
      if not qstripped:
          return False, "nfr: --quantifier required and non-empty"
      if qstripped.lower() in VAGUE_BLOCKLIST:
          return False, (
              f"nfr: vague quantifier '{q}' rejected. "
              "Use numeric threshold + unit (e.g. '10K users @ p95 < 200ms') "
              "OR named-class with cite source (e.g. 'PCI-DSS Level 1')."
          )
      if not NUMERIC_THRESHOLD.search(qstripped):
          return False, (
              "nfr: quantifier requires numeric threshold with unit "
              "(ms/s/users/req/rps/GB/%/$/connections/rows) "
              "OR named-class citation (e.g. 'PCI-DSS Level 1', 'SOC 2 Type II'). "
              "Bare adjective rejected as vague."
          )
      return True, ""
  ```

  Rationale: bare `--quantifier "high"` would be technically non-empty but semantically vacuous — escape hatch in disguise. Numeric-with-unit OR named-compliance-class are the two legitimate shapes.

- `constitution_anchor`: require `--constitution-ref` (e.g. `§3.6`). Helper reads `<install_root>/constitution.md`, greps for `^### §<ref>` or `^### <ref>`. Reject on miss with stderr `constitution_anchor: §<X> not found in constitution.md`. **Known limitation (Risk 3)**: validator confirms section EXISTS, not that body matches framework canonical. Stale-body case caught by sibling `CONSTITUTION-DRIFT-DETECTOR-PLAN.md` (maintainer-side periodic check). Document in Step A.2 spec text.
- `external_system`: require either `--protocol` (e.g. "SAML 2.0", "REST", "gRPC") or `--contract-doc-ref` (path to OpenAPI / proto file).

A.1.3 Migrate state file shape: rename `constraints[*].kind` value `use` to one of the three new kinds. Migration script reads existing `.devforge/specify-state.json` files (if any exist in test fixtures) and rewrites — most likely no real prod state exists yet on develop-2.0-init since `/specify` only just shipped.

A.1.4 **Test-first per `feedback_test_first_python_helpers`**:

- `tests/lib/test_specify_helper.py`: add cases per new kind. Round-trip via real `specify_helper render` (no hand-authored state JSON).
- Cases:
  - valid `nfr` with numeric-threshold quantifier (`"10K users @ p95 < 200ms"`)
  - valid `nfr` with named-class quantifier (`"PCI-DSS Level 1"`) — NOTE: regex test only catches numeric; named-class path requires additional regex branch OR `--cite-source` flag. Decide at impl time; document choice.
  - **reject empty-quantifier** `nfr` with stderr matching "required and non-empty"
  - **reject vague-quantifier** `nfr` (`--quantifier "high"`) with stderr matching "vague quantifier"
  - **reject bare-adjective** `nfr` (`--quantifier "fast and scalable"`) with stderr matching "numeric threshold"
  - valid `constitution_anchor` with real `§3.6` ref against fixture constitution
  - reject missing-ref `constitution_anchor` with stderr citing the section
  - reject `--kind=use` with helpful stderr citing all three replacement kinds
  - valid `external_system` with `--protocol "REST"`
  - reject `external_system` with neither `--protocol` nor `--contract-doc-ref`
- Run: `cd src/devforge && pytest ../../tests/lib/test_specify_helper.py -v` → green.

#### Step A.2 — Spec text update

`src/commands/specify/main.md` Step 4.6 (§7) rewrite:

A.2.1 Replace the single bash block with a per-kind explanation block. State the WHAT/HOW boundary explicitly: *"§7 captures **constraints that drive architecture**, not **the architecture itself**. Architecture choices land in `/plan`, sourced from CBM-indexed prior decisions + constitution rules."*

A.2.2 Add per-kind invocation examples:

```bash
# NFR — drives architecture in /plan
.devforge/lib/specify_helper record-constraint \
    --kind nfr \
    --quantifier "10K concurrent users @ p95 < 200ms" \
    --content "must support 10K concurrent users with p95 latency under 200ms"

# Constitution anchor — transcribes a code-pattern rule
.devforge/lib/specify_helper record-constraint \
    --kind constitution_anchor \
    --constitution-ref "§3.6" \
    --content "domain types from pkg-cse-core must be wrapped at module scope (Open/Closed)"

# External system — integration contract
.devforge/lib/specify_helper record-constraint \
    --kind external_system \
    --protocol "REST" \
    --content "must integrate with corporate IdP via OIDC"
```

A.2.3 Anti-pattern callout:

> **DO NOT** use `--kind nfr` to encode architecture choice. `--content "must use microservice architecture"` is rejected — that's a `/plan` decision, sourced from CBM-indexed prior plans + constitution. If you're tempted to record architecture in §7, the corresponding NFR is what belongs here.

A.2.3.b **Known limitation disclosure** (Risk 3 from 2026-05-17 audit):

> **`constitution_anchor` validates section EXISTS, not that the cited body matches framework canonical.** If the consumer's `<install_root>/constitution.md` has drifted from framework `src/constitution.md` (e.g. consumer was `/constitute`'d before a strengthening patch landed), the anchor citation will pass the structural gate but reference stale body text.
>
> Defense: maintainer runs `constitute_helper forge-internal:verify-universal-defaults --consumer-path <dir>` periodically (per `CONSTITUTION-DRIFT-DETECTOR-PLAN.md`) to catch staleness. Detector reports `MISSING` / `DRIFT` findings; resync stays manual until a separate plan ships the writer.
>
> Practical implication: an LLM citing `§3.6` via `constitution_anchor` is citing the consumer's rendered body, not framework canonical. Both surfaces re-converge on natural `/constitute` re-run.

A.2.4 Verify the existing Phase 4.5 coverage rule still names §7 by section number (it does — line 543) — no cross-ref break.

#### Step A.3 — Dual-agent review (per `feedback_dual_agent_verify_command_statements`)

A.3.1 Spawn `instruction-author` agent: brief contains Steps A.1 + A.2 spec, existing `src/commands/specify/main.md` Step 4.6 verbatim, the rationale above. Goal = rewrite Step 4.6 against new helper API, preserve helper-owns-shape, no LLM-side validation logic (helper owns gates).

A.3.2 Spawn `instruction-reviewer` agent in parallel: brief = read the rewritten Step 4.6, check intra-file consistency (Phase 4.5 coverage rule cross-ref, Step 4.6 header numbering, render-label naming).

A.3.3 Spawn `claude-code-guide` agent: verify no Claude Code authoring conventions broken. Brief: "Does Claude Code support multi-required-flag enum subcommands? Confirm idiomatic CLI shape for `--kind X --required-flag-for-X Y`."

A.3.4 Iterate until clean per `feedback_iterative_review_loop_preferred`.

#### Step A.4 — Cross-check propagation

A.4.1 Grep for `record-constraint` across `src/`:

```bash
grep -rn "record-constraint" src/
```

Expected hits: `src/commands/specify/main.md` Step 4.6 (just edited); maybe template fixtures.

A.4.2 Grep test fixtures:

```bash
grep -rn "kind.*use\|use.*kind" tests/lib/fixtures/
```

Update any fixture that uses old `--kind use` to the new kind taxonomy.

A.4.3 Grep `cse-strata-ws-forge` reference project (out-of-tree — do NOT modify, but verify the legacy v2 plan doesn't depend on `use` kind in a way the port would carry over):

```bash
grep -n "record-constraint\|kind.*use" /Users/mykolakudlyk/Projects/doosan/cse-strata-ws-forge/.claude/commands/plan.md
```

Plan-port (Gap B) handles whatever surfaces.

A.4.4 Per `feedback_preempt_future_hallucination`: a fresh session might falsely believe `--kind use` is still valid. The fix is: helper rejects on attempt with explicit migration message naming all three new kinds. Memory entry recommended (see "Memory updates" below).

#### Step A.5 — Verify end-to-end

A.5.1 In `~/Projects/testForge20` (or fresh target):
```bash
bash install.sh
```

A.5.2 Run `/specify` against a synthetic feature description that would tempt architecture pre-lock. Confirm the spec's §7 contains `nfr` + `constitution_anchor` entries and NO architecture choices.

A.5.3 Confirm `specify_helper render` output renders the three new render labels correctly.

A.5.4 Confirm legacy `--kind use` invocation exits 2 with stderr citing the three new kinds.

### Tradeoffs / argued

- **Cost**: doubles §7's invocation surface area; LLM has more decisions per-constraint. Mitigated by helper-owned gates — LLM can't slip; gate forces correct kind.
- **Risk**: `constitution_anchor` requires constitution to be populated. Phase 0.1 already gates on `_Run /constitute to populate_` literal absence (specify/main.md:30), so this is structurally safe.
- **Alternative considered + rejected**: keep `--kind use` but add a `--cite-constitution-ref` optional flag, lint-warn when missing. Rejected per `feedback_zero_escape_hatch_policy` — optional flags are escape hatches.
- **Alternative considered + rejected**: separate the three layers into three artefact files (`intent.md` / `spec.md` / `plan.md`). Rejected as L3 jump — too big for one patch cycle. Article confessions confirm even Ahuja's tool isn't fully L3. Deferred to future plan.

### Out of scope (Gap A)

- Renaming §7 heading itself (e.g. "Non-Functional Intent & Constraints"). Considered. Skipping — header rename creates downstream find/replace work across reference projects + parity fixtures. Render label changes are sufficient.
- Adding new sections (§7a / §7b split). Considered. Skipping — single-section with kind taxonomy is cleaner than two sections with overlap risk.

---

## Gap B — `/plan` redesign inherits §7 collapse via Phase 1.5 enumeration

### Evidence

`PLAN-COMMAND-REDESIGN-PLAN.md` Step 2.5 (line ~120 in that file):

> `render-findings-from-spec <spec-path>` — Phase 1.5 skeleton.
> Parse the spec's §3 Desired Behavior bullets, §4 Affected Areas table rows, §5 AC subsections (5.1–5.7), §6 OOS bullets, **§7 Constraints bullets**, §8 Open Questions bullets, §9 Risks table rows.

Phase 1.5 enumerates §7 verbatim into the plan's conversation. With §7 collapsed (Gap A), any architecture pre-lock in spec's §7 propagates into `/plan`'s Phase 1.5 findings — and from there into Phase 2 plan rendering. Plan then locks the architecture row to the pre-lock without consulting prior-art / CBM (Gap C).

Without Gap A's fix, Gap B's `/plan` redesign would ship the parity-validated v2 port AND carry the layer-collapse forward. The Vercel→GCP scenario article describes lands here.

### Severity

**MEDIUM** — wholly dependent on Gap A. If A lands, B's fix is mostly inheritance.

### Article principle violated

Same as Gap A — implementation pre-locks in spec doc propagate downstream.

### Proposed fix

Gate Gap B fix on Gap A delivery. Once A's new kind taxonomy is live:

#### Step B.1 — Update `plan_helper render-findings-from-spec`

B.1.1 `src/devforge/lib/plan_helper.py` (to-be-built per PLAN-COMMAND-REDESIGN Step 2.5): when parsing §7, emit per-kind buckets, NOT a flat bullet list. New skeleton shape:

```markdown
### §7 Constraints

**NFR constraints (drive architecture):**
- §7 row 1: <quantifier> — <content>
- §7 row 2: <quantifier> — <content>

**Constitution anchors (transcribed rules):**
- §7 row 3: §3.6 — <content>

**External system contracts:**
- §7 row 4: <protocol> — <content>
```

B.1.2 Each bucket has [PLAN COVERAGE: ?] marker — but the NFR bucket explicitly drives the next phase (Phase 2 architecture decision). Constitution anchors fold into the Constitution Constraints column. External-system contracts get their own integration row.

#### Step B.2 — Update `plan_helper render-plan-table`

B.2.1 Plan table currently (per v2 cse-strata plan.md) renders an architecture-decision row. After Gap A: architecture row sources from (i) NFR constraints from §7-nfr bucket, (ii) prior-art via CBM consult (Gap C), (iii) constitution rules from §7-constitution_anchor bucket. NEVER from a `use`-kind pre-lock — that path is gone.

B.2.2 Helper emits the architecture-decision row with NFR ↔ choice mapping (e.g., "10K concurrent users → service per bounded context" with citation).

#### Step B.3 — Update PLAN-COMMAND-REDESIGN-PLAN.md

B.3.1 Edit `PLAN-COMMAND-REDESIGN-PLAN.md` Step 2.5 to reference the new §7 sub-bucket shape. Add Step 2.5.b: "NFR-aware findings emission."

B.3.2 Edit `PLAN-COMMAND-REDESIGN-PLAN.md` Step 6 (parity): the v2 baseline was measured BEFORE Gap A. Decide whether to re-baseline or accept that the new §7 shape will introduce legitimate variance vs v2 outputs. Argued recommendation: re-baseline post-A — the 4.4–5% target was for the OLD §7 shape; new shape needs its own variance measurement. Note variance target may shift to 5–7% acceptable since plan now references richer §7 structure.

#### Step B.4 — Dual-agent review

Same as A.3 — `instruction-author` + `instruction-reviewer` + `claude-code-guide` on the rewritten plan-redesign Step 2.5 + the new `plan_helper` subcommand.

#### Step B.5 — Verify

B.5.1 Run synthetic `/plan` against a spec rewritten with the new §7 kind taxonomy. Confirm Phase 1.5 findings emit the three-bucket shape.

B.5.2 Confirm plan table architecture row cites NFR + CBM-prior-art (Gap C) + constitution-anchor — does NOT cite an architecture pre-lock.

### Tradeoffs / argued

- **Re-baseline cost**: 4 fresh testForge20 runs to re-measure variance. Time: ~30 min/run = 2hr wall-clock. Worth it — old baseline doesn't apply.
- **Sequencing risk**: if A lands but Gap C does not, `/plan` has nothing to consult for architecture decisions and falls back to LLM guess. That's worse than today's pre-lock-in-spec scenario. **MUST land A + C together, or accept LLM-best-guess interim.**

### Out of scope (Gap B)

- `/breakdown` port (already out of scope per PLAN-COMMAND-REDESIGN-PLAN).
- Re-running variance against an OLDER spec shape (cse-strata 008 with `use`-kind constraints). Use new-shape fixture.

---

## Gap C — No empirical-memory consult in `/plan` for architecture decisions

### Evidence

`PLAN-COMMAND-REDESIGN-PLAN.md` has:

- **Phase 0 Patch 1**: Context7 binding (`mcp__context7__resolve-library-id` + `query-docs`) — external library docs. ✓
- **Phase 0 Patch 2**: research output rule — links to `research/*.md` files if present. ✓
- **No CBM consult phase** for prior `/plan` architecture decisions.

`src/commands/specify/main.md:403-410` exercises CBM (`search_graph` / `search_code` / `trace_path` / `get_code_snippet`) — but for **current code discovery** (what exists now), NOT **prior decision-history** (what architecture did we pick last time this intent class showed up).

`src/constitution.md §3.7` "Check Before You Build" says to search CBM for existing utilities — but addresses code-reuse, not architecture-decision-reuse.

CBM indexes:

- `File` nodes (file paths)
- `Function` / `Method` / `Class` nodes
- `Section` nodes (md heading-only granularity per memory `project_cbm_empirical_state_2026_05_09`)
- Call edges

CBM does NOT index:

- `specs/NNN-*/plan.md` content as queryable architecture decisions
- intent → architecture mappings
- prior NFR → architecture-choice rationales

### Severity

**MEDIUM-LOW**. Important for L3 maturity claim. But:

- Forge is young — `specs/` directory is empty/near-empty in most install targets. Empirical memory has nothing to consult yet.
- First N specs HAVE to guess architecture from constitution + LLM judgment. CBM consult adds value only after a corpus accumulates.
- Without Gap C, `/plan` still works — falls back to constitution + LLM. Just doesn't get Ahuja's "system answers from organizational history" value claim.

### Article principle violated

> "Context crafting — the decision layer is backed by empirical memory. Given this intent, under these constraints, with this organizational history — which architecture, which patterns, which tools? The system answers."

### Proposed fix

Two-stage approach. Stage 1 = cheap text-grep over prior plans (works today). Stage 2 = CBM-indexed plan metadata (future, deeper).

#### Stage 1 — Text-grep prior plans (immediate)

##### Step C.1.1 — New helper subcommand

`plan_helper consult-prior-plans <spec-type> <nfr-quantifiers>`:

- Glob `specs/*/plan.md` under install root.
- For each prior plan: parse the architecture-decision row, extract `(spec_type, nfr_summary, architecture_choice, outcome_marker)`.
- Filter prior plans by `spec_type` match.
- For each match: print one-line summary.

Example output:

```
Found 3 prior plans with spec_type=feature_addition:
  specs/003-add-export-jobs/plan.md — NFR: 1K daily exports, p95<5s — choice: queue-worker pattern (status: Complete)
  specs/007-add-tenant-filter/plan.md — NFR: 50K row scan, p95<300ms — choice: indexed lookup (status: Approved)
  specs/011-add-billing-export/plan.md — NFR: 10K daily, idempotent — choice: queue-worker pattern (status: Draft)

Recurrent choice: queue-worker pattern (2/3). Reuse candidate.
```

LLM consumes this in Phase 1 architecture decision, cites the prior plan if reusing.

##### Step C.1.2 — Spec text update

Add new Phase 1.x to `src/commands/plan/main.md` (when ported per PLAN-COMMAND-REDESIGN): "Phase 1.X — Prior-art consult." Single helper invocation. LLM emits one-line citation in plan table if reused.

##### Step C.1.3 — Plan output update

Architecture-decision row in plan table grows a `Prior-art: <ref>` column. If no match, `Prior-art: none (first of class).`

##### Step C.1.4 — Test-first

`tests/lib/test_plan_helper.py`: synthetic `specs/001-foo/plan.md` + `specs/002-bar/plan.md` with deterministic architecture-row shapes. `consult-prior-plans feature_addition` returns parsed summaries. Edge case: no prior plans → exit 0, empty summary block.

#### Stage 2 — CBM-indexed plan metadata (deferred)

Index plan-row metadata as graph nodes for richer query. Example: `query_graph("MATCH (p:PlanRow {spec_type:'feature_addition'}) WHERE p.nfr_user_count > 5000 RETURN p.architecture_choice")`. Defer until Stage 1 generates enough corpus to justify the indexing investment.

### Tradeoffs / argued

- **Stage 1 limitation**: text-grep is brittle — depends on plan.md format being stable. Mitigated by `plan_helper` being the sole writer of plan.md (helper-owns-shape extends to readers too).
- **First-plan problem**: on a fresh install with empty `specs/`, the consult returns empty. That's OK — LLM falls back to constitution + judgment. Same as today.
- **Cross-project memory**: prior plans across DIFFERENT install targets (e.g. testForge20's plans vs cse-strata's) are not consulted. Each install is its own corpus. Cross-corpus consult is a future story.
- **Alternative considered**: encode architecture-decision history in `.devforge/decisions.jsonl` append-only log. Rejected — duplicates plan.md content, syncs go stale. Better to make plan.md the single source.

### Verification

C-VERIFY-1: After 3 synthetic plans exist in `specs/`, run `/plan` against a 4th spec — confirm Phase 1.X surfaces the prior 3 in conversation before architecture row renders.

C-VERIFY-2: Confirm LLM cites prior-plan path in plan table's Prior-art column when reusing.

C-VERIFY-3: First-plan-of-class case: empty `specs/` + new spec → Phase 1.X reports "no prior art" without erroring.

### Out of scope (Gap C)

- Cross-project CBM consult (Stage 2 deferred).
- Outcome tracking (was the prior plan's choice validated by `/execute-task`? was it later reverted?). Plan-row has `Status: Draft|Approved|Complete` per existing flip mechanic — that's sufficient outcome marker for Stage 1.

---

## Gap D — Intent-kind dimension absent from spec-type classification (DEFER)

### Evidence

`src/commands/specify/main.md:343-356` enumerates 5 spec types:

- `migration_tooling`
- `feature_addition`
- `bug_fix`
- `refactor`
- `greenfield_feature`

Article distinguishes two intent kinds:

- **Consumer intent**: epics — "user wants red shoes, ₹3,000–5,000, eight-hour comfort"
- **Engineering intent**: plays — "commit code grouped by concern, follow conventional commits"

Forge's 5 types all sit on the **engineering-intent axis**. None capture consumer-intent epic-decomposition.

### Severity

**LOW for forge's current scope**.

### Argued — recommend SKIP

Reasoning:

1. Forge is a **dev-tools meta-framework**. Its consumers are engineers building dev tooling or shipping engineering features. Consumer-intent rarely surfaces at forge's framework level.
2. Forge's TARGET projects (where templates land — e.g. testForge20, cse-strata-ws-forge) ship internal-engineering features. Even those rarely express "consumer intent" in the article's sense (eCommerce feature design, marketplace flow).
3. Adding a 6th spec-type or a parallel `intent_kind` axis without a triggering use-case is YAGNI. Per memory `feedback_track_a_yagni_rollback`: *"Build for real consumers not speculative ones."* Track A rollback case study applies.
4. If a consumer-product-eng team adopts forge AND surfaces a real gap, revisit. Until then: the 5-type axis covers forge's actual consumers.

### What changes — NOTHING

No code change. Document the decision in this plan + memory for traceability.

### Trigger for revisit

If/when any of:

- A consumer-product team adopts forge and writes a `/specify` that doesn't fit any of the 5 types cleanly.
- The forge framework itself ships features whose intent class is consumer-facing (e.g. `/onboard` evolution if it ever becomes user-flow-shaped).
- Article gains broader adoption and consumer-intent axis becomes industry-standard vocabulary that forge users expect.

### Out of scope (Gap D)

Everything. This section exists to document the explicit defer.

---

## Gap E — Spec→code drift detection not active

### Evidence

`src/devforge/lib/cbm_sync_helper.py` (verified 2026-05-17):

- `write` — stamps `git_sha` (current repo HEAD) into `.devforge/cbm-stamp.json`.
- `check` — compares stamp to current HEAD. States: `current` / `missing` / `drift <a>..<b>`.
- **Scope**: whole-repo HEAD stamp. NOT per-spec.

No `spec.md` ↔ code-state binding exists. When `/specify` writes `specs/NNN-foo/spec.md` at HEAD `abc123`, then 3 months later HEAD is `xyz789`, there's no record that the spec was authored against `abc123`. The spec might still be relevant; it might be stale; it lies confidently either way.

Article's spec-dreamstate failure mode (Three-month rewrite story):

> "The spec had drifted — and a drifted spec is worse than no spec, because it lies with confidence. The system had forgotten what it was building, why, and how."

### Severity

**MEDIUM** (becomes HIGH at multi-month timescales). Today's specs are days/weeks old in forge's lifecycle. Article's failure mode hits at quarter+ timescales. Forge will hit this if framework outlives `develop-2.0-init` branch.

### Article principle violated

> "Memory isn't a feature. It's the prerequisite. … If you want to reach Level 4, the system needs to know where it's standing — not just what it was told to build on day one."

### Proposed fix

Extend `cbm_sync_helper` with per-spec stamping.

#### Step E.1 — Helper API extension

`cbm_sync_helper`:

E.1.1 New subcommands:

- `stamp-spec <spec-path>` — record `(spec_path, git_sha_at_write, cbm_index_version_at_write, timestamp_iso)` into `.devforge/spec-stamps.jsonl` (append-only).
- `check-spec <spec-path>` — return state token:
  - `current` if stamp's `git_sha` matches HEAD
  - `missing` if no stamp for this spec
  - `drift <a>..<b>` if stamp's `git_sha` differs from HEAD AND files-cited-by-spec changed since `<a>`
  - `current-but-stale-cbm` if `git_sha` matches but CBM index version differs (rare)

E.1.2 Drift detection logic for `check-spec`:

- Parse spec.md §4 Affected Areas table — extract `Files` column.
- For each file: `git log <stamp_sha>..HEAD -- <file>` — non-empty → file changed since spec write.
- If any cited file changed → emit `drift`.
- If no cited file changed → emit `current` even if HEAD advanced.

E.1.3 **Known limitation disclosure** (Risk 4 from 2026-05-17 audit):

> **Drift detection precision = §4 Affected Areas completeness ceiling.** If the spec author misses a file in §4, drift on that file is silent — the spec lies with confidence, exactly the failure mode this gate was meant to catch, just shifted from §7 (closed by Gap A) to §4.
>
> Why we accept this:
> 1. `/breakdown` already pressures §4 completeness for task partitioning. Same pressure benefits drift detection.
> 2. Auto-discovering full file set at stamp time requires CBM `trace_path` expansion (depth-N walk from §4-cited files) — imperfect (misses runtime-loaded paths, dynamic imports) AND adds index-dependency at stamp time.
> 3. Better to ship Stage 1 + measure real-world miss rate than over-engineer Stage 1.
>
> Stage 2 mitigation (deferred): at `stamp-spec` write, run `trace_path mode=calls direction=outbound depth=1` on each §4-cited file → expand recorded cited set. Defer until empirical miss-rate justifies cost.
>
> Document this limitation in `/specify` Phase 4 spec text (Step E.2) so spec authors know §4 completeness is load-bearing for drift detection, not just task partitioning.

#### Step E.2 — Wire into `/specify` Phase 4

After spec.md render + save (Step 4.10), call `cbm_sync_helper stamp-spec <spec-path>`. Single line addition.

#### Step E.3 — Wire into `/plan` Phase 0

`/plan` Phase 0a (spec resolution per PLAN-COMMAND-REDESIGN Step 3.1) — after `pick-spec`, call `cbm_sync_helper check-spec <picked-path>`:

- `current` → proceed silently.
- `missing` → surface to user: "Spec has no drift stamp. Proceeding without baseline."
- `drift <a>..<b>` → emit warning block citing changed files; ask user "spec may be stale — proceed / re-specify / cancel?"

#### Step E.4 — Wire into `/execute-task` entry

Same `check-spec` invocation as Step E.3. Warn on drift before any code change.

#### Step E.5 — Test-first

`tests/lib/test_cbm_sync_helper.py`:

- `test_stamp_spec_round_trip` — stamp then check returns `current`.
- `test_check_spec_drift_when_cited_file_changes` — stamp, mutate a cited file, commit, check returns `drift`.
- `test_check_spec_clean_when_unrelated_file_changes` — stamp, mutate an unrelated file, commit, check returns `current`.
- `test_check_spec_missing_for_unstamped_spec` — returns `missing`.

#### Step E.6 — Dual-agent review

Wire-in points (specify Phase 4, plan Phase 0a, execute-task entry) all need spec-text updates. `instruction-author` + `instruction-reviewer` + `claude-code-guide` per `feedback_dual_agent_verify_command_statements`.

#### Step E.7 — Cross-check

`grep -rn "cbm-stamp\|cbm_sync_helper" src/` — confirm existing `cbm_sync_helper` repo-HEAD stamp behavior still works (do not regress).

Memory entries `project_cbm_sync_delivered.md` flags "empirical drift-test against git-tracked target still pending" — the new per-spec drift IS that test substrate. Update memory after delivery.

### Verification

E-VERIFY-1: Synthetic spec at HEAD `A`, mutate cited file, commit at HEAD `B`, run `/plan` → warns about drift, names changed files.

E-VERIFY-2: Synthetic spec at HEAD `A`, mutate unrelated file, commit at HEAD `B`, run `/plan` → no warning.

E-VERIFY-3: Spec without stamp (legacy/pre-E.2 spec) — `check-spec` returns `missing`, `/plan` notes baseline absence and proceeds.

### Tradeoffs / argued

- **Append-only log growth**: `.devforge/spec-stamps.jsonl` grows with each `/specify` invocation. ~200 bytes/line. 1000 specs = 200KB. Negligible.
- **Cited-file accuracy**: relies on spec §4 Affected Areas being complete. If spec misses a file in §4, drift on that file is invisible. Acceptable — §4 already governs `/breakdown` task partitioning, so completeness pressure exists.
- **CBM index version coupling**: optional. Stage 1 = git_sha only. Stage 2 = also track CBM index version. Defer Stage 2 until index drift becomes a visible issue.
- **Alternative considered**: embed `**Stamp**: <sha>` in spec.md frontmatter directly. Rejected — pollutes the spec document with bookkeeping. Sidecar `.jsonl` is cleaner.

### Out of scope (Gap E)

- Auto-rewriting drifted specs. User decision.
- Stamping `plan.md` similarly. Future plan — same pattern applies but separate change.
- CBM-index-version tracking (Stage 2 deferred).

---

## Sequencing summary

| Order | Gap | Blocker | Effort | Value |
|---|---|---|---|---|
| 1 | A — §7 kind split | none | M (helper + spec + tests + dual-agent review) | HIGH — load-bearing on every spec |
| 2 | B — `/plan` redesign inherits A | needs A | S (mostly inheritance + plan helper update) | MEDIUM — depends on A |
| 3 | C — CBM prior-plan consult | needs B (lands inside /plan redesign) | M (new helper subcommand + spec phase + tests) | MEDIUM-LOW — value grows with corpus |
| 4 | E — per-spec drift stamp | independent (any time) | M (helper extension + 3 wire-in points + tests) | MEDIUM, growing |
| – | D — intent-kind | DEFER | – | LOW |

**Recommended interleaving**: A → B+C bundled (since both land in `/plan` redesign) → E. Total: ~3 small plans worth of work or 1 medium plan. Could merge into PLAN-COMMAND-REDESIGN-PLAN as Steps 7–9 if user wants a single integration plan.

## When resuming work

1. Read this plan top-to-bottom.
2. Check `git status` on `develop-2.0-init` for in-flight work.
3. Confirm `PLAN-COMMAND-REDESIGN-PLAN.md` Step 6 (parity 4-run gate) is still open OR landed — Gap B's re-baseline decision (Step B.3.2) depends on this.
4. Confirm `RESEARCH-HELPER-API-ENUM-PLAN.md` is closed (research-helper Patches 1–4 already shipped per recent commits).
5. Confirm `CONSTITUTION-STRENGTHENING-PLAN.md` patches are applied — Gap A's `constitution_anchor` kind validates against `constitution.md`, so constitution must be stable.
6. Start at Gap A Step A.1.

## Out of scope (this plan)

- L3 maturity jump: split `intent.md` / `spec.md` / `plan.md` into 3 separate artefact files. Too big for one cycle.
- L4 / L5 maturity work (autonomous reasoning, dark factory). Aspirational.
- Cross-project CBM consult (Stage 2 of Gap C).
- Article's Four Crafts → P-CAM mapping. Architectural fit confirmed; no code change required.
- Renaming `/specify` Phase 4.6 §7 heading. Render-label changes sufficient.

## Memory updates

After delivery, write memory entries:

- `feedback_specify_section7_kind_taxonomy.md` — new `nfr` / `constitution_anchor` / `external_system` kinds; `use` removed; rationale (Three-Layer-Separation article).
- `project_three_layer_separation_delivered.md` — what shipped, what deferred (Gap D), what's next (L3 future).
- Update `project_cbm_sync_delivered.md` — note per-spec drift now active (Gap E).

## Notes on the article itself

Article's central claim (spec-driven collapses without three-layer separation) holds against forge's current state. Article's confessions (author at L2.5–2.75; "we still make pre-lock decisions at prepare-time that a truly Level 3 system would resolve at implement-time") describe forge's state verbatim. The article does NOT change forge's strategic direction — it validates and accelerates the trajectory already encoded in CBM, helper-owns-shape, constitution patches, and research-helper gates. This plan is a delta against that trajectory, not a pivot.

Article's weakness for forge: it speaks to product-engineering teams. Forge is meta-tooling for engineering teams. Article's "consumer intent" axis (Gap D) doesn't apply at forge's scope — recommended defer is the correct response, not a capitulation.
