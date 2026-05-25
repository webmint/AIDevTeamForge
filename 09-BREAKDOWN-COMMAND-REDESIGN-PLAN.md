# 09 — /breakdown Command Redesign Plan

**Status**: ✅ SHIPPED 2026-05-25 on `develop-2.0-init` (working-tree, not yet committed). All 8 execution phases DONE; 235 breakdown helper tests + 610 across breakdown/plan/specify; e2e chain validated. Remaining: interactive LLM-driven `/breakdown` run = user-driven (testForge20 re-install + live session). Re-read only if maintaining the feature.
**Author handoff target**: `/execute-task` (07-EXECUTE-TASK-REDESIGN-PLAN.md) — breakdown is its hard upstream precondition; 07's read contract was re-pointed (Phase 7) at `breakdown-handoff.json`.

## Driver

`/breakdown` is MISSING from `src/commands/` (per 2026-05-21 audit; only an old pre-pivot draft survives at `src/_pending/commands/breakdown.md`). It is the one chain hop between `/plan` and `/execute-task`. The plan→breakdown **producer** is already shipped (`plan_helper finalize-handoff` → `specs/NNN/plan-handoff.json`, schema `src/devforge/lib/_plan/handoff_schema.py`); `/breakdown` is its **consumer**, and per the "consumer obeys producer" principle it must conform to that producer's shape. This plan builds `/breakdown` aligned with the full redesigned chain (`/research` → `/discover` → `/specify` → `/plan`), reusing their structural patterns verbatim where they apply.

## Context in the workflow

```
/research (optional) → /specify → /plan → /breakdown → /execute-task → /review → /verify → /summarize → /finalize
```

`/breakdown` runs AFTER plan approval, BEFORE task execution. It takes an approved `plan.md` (+ its sibling `plan-handoff.json`) and produces ordered, atomic, agent-assigned tasks with verifiable contracts.

### What is already built (read contracts — do NOT rebuild)

| Artefact | Path | Role for breakdown |
|---|---|---|
| Plan→breakdown producer | `plan_helper finalize-handoff` | Writes `specs/NNN/plan-handoff.json` breakdown consumes |
| Plan handoff schema | `src/devforge/lib/_plan/handoff_schema.py` | `BreakdownSeeds` (layer_map, key_design_decisions, file_impact, doc_impact, risks, specialist_consultation, dependencies) + `Provenance` → sibling specify handoff. `handoff_kind="plan"`, `SCHEMA_VERSION="1.0"` |
| Helper-owns-shape pattern | `plan_helper.py` (10 verbs) + `tests/lib/test_plan_helper.py` (94 tests) | The exact verb/test/launcher conventions breakdown_helper mirrors |
| POSIX launcher convention | `src/devforge/lib/plan_helper` (sh launcher) + `plan_helper.py` | breakdown ships `breakdown_helper` launcher + `breakdown_helper.py` + `_breakdown/` |
| Consumer-reads-producer reference | `src/devforge/lib/_specify/_cmds_handoff.py:cmd_import_handoff` / `cmd_find_handoffs` | Pattern for `read-plan-handoff` (load sibling JSON, validate kind, render) |
| Agent-assignment table (source) | `src/_pending/commands/_agent-assignment.md` | File-layer→agent map; inlined into breakdown main.md (see Decision 3) |
| Storage-rules task format | `src/devforge/storage-rules.md` §"Task File Format" (lines 83-135) | Human `tasks/*.md` shape (`**Agent**:` line, Contracts Expects/Produces, Done-when) |
| Execute-task read contract | `07-EXECUTE-TASK-REDESIGN-PLAN.md` lines 45-54 | Currently assumes YAML frontmatter `agent:` — **must be re-pointed at breakdown-handoff.json** (Decision 1; 07 only DRAFTED, free edit) |

## Settled design decisions (confirmed with user 2026-05-24)

