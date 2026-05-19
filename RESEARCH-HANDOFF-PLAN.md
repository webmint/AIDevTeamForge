# RESEARCH-HANDOFF-PLAN

**Status**: Steps 1+2+3+4 SHIPPED 2026-05-19 (schema lock 50 tests + test_infra detection 144 tests + finalize-handoff 343 tests + probe-tier classifier 361 tests); Steps 5-10 pending
**Date**: 2026-05-17 (Step 1 landed 2026-05-19)
**Branch**: `develop-2.0-init`
**Owner**: orchestrator (Claude) + user
**Driver**: 2026-05-17 conversation surfaced two structural gaps in current `/research → /specify` pipeline: (1) manual paste handoff loses ~90% of research context; (2) research outcomes never marked (hypothesis-vs-reality drift invisible). Plan introduces helper-owned `handoff.json` artefact spanning research → spec → plan → execute-task command boundaries, plus probe-tier classification (1 / 1.5 / 2 / 3) closing the "who runs probe" question.

## Context for next session

Current pipeline:

```
Jira ticket  →  /research  →  [manual paste 5-of-50 fields]  →  /specify  →  /plan  →  /execute-task
```

Failure modes documented 2026-05-17:

1. **Manual handoff loss** — research produces ~50 structured fields (symptom + codebase findings + hypothesis enumeration + falsifiers + approaches + constitution constraints + single-layer justification + cites). Copy-paste block at bottom transcribes 5 fields. /specify re-derives intent + constraints from research.md prose. Re-derivation = drift across command boundary.

2. **Research outcome unmarked** — research ends with "Hypothesis (needs repro)". Nowhere captures whether probe confirmed primary / runner-up / neither, what actually shipped, or how reality differed from recommended approach. Future LLM reads stale research, treats speculation and validated equally. Empirical-memory corpus = corrupt by indistinction.

3. **Probe actor ambiguous** — research recommends a "verify step" (typically code instrumentation + UI navigation). Unclear who runs probe: LLM, user, or both. Default in current research output = Tier 3 (user manual) even when Tier 1 (LLM-written unit test) is feasible.

### What this plan ships

Single helper-owned artefact `research/<NNN>-<topic>/handoff.json` carrying:

- **Intent block** — symptom + desired + scope (preserves Jira reformulation)
- **Spec seeds** — constraints (post-Gap-A kind taxonomy) + affected areas + risks + open questions
- **Plan seeds** — recommended approach + layer destination + cited canonical patterns + alternatives considered + complexity
- **Probe block** — tier (1 / 1.5 / 2 / 3) + actor + discriminator + feasibility-check
- **Outcome block** — null until probe confirms; filled by `append-outcome` subcommand
- **Downstream links** — back-references filled by /specify, /plan, /execute-task as pipeline progresses

Helper subcommands write + read; LLM never edits handoff.json directly.

### Dependencies on V2 + V3 + 18 May work

Gates AFTER RESEARCH-FRAMING-REGRESSION-PLAN-V2 SHIPPED + V3 empirical-verifies + 18 May patches land:

| Dependency | Why required |
|---|---|
| **V2 Patch 6** (Phase 2.4d data-flow chain) | `handoff.json` `spec_seeds.data_flow_chain` block includes V2's `handler_qn` + `write_boundary_qn` + `intermediate_qns[]` + `trace_mode`. Schema must absorb V2 fields. **V2 SHIPPED + verified 3/3 on 2026-05-18.** |
| **V2 Patch 7** (id-stability axis) | `handoff.json` `spec_seeds.value_semantics[*].stable_across_calls` + new `spec_seeds.value_production_sites[]` collection. Schema must absorb V2 fields. **V2 SHIPPED + verified 3/3 on 2026-05-18.** |
| **V3 Patch 8** (literal-archaeology gate) | `handoff.json` `spec_seeds.literal_archaeology[]` collection with `{literal, file_line, introduced_by, introduced_when, commit_subject, intent}` rows. 6-value `intent` enum locked (`placeholder | migrated | deliberate | forgotten | inherited-refactor | generated`). |
| **V3 Patch 9** (argument-duplication shape-check) | `handoff.json` `plan_seeds.proposed_call_shape` string field. Required when bug + (single-layer OR literal-replacement). Helper-validated for argument duplication. |
| **V3 empirical verify passed** | If V3 verify fails (still produces 3-turn S3 derivation on splitOnSNA-class bugs), handoff.json structurally permanizes wrong recipe. Block handoff schema lock until V3 catches the literal+duplication pattern in turn 1. |
| THREE-LAYER Gap A (`--kind` taxonomy split) | `spec_seeds.constraints[].kind` enum uses `nfr` / `constitution_anchor` / `external_system`. Pre-Gap-A `use` kind would be carried into handoff schema. |
| COMMAND-VERIFY-GATES Step 2 (`init_helper verify`) | This plan extends `init_helper` for `test_infra` detection. Step 2's `verify` shape must be locked first to avoid conflict. |
| COMMAND-VERIFY-GATES Step 3 (`specify verify-rendered`) | This plan's `specify_helper import-handoff` mutates state pre-render. Step 3 verifies post-render. Sequential — no conflict but verify-rendered should land first to anchor render's canonical form. |

Gap E (per-spec drift stamp) and DRIFT-DETECTOR are orthogonal — no blocking dep either direction.

### Sequencing rule

**Start RESEARCH-HANDOFF Step 1 ONLY after WORKFLOW-2026-05-18 Phase 4 (end-of-day verification) clears.** Phase 0 of this plan re-runs state checks against 18-May patches to confirm dependencies are stable.

---

## Phase 0 — Pre-flight (10 min)

0.1 Verify V2 + V3 patches landed AND both empirical-verified:

```bash
cd /Users/mykolakudlyk/Projects/ai-dev-team-forge

# V2 patches (already shipped + verified 2026-05-18)
grep -nE 'record-data-flow-chain' src/devforge/lib/research_helper.py          # V2 Patch 6
grep -nE 'record-value-production-site' src/devforge/lib/research_helper.py    # V2 Patch 7
grep -nE 'stable_across_calls' src/devforge/lib/research_helper.py             # V2 Patch 7 axis
grep -nE 'Phase 2\.4d' src/commands/research/main.md                           # V2 Patch 6 spec
grep -nE 'empirically verified \(3/3 causes\)' RESEARCH-FRAMING-REGRESSION-PLAN-V2.md  # V2 status

# V3 patches (block handoff schema lock until verified)
grep -nE 'record-literal-archaeology' src/devforge/lib/research_helper.py      # V3 Patch 8
grep -nE 'proposed_call_shape' src/devforge/lib/research_helper.py             # V3 Patch 9
grep -nE 'Phase 2\.5b' src/commands/research/main.md                           # V3 Patch 8 spec
grep -nE 'check 17|check 18' src/devforge/lib/research_helper.py               # V3 verify checks
grep -nE 'V3 applied \+ empirically verified \(turn-1-S3' RESEARCH-FRAMING-REGRESSION-PLAN-V3.md  # V3 status
```

All ≥1 hit AND BOTH V2 + V3 status fields updated to verified → proceed.
Any miss → V2/V3 work incomplete; STOP. handoff.json schema must absorb V2+V3 fields and assume V2+V3 framing-quality gates work.

0.2 Verify 18 May patches landed:

```bash
grep -nE 'kind.*nfr.*constitution_anchor' src/devforge/lib/specify_helper.py   # Gap A
grep -nE 'add_parser\("verify"' src/devforge/lib/init_helper.py                # CVG Step 2
grep -nE '"verify-rendered"' src/devforge/lib/specify_helper.py                # CVG Step 3
grep -nE 'stamp-spec' src/devforge/lib/cbm_sync_helper.py                      # Gap E
grep -nE 'forge-internal:verify-universal-defaults' src/devforge/lib/constitute_helper.py  # DRIFT
```

All ≥1 hit → proceed. Any 0 → 18-May work incomplete; finish that first.

0.3 Confirm test fixture: `testForge20` has at least one `research/` directory with output from a V2-aware `/research` run (post-V2-shipped + post-empirical-verify). If empty OR fixture pre-dates V2: run a synthetic V2-aware `/research` against any trivial topic in testForge20 to seed first fixture with V2 fields populated.

---

## Step 1 — Lock `handoff.json` schema

**Status**: SHIPPED 2026-05-19. `src/devforge/lib/_research/__init__.py` + `src/devforge/lib/_research/handoff_schema.py` (996 lines, stdlib-only dataclasses; pydantic/jsonschema rejected — not installed, project convention) + `tests/lib/test_research_handoff_schema.py` (50 tests = 6 base + 5 V2 data-flow + 5 V2 stability + 8 V3 archaeology + 10 V3 call-shape + 16 edge-cases). Validators absorb V2 (data_flow_chain + trace_mode + value_semantics.stable_across_calls + value_production_sites) and V3 (literal_archaeology 6-value intent enum + proposed_call_shape parser with optional-chaining + argument-duplication reject + fail-soft on nested calls). `compute_confidence_grade` derives HIGH/MEDIUM/LOW from (tier, evidence_source, hypothesis_confirmed, has_production_site_check); production-site-bug + non-test-result evidence downgrades primary-hit from HIGH to MEDIUM; tier-1/1.5 + test-result + inconclusive yields MEDIUM (not LOW fallback). Reviewer audit: 5 findings (0H/2M/1L/2N) — F1+F2+F3+F4 applied, F5 skipped (correct fail-soft behavior, no code change needed).

**Owner**: python-engineer + instruction-author.

### Files

- `src/devforge/lib/_research/handoff_schema.py` (new) — pydantic model OR jsonschema definition. Single source of truth for shape.
- `tests/lib/test_research_handoff_schema.py` (new) — schema validation tests; round-trip via real `/research` state.

### Schema

