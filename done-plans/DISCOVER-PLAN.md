# /discover command plan

Status: **partial — helper done, spec done, emitter done, 4 empirical runs DONE + 5 fix families (A+B+C+E+F) applied 2026-05-14. D deferred. Empirical spot-rerun + ship still pending.** Net-new command.
Active branch: `develop-2.0-init` (or successor — confirm at session start).

## Next session pickup (READ FIRST)

State as of 2026-05-14:

- Helper shipped: `src/devforge/lib/discover_helper.py` (~2026 LOC) + launcher + `tests/lib/test_discover_helper.py` (156 tests passing on `.venv-test/bin/pytest`).
- Spec shipped: `src/commands/discover/main.md` (429 lines) — passed triple-verify (instruction-reviewer + claude-code-guide both clean after 1 fix-loop iter).
- Emitter wired: `scripts/emitters/claude.py` `_PROMOTED` includes `"discover"`.
- Cross-doc updates landed: `README.md`, `src/CLAUDE.md` template, `DEVELOPMENT-STATUS.md`, `src/devforge/storage-rules.md`.
- testForge20 emitted: `scripts/generate.sh` already propagated `/discover` spec + helper to `/Users/mykolakudlyk/Projects/testForge20/`.
- Empirical runs done on testForge20 (4 saved reports under `discover/`):
  - Run 1 (vague audit-log): verdict `Reconsider`, exposed Prior Art render bug — FIXED inline 2026-05-13.
  - Run 2 (anchored tamper-evident): verdict `Reconsider`, exposed slug-truncation bug → Fix C.
  - Run 3 (vague background-jobs): verdict `Reconsider`, exposed Option-letter prefix-dup bug → Fix E. Drift-detection NOT exercised on this run.
  - Run 4 (anchored background-queue): verdict `Promising with caveats` — FIRST proceeding-set verdict. Drift-detection fired mid-rubric + resolved via user-chosen path. Exposed next-step text bloat + literal `\\n\\n` artifacts → Fix F.
- All findings batched into the "Pending fixes" section below.

**To resume**: apply fixes A through F in one revision cycle (D deferred). See "## Pending fixes from empirical runs" + "### When to apply" sections below for exact code locations, helper/spec edit shapes, test additions, and the 6-step apply sequence. Then spot-rerun Run 1 audit-log topic to confirm Fix B materially changes output (internal canonical search should surface `RevisionHistoryBLoC` upfront via the new Phase 2.0 step instead of via Stream B accident).

## Session log

### 2026-05-14 session 2 — fixes A+B+C+E+F applied + propagated to testForge20

Helper + spec edits, tests, triple-verify, re-emit. Spot-rerun pending user invocation.

**Helper changes** (`src/devforge/lib/discover_helper.py`):

- **Fix C** — `derive_topic_slug` now truncates at last `-` boundary before `_SLUG_MAX_CHARS` (was mid-char). Empty fallback paths preserved.
- **Fix E** — `cmd_set_design_option` rejects `--name` starting with `^(option\s+)?[a-z]\s*:\s*` (regex `_OPTION_LETTER_PREFIX_RE`); exit 2 with explicit message. Reasoning: defensive setter rejection > pure spec instruction per `feedback_helper_owns_contract_filesystem_forcing`. "Option A" without colon still accepted (no rendering bug there).
- **Fix F1** — `cmd_set_next_step_text` gains `--topic` arg. When passed, distilled topic = `--topic`; else fallback to first-sentence split of `functional_scope.value`. Spec instructs orchestrator to pass distilled `≤200 char` value.
- **Fix F2** — new `_clean_inline_escapes` helper collapses `\\r\\n` / `\\n` / `\\r` / `\\t` literal escape sequences (and runs of them) to a single space. Applied to `--topic`, `functional_scope`, `users`, `success_criteria`, `recommended_name` before composing next-step text. Defensive — orchestrator should NEVER pass literal escapes, but Run 4 evidence shows it happens.
- **Fix B (invariant G)** — new rule in `cmd_verify`: when ≥1 `prior_art[*].source.startswith("internal:")`, `recommended_option.rationale` MUST contain at least one of those `internal:<path>` substrings. Forces "extend existing X" framing; "build new" requires explicit capability-gap rationale.

**Spec changes** (`src/commands/discover/main.md`):

- **Fix A** — new "**`--module-path` grounding (MANDATORY)**" paragraph inserted in Step 2.2 (formerly "Stream B"), immediately after the `record-integration-touchpoint` example. Specifies verbatim copy from `search_graph` / `search_code` result-row `file_path`, fallback retry chain, unverified marker convention.
- **Fix B** — new `### Step 2.0 — Internal canonical-pattern search (MANDATORY)` section before Step 2.1. Specifies verb/noun extraction from `functional_scope`, project-wide `search_graph` + `search_code` chain, `record-prior-art --source "internal:<file_path>"` setter, verbatim-echo user-facing report (gate before Step 2.1), helper-invariant-G cross-reference. Updated Phase 2 intro to "three sequential steps" framing. Renamed Stream A → Step 2.1 (gap-narrowed), Stream B → Step 2.2. Added rule G to verify rules list.
- **Fix E** — design-options setter prose adds the no-letter-prefix mandate + setter-rejection note.
- **Fix F** — `set-next-step-text` directives split into pursue-verdict (with `--topic`) and Reconsider (without `--topic`) bash blocks; Reconsider call now correctly framed as "clears `next_step_text` to `None`" (not "no-op"). Topic distillation guidance + literal-escape defensiveness clause.

**Triple-verify result**: instruction-reviewer found 3 findings (1 high logical-contradiction, 1 medium placeholder mismatch, 1 low verbatim-echo wording miss); claude-code-guide clean. All 3 findings auto-fixed inline.

**Tests**: 171 passing (was 156; +15 across slug-boundary, option-letter rejection + render shape, next-step `--topic` + escape stripping, invariant G coverage). `.venv-test/bin/pytest tests/lib/test_discover_helper.py -q` clean.

