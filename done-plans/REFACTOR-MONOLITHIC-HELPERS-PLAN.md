# REFACTOR-MONOLITHIC-HELPERS-PLAN

**Status**: ALL PHASES DONE 2026-05-20. Phases A2 + B1 + C1 + C2 + D shipped on `develop-2.0-init` (see commits below). Plan retired; retained for design rationale.
**Branch**: `develop-2.0-init`

## Phase delivery log

| Phase | Helper | Shim Lines (post) | Modules | Commit |
|---|---|---|---|---|
| A2 | `configure_helper.py` | ~70 | `_configure/` 12 modules | shipped 2026-05-18 |
| B1 | `_generate_docs/_doc_setters.py` | n/a (internal split) | `_doc_setters/_project.py` + `_package.py` | shipped 2026-05-18 |
| C1 | `constitute_helper.py` | ~70 | `_constitute/` 12 modules | shipped 2026-05-19 |
| C2 | `specify_helper.py` | 72 | `_specify/` 12 modules | shipped 2026-05-19 (commit `37050fd`) |
| D | `research_helper.py` | 73 | `_research/` 18 modules + `_shared/literal_call_shape.py` | shipped 2026-05-20 (commit `6c8545c`) |

Verification across all phases: existing pytest suites green at pre-refactor count; POSIX launcher `--help` bit-identical; cross-ref grep clean. No behavior changes, no signature changes, no test-file modifications.


**Driver**: Five `*_helper.py` files in `src/devforge/lib/` have crossed 2000 lines; the largest (`research_helper.py`) is 4011 lines. Each iteration adds 200-400 lines without seams. Cognitive cost compounds. The proven template — `_generate_docs/` subpackage + thin `generate_docs_helper.py` shim re-exporting `main` — already exists in-tree and has shipped through GENERATE-DOCS-PLAN. This plan applies the same template to the remaining monolithic helpers, sequenced by commit-frequency (cold first, hot last) to minimize merge friction against in-flight work.

## Context for next session

### Why subpackage, not flat split

`src/devforge/lib/generate_docs_helper.py` (2 KB) is a thin shim re-exporting `main` from `_generate_docs/` package alongside selected state + validator symbols for direct-import tests. The shim preserves the public import path (`from devforge.lib.generate_docs_helper import …`) and the POSIX launcher (`src/devforge/lib/generate_docs_helper`) calls into it unchanged. Consumers see zero churn. The same shape applies here.

### Target template

```
src/devforge/lib/
  <name>_helper.py             # thin shim — re-export main + public API symbols
  _<name>/
    __init__.py                # from ._cli import main
    _cli.py                    # build_parser + subcommand dispatch + main()
    _state.py                  # defaults, _load, _dump, _atomic_write_json,
                               #   _lock_path, _state_transaction, _*_path
    _validators.py             # _validate_scalar / _enum / _array / _verbatim, _die
    _<domain>.py …             # helper-specific logic, one module per concern
```

Test files mirror the split — `tests/lib/test_<name>_<module>.py` per submodule. Precedent: 6281-line `test_generate_docs_helper.py` already broken into 8 files (`test_doc_setters_project`, `test_doc_setters_package`, `test_project_input`, `test_glossary`, `test_index_helper`, `test_verify_file_docs`, `test_set_concern_tree`, `test_validate_file_doc`).

### Snapshot of monolithic helpers (2026-05-18)

| Helper | Lines | Recent commits (2 wk) | Pending plan touches | Phase |
|---|---|---|---|---|
| `research_helper.py` | 4011 | 10 | /research HOW-extraction queued; RESEARCH-HANDOFF-PLAN pending | D (last) |
| `configure_helper.py` | 3312 | 2 | none | A (first) |
| `constitute_helper.py` | 3105 | 6 | `CONSTITUTION-DRIFT-DETECTOR-PLAN.md` (DRAFTED) | C |
| `specify_helper.py` | 3020 | 4 | `COMMAND-VERIFY-GATES-PLAN.md` Step 3 (DRAFTED) | C |
| `discover_helper.py` | 2123 | 1 | none | A |
| `_generate_docs/_doc_setters.py` | 2041 | 0 (subpackage) | none | B |

`init_helper.py` (949 lines) sits below the 1000-line threshold even after `COMMAND-VERIFY-GATES-PLAN.md` Step 2 lands (additive). Out of scope.

### Cross-helper dependencies (must preserve)

