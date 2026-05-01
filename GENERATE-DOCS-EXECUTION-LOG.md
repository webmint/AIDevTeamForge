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

---

## Phase 2.1 — `/generate-docs` spec + tech-writer SKELETON-FILL MODE + emitter promotion

**Status**: ✅ DONE
**Commit**: see `git log` for SHA — atomic commit covering spec + agent mode + emitter

### Files written / modified

- **NEW** `src/commands/generate-docs/main.md` — 102 lines (slash-command spec; ~150 was the target — landed lighter because helper carries structural load + agent-file owns dispatch contract; basic-path discipline kept Phase 0–5 tight)
- **MODIFIED** `src/agents/tech-writer.md` — 261 → 326 lines (+65)
  - Frontmatter description updated to mention SKELETON-FILL MODE
  - Operating Modes summary list: "three modes" → "four modes"
  - New `### Skeleton-Fill Mode (invoked by /generate-docs)` subsection under Operating Modes
  - Mode-routing prose updated to branch on SKELETON-FILL first
  - New top-level `## SKELETON-FILL MODE (used by /generate-docs)` section appended after `### Rules` (~54 lines: mode preamble + Mode contract + retry budget + structured report + Mode constraints + "What NOT to do")
- **MODIFIED** `scripts/emitters/claude.py` — +2 lines (`_PROMOTED` tuple now `("init-forge", "onboard", "generate-docs", "constitute")`; docstring "Responsibilities" list updated)

### Subcommand dispatch flow (the new `/generate-docs` -> tech-writer cycle)

```
User invokes: /generate-docs
  ↓
Phase 0: pre-flight (verify .devforge/init.yaml, helper executable, target path)
  ↓
Phase 1: discover package via manifest at db-cse-ui-strata/apps/app-web/package.json
  ↓
Phase 2: register package + extract scripts via helper
  - add-package + set-package-{language,framework,build-tool}
  - extract-package-scripts → loop add-package-script per entry
  ↓
Phase 3: render-package-skeleton, then dispatch tech-writer (SKELETON-FILL MODE)
  - Orchestrator brief: mode + path + name + skeleton-path + helper-path + source-root
  - Tech-writer reads source, invokes setters, validates, renders final doc
  - Tech-writer returns structured report
  ↓
Phase 4: verify produced doc (read final .md, run status, print VERBATIM to user)
  ↓
Phase 5: report (counts + path + iteration scope reminder)
```

### Tech-writer SKELETON-FILL MODE contract (the ~30-line target — actual ~54 lines)

The mode section instructs the agent on:
- 6 orchestrator-provided parameters (mode, package path, package name, skeleton path, helper path, source root)
- 6 numbered actions: read source → invoke setters → run validate → handle errors → render final doc → return report
- Tools allowed: Read, Bash, Grep, Glob (NOT Write, Edit — helper writes for it)
- Validate retry cap: 3 attempts before surfacing to user
- Out-of-scope list: Concern docs (Phase 3), Architecture docs (Phase 4), Memory archaeology (Phase 5), cross-package decisions, modifying source files

Skeleton-fill primitive insight: the helper carries the structural load (markdown templates, citation format, section ordering, [TODO] marker convention). The agent only knows: read source, invoke setters, run validate, render doc, report.

### Agents invoked + loops

1. **instruction-author** — drafted spec + tech-writer mode section in one dispatch
2. **python-engineer** (parallel) — emitter `_PROMOTED` update
3. **instruction-reviewer** (parallel close-out) — surfaced 1 MEDIUM (`add-package-hazard` exception to the "all add-* reject duplicates" claim — hazards are permissive by design)
4. **claude-code-guide** (parallel close-out) — spec-compliant, 0 concerns
5. **python-reviewer** (parallel close-out) — emitter clean, 0 concerns; ran end-to-end install smoke against /tmp tmpdir, confirmed `generate-docs.md` ships
6. **instruction-author** — fix applied: differentiated `add-package-{script,export,dep}` (duplicate-rejecting) from `add-package-hazard` (permissive); workaround for hazard mis-registration named (reset + re-fill OR accept duplicate)

