# 20 — REVIEW COMMAND REDESIGN PLAN

**Status:** **Phases 0–6 SHIPPED in the working tree (uncommitted) 2026-06-15** on `develop-2.0-init`; only **Phase 7 (testForge20 e2e) remains, user-driven HARD GATE**. As-built: Phase 0 extracted the roster-agnostic refutation engine (`findings_schema`, `_consume`, `_validate`, `_consensus`, `_verify`) from `_audit/` into `src/devforge/lib/_shared/` (flat) + parameterized `route_refutation(priority=None)` so `/audit` is behaviorally identical (its `tests/lib/_audit/` suite is the green regression net); Phases 1–5 built the `_review/` helper subpackage (`_preflight`, `_state`, `_scope`, `_brief`, the shared refutation verbs via `_cli`, `_report`) + `review_helper{,.py}` + `src/commands/review/main.md` + 4 `references/`; Phase 6 promoted `review` in the emitter `_PROMOTED`, deleted the stale `src/_pending/commands/review.md`, and reconciled docs. `267 tests/lib/_review/` tests pass; install-ride clean (review command: yes, folder, 4 references; 0 `{{` leaks; executable helper). The per-phase sections below are the original design; the Verify blocks were all met. OQ-1 resolved to Path A (no audit-freeze); OQ-2 to flat `_shared/`; OQ-3 (structured `review-handoff.json`) deferred to when `/verify` is built.

Redesigns the `/review` command from the stale pre-pivot draft (`src/_pending/commands/review.md`) into a live, emitted, pipeline-wired feature-level review command at `src/commands/review/main.md` + `references/` + a `src/devforge/lib/_review/` helper subpackage. It REUSES the precision refutation engine that already ships inside `/audit` (`src/devforge/lib/_audit/_verify.py` and siblings — see plan 19, SHIPPED in the working tree) by extracting the roster-agnostic pieces into `src/devforge/lib/_shared/` first (Phase 0).

## Scope & assumptions

These are decided, not open (except the OQs in `## Open questions`):

1. **`/review` is the FEATURE-LEVEL emergent / cross-task review** — the pipeline step run after `/implement` drains a feature's tasks and before `/verify`. It is NOT standalone in the workflow sense (that role belongs to `/audit`). In this plan "standalone" refers ONLY to `/review`'s CODE not depending on `/audit`'s helper subpackage (achieved by the Phase 0 `_shared/` extraction), never to its workflow position. `/review` stays pipeline-wired after `/implement` — the workflow chain in `src/CLAUDE.md` already names it in that slot (verified: `src/CLAUDE.md` Workflow chain line `/implement → /review → /verify`).
2. **The target is a NEW live command tree** at `src/commands/review/` (folder layout: `main.md` + `references/*.md`), a NEW helper subpackage `src/devforge/lib/_review/`, and a NEW launcher `src/devforge/lib/review_helper{,.py}`. The stale `src/_pending/commands/review.md` draft is DELETED (Phase 6), not rewritten — leaving it on disk is a future-hallucination seed (a fresh session could mistake the draft for the SSOT, as plan 19 noted for the `/audit` draft).
3. **Every file path and identifier in this plan is verified against the live tree this session.** The `main.md` / helper line numbers cited are pre-edit; after a phase edits a file, re-read it from scratch rather than navigating by these numbers.
4. **Build NOW; do NOT gate on `/audit`'s testForge20 e2e** (the user-driven gate from plans 10/11/12/19). The Phase 0 extraction's regression net is `/audit`'s existing `tests/lib/_audit/` unit suite — they must stay green after the extraction, which is the safety property that lets this plan proceed without waiting on `/audit`'s manual e2e. (OQ-1 records the audit-freeze fallback.)

## Command mission (what /review is for)

`/review` exists to catch the ONE review job nothing else in the pipeline owns: **emergent cross-task issues** that the per-task review STRUCTURALLY cannot see because it reviews each task's diff in isolation.

The reasoning, grounded in the live pipeline:

- `/implement` PHASE 6 already runs a **per-task panel of four read-only reviewers** (`code-reviewer` + `qa-reviewer` + `security-reviewer` + `performance-analyst`, merged to one verdict) with an **all-findings-fixed gate** — `approve` is reachable only from a fully-clean panel (verified: `src/commands/implement/main.md:176–213`, the "Autonomous review PANEL loop", and the PHASE-7 "all findings fixed before `approve`" rule). So per-task code quality, security depth, test adequacy, and performance are already forced clean on each task's own diff.
- `/verify` does the cross-task **integration** check — type/import/contract/state-flow consistency across the assembled feature (verified: `src/CLAUDE.md` `/verify` entry — "Performs cross-task integration check (not full code review — that was done per-task)").
- The ONLY unowned job is **emergent cross-task issues** the per-task panel cannot see by construction (it never sees two tasks' diffs together): cross-task security holes (task A's auth boundary + task B's new endpoint), assembled-data-flow performance (a query pattern fine per-task that N-pluses once tasks compose), cross-task duplication / diverged copies, and cross-task architectural drift.

### The review-vs-audit invariant

`/review` and `/audit` both run a finder-ensemble + refutation, but they are different commands with non-overlapping jobs. This table is the invariant the plan must preserve:

| Axis | `/review` | `/audit` |
|---|---|---|
| **Trigger** | in-pipeline, after `/implement` drains a feature | standalone, manual / periodic |
| **Scope** | ONE feature's assembled diff (all its tasks together) | whole project, or any part (file / dir / hotspot) |
| **Output** | `specs/[feature]/review.md` — feeds `/verify` | `audits/YYYY-MM-DD-audit.md` — terminal report |
| **Cadence** | once per feature | periodic (after several specs ship) |

Both invoke a finder ensemble in adversarial mode and gate findings through a refutation pass; the SHARED machinery is exactly what Phase 0 extracts into `_shared/`. What differs — roster, scope resolution, report destination, pipeline wiring — is what `/review` owns in `_review/`.

## Reviewer roster

**5 FINDERS:** `code-reviewer`, `architect`, `qa-reviewer`, `security-reviewer`, `performance-analyst`.

Rationale for the two finders beyond `/audit`'s four: at FEATURE scope, two emergent categories only make sense across tasks and need a dedicated finder each — `architect` covers cross-task architectural drift (the "two tasks that can't both be right" situation, now at feature scale), and `performance-analyst` covers assembled-data-flow performance (a cost that only appears once the tasks compose). Both are emergent categories the per-task panel cannot surface.

**REFUTERS:** `/audit`'s four priority agents — `[code-reviewer, architect, qa-reviewer, security-reviewer]`. This is the existing `_REFUTER_PRIORITY` constant in `_verify.py` (verified: `src/devforge/lib/_audit/_verify.py:80–85`), which **excludes `performance-analyst` by design**. The asymmetry is principled, NOT a bug to fix: a perf specialist SURFACES perf findings (finder role); a generalist REFUTES them (refuter role). `route_refutation` already takes `present_finders` as a parameter and assigns each finding the first present priority agent that is not the finding's author — so a `performance-analyst`-authored finding still gets a valid non-author refuter (the first priority agent ≠ author), and `performance-analyst` can be a FINDER with **zero engine change** to the routing logic — it simply never SERVES as a refuter. (Verified by reading `route_refutation` at `_verify.py:265–339`: the per-finding selection loop iterates `_REFUTER_PRIORITY` and picks the first present, non-author candidate; a `performance-analyst` author falls straight through to `code-reviewer`/`architect`/etc.)

Phase 0 parameterizes the refuter priority list (see below) so this default is explicit and `/audit` stays behaviorally identical, but no change to `route_refutation`'s logic is required to support a 5-finder/4-refuter split.

## Reuse architecture (Path A — the default)

The refutation engine that gives `/audit` its precision is roster-agnostic and is the EXACT machinery `/review` needs. Path A extracts it into `src/devforge/lib/_shared/` so BOTH commands consume one copy; the precision engine never forks.

**What is roster-agnostic (reusable — verified this session via grep + read):**

- `findings_schema.py` — the `Finding` / `AuditReport` dataclasses + `SEVERITY_ENUM` / `CATEGORY_ENUM`. The `agent` field is explicitly NOT validated against a roster (verified: `findings_schema.py:99` docstring "the roster is NOT validated here -- only non-empty is required").
- `_consume.py` — `ParsedFinding` + `parse_agent_tmp`. Parses the finder output-contract markdown into finding dicts; never references a roster (grep for the five agent names in `_consume.py` = 0 matches).
- `_validate.py` — the 5-check anti-hallucination guard (`validate_findings`). Zero roster coupling (grep = 0 matches).
- `_consensus.py` — `compute_consensus` (exact-hash cross-agent merge + severity bump). Zero roster coupling (grep = 0 matches).
- `_verify.py` — the refutation engine: `route_refutation`, `render_verify_brief`, `consume_verdicts`, `apply_verdicts` (the confirmed/dismissed/uncertain/contested D7 partition). The ONLY roster coupling is the module constant `_REFUTER_PRIORITY` (`_verify.py:80–85`), which Phase 0 parameterizes.

**What is roster/audit-SPECIFIC (stays in `_audit/`, NOT extracted — verified this session):**

- `_scope.py` — `_FOCUS_BLOCKS` (keyed to `/audit`'s 4-finder roster, `_scope.py:26–69`) + `render_agent_brief` (injects the audit checklists + a per-agent focus block, raises `ValueError` if `agent not in _FOCUS_BLOCKS`, `_scope.py:571`). `/review` builds its OWN finder brief in `_review/` with its own focus blocks; it does NOT call `render_agent_brief`. `render_verify_brief` (refuter brief, in `_verify.py`) IS roster-agnostic and IS reused.
- `_preflight.py` — `_AUDIT_AGENTS` (the 4-finder `check-agents` roster, `_preflight.py:21–26`). `/review` has its own 5-finder existence check in `_review/`.
- `_report.py` — buckets/renders the `audits/` report (references the agent names). `/review` has its own `_review/_report.py` writing `specs/[feature]/review.md`.
- `_cli.py` — the `_audit` verb registry. `/review` has its own `_review/_cli.py`.

**Phase 0 mechanics:**

1. Move (or re-home) the five roster-agnostic modules — `findings_schema`, `_consume`, `_validate`, `_consensus`, `_verify` — into `src/devforge/lib/_shared/`. The subpackage layout (a `_shared/refutation/` subpackage vs flat `_shared/*` modules) is the author's call at build time; `_shared/` already holds flat modules (`literal_call_shape.py`, `node_bin.py`, `text_overlap.py` — verified via glob), so flat is the established precedent, but a `refutation/` subpackage is acceptable if the five modules read better grouped. Whichever is chosen, name it explicitly in the Phase-0 commit message and the helper-locations table.
2. Parameterize `route_refutation`: add a `priority=None` parameter that defaults to the existing audit constant (`_REFUTER_PRIORITY`) when `None`, so `/audit` callers stay byte-behaviorally identical and `/review` can pass the same four-refuter list explicitly (or rely on the default — they are the same list). Do NOT add `performance-analyst` to the priority list (it is a finder only; see `## Reviewer roster`).
3. Re-point `_audit`'s imports (`_cli.py`, `_merge.py`, `_rank.py`, and the `_audit` test imports) from the moved modules' old `_audit` location to `_shared`. Keep any `_audit`-local re-export shims minimal — prefer updating the import sites over leaving stale aliases (a stale alias is a future-hallucination seed).
4. The regression net is `/audit`'s existing `tests/lib/_audit/` suite (~900 tests per plan 12's count) plus the `_audit` test modules that import the moved schemas. They must stay green after the extraction with no behavior change. (Per repo discipline, the moved modules' own tests move with them to `tests/lib/_shared/` and stay green; new helper tests round-trip real producer output, not hand-faked fixtures.)

**Path A is the default. The alternative is OQ-1** (audit-freeze fallback — `/review` carries its own copy of the engine). Path A is preferred because the precision engine then lives in exactly ONE place and cannot drift between the two commands.

## Pipeline consumers of `review.md`

`review.md` must remain the produced artifact (a markdown file at `specs/[feature]/review.md`), because two downstream consumers already read it:

- `/verify` folds review findings into its verdict (verified: `src/_pending/commands/verify.md:26,34,158,316` — `/verify` reads `specs/[feature]/review.md` and warns if missing; `/verify` is itself an unbuilt draft).
- `/audit` reads recent `specs/*/review.md` files for recurring-issue tracking (verified: `src/commands/audit/main.md:436–437` Phase 4.3 — globs `specs/*/review.md`, extracts Critical findings).

So `_review/_report.py` writes `specs/[feature]/review.md` as markdown. A STRUCTURED sibling handoff (a typed `review-handoff.json` for `/verify` to consume typed fields) is DEFERRED — `/verify` is an unbuilt draft, so "consumer obeys producer" means the producer's structured contract is built when `/verify` is refactored to consume it (this is the same pattern plans applied to plan→breakdown). Recorded as OQ-3.

## Anti-relitigation — honest limitation

`/review` must instruct its finders to report ONLY emergent cross-task issues — NOT to re-flag what the `/implement` per-task panel already forced fixed. This is **PROMPT-ENFORCED ONLY** — it lives in a `references/` anti-relitigation preamble injected verbatim into every finder brief. It is **NOT mechanical**, and the plan states this as a known limitation, not a solved problem:

- `/implement` does not persist per-task findings to a file (the per-task panel's findings live only in that task's loop; PHASE 6 synthesizes them into a repair brief and drives them to clean, then the loop exits — nothing is written to disk for `/review` to dedup against). So there is nothing to mechanically dedup against.
- A mechanical anti-relitigation dedup is therefore INFEASIBLE and is NOT proposed. The honest framing: the per-task panel having already forced its findings clean means a well-behaved finder reviewing the assembled diff SHOULD find mostly emergent issues anyway; the preamble reinforces that, and the refutation pass (Phase 4) filters re-flags that slip through as undemonstrable-at-feature-scope. This narrows but does not eliminate relitigation.

## Phases

Each phase: objective, files touched, helper verbs/modules introduced, and a `## Verify` criterion. Per repo discipline (CLAUDE.md): every `.py` helper change goes through **python-engineer → python-reviewer** with a test written + actually run in the SAME turn (test-immediately-after-write; parsers round-trip REAL producer output, not hand-faked fixtures); every command/spec/reference/CLAUDE.md/plan markdown edit goes through **instruction-author → instruction-reviewer** (route-spec-edits-through-agent-flow); for any Claude-Code-integration concern — the finder/refuter Task dispatch shape, `subagent_type` usage, the emitter/install behavior, command frontmatter (`disable-model-invocation`, `argument-hint`) — verify current conventions via the **claude-code-guide** agent BEFORE writing the spec (confidence is not verification). Each phase leaves the system buildable and tests green.

### Phase 0 — Shared-engine extraction

**Objective:** lift the roster-agnostic refutation engine into `_shared/` so `/review` and `/audit` share one copy; parameterize `route_refutation`'s refuter priority; re-point `_audit` imports; keep `/audit` byte-behaviorally unchanged.

- **Files touched:** move `findings_schema.py`, `_consume.py`, `_validate.py`, `_consensus.py`, `_verify.py` from `src/devforge/lib/_audit/` into `src/devforge/lib/_shared/` (flat or a `_shared/refutation/` subpackage — author's call, named in the commit). Add a `priority=None` param to `route_refutation` (default = the existing `_REFUTER_PRIORITY`). Re-point every `_audit` import of those modules (`_cli.py`, `_merge.py`, `_rank.py`, and the `_audit` test imports) to `_shared`. Move the five modules' own tests to `tests/lib/_shared/`.
- **Modules/verbs introduced:** none new — this is a relocation + one signature widening. No verb signatures change.
- **Execution:** python-engineer → python-reviewer; the moved tests + the re-pointed `_audit` suite run green in the same turn.

#### Verify

```bash
# The five modules now live under _shared:
ls src/devforge/lib/_shared/   # expect: findings_schema, _consume, _validate, _consensus, _verify (flat or under refutation/)
# _audit no longer holds its own copies (re-pointed to _shared):
grep -rn "from .findings_schema\|from ._verify\|from ._consensus\|from ._validate\|from ._consume" src/devforge/lib/_audit/   # read: imports now resolve to _shared (e.g. from .._shared... or a thin re-export shim), no orphaned local copy
# route_refutation parameterized, audit default preserved:
grep -n "def route_refutation" src/devforge/lib/_shared/_verify.py   # expect: signature carries priority=None
grep -n "_REFUTER_PRIORITY" src/devforge/lib/_shared/_verify.py      # expect: still the [code-reviewer, architect, qa-reviewer, security-reviewer] default (performance-analyst NOT added)
# Regression net green — /audit behaviorally unchanged:
python -m pytest tests/lib/_audit/    # expect: green (~900 tests), zero behavior change
python -m pytest tests/lib/_shared/   # expect: green (the moved tests)
```

DoD: the five roster-agnostic modules live under `_shared/`; `route_refutation` takes `priority=None` defaulting to the audit constant (and `performance-analyst` is NOT in that constant); every `_audit` import is re-pointed; the moved tests + the full `tests/lib/_audit/` suite are green with `/audit` byte-behaviorally unchanged; python-reviewer loop applied. (Under OQ-1's audit-freeze fallback this whole phase is replaced by a `/review`-local copy of the engine — see OQ-1; only Phase 0 changes.)

### Phase 1 — `_review/` scaffold + preflight

**Objective:** create the `_review/` subpackage, the launcher, run-state, and the preflight gate.

- **Files touched:** new `src/devforge/lib/_review/` subpackage (`_cli.py` registry mirroring `_audit/_cli.py`'s `_SUBCOMMAND_REGISTRY` pattern at `_cli.py:1375`); new launcher `src/devforge/lib/review_helper{,.py}` (the `.py` shim mirrors `audit_helper.py` verbatim in shape — `sys.path` insert + `from _review._cli import main`); new `src/devforge/lib/_review/_state.py` (status-and-flip, mirroring `_audit/_state.py` `check-status-and-flip`).
- **Modules/verbs introduced:** `check-status-and-flip` (run-state) + a `preflight` verb that gates on (a) the 4-command setup chain `/init-forge → /generate-docs → /configure → /constitute` (mirroring `/audit`'s Phase-1.3 setup expectation), (b) the constitution-populated guard — STOP if `constitution.md` is absent or still carries the unpopulated-constitution sentinels in `_preflight.py` (the same set `/audit`'s `preflight-context` uses — e.g. `{{CONSTITUTION_BODY}}`, `"Run /constitute to populate"`) (the same guard `/audit` `preflight-context` applies via a `constitution_populated` JSON field, `audit/main.md:147`), and (c) Source-Root / wrapper-mode resolution read from `CLAUDE.md` (so finders read source files from the correct location in wrapper mode).
- **Execution:** python-engineer → python-reviewer; tests round-trip a real `CLAUDE.md` + `constitution.md` fixture (populated and unpopulated) in the same turn.

#### Verify

```bash
ls src/devforge/lib/_review/ src/devforge/lib/review_helper src/devforge/lib/review_helper.py   # expect: present
grep -n "_SUBCOMMAND_REGISTRY" src/devforge/lib/_review/_cli.py   # expect: registry present, mirroring _audit
.devforge/lib/review_helper preflight   # (in a fixture) expect: STOPs on unpopulated constitution; passes on populated; reports Source Root
python -m pytest tests/lib/_review/test_preflight.py tests/lib/_review/test_state.py   # expect: green
```

DoD: `_review/` subpackage + `review_helper{,.py}` launcher + `_state.py` exist; the preflight verb gates the setup chain + the populated-constitution sentinel + resolves Source Root/wrapper-mode; helper tests written + run + green; python-reviewer loop applied.

### Phase 2 — Scope resolution

**Objective:** compute the assembled-feature diff (all the feature's tasks together) and render a scope block — replacing the stale draft's task-completion-note prose parsing.

- **Files touched:** new `src/devforge/lib/_review/_scope.py`.
- **Modules/verbs introduced:** `resolve-feature-scope` — given the feature dir (`specs/NNN-…`, from `$ARGUMENTS` or the most-recently-modified feature), compute the changed-files list as the **merge-base diff of the feature's `spec/NNN-…` branch**: `git diff --name-only $(git merge-base <base> HEAD)..HEAD` (the assembled feature diff — every task's changes together, which is exactly the cross-task surface the per-task panel never saw). The verb emits the changed-files list + a rendered scope block (modeled on `_audit/_scope.py` `render_scope_block`). It must handle (a) wrapper-mode source-root (prefix source files with Source Root for the finder briefs, as `/audit` does via `--source-root`), and (b) the WIP-commits-accumulated state — `/implement` leaves per-task WIP commits that are squashed only by `/finalize`, so the merge-base..HEAD range spans many WIP commits and the diff is their union (this is correct: `/review` runs before `/finalize`, so the WIP commits ARE the feature's work).
- **Why merge-base, not completion-note parsing:** the stale draft (`src/_pending/commands/review.md:19,25`) reads each task file's "Completion Notes (files changed)" prose to assemble the changed-file list. That is brittle (depends on the agent having written accurate prose) and is exactly the kind of prose-scrape this repo's "consumer obeys producer" discipline rejects. The git merge-base diff is the mechanical ground truth of what the feature changed.
- **Execution:** python-engineer → python-reviewer; tests round-trip a real git fixture (a feature branch with WIP commits) in the same turn.

#### Verify

```bash
grep -n "resolve-feature-scope" src/devforge/lib/_review/_cli.py   # expect: registered
# In a git fixture with a spec/NNN branch + WIP commits:
.devforge/lib/review_helper resolve-feature-scope --feature specs/001-... --source-root .   # expect: changed-files = merge-base..HEAD union, + scope block
python -m pytest tests/lib/_review/test_scope.py   # expect: green incl. the WIP-commits-span case + wrapper-mode source-root case
```

DoD: `resolve-feature-scope` computes the assembled-feature diff via merge-base..HEAD (handling accumulated WIP commits + wrapper-mode source-root) and renders a scope block; no task-completion-note prose parsing; helper tests written + run + green; python-reviewer loop applied.

### Phase 3 — 5-finder dispatch

**Objective:** dispatch the five finders in adversarial mode over the assembled feature diff, with the anti-relitigation preamble injected, and consume + validate their findings — wiring the orchestrator scratch-chain in `main.md`.

- **Files touched:** new `src/commands/review/references/` — three reference files: (1) an **anti-relitigation preamble** (default = report only emergent cross-task issues, not what the per-task panel already fixed; honest-limitation framing per `## Anti-relitigation`), (2) an **emergent-issue checklist** (the cross-task categories: cross-task security holes, assembled-data-flow performance, cross-task duplication/divergence, cross-task architectural drift — each naming the `Category` its findings carry, mirroring `/audit`'s `best-practices-checklist.md` convention), and (3) a **feature-review report-format** orientation file (the `review.md` skeleton, modeled on `/audit`'s `report-format.md`). New `src/devforge/lib/_review/` brief assembly. New `src/commands/review/main.md`.
- **Modules/verbs introduced:** a `render-agent-brief` verb in `_review/` that assembles the finder brief (the anti-relitigation preamble + emergent-issue checklist injected VERBATIM, the scope block, a per-finder focus block for the 5-finder roster, and the output contract) — this is `/review`'s OWN brief assembly (it does NOT call `_audit`'s `render_agent_brief`, which is keyed to the 4-finder `_FOCUS_BLOCKS`). Consume + validate REUSE `_shared` (`parse_agent_tmp` via a `consume-tmp` verb + `validate_findings` via a `validate-findings` verb) — the finder output contract is the SAME `## Finding N` markdown shape `_shared/_consume.py` parses, so `/review`'s finders write that shape and the shared parser consumes it unchanged.
- **`main.md` wiring:** mirror `/audit`'s orchestrator scratch-chain — each verb's stdout captured to a `$WORKDIR` file the next verb reads (re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-review"` at the top of every Bash block; the literal differs from audit's `forge-audit` to avoid collision). Dispatch the five finders in batches (mirroring `/audit`'s Batch A/B pattern at `audit/main.md:287–294` to avoid context exhaustion — e.g. two batches of 2–3). Each finder writes `$WORKDIR/tmp-<agent>.md` via Bash redirection (read-only finders carry `Bash`, so no Write tool needed — same mechanism `/audit`'s finders use).
- **Execution:** the three references + `main.md` via instruction-author → instruction-reviewer (claude-code-guide consulted first for the 5-finder Task dispatch shape); the `render-agent-brief` verb via python-engineer → python-reviewer with a test in the same turn.

#### Verify

```bash
ls src/commands/review/references/   # expect: 3 reference files (anti-relitigation preamble, emergent-issue checklist, report-format)
grep -n "render-agent-brief\|consume-tmp\|validate-findings" src/devforge/lib/_review/_cli.py   # expect: all registered
# main.md wires the scratch-chain + the 5 finders + anti-relitigation:
grep -n "code-reviewer\|architect\|qa-reviewer\|security-reviewer\|performance-analyst" src/commands/review/main.md   # expect: all 5 finders named
grep -n "forge-review\|WORKDIR\|tmp-" src/commands/review/main.md   # expect: the $WORKDIR scratch-chain
python -m pytest tests/lib/_review/test_scope.py tests/lib/_review/   # expect: green (brief assembly tests incl. anti-relitigation preamble injected verbatim)
```

DoD: the three `references/` files exist (anti-relitigation preamble + emergent-issue checklist + report-format); `render-agent-brief` assembles `/review`'s 5-finder brief with the anti-relitigation preamble injected verbatim; consume + validate reuse `_shared`; `main.md` wires the batched 5-finder dispatch + the orchestrator scratch-chain (`$WORKDIR=forge-review`); helper test + author→reviewer + claude-code-guide loops applied.

### Phase 4 — Refutation pass

**Objective:** cross-examine the validated findings with `/review`'s roster and partition into confirmed / dismissed / uncertain / contested — reusing the `_shared` refutation engine wholesale.

- **Files touched:** `src/commands/review/main.md` (the refutation sub-phase wiring); `src/commands/review/references/` reuses the SAME refutation preamble `/audit` ships (it is finder-agnostic — verified: `src/commands/audit/references/refutation-preamble.md` carries no agent-specific persona, the persona comes from `subagent_type`). Either reference `/audit`'s copy or ship `/review`'s own copy of the identical file (author's call; if copied, note it is a deliberate duplicate of a finder-agnostic file, kept in sync). No new helper module — Phase 4 calls the `_shared` verbs.
- **Modules/verbs introduced:** none new — REUSE `_shared` `route_refutation` (the `route-refutation` verb) / `render_verify_brief` (`render-verify-brief`) / `consume_verdicts` (`consume-verdicts`) / `apply_verdicts` (`apply-verdicts`), exposed through `_review/_cli.py` (which imports them from `_shared`). The refuter priority is `/audit`'s four (`route_refutation`'s default, with `performance-analyst` excluded — see `## Reviewer roster`), so a `performance-analyst`-authored finding routes to the first non-author priority refuter and `performance-analyst` never refutes.
- **D7 partition (same routing as `/audit`):** `apply_verdicts` returns confirmed / dismissed / uncertain / contested, routing high-stakes `security` / `[CONSTITUTION-VIOLATION]` `uncertain` (and a dismissed grounded `[CONSTITUTION-VIOLATION]`) to the headline `[CONTESTED]` bucket, all other-category `uncertain` to the appendix (verified: `_shared/_verify.py` `apply_verdicts` D7 logic — `_is_high_stakes`, `_has_constitution_tag`, the constitution carve-out).
- **`main.md` wiring:** mirror `/audit`'s Phase-4.2.5 per-author dispatch loop (`audit/main.md:374–431`): `route-refutation` over the validated working list + the present-finders list → per-refuter-group `render-verify-brief` + refuter Task dispatch (in batches) → `consume-verdicts` per refuter → merge → `apply-verdicts` → the four buckets.
- **Execution:** `main.md` via instruction-author → instruction-reviewer (claude-code-guide consulted for the refuter Task dispatch shape). No new helper code — the `_shared` verbs are already tested; `_review/_cli.py` exposes them, and the exposure (the registry entries + the import wiring) gets a python-engineer → python-reviewer pass with a test asserting the verbs dispatch to the shared functions.

#### Verify

```bash
# The shared refutation verbs are exposed through review_helper:
grep -n "route-refutation\|render-verify-brief\|consume-verdicts\|apply-verdicts" src/devforge/lib/_review/_cli.py   # expect: all four registered (importing from _shared)
# main.md wires the refutation pass with review's roster:
grep -n "route-refutation\|apply-verdicts\|confirmed\|dismissed\|contested" src/commands/review/main.md   # expect: the D7 partition wired
# The refutation preamble is present (shared copy or review's own identical copy):
ls src/commands/review/references/refutation-preamble.md 2>/dev/null || grep -n "refutation-preamble" src/commands/review/main.md   # expect: resolvable
python -m pytest tests/lib/_review/   # expect: green (the verb-exposure test confirms review_helper dispatches to _shared)
```

DoD: `/review`'s refutation pass reuses `_shared` `route_refutation` / `render_verify_brief` / `consume_verdicts` / `apply_verdicts` with `/review`'s roster (4 refuters, `performance-analyst` finder-only); the D7 confirmed/dismissed/uncertain/contested partition is wired in `main.md`; the refutation preamble is resolvable; the verb-exposure test is green; author→reviewer + claude-code-guide loops applied.

### Phase 5 — Report

**Objective:** render `specs/[feature]/review.md` (helper-owned) from the partitioned findings, plus an inline summary — feeding `/verify` + `/audit`'s recurring scan.

- **Files touched:** new `src/devforge/lib/_review/_report.py`; `src/commands/review/main.md` (the report + summary phases).
- **Modules/verbs introduced:** a `render-report` verb that writes `specs/[feature]/review.md` — CONFIRMED findings as the headline, high-stakes `[CONTESTED]` findings surfaced IN the headline flagged (never buried), and a Dismissed / Worth-a-glance appendix for dismissed + low-stakes uncertain (the same headline/appendix split `/audit`'s `_report.py` applies, but writing to `specs/[feature]/review.md` not `audits/`); plus a `render-inline-summary` verb (count-first inline block, per the audit-format discipline). The report is **findings only, NO verdict** — preserve the stale draft's contract (`src/_pending/commands/review.md:144` "Review does not render a verdict — the verdict is `/verify`'s job"); the verdict belongs to `/verify`, which consumes `review.md`.
- **Execution:** python-engineer → python-reviewer; `_report.py` tests round-trip a real partitioned-findings dict (confirmed/dismissed/uncertain/contested) in the same turn; `main.md` phases via instruction-author → instruction-reviewer.

#### Verify

```bash
grep -n "render-report\|render-inline-summary" src/devforge/lib/_review/_cli.py   # expect: registered
# Report writes specs/[feature]/review.md, findings-only, headline + appendix:
.devforge/lib/review_helper render-report --report <fixture> --feature specs/001-...   # expect: specs/001-.../review.md written; CONFIRMED headline + [CONTESTED] surfaced + Dismissed appendix; NO verdict line
python -m pytest tests/lib/_review/test_report.py   # expect: green (headline = confirmed ∪ high-stakes contested; appendix = dismissed + low-stakes uncertain; no verdict)
```

DoD: `render-report` writes `specs/[feature]/review.md` (helper-owned) with a CONFIRMED headline + surfaced high-stakes `[CONTESTED]` + a Dismissed/Worth-a-glance appendix, findings-only (no verdict); `render-inline-summary` prints the count-first block; the output feeds `/verify` + `/audit`'s recurring scan; helper tests written + run + green; author→reviewer + python→reviewer loops applied.

### Phase 6 — Wire-in

**Objective:** make `/review` actually emit + install, delete the stale draft, and reconcile every `/review` reference.

- **Add `review` to the emitter `_PROMOTED` tuple** — `scripts/emitters/claude.py:51` (verified: the tuple currently ends `…, "implement", "pr-review", "audit")` and does NOT contain `review`, so `/review` is NOT emitted today). Append `"review"`.
- **DELETE the stale `src/_pending/commands/review.md`** (the pre-pivot draft superseded by the live command). Sweep for any live consumer of that path before deleting.
- **Reconcile `src/CLAUDE.md`:** the `/review` "Command Details" entry already exists (verified: `src/CLAUDE.md` `#### /review [spec-file]`) and the Workflow chain already names `/review` in the `/implement → /review → /verify` slot — update the entry's body to describe the redesigned command (emergent cross-task review, 5-finder ensemble + refutation, `specs/[feature]/review.md`, findings-only) without changing its pipeline position. Keep it a purpose one-liner per the plan-08 trim discipline (mechanics live in `main.md`).
- **Cross-ref sweep of every `/review` reference** (verified inventory this session, to confirm each still aligns after the redesign):
  - `src/CLAUDE.md` — Workflow chain line + the `/review` Command-Details entry (reconcile, above).
  - `src/commands/plan/main.md:24` + `src/commands/breakdown/main.md:23` — the workflow-chain comment lines naming `/review` (confirm still accurate; no change expected).
  - `src/commands/breakdown/main.md:242–243` + `src/_pending/commands/_agent-assignment.md` — the agent-assignment rows stating `performance-analyst` / `security-reviewer` "review during `/review`, never implement" (confirm still accurate — `/review` is where those agents review; no change expected).
  - `src/agents/architect.md:146` — "Reject any request to run /specify, /implement, /review, …" (confirm still accurate; `architect` is a `/review` FINDER but does not RUN the command — no change).
  - `src/agents/qa-reviewer.md:3` — "Use during /review, /audit, /fix, and /refactor" (confirm still accurate; `qa-reviewer` is a `/review` finder — no change).
  - `src/commands/audit/main.md:436–437` — the recurring-issue scan that globs `specs/*/review.md` (confirm the redesigned `review.md` is still the artifact it reads — it is, per Phase 5; no change).
  - `src/_pending/commands/verify.md` — the `/verify` draft's `review.md` consumption (an unbuilt draft; confirm it still references `specs/[feature]/review.md` — it does; the structured-handoff producer is OQ-3/deferred, so no change here now).
- **Install-ride verification** (mirror how plans 10/11 describe their install-ride checks): run `install.sh <tmp-target>` and confirm `review command: yes (folder, N references)` (N = the reference-file count from Phase 3, auto-globbed by the emitter), **0 `{{` placeholder leaks** in the emitted command, and an **executable `review_helper` installed** at `.devforge/lib/review_helper`.
- **Execution:** the `_PROMOTED` edit is a one-line Python tuple change (python-engineer → python-reviewer — confirm the emit still passes `tests/scripts/`); the deletion + all markdown reconciliation via instruction-author → instruction-reviewer; claude-code-guide consulted for the emitter/install behavior. Add a `CHANGELOG.md` entry + the repo-root `CLAUDE.md` active-plans entry for plan 20.

#### Verify

```bash
# review promoted in the emitter:
grep -n "review" scripts/emitters/claude.py   # expect: "review" in _PROMOTED
# stale draft deleted, no live consumer:
ls src/_pending/commands/review.md 2>/dev/null   # expect: absent
grep -rn "_pending/commands/review" src/ scripts/ install.sh   # expect: no live consumer
# every /review reference still aligns (no dangling):
grep -rn "/review\|review\.md" src/ | grep -v "pr-review\|review-loop\|review-panel\|review-helper"   # read: only the inventoried, still-accurate references
# install ride:
#   install.sh <tmp> reports: review command: yes (folder, N references); 0 '{{' leaks; .devforge/lib/review_helper executable
python -m pytest tests/scripts/   # expect: green (emit still works with review added)
```

DoD: `review` is in `_PROMOTED` (so it emits/installs); the stale `src/_pending/commands/review.md` is deleted with no live consumer; the `src/CLAUDE.md` entry + Workflow chain reconcile to the redesigned command (pipeline position unchanged); the cross-ref sweep is clean (every inventoried `/review` reference still accurate); the install ride shows `review command: yes` with N references, 0 `{{` leaks, and an executable helper; `CHANGELOG.md` + repo-root `CLAUDE.md` updated; author→reviewer + python→reviewer + claude-code-guide loops applied.

### Phase 7 — testForge20 e2e (USER-DRIVEN — HARD GATE)

**Objective:** the repo's standard manual e2e gate — confirm `/review` works end to end on a real multi-task feature.

- Re-install the forge into testForge20 (so the new `/review` source is emitted) and run `/review` over a feature whose tasks were drained by `/implement` (a multi-task feature with an assembled diff spanning several WIP commits).
- **Success looks like:** the run surfaces ≥1 GENUINE emergent cross-task finding (a cross-task security hole, an assembled-data-flow perf issue, cross-task duplication, or architectural drift — something the per-task panel structurally could not have seen); the refutation pass DISMISSES fabricated/undemonstrable findings (precision held); `specs/[feature]/review.md` is written with the CONFIRMED headline + Dismissed appendix, findings-only (no verdict); and `/verify` can consume the written `review.md` (the consumer reads it — verified against the `/verify` draft's read path, when `/verify` exists).
- Confirm the install ride (can be checked now): `review command: yes (folder, N references)`, 0 `{{` leaks, executable helper.

#### Verify

```bash
# (User-driven — run against a testForge20 install with the new source emitted.)
# Observe during the /review run:
#   - resolve-feature-scope computes the assembled merge-base..HEAD diff across the feature's WIP commits.
#   - The 5 finders dispatch in batches; the refutation pass runs with the 4-refuter roster (performance-analyst finds, never refutes).
#   - At least one genuine emergent cross-task finding is CONFIRMED and headlined.
#   - Fabricated / per-task-already-fixed findings are DISMISSED (precision).
#   - specs/[feature]/review.md is written: CONFIRMED headline + [CONTESTED] surfaced + Dismissed appendix; NO verdict line.
#   - /verify can read the review.md (when /verify exists).
```

DoD: e2e confirms `/review` over a multi-task feature surfaces ≥1 genuine emergent cross-task finding, refutation dismisses fabricated ones, `review.md` is written (findings-only), and `/verify` can consume it; user-driven sign-off.

## Decisions (settled — flip any during review)

### D1 — `/review` is feature-level emergent review; `/audit` is standalone

`/review` owns the cross-task EMERGENT job (issues the per-task panel cannot see by construction); `/audit` owns the standalone periodic whole-project audit. They share machinery (the refutation engine) but not jobs (see the invariant table in `## Command mission`). "Standalone" for `/review` means code-independence from `/audit`, never workflow-independence.

### D2 — 5 finders, 4 refuters (performance-analyst finds but never refutes)

Finders: `code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst`. Refuters: `/audit`'s four (`_REFUTER_PRIORITY`, excluding `performance-analyst`). The asymmetry is principled (a specialist surfaces, a generalist refutes) and needs ZERO change to `route_refutation`'s logic — a `performance-analyst`-authored finding already routes to the first non-author priority refuter (verified against `route_refutation` at `_verify.py:265–339`). Do NOT add `performance-analyst` to the refuter priority list.

### D3 — Path A (shared extraction) is the default; the engine never forks

Extract the roster-agnostic engine into `_shared/` and parameterize `route_refutation`'s priority so both commands consume one copy. The precision engine lives in exactly one place; duplication is the OQ-1 fallback only, taken only under an audit-freeze constraint.

### D4 — `review.md` stays a markdown artifact; the structured handoff is deferred

`review.md` remains a produced markdown file (`/verify` + `/audit` already consume it). A typed `review-handoff.json` for `/verify` is deferred until `/verify` is built to consume it ("consumer obeys producer") — OQ-3.

### D5 — Anti-relitigation is prompt-enforced only (honest limitation)

`/implement` does not persist per-task findings, so a mechanical dedup is infeasible. The anti-relitigation preamble (a `references/` file injected verbatim) is the only mechanism; the plan states this as a known limitation, not a solved problem. Do NOT propose a mechanical dedup.

### D6 — Scope is the assembled-feature git diff, not completion-note prose

`resolve-feature-scope` computes the changed-files list from `git diff --name-only $(git merge-base <base> HEAD)..HEAD` (the union of the feature's WIP commits), not by parsing task-completion-note prose (which the stale draft did). The git diff is mechanical ground truth.

## Open questions (OQ-N)

- **OQ-1 — audit-freeze fallback for Phase 0.** Path A (D3) extracts the engine into `_shared/` and re-points `/audit`'s imports, which touches `/audit`'s source. IF the project decides `/audit` must stay byte-FROZEN until its own testForge20 e2e (plan 11/12/19 gate) passes — i.e. no `/audit` source may change first — then Phase 0 is replaced by the fallback: `/review` carries its OWN copy of the five engine modules under `_review/`, and `/audit` is left untouched. Cost of the fallback: the precision engine then lives in TWO places and can DRIFT (a bug fixed in one copy is not fixed in the other) — strictly worse than Path A. Under the fallback ONLY Phase 0 changes (the engine is copied, not moved; `route_refutation`'s priority is parameterized in `/review`'s copy only); Phases 1–7 are identical. **Lean: Path A** — the `tests/lib/_audit/` suite is the regression net that proves `/audit` stays behaviorally identical through the extraction, so a true byte-freeze is unnecessary. Resolve with the user before Phase 0.
- **OQ-2 — `_shared/` layout: flat modules vs a `_shared/refutation/` subpackage.** `_shared/` currently holds flat modules (`literal_call_shape.py`, `node_bin.py`, `text_overlap.py` — verified via glob), so flat is the established precedent. But the five refutation modules are a cohesive cluster and might read better under `_shared/refutation/`. Lean: flat (follow the existing `_shared/` precedent), but defer to the author at Phase-0 build time; name the choice in the commit and the helper-locations table. This is an authoring-mechanics decision, not architecture.
- **OQ-3 — structured `review-handoff.json` for `/verify`.** Deferred (D4): `/verify` is an unbuilt draft, so the producer-side typed handoff is built when `/verify` is refactored to consume it ("consumer obeys producer"). For now `review.md` markdown is the only contract. Resolve when `/verify` is built, not in this plan.

## Out of scope (do NOT plan here)

- **Changing `/implement`'s per-task panel** (`src/commands/implement/main.md` PHASE 6 — plan 17 owns it). `/review` must NOT relitigate what the per-task panel already forced fixed; it only adds the feature-level emergent layer.
- **Changing `/verify`** (an unbuilt draft). `/review` produces `review.md`; `/verify` consumes it when `/verify` is built. The structured handoff is OQ-3.
- **Adding `performance-analyst` to the refuter priority list** (D2 — it is a finder only).
- **A mechanical anti-relitigation dedup** (D5 — infeasible; per-task findings are not persisted).
- **Re-opening `/audit`'s recall or precision work** (plans 10/11/12/19). Phase 0 extracts the shared engine without changing `/audit`'s behavior; the `tests/lib/_audit/` suite proves it.
- **A new agent `.md` file.** `/review`'s 5 finders + 4 refuters are all existing plan-15 roster agents; no 18th agent.

## Context for next session

- `/review` is the FEATURE-LEVEL emergent cross-task review — the pipeline step after `/implement` drains a feature's tasks, before `/verify`. Its sole reason to exist: `/implement` PHASE 6 already forces a per-task 4-reviewer panel clean (all findings fixed), and `/verify` does the cross-task INTEGRATION check, so the only UNOWNED job is emergent cross-task issues the per-task panel cannot see in isolation (cross-task security holes, assembled-data-flow perf, cross-task duplication, architectural drift). See the review-vs-audit invariant table in `## Command mission`.
- **5 finders** (`code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst`), **4 refuters** (`/audit`'s `_REFUTER_PRIORITY`, performance-analyst excluded — it finds, never refutes; ZERO `route_refutation` change needed, verified at `_verify.py:265–339`).
- **Path A (D3):** extract the roster-agnostic engine — `findings_schema`, `_consume`, `_validate`, `_consensus`, `_verify` (verified zero roster coupling this session) — into `_shared/`; parameterize `route_refutation`'s priority (`priority=None` defaulting to the audit constant); re-point `_audit` imports; `tests/lib/_audit/` (~900 tests) is the regression net proving `/audit` stays behaviorally identical. The roster-coupled `_audit` pieces (`_scope._FOCUS_BLOCKS` + `render_agent_brief`, `_preflight._AUDIT_AGENTS`, `_report`, `_cli`) STAY in `_audit/`; `/review` builds its own brief/preflight/report/cli in `_review/`. The refutation preamble (`audit/references/refutation-preamble.md`) is finder-agnostic and reused verbatim (the persona comes from `subagent_type`).
- **8 phases:** 0 shared-engine extraction → 1 `_review/` scaffold + preflight → 2 scope resolution (merge-base..HEAD assembled diff, not completion-note prose) → 3 5-finder dispatch (anti-relitigation preamble + emergent-issue checklist + report-format references; brief assembly; consume+validate reuse `_shared`; orchestrator scratch-chain `$WORKDIR=forge-review`) → 4 refutation pass (reuse `_shared` route/render-verify/consume-verdicts/apply-verdicts; D7 partition) → 5 report (`specs/[feature]/review.md`, confirmed headline + [CONTESTED] surfaced + dismissed appendix, findings-only no verdict) → 6 wire-in (add `review` to emitter `_PROMOTED` at `claude.py:51`; delete stale `src/_pending/commands/review.md`; reconcile `src/CLAUDE.md`; cross-ref sweep; install ride) → 7 testForge20 e2e (USER-DRIVEN HARD GATE).
- **3 OQs:** OQ-1 (audit-freeze fallback — `/review`-local engine copy if `/audit` must stay byte-frozen; lean Path A), OQ-2 (`_shared/` flat vs `refutation/` subpackage; lean flat), OQ-3 (structured `review-handoff.json` for `/verify`; deferred until `/verify` is built).
- **Honest limitations recorded:** anti-relitigation is prompt-only (D5 — per-task findings are not persisted, so no mechanical dedup); the structured handoff is deferred (D4/OQ-3).
- **Verified file:line facts (this session):** `_PROMOTED` lacks `review` (`scripts/emitters/claude.py:51`); `route_refutation(findings, present_finders)` + `_REFUTER_PRIORITY = [code-reviewer, architect, qa-reviewer, security-reviewer]` excludes performance-analyst (`_verify.py:80–85, 265–339`); the D7 partition (`apply_verdicts`, `_verify.py:532–632`); `findings_schema`/`_consume`/`_validate`/`_consensus`/`_verify` have zero roster coupling (grep = 0 for the five agent names in `_validate.py`/`_consensus.py`/`_consume.py`); `_FOCUS_BLOCKS` (audit-specific, `_scope.py:26–69`) + `render_agent_brief` raises on unknown agent (`_scope.py:571`); `_AUDIT_AGENTS` (audit-specific, `_preflight.py:21–26`); `_shared/` holds flat modules (`literal_call_shape.py`, `node_bin.py`, `text_overlap.py`); `audit_helper.py` launcher shim shape (the `review_helper.py` model); the audit scratch-chain + Batch A/B dispatch (`audit/main.md:287–294, 374–431`); `/implement` per-task panel + all-findings-fixed gate (`implement/main.md:176–213`); the `/review` reference inventory (`src/CLAUDE.md` Workflow + Command-Details entry; `plan/main.md:24`; `breakdown/main.md:23,242–243`; `architect.md:146`; `qa-reviewer.md:3`; `audit/main.md:436–437`; `verify.md:26,34,158,316`; the stale draft `src/_pending/commands/review.md`).

## When resuming work

1. **Re-read this plan in full** + the live files it grounds against: `src/_pending/commands/review.md` (the stale draft being replaced), `src/commands/audit/main.md` (the structural model + the refutation scratch-chain), `src/devforge/lib/_audit/_verify.py` (the engine being reused) + `_consume.py` / `_validate.py` / `_consensus.py` / `findings_schema.py` (the other roster-agnostic pieces) + `_scope.py` / `_preflight.py` (the roster-coupled pieces that STAY in `_audit/`), `src/commands/implement/main.md` PHASE 6 (the per-task panel `/review` must not relitigate), and `src/CLAUDE.md` (the `/review` entry + workflow chain the wire-in reconciles). The `main.md`/helper line numbers above are pre-edit; re-read each file from scratch after a phase edits it.
2. **Resolve OQ-1 (audit-freeze: Path A or fallback) with the user BEFORE Phase 0** — it determines whether Phase 0 MOVES the engine (Path A, lean) or COPIES it (`/review`-local). OQ-2 (`_shared/` layout) and OQ-3 (structured handoff) can ride the leans.
3. **Execute Phases 0→7 in order** (each green before the next). Phase 0 is the foundation (the shared engine); Phases 1–5 build `_review/` + `main.md` on top; Phase 6 wires it into the emitter + reconciles docs; Phase 7 is the user-driven HARD GATE.
4. Route every Python helper change through **python-engineer → python-reviewer** with a test written + run in the same turn (round-trip REAL producer output — the finder/refuter markdown contracts and a real git fixture for scope — not hand-faked fixtures); route every command/spec/reference/CLAUDE.md/plan markdown edit through **instruction-author → instruction-reviewer**; verify the 5-finder + 4-refuter Task dispatch shape, `subagent_type` usage, the emitter/install behavior, and command frontmatter via the **claude-code-guide** agent BEFORE writing the relevant spec.
5. Commit alongside the work in repo commit style (lowercase, terse, scope prefix — e.g. `feat(review): feature-level emergent review on the shared refutation engine`, `refactor(shared): extract roster-agnostic refutation engine from _audit`).

## Related plans

- `17-IMPLEMENT-PER-TASK-PANEL-PLAN.md` — owns `/implement`'s PER-TASK 4-reviewer panel + all-findings-fixed gate (SHIPPED). `/review` is the FEATURE-LEVEL layer ABOVE that per-task panel — it catches the emergent cross-task issues the per-task panel structurally cannot see, and must NOT relitigate what the per-task panel already forced fixed (D5).
- `19-AUDIT-FALSE-POSITIVE-PRECISION-PLAN.md` — built `/audit`'s refutation / cross-examination stage (`_verify.py` + the four verbs + `references/refutation-preamble.md`, SHIPPED in the working tree). This plan EXTRACTS that engine into `_shared/` (Phase 0) and REUSES it for `/review`; it parameterizes `route_refutation`'s priority so `/audit` stays behaviorally identical. The refutation-preamble is finder-agnostic and reused verbatim.
- `10-AUDIT-COMMAND-PORT-PLAN.md` + `11-AUDIT-FULL-SPECTRUM-PLAN.md` + `12-AUDIT-MULTI-PASS-UNION-PLAN.md` — built/extended `/audit` (the structural model for `/review`'s `main.md` scratch-chain, batched dispatch, helper/orchestrator split). Their user-driven testForge20 e2e gates are independent of this plan; Phase 0's regression net (`tests/lib/_audit/`) is what keeps `/audit` behaviorally identical through the extraction (OQ-1).
- `15-AGENT-STANDARDIZATION-PLAN.md` — owns the 17-agent roster + the `generate-agents.py` build contract. All of `/review`'s 5 finders + 4 refuters are existing standardized roster agents; this plan adds NO agent file and does not touch plan 15's roster.