- `configure_helper` imports `init_helper`
- `constitute_helper` imports `init_helper` + `configure_helper`
- Each POSIX launcher (`src/devforge/lib/<name>_helper` shell wrapper) invokes `python3 <name>_helper.py …`
- Tests in `tests/lib/test_<name>_helper.py` import top-level symbols from `<name>_helper`

The thin-shim pattern preserves all of the above. Zero call-site churn is a hard constraint.

### Duplicated infrastructure (NOT addressed here)

Each of the 5 monolithic helpers carries its own copy of `_atomic_write_json`, `_lock_path`, `_state_transaction`, `_die`, `_validate_scalar/_enum/_array/_verbatim`. Subtle signature differences exist (e.g., `_validate_enum` takes `tuple` in `research_helper`, `set` in `constitute_helper`). Deduplication into a shared `_lib_core/` module is **out of scope for this plan** — premature extraction risks changing semantics under tests across all 5 helpers at once. Revisit only if appetite remains after Phase D ships.

## Conventions (apply to every phase)

- **Test-first** per `feedback_test_first_python_helpers.md` — refactored modules pass the existing test suite **before** any test file is split; the test split is a follow-up step within the same phase.
- **Cross-check after every change** per `feedback_cross_check_after_every_change.md` — grep for the helper name across `src/`, `tests/`, `scripts/`, `*.md`; verify thin shim still exports every referenced symbol.
- **Sentence-level hallucination check** for any spec / docstring touched.
- **Helper-owns-shape** per `feedback_helper_owns_shape_principle.md` — public API on the shim is the shape contract; submodules are internal.
- **Emitter cross-check** per `feedback_emitter_promoted_cross_check.md` — `scripts/emitters/claude.py` references helper files by name; verify `_PROMOTED` list does not need adjustment (no new top-level files are added — only the existing `<name>_helper.py` is rewritten into a shim).
- **Multi-Python verify** — `.pyc` cache in `__pycache__/` shows both `cpython-312` and `cpython-314`. Run pytest under whichever interpreters CI runs (verify against `.python-version` / CI config before declaring phase done).
- **POSIX launcher smoke** — every phase ends with `./src/devforge/lib/<name>_helper --help` returning 0 and listing every subcommand the pre-refactor helper exposed.

## Phase A — Cold helpers (READY NOW)

No pending plan touches `discover_helper` or `configure_helper`. These are the safest entry points.

### Phase A1 — `discover_helper.py` (2123 L)

**Seams** (verified against current symbol layout):
- `_discover/_state.py` — `_empty_dimension`, `default_memo_state`, `default_report_state`, `_memo_path`, `_report_path`, `_atomic_write_json`, `_load_memo`, `_load_report`, `_lock_path`, `_state_transaction`
- `_discover/_validators.py` — `_die`, `_validate_scalar`
- `_discover/_topic.py` — `derive_topic_slug`, `_tokenize_for_conflict`, `_detect_scope_conflicts`, `_compute_scope_coverage`
- `_discover/_cli.py` — `build_parser`, `_register_subcommands`, `main`, every `cmd_*` handler
- `discover_helper.py` (shim, ~50 lines) — re-export `main` plus `default_memo_state` / `default_report_state` / `_load_memo` / `_load_report` / `derive_topic_slug` for direct-import tests

**Test split** (after pytest green on the in-place rewrite):
- `tests/lib/test_discover_state.py` — defaults + IO round-trip
- `tests/lib/test_discover_topic.py` — slug + conflict + coverage
- `tests/lib/test_discover_helper.py` — slimmed to CLI-level integration tests only

### Verify (A1)

```bash
.venv/bin/pytest tests/lib/test_discover_helper.py -q
./src/devforge/lib/discover_helper --help | grep -c '^  [a-z]' # subcommand count matches pre-refactor baseline
wc -l src/devforge/lib/_discover/*.py | awk 'NR==NF {exit ($1>1000)}' # every module < 1000 L
grep -rn "from devforge.lib.discover_helper\|import discover_helper" src/ tests/ scripts/ | wc -l # unchanged from pre-refactor count
```

### Phase A2 — `configure_helper.py` (3312 L)

