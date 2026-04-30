# /generate-docs execution log

Tracks step-by-step outcomes of `GENERATE-DOCS-PLAN.md` execution. Per the plan's "When resuming work" section, this file is updated after each step with: step ID, commit SHA(s), agents invoked, loops needed, comparison outcomes, decisions made, future-session-falsely-believes check result.

Plan reference: `GENERATE-DOCS-PLAN.md` at repo root.

---

## Phase 1.1 — Implement `generate_docs_schema.py` + tests

**Status**: ✅ DONE
**Commit**: see `git log` for SHA — committed in same commit as this log entry's creation

### Files written

- `src/devforge/lib/generate_docs_schema.py` — 14 dataclasses (`SourceCite`, `CodeBlock`, `Export`, `Dependency`, `Hazard`, `PackageDoc`, `ConcernDoc`, `Pattern`, `Layer`, `DepEdge`, `Decision`, `ArchitectureDoc`, `MemoryFinding`) + 2 private helpers (`_require_nonempty`, `_require_in_enum`) + 3 module-level enum tuples (`EXPORT_KINDS`, `DEPENDENCY_KINDS`, `HAZARD_CATEGORIES`)
- `tests/lib/test_generate_docs_schema.py` — 97 tests across 16 TestCase classes
- `GENERATE-DOCS-EXECUTION-LOG.md` — this file

### Agents invoked

- `python-engineer` — initial implementation (1 invocation)
- `python-reviewer` — first audit, surfaced 3 findings (1 medium, 2 low)
- `python-engineer` — applied 3 fixes (S1: missing `SourceCite.end` type tests; S2: `detect.md §4.5` forward-ref framing; S3: `default_factory=list` clarifying comments)
- `python-reviewer` — close-out audit, 0 findings

### Loops

2 loops (initial implementation → reviewer findings → fix application → close-out audit clean)

### Verify outcomes

- `python3 -m unittest tests.lib.test_generate_docs_schema -v` → 97/97 passing
- `python3 -m unittest discover tests/lib -q` → 433/433 passing (336 baseline + 97 new)
- Tests idempotent across two successive runs (0.002s, 0.002s — no shared state)
- No regressions in pre-existing 336 tests

### Comparison

N/A (foundation step; no doc-output comparison until Phase 2.2 produces first per-package doc)

### Decisions made

1. **Type-hint convention**: explicit `typing.Optional/List/Dict/Literal`, no `from __future__ import annotations`. Rationale: keeps types as runtime objects for unambiguous `isinstance` checks in `__post_init__`; matches `init_helper.py`'s no-future-import style; sidesteps Python 3.8 PEP 585/604 footgun.
2. **Literal enums mirrored as runtime tuples**: `EXPORT_KINDS`, `DEPENDENCY_KINDS`, `HAZARD_CATEGORIES` exported as module-level tuples alongside the `Literal` type aliases. `Literal` is type-checker-only at runtime — tests + future helper need an iterable allow-list.
3. **`bool` rejected for `int` fields**: `isinstance(self.start, bool)` short-circuit in `SourceCite.__post_init__` (Python `bool` is a subclass of `int`). After Fix S1, both `start` AND `end` have explicit test coverage for this trap.
4. **Two-helper validation surface**: `_require_nonempty` + `_require_in_enum` (both private, both directly tested). Reused across 14 dataclasses.
5. **`default_factory=list` ergonomic improvement over plan**: plan's schema sketch shows list fields without defaults; implementation adds `default_factory=list` for `PackageDoc`, `ConcernDoc`, `ArchitectureDoc` lists. After Fix S3, each class has an inline comment naming `generate_docs_helper.py`'s `validate-*` subcommands as the non-empty enforcement point.
6. **Cross-record / filesystem checks deferred to helper**: schema validates per-record only. Module docstring explicitly lists what's NOT validated at schema level (snippet verbatim match, cite.file existence, internal Dependency target resolution, architecture_shape closed-enum, MemoryFinding.unit semantics).

### Future-session-falsely-believes check (post-fix)