```json
{
  "schema_version": "1.0",
  "research_path": "research/2026-05-17-restriction-on-adding-the.md",
  "research_completed_at": "2026-05-17T14:32:00Z",
  "mode": "bug | feature_addition | migration | refactor | greenfield",

  "intent": {
    "symptom_summary": "string (required)",
    "desired_summary": "string (required)",
    "scope": "feature-wide | file-local | package-local | system-wide"
  },

  "spec_seeds": {
    "spec_type_hint": "migration_tooling | feature_addition | bug_fix | refactor | greenfield_feature",
    "constraints": [
      {
        "kind": "nfr | constitution_anchor | external_system | follow | not_break",
        "content": "string",
        "quantifier": "string (required when kind=nfr)",
        "constitution_ref": "string (required when kind=constitution_anchor)",
        "protocol": "string (required when kind=external_system, OR contract_doc_ref)",
        "contract_doc_ref": "string (required when kind=external_system, OR protocol)"
      }
    ],
    "affected_areas": [
      {
        "area": "string",
        "files": ["path:line"],
        "impact": "string"
      }
    ],
    "risks": [
      {
        "risk": "string",
        "likelihood": "Low | Med | High",
        "impact": "Low | Med | High",
        "mitigation": "string"
      }
    ],
    "open_questions": [
      {
        "question": "string",
        "blocking": "bool"
      }
    ],

    "data_flow_chain": {
      "_source": "V2 Patch 6 (Phase 2.4d) — required when bug-mode + presentation-layer symptom; null otherwise",
      "handler_qn": "string (the user-action handler in the symptom file)",
      "write_boundary_qn": "string (the persistence call the handler eventually reaches)",
      "intermediate_qns": ["qualified.name.of.intermediate"],
      "trace_mode": "data_flow | calls (which trace_path mode produced the intermediates list per V2 C6 fallback)"
    },

    "value_semantics": [
      {
        "_source": "V2 Patch 7 (id-stability axis)",
        "value": "string (symbol name being classified, e.g. bqItemId)",
        "classification": "preference | invariant | unclassified",
        "stable_across_calls": "true | false | unknown (V2 Patch 7 — required when classification=invariant AND symptom is presentation-layer; accepted-as-unknown when symptom is domain-layer per V2 C4 cyclic-dep mitigation)"
      }
    ],

    "value_production_sites": [
      {
        "_source": "V2 Patch 7 (new collection) — append-only; distinct file_line dedupe per value",
        "value": "string (matches value_semantics[*].value)",
        "file_line": "path:line (where the value is produced/assigned; e.g. src/helpers/strataFamilyToItemAdapters.ts:5)",
        "is_stable": "true | false (false = production site rewrites value per call — Math.random / Date.now / uuid pattern)"
      }
    ],

    "literal_archaeology": [
      {
        "_source": "V3 Patch 8 (new collection) — git-archaeology on hardcoded literals proposed for replacement; distinct (literal, file_line) dedupe",
        "literal": "string (the literal token as it appears in source — e.g. 'false', '0', '\"\"', 'None', '0xff', '100n', '1e-9')",
        "file_line": "path:line (where the literal lives; rejects (none) sentinel — archaeology requires a real path)",
        "introduced_by": "7-40 char hex commit-sha that introduced the literal",
        "introduced_when": "YYYY-MM-DD ISO date",
        "commit_subject": "non-empty commit subject string",
        "intent": "placeholder | migrated | deliberate | forgotten | inherited-refactor | generated (6-value enum LOCKED 2026-05-18)"
      }
    ]
  },

  "plan_seeds": {
    "recommended_approach_id": "snake_case_id",
    "recommended_approach_summary": "string",
    "layer_destination": "string (package or layer name)",
    "layer_justification": "string",
    "cited_canonical_patterns": [
      {
        "qn": "qualified.name.From.CBM",
        "file_line": "path/to/file.ext:line"
      }
    ],
    "alternatives_considered": [
      {
        "id": "snake_case_id",
        "summary": "string",
        "rejected_reason": "string"
      }
    ],
    "complexity": {
      "changes": "Low | Med | High",
      "risk": "Low | Med | High",
      "verify_cost": "Low | Med | High"
    },
    "proposed_call_shape": "string | null — V3 Patch 9. Required when mode=bug AND (single-layer recommendation OR recommended_approach involves literal replacement). Exact call shape post-fix (e.g. 'fetchOrder()'). Helper-validated: parses as function-call shape (regex `^[A-Za-z_][\\w.]*\\([^)]*\\)$`); arg list split on top-level commas; identifier regex with optional-chaining (`[A-Za-z_][\\w]*(?:\\??\\.[A-Za-z_][\\w]*)*`); rejects if any identifier appears more than once in arg list. Fail-soft on parser failure (advisory, not block). Null when V3 trigger conditions not met."
  },

  "probe": {
    "tier": "1 | 1.5 | 2 | 3",
    "actor": "llm | user",
    "test_framework": "vitest | jest | pytest | go-test | cargo-test | rspec | null",
    "test_path": "path/to/test.spec.ts | null",
    "script_path": "research/<NNN>/probe-script.<ext> | null",
    "is_first_test_for_file": "bool",
    "discriminator": {
      "primary_confirms_if": "string",
      "runner_up_confirms_if": "string",
      "both_disproved_if": "string",
      "production_site_check": "string | null — V2 Patch 7 wiring: when spec_seeds.value_production_sites contains any entry with is_stable=false, this field cites the production-site file:line; probe must verify the rewriter at that location is actually invoked on the value path AND that comparison downstream of it fails. Tier 1 test path: synthesize input pre-rewriter + post-rewriter, assert downstream comparator behavior. Null when no unstable production sites recorded."
    },
    "feasibility_check": {
      "data_shape_only": "bool",
      "auth_required": "bool",
      "network_dependent": "bool",
      "timing_dependent": "bool",
      "is_test_code": "bool — true when affected_areas all match test-file patterns; forbids tier=1 (circular)"
    }
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
  "hypothesis_confirmed": "primary | runner_up | none | inconclusive",
  "evidence_source": "test-result | llm-ui-session-log | user-observation",
  "evidence_cite": "string (path / SHA / verbatim observation)",
  "actual_fix_path": "string",
  "delta_from_recommendation": "string | null",
  "confirmed_date": "ISO-8601",
  "confirmed_commit_sha": "string | null",
  "confidence_grade": "HIGH | MEDIUM | LOW"
}
```

### Validators

- All `required` fields enforced.
- `constraints[*].kind` conditional requireds (matches Gap A taxonomy).
- `probe.tier` numeric closed set.
- `probe.feasibility_check.is_test_code == true` → `probe.tier != "1"` (helper rejects).
- `probe.tier == "1"` → `test_framework != null` AND `test_path != null`.
- `probe.tier == "1.5"` → `script_path != null` AND `test_framework == null`.
- `outcome.evidence_source` enum; `confidence_grade` derived from `(tier, evidence_source, hypothesis_confirmed)` tuple.
- **V2-derived validators**:
  - `spec_seeds.data_flow_chain` REQUIRED when `mode == "bug"` AND symptom file matches presentation-layer heuristic (per V2 `_is_presentation_layer`). Null otherwise.
  - `spec_seeds.data_flow_chain.trace_mode` ∈ `{"data_flow", "calls"}`.
  - `spec_seeds.value_semantics[*].stable_across_calls` REQUIRED when `classification == "invariant"` AND symptom is presentation-layer (V2 Patch 7 gating per V2 C4).
  - `spec_seeds.value_semantics[*].stable_across_calls == "false"` → at least one `spec_seeds.value_production_sites[*]` row exists matching `value`.
  - `spec_seeds.value_production_sites[*].file_line` must be a real path:line (reject `(none)` sentinel per V2 Patch 7).
  - `spec_seeds.value_production_sites[]` append-only; distinct `file_line` per `value`.
  - `probe.discriminator.production_site_check` NON-NULL when any `value_production_sites[*].is_stable == false`.
  - `confidence_grade` derivation extended: when `probe.discriminator.production_site_check` non-null AND `outcome.hypothesis_confirmed == "primary"`, evidence_source MUST be `test-result` to score HIGH (production-site bugs need executable evidence; LLM observation is insufficient).