Total: 2 effective loops across 6 agent invocations. Faster than Phase 1.2 (the heavier Python work).

### Verify outcomes

- `python3 -m unittest discover tests/lib -q` → 584/584 passing (unchanged — no Python code modified beyond emitter docstring + tuple)
- End-to-end install smoke test (python-reviewer): `/tmp/emitter-smoke` build confirms `generate-docs.md` ships into `<target>/.claude/commands/`
- All 18 helper subcommands referenced in spec + agent mode-section exist in `_cli.py` `_SUBCOMMANDS` registry
- Hazard categories list in tech-writer.md exactly matches `generate_docs_schema.HAZARD_CATEGORIES`
- Iteration banner pattern matches `/onboard`'s pattern (commit `f6c2557`)

### Decisions

1. **Add SKELETON-FILL MODE to existing tech-writer.md** rather than rewrite or create new agent file. Tech-writer already serves multiple modes (ONBOARDING, REFRESH, default task-doc); adding a 4th mode is the cleanest pattern. /onboard's iteration banner depends on the existing ONBOARDING MODE contract; rewriting would break /onboard before Phase 8.2 retirement.
2. **`scripts/generate-agents.py` propagates** `tech-writer.md` to target's `.claude/agents/tech-writer.md`. No changes needed to that emitter — the source format is unchanged structurally; only content was added.
3. **Iteration banner pattern reused** from `/onboard`'s commit `f6c2557` (bold "This override is in effect until removed", phase-behavior table, "Removing this override" sentence with reference to Phase 7.1 spec edit).
4. **Forward refs to helper internals** verified at audit time (whitespace normalization, validate-package error contract, extract-package-scripts stdout shape, add-* duplicate behavior — only the last needed correction).
5. **`_PROMOTED` order** chose execution flow (init-forge → onboard → generate-docs → constitute) rather than alphabetical. Matches the pre-existing pattern.
6. **No `references/` subdirectory** for `/generate-docs` — spec is short enough to be self-contained per basic-path discipline.

### Future-session-falsely-believes check

- Could a session believe SKELETON-FILL MODE is for multi-package? NO — explicit "ONE package per dispatch"
- Could a session believe the helper is optional? NO — explicit "all writes happen via the helper"
- Could a session believe tech-writer designs markdown templates? NO — explicit "helper carries the structural load"
- Could a session believe Concern/Architecture/Memory tiers are in scope? NO — explicit "out of scope" list
- Could a session believe the iteration banner can be removed unilaterally? NO — explicit "removing this section: ... full multi-package flow resumes via the Phase 7.1 spec edit"
- Could a session believe `add-package-hazard` rejects duplicates? NO — fix applied: explicitly distinguishes hazard (permissive) from script/export/dep (duplicate-rejecting)

### Open follow-ups (not blocking next phase)