- Could a fresh session falsely believe `architecture_shape` is enum-validated at schema? **NO** — module docstring + `ArchitectureDoc` docstring both state the closed-enum check lives in `generate_docs_helper.py` and reference `GENERATE-DOCS-PLAN.md` Phase 4 for the future enum source.
- Could a fresh session falsely believe `CodeBlock.snippet` is compared to source at schema? **NO** — `CodeBlock` docstring states the verbatim-match enforcement happens in `generate_docs_helper.py`.
- Could a fresh session falsely believe `Dependency(kind="internal")` validates target existence? **NO** — module docstring lists this as a deferred-to-helper check.
- Could a fresh session falsely believe `detect.md` exists somewhere? **NO** — Fix S2 removed the misleading `detect.md §4.5` reference; the two remaining `detect.md` references in `src/` (in `wizard_render.py` + `setup-wizard/main.md`) point to the existing legacy file at `src/commands/setup-wizard/references/detect.md`.
- Could a fresh session falsely believe LLM can ship docs with empty list fields silently? **NO** — Fix S3's per-class inline comments name `generate_docs_helper.py`'s `validate-*` subcommands as the enforcement point.
- Could a fresh session falsely believe `SourceCite.end` allows bool inputs? **NO** — Fix S1 added explicit `test_bool_end_rejected` + `test_non_int_end_rejected` to anchor the guard.

### Naming-collision flag (carried for Phase 8.2 retirement work)

`PackageDoc`, `ConcernDoc`, `MemoryFinding` exist as class names in both `src/devforge/lib/generate_docs_schema.py` (this work) and `src/devforge/lib/onboard_helper.py` (legacy, vault-restored). Different shapes (legacy = string-blob register-then-compose; new = python-skeleton primitive). The two modules don't import each other; no Python-level collision. Bounded until Phase 8.2 removes the legacy `onboard_helper.py`.

### Next step

Phase 1.2 — Implement `generate_docs_helper.py` skeleton + fill + validate (PackageDoc tier only). See `GENERATE-DOCS-PLAN.md` Step 1.2 for the brief.

---

## Phase 1.2a — Helper PackageDoc tier setters + refactor + 6 review findings

**Status**: ✅ DONE
**Commit**: see `git log` for SHA — atomic commit covering helper + refactor + fixes
**Scope expansion vs plan**: plan said Step 1.2 = single helper file; user intervention during the work requested a structural refactor (SOLID/KISS/DRY/GRASP via `python-engineer.md` Design discipline section) before further code lands on top. This step now delivers the helper AS a refactored package + the design-discipline doc update + the 6 reviewer findings.

### Files written

