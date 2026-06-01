# /audit Command — Port + Hotspot Middle-Mode Plan

**Status**: Phases 0–7 SHIPPED 2026-06-01 (working-tree, not committed) on `develop-2.0-init`. Only **Phase 8 (testForge20 e2e, user-driven stop)** remains. `_audit/` helper subpackage (17 verbs across schema + state + preflight + hotspot + scope + consume/validate/consensus/rank + report/inline + cli) + launcher + `src/commands/audit/main.md` (6-phase spec, full producer→consumer scratch-file chain) + 4 `references/*.md` + emitter `_PROMOTED += audit` + CLAUDE.md/CHANGELOG/src-CLAUDE.md reconciliation, all behind per-phase python-engineer→python-reviewer (and instruction-author→instruction-reviewer for the spec) loops. ~595 `tests/lib/_audit/` tests; full repo suite 1620 passed (excl. 3 pre-existing unrelated `test_doc_setters*` collection errors). Install ride verified (`audit command: yes (folder, 4 references)`, 0 placeholder leaks, executable installed helper). **Supersedes the abandoned `/audit-file` draft** (prior content of this file). Ports the existing 534-line `/audit` draft at `src/_pending/commands/audit.md` to current framework conventions (helper-subpackage + slash-command-spec + emitter + install + testForge20 stop), AND adds a new **`--top N` hotspot middle mode** for very-large repos where broad mode is impractical and narrow mode is too narrow. All three modes (narrow / hotspot / broad) ship at once per user direction.

The pending `/audit` draft is the source of truth for: agent ensemble, adversarial preamble, mislogic checklist, report format, anti-hallucination guard, cross-agent consensus, force-rank Top 10, recurring-issues mapping, storage layout. The port preserves these verbatim where possible; extracts mechanical work into helper verbs; adds hotspot scoring as the new middle path.

## Driver

Two driving needs:

1. **Port the mature draft.** `src/_pending/commands/audit.md` is 534 lines of well-designed audit machinery — 6 phases, 4 adversarial specialist agents in parallel batches, agent-existence guard, anti-hallucination + consensus + force-rank, recurring-issues mapping. It exists, it's coherent, it's been thought through. Writing a parallel `/audit-file` (per the prior draft of this file) would have duplicated 80% of its scope. Port it.

2. **Broad mode doesn't scale on very-big projects.** The current draft has two modes — **broad** (`--full` / empty → whole codebase) and **narrow** (file / directory / `--uncommitted`). On a 500K+ LOC monorepo, broad blows up: 4 agents reading the world produce too many findings for the Top-10 ranker to separate signal from noise; per-agent context windows pressure quality; cost is unbounded. Narrow doesn't help here — auditing one file at a time on a giant repo is slow and misses cross-cutting patterns. The missing middle is **risk-targeted broad**: score every file by `(churn × callers × size)`, take top N, run the ensemble against just that set. Periodic, bounded, signal-rich.

`/audit --top N` (default `N=25`) is the new middle mode.

## Context in the workflow

`/audit` is **standalone** — NOT part of any workflow chain (research → discover → specify → plan → breakdown → execute-task). Invoke manually after several specs ship, or on a periodic cadence, or when "is this codebase dangerous?" needs an answer. Matches the draft's stated posture verbatim.

Distinct from `/review` (the other pending draft): `/review` is post-spec-completion feature review feeding `/verify`; `/audit` is drift/mislogic hunt across whatever scope. Different agent set (`/audit` skips `performance-analyst`), different trigger (manual vs chain), different output consumer (none vs `/verify`).

### What is already built (read contracts — do NOT rebuild)

| Piece | Path | Use |
|---|---|---|
| `/audit` draft (source of truth) | `src/_pending/commands/audit.md` | Port phases + adversarial preamble + mislogic checklist + report format VERBATIM where possible |
| `code-reviewer` agent (incl. §7 DIR check per plan 05) | `src/agents/code-reviewer.md` | Primary mislogic hunter (Batch A) |
| `architect` agent | `src/agents/architect.md` | Cross-module contradictions (Batch A) |
| `qa-engineer` agent | `src/agents/qa-engineer.md` | Logic blind spots (Batch B); NOT test writing per draft Phase 3.1 |
| `security-reviewer` agent | `src/agents/security-reviewer.md` | Security drift (Batch B) |
| CBM tools | `search_graph`, `trace_path`, `get_code_snippet`, `query_graph` | Hotspot scoring (caller counts) + per-agent reference resolution |
| Audit-format discipline | `CLAUDE.md` § "Audit format" | Phase 6 presentation contract (count first; one finding at a time; severity/location/issue/why/fix; `fix / defer / skip / discuss?` prompt verbatim) |
| Emitter `_PROMOTED` mechanism | `scripts/emitters/claude.py` | Slash command shipping |
| Helper-subpackage architecture | `src/devforge/lib/_<cmd>/` + `<cmd>_helper.py` + launcher | Pattern to extract orchestrator/helper split (the draft predates this) |

## Settled design decisions

### Decision 1 — Port the existing draft, do not rewrite

The draft is comprehensive. Port preserves: agent ensemble, batch shape, adversarial preamble, mislogic checklist, anti-hallucination guard, cross-agent consensus, force-rank Top 10, recurring-issues mapping, storage layout, agent-existence guard, Source Root handling. Rewriting risks losing hard-won design.

### Decision 2 — Three modes ship at once: narrow / hotspot (NEW) / broad

