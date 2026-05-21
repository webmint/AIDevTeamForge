# CONSTITUTION-FORCING-FUNCTIONS-PLAN

**Status**: Drafted 2026-05-21.
**Branch**: `develop-2.0-init`
**Driver**: 2026-05-21 conversation — Sonnet 1.28 generated a duplicate magic string `'SHIPPING'` for `OrgV2AddressType.Shipping = 'SHIPPING'` (member of a generated enum in `pkg-cse-types/index.d.ts:2569`) in target code. Direct violation of universal §3.5 ("No magic values"); the per-consumer §3.1 ("Type Safety", project-specific) would also typically encode a "generated types are source of truth" rule for a TS stack and was equally bypassed. Prose-only constitution rules are insufficient: the model reads them but does not ground them against the codebase. Pattern matches the rationale of `CONSTITUTION-DRIFT-DETECTOR-PLAN.md` ("shell-fact instead of by-eye"). This plan extends the same shape into a family of mechanical detectors that catch the rule classes LLMs systematically violate.

## Context for next session

`CONSTITUTION-DRIFT-DETECTOR-PLAN.md` established the pattern: helper subcommand parses a declared source-of-truth + a comparison surface, emits structured findings, exit-2 on violation, exit-0 on clean. That plan is **forge-internal** (compares forge canonical template vs consumer state). This plan extends the same shape to **consumer-side** detectors that compare the consumer's own source against the consumer's own generated types / declared layer graph / declared repository dirs.

Three load-bearing detectors, ranked by confidence + value:

1. **Magic-enum duplication** — string literal in consumer source matches a member of a generated enum/union from a declared generated-types directory. Backed by `src/constitution.md` §3.5 "No magic values" (universal). Highest-confidence; the specific violation that triggered this plan. (Note: project-specific §3.1 "Type Safety" — populated by `/constitute` per-consumer — typically encodes the "generated types are source of truth" rule for a given consumer's stack, but that is a per-project body, not the universal anchor.)
2. **Cross-layer import violation** — import path crosses a layer boundary declared in `.devforge/constitute.json`. Architecture fitness function shape. Backed by §3.6 "Design Principles" (universal SOLID block). High-confidence given declared layer graph.
3. **`any`-with-generated-available** — `: any` annotation in a file that imports from a declared generated-types dir. Signals "LLM gave up on typing instead of importing the available generated type". Backed by §3.5 "No magic values" (extended interpretation: `any` is the type-system equivalent of a magic value — opaque, unenforced, duplicates information that exists elsewhere). Pure grep; high precision when scoped to importing files.

Three deferred (med/low confidence; queued behind empirical evidence):

4. Schema/contract drift (openapi-typescript handrolled-DTO mismatch) — needs schema parser per stack; not yet pulled by a real violation.
5. Test-presence for new exports — high false-positive risk on type-only exports and refactors.
6. Literal-archaeology / 6-value intent classification — already queued in `04-PR-REVIEW-PLAN.md`; lives at PR-review surface, not pre-commit.

## Design

### Scope: consumer-shipped, not forge-internal

Unlike `CONSTITUTION-DRIFT-DETECTOR` (forge dev repo runs against consumer path), these detectors need the consumer's own source + the consumer's own generated types. They ship in the consumer's `.devforge/lib/constitute_helper` via `install.sh` / `update.sh` / `manifest.json`.

Verb naming: `verify-<rule>` (no `forge-internal:` prefix; these are consumer-facing). Same exit semantics as drift-detector (exit 0 clean; exit 2 with stderr findings + stdout JSON report).

### Config: extend `.devforge/constitute.json`

Helper-owns-shape (per `feedback_helper_owns_shape_principle.md`). Add `forcing_functions` block:

```json
{
  "forcing_functions": {
    "magic_enum_duplication": {
      "enabled": true,
      "generated_types_dirs": ["packages/cse-types/src"],
      "allowlist_paths": ["*.log.ts", "**/*.log.ts", "scripts/**", "**/scripts/**", "*.fixture.ts", "**/*.fixture.ts"]
    },
    "cross_layer_imports": {
      "enabled": true,
      "layer_graph": {
        "domain": [],
        "infra": ["domain"],
        "ui": ["domain", "infra"]
      },
      "layer_dirs": {
        "domain": "packages/*/domain/**",
        "infra": "packages/*/infra/**",
        "ui": "packages/*/ui/**"
      }
    },
    "any_with_generated_available": {
      "enabled": true,
      "generated_types_dirs": ["packages/cse-types/src"]
    }
  }
}
```

Populated by `/constitute` wizard (Phase 5 extension — unscheduled until then) or hand-edited into `.devforge/constitute.json` directly for early adoption. Schema validated by `_constitute/_schema.py` (Phase 0 accepts the top-level key; per-rule validation lands with each detector in Phases 1-4).

**Allowlist glob behavior** — `path_in_allowlist` uses `fnmatch.fnmatch`, which does NOT expand `**` recursively across directory separators (unlike shell-glob `**` or `pathlib.Path.match` in Python 3.13+). Always pair a `**/<x>` glob with its top-level twin (`<x>` or `<x>/**`) to cover both nested and top-level matches. The example above lists both forms intentionally. Phase 1 magic-enum scanner doc must repeat this guidance for consumer config-authoring.

### Integration surfaces

Per detector (declared in config, defaulted by family design):

- **Pre-edit briefing** — `/execute-task` brief generation queries the active detectors for advisory inputs. Magic-enum contributes its enum-value inventory (a banlist of strings the agent must `import` instead of duplicate). Cross-layer contributes the layer graph (a directed-import map). `any`-with-generated contributes the list of generated-types dirs the agent should reach for first.
- **Post-edit verify gate** — after the agent edits, run each enabled `constitute_helper verify-<rule>`. Exit-2 = STOP, surface findings to user, do not present "task complete." This is the **load-bearing surface**.
- **Pre-commit hook (optional)** — installed by `/init-forge` if the user confirms. Same verbs, runs on staged diff scope rather than full tree.

Recommendation: verify-gate as the only mandatory surface. Pre-commit is a bonus convenience that the consumer can wire. Pre-edit briefing is an optimization that reduces violations rather than catching them after the fact.

### Allowlist mechanism

Two layers, both required:

1. **Path-glob allowlist** in config — for whole-file or directory exemptions (fixtures, logs, scripts).
2. **Inline comment escape** — `// forcing-fn-ok: <reason>` on the line containing the offending pattern. Helper greps for the marker before flagging. `<reason>` is mandatory free-text so escapes leave an audit trail.

No third escape (no env-var bypass, no "skip if CI" flag). Zero-escape-hatch per CLAUDE.md meta-discipline.

### YAGNI engagement on the "family" abstraction

**Counter-argument considered**: could ship magic-enum standalone, see if the pattern generalizes empirically before designing a family. Detectors 2+3 are named but not yet pulled by a specific real violation.

**Argument for family-shape now**: drift-detector already established the helper-subcommand + exit-semantics + finding-shape pattern. Designing the shared substrate once (config namespace `forcing_functions.<rule>`, shared exit-code constants, shared allowlist machinery, shared JSON report serializer) costs ~20% over a standalone magic-enum implementation and prevents 3× rework if detectors 2+3 ship later.

**Decision**: ship magic-enum first **with family-aware shape**. Phase 0 lays the shared substrate. Phase 1 implements magic-enum on that substrate. Phases 3-4 (cross-layer, `any`-leak) are sketched but **do not implement until magic-enum passes empirical verify on testForge20 + cse-strata-ws-forge wrapper** (Phase 2). Closes YAGNI without painting into corner.

### Relationship to drift-detector

Sister plan, complementary scope. Drift-detector is forge-internal one-shot diff; this is consumer-side recurring gate. Both inherit the exit-2 / stderr-findings / stdout-JSON shape. Land order: drift-detector first (smaller, parent pattern), then this plan extends. Plans do not block each other technically (different code paths), but landing drift-detector first prevents this plan from re-deriving the shared shape on the fly.

---

## Phase 0 — Family-shape substrate

**Owner**: python-engineer.

### Files

- `src/devforge/lib/_constitute/_forcing_functions/__init__.py` — new **nested** subpackage inside the existing `_constitute/` package (not a lib-level sibling like `_research/` or `_constitute/`). Follows the verb-namespaced module split pattern already used within `_constitute/` itself (`_cmds_set.py`, `_cmds_read.py`, `_cmds_render.py`, `_cmds_quality.py`). The `_forcing_functions/` namespace groups all forcing-function verbs + their internal substrate; each detector gets its own sub-subpackage (`_magic_enum/`, `_cross_layer/`, `_any_leak/`).
- `src/devforge/lib/_constitute/_forcing_functions/_shared.py` — substrate:
  - `Finding` dataclass: `rule: str, path: str, line: int, kind: Literal["VIOLATION"], summary: str, fix_hint: str | None`. **Scope**: this `Finding` type is forcing-functions-only. Drift-detector (sibling plan `CONSTITUTION-DRIFT-DETECTOR-PLAN.md`) emits its own findings with `DRIFT` / `MISSING` kinds against a different comparison axis (template canonical vs consumer state). The two finding types do NOT merge — if drift-detector lands first with its own `Finding` shape, leave both distinct; do not retrofit a shared `kind` enum that conflates rule-violation-in-code (this plan) with template-vs-state-drift (sibling plan).
  - `EXIT_CLEAN = 0`, `EXIT_FINDINGS = 2`.
  - `emit_findings(rule: str, findings: list[Finding]) -> int` — prints each finding to stderr in `path:line: <KIND> [<rule>] <summary>` format; prints JSON report `{rule: ..., findings: [...]}` to stdout; returns exit code. The `rule` argument is the top-level JSON grouping key (callers ensure all `Finding.rule` per-element values match; the function does not enforce coherence). On empty findings list: no output, return `EXIT_CLEAN`.
  - `has_inline_escape(file_path: Path, line_number: int) -> bool` — greps for `// forcing-fn-ok:` or `# forcing-fn-ok:` on the same line.
  - `path_in_allowlist(file_path: Path, allowlist_globs: list[str]) -> bool` — fnmatch against config globs.
- `src/devforge/lib/_constitute/_schema.py` — extend with `forcing_functions` top-level key acceptance only (Phase 0 accepts any dict value; no per-rule validation). Per-rule schema validation is deferred to Phases 1-4: each detector defines + validates its own block alongside its implementation. No `_schemas.py` module created in Phase 0.
- `tests/lib/test_constitute_forcing_functions_shared.py` — unit tests:
  - `test_finding_serializes_to_json` (round-trip).
  - `test_emit_findings_exit_code_clean` (empty list → exit 0, no stderr).
  - `test_emit_findings_exit_code_dirty` (one finding → exit 2, stderr cites it).
  - `test_inline_escape_detection` (file with `// forcing-fn-ok: reason` on line N → has_inline_escape returns True).
  - `test_path_allowlist_match` (glob match + non-match).

### Verify

```bash
pytest tests/lib/test_constitute_forcing_functions_shared.py -v
python3 -c "
import sys; sys.path.insert(0, 'src/devforge/lib')
from _constitute._forcing_functions._shared import Finding, EXIT_FINDINGS, EXIT_CLEAN
assert EXIT_CLEAN == 0 and EXIT_FINDINGS == 2
f = Finding(rule='m', path='x.ts', line=1, kind='VIOLATION', summary='s', fix_hint=None)
print(f)
"
```

---

## Phase 1 — Magic-enum detector (pilot)

**Owner**: python-engineer + instruction-author.

### Step 1.1 — Generated-enum inventory parser

`src/devforge/lib/_constitute/_forcing_functions/_magic_enum/_inventory.py`:

- `extract_enum_inventory(generated_dirs: list[Path]) -> dict[str, list[str]]` — returns `{enum_or_union_name: [member_string_values]}`. Parses TypeScript `.d.ts` and `.ts` files via regex-based extractor (no TS AST dependency in Phase 1; upgrade-able to `tree-sitter-typescript` if precision becomes a problem in Phase 2). Recognizes:
  - `enum X { A = 'a', B = 'b' }` → `{X: ['a', 'b']}`.
  - `type X = 'a' | 'b' | 'c'` (string-literal union) → `{X: ['a', 'b', 'c']}`.
  - `const X = { A: 'a' as const } as const` → `{X: ['a']}` (escape hatch for projects using const-object pattern).
- `tests/lib/test_magic_enum_inventory.py` — fixtures cover all three shapes + a non-enum const that should be ignored (`const X = 'literal'`).

### Step 1.2 — Consumer-source scanner

`src/devforge/lib/_constitute/_forcing_functions/_magic_enum/_scanner.py`:

- `scan_for_magic_enum_violations(root: Path, inventory: dict[str, list[str]], allowlist_globs: list[str], generated_dirs: list[Path]) -> list[Finding]`. Walks `*.ts`, `*.tsx`, `*.vue` under root excluding `generated_dirs` and `allowlist_globs`. For each string literal token, checks if its value is in any inventory list. If yes:
  - If the file already imports the enum/union name from a path under `generated_dirs` AND the literal is in a non-RHS position (e.g., log message, error string) — skip (legitimate).
  - If the line has `// forcing-fn-ok:` escape — skip.
  - Else emit `Finding(rule='magic_enum_duplication', kind='VIOLATION', summary="literal 'X' matches <EnumName>.<Member> from <generated-path>; import the enum", fix_hint="import { <EnumName> } from '<generated-path>'; use <EnumName>.<Member>")`.

- `tests/lib/test_magic_enum_scanner.py` fixtures:
  - Violation: file uses `const role = 'SHIPPING'` where `OrgV2AddressType.Shipping = 'SHIPPING'` exists in inventory. Expect 1 finding.
  - Legitimate import: file imports `OrgV2AddressType` and uses `OrgV2AddressType.Shipping`. Expect 0 findings.
  - Legitimate log: file logs `console.log('SHIPPING started')` (string position is non-RHS). Expect 0 findings.
  - Escape: file has `const role = 'SHIPPING'; // forcing-fn-ok: legacy contract`. Expect 0 findings.
  - Allowlist: file `scripts/seed.ts` matches allowlist glob. Expect 0 findings.

### Step 1.3 — Subcommand `verify-magic-enum`

`src/devforge/lib/_constitute/_forcing_functions/_magic_enum/_cmd.py`:

- Register `verify-magic-enum` on `constitute_helper` CLI. Flags:
  - `--root <dir>` (default: cwd) — consumer project root.
  - `--config <path>` (default: `<root>/.devforge/constitute.json`) — config source.
- Logic: read `forcing_functions.magic_enum_duplication` from config; if `enabled: false`, exit 0 silently. Else: extract inventory (Step 1.1), scan source (Step 1.2), emit findings via `_shared.emit_findings`.
- `tests/lib/test_verify_magic_enum_cmd.py` — end-to-end: temp dir with `.devforge/constitute.json` + fake generated dir + fake consumer source. Assert exit code + stderr content + stdout JSON shape.

### Verify

```bash
pytest tests/lib/test_magic_enum_inventory.py tests/lib/test_magic_enum_scanner.py tests/lib/test_verify_magic_enum_cmd.py -v
./src/devforge/lib/constitute_helper verify-magic-enum --help
# Synthetic fixture sanity:
./src/devforge/lib/constitute_helper verify-magic-enum --root tests/fixtures/magic_enum_violation_project
# Expect exit 2 + 1 stderr finding.
```

---

## Phase 2 — Empirical verify on testForge20 + cse-strata-ws-forge wrapper

**Owner**: orchestrator (manual triage).

### Procedure

1. Run `verify-magic-enum` against `~/Projects/testForge20` after seeding its `.devforge/constitute.json` with a `forcing_functions.magic_enum_duplication` block pointing at its `pkg-cse-types/` (or equivalent generated dir).
2. Capture findings. Triage each:
   - **True positive** (real magic-string duplication) — keep.
   - **False positive** — categorize: (a) detector bug → patch Phase 1; (b) legitimate exception → add to allowlist or document the inline-escape pattern.
3. Stop criterion: false-positive rate ≤ 5% on the triaged sample. If above, patch detector before extending family.
4. Repeat against `cse-strata-ws-forge` wrapper project.
5. Land conclusions in `EMPIRICAL-VERIFY-MAGIC-ENUM-<date>.md` (one-shot log; auto-memory-able after).

### Verify

```bash
# Ledger exists + records the FP rate + records the seed-violation capture:
ls EMPIRICAL-VERIFY-MAGIC-ENUM-*.md
grep -E "false.positive.rate" EMPIRICAL-VERIFY-MAGIC-ENUM-*.md
grep -E "OrgV2AddressType\.Shipping|SHIPPING.*caught" EMPIRICAL-VERIFY-MAGIC-ENUM-*.md
# Re-run the detector against testForge20 to reproduce a clean / known finding set:
./src/devforge/lib/constitute_helper verify-magic-enum --root ~/Projects/testForge20
# Expect exit 2 + the violations recorded in the ledger.
```

Assertion thresholds (all required to pass Phase 2):
- Ledger committed at `EMPIRICAL-VERIFY-MAGIC-ENUM-<date>.md`.
- False-positive rate ≤ 5% recorded in ledger.
- Seed violation (`OrgV2AddressType.Shipping = 'SHIPPING'`) confirmed caught.

---

## Phase 3 — Cross-layer import detector

**Owner**: python-engineer + instruction-author.

**Do not start until Phase 2 closes clean.**

### Files (skeleton)

- `src/devforge/lib/_constitute/_forcing_functions/_cross_layer/_graph.py` — load `layer_graph` + `layer_dirs` from config; build a directed allowed-import map.
- `src/devforge/lib/_constitute/_forcing_functions/_cross_layer/_scanner.py` — walk source; for each `import ... from '<path>'`, resolve source file's layer + target path's layer; if edge not in allowed-import map, emit `Finding(rule='cross_layer_imports', kind='VIOLATION', ...)`.
- `src/devforge/lib/_constitute/_forcing_functions/_cross_layer/_cmd.py` — register `verify-cross-layer-imports` subcommand.
- Tests mirror Phase 1 structure.

### Verify

```bash
pytest tests/lib/test_cross_layer_graph.py tests/lib/test_cross_layer_scanner.py tests/lib/test_verify_cross_layer_imports_cmd.py -v
./src/devforge/lib/constitute_helper verify-cross-layer-imports --help
# Empirical pass mirrors Phase 2 protocol — ledger at EMPIRICAL-VERIFY-CROSS-LAYER-<date>.md:
ls EMPIRICAL-VERIFY-CROSS-LAYER-*.md
grep -E "false.positive.rate" EMPIRICAL-VERIFY-CROSS-LAYER-*.md
```

Same ≤ 5% false-positive threshold as Phase 2 before unlocking Phase 4.

---

## Phase 4 — `any`-with-generated-available detector

**Owner**: python-engineer + instruction-author.

**Do not start until Phase 3 closes clean.**

### Files (skeleton)

- `src/devforge/lib/_constitute/_forcing_functions/_any_leak/_scanner.py` — scan `*.ts` / `*.tsx` / `*.vue` for `: any` (typed annotation), `as any` (cast), or `<any>` (generic). For each hit, check if the containing file has any import statement whose path resolves under any `generated_types_dirs` from config. If yes, emit `Finding(rule='any_with_generated_available', kind='VIOLATION', summary="any-typed in file with access to generated types; replace with the appropriate generated type or narrow explicitly")`.
- `src/devforge/lib/_constitute/_forcing_functions/_any_leak/_cmd.py` — register `verify-any-leak` subcommand.

### Verify

```bash
pytest tests/lib/test_any_leak_scanner.py tests/lib/test_verify_any_leak_cmd.py -v
./src/devforge/lib/constitute_helper verify-any-leak --help
# Empirical pass mirrors Phase 2 protocol — ledger at EMPIRICAL-VERIFY-ANY-LEAK-<date>.md:
ls EMPIRICAL-VERIFY-ANY-LEAK-*.md
grep -E "false.positive.rate" EMPIRICAL-VERIFY-ANY-LEAK-*.md
```

Same ≤ 5% false-positive threshold as Phase 2.

---

## Phase 5 — Integration with /execute-task + optional pre-commit hook

**Owner**: instruction-author + python-engineer.

**Do not start until Phase 1 passes its Verify block AND Phase 2 empirical verify records a false-positive rate ≤ 5%.** Subsequent detectors (Phases 3, 4) extend the gate as they land, but Phase 5 wiring is bounded by the Phase 1+2 gate alone — runtime opt-in via config is a property of the helper, not justification for softening the implementation gate.

**Precondition check (run before Phase 5 begins):**

```bash
# Confirm execute-task spec location — PLAN-COMMAND-REDESIGN (memory-only reference;
# no file-level plan in repo root as of plan draft) may have moved or renamed it.
ls src/commands/execute-task/main.md 2>/dev/null || ls src/commands/execute-task/*.md 2>/dev/null
# If neither resolves: check repo-root CLAUDE.md active-plans table for the canonical
# execute-task spec path post-redesign. Do not assume src/commands/execute-task/main.md.
```

### Files

- `src/commands/execute-task/main.md` (or whichever current execute-task spec is canonical post-PLAN-COMMAND-REDESIGN) — append a verify-gate step after agent-edit completion + before user-presentation. Step invokes `constitute_helper verify-<rule>` for each rule with `enabled: true` in `.devforge/constitute.json`. Exit 2 = STOP; capture the helper's **stdout JSON** (the programmatic finding report — `{rule, findings: [...]}`) and relay it to the user as a fenced JSON code block; stderr lines are human-readable supplementary output and MUST NOT be the source of relayed findings (the `path:line: KIND` prefix is ambiguous when `path` contains `:`, per `_shared.emit_findings` Known limitations). Do not declare task complete.
- `src/commands/execute-task/references/forcing-functions-gate.md` — reference doc explaining the gate, the verbs, the exit semantics, and how to triage findings.
- `src/files/git-hooks/pre-commit-forcing-functions.sh` (new template) — installable pre-commit hook script. `install.sh` / `update.sh` does NOT auto-install it; `/init-forge` STEP 0 offers it after the wizard captures `forcing_functions` config.
- `src/commands/init-forge/main.md` — extend STEP 0 to surface the pre-commit option with a single AskUserQuestion (per `feedback_askuserquestion_single_line_only.md` single-line constraint).

### Verify

```bash
# Helper-side cross-check:
grep -nE "forcing.functions" src/commands/execute-task/main.md
grep -nE "pre-commit-forcing-functions" src/commands/init-forge/main.md
grep -nE "forcing_functions" src/devforge/lib/_constitute/_schema.py
# Real integration: re-run /execute-task on a testForge20 task that touches an enum-known surface;
# verify the gate fires when the agent writes a magic-string and STOPs before user-presentation.
```

---

## Phase 6 — Documentation + constitution cross-reference

**Owner**: instruction-author.

### Files

- `CHANGELOG.md` — entries for each shipped detector + the family substrate. Cross-ref `feedback_release_docs.md`.
- Repo-root `CLAUDE.md` (at `/Users/mykolakudlyk/Projects/ai-dev-team-forge/CLAUDE.md`) — extend the "Where to find what" table with a row for the consumer-side `verify-<rule>` verbs. Distinct from the drift-detector forge-internal row. **Do NOT edit `src/CLAUDE.md`** — that path is the consumer-shipped template with `{{PROJECT_NAME}}` substitutions; forge-internal helper documentation belongs in the repo-root surface only.
- `src/constitution.md` — append backing-detector lines to the universal sections (only — not to project-specific sections, which would create per-project drift):
  - §3.5 ("No magic values") gains **two** backing-detector lines, one for `verify-magic-enum`, one for `verify-any-leak`. Suggested wording: *"Backed by `constitute_helper verify-magic-enum` when `forcing_functions.magic_enum_duplication.enabled = true` in `.devforge/constitute.json` — prose violations surface as exit-2 findings during /execute-task verify-gate."* + *"Backed by `constitute_helper verify-any-leak` when `forcing_functions.any_with_generated_available.enabled = true` — `any` annotations in files importing from generated-types dirs surface as exit-2 findings."*
  - §3.6 ("Design Principles" — SOLID universal block) gains one backing-detector line for `verify-cross-layer-imports`.
  - **Do NOT append to §3.1** (project-specific Type Safety) — its body is populated per-consumer by `/constitute`. Universal-detector cross-references in project-specific sections would mislead future sessions about which sections are framework-owned vs project-owned.
- `DEVELOPMENT-STATUS.md` — single-line entry under "Active commands / helpers".

### Verify

```bash
grep -nE "verify-magic-enum|verify-cross-layer-imports|verify-any-leak" CLAUDE.md CHANGELOG.md src/constitution.md DEVELOPMENT-STATUS.md
```

Cross-check per `feedback_cross_check_after_every_change.md`: grep for every helper name across the entire codebase; ensure no dangling reference, no contradictory text in other files, no missed derivative location.

---

## When resuming work

1. Read this plan top-to-bottom.
2. Cross-read `CONSTITUTION-DRIFT-DETECTOR-PLAN.md` (pattern parent) + `CONSTITUTION-STRENGTHENING-PLAN.md` (the canonical rule bodies these detectors back).
3. Verify state of each phase on-disk. Each check below mirrors the corresponding phase's `### Verify` block; a phase is "done" only when its check returns the success signal (not merely when a directory or file exists).

   ```bash
   # Phase 0 — substrate importable:
   python3 -c "import sys; sys.path.insert(0,'src/devforge/lib'); from _constitute._forcing_functions._shared import Finding, EXIT_CLEAN, EXIT_FINDINGS; print('Phase 0 substrate ok')" 2>/dev/null || echo "Phase 0 not done"

   # Phase 1 — magic-enum verb CLI-wired (not just present in source text):
   ./src/devforge/lib/constitute_helper verify-magic-enum --help >/dev/null 2>&1 && echo "Phase 1 wired" || echo "Phase 1 not wired"

   # Phase 2 — ledger exists AND records FP rate AND records seed-violation capture:
   ls EMPIRICAL-VERIFY-MAGIC-ENUM-*.md 2>/dev/null \
     && grep -lE "false.positive.rate" EMPIRICAL-VERIFY-MAGIC-ENUM-*.md \
     && grep -lE "OrgV2AddressType\.Shipping|SHIPPING.*caught" EMPIRICAL-VERIFY-MAGIC-ENUM-*.md

   # Phase 3 — cross-layer verb CLI-wired AND empirical ledger records FP rate:
   ./src/devforge/lib/constitute_helper verify-cross-layer-imports --help >/dev/null 2>&1 && echo "Phase 3 wired" || echo "Phase 3 not wired"
   ls EMPIRICAL-VERIFY-CROSS-LAYER-*.md 2>/dev/null \
     && grep -lE "false.positive.rate" EMPIRICAL-VERIFY-CROSS-LAYER-*.md

   # Phase 4 — any-leak verb CLI-wired AND empirical ledger records FP rate:
   ./src/devforge/lib/constitute_helper verify-any-leak --help >/dev/null 2>&1 && echo "Phase 4 wired" || echo "Phase 4 not wired"
   ls EMPIRICAL-VERIFY-ANY-LEAK-*.md 2>/dev/null \
     && grep -lE "false.positive.rate" EMPIRICAL-VERIFY-ANY-LEAK-*.md

   # Phase 5 — execute-task gate + init-forge wizard + schema validator all present:
   grep -nE "forcing.functions" src/commands/execute-task/main.md \
     && grep -nE "pre-commit-forcing-functions" src/commands/init-forge/main.md \
     && grep -nE "forcing_functions" src/devforge/lib/_constitute/_schema.py

   # Phase 6 — docs landed across all four surfaces (matches Phase 6 Verify block exactly):
   grep -nE "verify-magic-enum|verify-cross-layer-imports|verify-any-leak" CLAUDE.md CHANGELOG.md src/constitution.md DEVELOPMENT-STATUS.md
   ```
4. For each unfinished phase, dispatch the named owner with a complete brief per `feedback_no_underspecification_when_delegating.md`. Follow every python-engineer dispatch with a python-reviewer dispatch per `feedback_dual_agent_verify_command_statements.md`. Follow every instruction-author dispatch with an instruction-reviewer dispatch.
5. **Phase 2 gates Phases 3-4**. Do not implement cross-layer or any-leak before magic-enum passes empirical verify on at least one real consumer (testForge20 ideally; cse-strata-ws-forge wrapper as a second confirm).
6. **Phase 5 is opt-in per detector**. A consumer that only enables magic-enum gets the magic-enum gate wired; the others stay inactive. Helper-owns-shape ensures the gate iterates only the enabled rules.

## Out of scope (this plan)

- **Automatic fix application** — every detector is read-only. Findings carry a `fix_hint` field for human / LLM triage; no in-place rewrite.
- **Schema/contract drift detector** (openapi-typescript handrolled-DTO mismatch) — deferred. Needs per-stack schema parser. Pull when a real violation surfaces.
- **Test-presence detector** — deferred. High false-positive risk on type-only exports.
- **Literal-archaeology / 6-value intent classification** — lives in `04-PR-REVIEW-PLAN.md` at the PR-review surface, not this plan's pre-commit / verify-gate surface.
- **Stale JSDoc detector** — deferred; high false-positive on TS where types carry the contract.
- **CBM-graph-based detectors** (e.g., "dead exports", "unused functions") — out of scope; CBM has its own query verbs and runs at a different cadence than verify-gate.
- **Cross-language / non-TS support** — Phases 1-4 are TS-centric (the seed §3.5 magic-value violation surfaced in TS code touching a generated enum). Python / Go / Rust support is future-work driven by an actual cross-language consumer pulling it.

## Related plans

- `CONSTITUTION-DRIFT-DETECTOR-PLAN.md` — sibling. Forge-internal one-shot template drift check. Established the helper-subcommand + exit-2 + stderr-findings + stdout-JSON pattern this plan extends.
- `CONSTITUTION-STRENGTHENING-PLAN.md` — closed 2026-05-16. Strengthened the canonical universal-rule bodies. Detectors in this plan are the mechanical backing for those strengthened rules.
- `COMMAND-VERIFY-GATES-PLAN.md` — sibling. Converts `## Verify` blocks in done-commands from prose to shell-fact. Same facts-first philosophy applied to command specs instead of constitution rules.
- `04-PR-REVIEW-PLAN.md` — sibling. Literal-archaeology / scope-drift / blast-radius live there at the PR-review surface; complementary to the verify-gate surface this plan targets.
- `PLAN-COMMAND-REDESIGN` (referenced by `feedback_18_may_patches_delivered.md` as the parity gate for Gap B/C) — Phase 5 of this plan touches `/execute-task` spec; coordinate with whatever execute-task version that redesign produces.