**Seams** (verified against current symbol layout):
- `_configure/_state.py` — `_output_file_path`, `default_state`, `_write_state`, `_load`, `_dump`, `_lock_file_path`, `_state_transaction`
- `_configure/_validators.py` — `_die`, `_validate_scalar`, `_validate_enum`, `_validate_string_array`, `_validate_path_value`, `_validate_verbatim`
- `_configure/_yaml.py` — `_needs_quoting`, `_emit_scalar`, `emit_yaml`, `YamlParseError`, `_parse_scalar_token`, `parse_yaml`
- `_configure/_cli.py` — `build_parser`, every `cmd_*` handler, `main`
- `configure_helper.py` (shim) — re-export `main`, `default_state`, `emit_yaml`, `parse_yaml`, `YamlParseError`, validators referenced by `constitute_helper`

**Test split**:
- `tests/lib/test_configure_yaml.py` — emit + parse round-trip
- `tests/lib/test_configure_state.py` — defaults + transactions
- `tests/lib/test_configure_helper.py` — slimmed to CLI-level

### Verify (A2)

```bash
.venv/bin/pytest tests/lib/test_configure_helper.py tests/lib/test_constitute_helper.py -q # constitute imports configure — both must stay green
./src/devforge/lib/configure_helper --help | grep -c '^  [a-z]'
wc -l src/devforge/lib/_configure/*.py
grep -rn "import configure_helper" src/ tests/
```

## Phase B — Internal-only split (READY NOW, parallel-safe with A)

### Phase B1 — `_generate_docs/_doc_setters.py` (2041 L)

Affects a subpackage that already exists; no public API surface changes. Tests already split by tier (`test_doc_setters_project.py` 1748 L + `test_doc_setters_package.py` 498 L) — module split mirrors tier.

**Seams** (revisit before entering; current symbol survey not yet run):
- `_doc_setters/_project.py` — project-tier setters
- `_doc_setters/_package.py` — package-tier setters
- `_doc_setters/__init__.py` — re-export the symbols `_generate_docs/_cli.py` currently imports from `_doc_setters`

### Verify (B1)

```bash
.venv/bin/pytest tests/lib/test_doc_setters_project.py tests/lib/test_doc_setters_package.py tests/lib/test_generate_docs_helper.py -q
grep -rn "from _generate_docs._doc_setters\|from \._doc_setters" src/devforge/lib/ tests/
wc -l src/devforge/lib/_generate_docs/_doc_setters/*.py
```

## Phase C — Blocked on DRAFTED plans

### Phase C1 — `constitute_helper.py` (3105 L)

**Blocker**: `CONSTITUTION-DRIFT-DETECTOR-PLAN.md` lands its `forge-internal:verify-universal-defaults` subcommand. Refactor on top.

**Seams** (revisit after blocker lands):
- `_constitute/_state.py` — `_empty_section`, `_empty_patterns_section`, `_empty_scaffolding_guide`, `default_state`, `_write_state`, `_load`, `_dump`, `_lock_file_path`, `_state_transaction`, `_output_file_path`
- `_constitute/_validators.py` — `_die`, `_validate_scalar`, `_validate_enum`, `_validate_string_array`, `_validate_path_value`, `_validate_verbatim`
- `_constitute/_universal_blocks.py` — `_parse_universal_blocks`, `_split_design_principles`, `_split_solid_sub_rules`, `_split_bullet_rules`, `_extract_universal_rules_from_state`
- `_constitute/_drift.py` — drift-detector logic (new; lands from CONSTITUTION-DRIFT-DETECTOR-PLAN before this phase enters)
- `_constitute/_cli.py` — `build_parser`, every `cmd_*` handler, `main`
- `constitute_helper.py` (shim)

### Phase C2 — `specify_helper.py` (3020 L)

**Blocker**: `COMMAND-VERIFY-GATES-PLAN.md` Step 3 ships the post-render verify gate. Refactor on top.

**Seams** (revisit after blocker lands):
- `_specify/_state.py` — `default_state`, `_state_path`, `_atomic_write_json`, `_load_state`, `_lock_path`, `_state_transaction`
- `_specify/_validators.py` — `_die`, `_validate_scalar`, `_validate_enum`
- `_specify/_topic_match.py` — `topic_tokens`, `filename_tokens`, `filename_matches_topic`, `source_origin_for_path`
- `_specify/_findings.py` — `_finding_slug`, `_next_finding_id`, `_source_coverage`
- `_specify/_cli.py` — `build_parser`, every `cmd_*` handler, `main`
- `specify_helper.py` (shim)

### Verify (C1 / C2)

```bash
.venv/bin/pytest tests/lib/test_constitute_helper.py -q     # C1
.venv/bin/pytest tests/lib/test_specify_helper.py -q        # C2
./src/devforge/lib/constitute_helper --help                  # C1
./src/devforge/lib/specify_helper --help                     # C2
```