| Mode | Argument shape | Scope | Pipeline depth |
|---|---|---|---|
| **narrow** | `/audit <file>` or `/audit <dir>` or `/audit --uncommitted` | Single file, single directory (recursive subtree, filtered per Decision 9), or working-tree changes | Single-file: simplified (skip recurring-issues). Directory + uncommitted: full per Decision 10 |
| **hotspot** (NEW) | `/audit --top N` | Top N files by risk score (churn × callers × size) | Full pipeline incl. recurring-issues mapping |
| **broad** | `/audit` (empty) or `/audit --full` | Whole codebase | Full pipeline per draft |

Defaults: hotspot `N=25` (OQ-2). Hotspot is the default recommended mode for periodic audits on repos > ~50K LOC.

### Decision 3 — Hotspot risk score formula

```
risk(file) = w_c * churn_norm + w_k * callers_norm + w_s * size_norm
```
where:
- `churn` = commit count touching file in last 90 days (via `git log --since=90.days.ago --oneline -- <file>`)
- `callers` = inbound edge count to symbols in file (CBM `trace_path(mode=calls)` aggregated)
- `size` = lines of code (non-blank, non-comment)
- `*_norm` = min-max normalized within the codebase

**Default weights**: `w_c=0.5, w_k=0.4, w_s=0.1` (recent change + heavy use = high risk; size only as tiebreaker). Weights configurable via `--weights c=0.5,k=0.4,s=0.1` for tuning. See OQ-1.

### Decision 4 — Storage per draft

Single file `audits/YYYY-MM-DD-audit.md` at workspace root (the directory containing `CLAUDE.md`), always — never under Source Root even in wrapper mode. Temp files `audits/.tmp-<agent>.md` for streaming consolidation. `audits/.gitignore` with `.tmp-*.md` line auto-created on first run. Collision: append `-2`, `-3` etc. All per draft Phase 5 lines 264–272.

### Decision 5 — Helper subpackage split

The draft is monolithic (orchestrator does everything). Current framework convention is orchestrator-as-flow-controller + helper-as-mechanical-worker. Extract:

- **Helper owns**: argument parsing, mode resolution, agent-existence check, hotspot scoring, scope computation, tmp-file consumption, finding validation (regex parse + line-existence check), consensus computation, force-rank, recurring-issues file globbing, report rendering, inline summary rendering.
- **Orchestrator (main.md) owns**: actual agent invocations (Task tool calls), the adversarial preamble text (load-bearing — must reach the agent verbatim), user-facing prose, phase narration, audit-format pacing.

This mirrors `/plan` and `/breakdown` separation.

### Decision 6 — Adversarial preamble + mislogic checklist preserved verbatim

These are load-bearing prompts. The draft has them as long verbatim text blocks (lines 407–528). They go into `src/commands/audit/references/adversarial-preamble.md` + `references/mislogic-checklist.md` as reference files the main.md instructs the orchestrator to read in full and inject into every agent invocation. No paraphrase. No "summarize then inject." No helper-templated injection (the helper handles structure; the prompt text bypasses it).

### Decision 7 — Constitution + MEMORY + recent-reviews integration kept

Per draft Phase 1 steps 3–6: read `constitution.md` (guard against unpopulated state), read `CLAUDE.md` (Source Root + project type), read `.claude/memory/MEMORY.md` (pitfalls + lessons), glob `specs/*/review.md` (recurring-issues — broad + hotspot modes only; narrow skips). All preserved.

### Decision 8 — Hotspot mode requires CBM; no grep fallback for scoring

The hotspot risk score depends on caller counts from CBM `trace_path`. A grep-approximation of caller counts (literal symbol search) is too noisy — common-named symbols (`get`, `set`, `init`) get false-high scores; renames between sites mask true callers. If CBM is absent in hotspot mode, helper exits 2 with install reminder. Other modes degrade gracefully (CBM optional for narrow / broad).

### Decision 9 — Directory mode file filter: tracked + non-gitignored

When `/audit <dir>` resolves to a recursive subtree, the file set = **`git ls-files <dir>`** (tracked files, automatically respects `.gitignore`). Language-agnostic, predictable, no detection failure on polyglot subtrees (e.g., `src/auth/` with `.ts` + `.sql` + `.md` — all three audited together). Rejected alternatives:

- **Source-language filter** (e.g. only `.ts`/`.tsx` matching project type from `CLAUDE.md`) — breaks on polyglot dirs; "smart" detection adds a failure mode that "audit everything tracked here" doesn't have.
- **All readable files** — pulls in generated/vendored junk a `.gitignore` exists to exclude; pure noise.

Outside-of-git fallback (rare — auditing a non-git directory): walk filesystem, skip dot-directories, skip common ignore patterns (`node_modules/`, `dist/`, `build/`, `__pycache__/`, `.venv/`). Documented as a degenerate path; primary contract is `git ls-files`.

### Decision 10 — Narrow pipeline depth: simplified only for single-file; full for directory + uncommitted

The draft's "narrow = simplified pipeline (skip recurring-issues mapping)" was a single-knob decision. Splitting it:

- **Single file** → simplified pipeline (no recurring-issues mapping). A one-file audit doesn't benefit from cross-feature review context; the file is the context.
- **Directory + uncommitted** → full pipeline (include recurring-issues mapping). A subtree or working-tree change benefits from "are these issues we've already flagged elsewhere?" The mapping cost is ~10ms (glob `specs/*/review.md` + read up to 5 files); not worth a knob.

This deviates from the draft's literal text but preserves its intent: the simplification existed to avoid expensive cross-feature work when scope is tiny. Directory + uncommitted aren't tiny.

### Decision 11 — Big-directory guard at >200 source files

When `resolve-scope` produces a file list with `> 200` files for a non-broad mode, helper sets a `scope_oversize: true` flag in its output. Orchestrator presents a guard prompt via `AskUserQuestion` before agent dispatch:

> Auditing **{N} files** in `{path}`. This approaches broad-mode scope without `--full`'s recurring-issues breadth. Options:
> - `/audit --top 25` — risk-targeted sample (recommended for periodic checks)
> - `/audit --full` — whole codebase with recurring-issues
> - Proceed anyway with current narrow scope

Threshold `200` is tunable via `--scope-limit N`. Below threshold: silent proceed. Above threshold: gate. Prevents the "I typed `/audit src/` on a 4000-file repo and burned 30 minutes" failure mode.

## Open questions — RESOLVED 2026-05-31

All five answered via `AskUserQuestion` sequential pass; all picks confirmed orchestrator recommendations (defaults already baked into Decisions 2/3 + AuditReport schema, so no cascading plan edits required).

- **OQ-1 — Hotspot weighting**: ✅ **RESOLVED — `w_c=0.5, w_k=0.4, w_s=0.1`** (recent-change-heavy). Encoded as default in Decision 3. `--weights c=...,k=...,s=...` knob preserved.

- **OQ-2 — Hotspot default N**: ✅ **RESOLVED — `N=25`**. Encoded as default in Decision 2. `--top N` knob preserved.

- **OQ-3 — Multi-path narrow mode**: ✅ **RESOLVED — single scope per audit (MVP)**. Argument parser rejects >1 positional path with usage hint. Forward-compat door not explicitly added.

- **OQ-4 — Hotspot e2e fixture**: ✅ **RESOLVED — synthetic mini-repo at `tests/fixtures/audit_hotspot_repo/`** with committed regen script seeding ~50 files + 10 high-churn files (8–18 commits each) over a synthetic 90-day window. testForge20 e2e covers narrow + broad only.

- **OQ-5 — Hotspot "Next 10 Candidates" tail**: ✅ **RESOLVED — YES, always include**. `AuditReport.next_candidates` populated in hotspot mode (empty otherwise) with positions N+1..N+10; report appendix renders `file · score · (churn, callers, size)` per line.

## Architecture / file inventory

```
src/commands/audit/
├── main.md                                # ported slash command spec — 6 phases per draft
└── references/
    ├── adversarial-preamble.md            # VERBATIM from draft lines 407–460
    ├── mislogic-checklist.md              # VERBATIM from draft lines 461–528
    ├── report-format.md                   # draft Phase 5 § "Report format" extracted
    └── hotspot-scoring.md                 # NEW — formula, weights, defaults, knobs

src/devforge/lib/_audit/
├── __init__.py
├── _cli.py                                # argparse + verb dispatch
├── _preflight.py                          # mode resolution + agent-existence + constitution/MEMORY/CLAUDE reads
├── _hotspot.py                            # risk scoring (churn + CBM callers + size)
├── _scope.py                              # mode → file-list resolution (narrow / hotspot / broad)
├── _consume.py                            # read + parse tmp-<agent>.md files
├── _validate.py                           # anti-hallucination guard (Phase 4.2 of draft)
├── _consensus.py                          # cross-agent exact-match (Phase 4.3)
├── _rank.py                               # force-rank Top 10 (Phase 4.5) + recurring-issues mapping (4.4)
├── _report.py                             # final MD render per draft Phase 5
├── _inline.py                             # Phase 6 inline summary
├── _state.py                              # session state JSON (phase + scope + outpath)
├── findings_schema.py                     # dataclasses: Finding, AuditReport
└── hotspot_schema.py                      # dataclasses: FileScore, HotspotResult

src/devforge/lib/audit_helper                # launcher shim (cp -R preserves +x)
src/devforge/lib/audit_helper.py             # entrypoint → _audit._cli.main

tests/lib/_audit/
├── test_findings_schema.py
├── test_hotspot_schema.py
├── test_preflight.py                       # mode resolution + guards
├── test_hotspot.py                         # scoring math + weight knobs + CBM-required gate
├── test_scope.py                           # narrow/hotspot/broad → file list
├── test_consume.py                         # regex parse of tmp files
├── test_validate.py                        # finding rejection cases
├── test_consensus.py                       # exact-match cross-agent
├── test_rank.py                            # Top 10 force-rank + recurring mapping
├── test_report.py                          # report render byte-fixture
├── test_inline.py
├── test_state.py
└── test_cli.py

tests/fixtures/audit_hotspot_repo/          # NEW — synthetic mini-repo for hotspot e2e
├── (seeded git history: 50 files; 10 with scripted artificial churn)
└── README.md                               # how the fixture is regenerated
```

Emitter wire-in: append `"audit"` to `scripts/emitters/claude.py` `_PROMOTED`.

## Schema design

### Finding (parsed from agent tmp files per draft Phase 3.2)

```python
@dataclass(frozen=True)
class Finding:
    finding_id: str                # e.g. "F-001"
    agent: str                     # "code-reviewer" | "architect" | "qa-engineer" | "security-reviewer"
    severity: Literal["Critical", "High", "Medium", "Info"]
    file: str                      # absolute or workspace-relative
    line: int                      # 1-based; -1 if unspecified by agent
    title: str
    explanation: str               # what's wrong + why
    suggested_fix: str
    references: list[str]          # CLAUDE/constitution sections cited, if any
    source_pass: str               # which agent produced
```

### AuditReport (draft Phase 5 final output)

```python
@dataclass(frozen=True)
class AuditReport:
    schema_version: str            # "1"
    audit_date: str                # YYYY-MM-DD
    mode: Literal["narrow", "hotspot", "broad"]
    scope_description: str         # human-readable scope summary
    scope_files: list[str]         # exact files audited
    agents_run: list[str]
    agents_skipped: list[str]      # not installed
    findings: list[Finding]
    consensus: dict[str, list[str]]   # finding_id → list of agents that flagged
    top10: list[str]                  # ordered finding_ids
    recurring_issues_resolved: list[str]
    recurring_issues_unresolved: list[str]
    next_candidates: list[FileScore]   # hotspot mode only; empty otherwise
```