### Decision 1 — Machine contract carrier: sibling `breakdown-handoff.json`, NOT YAML frontmatter

`/breakdown` emits two artefacts: human-readable `tasks/*.md` (storage-rules format preserved, including the `**Agent**:` line) AND a schema-validated sibling `specs/NNN/breakdown-handoff.json` carrying the machine-readable per-task contract (agent, depends_on, touched_files, expects, produces, ac_addressed, review_checkpoint). `/execute-task` reads the JSON, not the markdown.

**Why** (over the YAML-frontmatter assumption in 07): every existing chain hop carries its machine contract in a schema-validated sibling JSON (research→specify `handoff.json`, specify→plan `handoff.json`, plan→breakdown `plan-handoff.json`); the human docs (`spec.md`, `plan.md`) stay pure markdown with zero machine frontmatter. Frontmatter would make breakdown the one inconsistent hop, would duplicate `agent`/`files` already stated in the task body (drift), and would skip the dataclass `__post_init__` validation the chain relies on. JSON-in-frontmatter is a non-starter (Claude Code expects YAML frontmatter; JSON inside `---` is non-standard/fragile).

**Cost**: `07-EXECUTE-TASK-REDESIGN-PLAN.md` lines 45-54 (+ 50, 168) currently document the read contract as YAML frontmatter `agent:` / `touched_files:`. Since 07 is DRAFTED-not-shipped, this plan's Phase 7 edits 07 to point at `breakdown-handoff.json`. (Cross-ref tracked — see Phase 7.)

### Decision 2 — Producer built now; execute-task consumer conforms later

Build `breakdown_helper finalize-handoff` + `_breakdown/handoff_schema.py` in this plan even though `/execute-task` does not exist yet. Identical to how `plan_helper finalize-handoff` shipped ahead of its `/breakdown` consumer. The producer defines the shape; the future consumer obeys it.

### Decision 3 — Architect consultation: mandatory + scoped at the decomposition phase

`/breakdown` Phase 2 (decomposition) ALWAYS invokes the `architect` agent (orchestrator-mediated specialist relay, identical mechanism to `/plan` Phase 1.3) with a FIXED sub-question set scoped to the genuinely-architectural layer: (1) task atomicity boundaries / bundling, (2) dependency ordering & direction, (3) contract-chain integrity. Agent ASSIGNMENT stays orchestrator-direct via the inlined `_agent-assignment` table (a lookup, not judgment); the architect only *validates* design-decision task assignments.

**Why** "mandatory + scoped" and not orchestrator-direct: the decomposition layer (atomic-task boundaries, ordering, Expects/Produces contracts) is net-new judgment the plan did NOT produce — so it is not re-derivation of the plan's own architect output, killing the redundancy objection. "Mandatory + fixed sub-questions" means scoping governs *what is asked*, never *whether the architect is called* — escape-hatch-free, structurally identical to `/plan`. Corrects the stale "architect owns /plan and /breakdown" framing: per `src/commands/plan/main.md`, the orchestrator authors all artefacts and the architect is a consulted specialist at mandatory hooks — there is no command "ownership." (Memory `project_architect_role_scope.md` body already reflects this; index line corrected 2026-05-24.)

### Sub-decisions (orchestrator-chosen; flagged as open questions below where the user may redirect)

- **Monolithic `main.md`** — no `references/` dir, matching all four redesigned commands (research/discover/specify/plan are all single-file). The `_agent-assignment` table is **inlined permanently** into breakdown's main.md (see OQ-3 — breakdown is the sole agent-assignment owner since `/fix` + `/refactor` are slated for removal).
- **Greenfield vs existing-codebase task ordering** — retain both branches from the old draft (Phase 1 of main.md), updated to read from `plan-handoff.json` seeds rather than re-scanning the spec.
- **Contract-chain integrity is a helper forcing-function** (`verify-contract-chain`), not LLM prose — mechanical, walks the task set, reports orphan `Produces` / unsatisfied `Expects`. Consistent with the forcing-functions philosophy (01-CONSTITUTION-FORCING-FUNCTIONS) and `feedback_helper_owns_contract_filesystem_forcing`.