## Phase D — `research_helper.py` (4011 L) LAST

**Blocker**: /research HOW-extraction migration to /plan settles. `RESEARCH-HANDOFF-PLAN` and `WORKFLOW-2026-05-18.md` close out. No V4 regression patch in flight.

**Why last**: 10 commits in 2 weeks; V3 Patches 6/7/8/9 just landed; Patches 8+9 added literal-archaeology + arg-duplication gates that may still see follow-ups. Refactoring during patch-warm phase = ugly rebases against empirically-verified state-shape changes.

**Seams** (revisit before entering — current symbol list is a strong hint, not the final shape):
- `_research/_state.py` — `_empty_dimension`, `default_memo_state`, `default_report_state`, `_memo_path`, `_report_path`, `_atomic_write_json`, `_load_memo`, `_load_report`, `_lock_path`, `_state_transaction`
- `_research/_validators.py` — `_die`, `_validate_scalar`, `_validate_enum`, `_validate_string_array_json`, `_validate_verbatim`, `_validate_file_line`, `_split_path_line`, `_has_anchor_finding`
- `_research/_literal_call_shape.py` — `_detect_literal_replacement`, `_normalize_call_shape`, `_split_top_level_args`, `_detect_arg_duplication` (Patch 8 + Patch 9 surface area)
- `_research/_layer_package.py` — `_is_presentation_layer`, `_extract_package`
- `_research/_verify_gates.py` — `_compute_check_8b_would_fire`, plus the rest of the check-N family (full enumeration deferred until phase entry)
- `_research/_render.py` — `_render_report_md` + helpers
- `_research/_cli.py` — `build_parser`, every `cmd_*` handler, `main`
- `research_helper.py` (shim)

### Verify (D)

```bash
.venv/bin/pytest tests/lib/test_research_helper.py -q        # 267+ tests as of Patch 9; baseline must stay green
./src/devforge/lib/research_helper --help
wc -l src/devforge/lib/_research/*.py
grep -rn "from devforge.lib.research_helper\|import research_helper" src/ tests/ scripts/
```

## Risk register

- **R1 — Multi-Python**: `__pycache__/` shows `cpython-312` + `cpython-314`. Each phase's verify must run under both if CI exercises both.
- **R2 — Cross-helper imports**: `configure_helper` ← `init_helper`, `constitute_helper` ← (`init_helper` + `configure_helper`). Shim re-exports must cover every symbol these dependents reach for. Audit with grep before each phase's shim is finalized.
- **R3 — POSIX launcher path**: `src/devforge/lib/<name>_helper` (no `.py`) is a shell wrapper. Verify it still locates the Python entry after the rewrite (Python script kept at the same path, just shortened).
- **R4 — Test direct-imports**: tests reach for non-`main` symbols (`default_state`, validators, etc.). Generate the symbol list before writing the shim by grepping `tests/lib/test_<name>_helper.py` for `from <name>_helper import …`.
- **R5 — In-flight patches against research_helper**: Phase D entry condition is "no V4 patch active". Confirm before entering.

## When resuming work

1. Re-read this plan's status line — confirm phase boundaries haven't shifted.
2. Verify each helper's line count + 2-week commit count is still in the same ballpark as the snapshot table above. If `research_helper` has dropped below 3000 lines from extraction work, Phase D may be smaller than drafted.
3. Check that the named blockers are still in flight or have landed:
   - `CONSTITUTION-DRIFT-DETECTOR-PLAN.md` — landed? → C1 unblocked.
   - `COMMAND-VERIFY-GATES-PLAN.md` Step 3 — landed? → C2 unblocked.
   - /research HOW-extraction + `RESEARCH-HANDOFF-PLAN` + `WORKFLOW-2026-05-18.md` — closed? → D unblocked.
4. Pick the phase whose blocker is clear. Re-survey the helper's symbol layout (`grep -n "^def \|^class " src/devforge/lib/<name>_helper.py`) before writing seams — the snapshot here is a hint, not a contract.
5. Execute the phase: subpackage split → in-place pytest green → test file split → POSIX launcher smoke → cross-ref grep → commit.

## Out of scope

- Shared-infra deduplication (`_lib_core/`) — revisit after Phase D ships, only if appetite remains.
- `init_helper.py` (949 L) — below threshold.
- Test file size reduction for non-monolithic helpers.
- Documentation regeneration / `CHANGELOG.md` entry — handled at phase-completion time per `feedback_release_docs.md`.