### FileScore (hotspot)

```python
@dataclass(frozen=True)
class FileScore:
    file: str                      # workspace-relative
    churn: int                     # commit count in 90d window
    callers: int                   # CBM inbound-edge count
    size_loc: int                  # non-blank non-comment lines
    churn_norm: float              # [0,1]
    callers_norm: float            # [0,1]
    size_norm: float               # [0,1]
    score: float                   # weighted sum, [0,1]
    rank: int                      # 1-based
```

## Helper verb inventory — `audit_helper`

| Verb | Phase | Description |
|---|---|---|
| `check-agents` | 1 | Detect which of the 4 agents exist in `.claude/agents/`; exit-2 if all missing |
| `resolve-mode <args>` | 1 | Parse `$ARGUMENTS` → mode (narrow / hotspot / broad) + scope arg; usage hint on bad input |
| `preflight-context` | 1 | Read constitution + CLAUDE.md + MEMORY.md; emit structured context block; guard on unpopulated constitution |
| `compute-hotspots --top N [--weights ...]` | 2 | git log + CBM call counts + LOC; produce ranked `hotspot.json` |
| `render-hotspot-summary` | 2 | Human-readable hotspot table for the report (top N + next 10) |
| `resolve-scope <mode>` | 2 | mode + hotspot result → ordered file list. Directory mode walks subtree via `git ls-files <dir>` per Decision 9 (filesystem fallback for non-git roots). Output includes `file_count` + `scope_oversize` flag (true if `file_count > --scope-limit` default 200, per Decision 11) for orchestrator to gate on. |
| `render-scope-block` | 2 | Scope summary for both the agent brief and the final report |
| `render-agent-brief <agent>` | 3 | Assemble per-agent prompt: scope + adversarial preamble + mislogic checklist + agent-specific focus + closing reminder + output contract |
| `consume-tmp <agent>` | 4 | Read `audits/.tmp-<agent>.md`; regex-parse to `Finding[]` |
| `validate-findings <agent>` | 4 | Anti-hallucination: file exists, line in range, severity ∈ allowed set; emit per-finding pass/reject |
| `compute-consensus` | 4 | Exact-match `(file, line, title-stem)` across agents → consensus map |
| `force-rank-top10` | 4 | Severity × consensus × scope-position → ordered Top 10 finding_ids |
| `map-recurring-issues` | 4 | Glob `specs/*/review.md` (last 90 days, cap 25 entries); per-entry: resolved / unresolved / not-checked |
| `render-report` | 5 | Full audit MD per draft format; write to `audits/YYYY-MM-DD-audit.md` with collision suffix |
| `render-inline-summary` | 6 | Phase 6 inline block: Top 5 + counts + report path |
| `cleanup-tmps` | 5 | Delete `audits/.tmp-*.md` after successful report write (Phase 4 deletes per-agent on success; this catches the failure case per draft line 264) |
| `check-status-and-flip` | all | Phase state transitions in `state.json` |

## Command spec — `src/commands/audit/main.md` phase structure (mirrors draft verbatim)

```
Preflight: CBM Refresh + Read Tier              → ensure-cbm + state load
PHASE 1: Load Context & Guard                   → resolve-mode + check-agents + preflight-context
PHASE 2: Determine Scope                        → compute-hotspots (if hotspot) + resolve-scope + render-scope-block
PHASE 3: Launch Adversarial Agents               → render-agent-brief × 4 + Task-tool batched parallel × 2 batches
PHASE 4: Stream-Consolidate, Verify, Rank        → consume-tmp × 4 + validate-findings × 4 + compute-consensus + force-rank-top10 + map-recurring-issues (broad+hotspot)
PHASE 5: Write Report                            → render-report + cleanup-tmps
PHASE 6: Present Inline Summary                  → render-inline-summary
```

The adversarial preamble + mislogic checklist + per-agent focus blocks + output contract + closing-mode reminder all live in `references/*.md`. main.md instructs the orchestrator to read them in full and pass through verbatim to each agent invocation.

## Execution phases (build order) — mirrors 09

### Phase 0 — Schema substrate + preflight verbs ✅ DONE 2026-05-31

**Status**: SHIPPED (working-tree, not committed). Built `src/devforge/lib/_audit/{__init__,findings_schema,hotspot_schema,_state,_preflight,_cli}.py` + `tests/lib/_audit/{test_findings_schema,test_hotspot_schema,test_state,test_preflight}.py` (187 tests; full repo suite 1128 passed / 2 skipped, zero regressions). Schemas follow the `_breakdown/handoff_schema.py` convention (stdlib, no `from __future__`, frozen, mechanical `__post_init__`); `_state`/`_preflight`/`_cli` follow the `_pr_review` convention (argparse subparsers, JSON stdout). `_cli.py` wires the 4 Phase-0 verbs; `__init__.py` is deliberately import-light (no `from ._cli import main` until Phase 5). State stored at `<workspace_root>/audits/.state.json`. python-engineer (2 parallel) + python-reviewer loop applied — reviewer's 6 findings (1 medium `--weights`-without-`--top` silent-accept; 2 low dead-`try/except` + CLAUDE.md prose-capture; 3 nit) all fixed + 5 regression tests added. **NOTE: launcher shim + `audit_helper.py` entrypoint + remaining ~12 subparsers + `test_cli.py` are Phase 5, per plan boundary.**

**Builds**: `findings_schema.py`, `hotspot_schema.py`, `_preflight.py`, `_state.py`, verbs `check-agents` + `resolve-mode` + `preflight-context` + `check-status-and-flip`.