1. **`src/CLAUDE.md` workflow chain** still lists `/setup-wizard → /constitute → /onboard → /research → /specify` — does NOT yet mention `/generate-docs`. Out of this dispatch's scope (broader 4-command pivot rollout per `ARCHITECTURE-PIVOT-PLAN.md` Steps 2-8). Update during the broader pivot work.
2. **`tech-writer.md` source format inconsistencies** with Claude Code subagent runtime spec (`model_tier: do` field, ```yaml fenced block instead of `---` markers) — pre-existing convention normalized by `scripts/generate-agents.py`. Out of scope here; flag for future agent-emitter review.

### Next step

**Phase 2.2** — User runs `/generate-docs` on testForge20 against `apps/app-web/`. This is the FIRST EMPIRICAL COMPARISON vs the `/onboard` baselines:
- Heavy spec /onboard: 1 monolith, ~50 KB, 33 citations
- Reference spec /onboard: 10 docs, 60.8 KB, 0 citations
- cse-strata-ws-forge actual reference: 12 docs, 44.5 KB, 0 citations

Targets per `GENERATE-DOCS-PLAN.md`:
1. Coverage ≥ 10 concern docs ... wait, this is single-package iteration so just the `index.md` for app-web (concern docs are Phase 3)
2. Citation discipline = every code block has `<!-- path:line-range -->` ref, validated by validate-package
3. Structural consistency = schema / A.2.1 template / citation format are deterministic across runs; LLM-selected content (export set, hazard set, prose) varies per run by design. Helper-level render (`render-package-doc` invoked twice on the same stable state) is byte-identical.
4. A.2.1 template uniformity (Overview / Directory Structure / Tech Stack / Scripts / Main Exports / Types / Dependencies / Hazards / Usage Example / Consumer Pattern)

Phase 2.2 needs the user to install testForge20 with the latest framework state (committed to develop-2.0-init) and run `/generate-docs` interactively. The result is then evaluated against the empirical baseline targets. If shape is approved → Phase 2.3 (lock baseline). If not approved → iterate spec/render template/agent contract until it is.

---

## Phase 2.2 — Empirical iteration on testForge20 + A/B architecture comparison

**Status**: ✅ DONE
**Outcome**: Multiple iteration rounds + empirical A/B comparison decisively resolved the Phase 3 dispatch architecture. Orchestrator-direct slot-fill replaces tech-writer subagent dispatch as canonical.

### Iteration rounds (chronological)

1. **Initial run** — output had: incorrect "Configure, Select, Execute" expansion of "CSE" (hallucination); prior run state preserved blocked progress
2. **No-abbreviation-guessing rule** added to `tech-writer.md` (commit `96af2c5`); CSE expansion now resolved via README (correctly: "Connected Sales Experience")
3. **4 post-Phase-2.2 fixes** (commit `ebd3f21`): validate-package hardening (anti-pattern #2 closed); Phase 0 reset prompt; setter signature documentation; launcher rename (`generate_docs` → `generate_docs_helper`)
4. **State-persistence race condition** (commit `b3bba61`): concurrent setters were racing on load-modify-write; fixed via `_state_transaction()` context manager + `fcntl.flock`; defense-in-depth `_check_optional_render` validator added
5. **Three optimization commitments captured** (commit `377edae`): tech-writer prompt tightening, Resume slot-skip, per-concern parallelism — quality-driven, NOT speed-gated
6. **Tech-writer audit + revise** (commit `6bb69f5`): refresh mode removed (forward ref to non-existent `/refresh-docs`); onboarding mode marked deprecated; rules split universal vs Normal-only; 8 fixes total
7. **HTML-escape + Phase 0/2 spec tightening** (commit `6853244`): prose narrative fields (overview, hazard description, dep purpose, export description) HTML-escape `<>&`; Phase 2 step 7 verification gate added (hard requirement; blocks Phase 3 entry if fields unset)
8. **Option B architecture decision** (commit `125acc7`): A/B comparison run revealed:
   - Option A (tech-writer subagent dispatch): 7 exports, 2 hazards, 9 citations; broke helper-API contract with 2 direct JSON state edits; misclassified 19 workspace-internal deps as external
   - Option B (orchestrator-direct, no tech-writer dispatch): 16 exports, 9 hazards, 18 citations; respected helper-API contract; correctly classified 19 workspace-internal deps; surfaced helper-API walls cleanly rather than bypass
   
   Option B's wins (2-4× coverage, no contract breaks, correct classification) decisive at Phase 2's single-package scope. Tech-writer subagent's scoped context made it more likely to choose bypass over abort when hitting walls; orchestrator (Claude Code main session) had full source + spec context.
   
   Spec changed: Phase 3 of `/generate-docs/main.md` is now orchestrator-direct slot-fill (no `Agent` tool dispatch with `subagent_type=tech-writer`). Anachronistic tech-writer references in Phases 0/2/4 reworded. Iteration banner annotated with A/B comparison outcome.
   
   Helper fix (same commit): `_validators.py` gained third internal-dep resolution check via `init.yaml.packages_detected[]` basename match — closes the wall that blocked option B's first run (workspace-internal deps couldn't resolve in single-package iteration with nested workspace paths). 18 new tests added (8 CLI + 10 unit) including the exact testForge20 shape (pre-fix 19 errors → post-fix 0).

### Final approved baseline (testForge20 `apps/app-web`)

- 474-line single-package doc, ~30 KB
- A.2.1 strict template (Overview / Directory / Tech Stack / Scripts / Main Exports / Dependencies [Workspace-internal + External] / Hazards / Usage Example / Consumer Pattern)
- 18 mechanically-validated citations, all `<!-- path:line-range -->` paired
- 16 exports with verbatim code blocks
- 9 hazards with closed-enum categories: type-safety×3, duplication, v1-v2-coexistence, inconsistency, complexity, naming
- 36 dependencies (19 workspace-internal correctly identified + 17 external)
- HTML-escaped narrative fields (TypeScript generics like `DeepReadonly<Ref<S>>` rendered safely)
- Tech Stack table populated: typescript / Vue 3 / vite (Phase 2 step 7 gate enforced)
- Scripts table populated: 11 entries from `package.json scripts`
- Idempotency verified: back-to-back `render-package-doc` produces byte-identical output (md5 confirmed: `25db847e5c016bf7bc88c70feb9cf807`)
- Full `/generate-docs` run-to-run is NOT byte-identical across runs (LLM judgment varies — empirically: ~7 of ~16 exports overlap, ~2 of ~5 hazards overlap, prose differs). This is by-design variance: schema, A.2.1 template, and citation format remain stable across runs. The python-skeleton primitive locks structure + factual format; content reflects current LLM judgment per run

### Vs prior baselines (the empirical comparison in the plan)

| Source | Files | Bytes | Citations | Workspace-internal | Helper contract |
|---|---|---|---|---|---|
| Heavy spec /onboard (initial monolith) | 1 | ~50 KB | 33 (trust-based) | informal | helper-mediated, validation gates skipped (iteration mode) |
| Reference spec /onboard 10-doc | 10 | 60.8 KB | 0 | informal | n/a |
| cse-strata-ws-forge actual reference | 12 | 44.5 KB | 0 | informal | n/a |
| Option A tech-writer | 1 | ~50 KB | 9 (validated) | 0 (lied) | broken (2 JSON edits) |
| **Option B orchestrator-direct (locked baseline)** | **1** | **~30 KB** | **18 (validated)** | **19 (correct)** | **respected** |

### Agents invoked + loops

This phase had MANY iteration rounds (probably the most of any phase). Per-round agent invocations summed to ~20-25 across `instruction-author`, `instruction-reviewer`, `claude-code-guide`, `python-engineer`, `python-reviewer`. Loops typically converged in 1-3 rounds per fix.

### Decisions made

1. **CSE = "Connected Sales Experience"** correctly resolved via README; framework remained content-blind (no hardcoded abbreviation table)
2. **State-persistence race fix** via `fcntl.flock` + `_state_transaction()` — atomic read-modify-write for setters
3. **HTML-escape narrative prose** — TypeScript generics `<S>` no longer trigger HTML strikethrough in rendered docs
4. **Phase 2 step 7 verification gate** — hard requirement before Phase 3 entry; LLM dropout caught
5. **Internal-dep auto-resolution via init.yaml.packages_detected[]** — workspace-internal deps resolve in single-package iteration
6. **Orchestrator-direct Phase 3 architecture** — option B canonical; tech-writer subagent dispatch reserved for future Phase 7.1 only if/when wall-clock requires

### Anti-patterns closed during this phase

- #2 (validation deferred) — `_check_optional_render` defense-in-depth + Phase 2 step 7 gate
- #4 (atomic writes) — preserved via `_state_transaction`'s mkstemp + os.replace
- #6 (compose without idempotency) — `render-package-doc` re-invocation on already-rendered, stable state does not delete prior state or produce "missing required" errors; `add-package` re-registration is rejected with exit 2 (not silent data loss). Helper-level render output (same state → same markdown bytes) is by-design mechanical determinism; full `/generate-docs` LLM-in-loop variance is outside #6's scope
- #7 (unanchored separator splits) — anchored regex in init.yaml parser

### Future-session-falsely-believes check

- Could a session believe tech-writer dispatch is canonical for /generate-docs? NO — Open decisions #9 RESOLVED + Step 2.3 Lock-in record + Step 2.2 historical-context annotation
- Could a session believe state-persistence is race-free without lock? NO — `_state.py` docstring + `_state_transaction()` enforce
- Could a session believe TypeScript generics in prose render verbatim? NO — HTML-escape applied; tests cover edge cases
- Could a session believe Phase 2 succeeds without populating optional fields? NO — step 7 gate is HARD
- Could a session believe internal-dep validator only checks state + filesystem? NO — third check via init.yaml documented
- Could a session believe full `/generate-docs` runs are byte-idempotent across runs? NO — Step 2.3 Lock-in record + Phase 2.2 Final-approved-baseline note explicitly scope idempotency to helper level; full LLM-in-loop runs are non-idempotent by design
- Could a session believe the locked Phase 2.3 baseline (474-line index.md) is the canonical `/generate-docs` index shape? NO — it's the iteration-mode shape (single-package, no concern docs yet). The LLM rationally packs everything important into the only doc available; once Phase 3 concern docs land, exports / hazards / details relocate per-concern and index.md slims toward the cse-strata-ws-forge reference (~113 lines). Expected, not a bug. Verify when Phase 3 lands.
- Could a session believe partial folder descriptions in iteration-mode tree output are a spec defect? NO — the LLM applies redundancy judgment: when the parent folder's description carries the load (e.g., `components/ # Vue SFCs grouped by feature area`), nested children with self-documenting names get no description. In Phase 3 each substantive nested folder becomes its own concern doc with full description, so the gap resolves naturally. Don't tighten the spec to force tautological descriptions in iteration mode.

---

## Phase 2.3 — Lock baseline + architecture decision recorded

**Status**: ✅ DONE
**Plan annotations** (commit pending): Step 2.3 Lock-in record + Open decisions #9 (RESOLVED post-A/B comparison) + Phase 3.2 / Phase 7.1 brief updates + Step 2.2 historical-context annotation. Tech-writer's prompt-tightening RECOMMENDED bullet marked SUPERSEDED.

### Approved baseline shape (locked)

See Phase 2.2's Final approved baseline section above. The 474-line `apps/app-web/index.md` doc is the reference shape for downstream phases. Future Phase 3 concern decomposition produces per-concern docs that EACH match this shape's structure (Overview / Directory / Public Surface / Types / Dependencies / Hazards / Usage Example), scoped per concern.

### Architectural baseline (locked)

- **Phase 3 dispatch**: orchestrator-direct slot-fill, NOT tech-writer subagent
- **Phase 7.1 multi-package**: orchestrator-direct repeated per package; sequential default; per-package `Agent` tool dispatches with inline briefs only when wall-clock requires
- **Tech-writer.md SKELETON-FILL MODE**: retained for future reference; NOT invoked by canonical /generate-docs spec
- **Tech-writer.md other modes** (Normal, Onboarding deprecated): unchanged — still apply for /finalize/fix/refactor (Normal Mode) and legacy /onboard (Onboarding Mode pending Phase 8.2 retirement)

### Next step

**Phase 3** — Per-concern decomposition. The plan's Phase 3 has 2 sub-steps:

- **Step 3.1**: extend `generate_docs_helper.py` with `ConcernDoc` subcommands (parallel to PackageDoc tier) — `add-concern`, `set-concern-overview`, `set-concern-tree`, `add-concern-export`, `add-concern-dep`, `add-concern-hazard`, `set-concern-usage-example`, `render-concern-skeleton`, `validate-concern`, `render-concern-doc`. Schema-anchored (`ConcernDoc` dataclass already defined in `generate_docs_schema.py` per Phase 1.1).
- **Step 3.2**: extend `/generate-docs/main.md` Phase 3 with concern dispatch — orchestrator detects substantive subfolders, dispatches one slot-fill cycle per concern (orchestrator-direct OR per-concern `Agent` tool dispatches with inline briefs). Per-concern parallelism is mandatory architecture (Phase 3 commitment from `377edae`); Resume slot-skip behavior preserved.

For testForge20 `apps/app-web`: expected to produce ~8-10 concern docs (composables, components, helpers, plugins, router, types, etc.) each at ~50-150 lines, matching cse-strata-ws-forge reference's per-concern shape.