- **V3-derived validators**:
  - `spec_seeds.literal_archaeology[]` REQUIRED when `mode == "bug"` AND `plan_seeds.recommended_approach_summary` contains literal-replacement pattern (regex matching V3 Patch 8 detector: `replace <X> with <Y>` / `change <X> to <Y>` / `<X> -> <Y>` where `<X>` is a recognizable literal token).
  - `spec_seeds.literal_archaeology[*].intent` ∈ closed 6-value enum (`placeholder | migrated | deliberate | forgotten | inherited-refactor | generated`).
  - `spec_seeds.literal_archaeology[*].introduced_by` matches `^[0-9a-f]{7,40}$` (hex commit-sha).
  - `spec_seeds.literal_archaeology[*].introduced_when` parses as ISO date.
  - `spec_seeds.literal_archaeology[*].file_line` rejects `(none)` sentinel.
  - `spec_seeds.literal_archaeology[]` distinct `(literal, file_line)` per row.
  - `plan_seeds.proposed_call_shape` REQUIRED when `mode == "bug"` AND (`plan_seeds.layer_justification` is single-layer OR `plan_seeds.recommended_approach_summary` matches literal-replacement regex). Null otherwise.
  - `plan_seeds.proposed_call_shape` parses via V3 Patch 9 regex; rejects argument duplication (any identifier appearing >1 time in arg list with optional-chaining support).
  - Parser-failure fail-soft: if `proposed_call_shape` cannot be parsed (nested calls / spread / template literals), schema accepts with advisory note (does NOT reject — V3 Patch 9 explicit fail-soft posture).
  - When `spec_seeds.literal_archaeology[*].intent in {placeholder, forgotten, inherited-refactor}`, `plan_seeds.recommended_approach_summary` MUST cite escalation of default-source one layer up from the literal site (helper-side prose-regex check).

### Verify

```bash
pytest tests/lib/test_research_handoff_schema.py -v
# Cases:
#   - valid_handoff_full_bug — happy path with primary + runner-up
#   - reject_kind_use_constraint — legacy --kind use rejected (Gap A taxonomy)
#   - reject_tier_1_when_is_test_code — circular probe blocked
#   - reject_tier_1_without_test_framework
#   - reject_tier_1_5_with_test_framework
#   - valid_outcome_appended — outcome slot populated
# V2 cases:
#   - valid_handoff_with_data_flow_chain — V2 Patch 6 fields populated
#   - require_data_flow_chain_when_bug_presentation_layer — V2 gating
#   - accept_null_data_flow_chain_when_domain_layer_symptom
#   - require_stable_across_calls_when_invariant_presentation_layer
#   - accept_unknown_stable_when_domain_layer_symptom — V2 C4 mitigation
#   - require_production_site_when_stable_false
#   - append_only_distinct_file_line_dedupe_production_sites
#   - reject_invalid_trace_mode_enum
#   - require_production_site_check_when_unstable_value
#   - require_test_result_evidence_for_high_confidence_when_production_site_path
# V3 cases:
#   - valid_handoff_with_literal_archaeology — V3 Patch 8 fields populated
#   - require_literal_archaeology_when_bug_with_literal_replacement
#   - reject_invalid_intent_enum_value — must be one of 6 locked values
#   - reject_short_commit_sha_introduced_by — <7 chars rejected
#   - reject_non_hex_commit_sha_introduced_by
#   - reject_non_iso_date_introduced_when
#   - reject_none_sentinel_file_line_in_archaeology
#   - distinct_literal_file_line_dedupe — same (literal, file_line) is no-op
#   - require_proposed_call_shape_when_single_layer_bug
#   - require_proposed_call_shape_when_literal_replacement
#   - reject_argument_duplication_in_proposed_call_shape — same identifier appears twice
#   - accept_optional_chaining_identifier_in_call_shape — a?.b?.c parses correctly
#   - fail_soft_on_nested_call_shape — advisory not rejection
#   - require_escalation_cite_when_intent_inherited_refactor
#   - require_escalation_cite_when_intent_forgotten
#   - require_escalation_cite_when_intent_placeholder
#   - accept_direct_replacement_when_intent_deliberate — no escalation needed
#   - accept_generated_intent_without_escalation_check
```

---

## Step 2 — `init_helper` test_infra detection

**Status**: SHIPPED 2026-05-19. `src/devforge/lib/init_helper.py` (+~500 lines): `_detect_test_infra` walker spans 5 languages (JS/TS `package.json` devDeps depth ≤2 incl. `packages/*/`; Python `pyproject.toml` + `requirements*.txt` line-bounded scan; Go `**/*_test.go` depth ≤3; Rust `src/**/*.rs` `#[cfg(test)]` with `//` comment-strip; Ruby `Gemfile`); status derives `absent`/`partial`/`present` from populated bucket count. New CLI: `detect-test-infra` + `set-test-infra` (framework→bucket mismatch + status enum validators). YAML `test_infra_record` field-kind round-trips via emit/parse; `_load_state` backfills default block on legacy yaml. `cmd_verify` gains soft-warning channel (`verify: WARN: ...` to stderr, exit 0) when packages_detected populated + test_infra absent + on-disk detector finds something. Tests: 33 new (5 classes: `TestDetectTestInfra` × 16 + `TestSetTestInfra` × 5 + `TestTestInfraYamlRoundTrip` × 4 + `TestVerifyTestInfra` × 5 + `TestDetectTestInfraCLI` × 3) → 144 total green. Reviewer audit: 5 findings (1H/2M/1L/1N) — ALL applied (F1 dead double-validator removed, F2+F3 pyproject/rust comment false-positives closed via line-bounded scan, F4 unreachable dict-type branch + dead test removed, F5 stale subcommand-count test renamed/extended). testForge20 integration verified: `frontend=vitest, status=partial` from `packages/pkg-cse-core/package.json`; `cmd_verify` exits 0.

**Owner**: python-engineer.

### Why

handoff.json `probe.tier` decision depends on whether codebase has test infrastructure. `init_helper` already detects packages; extend to detect test frameworks.

### Files

- `src/devforge/lib/init_helper.py` — add `_detect_test_infra(project_root: Path) -> dict` walking:
  - JS/TS: `package.json` `devDependencies` matching `vitest|jest|mocha|jasmine|playwright|cypress`
  - Python: `pyproject.toml` / `requirements*.txt` matching `pytest|nose2`
  - Go: any `*_test.go` exists under project root (depth ≤3)
  - Rust: any `#[cfg(test)]` in `src/**/*.rs`
  - Ruby: `Gemfile` matches `rspec|minitest`
- `.devforge/init.yaml` gains `test_infra` field:
  ```yaml
  test_infra:
    frontend: "vitest"     # or null
    backend: "pytest"      # or null
    e2e: "playwright"      # or null
    status: "present" | "partial" | "absent"
  ```
- `init_helper set-test-infra` subcommand for explicit override (user can correct false-negative detection).
- `tests/lib/test_init_helper.py` — add `test_detect_test_infra_*` cases per language.

### Cross-check with COMMAND-VERIFY-GATES Step 2