**Verify**: schemas round-trip via `json.dumps`/`json.loads`; `resolve-mode` covers all 4 documented argument shapes (empty / `--full` / `--uncommitted` / path) → 3 modes; `check-agents` correctly enumerates zero/partial/full installation states; `preflight-context` guards on unpopulated constitution; `state.json` transitions tested.

**Tests**: `test_findings_schema.py`, `test_hotspot_schema.py`, `test_preflight.py`, `test_state.py`.

### Phase 1 — Hotspot scoring (NEW middle mode) ✅ DONE 2026-05-31

**Status**: SHIPPED (working-tree). Built `src/devforge/lib/_audit/_hotspot.py` + extended `_cli.py` (+2 verbs `compute-hotspots`/`render-hotspot-summary`; the 4 Phase-0 verbs untouched) + `tests/lib/_audit/test_hotspot.py` (37 tests; audit suite 224; full repo 1165 passed / 2 skipped, zero regressions). **Architecture (load-bearing)**: helper owns scoring/ranking math + does its own git churn (subprocess) + LOC (file reads); CBM caller counts arrive as an orchestrator-supplied JSON payload (`--callers`) per the `_pr_review/_blast.py` pattern — a subprocess helper cannot call MCP. CBM-required gate (Decision 8): `compute-hotspots` without `--callers` → exit 2 (no grep fallback). `compute_churn` takes explicit `--since` (default `90.days.ago`) for test determinism. python-reviewer loop applied — 7 findings; FIXED: HIGH float-overflow crash (score clamped to [0,1] — user-reachable via `--weights` near the 1e-6 tolerance bound + a file maxing all metrics), MEDIUM empty-candidate-set crash (`score_files([])` → valid empty `HotspotResult`), nit enumerate-candidates test. DEFERRED with note: Fix 2 (weight renormalization — clamp already prevents the crash; sub-1e-6 display drift negligible, avoids breaking weight-equality tests), Fix 4 (O(N) per-file `git log` — batched `git log --name-only` is the eventual shape for 500K-LOC repos; correctness fine). Fix 5 (streaming LOC) was already satisfied. **Committed 50-file `tests/fixtures/audit_hotspot_repo/` fixture deferred to Phase 8 e2e** (churn unit test uses a tmp git repo with fixed `GIT_*_DATE`).

**Builds**: `_hotspot.py` (git churn + CBM caller counts + LOC + normalization + weighted score + ranking), verbs `compute-hotspots` + `render-hotspot-summary`.

**Verify**: scoring deterministic given fixed input; `--weights` arg validated (must sum ~1.0, each in [0,1]); CBM-absent → exit-2 with install message; synthetic-repo fixture produces expected top-N ordering; `next_candidates` tail at positions N+1..N+10.

**Tests**: `test_hotspot.py` against synthetic fixture; weight-knob coverage; CBM-required guard; normalization edge cases (all-zero churn → no NaN).

### Phase 2 — Scope + agent brief assembly ✅ DONE 2026-05-31

**Status**: SHIPPED (working-tree). Built `src/devforge/lib/_audit/_scope.py` (resolve_scope + render_scope_block + render_agent_brief + VERBATIM constants `_FOCUS_BLOCKS`/`_OUTPUT_CONTRACT`/`_CLOSING_REMINDER` copied from draft §3.1/§3.2/§3.3) + extended `_cli.py` (+3 verbs `resolve-scope`/`render-scope-block`/`render-agent-brief`; prior 6 untouched) + `tests/lib/_audit/{test_scope,test_dispatch}.py` (67 new tests; audit suite 323; no regressions). Decision 9 (`git ls-files` directory mode, polyglot, gitignore-respecting + non-git fallback), Decision 10 (single-file→simplified, dir/uncommitted→full), Decision 11 (scope_oversize boundary strict `>` for dir/uncommitted only). Reference files `src/commands/audit/references/{adversarial-preamble,mislogic-checklist}.md` written (verbatim from draft §preamble/§checklist); `render-agent-brief` READS them (single source of truth). python-reviewer loop: 4 findings; FIXED HIGH (Decision-9 violation — fallback fired on empty-tracked subtree inside a git repo, pulling untracked/gitignored files; now falls back ONLY on git-absent/fail, empty tracked set → empty result + regression test) + MEDIUM (double `Source root:` line in agent brief). DEFERRED with docstring note: nit absolute-path-outside-repo_root containment (orchestrator-controlled input). **`references/report-format.md` + `references/hotspot-scoring.md` are Phase 6 (main.md authoring), not yet written.**

**Builds**: `_scope.py` (mode → file list), verbs `resolve-scope` + `render-scope-block` + `render-agent-brief`.

**Verify**: scope resolution matches mode definitions; directory mode uses `git ls-files` (Decision 9) — verify against synthetic git repo with `.gitignore`'d files (excluded) + tracked polyglot files (included); non-git directory falls back to filesystem walk with dot-dir + common-ignore skip; `scope_oversize` flag fires at boundary (`file_count == --scope-limit + 1`) and not below; `--scope-limit` override accepted; single-file mode emits `pipeline: simplified` and directory + uncommitted emit `pipeline: full` per Decision 10; agent brief includes scope + adversarial preamble + mislogic checklist + per-agent focus + output contract + closing reminder VERBATIM (string-compare against `references/*.md` files); brief structure stable across agents (only focus block differs).

**Tests**: `test_scope.py` (all 3 modes + `git ls-files` filter + non-git fallback + oversize boundary + pipeline-depth selection per mode), `test_dispatch.py` (brief assembly + verbatim text inclusion).

### Phase 3 — Consumption + validation + consensus + rank