## Open questions — RESOLVED 2026-05-24

- **OQ-1 — handoff filename**: ✅ `breakdown-handoff.json`, `handoff_kind="breakdown"` (kind-symmetric with `plan-handoff.json`).
- **OQ-2 — plan status flip**: ✅ `/breakdown` flips plan `Draft → Approved` via `check-status-and-flip`, mirroring how `/plan` flips the spec; no new state. (`plan/main.md` Phase 4: plan "stays Draft until /breakdown runs.")
- **OQ-3 — agent-assignment table placement**: ✅ **Inline into breakdown `main.md` permanently** — `/fix` + `/refactor` (the only other prospective consumers) are **planned for removal**, so `/breakdown` is the sole agent-assignment owner. No shared-reference file, no later extraction. `src/_pending/commands/_agent-assignment.md` is the inline source; it is NOT promoted as a standalone reference.
- **OQ-4 — task-file completion-notes block**: ✅ breakdown emits the empty completion-notes skeleton — it is the read contract `/execute-task` fills.
- **OQ-5 — testForge20 e2e gating**: ✅ this plan blocks DONE on Phase 8 e2e (mirrors 07 Phase 11 discipline).

## Architecture / file inventory

New files:

| File | Purpose |
|---|---|
| `src/devforge/lib/_breakdown/__init__.py` | Package marker |
| `src/devforge/lib/_breakdown/handoff_schema.py` | Dataclass schema for `breakdown-handoff.json` (pure records, `__post_init__` validation, stdlib-only, Py3.8+, no I/O) |
| `src/devforge/lib/breakdown_helper.py` | Verb implementations + argparse CLI |
| `src/devforge/lib/breakdown_helper` | POSIX sh launcher (copy of `plan_helper` launcher, name-swapped) |
| `tests/lib/test_breakdown_helper.py` | Tests; round-trip via real producers (`plan_helper finalize-handoff` for `read-plan-handoff`; helper-rendered task files for `finalize-handoff`/`verify-contract-chain`) |
| `src/commands/breakdown/main.md` | Slash-command spec |

Modified files:

| File | Change |
|---|---|
| `scripts/emitters/claude.py` | `_PROMOTED` tuple (line 55) += `"breakdown"` |
| `src/devforge/storage-rules.md` | Add `breakdown-handoff.json` to the storage tree + task-format note (reconcile with Decision 1) |
| `src/CLAUDE.md` | Command catalog `/breakdown` entry already present (line ~) — verify accuracy post-build; no phase-paragraph (per 08-CLAUDE-MD-COMMAND-TRIM) |
| `07-EXECUTE-TASK-REDESIGN-PLAN.md` | Re-point read contract (lines 45-54, 50, 168) from YAML frontmatter → `breakdown-handoff.json` |
| `CHANGELOG.md`, `DEVELOPMENT-STATUS.md` | Release propagation (`feedback_release_docs`) |

## Schema design — `_breakdown/handoff_schema.py`

Mirror `_plan/handoff_schema.py` conventions exactly (constants block, `_require_nonempty`/`_require_in_enum` helpers, row dataclasses, co-vary invariant on provenance).