Step 2's `init_helper verify` invariants list (per `COMMAND-VERIFY-GATES-PLAN.md` Step 2) does NOT currently require `test_infra` populated. Add to invariant list: if any detection heuristic returns positive, `test_infra` block must be non-empty. Soft-fail (warn, not exit 2) — absence is legitimate state.

### Verify

```bash
pytest tests/lib/test_init_helper.py -k "test_detect_test_infra" -v
./.devforge/lib/init_helper detect-test-infra --project-root ~/Projects/testForge20
# Expect: stdout JSON with frontend/backend/e2e fields populated per testForge20's manifests
```

---

## Step 3 — `research_helper finalize-handoff`

**Status**: SHIPPED 2026-05-19. `src/devforge/lib/research_helper.py` (+~530 lines): `cmd_finalize_handoff` subcommand loads research-state.json (memo) + research-report.json (report), maps via `_build_handoff_from_state` to `Handoff` dataclass per Step 1 schema, atomic-writes JSON via reused `_atomic_write_json`. Required-field guards reject incomplete state (memo.mode / memo.topic_slug / report.date / report.recommended_approach / report.complexity → exit 2 + stderr cite). Schema validation surfaces as exit 2 + `"finalize-handoff: schema validation failed: <message>"`. `_resolve_cite_to_file_line` walks fix_path_helpers / consumer_chain / value_semantics / dead_siblings to populate `cited_canonical_patterns[].file_line` from real path:line (not QN fallback). `verify_step.discriminator` → `probe.discriminator.primary_confirms_if` (semantic-correct mapping; `.probe` is the ACTION not the criterion). Probe block STUB DEFAULTS (tier=3 / actor=user / discriminator placeholders) — Step 4 replaces with smart classifier. Acknowledged limitations: constitution_constraints all map to `kind="follow"` (setter shape lacks anchor); `data_flow_chain.trace_mode` defaults `"calls"` (state lacks axis); `enhancement` → `feature_addition` translation via `_MEMO_MODE_TO_HANDOFF_MODE`. Tests: 23 new in `TestFinalizeHandoff` (round-trip + 4 missing-field guards + atomicity + creates-parent-dirs + path-defaults + V2/V3 propagate + production_site_check + tier-3-default + alternatives-exclude-recommended + constraints-all-follow + schema-validation + cited-patterns-resolve + sentinel-preservation + missing-date) → 343 total green. Reviewer audits: python-reviewer 4 (1H/2M/1L) all applied (F1 KeyError guard, F2 cited_patterns resolver, F3 atomicity sentinel test, F4 missing-date test); instruction-reviewer 4 (1H/1M/1L/1N) all applied (F1 `--from-handoff` hallucination → `specify_helper import-handoff` Step 6 ref, F2 path-geometry "sibling" → "nested inside subdirectory", F3 `<md path>` → `<abs md path>`, F4 collision policy added); claude-code-guide clean. `src/commands/research/main.md` Phase 4 gains `### Emit handoff.json (mandatory on save)` sub-section (path = `research/<date>-<slug>/handoff.json` per-research subdir; .md stays flat at `research/<date>-<slug>.md`) + closing-message branches updated for proceed/non-proceed/skip paths.

**Owner**: python-engineer + instruction-author.

### Files

- `src/devforge/lib/research_helper.py` — register `finalize-handoff` subcommand.
  - Inputs: `--research-state-path .devforge/research-state.json`
  - Output: `research/<NNN>-<topic>/handoff.json` (atomic write via tempfile + rename)
  - Logic: parse research-state.json; emit handoff.json per schema; validate via Step 1 schema validator before write; reject if schema-invalid.
- `src/commands/research/main.md` — add new Phase (after current final phase, before existing "## Next step" copy-paste block):
  ```bash
  ./.devforge/lib/research_helper finalize-handoff \
      --research-state-path .devforge/research-state.json \
      --emit-handoff-json research/<NNN>-<topic>/handoff.json
  ```
  LLM surfaces handoff.json path to user before showing the existing /specify paste block. Paste block stays as fallback for /specify auto-discovery failure cases.
- `tests/lib/test_research_helper.py` — add `test_finalize_handoff_round_trip` — fixture state → handoff.json → re-parse → assert all blocks intact.

### Verify

```bash
pytest tests/lib/test_research_helper.py -k "finalize_handoff" -v
# Integration: run /research synthetic; confirm research/<NNN>/handoff.json appears with valid schema.
```

---

## Step 4 — Probe-tier classification gate

**Status**: SHIPPED 2026-05-19. `src/devforge/lib/research_helper.py` (+~325 lines): `cmd_set_probe_feasibility` writes 5 booleans (`data_shape_only`, `auth_required`, `network_dependent`, `timing_dependent`, `is_test_code`) to `report["probe_feasibility"]` via argparse `choices=("true","false")` exact-match (lowercase-only). `_classify_probe_tier` decision tree: `is_test_code` → tier=3 (circular gate); `data_shape_only AND NOT (auth|network|timing)` → tier=1 (if test_infra populated) else 1.5; `auth_required OR network_dependent` → tier=2 if `DEVFORGE_CHROME_MCP_AVAILABLE=1` else 3; fallback tier=3. Tier=1 picks framework via `_pick_framework_from_test_infra` (frontend→backend→e2e first non-null); demotes to 1.5 if all buckets None. `_FRAMEWORK_EXTENSION_MAP` covers all 6 schema-valid frameworks (vitest/jest/mocha/jasmine→.spec.ts, pytest/nose2→.py, go-test→_test.go, cargo-test→.rs, rspec→_spec.rb, minitest→_test.rb, playwright/cypress→.spec.ts). Tier=1.5 default script_path = `research/<date>-<slug>/probe-script.mjs` (Node universal runtime). `_read_test_infra_status` reads `.devforge/init.yaml` via reused `init_helper.parse_yaml`; guard-wrapped sys.path injection; narrowed `(OSError, UnicodeDecodeError, init_helper.YamlParseError)` except clause (no bare `Exception` swallow). `_chrome_mcp_available` reads env var strict `"1"` only. `cmd_finalize_handoff` gains required-field guard rejecting incomplete probe_feasibility with `"finalize-handoff: probe_feasibility incomplete; missing flags: [...]"`. Discriminator placeholders updated per tier (1/1.5 → executable language, else → "tbd"). **Deferred**: plan-line "reject downgrade attempts" — no override surface exists in finalize-handoff (`--probe-tier` not accepted); documented as Step-4-scope deferral in classifier docstring at line 4464. Tests: ~36 new in `TestFinalizeHandoff` + `TestProbeTierClassifier` (set-feasibility round-trip + tier-1/1.5/2/3 paths + framework-extension parametrize × 6 + test-code-circular + chrome-mcp env-var + required-field guard + downgrade-demotion). Existing `_setup_minimal_bug_state` fixture extended with set-probe-feasibility all-False defaults. → 361 file-total green. Reviewer audits: python-reviewer 8 (1H/3M/2L/2N) — F2+F4+F5+F6+F7+F8 applied (dead params removed, case-insensitive docstring fixed, sys.path guarded, exception narrowed, redundant assignments dropped, framework coverage extended); F1 → instruction-author scope; F3 deferred per orchestrator brief. instruction-reviewer 3 (2M/1L) all applied (F1 false-causation ordering → convention statement, F2 JSON-escape diagnosis scoped via inline parenthetical, F3 partial error-string quote extended). `src/commands/research/main.md` Phase 2.6 gains "Probe feasibility classification (MANDATORY — all modes)" sub-step between structured-root-cause block and set-verify-step block (bold-prose intro per intra-file convention; no Phase 2.7 heading).