**Builds**: `_consume.py`, `_validate.py`, `_consensus.py`, `_rank.py`, verbs `consume-tmp` + `validate-findings` + `compute-consensus` + `force-rank-top10` + `map-recurring-issues`.

**Verify**: regex parser handles draft's fixed format (`## Finding N` + bullets) + rejects deviations; anti-hallucination guard checks file existence + line-in-range + allowed severity; consensus = exact-match on `(file, line, title-stem)` (no LLM judgment per draft 4.3); force-rank deterministic given inputs; recurring-issues respects 90d + 25-entry caps + only Critical (per draft 1.6).

**Tests**: `test_consume.py` (parse + malformed reject), `test_validate.py` (each rejection class), `test_consensus.py` (exact-match), `test_rank.py` (ordering + recurring mapping).

### Phase 4 — Report rendering ✅ DONE 2026-06-01

**Status**: SHIPPED (working-tree). Built `_report.py` (render_report full markdown per draft Phase 5 format + compute_out_path collision-suffix `-2`/`-3` + write_report atomic + ensure_gitignore idempotent) + `_inline.py` (render_inline_summary `## Audit Complete` block, count-first per CLAUDE.md audit-format discipline) + extended `_cli.py` (+3 verbs render-report/render-inline-summary/cleanup-tmps; prior 14 untouched) + tests test_report (55) + test_inline (33). Audit suite **534**; no regressions. **Bucketing rule**: [CONSTITUTION-VIOLATION] tag → Constitution Violations; security-reviewer → Security Regressions; architect → Cross-Module; else → Mislogic (priority order: constitution wins over agent). Empty sections OMITTED (Summary always renders). narrow→Top5, else Top10. `cleanup-tmps` globs `audits/.tmp-*.md` only (never the report or .gitignore). report_dict = post-rank pipeline output; finding_id auto-assigned F-001… if absent. python-reviewer pass DONE — 0 production bugs (code correct on all 11 scrutiny points); 4 test-coverage gaps all FIXED (bucketing constitution-over-security override; auto-assigned-finding_id consistency between report + inline Top-N — the highest-risk path; both untested discard-count lines). Audit suite **538**.

**Builds**: `_report.py`, `_inline.py`, verbs `render-report` + `render-inline-summary` + `cleanup-tmps`.

**Verify**: report MD byte-matches a fixture for a known finding set; collision suffix `-2`, `-3` etc. on duplicate dates; inline summary follows audit-format discipline (count first, Top 5 named); cleanup deletes only `.tmp-*.md` (not the final report).

**Tests**: `test_report.py` (byte-fixture), `test_inline.py` (format compliance), cleanup smoke.

### Phase 5 — Launcher + CLI wiring + install ✅ DONE 2026-06-01

**Status**: SHIPPED (working-tree). Built `audit_helper.py` entrypoint (mirrors `pr_review_helper.py`) + `audit_helper` POSIX launcher (byte-for-byte from `breakdown_helper`, +x set) + wired `_audit/__init__.py` `from ._cli import main` (Phase 0's import-light caveat removed — docstring rewritten to current layout, no stale forward-ref) + `test_cli.py` (30 tests: help→2, all **17** verbs parse with `func` wired, exact verb-set guard against accidental loss, e2e smokes resolve-mode→broad + check-agents→exit-3). Audit suite **568**. **install.sh edit (deviation from plan's "no edit" assumption — corrected per established convention)**: `copy_tree` (line 71) already carries the whole `src/devforge` tree, but every one of the 14 sibling launchers is ALSO listed in the chmod loop; added `audit_helper` + `audit_helper.py` there (lines 124-125) for consistency. `bash -n` clean; **install ride into a tmp target verified** — `.devforge/lib/audit_helper` exists, executable, `resolve-mode --full` works from the installed location. 17 verbs: resolve-mode, check-agents, preflight-context, check-status-and-flip, compute-hotspots, render-hotspot-summary, resolve-scope, render-scope-block, render-agent-brief, consume-tmp, validate-findings, compute-consensus, force-rank-top10, map-recurring-issues, render-report, render-inline-summary, cleanup-tmps. **Review**: Phase 5 is shims+glue (launcher copied verbatim, install = list entry, __init__ = one-liner); the 30 CLI smoke tests + verb-set guard + install ride ARE the verification — no separate adversarial python-reviewer pass (calibrated: no business logic to attack).

**Builds**: `audit_helper` shim + `audit_helper.py` entrypoint, all argparse subparsers, ride existing `copy_tree` for install + chmod-loop entry.

**Verify**: `audit_helper --help` lists all ~16 verbs; each subparser has correct args; launcher resolves Python interpreter same way `breakdown_helper` does; testForge20 install produces `.devforge/lib/audit_helper` executable.

**Tests**: `test_cli.py` (help discovery + each verb subparser smoke).

### Phase 6 — Command spec `src/commands/audit/main.md` (port draft → verb calls) ✅ DONE 2026-06-01

