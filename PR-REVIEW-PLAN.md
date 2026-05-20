# PR-REVIEW-PLAN

**Status**: DRAFTED 2026-05-20. Multi-session execution plan for `/pr-review <PR#>` slash command + `pr_review_helper` subpackage. Personal-overlay tool: reviewer's local forge install reviews foreign-repo PRs (e.g. Doosan monorepo) where authoring team is unaware of forge. Output stays private to reviewer; reviewer manually re-translates findings into PR comments.

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

- `python -m src.devforge.lib.pr_review_helper --help` lists all 11 verbs
- Each verb stub returns exit 1 with "not implemented" message
- `pytest tests/lib/_pr_review/` discovers (no tests yet but suite resolves)

### Step 2 — Phase -1 + Phase 0: CBM ensure + forge-state detect

**Why**: Subsequent phases depend on CBM being indexed + forge-tier known. Detect early; bail or prompt cleanly.

**Changes**:

- `_pr_review/_ensure_cbm.py` — calls `index_status` MCP; if absent, surfaces install instructions + cost estimate; if stale, calls `detect_changes`
- `_pr_review/_detect_tier.py` — scans for `.devforge/constitute.json`, `.devforge/<concern>/` folders, `src/constitution.md`, ADR folder; returns tier=`full|partial|none` with manifest
- Tests with mock CBM responses + temp filesystem fixtures

**Verify**:

- `pr_review_helper ensure-cbm-index --target <path>` prints status (ok / stale / absent + cost estimate)
- `pr_review_helper detect-forge-state --target <path>` prints tier + manifest JSON
- Test matrix covers: indexed+full / indexed+partial / indexed+none / not-indexed / stale-index

### Step 3 — Phase 1: Intake helper

**Why**: PR + ticket data loaded once, passed via state to subsequent phases. Centralizes `gh` invocation.

**Changes**:

- `_pr_review/_intake.py` — wraps `gh pr view --json` + `gh pr diff`; accepts `--ticket-text` flag (raw paste) OR `--ticket-file` (path to text file); populates `PRReviewState.diff`, `.pr_body`, `.linked_issues`, `.ticket_text`
- Error handling: PR not found, gh not authenticated, network failure
- Tests with `gh` mocked via `subprocess.run` patching

**Verify**:

- `pr_review_helper intake --pr 304 --repo DoosanICA/db-cse-ui-strata --ticket-text "..."` outputs intake.json (structured)
- Error cases produce non-zero exit with clear message
- Test coverage: happy path / PR not found / no ticket text

### Step 4 — Phase 2: Code-smell + slop heuristics

**Why**: Core differentiator. Detects AI-slop + code-smell agnostic of author seniority. Replay-validated against PR #304.

**Changes**:

- `_pr_review/_smells/__init__.py` + per-heuristic modules:
  - `empty_pr_body.py`
  - `atomic_dump.py` (single-commit, large-file additions)
  - `duplication_ratio.py` (compares new file content vs existing files via CBM `search_code` or python `difflib`)
  - `hedge_defensive.py` (regex/AST scan for `|| ''` chains, triple-assignment)
  - `verbose_commit_msg.py` (commit-msg pattern matching)
  - `literal_archaeology_adapter.py` (calls `_shared/literal_archaeology` on diff-introduced literals)
  - `argument_duplication.py` (CBM trace_path on new args vs existing call-chain args)
  - `hallucinated_api.py` (referenced symbols not in CBM graph)
- `_pr_review/_smells/_catalog.py` — registry + tier classification (port from RESEARCH-HANDOFF probe-tier pattern)
- Test per heuristic: hand-authored fixtures + PR #304 diff replay

**Verify**:

- `pr_review_helper detect-smells --intake intake.json` outputs `smells.json` (list of detections, each with: heuristic, severity, location, evidence)
- PR #304 replay surfaces ≥6 of: empty body / duplication 80% / hedge-defensive triple-assign / atomic dump / verbose commit msg / hallucinated-or-magic literals
- Per-heuristic test coverage ≥1 positive + ≥1 negative case

### Step 5 — Phase 3: Blast radius

**Why**: User's stated #2 differentiator after smell detection. CBM-driven matrix of changed-symbol fan-out.

**Changes**:

- `_pr_review/_blast.py`:
  - Parse diff → identify changed symbols (functions, classes, exported types)
  - For each: CBM `trace_path(symbol, mode=calls, direction=in)` → callers
  - CBM `trace_path(symbol, mode=calls, direction=out)` → callees
  - CBM `trace_path(symbol, mode=data_flow)` → reach
  - Cross-concern detection: callers in concerns not touched by diff = surprise blast
  - Test-coverage check: CBM `search_graph` for test files referencing each caller
  - Produces blast matrix per symbol
- Text-search fallback when CBM returns 0 hits (per `feedback_cbm_discovery_chain_search_graph_then_code`)
- Tests with mock CBM responses + small real-world fixture (forge repo itself)

**Verify**:

- `pr_review_helper compute-blast-radius --intake intake.json` outputs `blast.json`
- PR #304 replay surfaces high-risk symbols: `QuoteOrganizationInfo` (20+ callers across packages), `hasEmptyFields` (2 callers including Bulk button)
- Test coverage: single-caller / multi-caller / cross-concern / data-flow chain / CBM-miss-with-text-fallback

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