```
SCHEMA_VERSION = "1.0"
HANDOFF_KIND   = "breakdown"
_VALID_UPSTREAM_HANDOFF_KIND = ("plan",)
REVIEW_CHECKPOINT_ENUM        = (True, False)   # bool

@dataclass TaskRow:
    number: str               # zero-padded "001"
    title: str                # imperative
    agent: str                # must match an agent name; validated non-empty only (roster not hardcoded)
    depends_on: List[str]     # task numbers, may be empty
    blocks: List[str]         # task numbers, may be empty
    touched_files: List[str]  # file paths, may be empty
    expects: List[str]        # contract preconditions (semantic identifiers)
    produces: List[str]       # contract postconditions
    ac_addressed: List[str]   # AC ids, ≥1 enforced by verify-ac-coverage (not the schema)
    doc_refs: List[str]       # ≤2, may be empty
    review_checkpoint: bool

@dataclass Provenance:        # identical pattern to _plan; upstream = sibling plan-handoff.json
    upstream_handoff_path: Optional[str] = None
    upstream_handoff_kind: Optional[str] = None   # "plan" or None (co-vary)
    plan_path: Optional[str] = None
    spec_path: Optional[str] = None

@dataclass Breakdown:         # top-level (parallels _plan.Handoff)
    schema_version: str
    handoff_kind: str         # constant "breakdown"
    tasks_dir: str            # specs/NNN/tasks/
    breakdown_completed_at: str
    provenance: Provenance
    tasks: List[TaskRow]
    additions: List[str]      # files discovered not in plan/spec
    dependency_graph: str     # raw graph text from README (best-effort, may be "")
```

Validation is mechanical only (non-empty required strings, list-type checks, enum/kind constants, co-vary). Placeholder detection (rows like `[path]`, `(none)`) is the producer's responsibility, not the schema's — identical to `_plan`.

## Helper verb inventory — `breakdown_helper`

Mirrors `plan_helper`'s 10-verb surface. Helper owns shape; LLM composes values.

| Verb | Role | Mirrors |
|---|---|---|
| `pick-plan [path]` | Resolve which `plan.md` to break down; auto-pick by mtime; validate it is a `plan.md` (not dir) | `plan_helper pick-spec` |
| `render-pick-summary <plan-path>` | Deterministic preview block (plan path, status, file-impact count, risk count, mtime) | `plan_helper render-pick-summary` |
| `list-plans` | All `specs/*/plan.md` by mtime desc, one line each | `plan_helper list-specs` |
| `check-status-and-flip <plan-path>` | Flip plan `Draft → Approved` (OQ-2); five state tokens | `plan_helper check-status-and-flip` |
| `read-plan-handoff <plan-path>` | **CONSUMER**: load sibling `plan-handoff.json`, validate `handoff_kind=="plan"`, render seeds (layer_map/file_impact/decisions/deps/risks) for decomposition. Sentinel `no-handoff` → LLM falls back to reading `plan.md` directly (no duplicate Python parser) | `specify_helper import-handoff` |
| `render-findings-from-plan <plan-path> [spec-path]` | Intermediate enumeration forcing every plan file-impact row + every spec AC to be acknowledged before tasks are written | `plan_helper render-findings-from-spec` |
| `render-task-file` | Emit one task `.md` skeleton (storage-rules shape; helper owns headings) | (new; helper-owns-shape) |
| `render-tasks-index` | Emit `tasks/README.md` skeleton (dep-graph fence + index table + additions + risk + checkpoints) | (new) |
| `render-consultation-block` | Specialist Consultation provenance skeleton (verdict enum) | `plan_helper render-consultation-block` |
| `verify-contract-chain <tasks-dir>` | **Forcing function**: parse all task Expects/Produces, report orphan Produces / unsatisfied Expects | (new; forcing-function) |
| `verify-ac-coverage <tasks-dir> <spec-path>` | **Forcing function**: every spec AC addressed by ≥1 task; report uncovered ACs | (new; forcing-function) |
| `finalize-handoff <tasks-dir|plan-path>` | **PRODUCER**: parse `tasks/*.md` + README → `breakdown-handoff.json` (atomic write); provenance → sibling `plan-handoff.json` | `plan_helper finalize-handoff` |
| `render-execute-task-handoff <plan-path>` | Deterministic manual next-step block → `/execute-task NNN` (numerically-lowest first task; restart-Claude-Code reminder); derives `tasks/` from plan-dir internally | `plan_helper render-breakdown-handoff` |

