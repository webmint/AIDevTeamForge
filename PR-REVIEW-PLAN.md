# PR-REVIEW-PLAN

**Status**: DRAFTED 2026-05-20 — Steps 0 (PRECONDITION MET) + 1 (scaffold) + 2 (CBM ensure + forge-state detect) + 3 (intake) + 4 (4a text-pattern + 4b advanced smells; detect-smells verb wired with full 8-heuristic catalog) + 5 (compute-blast-radius probe-spec extraction) + 6 (bundle-context + import-handoffs) + 7 (check-scope-drift bullet-extraction scaffold) + 8 (dispatch-review FAT brief assembly) + 9 (finalize-output + append-to-replay-corpus) + 10 (slash command spec + emitter `_PROMOTED` wire-in) + 11 (PR #304 replay fixture + end-to-end helper test) shipped through 2026-05-21; ALL 11 HELPER VERBS IMPLEMENTED + slash command spec live + synthetic replay validated; Step 12 PENDING (testForge20 end-to-end manual verify on real foreign-repo PR — STOP POINT per user direction). Multi-session execution plan for `/pr-review <PR#>` slash command + `pr_review_helper` subpackage. Personal-overlay tool: reviewer's local forge install reviews foreign-repo PRs (e.g. Doosan monorepo) where authoring team is unaware of forge. Output stays private to reviewer; reviewer manually re-translates findings into PR comments.

**Queued behind**: RESEARCH-HANDOFF-PLAN Step 10 (testForge20 manual verify). Steps 1-9 shipped; reuse surfaces stable.

---

## Context for next session

**Use case** (re-read before resuming):

- Reviewer has forge installed locally + has run `/init-forge` + `/configure` + `/constitute` + `/generate-docs` on target foreign repo (private overlay; not committed to foreign repo)
- Foreign-repo team does not use forge, has no idea forge artifacts exist
- Reviewer pulls teammate PRs via `gh pr view` + `gh pr diff`, runs `/pr-review <PR#>` locally
- Command emits terse findings (smells + blast + scope-drift + convention deviations) → reviewer reads → reviewer authors PR comments in team-appropriate language

**Why this command vs existing surfaces** (don't re-litigate; settled in design conversation 2026-05-19/20):

- `/review` (built-in) — generic, no project context
- `/ultrareview` — cloud multi-agent, deep but project-context-blind
- `cavecrew-reviewer` — terse + read-only enforced, but blind without brief
- `/pr-review` (this plan) — **forge-overlay-aware**, AI-slop-detecting, blast-radius-computing, scope-drift-checking. Differentiators: code-smell heuristics (Phase 2), CBM blast (Phase 3), scope-drift matrix (Phase 5).

**Canonical replay case**: PR #304 (DoosanICA/db-cse-ui-strata, MIG-2198, merged 2026-04-21). Built parallel internal Ship-To picker instead of refactoring external one per ticket. 80% file duplication, missing validation gate for external users, no Strata env gate, AC-7 format missing on Ordered-By + Deliver-To. Triggered 4+ follow-up tickets over 1 month. Full gap analysis in design session transcript. See `## Replay corpus`.

**Reuse from RESEARCH-HANDOFF + RESEARCH-V3**:

| Source | Artifact | Reuse in /pr-review |
|---|---|---|
| RESEARCH-HANDOFF Step 1 | `handoff.json` schema | Pattern for `pr-review-bundle.json` output |
| RESEARCH-HANDOFF Step 4 | probe-tier classifier | Port → smell-tier classifier (cosmetic / structural / blast / hallucination) |
| RESEARCH-HANDOFF Step 5 | record-probe-script | Pattern for replay corpus storage |
| RESEARCH-HANDOFF Step 6 | `cmd_import_handoff` / `cmd_find_handoffs` | PR-review imports prior /research handoff for ticket area as authoritative context |
| RESEARCH-HANDOFF Step 7 | append-outcome | PR-review outcome appended back to handoff (closes loop) |
| RESEARCH-V3 (shipped) | `_literal_call_shape.py` module (LITERAL_TOKEN_RE + `_detect_arg_duplication` + `_detect_literal_replacement`) | Moved to `_shared/literal_call_shape.py`; both /research + /pr-review consume |
| RESEARCH-V3 (shipped) | argument-duplication lesson | Encode as Phase 2 heuristic (consumes `_detect_arg_duplication` from `_shared`) |
| `_generate_docs/` template | subpackage layout | `_pr_review/` mirrors layout |

---

## Goals

1. Surface AI-slop + code-smell patterns in diff (Phase 2)
2. Compute blast radius via CBM `trace_path` (callers, cross-concern leaks, untested consumers) (Phase 3)
3. Detect scope drift between ticket text + diff (Phase 5)
4. Cite findings against authoritative sources (constitution / overlay / ADRs / plans) (Phase 6 brief)
5. Output terse findings for reviewer's manual translation to PR comments (Phase 7)

## Scope

**In**:

- `/pr-review <PR#> [--ticket-text "..."]` slash command in `src/commands/pr-review/`
- `pr_review_helper` subpackage at `src/devforge/lib/_pr_review/` (mirrors `_generate_docs/` template)
- AI-slop heuristic catalog (extensible per-project)
- Tier-degradation: full / partial / none forge-overlay support
- CBM index prerequisite check + prompt
- Replay corpus seeded with PR #304

**Out**:

- Posting findings to PR comments automatically — reviewer translates manually
- Ticket-source adapters beyond raw paste (no Linear/Jira/GitHub-issue auto-parsing in v1)
- Multi-PR batch review
- Author-seniority heuristics (junior/senior bucketing — agnostic per design decision)
- Two-mode output (`--raw` vs `--plain`) — dropped per private-use scope

---

## Architecture overview

```
/pr-review <PR#> [--ticket-text "..."]
├── Phase -1: CBM index ensure (prompt + index_repository if absent)
├── Phase 0:  Forge-state tier detect (full / partial / none)
├── Phase 1:  Intake (gh pr view + gh pr diff + ticket text paste)
├── Phase 2:  Code-smell + slop heuristics
│             ├── literal-archaeology smell (consumes regexes from `_shared/literal_call_shape.py`; auto git-blame on diff-introduced literals = /pr-review-side novel logic)
│             ├── argument-duplication (consumes `_detect_arg_duplication` from `_shared/literal_call_shape.py`)
│             ├── duplication-ratio, hedge-defensive, atomic-dump,
│             │   empty PR body, hallucinated APIs, etc.
│             └── replay catalog (PR #304 corpus + extensions)
├── Phase 3:  Blast radius (CBM trace_path: callers / callees / data-flow)
├── Phase 4:  Context bundle
│             ├── universal src/constitution.md sections
│             ├── .devforge/<concern>/ overlay docs (if tier=full)
│             ├── .devforge/constitute.json overrides
│             ├── repo-root *-PLAN.md (in-flight intent)
│             ├── CBM manage_adr list
│             └── import existing research handoffs matching ticket area
├── Phase 5:  Scope-drift (ticket bullets × diff coverage matrix)
├── Phase 6:  Reviewer dispatch (cavecrew-reviewer FAT brief, citation discipline)
└── Phase 7:  Output (findings.md) + replay corpus update (pr-review-bundle.json)
```

**Helper API** (verbs follow helper-owns-shape pattern per `feedback_helper_owns_shape_principle`):

```
pr_review_helper.py (entry point) + _pr_review/ subpackage

verbs:
  ensure-cbm-index            (Phase -1)
  detect-forge-state          (Phase 0)
  intake                      (Phase 1)
  detect-smells               (Phase 2)
  compute-blast-radius        (Phase 3)
  bundle-context              (Phase 4)
  import-handoffs             (Phase 4 sub — reuses RESEARCH-HANDOFF cmd_find_handoffs)
  check-scope-drift           (Phase 5)
  dispatch-review             (Phase 6 — assembles FAT brief, invokes cavecrew-reviewer)
  finalize-output             (Phase 7)
  append-to-replay-corpus     (Phase 7 sub)
```

---

## Steps

### Step 0 — Prerequisite refactor: move `_literal_call_shape` to `_shared/`

**Why**: V3's `_literal_call_shape.py` module (regex + parser primitives — `LITERAL_TOKEN_RE`, `_detect_arg_duplication`, `_detect_literal_replacement`, `CALL_SHAPE_RE`, `IDENT_CHAIN_RE`, helpers) is consumed by 4 sites (3 `_research/_cmds_*.py` modules + `research_helper.py` shim) and will be the first /pr-review Phase 2 dependency. Move to a shared layer so /pr-review imports through a non-research namespace.

**Discovery note (2026-05-20)**: original plan draft hypothesized extracting a single `literal_archaeology` function — that was a hallucination (no such function exists in the codebase; research uses a USER-driven CLI `cmd_record_literal_archaeology` that stores user-typed rows). The actual extractable surface is the existing module `_literal_call_shape.py`. Recorded here to keep the plan honest for future-session readers.

**Import topology note**: `research_helper.py:30` inserts `src/devforge/lib/` onto `sys.path` so `_research` + `_shared` are loaded as TOP-LEVEL packages, not as children of `devforge.lib`. Relative `from .._shared...` imports therefore fail with `ImportError: attempted relative import beyond top-level package`. All 4 import sites use absolute `from _shared.literal_call_shape import ...` form to match this loader topology.

**Changes**:

- New: `src/devforge/lib/_shared/__init__.py`
- Moved: `src/devforge/lib/_research/_literal_call_shape.py` → `src/devforge/lib/_shared/literal_call_shape.py` (verbatim — no internal renames)
- Updated 4 import sites — all absolute (`from _shared.literal_call_shape import ...`):
  - `_research/_cmds_dataflow.py:20` (imports `LITERAL_TOKEN_RE`)
  - `_research/_cmds_render_verify.py:21` (imports `_detect_arg_duplication`, `_detect_literal_replacement`)
  - `_research/_cmds_approach.py:17` (imports `CALL_SHAPE_RE`, `_detect_arg_duplication`, `_detect_literal_replacement`, `_normalize_call_shape`)
  - `research_helper.py:55` (imports `_detect_arg_duplication`, `_detect_literal_replacement`, `_split_top_level_args`)
- **LEFT ALONE**: `_research/handoff_schema.py:83-89` local `_LITERAL_REPLACEMENT_RE` + `_CALL_SHAPE_RE` (smaller schema-validation-local subset; REFACTOR-MONOLITHIC-HELPERS Phase D scope)

**Verify**:

- `grep -rn "literal_call_shape" src/ --include="*.py"` shows exactly 4 hits — all import sites: `_research/_cmds_dataflow.py:20`, `_research/_cmds_render_verify.py:21`, `_research/_cmds_approach.py:17`, `research_helper.py:55` — all via `from _shared.literal_call_shape import ...`; zero hits for `_research._literal_call_shape` or `from ._literal_call_shape`
- `ls src/devforge/lib/_shared/literal_call_shape.py` confirms the definition file exists (separate from the content grep above)
- `pytest tests/lib/test_research_helper.py` green (no regression — empirical 2026-05-20: 389 passed, 2 skipped)
- New file at `_shared/literal_call_shape.py` is byte-identical to old `_research/_literal_call_shape.py` (except path)

**Status (2026-05-20)**: PRECONDITION MET — subsumed by `REFACTOR-MONOLITHIC-HELPERS-PLAN` Phase D shipped earlier the same day (commit `6c8545c refactor(research): split research_helper into _research/ + _shared/ subpackages`). Phase D split the 5333-line research_helper.py into 18 `_research/` modules + promoted literal_call_shape to `_shared/`, with all 4 import sites already pointing to `_shared.literal_call_shape`. Test suite verified green (389 passed, 2 skipped) post-Phase-D. No /pr-review-side work required for Step 0; section retained for historical / forensic context.

### Step 1 — Helper subpackage scaffold + CLI entry

**Why**: Start with skeleton so all subsequent steps land into stable structure. Mirrors `_generate_docs/` per proven template.

**Changes**:

- New: `src/devforge/lib/pr_review_helper.py` (thin CLI dispatcher, `argparse` subcommands)
- New: `src/devforge/lib/_pr_review/__init__.py`
- New: `src/devforge/lib/_pr_review/_cli.py` (subcommand registry)
- New: `src/devforge/lib/_pr_review/_state.py` (PRReviewState dataclass — holds PR#, diff, ticket text, bundle, findings)
- New: `src/devforge/lib/_pr_review/_validators.py` (input validation shared across verbs)
- Stub all verbs as `NotImplementedError` with docstring

**Verify**:

- `PYTHONPATH=src python -m devforge.lib.pr_review_helper --help` lists all 11 verbs
- Each verb stub returns exit 1 with `pr_review_helper <verb>: not yet implemented (PR-REVIEW-PLAN Step <N> pending)` stderr
- `./.venv-test/bin/pytest tests/lib/_pr_review/` green — 60 tests passing

**Status (2026-05-20)**: COMPLETE — scaffold shipped via python-engineer; 60 tests green (test_cli + test_state + test_validators); python-reviewer audit yielded 4 findings (F1 medium STATE_DIR_PATTERN dead code, F2 low _VERB_STEP dead dict, F3 low this Verify clause stale, F4 nit _die missing helper-prefix); all 4 applied.

### Step 2 — Phase -1 + Phase 0: CBM ensure + forge-state detect

**Why**: Subsequent phases depend on CBM being indexed + forge-tier known. Detect early; bail or prompt cleanly.

**Changes**:

- `_pr_review/_ensure_cbm.py` — wraps `cbm_sync_helper check` subprocess (NOT direct MCP call — helpers can't invoke MCP tools); emits structured JSON with `status` (`ok|stale|absent|not-a-git-repo`) + `next_action` + `mcp_tool_hint` + cost estimate for LLM consumption
- `_pr_review/_detect_tier.py` — pure-filesystem scan for `.devforge/constitute.json`, `src/constitution.md`, `.devforge/<concern>/` dirs (filters infra subdirs: `lib`, `template`, `pr-reviews`), ADR dir (priority order); returns tier=`full|partial|none` with manifest JSON
- Tests with `subprocess.run` mocked for CBM check + `tmp_path` fixtures for filesystem detection

**Verify**:

- `PYTHONPATH=src python -m devforge.lib.pr_review_helper ensure-cbm-index --target <path>` outputs JSON with `status` / `cbm_state_token` / `next_action` / `mcp_tool_hint` / `cost_estimate_usd` / `target_path`
- `PYTHONPATH=src python -m devforge.lib.pr_review_helper detect-forge-state --target <path>` outputs JSON with `tier` / `manifest` / `target_path`
- Test matrix: `current` / `drift` / `missing` / `not-a-git-repo` CBM states + tier-full / tier-partial / tier-none with infra-dir filter coverage

**Status (2026-05-20)**: COMPLETE — `_ensure_cbm.py` (160L) + `_detect_tier.py` (119L) shipped via python-engineer; 131 tests green (123 prior + 8 new); python-reviewer audit yielded 4 findings (F1 high cwd missing from subprocess, F2 medium infra-dirs leaking into concern list, F3 low subprocess crash misclassified, F4 nit dead vars); all 4 applied; post-fix re-audit clean. Smoke against forge meta-repo: `tier="partial"` (constitution.md only; .devforge/lib filtered correctly).

### Step 3 — Phase 1: Intake helper

**Why**: PR + ticket data loaded once, passed via state to subsequent phases. Centralizes `gh` invocation.

**Changes**:

- `_pr_review/_intake.py` — wraps `gh pr view --json` + `gh pr diff`; accepts mutually-exclusive `--ticket-text` (raw paste) | `--ticket-file` (path to UTF-8 file) via argparse group; populates `PRReviewState.{pr_number, repo, diff, pr_body, linked_issues, ticket_text}`; writes to `state_path` (`.devforge/pr-reviews/<PR#>/state.json`) via atomic temp-file + rename
- Linked-issue extraction: `closingIssuesReferences` from `gh pr view --json` as primary; body-regex fallback (matches both `#<N>` short refs + full GitHub URLs); deduped by full URL string; sorted by issue number
- Error handling: PR not found, gh not authenticated, JSON parse failures, missing ticket file
- Tests with `gh` mocked via `subprocess.run` patching + `tmp_path` for state-file fixtures

**Verify**:

- `PYTHONPATH=src python -m devforge.lib.pr_review_helper intake --pr <N> --repo <owner>/<repo> [--ticket-text "..." | --ticket-file <path>] --target <path>` writes `state.json` + prints output JSON to stdout
- Output JSON keys: `status`, `state_path`, `pr_number`, `repo`, `files_changed`, `additions`, `deletions`, `title`, `ticket_text_length`
- Error cases produce non-zero exit with descriptive stderr (gh exit code propagated)
- Test coverage: happy path / PR not found / no auth / linked-issue dedup-by-URL / mutually-exclusive ticket args / atomic state write

**Status (2026-05-20)**: COMPLETE — `_intake.py` (266L) shipped via python-engineer; 193 tests green (131 prior + 62 new — 55 for intake + 7 cli updates); python-reviewer audit yielded 5 findings (F1 medium dedup-by-number drops cross-repo same-number issues, F2 low stale docstring, F3 low unused `_die` import, F4 nit unused `sys` import, F5 nit "9 stub verbs" claim stale); all 5 applied; re-audit found 1 trailing nit (docstring order swap) applied inline. Linked-issue format: full URLs (`https://github.com/<owner>/<repo>/issues/<N>`).

### Step 4 — Phase 2: Code-smell + slop heuristics

**Why**: Core differentiator. Detects AI-slop + code-smell agnostic of author seniority. Replay-validated against PR #304.

**Split into 4a (text-pattern, ship-first) + 4b (advanced cross-file / git-blame / CBM-driven)** to keep commits reviewable.

#### Step 4a — Text-pattern heuristics + catalog + verb (ship-first)

**Changes**:

- `_pr_review/_smells/__init__.py` — package init
- `_pr_review/_smells/_catalog.py` — heuristic registry + dispatch loop; each entry has `(name, severity, run_fn)`; heuristic interface `run(state: PRReviewState) -> list[dict]`
- `_pr_review/_smells/empty_pr_body.py` — fires when `pr_body` is empty / ≤30 chars after whitespace strip; severity `low`
- `_pr_review/_smells/atomic_dump.py` — fires when diff additions exceed thresholds (defaults: >300 lines OR >4 new files in one commit); severity `medium`
- `_pr_review/_smells/hedge_defensive.py` — regex scan over diff additions for `|| ''`, `|| 0`, `|| []`, `|| {}` patterns + triple-assignment `a = b = c = value`; severity `low`
- `_pr_review/_smells/verbose_commit_msg.py` — commit-msg pattern matching ("Refactor X to improve Y and Z", "Update X to handle Y", > 12 words); severity `nit`
- `cmd_detect_smells` in `_cli.py` — reads `state.json` (from intake); runs all catalog entries; appends findings to `state.smells`; writes back atomically

#### Step 4b — Advanced heuristics (ship-second)

**Changes**:

- `_pr_review/_smells/duplication_ratio.py` — file-vs-file similarity via `difflib` (Python stdlib); compares new-file content reconstructed from diff `+` lines against existing files in target repo (sorted by basename similarity, capped 200 candidates, ≥0.80 ratio threshold, ≥50-line minimum); single highest-ratio match cited
- `_pr_review/_smells/literal_archaeology_adapter.py` — git blame on diff-introduced literals (read-only `git blame -L`, `git log -1`); classifies intent via 6-value pattern set (placeholder / migrated / deliberate / forgotten / inherited-refactor / generated); cap 50 literals per PR; fail-soft when target not a git repo or git binary unavailable
- `_pr_review/_smells/argument_duplication.py` — extracts function-call shapes from diff via local `_FUNCTION_CALL_RE` (word-boundary anchored, excludes numeric-prefix shapes); passes full call-shape string to canonical `_shared/literal_call_shape._detect_arg_duplication`; cap 100 shapes per PR
- `_pr_review/_smells/hallucinated_api.py` — extracts IMPORT statements (Python / TS / JS / Vue) from diff additions; subprocess grep over target repo for module references; stdlib allowlist (~50 Python modules) prevents trivial false positives; cap 30 imports per PR; fail-soft when grep unavailable

**Verify (both waves combined)**:

- `PYTHONPATH=src python -m devforge.lib.pr_review_helper detect-smells --pr <N> --target <path>` mutates `state.smells` + outputs summary JSON (count + by-severity bucket)
- Per-heuristic test: ≥1 positive (fires) + ≥1 negative (doesn't fire) fixture
- PR #304 replay (after Step 11 fixture in place): ≥6 of 9 expected gap-class smells fire (empty body, atomic dump, hedge-defensive triple-assign, verbose commit msg, duplication 80%, hallucinated-or-magic literals, argument duplication if call shape extractable)

**Status (2026-05-20)**: 4a + 4b COMPLETE.
- 4a: 4 text-pattern heuristics + catalog (`register` / `run_all` / `clear_registry`) + `detect-smells` verb shipped; PRReviewState extended with `commit_subjects: List[str]`; intake fetches `commits` from gh; 323 tests green. python-reviewer found 4 findings (F1 medium vacuous idempotency, F2 low `_ADDED_LINE_RE` blank-line bleed, F3 low indexing inconsistency, F4 nit unused `Optional`); all applied; re-audit clean. All `location` values 0-indexed universally.
- 4b: 4 advanced heuristics shipped consuming canonical `_shared/literal_call_shape` (Phase D); PRReviewState extended with `target: str` (runtime-injected, persisted-but-overwritten); 459 tests green (323 prior + 136 new). python-reviewer found 6 findings (F1 high duplicate `_pr_review/_shared/` created by accident — deleted + retargeted to canonical, F2 medium `os.walk` hidden-dir filter bypass, F3 medium `[^+]` blank-line cross in 2 modules, F4 low `forgotten` pattern too narrow + reordering, F5 low dynamic-attribute injection → declared field, F6 nit "Step 4b" stale citation); all applied; re-audit found 1 follow-up medium (target-field comment factually wrong about persistence) applied inline. ALL git ops in heuristics READ-ONLY (`git blame` / `git log` / `git show`).

### Step 5 — Phase 3: Blast radius

**Why**: User's stated #2 differentiator after smell detection. Helper extracts changed symbols + emits probe specs; LLM fills callers/callees/data-flow via CBM `trace_path` at Step 8 dispatch-review time (helpers can't call MCP directly — clean split per `feedback_helper_owns_shape_principle`).

**Changes**:

- `_pr_review/_blast.py` (helper-side):
  - Parse diff → identify changed symbols per language (Python `def`/`class`/`async def`; TS/JS `function`/`class`/`interface`/`type`/typed-or-untyped `const = fn`; Vue implicit component from basename + script-block scan; Go `func`/`type ... struct/interface`; Java method/class; Ruby `def`/`class`; Rust `fn`/`struct`/`enum`/`trait`)
  - Build canonical probe-spec entry per symbol (helper-owns-shape): `{symbol, file, kind, language, diff_line_hint, mcp_hints, callers=[], callees=[], data_flow_targets=[], tests_referencing=[], filled=False}`
  - Dedup by `(symbol, file)`; sort by `(file, symbol)`; cap `_MAX_SYMBOLS_PER_PR = 100`
  - REPLACE `state.blast` entirely on re-run (not append) — fresh probe spec each invocation
- Step 8 dispatch-review (deferred): LLM consumes probe specs, runs CBM `trace_path` per symbol, fills caller/callee/data_flow_targets/tests_referencing, sets `filled=True`. Text-search fallback when CBM returns 0 hits (per `feedback_cbm_discovery_chain_search_graph_then_code`) handled at that layer.

**Verify**:

- `PYTHONPATH=src python -m devforge.lib.pr_review_helper compute-blast-radius --pr <N> --target <path>` populates `state.blast` + outputs summary JSON (`status`, `state_path`, `pr_number`, `symbols_extracted`, `by_language`, `by_kind`, `next_action`, `capped`)
- Per-language regex test coverage (positive + negative) + Vue implicit-component + dedup + cap + REPLACE semantics + shape validation
- PR #304 replay (Step 11): probe specs emitted for `QuoteOrganizationInfo` (extended interface — TS) + `hasEmptyFields` (Vue method) + `OrderInternalShipToColumn` (Vue component); Step 8 LLM later fills caller matrix

**Status (2026-05-20)**: COMPLETE — `_blast.py` (577L) + `test_blast.py` (516L) shipped via python-engineer; 592 tests green (459 prior + 133 new). python-reviewer audit yielded 4 findings (F1 medium typed-const arrow regex missed React/TS idiom, F2 low `continue`→`break` pattern-skip semantics, F3 low dead test guard, F4 nit subparser duplication + stale docstring); all 4 applied; re-audit clean. `_PR_REQUIRED_VERBS` frozenset extracted; Step 4+5 verbs share arg-registration block. NO state-mutating git ops; NO `run_in_background` subprocesses. Probe specs await Step 8 LLM-side CBM population.

### Step 6 — Phase 4: Context bundle + handoff import

**Why**: Tiered bundle of authoritative project context fed to reviewer. Includes reuse of RESEARCH-HANDOFF infrastructure: existing /research handoffs for the ticket area become input.

**Changes**:

- `_pr_review/_bundle.py`:
  - Universal: `src/constitution.md` (always)
  - Tier=full: `.devforge/<concern>/overview.md` + `architecture.md` per touched concern
  - Tier=full or partial: `.devforge/constitute.json` overrides
  - Always: repo-root `*-PLAN.md` (in-flight intent)
  - CBM `manage_adr list` → ADRs
- `_pr_review/_handoff_import.py` — wraps RESEARCH-HANDOFF `cmd_find_handoffs` + `cmd_import_handoff`; matches by ticket text keyword or changed-files heuristic
- Concern detection: changed file paths → `.devforge/<concern>/` mapping (helper: `_pr_review/_concerns.py`)
- Bundle size cap: per-concern doc injection only when >N% of concern's files touched OR specific touched-function documented in concern's setters
- Tests with real `.devforge/` fixture + synthetic handoff

**Verify**:

- `PYTHONPATH=src python -m devforge.lib.pr_review_helper bundle-context --pr <N> --target <path>` populates `state.bundle.{constitution_md, constitute_json, concern_docs, adrs, plan_files}` + outputs summary JSON (sources_gathered counts)
- `PYTHONPATH=src python -m devforge.lib.pr_review_helper import-handoffs --pr <N> --target <path>` appends `state.bundle.research_handoffs` + outputs summary (matched count + total scanned)
- Test coverage: tier-full / tier-partial / tier-none / handoff-match-found / handoff-no-match / token-too-short fallback / caps tripped

**Status (2026-05-20)**: COMPLETE — `_bundle.py` (486L) + `_handoff_import.py` (406L) shipped via python-engineer; 721 tests green (592 prior + 129 new). python-reviewer audit yielded 4 findings (F1 medium docstring vs code mismatch on unreadable-file semantics, F2 low `_excerpt_handoff` duplicate inline impl, F3 low undocumented verdict→mode fallback, F4 nit `_write_state` duplicated across 4 modules); F1/F2/F3 applied; F4 DEFERRED to future consolidation step with TODO markers added to all 4 copies (`_intake.py`, `_blast.py`, `_bundle.py`, `_handoff_import.py`). NO state-mutating git ops; NO `run_in_background` subprocesses. Bundle schema canonical in `_bundle.py` module docstring.

### Step 7 — Phase 5: Scope-drift check

**Why**: Did the diff build what the ticket asked? PR #304 failed this hard. Single highest-signal Phase for AI-slop divergence.

**Changes**:

- `_pr_review/_scope_drift.py` (helper-side, deterministic — same split as Step 5 blast probe-spec):
  - Extract ticket bullets via 5-strategy regex chain in priority order: markdown_bullet → numbered_list → ac_marker → gwt → sentence_fallback (last-resort, only when other 4 yield 0 for the text block)
  - Scan `state.ticket_text` (primary) + `state.pr_body` (secondary); dedupe by lowercased+stripped; cap `_MAX_BULLETS = 50`
  - Emit `state.drift = {bullets, coverage_matrix=[], scope_creep_files=[], filled=False}` — coverage_matrix + scope_creep_files are LLM-filled at Step 8 dispatch-review
- LLM-side coverage assessment + scope-creep file detection deferred to Step 8 reviewer brief (consistent with Step 5 blast-radius CBM-fill split)

**Verify**:

- `PYTHONPATH=src python -m devforge.lib.pr_review_helper check-scope-drift --pr <N> --target <path>` writes `state.drift` + outputs summary JSON (bullets_extracted, by_source, by_extracted_via, capped, next_action)
- Test coverage: each extractor (markdown/numbered/AC/GWT/sentence-fallback) positive + negative; dedup + cap; REPLACE semantics; empty-input no-crash
- PR #304 replay (Step 11): ≥9 AC bullets extracted from ticket_text via ac_marker; LLM-side coverage assessment at Step 8/11 surfaces gaps (`AC-7 Ordered-By/Deliver-To format missing`, `AC-9 Strata gate missing`, `scope-creep: internal picker built`)

**Status (2026-05-20)**: COMPLETE — `_scope_drift.py` (~280L) + `test_scope_drift.py` (~450L) shipped via python-engineer; 807 tests green (721 prior + 86 new). Original plan draft proposed LLM-driven extraction (Haiku); revised design split work LLM-side at Step 8 to keep helper deterministic + zero-cost. python-reviewer audit yielded 4 findings (F1 medium plan-vs-impl drift on LLM extraction — fixed by this Status block + Changes rewrite, F2 low pr_body sentence-fallback lacks integration test, F3 low GWT "AND" prose false-positive — documented as known design choice, F4 nit `_write_state` TODO comment count); all 4 applied. NO LLM calls; NO MCP; NO state-mutating git; NO `run_in_background` subprocesses.

### Step 8 — Phase 6: Reviewer dispatch (FAT brief)

**Why**: All prior phases feed the brief. `cavecrew-reviewer` gets project-context-aware brief biased toward slop + blast + drift detection.

**Changes**:

- `_pr_review/_dispatch.py` (helper-side; NO Task-tool / agent invocation):
  - Assembles FAT brief.md as 10 canonical sections: metadata, ticket text, linked issues, diff (with mid-excerpt strategy when over cap), code-smell findings (Step 4), blast-radius probe specs (Step 5 — TODO renderings for unfilled + resolved for filled), scope-drift bullets (Step 7), context bundle (Step 6), reviewer instructions, notes
  - Brief framing in instructions section: "Author unaware of forge standards. Time-constrained + LLM-assisted possible. Flag slop + drift + blast. Cite source per finding (constitution / overlay / plan / ADR / smells-heuristic / blast-data). Skip nits unless meaning-changing."
  - Finding schema documented in instructions section: `{severity, location, category, evidence, fix_hint, source_heuristic}`
  - LLM (orchestrator) reads brief.md, dispatches `cavecrew-reviewer` via Task tool, parses findings, appends to `state.findings` directly
- Caps: diff 80000, constitution 30000, concern docs 5000, handoffs 2000, plans inline 300, ADRs inline 200, total brief target ≤100000 chars
- Tests verify section assemblers + cap truncation + state-load path + output JSON shape

**Verify**:

- `PYTHONPATH=src python -m devforge.lib.pr_review_helper dispatch-review --pr <N> --target <path>` writes `.devforge/pr-reviews/<N>/brief.md` + outputs summary JSON (brief_path, brief_size_chars, sections_included, counts)
- Brief size <100000 chars; sections_included lists all 10
- Smoke: synthetic state with intake+smells+blast+drift+bundle → brief.md generated
- LLM-side cavecrew dispatch + findings append: Step 11 PR #304 replay + Step 12 testForge20 manual verify

**Status (2026-05-21)**: COMPLETE — `_dispatch.py` (833L) + `test_dispatch.py` (1202L, 100 tests) shipped via python-engineer; 919 tests green (807 prior + 112 new). python-reviewer audit yielded 4 findings (F1 HIGH `float(None)` crash when LLM fills `confidence: null` — fixed via `entry.get("confidence") or 0.0`, F2 medium `_ADR_CAP`/`_PLAN_CAP` constants ineffective due to inline slices — renamed to `_ADR_INLINE_CAP=200`/`_PLAN_INLINE_CAP=300` + dead `_truncate` calls removed, F3 low `_write_state` dead code copy in `_dispatch.py` — removed + TODO count reverted to 5 across remaining modules, F4 low `sections_included` missed `"notes"` — added); all 4 applied; re-audit needed. NO LLM/MCP/git-mutating/run-in-background calls.

### Step 9 — Phase 7: Output + replay corpus

**Why**: Findings rendered in terse markdown for reviewer reading. Bundle archived for replay + future regression-test.

**Changes**:

- `_pr_review/_output.py`:
  - Markdown rendering: sorted by severity, file:line, fix-suggestion
  - Summary header: PR#, ticket, slop-score, blast-risk-score, drift-summary
- `_pr_review/_replay.py`:
  - Writes full `pr-review-bundle.json` to `.devforge/pr-reviews/<PR#>/` (cached locally, gitignored)
  - Appends to replay-corpus index for regression-test (Step 11)
- Tests: rendering snapshot + replay-corpus append idempotency

**Verify**:

- `PYTHONPATH=src python -m devforge.lib.pr_review_helper finalize-output --pr <N> --target <path>` renders `<target>/.devforge/pr-reviews/<N>/findings.md` (severity-sorted + summary header with slop/blast/drift scores) + outputs summary JSON
- `PYTHONPATH=src python -m devforge.lib.pr_review_helper append-to-replay-corpus --pr <N> --target <path>` writes `<target>/.devforge/pr-reviews/<N>/pr-review-bundle.json` + upserts `<target>/.devforge/pr-reviews/_corpus_index.json`
- Idempotent: re-running append-to-replay-corpus updates last_reviewed_at + review_count++, preserves first_reviewed_at
- Test coverage: render + summary + sort + score computation + upsert (created/updated) + fail-soft on missing/malformed index

**Status (2026-05-21)**: COMPLETE — `_output.py` (312L) + `_replay.py` (281L) shipped via python-engineer; 1068 tests green (919 prior + 149 new — 145 step-9 + 4 from F3 title-persistence cross-file fix). python-reviewer audit yielded 4 findings (F1 medium `_sort_findings` docstring lied about sort order — fixed, F2 low `utcnow` deprecation — migrated 2 files to `datetime.now(timezone.utc)`, F3 low PR title never persisted to state — added `pr_title` field to PRReviewState + intake populates + output reads, F4 nit metrics double-computation — DEFERRED); F1/F2/F3 applied. ZERO stubs remain in `_cli.py`; all 11 verbs implemented. findings.md schema + corpus_index.json schema (`schema_version: "1"`) canonical. NO LLM/MCP/git-mutating/run-in-background invocations.

### Step 10 — Slash command spec + emitter wire-in

**Why**: Ship as user-facing slash command. Per `feedback_emitter_promoted_cross_check` — adding `src/commands/<name>/` requires `scripts/emitters/claude.py _PROMOTED` update.

**Changes**:

- New: `src/commands/pr-review/main.md` (331L slash command spec) — 13 phases: -1 / 0 / 1 / 2 / 3 / 3.5 (LLM blast-fill via CBM trace_path) / 4 / 4.5 / 5 / 6 / 6.5 (LLM cavecrew dispatch + findings append) / 7 / 7.5; frontmatter uses `disable-model-invocation: true` + `arguments: [pr_number]` per claude-code-guide consultation; allowed-tools restricted to `Bash(gh pr *|gh issue *|git rev-parse *|git blame *|git log *|grep *|.venv-test/bin/python *|python *|python3 *)` + `Read(.)`; NO `model:` override, NO `context: fork`
- Modified: `scripts/emitters/claude.py` — added `pr-review` to `_PROMOTED` tuple (per `feedback_emitter_promoted_cross_check`)
- Spec authored via `instruction-author` agent + claude-code-guide consultation (per `feedback_claude_code_authoring_best_practices` + `feedback_dual_agent_verify_command_statements`)
- Spec reviewed via `instruction-reviewer` agent

**Verify**:

- `bash scripts/generate.sh` produces `.claude/commands/pr-review.md` in target install (Step 12 manual gate)
- Install on `testForge20`: `/pr-review` slash command appears + runs through to helper invocation (Step 12)
- `instruction-reviewer` audit clean (post-fix re-audit deferred — orchestrator applied all 7 findings inline)
- `claude-code-guide` confirmed frontmatter + structure compliant with Claude Code conventions per docs.claude.com/docs/en/slash-commands

**Status (2026-05-21)**: COMPLETE — `src/commands/pr-review/main.md` (331L) shipped via instruction-author (claude-code-guide consulted for slash-command frontmatter + structure conventions); 1068 pytest still green (no helper code touched). instruction-reviewer audit yielded 7 findings (F1 high Phase 7 stdout `findings_count`→`findings_total`, F2 high Phase 7.5 stdout key list diverged from `_replay.py` schema, F3 medium `coverage_matrix` status values `covered/unclear` → canonical `satisfied/unknown`, F4 medium corpus_index.json keyed-by-PR-number claim wrong — it's `entries` array, F5 medium `state.smells` vs `state.findings` confusion in Phase 6.5 prose, F6 low Phase -1 dict key enumeration incomplete, F7 low blast-risk-score formula wrong); all 7 applied via instruction-author. Emitter `_PROMOTED` tuple in `scripts/emitters/claude.py` updated.

### Step 11 — PR #304 replay validation gate

**Why**: Replay-the-failure principle (per `project_research_patches_1_5_empirical_failed`). Plan claims surface a defined gap set; replay confirms or invalidates.

**Setup**:

- Fixture: `tests/fixtures/pr_review_replay_corpus/304/` contains
  - `pr_view.json` (mock `gh pr view` output)
  - `pr_diff.patch` (full diff)
  - `ticket.txt` (ticket text from design conversation transcript)
  - `expected_findings.yaml` (9-gap list from design analysis)

**Replay**:

- Invoke full helper pipeline end-to-end on synthetic fixture (LLM-side Phase 3.5 CBM + Phase 6.5 cavecrew NOT exercised — those are Step 12 manual verify)
- Compare actual helper outputs vs `expected_outcomes.json` declarative gate

**Verify**:

- All 4 expected smells fire (`empty_pr_body`, `atomic_dump`, `hedge_defensive`, `verbose_commit_msg`)
- ≥3 blast probe specs extracted (vue + typescript symbols; `filled=False` since LLM phase skipped)
- ≥9 scope-drift bullets extracted (≥1 via `ac_marker`)
- brief.md generated with PR # + AC text + smell names
- findings.md generated with empty-findings marker (state.findings unfilled since LLM skipped)
- corpus_index.json upserted with pr=304 entry

**Status (2026-05-21)**: COMPLETE — fixture `tests/fixtures/pr_review_replay_corpus/304/` (4 files: pr_view.json / pr_diff.patch / ticket.txt / expected_outcomes.json) + end-to-end test `tests/lib/_pr_review/test_replay_pr304.py` (601L, 13 tests) shipped via python-engineer; 1081 tests green (1068 prior + 13 new). All 11 helper verbs exercised against synthetic fixture; all expected gap classes detected. Engineer adjusted fixture (5 new files / 336 added lines) to clear `atomic_dump` heuristic threshold (`new_files > 4` strict). NO LLM/MCP/git-mutating/run-in-background. LLM-side phases (3.5 CBM trace_path; 6.5 cavecrew dispatch) deferred to Step 12 manual verify on real foreign-repo PR.

### Step 12 — testForge20 end-to-end manual verification

**Why**: Replay corpus = synthetic. Real-PR run on real foreign repo proves install + tier-degradation + CBM integration.

**Setup**:

- Choose 2-3 real PRs from foreign repo (Doosan or other) reviewer has access to
- Forge installed on testForge20; `.devforge/` overlay populated on target repo via `/init-forge` chain
- CBM index populated on target repo

**Verify**:

- `/pr-review <PR#>` runs to completion across full pipeline
- Findings markdown produced
- No crashes on tier=partial or tier=none paths (sanity)
- Reviewer reads findings, confirms signal-to-noise ratio acceptable (subjective; documented assessment)

**Stop condition**: Step 12 green = plan complete + close. Iteration on heuristic catalog moves to follow-up tickets (per CLAUDE.md "Currently active" lifecycle).

---

## Risks

1. **CBM index staleness on monorepo** — Doosan + similar repos ship daily; overlay drifts. Mitigation: Phase -1 surfaces staleness; reviewer prompted to re-index before run.
2. **Bundle-size explosion on broad PRs** — diff touches 8 concerns → 8 architecture docs → giant brief. Mitigation: per-concern injection threshold (>N% of concern's files touched OR explicit setter overlap).
3. **LLM-extracted ticket bullets (Phase 5) low quality** — vague tickets → garbage matrix. Mitigation: confidence flag per bullet; reviewer can disregard low-confidence drift findings.
4. **Smell-heuristic false positives** — valid code sometimes triple-assigns, etc. Mitigation: heuristic-catalog yaml with per-project override (`.devforge/local/smell-overrides.yaml`); start conservative.
5. **Cost surprise on first run against new repo** — initial `/generate-docs` overlay ~$50-200 Haiku. Mitigation: Phase 0 surfaces cost estimate; reviewer can run tier=partial (constitution + CBM only).
6. **NDA / confidentiality on foreign-repo code → LLM** — enterprise repos may restrict. Mitigation: spec `main.md` includes explicit confidentiality reminder; user confirms before running first time.
7. **CBM cross-package scope** — monorepo with per-package indices understates cross-package blast. Mitigation: Phase -1 checks index scope; warns if appears partial.
8. **Reviewer self-trap** — trusting tool output without reading diff. Mitigation: output explicitly framed as "review input, not review output" in finalize-output header.
9. **Step 0 refactor breaks research_helper consumers** — moving `_literal_call_shape.py` to `_shared/` changes import path. **Risk SURFACED 2026-05-20**: initial grep missed all 4 internal consumers (`_cmds_dataflow.py`, `_cmds_render_verify.py`, `_cmds_approach.py`, `research_helper.py`), causing test `TestRecommendedApproachSingleLayerGate::test_set_recommended_approach_single_layer_requires_justification` to fail in interim states. Recovery required two passes: initial 3-site update + `research_helper.py:55` site found by python-reviewer audit. **Resolved** by updating all 4 import sites to absolute form (`from _shared.literal_call_shape import ...`) matching research_helper's `sys.path` topology. Lesson recorded: cross-grep MUST include relative-import patterns (`from ._<name> import`), absolute-import patterns (`from _<pkg>._<name> import`), and dotted-path references — not just bare symbol names. Don't filter `research_helper.py` out of consumer-discovery grep just because it has known inline duplicates elsewhere.
10. **RESEARCH-HANDOFF Step 10 surfaces breaking issues** — handoff schema or `cmd_import_handoff` may shift before /pr-review consumes. Mitigation: defer Step 6 implementation until Step 10 verify green; intermediate steps unaffected.

---

## Replay corpus (seed)

### PR #304 — DoosanICA/db-cse-ui-strata, MIG-2198

**Merged**: 2026-04-21. **Author**: npineda. **Branch**: ?→dev. **Files**: +789 lines, 5 new files, 4 modified.

**Ticket summary**: "Update Draft Order screen Ship-To selection for Strata orgs. Existing UI (external) updated with: red-asterisk required marker, V2 search API (descendant ship-to), auto-select-if-single, blank-if-multi, validation gate on Next-Preview, modal updated with SAP Customer # column + SHIPPING address + pagination, selected display in compact format `erpCustomer / name1 name2 / address / city, state postalCode` applied to Ship-To + Ordered-By + Deliver-To with correct address types. Strata env only."

**Actual delivery**:

- Built NEW parallel internal Ship-To picker (`OrderInternalShipToColumn.vue`) instead of refactoring external picker (`OrderAddressInfoExternal.vue`)
- 80% file duplication: new component near-identical to existing external picker
- Asterisk added to both panels (only correct delivery)
- V2 search composable shipped (`useShipToOrgSearchV2.ts`)
- Modal V2 shipped (`ShipToOrganizationModalV2.vue`) but only wired to internal picker
- Validation gate (`hasEmptyFields`) extended for `isInternalUser` branch only — external users still pass with empty ship-to
- AC-7 compact format applied to internal Ship-To column only; Ordered-By + Deliver-To still flat-list via legacy `OrderAddressView`
- No explicit Strata env gate
- PR body empty
- Triggered follow-up tickets: MIG-2612, MIG-2613, MIG-2615, MIG-2616 (revert), current spec/009 branch

**Expected /pr-review findings** (9-gap list, must surface ≥8):

1. **smell — empty-pr-body** — PR body empty; AC traceability impossible
2. **smell — duplication-ratio (80%)** — `OrderInternalShipToColumn` ≈ existing `OrderAddressInfoExternal`; extract or justify
3. **smell — hedge-defensive** — `useShipToOrgSearchV2.ts` mapper triple-assigns `shippingAddress = billingAddress = address`
4. **smell — atomic-dump** — 789 lines / 5 new files / single commit
5. **smell — verbose-commit-msg** — "Refactor X to improve Y and Z" pattern
6. **blast — high-fan-out** — `QuoteOrganizationInfo` field additions ripple across pkg-cse-core (20+ consumers); no tests guarding callers
7. **blast — cross-concern caller miss** — `hasEmptyFields` change affects both Next + Bulk buttons; review only verified one
8. **drift — AC-7 missing on external** — ticket requires compact format on Ship-To + Ordered-By + Deliver-To both panels; only internal Ship-To delivered
9. **drift — AC-9 env gate missing** — ticket specifies Strata-only; no detection gate in code

### Future replay entries

Added by reviewer as new PRs trigger heuristic-catalog extensions. Each entry: `pr_view.json` + `diff.patch` + `ticket.txt` + `expected_findings.yaml`. Stored under `tests/fixtures/pr_review_replay_corpus/<id>/`.

---

## When resuming work

1. **Re-read this plan in full first.** Multi-session state isn't in the conversation.
2. Check git log for plan-step commits since last session: `git log --oneline --grep="pr-review"`.
3. Verify RESEARCH-HANDOFF status — if Step 10 still pending, defer Step 6 implementation (Phase 4 handoff import depends on Step 6 of that plan).
4. Run `pytest tests/lib/_pr_review/ tests/lib/_shared/` to confirm prior steps still green.
5. Find next undone step (`grep -n "Verify" PR-REVIEW-PLAN.md` + cross-ref to git log).
6. Execute step per CLAUDE.md "Working process" — draft change list, argue, align, implement, verify, commit.
7. Per-step commit format: `feat(pr-review): step N — <short>` for code; `docs(pr-review-plan): <revision note>` for plan edits.

**Hard stop**: Step 12 green = plan complete. Subsequent heuristic-catalog extensions ship as follow-up tickets, not plan amendments.