- `pr_review_helper bundle-context --intake intake.json --blast blast.json` outputs `context.json`
- PR #304 replay: bundle includes order-flow concern docs (if .devforge/order-flow/ existed) + universal SOLID/DRY constitution sections + any matching research handoff
- Test coverage: tier-full / tier-partial / tier-none / handoff-match-found / handoff-no-match

### Step 7 — Phase 5: Scope-drift check

**Why**: Did the diff build what the ticket asked? PR #304 failed this hard. Single highest-signal Phase for AI-slop divergence.

**Changes**:

- `_pr_review/_scope_drift.py`:
  - Extract ticket bullets via LLM (Haiku — cheap; cost surfaced)
  - For each bullet: locate diff evidence (file/line matching the requirement)
  - Coverage matrix: bullet → satisfied | partial | missing | scope-creep-elsewhere
  - Flag: bullets-missing list + diff-files-outside-bullets list
- Confidence flag per bullet (LLM-extracted requirements vary in quality)
- Tests with PR #304 ticket text + diff

**Verify**:

- `pr_review_helper check-scope-drift --intake intake.json` outputs `drift.json`
- PR #304 replay: surfaces "AC-7 format on Ordered-By + Deliver-To missing", "AC-9 Strata env gate missing", "scope-creep: built internal picker not requested by ticket"
- Test coverage: full-coverage / partial / scope-creep / no-ticket-text-bail

### Step 8 — Phase 6: Reviewer dispatch (FAT brief)

**Why**: All prior phases feed the brief. `cavecrew-reviewer` gets project-context-aware brief biased toward slop + blast + drift detection.

**Changes**:

- `_pr_review/_dispatch.py`:
  - Assembles FAT brief from intake + smells + blast + bundle + drift
  - Brief framing: "Author is unaware of forge standards. Treat as time-constrained author + LLM-assisted possible. Flag slop + drift + blast risk. Cite source per finding (constitution / overlay / plan / ADR). Skip nits."
  - Invokes `cavecrew-reviewer` agent via Task tool
  - Captures findings per `feedback_audit_format` (severity / location / issue / why / fix)
- Citation discipline: each finding must name its source layer
- Tests verify brief assembly (not LLM output) — input → expected brief string

**Verify**:

- `pr_review_helper dispatch-review --intake intake.json --smells smells.json --blast blast.json --context context.json --drift drift.json` outputs `findings.json`
- Brief includes all input artifacts (verify via string assertions)
- Manual smoke: dispatch on PR #304 yields ≥10 findings spanning smell/blast/drift categories

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

- `pr_review_helper finalize-output --findings findings.json` writes `pr-review-<PR#>.md` + `pr-review-bundle.json`
- Output markdown human-readable + scannable
- Replay corpus entry created in `tests/fixtures/pr_review_replay_corpus/<PR#>/`

### Step 10 — Slash command spec + emitter wire-in

**Why**: Ship as user-facing slash command. Per `feedback_emitter_promoted_cross_check` — adding `src/commands/<name>/` requires `scripts/emitters/claude.py _PROMOTED` update.

**Changes**:

- New: `src/commands/pr-review/main.md` (slash command spec)
- New: `src/commands/pr-review/references/pr_review_helper-api.md` (verb API reference)
- Modified: `scripts/emitters/claude.py` — add `pr-review` to `_PROMOTED` list
- Spec authored via `instruction-author` agent (per `feedback_claude_code_authoring_best_practices`)
- Spec reviewed via `instruction-reviewer` + `claude-code-guide` (per `feedback_dual_agent_verify_command_statements`)

**Verify**:

- `bash scripts/generate.sh` produces `.claude/commands/pr-review.md` in target install
- Install on `testForge20`: `/pr-review` slash command appears + runs through to helper invocation
- `instruction-reviewer` finds no logic gaps in spec
- `claude-code-guide` confirms frontmatter + structure compliant with Claude Code conventions

### Step 11 — PR #304 replay validation gate

**Why**: Replay-the-failure principle (per `project_research_patches_1_5_empirical_failed`). Plan claims surface a defined gap set; replay confirms or invalidates.

**Setup**:

- Fixture: `tests/fixtures/pr_review_replay_corpus/304/` contains
  - `pr_view.json` (mock `gh pr view` output)
  - `pr_diff.patch` (full diff)
  - `ticket.txt` (ticket text from design conversation transcript)
  - `expected_findings.yaml` (9-gap list from design analysis)

**Replay**:

- Invoke full pipeline end-to-end on fixture (CBM mocked OR run against a real CBM index of cloned db-cse-ui-strata at PR #304 timestamp)
- Compare actual findings vs `expected_findings.yaml`

**Verify**:

- ≥8 of 9 expected gaps surface (per design matrix: empty PR body, duplication, hedge-defensive, scope drift, missing validation, missing env gate, AC-7 missing, anchoring, atomic dump)
- No false-positive findings with severity ≥ high
- Replay reproducible (deterministic across runs given same fixtures + CBM index)

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