## Command spec — `src/commands/breakdown/main.md` phase structure

Phase numbering mirrors `/plan` so the chain reads consistently.

- **PHASE 0a — Plan resolution**: `pick-plan` → `render-pick-summary` → `AskUserQuestion` ("Process this plan?" yes/pick-other/cancel). `pick-other` → `list-plans`.
- **PHASE 0a.5 — Upstream handoff (consumer core)**: `read-plan-handoff`. Renders the plan seeds verbatim as the authoritative decomposition input. `no-handoff` → fall back to reading `plan.md` directly.
- **PHASE 0b — Status check + flip**: verify spec is Approved AND plan is approved; `check-status-and-flip` (OQ-2). Constitution guard (`_Run /constitute to populate_` → stop).
- **PHASE 0 — Context load**: constitution, CLAUDE.md, MEMORY.md, supporting docs (research/data-model/contracts if present). Source Root resolution.
- **PHASE 1 — Deep file analysis**: existing-codebase vs greenfield branches (retained from old draft), driven by `plan-handoff` `file_impact` + `layer_map` seeds.
- **PHASE 1.5 — Findings from Plan** (REQUIRED intermediate): `render-findings-from-plan`, fill coverage markers inline. Forcing-function gate before any task is written.
- **PHASE 2 — Decomposition (MANDATORY scoped architect)**: invoke `architect` (Decision 3) with fixed sub-questions (atomicity / ordering / contract-chain); orchestrator-mediated specialist relay; agent assignment via inlined `_agent-assignment` table; bundle-mechanical-tasks rule.
- **PHASE 3 — Write tasks**: `render-task-file` per task + `render-tasks-index`; `render-consultation-block` into README provenance.
- **PHASE 3.5 — Integrity gates**: `verify-contract-chain` + `verify-ac-coverage`; surface orphans/uncovered-ACs; revise or flag in README Risk Assessment.
- **PHASE 4 — User approval** (HARD GATE): summary + `AskUserQuestion` (approve/request-changes/cancel).
- **PHASE 5 — Finalize**: `finalize-handoff` → `breakdown-handoff.json` (non-blocking best-effort, mirror plan); `render-execute-task-handoff` (guaranteed human bridge); closing confirmation.

## Execution phases (build order)

Each phase leaves the system buildable + tested. Test-immediately-after-write applies to every helper function (`feedback_test_first_python_helpers`).

### Phase 0 — Schema substrate ✅ DONE 2026-05-24
`_breakdown/__init__.py` + `_breakdown/handoff_schema.py` + tests (construct valid/invalid Breakdown/TaskRow/Provenance; enum/kind/co-vary rejection). Added `REVIEW_CHECKPOINT_ENUM`. python-reviewer pass applied (nonempty-before-enum on `upstream_handoff_kind`; nonempty guards on `plan_path`/`spec_path`). `_plan` template intentionally NOT modified (out of scope). 74 tests green.
**Verify**: `python -m pytest tests/lib/test_breakdown_helper.py` → 74 passed.

### Phase 1 — Consumer + resolution verbs ✅ DONE 2026-05-24
`pick-plan`, `render-pick-summary`, `list-plans`, `check-status-and-flip`, `read-plan-handoff` + `breakdown_helper.py` (~700 lines, monolithic like `plan_helper.py`) + POSIX launcher. `read-plan-handoff` round-trips a REAL `plan_helper finalize-handoff` output (genuine integration test, reviewer-confirmed). python-reviewer pass applied (double-dash dependency render fix; split misleading "wrong-kind" vs "wrong schema_version" messages; tightened round-trip assertions). `plan_helper`/`_plan` untouched.
**Verify**: `python -m pytest tests/lib/test_breakdown_helper.py` → 115 passed.

