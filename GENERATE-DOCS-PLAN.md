# /generate-docs — new command via python-skeleton primitive

**Status**: Draft, not yet executed. Awaiting user approval.
**Branch**: `develop-2.0-init` (continues from Step 1 of `ARCHITECTURE-PIVOT-PLAN.md`).
**Coexistence (this iteration only)**: `/onboard` (existing, with vault-restored helper + iteration banner) is **NOT modified by this plan**. `/generate-docs` is a NEW command that ships alongside `/onboard`. Once `/generate-docs` is proven via the empirical gate (Phase 8), Phase 8.2 retires `/onboard` and removes the old code (vault `onboard_helper.py`, `/onboard` spec, `_PROMOTED` entry, install/update references). Per user directive: "u will develop new scripts, old will be removed" — old is removed AFTER new is proven, not before.
**Supersedes**: Step 2 of `ARCHITECTURE-PIVOT-PLAN.md` ("Schema-anchor /generate-docs outputs"). The schema-anchored design from memory `project_schema_anchored_generate_docs.md` becomes the foundation; the python-skeleton primitive is the implementation pattern that realizes it.
**Source notes**: `20 Projects/AIDevTeamForge/rewritePlans/{Python skeleton as unifying primitive, Documentation Strategy - Research-Quality Optimization, Docs improvement priority for research-quality optimization, Docs strategy - mechanical first then non-derivable, Specify skeleton script - first prototype sketch}.md` in Obsidian.

---

## ⚠️ Execution discipline (load-bearing — read before any step)

**This iteration is agent-mediated only.** No direct code/spec writing by the orchestrator. Every artifact (Python helper, schema dataclass, test, command spec, reference doc, script) is produced by a dedicated agent and reviewed by a dedicated reviewer agent. The orchestrator coordinates and decides; agents execute.

### Agents in use

| Agent | Used for | Always includes |
|---|---|---|
| `python-engineer` | Writing Python code in `src/devforge/lib/*.py`, `scripts/*.py`, with their tests in same turn | (a) cross-check: grep for callers / dependent files / overlapping tests; (b) impact analysis: what does this change touch downstream; (c) rethink-on-conflict: if cross-check or impact analysis surfaces inconsistency, halt and re-design before writing |
| `python-reviewer` | Auditing python-engineer's output before integration | (a) re-read source files cited; (b) re-run tests independently; (c) flag every cross-reference the engineer didn't update |
| `instruction-author` | Writing/editing spec markdown (`src/commands/generate-docs/main.md`, `references/*.md`, `CLAUDE.md` updates) | (a) cross-check: grep for affected identifiers / paths / section numbers; (b) impact analysis: which downstream commands or specs reference this; (c) rethink-on-conflict: if dangling refs surface, re-plan the spec before writing |
| `instruction-reviewer` | Auditing instruction-author's output for logical flow + cross-ref consistency + sentence-level hallucination | (a) intra-file consistency check; (b) flag every forward-ref to non-existent state |
| `claude-code-guide` | Validating Claude Code authoring conventions for command/agent files (frontmatter, slash command shape, MCP server interactions, etc.) | Fetches `docs.claude.com` content live; never relies on training memory |

### The mandatory loop per step

```
1. Orchestrator briefs the engineer agent with FULL context:
     - what to build (function signature, schema, spec section)
     - integration: where this fits, what consumes its output
     - constraints: existing patterns, conventions, anti-patterns to avoid
     - edge cases the orchestrator already knows
     - success criteria + verification protocol
     - explicit "what NOT to do" (out-of-scope changes)

2. Engineer does the work AND IN THE SAME TURN:
     a. Cross-checks: greps for callers, dependent files, overlapping tests, refs to identifiers
     b. Impact analysis: enumerates downstream effects (which files break, which tests need updating, which specs cite what's changing)
     c. If (a) or (b) surface inconsistency or potential bug:
          → STOP. Re-plan. Report the conflict to orchestrator. Do not proceed until resolved.
     d. Otherwise: writes function + tests, runs tests, reports back

3. Reviewer audits engineer's output:
     - Reads the actual files (not the engineer's summary)
     - Re-runs tests independently
     - Re-runs cross-check + impact analysis from scratch
     - Reports findings: severity / location / issue / why / fix per finding

4. If reviewer surfaces issues:
     → Loop back to step 1 with reviewer's findings as additional brief context
     → Engineer re-does affected portions, including new cross-check + impact analysis
     → Reviewer re-audits
     → Loop until clean

5. Orchestrator integrates only when reviewer reports clean
     - Updates GENERATE-DOCS-EXECUTION-LOG.md with the step's outcome
     - Commits the work as a discrete, independently-buildable commit
```

### Rules

1. **No orchestrator-direct writes.** Even one-line spec edits go through `instruction-author` + `instruction-reviewer`. Even one-line Python edits go through `python-engineer` + `python-reviewer`. Discipline holds for trivial-looking changes because trivial-looking changes are where cross-reference inconsistency leaks in.
2. **Cross-check + impact analysis are non-negotiable parts of every agent task.** A brief that omits "include cross-check and impact analysis" is an incomplete brief and the orchestrator must rewrite it.
3. **Rethink on conflict, don't paper over.** If an agent's cross-check surfaces a conflict (e.g., the new schema field clashes with an existing detect_report convention), the agent halts and reports. The orchestrator either re-plans the step or accepts the conflict explicitly. No silent merging.
4. **Fully logical, fully aligned.** End state of every step must be: zero dangling references in the repo, zero contradictions between specs, zero unreferenced schema fields, zero deferred TODOs added by this work. Future-session-falsely-believes check (per `feedback_preempt_future_hallucination.md`) runs before declaring step done.
5. **Goal: a tool simpler and higher-quality than `/onboard` is today.** Quality measured by: structural consistency (zero structural variance across re-runs), retrieval recall for `/research` (Phase 8 empirical gate), citation validity rate (mechanical), agent friendliness (predictable doc shape).
6. **Briefs are self-contained.** Per `feedback_no_underspecification_when_delegating.md`: every agent invocation gets goal + integration + constraints + known edge cases + success criteria + what-not-to-do. Thin briefs are the orchestrator's failure, not the agent's.

---

## Goal

**Make `docs/` well-populated and optimized for LLM consumption, because `/research` will be the new starting command for feature work.** The LLM-side flow becomes:

1. User invokes `/research <fuzzy intent>` (or its evolution that includes "preliminary analysis of what the human actually wanted")
2. `/research` reads the doc layer's entry-point index (topic index)
3. `/research` follows index pointers to relevant per-package + per-concern docs
4. `/research` cross-references glossary for unfamiliar terms, reverse index for file lookups, pattern catalog for prior art
5. `/research` synthesizes the user's intent + retrieved docs + targeted code reads into a research output
6. `/specify` consumes the research output + does preliminary analysis of what the human wanted → spec.md

The doc layer is **infrastructure for `/research`**, not a deliverable in its own right. Doc quality is judged by: how much retrieval recall it gives `/research`, how cleanly it answers "what does this do / where is this / what does this term mean" without forcing `/research` to grep blindly.

This reframes the new command's optimization target:
- **Primary**: docs that `/research` can consume cheaply and exhaustively (high recall, structurally predictable, citation-validated)
- **Secondary**: docs that human-readable as a side effect (fine, but not the design driver)

### Mechanism

`/generate-docs` uses a **skeleton-fill** model. Each doc artifact gets a Python-generated skeleton with `[TODO]` slots; LLM fills slots only; validator checks structure + factual accuracy mechanically.

**Structural variance → 0%** because structure isn't LLM-generated. Remaining variance is decision-quality and prose, which is the actual LLM work. **Predictable structure is what makes `/research` cheap** — a downstream LLM reading the docs knows where to look without re-discovering layout per project.

**Citation discipline becomes mechanical** — every `<!-- path:line-range -->` reference is validated against the source filesystem, every code snippet is compared verbatim to the cited line range. LLM cannot fabricate code that passes validation. **`/research` can trust citations as ground truth** — no re-verification step needed.

**Three-mode separation** (from `Docs strategy - mechanical first, then non-derivable.md`):
- **Mode 1** — codebase extraction (mechanical scripts + skeleton-fill). This plan's scope.
- **Mode 2** — interview-driven content (rationale, anti-patterns, deep playbooks, glossary definitions). Deferred to a future plan after Mode 1 lands and an empirical gate (Phase 8 — `/research` parity test) justifies the human-time investment.
- **Mode 3** — refresh / re-validate. Out of scope — handled by a future `/refresh-docs` command consuming the same scripts.

---

## Principles (load-bearing reasoning)

These principles govern the design of `/generate-docs` and Track B scripts. They're stated explicitly so future sessions don't unknowingly drift away from the rationale.

### 1. Recall over precision for `/research`

`/research`'s output quality is bounded by what it retrieved. Synthesis cannot operate on content that wasn't found. Cost of missing relevant content is high (downstream commands compound the gap). Cost of including marginal content is low (LLM reads more; no harm). Therefore: docs infrastructure optimizes for recall (find more relevant content) not precision (filter aggressively).

Implication: the topic index, glossary, and reverse index are sized for inclusiveness. A noisy entry-point row that occasionally surfaces irrelevant docs is acceptable; a tight one that misses the relevant doc is not.

### 2. If an LLM can derive content from code, the doc adds no unique value

Doc work is justified only when it encodes knowledge that lives outside the codebase. Mechanical content (file paths, identifier inventories, type definitions, citation accuracy) is derivable — generate it via script; regenerate on demand; never hand-author it. Non-derivable content (decision rationale, anti-pattern catalogs from incident memory, business glossary definitions) requires human input — defer until the empirical gate justifies the time investment.

Implication: every proposed doc artifact gets the derivability test before it's added. If a script can produce it, a script must produce it.

### 3. Cost asymmetry justifies mechanical-first sequencing

Mechanical work: ~10 hours of script-writing once, runs forever, refreshes automatically, no per-run cost. Human-knowledge work: 30+ hours of solo-dev time, slowly stales, decays without active maintenance.

Solo-dev time is the binding constraint. Mechanical-first ordering frees that time for work only the developer can do. Reversing the order spends the bottleneck resource on the cheaper class of work.

Implication: this plan ships mechanical artifacts (Mode 1) in full before any human-time investment (Mode 2). The empirical gate (Phase 8.1) decides whether Mode 2 is justified.

### 4. Mechanical scripts compound with future docs work

Two consequences of the same property:

- **Diagnostic surface**: scripts surface gaps that human-knowledge work fills (reverse index → which files have no docs; accuracy validation → which docs are stale; constitution scanner → which rules don't anchor). Without the diagnostic, human-time work is invested without a punch list.
- **Survives restructuring**: scripts regenerate against any future docs layout. Mechanical infrastructure doesn't need to be rebuilt when content is reorganized. Future "simplify by removing the topic index" proposals fail this check — they discard load-bearing infrastructure that costs ~10 hours to rebuild and serves every `/research` invocation.

Implication: scripts are foundational, not provisional. They're protected from "cleanup" decisions that don't account for retrieval-recall consequences.

### 5. Ecosystem-agnostic by design

The framework targets any language / build-system / monorepo convention. testForge20 (JS/TS/Vue monorepo) is the iteration's parity-test fixture, not the framework's design target. Helper subcommands and Track B scripts must dispatch on ecosystem signals (manifest type, source-root convention, identifier conventions) rather than hardcode JS/TS assumptions. Where ecosystem-specific behavior is required, the dispatch is explicit (manifest detection table, per-language identifier patterns, ecosystem-aware monorepo walking).

Implication: every brief that touches "package.json" / "src/" / "camelCase" / "BLoC pattern" must spell out the dispatch for non-JS ecosystems. Phase 8.1's empirical gate measures on testForge20 but ALSO requires sanity-check on at least one non-JS fixture (Rust crate or Python package) before declaring victory.

---

## Base acceptance criteria (orchestrator-level)

These apply to every script and helper subcommand in this plan. The orchestrator includes them in every `python-engineer` brief; per-step verify sections add step-specific criteria on top.

1. **Idempotent** — re-running on unchanged inputs produces byte-identical output
2. **Diff-friendly** — output is line-stable so reviewers can audit changes
3. **No manual setup** — runs end-to-end via `python3 <script>.py` (or helper subcommand) with no flags beyond what the brief specifies
4. **`[TODO]` placeholders are non-blocking** — scripts may emit `[TODO]` markers for human-supplied content; these do not cause script-level failure
5. **Stdlib only** — no third-party dependencies; `init_helper.py`'s utility patterns (atomic write via `tempfile.mkstemp` + `os.replace`, `argparse`, `die()`) are the reference
6. **Self-contained output** — generated markdown reads without external context

Per-step verify sections retain step-specific criteria (test counts, fixture choices, output format details).

---

## Empirical baseline (what we compare against)

Two reference outputs exist for `apps/app-web/` of testForge20:

| Source | File count | Bytes | Citations | Section shape | Decomposition |
|---|---|---|---|---|---|
| Heavy spec (today's `/onboard` helper-mediated run) | 1 monolith | ~50 KB | 33/33 paired | Strict A.2.1 template, 13 collapsed concern subsections | None (one doc) |
| Reference spec (cse-strata-ws-forge older `/onboard`, today's testForge20 re-run) | 10 docs | 60.8 KB | **0** | Loose content-driven (Tech Stack / Route Table / Business Rules / etc.) | Per-concern split |
| cse-strata-ws-forge actual reference docs (months-old original run) | 12 docs | 44.5 KB | 0 | Strict A.2.1 template (Overview / Directory Structure / Main Exports / Types / Dependencies / Usage Example) | Per-concern split |

**Targets `/generate-docs` must hit:**
1. **Coverage ≥** reference (10–12 concern docs covering all substantive subfolders)
2. **Decomposition** = per-concern split (not monolith)
3. **Citation discipline** = every code block paired with `<!-- path:line-range -->` reference, validated mechanically against source
4. **Structural consistency** = re-runs produce structurally identical output (schema, A.2.1 template, citation format are deterministic across runs; LLM-selected content — export set, hazard set, prose — varies per run by design). Helper-level render (`render-package-doc` invoked twice on the same stable state) is byte-identical.
5. **Section template uniformity** — choose one template (strict A.2.1 or content-driven) and enforce across all package docs
6. **Higher quality than today's `/onboard`** — measured by Phase 8's empirical gate (retrieval recall for `/research`, citation validity, intent-analysis quality)

**testForge20 is the iteration's TEST FIXTURE, not the framework's design target.** Per Principle 5 (ecosystem-agnostic by design), the helper + scripts must produce equivalent quality on any ecosystem. testForge20 is chosen as the parity anchor because it has both the cse-strata-ws-forge reference docs (for shape comparison) and a complex monorepo structure (apps/ + packages/ + ~26 manifests). Phase 8.1's empirical gate measures on testForge20 PLUS at least one non-JS fixture (Rust crate or Python package — pick whatever's available at gate time) before declaring victory.

Each plan step's verify includes a comparison against this baseline.

---

## Architecture (after `/generate-docs` lands)

```
src/devforge/lib/
  generate_docs_schema.py    ← dataclasses (single source of truth, NEW)
  generate_docs_helper.py    ← skeleton generator + validator + render (NEW)
  generate_docs              ← POSIX launcher (NEW)
  onboard_helper.py          ← existing /onboard (UNCHANGED this iteration; REMOVED in Phase 8.2)
  onboard_helper             ← existing /onboard launcher (UNCHANGED; REMOVED in Phase 8.2)
  init_helper.py             ← existing /init-forge (UNCHANGED)
  detect_report.py           ← legacy /setup-wizard (UNCHANGED, deprecated)
  wizard_render.py           ← legacy /setup-wizard (UNCHANGED, deprecated)

src/commands/
  generate-docs/
    main.md                  ← LLM-facing instructions (slim, ~150 lines, NEW)
    references/              ← per-mode references (slot-filling guidance,
                               citation discipline, hazard-finding mandates)
  onboard/                   ← existing (UNCHANGED this iteration; REMOVED in Phase 8.2)
  init-forge/                ← existing (UNCHANGED)
  setup-wizard/              ← legacy (UNCHANGED, source kept; emitter doesn't ship)
  constitute/                ← existing (UNCHANGED)

scripts/                     ← Track B retrieval-optimization scripts (NEW)
  build_topic_index.py       ← script J (entry point — highest priority)
  extract_glossary_terms.py  ← script C-extraction
  build_docs_index.py        ← script B (reverse index)
  build_pattern_catalog.py   ← script D (pattern catalog)
  validate_doc_claims.py     ← script A (accuracy report)
  scan_constitution_anchors.py ← script H (constitution anchors)
  add_freshness_footers.py   ← script I (freshness footers)

tests/lib/
  test_generate_docs_schema.py     ← schema validation (NEW)
  test_generate_docs_helper.py     ← per-subcommand tests (NEW; target ~100-150)
  (existing test files unchanged: test_init_helper.py, test_detect_report.py, test_wizard_render.py)
tests/scripts/
  test_build_topic_index.py        (NEW)
  test_extract_glossary_terms.py   (NEW)
  test_build_docs_index.py         (NEW)
  test_build_pattern_catalog.py    (NEW)
  test_validate_doc_claims.py      (NEW)
  test_scan_constitution_anchors.py (NEW)
  test_add_freshness_footers.py    (NEW)

scripts/emitters/claude.py
  _PROMOTED                  ← extend tuple with "generate-docs"; "onboard" stays this iteration; removed in Phase 8.2
```

Two parallel tracks:
- **Track A** — `/generate-docs` core (PackageDoc + ConcernDoc + ArchitectureDoc + memory archaeology) via skeleton primitive
- **Track B** — 7 standalone retrieval-optimization scripts (J, C-extraction, B, D, A, H, I) — **load-bearing for `/research` consumption, not enrichment**

Tracks are independent — Track B scripts run on already-generated docs/, so they need at least Phase 2 (per-package docs from `/generate-docs`) to operate on. The plan sequences Track A through Phase 2 first, then interleaves Track B with Phase 3+ in priority order so `/research`-consumable artifacts appear as soon as possible.

## `/research` consumer protocol

This is how the artifacts get consumed in the post-rewrite world. Each layer answers a different question: topic index ("what's relevant to this fuzzy input?"), glossary ("what does this term mean?"), reverse index ("which docs reference this file?"). Drives the priority of every doc artifact in the plan.

```
/research <fuzzy intent> session start
  │
  ▼
1. Read docs/topic-index.md (Track B Step 6.4 — the entry point)
   ~40 rows, < 5 KB; LLM matches user intent against Topic name + Domain terms
  │
  ▼
2. Score top 1-3 matching topics. Each topic row points to:
   - Brief (one paragraph, derived from package's index.md Overview)
   - Domain terms (top 10-15 identifiers)
   - Code locations (directory paths)
   - Reference docs (per-package + per-concern docs from Track A)
  │
  ▼
3. Read ONLY the Reference docs from selected topics (typically 2-5 files,
   ~10-30 KB total). Each doc has predictable A.2.1 structure:
   Overview / Directory / Main Exports / Types / Dependencies / Usage Example
   plus inline Hazards section flagging known mislogic.
  │
  ▼
4. As needed during deeper exploration:
   - docs/glossary.md (Track B Step 6.3) for unfamiliar terms
   - docs/index.md (Track B Step 6.2) for "which docs reference this file?"
   - docs/patterns/index.md (Track B Step 6.6) for "what's the canonical X?"
   - docs/accuracy-report.md (Track B Step 6.5) to filter stale claims
  │
  ▼
5. Targeted source reads (only when docs don't answer the question)
   - Citations in docs are validated → trust them as ground truth
   - Source reads only for content beyond the boundary surface
  │
  ▼
6. Synthesize: research output + preliminary analysis of user intent
   → handoff to /specify
```

**Replaces** "read full docs/ and grep" with "read 1 entry-point index + 2-5 specific docs + targeted lookups." Cuts retrieval-context size by ~80% per the source notes. **More important: gives `/research` a deterministic retrieval surface so its output is reproducible across sessions.**

This protocol implies the artifact priority for `/generate-docs`:

| Priority | Artifact | Source | Why it's load-bearing |
|---|---|---|---|
| **1** | Per-package + per-concern docs | Track A Phase 2-3 | The actual content. Empty docs/ = nothing for `/research` to retrieve. |
| **2** | `docs/topic-index.md` | Track B Step 6.4 | Entry point. Without it, `/research` reads full docs/. |
| **3** | `docs/glossary.md` | Track B Step 6.3 | Term disambiguation at retrieval entry. |
| **4** | `docs/index.md` (reverse) | Track B Step 6.2 | File→doc lookup during exploration. |
| **5** | `docs/architecture.md` | Track A Phase 4 | Workspace-level patterns + dep graph for cross-package questions. |
| **6** | `.devforge/memory.md` | Track A Phase 5 | Hazards / known mislogic / V1-V2 coexistence — content `/research` can't grep. |
| **7** | `docs/patterns/index.md` | Track B Step 6.6 | Prior-art references. |
| **8** | `docs/accuracy-report.md` | Track B Step 6.5 | Filter for stale citations. |
| **9** | `docs/constitution-anchors-report.md` | Track B Step 6.7 | Cross-reference rules to features. |
| **10** | Freshness footers | Track B Step 6.8 | Per-doc staleness diagnostic. |

**Sequencing implication**: after Track A Phase 2 ships per-package docs, Track B Step 6.4 (topic index) is the next-highest-priority work. It unlocks `/research`'s entry-point flow. Phases 3-5 of Track A (concerns, architecture, memory) and remaining Track B scripts ship after.

---

## Schema (Track A foundation)

Single source of truth in `src/devforge/lib/generate_docs_schema.py`. Generator and validator both import. Built in Phase 1.1 by `python-engineer` (with `python-reviewer` audit).

```python
from dataclasses import dataclass, field
from typing import Optional, Literal

ExportKind = Literal[
    "function", "class", "type", "constant", "config",
    "schema", "command", "component", "directive", "plugin", "other"
]
DependencyKind = Literal["internal", "external"]
HazardCategory = Literal[
    "naming", "performance", "type-safety", "duplication",
    "inconsistency", "v1-v2-coexistence", "complexity"
]

@dataclass
class SourceCite:
    """A <file>:<start>-<end> source reference."""
    file: str        # relative to project root
    start: int       # line number, 1-indexed
    end: int         # line number, inclusive

@dataclass
class CodeBlock:
    """A code snippet lifted verbatim from source with citation."""
    language: str
    snippet: str     # verbatim, validator compares to source
    cite: SourceCite

@dataclass
class Export:
    name: str
    kind: ExportKind
    signature: Optional[str]
    description: str
    code: CodeBlock

@dataclass
class Dependency:
    name: str
    kind: DependencyKind
    version: Optional[str]
    purpose: str
    consumer_locations: list[str] = field(default_factory=list)

@dataclass
class Hazard:
    category: HazardCategory
    description: str
    cite: Optional[SourceCite]

@dataclass
class PackageDoc:
    name: str
    path: str                                 # relative to project root
    overview: str                             # 1-2 paragraphs
    directory_tree: str                       # multi-line ascii tree
    primary_language: str
    framework: Optional[str]
    build_tool: Optional[str]
    scripts: dict[str, str]                   # from package.json scripts block
    exports: list[Export]
    dependencies: list[Dependency]
    hazards: list[Hazard]                     # mislogic / naming / perf inline observations
    usage_example: Optional[CodeBlock]
    consumer_pattern: Optional[CodeBlock]

@dataclass
class ConcernDoc:
    package_path: str                         # parent package
    concern_name: str                         # subfolder name
    overview: str
    directory_tree: str
    public_surface: list[Export]              # NB: at concern level, called "Public Surface" not "Main Exports"
    types: list[CodeBlock]
    dependencies: list[Dependency]
    hazards: list[Hazard]
    usage_example: Optional[CodeBlock]

@dataclass
class ArchitectureDoc:
    project_name: str
    architecture_shape: str                   # closed enum from detect.md §4.5
    patterns: list["Pattern"]
    layers: list["Layer"]
    cross_package_deps: list["DepEdge"]
    decisions: list["Decision"]

@dataclass
class Pattern:
    name: str
    description: str
    applies_in: list[str]                     # paths
    evidence: list[SourceCite]

@dataclass
class Layer:
    name: str
    description: str
    sample_packages: list[str]

@dataclass
class DepEdge:
    from_pkg: str
    to_pkg: str
    reason: str

@dataclass
class Decision:
    title: str
    rationale: str
    evidence: list[SourceCite]

@dataclass
class MemoryFinding:
    category: HazardCategory
    unit: str                                 # package or "workspace"
    observation: str                          # one line
    cite: Optional[SourceCite]
```

Schema accommodates both A.2.1 strict template (via `Export` + `CodeBlock` lists) and the content-driven richness from today's reference run (via `hazards` for inline observations + flexible `directory_tree` text).

---

## Track A — `/generate-docs` core

### Phase 1 — Foundation (schema + skeleton primitive proof)

#### Step 1.1: Implement `generate_docs_schema.py` + tests

**Brief to `python-engineer`** (orchestrator must include all of these explicitly in the agent invocation):
- **Goal**: implement all dataclasses defined in the Schema section above as `src/devforge/lib/generate_docs_schema.py`. Pure dataclasses with `__post_init__` field validation (e.g., `SourceCite.start <= SourceCite.end`, `Export.code.cite` references file extensions matching `Export.kind`'s expected ecosystem). No side effects, no IO, no business logic.
- **Integration**: imported by `generate_docs_helper.py` (Step 1.2) and validator subcommands. Imported by tests in `tests/lib/test_generate_docs_schema.py`.
- **Constraints**: Python 3.8+ target — use `Optional[X]` and `list[X]` (3.9+) deliberately if confirmed against installed Python; per `python-engineer.md` anti-pattern #10, prefer `Optional` from `typing` for safety. Stdlib only (no pydantic). Match existing helper conventions: see `src/devforge/lib/init_helper.py` for atomic write patterns and argparse style (relevant for Step 1.2, not Step 1.1).
- **Edge cases the orchestrator already knows**: empty exports list, missing optional fields (framework, usage_example), CodeBlock with empty snippet, Hazard without cite, line ranges spanning end of file.
- **Success criteria**: every dataclass has a unit test for happy path + every field's failure mode (missing required, type mismatch, invariant violation). Target ~25 tests passing.
- **Out of scope**: rendering logic (Step 1.2), state persistence (Step 1.2), file I/O of any kind.
- **Cross-check / impact analysis (mandatory)**: grep for any other file importing from `devforge.lib.*` schema-shaped modules; confirm no name conflicts with detect_report's setters or wizard_render's state shapes; confirm enum literals don't collide with existing helper conventions. If any conflict, halt and report.
- **Loop**: `python-reviewer` audits. If reviewer surfaces an issue (e.g., a missing dataclass field for a real LLM-side need, or an invariant the engineer didn't catch), engineer re-plans + re-implements + re-tests. Iterate until reviewer reports clean.

**Verify (orchestrator-side, after agent loop closes):**
1. `python3 -m unittest tests.lib.test_generate_docs_schema -v` — ~25 tests passing
2. `python3 -m unittest discover tests/lib -q` — 336 baseline + 25 new = ~361 OK
3. `grep -rn "generate_docs_schema" src/` — confirm only Step 1.1's new file references it (not yet imported elsewhere; Step 1.2 wires it)
4. Future-session-falsely-believes check: a fresh session reading `src/devforge/lib/generate_docs_schema.py` should not be misled about which fields are required vs optional.

**Compare:** N/A (foundation; nothing to compare yet).

---

#### Step 1.2: Implement `generate_docs_helper.py` skeleton + fill + validate (PackageDoc only)

**Brief to `python-engineer`**:
- **Goal**: implement `src/devforge/lib/generate_docs_helper.py` with the subcommand surface for the **PackageDoc tier only**. Other tiers (ConcernDoc, ArchitectureDoc, MemoryFinding) come in later phases. Subcommands required at this step:
  ```
  generate_docs_helper reset
  generate_docs_helper add-package --path <p> --name <n>
  generate_docs_helper set-package-overview --path <p> --text "..."
  generate_docs_helper set-package-tree --path <p> --text "..."
  generate_docs_helper set-package-language --path <p> --value <l>
  generate_docs_helper set-package-framework --path <p> --value <f>
  generate_docs_helper set-package-build-tool --path <p> --value <t>
  generate_docs_helper add-package-script --path <p> --script-name <n> --command "..."
  generate_docs_helper add-package-export --path <p> --name <n> --kind <k> --signature "..." \
      --description "..." --language <l> --code-snippet "..." --cite-file <f> --cite-start <s> --cite-end <e>
  generate_docs_helper add-package-dep --path <p> --name <n> --kind internal|external \
      --version <v> --purpose "..." --consumer-location <loc>...
  generate_docs_helper add-package-hazard --path <p> --category <c> --description "..." \
      [--cite-file <f> --cite-start <s> --cite-end <e>]
  generate_docs_helper set-package-usage-example --path <p> --language <l> --code-snippet "..." \
      --cite-file <f> --cite-start <s> --cite-end <e>
  generate_docs_helper render-package-skeleton --path <p>
  generate_docs_helper validate-package --path <p>
  generate_docs_helper render-package-doc --path <p>
  generate_docs_helper status
  generate_docs_helper extract-package-scripts --path <p>
  ```

  **Manifest dispatch for `extract-package-scripts`** (per Principle 5 — ecosystem-agnostic by design): the subcommand detects the package's manifest type and extracts scripts accordingly. Dispatch table:

  | Ecosystem | Manifest file | Scripts source |
  |---|---|---|
  | JS/TS | `package.json` | `scripts` block (verbatim) |
  | Rust | `Cargo.toml` | `[package.metadata.scripts]` if present, else default `cargo build/test/run/clippy/fmt` |
  | Python (PEP 621) | `pyproject.toml` | `[project.scripts]` + `[tool.poetry.scripts]` if Poetry |
  | Python (legacy) | `setup.py` / `setup.cfg` | `entry_points.console_scripts` |
  | Go | `go.mod` | no scripts in manifest; default `go build/test/run/vet` |
  | Java/Maven | `pom.xml` | standard goals: `mvn clean install / mvn test / mvn package` |
  | Java/Gradle | `build.gradle` / `build.gradle.kts` | best-effort static parse of top-level `task` declarations in `build.gradle` / `build.gradle.kts` (do NOT shell out to `./gradlew tasks`); standard lifecycle: `./gradlew build / test / assemble` |
  | .NET | `*.csproj` | default `dotnet build/test/run` |
  | Ruby | `Gemfile` + `Rakefile` | best-effort static parse of top-level `task :name` declarations in Rakefile (do NOT shell out to `rake -T`); default `bundle install / bundle exec` |
  | PHP | `composer.json` | `scripts` block (verbatim) |

  When no manifest is detected at the package path, exit 2 with a clear message naming the path and the manifests checked. When a manifest is detected but has no scripts block, return the ecosystem's default script set. The subcommand's tests cover at minimum the JS/TS, Python (pyproject), Rust, and Go cases; other ecosystems default to graceful fallback.

- **Integration**: invoked by the `/generate-docs` LLM (Phase 2.1's spec). Reads/writes state at `.devforge/.generate-docs-state.json` (DISTINCT from `/onboard`'s `.devforge/.onboard-state.json` to avoid collision). Renders to `docs/<path>/index.md.skeleton` and `docs/<path>/index.md`.
- **Constraints**:
  - Match `src/devforge/lib/init_helper.py` patterns for argparse, `die()`, atomic file writes via `tempfile.mkstemp` + `os.replace`. Reference but do not reproduce vault helper anti-patterns (see `python-engineer.md` Patterns to avoid #1–#10).
  - Stdlib only.
  - Validation rules (mandatory):
    1. All dataclass required fields populated
    2. Every `[TODO]` slot filled in skeleton output before validate-package can pass
    3. Every `SourceCite` references a file that exists relative to project root
    4. Every `SourceCite` line range is within the file's actual line count
    5. Every `CodeBlock.snippet` matches the source at `cite.file:cite.start-cite.end` verbatim (whitespace-normalized — strip trailing whitespace per line, leading/trailing blank lines)
    6. Every `Dependency` with `kind=internal` has a target that exists either in registered state (another package) or as a directory under project root
    7. Enum membership validated at set-time, not compose-time (per anti-pattern #2)
  - Render templates use manual concatenation (no jinja2). Pattern from memory `project_schema_anchored_generate_docs.md`. Section ordering follows the strict A.2.1 template: `# {name}` / `## Overview` / `## Directory Structure` / `## Tech Stack` / `## Scripts` / `## Main Exports` / `## Types` (extracted from exports with `kind=type`) / `## Dependencies` (split into Workspace-internal + External) / `## Hazards` / `## Usage Example`.
- **Edge cases**: missing source file, line range out of bounds, snippet whitespace mismatch, CRLF vs LF, empty package (no exports), package never `add-package`d before `set-package-overview` called, double `add-package` (idempotency), validate before render-skeleton, render-skeleton when state is empty.
- **Success criteria**: `python3 -m unittest tests.lib.test_generate_docs_helper -v` — target ~80–100 tests passing. End-to-end test: starting clean state, register one package via setters → render-package-skeleton → no `[TODO]` if all setters called → validate-package passes → render-package-doc produces final markdown matching golden fixture.
- **Out of scope**: ConcernDoc / ArchitectureDoc / MemoryFinding subcommands (later phases). Pre-existing `/onboard`'s helper at `src/devforge/lib/onboard_helper.py` MUST NOT be modified.
- **Cross-check / impact analysis (mandatory)**:
  - Grep for `.devforge/.generate-docs-state.json` and `.devforge/.onboard-state.json` to confirm no path collision (the existing `/onboard`'s state file is at `.devforge/.onboard-state.json` — confirm `/generate-docs` uses a distinct path)
  - Grep for `generate_docs_helper` to confirm it's not yet referenced (Step 2.1 wires it from spec)
  - Confirm install.sh's `cp -R src/devforge/lib/` will pick up the new file automatically (no install.sh edit needed)
  - Confirm `scripts/emitters/claude.py` doesn't yet promote `generate-docs` (Step 2.1 will)
  - If any of the above surfaces conflict, halt and report
- **Loop**: `python-reviewer` audits. Reviewer reads source files cited in code-block validation tests; reviewer re-runs tests; reviewer flags any test fixture that doesn't round-trip through the real producer. Iterate until clean.

**Verify (orchestrator-side):**
1. Test count: ~80–100 new + 361 prior ≈ ~441–461 OK
2. POSIX launcher works: `src/devforge/lib/generate_docs --help` matches the Python CLI
3. End-to-end smoke in `/tmp/gd-smoke`: register a fake package → render-skeleton → fill via mock LLM → validate → render-doc → diff against expected golden
4. Re-run the smoke twice: byte-identical state file (idempotency)
5. Cross-ref: grep for `onboard_helper` shows it untouched in `src/devforge/lib/`

**Compare:** N/A (helper infrastructure; doc-generation comparison comes in Phase 2.2).

---

### Phase 2 — Per-package skeleton end-to-end

#### Step 2.1: Author `/generate-docs` spec + emitter promotion

**Brief to `instruction-author`**:
- **Goal**: write `src/commands/generate-docs/main.md` (target ~150 lines) for a single-package iteration scope (testForge20 `apps/app-web/`). The spec drives the LLM through the skeleton-fill loop using `generate_docs_helper`'s subcommands from Step 1.2. Phase structure:
  1. **Phase 0**: pre-flight — verify `.devforge/`, `init.yaml` exists, target package path argument provided. Verify `.devforge/lib/generate_docs_helper` is executable. Iteration banner clearly marks single-package scope.
  2. **Phase 1**: discover the assigned package — read the package's manifest selecting by ecosystem (per Step 1.2's dispatch table: `package.json` for JS/TS; `Cargo.toml` for Rust; `pyproject.toml` / `setup.py` for Python; `go.mod` for Go; `pom.xml` / `build.gradle` for Java; `*.csproj` for .NET; `Gemfile` / `Rakefile` for Ruby; `composer.json` for PHP). Invoke `generate_docs_helper add-package` + `set-package-language` + `set-package-build-tool` + (optional) `set-package-framework`. Loop `extract-package-scripts` output through `add-package-script`. Source-root convention also dispatches by ecosystem: JS/TS → `src/`; Rust → `src/`; Ruby → `lib/`; Java/Kotlin → `src/main/java/<groupId>/<pkg>/` (collapse boilerplate path segments); Python → `src/<pkg>/` or `<pkg>/`; Go → unit root with `cmd/`, `pkg/`, `internal/` as direct concerns; C#/.NET → project folder directly. The LLM applies the convention for the detected ecosystem; spec must not assume `src/`.
  3. **Phase 2**: render skeleton — invoke `render-package-skeleton`. LLM reads the resulting `docs/<path>/index.md.skeleton` to see what `[TODO]` slots need filling.
  4. **Phase 3**: fill skeleton — for each `[TODO]` slot, the LLM:
     - Reads source files
     - Lifts code verbatim with line-range citation
     - Invokes the corresponding setter (`set-package-overview`, `add-package-export`, etc.)
     - Citation discipline mandatory — every `--code-snippet` setter requires `--cite-file` + `--cite-start` + `--cite-end`
  5. **Phase 4**: validate — invoke `validate-package`. On pass: invoke `render-package-doc` (renames `.skeleton` → `.md`). On fail: read errors, fix offending registrations, re-validate.
  6. **Phase 5**: report — print summary (package name, exports count, hazards count, citations count + verified count). Print full content of generated doc verbatim for user review (per `feedback_verbatim_echo_directive.md`).
- **Paired agent file**: in the SAME dispatch, also draft `.claude/agents/tech-writer.md` (~30 lines + frontmatter). The tech-writer is a dedicated subagent for the per-package skeleton-fill loop, dispatched by the `/generate-docs` orchestrator (this spec) once per package. Tight contract:
  - Receives one package assignment from the orchestrator (path + name + iteration mode flag)
  - Reads the package's source files
  - Invokes `generate_docs_helper` setters with values lifted from real source (citation discipline mandatory: every code-snippet setter requires `--cite-file` + `--cite-start` + `--cite-end`)
  - Runs `validate-package`
  - On validate failure: reads errors, fixes offending registrations, re-validates (cap retries at 3; surface to user above)
  - On success: runs `render-package-doc` (renames `.skeleton` → `.md`)
  - Returns: package name, exports count, hazards count, citations count + verified count

  Frontmatter: `name: tech-writer`, `description: Per-package skeleton-fill subagent for /generate-docs`, `tools: Read, Bash, Grep, Glob`, no `model:` override (per `feedback_avoid_command_model_override.md`).

  The skeleton-fill primitive carries the structural load — the tech-writer doesn't need to know markdown templates, citation format, or section ordering. Helper enforces all of that. Tech-writer only knows: read source, fill slots, run validate.
- **Integration**: the spec is consumed by the LLM in Claude Code at testForge20. Emitter (`scripts/emitters/claude.py`) ships it to `<target>/.claude/commands/generate-docs.md`. `_PROMOTED` tuple gets `"generate-docs"` added (alongside `"onboard"` which stays this iteration).
- **Constraints**:
  - Single-package iteration scope (mark as TEMPORARY; Phase 7.1 lifts to multi-package)
  - Reference docs for slot-filling guidance live in `src/commands/generate-docs/references/` if needed; basic-path may keep them inline for now
  - Spec is LLM instructions; per `feedback_llm_instructions_self_contained.md`, no forward-refs to future phases of this plan; scope only what THIS step ships
  - Per `feedback_askuserquestion_single_line_only.md`, AskUserQuestion calls (if any) use single-line text
  - Per `feedback_avoid_command_model_override.md`, no `model:` frontmatter override
- **Edge cases**: package.json missing (assume non-JS ecosystem; LLM falls through to ecosystem-specific manifest), package has no scripts, `validate-package` fails repeatedly (cap retries; surface to user), source file missing during citation
- **Success criteria**: spec is ≤200 lines, references zero legacy verbs (no `add-package-doc(--content blob)`), every helper subcommand named in the spec actually exists in Step 1.2's helper, every section's purpose is clear without forward-refs.
- **Out of scope**: ConcernDoc workflow (Phase 3), ArchitectureDoc workflow (Phase 4), memory archaeology (Phase 5), Track B scripts (Phase 6), multi-package orchestration (Phase 7.1).
- **Cross-check / impact analysis (mandatory)**:
  - Grep for every helper subcommand named in the spec → must exist in Step 1.2's helper
  - Grep for `/onboard` references in CLAUDE.md / install.sh / other specs → confirm none accidentally cite `/generate-docs` instead
  - Grep for `setup-wizard` / `init-forge` / `onboard` / `constitute` to confirm `/generate-docs` slots in cleanly without duplicating any existing command's role
  - Confirm `scripts/emitters/claude.py` _PROMOTED change is staged in this step (not deferred)
  - Confirm tech-writer agent file frontmatter matches Claude Code subagent spec (per `claude-code-guide` verification of `.claude/agents/python-engineer.md` patterns)
  - Confirm tech-writer's tool allowlist (`Read, Bash, Grep, Glob`) is sufficient for the contract — agent must NOT need `Write` (helper writes for it via setters) or `Edit` (no file modifications outside helper)
  - If any cross-reference surfaces conflict, halt and report
- **Loop**: `instruction-reviewer` + `claude-code-guide` audit BOTH files IN PARALLEL. instruction-reviewer for intra-file logical flow + sentence-level hallucination check (covers both `main.md` AND `tech-writer.md`). claude-code-guide for slash command authoring conventions (`main.md`) AND subagent definition conventions (`tech-writer.md` frontmatter, tools list, body structure). Both reviewers must report clean before integration.

**Brief to `python-engineer`** (small parallel task — emitter update):
- **Goal**: update `scripts/emitters/claude.py` `_PROMOTED` tuple to include `"generate-docs"`. Add the helper to `src/devforge/lib/` shipping list comments if relevant.
- **Cross-check / impact analysis**: confirm the emitter handles the new directory structure (with `references/` if used). Run install end-to-end against tmpdir and grep `<target>/.claude/commands/generate-docs.md` exists. Confirm `onboard.md` still ships (untouched).
- **Loop**: `python-reviewer` audits. Reviewer re-runs install end-to-end. Iterate until clean.

**Verify (orchestrator-side):**
1. Spec + emitter changes integrated cleanly
2. Install.sh end-to-end produces `<target>/.claude/commands/generate-docs.md` with the right content
3. testForge20 install: spec lands at `testForge20/.claude/commands/generate-docs.md`
4. No regression on existing commands' install (init-forge, onboard, constitute still ship)

**Compare:** N/A (spec authoring; comparison happens in Step 2.2).

---

#### Step 2.2: Run `/generate-docs apps/app-web` against testForge20 — first comparison

> **Historical context (post-A/B comparison)**: The tech-writer subagent dispatch references in this step's expected output and verify section reflect the option-A architecture that motivated the empirical A/B comparison. Per Step 2.3's Lock-in record + Open decisions #9, the canonical Phase 3 architecture is orchestrator-direct slot-fill (NOT tech-writer subagent). Step 2.2's tech-writer-specific success criteria are preserved here for the historical decision trail; they are NO LONGER required for canonical /generate-docs runs going forward. The empirical run that produced the locked-in baseline (16 exports / 9 hazards / 18 citations / idempotent render) was orchestrator-direct, not tech-writer-mediated.

**Orchestrator action**: instruct user to install the updated framework on testForge20 and run `/generate-docs apps/app-web` in Claude Code at testForge20.

**Expected output**:
- `docs/db-cse-ui-strata/apps/app-web/index.md` populated
- Every code block has `<!-- path:line-range -->` reference
- Validator confirms 0 stale citations, 0 snippet mismatches
- Helper-level idempotency (mandatory, mechanical): `render-package-doc` invoked twice on the same stable state produces byte-identical output
- LLM-level non-idempotency (by design): full `/generate-docs` runs with the LLM in the loop produce different content per run — different exports chosen from the same source surface, different hazards identified, different prose phrasing. The schema, A.2.1 template, and citation format are deterministic; LLM selection and prose are variable. This reflects the python-skeleton primitive's design intent: structure locked, content reflects current LLM judgment
- Tech-writer agent dispatch executes successfully — orchestrator launches one tech-writer subagent for `apps/app-web/`, the subagent fills slots + validates + reports clean

**Verify**:
1. File exists at expected path
2. `generate_docs_helper validate-package --path db-cse-ui-strata/apps/app-web` exits 0
3. Diff between back-to-back `render-package-doc` invocations on stable state: zero changes (helper-level idempotency check). Note: full `/generate-docs` re-runs with the LLM in the loop are NOT byte-idempotent across runs by design — see Step 2.3 Lock-in record.
4. Compare to baseline:
   - **vs heavy-spec /onboard monolith** (50 KB, 1 file): shape is decomposed at the package level (this is one package doc; concerns come in Phase 3)
   - **vs reference-spec /onboard 10-doc run** (1174 lines, 60.8 KB): index.md alone won't equal the full 10-doc tree — that's Phase 3's work. But this index.md should match the reference's `index.md` shape (113 lines, A.2.1 template) plus citation discipline (which reference lacked).
   - **vs cse-strata-ws-forge actual reference index.md** (113 lines, no citations): same A.2.1 template, plus citations.
5. Tech-writer agent dispatch worked: log shows the subagent invocation completed without orchestrator intervention beyond the initial brief; the subagent's report matches the actual state file content.

**Compare protocol**: capture a snapshot of the produced doc + the state file. For helper-level idempotency, diff a second `render-package-doc` invocation against the first on the same stable state (expect zero changes). For shape comparison, diff against cse-strata-ws-forge reference. Note: a fresh full `/generate-docs` re-run is NOT expected to byte-match the prior run (LLM judgment varies — see Step 2.3 Lock-in record); shape consistency is the comparison criterion, not byte equality. Document outcomes in `GENERATE-DOCS-EXECUTION-LOG.md`.

**If structurally far from cse-strata-ws-forge reference**:
- Re-brief `python-engineer` + `instruction-author` with the deviation
- Each agent does cross-check + impact analysis on which side (helper render template vs spec slot-filling guidance) caused the deviation
- Whichever agent's domain owns the issue takes the fix; reviewer audits; loop until clean
- Re-run Step 2.2 after fixes

**Iterate to lock shape** before proceeding to Phase 3.

---

#### Step 2.3: Lock shape, document baseline for downstream phases

**Orchestrator action**: once Step 2.2 produces a doc the user approves, record the approved shape as the new baseline for Phase 3+ (concern docs must be visually + structurally consistent with this approved package doc).

**Tech-writer prompt tightening pass (SUPERSEDED — see Lock-in record below)**: the motivation for this RECOMMENDED pass was agent clarity + per-subagent context efficiency when Phase 3 dispatches per concern. The architecture decision recorded under "Lock-in record" below removes the tech-writer subagent from the canonical Phase 3 dispatch path of `/generate-docs`. Tightening within `src/agents/tech-writer.md` SKELETON-FILL MODE is therefore deferred until/unless Phase 7.1 reintroduces tech-writer dispatch for multi-package wall-clock reasons. Tightening levers retained here for record:

- **Reduce setter-step enumeration verbosity**: consolidate the existing 6-step "You do" list (currently lines ~292–314 of `tech-writer.md`) where consolidation does not lose precision. The setter list (step 3) carries the load — surrounding steps may compress.
- **Defer hazard-finding to a separate dedicated pass within the agent**: avoid blending hazard-search with export-extraction in one read pass. First pass extracts public surface (exports, deps, usage example) from manifest + boundary files; second pass scans for hazards across the same source. Two narrower passes have better per-pass cohesion than one wide pass.
- **Cap source-reading depth**: instruct the agent to read public-API-relevant files first (manifest, index/entry-point, files containing exported symbols); only descend into implementation if a public symbol's signature or description cannot be filled from the boundary surface alone.

Tightening (when re-activated) must NOT relax: citation discipline (every snippet setter still requires verbatim source + cite triple), abbreviation-verification rule, hazard-category enum, retry cap on `validate-package` failure.

### Lock-in record (Step 2.3 — completed)

**Status**: DONE.

**Approved baseline shape** (testForge20 `apps/app-web` reference):

- 474-line single-package doc, ~30 KB
- A.2.1 strict template (Overview / Directory / Tech Stack / Scripts / Main Exports / Dependencies [Workspace-internal + External] / Hazards / Usage Example / Consumer Pattern)
- 18 mechanically-validated citations, all `<!-- path:line-range -->` paired
- 16 exports with verbatim code blocks
- 9 hazards with closed-enum categories (`naming|performance|type-safety|duplication|inconsistency|v1-v2-coexistence|complexity`)
- 36 dependencies (workspace-internal vs external split; 19 internal correctly classified + 17 external)
- HTML-escaped narrative fields (TypeScript generics like `DeepReadonly<Ref<S>>` rendered safely)
- Idempotency verified: back-to-back `render-package-doc` produces byte-identical output (md5 match)
- Empirical run-to-run variance (full `/generate-docs` with LLM in loop): between two consecutive fresh runs only ~7 of ~16 exports overlap and only ~2 of ~5 hazards overlap; prose differs. Schema, A.2.1 template, and citation format remain identical across runs. This is by-design variance, not a bug — the locked layer is structure + factual format; content reflects current LLM judgment
- `validate-package` exits 0 against approved state

**Architecture decision (Phase 3 dispatch model)**: orchestrator-direct slot-fill is the canonical Phase 3 architecture for `/generate-docs`. Empirical A/B comparison on testForge20 between option A (tech-writer subagent dispatch) and option B (orchestrator-direct fill) showed option B with 2–4× coverage (16 vs 7 exports, 9 vs 2 hazards, 18 vs 9 citations), zero helper-API contract breaks (option A made 2 direct JSON edits to the state file), and correct workspace-internal classification (option A misclassified all 19 as external). The full RESOLVED entry is open decision item #9 below; that entry is the canonical record. Tightening of `src/agents/tech-writer.md` SKELETON-FILL MODE is deferred (see "SUPERSEDED" note above); the agent file itself remains valid for non-`/generate-docs` uses (ONBOARDING mode for legacy `/onboard`, default Normal Mode for `/finalize` / fix / refactor doc updates).

Lock-in commit captures wall-clock timings (pre + post) for record-keeping in `GENERATE-DOCS-EXECUTION-LOG.md` but does NOT gate lock-in on a speed delta. The /generate-docs command is ideally a one-time action per project; wall-clock cost is amortized over the project lifetime.

**Verify**: user explicitly approves. Record commit SHA + approved doc copy + pre/post wall-clock timings (observation only, no target) + tightening levers applied (or skipped with reasoning) in `GENERATE-DOCS-EXECUTION-LOG.md`.

**Compare:** N/A for shape (lock-in step). Wall-clock timings recorded for both runs (no target — empirical observation only).

---

### Phase 3 — Per-concern skeleton (ConcernDoc)

#### Step 3.1: Extend helper with ConcernDoc subcommands

**Brief to `python-engineer`** (extends Step 1.2's helper):
- **Goal**: add concern-tier subcommands to `generate_docs_helper.py`, mirroring the package-tier surface:
  ```
  generate_docs_helper add-concern --package <p> --concern <c>
  generate_docs_helper set-concern-overview --package <p> --concern <c> --text "..."
  generate_docs_helper set-concern-tree --package <p> --concern <c> --text "..."
  generate_docs_helper add-concern-export --package <p> --concern <c> ...
  generate_docs_helper add-concern-type --package <p> --concern <c> --code-snippet "..." --cite-file <f> ...
  generate_docs_helper add-concern-dep --package <p> --concern <c> ...
  generate_docs_helper add-concern-hazard --package <p> --concern <c> ...
  generate_docs_helper set-concern-usage-example --package <p> --concern <c> ...
  generate_docs_helper render-concern-skeleton --package <p> --concern <c>
  generate_docs_helper validate-concern --package <p> --concern <c>
  generate_docs_helper render-concern-doc --package <p> --concern <c>
  ```
- **Integration**: extends state file shape (per-package now has a list of concerns). Concern docs use `## Public Surface` instead of `## Main Exports` (cse-strata-ws-forge convention).
- **Constraints**: when `validate-package` runs, also enforce per-concern decomposition coverage — filesystem walk of substantive subfolders (rule: ≥2 files OR clear architectural role — examples per ecosystem: JS/TS → `components/`, `services/`, `routing/`, `composables/`, `stores/`, `plugins/`; Python → `handlers/`, `models/`, `repositories/`, `services/`, `views/`; Go → `handlers/`, `middleware/`, `repository/`, `service/`; Rust → `services/`, `handlers/`, `traits/`, `repositories/`; Java/Kotlin → `controllers/`, `services/`, `repositories/`, `entities/`; the `python-engineer` implementing the gate must build an ecosystem-aware role list, not hardcode JS names) vs registered concerns. Missing concerns fail validation.
- **Cross-check / impact analysis**:
  - State file schema migration: ensure existing Phase 2 state files don't break
  - Tests: ~50 new tests covering setters + isolation across packages + decomposition gate
  - Concern label change: verify nothing in the codebase greps for `## Main Exports` at concern level
- **Loop**: `python-reviewer` audits. Reviewer re-runs full helper test suite. Iterate.

**Verify**: ~50 new tests + ~80–100 prior + 361 baseline ≈ ~510 OK.

**Compare:** N/A (helper extension).

---

#### Step 3.2: Extend `/generate-docs` spec for concern dispatch

**Brief to `instruction-author` + `claude-code-guide` + `instruction-reviewer`**:
- **Goal**: extend `src/commands/generate-docs/main.md` so Phase 3 of the spec instructs the LLM to detect substantive subfolders and dispatch one `add-concern` + slot-fill cycle per concern. After all concerns registered, `validate-package` (which now includes the decomposition gate) catches missed concerns. Per the open-decision item #9 architecture decision, concern dispatch is orchestrator-direct (per-concern subagents dispatched via the Agent tool with inline briefs) — NOT routed through the `tech-writer` SKELETON-FILL MODE subagent.
- **Resume-mode slot-skip behavior (mandatory)**: when `/generate-docs` is invoked with state pre-existing — Phase 0's Resume branch (added at commit `ebd3f21`) keeps state instead of resetting — the per-concern dispatch brief must include explicit "skip slots already populated; fill only `[TODO]` slots" instruction. The motivation is **correctness + UX** (Resume should resume, not redo): a package whose only un-filled slot is a single export must not trigger a full re-read of the package's source — the dispatched subagent reads only what's needed to fill the remaining `[TODO]`s. This must be made explicit in the dispatch brief shape (orchestrator-composed inline brief per concern). Speed benefit is a side effect, not the driver.
- **Per-concern dispatch parallelism (mandatory)**: per-concern dispatches for a single package MUST run in parallel — single orchestrator message containing multiple `Agent` tool blocks (each with its own inline brief), one per concern, dispatched simultaneously per Claude Code's parallel-tool-call mechanism. Sequential dispatch is forbidden at this step. The motivation is **architectural** — concerns within a single package are independent (each fills its own slots from a disjoint source-tree subset; no cross-concern data dependency); sequential dispatch would impose an artificial ordering. Verify by inspecting the orchestrator's invocation log: the N concern subagents launched within the same dispatch turn. This is orthogonal to per-package parallelism (Phase 7.1's thresholds): per-concern parallelism is INSIDE a single package, per-package parallelism is ACROSS packages. A workspace with N packages × M concerns per package benefits from both axes. Wall-clock observation: per-concern parallelism naturally drops total fill time to (longest concern's fill time + dispatch overhead) vs (sum of all concerns' fill times) — record this as side-effect data, not as the success criterion.
- **Cross-check / impact analysis**: every concern subcommand named in spec must exist in Step 3.1's helper; iteration banner stays single-package; the dispatch-brief shape makes Resume-mode slot-skip explicit (verify by reading the brief's text, not just behavior); the spec's concern-dispatch section explicitly instructs parallel `Agent` tool dispatch (verify by spec text).
- **Loop**: instruction-reviewer + claude-code-guide audit. Iterate.

**Verify**: user runs `/generate-docs apps/app-web` again. Expected: 1 package doc + ~9 concern docs (matching cse-strata-ws-forge's 12-doc shape minus 2 that don't apply to testForge20).

**Compare**:
- File count: target 10–12 docs
- Decomposition: per-concern split (not monolith)
- Citation discipline: every code block validated
- Re-run idempotency at helper level: back-to-back `render-concern-doc` invoked on the same stable state produces zero diff. Note: full `/generate-docs` concern dispatch is NOT byte-idempotent across runs (LLM judgment varies — different exports / hazards / prose per run). This verify bullet checks render mechanics only; LLM-in-loop variance is by design and outside this success criterion
- **Per-concern parallelism (success criterion)**: inspect orchestrator's invocation log for the run — N concern subagents must launch within the same dispatch turn (single message, multiple `Agent` tool blocks). If the log shows sequential dispatch, the spec's Phase 3 instructions are buggy → loop back to author. Wall-clock data recorded as observation only: (longest concern's fill time + dispatch overhead) vs (sum of all concerns' fill times) — captured in `GENERATE-DOCS-EXECUTION-LOG.md` as side-effect data, not as a gate.
- **Resume-mode slot-skip behavior (success criterion)**: a Resume run whose state already has most slots populated must NOT trigger a full source re-read for those packages — verify by reading the dispatch brief text (it says "fill only `[TODO]` slots") and by inspecting the subagent's reported reads (only files needed for remaining `[TODO]`s). Wall-clock for Resume vs fresh run captured in `GENERATE-DOCS-EXECUTION-LOG.md` as observation only.

If file count short of target, the decomposition gate should have caught missing concerns. If gate didn't catch, gate is buggy → loop back to Step 3.1.

---

### Phase 4 — Architecture skeleton (ArchitectureDoc)

#### Step 4.1: Extend helper with ArchitectureDoc subcommands

**Brief to `python-engineer`**:
- **Goal**: add architecture-tier subcommands per the Schema section (`add-architecture`, `add-architecture-pattern`, `add-architecture-layer`, `add-architecture-dep`, `add-architecture-decision`, `render-architecture-skeleton`, `validate-architecture`, `render-architecture-doc`). Output: `docs/architecture.md`.
- **Cross-check / impact analysis**: cross-package deps inferred from per-package `Dependency` entries with `kind=internal` — verify state coherence; tests ~30 new.
- **Loop**: `python-reviewer` audits.

**Verify**: ~30 new + ~510 prior ≈ ~540 OK.

#### Step 4.2: Extend `/generate-docs` spec for architecture pass

**Brief to `instruction-author` + `instruction-reviewer` + `claude-code-guide`**:
- **Goal**: spec drives architecture pass after all packages registered.
- **Cross-check / impact analysis**: cross-pkg dep references must resolve to registered packages; spec's iteration banner expanded to include "single-project architecture pass" scope.
- **Loop**: reviewers audit.

**Verify**: user runs full cycle. Architecture doc produced. Compare to cse-strata-ws-forge `docs/db-cse-ui-strata/architecture.md`.

---

### Phase 5 — Memory archaeology

#### Step 5.1: Extend helper with MemoryFinding subcommands

**Brief to `python-engineer`**:
- **Goal**: add `add-memory-finding`, `render-memory-skeleton`, `validate-memory`, `render-memory-md` (appends to `.devforge/memory.md`).
- **Cross-check / impact analysis**: memory file path conflict with existing `.devforge/memory.md` schema; merge semantics if file exists; tests ~20 new.
- **Loop**: `python-reviewer` audits.

**Verify**: ~20 new + ~540 prior ≈ ~560 OK.

#### Step 5.2: Extend `/generate-docs` spec for memory archaeology pass

**Brief to `instruction-author` + reviewers**:
- **Goal**: spec drives source-reading walk producing categorized findings via the new API.
- **Cross-check / impact analysis**: confirm pass runs as separate source-reading walk (not summary of already-generated docs); per `Pass 2C` design in current /onboard spec, this is a distinct prompt with its own template.
- **Loop**: reviewers audit.

**Verify**: user runs full cycle. `.devforge/memory.md` populated.

---

## Track B — Retrieval-optimization scripts

These scripts run on already-generated `docs/` and produce the artifacts `/research` directly consumes.

**Execution order (priority-driven, NOT numerical step order)** — based on `/research` consumer protocol priority table:

1. **Step 6.4 — Topic index (J)** — first, because it's `/research`'s entry point.
2. **Step 6.3 — Glossary extraction (C)** — second, term disambiguation at retrieval entry.
3. **Step 6.2 — Reverse index (B)** — third, file→doc lookup during exploration.
4. **Step 6.6 — Pattern catalog (D)** — fourth, prior-art references.
5. **Step 6.5 — Accuracy validation (A)** — fifth, filter for stale citations.
6. **Step 6.7 — Constitution anchors (H)** — sixth, after `/constitute` populates rules.
7. **Step 6.8 — Freshness footers (I)** — last, per-doc metadata.

Each script is a `python-engineer` task with `python-reviewer` audit per the mandatory loop. Each script's brief includes goal / integration / constraints / edge cases / success criteria / cross-check + impact analysis / out-of-scope.

### Step 6.1: Pre-step — `extract-package-scripts` subcommand

Already specified as part of Step 1.2's helper subcommand surface. No separate script — this is a helper subcommand, not a standalone script.

### Step 6.2: Script B — Reverse index (`scripts/build_docs_index.py`)

**Brief to `python-engineer`**:
- **Goal**: parse all `*.md` in `docs/<project>/` for `<!-- path:line -->` markers + prose path mentions; build forward index doc→files; invert to file→docs; extract H2/H3 + bolded terms for concept→docs; write `docs/index.md`.
- **Constraints**: idempotent, alphabetically sorted, stdlib only.
- **Cross-check / impact analysis**: confirm citation marker regex matches the format `generate_docs_helper` produces in Step 1.2; confirm no other `docs/index.md` consumer expects a different shape.
- **Tests**: ~15. End-to-end on testForge20 docs/.
- **Loop**: reviewer audits.

### Step 6.3: Script C-extraction — Glossary terms (`scripts/extract_glossary_terms.py`)

**Brief**: extract candidate terms by ecosystem-aware identifier convention (per Principle 5 — ecosystem-agnostic by design):

- **All ecosystems**: `ALL_CAPS_SNAKE_CASE` constants (acronyms, configuration keys)
- **JS/TS**: `camelCase` exports (functions, vars), `PascalCase` types/interfaces/classes
- **Python**: `snake_case` module-level functions/vars (frequency ≥3), `PascalCase` classes
- **Rust**: `snake_case` public functions, `PascalCase` types/traits/enums
- **Go**: capitalized identifiers (export signal — first letter uppercase)
- **Java/Kotlin**: `camelCase` methods, `PascalCase` classes/interfaces
- **C#**: `PascalCase` for both methods and types
- **Ruby**: `snake_case` methods, `PascalCase` classes/modules

For each candidate term: search for definitions in language-specific docstring conventions (JSDoc `/** */`, Python docstrings, Rust doc comments `///`, Go doc comments above declarations, Javadoc `/** */`, RDoc `# `), type definitions with description comments, and existing doc mentions. If a definition is found in code → include verbatim. If not → mark `[TODO: human-define]`. Sort sections by frequency of appearance (most-used first).

**Output**: write to `docs/glossary.md` (overwrite if exists; idempotent per Base acceptance criterion 1).

Tests ~10, covering at minimum JS/TS, Python, Rust, and Go fixtures.

### Step 6.4: Script J — Topic index (`scripts/build_topic_index.py`)

**Brief**: read `.devforge/init.yaml`'s `packages_detected` array (populated by `/init-forge`, ecosystem-neutral) for the workspace's package set. For each detected package, build one topic-index row. Sub-topic iteration dispatches by ecosystem (per Principle 5): for JS/TS and Rust → scan `src/*`; for Go → scan `cmd/`, `pkg/`, `internal/` at the unit root; for Python → scan `src/<pkg>/` subfolders (PEP 621 `src/` layout) or the package root's direct subfolders (flat layout); for Java/Kotlin → scan immediate children of `src/main/java/<groupId>/<pkg>/` (Java) or `src/main/kotlin/<groupId>/<pkg>/` (Kotlin); use whichever root directory exists (some hybrid projects have both — scan both in that case); for all other ecosystems → fall back to any direct subdirectory at the unit root with ≥5 source files. Apply the sub-topic threshold uniformly across ecosystems: ≥3 substantive subdirectories AND each containing ≥5 source files OR clear architectural role (e.g., `src/quote/`, `cmd/server/`, `pkg/auth/`). Below threshold → one row per package; at-or-above threshold → iterate inner folders as sub-topics.

Each row's columns:

| Topic | Brief | Domain terms | Code locations | Reference docs |
|-------|-------|--------------|----------------|----------------|

- **Topic**: directory name with prefix stripped (`pkg-cse-quote` → "Quote"; `users-api` → "Users-Api")
- **Brief**: first paragraph of `index.md` Overview, or `[no description — see <reference docs>]` fallback
- **Domain terms**: top 10–15 most-frequent identifiers in the topic's source files, filtered against language-specific common-noise lists (e.g., JS/TS: `function const return import export`; Python: `def class import from return`; Rust: `fn pub use mod return impl`; Go: `func var package import return`) and against the glossary's known terms
- **Code locations**: the topic's directory path
- **Reference docs**: docs that contain path mentions of files in this directory (joined from Step 6.2's reverse-index output)

**Output**: write to `docs/topic-index.md` as a single markdown table sorted alphabetically by topic name (overwrite if exists; idempotent per Base acceptance criterion 1). Tests ~10, covering at minimum: a multi-package monorepo (testForge20-shaped), a single-package project, and a densely-featured package that triggers sub-topic iteration.

**Note**: this is the highest-priority Track B script per the consumer protocol — it is `/research`'s entry point.

### Step 6.5: Script A — Accuracy validation (`scripts/validate_doc_claims.py`)

**Brief**: for each citation marker → re-read source at cited range → compare to doc's code block (whitespace-normalized) → flag STALE with diff. For prose path mentions → verify file exists. For script-command mentions, dispatch by ecosystem (per Principle 5, mirroring Step 1.2's manifest dispatch table): `npm run X` (JS/TS) → check `package.json` `scripts` contains X; `poetry run X` or `python -m X` (Python) → check `[tool.poetry.scripts]` in `pyproject.toml` or `[project.scripts]` in PEP 621 form; `cargo X` (Rust) → validate against known cargo subcommands + `[package.metadata.scripts]` if present; `mvn X` (Java/Maven) → validate against Maven standard lifecycle phases and goals; `./gradlew X` (Java/Gradle) → validate against known Gradle lifecycle phases plus best-effort static parse of top-level `task` declarations in `build.gradle` / `build.gradle.kts`; do NOT shell out to `./gradlew tasks`; `dotnet X` (.NET) → validate against standard `dotnet` subcommands; `go X` (Go) → validate against the standard `go` subcommand list; `bundle exec rake X` (Ruby) → best-effort static parse of top-level `task :name` declarations in Rakefile; mark as N/A for dynamically-defined tasks; do NOT shell out to `rake -T`; `composer X` (PHP) → check `composer.json` `scripts` block contains X; other ecosystems → skip script-command validation and log as N/A. Tests ~10 including stale/missing fixtures.

### Step 6.6: Script D — Pattern catalog (`scripts/build_pattern_catalog.py`)

**Brief**: per pattern category, identify the canonical reference implementation by import-graph fan-in (most-imported file = canonical example). Pattern categories are **discovered per project, not hardcoded** (per Principle 5 — ecosystem-agnostic by design):

- The script first builds the import graph for the workspace using language-appropriate parsers (TypeScript imports, Python `import`/`from`, Rust `use`, Go `import`, Java `import`, etc.)
- For each top-level source-folder pattern (e.g., files matching `*BLoC.ts`, `*Service.ts`, `routes/*.ts` in JS/TS; `repositories/*.py`, `models/*.py` in Python; `traits/*.rs`, `services/*.rs` in Rust; `cmd/*.go`, `handler/*.go` in Go), count fan-in
- High-fan-in files within each pattern become the canonical example for that pattern
- Pattern category names are inferred from the directory/filename conventions present in the project — NOT hardcoded as "BLoC" / "GraphQL query" / "Vue composable" (those are JS/TS/Vue-specific)

Output table: `Pattern | Reference implementation path | Used when (one-line description extracted from file's top comment if present, else [TODO])`. Tests ~5, covering JS/TS + Python + Rust fixtures at minimum.

### Step 6.7: Script H — Constitution anchors (`scripts/scan_constitution_anchors.py`)

**Brief**: parse constitution.md for rule markers; search docs/ for cross-references; output report of unanchored rules. Tests ~5.

### Step 6.8: Script I — Freshness footers (`scripts/add_freshness_footers.py`)

**Brief**: for each doc, run `git log -1 --format=%H,%ai` against doc itself and citation-referenced source files; append footer with most-recent timestamp. Tests ~5.

---

## Phase 7 — Compose pipeline + spec finalization + multi-package run

### Step 7.1: Lift iteration banner from `/generate-docs` (NOT `/onboard`)

**Brief to `instruction-author` + reviewers**:
- **Goal**: remove the single-package iteration banner from `src/commands/generate-docs/main.md`. Spec now drives full multi-package + architecture + memory archaeology workflow.

  The multi-package flow is structurally identical to Phase 2.2's single-package flow — orchestrator-direct slot-fill, repeated per package in `packages_detected[]`. Default sequential per-package processing (one orchestrator pass at a time). For workspaces where sequential processing is wall-clock infeasible, dispatch per-package via the Agent tool with inline briefs (orchestrator-direct, not routed through the `tech-writer` SKELETON-FILL MODE subagent — see open decision #9). Parallelism thresholds (<50 source files = direct, 50–500 = sequential or small parallel batches per-package, 500+ = parallel batches) apply to the per-package Agent dispatch decision when wall-clock requires it. The slot-fill contract (helper API, citation discipline, validate-then-render flow) does NOT change between single-package and multi-package — only the loop count and (when wall-clock requires) the dispatch shape.
- **Cross-check / impact analysis**: every helper subcommand named in spec must exist; testForge20 deployment of the updated spec doesn't break the previously-iterated `apps/app-web/` doc; `/onboard`'s iteration banner is NOT touched (this plan does not modify `/onboard` per user directive).
- **Loop**: reviewers audit.

**Verify**: user runs `/generate-docs` (no scope flag) on testForge20.
- Target: ≥97 generated docs (matching cse-strata-ws-forge full count)
- Every package + concern doc present
- `docs/architecture.md` produced
- `.devforge/memory.md` populated
- Idempotency at helper level: back-to-back `render-package-doc` / `render-concern-doc` invocations on stable state produce zero diff. Full `/generate-docs` re-run is NOT byte-idempotent across runs (LLM judgment varies — different exports / hazards / prose per run); shape and citation discipline remain stable.

### Step 7.2: Repo-wide cross-reference cleanup (still pre-Phase-8.2 retirement)

**Brief to `instruction-author` + reviewers**:
- **Goal**: grep for `/generate-docs`, `generate_docs_helper`, `.generate-docs-state.json` across CLAUDE.md / DEVELOPMENT-STATUS.md / CHANGELOG.md / install.sh / update.sh / scripts/emitters/claude.py / Memory files. Update or add references where appropriate. Annotate `ARCHITECTURE-PIVOT-PLAN.md` Step 2 as superseded by this plan. Annotate memory `project_schema_anchored_generate_docs.md` as foundation; the python-skeleton primitive realizes it.
- **Cross-check / impact analysis (mandatory)**: per `feedback_cross_check_after_every_change.md`, end state must have zero dangling references repo-wide. **`/onboard` references stay intact** at this stage — removal is in Phase 8.2.
- **Loop**: reviewer audits with full repo-wide grep verification.

**Verify**: repo-wide grep returns no dangling references to `/generate-docs`. Tests still passing. `/generate-docs` install end-to-end on a fresh tmpdir produces a working command. `/onboard` install end-to-end on a fresh tmpdir still produces today's working `/onboard` (untouched).

---

## Phase 8 — Empirical gate + old-code retirement

**This phase is the validation that the entire rewrite hit its goal.** Per the goal section: doc quality is judged by how much retrieval recall it gives `/research`. Phase 8 measures exactly that. **Phase 8.2 is also where old `/onboard` code is removed**, per user directive: "u will develop new scripts, old will be removed."

### Step 8.1: Parity test on `/research`

Per `Documentation Strategy - Research-Quality Optimization.md`'s acceptance criteria:

- Same `/research` prompt across ≥4 sessions
- Baseline: pre-rewrite retrieval recall (measured against today's testForge20 docs/, before Track B scripts run)
- Target: ≥20% improvement in cited-relevant-files

Two prompt families:

**Family A — retrieval breadth/depth:**
- "Investigate the BLoC adapter pattern's coverage across packages and identify gaps"
- "Map the auth flow from Okta token to permitted route entry"
- "Find every place quote state is persisted vs derived"

**Family B — intent analysis (the "preliminary analysis of what the human wanted" capability):**
- "I want to add the ability to delete a quote line"
- "Make the org switcher smarter"

For each prompt: 4 sessions pre-rewrite + 4 sessions post-rewrite. Measure:
- **Retrieval recall**: count of relevant files cited (target ≥20% improvement)
- **Concept coverage**: count of domain concepts mentioned correctly (target ≥20% improvement)
- **Decision variance**: cross-session variance on what's in scope (target reduction)
- **Intent-analysis quality**: does `/research` surface ambiguity that requires clarification, vs jumping to implementation? (qualitative — user judges)

**Verify**: protocol documented; numbers recorded in `GENERATE-DOCS-EXECUTION-LOG.md`.

**Compare**: to baseline. If target hit → rewrite succeeded; proceed to Step 8.2. If target missed → investigate which artifact is failing to deliver retrieval lift before any retirement.

### Step 8.2: Retire `/onboard` (old code removal)

Once Step 8.1 confirms `/generate-docs` quality, remove the old code per user directive. Agent-mediated:

**Brief to `python-engineer` (removal task)**:
- **Goal**: remove all artifacts of the old `/onboard` command:
  - `src/commands/onboard/` directory (the spec)
  - `src/devforge/lib/onboard_helper.py` + launcher
  - `tests/lib/test_onboard_helper.py` (if any was added later)
  - `.vault/devforge/lib/onboard_helper.py` (or keep as historical artifact — orchestrator decides per `feedback_cross_check_after_every_change.md` after evaluating value)
- **Cross-check / impact analysis (mandatory)**:
  - Grep for every `/onboard` reference in install.sh / update.sh / CLAUDE.md / docs / specs / tests / scripts
  - Each reference must be updated, replaced with `/generate-docs`, or removed cleanly
  - If a reference can't be cleanly updated (e.g., a doc captures historical context), halt and ask
  - Confirm `.claude/agents/python-engineer.md` reference to `.vault/` either updates or removes
  - Confirm `scripts/emitters/claude.py` `_PROMOTED` removes `"onboard"` (`"generate-docs"` stays)
- **Loop**: `python-reviewer` audits with full repo-wide grep. Iterate.

**Brief to `instruction-author` (spec/doc cleanup)**:
- **Goal**: update CLAUDE.md (project + template), DEVELOPMENT-STATUS.md, CHANGELOG.md, README, ARCHITECTURE-PIVOT-PLAN.md, and any other plan/spec files that reference `/onboard`. Replace with `/generate-docs` or remove. Annotate the changelog entry: "X.Y.Z: removed /onboard (replaced by /generate-docs); see GENERATE-DOCS-PLAN.md Step 8.2."
- **Cross-check / impact analysis**: end state must have zero `/onboard` references in active code paths. Historical references in commit messages and Obsidian notes are out of scope.
- **Loop**: `instruction-reviewer` + `claude-code-guide` audit.

**Verify**:
- `grep -rn "/onboard\|onboard_helper\|src/commands/onboard" .` (excluding `.git/`, `.vault/` if kept) returns zero matches in active code
- All tests still passing
- testForge20 install: `/onboard.md` no longer ships; `/generate-docs.md` ships
- Existing docs already generated by `/generate-docs` are unaffected

**Decision on Mode 2 (interview-driven content) follow-on plan**:
- Mode 2 work (decision rationale, anti-pattern catalog, deep playbooks, glossary definitions) — justified if Step 8.1 hits target. Author follow-on plan (separate from this one).
- Decision documented in `GENERATE-DOCS-EXECUTION-LOG.md`.

---

## Cost estimate

| Phase | Steps | Sessions | Lines of code |
|---|---|---|---|
| Phase 1 (foundation) | 2 | 1–2 | ~600 (schema + helper + tests) |
| Phase 2 (per-package) | 3 | 1–2 | ~300 (spec + emitter + iteration) |
| Phase 3 (per-concern) | 2 | 1 | ~400 (helper extension + spec) |
| Phase 4 (architecture) | 2 | 1 | ~300 (helper extension + spec) |
| Phase 5 (memory) | 2 | 0.5 | ~200 (helper extension + spec) |
| Phase 6 (Track B scripts) | 7 | 2–3 | ~1000 (7 scripts) |
| Phase 7 (integration) | 2 | 1 | ~200 (spec polish + cross-ref) |
| Phase 8 (gate + retirement) | 2 | 1 | (measurement + removal, ~100 lines net) |

**Total: ~3000 lines of Python infrastructure + spec + tests, across ~10–12 sessions** (slightly higher than initial estimate due to agent-mediated discipline overhead — every step's loop adds review iterations, but the loop catches issues before integration vs after).

---

## Compare-as-you-go discipline (incremental verification)

Each step's verify section lists what to compare against. Concrete protocol per step:

1. **Before the step**: orchestrator snapshots relevant testForge20 state (commit-id of testForge20, byte-count of `docs/`, file-count, contents of `.devforge/.generate-docs-state.json`). Records in `GENERATE-DOCS-EXECUTION-LOG.md`.
2. **After the step**: re-run any affected `/generate-docs` flow on testForge20. Capture the same artifacts.
3. **Diff**: programmatic diff against snapshot + against published baseline (cse-strata-ws-forge reference, today's reference-spec /onboard run, today's heavy-spec /onboard run — whichever is the relevant comparison).
4. **Decide**: continue / iterate within step / pause for design decision. Don't proceed to next step if comparison fails verify criteria.

`GENERATE-DOCS-EXECUTION-LOG.md` lives at the repo root, created in Phase 1.1's first session. Accumulates step-by-step outcomes — what was built (which agents, which loops), what the comparison showed, what decisions were made. This is the compare-results infrastructure + the audit trail for the agent-mediated workflow.

---

## Open decisions

These need user input before or during execution:

1. **Section template uniformity** — strict A.2.1 (Overview / Directory / Main Exports / Types / Dependencies / Usage Example) like cse-strata-ws-forge reference, OR content-driven labels like today's testForge20 reference run? Strict wins on agent-load predictability; content-driven wins on readability. **Default in plan: strict A.2.1** — schema enforces it.
2. **`Hazard` section in package docs** — first-class section (visible to LLMs as `## Hazards`) vs internal to memory archaeology only? **Default: first-class** — today's heavy-spec run produced 5 inline hazard callouts and they were valuable.
3. **Concern doc label** — `## Public Surface` (cse-strata-ws-forge) or `## Main Exports` (today's heavy-spec)? **Default: `## Public Surface` at concern, `## Main Exports` at package-index level** (matches cse-strata-ws-forge).
4. **Track B sequencing** — interleave with Track A or land Track A complete first? **Default: after Track A Phase 2 lands, then priority order: J → C → B → D → A → H → I.**
5. **Single-package iteration scope for Phase 2** — testForge20 `apps/app-web/` (current iteration target) or smaller package? **Default: `apps/app-web/`** — already wired, comparison baselines exist.
6. **Tests directory for scripts** — `tests/scripts/` vs `tests/lib/`? **Default: `tests/scripts/`** for parallel structure with `scripts/`.
7. **`.vault/` retention in Phase 8.2** — keep `.vault/devforge/lib/onboard_helper.py` as historical artifact (referenced by `python-engineer.md` for anti-pattern lessons) or remove? **Default: keep `.vault/`** until a follow-on plan decides; `python-engineer.md` explicitly cites it as reference.
8. **Tech-writer subagent — agreed scope (RESOLVED)**: reintroduce `tech-writer` as a dedicated agent file at `.claude/agents/tech-writer.md` (~30 lines + frontmatter). Drafted paired with Phase 2.1's `/generate-docs` spec in the same `instruction-author` dispatch. Used from Step 2.2's single-package iteration onward (Phase 7.1's multi-package is the same dispatch repeated). Skeleton-fill primitive shrinks the agent contract from ~100–150 lines (if the agent owned templates) to ~30 lines (helper owns templates; agent fills slots + runs validate). User-agreed during Step 1.2a session.
9. **Phase 3 dispatch model — empirically resolved (RESOLVED post-A/B comparison)**: orchestrator-direct slot-fill is the canonical Phase 3 architecture for `/generate-docs`. Decision #8 above chose to introduce a tech-writer subagent for SKELETON-FILL MODE; empirical A/B comparison on testForge20 in subsequent iteration showed:
   - Option A (tech-writer subagent dispatch): 7 exports, 2 hazards, 9 citations; helper-API contract broken (2 direct JSON edits to state file); workspace-internal deps misclassified (all 19 internal misclassified as external)
   - Option B (orchestrator-direct slot-fill): 16 exports, 9 hazards, 18 citations; helper-API contract respected; workspace-internal deps correctly classified

   Option B's wins (2–4× coverage, no contract breaks, correct classification) are decisive at Phase 2's single-package scope. The orchestrator (Claude Code main session running `/generate-docs`) has full source context + full spec context, allowing it to surface helper-API walls cleanly rather than bypass them — exactly the failure mode the helper-mediated architecture was designed to prevent. Tech-writer subagent's scoped context made it more likely to choose bypass over abort when hitting a wall.

   **Implications**:
   - `src/agents/tech-writer.md` SKELETON-FILL MODE section retained for future reference / potential Phase 7.1 reuse, but NOT INVOKED by current `/generate-docs` spec.
   - Phase 3 (concern decomposition) inherits orchestrator-direct: the orchestrator dispatches per-concern subagents directly via the Agent tool with inline briefs (no SKELETON-FILL-MODE tech-writer in between).
   - Phase 7.1 (multi-package) defaults to orchestrator-direct sequential per-package processing; reintroduce tech-writer or generic Agent dispatches ONLY if wall-clock makes sequential infeasible.
   - Tech-writer's other modes (ONBOARDING for legacy `/onboard`, default Normal Mode for `/finalize` / fix / refactor doc updates) remain valid — this decision scopes only to `/generate-docs`'s SKELETON-FILL flow.

   **Carry-forward**: Phase 3.1 (`extend helper with ConcernDoc subcommands`) and Phase 3.2 (`extend /generate-docs spec for concern dispatch`) updated to reflect orchestrator-direct dispatch (NOT tech-writer subagent). Phase 7.1's "structurally identical to Phase 2.2's single-package flow" statement is now correct under this resolution: single-package single-orchestrator → multi-package multi-orchestrator-dispatch. Decision #8 is preserved above as the historical record of the original choice; this item supersedes its dispatch model.

---

## Integration with existing plans + memory

- **`ARCHITECTURE-PIVOT-PLAN.md` Step 2** — superseded by this plan. Annotation added in Step 7.2.
- **Memory `project_schema_anchored_generate_docs.md`** — foundation for this plan's schema. The python-skeleton primitive is the *implementation pattern* that realizes the schema-anchored design. Annotation added in Step 7.2.
- **Memory `project_schema_anchored_constitute.md`** — sibling for `/constitute`. Same primitive applies (`/constitute` rewrite is `ARCHITECTURE-PIVOT-PLAN.md` Step 8). Out of scope for this plan; tackled later.
- **`/onboard` (existing)** — untouched throughout Phases 1–7 of this plan. Iteration banner stays. Vault-restored helper stays. **Removed in Phase 8.2** after the empirical gate validates `/generate-docs`.

---

## When resuming work

1. Read this plan in full — pay attention to the **⚠️ Execution discipline** section near top. Agent-mediated only; no orchestrator-direct writes.
2. Check current branch: `develop-2.0-init`. If different, switch.
3. Verify test baseline: `python3 -m unittest discover tests/lib -q` should report at least 336 OK plus tests added by completed phases.
4. Check `GENERATE-DOCS-EXECUTION-LOG.md` for last completed step + agent loop outcomes + decisions made.
5. Pick up at the next uncompleted step.
6. **Always** apply the agent-mediated mandatory loop: brief → engineer does work + cross-check + impact analysis → reviewer audits → loop until clean → integrate → log.
7. Commit each step independently. Don't bundle. Each commit message references the step (e.g., `generate-docs: Step 1.1 — schema + tests`).
8. After each step, update `GENERATE-DOCS-EXECUTION-LOG.md` with: step ID, commit SHA, agents invoked, loops needed, comparison outcomes, decisions made, future-session-falsely-believes check result.