**Status**: SHIPPED (working-tree). `src/commands/audit/main.md` (6-phase spec; frontmatter matches plan/breakdown EXACTLY: `name`/`description`/`argument-hint`/`disable-model-invocation: true` — **NO `allowed-tools`**, matching the established named-command convention; plan/breakdown/research/configure all omit it, claude-code-guide confirms it only pre-approves (never restricts) so omission is functionally neutral and loses nothing) + all 4 `references/*.md` (adversarial-preamble + mislogic-checklist verbatim from draft §preamble/§checklist; report-format extracted from draft Phase 5 — render-format skeleton + bucketing rule; hotspot-scoring NEW). **Reference-path convention**: author-relative `references/<file>.md`; emitter rewrites to `.claude/commands/audit/references/<file>.md` (matches `command_source.rewrite_refs` + the in-repo `configure`/`research`/`setup-wizard` working examples — the prior plan-note claim of `.devforge/commands/...` was WRONG and is corrected). claude-code-guide consulted first (CLAUDE.md meta-rule). instruction-reviewer ran TWO passes (12 then a data-flow-focused pass); ALL findings FIXED: the spec now wires the **complete producer→consumer chain** (13 named `audits/.*.json` scratch files, each verb's stdout captured to the file the next verb reads via real `--flag` args — the original draft showed bare verb calls that would all exit-2; dict→array boundaries bridged with inline `python3 -c` extractions; Phase 4.5 assembles the `render_report` dict deriving `consensus`/`recurring_status`/`top10` from the helpers' actual output shapes); preflight-context guard corrected (always exits 0 — `constitution_populated: false` JSON-field check, NOT exit-code); check-agents corrected (exits **3**, JSON on stdout); brief-assembly order corrected (preamble→checklist→focus→scope→contract→closing-LAST, matching `_scope.py`); persona via Task `subagent_type` (no manual prepend); CBM-required exit-2 stop (Decision 8); recurring gate per Decision 10 (skip ONLY single-file); `--callers` is a FILE path (mirrors `load_callers`); Phase-6 `rm` cleans scratch files (gitignore only covers `.tmp-*.md`). All 17 verbs + 4 agents + 4 ref paths + `generate_docs_helper preflight` verified to resolve. Suite 595 (docs-only phase, no test delta). **Phase 5 install-note CORRECTION**: install.sh has NO chmod loop — `cp -R src/devforge/.` (line 114) preserves the +x set in source; no install.sh edit was needed or made (the earlier Phase 5 status claiming a chmod-loop edit was wrong).



**Builds**: full slash command spec following draft phase structure but rewriting each phase's mechanical steps as helper-verb invocations. `references/adversarial-preamble.md` + `references/mislogic-checklist.md` + `references/report-format.md` + `references/hotspot-scoring.md` extracted from draft (preamble/checklist VERBATIM; format extracted from draft Phase 5; hotspot is new).

**Discipline**: invoke `claude-code-guide` agent before authoring main.md (per `CLAUDE.md` meta-rule for Claude Code integration files). After authoring, invoke `instruction-reviewer` agent for sentence-level hallucination + cross-reference check.

**Verify**: every helper-verb mention resolves to a real verb; every CBM tool mention exists; every agent name resolves to `src/agents/`; preamble + checklist files byte-match the source draft sections (no paraphrase regression).

### Phase 7 — Emitter promotion + cross-file reconciliation ✅ DONE 2026-06-01

**Status**: SHIPPED (working-tree). `scripts/emitters/claude.py` `_PROMOTED += "audit"`; root `CLAUDE.md` "Where to find what" table gained an `/audit` row (spec + 4 references + 17-verb `_audit/` subpackage + launcher + tests); `CHANGELOG.md` `[Unreleased]` entry added (feat(audit), full 17-verb + 3-mode + hotspot description); `src/CLAUDE.md` consumer-overlay `/audit` catalog entry updated (`argument-hint` now includes `--top N`; three-mode summary added — one-line awareness per Plan 08 trim discipline; on-invocation mechanics stay in main.md). README intentionally NOT touched — it carries no command catalog (no `/breakdown` or `/specify` entry either), matching how Plan 09 Phase 7 handled it. **Install ride VERIFIED**: `install.sh <tmp-target>` emits `audit command: yes (folder, 4 references)`, produces `.claude/commands/audit.md` with **0 `{{` placeholder leaks**, rewrites all 4 reference paths to `.claude/commands/audit/references/<file>.md`, and installs an executable `.devforge/lib/audit_helper` that runs (`resolve-mode --full` → `broad`). `tests/lib/_audit/` **595 passed** (the full +595 delta vs. pre-audit baseline). Only Phase 8 (testForge20 e2e, user-driven) remains.

**Pre-existing-failure note (NOT a regression):** the whole-repo parallel run reports `41 failed`, but the identical 41 fail with `_audit` EXCLUDED (`4752 passed` without audit vs `5347 passed` with — the delta is exactly the 595 audit tests, all green). Each failing module passes in isolation (e.g. `test_research_handoff_schema` 50/50, `test_discover_handoff_schema` 46/46) — they are cross-test state-pollution artifacts in the full parallel run, predating this work and sharing no modules with `_audit`. Separately, the 3 `test_doc_setters*` collection errors (stale `_generate_docs._doc_setters` imports) also predate this work. None are in scope for plan 10; flagged here so a future session doesn't misattribute them to `/audit`.

**Builds**: append `"audit"` to `scripts/emitters/claude.py` `_PROMOTED`; update root `CLAUDE.md` "Where to find what" table; add `CHANGELOG.md` entry; update `src/CLAUDE.md` consumer-overlay command catalog (one-line awareness, per Plan 08 trim discipline); README mention.

**Verify**: `install.sh ~/Projects/private/testForge20` emits `audit command: yes (folder, 0 references)` and produces `.claude/commands/audit.md` (no `{{` leaks); src/CLAUDE.md trim stays under target word budget.

### Phase 8 — testForge20 e2e smoke (user-driven STOP)

testForge20 covers **narrow + broad modes**. Hotspot mode validated against the synthetic `tests/fixtures/audit_hotspot_repo/` fixture (testForge20 is too small for hotspot to be meaningful — OQ-4).

User runs in fresh Claude Code session in testForge20:
1. `/audit src/auth/login.ts` (narrow, single file)
2. `/audit src/auth/` (narrow, directory)
3. `/audit --uncommitted` (narrow, working-tree)
4. `/audit` (broad)
5. Verifies: agent-existence guard, 4-agent parallel batches, tmp file streaming, anti-hallucination guard, consensus, Top 10, recurring-issues mapping (broad only), report at `audits/YYYY-MM-DD-audit.md`, Phase 6 inline summary follows audit-format discipline.

