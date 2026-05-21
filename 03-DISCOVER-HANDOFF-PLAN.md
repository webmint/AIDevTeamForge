# DISCOVER-HANDOFF-PLAN

**Status**: IN-FLIGHT 2026-05-20. Steps 1+3+4+5+6+7 SHIPPED on `develop-2.0-init` (commits `895eb80` schema, `067c09d` finalize+append-outcome, `8e4c8e9` specify+research kind-dispatch). Step 2 N/A (research-side reuse). Step 8 = manual testForge20 e2e pending. 786 tests pass + 2 skipped + 13 subtests. Iterative review loops all clean (Step 1: 2 iters 5→1→0; Step 3+5: 2 iters 5→2→0; Step 4+6: 2 iters 4→0).
**Date**: 2026-05-19 (drafted) / 2026-05-20 (path-fix revision + 6-of-8 steps shipped)
**Branch**: `develop-2.0-init`
**Owner**: orchestrator (Claude) + user
**Driver**: Parallel of RESEARCH-HANDOFF-PLAN for the greenfield-feature track. `/discover` produces a structurally rich report (8-dim memo + prior-art + fit-assessment + 2-3 design options + build-vs-buy + derisk plan + verdict) that today hands off to `/specify` via the same manual paste-block bridge `/research` uses. Same two structural gaps apply: (1) ~90% of memo+report content is lost across the command boundary; (2) verdict + recommended-option speculation is never marked against what actually shipped. This plan introduces a helper-owned `<topic-slug>.handoff.json` artefact for `/discover` that bridges into the same `specify_helper import-handoff` infra introduced by RESEARCH-HANDOFF, plus a discover-shaped outcome marker (design-option-shipped + build-vs-buy-actual + internal-extension-followed).

## Context for next session

Current pipeline:

```
Feature idea  →  /discover  →  [manual paste 4-of-~30 fields]  →  /specify  →  /plan  →  /execute-task
```

Failure modes (isomorphic to research-side, content differs):

1. **Manual handoff loss** — `/discover` produces a ScopingMemo (8 dimensions × {value, state, turns} = 24 fields + references + gaps + conflicts) plus a DiscoveryReport (~20 structured fields: prior_art[], integration_touchpoints[], fit_assessments[], overall_fit, effort_estimate, fit_rationale, design_options[], recommended_option, build_vs_buy, derisk_plan[], constitution_constraints[], verdict, recommendation, next_step_text). Today's Phase 4 emits only the `## Next Step` block (topic + verdict + 3-4 key facts). `/specify` re-derives spec-relevant fields from prose. Re-derivation = drift across command boundary.

2. **Discovery outcome unmarked** — `/discover` ends with verdict ∈ {`Worth pursuing`, `Promising with caveats`, `Reconsider`} + a recommended design option (A/B/C). Nowhere captures which option actually shipped, whether build-vs-buy recommendation held, whether internal canonical-pattern extension (invariant G) was followed, or how reality differed from the recommended path. Future LLM reads stale discovery reports, treats speculation and validated equally. Empirical-memory corpus = corrupt by indistinction (same problem as research, different content).

3. **Internal canonical-pattern findings discarded** — Step 2.0 of `/discover` enumerates `internal:<path>` prior-art entries representing existing implementations of the requested capability. Invariant G forces `recommended_option.rationale` to cite at least one of them when present. Today this signal dies at the report render boundary. `/specify` cannot pre-seed `affected_areas` from those internal hits, so the spec author re-discovers them.

### What this plan ships

Single helper-owned artefact `discover/<date>-<topic-slug>.handoff.json` (sibling-file form alongside the existing flat `discover/<date>-<topic-slug>.md` — no directory restructure) carrying:

- **Intent block** — feature concept + topic + scope (greenfield reformulation of research's symptom/desired pair)
- **Spec seeds** — constraints (post-Gap-A kind taxonomy) + affected areas (seeded from `integration_touchpoints` + `internal:<path>` prior-art) + risks (lifted from derisk plan) + open questions (lifted from `open_uncertainties` + `gaps[]`)
- **Plan seeds** — recommended_option + design_options + build_vs_buy + complexity + cited canonical patterns (both internal + external from prior_art)
- **Discovery-specific** — overall_fit + effort_estimate + verdict + memo dimensions (preserved verbatim for downstream auditability)
- **Outcome block** — null until feature ships; filled by `append-outcome` subcommand with design-option-shipped + build-vs-buy-actual + internal-extension-followed signals
- **Downstream links** — back-references filled by /specify, /plan, /execute-task as pipeline progresses

Helper subcommands write + read; LLM never edits handoff.json directly. Validators are discover-shaped, NOT research-shaped — no probe-tier, no test_infra, no literal_archaeology, no data_flow_chain (those are research-bug-mode artefacts).

### Dependencies on RESEARCH-HANDOFF-PLAN

Per actual research-side state inspected 2026-05-20: **Steps 1+2+3+4+5+6+7+9 ALL SHIPPED + COMMITTED; Step 8 DEFERRED (no `/execute-task` command exists); Step 10 = manual testForge20 verification.** Helper splits also shipped: `research_helper` → `_research/` subpackage (18 files), `specify_helper` → `_specify/` subpackage (11 files), both with thin shims at original paths.

| Dependency | Status | Why required |
|---|---|---|
| RESEARCH-HANDOFF Step 1 (handoff_schema dataclass module) | **SHIPPED** commit `6a0c2d1` — `src/devforge/lib/_research/handoff_schema.py` (41.2K, ~20 dataclasses, `__post_init__` validators, module-level `compute_confidence_grade()`) + `tests/lib/test_research_handoff_schema.py` (36.2K) | Pattern source. Discover Step 1 mirrors the dataclass shape (NOT pydantic, NOT jsonschema). Schema module is I/O-free; no `to_dict` / `from_dict`; validation mechanical. CLI handler does I/O in `_discover/_cmds_handoff.py`. |
| RESEARCH-HANDOFF Step 3 (`research_helper finalize-handoff`) | **SHIPPED** commit `916642d` — registered in `_research/_cli.py:205`, body in `_research/_cmds_handoff.py` (12.4K), state→dataclass mapping in `_research/_handoff_build.py` (19.9K) | Pattern source for discover Step 3 CLI + builder split. Discover-side mirrors the three-file split (`_cli.py` parser entry / `_cmds_handoff.py` handler / `_handoff_build.py` mapper). |
| RESEARCH-HANDOFF Step 6 (`specify_helper import-handoff` + Phase 0.4 discovery) | **SHIPPED** commit `ccbd2db` — `_specify/_cli.py:584` (import-handoff) + `_specify/_cli.py:594` (find-handoffs); body in `_specify/_cmds_handoff.py` (17.1K) | This plan's Step 4 extends `_specify/_cmds_handoff.py` to dispatch on `handoff_kind` + glob `discover/*.handoff.json`. |
| RESEARCH-HANDOFF Step 7 (`append-outcome` + `check-outcome`) | **SHIPPED** commit `1191805` — registered in `_research/_cli.py:692` + `_research/_cli.py:723`, body in `_research/_cmds_handoff.py` | Pattern source for discover Step 5 append-outcome + Step 6 check-outcome kind-dispatch extension. |
| RESEARCH-HANDOFF Step 8 (`/execute-task` outcome reminder wire-in) | **DEFERRED** (no `/execute-task` command exists) | Discover Step 6 inherits same posture: ship helper-side `check-outcome` kind-dispatch NOW; defer `/execute-task` wire-in until that command lands. |
| RESEARCH-HANDOFF Step 10 (testForge20 e2e procedure) | Manual verification posture | This plan's Step 8 mirrors the manual procedure with `/research`→`/discover` substitution. |
| THREE-LAYER Gap A (`--kind` taxonomy split) | `spec_seeds.constraints[].kind` enum uses `nfr` / `constitution_anchor` / `external_system`. Same as research-side. Already shipped 2026-05-18. |
| COMMAND-VERIFY-GATES Step 2 (`init_helper verify`) | Pre-existing dep for the install-chain gate `/discover` Phase 0.1 already checks. Already shipped 2026-05-18. |
| COMMAND-VERIFY-GATES Step 3 (`specify verify-rendered`) | Same as research-side — `import-handoff` mutates state pre-render. Already shipped 2026-05-18. |

**No V2/V3 dependency** — V2 patches (data_flow_chain, value_semantics, value_production_sites) and V3 patches (literal_archaeology, proposed_call_shape) are research-bug-mode framing fixes for presentation-layer↔domain-layer drift. Greenfield discovery has no symptom file, no value-comparison failure, no literal-replacement pattern, no hypothesis-vs-reality gap of the same shape. Schema does NOT absorb V2/V3 fields.

**No probe-tier dependency** — `/discover` has no probe block. Verification of design-option fit is post-shipment (outcome marker), not pre-shipment (probe).

**No test_infra dependency** — `init_helper test_infra` detection (RESEARCH-HANDOFF Step 2) feeds probe-tier selection. Not consumed by discover schema.

### Sequencing rule

**All research-side dependencies SHIPPED.** Discover Steps 1-8 may execute in linear order with no external gates remaining. Internal dependencies within this plan:

- Step 1 (schema) — first; nothing depends on inputs from other steps
- Step 3 (finalize-handoff) — depends on Step 1
- Step 4 (specify extension) — depends on Step 1 (reads schema)
- Step 5 (append-outcome) — depends on Step 1 + Step 3 (handoff file must exist before outcome appended)
- Step 6 (check-outcome kind-dispatch) — depends on Step 1 (reads handoff_kind); `/execute-task` wire-in DEFERRED per research Step 8 posture
- Step 7 (cross-grep) — bookkeeping; runs after Steps 1-6
- Step 8 (e2e testForge20) — runs last; requires Steps 1-6 shipped

Phase 0 confirms shipped-state of research-side deps before Step 1 starts.

---

## Phase 0 — Pre-flight (5 min)

0.1 Verify research-side shipped + helper splits in place:

```bash
cd /Users/mykolakudlyk/Projects/ai-dev-team-forge

# Schema source pattern (Step 1):
ls src/devforge/lib/_research/handoff_schema.py
grep -nE '^class (Intent|SpecSeeds|PlanSeeds|Outcome|Handoff)' src/devforge/lib/_research/handoff_schema.py
grep -nE 'def compute_confidence_grade' src/devforge/lib/_research/handoff_schema.py

# finalize-handoff + builder split (Step 3 pattern source):
ls src/devforge/lib/_research/_cmds_handoff.py src/devforge/lib/_research/_handoff_build.py
grep -nE '"finalize-handoff"' src/devforge/lib/_research/_cli.py

# specify import-handoff + find-handoffs (Step 4 edit target):
ls src/devforge/lib/_specify/_cmds_handoff.py
grep -nE '"import-handoff"|"find-handoffs"' src/devforge/lib/_specify/_cli.py
grep -nE 'Phase 0\.4' src/commands/specify/main.md

# append-outcome + check-outcome (Step 5+6 pattern source / edit target):
grep -nE '"append-outcome"|"check-outcome"' src/devforge/lib/_research/_cli.py

# discover subpackage present (Step 1+3+5 edit target):
ls src/devforge/lib/_discover/_cli.py src/devforge/lib/_discover/_state.py
```

All ≥1 hit → proceed. Any miss → research-side regression OR helper-split unexpected revert; investigate before continuing.

0.2 Verify Gap A + COMMAND-VERIFY-GATES still in place:

```bash
grep -nE 'kind.*nfr.*constitution_anchor' src/devforge/lib/_specify/
grep -nE 'add_parser\("verify"' src/devforge/lib/init_helper.py
grep -nE '"verify-rendered"' src/devforge/lib/_specify/_cli.py
```

All ≥1 hit → proceed.

0.3 Confirm test fixture: `testForge20` has at least one `discover/` directory with output from a current `/discover` run (post-Step-2.0 internal-canonical-pattern era). If empty: run a synthetic `/discover` against any greenfield-feature topic in testForge20 whose verb hits an existing testForge20 implementation (otherwise invariant G is no-op and the fixture won't exercise the cite-back validator).

0.2 Verify Gap A + COMMAND-VERIFY-GATES still in place:

```bash
grep -nE 'kind.*nfr.*constitution_anchor' src/devforge/lib/specify_helper.py       # Gap A
grep -nE 'add_parser\("verify"' src/devforge/lib/init_helper.py                    # CVG Step 2
grep -nE '"verify-rendered"' src/devforge/lib/specify_helper.py                    # CVG Step 3
```

All ≥1 hit → proceed.

0.3 Confirm test fixture: `testForge20` has at least one `discover/` directory with output from a current `/discover` run (post-Step-2.0 internal-canonical-pattern era). If empty: run a synthetic `/discover` against any greenfield-feature topic in testForge20 to seed first fixture with `internal:<path>` prior-art populated (use a feature whose verb hits an existing testForge20 implementation, otherwise invariant G is no-op and the fixture won't exercise the cite-back validator).

---

## Step 1 — Lock `<topic-slug>.handoff.json` schema

**Owner**: python-engineer + instruction-author.

### Implementation pattern (LOCKED — mirrors research-side)

Per inspection of `src/devforge/lib/_research/handoff_schema.py` (landed untracked 2026-05-19):

- **Dataclasses only.** No pydantic. No jsonschema. `from dataclasses import dataclass, field`.
- **Pure records.** No `to_dict` / `from_dict`. No serialization. No I/O. No render logic. Schema module imports are limited to stdlib (`dataclasses`, `typing`, `datetime`, `re`).
- **Validation in `__post_init__`.** Mechanical only — required string fields non-empty after `.strip()`, enums via `_require_in_enum`, conditional requireds checked field-by-field.
- **Module-level helper functions** for cross-field checks (mirror research-side `_require_nonempty`, `_require_in_enum`; add discover-specific predicates as needed for D-mirror + G-mirror invariants).
- **Module-level `compute_confidence_grade(...)` function** (matches research Outcome convention). NOT a method on `Outcome`.
- **CLI handler owns I/O** in `src/devforge/lib/_discover/_cli.py` — read JSON file → instantiate dataclass (raises ValueError on schema violation) → mutate → write JSON file.

### Files

- `src/devforge/lib/_discover/handoff_schema.py` (new) — dataclass schema module per pattern above. Single source of truth for discover-side shape.
- `tests/lib/test_discover_handoff_schema.py` (new) — schema validation tests; round-trip via real `/discover` state.

### Class roster (matches schema JSON structure below)

```
Intent                          (matches research Intent shape — different fields)
Constraint                      (Gap A taxonomy; identical to research)
AffectedArea                    (adds is_internal_extension_candidate flag vs research)
Risk                            (identical to research)
OpenQuestion                    (identical to research)
DimensionRecord                 (NEW — per-dimension {value, state, turns} record)
SpecSeeds                       (different content from research SpecSeeds — no V2/V3 fields)
DesignOption                    (NEW — discover-specific)
BuildVsBuy                      (NEW — discover-specific)
CitedPattern                    (adds is_internal flag vs research CitedPattern)
Complexity                      (identical enum to research, different derivation source)
PlanSeeds                       (different content from research PlanSeeds — design_options/build_vs_buy instead of probe)
FitAssessment                   (NEW — discover-specific)
DiscoveryBlock                  (NEW — wraps verdict + overall_fit + fit_assessments + memo_dimensions + references + gaps)
Outcome                         (different fields from research Outcome — design-shipped vs hypothesis-confirmed)
DownstreamLinks                 (identical to research)
Handoff                         (top-level; handoff_kind = "discover" constant)
```

Module-level predicates (mirror research pattern):

```
_require_nonempty(value, field_name)
_require_in_enum(value, allowed, field_name)
_has_internal_prior_art(cited_patterns)         — true when any CitedPattern.is_internal
_rationale_cites_internal(rationale, patterns)  — G-mirror check
_is_strained_or_misfit(overall_fit, effort)     — D-mirror gating predicate
_compute_complexity_changes(effort_estimate)    — deterministic mapping
_compute_complexity_risk(overall_fit)           — deterministic mapping
_compute_complexity_verify_cost(derisk_count)   — deterministic mapping

compute_confidence_grade(
    verdict_held,
    matches_recommendation,
    matches_build_vs_buy_recommendation,
    internal_extension_followed,
)
```

### Schema

```json
{
  "schema_version": "1.0",
  "handoff_kind": "discover",
  "report_path": "discover/2026-05-19-audit-log-persistence.md",
  "discover_completed_at": "2026-05-19T14:32:00Z",

  "intent": {
    "feature_concept": "string (required) — 1-2 sentence concept lifted from memo.dimensions.functional_scope.value, LLM-distilled to ≤200 chars",
    "topic": "string (required) — verbatim memo.topic",
    "topic_slug": "string (required) — verbatim memo.topic_slug",
    "scope_summary": "string — concise paraphrase of memo.dimensions.functional_scope.value (full text preserved in discovery_block.memo_dimensions)"
  },

  "spec_seeds": {
    "spec_type_hint": "greenfield_feature (constant — /discover always pre-seeds greenfield_feature per /specify Phase 3 path table)",
    "constraints": [
      {
        "_source": "lifted from memo.dimensions.constraints.value + memo.dimensions.non_goals.value + report.constitution_constraints[*]",
        "kind": "nfr | constitution_anchor | external_system",
        "content": "string",
        "quantifier": "string (required when kind=nfr)",
        "constitution_ref": "string (required when kind=constitution_anchor; populated from report.constitution_constraints[*].rule)",
        "protocol": "string (required when kind=external_system, OR contract_doc_ref)",
        "contract_doc_ref": "string (required when kind=external_system, OR protocol)"
      }
    ],
    "affected_areas": [
      {
        "_source": "lifted from report.integration_touchpoints[*] + the subset of report.prior_art[*] whose source starts with 'internal:'",
        "area": "string (touchpoint.name OR prior_art.reference)",
        "files": ["path:line OR path (touchpoint.module_path OR internal:<path> stripped of prefix)"],
        "impact": "string (touchpoint.reason OR 'existing implementation — extension candidate per invariant G')",
        "is_internal_extension_candidate": "bool (true when sourced from internal:<path> prior_art; downstream cite-rule hook)"
      }
    ],
    "risks": [
      {
        "_source": "lifted from report.derisk_plan[*] (each derisk item rephrased as a risk to mitigate) + fit_assessments[*].blockers[*]",
        "risk": "string",
        "likelihood": "Low | Med | High",
        "impact": "Low | Med | High",
        "mitigation": "string (verbatim derisk_plan item when sourced from derisk_plan)"
      }
    ],
    "open_questions": [
      {
        "_source": "lifted from report.open_uncertainties[*] + memo.gaps[*]",
        "question": "string",
        "blocking": "bool"
      }
    ]
  },

  "plan_seeds": {
    "recommended_option_id": "string (matches one of design_options[*].id)",
    "recommended_option_rationale": "string (verbatim report.recommended_option.rationale)",
    "design_options": [
      {
        "_source": "verbatim report.design_options[*]; helper auto-assigns id = A|B|C... per insertion order, matching render letter-prefix",
        "id": "A | B | C | ...",
        "name": "string (verbatim design_options[*].name; no letter prefix per existing setter validator)",
        "shape": "string (1-3 sentences from design_options[*].shape)",
        "pros": ["string"],
        "cons": ["string"],
        "complexity": "Low | Med | High"
      }
    ],
    "build_vs_buy": {
      "_source": "verbatim report.build_vs_buy",
      "recommendation": "Build | Buy | Hybrid",
      "build_path": "string (verbatim build_vs_buy.build)",
      "buy_path": "string (verbatim build_vs_buy.buy)",
      "reasoning": "string (verbatim build_vs_buy.reasoning)"
    },
    "cited_canonical_patterns": [
      {
        "_source": "report.prior_art[*] — both external (library/product/pattern) and internal (internal:<path>) entries flow here; downstream /plan can split by source-prefix",
        "reference": "string (prior_art.reference)",
        "kind": "library | product | pattern",
        "source": "string (URL, context7-id, OR internal:<path>)",
        "relevance": "string (prior_art.relevance)",
        "is_internal": "bool (true when source starts with 'internal:')"
      }
    ],
    "complexity": {
      "_source": "report.effort_estimate maps to changes axis; risk axis derived from overall_fit; verify_cost axis derived from len(derisk_plan)",
      "changes": "Low | Med | High (mapped: 'Low'→'Low', 'Medium'→'Med', 'High'→'High', 'Major refactor required'→'High')",
      "risk": "Low | Med | High (mapped: 'Good'→'Low', 'Acceptable'→'Med', 'Strained'→'High', 'Misfit'→'High')",
      "verify_cost": "Low | Med | High (derived: <=2 derisk items→'Low'; 3-5→'Med'; >5→'High')"
    }
  },

  "discovery_block": {
    "_purpose": "discover-only fields preserved for downstream auditability + outcome-marker reference; not consumed by /specify import seeding directly",
    "overall_fit": "Good | Acceptable | Strained | Misfit",
    "effort_estimate": "Low | Medium | High | Major refactor required",
    "fit_rationale": "string (verbatim report.fit_rationale)",
    "fit_assessments": [
      {
        "touchpoint": "string",
        "user_expected": "string",
        "reality": "string",
        "effort": "Low | Medium | High | Major refactor required",
        "blockers": ["string"]
      }
    ],
    "verdict": "Worth pursuing | Promising with caveats | Reconsider",
    "override_recorded": "bool (verbatim memo.override_recorded — captures whether scope-finalize --accept-gaps was used; downstream verdict-flip audit trail)",
    "memo_dimensions": {
      "_purpose": "verbatim memo.dimensions preserved so future /specify or audit can re-read original 8-dim scoping context without round-tripping through prose",
      "functional_scope": {"value": "string|null", "state": "Clear|Partial|Missing", "turns": "int"},
      "users": {"value": "string|null", "state": "Clear|Partial|Missing", "turns": "int"},
      "inputs_outputs": {"value": "string|null", "state": "Clear|Partial|Missing", "turns": "int"},
      "integration_points": {"value": "string|null", "state": "Clear|Partial|Missing", "turns": "int"},
      "constraints": {"value": "string|null", "state": "Clear|Partial|Missing", "turns": "int"},
      "non_goals": {"value": "string|null", "state": "Clear|Partial|Missing", "turns": "int"},
      "success_criteria": {"value": "string|null", "state": "Clear|Partial|Missing", "turns": "int"},
      "edge_cases": {"value": "string|null", "state": "Clear|Partial|Missing", "turns": "int"}
    },
    "references": ["string (verbatim memo.references)"],
    "gaps": [
      {"dimension": "string (underscore form)", "description": "string"}
    ]
  },

  "outcome": null,

  "downstream_links": {
    "spec_path": "specs/NNN-<feature>/spec.md | null",
    "plan_path": "specs/NNN-<feature>/plan.md | null",
    "execute_task_commit_shas": []
  }
}
```

**Outcome block shape** (filled by `append-outcome`):

```json
"outcome": {
  "design_option_shipped_id": "A | B | C | hybrid | none — which design_options[*].id was actually built; 'hybrid' when the shipped shape combines >1 option; 'none' when feature was abandoned post-discovery",
  "design_option_shipped_summary": "string (1-3 sentences describing what actually shipped — may differ from recommended_option even when ids match)",
  "matches_recommendation": "bool (design_option_shipped_id == plan_seeds.recommended_option_id)",
  "build_vs_buy_actual": "Build | Buy | Hybrid | none",
  "matches_build_vs_buy_recommendation": "bool (build_vs_buy_actual == plan_seeds.build_vs_buy.recommendation)",
  "internal_extension_followed": "bool | null — null when no internal:<path> prior_art existed; true when spec_seeds.affected_areas[*].is_internal_extension_candidate was actually extended (cited in shipped commit messages OR file diffs touch the cited path); false when fresh-build despite invariant G cite",
  "delta_from_recommendation": "string | null — narrative of how shipped path diverged; null when matches_recommendation AND matches_build_vs_buy_recommendation AND (internal_extension_followed in {true, null})",
  "verdict_held": "bool — false when discover verdict was 'Reconsider' but feature shipped anyway (override happened post-discovery), OR verdict was 'Worth pursuing' or 'Promising with caveats' but feature was abandoned (design_option_shipped_id == 'none')",
  "shipped_commit_sha": "string | null (final feature commit SHA from /finalize)",
  "shipped_date": "ISO-8601",
  "confidence_grade": "HIGH | MEDIUM | LOW (derived from tuple — see Step 5 validator)"
}
```

### Validators

- All `required` fields enforced.
- `handoff_kind == "discover"` constant; reject if anything else.
- `spec_seeds.spec_type_hint == "greenfield_feature"` constant (locked because /discover always seeds greenfield path; verify with helper-side equality check).
- `spec_seeds.constraints[*].kind` ∈ Gap A taxonomy (`nfr | constitution_anchor | external_system`); conditional requireds match Gap A spec.
- `plan_seeds.design_options[]` length ≥ 1 when `discovery_block.verdict` ∈ `{Worth pursuing, Promising with caveats}`; may be empty when verdict is `Reconsider`.
- `plan_seeds.recommended_option_id` MUST match an existing `design_options[*].id` when `verdict` ∈ `{Worth pursuing, Promising with caveats}`; may be null when verdict is `Reconsider`.
- `plan_seeds.design_options[*].id` ∈ `A | B | C | D | E | F | G | H` (helper auto-assigns; 8-cap matches realistic ceiling for design alternatives in a single discovery cycle).
- `plan_seeds.design_options[*].id` distinct (no duplicate letter ids).
- `plan_seeds.design_options[*].complexity` ∈ `{Low, Med, High}` (matches existing setter enum; note `Med` not `Medium`).
- `plan_seeds.build_vs_buy.recommendation` ∈ `{Build, Buy, Hybrid}`.
- `plan_seeds.cited_canonical_patterns[*].is_internal == true` ↔ `source` starts with `internal:` (helper-validated equivalence).
- `plan_seeds.complexity` axis derivations are deterministic — helper computes from source fields, rejects manually-set values that don't match derivation.
- `discovery_block.overall_fit` ∈ `{Good, Acceptable, Strained, Misfit}`.
- `discovery_block.effort_estimate` ∈ `{Low, Medium, High, "Major refactor required"}` (note: `Medium` here, mapped to `Med` for `plan_seeds.complexity.changes`).
- `discovery_block.verdict` ∈ `{Worth pursuing, Promising with caveats, Reconsider}`.
- **Verdict-flip carry-through validator (D-mirror)** — when `discovery_block.overall_fit` ∈ `{Strained, Misfit}` OR `discovery_block.effort_estimate == "Major refactor required"`, the source `/discover` invocation MUST have set `discovery_block.verdict == "Reconsider"` UNLESS `discovery_block.override_recorded == true`. Helper rejects schemas violating this — same rule as `/discover` invariant D, replicated at handoff level to catch schema drift between source state and handoff write.
- **Internal-extension cite carry-through (G-mirror)** — when any `plan_seeds.cited_canonical_patterns[*].is_internal == true`, `plan_seeds.recommended_option_rationale` MUST contain at least one of those `internal:` paths as a substring. Mirror of `/discover` invariant G; replicated at handoff level.
- **Outcome validators** (when `outcome != null`):
  - `outcome.design_option_shipped_id` ∈ `{A, B, C, D, E, F, G, H, hybrid, none}`.
  - `outcome.matches_recommendation` is helper-computed (not user-set); reject manual override that doesn't match computation.
  - `outcome.build_vs_buy_actual` ∈ `{Build, Buy, Hybrid, none}`; `matches_build_vs_buy_recommendation` helper-computed.
  - `outcome.internal_extension_followed`: when `plan_seeds.cited_canonical_patterns[*].is_internal` has no true entries, MUST be null; otherwise MUST be true or false.
  - `outcome.delta_from_recommendation` MUST be non-null when ANY of (`matches_recommendation == false`, `matches_build_vs_buy_recommendation == false`, `internal_extension_followed == false`).
  - `outcome.verdict_held` is helper-computed from `(discovery_block.verdict, design_option_shipped_id, shipped_commit_sha)` — `false` when verdict was `Reconsider` and `shipped_commit_sha != null`, OR when verdict was `Worth pursuing` or `Promising with caveats` and `design_option_shipped_id == "none"` (both proceeding-verdicts imply intent-to-ship; abandonment of either signals verdict-not-held).
  - `outcome.confidence_grade` derivation:
    - `verdict_held == true` AND `matches_recommendation == true` AND `matches_build_vs_buy_recommendation == true` AND `internal_extension_followed in {true, null}` → HIGH
    - `verdict_held == true` AND any one of the three match flags is false → MEDIUM (recommendation diverged but verdict held)
    - `verdict_held == false` → LOW (discovery framing was wrong)

### Verify

```bash
pytest tests/lib/test_discover_handoff_schema.py -v
# Cases:
#   - valid_handoff_full_worth_pursuing — happy path with 3 design options + internal prior_art + recommended_option cites internal path
#   - valid_handoff_reconsider_verdict — verdict=Reconsider, design_options may be empty, recommended_option may be null
#   - valid_handoff_override_recorded — strained fit BUT override_recorded=true permits non-Reconsider verdict
#   - reject_handoff_kind_not_discover — handoff_kind != "discover" rejected
#   - reject_spec_type_hint_other_than_greenfield_feature
#   - reject_design_option_letter_prefix_in_name — matches existing setter rule
#   - reject_duplicate_design_option_ids
#   - reject_recommended_option_id_not_in_design_options
#   - reject_invalid_complexity_enum_medium_not_med
#   - reject_invalid_overall_fit_enum
#   - reject_verdict_not_reconsider_when_strained_no_override — D-mirror
#   - accept_verdict_not_reconsider_when_strained_with_override
#   - reject_recommended_rationale_missing_internal_path_cite_when_internal_prior_art_exists — G-mirror
#   - reject_is_internal_true_with_non_internal_source_prefix — equivalence violation
#   - reject_complexity_changes_value_inconsistent_with_effort_estimate — derivation check
#   - accept_outcome_high_confidence_full_match — outcome appended; verdict held; all match flags true
#   - accept_outcome_medium_confidence_design_diverged — outcome appended; verdict held; matches_recommendation=false
#   - accept_outcome_low_confidence_verdict_reversed — outcome appended; verdict was Reconsider but feature shipped
#   - reject_outcome_delta_null_when_match_flag_false
#   - reject_outcome_internal_extension_followed_non_null_when_no_internal_prior_art
#   - reject_outcome_internal_extension_followed_null_when_internal_prior_art_exists
```

---

## Step 2 — REUSE research-side `init_helper test_infra`

**Status**: NOT NEEDED by this plan. Discover handoff has no probe block; `test_infra` detection is consumed by probe-tier classification, which is research-bug-mode-only. Confirm `init_helper test_infra` exists (already shipped by RESEARCH-HANDOFF Step 2) but do not extend.

### Verify

```bash
grep -nE 'test_infra' src/devforge/lib/init_helper.py | head -3
# Expect ≥1 hit (RESEARCH-HANDOFF Step 2 shipped this); no edits this plan.
```

---

## Step 3 — `discover_helper finalize-handoff`

**Owner**: python-engineer + instruction-author.

### Files

Three-file split mirrors research-side pattern (`_cli.py` parser entry / `_cmds_handoff.py` handler body / `_handoff_build.py` state→dataclass mapper):

- `src/devforge/lib/_discover/_cli.py` — add parser entry for `finalize-handoff` subcommand (small change: subparser registration + arg defs); dispatches to handler in `_cmds_handoff.py`.
  - Args: `--devforge-dir .devforge` (default; reads `discover-scope.json` + `discover-report.json` from there) + `--emit-handoff-json <path>` (default computed: `discover/<report.date>-<memo.topic_slug>.handoff.json`).

- `src/devforge/lib/_discover/_cmds_handoff.py` (NEW — mirrors `_research/_cmds_handoff.py` 12.4K) — handler body for `finalize-handoff` (and later `append-outcome` from Step 5). Logic:
  1. Load memo + report from `.devforge/discover-scope.json` + `.devforge/discover-report.json` via existing `_state._load_memo` / `_load_report` (raise if either missing — handoff cannot be composed without both).
  2. Run `verify` invariants A-G (existing `/discover` Phase 3 verify) BEFORE schema mapping — handoff write rejects unverified state. Catches the case where `/discover` Phase 3 was skipped and the user reached for handoff anyway.
  3. Delegate state→dataclass mapping to `_handoff_build.build_handoff(memo, report) -> Handoff`.
  4. CLI catches `ValueError` from `Handoff.__post_init__`, formats error to stderr matching research-side `finalize-handoff` error format (lock the format by grepping `_research/_cmds_handoff.py` for the existing stderr template; copy verbatim).
  5. Atomic write JSON-serialized dataclass to target path via existing `_state._atomic_write_json`. Use `dataclasses.asdict` for the JSON dump.
  - Idempotent — re-running overwrites the existing handoff file (single source of truth lives in `.devforge/discover-*.json`; handoff is a derived artefact).

- `src/devforge/lib/_discover/_handoff_build.py` (NEW — mirrors `_research/_handoff_build.py` 19.9K) — deterministic `memo + report -> Handoff` mapping per Step 1 schema. No LLM intervention. Pure function for testability.

- `src/commands/discover/main.md` — add new sub-phase in Phase 4 BEFORE the existing "Ask to save" prompt:

  ```markdown
  ### Phase 4.0 — Finalize handoff artefact

  After Phase 3 `verify` exits 0 AND BEFORE the "Save this discovery report?" prompt:

  ```bash
  .devforge/lib/discover_helper finalize-handoff
  ```

  Helper writes `discover/<report.date>-<memo.topic_slug>.handoff.json` (sibling to the eventual rendered report). On exit 0: surface the path to the user in your next user-facing message as a fenced code block, then proceed to the save prompt. On non-zero exit: copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) and end the turn; the user must address the cited verify violation (likely a missing setter call from Phase 3) and re-invoke `/discover`.
  ```

  Place this between the Phase 3 "Render" sub-section and Phase 4's "Ask to save" sub-section. Existing manual `## Next Step` block in the rendered report stays as a fallback for `/specify` auto-discovery failure cases.

- `tests/lib/test_discover_handoff_cli.py` (NEW — mirrors `tests/lib/test_research_handoff_schema.py` naming; CLI-level finalize-handoff + append-outcome tests live here, separate from schema-level tests in `test_discover_handoff_schema.py`) — add `test_finalize_handoff_round_trip` — fixture memo+report state → finalize-handoff → re-parse handoff.json → assert all blocks intact AND schema-valid.

  Existing test split (per commit `c1a9c59 test(discover): split test_discover_helper by domain`): `test_discover_helper.py` (91.9K — CLI behavior tests), `test_discover_state.py` (13.3K), `test_discover_topic.py` (16.0K). Handoff tests get their own file rather than swelling `test_discover_helper.py`.

- `tests/lib/test_discover_handoff_build.py` (NEW) — pure-function tests for `_handoff_build.build_handoff(memo, report)` — fixture state → built `Handoff` dataclass → assert mapping correctness without filesystem I/O.

### Cross-check with /discover Phase 3 verify

`finalize-handoff` invokes `verify` internally per logic step 3 above. This is intentional double-gating: Phase 3 verify already runs in the spec'd flow, but `finalize-handoff` re-runs it defensively in case a future spec change reorders phases. Cost: one extra invariant pass per finalize call (~ms-scale). Benefit: handoff schema cannot ship invariant violations downstream.

### Verify

```bash
pytest tests/lib/test_discover_handoff_build.py tests/lib/test_discover_handoff_cli.py -k "finalize_handoff" -v
# Integration: run /discover synthetic on testForge20; confirm discover/<date>-<slug>.handoff.json appears with valid schema.
```

---

## Step 4 — Extend `specify_helper import-handoff` for discover variant

**Owner**: python-engineer + instruction-author.

### Why

RESEARCH-HANDOFF Step 6 shipped `specify_helper import-handoff` for research handoffs + `find-handoffs` Phase 0.4 discovery in `/specify`. Both currently scope to `research/*/handoff.json`. This step extends them to also handle `discover/*.handoff.json` with discover-specific seeding behavior.

### Files

Helper edits target the split-package body file `_specify/_cmds_handoff.py` (17.1K), NOT the 72-line thin shim `src/devforge/lib/specify_helper.py`.

- `src/devforge/lib/_specify/_cmds_handoff.py` — extend `import-handoff` handler:
  - Detect handoff kind by reading top-level `handoff_kind` field (`research` vs `discover`) before any seeding logic. Add a `_dispatch_import_handoff(handoff_dict)` helper that routes to existing research-path code OR new discover-path code based on `handoff_kind` value.
  - Discover-variant seeding behavior:
    - `constraints[]` from `spec_seeds.constraints` (same as research-variant — Gap A taxonomy matches).
    - `affected_areas[]` from `spec_seeds.affected_areas` — preserves `is_internal_extension_candidate` flag in a new `.devforge/specify-state.json` field so the spec author surfaces "extend existing implementation at `<path>`" when composing affected-areas section.
    - `risks[]` from `spec_seeds.risks`.
    - `open_questions[]` from `spec_seeds.open_questions`.
    - `spec_type` locked to `greenfield_feature` (no AskUserQuestion confirmation — `/discover` exclusively pre-seeds this type; helper rejects override attempt).
    - records `source.handoff_path` + `source.discover_completed_at` + `source.handoff_kind = "discover"` in state.
    - Mutates `downstream_links.spec_path` in handoff.json with the future `specs/NNN-*/spec.md` path (same as research-variant).
    - **Discover-specific pre-seed**: copy `plan_seeds.recommended_option_rationale` + `plan_seeds.build_vs_buy.recommendation` into a new `.devforge/specify-state.json` field `source.discover_recommended_summary` so the spec author has the recommended direction without re-reading the discovery report.
  - Idempotent — re-import overwrites pre-seeded blocks; warns if `.devforge/specify-state.json` has non-empty user-composed fields (overview / desired_behavior / AC) that import-handoff would NOT overwrite (same warning as research-variant).

- `src/devforge/lib/_specify/_cmds_handoff.py` — extend `find-handoffs` handler (same file):
  - Glob both `research/*/handoff.json` AND `discover/*.handoff.json` within the `--since` window.
  - Emit one-line summary per finding including `kind` field: `<mtime> <handoff_path> <kind=research|discover> <mode_or_verdict> <recommended_summary>`.
  - For discover entries, `mode_or_verdict` field is `verdict=<Worth pursuing|Promising with caveats|Reconsider>`; for research entries, `mode_or_verdict` is `mode=<bug|feature_addition|...>`.

- `src/devforge/lib/_specify/_schema.py` (9.9K — existing) — extend `.devforge/specify-state.json` schema to add the new `source.handoff_kind` / `source.discover_completed_at` / `source.discover_recommended_summary` fields plus a per-`affected_area` `is_internal_extension_candidate` bool field.

- `src/commands/specify/main.md` — extend the existing Phase 0.4 AskUserQuestion to surface kind discriminator:
  - Replace existing Phase 0.4 question text (single-line) from research-only framing to: `"Found <N> recent handoff(s) — <R> research, <D> discover. Pre-seed spec from one? [yes-most-recent / pick-other / cold]"`.
  - `yes-most-recent` branch: import-handoff invocation unchanged (kind auto-detected via top-level field).
  - `pick-other` branch: list with kind tag prefix (`[research]` or `[discover]`) so user picks by topic + kind.
  - `cold` branch: unchanged.

- `tests/lib/test_specify_helper.py`:
  - `test_import_handoff_discover_round_trip` — discover handoff.json → import → state.json fields populated; spec_type locked to greenfield_feature
  - `test_import_handoff_discover_preserves_is_internal_extension_candidate`
  - `test_import_handoff_discover_records_recommended_summary`
  - `test_import_handoff_discover_rejects_spec_type_override`
  - `test_find_handoffs_globs_both_research_and_discover`
  - `test_find_handoffs_emits_kind_discriminator`
  - `test_find_handoffs_summary_format_research_vs_discover`

### Cross-check with research-variant

The research-variant `import-handoff` test cases shipped under RESEARCH-HANDOFF Step 6 MUST continue to pass after this extension. Add a regression guard in `tests/lib/test_specify_helper.py`: invoke a research-handoff fixture via the post-extension code path; assert identical behavior to the pre-extension research-only path. Catches the case where discover-variant branching accidentally regresses research-variant behavior.

### Verify

```bash
pytest tests/lib/test_specify_helper.py -k "handoff" -v
# Integration: testForge20 — run /discover synthetic, then /specify → Phase 0.4 surfaces both handoffs (research + discover), user picks discover, state pre-seeded with greenfield_feature + constraints + areas (with internal-extension flags) + risks.
```

---

## Step 5 — `discover_helper append-outcome`

**Owner**: python-engineer + instruction-author.

### Files

- `src/devforge/lib/_discover/_cli.py` — add parser entry for `append-outcome` subcommand; dispatches to handler in `_cmds_handoff.py` (added by Step 3).
- `src/devforge/lib/_discover/_cmds_handoff.py` — add `append-outcome` handler body (same file extended in Step 3):

  ```bash
  .devforge/lib/discover_helper append-outcome \
      --handoff-path discover/<date>-<slug>.handoff.json \
      --design-option-shipped-id <A|B|C|...|hybrid|none> \
      --design-option-shipped-summary "<1-3 sentence description of what shipped>" \
      --build-vs-buy-actual <Build|Buy|Hybrid|none> \
      [--delta-from-recommendation "<text>"] \
      [--shipped-commit-sha "<sha>"] \
      [--internal-extension-followed <true|false>]
  ```

  Logic:
  1. Validate handoff.json schema before mutation.
  2. Compute helper-side derived fields:
     - `matches_recommendation = (design_option_shipped_id == plan_seeds.recommended_option_id)`
     - `matches_build_vs_buy_recommendation = (build_vs_buy_actual == plan_seeds.build_vs_buy.recommendation)`
     - `verdict_held` per the Step 1 rule
     - `confidence_grade` per the Step 1 derivation table
  3. Enforce `--internal-extension-followed` presence requirement:
     - When handoff has no `internal:` prior-art entries → flag MUST be omitted (helper rejects if supplied; result field set to null).
     - When handoff has ≥1 `internal:` prior-art entry → flag MUST be supplied (helper rejects with stderr citing the unfollowed invariant-G cite path).
  4. Enforce `--delta-from-recommendation` presence requirement: required when any of the three match flags computes to false; helper rejects with stderr citing which flag is false.
  5. Fill `outcome` block in handoff.json (atomic write).
  6. ALSO append `## Outcome` section to the parallel `discover/<date>-<slug>.md` rendered report — single source of truth lives in handoff.json; markdown reflection is for human readers. Same pattern as research-side append-outcome.

- `tests/lib/test_discover_handoff_cli.py` (same file Step 3 creates):
  - `test_append_outcome_high_confidence_full_match`
  - `test_append_outcome_medium_confidence_design_diverged`
  - `test_append_outcome_low_confidence_verdict_reversed_reconsider_to_ship`
  - `test_append_outcome_requires_delta_when_match_flag_false`
  - `test_append_outcome_requires_internal_extension_flag_when_internal_prior_art`
  - `test_append_outcome_rejects_internal_extension_flag_when_no_internal_prior_art`
  - `test_append_outcome_idempotent_overwrite`
  - `test_append_outcome_reflects_to_markdown`
  - `test_append_outcome_helper_computes_match_flags_rejects_manual_override`

### Verify

```bash
pytest tests/lib/test_discover_handoff_cli.py -k "append_outcome" -v
```

---

## Step 6 — Extend `check-outcome` for handoff_kind dispatch

**Status**: helper-side dispatch extension ships NOW. `/execute-task` wire-in DEFERRED per research Step 8 posture (no `/execute-task` command exists).

### Why

RESEARCH-HANDOFF Step 7 shipped `check-outcome` (commit `1191805`) reading `handoff.outcome` and emitting research-shaped reminder. Discover handoffs ALSO can be linked via `.devforge/specify-state.json:source.handoff_path` (same `import-handoff` machinery after Step 4). Without dispatch, `check-outcome` on a discover handoff would emit research-shaped (wrong-shape) reminder text.

### Files

Helper edits target the split-package body file `_research/_cmds_handoff.py` (12.4K), NOT the 73-line thin shim `src/devforge/lib/research_helper.py`.

- `src/devforge/lib/_research/_cmds_handoff.py` — extend `check-outcome` handler:
  - Read top-level `handoff_kind` field before composing reminder text.
  - When `handoff_kind == "research"` → existing reminder text (unchanged).
  - When `handoff_kind == "discover"` → discover-shaped reminder text:

    > Task shipped at commit `<SHA>`. Linked discovery handoff has no outcome marker.
    > Run `.devforge/lib/discover_helper append-outcome` to record:
    >   - which design option (A/B/C/hybrid/none) actually shipped
    >   - whether the recommended build-vs-buy direction held (Build/Buy/Hybrid/none)
    >   - whether the internal-canonical-pattern extension was followed (when applicable)
    >
    > Skipping leaves the discovery report as speculation in empirical-memory corpus.

  - When `handoff_kind` is anything else → reject with stderr citing unknown kind.

  Note on file location: `check-outcome` body currently lives in `_research/_cmds_handoff.py` because research-side owned the subcommand first. Cross-kind dispatch arguably belongs in `_shared/`. Defer the `_shared/_handoff_check_outcome.py` extraction to a follow-up refactor plan; in-place extension is the smaller change AND matches the "Alternative refactor: introduce a kind-agnostic `handoff_helper check-outcome`" deferral noted in research-side comments.

- `src/commands/execute-task/main.md` — **WIRE-IN DEFERRED**. `/execute-task` command does not exist yet (`ls src/commands/` shows only init-forge / generate-docs / configure / constitute / research / specify / discover / plan / setup-wizard / onboard). When `/execute-task` lands in a future plan, that plan owns wiring `check-outcome` into Phase N with kind-dispatch text already shipped by this step.

- `tests/lib/test_research_helper.py` (382K — sole test file for research helper; not split yet):
  - `test_check_outcome_dispatches_to_research_reminder_when_research_kind`
  - `test_check_outcome_dispatches_to_discover_reminder_when_discover_kind`
  - `test_check_outcome_rejects_unknown_handoff_kind`

### Verify

```bash
pytest tests/lib/test_research_helper.py -k "check_outcome" -v
```

`/execute-task` wire-in deferred — no spec file to grep until that command lands.

---

## Step 7 — Cross-grep + emitter check

**Owner**: orchestrator.

### Files

- `scripts/emitters/claude.py` — confirm `discover_helper` is already on the promoted-helpers list (it should be — `/discover` is in production). No new commands added by this plan; only new subcommands on the existing helper. Emitter unchanged per `feedback_emitter_promoted_cross_check`.

### Cross-grep checks

```bash
grep -RnE 'discover.*handoff\.json|finalize-handoff|append-outcome' src/devforge/lib/_discover/ tests/lib/ | wc -l
# Expect ≥ 8 hits across new verbs in discover scope

grep -RnE 'handoff_kind.*discover' src/devforge/lib/ tests/lib/ scripts/
# Expect ≥ 3 hits (schema, import-handoff dispatch, find-handoffs glob)

grep -RnE 'discover.*handoff' src/CLAUDE.md
# Add 1-line mention to CLAUDE.md "Where to find what" table if absent (alongside the research-handoff entry from RESEARCH-HANDOFF Step 9)

grep -RnE 'spec_type_hint.*greenfield_feature' src/devforge/lib/_discover/handoff_schema.py
# Expect locked constant; verify no escape hatch
```

---

## Step 8 — End-to-end verify on testForge20

**Owner**: orchestrator + user.

### Procedure

1. `cd ~/Projects/testForge20 && bash ~/Projects/ai-dev-team-forge/install.sh` — install fresh.
2. Run synthetic `/discover "<topic>"` against a topic whose verb hits at least one existing testForge20 implementation (exercises Step 2.0 internal canonical-pattern surfacing + invariant G).
3. Confirm Phase 3 verify passes (exit 0) AND Phase 4.0 emits `discover/<date>-<slug>.handoff.json` with valid schema (re-validate manually with `discover_helper finalize-handoff --emit-handoff-json /tmp/probe.json` and diff against the on-disk artefact).
4. Inspect handoff blocks:
   - `spec_seeds.affected_areas[*].is_internal_extension_candidate == true` for each internal-prior-art-sourced area.
   - `plan_seeds.cited_canonical_patterns[*].is_internal == true` for each `internal:` prior-art entry; `recommended_option_rationale` contains the internal path substring.
   - `discovery_block.verdict` matches the verdict displayed at Phase 3 render time.
5. Run `/specify` → Phase 0.4 surfaces both research + discover handoffs (if any of each exist) with kind discriminator → accept the discover handoff → state.json pre-seeded with:
   - `spec_type == "greenfield_feature"` (locked).
   - `constraints[]` + `affected_areas[]` (with `is_internal_extension_candidate` preserved) + `risks[]` + `open_questions[]` populated.
   - `source.handoff_kind == "discover"`.
   - `source.discover_recommended_summary` non-empty.
6. Confirm `handoff.json.downstream_links.spec_path` filled after import.
7. Cancel /specify at next gate (don't run full spec for this verify).
8. Run `discover_helper append-outcome` manually with synthetic shipped-fields. Test both happy-path (full match → HIGH confidence) AND divergent-path (different design option shipped → MEDIUM + delta required).
9. Confirm `outcome` block fills in handoff.json AND `## Outcome` section appears in `discover/<date>-<slug>.md`.
10. Confidence grade auto-computed correctly per tuple.

---

## When resuming work

1. Read this plan top-to-bottom.
2. Run Phase 0 state checks — confirm research-side shipped state still in place + helper splits intact.
3. For each Step 1-8, grep for the helper subcommand registrations to find resume point:
   ```bash
   ls src/devforge/lib/_discover/handoff_schema.py src/devforge/lib/_discover/_cmds_handoff.py src/devforge/lib/_discover/_handoff_build.py 2>/dev/null
   grep -nE '"finalize-handoff"|"append-outcome"' src/devforge/lib/_discover/_cli.py 2>/dev/null
   grep -nE 'handoff_kind.*discover|discover/\*\.handoff\.json' src/devforge/lib/_specify/_cmds_handoff.py 2>/dev/null
   grep -nE 'handoff_kind.*discover' src/devforge/lib/_research/_cmds_handoff.py 2>/dev/null
   ```
4. First subcommand or schema branch missing = resume there.
5. Per-step dispatch chain: python-engineer → python-reviewer → instruction-author (when spec text touched) → instruction-reviewer + claude-code-guide (parallel) per `feedback_dual_agent_verify_command_statements`.
6. Final integration: Step 8 against testForge20.

## Out of scope (this plan)

- **Probe block for greenfield** — `/discover` has no probe (post-shipment verification via outcome marker is the equivalent). No `probe.tier` / `test_infra` consumption.
- **V2/V3 framing fields** — `data_flow_chain`, `value_semantics`, `value_production_sites`, `literal_archaeology`, `proposed_call_shape` are research-bug-mode artefacts. Greenfield discovery has no symptom file or hypothesis-vs-reality gap of the same shape; schema does not absorb them.
- **Cross-discover consult at /discover time** — globbing prior `discover/*.handoff.json` for analogous greenfield framings is future scope, parallel to the deferred research-side cross-consult per RESEARCH-HANDOFF "Out of scope".
- **`/plan` consumes discover handoff** — gates on PLAN-COMMAND-REDESIGN parity. Add as a step in that plan when parity clears, NOT here. Same posture as research-side.
- **Mid-flight resume** — `/discover` is fresh-every-run; this plan does not change that. Handoff is composed at Phase 4.0, after the full flow completes.
- **Multi-discovery aggregation into a single spec** — single handoff per discover invocation. `/specify` imports one handoff at a time, same as research-side.
- **Promoting `Reconsider`-verdict discoveries to spec via handoff** — `import-handoff` does NOT block on verdict; it surfaces all globbed handoffs equally. `/specify` user decides whether to proceed despite a `Reconsider` verdict. Outcome marker (Step 5) captures `verdict_held = false` if user ships anyway, which surfaces in confidence grade.
- **Outcome auto-detection from git history** — `append-outcome` is user-invoked with explicit args. No auto-detection of `design_option_shipped_id` from commit content. Cost/benefit: heuristic detection over commit messages would be noisy; user judgment is more reliable.

## Related plans

- `RESEARCH-HANDOFF-PLAN.md` — **PRECEDES this plan**. Steps 1-7+9 SHIPPED 2026-05-19 (Step 8 deferred, Step 10 manual). Provides dataclass schema pattern (Step 1), `_research/_cmds_handoff.py` + `_handoff_build.py` split (Step 3), `_specify/_cmds_handoff.py` import/find infrastructure (Step 6), `check-outcome` subcommand (Step 7). This plan extends each.
- `THREE-LAYER-SEPARATION-PLAN.md` Gap A — provides `--kind` taxonomy this plan's handoff schema consumes (already shipped 2026-05-18).
- `COMMAND-VERIFY-GATES-PLAN.md` Steps 2+3 — `init_helper verify` + `specify_helper verify-rendered` (already shipped 2026-05-18).
- `02-PLAN-COMMAND-REDESIGN-PLAN.md` — orthogonal until parity 4-run gate clears; future step (handoff-aware /plan) gates on parity completion. Discover-handoff fields (`plan_seeds.design_options`, `build_vs_buy`, `cited_canonical_patterns`) feed naturally into a redesigned /plan.
- `REFACTOR-MONOLITHIC-HELPERS-PLAN.md` — **FULLY SHIPPED** 2026-05-20 (commit `9264ab1`). All 5 helpers split into `_<name>/` subpackages. This plan adds new files (`handoff_schema.py` / `_cmds_handoff.py` / `_handoff_build.py`) under the existing `_discover/` subpackage following the established three-file split pattern from `_research/`.

## L3-scoring delta after this plan ships

| L3 requirement | Pre-plan (post-RESEARCH-HANDOFF only) | Post-plan |
|---|---|---|
| 1. Separated artefacts | STRONGER (research handoff carries 3-layer split) | **STRONGER+** (greenfield discovery handoff carries same split for greenfield path) |
| 2. Eval-shaped contracts | PARTIAL | PARTIAL (unchanged — AC EARS shape pre-existing) |
| 3. Empirical-memory corpus | STRONGER (research outcome marker) | **STRONGER+** (discover outcome marker captures design-option-shipped + build-vs-buy-actual + internal-extension-followed signals) |
| 4. Decision-rationale capture | YES | YES (preserved across command boundary for both tracks) |
| 5. Query loop | PARTIAL | PARTIAL (cross-handoff consult is separate future plan; applies to both tracks) |
| 6. Drift detection | STRONGER (Gap E + research outcome) | **STRONGER+** (discover verdict-held signal catches scope/effort estimation drift) |
| 7. Resync mechanism | NO | NO (resync helper still future-work) |
| 8. Constraint traceability | STRONGER (research handoff into spec) | **STRONGER+** (discover constraints + internal-extension affected-areas seed into spec) |

**Net: 4 of 8 strengthened further. Forge reaches L2.95 territory.** Still not strict L3 (corpus query loop + resync absent), but parity coverage across both pre-spec entry tracks (`/research` for existing-code bugs, `/discover` for greenfield features).