**Owner**: python-engineer + instruction-author.

### Files

- `src/devforge/lib/research_helper.py` — `finalize-handoff` extended with probe-tier classification phase BEFORE writing handoff.json:
  1. Read `feasibility_check` block from research-state (LLM-set during research).
  2. Read `test_infra.status` from `.devforge/init.yaml`.
  3. Apply decision tree:
     ```
     if feasibility_check.is_test_code:
         tier candidates = [2, 3]
     elif feasibility_check.data_shape_only AND NOT (auth_required OR network_dependent OR timing_dependent):
         if test_infra.status == "absent":
             tier = "1.5"
         else:
             tier = "1"
     elif feasibility_check.auth_required OR feasibility_check.network_dependent:
         if chrome_mcp_available():
             tier = "2"
         else:
             tier = "3"
     else:
         tier = "3"  # fallback
     ```
  4. Helper writes `probe.tier` + `probe.actor` (LLM for 1/1.5; LLM+user for 2; user for 3) deterministically.
  5. Reject downgrade attempts: if helper computes tier=1 but research-state requests tier=3, reject with stderr citing why tier=1 is feasible.

- `src/commands/research/main.md` — add new sub-phase in research Phase 3 (after hypothesis enumeration, before recommended verify step): LLM populates `feasibility_check` block via:
  ```bash
  ./.devforge/lib/research_helper set-probe-feasibility \
      --data-shape-only <true|false> \
      --auth-required <true|false> \
      --network-dependent <true|false> \
      --timing-dependent <true|false> \
      --is-test-code <true|false>
  ```
  Closed booleans; helper validates each is set before `finalize-handoff` runs.

- `tests/lib/test_research_helper.py`:
  - `test_probe_tier_1_when_data_shape_only_and_test_infra_present`
  - `test_probe_tier_1_5_when_data_shape_only_and_test_infra_absent`
  - `test_probe_tier_2_when_auth_required_and_chrome_mcp`
  - `test_probe_tier_3_when_user_manual_required`
  - `test_reject_tier_1_when_circular_test_code`
  - `test_reject_downgrade_from_computed_tier_1`

### Verify

```bash
pytest tests/lib/test_research_helper.py -k "probe_tier" -v
```

---

## Step 5 — Tier 1.5 standalone probe-script support

**Owner**: python-engineer + python-reviewer.

### Why

Codebases with no test infrastructure need probe path that doesn't require framework setup. LLM writes self-contained script; helper records path; runs via system `node` / `python` / etc.

### Files

- `src/devforge/lib/research_helper.py` — `record-probe-script` subcommand:
  ```bash
  ./.devforge/lib/research_helper record-probe-script \
      --script-path research/<NNN>/probe-script.<ext> \
      --runtime <node|python|ruby|deno|bun> \
      --inlines-from "file:line,file:line,..."
  ```
  Validates:
  - `script-path` exists and is within `research/<NNN>/` directory
  - `--runtime` available on PATH (`which <runtime>`)
  - `--inlines-from` lists file:line locations whose code the script inlines verbatim — helper records but does NOT verify byte-match (cost/value trade-off; user-readable cross-check via `git blame`)
- `src/commands/research/main.md` — when `probe.tier == "1.5"`, add directive: *"Write `research/<NNN>/probe-script.<ext>` that inlines the buggy logic VERBATIM from cited file:line locations. Do NOT reconstruct; copy. Add `// SOURCE: <file>:<line>` comment on each inlined block for traceability."*
- **probe-script reviewer agent invocation** — after script written, dispatch `python-reviewer` (or new `probe-script-reviewer` agent) to verify:
  - inlined code matches cited file:line literally (grep cited path:line for the literal string in script)
  - script's pass/fail assertion maps to `probe.discriminator` block in handoff.json
  - no spurious logic added beyond minimum probe
- `tests/lib/test_research_helper.py`:
  - `test_record_probe_script_happy_path`
  - `test_reject_probe_script_outside_research_dir`
  - `test_reject_probe_script_runtime_not_on_path`

### Verify

```bash
pytest tests/lib/test_research_helper.py -k "probe_script" -v
# Integration: synthetic research with test_infra.status=absent → finalize-handoff sets tier=1.5 → LLM writes probe-script.mjs → record-probe-script accepts → reviewer agent clean.
```

---

## Step 6 — `specify_helper import-handoff`

**Owner**: python-engineer + instruction-author.

### Files

- `src/devforge/lib/specify_helper.py` — register `import-handoff` subcommand.
  - Inputs: `--handoff-path research/<NNN>/handoff.json`
  - Logic: parse handoff.json; validate schema; pre-seed `.devforge/specify-state.json`:
    - `constraints[]` from `spec_seeds.constraints` (no transformation — Gap A taxonomy matches)
    - `affected_areas[]` from `spec_seeds.affected_areas`
    - `risks[]` from `spec_seeds.risks`
    - `open_questions[]` from `spec_seeds.open_questions`
    - `spec_type` from `spec_seeds.spec_type_hint` (LLM confirms via AskUserQuestion before locking)
    - records `source.handoff_path` + `source.research_completed_at` in state
  - Mutates `downstream_links.spec_path` in handoff.json with the future `specs/NNN-*/spec.md` path (computed deterministically from current spec NNN slot).
  - Idempotent — re-import overwrites pre-seeded blocks; warns if `.devforge/specify-state.json` has non-empty user-composed fields (overview / desired_behavior / AC) that import-handoff would NOT overwrite.