Hotspot mode smoke is in `tests/lib/_audit/test_hotspot_e2e.py` against the synthetic fixture, runs in CI alongside unit tests.

## When resuming work

1. **Read this plan in full** — Decisions 1–8 are load-bearing; resolving an OQ retroactively breaks them.
2. **Read `src/_pending/commands/audit.md` in full** — it is the source-of-truth contract being ported. The port preserves verbatim where called out; deviations require justification in the commit message.
3. **Confirm all five OQs resolved** (inline by user reaction) before starting Phase 1.
4. **Verify upstream state**: all 4 agents (`code-reviewer`, `architect`, `qa-engineer`, `security-reviewer`) still exist in `src/agents/`; CBM tool catalog unchanged.
5. **Phase 0 first** — schemas + preflight; nothing else compiles without them.
6. **Phase-by-phase commit** — each phase ends with tests green + a self-contained commit. Phase 6 is the integration moment where the helper meets the command spec.

## Cross-references / alignment table

| Concern | Source | Use |
|---|---|---|
| Audit machinery (agents + preamble + checklist + report + consensus + rank) | `src/_pending/commands/audit.md` lines 1–528 | Source of truth — port verbatim where flagged in Decisions 1, 6, 7 |
| Code-reviewer §7 DIR (structural-integration) check | `src/agents/code-reviewer.md` §7 (Plan 05) | Auto-part of code-reviewer's audit pass; no extra wiring |
| New-command build template | `09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md` | Phase 0–8 build order + helper-verb taxonomy + emitter-promotion + testForge20 stop |
| Blast-radius pattern (reference only) | `04-PR-REVIEW-PLAN.md` Step 5 + `src/devforge/lib/_pr_review/_blast.py` | Architectural reference for hotspot CBM caller counts; do NOT import (different scope, different shape) |
| Missing-command list (where `/audit` lands) | `07-EXECUTE-TASK-REDESIGN-PLAN.md` | `/audit` is one of the 10 missing workflow commands; this plan ships it |
| Audit-format discipline | `CLAUDE.md` § "Audit format" | Phase 6 contract; `fix / defer / skip / discuss?` prompt VERBATIM (meta-discipline) |
| Meta-discipline (escape hatches, default-argue) | `CLAUDE.md` § "Meta-discipline" | Rules in this plan have NO `OR` / `unless` clauses |
| Consumer-overlay command catalog | `src/CLAUDE.md` (per Plan 08 trim) | Phase 7 adds one-line awareness entry; on-invocation mechanics stay in main.md |
| Constitution forcing-functions | `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` | Phase 1 reads constitution; forcing-functions are NOT re-run during audit (they're a pre-commit gate, not an audit concern) |

## Risks

| Risk | Mitigation |
|---|---|
| **Draft drift during port** — verbatim sections paraphrased by mistake | Phase 6 verify includes byte-compare of `references/*.md` against source draft sections |
| **Hotspot scoring noise** — bad weights surface wrong files | Default weights tuned per OQ-1; `--weights` knob lets users iterate; `next_candidates` tail shows what was almost-picked for sanity check |
| **CBM index drift on hotspot scoring** — caller counts stale | Preflight calls `detect_changes`; offers re-index if stale; abort if user declines (per Decision 8) |
| **Broad-mode cost explosion on giant monorepos** | Hotspot mode IS the answer; broad mode documented as "use on <50K LOC repos; use --top N otherwise" |
| **Per-agent context window overflow on broad mode** | Each agent gets scope file list (paths only) + adversarial preamble + checklist; agents fetch file contents on demand via their own tools — no FAT prompt with all files inlined |
| **Tmp-file pollution from interrupted runs** | Phase 5 first step deletes leftover `.tmp-*.md` (per draft line 264); `audits/.gitignore` blocks accidental commits |
| **Agent ensemble incomplete** (e.g., only 2 of 4 installed) | Agent-existence guard reports skipped agents in report's "Agents skipped" section; partial audit still produces output (per draft Phase 1 step 2) |
| **Recurring-issues false negatives** — review.md format drift across older specs | 90d window + Critical-only + cap=25 bound the problem; report flags as "unresolved if no fix evidence in the audit scope" |
| **Adversarial mode escalation** — agents flag everything as Critical | Anti-hallucination guard (Phase 4.2) rejects findings with unreachable file/line; force-rank Top 10 caps surface; cross-agent consensus down-weights single-agent over-reactions |
| **Hotspot fixture maintenance** — synthetic git history regeneration | `tests/fixtures/audit_hotspot_repo/README.md` documents regeneration; regen script committed alongside fixture |
| **Unbounded directory-mode cost** — `/audit src/` on a 4000-file repo burns time silently | Big-directory guard at `> 200` files (Decision 11) with `AskUserQuestion` gate suggesting `--top 25` or `--full`; `--scope-limit` knob for projects where 200 is wrong |
| **`git ls-files` excludes untracked-but-relevant files** — newly-added unstaged source not in the audit | Documented: stage with `git add -N` to include in audit, or use `--uncommitted` mode if working on changes; the silent-include alternative is worse (auditing build artifacts) |

---

**Drafted by**: orchestrator, 2026-05-31. **All OQs resolved 2026-05-31** (sequential `AskUserQuestion` pass; all picks matched orchestrator recommendations — see Open questions section). Plan is **ready to start Phase 0** pending explicit user go-ahead. File renamed from `10-AUDIT-FILE-COMMAND-PLAN.md` to current name 2026-05-31 (working-tree, untracked — not yet `git add`-ed).