### Phase 2 — Decomposition-support verbs ✅ DONE 2026-05-24
`render-findings-from-plan` (markers `[TASK COVERAGE: ?]` / `[ADDRESSED BY: ?]`), `render-task-file` (storage-rules §Task File Format skeleton incl. empty Completion Notes per OQ-4), `render-tasks-index`, `render-consultation-block` (byte-identical to plan_helper's). python-reviewer pass applied (distinct Done-When placeholder texts matching storage-rules; +2 missing-path tests). `datetime.utcnow()` deprecation DEFERRED (codebase-wide pattern, warning-not-error on current runtime — fix in a separate codebase-wide change).
**Verify**: `python -m pytest tests/lib/test_breakdown_helper.py` → 165 passed.

### Phase 3 — Integrity forcing-functions ✅ DONE 2026-05-25
`verify-contract-chain` (normalized-bullet match: orphan Produces / unsatisfied Expects, advisory; violations→exit2 stdout, setup-error→exit2 stderr), `verify-ac-coverage` (every spec AC referenced by ≥1 task; uncovered→exit2; zero-AC spec→exit0 `no-acs`). Reuses `_parse_acs`. python-reviewer pass applied (boundary docstring; no-Contracts test; `\b` on AC-ref regex). Reviewer confirmed bracket-placeholder detection is start-anchored (real contracts with trailing `[...]` not dropped) + AC-1/AC-12 no collision.
**Verify**: `python -m pytest tests/lib/test_breakdown_helper.py` → 190 passed.

### Phase 4 — Producer + next-step verbs ✅ DONE 2026-05-25
`finalize-handoff <plan-path>` (parses `tasks/*.md` + README → `<plan-dir>/breakdown-handoff.json`, atomic write, exit 0/1/2; provenance → sibling `plan-handoff.json` kind="plan"; placeholder agent → exit 2 naming file), `render-execute-task-handoff <plan-path>` (manual next-step block, numerically-lowest first task, restart reminder). Round-trip reconstructs the JSON through `_breakdown.handoff_schema` dataclasses to prove schema-validity; provenance round-trips REAL `plan_helper finalize-handoff`. python-reviewer pass applied incl. **HIGH** fix (`_CONTEXT_DOCS_RE` newline-swallow → phantom `## Files` doc_ref) + robust `startswith("[")` placeholder guard + numeric first-task selection. 13 verbs total.
**Verify**: `python -m pytest tests/lib/test_breakdown_helper.py` → 232 passed.

### Phase 5 — Launcher + CLI wiring + install ✅ DONE 2026-05-25
Launcher + per-verb subparser wiring landed incrementally across P1–P4. Ship surface confirmed (`src/devforge/lib/{breakdown_helper (exec), breakdown_helper.py, _breakdown/}` — carried by install's `cp -R src/devforge/lib`). Launcher `--help` dispatches all 13 verbs. Real `.devforge/lib/` install smoke deferred to Phase 8 (needs testForge20).
**Verify**: `python -m pytest tests/lib/test_breakdown_helper.py tests/lib/test_plan_helper.py` → 326 passed (232 breakdown + 94 plan; zero regressions, cross-helper imports clean).

### Phase 6 — Command spec `main.md` ✅ DONE 2026-05-25
`src/commands/breakdown/main.md` authored via the triple-agent loop: `instruction-author` wrote it (mirroring `plan/main.md`), `instruction-reviewer` + `claude-code-guide` reviewed. 11 phases + inlined Agent Assignment table (OQ-3) + IMPORTANT RULES. claude-code-guide: conventions all current, parity-confirmed vs `/plan`, zero findings. instruction-reviewer: 8 findings ALL fixed — incl. 2 HIGH (`## Additions to Plan` → `## Additions to Spec` to match the helper; present-tense `/execute-task` claims → forward-reference framing), `<spec-path>` derivation made explicit, full `verify-contract-chain` success token. All `/execute-task` mentions are now policy/producer-framing/forward-ref only (no present-tense behavioral claims about the unbuilt consumer).
**Verify**: reviewer + claude-code-guide clean; all 13 helper-verb references match shipped verbs; AskUserQuestion blocks single-line.

### Phase 7 — Emitter promotion + cross-file reconciliation ✅ DONE 2026-05-25
`scripts/emitters/claude.py` `_PROMOTED += "breakdown"`; `src/devforge/storage-rules.md` tree + lifecycle add the chain handoff artefacts (`handoff.json` / `plan-handoff.json` / `breakdown-handoff.json`) + machine-contract note; `src/CLAUDE.md` catalog entry corrected (`[spec-file]`→`[plan-file]`, mentions `breakdown-handoff.json`); `07-EXECUTE-TASK` read-contract section re-pointed YAML-frontmatter → `breakdown-handoff.json` with a ⚠️ SUPERSEDES callout flagging the derivative frontmatter sketches (parse_task_file / agent-dispatch / Phase 11) to rework when 07 builds; DEVELOPMENT-STATUS breakdown line + `_agent-assignment.md` partial line updated; CHANGELOG `### Added` entry.
**Verify**: emitter run against a temp target emits `.claude/commands/breakdown.md` (423 lines, valid frontmatter); 07 read-contract no longer claims frontmatter as the authoritative contract.

### Phase 8 — e2e smoke (OQ-5) ✅ DONE 2026-05-25 (helper-level) / interactive run = user-driven
Self-contained end-to-end chain run against the real shipped helpers (installed-invocation style, zero side-effects): `plan_helper finalize-handoff` → `breakdown_helper {pick-plan, read-plan-handoff, check-status-and-flip, render-findings-from-plan}` → write tasks → `verify-contract-chain` (advisory exit-2 case + fully-closed exit-0 case both verified) → `verify-ac-coverage` (exit 0) → `finalize-handoff` → `breakdown-handoff.json` reconstructed through `_breakdown.handoff_schema` (provenance→plan, original-case contracts, AC/agent/review_checkpoint parsed) → `render-execute-task-handoff` (`/execute-task 001` + restart reminder). **This e2e caught a real producer bug** (finalize-handoff stored casefolded contract text — fixed: extraction preserves case, only `verify-contract-chain` comparison normalizes; +3 regression tests). The full INTERACTIVE LLM-driven run (orchestrator following `main.md`, architect dispatch, AskUserQuestion gates) requires a testForge20 forge re-install + live session — **user-driven** (matches the deferred interactive-e2e stops in 02/04); the non-interactive helper+chain validation above is complete.
**Verify**: e2e script PASS; 610 passed across breakdown(235)+plan+specify suites (zero regressions); emitter emits `breakdown.md`.

## When resuming work

1. Re-read this plan in full + `src/commands/plan/main.md` (the structural template) + `src/devforge/lib/_plan/handoff_schema.py` (the producer breakdown consumes).
2. Confirm OQ-1..5 with the user if not yet answered — they fork Phase 0/4/5.
3. Check `git log --oneline` on `develop-2.0-init` for which execution phase last landed.
4. `pytest tests/lib/test_breakdown_helper.py` to see current verb coverage.
5. Build phases in order; each must be buildable + tested before the next.

## Cross-references / alignment table

| Concern | Source of truth |
|---|---|
| Producer breakdown obeys | `src/devforge/lib/_plan/handoff_schema.py` + `plan_helper finalize-handoff` |
| Structural template | `src/commands/plan/main.md` |
| Consumer-reads-producer pattern | `src/devforge/lib/_specify/_cmds_handoff.py` |
| Task-file human format | `src/devforge/storage-rules.md` §Task File Format |
| Agent-layer map | `src/_pending/commands/_agent-assignment.md` (inlined per OQ-3) |
| Downstream consumer (future) | `07-EXECUTE-TASK-REDESIGN-PLAN.md` (read contract re-pointed in Phase 7) |
| Architect role policy | memory `project_architect_role_scope.md` |