- `src/commands/specify/main.md` — add new Phase 0.4 (after existing Phase 0.3 session-state reset, before Phase 1 input reads):
  ```markdown
  ### Phase 0.4 — Handoff discovery

  ```bash
  .devforge/lib/specify_helper find-handoffs --since "7 days"
  ```

  Helper globs `research/*/handoff.json` modified within window; emits one-line summary per finding (mtime + research_path + mode + recommended_approach_summary). On hits:

  - AskUserQuestion `"Found research handoff(s). Pre-seed spec from one? [yes-most-recent / pick-other / cold]"`.
  - `yes-most-recent` → invoke `import-handoff --handoff-path <most-recent>`. LLM emits handoff summary to user.
  - `pick-other` → list all; user picks index; invoke `import-handoff` against selection.
  - `cold` → skip; current behavior (fresh slate, no pre-seed).

  On no hits → emit "No recent research handoff found; proceeding cold" and continue Phase 1.

  AskUserQuestion question text is single-line per `feedback_askuserquestion_single_line_only`.
  ```

- `tests/lib/test_specify_helper.py`:
  - `test_import_handoff_round_trip` — handoff.json → import → state.json fields populated
  - `test_import_handoff_writes_downstream_link` — handoff.json's `downstream_links.spec_path` updated
  - `test_import_handoff_idempotent` — re-import doesn't duplicate constraints
  - `test_import_handoff_warns_on_existing_user_fields`
  - `test_find_handoffs_globs_recent_only`

### Verify

```bash
pytest tests/lib/test_specify_helper.py -k "handoff" -v
# Integration: testForge20 — run /research synthetic, then /specify → Phase 0.4 surfaces handoff, user accepts, state pre-seeded.
```

---

## Step 7 — `research_helper append-outcome`

**Owner**: python-engineer + instruction-author.

### Files

- `src/devforge/lib/research_helper.py` — register `append-outcome` subcommand:
  ```bash
  ./.devforge/lib/research_helper append-outcome \
      --handoff-path research/<NNN>/handoff.json \
      --hypothesis-confirmed <primary|runner_up|none|inconclusive> \
      --evidence-source <test-result|llm-ui-session-log|user-observation> \
      --evidence-cite "<path|SHA|verbatim observation>" \
      --actual-fix-path "<text>" \
      [--delta-from-recommendation "<text>"] \
      [--confirmed-commit-sha "<sha>"]
  ```
  Logic:
  1. Validate handoff.json schema before mutation
  2. Compute `confidence_grade` from `(probe.tier, evidence_source, hypothesis_confirmed)`:
     ```
     tier=1 + test-result + (primary|runner_up) → HIGH
     tier=1 + test-result + none → HIGH (disproved is also strong signal)
     tier=1.5 + test-result + any → HIGH
     tier=2 + llm-ui-session-log + clear → MEDIUM
     tier=2 + user-observation → LOW
     tier=3 + user-observation → LOW
     all else → LOW
     ```
  3. Fill `outcome` block in handoff.json (atomic write)
  4. ALSO append `## Outcome` section to the parallel `research/<NNN>/*.md` file — single source of truth lives in handoff.json; markdown reflection is for human readers
- `tests/lib/test_research_helper.py`:
  - `test_append_outcome_high_confidence_tier_1`
  - `test_append_outcome_low_confidence_tier_3`
  - `test_append_outcome_idempotent_overwrite`
  - `test_append_outcome_reflects_to_markdown`

### Verify

```bash
pytest tests/lib/test_research_helper.py -k "append_outcome" -v
```

---

## Step 8 — `/execute-task` outcome reminder

**Owner**: instruction-author.

### Files

- `src/commands/execute-task/main.md` (assume command exists by 18 May completion; if not, defer this step to when execute-task lands). Add new Phase at task-completion gate:
  ```markdown
  ### Phase N — Outcome reminder

  After task ships (commit + verify pass), if a `handoff.json` is linked via `.devforge/specify-state.json:source.handoff_path`:

  ```bash
  .devforge/lib/research_helper check-outcome --handoff-path <linked-handoff>
  ```

  Helper checks if `outcome` block is null. If null, surface reminder:

  > Task shipped at commit `<SHA>`. Linked research handoff has no outcome marker.
  > Run `.devforge/lib/research_helper append-outcome` to record:
  >   - which hypothesis (primary/runner_up/none) actually confirmed
  >   - what shipped (may differ from recommended approach)
  >   - evidence source (test-result / session-log / observation)
  >
  > Skipping leaves the research file as speculation in empirical-memory corpus.

  Non-blocking — task completes regardless. User decides whether to record outcome.
  ```
- `tests/lib/test_research_helper.py`:
  - `test_check_outcome_returns_null_when_unmarked`
  - `test_check_outcome_returns_filled_when_marked`

### Verify

```bash
pytest tests/lib/test_research_helper.py -k "check_outcome" -v
grep -n "check-outcome" src/commands/execute-task/main.md
```

---

## Step 9 — Cross-grep + emitter check

**Owner**: orchestrator.

### Files

- `scripts/emitters/claude.py` — confirm `research_helper` + `specify_helper` + `init_helper` are already on `_PROMOTED` list (they should be). No new commands added by this plan — only new subcommands on existing helpers, so emitter unchanged per `feedback_emitter_promoted_cross_check`.

### Cross-grep checks

```bash
grep -RnE 'handoff\.json|finalize-handoff|import-handoff|append-outcome|probe.tier' src/ tests/ scripts/ | wc -l
# Expect ≥ 15 hits across new verbs

grep -RnE 'handoff\.json' src/CLAUDE.md
# Add 1-line mention to CLAUDE.md "Where to find what" table if absent

grep -RnE '"use"' src/devforge/lib/specify_helper.py tests/lib/
# Should be 0 hits (Gap A removed --kind use); confirm handoff schema doesn't reintroduce
```

---

## Step 10 — End-to-end verify on testForge20

**Owner**: orchestrator + user.

### Procedure

1. `cd ~/Projects/testForge20 && bash ~/Projects/ai-dev-team-forge/install.sh` — install fresh.
2. Run synthetic `/research "<topic>"` (use a real testForge20 codebase question for fidelity).
3. Confirm `research/<NNN>/handoff.json` produced with schema-valid content.
4. Inspect probe block — confirm tier set correctly per detected test_infra + feasibility flags.
5. If `tier == 1`: confirm LLM writes test file at `probe.test_path`; run via detected framework; result captured.
6. If `tier == 1.5`: confirm probe-script.mjs (or .py) written; runtime verified on PATH; LLM runs; output captured.
7. Run `/specify` → Phase 0.4 surfaces handoff → accept → state.json pre-seeded with constraints + areas + risks from handoff.
8. Confirm `handoff.json.downstream_links.spec_path` filled after import.
9. Cancel /specify at next gate (don't run full spec for this verify).
10. Run `research_helper append-outcome` manually with synthetic test result.
11. Confirm `outcome` block fills in handoff.json AND `## Outcome` section appears in research/<NNN>/*.md.
12. Confidence grade auto-computed correctly per tuple.

---

## When resuming work

1. Read this plan top-to-bottom.
2. Run Phase 0 state checks — confirm all 18-May patches landed.
3. For each Step 1-10, grep for the helper subcommand registrations to find resume point:
   ```bash
   grep -nE 'finalize-handoff|set-probe-feasibility|record-probe-script|import-handoff|append-outcome|check-outcome|detect-test-infra' src/devforge/lib/
   ```
4. First subcommand missing = resume there.
5. Per-step dispatch chain: python-engineer → python-reviewer → instruction-author (when spec text touched) → instruction-reviewer + claude-code-guide (parallel) per `feedback_dual_agent_verify_command_statements`.
6. Final integration: Step 10 against testForge20.

## Out of scope (this plan)

- **Bidirectional Jira sync** (Option C from 2026-05-17 conversation) — too coupled. Jira drift accepted per user decision 2026-05-17.
- **Cross-research consult** at /research time (glob prior `research/*/handoff.json` for analogous framing) — future plan. This plan ships the artefact (handoff.json with structured fields). Query loop over handoff corpus is separate work.
- **`/plan` consumes handoff** — same as cross-research consult; depends on `/plan` redesign (PLAN-COMMAND-REDESIGN parity gate). Add as Step 11 to that plan when parity clears, NOT here.
- **Test infrastructure adoption** as part of bug fix — Tier 1.5 fallback keeps bug fix shippable. Test-infra adoption is separate /specify scope.
- **Promotion of Tier 1.5 probe-script → real test** — handoff records script existence; promotion to real test framework is post-fix housekeeping, user-driven.
- **Probe re-run automation** — if hypothesis changes post-outcome, user re-runs probe manually. No auto-trigger.
- **Multi-research aggregation** — single handoff.json per research file. No aggregation across N research runs into single spec. /specify imports one handoff at a time.

## Related plans

- `RESEARCH-FRAMING-REGRESSION-PLAN-V2.md` — **PRECEDES this plan**. V2 SHIPPED + verified 3/3 on 2026-05-18. Adds `data_flow_chain`, `value_semantics[*].stable_across_calls`, `value_production_sites[]` to research state shape; these flow into handoff.json `spec_seeds`.
- `RESEARCH-FRAMING-REGRESSION-PLAN-V3.md` — **PRECEDES this plan**. V3 IN-FLIGHT 2026-05-18. Adds `literal_archaeology[]` to research state shape + `recommended_approach.proposed_call_shape` field; these flow into handoff.json `spec_seeds` + `plan_seeds`. Schema lock blocks until V3 empirical-verifies (turn-1-S3 acceptance on splitOnSNA topic).
- `WORKFLOW-2026-05-18.md` — this plan's Phase 0 depends on V2 verified + V3 empirical-verify + 18-May execution completing
- `THREE-LAYER-SEPARATION-PLAN.md` Gap A — provides `--kind` taxonomy this plan's handoff schema consumes
- `THREE-LAYER-SEPARATION-PLAN.md` Gap E — per-spec drift stamp; handoff.json could include spec-stamp reference in `downstream_links` future enhancement
- `COMMAND-VERIFY-GATES-PLAN.md` Steps 2 + 3 — `init_helper verify` + `specify_helper verify-rendered` must land first
- `CONSTITUTION-DRIFT-DETECTOR-PLAN.md` — orthogonal; no dependency either direction
- `PLAN-COMMAND-REDESIGN-PLAN.md` — orthogonal until parity 4-run gate clears; future Step 11 (handoff-aware /plan) gates on parity completion
- **Pipeline-handoff expansion** (deferred per user 2026-05-18) — possible future scope expansion from research→specify bridge to full-pipeline memory (research/discover → specify → plan → execute-task → verify, each stage append-only via helper). Re-evaluate after V3 verify + 18 May patches ship.

## L3-scoring delta after this plan ships

| L3 requirement | Pre-plan | Post-plan |
|---|---|---|
| 1. Separated artefacts | PARTIAL (Jira + research.md + future spec/plan) | **STRONGER** (handoff.json structurally carries the 3-layer split across command boundary) |
| 2. Eval-shaped contracts | PARTIAL | PARTIAL (unchanged — AC EARS shape pre-existing) |
| 3. Empirical-memory corpus | PARTIAL (CBM code-only; no decision history) | **STRONGER** (handoff.json + outcome = queryable decision-history corpus seed) |
| 4. Decision-rationale capture | YES (research is exceptional already) | YES (preserved across command boundary now) |
| 5. Query loop | PARTIAL (/research Patches 1-4) | PARTIAL (cross-handoff consult is separate future plan) |
| 6. Drift detection | PARTIAL (Gap E spec-stamp from 18 May) | **STRONGER** (outcome marker catches hypothesis-vs-reality drift) |
| 7. Resync mechanism | NO | NO (resync helper still future-work) |
| 8. Constraint traceability | PARTIAL (Constitution Constraints table in research) | **STRONGER** (structurally preserved via handoff.json into spec state) |

**Net: 4 of 8 strengthened. Forge moves L2.75 → L2.9 territory.** Not strict L3 (corpus query loop + resync still absent), but closer than any prior cycle.