- `.claude/agents/python-engineer.md` — added `## Design discipline` section (lines 42-99); SOLID/KISS/DRY/GRASP + module-split thresholds + grandfathered helper list. Committed separately at `6b21e06` so the refactor runs under the new discipline.
- `src/devforge/lib/generate_docs_helper.py` — 52-line shim (re-exports for test compat + `main` forwarding). Down from initial 1144-line monolith.
- `src/devforge/lib/generate_docs` — POSIX launcher (unchanged behavior; invokes the shim).
- `src/devforge/lib/_generate_docs/` — NEW internal package, 6 submodules:
  - `__init__.py` — 11 lines, re-exports `main`
  - `_state.py` — 172 lines (atomic JSON read-modify-write; `StateLoadError`; `_die`/`_info`)
  - `_validation.py` — 109 lines (string + line-range + enum membership; control-char rejection at set-time per anti-pattern #1)
  - `_setters.py` — 520 lines (all 12 PackageDoc-tier setter handlers; in plan-a-split zone but cohesion accepted; size note in module docstring)
  - `_status.py` — 102 lines (`cmd_status` + render helpers)
  - `_manifest.py` — 220 lines (`extract-package-scripts`; per-ecosystem dispatch; pyproject.toml + Rakefile static-parse; no subprocess)
  - `_cli.py` — 195 lines (argparse plumbing; OCP subcommand registry as list-of-tuples; `_add_cite_args` factory used 3× per Rule of Three)
- `tests/lib/test_generate_docs_helper.py` — 117 tests (was 111 in initial 1.2a; +6 for findings 1+2)

### Subcommands implemented (1.2a scope only)

`reset`, `add-package`, `set-package-overview`, `set-package-tree`, `set-package-language`, `set-package-framework`, `set-package-build-tool`, `add-package-script`, `add-package-export`, `add-package-dep`, `add-package-hazard`, `set-package-usage-example`, `status`, `extract-package-scripts`. Total: 14 subcommands.

Sub-step 1.2b adds: `set-package-consumer-pattern`, `render-package-skeleton`, `validate-package`, `render-package-doc`. Concern/architecture/memory tiers come in Phases 3-5.

### Agents invoked + loops

1. **python-engineer** — initial implementation as 1144-line monolith (1 invocation, ~28 min)
2. **python-reviewer** — close-out audit on monolith, surfaced 4 findings (1 high, 1 medium, 1 low, 1 nit)
3. **User intervention** — flagged monolith as unsupportable; requested refactor + agent-definition update with SOLID/KISS/DRY/GRASP discipline
4. **instruction-author** — added `## Design discipline` section to `python-engineer.md`
5. **instruction-reviewer + claude-code-guide** (parallel) — 1 medium finding (DIP→SRP misclassification)
6. **instruction-author** — fix 1 (sentence relocated DIP bullet → SRP bullet, principle relabeled)
7. **python-engineer** — first refactor pass timed out after extracting `_state.py` + `_validation.py`
8. **python-engineer (continuation)** — completed extraction (`_setters.py`, `_status.py`, `_manifest.py`, `_cli.py`); converted helper to shim; ~30 min
9. **python-reviewer** — refactor audit, 0 high/med, 1 low + 1 nit on docstrings
10. **python-engineer** — applied 6 findings (4 deferred from monolith review + 2 new docstring findings) in one pass
11. **python-reviewer** — final close-out, 0 findings

Total: 7 effective loops across 11 agent invocations.

### Verify outcomes

- `python3 -m unittest discover tests/lib -q` → 550/550 passing (was 433 baseline; +117 helper tests)
- Idempotency: 2 successive runs produce identical results
- No regressions in pre-existing 433 schema-tier tests
- Acyclic dependency graph confirmed: `_state.py` + `_validation.py` are leaves; `_setters` depends on both + schema; `_status` on `_state`; `_manifest` on `_state`+`_validation` (`_die`/`_info`/`_validate_string` only); `_cli` on `_setters`+`_status`+`_manifest`; shim depends on `_generate_docs` package
- POSIX launcher untouched; CLI surface byte-identical to monolith pre-refactor

### 6 reviewer findings applied

| # | Severity | Location | Fix |
|---|---|---|---|
| 1 | HIGH | `_state.py` `_load_state` + new test | Wrong-type `packages` field raises `StateLoadError` (was silent reset). Test `test_packages_wrong_type_raises_state_load_error` regression-guards |
| 2 | MEDIUM | `_manifest.py` | pyproject.toml `[project.scripts]`/`[tool.poetry.scripts]` regex parser; Rakefile static-parse for `task :name`/`task "name"`/`task 'name'`; +5 tests |
| 3 | LOW | `_validation.py` | Removed dead `_MULTILINE_FIELDS` constant |
| 4 | NIT | `_status.py` | Corrected `_render_optional_field_status` docstring: whitespace-only does NOT clear field, only exact `""` does |
| 5 | LOW | `_setters.py` | Added size-acknowledgment paragraph to module docstring (plan-a-split zone, cohesion accepted, split at 600) |
| 6 | NIT | `_setters.py` | Reworded first sentence to remove "and" (SRP discipline) |

### Decisions

1. **Refactor structure**: sibling internal package `src/devforge/lib/_generate_docs/` with underscore-prefixed submodules; thin shim at `src/devforge/lib/generate_docs_helper.py` for launcher path stability + test re-exports. Schema stays at top-level (not moved into the package).
2. **`_setters.py` size (520 lines, > 400 plan-a-split target)**: cohesion case (all 12 setters share read-validate-mutate-write idiom) outweighs splitting case at this scale; split deferred until file approaches the hard 600-line threshold. Documented in module docstring per Finding 5.
3. **Shim size (52 lines, > 25 target)**: 27 extra lines are forced re-exports for test compatibility (tests reference `gdh.STATE_FILE_NAME`, `gdh._validate_string`, etc.). The "no test changes" constraint locks this. Could be reduced to ~10 lines if a future change updates tests to import from package internals directly.
4. **`__init__.py` minimal re-export**: only `main` exposed; submodules are internal-only.
5. **OCP subcommand registry**: list-of-tuples `_SUBCOMMANDS = [(name, parser_factory, handler), ...]` in `_cli.py`. New subcommands = one-line append + a parser-factory.
6. **DRY `_add_cite_args` factory**: extracted in `_cli.py` because the `--cite-file/--cite-start/--cite-end` triplet appears in 3 places (export, hazard, usage-example) — meets Rule of Three.

### Anti-patterns avoided

- #1 (control-char escaping at set-time): single-line fields reject `\n\r\t` and `<0x20`; multi-line fields permit `\n\r\t` only
- #2 (type validation deferred): all enum membership at set-time, not at status/render
- #4 (fixed-name temp files): `tempfile.mkstemp` + `os.replace` + try/except unlinking temp
- #6 (compose without idempotency): duplicate `add-package` rejected; field overwrites allowed by design
- #7 (unanchored separator splits): argparse parses; no manual string splits on user input
- #8 (file-path+line-range docstring citations): no `path/file.md:NN-MM` style citations; section/symbol references only
- #10 (modern type-hint syntax): `Optional`/`List`/`Dict` from typing; no `X | None` or bare `list[X]` in runtime types

### Future-session-falsely-believes check

- `info()` exists as `init_helper.py` pattern? NO (no info() anywhere in repo)
- Wrong-type `packages` silently accepted? NO (raises StateLoadError + test)
- pyproject `[project.scripts]` ignored? NO (regex-parsed)
- `_MULTILINE_FIELDS` is live code? NO (removed)
- Whitespace-only `--value` clears optional fields? NO (docstring corrected)
- `_setters.py` size accidental? NO (size note in docstring)
- Shim contains business logic? NO (no `def`/`class`; pure re-exports)
- Schema is inside `_generate_docs/`? NO (stays at top level)

### Scope expansion notes

This step exceeded the original Step 1.2 plan in two ways, both user-requested:

1. **Refactor**: plan said one file; user requested package split. Aligned with Design discipline thresholds.
2. **Agent definition update**: plan didn't include this; user requested SOLID/KISS/DRY/GRASP discipline before further code lands. Committed separately at `6b21e06`.

GENERATE-DOCS-PLAN.md not yet updated to reflect this scope expansion. Plan annotation deferred — not blocking subsequent steps.

### Next step

Phase 1.2b — `set-package-consumer-pattern` setter + `render-package-skeleton` + `validate-package` + `render-package-doc`. The validate-package subcommand does the heavy lifting: filesystem checks (cite.file existence, line range bounds), snippet verbatim match against source, internal-Dependency target resolution. See `GENERATE-DOCS-PLAN.md` Step 1.2 brief for full spec.

---

## Phase 1.2b — render-package-skeleton + validate-package + render-package-doc + set-package-consumer-pattern

**Status**: ✅ DONE
**Commit**: see `git log` for SHA — atomic commit (4 subcommands + 5 follow-up fixes)
**Plan annotation**: tech-writer subagent decision committed separately at `54ad158` before Phase 1.2b dispatch.

### Files written / modified

- **NEW** `src/devforge/lib/_generate_docs/_render.py` — 370 lines (markdown render: `render_package_skeleton(state, path) -> str` + `cmd_render_package_skeleton`; atomic write via `tempfile.mkstemp` + `os.replace`)
- **NEW** `src/devforge/lib/_generate_docs/_validators.py` — 426 lines (cross-record + filesystem validation: `validate_package(state, path, project_root) -> List[error]` + `cmd_validate_package` + `cmd_render_package_doc` (gated by validate); 8 validation rules)
- **MODIFIED** `src/devforge/lib/_generate_docs/_setters.py` — 520 → 582 lines (+62 for `cmd_set_package_consumer_pattern`)
- **MODIFIED** `src/devforge/lib/_generate_docs/_cli.py` — 195 → 221 lines (+26 for 4 new subcommand registrations; updated `_add_cite_args` docstring count)
- **MODIFIED** `tests/lib/test_generate_docs_helper.py` — 1377 → 2188 lines (+672 for 34 new tests across 4 new TestCase classes)

### Subcommands added (4)

1. `set-package-consumer-pattern` — mirrors `set-package-usage-example`; sets `consumer_pattern` CodeBlock
2. `render-package-skeleton` — renders markdown skeleton with `[TODO]` slots to `docs/<path>/index.md.skeleton`
3. `validate-package` — runs 8 validation rules, collects all errors, exits 0 if clean / 2 if any error
4. `render-package-doc` — gated by validate; on pass renders to `docs/<path>/index.md` and removes `.skeleton`

### Validation rules (validate-package)

1. Required fields populated (overview, directory_tree, primary_language)
2. At least one export
3. At least one dependency
4. Per-CodeBlock filesystem checks (cite.file exists, readable, line range within bounds)
5. Per-CodeBlock snippet verbatim match (whitespace-normalized: strip trailing per line; CRLF→LF; strip leading/trailing fully-blank lines)
6. Internal Dependency target resolution (matches another registered package OR resolves to directory under project root)
7. Enum membership re-check (paranoia layer over set-time validation; catches state-file corruption)
8. No required-field [TODO] markers in rendered skeleton

Errors collected and reported all at once (no short-circuit per rule, no short-circuit within rules after Fix 2).

### Agents invoked + loops

1. **python-engineer** — initial Step 1.2b implementation (4 subcommands; ~18 min wall-clock)
2. **python-reviewer** — close-out audit, surfaced 5 findings (2 medium, 2 low, 1 nit)
3. **python-engineer** — applied 5 fixes in one pass
4. **python-reviewer** — final close-out, 0 findings

Total: 2 effective loops across 4 agent invocations. Significantly faster than Phase 1.2a (which had a refactor mid-stream); the Design discipline section guided the engineer to clean module placement from the start.

### Verify outcomes

- `python3 -m unittest discover tests/lib -q` → 584/584 passing (was 550 baseline; +34 new = 33 initial + 1 Fix-4 enum re-check test)
- Idempotency: 2 successive runs produce identical results
- `_render.py` 370 lines (under 400 plan-a-split target — clean)
- `_validators.py` 426 lines (in plan-a-split zone; size note added in module docstring per `_setters.py` precedent — Fix 5)
- `_setters.py` 582 lines (deeper into plan-a-split zone, near 600 hard threshold; flagged for split when next setter is added)
- Acyclic dependency graph: `_render.py` → `_state.py` only; `_validators.py` → `_render.py` + `_state.py`; `_setters.py` → `_state.py` + `_validation.py`; `_cli.py` → all sibling modules

### 5 reviewer findings applied (after initial implementation)

| # | Severity | Location | Fix |
|---|---|---|---|
| 1 | MEDIUM | `_render.py:63` `_TODO_USAGE_EXAMPLE` constant + test assertion | Text was "lift a real consumer pattern" inside Usage Example section — semantic mismatch. Changed to "lift a real usage example" |
| 2 | MEDIUM | `_validators.py` `_check_no_todos` | Was short-circuiting after first matching marker; now collects all matching markers (consistent with `validate_package` docstring's "all errors collected" claim) |
| 3 | LOW | `_cli.py:11-13` module docstring | Said `_add_cite_args` shared by 3 subcommands; with consumer-pattern added, now 4. Updated; dropped historical "Rule of Three threshold" sentence |
| 4 | LOW | `tests/lib/test_generate_docs_helper.py` | Added `test_enum_recheck_rejects_corrupted_state` for Rule 7 (enum re-check); previous tests only covered set-time validation |
| 5 | NIT | `_validators.py:1` module docstring | Added size acknowledgment note (mirroring `_setters.py` precedent): plan-a-split zone, cohesion accepted, future split direction named, 600-line trigger |

### Decisions during implementation

1. **`[TODO]` rule scope** — only flags UNSET REQUIRED fields, not optional ones. Optional sections (scripts/hazards/usage_example/consumer_pattern) legitimately render `[TODO]` when LLM elects not to fill. Implemented via `REQUIRED_FIELD_TODO_MARKERS` constant in `_render.py`.
2. **`DEVFORGE_PROJECT_ROOT` env override** — added so tests can use tmpdir as project root with `.devforge/` as a child.
3. **`render-package-doc` CLI placement** — lives in `_validators.py` (not `_render.py`) because it calls `validate_package` first; placing the CLI handler with its primary dependency avoids a `_render` → `_validators` import that would close a cycle. Pure render function `render_package_skeleton` stays in `_render.py` and is called by both `cmd_render_package_skeleton` AND `cmd_render_package_doc` (DRY).
4. **Cite-range bounds edge case** — file ending with `\n` produces N+1 items via `.split('\n')` (last is `''`); validator subtracts 1 to compute true line count. Without this, a 3-line file ending with newline would falsely accept `cite_end=4`.
5. **Whitespace normalization symmetric** — applied to BOTH source slice AND registered snippet so comparison is order-independent (LLM that lifts CRLF source as LF still validates, and vice versa).
6. **Internal dep resolution** — checks BOTH (a) match against another registered package's name, AND (b) resolve to a directory under project root. Either passes.

### Future-session-falsely-believes check

- Could a session believe `_validation.py` and `_validators.py` are the same? NO — `_validators.py` docstring opens with explicit distinction
- Could a session believe `render-package-doc` is in `_render.py`? NO — `_render.py` docstring lines 3-12 document the cycle-avoidance placement
- Could a session believe snippet validation is loose? NO — `_validators.py` docstring documents the normalization rules
- Could a session believe `[TODO]` check rejects optional `[TODO]`? NO — `REQUIRED_FIELD_TODO_MARKERS` is discoverable + commented
- Could a session believe Rule 7's enum re-check is untested? NO — `test_enum_recheck_rejects_corrupted_state` covers it

### Anti-patterns avoided

- #1 (control-char escaping at set-time): preserved in `_validation.py`; render module doesn't introduce new validators
- #2 (type validation deferred): enum re-check at validate-time IS NOT deferred validation — it's a paranoia layer over set-time validation, catching state-file corruption
- #4 (atomic writes via mkstemp + os.replace): preserved in `_render._atomic_write_text` for both `.skeleton` and `.md` outputs
- #6 (compose without idempotency): validate-package run twice produces the same error list
- #7 (unanchored separator splits): no manual string parsing of user input
- #8 (file-path+line-range docstring citations): module docstrings reference `python-engineer.md` Design discipline by symbol, not line range
- #9 (defensive dead branches): no unreachable guards
- #10 (modern type-hint syntax): `Optional`/`List`/`Dict` from typing throughout

### Open follow-ups (not blocking next phase)

1. **`_setters.py` near 600 hard threshold** (582 lines): when next setter is added (Phase 3 concern-tier setters or Phase 5 memory-finding setter), trigger the split into `_setters_scalar.py` + `_setters_records.py` per Design discipline.
2. **`_validators.py` future split direction** documented: `_validators_codeblock.py` (filesystem + snippet) vs `_validators_semantic.py` (required fields, deps, enums, todo-check). Trigger at 600 hard threshold.
3. **`--skip-hazards` referenced in TODO string but doesn't exist** — preserved as descriptive guidance per spec; if a future revision adds the flag, single edit point in `_render.py`.
4. **MemoryFinding schema defined but not yet exposed** — deferred to Phase 5 per plan.

### Step 1.2 complete

Step 1.2 (Phase 1.2a + Phase 1.2b) of `GENERATE-DOCS-PLAN.md` is now COMPLETE. The PackageDoc-tier helper supports the full skeleton-fill loop:

- Register: `add-package`
- Fill: 12 `set-package-*` and `add-package-*` setters
- Render skeleton: `render-package-skeleton`
- Validate: `validate-package` (8 rules, all errors collected)
- Render final: `render-package-doc` (validate-gated; replaces .skeleton with .md)
- Status: `status` (machine-readable progress)
- Manifest helper: `extract-package-scripts` (per-ecosystem dispatch, no subprocess)

### Next step

**Phase 2.1** — Author `/generate-docs` spec + emitter wiring + tech-writer agent. Per the plan annotation at `54ad158`, this dispatches `instruction-author` to draft BOTH `src/commands/generate-docs/main.md` AND `.claude/agents/tech-writer.md` in the same pass; reviewers (`instruction-reviewer` + `claude-code-guide`) audit both files in parallel. Plus `python-engineer` updates `scripts/emitters/claude.py` `_PROMOTED` tuple.