**Propagation**: `bash scripts/generate.sh /Users/mykolakudlyk/Projects/testForge20` pushed spec; helper synced manually via `cp src/devforge/lib/discover_helper.py /Users/mykolakudlyk/Projects/testForge20/.devforge/lib/discover_helper.py` (generate.sh does NOT propagate `.devforge/lib/` — install.sh's `cp -R src/devforge/.` is the only end-to-end install path).

**Pending for next session**:

1. User invokes `/discover "audit log for quote and order changes"` on testForge20. Verify Step 2.0 surfaces existing implementation entries upfront (Run 1 evidence pre-fix: only caught via Stream B accident). Verify rule G fires when rationale doesn't cite internal source. Verify recommended-option rationale frames as "extend existing `<path>`".
2. On clean spot-rerun: cross-update README, DEVELOPMENT-STATUS, `src/CLAUDE.md` (none needed if no command-surface changes — but verify), CHANGELOG entry. Then ship to develop-2.0-init.
3. Cross-doc check: confirm `src/CLAUDE.md` `/discover` description still accurate (mentions 8 dimensions, two streams → may need "three steps" framing update); README + DEVELOPMENT-STATUS narrative likely unaffected.

### 2026-05-13 to 2026-05-14 — 4 empirical runs on testForge20

Setup: `develop-2.0-init` branch, /discover spec + helper shipped end-to-end via `scripts/generate.sh` against `/Users/mykolakudlyk/Projects/testForge20`. Helper invariants verified across all 4 runs (verdict-flip rule fired correctly on every Strained-or-Major case + did NOT fire on Acceptable-or-Medium case; next-step text correctly omitted on Reconsider verdicts and rendered on `Promising with caveats`). CBM-usage telemetry grew across runs (run 1 baseline 427 lines → run 4 643 lines, +216 calls total across 4 runs).

Findings surfaced + queued: Fix A (path grounding) and Fix B (internal canonical-pattern search) from parallel-session audit against /research-parity lessons; Fix C (slug truncation), Fix E (option-letter prefix dup), Fix F (next-step text bloat + `\n\n` artifacts) from empirical run output. Fix D (verdict-flip rationale framing) deferred pending more evidence. Prior Art render bug discovered in Run 1 and fixed inline same-day (helper edit + re-render of saved report + propagate to testForge20).

Verdict distribution: 3× `Reconsider` (runs 1-3) + 1× `Promising with caveats` (run 4 — first proceeding-set, also first to emit copy-pasteable `/specify` next-step block). Drift-detection only exercised on run 4 (anchored topic `BullMQ-style or Temporal-style` vs constraints `tab close kills job, no new GraphQL operations` — resolved by rewriting `integration_points` to browser-only). Run 4 surfaced the richest constitution-constraint set (6 §refs vs 4 in earlier runs) suggesting orchestrator's reading of `constitution.md` deepens with more dimensions filled.

### 2026-05-12 session 1 — helper shipped, subagent dropped

Source: parallel-session audit 2026-05-14 against /research lessons (commits `9b900ff`, `910ad51`, `fad9f58`, `5427407`); empirical Run 1 (audit log, 2026-05-13) showed Stream B fit-check caught existing-infra reuse opportunity only because user's `integration_points` answer happened to point at the right packages — not robust to wrong-belief inputs.

Status of /research-parity lessons in /discover spec (`src/commands/discover/main.md` 429 lines):

| /research fix | /discover coverage | Action |
|---|---|---|
| Fresh-every-run (drop kill-and-resume) | ✅ covered (line 72) | none |
| Anti-skip rubric + anti-fabrication user-mode | ✅ covered (lines 78, 80) | none |
| `file:line` grounding from CBM result rows | ⚠ partial — `--module-path` accepted with no mandatory grounding clause | **Fix A** |
| Phase 2.4b canonical-pattern search (reuse over reinvent) | ✗ missing — only descriptive prose at lines 214/223 | **Fix B** |

### Fix A — `--module-path` grounding mandate

**Where**: Phase 2 Stream B Layer 2, after the CBM discovery chain block (around line 265 of `src/commands/discover/main.md`, near `record-integration-touchpoint --module-path` example).

**Add (verbatim wording, adapted from /research Phase 2.3 file:line grounding rule)**:

> **`--module-path` grounding (MANDATORY).** Every `module_path` value you pass to `record-integration-touchpoint` MUST be copied verbatim from a `search_graph` or `search_code` result row's `file_path` field, or be a directory prefix common to ≥2 such result rows (e.g., `packages/<pkg-name>/src/<concern>`). Never derive a module path from `get_code_snippet` output, raw recollection, or prose context — the LLM will hallucinate plausible-but-nonexistent package paths. If you only have a snippet and need the path, re-run `search_code` for a literal token from the snippet to recover the authoritative row. If that re-run returns 0 hits, widen the token (try a longer substring or a different literal from the same snippet) and retry once. If still 0 hits, the module is not reliably locatable — record `--module-path="(unverified)"` and note the unconfirmed status in `--reason`.

**Helper changes**: none required. `record-integration-touchpoint` already accepts the value as-is; mandate lives in spec prose. Same pattern as /research file:line.

**Cross-check**: grep entire spec body for any other `--module-path` site. There is one example block at line 265 — the new mandatory clause goes immediately after it.

### Fix B — Internal canonical-pattern search (Phase 2.0 — runs BEFORE Stream A)

**Why**: greenfield framing is failure-prone when project already implements ≥1 capability from `functional_scope` elsewhere in the codebase. Run 1 caught `pkg-cse-quote/revisionHistory` only by accident (user's `integration_points` answer happened to overlap). For a user whose belief is wrong about WHERE the feature touches, Stream B fit-check searches the wrong packages + misses existing infra entirely. Internal canonical-pattern search scans project-wide independent of user belief.

**Where**: insert as new sub-section `### Phase 2.0 — Internal canonical-pattern search (MANDATORY)` BEFORE Stream A (current Phase 2 Stream A starts around line 218 of `src/commands/discover/main.md`).

**Shape (zero-escape-hatch — no fuzzy thresholds)**:

For each capability verb extracted from `memo.functional_scope` (orchestrator-side parse, 1-5 verbs):

1. Run `search_code(pattern="<capability literal>")` project-wide. Examples: `functional_scope = "audit log for quote and order changes"` → verbs = `audit`, `revision`, `history`, `snapshot`. Search for each.
2. For each result row that plausibly implements the capability:
   - `record-prior-art --reference "<concern or class name>" --kind=pattern --relevance "internal — existing implementation of <capability>" --source "internal:<file_path>"` (the `--source` prefix `internal:` distinguishes project-internal hits from web survey hits)
   - `record-integration-touchpoint --name "<concern>" --module-path "<file_path-stem>" --reason "existing capability — candidate for reuse over fresh build"`
3. After all capability verbs scanned, run a verbatim-echo report to the user via plain-prose message: `"Internal canonical-pattern search found N existing implementation(s) of <capability list>: <bulleted list with file:path>. Stream A web survey will narrow to GAP only — capabilities NOT covered by these hits. Continue?"` followed by an AskUserQuestion confirming the gap-narrowed Stream A scope. End the turn.
4. Stream A then runs WebSearch / Context7 / WebFetch scoped to the GAP capabilities only (not the full `functional_scope`).

**Phase 3 verdict-flip extension**: If `report.prior_art` has ≥1 entry with `source.startswith("internal:")`, `set-recommended-option --rationale` MUST cite the internal implementation file:path and frame the recommended option as "extend existing" (e.g., "extend `pkg-cse-quote/revisionHistory`") rather than "build new `pkg-cse-audit`". Fresh-build path requires explicit `--rationale` text identifying which capability the existing implementation does NOT cover. Helper invariant (new): cross-check that if any prior-art `source.startswith("internal:")`, then `recommended_option.rationale` contains a substring matching one of those `source` paths. Verify rule G.

**Helper changes**: minimal — no new subcommand needed. `record-prior-art --source "internal:<path>"` reuses existing setter (the `source` field already accepts free-text per helper line 591-595). New invariant G added to `cmd_verify` cross-check logic + one new test.

**Cross-check**: grep for "Phase 2" and adjust sub-phase numbering — current Phase 2 split into 2.0 (new) → 2.1 Stream A → 2.2 Stream B. Update spec prose + any cross-references.

### Fix C — slug truncation at word boundary (from Run 2 finding, deferred 2026-05-14)

**Where**: helper slug derivation logic in `src/devforge/lib/discover_helper.py` (called by `cmd_set_topic` which auto-derives `topic_slug`). Same logic likely mirrors `research_helper` — check both for parity.

**Symptom (Run 2 evidence)**: anchored topic `tamper-evident audit log across quote/order/preferences mutations, similar to how stripe-events or temporal-history work` produced saved filename `2026-05-13-tamper-evident-audit-log-across-quote-order-preferences-muta.md` — slug cut mid-word at `muta` (intended `mutations`).

**Why it matters**: collision risk on similar-prefix topics + ugly filename. Two distinct topics with identical prefix-up-to-truncation would slugify identically → forced into `-2`/`-3` rename path that obscures original intent.

**Fix**: truncate at last `-` boundary before the char cap, not at the cap itself. Implementation sketch:

```python
def _slugify_topic(topic: str, max_len: int = 60) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    if len(raw) <= max_len:
        return raw
    # truncate at last word boundary before max_len
    cut = raw[:max_len].rsplit("-", 1)[0]
    return cut or raw[:max_len]  # fallback if no boundary exists
```

**Tests**: add round-trip test with the Run 2 topic string + assert slug ends on `mutations` or earlier complete word; assert slug ≤ max_len; assert collision-resistant on prefix variants.

**Cross-check**: confirm `research_helper.py` slug derivation matches the new wording before committing — symmetric fix or scoped per-helper.

### Fix D — verdict flip rule wording (deferred review)

Same Run 2 file `Rationale` (line 54) cites `Backend lives in a separate repo per user` as a top reason for `Strained` fit. That's a USER-PROVIDED CONSTRAINT, not a fit-check finding. The other two reasons (localStorage state isn't tamper-evident; GDPR retrofit) ARE real codebase findings.

**Consider**: spec prose for `set-fit-rationale` should instruct rationale must derive from fit-check REALITY rows, not from user-stated constraints. Currently nothing prevents the orchestrator from mixing.

**Severity**: nit — doesn't change verdict correctness on this run, but blurs the "user belief vs codebase reality" contract that gives the report its diagnostic value.

**Defer or skip pending more empirical evidence** — single-occurrence finding from one run; revisit after runs 3-4 to see if pattern repeats.

### Fix E — design-option name prefix duplication (from Run 3 finding, deferred 2026-05-14)

**Symptom (Run 3 evidence)**: design options render as `### Option A: A: app-web composable...` — double-letter prefix. Repeats for B and C. Runs 2 + 3 both exhibit; run 1 did too (verify). Cause: orchestrator passes `--name "A: app-web composable..."` (letter baked in) while helper render uses the literal `<name>` after `### Option `. Two letter prefixes survive.

**Where**: `cmd_set_design_option` setter + render section in `src/devforge/lib/discover_helper.py`. Need to inspect render code first.

**Fix preference (E1 — spec-side)**: tell the orchestrator in `/discover` Phase 3 setter prose to pass `--name "<description, NO letter prefix>"` for `set-design-option`. Helper auto-numbers by insertion order during render — letter is helper-owned. Update Phase 3 setter section:

> `set-design-option --name "<description, no letter prefix>" ...` — helper assigns the letter A/B/C automatically based on insertion order. Never bake `A:` or `Option A:` into the `--name` value; that produces double-prefix render artifacts.

**Alternate (E2 — helper-side)**: render strip — detect `^[A-Z]:\s*` prefix on `name` and strip before rendering. Defensive but masks orchestrator misuse rather than preventing it. Prefer E1.

**Tests**: add render-shape assertion that emitted heading matches `^### Option [A-Z]: [^A-Z:]` (first char after second colon is not another letter+colon).

**Cross-check**: confirm `research_helper.py` does not have an analog Option-letter-prefix render path (research uses Approaches by name, not letter-indexed) — symmetric check.

### Fix F — set-next-step-text composition bugs (from Run 4 findings, 2026-05-14)

**F1 — bloated topic, no distillation**: Run 4 next-step block at line 152 of `2026-05-14-background-job-queue-...md` dumps entire `memo.functional_scope` value (multi-paragraph, ~10 sentences) into `/specify "..."` topic. Plan §"Phase 2 report shape" line 254 specifies 1-2 sentence refined description distilled from `functional_scope + users + success_criteria`. Current behavior = verbatim dump, opposite of spec intent.

**F2 — literal `\n\n` escape sequences in rendered output**: Run 4 line 158 shows `...success_criteria.\\n\\nexport-full-history:...` embedded in next-step text. Markdown does NOT convert these; they render as ugly literal `\n\n`. Inside `/specify "..."` block it also breaks shell-quoting on copy-paste.

**Where**: `cmd_set_next_step_text` + render section in `src/devforge/lib/discover_helper.py`. Need to inspect composition logic.

**Fix paths**:
- **F1 (distillation)**: prefer adding `--topic` arg to `set-next-step-text` so orchestrator passes the LLM-distilled 1-2 sentence version; helper composes from that. Alternative: helper-side truncate at first `.`/sentence boundary of `functional_scope`. Spec must instruct orchestrator to distill before calling the setter.
- **F2 (newline cleanup)**: helper's composition logic must convert `\\n\\n` / `\\n` sequences in setter values to actual newlines OR strip them to single space before embedding in next-step block. Verify multi-line setter values round-trip cleanly through JSON state file.

**Tests**:
- F1: round-trip — set `functional_scope` to multi-paragraph value → `set-next-step-text` → assert next-step `--topic` ≤2 sentences (token count check).
- F2: set any setter with literal `"\n\n"` in value → `set-next-step-text` → assert rendered output contains no literal `\n` escape sequences.

**Cross-check**: `research_helper.set-next-step-text` for parity — if research has the same composition pattern, fix symmetrically.

### When to apply

After runs 2-4 of empirical complete + their findings batched. Single revision cycle covering A + B + C + E + F + any new findings. Then:

1. Apply spec edits (Fix A + Fix B prose).
2. Apply helper invariant G + new test in `discover_helper.py` + `test_discover_helper.py`.
3. Re-run `.venv-test/bin/pytest tests/lib/test_discover_helper.py -q` — must pass.
4. Re-emit to testForge20 via `scripts/generate.sh /Users/mykolakudlyk/Projects/testForge20`.
5. Spot-rerun 1 case where Fix B materially changes output (likely background-jobs run — checks whether `agentic_*` / `worker` / `queue` patterns exist project-wide).

### 2026-05-12 session 1 — helper shipped, subagent dropped

**Design change**: dropped `discover-web-researcher` subagent. Phase 1 web survey now runs orchestrator-inline (WebSearch + Context7 MCP + WebFetch) alongside orchestrator-inline fit-check. Rationale: per `feedback_avoid_subagents_for_sequential_identical_workflows` 3-benefit test, no real parallelism / context-budget / tool-isolation win to justify dispatch — `/research` runs fully orchestrator-only since 2026-05-11 and ships clean. Spec body + emitter brief reflect the change.

**Helper shipped** (Step 2 + Step 3 of Work order — fully done):

- `src/devforge/lib/discover_helper.py` (~2,026 lines, stdlib only, Python 3.8+, POSIX-targeted).
- `src/devforge/lib/discover_helper` (POSIX launcher, mirrors `constitute_helper` pattern).
- `tests/lib/test_discover_helper.py` (~2,387 lines, **156 tests passing**).

Subcommand surface (locked):

| Phase | Subcommands |
|---|---|
| Plumbing | `reset-memo`, `reset-report`, `read-memo`, `read-report`, `preflight`, `set-topic`, `set-date` |
| Phase 0 | `set-scope-<dimension>` (×8: functional-scope, users, inputs-outputs, integration-points, constraints, non-goals, success-criteria, edge-cases), `record-references`, `record-gap`, `check-conflicts`, `record-conflict-resolution`, `scope-coverage`, `scope-finalize` (`--accept-gaps`) |
| Phase 1 | `record-prior-art`, `record-integration-touchpoint`, `record-fit-assessment`, `set-overall-fit`, `set-effort-estimate`, `set-fit-rationale` |
| Phase 2 | `set-summary`, `set-design-option`, `set-recommended-option`, `set-build-vs-buy`, `set-derisk-plan`, `set-constitution-constraints`, `set-verdict`, `set-recommendation`, `set-next-step-text` |
| Cross-phase | `render`, `verify` |

State files: `.devforge/discover-scope.json` (ScopingMemo) + `.devforge/discover-report.json` (DiscoveryReport).

Invariants enforced by `verify`:
- A — required fields populated per verdict (Worth pursuing / Promising with caveats / Reconsider have different minima).
- B — `design_options` ≥ 1 entry when verdict ∈ proceeding-set.
- C — `recommended_option.name` matches an existing `design_options[*].name`.
- D — Verdict flip rule: `overall_fit ∈ {Strained, Misfit}` OR `effort_estimate = "Major refactor required"` → verdict MUST be `Reconsider` UNLESS `memo.override_recorded == True` (set by `scope-finalize --accept-gaps`).
- E — `next_step_text` non-empty when verdict ∈ proceeding-set; None when Reconsider.
- F — `derisk_plan` ≥ 1 entry when verdict ∈ proceeding-set.

Smoke verified end-to-end: reset → 8 scope dimensions → all Phase 2 setters → `verify` exit 0 → `render` emits full Markdown with all sections.

**Next session pickup (do these in order)**:

1. **Step 4** — author spec at `src/commands/discover/main.md` (no `model:` frontmatter override; orchestrator-inline across all 4 phases — NO subagent file). Use `src/commands/research/main.md` as the structural template (it is the closest parallel — same orchestrator-only pattern, same preflight gate, same rubric-Q&A shape). Dispatch the `instruction-author` agent with a self-contained brief including: helper subcommand surface (above), state-file paths, verdict flip rule, the spec must instruct verbatim helper-output echoes via the "copy VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase)" wording, stop discipline after every `AskUserQuestion` / prose prompt, Phase 1 uses WebSearch + Context7 (`mcp__context7__resolve-library-id` + `mcp__context7__query-docs`) + WebFetch directly from the orchestrator. The brief MUST also instruct instruction-author to consult `claude-code-guide` for current slash-command authoring conventions before drafting frontmatter.

2. **Step 5** — triple-verify loop. After spec drafts, dispatch `instruction-reviewer` + `claude-code-guide` in parallel (single message, two `Agent` tool calls). Iterate via `instruction-author` until both return clean. Then present to user for approval.

3. **Step 6** — update `scripts/emitters/claude.py` `_PROMOTED` list: add `"discover"` to the tuple. No agents-emitter update (no /discover subagent).

4. **Step 7** — cross-update `CLAUDE.md` (workflow line + command details section), `README.md`, `DEVELOPMENT-STATUS.md`, `src/CLAUDE.md` template, `.devforge/storage-rules.md` per `feedback_release_docs`. Add a `discover/YYYY-MM-DD-<topic-slug>.md` line under Artifact Storage parallel to `research/`.

5. **Step 8** — empirical test on testForge20 with a genuinely greenfield topic (e.g., "audit log persistence layer"). Validate: Phase 0 dialogue converges on bounded turns; Phase 1 narrowed query used (not raw user input); docs+CBM consultation paths fire; `.devforge/cbm-usage.log` records calls; render output is actionable; verdict flip rule triggers when fit is Strained/Misfit.

6. **Step 9** — ship to develop-2.0-init + CHANGELOG entry.

**Active TaskList at session end**:

- ✅ Stage A1: discover_helper foundation
- ✅ Stage A2: Phase 0 setters
- ✅ Stage A3: Phase 1 setters
- ✅ Stage A4: Phase 2 setters + render + verify
- ⏭️ Stage B: author `src/commands/discover/main.md` spec
- ⏭️ Stage C: triple-verify spec (instruction-reviewer + claude-code-guide parallel; iterate via instruction-author)
- ⏭️ Stage D: emitter `_PROMOTED` + cross-doc updates
- ⏭️ Stage E: empirical on testForge20 (user-driven)
- ⏭️ Stage F: CHANGELOG + ship

## Why /discover

`/research` (existing, under redesign per REDESIGN-RESEARCH-PLAN.md) targets existing-code delta — bug fix + enhancement. Both produce report shape: locate + trace + root-cause + options-to-bridge. Greenfield features (no related code exists yet) don't fit that shape: report's primary section "Existing Related Code" goes empty, "Gaps" balloons, "Approaches" collapses to "pick a library."

Greenfield needs a different lens:

- Prior-art survey (industry references, comparable products, established patterns).
- Integration surface sketch (where would this live in current architecture?).
- 2–3 design options (data model / state machine / API shape — not library comparison).
- Derisk plan (which unknown to prototype first).
- Build-vs-buy proposal.

`/discover` fills that gap. Workflow slot: `/discover → /specify → /plan → /breakdown → /execute-task → ...` — parallel to `/research` on the existing-code track. User picks at entry point.

## Naming locked

`/discover`. Alternatives considered in chat: `/groom` (Jira/PM backlog-refinement overload), `/explore`, `/scout`, `/prospect`. `/discover` reads clearest for an engineering audience; minor PM-discovery overload acceptable in context.

## Scope locked

1. Greenfield only — no existing-code investigation surface. If `/discover` detects related code mid-flow, recommend follow-up `/research` rather than handle both.
2. Pre-`/specify` slot, parallel to `/research`.
3. Output: structured report (rendered to console + ask-to-save like `/research`).
4. Orchestrator-inline web research + orchestrator-inline fit-check (see Agent ownership below — both subagents dropped 2026-05-12 per /research empirical evidence + `feedback_avoid_subagents_for_sequential_identical_workflows`).
5. Helper-owns-shape (per `feedback_helper_owns_shape_principle`). Report schema owned by Python helper; LLM composes values via setters.
6. **Phase 0 scoping dialogue** before investigation. Vague-idea input (e.g., "auth in NestJS") gets narrowed via rubric-driven Q&A before web-research dispatch or fit-check — otherwise web-research drowns in 50 generic results, fit-check scan has no focus target.

## Prerequisites (hard gate)

`/discover` refuses to run unless all setup-chain commands have completed. Helper `preflight` subcommand checks three artefacts at startup; exits non-zero with explicit instruction if any missing:

| Required artefact | Produced by | Hard-gate check |
|---|---|---|
| `.devforge/manifest.json` (or equivalent) | `/init-forge` | File exists |
| `docs/architecture.md` | `/generate-docs` | File exists + non-empty |
| `.devforge/project-config.json` | `/configure` | File exists + non-empty |
| `constitution.md` | `/constitute` | File exists + non-empty |

On missing artefact, helper emits:

```
BLOCKED: /discover requires the full 4-command setup chain.
Missing: <artefact>
Run: /init-forge → /generate-docs → /configure → /constitute, then retry /discover.
```

Exit code 2. No graceful skip, no fallback path. Setup is a prerequisite, not a recommendation.

## Phases (target order)

```
PHASE 0: Scoping dialogue          ← rubric-driven Q&A, orchestrator-only
PHASE 1: Investigation             ← orchestrator-inline web survey (WebSearch + Context7 + WebFetch) + orchestrator-inline fit-check (CBM + docs)
PHASE 2: Report drafting           ← orchestrator composes report from Phase 0 memo + Phase 1 findings
PHASE 3: Save + recommend          ← ask-to-save, next-step recommendation
```

## Existing-code awareness layer (docs + MCP)

`/discover` consults **two layers** when reasoning about existing code — both Phase 0 (pre-rubric hints for `integration_points`) and Phase 1 (fit-check):

### Layer 1: docs/ narrative context

Read by orchestrator (Phase 0 pre-rubric step + Phase 1 fit-check):

- `docs/architecture.md` — project-tier architecture (per Track 4, shipped 2026-05-09)
- `docs/<package>/architecture.md` — package-tier architecture
- `docs/<package>/<concern>/index.md` — concern md (per /generate-docs Phase 2)
- `docs/glossary.md` — term grounding (per JUDGMENT-LAYER-PLAN Track B)

Use docs/ for **narrative orientation** (what the project is, package responsibilities, domain vocabulary). Mirrors /research preflight pattern (`src/commands/research/main.md` Phase 0).

### Layer 2: CBM/MCP structural queries

CBM (codebase-memory-mcp) tools called by orchestrator inline (Phase 1 fit-check):

- `search_graph(name_pattern=..., label=..., qn_pattern=...)` — find named functions/classes/routes (File-label queries use `name_pattern`, not `file_pattern` — per memory `feedback_cbm_search_graph_pattern_keys`)
- `search_code(pattern=...)` — text-fallback for inline framework expressions invisible to graph (per memory `feedback_cbm_discovery_chain_search_graph_then_code` — mandatory chain: `search_graph` → `search_code` → declare absent only if BOTH return nothing)
- `trace_path(function_name, mode=calls|data_flow|cross_service)` — call chains for fit-check impact analysis
- `get_code_snippet(qualified_name)` — read source (NOT raw Read/cat)
- `get_architecture(aspects=...)` — structural summary
- `agentic_context "<topic>"` / `agentic_impact "<topic>"` / `agentic_architecture "<topic>"` — synthesized bundles when LLM mode enabled

### Runtime enforcement (hooks already shipped)

Four hooks at `src/hooks/` (propagated to target dir via install.sh; shipped 2026-05-09 per `project_track1_f11_hooks_shipped`):

- `cbm-session-reminder` (SessionStart) — injects CBM-first protocol into context on session start/resume/clear/compact
- `cbm-code-discovery-gate` (PreToolUse Read|Grep|Glob) — once-per-session block to remind CBM-first
- `bash-ban-raw-tools` (PreToolUse Bash) — once-per-session block on raw `grep`/`find`/`cat` over source-file extensions
- `cbm-mcp-marker` (PostToolUse Bash|mcp__codebase-memory-mcp__.*) — telemetry to `.devforge/cbm-usage.log`

Hooks fire once per session as reminder. `/discover` spec MUST explicitly instruct orchestrator (Phase 1 fit-check) to use CBM tools by name — hooks are reminder layer, not strict enforcement after first block. (Web-survey side has no CBM overlap — uses WebSearch / Context7 / WebFetch directly.)

### Preflight gate

Before Phase 1 work begins (web survey + fit-check, both orchestrator-inline), orchestrator runs preflight (mirror /research):

```
./.devforge/lib/generate_docs_helper preflight
```

Skip if `.devforge/.preflight-stamp` is fresher than 60s. Ensures CBM index is current. If preflight fails (no index), Phase 1 cannot proceed — hard-gate prerequisites already guarantee docs/ + constitution.md exist, so a preflight failure means CBM index is stale or missing. Emit error + instruct user to run `index_repository` (or rerun `/generate-docs` if substrate is broken).

## Phase 0: Scoping dialogue

**Goal**: convert vague-idea input into a structured scoping memo before any investigation fires. Without Phase 0, Phase 1 web survey + fit-check have no narrowed query and produce noisy output.

**Shape**: rubric-driven Q&A. Helper owns the rubric (closed list of dimensions); LLM detects unfilled dimensions, asks one question at a time targeting the highest-uncertainty dimension; helper records user-confirmed values via setters.

**Rubric (generic, topic-agnostic):**

| Dimension | What it captures | Example ("auth in NestJS") |
|---|---|---|
| `functional_scope` | What does the feature DO | "JWT login + refresh + RBAC + 2 OAuth providers" |
| `users` | Who interacts | "End users + admins; no machine-to-machine" |
| `inputs_outputs` | Data shape (request/response, events, persisted entities) | "Email+password OR OAuth callback → JWT pair" |
| `integration_points` | Where it touches existing system | "All API routes need guard; extend existing user table" |
| `constraints` | Perf / compliance / deploy / scale | "GDPR; 7-day session; SOC2 audit log" |
| `non_goals` | Explicit OUT (prevents scope creep) | "No SAML SSO; no biometric; no passwordless yet" |
| `success_criteria` | High-level "done" signal | "Signup → login → hit protected route → token refreshes" |
| `edge_cases` | Failure modes + unwanted-behavior surfaces (separate from `constraints` — limits vs failure semantics are different questions) | "OAuth provider returns 500; token replay; concurrent login race; user-row delete cascade" |

**Pre-rubric supplementary prompts**:

Before rubric Q&A begins, helper asks one-shot supplementary prompts (free-text, no state machine, doesn't gate exit):

- `references` — "Any similar existing code, libraries, or product references to pattern after?" Stored as `ScopingMemo.references: list[str]`. When non-empty, orchestrator-inline web survey + fit-check both receive reference names as additional search anchors — dramatically narrows web-research and codebase-fit scans. Skip cleanly if user has no reference; proceed to rubric without penalty.

Adopted from Agent OS `/shape-spec` pattern (compresses many future questions into one when user already has an anchor). Source: <https://buildermethods.com/agent-os/shape-spec>.

**Pre-rubric docs scan** (orchestrator-side):

Before asking the rubric questions, orchestrator reads `docs/architecture.md` + `docs/glossary.md` to surface candidate `integration_points` hints. When user reaches the `integration_points` question, orchestrator offers detected hints as starting suggestions (e.g., "I see your project has packages X, Y, Z — likely touchpoints?") rather than asking blind. Hooks-friendly: orchestrator reads `.md` (not source code), so CBM gate does not block.

Docs presence is guaranteed by the hard-gate prerequisites — no skip path needed.

**Question strategy per dimension**:

- **Closed-choice dimensions** (e.g., "JWT vs session", "build vs adopt OSS") → `AskUserQuestion` with 2–4 options (per `feedback_askuserquestion_single_line_only` — single-line, no multi-line markdown).
- **Open dimensions** (e.g., "describe your OAuth providers + scopes") → free-text prompt rendered as plain prose, user replies in next turn.
- LLM picks per dimension type at runtime.

**Bounded turns**:

- Hard cap: 3 follow-ups per dimension. After cap, helper logs the dimension as `Partial` and moves on.
- State enum (per dimension): `Clear` (user-confirmed) / `Partial` (asked but unresolved within turn cap) / `Missing` (not yet asked). Aligned with GitHub Spec Kit clarify taxonomy. Source: <https://github.com/github/spec-kit/blob/main/templates/commands/checklist.md>.
- Helper tracks coverage after every setter call. After every turn, helper emits coverage state (e.g., `5/8 Clear, 2 Partial, 1 Missing`).
- Exit when all 8 dimensions are `Clear` OR user explicitly accepts gaps. On accepted-gap exit, helper emits two artefacts:
  - **Coverage summary table** rendered at top of scoping memo (per-dimension `Clear`/`Partial`/`Missing` state).
  - **`[NEEDS CLARIFICATION: <dimension> — <gap description>]` markers** serialized into `ScopingMemo.gaps`, so `/specify` (downstream) sees explicit uncertainty rather than silent absence. Adopted from Spec Kit. Source: <https://github.com/github/spec-kit/blob/main/spec-driven.md>.
- `scope-finalize` exit code: `0` when all `Clear`; `0` with `override_recorded=true` when user accepted gaps + helper recorded the override; non-zero when `Partial`/`Missing` present without override (forces explicit user choice).

**Persistence**:

- Scoping memo saved to `.devforge/discover-scope.json` after every setter call (mirrors `/constitute` + `/configure` per-answer persistence pattern).
- If user kills `/discover` mid-flow, restart resumes from saved state — no dialogue replay.
- Helper subcommand `read-scope` returns current memo for resume; `set-scope-<dimension>` sets one dimension; `scope-coverage` returns coverage state; `scope-finalize` locks the memo for Phase 1.

**Misalignment detection (hybrid by severity)**:

When user's later answer contradicts or drifts from earlier confirmed dimensions, helper + orchestrator detect and respond by severity. Three categories:

| Category | Example | Detection layer | Response |
|---|---|---|---|
| **Direct contradiction** | `non_goals` contains "OAuth" + `integration_points` mentions "OAuth callback routes" | **Helper-side** (token-overlap rule, deterministic, no LLM) | **Hard-block.** Halt rubric Q&A, present conflict via AskUserQuestion ("which to keep?"), rewrite loser dimension, then resume. |
| **Drift / scope creep** | Started "auth for end users", later answer adds "admin SSO" — expands scope | **LLM-side** (orchestrator runs short check after each setter call: "does this new answer expand or conflict with previously confirmed dimensions?") | **Soft-flag.** Log to `conflicts` list, continue rubric Q&A, surface at next natural pause: "this expands scope from X to X+Y — keep, narrow, or split into two features?" |
| **Refinement** | `users` = "end users" → later "actually end users + admins" | **LLM-side** (same check, classified as refinement when older answer is subset of new) | **Quiet update.** Rewrite affected dimension, log change in memo, no interruption. |

**Per-setter call protocol**:

```
After every set-scope-<dimension>:
  1. Helper runs check-conflicts (token-overlap rules; cheap, deterministic).
     If direct contradiction → block via AskUserQuestion, record resolution, rewrite loser dimension.
  2. Else orchestrator runs LLM-side drift check (short prompt).
     If drift detected → log to ScopingMemo.conflicts with type=drift, surface at next pause.
     If refinement detected → log + quietly rewrite affected dimension.
  3. Resume rubric Q&A.
```

**Anti-patterns explicitly forbidden**:

- Silent overwrite — later answer must never replace earlier without surfacing in conflicts log.
- LLM-only detection for direct contradictions — token-overlap rules run first; LLM only handles semantic drift.
- Force user to re-walk all 8 dimensions on conflict — only re-ask the affected dimension(s).

**What Phase 0 feeds**:

- Phase 1 orchestrator-inline web survey: narrowed query built from `functional_scope + constraints + non_goals + edge_cases` (e.g., "NestJS Passport JWT multi-tenant RBAC patterns + token-replay mitigation" instead of "NestJS auth"). When `references` is non-empty, include reference names as additional search anchors. Orchestrator calls WebSearch / Context7 (`resolve-library-id` → `query-docs`) / WebFetch directly — no subagent dispatch.
- Phase 1 orchestrator-inline fit-check: scoped scan target from `integration_points` (e.g., "scan API route definitions + user/auth-adjacent modules" instead of "scan entire codebase"). The user's `integration_points` answer is **the user's belief** about what the new feature touches — Phase 1 produces the **reality check** (what actually exists, what would be touched, what would need refactor first). Mismatch between belief and reality is a Phase 2 report finding, not an error.
- Phase 2 report: every section is informed by memo (Prior Art relevance scored against `functional_scope` + `references`; Design Options framed against `constraints` + `non_goals` + `edge_cases`; Derisk Plan derived from highest-uncertainty `success_criteria` + flagged `edge_cases`; **Fit Assessment** reconciles user's `integration_points` belief against Phase 1 reality check; gap markers from `ScopingMemo.gaps` rendered in a dedicated "Open uncertainties" section).

## Phase 2 report shape (target)

```markdown
# Discovery: [Topic Name]

**Date**: [YYYY-MM-DD]
**Topic**: [user's original description]
**Verdict**: Worth pursuing / Promising with caveats / Reconsider

## Summary

[3–5 sentences: what the idea is, why it's worth (or not) pursuing, recommended starting shape]

## Prior Art

| Reference | What it is | Relevance |
|-----------|------------|-----------|
| [product/library/pattern] | [1-line] | [how it informs our shape] |

## Integration Surface

[Where this would live in the current architecture — bullet list of touchpoints + reasons.]

| Touchpoint | Module/file | Why touched |
|------------|-------------|-------------|
| [name] | [path] | [reason] |

## Fit Assessment

[Reconciliation of user's Phase 0 `integration_points` belief against Phase 1 scan reality. Mismatch IS the headline finding.]

| Touchpoint | User expected | Reality (scan) | Effort | Blockers |
|------------|---------------|----------------|--------|----------|
| [name] | yes/no | [what actually exists + compatibility note] | Low / Med / High | [list or "none"] |

**Overall fit**: Good / Acceptable / Strained / Misfit
**Effort estimate**: Low / Medium / High / Major refactor required
**Rationale**: [1–3 sentences explaining the fit verdict — what works, what doesn't, what would need to change first]

## Design Options

### Option A: [Name]
- **Shape**: [data model / state machine / API surface sketch — pseudocode OK]
- **Pros**: [list]
- **Cons**: [list]
- **Complexity**: Low / Medium / High

### Option B: [Name]
- (same shape)

**Recommended option**: [X] — [one-line rationale]

## Build vs Buy

| Build | Buy/Adopt |
|-------|-----------|
| [what we'd own] | [SaaS / OSS candidates] |

**Recommendation**: [Build / Buy / Hybrid] — [reasoning]

## Derisk Plan

[Ordered list of unknowns to probe first; smallest viable slice that validates the riskiest assumption.]

## Constitution Constraints

[If constitution.md populated, cite relevant rules + their impact on design.]

## Recommendation

- **Proceed**: "Run `/specify "[refined description]"` to formalize AC."
- **Reconsider**: "[Reason]. Consider [alternative] instead."

## Next step

[Rendered only when Verdict = Worth pursuing or Promising with caveats. Skipped on Reconsider.]

Copy the block below into a new `/specify` session manually. No automated handoff — user controls when (or if) `/specify` runs.

~~~
/specify "[1-2 sentence refined description distilled from functional_scope + users + success_criteria]"

Discovery reference: discover/YYYY-MM-DD-<topic-slug>.md
Key facts:
- Functional scope: [from ScopingMemo.functional_scope]
- Users: [from ScopingMemo.users]
- Success criteria: [from ScopingMemo.success_criteria]
- Recommended option: [Option name from Design Options]
- Open uncertainties: [count] (see discovery doc §Open uncertainties)
~~~
```

**Why this section exists**: `/discover` produces its own document shape (this report), not a `/specify` spec. This section is just a copy-pasteable starter prompt for the user — it lives at the bottom of the saved md file. Back-link to the discovery doc preserves full context for whoever reads `/specify` later.

### Verdict flip rule (effort-aware)

Helper enforces the following escalation:

- If Fit Assessment `Overall fit` = `Strained` OR `Misfit` → Verdict MUST be `Reconsider` UNLESS user's Phase 0 `non_goals` or explicit confirmation accepts the refactor cost upfront (helper records the override).
- If `Effort estimate` = `Major refactor required` → same rule: Verdict flips to `Reconsider` with rationale tying back to the specific Fit Assessment row that triggered it.
- Helper exit code from `verify` is non-zero if Verdict + Fit Assessment combination violates the rule without recorded override.

## Agent ownership — orchestrator-only across all phases

**All phases run on the main thread. NO subagent dispatch.**

**Phase 0 (Scoping dialogue)**: orchestrator-only. Dialogue cannot be dispatched — AskUserQuestion + free-text turns + setter calls must stay on the main thread for interaction fidelity.

**Phase 1 (Investigation)**: orchestrator-inline web survey + orchestrator-inline fit-check, both on the main thread (run sequentially or interleaved per orchestrator judgment).

- **Web survey** — orchestrator calls `WebSearch` / `mcp__context7__resolve-library-id` → `mcp__context7__query-docs` / `WebFetch` directly using the narrowed query from Phase 0 (`functional_scope + constraints + non_goals + edge_cases + references` when present). Output recorded via `record-prior-art` setter calls.
- **Fit-check** — uses the **two-layer awareness** (docs + CBM/MCP, see "Existing-code awareness layer" above) to scan for module structure scoped to Phase 0 `integration_points`. Discovery chain:
  - **Layer 1 (docs/)**: read `docs/architecture.md`, `docs/<package>/architecture.md` for the suspected packages, `docs/<package>/<concern>/index.md` for relevant concerns, `docs/glossary.md` for term grounding.
  - **Layer 2 (CBM)**: `agentic_context "<integration_points value>"` for synthesized bundle → `search_graph(name_pattern=...)` for named symbols → `search_code(pattern=...)` fallback for inline expressions (mandatory chain per `feedback_cbm_discovery_chain_search_graph_then_code`) → `trace_path` for impact chains on fit-check candidates → `get_code_snippet` to read source.
  - **Raw Read/Grep/Glob over source files**: orchestrator obeys the same CBM-first discipline; hooks (`bash-ban-raw-tools` + `cbm-code-discovery-gate`) enforce.

Fit-check outputs: (a) compressed touchpoint list (what exists + where), (b) **fit-check** per touchpoint — does the user's belief match reality? What's the integration effort? Are there blockers (incompatible schemas, conflicting patterns, missing infrastructure)? Reconciled view recorded via helper setters (`record-integration-touchpoint`, `record-fit-assessment`, `set-overall-fit`, `set-effort-estimate`).

**Phase 2 (Report drafting)**: orchestrator-only. Composes report from Phase 0 memo + Phase 1 findings.

**Phase 3 (Save + recommend)**: orchestrator-only. AskUserQuestion for save decision.

**Rationale for dropping all subagents (2026-05-12)**:
- `discover-fit-checker` (already dropped 2026-05-11) — /research empirical run showed dispatched investigator subagent cost 5-7× total tokens vs orchestrator-inline AND tunneled onto the first matched surface.
- `discover-web-researcher` (dropped 2026-05-12) — per `feedback_avoid_subagents_for_sequential_identical_workflows` 3-benefit test: parallelism gain is illusory when orchestrator is the dispatcher (orchestrator still blocks on subagent return); context-budget concern is overstated (orchestrator can call WebSearch directly and select compressed entries inline); tool isolation is not a real win when no other concurrent tool surface needs protection. `/research` is fully orchestrator-only and ships clean — `/discover` follows the same pattern.

## Constraints

- Zero-escape-hatch policy in spec body (no OR / if / except / unless / use-judgment).
- Helper-owns-shape: Python helper at `src/devforge/lib/discover_helper.py` mirroring `/constitute` + `/generate-docs` subcommand pattern.
- LLM-first density: spec body is LLM instructions, not human-onboarding wiki.
- Triple-agent verification on every spec edit: **instruction-author** writes/edits → **instruction-reviewer** checks intra-file logical flow + cross-reference consistency + sentence-level hallucination risk → **claude-code-guide** verifies Claude Code authoring conventions (external). All three must return clean before commit. Per `feedback_dual_agent_verify_command_statements` (rename pending).
- No real project names in examples (per `feedback_no_real_project_names`).
- Test-first for helper functions (per `feedback_test_first_python_helpers`).
- **No `model:` override** in `src/commands/discover/main.md` frontmatter (per `feedback_avoid_command_model_override`). Inherit session model.
- **Spec body is self-contained LLM instructions** scoped to `/discover` execution only — no forward refs to `/specify` or downstream phases in the spec prose (per `feedback_llm_instructions_self_contained`). The copy-pasteable next-step text lives in the OUTPUT document only (Phase 2 "Next step" section), never in the spec body. No automated handoff at runtime.
- **Verbatim echo directive** when spec instructs LLM to display helper output (coverage summary, scoping memo render, etc.): use the wording "copy VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase)" (per `feedback_verbatim_echo_directive`). "Relay" / "show" are ambiguous and get skipped.
- **Discovery document has its own shape** — not a `/specify` template, not a `/research` report. Owns: Verdict, Summary, Prior Art, Integration Surface, Fit Assessment, Design Options, Build-vs-Buy, Derisk Plan, Constitution Constraints, Open uncertainties, Next-step copy-pasteable text. Distinct identity preserved through render.

## Work order

- **Step 1**: confirm naming + scope + Phase 0 dialogue shape (done in chat 2026-05-11).
- **Step 2**: draft schemas (Python dataclasses / pydantic) for `discover_helper.py`:
  - Phase 0 `ScopingMemo` schema — 8 rubric dimensions (`functional_scope`, `users`, `inputs_outputs`, `integration_points`, `constraints`, `non_goals`, `success_criteria`, `edge_cases`) + per-dimension state enum (`Clear | Partial | Missing`, aligned with GitHub Spec Kit taxonomy) + per-dimension turn counts. Plus supplementary fields: `references: list[str]` (pre-rubric pointers; empty list when user has none), `gaps: list[{dimension: str, description: str}]` (NEEDS CLARIFICATION markers when user accepts partial exit), `override_recorded: bool`, `conflicts: list[Conflict]` (misalignment detection log). `Conflict` shape: `{type: "direct" | "drift" | "refinement", dimensions: list[str], description: str, resolution: "blocked-pending-user" | "user-chose-<X>" | "logged-no-action" | None}`. State persisted to `.devforge/discover-scope.json` (mirrors /constitute's `.devforge/constitute.json` pattern).
  - Phase 2 `DiscoveryReport` schema — sections per "Phase 2 report shape" above + next-step text section at bottom. Closed enums for Verdict, Recommendation, Complexity. State persisted to `.devforge/discover-report.json` while in-flight (mirrors /constitute's per-section state); rendered to `discover/YYYY-MM-DD-<topic-slug>.md` on Phase 3 save.
- **Step 3**: implement helper subcommands. Test-first per `feedback_test_first_python_helpers`. Subcommands:
  - Phase 0: `read-scope`, `set-scope-<dimension>` (×8 — includes `set-scope-edge-cases`), `record-references` (pre-rubric, optional one-shot), `record-gap` (when user accepts a dimension as `Partial`/`Missing` — appends NEEDS CLARIFICATION marker to `gaps`), `check-conflicts` (runs token-overlap rules after each setter; returns list of detected direct contradictions; orchestrator wraps with LLM-side drift check), `record-conflict-resolution` (logs user's resolution choice, rewrites loser dimension on direct contradiction), `scope-coverage` (returns `Clear`/`Partial`/`Missing` per dimension + coverage table + conflicts log summary), `scope-finalize` (emits coverage summary block + serialized gap markers + conflicts log; exit non-zero if `Partial`/`Missing` without `override_recorded` OR if any `conflicts.resolution == "blocked-pending-user"`).
  - Phase 1: `record-prior-art`, `record-integration-touchpoint`, `record-fit-assessment` (per-touchpoint: user-expected vs reality + effort + blockers), `set-overall-fit`, `set-effort-estimate`. All consumed by orchestrator inline — `record-prior-art` from web-survey results (WebSearch / Context7 / WebFetch called directly); fit-check setters from CBM + docs traversal.
  - Phase 2: `set-design-option`, `set-build-vs-buy`, `set-derisk-plan`, `set-verdict`, `set-recommendation`, `set-next-step-text` (composes the copy-pasteable `/specify` prompt section from ScopingMemo + DiscoveryReport state; only emits when Verdict ≠ Reconsider; pure text generation, no automation), `render` (concatenates all sections including next-step text at the bottom). `verify` enforces Verdict flip rule (Strained/Misfit/Major-refactor → Reconsider unless override recorded).
  - Prerequisites: `preflight` (hard-gate check for `.devforge/manifest.json` + `docs/architecture.md` + `constitution.md`; non-zero exit + message on missing).
  - Cross-phase: `summary`, `verify` (mirrors `/constitute` pattern).
  - **Test fixture**: author `tests/lib/fixtures/discover-sample-report.md` covering one happy-path greenfield-feasible scenario (generic placeholders per `feedback_no_real_project_names` — e.g., "auth in a TypeScript backend framework"). Round-trip discipline (per `feedback_test_first_python_helpers`): build via real helper setter calls → `render` → diff against fixture. Fixture maintained as the canonical expected-shape artifact for `render()` regression tests. Skeleton lives in helper code (inline render, mirrors /constitute); fixture is a complete example, not a skeleton.
- **Step 4**: author spec at `src/commands/discover/main.md` + reference docs (if any). Spec body covers all 4 phases with explicit transition gates (Phase 0 → Phase 1 requires `scope-finalize` exit code 0). No subagent file — Phase 1 web survey + fit-check both run orchestrator-inline.
- **Step 5**: triple-agent verify in iterative apply-verify loop (per `feedback_iterative_review_loop_preferred`):
  1. `instruction-author` drafts/edits spec.
  2. `instruction-reviewer` + `claude-code-guide` review in parallel (single message, two Agent tool calls).
  3. If either reviewer returns findings → loop back to step 1 with fixes briefed to author. Repeat until both reviewers clean.
  4. Present clean draft to user for approval.
  5. User approves → proceed to Step 6. User redirects → loop back to step 1 with new direction.
- **Step 6**: update emitter `scripts/emitters/claude.py` `_PROMOTED` list for `discover` command (per `feedback_emitter_promoted_cross_check`). No agents-emitter update — `/discover` ships no subagent.
- **Step 7**: cross-update README, DEVELOPMENT-STATUS, CLAUDE.template, storage-rules (per `feedback_release_docs`).
- **Step 8**: empirical test on testForge20 with a genuinely greenfield topic. Validate Phase 0 dialogue converges within bounded turns; validate Phase 1 web survey + fit-check both use narrowed query (not raw user input); validate docs/ + CBM consultation paths fire correctly + hooks log to `.devforge/cbm-usage.log`.
- **Step 9**: ship to develop-2.0-init / main with CHANGELOG entry. Cross-update README + DEVELOPMENT-STATUS + CLAUDE.template (per `feedback_release_docs`) confirmed at this step.

## Verify criteria

- **Step 3**: 100% helper subcommand tests pass; helper round-trips state via JSON. Coverage check on real input shapes (per `feedback_test_first_python_helpers`). Phase 0 specific:
  - `scope-coverage` returns accurate state after each setter call.
  - Bounded-turn cap (3 follow-ups/dimension) enforced; over-cap returns "partial" state, no crash.
  - `scope-finalize` exit code 0 only when all dimensions are `confirmed` OR user explicitly accepted gaps (helper records the override).
- **Step 4**: spec passes intra-file consistency check (instruction-author). Phase transitions documented with helper gate references.
- **Step 5**: both verifier agents return clean.
- **Step 6**: `./install.sh` on fresh testForge20 promotes `/discover` into `.claude/commands/`.
- **Step 8**: empirical run produces report with all sections populated; user confirms output is actionable + matches the design-exploration lens (not feasibility-check repurposed). Validate:
  - Phase 0 dialogue converges within bounded turns on a vague-idea input (e.g., "auth in NestJS").
  - Phase 1 web survey + fit-check both use narrowed query derived from scoping memo (inspect orchestrator turn transcript; raw user input must NOT appear verbatim as the WebSearch / Context7 / `search_graph` query). Orchestrator-inline fit-check uses the same narrowed scope from `integration_points`.
  - Kill-and-resume: kill `/discover` mid-Phase-0, restart, confirm dialogue resumes from saved state without re-asking confirmed dimensions.
  - **Fit Assessment populated with at least one user-belief-vs-reality mismatch row OR explicit "all match" rationale; never empty.**
  - **Verdict flip rule fires correctly**: induce a Strained/Misfit Fit Assessment, confirm Verdict auto-flips to Reconsider; record an override, confirm verify exits 0.
  - **`edge_cases` dimension populated** on greenfield input; not silently skipped or merged into `constraints`.
  - **Coverage summary table emitted** at Phase 0 exit (8 dimensions with `Clear`/`Partial`/`Missing` state); renders at top of scoping memo.
  - **`[NEEDS CLARIFICATION]` gap markers serialized** in `ScopingMemo.gaps` when user accepts partial exit; downstream `/specify` can read them. Markers also surface in Phase 2 report "Open uncertainties" section.
  - **`references` field captured** when user provides anchors; empty list (no fabrication) when user has none. Orchestrator web survey + fit-check both include references as search anchors when present.
  - **Hard-gate prerequisites enforced**: induce missing `docs/architecture.md`, confirm `preflight` exits non-zero with the required setup-chain message; restore and confirm exits clean.
  - **Next-step text section rendered** at bottom of saved md when Verdict ≠ Reconsider; section contains copy-pasteable `/specify "..."` prompt + key facts (functional_scope, users, success_criteria, recommended option, open-uncertainty count) + link back to saved discovery doc. Section omitted on Reconsider verdict. No orchestrator-driven automation — text is for user manual copy.
  - **Misalignment detection fires**:
    - **Direct contradiction**: induce conflict (e.g., set `non_goals` containing "OAuth", then `integration_points` mentioning "OAuth"); confirm helper `check-conflicts` flags it; confirm orchestrator blocks via AskUserQuestion; confirm `scope-finalize` exits non-zero until user resolves.
    - **Drift**: induce scope expansion (e.g., set `users` to "end users", later set to "end users + admins"); confirm LLM-side check classifies as `drift`; confirm logged to `conflicts` without blocking; confirm user prompted at next natural pause.
    - **Refinement**: induce subset-to-superset update on same dimension; confirm quiet rewrite without surfacing; confirm logged with `type=refinement` and `resolution=logged-no-action`.
  - **No silent overwrites**: any later answer that affects a confirmed dimension is logged in `conflicts` regardless of classification.
  - **Phase 1 fit-check (orchestrator-inline) uses CBM tools by name** (`search_graph`, `search_code`, `trace_path`, `get_code_snippet`) — never Read/Grep/Glob over source. Confirm by inspecting orchestrator turn transcript.
  - **Preflight gate fires** before Phase 1 work begins (web survey + fit-check, both orchestrator-inline); skipped only when `.devforge/.preflight-stamp` is fresher than 60s.
  - **`.devforge/cbm-usage.log` records** Phase 1 CBM invocations (telemetry from `cbm-mcp-marker` hook). Confirm log file grows during test run.

## Open questions

1. Should `/discover` output be savable to `discover/YYYY-MM-DD-topic.md` (mirroring `/research`'s `research/`)? Default yes for symmetry.
2. Cost gate: orchestrator-inline web survey uses Context7 + WebSearch + WebFetch. Surface estimated token cost before kicking off, parallel to `/generate-docs` Phase 1 cost gate?
3. ~~Hybrid input (mostly greenfield but touches some existing code)~~ **Closed 2026-05-11.** `/discover` always runs codebase fit-check in Phase 1; output may flip Verdict to Reconsider on high-effort fit (see Phase 2 report shape § Verdict flip rule + Agent ownership § Phase 1).
4. Helper signature: does helper need `read-*` subcommands (per `/constitute` pattern) or just setters + render + verify? Decide once schema is drafted.
5. Should `/discover` consult `constitution.md` proactively? Same conditional + non-blocking pattern as `/research` (per REDESIGN-RESEARCH-PLAN.md open question §2).
6. Phase 0 rubric extensibility per topic domain (auth vs data-pipeline vs UI feature). **Updated 2026-05-11**: universal 8th dimension `edge_cases` added based on SDD framework survey (Spec Kit + Kiro EARS + Tessl all treat failure-handling as first-class). Default still: strictly generic in v1, no topic-specific sub-dimensions. Revisit only if empirical use shows specific topics still under-specified after the 8-dimension rubric + supplementary `references` prompt.
7. BMAD PRFAQ kickoff sub-mode for ultra-vague input (≤1 sentence, no anchor verbs/nouns) — deferred per YAGNI. Add only if empirical signal shows the vague-input case is common. Source: <https://docs.bmad-method.org/explanation/analysis-phase/>.

## When resuming work

1. Read this file in full.
2. Read REDESIGN-RESEARCH-PLAN.md for the existing-code counterpart (boundary check — confirm split still holds).
3. Read `/constitute` as the reference shape: `src/devforge/lib/constitute_helper.py` + `src/commands/constitute/main.md`.
4. Pick up at the next unaddressed Work order step. (No subagents — Phase 1 web survey + fit-check both orchestrator-inline; see Agent ownership section.)
